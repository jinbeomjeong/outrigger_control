"""436.9 edition 6 Y-13 (``jp3_remedy_spec_v6_erratum1.md`` 1-3): the T-JR-12a bundle VBL
against VBL0 in ``jp3_tjr_judge.py``, the edition 5 VBJ bundle replay, and the edition 6 fixed
input list (erratum 1 1-2, ``jp3_fixed_inputs_list.py --edition 6``).

The replay reads the edition 5 run folder of the main checkout (``MAIN_CHECKOUT``); every
``main`` runs with the working folder elsewhere (tool rule (가)).
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
for _path in (COUPLED_DIR, ROOT / "03_src", Path(__file__).resolve().parent):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import jp3_baseline_compare as compare  # noqa: E402
import jp3_ed6_judge as ed6  # noqa: E402
import jp3_fixed_inputs_list as fixed_list  # noqa: E402
import jp3_tjr_judge as tjr  # noqa: E402
from test_jp3_12b_tools import _check_record  # noqa: E402
from test_jp3_ed5_erratum1 import _list_args, list_repo  # noqa: E402,F401  (fixture)

MAIN_CHECKOUT = Path(r"C:\workspace\outrigger_control")
ED5_DG3 = MAIN_CHECKOUT / "06_analysis" / "02_control" / "j_p3_cause" / "j9_runs" / "606f8713" \
    / "dg3_a1"
L1_KEYS = MAIN_CHECKOUT / "06_analysis" / "02_control" / "j_p3_cause" / "prelaunch_j9" \
    / "l1_keys_d3c6c57e.json"
SEALED = ["A_i", "A_ii", "B3"]


# ------------------------------------------------------------------------------- J-P3 rows
def _jp3_line(grade: str = "normal") -> dict:
    return {"hydraulics_record": {"extend_bound_check": {**_check_record(),
                                                         "sensor_grade": grade}},
            "has_rod_reading": True}


@pytest.mark.parametrize(("grades", "vbl", "vbj"), [
    (["normal"], ("pass", [], []), ("pass", [], [])),
    (["normal", "normal"], ("setting_defect", ["setting"], []),
     ("not_judgeable", [], ["not_judgeable"])),
    (["conservative"], ("not_judgeable", [], ["not_judgeable"]),
     ("not_judgeable", [], ["not_judgeable"])),
])
def test_vbl_jp3_judged_rows_other_than_1(grades, vbl, vbj) -> None:
    """Erratum 1 1-3 5 / 8: VBL judged rows other than 1 are a setting defect (0: not
    judgeable); the edition 5 VBJ bundle keeps 4a-7 erratum 1 7 (not judgeable)."""
    lines = [_jp3_line(grade) for grade in grades]
    for bundle, (outcome, defects, unjudged) in (("VBL", vbl), ("VBJ", vbj)):
        problems = compare.Problems()
        found = tjr._dg3_j_p3(lines, problems, bundle)
        assert found["outcome"] == outcome, bundle
        assert bool(problems.setting_defects) == bool(defects), bundle
        assert bool(problems.not_judgeable) == bool(unjudged), bundle
        assert all(text.startswith(f"{bundle}:") for text in
                   problems.setting_defects + problems.not_judgeable)


# ------------------------------------------------------------------------------- identity
@pytest.fixture(scope="module")
def sealed_settings() -> dict:
    return ed6.sealed_lsb_settings()


def _side(folder: Path, setting: str, settings: dict, *, p3_on: bool, edit=None) -> dict:
    """One Dg-3 side of two lines with their T4h meta (the r79 form)."""
    folder.mkdir(parents=True)
    results = []
    for index in range(2):
        key = f"cand=current#L2|s0|g6|{index}|x{index}|top|Fs0"
        name = f"line{index}.npz"
        line = {"key": key, "v5_setting": setting, "t4h_file": name, "run_extend_start_revision":
                6 if p3_on else None,
                "hydraulic_options": dict.fromkeys(("extend_start_tracked", "extend_start_hold",
                                                    "extend_start_witness"), p3_on),
                "hydraulics_record": {"extend_bound_check": _check_record() if p3_on else None}}
        if not p3_on:
            del line["run_extend_start_revision"]
        meta = {"controller_tag": ed6.ED6_TAG if p3_on else ed6.ED6_P3_OFF_TAG,
                "lsb_components": list(SEALED), "lsb_settings": copy.deepcopy(settings)}
        if edit is not None:
            edit(index, line, meta)
        np.savez(folder / name, meta_json=np.array(json.dumps(meta)))
        results.append(line)
    return {"results": results}


def _problems(tmp_path: Path, settings: dict, new_edit=None, base_edit=None) -> dict:
    new = _side(tmp_path / "new", "VBL", settings, p3_on=True, edit=new_edit)
    base = _side(tmp_path / "base", "VBL0", settings, p3_on=False, edit=base_edit)
    return tjr.ed6_bundle_problems(base, new, tmp_path / "base", tmp_path / "new")


def test_vbl_bundle_identity_holds(tmp_path, sealed_settings) -> None:
    assert _problems(tmp_path, sealed_settings) == {"setting_defects": [], "not_judgeable": []}


def test_vbl0_line_with_a_p3_record_is_a_defect(tmp_path, sealed_settings) -> None:
    def record(index, line, meta):
        if index == 0:
            line["hydraulics_record"]["extend_bound_check"] = _check_record()

    found = _problems(tmp_path, sealed_settings, base_edit=record)
    assert found["setting_defects"] == ["base cand=current#L2|s0|g6|0|x0|top|Fs0: a ③ record "
                                        "on a ③-off VBL0 line"]


@pytest.mark.parametrize("side", ["new", "base"])
def test_other_lsb_settings_are_a_defect(tmp_path, sealed_settings, side) -> None:
    def changed(index, line, meta):
        meta["lsb_settings"] = {**meta["lsb_settings"], "a1_cap_m_s": 2e-3}

    edits = {"new_edit": changed} if side == "new" else {"base_edit": changed}
    found = _problems(tmp_path, sealed_settings, **edits)
    assert len(found["setting_defects"]) == 2
    assert all(text.startswith(side) and "lsb_settings" in text
               for text in found["setting_defects"])


def test_vbl_tag_components_and_missing_t4h(tmp_path, sealed_settings) -> None:
    def old_tag(index, line, meta):
        meta["controller_tag"] = "final_C4G2_P3W_LAS_K1"
        meta["lsb_components"] = ["A_i", "A_ii"]

    found = _problems(tmp_path / "a", sealed_settings, new_edit=old_tag)
    assert len(found["setting_defects"]) == 4
    found = _problems(tmp_path / "b", sealed_settings)
    (tmp_path / "b" / "new" / "line1.npz").unlink()
    new = {"results": [{"key": "k", "t4h_file": "line1.npz"}]}
    found = tjr.ed6_bundle_problems({"results": []}, new, tmp_path / "b" / "base",
                                    tmp_path / "b" / "new")
    assert found["not_judgeable"] == ["new k: no T4h meta lsb_components / lsb_settings"]
    found = tjr.ed6_bundle_problems({"results": []}, new, None, tmp_path / "b" / "new")
    assert found["not_judgeable"][-1] == "--base-t4h missing (edition 6 identity)"


# ------------------------------------------------------------------------------- L1 inputs
def _l1_run(path: Path, setting: str) -> Path:
    keys = [row["key"] for row in json.loads(L1_KEYS.read_text(encoding="utf-8"))["results"]]
    lines = []
    for key in keys:
        tokens = key.split("|", 4)
        lines.append({"key": key, "level": "L1", "rod_model": "plant_truth",
                      "v5_setting": setting, "candidate": "current", "harness": tokens[2],
                      "inner": tokens[4]})
    meta = {"keys_file": {"sha256": hashlib.sha256(L1_KEYS.read_bytes()).hexdigest(),
                          "n_keys": len(keys)}}
    path.write_text(json.dumps({"meta": meta, "results": lines}), encoding="utf-8")
    return path


def test_l1_reference_of_another_setting_is_not_judgeable(tmp_path) -> None:
    """Erratum 1 1-3 3 / 8: each arm's L1 is its own setting's (4a-8 4.3)."""
    own = _l1_run(tmp_path / "l1_vbl.json", "VBL")
    assert tjr.l1_run_problems("VBL", own, L1_KEYS) == []
    other = _l1_run(tmp_path / "l1_vbj.json", "VBJ")
    problems = tjr.l1_run_problems("VBL", other, L1_KEYS)
    assert problems == ["VBL: 102 L1 lines with v5_setting other than 'VBL' (4a-8 4.3)"]
    inputs = tjr.Dg3JudgeInputs("VBL", tmp_path / "dg3.json", other,
                                hashlib.sha256(other.read_bytes()).hexdigest(),
                                tmp_path / "judge.json", L1_KEYS)
    (tmp_path / "dg3.json").write_text(json.dumps({"results": []}), encoding="utf-8")
    assert any("other than 'VBL'" in text for text in tjr.dg3_input_problems(inputs))
    assert "VBL" in tjr.PLANT_TRUTH_SETTINGS and "VBL0" in tjr.DG3_JUDGE_SETTINGS


# ------------------------------------------------------------------------------- VBJ replay
def test_edition_5_vbj_bundle_replay_equals_the_judgement(tmp_path, monkeypatch) -> None:
    """Erratum 1 1-3 1 / 8: ``t12 --bundle VBJ`` of the edition 5 run (606f8713, the step 6
    command) gives the stored judgement file (every key but the output path and command)."""
    judge = ED5_DG3 / "judge"
    stored = json.loads((judge / "t12_VBJ.json").read_text(encoding="utf-8"))
    out = tmp_path / "t12_VBJ.json"
    sha = "e3593c869d366ecb526cd998c3228eda25560c63a49589feef49dd8261d9794a"
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    code = tjr.main(["t12", "--bundle", "VBJ", "--base", str(ED5_DG3 / "dg3_VBJ0.json"),
                     "--base-judge", str(judge / "dg3_VBJ0_judge.json"), "--base-judge-sha256",
                     sha, "--new", str(ED5_DG3 / "dg3_VBJ.json"), "--new-judge",
                     str(judge / "dg3_VBJ_judge.json"), "--new-judge-sha256", sha,
                     "--out", str(out)])
    replay = json.loads(out.read_text(encoding="utf-8"))
    ignored = {"command", "out"}
    assert {k: v for k, v in replay.items() if k not in ignored} == {
        k: v for k, v in stored.items() if k not in ignored}
    assert code == {"pass": 0, "failed": 1}.get(stored["status"], 2)


# ------------------------------------------------------------------------------- fixed list
def test_fixed_list_edition_6(list_repo, tmp_path, monkeypatch) -> None:  # noqa: F811 (fixture)
    """Erratum 1 1-2: edition 6 needs no dry selection, but every sealed key and L1 key file
    with its sha256; edition 5 still needs the dry selection."""
    repo, entries, commit, worktree = list_repo
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    required = {"06_analysis/doc.md": hashlib.sha256(b"rule\n").hexdigest()}
    monkeypatch.setattr(fixed_list, "ED6_REQUIRED_SHA256", required)
    base = [arg for arg in _list_args(repo, entries, commit, tmp_path / "x", worktree)]
    without_dry = base[:base.index("--dry-selection")] + base[base.index("--dry-selection") + 2:]

    def run(name: str, *extra: str) -> int:
        out = tmp_path / f"{name}_{commit[:8]}.SHA256SUMS"
        args = [*without_dry[:-1], str(out), *extra]
        return fixed_list.main(args)

    assert run("ed6", "--edition", "6") == fixed_list.EXIT_WRITTEN
    written = (tmp_path / f"ed6_{commit[:8]}.SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert written[0] == f"# run_commit {commit}"  # erratum 2 2-3 3
    assert all(not line.startswith("#") for line in written[1:])
    assert run("ed5") == fixed_list.EXIT_NOT_USABLE  # edition 5 needs --dry-selection
    monkeypatch.setattr(fixed_list, "ED6_REQUIRED_SHA256", {"06_analysis/doc.md": "0" * 64})
    assert run("sha", "--edition", "6") == fixed_list.EXIT_NOT_USABLE
    monkeypatch.setattr(fixed_list, "ED6_REQUIRED_SHA256", {"06_analysis/none.json": "0" * 64})
    assert run("missing", "--edition", "6") == fixed_list.EXIT_NOT_USABLE


def test_edition_6_required_inputs_have_their_sealed_sha256() -> None:
    for name, sha in fixed_list.ED6_REQUIRED_SHA256.items():
        assert hashlib.sha256((MAIN_CHECKOUT / name).read_bytes()).hexdigest() == sha, name
