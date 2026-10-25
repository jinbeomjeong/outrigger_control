"""P-S8-13 locked fallback estimate of ``control/two_pressure`` (hydraulics H-S8-2,
``00_docs/02_hydraulic/s8_seal_friction_counterbalance.md`` 10.4).

T7: synthetic lock-law generator (the L2b lock law of 10.1) over lock strokes, dead lengths,
lift-off, floor entry and return, a lock at the end of the valve-lag window and ``tau_v = 0``.
T8: the ``"fixed"`` rule is the estimate before P-S8-13; without a fallback leg the readings do
not depend on the rule. Monitors and settings pickled before P-S8-13 (ML ``branch.pkl``).
T1-T3, T6: record replays of ``07_results/S8`` (git-ignored; skipped without it) with the leg
forced to fallback, the same inputs as ``04_scripts/04_hydraulic/s8_cb/h_s8_2_lock_ratio.py``:
``record/record.npz`` ``meas.*``, ``r8_series.npz`` ``issued_u`` one period late, the true
pressure force of ``pads.npz`` at the sample instant.
"""

from __future__ import annotations

import copy
import json
import math
import pickle
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from outrigger_sim.control.two_pressure import (
    COLUMN_BOUND_META_KEYS,
    LoadEstimate,
    LockedRatioRule,
    RodSensorState,
    TwoPressureMonitor,
    TwoPressureSettings,
)
from outrigger_sim.signals import Measurements

BAR = 1e5
PERIOD_S = 0.1
HEAD_AREA = np.array([1.3273229e-2, 1.3273229e-2, 9.50331778e-3, 9.50331778e-3])
ANNULUS = np.array([3.76991118e-3, 3.76991118e-3, 3.14159265e-3, 3.14159265e-3])
ROD_WEIGHT_N = np.array([1047.19, 1047.19, 717.48, 717.48])
V_MAX = 0.020924
F_MIN_N = 9414.59
STROKE_MAX_M = 0.70
FLOOR_PA = 1.0e4 - 1.01325e5
"""Rod-side floor 0.1 bar absolute as gauge."""
OPTIMISM_LIMIT_N = 600.0
"""10.4 test criterion: the lower bound may lie at most 0.6 kN above the true force."""
FR = 1
GRAVITY_M_S2 = 9.80665

RESULTS = Path(__file__).resolve().parents[2] / "07_results" / "S8"
P1R = RESULTS / "p1r_20261024_222013"
CB = RESULTS / "cb_20261025_000840"
ML_EPISODES = RESULTS / "ml_pilot_20261025_002044" / "episodes"
ML_OLD_EPISODES = sorted(ML_EPISODES.glob("_replaced_*")) if ML_EPISODES.is_dir() else []
ML_BASES = sorted((RESULTS / "ml_pilot_20261025_002044").glob("bases/ML*/branch.pkl"))


def _monitor(settings: TwoPressureSettings | None = None) -> TwoPressureMonitor:
    settings = settings or TwoPressureSettings().with_r8_period()
    return TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN_N, PERIOD_S, settings=settings,
                              rod_weight_N=ROD_WEIGHT_N, stroke_max_m=STROKE_MAX_M)


# --- T7: synthetic lock law -----------------------------------------------------------------


@dataclass(frozen=True)
class LockedLeg:
    """L2b lock law of one leg (10.1): ``p_r = max(floor, p_r0 - r (F - F_lock) / A_ann)``,
    ``p_h = (F + p_r A_ann) / A_p``, ``r / (1 - r) = R A_ann / A_p``,
    ``R = (L_0h + s) / (L_0r + s_max - s)``."""

    stroke_m: float
    rod_dead_m: float
    head_dead_m: float
    lock_force_N: float
    p_r0_Pa: float
    leg: int = FR

    @property
    def ratio(self) -> float:
        head_column_m = self.head_dead_m + self.stroke_m
        return head_column_m / (self.rod_dead_m + STROKE_MAX_M - self.stroke_m)

    def pressures(self, force_N: float) -> tuple[float, float]:
        area_head, area_rod = HEAD_AREA[self.leg], ANNULUS[self.leg]
        x = self.ratio * area_rod / area_head
        share = x / (1.0 + x)
        rod_Pa = max(FLOOR_PA, self.p_r0_Pa - share * (force_N - self.lock_force_N) / area_rod)
        return (force_N + rod_Pa * area_rod) / area_head, rod_Pa


