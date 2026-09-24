import json
from dataclasses import asdict
from pathlib import Path

from sims_companion_sdk import BackendCapabilities, TurnRequest, TurnResponse


ROOT = Path(__file__).resolve().parents[1]


def test_protocol_schemas_are_strict_and_versioned():
    for name in ("turn-request.schema.json", "turn-response.schema.json", "capabilities.schema.json"):
        schema = json.loads((ROOT / "protocol" / "v0.1" / name).read_text(encoding="utf-8"))
        assert schema["$schema"].endswith("2020-12/schema")
        assert schema["additionalProperties"] is False


def test_sdk_contract_matches_read_only_protocol():
    capabilities = BackendCapabilities()
    request = TurnRequest("request", "conversation", "world", "main", "hello")
    response = TurnResponse("request", "conversation", "hello")
    assert capabilities.game_actions is False
    assert capabilities.cross_surface_recall is False
    assert request.surface == "sims"
    assert set(asdict(response)) == {"request_id", "conversation_id", "text", "intents", "protocol_version"}


def test_turn_request_preserves_existing_positional_argument_order():
    request = TurnRequest(
        "r", "c", "w", "b", "hello", ["evt"], "0.1", "sims",
        "proactive", {"zone": "demo"},
    )
    assert request.input_event_ids == ["evt"]
    assert request.protocol_version == "0.1"
    assert request.surface == "sims"
    assert request.turn_source == "proactive"
    assert request.world == {"zone": "demo"}
    assert request.history == []


def test_turn_request_schema_documents_history():
    schema = json.loads(
        (ROOT / "protocol" / "v0.1" / "turn-request.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert "history" in schema["properties"]
    assert schema["properties"]["history"]["type"] == "array"
