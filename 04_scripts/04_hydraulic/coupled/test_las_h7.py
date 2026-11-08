"""Checks of the H-7' comparison (``las_targeted_rules_rev4.md`` 2, 3), synthetic lines only.

Run (dynamics-dev): python -I -B -m pytest <this file> -p no:cacheprovider
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import las_h7  # noqa: E402
import pytest  # noqa: E402

D1 = las_h7.D1_FORMAT
R72 = las_h7.R72_FORMAT


def _d1(verdict: str = "pass", *, fail_items=(), faults=(), g62=True, p32=True,
        ready=60.0, stroke=0.6, fired: bool = False, events: bool = True) -> dict:
    names = {name: 1 for name in faults}
    if fired:
        names["INFO_LIFTOFF_SLOW"] = 1
    items = {}
    if g62 is not None:
        items["G6-2_loc"] = g62
    if p32 is not None:
        items["P3-2"] = p32
    return {"event_names": names if events else None,
            "d1": {"verdict": verdict, "fail_items": list(fail_items), "items": items,
                   "t_ready_s": ready, "stroke_max_m": stroke}}


def test_identical_lines_have_no_violation() -> None:
    assert las_h7.h7_violations(_d1(), _d1(), D1) == {}


@pytest.mark.parametrize(("new", "base", "criterion"), [
    (_d1("fail", fail_items=("READY",)), _d1(), "C2"),
    (_d1("fail", fail_items=("READY",)), _d1("allowed_stop"), "C2"),
    (_d1("fail", fail_items=("A", "B")), _d1("fail", fail_items=("A",)), "C2"),
    (_d1(faults=("FAULT_X",)), _d1(), "C3"),
    (_d1(events=False), _d1(), "C3"),
    (_d1(), _d1(events=False), "C3"),
    (_d1(g62=False), _d1(), "C4'"),
    (_d1(g62=None), _d1(), "C4'"),
    (_d1(p32=False), _d1(), "P3-2"),
    (_d1(p32=None), _d1(), "P3-2"),
    (_d1(ready=65.01), _d1(), "C5'-R"),
    (_d1(ready=None), _d1(), "C5'-R"),
    (_d1(stroke=0.6011), _d1(), "C5'-S"),
    (_d1(stroke=None), _d1(), "C5'-S"),
    (_d1(), _d1(stroke=None), "C5'-S"),
])
def test_each_violation_is_found_alone(new: dict, base: dict, criterion: str) -> None:
    assert list(las_h7.h7_violations(new, base, D1)) == [criterion]


def test_limits_and_the_allowed_none_cases() -> None:
    # 0.601 - 0.6 is 1.0000000000000009e-3 in binary: plain subtraction, as las_judge C5
    assert las_h7.h7_violations(_d1(ready=65.0, stroke=0.6009), _d1(), D1) == {}
    assert las_h7.h7_violations(_d1(ready=None), _d1(ready=None), D1) == {}  # both None
    assert las_h7.h7_violations(_d1(ready=70.0), _d1(ready=None), D1) == {}
    assert las_h7.h7_violations(_d1("fail", fail_items=("A",)),
                                _d1("fail", fail_items=("A", "B")), D1) == {}
    # a baseline without the item (G6 row without P3-2, steady row without G6-2) is n/a
    assert las_h7.h7_violations(_d1(p32=None, g62=None), _d1(p32=None, g62=None), D1) == {}
    assert las_h7.not_applicable(_d1(p32=None), D1) == ["P3-2"]
    # a baseline that already failed P3-2 / G6-2 is no target of that criterion
    assert las_h7.h7_violations(_d1(p32=False), _d1(p32=False), D1) == {}


def _r72(passed: bool = True, late: str | None = "pass", ready=70.0, stroke_mm=550.0,
         g62=True, events=(("1.0", "INFO_X"),)) -> dict:
    return {"events": [list(event) for event in events],
            "base": {"pass": passed, "gates": {"G6-2_loc": g62, "G6-3_Fmin": passed},
                     "late_loc_reapproach": {"verdict": late}, "t_ready_s": ready},
            "r79": {"max_true_stroke_mm": stroke_mm}}


def test_r72_format_reads_the_dg3_fields() -> None:
    assert las_h7.h7_violations(_r72(), _r72(), R72) == {}
    assert list(las_h7.h7_violations(_r72(late="fail"), _r72(), R72)) == ["P3-2"]
    assert las_h7.h7_violations(_r72(late="flag"), _r72(), R72) == {}  # FLAG is no failure
    assert list(las_h7.h7_violations(_r72(stroke_mm=551.5), _r72(), R72)) == ["C5'-S"]
    found = las_h7.h7_violations(_r72(passed=False), _r72(), R72)
    assert "C2" in found and "G6-3_Fmin" in found["C2"]
    fault = _r72(events=(("2.0", "FAULT_STROKE_END:FL"),))
    assert list(las_h7.h7_violations(fault, _r72(), R72)) == ["C3"]


def test_ready_only_format_skips_the_absent_quantities() -> None:
    fmt = las_h7.READY_ONLY_FORMAT
    assert fmt.absent == ["C4'", "P3-2", "C5'-S"]
    judge = {"name": "u9_judge", "version": "rules_rev1", "sha256": "e" * 64}
    line = {"event_names": {}, "judged": {"verdict": "pass", "fail_items": [], "judge": judge},
            "values": {"times": {"t_first_ready_s": 50.0}}}
    late = copy.deepcopy(line)
    late["values"]["times"]["t_first_ready_s"] = 56.0
    assert list(las_h7.h7_violations(late, line, fmt)) == ["C5'-R"]
    no_verdict = copy.deepcopy(line)
    del no_verdict["judged"]
    assert list(las_h7.h7_violations(no_verdict, line, fmt)) == ["C2"]
    anonymous = copy.deepcopy(line)  # rev4a 5: a judged block without the judge's identity
    del anonymous["judged"]["judge"]["sha256"]
    assert "verdict missing" in las_h7.h7_violations(anonymous, line, fmt)["C2"]


def test_a_possibly_cut_event_list_is_undecidable() -> None:
    capped = _d1()
    capped["event_names"] = {"INFO_X": las_h7.D1_EVENTS_LIMIT}
    with pytest.raises(las_h7.UndecidableLine, match="baseline"):
        las_h7.h7_violations(_d1(), capped, D1)
    full = _r72(events=[(str(i), "INFO_X") for i in range(las_h7.R79_EVENTS_LIMIT)])
    with pytest.raises(las_h7.UndecidableLine, match="new"):
        las_h7.h7_violations(full, _r72(), R72)
    flagged = {**_r72(), "events_incomplete": True}
    with pytest.raises(las_h7.UndecidableLine):
        las_h7.h7_violations(flagged, _r72(), R72)
    fired_full = las_h7.TargetLine("a", full, _r72(), [[1.0, "INFO_LIFTOFF_SLOW:FL"]])
    silent_full = las_h7.TargetLine("b", full, _r72(), [])
    result = las_h7.judge_batch("J-10", [fired_full, silent_full])
    assert sorted(result["undecidable"]) == ["a", "b"] and result["stop"]


def _d1s_case(verdict="pass", p32="pass", ready=67.3, stroke_mm=438.5, g62=True) -> dict:
    """The shape of ``paper_runs/d1_scm/d1s_judge.json`` ``cases.<id>`` (2026-11-08)."""
    return {"verdict": verdict, "gates": {"G6-2_loc": g62, "G6-3_Fmin": True},
            "p3_checks": {"P3-2_verdict": p32, "P3-3_within": True},
            "t_ready_rel_s": ready, "stroke_max_mm": stroke_mm,
            "events": ["INFO_PRESSURE_ZERO_CALIBRATED:FL", "crawler_liftoff_confirmed"]}


def _u3_record(verdict="pass", late="pass", ready=39.3, stroke_mm=407.2, warnings=()) -> dict:
    """The shape of ``v5_rerun/u3_slope_V0.json`` ``records[i]`` (2026-11-08)."""
    return {"verdict": verdict, "failed_rows": [], "late_loc_reapproach": {"verdict": late},
            "t_ready_s": ready, "max_stroke_mm": stroke_mm, "warnings": list(warnings)}


def _counted(case: dict, count: int | None = None) -> dict:
    """A J-3' row with ``result_events_count`` (the result.json count, default = its own)."""
    result = {"events": [{"t_s": 0.0, "name": n} for n in case["events"]]}
    row = las_h7.with_result_events_count(case, result)
    return row if count is None else {**row, las_h7.RESULT_EVENTS_COUNT_KEY: count}


