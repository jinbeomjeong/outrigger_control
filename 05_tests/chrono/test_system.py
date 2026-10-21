"""V0 convention checks of ``chrono/system.make_system`` (chrono_build_plan.md R1, R2, R6, R11).

Also: time-step selection from the YAML, invalid arguments, the engine boundary (pychrono only
under ``outrigger_sim/chrono``), a short drop smoke test on both contact models, the same drop
with every L1 solver / sparsity-lock combination against the former default (SPARSE_QR,
unlocked), and structural changes during a run with the sparsity pattern locked.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("pychrono")

import pychrono as ch  # noqa: E402

from outrigger_sim.chrono.system import (  # noqa: E402
    L1_DEFAULT_LOCK_SPARSITY_PATTERN,
    L1_DEFAULT_SOLVER,
    OPENMP_RUNTIME_PATH,
    ChronoModel,
    ChronoSystemBundle,
    LinearSolver,
    StepPurpose,
    force_sparsity_pattern_update,
    get_gravity,
    make_system,
    pardiso_mkl_status,
    select_time_step,
    set_gravity,
)
from outrigger_sim.params import Params, load_params  # noqa: E402

pytestmark = pytest.mark.chrono

MODELS = ("L1", "L2b_NSC")

# Drop smoke test (assumed test object, not machine data): a 0.3 m steel-sized cube with the
# FL moving-part mass so the floor material's gn (per moving-part mass) gives its design
# damping; dropped flat from 20 mm above the floor, run 0.5 s.
CUBE_EDGE_M = 0.3
DROP_HEIGHT_M = 0.02
DROP_TIME_S = 0.5
AVERAGE_WINDOW_S = 0.1
# Limits. Peak penetration: undamped bound v0 / omega with 4 contacts is 0.71 mm (SMC); 1 mm
# means "did not tunnel". Rest: SMC static penetration is m g / (4 kn) = 12.6 um; NSC is rigid.
MAX_PENETRATION_M = 1.0e-3
REST_PENETRATION_MAX_M = 1.0e-4
WEIGHT_BALANCE_REL_TOL = 0.01  # simulate-mode static equilibrium criterion (<= 1 %)
SMC_REST_SPEED_MAX_M_S = 1.0e-4
# NSC with penetration recovery alternates the contact impulse step by step; the vertical
# speed then jitters by about g dt while the position stays within 0.1 um.
NSC_JITTER_SPEED_FACTOR = 2.0
NSC_REST_DRIFT_MAX_M = 1.0e-6
# L1 solvers against the former default SPARSE_QR (unlocked) on the drop test (measured:
# bit-identical, 2026-10-20).
SOLVER_GAP_ABS_TOL_M = 1.0e-12
SOLVER_FORCE_REL_TOL = 1.0e-9
SOURCE_R11 = (
    "R11 convention (no YAML key); user decision 2026-10-20 "
    "(06_analysis/01_chrono/01_cost/solver_benchmark.json)"
)
# Structural-change test (assumed test objects): two cubes on the floor, a change at
# STRUCT_ADD_STEP undone at STRUCT_REMOVE_STEP. Locked vs unlocked SPARSE_LU was bit-identical
# in the scratchpad probe (2026-10-20); 1e-12 m leaves room for summation-order noise only.
STRUCT_STEPS = 1500
STRUCT_ADD_STEP = 500
STRUCT_REMOVE_STEP = 1000
STRUCT_BUSHING_K_N_M = 1.0e6
STRUCT_BUSHING_C_N_S_M = 1.0e3
STRUCT_GAP_ABS_TOL_M = 1.0e-12
STRUCT_MIN_EFFECT_M = 1.0e-5  # the change must move the bodies, or the comparison is vacuous


@pytest.fixture(scope="module")
def params(params_path: Path) -> Params:
    return load_params(params_path)


@pytest.fixture(scope="module", params=MODELS)
def bundle(request: pytest.FixtureRequest, params: Params) -> ChronoSystemBundle:
    return make_system(params, request.param)


# --- R1 gravity --------------------------------------------------------------------------


def test_r1_gravity_is_yaml_vector_and_not_zero(bundle: ChronoSystemBundle, params: Params) -> None:
    g = get_gravity(bundle.system)
    assert g == (0.0, 0.0, -params.meta.gravity_m_s2)
    assert params.meta.gravity_m_s2 == pytest.approx(9.80665, rel=0, abs=0)
    assert math.hypot(*g) > 0.0
    assert bundle.settings["gravity_m_s2"] == list(g)


def test_r1_chrono_default_gravity_is_zero() -> None:
    """The trap R1 guards against (pychrono 10.0.0 starts with a zero vector)."""
    g = ch.ChSystemSMC().GetGravitationalAcceleration()
    assert (g.x, g.y, g.z) == (0.0, 0.0, 0.0)


def test_set_gravity_changes_vector(params: Params) -> None:
    system = make_system(params, "L1").system
    set_gravity(system, (0.1, -0.2, -4.9))
    assert get_gravity(system) == (0.1, -0.2, -4.9)
    with pytest.raises(ValueError):
        set_gravity(system, (0.0, 0.0, math.nan))


# --- R2 collision system -----------------------------------------------------------------


def test_r2_collision_system_is_bullet(bundle: ChronoSystemBundle) -> None:
    collision_system = bundle.system.GetCollisionSystem()
    assert collision_system is not None
    assert collision_system.GetType() == ch.ChCollisionSystem.Type_BULLET
    assert bundle.settings["collision_system"] == "BULLET"


# --- R6 floor ----------------------------------------------------------------------------


def test_r6_floor_mass_and_fixed(bundle: ChronoSystemBundle, params: Params) -> None:
    floor = bundle.floor
    assert floor.GetMass() == params.contact.rigid_floor.ground_body_mass_kg == 1.0e9
    assert floor.IsFixed()
    assert floor.IsCollisionEnabled()
    assert bundle.settings["floor"]["top_z_m"] == params.ground.crawler_bottom_z_m
    assert any(body.GetName() == "floor" for body in bundle.system.GetBodies())


def test_r6_floor_without_plate_has_no_collision(params: Params) -> None:
    bundle = make_system(params, "L1", floor_plate=False)
    assert bundle.floor.IsFixed()
    assert bundle.floor.GetMass() == 1.0e9
    assert not bundle.floor.IsCollisionEnabled()
    assert bundle.settings["floor"]["plate"] is None


def test_floor_material_l1_is_normal_only(params: Params) -> None:
    material = make_system(params, "L1").floor_material
    l1 = params.contact.rigid_floor.L1
    assert isinstance(material, ch.ChContactMaterialSMC)
    # Chrono stores SMC coefficients as float32.
    assert material.GetKn() == pytest.approx(l1.kn_per_pad_N_m[0], rel=1e-7)
    assert material.GetGn() == pytest.approx(l1.gn_per_pad_1_s[0], rel=1e-7)
    assert (material.GetKt(), material.GetGt(), material.GetStaticFriction()) == (0.0, 0.0, 0.0)
    assert material.GetSlidingFriction() == 0.0


def test_floor_material_nsc_friction(params: Params) -> None:
    material = make_system(params, "L2b_NSC").floor_material
    assert isinstance(material, ch.ChContactMaterialNSC)
    friction = params.get("contact.rigid_floor.L2b_NSC.friction")
    assert material.GetStaticFriction() == pytest.approx(friction, rel=1e-7)
    assert material.GetSlidingFriction() == pytest.approx(friction, rel=1e-7)


# --- R11 integrator and solver -----------------------------------------------------------


def test_r11_timestepper(bundle: ChronoSystemBundle) -> None:
    expected = ch.ChTimestepper.Type_EULER_IMPLICIT_LINEARIZED
    assert bundle.system.GetTimestepperType() == expected
    assert bundle.settings["timestepper"] == "EULER_IMPLICIT_LINEARIZED"


def test_r11_l1_smc_sparse_lu_locked_by_default(params: Params) -> None:
    assert L1_DEFAULT_SOLVER is LinearSolver.SPARSE_LU
    assert L1_DEFAULT_LOCK_SPARSITY_PATTERN is True
    bundle = make_system(params, "L1")
    system = bundle.system
    assert isinstance(system, ch.ChSystemSMC)
    assert system.GetSolverType() == ch.ChSolver.Type_SPARSE_LU
    assert system.GetSolver().AsDirect() is not None
    assert system.GetContactForceModel() == ch.ChSystemSMC.Hooke
    assert not system.UsingMaterialProperties()
    assert system.GetTangentialDisplacementModel() == ch.ChSystemSMC.OneStep
    assert bundle.settings["solver"] == {
        "type": "SPARSE_LU",
        "lock_sparsity_pattern": True,
        "openmp_preload": None,
        "source": SOURCE_R11,
    }
    assert bundle.meta()["solver"]["lock_sparsity_pattern"] is True


def _setup_assembly_time_s(bundle: ChronoSystemBundle, steps: int) -> float:
    """Cumulative matrix-assembly time of the direct solver over ``steps`` steps [s]."""
    direct = bundle.system.GetSolver().AsDirect()
    direct.ResetTimers()
    for _ in range(steps):
        bundle.system.DoStepDynamics(bundle.dt_s)
    return float(direct.GetTimeSetup_Assembly())


def test_r11_lock_reaches_the_chrono_solver(params: Params) -> None:
    """Chrono has no getter for the lock; its effect (no pattern learner per step) is timed.

    Measured on the drop model: assembly about 7x faster when locked (2026-10-20); the bound
    0.6 leaves a wide margin for timer noise. One warm-up step removes the first-call cost.
    """
    times = {}
    for lock in (True, False):
        bundle = make_system(params, "L1", lock_sparsity_pattern=lock)
        _add_cube(bundle, params, x=0.0)
        bundle.system.DoStepDynamics(bundle.dt_s)
        times[lock] = _setup_assembly_time_s(bundle, 2000)
    assert times[True] < 0.6 * times[False], times


def test_r11_nsc_psor_iterations(params: Params) -> None:
    bundle = make_system(params, "L2b_NSC")
    system = bundle.system
    assert isinstance(system, ch.ChSystemNSC)
    assert system.GetSolverType() == ch.ChSolver.Type_PSOR
    iterations = system.GetSolver().AsIterative().GetMaxIterations()
    assert iterations == params.get("contact.rigid_floor.L2b_NSC.solver_max_iterations") == 50
    assert bundle.settings["solver"] == {
        "type": "PSOR",
        "max_iterations": 50,
        "source": "contact.rigid_floor.L2b_NSC.solver, "
        "contact.rigid_floor.L2b_NSC.solver_max_iterations",
    }


def test_pardiso_usable_with_openmp_preload(params: Params) -> None:
    """PARDISO_MKL works from a non-activated python.exe once libomp.dll is preloaded."""
    usable, detail = pardiso_mkl_status()
    assert usable, detail
    bundle = make_system(params, "L1", solver="PARDISO_MKL")
    assert bundle.system.GetSolverType() == ch.ChSolver.Type_PARDISO_MKL
    expected = str(OPENMP_RUNTIME_PATH) if sys.platform == "win32" else None
    assert bundle.settings["solver"]["openmp_preload"] == expected
    assert bundle.settings["solver"]["lock_sparsity_pattern"] is True


@pytest.mark.parametrize(
    ("solver", "lock", "chrono_type"),
    [
        ("SPARSE_QR", None, ch.ChSolver.Type_SPARSE_QR),
        ("SPARSE_QR", False, ch.ChSolver.Type_SPARSE_QR),
        ("SPARSE_LU", False, ch.ChSolver.Type_SPARSE_LU),
        (None, False, ch.ChSolver.Type_SPARSE_LU),
    ],
)
def test_l1_solver_options(
    params: Params, solver: str | None, lock: bool | None, chrono_type: int
) -> None:
    bundle = make_system(params, "L1", solver=solver, lock_sparsity_pattern=lock)
    assert bundle.system.GetSolverType() == chrono_type
    assert bundle.settings["solver"] == {
        "type": solver or "SPARSE_LU",
        "lock_sparsity_pattern": True if lock is None else lock,
        "openmp_preload": None,
        "source": SOURCE_R11,
    }


def test_force_sparsity_pattern_update_helper(params: Params) -> None:
    assert force_sparsity_pattern_update(make_system(params, "L1").system) is True
    assert force_sparsity_pattern_update(make_system(params, "L2b_NSC").system) is False


# --- time step ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("model", "purpose", "key"),
    [
        ("L1", "general", "simulation.L1.dt_s"),
        ("L2b_NSC", "general", "simulation.L2b_NSC.dt_s"),
        ("L1", "reference", "simulation.dt_reference_s"),
        ("L2b_NSC", "reference", "simulation.dt_reference_s"),
        ("L1", "transition", "simulation.dt_transition_s"),
        ("L2b_NSC", "transition", "simulation.dt_transition_s"),
    ],
)
def test_dt_from_yaml(params: Params, model: str, purpose: str, key: str) -> None:
    bundle = make_system(params, model, purpose=purpose)
    assert bundle.dt_s == params.get(key)
    assert bundle.settings["dt_source"] == key
    assert bundle.settings["dt_purpose"] == purpose


def test_dt_follows_overrides(params_path: Path) -> None:
    """dt is read from the parameters, not hard-coded."""
    changed = load_params(params_path, overrides={"simulation.L1.dt_s": 2.5e-4})
    assert make_system(changed, "L1").dt_s == 2.5e-4


def test_dt_explicit(params: Params) -> None:
    bundle = make_system(params, "L2b_NSC", dt=3.0e-5)
    assert bundle.dt_s == 3.0e-5
    assert bundle.settings["dt_purpose"] == StepPurpose.EXPLICIT.value


@pytest.mark.parametrize(
    "kwargs",
    [
        {"dt": 0.0},
        {"dt": -1e-4},
        {"dt": math.inf},
        {"dt": 1e-4, "purpose": "reference"},
        {"purpose": "fast"},
        {"purpose": "explicit"},
    ],
)
def test_dt_invalid(params: Params, kwargs: dict) -> None:
    with pytest.raises(ValueError):
        select_time_step(params, "L1", **kwargs)


# --- invalid arguments -------------------------------------------------------------------


@pytest.mark.parametrize("model", ["L2", "l1", "SMC", ""])
def test_invalid_model(params: Params, model: str) -> None:
    with pytest.raises(ValueError, match="unknown Chrono model"):
        make_system(params, model)


def test_invalid_solver_arguments(params: Params) -> None:
    with pytest.raises(ValueError):
        make_system(params, "L1", solver="PSOR")
    with pytest.raises(ValueError):
        make_system(params, "L2b_NSC", solver="SPARSE_QR")
    with pytest.raises(ValueError, match="lock_sparsity_pattern"):
        make_system(params, "L2b_NSC", lock_sparsity_pattern=True)
    with pytest.raises(ValueError):
        make_system(params, "L1", floor_leg="XX")


def test_meta_is_independent_copy(params: Params) -> None:
    bundle = make_system(params, ChronoModel.L1)
    meta = bundle.meta()
    meta["floor"]["mass_kg"] = 0.0
    assert bundle.settings["floor"]["mass_kg"] == 1.0e9
    assert meta["params_sha256"] == params.sha256


# --- engine boundary ---------------------------------------------------------------------


def test_pychrono_imported_only_under_chrono_package(project_root: Path) -> None:
    package = project_root / "03_src" / "outrigger_sim"
    pattern = re.compile(r"^\s*(import|from)\s+pychrono\b", re.MULTILINE)
    offenders = [
        path.relative_to(package).as_posix()
        for path in package.rglob("*.py")
        if "chrono" not in path.relative_to(package).parts[:1]
        and pattern.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


# --- drop smoke test ---------------------------------------------------------------------


def _add_cube(
    bundle: ChronoSystemBundle, params: Params, *, x: float, y: float = -0.2
) -> ch.ChBody:
    """Add the test cube (FL moving-part mass) DROP_HEIGHT_M above the floor at (x, y)."""
    mass = params.legs[0].moving_part.mass_kg
    half = CUBE_EDGE_M / 2.0
    floor_z = params.ground.crawler_bottom_z_m
    box = ch.ChBody()
    box.SetMass(mass)
    box.SetInertiaXX(ch.ChVector3d(1.0, 1.0, 1.0) * (mass * CUBE_EDGE_M**2 / 6.0))
    box.SetPos(ch.ChVector3d(x, y, floor_z + half + DROP_HEIGHT_M))
    box.EnableCollision(True)
    shape = ch.ChCollisionShapeBox(bundle.floor_material, CUBE_EDGE_M, CUBE_EDGE_M, CUBE_EDGE_M)
    box.AddCollisionShape(shape, ch.ChFramed())
    bundle.system.Add(box)
    return box


def _run_drop(
    bundle: ChronoSystemBundle, params: Params
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Drop the test cube; return (gap per step, contact Fz and vz in the last window)."""
    system = bundle.system
    half = CUBE_EDGE_M / 2.0
    floor_z = params.ground.crawler_bottom_z_m
    box = _add_cube(bundle, params, x=0.1)

    n_steps = round(DROP_TIME_S / bundle.dt_s)
    n_window = round(AVERAGE_WINDOW_S / bundle.dt_s)
    gaps = np.empty(n_steps)
    force_z = np.empty(n_window)
    speed_z = np.empty(n_window)
    for k in range(n_steps):
        system.DoStepDynamics(bundle.dt_s)
        gaps[k] = float(box.GetPos().z) - half - floor_z  # copied as float (R9)
        if k >= n_steps - n_window:
            force_z[k - (n_steps - n_window)] = float(box.GetContactForce().z)
            speed_z[k - (n_steps - n_window)] = float(box.GetPosDt().z)
    return gaps, force_z, speed_z


