# Assignment report — Break It Till It Holds

> **Submission status:** implementation and report structure are prepared. Execution-only
> observations and screenshots remain explicitly pending because no GitHub remote, Snowflake
> credentials, Mage runtime session, or RabbitMQ broker were supplied in this workspace.
> Replace every Pending field with output captured from your own run; do not present expected
> values as observed evidence.

## A. Git and CI/CD

### A1. Repository and automated tests

The repository uses the required GitHub Actions workflow: every push checks out the code,
sets up Python 3.12, installs `requirements.txt`, and runs pytest. The `prepare_data` block
uses the instructor's `train_test_split(test_size=0.2, random_state=42)` and the test asserts
120 training rows and 30 testing rows. The workflow is deliberately lightweight and does
not require Mage or Snowflake credentials.

**A1 fault procedure:** change only `test_size=0.2` to `test_size=0.3` in
`iris_project/transformers/prepare_data.py`; commit and push that change. The row-count tests
should fail because the split sizes no longer match 120 and 30. Restore `0.2` in a second
commit and push. Attach the genuine red and green GitHub Actions run links and commits here.

- Local fault reproduction: pytest failed with **105 training / 45 testing** rows when `test_size=0.3`; restoring `0.2` returned the local suite to **14 passed**. See `evidence/a1_local_fault_reproduction.txt`.
- Red GitHub Actions run: **Pending — capture actual run URL**.
- Breaking commit: **Pending — add commit hash**.
- Fixing commit: **Pending — add commit hash**.
- Green GitHub Actions run: **Pending — capture actual run URL**.

### A2. Six Git commands and local versus remote history

| Command | Meaning |
|---|---|
| `git init` | Creates the local `.git` repository in the working folder. |
| `git add <path>` | Places selected working-tree changes into the staging area. |
| `git commit -m "message"` | Saves a snapshot of staged changes in local repository history. |
| `git remote add origin <URL>` | Records the GitHub repository URL under the local nickname `origin`; it does not upload files. |
| `git push -u origin main` | Sends local commits to GitHub and records the upstream branch for later pushes. |
| `git pull origin main` | Fetches remote commits and integrates them into the current local branch. |

A commit is local history only. GitHub cannot see it until `git push` transfers the commit
objects and updates the remote branch. A meaningful project history should show separate
commits for repository setup, Mage implementation/tests, ELT SQL, stream implementation,
and final documentation/evidence updates. Do not fabricate commits or timestamps.

## B. Snowflake ELT fault laboratory

### B1. Baseline and duplicate order handling

The instructor pipeline is preserved as Extract → Landing → Bronze → Silver checked/clean →
Quarantine → Silver dedup → reference enrichment → Gold → Quality Checks. Its baseline to
verify is Bronze 8, Silver cleaned 6, quarantine 2 (ORD-1004 and ORD-1006), dedup 4, Gold 4,
revenue ₹7,785.00, loyalty points 126, and 25% rejected. **Observed baseline: Pending.**

The website API uses flat names (`order_id`, `cust_email`, `amount`, `updated_at`); the mobile
API uses nested / camel-case names (`orderId`, `customer.email`, `total.value`, `updatedAt`).
`SQL_10_ORDERS_CLEAN` maps both into a common `unified` shape with `UNION ALL`, then trims,
normalizes, parses dates/amounts, and uppercases currencies. For ORD-1003, the mobile
version has the later update timestamp and a populated amount; for ORD-1002, duplicate
records are resolved with arrival order when timestamps tie.

`SQL_20_ORDERS_DEDUP` applies `QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY
updated_at DESC, ingest_seq DESC) = 1`, leaving one row per order. On a replay, Bronze is
expected to append eight more raw rows, while Silver dedup should remain four and Gold
should remain four because `SQL_40_GOLD` uses `row_hash` and `MERGE`. **Replay evidence: Pending.**

### B2. Unsupported currency

