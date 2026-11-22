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
    # 2-10: a differing hash with a missing line is a failure, the problem kept
    differing_and_missing = _write_rows(tmp_path / "dm.jsonl",
                                        [{"job": jobs[0], "commands_sha256": "9" * 64}])
    report = j9.v0_sample(keys, differing_and_missing, stored, sha)
    assert report["status"] == "differs" and report["problems"]
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


def _status_of(**changes) -> str:
    report = {"no_reference": {}, "not_judgeable_items": [], "vb_fail_items": 0, "L-a": [],
              "L-b": [], "L-c": [], "stops": [], "identity_defects": [],
              "r15_worsening": {"failures": []}, "S8": {"failures": []},
              "J_vs_V0": {"VB": {"runs": 100}},
              "J-P3": {"status": "pass", "status_by_revision": {"4": "no_p3_runs",
                                                                "6": "pass"}}}
    report.update(changes)
    report["status_basis"] = j9.status_basis(report)
    return j9._status(report)


def test_status_order() -> None:
    """Erratum 2 2-10: failed > setting_defect > not_judgeable > pass."""
    assert _status_of() == "pass"  # an empty revision 4 side is no reason
    assert _status_of(vb_fail_items=1) == "failed"
    assert _status_of(**{"L-a": [{}]}) == "failed"
    assert _status_of(**{"L-c": [{}]}) == "failed"
    assert _status_of(**{"J-P3": {"status": "H-7"}}) == "failed"
    assert _status_of(**{"J-P3": {"status": "setting_defect",
                                  "status_by_revision": {"6": "H-7"}}}) == "failed"
    assert _status_of(**{"J-P3": {"status": "setting_defect"}}, stops=[{}]) == "failed"
    assert _status_of(**{"J-P3": {"status": "setting_defect"}}) == "setting_defect"
    assert _status_of(identity_defects=[{}], not_judgeable_items=[{}]) == "setting_defect"
    assert _status_of(**{"J-P3": {"status": "no_judged_runs"}}) == "not_judgeable"
    assert _status_of(no_reference={"x": [["R1", 0]]}) == "not_judgeable"
    assert _status_of(**{"J_vs_V0": {"VB": {"runs": 0}}}) == "not_judgeable"
    assert _status_of(vb_fail_items=1, no_reference={"x": [["R1", 0]]}) == "failed"
    assert _status_of(vb_fail_items=1, **{"J-P3": {"status": "no_p3_runs"}}) == "failed"


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


def test_s8_stop_value_none_is_not_judgeable() -> None:
    """Re-audit warning 3: a criteria 6 stop value None is never a silent pass."""
    row = _s8_row("VB", "eps 0.0")
    row["s8"] = {"margin_at_stop_kN": None, "max_after_stop_kN": 10.0}
    record = j9.s8_items({"VB": [row]})
    assert [item["item"] for item in record["not_judgeable"]] == ["F-5"]
    assert "margin_at_stop_kN" in record["not_judgeable"][0]["detail"]


def test_limit_cycle_and_r15_rules() -> None:
    rows_by = {"V0": [{"group": "R1", "n_rev": 10}],
               "LS1": [{"group": "R1", "row": "R1", "phase": "eps 0.0", "n_rev": 20}],
               "LS2": [{"group": "R1", "row": "R1", "phase": "eps 0.0", "n_rev": 15}],
               "LS3": [{"group": "R9", "row": "R9", "phase": "eps 0.0", "n_rev": 15}]}
    found = j9.limit_cycle_suspects(rows_by)
    assert [s["setting"] for s in found["suspects"]] == ["LS1"]
    # re-audit warning 3: no V0 maximum of the group is not judgeable, not skipped
    assert [(i["setting"], i["item"]) for i in found["not_judgeable"]] == [("LS3", "L-c")]

    def r15(setting, phase, force_kN):
        return {"row": "R15", "group": "R15", "phase": phase, "setting": setting,
                "is_event": True, "F_after_W_min_kN": force_kN, "F_after_event": force_kN}

    worse = {"V0": [r15("V0", "a", -0.2), r15("V0", "b", -0.7)],
             "VB": [r15("VB", "a", -3.0), r15("VB", "b", -3.5)]}
    assert j9.r15_worsening(worse)["failures"]
    within = {"V0": worse["V0"], "VB": [r15("VB", "a", -0.3), r15("VB", "b", -0.6)]}
    assert not j9.r15_worsening(within)["failures"]
    assert j9.r15_not_judgeable(j9.r15_worsening(within)) == []


