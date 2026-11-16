"""436.9 J-P3 remedy (``06_analysis/02_control/j_p3_cause/jp3_remedy_spec.md`` 5): ③ revision 5
of the monitor, the line-fill gate, the plant options P1 / P3 at function level and the tags.

T-JR-02 tags and settings, T-JR-03 line-fill gate bound (property test, seed 20261116),
T-JR-05 hold semantics, T-JR-06 (function part) the P1 gate state, T-JR-08 the P3 law. The
harness plant parts of T-JR-06 / T-JR-07 are ``test_jp3_harness_units.py``.
"""

from __future__ import annotations

import json
import math
import pickle
from dataclasses import replace

import numpy as np
import pytest

from outrigger_sim.control.extend_start_bound import (
    EXTEND_HOLD_REVISION,
    GATE_ROD_FLOOR_PA,
    ExtendBoundCheckRev5,
    ExtendStartBound,
    LineFillGateBound,
    LineFillGateParams,
    PeriodClass,
    check_extend_start_meta,
    j_p3_judgement_rev5,
    period_class_of,
)
from outrigger_sim.control.two_pressure import (
    RodSensorState,
    TwoPressureMonitor,
    TwoPressureSettings,
)
from outrigger_sim.hydraulics import v5_options
from outrigger_sim.hydraulics.check_open_delay import (
    CheckDelayCircuit,
    CheckDelayInputs,
    CheckOpenDelay,
    CheckOpenGate,
    RetractConfig,
    retract_dead,
)
from outrigger_sim.hydraulics.rod_release import (
    FLOW_LIMITED_R6_LAW,
    flow_limited_rod_pressure,
    flow_limited_rod_pressure_r6,
)
from outrigger_sim.hydraulics.v5_options import (
    CheckDelaySetting,
    HydraulicOptions,
    LockClosureSetting,
    controller_tag,
    extend_start_revision_of_tag,
    is_extend_start_tag,
)

BAR = 1e5
PERIOD_S = 0.1
HEAD_AREA = np.array([1.3273229e-2, 1.3273229e-2, 9.50331778e-3, 9.50331778e-3])
ANNULUS = np.array([3.76991118e-3, 3.76991118e-3, 3.14159265e-3, 3.14159265e-3])
V_MAX = 0.020924
STROKE_MAX_M = 0.70
F_MIN_N = 9414.59
RETRACT_ANCHOR_PA = (34.818 * BAR, 34.352 * BAR, 31.193 * BAR, 30.591 * BAR)
RR = 3
HOLD_SPEED_M_S = 0.01 * V_MAX
"""``u_hold``: decision 146, the ratio 0.01 of ``v_max`` (0.20924 mm/s)."""
GATE_SEED = 20261116
TAU_V_S = 0.1


def _hold_settings() -> TwoPressureSettings:
    return replace(TwoPressureSettings().with_r8_period(), extend_start_rule="tracked_bound",
                   extend_start_bound=ExtendStartBound(revision=EXTEND_HOLD_REVISION))


def _monitor(settings: TwoPressureSettings) -> TwoPressureMonitor:
    monitor = TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN_N, PERIOD_S, settings=settings,
                                 stroke_max_m=STROKE_MAX_M,
                                 retract_lock_rod_pressure_Pa=RETRACT_ANCHOR_PA)
    monitor.rod_state[RR] = RodSensorState.FALLBACK
    return monitor


def _read(monitor: TwoPressureMonitor, t_s: float, command_rr: float, head_bar: float = 60.0):
    commanded = np.zeros(4)
    commanded[RR] = command_rr
    monitor.read(t_s, np.full(4, head_bar * BAR), np.full(4, 5.0 * BAR), commanded, False, 2e3,
                 stroke_m=np.full(4, 0.395))
    return monitor.extend_bound_trace_row()


def _run(monitor, commands, heads=None, t0_s=0.0) -> list[dict]:
    rows = []
    for k, command in enumerate(commands):
        head = 60.0 if heads is None else heads[k]
        rows.append(_read(monitor, t0_s + (k + 1) * PERIOD_S, command, head))
    return rows


# --- T-JR-02 tags and settings ----------------------------------------------------------------

@pytest.mark.parametrize(("tag", "revision"), [
    ("final_C4G2_P3", 4), ("final_C4G2_P3_LAS", 4), ("final_C4G2_P3_K1", 4),
    ("final_C4G2_P3_LAS_K1", 4), ("final_C4G2_P3_LAS_K1_TCL", 4), ("final_C4G2_P3_TCL", 4),
    ("final_C4G2_P3H", 5), ("final_C4G2_P3H_LAS", 5), ("final_C4G2_P3H_K1", 5),
    ("final_C4G2_P3H_LAS_K1", 5), ("final_C4G2_P3H_LAS_K1_TCL", 5), ("final_C4G2_P3H_TCL", 5),
    ("final_C4G2", None), ("final_C4G2_LAS_K1", None), ("ABL_LAS_K1", None), (None, None)])
def test_t_jr_02_revision_of_every_suffix_combination(tag, revision) -> None:
    assert extend_start_revision_of_tag(tag) == revision
    assert is_extend_start_tag(tag) is (revision is not None)


def test_t_jr_02_controller_tag_and_lists() -> None:
    assert v5_options.EXTEND_HOLD_TAGS == ("final_C4G2_P3H", "final_C4G2_P3H_LAS",
                                           "final_C4G2_P3H_LAS_K1")
    assert v5_options.EXTEND_START_TAGS == ("final_C4G2_P3", "final_C4G2_P3_LAS",
                                            "final_C4G2_P3_LAS_K1")
    hold = HydraulicOptions(extend_start_tracked=True, extend_start_hold=True)
    assert controller_tag(hold) == "final_C4G2_P3H"
    assert controller_tag(HydraulicOptions(extend_start_tracked=True)) == "final_C4G2_P3"
    plant_only = HydraulicOptions(rod_release_force=True, lock_anchor_continuous=True)
    assert controller_tag(plant_only) is None  # P1 .. P4 are setting names, not tags


def _judged_options() -> HydraulicOptions:
    """The VBJ definition (spec 4.2)."""
    return HydraulicOptions(
        rod_release_force=True, lock_closure=LockClosureSetting(0.02, 0.05),
        lock_window_follows_plant=True, extend_start_tracked=True, extend_start_hold=True,
        line_fill_gate=CheckDelaySetting("VN", 1.0, 0.02), lock_anchor_continuous=True,
        rod_flow_cap_all=True, rod_reading_truth=True)


def test_t_jr_02_options_round_trip_and_law_name() -> None:
    options = _judged_options()
    values = options.to_dict()
    assert values["m2_law"] == FLOW_LIMITED_R6_LAW
    assert HydraulicOptions.from_dict(values) == options
    assert HydraulicOptions.from_stored(values) == options
    with pytest.raises(ValueError, match="M2 law"):
        HydraulicOptions.from_dict({**values, "m2_law": "flow_limited_r5"})
    with pytest.raises(ValueError, match="rod_flow_cap_all"):
        HydraulicOptions.from_stored({**values, "rod_flow_cap_all": False})
    off = HydraulicOptions(rod_release_force=True, extend_start_tracked=True)
    assert not set(v5_options.OPTIONAL_FIELDS[1:]) & set(off.to_dict())
    assert off.to_dict()["m2_law"] == "flow_limited_r5"


