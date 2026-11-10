"""D8x J3 diagnosis driver ``acceptance/d8x_diag.py`` (diagnostic, not a judgement path).

The driver imports ``acc_d8`` (which patches its process), so everything runs in a subprocess.
The rerun test runs one stored R-a case twice in one process, first through ``acc_d8.run_one``
alone and then through the recorders, and needs dynamics-dev (numba); about 1.5 min.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ACCEPTANCE = ROOT / "04_scripts" / "03_control" / "touch_phase" / "acceptance"
D8X_DIR = ROOT / "04_scripts" / "03_control" / "d8x"
sys.path.insert(0, str(D8X_DIR))

import d8x_spec as spec  # noqa: E402

RERUN_ID = "main|C2_tv0.1|top|rigid|r+p+0.5"
"""A stored K1-off R-a J3 fail (14 lifted chunks, d8x_g1_fail_rows.csv)."""
STORED_RA_OFF = Path(os.environ.get(
    "D8X_STORED_RA_OFF",
    r"C:\workspace\outrigger_control\06_analysis\02_control\d8x\ra\ra_off.json"))
"""The stored R-a K1-off run (git-ignored, main checkout); the stored-hash test skips without it."""

POINTS_CODE = (
    "import json, sys; sys.path.insert(0, sys.argv[1]); import d8x_diag; "
    "print(json.dumps({'sym': d8x_diag.diamond_points(5.5, 3.5), "
    "'ext': d8x_diag.diamond_points(5.7, 3.7)}))")

RERUN_CODE = """
import json, sys, tempfile
sys.path.insert(0, sys.argv[1])
import d8x_diag
acc_d8 = d8x_diag.acc_d8
record = acc_d8._record_module()
points = record.ra_point_angles(record.load_points(None))
case = next(c for c in acc_d8.d8x_cases(points, acc_d8.D8X_STAGES) if c["id"] == sys.argv[2])
plain = acc_d8.run_one(dict(case))
with tempfile.TemporaryDirectory() as folder:
    diag = d8x_diag.diag_run({"case": dict(case), "series_dir": folder, "save": "all"})
    import numpy as np
    with np.load(f"{folder}/{diag['diag']['series_file']}") as series:
        keys = sorted(series.files)
        n_chunks = int(series["t_s"].shape[0])
for row in (plain, diag):
    row.pop("module_files", None)
    row.pop("wall_s", None)
print(json.dumps({"plain": plain, "diag": diag, "keys": keys, "n_chunks": n_chunks}))
"""


def _subprocess(code: str, *args: str, timeout_s: float) -> subprocess.CompletedProcess:
    env = dict(os.environ, ACC_WT=str(ROOT), PYTHONDONTWRITEBYTECODE="1", ACC_D8X_K1="off")
    return subprocess.run([sys.executable, "-I", "-B", "-c", code, *args], capture_output=True,
                          text=True, env=env, cwd=str(ROOT), timeout=timeout_s, check=False)


def test_diamond_points_follow_the_d8x_point_file() -> None:
    completed = _subprocess(POINTS_CODE, str(ACCEPTANCE), timeout_s=600)
    assert completed.returncode == 0, completed.stderr[-3000:]
    out = json.loads(completed.stdout.strip().splitlines()[-1])
    d8x = spec.points_by_name(spec.build_points())
    # Same tags as the R-a table; the nose-down / nose-up halves equal there (3.7 both sides here).
    assert sorted(out["ext"]) == sorted(entry["tag"] for entry in spec.build_points()["ra_points"])
    for tag, (roll, pitch) in out["ext"].items():
        # The file has nose-up 3.6 and keeps the nose-down d45 at the literal 2.2627.
        if pitch < 0 or tag in ("d45++", "d45-+"):
            continue
        assert (roll, pitch) == pytest.approx(d8x[tag], abs=1e-9), tag
    for tag, (roll, pitch) in out["sym"].items():
        assert abs(roll) / 5.5 + abs(pitch) / 3.5 == pytest.approx(1.0, abs=5e-5), tag


@pytest.fixture(scope="module")
def rerun() -> dict:
    completed = _subprocess(RERUN_CODE, str(ACCEPTANCE), RERUN_ID, timeout_s=900)
    assert completed.returncode == 0, completed.stderr[-3000:]
    return json.loads(completed.stdout.strip().splitlines()[-1])


def test_recorders_do_not_change_the_run(rerun) -> None:
    plain, diag = dict(rerun["plain"]), dict(rerun["diag"])
    summary = diag.pop("diag")
    # The module list of the first run in a process misses outrigger_sim.hydraulics.v5_options
    # (acc_d8._d8x_fields lists the files before preset_controller_tag imports it).
    plain.pop("module_files_sha256")
    diag.pop("module_files_sha256")
    assert diag == plain
    assert summary["J3_recount"] == plain["d8x"]["J3_pad_lift_samples"] > 0
    assert sum(leg["chunks"] > 0 for leg in summary["legs"].values()) >= 1
    assert {"t_s", "pad_normal_min_N", "stroke_m", "command_m_s", "crawler_normal_N",
            "crawler_clearance_m", "att_rad", "ctrl_phase", "event_name"} <= set(rerun["keys"])
    assert rerun["n_chunks"] > 10_000


def test_rerun_gives_the_stored_command_hash(rerun) -> None:
    if not STORED_RA_OFF.is_file():
        pytest.skip(f"no stored R-a file {STORED_RA_OFF}")
    stored = next(row for row in json.loads(STORED_RA_OFF.read_text(encoding="utf-8"))["runs"]
                  if row["id"] == RERUN_ID)
    diag = rerun["diag"]
    assert diag["commands_sha256"] == stored["commands_sha256"]
    for key in ("J3_pad_lift_samples", "J3_pad_normal_min_N", "t_touch_s", "t_lift_s", "events"):
        assert diag["d8x"][key] == stored["d8x"][key], key
