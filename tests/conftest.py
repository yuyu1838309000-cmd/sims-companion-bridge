import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "gateway" / "src"))
sys.path.insert(0, str(ROOT / "sdk" / "python"))


@pytest.fixture
def game_event_factory():
    def make(event_id="evt-fixture", world_id="demo-world", branch_id="main",
             zone_name="Fixture Lot"):
        empty_needs = {key: None for key in
                       ("hunger", "energy", "fun", "social", "hygiene", "bladder")}
        return {
            "protocol_version": "0.1",
            "event_id": event_id,
            "world_id": world_id,
            "branch_id": branch_id,
            "type": "game.snapshot",
            "source": "game_mod",
            "provenance": "observed",
            "wallclock_unix": 1700000000.25,
            "sim_time": "Day 2, 14:30",
            "payload": {
                "snapshot_version": "0.1",
                "save_slot_id": "slot-7",
                "zone": {"zone_id": "zone-42", "name": zone_name},
                "simulation": {"sim_time": "Day 2, 14:30", "in_build_buy": False},
                "player": {
                    "sim_id": "sim-player", "name": "Player Sim",
                    "mood": {"name": "Focused", "intensity": 2},
                    "needs": dict(empty_needs, hunger=72.5),
                    "interactions": {"running": ["Read Book"], "queued": []},
                },
                "companion": None,
                "present_sims": [{"sim_id": "sim-player", "name": "Player Sim"}],
            },
        }
    return make
