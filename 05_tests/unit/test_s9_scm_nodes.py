"""Case GIFs (cad 2026-10-30): ``run_S9.py level --record-scm-nodes PERIOD_S`` (read-only SCM node record,
:class:`run_S9.ScmNodeRecorder`) and the p3b argv key. Small SCM systems only (no machine model, no closed loop)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT / "04_scripts" / "02_chrono", ROOT / "04_scripts" / "03_control" / "s9"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import run_S9  # noqa: E402

Z_PLANE = -1.0509
GRID = 0.01


def _ch():
    return pytest.importorskip("pychrono")


def _system(with_box: bool = True):
    ch = _ch()
    import pychrono.vehicle as veh

    s = ch.ChSystemSMC()
    s.SetCollisionSystemType(ch.ChCollisionSystem.Type_BULLET)
    s.SetGravitationalAcceleration(ch.ChVector3d(0.0, 0.0, -9.80665))
    s.SetNumThreads(1, 1, 1)
    t = veh.SCMTerrain(s, False)
    t.SetReferenceFrame(ch.ChCoordsysd(ch.ChVector3d(0.3, -0.2, Z_PLANE), ch.QUNIT))
    t.SetSoilParameters(2.0e6, 0.0, 1.1, 0.0, 30.0, 0.01, 2.0e8, 3.0e4)
    box = ch.ChBodyEasyBox(0.33, 0.33, 0.1, 2755.0, False, True, ch.ChContactMaterialSMC())
    box.SetPos(ch.ChVector3d(0.5, -0.1, Z_PLANE + 0.002 + 0.05))
    s.Add(box)
    t.AddActiveDomain(box, ch.ChVector3d(0, 0, -0.05), ch.ChVector3d(0.5, 0.5, 0.2))
    t.Initialize(3.0, 3.0, GRID)
    return s, t, box


def _model(t):
    return SimpleNamespace(terrains=(t,), pad_grid_m=GRID, dual_terrain=False, soil_patch_leg=None)


def _state(s, box):
    p, q, v = box.GetPos(), box.GetRot(), box.GetPosDt()
    return (float(s.GetChTime()), p.x, p.y, p.z, q.e0, q.e1, q.e2, q.e3, v.x, v.y, v.z)


# ------------------------------------------------------------------------------------------- CLI / argv
def test_option_absent_leaves_no_attribute_and_args_unchanged() -> None:
    base = ["level", "--soil", "J2", "--approved", "--case", "x", "--out-root", "x"]
    a = run_S9.build_parser().parse_args(base)
    assert not hasattr(a, "record_scm_nodes")
    b = run_S9.build_parser().parse_args(base + ["--record-scm-nodes", "0.5"])
    assert b.record_scm_nodes == 0.5
    assert {k: v for k, v in vars(b).items() if k != "record_scm_nodes"} == vars(a)


def test_p3b_argv_unchanged_without_key() -> None:
    c = {"soil": "J2", "pad_variant": "dwg_rear250", "level": "top", "fs_kN": 4.0, "grid_m": 0.01,
         "crawler_grid_m": 0.02}
    plain = run_S9.p3b_level_argv(dict(c))
    assert "--record-scm-nodes" not in plain
    with_key = run_S9.p3b_level_argv({**c, "record_scm_nodes": 0.5})
    assert with_key[:-1] == plain[:-1] + ["--record-scm-nodes", "0.5"] and with_key[-1] == plain[-1] == "--approved"


# ----------------------------------------------------------------------------------- real SCMTerrain
def test_recorder_is_read_only_bit_identical_dynamics() -> None:
    """The same small SCM run with and without snapshots every 50 steps: body state bit-identical."""
    s1, t1, b1 = _system()
    s2, t2, b2 = _system()
    rec = run_S9.ScmNodeRecorder(_model(t2), 0.025)
    rec.snapshot(float(s2.GetChTime()))
    for k in range(400):
        s1.DoStepDynamics(5.0e-4)
        s2.DoStepDynamics(5.0e-4)
        rec(float(s2.GetChTime()))
    assert _state(s1, b1) == _state(s2, b2)
    assert len(rec.snap_t) >= 8


def test_recorder_increment_reconstructs_the_last_levels(tmp_path: Path) -> None:
    ch = _ch()
    s, t, box = _system()
    rec = run_S9.ScmNodeRecorder(_model(t), 0.05)
    rec.snapshot(0.0)
    for _ in range(400):
        s.DoStepDynamics(5.0e-4)
        rec(float(s.GetChTime()))
    rec.snapshot(float(s.GetChTime()))
    info = rec.save(tmp_path / run_S9.SCM_NODES_NAME)
    assert info["snapshots"] == len(rec.snap_t) and info["terrains"] == ["pad"]
    z = np.load(tmp_path / run_S9.SCM_NODES_NAME)
    # replay: last written level per node == current levels within the write tolerance
    levels: dict[tuple[int, int], float] = {}
    for i, j, lv in zip(z["i"], z["j"], z["level_m"], strict=True):
        levels[(int(i), int(j))] = float(lv)
    now = {(p[0].x, p[0].y): p[1] for p in t.GetModifiedNodes(True)}
    assert set(now) == set(levels)
    err = max(abs(now[k] - levels[k]) for k in now)
    assert err <= run_S9.SCM_NODES_TOL_M + 1e-6  # float32 storage
    deepest = min(now.values())
    assert deepest < -1e-4  # the box left a rut
    # world position of the deepest node = frame.pos + (i grid, j grid, level) (identity rotation here)
    (i, j), lv = min(now.items(), key=lambda kv: kv[1])
    fr = z["frames"][-1, 0]
    world = fr[:3] + np.array([i * GRID, j * GRID, lv])
    info_node = t.GetNodeInfo(ch.ChVector3d(*map(float, world)))
    assert abs(float(info_node.sinkage) - (-lv)) < 1e-9
    # increment: fewer rows than every node at every snapshot
    assert len(z["snap"]) < len(now) * len(z["snap_t_s"])
