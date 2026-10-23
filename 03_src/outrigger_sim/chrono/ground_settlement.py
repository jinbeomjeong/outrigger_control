"""Prescribed ground settlement under one pad on the rigid floor (S6 control check 6, G4).

``00_docs/04_control/s6_control_spec.md`` 3 item 6 (RR ground settles 11.5 mm with a 2 s ramp
at READY + 5 s; on a rigid floor the floor-side anchor and the contact floor move) and 4 (G4);
user approval 2026-10-21 of the cad-expert proposal.

Model (only when ``L1Model(settlement_legs=...)`` names legs; default none = the S1-S6 model,
bit-identical):

* the pad patch of each named leg is taken off the fixed floor body and put on its own
  **patch body** (mass ``contact.rigid_floor.ground_body_mass_kg`` = 1e9 kg, R6, same pose
  as the floor, collision family floor, same SMC material);
* the patch body is tied to the floor by a ``ChLinkMotorLinearPosition`` (guide PRISMATIC,
  motor Z = floor normal) whose motion function is 0 until :meth:`GroundSettlement.schedule`
  sets ``z(t) = -depth * P345((t - t_start) / ramp)`` (``ChFunctionSequence`` of a constant 0,
  ``ChFunctionPoly345`` and a constant ``-depth``: position, velocity and acceleration
  continuous, so the SMC contact damping sees the true floor velocity);
* the leg's ground bushing uses the patch body as body B (``GroundBushingCoulomb(leg_floors)``),
  so the anchor moves with the settling floor (the normal offset of frame A is not loaded, the
  tangential anchor stays where the return mapping put it in patch coordinates).

Timing: the function is defined over time and :meth:`schedule` must be called at least two
steps before ``t_start`` (the motor function set between steps is loaded one step later, R15;
before ``t_start`` the new and the old function are both 0, so nothing jumps).

Snapshot: part ``ground_settlement`` (``t_start_s``, ``depth_m``, ``ramp_s``; NaN = not
scheduled). The patch body state is a function of time: after a restore
:meth:`GroundSettlement.sync` puts it on the prescribed position / velocity. Snapshots without
the part (states of models without settlement) restore with no settlement scheduled.

Diagnostic caveat: ``ProbeState.penetration_m`` measures against the fixed floor plane, so a
settled leg reads its penetration too small by the settlement depth.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pychrono as ch
from numpy.typing import NDArray

PART_PREFIX = "ground_settlement"
STATE_KEYS = ("t_start_s", "depth_m", "ramp_s")
DEFAULT_DEPTH_M = 0.0115
"""s6_control_spec.md 3 item 6: RR settlement 11.5 mm."""
DEFAULT_RAMP_S = 2.0
"""s6_control_spec.md 3 item 6: 2 s ramp."""
TAIL_S = 1.0e7
"""Duration of the final constant segment (longer than any run)."""


class GroundSettlement:
    """Patch bodies and motors of the settling legs (module docstring).

    Args:
        system: Chrono system.
        floor: Fixed floor body.
        leg_names: Settling legs (LEG_ORDER names).
        patch_bodies: One patch body per leg (already added, with its collision shape).
    """

    def __init__(
        self,
        system: ch.ChSystem,
        floor: ch.ChBody,
        leg_names: Sequence[str],
        patch_bodies: Sequence[ch.ChBody],
    ) -> None:
        self.system = system
        self.floor = floor
        self.leg_names = tuple(leg_names)
        self.bodies = tuple(patch_bodies)
        p = floor.GetPos()
        q = floor.GetRot()
        self._floor_pos = ch.ChVector3d(p.x, p.y, p.z)
        self._floor_rot = ch.ChQuaterniond(q.e0, q.e1, q.e2, q.e3)
        self.motors: list[ch.ChLinkMotorLinearPosition] = []
        self._functions: list[ch.ChFunction] = []
        for name, body in zip(self.leg_names, self.bodies, strict=True):
            motor = ch.ChLinkMotorLinearPosition()
            motor.SetName(f"settlement_motor_{name}")
            frame = ch.ChFramed(self._floor_pos, self._floor_rot)  # Z = floor normal
            motor.Initialize(body, floor, False, frame, frame)
            fn = ch.ChFunctionConst(0.0)
            motor.SetMotionFunction(fn)
            system.Add(motor)
            self.motors.append(motor)
            self._functions.append(fn)
        self.t_start_s = math.nan
        self.depth_m = math.nan
        self.ramp_s = math.nan

    @property
    def is_scheduled(self) -> bool:
        return math.isfinite(self.t_start_s)

    def _make_function(self) -> ch.ChFunction:
        seq = ch.ChFunctionSequence()
        seq.InsertFunct(ch.ChFunctionConst(0.0), self.t_start_s)
        seq.InsertFunct(ch.ChFunctionPoly345(-self.depth_m, self.ramp_s), self.ramp_s)
        seq.InsertFunct(ch.ChFunctionConst(-self.depth_m), TAIL_S)
        seq.Setup()
        return seq

    def _apply(self) -> None:
        self._functions = []
        for motor in self.motors:
            fn = self._make_function() if self.is_scheduled else ch.ChFunctionConst(0.0)
            motor.SetMotionFunction(fn)
            self._functions.append(fn)

    def schedule(
        self,
        t_start_s: float,
        depth_m: float = DEFAULT_DEPTH_M,
        ramp_s: float = DEFAULT_RAMP_S,
        *,
        dt_s: float | None = None,
    ) -> None:
        """Start the settlement of every settling leg at ``t_start_s`` (module docstring).

        Raises:
            ValueError: Already scheduled, non-positive depth / ramp, or ``t_start_s`` less
                than two steps ahead of the system time.
        """
        if self.is_scheduled:
            raise ValueError("settlement already scheduled")
        if not (depth_m > 0.0 and ramp_s > 0.0):
            raise ValueError(f"depth and ramp must be positive: {depth_m!r}, {ramp_s!r}")
        t_now = float(self.system.GetChTime())
        lead = 2.0 * (dt_s if dt_s is not None else 0.0)
        if not t_start_s >= t_now + lead:
            raise ValueError(f"t_start {t_start_s!r} s must be >= now {t_now!r} + 2 dt")
        self.t_start_s, self.depth_m, self.ramp_s = float(t_start_s), float(depth_m), float(ramp_s)
        self._apply()

    def displacement_m(self, t_s: float | None = None) -> float:
        """Prescribed settlement (m, >= 0 = down) at ``t_s`` (default: now)."""
        if not self.is_scheduled:
            return 0.0
        t = float(self.system.GetChTime()) if t_s is None else float(t_s)
        return -float(self._functions[0].GetVal(t))

    def sync(self) -> None:
        """Put every patch body on its prescribed pose and velocity at the system time."""
        t = float(self.system.GetChTime())
        fn = self._functions[0] if self._functions else ch.ChFunctionConst(0.0)
        z, v, a = float(fn.GetVal(t)), float(fn.GetDer(t)), float(fn.GetDer2(t))
        n = self.floor.TransformDirectionLocalToParent(ch.ChVector3d(0.0, 0.0, 1.0))
        for body in self.bodies:
            body.SetPos(ch.ChVector3d(self._floor_pos.x + z * n.x, self._floor_pos.y + z * n.y,
                                      self._floor_pos.z + z * n.z))
            body.SetRot(self._floor_rot)
            body.SetPosDt(ch.ChVector3d(v * n.x, v * n.y, v * n.z))
            body.SetPosDt2(ch.ChVector3d(a * n.x, a * n.y, a * n.z))
            body.SetAngVelParent(ch.ChVector3d(0.0, 0.0, 0.0))

    # --- snapshot part ------------------------------------------------------------------

    def state_arrays(self) -> dict[str, NDArray[Any]]:
        return {
            "t_start_s": np.array([self.t_start_s]),
            "depth_m": np.array([self.depth_m]),
            "ramp_s": np.array([self.ramp_s]),
        }

    def restore_state(self, arrays: Mapping[str, NDArray[Any]]) -> None:
        missing = [k for k in STATE_KEYS if k not in arrays]
        if missing:
            raise ValueError(f"ground settlement state lacks {missing}")
        self.t_start_s = float(np.asarray(arrays["t_start_s"]).reshape(-1)[0])
        self.depth_m = float(np.asarray(arrays["depth_m"]).reshape(-1)[0])
        self.ramp_s = float(np.asarray(arrays["ramp_s"]).reshape(-1)[0])
        self._apply()
        self.sync()

    def finish_restore(self) -> None:
        self.sync()

    def meta(self) -> dict[str, Any]:
        return {
            "legs": list(self.leg_names),
            "t_start_s": None if not self.is_scheduled else self.t_start_s,
            "depth_m": None if not self.is_scheduled else self.depth_m,
            "ramp_s": None if not self.is_scheduled else self.ramp_s,
            "model": "separate 1e9 kg pad patch body per leg on a ChLinkMotorLinearPosition "
            "(floor normal), z = -depth Poly345((t - t_start)/ramp); ground bushing body B = "
            "patch body",
        }


__all__ = ["DEFAULT_DEPTH_M", "DEFAULT_RAMP_S", "PART_PREFIX", "GroundSettlement"]