def _moving_pressures(leg: LockedLeg, force_N: float) -> tuple[float, float]:
    """A leg still moving (before the plant lock): rod side at its start value."""
    rod_Pa = leg.p_r0_Pa
    return (force_N + rod_Pa * ANNULUS[leg.leg]) / HEAD_AREA[leg.leg], rod_Pa


def _run_synthetic(leg: LockedLeg, command_m_s: float, move_forces_N, window_forces_N,
                   locked_forces_N, settings: TwoPressureSettings | None = None):
    """Feed a fallback leg: moving samples, command-free samples before the plant lock
    (still moving, valve lag), then the locked samples. Returns (estimates, true rod)."""
    monitor = _monitor(settings)
    monitor.rod_state[leg.leg] = RodSensorState.FALLBACK
    samples = [(command_m_s, *_moving_pressures(leg, f)) for f in move_forces_N]
    samples += [(0.0, *_moving_pressures(leg, f)) for f in window_forces_N]
    samples += [(0.0, *leg.pressures(f)) for f in locked_forces_N]
    estimates, truth = [], []
    for k, (command, head_Pa, rod_Pa) in enumerate(samples):
        commanded = np.zeros(4)
        commanded[leg.leg] = command
        head = np.full(4, 80 * BAR)
        rod = np.full(4, 5 * BAR)
        head[leg.leg], rod[leg.leg] = head_Pa, rod_Pa
        stroke = np.full(4, 0.3)
        stroke[leg.leg] = leg.stroke_m
        monitor.read(k * PERIOD_S, head, rod, commanded, False, 2e3, stroke_m=stroke)
        estimates.append(monitor._legs[leg.leg].rod_estimate_Pa)
        truth.append(rod_Pa)
    return np.array(estimates), np.array(truth)


def _ramp(start: float, end: float, count: int) -> list[float]:
    return list(np.linspace(start, end, count))


@pytest.mark.parametrize("stroke_m", [0.05, 0.40, 0.66])
@pytest.mark.parametrize("rod_dead_m", [0.02, 0.10])
@pytest.mark.parametrize("head_dead_m", [0.05, 0.08])
def test_t7_lift_off_after_a_lock_is_bounded(stroke_m, rod_dead_m, head_dead_m) -> None:
    """Locked after an extension (2 bar), the load falls to lift-off (``-m_rod g``)."""
    lock_N = 118.1e3
    leg = LockedLeg(stroke_m, rod_dead_m, head_dead_m, lock_N, 2 * BAR)
    lift_off_N = -ROD_WEIGHT_N[FR]
    estimates, truth = _run_synthetic(
        leg, 0.5 * V_MAX, [lock_N] * 5, [], [lock_N] * 3 + _ramp(lock_N, lift_off_N, 10)
        + [lift_off_N] * 5)
    assert np.all(estimates >= truth - 1e-6)


def test_t7_lift_off_after_the_travel_limit_lock_reaches_452_bar() -> None:
    """10.2 table 3: front 0.60 m, ``L_0r`` 0.02 m, locked at 278.7 kN (210 bar head) ->
    the rod side reaches about 452 bar at lift-off; no lift-off cap (10.4 ⑥)."""
    lock_N = 278.7e3
    leg = LockedLeg(0.60, 0.02, 0.05, lock_N, 2 * BAR)
    estimates, truth = _run_synthetic(
        leg, 0.5 * V_MAX, [lock_N] * 5, [], [lock_N] * 2 + _ramp(lock_N, -ROD_WEIGHT_N[FR], 8))
    assert truth[-1] == pytest.approx(451.7 * BAR, rel=2e-3)
    assert np.all(estimates >= truth - 1e-6)


