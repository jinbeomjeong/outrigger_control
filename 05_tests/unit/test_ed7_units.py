"""436.9 edition 7 units (``jp3_remedy_spec_v7.md`` 3, 6, 8 Y7-1 .. Y7-7), no harness run.

* Y7-1 A(i)-b (``lock_start_b``): trigger after ``N_blind`` dead-band periods with the still
  reference at read ``k_s + 2``, the three condition-3 variants, the implementation notes
  (가) .. (다), the ends, the reversal latch, the predictive protection, the record; P7-6 (no
  trigger = the commands of A(i)-b off) and the edition 6 meta / commands unchanged.
* Y7-2 D6 witness (``ground_contact.retract_witness_m``, ``two_pressure`` D6) and the probe
  retract position target (``ProbeRound`` on a toy leg).
* Y7-3 P1 supplement (``check_open_delay.CheckOpenGateP1Patch``): the hand path of the
  hydraulics review X (six cases, split volumes) and the H4 corner values, the trapped rise in
  neutral, the refill, no seed (d).
* Y7-4 ③ rev 7 (revision 7 = the bound of revision 6, tag ``final_C4G2_P3X``, Q7-C3 tokens),
  condition rows (``jp3_rev7_condition``).
* Y7-5 rules (``jp3_ed7_rules``): J7 by (name, leg, reason), deadlock signature, sensitivity
  split, (setting, row) cluster rule, U832.
* Y7-6 / Y7-7: the probe plan counts and the 12b edition 7 scan.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
for _path in (COUPLED_DIR, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from outrigger_sim.control import extend_start_bound as esb  # noqa: E402
from outrigger_sim.control.ground_contact import (  # noqa: E402
    ProbeD6Settings,
    ProbeReading,
    ProbeRound,
    ProbeSettings,
    retract_witness_m,
)
from outrigger_sim.control.lock_start_b import (  # noqa: E402
    BLIND_LATCH_EVENT,
    BLIND_PROTECT_EVENT,
    CAP_EVENT,
    CompletionFlags,
    CylinderGeometry,
    FloorInputs,
    LockStartB,
    LockStartBSettings,
)
from outrigger_sim.control.two_pressure import (  # noqa: E402
    D6Witness,
    RodSensorState,
    TwoPressureMonitor,
)
from outrigger_sim.hydraulics import v5_options  # noqa: E402
from outrigger_sim.hydraulics.check_open_delay import (  # noqa: E402
    CheckDelayCircuit,
    CheckDelayInputs,
    CheckOpenGateP1Patch,
    RetractConfig,
    fill_line_pressure_Pa,
    retract_dead,
)

V_MAX = 20.924e-3
T = 0.1
U_HOLD = 0.01 * V_MAX
STEP = 0.2e-3
TWIST = np.array([0.4761, -0.4761, -0.5228, 0.5228])
F_MIN = 9.415e3
GEOMETRY = CylinderGeometry(head_area_m2=np.full(4, 0.0133), annulus_area_m2=np.full(4, 0.0038),
                            stroke_max_m=0.70, max_speed_m_s=V_MAX, period_s=T,
                            increment_limit_m_s=0.25 * V_MAX)
SAFE_LOADS = np.full(4, 80.0e3)


def _inputs(t_s: float, acting: np.ndarray, requested: np.ndarray, stroke: np.ndarray, *,
            is_level: bool = True, completion: CompletionFlags | None = None,
            twist_N: float = 0.0, loads: np.ndarray = SAFE_LOADS,
            protected: np.ndarray | None = None) -> FloorInputs:
    return FloorInputs(t_s=t_s, is_level=is_level, is_fill_phase=True, is_fault=False,
                       requested_m_s=requested, acting_m_s=acting,
                       previous_output_m_s=acting, stroke_m=stroke,
                       head_Pa=np.full(4, 80e5), rod_Pa=np.full(4, 5e5),
                       protected=np.zeros(4, bool) if protected is None else protected,
                       fallback_legs=frozenset(), completion=completion, twist_load_N=twist_N,
                       twist_limit_N=15.0e3, lower_load_N=loads, force_N=loads + 5e3,
                       F_min_N=F_MIN, twist_vector=TWIST)


def _blind(**parameters) -> LockStartB:
    settings = LockStartBSettings(components=("A_ib",), **parameters)
    return LockStartB(settings, GEOMETRY)


def _dead_band_run(rule: LockStartB, periods: int, *, speed: float = 0.1e-3, leg: int = 0,
                   strokes=None, **keywords) -> list[np.ndarray]:
    """``periods`` LEVEL periods with leg ``leg`` commanded ``speed`` (inside the dead band)
    and acting the same; the outputs."""
    outputs = []
    for k in range(periods):
        command = np.zeros(4)
        command[leg] = speed
        stroke = np.full(4, 0.4) if strokes is None else np.full(4, 0.4) + strokes(k)
        outputs.append(rule.apply_floors(_inputs(k * T, command, command, stroke, **keywords)))
    return outputs


# ------------------------------------------------------------------------------ Y7-1 A(i)-b
def test_blind_fields_need_the_component_and_stay_out_of_an_edition_6_meta() -> None:
    with pytest.raises(ValueError, match="need the A_ib component"):
        LockStartBSettings(components=("A_i",), ib_blind_periods=30)
    edition_6 = LockStartBSettings(components=("A_i", "A_ii", "B3"))
    assert not any(name.startswith("ib_") for name in edition_6.to_meta())
    edition_7 = LockStartBSettings(components=("A_i", "A_ib", "A_ii", "B3"))
    assert edition_7.components == ("A_i", "A_ib", "A_ii", "B3")
    meta = edition_7.to_meta()
    assert meta["ib_blind_periods"] == 25 and meta["ib_still_m"] == 0.1e-3
    assert meta["ib_condition"] == "with_twist" and meta["ib_protect_stiffness_N_m"] == 41.0e6
    with pytest.raises(ValueError):
        LockStartBSettings(components=("A_ib",), ib_condition="nope")


def test_blind_triggers_after_25_periods_at_u_hold_plus_one_step() -> None:
    rule = _blind()
    outputs = _dead_band_run(rule, 27)
    assert all(abs(out[0] - 0.1e-3) < 1e-15 for out in outputs[:24])
    assert outputs[24][0] == pytest.approx(U_HOLD + STEP)  # note (다): trigger period
    assert outputs[25][0] == pytest.approx(U_HOLD + 2 * STEP)
    assert rule.blind_counts[0].triggers == 1 and rule.blind_counts[0].trigger_periods == [25]
    assert all(out[1:].tolist() == [0.0, 0.0, 0.0] for out in outputs)


def test_trigger_records_whether_the_completion_was_evaluated() -> None:
    """Control review 3: ``completion_known`` per shot, unknown triggers counted per leg."""
    unknown = _blind()
    _dead_band_run(unknown, 26)  # no completion flags: condition 3 open
    known = _blind()
    _dead_band_run(known, 26, completion=CompletionFlags(False, True, False))
    unknown_record, known_record = unknown.record()["blind"], known.record()["blind"]
    assert [shot["completion_known"] for shot in unknown_record["shots"]] == [False]
    assert unknown_record["legs"]["FL"]["triggers_completion_unknown"] == 1
    assert [shot["completion_known"] for shot in known_record["shots"]] == [True]
    assert known_record["legs"]["FL"]["triggers_completion_unknown"] == 0


def test_note_ga_raises_a_dead_band_request_that_edition_6_a_i_leaves() -> None:
    edition_6 = LockStartB(LockStartBSettings(components=("A_i",)), GEOMETRY)
    outputs = _dead_band_run(edition_6, 40)
    assert all(abs(out[0] - 0.1e-3) < 1e-15 for out in outputs)  # A(i) never acts there


def test_still_reference_skips_the_first_two_reads() -> None:
    """Reads 0 .. 1 carry the tail of the command before: a reference at read 0 would see a
    0.1 mm drop and not call the leg still; the reference at read 2 does."""
    def strokes(k: int) -> np.ndarray:
        shift = np.zeros(4)
        shift[0] = 0.0 if k == 0 else 0.3e-3
        return shift

    rule = _blind()
    _dead_band_run(rule, 26, strokes=strokes)
    assert rule.blind_counts[0].triggers == 1
    moving = _blind()
    _dead_band_run(moving, 30, strokes=lambda k: np.array([k * 0.15e-3 * T, 0, 0, 0]))
    assert moving.blind_counts[0].triggers == 0  # 0.15 mm/s moves 0.3 mm over the stretch


@pytest.mark.parametrize(("condition", "flags", "twist_N", "fires"), [
    ("with_twist", CompletionFlags(True, True, False), 20.0e3, True),
    ("with_twist", CompletionFlags(True, True, False), 10.0e3, False),
    ("with_twist", CompletionFlags(False, True, False), 0.0, True),
    ("attitude_clearance", CompletionFlags(True, True, False), 20.0e3, False),
    ("attitude_clearance", CompletionFlags(True, False, False), 0.0, True),
    ("level_incomplete", CompletionFlags(True, True, False), 0.0, True),
    ("level_incomplete", CompletionFlags(True, True, True), 0.0, False),
])
def test_condition_3_variants(condition, flags, twist_N, fires) -> None:
    rule = _blind(ib_condition=condition)
    _dead_band_run(rule, 30, completion=flags, twist_N=twist_N)
    assert (rule.blind_counts[0].triggers > 0) == fires


def test_blind_floor_ends_on_motion_zero_sign_and_cap() -> None:
    moved = _blind()
    _dead_band_run(moved, 25)
    for k in range(25, 30):  # the floor moves the leg 0.2 mm per period
        stroke = np.full(4, 0.4)
        stroke[0] += (k - 24) * 0.2e-3
        command = np.array([0.1e-3, 0, 0, 0])
        moved.apply_floors(_inputs(k * T, command, command, stroke))
    assert moved.blind_counts[0].end == {"moved": 1}
    zero = _blind()
    _dead_band_run(zero, 26)
    zero.apply_floors(_inputs(2.6, np.zeros(4), np.zeros(4), np.full(4, 0.4)))
    assert zero.blind_counts[0].end == {"zero": 1}
    sign = _blind()
    _dead_band_run(sign, 26)
    reverse = np.array([-0.1e-3, 0, 0, 0])
    sign.apply_floors(_inputs(2.6, reverse, reverse, np.full(4, 0.4)))
    assert sign.blind_counts[0].end == {"sign": 1}
    capped = _blind()
    events = []
    for k in range(25 + 4 + 51):  # 4 periods up to the cap, then N_cap
        command = np.array([0.1e-3, 0, 0, 0])
        capped.apply_floors(_inputs(k * T, command, command, np.full(4, 0.4)))
        events += [name for _, name in capped.events]
    assert capped.blind_counts[0].end == {"cap": 1}
    assert events == [f"{CAP_EVENT}:FL"]
    phase = _blind()
    _dead_band_run(phase, 26)
    phase.apply_floors(_inputs(2.6, np.zeros(4), np.zeros(4), np.full(4, 0.4), is_level=False))
    assert phase.blind_counts[0].end == {"phase": 1}


def test_reversal_latch_after_more_than_two_opposite_triggers() -> None:
    rule = _blind()
    events = []
    t = 0.0
    for cycle in range(5):
        speed = 0.1e-3 if cycle % 2 == 0 else -0.1e-3
        for _ in range(27):
            command = np.array([speed, 0, 0, 0])
            rule.apply_floors(_inputs(t, command, command, np.full(4, 0.4)))
            events += rule.events
            t += T
        zero = np.zeros(4)
        rule.apply_floors(_inputs(t, zero, zero, np.full(4, 0.4)))  # ends the floor (zero)
        t += T
    counts = rule.blind_counts[0]
    assert counts.triggers == 3 and counts.reversals == 3 and counts.latches == 1
    assert [name for _, name in events].count(f"{BLIND_LATCH_EVENT}:FL") == 1
    rule.apply_floors(_inputs(t, np.zeros(4), np.zeros(4), np.full(4, 0.4), is_level=False))
    assert not rule._blind[0].is_latched  # a new LEVEL stretch clears the latch


def test_predictive_protection_holds_the_shot_and_notes_once() -> None:
    low = np.array([12.0e3, 80.0e3, 80.0e3, 80.0e3])  # FL near F_min: a retract shot of RR
    rule = _blind()
    events = []
    for k in range(30):
        command = np.array([0.0, 0.0, 0.0, -0.1e-3])
        rule.apply_floors(_inputs(k * T, command, command, np.full(4, 0.4), loads=low))
        events += rule.events
    counts = rule.blind_counts[3]
    assert counts.triggers == 0 and counts.protect_blocked_periods == 6
    assert [name for _, name in events] == [f"{BLIND_PROTECT_EVENT}:RR"]
    # 41 MN/m x 0.4761 x 0.5228 x 0.85 mm = 8.7 kN off FL: 12 - 8.7 < F_min + 5 kN


def test_shot_record_takes_delta_D_one_second_after_the_end() -> None:
    rule = _blind()
    _dead_band_run(rule, 26, twist_N=1.0e3)
    zero = np.zeros(4)
    for k in range(26, 40):
        rule.apply_floors(_inputs(k * T, zero, zero, np.full(4, 0.4), twist_N=4.0e3))
    record = rule.record()["blind"]
    shot = record["shots"][0]
    assert shot["end"] == "zero" and shot["delta_D_N"] == pytest.approx(3.0e3)
    assert shot["twist_grew"] is True and record["shots_twist_grew"] == 1


def test_p7_6_without_a_trigger_the_commands_are_those_of_a_ib_off() -> None:
    """A stall above u_hold (edition 6 A(i) triggers) and dead-band periods too short for a
    trigger: A(i) + A(i)-b give exactly the A(i) commands."""
    def run(components: tuple[str, ...]) -> list[np.ndarray]:
        rule = LockStartB(LockStartBSettings(components=components), GEOMETRY)
        outputs = []
        for k in range(60):
            speed = 1.0e-3 if k < 30 else 0.1e-3 if k < 50 else 0.0
            command = np.array([speed, 0, 0, -0.05e-3 if k % 20 < 15 else 0.0])
            outputs.append(rule.apply_floors(_inputs(k * T, command, command,
                                                     np.full(4, 0.4))))
        return outputs

    with_a_ib, without = run(("A_i", "A_ib")), run(("A_i",))
    assert all(np.array_equal(a, b) for a, b in zip(with_a_ib, without, strict=True))


# ------------------------------------------------------------------------------ Y7-2 D6
def test_retract_witness_is_the_largest_e3_drop() -> None:
    assert math.isnan(retract_witness_m([0.4, 0.4]))
    reads = [0.4, 0.4, 0.4, 0.3999, 0.3996, 0.3993, 0.3993]
    assert retract_witness_m(reads) == pytest.approx(0.4 - (0.3996 + 0.3993 + 0.3993) / 3)
    assert retract_witness_m([0.4, 0.4, 0.4, 0.4002]) == pytest.approx(0.0)


def _monitor() -> TwoPressureMonitor:
    return TwoPressureMonitor(np.full(4, 0.0133), np.full(4, 0.0038), V_MAX, F_MIN, T)


class _Result:
    def __init__(self, leg: int, witness: float | None, *, is_reversed: bool = False,
                 k1_mid_opened: bool | None = None) -> None:
        self.leg_index, self.is_skipped, self.is_reversed = leg, False, is_reversed
        self.t_first_hold_end_s, self.t_second_hold_end_s = 1.0, 2.0
        self.retract_witness_m = witness
        self.retract_extra_m = self.retract_extra_periods = self.retract_target_reached = None
        self.k1_mid_opened = k1_mid_opened


def _d6_history(monitor: TwoPressureMonitor, rise_Pa: float) -> None:
    rod_extend, rod_retract = np.full(4, 5e5), np.full(4, 5e5 + rise_Pa)
    monitor._history.append((1.0, rod_extend, np.full(4, 80e5)))
    monitor._history.append((2.0, rod_retract, np.full(4, 80e5)))


def test_d6_witness_not_opened_rounds_neither_count_nor_reset() -> None:
    witness = D6Witness(witness_m=0.3e-3, warn_rounds=2)
    monitor = _monitor()
    _d6_history(monitor, 0.0)  # no rise: a judged round would miss
    monitor.probe_round_finished([_Result(0, 0.1e-3)], witness)
    monitor.probe_round_finished([_Result(0, None)], witness)
    names = [name for name, _ in monitor._events]
    assert names.count("INFO_D6_NOT_OPENED:FL") == 2
    assert "WARN_PROBE_RETRACT_NOT_OPENED:FL" in names
    assert monitor._legs[0].probe_misses == 0 and "WARN_ROD_PRESSURE_FALLBACK:FL" not in names
    monitor.probe_round_finished([_Result(0, 0.5e-3)], witness)
    monitor.probe_round_finished([_Result(0, 0.5e-3)], witness)
    assert "WARN_ROD_PRESSURE_FALLBACK:FL" in [name for name, _ in monitor._events]
    record = monitor.meta()["d6_witness"]
    assert record["not_judgeable_rounds"][0] == 2 and len(record["rounds"]) == 4


def test_d6_witness_rows_and_reversed_round_counts() -> None:
    """Control review 4 (record only): each witness row carries ``is_reversed`` and
    ``k1_mid_opened``; reversed rounds are counted per leg, substituted legs (fallback, out of
    D6) apart."""
    witness = D6Witness(witness_m=0.3e-3, warn_rounds=2)
    monitor = _monitor()
    _d6_history(monitor, 40e5)
    monitor.rod_state[1] = RodSensorState.FALLBACK
    monitor.probe_round_finished([_Result(0, 0.5e-3, is_reversed=True, k1_mid_opened=False),
                                  _Result(1, 0.5e-3, is_reversed=True),
                                  _Result(2, 0.5e-3)], witness)
    record = monitor.meta()["d6_witness"]
    assert [(row["leg"], row["is_reversed"], row["k1_mid_opened"]) for row in record["rounds"]
            ] == [("FL", True, False), ("RL", False, None)]
    assert record["reversed_rounds"] == {"not_substituted": [1, 0, 0, 0],
                                         "substituted": [0, 1, 0, 0]}


def test_d6_without_the_witness_is_the_edition_6_rule() -> None:
    monitor = _monitor()
    _d6_history(monitor, 0.0)
    monitor.probe_round_finished([_Result(0, None)])
    monitor.probe_round_finished([_Result(0, None)])
    assert "WARN_ROD_PRESSURE_FALLBACK:FL" in [name for name, _ in monitor._events]
    assert "d6_witness" not in monitor.meta()


def _toy_probe(d6: ProbeD6Settings | None, dead_m: float,
               start_m: float = 0.40) -> tuple[ProbeRound, list]:
    """Leg FL of a toy plant: the oil stroke follows the command one period late, a retract
    moves only after ``dead_m`` of commanded oil (a shut check); the other legs are skipped by
    the stroke guard. Returns the finished round and the FL commands."""
    stroke = np.array([start_m, 0.699, 0.699, 0.699])
    probe = ProbeRound(start=_probe_reading(0.0, stroke), settings=ProbeSettings(),
                       max_speed_m_s=V_MAX, period_s=T, load_sensitivity_diag_N_m=np.full(4, 5e6),
                       attitude_sensitivity_rad_m=np.zeros((4, 2)), stroke_max_m=0.70,
                       d6=d6, retract_need_ub_m=lambda leg, head, s: 3.0e-3)
    commands, previous, retract_oil = [], 0.0, 0.0
    t = 0.0
    while not probe.is_finished and t < 60.0:
        if previous < 0.0:
            retract_oil += -previous * T
            moving = max(retract_oil - dead_m, 0.0) - max(retract_oil + previous * T - dead_m, 0.0)
            stroke[0] -= moving
        else:
            stroke[0] += previous * T
        command = probe.step(_probe_reading(t, stroke))
        commands.append(float(command[0]))
        previous = float(command[0])
        t += T
    return probe, commands


def _probe_reading(t_s: float, stroke: np.ndarray) -> ProbeReading:
    return ProbeReading(t_s=t_s, cylinder_force_N=np.full(4, 60e3), rod_stroke_m=stroke.copy(),
                        motor_stroke_m=stroke.copy(), rate_attitude_rad=(0.0, 0.0),
                        filtered_attitude_rad=(0.0, 0.0), head_pressure_Pa=np.full(4, 80e5))


def test_probe_retract_target_returns_the_leg_and_the_witness_sees_it() -> None:
    plain, plain_commands = _toy_probe(None, dead_m=2.2e-3)
    assert plain.results[0].retract_witness_m is None and plain.results[0].retract_extra_m is None
    d6 = ProbeD6Settings(witness=True, retract_position_target=True)
    probe, commands = _toy_probe(d6, dead_m=2.2e-3)
    result = probe.results[0]
    assert result.retract_target_reached is True and result.retract_extra_m > 0.2e-3
    assert min(commands) >= -2.0e-3 * 1.0001 / 0.56  # the 2 mm move keeps its profile
    slow = [c for c in commands if -1.0e-3 - 1e-12 <= c < 0.0]
    assert slow and all(c >= -1.0e-3 - 1e-12 for c in slow)
    assert result.retract_witness_m >= 0.3e-3
    # cap: commanded retract <= need_ub (3 mm) + depth + 0.2 mm
    assert sum(-c * T for c in commands if c < 0.0) <= 3.0e-3 + 2.0e-3 + 0.2e-3 + 1e-9
    witness_only, _ = _toy_probe(ProbeD6Settings(witness=True), dead_m=2.2e-3)
    assert witness_only.results[0].retract_witness_m < 0.3e-3  # 2 mm never opened the line
    assert witness_only.results[0].retract_extra_m is None


def test_reversed_probe_records_whether_the_k1_mid_read_opened() -> None:
    """Q7-C2 (control review 4): a retract-first probe gets no (i-b) target; its result tells
    whether the retract reads up to the K1 mid read reached ``s_w,D6``."""
    margin = ProbeSettings().stroke_guard_margin_m
    near_top = 0.70 - margin - 1.0e-3  # a 2 mm extension would pass the guard: retract first
    d6 = ProbeD6Settings(witness=True, retract_position_target=True)
    shut, _ = _toy_probe(d6, dead_m=2.2e-3, start_m=near_top)
    moving, _ = _toy_probe(d6, dead_m=0.0, start_m=near_top)
    assert shut.results[0].is_reversed and moving.results[0].is_reversed
    assert shut.results[0].k1_mid_opened is False  # still in the dead stroke at the mid read
    assert moving.results[0].k1_mid_opened is True
    assert shut.results[0].retract_extra_m is None  # (i-b) is not applied when reversed
    extend_first, _ = _toy_probe(d6, dead_m=0.0)
    assert extend_first.results[0].k1_mid_opened is None


def test_probe_d6_settings_refuse_a_fast_slow_part() -> None:
    with pytest.raises(ValueError):
        ProbeD6Settings(retract_position_target=True, retract_slow_speed_m_s=2e-3)
    assert not ProbeD6Settings().is_enabled


# ------------------------------------------------------------------------------ Y7-3 P1
FRONT_A_H = math.pi / 4 * 0.130 ** 2
FRONT_A_ANN = math.pi / 4 * (0.130 ** 2 - 0.110 ** 2)
S_MAX, L0, V_LINE, BETA_H, P_T = 0.70, 0.05, 285e-6, 0.5e9, 2.0e5


def _hand_need_and_rise(beta: float, scale: float, band: float, p_h: float, p_r: float,
                        s: float, delivered_m: float | None = None) -> tuple[float, float]:
    """The hydraulics review hand path (``h7r4_calcs.py``, split volumes, ``k_ext`` 0)."""
    psi, p_cr, delta = 3.5, 3.0e5, 3.0e5
    k_h = beta * FRONT_A_H / (scale * L0 + s)
    drive = p_h + p_cr - P_T
    p_free = max(drive / psi, 0.0)
    if FRONT_A_ANN * (p_free - delta - p_r) > band:
        p_b = (drive - (FRONT_A_ANN * (delta + p_r) + band) / FRONT_A_H) / (
            psi - FRONT_A_ANN / FRONT_A_H)
    else:
        p_b = p_free

    def volume(p_line: float) -> float:
        dp_rod = max(p_line - delta - p_r, 0.0)
        return (scale * V_LINE * max(p_line - P_T, 0.0) / BETA_H
                + FRONT_A_ANN * (scale * L0 + S_MAX - s) * dp_rod / beta
                + FRONT_A_ANN * max(FRONT_A_ANN * dp_rod - band, 0.0) / k_h)

    need = volume(p_b) / FRONT_A_ANN
    if delivered_m is None or delivered_m >= need:
        return need, max(p_b - delta, p_r) - p_r
    low, high = P_T, p_b
    for _ in range(80):
        middle = 0.5 * (low + high)
        low, high = (middle, high) if volume(middle) < delivered_m * FRONT_A_ANN else (low, middle)
    return need, max(low - delta - p_r, 0.0)


def _patched_gate(beta: float, scale: float, c_v: float = 0.02) -> CheckOpenGateP1Patch:
    circuit = CheckDelayCircuit(head_area_m2=np.full(4, FRONT_A_H),
                                annulus_area_m2=np.full(4, FRONT_A_ANN), stroke_m=S_MAX,
                                rod_dead_length_m=L0, head_dead_length_m=L0,
                                bulk_modulus_Pa=1.0e9, tank_pressure_Pa=P_T, max_speed_m_s=V_MAX,
                                compensator_drop_Pa=10e5)
    patch = v5_options.P1PatchSetting(line_scale=scale, dead_scale=scale, bulk_modulus_Pa=beta)
    return CheckOpenGateP1Patch(v5_options.CheckDelaySetting("VN", 1.0, c_v), circuit, patch)


def _gate_inputs(gate, *, u: float, p_h: float = 99.39e5, p_r: float = 5.07e5,
                 band: float = 0.0, s: float = 0.40836, locked: bool = True,
                 dt: float = 0.1, t_s: float = 0.0, void: float = 0.0) -> CheckDelayInputs:
    speed = np.zeros(4)
    speed[0] = u
    voids = np.zeros(4)
    voids[0] = void
    return CheckDelayInputs(t_s, dt, speed, np.full(4, p_h), np.full(4, p_r),
                            np.array([locked, True, True, True]), voids,
                            np.full(4, band), np.full(4, s))


@pytest.mark.parametrize("scale", (0.5, 1.0, 1.5))
@pytest.mark.parametrize("band", (0.0, 4.0e3))
def test_hand_path_x_six_cases(scale: float, band: float) -> None:
    """Hydraulics review X with the split volumes: the gate's need and opening rise equal the
    hand path; the old uniform ``volume_scale`` keeps the review's code values."""
    gate = _patched_gate(1.0e9, scale)
    values = retract_dead(gate.retract_cfg, 99.39e5, 5.07e5, band, 0.40836, 0.0, FRONT_A_H,
                          FRONT_A_ANN, S_MAX, gate.L0r, gate.L0h, gate.beta, P_T)
    need, rise = _hand_need_and_rise(1.0e9, scale, band, 99.39e5, 5.07e5, 0.40836)
    assert values["need"] == pytest.approx(need, rel=1e-9)
    gate.x[0] = values["need"]
    rise_code = gate._fill_rise_of_x_Pa(_gate_inputs(gate, u=-2e-3, band=band), 0, 0.0)
    assert rise_code == pytest.approx(rise, rel=1e-9)
    old = retract_dead(RetractConfig(True, scale, V_LINE, BETA_H, 3.5, 3e5), 99.39e5, 5.07e5,
                       band, 0.40836, 0.0, FRONT_A_H, FRONT_A_ANN, S_MAX, L0, L0, 1.0e9, P_T)
    stored = {(0.5, 0.0): 0.7447, (0.5, 4e3): 0.6465, (1.0, 0.0): 1.4894,
              (1.0, 4e3): 1.2929, (1.5, 0.0): 2.2341, (1.5, 4e3): 1.9394}
    assert round(old["need"] * 1e3, 4) == stored[(scale, band)]


