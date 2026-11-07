"""Option ``extend_start_rule = "tracked_bound"`` (spec ``p3_extend_start_spec.md`` 4, with the
hydraulics-expert review of 2026-11-07): the recursive bound against the plant law.

T-P3-2: the r5 replica cases (s 0.30 m); T-P3-3: property test, seed 20261107, 1,000 random
command sequences against the plant law at the plant steps (L2b 1e-4 s, harness 5e-4 s) with the
nominal and the sensitivity-end parameters (B hose +36 %). v2 (user decision 2026-11-07): the
overlap cut holds only with a zero acting command.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from outrigger_sim.control.extend_start_bound import (
    EXTEND_START_REVISION,
    BoundGeometry,
    ExtendStartBound,
    ExtendStartTracker,
    PremiseRecord,
    check_extend_start_meta,
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
    tracker.advance(command_m_s, stroke_m, RETRACT_ANCHOR_PA, PERIOD_S)


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


def test_small_non_zero_command_counts_relief_below_the_overlap_cut() -> None:
    """v2 (user decision 2026-11-07, spec 3 (i)): a 1 % ``v_max`` command is below
    ``delta_ol`` 5 % but flows in the plant (L-6), so the bound counts ``kappa_x`` times the
    sub-step mean of ``u_v`` and relieves; v1 kept ``p_ret`` here (Dg-2 over-conservatism,
    spec 8)."""
    tracker = _tracker()
    command = np.array([0.01 * MAX_SPEED_M_S, 0.0, 0.0, 0.0])
    stroke = np.full(4, 0.3)
    expected_Pa = RETRACT_ANCHOR_PA[0]
    expected_valve = 0.0
    keep = math.exp(-1.0e-3 / VALVE_TAU_S)
    mean_share = VALVE_TAU_S / 1.0e-3 * (1.0 - keep)
    compliance = tracker.compliance_m3_Pa(0, 0.3)
    for _ in range(20):
        _advance(tracker, command, stroke)
        for _ in range(100):
            mean_valve = command[0] + (expected_valve - command[0]) * mean_share
            expected_valve = command[0] + (expected_valve - command[0]) * keep
            expected_Pa = flow_limited_rod_pressure(
                expected_Pa, BACK_PRESSURE_PA, 0.8 * mean_valve, 1.0e-3, LAG_S, compliance,
                HEAD_AREA_M2[0], ANNULUS_M2[0], False)
    assert tracker.valve_m_s[0] < 0.05 * MAX_SPEED_M_S
    assert tracker.pressure_Pa[0] == pytest.approx(expected_Pa, rel=1e-12)
    assert tracker.pressure_Pa[0] < RETRACT_ANCHOR_PA[0] - 1.0 * BAR
    assert tracker.pressure_Pa[1:].tolist() == list(RETRACT_ANCHOR_PA[1:])


def test_zero_command_tail_below_the_overlap_cut_holds() -> None:
    """With a zero acting command and ``u_v`` below 5 % ``v_max`` the plant cuts the tail:
    no relief is counted, the bound holds."""
    for zero_command_m_s in (0.0, 0.5e-6):  # the plant's zero is |u| <= 1e-6 m/s
        tracker = _tracker()
        tracker.valve_m_s = np.array([0.04 * MAX_SPEED_M_S, 0.0, 0.0, 0.0])
        for _ in range(5):
            _advance(tracker, np.array([zero_command_m_s, 0.0, 0.0, 0.0]), np.full(4, 0.3))
        assert tracker.pressure_Pa[0] == RETRACT_ANCHOR_PA[0]


def test_negative_valve_under_an_extend_command_counts_no_relief() -> None:
    """Right after a retract the valve is still negative under a small extend command: the
    plant fills, so the bound does not relieve until ``u_v > 0``."""
    tracker = _tracker()
    tracker.valve_m_s = np.array([-0.5 * MAX_SPEED_M_S, 0.0, 0.0, 0.0])
    tracker.advance(np.array([0.01 * MAX_SPEED_M_S, 0.0, 0.0, 0.0]), np.full(4, 0.3),
                    RETRACT_ANCHOR_PA, 1.0e-3)
    assert tracker.valve_m_s[0] < 0.0
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


def test_saturation_early_in_a_falling_sub_step_counts_no_relief() -> None:
    """v2 review (spec 3 (ii)): four valves fall through the ``eta_v Q_pump`` demand within one
    sub-step. The end values alone are below it; the start values are above it, so the sub-step
    is saturated and no relief is counted."""
    bound = ExtendStartBound()
    demand_per_speed = 2.0 * HEAD_AREA_M2[0] + 2.0 * HEAD_AREA_M2[2]
    threshold_m_s = bound.volumetric_efficiency * bound.pump_flow_m3_s / demand_per_speed
    command_m_s = 0.5 * MAX_SPEED_M_S
    keep = math.exp(-bound.substep_s / VALVE_TAU_S)
    end_m_s = 0.999 * threshold_m_s
    start_m_s = command_m_s + (end_m_s - command_m_s) / keep
    assert start_m_s > threshold_m_s > end_m_s
    tracker = _tracker()
    tracker.valve_m_s = np.full(4, start_m_s)
    tracker.advance(np.full(4, command_m_s), np.full(4, 0.3), RETRACT_ANCHOR_PA, bound.substep_s)
    assert tracker.valve_m_s[0] == pytest.approx(end_m_s, rel=1e-12)
    assert tracker.saturated_substeps == 1
    assert np.array_equal(tracker.pressure_Pa, np.array(RETRACT_ANCHOR_PA))


def test_premise_record_counts_a_pull_beyond_the_back_pressure() -> None:
    """Review item ①: an extending leg pulled beyond ``p_bB A_ann`` (FL 1.88 kN) is counted
    per 1 ms sub-step of the period; a retracting or still leg is not."""
    record = PremiseRecord(ANNULUS_M2)
    force = np.array([-1.9e3, -1.8e3, -1.9e3, FORCE_N])
    command = np.array([0.1, 0.1, -0.1, 0.1]) * MAX_SPEED_M_S
    record.count_tension(command, force, PERIOD_S)
    record.add_d2_start(2, 0.2e-3, 1.0e-3)
    record.add_d2_start(2, None, 1.0e-3)
    meta = record.to_meta()
    assert meta["tension_substeps"] == [100, 0, 0, 0]
    assert meta["tension_threshold_N"][0] == pytest.approx(1884.96, abs=0.01)
    assert meta["d2_violation_start_ratio"] == [[], [], [pytest.approx(0.2), None], []]


def test_bound_parameters_can_be_replaced() -> None:
    """The ASSUMPTION values are settings (hydraulics-expert review may change them)."""
    plain = _tracker(bound=ExtendStartBound(hose_factor=1.0))
    assert plain.compliance_m3_Pa(0, 0.3) == pytest.approx(
        _tracker().compliance_m3_Pa(0, 0.3) / 1.40, rel=1e-12)
    with pytest.raises(ValueError):
        ExtendStartBound(speed_factor=1.5)


def test_revision_is_in_the_meta_and_v1_meta_is_refused() -> None:
    """v2 review: the bound meta carries ``revision`` 2; a ``tracked_bound`` meta without it
    (v1) or with another revision is refused; a ``constant`` meta is not checked."""
    meta = ExtendStartBound().to_meta()
    assert meta["revision"] == EXTEND_START_REVISION == 2
    check_extend_start_meta({"extend_start_rule": "tracked_bound", "extend_start_bound": meta})
    check_extend_start_meta({"locked_ratio_rule": "column"})
    v1 = {key: value for key, value in meta.items() if key != "revision"}
    with pytest.raises(ValueError, match="v1"):
        check_extend_start_meta({"extend_start_rule": "tracked_bound", "extend_start_bound": v1})
    with pytest.raises(ValueError, match="revision 3"):
        check_extend_start_meta({"extend_start_rule": "tracked_bound",
                                 "extend_start_bound": {**meta, "revision": 3}})
    with pytest.raises(ValueError, match="revision"):
        ExtendStartBound(revision=1)


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
        tracker.advance(command, stroke, floor, bound.substep_s)
        values[substep] = tracker.pressure_Pa
    return values


# --- T-P3-3, priority saturation with falling valves (v2 review, spec 3 (ii)) ---------------

SATURATION_SEQUENCES = 300
SATURATION_PERIODS = 6
PLANT_VOLUMETRIC_EFFICIENCIES = (0.85, 0.95)
"""The plant's ``eta_v`` (VB 0.85, nominal 0.95); the bound uses 0.85."""
LEGS = np.arange(4)


