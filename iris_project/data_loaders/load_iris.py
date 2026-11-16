"""Load the instructor-provided scikit-learn Iris dataset.

The two optional runtime variables are fault-injection switches for C2. They are
false by default and do not alter the normal 150-row, three-class input.
"""
from sklearn.datasets import load_iris

try:
    from mage_ai.data_preparation.decorators import data_loader, test
except ImportError:  # Keep the function importable in lightweight local CI.
    def data_loader(fn):
        return fn
    def test(fn):
        return fn


@data_loader
def load_data(*args, **kwargs):
    iris = load_iris(as_frame=True)
    df = iris.frame.copy()

    # Controlled C2 fault injection. Leave these off for the baseline run.
    if kwargs.get("inject_missing", False):
        df.loc[df.index[0], "sepal length (cm)"] = float("nan")
    if kwargs.get("drop_target_class", False):
        df.loc[df["target"] == 2, "target"] = 1

    print("Rows loaded:", len(df), "| target classes:", sorted(df["target"].dropna().unique().tolist()))
    return df


@test
def test_output(output, *args):
    assert len(output) == 150, "Iris must have 150 rows"