def test_h4_corners_nominal_opens_slow_traps() -> None:
    nominal = _patched_gate(1.0e9, 1.0)
    need, _ = _hand_need_and_rise(1.0e9, 1.0, 0.0, 99.39e5, 5.07e5, 0.40836)
    assert round(need * 1e3, 3) == 1.489
    slow = _patched_gate(0.69e9, 1.5)
    slow.x[0] = 2.098e-3
    rise = slow._fill_rise_of_x_Pa(_gate_inputs(slow, u=-2e-3), 0, 0.0)
    assert round(rise / 1e5, 2) == 20.48  # h7r4_calcs.txt H4 slow k_ext 0
    assert nominal is not slow


def _deliver(gate, oil_m: float, speed: float = 2.0e-3) -> None:
    steps = round(oil_m / (speed * 0.01))
    for _ in range(steps):
        gate.filter(_gate_inputs(gate, u=-speed, dt=0.01))


def test_trapped_rise_survives_neutral_and_a_refill_starts_on_it() -> None:
    slow = _patched_gate(0.69e9, 1.5)
    _deliver(slow, 2.098e-3)
    assert not slow.is_open[0]
    held = float(slow.fill_rise_Pa[0])
    assert held == pytest.approx(20.48e5, rel=2e-3)
    trapped = slow._trapped_fill_m(_gate_inputs(slow, u=0.0), 0, held, 0.0)
    for _ in range(500):  # 5 s neutral: only the line share drains
        output = slow.filter(_gate_inputs(slow, u=0.0, dt=0.01))
    assert slow.fill_rise_Pa[0] == held and slow.x[0] == pytest.approx(trapped)
    assert np.isnan(output.opening_rod_pressure_Pa).all()  # (d): no seed
    _deliver(slow, 0.5e-3)
    assert slow.is_open[0] or slow.fill_rise_Pa[0] >= held
    slow.clear_fill(0)
    assert slow.fill_rise_Pa[0] == 0.0


