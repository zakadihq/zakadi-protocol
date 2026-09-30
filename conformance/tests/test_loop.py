"""The reference control loop of spec 05-sdk-contract.md 5.6 and the vectors/loop/ traces it
yields, which the checker holds to it (01-protocol.md 1.12, 05 5.16, D33, D95, D129, D130, D132)."""

import json
import math
import shutil
from pathlib import Path

import pytest

from zakadi_conformance.check import run_checks
from zakadi_conformance.examples import _loop_trace, _pings, _ticks
from zakadi_conformance.loop import Loop, replay
from zakadi_conformance.vectors import generate, loop_traces

TRACES = {trace["name"]: trace for trace in loop_traces()}


def run(start_rung, *runs, profile="webcodecs", loop=Loop, **inputs) -> dict:
    """What the loop yields over ticks built from runs of (count, queued_bytes, drained_bytes_1s,
    encoded_kbps_2s), with the other inputs given."""
    trace = _loop_trace("unit", "", profile, start_rung, _ticks(*runs), **inputs)
    return replay(trace, loop).expect


def rungs(expect: dict) -> list[tuple[int, int, str]]:
    return [(r["t_ms"], r["rung"], r["reason"]) for r in expect["rungs"]]


def decimation(expect: dict) -> list[tuple[int, int]]:
    return [(d["t_ms"], d["decimation"]) for d in expect["decimation"]]


# Readings of 5.6 other than the reference's, each of which a trace tells apart from it.


class NoDrainFloor(Loop):
    def drain_floor(self):
        return 1.0


class FullRateDrainFloor(Loop):
    def drain_floor(self):
        return 2 * super().drain_floor()


class NoRxSignal(Loop):
    def on_ping(self, t, rtt_ms, rx_kbps):
        super().on_ping(t, rtt_ms, None)


class NoRttSignal(Loop):
    def on_ping(self, t, rtt_ms, rx_kbps):
        super().on_ping(t, None, rx_kbps)


class RxTestedOnArrival(Loop):
    """07 7.6: an rx sample is judged when it arrives, against the last tick's encoded rate."""

    last_encoded = 0.0

    def on_tick(self, t, queued, drained, encoded_kbps):
        self.last_encoded = encoded_kbps
        return super().on_tick(t, queued, drained, encoded_kbps)

    def on_ping(self, t, rtt_ms, rx_kbps):
        low = rx_kbps is not None and rx_kbps < 0.8 * self.last_encoded
        super().on_ping(
            t, rtt_ms, None if rx_kbps is None else (0.0 if low else math.inf)
        )


class TimersRunOn(Loop):
    """07 7.6: the secondary signals' timers do not restart after a downshift."""

    def timers_start(self):
        return -math.inf


class SkippedTicksCount(Loop):
    KEYFRAME_SKIP_MS = 0


class SkippedTicksReset(Loop):
    def on_tick(self, t, queued, drained, encoded_kbps):
        if self.skipped(t):
            self.over600 = self.floor_ticks = 0
        return super().on_tick(t, queued, drained, encoded_kbps)


class NoDownshiftGuard(Loop):
    DOWN_GUARD_MS = 0


class NoEmergencyGuard(Loop):
    EMERGENCY_GUARD_MS = 0


class TwoRttSamples(Loop):
    """06 6.2.8's rttStable, which one sample satisfies."""

    RTT_MIN_SAMPLES = 1


class OverrideStopsTheCounts(Loop):
    """07 7.6: ticks under a set_rung override neither count nor reset."""

    def skipped(self, t):
        return super().skipped(t) or t < self.override_until


class FloorCountsTheStep(Loop):
    """06 6.2.8 before D130: the tick that steps down to rung 4 counts."""

    def counts_toward_floor(self, start, queue_ms):
        return super().counts_toward_floor(self.rung, queue_ms)


class MediarecorderHonoursKeyframes(Loop):
    def on_keyframe_request(self, t):
        self.last_request_at = t


# Step 1


def test_the_drain_is_floored_at_half_the_rungs_video_rate():
    # rung 2 has 400 kbps of video: the floor is 25000 bytes per second
    trace = _loop_trace(
        "unit", "", "webcodecs", 2, _ticks((1, 10000, 0, 424), (1, 10000, 40000, 424))
    )
    assert replay(trace).queue_ms == [(200, 400.0), (400, 250.0)]
    assert replay(trace, NoDrainFloor).queue_ms[0] == (200, 10_000_000.0)