The baseline `ARRAY_CONSTRUCT_COMPACT` checks order ID, email, pincode, date, update timestamp
and non-positive amount. The B2 variant adds an `IFF` condition for currency values outside
INR and USD. Because the currency was normalized with `UPPER(TRIM(currency))`, the EUR on
ORD-1006 is unambiguously invalid. The original reasons should be `bad_email` and
`bad_pincode`; the updated Silver checked reasons should additionally include
`unsupported_currency`. Gold should not gain an order because ORD-1006 is quarantined.

Quarantine idempotency is implemented by the `NOT EXISTS` predicate on `source`, null-safe
`order_id`, and the source `updated_at` stored in `row_data`. A repeated version of the same
bad source record is therefore not inserted a second time. The existing quarantine row is
not automatically rewritten with the new reason array; compare `silver.orders_checked` for
the updated reasons and the quarantine row count separately. **Observed result: Pending.**

### B3. Customer SCD Type 2 event

This is a legitimate historical data change, not a defective record. The predicted values
for CUST-02 / ORD-1002 are recorded in `docs/predictions.md`: two SCD2 versions, Gold tier
for the 2026-09-01 order, 70 points for ORD-1002, 161 Gold points total, and one Gold row
with changed `published_at`. The SCD2 SQL removes duplicate `(cust_id, valid_from)` events,
then uses `LEAD(valid_from)` to set each version's `valid_to` to the day before the next
version. The Gold join uses `order_date BETWEEN valid_from AND valid_to`, so it applies the
tier that was effective on the order date rather than the current tier.

**Predicted versus actual:** Actual values and before/after table outputs are Pending until
the CRM event is appended and the notebook is run.

### B4. Future-dated order check

The sixth quality check counts rows in `silver.orders_dedup` whose `order_date` is greater
than Snowflake `CURRENT_DATE()`. Insert the documented `ORD-TEST-FUTURE` fixture, rerun the
transformations and capture the check printing `PROBLEM` with a non-zero count. Then delete
the mock source row, rebuild Silver, explicitly remove the mock Gold row (the Gold `MERGE`
is upsert-only), and run checks again to capture `PASS`. **Both outputs: Pending.**

### B5. ETL versus ELT

ETL transforms data before loading it into the warehouse, which can reduce the amount of
raw data stored and is useful when data must be masked or transformed before entering the
target system. ELT loads source records first and uses the warehouse to transform them,
which keeps an auditable raw Bronze layer and makes it possible to rerun revised SQL rules
without extracting the source again. FreshCart benefits from ELT because web/mobile records
need repeated normalization, currency validation, deduplication and historical enrichment.
An ETL approach can still be preferable when regulation or a source contract requires
sensitive fields to be removed before data is landed in the warehouse.

## C. Mage Iris ML pipeline

### C1. Model quality test gate

The pipeline is `load_iris → validate_input → prepare_data → train_model`, with
`save_results` and `evaluate_model` as two downstream branches from `train_model`. Loader,
validation, split and model-quality tests are attached to their respective blocks. The
split contract is 120 train rows and 30 test rows; the model-quality gate requires accuracy
of at least 0.80. The five required runtime configurations are listed below.

### C1 experiment table

Delete `iris_predictions.csv` before each run and execute `max_depth=1,2,3,4,5` with
`mage run iris_project iris_classifier --test --runtime-vars`. Record values from Mage's
actual console output, not a separate scikit-learn calculation:

| max_depth | Test accuracy from Mage | `test_accuracy` passed? | `iris_predictions.csv` created? |
|---:|---:|---|---|
| 1 | Pending | Pending | Pending |
| 2 | Pending | Pending | Pending |
| 3 | Pending | Pending | Pending |
| 4 | Pending | Pending | Pending |
| 5 | Pending | Pending | Pending |

The downstream exporter is responsible for writing predictions. A model failing the
`@test` should not be saved because its quality contract has not been satisfied; persisting
it could allow a later consumer to mistake an invalid artifact for a releasable model.
The implementation therefore avoids writing a model file in `train_model`, before its
attached test has executed.

