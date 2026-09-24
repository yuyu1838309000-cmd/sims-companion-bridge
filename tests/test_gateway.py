import json
import threading
from http.client import HTTPConnection
from pathlib import Path

import pytest

from sims_companion_bridge.app import BridgeApp
from sims_companion_bridge.mock_backend import MockCompanionBackend
from sims_companion_bridge.server import create_server
from sims_companion_bridge.store import WorldStore
from sims_companion_bridge.validation import ValidationError, validate_backend_response


def chat_payload(message="hello", conversation="conversation-test"):
    return {"protocol_version": "0.1", "surface": "sims",
            "request_id": "request-test", "conversation_id": conversation,
            "world_id": "demo-world", "branch_id": "main",
            "turn_source": "user", "message": message}


def test_chat_persists_across_store_reopen(tmp_path):
    database = tmp_path / "world.sqlite3"
    store = WorldStore(database)
    app = BridgeApp(store, MockCompanionBackend())
    response = app.chat(chat_payload())
    assert response["protocol_version"] == "0.1"
    assert response["intents_executed"] is False
    store.close()
    reopened = WorldStore(database)
    assert reopened.turns("conversation-test")[0]["user_text"] == "hello"
    assert reopened.recent_events()[0]["type"] == "conversation.turn_completed"
    reopened.close()


def test_conversation_id_cannot_cross_world_branch(tmp_path):
    store = WorldStore(tmp_path / "scope.sqlite3")
    store.ensure_conversation("conversation-shared", "world-a", "main")
    with pytest.raises(ValueError, match="different world branch"):
        store.ensure_conversation("conversation-shared", "world-b", "branch-2")
    store.close()


def test_backend_intent_parameters_have_size_limit():
    oversized = {
        "protocol_version": "0.1",
        "request_id": "request-safe",
        "conversation_id": "conversation-safe",
        "text": "ok",
        "intents": [{"type": "display_hint", "parameters": {"blob": "x" * 5000}}],
    }
    with pytest.raises(ValidationError, match="size limit"):
        validate_backend_response(oversized)


def test_backend_intent_parameters_reject_non_finite_numbers():
    malformed = {
        "protocol_version": "0.1",
        "request_id": "request-safe",
        "conversation_id": "conversation-safe",
        "text": "ok",
        "intents": [{"type": "display_hint", "parameters": {"score": float("nan")}}],
    }
    with pytest.raises(ValidationError, match="JSON-serializable"):
        validate_backend_response(malformed)


class MismatchedBackend(MockCompanionBackend):
    def respond(self, request):
        result = super().respond(request)
        return type(result)("wrong-request", result.conversation_id, result.text, result.intents)


def test_untrusted_backend_identifiers_are_checked(tmp_path):
    store = WorldStore(tmp_path / "bad.sqlite3")
    app = BridgeApp(store, MismatchedBackend())
    with pytest.raises(ValidationError):
        app.chat(chat_payload())
    assert store.counts()["turns"] == 0
    store.close()


def test_create_server_accepts_programmatic_backend(tmp_path):
    class LocalAdapter(MockCompanionBackend):
        adapter_id = "local-adapter-test"

    instance = create_server(tmp_path / "custom.sqlite3", 0, backend=LocalAdapter())
    try:
        assert instance.app.diagnostics()["backend"]["id"] == "local-adapter-test"
        assert instance.store.counts()["worlds"] == 1
        assert instance.server_port > 0
    finally:
        instance.server_close()
        instance.store.close()


@pytest.fixture
def server(tmp_path):
    web = Path(__file__).resolve().parents[1] / "web"
    instance = create_server(tmp_path / "http.sqlite3", 0, web)
    thread = threading.Thread(target=instance.serve_forever, daemon=True); thread.start()
    yield instance
    instance.shutdown(); instance.server_close(); instance.store.close(); thread.join()


def http(server, method, path, body=None, headers=None):
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse(); data = response.read(); response_headers = dict(response.getheaders())
    status = response.status; connection.close()
    return status, response_headers, data


def test_full_http_demo_surface(server):
    status, headers, body = http(server, "GET", "/api/v0.1/health")
    assert status == 200 and json.loads(body)["status"] == "ok"
    assert headers["Content-Security-Policy"].startswith("default-src")
    assert b"Game Window" in http(server, "GET", "/")[2]
    assert json.loads(http(server, "GET", "/api/v0.1/world")[2])["world"]["world_id"] == "demo-world"
    diagnostics = json.loads(http(server, "GET", "/api/v0.1/diagnostics")[2])
    assert diagnostics["mode"] == "read_only"
    assert diagnostics["cross_surface_recall"]["enabled"] is False
    status, _, body = http(server, "POST", "/api/v0.1/chat", json.dumps(chat_payload(conversation="http-conversation")),
                           {"Content-Type": "application/json", "Origin": "http://127.0.0.1:%d" % server.server_port})
    assert status == 200 and json.loads(body)["intents_executed"] is False
    history = json.loads(http(server, "GET", "/api/v0.1/chat/history?conversation_id=http-conversation")[2])
    assert history["turns"][0]["user_text"] == "hello"


def test_http_security_boundaries(server):
    assert http(server, "GET", "/api/v0.1/health", headers={"Host": "example.invalid"})[0] == 403
    assert http(server, "POST", "/api/v0.1/chat", "{}", {"Content-Type": "text/plain"})[0] == 400
    assert http(server, "POST", "/api/v0.1/chat", "{}", {"Content-Type": "application/json", "Origin": "https://example.invalid"})[0] == 403
    assert http(server, "POST", "/api/v0.1/chat", "x" * 20000, {"Content-Type": "application/json"})[0] == 400