def test_t7_floor_entry_and_return_stays_bounded() -> None:
    """A load rise after the lock drives the rod side to the floor; the load then falls past
    the lock force (the rod side comes back on the same line)."""
    lock_N = 60e3
    leg = LockedLeg(0.45, 0.05, 0.05, lock_N, 30 * BAR)
    forces = [lock_N] * 2 + _ramp(lock_N, 200e3, 6) + _ramp(200e3, 10e3, 10)
    estimates, truth = _run_synthetic(leg, -0.5 * V_MAX, [lock_N] * 5, [], forces)
    assert truth.min() == pytest.approx(FLOOR_PA)
    assert np.all(estimates >= truth - 1e-6)


def test_t7_lock_at_the_window_end_on_a_higher_head_is_bounded() -> None:
    """The valve lag keeps the leg moving after the first command-free sample while the body
    settles onto it (head 2 -> 150 bar); the plant locks just before the window end."""
    leg_tmp = LockedLeg(0.50, 0.0361, 0.05, 0.0, 1.1 * BAR)
    window_forces = _ramp(0.0, 195e3, 10)
    leg = replace(leg_tmp, lock_force_N=window_forces[-1])
    after = _ramp(window_forces[-1], -ROD_WEIGHT_N[FR], 10) + [-ROD_WEIGHT_N[FR]] * 5
    estimates, truth = _run_synthetic(leg, 0.5 * V_MAX, [0.0] * 5, window_forces[:-1], after)
    assert np.all(estimates >= truth - 1e-6)
    fixed = TwoPressureSettings().with_r8_period()
    fixed = replace(fixed, locked_ratio_rule="fixed")
    old, _ = _run_synthetic(leg, 0.5 * V_MAX, [0.0] * 5, window_forces[:-1], after, fixed)
    assert np.any(old < truth - 50 * BAR)  # the rule before P-S8-13 missed this case


def test_t7_without_valve_lag_the_first_sample_is_the_lock() -> None:
    """``tau_v = 0``: the window is the first command-free sample alone."""
    settings = replace(TwoPressureSettings().with_r8_period(), lock_window_valve_tau_s=0.0)
    lock_N = 118.1e3
    leg = LockedLeg(0.40, 0.02, 0.08, lock_N, 2 * BAR)
    estimates, truth = _run_synthetic(
        leg, 0.5 * V_MAX, [lock_N] * 5, [], _ramp(lock_N, -ROD_WEIGHT_N[FR], 10), settings)
    assert np.all(estimates >= truth - 1e-6)
    monitor = _monitor(settings)
    commanded = np.zeros(4)
    commanded[FR] = 0.5 * V_MAX
    monitor.read(0.0, np.full(4, 80 * BAR), np.full(4, 5 * BAR), commanded, False, 2e3,
                 stroke_m=np.full(4, 0.3))
    monitor.read(0.1, np.full(4, 80 * BAR), np.full(4, 5 * BAR), np.zeros(4), False, 2e3,
                 stroke_m=np.full(4, 0.3))
    stretch = monitor._lock_stretches[FR]
    assert stretch.window_end_s == pytest.approx(0.2)


def test_t7_lock_after_a_retraction_starts_at_the_plant_value() -> None:
    """In the air after a retraction the plant locks the rod side at ``p_r0_after_retract``
    (34.8 bar FR-like), above the pilot threshold formula of a low head."""
    lock_N = -ROD_WEIGHT_N[FR]
    leg = LockedLeg(0.30, 0.05, 0.05, lock_N, 34.352 * BAR)
    estimates, truth = _run_synthetic(leg, -0.5 * V_MAX, [lock_N] * 5, [], [lock_N] * 10)
    locked = slice(5, None)  # the moving estimate (pilot threshold formula) is unchanged
    assert np.all(estimates[locked] >= truth[locked] - 1e-6)


