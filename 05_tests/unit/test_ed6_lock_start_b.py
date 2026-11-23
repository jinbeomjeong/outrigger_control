"""Edition 6 A(i) / A(ii) / B (``jp3_remedy_spec_v6.md`` 3 with the stats and hydraulics
reviews adopted on 2026-11-23; fast checks, no harness run).

Settings and options (canonical components, refusals, off = no key), tags (``_LSB`` after
``_LAS`` / ``_K1``, the existing tags unchanged), the ``run_v5`` settings of spec 3.4, the
rules on synthetic inputs (E3 triggers, ends, the dead-beat fill with its ramp-down, the
robust lower bound recomputed every period, the rod witness, priority, false triggers under
0.1 mm stroke noise), the symmetric increment limit, the G2 vector-ramp exclusion and the fixed
order of the output path in ``C2Controller.update`` and ``_level_step``.
"""

from __future__ import annotations

import inspect
import re
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.control import c2
from outrigger_sim.control.lock_start_b import (
    CAP_EVENT,
    ROD_FLOOR_PA,
    A1End,
    A2End,
    B3End,
    BEnd,
    CylinderGeometry,
    FloorInputs,
    LockAnchor,
    LockStartB,
    LockStartBSettings,
    deadbeat_fill_speed,
    extend_fill_bound_m,
    parameter_names,
    retract_fill_bound,
    void_estimate_m,
)
from outrigger_sim.hydraulics import v5_options as v5
from outrigger_sim.hydraulics.check_open_delay import RetractConfig, retract_dead
from outrigger_sim.hydraulics.v5_options import HydraulicOptions
from outrigger_sim.params import load_params

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = PROJECT_ROOT / "04_scripts" / "04_hydraulic" / "coupled"
V_MAX_M_S = 0.020924302
PERIOD_S = 0.1
STEP_M_S = 0.25 * V_MAX_M_S
U_HOLD_M_S = 0.01 * V_MAX_M_S
BAR = 1.0e5
FL = 0
GEOMETRY = CylinderGeometry(head_area_m2=np.array([1.3273e-2, 1.3273e-2, 9.503e-3, 9.503e-3]),
                            annulus_area_m2=np.array([3.770e-3, 3.770e-3, 3.142e-3, 3.142e-3]),
                            stroke_max_m=0.7, max_speed_m_s=V_MAX_M_S, period_s=PERIOD_S,
                            increment_limit_m_s=STEP_M_S)
EXISTING_TAGS = ("final_C4G2", "final_C4G2_LAS", "final_C4G2_LAS_K1", "final_C4G2_K1",
                 "final_C4G2_P3", "final_C4G2_P3_LAS_K1", "final_C4G2_P3H_LAS_K1",
                 "final_C4G2_P3W", "final_C4G2_P3W_LAS_K1", "final_C4G2_LAS_K1_TCL", "ABL_LAS_K1")


@pytest.fixture(scope="module")
def run_v5():
    sys.path.insert(0, str(COUPLED_DIR))
    try:
        import run_v5 as module

        yield module
    finally:
        sys.path.remove(str(COUPLED_DIR))


# ------------------------------------------------------------------------------ settings
def test_settings_are_off_by_default_and_canonical() -> None:
    assert not LockStartBSettings().is_enabled
    assert not c2.C2Config().lock_start_b.is_enabled
    assert not c2.C2Config().with_10hz_d1().lock_start_b.is_enabled
    settings = LockStartBSettings(components=("B", "A_i"))
    assert settings.components == ("A_i", "B1", "B3")  # "B" = B1 + B3
    assert LockStartBSettings(components=("B3",)).components == ("B3",)
    assert all(type(name) is str for name in settings.components)
    assert "components" not in parameter_names() and "a1_cap_m_s" in parameter_names()


@pytest.mark.parametrize("bad", [{"components": ("A_iii",)}, {"components": ("B1", "B1")},
                                 {"a2_fill_factor": 1.2}, {"a1_trigger_periods": 0},
                                 {"a1_trigger_periods": 2.0}, {"a2_fill_speed_ratio": 1.5},
                                 {"a2_hold_after_fill_s": 0.0}, {"b1_exit_margin_N": -1.0},
                                 {"a2_friction_band_N": (1.0, 2.0)}, {"a2_extend": 1}])
def test_settings_refuse_bad_values(bad: dict) -> None:
    with pytest.raises(ValueError):
        LockStartBSettings(**{"components": ("A_i",), **bad})


def test_preset_keyword_and_with_lock_start_b() -> None:
    preset = c2.C2Config().with_10hz_d1()
    on = c2.C2Config().with_10hz_d1(lock_start_b_components=("A_ii", "B"))
    assert on.lock_start_b.components == ("A_ii", "B1", "B3")
    assert replace(on, lock_start_b=LockStartBSettings()) == preset  # nothing else changes
    tuned = preset.with_lock_start_b(["A_i"], {"a1_cap_m_s": 1.0e-3})
    assert tuned.lock_start_b.a1_cap_m_s == 1.0e-3
    with pytest.raises(ValueError):
        preset.with_lock_start_b([])


def test_hydraulic_options_off_keep_their_dict_and_round_trip() -> None:
    assert "lsb_components" not in HydraulicOptions().to_dict()
    assert "lsb_parameters" not in HydraulicOptions().to_dict()
    options = HydraulicOptions.from_dict({"lsb_components": ["B", "A_ii"],
                                          "lsb_parameters": {"a2_fill_factor": 0.8}})
    assert options.lsb_components == ("A_ii", "B1", "B3")
    as_dict = options.to_dict()
    assert as_dict["lsb_components"] == ["A_ii", "B1", "B3"]
    assert as_dict["lsb_parameters"] == {"a2_fill_factor": 0.8}
    assert HydraulicOptions.from_dict(as_dict) == options
    with pytest.raises(ValueError, match="unknown"):
        HydraulicOptions(lsb_components=("B",), lsb_parameters=(("x", 1),))
    with pytest.raises(ValueError, match="need lsb_components"):
        HydraulicOptions(lsb_parameters=(("a2_fill_factor", 0.8),))
    with pytest.raises(SystemExit):
        v5.validate(options, period_s=0.1, engine="L2b")


def test_apply_controller_options_turns_the_components_on_and_off_is_identity() -> None:
    preset = c2.C2Config().with_10hz_d1()
    assert v5.apply_controller_options(preset, HydraulicOptions(), V_MAX_M_S, 0.1) is preset
    options = HydraulicOptions(lsb_components=("A_i", "A_ii", "B1", "B3"),
                               lsb_parameters=(("a1_step_m_s", 1e-4),))
    config = v5.apply_controller_options(preset, options, V_MAX_M_S, 0.1)
    assert config.lock_start_b.components == ("A_i", "A_ii", "B1", "B3")
    assert config.lock_start_b.a1_step_m_s == 1e-4
    v5.check_lock_start_b_config(config, options)
    with pytest.raises(RuntimeError):
        v5.check_lock_start_b_config(preset, options)
    with pytest.raises(RuntimeError):
        v5.check_lock_start_b_config(config, HydraulicOptions())
    with pytest.raises(RuntimeError):
        v5.check_lock_start_b_config(config, replace(options, lsb_parameters=()))


