"""Judgement rows of ``verify/s6_control.judge`` after spec rev. 3 (J1-J7, I1-I8).

Synthetic per-case metrics stand in for the Chrono case directories; the full pipeline was
re-applied to the stage-2 batches by hand (only the six 5b rows fail, as spec 18.1 P4 expects).
"""

from __future__ import annotations

import json

import pytest

from outrigger_sim.verify.s6_control import (
    TARGET_CHANGE_READY_S,
    W4_N,
    CaseCondition,
    case_condition,
    diagnostic_false_alarm_metrics,
    judge,
    superseded_by,
)


def _metrics(case: str, group: str, level: str = "top", floor: str = "flat", **extra) -> dict:
    base = {
        "case": case,
        "group": group,
        "level": level,
        "floor": floor,
        "grade": "ideal",
        "final_phase": "ready",
        "ready_window_ok": True,
        "saturation_steps": 0,
        "times_s": {"ready": 30.0},
    }
    base.update(extra)
    return base


def _rows(metrics, **kwargs):
    return judge(metrics, {}, **kwargs)


def _row(rows, item: str, case=None) -> dict:
    return next(r for r in rows if r["item"] == item and (case is None or r["case"] == case))


def test_as_shipped_accuracy_is_not_judged() -> None:
    m = _metrics("G3_top_flat_normal_as_shipped", "G3", att_err_last5_maxabs_deg=0.21)
    row = _row(_rows([m]), "2 attitude +-0.2 (+mount)")
    assert row["passed"] is None and "not judged" in row["note"]


def test_filter_residual_is_a_quality_metric() -> None:
    m = _metrics("G2_top_flat", "G2", filter_residual_last5_deg=0.011)
    row = _row(_rows([m]), "5b filter residual last 5 s")
    assert row["passed"] is False
    assert row["kind"] == "quality" and "spec shortfall" in row["note"]


def test_corrective_tolerance_is_wider_on_slopes() -> None:
    """J1: +-1 % W/4 flat, +-2 % W/4 on a slope (temporary)."""
    reduced = {"corrective_kN": [0.0, 0.0, 0.0, 0.0], "t_level_after_touch_s": 15.0}
    deviation = [1.3, 0.0, 0.0, 0.0]
    flat = _metrics("G1_top_flat", "G1", reduced=reduced, final_corrective_kN=deviation)
    slope = _metrics(
        "G1_top_diag3", "G1", floor="diag3", reduced=reduced, final_corrective_kN=deviation
    )
    rows = _rows([flat, slope])
    assert _row(rows, "1c final corrective A+F", "G1_top_flat")["passed"] is False
    diag = _row(rows, "1c final corrective A+F", "G1_top_diag3")
    assert diag["passed"] is True and diag["limit"] == pytest.approx(0.02 * W4_N / 1e3)


def test_level_time_uses_the_0p2_deg_hold() -> None:
    """J2: LEVEL -> held inside 0.2 deg against the reduced reference (spec 16.2 fallback)."""
    m = _metrics(
        "G1_top_roll3",
        "G1",
        floor="roll3",
        reduced={"t_level_after_touch_s": 15.0},
        t_within_0p2_after_level_s=7.82,
        t_ready_minus_touch_s=18.6,
    )
    rows = _rows([m])
    assert _row(rows, "1a LEVEL -> held in 0.2 deg")["passed"] is True
    assert _row(rows, "1a touch -> READY (report)")["passed"] is None


def test_target_change_limit_and_crawler_clearance() -> None:
    """J3 / I4: change -> READY <= 50 s; clearance judged only with a floor plane."""
    target = {
        "stroke_max_m": 0.6,
        "change_to_ready_s": 41.6,
        "breakdown_s": {"ramp_level_s": 20.0},
        "reanchor_after_change": True,
        "crawler_clearance_min_m": None,
    }
    m = _metrics("G5_top_flat_change_p3", "G5", target_T=target, att_err_last5_maxabs_deg=0.01)
    rows = _rows([m])
    assert TARGET_CHANGE_READY_S == 50.0
    assert _row(rows, "T3 change -> READY")["passed"] is True
    assert _row(rows, "T3 crawler clearance")["passed"] is None
    target["crawler_clearance_min_m"] = 0.031
    assert _row(_rows([m]), "T3 crawler clearance")["passed"] is True