def test_rx_below_0_8_times_the_encoded_rate_for_2_s_counts_as_queue_ms_above_600():
    expect = run(2, (15, 15000, 50000, 424), pings=_pings([(190, 150)] * 3))
    assert rungs(expect) == [(2400, 3, "backpressure")]
    assert rungs(run(2, (15, 15000, 50000, 424), pings=_pings([(190, 350)] * 3))) == []


def test_rtt_above_twice_its_session_median_for_2_s_counts_as_queue_ms_above_600():
    pings = _pings([(190, None)] * 4 + [(900, None)] * 3)
    assert rungs(run(2, (35, 15000, 50000, 424), pings=pings)) == [
        (6400, 3, "backpressure")
    ]


def test_the_secondary_signals_restart_their_timers_after_a_downshift():
    runs = (30, 15000, 50000, 424)
    pings = _pings([(190, 150)] * 6)
    assert rungs(run(2, runs, pings=pings)) == [
        (2400, 3, "backpressure"),
        (5400, 4, "backpressure"),
    ]
    assert rungs(run(2, runs, pings=pings, loop=TimersRunOn))[1][0] == 3400


# Step 2


def test_a_tick_within_300_ms_of_a_keyframe_request_is_skipped_and_holds_the_count():
    runs = (3, 35000, 50000, 424)
    assert rungs(run(2, runs, keyframe_requests=[250])) == [(600, 3, "backpressure")]
    assert (
        rungs(run(2, runs, keyframe_requests=[250], loop=SkippedTicksCount))[0][0]
        == 400
    )
    assert rungs(run(2, runs, keyframe_requests=[250], loop=SkippedTicksReset)) == []


# Step 3 and D33


def test_queue_ms_above_600_on_two_ticks_steps_down_one_rung_with_decimation_1():
    expect = run(2, (2, 35000, 50000, 424))
    assert rungs(expect) == [(400, 3, "backpressure")]
    assert decimation(expect) == [(400, 1)]


def test_the_two_tick_rule_waits_1_s_after_a_downshift_while_its_count_runs():
    assert rungs(run(0, (7, 70000, 100000, 924))) == [
        (400, 1, "backpressure"),
        (1400, 2, "backpressure"),
    ]


def test_queue_ms_above_1500_steps_down_two_rungs_and_again_600_ms_after_a_downshift():
    expect = run(0, (4, 160000, 100000, 924))
    assert rungs(expect) == [(200, 2, "backpressure"), (800, 4, "backpressure")]
    assert decimation(expect) == [(200, 2)]


def test_an_upshift_needs_three_rtt_samples_within_5_s():
    runs = (25, 3000, 50000, 266)
    pings = _pings([(None, None)] * 2 + [(190, None)] * 4)  # RTT from t_ms 2100
    expect = run(3, runs, pings=pings)
    assert rungs(expect) == [(4200, 2, "headroom")]
    assert rungs(run(3, runs, pings=pings, loop=TwoRttSamples)) == [
        (3200, 2, "headroom")
    ]


def test_an_upshift_waits_3_s_at_the_rung_and_1_s_after_the_last_idr_sent():
    runs = (30, 3000, 50000, 266)
    pings = _pings([(190, None)] * 6)
    assert rungs(run(3, runs, pings=pings))[0] == (3200, 2, "headroom")
    assert rungs(run(3, runs, pings=pings, idrs=[3150]))[0] == (4200, 2, "headroom")


def test_an_upshift_clears_decimation():
    runs = ((2, 35000, 50000, 424), (25, 3000, 50000, 266))
    expect = run(2, *runs, pings=_pings([(190, None)] * 6))
    assert rungs(expect) == [(400, 3, "backpressure"), (3600, 2, "headroom")]
    assert decimation(expect) == [(400, 1), (3600, 0)]


# set_rung (D132)


def test_a_set_rung_moves_the_rung_and_withholds_step_3_for_3_s_while_the_counts_run():
    runs = ((2, 35000, 50000, 424), (20, 35000, 50000, 624))
    expect = run(2, *runs, set_rung=[(450, 1)])
    assert rungs(expect) == [
        (400, 3, "backpressure"),
        (450, 1, "server"),
        (3600, 2, "backpressure"),
    ]
    assert decimation(expect) == [(400, 1), (450, 0), (3600, 1)]
    assert (
        rungs(run(2, *runs, set_rung=[(450, 1)], loop=OverrideStopsTheCounts))[2][0]
        == 3800
    )