def test_ratio_bound_matches_the_hydraulics_reproduction() -> None:
    """``R_ub`` of ``h_s8_2_lock_ratio.json`` ``part_a.R_ub_grid`` (kappa 1.1): 0.1308 /
    1.6937 / 24.0429 at s = 0 / 0.40 / 0.68 m. The 10.2 table 1 row (0.119 / 1.540 / 21.86)
    is the same formula without kappa. At 0.6948 m ``s'`` stops at ``s_max - 1 mm`` (10.4 ①):
    1.1 x 0.779 / 0.021. No stroke reading -> ``s' = s_max - 1 mm`` and a warning on a
    fallback leg."""
    monitor = _monitor()
    for stroke_m, expected in ((0.0, 0.1308), (0.40, 1.6937), (0.68, 24.0429),
                               (0.6948, 1.1 * 0.779 / 0.021)):
        assert monitor._ratio_bound(FR, stroke_m) == pytest.approx(expected, abs=1e-4)
    monitor.rod_state[FR] = RodSensorState.FALLBACK
    assert monitor._ratio_bound(FR, math.nan) == pytest.approx(1.1 * 0.779 / 0.021, rel=1e-9)
    assert ("WARN_FALLBACK_LOCK_STROKE_UNKNOWN:FR", True) in monitor.pop_events()


def test_reading_bound_carries_the_last_valid_reading() -> None:
    """⑤: a rod reading the model does not know (an older lock, 120 bar) is carried after the
    sensor falls back: ``p_r,read(k_v) + R_ub (H_v - p_h)^+``."""
    monitor = _monitor()
    head, rod = np.full(4, 100 * BAR), np.full(4, 120 * BAR)
    stroke = np.full(4, 0.40)
    still = np.zeros(4)
    monitor.read(0.0, head, rod, np.full(4, 0.5 * V_MAX), False, 2e3, stroke_m=stroke)
    for k in range(1, 15):
        monitor.read(k * PERIOD_S, head, rod, still, False, 2e3, stroke_m=stroke)
    monitor.rod_state[FR] = RodSensorState.FALLBACK
    lower_head = head.copy()
    lower_head[FR] = 90 * BAR
    monitor.read(1.5, lower_head, np.full(4, np.nan), still, False, 2e3, stroke_m=stroke)
    ratio = monitor._ratio_bound(FR, 0.40)
    assert monitor._legs[FR].rod_estimate_Pa == pytest.approx(120 * BAR + ratio * 10 * BAR)
    assert monitor.meta()["fallback_lock_current"][0]["source"] == "reading"


def test_deficit_cap_is_off_by_default_and_floors_the_fallback_lower_bound() -> None:
    """Open key for control (10.7 ②): ``lower >= F_min - cap`` on a fallback leg only."""
    assert TwoPressureSettings().fallback_lower_deficit_cap_N is None
    capped = _monitor(replace(TwoPressureSettings().with_r8_period(),
                              fallback_lower_deficit_cap_N=5e3))
    capped.rod_state[FR] = RodSensorState.FALLBACK
    head, rod = np.full(4, 5 * BAR), np.full(4, 5 * BAR)
    forces = capped.read(0.0, head, rod, np.full(4, -0.5 * V_MAX), False, 2e3,
                         stroke_m=np.full(4, 0.3))
    assert forces.lower[FR] == pytest.approx(F_MIN_N - 5e3)
    np.testing.assert_array_equal(forces.lower[[0, 2, 3]], forces.nominal[[0, 2, 3]])


# --- T8: the fixed rule and runs without a fallback ------------------------------------------


def _random_inputs(seed: int, count: int = 400):
    rng = np.random.default_rng(seed)
    commands = rng.choice([-0.5 * V_MAX, 0.0, 0.0, 0.0, 0.3 * V_MAX], size=(count, 4))
    commands = np.repeat(commands[::8], 8, axis=0)[:count]
    head = 60 * BAR + 40 * BAR * rng.random((count, 4))
    rod = 3 * BAR + 30 * BAR * rng.random((count, 4))
    stroke = 0.2 + 0.4 * rng.random((count, 4))
    return commands, head, rod, stroke


def _replay_synthetic(settings, fallback_from: int | None = None):
    commands, head, rod, stroke = _random_inputs(7)
    monitor = _monitor(replace(settings, diagnostics=False))
    out = []
    for k in range(len(commands)):
        if fallback_from is not None and k == fallback_from:
            monitor.rod_state[FR] = RodSensorState.FALLBACK
        forces = monitor.read(k * PERIOD_S, head[k], rod[k], commands[k], False, 2e3,
                              stroke_m=stroke[k])
        out.append(np.stack([forces.nominal, forces.lower, forces.upper, forces.head_only]))
    return np.array(out), monitor


