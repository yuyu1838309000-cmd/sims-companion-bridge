import json
from pathlib import Path
from sims_companion_sdk import BackendCapabilities, TurnRequest

ROOT=Path(__file__).resolve().parents[1]
def test_schemas_parse_and_are_strict():
    for path in (ROOT/"protocol"/"v0.1").glob("*.schema.json"):
        assert json.loads(path.read_text(encoding="utf-8"))["additionalProperties"] is False
def test_sdk_defaults_read_only():
    assert BackendCapabilities().game_actions is False
    assert BackendCapabilities().cross_surface_recall is False
    assert TurnRequest("r","c","w","b","hello").surface=="sims"
