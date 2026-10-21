"""Chrono system factory: the one place where engine-wide conventions are applied.

Conventions of ``00_docs/03_chrono/chrono_build_plan.md`` section 1 applied here:

* R1  gravity is always set explicitly from ``meta.gravity_m_s2`` (pychrono 10.0.0 starts
  with a zero vector). Later changes (gravity ramp, V12) go through :func:`set_gravity`.
* R2  collision system Bullet (Chrono >= 9 creates no contacts without one).
* R6  fixed floor body with mass ``contact.rigid_floor.ground_body_mass_kg`` (1e9 kg) and
  ``SetFixed(True)``. SMC Hooke damping uses the effective mass ``m1 m2 / (m1 + m2)``,
  which includes the fixed body; the ChBody default of 1 kg kills it.
* R11 integrator ``EULER_IMPLICIT_LINEARIZED``; solver L1 ``SPARSE_LU`` with a locked
  sparsity pattern (``SPARSE_QR`` and ``PARDISO_MKL`` as options, lock can be switched off),
  L2b-NSC ``contact.rigid_floor.L2b_NSC.solver`` with ``solver_max_iterations`` (PSOR, 50).

L1 solver choice (user decision 2026-10-20,
``06_analysis/01_chrono/01_cost/solver_benchmark.json``): on the full-scale L1 model with the
pattern locked, SPARSE_QR 147, SPARSE_LU 133 and PARDISO_MKL 447 us/step with results equal to <= 1e-14 m. SPARSE_QR grows super-linearly
(above about 180 unknowns it is the slowest); Pardiso has a fixed cost per factorisation and
does not beat SPARSE_LU up to 4,500 unknowns. The lock cuts matrix assembly about 7x.

Sparsity pattern lock and structural changes (pychrono 10.0.0, checked 2026-10-20):
``ChDirectSolverLS::LockSparsityPattern(true)`` skips the sparsity-pattern learner on every
Setup call except the first one or one requested by ``ForceSparsityPatternUpdate()``.
Structural changes are still handled:

* Adding or removing a physics item through the system (``Add``, ``RemoveLink``,
  ``RemoveBody``, ``RemoveOtherPhysicsItem``; e.g. a ground bushing in its own
  ``ChLoadContainer`` created and removed by the R15 events) clears ``ChSystem::is_updated``;
  the time stepper then calls the solver Setup with ``analyze = true`` and the pattern is
  rebuilt (matrix assembly time of that step equals the first step's).
* Changes the system does not see (a load added to a container that is already in the
  system, ``SetFixed`` toggled, ...) do not trigger the analysis; the matrix still takes the
  new entries because Chrono writes them with an inserting element setter.

Probe (scratchpad, two free boxes on an SMC floor, 3000 steps, change at step 1000 and undone
at step 2000): link added/removed, body added/removed, bushing in a new container,
bushing added to an existing container, body fixed/released. Locked and unlocked SPARSE_LU
trajectories were bit-identical in every case (PARDISO_MKL locked vs unlocked: identical as
well). :func:`force_sparsity_pattern_update` asks for a fresh pattern on the next Setup; it was
not needed for correctness in any probe case but is cheap (one learner pass) and is the
documented Chrono remedy, so call it after structural changes the system does not see.
``SetDisabled`` on a link is not a usable event mechanism with any direct solver (enabling
a link that was disabled from the start gave LU factorisation failures and NaN with QR and
Pardiso, locked or not); create and remove items instead.

Pardiso MKL and the OpenMP runtime (investigated 2026-10-20): in Chrono-dev the
``libiomp5md.dll`` that ``mkl_intel_thread.2.dll`` delay-loads is the llvm-openmp
compatibility DLL, a pure forwarder (all exports -> ``libomp.dll``). When ``python.exe`` is
called without activating the env, ``Library\\bin`` is not on the DLL search path, the
forwarded ``omp_in_parallel`` cannot be resolved and the first Pardiso solve kills the
process with 0xC06D007F. No export is missing and the MKL version is right; the env works
when activated (``conda run``). Fix used here, without changing PATH: load
``<sys.prefix>\\Library\\bin\\libomp.dll`` by absolute path before ``pychrono.pardisomkl``
(:func:`preload_openmp_runtime`), only when Pardiso is requested.

SMC settings (L1) follow the regression baseline ``04_scripts/02_chrono/test_stick_friction.py``
(bushing cases): Hooke force model, ``UseMaterialProperties(False)`` so ``kn``/``gn`` are
used directly (``gn`` per effective mass, R5), tangential displacement model ``OneStep``
(irrelevant because every SMC material has ``kt = gt = mu = 0``, R8; kept identical to the
baseline so the bushing regression of S0 reproduces it), slip-velocity threshold and
contact-stiff flag left at the Chrono defaults (both recorded in the settings).

Not done here (later stages): collision families (R14, S1), per-leg and crawler floor
patches (R13, S1/S2b), body/link creation. Pass ``floor_plate=False`` to build the floor
collision shapes elsewhere; the floor body itself is always created here.

Units SI, world frame Z-up (R3). The floor top face lies at ``ground.crawler_bottom_z_m``.
This is the only module (with the rest of ``outrigger_sim.chrono``) that imports pychrono.
"""

