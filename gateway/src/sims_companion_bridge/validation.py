"""Boundary validation for untrusted browser and backend data."""

import json
import re

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")
MAX_MESSAGE_CHARS = 2000
MAX_BACKEND_TEXT_CHARS = 4000
MAX_INTENT_PARAMETERS_BYTES = 4096
ALLOWED_TURN_SOURCES = {"user", "proactive", "world_event"}


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
