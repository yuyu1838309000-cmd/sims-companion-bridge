"""Application service shared by the HTTP layer and tests."""

from dataclasses import asdict
from sims_companion_sdk import TurnRequest, TurnResponse

from . import PROTOCOL_VERSION, __version__
from .recall import DisabledCrossSurfaceProvider
from .validation import ALLOWED_TURN_SOURCES, ValidationError, require_id, require_text, validate_backend_response


class BridgeApp:
    def __init__(self, store, backend):
        self.store = store
        self.backend = backend
        self.recall = DisabledCrossSurfaceProvider()
        self.store.seed_demo()

    def health(self):
        return {"status": "ok", "gateway_version": __version__, "protocol_version": PROTOCOL_VERSION,
                "store": "sqlite", "counts": self.store.counts()}

    def diagnostics(self):
        return {
            **self.health(),
            "backend": {"id": self.backend.adapter_id, "capabilities": asdict(self.backend.capabilities())},
            "cross_surface_recall": {"enabled": self.recall.enabled},
            "binding": "loopback_only",
            "mode": "read_only",
        }

    def world_snapshot(self):
        world = self.store.get_world()
        if not world:
            raise RuntimeError("demo world is unavailable")
        return {"world": world, "events": self.store.recent_events()}

    def chat_history(self, conversation_id):
        require_id(conversation_id, "conversation_id")
        return {"conversation_id": conversation_id, "turns": self.store.turns(conversation_id)}

    def chat(self, data):
        if not isinstance(data, dict):
            raise ValidationError("request body must be an object")
        allowed = {"protocol_version", "surface", "message", "request_id", "conversation_id", "world_id", "branch_id", "turn_source"}
        if set(data) - allowed:
            raise ValidationError("request contains unsupported fields")
        if not allowed.issubset(data):
            raise ValidationError("request is missing required fields")
        if data["protocol_version"] != PROTOCOL_VERSION or data["surface"] != "sims":
            raise ValidationError("unsupported protocol version or surface")
        message = require_text(data.get("message"))
        request_id = require_id(data["request_id"], "request_id")
        conversation_id = require_id(data["conversation_id"], "conversation_id")
        world_id = require_id(data["world_id"], "world_id")
        branch_id = require_id(data["branch_id"], "branch_id")
        turn_source = data.get("turn_source", "user")
        if turn_source not in ALLOWED_TURN_SOURCES:
            raise ValidationError("invalid turn_source")
        world = self.store.get_world(world_id, branch_id)
        if not world:
            raise ValidationError("unknown world or branch")
        self.store.ensure_conversation(conversation_id, world_id, branch_id)
        event_ids = [e["event_id"] for e in self.store.recent_events(world_id, branch_id, 10)]
        history = []
        for turn in self.store.all_turns(conversation_id):
            history.append({
                "role": "user",
                "content": turn["user_text"],
                "turn_source": turn["turn_source"],
            })
            history.append({
                "role": "assistant",
                "content": turn["assistant_text"],
            })
        backend_response = self.backend.respond(TurnRequest(
            request_id=request_id, conversation_id=conversation_id,
            world_id=world_id, branch_id=branch_id, message=message,
            input_event_ids=event_ids, history=history,
            turn_source=turn_source, world=world,
        ))
        if isinstance(backend_response, TurnResponse):
            backend_response = asdict(backend_response)
        backend_result = validate_backend_response(backend_response)
        if (backend_result["request_id"] != request_id or
                backend_result["conversation_id"] != conversation_id):
            raise ValidationError("backend response identifiers do not match the request")
        turn_id, output_message_id = self.store.add_turn(
            conversation_id, turn_source, message, backend_result["text"], event_ids
        )
        self.store.add_event(world_id, branch_id, "conversation.turn_completed", "gateway",
                             "local", {"conversation_id": conversation_id,
                                       "request_id": request_id,
                                       "message_id": output_message_id})
        return {
            "turn_id": turn_id,
            "output_message_id": output_message_id, **backend_result,
            "intents_executed": False,
        }