from __future__ import annotations

import copy
import ctypes
import functools
import math
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import pychrono as ch

from outrigger_sim.params import LEG_ORDER, Params


class ChronoModel(StrEnum):
    """Contact / actuator model family (CLAUDE.md '구동기 운용안 B')."""

    L1 = "L1"
    """SMC normal contact + ground bushing (controller development)."""
    L2B_NSC = "L2b_NSC"
    """NSC complementarity contact (large slope, seal friction, SCM re-assessment)."""


class StepPurpose(StrEnum):
    """Which YAML time step to use (``00_docs/01_dynamics/dynamics_model.md`` 4.3)."""

    GENERAL = "general"
    """``simulation.<model>.dt_s``: controller development, sensitivity, ML data."""
    REFERENCE = "reference"
    """``simulation.dt_reference_s``: reference solutions (V9 convergence)."""
    TRANSITION = "transition"
    """``simulation.dt_transition_s``: contact transitions (lift-off, re-touch, D2 peaks)."""
    EXPLICIT = "explicit"
    """Time step given by the caller (recorded only; not a valid ``purpose`` argument)."""


class LinearSolver(StrEnum):
    """Direct solvers accepted for the L1 (SMC) model."""

    SPARSE_QR = "SPARSE_QR"
    SPARSE_LU = "SPARSE_LU"
    PARDISO_MKL = "PARDISO_MKL"


# R11: convention choices, not parameter values (the YAML has no key for them).
TIMESTEPPER_NAME = "EULER_IMPLICIT_LINEARIZED"
L1_DEFAULT_SOLVER = LinearSolver.SPARSE_LU
L1_DEFAULT_LOCK_SPARSITY_PATTERN = True
SMC_CONTACT_FORCE_MODEL = "Hooke"
SMC_TANGENTIAL_DISPLACEMENT_MODEL = "OneStep"
COLLISION_SYSTEM_NAME = "BULLET"

# Default floor plate: geometric convention, not a physical parameter. Large enough for the
# whole machine on a slope run (machine footprint about 6 m x 4 m); thick so that Bullet
# never tunnels. S1 replaces it by per-leg and crawler patches.
FLOOR_PLATE_HALF_SIZE_M: tuple[float, float, float] = (20.0, 20.0, 0.5)

# Leg whose L1 contact values the default floor plate carries. Front and rear legs differ
# by about 2 % in kn; SMC combines two materials, so S1 gives each leg its own patch with
# that leg's values (chrono_build_plan.md R13 / risk 1). One plate cannot match both.
DEFAULT_FLOOR_LEG = "FL"

_RIGID_FLOOR = "contact.rigid_floor"
_TIME_STEP_KEYS: dict[tuple[ChronoModel, StepPurpose], str] = {
    (ChronoModel.L1, StepPurpose.GENERAL): "simulation.L1.dt_s",
    (ChronoModel.L2B_NSC, StepPurpose.GENERAL): "simulation.L2b_NSC.dt_s",
    (ChronoModel.L1, StepPurpose.REFERENCE): "simulation.dt_reference_s",
    (ChronoModel.L2B_NSC, StepPurpose.REFERENCE): "simulation.dt_reference_s",
    (ChronoModel.L1, StepPurpose.TRANSITION): "simulation.dt_transition_s",
    (ChronoModel.L2B_NSC, StepPurpose.TRANSITION): "simulation.dt_transition_s",
}


