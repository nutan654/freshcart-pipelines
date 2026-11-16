"""Collect FreshCart order events for a time window and hand them to the ELT runner.

Expected message body: {"source":"web"|"mobile", "data": {<raw API order>}}.
Messages are ACKed after an atomic local batch-file write. If Snowflake handoff fails,
re-run `python -m elt.runner --batch-file bonus_batch.json` after fixing the cause.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import pika

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

EXCHANGE = "freshcart-orders"
BINDING = "orders.#"
QUEUE = "freshcart-bonus"
BATCH_FILE = Path("bonus_batch.json")


def collect(channel, seconds: float) -> tuple[list, list[int]]:
    """Collect JSON payloads without ACK; return payloads and delivery tags."""
    batch, tags = [], []
    deadline = time.monotonic() + seconds
    messages = channel.consume(QUEUE, inactivity_timeout=1.0, auto_ack=False)
    try:
        while time.monotonic() < deadline:
            method, _properties, body = next(messages)
            if method is None:
                continue
            try:
                event = json.loads(body)
                if not isinstance(event, dict):
                    raise ValueError("event must be a JSON object")
                batch.append(event)
                tags.append(method.delivery_tag)
            except (ValueError, UnicodeDecodeError) as exc:
                print("Discarding invalid JSON event:", exc, flush=True)
                channel.basic_nack(method.delivery_tag, requeue=False)
    finally:
        channel.cancel()
    return batch, tags


def write_batch_atomically(batch: list) -> None:
    temp_path = BATCH_FILE.with_suffix(BATCH_FILE.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(batch, handle, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, BATCH_FILE)


def hand_off(batch: list) -> None:
    # Use the same SQL files extracted from the instructor notebook.
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from elt.runner import run_streamed_orders
    run_streamed_orders(batch)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=60.0)
    parser.add_argument("--dry-run", action="store_true", help="write the batch file without Snowflake handoff")
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("seconds must be positive")

    url = os.environ.get("RABBITMQ_URL", "amqp://localhost")
    conn = pika.BlockingConnection(pika.URLParameters(url))
    channel = conn.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE, durable=True)
    channel.queue_bind(exchange=EXCHANGE, queue=QUEUE, routing_key=BINDING)
    channel.basic_qos(prefetch_count=5000)
    print(f"Collecting from {QUEUE} for {args.seconds:.0f}s ...", flush=True)
    batch, delivery_tags = collect(channel, args.seconds)

    # Persist first, ACK second: if the process dies before ACK RabbitMQ can redeliver.
    write_batch_atomically(batch)
    for tag in delivery_tags:
        channel.basic_ack(tag)
    if conn.is_open:
        conn.close()

    print(f"Collected {len(batch)} messages; persisted {BATCH_FILE}")
    if not args.dry_run and batch:
        try:
            hand_off(batch)
        except Exception:
            print("Snowflake handoff failed. The persisted batch remains available for replay:", BATCH_FILE, file=sys.stderr)
            raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
