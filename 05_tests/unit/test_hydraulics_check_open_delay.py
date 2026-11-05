"""M1c port ``hydraulics.check_open_delay`` (v5 spec 2.4, C-1 .. C-4, C-9).

The stored unit tables (``pressure_review/m1c/unit_m1c.json``, ``m1b/unit_m1b.json``) came from
scripts in ``04_scripts/03_control/m1_check``; the port must give the same numbers.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.hydraulics.check_open_delay import (
    UNIT_STATUS,
    CheckDelayCircuit,
    CheckDelayInputs,
    CheckOpenDelay,
    CheckValveValues,
    RetractConfig,
    head_opens,
    p_a_of_x,
    p_b_equalized,
    retract_dead,
    rod_opens,
)
from outrigger_sim.hydraulics.v5_options import CheckDelaySetting

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REVIEW = PROJECT_ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "pressure_review"
T9 = REVIEW / "m1_hopsan" / "t9_quintic"
BAR = 1e5
P_T = 2e5
LEG_RR = 3
FL = 0
RL = 2
TAU_V = 0.1
STROKE_TOLERANCE_MM = 1e-4
KIND_OF_MODE = {"vent_ref": "VN", "block_lowA": "BL"}


def _coupled_params():
    path = PROJECT_ROOT / "04_scripts" / "04_hydraulic" / "coupled" / "params.py"
    spec = importlib.util.spec_from_file_location("v5_coupled_params_c", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.load_params()


P = _coupled_params()
VALUES = CheckValveValues()


def _retract_cfg(rod_forward: bool) -> RetractConfig:
    return RetractConfig(rod_forward=rod_forward, volume_scale=1.0, v_line_m3=VALUES.v_line_m3,
                         beta_hose_Pa=VALUES.beta_hose_Pa, psi=VALUES.psi,
                         p_crack_Pa=VALUES.p_crack_Pa)


# --- C-1: E1 rows of unit_m1c.json ------------------------------------------------------------

def _e1_times(kind: str, p_r, p_h, v, duration, s0, F_s):
    """``unit_m1c.e1_times`` on the port's functions (single leg RR, valve lag, from rest)."""
    A_h, A_r = float(P.A_h[LEG_RR]), float(P.A_r[LEG_RR])
    c_r, c_l = A_r * (P.L0r + P.stroke - s0) / P.beta, 285e-6 / 0.5e9
    is_vent = kind == "VN"
    K_n = (VALUES.neutral_fraction if is_vent else 0.0) * A_h * P.v_max / math.sqrt(P.dp_comp)
    dt = 1e-4
    u = x = delivered = t = 0.0
    t_rod = stroke_rod = stroke_head = None
    p_b_after = None
    while t < duration + 0.3:
        command = v if t < duration else 0.0
        u += (command - u) * dt / TAU_V
        gate = max(1.0 - u / (0.02 * P.v_max), 0.0)
        p_a = p_a_of_x(VALUES, 1.0, x, A_h, P_T)
        x = max(x + (u - K_n * gate * math.sqrt(max(p_a - P_T, 0.0)) / A_h) * dt, 0.0)
        delivered += u * dt
        t += dt
        p_a = p_a_of_x(VALUES, 1.0, x, A_h, P_T)
        if t_rod is None and rod_opens(VALUES, is_vent, p_a, p_r, P_T, P_T):
            t_rod, stroke_rod = t, delivered
            p_b_after = p_b_equalized(p_r, P_T, c_r, c_l)
        if t_rod is not None:
            p_r_law = 2e5 + (p_r - 2e5) * math.exp(-(t - t_rod) / 0.05)
            p_h_now = p_h - max(A_r * (p_r - p_r_law) - F_s, 0.0) / A_h
            if head_opens(VALUES, p_a, min(p_b_after, p_r_law), p_h_now):
                stroke_head = delivered
                break
    return stroke_rod, stroke_head


