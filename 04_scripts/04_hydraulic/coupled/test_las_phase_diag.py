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


NOMINAL_M3_S = ft.nominal_budget_m3_s(1.00333e-3)
FULL_M3_S = diag.full_flow_m3_s(HEAD_M2, ANNULUS_M2, V_MAX_M_S)


def test_plan_constants():
    assert round(diag.T1_S, 3) == 14.468  # plan 1.2 table value
    assert diag.BUNDLE_COUNTS["D-b"] == 30


def test_anchor_points_use_the_exact_budgets():
    nominal = diag.touch_budget_for("nom", 0, FULL_M3_S, NOMINAL_M3_S)
    assert nominal.budget_m3_s == NOMINAL_M3_S  # A-2: bit for bit the LF budget
    full = diag.touch_budget_for("1", 0, FULL_M3_S, NOMINAL_M3_S)
    assert full.budget_m3_s == FULL_M3_S  # A-1: the TOUCH command never exceeds it


def test_grid_formula_delays_the_touch_end_by_j_delta():
    for centre in diag.GRID_CENTRES:
        for j in diag.GRID_STEPS:
            point = diag.touch_budget_for(centre, j, FULL_M3_S, NOMINAL_M3_S)
            touch_time_s = diag.T1_S / point.scale  # T(s) = T_1 / s
            assert touch_time_s - point.centre_time_s == pytest.approx(0.025 * j, abs=1e-9)
    assert diag.touch_budget_for("0.94", 0, FULL_M3_S, NOMINAL_M3_S).scale == pytest.approx(0.94)
    with pytest.raises(ValueError):
        diag.touch_budget_for("0.9", 0, FULL_M3_S, NOMINAL_M3_S)
    with pytest.raises(ValueError):
        diag.touch_budget_for("1", 5, FULL_M3_S, NOMINAL_M3_S)


def test_plan_problem(tmp_path):
    plan = tmp_path / "plan.md"
    assert "missing" in diag.plan_problem(plan, "0" * 64)
    plan.write_bytes(b"sealed")
    digest = __import__("hashlib").sha256(b"sealed").hexdigest()
    assert diag.plan_problem(plan, digest) is None
    assert "!=" in diag.plan_problem(plan, "0" * 64)


def test_las_start_details():
    def las(started, failing=()):
        gates = {name: name not in failing for name in ("S7_light", "S7p_rise", "S8")}
        return {"started": started, "gates": gates, "gate_consistent": True}

    periods = [{"las": None}, {"las": las(False, ("S7_light",))},
               {"las": las(False, ("S7p_rise",))}, {"las": las(True)}, {"las": las(False)}]
    details = diag.las_start_details(periods)
    assert details["gates_false_before_start"] == ["S7p_rise"]
    assert details["gate_consistent"] is True and details["las_periods_recorded"] == 4
    assert diag.periods_between(22.3, 23.1) == 8


def test_out_path_problem(tmp_path):
    root = tmp_path / "project"
    out_dir = root / "diag"
    out_dir.mkdir(parents=True)
    assert diag.out_path_problem(out_dir / "a.jsonl", out_dir, root) is None
    assert "not in" in diag.out_path_problem(root / "a.jsonl", out_dir, root)
    assert diag.out_path_problem(tmp_path / "scratch.jsonl", out_dir, root) is None
    (out_dir / "b.jsonl").write_text("", encoding="utf-8")
    assert "exists" in diag.out_path_problem(out_dir / "b.jsonl", out_dir, root)


def test_grid_labels():
    assert diag.grid_label("nom", 3) == "LT-cnom-j3"
    labels = [label for label, _, _ in diag._variants("D-b")]
    assert len(labels) == 15 and len(set(labels)) == 15


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
    previous_output_m_s: np.ndarray = field(default_factory=lambda: np.zeros(4))


@dataclass
class Command:
    t_s: float
    leg_speed_m_s: np.ndarray


SETTINGS = SimpleNamespace(sum_on_fraction_W=0.6, light_leg_fraction_of_F_min=1.5,
                           slow_mean_fraction=0.16, rho_on=0.2, require_soil_response=True)
TOUCH_PERIODS = 2


class StandIn:
    """Two TOUCH periods at v_max, then LEVEL with the stand-in LAS-b stage (the c2 gate
    formula, scaled mean); the ramp passes the request on and stores it, as c2 does.

    ``switch_after_ramp_k``: in that period the phase becomes LEVEL after the ramp (a TOUCH
    budget then counts under the end phase LEVEL).
    """

    def __init__(self, loads_by_period, switch_after_ramp_k: int | None = None):
        self.config = SimpleNamespace(liftoff_approach_slow=SETTINGS,
                                      soil=SimpleNamespace(enable=True),
                                      twist_completion_relax=SimpleNamespace(enable=False),
                                      period_s=0.1, clip_returned_command=True)
        self.geometry = SimpleNamespace(F_min_N=F_MIN_N, max_speed_m_s=V_MAX_M_S,
                                        twist_vector=np.array([0.5, -0.5, -0.5, 0.5]),
                                        head_area_m2=HEAD_M2, annulus_area_m2=ANNULUS_M2)
        self._state = State()
        self.loads_by_period = loads_by_period
        self.switch_after_ramp_k = switch_after_ramp_k
        self.filtered_attitude_rad = (0.01, -0.02)

    def _reference_weight_N(self):
        return WEIGHT_N

    def _load_estimate_N(self, cylinder_force_N):
        return cylinder_force_N  # the PRESSURE judge returns its input object

    def _diff_sink_rates_m_s(self):
        return None

    def _apply_output_ramp(self, leg_speeds):
        output = np.asarray(leg_speeds, float).copy()
        self._state.previous_output_m_s = output
        return output

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
        if k >= TOUCH_PERIODS and k != self.switch_after_ramp_k:
            self._state.phase = c2.C2Phase.LEVEL
        speeds = np.full(4, V_MAX_M_S)
        if self._state.phase is c2.C2Phase.LEVEL:
            speeds = self._apply_liftoff_approach_slow(reading, speeds, np.zeros(4, bool))
        output = self._apply_output_ramp(speeds)
        if k == self.switch_after_ramp_k:
            self._state.phase = c2.C2Phase.LEVEL
        return Command(measurements.t_s, output)


