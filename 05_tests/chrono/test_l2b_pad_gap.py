"""``L2bModel(pad_gap_offsets_m=...)``: default model unchanged, offsets act on the pad contact
sphere radius only, bad inputs refused."""

from __future__ import annotations

import pytest

pytest.importorskip("pychrono")

from outrigger_sim.chrono.l2b_model import L2bModel  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

pytestmark = pytest.mark.chrono


@pytest.fixture(scope="module")
def params():
    return load_params(level="top", model="L2b_NSC")


def _yaml_radii(params) -> tuple[float, ...]:
    return tuple(leg.pad.swivel_center_above_pad_bottom_m for leg in params.legs)


def test_default_unchanged(params) -> None:
    model = L2bModel(params, extensions_m=(0.0,) * 4, start="hanging")
    assert model.pad_gap_offsets_m is None
    assert "pad_gap_offsets_m" not in model.meta()
    assert model.sphere_radii_m == _yaml_radii(params)


def test_offsets_change_the_radius_only(params) -> None:
    gaps = (0.002, -0.002, 0.002, -0.002)
    base = L2bModel(params, extensions_m=(0.0,) * 4, start="hanging")
    model = L2bModel(params, extensions_m=(0.0,) * 4, start="hanging", pad_gap_offsets_m=gaps)
    assert model.sphere_radii_m == tuple(r - g for r, g in zip(_yaml_radii(params), gaps, strict=True))
    assert model.meta()["pad_gap_offsets_m"] == list(gaps)
    for a, b in zip(base.sphere_centres_local_m, model.sphere_centres_local_m, strict=True):
        assert (a == b).all()


@pytest.mark.parametrize("gaps", [(0.002,) * 3, (0.2, 0.0, 0.0, 0.0)])
def test_bad_offsets_refused(params, gaps) -> None:
    with pytest.raises(ValueError):
        L2bModel(params, extensions_m=(0.0,) * 4, start="hanging", pad_gap_offsets_m=gaps)
