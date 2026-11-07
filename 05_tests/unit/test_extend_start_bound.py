"""Option ``extend_start_rule = "tracked_bound"`` (spec ``p3_extend_start_spec.md`` 4, with the
hydraulics-expert review of 2026-11-07): the recursive bound against the plant law.

T-P3-2: the r5 replica cases (s 0.30 m); T-P3-3: property test, seed 20261107, 1,000 random
command sequences against the plant law at the plant steps (L2b 1e-4 s, harness 5e-4 s) with the
nominal and the sensitivity-end parameters (B hose +36 %).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from outrigger_sim.control.extend_start_bound import (
    BoundGeometry,
    ExtendStartBound,
    ExtendStartTracker,
)
from outrigger_sim.hydraulics.rod_release import (
    METER_OUT_RATIO,
    SPOOL_REFERENCE_DROP_PA,
    TANK_PRESSURE_PA,
    flow_limited_rod_pressure,
)

BAR = 1.0e5
HEAD_AREA_M2 = (0.013273229, 0.013273229, 0.00950331778, 0.00950331778)
ANNULUS_M2 = (0.00376991118, 0.00376991118, 0.00314159265, 0.00314159265)
RETRACT_ANCHOR_PA = (34.818 * BAR, 34.352 * BAR, 31.193 * BAR, 30.591 * BAR)
STROKE_MAX_M = 0.70
MAX_SPEED_M_S = 20.9243016e-3
VALVE_TAU_S = 0.1
PERIOD_S = 0.1
LAG_S = 0.05
BACK_PRESSURE_PA = 5.0 * BAR
FORCE_N = 94.0e3
CONSTANT_START_PA = 13.0 * BAR
P_EXT_PA = 2.0 * BAR


def _tracker(start_Pa=RETRACT_ANCHOR_PA, bound: ExtendStartBound | None = None
             ) -> ExtendStartTracker:
    geometry = BoundGeometry(HEAD_AREA_M2, ANNULUS_M2, STROKE_MAX_M, MAX_SPEED_M_S, VALVE_TAU_S)
    return ExtendStartTracker(bound or ExtendStartBound(), geometry, start_Pa)


def _advance(tracker: ExtendStartTracker, command_m_s, stroke_m) -> None:
    tracker.advance(command_m_s, stroke_m, np.full(4, FORCE_N), RETRACT_ANCHOR_PA, PERIOD_S)


# --- T-P3-2 ---------------------------------------------------------------------------------

REPLICA_STROKE_M = 0.30
T_P3_2_CASES = (
    # (name, fraction, time [s], p_tr FL, p_tr RL [bar]) from r5_spec.md (1-leg replica)
    ("U1", 0.01, 0.5, 23.7957, 25.4655),
    ("U2", 0.10, 0.1, 15.0179, 17.6757),
    ("U2b", 0.01, 1.0, 15.0211, None),
    ("U3", 0.01, 5.0, 5.0, 5.0),
    ("U3b", 0.25, 0.1, 9.0354, None),
)


@pytest.mark.parametrize("name, fraction, duration_s, fl_bar, rl_bar", T_P3_2_CASES)
def test_t_p3_2_start_value_covers_the_r5_replica(name, fraction, duration_s, fl_bar,
                                                    rl_bar) -> None:
    """The start value ``max(13 bar, p + delta_m)`` at the first command-free read is at least
    the plant ``p_tr`` and the B anchor ``p_ext + (p_tr - p*)^+`` (spec T-P3-2)."""
    tracker = _tracker()
    command = np.zeros(4)
    command[[0, 2]] = fraction * MAX_SPEED_M_S
    stroke = np.full(4, REPLICA_STROKE_M)
    for _ in range(round(duration_s / PERIOD_S)):
        _advance(tracker, command, stroke)
    _advance(tracker, np.zeros(4), stroke)  # the first command-free read (valve tail)
    for leg, plant_bar in ((0, fl_bar), (2, rl_bar)):
        if plant_bar is None:
            continue
        start_Pa = max(CONSTANT_START_PA, tracker.bound_Pa(leg))
        plant_Pa = plant_bar * BAR
        anchor_Pa = P_EXT_PA + max(plant_Pa - BACK_PRESSURE_PA, 0.0)
        assert start_Pa >= plant_Pa
        assert start_Pa >= anchor_Pa
        over_kN = (start_Pa - anchor_Pa) * ANNULUS_M2[leg] / 1e3
        assert over_kN < 15.0, f"{name} leg {leg}: over-conservatism {over_kN:.2f} kN"


def test_relief_is_not_counted_below_the_overlap_cut() -> None:
    """A 1 % ``v_max`` command stays below ``delta_ol`` 5 %: no relief, the bound keeps
    ``p_ret``."""
    tracker = _tracker()
    command = np.array([0.01 * MAX_SPEED_M_S, 0.0, 0.0, 0.0])
    for _ in range(20):
        _advance(tracker, command, np.full(4, 0.3))
    assert tracker.pressure_Pa[0] == RETRACT_ANCHOR_PA[0]


def test_saturated_pump_or_stroke_end_counts_no_relief() -> None:
    """Review 2026-11-07 (2a, 2b): pump demand above ``eta_v Q_pump`` or a stroke reading at
    the end margin: ``u_lb = 0``."""
    saturated = _tracker()
    all_up = np.full(4, MAX_SPEED_M_S)
    saturated.valve_m_s = all_up.copy()  # past the ramp: 4 legs at v_max need 0.95 Q_pump
    for _ in range(10):
        _advance(saturated, all_up, np.full(4, 0.3))
    assert saturated.saturated_substeps > 0
    assert np.array_equal(saturated.pressure_Pa, np.array(RETRACT_ANCHOR_PA))
    at_end = _tracker()
    command = np.array([0.5 * MAX_SPEED_M_S, 0.0, 0.0, 0.0])
    for _ in range(10):
        _advance(at_end, command, np.array([0.6848, 0.3, 0.3, 0.3]))
    assert at_end.pressure_Pa[0] == RETRACT_ANCHOR_PA[0]
    free = _tracker()
    for _ in range(10):
        _advance(free, command, np.full(4, 0.3))
    assert free.pressure_Pa[0] < 10.0 * BAR


def test_retract_period_raises_the_bound_to_the_retract_floor() -> None:
    tracker = _tracker(start_Pa=np.full(4, 6.0 * BAR))
    _advance(tracker, np.array([-0.1 * MAX_SPEED_M_S, 0.0, 0.0, 0.0]), np.full(4, 0.3))
    assert tracker.pressure_Pa[0] == RETRACT_ANCHOR_PA[0]
    assert tracker.pressure_Pa[1] == 6.0 * BAR


def test_tension_substeps_count_a_pull_beyond_the_back_pressure() -> None:
    """Review item ①: an extending leg pulled beyond ``p_bB A_ann`` (FL 1.88 kN) is counted."""
    tracker = _tracker()
    force = np.array([-1.9e3, -1.8e3, FORCE_N, FORCE_N])
    command = np.array([0.1, 0.1, 0.0, 0.0]) * MAX_SPEED_M_S
    tracker.advance(command, np.full(4, 0.3), force, RETRACT_ANCHOR_PA, PERIOD_S)
    assert tracker.tension_substeps.tolist() == [100, 0, 0, 0]


def test_bound_parameters_can_be_replaced() -> None:
    """The ASSUMPTION values are settings (hydraulics-expert review may change them)."""
    plain = _tracker(bound=ExtendStartBound(hose_factor=1.0))
    assert plain.compliance_m3_Pa(0, 0.3) == pytest.approx(
        _tracker().compliance_m3_Pa(0, 0.3) / 1.40, rel=1e-12)
    with pytest.raises(ValueError):
        ExtendStartBound(speed_factor=1.5)


# --- T-P3-3 ---------------------------------------------------------------------------------

PROPERTY_SEED = 20261107
PROPERTY_SEQUENCES = 1000
PLANT_STEPS_S = (1.0e-4, 5.0e-4)
"""The plant steps: L2b and the harness kernel."""
PLANT_BULK_MODULI_PA = (0.69e9, 1.0e9, 1.6e9)
PLANT_HEAD_DEAD_M = (0.05, 0.08)
PLANT_ROD_DEAD_M = (0.02, 0.05, 0.10)
PLANT_HOSE_FACTORS = (1.0, 1.36)
PROPERTY_PERIODS = 24
"""2.4 s per sequence: the risk is a short extension after a retract lock."""
ROUNDING_PA = 1.0e-6
"""Both sides reach the same held or lagged value up to rounding (seen: 1.5e-9 Pa)."""


def _plant_compliance(leg, beta, head_dead, rod_dead, hose, stroke_m):
    head = beta * np.asarray(HEAD_AREA_M2)[leg] / (head_dead + stroke_m)
    annulus = np.asarray(ANNULUS_M2)[leg]
    rod = beta * annulus / (rod_dead + STROKE_MAX_M - stroke_m)
    return hose * annulus**2 * (1.0 / rod + 1.0 / head)


def _plant_step(pressure, target, speed, step_s, compliance, leg, is_retract):
    """:func:`flow_limited_rod_pressure` over arrays (checked against it below)."""
    head = np.asarray(HEAD_AREA_M2)[leg]
    annulus = np.asarray(ANNULUS_M2)[leg]
    lagged = target + (pressure - target) * math.exp(-step_s / LAG_S)
    fill = pressure + annulus * np.abs(speed) * step_s / compliance
    drop = np.sqrt(np.maximum(pressure - TANK_PRESSURE_PA, 0.0) / SPOOL_REFERENCE_DROP_PA)
    drain = pressure - METER_OUT_RATIO * head * np.abs(speed) * drop * step_s / compliance
    return np.where(is_retract & (target > pressure), np.minimum(lagged, fill),
                    np.where(~is_retract & (target < pressure), np.maximum(lagged, drain),
                             lagged))


def _random_sequences(rng: np.random.Generator) -> dict[str, np.ndarray]:
    """Per sequence: the leg, plant parameters, start stroke, retract target and the acting
    command of each period (extend, retract, zero; sizes 1 %-100 % v_max, 1-8 periods)."""
    count = PROPERTY_SEQUENCES
    periods = PROPERTY_PERIODS
    commands = np.zeros((count, periods))
    for row in range(count):
        position = 0
        while position < periods:
            length = int(rng.integers(1, 9))
            kind = rng.choice(3, p=(0.5, 0.2, 0.3))
            size = 10.0 ** rng.uniform(-2.0, 0.0) * MAX_SPEED_M_S
            value = (size, -size, 0.0)[kind]
            commands[row, position:position + length] = value
            position += length
    return {
        "leg": rng.choice([0, 2], size=count),
        "beta": rng.choice(PLANT_BULK_MODULI_PA, size=count),
        "head_dead": rng.choice(PLANT_HEAD_DEAD_M, size=count),
        "rod_dead": rng.choice(PLANT_ROD_DEAD_M, size=count),
        "hose": rng.choice(PLANT_HOSE_FACTORS, size=count),
        "stroke": rng.uniform(0.02, 0.6, size=count),
        "retract_target": rng.uniform(20.0, 60.0, size=count) * BAR,
        "commands": commands,
    }


def _plant_at_substeps(sequences, step_s: float) -> tuple[np.ndarray, np.ndarray]:
    """Plant rod pressure at every 1 ms boundary and the stroke at every period start."""
    leg = sequences["leg"]
    commands = sequences["commands"]
    count, periods = commands.shape
    pressure = np.asarray(RETRACT_ANCHOR_PA)[leg].copy()
    valve = np.zeros(count)
    stroke = sequences["stroke"].copy()
    steps_per_ms = round(1.0e-3 / step_s)
    samples = np.empty((count, periods * 100))
    strokes = np.empty((count, periods))
    keep = math.exp(-step_s / VALVE_TAU_S)
    for period in range(periods):
        strokes[:, period] = stroke
        command = commands[:, period]
        for substep in range(100):
            for _ in range(steps_per_ms):
                valve = command + (valve - command) * keep
                is_retract = valve < 0.0
                target = np.where(is_retract, sequences["retract_target"], BACK_PRESSURE_PA)
                compliance = _plant_compliance(leg, sequences["beta"], sequences["head_dead"],
                                               sequences["rod_dead"], sequences["hose"], stroke)
                pressure = _plant_step(pressure, target, valve, step_s, compliance, leg,
                                       is_retract)
                stroke = np.clip(stroke + valve * step_s, 0.0, STROKE_MAX_M)
            samples[:, period * 100 + substep] = pressure
    return samples, strokes


def test_vectorised_plant_step_is_the_plant_function() -> None:
    rng = np.random.default_rng(1)
    for _ in range(200):
        leg = int(rng.choice([0, 2]))
        pressure, target = rng.uniform(1.0, 60.0, size=2) * BAR
        speed = rng.uniform(-1.0, 1.0) * MAX_SPEED_M_S
        compliance = float(_plant_compliance(leg, 1.0e9, 0.05, 0.05, 1.0, 0.3))
        is_retract = speed < 0.0
        expected = flow_limited_rod_pressure(pressure, target, speed, 1e-4, LAG_S, compliance,
                                             HEAD_AREA_M2[leg], ANNULUS_M2[leg], is_retract)
        got = _plant_step(np.array([pressure]), np.array([target]), np.array([speed]), 1e-4,
                          compliance, leg, np.array([is_retract]))
        assert float(got[0]) == pytest.approx(expected, rel=1e-13, abs=1e-6)


@pytest.mark.parametrize("plant_step_s", PLANT_STEPS_S)
def test_t_p3_3_bound_is_above_the_plant_at_every_substep(plant_step_s: float) -> None:
    """Spec T-P3-3 (review: at the plant steps): ``p >= p_plant`` at every 1 ms sub-step of
    1,000 random sequences; the plant runs at the valve speed itself (no flow share, no
    overlap cut: its fastest relief) with nominal or sensitivity-end oil (B hose +36 %)."""
    sequences = _random_sequences(np.random.default_rng(PROPERTY_SEED))
    plant, strokes = _plant_at_substeps(sequences, plant_step_s)
    violations, worst_Pa = 0, -math.inf
    for row in range(PROPERTY_SEQUENCES):
        leg = int(sequences["leg"][row])
        floor = np.array(RETRACT_ANCHOR_PA)
        floor[leg] = max(floor[leg], sequences["retract_target"][row])
        tracker = _tracker()
        for period in range(sequences["commands"].shape[1]):
            command = np.zeros(4)
            command[leg] = sequences["commands"][row, period]
            stroke = np.full(4, 0.3)
            stroke[leg] = strokes[row, period]
            values = _substep_bounds(tracker, command, stroke, floor)
            plant_values = plant[row, period * 100:(period + 1) * 100]
            gap = plant_values - values[:, leg]
            violations += int(np.sum(gap > ROUNDING_PA))
            worst_Pa = max(worst_Pa, float(gap.max()))
    assert violations == 0, f"{violations} sub-steps above the bound, worst {worst_Pa / BAR} bar"


def _substep_bounds(tracker, command, stroke, floor) -> np.ndarray:
    """The tracker's ``p`` after every sub-step of one period (its own advance, one sub-step
    at a time: the retract floor and the stroke are the same in every call of the period)."""
    bound = tracker.bound
    values = np.empty((100, 4))
    for substep in range(100):
        tracker.advance(command, stroke, np.full(4, FORCE_N), floor, bound.substep_s)
        values[substep] = tracker.pressure_Pa
    return values
