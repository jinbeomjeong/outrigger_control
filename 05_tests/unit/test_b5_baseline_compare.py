"""B5 baseline comparison (``04_scripts/03_control/s9/b5_baseline_compare.py``): the C2 command
hash against the R2DS acceptance records, the ABL switches of the final controller (SGS and R4
off, spec 429.11), the IND wrapper (output delay d = 1, increment limit 0.25 v_max per period)
and the rigid-floor-only floor-drop event.

The hash checks run the reduced harness in a subprocess (numba, dynamics-dev; about 30 s each).
``A1-rigid`` runs by default; the soil cases are marked ``slow``:
``python.exe -I -m pytest 05_tests/unit/test_b5_baseline_compare.py -m slow``.
"""

from __future__ import annotations

import functools
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.control import c2, c8
from outrigger_sim.params import load_params
from outrigger_sim.signals import Measurements

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "04_scripts" / "03_control" / "s9" / "b5_baseline_compare.py"
sys.path.insert(0, str(SCRIPT.parent))
PRE_SWITCH_RUNNER = Path(__file__).with_name("pre_switch_preset_runner.py")

import b5_baseline_compare as b5  # noqa: E402
import b5_official as official  # noqa: E402
import b5_oos_cases as oos  # noqa: E402

GRAVITY_M_S2 = 9.80665
OOS_BATCH_SIZES = {"T1": 28, "T2": 9, "T3": 12, "T4": 8, "T5": 12, "T6": 6, "T7": 12, "T8": 4,
                   "T9": 4, "T10": 5}
SCRIPT_TIMEOUT_S = 600
HARNESS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
"""The stored hashes are dynamics-dev values: Chrono-dev's numpy / numba builds differ in the
last bits, so the harness always runs in dynamics-dev, whatever env runs pytest."""
R2DS_C2_HASHES = {
    # rev83/R2DS_slope.json, candidate "current"
    "A1-rigid": "a91e95796d41e1a06dd5513b1a191bbd0b5bb12e5cfa50e9df8feafebb27820f",
    "A1-J1": "58f77b7b7420e275c99bbf2abca49f7d4d3f72efc448a948ff468ca7b2d033d0",
    # rev83/R2DS_g6.json, g6|G1+J1@RR|top|Fs4, candidate "current"
    "A3-G1+J1@RR": "69288ee341a21bb170add6bdcd63e6106f2014316d3fa976b1a7362eb2cfd551",
}


# ------------------------------------------------------------------------------ C2 hashes
def _run_b5(case_id: str, out_path: Path) -> dict:
    environment = dict(os.environ, MKL_THREADING_LAYER="TBB", PYTHONDONTWRITEBYTECODE="1")
    completed = subprocess.run(
        # R2DS hashes predate the spec 429.11 preset switch: run with SGS and R4 off.
        [str(HARNESS_PYTHON), "-I", str(PRE_SWITCH_RUNNER), str(SCRIPT), "run",
         "--cases", case_id, "--controllers", "C2",
         "--workers", "1", "--out", str(out_path)],
        cwd=ROOT, env=environment, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=SCRIPT_TIMEOUT_S, check=False)
    assert completed.returncode == 0, completed.stderr[-3000:]
    (record,) = json.loads(out_path.read_text(encoding="utf-8"))["records"]
    return record


@pytest.mark.parametrize("case_id", [
    "A1-rigid",
    pytest.param("A1-J1", marks=pytest.mark.slow),
    pytest.param("A3-G1+J1@RR", marks=pytest.mark.slow),
])
def test_c2_command_hash_matches_r2ds(case_id: str, tmp_path: Path) -> None:
    if not HARNESS_PYTHON.exists():
        pytest.skip(f"dynamics-dev missing ({HARNESS_PYTHON})")
    record = _run_b5(case_id, tmp_path / "b5.json")
    assert "error" not in record, record.get("tb")
    assert record["commands_sha256"] == R2DS_C2_HASHES[case_id]


# ---------------------------------------------------------------- ABL final-controller switches
FINAL_FLAT_SOIL_MARGIN_M = 0.03
"""R4c30 (spec 429.11): the preset value after the B1 switch."""


