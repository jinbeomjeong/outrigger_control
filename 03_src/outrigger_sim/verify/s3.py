"""S3 V checks (engine independent): V8(a) numerical damping, V4 lift, V5, V6, V9 convergence.

``00_docs/03_chrono/chrono_build_plan.md`` S3; ``dynamics_model.md`` 5 (V1, V3, V4, V5, V6,
V8, V9, V13), 5.5 (V8(a) reduced role), 5.6 (V4 time origin = start command + ramp / 2, ramped
stops), 5.7 rev. 17 (crawler V8(a) judged on modal zeta + energy trend, max(E - E0) recorded;
V9 V4 judged on the geometric touch time, R15 touch recorded). Automatic pass / fail is a
pre-check; the physical judgement is the dynamics-expert's. L1-R runs (locked rod-side chamber)
judge V5 on the module normal force against the ``L1R_rod_side_reference_rev32`` block
(:func:`v5_l1r_checks`, dynamics_model.md 5.14.8 / 5.17.5); V6 keeps :func:`v6_checks` with the
L1-R thresholds of that block.

Tolerances (named constants below) come from those tables; ASSUMPTION marks a choice of this
module where the documents leave it open.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from numpy.typing import ArrayLike

from outrigger_sim.params import LEG_ORDER
from outrigger_sim.verify.checks import (
    CheckResult,
    check_abs,
    check_equal,
    check_max,
    check_rel,
)

# --- V8(a) -----------------------------------------------------------------------------------
V8A_ENERGY_RISE_REL_MAX = 0.01
"""max(E - E0) / E_kin0 <= 1 % (dynamics_model.md 5 V8 (a)); judged for the pad case only,
recorded for the crawler case (5.7 (a))."""
V8A_CRAWLER_TREND_REL_MAX = 0.01
"""Crawler V8(a): linear trend of the 1-s block means of (E - E0) / E_kin0 over the 60 s window
<= +1 % (dynamics_model.md 5.7 (a), dyn decision rev. 17)."""
V8A_ZETA_NUM_LIMIT_FACTOR = 0.1
"""zeta_num_i <= 0.1 zeta_i (modes 1-6)."""
V8A_MODE3_PRED_BAND = (0.7, 1.3)
"""Mode 3 zeta_num / (r3 omega3 dt / 2): recorded (met in S2a, 5.5), not judged."""

# --- V4 ----------------------------------------------------------------------------------------
V4_TOUCH_TOL_S = 0.05
V4_RESIDUAL_AMPLITUDE_MAX_DEG = 1.0e-3
V4_ENVELOPE_ZETA_REL_TOL = 0.30
V4_PEAK_REFERENCE_REL_BAND = 0.15
"""Dynamic peak vs the 3-DoF reference: recorded only (user decision 2026-10-20, option 2)."""
V1_PER_LEG_TOL_FRACTION_OF_W4 = 0.01
V1_SUM_REL_TOL = 1.0e-4
V3_ATTITUDE_TOL_DEG = 0.002
V13_MOTOR_VIOLATION_MAX_M = 1.0e-6
V4_JUDGED_RUN = "v4_D_wdefault"
"""V4 lift run the S3 judgement rests on: YAML ``simulation.L1.dt_s`` (2e-4 s since the
2026-10-21 regeneration) outside the ``simulation.dt_transition_s`` (1e-5 s) window."""
V4_PREVIOUS_JUDGED_RUN = "v4_D_w1e-04"
"""Judged run of the first S3 batch (1e-4 s outside the same window); comparison record only."""

# --- V5, V6 -----------------------------------------------------------------------------------
V5_REL_TOL = 0.05
V6_REL_TOL = 0.05

# --- V9 ----------------------------------------------------------------------------------------
V9_STATIC_TOL_FRACTION_OF_W4 = 0.001
V9_ATTITUDE_TOL_DEG = 1.0e-4
V9_TRANSIENT_REL_TOL = 0.01
V9_ORDER_RATIO = 2.0
V9_ORDER_RATIO_REL_TOL = 0.20
V9_V4_TOUCH_QUANTUM_S = 1.0e-4
"""V9 V4 geometric touch time (sphere bottom crossing the floor, interpolated) against the
reference dt: <= 1e-4 s for every dt (dynamics_model.md 5.7 (b), rev. 17). The R15 touch time
(end of the first N > 0 step) is recorded only: its detection lag is (1, 2] dt, so it differs
from the reference by up to ``2 dt - dt_ref`` plus the geometric difference (5.7 (b), (c))."""


def _legs(values: ArrayLike) -> list[float]:
    return [float(v) for v in np.asarray(values, dtype=float).reshape(-1)]


# --- V8(a) -----------------------------------------------------------------------------------


def v8a_checks(
    name: str,
    *,
    dt_s: float,
    energy_rise_rel: float,
    zeta_num_fit: Sequence[float],
    zeta_ref: Sequence[float],
    zeta_pred: Sequence[float] | None,
    key_zeta: str,
    yield_steps: Sequence[int],
    n_events: int,
    modes: bool = True,
    energy_rise_judged: bool = True,
) -> list[CheckResult]:
    """V8(a) of one run (``modes`` False: no pad-mode zeta items, e.g. the crawler case).

    Args:
        energy_rise_rel: ``max(E - E0) / E_kin0`` over the run (positive = rise); judged when
            ``energy_rise_judged`` (pad case), otherwise left to the caller's record (crawler
            case, dynamics_model.md 5.7 (a)).
        zeta_num_fit: Identified damping per mode with every physical damping off (= numerical).
        zeta_ref: Configured physical zeta per mode (limit = 0.1 x).
        zeta_pred: ``r_i omega_i dt / 2`` at ``dt_s`` (recorded ratio), or None.
    """
    out = []
    if energy_rise_judged:
        out.append(
            check_max(
                "V8a",
                f"{name}: energy rise max(E - E0) / E_kin0 (dt {dt_s:g} s)",
                max(energy_rise_rel, 0.0),
                V8A_ENERGY_RISE_REL_MAX,
                "1",
                note=f"signed value {energy_rise_rel:.3e} (negative = no rise)",
            )
        )
    out += [
        check_equal(
            "V8a", f"{name}: no bushing yield (small amplitude)", _legs(yield_steps), [0] * 4
        ),
        check_equal("V8a", f"{name}: no R15 events", n_events, 0),
    ]
    if not modes:
        return out
    zref = np.asarray(zeta_ref, dtype=float)
    zfit = np.asarray(zeta_num_fit, dtype=float)
    for i in range(len(zref)):
        limit = V8A_ZETA_NUM_LIMIT_FACTOR * float(zref[i])
        note = "mode 1: upper bound only" if i == 0 else ""
        if zeta_pred is not None:
            ratio = float(zfit[i]) / float(zeta_pred[i]) if zeta_pred[i] else math.nan
            note = (note + "; " if note else "") + f"zeta_num / (r omega dt / 2) = {ratio:.3f}"
        out.append(
            check_max(
                "V8a",
                f"{name}: mode {i + 1} zeta_num <= 0.1 zeta (dt {dt_s:g} s)",
                max(float(zfit[i]), 0.0),
                limit,
                "1",
                ref_key=key_zeta,
                note=note + f"; signed fit {float(zfit[i]):.4e}",
            )
        )
    return out


V8A_CRAWLER_NEG_ZETA_FRACTION = 0.01
"""Crawler V8(a) modal check: identified zeta with every physical damping off must not be below
-1 % of the physical zeta of that mode (energy gain < 1 % of the physical dissipation rate).
ASSUMPTION threshold, adopted as the judged quantity by dyn (dynamics_model.md 5.7 (a),
rev. 17)."""


def v8a_crawler_modal_checks(
    name: str, modes: Sequence[Mapping[str, Any]], zeta_physical: Mapping[str, float]
) -> list[CheckResult]:
    """Crawler V8(a): modal zeta (heave, roll, pitch) with damping off >= -1 % physical zeta."""
    out = []
    for m in modes:
        zp = float(zeta_physical[m["mode"]])
        z = float(m["zeta_fit"])
        out.append(
            CheckResult(
                "V8a",
                f"{name}: crawler {m['mode']} zeta with damping off >= -1 % physical zeta "
                "(no energy injection by the explicit SMC contact)",
                z,
                -V8A_CRAWLER_NEG_ZETA_FRACTION * zp,
                V8A_CRAWLER_NEG_ZETA_FRACTION,
                "min",
                "1",
                bool(math.isfinite(z) and z >= -V8A_CRAWLER_NEG_ZETA_FRACTION * zp),
                note=f"physical zeta {zp:.4g}; ASSUMPTION threshold (dynamics_model.md 5.7 (a))",
            )
        )
    return out


def v8a_crawler_checks(
    name: str,
    *,
    dt_s: float,
    energy_rise_rel: float,
    energy_trend_rel_over_window: float,
    window_s: float,
    modes: Sequence[Mapping[str, Any]],
    zeta_physical: Mapping[str, float],
    n_events: int,
) -> tuple[list[CheckResult], dict[str, Any]]:
    """Crawler V8(a) (dynamics_model.md 5.7 (a), rev. 17).

    Judged: modal zeta with every physical damping off >= -1 % physical zeta (heave, roll,
    pitch), trend of the 1-s block means over the window <= +1 % ``E_kin0``, no R15 events.
    Recorded: ``max(E - E0) / E_kin0`` (the plan's literal wording; it is the sum of the trend,
    the bounded semi-implicit Euler oscillation and float32 contact-geometry residuals at this
    small ``E_kin0``).

    Returns:
        ``(checks, recorded)``.
    """
    checks = v8a_checks(
        name,
        dt_s=dt_s,
        energy_rise_rel=energy_rise_rel,
        zeta_num_fit=[],
        zeta_ref=[],
        zeta_pred=None,
        key_zeta="",
        yield_steps=[0, 0, 0, 0],
        n_events=n_events,
        modes=False,
        energy_rise_judged=False,
    )
    checks += v8a_crawler_modal_checks(name, modes, zeta_physical)
    checks.append(
        check_max(
            "V8a",
            f"{name}: energy trend of 1-s block means over {window_s:g} s / E_kin0 "
            f"(dt {dt_s:g} s)",
            float(energy_trend_rel_over_window),
            V8A_CRAWLER_TREND_REL_MAX,
            "1",
            note="dynamics_model.md 5.7 (a): judged together with the modal zeta",
        )
    )
    recorded = {
        "energy_rise_rel_geometric (max(E - E0) / E_kin0, recorded)": float(energy_rise_rel),
        "limit_of_the_old_wording": V8A_ENERGY_RISE_REL_MAX,
        "note": "recorded only since rev. 17 (dynamics_model.md 5.7 (a)): at E_kin0 3.25 J the "
        "1 % band is the size of the bounded integrator oscillation and float32 contact "
        "residuals; energy injection shows as negative modal zeta (judged)",
    }
    return checks, recorded


def touch_geometric_checks(
    touch_by_dt: Mapping[float, Sequence[float]], ref_dt_s: float
) -> list[CheckResult]:
    """V9 V4 touch (judged, dynamics_model.md 5.7 (b)): geometric touch (sphere bottom
    crossing the floor, interpolated) against the reference dt within
    ``V9_V4_TOUCH_QUANTUM_S`` = 1e-4 s for every dt (no detection lag in it)."""
    ref = np.asarray(touch_by_dt[ref_dt_s], dtype=float)
    return [
        check_abs(
            "V9",
            f"V4 geometric touch time, dt {dt:g} vs {ref_dt_s:g} s (FL, FR, RL, RR)",
            touch,
            ref,
            V9_V4_TOUCH_QUANTUM_S,
            "s",
            note="R15 touch (first N > 0 step) lags the geometric crossing by 1-2 dt "
            "(explicit contact: detection at step start, force at step end)",
        )
        for dt, touch in touch_by_dt.items()
        if dt != ref_dt_s
    ]


# --- V4 ----------------------------------------------------------------------------------------


def v4_checks(
    name: str,
    *,
    touch_eq_s: Sequence[float],
    touch_ref_s: Sequence[float],
    key_touch: str,
    max_cylinder_force_N: Sequence[float],
    force_limit_N: float,
    key_force_limit: str,
    contact_force_mean_N: Sequence[float],
    contact_force_ref_N: Sequence[float],
    key_contact: str,
    total_weight_N: float,
    attitude_mean_deg: Sequence[float],
    attitude_ref_deg: Sequence[float],
    key_attitude: str,
    residual_amplitude_deg: Sequence[float],
    envelope_zeta: Mapping[str, Sequence[float]] | None,
    motor_violation_max_m: float,
    events: Sequence[Sequence[float]],
    any_nan: bool,
) -> list[CheckResult]:
    """V4 lift (rev. 15 time origin), V1 / V3 after the last stop, V13 health.

    Args:
        touch_eq_s: Per-leg first ``N > 0`` step time from the equivalent origin.
        envelope_zeta: ``{"mode k": (zeta_fit_corrected, zeta_ref)}`` for the residual
            rocking (judged +-30 %), or None.
        events: R15 events ``(t, leg, kind)`` of the run.
    """
    w4 = total_weight_N / 4.0
    out = [
        check_abs(
            "V4",
            f"{name}: touch time per leg from start command + ramp/2 (FL, FR, RL, RR)",
            touch_eq_s,
            touch_ref_s,
            V4_TOUCH_TOL_S,
            "s",
            ref_key=key_touch,
        ),
        check_max(
            "V4",
            f"{name}: max cylinder force per leg < moving saturation (no saturation)",
            max_cylinder_force_N,
            force_limit_N,
            "N",
            ref_key=key_force_limit,
        ),
        check_abs(
            "V1",
            f"{name}: contact force after the last stop, per leg",
            contact_force_mean_N,
            contact_force_ref_N,
            V1_PER_LEG_TOL_FRACTION_OF_W4 * w4,
            "N",
            ref_key=key_contact,
        ),
        check_rel(
            "V1",
            f"{name}: contact force sum after the last stop",
            float(np.sum(contact_force_mean_N)),
            float(np.sum(contact_force_ref_N)),
            V1_SUM_REL_TOL,
            "N",
            ref_key=key_contact,
        ),
        check_abs(
            "V3",
            f"{name}: attitude (roll, pitch) after the last stop",
            attitude_mean_deg,
            attitude_ref_deg,
            V3_ATTITUDE_TOL_DEG,
            "deg",
            ref_key=key_attitude,
        ),
        check_max(
            "V4",
            f"{name}: residual rocking (roll, pitch) 15 s after the last stop, half peak-to-peak "
            "over one first-rocking period",
            residual_amplitude_deg,
            V4_RESIDUAL_AMPLITUDE_MAX_DEG,
            "deg",
        ),
        check_max("V13", f"{name}: axial motor constraint violation", motor_violation_max_m,
                  V13_MOTOR_VIOLATION_MAX_M, "m"),
        check_equal("V13", f"{name}: no NaN", any_nan, False),
    ]
    created = sorted(int(e[1]) for e in events if int(e[2]) == 1)
    removed = [int(e[1]) for e in events if int(e[2]) == 2]
    out.append(
        check_equal("V4", f"{name}: one bushing creation per leg (R15)", created, [0, 1, 2, 3])
    )
    out.append(
        check_equal(
            "V4", f"{name}: bushing removals (contact loss after touch)", len(removed), 0
        )
    )
    if envelope_zeta:
        for mode, (z, zr) in envelope_zeta.items():
            out.append(
                check_rel(
                    "V4",
                    f"{name}: residual rocking envelope zeta, {mode} (zeta_num subtracted)",
                    float(z),
                    float(zr),
                    V4_ENVELOPE_ZETA_REL_TOL,
                    "1",
                )
            )
    return out


def v4_record_items(
    *,
    peak_pad_force_N: Sequence[float],
    peak_ref_N: Sequence[float],
) -> dict[str, Any]:
    """Recorded (not judged) V4 values: dynamic peak vs the 3-DoF reference (+-15 %)."""
    peak = np.asarray(peak_pad_force_N, dtype=float)
    ref = np.asarray(peak_ref_N, dtype=float)
    rel = (peak - ref) / ref
    return {
        "peak_pad_force_N": peak.tolist(),
        "reference_peak_N": ref.tolist(),
        "relative_difference": rel.tolist(),
        "within_15_percent": [bool(abs(r) <= V4_PEAK_REFERENCE_REL_BAND) for r in rel],
    }


def _nested_value(result: Mapping[str, Any], keys: Sequence[str]) -> Any:
    value: Any = result
    for key in keys:
        value = value[key]
    return value


def _leg_difference(
    judged: Mapping[str, Any], previous: Mapping[str, Any], *keys: str
) -> list[float]:
    judged_values = np.asarray(_nested_value(judged, keys), dtype=float)
    previous_values = np.asarray(_nested_value(previous, keys), dtype=float)
    return _legs(judged_values - previous_values)


def v4_judged_run_comparison(
    judged: Mapping[str, Any], previous: Mapping[str, Any]
) -> dict[str, Any]:
    """Recorded (not judged) differences of the judged V4 run from the previous judged run.

    Args:
        judged: ``result.json`` values of :data:`V4_JUDGED_RUN`.
        previous: ``result.json`` values of :data:`V4_PREVIOUS_JUDGED_RUN`.

    Returns:
        Time steps of both runs and judged minus previous (per leg in ``LEG_ORDER``): touch
        and crawler-off times (ms), peak cylinder force, final contact force (N), final
        attitude (roll, pitch; deg).
    """
    touch_ms = 1e3 * np.asarray(_leg_difference(judged, previous, "touch_eq_s"))
    crawler_off_ms = 1e3 * (float(judged["crawler_off_eq_s"]) - previous["crawler_off_eq_s"])
    return {
        "legs": list(LEG_ORDER),
        "dt_s": {"judged": judged["dt_s"], "previous": previous["dt_s"]},
        "touch_eq_minus_previous_ms": _legs(touch_ms),
        "crawler_off_eq_minus_previous_ms": crawler_off_ms,
        "peak_cylinder_force_minus_previous_N": _leg_difference(
            judged, previous, "peak_cylinder_force_N"
        ),
        "final_contact_force_minus_previous_N": _leg_difference(
            judged, previous, "final", "contact_force_N"
        ),
        "final_attitude_minus_previous_deg": _leg_difference(
            judged, previous, "final", "attitude_deg"
        ),
    }


# --- V5 ----------------------------------------------------------------------------------------


def v5_checks(
    delta_mm: float,
    *,
    dF_N: Sequence[float],
    dF_per_mm_ref_N: Sequence[float],
    key_dF: str,
    dattitude_deg: Sequence[float],
    dattitude_per_mm_ref_deg: Sequence[float],
    key_att: str,
) -> list[CheckResult]:
    """V5: FL +``delta_mm``; tolerance 5 % of the largest reference component (forces) and
    5 % per attitude component."""
    ref_f = np.asarray(dF_per_mm_ref_N, dtype=float) * delta_mm
    ref_a = np.asarray(dattitude_per_mm_ref_deg, dtype=float) * delta_mm
    out = [
        check_abs(
            "V5",
            f"FL +{delta_mm:g} mm: contact force change per leg (tol 5 % of max component)",
            dF_N,
            ref_f,
            V5_REL_TOL * float(np.max(np.abs(ref_f))),
            "N",
            ref_key=key_dF,
        )
    ]
    for j, label in enumerate(("roll", "pitch")):
        out.append(
            check_rel(
                "V5",
                f"FL +{delta_mm:g} mm: {label} change",
                float(dattitude_deg[j]),
                float(ref_a[j]),
                V5_REL_TOL,
                "deg",
                ref_key=key_att,
            )
        )
    return out


# --- V5, L1-R (locked rod-side chamber) --------------------------------------------------------


def l1r_module_normal_change(
    dF_contact_N: Sequence[float],
    *,
    moving_leg: int,
    k1_over_k2: Sequence[float],
    knee_dF_N: Sequence[float],
) -> list[float]:
    """Total module normal force change of an L1-R run from the SMC contact force change.

    dynamics_model.md 5.17.5 / 5.14.2: the SMC contact carries the head-only stiffness ``k2``
    (``k2 delta``); the rod-side chamber adds ``F_x`` so that ``N = k2 delta + F_x``. The legs
    locked at the start (all but ``moving_leg``) follow ``k1`` up to the knee and ``k2`` above
    it, so per locked leg ``dN = (k1 / k2) dF`` while ``dN <= dF_knee`` and
    ``dN = dF + dF_knee (1 - k2 / k1)`` above (unloading never reaches the knee). The moving
    leg is ``k2`` throughout (``dN = dF``).

    Args:
        dF_contact_N: SMC contact force change per leg from the locked start (N, LEG_ORDER).
        moving_leg: Index of the commanded leg.
        k1_over_k2: ``k1 / k2`` per leg (``L1R_K1_OVER_K2``).
        knee_dF_N: Knee load increase per leg after an extension (``L1R_KNEE_DF_AFTER_EXTEND_N``).
    """
    out = []
    for leg, (contact_change, ratio, knee) in enumerate(
        zip(dF_contact_N, k1_over_k2, knee_dF_N, strict=True)
    ):
        locked_change = float(ratio) * float(contact_change)
        if leg == moving_leg:
            out.append(float(contact_change))
        elif locked_change <= float(knee):
            out.append(locked_change)
        else:
            out.append(float(contact_change) + float(knee) * (1.0 - 1.0 / float(ratio)))
    return out


def v5_l1r_checks(
    delta_mm: float,
    *,
    dN_N: Sequence[float],
    dN_ref_N: Sequence[float],
    key_dN: str,
    dattitude_deg: Sequence[float],
    dattitude_ref_deg: Sequence[float],
    key_att: str,
) -> list[CheckResult]:
    """V5 of an L1-R run (dynamics_model.md 5.14.8, 5.17.5): module normal force change
    (:func:`l1r_module_normal_change`) against the dynamic replica, tolerance 5 % of its
    largest component; attitude 5 % per component."""
    ref_f = np.asarray(dN_ref_N, dtype=float)
    out = [
        check_abs(
            "V5",
            f"FL +{delta_mm:g} mm: L1-R module normal force change per leg (tol 5 % of max "
            "component)",
            dN_N,
            ref_f,
            V5_REL_TOL * float(np.max(np.abs(ref_f))),
            "N",
            ref_key=key_dN,
            note="SMC contact force converted to N = k2 delta + F_x (dynamics 5.17.5)",
        )
    ]
    for j, label in enumerate(("roll", "pitch")):
        out.append(
            check_rel(
                "V5",
                f"FL +{delta_mm:g} mm: {label} change (L1-R)",
                float(dattitude_deg[j]),
                float(dattitude_ref_deg[j]),
                V5_REL_TOL,
                "deg",
                ref_key=key_att,
            )
        )
    return out


# --- V6 ----------------------------------------------------------------------------------------


def v6_checks(
    direction: str,
    *,
    f_min_leg: str | None,
    f_min_delta_mm: float | None,
    liftoff_leg: str | None,
    liftoff_delta_mm: float | None,
    ref_f_min: Mapping[str, Any],
    ref_liftoff: Mapping[str, Any],
    key_f_min: str,
    key_liftoff: str,
) -> list[CheckResult]:
    """V6 for one direction (``FL+`` or ``FL-``): first leg at F_min (cylinder force) and the
    first unloaded leg (contact force 0), with the FL travel at that moment."""
    nan = math.nan
    return [
        check_equal("V6", f"{direction}: first leg at F_min", f_min_leg,
                    ref_f_min["leg_at_F_min"], ref_key=key_f_min),
        check_rel("V6", f"{direction}: FL travel at F_min", nan if f_min_delta_mm is None else
                  f_min_delta_mm, float(ref_f_min["delta_mm"]), V6_REL_TOL, "mm",
                  ref_key=key_f_min),
        check_equal("V6", f"{direction}: first unloaded leg", liftoff_leg,
                    ref_liftoff["unloaded_leg"], ref_key=key_liftoff),
        check_rel("V6", f"{direction}: FL travel at lift-off", nan if liftoff_delta_mm is None
                  else liftoff_delta_mm, float(ref_liftoff["delta_mm"]), V6_REL_TOL, "mm",
                  ref_key=key_liftoff),
    ]


# --- V9 ----------------------------------------------------------------------------------------


def order_ratio(values_by_dt: Mapping[float, float]) -> dict[str, float]:
    """Successive error ratio of a sequence at dt, dt/2, dt/4 (largest dt first):
    ``(v(dt) - v(dt/2)) / (v(dt/2) - v(dt/4))``."""
    dts = sorted(values_by_dt, reverse=True)
    if len(dts) < 3:
        raise ValueError(f"need three time steps, got {dts}")
    a, b, c = (values_by_dt[d] for d in dts[:3])
    den = b - c
    return {
        "dt_s": dts[:3],
        "d1": a - b,
        "d2": den,
        "ratio": (a - b) / den if den != 0.0 else math.nan,
    }


def v9_checks(
    name: str,
    *,
    dts_s: Sequence[float],
    static_force_N: Mapping[float, Sequence[float]] | None,
    total_weight_N: float,
    final_attitude_deg: Mapping[float, Sequence[float]] | None,
    transient_peak_N: Mapping[float, float] | None,
    ref_dt_s: float,
    order: Mapping[str, Mapping[str, float]] | None = None,
) -> list[CheckResult]:
    """V9 differences against the reference-dt run (``ref_dt_s``) and the order ratios.

    Args:
        static_force_N: dt -> per-leg static contact force (mean window).
        final_attitude_deg: dt -> (roll, pitch) mean over the last three rocking periods.
        transient_peak_N: dt -> transient extreme load (smooth test 1).
        order: ``{label: order_ratio(...)}`` of smooth quantities (judged 2 +- 20 %).
    """
    out: list[CheckResult] = []
    w4 = total_weight_N / 4.0
    for dt in dts_s:
        if dt == ref_dt_s:
            continue
        if static_force_N is not None:
            out.append(
                check_abs(
                    "V9",
                    f"{name}: static contact force, dt {dt:g} vs {ref_dt_s:g} s",
                    static_force_N[dt],
                    static_force_N[ref_dt_s],
                    V9_STATIC_TOL_FRACTION_OF_W4 * w4,
                    "N",
                )
            )
        if final_attitude_deg is not None:
            out.append(
                check_abs(
                    "V9",
                    f"{name}: final attitude (3-period mean), dt {dt:g} vs {ref_dt_s:g} s",
                    final_attitude_deg[dt],
                    final_attitude_deg[ref_dt_s],
                    V9_ATTITUDE_TOL_DEG,
                    "deg",
                )
            )
        if transient_peak_N is not None:
            out.append(
                check_rel(
                    "V9",
                    f"{name}: transient extreme load, dt {dt:g} vs {ref_dt_s:g} s",
                    transient_peak_N[dt],
                    transient_peak_N[ref_dt_s],
                    V9_TRANSIENT_REL_TOL,
                    "N",
                )
            )
    for label, res in (order or {}).items():
        out.append(
            CheckResult(
                "V9",
                f"{name}: error ratio {label} (dt {res['dt_s'][0]:g}/{res['dt_s'][1]:g}/"
                f"{res['dt_s'][2]:g} s)",
                res["ratio"],
                V9_ORDER_RATIO,
                V9_ORDER_RATIO_REL_TOL,
                "rel",
                "1",
                bool(
                    math.isfinite(res["ratio"])
                    and abs(res["ratio"] - V9_ORDER_RATIO)
                    <= V9_ORDER_RATIO_REL_TOL * V9_ORDER_RATIO
                ),
                deviation=(
                    res["ratio"] / V9_ORDER_RATIO - 1.0 if math.isfinite(res["ratio"]) else None
                ),
                note=f"differences {res['d1']:.4e}, {res['d2']:.4e}",
            )
        )
    return out


def v9_v4_r15_touch_record(
    *,
    touch_eq_by_dt: Mapping[float, Sequence[float]],
    ref_dt_s: float,
    dt_at_touch_by_key: Mapping[float, float],
    geometric_diff_max_s: float | None,
    label_by_dt: Mapping[float, str] | None = None,
) -> dict[str, Any]:
    """V9 V4 R15 touch times (recorded, dynamics_model.md 5.7 (b)): difference to the
    reference-dt run and the structural bound ``2 dt - dt_ref`` + the geometric difference
    (the R15 report lags the geometric crossing by (1, 2] dt).

    Args:
        touch_eq_by_dt: key (dt, or a dummy key for windowed runs) -> per-leg R15 touch.
        dt_at_touch_by_key: key -> step length in force at the touches (windowed runs: the
            transition dt).
        geometric_diff_max_s: max |geometric touch - reference| over the dt runs (None: not
            available; the bound then uses 0).
    """
    ref = np.asarray(touch_eq_by_dt[ref_dt_s], dtype=float)
    geo = 0.0 if geometric_diff_max_s is None else float(geometric_diff_max_s)
    out: dict[str, Any] = {}
    for key, touch in touch_eq_by_dt.items():
        if key == ref_dt_s:
            continue
        label = (label_by_dt or {}).get(key, f"dt {key:g} s")
        diff = np.asarray(touch, dtype=float) - ref
        dt = float(dt_at_touch_by_key[key])
        bound = max(2.0 * dt - ref_dt_s, 0.0) + geo
        out[label] = {
            "touch_minus_ref_s": diff.tolist(),
            "max_abs_s": float(np.max(np.abs(diff))),
            "dt_at_touch_s": dt,
            "structural_bound_s (2 dt - dt_ref + geometric diff)": bound,
            "within_structural_bound": bool(np.max(np.abs(diff)) <= bound + 1e-9),
        }
    return out


def v9_v4_checks(
    *,
    touch_eq_by_dt: Mapping[float, Sequence[float]],
    ref_dt_s: float,
    peak_cyl_by_dt: Mapping[float, Sequence[float]],
    final_force_by_dt: Mapping[float, Sequence[float]],
    final_attitude_by_dt: Mapping[float, Sequence[float]],
    total_weight_N: float,
    label_by_dt: Mapping[float, str] | None = None,
) -> list[CheckResult]:
    """V9 for V4: differences only (no order). The touch time is judged on the geometric
    definition (:func:`touch_geometric_checks`); the R15 touch is recorded
    (:func:`v9_v4_r15_touch_record`, dynamics_model.md 5.7 (b))."""
    out: list[CheckResult] = []
    w4 = total_weight_N / 4.0
    for dt in touch_eq_by_dt:
        if dt == ref_dt_s:
            continue
        label = (label_by_dt or {}).get(dt, f"dt {dt:g} s")
        out.append(
            check_rel(
                "V9",
                f"V4 {label}: peak cylinder force vs reference dt",
                peak_cyl_by_dt[dt],
                peak_cyl_by_dt[ref_dt_s],
                V9_TRANSIENT_REL_TOL,
                "N",
            )
        )
        out.append(
            check_abs(
                "V9",
                f"V4 {label}: final contact force vs reference dt",
                final_force_by_dt[dt],
                final_force_by_dt[ref_dt_s],
                V9_STATIC_TOL_FRACTION_OF_W4 * w4,
                "N",
            )
        )
        out.append(
            check_abs(
                "V9",
                f"V4 {label}: final attitude (3-period mean) vs reference dt",
                final_attitude_by_dt[dt],
                final_attitude_by_dt[ref_dt_s],
                V9_ATTITUDE_TOL_DEG,
                "deg",
            )
        )
    return out


__all__ = [
    "LEG_ORDER",
    "l1r_module_normal_change",
    "order_ratio",
    "v4_checks",
    "v4_record_items",
    "v5_checks",
    "v5_l1r_checks",
    "v6_checks",
    "touch_geometric_checks",
    "v8a_checks",
    "v8a_crawler_checks",
    "v8a_crawler_modal_checks",
    "v9_checks",
    "v9_v4_checks",
    "v9_v4_r15_touch_record",
]