def _saturation_sequences(rng: np.random.Generator) -> dict[str, np.ndarray]:
    """Four legs extending at 0.85-1.0 ``v_max`` (demand above ``eta_v Q_pump``), then falling
    commands of 0.2-0.95 ``v_max`` per period: the valves cross the saturation demand inside a
    sub-step."""
    count = SATURATION_SEQUENCES
    commands = rng.uniform(0.2, 0.95, size=(count, SATURATION_PERIODS, 4)) * MAX_SPEED_M_S
    return {
        "start_valve": rng.uniform(0.85, 1.0, size=(count, 4)) * MAX_SPEED_M_S,
        "commands": commands,
        "eta": rng.choice(PLANT_VOLUMETRIC_EFFICIENCIES, size=(count, 1)),
        "beta": rng.choice(PLANT_BULK_MODULI_PA, size=(count, 1)),
        "head_dead": rng.choice(PLANT_HEAD_DEAD_M, size=(count, 1)),
        "rod_dead": rng.choice(PLANT_ROD_DEAD_M, size=(count, 1)),
        "hose": rng.choice(PLANT_HOSE_FACTORS, size=(count, 1)),
        "stroke": rng.uniform(0.02, 0.6, size=(count, 4)),
    }


def _saturated_plant_at_substeps(sequences, step_s: float) -> tuple[np.ndarray, np.ndarray]:
    """Plant rod pressure of the four legs at every 1 ms boundary and the strokes at every
    period start. While the plant's demand ``sum A_h u_v`` exceeds its ``eta_v Q_pump`` every
    leg delivers 0 (the worst flow share: no relief)."""
    bound = ExtendStartBound()
    count = SATURATION_SEQUENCES
    pressure = np.tile(np.asarray(RETRACT_ANCHOR_PA), (count, 1))
    valve = sequences["start_valve"].copy()
    stroke = sequences["stroke"].copy()
    supply_m3_s = sequences["eta"][:, 0] * bound.pump_flow_m3_s
    steps_per_ms = round(1.0e-3 / step_s)
    keep = math.exp(-step_s / VALVE_TAU_S)
    samples = np.empty((count, SATURATION_PERIODS * 100, 4))
    strokes = np.empty((count, SATURATION_PERIODS, 4))
    for period in range(SATURATION_PERIODS):
        strokes[:, period] = stroke
        command = sequences["commands"][:, period]
        for substep in range(100):
            for _ in range(steps_per_ms):
                valve = command + (valve - command) * keep
                is_saturated = (valve @ np.asarray(HEAD_AREA_M2)) > supply_m3_s
                delivered = np.where(is_saturated[:, None], 0.0, valve)
                compliance = _plant_compliance(LEGS, sequences["beta"], sequences["head_dead"],
                                               sequences["rod_dead"], sequences["hose"], stroke)
                pressure = _plant_step(pressure, BACK_PRESSURE_PA, delivered, step_s, compliance,
                                       LEGS, np.zeros_like(pressure, dtype=bool))
                stroke = np.clip(stroke + delivered * step_s, 0.0, STROKE_MAX_M)
            samples[:, period * 100 + substep] = pressure
    return samples, strokes