class _FinalPresetHarness:
    """Stand-in for the harness module ``cl``: ``preset_config`` with SGS and R4 on, as the R8
    preset will be after the spec 429.11 switch."""

    @staticmethod
    def preset_config(contact, with_imu_samples, with_reapproach=True):
        del contact, with_imu_samples, with_reapproach
        return c2.C2Config().with_10hz_d1(soil_stop=True,
                                          flat_soil_margin_m=FINAL_FLAT_SOIL_MARGIN_M)


def _switches(config) -> tuple[bool, float]:
    return (config.lift_stroke_guard.soil_stop,
            config.slope_clearance_margin.flat_soil_margin_m)


def test_ablation_turns_sgs_and_r4_off() -> None:
    config = c2.C2Config().with_10hz_d1()
    assert _switches(b5.ablation_config(c2, config)) == (False, 0.0)


def test_ablation_turns_sgs_and_r4_off_on_the_final_preset() -> None:
    final = _FinalPresetHarness.preset_config(None, True)
    assert _switches(final) == (True, FINAL_FLAT_SOIL_MARGIN_M)
    assert _switches(b5.ablation_config(c2, final)) == (False, 0.0)
    for name in ("ABL", "ABL28"):
        config = b5._c2_config(_FinalPresetHarness, c2, name, {})
        assert _switches(config) == (False, 0.0), name
    assert _switches(b5._c2_config(_FinalPresetHarness, c2, "C2", {})) == (
        True, FINAL_FLAT_SOIL_MARGIN_M)


def test_ablation_ignores_switched_on_settings_defaults(monkeypatch) -> None:
    """A module-level default switch (settings classes default on) does not reach ABL."""
    monkeypatch.setattr(c2, "LiftStrokeGuardSettings",
                        functools.partial(c2.LiftStrokeGuardSettings, soil_stop=True))
    monkeypatch.setattr(c2, "SlopeClearanceMarginSettings",
                        functools.partial(c2.SlopeClearanceMarginSettings,
                                          flat_soil_margin_m=FINAL_FLAT_SOIL_MARGIN_M))
    config = b5.ablation_config(c2, c2.C2Config().with_10hz_d1())
    assert _switches(config) == (False, 0.0)


def test_controller_settings_of_c2_abl_and_ind() -> None:
    params = load_params()
    final = _FinalPresetHarness.preset_config(None, True)
    c2_ctrl = c2.C2Controller.from_params(params, final)
    abl_ctrl = c2.C2Controller.from_params(params, b5.ablation_config(c2, final))
    industry = b5.HarnessIndustry(b5.IndustryC8.from_params(params))
    assert b5.controller_settings(c2_ctrl) == {
        "soil_stop": True, "soil_stop_scope": "any_loc",
        "flat_soil_margin_m": FINAL_FLAT_SOIL_MARGIN_M}
    abl = b5.controller_settings(abl_ctrl)
    assert (abl["soil_stop"], abl["flat_soil_margin_m"]) == (False, 0.0)
    assert b5.controller_settings(industry) == b5.IND_CONTROLLER_SETTINGS


def test_settings_meta_keeps_one_value_per_controller_or_lists_a_mix() -> None:
    on = {"soil_stop": True, "soil_stop_scope": "any_loc", "flat_soil_margin_m": 0.03}
    off = {"soil_stop": False, "soil_stop_scope": "any_loc", "flat_soil_margin_m": 0.0}
    records = [{"controller": "C2", "controller_settings": on},
               {"controller": "C2", "controller_settings": on},
               {"controller": "ABL", "controller_settings": off},
               {"controller": "ABL", "controller_settings": on},
               {"controller": "IND", "error": "boom"}]
    assert b5.settings_meta(records) == {"C2": on, "ABL": [off, on]}