@pytest.mark.parametrize("changes", [
    {"extend_start_hold": True},  # without extend_start_tracked
    {"rod_release_force": False, "lock_anchor_continuous": True},
    {"rod_release_force": False, "rod_flow_cap_all": True},
    {"rod_release_force": False, "rod_reading_truth": True},
    {"check_delay": CheckDelaySetting("VN")},  # P1 with M1c
    {"line_fill_gate": CheckDelaySetting("BL")},  # BL with LC (D-6)
    {"extend_start_hold": False},  # P1 with the revision 4 bound (counterexample ⑥)
])
def test_t_jr_02_refused_combinations(changes) -> None:
    values = {"rod_release_force": True, "lock_closure": LockClosureSetting(0.02, 0.05),
              "lock_window_follows_plant": True, "extend_start_tracked": True,
              "extend_start_hold": True, "line_fill_gate": CheckDelaySetting("VN")}
    if "extend_start_hold" in changes and changes["extend_start_hold"]:
        values["extend_start_tracked"] = False
    values.update(changes)
    with pytest.raises(ValueError):
        HydraulicOptions(**values)


def test_t_jr_02_test_switch_allows_gate_with_revision_4(monkeypatch) -> None:
    """Case replay C only: ``ALLOW_GATE_WITH_REV4_FOR_TEST``."""
    values = {"rod_release_force": True, "extend_start_tracked": True,
              "line_fill_gate": CheckDelaySetting("VN")}
    with pytest.raises(ValueError, match="revision 4"):
        HydraulicOptions(**values)
    monkeypatch.setattr(v5_options, "ALLOW_GATE_WITH_REV4_FOR_TEST", True)
    assert HydraulicOptions(**values).extend_start_revision == 4


def test_t_jr_02_harness_only_plant_options() -> None:
    options = HydraulicOptions(rod_release_force=True, lock_anchor_continuous=True)
    v5_options.validate(options, period_s=PERIOD_S)
    with pytest.raises(SystemExit):
        v5_options.validate(options, period_s=PERIOD_S, engine="L2b")
    v5_options.validate(HydraulicOptions(extend_start_tracked=True, extend_start_hold=True),
                        period_s=PERIOD_S, engine="L2b")  # the rev 5 controller alone: yes


def test_t_jr_02_cli_round_trip() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    v5_options.add_hydraulic_arguments(parser, with_valve_tau=False)
    args = parser.parse_args([
        "--rod-release-force", "--lock-overlap-ratio", "0.02", "--lock-closing-delay-s", "0.05",
        "--lock-window-follows-plant", "--extend-start-tracked", "--extend-start-hold",
        "--line-fill-gate", "VN", "--lock-anchor-continuous", "--rod-flow-cap-all",
        "--rod-reading-truth"])
    assert v5_options.hydraulic_options_from_args(args) == _judged_options()
    assert vars(parser.parse_args([])) == {}
    with pytest.raises(SystemExit):
        v5_options.hydraulic_options_from_args(parser.parse_args(["--line-fill-gate-cv", "0.03"]))


def test_t_jr_02_controller_options_build_revision_5() -> None:
    from outrigger_sim.control.c2 import C2Config

    config = v5_options.apply_controller_options(C2Config().with_10hz_d1(), _judged_options(),
                                                 V_MAX, TAU_V_S)
    meta = config.two_pressure.to_meta()
    assert meta["extend_start_rule"] == "tracked_bound"
    assert meta["extend_start_bound"]["revision"] == 5
    assert meta["extend_start_bound"]["hold_speed_ratio"] == 0.01
    assert check_extend_start_meta(meta) == 5


def test_t_jr_02_revision_4_meta_keys_unchanged() -> None:
    meta = ExtendStartBound().to_meta()
    assert set(meta) == {"bulk_modulus_Pa", "head_dead_length_m", "rod_dead_length_m",
                         "hose_factor", "speed_factor", "overlap_cut_ratio", "lag_s",
                         "back_pressure_Pa", "margin_Pa", "substep_s", "pump_flow_m3_s",
                         "volumetric_efficiency", "stroke_end_m", "saturation_stop_head_Pa",
                         "revision"}
    assert list(meta)[-1] == "revision"


# --- T-JR-05 hold semantics -------------------------------------------------------------------

def test_t_jr_05_a_micro_reversal_keeps_one_stretch() -> None:
    """(a) 0 -> +2 um/s -> -2 um/s -> 0: one stretch, never closed, ④ updated every period."""
    monitor = _monitor(_hold_settings())
    rows = _run(monitor, [0.0, 2e-6, -2e-6, 0.0], heads=[60.0, 55.0, 50.0, 45.0])
    assert [row["class"][RR] for row in rows] == ["lock", "hold", "hold", "lock"]
    stretch = monitor._lock_stretches[RR]
    assert stretch.is_open and stretch.start_t_s == pytest.approx(0.1)
    models = [row["model_bound_Pa"][RR] for row in rows]
    assert all(later > earlier for earlier, later in zip(models, models[1:], strict=False))
    assert monitor._stretch_log is None  # nothing closed


def test_t_jr_05_a_micro_command_opens_a_stretch() -> None:
    """R5-5: after an extension, a micro command alone opens the stretch."""
    monitor = _monitor(_hold_settings())
    rows = _run(monitor, [0.25 * V_MAX] * 3 + [1e-5])
    assert rows[-1]["class"][RR] == "hold"
    assert monitor._lock_stretches[RR].is_open


@pytest.mark.parametrize(("command", "expected"), [
    (HOLD_SPEED_M_S, PeriodClass.HOLD), (-HOLD_SPEED_M_S, PeriodClass.HOLD),
    (HOLD_SPEED_M_S * (1 + 1e-9), PeriodClass.CARRY_EXT),
    (-HOLD_SPEED_M_S * (1 + 1e-9), PeriodClass.CARRY_RET), (0.0, PeriodClass.LOCK)])
def test_t_jr_05_b_hold_boundary(command, expected) -> None:
    assert period_class_of(command, HOLD_SPEED_M_S, True, False) is expected
    if expected.is_carry:
        assert period_class_of(command, HOLD_SPEED_M_S, False, False).value in ("ext", "ret")
        assert period_class_of(command, HOLD_SPEED_M_S, True, True).value in ("ext", "ret")


