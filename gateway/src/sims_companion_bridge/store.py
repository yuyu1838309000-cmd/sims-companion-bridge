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
  PRIMARY KEY (world_id, branch_id)
);
CREATE TABLE IF NOT EXISTS game_conversations (
  conversation_id TEXT PRIMARY KEY, world_id TEXT NOT NULL,
  branch_id TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS game_events (
  event_id TEXT PRIMARY KEY, world_id TEXT NOT NULL, branch_id TEXT NOT NULL,
  type TEXT NOT NULL, source TEXT NOT NULL, provenance TEXT NOT NULL,
  wallclock TEXT NOT NULL, sim_time TEXT, payload TEXT NOT NULL
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


class WorldStore:
    def __init__(self, path):
        self.path = str(Path(path))
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        with self._connection:
            self._connection.executescript(SCHEMA)

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
                "INSERT INTO worlds VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("demo-world", "main", "demo-slot", "synthetic-demo", "offline",
                 "Demo Neighborhood / Garden Lot", "At home", "Ready to chat"),
            )
            self.add_event("demo-world", "main", "world.loaded", "mock_game",
                           "demo_seed", {"zone": "Demo Neighborhood / Garden Lot"}, "Day 1, 09:00")
            self.add_event("demo-world", "main", "sim.mood_observed", "mock_game",
                           "demo_seed", {"subject": "player", "mood": "focused"}, "Day 1, 09:05")

    def get_world(self, world_id="demo-world", branch_id="main"):
        row = self._connection.execute(
            "SELECT * FROM worlds WHERE world_id=? AND branch_id=?", (world_id, branch_id)
        ).fetchone()
        return dict(row) if row else None

    def add_event(self, world_id, branch_id, event_type, source, provenance, payload, sim_time=None):
        event_id = "evt-" + uuid.uuid4().hex
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO game_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (event_id, world_id, branch_id, event_type, source, provenance,
                 utc_now(), sim_time, json.dumps(payload, separators=(",", ":"), ensure_ascii=True)),
            )
        return event_id

    def recent_events(self, world_id="demo-world", branch_id="main", limit=50):
        rows = self._connection.execute(
            "SELECT * FROM game_events WHERE world_id=? AND branch_id=? ORDER BY wallclock DESC LIMIT ?",
            (world_id, branch_id, min(max(int(limit), 1), 100)),
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
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