@pytest.mark.parametrize("plant_step_s", PLANT_STEPS_S)
def test_t_p3_3_saturation_with_falling_valves_stays_below_the_bound(plant_step_s) -> None:
    """Spec 3 (ii) v2 review: priority saturation on falling valves, seed 20261107 (own
    stream), 300 four-leg sequences, plant ``eta_v`` 0.85 / 0.95, sensitivity-end oil. The
    bound judges saturation on the larger of the sub-step start and end demand; ``p >= p_plant``
    at every 1 ms sub-step of every leg, and saturation occurs."""
    sequences = _saturation_sequences(np.random.default_rng([PROPERTY_SEED, 1]))
    plant, strokes = _saturated_plant_at_substeps(sequences, plant_step_s)
    violations, worst_Pa, saturated = 0, -math.inf, 0
    floor = np.array(RETRACT_ANCHOR_PA)
    for row in range(SATURATION_SEQUENCES):
        tracker = _tracker()
        tracker.valve_m_s = sequences["start_valve"][row].copy()
        for period in range(SATURATION_PERIODS):
            values = _substep_bounds(tracker, sequences["commands"][row, period],
                                     strokes[row, period], floor)
            gap = plant[row, period * 100:(period + 1) * 100] - values
            violations += int(np.sum(gap > ROUNDING_PA))
            worst_Pa = max(worst_Pa, float(gap.max()))
        saturated += tracker.saturated_substeps
    assert saturated > 0
    assert violations == 0, f"{violations} sub-steps above the bound, worst {worst_Pa / BAR} bar"
