"""Run a RabbitMQ driver: python stream/driver.py NAME PATTERN.

Normal mode creates a private, exclusive queue. Valid messages are ACKed; malformed
messages are NACKed with requeue=False so poison messages are discarded.
For D2, --queue NAME creates/uses a durable named queue and --crash-once exits
before the first ACK to let RabbitMQ redeliver that unacknowledged delivery.
"""
import argparse
import json
import os
import sys


try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

EXCHANGE = "rapido-dispatch"
REQUIRED_FIELDS = {"id", "city", "zone", "type", "ts"}


def decode_event(body: bytes) -> dict:
    """Decode and validate the event envelope without requiring a broker."""
    event = json.loads(body)
    if not isinstance(event, dict):
        raise ValueError("message body must be a JSON object")
    missing = REQUIRED_FIELDS.difference(event)
    if missing:
        raise ValueError("missing required field(s): " + ", ".join(sorted(missing)))
    return event


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("pattern")
    parser.add_argument("--queue", help="named durable queue for D2 recovery experiment")
    parser.add_argument("--crash-once", action="store_true", help="exit before ACK of first non-redelivered message")
    args = parser.parse_args()

    try:
        import pika
    except ImportError as exc:
        print("Install runtime dependencies with: pip install -r requirements.txt", file=sys.stderr)
        return 1

    url = os.environ.get("RABBITMQ_URL", "amqp://localhost")
    try:
        conn = pika.BlockingConnection(pika.URLParameters(url))
    except pika.exceptions.AMQPConnectionError as exc:
        print(f"Cannot connect to RabbitMQ: {exc}", file=sys.stderr)
        return 1

    channel = conn.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    if args.queue:
        queue = channel.queue_declare(queue=args.queue, durable=True).method.queue
    else:
        queue = channel.queue_declare(queue="", exclusive=True, auto_delete=True).method.queue
    channel.queue_bind(exchange=EXCHANGE, queue=queue, routing_key=args.pattern)
    channel.basic_qos(prefetch_count=1)

    def on_message(ch, method, properties, body):
        redelivered = " (REDELIVERED)" if method.redelivered else ""
        try:
            event = decode_event(body)
        except (ValueError, UnicodeDecodeError) as exc:
            print(f"[{args.name}] BAD {method.routing_key} -> NACK, discarded ({exc}){redelivered}", flush=True)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        print(f"[{args.name}] got {method.routing_key} {json.dumps(event)}{redelivered}", flush=True)
        if args.crash_once and not method.redelivered:
            print(f"[{args.name}] CRASH before ACK", flush=True)
            os._exit(1)  # intentionally simulates abrupt process death / lost TCP connection
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"[{args.name}] ACK sent", flush=True)

    channel.basic_consume(queue=queue, on_message_callback=on_message, auto_ack=False)
    print(f"[{args.name}] queue={queue} pattern={args.pattern} (Ctrl+C to stop)", flush=True)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print(f"\n[{args.name}] stopped")
    finally:
        if conn.is_open:
            conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
