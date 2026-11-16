"""Publish FreshCart raw order envelopes to the isolated bonus exchange.

Input file is a JSON list of {"source":"web"|"mobile", "data": {...}} records.
Run the same input twice to demonstrate Silver deduplication and Gold MERGE idempotency.
"""
import argparse
import json
import os
import sys

import pika

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

EXCHANGE = "freshcart-orders"
ROUTING_KEY = "orders.new"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, help="JSON file with FreshCart source/data envelopes")
    args = parser.parse_args()
    with open(args.file, encoding="utf-8") as handle:
        orders = json.load(handle)
    if not isinstance(orders, list):
        parser.error("input file must contain a JSON list")
    for index, item in enumerate(orders):
        if not isinstance(item, dict) or item.get("source") not in {"web", "mobile"} or not isinstance(item.get("data"), dict):
            parser.error(f"record {index} must contain source='web'|'mobile' and a data object")

    url = os.environ.get("RABBITMQ_URL", "amqp://localhost")
    try:
        conn = pika.BlockingConnection(pika.URLParameters(url))
    except pika.exceptions.AMQPConnectionError as exc:
        print(f"Cannot connect to RabbitMQ: {exc}", file=sys.stderr)
        return 1
    channel = conn.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    for order in orders:
        channel.basic_publish(
            exchange=EXCHANGE,
            routing_key=ROUTING_KEY,
            body=json.dumps(order),
            properties=pika.BasicProperties(content_type="application/json", delivery_mode=2),
        )
    print(f"Published {len(orders)} FreshCart order envelopes to {EXCHANGE} ({ROUTING_KEY})")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