def test_a_set_rung_to_a_lower_rung_keeps_decimation():
    runs = ((2, 35000, 50000, 424), (3, 15000, 50000, 266))
    expect = run(2, *runs, set_rung=[(650, 4)])
    assert rungs(expect) == [(400, 3, "backpressure"), (650, 4, "server")]
    assert decimation(expect) == [(400, 1)]


# Step 6 (D130)


@pytest.mark.parametrize(
    "start,runs",
    [
        (2, [(1, 40000, 25000, 424)]),
        (3, [(1, 40000, 25000, 266)]),
        (3, [(2, 11000, 15625, 266)]),
    ],
    ids=["emergency-two-rungs", "emergency-one-rung", "two-tick-rule"],
)
def test_the_floor_breaches_on_the_15th_tick_after_the_step_down_to_rung_4(start, runs):
    expect = run(start, *runs, (20, 40000, 20000, 162))
    step = expect["rungs"][-1]
    assert step["rung"] == 4
    assert expect["floor_tick"] == step["t_ms"] + 15 * 200


def test_a_skipped_tick_holds_the_floor_count():
    expect = run(
        2, (1, 40000, 25000, 424), (20, 40000, 20000, 162), keyframe_requests=[1050]
    )
    assert expect["floor_tick"] == 200 + 16 * 200


def test_on_mediarecorder_the_recorders_rung_is_the_floor_and_keyframes_are_ignored():
    expect = run(
        2,
        (15, 50000, 25000, 424),
        profile="mediarecorder",
        set_rung=[(1150, 3)],
        keyframe_requests=[1250],
    )
    assert rungs(expect) == [(1150, 2, "server")]
    assert decimation(expect) == [(200, 2)]
    assert expect["floor_tick"] == 15 * 200


# The traces


# What each trace yields, derived by hand from 5.6, D33, D130 and D132: its rungs, its changes of
# decimation and its floor tick.
EXPECTED = {
    "drain-floor": (
        [(2400, 3, "backpressure"), (3400, 4, "backpressure")],
        [(2400, 1)],
        None,
    ),
    "rx-signal": (
        [(4400, 3, "backpressure"), (7400, 4, "backpressure")],
        [(4400, 1)],
        None,
    ),
    "rtt-signal": ([(8400, 3, "backpressure")], [(8400, 1)], None),
    "keyframe-skip": (
        [(1200, 3, "backpressure"), (2400, 4, "backpressure")],
        [(1200, 1), (2400, 2)],
        5600,
    ),
    "two-tick-guard": (
        [
            (400, 1, "backpressure"),
            (1400, 2, "backpressure"),
            (2000, 4, "backpressure"),
        ],
        [(400, 1), (2000, 2)],
        None,
    ),
    "emergency-guard": (
        [(200, 2, "backpressure"), (800, 4, "backpressure")],
        [(200, 2)],
        None,
    ),
    "upshift": (
        [(400, 3, "backpressure"), (4200, 2, "headroom"), (9200, 1, "headroom")],
        [(400, 1), (4200, 0)],
        None,
    ),
    "set-rung-override": (
        [
            (400, 3, "backpressure"),
            (1150, 1, "server"),
            (4200, 2, "backpressure"),
            (5350, 3, "server"),
        ],
        [(400, 1), (1150, 0), (4200, 1)],
        None,
    ),
    "floor-webcodecs": ([(400, 4, "backpressure")], [(400, 2)], 3400),
    "floor-mediarecorder": ([(2150, 2, "server")], [(800, 2)], 3600),
}


def test_every_trace_is_listed():
    assert sorted(TRACES) == sorted(EXPECTED)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_each_trace_expects_what_5_6_yields(name):
    expect = TRACES[name]["expect"]
    assert (rungs(expect), decimation(expect), expect["floor_tick"]) == EXPECTED[name]


MUTATIONS = [
    (NoDrainFloor, "drain-floor"),
    (FullRateDrainFloor, "drain-floor"),
    (NoRxSignal, "rx-signal"),
    (RxTestedOnArrival, "rx-signal"),
    (TimersRunOn, "rx-signal"),
    (NoRttSignal, "rtt-signal"),
    (TimersRunOn, "rtt-signal"),
    (SkippedTicksCount, "keyframe-skip"),
    (SkippedTicksReset, "keyframe-skip"),
    (NoDownshiftGuard, "two-tick-guard"),
    (NoEmergencyGuard, "two-tick-guard"),
    (NoEmergencyGuard, "emergency-guard"),
    (TwoRttSamples, "upshift"),
    (OverrideStopsTheCounts, "set-rung-override"),
    (OverrideStopsTheCounts, "floor-mediarecorder"),
    (FloorCountsTheStep, "floor-webcodecs"),
    (FloorCountsTheStep, "keyframe-skip"),
    (MediarecorderHonoursKeyframes, "floor-mediarecorder"),
]