def _extend_until_head_opens(gate, speed: float = 5.0e-3, dt: float = 1.0e-3,
                             t0_s: float = 10.0) -> dict:
    """Extend the held leg in ``dt`` chunks (hydraulics probe C); the times and the held rise
    when the rod check and the head check opened."""
    seen: dict = {}
    for k in range(5000):
        t_s = round(t0_s + k * dt, 6)
        gate.filter(_gate_inputs(gate, u=speed, dt=dt, t_s=t_s))
        if gate.rod_released[0] and "rod_open_t_s" not in seen:
            seen.update(rod_open_t_s=t_s, rise_at_rod_open_Pa=float(gate.fill_rise_Pa[0]),
                        head_open_at_rod_open=bool(gate.is_open[0]))
        if gate.is_open[0]:
            seen.update(head_open_t_s=t_s, rise_at_head_open_Pa=float(gate.fill_rise_Pa[0]))
            return seen
    raise AssertionError("the head check never opened")


def _release_start(gate, *, setting: str = "VBM", locked_Pa: float = 10.0e5) -> list:
    """What the harness plant hands the M2 lag and the M2 shift at a release of leg FL (the
    plant's own ``_start_release`` on a bare instance; lag and shift record their inputs)."""
    import harness_hydraulics
    import run_v5

    options = run_v5.options_of(setting)[1]
    plant_class = harness_hydraulics.make_hydraulics_plant_class(
        object, options, (np.zeros(4), np.zeros(4)))
    plant = object.__new__(plant_class)
    started: list = []
    plant.__dict__.update(
        line_fill_gate=gate, rod_pressure_seed_Pa=np.full(4, np.nan), fill_release_log=[],
        stale_seed_log=None, lock_log=None, t=20.0, A_ann=np.full(4, FRONT_A_ANN),
        rod_pressure_lag=SimpleNamespace(start=lambda leg, p: started.append(("lag", p))),
        rod_release=SimpleNamespace(release=lambda leg, s: started.append(("m2", s))))
    plant._start_release(0, locked_Pa, 500.0)
    return started


