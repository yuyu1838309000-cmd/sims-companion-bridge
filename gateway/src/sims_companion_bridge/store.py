"""SQLite-backed source of truth for demo world state and events."""

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path


def utc_now():
    return datetime.now(timezone.utc).isoformat()


SCHEMA = """
CREATE TABLE IF NOT EXISTS worlds (
  world_id TEXT NOT NULL, branch_id TEXT NOT NULL, save_slot_id TEXT,
  fingerprint TEXT, status TEXT NOT NULL, zone TEXT NOT NULL,
  player_state TEXT NOT NULL, companion_state TEXT NOT NULL,
  current_snapshot TEXT, current_event_id TEXT,
  PRIMARY KEY (world_id, branch_id)
);
CREATE TABLE IF NOT EXISTS game_conversations (
  conversation_id TEXT PRIMARY KEY, world_id TEXT NOT NULL,
  branch_id TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS game_events (
  event_id TEXT PRIMARY KEY, world_id TEXT NOT NULL, branch_id TEXT NOT NULL,
  type TEXT NOT NULL, source TEXT NOT NULL, provenance TEXT NOT NULL,
  wallclock TEXT NOT NULL, sim_time TEXT, payload TEXT NOT NULL,
  canonical_event TEXT
);
CREATE TABLE IF NOT EXISTS turns (
  turn_id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL,
  turn_source TEXT NOT NULL, surface TEXT NOT NULL,
  input_event_ids TEXT NOT NULL, output_message_id TEXT NOT NULL,
  user_text TEXT NOT NULL, assistant_text TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS world_memories (
  memory_id TEXT PRIMARY KEY, world_id TEXT NOT NULL, branch_id TEXT NOT NULL,
  epistemic_status TEXT NOT NULL, evidence_refs TEXT NOT NULL, content TEXT NOT NULL
);
"""


class EventConflictError(ValueError):
    """An immutable event ID was reused for different content."""


