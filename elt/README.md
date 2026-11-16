# Part B — FreshCart Snowflake ELT

`freshcart_elt.ipynb` is based on the instructor's `freshcart_elt_simple` notebook. Its
sample records, schemas, SQL transformations, object names and first-run expected values
are retained. Connection details are read from environment variables rather than stored
in the notebook.

## Setup and run

1. Install base + Snowflake packages from the repository root:
   `python -m pip install -r requirements-snowflake.txt`
2. Copy `.env.example` to `.env` and set `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, and
   `SNOWFLAKE_PASSWORD` (plus role/warehouse if needed). The `.env` file is ignored by Git.
3. Open `elt/freshcart_elt.ipynb` in Jupyter or Colab and run from top to bottom.
4. Capture the result tables and `quality_checks()` output. The notebook has no claimed
   execution output in this repository because no Snowflake account/credentials were supplied.

## Baseline to verify (do not force)

| Layer / metric | Instructor baseline |
|---|---:|
| `bronze.orders_raw` first run | 8 |
| `silver.orders_clean` | 6 |
| `quarantine.orders` | 2 (`ORD-1004`, `ORD-1006`) |
| `silver.orders_dedup` | 4 |
| `gold.fct_orders` | 4 |
| Gold revenue | ₹7,785.00 |
| Gold loyalty points | 126 |
| Rejection share | 25% |

Use these queries to collect actual output:

```sql
SELECT COUNT(*) AS bronze_rows FROM bronze.orders_raw;
SELECT COUNT(*) AS silver_clean_rows FROM silver.orders_clean;
SELECT order_id, reasons FROM quarantine.orders ORDER BY order_id;
SELECT COUNT(*) AS dedup_rows FROM silver.orders_dedup;
SELECT COUNT(*) AS gold_orders, SUM(amount_inr) AS revenue_inr,
       SUM(loyalty_points) AS points FROM gold.fct_orders;
```

## SQL source files

`sql/00_setup.sql` through `sql/40_gold.sql` are extracted from the instructor notebook's
SQL cells. The baseline `10_orders_clean.sql` intentionally does not reject EUR, so the
first run preserves the original two reasons for `ORD-1006`. The separate
`sql/experiments/10_orders_clean_unsupported_currency.sql` is the B2 variant; it adds
`unsupported_currency` inside `ARRAY_CONSTRUCT_COMPACT` without changing the base notebook.

## Experiment notes

- **B1 replay:** Bronze is append-only. Re-running extracts another eight rows. The Silver
  dedup query chooses the latest row per order, and the Gold `MERGE` compares `row_hash`.
- **B2 currency:** `ORD-1006` should gain an `unsupported_currency` reason in the checked
  Silver table. Quarantine idempotency is keyed by source, order ID and source `updated_at`;
  an unchanged bad source version is not inserted again.
- **B3 SCD2:** the Arjun event is a legitimate historical CRM change, not a code fault.
  Predictions are recorded in `../docs/predictions.md` before running it.
- **B4 future date:** the notebook's sixth quality check counts future-dated deduplicated
  orders. Remove the mock raw row and its Gold row after the demonstration because Gold's
  `MERGE` is an upsert and does not delete rows absent from the source.

See `../docs/STAGE_GUIDE.md` and `../docs/assignment_report.md` for exact commands,
queries, report answers, and evidence items.