# ------------------------------------------------------------------------------ tags
def test_existing_tags_are_unchanged_by_the_new_suffix_helpers() -> None:
    expected = {  # the values of the helpers before edition 6 (bdb1a510)
        "final_C4G2": ("final_C4G2_LAS", "final_C4G2_K1", False, False, "final_C4G2", None),
        "final_C4G2_LAS_K1": ("final_C4G2_LAS_K1", "final_C4G2_LAS_K1", True, True,
                              "final_C4G2", None),
        "final_C4G2_K1": ("final_C4G2_LAS_K1", "final_C4G2_K1", False, True, "final_C4G2",
                          None),
        "final_C4G2_P3_LAS_K1": ("final_C4G2_P3_LAS_K1", "final_C4G2_P3_LAS_K1", True, True,
                                 "final_C4G2_P3", 4),
        "final_C4G2_P3H_LAS_K1": ("final_C4G2_P3H_LAS_K1", "final_C4G2_P3H_LAS_K1", True, True,
                                  "final_C4G2_P3H", 5),
        "final_C4G2_P3W": ("final_C4G2_P3W_LAS", "final_C4G2_P3W_K1", False, False,
                           "final_C4G2_P3W", 6),
        "final_C4G2_LAS_K1_TCL": ("final_C4G2_LAS_K1_TCL", "final_C4G2_LAS_K1_TCL", True, True,
                                  "final_C4G2", None),
        "ABL_LAS_K1": ("ABL_LAS_K1", "ABL_LAS_K1", True, True, "ABL", None),
    }
    for tag, values in expected.items():
        found = (v5.with_liftoff_slow_tag(tag), v5.with_order_gate_tag(tag),
                 v5.is_liftoff_slow_tag(tag), v5.is_order_gate_tag(tag),
                 v5.switch_base_tag(tag), v5.extend_start_revision_of_tag(tag))
        assert found == values, tag
        assert not v5.is_lock_start_b_tag(tag)


def test_lsb_suffix_follows_las_and_k1_and_keeps_the_revision() -> None:
    preset = c2.C2Config().with_10hz_d1()
    on = preset.with_lock_start_b(["A_ii"])
    assert v5.with_switch_tags("final_C4G2_P3W", preset) == "final_C4G2_P3W_LAS_K1"
    tag = v5.with_switch_tags("final_C4G2_P3W", on)
    assert tag == "final_C4G2_P3W_LAS_K1_LSB"
    assert v5.with_switch_tags(None, on) == "final_C4G2_LAS_K1_LSB"
    assert v5.extend_start_revision_of_tag(tag) == 6 and v5.is_extend_start_tag(tag)
    assert v5.is_liftoff_slow_tag(tag) and v5.is_order_gate_tag(tag)
    assert v5.is_lock_start_b_tag(tag) and v5.switch_base_tag(tag) == "final_C4G2_P3W"
    assert v5.with_liftoff_slow_tag("final_C4G2_P3W_LSB") == "final_C4G2_P3W_LAS_LSB"
    assert v5.with_order_gate_tag("final_C4G2_P3W_LAS_LSB") == "final_C4G2_P3W_LAS_K1_LSB"
    assert v5.with_lock_start_b_tag(tag) == tag
    assert v5.with_lock_start_b_tag("final_C4G2_LAS_K1_TCL") == "final_C4G2_LAS_K1_LSB_TCL"
    assert not v5.is_lock_start_b_tag(None)


# ------------------------------------------------------------------------------ run_v5
def test_edition_6_settings_are_spec_3_4(run_v5) -> None:
    lsb = ["A_i", "A_ii", "B3"]  # spec revision 6 Q6-14: the sealed range, B1 out
    vbj = run_v5.JP3_SETTINGS["VBJ"]
    assert run_v5.ED6_SETTINGS["VBL"] == (True, {**vbj[1], "lsb_components": lsb})
    assert run_v5.ED6_SETTINGS["VBL0"] == (True, {**run_v5.JP3_SETTINGS["VBJ0"][1],
                                                   "lsb_components": lsb})
    for n in "1234":
        assert run_v5.ED6_SETTINGS[f"LSL{n}"] == (True, {**run_v5.JP3_SETTINGS[f"LSJ{n}"][1],
                                                         "lsb_components": lsb})
    assert run_v5.ED6_SETTINGS["VBKL"] == (True, {**run_v5.JP3_SETTINGS["VBK"][1],
                                                   "lsb_components": lsb})
    assert run_v5.ED6_SETTINGS["VBKL0"] == (True, {**run_v5.JP3_SETTINGS["VBK0"][1],
                                                    "lsb_components": lsb})
    gates = {"VBLc005": (1.0, 0.005), "VBLc04": (1.0, 0.04), "VBLv05": (0.5, 0.02),
             "VBLv15": (1.5, 0.02)}
    for name, (scale, c_v) in gates.items():
        plant = run_v5.ED6_SETTINGS[name][1]
        assert plant == {**vbj[1], "line_fill_gate": {"kind": "VN", "volume_scale": scale,
                                                      "c_v": c_v}, "lsb_components": lsb}
    assert run_v5.ROD_FAULT_SETTINGS == ("VBK", "VBK0", "VBKL", "VBKL0")
    assert set(run_v5.ED6_SETTINGS) <= set(run_v5.T4H_SETTINGS)
    assert not set(run_v5.ED6_SETTINGS) & (set(run_v5.SETTINGS) | set(run_v5.JP3_SETTINGS))


def test_every_other_setting_keeps_the_components_off(run_v5) -> None:
    for name in (*run_v5.SETTINGS, *run_v5.JP3_SETTINGS):
        _, options = run_v5.options_of(name)
        assert options is None or not options.lsb_components, name
        assert options is None or "lsb_components" not in options.to_dict(), name
    for name in run_v5.ED6_SETTINGS:
        _, options = run_v5.options_of(name)
        preset = v5.apply_controller_options(c2.C2Config().with_10hz_d1(), options,
                                             V_MAX_M_S, 0.1)
        expected_base = "final_C4G2" if name in ("VBL0", "VBKL0") else "final_C4G2_P3W"
        assert v5.controller_tag(options, preset) == f"{expected_base}_LAS_K1_LSB", name


# ------------------------------------------------------------------------------ rules
def _inputs(t_s: float, requested, acting=None, stroke_mm=None, *, phase_level: bool = True,
            fill_phase: bool = True, fault: bool = False, previous=None, head_bar=90.0,
            rod_bar=2.0, protected=None, fallback=()) -> FloorInputs:
    requested = np.asarray(requested, float)
    return FloorInputs(
        t_s=t_s, is_level=phase_level, is_fill_phase=fill_phase, is_fault=fault,
        requested_m_s=requested,
        acting_m_s=np.zeros(4) if acting is None else np.asarray(acting, float),
        previous_output_m_s=np.zeros(4) if previous is None else np.asarray(previous, float),
        stroke_m=np.full(4, 0.3) if stroke_mm is None else np.asarray(stroke_mm, float) / 1e3,
        head_Pa=np.broadcast_to(np.asarray(head_bar, float) * BAR, (4,)).copy(),
        rod_Pa=np.broadcast_to(np.asarray(rod_bar, float) * BAR, (4,)).copy(),
        protected=np.zeros(4, bool) if protected is None else np.asarray(protected, bool),
        fallback_legs=frozenset(fallback))


def _leg(value: float, leg: int = FL) -> np.ndarray:
    speeds = np.zeros(4)
    speeds[leg] = value
    return speeds


def _deadband(**parameters) -> LockStartB:
    return LockStartB(LockStartBSettings(components=("A_i",), **parameters), GEOMETRY)


def _run_stall(lsb: LockStartB, u_m_s: float, periods: int, stroke_m_of=None):
    outputs = []
    for k in range(periods):
        stroke_mm = np.full(4, 300.0)
        if stroke_m_of is not None:
            stroke_mm[FL] = stroke_m_of(k) * 1e3
        outputs.append(lsb.apply_floors(_inputs(k * PERIOD_S, _leg(u_m_s), _leg(u_m_s),
                                                stroke_mm)))
    return np.array(outputs)