def test_t8_fixed_rule_is_the_estimate_before_p_s8_13() -> None:
    """``fixed``: moving value of the last moving sample (pilot extend 8 bar) plus 1.296 /
    1.232 times the head drop from the first command-free sample."""
    settings = replace(TwoPressureSettings().with_r8_period(), locked_ratio_rule="fixed")
    monitor = _monitor(settings)
    head = np.full(4, 100 * BAR)
    monitor.read(0.0, head, np.full(4, 2 * BAR), np.full(4, 0.5 * V_MAX), False, 2e3)
    monitor.read(0.1, head, np.full(4, 2 * BAR), np.zeros(4), False, 2e3)
    monitor.read(0.2, head - 10 * BAR, np.full(4, 2 * BAR), np.zeros(4), False, 2e3)
    expected = 8 * BAR + np.array(settings.fallback_locked_ratio) * 10 * BAR
    np.testing.assert_allclose(monitor.meta()["fallback_rod_estimate_Pa"], expected)
    meta = settings.to_meta()
    assert meta["locked_ratio_rule"] == "fixed"
    assert not set(COLUMN_BOUND_META_KEYS) & set(meta)
    assert "fallback_lock_log" not in monitor.meta()


def test_t8_without_a_fallback_leg_the_readings_do_not_depend_on_the_rule() -> None:
    settings = TwoPressureSettings().with_r8_period()
    column, _ = _replay_synthetic(settings)
    fixed, _ = _replay_synthetic(replace(settings, locked_ratio_rule="fixed"))
    np.testing.assert_array_equal(column, fixed)
    column_fb, _ = _replay_synthetic(settings, fallback_from=100)
    fixed_fb, _ = _replay_synthetic(replace(settings, locked_ratio_rule="fixed"),
                                    fallback_from=100)
    other = [0, 2, 3]
    np.testing.assert_array_equal(column_fb[:, :, other], fixed_fb[:, :, other])
    assert np.all(column_fb[100:, 1, FR] <= fixed_fb[100:, 1, FR] + 1e-6)


def test_column_bound_meta_is_json_and_lists_the_stretches() -> None:
    settings = TwoPressureSettings().with_r8_period()
    assert LockedRatioRule(settings.locked_ratio_rule) is LockedRatioRule.COLUMN_BOUND
    _, monitor = _replay_synthetic(settings, fallback_from=100)
    meta = monitor.meta()
    json.dumps(meta)
    assert meta["fallback_estimate_rule"] == "column_bound"
    assert meta["fallback_lock_stroke_max_m"] == STROKE_MAX_M
    assert meta["fallback_lock_log"] and all(row["leg"] == "FR"
                                             for row in meta["fallback_lock_log"])
    assert set(COLUMN_BOUND_META_KEYS) <= set(meta["settings"])


# --- pickles written before P-S8-13 ----------------------------------------------------------


def test_settings_pickled_before_p_s8_13_read_the_column_bound() -> None:
    settings = TwoPressureSettings().with_r8_period()
    state = dict(settings.__dict__)
    for key in (*COLUMN_BOUND_META_KEYS, "locked_ratio_rule", "fallback_lower_deficit_cap_N"):
        del state[key]
    old = object.__new__(TwoPressureSettings)
    old.__dict__.update(state)
    restored = pickle.loads(pickle.dumps(old))
    assert restored.locked_ratio_rule is LockedRatioRule.COLUMN_BOUND
    assert restored.fallback_lower_deficit_cap_N is None
    json.dumps(restored.to_meta())
    monitor = _monitor(restored)
    monitor.rod_state[FR] = RodSensorState.FALLBACK
    monitor.read(0.0, np.full(4, 80 * BAR), np.full(4, 5 * BAR), np.zeros(4), False, 2e3)


