# Part C — Mage Iris pipeline

This is the instructor notebook's Iris classifier, completed as a Mage project. It uses
scikit-learn's Iris dataset and a deterministic `train_test_split(test_size=0.2,
random_state=42)` split. The graph is:

```text
load_iris -> validate_input -> prepare_data -> train_model
                                                |-> save_results
                                                `-> evaluate_model
```

`validate_input` is the additional C2 gate. Its attached `@test` rejects missing values
and requires exactly three target classes. `prepare_data` has the mandatory 120/30 split
assertions. `train_model` reads `max_depth` from Mage runtime variables and has the
instructor's 80% minimum accuracy test.

## Install and run

From the repository root:

```bash
python -m pip install -r requirements-mage.txt
mage run iris_project iris_classifier --test
```

C1 — test all five depths (Linux/macOS shell):

```bash
for depth in 1 2 3 4 5; do
  rm -f iris_predictions.csv
  echo "=== max_depth=$depth ==="
  mage run iris_project iris_classifier --test --runtime-vars "{"max_depth": $depth}"
  test -f iris_predictions.csv && echo "CSV_CREATED=true" || echo "CSV_CREATED=false"
done
```

PowerShell equivalent:

```powershell
1..5 | ForEach-Object {
  Remove-Item iris_predictions.csv -ErrorAction SilentlyContinue
  mage run iris_project iris_classifier --test --runtime-vars "{`"max_depth`": $_}"
  if (Test-Path iris_predictions.csv) { 'CSV_CREATED=true' } else { 'CSV_CREATED=false' }
}
```

Do not assume `max_depth=1` fails. Capture each printed accuracy, the pipeline test result,
and whether the output file exists. The repository does not contain fabricated Mage run
results.

C2 controlled fault cases:

```bash
mage run iris_project iris_classifier --test --runtime-vars '{"inject_missing": true}'
mage run iris_project iris_classifier --test --runtime-vars '{"drop_target_class": true}'
```

Both switches default to `false`; use one at a time, capture the failing `validate_input`
`@test`, then run the normal pipeline again to restore the passing case.

Run the UI with `mage start iris_project`, open `http://localhost:6789`, and capture the
pipeline graph. `train_model` has two downstream edges, to `save_results` and
`evaluate_model`. `evaluate_model` prints a confusion matrix and accuracy / macro precision /
macro recall / macro F1 metrics.

**Artifact gate decision:** `train_model` deliberately does not call `joblib.dump`. In the
instructor notebook that write happened inside the transformer, before Mage runs its
attached `@test`; a failing model could therefore leave a `.pkl` artifact behind. This
implementation writes `iris_predictions.csv` only in the downstream exporter, which is
blocked until the accuracy test passes. No untested model artifact is persisted.
