# FAULTS.md — Break It Till It Holds

**Rule:** Observed-result cells stay `Pending` until the corresponding experiment has been
executed. The values in `docs/predictions.md` are predictions, not observations. A code path
or passing unit test is not evidence of a live Snowflake, Mage, GitHub Actions or RabbitMQ run.

| ID | Component | Injected fault / experiment | Expected detector | Observed result | Recovery | Evidence |
|---|---|---|---|---|---|---|
| A1 | Git / CI | Change `test_size` from `0.2` to `0.3` | `pytest` in GitHub Actions; 120/30 assertions | Local reproduction failed as expected: 105 train / 45 test; remote Actions result pending | Restored `0.2`; local suite passes; push the fixing commit | `evidence/a1_local_fault_reproduction.txt`; GitHub red/green runs and commit hashes pending |
| B1 | Snowflake | Replay the same web/mobile batch | Silver `QUALIFY ROW_NUMBER()` and Gold `row_hash` + `MERGE` | Pending | No data fix if counts/totals hold; retain idempotent SQL | Pending: before/after Bronze, Silver, Gold queries |
| B2 | Snowflake | Add unsupported-currency validation for EUR / ORD-1006 | `ARRAY_CONSTRUCT_COMPACT`, Silver clean/quarantine rules | Pending | Correct the currency or retain in quarantine | Pending: reasons before/after and quarantine count |
| B3 | Snowflake | Add CUST-02 Gold event effective 2026-08-15 (legitimate data change, not a fault) | SCD2 intervals and point-in-time Gold join | Pending | Preserve event history; remove test event after capture if restoring baseline | Pending: pre-run predictions and before/after SCD2/Gold output |
| B4 | Snowflake | Insert a future-dated mock order | Sixth `quality_checks()` future-date check | Pending | Delete raw fixture, rebuild Silver, remove mock Gold row | Pending: PROBLEM output, offending order, corrected data, PASS output |
| C1 | Mage | Run `max_depth` 1–5; report only any model-quality failure actually observed | `train_model.test_accuracy` `@test` gate | Pending | Use a passing configuration; do not save an unapproved output | Pending: five-row accuracy / gate / CSV table |
| C2 | Mage | Inject missing value or remove target class | `validate_input.test_input_quality` `@test` | Pending | Restore default runtime variables / valid Iris input | Pending: passing run, failing assertion, restored run |
| D1 | RabbitMQ | Omit `zone` from every Nth event | `basic_nack(requeue=False)` | Pending | Discard malformed event; correct producer schema | Pending: actual driver console showing ACK and NACK |
| D2 | RabbitMQ | Terminate consumer before ACK | Broker redelivery on durable queue | Pending | Restart same queue consumer and ACK redelivery | Pending: first delivery, crash, `REDELIVERED`, final ACK |
| BONUS | Integrated | Replay same streamed order batch | Silver dedup + Gold `row_hash` / `MERGE` | Pending | Safe replay; preserve stable order IDs and hashes | Pending: message logs, Bronze growth, Gold totals before/after |

## Technical record notes

- **A1:** the local fault reproduction proves the assertion detects the altered split; it does not replace the required GitHub Actions red/green runs.
- **B1:** expected first-run counts are Bronze 8, Silver clean 6, quarantine 2, dedup 4 and
  Gold 4. A replay appends Bronze raw rows but should not duplicate Gold.
- **B2:** baseline ORD-1006 reasons are expected to be `bad_email` and `bad_pincode`; the
  experiment adds `unsupported_currency`. The quarantine `NOT EXISTS` key is source,
  null-safe order ID and source update timestamp, so the same bad source version is not
  inserted twice. Existing quarantine reason arrays are not automatically updated.
- **B3:** Arjun's tier event is a historical data-change test. It must not be described as a
  malformed input or software defect.
- **C1:** do not assume depth 1 fails; record what Mage's own `@test` actually reports.
- **D2:** do not claim at-least-once redelivery until `REDELIVERED` appears in the restarted
  driver's output. A durable queue plus a persistent message is configured for the demo.
