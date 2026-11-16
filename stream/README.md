# Part D — RabbitMQ topic dispatch

The dispatcher publishes JSON events every two seconds to the durable `rapido-dispatch`
topic exchange. The routing keys are `city.zone.type`. Drivers declare private
exclusive/auto-delete queues in normal mode and bind the instructor's six patterns.

## Start RabbitMQ

Docker example:

```bash
docker run -d --name freshcart-rabbit -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

Set `RABBITMQ_URL=amqp://guest:guest@localhost:5672/%2F` in `.env` (default). Install
Python dependencies with `pip install -r requirements.txt`.

## Exact driver bindings

```bash
python stream/driver.py Ravi    "bangalore.koramangala.*"
python stream/driver.py Priya   "bangalore.indiranagar.*"
python stream/driver.py Arjun   "bangalore.*.ride"
python stream/driver.py Meena   "bangalore.*.food"
python stream/driver.py Karthik "chennai.tnagar.food"
python stream/driver.py Control "bangalore.#"
```

Run at least three in separate terminals, then run `python stream/dispatcher.py` for two
minutes. Stop with Ctrl+C. Take screenshots of dispatcher plus driver terminals.

## D1 six deterministic routing examples

```bash
python stream/routing.py
pytest -q tests/test_routing.py
```

The pure-Python matcher checks predicted routing locally; the live broker experiment is
still required to prove actual message receipt. To compare actual receipt, start all six
driver commands above in separate terminals, then publish each of the following keys one
at a time from another terminal. Check which driver consoles receive each message and compare
with `docs/predictions.md`:

```bash
python stream/dispatcher.py --key bangalore.koramangala.food --count 1
python stream/dispatcher.py --key bangalore.indiranagar.ride --count 1
python stream/dispatcher.py --key bangalore.whitefield.ride --count 1
python stream/dispatcher.py --key chennai.tnagar.food --count 1
python stream/dispatcher.py --key chennai.whitefield.ride --count 1
python stream/dispatcher.py --key bangalore.koramangala --count 1
```

The last example deliberately has only two routing-key words; the Control binding uses
`#`, which can match zero or more trailing words.

## D1 fault — malformed message / NACK

Run Control and Arjun, then publish twenty deterministic messages with every tenth missing
its `zone`:

```bash
python stream/dispatcher.py --key bangalore.koramangala.ride --bad-every 10 --count 20 --interval 0.5
```

Expected behavior to verify: good messages print `ACK sent`; malformed ones print `BAD ...
NACK, discarded`. `requeue=False` prevents a permanently invalid message from being delivered
forever. There is no dead-letter exchange configured, so NACKed poison messages are discarded.

## D2 fault — consumer crash / redelivery

Use a named durable queue for this separate recovery experiment:

```bash
# Terminal 1: start; this exits abruptly before ACK on its first valid delivery.
python stream/driver.py Ravi "bangalore.koramangala.*" --queue crash-demo --crash-once
# Terminal 2: send one persistent message.
python stream/dispatcher.py --key bangalore.koramangala.food --count 1
# Terminal 1: restart without the crash switch; same queue binding is reused.
python stream/driver.py Ravi "bangalore.koramangala.*" --queue crash-demo
```

Capture the first delivery + `CRASH before ACK`, then the restarted consumer's
`REDELIVERED` + `ACK sent`. The queue is durable and messages are published persistent.
Clean up after capture with `rabbitmqctl delete_queue crash-demo` (or delete it in the
RabbitMQ management UI).

A message being processed means application code ran; acknowledging means the consumer told
the broker it can remove the delivery. A crash between those moments can cause duplicate
processing, which is why consumers should be idempotent.

## Bonus: FreshCart to Snowflake

The bonus uses a separate durable exchange/queue and expects records shaped like:

```json
[
  {"source": "web", "data": {
    "order_id": "ORD-STREAM-01", "cust_email": "priya.r@gmail.com",
    "cust_name": "Priya R", "order_date": "2026-09-03", "amount": "100.00",
    "currency": "INR", "pincode": "600041", "updated_at": "2026-09-03 17:00:00"
  }}
]
```

Start consumer first and publisher second:

```bash
pip install -r requirements-snowflake.txt
python stream/bonus_consumer.py --seconds 60 --dry-run
python stream/bonus_publisher.py --file orders.json
```

For the live handoff, omit `--dry-run`. The consumer writes `bonus_batch.json` atomically
before ACKing collected messages, then calls `elt.runner`, which reuses the extracted
instructor SQL and Gold `MERGE`. On Snowflake handoff failure, replay the persisted file:

```bash
python -m elt.runner --batch-file bonus_batch.json
```

Run the publisher twice with the same order IDs and compare Gold count/revenue/points.
New messages must reference existing customer, FX and pincode reference data; this adapter
does not introduce a new external lookup service.