@pytest.mark.parametrize(
    "mutation,name", MUTATIONS, ids=[m.__name__ + "-" + n for m, n in MUTATIONS]
)
def test_a_trace_tells_another_reading_of_5_6_apart(mutation, name):
    assert replay(TRACES[name], mutation).expect != TRACES[name]["expect"]


# The checker over the traces


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("generated")
    generate(root)
    return root


@pytest.fixture
def tree(generated: Path, tmp_path: Path) -> Path:
    root = tmp_path / "tree"
    shutil.copytree(generated, root)
    return root


def edit_trace(root: Path, name: str, change) -> None:
    path = root / "vectors" / "loop" / (name + ".json")
    trace = json.loads(path.read_text(encoding="ascii"))
    change(trace)
    path.write_text(json.dumps(trace, indent=2) + "\n", encoding="ascii")


def fails_with(root: Path, text: str) -> None:
    found = run_checks(root).failures
    assert any(text in f for f in found), found


def test_the_generated_traces_pass_the_checker(generated):
    assert sorted(p.stem for p in (generated / "vectors" / "loop").glob("*.json")) == (
        sorted(TRACES)
    )
    assert run_checks(generated).failures == []


@pytest.mark.parametrize(
    "key,value,want",
    [
        (
            "floor_tick",
            3200,
            "expect.floor_tick differs from the reference loop's 3400",
        ),
        (
            "rungs",
            [],
            'expect.rungs differs from the reference loop\'s [{"t_ms": 400, "rung": 4, '
            '"reason": "backpressure"}]',
        ),
        ("decimation", [{"t_ms": 400, "decimation": 1}], "expect.decimation differs"),
    ],
)
def test_a_trace_whose_expectations_differ_from_the_reference_fails(
    tree, key, value, want
):
    edit_trace(tree, "floor-webcodecs", lambda t: t["expect"].update({key: value}))
    fails_with(tree, "loop trace floor-webcodecs: " + want)


def test_a_trace_that_breaks_its_schema_fails(tree):
    edit_trace(tree, "upshift", lambda t: t["ticks"][0].pop("drained_bytes_1s"))
    fails_with(tree, "loop trace upshift does not match its schema")


def test_a_trace_named_otherwise_or_on_another_ladder_fails(tree):
    def rename(t):
        t["name"] = "other"
        t["ladder"] = t["ladder"][::-1]

    edit_trace(tree, "drain-floor", rename)
    fails_with(tree, "loop trace drain-floor: name other differs from the file name")
    fails_with(tree, "loop trace drain-floor: the ladder is not rungs 0 to 4 in order")


def test_ticks_off_the_200_ms_grid_fail(tree):
    edit_trace(tree, "emergency-guard", lambda t: t["ticks"][2].update(t_ms=610))
    fails_with(tree, "loop trace emergency-guard: ticks are not every 200 ms")


def test_an_input_sharing_a_tick_s_t_ms_fails(tree):
    edit_trace(
        tree, "keyframe-skip", lambda t: t["keyframe_requests"][0].update(t_ms=800)
    )
    fails_with(tree, "loop trace keyframe-skip: two inputs share a t_ms")


def test_a_tick_after_the_floor_tick_fails(tree):
    def one_more(t):
        last = t["ticks"][-1]
        t["ticks"].append(last | {"t_ms": last["t_ms"] + 200})

    edit_trace(tree, "floor-webcodecs", one_more)
    fails_with(
        tree, "loop trace floor-webcodecs: ticks after the floor tick at t_ms 3400"
    )


def test_a_queue_within_1_ms_of_a_threshold_fails(tree):
    # 37513 bytes over rung 2's floor of 25000 bytes per second read 1500.52 ms
    edit_trace(
        tree, "floor-webcodecs", lambda t: t["ticks"][1].update(queued_bytes=37513)
    )
    fails_with(
        tree,
        "loop trace floor-webcodecs: queue_ms 1500.52 at t_ms 400 is within 1 ms of 1500",
    )