def test_target_change_without_ready_fails_after_the_limit() -> None:
    """Spec rev. 7 41.1: no READY and the run went past t_change + 50 s -> failed; ended
    earlier -> not judged."""
    target = {
        "stroke_max_m": 0.6,
        "change_to_ready_s": None,
        "run_after_change_s": 57.98,
        "breakdown_s": {"ramp_level_s": 20.0},
        "reanchor_after_change": True,
        "crawler_clearance_min_m": 0.03,
    }
    m = _metrics("G5_top_flat_change_p3", "G5", target_T=target)
    row = _row(_rows([m]), "T3 change -> READY")
    assert row["passed"] is False and row["value"] is not None and "41.1" in row["note"]
    target["run_after_change_s"] = 45.98
    row = _row(_rows([m]), "T3 change -> READY")
    assert row["passed"] is None and row["value"] is None


def test_item6_rows_are_judged() -> None:
    item6 = {
        "min_cyl_after_start_kN": 11.5,
        "re_ready_within_s": 7.8,
        "final_cyl_kN": [70.0] * 4,
        "final_att_maxabs_deg": 0.015,
        "pass_min": True,
        "pass_ready": True,
        "pass_final": True,
        "pass_att": True,
    }
    rows = _rows([_metrics("G4_top_flat_settleRR_pressure", "G4", item6=item6)])
    for item in (
        "6 min after settlement",
        "6 re-READY <= 40 s",
        "6 final >= F_min + 5 kN",
        "6 attitude <= 0.2 deg (+mount)",
    ):
        assert _row(rows, item)["passed"] is True


def _level_cases(floor: str, forces: dict, reanchor: dict, times: dict) -> list[dict]:
    return [
        _metrics(
            f"G2-R_{lv}_{floor}",
            "G2-R",
            level=lv,
            floor=floor,
            min_cyl_after_liftoff_kN=reanchor[lv],
            min_cyl_excl_reanchor_kN=forces[lv],
            min_cyl_reanchor_kN=reanchor[lv],
            min_cyl_leg="RR",
            min_cyl_t_s=40.0,
            t_ready_minus_touch_s=times[lv],
        )
        for lv in ("top", "middle", "bottom")
    ]


def test_level_trend_excludes_reanchor_and_compares_time_differences() -> None:
    """J4 (spec 20.3): ordering without REANCHOR, REANCHOR min >= F_min + 5 kN, time trend."""
    metrics = _level_cases(
        "fdown3.5",
        forces={"top": 50.5, "middle": 51.9, "bottom": 57.6},
        reanchor={"top": 30.1, "middle": 29.7, "bottom": 30.7},
        times={"top": 42.40, "middle": 42.38, "bottom": 42.32},
    )
    reduced = {"fdown3.5": {"top": 36.7, "middle": 36.7, "bottom": 36.6}}
    rows = _rows(metrics, reduced_level_times=reduced)
    assert _row(rows, "8 level trend min force (excl. REANCHOR)")["passed"] is True
    assert _row(rows, "8 REANCHOR min force")["passed"] is True
    assert _row(rows, "8 level trend time")["passed"] is True
    no_reduced = _row(_rows(metrics), "8 level trend time")
    assert no_reduced["passed"] is None


def test_reanchor_attitude_and_h4_reduction_rows() -> None:
    """The H4 reduction is recorded only since dynamics 5.17.3 (REXOME33 expectation)."""
    m = _metrics("G6_top_fdown3.5_H4on", "G6", floor="fdown3.5", reanchor_att_change_max_deg=0.0016)
    slope_r = {
        "H4_reduction_fdown3.5": {"reduction": 0.488},
        "H4_reduction_fup3.5": {"reduction": 0.30},
    }
    rows = _rows([m], slope_r=slope_r)
    assert _row(rows, "R attitude change during REANCHOR")["passed"] is True
    for floor in ("fdown3.5", "fup3.5"):
        row = _row(rows, "R H4 reduction (L basis)", floor)
        assert row["passed"] is None and row["kind"] == "report"


