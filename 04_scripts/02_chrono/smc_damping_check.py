"""Chrono 10 SMC Hooke damping check (S0, chrono_build_plan.md R5, damping_survey.md).

Question: does the installed pychrono 10.0.0 apply the Hooke normal damping as
``c = m_eff * gn`` with ``m_eff = m1 m2 / (m1 + m2)`` (``UseMaterialProperties(False)``), how are
two SMC materials combined, and does the YAML ``contact.rigid_floor.L1.gn_per_pad_1_s`` give the
intended leg damping ratio 0.03 on the uncoupled heave mode
(``derivation.damping_reference_mode_Hz`` 7.39 Hz)?

Cases (all on ``outrigger_sim.chrono.system.make_system(params, "L1", dt=...)``):

* single contact: one sphere (radius = ``legs.FL.pad.swivel_center_above_pad_bottom_m``, mass =
  ``legs.FL.moving_part.mass_kg``) resting on the fixed floor, started at the static penetration
  ``m g / kn`` with a small vertical speed ``V0_SINGLE_M_S`` (amplitude << penetration, so the
  contact never opens and the force law stays linear). Variants: floor mass (1e9, 1e3, 1 kg),
  gn scale (1, 0.1, 0), sphere material different from the floor (composition rule), contact
  Jacobian on/off (``SetContactStiff``).
* heave: rigid superstructure (``superstructure.mass_properties``, top level) with the 4 leg
  moving parts welded at the pad positions, one contact sphere per pad on a per-leg floor patch
  carrying that leg's L1 material (R13). The superstructure centre of mass is moved horizontally
  so that the total centre of mass lies on the stiffness centroid of the 4 pads: vertical
  contact forces then give no moment, the heave mode is uncoupled and its expected values are
  exactly ``sqrt(sum kn / M)`` and ``sum(gn_i m_eff,i) / (2 sqrt(sum kn M))``. This is a test
  model (ASSUMPTION: CoM shift, no tangential contact or bushing), not the machine model; the
  machine's heave-dominated mode with bushings is reference.json mode 5 (7.61 Hz, zeta 0.0324).

Identification: the vertical velocity (no static offset) sampled every ``stride`` steps is fitted
by a 2nd-order linear recurrence (Prony); its roots ``z`` give the equivalent continuous
eigenvalue ``ln(z) / (stride dt)``. For a linear system this is exact to round-off.

Numerical damping (measured here, pychrono 10.0.0): ``EULER_IMPLICIT_LINEARIZED`` integrates
the SMC contact force explicitly, i.e. semi-implicit (symplectic) Euler
``v1 = v0 + dt F(x0, v0) / m``, ``x1 = x0 + dt v1``: with ``gn = 0`` the amplitude does not
decay (no ``omega dt / 2`` numerical damping, which a backward-Euler contact would give).
``SetContactStiff(True)`` (header: "enables calculation of contact force Jacobians") gave
bit-identical results with SPARSE_LU locked/unlocked and SPARSE_QR, so the explicit map is used
for every case. Both discrete maps are evaluated exactly (:func:`discrete_modal`, backward Euler
kept for comparison) and :func:`invert_discrete` recovers ``k`` and ``c`` from the measured
eigenvalue.

Contact noise (measured here): the penetration Bullet reports carries noise of about
3e-8 m per metre of contact height |z| (1.5e-8 m at z = 0, 3.4e-8 m at the floor top
z = -1.05 m, 3.3e-7 m at z = -10 m), i.e. single-precision level. With kn 2.1e7 N/m that is
about 0.7 N rms per contact at the floor top, negligible against the pad loads (about 95 kN) but
1.5 % of the force amplitude of a 2 um vibration; the single-contact cases therefore use a 23 um
amplitude.

Run (repository root, about 15 s):
      C:\\ProgramData\\miniforge3\\envs\\Chrono-dev\\python.exe -I
      04_scripts/02_chrono/smc_damping_check.py
Out:  06_analysis/01_chrono/smc_damping.json
Units SI, world Z-up, gravity set by make_system.
"""

