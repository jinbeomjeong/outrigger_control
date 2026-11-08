"""s9_batch records the OMP_WAIT_POLICY it put into each child env (v5 criteria rev. 12a) in batch.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

import s9_batch as sb  # noqa: E402


def test_launch_env_record(monkeypatch) -> None:
    monkeypatch.delenv("OMP_WAIT_POLICY", raising=False)
    assert sb.launch_env_record(sb._case_env("pcore")) == {"omp_wait_policy": "PASSIVE"}
    assert sb.launch_env_record(sb._case_env("pcore", {"OMP_WAIT_POLICY": "ACTIVE"})) == {"omp_wait_policy": "ACTIVE"}
    assert sb.launch_env_record({}) == {"omp_wait_policy": None}


def test_batch_json_has_child_omp(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("OMP_WAIT_POLICY", raising=False)
    rows = [{"case": "t_default", "argv": [sys.executable, "-c", "pass"], "est_s": 1.0},
            {"case": "t_s8c", "argv": [sys.executable, "-c", "pass"], "est_s": 1.0, "s6c": True,
             "start_env": {"OMP_WAIT_POLICY": "ACTIVE"}}]
    monkeypatch.setattr(sb, "batches", lambda **_: {"TEST-ENV": rows})
    monkeypatch.setattr(sb, "ROOT", tmp_path)
    folder = sb.run_batch("TEST-ENV", parallel=2)
    doc = json.loads((Path(folder) / "batch.json").read_text("utf-8"))
    got = {c["case"]: c.get("omp_wait_policy") for c in doc["cases"]}
    assert got == {"t_default": "PASSIVE", "t_s8c": "ACTIVE"}
    assert "OMP_WAIT_POLICY=PASSIVE" in (Path(folder) / "progress.log").read_text("utf-8")
