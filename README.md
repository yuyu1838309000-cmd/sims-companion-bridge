# Sims Companion Bridge

Connect a long-running companion backend to a game-shaped, world-aware interface
without giving it control of the game. This v0.1 public demo runs entirely on
your machine: a real local gateway, a SQLite world/event store, a deterministic
mock companion, and an independent Game Window with Chat, Now, World, and
Diagnostics. No game or API key is required.

> Demo status: the mock experience is runnable. The game-mod directory is an
> unbuilt Python 3.7-compatible source skeleton and has **not** been tested in
> The Sims 4.

## Architecture

```text
Browser Game Window
        │ HTTP/JSON v0.1 on loopback only
        ▼
Local gateway ─── validates ───► deterministic mock adapter
        │                              │
        ▼                              └─ text + display-only intents
SQLite World Event Store
        ▲
future read-only game observations (skeleton only in v0.1)

Optional CrossSurfaceProvider: interface present, disabled by default
```

The World Event Store is the source of truth for game-world facts. It is kept
separate from any external companion memory.

## Quick start

Requires Python 3.9 or newer for the gateway.

```powershell
py -m pip install -e .; sims-companion-bridge
```

Open <http://127.0.0.1:8765>. Stop with `Ctrl+C`. The SQLite demo database is
created under `.local/` by default. Use `sims-companion-bridge --help` for the
port and database options.

Run tests:

```powershell
py -m pip install -e ".[dev]"
py -m pytest
```

## What v0.1 does

- Persists a synthetic world, events, conversations, and turns in SQLite.
- Produces deterministic local replies through a provider-neutral adapter.
- Shows live health, world state, history, events, and negotiated capabilities.
- Validates browser input and treats backend output as untrusted.
- Binds only to loopback and enforces Host, Origin, size, and static-path checks.

## Scope and non-goals

The environment is read-only. There are no game actions, autonomy hooks,
arbitrary URLs, shell commands, or file actions. Cross-surface recall is only an
interface and is disabled. The demo has no private persona or memory data and is
not a playable mod. See [the memory model](docs/memory-model.md) and
[security policy](SECURITY.md).

If a remote backend is added later, the adapter may send the current user
message, the complete prior Game Conversation, world/branch identifiers,
selected event IDs, and the read-only world snapshot off-device. Such a mode
must be explicit opt-in, disclose its destination and data fields, and must not
place credentials in the browser bundle.

## Repository map

- `gateway/`: localhost server, validation, service, and SQLite store
- `web/`: dependency-free independent Game Window
- `protocol/v0.1/`: versioned JSON Schema contracts
- `sdk/python/`: provider-neutral Python backend adapter SDK
- `adapters/mock/`: mock-adapter documentation
- `game-mod/`: Python 3.7-compatible, read-only source skeleton
- `docs/`: architecture, protocol, security, and memory design
- `tests/`: unit and HTTP integration coverage

## Roadmap

1. Package and game-test a read-only observation mod.
2. Add authenticated local ingestion with replay and reconnect behavior.
3. Add an explicitly configured remote adapter with consent and data previews.
4. Explore opt-in recall providers while preserving world/external-memory separation.

Licensed under the [MIT License](LICENSE).
