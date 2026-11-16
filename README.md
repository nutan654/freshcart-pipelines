# Break It Till It Holds

**A Fault-Injection Lab for an End-to-End Data Engineering Platform**

This repository builds and tests four small engineering components: GitHub Actions CI,
FreshCart ELT on Snowflake, a Mage Iris ML pipeline, and RabbitMQ topic-event streaming.
Its main record is [`FAULTS.md`](FAULTS.md), where each deliberate fault is paired with its
detector, recovery and evidence. No dashboard, chatbot or frontend is included.

## Project components

| Part | Component | Main idea | Location |
|---|---|---|---|
| A | Git + CI/CD | Catch a broken 80/20 split before merging/deployment | `.github/workflows/`, `tests/` |
| B | Snowflake ELT | Preserve raw data, normalize source differences, quarantine invalid rows, deduplicate and publish idempotently | `elt/` |
| C | Mage ML | Use block-level tests to prevent invalid input and low-quality model output from reaching exporters | `iris_project/` |
| D | RabbitMQ | Route events by topic, ACK valid messages, discard poison messages and demonstrate redelivery after consumer crash | `stream/` |
| Bonus | RabbitMQ → Snowflake | Batch order events into the instructor's existing ELT SQL | `stream/bonus_*.py`, `elt/runner.py` |

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the Mermaid diagram and detection
boundaries. The main flows are:

- Git push → GitHub Actions → Python 3.12 → pytest.
- FreshCart landing files → Bronze raw VARIANT → Silver validation / dedup → Quarantine +
  reference enrichment → Gold fact table → quality checks.
- Mage `load_iris` → `validate_input` → `prepare_data` → `train_model` → `save_results` and
  `evaluate_model`.
- Dispatcher → `rapido-dispatch` topic exchange → private driver queues → ACK/NACK; a
  separate durable queue is used for the crash/redelivery demonstration.

## Technology choices

- **Git / GitHub Actions:** version history and an automated regression gate on every push.
- **Python / pytest:** deterministic tests for the required split, event validation and topic
  matching; these tests run without Snowflake, Mage or RabbitMQ services.
- **Snowflake:** the instructor's warehouse ELT target; Bronze VARIANT preserves raw API
  payloads, while SQL handles normalization, quarantine, SCD2 and Gold `MERGE`.
- **Mage + scikit-learn:** block orchestration and attached `@test` gates around the supplied
  Iris decision-tree exercise.
- **RabbitMQ + pika:** topic exchange routing with explicit manual acknowledgements.

## Repository structure

```text
freshcart-pipelines/
├── README.md
├── FAULTS.md
├── requirements.txt
├── requirements-mage.txt
├── requirements-snowflake.txt
├── .env.example
├── elt/
│   ├── freshcart_elt.ipynb
│   ├── runner.py
│   └── sql/
├── iris_project/
│   ├── metadata.yaml
│   ├── data_loaders/
│   ├── transformers/
│   ├── data_exporters/
│   └── pipelines/iris_classifier/metadata.yaml
├── stream/
│   ├── dispatcher.py
│   ├── driver.py
│   ├── routing.py
│   └── bonus_*.py
├── tests/
└── docs/
```

## Base install and CI tests

Python 3.12 is used by GitHub Actions. From this repository root:

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pytest -q
```

The base suite does not need a cloud account or broker. The GitHub workflow runs the same
suite on every push. Mage and Snowflake connectors are intentionally optional so CI stays
fast and does not require credentials. A local compile + pytest run is recorded in
[`evidence/local_validation.txt`](evidence/local_validation.txt); it used Python 3.13.5,
so it is not a substitute for the required Python 3.12 GitHub Actions run.

## Environment variables and secrets

Copy `.env.example` to `.env`, then fill only the services you use. `.env` is ignored by Git.

| Variable | Used by | Example / purpose |
|---|---|---|
| `RABBITMQ_URL` | Part D / Bonus | `amqp://guest:guest@localhost:5672/%2F` |
| `SNOWFLAKE_ACCOUNT` | Part B / Bonus | Your Snowflake account identifier |
| `SNOWFLAKE_USER` | Part B / Bonus | Your Snowflake username |
| `SNOWFLAKE_PASSWORD` | Part B / Bonus | Your Snowflake password; never commit it |
| `SNOWFLAKE_ROLE` | Part B / Bonus | Defaults to `ACCOUNTADMIN` to match the instructor connection setup; use least privilege when possible |
| `SNOWFLAKE_WAREHOUSE` | Part B / Bonus | Defaults to `FRESHCART_WH` |
| `FRESHCART_LANDING_DIR` | Part B / Bonus | Local folder for compressed landing files |

