"""Addendum 4a-6 5 G-1 .. G-3 (user decision 2026-11-21): the dry key scan leaves out the J-P3
run outputs (scan-root relative paths starting with ``02_control/j_p3_cause/j9_runs/``, case as
it is, ``/`` separated): their dry r79 runs hold the dry key itself, so an earlier attempt
must not move the generated seed. The same key outside them stops the selection (not
judgeable). Synthetic scan roots only."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import jp3_dryrun_evidence as dryrun  # noqa: E402

BASE_KEY = "L2|s0|g6|0|g6|G1+J1@FL|top|Fs0"
DRY_KEY = "L2|s25|g6|0|g6|G1+J1@FL|top|Fs0"
RUN_OUTPUTS = "02_control/j_p3_cause/j9_runs/b51ed6e1/dry_a1"


def _r79_file(path: Path, key: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"meta": {}, "results": [{"key": f"cand=current#{key}"}]}),
                    encoding="utf-8")
    return path


def _scan_root(tmp_path: Path) -> Path:
    root = tmp_path / "06_analysis"
    _r79_file(root / "03_hydraulic" / "stored.json", "L2|s24|g6|0|g6|G1+J1@FL|top|Fs0")
    return root


def _selection(tmp_path: Path, root: Path, monkeypatch) -> dict:
    """``select`` on a synthetic scan root (fixed inputs and the event union stubbed)."""
    monkeypatch.setattr(dryrun, "fixed_input_problems", lambda inputs: [])
    monkeypatch.setattr(dryrun, "judged_union", lambda *args: {"event_union": set(),
                                                               "sizes": {}})
    dg3 = tmp_path / "dg3.json"
    dg3.write_text(json.dumps({"results": [{"key": "cand=current#L3|s0|h|1|x"}]}),
                   encoding="utf-8")
    noise = tmp_path / "noise.json"
    noise.write_text(json.dumps({"results": [{"key": f"cand=current#{BASE_KEY}",
                                              "level": "L2"}]}), encoding="utf-8")
    inputs = dryrun.SelectInputs(root, tmp_path / "main.jsonl", tmp_path, dg3, noise)
    return dryrun.select(inputs)


def test_g2_key_only_in_the_run_outputs_keeps_seed_25(tmp_path, monkeypatch) -> None:
    root = _scan_root(tmp_path)
    excluded = _r79_file(root / RUN_OUTPUTS / "r79_VBJ.json", DRY_KEY)
    selection = _selection(tmp_path, root, monkeypatch)
    assert (selection["r79_key"], selection["r79_seed"]) == (DRY_KEY, 25)
    scan = selection["scan"]
    assert scan["excluded_folder"] == dryrun.SCAN_EXCLUDED_FOLDER
    assert scan["files_excluded"] == 1
    assert scan["excluded"] == [{
        "path": f"{RUN_OUTPUTS}/r79_VBJ.json",
        "sha256": hashlib.sha256(excluded.read_bytes()).hexdigest(),
        "r79_keys": 1, "has_generated_key": True}]
    assert scan["seed_max"] == 24 and scan["files_scanned"] == 1  # the evidence outside
    assert all(not item["path"].startswith(dryrun.SCAN_EXCLUDED_FOLDER)
               for item in scan["files"])


@pytest.mark.parametrize("folder", ["02_control/j_p3_cause/other", "03_hydraulic/j9_runs"])
def test_g3_key_outside_the_run_outputs_stops(tmp_path, monkeypatch, folder) -> None:
    root = _scan_root(tmp_path)
    _r79_file(root / RUN_OUTPUTS / "r79_VBJ.json", DRY_KEY)
    _r79_file(root / folder / "r79.json", DRY_KEY)
    scan = dryrun.scan_r79_keys(root)
    assert dryrun.generated_key(BASE_KEY, scan.keys)[1] == 26
    with pytest.raises(dryrun.Stop, match="G-3"):
        _selection(tmp_path, root, monkeypatch)


@pytest.mark.parametrize(("relative", "excluded"), [
    ("02_control/j_p3_cause/j9_runs/a/b.json", True),
    ("02_control/j_p3_cause/j9_runs/a.jsonl", True),
    ("02_CONTROL/J_P3_CAUSE/J9_RUNS/a.jsonl", False),       # case as it is
    ("02_control\\j_p3_cause\\j9_runs\\a\\b.json", False),  # '/' separated only
    ("02_control/j_p3_cause/j9_runs_old/a.json", False),    # only that folder
    ("02_control/j_p3_cause/a/j9_runs/b.json", False),
    ("03_hydraulic/j9_runs/a.json", False),
])
def test_g1_exclusion_is_that_one_prefix(relative, excluded) -> None:
    assert dryrun.is_scan_excluded(relative) is excluded
