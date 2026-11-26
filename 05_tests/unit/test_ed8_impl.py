"""436.9 edition 8 implementation (``jp3_remedy_spec_v8_rules.md`` 16 Y8-1 .. Y8-10), no harness.

* Y8-1 PSW: the scale mid read (stuck then moving, retract first, only the end read, the rect
  profile), K1 and the other ``ProbeResult`` fields bit-identical with the PSW on and off (N-1
  premise 1), the new fields read only by ``_update_twist_stiffness_scale`` (N-1 premise 2,
  static), the PSW scale in the controller.
* Y8-2 the ``_ED8`` tag grammar (the spec table and every older tag unchanged), the edition 8
  settings and options, the identity guard.
* Y8-3 R2: the witness as a record (D6 judges as in edition 6, no witness event).
* Y8-7 / Y8-8 H3': a short first run needs 4 samples (boundary 0.5 s), a re-trigger run and a
  run after ``T_r`` end on 3; the record.
* Y8-9 ``EventTwin`` depth / ramp, the T4h name, the event shape.
* Y8-10 L-2: the waiver limits (rise 2.5 kN, ``n_still`` 49 / 50, ``|D|`` + 0.5 = 15 kN), the
  still count after the floors (one period late), the record.
* Y8-6 the layer rule (spec 6.3) and the key files (census 1043 lines, held-out 339 slots,
  deterministic).
* The old settings run no new line (P8-0: new fields off by default).
* ``ed8_probe`` arms and part p816; ``p816_compare`` from another working folder.
"""

from __future__ import annotations

