"""436.8 R4 supplement 4 (de45d301) in the path 1 tools: ``r4-inputs`` (4-1 .. 4-4), the named
``r4-lists`` inputs and ``family-f`` R-1 .. R-4 with its application (4-5); ``head-check`` without
``--files`` (pre-run audit A-4). Synthetic inputs only; no harness, Chrono or judgement run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
SCRIPTS = ROOT / "06_analysis" / "02_control" / "verif_matrix" / "scripts"
for _path in (COUPLED, SCRIPTS, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import resume4368_judge as judge  # noqa: E402

KIND_TAG = judge.KIND_TAGS
GOOD_GATES = dict.fromkeys(("Fmin_after_W", "U57_outside", "fault0", "end_att"), True)


def _write(path: Path, document) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".jsonl":
        path.write_text("".join(json.dumps(line) + "\n" for line in document), encoding="utf-8")
    else:
        path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _main(argv: list[str], out: Path) -> tuple[int, dict]:
    code = judge.main([*argv, "--out", str(out)])
    return code, json.loads(out.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ synthetic original files
def _setting_lines(field: str, settings: list[str]) -> list[dict]:
    lines = []
    for i, setting in enumerate(settings):
        tag = KIND_TAG[judge.kind_of_setting(setting)]
        line = {"controller_tag": tag, "key": f"k{i}", "event": "FS24"}
        if field == "job.setting":
            line["job"] = {"setting": setting, "case": f"c{i}"}
        else:
            line["setting"] = setting
        lines.append(line)
    return lines


def _grid(kind: str, runs: int, results: int = 2, fs24: int | None = None) -> dict:
    per = runs // results
    rows = []
    for i in range(results):
        events = ["FS24" if fs24 is not None and i * per + j < fs24 else "G4" for j in range(per)]
        rows.append({"key": f"g{i}", "v5_setting": "VB", "controller_tag": KIND_TAG[kind],
                     "runs": [{"event": e, "offset_s": float(j)} for j, e in enumerate(events)]})
    return {"meta": {}, "results": rows}


def _u6(per_kind: int) -> dict:
    records = [{"case": f"{c}{i}", "controller": c,
                "v5": {"controller_tag": KIND_TAG[judge.U6_CONTROLLER_KINDS[c]]}}
               for c in ("C2", "ABL", "IND") for i in range(per_kind)]
    return {"records": records}


def _items(kind: str, n: int, container: str = "records") -> dict:
    return {container: [{"id": f"k{i}", "key": f"k{i}", "controller_tag": KIND_TAG[kind],
                         "v5": {"controller_tag": KIND_TAG[kind]}} for i in range(n)]}


def _document(spec: judge.InputFile) -> object:
    name = Path(spec.name).name
    if name == "h1_d1.jsonl":
        return _setting_lines("job.setting", ["V0"] * 434 + ["VB"] * 434)
    if name == "h10_reuse_rerun.jsonl":
        settings = ["VB"] * 138 + [f"LS{n}" for n in range(1, 5) for _ in range(72)]
        return _setting_lines("job.setting", settings + ["V0"] * 10 + ["V3"] * 4)
    if name == "h9_family_F.jsonl":
        return _setting_lines("setting", ["V0"] * 32 + ["VB"] * 32)
    if name.endswith(".jsonl"):
        return [{"controller_tag": KIND_TAG[spec.kind], "job": {"setting": "V1"}}
                for _ in range(spec.expected)]
    if name == "u6_b5_main_VB.json":
        return _u6(16)
    if name == "u6_b5_wide_VB.json":
        return _u6(226)
    if "h9_family_F_V" in name:
        return _grid(spec.kind, 96, fs24=32)
    if name.startswith("grid_"):
        return _grid(spec.kind, spec.expected)
    container = "results" if name.startswith(("u3_C_", "u3_D_", "h")) else "records"
    return _items(spec.kind, spec.expected, container)


def _build_inputs(root: Path) -> None:
    for spec in judge.INPUT_FILES:
        _write(root / spec.name, _document(spec))
    for name in (*judge.KEY_SOURCES, *judge.V0_STORED_GRID):
        _write(root / name, {})


def _inputs(root: Path) -> tuple[int, dict]:
    return _main(["r4-inputs", "--root", str(root)], root / "inputs.json")


# ---------------------------------------------------------------------- 4-1 .. 4-4 r4-inputs
def test_r4_inputs_table_is_43_files_named_one_by_one() -> None:
    names = [spec.name for spec in judge.INPUT_FILES]
    assert len(names) == len(set(names)) == 43
    assert sum(n.startswith(judge.RK) for n in names) == 21
    assert sum(n.startswith(judge.LK) for n in names) == 22
    assert not any("*" in n for files in judge.BUNDLE_FILES.values() for n in files)
    assert len(judge.BUNDLE_FILES["H-3"]) == 18 and len(judge.BUNDLE_FILES["H-4"]) == 4


def test_r4_inputs_complete_synthetic_root_passes(tmp_path: Path) -> None:
    _build_inputs(tmp_path)
    code, report = _inputs(tmp_path)
    assert code == 0, (report["markers"], report["failed_checks"])
    assert report["file_count"] == {"RK": 21, "LK": 22}
    assert report["h10_kinds_record"] == {"③ 켬(VB)": 138, "③ 켬(LS)": 288, "③ 없음": 14}


def test_r4_inputs_missing_file_and_wrong_count_are_s15(tmp_path: Path) -> None:
    _build_inputs(tmp_path)
    (tmp_path / judge.KEY_SOURCES[2]).unlink()
    path = tmp_path / judge.RK / "h5_u9_v0.jsonl"
    path.write_text(path.read_text(encoding="utf-8").split("\n", 1)[1], encoding="utf-8")
    _, report = _inputs(tmp_path)
    assert any(m.startswith("S-15 (supplement 4-4") for m in report["markers"])
    assert any(c["check"].startswith("units ") and "h5_u9_v0" in c["check"]
               for c in report["failed_checks"])


def test_r4_inputs_per_line_kind_and_tag_stops(tmp_path: Path) -> None:
    """Supplement 4-3: kind by the field, tag compared; u6 ABL on one side is S-3 only."""
    _build_inputs(tmp_path)
    h1 = tmp_path / judge.RK / "h1_d1.jsonl"
    lines = [json.loads(x) for x in h1.read_text(encoding="utf-8").splitlines()]
    lines[0]["controller_tag"] = judge.TAG_P3  # a V0 line with the ③ tag: S-2
    del lines[1]["job"]["setting"]  # no kind input: S-11
    _write(h1, lines)
    main = tmp_path / judge.LK / "u6_b5_main_VB.json"
    document = json.loads(main.read_text(encoding="utf-8"))
    document["records"][16]["v5"]["controller_tag"] = judge.TAG_P3  # ABL name, C2 tag: S-3
    _write(main, document)
    _, report = _inputs(tmp_path)
    stops = {(f["result_file"].rsplit("/", 1)[-1], s["location"], s["stop"])
             for f in report["files"] for s in f.get("stops") or []}
    assert stops == {("h1_d1.jsonl", "line 1", "S-2"), ("h1_d1.jsonl", "line 2", "S-11"),
                     ("u6_b5_main_VB.json", "records[16]", "S-3")}


@pytest.mark.parametrize("controller, tag, expected", [
    ("ABL", judge.TAG_ABL, []), ("C2", judge.TAG_P3, []), ("IND", "IND", []),
    ("C2", judge.TAG_ABL, ["S-3"]), ("ABL", "IND", ["S-3"]), ("XX", judge.TAG_P3, ["S-11"]),
    ("IND", judge.TAG_V0, ["S-2"]),
])
def test_u6_controller_kinds(controller, tag, expected) -> None:
    spec = judge.InputFile("H-4", "", "u6.json", field="controller")
    _, problems = judge.unit_kind_check(spec, {"controller": controller,
                                               "v5": {"controller_tag": tag}}, None)
    assert [stop for stop, _ in problems] == expected


def test_grid_run_tag_is_the_job_tag() -> None:
    spec = judge.InputFile("H-9", "본", "grid_r67_main.json", kind=judge.KIND_P3_VB)
    _, problems = judge.unit_kind_check(spec, {"event": "G4"},
                                        {"controller_tag": judge.TAG_V0})
    assert problems == [("S-2", f"tag {judge.TAG_V0!r} != {judge.TAG_P3!r} of ③ 켬(VB)")]


# ------------------------------------------------------------------------- 4-5 family F
def _family_lines(**changes) -> list[dict]:
    lines = []
    for setting in ("V0", "VB"):
        for key in judge.FAMILY_F_KEYS:
            for i in range(16):
                lines.append({"setting": setting, "key": key, "offset_s": i * 0.00625,
                              "event": "FS24", "gates": dict(GOOD_GATES), "fault_events": [],
                              "final_phase": "ready",
                              "controller_tag": judge.TAG_P3 if setting == "VB"
                              else judge.TAG_V0})
    for index, change in changes.items():
        lines[int(index[1:])].update(change)
    return lines


def _family(tmp_path: Path, lines: list[dict], *extra: str) -> tuple[int, dict]:
    path = _write(tmp_path / "h9_family_F.jsonl", lines)
    return _main(["family-f", "--lines", str(path), *extra], tmp_path / "f.json")


def test_family_f_pass_and_record_values(tmp_path: Path) -> None:
    code, report = _family(tmp_path, _family_lines())
    assert code == 0 and report["result"] == "통과"
    assert report["k"] == {f"{s}|{k}": 0 for s in ("V0", "VB") for k in judge.FAMILY_F_KEYS}
    assert report["R-3"] is True and report["R-4"] is True


def test_family_f_r3_uses_fault_events_and_r4_the_v0_pair(tmp_path: Path) -> None:
    lines = _family_lines(i32={"fault_events": ["FAULT_X"]})  # VB, first FR line
    lines[33]["gates"] = {**GOOD_GATES, "end_att": False}  # VB false, V0 true: R-4
    code, report = _family(tmp_path, lines)
    assert report["result"] == "실패" and report["R-3"] is False and report["R-4"] is False
    assert report["R-4_violations"] == [{"key": lines[33]["key"], "offset_s": 0.00625,
                                         "gates": ["end_att"]}]


def test_family_f_gate_on_one_side_or_missing_is_not_judgeable(tmp_path: Path) -> None:
    lines = _family_lines()
    lines[40]["gates"] = {**GOOD_GATES, "extra": True}  # VB only
    del lines[50]["gates"]["U57_outside"]
    code, report = _family(tmp_path, lines)
    assert code == 1 and report["result"] == "판정 불가" and report["pass"] is False
    assert {u["item"] for u in report["not_judgeable"]} == {"R-4 (gate names differ)",
                                                            "k (two gates)"}


def test_family_f_shape_and_tag_stops(tmp_path: Path) -> None:
    lines = _family_lines()
    lines[0]["event"] = "G4"
    lines[63]["controller_tag"] = judge.TAG_V0
    code, report = _family(tmp_path, lines[:63] + [lines[63]] + [lines[62]])
    problems = " ".join(report["problems"])
    assert code == 1 and "S-15" in problems and "S-2 line 64" in problems


# The family F application (--grid-root, supplement 6-3) is tested with the full synthetic grid
# in test_resume4368_supplement5.py.


# --------------------------------------------------------------------------- audit A-4
def test_head_check_r4_without_files_is_s11(tmp_path: Path) -> None:
    code, report = _main(["head-check", "--expect", "0" * 40, "--r4", "0" * 40],
                         tmp_path / "h.json")
    assert code == 1 and "S-11 (RD-1 4: --r4 without --files)" in report["markers"]
