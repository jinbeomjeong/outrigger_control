"""L2b-NSC lateral leg bushing: leg moving part <-> superstructure at the ball centre.

``00_docs/03_chrono/chrono_build_plan.md`` S7 ('횡 부싱(입력 c_t/2), 가이드 x·y 해제');
``dynamics_model.md`` 2.3 (L2b-NSC row), 4.2.

With the drive guide freed in x, y (``chrono/l2b_actuator.GUIDE_FREE_XY``) the rod is held
laterally only by this bushing: stiffness ``k = actuator.L2b_NSC.lateral_bushing_N_m`` (swivel
leg bending in series with the concrete tangential stiffness, load at the ball centre) on both
lateral axes of the leg link frame, nothing on the leg axis (the axial path is the force law).

**Why not ``ChLoadBodyBodyBushingSpherical``** (the plan's '입력 c_t/2' bushing): it is a stiff
load with K / R Jacobians, and ``ChSolverPSOR`` refuses any system with stiffness or damping
matrices ("ChSolverPSOR: Can NOT use PSOR solver if the system includes stiffness or damping
matrices", pychrono 10.0.0, single-leg probe 2026-10-24). The L2b-NSC solver is PSOR 50
(``contact.rigid_floor.L2b_NSC.solver``), so the bushing is built from Jacobian-free items:

* per leg and lateral axis one ``ChLinkMotorLinearForce`` with guide FREE (no constraint at
  all), frames at the ball centre: frame 1 on the rod, frame 2 on the superstructure with its
  Z axis = link x (resp. link y). ``GetMotorPos()`` / ``GetMotorPosDt()`` are then the lateral
  offset of the rod point along that superstructure axis and its rate;
* after every step the hook sets ``F = -k (d - d_0) - c d'`` (``d_0`` = offset at build
  time = 0 for coincident frames). ``ChLinkMotorLinearForce::IntLoadResidual_F``
  (``ChLinkMotorLinearForce.cpp:36``) applies ``F`` along frame-2 Z on body 1 and ``-F`` on
  body 2, both at frame 1's point (no spurious moment), in the next step: an explicit spring
  (semi-implicit Euler, no numerical damping; stable for ``omega dt`` << 2: rod lateral
  ``sqrt(k/m)`` = 259 rad/s front, 186 rad/s rear).
* ``c`` is the **actual** dashpot = 2 x ``lateral_bushing_damping_input_N_s_m`` (the YAML input
  is halved for the 2x of ``ChLoadBodyBodyBushing*``; this element has no such factor). It equals
  ``contact.rigid_floor.L1.ct_per_pad_N_s_m`` (checked by the unit test).

Departure from ``dynamics_model.md`` 4.3 (implicit bushing, numerical damping ``r omega dt /
2``): this bushing is explicit, so the L2b-NSC lateral modes get no implicit-Euler numerical
damping; dynamics-expert to confirm the Δt rule for L2b-NSC.

Units SI; per-leg order as given.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pychrono as ch
from numpy.typing import NDArray

from outrigger_sim.params import LEG_ORDER, Params

HOOK_TIME_REL_TOL = 1.0e-12


class LateralHookMissedError(RuntimeError):
    """A step would run with lateral forces the hook did not set for it."""


@dataclass(frozen=True)
class LateralBushingValues:
    """Per-leg values (actual damping) with their YAML source."""

    stiffness_N_m: tuple[float, ...]
    damping_N_s_m: tuple[float, ...]
    """Actual dashpot = 2 x the YAML Chrono-bushing input."""
    source: str = (
        "actuator.L2b_NSC.lateral_bushing_N_m; damping = 2 x "
        "actuator.L2b_NSC.lateral_bushing_damping_input_N_s_m (input = actual / 2)"
    )


def lateral_bushing_values(params: Params, legs: Sequence[str] = LEG_ORDER) -> LateralBushingValues:
    if params.l2b is None:
        raise ValueError('params must be loaded with model="L2b_NSC"')
    a = params.l2b.actuator
    idx = [LEG_ORDER.index(name) for name in legs]
    return LateralBushingValues(
        stiffness_N_m=tuple(a.lateral_bushing_N_m[i] for i in idx),
        damping_N_s_m=tuple(2.0 * a.lateral_bushing_damping_input_N_s_m[i] for i in idx),
    )


class LateralBushings:
    """Explicit lateral bushings of the legs (module docstring).

    Args:
        system: Chrono system (the force elements are added to it).
        rods: Leg moving parts.
        superstructure: Body the legs hang from (a fixed frame in the single-leg test).
        frames_abs: Absolute link frame per leg at the ball centre (Z = leg axis, body -z).
        values: Stiffness and actual damping per leg.
    """

    def __init__(
        self,
        system: ch.ChSystem,
        rods: Sequence[ch.ChBody],
        superstructure: ch.ChBody,
        frames_abs: Sequence[ch.ChFramed],
        values: LateralBushingValues,
    ) -> None:
        n = len(rods)
        if len(frames_abs) != n or len(values.stiffness_N_m) != n:
            raise ValueError("need one frame and one value per leg")
        self.values = values
        self._k = np.array(values.stiffness_N_m, dtype=float)
        self._c = np.array(values.damping_N_s_m, dtype=float)
        self.motors: list[tuple[ch.ChLinkMotorLinearForce, ch.ChLinkMotorLinearForce]] = []
        self._functions: list[tuple[ch.ChFunctionConst, ch.ChFunctionConst]] = []
        # rotate the link frame so that its x (resp. y) axis becomes the element's Z axis
        to_x = ch.QuatFromAngleY(np.pi / 2.0)  # local Z -> link x
        to_y = ch.QuatFromAngleX(-np.pi / 2.0)  # local Z -> link y
        for i, (rod, frame) in enumerate(zip(rods, frames_abs, strict=True)):
            pair = []
            fns = []
            for axis, q_axis in (("x", to_x), ("y", to_y)):
                f = ch.ChFramed(frame.GetPos(), frame.GetRot() * q_axis)
                motor = ch.ChLinkMotorLinearForce()
                motor.SetName(f"lateral_bushing_{i}_{axis}")
                motor.SetGuideConstraint(ch.ChLinkMotorLinear.GuideConstraint_FREE)
                motor.Initialize(rod, superstructure, False, f, f)
                fn = ch.ChFunctionConst(0.0)
                motor.SetForceFunction(fn)
                system.Add(motor)
                pair.append(motor)
                fns.append(fn)
            self.motors.append((pair[0], pair[1]))
            self._functions.append((fns[0], fns[1]))
        self._force = np.zeros((n, 2))
        self._acting = np.zeros((n, 2))
        self._hook_t: float | None = None

    @property
    def n_legs(self) -> int:
        return len(self.motors)

    def displacement_m(self) -> NDArray[np.float64]:
        """Lateral offset of each rod ball point in the link axes (x, y) [m], shape (n, 2)."""
        return np.array([[m.GetMotorPos() for m in pair] for pair in self.motors], dtype=float)

    def velocity_m_s(self) -> NDArray[np.float64]:
        return np.array([[m.GetMotorPosDt() for m in pair] for pair in self.motors], dtype=float)

    @property
    def force_on_rod_N(self) -> NDArray[np.float64]:
        """Force set by the last hook on each rod in the link axes (x, y) [N] (acts next step)."""
        return self._force.copy()

    @property
    def acting_force_on_rod_N(self) -> NDArray[np.float64]:
        """Force that acted on each rod during the step just taken, link axes (x, y) [N]."""
        return self._acting.copy()

    def on_step_start(self, t_s: float) -> None:
        if self._hook_t is None:
            return
        if abs(self._hook_t - float(t_s)) > HOOK_TIME_REL_TOL * max(abs(t_s), 1.0):
            raise LateralHookMissedError(
                f"step at t = {t_s!r} s but the lateral bushing hook last ran at {self._hook_t!r} s"
            )

    def on_step_end(self) -> None:
        self._acting = self._force.copy()

    def hook(self, t_s: float) -> None:
        """After a step: ``F = -k d - c d'`` from the state at ``t_s`` (acts next step)."""
        d = self.displacement_m()
        v = self.velocity_m_s()
        self._force = -self._k[:, None] * d - self._c[:, None] * v
        for fns, forces in zip(self._functions, self._force, strict=True):
            fns[0].SetConstant(float(forces[0]))
            fns[1].SetConstant(float(forces[1]))
        self._hook_t = float(t_s)

    def force_on_rod_world_N(self, acting: bool = True) -> NDArray[np.float64]:
        """Bushing force on each rod in world axes, (n, 3) [N] (acting = of the last step)."""
        forces = self._acting if acting else self._force
        out = np.zeros((self.n_legs, 3))
        for i, pair in enumerate(self.motors):
            for j, motor in enumerate(pair):
                z = motor.GetFrame2Abs().GetRotMat().GetAxisZ()
                out[i] += forces[i, j] * np.array([z.x, z.y, z.z])
        return out

    # --- snapshot (R16) -------------------------------------------------------------------

    def state_arrays(self) -> dict[str, NDArray[Any]]:
        return {
            "force_N": self._force.copy(),
            "acting_force_N": self._acting.copy(),
            "hook_t_s": np.array([np.nan if self._hook_t is None else self._hook_t]),
        }

    def restore_state(self, arrays: Any) -> None:
        self._force = np.array(arrays["force_N"], dtype=float).reshape(self.n_legs, 2)
        self._acting = np.array(arrays["acting_force_N"], dtype=float).reshape(self.n_legs, 2)
        hook = float(np.asarray(arrays["hook_t_s"]).reshape(-1)[0])
        self._hook_t = None if np.isnan(hook) else hook
        for fns, forces in zip(self._functions, self._force, strict=True):
            fns[0].SetConstant(float(forces[0]))
            fns[1].SetConstant(float(forces[1]))

    def mark_hooked(self, t_s: float) -> None:
        self._hook_t = float(t_s)

    def meta(self) -> dict[str, Any]:
        return {
            "type": "explicit: 2 ChLinkMotorLinearForce per leg (guide FREE, Z = link x / y), "
            "F = -k d - c d' set after each step (PSOR refuses ChLoadBodyBodyBushing*)",
            "stiffness_N_m": list(self.values.stiffness_N_m),
            "damping_actual_N_s_m": list(self.values.damping_N_s_m),
            "source": self.values.source,
        }


__all__ = [
    "LateralBushingValues",
    "LateralBushings",
    "LateralHookMissedError",
    "lateral_bushing_values",
]
