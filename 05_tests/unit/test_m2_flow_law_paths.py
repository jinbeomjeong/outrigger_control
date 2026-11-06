"""M2 revision 3 on both plant paths (spec ``v5_hydraulic_impl_spec.md`` 2.3, M2-12, M2-13).

M2-12: the harness lag (``harness_hydraulics._RodPressureLag``) and the L2b state machine
(``RodChamberLeg`` with the law of ``L2bRodSide.set_rod_pressure_flow_law``) give the same rod
pressure for the same inputs. M2-13: the law on the valve input of the stored Hopsan C2 run reaches
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
from outrigger_sim.hydraulics.rod_release import RodPressureFlowLaw

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


def _hopsan_reference() -> tuple[dict, dict]:
    meta = json.loads((DATA_DIR / "m2_13_hopsan_c2_release.json").read_text(encoding="utf-8"))
    with np.load(DATA_DIR / "m2_13_hopsan_c2_release.npz") as arrays:
        return meta, {name: arrays[name] for name in arrays.files}


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
