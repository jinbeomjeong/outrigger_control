"""C2 load baseline of the pressure diagnosis (``s6_control_spec.md`` rev. 28, 110.1).

D5 (load sum) and E-5 (drift) compare against a load baseline stored in READY / DONE after
0.5 s without commands, never against the TOUCH-end GE1' reference. Synthetic readings as in
``test_c2_r6.py``: strokes follow the commands, a level accelerometer, a still gyro and the
rod-side synthesis; the crawler carries part of the weight until LEVEL starts.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace

import numpy as np
import pytest

from outrigger_sim.control.c2 import (
    C2Config,
    C2Controller,
    C2Geometry,
    C2Phase,
    ContactJudge,
    TargetSettings,
)
from outrigger_sim.params import load_params
from outrigger_sim.sensors.rod_side import RodSideParams, RodSideSynth
from outrigger_sim.signals import Measurements

GRAVITY_M_S2 = 9.80665
PERIOD_S = 0.02
FREE_AIR_S = 5.0
TOUCH_LOAD_N = 30e3
"""Leg load while the crawler still carries the rest (the TOUCH end of spec 110.1)."""
LEG_LOAD_N = 95e3
"""Leg load once the legs carry the machine (LEVEL onwards)."""
TIME_LIMIT_S = 150.0
SUM_WARNINGS = ("WARN_LOAD_SUM_MISMATCH", "WARN_PRESSURE_DRIFT")


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


@dataclass
class _Bench:
    """Readings from the controller's own commands; ``extra_load_N`` adds to every leg."""

    controller: C2Controller
    geometry: C2Geometry
    synth: RodSideSynth
    """Head and rod-side pressures of the 7.4 synthesis (a rod side that behaves like the
    circuit while the legs move, so D2 / D3 stay quiet)."""
    extra_load_N: Callable[[_Bench], np.ndarray] | None = None
    t_s: float = 0.0
    is_carrying: bool = False
    travel_m: np.ndarray = field(default_factory=lambda: np.zeros(4))
    last_command: np.ndarray = field(default_factory=lambda: np.zeros(4))
    ringing_start_s: float | None = None
    """Start of the heave ringing of :func:`_heave_ringing` (READY entry or last command)."""

    def loads(self) -> np.ndarray:
        if self.controller.phase is C2Phase.LEVEL:
            self.is_carrying = True
        if self.t_s < FREE_AIR_S:
            base = np.zeros(4)
        else:
            base = np.full(4, LEG_LOAD_N if self.is_carrying else TOUCH_LOAD_N)
        if self.extra_load_N is not None:
            base = base + self.extra_load_N(self)
        return base

    def step(self) -> None:
        self.t_s += PERIOD_S
        geometry = self.geometry
        strokes = (geometry.pad_bottom_z_retracted_m - geometry.crawler_bottom_z_m + 0.05
                   + self.travel_m)
        head, rod = self.synth.update(self.loads(), self.last_command, strokes)
        measurements = Measurements(
            t_s=self.t_s,
            specific_force_m_s2=np.array([0.0, 0.0, GRAVITY_M_S2]),
            angular_rate_rad_s=np.zeros(3),
            head_pressure_Pa=head,
            stroke_m=strokes,
            stroke_corrected_m=strokes,
            rod_pressure_Pa=rod,
        )
        self.last_command = np.asarray(self.controller.update(measurements).leg_speed_m_s)
        self.travel_m = self.travel_m + self.last_command * PERIOD_S

    def run_until(self, is_done: Callable[[], bool]) -> None:
        while not is_done() and self.t_s < TIME_LIMIT_S:
            self.step()
        assert is_done()

    def run_for(self, duration_s: float) -> None:
        for _ in range(round(duration_s / PERIOD_S)):
            self.step()


def _bench(geometry, contact=ContactJudge.COMBINED, extra_load_N=None) -> _Bench:
    config = C2Config(target=TargetSettings(check_time_s=0.0), output_ramp_time_s=None,
                      contact=contact)
    synth = RodSideSynth(RodSideParams(), geometry.head_area_m2, geometry.annulus_area_m2,
                         geometry.stroke_max_m, geometry.oil_dead_length_m, PERIOD_S)
    return _Bench(C2Controller(geometry, config), geometry, synth, extra_load_N)


def _sum_warnings(controller: C2Controller) -> list[str]:
    return [event.name for event in controller.events if event.name in SUM_WARNINGS]


def _load_reference(controller: C2Controller) -> list[dict]:
    return controller.meta()["two_pressure"]["load_reference"]


def test_touch_to_ready_raises_no_load_sum_warning(geometry) -> None:
    """110.1: the TOUCH end (crawler carrying, sum 120 kN) is no baseline; READY (380 kN)
    stores its own after the commands rest 0.5 s."""
    bench = _bench(geometry)
    bench.run_until(lambda: bench.controller.phase is C2Phase.READY)
    bench.run_for(5.0)
    controller = bench.controller
    assert _sum_warnings(controller) == []
    stores = _load_reference(controller)
    assert stores and stores[-1]["source"] == "ready"
    assert stores[-1]["sum_N"] == pytest.approx(4 * LEG_LOAD_N, rel=1e-9)
    assert all(store["source"] in ("done", "ready") for store in stores)