def test_r15_without_pairs_or_values_is_not_judgeable() -> None:
    """Re-audit H-1: "no R15 pair" and "판정 불가" are not-judgeable items, never a pass."""
    none_pair = j9.r15_worsening({"V0": [], "VB": []})
    assert none_pair["state"] == "no R15 pair"
    assert [i["item"] for i in j9.r15_not_judgeable(none_pair)] == ["J2"]
    v0 = _r15_event("V0", "a", gates=[], force_kN=-0.2)
    missing = j9.r15_worsening({"V0": [v0, _r15_event("V0", "b", gates=[], force_kN=-0.7)],
                                "VB": [_r15_event("VB", "a", gates=[], force_kN=None),
                                       _r15_event("VB", "b", gates=[], force_kN=-0.6)]})
    assert missing["state"] == "판정 불가" and missing["failures"] == []
    (item,) = j9.r15_not_judgeable(missing)
    assert item["kind"] == "not_judgeable" and "판정 불가" in item["detail"]


def _r15_event(setting: str, phase: str, *, gates: list[str], force_kN: float | None,
               t_back: float | None = 30.0) -> dict:
    return {"row": "R15", "group": "R15", "phase": phase, "setting": setting, "is_event": True,
            "gates": gates, "F_after_W_min_kN": force_kN, "F_after_event": force_kN,
            "t_back": t_back, "att_end": 0.05, "p_move_ev": 150.0, "final": "ready",
            "t_ready": 20.0}


def _steady(setting: str, phase: str, row: str = "R1", **values) -> dict:
    return {"row": row, "group": row, "phase": phase, "setting": setting, "is_event": False,
            "class": "pass", "t_ready": 30.0, "att_last5": 0.05, "p_move": 100.0,
            "F_after": 20.0, "final": "ready", "case_floor": [0.0, 0.0], **values}


def test_baseline_failures_of_every_pair() -> None:
    """Re-audit H-3 (2-9.3 210): every pair's reference failures with the judged row's state
    and the None reasons; R15 J2 of VBJ against V0 stays with the worsening rule."""
    rows_by = {"V0": [_r15_event("V0", "a", gates=["min_force"], force_kN=-0.2, t_back=None),
                      _r15_event("V0", "b", gates=["min_force"], force_kN=-0.7),
                      _steady("V0", "a", att_last5=None), _steady("V0", "b", p_move=None)],
               "VB": [_r15_event("VB", "a", gates=["min_force"], force_kN=-0.3),
                      _r15_event("VB", "b", gates=[], force_kN=-0.6),
                      _steady("VB", "a", att_last5=0.5), _steady("VB", "b", final="fault")],
               "LS1": [_steady("LS1", "a"), _steady("LS1", "b", row="R2")]}
    record = j9.baseline_failures(rows_by)
    assert record["counted"] == 0
    listed = [(i["row"], i["phase"], i["item"], i["reference_state"], i["setting_state"])
              for i in record["J_vs_V0"]]
    assert listed == [("R15", "a", "J1", "fail", "fail"), ("R15", "a", "J5", "fail", "pass"),
                      ("R15", "b", "J1", "fail", "pass"), ("R1", "a", "J6", "fail", "fail"),
                      ("R1", "b", "J10", "undetermined", "pass")]
    missing = [i for i in record["J_vs_V0"] if i["value_missing"]]
    assert [i["reason"] for i in missing] == ["t_back None", "att_last5 None", "p_move None"]
    vb_a = next(i for i in record["LS_vs_VB"] if i["phase"] == "a")
    assert (vb_a["reference"], vb_a["item"], vb_a["setting_state"]) == ("VB", "J6", "pass")
    assert record["count"] == len(record["J_vs_V0"]) + len(record["LS_vs_VB"])
    assert record["value_missing_count"] == 3


def test_own_item_failures_non_event_row() -> None:
    row = {"row": "S1", "is_event": False, "class": "fault", "t_ready": None, "att_last5": 0.3,
           "p_move": 190.0, "F_after": 5.0, "final": "fault"}
    items = [i["item"] for i in j9.own_item_failures(row)]
    assert items == ["J1", "J3", "J6", "J10", "J2", "J4"]
    passing = {**row, "class": "pass", "t_ready": 30.0, "att_last5": 0.1, "p_move": 100.0,
               "F_after": 20.0, "final": "ready"}
    assert j9.own_item_failures(passing) == []


