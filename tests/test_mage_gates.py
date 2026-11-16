"""Unit checks for Mage block contracts without requiring a Mage server."""

import pytest
from sklearn.datasets import load_iris

from iris_project.data_loaders.load_iris import load_data
from iris_project.transformers.prepare_data import transform
from iris_project.transformers.train_model import test_accuracy as mage_test_accuracy, train
from iris_project.transformers.validate_input import test_input_quality as mage_test_input_quality, validate_input


def test_original_iris_input_passes_validation():
    df = load_data()
    validated = validate_input(df)
    mage_test_input_quality(validated)
    assert len(validated) == 150


@pytest.mark.parametrize(
    ("runtime_fault", "message"),
    [
        ({"inject_missing": True}, "missing values"),
        ({"drop_target_class": True}, "exactly three target classes"),
    ],
)
def test_invalid_input_is_stopped_by_validation_gate(runtime_fault, message):
    bad_df = load_data(**runtime_fault)
    with pytest.raises(AssertionError, match=message):
        mage_test_input_quality(validate_input(bad_df))


def test_model_quality_gate_rejects_depth_one_and_accepts_depth_two():
    split = transform(load_iris(as_frame=True).frame)

    depth_one_predictions = train(split, max_depth=1)
    with pytest.raises(AssertionError, match="below 80%"):
        mage_test_accuracy(depth_one_predictions)

    depth_two_predictions = train(split, max_depth=2)
    mage_test_accuracy(depth_two_predictions)