from __future__ import annotations

import cmath
import json
import math
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "03_src") not in sys.path:
    sys.path.insert(0, str(ROOT / "03_src"))

import pychrono as ch  # noqa: E402

from outrigger_sim.chrono.system import make_smc_material, make_system  # noqa: E402
from outrigger_sim.params import LEG_ORDER, Params, load_params  # noqa: E402

PARAMS_PATH = ROOT / "02_params" / "rexome33.yaml"
OUT_JSON = ROOT / "06_analysis" / "01_chrono" / "smc_damping.json"

SYMPLECTIC = "symplectic_euler"
BACKWARD = "backward_euler"

V0_SINGLE_M_S = 1.0e-2  # amplitude v0/omega 23 um < static penetration 50 um (stays closed)
V0_HEAVE_M_S = 1.0e-3  # amplitude 22 um << static penetration 4.5 mm
SAMPLES_PER_PERIOD = 32
DECAY_STOP = 1.0e-2  # identification window ends when exp(-sigma t) reaches this (noise floor)
FLOOR_PATCH_HALF_M = 0.5  # per-leg floor patch half size (test geometry)


# --- linear oscillator: continuous and discrete -----------------------------------------


def continuous_modal(k: float, c: float, m: float) -> tuple[float, float]:
    """(omega_n [rad/s], zeta) of ``m x'' + c x' + k x = 0``."""
    omega = math.sqrt(k / m)
    return omega, c / (2.0 * math.sqrt(k * m))


def _step_matrix(k: float, c: float, m: float, h: float, scheme: str) -> np.ndarray:
    """One-step map of (x, v) for the given scheme."""
    if scheme == SYMPLECTIC:
        a = np.array([[0.0, 1.0], [-k / m, -c / m]])
        # v1 = v0 + h (a21 x0 + a22 v0); x1 = x0 + h v1
        v_row = np.array([h * a[1, 0], 1.0 + h * a[1, 1]])
        x_row = np.array([1.0, 0.0]) + h * v_row
        return np.vstack([x_row, v_row])
    if scheme == BACKWARD:
        d = m + h * c + h * h * k
        return np.array([[1.0 - h * h * k / d, h * m / d], [-h * k / d, m / d]])
    raise ValueError(f"unknown scheme {scheme!r}")


def discrete_modal(k: float, c: float, m: float, h: float, scheme: str) -> tuple[float, float]:
    """(omega_n, zeta) of the equivalent continuous eigenvalue ``ln(z) / h`` of the step map."""
    z = np.linalg.eigvals(_step_matrix(k, c, m, h, scheme))
    lam = complex(cmath.log(complex(z[np.argmax(np.imag(z))])) / h)
    return _modal_from_lambda(lam)


def _modal_from_lambda(lam: complex) -> tuple[float, float]:
    omega = abs(lam)
    return omega, -lam.real / omega


def invert_discrete(
    omega: float, zeta: float, m: float, h: float, scheme: str
) -> tuple[float, float]:
    """(k, c) whose step map has the equivalent eigenvalue (omega, zeta); exact inverse."""
    lam = complex(-zeta * omega, omega * math.sqrt(max(0.0, 1.0 - zeta * zeta)))
    z = cmath.exp(lam * h)
    trace = 2.0 * z.real
    det = abs(z) ** 2
    if scheme == SYMPLECTIC:
        c = m * (1.0 - det) / h
        k = m * (1.0 + det - trace) / (h * h)
        return k, c
    if scheme == BACKWARD:
        d = m / det
        c = (trace * d - 2.0 * m) / h
        k = (d - m - h * c) / (h * h)
        return k, c
    raise ValueError(f"unknown scheme {scheme!r}")


