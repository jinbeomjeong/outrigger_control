"""436.8 rules rev9 (``v5_resume_4368_rules_rev9.md``) in the path 1 tools.

R9-8: the seal lists of ``resume4368_judge``, ``judge4368_common`` and ``chrono_rows_judge_4368``
carry rev9 (S-1 when the file or its ``.sha256`` is missing or differs). R9-7: the recomputed tag
of K1 alone is ``final_C4G2_K1`` and of ③ + K1 without LAS-b ``final_C4G2_P3_K1``. R9-1: a
Chrono row whose ``expect_controller.ok`` is false or missing is S-2 in ``record-check``. The
J11 / LS / form items (R9-2 .. R9-6) are tested in ``test_resume4368_rev8.py``.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
CHRONO_SCRIPTS = ROOT / "04_scripts" / "02_chrono"
SCRIPTS = ROOT / "06_analysis" / "02_control" / "verif_matrix" / "scripts"
for _path in (COUPLED, CHRONO_SCRIPTS, SCRIPTS, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

pytest.importorskip("numpy")

import chrono_rows_judge_4368 as chrono_judge  # noqa: E402
import judge4368_common as common  # noqa: E402
import resume4368_judge as judge  # noqa: E402

REV9_NAME = "v5_resume_4368_rules_rev9.md"
REV9_SEAL = REV9_NAME.replace(".md", ".sha256")


def test_every_path1_seal_list_has_rev9() -> None:
    sha = judge.RULES_REV9_SHA256
    assert judge.RULES_REV9_NAME == REV9_NAME and len(sha) == 64
    assert (REV9_NAME, sha) in judge.SEALED_REVISIONS
    assert (REV9_NAME, sha) in common.SEALED_RULES
    assert chrono_judge.RULES_SEALS[REV9_NAME] == sha


def test_stored_rev9_matches_its_seal() -> None:
    assert judge.sealed_rules_check()["problems"] == []
    assert common.seal_report()["problems"] == []
    assert chrono_judge.seal_check(common.RULES_DIR)["ok"] is True


def _copy_sealed_rules(target: Path) -> None:
    for name in [*chrono_judge.RULES_SEALS, *(n for n, _ in judge.SEALED_REVISIONS)]:
        source = common.RULES_DIR / name
        for path in (source, source.with_suffix(".sha256")):
            shutil.copy2(path, target / path.name)


def _seal_findings(folder: Path) -> tuple[bool, bool, bool]:
    return (judge.sealed_rules_check(folder)["stop_S1"], common.seal_report(folder)["stop_S1"],
            not chrono_judge.seal_check(folder)["ok"])


def test_a_changed_rev9_file_is_s1(tmp_path: Path) -> None:
    _copy_sealed_rules(tmp_path)
    assert _seal_findings(tmp_path) == (False, False, False)
    rules = tmp_path / REV9_NAME
    rules.write_bytes(rules.read_bytes().replace(b"\n", b"\r\n"))
    assert _seal_findings(tmp_path) == (True, True, True)


@pytest.mark.parametrize("missing", [REV9_NAME, REV9_SEAL])
def test_a_missing_rev9_file_is_s1(tmp_path: Path, missing: str) -> None:
    _copy_sealed_rules(tmp_path)
    (tmp_path / missing).unlink()
    assert _seal_findings(tmp_path) == (True, True, True)


def test_r9_7_k1_alone_tags() -> None:
    assert judge.recompute_tag(False, False, True) == "final_C4G2_K1"
    assert judge.recompute_tag(True, False, True) == "final_C4G2_P3_K1"
    assert judge.recompute_tag(False, False, False) is None


@pytest.mark.parametrize("check", [{"ok": False}, None])
def test_r9_1_record_check_expect_controller(tmp_path: Path, monkeypatch, check) -> None:
    batch = tmp_path / "batch_V5-RESUME-K1-C5_20261113_120000"
    case = batch / "row"
    case.mkdir(parents=True)
    argv = ["python", "04_scripts/02_chrono/run_S9.py", "level", "--expect-controller",
            "final_C4G2_LAS_K1"]
    (batch / "batch.json").write_text(json.dumps({"cases": [{"case": "row", "argv": argv}]}),
                                      encoding="utf-8")
    result = {"c2_setup": {} if check is None else {"expect_controller": check}}
    (case / "result.json").write_text(json.dumps(result), encoding="utf-8")
    monkeypatch.setattr(judge, "sealed_rules_check", lambda: {"problems": [], "stop_S1": False})
    out = tmp_path / "rc.json"
    assert judge.main(["record-check", "--chrono", str(batch), "--out", str(out)]) == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["stop_S2"] is True and report["expect_controller_failed_R9_1"] == ["row"]
