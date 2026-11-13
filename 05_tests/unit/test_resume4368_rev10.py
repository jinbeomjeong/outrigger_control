"""436.8 rules rev10 (``v5_resume_4368_rules_rev10.md``, sealed 62a0bd8d) in the path 1 tools.

R10-3: the three seal lists carry rev10. R10-1a: the full batch name (``batch.json`` ``batch``
checked against the folder name part, a manifest ``batches`` key). R10-1b: unknown batch name,
zero / several manifest rows and zero / several ``batch.json`` entries = LS not judgeable; a
missing / unreadable manifest = input error (exit 2); not LS only with exactly one row per source
and no value on both. Synthetic inputs and the stored manifest only.
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

REV10_NAME = "v5_resume_4368_rules_rev10.md"
REV10_SHA256 = "62a0bd8dd6644f78bf37d052e884061d8c14e1cc96e2babc72a6ac0618f12c29"
C5 = "V5-RESUME-K1-C5"
MANIFEST = chrono_judge.load_manifest(chrono_judge.MANIFEST_DEFAULT)


# ------------------------------------------------------------------------------ R10-3 seals
def test_every_path1_seal_list_has_rev10() -> None:
    assert (judge.RULES_REV10_NAME, judge.RULES_REV10_SHA256) == (REV10_NAME, REV10_SHA256)
    assert (REV10_NAME, REV10_SHA256) in judge.SEALED_REVISIONS
    assert (REV10_NAME, REV10_SHA256) in common.SEALED_RULES
    assert chrono_judge.RULES_SEALS[REV10_NAME] == REV10_SHA256


def test_stored_rev10_matches_its_seal() -> None:
    assert judge.sealed_rules_check()["problems"] == []
    assert common.seal_report()["problems"] == []
    assert chrono_judge.seal_check(common.RULES_DIR)["ok"] is True


@pytest.mark.parametrize("missing", [REV10_NAME, REV10_NAME.replace(".md", ".sha256")])
def test_a_missing_rev10_file_is_s1(tmp_path: Path, missing: str) -> None:
    for name in [*chrono_judge.RULES_SEALS, *(n for n, _ in judge.SEALED_REVISIONS)]:
        source = common.RULES_DIR / name
        for path in (source, source.with_suffix(".sha256")):
            shutil.copy2(path, tmp_path / path.name)
    (tmp_path / missing).unlink()
    assert judge.sealed_rules_check(tmp_path)["stop_S1"] is True
    assert common.seal_report(tmp_path)["stop_S1"] is True
    assert chrono_judge.seal_check(tmp_path)["ok"] is False


# ----------------------------------------------------------------------- R10-1a batch name
FOLDER = f"07_results/S9/batch_{C5}_20261113_120000"


def test_batch_full_name_from_the_batch_key_checked_against_the_folder() -> None:
    assert chrono_judge.batch_full_name(FOLDER, {"batch": C5}, MANIFEST)["name"] == C5
    assert chrono_judge.batch_full_name(FOLDER, {}, MANIFEST)["name"] == C5  # no key: folder part


@pytest.mark.parametrize(
    ("folder", "doc"),
    [
        (FOLDER, {"batch": "V5-RESUME-K1-C1"}),  # key differs from the folder part
        (FOLDER, {"batch": "C5"}),  # short batch ID (original 4.3) is not the full name
        ("07_results/S9/some_folder", {}),  # no key, folder not batch_<name>_<stamp>
        ("07_results/S9/batch_V5-RESUME-K1-ZZ_20261113_120000", {}),  # not a manifest batches key
        ("07_results/S9/some_folder", {"batch": C5}),  # key without a folder part to check it with
    ],
)
def test_batch_full_name_unknown(folder: str, doc: dict) -> None:
    assert chrono_judge.batch_full_name(folder, doc, MANIFEST)["name"] is None


# ----------------------------------------------------------------------- R10-1b boundaries
def _meta(case: str, *, batch_doc: dict | None = None, count: int = 1, **extra) -> dict:
    meta = {"case": case, "_batch_case_count": count, **extra}
    meta["_batch_name"] = chrono_judge.batch_full_name(FOLDER, batch_doc or {"batch": C5}, MANIFEST)
    return meta


def test_ls_boundary_cases() -> None:
    ls = chrono_judge.ls_setting(_meta("E_G4_Fs8_LS1", v5_setting="LS1"), MANIFEST)
    assert (ls["is_ls"], ls["boundary_case"]) == (True, None)
    unknown = chrono_judge.ls_setting(
        _meta("E_G4_Fs8_LS1", batch_doc={"batch": "C5"}, v5_setting="LS1"), MANIFEST
    )
    assert (unknown["is_ls"], unknown["boundary_case"]) == (None, "batch_name_unknown")
    no_row = chrono_judge.ls_setting(_meta("NOT_A_CASE"), MANIFEST)
    assert (no_row["is_ls"], no_row["boundary_case"]) == (None, "manifest_rows_not_one")
    for count in (0, 2):
        entries = chrono_judge.ls_setting(
            _meta("E_G4_Fs8_LS1", count=count, v5_setting="LS1"), MANIFEST
        )
        assert (entries["is_ls"], entries["boundary_case"]) == (None, "batch_json_entries_not_one")


def test_several_manifest_rows_are_not_judgeable() -> None:
    manifest = {"batches": {C5: {"rows": [{"case": "X"}, {"case": "X"}]}}}
    meta = {
        "case": "X",
        "_batch_case_count": 1,
        "_batch_name": chrono_judge.batch_full_name(FOLDER, {"batch": C5}, manifest),
    }
    assert chrono_judge.ls_setting(meta, manifest)["boundary_case"] == "manifest_rows_not_one"


def test_not_ls_only_with_one_row_per_source_and_no_value() -> None:
    manifest = {"batches": {C5: {"rows": [{"case": "X", "v5_setting": None}]}}}
    meta = {
        "case": "X",
        "_batch_case_count": 1,
        "_batch_name": chrono_judge.batch_full_name(FOLDER, {"batch": C5}, manifest),
    }
    both = chrono_judge.ls_setting(meta, manifest)
    assert (both["is_ls"], both["boundary_case"]) == (False, "both_sources_without_v5_setting")
    assert chrono_judge.ls_setting({**meta, "_batch_case_count": 0}, manifest)["is_ls"] is None


def test_without_a_batch_record_the_batch_name_is_unknown() -> None:
    out = chrono_judge.ls_setting({"case": "E_G4_Fs8_LS1", "criteria_id": "C-5"}, MANIFEST)
    assert (out["is_ls"], out["boundary_case"]) == (None, "batch_name_unknown")


@pytest.mark.parametrize("content", [None, "{", json.dumps({"rows": []}), json.dumps([1])])
def test_missing_or_unreadable_manifest_is_an_input_error(tmp_path: Path, content) -> None:
    path = tmp_path / "manifest.json"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    with pytest.raises(chrono_judge.InputError):
        chrono_judge.load_manifest(path)


def test_judge_exits_2_without_a_manifest(tmp_path: Path, capsys) -> None:
    code = chrono_judge.main(
        [
            "judge",
            "--git-at-start",
            "4312b8e",
            "--out",
            str(tmp_path / "o.json"),
            "--row",
            str(tmp_path),
            "--manifest",
            str(tmp_path / "none.json"),
        ]
    )
    assert code == 2 and "manifest missing" in capsys.readouterr().out


def test_ls_source_check_counts(tmp_path: Path) -> None:
    folder = tmp_path / f"batch_{C5}_20261113_120000"
    folder.mkdir()
    cases = [
        {"case": "E_G4_Fs8_LS1", "v5_setting": "LS1"},
        {"case": "E_G4_Fs8", "v5_setting": "VB"},
        {"case": "E_G4_Fs8", "v5_setting": "VB"},
        {"case": "NOT_A_CASE"},
    ]
    (folder / "batch.json").write_text(json.dumps({"batch": C5, "cases": cases}), encoding="utf-8")
    check = chrono_judge.ls_source_check(folder, MANIFEST)
    assert check["batch_name"]["name"] == C5 and check["s11_rows"] == 2
    assert check["counts"]["batch_json_entries_not_one"] == 1
    assert check["counts"]["manifest_rows_not_one"] == 1