H4_MECHANISM_ITEM = "R H4 mechanism T_READY / mu(P_stop + m_rod g)"


def _h4_mechanism(ratio, t_ready=(16.5, 15.8), t_done=(20.0, 19.9)) -> dict:
    return {"legs": ["RL", "RR"], "ratio": list(ratio), "T_done_kN": list(t_done),
            "T_ready_kN": list(t_ready), "expected_kN": [17.3, 17.3], "P_stop_last_kN": 33.9,
            "reduction_recorded": [0.17, 0.21]}


@pytest.mark.parametrize(
    ("ratio", "t_ready", "expected"),
    [((0.95, 0.91), (16.5, 15.8), True),     # G6 of dynamics 5.17.3
     ((0.95, 0.89), (16.5, 15.4), False),    # below the band
     ((0.95, 1.05), (16.5, 21.0), False)],   # in band but larger than before H4
)
def test_j6_judges_the_h4_mechanism_on_g6(ratio, t_ready, expected) -> None:
    m = _metrics("G6_top_fdown3.5_H4on", "G6", floor="fdown3.5",
                 h4_mechanism=_h4_mechanism(ratio, t_ready))
    row = _row(_rows([m]), H4_MECHANISM_ITEM)
    assert row["passed"] is expected and row["kind"] == "function"


def test_j6_reports_other_h4_cases() -> None:
    m = _metrics("G2-R_middle_fdown3.5", "G2-R", floor="fdown3.5",
                 h4_mechanism=_h4_mechanism((0.86, 0.96)))
    row = _row(_rows([m]), H4_MECHANISM_ITEM)
    assert row["passed"] is None and row["kind"] == "report"


def _reject_metrics(final_phase="idle", **target) -> dict:
    row = {"stroke_max_m": 0.3, "motor_travel_m": 0.00335, "travel_after_check_m": 0.0,
           "check_excursion_m": 0.00335, "check_net_m": 1e-15, "check_travel_m": 0.00335,
           "calibration_active": True, "check_end_s": 2.4}
    row.update(target)
    return _metrics("G5_top_flat_reject", "G5", final_phase=final_phase, target_T=row)


@pytest.mark.parametrize(
    ("final_phase", "target", "expected"),
    [("idle", {}, True),                                          # batch B: U71 round trip
     ("idle", {"travel_after_check_m": 2e-6}, False),             # moved after CHECK
     ("idle", {"check_net_m": 2e-4}, False),                      # did not come back
     ("idle", {"check_excursion_m": 0.0036}, False),              # more than the round trip
     ("ready", {}, False),
     ("idle", {"calibration_active": False}, False),              # calibration off: still
     ("idle", {"calibration_active": False, "check_travel_m": 0.0, "check_excursion_m": 0.0,
               "motor_travel_m": 0.0}, True)],
)
def test_t1_reject_leaves_out_the_calibration_round_trip(final_phase, target, expected) -> None:
    row = _row(_rows([_reject_metrics(final_phase, **target)]), "T1 reject")
    assert row["passed"] is expected


def test_t1_reject_without_check_split_keeps_the_whole_run_rule() -> None:
    m = _metrics("G5_top_flat_reject", "G5", final_phase="idle",
                 target_T={"stroke_max_m": 0.3, "motor_travel_m": 0.00335})
    row = _row(_rows([m]), "T1 reject")
    assert row["passed"] is False and "whole-run" in row["note"]


def test_shadow_estimate_is_reported_not_judged() -> None:
    m = _metrics("G2_top_roll5.5", "G2", floor="roll5.5", shadow_minus_true_deg=[-0.0249, 0.002])
    row = _row(_rows([m]), "K8 shadow (B) - true floor")
    assert row["passed"] is None and "within" in row["note"]