def identify_prony(signal: np.ndarray, h_sample: float) -> tuple[float, float, float]:
    """Fit ``y[n+2] = a1 y[n+1] + a0 y[n]``; return (omega_n, zeta, relative residual)."""
    y = np.asarray(signal, dtype=float)
    a = np.column_stack([y[1:-1], y[:-2]])
    b = y[2:]
    coef, *_ = np.linalg.lstsq(a, b, rcond=None)
    residual = float(np.linalg.norm(a @ coef - b) / np.linalg.norm(b))
    roots = np.roots([1.0, -coef[0], -coef[1]])
    z = complex(roots[np.argmax(np.imag(roots))])
    if abs(z.imag) <= 0.0:
        raise RuntimeError("identification found no oscillating pair (overdamped?)")
    omega, zeta = _modal_from_lambda(complex(cmath.log(z) / h_sample))
    return omega, zeta, residual


def _stride_and_steps(omega: float, sigma: float, dt: float, t_max: float) -> tuple[int, int]:
    period = 2.0 * math.pi / omega
    stride = max(1, round(period / (SAMPLES_PER_PERIOD * dt)))
    t_end = min(t_max, -math.log(DECAY_STOP) / sigma) if sigma > 0.0 else t_max
    t_end = max(t_end, 3.0 * period)
    return stride, max(3 * stride, round(t_end / dt))


# --- results -----------------------------------------------------------------------------


@dataclass
class Result:
    """One identified case; all values SI. 'expected' = continuous model (no numerics)."""

    name: str
    dt_s: float
    scheme: str
    mass_kg: float
    k_expected_N_m: float
    c_expected_N_s_m: float
    f_expected_Hz: float
    zeta_expected: float
    f_discrete_Hz: float
    zeta_discrete: float
    f_measured_Hz: float
    zeta_measured: float
    zeta_numerical: float  # zeta_discrete - zeta_expected (exact map); approx. omega dt/2 for BE
    zeta_measured_minus_numerical: float
    k_identified_N_m: float  # exact inverse of the discrete map
    c_identified_N_s_m: float
    prony_residual: float
    steps: int
    stride: int
    wall_s: float
    extra: dict[str, Any] = field(default_factory=dict)

    def rel(self, key: str) -> float:
        """Relative error of a measured/identified quantity against the expected one."""
        pairs = {
            "f": (self.f_measured_Hz, self.f_discrete_Hz),
            "zeta": (self.zeta_measured, self.zeta_discrete),
            "zeta_corrected": (self.zeta_measured_minus_numerical, self.zeta_expected),
            "k": (self.k_identified_N_m, self.k_expected_N_m),
            "c": (self.c_identified_N_s_m, self.c_expected_N_s_m),
        }
        got, ref = pairs[key]
        return got - ref if ref == 0.0 else (got - ref) / ref  # absolute when ref is 0


def _finish(
    name: str,
    dt: float,
    scheme: str,
    m: float,
    k: float,
    c: float,
    velocity: list[float],
    stride: int,
    steps: int,
    wall: float,
    extra: dict[str, Any],
) -> Result:
    omega_c, zeta_c = continuous_modal(k, c, m)
    omega_d, zeta_d = discrete_modal(k, c, m, dt, scheme)
    omega_m, zeta_m, residual = identify_prony(np.asarray(velocity), stride * dt)
    k_id, c_id = invert_discrete(omega_m, zeta_m, m, dt, scheme)
    two_pi = 2.0 * math.pi
    return Result(
        name=name,
        dt_s=dt,
        scheme=scheme,
        mass_kg=m,
        k_expected_N_m=k,
        c_expected_N_s_m=c,
        f_expected_Hz=omega_c / two_pi,
        zeta_expected=zeta_c,
        f_discrete_Hz=omega_d / two_pi,
        zeta_discrete=zeta_d,
        f_measured_Hz=omega_m / two_pi,
        zeta_measured=zeta_m,
        zeta_numerical=zeta_d - zeta_c,
        zeta_measured_minus_numerical=zeta_m - (zeta_d - zeta_c),
        k_identified_N_m=k_id,
        c_identified_N_s_m=c_id,
        prony_residual=residual,
        steps=steps,
        stride=stride,
        wall_s=wall,
        extra=extra,
    )


# --- single contact ----------------------------------------------------------------------