def test_a1_triggers_on_a_stalled_leg_and_ramps_to_the_cap() -> None:
    lsb = _deadband(a1_trigger_periods=10, a1_trigger_travel_m=0.002e-3, a1_cap_periods=1000)
    u_m_s = 0.3e-3
    outputs = _run_stall(lsb, u_m_s, 30)
    counts = lsb.counts[FL]
    assert counts.a1_triggers == 1 and counts.a1_trigger_periods == [10]
    assert np.all(outputs[:10, FL] == u_m_s)  # the trigger period starts at max(|u|, u_hold)
    expected = np.minimum(u_m_s + 0.2e-3 * np.arange(1, 21), 1.05e-3)
    assert np.allclose(outputs[10:, FL], expected)  # hydraulics 5: 0.2 mm/s per period
    assert outputs[-1, FL] == pytest.approx(1.05e-3)
    assert np.all(outputs[:, 1:] == 0.0)


def test_a1_default_trigger_needs_the_commanded_travel() -> None:
    lsb = _deadband()  # N_trig 10, D_trig 0.5 mm: at 0.3 mm/s the travel decides (17 periods)
    _run_stall(lsb, 0.3e-3, 30)
    assert lsb.counts[FL].a1_trigger_periods == [17]


def test_a1_ends_on_the_cap_with_the_event() -> None:
    lsb = _deadband(a1_trigger_periods=5, a1_trigger_travel_m=0.001e-3, a1_cap_periods=3)
    events = []
    for k in range(40):
        lsb.apply_floors(_inputs(k * PERIOD_S, _leg(0.3e-3), _leg(0.3e-3)))
        events += lsb.events
    counts = lsb.counts[FL]
    assert counts.a1_end[str(A1End.CAP)] >= 1 and counts.a1_cap_reached >= 1
    assert events and all(name == f"{CAP_EVENT}:FL" for _, name in events)


def test_a1_motion_witness_is_e3() -> None:
    """The floor ends once the mean of the last three reads is 0.4 mm past the mean of the
    first three reads from the trigger (a one-read step alone does not end it)."""
    lsb = _deadband(a1_trigger_periods=5, a1_trigger_travel_m=0.001e-3)
    _run_stall(lsb, 0.3e-3, 5)  # triggers in the fifth period (read 300 mm)
    assert lsb.counts[FL].a1_triggers == 1
    for k, stroke in enumerate((300.0, 300.0, 300.5, 300.5)):
        lsb.apply_floors(_inputs(0.5 + 0.1 * k, _leg(0.3e-3), _leg(0.3e-3),
                                 np.r_[stroke, np.full(3, 300.0)]))
    assert not lsb.counts[FL].a1_end  # E3: mean(300.5, 300.5, 300) - 300 = 0.33 mm
    lsb.apply_floors(_inputs(0.9, _leg(0.3e-3), _leg(0.3e-3), np.r_[300.5, np.full(3, 300.0)]))
    assert lsb.counts[FL].a1_end == {str(A1End.MOVED): 1}


@pytest.mark.parametrize(("requested", "reason"), [(-0.3e-3, A1End.SIGN),
                                                   (0.1e-3, A1End.HOLD)])
def test_a1_ends_on_sign_and_hold(requested: float, reason: A1End) -> None:
    lsb = _deadband(a1_trigger_periods=5, a1_trigger_travel_m=0.001e-3)
    _run_stall(lsb, 0.3e-3, 8)
    lsb.apply_floors(_inputs(0.8, _leg(requested), _leg(0.3e-3)))
    assert lsb.counts[FL].a1_end == {str(reason): 1}


def test_a1_acts_in_level_only_and_not_below_u_hold() -> None:
    lsb = _deadband(a1_trigger_periods=5, a1_trigger_travel_m=0.001e-3)
    _run_stall(lsb, 0.3e-3, 8)
    output = lsb.apply_floors(_inputs(0.8, _leg(0.3e-3), _leg(0.3e-3), phase_level=False))
    assert output[FL] == 0.3e-3 and lsb.counts[FL].a1_end == {str(A1End.PHASE): 1}
    slow = _deadband(a1_trigger_periods=5, a1_trigger_travel_m=1e-9)
    outputs = _run_stall(slow, 0.5 * U_HOLD_M_S, 40)
    assert slow.counts[FL].a1_triggers == 0 and np.all(outputs[:, FL] == 0.5 * U_HOLD_M_S)


def _false_triggers(u_m_s: float, seed: int, periods: int = 3000,
                    noise_m: float = 0.1e-3) -> int:
    """A leg that moves at its command with N(0, noise) stroke reads (the harness noise)."""
    rng = np.random.default_rng(seed)
    lsb = _deadband()  # the adopted thresholds
    noise = rng.normal(0.0, noise_m, periods)
    _run_stall(lsb, u_m_s, periods, lambda k: 0.3 + u_m_s * k * PERIOD_S + noise[k])
    return lsb.counts[FL].a1_triggers


def test_a1_false_triggers_under_stroke_noise() -> None:
    """0.1 mm stroke noise on a leg that moves at its command: no trigger at 0.5 and 1 mm/s
    over 300 s x 5 seeds (stats s10: 0.00 % at flow factor 1.0)."""
    for u_m_s in (0.5e-3, 1.0e-3):
        assert [_false_triggers(u_m_s, seed) for seed in range(5)] == [0] * 5, u_m_s


def test_a1_detects_a_true_stall_under_noise() -> None:
    rng = np.random.default_rng(7)
    noise = rng.normal(0.0, 0.1e-3, 200)
    lsb = _deadband()
    _run_stall(lsb, 0.4e-3, 200, lambda k: 0.3 + noise[k])
    periods = lsb.counts[FL].a1_trigger_periods
    assert periods and 13 <= periods[0] <= 20  # D_trig 0.5 mm at 0.4 mm/s: 13 periods


# A(ii) --------------------------------------------------------------------------------
def _fill(**parameters) -> LockStartB:
    return LockStartB(LockStartBSettings(components=("A_ii",), **parameters), GEOMETRY)


def _lock(lsb: LockStartB, periods: int = 2, **reads) -> None:
    for k in range(periods):
        lsb.apply_floors(_inputs(k * PERIOD_S, np.zeros(4), **reads))


def _limited(previous: np.ndarray, request: np.ndarray) -> np.ndarray:
    """The controller's symmetric increment limit (``_limited_increment`` without a guard)."""
    return previous + np.clip(request - previous, -STEP_M_S, STEP_M_S)


def test_retract_bound_is_the_robust_set_of_the_hydraulics_formula() -> None:
    settings = LockStartBSettings(components=("A_ii",))
    x_lb, p_open = retract_fill_bound(settings, GEOMETRY, FL, 90 * BAR, 2 * BAR, 0.3, 0.0)
    config = RetractConfig(rod_forward=True, volume_scale=1.0, v_line_m3=142.5e-6,
                           beta_hose_Pa=1.0e9, psi=6.0, p_crack_Pa=1e5)
    direct = retract_dead(config, 86 * BAR, 6 * BAR, 16e3, 0.3, 0.0, 1.3273e-2, 3.770e-3, 0.7,
                          0.02, 0.05, 1.6e9, 2e5)
    assert x_lb == pytest.approx(direct["need"]) and p_open == pytest.approx(direct["p_open"])
    floored, _ = retract_fill_bound(settings, GEOMETRY, FL, 90 * BAR, ROD_FLOOR_PA - 5 * BAR,
                                    0.3, 0.0)  # p_r + e stays above the floor
    floor_direct = retract_dead(config, 86 * BAR, ROD_FLOOR_PA, 16e3, 0.3, 0.0, 1.3273e-2,
                                3.770e-3, 0.7, 0.02, 0.05, 1.6e9, 2e5)["need"]
    assert floored == pytest.approx(floor_direct)
    half = replace(settings, a2_fill_factor=0.5)
    assert retract_fill_bound(half, GEOMETRY, FL, 90 * BAR, 2 * BAR, 0.3, 0.0)[0] == \
        pytest.approx(x_lb / 2)
    rear, _ = retract_fill_bound(settings, GEOMETRY, 2, 90 * BAR, 2 * BAR, 0.3, 0.0)
    rear_direct = retract_dead(config, 86 * BAR, 6 * BAR, 13.328e3, 0.3, 0.0, 9.503e-3,
                               3.142e-3, 0.7, 0.02, 0.05, 1.6e9, 2e5)["need"]
    assert rear == pytest.approx(rear_direct)


