"""Second downstream branch: confusion matrix and macro-averaged metrics."""
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

try:
    from mage_ai.data_preparation.decorators import transformer
except ImportError:
    def transformer(fn):
        return fn


@transformer
def evaluate(df, *args, **kwargs):
    y_true = df["target"]
    y_pred = df["predicted"]
    confusion = pd.crosstab(y_true, y_pred, rownames=["actual"], colnames=["predicted"])
    print("Confusion matrix:")
    print(confusion)

    metrics = pd.DataFrame({
        "metric": ["accuracy", "precision_macro", "recall_macro", "f1_macro"],
        "value": [
            round(accuracy_score(y_true, y_pred), 3),
            round(precision_score(y_true, y_pred, average="macro", zero_division=0), 3),
            round(recall_score(y_true, y_pred, average="macro", zero_division=0), 3),
            round(f1_score(y_true, y_pred, average="macro", zero_division=0), 3),
        ],
    })
    print("Metrics:")
    print(metrics.to_string(index=False))
    return metrics