# -------------------------------------------------------------------------------- IND wrapper
def _untouched_measurements(t_s: float, geometry) -> Measurements:
    """Level body, retracted legs, no load: C8 stays in TOUCH and asks v_max on every leg."""
    strokes = geometry.pad_bottom_z_retracted_m - geometry.crawler_bottom_z_m
    level = np.array([0.0, 0.0, GRAVITY_M_S2])
    return Measurements(
        t_s=t_s, specific_force_m_s2=level, angular_rate_rad_s=np.zeros(3),
        head_pressure_Pa=np.zeros(4), stroke_m=strokes, stroke_corrected_m=strokes,
        imu_specific_force_samples_m_s2=np.tile(level, (10, 1)))


def test_industry_output_is_one_period_late_and_increment_limited() -> None:
    params = load_params()
    industry = b5.IndustryC8.from_params(params)
    plain = c8.C8Controller.from_params(params, industry.settings)
    v_max = industry.geometry.max_speed_m_s
    period_s = industry.period_s
    assert period_s == pytest.approx(0.1)

    delayed, undelayed = [], []
    for k in range(8):
        measurements = _untouched_measurements(period_s * (k + 1), industry.geometry)
        delayed.append(np.asarray(industry.update(measurements).leg_speed_m_s))
        undelayed.append(np.asarray(plain.update(measurements).leg_speed_m_s))

    np.testing.assert_array_equal(delayed[0], np.zeros(4))
    for k in range(1, 8):
        np.testing.assert_allclose(delayed[k], undelayed[k - 1], rtol=0, atol=1e-15)
    steps = np.diff(np.vstack([np.zeros(4), *delayed]), axis=0)
    assert np.max(np.abs(steps)) <= 0.25 * v_max * (1 + 1e-12)
    np.testing.assert_allclose(delayed[1], np.full(4, 0.25 * v_max))
    np.testing.assert_allclose(delayed[5], np.full(4, v_max))


def test_industry_reset_clears_the_delayed_command() -> None:
    industry = b5.IndustryC8.from_params(load_params())
    for k in range(3):
        industry.update(_untouched_measurements(0.1 * (k + 1), industry.geometry))
    industry.reset()
    command = industry.update(_untouched_measurements(0.4, industry.geometry))
    np.testing.assert_array_equal(command.leg_speed_m_s, np.zeros(4))


def test_harness_wrapper_maps_the_phase_and_records_changes() -> None:
    wrapper = b5.HarnessIndustry(b5.IndustryC8.from_params(load_params()))
    assert wrapper.phase is b5.C2Phase.TOUCH
    wrapper.inner.phase = c8.C8Phase.LIFT
    wrapper.update(_untouched_measurements(0.1, wrapper.geometry))
    assert wrapper.phase is b5.C2Phase.LEVEL
    assert [event.name for event in wrapper.events] == ["ind_phase:lift"]
    assert math.isclose(wrapper.events[0].t_s, 0.1)


# ------------------------------------------------------------------------------- floor drop
def test_every_table_case_is_valid() -> None:
    for case_id in b5.CASES:
        b5.case_spec(case_id)


def test_every_table_case_has_a_display_name() -> None:
    assert set(b5.CASE_DISPLAY_NAMES) == set(b5.CASES)
    names = list(b5.CASE_DISPLAY_NAMES.values())
    assert all(name.strip() for name in names)
    assert len(set(names)) == len(names), "two cases share a display name"


def test_floor_drop_event_is_accepted_on_the_rigid_floor() -> None:
    spec = b5.case_spec("A4-G4RR-Fs8")
    assert spec["event"][0] == "RR"


@pytest.mark.parametrize("spec", [
    {"harness": "slope", "src": "H1|J1|B|top|flat", "event": ("RR", 0.0115, 2.0, 2.0)},
    {"harness": "g6", "src": "g6|G1+J1@RR|top|Fs4", "event": ("RR", 0.0115, 2.0, 2.0)},
    {"harness": "g6", "src": "g6r|rigid+J1@FL|top|Fs4", "event": ("FL", 0.01, 1.0, 1.0)},
])
def test_floor_drop_event_on_a_soil_case_raises(spec: dict, monkeypatch) -> None:
    monkeypatch.setitem(b5.CASES, "X-soil-event", spec)
    with pytest.raises(ValueError, match="rigid floor"):
        b5.case_spec("X-soil-event")
    assert any("rigid floor" in text
               for text in b5._invalid_arguments(["X-soil-event"], ["C2"]))


