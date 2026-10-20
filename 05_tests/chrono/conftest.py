"""Shared Chrono test objects: the single pad-sized block of the stick-friction baseline.

The block reproduces ``04_scripts/02_chrono/test_stick_friction.py`` (``build``, bushing
cases) with library code: ``make_system`` (R1, R2, R6, R11) + ``GroundBushingCoulomb``.
Its values are the ``reference`` block of ``06_analysis/01_chrono/stick_friction.json`` (the
baseline was computed with the ζ 0.05 contact values of that day; the current YAML has
ζ 0.03), so the regression compares like with like.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pytest

pytest.importorskip("pychrono")

import pychrono as ch  # noqa: E402

from outrigger_sim.chrono.ground_bushing import (  # noqa: E402
    GroundBushingCoulomb,
    PadBushingSpec,
)
from outrigger_sim.chrono.system import make_smc_material, make_system  # noqa: E402
from outrigger_sim.params import Params, load_params  # noqa: E402

STICK_FRICTION_JSON = Path("06_analysis") / "01_chrono" / "stick_friction.json"
# Baseline script constants (not in the JSON reference block).
BLOCK_SLIP_DAMPING_REENABLE_M_S = 1.0e-3  # V_STICK of the script = YAML value 0.001
BLOCK_GROUND_BOX_M = (60.0, 4.0, 0.4)  # ground box of the script, top face at z_local = 0


@dataclass
class BlockModel:
    """One block on a (tilted) floor with a ground bushing."""

    system: Any
    floor: Any
    block: Any
    bushing: GroundBushingCoulomb
    normal: np.ndarray
    tangent: np.ndarray
    start_pos: np.ndarray
    dt_s: float
    weight_N: float

    def step(self) -> list[Any]:
        self.system.DoStepDynamics(self.dt_s)
        return self.bushing.after_step()

    def pos(self) -> np.ndarray:
        p = self.block.GetPos()
        return np.array([p.x, p.y, p.z])


@pytest.fixture(scope="session")
def params() -> Params:
    return load_params()


@pytest.fixture(scope="session")
def stick_reference(project_root: Path) -> dict[str, Any]:
    """``stick_friction.json``: ``reference`` values and ``cases`` by name."""
    data = json.loads((project_root / STICK_FRICTION_JSON).read_text(encoding="utf-8"))
    return {"reference": data["reference"], "cases": {c["name"]: c for c in data["cases"]}}


@pytest.fixture(scope="session")
def block_factory(params: Params, stick_reference: dict[str, Any]) -> Callable[..., BlockModel]:
    """Return ``build(slope_deg, *, v0=(0,0,0), dt=None, solver=None, lock=None)``."""
    ref = stick_reference["reference"]

    def build(
        slope_deg: float,
        *,
        v0: tuple[float, float, float] = (0.0, 0.0, 0.0),
        dt: float | None = None,
        solver: str | None = None,
        lock: bool | None = None,
        name: str = "block",
    ) -> BlockModel:
        dt_s = float(ref["dt_s"]) if dt is None else dt
        bundle = make_system(
            params, dt=dt_s, floor_plate=False, solver=solver, lock_sparsity_pattern=lock
        )
        system, floor = bundle.system, bundle.floor
        a = math.radians(slope_deg)
        n = np.array([math.sin(a), 0.0, math.cos(a)])
        t = np.array([math.cos(a), 0.0, -math.sin(a)])
        floor.SetRot(ch.QuatFromAngleY(a))
        mass = float(ref["mass_kg"])
        radius = float(ref["sphere_radius_m"])
        material = make_smc_material(float(ref["kn_N_m"]), float(ref["cn_N_s_m"]) / mass)
        floor.EnableCollision(True)
        bx, by, bz = BLOCK_GROUND_BOX_M
        floor.AddCollisionShape(
            ch.ChCollisionShapeBox(material, bx, by, bz),
            ch.ChFramed(ch.ChVector3d(0.0, 0.0, -0.5 * bz), ch.QUNIT),
        )
        g = params.meta.gravity_m_s2
        block = ch.ChBody()
        block.SetName(name)
        block.SetMass(mass)
        block.SetInertiaXX(ch.ChVector3d(1.0, 1.0, 1.0) * (mass / 6.0))
        delta0 = mass * g * math.cos(a) / float(ref["kn_N_m"])
        c0 = n * (radius - delta0)
        block.SetPos(ch.ChVector3d(*c0))
        block.SetPosDt(ch.ChVector3d(*v0))
        block.EnableCollision(True)
        block.AddCollisionShape(ch.ChCollisionShapeSphere(material, radius), ch.ChFramed())
        system.Add(block)
        align = ch.ChLinkLockAlign()
        align.Initialize(block, floor, ch.ChFramed(ch.ChVector3d(*c0), ch.QUNIT))
        system.Add(align)
        pad = PadBushingSpec(
            name=name,
            body=block,
            sphere_centre_body_local_m=(0.0, 0.0, 0.0),
            sphere_radius_m=radius,
            stiffness_N_m=float(ref["kt_N_m"]),
            damping_input_N_s_m=0.5 * float(ref["ct_N_s_m"]),  # R7
        )
        bushing = GroundBushingCoulomb(
            system,
            floor,
            [pad],
            friction=float(ref["mu"]),
            slip_damping_reenable_speed_m_s=BLOCK_SLIP_DAMPING_REENABLE_M_S,
            dt_s=dt_s,
        )
        bushing.attach()
        return BlockModel(system, floor, block, bushing, n, t, c0, dt_s, mass * g)

    return build