def test_void_estimate_is_the_two_chamber_formula() -> None:
    settings = LockStartBSettings(components=("A_ii",))
    anchor = LockAnchor(head_Pa=60 * BAR, rod_Pa=10 * BAR, stroke_m=0.3)
    void = void_estimate_m(settings, GEOMETRY, anchor, 90 * BAR, 2 * BAR)
    expected = ((0.05 + 0.3) * 30 * BAR / 1.6e9 + (0.02 + 0.7 - 0.3) * (-8 * BAR) / 0.69e9)
    assert void == pytest.approx(max(expected, 0.0)) and void > 0.0
    assert void_estimate_m(settings, GEOMETRY, anchor, 50 * BAR, 10 * BAR) == 0.0  # clipped


def test_extend_bound_is_the_hydraulics_formula() -> None:
    settings = LockStartBSettings(components=("A_ii",))
    p_r, p_h = 5 * BAR, 90 * BAR
    released = 2 * BAR + (p_r - 4 * BAR + 1 * BAR - 2 * BAR) / 6
    head_open = p_h - 4 * BAR + 1 * BAR - 6 * (p_r + 4 * BAR)
    expected = (max(released, head_open) - 2 * BAR) * 142.5e-6 / (1.3273e-2 * 1.0e9)
    assert extend_fill_bound_m(settings, GEOMETRY, FL, p_h, p_r) == pytest.approx(expected)
    assert 0.0 < expected < 0.25e-3  # hydraulics 2: 0 .. 0.21 mm


def test_deadbeat_plan_lands_with_its_ramp_down() -> None:
    """Stats Q-B: 1.7 mm is 5.23 -> 8.50 -> 3.27 -> 0 mm/s (4 periods)."""
    remaining, previous, profile = 1.7e-3, 0.0, []
    for _ in range(6):
        speed = deadbeat_fill_speed(remaining, previous, V_MAX_M_S, STEP_M_S, PERIOD_S)
        profile.append(speed)
        remaining -= speed * PERIOD_S
        previous = speed
    assert np.allclose(np.array(profile) * 1e3, [5.231, 8.4996, 3.269, 0.0, 0.0, 0.0],
                       atol=2e-3)
    assert remaining == pytest.approx(0.0, abs=1e-9)
    steps = np.diff(np.r_[0.0, profile])
    assert np.all(np.abs(steps) <= STEP_M_S + 1e-12)  # the ramp-down keeps the limit too


def test_increment_limit_is_symmetric() -> None:
    controller = _controller()
    controller._state.previous_output_m_s = np.array([-10e-3, 10e-3, 0.0, 0.0])
    change = controller._limited_increment(np.zeros(4))
    assert change[0] == pytest.approx(STEP_M_S) and change[1] == pytest.approx(-STEP_M_S)
    up = controller._limited_increment(np.array([0.0, 0.0, 10e-3, -10e-3]))
    assert up[2] == pytest.approx(STEP_M_S) and up[3] == pytest.approx(-STEP_M_S)


LOCKED_READS = {"head_bar": 60.0, "rod_bar": 10.0}
FILL_READS = {"head_bar": 120.0, "rod_bar": 1.0}
"""A leg locked at 60 / 10 bar whose load rose to 120 bar (rod at 1 bar): x_lb about 1.2 mm
(void included), several planned periods."""


def test_a2_fill_lands_on_the_bound_under_the_increment_limit() -> None:
    lsb = _fill()
    _lock(lsb, **LOCKED_READS)
    previous = np.zeros(4)
    for k in range(10):
        request = _leg(-0.5e-3)
        floored = lsb.apply_floors(_inputs(0.2 + 0.1 * k, request, previous, previous=previous,
                                           **FILL_READS))
        previous = _limited(previous, floored)
        lsb.after_output(previous)
        if lsb.counts[FL].a2_end:
            break
    counts = lsb.counts[FL]
    assert counts.a2_floors == 1 and counts.a2_end == {str(A2End.FILLED): 1}
    bound = counts.a2_start_bounds_m[0]
    assert 1.0e-3 < bound < 1.5e-3


def test_a2_commanded_travel_is_the_bound() -> None:
    """The fill periods command exactly ``x_lb`` (plus at most the leg's own command)."""
    lsb = _fill()
    _lock(lsb)
    previous, commanded = np.zeros(4), 0.0
    for k in range(10):
        floored = lsb.apply_floors(_inputs(0.2 + 0.1 * k, _leg(-0.5e-3), previous,
                                           previous=previous))
        is_filling = bool(lsb._fill[FL].is_on)
        previous = _limited(previous, floored)
        lsb.after_output(previous)
        if is_filling:
            commanded += abs(previous[FL]) * PERIOD_S
        if lsb.counts[FL].a2_end:
            break
    bound = lsb.counts[FL].a2_start_bounds_m[0]
    assert bound - 1e-9 <= commanded <= bound + 0.5e-3 * PERIOD_S + 1e-9


def test_a2_bound_is_recomputed_every_period() -> None:
    lsb = _fill(a2_fill_speed_ratio=0.01)  # a slow fill keeps the episode open
    _lock(lsb)
    lsb.apply_floors(_inputs(0.2, _leg(-0.5e-3)))
    first = lsb._fill[FL].lower_bound_m
    lsb.apply_floors(_inputs(0.3, _leg(-0.5e-3), head_bar=120.0))
    assert lsb._fill[FL].lower_bound_m > first  # higher head pressure, larger bound
    arrays = lsb.trace_arrays_at(np.array([0.2, 0.3]))
    assert arrays["lsb_a2_lower_bound_m"][1, FL] > arrays["lsb_a2_lower_bound_m"][0, FL]


def test_a2_bound_of_every_period_carries_the_band_and_the_void() -> None:
    """Stats s21 recheck: kappa 1.0 is a lower bound only with the robust band term
    (2 F_s,max) in the bound recomputed every period from that period's reads and the void of
    the lock anchor."""
    lsb = _fill(a2_fill_speed_ratio=0.01)
    _lock(lsb, head_bar=60.0, rod_bar=10.0)  # the anchor: 60 / 10 bar, 300 mm
    anchor = LockAnchor(head_Pa=60 * BAR, rod_Pa=10 * BAR, stroke_m=0.3)
    for k, (head_bar, rod_bar) in enumerate(((90.0, 2.0), (100.0, 1.0), (80.0, 3.0))):
        lsb.apply_floors(_inputs(0.2 + 0.1 * k, _leg(-0.5e-3), head_bar=head_bar,
                                 rod_bar=rod_bar))
        void = void_estimate_m(lsb.settings, GEOMETRY, anchor, head_bar * BAR, rod_bar * BAR)
        expected, _ = retract_fill_bound(lsb.settings, GEOMETRY, FL, head_bar * BAR,
                                         rod_bar * BAR, 0.3, void)
        assert lsb._fill[FL].lower_bound_m == pytest.approx(expected), k
        without_band = replace(lsb.settings, a2_friction_band_N=(0.0,) * 4)
        larger, _ = retract_fill_bound(without_band, GEOMETRY, FL, head_bar * BAR,
                                       rod_bar * BAR, 0.3, void)
        assert larger > expected  # the band term is in the bound
    assert lsb.settings.a2_friction_band_N == (16e3, 16e3, 13.328e3, 13.328e3)
    assert lsb.settings.a2_fill_factor == 1.0


