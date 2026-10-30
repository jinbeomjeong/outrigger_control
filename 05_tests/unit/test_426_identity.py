"""Spec 426.7 T-2 .. T-4 (and the 426.5 / 426.6 reference identities): command hashes of the
harness paths after the study A..D extensions, by ``04_scripts/03_control/s9/x426_identity.py``
in dynamics-dev (the rev83 hashes were run there). Slow: 19 closed-loop runs, about 6 min on two
workers."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HARNESS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
IDENTITY_SCRIPT = ROOT / "04_scripts" / "03_control" / "s9" / "x426_identity.py"
PRE_SWITCH_RUNNER = Path(__file__).with_name("pre_switch_preset_runner.py")


@pytest.mark.slow
def test_t2_t3_t4_and_reference_hashes_unchanged(tmp_path) -> None:
    if not HARNESS_PYTHON.exists():
        pytest.skip("dynamics-dev missing")
    out_path = tmp_path / "x426_identity.json"
    environment = {**os.environ, "MKL_THREADING_LAYER": "TBB", "OMP_NUM_THREADS": "1",
                   "PYTHONDONTWRITEBYTECODE": "1"}
    # The stored hashes predate the spec 429.11 preset switch (SGS, R4 off).
    subprocess.run([str(HARNESS_PYTHON), "-I", "-B", str(PRE_SWITCH_RUNNER), str(IDENTITY_SCRIPT),
                    str(out_path), "2"],
                   cwd=ROOT, env=environment, check=True, capture_output=True, timeout=3600)
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    failed = [(r["part"], r["id"], r.get("error")) for r in payload["rows"] if not r.get("equal")]
    assert not failed
    assert all(r["stored_matches_spec_prefix"] for r in payload["rows"] if "spec_prefix" in r)
    assert {r["part"] for r in payload["rows"]} == {"t2", "t3", "t4", "c_ref", "d_ref", "t5"}