# ------------------------------------------------------------------------ out-of-sample ids
def test_oos_list_has_the_designed_batches() -> None:
    assert {name: len(ids) for name, ids in oos.OOS_BATCH_IDS.items()} == OOS_BATCH_SIZES
    assert len(oos.OOS_CASES) == 100
    assert len(set(oos.OOS_CASES)) == 100
    assert b5.resolve_case_ids("oos") == list(oos.OOS_CASES)


def test_oos_slope_id_round_trips_through_the_slope_case() -> None:
    for case_id in oos.OOS_CASES:
        if not case_id.startswith(oos.OOS_SLOPE_PREFIX):
            continue
        case = oos.parse_slope_case(case_id)
        assert case.group == "X"
        assert oos.slope_case_id(case.soil, case.pad, case.level, case.roll_deg,
                                 case.pitch_deg, case.fs_kN) == case_id
        assert b5.case_spec(case_id) == {"harness": "slope", "src": case_id}


def test_oos_slope_id_parses_the_angles_scaled_by_k() -> None:
    case = oos.parse_slope_case("X|J2|B|top|2.0625,1.5|Fs4")  # edge_nd @ k 0.9375
    assert (case.soil, case.pad, case.level) == ("J2", "B", "top")
    assert (case.roll_deg, case.pitch_deg, case.fs_kN) == (2.0625, 1.5, 4.0)
    assert case.harness_settle_key == "J2|top|2.0625|1.5"
    assert "X|J2|B|top|2.0625,1.5|Fs4" in oos.OOS_BATCH_IDS["T5"]


@pytest.mark.parametrize("case_id", [
    "X|J1|B|top|0,2",                # no F_s field
    "X|J1|B|top|0;2|Fs4",            # angles not comma separated
    "X|K9|B|top|0,2|Fs4",            # unknown soil
    "X|J1|C|top|0,2|Fs4",            # unknown pad
    "X|J1|B|high|0,2|Fs4",           # unknown level
])
def test_malformed_oos_slope_id_is_rejected(case_id: str) -> None:
    with pytest.raises(ValueError):
        oos.parse_slope_case(case_id)
    assert b5._invalid_arguments([case_id], ["C2"])


def test_case_list_keeps_the_comma_inside_the_angles() -> None:
    assert b5.split_case_list("A1-rigid,X|J1|B|top|0,2|Fs4,G|g6x|G1+J1@FL|middle|Fs4") == [
        "A1-rigid", "X|J1|B|top|0,2|Fs4", "G|g6x|G1+J1@FL|middle|Fs4"]
    assert b5.split_case_list("X|J1|B|top|0,2|Fs4,X|J2|B|top|0,3|Fs4") == [
        "X|J1|B|top|0,2|Fs4", "X|J2|B|top|0,3|Fs4"]


# --------------------------------------------------------------------------------- overlap
def _in_sample_toy() -> set[tuple]:
    study_1 = [oos.slope.SlopeCase("H1", "J1", "B", "top", "nose_down", 0.0, 3.2)]
    return oos.in_sample_keys(study_1, ["g6|G1+J1@RR|top|Fs4"])


@pytest.mark.parametrize("case_id", ["X|J1|B|top|0,3.2|Fs4", "G|g6x|G1+J1@RR|top|Fs4"])
def test_oos_id_repeating_an_in_sample_case_raises(case_id: str) -> None:
    with pytest.raises(ValueError, match="repeats in-sample"):
        oos.check_no_overlap([case_id], _in_sample_toy())


def test_oos_ids_repeating_each_other_raise() -> None:
    with pytest.raises(ValueError, match="repeats X"):
        oos.check_no_overlap(["X|J1|B|top|0,2|Fs4", "X|J1|B|top|0,2.0|Fs4"], set())


def test_oos_id_on_another_harness_or_f_s_does_not_overlap() -> None:
    # same soil / slope as the in-sample cases, but F_s 8 or the g6 harness at another level
    oos.check_no_overlap(["X|J1|B|top|0,3.2|Fs8", "G|g6x|G1+J1@RR|middle|Fs4"], _in_sample_toy())