@pytest.fixture(scope="module")
def drop_sparse_qr(params: Params) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Reference: the former L1 default (SPARSE_QR, pattern not locked)."""
    bundle = make_system(params, "L1", solver="SPARSE_QR", lock_sparsity_pattern=False)
    return _run_drop(bundle, params)


@pytest.mark.parametrize("model", MODELS)
def test_drop_box_comes_to_rest_on_floor(params: Params, model: str) -> None:
    bundle = make_system(params, model)  # fresh system: the shared fixture stays body-free
    gaps, force_z, speed_z = _run_drop(bundle, params)
    weight = params.legs[0].moving_part.mass_kg * params.meta.gravity_m_s2
    n_window = len(force_z)

    assert -gaps.min() <= MAX_PENETRATION_M
    rest = gaps[-n_window:]
    assert -rest.min() <= REST_PENETRATION_MAX_M
    assert force_z.mean() == pytest.approx(weight, rel=WEIGHT_BALANCE_REL_TOL)
    if bundle.model is ChronoModel.L1:
        assert rest.max() < 0.0  # compliant contact: resting in (small) penetration
        assert np.abs(speed_z).max() <= SMC_REST_SPEED_MAX_M_S
    else:
        jitter = NSC_JITTER_SPEED_FACTOR * params.meta.gravity_m_s2 * bundle.dt_s
        assert np.abs(speed_z).max() <= jitter
        assert rest.max() - rest.min() <= NSC_REST_DRIFT_MAX_M


@pytest.mark.parametrize(
    ("solver", "lock"),
    [
        (None, None),  # default: SPARSE_LU, locked
        ("SPARSE_LU", False),
        ("SPARSE_QR", True),
        ("PARDISO_MKL", None),
        ("PARDISO_MKL", False),
    ],
)
def test_drop_solver_matches_former_sparse_qr(
    params: Params,
    solver: str | None,
    lock: bool | None,
    drop_sparse_qr: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> None:
    gaps_qr, force_qr, _speed_qr = drop_sparse_qr
    bundle = make_system(params, "L1", solver=solver, lock_sparsity_pattern=lock)
    gaps, force_z, _speed = _run_drop(bundle, params)
    assert np.max(np.abs(gaps - gaps_qr)) <= SOLVER_GAP_ABS_TOL_M
    assert gaps[-1] == pytest.approx(gaps_qr[-1], rel=0, abs=SOLVER_GAP_ABS_TOL_M)
    assert force_z.mean() == pytest.approx(force_qr.mean(), rel=SOLVER_FORCE_REL_TOL)


# --- structural change with a locked sparsity pattern ------------------------------------


def _run_structural_change(
    params: Params, event: str | None, *, lock: bool, refresh: bool = False
) -> np.ndarray:
    """Two cubes; at STRUCT_ADD_STEP add an item between them, remove it at STRUCT_REMOVE_STEP.

    Events: ``"link"`` (``ChLinkLockLock``, KKT grows by 6 rows), ``"bushing"``
    (``ChLoadBodyBodyBushingSpherical`` in its own load container added through the system,
    the R15 pattern: new off-diagonal stiffness blocks), ``"bushing_silent"`` (the bushing
    added to a container already in the system, a change ``ChSystem`` does not detect;
    removal through the system). ``refresh`` calls :func:`force_sparsity_pattern_update`
    after each change. Returns the positions of both cubes per step, shape (steps, 6) [m].
    """
    bundle = make_system(params, "L1", lock_sparsity_pattern=lock)
    system = bundle.system
    cube_a = _add_cube(bundle, params, x=0.0)
    cube_b = _add_cube(bundle, params, x=0.5)
    cube_a.SetPosDt(ch.ChVector3d(0.05, 0.0, 0.0))
    anchor = ch.ChFramed(ch.ChVector3d(0.25, -0.2, cube_a.GetPos().z), ch.QUNIT)
    standing = ch.ChLoadContainer()
    system.Add(standing)

    def bushing() -> ch.ChLoadBodyBodyBushingSpherical:
        k = ch.ChVector3d(1.0, 1.0, 1.0) * STRUCT_BUSHING_K_N_M
        c = ch.ChVector3d(1.0, 1.0, 1.0) * STRUCT_BUSHING_C_N_S_M
        return ch.ChLoadBodyBodyBushingSpherical(cube_a, cube_b, anchor, k, c)

    item: object = None
    positions = np.empty((STRUCT_STEPS, 6))
    for k in range(STRUCT_STEPS):
        if k == STRUCT_ADD_STEP and event is not None:
            if event == "link":
                item = ch.ChLinkLockLock()
                item.Initialize(cube_a, cube_b, anchor)
                system.Add(item)
            elif event == "bushing":
                item = ch.ChLoadContainer()
                item.Add(bushing())
                system.Add(item)
            else:  # bushing_silent
                standing.Add(bushing())
                item = standing
            if refresh:
                force_sparsity_pattern_update(system)
        if k == STRUCT_REMOVE_STEP and item is not None:
            if event == "link":
                system.RemoveLink(item)
            else:
                system.RemoveOtherPhysicsItem(item)
            if refresh:
                force_sparsity_pattern_update(system)
        system.DoStepDynamics(bundle.dt_s)
        pa, pb = cube_a.GetPos(), cube_b.GetPos()
        positions[k] = (pa.x, pa.y, pa.z, pb.x, pb.y, pb.z)  # copied as floats (R9)
    return positions


@pytest.fixture(scope="module")
def structural_baseline(params: Params) -> np.ndarray:
    return _run_structural_change(params, None, lock=True)


@pytest.mark.parametrize("event", ["link", "bushing", "bushing_silent"])
def test_locked_pattern_survives_structural_change(
    params: Params, event: str, structural_baseline: np.ndarray
) -> None:
    unlocked = _run_structural_change(params, event, lock=False)
    locked = _run_structural_change(params, event, lock=True)
    refreshed = _run_structural_change(params, event, lock=True, refresh=True)
    effect = np.abs(unlocked - structural_baseline)
    assert effect[:STRUCT_ADD_STEP].max() == 0.0
    assert effect.max() >= STRUCT_MIN_EFFECT_M  # the change does act on the cubes
    assert np.all(np.isfinite(locked))
    assert np.abs(locked - unlocked).max() <= STRUCT_GAP_ABS_TOL_M
    assert np.abs(refreshed - unlocked).max() <= STRUCT_GAP_ABS_TOL_M