def test_rod_check_opening_clears_the_held_rise_probe_c() -> None:
    """Hydraulics review 1-4 (user decision: 0 when the rod check opens): a held retract fill
    of the slow corner, then an extension; the rise is 0 from the rod check's pilot opening
    on, logged once, so the extend release starts at the locked truth and M2 gets the inputs
    of a leg that never held a fill."""
    held_gate = _patched_gate(0.69e9, 1.5)
    _deliver(held_gate, 2.098e-3)
    held_Pa = float(held_gate.fill_rise_Pa[0])
    assert held_Pa == pytest.approx(20.48e5, rel=2e-3) and not held_gate.is_open[0]
    held = _extend_until_head_opens(held_gate)
    assert held["rise_at_rod_open_Pa"] == 0.0 and not held["head_open_at_rod_open"]
    assert held["head_open_t_s"] > held["rod_open_t_s"]
    assert held_gate.rod_check_clear_log == [(held["rod_open_t_s"], 0, held_Pa)]
    assert held_gate.rod_check_clear_count == 1
    summary = held_gate.summary()
    assert summary["rod_check_clear_log_columns"] == ["t_s", "leg", "cleared_fill_rise_Pa"]
    assert summary["rod_check_clear_log_truncated"] is False
    fresh_gate = _patched_gate(0.69e9, 1.5)
    fresh = _extend_until_head_opens(fresh_gate)
    assert fresh["head_open_t_s"] - fresh["rod_open_t_s"] == pytest.approx(
        held["head_open_t_s"] - held["rod_open_t_s"])
    assert fresh_gate.rod_check_clear_log == []  # nothing to clear: no row
    assert _release_start(held_gate) == _release_start(fresh_gate)
    assert _release_start(held_gate)[0] == ("lag", 10.0e5)  # base, no fill rise