def effective_mass(m1: float, m2: float) -> float:
    """m1 m2 / (m1 + m2) (the source reading of ChContactSMC)."""
    return m1 * m2 / (m1 + m2)


def single_contact(
    params: Params,
    *,
    dt: float,
    name: str = "single",
    floor_mass_kg: float | None = None,
    gn_scale: float = 1.0,
    sphere_kn_N_m: float | None = None,
    sphere_gn_1_s: float | None = None,
    contact_stiff: bool = False,
    t_max_s: float = 0.2,
) -> Result:
    """One sphere on the floor plate (FL material), vertical free vibration about equilibrium.

    ``sphere_kn_N_m``/``sphere_gn_1_s`` give the sphere its own material (composition test);
    by default it copies the floor material, so the composite equals the floor values.
    Expected values use the arithmetic mean (installed ChContactMaterialCompositionStrategy)
    and ``c = m_eff * gn``.
    """
    leg = params.leg("FL")
    mass = leg.moving_part.mass_kg
    radius = leg.pad.swivel_center_above_pad_bottom_m
    bundle = make_system(params, "L1", dt=dt)
    system = bundle.system
    system.SetContactStiff(contact_stiff)
    floor_mat = bundle.floor_material
    if gn_scale != 1.0:
        floor_mat.SetGn(floor_mat.GetGn() * gn_scale)
    if floor_mass_kg is not None:
        bundle.floor.SetMass(floor_mass_kg)
    kn_f, gn_f = floor_mat.GetKn(), floor_mat.GetGn()
    kn_s = kn_f if sphere_kn_N_m is None else sphere_kn_N_m
    gn_s = gn_f if sphere_gn_1_s is None else sphere_gn_1_s
    sphere_mat = make_smc_material(kn_s, gn_s)
    kn_s, gn_s = sphere_mat.GetKn(), sphere_mat.GetGn()  # float32 as stored by Chrono
    composite = ch.ChContactMaterialCompositeSMC(
        ch.ChContactMaterialCompositionStrategy(), sphere_mat, floor_mat
    )
    k = 0.5 * (kn_s + kn_f)
    gn = 0.5 * (gn_s + gn_f)
    m_floor = bundle.floor.GetMass()
    m_eff = effective_mass(mass, m_floor)
    c = gn * m_eff

    g = params.meta.gravity_m_s2
    delta0 = mass * g / k
    top = params.ground.crawler_bottom_z_m
    body = ch.ChBody()
    body.SetMass(mass)
    i_sphere = 0.4 * mass * radius * radius  # inertia irrelevant (no tangential force)
    body.SetInertiaXX(ch.ChVector3d(i_sphere, i_sphere, i_sphere))
    body.SetPos(ch.ChVector3d(0.0, 0.0, top + radius - delta0))
    body.SetPosDt(ch.ChVector3d(0.0, 0.0, V0_SINGLE_M_S))
    body.EnableCollision(True)
    body.AddCollisionShape(ch.ChCollisionShapeSphere(sphere_mat, radius))
    system.Add(body)

    scheme = SYMPLECTIC  # measured: SetContactStiff(True) changes nothing (module docstring)
    omega, zeta = continuous_modal(k, c, mass)
    stride, steps = _stride_and_steps(omega, zeta * omega, dt, t_max_s)
    velocity: list[float] = []
    start = time.perf_counter()
    for i in range(steps + 1):
        if i % stride == 0:
            velocity.append(float(body.GetPosDt().z))
        if i < steps:
            system.DoStepDynamics(dt)
    wall = time.perf_counter() - start
    extra = {
        "floor_mass_kg": m_floor,
        "m_eff_kg": m_eff,
        "sphere_kn_N_m": kn_s,
        "sphere_gn_1_s": gn_s,
        "floor_kn_N_m": kn_f,
        "floor_gn_1_s": gn_f,
        "composite_kn_N_m": float(composite.kn),
        "composite_gn_1_s": float(composite.gn),
        "contact_stiff": contact_stiff,
        "static_penetration_m": delta0,
        "v0_m_s": V0_SINGLE_M_S,
    }
    return _finish(name, dt, scheme, mass, k, c, velocity, stride, steps, wall, extra)


