# Stage-by-stage execution guide

The implementation is prepared, but execution-based evidence must come from your own
accounts and local broker. Run in this order so each experiment has a known-good baseline.

## Stage 1 — Git and CI (Part A)

```bash
git init
git branch -M main
git add .gitignore .env.example requirements.txt requirements-mage.txt requirements-snowflake.txt README.md pytest.ini
git commit -m "Add repository skeleton and dependency groups"
git add iris_project tests/test_prepare_data.py .github/workflows/ci.yml
git commit -m "Add Mage Iris blocks, split tests and CI"
pytest -q
```

Create an empty GitHub repository named `freshcart-pipelines`, then:

```bash
git remote add origin <YOUR_GITHUB_REPOSITORY_URL>
git push -u origin main
```

A1: change `test_size=0.2` to `0.3`, run `pytest -q`, commit and push to get the genuine red
Actions run. Restore `0.2`, commit and push again to get the green run. Do not manufacture
Actions screenshots or commit history. Then make separate meaningful commits for ELT SQL,
RabbitMQ implementation, and final report/evidence.

## Stage 2 — FreshCart baseline (Part B)

Follow `elt/README.md`. Use a Snowflake account with sufficient permission to create the
`FRESHCART_WH` warehouse and `FRESHCART` database. Never commit `.env`. Run the notebook
from top to bottom and compare every baseline count with the assignment before continuing.
If a count differs, stop and investigate rather than adjusting SQL to force the expected value.

## Stage 3 — FreshCart experiments

- B1: run `run_pipeline()` a second time and compare Bronze, dedup, Gold and hash values.
- B2: replace the `SQL_10_ORDERS_CLEAN` string with the B2 file variant; query ORD-1006
  before/after and compare quarantine row count.
- B3: write the pre-run predictions in `docs/predictions.md`, append the Arjun event, run,
  compare SCD2 and Gold. Remove the event after collecting evidence.
- B4: use the notebook's documented future-order SQL, collect PROBLEM, delete the raw and
  Gold fixture records, rebuild transformations, and collect PASS.

Run all original baseline queries again after restoring all experiment changes.

## Stage 4 — Mage (Part C)

```bash
python -m pip install -r requirements-mage.txt
mage run iris_project iris_classifier --test
```

Perform the five C1 runtime configurations with output CSV deletion before every run (see
`iris_project/README.md`). Perform C2 valid, injected-failure and restored-valid runs. Start
`mage start iris_project` to capture the graph and evaluation outputs.

## Stage 5 — RabbitMQ (Part D)

Start a local broker using the Docker command in `stream/README.md`. Start drivers before
the dispatcher. Run the dispatcher with three or more drivers for two minutes. Then perform
the deterministic malformed-event and named durable-queue crash/recovery experiments.

## Stage 6 — Bonus

Only after Part B and Part D work, test the isolated `freshcart-orders` integration. The
consumer writes its batch file before ACK. Configure both RabbitMQ and Snowflake credentials,
run the same FreshCart order batch twice, and compare Gold totals.

## Stage 7 — Report

Complete `docs/assignment_report.md` from actual run outputs. Add the repo URL, at least five
meaningful commits, real CI links, exact terminal/warehouse results and a half-page reflection
about a failure you executed. Export the report to the requested PDF name after evidence is
complete; keep screenshots in an appendix (outside the eight-page answer body).
