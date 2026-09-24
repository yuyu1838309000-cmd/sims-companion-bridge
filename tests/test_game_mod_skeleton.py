import importlib.util
from pathlib import Path


def load_bridge_class():
    path = Path(__file__).resolve().parents[1] / "game-mod" / "src" / "sims_companion_bridge" / "bridge.py"
    spec = importlib.util.spec_from_file_location("game_bridge", str(path))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.ReadOnlyBridge


def test_read_only_bridge_bounds_queue_and_drains_json():
    bridge = load_bridge_class()("world")
    event = bridge.publish_snapshot("Demo Zone", "home", "available")
    assert event["type"] == "game.snapshot"
    assert len(bridge.drain_json()) == 1
    assert bridge.drain_json() == []



def test_read_only_bridge_rejects_non_protocol_identifiers():
    bridge_class = load_bridge_class()
    for invalid in ("world with spaces", "", "x" * 65):
        try:
            bridge_class(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid world_id was accepted: %r" % invalid)