def static_penetration(params: Params, *, dt: float, t_s: float = 0.15) -> dict[str, float]:
    """Sphere released at contact (zero penetration); final penetration vs m g / kn."""
    leg = params.leg("FL")
    mass = leg.moving_part.mass_kg
    radius = leg.pad.swivel_center_above_pad_bottom_m
    bundle = make_system(params, "L1", dt=dt)
    top = params.ground.crawler_bottom_z_m
    mat = bundle.floor_material
    body = ch.ChBody()
    body.SetMass(mass)
    body.SetInertiaXX(ch.ChVector3d(1.0, 1.0, 1.0))
    body.SetPos(ch.ChVector3d(0.0, 0.0, top + radius))
    body.EnableCollision(True)
    body.AddCollisionShape(ch.ChCollisionShapeSphere(mat, radius))
    bundle.system.Add(body)
    for _ in range(round(t_s / dt)):
        bundle.system.DoStepDynamics(dt)
    measured = top + radius - float(body.GetPos().z)
    expected = mass * params.meta.gravity_m_s2 / mat.GetKn()
    force = float(body.GetContactForce().z)
    return {
        "penetration_measured_m": measured,
        "penetration_expected_m": expected,
        "rel_error": (measured - expected) / expected,
        "contact_force_z_N": force,
        "weight_N": mass * params.meta.gravity_m_s2,
    }


# --- heave of the 4-pad rigid assembly ---------------------------------------------------