def test_retract_release_still_starts_on_the_held_rise() -> None:
    """The retract opening path is unchanged: base + Delta p_fill (the old M2 seed)."""
    gate = _patched_gate(0.69e9, 1.5)
    _deliver(gate, 2.098e-3)
    held_Pa = float(gate.fill_rise_Pa[0])
    started = _release_start(gate)
    assert started[0] == ("lag", pytest.approx(10.0e5 + held_Pa))
    assert gate.fill_rise_Pa[0] == 0.0 and gate.void_fill_m[0] == 0.0


def test_partial_void_fill_stays_trapped_in_neutral_probe_b() -> None:
    """Hydraulics review 1-1 (probe B): 0.5 mm into a 1 mm void raises nothing, yet neutral
    keeps it (up to the present void); a release or a new lock clears it."""
    gate = _patched_gate(1.0e9, 1.0)
    for _ in range(25):  # 2 mm/s x 0.25 s = 0.5 mm
        gate.filter(_gate_inputs(gate, u=-2.0e-3, dt=0.01, void=1.0e-3))
    assert gate.fill_rise_Pa[0] == 0.0
    assert gate.void_fill_m[0] == pytest.approx(0.5e-3)
    for _ in range(300):  # 3 s neutral
        gate.filter(_gate_inputs(gate, u=0.0, dt=0.01, void=1.0e-3))
    assert gate.x[0] == pytest.approx(0.5e-3)
    for _ in range(300):  # the void shrank: the floor follows it
        gate.filter(_gate_inputs(gate, u=0.0, dt=0.01, void=0.3e-3))
    assert gate.x[0] == pytest.approx(0.3e-3)
    gate.clear_fill(0)
    assert gate.void_fill_m[0] == 0.0


def test_fill_line_pressure_is_the_inverse_of_the_volume_law() -> None:
    c_l, c_r, c_h = 1e-12, 2e-12, 4e-12
    for volume in (0.0, 1e-7, 5e-6, 3e-5):
        pressure = fill_line_pressure_Pa(volume, 2e5, 8e5, 12e5, c_l, c_r, c_h)
        back = (c_l * max(pressure - 2e5, 0) + c_r * max(pressure - 8e5, 0)
                + c_h * max(pressure - 12e5, 0))
        assert back == pytest.approx(volume, abs=1e-18)
    assert fill_line_pressure_Pa(0.0, 2e5, 1e5, 1e5, c_l, c_r, c_h) == 1e5


def test_p1_patch_options_refusals_and_names() -> None:
    plant = {"rod_release_force": True, "rod_reading_truth": True,
             "line_fill_gate": {"kind": "VN", "volume_scale": 1.0, "c_v": 0.02}}
    options = v5_options.HydraulicOptions.from_dict({**plant, "p1_patch": {}})
    assert options.to_dict()["p1_patch"]["k_ext_form"] == "b0"
    with pytest.raises(ValueError, match="needs P4"):  # hydraulics review 2 guard
        v5_options.HydraulicOptions.from_dict({**plant, "rod_reading_truth": False,
                                               "p1_patch": {}})
    with pytest.raises(ValueError, match="volume_scale must be 1"):
        v5_options.HydraulicOptions.from_dict({**plant, "line_fill_gate": {
            "kind": "VN", "volume_scale": 1.5, "c_v": 0.02}, "p1_patch": {}})
    with pytest.raises(ValueError, match="needs the P1"):
        v5_options.HydraulicOptions.from_dict({"rod_release_force": True, "p1_patch": {}})
    with pytest.raises(ValueError):
        v5_options.P1PatchSetting(k_ext_form="b1")
    assert "p1_patch" not in v5_options.HydraulicOptions.from_dict(plant).to_dict()


# ------------------------------------------------------------------------------ Y7-4 ③ rev 7
def test_revision_7_is_the_bound_of_revision_6_with_its_own_identity() -> None:
    bound6, bound7 = esb.ExtendStartBound(revision=6), esb.ExtendStartBound(revision=7)
    assert bound7.is_witness_revision and bound7.is_hold_revision
    assert {k: v for k, v in bound7.to_meta().items() if k != "revision"} == {
        k: v for k, v in bound6.to_meta().items() if k != "revision"}
    assert bound7.identity()["rule_revision"] == 7
    assert bound7.identity()["spec_edition"] == esb.JP3_SPEC_EDITION_V7
    assert esb.HOLD_REVISIONS == (5, 6, 7)


def test_q7_c3_tags_and_names() -> None:
    import run_v5

    for suffix in ("", "_LAS", "_K1", "_LAS_K1", "_LAS_K1_LSB"):
        tag = v5_options.EXTEND_REV7_CONTROLLER_TAG + suffix
        assert v5_options.extend_start_revision_of_tag(tag) == 7, tag
        assert v5_options.is_extend_start_tag(tag)
    # the older bases keep their revisions (no prefix test)
    assert v5_options.extend_start_revision_of_tag("final_C4G2_P3W_LAS_K1_LSB") == 6
    assert v5_options.extend_start_revision_of_tag("final_C4G2_P3_LAS_K1") == 4
    vbm = run_v5.options_of("VBM")[1]
    assert vbm.extend_start_revision == 7 and vbm.lsb_components == ("A_i", "A_ib", "A_ii", "B3")
    assert run_v5.options_of("VBM0")[1].extend_start_revision is None
    for name in run_v5.ED7_SETTINGS:  # no older setting name is shadowed
        assert name not in {**run_v5.SETTINGS, **run_v5.JP3_SETTINGS, **run_v5.ED6_SETTINGS}
    assert "VBMslow" in run_v5.ED7_SENSITIVITY_SETTINGS
    assert len(run_v5.ED7_SENSITIVITY_RECORD_SETTINGS) == 6


