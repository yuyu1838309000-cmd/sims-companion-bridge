import copy
import sqlite3

import pytest

from sims_companion_bridge.store import EventConflictError, WorldStore
from sims_companion_bridge.validation import validate_game_event


def test_existing_database_migrates_without_deletion(tmp_path):
    database = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(str(database))
    connection.executescript("""
        CREATE TABLE worlds (
          world_id TEXT NOT NULL, branch_id TEXT NOT NULL, save_slot_id TEXT,
          fingerprint TEXT, status TEXT NOT NULL, zone TEXT NOT NULL,
          player_state TEXT NOT NULL, companion_state TEXT NOT NULL,
          PRIMARY KEY (world_id, branch_id)
        );
        CREATE TABLE game_events (
          event_id TEXT PRIMARY KEY, world_id TEXT NOT NULL, branch_id TEXT NOT NULL,
          type TEXT NOT NULL, source TEXT NOT NULL, provenance TEXT NOT NULL,
          wallclock TEXT NOT NULL, sim_time TEXT, payload TEXT NOT NULL
        );
        INSERT INTO worlds VALUES
          ('legacy-world', 'main', 'slot-old', 'old', 'offline', 'Old Lot', 'Home', 'Ready');
    """)
    connection.commit()
    connection.close()

    store = WorldStore(database)
    assert store.get_world("legacy-world", "main")["current_snapshot"] is None
    world_columns = {row[1] for row in store._connection.execute("PRAGMA table_info(worlds)")}
    event_columns = {row[1] for row in store._connection.execute("PRAGMA table_info(game_events)")}
    assert {"current_snapshot", "current_event_id"}.issubset(world_columns)
    assert "canonical_event" in event_columns
    store.close()


def test_ingestion_atomically_updates_world_and_persists_immutable_event(tmp_path, game_event_factory):
    store = WorldStore(tmp_path / "atomic.sqlite3")
    event = validate_game_event(game_event_factory())
    result = store.ingest_snapshot_event(event)
    event["payload"]["zone"]["name"] = "Mutated after insert"

    world = store.get_world("demo-world", "main")
    assert result == {"event_id": "evt-fixture", "duplicate": False}
    assert world["status"] == "online"
    assert world["zone"] == "Fixture Lot"
    assert world["current_event_id"] == "evt-fixture"
    assert world["current_snapshot"]["zone"]["name"] == "Fixture Lot"
    events = store.recent_events("demo-world", "main")
    assert len(events) == 1
    assert events[0]["event_id"] == "evt-fixture"
    assert events[0]["payload"]["zone"]["name"] == "Fixture Lot"
    assert "canonical_event" not in events[0]
    store.close()


def test_failed_event_insert_rolls_back_world_update(tmp_path, game_event_factory):
    store = WorldStore(tmp_path / "rollback.sqlite3")
    store.seed_demo()
    store._connection.execute("""
        CREATE TRIGGER reject_fixture_event BEFORE INSERT ON game_events
        WHEN NEW.event_id = 'evt-fixture'
        BEGIN SELECT RAISE(ABORT, 'fixture failure'); END
    """)
    with pytest.raises(sqlite3.IntegrityError, match="fixture failure"):
        store.ingest_snapshot_event(validate_game_event(game_event_factory()))
    world = store.get_world()
    assert world["status"] == "offline"
    assert world["current_snapshot"] is None
    assert all(item["event_id"] != "evt-fixture" for item in store.recent_events())
    store.close()


def test_duplicate_is_idempotent_but_conflicting_duplicate_is_rejected(tmp_path, game_event_factory):
    store = WorldStore(tmp_path / "duplicate.sqlite3")
    event = validate_game_event(game_event_factory())
    assert store.ingest_snapshot_event(event)["duplicate"] is False
    assert store.ingest_snapshot_event(copy.deepcopy(event))["duplicate"] is True
    assert store.counts()["game_events"] == 1

    conflict = copy.deepcopy(event)
    conflict["payload"]["zone"]["name"] = "Different Lot"
    with pytest.raises(EventConflictError, match="different content"):
        store.ingest_snapshot_event(conflict)
    assert store.get_world()["zone"] == "Fixture Lot"
    assert store.counts()["game_events"] == 1
    store.close()


def test_preferred_world_tracks_latest_observed_branch(tmp_path, game_event_factory):
    store = WorldStore(tmp_path / "preferred.sqlite3")
    store.seed_demo()
    store.ingest_snapshot_event(validate_game_event(game_event_factory(
        event_id="evt-first", world_id="world-first", branch_id="main"
    )))
    store.ingest_snapshot_event(validate_game_event(game_event_factory(
        event_id="evt-second", world_id="world-second", branch_id="branch-2"
    )))
    preferred = store.preferred_world()
    assert (preferred["world_id"], preferred["branch_id"]) == ("world-second", "branch-2")
    assert preferred["current_event_id"] == "evt-second"
    store.close()


def test_world_and_branch_snapshots_are_isolated(tmp_path, game_event_factory):
    store = WorldStore(tmp_path / "isolation.sqlite3")
    first = validate_game_event(game_event_factory(
        event_id="evt-a", world_id="world-a", branch_id="main", zone_name="Main Lot"
    ))
    second = validate_game_event(game_event_factory(
        event_id="evt-b", world_id="world-a", branch_id="alternate", zone_name="Other Lot"
    ))
    store.ingest_snapshot_event(first)
    store.ingest_snapshot_event(second)
    assert store.get_world("world-a", "main")["zone"] == "Main Lot"
    assert store.get_world("world-a", "alternate")["zone"] == "Other Lot"
    assert [item["event_id"] for item in store.recent_events("world-a", "main")] == ["evt-a"]
    assert [item["event_id"] for item in store.recent_events("world-a", "alternate")] == ["evt-b"]
    store.close()