### Required evaluation branch

`evaluate_model` is an additional transformer whose upstream is `train_model`. It prints a
confusion matrix and a metrics table containing accuracy, macro precision, macro recall and
macro F1. Attach the actual output and Mage UI graph screenshot: **Pending**.

### C2. Invalid input data

`validate_input` is a separate transformer immediately after `load_iris`, with an attached
`@test` requiring no missing values and exactly three target classes. The passing case is
the original Iris dataset. To inject a controlled failure, run with
`--runtime-vars '{"inject_missing": true}'` or
`--runtime-vars '{"drop_target_class": true}'`. Capture the test failure and then run with
default variables to restore the valid input. **Execution outputs: Pending.**

## D. RabbitMQ streaming fault laboratory

### D1. Topic routing

The required exchange is `rapido-dispatch`. The six binding patterns are Ravi
`bangalore.koramangala.*`, Priya `bangalore.indiranagar.*`, Arjun `bangalore.*.ride`,
Meena `bangalore.*.food`, Karthik `chennai.tnagar.food`, and Control `bangalore.#`.
`docs/predictions.md` contains the predicted receivers for all six instructor examples.
The pure-Python routing tests check those predictions, but only the live RabbitMQ run proves
actual receipt. **Live queue evidence: Pending.**

### D1 fault — malformed message and ACK/NACK behavior

The dispatcher selects Bangalore or Chennai, a configured zone and ride/food type, and
publishes JSON events every two seconds. The driver validates required fields. A valid
message is acknowledged with `basic_ack`; a malformed event missing `zone` is rejected
with `basic_nack(requeue=False)`. Requeueing a message that can never pass validation would
create a poison-message loop: it would repeatedly return to the queue, consume capacity and
potentially prevent healthy messages from progressing. **Two-minute runtime and malformed
message console evidence: Pending.**

### D2 fault — consumer crash and redelivery

The recovery demonstration uses a named durable queue and persistent message. The consumer
process exits before ACK, leaving the delivery unacknowledged. After RabbitMQ detects the
connection loss, the message should become available again; the restarted consumer should
see `method.redelivered=True` and ACK it. Processing and ACK are different events: application
logic may have run even though the broker has not been told it completed. This is why a
crash after processing but before ACK can produce duplicate delivery and why consumers
should make their side effects idempotent. **Redelivery is not claimed until the console
shows `REDELIVERED`: Pending.**

## Reflection — a genuine local test failure and recovery

During repository validation, the first `pytest -q` run stopped during test collection with
`ModuleNotFoundError: No module named 'pika'`. The affected tests were exercising pure event
construction and JSON validation; they did not connect to RabbitMQ. The cause was that the
broker library was imported at module load time, making an optional runtime dependency a
requirement even for offline unit tests. I moved the `pika` imports into the dispatcher and
driver entry-point functions. The command-line programs still require `pika`, which remains
listed in `requirements.txt`, but importing their pure helper functions no longer needs a
broker installation.

The next run exposed a second, separate collection issue: pytest treated imported Mage block
functions named `test_accuracy` and `test_input_quality` as test cases and tried to inject a
fixture called `output`. Those functions are Mage hooks, not standalone pytest tests. I
aliased them on import in the unit-test module and called the aliases from explicit tests.
The recovery was verified by `python -m compileall -q elt iris_project stream tests` and a
subsequent `pytest -q` result of **14 passed**. The captured environment was Python 3.13.5
with pytest 9.0.2; this is local validation, not a claim that GitHub Actions on Python 3.12
or the live RabbitMQ experiments have run. The final local output is in
`evidence/local_validation.txt`.

## Screenshot appendix

Attach evidence listed in `docs/evidence_checklist.md`. Evidence filenames and dates are
Pending until screenshots and terminal captures exist.