@pytest.mark.parametrize(("second", "reason"), [
    ({"requested": _leg(-0.1e-3)}, A2End.HOLD),
    ({"requested": _leg(0.5e-3)}, A2End.SIGN),
    ({"requested": _leg(-0.5e-3), "fault": True}, A2End.FAULT),
    ({"requested": _leg(-0.5e-3), "fill_phase": False}, A2End.FAULT),
    ({"requested": _leg(-0.5e-3), "stroke_mm": np.r_[298.9, np.full(3, 300.0)]}, A2End.MOVED),
    ({"requested": _leg(-0.5e-3), "rod_bar": np.r_[42.0, np.full(3, 2.0)]}, A2End.ROD_WITNESS),
])
def test_a2_end_reasons(second: dict, reason: A2End) -> None:
    lsb = _fill(a2_fill_speed_ratio=0.01)
    _lock(lsb, stroke_mm=np.full(4, 300.0))
    lsb.apply_floors(_inputs(0.2, _leg(-0.5e-3), stroke_mm=np.full(4, 300.0)))
    requested = second.pop("requested")
    stroke = second.pop("stroke_mm", np.full(4, 300.0))
    lsb.apply_floors(_inputs(0.3, requested, stroke_mm=stroke, **second))
    assert lsb.counts[FL].a2_end == {str(reason): 1}


def test_a2_head_pressure_changes_are_no_witness() -> None:
    """Hydraulics 3: the head signal is not used (a head fall keeps the fill going)."""
    lsb = _fill(a2_fill_speed_ratio=0.01)
    _lock(lsb)
    lsb.apply_floors(_inputs(0.2, _leg(-0.5e-3), head_bar=110.0))
    lsb.apply_floors(_inputs(0.3, _leg(-0.5e-3), head_bar=90.0))
    lsb.apply_floors(_inputs(0.4, _leg(-0.5e-3), head_bar=80.0))
    assert lsb._fill[FL].is_on and not lsb.counts[FL].a2_end


def test_a2_rod_witness_threshold() -> None:
    lsb = _fill(a2_fill_speed_ratio=0.01)
    _lock(lsb)
    lsb.apply_floors(_inputs(0.2, _leg(-0.5e-3)))
    fill = lsb._fill[FL]
    _, open_Pa = retract_fill_bound(lsb.settings, GEOMETRY, FL, 90 * BAR, 2 * BAR, 0.3, 0.0)
    assert fill.rod_witness_Pa == pytest.approx(max(3 * BAR, 0.5 * (open_Pa - 2 * BAR)))
    below = 2.0 + fill.rod_witness_Pa / BAR - 0.1
    lsb.apply_floors(_inputs(0.3, _leg(-0.5e-3), rod_bar=np.r_[below, np.full(3, 2.0)]))
    assert lsb._fill[FL].is_on


def test_a2_extension_is_off_by_default() -> None:
    lsb = _fill()
    _lock(lsb)
    lsb.apply_floors(_inputs(0.2, _leg(0.5e-3)))
    assert lsb.counts[FL].a2_floors == 0
    on = _fill(a2_extend=True)
    _lock(on, head_bar=150.0)
    on.apply_floors(_inputs(0.2, _leg(0.5e-3), head_bar=150.0))
    assert on.counts[FL].a2_floors == 1


def test_a2_starts_on_a_reversal_and_skips_fallback_legs_and_missing_rod_readings() -> None:
    lsb = _fill()
    lsb.apply_floors(_inputs(0.0, _leg(-0.5e-3), _leg(-2e-3), previous=_leg(-2e-3)))
    assert lsb.counts[FL].a2_floors == 0  # no lock, no reversal
    lsb.apply_floors(_inputs(0.1, _leg(-0.5e-3), _leg(2e-3), previous=_leg(2e-3)))
    assert lsb.counts[FL].a2_floors == 1  # the direction change empties the line
    fallback = _fill()
    _lock(fallback, fallback=(FL,))
    fallback.apply_floors(_inputs(0.2, _leg(-0.5e-3), fallback=(FL,)))
    assert fallback.counts[FL].a2_floors == 0
    no_rod = _fill()
    _lock(no_rod, rod_bar=np.nan)
    no_rod.apply_floors(_inputs(0.2, _leg(-0.5e-3), rod_bar=np.nan))
    assert no_rod.counts[FL].a2_floors == 0


def test_a2_hold_variant_holds_one_increment_until_the_timeout() -> None:
    lsb = _fill(a2_hold_after_fill_s=1.0)
    _lock(lsb)
    previous, outputs = np.zeros(4), []
    for k in range(20):
        floored = lsb.apply_floors(_inputs(0.2 + 0.1 * k, _leg(-0.5e-3), previous,
                                           previous=previous))
        previous = _limited(previous, floored)
        lsb.after_output(previous)
        outputs.append(previous[FL])
        if lsb.counts[FL].a2_end:
            break
    counts = lsb.counts[FL]
    assert counts.a2_end == {str(A2End.HOLD_TIMEOUT): 1} and counts.a2_hold_periods >= 10
    assert min(outputs[:-1]) <= -STEP_M_S + 1e-12  # the held speed floor is one increment


def test_protected_legs_keep_their_command() -> None:
    lsb = _fill()
    _lock(lsb, **LOCKED_READS)
    protected = np.array([True, False, False, False])
    output = lsb.apply_floors(_inputs(0.2, np.full(4, -0.5e-3), protected=protected,
                                      **FILL_READS))
    assert output[FL] == -0.5e-3
    assert np.allclose(output[1:], -STEP_M_S)  # the first planned period of the others


# B ------------------------------------------------------------------------------------
def test_b_blocks_retraction_and_ends_on_the_load() -> None:
    lsb = LockStartB(LockStartBSettings(components=("B",)), GEOMETRY)
    speeds = np.array([-1e-3, -1e-3, -1e-3, 1e-3])
    assert np.array_equal(lsb.blocked_retract_speeds(speeds, np.zeros(4, np.int64)), speeds)
    lsb.start_event_order(2, 10.0)
    blocked = lsb.blocked_retract_speeds(speeds, np.array([0, 1, 0, 0], np.int64))
    assert blocked.tolist() == [-1e-3, 0.0, 0.0, 1e-3]
    assert lsb.counts[2].b1_blocked_periods == 1 and lsb.counts[1].b1_blocked_periods == 1
    assert lsb.required_samples(2, 2) == 2  # B2 off by default (stats Q-G)
    for k in range(2):
        lsb.update_event_exit(10.1 + 0.1 * k, 20e3, 11.4e3)
    assert lsb.event_leg == 2
    lsb.update_event_exit(10.3, 20e3, 11.4e3)  # N_B 3
    assert lsb.event_leg is None and lsb.b_episodes[-1]["end"] == str(BEnd.LOAD)
    lsb.start_event_order(0, 11.0)
    lsb.start_event_order(3, 11.5)
    assert lsb.b_episodes[-1]["end"] == str(BEnd.REPLACED) and lsb.event_leg == 3


def test_b2_option_shortens_the_start_of_the_predicted_leg() -> None:
    lsb = LockStartB(LockStartBSettings(components=("B",), b2_required_samples=1), GEOMETRY)
    lsb.start_event_order(2, 10.0)
    assert lsb.required_samples(2, 2) == 1 and lsb.required_samples(1, 2) == 2


