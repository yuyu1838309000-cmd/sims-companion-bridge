# Review notes

## Implemented

- Localhost-only gateway, persistent SQLite World Event Store, deterministic mock companion, strict validation, and a working four-tab Game Window.
- Protocol v0.1 schemas, capability negotiation, Python adapter SDK, disabled cross-surface recall interface, and inert semantic intents.
- Python 3.7-compatible read-only normalization, lazy TS4 reader, bounded
  loopback transport, thin loader, and explicit `scb.snapshot` / `scb.status`
  commands. A reproducible TS4Script candidate exists; its first read-only
  real-game smoke test passed on The Sims 4 1.128.90.1030. It cannot perform
  actions or alter autonomy.
- Strict `game.snapshot` contract and dedicated loopback ingestion route with
  atomic branch snapshot/event persistence, canonical idempotency, conflict
  detection, and additive SQLite migration.
- MIT license, public documentation, packaging metadata, and unit/integration tests.

## Verification

Verification on 2026-09-25:

- Full source/fixture/local-loopback suite after DX9 process detection fix: `pytest` -> **39 passed**.
- CPython 3.7.9 compiled all six `game-mod/src` modules and the build script.
- The generated TS4Script contains six sourceless Python 3.7 bytecode modules;
  its `420d0d0a` magic matches the current 1.128.90.1030 game runtime.
- Localhost integration tests verify ingestion, idempotent replay, conflict,
  preferred observed-world selection, and the next backend `TurnRequest.world`
  snapshot.
- Public-safety scans found no private names, local user ID, private server path, API-key-looking value, or non-demo credentials in source or the candidate archive; every pyc `co_filename` is relative.
- Codex review passes caught and fixed non-finite JSON backend parameters, persisted chat-history rendering, protocol-compatible game-side world/branch identifiers, positional SDK compatibility, and remote-backend privacy disclosure.
- Additional manual review fixed conversation IDs crossing world/branch boundaries, separated running from queued TS4 interactions, removed the Game Window's hard-coded demo-world routing, bounded backend intent parameters, and ensured the complete persisted Game Conversation reaches the backend independently of the UI history limit.
- Real-game smoke on 1.128.90.1030 loaded `scb.status`, delivered one `scb.snapshot` end to end, selected the observed save world, showed the real Sim state in the browser diagnostics page, and stored a chat turn scoped to that real world/branch. No new LastException, LastCrash, or lastUIException was produced. Candidate SHA256: `9578fc13c50f79a2bd5935d0085c7f4cd78aa3e16fb74cd89c1e5471db6ba80f`.

## Known gaps

Remote backends, automatic live lifecycle wiring, implemented recall, and
action execution remain outside v0.1. The first read-only real-game smoke has
passed, but broader game cases and a player-ready release are still later
milestones. The current Reader also returns a valid zone ID while the human-readable
zone name is null on the tested save; this is non-blocking and remains to be fixed.

## Public-safety boundary

The included mock mode makes no external model/API requests. Samples are synthetic and generic. Diagnostics expose product state only. The browser receives no backend credentials. A future remote-backend mode must be explicit opt-in and disclose which chat/world fields leave the machine.
