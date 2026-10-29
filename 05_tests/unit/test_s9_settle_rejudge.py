"""Settle v2 re-judge of ``records`` inputs (``04_scripts/03_control/s9/s9_settle_rejudge.py``).

s9_slope_fix_candidates.py ``run`` writes ``records`` without settle data; their settle v2 verdict
comes from a re-judged s9_soil_slope ``results`` baseline (direct / baseline_rows / rebuilt).
Synthetic inputs only, no simulation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT / "04_scripts" / "03_control" / "s9", ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import s9_settle_rejudge as rj  # noqa: E402

BASELINE_HASH = "a" * 64
OTHER_HASH = "b" * 64
GUARD_WARNING = "WARN_LIFT_STROKE_LIMITED:FL"


def _baseline_result(case_id: str, *, is_settle_ok: bool = True,
                     verdict_rows: str = "pass") -> dict:
    return {"id": case_id, "settle": {"check": {"ok": is_settle_ok}},
            "run": {"commands_sha256": BASELINE_HASH}, "verdict_rows": verdict_rows,
            "verdict": verdict_rows if is_settle_ok else "settle_check_fail"}


def _record(case_id: str = "H1|G1|B|top|flat", *, verdict: str = "settle_check_fail",
            record_hash: str = OTHER_HASH, failed_rows: list[str] | None = None,
            warnings: list[str] | None = None) -> dict:
    return {"id": case_id, "candidate": "current", "verdict": verdict, "hash": record_hash,
            "failed_rows": failed_rows or [], "warnings": warnings or [], "passed": False}


@pytest.mark.parametrize(("failed_rows", "warnings", "expected"), [
    (["fault_ready"], [], "fail"),
    ([], ["FAULT_STROKE_END:RL"], "fail"),
    ([], [], "pass"),
    (["P3-1"], [], "fail"),
    (["P3-5", "SL-1"], [GUARD_WARNING], "stroke_limited_pass"),
    (["P3-5", "P3-3"], [GUARD_WARNING], "stroke_limited_fail"),
])
def test_rebuild_row_verdict(failed_rows, warnings, expected) -> None:
    record = _record(failed_rows=failed_rows, warnings=warnings)
    assert rj.rebuild_row_verdict(record) == expected


def test_hash_match_takes_the_baseline_row_verdict() -> None:
    baseline = {"c": _baseline_result("c", verdict_rows="stroke_limited_pass")}
    record = _record("c", record_hash=BASELINE_HASH)
    assert rj.record_settle_v2_verdict(record, baseline) == ("stroke_limited_pass",
                                                             rj.SOURCE_BASELINE_ROWS)


def test_hash_mismatch_rebuilds_from_failed_rows() -> None:
    baseline = {"c": _baseline_result("c", verdict_rows="fail")}
    record = _record("c", failed_rows=["P3-5"], warnings=[GUARD_WARNING])
    assert rj.record_settle_v2_verdict(record, baseline) == ("stroke_limited_pass",
                                                             rj.SOURCE_REBUILT)


@pytest.mark.parametrize(("verdict", "is_settle_ok", "in_baseline", "expected"), [
    ("fail", True, True, "fail"),
    ("pass", False, True, "settle_check_fail"),
    ("settle_check_fail", False, True, "settle_check_fail"),
    ("settle_check_fail", True, False, "settle_check_fail"),
])
def test_other_records_are_direct(verdict, is_settle_ok, in_baseline, expected) -> None:
    baseline = {"c": _baseline_result("c", is_settle_ok=is_settle_ok)} if in_baseline else {}
    record = _record("c", verdict=verdict, record_hash=BASELINE_HASH)
    assert rj.record_settle_v2_verdict(record, baseline) == (expected, rj.SOURCE_DIRECT)


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_records_file_round_trip(tmp_path: Path) -> None:
    baseline_path = _write_json(tmp_path / "baseline.json", {
        "meta": {"settle_rejudge": {}},
        "results": [_baseline_result("a"), _baseline_result("b", verdict_rows="fail")]})
    records = [_record("a", record_hash=BASELINE_HASH), _record("b"),
               _record("a", verdict="fail")]
    source_path = _write_json(tmp_path / "fix.json", {
        "meta": {"script": "fix"}, "summary": {"stale": 1}, "records": records})

    report = rj.rejudge_file(source_path, rj.DEFAULT_TABLE, "_v2", baseline_path=baseline_path,
                             out_dir=tmp_path / "out")

    written = json.loads((tmp_path / "out" / "fix_v2.json").read_text(encoding="utf-8"))
    assert report["out"] == tmp_path / "out" / "fix_v2.json"
    assert [r["verdict"] for r in written["records"]] == ["pass", "pass", "fail"]
    assert [r["settle_v2_source"] for r in written["records"]] == [
        rj.SOURCE_BASELINE_ROWS, rj.SOURCE_REBUILT, rj.SOURCE_DIRECT]
    assert [r["verdict_before_settle_v2"] for r in written["records"]] == [
        "settle_check_fail", "settle_check_fail", "fail"]
    assert [r["passed"] for r in written["records"]] == [True, True, False]
    assert "summary" not in written
    assert written["counts"]["after"] == {"pass": 2, "fail": 1}
    meta = written["meta"]["settle_rejudge"]
    assert meta["from_sha256"] == rj._sha256(source_path)
    assert meta["baseline_sha256"] == rj._sha256(baseline_path)


def test_baseline_must_be_rejudged(tmp_path: Path) -> None:
    baseline_path = _write_json(tmp_path / "raw.json", {"meta": {}, "results": []})
    with pytest.raises(ValueError, match="re-judged"):
        rj.load_baseline(baseline_path)


def test_unknown_format_is_rejected(tmp_path: Path) -> None:
    source_path = _write_json(tmp_path / "other.json", {"meta": {}, "rows": []})
    with pytest.raises(ValueError, match="'results'"):
        rj.rejudge_file(source_path, rj.DEFAULT_TABLE, "_v2", out_dir=tmp_path)
