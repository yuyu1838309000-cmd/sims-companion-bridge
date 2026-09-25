[Reading 81 lines from start (total: 81 lines, 0 remaining)]

# Compatibility and current support

[中文](compatibility.md)

This page answers one question: **can I use this project right now?**

Last reviewed: 2026-09-25.

## Current platform status

| Item | Current status |
| --- | --- |
| Windows | Development target |
| macOS | Not verified |
| The Sims 4 1.128.90.1030 | Current test target |
| Other Sims 4 versions | Not verified |
| Local demo without The Sims 4 | Supported |
| Real-game TS4Script | Read-only smoke passed on 1.128.90.1030 |

## Which users can use it now?

### I only want to download a finished Mod and play

**Not yet.**

The current game package has passed its first read-only real-game smoke test, but it is not yet a finished player release.

### I want to see the project without installing The Sims 4

**Yes.**

The local demo works without the game and without an API key.

### I already have my own AI companion or chat service

**Only with developer help for now.**

The project already has a backend adapter interface, but there is no simple settings page for entering a service URL or API key yet.

### I use an OpenAI-compatible API, Ollama, or another common AI service

**There is no built-in one-click setup yet.**

A developer can write an adapter, but these services are not currently advertised as plug-and-play integrations.

### I want the AI to control Sims

**Not in the current version.**

The current game integration is read-only.

### I want to develop an integration

**Yes.**

Developers can use the local demo, Python SDK, backend adapter interface, protocol schemas, automated tests, and TS4Script build path.

## What is deliberately not supported yet?

The current public version does not provide:

- automatic Sim control;
- autonomous gameplay;
- proactive AI messages;
- cross-chat memory sharing;
- remote backend configuration UI;
- one-click installer;
- verified macOS support;
- a promise that every Sims 4 patch is compatible.

## How compatibility is reported

We do not use wording such as "supports the latest version" because The Sims 4 changes over time.

Compatibility should be written as:

```text
Verified on The Sims 4 <exact version>
```

Automated tests and real-game tests are reported separately.

A build is not called game-tested until it has actually loaded and worked in the target game version.

[executed on device: WIN-15QI2I7SNM4 (3b0744ec-1adf-45d0-b2db-5f62af795dec)]