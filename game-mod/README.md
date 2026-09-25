# The Sims 4 read-only bridge

This directory contains Python 3.7-compatible source plus a reproducible
TS4Script build for the first public environment-observation path. The generated
archive is an **untested candidate**, not a game-verified release. Nothing here
performs game actions, changes autonomy, edits saves, or executes backend output.

The source is split into auditable boundaries:

- `ts4_reader.py` lazily imports TS4 APIs and reads save, zone, simulation,
  active-player, optional bound-companion, and present-Sim state. Individual
  fields fail soft when a patch-specific API is missing. Lot51 Core is only an
  optional guarded save-slot fallback.
- `bridge.py` is pure Python normalization. `normalize_observation()` closes and
  bounds the structured payload; `ReadOnlyBridge.publish_snapshot()` creates
  the versioned `game.snapshot` envelope and only queues it in memory.
- `transport.py` permits an explicit loopback HTTP origin only, bypasses
  system proxies, and keeps HTTP on a bounded daemon worker.
- `runtime.py` registers only `scb.snapshot` and `scb.status`. Snapshot
  reads happen on the game thread; delivery is queued to the worker. There is
  no automatic polling or action execution.
- `sims_companion_bridge_bootstrap.py` is the thin loader entrypoint used by
  the TS4Script archive.

Build the candidate with CPython 3.7:

```powershell
python game-mod/build_ts4script.py --game-version <exact-game-version>
```

The output is `game-mod/dist/SimsCompanionBridge.ts4script` plus
`SimsCompanionBridge.manifest.json`. The manifest records artifact hash,
bytecode/runtime metadata, target game version, git state, and explicit
`game_tested=false`. Run `py scripts/preflight.py --game-version <exact-game-version>` from the repository root
before any controlled Live Mods installation.

The endpoint is `POST /api/v0.1/game/events`; it carries observations only, with
no credentials or commands. The candidate must not be called game-tested until
the loader, reader APIs, and command path pass `docs/GAME_TEST_CHECKLIST.md` on
the target game patch.