def test_ready_tail_transient_raises_no_load_sum_warning(geometry) -> None:
    """110.1 (4): the U67 tail moves the legs in READY; a load transient while any command is
    non-zero (here -15 kN per leg, -60 kN on the sum) is not judged."""

    def transient_while_moving(bench: _Bench) -> np.ndarray:
        is_moving = bench.controller.phase is C2Phase.READY and np.any(bench.last_command)
        return np.full(4, -15e3 if is_moving else 0.0)

    bench = _bench(geometry, extra_load_N=transient_while_moving)
    bench.run_until(lambda: "ready_heave_tail" in [e.name for e in bench.controller.events])
    bench.run_for(5.0)
    assert bench.controller.meta()["lock_tail"]["count"] >= 1
    assert _sum_warnings(bench.controller) == []


def test_pressure_judge_ready_for_60_s_raises_no_drift(geometry) -> None:
    """110.1: the pressure judge has no probe, so the old READY refresh never came and E-5
    fired 30 s after READY against the TOUCH reference; now the baseline is stored anyway."""
    bench = _bench(geometry, contact=ContactJudge.PRESSURE)
    bench.run_until(lambda: bench.controller.phase is C2Phase.READY)
    bench.run_for(60.0)
    assert bench.controller.phase is C2Phase.READY
    assert _sum_warnings(bench.controller) == []
    assert _load_reference(bench.controller)[-1]["source"] == "ready"


HEAVE_HZ = 8.7
HEAVE_ZETA = 0.03
RINGING_PER_LEG_N = 0.75e3
"""+-3 kN on the sum (spec rev. 29 120), restarted at every READY entry and every command."""


def _heave_ringing(bench: _Bench) -> np.ndarray:
    """Decaying 8.7 Hz ringing on every leg from the last leg command on (READY only)."""
    if bench.controller.phase is not C2Phase.READY:
        bench.ringing_start_s = None
        return np.zeros(4)
    if np.any(bench.last_command) or bench.ringing_start_s is None:
        bench.ringing_start_s = bench.t_s
    elapsed_s = bench.t_s - bench.ringing_start_s
    omega = 2.0 * np.pi * HEAVE_HZ
    amplitude_N = RINGING_PER_LEG_N * np.exp(-HEAVE_ZETA * omega * elapsed_s)
    return np.full(4, amplitude_N * np.cos(omega * elapsed_s))


def _run_with_ringing(geometry, mean_s: float) -> tuple[_Bench, list[np.ndarray]]:
    bench = _bench(geometry, extra_load_N=_heave_ringing)
    config = bench.controller.config
    two_pressure = replace(config.two_pressure, load_reference_mean_s=mean_s)
    bench.controller = C2Controller(geometry, replace(config, two_pressure=two_pressure))
    commands = []
    ready_since_s = None
    while bench.t_s < TIME_LIMIT_S and (ready_since_s is None or bench.t_s < ready_since_s + 5.0):
        bench.step()
        commands.append(bench.last_command.copy())
        if ready_since_s is None and bench.controller.phase is C2Phase.READY:
            ready_since_s = bench.t_s
    assert ready_since_s is not None
    return bench, commands


def test_baseline_mean_keeps_the_commands_and_the_store_times(geometry) -> None:
    """120 / 129 ②: the baseline mean is diagnosis only, so on the same heave ringing the
    commands are bit for bit those of the one-sample baseline and the stores fall on the same
    periods; the mean lands nearer the ringing-free sum."""
    mean_bench, mean_commands = _run_with_ringing(geometry, 0.5)
    single_bench, single_commands = _run_with_ringing(geometry, PERIOD_S)
    assert len(mean_commands) == len(single_commands)
    for mean_command, single_command in zip(mean_commands, single_commands, strict=True):
        np.testing.assert_array_equal(mean_command, single_command)
    mean_stores = _load_reference(mean_bench.controller)
    single_stores = _load_reference(single_bench.controller)
    assert [s["t_s"] for s in mean_stores] == [s["t_s"] for s in single_stores]
    assert mean_stores[-1]["sample_count"] == 25 and single_stores[-1]["sample_count"] == 1
    assert abs(mean_stores[-1]["sum_N"] - 4 * LEG_LOAD_N) <= 0.5e3


def test_r8_diagnostics_preset_touches_only_the_pressure_diagnosis() -> None:
    """126 #3: ``with_r8_diagnostics`` swaps in the 10 Hz constants and nothing else."""
    config = C2Config()
    r8 = config.with_r8_diagnostics()
    assert r8.two_pressure == config.two_pressure.with_r8_period()
    assert replace(r8, two_pressure=config.two_pressure) == config


def test_load_step_in_ready_after_the_baseline_warns_once(geometry) -> None:
    """D5 still works: -15 kN per leg (sum -60 kN, beyond 4 F_band + 2.5 kN with the 13 kN
    starting band) 2 s after the baseline -> one ``WARN_LOAD_SUM_MISMATCH`` with its meta."""
    def step_after_baseline(bench: _Bench) -> np.ndarray:
        ready_stores = [s for s in _load_reference(bench.controller) if s["source"] == "ready"]
        is_stepped = bool(ready_stores) and bench.t_s >= ready_stores[0]["t_s"] + 2.0
        return np.full(4, -15e3 if is_stepped else 0.0)

    bench = _bench(geometry, contact=ContactJudge.PRESSURE, extra_load_N=step_after_baseline)
    bench.run_until(lambda: bench.controller.phase is C2Phase.READY)
    bench.run_for(10.0)
    controller = bench.controller
    assert _sum_warnings(controller).count("WARN_LOAD_SUM_MISMATCH") == 1
    logged = controller.meta()["two_pressure"]["load_sum_events"]
    assert logged[0]["event"] == "WARN_LOAD_SUM_MISMATCH"
    assert logged[0]["sum_N"] - logged[0]["reference_sum_N"] == pytest.approx(-60e3, abs=1.0)
    assert logged[0]["allowed_N"] > 0.0
