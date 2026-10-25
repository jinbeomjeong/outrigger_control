"""S8 C-S8-4: episode branch (run_S8C.save_branch / restore_branch + runner resume_command):
the branch continues bit-identically, and a run split at a control instant equals the unsplit
run (criterion <= 1e-9 m, R16)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("pychrono")

pytestmark = pytest.mark.chrono

ROOT = Path(__file__).resolve().parents[2]


def test_branch_continuity(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OUTRIGGER_S8_CRAWLER", "rigid")
    sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))
    import run_S8C

    out = run_S8C.smoke_branch(0.3, 0.3, work_dir=tmp_path)
    assert out["max_pos_diff_m"] <= 1e-9
    assert out["max_pos_diff_split_vs_unsplit_m"] <= 1e-9
    assert out["passed"]
    assert os.environ["OUTRIGGER_S8_CRAWLER"] == "rigid"