def test_monitor_pickled_before_p_s8_13_keeps_running_and_its_old_anchor() -> None:
    """A monitor without the P-S8-13 attributes (class defaults) inside a lock stretch: the
    readings without a fallback are unchanged, a fallback leg keeps the old anchor as one
    more candidate (unknown last direction)."""
    settings = TwoPressureSettings().with_r8_period()
    new = _monitor(settings)
    head, rod = np.full(4, 120 * BAR), np.full(4, 2 * BAR)
    new.read(0.0, head, rod, np.full(4, 0.5 * V_MAX), False, 2e3, stroke_m=np.full(4, 0.4))
    for leg in new._legs:  # what the code before P-S8-13 stored at the first still sample
        leg.lock_rod_estimate_Pa, leg.lock_head_Pa = 8 * BAR, 150 * BAR
    old = copy.deepcopy(new)
    for name in ("_column_stroke_max_m", "_retract_lock_floor_Pa", "_lock_stretches",
                 "_fallback_lock_log"):
        del old.__dict__[name]
    restored = pickle.loads(pickle.dumps(old))
    a = new.read(0.1, head, rod, np.zeros(4), True, 2e3, stroke_m=np.full(4, 0.4))
    b = restored.read(0.1, head, rod, np.zeros(4), True, 2e3, stroke_m=np.full(4, 0.4))
    np.testing.assert_array_equal(np.stack([a.nominal, a.lower, a.upper]),
                                  np.stack([b.nominal, b.lower, b.upper]))
    assert new.pop_events() == restored.pop_events()
    restored.rod_state[FR] = RodSensorState.FALLBACK
    restored.read(0.2, head, rod, np.zeros(4), True, 2e3, stroke_m=np.full(4, 0.4))
    ratio = restored._ratio_bound(FR, 0.4)
    assert restored._legs[FR].rod_estimate_Pa >= 8 * BAR + ratio * 30 * BAR - 1e-6
    json.dumps(restored.meta())


@pytest.mark.skipif(not ML_BASES, reason="07_results/S8 ML pilot bases not present")
@pytest.mark.parametrize("branch", ML_BASES, ids=lambda path: path.parent.name)
def test_controller_from_an_old_branch_runs_with_a_fallback_leg(branch) -> None:
    """⑧: every ML ``branch.pkl`` (pickled before P-S8-13) restores, takes the current
    settings and runs with one leg falling back (the column bound on an old monitor)."""
    with open(branch, "rb") as handle:
        blob = pickle.load(handle)  # noqa: S301 - own batch file
    controller = blob["controller"]
    inner = getattr(controller, "inner", controller)
    monitor = inner._pressures
    current = TwoPressureSettings().with_r8_period()
    if monitor.settings.counterbalance is not None:
        current = current.with_lock_valve("counterbalance", monitor.settings.counterbalance)
    monitor.refresh_settings(current)
    assert monitor.settings.locked_ratio_rule is LockedRatioRule.COLUMN_BOUND
    head = np.asarray(inner._state.last_forces.head_only) / monitor.head_area_m2
    stroke = np.asarray(inner._state.last_reading.motor_stroke_m, dtype=float)
    level = np.array([0.0, 0.0, GRAVITY_M_S2])
    rod = np.full(4, 5e5)
    for k in range(8):
        if k == 2:
            rod = rod.copy()
            rod[FR] = math.nan  # D1 -> fallback
        command = controller.update(Measurements(
            t_s=float(blob["t_s"]) + (k + 1) * PERIOD_S,
            specific_force_m_s2=level,
            angular_rate_rad_s=np.zeros(3),
            head_pressure_Pa=head,
            stroke_m=stroke,
            rod_pressure_Pa=rod,
            imu_specific_force_samples_m_s2=np.tile(level, (10, 1)),
        ))
        assert np.all(np.isfinite(command.leg_speed_m_s))
    assert FR in monitor.fallback_legs
    assert math.isfinite(monitor._legs[FR].rod_estimate_Pa)
    json.dumps(monitor.meta())


# --- 218.10 record: the guard on a fallback leg ----------------------------------------------