def heave(params: Params, *, dt: float, t_max_s: float = 2.0) -> Result:
    """Uncoupled heave of the superstructure + 4 welded moving parts (module docstring)."""
    bundle = make_system(params, "L1", dt=dt, floor_plate=False)
    system = bundle.system
    floor = bundle.floor
    floor.EnableCollision(True)
    top = params.ground.crawler_bottom_z_m
    g = params.meta.gravity_m_s2
    sup_props = params.superstructure.mass_properties
    m_sup = sup_props.mass_kg

    l1 = params.contact.rigid_floor.L1
    pads = []
    for index, name in enumerate(LEG_ORDER):
        leg = params.legs[index]
        mat = make_smc_material(l1.kn_per_pad_N_m[index], l1.gn_per_pad_1_s[index])
        hx = FLOOR_PATCH_HALF_M
        x, y, _ = leg.pad_bottom_center_retracted_m
        floor.AddCollisionShape(
            ch.ChCollisionShapeBox(mat, 2 * hx, 2 * hx, 2 * hx),
            ch.ChFramed(ch.ChVector3d(x, y, top - hx), ch.QUNIT),
        )
        pads.append((name, leg, mat, x, y))

    kn = np.array([p[2].GetKn() for p in pads], dtype=float)
    gn = np.array([p[2].GetGn() for p in pads], dtype=float)
    m_pad = np.array([p[1].moving_part.mass_kg for p in pads])
    xy = np.array([[p[3], p[4]] for p in pads])
    m_total = m_sup + float(m_pad.sum())
    k_sum = float(kn.sum())
    m_eff = np.array([effective_mass(m, floor.GetMass()) for m in m_pad])
    c_sum = float(np.sum(gn * m_eff))
    centroid = (kn @ xy) / k_sum
    # superstructure CoM shifted so that the total CoM lies on the stiffness centroid
    sup_xy = (m_total * centroid - m_pad @ xy) / m_sup
    delta0 = m_total * g / k_sum
    sup_z = top - delta0 + (sup_props.com_m[2] - params.ground.crawler_bottom_z_m)

    sup = ch.ChBody()
    sup.SetName("superstructure")
    sup.SetMass(m_sup)
    inertia = sup_props.inertia_kg_m2
    sup.SetInertiaXX(ch.ChVector3d(inertia[0][0], inertia[1][1], inertia[2][2]))
    sup.SetInertiaXY(ch.ChVector3d(inertia[0][1], inertia[0][2], inertia[1][2]))
    sup.SetPos(ch.ChVector3d(float(sup_xy[0]), float(sup_xy[1]), sup_z))
    sup.SetPosDt(ch.ChVector3d(0.0, 0.0, V0_HEAVE_M_S))
    system.Add(sup)

    keep: list[Any] = []
    pad_bodies = []
    for name, leg, mat, x, y in pads:
        mp = leg.moving_part
        radius = leg.pad.swivel_center_above_pad_bottom_m
        h_com = leg_com_above_pad_bottom(params, name)
        body = ch.ChBody()
        body.SetName(f"moving_part_{name}")
        body.SetMass(mp.mass_kg)
        body.SetInertiaXX(
            ch.ChVector3d(mp.inertia_kg_m2[0][0], mp.inertia_kg_m2[1][1], mp.inertia_kg_m2[2][2])
        )
        pos = ch.ChVector3d(x, y, top - delta0 + h_com)
        body.SetPos(pos)
        body.SetPosDt(ch.ChVector3d(0.0, 0.0, V0_HEAVE_M_S))
        body.EnableCollision(True)
        body.AddCollisionShape(
            ch.ChCollisionShapeSphere(mat, radius),
            ch.ChFramed(ch.ChVector3d(0.0, 0.0, radius - h_com), ch.QUNIT),
        )
        system.Add(body)
        weld = ch.ChLinkLockLock()
        weld.Initialize(body, sup, ch.ChFramed(pos, ch.QUNIT))
        system.Add(weld)
        keep.append(weld)
        pad_bodies.append(body)

    omega, zeta = continuous_modal(k_sum, c_sum, m_total)
    stride, steps = _stride_and_steps(omega, zeta * omega, dt, t_max_s)
    velocity: list[float] = []
    rot_rate_max = 0.0
    force0 = None
    start = time.perf_counter()
    for i in range(steps + 1):
        if i % stride == 0:
            velocity.append(float(sup.GetPosDt().z))
            w = sup.GetAngVelParent()
            rot_rate_max = max(rot_rate_max, math.hypot(w.x, w.y))
        if i < steps:
            system.DoStepDynamics(dt)
            if force0 is None:
                force0 = sum(float(b.GetContactForce().z) for b in pad_bodies)
    wall = time.perf_counter() - start
    design_zeta = float(params.get("contact.rigid_floor.L1.derivation.damping_ratio"))
    design_f = float(params.get("contact.rigid_floor.L1.derivation.damping_reference_mode_Hz"))
    design_m = float(params.get("contact.rigid_floor.L1.derivation.damping_mass_kg"))
    cn = np.array(l1.cn_per_pad_N_s_m, dtype=float)
    extra = {
        "m_total_kg": m_total,
        "m_pad_kg": m_pad.tolist(),
        "m_eff_per_pad_kg": m_eff.tolist(),
        "gn_per_pad_1_s": gn.tolist(),
        "kn_per_pad_N_m": kn.tolist(),
        "c_per_pad_N_s_m": (gn * m_eff).tolist(),
        "cn_per_pad_yaml_N_s_m": cn.tolist(),
        "stiffness_centroid_xy_m": centroid.tolist(),
        "superstructure_com_xy_shifted_m": sup_xy.tolist(),
        "superstructure_com_xy_yaml_m": list(sup_props.com_m[:2]),
        "static_penetration_m": delta0,
        "contact_force_sum_first_step_N": force0,
        "weight_N": m_total * g,
        "max_roll_pitch_rate_rad_s": rot_rate_max,
        "heave_velocity_amplitude_m_s": V0_HEAVE_M_S,
        "design": {
            "damping_ratio": design_zeta,
            "damping_reference_mode_Hz": design_f,
            "damping_mass_kg": design_m,
            "source": "contact.rigid_floor.L1.derivation",
        },
    }
    return _finish(
        "heave", dt, SYMPLECTIC, m_total, k_sum, c_sum, velocity, stride, steps, wall, extra
    )