def test_edition_6_settings_keep_their_option_dicts() -> None:
    import run_v5

    for name in (*run_v5.ED6_SETTINGS, *run_v5.JP3_SETTINGS, *run_v5.SETTINGS):
        options = run_v5.options_of(name)[1]
        if options is None:
            continue
        keys = set(options.to_dict())
        assert not keys & {"p1_patch", "probe_d6_settings", "extend_start_rev7"}, name


def _condition_arrays() -> dict:
    """10 reads: an event at 1.0 s, PROBE reads 3 .. 7; leg FR goes locked_ext -> moving_ext at
    read 5 and reads carry_ext at 5 and 6 (read 6 breaches by 2 bar)."""
    t_s = np.round(np.arange(10) * 0.5, 3)
    phase = np.array(["level"] * 3 + ["probe"] * 5 + ["ready"] * 2)
    codes = esb.PLANT_STATE_CODES
    states = np.full((10, 4), codes["locked_ext"], np.int8)
    states[5:, 1] = codes["moving_ext"]
    classes = np.full((10, 4), esb.PERIOD_CLASS_CODES[esb.PeriodClass.LOCK], np.int8)
    classes[5:7, 1] = esb.PERIOD_CLASS_CODES[esb.PeriodClass.CARRY_EXT]
    used = np.full((10, 4), 20e5)
    truth = np.full((10, 4), 10e5)
    truth[6, 1] = 22e5
    return {"t_s": t_s, "phase": phase, "jp3_t_s": t_s, "jp3_class": classes,
            "jp3_plant_state": states, "jp3_p_tr_Pa": truth, "jp3_used_bound_Pa": used}


def test_rev7_condition_reads_and_classes() -> None:
    import jp3_rev7_condition as condition

    reads = condition.condition_reads(_condition_arrays(), 1.0)
    assert [(read.leg, read.is_breach) for read in reads] == [(1, False), (1, True)]
    judged = {"job": {"setting": "VBM"}, "t_event_s": 1.0, "t4h_file": "x.npz",
              "hydraulic_options": {"p1_patch": {"line_scale": 1.0}}}
    entry = condition.line_condition(judged, _condition_arrays())
    assert entry["state"] == "fail" and entry["condition_breach_reads"] == 1
    old = {"job": {"setting": "VBL"}, "t_event_s": 1.0, "t4h_file": "x.npz",
           "hydraulic_options": {}, "hydraulics_record": {"stale_seed_release": {
               "log": [[2.45, 1, True, 30e5, 10e5]],
               "log_columns": ["t_release_s", "leg", "seed_from_moving_open", "seed_Pa",
                               "p_r_locked_Pa"]}}}
    old_entry = condition.line_condition(old, _condition_arrays())
    assert old_entry["state"] == "record"
    assert old_entry["breach_seed_classes"][condition.ARTIFACT] == 1
    without_key = condition.line_condition({**old, "hydraulics_record": {}}, _condition_arrays())
    assert without_key["state"] == "not_judgeable"
    summary = condition.summarize([old_entry])
    assert summary["status"] == "not_judgeable" and summary["record_artifact_reads"] == 1
    no_condition = condition.line_condition({**judged, "t_event_s": 9.0}, _condition_arrays())
    assert condition.summarize([no_condition])["status"] == "not_judgeable"
    missing = condition.line_condition(judged, None)
    assert condition.summarize([missing])["status"] == "setting_defect"


_VBM_LINE = {"job": {"setting": "VBM"}, "hydraulic_options": {"p1_patch": {"line_scale": 1.0}}}
_VBL_LINE = {"job": {"setting": "VBL"}, "hydraulic_options": {}}


def test_rev7_condition_head_only_lines_are_not_applicable() -> None:
    """A declared head-only (steady) line has no ③ trace and no event: ``head_only`` on any
    plant, outside the judged count; undeclared it stays a setting defect; declared but with a
    trace or an event it contradicts itself (judged plant: defect, old plant: not judgeable)."""
    import jp3_rev7_condition as condition

    steady = {**_VBM_LINE, "t_event_s": None, "t4h_file": "S5.npz"}
    names = frozenset({"t_s", "phase", "meta_json"})
    declared = condition.line_condition(steady, None, {"head_only_declared": True}, names)
    assert declared["state"] == "head_only" and declared["head_only_declared"] is True
    by_line_field = condition.line_condition({**steady, "head_only_declared": True}, None)
    assert by_line_field["state"] == "head_only"
    meta_wins = condition.line_condition({**steady, "head_only_declared": True}, None,
                                         {"head_only_declared": False}, names)
    assert meta_wins["state"] == "setting_defect"  # 4a-7 1.1: the T4h meta first
    undeclared = condition.line_condition(steady, None, {}, names)
    assert undeclared["state"] == "setting_defect"
    with_trace = condition.line_condition(steady, None, {"head_only_declared": True},
                                          names | {"jp3_t_s"})
    assert with_trace["state"] == "setting_defect"
    assert with_trace["head_only_contradictions"] == ["jp3_t_s"]
    with_event = condition.line_condition({**_VBL_LINE, "t_event_s": 1.0}, None,
                                          {"head_only_declared": True}, names)
    assert with_event["state"] == "not_judgeable"
    assert with_event["head_only_contradictions"] == ["t_event_s"]
    event_line = condition.line_condition({**_VBM_LINE, "t_event_s": 1.0, "t4h_file": "x.npz"},
                                          _no_breach_arrays(), {"head_only_declared": False})
    summary = condition.summarize([declared, event_line])
    assert summary["status"] == "pass" and summary["judged_lines"] == 1
    assert summary["head_only_lines"] == {"judged_plant": 1, "record_plant": 0}
    assert summary["states"] == {"head_only": 1, "judged": 1}
    assert condition.summarize([declared])["status"] == "not_judgeable"  # never a pass


def _no_breach_arrays() -> dict:
    arrays = _condition_arrays()
    arrays["jp3_p_tr_Pa"] = np.full((10, 4), 10e5)
    return arrays


def _save_t4h(path: Path, arrays: dict, meta: dict) -> None:
    np.savez(path, meta_json=np.array(json.dumps(meta)), **arrays)


