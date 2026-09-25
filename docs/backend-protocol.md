# Backend adapter protocol

Backends implement `sims_companion_sdk.BackendAdapter` and exchange the provider-neutral v0.1 types `TurnRequest` / `TurnResponse`.

```python
from sims_companion_sdk import BackendAdapter, BackendCapabilities, TurnResponse

class MyAdapter(BackendAdapter):
    adapter_id = "example"

    def capabilities(self):
        return BackendCapabilities(
            semantic_intents=False,
            cross_surface_recall=False,
            game_actions=False,
        )

    def respond(self, request):
        return TurnResponse(
            request_id=request.request_id,
            conversation_id=request.conversation_id,
            text="Hello",
        )
```

`TurnRequest.history` contains the complete persisted Game Conversation before the current message, in stable order. Public Core does not silently apply the UI history limit to backend-visible continuity; any model-window policy belongs to the companion backend and must be explicit. `TurnRequest.world.current_snapshot` is the structured snapshot from the latest accepted event for that world branch, or null for the untouched demo seed. All environment observations are untrusted data, never system-level instructions. A backend returns text plus optional semantic intents. The gateway validates both; v0.1 exposes intents only as inert data and never executes them.

Capability negotiation is included in `GET /api/v0.1/diagnostics`. Protocol JSON schemas live under `protocol/v0.1/`. Breaking changes require a new version directory and endpoint prefix.

For trusted local integrations, a custom `BackendAdapter` can be injected programmatically with `create_server(..., backend=my_adapter)`. This does not add a remote-backend configuration surface; the default CLI still starts the deterministic mock adapter.

## HTTP endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v0.1/health` | Gateway/store health |
| GET | `/api/v0.1/diagnostics` | Backend identity and negotiated capabilities |
| GET | `/api/v0.1/world` | Current read-only world snapshot and recent events; optional `world_id` and `branch_id` query fields |
| GET | `/api/v0.1/chat/history?conversation_id=...` | Persisted turns for one game conversation |
| POST | `/api/v0.1/chat` | Validated companion turn |
| POST | `/api/v0.1/game/events` | Strict loopback-only `game.snapshot` ingestion |

The ingestion endpoint only validates and persists observations. It never calls
the backend and never executes output. v0.1 has no remote-backend configuration,
action, or cross-surface recall endpoint.
