"""C-S8-76 rigid block under one pad (``chrono/pad_block``, ``L1Model(pad_blocks=...)``):
default model unchanged, block geometry on the restored settled crawler, contact on the block
top with the floor's material and the ground bushing on the block body, bad inputs refused."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("pychrono")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

from outrigger_sim.chrono.contact import shape_materials  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.record import load_snapshot  # noqa: E402

pytestmark = pytest.mark.chrono

SNAP = "S6_crawler_top_flat"
STATES = ROOT / "07_results" / "states_L1R"


@pytest.fixture(scope="module")
def st():
    import run_S6C  # sets OUTRIGGER_ROD_SIDE_MECHANICS (L1-R) like the runner

    return run_S6C.st


@pytest.fixture(scope="module")
def params():
    return load_params(level="top")


def _build(st, params, blocks=None):
    if not (STATES / f"{SNAP}.npz").exists():
        pytest.skip(f"{SNAP} snapshot missing")
    model, _ = st.build_crawler_model(params, "flat", attach=False,
                                      **({"pad_blocks": blocks} if blocks else {}))
    t0 = model.restore(load_snapshot(SNAP, params_sha256=params.sha256, directory=STATES))
    return model, t0


def test_default_model_unchanged(st, params) -> None:
    model, _ = _build(st, params)
    assert model.pad_blocks is None
    assert "pad_blocks" not in model.meta()
    assert np.array_equal(model.pad_block_offsets_m(), np.zeros(4))
    assert all(p is None for p in model.rod_chamber._patch_bodies)  # noqa: SLF001
    assert all(leg.floor is model.floor for leg in model.bushing._legs)  # noqa: SLF001


def test_block_geometry_and_contact(st, params) -> None:
    m0, _ = _build(st, params)
    g0 = st.pad_gaps_m(m0)
    h = float(g0[0]) - 0.002  # g_start 2 mm
    model, t0 = _build(st, params, {"FL": h})
    blk = model.pad_blocks.bodies["FL"]
    assert blk.IsFixed() and blk.GetMass() == m0.floor.GetMass()
    assert model.pad_blocks.surface_offset_measured_m("FL") == pytest.approx(h, abs=1e-12)
    assert [p.name for p in model.patches if p not in model.floor_body_patches] == ["pad_FL"]
    assert model.bushing._legs[0].floor is blk  # noqa: SLF001
    assert model.rod_chamber._patch_bodies[0] is blk  # noqa: SLF001
    gaps = st.pad_gaps_m(model)
    assert gaps[0] == pytest.approx(0.002, abs=1e-12)
    assert np.array_equal(gaps[1:], g0[1:])
    # same SMC material as the fixed-floor pad patch of that leg
    floor_mats = shape_materials(m0.floor)
    blk_mats = shape_materials(blk)
    assert len(blk_mats) == 1
    keys = ("kn_N_m", "gn_1_s", "kt_N_m", "gt_1_s", "friction")
    assert any(all(fm[k] == blk_mats[0][k] for k in keys) for fm in floor_mats)
    assert model.meta()["pad_blocks"]["legs"] == ["FL"]
    # extend FL at v_max for 0.2 s (4.2 mm > 2 mm gap): FL loads on the block, others free
    v = float(params.actuator.max_speed_m_s)
    for _ in range(round(0.2 / model.dt_s)):
        model.set_command(np.array([v, 0.0, 0.0, 0.0]))
        model.step()
    n = model.truth(model.probe()).F_contact_n_N
    assert n[0] > 1.0e3 and np.all(np.asarray(n[1:]) == 0.0)
    assert model.bushing.in_contact.tolist() == [True, False, False, False]
    assert model.bushing.anchors_world_m()[0, 2] == pytest.approx(model.floor_z_m + h, abs=1e-9)
    assert model.rod_chamber.last_deflection_m[0] > 0.0


@pytest.mark.parametrize("blocks", [{"XX": 0.1}, {"FL": 0.0}, {"FL": -0.1}])
def test_bad_blocks_refused(st, params, blocks) -> None:
    with pytest.raises(ValueError):
        st.build_crawler_model(params, "flat", attach=False, pad_blocks=blocks)


def test_block_and_settlement_same_leg_refused(st, params) -> None:
    with pytest.raises(ValueError):
        st.build_crawler_model(params, "flat", attach=False, settlement_legs=("RR",),
                               pad_blocks={"RR": 0.1})