def _b3_period(lsb: LockStartB, t_s: float, is_released: bool, travel_m: float = 0.1e-3) -> bool:
    """One LEVEL period as the controller runs it: the checks, then the commanded travel."""
    lsb.update_pre_twist(t_s, is_released)
    if lsb.pre_twist_leg is None:
        return False
    return lsb.command_pre_twist(t_s, travel_m, 0.04)


def test_b3_pre_twist_ends_resolved_on_travel_cap_and_replacement() -> None:
    lsb = LockStartB(LockStartBSettings(components=("B3",)), GEOMETRY)
    assert lsb.settings.b3_end_periods == 2 and lsb.settings.b3_travel_cap_fraction == 0.065
    assert lsb.settings.b3_protect_margin_N == 35e3
    lsb.start_pre_twist(3, 10.0)
    assert _b3_period(lsb, 10.0, False)
    assert _b3_period(lsb, 10.1, True)
    assert _b3_period(lsb, 10.2, False)  # a falling period resets the count
    assert _b3_period(lsb, 10.3, True)
    assert not _b3_period(lsb, 10.4, True)  # 2 resolved periods in a row
    episode = lsb.b3_episodes[-1]
    assert episode["end"] == str(B3End.RESOLVED) == "resolved" and episode["periods"] == 4
    assert episode["commanded_travel_m"] == pytest.approx(0.4e-3)
    assert lsb.counts[3].b3_periods == 4
    lsb.start_pre_twist(1, 11.0)
    assert _b3_period(lsb, 11.0, False, 2.0e-3)
    assert not _b3_period(lsb, 11.1, False, 2.0e-3)  # 4.0 mm would pass 0.065 x 40 = 2.6 mm
    episode = lsb.b3_episodes[-1]
    assert episode["end"] == "travel_cap" and episode["commanded_travel_m"] == pytest.approx(2e-3)
    lsb.start_pre_twist(0, 12.0)
    lsb.start_pre_twist(2, 12.1)
    assert lsb.b3_episodes[-1]["end"] == str(B3End.REPLACED) and lsb.pre_twist_leg == 2
    assert lsb.record()["b3_active_leg"] == "RL"


def test_b3_period_limit_option_and_no_restart_after_protect() -> None:
    lsb = LockStartB(LockStartBSettings(components=("B3",), b3_max_periods=2), GEOMETRY)
    lsb.start_pre_twist(3, 10.0)
    assert _b3_period(lsb, 10.0, False) and _b3_period(lsb, 10.1, False)
    assert not _b3_period(lsb, 10.2, False)
    assert lsb.b3_episodes[-1]["end"] == "travel_cap"
    lsb.start_pre_twist(3, 11.0)
    lsb.end_pre_twist(11.1, B3End.PROTECT)
    lsb.start_pre_twist(3, 11.2)  # blocked in this LEVEL stretch
    assert lsb.pre_twist_leg is None and lsb.b3_episodes[-1]["end"] == "protect"
    lsb.clear_protect_block()
    lsb.start_pre_twist(3, 20.0)
    assert lsb.pre_twist_leg == 3


def _b3_controller() -> c2.C2Controller:
    controller = _controller(("B3",))
    state = controller._state
    state.phase = c2.C2Phase.LEVEL
    state.touched[:] = True
    return controller


def test_b3_starts_with_the_reapproach_conditions_and_takes_its_rate() -> None:
    controller = _b3_controller()
    reading = _reading(50.0)
    controller._start_event_order(3, reading)
    lsb = controller._lock_start_b_state()
    assert lsb.pre_twist_leg == 3 and lsb.event_leg is None  # B3 alone: no B1 episode
    rate = controller._twist_channel_rate(reading, is_held=True, pre_twist_leg=3)
    assert rate == controller._lift_twist_rate(reading, 3)  # factor 1 (spec revision 5)
    assert rate != 0.0
    blocked = _b3_controller()
    blocked._state.is_reapproach_armed[3] = False
    blocked._start_event_order(3, reading)
    assert blocked._lock_start_b_state().pre_twist_leg is None
    single = _b3_controller()
    single._state.active_reapproaches[1] = object()  # another leg re-approaches
    single._start_event_order(3, reading)
    assert single._lock_start_b_state().pre_twist_leg is None


def test_b3_factor_is_at_most_one_in_the_pre_loc_window() -> None:
    """Spec revision 5: no P-S8-30 x4 for the pre-twist; the RT 2 re-trigger factor stays."""
    controller = _b3_controller()
    pause = controller.config.pre_loc_lift_pause
    assert pause.enable and pause.reapproach_speed_factor > 1.0
    assert controller._is_in_pre_loc_window()  # no LOC yet
    reading = _reading(50.0)
    base = controller._lift_twist_rate(reading, 3)
    assert controller._pre_twist_rate(reading, 3) == base
    settings = controller.config.r8.lifted_reapproach
    controller._state.reapproach_last_end_s = 49.9  # a re-trigger window
    assert settings.is_retrigger(50.0, 49.9) and settings.retrigger_speed_factor == 0.6
    assert controller._pre_twist_rate(reading, 3) == pytest.approx(base * 0.6)


def test_b3_travel_cap_counts_the_fastest_leg() -> None:
    """Spec revision 5: the commanded travel is max|n| |tau_dot| T, also for a leg whose own
    component is smaller (front and rear legs differ)."""
    controller = _b3_controller()
    twist = controller.geometry.twist_vector
    slow_leg = int(np.argmin(np.abs(twist)))
    assert abs(twist[slow_leg]) < np.max(np.abs(twist))
    controller._start_event_order(slow_leg, _reading(50.0))
    reading = _loads_reading(50.1, 60e3)
    rate = controller._pre_twist_rate(reading, slow_leg)
    assert controller._update_pre_twist(reading, np.zeros(4, bool)) == slow_leg
    commanded = controller._lock_start_b_state().pre_twist.commanded_m
    assert commanded == pytest.approx(float(np.max(np.abs(twist))) * abs(rate) * 0.1)
    assert commanded > abs(twist[slow_leg] * rate) * 0.1
    periods = 1
    while controller._update_pre_twist(_loads_reading(50.1 + 0.1 * periods, 60e3),
                                       np.zeros(4, bool)) is not None:
        periods += 1
    lsb = controller._lock_start_b_state()
    episode = lsb.b3_episodes[-1]
    assert episode["end"] == "travel_cap"
    assert episode["commanded_travel_m"] <= 0.065 * 0.04 + 1e-12
    assert episode["commanded_travel_m"] + commanded > 0.065 * 0.04


def test_b3_protection_holds_the_pre_twist_at_zero() -> None:
    controller = _b3_controller()
    low = c2._Reading(50.0, np.full(4, 90e3), np.full(4, 0.3), np.full(4, 0.3),
                      np.full(4, 90e3), np.full(4, 1e3), np.full(4, 90e3), np.full(4, 90e3))
    assert controller._pre_twist_rate(low, 3) == 0.0


def _loads_reading(t_s: float, lower_N: float) -> c2._Reading:
    force = np.full(4, 90e3)
    return c2._Reading(t_s, force, np.full(4, 0.3), np.full(4, 0.3), force,
                       np.full(4, lower_N), force, force)


