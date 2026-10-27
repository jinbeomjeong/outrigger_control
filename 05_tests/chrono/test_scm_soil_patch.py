"""G6 soil patch (``S9Model(soil_patch=...)``, cad G6 study / user decision 2026-10-27): one pad on a
third SCMTerrain with its own soil set and anchor values; the default dual model unchanged
(bit-identical forces and meta without the patch), bad inputs refused."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.chrono.scm_model import S9Model, load_soil_set  # noqa: E402
from outrigger_sim.pad_variants import apply_pad_variant, pad_variant_meta  # noqa: E402
from outrigger_sim.params import LEG_ORDER, load_params  # noqa: E402

pytestmark = pytest.mark.chrono


@pytest.fixture(scope="module")
def params_b():
    return apply_pad_variant(load_params(level="top", model="L2b_NSC"), "dwg_rear250")


def _model(params_b, **kw):
    pv = pad_variant_meta("dwg_rear250", params=params_b)
    return S9Model(params_b, load_soil_set("G1"), pv, grid_m=0.04, crawler_grid_m=0.04, **kw)


def _run(model, n=30):
    out = []
    for _ in range(n):
        model.step()
        out.append(np.concatenate([model.forces.pad_force_N.ravel(), model.forces.sup_force_N]))
    return np.array(out)


def test_patch_layout_and_anchor_values(params_b) -> None:
    j1 = load_soil_set("J1")
    model = _model(params_b, soil_patch=("RR", j1), soil_patch_grid_m=0.04)
    assert len(model.terrains) == 3 and model.soil_patch_leg == "RR"
    k = LEG_ORDER.index("RR")
    assert model.pad_terrain_by_leg[k] is model.terrains[2]
    assert all(model.pad_terrain_by_leg[i] is model.pad_terrain for i in range(4) if i != k)
    names_pad = [d["name"] for d in model.terrain_meta["active_domains"]]
    names_patch = [d["name"] for d in model.terrain_meta["soil_patch"]["terrain"]["active_domains"]]
    assert names_pad == ["pad_FL", "pad_FR", "pad_RL"] and names_patch == ["pad_RR"]
    assert model.terrain_meta["layout"] == "triple"
    assert model.terrain_meta["soil_patch"]["terrain"]["SetSoilParameters"]["n"] == pytest.approx(0.13)
    specs = model.pad_bushing._pads  # noqa: SLF001
    assert specs[k].friction == pytest.approx(np.tan(np.radians(34.0)))
    assert all(specs[i].friction is None for i in range(4) if i != k)
    assert specs[k].adhesion_N == pytest.approx(model.patch_pad_values.adhesion_N[k]) and specs[k].adhesion_N > 0
    assert specs[0].adhesion_N == model.pad_values.adhesion_N[0] == 0.0  # G1: c = 0
    meta = model.meta()
    assert meta["terrain_layout"]["layout"] == "triple" and meta["soil_patch"]["leg"] == "RR"
    f = _run(model)
    assert np.all(np.isfinite(f))


def test_no_patch_is_unchanged(params_b) -> None:
    a = _model(params_b)
    assert len(a.terrains) == 2 and a.soil_patch_leg is None
    assert "soil_patch" not in a.meta() and "soil_patch" not in a.terrain_meta
    assert "layout" not in a.meta()["terrain_layout"]
    assert all(s.friction is None for s in a.pad_bushing._pads)  # noqa: SLF001
    b = _model(params_b)
    assert np.array_equal(_run(a), _run(b))


def test_patch_needs_dual_terrain_and_valid_leg(params_b) -> None:
    pv = pad_variant_meta("dwg_rear250", params=params_b)
    j1 = load_soil_set("J1")
    with pytest.raises(ValueError, match="dual"):
        S9Model(params_b, load_soil_set("G1"), pv, grid_m=0.04, soil_patch=("RR", j1))
    with pytest.raises(ValueError, match="soil_patch"):
        _model(params_b, soil_patch=("XX", j1))