def test_t_jr_05_c_retract_hold_adds_one_candidate_above_the_retract_model() -> None:
    monitor = _monitor(_hold_settings())
    _run(monitor, [0.0, 0.0, -1e-4], heads=[60.0, 60.0, 60.0])
    stretch = monitor._lock_stretches[RR]
    assert stretch.candidate_sources.count("retract_hold") == 1
    assert stretch.retract_hold_candidates == 1
    retract_model_Pa = monitor._retract_rod_estimate_Pa(60.0 * BAR)
    assert stretch.model_bound_Pa >= max(retract_model_Pa, RETRACT_ANCHOR_PA[RR])


@pytest.mark.parametrize("sign", [1.0, -1.0])
def test_t_jr_05_d_first_carry_period_seeds_both_directions(sign) -> None:
    """(d) R5-3: after a long extension (p_hat near p_bB) and a lock whose ④ rose, the first
    carry period seeds ④ in either direction; the next carry period keeps it sticky."""
    monitor = _monitor(_hold_settings())
    _run(monitor, [0.5 * V_MAX] * 30)
    _run(monitor, [0.0] * 5, heads=[80.0, 70.0, 60.0, 50.0, 40.0], t0_s=3.0)
    model_Pa = monitor.locked_model_bound_Pa()[RR]
    rows = _run(monitor, [sign * 0.1 * V_MAX] * 2, heads=[40.0, 40.0], t0_s=3.5)
    tracker = monitor._extend_tracker
    seeds = tracker.lock_seed_raises if sign > 0 else tracker.retract_seed_raises
    assert seeds[RR] == 1
    assert rows[0]["class"][RR] == ("carry_ext" if sign > 0 else "carry_ret")
    assert rows[0]["ext_bound_Pa"][RR] >= model_Pa  # no relief before the gate opened
    log = monitor._stretch_log[-1]
    assert log["seed_before_Pa"] < log["seed_after_Pa"] == pytest.approx(model_Pa)
    assert log["close_reason"] == "above_hold"


def test_t_jr_05_d_carry_raises_with_a_falling_head() -> None:
    """Sticky ④c: in a carry period whose head reading fell, ``p_hat`` rises to ④c."""
    monitor = _monitor(_hold_settings())
    _run(monitor, [0.5 * V_MAX] * 30)
    _run(monitor, [0.0] * 3, heads=[80.0, 80.0, 80.0], t0_s=3.0)
    _run(monitor, [0.02 * V_MAX] * 2, heads=[80.0, 60.0], t0_s=3.3)
    assert monitor._extend_tracker.carry_raises[RR] >= 1


@pytest.mark.parametrize("rule", ["inherit_when_gate_shut", "fresh_stretch"])
def test_t_jr_05_h_carry_ending_in_a_hold_keeps_the_lock_candidates(rule) -> None:
    """``carry_end_rule`` (implementer addition, case replay E LSJ4 FL 49.0 s): a short retract
    carry whose gate never opened, then a hold: with the inherit rule the new stretch keeps
    the carried candidates (④ stays at the carry's ④c); the spec 2.1 form starts afresh."""
    bound = ExtendStartBound(revision=EXTEND_HOLD_REVISION, carry_end_rule=rule)
    monitor = _monitor(replace(_hold_settings(), extend_start_bound=bound))
    _run(monitor, [0.5 * V_MAX] * 20)
    _run(monitor, [0.0] * 4, heads=[90.0, 80.0, 70.0, 60.0], t0_s=2.0)
    rows = _run(monitor, [-0.015 * V_MAX] * 2 + [-0.2e-3], heads=[58.0, 56.0, 54.0], t0_s=2.4)
    assert [row["class"][RR] for row in rows] == ["carry_ret", "carry_ret", "hold"]
    carry_bound = rows[1]["carry_bound_Pa"][RR]
    stretch = monitor._lock_stretches[RR]
    if rule == "inherit_when_gate_shut":
        assert stretch.inherited_candidates > 0
        assert rows[2]["model_bound_Pa"][RR] >= carry_bound
    else:
        assert stretch.inherited_candidates == 0
        assert rows[2]["model_bound_Pa"][RR] < carry_bound


def test_t_jr_05_e_hold_does_not_teach_the_online_ratio(monkeypatch) -> None:
    monitor = _monitor(_hold_settings())
    calls = []
    monkeypatch.setattr(type(monitor), "_is_tracking_online_ratio", property(lambda self: True))
    monkeypatch.setattr(monitor, "_track_online_ratio", lambda *args: calls.append(args[0]))
    _run(monitor, [0.0, 0.0, 1e-5, -1e-5, 0.0])
    assert calls.count(RR) == 3  # the three lock periods of RR only


def test_t_jr_05_f_revision_4_pickle_restores_with_an_empty_hold_state() -> None:
    revision_4 = replace(TwoPressureSettings().with_r8_period(), extend_start_rule="tracked_bound")
    monitor = _monitor(revision_4)
    _run(monitor, [0.25 * V_MAX] * 3 + [0.0] * 3)
    restored = pickle.loads(pickle.dumps(monitor))
    assert "gate" not in restored._extend_tracker.__dict__
    restored.refresh_settings(_hold_settings())
    row = _read(restored, 0.7, 1e-5)
    assert row["class"][RR] == "hold"
    assert restored._extend_tracker.hold_periods.tolist() == [0, 0, 0, 1]


def test_t_jr_05_f_revision_5_pickle_continues_bit_for_bit() -> None:
    monitor = _monitor(_hold_settings())
    _run(monitor, [0.25 * V_MAX] * 3 + [0.0, 1e-5])
    copy = pickle.loads(pickle.dumps(monitor))
    for k, command in enumerate((0.05 * V_MAX, 0.05 * V_MAX, 0.0, -0.05 * V_MAX)):
        t_s = 0.6 + k * PERIOD_S
        assert json.dumps(_read(monitor, t_s, command)) == json.dumps(_read(copy, t_s, command))
    assert json.dumps(copy.meta(), default=str) == json.dumps(monitor.meta(), default=str)


def test_t_jr_05_g_revision_5_keys_only_with_revision_5() -> None:
    revision_4 = _monitor(replace(TwoPressureSettings().with_r8_period(),
                                  extend_start_rule="tracked_bound"))
    revision_5 = _monitor(_hold_settings())
    for monitor in (revision_4, revision_5):
        _run(monitor, [0.25 * V_MAX] * 2 + [0.0] * 2)
    record_4 = revision_4.meta()["extend_start_record"]
    record_5 = revision_5.meta()["extend_start_record"]
    assert set(record_4) == {"extend_bound_Pa", "valve_estimate_m_s", "saturated_substeps",
                             "saturation_stop_periods", "lock_seed_raises"}
    assert set(record_5) - set(record_4) == {
        "rule_revision", "retract_seed_raises", "carry_raises", "hold_periods", "carry_periods",
        "gate_open_substeps", "gate_never_opened_carries", "hold_speed_m_s", "stretch_log"}
    assert revision_4.extend_bound_trace_row() is None
    assert "hold_periods" not in (revision_4.meta()["fallback_lock_current"] or [{}])[0]
    assert "hold_periods" in revision_5.meta()["fallback_lock_current"][0]