def test_b3_own_protection_ends_the_pre_twist() -> None:
    """Dynamics review: below F_min + 35 kN (about 44 kN) on a leg the twist unloads the
    pre-twist ends (``protect``), although the re-approach protection (F_min + 5 kN) passes."""
    controller = _b3_controller()
    controller._start_event_order(3, _reading(50.0))
    reapproaching = np.zeros(4, bool)
    assert controller._update_pre_twist(_loads_reading(50.1, 60e3), reapproaching) == 3
    lsb = controller._lock_start_b_state()
    assert lsb.pre_twist.commanded_m > 0.0  # commanded twist travel, not the stroke
    assert controller._lift_twist_rate(_loads_reading(50.2, 30e3), 3) is not None
    assert controller._update_pre_twist(_loads_reading(50.2, 30e3), reapproaching) is None
    assert lsb.b3_episodes[-1]["end"] == "protect"
    controller._start_event_order(3, _reading(50.3))
    assert lsb.pre_twist_leg is None  # no restart in this LEVEL stretch


def test_b3_predictive_protection_option() -> None:
    controller = c2.C2Controller.from_params(
        load_params(), c2.C2Config().with_10hz_d1().with_lock_start_b(
            ["B3"], {"b3_protect_predictive": True}))
    controller._state.phase = c2.C2Phase.LEVEL
    controller._state.touched[:] = True
    twist = controller.geometry.twist_vector
    unloaded = np.sign(twist) != np.sign(twist[3])
    for lower_N in (60e3, 400e3):
        reading = _loads_reading(50.0, lower_N)
        rate = controller._pre_twist_rate(reading, 3)
        assert rate != 0.0
        loads_N = controller._load_estimate_N(reading.cylinder_force_lower_N)
        step_N = 21.7e6 * np.abs(twist) * float(twist @ twist) * abs(rate) * 0.1
        expected = bool(np.any((loads_N - 2 * step_N)[unloaded]
                               < controller.geometry.F_min_N + 5e3))
        assert controller._is_pre_twist_protected(reading, 3, rate) is expected
    assert controller._is_pre_twist_protected(_loads_reading(50.0, 400e3), 3, 0.0) is False


def test_b3_hands_over_to_the_formal_reapproach() -> None:
    controller = _b3_controller()
    controller._start_event_order(3, _reading(50.0))
    reapproaching = np.array([False, False, False, True])
    assert controller._update_pre_twist(_reading(50.1), reapproaching) is None
    assert controller._lock_start_b_state().b3_episodes[-1]["end"] == str(B3End.HANDOVER)


@pytest.mark.parametrize(("previous_kN", "latest_kN", "released"), [
    (20.0, 20.0, True), (19.0, 20.0, True), (21.0, 20.0, False), (15.0, 16.0, False)])
def test_b3_release_is_p5_without_a_fall(previous_kN: float, latest_kN: float,
                                         released: bool) -> None:
    """Stats s30: released = the lower estimate >= P5 (F_min + 7 kN, about 16.4 kN) and not
    below the previous period's, computed every LEVEL period."""
    controller = _b3_controller()
    history = controller._state.load_estimate_history
    history.clear()
    for value_kN in (previous_kN, latest_kN):
        estimate = np.full(4, 60e3)
        estimate[3] = value_kN * 1e3
        history.append(estimate)
    assert controller._is_pre_twist_released(3) is released


def test_trace_arrays_align_on_the_read_times() -> None:
    lsb = _fill()
    for k in range(3):
        lsb.apply_floors(_inputs(k * PERIOD_S, np.zeros(4) if k < 2 else _leg(-0.5e-3)))
    arrays = lsb.trace_arrays_at(np.array([0.0, 0.15, 0.2]))
    assert arrays["lsb_read_found"].tolist() == [True, False, True]
    assert arrays["lsb_a2_on"][2, FL] and not arrays["lsb_a2_on"][0].any()
    assert np.isnan(arrays["lsb_input_m_s"][1]).all()
    assert arrays["lsb_event_leg"].tolist() == [-1, -1, -1]
    assert all(value.shape[0] == 3 for value in arrays.values())


# ------------------------------------------------------------------------------ controller
def _controller(components=("A_ii",), **parameters) -> c2.C2Controller:
    config = c2.C2Config().with_10hz_d1().with_lock_start_b(components, parameters)
    return c2.C2Controller.from_params(load_params(), config)


def _reading(t_s: float, stroke_m: float = 0.3) -> c2._Reading:
    force = np.full(4, 90e3)
    return c2._Reading(t_s, force, np.full(4, stroke_m), np.full(4, stroke_m), force, force,
                       force, force)


def _measurements(t_s: float, stroke_m: float = 0.3, head_bar: float = 120.0,
                  rod_bar: float = 1.0) -> c2.Measurements:
    return c2.Measurements(t_s=t_s, specific_force_m_s2=np.array([0.0, 0.0, 9.81]),
                           angular_rate_rad_s=np.zeros(3),
                           head_pressure_Pa=np.full(4, head_bar * BAR),
                           stroke_m=np.full(4, stroke_m), rod_pressure_Pa=np.full(4, rod_bar * BAR))


def _level_controller(**parameters) -> c2.C2Controller:
    controller = _controller(**parameters)
    controller._state.phase = c2.C2Phase.LEVEL
    for k in range(2):  # two locked periods (N_lock)
        controller._apply_lock_start_floors(_reading(0.8 + 0.1 * k),
                                            _measurements(0.8, **LOCKED_READS),
                                            np.zeros(4), controller._lift_guard_period_count())
    return controller


def test_increment_limit_and_end_slowdown_act_after_the_rules() -> None:
    controller = _level_controller()
    assert controller._lock_start_b_state().geometry.increment_limit_m_s == \
        pytest.approx(0.25 * controller.geometry.max_speed_m_s)
    floored = controller._apply_lock_start_floors(_reading(1.0), _measurements(1.0),
                                                  _leg(-0.5e-3),
                                                  controller._lift_guard_period_count())
    max_speed = controller.geometry.max_speed_m_s
    assert floored[FL] == pytest.approx(-0.25 * max_speed)  # the first planned period
    output = controller._apply_output_ramp(floored)
    assert output[FL] == pytest.approx(-0.25 * max_speed)  # U-R8-27 increment limit (Q6-6)
    near_end = controller.geometry.stroke_soft_max_m - 0.012
    extending = controller._slow_near_stroke_end(_reading(1.1, near_end), _leg(max_speed))
    assert extending[FL] <= 0.25 * max_speed + 1e-12


def test_vector_ramp_ignores_the_raised_legs() -> None:
    """Hydraulics 7: a fill request the G2 ramp cuts must not slow the other legs."""
    base = np.array([-0.5e-3, 10e-3, 2e-3, 10e-3])
    with_rules = _level_controller()
    floored = with_rules._apply_lock_start_floors(_reading(1.0), _measurements(1.0), base,
                                                  with_rules._lift_guard_period_count())
    assert with_rules._lock_start_b_state().last_raised.tolist() == [True, False, False, False]
    off = c2.C2Controller.from_params(load_params(), c2.C2Config().with_10hz_d1())
    off._state.phase = c2.C2Phase.LEVEL
    assert with_rules.config.touch_twist_hold.vector_ramp
    expected = off._apply_output_ramp(base.copy())
    output = with_rules._apply_output_ramp(floored)
    assert np.allclose(output[1:], expected[1:])
    assert output[FL] == pytest.approx(-0.25 * with_rules.geometry.max_speed_m_s)


