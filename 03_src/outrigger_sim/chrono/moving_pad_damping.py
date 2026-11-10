"""L1-R moving-leg pad damping (K-2 V-6, ``k2_touch_creep_rules.md`` 3.5, ``k2_dyn_spec.md`` 3).

The L1 pad contact is SMC Hooke with one LOCK-based dashpot ``g_n`` per leg
(``contact.rigid_floor.L1.gn_per_pad_1_s``, leg axial ``zeta`` 0.03,
``derivation.damping_ratio``). The dynamics specification gives a moving leg (valve open) the
axial ``zeta`` 0.10: only the **normal** dashpot changes,
``c_n,move = c_n,LOCK x zeta_move / zeta_LOCK``; the tangential path (ground bushing, not the
SMC material) keeps its LOCK values.

Mechanism (chrono-rag, PyChrono 10.0.0 sources):

* ``ChContactContainerSMC::AddContact`` (``src/chrono/physics/ChContactContainerSMC.cpp:94``)
  builds a new ``ChContactMaterialCompositeSMC`` from the two shape materials at every collision
  detection, i.e. every step; a material changed in a step hook acts from the next step (the
  1-step hook-lag convention).
* ``ChContactMaterialCompositeSMC`` (``ChContactMaterialSMC.cpp:124``):
  ``gn = CombineDampingCoefficient(gn_1, gn_2)``; the default strategy
  (``ChContactMaterial.h:157``) is the mean ``(a1 + a2) / 2``. The pad sphere and its floor
  patch carry the same material values (``chrono/contact`` R13), so both are set to the moving
  value and the composite equals it. ``m_eff`` does not change, so ``c_n`` scales with ``g_n``.

Valve open (the dynamics definition): ``|u| > lock_eps`` with ``u`` the spool state that drives
the step (``L1SpeedActuator.valve_state_m_s`` read in the runner step hook) and ``lock_eps`` =
``actuator.rod_side.lock_eps_m_s`` (1e-6 m/s). Decided per physics step (dt 2e-4 s, finer than
the harness 1 ms chunks); the valve lag tail follows the same ``|u|`` rule.

The L1-R machine's one-sided clamp (``chrono/rod_chamber_link.one_sided_extra_force_N``) uses its
own ``c_n`` copy; the hook scales it by the same factor in the same call. The machine step of a
step runs before the step hook, so the clamp sees the new value one step after Chrono (the clamp
acts only near zero contact force; ASSUMPTION that this one-step offset is negligible).

Not installed = no material or machine value is touched (bit-identical runs).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pychrono as ch

from outrigger_sim.params import LEG_ORDER

LOCK_EPS_KEY = "actuator.rod_side.lock_eps_m_s"
ZETA_LOCK_KEY = "contact.rigid_floor.L1.derivation.damping_ratio"
SERIES_NAME = "pad_damping.npz"


@dataclass(frozen=True)
class MovingPadDampingSettings:
    """``zeta_moving`` [-] of an open leg, ``lock_eps_m_s`` [m/s], ``zeta_lock`` [-] (YAML)."""

    zeta_moving: float
    lock_eps_m_s: float
    zeta_lock: float

    def __post_init__(self) -> None:
        for name in ("zeta_moving", "lock_eps_m_s", "zeta_lock"):
            v = float(getattr(self, name))
            if not (v > 0.0 and np.isfinite(v)):
                raise ValueError(f"{name} must be > 0 and finite, got {v!r}")

    @property
    def factor(self) -> float:
        return float(self.zeta_moving) / float(self.zeta_lock)

    @classmethod
    def from_params(cls, params: Any, zeta_moving: float) -> MovingPadDampingSettings:
        return cls(
            float(zeta_moving), float(params.get(LOCK_EPS_KEY)), float(params.get(ZETA_LOCK_KEY))
        )


def open_fraction(switches, t_from_s: float, t_to_s: float, n_legs: int = 4) -> list[float] | None:
    """Per leg: time share of ``[t_from, t_to]`` with the open decision in force.

    ``switches`` = ``(t, leg, is_open)`` in time order; a decision at ``t`` holds until the next
    one of that leg, LOCK before the first. None for an empty window.
    """
    a, b = float(t_from_s), float(t_to_s)
    if not b > a:
        return None
    out = []
    for i in range(n_legs):
        state, t_prev, open_s = False, a, 0.0
        for t, leg, s in switches:
            if int(leg) != i:
                continue
            t = float(t)
            if t > b:
                break
            if t > t_prev:
                open_s += (t - t_prev) if state else 0.0
                t_prev = t
            state = bool(s)
        open_s += (b - t_prev) if state else 0.0
        out.append(open_s / (b - a))
    return out


def load_switches(path: Path | str) -> list[tuple[float, int, bool]]:
    """The switches of a saved :data:`SERIES_NAME`."""
    with np.load(path) as d:
        return [
            (float(t), int(leg), bool(s))
            for t, leg, s in zip(d["t"], d["leg"], d["is_open"], strict=True)
        ]


def _smc(shape_owner: ch.ChBody, index: int) -> ch.ChContactMaterialSMC:
    model = shape_owner.GetCollisionModel()
    mat = ch.CastToChContactMaterialSMC(model.GetShapeInstance(index).shape.GetMaterial())
    if mat is None:
        raise RuntimeError(f"{shape_owner.GetName()}: shape {index} has no SMC material")
    return mat


def pad_materials(model: Any) -> list[tuple[ch.ChContactMaterialSMC, ch.ChContactMaterialSMC]]:
    """``(pad sphere material, pad patch material)`` per leg (LEG_ORDER) of an ``L1Model``.

    The sphere is the only collision shape of the leg body; the patch is shape ``k`` of the floor
    body (``k`` = index of ``pad_<leg>`` in ``model.floor_body_patches``, the order of
    ``add_floor_patches``) or shape 0 of a settlement / block patch body.

    Raises:
        RuntimeError: A leg body without exactly one shape, or a patch not found.
    """
    by_body: dict[str, ch.ChBody] = {}
    settlement = getattr(model, "settlement", None)
    if settlement is not None:
        by_body.update(dict(zip(settlement.leg_names, settlement.bodies, strict=True)))
    blocks = getattr(model, "pad_blocks", None)
    if blocks is not None:
        by_body.update(blocks.bodies)
    floor_names = [p.name for p in model.floor_body_patches]
    out = []
    for name, leg in zip(LEG_ORDER, model.legs, strict=True):
        if leg.GetCollisionModel().GetNumShapes() != 1:
            raise RuntimeError(f"leg {name}: expected one pad sphere shape")
        sphere = _smc(leg, 0)
        if name in by_body:
            patch = _smc(by_body[name], 0)
        else:
            try:
                k = floor_names.index(f"pad_{name}")
            except ValueError as error:
                raise RuntimeError(f"leg {name}: no floor patch pad_{name}") from error
            patch = _smc(model.floor, k)
        out.append((sphere, patch))
    return out


class MovingPadDamping:
    """Runner ``step_hook`` (module docstring).

    Per step, a leg with ``|u| > lock_eps`` gets ``g_n x factor`` on its pad sphere and patch
    materials (acting from the next step), a LOCK leg the YAML value. Records the per-step
    decision as transitions (``t`` = Chrono time at the hook, absolute s).
    """

    def __init__(self, model: Any, settings: MovingPadDampingSettings) -> None:
        self.model = model
        self.settings = settings
        self.materials = pad_materials(model)
        self.gn_lock = np.array([float(s.GetGn()) for s, _ in self.materials])
        patch_gn = np.array([float(p.GetGn()) for _, p in self.materials])
        if not np.array_equal(self.gn_lock, patch_gn):
            raise RuntimeError(f"pad sphere / patch g_n differ {self.gn_lock} / {patch_gn}")
        self.gn_move = np.array([float(np.float32(g * settings.factor)) for g in self.gn_lock])
        rc = getattr(model, "rod_chamber", None)
        self._rc = rc if rc is not None and getattr(rc, "enabled", False) else None
        self.c_lock = None if self._rc is None else np.array(self._rc._contact_damping, float)
        self.c_move = None if self.c_lock is None else self.c_lock * (self.gn_move / self.gn_lock)
        self.state = np.zeros(len(self.materials), dtype=bool)
        self.t_first: float | None = None
        self.t_last: float | None = None
        self.n_steps = 0
        self.open_steps = np.zeros(len(self.materials), dtype=np.int64)
        self.switches: list[tuple[float, int, bool]] = []

    def _set(self, i: int, is_open: bool) -> None:
        gn = float(self.gn_move[i] if is_open else self.gn_lock[i])
        sphere, patch = self.materials[i]
        sphere.SetGn(gn)
        patch.SetGn(gn)
        if self._rc is not None:
            self._rc._contact_damping[i] = float(self.c_move[i] if is_open else self.c_lock[i])

    def __call__(self, engine: Any) -> None:
        t = float(self.model.system.GetChTime())
        u = np.abs(np.asarray(self.model.actuator.valve_state_m_s, float))
        want = u > self.settings.lock_eps_m_s
        if self.t_first is None:
            self.t_first = t
        self.t_last = t
        self.n_steps += 1
        self.open_steps += want
        for i in np.flatnonzero(want != self.state):
            self._set(int(i), bool(want[i]))
            self.switches.append((t, int(i), bool(want[i])))
        self.state = want

    def restore_lock(self) -> None:
        """Every leg back to the LOCK values (end of a run)."""
        for i in range(len(self.materials)):
            self._set(i, False)
        self.state[:] = False

    def open_fraction(self, t_from_s: float, t_to_s: float) -> list[float] | None:
        """:func:`open_fraction` of this run's switches."""
        return open_fraction(self.switches, t_from_s, t_to_s, len(self.materials))

    def save(self, path: Path | str) -> dict[str, Any]:
        sw = np.asarray(self.switches, dtype=float).reshape(-1, 3)
        np.savez_compressed(
            path, t=sw[:, 0], leg=sw[:, 1].astype(np.int8), is_open=sw[:, 2].astype(bool)
        )
        return {
            "file": Path(path).name,
            "switches": int(sw.shape[0]),
            "columns": "t (absolute s, hook time), leg (0..3 LEG_ORDER), "
            "is_open (decision acting from the next step)",
        }

    def meta(self) -> dict[str, Any]:
        s = self.settings

        def by_leg(values):
            return None if values is None else dict(zip(LEG_ORDER, values.tolist(), strict=True))

        return {
            "enabled": True,
            "zeta_moving": s.zeta_moving,
            "zeta_lock": s.zeta_lock,
            "factor": s.factor,
            "lock_eps_m_s": s.lock_eps_m_s,
            "gn_lock_1_s": by_leg(self.gn_lock),
            "gn_move_1_s": by_leg(self.gn_move),
            "c_lock_N_s_m": by_leg(self.c_lock),
            "c_move_N_s_m": by_leg(self.c_move),
            "n_steps": self.n_steps,
            "n_switches": len(self.switches),
            "open_step_share": by_leg(self.open_steps / max(self.n_steps, 1)),
            "rule": "open = |valve_state_m_s| > lock_eps per step (step hook); g_n of the pad "
            "sphere and its patch material = g_n,LOCK x zeta_moving / zeta_lock (normal only, "
            "SMC composite = mean of the two), from the next step; L1-R clamp c_n scaled in the "
            "same call (k2_dyn_spec.md 3)",
        }