def test_t8_premise_commands_unchanged_without_a_fallback_leg() -> None:
    """Spec 2.8: revision 5 changes no diagnosis output while no leg falls back (the monitor's
    events and forces equal revision 4 on the same reads)."""
    revision_4 = replace(TwoPressureSettings().with_r8_period(), extend_start_rule="tracked_bound")
    monitors = []
    for settings in (revision_4, _hold_settings()):
        monitor = TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN_N, PERIOD_S,
                                     settings=settings, stroke_max_m=STROKE_MAX_M,
                                     retract_lock_rod_pressure_Pa=RETRACT_ANCHOR_PA)
        monitors.append(monitor)
    rng = np.random.default_rng(GATE_SEED)
    head = np.full(4, 60.0 * BAR)
    compared = 0
    for k in range(60):
        commanded = rng.choice([0.0, 1e-5, -1e-5, 0.1 * V_MAX, -0.05 * V_MAX], size=4)
        head = head + rng.uniform(-0.5, 0.5, size=4) * BAR  # no D1 step
        forces = [monitor.read((k + 1) * PERIOD_S, head, np.full(4, 8.0 * BAR), commanded, False,
                               2e3, stroke_m=np.full(4, 0.395)) for monitor in monitors]
        if monitors[0].fallback_legs or monitors[1].fallback_legs:
            break
        assert np.array_equal(forces[0].lower, forces[1].lower)
        assert np.array_equal(forces[0].upper, forces[1].upper)
        assert monitors[0].pop_events() == monitors[1].pop_events()
        compared += 1
    assert compared > 30


# --- T-JR-03 line-fill gate bound ---------------------------------------------------------------

def _circuit() -> CheckDelayCircuit:
    """The harness M1c circuit (``params.py`` values: L0 0.05 m, beta 1 GPa, p_T 2 bar)."""
    return CheckDelayCircuit(HEAD_AREA.copy(), ANNULUS.copy(), STROKE_MAX_M, 0.05, 0.05, 1.0e9,
                             2.0e5, V_MAX, 10.0e5)


def _gate() -> LineFillGateBound:
    return LineFillGateBound(LineFillGateParams(), HEAD_AREA, ANNULUS, STROKE_MAX_M, V_MAX)


def _valve_mean(start_m_s: float, command_m_s: float, step_s: float) -> tuple[float, float]:
    """(end, exact mean) of the first-order valve over one step."""
    keep = math.exp(-step_s / TAU_V_S)
    end = command_m_s + (start_m_s - command_m_s) * keep
    mean = command_m_s + (start_m_s - command_m_s) * (TAU_V_S / step_s) * (1.0 - keep)
    return end, mean


HEAD_READ_ERROR_PA = 4.62e5
"""Normal-grade worst head reading error (4 bar clip + 3 sigma noise + resolution; review 3.1)."""
HEAD_BUMP_MAX_PA = 3.6e5
"""Intra-period head bump of the review grid (3.4 kN ringing, ASSUMPTION of ``e_h``)."""
LOCKED_ROD_PER_HEAD = 1.2278
"""``-dp_r / dp_h`` of a locked rear leg (hydraulics_review 2): the rod moves against the bump."""


def _plant_open_time_s(plant: CheckOpenGate, leg: int, commands_m_s, head_Pa: float,
                       rod_Pa: float, band_N: float, start_valve_m_s: float,
                       step_s: float = 1e-3, head_bump_Pa: float = 0.0) -> float | None:
    """First time the P1 gate passes the speed of the locked leg. ``step_s`` 1 ms = the harness
    chunk that calls the gate (``harness_hydraulics._step_with_line_fill_gate``). The head
    rises inside every period by ``head_bump_Pa`` at mid period (equal at the reads), the rod
    pressure moves the other way by the locked ratio."""
    valve = start_valve_m_s
    chunks = round(PERIOD_S / step_s)
    for period, command in enumerate(commands_m_s):
        for sub in range(chunks):
            valve, mean = _valve_mean(valve, command, step_s)
            bump_Pa = head_bump_Pa * math.sin(math.pi * (sub + 1) / chunks)
            u = np.zeros(4)
            u[leg] = mean
            band = np.zeros(4)
            band[leg] = band_N
            rod_now_Pa = max(rod_Pa - LOCKED_ROD_PER_HEAD * bump_Pa, GATE_ROD_FLOOR_PA)
            inputs = CheckDelayInputs(0.0, step_s, u, np.full(4, head_Pa + bump_Pa),
                                      np.full(4, rod_now_Pa), np.ones(4, bool), np.zeros(4),
                                      band, np.full(4, 0.395))
            if plant.filter(inputs).speed_m_s[leg] != 0.0:
                return period * PERIOD_S + (sub + 1) * step_s
    return None


def _tracker_open_time_s(gate: LineFillGateBound, leg: int, commands_m_s, head_Pa: float,
                         rod_Pa: float, start_valve_m_s: float,
                         head_read_error_Pa: float = 0.0) -> float | None:
    """First opening of the tracker gate, classes as the monitor gives them (the gate runs only
    in carry periods and is reset in lock and hold periods); the head reading carries
    ``head_read_error_Pa``."""
    valve = start_valve_m_s
    follows_lock, step_s = True, 1e-3
    head_ub_Pa = head_Pa + head_read_error_Pa + gate.params.head_reading_margin_Pa
    for period, command in enumerate(commands_m_s):
        period_class = period_class_of(command, HOLD_SPEED_M_S, follows_lock,
                                       bool(gate.is_open[leg]))
        if period_class.is_locked:
            gate.reset(leg)
            follows_lock = True
        elif not period_class.is_carry:
            follows_lock = False
        for sub in range(round(PERIOD_S / step_s)):
            valve, mean = _valve_mean(valve, command, step_s)
            if period_class.is_carry and gate.advance_substep(
                    leg, mean, step_s, head_ub_Pa, rod_Pa, 0.395, 1 if command > 0 else -1):
                return period * PERIOD_S + (sub + 1) * step_s
        if period_class.is_carry and gate.is_open[leg]:
            follows_lock = False
    return None


def _random_commands(rng: np.random.Generator) -> list[float]:
    """1 s after a lock: zero, micro (0.05 .. 1 % v_max) and large (1 .. 25 % v_max) commands
    with random signs and direction changes."""
    commands = []
    while len(commands) < 10:
        kind = rng.integers(3)
        level = (0.0 if kind == 0 else rng.uniform(0.0005, 0.01) if kind == 1
                 else rng.uniform(0.01, 0.25))
        sign = rng.choice((-1.0, 1.0))
        commands += [sign * level * V_MAX] * int(rng.integers(1, 4))
    return commands[:10]