def _rerun(record: dict, las_events: dict | None) -> dict:
    """A J-7 rerun record: the stored fields plus the ``v5`` block's ``las_events``."""
    return {**record, "v5": {} if las_events is None else {"las_events": las_events}}


def test_j3_format_is_declared_and_checks_the_event_count() -> None:
    d1s = las_h7.BATCH_FORMATS["J-3'"]
    assert d1s.status is las_h7.FormatStatus.DECLARED and d1s.absent == []
    assert las_h7.h7_violations(_counted(_d1s_case()), _counted(_d1s_case()), d1s) == {}
    found = las_h7.h7_violations(_counted(_d1s_case(p32="fail", stroke_mm=440.0)),
                                 _counted(_d1s_case()), d1s)
    assert sorted(found) == ["C5'-S", "P3-2"]
    with pytest.raises(las_h7.UndecidableLine, match="2 events != result.json 5"):
        las_h7.h7_violations(_counted(_d1s_case(), 5), _counted(_d1s_case()), d1s)
    with pytest.raises(las_h7.UndecidableLine, match="baseline: no result_events_count"):
        las_h7.h7_violations(_counted(_d1s_case()), _d1s_case(), d1s)


def test_j7_format_reads_las_events_of_the_rerun_and_warnings_of_the_baseline() -> None:
    u3 = las_h7.BATCH_FORMATS["J-7-slope"]
    assert u3.status is las_h7.FormatStatus.DECLARED and u3.absent == ["C4'"]
    quiet = las_h7.las_events_record([])
    assert las_h7.h7_violations(_rerun(_u3_record(), quiet), _u3_record(), u3) == {}
    fault = las_h7.las_events_record([(40.0, "FAULT_STROKE_END:FL")])
    assert list(las_h7.h7_violations(_rerun(_u3_record(), fault), _u3_record(), u3)) == ["C3"]
    stored_fault = _u3_record(warnings=("FAULT_STROKE_END:FL",))  # baseline FAULT = warnings
    assert las_h7.h7_violations(_rerun(stored_fault, fault), stored_fault, u3) == {}
    assert las_h7.h7_violations(_rerun(_u3_record(late="flag"), quiet), _u3_record(), u3) == {}
    with pytest.raises(las_h7.UndecidableLine, match="las_events"):
        las_h7.h7_violations(_rerun(_u3_record(), None), _u3_record(), u3)
    fired = las_h7.las_events_record([(30.0, "INFO_LIFTOFF_SLOW:RR")])
    lines = [las_h7.TargetLine("fired", _rerun(_u3_record(ready=50.0), fired), _u3_record(),
                               None),
             las_h7.TargetLine("no record", _rerun(_u3_record(), None), _u3_record(), None),
             las_h7.TargetLine("silent", _rerun(_u3_record(), quiet), _u3_record(), None)]
    result = las_h7.judge_batch("J-7-slope", lines)
    assert result["fired"] == ["fired"] and list(result["violations"]) == ["fired"]
    assert list(result["undecidable"]) == ["no record"] and result["stop"]


