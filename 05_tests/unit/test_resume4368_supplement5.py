"""436.8 R4 supplement 5 (89cb422d, user decision 129) in the path 1 tools: ``grid-h10`` pairs the
768 VB grid runs with their V0 runs (5-1), takes the run ``pass`` (5-2), lists the raw and the
family F excluded pass -> fail rows (5-3) and gives the v5 criteria H-10 grid term (5-4).
Synthetic grid files only; no harness or judgement run.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "06_analysis" / "02_control" / "verif_matrix" / "scripts"
for _path in (SCRIPTS, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import resume4368_judge as judge  # noqa: E402

GOOD_GATES = dict.fromkeys(("Fmin_after_W", "U57_outside", "fault0", "end_att"), True)
FS24_PHASES = {"grid_r67_main": 2, "grid_r67_top": 4}
OLD_V0_TAG = "c4g2_only"


def _write(path: Path, document) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".jsonl":
        path.write_text("".join(json.dumps(line) + "\n" for line in document), encoding="utf-8")
    else:
        path.write_text(json.dumps(document), encoding="utf-8")


def _runs(name: str, key: str, salt: str) -> list[dict]:
    """24 runs of one key: FS24 phases (family F keys of r67 files) then G4 phases."""
    fs24 = FS24_PHASES.get(name, 0) if key in judge.FAMILY_F_KEYS else 0
    events = ["FS24"] * fs24 + ["G4"] * (24 - fs24)
    runs = []
    for index, event in enumerate(events):
        offset = (index if event == "FS24" else index - fs24) * 0.025
        runs.append({"event": event, "offset_s": offset, "pass": True,
                     "gates": dict(GOOD_GATES), "fault_events": [],
                     "commands_sha256": f"{salt}{name}|{key}|{event}|{offset}"})
    return runs


def _grid(name: str, tag: str, setting: str, salt: str = "") -> dict:
    keys = [f"k{i}" for i in range(6)]
    keys += list(judge.FAMILY_F_KEYS) if name in FS24_PHASES else ["k6", "k7"]
    return {"meta": {}, "results": [{"key": key, "v5_setting": setting, "controller_tag": tag,
                                     "runs": _runs(name, key, salt)} for key in keys]}


def _family_lines(*, fail_r1: bool = False) -> list[dict]:
    lines = []
    for setting in ("V0", "VB"):
        for key in judge.FAMILY_F_KEYS:
            for i in range(16):
                gates = dict(GOOD_GATES)
                if fail_r1 and setting == "VB" and i < 5:
                    gates["U57_outside"] = False
                lines.append({"setting": setting, "key": key, "offset_s": i * 0.00625,
                              "event": "FS24", "gates": gates, "fault_events": [],
                              "final_phase": "ready",
                              "controller_tag": judge.TAG_P3 if setting == "VB"
                              else judge.TAG_V0})
    return lines


def _build(root: Path, *, sample_differs: bool = False) -> None:
    for name in judge.GRID_NAMES:
        _write(root / judge.GRID_VB_DIR / f"{name}.json", _grid(name, judge.TAG_P3, "VB"))
        stored = _grid(name, OLD_V0_TAG, "V0")
        _write(root / judge.GRID_V0_STORED_DIR / f"{name}.json", stored)
        sample = _grid(name, judge.TAG_V0, "V0", "new" if sample_differs else "")
        sample["results"] = [sample["results"][0], sample["results"][-1]]
        _write(root / judge.GRID_V0_SAMPLE_DIR / f"{name}.json", sample)
        _write(root / judge.GRID_V0_768_DIR / f"{name}.json", _grid(name, judge.TAG_V0, "V0"))
    _write(root / judge.FAMILY_F_LINES, _family_lines())


def _edit(root: Path, folder: str, name: str, change) -> None:
    path = root / folder / f"{name}.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    change(document)
    _write(path, document)


def _run(root: Path, i: int, j: int, name: str = "grid_r67_main", folder: str | None = None,
         **values) -> None:
    def change(document: dict) -> None:
        document["results"][i]["runs"][j].update(copy.deepcopy(values))
    _edit(root, folder or judge.GRID_VB_DIR, name, change)


def _grid_h10(root: Path) -> tuple[int, dict]:
    out = root / "grid_h10.json"
    code = judge.main(["grid-h10", "--root", str(root), "--out", str(out)])
    return code, json.loads(out.read_text(encoding="utf-8"))


FAMILY_FR = 6  # results index of FAMILY_F_KEYS[0] in grid_r67_* files


def test_all_pass_is_no_finding(tmp_path: Path) -> None:
    _build(tmp_path)
    code, report = _grid_h10(tmp_path)
    assert code == 0, report["markers"]
    assert report["v0_pair_source"]["source"] == judge.V0_SOURCE_STORED
    assert (report["rows"], report["judged_rows"], report["N_raw"], report["N_F"]) == (
        768, 768, 0, 0)
    assert len(report["family_f_rows"]) == 12 and report["family_f_condition"] is False
    assert report["record"]["pass_to_pass"] == 768
    assert report["h10_grid_selected"]["count"] == "N_raw"
    assert [row["count"] for row in report["h10_grid_table"]] == ["N_raw", "N_F", None]


def test_raw_pass_to_fail_row_in_rd7_notation(tmp_path: Path) -> None:
    _build(tmp_path)
    _run(tmp_path, 2, 3, name="grid_r69_top", **{"pass": False,
                                                  "gates": {**GOOD_GATES, "end_att": False}})
    code, report = _grid_h10(tmp_path)
    assert code == 1 and report["N_raw"] == 1 and report["N_F"] == 1
    row = report["raw_pass_to_fail"][0]
    assert row == {"bundle": "H-9", "result_file": f"{judge.GRID_VB_DIR}/grid_r69_top.json",
                   "location": "results[2].runs[3]", "file": "grid_r69_top.json",
                   "key": "k2", "setting": "VB", "event": "G4", "offset_s": 3 * 0.025,
                   "vb_false_gates": ["end_att"], "v0_false_gates": [],
                   "v0_result_file": f"{judge.GRID_V0_STORED_DIR}/grid_r69_top.json",
                   "v0_location": "results[2].runs[3]"}
    assert any("H-10" in marker for marker in report["markers"])


def _family_two_gate_fail(root: Path) -> None:
    _run(root, FAMILY_FR, 0, **{"pass": False, "gates": {**GOOD_GATES, "Fmin_after_W": False}})


@pytest.mark.parametrize("fail_r1, selected, code", [(False, "N_F", 0), (True, None, 1)])
def test_family_f_condition_selects_the_count(tmp_path, fail_r1, selected, code) -> None:
    _build(tmp_path)
    _family_two_gate_fail(tmp_path)
    if fail_r1:
        _write(tmp_path / judge.FAMILY_F_LINES, _family_lines(fail_r1=True))
    got, report = _grid_h10(tmp_path)
    assert report["family_f_condition"] is True and (report["N_raw"], report["N_F"]) == (1, 0)
    assert report["h10_grid_selected"]["count"] == selected and got == code
    assert report["family_f_result"] == ("실패" if fail_r1 else "통과")
    table_row = next(r for r in report["family_f_rows"] if r["location"] == "results[6].runs[0]")
    assert (table_row["vb_pass"], table_row["v0_pass"], table_row["vb_pass_without_two"],
            table_row["v0_pass_without_two"]) == (False, True, True, True)


def test_family_f_rows_are_judged_again_on_both_sides(tmp_path: Path) -> None:
    """Supplement 5-3 (다): V0 failed by a two gate, VB by another gate = fail -> fail in (가)
    but pass -> fail without the two gates."""
    _build(tmp_path)
    _run(tmp_path, FAMILY_FR, 1, folder=judge.GRID_V0_STORED_DIR,
         **{"pass": False, "gates": {**GOOD_GATES, "U57_outside": False}})
    _run(tmp_path, FAMILY_FR, 1, **{"pass": False, "gates": {**GOOD_GATES, "end_att": False}})
    _, report = _grid_h10(tmp_path)
    assert report["N_raw"] == 0 and report["N_F"] == 1
    assert report["record"]["fail_to_fail"] == 1
    assert report["excluded_pass_to_fail"][0]["v0_false_gates"] == ["U57_outside"]


def test_pairing_tolerance_duplicates_and_v0_only(tmp_path: Path) -> None:
    _build(tmp_path)

    def change(document: dict) -> None:
        runs = document["results"][1]["runs"]  # not a sample job (first / last)
        runs[5]["offset_s"] += 5e-10  # same phase within 1e-9 s
        runs.append({**runs[6], "offset_s": runs[6]["offset_s"] + 5e-10})  # second pair
        runs.append({**runs[7], "offset_s": 99.0})  # V0 only
    _edit(tmp_path, judge.GRID_V0_STORED_DIR, "grid_r69_bottom", change)
    code, report = _grid_h10(tmp_path)
    reasons = {(r["location"], tuple(r["reasons"])) for r in report["record"]["not_judgeable"]}
    assert reasons == {("results[1].runs[6]", ("2 V0 pairs (supplement 5-1)",)),
                       ("results[1].runs[25]",("V0 run without a VB row (supplement 5-1)",))}
    assert code == 1 and report["judged_rows"] == 767


@pytest.mark.parametrize("values, reason", [
    ({"pass": 1}, "VB pass is not a bool"),
    ({"pass": True, "gates": {**GOOD_GATES, "fault0": False}},
     "VB pass differs from the AND of the gates"),
    ({"gates": {**GOOD_GATES, "fault0": "yes"}}, "VB gates is not a gate name -> bool map"),
    ({"fault_events": None}, "VB fault_events is not a list"),
])
def test_row_pass_form_is_not_judgeable(tmp_path, values, reason) -> None:
    _build(tmp_path)
    _run(tmp_path, 1, 1, **values)
    code, report = _grid_h10(tmp_path)
    assert [r["reasons"] for r in report["record"]["not_judgeable"]] == [[reason]]
    assert code == 1 and any("판정 불가" in m for m in report["markers"])


def test_fault_rows_are_counted(tmp_path: Path) -> None:
    _build(tmp_path)
    _run(tmp_path, 0, 0, name="grid_r67_top", fault_events=["FAULT_X"])
    code, report = _grid_h10(tmp_path)
    assert report["record"]["fault"] == 1 and code == 1
    assert any("FAULT 0" in marker for marker in report["markers"])


def test_family_f_gate_names_must_match(tmp_path: Path) -> None:
    _build(tmp_path)
    _run(tmp_path, FAMILY_FR, 0, gates={**GOOD_GATES, "extra": True})
    _, report = _grid_h10(tmp_path)
    assert [r["reasons"] for r in report["record"]["not_judgeable"]] == [
        ["family F: VB and V0 gate names differ"]]


def test_tags_and_the_v0_768_source(tmp_path: Path) -> None:
    _build(tmp_path, sample_differs=True)
    _edit(tmp_path, judge.GRID_VB_DIR, "grid_r69_top",
          lambda d: d["results"][0].update(controller_tag=judge.TAG_V0))
    code, report = _grid_h10(tmp_path)
    assert report["v0_pair_source"]["source"] == judge.V0_SOURCE_768
    assert {s["stop"] for s in report["stops"]["tags"]} == {"S-2"}
    assert len(report["stops"]["tags"]) == 24 and code == 1


def test_sample_problem_leaves_the_source_undecided(tmp_path: Path) -> None:
    _build(tmp_path)
    _edit(tmp_path, judge.GRID_V0_SAMPLE_DIR, "grid_r67_top",
          lambda d: d["results"][0]["runs"].pop())
    code, report = _grid_h10(tmp_path)
    assert code == 1 and report["v0_pair_source"]["source"] is None
    assert "raw_pass_to_fail" not in report


def test_list_order_is_file_key_event_phase() -> None:
    rows = [{"file": "grid_r69_top.json", "key": "a", "event": "G4", "offset_s": 0.1},
            {"file": "grid_r67_top.json", "key": "b", "event": "G4", "offset_s": 0.05},
            {"file": "grid_r67_top.json", "key": "b", "event": "FS24", "offset_s": 0.1},
            {"file": "grid_r67_top.json", "key": "b", "event": "FS24", "offset_s": 0.025}]
    ordered = sorted(rows, key=judge.grid_sort_key)
    assert [(r["file"][5:8], r["event"], r["offset_s"]) for r in ordered] == [
        ("r67", "FS24", 0.025), ("r67", "FS24", 0.1), ("r67", "G4", 0.05), ("r69", "G4", 0.1)]