def test_oos_list_does_not_overlap_study_1_and_g6() -> None:
    pytest.importorskip("numba", reason="r72_g6_screen imports numba (dynamics-dev)")
    b5.check_oos_overlap(list(oos.OOS_CASES))


# ------------------------------------------------------------------------------ settle rows
def test_soil_case_without_a_settle_row_is_rejected() -> None:
    with pytest.raises(oos.NoSettleRowError, match="J1\\|top\\|0\\|2"):
        oos.slope_case_payload("X|J1|B|top|0,2|Fs4", {})
    problems = b5.settle_row_problems(["X|J1|B|top|0,2|Fs4", "A1-rigid"], {},
                                      allow_no_settle_row=False)
    assert list(problems) == ["X|J1|B|top|0,2|Fs4"]


def test_soil_case_without_a_settle_row_runs_uncorrected_when_allowed() -> None:
    payload = oos.slope_case_payload("X|J1|B|top|0,2|Fs4", {}, allow_no_settle_row=True)
    assert payload["settle_table_status"] == "no_table_row"
    assert payload["id"] == "X|J1|B|top|0,2|Fs4"
    assert not b5.settle_row_problems(["X|J1|B|top|0,2|Fs4"], {}, allow_no_settle_row=True)


def test_rigid_oos_case_needs_no_settle_row() -> None:
    payload = oos.slope_case_payload("X|rigid|B|middle|0,3.2|Fs4", {})
    assert payload["settle_table_status"] == "rigid_reference"


def test_every_oos_soil_case_has_a_settle_row() -> None:
    assert not b5.settle_row_problems(list(oos.OOS_CASES), b5.load_settle_rows(),
                                      allow_no_settle_row=False)


def test_skip_option_drops_only_the_cases_without_a_row(monkeypatch) -> None:
    monkeypatch.setattr(b5, "load_settle_rows", dict)
    args = b5._parse_args(["run", "--cases", "x", "--skip-no-settle-row"])
    kept = b5._without_unsettled_cases(["A1-rigid", "X|J1|B|top|0,2|Fs4"], args)
    assert kept == ["A1-rigid"]
    strict_args = b5._parse_args(["run", "--cases", "x"])
    with pytest.raises(SystemExit, match="no settle-table row"):
        b5._without_unsettled_cases(["X|J1|B|top|0,2|Fs4"], strict_args)


# ------------------------------------------------------------------------ official: IND NA
def _slope_rows(failing: tuple[str, ...] = ()) -> dict:
    """Judged slope rows of a run without stroke guard or FAULT; the ``failing`` rows fail."""
    rows = {name: {"pass": True} for name in ("P3-1", "P3-2", "P3-3", "P3-4", "P3-5", "P3-8")}
    rows["P3-1"]["flag_names"] = []
    rows.update({"P3-6": {"kind": "record"}, "P3-7": {"kind": "record"},
                 "fault_ready": {"pass": True, "has_fault": False},
                 "SL-1": {"pass": True, "stroke_faults": [], "guard_warning": False,
                          "lifted_legs": []},
                 "SL-2": {"kind": "record"}, "SL-3": {"kind": "record"},
                 "SL-4": {"kind": "record"}})
    for name in failing:
        rows[name]["pass"] = False
    return rows


def test_industry_slope_verdict_leaves_out_the_c2_event_rows() -> None:
    fields = official.industry_slope_fields(_slope_rows(("P3-2", "P3-8")), {"check": None})
    assert fields["official_verdict"] == "pass"
    assert fields["official_verdict_strict"] == "fail"
    assert fields["official_failed_rows"] == []
    assert fields["official_na_rows"] == ["P3-2", "P3-8", "SL-3"]


def test_industry_slope_verdict_still_fails_on_a_truth_row() -> None:
    fields = official.industry_slope_fields(_slope_rows(("P3-4",)), {"check": None})
    assert fields["official_verdict"] == "fail"
    assert fields["official_failed_rows"] == ["P3-4"]


