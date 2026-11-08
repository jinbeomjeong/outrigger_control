"""Checks of the LAS-b phase diagnosis recorder (``las_phase_diag.py``), no harness run.

The hooks are installed on a stand-in controller class (the method and attribute names the
recorder reads of ``C2Controller``); its LAS-b stage follows the c2 gate formula, so the
recorded gates must agree with the stand-in's start. Run (dynamics-dev):
  python -I -B -m pytest <this file> -p no:cacheprovider
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "03_src"))

import fb_targeted as ft  # noqa: E402
import las_phase_diag as diag  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

from outrigger_sim.control import c2  # noqa: E402

V_MAX_M_S = 0.020924
F_MIN_N = 9415.0
WEIGHT_N = 376_700.0
HEAD_M2 = np.array([1.3273e-2, 1.3273e-2, 9.503e-3, 9.503e-3])
ANNULUS_M2 = np.array([3.770e-3, 3.770e-3, 3.142e-3, 3.142e-3])
LIMITS = diag.GateLimits(0.6, 1.5, 0.16, 0.2, WEIGHT_N, F_MIN_N, V_MAX_M_S)
OPEN_FLAGS = diag.GateFlags(True, True, False, False, True, False)
LIGHT_RL_LOADS = np.array([130e3, 60e3, 10e3, 130e3])
"""RL lightest; its diagonal (RL + FR) carries 70 of 330 kN, so rho = 0.576."""


# ------------------------------------------------------------------------------- pure helpers
def test_gate_record_all_hold_and_values():
    loads = LIGHT_RL_LOADS
    rho, lightest = c2.diagonal_deficit_ratio(loads)
    record = diag.gate_record(loads, rho, lightest, 0.1, np.full(4, V_MAX_M_S), OPEN_FLAGS,
                              LIMITS)
    assert record["lightest_leg"] == "RL"
    assert record["rho"] == pytest.approx((330e3 - 2 * 70e3) / 330e3)
    assert record["sum_over_W"] == pytest.approx(330e3 / WEIGHT_N)
    assert record["min_over_F_min"] == pytest.approx(10e3 / F_MIN_N)
    assert record["rho"] == pytest.approx(rho)
    assert record["all_hold"] is True


@pytest.mark.parametrize(("previous_rho", "speed", "failing"), [
    (None, V_MAX_M_S, "S7p_rise"),     # no previous LEVEL period: not rising
    (0.99, V_MAX_M_S, "S7p_rise"),     # rho below the previous one
    (0.1, 0.1 * V_MAX_M_S, "S8"),      # slow mean
])
def test_gate_record_single_failures(previous_rho, speed, failing):
    loads = LIGHT_RL_LOADS
    rho, lightest = c2.diagonal_deficit_ratio(loads)
    record = diag.gate_record(loads, rho, lightest, previous_rho, np.full(4, speed),
                              OPEN_FLAGS, LIMITS)
    assert [name for name, ok in record["gates"].items() if not ok] == [failing]
    assert record["all_hold"] is False


def test_gate_record_nan_rho_is_none():
    loads = np.zeros(4)
    rho, lightest = c2.diagonal_deficit_ratio(loads)
    record = diag.gate_record(loads, rho, lightest, 0.1, np.full(4, V_MAX_M_S), OPEN_FLAGS,
                              LIMITS)
    assert record["rho"] is None and record["gates"]["S7p_rise"] is False


def test_done_gate_values():
    settings = diag.RelaxSettings(10.0, 5.0, 0.0, 600.0, 15e3, 0.1)
    history = [(20.0 + 0.1 * i, 12e3 - 10.0 * i) for i in range(51)]
    out = diag.done_gate_values(25.0, history, 14.9, -11.5e3, settings)
    assert out["is_settled"] and out["is_window_full"] and out["is_non_increasing"]
    assert out["is_D_small"] and out["D_kN"] == pytest.approx(-11.5)
    empty = diag.done_gate_values(25.0, [], None, 20e3, settings)
    assert not empty["is_settled"] and not empty["is_window_full"] and not empty["is_D_small"]


def _period(t, phase, loc):
    return {"t_s": t, "phase": phase, "loc": loc}


def test_record_windows():
    periods = [_period(round(0.1 * i, 1), "touch" if i < 50 else "level", 100 <= i < 120)
               for i in range(150)]
    periods += [_period(15.0, "level", True), _period(15.1, "done", True)]
    touch_ends = [{"t_s": 5.0}]
    window_a = diag.record_window("D-a", periods, touch_ends)
    assert window_a["t0_s"] == pytest.approx(4.5) and window_a["t1_s"] == pytest.approx(12.0)
    kept = diag.periods_in(periods, window_a)
    assert kept[0]["t_s"] == pytest.approx(4.5) and kept[-1]["t_s"] == pytest.approx(12.0)
    window_c = diag.record_window("D-c", periods, touch_ends)
    assert window_c["t0_s"] == pytest.approx(14.5) and window_c["t1_s"] == pytest.approx(16.1)


def test_force_window_finds_the_focus_minimum():
    from harness_flow import COLUMN, COLUMNS

    t = np.arange(0.0, 3.0, 1e-3)
    rows = np.zeros((t.size, len(COLUMNS)))
    rows[:, COLUMN["t"]] = t
    for leg in diag.LEG_ORDER:
        rows[:, COLUMN[f"true_force_{leg}"]] = 50e3
    rows[:, COLUMN["true_force_RL"]] = 20e3 + 5e3 * (t - 2.0) ** 2
    rows[t < 1.0, COLUMN["true_force_RL"]] = 1e3  # before the lift-off: ignored
    out = diag.force_window(rows, COLUMN, 1.0)
    assert out["t_focus_min_s"] == pytest.approx(2.0)
    assert out["focus_min_kN"] == pytest.approx(20.0)
    assert out["min_leg"] == "RL"
    assert len(out["rows"]) == 1001
    assert diag.force_window(rows, COLUMN, None) is None


def test_seeded_budget_at_s_nom_is_the_lf_budget():
    nominal = ft.nominal_budget_m3_s(1.00333e-3)
    full = diag.full_flow_m3_s(HEAD_M2, ANNULUS_M2, V_MAX_M_S)
    state, record = diag.seeded_budget(nominal / full, nominal, HEAD_M2, ANNULUS_M2, V_MAX_M_S)
    assert state.budget_m3_s == pytest.approx(nominal, rel=1e-15)
    assert state.nominal_m3_s == nominal
    state_one, record_one = diag.seeded_budget(1.0, nominal, HEAD_M2, ANNULUS_M2, V_MAX_M_S)
    assert state_one.budget_m3_s == full and record_one["s_nom"] == pytest.approx(nominal / full)


def test_out_path_problem(tmp_path):
    root = tmp_path / "project"
    out_dir = root / "diag"
    out_dir.mkdir(parents=True)
    assert diag.out_path_problem(out_dir / "a.jsonl", out_dir, root) is None
    assert "not in" in diag.out_path_problem(root / "a.jsonl", out_dir, root)
    assert diag.out_path_problem(tmp_path / "scratch.jsonl", out_dir, root) is None
    (out_dir / "b.jsonl").write_text("", encoding="utf-8")
    assert "exists" in diag.out_path_problem(out_dir / "b.jsonl", out_dir, root)


def test_candidate_labels():
    assert diag.candidate_label("LF", 0.95) == "LF-s0.95"
    assert diag.candidate_label("L", None) == "L"


# ------------------------------------------------------------------------------- stand-in
@dataclass
class Reading:
    t_s: float
    cylinder_force_lower_N: np.ndarray
    cylinder_force_N: np.ndarray
    motor_stroke_m: np.ndarray = field(default_factory=lambda: np.full(4, 0.3))
    rod_stroke_m: np.ndarray = field(default_factory=lambda: np.full(4, 0.299))


@dataclass
class SlowState:
    is_armed: bool = True
    is_active: bool = False
    has_loc_been_seen: bool = False
    previous_rho: float | None = None
    end_s: float | None = None
    end_reason: str | None = None
    sum_periods: int = 0


@dataclass
class State:
    phase: c2.C2Phase = c2.C2Phase.TOUCH
    liftoff_slow: SlowState = field(default_factory=SlowState)
    soil: object = None
    in_crawler_zone: bool = True
    last_reading: Reading | None = None
    twist_relax_history: object = None
    twist_relax_settled_since_s: float | None = None
    complete_since_s: float | None = None
    diff_sink: object = None


@dataclass
class Command:
    t_s: float
    leg_speed_m_s: np.ndarray


SETTINGS = SimpleNamespace(sum_on_fraction_W=0.6, light_leg_fraction_of_F_min=1.5,
                           slow_mean_fraction=0.16, rho_on=0.2, require_soil_response=True)


class StandIn:
    """``update`` runs the stand-in LAS-b stage in LEVEL (the c2 gate formula, scaled mean)
    and passes the result through ``fb.budget_output`` (module global, as the FB wrapper)."""

    def __init__(self, loads_by_period):
        self.config = SimpleNamespace(liftoff_approach_slow=SETTINGS,
                                      soil=SimpleNamespace(enable=True),
                                      twist_completion_relax=SimpleNamespace(enable=False),
                                      period_s=0.1)
        self.geometry = SimpleNamespace(F_min_N=F_MIN_N, max_speed_m_s=V_MAX_M_S,
                                        twist_vector=np.array([0.5, -0.5, -0.5, 0.5]),
                                        head_area_m2=HEAD_M2, annulus_area_m2=ANNULUS_M2)
        self._state = State()
        self.loads_by_period = loads_by_period
        self.budget = ft.FbState(nominal_m3_s=1e-4, budget_m3_s=1e-4)
        self.filtered_attitude_rad = (0.01, -0.02)

    def _reference_weight_N(self):
        return WEIGHT_N

    def _load_estimate_N(self, cylinder_force_N):
        return cylinder_force_N  # the PRESSURE judge returns its input object

    def _diff_sink_rates_m_s(self):
        return None

    def _apply_liftoff_approach_slow(self, reading, leg_speeds, reapproaching):
        slow = self._state.liftoff_slow
        loads = self._load_estimate_N(reading.cylinder_force_lower_N)
        rho, _ = c2.diagonal_deficit_ratio(loads)
        previous = slow.previous_rho
        slow.previous_rho = rho
        is_rising = previous is not None and rho >= SETTINGS.rho_on and rho > previous
        gates = (np.sum(loads) >= 0.6 * WEIGHT_N and np.min(loads) < 1.5 * F_MIN_N
                 and is_rising and np.mean(leg_speeds) > 0.16 * V_MAX_M_S
                 and not np.any(reapproaching))
        if slow.is_armed and gates:
            slow.is_armed, slow.is_active = False, True
        if not slow.is_active:
            return leg_speeds
        return leg_speeds * (0.16 * V_MAX_M_S / np.mean(leg_speeds))

    def update(self, measurements):
        k = int(round(measurements.t_s / 0.1))
        loads = np.asarray(self.loads_by_period[k], float)
        reading = Reading(measurements.t_s, loads, loads.copy())
        self._state.last_reading = reading
        if k >= 1:
            self._state.phase = c2.C2Phase.LEVEL
        speeds = np.full(4, V_MAX_M_S)
        if self._state.phase is c2.C2Phase.LEVEL:
            speeds = self._apply_liftoff_approach_slow(reading, speeds, np.zeros(4, bool))
        output = ft.budget_output(self.budget, speeds, self.geometry, str(self._state.phase))
        return Command(measurements.t_s, output)


LOADS = [[80e3, 80e3, 80e3, 80e3], [100e3, 80e3, 40e3, 100e3], [120e3, 60e3, 12e3, 120e3],
         [120e3, 60e3, 12e3, 120e3], [125e3, 55e3, 8e3, 125e3]]
"""TOUCH, then LEVEL: rho 0.25 (no light leg), 0.54 rising with RL light (start), held."""


def _run(is_recording: bool, scale: float | None = None):
    diag.install(is_recording, scale, controller_class=StandIn, nominal_m3_s=1e-4)
    try:
        controller = StandIn(LOADS)
        commands = [controller.update(SimpleNamespace(t_s=0.1 * k)) for k in range(len(LOADS))]
    finally:
        diag.uninstall()
    return controller, commands


def test_recorder_keeps_the_commands_and_reads_the_gates():
    plain = StandIn(LOADS)
    reference = [plain.update(SimpleNamespace(t_s=0.1 * k)) for k in range(len(LOADS))]
    controller, commands = _run(is_recording=True)
    for got, want in zip(commands, reference, strict=True):
        assert np.array_equal(got.leg_speed_m_s, want.leg_speed_m_s)
    log = controller.__dict__[diag.LOG_ATTRIBUTE]
    assert [entry["t_s"] for entry in log.touch_ends] == [pytest.approx(0.1)]
    las = [period["las"] for period in log.periods]
    assert las[0] is None  # TOUCH period
    assert all(entry["gate_consistent"] for entry in las[1:])
    started = [entry["started"] for entry in las[1:]]
    assert started.count(True) == 1
    assert log.periods[1]["budget"]["phase"] == "level"
    assert ft.budget_output.__module__ == "fb_targeted"  # uninstall put the original back


def test_budget_hook_reports_the_scale():
    controller, _ = _run(is_recording=True)
    touch = controller.__dict__[diag.LOG_ATTRIBUTE].periods[0]["budget"]
    expected = 1e-4 / ft.command_flow_m3_s(np.full(4, V_MAX_M_S), HEAD_M2, ANNULUS_M2)
    assert touch["acted"] is True and touch["scale"] == pytest.approx(expected)


def test_seed_only_install_records_nothing():
    controller, _ = _run(is_recording=False, scale=0.9)
    log = controller.__dict__[diag.LOG_ATTRIBUTE]
    assert log.periods == [] and log.budget_seed["s"] == 0.9
    assert controller.__dict__["_fb_run"].budget_m3_s == pytest.approx(
        0.9 * diag.full_flow_m3_s(HEAD_M2, ANNULUS_M2, V_MAX_M_S))


def test_install_twice_raises():
    diag.install(True, controller_class=StandIn)
    try:
        with pytest.raises(RuntimeError):
            diag.install(True, controller_class=StandIn)
    finally:
        diag.uninstall()
