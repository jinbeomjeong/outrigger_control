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


def test_v0_sample_keys_first_and_last_line_of_every_row(tmp_path, monkeypatch) -> None:
    """2-9.1: rows without the phase fields (the G4 twins one row), first and last line."""
    jobs = [job for job in run_v5.batch_jobs("main") if job["setting"] == "V0"]
    stored = _write_rows(tmp_path / "main.jsonl", [{"job": {**job, "mask": 3},
                                                    "commands_sha256": SHA} for job in jobs])
    sha = hashlib.sha256(stored.read_bytes()).hexdigest()
    document = j9.v0_sample_keys(stored, sha)
    assert document["rows"] == 24 and len(document["jobs"]) <= 48
    assert all("mask" not in job for job in document["jobs"])
    twin_jobs = [job for job in jobs if job.get("twin")]
    assert len({j9._row_identity(job) for job in twin_jobs}) == 1  # twin is not an identity
    by_row: dict[str, list[dict]] = {}
    for job in jobs:
        by_row.setdefault(j9._row_identity(job), []).append(job)
    expected = [job for group in by_row.values()
                for job in ([group[0]] if len(group) == 1 else [group[0], group[-1]])]
    assert document["jobs"] == expected
    twins = [job for job in document["jobs"] if job.get("twin")]
    assert len(twins) == 2  # the G4 width grid is one row: its first and last line
    monkeypatch.setattr(j9, "V0_SAMPLE_ROWS", 23)
    with pytest.raises(j9.NotJudgeable, match="24 V0 rows"):
        j9.v0_sample_keys(stored, sha)


def _s8_row(setting: str, phase: str, *, margin=1.0, after=10.0, ready=None) -> dict:
    return {"row": "S8", "phase": phase, "setting": setting, "t_ready": ready,
            "events_full": [(10.0, "WARN_LIFT_STROKE_LIMITED:FL"),
                            (10.0, "FAULT_LIFT_STROKE_LIMIT:soil:FL")],
            "events_capped": False, "sa4": {"F_min_after_stop_N": [2e4] * 4,
                                            "lift_after_stop_ms": [0, 0, 0, 0]},
            "F_after": 20.0, "p_move": 100.0, "pressure": {"saturation_leg_chunks": 0},
            "s8": {"margin_at_stop_kN": margin, "max_after_stop_kN": after}}


def test_s8_f5_record_sa4_failure_and_stop() -> None:
    record = j9.s8_items({"VB": [_s8_row("VB", "eps 0.0", margin=-1.0)]})
    assert record["f5_records"] and not record["failures"] and not record["stops"]
    record = j9.s8_items({"VB": [_s8_row("VB", "eps 0.0", margin=-7.0)]})
    assert record["stops"][0]["item"] == "F-5"
    record = j9.s8_items({"VB": [_s8_row("VB", "eps 0.0", after=14.3)]})
    assert record["stops"]
    record = j9.s8_items({"LS1": [_s8_row("LS1", "eps 0.0", ready=50.0)]})
    assert record["failures"][0]["detail"] == ["no_ready"]


def test_limit_cycle_and_r15_rules() -> None:
    rows_by = {"V0": [{"group": "R1", "n_rev": 10}],
               "LS1": [{"group": "R1", "row": "R1", "phase": "eps 0.0", "n_rev": 20}],
               "LS2": [{"group": "R1", "row": "R1", "phase": "eps 0.0", "n_rev": 15}]}
    assert [s["setting"] for s in j9.limit_cycle_suspects(rows_by)] == ["LS1"]

    def r15(setting, phase, force_kN):
        return {"row": "R15", "group": "R15", "phase": phase, "setting": setting,
                "is_event": True, "F_after_W_min_kN": force_kN, "F_after_event": force_kN}

    worse = {"V0": [r15("V0", "a", -0.2), r15("V0", "b", -0.7)],
             "VB": [r15("VB", "a", -3.0), r15("VB", "b", -3.5)]}
    assert j9.r15_worsening(worse)["failures"]
    within = {"V0": worse["V0"], "VB": [r15("VB", "a", -0.3), r15("VB", "b", -0.6)]}
    assert not j9.r15_worsening(within)["failures"]
    assert j9.r15_worsening({"V0": [], "VB": []})["state"] == "no R15 pair"


def _r15_event(setting: str, phase: str, *, gates: list[str], force_kN: float,
               t_back: float | None = 30.0) -> dict:
    return {"row": "R15", "group": "R15", "phase": phase, "setting": setting, "is_event": True,
            "gates": gates, "F_after_W_min_kN": force_kN, "F_after_event": force_kN,
            "t_back": t_back, "att_end": 0.05, "p_move_ev": 150.0, "final": "ready",
            "t_ready": 20.0}


def test_r15_baseline_failures_leave_j2_to_the_worsening_rule() -> None:
    """Erratum 2 final 2-9.3: V0's R15 failures other than J2 are baseline failures (records);
    J2 is the worsening rule's; a VBJ pass on the item is kept as ``vbj_also_fails`` False."""
    rows_by = {"V0": [_r15_event("V0", "a", gates=["min_force"], force_kN=-0.2, t_back=None),
                      _r15_event("V0", "b", gates=["min_force"], force_kN=-0.7)],
               "VB": [_r15_event("VB", "a", gates=["min_force"], force_kN=-0.3),
                      _r15_event("VB", "b", gates=[], force_kN=-0.6)]}
    listed = j9.r15_baseline_failures(rows_by)
    assert [(i["phase"], i["item"], i["vbj_also_fails"]) for i in listed] == [
        ("a", "J1", True), ("a", "J5", False), ("b", "J1", False)]
    assert all(i["kind"] == "baseline_failure" and i["item"] != "J2" for i in listed)
    assert j9.r15_baseline_failures({"V0": rows_by["V0"], "VB": []}) == []
    other = {"V0": [{**rows_by["V0"][0], "row": "R14"}], "VB": [{**rows_by["VB"][0],
                                                                  "row": "R14"}]}
    assert j9.r15_baseline_failures(other) == []
    assert j9.r15_worsening(rows_by)["failures"] == []


def test_own_item_failures_non_event_row() -> None:
    row = {"row": "S1", "is_event": False, "class": "fault", "t_ready": None, "att_last5": 0.3,
           "p_move": 190.0, "F_after": 5.0, "final": "fault"}
    items = [i["item"] for i in j9.own_item_failures(row)]
    assert items == ["J1", "J3", "J6", "J10", "J2", "J4"]
    passing = {**row, "class": "pass", "t_ready": 30.0, "att_last5": 0.1, "p_move": 100.0,
               "F_after": 20.0, "final": "ready"}
    assert j9.own_item_failures(passing) == []


@pytest.mark.skipif(not MAIN_JSONL.is_file(), reason="stored v5/main.jsonl not present")
def test_v0_sample_keys_of_the_stored_file(tmp_path) -> None:
    sha = hashlib.sha256(MAIN_JSONL.read_bytes()).hexdigest()
    document = j9.v0_sample_keys(MAIN_JSONL, sha)
    assert (document["rows"], len(document["jobs"])) == (24, 48)
    keys = tmp_path / "keys.json"
    keys.write_text(json.dumps(document), encoding="utf-8")
    assert len(run_v5.j9_v0_sample_jobs(keys)) == 48


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
