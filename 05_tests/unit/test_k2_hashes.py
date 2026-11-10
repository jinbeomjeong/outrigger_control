"""K-2 identity runs (``k2_touch_creep_rules.md`` 9.2, I-4 / I-5 / I-8), slow: the reduced harness in dynamics-dev.

* T-K2-1 (I-5): ``acc_d8.py --k1 off --k2 on`` on the 8 screen VC ids gives the ``commands_sha256`` of
  ``06_analysis/02_control/k2/screen/j3ctrl_run2a_variants.json`` (variant VC).
* T-K2-2 (I-4, reduced): ``--k2 off`` on the 5 diagnosis rerun ids gives the stored hashes
  (``06_analysis/02_control/d8x/diag/rerun/rerun_summary.json``).
* I-8: KPlant with every dissipation option off is the plant before them: the G0 60 evaluations
  (``run_d8x_g0_rev3.py``) equal ``d8x_g0_rev3.json`` item for item, and the first 24 R-c jobs of the stored
  ``rc/hrx_off.jsonl`` (key order) give their ``commands_sha256`` (the stored file is a raw result of the main
  checkout; the test skips without it).

Run on the E-cores with one BLAS thread (P-cores may be busy): the workers inherit the affinity of pytest.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HARNESS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
ACC_D8 = ROOT / "04_scripts" / "03_control" / "touch_phase" / "acceptance" / "acc_d8.py"
POINTS = ROOT / "06_analysis" / "02_control" / "d8x" / "d8x_points.json"
SCREEN = ROOT / "06_analysis" / "02_control" / "k2" / "screen" / "j3ctrl_run2a_variants.json"
RERUN = ROOT / "06_analysis" / "02_control" / "d8x" / "diag" / "rerun" / "rerun_summary.json"
G0_SCRIPT = ROOT / "04_scripts" / "01_dynamics" / "run_d8x_g0_rev3.py"
G0_STORED = ROOT / "06_analysis" / "00_dynamics" / "d8x_g0_rev3.json"
RC_STORED = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\d8x\rc\hrx_off.jsonl")
RC_RUNNER = Path(__file__).with_name("k2_rc_sample_runner.py")
G0_COMPARE_KEYS = {"G0-1": "s_max_m", "G0-2": "F_static_min_N", "G0-3": "swivel_deg", "G0-4": "floor_hat_deg"}
WORKERS = 8
TIMEOUT_S = 3600

pytestmark = [pytest.mark.slow,
              pytest.mark.skipif(not HARNESS_PYTHON.is_file(), reason="dynamics-dev interpreter missing")]


def _env() -> dict:
    env = dict(os.environ)
    for name in ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "NUMBA_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        env[name] = "1"
    env["MKL_THREADING_LAYER"] = "TBB"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for name in ("ACC_K2", "ACC_D8X_K2", "ACC_D8X_AUG", "ACC_D8X_SERIES_DIR"):
        env.pop(name, None)
    env["ACC_WT"] = str(ROOT)
    return env


def _acc_d8(tmp_path: Path, ids: list[str], k2: str) -> dict:
    keys = tmp_path / f"keys_{k2}.txt"
    keys.write_text("\n".join(ids) + "\n", encoding="utf-8")
    out = tmp_path / f"ra_k2{k2}.json"
    done = subprocess.run([str(HARNESS_PYTHON), "-I", "-B", str(ACC_D8), "--points", str(POINTS), "--k1", "off",
                           "--k2", k2, "--keys-file", str(keys), "--workers", str(WORKERS), str(out)],
                          cwd=ROOT, env=_env(), capture_output=True, text=True, timeout=TIMEOUT_S, check=False)
    assert done.returncode == 0, done.stderr[-3000:]
    return {run["id"]: run for run in json.loads(out.read_text(encoding="utf-8"))["runs"]}


def test_t_k2_1_screen_vc_hashes(tmp_path) -> None:
    want = {r["id"]: r["commands_sha256"] for r in json.loads(SCREEN.read_text(encoding="utf-8"))
            if r["variant"] == "VC"}
    assert len(want) == 8
    runs = _acc_d8(tmp_path, sorted(want), "on")
    assert {key: runs[key]["commands_sha256"] for key in want} == want
    for run in runs.values():  # T-K2-6 and the row record
        assert run["touch_creep_latch"] is True and run["controller_tag"] == "final_C4G2_LAS_TCL"
        assert (tmp_path / "ra_k2on_series" / run["series_file"]).is_file()
        names = [name for _, name in run["d8x"]["events"]]
        assert sorted(n for n in names if n.startswith("INFO_TOUCH_CREEP_LATCH")) == [
            f"INFO_TOUCH_CREEP_LATCH:{leg}" for leg in ("FL", "FR", "RL", "RR")]
        assert not [n for n in names if n.startswith("INFO_TOUCH_DIP_HELD")]
        assert isinstance(run["k2"]["dhat_N"], float)  # rules rev1 4 record (no command effect)
        assert isinstance(run["k2"]["dhat_window_open_legs"], list)
        assert len(run["k2"]["dhat_window_stroke_mm"]) == 4


def test_t_k2_2_off_arm_keeps_the_stored_hashes(tmp_path) -> None:
    want = {r["id"]: r["commands_sha256"] for r in json.loads(RERUN.read_text(encoding="utf-8"))["runs"]}
    runs = _acc_d8(tmp_path, sorted(want), "off")
    assert {key: runs[key]["commands_sha256"] for key in want} == want
    for run in runs.values():
        assert run["touch_creep_latch"] is False and run["controller_tag"] == "final_C4G2_LAS"
        assert not [name for _, name in run["d8x"]["events"] if name.startswith("INFO_TOUCH_CREEP_")]


def test_i8_g0_values_unchanged(tmp_path) -> None:
    out = tmp_path / "g0.json"
    done = subprocess.run([str(HARNESS_PYTHON), "-I", "-B", str(G0_SCRIPT), "--workers", str(WORKERS),
                           "--out", str(out)], cwd=ROOT, env=_env(), capture_output=True, text=True,
                          timeout=TIMEOUT_S, check=False)
    assert done.returncode == 0, done.stderr[-3000:]
    stored = {(r["level"], r["tag"]): r for r in json.loads(G0_STORED.read_text(encoding="utf-8"))["rows"]}
    rows = json.loads(out.read_text(encoding="utf-8"))["rows"]
    assert len(rows) == len(stored) == 60
    differing = [(row["level"], row["tag"], item) for row in rows for item, name in G0_COMPARE_KEYS.items()
                 if row["G0"][item].get(name) != stored[(row["level"], row["tag"])]["G0"][item].get(name)]
    assert differing == []


@pytest.mark.skipif(not RC_STORED.is_file(), reason="stored R-c hrx_off.jsonl (main checkout raw result) missing")
def test_i8_rc_sample_hashes(tmp_path) -> None:
    out = tmp_path / "rc.json"
    done = subprocess.run([str(HARNESS_PYTHON), "-I", "-B", str(RC_RUNNER), str(ROOT), str(RC_STORED), str(out),
                           str(WORKERS)], cwd=ROOT, env=_env(), capture_output=True, text=True,
                          timeout=TIMEOUT_S, check=False)
    assert done.returncode == 0, done.stderr[-3000:]
    summary = json.loads(out.read_text(encoding="utf-8"))["summary"]
    assert summary == {**summary, "n": 24, "equal": 24, "errors": 0}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