def test_las_events_record_reads_events_only() -> None:
    class Event:
        def __init__(self, t_s: float, name: str) -> None:
            self.t_s, self.name = t_s, name

    events = [Event(30.0, "INFO_LIFTOFF_SLOW:RR"), Event(31.0, "INFO_LIFTOFF_SLOW_END:loc"),
              Event(40.0, "FAULT_STROKE_END:FL"), Event(41.0, "crawler_liftoff_confirmed")]
    before = [(e.t_s, e.name) for e in events]
    record = las_h7.las_events_record(events)
    assert record == {"liftoff_slow": [[30.0, "INFO_LIFTOFF_SLOW:RR"],
                                       [31.0, "INFO_LIFTOFF_SLOW_END:loc"]],
                      "fault_names": ["FAULT_STROKE_END:FL"], "event_count": 4}
    assert [(e.t_s, e.name) for e in events] == before
    assert las_h7.las_events_record([(1.0, "INFO_X")])["event_count"] == 1


def test_rev4c_formats_are_declared_with_their_format_absent_cells() -> None:
    assert las_h7.BATCH_FORMATS["J-5"].absent == ["C4'", "P3-2"]
    assert las_h7.BATCH_FORMATS["J-13-grid_vb"].absent == ["C4'", "P3-2", "C5'-S"]
    assert las_h7.BATCH_FORMATS["J-15"].absent == ["C4'"]
    assert all(fmt.status is las_h7.FormatStatus.DECLARED
               for fmt in las_h7.BATCH_FORMATS.values())
    grid = las_h7.BATCH_FORMATS["J-13-grid_vb"]
    run = {"pass": True, "gates": {"fault0": True}, "fault_events": [], "warnings": [],
           "t_ready_back_s": 22.6, "las_events": las_h7.las_events_record([])}
    late = {**run, "t_ready_back_s": 30.0, "warnings": ["FAULT_X"]}
    assert sorted(las_h7.h7_violations(late, run, grid, allow_draft=True)) == ["C3", "C5'-R"]
    stage3 = las_h7.BATCH_FORMATS["J-15"]
    result = {"events": [{"t_s": 1.0, "name": "crawler_liftoff_confirmed"}],
              "judged": {"verdict": "pass", "fail_items": [],
                         "judge": {"name": "rev12", "version": "12", "sha256": "e" * 64}},
              "p3b": {"checks": {"P3-2_verdict": "pass"},
                      "P3-6_ready": {"t_ready_after_loop_start_s": 70.2},
                      "P3-5_clearance_stroke": {"s_motor_max_m": [0.40, 0.41, 0.39, 0.40]}}}
    worse = json.loads(json.dumps(result))
    worse["p3b"]["P3-5_clearance_stroke"]["s_motor_max_m"][1] = 0.412
    assert list(las_h7.h7_violations(worse, result, stage3, allow_draft=True)) == ["C5'-S"]


