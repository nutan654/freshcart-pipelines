"""Train the instructor's decision tree and return predictions for the test rows.

Do not persist an artifact here: Mage runs the @test gate only after this function
returns. Saving here would allow a failing model to leave a persisted artifact.
The downstream save_results block is the only prediction-output writer.
"""
from sklearn.tree import DecisionTreeClassifier

try:
    from mage_ai.data_preparation.decorators import transformer, test
except ImportError:
    def transformer(fn):
        return fn
    def test(fn):
        return fn

FEATURES = [
    "sepal length (cm)",
    "sepal width (cm)",
    "petal length (cm)",
    "petal width (cm)",
]


@transformer
def train(df, *args, **kwargs):
    max_depth = int(kwargs.get("max_depth", 3))
    if max_depth < 1:
        raise ValueError("max_depth must be >= 1")

    train_df = df[df["split"] == "train"]
    test_df = df[df["split"] == "test"].copy()
    model = DecisionTreeClassifier(max_depth=max_depth, random_state=42)
    model.fit(train_df[FEATURES], train_df["target"])
    test_df["predicted"] = model.predict(test_df[FEATURES])
    accuracy = (test_df["predicted"] == test_df["target"]).mean()
    print("max_depth =", max_depth, "| Test accuracy =", round(float(accuracy), 3))
    return test_df


@test
def test_accuracy(output, *args):
    accuracy = (output["predicted"] == output["target"]).mean()
    assert accuracy >= 0.8, "Model accuracy is below 80%"