def test_c1_port_reproduces_the_stored_vn_and_bl_rows() -> None:
    stored = json.loads((REVIEW / "m1c" / "unit_m1c.json").read_text(encoding="utf-8"))
    rows = {row["name"] + row["mode"]: row for row in stored["early_rows"]}
    inputs = json.loads((T9 / "early_unit.json").read_text(encoding="utf-8"))
    s0 = float(P.s0[LEG_RR])
    checked = 0
    for row in inputs:
        if row["mode"] not in KIND_OF_MODE:
            continue
        duration = min(0.003 / (row["v_mm_s"] * 1e-3), 6.0)
        rod, head = _e1_times(KIND_OF_MODE[row["mode"]], row["p_r_pre"] * BAR,
                              row["p_h_pre"] * BAR, row["v_mm_s"] * 1e-3, duration, s0, row["F_s"])
        expected = rows[row["name"] + row["mode"]]
        for new, old in ((rod, expected["m1c_rod_mm"]), (head, expected["m1c_head_mm"])):
            assert (new is None) == (old is None)
            if new is not None:
                assert abs(round(new * 1e3, 4) - old) <= STROKE_TOLERANCE_MM
        checked += 1
    assert checked == 60


# --- C-2: retract side of unit_m1b.json --------------------------------------------------------

def _rod_state_after_ramp(leg: int, creep_mm: float, crack_b: float) -> tuple[float, float]:
    """``unit_m1b.rod_state_after_ramp`` (bench timing, vent refill)."""
    A_ann = float(P.A_r[leg])
    v_rod = A_ann * (P.L0r + P.stroke - float(P.s0[leg]))
    K_n = 0.05 * float(P.A_h[leg]) * P.v_max / math.sqrt(P.dp_comp)
    y, dt, rate, floor = 2e5, 1e-3, creep_mm * 1e-3, -1e5
    for k in range(1200):
        sdot = rate if k < 1000 else 0.0
        q = K_n * math.sqrt(max(2e5 - max(y, floor) - crack_b, 0.0))
        y = min(y + (-A_ann * sdot + q) * P.beta / v_rod * dt, 2e5)
    return max(y, floor), max(floor - y, 0.0) * v_rod / P.beta / A_ann


def _t1_need_mm(row) -> float:
    mode, leg = row["mode"], row["leg"]
    p_T = 0.0 if "pT0" in mode else 2e5
    f_band = row["F_s_N"] if mode == "IC_floor" else 0.0
    rod_forward = mode in ("IC_floor", "ramp_floor_ref", "ramp_vent_pT0", "ramp_lowcrack")
    if mode in ("ramp_vent", "ramp_vent_stock", "ramp_lowcrack"):
        crack_b = 0.5e5 if mode == "ramp_lowcrack" else 0.0
        p_r, void = _rod_state_after_ramp(leg, row["creep_ramp_mm"], crack_b)
        rod_forward = False
    else:
        p_r, void = row["p_r_pre"] * BAR, row["void_mm"] * 1e-3
    values = retract_dead(_retract_cfg(rod_forward), row["p_h_pre"] * BAR, p_r, f_band,
                          float(P.s0[leg]), void, float(P.A_h[leg]), float(P.A_r[leg]), P.stroke,
                          P.L0r, P.L0h, P.beta, p_T)
    return round(values["need"] * 1e3, 4)


def test_c2_retract_port_reproduces_unit_m1b() -> None:
    stored = json.loads((REVIEW / "m1b" / "unit_m1b.json").read_text(encoding="utf-8"))
    inputs = {row["name"]: row
              for row in json.loads((REVIEW / "m1_hopsan" / "t1_floor.json").read_text("utf-8"))}
    assert stored["t1"]
    for row in stored["t1"]:
        assert _t1_need_mm(inputs[row["name"]]) == row["m1b_mm"]


# --- C-3, C-4: hand values ----------------------------------------------------------------------

def _circuit() -> CheckDelayCircuit:
    return CheckDelayCircuit(head_area_m2=P.A_h, annulus_area_m2=P.A_r, stroke_m=P.stroke,
                             rod_dead_length_m=P.L0r, head_dead_length_m=P.L0h,
                             bulk_modulus_Pa=P.beta, tank_pressure_Pa=P_T, max_speed_m_s=P.v_max,
                             compensator_drop_Pa=P.dp_comp)


def _extend_until_open(kind: str, leg: int, p_h_Pa: float) -> tuple[float, float]:
    """Stroke delivered into the line [mm] when the rod and the head check open."""
    model = CheckOpenDelay(CheckDelaySetting(kind), _circuit())
    dt, speed = 1e-4, 0.25 * P.v_max
    u = np.zeros(4)
    u[leg] = speed
    p_h = np.full(4, p_h_Pa)
    pushed = 0.0
    rod_at = None
    for k in range(200000):
        out = model.filter(CheckDelayInputs(k * dt, dt, u, p_h, np.full(4, 2 * BAR),
                                            np.ones(4, bool), np.zeros(4), np.zeros(4),
                                            P.s0.copy()))
        pushed += speed * dt
        if rod_at is None and model.rod_released[leg]:
            rod_at = pushed
        if model.is_open[leg]:
            assert out.speed_m_s[leg] > 0.0
            return rod_at * 1e3, pushed * 1e3
    raise AssertionError("the head check did not open")


