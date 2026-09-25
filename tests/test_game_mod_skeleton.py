import importlib.util
import threading
from pathlib import Path

from sims_companion_bridge.validation import validate_game_event


ROOT = Path(__file__).resolve().parents[1]


def load_game_module(filename, module_name):
    path = ROOT / "game-mod" / "src" / "sims_companion_bridge" / filename
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_bridge_class():
    return load_game_module("bridge.py", "game_bridge").ReadOnlyBridge


def test_read_only_bridge_bounds_queue_and_drains_json():
    bridge = load_bridge_class()("world")
    event = bridge.publish_snapshot("Demo Zone", "home", "available")
    assert event["type"] == "game.snapshot"
    assert len(bridge.drain_json()) == 1
    assert bridge.drain_json() == []



def test_read_only_bridge_rejects_non_protocol_identifiers():
    bridge_class = load_bridge_class()
    for invalid in ("world with spaces", "", "x" * 65):
        try:
            bridge_class(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid world_id was accepted: %r" % invalid)


def test_fixture_observation_normalizes_to_gateway_contract():
    module = load_game_module("bridge.py", "game_bridge_normalize")
    observation = {
        "save_slot_id": "slot-1",
        "zone": {"zone_id": "zone-9", "name": "Z" * 400},
        "simulation": {"sim_time": "Day 3, 08:10", "in_build_buy": False},
        "player": {
            "sim_id": "sim-1", "name": "Test Sim",
            "mood": {"name": "Happy", "intensity": float("nan")},
            "needs": {"hunger": float("inf"), "energy": 150},
            "interactions": {"running": ["Cook"], "queued": ["x" * 300] * 30},
        },
        "present_sims": [
            {"sim_id": "sim-{}".format(index), "name": "Present " + str(index)}
            for index in range(45)
        ],
    }
    event = module.ReadOnlyBridge("fixture-world").publish_snapshot(
        observation, event_id="evt-normalized", wallclock_unix=1700000000
    )
    clean = validate_game_event(event)
    assert len(clean["payload"]["zone"]["name"]) == 256
    assert clean["payload"]["player"]["mood"]["intensity"] is None
    assert clean["payload"]["player"]["needs"]["hunger"] is None
    assert clean["payload"]["player"]["needs"]["energy"] == 100
    assert len(clean["payload"]["present_sims"]) == 40


def test_ts4_reader_is_lazy_and_each_field_fails_soft():
    reader = load_game_module("ts4_reader.py", "game_ts4_reader")
    assert reader.read_observation(services_module=None)["player"] is None

    class BrokenClockNow(object):
        def hour(self):
            return 12

        def minute(self):
            raise RuntimeError("patch-specific API changed")

        def __str__(self):
            return "fallback-time"

    class Clock(object):
        def now(self):
            return BrokenClockNow()

    class Lot(object):
        name = "Fixture Lot"

    class Zone(object):
        id = 42
        lot = Lot()
        is_in_build_buy = False

        @property
        def name(self):
            raise AttributeError("name unavailable")

    class FocusedMood(object):
        pass

    class HungerCommodity(object):
        min_value = -100
        max_value = 100
        stat_type = type("HungerNeed", (), {})

        def get_value(self):
            return 0

    class SimInfo(object):
        sim_id = 1001
        first_name = "Fixture"
        last_name = "Sim"
        commodity_tracker = [HungerCommodity()]

        def get_mood(self):
            return FocusedMood()

        def get_mood_intensity(self):
            raise RuntimeError("optional API unavailable")

        def get_sim_instance(self):
            return None

    sim_info = SimInfo()

    class SimInstance(object):
        def __init__(self, info):
            self.sim_info = info

        def is_on_active_lot(self):
            return True

    class Manager(object):
        def get(self, _sim_id):
            raise KeyError("not loaded")

        def instanced_sims_gen(self):
            return iter([SimInstance(sim_info)])

    class Persistence(object):
        def get_save_slot_proto_guid(self):
            raise AttributeError("not on this patch")

    class Services(object):
        def active_sim_info(self):
            return sim_info

        def current_zone(self):
            return Zone()

        def game_clock_service(self):
            return Clock()

        def sim_info_manager(self):
            return Manager()

        def get_persistence_service(self):
            return Persistence()

    observation = reader.read_observation("2002", Services())
    assert observation["zone"] == {"zone_id": "42", "name": "Fixture Lot"}
    assert observation["simulation"] == {"sim_time": "fallback-time", "in_build_buy": False}
    assert observation["player"]["name"] == "Fixture Sim"
    assert observation["player"]["mood"]["intensity"] is None
    assert observation["player"]["needs"]["hunger"] == 50.0
    assert observation["companion"] is None
    assert observation["present_sims"] == [{"sim_id": "1001", "name": "Fixture Sim"}]


def test_ts4_reader_keeps_running_and_queued_interactions_separate():
    reader = load_game_module("ts4_reader.py", "game_ts4_reader_interactions")

    class RunningSuper(object):
        pass

    class RunningMixer(object):
        pass

    class QueuedInteraction(object):
        pass

    running_super = type("Interaction", (), {"affordance": RunningSuper})()
    running_mixer = type("Interaction", (), {"affordance": RunningMixer})()
    queued = type("Interaction", (), {"affordance": QueuedInteraction})()

    class Queue(object):
        running = running_super

        def __iter__(self):
            return iter([running_super, queued])

    class SIState(object):
        def sis_actor_gen(self):
            return iter([running_mixer])

    class Sim(object):
        queue = Queue()
        si_state = SIState()

    class SimInfo(object):
        def get_sim_instance(self):
            return Sim()

    assert reader._read_interactions(SimInfo()) == {
        "running": ["RunningSuper", "RunningMixer"],
        "queued": ["QueuedInteraction"],
    }


def test_event_worker_is_bounded_daemon_with_explicit_stop():
    transport_module = load_game_module("transport.py", "game_transport_worker")
    delivered = threading.Event()

    class FakeTransport(object):
        def post_event(self, event):
            delivered.set()
            return True, {"event_id": event["event_id"]}

    worker = transport_module.EventWorker(FakeTransport(), max_queue=2)
    worker.start()
    assert worker._thread.daemon is True
    assert worker.submit({"event_id": "evt-worker"}) is True
    assert delivered.wait(2)
    assert worker.stop(2) is True
    assert worker.last_result == (True, {"event_id": "evt-worker"})
