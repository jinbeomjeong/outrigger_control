"""D-1 harness paths (``d1_dynamics_check.md`` 5): P-2 slope on the rigid-base PS-a plant, P-3
the G6 wrapper's settle lookup (base soil, auger level, slope), P-4 the PS-c event of the 426.3
mechanism. Needs numba; the slow tests run full harness runs in dynamics-dev subprocesses."""

from __future__ import annotations

import contextlib
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("numba")

ROOT = Path(__file__).resolve().parents[2]
S9_DIR = ROOT / "04_scripts" / "03_control" / "s9"
S8_DIR = ROOT / "04_scripts" / "03_control" / "s8"
for _path in (S9_DIR, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import s9_soil_closed_loop as sl  # noqa: E402
import s9_soil_event_screen as screen  # noqa: E402

HARNESS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
RUNNER = Path(__file__).resolve().with_name("d1_harness_runner.py")
TIMEOUT_S = 900
LOWER_MM = 20.0
GAP_TOL_M = 1e-9


@contextlib.contextmanager
def _argv_as_root():
    saved = sys.argv
    sys.argv = [saved[0] if saved else "", str(ROOT)]
    try:
        yield
    finally:
        sys.argv = saved


@pytest.fixture(scope="module")
def r72():
    if str(S8_DIR) not in sys.path:
        sys.path.insert(0, str(S8_DIR))
    with _argv_as_root():
        import r72_g6_screen as module
    return module


@pytest.fixture(scope="module")
def harness():
    return sl._imports()


def _run(request: dict, tmp_path: Path) -> dict:
    if not HARNESS_PYTHON.exists():
        pytest.skip("dynamics-dev missing")
    out_path = tmp_path / f"report_{len(list(tmp_path.iterdir()))}.json"
    environment = {**os.environ, "MKL_THREADING_LAYER": "TBB", "PYTHONDONTWRITEBYTECODE": "1"}
    subprocess.run([str(HARNESS_PYTHON), "-I", "-B", str(RUNNER), json.dumps(request),
                    str(out_path)], check=True, env=environment, timeout=TIMEOUT_S)
    return json.loads(out_path.read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------------- P-2 / P-3
def test_g6_job_passes_slope_and_hook_into_the_case(r72, monkeypatch) -> None:
    """``job(key, slope=, settle_hook=)`` gives s9 ``run_case`` both keys; a former call not."""
    seen = []

    def capture(case):
        seen.append(dict(case))
        raise RuntimeError("stop after the case dict")

    monkeypatch.setattr(r72, "_install", lambda: None)  # keep the s9 module of this process
    monkeypatch.setattr(r72.sl, "run_case", capture)
    r72.job("d1|G1+J1@FL|middle|Fs4", slope=(0.0, 2.4), settle_hook="harness")
    r72.job("g6|G1+J1@FL|top|Fs4")
    assert seen[0]["slope"] == (0.0, 2.4) and seen[0]["settle_hook"] == "harness"
    assert "slope" not in seen[1] and "settle_hook" not in seen[1]


def test_g6_plant_takes_the_settle_row_of_the_base_level_and_slope(r72, harness) -> None:
    """P-3: ``G1+J1@FL`` on (0, 2.4) at the middle auger level reads ``G1|middle|0|2.4``."""
    cl = harness[0]
    plant = r72.make_plant_per_leg(cl, "middle", "G1+J1@FL", "B", 4.0, slope=(0.0, 2.4),
                                   settle_hook="harness")
    row = sl.load_settle_row("G1", "middle", (0.0, 2.4))
    assert plant.settle_info["row_key"] == "G1|middle|0|2.4"
    assert isinstance(plant.soil, r72.SoilPadsPerLeg)
    assert plant.soil.settle_row is row
    np.testing.assert_array_equal(plant.soil.h, np.asarray(row["pad_h_m"], float))
    assert plant.soil.n_arr[0] != plant.soil.n_arr[1]  # J1 under FL, G1 elsewhere


def test_rigid_patch_plant_on_a_slope_keeps_the_patch_on_the_floor_plane(r72, harness) -> None:
    """P-2: the patch element's surface is the tilted floor (h = 0, goff 0, floor normal)."""
    cl = harness[0]
    plant = r72.make_plant_per_leg(cl, "top", "rigid+J1@RL", "B", 4.0, slope=(0.0, -2.4))
    assert isinstance(plant.soil, r72.MixedRigidPads)
    assert not plant.soil.h.any() and not plant.goff.any()
    assert plant.nrm[0] < 0.0  # nose-up floor: the normal leans backwards


@pytest.mark.slow
def test_rigid_slope_mixed_kernel_equals_the_rigid_path(tmp_path: Path) -> None:
    """P-2 end condition: the PS-a plant with its patch leg back to rigid (``R72_PATH``
    per_leg_force, all four legs rigid in ``MixedRigidPads``) on a sloped floor gives the
    command hash of the plain rigid run (``s9`` path)."""
    request = {"kind": "r72", "key": "ref|rigid|top|Fs4", "slope": [0.0, 2.4]}
    plain = _run({**request, "path": "s9"}, tmp_path)
    mixed = _run({**request, "path": "per_leg_force"}, tmp_path)
    assert plain["hash"] == mixed["hash"]
    assert mixed["settle"]["gap_mm"] is not None  # the mixed kernel ran


R1_V0_STORED_HASH = "a91e95796d41e1a06dd5513b1a191bbd0b5bb12e5cfa50e9df8feafebb27820f"
"""``main.jsonl`` line of {"case": "R1", "eps": 0.0, "setting": "V0"} (rigid top flat)."""


@pytest.mark.slow
def test_d1_steady_row_is_the_v5_steady_run(tmp_path: Path) -> None:
    """``run_v5`` job of D-1 row H-R-0 T flat K1 (V0, eps 0) = the stored v5 R1 V0 run, and
    its ``d1`` record carries the sealed selection fields."""
    sys.path.insert(0, str(ROOT / "04_scripts" / "04_hydraulic" / "coupled"))
    import d1_rows
    import d1_select

    row = next(r for r in d1_rows.all_rows() if r.key == "D1|H-R-0|rigid|T|flat|K1")
    report = _run({"kind": "v5", "job": {"d1": row.to_job(), "eps": 0.0, "setting": "V0"}},
                  tmp_path)
    assert report["hash"] == R1_V0_STORED_HASH
    assert set(d1_select.REQUIRED_FIELDS) <= set(report["d1"])
    assert report["d1"]["verdict"] == "pass" and report["d1"]["j_p3"] == "not_applicable"


# ------------------------------------------------------------------------------------------ P-4
def test_progressive_sink_event_form() -> None:
    event = screen.progressive_sink_event(20.0, 6.0)
    assert event == {"depth": 0.020, "ramp": 6.0}
    assert screen.progressive_sink_event(0.0, 6.0)["depth"] == 0.0
    for bad in ((-1.0, 6.0), (20.0, 0.0), (float("nan"), 6.0)):
        with pytest.raises(ValueError):
            screen.progressive_sink_event(*bad)


def test_unloaded_pad_follows_the_lowered_reference_surface(harness) -> None:
    """P-4: with the pads in the air (crawler settled), lowering the soil surface under FL by
    d moves its pad gap by d and leaves the soil state and the other pads alone."""
    cl, c2, meas = harness
    plant, ctrl, _ = screen.make_event_base(cl, c2, "J1", "top", "B", 4.0)
    before = sl.pad_floor_gaps_m(cl, plant)
    state = [plant.soil.z.copy(), plant.soil.sp.copy(), plant.soil.sy.copy()]
    hook = screen.soil_event_floor(0, LOWER_MM * 1e-3, 0.5, t_ev=plant.t)
    rec, zero = {}, np.zeros(4)
    for _ in range(10):  # 1 s, past the 0.5 s ramp
        screen.control_period_rec(cl, meas, plant, zero, zero, ctrl.geometry.head_area_m2,
                                  ctrl.period_s, rec, floor_fn=hook)
    change = sl.pad_floor_gaps_m(cl, plant) - before
    assert abs(change[0] - LOWER_MM * 1e-3) <= 1e-4  # body still on the crawler (sub-0.1 mm)
    assert np.abs(change[1:]).max() <= 1e-4
    assert np.abs(change[0] - change[1:].mean() - LOWER_MM * 1e-3) <= 1e-6
    # unloaded elements: the 1 ms bisection leaves z at its bracket residual (~1e-28 m) on
    # every pad, event or not; the plastic memory sp, sigma_y stays untouched
    np.testing.assert_allclose(plant.soil.z, state[0], rtol=0.0, atol=1e-12)
    for old, new in zip(state[1:], (plant.soil.sp, plant.soil.sy), strict=True):
        np.testing.assert_array_equal(old, new)
    assert not plant.soil.force.any()


@pytest.mark.slow
def test_zero_depth_event_is_bit_identical_to_no_event(harness) -> None:
    """P-4 end condition: d = 0 with the hook installed gives the commands of the branch
    without an event (same branch length: T 6 s keeps max(12, T + 3) = 12 s)."""
    cl, c2, meas = harness
    plant, ctrl, _ = screen.make_event_base(cl, c2, "J1", "top", "B", 4.0)
    base = screen.run_base_soil(cl, meas, plant, ctrl, stop_t=40.0)
    t_ev = plant.t + screen.PRE_S
    results = []
    for spec in (None, screen.progressive_sink_event(0.0, 6.0)):
        branch = screen.branch_soil(cl, meas, copy.deepcopy(plant), copy.deepcopy(ctrl),
                                    base["cmd"].copy(), base["valve"].copy(),
                                    None if spec is None else "c-mid", 0, t_ev,
                                    event_spec=spec)
        results.append(branch)
    assert results[0].commands_sha256 == results[1].commands_sha256
    np.testing.assert_array_equal(results[0].rows, results[1].rows)