def test_rev7_condition_main_on_producer_rows_from_another_folder(tmp_path, monkeypatch) -> None:
    """Producer form (``t4h_file`` = a bare name, T4h folder ``<rows stem>_t4h``) and the CWD
    elsewhere: an event line judged, a steady head-only line ``head_only``, exit 0."""
    import jp3_rev7_condition as condition

    run = tmp_path / "run"
    t4h = run / "rows_t4h"
    t4h.mkdir(parents=True)
    _save_t4h(t4h / "R12.npz", _no_breach_arrays(), {"head_only_declared": False})
    steady_arrays = {"t_s": np.arange(3) * 0.1, "phase": np.array(["level"] * 3)}
    _save_t4h(t4h / "S5.npz", steady_arrays, {"head_only_declared": True})
    rows = [{**_VBM_LINE, "t_event_s": 1.0, "t4h_file": "R12.npz", "head_only_declared": False},
            {**_VBM_LINE, "t_event_s": None, "t4h_file": "S5.npz", "head_only_declared": True},
            {"error": "a failed job", "job": {"setting": "VBM"}}]
    (run / "rows.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows),
                                    encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    code = condition.main(["--rows", str(run / "rows.jsonl"), "--out", str(tmp_path / "c.json")])
    report = json.loads((tmp_path / "c.json").read_text(encoding="utf-8"))
    assert code == condition.EXIT_PASS and report["summary"]["status"] == "pass"
    assert report["summary"]["states"] == {"head_only": 1, "judged": 1}
    assert [entry["state"] for entry in report["lines"]] == ["judged", "head_only"]


def test_stale_seed_record_shows_a_truncated_log(monkeypatch) -> None:
    """Hydraulics review 3: the counts cover every seeded release, ``log_truncated`` says when
    the capped log lost rows, and the condition tool does not call such a release no_seed."""
    import harness_hydraulics
    import jp3_rev7_condition as condition
    import run_v5

    monkeypatch.setattr(harness_hydraulics, "MAX_LOGGED_LOCK_EVENTS", 3)
    plant_class = harness_hydraulics.make_hydraulics_plant_class(
        object, run_v5.options_of("VBL")[1], (np.zeros(4), np.zeros(4)))
    plant = object.__new__(plant_class)
    plant.__dict__.update(stale_seed_log=[], stale_seed_counts=[0, 0],
                          seed_from_moving=np.ones(4, bool), t=0.0)
    for k in range(5):
        plant.t = 1.0 + k
        plant._log_stale_seed(1, 10e5, 30e5)
    record = plant.stale_seed_release_record()
    assert (record["releases_with_seed"], record["stale_releases"]) == (5, 1)
    assert record["log_rows"] == 3 and record["log_truncated"] is True
    assert condition.release_seed_class(record, 1, 1.0, 0.9) == condition.ARTIFACT
    assert condition.release_seed_class(record, 1, 3.0, 2.9) == condition.SEED_NOT_STALE
    assert condition.release_seed_class(record, 1, 5.0, 4.9) == condition.LOG_TRUNCATED
    complete = {**record, "log_truncated": False}
    assert condition.release_seed_class(complete, 1, 5.0, 4.9) == condition.NO_SEED


# ------------------------------------------------------------------------------ Y7-5 rules
def _metric(events: list, bad: list | None = None) -> dict:
    return {"events_full": events, "events_capped": False, "bad_436": bad or []}


def test_j7_ed7_compares_name_leg_reason_and_records_the_period_shift() -> None:
    import jp3_ed7_rules as rules

    base = _metric([(10.0, "WARN_ROD_PRESSURE_FALLBACK:FL"),
                    (10.0, "INFO_ROD_PRESSURE_FAULT_REASON:FL:D6")])
    same_later = _metric([(10.3, "WARN_ROD_PRESSURE_FALLBACK:FL"),
                          (10.3, "INFO_ROD_PRESSURE_FAULT_REASON:FL:D6")])
    items = rules.j7_items_ed7(base, same_later, [base])
    assert [item["kind"] for item in items] == ["record"] and "+3 periods" in items[0]["detail"]
    other_reason = _metric([(10.0, "WARN_ROD_PRESSURE_FALLBACK:FL"),
                            (10.0, "INFO_ROD_PRESSURE_FAULT_REASON:FL:D2")])
    assert [item["kind"] for item in rules.j7_items_ed7(base, other_reason, [base])] == ["fail"]
    unknown = _metric([(5.0, "WARN_ROD_PRESSURE_FALLBACK:RR")])
    assert "reason unknown" in rules.j7_items_ed7(base, unknown, [base])[0]["detail"]
    assert rules.j7_items_ed7(unknown, unknown, [unknown]) == []
    warn = _metric([], ["WARN_PROBE_RETRACT_NOT_OPENED"])
    assert rules.j7_items_ed7(_metric([]), warn, [])[0]["kind"] == "fail"  # Q7-C4: as now
    capped = {**base, "events_capped": True}
    assert rules.j7_items_ed7(capped, base, [])[0]["kind"] == "not_judgeable"


def test_stall_signature_condition_1_by_event() -> None:
    import jp3_ed7_rules as rules

    t = np.arange(0, 60, 0.5)
    strokes = np.full((len(t), 4), 0.4)
    phases = ["ready" if 5 <= x < 10 else "level" for x in t]
    assert rules.is_stall_signature_ed7(phases, t, strokes, 20.0)  # no READY after the event
    assert not rules.is_stall_signature_ed7(phases, t, strokes, None)  # READY was seen
    assert not rules.is_stall_signature_ed7(phases, t, strokes, 7.0)
    assert not rules.is_stall_signature_ed7([*phases[:-1], "fault"], t, strokes, 20.0)
    moving = strokes.copy()
    moving[-5:, 2] += 2e-3
    assert not rules.is_stall_signature_ed7(phases, t, moving, 20.0)


def test_sensitivity_split_and_cluster_rule() -> None:
    import jp3_ed7_rules as rules

    split = rules.split_sensitivity([{"setting": "VBMslow"}, {"setting": "VBMh05"},
                                     {"setting": "VBM"}])
    assert [len(split[name]) for name in ("judged", "record", "other")] == [1, 1, 1]
    assert rules.row_key({"case": "R12", "twin": {"level": "top", "leg": "FR",
                                                  "fs_kN": 0.0}}) == "R12 top-FR-Fs0"
    units = [{"setting": "VBMslow", "row": f"R{i}", "phase": "o0", "failed": True}
             for i in range(4)]
    assert rules.cluster_judgement(units)["status"] == "pass"  # 4 singles = k
    assert rules.cluster_judgement([*units, {"setting": "VBMfast", "row": "R9", "phase": "o0",
                                             "failed": True}])["status"] == "fail"
    pair = [{"setting": "VBMc04", "row": "R12", "phase": phase, "failed": True}
            for phase in ("o0.0", "o0.05")]
    assert rules.cluster_judgement(pair)["multi_phase_clusters"] == ["VBMc04 R12"]
    observed = frozenset({("VBMc04", "R12 o0.0")})
    assert rules.cluster_judgement(pair, observed=observed)["status"] == "pass"
    assert rules.cluster_judgement([])["status"] == "not_judgeable"


def test_u832_clusters_are_the_three_edition_6_failures() -> None:
    import jp3_ed7_rules as rules

    assert rules.is_u832_cluster("bottom", "FR", 4.0, "RE1bF", "ready")
    assert not rules.is_u832_cluster("bottom", "FL", 4.0, "RE1bF", "ready")
    assert not rules.is_u832_cluster("bottom", "FR", 4.0, "RE1bF", "level")


# ------------------------------------------------------------------------------ Y7-6 / Y7-7
def test_probe_plan_counts_and_names() -> None:
    import ed7_probe as probe

    assert len(probe.KEYS) == 15 and len(probe.D_KEYS) == 12
    assert len(probe.probe_jobs(part="main")) == 15 * 6 * 7
    assert len(probe.probe_jobs(part="d")) == 24 and len(probe.probe_jobs()) == 654
    settings = probe.probe_settings()
    assert settings["P7-M-a3"][1]["lsb_parameters"] == {"ib_condition": "level_incomplete"}
    assert "probe_d6_settings" not in settings["P7-M-c2"][1]
    assert "p1_patch" not in settings["P7-L-a2"][1] and "p1_patch" in settings["P7-Mslow-a2"][1]
    assert settings["P7-M-a6"][1]["lsb_components"] == ["A_ib", "A_ii", "B3"]
    assert probe.split_setting_name("P7-Mc04-a5") == ("Mc04", "a5")
    assert not any(name.startswith("P7-") for name in probe.run_v5.ALL_SETTINGS)


def test_probe_d_keys_equal_the_record_part_d_blob() -> None:
    import ed7_key_lists
    import ed7_probe as probe

    done = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", "3ecf61f1"],
                          capture_output=True, check=False)
    if done.returncode != 0:
        pytest.skip("the record part D commit is not in this repository")
    data = ed7_key_lists.d_key_blob(ROOT)
    assert ed7_key_lists.d_jobs_from_blob(data) == [dict(job) for job in probe.D_KEY_JOBS]


def test_12b_edition_7_scans_the_required_roots_in_every_kind(tmp_path) -> None:
    import jp3_12b_plan as plan
    from test_jp3_12b_tools import write_noise

    noise = tmp_path / "noise.json"
    noise_sha = write_noise(noise)
    scan = tmp_path / "scan"
    scan.mkdir()
    required = tmp_path / "ed6_run"
    required.mkdir()
    np.savez(required / "t4h.npz", meta_json=np.array(json.dumps(
        {"key": "L2|s50|g6|0|x0|top|Fs0"})))
    with pytest.raises(plan.NotUsable, match="needs --scan-required"):
        plan.select(noise, scan, tmp_path / "p0", noise_sha256=noise_sha, edition=7)
    document = plan.select(noise, scan, tmp_path / "p1", noise_sha256=noise_sha, edition=7,
                           required_roots=(required,))
    assert [document["blocks"][f"b{j}"]["seed_index"] for j in range(1, 5)] == [60, 61, 62, 63]
    assert document["edition"] == 7 and document["inputs"]["scan_required"] == [str(required)]
    assert document["run_commands"][0].startswith("R79_V5_SETTING=VBKM0 ")
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(plan.NotUsable, match="without a file"):
        plan.select(noise, scan, tmp_path / "p2", noise_sha256=noise_sha, edition=7,
                    required_roots=(empty,))
    with pytest.raises(plan.NotUsable, match="edition 7 option"):
        plan.select(noise, scan, tmp_path / "p3", noise_sha256=noise_sha, edition=6,
                    required_roots=(required,))


