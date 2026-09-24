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

`TurnRequest.world` and future environment observations are untrusted data, never system-level instructions. A backend returns text plus optional semantic intents. The gateway validates both; v0.1 exposes intents only as inert data and never executes them.

Capability negotiation is included in `GET /api/v0.1/diagnostics`. Protocol JSON schemas live under `protocol/v0.1/`. Breaking changes require a new version directory and endpoint prefix.

## HTTP endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v0.1/health` | Gateway/store health |
| GET | `/api/v0.1/diagnostics` | Backend identity and negotiated capabilities |
| GET | `/api/v0.1/world` | Current synthetic read-only world snapshot and recent events |
| GET | `/api/v0.1/chat/history?conversation_id=...` | Persisted turns for one game conversation |
| POST | `/api/v0.1/chat` | Validated companion turn |

v0.1 has no remote-backend configuration endpoint, game-ingestion endpoint, action endpoint, or cross-surface recall endpoint.