def test_a_draft_format_does_not_judge_without_confirmation() -> None:
    from dataclasses import replace

    draft = replace(las_h7.BATCH_FORMATS["J-13-grid_vb"], status=las_h7.FormatStatus.DRAFT)
    with pytest.raises(ValueError, match="control-expert"):
        las_h7.h7_violations({}, {}, draft)


def test_fired_detection_ignores_the_end_event() -> None:
    assert las_h7.is_fired({"INFO_LIFTOFF_SLOW": 1})
    assert las_h7.is_fired([[1.0, "INFO_LIFTOFF_SLOW:FL"]])
    assert not las_h7.is_fired({"INFO_LIFTOFF_SLOW_END": 1})
    assert not las_h7.is_fired(None)


def test_batch_judgement_targets_and_first_runs() -> None:
    lines = [las_h7.TargetLine("a", _d1(fired=True, ready=80.0), _d1(), {"INFO_LIFTOFF_SLOW": 1}),
             las_h7.TargetLine("b", _d1(fired=True), None, {"INFO_LIFTOFF_SLOW": 1}),
             las_h7.TargetLine("c", _d1(ready=99.0), _d1(), {})]
    result = las_h7.judge_batch("J-1", lines)
    assert result["targets"] == 1 and list(result["violations"]) == ["a"]
    assert result["fired_without_baseline"] == ["b"] and result["stop"]
    first = las_h7.judge_batch("J-8", lines)
    assert first["h7_applies"] is False and first["fired"] == ["a", "b"]
    with pytest.raises(KeyError):
        las_h7.judge_batch("J-99", lines)


def test_silent_lines_keep_the_stored_hash() -> None:
    """rev4c 4: per batch, a silent line with another (or no) hash stops; 0 silent is noted."""
    same = las_h7.TargetLine("same", _d1(), _d1(), {}, new_hash="a" * 64, base_hash="a" * 64)
    other = las_h7.TargetLine("other", _d1(), _d1(), {}, new_hash="b" * 64, base_hash="a" * 64)
    result = las_h7.judge_batch("J-1", [same])
    assert result["silent_hash"]["silent_equal"] == 1 and not result["stop"]
    result = las_h7.judge_batch("J-1", [same, other])
    assert list(result["silent_hash"]["silent_hash_differs"]) == ["other"] and result["stop"]
    fired = las_h7.TargetLine("f", _d1(fired=True), _d1(), {"INFO_LIFTOFF_SLOW": 1})
    none_silent = las_h7.judge_batch("J-1", [fired])["silent_hash"]
    assert none_silent["silent_lines"] == 0 and none_silent["note"]


