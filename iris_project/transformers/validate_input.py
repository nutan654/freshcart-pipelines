"""Validate source data before the train/test split."""
try:
    from mage_ai.data_preparation.decorators import transformer, test
except ImportError:  # Lightweight CI can import and unit-test block code without Mage.
    def transformer(fn):
        return fn
    def test(fn):
        return fn


@transformer
def validate_input(df, *args, **kwargs):
    return df.copy()


@test
def test_input_quality(output, *args):
    assert not output.isna().any().any(), "Input contains missing values"
    assert output["target"].nunique() == 3, "Iris input must contain exactly three target classes"
