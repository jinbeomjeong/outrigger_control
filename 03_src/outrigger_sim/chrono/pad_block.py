"""Rigid block under one pad on the rigid floor (C-S8-76, non-planar start G8).

``00_docs/04_control/s6_control_spec.md`` rev. 69 360.1 / 363: after the crawler settle the
floor under ONE pad is raised so that its zero-stroke gap becomes ``g_start`` (crawler floor
unchanged). On the L1 Chrono model this is a block of height ``h`` (= g0 - g_start) under that
pad (only when ``L1Model(pad_blocks=...)`` names legs; default none = the model unchanged,
bit-identical):

* the pad patch of each named leg is taken off the fixed floor body and put on its own
  **block body**: fixed (``SetFixed(True)``), mass ``contact.rigid_floor.ground_body_mass_kg``
  (1e9 kg, R6) like the floor body, the floor's orientation, its origin moved by ``h`` along
  the floor normal. Same patch box (footprint ``2 x PAD_PATCH_HALF_SIZE_M`` = 0.8 m square >= the
  0.330 m pad), same SMC material, collision family floor: the contact model and the contact
  material are those of the floor (the SMC ``m_eff`` sees the same 1e9 kg ground mass; Chrono
  ``ChDefaultContactForceTorqueSMC`` takes ``mass1`` / ``mass2`` of the two contactables,
  ``src/chrono/physics/ChContactSMC.h:53``);
* the leg's ground bushing uses the block body as body B (``GroundBushingCoulomb(leg_floors)``),
  and the L1-R deflection is measured against the block surface (``rod_chamber_link``: patch
  offset ``s = n . (x_block - x_floor)`` = ``h``, block velocity 0), as for a settlement patch.

The block body is not a snapshot body (fixed, no state): a snapshot of the settled crawler
restores into a model with a block unchanged, provided the pad does not overlap the block at
the restored state (the runner checks ``g_start > 0``).

Diagnostic caveat (as ``ground_settlement``): ``ProbeState.penetration_m`` measures against the
fixed floor plane, so a blocked leg reads its penetration too large by ``h``; use
:meth:`PadBlocks.offsets_m` to correct gaps. Units SI.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pychrono as ch
from numpy.typing import NDArray

PART_NAME = "pad_blocks"


class PadBlocks:
    """Fixed block bodies under named pads (module docstring).

    Args:
        floor: Fixed floor body (its pose is final: blocks copy it at construction).
        heights_m: Block height per leg name (> 0, along the floor normal).
        bodies: One block body per leg (already added, with its collision shape).
    """

    def __init__(self, floor: ch.ChBody, heights_m: Mapping[str, float],
                 bodies: Mapping[str, ch.ChBody]) -> None:
        self.floor = floor
        self.heights_m = {k: float(v) for k, v in heights_m.items()}
        self.bodies = dict(bodies)

    @property
    def leg_names(self) -> tuple[str, ...]:
        return tuple(self.heights_m)

    def offsets_m(self, leg_order: Sequence[str]) -> NDArray[np.float64]:
        """Block height per leg of ``leg_order`` (0 without a block) [m]."""
        return np.array([self.heights_m.get(n, 0.0) for n in leg_order], dtype=float)

    def surface_offset_measured_m(self, name: str) -> float:
        """``n . (x_block - x_floor)`` of the Chrono bodies (= the height; check value)."""
        body = self.bodies[name]
        n = self.floor.TransformDirectionLocalToParent(ch.ChVector3d(0.0, 0.0, 1.0))
        p, f = body.GetPos(), self.floor.GetPos()
        return float((p.x - f.x) * n.x + (p.y - f.y) * n.y + (p.z - f.z) * n.z)

    def meta(self) -> dict[str, Any]:
        return {
            "legs": list(self.leg_names),
            "height_m": dict(self.heights_m),
            "height_measured_m": {n: self.surface_offset_measured_m(n) for n in self.leg_names},
            "model": "fixed 1e9 kg block body per leg (floor orientation, origin + h n), the leg's "
                     "pad patch box and SMC material moved onto it; ground bushing body B = block "
                     "body; L1-R deflection against the block surface (C-S8-76, spec rev. 69 363)",
        }


def make_block_body(floor: ch.ChBody, name: str, height_m: float, mass_kg: float) -> ch.ChBody:
    """A fixed body with the floor's orientation, its origin moved by ``height_m`` along the
    floor normal (collision shapes added by the caller in floor-body coordinates)."""
    if not (np.isfinite(height_m) and height_m > 0.0):
        raise ValueError(f"block height of {name} must be > 0, got {height_m!r}")
    body = ch.ChBody()
    body.SetName(f"pad_block_{name}")
    body.SetMass(float(mass_kg))
    body.SetInertiaXX(ch.ChVector3d(mass_kg, mass_kg, mass_kg))
    fpos, frot = floor.GetPos(), floor.GetRot()
    n = floor.TransformDirectionLocalToParent(ch.ChVector3d(0.0, 0.0, 1.0))
    body.SetPos(ch.ChVector3d(fpos.x + height_m * n.x, fpos.y + height_m * n.y,
                              fpos.z + height_m * n.z))
    body.SetRot(ch.ChQuaterniond(frot.e0, frot.e1, frot.e2, frot.e3))
    body.SetFixed(True)
    return body


__all__ = ["PART_NAME", "PadBlocks", "make_block_body"]
