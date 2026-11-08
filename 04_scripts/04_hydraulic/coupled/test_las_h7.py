"""Checks of the H-7' comparison (``las_targeted_rules_rev4.md`` 2, 3), synthetic lines only.

Run (dynamics-dev): python -I -B -m pytest <this file> -p no:cacheprovider
"""
from __future__ import annotations

import copy
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


def test_j3_and_j7_formats_read_the_stored_fields() -> None:
    d1s, u3 = las_h7.BATCH_FORMATS["J-3'"], las_h7.BATCH_FORMATS["J-7-slope"]
    assert d1s.status is las_h7.FormatStatus.DRAFT and u3.status is las_h7.FormatStatus.DRAFT
    assert las_h7.h7_violations(_d1s_case(), _d1s_case(), d1s, allow_draft=True) == {}
    found = las_h7.h7_violations(_d1s_case(p32="fail", stroke_mm=440.0), _d1s_case(), d1s,
                                 allow_draft=True)
    assert sorted(found) == ["C5'-S", "P3-2"]
    assert u3.absent == ["C4'"]
    fault = _u3_record(warnings=("FAULT_STROKE_END:FL",))
    assert list(las_h7.h7_violations(fault, _u3_record(), u3, allow_draft=True)) == ["C3"]
    assert las_h7.h7_violations(_u3_record(late="flag"), _u3_record(), u3, allow_draft=True) == {}


def test_a_draft_format_does_not_judge_without_confirmation() -> None:
    draft = las_h7.BATCH_FORMATS["J-13-grid_vb"]
    assert draft.status is las_h7.FormatStatus.DRAFT
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
