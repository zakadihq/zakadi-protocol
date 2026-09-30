"""The client control loop of spec 05-sdk-contract.md 5.6 as a pure function over per-tick inputs.

`replay` runs the 200 ms loop over the inputs of a `vectors/loop/*.json` trace, in t_ms order,
and returns what the trace expects of an SDK: every `rung` the client announces, every change of
decimation and the tick that sends `bye floor_breached`. It implements steps 1 to 4 and 6 of 5.6
(step 5, `stats`, runs on its own timer) as D33, D130 and D132 read them, which is 06 6.2.8 with
three RTT samples needed for an upshift:

- step 1: the drain is floored at half the rung's video rate; `ping.rx_kbps` below 0.8 x the
  tick's `encoded_kbps_2s`, or an RTT above 2 x the session median, held for 2 s by the samples
  since the last downshift, the latest no older than 1.5 s, counts as `queue_ms > 600` (D132);
- step 2: a tick within 300 ms of a keyframe request is skipped and holds every count; the
  `mediarecorder` profile ignores keyframe requests (01 1.5);
- step 3: the emergency rule, then the two-tick rule, then the upshift, with the guards of D33;
  an upshift needs three RTT samples within 5 s and the last IDR sent more than 1 s ago (D132);
- a `set_rung` moves the rung at once, clearing decimation on an upshift, and withholds step 3
  for 3 s while the counts keep running (D132); on `mediarecorder` the rung cannot change and the
  answer carries the unchanged rung (06 6.2.7);
- step 6: the ticks that begin at the floor rung (rung 4, or the recorder's rung on
  `mediarecorder`) with `queue_ms` above 1500 are counted, and the 15th breaches (D130).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import NamedTuple

TICK_MS = 200


class Replay(NamedTuple):
    """What the loop yields over a trace: its `expect` object, and the queue_ms of every tick."""

    expect: dict
    queue_ms: list[tuple[int, float]]


def _upper_median(values: list[float]) -> float | None:
    """The median as 06 6.2.8 and 07 7.6 take it: the upper middle value of an even count."""
    return sorted(values)[len(values) // 2] if values else None


class Loop:
    """The loop's state of 5.6 and its rules, one method each; t_ms 0 is where it starts."""

    QUEUE_EMERGENCY_MS = 1500
    QUEUE_HIGH_MS = 600
    QUEUE_LOW_MS = 150
    KEYFRAME_SKIP_MS = 300
    EMERGENCY_GUARD_MS = 600  # D33
    DOWN_GUARD_MS = 1000  # D33
    SIGNAL_HOLD_MS = 2000
    SIGNAL_FRESH_MS = 1500
    RTT_WINDOW_MS = 5000
    RTT_MIN_SAMPLES = 3  # D132
    DWELL_MS = 3000
    KEYFRAME_GUARD_MS = 1000
    OVERRIDE_MS = 3000
    FLOOR_TICKS = 15  # D130

    def __init__(self, profile: str, ladder: list[dict], start_rung: int) -> None:
        self.ladder = ladder
        self.top = len(ladder) - 1
        self.can_change = profile != "mediarecorder"
        self.floor_rung = self.top if self.can_change else start_rung
        self.rung = start_rung
        self.decimation = 0
        self.dwell_start = 0
        self.last_down_at = -math.inf
        self.last_idr_at = -math.inf
        self.last_request_at = -math.inf
        self.override_until = -math.inf
        self.over600 = 0
        self.floor_ticks = 0
        self.rtt: list[tuple[int, float]] = []
        self.rx: list[tuple[int, float]] = []
        self.rungs: list[dict] = []
        self.decimations: list[dict] = []
        self.floor_tick: int | None = None

    # Inputs other than ticks.

    def on_ping(self, t: int, rtt_ms: float | None, rx_kbps: float | None) -> None:
        if rtt_ms is not None:
            self.rtt.append((t, rtt_ms))
        if rx_kbps is not None:
            self.rx.append((t, rx_kbps))

    def on_keyframe_request(self, t: int) -> None:
        if self.can_change:  # 01 1.5: clients on mediarecorder ignore keyframe
            self.last_request_at = t

    def on_idr(self, t: int) -> None:
        self.last_idr_at = t

    def on_set_rung(self, t: int, rung: int) -> None:
        self.override_until = t + self.OVERRIDE_MS
        to = rung if self.can_change else self.rung
        if to < self.rung:
            self.set_decimation(t, 0)
        if to != self.rung:
            self.rung = to
            self.dwell_start = t
        self.rungs.append({"t_ms": t, "rung": self.rung, "reason": "server"})

    # The tick.

    def on_tick(self, t: int, queued: int, drained: int, encoded_kbps: float) -> float:
        queue_ms = 1000 * queued / max(drained, self.drain_floor())
        if self.skipped(t):
            return queue_ms
        start = self.rung
        congested = queue_ms > self.QUEUE_HIGH_MS or self.hidden(t, encoded_kbps)
        self.over600 = self.over600 + 1 if congested else 0
        if t >= self.override_until:
            self.step3(t, queue_ms)
        if self.counts_toward_floor(start, queue_ms):
            self.floor_ticks += 1
        else:
            self.floor_ticks = 0
        if self.floor_ticks >= self.FLOOR_TICKS:
            self.floor_tick = t
        return queue_ms

    def drain_floor(self) -> float:
        """Step 1: bytes per second, half the rung's video rate."""
        return self.ladder[self.rung]["video_kbps"] * 125 / 2

    def skipped(self, t: int) -> bool:
        """Step 2."""
        return t - self.last_request_at < self.KEYFRAME_SKIP_MS

    def hidden(self, t: int, encoded_kbps: float) -> bool:
        """Step 1's secondary signals, tested on every tick (D132)."""
        if self.held(self.rx, t, lambda kbps: kbps < 0.8 * encoded_kbps):
            return True
        median = _upper_median([ms for _, ms in self.rtt])
        if median is None:
            return False
        limit = 2 * median
        return self.held(self.rtt, t, lambda ms: ms > limit)

    def timers_start(self) -> float:
        """The secondary signals' timers restart at the last downshift (D132)."""
        return self.last_down_at

    def held(
        self, samples: list[tuple[int, float]], t: int, bad: Callable[[float], bool]
    ) -> bool:
        """The samples since the timers started end in a run of bad ones that began 2 s ago or
        more, and the latest sample is fresh."""
        start = self.timers_start()
        since: int | None = None
        for at, value in samples:
            if at >= start:
                since = (at if since is None else since) if bad(value) else None
        return (
            since is not None
            and t - since >= self.SIGNAL_HOLD_MS
            and t - samples[-1][0] <= self.SIGNAL_FRESH_MS
        )

    def rtt_stable(self, t: int) -> bool:
        """The latest RTT within 20 percent of the median of the last 5 s, over three samples or
        more (D132)."""
        recent = [ms for at, ms in self.rtt if t - at <= self.RTT_WINDOW_MS]
        median = _upper_median(recent)
        return (
            len(recent) >= self.RTT_MIN_SAMPLES
            and median is not None
            and abs(recent[-1] - median) <= 0.2 * median
        )

    def step3(self, t: int, queue_ms: float) -> None:
        since_down = t - self.last_down_at
        to, decimation, reason = self.rung, self.decimation, "backpressure"
        if queue_ms > self.QUEUE_EMERGENCY_MS and since_down >= self.EMERGENCY_GUARD_MS:
            to, decimation = min(self.rung + 2, self.top), 2
        elif self.over600 >= 2 and since_down >= self.DOWN_GUARD_MS:
            to, decimation = min(self.rung + 1, self.top), max(decimation, 1)
        elif (
            queue_ms < self.QUEUE_LOW_MS
            and self.rtt_stable(t)
            and t - self.dwell_start > self.DWELL_MS
            and t - self.last_idr_at > self.KEYFRAME_GUARD_MS
            and self.rung > 0
        ):
            to, decimation, reason = self.rung - 1, 0, "headroom"
        self.set_decimation(t, decimation)
        if to != self.rung and self.can_change:
            # a downshift resets the count and restarts the timers (D33, D132)
            if to > self.rung:
                self.last_down_at = t
                self.over600 = 0
            self.rung = to
            self.dwell_start = t
            self.rungs.append({"t_ms": t, "rung": to, "reason": reason})

    def counts_toward_floor(self, start: int, queue_ms: float) -> bool:
        """Step 6: the tick began at the floor rung, so the step down to it does not count (D130)."""
        return start == self.floor_rung and queue_ms > self.QUEUE_EMERGENCY_MS

    def set_decimation(self, t: int, decimation: int) -> None:
        if decimation != self.decimation:
            self.decimation = decimation
            self.decimations.append({"t_ms": t, "decimation": decimation})