@dataclass(frozen=True)
class ChronoSystemBundle:
    """Result of :func:`make_system`.

    Attributes:
        system: ``ChSystemSMC`` (L1) or ``ChSystemNSC`` (L2b_NSC).
        floor: Fixed floor body (R6), already added to ``system``.
        floor_material: Contact material of the default floor plate (also the template for
            bodies that touch it in tests); ``ChContactMaterialSMC`` or ``ChContactMaterialNSC``.
        model: Model family.
        dt_s: Time step to pass to ``DoStepDynamics`` [s].
        settings: Applied settings for the run metadata; use :meth:`meta` for a copy.
    """

    system: ch.ChSystem
    floor: ch.ChBody
    floor_material: ch.ChContactMaterial
    model: ChronoModel
    dt_s: float
    settings: Mapping[str, Any]

    def meta(self) -> dict[str, Any]:
        """Deep copy of :attr:`settings` (JSON-serialisable) for ``meta.json``."""
        return copy.deepcopy(dict(self.settings))


# --- small helpers -----------------------------------------------------------------------


def _as_model(model: ChronoModel | str) -> ChronoModel:
    try:
        return ChronoModel(model)
    except ValueError:
        valid = [member.value for member in ChronoModel]
        raise ValueError(f"unknown Chrono model {model!r}, expected one of {valid}") from None


def _positive_finite(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name}: expected a positive number, got {value!r}")
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{name}: expected a positive finite number, got {value!r}")
    return number


def gravity_vector(params: Params) -> tuple[float, float, float]:
    """World gravity ``(0, 0, -meta.gravity_m_s2)`` [m/s^2] (Z-up, R1/R3)."""
    return (0.0, 0.0, -params.meta.gravity_m_s2)


def set_gravity(system: ch.ChSystem, vector: Sequence[float]) -> None:
    """Set the world gravity vector [m/s^2]; the only place that calls the Chrono setter.

    Use it for the gravity ramp of V12 as well (chrono_build_plan.md R1).
    """
    gx, gy, gz = (float(component) for component in vector)
    if not all(math.isfinite(component) for component in (gx, gy, gz)):
        raise ValueError(f"gravity: expected a finite 3-vector, got {vector!r}")
    system.SetGravitationalAcceleration(ch.ChVector3d(gx, gy, gz))


def get_gravity(system: ch.ChSystem) -> tuple[float, float, float]:
    """Copy of the system gravity vector [m/s^2] (no Chrono reference kept, R9)."""
    g = system.GetGravitationalAcceleration()
    return (float(g.x), float(g.y), float(g.z))


def select_time_step(
    params: Params,
    model: ChronoModel | str = ChronoModel.L1,
    *,
    purpose: StepPurpose | str = StepPurpose.GENERAL,
    dt: float | None = None,
) -> tuple[float, StepPurpose, str]:
    """Return ``(dt_s, purpose, source)``; values come from the YAML only.

    Args:
        params: Loaded parameters.
        model: ``"L1"`` or ``"L2b_NSC"``.
        purpose: ``"general"``, ``"reference"`` or ``"transition"``.
        dt: Explicit time step [s]; then ``purpose`` must stay ``"general"``.

    Raises:
        ValueError: Unknown model or purpose, non-positive ``dt``, or ``dt`` together with a
            non-default ``purpose`` (ambiguous request).
    """
    chrono_model = _as_model(model)
    try:
        step_purpose = StepPurpose(purpose)
    except ValueError:
        valid = [p.value for p in StepPurpose if p is not StepPurpose.EXPLICIT]
        raise ValueError(f"unknown purpose {purpose!r}, expected one of {valid}") from None
    if step_purpose is StepPurpose.EXPLICIT:
        raise ValueError("purpose 'explicit' is set by passing dt, not by name")
    if dt is not None:
        if step_purpose is not StepPurpose.GENERAL:
            raise ValueError(
                f"give either dt or purpose, not both (purpose={step_purpose.value!r})"
            )
        return _positive_finite(dt, "dt"), StepPurpose.EXPLICIT, "argument dt"
    key = _TIME_STEP_KEYS[(chrono_model, step_purpose)]
    return _positive_finite(params.get(key), key), step_purpose, key