def leg_com_above_pad_bottom(params: Params, leg: str) -> float:
    """``legs.<leg>.moving_part.com_above_pad_bottom_m`` [m]."""
    return float(params.get(f"legs.{leg}.moving_part.com_above_pad_bottom_m"))


# --- main --------------------------------------------------------------------------------


def _pychrono_version() -> str | None:
    """Version from the env's conda metadata (pychrono has no ``__version__``)."""
    meta = Path(sys.prefix) / "conda-meta"
    names = sorted(meta.glob("pychrono-*.json")) if meta.is_dir() else []
    return json.loads(names[-1].read_text(encoding="utf-8"))["version"] if names else None


def run_all(params: Params) -> dict[str, Any]:
    """Every case of the module docstring for dt 1e-4 and 1e-5 s."""
    dts = (
        float(params.get("simulation.L1.dt_s")),
        float(params.get("simulation.dt_reference_s")),
    )
    l1 = params.contact.rigid_floor.L1
    kn_f, gn_f = l1.kn_per_pad_N_m[0], l1.gn_per_pad_1_s[0]
    results: list[Result] = []
    for dt in dts:
        results += [
            single_contact(params, dt=dt, name="floor_1e9"),
            single_contact(params, dt=dt, name="floor_1e3", floor_mass_kg=1.0e3),
            single_contact(params, dt=dt, name="floor_1", floor_mass_kg=1.0),
            single_contact(params, dt=dt, name="gn_x0.1", gn_scale=0.1),
            single_contact(params, dt=dt, name="gn_x0", gn_scale=0.0),
            single_contact(params, dt=dt, name="gn_x0_stiff", gn_scale=0.0, contact_stiff=True),
            single_contact(params, dt=dt, name="floor_1e9_stiff", contact_stiff=True),
            single_contact(
                params,
                dt=dt,
                name="composite",
                sphere_kn_N_m=3.0 * kn_f,
                sphere_gn_1_s=0.25 * gn_f,
            ),
            heave(params, dt=dt),
        ]
    composite_hypotheses = {
        "arithmetic_mean": {"kn": 0.5 * (3.0 + 1.0) * kn_f, "gn": 0.5 * (0.25 + 1.0) * gn_f},
        "harmonic_mean": {"kn": 2 * 3.0 / 4.0 * kn_f, "gn": 2 * 0.25 / 1.25 * gn_f},
        "series": {"kn": 3.0 / 4.0 * kn_f, "gn": 0.25 / 1.25 * gn_f},
        "min": {"kn": kn_f, "gn": 0.25 * gn_f},
        "max": {"kn": 3.0 * kn_f, "gn": gn_f},
    }
    return {
        "pychrono_version": _pychrono_version(),
        "params_sha256": params.sha256,
        "static_penetration": static_penetration(params, dt=dts[0]),
        "composite_hypotheses_floor_FL": composite_hypotheses,
        "cases": [
            asdict(r) | {"rel": {q: r.rel(q) for q in ("f", "zeta", "k", "c")}} for r in results
        ],
    }


def main() -> None:
    params = load_params(PARAMS_PATH)
    report = run_all(params)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    header = f"{'case':18s} {'dt':>7s} {'f_exp':>9s} {'f_meas':>9s} {'z_exp':>8s} {'z_disc':>8s}"
    print(
        header
        + f" {'z_meas':>8s} {'z_corr':>8s} {'c_rel':>9s} {'k_rel':>9s} {'res':>8s} {'wall':>6s}"
    )
    for case in report["cases"]:
        print(
            f"{case['name']:18s} {case['dt_s']:7.0e} {case['f_expected_Hz']:9.4f} "
            f"{case['f_measured_Hz']:9.4f} {case['zeta_expected']:8.5f} "
            f"{case['zeta_discrete']:8.5f} {case['zeta_measured']:8.5f} "
            f"{case['zeta_measured_minus_numerical']:8.5f} {case['rel']['c']:9.2e} "
            f"{case['rel']['k']:9.2e} {case['prony_residual']:8.1e} {case['wall_s']:6.2f}"
        )
    print(json.dumps(report["static_penetration"], indent=1))
    print(f"wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
