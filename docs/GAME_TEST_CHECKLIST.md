# Real-game test checklist

Use this checklist only after preflight reports `GATE=READY_FOR_GAME_TEST`.
The checklist is intentionally read-only for v0.1.

## A. Before installing

- [ ] Record candidate filename and SHA256 from the build manifest.
- [ ] Confirm the target Sims 4 version.
- [ ] Confirm The Sims 4 is not running.
- [ ] Identify the currently installed bridge build, if any.
- [ ] Preserve unrelated Live Mods and user files.
- [ ] Install only the intended `.ts4script` into a dedicated shallow folder.

**Stop immediately** if the candidate hash is unknown, the game is running, or
the Live Mods target is ambiguous.

## B. Loader smoke test

Start The Sims 4 normally.

- [ ] Game reaches the main menu.
- [ ] Script Mods are enabled.
- [ ] No new bridge-related LastException/LastCrash appears during load.
- [ ] Load a disposable/known test save before deeper checks.
- [ ] `scb.status` is registered and responds.

If `scb.status` is absent, stop here. Do not diagnose Gateway, AI, or world
routing until loader registration is fixed.

## C. Manual read-only snapshot

With the test household/zone loaded:

- [ ] Run `scb.snapshot` once.
- [ ] Command reports that work was queued.
- [ ] Run `scb.status` again.
- [ ] Worker reports successful delivery, not merely “queued”.
- [ ] No new bridge-related exception was created.

Expected behavior: the command reads current game state only. It must not alter
autonomy, relationships, money, skills, careers, objects, Sims, or the save.

## D. Gateway and world verification

- [ ] Local Gateway is reachable on the configured loopback endpoint.
- [ ] A new `game.snapshot` event exists.
- [ ] World/branch is no longer forced to `demo-world`.
- [ ] Current save identity is stable across repeated snapshots.
- [ ] Zone and game time match the loaded game.
- [ ] Active/player Sim and present Sims are plausible.
- [ ] Running and queued interactions are not duplicated incorrectly.
- [ ] Optional unavailable fields fail soft instead of dropping the snapshot.

## E. Game Window verification

- [ ] The Game Window switches to the most recently observed real game world.
- [ ] The visible world/branch matches the Gateway.
- [ ] A Game Conversation is scoped to that world/branch.
- [ ] Sending a chat turn refreshes the active world before routing.
- [ ] Demo-world history does not leak into the real-world conversation.
- [ ] Backend receives the current structured world snapshot.

## F. Result classification

Use exactly one result:

- `GAME_LOADED`: loader/commands work, deeper path not yet verified.
- `GAME_SMOKE_TESTED`: one read-only snapshot completed end to end.
- `GAME_TESTED`: planned v0.1 real-game cases passed on the recorded patch.
- `BLOCKED`: test could not continue because a prerequisite failed.
- `FAILED`: a reproducible defect occurred.

Record the game version, candidate SHA256, result, and any new logs. Automated
test results remain a separate field.

## G. After a failure

Do not stack unrelated fixes. Capture the smallest failing layer:

```text
loader -> reader -> queue -> transport -> gateway -> store -> Game Window
```

Fix that layer in source, re-run automated tests, rebuild a new candidate, run
preflight again, and only then replace the Live build.