def _pool_rows() -> list[dict]:
    """A synthetic stats s30 pool: the three U832 clusters, 168 other eligible clusters, one
    V0-mixed cluster and one without an unused V0-passing offset."""
    def rows(level, fs, timing, leg, event, passes=("True", "True"), used=("True", "False")):
        return [{"level": level, "fs_kN": str(fs), "timing": timing, "leg": leg,
                 "event": event, "offset_s": str(0.025 * k), "v0_pass": passes[k],
                 "used_ed6": used[k], "v0_sha": f"h{level}{fs}{leg}{event}{k}"}
                for k in range(2)]

    pool = []
    for leg, fs in (("FL", 2.0), ("FR", 2.0), ("FR", 4.0)):
        pool += rows("bottom", fs, "ready", leg, "RE1bF")
    for index in range(168):
        pool += rows("top", float(index), "level", "RR", "G4")
    pool += rows("top", 999.0, "level", "RL", "G4", passes=("True", "False"))
    pool += rows("top", 998.0, "level", "RL", "G4", used=("True", "True"))
    return pool


def test_g1_flags_keep_the_k_and_fault_jp3_denominators_apart() -> None:
    """Stats review 3 ① (user decision): U832 lines leave only the k count (168); FAULT 0 and
    J-P3 are judged on all 171 lines, and each count uses its own flag."""
    import ed7_key_lists as keys

    pool = keys.pool_document(_pool_rows(), "sha")
    assert (pool["expected_lines"], pool["k_counted_lines"],
            pool["fault_jp3_judged_lines"]) == (171, 168, 171)
    assert "judged_lines" not in pool and set(pool["line_flags"]) == {"counted_for_k",
                                                                      "judged_fault_jp3"}
    clusters = keys.pool_clusters(_pool_rows())
    lines = [{**keys.g1_line_flags(cluster), "head_only_declared": index % 10 == 0}
             for index, (cluster, entry) in enumerate(clusters.items())
             if entry["candidates"] and not entry["is_mixed"]]
    assert sum(not line["counted_for_k"] for line in lines) == 3
    assert all(line["judged_fault_jp3"] for line in lines)
    counts = keys.g1_denominators(lines)
    head_only = sum(line["head_only_declared"] for line in lines)
    assert counts == {"k_counted_lines": 168, "fault_jp3_judged_lines": 171,
                      "expected_j_p3_judged_rows": 171 - head_only}


def _blind_tree(root: Path) -> tuple[Path, Path]:
    """``<root>/06_analysis`` with the edition 7 blind folder layout: blind entries hold a
    colliding key (``s50``), a sibling outside the blind prefixes holds nothing."""
    run = root / "06_analysis" / "02_control" / "j_p3_cause" / "j9_runs" / "606f8713"
    dry = run / "cdry_a1"
    key_text = json.dumps({"key": "L2|s50|g6|0|x0|top|Fs0"})
    for blind in (dry / "VBK_c92_b1", dry / "logs"):
        blind.mkdir(parents=True)
        (blind / "run.json").write_text(key_text, encoding="utf-8")
    (dry / "VBK_c93.jsonl").write_text(key_text + "\n", encoding="utf-8")
    (dry / "VBK0_c92").mkdir()  # not blind: VBK0, not VBK_c92
    (dry / "VBK0_c92" / "run.json").write_text("{}", encoding="utf-8")
    return root / "06_analysis", run


def _guard_blind(monkeypatch) -> None:
    """Make every file-system touch of a blind path fail the test."""
    import jp3_12b_plan as plan

    def is_blind_text(path) -> bool:
        return plan.is_blind(Path(os.fspath(path)), plan.ED7_BLIND_PREFIXES)

    real_scandir, real_stat = os.scandir, os.stat

    def scandir(path="."):
        assert not is_blind_text(path), f"scandir of a blind path {path}"
        return real_scandir(path)

    def stat(path, *args, **kwargs):
        assert isinstance(path, int) or not is_blind_text(path), f"stat of a blind path {path}"
        return real_stat(path, *args, **kwargs)

    real_read_bytes = Path.read_bytes

    def read_bytes(self):
        assert not is_blind_text(self), f"read of a blind path {self}"
        return real_read_bytes(self)

    monkeypatch.setattr(os, "scandir", scandir)
    monkeypatch.setattr(os, "stat", stat)
    monkeypatch.setattr(Path, "read_bytes", read_bytes)


def test_12b_edition_7_never_touches_or_names_the_blind_paths(tmp_path, monkeypatch) -> None:
    import jp3_12b_plan as plan
    from test_jp3_12b_tools import write_noise

    noise = tmp_path / "noise.json"
    noise_sha = write_noise(noise)
    scan_root, run = _blind_tree(tmp_path / "repo")
    extra = tmp_path / "tests"
    extra.mkdir()
    _guard_blind(monkeypatch)
    document = plan.select(noise, scan_root, tmp_path / "plans", noise_sha256=noise_sha,
                           edition=7, extra_roots=(extra,), required_roots=(run,),
                           excludes=("*VBK_c9*",))  # would list blind files if walked
    # the s50 keys of the blind files were never read: no seed step
    assert [document["blocks"][f"b{j}"]["seed_index"] for j in range(1, 5)] == [50, 51, 52, 53]
    assert document["inputs"]["blind_prefixes_applied"] == len(plan.ED7_BLIND_PREFIXES) == 3
    for path in (tmp_path / "plans").iterdir():
        text = path.read_text(encoding="utf-8")
        for name in ("VBK_c92", "VBK_c93", "logs", "cdry_a1/logs"):
            assert name not in text, (path.name, name)
    assert document["inputs"]["scan_excluded_files"] == []
    with pytest.raises(plan.NotUsable, match="blind prefix"):
        plan.select(noise, scan_root, tmp_path / "p2", noise_sha256=noise_sha, edition=7,
                    required_roots=(run / "cdry_a1" / "logs",))


def test_12b_blind_prefixes_leave_edition_6_as_it_was(tmp_path) -> None:
    """Edition 6 keeps its ``rglob`` scan: the blind folder's ``s50`` key is still read."""
    import jp3_12b_plan as plan
    from test_jp3_12b_tools import write_noise

    noise = tmp_path / "noise.json"
    noise_sha = write_noise(noise)
    scan_root, _ = _blind_tree(tmp_path / "repo")
    extra = tmp_path / "tests"
    extra.mkdir()
    document = plan.select(noise, scan_root, tmp_path / "plans", noise_sha256=noise_sha,
                           edition=6, extra_roots=(extra,))
    assert document["blocks"]["b1"]["seed_index"] == 60
    assert "blind_prefixes_applied" not in document["inputs"]


def test_key_lists_g1_needs_the_seed(tmp_path, capsys) -> None:
    import ed7_key_lists

    code = ed7_key_lists.main(["--out-dir", str(tmp_path / "k"), "--pool-csv",
                               str(tmp_path / "none.csv"), "--grid-root", str(tmp_path),
                               "--only", "confirm_g1_grid171.json"])
    assert code == 2 and "needs --g1-seed" in capsys.readouterr().out


def test_unchanged_default_probe_d6_and_replace_keep_settings_frozen() -> None:
    settings = ProbeD6Settings(witness=True)
    assert replace(settings, witness_m=0.5e-3).witness_m == 0.5e-3
    assert settings.to_meta()["witness_m"] == 0.3e-3