LOADS = [[80e3, 80e3, 80e3, 80e3], [80e3, 80e3, 80e3, 80e3], [100e3, 80e3, 40e3, 100e3],
         [120e3, 60e3, 12e3, 120e3], [120e3, 60e3, 12e3, 120e3], [125e3, 55e3, 8e3, 125e3]]
"""TOUCH x 2, then LEVEL: rho 0.25 (no light leg), 0.54 rising with RL light (start), held."""


def _run(is_recording: bool, grid_point=None, switch_after_ramp_k=None):
    diag.install(is_recording, grid_point, controller_class=StandIn,
                 nominal_m3_s=NOMINAL_M3_S)
    try:
        controller = StandIn(LOADS, switch_after_ramp_k)
        commands = [controller.update(SimpleNamespace(t_s=0.1 * k)) for k in range(len(LOADS))]
    finally:
        diag.uninstall()
    return controller, commands


def _plain_commands():
    plain = StandIn(LOADS)
    return [plain.update(SimpleNamespace(t_s=0.1 * k)) for k in range(len(LOADS))]


def test_recorder_keeps_the_commands_and_reads_the_gates():
    controller, commands = _run(is_recording=True)
    for got, want in zip(commands, _plain_commands(), strict=True):
        assert np.array_equal(got.leg_speed_m_s, want.leg_speed_m_s)
    log = controller.__dict__[diag.LOG_ATTRIBUTE]
    assert [entry["t_s"] for entry in log.touch_ends] == [pytest.approx(0.2)]
    las = [period["las"] for period in log.periods]
    assert las[:TOUCH_PERIODS] == [None, None]
    assert all(entry["gate_consistent"] for entry in las[TOUCH_PERIODS:])
    assert [entry["started"] for entry in las[TOUCH_PERIODS:]] == [False, True, False, False]
    assert diag.las_start_details(log.periods)["gates_false_before_start"] == [
        "S7_light", "S7p_rise"]
    assert log.touch_budget is None and all(p["budget"] is None for p in log.periods)
    assert ft.budget_output.__module__ == "fb_targeted"  # uninstall put the original back


def test_touch_budget_scales_touch_periods_only():
    controller, commands = _run(is_recording=True, grid_point=("nom", 0))
    plain = _plain_commands()
    s_nom = NOMINAL_M3_S / FULL_M3_S
    for k, (got, want) in enumerate(zip(commands, plain, strict=True)):
        expected = want.leg_speed_m_s * (s_nom if k < TOUCH_PERIODS else 1.0)
        assert np.allclose(got.leg_speed_m_s, expected, rtol=1e-12, atol=0.0)
    assert np.array_equal(controller._state.previous_output_m_s, commands[-1].leg_speed_m_s)
    log = controller.__dict__[diag.LOG_ATTRIBUTE]
    block = diag.touch_budget_record(log)
    assert block["acted_by_end_phase"] == {"touch": 2}
    assert block["level_budget_periods"] == 0 and block["excluded"] is False
    budgets = [p["budget"] for p in log.periods]
    assert [b is not None for b in budgets] == [True, True, False, False, False, False]
    assert budgets[0]["acted"] and budgets[0]["scale"] == pytest.approx(s_nom)


def test_anchor_a1_budget_never_acts():
    _, commands = _run(is_recording=True, grid_point=("1", 0))
    for got, want in zip(commands, _plain_commands(), strict=True):
        assert np.array_equal(got.leg_speed_m_s, want.leg_speed_m_s)


def test_budget_acting_in_a_period_ending_in_level_excludes_the_line():
    controller, _ = _run(is_recording=False, grid_point=("0.94", 2), switch_after_ramp_k=1)
    log = controller.__dict__[diag.LOG_ATTRIBUTE]
    block = diag.touch_budget_record(log)
    assert log.periods == []  # no recording hooks
    assert block["acted_by_end_phase"] == {"touch": 1, "level": 1}
    assert block["level_budget_periods"] == 1 and block["excluded"] is True


def test_install_twice_raises():
    diag.install(True, controller_class=StandIn)
    try:
        with pytest.raises(RuntimeError):
            diag.install(True, controller_class=StandIn)
    finally:
        diag.uninstall()
