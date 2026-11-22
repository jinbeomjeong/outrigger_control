"""436.9 edition 5 j9_main (erratum 2 2-7.1): ``jp3_j9main_judge.py`` and the run_v5 V0 sample
batch. The end-to-end judge test reads the stored ``v5/main.jsonl`` (its VB / LS lines stand in
for VBJ / LSJ rows; only statuses and counts are asserted, no value is printed)."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import jp3_j9main_judge as j9  # noqa: E402
import run_v5  # noqa: E402

DATA_ROOT = Path(os.environ.get("OUTRIGGER_RECORDS_ROOT", ROOT))
MAIN_JSONL = DATA_ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "main.jsonl"
SHA = "c" * 64


def _write_rows(path: Path, rows: list[dict]) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _v0_jobs(count: int) -> list[dict]:
    return [job for job in run_v5.batch_jobs("main") if job["setting"] == "V0"][:count]


def test_v0_sample_same_differs_and_refusals(tmp_path) -> None:
    jobs = _v0_jobs(3)
    stored = _write_rows(tmp_path / "main.jsonl", [{"job": job, "commands_sha256": f"{i}" * 64}
                                                  for i, job in enumerate(jobs)])
    sha = hashlib.sha256(stored.read_bytes()).hexdigest()
    keys = tmp_path / "keys.json"
    keys.write_text(json.dumps({"jobs": jobs[:2]}), encoding="utf-8")
    same = _write_rows(tmp_path / "same.jsonl", [{"job": job, "commands_sha256": f"{i}" * 64}
                                                for i, job in enumerate(jobs[:2])])
    assert j9.v0_sample(keys, same, stored, sha)["status"] == "same"
    other = _write_rows(tmp_path / "other.jsonl", [{"job": jobs[0], "commands_sha256": "0" * 64},
                                                  {"job": jobs[1], "commands_sha256": "9" * 64}])
    report = j9.v0_sample(keys, other, stored, sha)
    assert report["status"] == "differs" and len(report["differing"]) == 1
    missing = _write_rows(tmp_path / "missing.jsonl",
                          [{"job": jobs[0], "commands_sha256": "0" * 64}])
    assert j9.v0_sample(keys, missing, stored, sha)["status"] == "not_judgeable"
    with pytest.raises(j9.NotJudgeable, match="sha256"):
        j9.v0_sample(keys, same, stored, "0" * 64)
    vb = tmp_path / "vb_keys.json"
    vb.write_text(json.dumps([{**jobs[0], "setting": "VB"}]), encoding="utf-8")
    with pytest.raises(j9.NotJudgeable, match="not of V0"):
        j9.v0_sample(vb, same, stored, sha)


def test_run_v5_v0_sample_batch_takes_v0_main_jobs_only(tmp_path) -> None:
    keys = tmp_path / "keys.json"
    keys.write_text(json.dumps({"jobs": _v0_jobs(2)}), encoding="utf-8")
    assert run_v5.j9_v0_sample_jobs(keys) == _v0_jobs(2)
    keys.write_text(json.dumps([{**_v0_jobs(1)[0], "setting": "VB"}]), encoding="utf-8")
    with pytest.raises(SystemExit, match="no V0 job"):
        run_v5.j9_v0_sample_jobs(keys)
    with pytest.raises(SystemExit):
        run_v5._parse_args(["j9_v0_sample"])  # the batch needs --jobs-file
    with pytest.raises(SystemExit):
        run_v5._parse_args(["main", "--jobs-file", str(keys)])  # and only it takes one


def test_check_rows_refuses_other_jobs_errors_and_settings() -> None:
    rows = [{"job": job} for job in run_v5.j9_main_jobs()]
    j9.check_rows(rows)
    with pytest.raises(j9.NotJudgeable, match="not the j9_main jobs"):
        j9.check_rows(rows[1:])
    with pytest.raises(j9.NotJudgeable, match="error lines"):
        j9.check_rows([{**rows[0], "error": "x"}, *rows[1:]])


def test_status_order() -> None:
    base = {"no_reference": {}, "not_judgeable_items": [], "vb_fail_items": 0, "L-a": [],
            "L-b": [], "stops": [], "J-P3": {"status": "pass"}}
    assert j9._status(base) == "pass"
    assert j9._status({**base, "vb_fail_items": 1}) == "failed"
    assert j9._status({**base, "L-a": [{}]}) == "failed"
    assert j9._status({**base, "J-P3": {"status": "H-7"}}) == "failed"
    assert j9._status({**base, "J-P3": {"status": "setting_defect"}, "stops": [{}]}) == (
        "setting_defect")
    assert j9._status({**base, "J-P3": {"status": "no_judged_runs"}}) == "not_judgeable"
    assert j9._status({**base, "no_reference": {"x": [["R1", 0]]}}) == "not_judgeable"


@pytest.mark.skipif(not MAIN_JSONL.is_file(), reason="stored v5/main.jsonl not present")
def test_judge_end_to_end_on_stored_lines(tmp_path, monkeypatch, capsys) -> None:
    """The stored VB / LS lines renamed VBJ / LSJ are exactly the j9_main jobs; the judge runs
    the 436.8 tables with the setting map (counts only)."""
    rename = {"VB": "VBJ", "LS1": "LSJ1", "LS2": "LSJ2", "LS3": "LSJ3", "LS4": "LSJ4"}
    wanted = {run_v5.job_key(job) for job in run_v5.j9_main_jobs()}
    rows = []
    for line in MAIN_JSONL.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        setting = row["job"].get("setting")
        if setting in rename:
            row["job"] = {**row["job"], "setting": rename[setting]}
            if run_v5.job_key(row["job"]) in wanted:
                rows.append(row)
    rows_path = _write_rows(tmp_path / "j9_main.jsonl", rows)
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    out = tmp_path / "report.json"
    sha = hashlib.sha256(MAIN_JSONL.read_bytes()).hexdigest()
    code = j9.main(["judge", "--rows", str(rows_path), "--v0", str(MAIN_JSONL), "--v0-sha256",
                    sha, "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert code in (0, 1, 2) and report["status"] in ("pass", "failed", "setting_defect",
                                                      "not_judgeable")
    assert report["rows"] == len(run_v5.j9_main_jobs())
    assert report["J_vs_V0"]["VB"]["runs"] == 100 and report["no_reference"] == {}
    assert {report["LS_vs_VB"][s]["runs"] for s in ("LS1", "LS2", "LS3", "LS4")} == {72}
    assert all(i["item"] != "J-P3" for i in report["J_vs_V0"]["VB"]["items"])
    assert "rev6" in report["J-P3"] or report["J-P3"]["status"] in ("setting_defect",
                                                                    "no_p3_runs")
