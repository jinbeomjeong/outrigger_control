"""M2 revisions 3 and 4 on both plant paths (spec ``v5_hydraulic_impl_spec.md`` 2.3, M2-12,
M2-13).

M2-12: the harness lag (``harness_hydraulics._RodPressureLag``) and the L2b state machine
(``RodChamberLeg`` with the law of ``L2bRodSide.set_rod_pressure_flow_law``) give the same rod
pressure for the same inputs, and (revision 4) the same compensated pressure ``p + Delta w``.
M2-13: the law on the valve input of the stored Hopsan C2 run reaches
20 bar within 5 ms of Hopsan (``05_tests/data/m2_13_hopsan_c2_release.*``, hydraulics-expert run
of 2026-11-06). No pychrono, no numba.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest

from outrigger_sim.hydraulics.l2b_rod_side import L2bRodSide
from outrigger_sim.hydraulics.rod_chamber import RodChamberLegInput
from outrigger_sim.hydraulics.rod_release import (
    RodPressureFlowLaw,
    compensated_rod_pressure_Pa,
    release_weight,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HARNESS_HYDRAULICS = (PROJECT_ROOT / "04_scripts" / "04_hydraulic" / "coupled"
                      / "harness_hydraulics.py")
DATA_DIR = PROJECT_ROOT / "05_tests" / "data"
BAR = 1.0e5
STEP_S = 1.0e-4
LAG_S = 0.05
LOCK_EPS_M_S = 1.0e-6
CLOSING_DELAY_S = 100.0
"""Longer than the zero-speed stretch of the input sequence (0.05 s)."""
HEAD_AREA_M2 = (0.013273229, 0.013273229, 0.00950331778, 0.00950331778)
ANNULUS_M2 = (0.00376991118, 0.00376991118, 0.00314159265, 0.00314159265)
EXTENSION_M = (0.4011, 0.4011, 0.3909, 0.3909)
MAX_SPEED_M_S = 20.9243016e-3
FRONT_LEFT = 0
HOPSAN_START_S = 1.5
HOPSAN_END_S = 2.2
VALVE_GRID_S = 1.0e-3
LEVEL_PA = 20.0 * BAR
M2_13_TOLERANCE_S = 5.0e-3


def _load_harness_hydraulics() -> ModuleType:
    """The harness adapter by path (its folder is not a package)."""
    spec = importlib.util.spec_from_file_location("m2_harness_hydraulics", HARNESS_HYDRAULICS)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _rod_side() -> L2bRodSide:
    law = L2bRodSide(head_area_m2=HEAD_AREA_M2, annulus_area_m2=ANNULUS_M2,
                     k_out_N_m=[math.inf] * 4, bulk_modulus_Pa=1.0e9, head_dead_length_m=0.05,
                     rod_dead_length_m=[0.05] * 4, stroke_m=0.70,
                     p_r0_after_extend_Pa=[2.0 * BAR] * 4, p_r0_after_retract_Pa=[2.0 * BAR] * 4,
                     p_floor_abs_Pa=1.0e4, release_tau_s=LAG_S, lock_eps_m_s=LOCK_EPS_M_S)
    law.set_rod_pressure_flow_law(RodPressureFlowLaw())
    # the LC wait: the zero-speed stretch stays in the moving law, as on the harness
    law.set_closing_delay(CLOSING_DELAY_S)
    return law


def _harness_plant(rod_side: L2bRodSide) -> SimpleNamespace:
    """The plant attributes ``_RodPressureLag`` reads, at the same oil columns as ``rod_side``."""
    return SimpleNamespace(
        flow_limiter=SimpleNamespace(params=SimpleNamespace(A_h=np.array(HEAD_AREA_M2))),
        A_ann=np.array(ANNULUS_M2),
        kh=np.array([rod_side.head_stiffness_N_m(i, EXTENSION_M[i]) for i in range(4)]),
        kr=np.array([rod_side.rod_stiffness_N_m(i, EXTENSION_M[i]) for i in range(4)]),
        dt=STEP_S, tau=LAG_S)


def _input_sequence(leg: int) -> list[tuple[float, float]]:
    """(speed, cylinder force) per step: slow and fast moves both ways, a stop, reversals."""
    rng = np.random.default_rng(20261106 + leg)
    rows = []
    for fraction, steps in ((0.01, 3000), (-0.01, 6000), (0.0, 500), (-0.25, 2000),
                            (0.25, 3000), (-0.002, 2000), (0.6, 1000)):
        forces = 80.0e3 + 30.0e3 * rng.standard_normal(steps)
        rows.extend((fraction * MAX_SPEED_M_S, float(force)) for force in forces)
    return rows


@pytest.mark.parametrize("leg", range(4))
def test_m2_12_harness_and_l2b_give_the_same_pressure(leg: int) -> None:
    """Spec M2-12: same inputs -> same rod pressure (relative 1e-12) on every leg."""
    harness = _load_harness_hydraulics()
    rod_side = _rod_side()
    machine = rod_side._legs[leg]
    lag = harness._RodPressureLag(_harness_plant(rod_side))
    start_Pa = 12.0 * BAR
    lag.start(leg, start_Pa)
    machine.tracked_rod_pressure_Pa = start_Pa
    direction = 1.0
    worst = 0.0
    for k, (speed_m_s, force_N) in enumerate(_input_sequence(leg)):
        if abs(speed_m_s) > LOCK_EPS_M_S:
            direction = math.copysign(1.0, speed_m_s)
        from_harness = lag.relax(leg, direction, force_N, speed_m_s)
        machine.step(RodChamberLegInput(
            time_s=k * STEP_S, step_s=STEP_S, applied_speed_m_s=speed_m_s, pad_deflection_m=0.0,
            pad_deflection_rate_m_s=0.0, motor_position_m=EXTENSION_M[leg],
            cylinder_force_N=force_N))
        from_l2b = machine.tracked_rod_pressure_Pa
        worst = max(worst, abs(from_harness - from_l2b) / max(abs(from_l2b), 1.0))
    assert not machine.is_locked  # both paths stayed in their moving law
    assert worst <= 1e-12


RELEASE_DROP_PA = -82.72 * BAR
"""``Delta`` of a lifted leg (2 bar lock, about 84.7 bar at the release; P-1 hand value)."""


@pytest.mark.parametrize("leg", range(4))
def test_m2_12_harness_and_l2b_give_the_same_compensated_pressure(leg: int) -> None:
    """Spec M2-12, revision 4: ``p_hat = p + Delta w`` is the same on both paths (relative
    1e-12); the harness ``w`` is ``release_weight(t - t_rel, tau)``, the L2b ``w`` the release
    decay of the rod-side machine. Both legs are released at t = 0."""
    harness = _load_harness_hydraulics()
    rod_side = _rod_side()
    machine = rod_side._legs[leg]
    lag = harness._RodPressureLag(_harness_plant(rod_side))
    start_Pa = 84.72 * BAR
    lag.start(leg, start_Pa)
    machine.tracked_rod_pressure_Pa = start_Pa
    machine.release_time_s = 0.0  # as if the machine had left its lock at t = 0
    direction = 1.0
    worst = 0.0
    for k, (speed_m_s, force_N) in enumerate(_input_sequence(leg)):
        if abs(speed_m_s) > LOCK_EPS_M_S:
            direction = math.copysign(1.0, speed_m_s)
        t_s = k * STEP_S
        harness_p_Pa = lag.relax(leg, direction, force_N, speed_m_s)
        harness_hat = compensated_rod_pressure_Pa(
            harness_p_Pa, RELEASE_DROP_PA, release_weight(t_s - 0.0, LAG_S))
        machine.step(RodChamberLegInput(
            time_s=t_s, step_s=STEP_S, applied_speed_m_s=speed_m_s, pad_deflection_m=0.0,
            pad_deflection_rate_m_s=0.0, motor_position_m=EXTENSION_M[leg],
            cylinder_force_N=force_N))
        l2b_hat = compensated_rod_pressure_Pa(
            machine.tracked_rod_pressure_Pa, RELEASE_DROP_PA, machine.release_decay())
        worst = max(worst, abs(float(harness_hat - l2b_hat)) / max(abs(float(l2b_hat)), 1.0))
    assert not machine.is_locked
    assert machine.release_decay() < 1e-6  # the sequence runs out the decay
    assert worst <= 1e-12


ANCHOR_START_PA = 34.818 * BAR
ANCHOR_FORCE_N = 94.0e3
ANCHOR_CASES = ((0.01, 0.5), (0.10, 0.1), (0.01, 1.0), (0.25, 0.1), (0.01, 5.0))
"""r5 spec U1, U2, U2b, U3b, U3: (fraction of v_max, extension time [s])."""


def _anchor_rod_side() -> L2bRodSide:
    """Two legs (FL, RL) locked after a retract at 34.818 bar, M2 on, no LC wait."""
    law = L2bRodSide(head_area_m2=HEAD_AREA_M2[::2], annulus_area_m2=ANNULUS_M2[::2],
                     k_out_N_m=[math.inf] * 2, bulk_modulus_Pa=1.0e9, head_dead_length_m=0.05,
                     rod_dead_length_m=[0.05] * 2, stroke_m=0.70,
                     p_r0_after_extend_Pa=[2.0 * BAR] * 2,
                     p_r0_after_retract_Pa=[ANCHOR_START_PA] * 2, p_floor_abs_Pa=1.0e4,
                     release_tau_s=LAG_S, lock_eps_m_s=LOCK_EPS_M_S)
    law.set_rod_pressure_flow_law(RodPressureFlowLaw())
    return law


def _l2b_extension_anchor(fraction: float, duration_s: float) -> np.ndarray:
    """L2b: retract-lock, extend, stop; the lock anchor of both legs."""
    law = _anchor_rod_side()
    stroke_m = np.array(EXTENSION_M[::2])
    head_stiffness = np.array([law.head_stiffness_N_m(i, stroke_m[i]) for i in range(2)])
    compression_m = ANCHOR_FORCE_N / head_stiffness
    force_N = np.full(2, ANCHOR_FORCE_N)
    t_s = 0.0
    speeds = ([-0.01 * MAX_SPEED_M_S] * 20 + [0.0] * 6
              + [fraction * MAX_SPEED_M_S] * round(duration_s / STEP_S) + [0.0])
    for speed_m_s in speeds:
        law.spring_force_N(t_s, STEP_S, np.full(2, speed_m_s), stroke_m, compression_m, force_N)
        t_s += STEP_S
    return law.lock_anchor_rod_pressure_Pa


@pytest.mark.parametrize("fraction, duration_s", ANCHOR_CASES)
def test_m2_12_r5_extension_anchor_is_the_same_on_both_paths(fraction, duration_s) -> None:
    """M2-12, revision 5: the harness anchor ``p_ext + _RodPressureLag.extension_excess_Pa``
    (floor ``p_floor``) equals the L2b lock anchor for the same extension at the same oil
    columns and step (relative 1e-12)."""
    harness = _load_harness_hydraulics()
    rod_side = _rod_side()
    lag = harness._RodPressureLag(_harness_plant(rod_side))
    l2b_anchor_Pa = _l2b_extension_anchor(fraction, duration_s)
    floor_Pa = 1.0e4 - 101325.0
    for index, leg in enumerate((0, 2)):
        lag.start(leg, ANCHOR_START_PA)
        for _ in range(round(duration_s / STEP_S)):
            lag.relax(leg, 1.0, ANCHOR_FORCE_N, fraction * MAX_SPEED_M_S)
        harness_anchor_Pa = max(2.0 * BAR + lag.extension_excess_Pa(leg, ANCHOR_FORCE_N),
                                floor_Pa)
        assert harness_anchor_Pa == pytest.approx(float(l2b_anchor_Pa[index]), rel=1e-12)


def _hopsan_reference() -> tuple[dict, dict]:
    """Meta and the series; each ``.npy`` holds rows (time, value) (``*.npz`` is git-ignored)."""
    meta = json.loads((DATA_DIR / "m2_13_hopsan_c2_release.json").read_text(encoding="utf-8"))
    hopsan = np.load(DATA_DIR / "m2_13_hopsan_c2_release_hopsan.npy", allow_pickle=False)
    valve = np.load(DATA_DIR / "m2_13_hopsan_c2_release_valve.npy", allow_pickle=False)
    return meta, {"hopsan_t_s": hopsan[0], "hopsan_rod_pressure_FL_Pa": hopsan[1],
                  "valve_t_s": valve[0], "valve_speed_FL_m_s": valve[1]}


def _first_time_at_or_below(t_s: np.ndarray, pressure_Pa: np.ndarray, level_Pa: float) -> float:
    index = np.flatnonzero((pressure_Pa <= level_Pa) & (t_s >= HOPSAN_START_S))
    return float(t_s[index[0]])


def test_m2_13_law_reaches_20_bar_with_hopsan() -> None:
    """Spec M2-13: FL extends from a 34.818 bar lock on the Hopsan valve input; the 20 bar
    crossing of the law is within 5 ms of the stored Hopsan C2 run (hydraulics-expert 1.8 ms)."""
    meta, series = _hopsan_reference()
    law = RodPressureFlowLaw()
    compliance = law.rod_compliance_m3_Pa(meta["annulus_area_FL_m2"],
                                          meta["head_stiffness_FL_N_m"],
                                          meta["rod_stiffness_FL_N_m"])
    valve_t, valve_speed = series["valve_t_s"], series["valve_speed_FL_m_s"]
    first_grid = round(valve_t[0] / VALVE_GRID_S)
    pressure_Pa = meta["rod_pressure_start_Pa"]
    times, pressures = [], []
    for k in range(round((HOPSAN_END_S - HOPSAN_START_S) / STEP_S) + 1):
        t_s = HOPSAN_START_S + k * STEP_S
        j = min(round(t_s / VALVE_GRID_S) - first_grid, len(valve_t) - 1)
        speed_m_s = float(valve_speed[j])
        if speed_m_s > 0.0:
            pressure_Pa = law.rod_pressure_Pa(
                pressure_Pa, meta["extend_target_Pa"], speed_m_s, STEP_S, meta["lag_s"],
                compliance, meta["head_area_FL_m2"], meta["annulus_area_FL_m2"],
                is_retract=False)
        times.append(t_s)
        pressures.append(pressure_Pa)
    law_s = _first_time_at_or_below(np.array(times), np.array(pressures), LEVEL_PA)
    hopsan_s = _first_time_at_or_below(series["hopsan_t_s"], series["hopsan_rod_pressure_FL_Pa"],
                                       LEVEL_PA)
    assert hopsan_s == pytest.approx(meta["hopsan_t_to_20bar_s"], abs=1e-12)
    assert abs(law_s - hopsan_s) <= M2_13_TOLERANCE_S
