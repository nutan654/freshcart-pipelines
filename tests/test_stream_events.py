import json

import pytest

from stream.dispatcher import make_event
from stream.driver import decode_event


def test_dispatcher_fault_message_omits_zone_only_on_configured_sequence():
    _, good = make_event(seq=9, bad_every=10, key="bangalore.koramangala.ride")
    _, bad = make_event(seq=10, bad_every=10, key="bangalore.koramangala.ride")
    assert "zone" in good
    assert "zone" not in bad


def test_decode_event_accepts_valid_message():
    event = {"id": "1", "city": "bangalore", "zone": "koramangala", "type": "ride", "ts": "now"}
    assert decode_event(json.dumps(event).encode()) == event


def test_decode_event_rejects_missing_zone():
    event = {"id": "1", "city": "bangalore", "type": "ride", "ts": "now"}
    with pytest.raises(ValueError, match="zone"):
        decode_event(json.dumps(event).encode())
