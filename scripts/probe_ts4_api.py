"""Read-only compatibility probe for the TS4 APIs used by the game bridge.

Run with the same Python major/minor as The Sims 4 bytecode (currently 3.7).
This checks symbol presence only; it does not replace a real-game smoke test.
"""
from __future__ import absolute_import, print_function

import argparse
import marshal
import os
import sys
import types
import zipfile


REQUIRED_CODE_OBJECTS = {
    "zone.pyc": (
        "load_zone",
        "do_zone_spin_up",
        "on_loading_screen_animation_finished",
        "on_teardown",
        "save_zone",
    ),
    "zone_spin_up_service.pyc": ("on_loading_screen_animation_finished",),
    "sims/sim.pyc": ("push_super_affordance",),
    "interactions/interaction_queue.pyc": ("__iter__", "run_interaction_gen", "running"),
    "interactions/si_state.pyc": ("__iter__", "sis_actor_gen"),
    "interactions/base/interaction.pyc": ("_trigger_interaction_start_event",),
    "services/__init__.pyc": (
        "active_sim_info",
        "current_zone",
        "get_persistence_service",
        "game_clock_service",
        "sim_info_manager",
        "client_manager",
    ),
    "services/persistence_service.pyc": ("get_save_slot_proto_guid",),
    "sims/sim_info_manager.pyc": ("instanced_sims_gen",),
    "sims/sim_info.pyc": ("get_sim_instance",),
}

REQUIRED_REFERENCES = {
    "zone.pyc": ("is_in_build_buy",),
    "sims/sim_info.pyc": ("get_mood", "get_mood_intensity"),
}


def _walk(code):
    yield code
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            for child in _walk(value):
                yield child


def _load_code(archive, name):
    raw = archive.read(name)
    if len(raw) < 16:
        raise ValueError("%s has an invalid pyc header" % name)
    return raw[:4].hex(), marshal.loads(raw[16:])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Probe TS4 bytecode symbols used by Sims Companion Bridge")
    parser.add_argument("--simulation-zip", required=True)
    args = parser.parse_args(argv)

    if sys.version_info[:2] != (3, 7):
        print("[FAIL] probe must run under CPython 3.7; got %s.%s" % sys.version_info[:2])
        return 2

    path = os.path.abspath(args.simulation_zip)
    failures = []
    magics = set()

    try:
        archive = zipfile.ZipFile(path, "r")
    except Exception as exc:
        print("[FAIL] cannot open simulation.zip: %s" % exc)
        return 2

    with archive:
        names = set(archive.namelist())
        modules = sorted(set(REQUIRED_CODE_OBJECTS) | set(REQUIRED_REFERENCES))
        for module in modules:
            if module not in names:
                failures.append("missing module: %s" % module)
                continue
            try:
                magic, root = _load_code(archive, module)
            except Exception as exc:
                failures.append("cannot inspect %s: %s" % (module, exc))
                continue
            magics.add(magic)
            code_objects = list(_walk(root))
            code_names = set(item.co_name for item in code_objects)
            referenced_names = set()
            for item in code_objects:
                referenced_names.update(item.co_names)

            for symbol in REQUIRED_CODE_OBJECTS.get(module, ()):
                if symbol not in code_names:
                    failures.append("%s missing code object %s" % (module, symbol))
            for symbol in REQUIRED_REFERENCES.get(module, ()):
                if symbol not in referenced_names:
                    failures.append("%s missing reference %s" % (module, symbol))

    if len(magics) == 1:
        print("[PASS] bytecode magic=%s" % next(iter(magics)))
    else:
        failures.append("mixed or missing bytecode magic: %r" % sorted(magics))

    if failures:
        for failure in failures:
            print("[FAIL] " + failure)
        print("COMPAT=NOT_READY")
        return 1

    print("[PASS] required bridge symbols are present")
    print("COMPAT=SOURCE_COMPATIBLE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
