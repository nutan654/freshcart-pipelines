# Evidence checklist

Do not mark an item complete until the screenshot, terminal output, exported notebook output,
or GitHub run exists. Store original captures under `evidence/` (the folder is intentionally
not pre-filled). Redact account identifiers, emails, tokens and other credentials before
sharing the repository.

## Local validation

- [x] Offline compile check and 14 passing pytest tests (`local_validation.txt`; Python 3.13.5).
- [ ] Python 3.12 GitHub Actions baseline run.

## Part A — Git / CI

- [ ] GitHub repository URL and `git log --oneline` showing at least five meaningful commits.
- [ ] Green baseline GitHub Actions run.
- [x] A1 local fault reproduction: `test_size=0.3` produced 105/45 and failed the 120-row assertion (`../evidence/a1_local_fault_reproduction.txt`).
- [ ] A1 breaking commit where `test_size` changes from `0.2` to `0.3`.
- [ ] Genuine red GitHub Actions run showing the 120/30 assertions failing.
- [ ] Subsequent fixing commit restoring `0.2`.
- [ ] Genuine green GitHub Actions run after the fix.

## Part B — Snowflake

- [ ] Baseline run: Bronze 8, Silver clean 6, quarantine 2, dedup 4, Gold 4.
- [ ] Baseline Gold revenue ₹7,785.00, points 126, rejection share 25%.
- [ ] B1: web/mobile field normalization for ORD-1002 and ORD-1003.
- [ ] B1: `QUALIFY ROW_NUMBER()` survivor, and before/after replay counts proving Bronze append + Gold unchanged.
- [ ] B2: ORD-1006 reasons before / after adding unsupported_currency; quarantine count comparison.
- [ ] B3: SCD2 CUST-02 history before / after; prediction versus actual table; changed `published_at`.
- [ ] B4: future test order, sixth check PROBLEM, then cleanup and PASS.

## Part C — Mage

- [ ] Baseline pipeline execution with `--test`.
- [ ] C1 table for `max_depth=1,2,3,4,5`: accuracy, accuracy-gate pass/fail, CSV created yes/no.
- [ ] Delete `iris_predictions.csv` before every C1 run; capture terminal outputs.
- [ ] C2 passing validation run.
- [ ] C2 failing run with `inject_missing=true` or `drop_target_class=true`.
- [ ] Passing rerun after restoring the input.
- [ ] Pipeline `metadata.yaml` screenshot showing `train_model` has two downstream blocks.
- [ ] Confusion matrix and metrics table output.
- [ ] Mage UI pipeline graph screenshot.

## Part D — RabbitMQ

- [ ] Six D1 routing examples: predicted queues versus actual live driver consoles.
- [ ] Dispatcher + at least three drivers running for two minutes.
- [ ] D1 malformed event console output: valid ACK and malformed NACK/discard.
- [ ] D2 original delivery before ACK and abrupt consumer termination.
- [ ] D2 restarted consumer prints `REDELIVERED` and final ACK.

## Bonus

- [ ] Publisher and consumer logs for a one-minute batch.
- [ ] Snowflake landing and Bronze rows for the streamed batch.
- [ ] Two replays with Gold count/revenue/points unchanged.

## Report appendix

- [ ] Diagram screenshot or rendered Mermaid diagram.
- [ ] Half-page reflection based on one failure you personally executed and diagnosed.
