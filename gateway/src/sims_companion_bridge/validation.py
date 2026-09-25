"""Boundary validation for untrusted browser and backend data."""

import json
import math
import re

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")
MAX_MESSAGE_CHARS = 2000
MAX_BACKEND_TEXT_CHARS = 4000
MAX_INTENT_PARAMETERS_BYTES = 4096
MAX_GAME_EVENT_BYTES = 16 * 1024
MAX_GAME_PAYLOAD_BYTES = 12 * 1024
MAX_JSON_DEPTH = 8
MAX_JSON_NODES = 512
MAX_WALLCLOCK_UNIX = 4102444800
ALLOWED_TURN_SOURCES = {"user", "proactive", "world_event"}
GAME_EVENT_FIELDS = {
    "protocol_version", "event_id", "world_id", "branch_id", "type",
    "source", "provenance", "wallclock_unix", "sim_time", "payload",
}
SNAPSHOT_FIELDS = {
    "snapshot_version", "save_slot_id", "zone", "simulation", "player",
    "companion", "present_sims",
}
SIM_FIELDS = {"sim_id", "name", "mood", "needs", "interactions"}
NEED_NAMES = {"hunger", "energy", "fun", "social", "hygiene", "bladder"}


class ValidationError(ValueError):
    pass


def require_id(value, name):
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ValidationError("{} must be a safe identifier".format(name))
    return value


def require_text(value, name="message", limit=MAX_MESSAGE_CHARS):
    if not isinstance(value, str):
        raise ValidationError("{} must be text".format(name))
    value = value.strip()
    if not value:
        raise ValidationError("{} cannot be empty".format(name))
    if len(value) > limit:
        raise ValidationError("{} exceeds {} characters".format(name, limit))
    return value


def _validate_json_shape(value, depth=0, state=None):
    """Reject values JSON itself cannot safely represent, before field parsing."""
    if state is None:
        state = {"nodes": 0, "containers": set()}
    state["nodes"] += 1
    if state["nodes"] > MAX_JSON_NODES:
        raise ValidationError("game event exceeds the JSON node limit")
    if depth > MAX_JSON_DEPTH:
        raise ValidationError("game event exceeds the JSON nesting limit")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValidationError("game event numbers must be finite")
    if isinstance(value, int) and not isinstance(value, bool) and abs(value) > 10 ** 15:
        raise ValidationError("game event number is outside the supported range")
    if isinstance(value, str):
        if len(value) > 4096:
            raise ValidationError("game event string exceeds the safety limit")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    if isinstance(value, (dict, list)):
        marker = id(value)
        if marker in state["containers"]:
            raise ValidationError("game event must not contain circular data")
        state["containers"].add(marker)
        try:
            if isinstance(value, dict):
                for key, item in value.items():
                    if not isinstance(key, str):
                        raise ValidationError("game event object keys must be text")
                    _validate_json_shape(item, depth + 1, state)
            else:
                for item in value:
                    _validate_json_shape(item, depth + 1, state)
        finally:
            state["containers"].remove(marker)
        return
    raise ValidationError("game event must contain only JSON values")


def _json_bytes(value, error_message):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError):
        raise ValidationError(error_message)


def _optional_text(value, name, limit):
    if value is None:
        return None
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ValidationError("{} must be null or 1 to {} characters".format(name, limit))
    return value


def _optional_id(value, name):
    if value is None:
        return None
    return require_id(value, name)


def _exact_object(value, fields, name):
    if not isinstance(value, dict) or set(value) != fields:
        raise ValidationError("{} fields do not match protocol v0.1".format(name))
    return value


def _finite_number(value, name, minimum, maximum, nullable=True):
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValidationError("{} must be a finite number".format(name))
    if value < minimum or value > maximum:
        raise ValidationError("{} is outside the supported range".format(name))
    return value


def _text_list(value, name, limit, item_limit=128):
    if not isinstance(value, list) or len(value) > limit:
        raise ValidationError("{} must be a list of at most {} items".format(name, limit))
    output = []
    for item in value:
        if not isinstance(item, str) or not item or len(item) > item_limit:
            raise ValidationError("{} items must contain 1 to {} characters".format(
                name, item_limit
            ))
        output.append(item)
    return output


def _validate_sim(value, name):
    if value is None:
        return None
    _exact_object(value, SIM_FIELDS, name)
    mood = _exact_object(value["mood"], {"name", "intensity"}, name + ".mood")
    needs = _exact_object(value["needs"], NEED_NAMES, name + ".needs")
    interactions = _exact_object(
        value["interactions"], {"running", "queued"}, name + ".interactions"
    )
    return {
        "sim_id": _optional_id(value["sim_id"], name + ".sim_id"),
        "name": _optional_text(value["name"], name + ".name", 128),
        "mood": {
            "name": _optional_text(mood["name"], name + ".mood.name", 64),
            "intensity": _finite_number(
                mood["intensity"], name + ".mood.intensity", -1000, 1000
            ),
        },
        "needs": {key: _finite_number(needs[key], name + ".needs." + key, 0, 100)
                  for key in sorted(NEED_NAMES)},
        "interactions": {
            "running": _text_list(interactions["running"], name + ".interactions.running", 8),
            "queued": _text_list(interactions["queued"], name + ".interactions.queued", 20),
        },
    }