class WorldStore:
    def __init__(self, path):
        self.path = str(Path(path))
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        with self._connection:
            self._connection.executescript(SCHEMA)
            self._migrate_schema()

    def _migrate_schema(self):
        """Apply additive migrations required by databases created before ingestion."""
        world_columns = {row["name"] for row in self._connection.execute("PRAGMA table_info(worlds)")}
        if "current_snapshot" not in world_columns:
            self._connection.execute("ALTER TABLE worlds ADD COLUMN current_snapshot TEXT")
        if "current_event_id" not in world_columns:
            self._connection.execute("ALTER TABLE worlds ADD COLUMN current_event_id TEXT")
        event_columns = {row["name"] for row in self._connection.execute("PRAGMA table_info(game_events)")}
        if "canonical_event" not in event_columns:
            self._connection.execute("ALTER TABLE game_events ADD COLUMN canonical_event TEXT")

    def close(self):
        self._connection.close()

    def seed_demo(self):
        with self._lock, self._connection:
            exists = self._connection.execute(
                "SELECT 1 FROM worlds WHERE world_id=? AND branch_id=?", ("demo-world", "main")
            ).fetchone()
            if exists:
                return
            self._connection.execute(
                """INSERT INTO worlds
                   (world_id, branch_id, save_slot_id, fingerprint, status, zone,
                    player_state, companion_state, current_snapshot, current_event_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("demo-world", "main", "demo-slot", "synthetic-demo", "offline",
                 "Demo Neighborhood / Garden Lot", "At home", "Ready to chat", None, None),
            )
            self.add_event("demo-world", "main", "world.loaded", "mock_game",
                           "demo_seed", {"zone": "Demo Neighborhood / Garden Lot"}, "Day 1, 09:00")
            self.add_event("demo-world", "main", "sim.mood_observed", "mock_game",
                           "demo_seed", {"subject": "player", "mood": "focused"}, "Day 1, 09:05")

    @staticmethod
    def _decode_world(row):
        if not row:
            return None
        world = dict(row)
        world["current_snapshot"] = (
            json.loads(world["current_snapshot"]) if world["current_snapshot"] else None
        )
        return world

    def get_world(self, world_id="demo-world", branch_id="main"):
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM worlds WHERE world_id=? AND branch_id=?", (world_id, branch_id)
            ).fetchone()
        return self._decode_world(row)

    def preferred_world(self):
        """Return the most recently observed game branch, falling back to demo."""
        with self._lock:
            row = self._connection.execute(
                """SELECT worlds.* FROM worlds
                   JOIN game_events ON game_events.event_id = worlds.current_event_id
                   WHERE worlds.current_snapshot IS NOT NULL
                   ORDER BY game_events.rowid DESC LIMIT 1"""
            ).fetchone()
            if row is None:
                row = self._connection.execute(
                    "SELECT * FROM worlds WHERE world_id=? AND branch_id=?",
                    ("demo-world", "main"),
                ).fetchone()
        return self._decode_world(row)

    def add_event(self, world_id, branch_id, event_type, source, provenance, payload, sim_time=None):
        event_id = "evt-" + uuid.uuid4().hex
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO game_events
                   (event_id, world_id, branch_id, type, source, provenance,
                    wallclock, sim_time, payload, canonical_event)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_id, world_id, branch_id, event_type, source, provenance,
                 utc_now(), sim_time, json.dumps(payload, separators=(",", ":"), ensure_ascii=True),
                 None),
            )
        return event_id

    @staticmethod
    def _canonical_json(value):
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)

    @staticmethod
    def _sim_display(sim, missing):
        if sim is None:
            return missing
        name = sim.get("name") or "Unnamed Sim"
        mood = (sim.get("mood") or {}).get("name")
        return "{} ({})".format(name, mood) if mood else name

    def ingest_snapshot_event(self, event):
        """Atomically persist an immutable event and its branch's current snapshot."""
        canonical = self._canonical_json(event)
        payload = event["payload"]
        payload_json = self._canonical_json(payload)
        event_id = event["event_id"]
        zone = payload["zone"].get("name") or payload["zone"].get("zone_id") or "Unknown zone"
        player_state = self._sim_display(payload.get("player"), "No active player Sim")
        companion_state = self._sim_display(payload.get("companion"), "No bound companion Sim")
        wallclock = datetime.fromtimestamp(event["wallclock_unix"], timezone.utc).isoformat()
        with self._lock, self._connection:
            existing = self._connection.execute(
                "SELECT canonical_event FROM game_events WHERE event_id=?", (event_id,)
            ).fetchone()
            if existing:
                if existing["canonical_event"] == canonical:
                    return {"event_id": event_id, "duplicate": True}
                raise EventConflictError("event_id is already bound to different content")
            self._connection.execute(
                """INSERT INTO worlds
                   (world_id, branch_id, save_slot_id, fingerprint, status, zone,
                    player_state, companion_state, current_snapshot, current_event_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(world_id, branch_id) DO UPDATE SET
                     save_slot_id=excluded.save_slot_id,
                     fingerprint=excluded.fingerprint,
                     status=excluded.status,
                     zone=excluded.zone,
                     player_state=excluded.player_state,
                     companion_state=excluded.companion_state,
                     current_snapshot=excluded.current_snapshot,
                     current_event_id=excluded.current_event_id""",
                (event["world_id"], event["branch_id"], payload.get("save_slot_id"),
                 "observed:" + event_id, "online", zone, player_state, companion_state,
                 payload_json, event_id),
            )
            self._connection.execute(
                """INSERT INTO game_events
                   (event_id, world_id, branch_id, type, source, provenance,
                    wallclock, sim_time, payload, canonical_event)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_id, event["world_id"], event["branch_id"], event["type"],
                 event["source"], event["provenance"], wallclock, event["sim_time"],
                 payload_json, canonical),
            )
        return {"event_id": event_id, "duplicate": False}

    def recent_events(self, world_id="demo-world", branch_id="main", limit=50):
        with self._lock:
            rows = self._connection.execute(
                """SELECT * FROM game_events WHERE world_id=? AND branch_id=?
                   ORDER BY rowid DESC LIMIT ?""",
                (world_id, branch_id, min(max(int(limit), 1), 100)),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item.pop("canonical_event", None)
            item["payload"] = json.loads(item["payload"])
            result.append(item)
        return result

    def ensure_conversation(self, conversation_id, world_id, branch_id):
        with self._lock, self._connection:
            existing = self._connection.execute(
                "SELECT world_id, branch_id FROM game_conversations WHERE conversation_id=?",
                (conversation_id,),
            ).fetchone()
            if existing:
                if existing["world_id"] != world_id or existing["branch_id"] != branch_id:
                    raise ValueError("conversation_id is already bound to a different world branch")
                return
            self._connection.execute(
                "INSERT INTO game_conversations VALUES (?, ?, ?, ?)",
                (conversation_id, world_id, branch_id, utc_now()),
            )

    def add_turn(self, conversation_id, turn_source, user_text, assistant_text, input_event_ids):
        turn_id = "turn-" + uuid.uuid4().hex
        message_id = "msg-" + uuid.uuid4().hex
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO turns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (turn_id, conversation_id, turn_source, "sims", json.dumps(input_event_ids),
                 message_id, user_text, assistant_text, utc_now()),
            )
        return turn_id, message_id

    def turns(self, conversation_id, limit=100):
        rows = self._connection.execute(
            "SELECT * FROM turns WHERE conversation_id=? ORDER BY created_at ASC, rowid ASC LIMIT ?",
            (conversation_id, min(max(int(limit), 1), 200)),
        ).fetchall()
        return self._decode_turn_rows(rows)

    def all_turns(self, conversation_id):
        """Return the complete persisted Game Conversation in stable order.

        Public Core intentionally does not silently trim backend-visible Game
        Conversation history. Prompt/window policy belongs to the companion
        backend, while the Core remains the durable source of conversation
        continuity.
        """
        rows = self._connection.execute(
            "SELECT * FROM turns WHERE conversation_id=? ORDER BY created_at ASC, rowid ASC",
            (conversation_id,),
        ).fetchall()
        return self._decode_turn_rows(rows)

    @staticmethod
    def _decode_turn_rows(rows):
        result = []
        for row in rows:
            item = dict(row)
            item["input_event_ids"] = json.loads(item["input_event_ids"])
            result.append(item)
        return result

    def counts(self):
        names = ("worlds", "game_events", "game_conversations", "turns", "world_memories")
        with self._lock:
            return {name: self._connection.execute(
                "SELECT COUNT(*) FROM " + name).fetchone()[0] for name in names}