def test_own_item_j3_rigid_record_rows() -> None:
    """Re-audit warning 1: the D-11 rigid record branch (FLAG on the row, ``case_floor``)."""
    flat = _steady("V0", "a", t_ready=95.0)
    assert [(i["item"], i["state"]) for i in j9.own_item_failures(flat)] == [("J3", "flag")]
    slope = _steady("V0", "a", t_ready=95.0, case_floor=[2.0, 0.0])
    assert j9.own_item_failures(slope) == []
    no_floor = _steady("V0", "a", case_floor=None)
    (entry,) = j9.own_item_failures(no_floor)
    assert (entry["item"], entry["state"], entry["reason"]) == ("J3", "record",
                                                                "case_floor_deg None")


# ------------------------------------------------------------------------------ H-2 identity
REV6_TAG = "final_C4G2_P3W_LAS_K1"
WITNESS_OPTIONS = {"extend_start_tracked": True, "extend_start_hold": True,
                   "extend_start_witness": True}


def _rev6_record(breaches: int = 0) -> dict:
    return {"rule_revision": 6, "spec_edition": "fe6f5844",
            "carry_end_rule": "inherit_when_gate_shut", "retract_start_rule": "with_tracker",
            "identity_consistent": True, "sensor_grade": "normal",
            "jp3a_breach_reads": [breaches, 0, 0, 0], "jp3b_breach_over_tol_reads": [0] * 4,
            "jp3c_breach_reads": [0] * 4}


def _line(setting: str, metric: dict, **changes) -> dict:
    line = {"job": {"setting": setting, "case": metric["row"], "phase": metric["phase"]},
            "controller_tag": REV6_TAG, "hydraulic_options": dict(WITNESS_OPTIONS),
            "hydraulics_record": {"extend_bound_check": _rev6_record()},
            "head_only_declared": False, "_metric": metric}
    line.update(changes)
    return line


def test_line_identity_problems() -> None:
    from outrigger_sim.hydraulics.v5_options import extend_start_revision_of_tag

    assert extend_start_revision_of_tag(REV6_TAG) == 6
    metric = _steady("VB", "a")
    assert j9.line_identity_problems(_line("VBJ", metric)) == []
    assert j9.line_identity_problems(_line("VBJ", metric, run_extend_start_revision=6)) == []
    cases = {"tag": {"controller_tag": "final_C4G2_P3H_LAS_K1"},
             "no_tag": {"controller_tag": None},
             "revision_key": {"run_extend_start_revision": 5},
             "options": {"hydraulic_options": {**WITNESS_OPTIONS, "extend_start_witness": False}},
             "rule_revision": {"hydraulics_record": {"extend_bound_check": {
                 **_rev6_record(), "rule_revision": 5}}},
             "spec_edition": {"hydraulics_record": {"extend_bound_check": {
                 **_rev6_record(), "spec_edition": "8be9de22"}}}}
    for name, change in cases.items():
        assert len(j9.line_identity_problems(_line("VBJ", metric, **change))) == 1, name
    no_record = _line("VBJ", metric, hydraulics_record={"extend_bound_check": None})
    assert j9.line_identity_problems(no_record) == []  # J-P3's run-case table


# ------------------------------------------------------- synthetic judge (2-10, warning 5)
def _synthetic_world(*, vb_r1_class: str = "pass", vb_r15_force: float | None = -0.3,
                     extra_vb: bool = False, identity_change: dict | None = None):
    """V0 / VBJ / LSJ1 .. 4 rows R1 (steady) and R15 (event), phases a / b; VBJ / LSJ lines
    are clean rev 6 (J-P3 pass on its revision 6 side, revision 4 side empty)."""
    v0 = [_steady("V0", p) for p in "ab"] + [
        _r15_event("V0", "a", gates=[], force_kN=-0.2),
        _r15_event("V0", "b", gates=[], force_kN=-0.7)]
    vb = [_steady("VB", "a", **{"class": vb_r1_class}), _steady("VB", "b"),
          _r15_event("VB", "a", gates=[], force_kN=vb_r15_force),
          _r15_event("VB", "b", gates=[], force_kN=-0.6)]
    if extra_vb:
        vb.append(_steady("VB", "a", row="R2"))
    lines = [_line("VBJ", metric) for metric in vb]
    for index in range(1, 5):
        lines += [_line(f"LSJ{index}", _steady(f"LS{index}", p)) for p in "ab"]
    if identity_change:
        lines[0].update(identity_change)
    common = {"n_rev": 3, "post_clip": [0, 0, 0, 0], "lwa": {}, "bad": [], "bad_436": [],
              "fallback_436": [], "events_capped": False, "events_full": [], "sa4": None,
              "pressure": {}, "controller_tag": None, "head_only_declared": True,
              "j_p3_view": None, "rod_reading": None, "t4h_lookup": {}, "bound_check": None}
    for metric in [*v0, *(line["_metric"] for line in lines)]:
        for key, value in common.items():
            metric.setdefault(key, value)
    return lines, [{"job": {"setting": "V0"}, "_metric": metric} for metric in v0]