# --- materials ---------------------------------------------------------------------------


def make_smc_material(kn_N_m: float, gn_1_s: float) -> ch.ChContactMaterialSMC:
    """SMC material for the L1 model: normal only, ``kt = gt = mu = 0`` (R8), ``e = 0``.

    Args:
        kn_N_m: Hooke normal stiffness [N/m].
        gn_1_s: Hooke normal damping per unit effective mass [1/s] (R5).
    """
    material = ch.ChContactMaterialSMC()
    material.SetKn(_positive_finite(kn_N_m, "kn_N_m"))
    material.SetGn(float(gn_1_s))
    material.SetKt(0.0)
    material.SetGt(0.0)
    material.SetFriction(0.0)
    material.SetRestitution(0.0)
    return material


def make_nsc_material(friction: float) -> ch.ChContactMaterialNSC:
    """NSC material for the L2b-NSC model: Coulomb ``mu``, restitution 0."""
    material = ch.ChContactMaterialNSC()
    material.SetFriction(float(friction))
    material.SetRestitution(0.0)
    return material


def floor_material_values(
    params: Params, model: ChronoModel | str, leg: str = DEFAULT_FLOOR_LEG
) -> dict[str, Any]:
    """Material values of the floor for ``model`` (L1: values of ``leg``) with YAML sources."""
    chrono_model = _as_model(model)
    if chrono_model is ChronoModel.L1:
        if leg not in LEG_ORDER:
            raise ValueError(f"unknown leg {leg!r}, expected one of {LEG_ORDER}")
        index = LEG_ORDER.index(leg)
        l1 = params.contact.rigid_floor.L1
        return {
            "type": "SMC",
            "leg": leg,
            "kn_N_m": l1.kn_per_pad_N_m[index],
            "gn_1_s": l1.gn_per_pad_1_s[index],
            "kt_N_m": 0.0,
            "gt_1_s": 0.0,
            "friction": 0.0,
            "restitution": 0.0,
            "source": (
                f"{_RIGID_FLOOR}.L1.kn_per_pad_N_m.{leg}, .gn_per_pad_1_s.{leg}; kt=gt=mu=0 (R8)"
            ),
        }
    key = f"{_RIGID_FLOOR}.L2b_NSC.friction"
    return {
        "type": "NSC",
        "friction": float(params.get(key)),
        "restitution": 0.0,
        "source": key,
    }


def _material_from_values(values: Mapping[str, Any]) -> ch.ChContactMaterial:
    if values["type"] == "SMC":
        return make_smc_material(values["kn_N_m"], values["gn_1_s"])
    return make_nsc_material(values["friction"])


# --- system setup ------------------------------------------------------------------------


def _configure_smc(system: ch.ChSystemSMC) -> dict[str, Any]:
    system.UseMaterialProperties(False)
    system.SetContactForceModel(getattr(ch.ChSystemSMC, SMC_CONTACT_FORCE_MODEL))
    system.SetTangentialDisplacementModel(
        getattr(ch.ChSystemSMC, SMC_TANGENTIAL_DISPLACEMENT_MODEL)
    )
    return {
        "contact_force_model": SMC_CONTACT_FORCE_MODEL,
        "use_material_properties": bool(system.UsingMaterialProperties()),
        "tangential_displacement_model": SMC_TANGENTIAL_DISPLACEMENT_MODEL,
        "slip_velocity_threshold_m_s": float(system.GetSlipVelocityThreshold()),
        "contact_stiff": bool(system.IsContactStiff()),
        "source": "04_scripts/02_chrono/test_stick_friction.py (bushing cases); R5, R8",
    }


OPENMP_RUNTIME_PATH = Path(sys.prefix) / "Library" / "bin" / "libomp.dll"
"""Target of the llvm-openmp forwarder ``libiomp5md.dll`` (conda env layout on Windows)."""

