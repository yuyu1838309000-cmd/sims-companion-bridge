# Development workflow and gates

This project separates design, source work, candidate packaging, Live Mods, and
real-game verification. Passing an offline test never implies that a Mod has
loaded successfully in The Sims 4.

## Canonical status names

Use these exact states when reporting progress:

1. `DESIGN`
2. `SOURCE_IMPLEMENTED`
3. `SOURCE_REVIEWED`
4. `AUTOMATED_TESTED`
5. `INSTALLABLE_CANDIDATE`
6. `GAME_LOADED`
7. `GAME_SMOKE_TESTED`
8. `GAME_TESTED`
9. `RELEASE_CANDIDATE`
10. `RELEASED`

Do not collapse `AUTOMATED_TESTED` and `GAME_TESTED` into “tested”.

## P0 - Define scope

Before code, write the smallest user-visible goal and an explicit non-goal list.
Record whether the change reads game state, changes game state, uses a backend,
or crosses the Public Core / private-adapter boundary.

**Gate:** the feature can be explained in one or two sentences and its
non-goals are explicit.

## P1 - Define contracts before TS4 APIs

Define or update the versioned public payload first. Mark fields as required,
optional, bounded, and fail-soft. Keep TS4 object details behind the reader.

Preferred dependency direction:

```text
TS4 API -> reader -> public snapshot/event -> gateway/store -> backend/UI
```

A game patch should normally require reader changes, not protocol-wide changes.

## P2 - Implement only in the source workspace

The repository is the development workspace. The user's Live Mods directory is
a runtime target, never an editing workspace.

During source work:

- never edit a `.ts4script` inside Live Mods;
- never replace a Live Mod while the game is running;
- never copy private persona, memory, credentials, or server addresses into the
  Public Core;
- treat a dirty working tree as protected state, not disposable state;
- do not use reset/clean/checkout to make a workspace “look clean”.

**Gate:** source is implemented inside the intended boundary and reviewed for
scope creep.

## P3 - Static and privacy checks

Before packaging, verify the target Python compatibility, source syntax,
`git diff --check`, privacy boundaries, and generated-bytecode path leakage.

For game-side code, compile with the Python runtime required by the target game
patch. Do not use the gateway's newer Python runtime to produce TS4 bytecode.

**Gate:** no static, privacy, or compatibility blocker remains.

## P4 - Automated tests

Run reader fixtures, schema validation, gateway/store integration, replay and
conflict tests, HTTP boundary tests, and relevant Game Window tests.

Fixtures prove normalization and contracts. They do **not** prove that EA's
current runtime still exposes the same API.

**Gate:** the complete relevant automated suite passes.

## P5 - Build an installable candidate

Build with:

```powershell
python game-mod/build_ts4script.py --game-version <exact-game-version>
```

The build writes both the `.ts4script` and a sibling
`.manifest.json`. The manifest records the artifact hash, Python bytecode
magic, module list, target game version, git state, source fingerprint, and the
fact that the build is not game-tested. Archive metadata is normalized so the
same source produces the same artifact hash; preflight rejects a stale candidate
when its source fingerprint no longer matches the current game-side source.

Run the preflight gate from a normal development Python:

```powershell
py scripts/preflight.py --game-version <exact-game-version>
```

A private environment may additionally pass a local deny-list with
`--deny-file`; private terms must not be committed to this repository.

Expected final line:

```text
GATE=READY_FOR_GAME_TEST
```

`READY_FOR_GAME_TEST` means “safe to proceed to controlled installation”.
It does not mean the candidate is installed or game-tested.

## P6 - Live Mods installation gate

Before changing Live Mods:

- The Sims 4 must be stopped.
- The exact candidate hash must be known.
- The previous installed build must be identifiable or backed up.
- Install only the intended candidate into a dedicated shallow Mod directory.
- Do not copy development caches, source trees, databases, or manifests unless
  deliberately required for diagnostics.

Installing is a separate operation from building. Never make build scripts
silently mutate Live Mods.

## P7 - Real-game smoke test

First prove only that the Mod is alive. Follow
[GAME_TEST_CHECKLIST.md](GAME_TEST_CHECKLIST.md).

The first smoke test should verify loader registration, manual status/snapshot
commands, worker delivery, gateway ingestion, world selection, and Game Window
routing. Do not enable unrelated features while diagnosing loader/reader
compatibility.

**Gate:** the read-only path works in the target game patch without new
script/LastException failures.

## P8 - Feature tests and regression

After smoke success, test one capability at a time. Record expected input,
observable result, and failure behavior. Re-run the automated suite after
game-driven fixes.

Avoid enabling environment polling, recall, proactive messaging, and game
actions in one test step; otherwise failures become expensive to isolate.

## P9 - Game actions use a separate permission track

Observation permission never implies action permission. Any future action layer
must distinguish read-only observation, low-risk actions, state mutation, and
destructive actions. Save edits, money, relationships, careers, CAS, deletion,
and similar mutations require explicit design and separate tests.

## Cost-control rules

To keep maintenance cheap:

- keep one public protocol and one reader boundary rather than patch-specific
  logic throughout the stack;
- keep one current candidate in `game-mod/dist`, identified by hash;
- make preflight checks executable instead of relying on memory;
- log automated and real-game verification separately;
- prefer fail-soft optional fields over failing a whole snapshot;
- never perform network I/O on the game thread;
- never access live TS4 objects from the network worker;
- keep Snapshot (“what is true now”) separate from Event (“what happened”);
- record compatibility as “verified on <game version>”, not “supports latest”.

These rules are intended to make a new game patch or new contributor require a
small reader/test update rather than a new architecture.


## Updating GitHub

Do not push every local edit just because it exists.

Update the public GitHub repository when a coherent development step is ready to be understood by someone outside the project.

Before a normal push:

- review the diff;
- run the relevant automated tests;
- run privacy checks for public files;
- make sure README claims match the real tested state;
- update user-facing docs when installation, compatibility, or behavior changed;
- do not call a build game-tested unless it actually passed the real-game check.

A player-facing release that contains a TS4Script should not be published as a normal installable release until the target game version has passed the real-game smoke test.

Small internal refactors that do not change public behavior do not require README edits.

## Public documentation style

The public README is written for people who may know The Sims 4 but may not know this codebase.

Keep it short and answer these questions first:

1. What does this project do?
2. Who can use it now?
3. What works today?
4. Is it safe to install?
5. Where are the installation steps?
6. Where should a developer go next?

Rules:

- use ordinary words before technical terms;
- explain necessary terms once instead of inventing project-specific names for simple ideas;
- keep README.md (Chinese default) and README.en.md (English switch) consistent;
- put detailed protocol, architecture, and test information in docs/, not on the README front page;
- use exact support wording such as `Verified on The Sims 4 <exact version>`;
- clearly separate “works in automated tests” from “verified in the real game”;
- clearly say when a feature is not available yet.
