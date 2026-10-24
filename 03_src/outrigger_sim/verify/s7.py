"""S7 checks: L2b-NSC V0-V14 (engine independent: arrays and dicts in, :class:`CheckResult` out).

``00_docs/03_chrono/chrono_build_plan.md`` S7 pass table; ``dynamics_model.md`` rev. 33 5.20
(5.20.4 statics / LOCK modes, 5.20.5 V5 / V6, 5.20.6 V4, 5.20.7 V12, 5.20.8 V14, 5.20.9 answers
Q1-Q5, 5.20.11 column rule and piston-stop monitor, supplement 1). Reference block
``reference.json / L2b_NSC_reference_rev33`` (:data:`REF_BLOCK`); V5 against the L1-R
quasi-static block (5.20.5: "V5 +1 mm 기준은 L1-R V5 값과 같다"); V12 against ``slope_V12 /
<case> / L2b_NSC``. Automatic pass / fail is a pre-check; the physical judgement is the
dynamics-expert's.

Rules of this module (the L1 rows of ``dynamics_model.md`` 5 unless named):

* **Pre-checks** (id ``pre``, 5.20.8 condition / 5.20.11): rod-side lock table of every locked
  leg: ``s_lock`` = the run's own ``s_ref`` at the lock instant (relative 1e-6, the column
  convention ``s_lock = s_ref``, not the rod body ``s = s_ref - F / k_2``); ``s_lock`` vs the
  reference extension and ``k_h``, ``k_r`` vs ``beta A / (L0 + ...)`` from ``leg_parameters``
  within 1e-6 **plus the printed-digit rounding bound** of the reference numbers (the reference
  prints 5-6 significant digits; the rounding alone is up to ~1e-5 relative, while the wrong
  column convention moves ``k_r`` by ~1 %); ``L_0r`` equal to the reference. Piston monitor:
  stop-violation steps 0 on every leg (a run with a violation is not judged).
* **V0**: inventory vs YAML (mass, CoM, inertia relative 1e-9; gravity; motor constraints 3 =
  guide x, y free); air sign test (``+v_max`` 1 s: pad dz = -motor travel within 1e-9 m;
  hanging force = ``-m_rod g`` +-1 N).
* **V1 / V2 / V3 / V13** (settle, still window 5 s, 0.1 s window means, 5.20.9 Q3): contact
  per leg vs ``levels / <level> / contact_force_N`` <= 1 % W/4, sum <= 1e-4 W; axial spring
  compression ``F / k_2(e_op)`` +-5 %; attitude +-0.002 deg; V13: span of the 0.1 s window
  means <= 0.1 % W/4 (contact) and attitude span <= 1e-4 deg; step standard deviations recorded
  (contact target <= 2 % of the contact force; law output ``F`` flagged above 0.1 % W/4).
* **V10**: V1 of every level vs the linear reference <= 0.1 % W/4 (the V10 row; Chrono has the
  P-delta share, rev. 22); modes 1-2 of the V7 runs +-3 % and top < middle < bottom.
* **V5**: FL +1 / +5 mm, cylinder force change per leg vs the L1-R quasi-static values
  (``L1R_rod_side_reference_rev32 / V5_V6_quasi_static / top / L1R (FL moving, others LOCK)``;
  identical to the L2b model at ``e_op``: ``s_lock = e_op``), 5 % of the largest component;
  attitude change +-5 %.
* **V6**: first leg at F_min (law output, 0.1 s centred window mean) and first unloaded pad
  (0.1 s centred window mean of the contact normal <= 0), travel = ``s_ref - s_ref0`` of the
  moving leg; leg equal, travel +-5 % (``single_leg_thresholds_mm / <test> / L1R_after_extend``).
* **V7** (5.20.9 Q1): first six LOCK modes, identified natural frequency +-3 % of ``f_damped_Hz``
  (= ``|lambda| / 2 pi``, the S2a / S4 rule), zeta **without** the ``r omega dt / 2`` correction
  +-30 %.
* **V8(a)** (5.20.9 Q1): every dashpot 0; per mode ``|zeta_fit| <= 0.1 zeta_LOCK`` (both dt) and
  bounded oscillation: modal envelope of the last 10 s / first 10 s <= 1 + :data:`V8A_GROWTH_TOL`
  (ASSUMPTION of this module; semi-implicit Euler keeps the amplitude).
* **V9**: FL +1 mm at 1e-4 / 5e-5 / 2.5e-5 s vs 1e-5 s: final force <= 0.1 % W/4, final attitude
  <= 1e-4 deg, transient extreme (RL cylinder force change) <= 1 %; error ratio of the transient
  extreme 2 +- 20 % (first order, 5.20.9 Q1).
* **V11** (legs in the air): applied reference speed ``|u| <= v_max (1 + 1e-3)`` and ``v_max``
  reached, ``s_ref`` within ``[-1e-4, stroke + 1e-4]``, full stroke rest to rest ``stroke / v_max +
  ramp`` +-0.05 s (measured on ``s_ref``: the force-law leg has no rigid motor); rod tracking
  ``s - s_ref`` recorded.
* **V11b** (5.20.9 Q2, Q5; rigid two-sided bond): per direction, saturation reached; force after
  the first saturated step <= limit x 1.01; ``s_ref`` travel after the first saturated step
  <= 0.04 mm; force change after the stop ``F_settled - F_sat`` vs ``-(c_mov v_max - k_2 v_max
  t_stop / 2)`` (-1,555 / -1,411 N front / rear, extension; sign reversed for retraction) within
  +-10 % or +-0.1 kN, whichever is larger; compression change ``dF / k_2`` recorded.
* **V12** (means over the last 3 s): contact vertical per leg +-1 % W/4; horizontal x, y +-10 % or
  +-0.2 kN; in-plane slip of the pad sphere centre < 0.1 mm.
* **V4(NSC)**: per-leg touch time (equivalent origin) vs ``V4_NSC / L2b_dynamic / touch_s``
  +-0.05 s; residual roll / pitch amplitude 15 s after the last stop < 0.001 deg; final contact vs
  V1 recorded (rod-side lock path dependence).
* **V14** (5.20.8): per case RL+ secant ``dF_RL(+1 mm)`` +-5 %, F_min and lift-off thresholds +-5 %
  with the leg equal, in-plane slip < 0.1 mm, LOCK frequencies of the six modes +-3 % (ERA of the
  modal run; the slope cases have no mode shapes in the reference).

Units SI unless named; angles in deg where the id or the name says so.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.verify.checks import CheckResult, check_abs, check_equal, check_max, check_rel

LEGS = ("FL", "FR", "RL", "RR")
REF_BLOCK = "L2b_NSC_reference_rev33"
REF = f"reference.json / {REF_BLOCK}"

PRE_REL_TOL = 1.0e-6
"""5.20.8 / 5.20.11: lock-table values vs the reference, relative 1e-6 (plus printed rounding)."""
V0_REL_TOL = 1.0e-9
V0_SIGN_TOL_M = 1.0e-9
V0_HANGING_TOL_N = 1.0
V0_MOTOR_CONSTRAINTS = 3
"""PRISMATIC 5 -> 3 with ``SetGuideConstraint(False, False, True, True, True)`` (plan S7)."""
V1_LEG_W4 = 1.0e-2
V1_SUM_REL = 1.0e-4
V2_REL = 0.05
V3_ABS_DEG = 0.002
V13_W4 = 1.0e-3
V13_ATT_DEG = 1.0e-4
V13_CONTACT_STD_REL = 0.02
"""Record target (5.20.9 Q3): PSOR step standard deviation <= 2 % of the contact force."""
V10_W4 = 1.0e-3
V5_REL = 0.05
V6_REL = 0.05
V7_F_REL = 0.03
V7_ZETA_REL = 0.30
V8A_ZETA_FACTOR = 0.1
V8A_GROWTH_TOL = 0.05
"""ASSUMPTION (this module): 'bounded oscillation' = modal peak envelope of the last 10 s at
most 5 % above that of the first 10 s (an undamped semi-implicit Euler keeps it at 1)."""
V8A_ENVELOPE_S = 10.0
V9_STATIC_W4 = 1.0e-3
V9_ATT_DEG = 1.0e-4
V9_TRANSIENT_REL = 0.01
V9_RATIO = 2.0
V9_RATIO_REL = 0.20
V11_SPEED_REL = 1.0e-3
V11_POS_MIN_M = -1.0e-4
V11_POS_MARGIN_M = 1.0e-4
V11_TIME_TOL_S = 0.05
V11B_FORCE_REL = 0.01
V11B_SREF_TRAVEL_M = 4.0e-5
V11B_DF_REL = 0.10
V11B_DF_ABS_N = 100.0
V12_VERT_W4 = 1.0e-2
V12_HOR_REL = 0.10
V12_HOR_ABS_N = 200.0
V12_SLIP_M = 1.0e-4
V4_TOUCH_TOL_S = 0.05
V4_RESIDUAL_DEG = 1.0e-3
V4_RESIDUAL_AFTER_S = 15.0
V14_REL = 0.05
V14_F_REL = 0.03
V14_SLIP_M = 1.0e-4
SECANT_START_SPAN_M = 5.0e-5
"""Travel span of the start line of :func:`secant_at` (below the first knee, >= 0.17 mm)."""


def _legs(v: ArrayLike) -> str:
    return " / ".join(f"{x:.6g}" for x in np.asarray(v, dtype=float).ravel())


# --- small analysis helpers (arrays) -----------------------------------------------------------


def printed_half_unit(value: float) -> float:
    """Half a unit in the last printed digit of ``value`` (shortest repr); 0 for 0."""
    if value == 0.0 or not math.isfinite(value):
        return 0.0
    exponent = Decimal(repr(float(value))).normalize().as_tuple().exponent
    return 0.5 * 10.0 ** int(exponent)


def printed_rel(value: float) -> float:
    """Relative printed-digit half unit of ``value``."""
    return printed_half_unit(value) / abs(value) if value else 0.0


def centred_moving_mean(t: ArrayLike, y: ArrayLike, window: int) -> tuple[NDArray, NDArray]:
    """Moving mean over ``window`` samples, assigned to the window centre time.

    Returns ``(t_centre, mean)``; ``y`` may be (n,) or (n, k).
    """
    tt = np.asarray(t, dtype=float)
    yy = np.asarray(y, dtype=float)
    one = yy.ndim == 1
    if one:
        yy = yy[:, None]
    window = int(max(1, min(window, len(tt))))
    c = np.cumsum(np.vstack([np.zeros((1, yy.shape[1])), yy]), axis=0)
    mean = (c[window:] - c[:-window]) / window
    tc = 0.5 * (tt[window - 1:] + tt[: len(tt) - window + 1])
    return tc, (mean[:, 0] if one else mean)


def first_crossing(x: ArrayLike, y: ArrayLike, level: float, *, downward: bool = True
                   ) -> float | None:
    """``x`` where ``y`` first crosses ``level`` (linear interpolation), None if never."""
    xx = np.asarray(x, dtype=float)
    yy = np.asarray(y, dtype=float) - level
    hit = np.flatnonzero(yy <= 0.0) if downward else np.flatnonzero(yy >= 0.0)
    if hit.size == 0:
        return None
    k = int(hit[0])
    if k == 0:
        return float(xx[0])
    y0, y1 = yy[k - 1], yy[k]
    frac = y0 / (y0 - y1) if y0 != y1 else 1.0
    return float(xx[k - 1] + frac * (xx[k] - xx[k - 1]))


def integrate_rotation(t: ArrayLike, omega: ArrayLike, t0: float | None = None) -> NDArray:
    """Small-angle rotation vector ``theta(t) = int omega dt`` (trapezoid), world axes.

    ``t0`` (the kick time) adds the first interval ``omega(t_first) (t_first - t0)``.
    """
    tt = np.asarray(t, dtype=float)
    w = np.asarray(omega, dtype=float)
    out = np.zeros_like(w)
    out[1:] = np.cumsum(0.5 * (w[1:] + w[:-1]) * np.diff(tt)[:, None], axis=0)
    if t0 is not None:
        out += w[0] * (tt[0] - t0)
    return out


def modal_q(t: ArrayLike, origin_m: ArrayLike, vel_m_s: ArrayLike, omega: ArrayLike,
            point_body_m: Sequence[float], rod_z_m: ArrayLike, t_kick: float | None = None
            ) -> NDArray:
    """10-coordinate displacement ``[u (3), theta (3), rod z (4)]`` of the reference block
    (``mode_shapes / coordinates``) from a level start (body axes = world axes, small angles):
    ``u = d origin + theta x p``; ``theta`` from the integrated world angular velocity; rod rows =
    vertical displacement of the pad sphere centres (up +). Displacements are taken from the
    kick time (first sample shifted back by its velocity)."""
    tt = np.asarray(t, dtype=float)
    o = np.asarray(origin_m, dtype=float)
    v = np.asarray(vel_m_s, dtype=float)
    theta = integrate_rotation(tt, omega, t_kick)
    shift = 0.0 if t_kick is None else (tt[0] - t_kick)
    d_origin = o - o[0] + v[0] * shift
    p = np.asarray(point_body_m, dtype=float)
    u = d_origin + np.cross(theta, p)
    rz = np.asarray(rod_z_m, dtype=float)
    return np.hstack([u, theta, rz - rz[0]])


def envelope_ratio(t: ArrayLike, eta: ArrayLike, span_s: float = V8A_ENVELOPE_S) -> float:
    """max |eta - mean| over the last ``span_s`` / over the first ``span_s``."""
    tt = np.asarray(t, dtype=float)
    y = np.asarray(eta, dtype=float)
    first = tt <= tt[0] + span_s
    last = tt >= tt[-1] - span_s
    y = y - np.mean(y)
    a0 = float(np.max(np.abs(y[first])))
    return float(np.max(np.abs(y[last])) / a0) if a0 > 0.0 else math.nan


# --- pre-checks --------------------------------------------------------------------------------


@dataclass(frozen=True)
class LegParameters:
    """``leg_parameters`` of the reference block (per leg in LEG_ORDER)."""

    head_area_m2: NDArray
    annulus_area_m2: NDArray
    beta_Pa: float
    l0h_m: float
    l0r_m: float
    stroke_m: float
    k_out_N_m: NDArray

    @classmethod
    def from_block(cls, block: Mapping[str, Any]) -> LegParameters:
        lp = block["leg_parameters"]
        return cls(np.asarray(lp["head_area_m2"], float), np.asarray(lp["annulus_area_m2"], float),
                   float(lp["beta_Pa"]), float(lp["head_dead_length_L0h_m"]),
                   float(lp["rod_dead_length_L0r_m"]), float(lp["stroke_m"]),
                   np.asarray(lp["k_out_N_m (series rod, frame, concrete)"], float))

    def k_h(self, i: int, s: float) -> float:
        return self.beta_Pa * self.head_area_m2[i] / (self.l0h_m + s)

    def k_r(self, i: int, s: float) -> float:
        return self.beta_Pa * self.annulus_area_m2[i] / (self.stroke_m - s + self.l0r_m)

    def k_h_bound(self, i: int, s: float) -> float:
        """Relative printed-digit bound of :meth:`k_h` (s exact)."""
        return (printed_rel(self.beta_Pa) + printed_rel(self.head_area_m2[i])
                + printed_half_unit(self.l0h_m) / (self.l0h_m + s))

    def k_r_bound(self, i: int, s: float) -> float:
        return (printed_rel(self.beta_Pa) + printed_rel(self.annulus_area_m2[i])
                + (printed_half_unit(self.stroke_m) + printed_half_unit(self.l0r_m))
                / (self.stroke_m - s + self.l0r_m))


def lock_table_checks(case: str, table: Mapping[str, Any], *, s_ref_at_lock_m: Sequence[float],
                      ref_extensions_m: Sequence[float] | None, leg_params: LegParameters,
                      locked_legs: Sequence[int], key: str = "",
                      extra_bound_m: ArrayLike | None = None) -> list[CheckResult]:
    """Pre-checks of the rod-side lock table of one run (5.20.8 condition, 5.20.11).

    Args:
        table: ``result.json / rod_side_lock_table`` (end of the run).
        s_ref_at_lock_m: The run's own ``s_ref`` when the legs locked (placement extensions).
        ref_extensions_m: Reference extensions of the case (None: skip that row).
        locked_legs: Leg indices that must be locked at the end of the run.
        extra_bound_m: Per-leg extra bound of the reference-extension row [m] (the runner
            places the legs on the slope read from the printed ``ground_roll_pitch_deg``; its
            half unit times the pad lever, :func:`slope_rounding_bound_m`).
    """
    out: list[CheckResult] = []
    s_lock = np.asarray(table["s_lock_m (s_ref at the lock instant)"], float)
    k_h = np.asarray(table["k_h_N_m"], float)
    k_r = np.asarray(table["k_r_N_m"], float)
    l0r = np.asarray(table["L0r_m"], float)
    locked = np.asarray(table["locked"], bool)
    idx = list(locked_legs)
    names = ",".join(LEGS[i] for i in idx)
    out.append(check_equal("pre", f"{case}: legs locked at the end ({names})",
                           bool(np.all(locked[idx])), True, note=f"locked {locked.tolist()}"))
    out.append(check_rel("pre", f"{case}: s_lock = own s_ref at the lock instant ({names})",
                         s_lock[idx], np.asarray(s_ref_at_lock_m, float)[idx], PRE_REL_TOL, "m",
                         note="column convention s_lock = s_ref (5.20.2 suppl. 1)"))
    if ref_extensions_m is not None:
        ref_e = np.asarray(ref_extensions_m, float)[idx]
        bound = np.array([printed_half_unit(e) for e in ref_e]) + PRE_REL_TOL * np.abs(ref_e)
        if extra_bound_m is not None:
            bound = bound + np.asarray(extra_bound_m, float)[idx]
        dev = s_lock[idx] - ref_e
        out.append(CheckResult("pre", f"{case}: s_lock vs reference extension ({names})",
                               s_lock[idx], ref_e, bound, "abs (1e-6 rel + printed half unit)",
                               "m", bool(np.all(np.abs(dev) <= bound)), ref_key=key,
                               deviation=dev))
    kh_ref = np.array([leg_params.k_h(i, s_lock[i]) for i in idx])
    kr_ref = np.array([leg_params.k_r(i, s_lock[i]) for i in idx])
    kh_tol = np.array([PRE_REL_TOL + leg_params.k_h_bound(i, s_lock[i]) for i in idx])
    kr_tol = np.array([PRE_REL_TOL + leg_params.k_r_bound(i, s_lock[i]) for i in idx])
    for label, got, ref, tol in (("k_h = beta A_p / (L0h + s_lock)", k_h[idx], kh_ref, kh_tol),
                                 ("k_r = beta A_ann / (s_max - s_lock + L0r)", k_r[idx], kr_ref,
                                  kr_tol)):
        rel = got / ref - 1.0
        out.append(CheckResult("pre", f"{case}: {label} ({names})", got, ref, tol,
                               "rel (1e-6 + printed rounding of leg_parameters)", "N/m",
                               bool(np.all(np.abs(rel) <= tol)),
                               ref_key=f"{REF} / leg_parameters", deviation=rel))
    out.append(check_abs("pre", f"{case}: L0r = reference", l0r, [leg_params.l0r_m] * len(l0r),
                         1.0e-12, "m", ref_key=f"{REF} / leg_parameters / rod_dead_length_L0r_m"))
    return out


def slope_rounding_bound_m(roll_pitch_deg: Sequence[float], pad_xy_m: ArrayLike) -> NDArray:
    """Extension change caused by the printed-digit rounding of the slope angles: the plane
    height at pad i moves by ``h_pitch |x_i - mean x| + h_roll |y_i - mean y|`` (the body height
    takes the mean shift), ``h`` = half unit of the printed angle [rad]."""
    xy = np.asarray(pad_xy_m, float)
    h_roll, h_pitch = (math.radians(printed_half_unit(float(a))) for a in roll_pitch_deg)
    return (h_pitch * np.abs(xy[:, 0] - xy[:, 0].mean())
            + h_roll * np.abs(xy[:, 1] - xy[:, 1].mean()))


def piston_checks(case: str, monitor: Mapping[str, Any]) -> list[CheckResult]:
    """5.20.11: stop-violation steps 0 on every leg (else the run is not judged)."""
    steps = np.asarray(monitor["stop_violation_steps"], float)
    return [check_max("pre", f"{case}: piston stop violations (steps per leg)", steps, 0.0,
                      "steps", note=f"piston max {_legs(monitor['piston_max_m'])} m, min "
                      f"{_legs(monitor['piston_min_m'])} m, tol {monitor['tolerance_m']} m")]


# --- V0 -----------------------------------------------------------------------------------------


def v0_checks(inventory: Mapping[str, Any], *, gravity_m_s2: Sequence[float],
              sup_mass_kg: float, sup_com_m: Sequence[float], sup_inertia: ArrayLike,
              rod_masses_kg: Sequence[float], level: str) -> list[CheckResult]:
    """Inventory vs YAML (Chrono doubles copied, relative 1e-9) and the L2b settings."""
    sup = inventory["superstructure"]
    inertia_ref = np.asarray(sup_inertia, float)
    return [
        check_abs("V0", f"{level}: gravity", inventory["gravity_m_s2"], gravity_m_s2, 1e-12,
                  "m/s^2"),
        check_rel("V0", f"{level}: superstructure mass", sup["mass_kg"], sup_mass_kg, V0_REL_TOL,
                  "kg"),
        check_abs("V0", f"{level}: superstructure CoM (body)", sup["com_body_m"], sup_com_m,
                  V0_REL_TOL, "m"),
        check_abs("V0", f"{level}: superstructure inertia about the CoM", sup["inertia_kg_m2"],
                  inertia_ref, V0_REL_TOL * float(np.abs(inertia_ref).max()), "kg m^2"),
        check_rel("V0", f"{level}: rod masses", [leg["mass_kg"] for leg in inventory["legs"]],
                  rod_masses_kg, V0_REL_TOL, "kg"),
        check_equal("V0", f"{level}: motor bilateral constraints = 3 (guide x, y free)",
                    inventory["motor_constraints"], [V0_MOTOR_CONSTRAINTS] * 4),
        check_equal("V0", f"{level}: Bullet collision system, fixed floor",
                    bool(inventory["collision_system_is_bullet"] and inventory["floor"]["fixed"]),
                    True),
    ]


def v0_sign_checks(pad_dz_m: Sequence[float], motor_ds_m: Sequence[float],
                   hanging_force_N: Sequence[float], rod_weight_N: Sequence[float]
                   ) -> list[CheckResult]:
    """Air sign test: +v_max 1 s moves the pad down by the motor travel; the hanging rod pulls."""
    ds = np.asarray(motor_ds_m, float)
    return [
        check_equal("V0", "sign: +speed extends (motor travel > 0)", bool(np.all(ds > 0)), True,
                    note=f"travel {_legs(ds)} m"),
        check_abs("V0", "sign: pad dz = -motor travel", pad_dz_m, -ds, V0_SIGN_TOL_M, "m"),
        check_abs("V0", "sign: hanging force = -m_rod g", hanging_force_N,
                  -np.asarray(rod_weight_N, float), V0_HANGING_TOL_N, "N"),
    ]


# --- V1 / V2 / V3 / V13 -------------------------------------------------------------------------


def settle_checks(level: str, still: Mapping[str, Any], ref_level: Mapping[str, Any],
                  *, key: str) -> list[CheckResult]:
    """V1 / V2 / V3 / V13(NSC) of one settle run (still window statistics of ``run_S7``)."""
    w = float(ref_level["W_total_N"])
    w4 = w / 4.0
    contact = np.asarray(still["pad_normal_mean_N"], float)
    ref_c = np.asarray(ref_level["contact_force_N (V1)"], float)
    comp = np.asarray(still["axial_spring_compression_mm"], float)
    ref_comp = np.asarray(ref_level["axial_spring_compression_mm (V2, F / k2(e_op))"], float)
    att = np.asarray(still["roll_pitch_mean_deg"], float)
    ref_att = np.asarray(ref_level["static_attitude_deg (roll, pitch) (V3)"], float)
    std_n = np.asarray(still["pad_normal_step_std_N"], float)
    std_f = np.asarray(still["cylinder_force_step_std_N"], float)
    return [
        check_abs("V1", f"{level}: contact force per leg (5 s mean of 0.1 s windows)", contact,
                  ref_c, V1_LEG_W4 * w4, "N", ref_key=f"{key} / contact_force_N (V1)",
                  note=f"tol 1 % W/4 = {V1_LEG_W4 * w4:.4g} N"),
        check_rel("V1", f"{level}: sum of contact forces vs W", float(contact.sum()), w,
                  V1_SUM_REL, "N", ref_key=f"{key} / W_total_N"),
        check_rel("V2", f"{level}: axial spring compression F / k2(e_op)", comp, ref_comp, V2_REL,
                  "mm", ref_key=f"{key} / axial_spring_compression_mm"),
        check_abs("V3", f"{level}: attitude (roll, pitch)", att, ref_att, V3_ABS_DEG, "deg",
                  ref_key=f"{key} / static_attitude_deg"),
        check_max("V13", f"{level}: contact force span of 0.1 s window means (5 s)",
                  still["pad_normal_window_span_N"], V13_W4 * w4, "N",
                  note=f"tol 0.1 % W/4 = {V13_W4 * w4:.4g} N (5.20.9 Q3)"),
        check_max("V13", f"{level}: attitude span (5 s)", still["roll_pitch_span_deg"],
                  V13_ATT_DEG, "deg"),
        check_max("info", f"{level}: contact force step std / contact force (PSOR, record)",
                  std_n / np.abs(ref_c), V13_CONTACT_STD_REL, "-",
                  note=f"std {_legs(std_n)} N"),
        check_max("info", f"{level}: law output F step std (record; > 0.1 % W/4 -> PSOR 100 / "
                  "recovery-speed runs)", std_f, V13_W4 * w4, "N",
                  note=f"window-mean span {_legs(still['cylinder_force_window_span_N'])} N"),
    ]


def v10_load_checks(contact_by_level: Mapping[str, Sequence[float]],
                    ref_by_level: Mapping[str, Sequence[float]], w_total_N: float
                    ) -> list[CheckResult]:
    """V10: V1 of each level vs the linear reference <= 0.1 % W/4 (P-delta share inside)."""
    tol = V10_W4 * w_total_N / 4.0
    return [check_abs("V10", f"{lv}: contact force per leg vs linear reference", c,
                      ref_by_level[lv], tol, "N", ref_key=f"{REF} / levels / {lv} / "
                      "contact_force_N (V1)", note=f"tol 0.1 % W/4 = {tol:.4g} N")
            for lv, c in contact_by_level.items()]


def v10_order_checks(f_by_level: Mapping[str, Sequence[float]]) -> list[CheckResult]:
    out = []
    levels = ("top", "middle", "bottom")
    for i in range(2):
        f = [float(f_by_level[lv][i]) for lv in levels]
        out.append(check_equal("V10", f"mode {i + 1} order top < middle < bottom",
                               bool(np.all(np.isfinite(f)) and np.all(np.diff(f) > 0)), True,
                               note=" / ".join(f"{v:.4f}" for v in f) + " Hz"))
    return out


# --- V5 / V6 ------------------------------------------------------------------------------------


def v5_checks(delta_mm: float, *, dF_N: Sequence[float], dF_ref_N: Sequence[float],
              datt_deg: Sequence[float], datt_ref_deg: Sequence[float], key: str
              ) -> list[CheckResult]:
    ref = np.asarray(dF_ref_N, float)
    out = [check_abs("V5", f"FL +{delta_mm:g} mm: cylinder force change per leg (5 % of max)",
                     dF_N, ref, V5_REL * float(np.abs(ref).max()), "N", ref_key=key)]
    for j, lab in enumerate(("roll", "pitch")):
        out.append(check_rel("V5", f"FL +{delta_mm:g} mm: {lab} change", float(datt_deg[j]),
                             float(datt_ref_deg[j]), V5_REL, "deg", ref_key=key))
    return out


@dataclass(frozen=True)
class ThresholdResult:
    """First F_min leg / travel and first unloaded pad / travel of a creep run."""

    f_min_leg: str | None
    f_min_mm: float | None
    liftoff_leg: str | None
    liftoff_mm: float | None


def creep_thresholds(t: ArrayLike, travel_m: ArrayLike, cylinder_force_N: ArrayLike,
                     contact_normal_N: ArrayLike, f_min_N: float, *, window: int,
                     exclude_leg: int | None = None) -> ThresholdResult:
    """Thresholds of a creep run from 0.1 s centred window means (5.20.9 Q3 noise rule).

    The moving leg is excluded from the F_min search (its force rises when it extends; with a
    retraction it can be the F_min leg, so pass ``exclude_leg=None`` then).
    """
    tc, f_mean = centred_moving_mean(t, cylinder_force_N, window)
    _, n_mean = centred_moving_mean(t, contact_normal_N, window)
    trav = np.interp(tc, np.asarray(t, float), np.asarray(travel_m, float))
    legs = [i for i in range(4) if i != exclude_leg]

    def first(values: NDArray, level: float) -> tuple[str | None, float | None]:
        best: tuple[int | None, float | None] = (None, None)
        for i in legs:
            x = first_crossing(trav, values[:, i], level)
            if x is not None and (best[1] is None or x < best[1]):
                best = (i, x)
        return (None if best[0] is None else LEGS[best[0]],
                None if best[1] is None else 1e3 * best[1])

    fl, fm = first(f_mean, f_min_N)
    ll, lm = first(n_mean, 0.0)
    return ThresholdResult(fl, fm, ll, lm)


def threshold_checks(id_: str, test: str, got: ThresholdResult, *, f_min_ref: Mapping[str, Any],
                     liftoff_ref: Mapping[str, Any], key: str) -> list[CheckResult]:
    """Leg equal and travel +-5 % for F_min and lift-off (V6, V14)."""
    nan = math.nan
    return [
        check_equal(id_, f"{test}: first leg at F_min", got.f_min_leg, f_min_ref["leg"],
                    ref_key=key),
        check_rel(id_, f"{test}: travel at F_min", nan if got.f_min_mm is None else got.f_min_mm,
                  float(f_min_ref["value"]), V6_REL, "mm", ref_key=key),
        check_equal(id_, f"{test}: first unloaded pad", got.liftoff_leg, liftoff_ref["leg"],
                    ref_key=key),
        check_rel(id_, f"{test}: travel at lift-off",
                  nan if got.liftoff_mm is None else got.liftoff_mm,
                  float(liftoff_ref["value"]), V6_REL, "mm", ref_key=key),
    ]


# --- V7 / V8(a) / V14 modes ----------------------------------------------------------------------


@dataclass(frozen=True)
class ModeId:
    """Identified mode (1-based ``mode``): natural frequency ``f_d / sqrt(1 - zeta^2)``."""

    mode: int
    f_Hz: float
    zeta: float
    source: str
    note: str = ""


def mode_checks(id_: str, label: str, rows: Sequence[ModeId], *, f_ref_Hz: Sequence[float],
                zeta_ref: Sequence[float] | None, key_f: str, key_zeta: str = "",
                f_tol: float = V7_F_REL) -> list[CheckResult]:
    """Frequency +-``f_tol`` and (if given) zeta +-30 % without numerical-damping correction."""
    out: list[CheckResult] = []
    for r in rows:
        i = r.mode - 1
        out.append(check_rel(id_, f"{label}: mode {r.mode} natural frequency ({r.source})",
                             r.f_Hz, float(f_ref_Hz[i]), f_tol, "Hz", ref_key=key_f,
                             note=r.note))
        if zeta_ref is not None:
            out.append(check_rel(id_, f"{label}: mode {r.mode} zeta, no r omega dt / 2 "
                                 f"correction ({r.source})", r.zeta, float(zeta_ref[i]),
                                 V7_ZETA_REL, "-", ref_key=key_zeta,
                                 note="explicit springs: no numerical damping (5.20.9 Q1)"))
    return out


def v8a_checks(dt_s: float, rows: Sequence[ModeId], growth: Sequence[float],
               zeta_ref: Sequence[float], *, key: str) -> list[CheckResult]:
    """V8(a) of one dt: per mode ``|zeta_fit| <= 0.1 zeta`` and envelope ratio <= 1.05."""
    out: list[CheckResult] = []
    for r, g in zip(rows, growth, strict=True):
        lim = V8A_ZETA_FACTOR * float(zeta_ref[r.mode - 1])
        out.append(check_max("V8a", f"dt {dt_s:g} s: mode {r.mode} |zeta_num| <= 0.1 zeta",
                             abs(r.zeta), lim, "-", ref_key=key,
                             note=f"zeta_fit {r.zeta:.3g} ({r.source}), f {r.f_Hz:.4f} Hz"))
        out.append(check_max("V8a", f"dt {dt_s:g} s: mode {r.mode} bounded oscillation "
                             "(envelope last / first 10 s)", g, 1.0 + V8A_GROWTH_TOL, "-",
                             note="ASSUMPTION tolerance of this module"))
    return out


# --- V9 -----------------------------------------------------------------------------------------


def v9_checks(*, final_force_N: Mapping[float, Sequence[float]],
              final_att_deg: Mapping[float, Sequence[float]],
              transient_N: Mapping[float, float], ref_dt_s: float, w_total_N: float
              ) -> list[CheckResult]:
    """Differences vs the reference dt and the error ratio of the transient extreme."""
    out: list[CheckResult] = []
    w4 = w_total_N / 4.0
    for dt in sorted(final_force_N, reverse=True):
        if dt == ref_dt_s:
            continue
        out.append(check_abs("V9", f"final cylinder force, dt {dt:g} vs {ref_dt_s:g} s",
                             final_force_N[dt], final_force_N[ref_dt_s], V9_STATIC_W4 * w4, "N"))
        out.append(check_abs("V9", f"final attitude, dt {dt:g} vs {ref_dt_s:g} s",
                             final_att_deg[dt], final_att_deg[ref_dt_s], V9_ATT_DEG, "deg"))
        out.append(check_rel("V9", f"transient extreme (RL dF), dt {dt:g} vs {ref_dt_s:g} s",
                             transient_N[dt], transient_N[ref_dt_s], V9_TRANSIENT_REL, "N"))
    dts = sorted((d for d in transient_N if d != ref_dt_s), reverse=True)[:3]
    if len(dts) == 3:
        a, b, c = (transient_N[d] for d in dts)
        ratio = (a - b) / (b - c) if b != c else math.nan
        out.append(CheckResult(
            "V9", f"error ratio of the transient extreme (dt {dts[0]:g}/{dts[1]:g}/{dts[2]:g} s)",
            ratio, V9_RATIO, V9_RATIO_REL, "rel", "1",
            bool(math.isfinite(ratio) and abs(ratio - V9_RATIO) <= V9_RATIO_REL * V9_RATIO),
            note=f"differences {a - b:.4e}, {b - c:.4e} N"))
    return out


# --- V11 / V11b ---------------------------------------------------------------------------------


def v11_checks(*, v_max: float, max_abs_u: Sequence[float], reach_legs: Sequence[bool],
               s_ref_min: float, s_ref_max: float, stroke_m: float,
               stroke_times_s: Mapping[str, float], expected_time_s: float,
               tracking_max_m: Sequence[float]) -> list[CheckResult]:
    """V11 on the reference ``s_ref`` / applied speed ``u`` (no rigid motor in L2b)."""
    u = np.asarray(max_abs_u, float)
    reach = [float(x) for x, r in zip(u, reach_legs, strict=True) if r]
    times = np.array(list(stroke_times_s.values()), float)
    hi = stroke_m + V11_POS_MARGIN_M
    return [
        check_max("V11", "applied speed <= v_max (1 + 1e-3)", u, v_max * (1 + V11_SPEED_REL),
                  "m/s"),
        check_abs("V11", "applied speed reaches v_max", reach, [v_max] * len(reach),
                  v_max * V11_SPEED_REL, "m/s"),
        check_equal("V11", f"s_ref within [{V11_POS_MIN_M:g}, {hi:.4f}] m",
                    bool(s_ref_min >= V11_POS_MIN_M and s_ref_max <= hi), True,
                    note=f"min {s_ref_min!r}, max {s_ref_max!r}"),
        check_abs("V11", "full stroke rest to rest (s_ref) = stroke / v_max + ramp", times,
                  [expected_time_s] * len(times), V11_TIME_TOL_S, "s",
                  note=f"keys {list(stroke_times_s)}"),
        check_max("info", "rod tracking |s - s_ref - hanging offset| max (record)",
                  tracking_max_m, math.inf, "m"),
    ]


@dataclass(frozen=True)
class V11bPhase:
    """One saturation phase of the single-leg run (5.20.9 Q2)."""

    direction: int
    """+1 extension, -1 retraction."""
    saturated: bool
    f_sat_N: float
    """Force (that acted) at the first saturated step."""
    f_max_abs_after_N: float
    s_ref_travel_after_m: float
    f_settled_N: float
    """Mean force over the last ``settle_s`` of the phase."""
    compression_change_m: float


def v11b_phase(t: ArrayLike, force_N: ArrayLike, s_ref_m: ArrayLike, saturated: ArrayLike,
               motor_pos_m: ArrayLike, *, t0: float, t1: float, direction: int, k2_N_m: float,
               settle_s: float = 0.1) -> V11bPhase:
    """Analyse one commanded phase ``[t0, t1)`` of the V11b run."""
    tt = np.asarray(t, float)
    m = (tt > t0) & (tt <= t1)
    f = np.asarray(force_N, float)[m]
    sr = np.asarray(s_ref_m, float)[m]
    sat = np.asarray(saturated, bool)[m]
    sp = np.asarray(motor_pos_m, float)[m]
    tp = tt[m]
    if not sat.any():
        return V11bPhase(direction, False, math.nan, math.nan, math.nan, math.nan, math.nan)
    k = int(np.flatnonzero(sat)[0])
    late = tp >= tp[-1] - settle_s
    f_settled = float(np.mean(f[late]))
    comp_sat = sr[k] - sp[k]
    comp_end = float(np.mean(sr[late] - sp[late]))
    return V11bPhase(direction, True, float(f[k]), float(np.max(np.abs(f[k:]))),
                     float(direction * (sr[-1] - sr[k])), f_settled, comp_end - comp_sat)


def v11b_expected_dF(c_move: float, k2: float, v_max: float, t_stop: float) -> float:
    """Extension: ``-c_mov v_max + k_2 v_max t_stop / 2`` (5.20.9 Q2 (b))."""
    return -c_move * v_max + k2 * v_max * t_stop / 2.0


def v11b_creep_bound_m(c_move: float, k2: float, v_max: float, dt_s: float) -> float:
    """L1 rev. 23 creep bound from the first saturated step: ``c v_max / k + v_max dt + 0.01 mm``
    (5.10). S7 judgement (rev. 34): law C re-arms while the command persists, so the reference
    creeps until the spring alone carries the limit (the moving-damper share ``c_mov v_max``)."""
    return c_move * v_max / k2 + v_max * dt_s + 1.0e-5


def v11b_checks(leg: str, phase: V11bPhase, *, limit_N: float, expected_dF_N: float,
                key: str, creep_bound_m: float | None = None) -> list[CheckResult]:
    """V11b of one direction (rev. 34 rule; the 5.20.9 Q2 latched-stop rows are information).

    Judged: saturation reached; ``|F|`` after the first saturated step <= limit x 1.01; settled
    mean ``|F|`` / limit in 0.99-1.01 (last 0.1 s of the phase); ``s_ref`` creep <=
    ``creep_bound_m`` (:func:`v11b_creep_bound_m`; None = 0.04 mm). Information: the Q2 (a)
    0.04 mm row and the Q2 (b) force drop (they assumed a latched stop)."""
    name = "extend" if phase.direction > 0 else "retract"
    tag = f"{leg} {name}"
    exp = phase.direction * expected_dF_N
    tol = max(V11B_DF_REL * abs(exp), V11B_DF_ABS_N)
    out = [check_equal("V11b", f"{tag}: saturation reached", phase.saturated, True)]
    if not phase.saturated:
        return out
    bound = V11B_SREF_TRAVEL_M if creep_bound_m is None else creep_bound_m
    lo, hi = 1.0 - V11B_FORCE_REL, 1.0 + V11B_FORCE_REL
    ratio = abs(phase.f_settled_N) / limit_N
    out += [
        check_max("V11b", f"{tag}: |F| after the first saturated step / limit",
                  phase.f_max_abs_after_N / limit_N, hi, "-", ref_key=key,
                  note=f"limit {limit_N:.6g} N, F_sat {phase.f_sat_N:.6g} N"),
        CheckResult("V11b", f"{tag}: settled mean |F| / limit (last 0.1 s)", ratio, 1.0,
                    [lo, hi], "band", "-", bool(lo <= ratio <= hi), ref_key=key),
        check_max("V11b", f"{tag}: s_ref creep after the first saturated step",
                  phase.s_ref_travel_after_m, bound, "m",
                  note="bound c_mov v_max / k2 + v_max dt + 0.01 mm (L1 rev. 23 form, rev. 34)"),
        check_max("info", f"{tag}: s_ref travel vs 5.20.9 Q2 (a) 0.04 mm (latched stop, record)",
                  phase.s_ref_travel_after_m, V11B_SREF_TRAVEL_M, "m"),
        check_abs("info", f"{tag}: force change after the stop vs 5.20.9 Q2 (b) (latched stop, "
                  "record)", phase.f_settled_N - phase.f_sat_N, exp, tol, "N",
                  ref_key="dynamics_model.md 5.20.9 Q2 (b)",
                  note=f"expected {exp:.1f} N if the stop latched; law C re-arms instead"),
        check_max("info", f"{tag}: compression change dF / k2 (record, 'creep' of cad)",
                  abs(phase.compression_change_m), math.inf, "m",
                  note=f"signed {phase.compression_change_m:.4g} m"),
    ]
    return out


# --- V12 / V14 slip -----------------------------------------------------------------------------


def in_plane(vec: ArrayLike, normal: Sequence[float]) -> NDArray:
    v = np.asarray(vec, float)
    n = np.asarray(normal, float)
    n = n / np.linalg.norm(n)
    return v - np.outer(v @ n, n) if v.ndim == 2 else v - (v @ n) * n


def v12_checks(case: str, *, contact_world_N: ArrayLike, ref: Mapping[str, Any],
               slip_in_plane_m: ArrayLike, w_total_N: float, key: str) -> list[CheckResult]:
    """V12: vertical +-1 % W/4, horizontal +-10 % or 0.2 kN, in-plane slip < 0.1 mm."""
    c = np.asarray(contact_world_N, float)
    w4 = w_total_N / 4.0
    vert_ref = np.asarray(ref["contact_vertical_N"], float)
    hor_ref = np.asarray(ref["contact_horizontal_xy_N"], float)
    hor = c[:, :2]
    tol_h = np.maximum(V12_HOR_REL * np.abs(hor_ref), V12_HOR_ABS_N)
    dev = hor - hor_ref
    slip = np.linalg.norm(np.asarray(slip_in_plane_m, float), axis=1)
    return [
        check_abs("V12", f"{case}: contact vertical per leg", c[:, 2], vert_ref,
                  V12_VERT_W4 * w4, "N", ref_key=f"{key} / contact_vertical_N"),
        CheckResult("V12", f"{case}: contact horizontal x, y per leg", hor, hor_ref, tol_h,
                    "abs (max(10 %, 0.2 kN))", "N", bool(np.all(np.abs(dev) <= tol_h)),
                    ref_key=f"{key} / contact_horizontal_xy_N", deviation=dev),
        check_max("V12", f"{case}: in-plane slip of the pad sphere centre", slip, V12_SLIP_M,
                  "m"),
    ]


# --- V4 -----------------------------------------------------------------------------------------


def v4_checks(touch_s: Sequence[float | None], ref_touch_s: Sequence[float], *,
              residual_amp_deg: Sequence[float], key: str) -> list[CheckResult]:
    t = np.array([math.nan if x is None else x for x in touch_s], float)
    return [
        check_abs("V4", "touch time per leg (equivalent origin)", t, ref_touch_s, V4_TOUCH_TOL_S,
                  "s", ref_key=key, note="L2b dynamic 3-DoF reference (5.20.6)"),
        check_max("V4", f"roll / pitch residual amplitude {V4_RESIDUAL_AFTER_S:g} s after the "
                  "last stop", residual_amp_deg, V4_RESIDUAL_DEG, "deg"),
    ]


# --- V14 ----------------------------------------------------------------------------------------


def secant_at(travel_m: ArrayLike, force_N: ArrayLike, delta_m: float, t: ArrayLike,
              window: int) -> NDArray:
    """Window-mean cylinder force change at travel ``delta_m`` from the creep start (per leg).

    The force at zero travel is the straight line through the window means of the first
    :data:`SECANT_START_SPAN_M` of travel, evaluated at 0 (the first window centre is already
    half a window into the motion)."""
    tc, fm = centred_moving_mean(t, force_N, window)
    trav = np.interp(tc, np.asarray(t, float), np.asarray(travel_m, float))
    start = trav <= trav[0] + SECANT_START_SPAN_M
    if np.count_nonzero(start) >= 2 and np.ptp(trav[start]) > 0.0:
        f0 = np.array([np.polyval(np.polyfit(trav[start], fm[start, i], 1), 0.0)
                       for i in range(fm.shape[1])])
    else:
        f0 = fm[0]
    out = np.array([np.interp(delta_m, trav, fm[:, i]) for i in range(fm.shape[1])])
    return out - f0


def v14_checks(case: str, *, secant_N: Sequence[float], thresholds: ThresholdResult,
               ref: Mapping[str, Any], slip_m: Sequence[float], key: str) -> list[CheckResult]:
    sec_ref = np.asarray(ref["dF_cyl_secant_+1mm_N (judged, crosses the knees)"], float)
    sec = np.asarray(secant_N, float)
    out = [
        check_rel("V14", f"{case}: RL+ secant dF_RL (+1 mm)", float(sec[2]), float(sec_ref[2]),
                  V14_REL, "N", ref_key=key, note=f"all legs {_legs(sec)} / ref {_legs(sec_ref)}"),
    ]
    out += threshold_checks("V14", f"{case} RL+", thresholds,
                            f_min_ref=ref["F_min_threshold_mm"],
                            liftoff_ref=ref["liftoff_threshold_mm"], key=key)
    out.append(check_max("V14", f"{case}: in-plane contact slip (settle + creep to F_min)",
                         slip_m, V14_SLIP_M, "m",
                         note="centre motion minus the rolling lever dtheta x r n"))
    return out


def summarize_ids(checks: Sequence[Mapping[str, Any]]) -> dict[str, bool]:
    """``{id: all passed}`` of JSON rows (``info`` excluded)."""
    out: dict[str, bool] = {}
    for c in checks:
        if c["id"] == "info":
            continue
        out[c["id"]] = out.get(c["id"], True) and bool(c["passed"])
    return out


__all__ = [
    "LEGS", "REF", "REF_BLOCK", "LegParameters", "ModeId", "ThresholdResult", "V11bPhase",
    "centred_moving_mean", "creep_thresholds", "envelope_ratio", "first_crossing", "in_plane",
    "integrate_rotation", "lock_table_checks", "modal_q", "mode_checks", "piston_checks",
    "printed_half_unit", "printed_rel", "secant_at", "settle_checks", "summarize_ids",
    "threshold_checks", "v0_checks", "v0_sign_checks", "v10_load_checks", "v10_order_checks",
    "v11_checks", "v11b_checks", "v11b_creep_bound_m", "v11b_expected_dF", "v11b_phase",
    "slope_rounding_bound_m", "v12_checks", "v14_checks",
    "v4_checks", "v5_checks", "v8a_checks", "v9_checks",
]
