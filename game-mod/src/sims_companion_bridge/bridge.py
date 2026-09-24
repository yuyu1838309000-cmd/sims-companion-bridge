"""Game-facing read-only boundary. No game imports keep this skeleton testable."""
from __future__ import absolute_import

import json
import re
import time
import uuid


ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")


class ReadOnlyBridge(object):
    """Converts allow-listed game observations into bounded protocol events."""

    MAX_QUEUE = 100

    def __init__(self, world_id, branch_id="main"):
        self.world_id = self._identifier(world_id, "world_id")
        self.branch_id = self._identifier(branch_id, "branch_id")
        self._queue = []

    @staticmethod
    def _identifier(value, name):
        if not isinstance(value, str) or not ID_RE.fullmatch(value):
            raise ValueError("%s must match the protocol identifier format" % name)
        return value

    @staticmethod
    def _bounded(value, name):
        if not isinstance(value, str) or not value or len(value) > 128:
            raise ValueError("%s must contain 1 to 128 characters" % name)
        return value

    def publish_snapshot(self, zone_name, player_state, companion_state, sim_time=None):
        """Queue allow-listed display strings; never accept commands or instructions."""
        payload = {
            "zone": self._bounded(zone_name, "zone_name"),
            "player_state": self._bounded(player_state, "player_state"),
            "companion_state": self._bounded(companion_state, "companion_state"),
        }
        event = {
            "protocol_version": "0.1",
            "event_id": str(uuid.uuid4()),
            "world_id": self.world_id,
            "branch_id": self.branch_id,
            "type": "game.snapshot",
            "source": "game_mod",
            "provenance": "observed",
            "wallclock_unix": time.time(),
            "sim_time": sim_time,
            "payload": payload,
        }
        self._queue.append(event)
        if len(self._queue) > self.MAX_QUEUE:
            self._queue.pop(0)
        return event

    def drain_json(self):
        """Return queued envelopes for a future loopback transport implementation."""
        output = [json.dumps(item, separators=(",", ":"), sort_keys=True) for item in self._queue]
        self._queue = []
        return output
