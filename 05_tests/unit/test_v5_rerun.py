"""Paper v5 U-3 / U-6 rerun support (``u3_u6_rerun_rules.md``): options, key lists, the D-1
reuse rules Q-1 / Q-2 / Q-4 / Q-5 and the U-3 judge, on stored files and synthetic lines (no
harness run; the short harness probes are recorded in the merge report)."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
S9_DIR = ROOT / "04_scripts" / "03_control" / "s9"
for _path in (COUPLED_DIR, S9_DIR, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import u3_judge  # noqa: E402
import u3_reuse  # noqa: E402
import v5_rerun  # noqa: E402

S9_OUT = ROOT / "06_analysis" / "02_control" / "s9"


# ------------------------------------------------------------------------------- options
def test_split_argv_keeps_the_positional_arguments() -> None:
    argv = ["r72.py", "root", "out.json", "--v5-setting", "VB", "4", "--ids-from", "x.json",
            "--pad", "B"]
    rest, options = v5_rerun.split_argv(argv)
    assert rest == ["r72.py", "root", "out.json", "4"]
    assert options == v5_rerun.RerunOptions("VB", Path("x.json"), "B")
    assert v5_rerun.split_argv(["r72.py", "root", "--list"])[1] == v5_rerun.RerunOptions()


@pytest.mark.parametrize("argv", [["s", "--v5-setting", "V9"], ["s", "--pad", "B"],
                                  ["s", "--v5-setting"]])
def test_split_argv_refuses_bad_options(argv) -> None:
    with pytest.raises(SystemExit):
        v5_rerun.split_argv(argv)


def test_vb_and_u6_definitions() -> None:
    _, vb = v5_rerun.options_of("VB")
    _, plant_only = v5_rerun.options_of("VB", extend_start=False)
    flow_v0, v0 = v5_rerun.options_of("V0")
    assert vb.extend_start_tracked and vb.rod_release_force and vb.lock_window_follows_plant
    assert vb.lock_closure.overlap_ratio == 0.02 and vb.lock_closure.closing_delay_s == 0.05
    assert not plant_only.extend_start_tracked and plant_only.lock_closure == vb.lock_closure
    assert v0 is None and not flow_v0.is_enabled
    assert v5_rerun.controller_tag(vb) == "final_C4G2_P3"
    assert v5_rerun.controller_tag(v0) == "final_C4G2"
    assert v5_rerun.controller_tag(plant_only, "ABL") == "ABL"
    assert v5_rerun.definition("VB", "IND")["controller_tag"] == "IND"
    assert v5_rerun.definition_sha256("VB") != v5_rerun.definition_sha256("VB", "ABL")


def test_j_p3_of_a_head_only_vb_run() -> None:
    assert v5_rerun.j_p3_status("final_C4G2_P3", None, False, True) == "no_rod_reading"
    assert v5_rerun.j_p3_status("final_C4G2_P3", None, False, False) == "setting_defect"
    assert v5_rerun.j_p3_status("final_C4G2_P3", None, True, True) == "setting_defect"
    assert v5_rerun.j_p3_status("final_C4G2", None, False, True) == "not_applicable"
    assert v5_rerun.j_p3_status("ABL", None, False, True) == "not_applicable"


# ------------------------------------------------------------------------------ key lists
@pytest.mark.parametrize(("key", "pad"), [
    ("H1|J1|A|top|flat", "A"), ("H1|J1|B|top|flat", "B"), ("g6|G1+J1@FL|top|Fs4|PA", "A"),
    ("g6|G1+J1@FL|top|Fs4", "B"), ("base|rigid|0,0|top|Fs4|b1", "B"),
    ("S|H3|J1|A|top|edge_nd@k0.5", "A"), ("G|g6r|rigid+S1@RR|bottom|Fs0", "B"),
    ("slope|edge|top|4.0|FL|raised|20.0|proj", "B")])
def test_pad_of_key(key, pad) -> None:
    assert v5_rerun.pad_of_key(key) == pad


@pytest.mark.parametrize(("bundle", "count"), [
    (("rev85/finB2_harness.json", "slope"), 110), (("rev85/finB2_harness.json", "h6"), 26),
    (("rev85/finB2_h9.json", "h9"), 24), (("rev85/finB2_p0.json", "g6"), 116),
    (("rev85/finB2_p0.json", "g8"), 516), (("rev85/finB2_p0.json", "p3b"), 171),
    (("rev85/finB2_x426b.json", "x426b"), 84), (("rev85/fin_x426_C.json", None), 34),
    (("rev85/fin_x426_D.json", None), 33), (("rev84/fin2_b5_wide_official.json", None), 226)])
def test_rules_2_and_3_key_counts(bundle, count) -> None:
    path, suite = bundle
    if not (S9_OUT / path).is_file():
        pytest.skip(f"stored file {path} absent")
    keys = v5_rerun.ids_from(S9_OUT / path, "B", suites=None if suite is None else (suite,))
    assert len(keys) == count


def test_select_known_refuses_a_foreign_key() -> None:
    assert v5_rerun.select_known(["a", "b"], ["b", "a", "c"]) == ["a", "b"]
    with pytest.raises(SystemExit):
        v5_rerun.select_known(["a", "x"], ["a"])


# ----------------------------------------------------------------------------------- reuse
def test_reuse_table_is_the_19_keys_of_rules_6() -> None:
    families = {}
    for family, _ in u3_reuse.REUSE_TABLE.values():
        families[family] = families.get(family, 0) + 1
    assert len(u3_reuse.REUSE_TABLE) == 19
    assert families == {"H-S-0 flat": 6, "H-S-1": 2, "H-S-0 fdown-rec": 5,
                        "H-S-0 diag-rec": 2, "H-S-0 roll+rec": 2, "H-S-0 roll-rec": 2}


def _payload(soil: str, level: str = "top") -> dict:
    return {"soil": soil, "pad": "B", "level": level, "roll_deg": 0.0, "pitch_deg": 0.0,
            "fs_kN": 4.0, "mass_scale": 1.0, "settle_table_status": "table"}


def _line(soil: str, *, eps: float = 0.0, setting: str = "VB", sha: str = "s",
          u3: bool = True) -> dict:
    _, options = v5_rerun.options_of(setting)
    row = {"key": f"D1|H-S-0|{soil}|T|flat|K1", "base": soil, "level": "top", "roll_deg": 0.0,
           "pitch_deg": 0.0, "crawler_k_scale": 1.0, "patch_soil": None, "sink": None}
    d1 = {"key": f"{row['key']}|{setting}|e{eps:g}", "head_only_declared": True,
          "has_rod_reading": False, "j_p3": "no_rod_reading"}
    if u3:
        d1["u3"] = {"verdict": "pass", "passed": True, "failed_rows": [], "hash": "h",
                    "t_ready_s": 40.0, "flags": [], "warnings": []}
    return {"job": {"d1": row, "eps": eps, "setting": setting}, "commands_sha256": sha,
            "controller_tag": "final_C4G2_P3" if setting == "VB" else None,
            "hydraulic_options": None if options is None else options.to_dict(), "d1": d1}


def _jobs(*soils: str) -> list[dict]:
    return [{"suite": "slope", "id": f"H1|{soil}|B|top|flat", "payload": _payload(soil),
             "candidate": "current"} for soil in soils]


def _write(tmp_path, lines, name: str = "d1.jsonl") -> Path:
    path = tmp_path / name
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    return path


def test_reuse_after_an_equal_sample_hash(tmp_path) -> None:
    path = _write(tmp_path, [_line("G1", sha="a"), _line("J1", sha="b")])
    plan = u3_reuse.plan(path, "VB", _jobs("G1", "J1"), settle_hook="harness")
    assert plan.samples == {"H-S-0 flat": "H1|G1|B|top|flat"}
    assert plan.reusable_ids == {"H1|J1|B|top|flat"}
    decision = u3_reuse.decide(plan, {"H1|G1|B|top|flat": {"v5": {"logged_commands_sha256": "a"}}})
    assert decision.reused_ids == {"H1|J1|B|top|flat"}
    record = u3_reuse.reused_record(plan, _jobs("J1")[0], decision)
    assert record["reuse"] == "d1" and record["d1_key"] == "D1|H-S-0|J1|T|flat|K1|VB|e0"
    assert record["v5"]["controller_tag"] == "final_C4G2_P3"
    assert record["v5"]["extend_start"]["revision"] == 4
    assert record["verdict"] == "pass" and record["id"] == "H1|J1|B|top|flat"


def test_reuse_refused_cases(tmp_path) -> None:
    sample = {"H1|G1|B|top|flat": {"v5": {"logged_commands_sha256": "other"}}}
    path = _write(tmp_path, [_line("G1", sha="a"), _line("J1", sha="b")])
    plan = u3_reuse.plan(path, "VB", _jobs("G1", "J1"), settle_hook="harness")
    assert u3_reuse.decide(plan, sample).reused_ids == set()  # Q-4: sample hash differs
    plan = u3_reuse.plan(path, "V0", _jobs("G1", "J1"), settle_hook="harness")
    assert set(plan.rejected) == {"H1|G1|B|top|flat", "H1|J1|B|top|flat"}  # Q-1: setting
    eps_only = _write(tmp_path, [_line("G1", eps=2e-3), _line("J1", u3=False)], "eps.jsonl")
    plan = u3_reuse.plan(eps_only, "VB", _jobs("G1", "J1"), settle_hook="harness")
    assert plan.rejected["H1|G1|B|top|flat"].startswith("Q-1")
    assert plan.rejected["H1|J1|B|top|flat"].startswith("Q-5")
    plan = u3_reuse.plan(path, "VB", _jobs("G1", "J1"), settle_hook="p0")
    assert all(reason.startswith("Q-2") for reason in plan.rejected.values())
    jobs = _jobs("G1")
    jobs[0]["payload"]["fs_kN"] = 0.0
    plan = u3_reuse.plan(path, "VB", jobs, settle_hook="harness")
    assert "fs_kN" in plan.rejected["H1|G1|B|top|flat"]
    other = copy.deepcopy(_line("G1"))
    other["hydraulic_options"] = None
    plan = u3_reuse.plan(_write(tmp_path, [other], "other.jsonl"), "VB", _jobs("G1"),
                         settle_hook="harness")
    assert "plant options" in plan.rejected["H1|G1|B|top|flat"]


# ------------------------------------------------------------------------------------ judge
def test_grade_classes() -> None:
    record = u3_judge.Bundle("h9", "x", "record", 1, "h9")
    assert u3_judge.grade({"verdict": "pass", "flags": []}, record, None)["grade"] == "pass"
    assert u3_judge.grade({"verdict": "pass", "flags": ["F"]}, record, None)["grade"] == "flag"
    assert u3_judge.grade({"verdict": "stroke_limited_stop"}, record, None)["grade"] == \
        "safe_stop"
    assert u3_judge.grade({"verdict": "settle_check_fail"}, record, None)["grade"] == "fail"
    assert u3_judge.grade({"error": "x"}, record, None)["grade"] == "fail"
    r72 = u3_judge.Bundle("C", "x", "r72", 1)
    demoted = {"gates": {"G6-1": True, "G6-3_Fmin": True, "G6-7_preloc": False},
               "preloc_flag_ok": True, "flags": [], "final_phase": "ready"}
    assert u3_judge.grade(demoted, r72, None) == {"grade": "flag", "verdict": None,
                                                  "flags": ["P3-8_demoted"]}


def test_classes_and_phrase() -> None:
    v0 = {"a": {"grade": "pass"}, "b": {"grade": "fail"}, "c": {"grade": "fail"},
          "d": {"grade": "pass"}}
    vb = {"a": {"grade": "fail", "verdict": "fail", "flags": []},
          "b": {"grade": "fail", "verdict": "fail", "flags": []},
          "c": {"grade": "flag", "verdict": "pass", "flags": ["F"]},
          "d": {"grade": "safe_stop", "verdict": "stroke_limited_stop", "flags": []}}
    classes = u3_judge.classify_pairs(v0, vb)
    assert [c["key"] for c in classes["vb_only_failure"]] == ["a"]
    assert classes["baseline_failure"] == ["b"]
    assert classes["vb_improvement"] == [{"key": "c", "vb": "flag"}]
    assert classes["safe_stop_move"] == [{"key": "d", "v0": "pass", "vb": "safe_stop"}]
    counts = {"pass": 3, "flag": 1, "safe_stop": 0, "fail": 2}
    assert u3_judge.phrase(counts, 1) is None
    assert u3_judge.phrase(counts, 0) == "VB 통과 3 / FLAG 1 / 안전 종료 0 / 실패 2(그중 VB 고유 0)"


def test_differences_count_one_sided_values_as_na() -> None:
    out = u3_judge.differences({"a": {"t_ready_s": 40.0}, "b": {"t_ready_s": None}},
                               {"a": {"t_ready_s": 42.5}, "b": {"t_ready_s": 50.0}})
    assert out["t_ready_s"] == {"n": 1, "NA": 1, "mean": 2.5, "min": 2.5, "max": 2.5}


def test_gate_g2_and_g4_fields() -> None:
    good = {"v5": {"v5_setting": "VB", "controller_tag": "final_C4G2_P3",
                   "extend_start": {"rule": "tracked_bound", "revision": 4},
                   "definition_sha256": "d", "head_only_declared": True,
                   "has_rod_reading": False, "j_p3": "no_rod_reading"}, "id": "k"}
    assert u3_judge.run_v5_problems(good, "VB", "final_C4G2_P3", needs_bound=True) == []
    assert u3_judge.gate_j_p3([good]) == []
    rod = copy.deepcopy(good)
    rod["v5"].update(has_rod_reading=True, j_p3="pass")
    assert u3_judge.gate_j_p3([rod])[0]["j_p3"] == "pass"
    assert u3_judge.gate_j_p3([rod])[0]["reason"].startswith("head-only suite")
    abl = copy.deepcopy(good)
    abl["v5"]["controller_tag"] = "ABL"
    assert u3_judge.run_v5_problems(abl, "VB", "ABL", needs_bound=False) == [
        "③ on where it must be off"]


# ----------------------------------------------------------- rules rev1 (g8 rod readings, G-6)
def _vb_run(suite: str, *, rod: bool, j_p3: str, fallback: int = 0, breach: int = 0) -> dict:
    bound = {"breach_reads": [breach, 0, 0, 0], "margin_used_reads": [0] * 4,
             "locked_breach_over_tol_reads": [0] * 4} if rod else None
    return {"suite": suite, "id": f"{suite}|key", "warnings": [],
            "v5": {"v5_setting": "VB", "controller_tag": "final_C4G2_P3", "j_p3": j_p3,
                   "has_rod_reading": rod, "head_only_declared": suite != "g8",
                   "extend_bound_check": bound, "rod_pressure_fallback_events": fallback}}


def test_g8_rod_reading_and_j_p3_pass_passes_g4() -> None:
    assert u3_judge.rod_reading_suites() == ("g8",)
    assert u3_judge.gate_j_p3([_vb_run("g8", rod=True, j_p3="pass")]) == []
    assert u3_judge.gate_fallback([_vb_run("g8", rod=True, j_p3="pass")]) == []


def test_g8_without_rod_reading_stops_g4() -> None:
    stops = u3_judge.gate_j_p3([_vb_run("g8", rod=False, j_p3="no_rod_reading")])
    assert [(s["suite"], s["j_p3"], s["has_rod_reading"]) for s in stops] == [
        ("g8", "no_rod_reading", False)]
    breach = u3_judge.gate_j_p3([_vb_run("g8", rod=True, j_p3="H-7", breach=1)])
    assert breach and breach[0]["j_p3"] == "H-7"


def test_head_only_suite_with_a_rod_reading_stops_g4() -> None:
    stops = u3_judge.gate_j_p3([_vb_run("slope", rod=True, j_p3="pass")])
    assert [(s["suite"], s["j_p3"], s["has_rod_reading"]) for s in stops] == [
        ("slope", "pass", True)]
    assert u3_judge.gate_j_p3([_vb_run("slope", rod=False, j_p3="no_rod_reading")]) == []


def test_one_g8_fallback_stops_g6() -> None:
    stops = u3_judge.gate_fallback([_vb_run("g8", rod=True, j_p3="pass", fallback=1),
                                    _vb_run("slope", rod=False, j_p3="no_rod_reading",
                                            fallback=3)])
    assert stops == [{"key": "g8|key", "suite": "g8", "fallback_events": 1}]


def test_previous_g6_grade_is_the_stored_verdict() -> None:
    g6 = u3_judge.Bundle("g6", "x", "g6", 1, "g6")
    stored = {"verdict": "fail", "failed_rows": ["G6-7_preloc"], "flags": []}
    previous = u3_judge.previous_grade(stored, g6, None)
    assert previous["grade"] == "fail" and previous["previous_g6_demotion"] == "not_applied"


def test_rules_revision_record_reads_the_file(tmp_path) -> None:
    text = tmp_path / "u3_u6_rerun_rules_rev1.md"
    text.write_bytes(b"rev1\r\n")
    sha = v5_rerun.text_sha256(text)
    (tmp_path / "u3_u6_rerun_rules_rev1.sha256").write_text(f"{sha}  x\n", encoding="utf-8")
    assert u3_judge.revision_record(text) == {"rules": text.name, "sha256": sha,
                                              "sealed_sha256": sha, "match_seal": True}
    assert u3_judge.RULES_REVISIONS[0].name == "u3_u6_rerun_rules_rev1.md"