@pytest.mark.parametrize("kind", ["VN", "BL"])
def test_t_jr_03_tracker_gate_never_opens_before_the_plant(kind) -> None:
    """Spec T-JR-03 with the review 3.5 inputs (seed 20261116): 1,000 random command sequences,
    head 5 .. 200 bar, rod at the floor, 0, p_T or 2 .. 80 bar, plant band 0 .. 16 kN, head
    reading error -4.62 / 0 / +4.62 bar, intra-period head bump 0 .. 3.6 bar: the tracker gate
    (``e_h`` 9 bar) never opens before the plant."""
    rng = np.random.default_rng([GATE_SEED, 0 if kind == "VN" else 1])
    violations, opened = [], 0
    for sequence in range(250):
        plant = CheckOpenGate(CheckDelaySetting(kind), _circuit())
        gate = _gate()
        for leg in range(4):
            commands = _random_commands(rng)
            head_Pa = rng.uniform(5.0, 200.0) * BAR
            rod_Pa = float(rng.choice([GATE_ROD_FLOOR_PA, 0.0, 2.0e5,
                                       rng.uniform(2.0, 80.0) * BAR]))
            band_N = rng.uniform(0.0, 16.0e3)
            start_valve = rng.uniform(-1.0, 1.0) * HOLD_SPEED_M_S
            read_error_Pa = float(rng.choice([-HEAD_READ_ERROR_PA, 0.0, HEAD_READ_ERROR_PA]))
            bump_Pa = rng.uniform(0.0, HEAD_BUMP_MAX_PA)
            t_plant = _plant_open_time_s(plant, leg, commands, head_Pa, rod_Pa, band_N,
                                         start_valve, head_bump_Pa=bump_Pa)
            t_tracker = _tracker_open_time_s(gate, leg, commands, head_Pa, rod_Pa, start_valve,
                                             read_error_Pa)
            opened += t_tracker is not None
            if t_tracker is not None and (t_plant is None or t_tracker < t_plant - 1e-9):
                violations.append((sequence, leg, t_plant, t_tracker))
    assert violations == []
    assert opened > 100  # the property is not empty


def test_t_jr_03_retract_need_monotonicity_grid() -> None:
    """Review 3.3: the retract need is non-decreasing in ``p_h`` and non-increasing in ``p_r``,
    ``F_band`` and the stroke, so the gate's single point (``p_r`` floor, ``F_band`` 0, the
    stroke reading or 0) bounds every grid input from above."""
    config = RetractConfig(rod_forward=True, volume_scale=1.0, v_line_m3=285e-6,
                           beta_hose_Pa=0.5e9, psi=3.5, p_crack_Pa=3e5)

    def need(head, rod, band, stroke=0.395):
        return retract_dead(config, head, rod, band, stroke, 0.0, HEAD_AREA[RR], ANNULUS[RR],
                            STROKE_MAX_M, 0.10, 0.08, 0.69e9, 2.0e5)["need"]

    heads = np.linspace(5.0, 200.0, 20) * BAR
    rods = np.linspace(GATE_ROD_FLOOR_PA / BAR, 80.0, 20) * BAR
    bands = np.linspace(0.0, 16.0e3, 9)
    grid = np.array([[[need(h, r, b) for b in bands] for r in rods] for h in heads])
    assert np.all(np.diff(grid, axis=0) >= -1e-15)
    assert np.all(np.diff(grid, axis=1) <= 1e-15)
    assert np.all(np.diff(grid, axis=2) <= 1e-15)
    strokes = np.linspace(0.0, STROKE_MAX_M, 15)
    by_stroke = np.array([need(60.0 * BAR, GATE_ROD_FLOOR_PA, 0.0, s) for s in strokes])
    assert np.all(np.diff(by_stroke) <= 1e-15)
    gate = _gate()
    for index, head in enumerate(heads):
        upper, _ = gate.retract_need_m(RR, float(head), 0.395)
        assert upper >= grid[index].max() - 1e-15
        assert gate.retract_need_m(RR, float(head), math.nan)[0] >= upper


def test_t_jr_03_case_values_of_spec_2_4() -> None:
    """Spec 2.4 table (R12 RR 49.0 -> 49.1 s) with the decision 147 gate values: P1 plant VN
    opens at 70 ms, the tracker gate (kappa 0.8, e_h 9 bar, valve from 0.0749 mm/s, ``p_hat``
    = ④ 70 bar) at 148 ms (``hydraulics_remedy_review.md`` 3.5), +-1 ms."""
    commands = [4.71e-3] * 3
    plant = CheckOpenGate(CheckDelaySetting("VN"), _circuit())
    t_plant = _plant_open_time_s(plant, RR, commands, 35.2 * BAR, 53.9 * BAR, 0.0, 0.0749e-3,
                                 step_s=1e-3)
    gate = _gate()
    assert gate.params.head_reading_margin_Pa == 9.0e5
    head_ub_Pa = 35.2 * BAR + gate.params.head_reading_margin_Pa
    valve, t_tracker = 0.0749e-3, None
    for sub in range(300):
        valve, mean = _valve_mean(valve, 4.71e-3, 1e-3)
        if gate.advance_substep(RR, mean, 1e-3, head_ub_Pa, 70.0 * BAR, 0.395, 1):
            t_tracker = (sub + 1) * 1e-3
            break
    # +-1 ms (the review's 148 ms is the hand fill without the VN drain of the first ~9 ms,
    # which the gate keeps: 149 ms here); 1e-9 s absorbs the float sum of the 1 ms steps
    assert t_plant == pytest.approx(0.070, abs=1e-3 + 1e-9)
    assert t_tracker == pytest.approx(0.148, abs=1e-3 + 1e-9)


def test_gate_values_of_decision_147() -> None:
    params = LineFillGateParams()
    assert params.head_reading_margin_Pa == 9.0e5
    assert params.retract_friction_band_N == 0.0
    assert params.rod_floor_Pa == pytest.approx(-0.91325e5)


def test_hold_ratio_stays_below_the_premise_limit() -> None:
    """Review 2.2 (decision 147): u_hold 0.01 v_max; the hold premise needs <= 1.2 % v_max."""
    from outrigger_sim.control.extend_start_bound import HOLD_SPEED_RATIO, HOLD_SPEED_RATIO_MAX

    assert HOLD_SPEED_RATIO == 0.01 <= HOLD_SPEED_RATIO_MAX == 0.012
    assert ExtendStartBound(revision=5, hold_speed_ratio=0.012).hold_speed_ratio == 0.012
    with pytest.raises(ValueError, match="hold_speed_ratio"):
        ExtendStartBound(revision=5, hold_speed_ratio=0.0121)


# --- T-JR-06 (function part) P1 gate state ------------------------------------------------------