def test_guard_on_a_fallback_leg_is_logged_in_stretches() -> None:
    """Control spec rev. 48 218.10 (P-S8-13 complement): consecutive guarded periods of a
    fallback leg form one stretch with its duration and the head where the guard stopped;
    a gap opens a new stretch; a guard on a leg with its rod sensor is not logged."""
    from outrigger_sim.control.c2 import C2Controller
    from outrigger_sim.params import load_params

    controller = C2Controller.from_params(load_params())
    area = controller.geometry.head_area_m2

    def guard(t_s, head_bar, lowest_leg):
        loads = np.full(4, 50e3)
        loads[lowest_leg] = 5e3
        reading = SimpleNamespace(t_s=t_s, head_only_force_N=np.full(4, head_bar * BAR) * area)
        controller._log_fallback_guard(reading, loads)

    guard(1.0, 30.0, FR)
    assert controller.meta()["fallback_guard"] == []
    controller._pressures.rod_state[FR] = RodSensorState.FALLBACK
    period_s = controller.config.period_s
    for k, head_bar in enumerate((30.0, 35.0, 40.0)):
        guard(2.0 + k * period_s, head_bar, FR)
    guard(3.0, 50.0, FR)
    stretches = controller.meta()["fallback_guard"]
    assert [row["periods"] for row in stretches] == [3, 1]
    assert stretches[0]["leg"] == "FR"
    assert stretches[0]["duration_s"] == pytest.approx(3 * period_s)
    assert stretches[0]["head_end_Pa"] == pytest.approx(40 * BAR)
    json.dumps(stretches)


# --- T1-T3, T6: record replays ------------------------------------------------------------


def _old_ml_episode(name: str) -> Path:
    return ML_OLD_EPISODES[-1] / name if ML_OLD_EPISODES else ML_EPISODES / "missing" / name


CASES = {
    "T1": {"case": _old_ml_episode("ML00_ep5"), "legs": ("FR",), "force_s": 61.1,
           "judge_s": (61.6, 89.0), "rod_bound": True},
    "T1b": {"case": ML_EPISODES / "ML17_ep4", "legs": ("FR",), "force_s": 66.2,
            "judge_s": (67.4, 94.0)},
    "T2": {"case": P1R / "K0V_top_fdown3.5_Fs0", "legs": ("FR",), "force_s": 55.1,
           "judge_s": (55.1, 63.4)},
    "T3": {"case": CB / "CB_H4V_fdown3.5_Fs0", "legs": ("FR", "FL"), "force_s": 52.0,
           "judge_s": (52.0, 63.4)},
    "T6a": {"case": P1R / "E_G4_Fs8", "legs": ("FL",), "force_s": None,
            "judge_s": (6.4, 7.8)},
    "T6b": {"case": CB / "CB_H4V_fdown3.5_Fs0", "legs": ("RR",), "force_s": None,
            "judge_s": (26.3, 26.6)},
    "T6c": {"case": P1R / "K0_top_rpBop_Fs0", "legs": ("FR",), "force_s": None,
            "judge_s": (4.0, 4.6)},
}
"""10.4 ⑦: the leg falls back at ``force_s`` (``None`` = from the record start); the lower
bound is judged on the command-free samples of the leg within ``judge_s`` (the moving
estimate is not part of P-S8-13, as in the hydraulics reproduction). T1 the old episode
(``episodes/_replaced_*``) the hydraulics analysed; ``rod_bound``: also ``p_hat >= p_r,true``
(the 216 bar lift-off samples included). T1b (control spec rev. 48 218.6, 218.15): the rerun
ML17_ep4 FR whose false D1 fallback at 66.2 s gave the F2 of 35.6 kN (67.4-94 s)."""
LEG_NAMES = ("FL", "FR", "RL", "RR")


def _case_settings(case: Path, rule: str) -> TwoPressureSettings:
    settings = replace(TwoPressureSettings().with_r8_period(), locked_ratio_rule=rule)
    meta = json.loads((case / "record" / "meta.json").read_text(encoding="utf-8"))
    s8 = meta["run"]["engine"]["actuator"].get("s8") or {}
    if s8.get("lock_valve") != "counterbalance":
        return settings
    params = SimpleNamespace(**s8["counterbalance"]["params"])
    return settings.with_lock_valve("counterbalance", params)


