"""Publish ride/food events to the required RabbitMQ topic exchange.

Normal mode publishes one event every two seconds. D1 can be injected with
--bad-every N (the Nth event has no `zone`). --key and --count make a short,
repeatable routing experiment possible without changing the production defaults.
"""
import argparse
import json
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone


try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

EXCHANGE = "rapido-dispatch"
CITY_ZONES = {
    "bangalore": ["koramangala", "indiranagar", "whitefield"],
    "chennai": ["tnagar", "adyar", "whitefield"],
}
TYPES = ["ride", "food"]


def make_event(seq: int, bad_every: int = 0, key: str | None = None):
    """Build (routing_key, event); omit zone on every Nth event when requested."""
    if key:
        parts = key.split(".")
        city = parts[0]
        zone = parts[1] if len(parts) > 1 else "unknown"
        event_type = parts[2] if len(parts) > 2 else "unknown"
    else:
        city = random.choice(list(CITY_ZONES))
        zone = random.choice(CITY_ZONES[city])
        event_type = random.choice(TYPES)

    event = {
        "id": str(uuid.uuid4())[:8],
        "city": city,
        "zone": zone,
        "type": event_type,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    routing_key = key or f"{city}.{zone}.{event_type}"
    if bad_every and seq % bad_every == 0:
        del event["zone"]
    return routing_key, event


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--bad-every", type=int, default=0)
    parser.add_argument("--count", type=int, default=0, help="0 means run until Ctrl+C")
    parser.add_argument("--key", help="fixed city.zone.type routing key for experiments")
    args = parser.parse_args()
    if args.interval <= 0 or args.bad_every < 0 or args.count < 0:
        parser.error("interval must be positive; bad-every and count cannot be negative")

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
    seq = 0
    try:
        while True:
            seq += 1
            routing_key, event = make_event(seq, args.bad_every, args.key)
            channel.basic_publish(
                exchange=EXCHANGE,
                routing_key=routing_key,
                body=json.dumps(event),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,  # persistent message for durable-queue recovery demos
                ),
            )
            malformed = "  <-- MALFORMED (missing zone)" if "zone" not in event else ""
            print(f"[{seq}] sent {routing_key} {json.dumps(event)}{malformed}", flush=True)
            if args.count and seq >= args.count:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\ndispatcher stopped")
    finally:
        if conn.is_open:
            conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