No credentials or connection URLs are committed. The instructor's sample account/user values
were removed from the submitted copy of the notebook and replaced with environment lookups.

## Part B — Snowflake ELT

Install the optional connector:

```bash
pip install -r requirements-snowflake.txt
```

Open `elt/freshcart_elt.ipynb` in Jupyter/Colab, set the environment variables, and run all
cells top-to-bottom. The original schemas and SQL are preserved in `elt/sql/`. Verify the
instructor baseline: Bronze 8, Silver clean 6, quarantine 2 (`ORD-1004`, `ORD-1006`), dedup
4, Gold 4 orders, ₹7,785.00 revenue, 126 points and 25% rejection share. These are target
values to verify, not claims that Snowflake was executed in this environment.

Fault instructions and the B2 SQL patch are documented in `elt/README.md` and the notebook.

## Part C — Mage Iris

Install Mage separately:

```bash
pip install -r requirements-mage.txt
mage run iris_project iris_classifier --test
```

To run depth experiments, delete `iris_predictions.csv` before each run and execute
`max_depth=1,2,3,4,5` using `--runtime-vars`. C2 invalid-input switches are documented in
`iris_project/README.md`. Start the UI with `mage start iris_project` and capture the graph.
The model accuracy table is deliberately pending until actual Mage runs are performed.

## Part D — RabbitMQ

Start a local broker (Docker example):

```bash
docker run -d --name freshcart-rabbit -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

Then run three or more drivers in separate terminals before starting the dispatcher:

```bash
python stream/driver.py Ravi "bangalore.koramangala.*"
python stream/driver.py Arjun "bangalore.*.ride"
python stream/driver.py Control "bangalore.#"
python stream/dispatcher.py
```

Let them run for two minutes. For the D1 malformed-message fault (one malformed event every ten messages) use:

```bash
python stream/dispatcher.py --key bangalore.koramangala.ride --bad-every 10 --count 20 --interval 0.5
```

The D2 named durable queue crash/recovery steps and all six exact driver bindings are in
[`stream/README.md`](stream/README.md).

## Bonus streaming integration

The optional integration is isolated from mandatory Part D. Its incoming event envelope is
`{"source":"web"|"mobile", "data":{...raw source record...}}`. The consumer collects a
one-minute batch, writes `bonus_batch.json` atomically, ACKs the stored messages, and invokes
`elt.runner` unless `--dry-run` is selected. Configure both RabbitMQ and Snowflake, install
`requirements-snowflake.txt`, and follow `stream/README.md`. On handoff failure the persisted
file can be replayed with `python -m elt.runner --batch-file bonus_batch.json`.

## Evidence, report and known limitations

- Main fault ledger: [`FAULTS.md`](FAULTS.md).
- Step-by-step execution: [`docs/STAGE_GUIDE.md`](docs/STAGE_GUIDE.md).
- Evidence list: [`docs/evidence_checklist.md`](docs/evidence_checklist.md).
- Predictions: [`docs/predictions.md`](docs/predictions.md).
- Assignment report: [`docs/assignment_report.md`](docs/assignment_report.md).

**Known limitations / unexecuted evidence:** this workspace has no GitHub remote, Snowflake
credentials, live Mage UI session, or RabbitMQ broker. Therefore genuine red/green Actions
runs, Snowflake row counts, Mage accuracy outcomes, RabbitMQ receipt/ACK/NACK and redelivery
screenshots must be produced by running the commands in your environment. Their result
fields remain Pending. The six routing predictions are unit-tested locally, but that does
not substitute for live broker routing evidence. The bonus adapter expects the instructor's
existing CRM, FX and pincode reference data to have been loaded and uses the extracted SQL;
it does not add an external pincode lookup.
