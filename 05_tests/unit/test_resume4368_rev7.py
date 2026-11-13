"""436.8 rules rev7 (``v5_resume_4368_rules_rev7.md``, sealed e81f7d31) in the path 1 tools.

R7-7: the seal lists of ``resume4368_judge``, ``judge4368_common`` and
``chrono_rows_judge_4368`` carry rev7, and each tool stops (S-1) when the rev7 file or its
``.sha256`` is missing or differs. R7-1a: ``gs`` / ``record-check`` compare the top-level
``controller_tag`` of r79 / grid results with the T4h meta tag of the same run (S-2 when they
differ or only one side has a tag). Synthetic inputs only; no harness or Chrono run.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

ROOT = Path(__file__).resolve().parents[2]
COUPLED = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
CHRONO_SCRIPTS = ROOT / "04_scripts" / "02_chrono"
SCRIPTS = ROOT / "06_analysis" / "02_control" / "verif_matrix" / "scripts"
for _path in (COUPLED, CHRONO_SCRIPTS, SCRIPTS, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import chrono_rows_judge_4368 as chrono_judge  # noqa: E402
import judge4368_common as common  # noqa: E402
import resume4368_judge as judge  # noqa: E402

REV7_NAME = "v5_resume_4368_rules_rev7.md"
REV7_SHA256 = "e81f7d31779b0d69a140c9d90aa4684f3c9299e84aec6af06b13d48d58631502"
TAG_P3 = "final_C4G2_P3_LAS_K1"
TAG_V0 = "final_C4G2_LAS_K1"
TAG_BEFORE_FIX = "final_C4G2_P3"
"""The b1ddeae G-S top-level tag of H-6 / H-8 / grid (rev7 R7-1b record defect)."""


# ------------------------------------------------------------------------------- R7-7 seals
def test_every_path1_seal_list_has_rev7() -> None:
    assert (judge.RULES_REV7_NAME, judge.RULES_REV7_SHA256) == (REV7_NAME, REV7_SHA256)
    assert (REV7_NAME, REV7_SHA256) in judge.SEALED_REVISIONS
    assert (REV7_NAME, REV7_SHA256) in common.SEALED_RULES
    assert chrono_judge.RULES_SEALS[REV7_NAME] == REV7_SHA256


def test_stored_rev7_matches_its_seal() -> None:
    assert judge.sealed_rules_check()["problems"] == []
    assert common.seal_report()["problems"] == []
    assert chrono_judge.seal_check(common.RULES_DIR)["ok"] is True


def _copy_sealed_rules(target: Path) -> None:
    for name in [*chrono_judge.RULES_SEALS, *(n for n, _ in judge.SEALED_REVISIONS)]:
        source = common.RULES_DIR / name
        for path in (source, source.with_suffix(".sha256")):
            shutil.copy2(path, target / path.name)


def _seal_findings(folder: Path) -> tuple[bool, bool, bool]:
    """(resume4368_judge S-1, judge4368_common S-1, chrono seal not ok) for one rules folder."""
    return (judge.sealed_rules_check(folder)["stop_S1"], common.seal_report(folder)["stop_S1"],
            not chrono_judge.seal_check(folder)["ok"])


def test_rev7_seal_holds_on_a_copy(tmp_path: Path) -> None:
    _copy_sealed_rules(tmp_path)
    assert _seal_findings(tmp_path) == (False, False, False)


def test_a_changed_rev7_file_is_s1(tmp_path: Path) -> None:
    _copy_sealed_rules(tmp_path)
    rules = tmp_path / REV7_NAME
    rules.write_bytes(rules.read_bytes().replace(b"\n", b"\r\n"))  # sealed raw: CRLF differs
    assert _seal_findings(tmp_path) == (True, True, True)


def test_a_rev7_seal_file_with_another_value_is_s1(tmp_path: Path) -> None:
    _copy_sealed_rules(tmp_path)
    seal = tmp_path / "v5_resume_4368_rules_rev7.sha256"
    seal.write_text(f"{'0' * 64}  {REV7_NAME}\n", encoding="utf-8")
    assert _seal_findings(tmp_path) == (True, True, True)


@pytest.mark.parametrize("missing", [REV7_NAME, "v5_resume_4368_rules_rev7.sha256"])
def test_a_missing_rev7_file_is_s1(tmp_path: Path, missing: str) -> None:
    _copy_sealed_rules(tmp_path)
    (tmp_path / missing).unlink()
    assert _seal_findings(tmp_path) == (True, True, True)


# --------------------------------------------------------------------------- R7-1a tag check
def _r79_result(key: str, top_tag: str | None, t4h_file: str | None) -> dict:
    record: dict = {"key": key, "seed_index": 0, "harness": "g8", "inner": 0}
    if top_tag is not None:
        record["controller_tag"] = top_tag
    if t4h_file is not None:
        record["t4h_file"] = t4h_file
    return record


def _write_t4h(folder: Path, name: str, meta: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    np.savez(folder / name, t_s=np.zeros(2), meta_json=np.array(json.dumps(meta)))


def _write_result(path: Path, results: list[dict]) -> Path:
    path.write_text(json.dumps({"meta": {}, "results": results}), encoding="utf-8")
    return path


def test_tags_equal_on_both_sides_match(tmp_path: Path) -> None:
    _write_t4h(tmp_path / "h6_t4h", "a.npz", {"controller_tag": TAG_P3})
    result = _write_result(tmp_path / "h6.json", [_r79_result("a", TAG_P3, "a.npz")])
    check = judge.r79_tag_check([result])
    assert (check["compared"], check["mismatched"], check["stop_S2"]) == (1, 0, False)


@pytest.mark.parametrize(
    ("top_tag", "meta", "reason"),
    [
        (TAG_BEFORE_FIX, {"controller_tag": TAG_P3}, "differs"),  # b1ddeae H-6 / H-8
        (None, {"controller_tag": TAG_V0}, "T4h meta only"),  # b1ddeae H-7
        (TAG_P3, {"controller_tag": None}, "top level only"),
        (TAG_P3, {}, "top level only"),
    ],
)
def test_different_or_one_sided_tags_are_s2(tmp_path: Path, top_tag, meta, reason) -> None:
    _write_t4h(tmp_path / "h6_t4h", "a.npz", meta)
    result = _write_result(tmp_path / "h6.json", [_r79_result("a", top_tag, "a.npz")])
    check = judge.r79_tag_check([result])
    assert (check["compared"], check["mismatched"], check["stop_S2"]) == (1, 1, True)
    assert reason in check["rows"][0]["reason"] and check["rows"][0]["status"] == "S-2"


def test_a_listed_t4h_file_that_is_not_found_is_s2(tmp_path: Path) -> None:
    result = _write_result(tmp_path / "h6.json", [_r79_result("a", TAG_P3, "a.npz")])
    check = judge.r79_tag_check([result])
    assert check["stop_S2"] is True and "not found" in check["rows"][0]["reason"]


def test_t4h_folder_conventions_and_option(tmp_path: Path) -> None:
    """``<stem>_t4h/`` (resume_k1_steps) and ``t4h/`` (las_t3), and ``--t4h-dir`` first."""
    _write_t4h(tmp_path / "t4h", "a.npz", {"controller_tag": TAG_P3})
    result = _write_result(tmp_path / "result.json", [_r79_result("a", TAG_P3, "a.npz")])
    assert judge.r79_tag_check([result])["stop_S2"] is False
    _write_t4h(tmp_path / "elsewhere", "a.npz", {"controller_tag": TAG_V0})
    assert judge.r79_tag_check([result], [tmp_path / "elsewhere"])["stop_S2"] is True


def test_runs_without_a_t4h_record_are_not_compared(tmp_path: Path) -> None:
    """Grid job records and r79 runs without ``R79_T4H_DIR`` (rev7 gives no comparison)."""
    grid = {"meta": {}, "results": [{"key": "g", "controller_tag": TAG_BEFORE_FIX,
                                     "runs": [{"event": "FS24"}]}]}
    grid_path = tmp_path / "grid.json"
    grid_path.write_text(json.dumps(grid), encoding="utf-8")
    r79 = _write_result(tmp_path / "seedext.json", [_r79_result("s", TAG_BEFORE_FIX, None)])
    check = judge.r79_tag_check([grid_path, r79])
    assert (check["compared"], check["not_compared"], check["stop_S2"]) == (0, 2, False)
    assert check["not_compared_by_file"] == {str(grid_path): 1, str(r79): 1}


def _run_cli(argv: list[str], monkeypatch) -> tuple[int, dict]:
    monkeypatch.setattr(judge, "sealed_rules_check", lambda: {"problems": [], "stop_S1": False})
    code = judge.main(argv)
    out = Path(argv[argv.index("--out") + 1])
    return code, json.loads(out.read_text(encoding="utf-8"))


def test_gs_stops_on_a_tag_mismatch_without_printing_values(tmp_path: Path, monkeypatch) -> None:
    _write_t4h(tmp_path / "h7_t4h", "a.npz", {"controller_tag": TAG_V0})
    result = _write_result(tmp_path / "h7.json", [_r79_result("a", None, "a.npz")])
    code, report = _run_cli(["gs", "--harness", str(result), "--out",
                             str(tmp_path / "gs.json")], monkeypatch)
    assert code == 1 and report["stop_S2"] is True
    row = report["r79_tag_check"]["rows"][0]
    assert "top_tag" not in row and "t4h_tag" not in row  # gs reports presence only


def test_record_check_reports_the_tag_values(tmp_path: Path, monkeypatch) -> None:
    _write_t4h(tmp_path / "x", "a.npz", {"controller_tag": TAG_P3})
    result = _write_result(tmp_path / "h6.json", [_r79_result("a", TAG_BEFORE_FIX, "a.npz")])
    code, report = _run_cli(["record-check", "--harness", str(result), "--t4h-dir",
                             str(tmp_path / "x"), "--out", str(tmp_path / "rc.json")],
                            monkeypatch)
    assert code == 1 and report["stop_S2"] is True
    row = report["r79_tag_check"]["rows"][0]
    assert (row["top_tag"], row["t4h_tag"]) == (TAG_BEFORE_FIX, TAG_P3)
