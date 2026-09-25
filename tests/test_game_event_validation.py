import copy

import pytest

from sims_companion_bridge.validation import ValidationError, validate_game_event


def test_valid_game_snapshot_event_is_strictly_normalized(game_event_factory):
    event = game_event_factory()
    assert validate_game_event(event) == event
    for field, value in (("type", "other.snapshot"), ("source", "browser"),
                         ("provenance", "claimed")):
        malformed = copy.deepcopy(event)
        malformed[field] = value
        with pytest.raises(ValidationError):
            validate_game_event(malformed)


def test_game_event_rejects_unknown_fields_and_malformed_ids(game_event_factory):
    event = game_event_factory()
    event["unexpected"] = True
    with pytest.raises(ValidationError, match="fields"):
        validate_game_event(event)
    event = game_event_factory(event_id="contains spaces")
    with pytest.raises(ValidationError, match="event_id"):
        validate_game_event(event)
    event = game_event_factory()
    event["payload"]["zone"]["unexpected"] = "data"
    with pytest.raises(ValidationError, match="snapshot zone"):
        validate_game_event(event)


@pytest.mark.parametrize("number", [float("nan"), float("inf"), float("-inf")])
def test_game_event_rejects_non_finite_numbers(game_event_factory, number):
    event = game_event_factory()
    event["payload"]["player"]["needs"]["hunger"] = number
    with pytest.raises(ValidationError, match="finite"):
        validate_game_event(event)


def test_game_event_rejects_excessive_depth_before_field_parsing(game_event_factory):
    event = game_event_factory()
    nested = []
    cursor = nested
    for _ in range(10):
        child = []
        cursor.append(child)
        cursor = child
    event["unexpected"] = nested
    with pytest.raises(ValidationError, match="nesting"):
        validate_game_event(event)


def test_game_event_rejects_oversized_utf8_payload(game_event_factory):
    event = game_event_factory()
    event["payload"]["present_sims"] = [
        {"sim_id": "sim-{}".format(index), "name": "\U0001f642" * 128}
        for index in range(40)
    ]
    with pytest.raises(ValidationError, match="payload exceeds"):
        validate_game_event(event)