def _jp_verify(*, passed=True, events=("floor_estimate_touch",), fault_row=None) -> dict:
    """The shape of ``paper_runs/jp_verify/verify_v5jp_*.json`` (2026-11-08)."""
    rows = [{"item": "run", "case": "N_G4_Fs0_pressure", "passed": True},
            {"item": "3 F_min (1 ms)", "case": "N_G4_Fs0_pressure", "passed": passed}]
    if fault_row is not None:
        rows.append({"item": "fault rows", "case": "N_G4_Fs0_pressure", "passed": fault_row})
    metrics = {"case": "N_G4_Fs0_pressure", "ready_s": 30.9,
               "stroke": {"max_m": [0.403, 0.402, 0.392, 0.404]},
               "events": [f"C2Event(t_s=26.9, name='{name}')" for name in events]}
    return {"rows": rows, "metrics": [metrics]}


def test_jp_format_reads_rows_metrics_and_las_events() -> None:
    fmt = las_h7.BATCH_FORMATS["J-5"]
    base = las_h7.jp_case_line(_jp_verify(), "N_G4_Fs0_pressure")
    quiet = las_h7.las_events_record([])
    new = las_h7.jp_case_line(_jp_verify(), "N_G4_Fs0_pressure", quiet)
    assert las_h7.h7_violations(new, base, fmt) == {}
    failed = las_h7.jp_case_line(_jp_verify(passed=False), "N_G4_Fs0_pressure", quiet)
    assert "3 F_min (1 ms)" in las_h7.h7_violations(failed, base, fmt)["C2"]
    fault = las_h7.las_events_record([(40.0, "FAULT_STROKE_END:FL")])
    new_fault = las_h7.jp_case_line(_jp_verify(), "N_G4_Fs0_pressure", fault)
    assert list(las_h7.h7_violations(new_fault, base, fmt)) == ["C3"]
    stored_fault = las_h7.jp_case_line(_jp_verify(events=("FAULT_STROKE_END:FL",)),
                                       "N_G4_Fs0_pressure")
    assert las_h7.h7_violations(new_fault, stored_fault, fmt) == {}  # metrics.events FAULT
    # a failed FAULT row joins the baseline set but names no event: a new FAULT stays new
    row_fault = las_h7.jp_case_line(_jp_verify(fault_row=False), "N_G4_Fs0_pressure")
    assert "C3" in las_h7.h7_violations(
        las_h7.jp_case_line(_jp_verify(fault_row=False), "N_G4_Fs0_pressure", fault),
        row_fault, fmt)
    longer = json.loads(json.dumps(_jp_verify()))
    longer["metrics"][0]["stroke"]["max_m"][3] = 0.4055
    assert list(las_h7.h7_violations(las_h7.jp_case_line(longer, "N_G4_Fs0_pressure", quiet),
                                     base, fmt)) == ["C5'-S"]


def test_jp_without_las_events_or_fault_source_is_undecidable() -> None:
    fmt = las_h7.BATCH_FORMATS["J-5"]
    base = las_h7.jp_case_line(_jp_verify(), "N_G4_Fs0_pressure")
    with pytest.raises(las_h7.UndecidableLine, match="las_events"):
        las_h7.h7_violations(base, base, fmt)
    bare = {"case": "x", "metrics": {"ready_s": 1.0}}
    new = las_h7.jp_case_line(_jp_verify(), "N_G4_Fs0_pressure", las_h7.las_events_record([]))
    with pytest.raises(las_h7.UndecidableLine, match="no FAULT source"):
        las_h7.h7_violations(new, bare, fmt)
    # the stored metrics.events never mark a line fired
    stored_las = las_h7.jp_case_line(_jp_verify(events=("INFO_LIFTOFF_SLOW:FL",)),
                                     "N_G4_Fs0_pressure")
    result = las_h7.judge_batch("J-5", [las_h7.TargetLine("k", stored_las, base)])
    assert result["fired"] == [] and "k" in result["undecidable"]