def test_t_jr_06_gate_state_is_the_m1c_state_bit_for_bit() -> None:
    rng = np.random.default_rng(GATE_SEED)
    delay = CheckOpenDelay(CheckDelaySetting("VN"), _circuit())
    gate = CheckOpenGate(CheckDelaySetting("VN"), _circuit())
    locked = np.ones(4, bool)
    for step in range(3000):
        if step % 200 == 0:
            command = rng.choice([0.0, 2e-6, -2e-6, 4.7e-3, -2e-3], size=4)
        inputs = CheckDelayInputs(step * 1e-3, 1e-3, command, rng.uniform(10, 90, 4) * BAR,
                                  rng.uniform(2, 60, 4) * BAR, locked.copy(), np.zeros(4),
                                  rng.uniform(0, 8e3, 4), np.full(4, 0.39))
        delay_out = delay.filter(inputs)
        gate_out = gate.filter(inputs)
        for name in CheckOpenDelay.STATE_FIELDS:
            expected, actual = getattr(delay, name), getattr(gate, name)
            is_float = np.issubdtype(np.asarray(expected).dtype, np.floating)
            assert np.array_equal(expected, actual, equal_nan=is_float), name
        held = locked & ~gate.is_open
        assert np.array_equal(gate_out.speed_m_s[~held], command[~held])
        assert not gate_out.speed_m_s[held].any()
        assert not gate_out.creep_shift_m.any() and not gate_out.opening_shift_m.any()
        assert not gate_out.lock_damping.any()
        # decision 147: the retract M2 seed is the one M1c output P1 keeps
        assert np.array_equal(gate_out.opening_rod_pressure_Pa,
                              delay_out.opening_rod_pressure_Pa, equal_nan=True)
    assert gate.summary()["mode"] == "gate_only"
    assert gate.summary()["output_exceptions"] == gate.meta()["output_exceptions"] == [
        "retract_m2_seed"]
    assert "decision 147" in gate.summary()["output_exception"]
    assert "decision 147" in gate.meta()["output_exception"]