def _event3(**kw):
    base = {"t_event_s": 42.0, "re_ready_s": 70.0, "re_ready_after_event_s": 28.0,
            "min_cyl_before_event_kN": 60.0, "min_cyl_after_re_ready_kN": 50.0,
            "other_legs_lifted_s": 0.0, "other_legs_lifted_per_leg_s": [0.0, 0.0, 0.0],
            "rr_lifted_after_re_ready_s": 0.0, "rr_lifted_event_to_re_ready_s": 6.0,
            "rr_lifted_ratio": 6.0 / 28.0}
    base.update(kw)
    return base


def test_floor_event_item3_rows() -> None:
    """Spec rev. 7 41.2 decision (a): whole-run F_min is info, the split rows are judged."""
    m = _metrics("RE1bF_top_flat_dropRR30", "RE1b", event="drop_RR_30",
                 min_cyl_after_liftoff_kN=0.0, min_cyl_leg="RR", min_cyl_t_s=42.1,
                 event3=_event3())
    rows = _rows([m])
    whole = _row(rows, "3 F_min (1 ms)")
    assert whole["passed"] is None and whole["kind"] == "info" and "41.2/23" in whole["note"]
    for item in ("3 F_min before the event", "3 F_min after the re-READY",
                 "3 lift-off other legs after the event", "3 lift-off RR after the re-READY",
                 "RE1b re-READY <= 60 s"):
        assert _row(rows, item)["passed"] is True, item
    report = _row(rows, "3 lift-off RR time / ratio (report)")
    assert report["passed"] is None and report["value"][0] == 6.0


def test_floor_event_without_re_ready_and_without_lift_off() -> None:
    m = _metrics("RE1bP_top_flat_dropRR30_probe", "RE1b", event="drop_RR_30_probe",
                 min_cyl_after_liftoff_kN=5.0, min_cyl_leg="RR", min_cyl_t_s=40.0,
                 event3=_event3(re_ready_s=None, re_ready_after_event_s=None,
                                min_cyl_after_re_ready_kN=None, rr_lifted_after_re_ready_s=None,
                                rr_lifted_event_to_re_ready_s=0.0, rr_lifted_ratio=None,
                                other_legs_lifted_s=0.1))
    rows = _rows([m])
    assert _row(rows, "3 F_min after the re-READY")["passed"] is None
    assert _row(rows, "3 lift-off RR after the re-READY")["passed"] is None
    assert _row(rows, "RE1b re-READY <= 60 s")["passed"] is False
    assert _row(rows, "3 lift-off other legs after the event")["passed"] is False
    assert _row(rows, "3 lift-off RR time / ratio (report)")["note"] == "사건 미발현"


def test_non_event_case_keeps_the_judged_f_min_row() -> None:
    m = _metrics("G4_top_flat_settleRR_pressure", "G4", event="settle_RR",
                 min_cyl_after_liftoff_kN=11.5, min_cyl_leg="RR", min_cyl_t_s=45.0)
    assert _row(_rows([m]), "3 F_min (1 ms)")["passed"] is True


# --- spec rev. 28: condition, one-sided J6, false diagnosis, superseded rows ------------------

H4_ONE_SIDED_ITEM = "R H4 mechanism one-sided T_READY / mu(P_stop + m_rod g)"
FALSE_DIAGNOSIS_ITEM = "72.1 (6) no false pressure diagnosis"