def _run_synthetic(tmp_path, monkeypatch, capsys, lines, v0_lines, *, j_p3_rows=None):
    import judge_stage1_4368 as path1

    monkeypatch.setattr(j9, "check_rows", lambda rows: None)
    monkeypatch.setattr(j9, "stored_v0_rows", lambda path, sha: v0_lines)
    monkeypatch.setattr(j9, "_metric_rows", lambda rows, folders, relabel: [
        dict(row["_metric"]) for row in rows])
    monkeypatch.setattr(path1, "rod_reading", lambda row, folders: True)
    if j_p3_rows is not None:
        monkeypatch.setattr(j9, "j_p3_rows", j_p3_rows)
    rows_path = _write_rows(tmp_path / "j9_main.jsonl", lines)
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    out = tmp_path / "report.json"
    code = j9.main(["judge", "--rows", str(rows_path), "--v0", str(rows_path),
                    "--v0-sha256", SHA, "--out", str(out)])
    last = json.loads(capsys.readouterr().out.splitlines()[-1])
    return code, last, json.loads(out.read_text(encoding="utf-8"))


def test_synthetic_rev6_only_passes(tmp_path, monkeypatch, capsys) -> None:
    """Re-audit warning 5: rev 6 lines only - J-P3 pass (revision 4 side empty is no reason)
    and the j9_main judge pass, exit 0."""
    code, last, report = _run_synthetic(tmp_path, monkeypatch, capsys, *_synthetic_world())
    assert code == 0 and last["status"] == "pass", report["status_basis"]
    assert report["J-P3"]["status"] == "pass"
    assert report["J-P3"]["status_by_revision"] == {"4": "no_p3_runs", "6": "pass"}
    assert report["J-P3"]["rev6"]["runs_judged"] == 12  # VBJ 4 + LSJ1 .. 4 x 2
    assert report["identity_defects"] == [] and report["not_judgeable_items"] == []
    assert report["r15_worsening"]["pairs"] == 2


def test_synthetic_failure_with_no_reference_is_exit_1(tmp_path, monkeypatch, capsys) -> None:
    lines, v0 = _synthetic_world(vb_r1_class="fault", extra_vb=True)
    code, last, report = _run_synthetic(tmp_path, monkeypatch, capsys, lines, v0)
    assert code == 1 and last["status"] == "failed"
    assert report["no_reference"] and report["vb_fail_items"] == 1
    assert report["status_basis"]["failures"] and report["status_basis"]["not_judgeable"]


def test_synthetic_r15_not_judgeable_alone_is_exit_2(tmp_path, monkeypatch, capsys) -> None:
    lines, v0 = _synthetic_world(vb_r15_force=None)
    code, last, report = _run_synthetic(tmp_path, monkeypatch, capsys, lines, v0)
    assert code == 2 and last["status"] == "not_judgeable", report["status_basis"]
    assert [i["item"] for i in report["not_judgeable_items"]] == ["J2"]
    assert report["status_basis"]["failures"] == []


def test_synthetic_jp3_without_rows_and_a_failure_is_exit_1(tmp_path, monkeypatch,
                                                            capsys) -> None:
    lines, v0 = _synthetic_world(vb_r1_class="fault")
    code, last, report = _run_synthetic(tmp_path, monkeypatch, capsys, lines, v0,
                                        j_p3_rows=lambda rows, folders: [])
    assert code == 1 and last["status"] == "failed"
    assert report["J-P3"]["status"] == "no_p3_runs"
    assert "J-P3 no_p3_runs" in report["status_basis"]["not_judgeable"]


def test_synthetic_identity_defect_is_a_setting_defect(tmp_path, monkeypatch, capsys) -> None:
    """H-2: a VBJ line of another tag base: setting_defect (exit 2) when nothing fails."""
    lines, v0 = _synthetic_world(identity_change={"controller_tag": "final_C4G2_P3H_LAS_K1"})
    code, last, report = _run_synthetic(tmp_path, monkeypatch, capsys, lines, v0)
    assert code == 2 and last["status"] == "setting_defect"
    assert len(report["identity_defects"]) == 1


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
