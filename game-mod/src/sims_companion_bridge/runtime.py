"""Minimal in-game entrypoint for read-only snapshot delivery.

This module registers explicit Live cheat commands only. It does not poll,
change game state, or perform network I/O on the simulation thread.
"""
from __future__ import absolute_import

import hashlib

import sims4.commands

from .bridge import ReadOnlyBridge
from .transport import EventWorker, LoopbackTransport
from .ts4_reader import read_observation


DEFAULT_GATEWAY = "http://127.0.0.1:8765"
_worker = None
_bridge = None
_bridge_world_id = None


def _output(connection):
    return sims4.commands.CheatOutput(connection)


def _world_id(save_slot_id):
    raw = str(save_slot_id or "unsaved").encode("utf-8", "replace")
    return "save-" + hashlib.sha256(raw).hexdigest()[:24]


def _ensure_sender(world_id):
    global _worker, _bridge, _bridge_world_id
    if _worker is None:
        _worker = EventWorker(LoopbackTransport(DEFAULT_GATEWAY), max_queue=20)
        _worker.start()
    if _bridge is None or _bridge_world_id != world_id:
        _bridge = ReadOnlyBridge(world_id, "main")
        _bridge_world_id = world_id
    return _bridge, _worker


@sims4.commands.Command("scb.snapshot", command_type=sims4.commands.CommandType.Live)
def snapshot_command(_connection=None):
    """Read current state on the game thread and enqueue one loopback event."""
    output = _output(_connection)
    try:
        observation = read_observation()
        world_id = _world_id(observation.get("save_slot_id"))
        bridge, worker = _ensure_sender(world_id)
        event = bridge.publish_snapshot(observation)
        if not worker.submit(event):
            output("[SCB] snapshot not queued; sender is unavailable or busy")
            return
        output("[SCB] snapshot queued: %s" % event["event_id"])
        output("[SCB] world=%s zone=%s" % (
            world_id, observation.get("zone", {}).get("name") or "unknown"
        ))
    except Exception as exc:
        output("[SCB] snapshot failed: %s" % str(exc)[:160])


@sims4.commands.Command("scb.status", command_type=sims4.commands.CommandType.Live)
def status_command(_connection=None):
    """Show sender state without touching gameplay state."""
    output = _output(_connection)
    if _worker is None:
        output("[SCB] sender has not started; run scb.snapshot")
        return
    thread = _worker._thread
    output("[SCB] sender=%s world=%s" % (
        "running" if thread is not None and thread.is_alive() else "stopped",
        _bridge_world_id or "none",
    ))
    if _worker.last_result is not None:
        ok, result = _worker.last_result
        output("[SCB] last_delivery=%s %s" % ("ok" if ok else "failed", str(result)[:160]))