def test_industry_slope_verdict_keeps_the_settle_check() -> None:
    fields = official.industry_slope_fields(_slope_rows(), {"check": {"ok": False}})
    assert fields["official_verdict"] == "settle_check_fail"


def test_industry_slope_reanchor_rows_are_na() -> None:
    rows = {**_slope_rows(), "RA-1": {"pass": True}, "RA-2": {"pass": None},
            "RA-5": {"kind": "record"}}
    fields = official.industry_slope_fields(rows, {"check": None})
    assert {"RA-1", "RA-2", "RA-5"} <= set(fields["official_na_rows"])
    assert fields["official_verdict"] == "pass"
    assert fields["official_verdict_strict"] == "fail"


G6_GATES = ("G6-1_crawler", "G6-2_loc", "G6-3_Fmin", "G6-4_att", "G6-5_rut_stroke",
            "G6-6_fault_ready", "G6-7_preloc")


def _g6_record(failing: tuple[str, ...] = ()) -> dict:
    """r72 ``job`` record of a run in READY; the ``failing`` gates fail."""
    gates = {name: name not in failing for name in G6_GATES}
    return {"gates": gates, "flags": [], "final_phase": "ready", "preloc_flag_ok": None}


def test_industry_g6_verdict_leaves_out_the_loc_and_preloc_gates() -> None:
    record = _g6_record(("G6-2_loc", "G6-7_preloc"))
    record["flags"] = ["P3-1_transient_recontact", official.late_loc_rule.G62_FLAG]
    fields = official.judge_g6(record, is_industry=True)
    assert fields["official_verdict"] == "pass"
    assert fields["official_verdict_strict"] == "fail"
    assert fields["official_failed_rows"] == []
    assert fields["official_na_rows"] == ["G6-2_loc", "G6-7_preloc"]
    assert fields["official_flags"] == ["P3-1_transient_recontact"]
    assert fields["official_before_p38"]["verdict"] == "fail"


def test_industry_g6_verdict_fails_on_a_truth_gate() -> None:
    fields = official.judge_g6(_g6_record(("G6-3_Fmin",)), is_industry=True)
    assert fields["official_verdict"] == "fail"
    assert fields["official_failed_rows"] == ["G6-3_Fmin"]


@pytest.mark.parametrize(("preloc_flag_ok", "fmin_ok", "final_phase", "verdict", "flags"), [
    (True, True, "ready", "pass", ["P3-8_demoted"]),
    (False, True, "ready", "pass", ["P3-8_preloc_loss"]),
    (False, False, "ready", "fail", []),
    (False, True, "fault", "fail", []),
    (None, True, "ready", "fail", ["P3-8_unchecked"]),
])
def test_c2_g6_preloc_gate_demotion(preloc_flag_ok, fmin_ok, final_phase, verdict,
                                    flags) -> None:
    record = _g6_record(("G6-7_preloc",) if fmin_ok else ("G6-7_preloc", "G6-3_Fmin"))
    record.update(preloc_flag_ok=preloc_flag_ok, final_phase=final_phase)
    fields = official.judge_g6(record, is_industry=False)
    assert fields["official_verdict"] == verdict
    assert fields["official_verdict_strict"] == verdict
    assert fields["official_flags"] == flags
    assert "G6-7_preloc" in fields["official_before_p38"]["failed_rows"]


def test_g6_job_error_is_raised() -> None:
    with pytest.raises(RuntimeError, match="r72 job failed"):
        official.judge_g6({"key": "k", "error": "boom"}, is_industry=False)


def test_industry_wrapper_answers_the_judge_neutrally() -> None:
    wrapper = b5.HarnessIndustry(b5.IndustryC8.from_params(load_params()))
    soil = wrapper._soil_state()
    assert soil.plateau_start_s is None
    assert soil.clearance_at_plateau_start_m is None
    assert not soil.is_loc_anchor_applied
    assert wrapper._state.reanchor_anchor_pitch_rad is None
    assert math.isnan(wrapper._clearance_estimate_m(np.zeros(4)))
    expected_N = wrapper.geometry.superstructure_mass_kg * GRAVITY_M_S2
    assert wrapper._reference_weight_N() == pytest.approx(expected_N)