def test_t_jr_06_micro_command_never_opens_the_gate() -> None:
    """+-2 um/s for 1 s on a locked leg: the line never reaches a check (no release)."""
    gate = CheckOpenGate(CheckDelaySetting("VN"), _circuit())
    for step in range(1000):
        command = np.full(4, 2e-6 if (step // 100) % 2 == 0 else -2e-6)
        inputs = CheckDelayInputs(step * 1e-3, 1e-3, command, np.full(4, 40 * BAR),
                                  np.full(4, 40 * BAR), np.ones(4, bool), np.zeros(4),
                                  np.zeros(4), np.full(4, 0.39))
        assert not gate.filter(inputs).speed_m_s.any()


# --- T-JR-08 P3 law -------------------------------------------------------------------------------

R6_STEP_S, R6_LAG_S = 5.0e-4, 0.05
"""Harness inner step and plant lag of the review 1.4 reference values."""
R6_LEGS = {"front": (0.013273229, 0.00376991118, 0.4011),
           "rear": (math.pi / 4 * 0.11**2, math.pi / 4 * (0.11**2 - 0.09**2), 0.3909)}
"""(A_h, A_ann, e_op) of ``hr01_p3_flow_law.LEGS`` (beta 1 GPa, L0 0.05 m, stroke 0.70 m)."""
R6_REFERENCE = {
    "front": {"c_micro_dp_bar": -0.015359048482244834, "d_micro_dp_bar": 0.0020963346417993307,
              "c22_t30_s": 0.4935, "c22_p1s_bar": 13.095464350212021,
              "c22_rate_bar_s": 43.96202401423827},
    "rear": {"c_micro_dp_bar": -0.014512402178933844, "d_micro_dp_bar": 0.0019807782658026554,
             "c22_t30_s": 0.4245, "c22_p1s_bar": 14.573809395430029,
             "c22_rate_bar_s": 50.39000004474074}}
"""``hydraulics_remedy_review.md`` 1.4 (values of ``hr01_p3_flow_law.json``)."""


def _r6_leg(name: str):
    """(params, C_r) of a review leg."""
    from outrigger_sim.hydraulics.rod_chamber import RodChamberLegParams
    from outrigger_sim.hydraulics.rod_release import RodPressureFlowLaw

    head_area, annulus, e_op = R6_LEGS[name]
    k_h = 1.0e9 * head_area / (0.05 + e_op)
    k_r = 1.0e9 * annulus / (0.05 + 0.70 - e_op)
    params = RodChamberLegParams(head_area_m2=head_area, annulus_area_m2=annulus,
                                 head_stiffness_N_m=k_h, rod_stiffness_N_m=k_r,
                                 outer_stiffness_N_m=math.inf, rod_weight_N=0.0)
    return params, RodPressureFlowLaw.rod_compliance_m3_Pa(annulus, k_h, k_r)


def _r6_run(name: str, start_Pa: float, force_N: float, speed_m_s: float, steps: int,
            is_retract: bool, law: str = "r6") -> np.ndarray:
    from outrigger_sim.hydraulics.rod_chamber import RodChamberMode

    params, compliance = _r6_leg(name)
    mode = RodChamberMode.RET if is_retract else RodChamberMode.EXT
    target_Pa = params.moving_target_rod_pressure_Pa(mode, force_N)
    pressure, values = start_Pa, []
    for _ in range(steps):
        if law == "r6":
            pressure = flow_limited_rod_pressure_r6(
                pressure, target_Pa, speed_m_s, R6_STEP_S, R6_LAG_S, compliance,
                params.head_area_m2, params.annulus_area_m2, is_retract, force_N,
                params.p_head_back_retract_Pa)
        else:
            pressure = flow_limited_rod_pressure(
                pressure, target_Pa, speed_m_s, R6_STEP_S, R6_LAG_S, compliance,
                params.head_area_m2, params.annulus_area_m2, is_retract)
        values.append(pressure)
    return np.asarray(values)


@pytest.mark.parametrize("name", ["front", "rear"])
def test_t_jr_08_reference_values_of_the_review(name) -> None:
    """Review 1.4 #2 / #3: the (c) and (d) micro cases (1 um/s x 0.1 s, < 0.1 bar) and the (c)
    example (50 bar, 22 kN, 1 mm/s) reproduce ``hr01`` to 1e-9 relative."""
    reference = R6_REFERENCE[name]
    head_area, annulus, _ = R6_LEGS[name]
    force_c = 210e5 * head_area - 80e5 * annulus
    c_micro = _r6_run(name, 80e5, force_c, 1e-6, 200, True)
    d_micro = _r6_run(name, 2e5, 10e3, 1e-6, 200, False)
    assert (c_micro[-1] - 80e5) / BAR == pytest.approx(reference["c_micro_dp_bar"], rel=1e-9)
    assert (d_micro[-1] - 2e5) / BAR == pytest.approx(reference["d_micro_dp_bar"], rel=1e-9)
    assert abs(c_micro[-1] - 80e5) < 0.1 * BAR and abs(d_micro[-1] - 2e5) < 0.1 * BAR
    example = _r6_run(name, 50e5, 22e3, 1e-3, 4000, True)
    assert (50e5 - example[0]) / R6_STEP_S / BAR == pytest.approx(reference["c22_rate_bar_s"],
                                                                  rel=1e-9)
    first_30 = int(np.flatnonzero(example <= 30e5)[0])
    assert (first_30 + 1) * R6_STEP_S == pytest.approx(reference["c22_t30_s"], abs=1e-12)
    assert example[1999] / BAR == pytest.approx(reference["c22_p1s_bar"], rel=1e-9)


@pytest.mark.parametrize("name", ["front", "rear"])
def test_t_jr_08_vmax_grid_converges_to_r5(name) -> None:
    """Review 1.4 #4: on the 1.3 grid (F, start, both directions, v_max) the 0.3 s values of r6
    and r5 differ by <= 0.3 bar; the transient maximum (<= 12 bar) is a record only."""
    worst_end_Pa = 0.0
    for force_kN in (-1.0, 0.0, 2.0, 5.0, 10.0, 25.0, 50.0, 80.0):
        for start_bar in (2.0, 5.0, 13.0, 30.0, 54.0, 80.0):
            for is_retract in (True, False):
                r6 = _r6_run(name, start_bar * BAR, force_kN * 1e3, V_MAX, 600, is_retract)
                r5 = _r6_run(name, start_bar * BAR, force_kN * 1e3, V_MAX, 600, is_retract,
                             "r5")
                worst_end_Pa = max(worst_end_Pa, abs(r6[-1] - r5[-1]))
                assert np.max(np.abs(r6 - r5)) <= 12.0 * BAR
    assert worst_end_Pa <= 0.3 * BAR


def test_t_jr_08_r5_branches_bit_for_bit() -> None:
    """Review 1.4 #1 / #4: branches (a) and (b), and every step whose cap is not binding, are
    the r5 function bit for bit."""
    params, compliance = _r6_leg("rear")
    rng = np.random.default_rng(GATE_SEED)
    for _ in range(4000):
        previous, target = rng.uniform(-0.5, 80.0, 2) * BAR
        speed = rng.uniform(0.0, V_MAX)
        is_retract = bool(rng.integers(2))
        force = rng.uniform(-5e3, 80e3)
        r5_value = flow_limited_rod_pressure(previous, target, speed, R6_STEP_S, R6_LAG_S,
                                             compliance, params.head_area_m2,
                                             params.annulus_area_m2, is_retract)
        r6_value = flow_limited_rod_pressure_r6(previous, target, speed, R6_STEP_S, R6_LAG_S,
                                                compliance, params.head_area_m2,
                                                params.annulus_area_m2, is_retract, force,
                                                params.p_head_back_retract_Pa)
        is_r5_branch = (is_retract and target >= previous) or (not is_retract
                                                                and target <= previous)
        lagged = target + (previous - target) * math.exp(-R6_STEP_S / R6_LAG_S)
        if is_r5_branch or r6_value == lagged:
            assert r6_value == r5_value


def test_t_jr_08_monotone_and_no_fixed_point() -> None:
    """Review 1.4 #5 / #6: one step is non-decreasing in ``p^(k-1)``; a retracting leg above
    its target with ``s > 0`` always loses pressure (no stall)."""
    from outrigger_sim.hydraulics.rod_chamber import RodChamberMode

    for name in ("front", "rear"):
        params, compliance = _r6_leg(name)
        for step_s in (5e-4, 1e-3):
            for force_kN in (-5.0, 0.0, 5.0, 25.0, 80.0):
                for is_retract in (True, False):
                    mode = RodChamberMode.RET if is_retract else RodChamberMode.EXT
                    target = params.moving_target_rod_pressure_Pa(mode, force_kN * 1e3)
                    previous = np.linspace(-0.9e5, 250e5, 2501)
                    values = np.array([flow_limited_rod_pressure_r6(
                        p, target, V_MAX, step_s, R6_LAG_S, compliance, params.head_area_m2,
                        params.annulus_area_m2, is_retract, force_kN * 1e3,
                        params.p_head_back_retract_Pa) for p in previous])
                    assert np.all(np.diff(values) >= -1e-6)
                    if is_retract:
                        above = previous > target
                        assert np.all(values[above] < previous[above])


CLOSED_FORM_LIMIT_N = {"front": 3.6e3, "rear": 2.2e3}
"""T-JR-17 ②: up to this net force the closed form ``phi p_bA - F / A_ann`` is the function."""
CLOSED_FORM_GAP_BAR = {"front": {5e3: -4.0, 25e3: -61.7, 50e3: -133.9},
                       "rear": {5e3: -9.7, 25e3: -80.0, 50e3: -167.9}}
"""T-JR-17 ②: closed form minus function (``hydraulics_remedy_review.md`` 10)."""


@pytest.mark.parametrize("name", ["front", "rear"])
def test_t_jr_17_closed_form_holds_only_for_light_legs(name) -> None:
    """3rd edition T-JR-17 ②: on F -20 .. 300 kN the closed form equals
    ``moving_target_rod_pressure_Pa(RET, F)`` only up to 3.6 kN (front) / 2.2 kN (rear); above,
    the function is larger by the review values."""
    from outrigger_sim.hydraulics.rod_chamber import RodChamberMode

    params, _ = _r6_leg(name)
    phi = params.head_area_m2 / params.annulus_area_m2

    def gap_Pa(force_N: float) -> float:
        closed_Pa = phi * params.p_head_back_retract_Pa - force_N / params.annulus_area_m2
        return closed_Pa - params.moving_target_rod_pressure_Pa(RodChamberMode.RET, force_N)

    limit_N = CLOSED_FORM_LIMIT_N[name]
    for force_N in np.linspace(-20e3, 300e3, 321):
        if force_N <= limit_N - 0.1e3:
            assert abs(gap_Pa(force_N)) <= 1.0
        elif force_N >= limit_N + 0.1e3:
            assert gap_Pa(force_N) < -1.0
    for force_N, expected_bar in CLOSED_FORM_GAP_BAR[name].items():
        assert gap_Pa(force_N) / BAR == pytest.approx(expected_bar, abs=0.05)


def test_t_jr_17_last_target_is_the_target_the_law_used() -> None:
    """3rd edition T-JR-17 ①: ``_RodPressureLag.last_target_Pa`` is bit for bit the target the
    same step handed to ``flow_limited_rod_pressure_r6``."""
    import sys
    import types
    from pathlib import Path

    from outrigger_sim.hydraulics.rod_chamber import RodChamberMode
    from outrigger_sim.hydraulics.rod_release import RodPressureFlowLawR6

    coupled = Path(__file__).resolve().parents[2] / "04_scripts" / "04_hydraulic" / "coupled"
    if str(coupled) not in sys.path:
        sys.path.insert(0, str(coupled))
    import harness_hydraulics

    params, compliance = _r6_leg("rear")
    k_h = 1.0e9 * params.head_area_m2 / (0.05 + 0.3909)
    k_r = 1.0e9 * params.annulus_area_m2 / (0.05 + 0.70 - 0.3909)
    plant = types.SimpleNamespace(
        flow_limiter=types.SimpleNamespace(params=types.SimpleNamespace(
            A_h=np.full(4, params.head_area_m2))),
        A_ann=np.full(4, params.annulus_area_m2), kh=np.full(4, k_h), kr=np.full(4, k_r),
        dt=R6_STEP_S, tau=R6_LAG_S)
    lag = harness_hydraulics._RodPressureLag(plant, RodPressureFlowLawR6())
    rng = np.random.default_rng(GATE_SEED)
    for _ in range(200):
        leg, direction = int(rng.integers(4)), float(rng.choice((-1.0, 1.0)))
        force, speed = rng.uniform(-5e3, 80e3), rng.uniform(0.0, V_MAX)
        previous = rng.uniform(-0.5e5, 80e5)
        lag.start(leg, previous)
        value = lag.relax(leg, direction, force, speed)
        mode = RodChamberMode.EXT if direction > 0 else RodChamberMode.RET
        target = params.moving_target_rod_pressure_Pa(mode, force)
        assert lag.last_target_Pa[leg] == target
        assert value == flow_limited_rod_pressure_r6(
            previous, target, speed, R6_STEP_S, R6_LAG_S, lag._compliance_m3_Pa[leg],
            params.head_area_m2, params.annulus_area_m2, direction < 0, force,
            params.p_head_back_retract_Pa)
    assert compliance > 0.0


def test_t_jr_08_retract_drain_guard() -> None:
    params, compliance = _r6_leg("rear")
    with pytest.raises(ValueError, match="p_bA - p_T"):
        flow_limited_rod_pressure_r6(50e5, 10e5, 1e-3, R6_STEP_S, R6_LAG_S, compliance,
                                     params.head_area_m2, params.annulus_area_m2, True, 22e3,
                                     2.4e5)


# --- revision 5 J-P3 record and judgement ---------------------------------------------------------

def test_rev5_check_classifies_by_the_monitor_class() -> None:
    check = ExtendBoundCheckRev5(np.full(4, 600.0) / ANNULUS)
    tolerance_Pa = 600.0 / ANNULUS[RR]
    classes = ["ext", "hold", "carry_ret", "lock"]
    used = np.array([10.0, 20.0, 30.0, 40.0]) * BAR
    plant = used + np.array([2.0, 0.5 * tolerance_Pa, -1.0, 1.5 * tolerance_Pa])
    states = ["locked_ret", "locked_ext", "moving_ret", "locked_ext"]
    check.add(1.0, classes, used, plant, states, None)
    record = check.record()
    assert record["jp3a_breach_reads"] == [1, 0, 0, 0]
    assert record["jp3a_by_plant_state"]["locked_ret"]["breach_reads"] == [1, 0, 0, 0]
    assert record["jp3b_breach_reads"] == [0, 1, 0, 0]
    assert record["jp3b_breach_over_tol_reads"] == [0, 0, 0, 0]
    assert record["jp3c_breach_reads"] == [0, 0, 0, 0]
    assert record["lock_ext_breach_over_tol_reads"] == [0, 0, 0, 1]
    assert record["class_reads"]["hold"] == [0, 1, 0, 0]
    assert record["trace_excerpt"]  # the breach rows are in the excerpt
    arrays = check.trace.arrays()
    assert arrays["jp3_class"].shape == (1, 4) and arrays["jp3_class"].dtype == np.int8


def test_rev5_check_splits_trapped_and_fill_shares() -> None:
    """3rd edition 6.2 / T-JR-17 ④ ⑤: a carry_ret / ret read above the plant's last target is
    trapped (J-P3c judged, ``ret_trapped``), at or below it (equal = fill, ⑤) the fill share
    (recorded); a carry_ret read of a plant leg still locked is trapped anyway (④)."""
    check = ExtendBoundCheckRev5(np.full(4, 600.0) / ANNULUS, "ideal")
    used = np.full(4, 15.0 * BAR)
    plant = np.array([20.0, 18.0, 20.0, 18.0]) * BAR  # every read breaches the bound
    target = np.array([18.0, 18.0, 25.0, 25.0]) * BAR
    check.add(1.0, ["carry_ret", "carry_ret", "carry_ret", "ret"], used, plant,
              ["moving_ret", "moving_ret", "locked_ret", "moving_ret"], None, target)
    record = check.record()
    assert record["jp3c_breach_reads"] == [1, 0, 1, 0]  # above p* / equal = fill / locked
    assert record["jp3c_fill_breach_reads"] == [0, 1, 0, 0]
    assert record["jp3c_fill_max_excess_bar"][1] == pytest.approx(3.0)
    assert record["ret_fill_breach_reads"] == [0, 0, 0, 1]
    assert record["ret_trapped_reads"] == [0, 0, 0, 0]
    assert record["sensor_grade"] == "ideal" and record["jp3_judged_row"] is True
    assert "p_star_ret_Pa" in record["trace_excerpt_columns"]
    assert check.trace.arrays()["jp3_p_star_ret_Pa"].shape == (1, 4)


def test_rev5_judgement_sums_the_judged_keys_and_refuses_revision_4_records() -> None:
    passing = {"rule_revision": 5, "jp3a_breach_reads": [0, 0, 0, 0],
               "jp3b_breach_over_tol_reads": [0, 0, 0, 0], "jp3c_breach_reads": [0, 0, 0, 0],
               "jp3b_breach_reads": [0, 2, 0, 0], "sensor_grade": "ideal"}
    assert j_p3_judgement_rev5([passing])["status"] == "pass"
    assert j_p3_judgement_rev5([passing])["jp3b_breach_reads_flag"] == 2
    breached = {**passing, "jp3c_breach_reads": [0, 0, 0, 1]}
    assert j_p3_judgement_rev5([passing, breached])["status"] == "H-7"
    old = {"breach_reads": [0, 0, 0, 0]}
    assert j_p3_judgement_rev5([old])["status"] == "setting_defect"
    assert j_p3_judgement_rev5([])["status"] == "no_p3_runs"


def test_rev5_judgement_records_only_the_conservative_and_old_worst_rows() -> None:
    """Decisions 147 / 148: J-P3 judges the ideal and normal rows; conservative and old_worst
    rows are recorded; a row without a grade is a setting defect."""
    passing = {"rule_revision": 5, "jp3a_breach_reads": [0, 0, 0, 0],
               "jp3b_breach_over_tol_reads": [0, 0, 0, 0], "jp3c_breach_reads": [0, 0, 0, 0]}
    breached = {**passing, "jp3a_breach_reads": [1, 0, 0, 0]}
    result = j_p3_judgement_rev5([passing, breached, breached], None, None,
                                 ["normal", "conservative", "old_worst"])
    assert result["status"] == "pass"
    assert result["record_only_grade_sums"]["jp3a_breach_reads"] == 2
    assert result["runs_by_case"]["record_only_sensor_grade"] == 2
    assert j_p3_judgement_rev5([{**breached, "sensor_grade": "ideal"}])["status"] == "H-7"
    missing = j_p3_judgement_rev5([passing])
    assert missing["status"] == "setting_defect"
    assert missing["runs_by_case"]["defect_sensor_grade_missing"] == 1
