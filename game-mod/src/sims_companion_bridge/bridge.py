"""Pure Python 3.7 game observation normalization and event construction."""
from __future__ import absolute_import

import json
import math
import re
import time
import uuid


ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")
NEED_NAMES = ("hunger", "energy", "fun", "social", "hygiene", "bladder")
MAX_PAYLOAD_BYTES = 12 * 1024
MAX_WALLCLOCK_UNIX = 4102444800


def _text(value, limit):
    if value is None:
        return None
    try:
        value = str(value).strip()
    except Exception:
        return None
    if not value:
        return None
    return value[:limit]


def _identifier_or_none(value):
    if value is None:
        return None
    try:
        value = str(value).strip()
    except Exception:
        return None
    return value if ID_RE.fullmatch(value) else None


def _number(value, minimum, maximum):
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(value):
        return None
    return max(minimum, min(maximum, value))


def _text_list(value, limit):
    if not isinstance(value, (list, tuple)):
        return []
    output = []
    for item in value:
        clean = _text(item, 128)
        if clean is not None:
            output.append(clean)
        if len(output) >= limit:
            break
    return output


def _normalize_sim(value):
    if not isinstance(value, dict):
        return None
    mood = value.get("mood") if isinstance(value.get("mood"), dict) else {}
    needs = value.get("needs") if isinstance(value.get("needs"), dict) else {}
    interactions = value.get("interactions")
    if not isinstance(interactions, dict):
        interactions = value.get("actions") if isinstance(value.get("actions"), dict) else {}
    return {
        "sim_id": _identifier_or_none(value.get("sim_id")),
        "name": _text(value.get("name"), 128),
        "mood": {
            "name": _text(mood.get("name"), 64),
            "intensity": _number(mood.get("intensity"), -1000.0, 1000.0),
        },
        "needs": {key: _number(needs.get(key), 0.0, 100.0) for key in NEED_NAMES},
        "interactions": {
            "running": _text_list(interactions.get("running"), 8),
            "queued": _text_list(interactions.get("queued"), 20),
        },
    }


def _payload_size(payload):
    return len(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8"))


def _fit_payload(payload):
    """Prefer core state and shed optional list detail until the wire bound fits."""
    while _payload_size(payload) > MAX_PAYLOAD_BYTES and payload["present_sims"]:
        payload["present_sims"].pop()
    for sim_name in ("player", "companion"):
        sim = payload[sim_name]
        if sim is None:
            continue
        for list_name in ("queued", "running"):
            while (_payload_size(payload) > MAX_PAYLOAD_BYTES and
                   sim["interactions"][list_name]):
                sim["interactions"][list_name].pop()
    if _payload_size(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError("normalized snapshot exceeds the protocol size limit")
    return payload


def normalize_observation(observation):
    """Convert a best-effort reader result into the strict v0.1 snapshot payload."""
    if not isinstance(observation, dict):
        raise ValueError("observation must be an object")
    zone = observation.get("zone") if isinstance(observation.get("zone"), dict) else {}
    simulation = observation.get("simulation")
    if not isinstance(simulation, dict):
        simulation = observation.get("world") if isinstance(observation.get("world"), dict) else {}
    build_buy = simulation.get("in_build_buy", simulation.get("build_buy"))
    if not isinstance(build_buy, bool):
        build_buy = None
    raw_present = observation.get("present_sims")
    present = []
    if isinstance(raw_present, (list, tuple)):
        for item in raw_present[:40]:
            if not isinstance(item, dict):
                continue
            present.append({
                "sim_id": _identifier_or_none(item.get("sim_id")),
                "name": _text(item.get("name"), 128),
            })
    payload = {
        "snapshot_version": "0.1",
        "save_slot_id": _identifier_or_none(
            observation.get("save_slot_id", observation.get("save_id"))
        ),
        "zone": {
            "zone_id": _identifier_or_none(zone.get("zone_id")),
            "name": _text(zone.get("name"), 256),
        },
        "simulation": {
            "sim_time": _text(simulation.get("sim_time"), 64),
            "in_build_buy": build_buy,
        },
        "player": _normalize_sim(observation.get("player", observation.get("user"))),
        "companion": _normalize_sim(observation.get("companion")),
        "present_sims": present,
    }
    return _fit_payload(payload)


class ReadOnlyBridge(object):
    """Convert allow-listed observations into bounded protocol events."""

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

    def publish_snapshot(self, observation, player_state=None, companion_state=None,
                         sim_time=None, event_id=None, wallclock_unix=None):
        """Queue a snapshot without doing network I/O on the calling thread.

        The three-string form remains accepted for source compatibility with the
        original skeleton. New integrations should pass a reader observation.
        """
        if isinstance(observation, str):
            observation = {
                "zone": {"zone_id": None, "name": observation},
                "simulation": {"sim_time": sim_time, "in_build_buy": None},
                "player": {"name": player_state},
                "companion": {"name": companion_state},
                "present_sims": [],
            }
        payload = normalize_observation(observation)
        event_id = event_id or ("evt-" + uuid.uuid4().hex)
        event_id = self._identifier(event_id, "event_id")
        wallclock_unix = time.time() if wallclock_unix is None else wallclock_unix
        if (isinstance(wallclock_unix, bool) or
                not isinstance(wallclock_unix, (int, float)) or
                not math.isfinite(wallclock_unix) or
                wallclock_unix < 0 or wallclock_unix > MAX_WALLCLOCK_UNIX):
            raise ValueError("wallclock_unix is outside the protocol range")
        event_sim_time = _text(sim_time, 64) or payload["simulation"]["sim_time"]
        payload["simulation"]["sim_time"] = event_sim_time
        event = {
            "protocol_version": "0.1",
            "event_id": event_id,
            "world_id": self.world_id,
            "branch_id": self.branch_id,
            "type": "game.snapshot",
            "source": "game_mod",
            "provenance": "observed",
            "wallclock_unix": wallclock_unix,
            "sim_time": event_sim_time,
            "payload": payload,
        }
        self._queue.append(event)
        if len(self._queue) > self.MAX_QUEUE:
            self._queue.pop(0)
        return event

    def drain_events(self):
        output = self._queue
        self._queue = []
        return output

    def drain_json(self):
        """Drain canonical JSON envelopes for diagnostics or a transport worker."""
        return [json.dumps(item, separators=(",", ":"), sort_keys=True,
                           ensure_ascii=False, allow_nan=False)
                for item in self.drain_events()]
