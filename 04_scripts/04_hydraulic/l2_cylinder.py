"""L2 hydraulic leg actuator: reference implementation of the discrete force law.

Specification: 00_docs/02_hydraulic/l2_hydraulic_model_spec.md (sections 3-5). This module is the
executable form of that spec. It is plain numpy/math (no pint, no Chrono) so that it can be imported
from the Chrono-dev environment as well; units are SI throughout. Every default that is not from CAD
or a user decision is an ASSUMPTION and is listed in l2_params.py.

Sign conventions (one leg)
  s        piston extension relative to the barrel [m]; 0 = fully retracted, + = leg longer
  v        ds/dt [m/s]
  F        actuator force on the rod chain [N]; + = pushes the rod out (the leg carries compression)
  p_*      ABSOLUTE pressure [Pa]; gauge = p - p_atm. Head chamber "A", rod-side (annulus) chamber "B"
  Q_*      volumetric flow INTO a chamber [m^3/s], evaluated at the chamber pressure
  m_*      oil amount of a chamber, expressed as liquid volume at p_atm [m^3] (mass / rho(p_atm))

Equation of state (exact, no time-step limit): a chamber of geometric volume V holding m obeys
  V = m exp(-(p - p_atm)/beta_L) + m r (p_air/p)^(1/n),   r = x_air/(1 - x_air)
With x_air = 0 this is p = p_atm + beta_L ln(m / V), the exact integral of dp/dt = beta/V (Q - dV/dt)
when dm/dt = Q m / V (see continuity()). Below p_cav the chamber cavitates (p held at p_cav).

Discrete step (called once per mechanical step, see L2Cylinder.step):
  1. pressure valves (relief, counterbalance): Hopsan-compatible law, explicit with the previous pressure
  2. chamber oil amounts: linearly implicit Euler on dm/dt = Q(p) m / V (unconditionally stable for
     dQ/dp <= 0), the piston volume change enters exactly through V(s)
  3. pressures from the equation of state (algebraic)
  4. LuGre seal friction: exact exponential update of the bristle state for a constant velocity
  5. force F = (p_A - p_ref) A_A - (p_B - p_ref) A_B - F_fric - c_h v
  Optional massless series spring k_s (rod / frame / concrete merged into the force law, L2b-NSC):
  the piston position s_p is solved from F_int(s_p) = k_s (s_p - s_link) by Newton.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

# ---------------------------------------------------------------------------------------------
# parameters
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Geometry:
    area_head_m2: float          # A_A = pi/4 D^2
    area_rod_side_m2: float      # A_B = pi/4 (D^2 - d^2)
    stroke_m: float
    dead_volume_head_m3: float   # V_0A: block passage + port + cushion at s = 0
    dead_volume_rod_m3: float    # V_0B at s = stroke


@dataclass(frozen=True)
class Fluid:
    beta_L_Pa: float = 1.0e9          # lumped liquid + wall + residual bulk modulus (user decision 1.0 GPa)
    air_fraction: float = 0.0         # free-air volume fraction at p_air_ref (0 = constant beta)
    p_air_ref_abs_Pa: float = 1.0e5
    polytropic_n: float = 1.0
    p_atm_Pa: float = 1.0e5           # gauge reference (Hopsan tank default 1e5 Pa)
    p_cav_abs_Pa: float = 0.0         # cavitation floor (absolute)


@dataclass(frozen=True)
class Friction:
    """LuGre seal friction between piston/rod and barrel (parallel to the oil column)."""
    F_s_N: float = 0.0                # static (breakaway) friction
    F_c_N: float | None = None        # Coulomb level; None -> = F_s (static = kinetic, V15 mode)
    v_stribeck_m_s: float = 0.005
    sigma0_N_m: float = 1.0e10        # bristle stiffness (presliding F_s/sigma0)
    sigma1_N_s_m: float = 0.0         # bristle damping
    pressure_coeff_per_Pa: float = 0.0  # F scaled by (1 + k_p (p_A_g - p_ref_g)) (Kuehnlein K_p ~ 4e-7 1/Pa)
    pressure_ref_gauge_Pa: float = 0.0

    def g(self, v: float, scale: float = 1.0) -> float:
        fc = self.F_s_N if self.F_c_N is None else self.F_c_N
        return scale * (fc + (self.F_s_N - fc) * math.exp(-(v / self.v_stribeck_m_s) ** 2))


@dataclass(frozen=True)
class PressureValve:
    """Pressure-opened valve (relief / counterbalance relief function), Hopsan-2.24 compatible law.

    Opening coefficient (flow coefficient, m^3/s/sqrt(Pa)):
      x_s = (p_in_g - p_set_g + pilot_ratio * p_pilot_g) / b,   b = C_s + C_f (p_in - p_out)
      C_s = sqrt(p_nom)/k_cs,  C_f = 1/(k_cf sqrt(p_nom)),  x in [0, q_nom/sqrt(p_nom)]
      play (hysteresis) of width p_h/b, then first-order lag tau.
      Q = x sqrt(|p_in - p_out|) sign(p_in - p_out)  (from in to out)
    Hopsan uses absolute p_in and pilot pressures; the generator shifts p_ref so both are gauge-equal.
    """
    p_set_gauge_Pa: float
    pilot_ratio: float = 0.0
    hysteresis_Pa: float = 0.0
    tau_s: float = 0.01
    k_cs: float = 1.0e-6
    k_cf: float = 4.0e-10
    q_nom_m3_s: float = 1.0e-3
    p_nom_Pa: float = 7.0e6

    @property
    def c_s(self) -> float:
        return math.sqrt(self.p_nom_Pa) / self.k_cs

    @property
    def c_f(self) -> float:
        return 1.0 / (self.k_cf * math.sqrt(self.p_nom_Pa))

    @property
    def x_max(self) -> float:
        return self.q_nom_m3_s / math.sqrt(self.p_nom_Pa)


@dataclass(frozen=True)
class CylinderParams:
    geometry: Geometry
    fluid: Fluid = Fluid()
    friction: Friction = Friction()
    c_h_locked_N_s_m: float = 0.0      # hydraulic / seal viscous damping, locked (ASSUMPTION zeta 0.03)
    c_h_moving_N_s_m: float = 0.0      # while a valve section drives the leg (ASSUMPTION zeta 0.10)
    leak_internal_m3_s_Pa: float = 0.0  # piston seal A -> B
    leak_ext_head_m3_s_Pa: float = 0.0  # check-valve seat / rod gland to tank (gauge driven)
    leak_ext_rod_m3_s_Pa: float = 0.0
    relief: PressureValve | None = None          # 210 bar stall model at the head chamber (moving)
    counterbalance: PressureValve | None = None  # option: head chamber relief at 350 bar (locked)
    k_series_N_m: float = math.inf     # massless series spring rod+frame(+concrete) merged into the law
    p_force_ref_abs_Pa: float | None = None  # None -> p_atm (physical); 0.0 -> Hopsan convention
    end_stop_k_N_m: float = 1.0e9      # penalty end stops at s < 0 and s > stroke (ASSUMPTION)
    moving_extra_volume_head_m3: float = 0.0  # line/hose volume (bulk-equivalent) joined while POC-A open

    @property
    def p_ref(self) -> float:
        return self.fluid.p_atm_Pa if self.p_force_ref_abs_Pa is None else self.p_force_ref_abs_Pa


@dataclass
class Inputs:
    """Per-step hydraulic inputs (from the valve section model or a test schedule)."""
    q_head_m3_s: float = 0.0          # flow-controlled flow into A (pressure-compensated section), + in
    rod_valve_open: float = 0.0       # 0..1 opening of the rod-side path (POC-B piloted open + spool)
    rod_valve_Ks: float = 0.0         # m^3/s/sqrt(Pa) at full opening (turbulent)
    p_rod_line_g_Pa: float = 0.0      # rod-side line pressure (tank 0 when extending, pilot when retracting)
    head_poc_open: bool = False       # head line joined to the chamber (moving)
    moving: bool = False              # selects c_h_moving
    p_cb_pilot_g_Pa: float = 0.0      # counterbalance pilot (opposite line), gauge


@dataclass
class State:
    m_A: float = 0.0
    m_B: float = 0.0
    p_A: float = 1.0e5
    p_B: float = 1.0e5
    s_p: float = 0.0       # piston position (= link position when k_series = inf)
    z: float = 0.0         # LuGre bristle state [m]
    x_relief: float = 0.0
    x_cb: float = 0.0
    head_joined: bool = False
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------------------------
# equation of state and continuity
# ---------------------------------------------------------------------------------------------


def fluid_volume(m: float, p: float, f: Fluid) -> tuple[float, float]:
    """Volume of oil amount m at absolute pressure p and dV/dp (<= 0)."""
    vl = m * math.exp(-(p - f.p_atm_Pa) / f.beta_L_Pa)
    dv = -vl / f.beta_L_Pa
    if f.air_fraction > 0.0:
        r = f.air_fraction / (1.0 - f.air_fraction)
        pp = max(p, 1.0)
        vg = m * r * (f.p_air_ref_abs_Pa / pp) ** (1.0 / f.polytropic_n)
        return vl + vg, dv - vg / (f.polytropic_n * pp)
    return vl, dv


def pressure_from_state(m: float, V: float, f: Fluid, p_guess: float | None = None) -> float:
    """Solve fluid_volume(m, p) = V for p (absolute), floor p_cav (cavitation)."""
    if f.air_fraction <= 0.0:
        return max(f.p_atm_Pa + f.beta_L_Pa * math.log(m / V), f.p_cav_abs_Pa)
    p_floor = max(f.p_cav_abs_Pa, 1.0)
    vf_floor, _ = fluid_volume(m, p_floor, f)
    if vf_floor <= V:
        return p_floor
    # Newton in y = ln p (the function is smooth and monotone); bisection guard
    lo, hi = p_floor, max(p_guess or f.p_atm_Pa, p_floor) * 2.0
    while fluid_volume(m, hi, f)[0] > V:
        hi *= 2.0
    p = min(max(p_guess or 0.5 * (lo + hi), lo), hi)
    for _ in range(60):
        vf, dv = fluid_volume(m, p, f)
        r = vf - V
        if r > 0.0:
            lo = p
        else:
            hi = p
        if abs(r) <= 1e-13 * V:
            break
        p_new = p - r / dv
        if not (lo < p_new < hi):
            p_new = 0.5 * (lo + hi)
        p = p_new
    return p


def beta_eff(m: float, p: float, f: Fluid) -> float:
    """Effective bulk modulus V / (-dV/dp) of the chamber content at p (0 when cavitating)."""
    if p <= f.p_cav_abs_Pa and f.air_fraction <= 0.0:
        return 0.0
    vf, dv = fluid_volume(m, p, f)
    return vf / (-dv)


def continuity(m: float, V_old: float, V_new: float, p: float, q: float, dqdp: float,
               dt: float, f: Fluid) -> float:
    """Linearly implicit update of the oil amount over one step (returns the new m).

    dm/dt = Q(p) m / V_f(p); Q(p_new) ~ q + dqdp (p_new - p); p_new - p ~ beta (dm/m - dV/V).
    With dqdp <= 0 the denominator is >= 1: stable for any dt.
    """
    vf, dv = fluid_volume(m, p, f)
    b = 0.0 if (p <= f.p_cav_abs_Pa and f.air_fraction <= 0.0) else vf / (-dv)
    a = dt * m / vf
    dV = V_new - V_old
    den = 1.0 - dt * dqdp * b / vf
    return m + a * (q - dqdp * b * dV / V_new) / den


def mass_for_pressure(p: float, V: float, f: Fluid) -> float:
    """Oil amount that gives absolute pressure p in volume V (inverse EOS)."""
    vf1, _ = fluid_volume(1.0, p, f)
    return V / vf1


# ---------------------------------------------------------------------------------------------
# components
# ---------------------------------------------------------------------------------------------


def lugre_update(z: float, v: float, dt: float, fr: Friction, scale: float = 1.0) -> tuple[float, float]:
    """Exact bristle update for constant v over dt; returns (z_new, friction force on the piston, + along v)."""
    if fr.F_s_N <= 0.0 and (fr.F_c_N or 0.0) <= 0.0:
        return 0.0, 0.0
    g = fr.g(v, scale)
    s0 = fr.sigma0_N_m
    if v == 0.0 or g <= 0.0:
        z_new = z
    else:
        lam = s0 * abs(v) / g
        z_ss = math.copysign(g / s0, v)
        z_new = z_ss + (z - z_ss) * math.exp(-lam * dt)
    force = s0 * z_new + fr.sigma1_N_s_m * (z_new - z) / dt
    return z_new, force


def play(xs: float, xh: float, xd: float) -> float:
    """Hopsan ValveHysteresis: backlash of width xh around xs acting on the previous output xd."""
    if xd < xs - 0.5 * xh:
        return xs - 0.5 * xh
    if xd > xs + 0.5 * xh:
        return xs + 0.5 * xh
    return xd


def pressure_valve_update(x: float, pv: PressureValve, p_in_g: float, p_out_g: float,
                          p_pilot_g: float, dt: float) -> float:
    """Advance the opening coefficient x of a pressure valve by dt (explicit in pressure)."""
    dp = max(p_in_g - p_out_g, 0.0)
    b = pv.c_s + pv.c_f * dp
    xs = (p_in_g - pv.p_set_gauge_Pa + pv.pilot_ratio * max(p_pilot_g, 0.0)) / b
    xsh = play(xs, pv.hysteresis_Pa / b, x)
    x_new = xsh + (x - xsh) * math.exp(-dt / pv.tau_s)
    return min(max(x_new, 0.0), pv.x_max)


def turbulent(Ks: float, dp: float) -> tuple[float, float]:
    """Q = Ks sqrt|dp| sign(dp) and dQ/d(dp) (regularised near dp = 0, 1 kPa)."""
    if Ks <= 0.0:
        return 0.0, 0.0
    a = 1.0e3
    if abs(dp) >= a:
        q = Ks * math.copysign(math.sqrt(abs(dp)), dp)
        return q, Ks / (2.0 * math.sqrt(abs(dp)))
    # odd cubic blend below a: value and slope match the square root at |dp| = a (C1)
    sa = math.sqrt(a)
    x = dp / a
    q = Ks * sa * (1.25 * x - 0.25 * x ** 3)
    return q, Ks * sa * (1.25 - 0.75 * x * x) / a


# ---------------------------------------------------------------------------------------------
# the actuator
# ---------------------------------------------------------------------------------------------


class L2Cylinder:
    """One leg: double-acting cylinder, dual POC lock, optional counterbalance, LuGre seal friction."""

    def __init__(self, prm: CylinderParams):
        self.prm = prm
        self.st = State()
        self.t = 0.0

    # geometry -------------------------------------------------------------------------------
    def V_A(self, s: float) -> float:
        g = self.prm.geometry
        return g.dead_volume_head_m3 + g.area_head_m2 * s

    def V_B(self, s: float) -> float:
        g = self.prm.geometry
        return g.dead_volume_rod_m3 + g.area_rod_side_m2 * (g.stroke_m - s)

    def k_oil(self, s: float | None = None, include_rod_side: bool = True) -> float:
        """Locked hydraulic stiffness beta_A A_A^2/V_A + beta_B A_B^2/V_B at the current state."""
        g, f, st = self.prm.geometry, self.prm.fluid, self.st
        s = st.s_p if s is None else s
        k = beta_eff(st.m_A, st.p_A, f) * g.area_head_m2 ** 2 / self.V_A(s)
        if include_rod_side:
            k += beta_eff(st.m_B, st.p_B, f) * g.area_rod_side_m2 ** 2 / self.V_B(s)
        return k

    # initialisation ---------------------------------------------------------------------------
    def init_static(self, s_link: float, F0: float, p_rod_g0: float = 2.0e5, t0: float = 0.0) -> None:
        """Locked equilibrium: force F0 at link extension s_link, rod side at p_rod_g0 (gauge), z = 0."""
        prm, f, g = self.prm, self.prm.fluid, self.prm.geometry
        s_p = s_link + (F0 / prm.k_series_N_m if math.isfinite(prm.k_series_N_m) else 0.0)
        p_B = f.p_atm_Pa + p_rod_g0
        p_A = prm.p_ref + (F0 + (p_B - prm.p_ref) * g.area_rod_side_m2) / g.area_head_m2
        self.st = State(m_A=mass_for_pressure(p_A, self.V_A(s_p), f),
                        m_B=mass_for_pressure(p_B, self.V_B(s_p), f),
                        p_A=p_A, p_B=p_B, s_p=s_p, z=0.0)
        self.t = t0

    # internals -------------------------------------------------------------------------------
    def _force_parts(self, st: State, s_p: float, v_p: float, dt: float, inp: Inputs,
                     commit_z: bool) -> tuple[float, float, dict]:
        """Hydraulic + friction + damping force at piston position s_p (pressures already in st)."""
        prm, g = self.prm, self.prm.geometry
        F_h = (st.p_A - prm.p_ref) * g.area_head_m2 - (st.p_B - prm.p_ref) * g.area_rod_side_m2
        fr = prm.friction
        scale = 1.0
        if fr.pressure_coeff_per_Pa:
            scale = max(0.0, 1.0 + fr.pressure_coeff_per_Pa
                        * (st.p_A - prm.fluid.p_atm_Pa - fr.pressure_ref_gauge_Pa))
        z_new, F_f = lugre_update(st.z, v_p, dt, fr, scale)
        c_h = prm.c_h_moving_N_s_m if inp.moving else prm.c_h_locked_N_s_m
        F_d = c_h * v_p
        F_stop = 0.0
        if s_p < 0.0:
            F_stop = -prm.end_stop_k_N_m * s_p
        elif s_p > g.stroke_m:
            F_stop = -prm.end_stop_k_N_m * (s_p - g.stroke_m)
        F = F_h - F_f - F_d + F_stop
        if commit_z:
            st.z = z_new
        return F, F_h, {"F_h": F_h, "F_fric": F_f, "F_damp": F_d, "F_stop": F_stop, "z": z_new}

    def _hydraulic_update(self, st: State, s_p_new: float, dt: float, inp: Inputs) -> dict:
        """Valves, continuity and EOS for one step with the piston moving st.s_p -> s_p_new (in place)."""
        prm, f = self.prm, self.prm.fluid
        pa_g, pb_g = st.p_A - f.p_atm_Pa, st.p_B - f.p_atm_Pa

        # head line joins the chamber while POC-A is open (bulk-equivalent hose volume)
        Vx = prm.moving_extra_volume_head_m3
        if Vx > 0.0 and inp.head_poc_open != st.head_joined:
            dm = mass_for_pressure(st.p_A, Vx, f)
            st.m_A += dm if inp.head_poc_open else -dm
            st.head_joined = inp.head_poc_open
        VxA = Vx if st.head_joined else 0.0

        # pressure valves (explicit in the previous pressure)
        q_rel = dq_rel = 0.0
        if prm.relief is not None and inp.moving:
            # MCV relief sits upstream of POC-A: it only sees the chamber while the section feeds it
            st.x_relief = pressure_valve_update(st.x_relief, prm.relief, pa_g, 0.0, 0.0, dt)
            q_rel, dq_rel = turbulent(st.x_relief, pa_g)
        else:
            st.x_relief = 0.0
        q_cb = dq_cb = 0.0
        if prm.counterbalance is not None:
            st.x_cb = pressure_valve_update(st.x_cb, prm.counterbalance, pa_g, 0.0,
                                            inp.p_cb_pilot_g_Pa, dt)
            q_cb, dq_cb = turbulent(st.x_cb, pa_g)
        q_rod, dq_rod = turbulent(inp.rod_valve_open * inp.rod_valve_Ks, inp.p_rod_line_g_Pa - pb_g)
        q_int = prm.leak_internal_m3_s_Pa * (st.p_A - st.p_B)

        qA = inp.q_head_m3_s - q_rel - q_cb - q_int - prm.leak_ext_head_m3_s_Pa * max(pa_g, 0.0)
        dqA = -dq_rel - dq_cb - prm.leak_internal_m3_s_Pa - prm.leak_ext_head_m3_s_Pa
        qB = q_rod + q_int - prm.leak_ext_rod_m3_s_Pa * max(pb_g, 0.0)
        dqB = -dq_rod - prm.leak_internal_m3_s_Pa - prm.leak_ext_rod_m3_s_Pa

        VA0, VA1 = self.V_A(st.s_p) + VxA, self.V_A(s_p_new) + VxA
        VB0, VB1 = self.V_B(st.s_p), self.V_B(s_p_new)
        st.m_A = continuity(st.m_A, VA0, VA1, st.p_A, qA, dqA, dt, f)
        st.m_B = continuity(st.m_B, VB0, VB1, st.p_B, qB, dqB, dt, f)
        st.p_A = pressure_from_state(st.m_A, VA1, f, st.p_A)
        st.p_B = pressure_from_state(st.m_B, VB1, f, st.p_B)
        st.s_p = s_p_new
        return {"q_relief": q_rel, "q_cb": q_cb, "q_rod": q_rod, "q_head_in": inp.q_head_m3_s,
                "q_int": q_int}

    # public step ----------------------------------------------------------------------------------
    def step(self, s_link: float, v_link: float, dt: float, inp: Inputs) -> dict:
        """Advance the hydraulic states to the new link state and return the actuator force.

        Called once per mechanical step with the link extension/velocity at the END of that step.
        The returned force is what the mechanical solver applies over the following step (spec 5.2).
        """
        prm = self.prm
        st = self.st
        if not math.isfinite(prm.k_series_N_m):
            flows = self._hydraulic_update(st, s_link, dt, inp)
            F, F_h, parts = self._force_parts(st, s_link, v_link, dt, inp, commit_z=True)
            s_p, v_p = s_link, v_link
        else:
            s_p, v_p, F, F_h, parts, flows = self._solve_series(s_link, dt, inp)
        self.t += dt
        g = prm.geometry
        f = prm.fluid
        return {
            "t": self.t, "F": F, "s_p": s_p, "v_p": v_p,
            "p_A_g": st.p_A - f.p_atm_Pa, "p_B_g": st.p_B - f.p_atm_Pa,
            "F_sensor": (st.p_A - f.p_atm_Pa) * g.area_head_m2,
            **parts, **flows, "x_relief": st.x_relief, "x_cb": st.x_cb,
        }

    def _solve_series(self, s_link: float, dt: float, inp: Inputs):
        """Massless series spring: find s_p with F_int(s_p) = k_s (s_p - s_link) (Newton, <= 8 it)."""
        k_s = self.prm.k_series_N_m
        st0 = self.st
        s_prev = st0.s_p
        guess = s_prev + (s_link - st0.extra.get("s_link_prev", s_link))

        def residual(sp: float):
            trial = replace(st0, extra=dict(st0.extra))
            flows = self._hydraulic_update(trial, sp, dt, inp)
            v = (sp - s_prev) / dt
            F, F_h, parts = self._force_parts(trial, sp, v, dt, inp, commit_z=True)
            return F - k_s * (sp - s_link), trial, F, F_h, parts, flows, v

        sp = guess
        r, trial, F, F_h, parts, flows, v = residual(sp)
        for _ in range(8):
            h = 1e-8
            r2 = residual(sp + h)[0]
            dr = (r2 - r) / h
            if dr >= 0.0:
                dr = -k_s
            sp_new = sp - r / dr
            r, trial, F, F_h, parts, flows, v = residual(sp_new)
            if abs(sp_new - sp) < 1e-12:
                sp = sp_new
                break
            sp = sp_new
        trial.extra["s_link_prev"] = s_link
        self.st = trial
        F_link = k_s * (sp - s_link)
        return sp, v, F_link, F_h, parts, flows

    def force_preview(self, s_link: float, v_link: float, dt: float, inp: Inputs) -> float:
        """Force at a trial link state WITHOUT committing (lag compensation / predictor, spec 5.3)."""
        saved_st = replace(self.st, extra=dict(self.st.extra))
        saved_t = self.t
        out = self.step(s_link, v_link, dt, inp)
        self.st, self.t = saved_st, saved_t
        return out["F"]


# ---------------------------------------------------------------------------------------------
# valve section (Level 1): velocity command -> flow inputs
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ValveSection:
    """Pressure-compensated proportional section + dual POC, Level 1 (spec 4.1).

    u (m/s, + extend) is rate-limited (0 -> v_max in ramp_time_s). The head flow is A_A u_v (load
    independent: compensated meter-in when extending; meter-out assumed compensated when retracting,
    ASSUMPTION). The rod side is connected to its line through an orifice while moving: tank when
    extending, the POC-A pilot pressure when retracting.
    """
    area_head_m2: float
    area_rod_side_m2: float
    v_max_m_s: float = 0.0226666667
    ramp_time_s: float = 0.1
    rod_valve_Ks: float = 2.83e-8          # 5 bar at A_B v_max (ASSUMPTION)
    pilot_ratio_poc: float = 3.5           # ASSUMPTION
    poc_crack_Pa: float = 3.0e5            # ASSUMPTION
    poc_hysteresis_Pa: float = 2.0e5       # ASSUMPTION
    p_tank_g_Pa: float = 0.0


@dataclass
class ValveState:
    u_v: float = 0.0
    poc_b_open: bool = False


def valve_inputs(vs: ValveSection, vst: ValveState, u_cmd: float, p_A_g: float, dt: float) -> Inputs:
    """Ramp the command and build Inputs for one step (Level 1)."""
    u = max(-vs.v_max_m_s, min(vs.v_max_m_s, u_cmd))
    rate = vs.v_max_m_s / vs.ramp_time_s
    du = max(-rate * dt, min(rate * dt, u - vst.u_v))
    vst.u_v += du
    moving = abs(vst.u_v) > 0.0
    if vst.u_v > 0.0:
        q = vs.area_head_m2 * vst.u_v
        p_line_b = vs.p_tank_g_Pa
    elif vst.u_v < 0.0:
        q = vs.area_head_m2 * vst.u_v
        # pilot (line B) needed to hold POC-A open against the trapped head pressure
        p_line_b = max(p_A_g, 0.0) / vs.pilot_ratio_poc + vs.poc_crack_Pa
    else:
        q = 0.0
        p_line_b = vs.p_tank_g_Pa
    vst.poc_b_open = moving
    return Inputs(q_head_m3_s=q, rod_valve_open=1.0 if moving else 0.0, rod_valve_Ks=vs.rod_valve_Ks,
                  p_rod_line_g_Pa=p_line_b, head_poc_open=moving, moving=moving)
