"""D8x runners: H-R-X rows (``d1_rows.d8x_jobs``) and the R-a cases (``acc_d8.d8x_cases``).

Rules ``d8x_rules.md`` 3 (R-a 1,102, R-c 288) with ``d8x_rules_rev1.md`` 1.2 (angles) and 9.2
items 2 / 3. The acceptance harness patches its process, so the R-a case list is built in a
subprocess.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
D8X_DIR = ROOT / "04_scripts" / "03_control" / "d8x"
ACC_D8 = ROOT / "04_scripts" / "03_control" / "touch_phase" / "acceptance" / "acc_d8.py"
for path in (COUPLED, D8X_DIR):
    sys.path.insert(0, str(path))

import d1_rows  # noqa: E402
import d8x_spec as spec  # noqa: E402

POINTS = spec.build_points()


@pytest.mark.parametrize(("k1", "count"), [("off", 192), ("on", 96)])
def test_hrx_jobs_are_the_expected_keys(k1, count) -> None:
    jobs = d1_rows.d8x_jobs(k1)
    keys = [f"{job['d1']['key']}|{job['setting']}|e{job['eps']:g}" for job in jobs]
    assert len(jobs) == count
    assert keys == spec.expected_rc_keys(POINTS, k1)
    assert {job["k1"] for job in jobs} == {k1}


def test_hrx_rows_take_the_rev1_angles() -> None:
    rows = d1_rows.d8x_rows()
    assert len(rows) == 48
    angles = spec.points_by_name(POINTS)
    for row in rows:
        assert (row.roll_deg, row.pitch_deg) == angles[row.slope_name]
        assert row.group == d1_rows.D8X_GROUP and row.base == d1_rows.RIGID
        assert row.ready_limit_s == 120.0
    names = {row.slope_name for row in rows}
    assert "fup3.6" in names and "fup3.7" not in names


def test_hrx_rows_stay_out_of_the_d1_batch() -> None:
    assert all(row.group != d1_rows.D8X_GROUP for row in d1_rows.all_rows())
    assert len(d1_rows.all_rows()) == 217
    with pytest.raises(ValueError, match="k1"):
        d1_rows.d8x_jobs("maybe")


def test_acc_d8_cases_are_the_expected_ids() -> None:
    code = ("import json, sys; points, folder = sys.argv[1], sys.argv[2]; "
            "sys.argv = ['acc_d8.py', '--points', points]; "
            "sys.path.insert(0, folder); import acc_d8; d8x_record = acc_d8._record_module(); "
            "doc = d8x_record.load_points(points); "
            "pts = d8x_record.ra_point_angles(doc); "
            "out = {s: [c['id'] for c in acc_d8.d8x_cases(pts, tuple(s.split(',')))] "
            "for s in ('main,robust,kt', 'main')}; "
            "out['first'] = acc_d8.d8x_cases(pts, ('kt',))[0]['d8x']; print(json.dumps(out))")
    env = dict(os.environ, ACC_WT=str(ROOT), PYTHONDONTWRITEBYTECODE="1")
    completed = subprocess.run([sys.executable, "-I", "-c", code, str(spec.POINTS_PATH),
                                str(ACC_D8.parent)], capture_output=True, text=True, env=env,
                               cwd=str(ROOT), timeout=600, check=False)
    assert completed.returncode == 0, completed.stderr[-3000:]
    out = json.loads(completed.stdout.strip().splitlines()[-1])
    assert out["main,robust,kt"] == spec.expected_ra_ids(POINTS, ("main", "robust", "kt"))
    assert out["main"] == spec.expected_ra_ids(POINTS, ("main",))
    assert out["first"]["stage"] == "kt" and out["first"]["level"] == "top"