@pytest.mark.parametrize(
    ("settings", "expected"),
    [({"case_id": "PS1_G4_normal_cal_s12346", "pressure_grade": "normal",
       "zero_calibration": True}, CaseCondition.BASE),
     ({"case_id": "PS4_G4_FLp4_RRm4_cal", "pressure_grade": "normal",
       "zero_calibration": True, "head_offset_bar": [4.0, 0.0, 0.0, -4.0]}, CaseCondition.BASE),
     ({"case_id": "PS4_G4_FLp4_RRm4_nocal", "pressure_grade": "normal",
       "zero_calibration": False}, CaseCondition.SENSITIVITY),
     ({"case_id": "PS3_G4_old_worst_cal", "pressure_grade": "old_worst",
       "zero_calibration": True}, CaseCondition.SENSITIVITY),
     ({"case_id": "G3_top_flat_normal_as_shipped", "grade": "normal_as_shipped",
       "pressure_grade": "normal", "zero_calibration": True}, CaseCondition.SENSITIVITY),
     ({"case_id": "G3_top_flat_good_zeroed", "grade": "good_zeroed"}, CaseCondition.BASE),
     ({"case_id": "PS2_flat_conservative_nocal"}, CaseCondition.SENSITIVITY)],
)
def test_case_condition(settings, expected) -> None:
    """Spec rev. 28 111: base = ideal, or normal / good + calibration (PS-4 cal included);
    sensitivity = calibration off, IMU as shipped, conservative / old-worst grade. Older
    settings without the keys are read from the case id."""
    condition, reasons = case_condition(settings)
    assert condition is expected
    assert bool(reasons) is (expected is CaseCondition.SENSITIVITY)


def _probe(margin_kN: float) -> dict:
    return {"windows_s": [[40.0, 52.0]], "att_change_max_deg": 0.02, "verdict_match": True,
            "load_error_margin_kN": margin_kN}


def test_sensitivity_case_reports_7c_and_the_d8_margin() -> None:
    """111: a sensitivity case keeps F_min, lift-off and READY judged; 7c and F_min + 5 kN are
    reported with the raw outcome kept."""
    m = _metrics("PS2_fdown3.5_old_worst_nocal", "PS", floor="fdown3.5",
                 condition="sensitivity", condition_reasons=["pressure grade old_worst"],
                 min_cyl_after_liftoff_kN=13.52, min_cyl_leg="RL", min_cyl_t_s=60.0,
                 pad_N_min_after_liftoff_kN=10.0, F_min_N=9414.59)
    rows = judge([m], {m["case"]: _probe(2.75)})
    for item in ("7c load estimate error", "R/D8 min force >= F_min + 5 kN"):
        row = _row(rows, item)
        assert row["passed"] is None and row["passed_raw"] is False, item
        assert row["kind"] == "report" and row["condition"] == "sensitivity", item
        assert "old_worst" in row["note"], item
    for item in ("3 F_min (1 ms)", "R/D8 no pad lift-off", "run", "4 saturation steps"):
        assert _row(rows, item)["passed"] is True, item


def test_base_case_keeps_7c_judged() -> None:
    m = _metrics("PS1_flat_normal_cal_s12346", "PS", condition="base", condition_reasons=[])
    row = _row(judge([m], {m["case"]: _probe(0.4)}), "7c load estimate error")
    assert row["passed"] is False and row["kind"] == "function" and "condition" not in row


@pytest.mark.parametrize(
    ("ratio", "t_ready", "expected"),
    [((0.822, 0.973), (16.5, 15.8), True),   # PS1 fdown of bundle B: below 0.9 is safe
     ((0.95, 1.12), (16.5, 15.8), False),    # above 1.1
     ((0.86, 0.96), (16.5, 21.0), False)],   # not smaller than before H4
)
def test_j6_one_sided_on_combined_h4_cases(ratio, t_ready, expected) -> None:
    """112.1: G2-R / G3 / PS1 (combined judge) judge ratio <= 1.1 and T_READY < T_DONE; the
    two-sided row stays a report."""
    m = _metrics("G2-R_middle_fdown3.5", "G2-R", floor="fdown3.5", contact="combined",
                 h4_mechanism=_h4_mechanism(ratio, t_ready))
    rows = _rows([m])
    row = _row(rows, H4_ONE_SIDED_ITEM)
    assert row["passed"] is expected and row["kind"] == "function"
    assert _row(rows, H4_MECHANISM_ITEM)["passed"] is None


