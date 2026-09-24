# Sims Companion Bridge — Public Demo Spec

Goal: build a clean public demo repository for a The Sims 4 companion bridge.

## Positioning
This is not "another AI NPC mod". It is a bridge that lets users connect an existing long-running AI companion/agent backend to The Sims 4 through an independent game window, world-scoped state, and a provider-neutral protocol.

## Public v0.1 scope
- No private user/persona data.
- No hard-coded personal names, servers, API keys, memory content, or local machine paths.
- Windows-first demo, but protocol/core code should not hard-code Windows paths.
- Must run without The Sims 4 using a mock game environment.
- Game actions/autonomy are NOT part of v0.1 demo. Read-only environment only.
- Cross-surface recall is interface-only in v0.1, disabled by default.
- Game world data is separate from external companion memory.
- World Event Store is the source of truth for game-world facts.

## Architecture
1. game-mod/: Python 3.7-compatible TS4 bridge source skeleton.
2. gateway/: modern Python local gateway, localhost-only.
3. web/: independent Game Window UI.
4. protocol/: versioned schemas/contracts.
5. sdk/python/: backend adapter SDK.
6. adapters/mock/: deterministic demo backend.
7. docs/: architecture, backend protocol, security, memory model.
8. tests/: unit/integration tests.

## Required demo experience
Run one command and open a local Game Window:
- Chat tab: send a message to the mock companion.
- Now tab: display mock game online/offline, zone, player/companion state.
- World tab: show world id/branch id and recent world events.
- Diagnostics tab: show protocol version, gateway health, backend capabilities.
- No external API key required.

## Protocol principles
Public protocol uses generic terms, NOT implementation-specific names like normal/contact/activity.
- surface = "sims"
- turn_source = "user" | "proactive" | "world_event"
- request_id, conversation_id, world_id, branch_id
- capabilities negotiation
- backend returns text and optional semantic intents; v0.1 demo does not execute intents.
- strict validation and size limits.
- backend is untrusted input.

## Data model
World(world_id, branch_id, save_slot_id?, fingerprint?, status)
GameConversation(conversation_id, world_id, branch_id, created_at)
GameEvent(event_id, type, source, provenance, wallclock, sim_time?, payload)
Turn(turn_id, turn_source, surface, input_event_ids, output_message_id)
WorldMemory(memory_id, world_id, branch_id, epistemic_status, evidence_refs)
CrossSurfaceProvider is optional and disabled in demo.

## Security
- gateway binds only 127.0.0.1
- strict Host/Origin checks for UI/API
- no secrets in browser bundle
- remote backend output must be validated
- environment text is untrusted data, never system instructions
- sanitized support/doctor output
- no shell/arbitrary URL/arbitrary file actions
- README must clearly disclose what data leaves the machine when remote backend mode is later enabled

## Repo quality
- MIT license
- THIRD_PARTY_NOTICES.md
- .gitignore
- pyproject.toml
- README.md with 30-second overview, architecture diagram, quick start, current scope/non-goals, roadmap
- tests runnable via pytest
- package should be understandable to HR/open-source visitors quickly
- no fake claims that the TS4 integration has already been game-tested

## Important
Build a working mock-first demo, not a fake static mockup. Gateway + SQLite store + mock backend + web UI should genuinely exchange messages and persist demo world events.