_openmp_handles: list[Any] = []  # keeps the preloaded DLL referenced for the process lifetime


def preload_openmp_runtime() -> str | None:
    """Load :data:`OPENMP_RUNTIME_PATH` by absolute path once; return the path (None off Windows).

    Must run before the first Pardiso solve (see the module docstring). Does not touch PATH.

    Raises:
        RuntimeError: The DLL is missing or cannot be loaded.
    """
    if sys.platform != "win32":
        return None
    path = str(OPENMP_RUNTIME_PATH)
    if not _openmp_handles:
        if not OPENMP_RUNTIME_PATH.is_file():
            raise RuntimeError(
                f"PARDISO_MKL needs {path} (llvm-openmp; libiomp5md.dll forwards to it): not found"
            )
        try:
            _openmp_handles.append(ctypes.WinDLL(path))
        except OSError as error:
            raise RuntimeError(f"PARDISO_MKL: cannot load {path}: {error}") from error
    return path


def _pardiso_probe_code() -> str:
    preload = (
        f"import ctypes; ctypes.WinDLL({str(OPENMP_RUNTIME_PATH)!r})\n"
        if sys.platform == "win32"
        else ""
    )
    return preload + (
        "import pychrono as ch, pychrono.pardisomkl as pm\n"
        "s = ch.ChSystemSMC()\n"
        "s.SetGravitationalAcceleration(ch.ChVector3d(0, 0, -1))\n"
        "b = ch.ChBody(); b.SetMass(1.0); s.Add(b)\n"
        "p = pm.ChSolverPardisoMKL(); s.SetSolver(p)\n"
        "s.DoStepDynamics(1e-3)\n"
        "print('ok')\n"
    )