def test_j6_one_sided_is_not_added_to_g6_and_reported_without_combined() -> None:
    g6 = _metrics("G6_top_fdown3.5_H4on", "G6", floor="fdown3.5", contact="pressure",
                  h4_mechanism=_h4_mechanism((0.95, 0.91)))
    assert not [r for r in _rows([g6]) if r["item"] == H4_ONE_SIDED_ITEM]
    older = _metrics("G2-R_top_fdown3.5", "G2-R", floor="fdown3.5",
                     h4_mechanism=_h4_mechanism((0.95, 0.96)))
    row = _row(_rows([older]), H4_ONE_SIDED_ITEM)
    assert row["passed"] is None and row["kind"] == "report"


def test_j6_one_sided_of_a_sensitivity_case_is_reported() -> None:
    m = _metrics("PS2_fdown3.5_old_worst_nocal", "PS", floor="fdown3.5", contact="combined",
                 condition="sensitivity", condition_reasons=["zero calibration off"],
                 h4_mechanism=_h4_mechanism((0.56, 1.16)))
    row = _row(_rows([m]), H4_ONE_SIDED_ITEM)
    assert row["passed"] is None and row["passed_raw"] is False and row["kind"] == "report"


POST_110_1_SETTINGS = {"load_reference_settle_s": 0.5}
"""``two_pressure`` settings of a run by the 110.1 controller."""


def _events_case(*names: str, two_pressure_settings=POST_110_1_SETTINGS, case_dir=None) -> dict:
    lines = [f"C2Event(t_s={30.0 + i}, name='{name}')" for i, name in enumerate(names)]
    controller_meta = {"two_pressure": {"settings": dict(two_pressure_settings)}}
    result = {"case": "G1_top_flat", "controller_meta": controller_meta}
    return {"events": lines, "result": result, "dir": case_dir}


def test_false_diagnosis_row() -> None:
    """110.1: no D5 / E-5 warning without injection is judged; injected cases are recorded."""
    warned = diagnostic_false_alarm_metrics(
        _events_case("ready_heave_tail", "WARN_LOAD_SUM_MISMATCH"), {"head_offset_bar": [0] * 4})
    assert warned == {"counts": {"WARN_LOAD_SUM_MISMATCH": 1, "WARN_PRESSURE_DRIFT": 0},
                      "injection": [], "constant_offset": [],
                      "pre_load_reference_code": False, "replay": None}
    rows = _rows([_metrics("G1_top_flat", "G1", diagnostic_check=warned)])
    assert _row(rows, FALSE_DIAGNOSIS_ITEM)["passed"] is False
    quiet = diagnostic_false_alarm_metrics(_events_case("ready_heave_tail"), {})
    rows = _rows([_metrics("G1_top_flat", "G1", diagnostic_check=quiet)])
    assert _row(rows, FALSE_DIAGNOSIS_ITEM)["passed"] is True
    drift = diagnostic_false_alarm_metrics(_events_case("WARN_PRESSURE_DRIFT"),
                                           {"head_drift_bar": [2.0, 0.0, 0.0, 0.0]})
    rows = _rows([_metrics("PS5_flat_drift_FLp2_600s", "PS", diagnostic_check=drift)])
    row = _row(rows, FALSE_DIAGNOSIS_ITEM)
    assert row["passed"] is None and row["kind"] == "report" and "head_drift_bar" in row["note"]


def test_constant_head_offset_is_judged() -> None:
    """Rev. 29 122: a constant ``head_offset_bar`` (PS4, PS7d/e) is no injection."""
    offset = diagnostic_false_alarm_metrics(
        _events_case("ready_heave_tail"), {"head_offset_bar": [4.0, 0.0, 0.0, -4.0]})
    assert offset["injection"] == [] and offset["constant_offset"] == ["head_offset_bar"]
    row = _row(_rows([_metrics("PS4_RE1bF_FLp4_RRm4_nocal", "PS", diagnostic_check=offset)]),
               FALSE_DIAGNOSIS_ITEM)
    assert row["passed"] is True and row["kind"] == "function"


