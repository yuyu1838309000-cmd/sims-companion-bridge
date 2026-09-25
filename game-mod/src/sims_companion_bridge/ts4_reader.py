"""Best-effort, read-only TS4 state access with no import-time game dependency.

The public contract is intentionally smaller than the available game API. Every
field is isolated so a missing or patch-specific API becomes null/empty data.
"""
from __future__ import absolute_import

import importlib


NEED_HINTS = ("hunger", "energy", "fun", "social", "hygiene", "bladder")


def _safe(function, default=None):
    try:
        return function()
    except Exception:
        return default


def _value(value, default=None):
    if value is None:
        return default
    return _safe(value, default) if callable(value) else value


def _friendly_name(value):
    if value is None:
        return None
    name = _safe(lambda: value.__name__)
    if not name:
        name = _safe(lambda: value.__class__.__name__)
    if not name:
        name = _safe(lambda: str(value))
    return _safe(lambda: str(name).replace("_", " ")) if name else None


def _sim_name(sim_info):
    first = _safe(lambda: sim_info.first_name, "") or ""
    last = _safe(lambda: sim_info.last_name, "") or ""
    name = _safe(lambda: (str(first) + " " + str(last)).strip(), "")
    return name or None


def _load_services():
    return _safe(lambda: importlib.import_module("services"))


def _read_save_slot_id(services_module):
    try:
        lot51_save = importlib.import_module("lot51_core.lib.save")
        value = lot51_save.get_save_slot_guid()
        if value is not None:
            return str(value)
    except Exception:
        pass
    persistence = _safe(lambda: services_module.get_persistence_service())
    if persistence is None:
        persistence = _safe(lambda: services_module.persistence_service())
    value = _safe(lambda: persistence.get_save_slot_proto_guid()) if persistence else None
    if value is None and persistence is not None:
        value = _safe(lambda: persistence.save_slot_id)
    return str(value) if value is not None else None


def _active_sim_info(services_module):
    sim_info = _safe(lambda: services_module.active_sim_info())
    if sim_info is not None:
        return sim_info
    client = _safe(lambda: services_module.client_manager().get_first_client())
    active = _safe(lambda: client.active_sim) if client is not None else None
    return _safe(lambda: active.sim_info) if active is not None else None


def _find_sim_info(services_module, sim_id):
    if sim_id is None:
        return None
    manager = _safe(lambda: services_module.sim_info_manager())
    if manager is None:
        return None
    return _safe(lambda: manager.get(int(sim_id)))


def _read_zone(services_module):
    zone = _safe(lambda: services_module.current_zone())
    if zone is None:
        return {"zone_id": None, "name": None}, None
    zone_id = _safe(lambda: zone.id)
    if zone_id is None:
        zone_id = _safe(lambda: zone.zone_id)
    name = _safe(lambda: zone.name)
    lot = _safe(lambda: zone.lot)
    if not name and lot is not None:
        name = _safe(lambda: lot.name) or _safe(lambda: lot.lot_name)
    build_buy = _value(_safe(lambda: zone.is_in_build_buy))
    if not isinstance(build_buy, bool):
        build_buy = None
    return {
        "zone_id": _safe(lambda: str(zone_id)) if zone_id is not None else None,
        "name": _safe(lambda: str(name)) if name else None,
    }, build_buy


def _read_sim_time(services_module):
    clock = _safe(lambda: services_module.game_clock_service())
    now = _safe(lambda: clock.now()) if clock is not None else None
    if now is None:
        return None
    hour = _value(_safe(lambda: now.hour))
    minute = _value(_safe(lambda: now.minute))
    day = _value(_safe(lambda: now.day))
    if hour is None or minute is None:
        return _safe(lambda: str(now))
    prefix = _safe(lambda: "Day %s, " % day, "") if day is not None else ""
    return _safe(lambda: "%s%02d:%02d" % (prefix, int(hour), int(minute)),
                 _safe(lambda: str(now)))


def _read_mood(sim_info):
    mood = _safe(lambda: sim_info.get_mood())
    intensity = _safe(lambda: sim_info.get_mood_intensity())
    return {"name": _friendly_name(mood), "intensity": intensity}


