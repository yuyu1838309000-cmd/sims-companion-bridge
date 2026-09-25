[Reading 128 lines from start (total: 128 lines, 0 remaining)]

# Sims Companion Bridge

[中文](README.md)

Sims Companion Bridge connects an external AI companion or chat service to **The Sims 4**.

The goal is simple: let the AI know what is happening in the game and provide a separate game-focused conversation experience without mixing it with normal chat. The browser page in this repository is currently for demos and diagnostics; it is not meant to be a permanent requirement for players.

**The current version is read-only. It can read game state. It cannot control Sims.**

> Current status: the read-only path has passed its first real-game smoke test on **The Sims 4 1.128.90.1030**.
> This proves the script can load, read real game state, and deliver it to the local helper, but this is still not a normal player release.

## Who is this for?

### Players

This project is intended for players who want an AI companion to share a Sims world with them.

However, the current build is still a development preview. If you only want to download a finished Mod and play, wait for a game-tested release.

### People who already have an AI service

The project is designed so an existing companion or chat backend can be connected instead of creating a second AI personality inside the Mod.

At the moment, connecting a custom backend still requires developer work. There is no simple "paste an API key and play" setup yet.

### Developers

You can already run the local demo, inspect the protocol, build the read-only TS4Script, and write a custom backend adapter.

See [compatibility and current support](docs/compatibility.en.md) for the exact status.

## What works now?

| Feature | Status |
| --- | --- |
| Local Game Window demo | Works |
| Local SQLite world/event storage | Works |
| Mock AI conversation | Works |
| Read-only game snapshot protocol | Works in automated tests |
| Build a Python 3.7 TS4Script | Works |
| Real The Sims 4 loading test | Read-only smoke passed on 1.128.90.1030 |
| AI controls Sims | Not available |
| Simple setup for ordinary players | Not available yet |

## How it works

```text
The Sims 4
   |
   | read-only game state
   v
Local helper program
   |
   +--> saves world/events locally
   |
   +--> sends the current game context to the connected AI service
   |
   v
Game Window
```

The game-side script stays small. AI models, memory, databases, and other heavier work stay outside the game process.

## Try the local demo

The demo does **not** require The Sims 4 or an API key.

Requires Python 3.9 or newer:

```powershell
py -m pip install -e .
sims-companion-bridge
```

Then open:

```text
http://127.0.0.1:8765
```

This page is currently a development demo and diagnostics surface, not a permanent player requirement. Stop it with `Ctrl+C`.

## Test it with The Sims 4

The current game package is for controlled development testing only.

Read [Installation and game test](docs/installation.en.md) before copying anything into your Mods folder.

## Connect your own AI service

The default demo uses a local mock AI.

Developers can connect another backend through the Python adapter interface. See [Backend adapter protocol](docs/backend-protocol.md).

A simple setup screen for common AI services is not available yet.

## Current safety limits

The current game integration:

- does not control Sims;
- does not change money, relationships, skills, careers, or saves;
- does not run shell commands or arbitrary file actions;
- only sends game snapshots to a local loopback address;
- treats external backend output as untrusted data.

See [Security](SECURITY.md) for details.

## Documentation

For most people:

- [Installation and game test](docs/installation.en.md)
- [Compatibility and current support](docs/compatibility.en.md)

For developers:

- [Architecture](docs/architecture.md)
- [Backend adapter protocol](docs/backend-protocol.md)
- [Development workflow](docs/development-workflow.md)
- [Real-game test checklist](docs/GAME_TEST_CHECKLIST.md)

## License

MIT. See [LICENSE](LICENSE).

[executed on device: WIN-15QI2I7SNM4 (3b0744ec-1adf-45d0-b2db-5f62af795dec)]