def forced_fallback_replay(spec: dict, rule: str) -> dict | None:
    """Per judged leg: worst ``lower - F_true`` [N], its time, ``min(p_hat - p_r,true)``,
    the conservatism at the window end and the lowest ``p_hat`` after ``rod_floor``."""
    case = spec["case"]
    if not (case / "pads.npz").exists():
        return None
    controller = json.loads((case / "result.json").read_text(encoding="utf-8"))[
        "controller_meta"]
    meta = controller["two_pressure"]
    monitor = TwoPressureMonitor(
        meta["head_area_m2"], meta["annulus_area_m2"], controller["geometry"]["max_speed_m_s"],
        controller["geometry"]["F_min_N"], controller["period_s"],
        LoadEstimate(meta["load_estimate"]), _case_settings(case, rule), meta["rod_weight_N"],
        stroke_max_m=controller["geometry"]["stroke_max_m"])
    with np.load(case / "r8_series.npz") as r8:
        t, issued, phase, band = r8["t"], r8["issued_u"], r8["phase"], r8["F_band_N"]
    with np.load(case / "record" / "record.npz") as record:
        index = np.clip(np.searchsorted(record["t"], t - 1e-9), 0, record["t"].size - 1)
        head = record["meas.head_pressure"][index]
        rod = record["meas.rod_pressure"][index]
        stroke = record["meas.stroke"][index]
    with np.load(case / "pads.npz") as pads:
        index = np.clip(np.searchsorted(pads["t"], t - 1e-9), 0, pads["t"].size - 1)
        f_true, rod_true = pads["F_pressure"][index], pads["rod_pressure"][index]
    commanded = np.vstack([np.zeros((1, 4)), issued[:-1]])
    legs = [LEG_NAMES.index(name) for name in spec["legs"]]
    calibration = controller.get("zero_calibration") or {}
    end_s = (calibration.get("result") or {}).get("t_end_s")
    has_offsets = end_s is None or t[0] > end_s
    if has_offsets:
        monitor.set_zero_offsets_N(meta["zero_offsets_N"])
    lower, estimate = np.zeros((t.size, 4)), np.zeros((t.size, 4))
    for k in range(t.size):
        if spec["force_s"] is None or t[k] >= spec["force_s"] - 1e-9:
            for leg in legs:
                monitor.rod_state[leg] = RodSensorState.FALLBACK
        bands = monitor.leg_seal_bands_N(band[k - 1] if k else band[0])
        is_locked = bool(k) and phase[k - 1] == "READY"
        forces = monitor.read(t[k], head[k], rod[k], commanded[k], is_locked, bands,
                              stroke_m=stroke[k])
        lower[k] = forces.lower
        estimate[k] = [watch.rod_estimate_Pa for watch in monitor._legs]
        if not has_offsets and end_s is not None and t[k] >= end_s - 1e-9:
            monitor.set_zero_offsets_N(calibration["offsets_N"])
            has_offsets = True
    start_s, stop_s = spec["judge_s"]
    in_window = (t >= start_s - 1e-9) & (t <= stop_s + 1e-9)
    out = {}
    for leg in legs:
        judged = in_window & (commanded[:, leg] == 0.0)
        error = lower[judged, leg] - f_true[judged, leg]
        out[LEG_NAMES[leg]] = {
            "samples": int(judged.sum()),
            "err_max_N": float(error.max()),
            "t_err_max": float(t[judged][int(np.argmax(error))]),
            "rod_margin_min_Pa": float(np.min(estimate[judged, leg] - rod_true[judged, leg])),
            "over_end_N": float(-error[-1]),
        }
    return out


@pytest.mark.parametrize("name", sorted(CASES))
def test_record_replay_lower_bound_is_not_optimistic(name) -> None:
    """T1-T3, T6: lower bound <= true force + 0.6 kN on the judged samples; T1: ``p_hat >=
    p_r,true`` on every one of them (lift-off at 216 bar included)."""
    spec = CASES[name]
    result = forced_fallback_replay(spec, "column_bound")
    if result is None:
        pytest.skip(f"{spec['case']} not present")
    for row in result.values():
        assert row["samples"] > 0
        assert row["err_max_N"] <= OPTIMISM_LIMIT_N
        if spec.get("rod_bound"):
            assert row["rod_margin_min_Pa"] >= 0.0
