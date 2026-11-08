"""D-1 verification matrix, harness support (``d1_dynamics_check.md`` 5, P-1 .. P-6).

P-1: crawler stiffness factor of the reduced harness ``Plant`` (U6: normal and tangential x s,
dashpots x sqrt(s), applied before the analytic settle pose). Needs numba (the harness module).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("numba")

ROOT = Path(__file__).resolve().parents[2]
DYNAMICS_DIR = ROOT / "04_scripts" / "01_dynamics"
if str(DYNAMICS_DIR) not in sys.path:
    sys.path.insert(0, str(DYNAMICS_DIR))

import run_control_comparison as rcc  # noqa: E402

X3_COMPRESSION_MM = 1.27
"""Mean compression of the loaded crawler spheres at x3 (dynamics-expert statics, d1 3.1; cad
C-1: the body origin sinks 1.19 mm, the sphere mean is 1.27 mm)."""
X3_COMPRESSION_REL_TOL = 0.05
X3_FLAT_PITCH_DEG = 0.086
X3_FLAT_PITCH_TOL_DEG = 0.01
X3_ACTIVE_SPHERES = 12


def _crawler_compression(plant) -> tuple[float, int]:
    """Mean compression of the spheres below the floor plane [mm] and their number."""
    rotation = rcc._R(plant.q)
    heights = np.array([float(plant.nrm @ (plant.r + rotation @ c)) for c in plant.cr_rel])
    loaded = heights < 0.0
    return float(-heights[loaded].mean() * 1e3), int(loaded.sum())


def _plant_class():
    """The module's own ``Plant``: ``run_mast_flex_c2_check`` (imported by other tests of the
    session) rebinds ``rcc.Plant`` to its ``FlexPlant``, whose signature has no keyword."""
    return next(cls for cls in rcc.Plant.__mro__
                if cls.__name__ == "Plant" and cls.__module__ == rcc.__name__)


# ------------------------------------------------------------------------------------------ P-1
def test_x1_is_the_module_default_and_leaves_the_arrays_alone() -> None:
    assert rcc.CRAWLER_K_SCALE == 1.0
    default = _plant_class()("top", 0.0, 0.0)
    explicit = _plant_class()("top", 0.0, 0.0, crawler_k_scale=1.0)
    assert default.crawler_k_scale == 1.0
    for name in ("kcr", "ccr", "ktcr", "ctcr", "q", "r"):
        assert getattr(default, name).tobytes() == getattr(explicit, name).tobytes(), name


def test_x3_scales_stiffness_and_damping_of_both_directions() -> None:
    base = _plant_class()("top", 0.0, 0.0)
    stiff = _plant_class()("top", 0.0, 0.0, crawler_k_scale=3.0)
    np.testing.assert_allclose(stiff.kcr, 3.0 * base.kcr, rtol=1e-15)
    np.testing.assert_allclose(stiff.ktcr, 3.0 * base.ktcr, rtol=1e-15)
    np.testing.assert_allclose(stiff.ccr, math.sqrt(3.0) * base.ccr, rtol=1e-15)
    np.testing.assert_allclose(stiff.ctcr, math.sqrt(3.0) * base.ctcr, rtol=1e-15)


def test_x3_settle_pose_is_the_stiffer_crawler_statics() -> None:
    """End condition of P-1: mean sphere compression 1.27 mm +- 5 %, flat settle pitch
    0.086 +- 0.01 deg, 12 loaded spheres (the pose is computed with the scaled springs)."""
    plant = _plant_class()("top", 0.0, 0.0, crawler_k_scale=3.0)
    compression_mm, n_loaded = _crawler_compression(plant)
    assert compression_mm == pytest.approx(X3_COMPRESSION_MM, rel=X3_COMPRESSION_REL_TOL)
    assert n_loaded == X3_ACTIVE_SPHERES
    pitch_deg = math.degrees(plant.attitude()[1])
    assert abs(pitch_deg - X3_FLAT_PITCH_DEG) <= X3_FLAT_PITCH_TOL_DEG


def test_module_factor_reaches_plants_built_without_the_keyword(monkeypatch) -> None:
    """FlexPlant and the soil harness call ``Plant.__init__`` positionally: the module value."""
    monkeypatch.setattr(rcc, "CRAWLER_K_SCALE", 3.0)
    plant = rcc.Plant("top", 0.0, 0.0)
    assert plant.crawler_k_scale == 3.0
    assert _crawler_compression(plant)[1] == X3_ACTIVE_SPHERES


@pytest.mark.parametrize("scale", [0.0, -1.0, float("nan")])
def test_bad_factor(scale) -> None:
    with pytest.raises(ValueError):
        _plant_class()("top", 0.0, 0.0, crawler_k_scale=scale)