@pytest.mark.parametrize("leg, p_h_bar, stroke_mm", [(FL, 89.5, 0.3586), (RL, 76.0, 0.4199)])
def test_c3_bl_head_opens_at_the_hand_line_stroke(leg, p_h_bar, stroke_mm) -> None:
    """BL (no drain): the head check opens at p_A = p_h + p_cr - psi p_B (85.5 / 72.0 bar)."""
    rod_mm, head_mm = _extend_until_open("BL", leg, p_h_bar * BAR)
    step_mm = 0.25 * P.v_max * 1e-4 * 1e3
    assert rod_mm <= step_mm  # BL rod check opens at once
    assert head_mm == pytest.approx(stroke_mm, abs=5e-5 + step_mm)


def test_c3_vn_rod_opens_at_2p857_bar() -> None:
    p_a_Pa = P_T + 0.857e5
    x_mm = (p_a_Pa - P_T) * VALUES.v_line_m3 / (float(P.A_h[FL]) * VALUES.beta_hose_Pa) * 1e3
    assert round(x_mm, 5) == 0.00368
    rod_mm, _ = _extend_until_open("VN", FL, 89.5 * BAR)
    assert rod_mm >= x_mm  # the vent drain makes the delivered stroke at least the line state


C4_TABLE = [  # (rod_forward, F_band kN, need, p_open bar, creep, discharge)
    (False, 0.0, 1.6311, 27.96, 0.3327, 0.4074),
    (False, 4.0, 1.4363, 27.03, 0.3207, 0.3933),
    (True, 0.0, 1.4714, 27.70, 0.2908, 0.4034),
    (True, 4.0, 1.2766, 26.76, 0.2788, 0.3894),
]


@pytest.mark.parametrize("rod_forward, band_kN, need, p_open, creep, discharge", C4_TABLE)
def test_c4_retract_hand_values(rod_forward, band_kN, need, p_open, creep, discharge) -> None:
    values = retract_dead(_retract_cfg(rod_forward), 89.5 * BAR, 2 * BAR, band_kN * 1e3, 0.4011,
                          0.0, float(P.A_h[FL]), float(P.A_r[FL]), P.stroke, P.L0r, P.L0h,
                          P.beta, P_T)
    assert round(values["need"] * 1e3, 4) == need
    assert round(values["p_open"] / BAR, 2) == p_open
    assert round(values["creep_ref"] * 1e3, 4) == creep
    assert round(values["discharge"] * 1e3, 4) == discharge


def test_c9_unit_status_and_left_out_variants() -> None:
    model = CheckOpenDelay(CheckDelaySetting("VN"), _circuit())
    assert model.meta()["unit_status"] == UNIT_STATUS == "below_criteria_reference_only"
    assert model.summary()["unit_status"] == UNIT_STATUS
    with pytest.raises(ValueError):
        CheckDelaySetting("VR")
    for key in ("e2", "e4", "no_delay", "rod_early"):
        with pytest.raises(ValueError):
            CheckDelaySetting.from_dict({"kind": "VN", key: True})


def test_retract_fill_holds_the_leg_creeps_and_opens() -> None:
    model = CheckOpenDelay(CheckDelaySetting("BL"), _circuit())
    dt = 1e-3
    u = np.zeros(4)
    u[FL] = -0.25 * P.v_max
    creep_total = 0.0
    opened = None
    counts = defaultdict(int)
    for k in range(5000):
        out = model.filter(CheckDelayInputs(k * dt, dt, u, np.full(4, 89.5 * BAR),
                                            np.full(4, 2 * BAR), np.ones(4, bool), np.zeros(4),
                                            np.zeros(4), np.full(4, 0.4011)))
        creep_total += out.creep_shift_m[FL]
        counts["hold"] += bool(out.lock_damping[FL])
        if out.opening_shift_m[FL] > 0.0:
            opened = out
            break
    assert opened is not None and counts["hold"] > 0
    assert opened.opening_rod_pressure_Pa[FL] / BAR == pytest.approx(27.96, abs=0.01)
    assert (creep_total + opened.opening_shift_m[FL] - 0.4074e-3) * 1e3 == pytest.approx(
        0.3327, abs=1e-4)