def replay(trace: dict, loop: type[Loop] = Loop) -> Replay:
    """Runs the loop over the trace's inputs in t_ms order, an input other than a tick first at
    equal t_ms, until the floor breaches or the ticks end."""
    state = loop(trace["profile"], trace["ladder"], trace["start_rung"])
    inputs = sorted(
        [(p["t_ms"], 0, "ping", p) for p in trace["pings"]]
        + [(k["t_ms"], 0, "keyframe", k) for k in trace["keyframe_requests"]]
        + [(i["t_ms"], 0, "idr", i) for i in trace["idrs"]]
        + [(s["t_ms"], 0, "set_rung", s) for s in trace["set_rung"]]
        + [(tk["t_ms"], 1, "tick", tk) for tk in trace["ticks"]],
        key=lambda item: (item[0], item[1]),
    )
    queue: list[tuple[int, float]] = []
    for t, _, kind, item in inputs:
        if kind == "ping":
            state.on_ping(t, item["rtt_ms"], item["rx_kbps"])
        elif kind == "keyframe":
            state.on_keyframe_request(t)
        elif kind == "idr":
            state.on_idr(t)
        elif kind == "set_rung":
            state.on_set_rung(t, item["rung"])
        else:
            queue_ms = state.on_tick(
                t,
                item["queued_bytes"],
                item["drained_bytes_1s"],
                item["encoded_kbps_2s"],
            )
            queue.append((t, queue_ms))
        if state.floor_tick is not None:
            break
    expect = {
        "rungs": state.rungs,
        "decimation": state.decimations,
        "floor_tick": state.floor_tick,
    }
    return Replay(expect, queue)