def validate_game_event(value):
    """Validate and normalize the sole public game-ingestion event in v0.1."""
    _validate_json_shape(value)
    _exact_object(value, GAME_EVENT_FIELDS, "game event")
    if value["protocol_version"] != "0.1":
        raise ValidationError("unsupported game event protocol version")
    if value["type"] != "game.snapshot":
        raise ValidationError("unsupported game event type")
    if value["source"] != "game_mod" or value["provenance"] != "observed":
        raise ValidationError("invalid game event source or provenance")
    payload = _exact_object(value["payload"], SNAPSHOT_FIELDS, "snapshot payload")
    if payload["snapshot_version"] != "0.1":
        raise ValidationError("unsupported snapshot version")
    zone = _exact_object(payload["zone"], {"zone_id", "name"}, "snapshot zone")
    simulation = _exact_object(
        payload["simulation"], {"sim_time", "in_build_buy"}, "snapshot simulation"
    )
    if value["sim_time"] != simulation["sim_time"]:
        raise ValidationError("event and snapshot sim_time must match")
    if simulation["in_build_buy"] is not None and not isinstance(simulation["in_build_buy"], bool):
        raise ValidationError("snapshot simulation.in_build_buy must be boolean or null")
    present = payload["present_sims"]
    if not isinstance(present, list) or len(present) > 40:
        raise ValidationError("snapshot present_sims must contain at most 40 items")
    clean_present = []
    for index, item in enumerate(present):
        item = _exact_object(item, {"sim_id", "name"}, "present sim")
        clean_present.append({
            "sim_id": _optional_id(item["sim_id"], "present_sims[{}].sim_id".format(index)),
            "name": _optional_text(item["name"], "present_sims[{}].name".format(index), 128),
        })
    clean = {
        "protocol_version": "0.1",
        "event_id": require_id(value["event_id"], "event_id"),
        "world_id": require_id(value["world_id"], "world_id"),
        "branch_id": require_id(value["branch_id"], "branch_id"),
        "type": "game.snapshot",
        "source": "game_mod",
        "provenance": "observed",
        "wallclock_unix": _finite_number(
            value["wallclock_unix"], "wallclock_unix", 0, MAX_WALLCLOCK_UNIX, nullable=False
        ),
        "sim_time": _optional_text(value["sim_time"], "sim_time", 64),
        "payload": {
            "snapshot_version": "0.1",
            "save_slot_id": _optional_id(payload["save_slot_id"], "save_slot_id"),
            "zone": {
                "zone_id": _optional_id(zone["zone_id"], "zone_id"),
                "name": _optional_text(zone["name"], "zone.name", 256),
            },
            "simulation": {
                "sim_time": _optional_text(simulation["sim_time"], "simulation.sim_time", 64),
                "in_build_buy": simulation["in_build_buy"],
            },
            "player": _validate_sim(payload["player"], "snapshot player"),
            "companion": _validate_sim(payload["companion"], "snapshot companion"),
            "present_sims": clean_present,
        },
    }
    if len(_json_bytes(clean["payload"], "snapshot payload must be JSON-safe")) > MAX_GAME_PAYLOAD_BYTES:
        raise ValidationError("snapshot payload exceeds the protocol size limit")
    if len(_json_bytes(clean, "game event must be JSON-safe")) > MAX_GAME_EVENT_BYTES:
        raise ValidationError("game event exceeds the protocol size limit")
    return clean


def validate_backend_response(value):
    if not isinstance(value, dict):
        raise ValidationError("backend response must be an object")
    required = {"protocol_version", "request_id", "conversation_id", "text", "intents"}
    if set(value) != required:
        raise ValidationError("backend response fields do not match protocol v0.1")
    if value["protocol_version"] != "0.1":
        raise ValidationError("backend protocol version is unsupported")
    request_id = require_id(value["request_id"], "request_id")
    conversation_id = require_id(value["conversation_id"], "conversation_id")
    text = require_text(value.get("text"), "backend text", MAX_BACKEND_TEXT_CHARS)
    intents = value.get("intents", [])
    if not isinstance(intents, list) or len(intents) > 16:
        raise ValidationError("backend intents must be a list of at most 16 items")
    clean = []
    for intent in intents:
        if not isinstance(intent, dict) or set(intent) - {"type", "parameters"}:
            raise ValidationError("invalid semantic intent")
        intent_type = require_id(intent.get("type"), "intent type")
        parameters = intent.get("parameters", {})
        if not isinstance(parameters, dict):
            raise ValidationError("intent parameters must be an object")
        try:
            encoded_parameters = json.dumps(
                parameters, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            ).encode("utf-8")
        except (TypeError, ValueError, RecursionError):
            raise ValidationError("intent parameters must be JSON-serializable")
        if len(encoded_parameters) > MAX_INTENT_PARAMETERS_BYTES:
            raise ValidationError("intent parameters exceed the protocol size limit")
        clean.append({"type": intent_type, "parameters": parameters})
    return {"protocol_version": "0.1", "request_id": request_id,
            "conversation_id": conversation_id, "text": text, "intents": clean}
