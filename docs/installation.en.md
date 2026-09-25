[Reading 128 lines from start (total: 128 lines, 0 remaining)]

# Installation and game test

[中文](installation.md)

This page describes the **current development-test installation**.

The project is not yet a normal player release. The TS4Script build has not completed real-game verification, so these steps are for controlled testing only.

## Before you start

You need:

- The Sims 4;
- Script Mods enabled in Game Options;
- Python 3.9 or newer for the local helper program;
- CPython 3.7 only if you want to rebuild the TS4Script yourself.

The current test target is:

```text
The Sims 4 1.128.90.1030
```

Other game versions are not yet verified.

## 1. Start the local helper program

From the repository root:

```powershell
py -m pip install -e .
sims-companion-bridge
```

Open:

```text
http://127.0.0.1:8765
```

You should see the local Game Window.

## 2. Prepare the TS4Script test build

If you are using the repository build:

```powershell
python game-mod/build_ts4script.py --game-version 1.128.90.1030
py scripts/preflight.py --game-version 1.128.90.1030
```

Do not continue unless the final preflight line is:

```text
GATE=READY_FOR_GAME_TEST
```

The build file is:

```text
game-mod/dist/SimsCompanionBridge.ts4script
```

## 3. Install the test build

Fully close The Sims 4 first.

Place only the `.ts4script` file in a shallow folder inside your Sims 4 Mods folder, for example:

```text
Mods/
  SimsCompanionBridge/
    SimsCompanionBridge.ts4script
```

Do not copy the repository, source files, test files, SQLite databases, or build manifest into Mods.

The exact Sims 4 user-data folder can vary, especially when Windows Documents is redirected. Use the folder your game actually uses instead of assuming a fixed path.

## 4. Start the game

Start The Sims 4 normally.

Make sure both of these are enabled:

- Custom Content and Mods;
- Script Mods Allowed.

A full game restart is required after changing Script Mods settings or replacing a TS4Script.

## 5. Run the current smoke test

The current build exposes two read-only commands:

```text
scb.status
scb.snapshot
```

Run `scb.status` first.

Then run `scb.snapshot`.

The test checks whether the game can:

1. load the script;
2. read the current save/zone/Sim state;
3. send one read-only snapshot to the local helper program;
4. show the real game world in the Game Window.

See [the full checklist](GAME_TEST_CHECKLIST.md) for developer verification.

## What this test does not do

It does not:

- control Sims;
- change autonomy;
- change money, relationships, skills, careers, CAS, or saves;
- run AI actions;
- enable proactive messages;
- connect a remote AI service.

## For normal players

There is no normal-player installation package yet.

A future game-tested release should not require players to install Python 3.7, compile bytecode, run preflight, or understand the development repository.

Until then, treat this page as a development test guide, not a finished end-user installer.

[executed on device: WIN-15QI2I7SNM4 (3b0744ec-1adf-45d0-b2db-5f62af795dec)]