def _read_needs(sim_info):
    output = {}
    tracker = _safe(lambda: sim_info.commodity_tracker)
    commodities = _safe(lambda: list(tracker), []) if tracker is not None else []
    for commodity in commodities or []:
        raw_name = (_friendly_name(_safe(lambda: commodity.stat_type)) or "").lower().replace(" ", "_")
        for key in NEED_HINTS:
            if key not in raw_name or key in output:
                continue
            value = _safe(lambda: float(commodity.get_value()))
            minimum = _safe(lambda: float(commodity.min_value), -100.0)
            maximum = _safe(lambda: float(commodity.max_value), 100.0)
            if value is None or minimum is None or maximum is None:
                output[key] = None
            elif maximum == minimum:
                output[key] = value
            else:
                output[key] = ((value - minimum) / (maximum - minimum)) * 100.0
    return output


def _interaction_name(interaction):
    affordance = _safe(lambda: interaction.affordance)
    return _friendly_name(affordance) or _friendly_name(interaction)


def _read_interactions(sim_info):
    sim = _safe(lambda: sim_info.get_sim_instance())
    if sim is None:
        return {"running": [], "queued": []}
    queue = _safe(lambda: sim.queue)
    current = _safe(lambda: queue.running) if queue is not None else None
    running_items = []
    if current is not None:
        running_items.append(current)
    si_state = _safe(lambda: sim.si_state)
    mixers = _safe(lambda: list(si_state.sis_actor_gen()), []) if si_state is not None else []
    for item in mixers or []:
        if item is not current:
            running_items.append(item)

    queued_items = _safe(lambda: list(queue), []) if queue is not None else []
    running_ids = set(id(item) for item in running_items)
    queued_items = [item for item in (queued_items or []) if id(item) not in running_ids]

    running = []
    for item in running_items[:8]:
        name = _interaction_name(item)
        if name:
            running.append(name)
    queued = []
    for item in queued_items[:20]:
        name = _interaction_name(item)
        if name:
            queued.append(name)
    return {"running": running, "queued": queued}


def _read_sim(sim_info):
    if sim_info is None:
        return None
    sim_id = _safe(lambda: sim_info.sim_id)
    return {
        "sim_id": _safe(lambda: str(sim_id)) if sim_id is not None else None,
        "name": _safe(lambda: _sim_name(sim_info)),
        "mood": _safe(lambda: _read_mood(sim_info), {"name": None, "intensity": None}),
        "needs": _safe(lambda: _read_needs(sim_info), {}),
        "interactions": _safe(
            lambda: _read_interactions(sim_info), {"running": [], "queued": []}
        ),
    }


def _read_present_sims(services_module):
    manager = _safe(lambda: services_module.sim_info_manager())
    sims = _safe(lambda: list(manager.instanced_sims_gen()), []) if manager is not None else []
    output = []
    for sim in (sims or [])[:40]:
        try:
            on_lot = getattr(sim, "is_on_active_lot", None)
            if callable(on_lot) and not on_lot():
                continue
            sim_info = getattr(sim, "sim_info", sim)
            sim_id = getattr(sim_info, "sim_id", None)
            output.append({
                "sim_id": str(sim_id) if sim_id is not None else None,
                "name": _sim_name(sim_info),
            })
        except Exception:
            continue
    return output


def read_observation(bound_companion_sim_id=None, services_module=None):
    """Read a generic snapshot. Supplying services_module enables fixture tests."""
    services_module = services_module or _load_services()
    if services_module is None:
        return {
            "save_slot_id": None,
            "zone": {"zone_id": None, "name": None},
            "simulation": {"sim_time": None, "in_build_buy": None},
            "player": None,
            "companion": None,
            "present_sims": [],
        }
    zone, build_buy = _safe(
        lambda: _read_zone(services_module),
        ({"zone_id": None, "name": None}, None),
    )
    player = _safe(lambda: _active_sim_info(services_module))
    companion = _safe(lambda: _find_sim_info(services_module, bound_companion_sim_id))
    return {
        "save_slot_id": _safe(lambda: _read_save_slot_id(services_module)),
        "zone": zone,
        "simulation": {
            "sim_time": _safe(lambda: _read_sim_time(services_module)),
            "in_build_buy": build_buy,
        },
        "player": _safe(lambda: _read_sim(player)),
        "companion": _safe(lambda: _read_sim(companion)),
        "present_sims": _safe(lambda: _read_present_sims(services_module), []),
    }