@functools.cache
def pardiso_mkl_status() -> tuple[bool, str]:
    """Return ``(usable, detail)`` for the Pardiso MKL solver, probed in a child process.

    The child process does what :func:`make_system` does (preload ``libomp.dll``, import
    ``pychrono.pardisomkl``, one solve). A child is needed because a broken OpenMP/MKL link
    does not raise: the first solve kills the process (0xC06D007F when the forwarder target
    ``libomp.dll`` cannot be found, see the module docstring). The result is cached.
    """
    try:
        done = subprocess.run(
            [sys.executable, "-I", "-c", _pardiso_probe_code()],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, f"probe failed: {error!r}"
    if done.returncode == 0 and done.stdout.strip().endswith("ok"):
        return True, "one solve passed"
    code = done.returncode & 0xFFFFFFFF
    tail = (done.stderr or "").strip().splitlines()[-1:] or [""]
    return False, f"probe exit code 0x{code:08X} {tail[0]}".strip()


def _direct_solver(system: ch.ChSystem) -> Any | None:
    """The system's ``ChDirectSolverLS`` or None (iterative solver, e.g. PSOR)."""
    solver = system.GetSolver()
    return None if solver is None else solver.AsDirect()


def force_sparsity_pattern_update(system: ch.ChSystem) -> bool:
    """Ask the direct solver to rebuild its sparsity pattern on the next Setup call.

    Use after a structural change the system does not detect by itself while the pattern is
    locked (a load added to a ``ChLoadContainer`` that is already in the system, a body
    fixed or released, ...). Items added or removed through the system (``Add``,
    ``Remove*``) need no call: Chrono re-analyses then (module docstring). The call is
    harmless and cheap otherwise (one pattern-learner pass on the next step).

    Returns:
        True if the request was passed to a direct solver; False for an iterative solver
        (NSC PSOR), where there is no pattern to update.
    """
    direct = _direct_solver(system)
    if direct is None:
        return False
    direct.ForceSparsityPatternUpdate()
    return True


def _configure_l1_solver(
    system: ch.ChSystem, solver: LinearSolver, lock_sparsity_pattern: bool
) -> dict[str, Any]:
    preloaded: str | None = None
    if solver is LinearSolver.PARDISO_MKL:
        usable, detail = pardiso_mkl_status()
        if not usable:
            raise RuntimeError(f"PARDISO_MKL is not usable in this environment: {detail}")
        preloaded = preload_openmp_runtime()  # before the module import and the first solve
        import pychrono.pardisomkl as pardisomkl  # optional module, only when requested

        pardiso = pardisomkl.ChSolverPardisoMKL()
        system.SetSolver(pardiso)
        # SetSolver takes a shared pointer; keep the Python object alive with the system.
        system._outrigger_pardiso_solver = pardiso  # type: ignore[attr-defined]
    else:
        system.SetSolverType(getattr(ch.ChSolver, f"Type_{solver.value}"))
    direct = _direct_solver(system)
    if direct is None:  # cannot happen for the three LinearSolver members
        raise RuntimeError(f"{solver.value}: Chrono did not create a direct solver")
    direct.LockSparsityPattern(lock_sparsity_pattern)
    return {
        "type": solver.value,
        "lock_sparsity_pattern": lock_sparsity_pattern,
        "openmp_preload": preloaded,
        "source": "R11 convention (no YAML key); user decision 2026-10-20 "
        "(06_analysis/01_chrono/01_cost/solver_benchmark.json)",
    }


def _configure_nsc_solver(system: ch.ChSystem, params: Params) -> dict[str, Any]:
    name_key = f"{_RIGID_FLOOR}.L2b_NSC.solver"
    iterations_key = f"{_RIGID_FLOOR}.L2b_NSC.solver_max_iterations"
    name = str(params.get(name_key))
    iterations = int(params.get(iterations_key))
    solver_type = getattr(ch.ChSolver, f"Type_{name}", None)
    if solver_type is None:
        raise ValueError(f"{name_key}: unknown Chrono solver {name!r}")
    if iterations <= 0:
        raise ValueError(f"{iterations_key}: expected a positive count, got {iterations}")
    system.SetSolverType(solver_type)
    iterative = system.GetSolver().AsIterative()
    if iterative is None:
        raise ValueError(f"{name_key}: solver {name!r} is not iterative")
    iterative.SetMaxIterations(iterations)
    return {
        "type": name,
        "max_iterations": iterations,
        "source": f"{name_key}, {iterations_key}",
    }


def _add_floor(
    system: ch.ChSystem,
    params: Params,
    material: ch.ChContactMaterial,
    floor_plate: bool,
) -> tuple[ch.ChBody, dict[str, Any]]:
    mass = _positive_finite(
        params.contact.rigid_floor.ground_body_mass_kg, f"{_RIGID_FLOOR}.ground_body_mass_kg"
    )
    top_z = params.ground.crawler_bottom_z_m
    floor = ch.ChBody()
    floor.SetName("floor")
    floor.SetMass(mass)
    floor.SetFixed(True)
    info: dict[str, Any] = {
        "mass_kg": mass,
        "mass_source": f"{_RIGID_FLOOR}.ground_body_mass_kg",
        "fixed": True,
        "top_z_m": top_z,
        "top_z_source": "ground.crawler_bottom_z_m",
        "plate": None,
    }
    if floor_plate:
        hx, hy, hz = FLOOR_PLATE_HALF_SIZE_M
        floor.EnableCollision(True)
        shape = ch.ChCollisionShapeBox(material, 2.0 * hx, 2.0 * hy, 2.0 * hz)
        floor.AddCollisionShape(shape, ch.ChFramed(ch.ChVector3d(0.0, 0.0, top_z - hz), ch.QUNIT))
        info["plate"] = {"half_size_m": [hx, hy, hz], "centre_m": [0.0, 0.0, top_z - hz]}
    system.Add(floor)
    return floor, info


def make_system(
    params: Params,
    model: ChronoModel | str = ChronoModel.L1,
    *,
    purpose: StepPurpose | str = StepPurpose.GENERAL,
    dt: float | None = None,
    solver: LinearSolver | str | None = None,
    lock_sparsity_pattern: bool | None = None,
    floor_plate: bool = True,
    floor_leg: str = DEFAULT_FLOOR_LEG,
) -> ChronoSystemBundle:
    """Create a Chrono system with the R1, R2, R6 and R11 conventions applied.

    Args:
        params: Parameters from :func:`outrigger_sim.params.load_params`.
        model: ``"L1"`` -> ``ChSystemSMC``; ``"L2b_NSC"`` -> ``ChSystemNSC``.
        purpose: Time-step choice, see :func:`select_time_step`.
        dt: Explicit time step [s] (overrides the YAML choice; ``purpose`` must stay default).
        solver: L1 only: ``"SPARSE_LU"`` (default), ``"SPARSE_QR"`` or ``"PARDISO_MKL"``
            (preloads ``libomp.dll``, see :func:`preload_openmp_runtime`). L2b_NSC takes the
            solver from ``contact.rigid_floor.L2b_NSC`` and rejects this argument.
        lock_sparsity_pattern: L1 only: lock the direct solver's sparsity pattern
            (default ``True``, applied to every direct solver). Items added or removed through
            the system are re-analysed by Chrono; after changes it does not see, call
            :func:`force_sparsity_pattern_update` (module docstring). L2b_NSC (iterative PSOR)
            rejects this argument.
        floor_plate: Add the default floor plate (top face at ``ground.crawler_bottom_z_m``).
            ``False`` leaves the fixed floor body without collision shapes for S1 patches.
        floor_leg: L1 only: leg whose contact values the default plate carries.

    Returns:
        :class:`ChronoSystemBundle`; step with ``bundle.system.DoStepDynamics(bundle.dt_s)``.

    Raises:
        ValueError: Unknown model, purpose, solver or leg; bad ``dt``; ``solver`` or
            ``lock_sparsity_pattern`` for NSC.
        RuntimeError: ``PARDISO_MKL`` requested but not usable (see :func:`pardiso_mkl_status`).
    """
    chrono_model = _as_model(model)
    dt_s, step_purpose, dt_source = select_time_step(params, chrono_model, purpose=purpose, dt=dt)

    if chrono_model is ChronoModel.L1:
        linear_solver = L1_DEFAULT_SOLVER if solver is None else LinearSolver(solver)
        lock = (
            L1_DEFAULT_LOCK_SPARSITY_PATTERN
            if lock_sparsity_pattern is None
            else bool(lock_sparsity_pattern)
        )
        system: ch.ChSystem = ch.ChSystemSMC()
        contact_settings = _configure_smc(system)
    else:
        if solver is not None:
            raise ValueError("solver is set from contact.rigid_floor.L2b_NSC for the NSC model")
        if lock_sparsity_pattern is not None:
            raise ValueError("lock_sparsity_pattern applies to the L1 direct solvers only")
        system = ch.ChSystemNSC()
        contact_settings = {"source": "NSC complementarity contact, R11"}

    # R2
    system.SetCollisionSystemType(getattr(ch.ChCollisionSystem, f"Type_{COLLISION_SYSTEM_NAME}"))
    # R1
    gravity = gravity_vector(params)
    set_gravity(system, gravity)
    # R11
    system.SetTimestepperType(getattr(ch.ChTimestepper, f"Type_{TIMESTEPPER_NAME}"))
    if chrono_model is ChronoModel.L1:
        solver_settings = _configure_l1_solver(system, linear_solver, lock)
    else:
        solver_settings = _configure_nsc_solver(system, params)

    # R6
    material_values = floor_material_values(params, chrono_model, floor_leg)
    floor_material = _material_from_values(material_values)
    floor, floor_info = _add_floor(system, params, floor_material, floor_plate)
    if floor_plate:
        floor_info["material"] = material_values

    settings: dict[str, Any] = {
        "engine": "pychrono",
        "model": chrono_model.value,
        "system_class": type(system).__name__,
        "dt_s": dt_s,
        "dt_purpose": step_purpose.value,
        "dt_source": dt_source,
        "gravity_m_s2": list(gravity),
        "gravity_source": "meta.gravity_m_s2 (vector (0, 0, -g), R1)",
        "collision_system": COLLISION_SYSTEM_NAME,
        "timestepper": TIMESTEPPER_NAME,
        "solver": solver_settings,
        "contact": contact_settings,
        "floor": floor_info,
        "params_sha256": params.sha256,
    }
    return ChronoSystemBundle(
        system=system,
        floor=floor,
        floor_material=floor_material,
        model=chrono_model,
        dt_s=dt_s,
        settings=settings,
    )