def test_g2_raised_leg_keeps_at_least_the_common_ratio_and_the_split_is_recorded() -> None:
    """Spec revision 5 G2 conditions: (가) the raised leg takes its own symmetric limit,
    (다) its output is at least its pre-rule command times the G2 common ratio, (라) the
    period is recorded as ``lsb_g2_split``."""
    base = np.array([-0.5e-3, 10e-3, 2e-3, 10e-3])
    controller = _level_controller()
    previous = controller._state.previous_output_m_s.copy()
    floored = controller._apply_lock_start_floors(_reading(1.0), _measurements(1.0), base,
                                                  controller._lift_guard_period_count())
    output = controller._apply_output_ramp(floored)
    step = 0.25 * controller.geometry.max_speed_m_s
    assert abs(output[FL] - previous[FL]) <= step + 1e-12  # (가)
    change = base - previous
    per_leg = np.clip(change, -step, step)
    cut = np.abs(change) > np.abs(per_leg) + 1e-12
    ratio = float(np.min(np.abs(per_leg[cut]) / np.abs(change[cut])))
    assert abs(output[FL]) >= abs(previous[FL] + ratio * change[FL]) - 1e-12  # (다)
    lsb = controller._lock_start_b_state()
    assert lsb.g2_split_periods == 1 and lsb.record()["g2_split_periods"] == 1  # (라)
    arrays = lsb.trace_arrays_at(np.array([1.0, 0.9]))
    assert arrays["lsb_g2_split"].tolist() == [True, False]


def test_a_guard_period_protects_every_leg_and_clipped_legs_keep_zero() -> None:
    controller = _controller()
    controller._state.phase = c2.C2Phase.LEVEL
    reading = _reading(1.0)
    assert controller._floor_protected_legs(reading, _leg(-0.5e-3), True).all()
    flags = controller._state.output_limit_flags
    flags[c2.OutputLimit.CRAWLER_RULE.value][FL] = True
    assert controller._floor_protected_legs(reading, _leg(-0.5e-3), False)[FL]
    at_bottom = _reading(1.0, stroke_m=0.0)
    assert controller._floor_protected_legs(at_bottom, _leg(-0.5e-3), False)[FL]


def test_meta_and_records_only_with_a_component_on() -> None:
    off = c2.C2Controller.from_params(load_params(), c2.C2Config().with_10hz_d1())
    assert "lock_start_b" not in off.meta()
    assert off.lock_start_b_trace_arrays(np.array([0.0])) == {}
    assert off.lock_start_b_record() is None
    on = _controller(("A_i", "B"))
    meta = on.meta()["lock_start_b"]
    assert meta["settings"]["components"] == ["A_i", "B1", "B3"]
    assert on.lock_start_b_record()["components"] == ["A_i", "B1", "B3"]


def _call_order(method, names: tuple[str, ...]) -> list[int]:
    source = inspect.getsource(method)
    return [re.search(rf"\b{name}\(", source).start() for name in names]


def test_output_path_order_is_fixed() -> None:
    """Spec 8 Y-1: B after the re-approach speeds and before the pre-LOC pause, LAS-b and the
    stroke-budget guard; the A rules after the phase command and before the stroke-end
    slowdown and the increment limit; the commanded fill after the increment limit."""
    update = _call_order(c2.C2Controller.update,
                         ("_phase_command", "_apply_lock_start_floors", "_slow_near_stroke_end",
                          "_apply_output_ramp", "after_output", "_delay_output"))
    assert update == sorted(update)
    level = _call_order(c2.C2Controller._level_step,
                        ("_reapproaching_legs", "_update_pre_twist", "_twist_channel_rate",
                         "_update_completion", "_update_crawler_zone",
                         "_apply_reapproach_speeds",
                         "_apply_event_order", "_apply_pre_loc_lift_pause",
                         "_apply_liftoff_approach_slow", "_apply_lift_stroke_guard",
                         "_update_stroke_end_fault", "_clip_at_stroke_ends"))
    assert level == sorted(level)
    start = _call_order(c2.C2Controller._start_reapproaches,
                        ("_reapproach_required_samples", "_defers_reapproach",
                         "_begin_reapproach"))
    assert start == sorted(start)
    ramp = _call_order(c2.C2Controller._apply_output_ramp,
                       ("_limited_increment", "_vector_ramp_outside_lock_start"))
    assert ramp == sorted(ramp)


def _share_module():
    sys.path.insert(0, str(COUPLED_DIR))
    try:
        import ed6_probe_share as share
    finally:
        sys.path.remove(str(COUPLED_DIR))
    return share


def _share_inputs(failed_by_arm: dict, stalls: dict | None = None, activation: int = 1):
    """Groups (5 plants x arms) with the given failed-key counts on plant J only, and rows."""
    share = _share_module()
    plants = tuple(share.probe.PLANTS)
    groups, rows = {}, []
    for arm in share.probe.ARMS:
        for plant in plants:
            count = failed_by_arm.get(arm, 0) if plant == "J" else 0
            groups[(plant, arm)] = {"failed_keys": [f"k{i}" for i in range(count)],
                                    "no_reference": [], "not_judgeable_items": []}
            row = {"plant": plant, "arm": arm,
                   "stall_signature": bool((stalls or {}).get((plant, arm)))}
            for keys in share.ACTIVATION_KEYS.values():
                row.update({key: activation for key in keys})
            rows.append(row)
    return share, groups, rows, plants


def test_share_rule_keeps_ties_and_drops_on_fewer_failures() -> None:
    share, groups, rows, plants = _share_inputs({"a1a2b": 2, "a2b": 2, "a1b": 3, "a1a2": 1,
                                                 "a1a2b1": 1, "a1a2bh": 1})
    decision = share.share_decision(groups, rows, plants)
    components = decision["components"]
    assert decision["status"] == "decided"
    assert components["A_i"]["keep"]  # tie with a2b: kept
    assert components["A_ii"]["keep"]  # leaving it out fails more
    assert not components["B"]["keep"]  # leaving B out fails fewer
    assert not components["B3"]["keep"]  # dropped with B
    assert decision["hold_variant"]["include"]  # 1 < 2
    assert decision["kept"] == ["A_i", "A_ii"]


def test_share_rule_b3_margin_activation_and_the_c04_stall() -> None:
    share, groups, rows, plants = _share_inputs({"a1a2b": 3, "a1a2b1": 2, "a2b": 3,
                                                 "a1b": 3, "a1a2": 3})
    decision = share.share_decision(groups, rows, plants)
    assert decision["components"]["B3"]["keep"]  # 1 fewer < margin 2: kept
    share, groups, rows, plants = _share_inputs({"a1a2b": 3, "a1a2b1": 1, "a2b": 3,
                                                 "a1b": 3, "a1a2": 3})
    assert not share.share_decision(groups, rows, plants)["components"]["B3"]["keep"]
    share, groups, rows, plants = _share_inputs({}, activation=0)
    decision = share.share_decision(groups, rows, plants)
    assert not decision["components"]["A_i"]["keep"]  # never acted
    assert not decision["components"]["B"]["keep"]  # B never acted
    b3 = decision["components"]["B3"]  # B3 has no activation rule, but goes with B
    assert not b3["keep"] and "dropped with B" in b3["rule"]
    share, groups, rows, plants = _share_inputs({}, stalls={("c04", "a2b"): True},
                                                activation=0)
    assert share.share_decision(groups, rows, plants)["components"]["A_i"]["keep"]
    groups[("J", "a1b")]["no_reference"] = [["R12", "o0.0"]]
    assert share.share_decision(groups, rows, plants)["status"] == "not_judgeable"


def test_probe_constants_match_the_12b_stall_definition() -> None:
    sys.path.insert(0, str(COUPLED_DIR))
    try:
        import ed6_probe_share as share
        import jp3_12b_judge as judge12b
    finally:
        sys.path.remove(str(COUPLED_DIR))
    assert share.STALL_WINDOW_S == judge12b.STALL_WINDOW_S
    assert share.STALL_SPAN_M == judge12b.STALL_SPAN_M
    assert share.STALL_WINDOW_TOLERANCE_S == judge12b.STALL_WINDOW_TOLERANCE_S
    assert tuple(share.STALL_LAST_PHASES) == tuple(judge12b.STALL_LAST_PHASES)
