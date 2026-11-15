"""436.8 Chrono path 1 bundle grades (``04_scripts/02_chrono/chrono_bundle_grade_4368.py``; rules
rev18 R18-2).

Synthetic inputs only (batch folders, manifest, ``chrono_rows_judge`` output, runner judge files,
``result.json``); the seal check reads the checkout's rules files. No Chrono run, no judgement.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHRONO_SCRIPTS = PROJECT_ROOT / "04_scripts" / "02_chrono"
RULES_DIR = PROJECT_ROOT / "06_analysis" / "02_control" / "verif_matrix"
GIT = "b9f5707d7f3f7a26230b25f4edbc1fec587ca612"
STAMP = "20261114_110925"


@pytest.fixture(scope="module")
def mod():
    sys.path.insert(0, str(CHRONO_SCRIPTS))
    try:
        return __import__("chrono_bundle_grade_4368")
    finally:
        sys.path.remove(str(CHRONO_SCRIPTS))


@pytest.fixture(scope="module", autouse=True)
def _rules_present(mod):
    names = list(mod.rows_judge.RULES_SEALS)
    if not all((RULES_DIR / n).is_file() for n in names):
        pytest.skip("sealed rules files not in this checkout")


# ------------------------------------------------------------------------------- fixture builder
def write_json(path: Path, doc: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def entry(case: str, criteria: str, engine: str, **extra: Any) -> dict[str, Any]:
    return {"case": case, "criteria_id": criteria, "r4368": {"engine": engine},
            "code_at_launch": {"git": {"head": GIT, "dirty": []}}, **extra}


class Bundle:
    """Synthetic batch, manifest, judge output and runner judge files of one bundle."""

    def __init__(self, root: Path, name: str):
        self.root = root
        self.name = name
        self.batch = root / "S9" / f"batch_V5-RESUME-K1-{name}_{STAMP}"
        self.runner_dir = root / "runner_judge"
        self.entries: list[dict[str, Any]] = []
        self.judged: list[dict[str, Any]] = []
        self.manifest_extra: list[str] = []
        self.stops: list[dict[str, str]] = []

    def add_scm(self, e: dict[str, Any], result: dict[str, Any], items: dict[str, Any],
                **judged: Any) -> None:
        self.entries.append(e)
        result.setdefault("code_state", {"git_at_start": {"head": GIT}})
        write_json(self.batch / e["case"] / "result.json", result)
        self.judged.append({"case": e["case"], "dir": str(self.batch / e["case"]),
                            "items": items, **judged})

    def add_rigid(self, e: dict[str, Any], runner_rows: list[dict[str, Any]],
                  items: dict[str, Any], prefix: str, suffix: str = "verify_S8C") -> None:
        self.entries.append(e)
        folder = self.root / "S8" / f"tag_{e['case']}_{STAMP}"
        write_json(folder / e["case"] / "result.json", {"settings": {}})
        self.judged.append({"case": e["case"], "dir": str(folder / e["case"]), "items": items})
        rows = [{"case": e["case"], **r} for r in runner_rows]
        write_json(self.runner_dir / f"{prefix}_{e['case']}.{suffix}.json",
                   {"meta": {"batch": str(folder)}, "rows": rows})

    def write(self) -> dict[str, Path]:
        write_json(self.batch / "batch.json", {"batch": f"V5-RESUME-K1-{self.name}",
                                               "cases": self.entries})
        cases = [e["case"] for e in self.entries] + self.manifest_extra
        manifest = write_json(self.root / "manifest.json", {"batches": {
            f"V5-RESUME-K1-{self.name}": {"rows": [{"case": c} for c in cases]}}})
        judge = write_json(self.root / "judge.json", {
            "seals": {"ok": True}, "deviates_from_rev6": None,
            "commit_identity_R11_4": {"git_at_start": GIT}, "rows": self.judged,
            "stops": self.stops, "tool": "synthetic"})
        return {"manifest": manifest, "judge": judge}


def run(mod, bundle: Bundle, tmp_path: Path, name: str, *extra: str) -> tuple[int, dict]:
    paths = bundle.write()
    out = tmp_path / f"{name}.json"
    argv = ["grade", "--bundle", name, "--git-at-start", GIT, "--batch", str(bundle.batch),
            "--manifest", str(paths["manifest"]), "--rules-dir", str(RULES_DIR), "--out", str(out),
            *extra]
    if name in mod.GRADED_BUNDLES:
        argv += ["--rows-judge", str(paths["judge"]), "--runner-judge-dir",
                 str(bundle.runner_dir)]
    code = mod.main(argv)
    return code, json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}


def runner_pass_rows() -> list[dict[str, Any]]:
    return [{"item": "run", "passed": True, "kind": "function"},
            {"item": "4 max moving pressure", "passed": True, "value": 98.0, "kind": "function"},
            {"item": "4 saturation steps", "passed": True, "value": 0, "kind": "function"},
            {"item": "C1 D8 min true rod force (raw 1 ms) >= F_min + 5 kN", "passed": True,
             "value": 56.0, "kind": "judged"},
            {"item": "F4 record", "passed": None, "kind": "record"}]


def rigid_items(*, moving_bar: float = 98.0, c1: str = "pass", j_p3: str = "pass"
                ) -> dict[str, Any]:
    return {"moving_pressure_D-32": {"status": "judged", "max_moving_bar": moving_bar,
                                     "saturated_samples": 0},
            "C1_R40": {"status": "judged", "verdict": c1, "raw_min_N": 56000.0},
            "J-P3_R8-2": {"status": j_p3, "breach_reads": 0},
            "J11_R8-3": {"status": "no_fallback_leg"}}


def p3b_ok(**checks: Any) -> dict[str, Any]:
    base = {"P3-1_crawler_zero_after_ready": True, "P3-2_late_loc_reapproach": False,
            "P3-2_late_loc_revoked": False, "P3-4_verdict": "pass", "P3-5_within": True,
            "P3-6_within": True, "P3-7_within": True, "P3-9_flags": 0}
    return {"checks": {**base, **checks}}


def scm_items(**over: Any) -> dict[str, Any]:
    items = {"P3-1_recontact_D-36": {"pass": True, "flags": []},
             "P3-2_D-37_D-38": {"within": True},
             "P3-3_after_t_D": {"within": True, "F_min_after_departure_N": 50000.0},
             "P3-8_D-34_D-35": {"verdict": "pass", "fault": False, "flags": []},
             "J-P3_R8-2": {"status": "pass", "breach_reads": 0},
             "J11_R8-3": {"status": "no_fallback_leg"},
             "SGS_427_9_D-26": {"applies": None}}
    items.update(over)
    return items


def c1_bundle(tmp_path: Path) -> Bundle:
    b = Bundle(tmp_path, "C1")
    for i in range(6):
        b.add_rigid(entry(f"D1C2_{i}", "C-1", "L2b_NSC", d1_id=f"C2-0{i}", d1_role="judge"),
                    runner_pass_rows(), rigid_items(), "C1")
    for i in range(4):
        b.add_rigid(entry(f"D1C1_{i}", "C-1", "L1R", d1_id=f"C1-1{i}", d1_role="record"),
                    runner_pass_rows(), rigid_items(), "C1", "verify_S6C")
    return b


# ------------------------------------------------------------------------------------- C-1 rigid
def test_c1_pass_and_record_rows(mod, tmp_path):
    code, doc = run(mod, c1_bundle(tmp_path), tmp_path, "C-1")
    assert code == 0
    grade = doc["bundle_grade"]
    assert grade["grade"] == "pass" and grade["status"] == "통과"
    assert grade["judged_rows"] == 6 and grade["record_rows"] == 4
    row = doc["rows"][0]
    applied = [o["item"].split(" ")[0] for o in row["overrides"] if o["applied"]]
    assert applied == ["4", "4", "C1"]  # moving pressure, saturation, C1 R40 replaced
    assert doc["row_count_S15"]["ok"] is True


def test_c1_recomputed_item_overrides_runner(mod, tmp_path):
    b = c1_bundle(tmp_path)
    b.judged[0]["items"] = rigid_items(moving_bar=181.0)  # runner said 98 bar, pass
    code, doc = run(mod, b, tmp_path, "C-1")
    row = doc["rows"][0]
    moving = next(i for i in row["items"] if i["item"] == "4 max moving pressure")
    assert moving["verdict"] == "fail" and moving["source"] == "recomputed D-32"
    log = next(o for o in row["overrides"] if o["item"] == "4 max moving pressure")
    assert log["runner"] == {"verdict": "pass", "value": 98.0}
    assert log["recomputed"] == {"verdict": "fail", "value": 181.0}
    assert row["grade"] == "fail" and doc["bundle_grade"]["status"] == "미달"
    assert code == 0  # a fail is a result, not a stop


def test_record_row_failure_is_reported_not_graded(mod, tmp_path):
    b = c1_bundle(tmp_path)
    b.judged[6]["items"] = rigid_items(c1="fail")  # C1-10 record row
    _, doc = run(mod, b, tmp_path, "C-1")
    assert doc["bundle_grade"]["status"] == "통과"
    assert doc["bundle_grade"]["record_rows_reported"] == [{"case": "D1C1_0", "grade": "fail"}]


def test_missing_runner_judge_file_is_not_judgeable(mod, tmp_path):
    b = c1_bundle(tmp_path)
    b.write()
    (b.runner_dir / "C1_D1C2_2.verify_S8C.json").unlink()
    b.write = lambda: {"manifest": tmp_path / "manifest.json", "judge": tmp_path / "judge.json"}
    _, doc = run(mod, b, tmp_path, "C-1")
    row = next(r for r in doc["rows"] if r["case"] == "D1C2_2")
    assert row["grade"] == "not_judgeable"
    assert row["missing_inputs"] == ["runner judge verify_S8C"]
    assert doc["bundle_grade"]["status"] == "판정 불가"


def test_missing_judge_row_is_not_judgeable(mod, tmp_path):
    b = c1_bundle(tmp_path)
    b.judged.pop(1)
    _, doc = run(mod, b, tmp_path, "C-1")
    row = next(r for r in doc["rows"] if r["case"] == "D1C2_1")
    assert row["grade"] == "not_judgeable" and "chrono_rows_judge row" in row["missing_inputs"]


def test_runner_hold_and_j_p3_h7_stop(mod, tmp_path):
    b = c1_bundle(tmp_path)
    b.judged[0]["items"] = rigid_items(c1="pass")
    b.judged[0]["items"]["C1_R40"] = {"status": "not_judgeable", "hold": True}
    b.stops = [{"case": "D1C2_0", "reason": "R40-2 hold (not judgeable, ask)"},
               {"case": "other_bundle_row", "reason": "not this bundle"}]
    code, doc = run(mod, b, tmp_path, "C-1")
    assert code == 1
    assert doc["stops"] == [{"case": "D1C2_0", "reason": "R40-2 hold (not judgeable, ask)"}]
    assert doc["bundle_grade"]["grade"] is None
    assert doc["bundle_grade"]["grade_without_stop"] == "not_judgeable"


def test_runner_folder_mismatch_is_input_error(mod, tmp_path):
    b = c1_bundle(tmp_path)
    b.write()
    path = b.runner_dir / "C1_D1C2_0.verify_S8C.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["meta"]["batch"] = str(tmp_path / "S8" / "another_folder")
    path.write_text(json.dumps(data), encoding="utf-8")
    b.write = lambda: {"manifest": tmp_path / "manifest.json", "judge": tmp_path / "judge.json"}
    code, _ = run(mod, b, tmp_path, "C-1")
    assert code == 2


# ------------------------------------------------------------------------------------- row count
def test_row_count_mismatch_is_s15_without_grade(mod, tmp_path):
    b = c1_bundle(tmp_path)
    b.entries.pop()
    b.judged.pop()
    code, doc = run(mod, b, tmp_path, "C-1")
    assert code == 1
    assert doc["row_count_S15"]["found"] == 9 and doc["row_count_S15"]["ok"] is False
    assert doc["bundle_grade"]["grade"] is None and "S-15" in doc["bundle_grade"]["reason"]
    assert any("S-15" in s["reason"] for s in doc["stops"])


def test_empty_bundle_gets_no_grade(mod, tmp_path):
    b = Bundle(tmp_path, "C3")
    code, doc = run(mod, b, tmp_path, "C-3")
    assert code == 1 and doc["rows"] == []
    assert doc["bundle_grade"]["grade"] is None


def test_row_not_in_manifest_is_s15(mod, tmp_path):
    b = c1_bundle(tmp_path)
    b.write()
    manifest = tmp_path / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["batches"]["V5-RESUME-K1-C1"]["rows"].pop(0)
    manifest.write_text(json.dumps(data), encoding="utf-8")
    b.write = lambda: {"manifest": manifest, "judge": tmp_path / "judge.json"}
    code, doc = run(mod, b, tmp_path, "C-1")
    assert code == 1 and doc["row_count_S15"]["not_in_manifest"] == ["D1C2_0"]


def test_assumed_rows_judge_output_is_refused(mod, tmp_path):
    b = c1_bundle(tmp_path)
    b.write()
    judge = tmp_path / "judge.json"
    data = json.loads(judge.read_text(encoding="utf-8"))
    data["deviates_from_rev6"] = {"C-1": "not_judgeable"}
    judge.write_text(json.dumps(data), encoding="utf-8")
    b.write = lambda: {"manifest": tmp_path / "manifest.json", "judge": judge}
    code, _ = run(mod, b, tmp_path, "C-1")
    assert code == 2


# ------------------------------------------------------------------------------------- C-2 / C-3
def soil_event(gates: dict[str, Any], *, fast: bool = False, stroke: float = 517.0,
               flags: list[str] | None = None) -> dict[str, Any]:
    return {"soil_event": {"judgement": {"gates": gates, "fast": fast, "flags": flags or [],
                                         "stroke_max_run_mm": stroke}}}


SLOW_GATES = {"E-1_no_lift": True, "E-3_Fmin_after_event": True, "E-4_window_350bar": True,
              "E-4_moving_180bar": True, "E-4_saturation0": True, "E-5_end_ready_att": True,
              "E-5_fault0": True, "E-5_stroke": True, "E-6_crawler": True,
              "E-7_recurrence": True}


def c2_bundle(tmp_path: Path, *, sgs_class: str = "stroke_limited_stop",
              event_gates: dict[str, Any] | None = None) -> Bundle:
    b = Bundle(tmp_path, "C2")
    for i, rid in enumerate(("C2-03", "C2-07")):
        b.add_rigid(entry(f"D1C2_roll{i}", "C-2", "L2b_NSC", d1_id=rid, d1_role="judge"),
                    runner_pass_rows(), rigid_items(), "C2")
    sgs = {"applies": True, "class": sgs_class, "conditions": {"1_soil_stop_first": True}}
    for rid in ("S-01", "S-02"):
        b.add_scm(entry(f"D1S_{rid}", "C-2", "SCM", d1_id=rid, d1_role="judge"),
                  {"p3b": p3b_ok(**{"P3-4_verdict": "fail", "P3-6_within": False})},
                  scm_items(**{"SGS_427_9_D-26": sgs}))
    b.add_scm(entry("D1PSC_base", "C-2", "SCM", d1_id="PSC-base-FL", d1_role="timing base",
                    d1_select="psc"), {"p3b": p3b_ok()}, scm_items())
    gates = SLOW_GATES if event_gates is None else event_gates
    b.add_scm(entry("D1PSC_cslow", "C-2", "SCM", d1_id="PSC-c-slow-FL",
                    d1_role="judge (426.3 E-1 .. E-7 + DSb75 record)", d1_select="psc"),
              {"p3b": p3b_ok(), **soil_event(gates)}, scm_items())
    return b


def test_c2_safe_stop_and_event_row(mod, tmp_path):
    code, doc = run(mod, c2_bundle(tmp_path), tmp_path, "C-2")
    assert code == 0
    rows = {r["case"]: r for r in doc["rows"]}
    assert rows["D1S_S-01"]["grade"] == "allowed_stop"  # P3-4 / P3-6 failures recorded only
    recorded = {i["item"]: i["verdict_recorded"] for i in rows["D1S_S-01"]["record_items"]
                if "verdict_recorded" in i}
    assert recorded["P3-4"] == "fail" and recorded["P3-6"] == "fail"
    assert rows["D1PSC_base"]["role"] == "record"
    event = rows["D1PSC_cslow"]
    assert event["grade"] == "pass"
    assert [i["item"] for i in event["items"]][:6] == ["E-1", "E-3", "E-4", "E-5", "E-6", "E-7"]
    assert doc["bundle_grade"]["allowed_stop_rows"] == ["D1S_S-01", "D1S_S-02"]
    assert doc["bundle_grade"]["status"] == "통과"


def test_c2_safe_stop_condition_false_is_fail(mod, tmp_path):
    _, doc = run(mod, c2_bundle(tmp_path, sgs_class="fail"), tmp_path, "C-2")
    assert {r["case"]: r["grade"] for r in doc["rows"]}["D1S_S-01"] == "fail"
    assert doc["bundle_grade"]["status"] == "미달"


def test_c2_event_row_missing_e_item_is_not_judgeable(mod, tmp_path):
    gates = {k: v for k, v in SLOW_GATES.items() if not k.startswith("E-7")}
    _, doc = run(mod, c2_bundle(tmp_path, event_gates=gates), tmp_path, "C-2")
    event = next(r for r in doc["rows"] if r["case"] == "D1PSC_cslow")
    assert event["grade"] == "not_judgeable"
    assert next(i for i in event["items"] if i["item"] == "E-7")["verdict"] == "not_judgeable"
    assert doc["bundle_grade"]["status"] == "판정 불가"


def test_fast_event_needs_e2(mod):
    gates = dict(SLOW_GATES)
    items = mod.soil_event_items(soil_event(gates, fast=True))
    e2 = next(i for i in items if i["item"] == "E-2")
    assert e2["verdict"] == "not_judgeable"
    flagged = mod.soil_event_items(soil_event({**gates, "E-2_adj_sum": True}, fast=True,
                                              flags=["E-6_event_transient_recontact"]))
    assert next(i for i in flagged if i["item"] == "E-6")["verdict"] == "flag"
    too_long = mod.soil_event_items(soil_event(gates, stroke=690.0))
    assert next(i for i in too_long if i["item"] == "stroke_le_684.8mm")["verdict"] == "fail"


def test_c3_g6_grade_with_p37(mod, tmp_path):
    b = Bundle(tmp_path, "C3")
    for rid, p37 in (("S-03", True), ("S-04", False)):
        b.add_scm(entry(f"D1S_G1_{rid}", "C-3", "SCM", d1_id=rid, d1_role="judge"),
                  {"p3b": p3b_ok(**{"P3-7_within": p37})}, scm_items(), grade="pass",
                  gates={"G6-1_crawler": "pass"})
    code, doc = run(mod, b, tmp_path, "C-3")
    grades = {r["row_id"]: r["grade"] for r in doc["rows"]}
    assert grades == {"S-03": "pass", "S-04": "fail"} and code == 0
    assert doc["bundle_grade"]["status"] == "미달"


# ------------------------------------------------------------------------------------- C-5
C5_SCM = ("P3b_J1_B_top_Fs4", "P3b_J1_B_top_Fs4_v0v", "P3b_J2_t180", "P3b_J2_t180_v0v",
          "S9SL_p0", "S9SL_p0_v0v", "seed26", "seed27", "seed28", "seed29", "seed26_flow")
C5_RIGID_EXTRA = ("E_G4_Fs4", "E_G4_Fs4_V0", "E_G4_Fs4_ph0.05", "E_G4_Fs4_ph0.05_V0",
                  "G1R_FS24_FL_top_o050_Fs0", "G1R_FS24_FL_top_o050_Fs0_V0")


def t45_row(case: str, over_t4: int = 0, *, t4_0: bool = True) -> dict[str, Any]:
    return {"case": case, "settings_equal": True, "t4_0": t4_0,
            "T4": {"over_0p6kN": over_t4}, "T5": {"over_0p6kN": 0}}


def c5_bundle(mod, tmp_path: Path) -> tuple[Bundle, Path]:
    b = Bundle(tmp_path, "C5")
    for case in (*mod.T45_CASES, *C5_RIGID_EXTRA):
        b.add_rigid(entry(case, "C-5", "L2b_NSC"), runner_pass_rows(), rigid_items(), "C5")
    for case in C5_SCM:
        b.add_scm(entry(case, "C-5", "SCM"), {"p3b": p3b_ok()}, scm_items())
    t45 = write_json(tmp_path / "t45.json", {"criteria": "rev7",
                                             "rows": [t45_row(c) for c in mod.T45_CASES]})
    return b, t45


def test_c5_pass_with_t45(mod, tmp_path):
    b, t45 = c5_bundle(mod, tmp_path)
    code, doc = run(mod, b, tmp_path, "C-5", "--t45", str(t45))
    assert code == 0 and doc["row_count_S15"]["found"] == 35
    assert doc["bundle_grade"]["status"] == "통과"
    assert doc["t4_t5_phrase"]["phrase"].startswith("일치")
    pair = next(p for p in doc["pairs_record"] if p["base"] == "E_G4_Fs4")
    assert pair["pair"] == "E_G4_Fs4_V0"


def test_c5_t4_excess_stops_h7(mod, tmp_path):
    b, t45 = c5_bundle(mod, tmp_path)
    data = json.loads(t45.read_text(encoding="utf-8"))
    data["rows"][0] = t45_row(data["rows"][0]["case"], over_t4=2)
    t45.write_text(json.dumps(data), encoding="utf-8")
    code, doc = run(mod, b, tmp_path, "C-5", "--t45", str(t45))
    assert code == 1
    assert any(s["reason"] == "T4_T5: H-7" for s in doc["stops"])
    assert doc["t4_t5_phrase"]["phrase"].startswith("불일치")


def test_c5_without_t45_is_not_judgeable(mod, tmp_path):
    b, _ = c5_bundle(mod, tmp_path)
    _, doc = run(mod, b, tmp_path, "C-5")
    assert doc["bundle_grade"]["status"] == "판정 불가"
    assert doc["t4_t5_phrase"]["phrase"].startswith("판정 안 함")


def test_c5_vb_specific_failure_and_j11(mod, tmp_path):
    b, t45 = c5_bundle(mod, tmp_path)
    vb = next(j for j in b.judged if j["case"] == "P3b_J1_B_top_Fs4")
    vb["items"]["P3-3_after_t_D"] = {"within": False}
    late = next(j for j in b.judged if j["case"] == "seed26")
    late["items"]["J11_R8-3"] = {"status": "H-7", "n_late_fallback_R6_B7": 1}
    code, doc = run(mod, b, tmp_path, "C-5", "--t45", str(t45))
    reasons = [s["reason"] for s in doc["stops"]]
    assert code == 1
    assert any(r.startswith("VB-specific failure: P3b_J1_B_top_Fs4 fail") for r in reasons)
    grades = {r["case"]: r["grade"] for r in doc["rows"]}
    assert grades["seed26"] == "fail" and grades["P3b_J1_B_top_Fs4_v0v"] == "pass"


def test_t45_needs_revision_7(mod, tmp_path):
    b, t45 = c5_bundle(mod, tmp_path)
    t45.write_text(json.dumps({"criteria": "rev6", "rows": []}), encoding="utf-8")
    code, _ = run(mod, b, tmp_path, "C-5", "--t45", str(t45))
    assert code == 2


# ------------------------------------------------------------------------------------- records
def p3a(**over: Any) -> dict[str, Any]:
    checks = {"P3a-1_within": True, "P3a-2_lifted": True, "P3a-3_within": True,
              "P3a-4_within": True, "P3a-5_within": True, "abort": False}
    checks.update(over)
    return {"p3a": {"checks": checks,
                    "P3a-9_min_cylinder_force": {"before_liftoff": {"any_flag": False}}}}


def test_openloop_record_complete_and_incomplete(mod, tmp_path):
    b = Bundle(tmp_path, "C6C7")
    for case, crit in (("P3a_prop", "C-6"), ("P3a_VB_FB", "C-7a"), ("P3a_V0_FB", "C-7b")):
        b.add_scm(entry(case, crit, "SCM"), p3a(), {})
    code, doc = run(mod, b, tmp_path, "C-6C7")
    assert code == 0 and doc["record_status"] == "기록 완료"
    result = b.batch / "P3a_V0_FB" / "result.json"
    data = json.loads(result.read_text(encoding="utf-8"))
    del data["p3a"]["checks"]["P3a-5_within"]
    result.write_text(json.dumps(data), encoding="utf-8")
    b.write = lambda: {"manifest": tmp_path / "manifest.json", "judge": tmp_path / "judge.json"}
    _, doc = run(mod, b, tmp_path, "C-6C7")
    assert doc["record_status"] == "기록 불완전"
    row = next(r for r in doc["rows"] if r["case"] == "P3a_V0_FB")
    assert row["missing_inputs"] == ["P3a-5_within"]


def oc5_files(tmp_path: Path, b: Bundle, case: str, m_class: str, *, fmin: bool = True
              ) -> list[str]:
    oc5 = write_json(tmp_path / f"oc5_{case}.json", {
        "result": str(b.batch / case / "result.json"), "class": m_class, "m_N": 5869.6,
        "status": "기록", "values": {"R_c_operating": 0.95}})
    argv = ["--oc5", str(oc5)]
    if fmin:
        f = write_json(tmp_path / f"fmin_{case}.json", {
            "case": str(b.batch / case), "status": "기록", "t_D_s": 35.0,
            "F_below_F_min": {"ms": [0.0, 0.0, 158.0, 0.0]}})
        argv += ["--fmin-time", str(f)]
    return argv


def test_c8_record_with_s9_handling(mod, tmp_path):
    b = Bundle(tmp_path, "OC5")
    b.add_scm(entry("OC5_VB", "C-8a", "SCM"), {"p3b": {}}, {})
    b.add_scm(entry("OC5_V0", "C-8b", "SCM"), {"p3b": {}}, {})
    argv = oc5_files(tmp_path, b, "OC5_VB", "stop_S9") + oc5_files(tmp_path, b, "OC5_V0",
                                                                   "record")
    code, doc = run(mod, b, tmp_path, "C-8", *argv)
    assert code == 0 and doc["record_status"] == "기록 완료"
    vb = next(r for r in doc["rows"] if r["case"] == "OC5_VB")
    assert "R18-5" in vb["S-9_handled"] and vb["stops"] == []
    assert vb["fmin_time"]["F_below_F_min"]["ms"][2] == 158.0


def test_c8_s9_on_v0_stops_and_missing_fmin(mod, tmp_path):
    b = Bundle(tmp_path, "OC5")
    b.add_scm(entry("OC5_VB", "C-8a", "SCM"), {"p3b": {}}, {})
    b.add_scm(entry("OC5_V0", "C-8b", "SCM"), {"p3b": {}}, {})
    argv = oc5_files(tmp_path, b, "OC5_VB", "record", fmin=False) + oc5_files(
        tmp_path, b, "OC5_V0", "stop_S9")
    code, doc = run(mod, b, tmp_path, "C-8", *argv)
    assert code == 1 and doc["record_status"] == "기록 불완전"
    assert doc["stops"] == [{"case": "OC5_V0", "reason": "S-9 (original 7.4)"}]


# ------------------------------------------------------------------------------------- commit / CLI
def test_commit_identity_s12(mod, tmp_path):
    b = c1_bundle(tmp_path)
    b.entries[0]["code_at_launch"]["git"]["head"] = "0" * 40
    code, doc = run(mod, b, tmp_path, "C-1")
    assert code == 1 and any(s["reason"].startswith("S-12") for s in doc["stops"])


def test_seals_command(mod, capsys):
    assert mod.main(["seals", "--rules-dir", str(RULES_DIR)]) == 0
    last = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert last["files"]["v5_resume_4368_rules_rev18.md"]["ok"] is True


def test_worst_order(mod):
    assert mod.worst([]) == "pass"
    assert mod.worst(["allowed_stop", "flag"]) == "flag"
    assert mod.worst(["fail", "not_judgeable", "pass"]) == "not_judgeable"
