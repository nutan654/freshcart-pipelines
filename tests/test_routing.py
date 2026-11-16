import pytest

from stream.routing import receivers


CASES = [
    ("bangalore.koramangala.food", {"Ravi", "Meena", "Control"}),
    ("bangalore.indiranagar.ride", {"Priya", "Arjun", "Control"}),
    ("bangalore.whitefield.ride", {"Arjun", "Control"}),
    ("chennai.tnagar.food", {"Karthik"}),
    ("chennai.whitefield.ride", set()),
    ("bangalore.koramangala", {"Control"}),
]


@pytest.mark.parametrize("routing_key,expected", CASES)
def test_six_instructor_topic_routing_examples(routing_key, expected):
    assert set(receivers(routing_key)) == expected