def _write_replay(path, longest_run_s: float) -> None:
    case = {"case": "G1_top_flat", "batch": "stage2_old", "longest_run_over_4kN_s": longest_run_s,
            "max_abs_dev_kN": 5.46, "references_t_s_sum_kN": [[26.34, 376.0]]}
    path.write_text(json.dumps({"cases": [case]}), encoding="utf-8")


@pytest.mark.parametrize(("longest_run_s", "replay_passed"),
                         [(0.06, True), (0.5, None), (30.0, False)])
def test_pre_110_1_record_is_superseded_by_the_replay(tmp_path, longest_run_s,
                                                      replay_passed) -> None:
    """Rev. 29 129 ①: no ``load_reference_settle_s`` in the run's settings -> the recorded
    warning row is ``superseded`` (``passed`` None, raw outcome kept), ``replay_passed`` from
    the replay file (E-5 30 s; D5 decided only below the 0.5 s hold)."""
    replay_path = tmp_path / f"replay_{longest_run_s:g}.json"
    _write_replay(replay_path, longest_run_s)
    case = _events_case("WARN_LOAD_SUM_MISMATCH", two_pressure_settings={},
                        case_dir=tmp_path / "stage2_old" / "G1_top_flat")
    check = diagnostic_false_alarm_metrics(case, {}, replay_path)
    assert check["pre_load_reference_code"] is True
    assert check["replay"]["replay_passed"] is replay_passed
    row = _row(_rows([_metrics("G1_top_flat", "G1", diagnostic_check=check)]),
               FALSE_DIAGNOSIS_ITEM)
    assert row["kind"] == "superseded" and row["passed"] is None and row["passed_raw"] is False
    assert row["replay_passed"] is replay_passed
    assert row["superseded_by"] == "verify_S6_L1_diag_load_reference_rev29.json"
    assert row["note"].startswith("pre-110.1 record; judged by offline replay")


def test_pre_110_1_record_missing_from_the_replay(tmp_path) -> None:
    replay_path = tmp_path / "replay.json"
    _write_replay(replay_path, 0.0)
    case = _events_case(two_pressure_settings={}, case_dir=tmp_path / "other" / "G1_top_flat")
    check = diagnostic_false_alarm_metrics(case, {}, replay_path)
    assert check["pre_load_reference_code"] is True and check["replay"] is None
    row = _row(_rows([_metrics("G1_top_flat", "G1", diagnostic_check=check)]),
               FALSE_DIAGNOSIS_ITEM)
    assert row["kind"] == "superseded" and row["replay_passed"] is None
    assert row["passed_raw"] is True


L1R_OFF_FALLBACK = {"rod_side_mechanics_override": "one_sided_parallel",
                    "effective_mechanics": "off", "fallback": "settlement legs"}


@pytest.mark.parametrize(
    ("settings", "expected"),
    [({"event": "drop_RR_30", "l1r": L1R_OFF_FALLBACK}, True),
     ({"event": "settle_RR", "l1r": L1R_OFF_FALLBACK}, True),
     ({"event": "drop_RR_30",
       "l1r": {**L1R_OFF_FALLBACK, "effective_mechanics": "one_sided_parallel"}}, False),
     ({"event": None, "l1r": L1R_OFF_FALLBACK}, False),
     ({"event": "drop_RR_30"}, False)],
)
def test_superseded_by_b2(settings, expected) -> None:
    """109.2: only settlement / drop runs of an L1-R bundle with the mechanics off."""
    assert (superseded_by(settings) is not None) is expected


def test_superseded_rows_are_records() -> None:
    m = _metrics("G4_top_flat_settleRR_pressure", "G4", event="settle_RR",
                 min_cyl_after_liftoff_kN=11.5, min_cyl_leg="RR", min_cyl_t_s=45.0,
                 superseded_by="B2 (L1-R on, spec rev. 28 109.2)")
    row = _row(_rows([m]), "3 F_min (1 ms)")
    assert row["passed"] is None and row["passed_raw"] is True
    assert row["kind"] == "superseded" and row["superseded_by"].startswith("B2")