import ast
import json
import math
import os
import sys
from collections import deque
from dataclasses import fields, replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
for _path in (COUPLED_DIR, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from outrigger_sim.control import c2  # noqa: E402
from outrigger_sim.control import ground_contact as gc  # noqa: E402
from outrigger_sim.control.lock_start_b import (  # noqa: E402
    CylinderGeometry,
    FloorInputs,
    LockStartB,
    LockStartBSettings,
)
from outrigger_sim.control.two_pressure import D6Witness, TwoPressureMonitor  # noqa: E402
from outrigger_sim.hydraulics import v5_options as v5  # noqa: E402

V_MAX = 20.924e-3
T = 0.1
F_MIN = 9.415e3
PSW_TRAVEL_M = 0.05e-3
RECORDS_ROOT = Path(os.environ.get("OUTRIGGER_RECORDS_ROOT", str(ROOT)))
"""The checkout with the analysis records (the main checkout when the tests run in a
worktree)."""


# ----------------------------------------------------------------------------- Y8-1 PSW
def _probe_reading(t_s: float, motor: np.ndarray, piston: np.ndarray) -> gc.ProbeReading:
    # oil column 3e7 N/m between the motor and the piston, pad 1e7 N/m under the piston
    force = 60e3 + 3e7 * (motor - piston) + 1e7 * (piston - 0.3)
    return gc.ProbeReading(t_s=t_s, cylinder_force_N=force, rod_stroke_m=piston.copy(),
                           motor_stroke_m=motor.copy(), rate_attitude_rad=(0.0, 0.0),
                           filtered_attitude_rad=(0.0, 0.0))


def _toy_probe(settings: gc.ProbeSettings, *, stuck_until_s: float = 0.0,
               retract_first: bool = False, move_at_s: float | None = None,
               ) -> tuple[gc.ProbeRound, list[np.ndarray]]:
    """Leg FL's piston stays while ``t < stuck_until_s`` (or, with ``move_at_s``, until that
    read: it then jumps to the motor stroke); the other legs follow the motor."""
    motor = np.full(4, 0.3)
    piston = motor.copy()
    probe = gc.ProbeRound(start=_probe_reading(0.0, motor, piston), settings=settings,
                          max_speed_m_s=V_MAX, period_s=T,
                          load_sensitivity_diag_N_m=np.full(4, 5e6),
                          attitude_sensitivity_rad_m=np.zeros((4, 2)), stroke_max_m=0.70,
                          retract_first_legs=(0,) if retract_first else ())
    previous, commands, t = np.zeros(4), [], 0.0
    while not probe.is_finished and t < 60.0:
        step_m = previous * T
        motor = motor + step_m
        is_stuck = t < stuck_until_s - 1e-9
        if move_at_s is not None:
            is_stuck = t < move_at_s - 1e-9
            if not is_stuck:
                piston[0] = motor[0]
        piston[1:] += step_m[1:]
        if not is_stuck and move_at_s is None:
            piston[0] += step_m[0]
        previous = probe.step(_probe_reading(round(t, 6), motor, piston))
        commands.append(previous.copy())
        t += T
    return probe, commands


NEW_RESULT_FIELDS = ("scale_stiffness_N_m", "scale_mid_shift_periods", "moved_by_mid_m")


def _same(a, b) -> bool:
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return True
    return a == b


def test_psw_stuck_reads_move_the_scale_mid_and_keep_k1() -> None:
    off, off_commands = _toy_probe(gc.ProbeSettings(), stuck_until_s=0.65)
    on, on_commands = _toy_probe(
        gc.ProbeSettings(scale_mid_min_piston_travel_m=PSW_TRAVEL_M), stuck_until_s=0.65)
    assert all(np.array_equal(a, b) for a, b in zip(off_commands, on_commands, strict=True))
    for result_off, result_on in zip(off.results, on.results, strict=True):
        for item in fields(gc.ProbeResult):  # N-1 premise 1: existing fields bit-identical
            if item.name not in NEW_RESULT_FIELDS:
                assert _same(getattr(result_off, item.name), getattr(result_on, item.name))
    fl = on.results[0]
    assert fl.moved_by_mid_m == pytest.approx(0.0)
    assert fl.scale_mid_shift_periods >= 1
    assert math.isfinite(fl.scale_stiffness_N_m)
    assert fl.scale_stiffness_N_m != fl.incremental_stiffness_N_m
    fr = on.results[1]  # moving from the first read: the scale mid is the K1 mid
    assert fr.scale_mid_shift_periods == 0
    assert fr.scale_stiffness_N_m == fr.incremental_stiffness_N_m
    assert math.isnan(off.results[0].scale_stiffness_N_m)  # PSW off: the field stays off


def test_psw_retract_first_takes_the_sign_of_the_first_move() -> None:
    probe, _ = _toy_probe(gc.ProbeSettings(scale_mid_min_piston_travel_m=PSW_TRAVEL_M),
                          stuck_until_s=0.65, retract_first=True)
    fl = probe.results[0]
    assert fl.is_reversed and fl.moved_by_mid_m == pytest.approx(0.0)
    assert fl.scale_mid_shift_periods >= 1 and math.isfinite(fl.scale_stiffness_N_m)
    assert fl.scale_stiffness_N_m > 0.0


def test_psw_only_the_end_read_moved_gives_nan() -> None:
    plain, _ = _toy_probe(gc.ProbeSettings(), stuck_until_s=0.0)
    end_s = plain.results[0].t_first_hold_end_s
    on, _ = _toy_probe(gc.ProbeSettings(scale_mid_min_piston_travel_m=PSW_TRAVEL_M),
                       move_at_s=end_s)
    fl = on.results[0]
    assert math.isfinite(fl.incremental_stiffness_N_m)
    assert fl.scale_mid_shift_periods is None and math.isnan(fl.scale_stiffness_N_m)


def test_psw_rect_profile_keeps_k1() -> None:
    settings = gc.ProbeSettings(profile=gc.ProbeProfile.RECT,
                                scale_mid_min_piston_travel_m=PSW_TRAVEL_M)
    probe, _ = _toy_probe(settings)
    for result in probe.results:
        assert _same(result.scale_stiffness_N_m, result.incremental_stiffness_N_m)


def test_psw_formula_rules() -> None:
    settings = gc.ProbeSettings(scale_mid_min_piston_travel_m=PSW_TRAVEL_M)
    sample = gc.ProbeSample(0, 50e3, 0.3, 0.3, 60e3, 0.302, 0.302, 50e3, 0.3,
                            first_move_mid_force_N=55e3, first_move_mid_rod_stroke_m=0.3,
                            scale_mid_force_N=56e3, scale_mid_rod_stroke_m=0.3008)
    assert gc.psw_scale_stiffness_N_m(sample, settings, 1.0) == pytest.approx(4e3 / 1.2e-3)
    no_mid = replace(sample, first_move_mid_rod_stroke_m=math.nan)
    assert gc.psw_scale_stiffness_N_m(no_mid, settings, 7.0) == 7.0
    short = replace(sample, scale_mid_rod_stroke_m=0.3019)  # 0.1 mm < 0.2 mm
    assert math.isnan(gc.psw_scale_stiffness_N_m(short, settings, 1.0))
    no_scale_mid = replace(sample, scale_mid_rod_stroke_m=math.nan)
    assert math.isnan(gc.psw_scale_stiffness_N_m(no_scale_mid, settings, 1.0))
    with pytest.raises(ValueError):
        gc.ProbeSettings(scale_mid_min_piston_travel_m=0.0)


def _attribute_reads(tree: ast.AST, names: tuple[str, ...]) -> list[str]:
    """Functions (qualified) that read ``.<name>`` for one of ``names``."""
    found = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.stack: list[str] = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_Attribute(self, node: ast.Attribute) -> None:
            if node.attr in names and isinstance(node.ctx, ast.Load):
                found.append(".".join(self.stack) or "<module>")
            self.generic_visit(node)

    Visitor().visit(tree)
    return found


def test_psw_fields_are_read_by_the_scale_update_only() -> None:
    """N-1 premise 2 (static): outside ``ground_contact`` (which makes them) the PSW fields of a
    probe result are read only in ``C2Controller._psw_scale_ratios``, which only
    ``_update_twist_stiffness_scale`` calls; so the PSW reaches the commands only through
    ``state.twist_stiffness_scale``."""
    readers = []
    for folder in (ROOT / "03_src", ROOT / "04_scripts"):
        for path in sorted(folder.rglob("*.py")):
            if path.name == "ground_contact.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            readers += [f"{path.name}:{name}" for name in _attribute_reads(tree, NEW_RESULT_FIELDS)]
    assert readers == ["c2.py:_psw_scale_ratios"] * len(readers) and readers
    tree = ast.parse((ROOT / "03_src" / "outrigger_sim" / "control" / "c2.py").read_text(
        encoding="utf-8"))
    callers = _attribute_reads(tree, ("_psw_scale_ratios",))
    assert callers == ["_update_twist_stiffness_scale"]
    scale_writers = [name for name in _attribute_reads(tree, ("psw_round_legs",))]
    assert set(scale_writers) == {"_record_probe_stiffness"}


@pytest.fixture(scope="module")
def geometry():
    from outrigger_sim.params import load_params

    return c2.C2Geometry.from_params(load_params())


def _results(geometry, ratios, scale_ratios, shifts=None) -> tuple:
    nominal = geometry.load_sensitivity_diag_N_m
    results = []
    for leg, (ratio, scale) in enumerate(zip(ratios, scale_ratios, strict=True)):
        results.append(gc.ProbeResult(
            leg, 50e3, 0.0, ratio * nominal[leg], True, is_grounded_by_stiffness=True,
            scale_stiffness_N_m=scale * nominal[leg],
            scale_mid_shift_periods=(shifts or [0] * 4)[leg], moved_by_mid_m=0.1e-3))
    return tuple(results)


def test_psw_scale_update_and_record(geometry) -> None:
    config = c2.C2Config().with_10hz_d1().with_ed8(dict(c2.ED8_CONTROLLER_SETTINGS))
    controller = c2.C2Controller(geometry, config)
    results = _results(geometry, [2.8, 2.6, 2.9, 2.7], [1.3, 1.2, 0.2, math.nan], [2, 0, 1, None])
    controller._state.probe_round_count += 1
    controller._update_twist_stiffness_scale(results, 5.0)
    controller._record_probe_stiffness(results, 5.0)
    (entry,) = controller.probe_stiffness_record()
    assert entry["scale_leg_count"] == 2  # RL under 0.3 S_ii, RR NaN
    assert entry["raw_ratio"] is None and entry["twist_stiffness_scale"] is None
    assert entry["legs"]["FL"]["is_psw_scale_leg"] is True
    assert entry["legs"]["RL"]["is_psw_scale_leg"] is False
    assert entry["legs"]["FL"]["scale_mid_shift_periods"] == 2
    assert entry["legs"]["RR"]["scale_k_N_m"] is None
    results = _results(geometry, [2.8, 2.6, 2.9, 2.7], [1.3, 1.2, 1.4, 3.7])
    controller._update_twist_stiffness_scale(results, 6.0)
    assert controller._state.twist_stiffness_raw_ratio == pytest.approx(1.35)
    assert controller._state.twist_stiffness_scale == pytest.approx(1.35)
    assert not [e for e in controller.events if e.name.startswith("WARN_PROBE_STIFFNESS")]
    results = _results(geometry, [1.0] * 4, [3.7, 3.7, 3.7, 3.7])
    controller._update_twist_stiffness_scale(results, 7.0)  # above 3.6: the warning
    assert [e.name for e in controller.events][-1].startswith("WARN_PROBE_STIFFNESS")


# ------------------------------------------------------------------------ Y8-2 tags, settings
OLD_TAGS = (
    "final_C4G2", "final_C4G2_LAS", "final_C4G2_LAS_K1", "final_C4G2_P3", "final_C4G2_P3_LAS",
    "final_C4G2_P3_LAS_K1", "final_C4G2_P3_K1", "final_C4G2_P3H_LAS_K1", "final_C4G2_P3W",
    "final_C4G2_P3W_LAS_K1_LSB", "final_C4G2_P3X_LAS_K1_LSB", "final_C4G2_LAS_K1_LSB",
    "final_C4G2_LAS_K1_TCL", "final_C4G2_P3_LAS_K1_TCL", "ABL_LAS_K1", "ABL_LAS",
)
OLD_TAG_TABLE = {  # tag: (switch_base_tag, revision, LSB, K1 gate, LAS, TCL)
    "final_C4G2": ("final_C4G2", None, False, False, False, False),
    "final_C4G2_LAS": ("final_C4G2", None, False, False, True, False),
    "final_C4G2_LAS_K1": ("final_C4G2", None, False, True, True, False),
    "final_C4G2_P3": ("final_C4G2_P3", 4, False, False, False, False),
    "final_C4G2_P3_LAS": ("final_C4G2_P3", 4, False, False, True, False),
    "final_C4G2_P3_LAS_K1": ("final_C4G2_P3", 4, False, True, True, False),
    "final_C4G2_P3_K1": ("final_C4G2_P3", 4, False, True, False, False),
    "final_C4G2_P3H_LAS_K1": ("final_C4G2_P3H", 5, False, True, True, False),
    "final_C4G2_P3W": ("final_C4G2_P3W", 6, False, False, False, False),
    "final_C4G2_P3W_LAS_K1_LSB": ("final_C4G2_P3W", 6, True, True, True, False),
    "final_C4G2_P3X_LAS_K1_LSB": ("final_C4G2_P3X", 7, True, True, True, False),
    "final_C4G2_LAS_K1_LSB": ("final_C4G2", None, True, True, True, False),
    "final_C4G2_LAS_K1_TCL": ("final_C4G2", None, False, True, True, True),
    "final_C4G2_P3_LAS_K1_TCL": ("final_C4G2_P3", 4, False, True, True, True),
    "ABL_LAS_K1": ("ABL", None, False, True, True, False),
    "ABL_LAS": ("ABL", None, False, False, True, False),
}


def _tag_row(tag: str) -> tuple:
    return (v5.switch_base_tag(tag), v5.extend_start_revision_of_tag(tag),
            v5.is_lock_start_b_tag(tag), v5.is_order_gate_tag(tag), v5.is_liftoff_slow_tag(tag),
            v5.is_touch_creep_tag(tag))


def test_old_tags_keep_their_readings() -> None:
    assert set(OLD_TAG_TABLE) == set(OLD_TAGS)
    for tag, expected in OLD_TAG_TABLE.items():
        assert _tag_row(tag) == expected, tag
        assert v5.is_ed8_tag(tag) is False
        assert v5.with_lock_start_b_tag(v5.with_lock_start_b_tag(tag)).count("_LSB") == 1


def test_ed8_tags_of_the_spec_table() -> None:
    vbn, vbn0 = "final_C4G2_P3X_LAS_K1_LSB_ED8", "final_C4G2_LAS_K1_LSB_ED8"
    assert _tag_row(vbn) == ("final_C4G2_P3X", 7, True, True, True, False)
    assert _tag_row(vbn0) == ("final_C4G2", None, True, True, True, False)
    assert v5.is_ed8_tag(vbn) and v5.is_ed8_tag(vbn0)
    assert v5.with_lock_start_b_tag(vbn) == vbn  # no _LSB after _ED8
    assert v5.with_order_gate_tag(vbn) == vbn and v5.with_liftoff_slow_tag(vbn) == vbn
    assert v5.with_touch_creep_tag(vbn) == "final_C4G2_P3X_LAS_K1_LSB_TCL_ED8"
    assert v5.with_ed8_tag("final_C4G2_P3X_LAS_K1_LSB") == vbn
    assert v5.with_ed8_tag(vbn) == vbn


def test_edition_8_settings_and_tags() -> None:
    import run_v5

    names = {"VBN", "VBN0", "VBKN", "VBKN0", *(f"LSN{n}" for n in "1234"),
             *(f"VBN{key}" for key in run_v5.ED7_SENSITIVITY)}
    assert set(run_v5.ED8_SETTINGS) == names
    assert names <= set(run_v5.ALL_SETTINGS) and names <= set(run_v5.T4H_SETTINGS)
    assert {"VBKN", "VBKN0"} <= set(run_v5.ROD_FAULT_SETTINGS)
    assert {key: tuple(value) if isinstance(value, list) else value
            for key, value in run_v5.ED8_CONTROLLER_CHANGES.items()} == dict(
        c2.ED8_CONTROLLER_SETTINGS)
    config = c2.C2Config().with_10hz_d1()
    for name, expected in (("VBN", "final_C4G2_P3X_LAS_K1_LSB_ED8"),
                           ("VBN0", "final_C4G2_LAS_K1_LSB_ED8"),
                           ("LSN2", "final_C4G2_P3X_LAS_K1_LSB_ED8"),
                           ("VBM", "final_C4G2_P3X_LAS_K1_LSB"),
                           ("VBM0", "final_C4G2_LAS_K1_LSB")):
        _, options = run_v5.options_of(name)
        built = v5.apply_controller_options(config, options, V_MAX, 0.1)
        assert v5.controller_tag(options, built) == expected, name
        v5.check_ed8_config(built, options)
        assert v5.HydraulicOptions.from_dict(options.to_dict()) == options
    vbm = run_v5.ED7_SETTINGS["VBM"][1]
    vbn = run_v5.ED8_SETTINGS["VBN"][1]
    assert {k: v for k, v in vbn.items() if k not in ("probe_d6_settings", "ed8_settings")} == {
        k: v for k, v in vbm.items() if k != "probe_d6_settings"}
    assert vbn["probe_d6_settings"] == {"witness": True, "retract_position_target": False,
                                        "witness_mode": "record"}


def test_old_settings_have_no_edition_8_field() -> None:
    import run_v5

    for name, (_, options) in run_v5.ALL_SETTINGS.items():
        if name in run_v5.ED8_SETTINGS:
            continue
        built = run_v5.options_of(name)[1]
        assert "ed8_settings" not in options and "witness_mode" not in (
            options.get("probe_d6_settings") or {}), name
        if built is not None:
            assert "ed8_settings" not in built.to_dict(), name
    preset = c2.C2Config().with_10hz_d1()
    assert preset.has_ed8_changes is False and c2.C2Config().has_ed8_changes is False
    assert c2.R8_D1_SETTINGS.lifted_reapproach.short_run_s is None
    assert preset.twist_completion_relax.locked_drift_waiver is False
    assert preset.probe.scale_mid_min_piston_travel_m is None
    assert gc.ProbeD6Settings(witness=True).to_meta() == {
        "witness": True, "witness_m": 0.3e-3, "not_opened_warn_rounds": 2,
        "retract_position_target": False, "retract_slow_speed_m_s": 1.0e-3,
        "retract_extra_margin_m": 0.2e-3, "head_reading_margin_Pa": 9.0e5}


def test_with_ed8_and_the_identity_guard() -> None:
    preset = c2.C2Config().with_10hz_d1()
    config = preset.with_ed8(dict(c2.ED8_CONTROLLER_SETTINGS))
    assert config.probe.scale_mid_min_piston_travel_m == PSW_TRAVEL_M
    assert config.r8.stiffness_warning_range == (0.8, 3.6)
    assert config.r8.lifted_reapproach.short_run_s == 0.5
    assert config.r8.lifted_reapproach.short_run_exit_samples == 4
    assert config.twist_completion_relax.locked_drift_waiver is True
    assert config.twist_completion_relax.waiver_max_rise_N == 2500.0
    assert config.twist_completion_relax.waiver_margin_N == 500.0
    assert config.has_ed8_changes and v5.is_ed8_on(config)
    with pytest.raises(ValueError):
        preset.with_ed8({"psw": 1.0})
    with pytest.raises(ValueError):
        preset.with_ed8({"short_run_s": 0.5, "short_run_exit_samples": 2})
    options = v5.HydraulicOptions(ed8_settings=(("short_run_s", 0.5),))
    with pytest.raises(RuntimeError):
        v5.check_ed8_config(preset, options)
    with pytest.raises(RuntimeError):
        v5.check_ed8_config(config, v5.HydraulicOptions())
    with pytest.raises(ValueError):
        v5.HydraulicOptions(ed8_settings=(("unknown", 1),))


# ------------------------------------------------------------------------ Y8-3 R2 witness
class _Result:
    def __init__(self, leg: int, witness: float | None) -> None:
        self.leg_index, self.is_skipped, self.is_reversed = leg, False, False
        self.t_first_hold_end_s, self.t_second_hold_end_s = 1.0, 2.0
        self.retract_witness_m = witness
        self.retract_extra_m = self.retract_extra_periods = self.retract_target_reached = None
        self.k1_mid_opened = None


def _monitor(rise_Pa: float) -> TwoPressureMonitor:
    monitor = TwoPressureMonitor(np.full(4, 0.0133), np.full(4, 0.0038), V_MAX, F_MIN, T)
    monitor._history.append((1.0, np.full(4, 5e5), np.full(4, 80e5)))
    monitor._history.append((2.0, np.full(4, 5e5 + rise_Pa), np.full(4, 80e5)))
    return monitor


def test_r2_witness_record_judges_as_edition_6_and_raises_no_witness_event() -> None:
    record_only = D6Witness(witness_m=0.3e-3, warn_rounds=2, is_record_only=True)
    plain, recorded = _monitor(0.0), _monitor(0.0)
    for witness in (None, 0.1e-3):
        plain.probe_round_finished([_Result(0, witness)])
        recorded.probe_round_finished([_Result(0, witness)], record_only)
    assert [n for n, _ in plain._events] == [n for n, _ in recorded._events]
    assert "WARN_ROD_PRESSURE_FALLBACK:FL" in [n for n, _ in recorded._events]
    names = [n for n, _ in recorded._events]
    assert not [n for n in names if n.startswith(("INFO_D6_NOT_OPENED",
                                                    "WARN_PROBE_RETRACT_NOT_OPENED"))]
    log = recorded.meta()["d6_witness"]
    assert log["not_opened_rounds"][0] == 2 and log["would_warn"][0] is True
    assert len(log["rounds"]) == 2 and log["rounds"][0]["witness_mode"] == "record"
    with pytest.raises(ValueError):
        gc.ProbeD6Settings(witness=False, retract_position_target=True, witness_mode="record")
    assert gc.ProbeD6Settings(witness=True, witness_mode="record").to_meta()[
        "witness_mode"] == "record"


# ------------------------------------------------------------------------ Y8-7 / Y8-8 H3'
def _reapproach_controller(geometry, *, h3: bool):
    config = c2.C2Config().with_10hz_d1()
    if h3:
        config = config.with_ed8({"short_run_s": 0.5, "short_run_exit_samples": 4})
    return c2.C2Controller(geometry, config)


def _end_time(geometry, start_s: float, highs: tuple[float, ...], *, h3: bool,
              is_retrigger: bool = False, t_last: float = 1.2):
    controller = _reapproach_controller(geometry, h3=h3)
    settings = controller.config.r8.lifted_reapproach
    run = c2._Reapproach(1, start_s, 0.0, settings.mode, is_retrigger=is_retrigger)
    controller._state.active_reapproaches = {1: run}
    t = round(start_s + 0.1, 6)
    while t <= t_last + 1e-9 and controller._state.active_reapproaches:
        loads = np.full(4, 50e3)
        loads[2] = -3e3  # the diagonal leg RL at the handover
        loads[1] = 50e3 if any(abs(t - h) < 1e-6 for h in highs) else 0.0
        reading = SimpleNamespace(t_s=t, motor_stroke_m=np.zeros(4))
        controller._end_finished_reapproaches(reading, loads, settings)
        t = round(t + 0.1, 6)
    return (None if controller._state.active_reapproaches else run.end_s), run


@pytest.mark.parametrize("start, highs, h3_end, plain_end", [
    (0.1, (0.2, 0.3, 0.4, 0.5), 0.5, 0.4),  # a short first run: 3 -> 4 samples
    (0.1, (0.2, 0.3, 0.4), None, 0.4),  # the fourth sample low: it goes on
    (0.1, (0.4, 0.5, 0.6), None, 0.6),  # exactly T_r after the start: 4 samples
    (0.1, (0.4, 0.5, 0.6, 0.7), 0.7, 0.6),
    (0.1, (0.7, 0.8, 0.9), 0.9, 0.9),  # after T_r: 3 samples
    (0.075, (0.775, 0.875, 0.975), 0.975, 0.975),  # the late handover is unchanged
])
def test_h3_prime_exit_samples(geometry, start, highs, h3_end, plain_end) -> None:
    end, _ = _end_time(geometry, start, highs, h3=True)
    assert _same(end, h3_end)
    plain, plain_run = _end_time(geometry, start, highs, h3=False)
    assert _same(plain, plain_end)
    assert plain_run.exit_required_samples is None  # H3' off: no record


def test_h3_prime_re_trigger_runs_end_on_three(geometry) -> None:
    end, run = _end_time(geometry, 0.1, (0.2, 0.3, 0.4), h3=True, is_retrigger=True)
    assert end == pytest.approx(0.4) and run.exit_required_samples == 3
    assert run.short_run_extended is False


def test_h3_prime_record(geometry) -> None:
    end, run = _end_time(geometry, 0.1, (0.2, 0.3, 0.4, 0.5), h3=True)
    assert end == pytest.approx(0.5)
    assert run.short_run_extended is True and run.ordinary_end_s == pytest.approx(0.4)
    assert run.exit_required_samples == 4 and run.handover_diagonal_load_N == -3e3
    meta = run.to_meta()
    assert {"exit_required_samples", "short_run_extended", "ordinary_end_s",
            "handover_diagonal_load_N"} <= set(meta)
    _, plain_run = _end_time(geometry, 0.1, (0.2, 0.3, 0.4), h3=False)
    assert "exit_required_samples" not in plain_run.to_meta()


def test_h3_prime_settings_check() -> None:
    settings = c2.LiftedReapproachSettings(short_run_s=0.5, short_run_exit_samples=4)
    assert settings.exit_samples_of(0.6, 0.1, False) == 4
    assert settings.exit_samples_of(0.6 + 1e-6, 0.1, False) == 3
    assert settings.exit_samples_of(0.3, 0.1, True) == 3
    assert c2.LiftedReapproachSettings().exit_samples_of(0.2, 0.1, False) == 3
    with pytest.raises(ValueError):
        c2.LiftedReapproachSettings(short_run_s=0.0)
    with pytest.raises(ValueError):
        c2.LiftedReapproachSettings(short_run_s=0.5, short_run_exit_samples=2)


# ------------------------------------------------------------------------ Y8-10 L-2
def _waiver_controller(geometry, *, waiver: bool = True):
    config = c2.C2Config().with_10hz_d1().with_lock_start_b(("A_i", "A_ib", "A_ii", "B3"))
    if waiver:
        config = config.with_ed8({"locked_drift_waiver": True})
    controller = c2.C2Controller(geometry, config)
    controller._lock_start_b_state()
    return controller


def _history(start_N: float, rise_N: float, end_N: float) -> deque:
    times = [round(0.1 * k, 6) for k in range(51)]
    values = [start_N] * 50 + [end_N]
    values[25] = start_N + rise_N
    return deque(zip(times, values, strict=True))


@pytest.mark.parametrize("counts, start, rise, end, expected", [
    ([50, 0, 0, 0], 7e3, 2500.0, 8e3, True),  # rise = 2.5 kN: waived
    ([50, 0, 0, 0], 7e3, 2500.1, 8e3, False),
    ([49, 0, 0, 0], 7e3, 1000.0, 8e3, False),  # n_still one period short
    ([0, 0, 0, 50], 14e3, 0.0, 14.5e3, True),  # |D| + 0.5 kN = 15 kN
    ([0, 0, 0, 50], 14e3, 0.0, 14.5e3 + 1.0, False),
])
def test_l2_waiver_limits(geometry, counts, start, rise, end, expected) -> None:
    controller = _waiver_controller(geometry)
    controller._state.lock_start_b.still_periods = list(counts)
    assert controller._is_locked_drift_waived(_history(start, rise, end)) is expected
    waivers = controller.twist_waiver_record()
    assert waivers["n_waiver_periods"] == int(expected)
    if expected:
        assert waivers["waiver_periods"][0]["legs"] == [
            c2.LEG_ORDER[leg] for leg, count in enumerate(counts) if count >= 50]


def test_l2_waived_relax_done_is_recorded(geometry) -> None:
    controller = _waiver_controller(geometry)
    controller._state.lock_start_b.still_periods = [50, 0, 0, 0]
    controller._is_locked_drift_waived(_history(7e3, 1000.0, 8e3))
    controller._report_twist_relaxed_done(30.0, 8e3)
    record = controller.twist_waiver_record()
    assert record["n_waiver_done"] == 1 and record["waivers"][0]["done_t_s"] == 30.0
    assert [e.name for e in controller.events] == ["INFO_TWIST_UNSETTLED:8.0"]
    assert set(controller._twist_relax_meta()) >= {"n_waiver_done", "waivers"}
    plain = _waiver_controller(geometry, waiver=False)
    assert "n_waiver_done" not in plain._twist_relax_meta()


GEOMETRY = CylinderGeometry(head_area_m2=np.full(4, 0.0133), annulus_area_m2=np.full(4, 0.0038),
                            stroke_max_m=0.70, max_speed_m_s=V_MAX, period_s=T,
                            increment_limit_m_s=0.25 * V_MAX)


def _floor_inputs(t_s: float, command: np.ndarray, *, is_level: bool = True) -> FloorInputs:
    loads = np.full(4, 80e3)
    return FloorInputs(t_s=t_s, is_level=is_level, is_fill_phase=True, is_fault=False,
                       requested_m_s=command, acting_m_s=command, previous_output_m_s=command,
                       stroke_m=np.full(4, 0.4), head_Pa=np.full(4, 80e5),
                       rod_Pa=np.full(4, 5e5), protected=np.zeros(4, bool),
                       fallback_legs=frozenset(), completion=None, twist_load_N=0.0,
                       twist_limit_N=15.0e3, lower_load_N=loads, force_N=loads + 5e3,
                       F_min_N=F_MIN, twist_vector=np.array([0.4761, -0.4761, -0.5228, 0.5228]))


def test_still_count_follows_the_floors_and_resets_outside_level() -> None:
    rule = LockStartB(LockStartBSettings(components=("A_ib",), ib_blind_periods=1000), GEOMETRY)
    rule.counts_still_periods = True
    command = np.array([0.1e-3, 0.0, 0.0, 0.0])  # inside the dead band: an A(i)-b stretch
    counts = []
    for k in range(10):
        rule.apply_floors(_floor_inputs(k * T, command))
        counts.append(rule.still_periods[0])
    skip = rule.settings.ib_reference_skip_reads
    first = skip + 3  # the period whose stretch has skip + 3 reads
    assert counts == [0] * (first - 1) + list(range(1, 11 - first + 1))
    rule.apply_floors(_floor_inputs(10 * T, command, is_level=False))
    assert rule.still_periods[0] == 0
    off = LockStartB(LockStartBSettings(components=("A_ib",)), GEOMETRY)
    off.apply_floors(_floor_inputs(0.0, command))
    assert off.still_periods == [0, 0, 0, 0]


# ------------------------------------------------------------------------ Y8-9 EventTwin
def test_event_twin_depth_and_ramp() -> None:
    import run_v5
    import verdict_cases
    import verdict_runs

    twin = verdict_cases.EventTwin(None, None, "RE1bF", "FR", "ready", 0.0125, 3.0,
                                   level="bottom", depth_m=0.025, ramp_s=0.05)
    events = {"RE1bF": {"depth": 0.030, "ramp": 0.05}}
    assert verdict_runs.event_shape(twin, events) == {"depth": 0.025, "ramp": 0.05}
    plain = replace(twin, depth_m=None, ramp_s=None)
    assert verdict_runs.event_shape(plain, events) is events["RE1bF"]
    with pytest.raises(ValueError):
        replace(twin, ramp_s=None)
    job = {"case": "R12", "eps": 0.0, "offset_s": 0.0125, "setting": "VBN",
           "twin": {"level": "bottom", "leg": "FR", "fs_kN": 3.0, "event": "RE1bF",
                    "timing": "ready", "depth_m": 0.025, "ramp_s": 0.05}}
    assert run_v5.t4h_file_name(job) == (
        "R12_bottom-FR-Fs3-o0.0125-RE1bF-ready-d0.025-r0.05_VBN.npz")
    old = {**job, "twin": {k: v for k, v in job["twin"].items() if k not in ("depth_m", "ramp_s")}}
    assert run_v5.t4h_file_name(old) == "R12_bottom-FR-Fs3-o0.0125-RE1bF-ready_VBN.npz"
    case, _ = run_v5._case_of(job)
    assert case.twin.depth_m == 0.025 and case.twin.ramp_s == 0.05


# ------------------------------------------------------------------------ Y8-6 layer rule
@pytest.mark.parametrize("job, starts, expected", [
    ({"case": "R16", "eps": 0.0, "offset_s": 0.0}, [[0.3, "RR"]], "E"),  # default RE1bF FL
    ({"case": "R12", "eps": 0.0, "offset_s": 0.0}, [[0.3, "FL"]], "N"),  # default G4 RR
    ({"case": "R12", "eps": 0.0, "offset_s": 0.0,
      "twin": {"level": "bottom", "leg": "FR", "fs_kN": 0.0, "event": "RE1bF",
               "timing": "ready"}}, [[0.45, "RL"]], "E"),
    ({"case": "R12", "eps": 0.0, "offset_s": 0.0,
      "twin": {"level": "bottom", "leg": "FR", "fs_kN": 0.0, "event": "RE1bF",
               "timing": "ready"}}, [[0.46, "RL"], [-0.1, "RL"], [0.2, "FR"]], "N"),
    ({"case": "R12", "eps": 0.0, "offset_s": 0.0,
      "twin": {"level": "bottom", "leg": "FR", "fs_kN": 0.0, "event": "FS24",
               "timing": "ready"}}, [[0.3, "RL"]], "N"),  # FS24 is no E candidate
    ({"case": "R12", "eps": 0.0, "offset_s": 0.0,
      "twin": {"level": "bottom", "leg": "FR", "fs_kN": 0.0, "event": "RE1bF", "timing": "ready",
               "depth_m": 0.025, "ramp_s": 0.05}}, [[0.0, "RL"]], "E"),  # a shape variant
    ({"case": "R14", "eps": 0.0, "offset_s": 0.0}, [], "N"),  # an empty list
    ({"case": "S8", "eps": 0.0}, None, "N"),  # a steady row needs no key
    ({"case": "R12", "eps": 0.0, "offset_s": 0.0,
      "twin": {"level": "top", "leg": "FR", "fs_kN": 0.0}}, None, "N"),  # G4: no key needed
])
def test_layer_rule(job, starts, expected) -> None:
    import ed8_key_lists as keys

    assert keys.stratum_of(job, starts) == expected


def test_layer_rule_defects_and_the_fast_field() -> None:
    import ed8_key_lists as keys

    with pytest.raises(keys.LayerInputError):
        keys.stratum_of({"case": "R15", "eps": 0.0, "offset_s": 0.0}, None)
    with pytest.raises(keys.LayerInputError):
        keys.stratum_of({"case": "R13", "eps": 0.0}, [])
    line = {"event_output": {"fast": True, "reapproach_starts": [[0.6, "RR"]]}}
    assert keys.stratum_of({"case": "R16", "eps": 0.0}, keys.main_line_starts(line)) == "N"
    assert keys.main_line_starts({"event_output": {}}) is None
    grid = {"results": [{"key": "k", "runs": [{"commands_sha256": "a"},
                                               {"commands_sha256": "b",
                                                "reapproach_starts": [[0.3, "RL"]]}]}]}
    assert keys.grid_run_starts(grid, {"key": "k", "run_id": "1",
                                       "v0_commands_sha256": "b"}) == [[0.3, "RL"]]
    with pytest.raises(keys.LayerInputError):
        keys.grid_run_starts(grid, {"key": "k", "run_id": 1, "v0_commands_sha256": "a"})
    found = keys.event_of_job({"case": "R12", "twin": {"leg": "FL"}})
    assert (found.event, found.leg, found.event_source, found.leg_source) == (
        "G4", "FL", "default", "twin")


# ------------------------------------------------------------------------ Y8-6 key files
def _sources_present() -> bool:
    import ed8_key_lists as keys

    return all((RECORDS_ROOT / path).exists() for path, _ in (
        keys.J9_MAIN, keys.SENS_KEYS, keys.G1_KEYS, keys.GRID192_KEYS))


@pytest.fixture(scope="module")
def key_sources():
    import ed8_key_lists as keys

    if not _sources_present():
        pytest.skip(f"the key-file sources are not under {RECORDS_ROOT} (OUTRIGGER_RECORDS_ROOT)")
    return keys.read_census_sources(RECORDS_ROOT)


def test_census_keys_are_deterministic_and_complete(key_sources) -> None:
    import ed8_key_lists as keys

    first = keys.document_bytes(keys.census_document(key_sources))
    second = keys.document_bytes(keys.census_document(key_sources))
    assert first == second
    document = json.loads(first)
    lines = document["lines"]
    assert len(lines) == document["expected_lines"] == 1043
    stages = [line["stage"] for line in lines]
    assert [stages.count(name) for name in ("C-J", "C-S", "C-D", "C-G")] == [388, 460, 24, 171]
    settings = {line["job"]["setting"] for line in lines}
    assert settings <= {"VBN", "VBNslow", *(f"LSN{n}" for n in "1234"),
                        *(f"VBN{key}" for key in ("fast", "c005", "c04", "b069", "b16",
                                                  "h05", "h15", "d05", "d15"))}
    keys_of_lines = [json.dumps(line["job"], sort_keys=True) for line in lines]
    assert len(set(keys_of_lines)) == 1043
    resolution = document["event_resolution"]
    assert all(counts.get("kind:unresolved", 0) == 0 for counts in resolution.values())
    assert not [line for line in lines if {"mask", "t4h_dir"} & set(line["job"])]


def test_heldout_keys_are_deterministic(key_sources) -> None:
    import ed8_key_lists as keys

    first = keys.document_bytes(keys.heldout_document(RECORDS_ROOT, key_sources))
    second = keys.document_bytes(keys.heldout_document(RECORDS_ROOT, key_sources))
    assert first == second
    document = json.loads(first)
    lines = document["lines"]
    assert len(lines) == 339 and document["seed"] == 20261127
    counts = {name: sum(line["source"] == name for line in lines)
              for name in ("a_phase", "b_shape", "c_fs")}
    assert counts == {"a_phase": 171, "b_shape": 48, "c_fs": 120}
    assert [(line["source"], line["slot"]) for line in lines] == sorted(
        (line["source"], line["slot"]) for line in lines)
    for line in lines:
        assert line["job"]["setting"] == "VBN" and line["v0_pair"]["job"]["setting"] == "V0"
        offset = line["job"]["offset_s"]
        if line["source"] == "a_phase":
            assert offset in keys.NEW_PHASES_S and len(line["aa_order"]) == 3
        elif line["source"] == "b_shape":
            assert line["job"]["twin"]["event"] == "RE1bF"
            assert "depth_m" in line["job"]["twin"] and len(line["aa_order"]) == 15
        else:
            assert line["job"]["twin"]["fs_kN"] in (1.0, 3.0, 6.0)
    other_seed = keys.heldout_slots(keys.heldout_frames(
        keys.stored_cluster_passes(RECORDS_ROOT, key_sources.grid192_lines)), seed=1)
    assert [line["job"] for line in other_seed] != [line["job"] for line in lines]


def test_edition_8_batches(key_sources, tmp_path: Path, monkeypatch) -> None:
    import hashlib

    import ed8_key_lists as keys
    import run_v5

    census = tmp_path / "census_keys_ed8.json"
    census.write_bytes(keys.document_bytes(keys.census_document(key_sources)))
    heldout = tmp_path / "heldout_g_ed8.json"
    heldout.write_bytes(keys.document_bytes(keys.heldout_document(RECORDS_ROOT, key_sources)))
    monkeypatch.setattr(run_v5, "ED8_KEYS_FILE", [census])
    with pytest.raises(SystemExit):  # the table is empty until C8
        run_v5.batch_jobs(run_v5.ED8_KEYS_BATCH)
    monkeypatch.setattr(run_v5, "ED8_KEY_FILE_SHA256", {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (census, heldout)})
    assert len(run_v5.batch_jobs(run_v5.ED8_KEYS_BATCH)) == 1043
    with pytest.raises(SystemExit):  # the census file is no held-out file
        run_v5.batch_jobs(run_v5.ED8_HELDOUT_V0_BATCH)
    monkeypatch.setattr(run_v5, "ED8_KEYS_FILE", [heldout])
    vbn = run_v5.batch_jobs(run_v5.ED8_KEYS_BATCH)
    v0 = run_v5.batch_jobs(run_v5.ED8_HELDOUT_V0_BATCH)
    aa2 = run_v5.batch_jobs("ed8_heldout_aa2")
    assert (len(vbn), len(v0), len(aa2)) == (339, 678, 339)
    assert {job["setting"] for job in vbn} == {"VBN"}
    assert {job["setting"] for job in v0 + aa2} == {"V0"}
    assert len({run_v5.job_key(job) for job in v0}) == 678
    main_jsonl = RECORDS_ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "main.jsonl"
    if main_jsonl.exists():  # the stored V0 / VB lines (git excluded): P8-1 reads its 22 jobs
        monkeypatch.setattr(run_v5, "P3_HASH_SOURCE_OVERRIDE", [main_jsonl])
        t8 = run_v5.batch_jobs(run_v5.ED8_T8_BATCH)
        assert len(t8) == 44 and {job["setting"] for job in t8} == {"VBN", "VBN0"}
    cases = run_v5.batch_jobs(run_v5.ED8_CASES_BATCH)
    assert len(cases) == 10 and {job["setting"] for job in cases} == set(
        run_v5.ED8_JUDGED_SETTINGS)


# ------------------------------------------------------------------------ old settings
def test_old_settings_run_no_new_line(monkeypatch, geometry) -> None:
    """P8-0 premise: with every new field at its default the PSW, H3' record, L-2 count / waiver
    and Y8-4 record helpers are never called."""

    def forbidden(*args, **kwargs):
        raise AssertionError("an edition 8 line ran on an old setting")

    for owner, name in ((gc.ProbeRound, "_note_scale_mid"), (gc.ProbeRound, "_psw_fields"),
                        (c2.C2Controller, "_note_exit_test"),
                        (c2.C2Controller, "_is_locked_drift_waived"),
                        (c2.C2Controller, "_note_completion_trace"),
                        (c2.C2Controller, "_psw_scale_ratios"),
                        (LockStartB, "_count_still_periods")):
        monkeypatch.setattr(owner, name, forbidden)
    monkeypatch.setattr(gc, "psw_scale_stiffness_N_m", forbidden)
    _toy_probe(gc.ProbeSettings(), stuck_until_s=0.65)
    _end_time(geometry, 0.1, (0.2, 0.3, 0.4), h3=False)
    controller = _waiver_controller(geometry, waiver=False)
    controller._state.lock_start_b.apply_floors(_floor_inputs(0.0, np.full(4, 0.1e-3)))
    results = _results(geometry, [1.2] * 4, [1.2] * 4)
    controller._update_twist_stiffness_scale(results, 1.0)


# ------------------------------------------------------------------------ ed8_probe arms
def test_probe_arms_of_the_spec() -> None:
    import ed8_probe as probe
    import run_v5

    settings = probe.probe_settings()
    b_impl = settings["P8-M-B_impl"][1]
    a2w = settings["P8-M-a2w"][1]
    assert {k: v for k, v in b_impl.items() if k != "ed8_settings"} == a2w
    assert b_impl["ed8_settings"] == {"short_run_exit_samples": 4, "short_run_s": 0.5}
    l2 = settings["P8-M-L2_impl"][1]
    assert l2["ed8_settings"] == {**b_impl["ed8_settings"], "locked_drift_waiver": True}
    assert settings["P8-M-a8"][1] == run_v5.ED8_SETTINGS["VBN"][1]
    assert settings["P8-LSM4-a8"][1] == run_v5.ED8_SETTINGS["LSN4"][1]
    assert settings["P8-Mslow-a8"][1] == run_v5.ED8_SETTINGS["VBNslow"][1]
    assert settings["P8-KM0-a8"][1] == run_v5.ED8_SETTINGS["VBKN0"][1]
    km0 = settings["P8-KM0-B_impl"][1]
    vbkm0 = run_v5.ED7_SETTINGS["VBKM0"][1]
    assert {k: v for k, v in km0.items() if k not in ("ed8_settings", "probe_d6_settings")} == {
        k: v for k, v in vbkm0.items() if k != "probe_d6_settings"}
    for arm, missing in (("a8_psw_off", "psw_min_travel_m"), ("a8_h3_off", "short_run_s"),
                         ("a8_l2_off", "locked_drift_waiver")):
        changes = settings[f"P8-M-{arm}"][1]["ed8_settings"]
        assert missing not in changes and len(changes) < len(run_v5.ED8_CONTROLLER_CHANGES)


def test_probe_part_p816_plan(tmp_path: Path) -> None:
    import ed8_probe as probe

    jobs = probe.probe_jobs(("p816",), probe.PLANTS, ("B_impl", "L2_impl"))
    assert len(jobs) == 54
    r79 = [job for job in jobs if "r79_key" in job]
    assert len(r79) == 8 and {job["setting"] for job in r79} == {"P8-KM0-B_impl",
                                                                  "P8-KM0-L2_impl"}
    plan = tmp_path / "plan.json"
    plan.write_text("{}", encoding="utf-8")
    args = probe._parser().parse_args(["--out", str(tmp_path / "o.jsonl"), "--part", "p816",
                                       "--arms", "B_impl,L2_impl", "--r79-plan", str(plan)])
    with pytest.raises(ValueError, match="sha256"):
        probe._selection(args)
    args = probe._parser().parse_args(["--out", str(tmp_path / "o.jsonl"), "--part", "p816",
                                       "--arms", "B_impl"])
    with pytest.raises(ValueError, match="--r79-plan"):
        probe._selection(args)
    default = probe._parser().parse_args(["--out", str(tmp_path / "o.jsonl"), "--part", "main"])
    plan_jobs, _ = probe._selection(default)
    assert not [job for job in plan_jobs if job["setting"].startswith("P8-KM0-")]


# ------------------------------------------------------------------------ p816_compare
def _reference_lines() -> list[dict]:
    import ed8_probe as probe

    plant_of = {"M": "VBM", "LSM4": "LSM4", "Mslow": "VBMslow"}
    lines = []
    for arm in ("B", "L2", "L1"):
        for index, (plant, row) in enumerate(probe.P816_V5_ROWS):
            lines.append({"p814_job": {**row, "setting": f"P814-{arm}-{plant_of[plant]}"},
                          "commands_sha256": f"{arm}{index}"})
        for index, key in enumerate(probe.P816_R79_KEYS):
            lines.append({"p814_job": {"r79_key": key, "setting": f"P814-{arm}-VBKM0"},
                          "commands_sha256": f"{arm}r{index}"})
    return lines


def _run_lines(reference: list[dict]) -> list[dict]:
    arm_of = {"B": "B_impl", "L2": "L2_impl"}
    plant_of = {"VBM": "M", "LSM4": "LSM4", "VBMslow": "Mslow", "VBKM0": "KM0"}
    lines = []
    for line in reference:
        _, arm, plant = line["p814_job"]["setting"].split("-")
        if arm not in arm_of:
            continue
        job = {**line["p814_job"], "setting": f"P8-{plant_of[plant]}-{arm_of[arm]}"}
        lines.append({"job": job, "commands_sha256": line["commands_sha256"],
                      "ed8_probe": {"arm": arm_of[arm], "plant": plant_of[plant]}})
    return lines


def _write_jsonl(path: Path, lines: list[dict]) -> None:
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")


def test_p816_compare_from_another_folder(tmp_path: Path, monkeypatch, capsys) -> None:
    import hashlib

    import p816_compare

    data = tmp_path / "data"
    data.mkdir()
    reference = _reference_lines()
    _write_jsonl(data / "runs.jsonl", reference)
    monkeypatch.setattr(p816_compare, "REFERENCE_SHA256",
                        hashlib.sha256((data / "runs.jsonl").read_bytes()).hexdigest())
    work = tmp_path / "elsewhere"
    work.mkdir()
    monkeypatch.chdir(work)
    run = _run_lines(reference)

    def compare(lines: list[dict], name: str) -> tuple[int, dict]:
        _write_jsonl(data / f"{name}.jsonl", lines)
        code = p816_compare.main(["--reference", str(data / "runs.jsonl"),
                                  "--run", str(data / f"{name}.jsonl"),
                                  "--out", str(data / f"{name}.json")])
        last = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        return code, last

    code, last = compare(run, "pass2")
    assert code == 0 and last["status"] == "pass" and last["equal"] == 54
    changed = [dict(line) for line in run]
    changed[0] = {**changed[0], "commands_sha256": "other"}
    code, last = compare(changed, "differ")
    assert code == 1 and last["equal"] == 53
    code, last = compare(run[1:], "missing")
    assert code == 1 and last["counts"]["B_impl"].get("missing") == 1
    errored = [dict(line) for line in run]
    errored[5] = {"job": errored[5]["job"], "error": "x", "ed8_probe": errored[5]["ed8_probe"]}
    code, last = compare(errored, "error")
    assert code == 1
    extra = [*run, {"job": {"case": "S1", "eps": 0.0, "setting": "P8-M-B_impl"},
                    "commands_sha256": "x", "ed8_probe": {"arm": "B_impl", "plant": "M"}}]
    code, last = compare(extra, "extra")
    assert code == 1 and last["extra_run_keys"] == 1
    code, last = compare(run, "pass2")  # an existing --out is refused
    assert code == 2 and last["status"] == "input_error"
    monkeypatch.setattr(p816_compare, "REFERENCE_SHA256", "0" * 64)
    code, last = compare(run, "badref")
    assert code == 2
