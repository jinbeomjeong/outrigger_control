"""S6 checks (Chrono infrastructure, branch A): V11b, V17 path, sensor truth, V13, closed-loop
smoke (engine independent: arrays in, :class:`CheckResult` out).

``00_docs/03_chrono/chrono_build_plan.md`` S6 pass table. Automatic pass / fail is a pre-check;
the physical judgement is the dynamics-expert's.

* **V11b** (single leg, :mod:`outrigger_sim.chrono.single_leg`; dyn rev. 23 5.10, user
  decision 2026-10-21 U2 = (b); force law C: stop over 2 ms, saturation judged on
  ``F_cyl - m_rod a``). Ref keys ``reference.json / hydraulic_circuit / max_head_force_N`` /
  ``max_rod_side_force_N`` (the YAML ``actuator.max_force_*_N`` are the same values
  unrounded). Judged per direction (:func:`v11b_checks`):

  - saturation reached; ``|F_cyl|`` / limit after the first saturated step <= 1.01
    (``V11b.*.force``);
  - motion in the commanded direction **from the first saturated step** (creep
    ``~ c_n v / k_n`` included) <= 0.04 mm (``V11b.*.motion``, U2 = b); the motion in the
    settled window ``t_sat + 0.5 s`` .. reversal is info (``V11b.*.motion_settled.info``);
  - settled-window mean force / limit within 0.99-1.01 (``V11b.*.settled_mean_force``);
  - reading inertia ``|F_cyl + m_rod g - F_spring|`` <= 1.5 m_rod v_max / t_sat
    (``V11b.reading_inertia``);
  - a reversed command is followed within 2 steps and reaches ``v_max`` within the command
    ramp + hook lag (``V11b.reverse_to_*``).
* **V17 path**: locked head pressure of a settled state,
  :func:`~outrigger_sim.sensors.hydraulic.locked_pressure_report` with and without the locked
  mask (:func:`v17_checks`): no 350 bar exceedance on the **locked samples** (command 0 and
  applied speed 0; user decision 2026-10-21), the all-sample result is info, moving samples
  <= 210 bar relief x 1.01, locked-mask maximum = all-sample maximum. The settled maximum is
  judged per leg against the nonlinear **P-delta** static solution within 0.01 % W/4
  (:func:`v17_pdelta_checks`, dyn rev. 23 U3 = (a),
  ``06_analysis/00_dynamics/s1_pdelta_check.json``); the linear statics within 1 % W/4 is info.
  The older comparison with ``reference.json / hydraulic_circuit / max_static_head_pressure_Pa``
  (linear L1 statics, 0.1 % W/4 as pressure) stays available in :func:`v17_checks`
  (``ref_max_Pa``).
* **Sensor truth**: static level / tilted body -> IMU specific force = ``R^T (0, 0, g)``,
  pressure x ``A_head`` = cylinder force, ``stroke_corrected`` = ``s_motor - F_cyl / k_oil``,
  relative <= 1e-6.
* **V13**: no non-finite value in a zero-order-hold run (per-step monitor + Record).

Units SI unless the id says otherwise.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.frames import quat_to_matrix
from outrigger_sim.params import LEG_ORDER
from outrigger_sim.sensors.hydraulic import locked_pressure_report
from outrigger_sim.verify.checks import CheckResult, check_abs, check_equal, check_max

V11B_FORCE_TOL_REL = 0.01
V11B_MOTION_TOL_M = 4.0e-5
"""User decision 2026-10-21 (U2 = b): motion in the commanded direction from the first
saturated step <= 0.04 mm (dyn rev. 23 5.10)."""
V11B_MEAN_FORCE_BAND = (0.99, 1.01)
"""Settled-window mean force / limit (dyn rev. 23)."""
V11B_INERTIA_FACTOR = 1.5
"""Reading inertia |F_cyl + m_rod g - F_spring| <= 1.5 m_rod v_max / t_sat (dyn rev. 23)."""
V17_PDELTA_TOL_W4_FRACTION = 1.0e-4
"""U3 = (a): per-leg settled maximum - P-delta solution <= 0.01 % W/4 (dyn rev. 23)."""
V17_LINEAR_INFO_W4_FRACTION = 1.0e-2
V11B_SETTLE_S = 0.5
"""Settled window start after the first saturated step (judged motion)."""
V11B_REVERSE_STEPS_MAX = 2
"""Steps from the reversed command to the first reversed applied speed (hook lag 1 + 1)."""
SENSOR_TRUTH_TOL_REL = 1.0e-6
V17_TOL_W4_FRACTION = 1.0e-3
"""S1 V1 tolerance (0.1 % W/4), used for the V17 maximum as a pressure (proposal)."""

REF_MAX_HEAD_FORCE = "reference.json / hydraulic_circuit / max_head_force_N"
REF_MAX_ROD_SIDE_FORCE = "reference.json / hydraulic_circuit / max_rod_side_force_N"
REF_MAX_STATIC_HEAD_PRESSURE = "reference.json / hydraulic_circuit / max_static_head_pressure_Pa"
YAML_LOCKED_LIMIT = "YAML actuator.locked_pressure_limit_Pa"


# --- V11b -----------------------------------------------------------------------------------


def _command_changes(t: NDArray, u_cmd: NDArray) -> list[tuple[int, float, float]]:
    """``(index, old, new)`` where the held command changes (index of the first new sample)."""
    idx = np.flatnonzero(np.diff(u_cmd) != 0.0) + 1
    return [(int(i), float(u_cmd[i - 1]), float(u_cmd[i])) for i in idx]


def _reverse_follow(
    t: NDArray, u_applied: NDArray, i_cmd: int, sign: float, v_max: float
) -> dict[str, Any]:
    """Steps until the applied speed has the commanded sign, and time to reach ``v_max``."""
    after = sign * u_applied[i_cmd:]
    moving = np.flatnonzero(after > 0.0)
    full = np.flatnonzero(after >= v_max * (1.0 - 1e-9))
    return {
        "steps_to_first_motion": int(moving[0]) if moving.size else None,
        "time_to_full_speed_s": float(t[i_cmd + full[0]] - t[i_cmd]) if full.size else None,
    }


def v11b_analysis(
    arrays: Mapping[str, ArrayLike],
    *,
    f_ext_N: float,
    f_ret_N: float,
    v_max_m_s: float,
    settle_s: float = V11B_SETTLE_S,
    rod_mass_kg: float | None = None,
    gravity_m_s2: float | None = None,
    spring_c_N_s_m: float | None = None,
    spring_k_N_m: float | None = None,
) -> dict[str, Any]:
    """Numbers of one single-leg schedule (extend into saturation, retract into the pull
    limit, extend again); ``arrays`` from :func:`outrigger_sim.chrono.single_leg.run_schedule`.
    """
    t = np.asarray(arrays["t"], dtype=float)
    f = np.asarray(arrays["F_cyl"], dtype=float)
    s = np.asarray(arrays["s_motor"], dtype=float)
    ua = np.asarray(arrays["u_applied"], dtype=float)
    uc = np.asarray(arrays["u_cmd"], dtype=float)
    sat = np.asarray(arrays["saturated"], dtype=bool)
    changes = _command_changes(t, uc)
    out: dict[str, Any] = {"command_changes": [(float(t[i]), a, b) for i, a, b in changes]}
    if rod_mass_kg is not None and gravity_m_s2 is not None and "F_spring" in arrays:
        inertia = f + rod_mass_kg * gravity_m_s2 - np.asarray(arrays["F_spring"], dtype=float)
        out["reading_inertia_max_N"] = float(np.max(np.abs(inertia)))
    creep_ref = None
    if spring_c_N_s_m is not None and spring_k_N_m is not None:
        creep_ref = spring_c_N_s_m * v_max_m_s / spring_k_N_m
        out["creep_reference_c_v_over_k_m"] = creep_ref
    phases = []
    for k, (i0, _old, new) in enumerate(changes):
        i1 = changes[k + 1][0] if k + 1 < len(changes) else len(t)
        if new == 0.0:
            continue
        sign = 1.0 if new > 0.0 else -1.0
        limit = f_ext_N if sign > 0 else f_ret_N
        hit = sat[i0:i1] & (f[i0:i1] * sign > 0.0)
        follow = _reverse_follow(t, ua, i0, sign, v_max_m_s)
        phase: dict[str, Any] = {
            "direction": "extend" if sign > 0 else "retract",
            "t_command_s": float(t[i0]),
            "t_end_s": float(t[i1 - 1]),
            "follow": follow,
            "saturated": bool(hit.any()),
        }
        if hit.any():
            j = i0 + int(np.argmax(hit))
            win = slice(j, i1)
            settled = (t >= t[j] + settle_s) & (np.arange(len(t)) < i1)
            ks = np.flatnonzero(settled)
            pos = s[win] * sign
            phase.update(
                t_first_saturation_s=float(t[j]),
                force_at_first_saturation_N=float(f[j]),
                force_peak_N=float(f[win].max() if sign > 0 else f[win].min()),
                force_peak_over_limit=float((f[win].max() if sign > 0 else -f[win].min()) / limit),
                force_dip_N=float(f[win].min() if sign > 0 else f[win].max()),
                creep_from_first_m=float(pos.max() - pos[0]),
                motion_settled_m=float((s[ks] * sign).max() - s[ks[0]] * sign) if ks.size else None,
                t_settled_from_s=float(t[ks[0]]) if ks.size else None,
                saturated_steps=int(sat[win].sum()),
                settled_mean_force_over_limit=float(np.mean(f[ks]) * sign / limit)
                if ks.size else None,
                creep_over_reference=None if creep_ref is None
                else float((pos.max() - pos[0]) / creep_ref),
            )
        phases.append(phase)
    out["phases"] = phases
    return out


def v11b_checks(
    analysis: Mapping[str, Any],
    *,
    f_ext_N: float,
    f_ret_N: float,
    ramp_s: float,
    dt_s: float,
    case: str = "",
    inertia_limit_N: float | None = None,
) -> list[CheckResult]:
    """V11b checks from :func:`v11b_analysis` (module docstring; dyn rev. 23, U2 = b)."""
    out: list[CheckResult] = []
    if inertia_limit_N is not None and "reading_inertia_max_N" in analysis:
        out.append(
            check_max(
                "V11b.reading_inertia",
                f"|F_cyl + m_rod g - F_spring| over the run (rod inertia in the reading)"
                f"{' [' + case + ']' if case else ''}",
                analysis["reading_inertia_max_N"],
                inertia_limit_N,
                "N",
                note="1.5 m_rod v_max / t_sat (dyn rev. 23)",
            )
        )
    tag = f" [{case}]" if case else ""
    by_dir: dict[str, list[Mapping[str, Any]]] = {"extend": [], "retract": []}
    for ph in analysis["phases"]:
        by_dir[ph["direction"]].append(ph)
    for direction, limit, key in (
        ("extend", f_ext_N, REF_MAX_HEAD_FORCE),
        ("retract", f_ret_N, REF_MAX_ROD_SIDE_FORCE),
    ):
        sat = [ph for ph in by_dir[direction] if ph["saturated"]]
        out.append(
            check_equal(
                f"V11b.{direction}.reached",
                f"saturation reached ({direction}){tag}",
                bool(sat),
                True,
                ref_key=key,
            )
        )
        if not sat:
            continue
        ph = sat[0]
        out.append(
            check_max(
                f"V11b.{direction}.force",
                f"|F_cyl| / limit after the first saturated step ({direction}){tag}",
                ph["force_peak_over_limit"],
                1.0 + V11B_FORCE_TOL_REL,
                "1",
                ref_key=key,
                note=f"limit {limit} N (YAML actuator.max_force_*_N)",
            )
        )
        out.append(
            check_max(
                f"V11b.{direction}.motion",
                f"motion in the commanded direction from the first saturated step ({direction})"
                f"{tag}",
                ph["creep_from_first_m"],
                V11B_MOTION_TOL_M,
                "m",
                note="user decision 2026-10-21 U2 = (b); creep / (c_n v_max / k_n) = "
                f"{ph.get('creep_over_reference')}",
            )
        )
        settled = ph["motion_settled_m"]
        out.append(
            CheckResult(
                f"V11b.{direction}.motion_settled.info",
                f"motion in the settled window t_sat + {V11B_SETTLE_S} s .. reversal "
                f"({direction}){tag}",
                settled, None, None, "info", "m", True,
            )
        )
        mean = ph.get("settled_mean_force_over_limit")
        lo, hi = V11B_MEAN_FORCE_BAND
        out.append(
            CheckResult(
                f"V11b.{direction}.settled_mean_force",
                f"settled-window mean force / limit ({direction}){tag}",
                mean, [lo, hi], [lo, hi], "band", "1",
                mean is not None and lo <= mean <= hi, ref_key=key,
            )
        )
    # reversal: every non-first command phase must follow at once
    phases = analysis["phases"]
    for prev, ph in zip(phases[:-1], phases[1:], strict=True):
        if prev["direction"] == ph["direction"]:
            continue
        follow = ph["follow"]
        steps = follow["steps_to_first_motion"]
        full = follow["time_to_full_speed_s"]
        out.append(
            check_max(
                f"V11b.reverse_to_{ph['direction']}.steps",
                f"steps from the reversed command to reversed motion{tag}",
                np.nan if steps is None else steps,
                V11B_REVERSE_STEPS_MAX,
                "steps",
            )
        )
        out.append(
            check_max(
                f"V11b.reverse_to_{ph['direction']}.full_speed",
                f"time from the reversed command to |u| = v_max{tag}",
                np.nan if full is None else full,
                ramp_s + (V11B_REVERSE_STEPS_MAX + 1) * dt_s,
                "s",
                note="acceleration limit actuator.command_ramp_s + hook lag",
            )
        )
    return out


# --- V17 path -------------------------------------------------------------------------------


def locked_mask(u_cmd: ArrayLike, u_applied: ArrayLike) -> NDArray[np.bool_]:
    """Locked samples per leg: command 0 and applied speed 0 (valve centred, lock valve
    closed). A leg stalled by the force saturation (command != 0) is *not* locked."""
    return (np.asarray(u_cmd) == 0.0) & (np.asarray(u_applied) == 0.0)


def v17_reports(
    t_s: ArrayLike,
    head_pressure_Pa: ArrayLike,
    limit_Pa: float,
    u_cmd: ArrayLike,
    u_applied: ArrayLike,
) -> dict[str, Any]:
    """Both mask variants (all samples / locked samples only), JSON-ready."""
    p = np.asarray(head_pressure_Pa, dtype=float)
    mask = locked_mask(u_cmd, u_applied)
    out: dict[str, Any] = {
        "all_samples": locked_pressure_report(t_s, p, limit_Pa).to_dict(),
        "locked_fraction_per_leg": dict(zip(LEG_ORDER, mask.mean(axis=0).tolist(), strict=True)),
    }
    if mask.any():
        out["locked_only"] = locked_pressure_report(t_s, p, limit_Pa, is_locked=mask).to_dict()
    else:
        out["locked_only"] = None
    if (~mask).any():
        moving = np.where(~mask, p, -np.inf)
        out["moving_max_Pa"] = float(moving.max())
    else:
        out["moving_max_Pa"] = None
    return out


def v17_checks(
    reports: Mapping[str, Any],
    *,
    level: str,
    ref_max_Pa: float | None,
    tol_Pa: float,
    step_max_force_N: Sequence[float] | None = None,
    head_area_m2: float | None = None,
    relief_Pa: float | None = None,
) -> list[CheckResult]:
    """V17 path checks of one run (reference maximum only for the top level). The 350 bar
    check uses the locked mask (:func:`locked_mask`, user decision 2026-10-21)."""
    out: list[CheckResult] = []
    rep = reports["all_samples"]
    locked = reports.get("locked_only")
    # user decision 2026-10-21: the 350 bar judgement uses the locked mask (command 0 and
    # applied speed 0); the all-sample result is info, moving samples are judged against
    # the 210 bar relief separately
    if locked is not None:
        out.append(
            check_equal(
                f"V17.{level}.not_exceeded",
                f"no 350 bar exceedance in locked samples ({level})",
                bool(locked["is_exceeded"]),
                False,
                ref_key=YAML_LOCKED_LIMIT,
                note="locked mask: u_cmd = 0 and u_applied = 0 (user decision 2026-10-21)",
            )
        )
    out.append(
        CheckResult(
            f"V17.{level}.all_samples.info",
            f"350 bar exceedance over all samples, info only ({level})",
            bool(rep["is_exceeded"]),
            False,
            0,
            "info",
            "",
            True,
            ref_key=YAML_LOCKED_LIMIT,
            note=f"all-sample max {rep['max_pressure_Pa']:.6g} Pa",
        )
    )
    moving_max = reports.get("moving_max_Pa")
    if moving_max is not None and relief_Pa is not None:
        out.append(
            check_max(
                f"V17.{level}.moving_relief",
                f"moving samples: head pressure <= 210 bar relief x 1.01 ({level})",
                moving_max,
                relief_Pa * (1.0 + V11B_FORCE_TOL_REL),
                "Pa",
                ref_key="YAML actuator.relief_pressure_moving_Pa",
            )
        )
    if locked is not None:
        out.append(
            check_abs(
                f"V17.{level}.mask_same",
                f"locked-mask maximum = all-sample maximum (settled run, {level})",
                locked["max_pressure_Pa"],
                rep["max_pressure_Pa"],
                0.0,
                "Pa",
            )
        )
    if ref_max_Pa is not None:
        out.append(
            check_abs(
                f"V17.{level}.max",
                f"settled maximum head pressure vs linear static maximum ({level}, "
                f"{rep['max_leg']})",
                rep["max_pressure_Pa"],
                ref_max_Pa,
                tol_Pa,
                "Pa",
                ref_key=REF_MAX_STATIC_HEAD_PRESSURE,
                note="tol = 0.1 % W/4 / A_head (S1 V1 tolerance, proposal)",
            )
        )
        if step_max_force_N is not None and head_area_m2 is not None:
            out.append(
                check_abs(
                    f"V17.{level}.max_per_step",
                    f"per-step maximum head pressure vs linear static maximum ({level})",
                    float(np.max(step_max_force_N)) / head_area_m2,
                    ref_max_Pa,
                    tol_Pa,
                    "Pa",
                    ref_key=REF_MAX_STATIC_HEAD_PRESSURE,
                )
            )
    return out


def v17_pdelta_checks(
    *,
    level: str,
    settled_max_cyl_N: Sequence[float],
    pdelta_cyl_N: Sequence[float],
    linear_cyl_N: Sequence[float],
    w4_N: float,
) -> list[CheckResult]:
    """U3 = (a) (dyn rev. 23): per-leg settled maximum cylinder force vs the nonlinear
    (P-delta) static solution ``s1_pdelta_check.json <level>.nonlinear_cyl_N`` within 0.01 %
    W/4; vs the linear reference within 1 % W/4 recorded."""
    mx = np.asarray(settled_max_cyl_N, dtype=float)
    pd = np.asarray(pdelta_cyl_N, dtype=float)
    lin = np.asarray(linear_cyl_N, dtype=float)
    return [
        check_abs(
            f"V17.{level}.pdelta",
            f"settled max cylinder force per leg - P-delta static solution ({level})",
            mx, pd, V17_PDELTA_TOL_W4_FRACTION * w4_N, "N",
            ref_key="06_analysis/00_dynamics/s1_pdelta_check.json / <level> / nonlinear_cyl_N",
            note="tol 0.01 % W/4 (dyn rev. 23, U3 = a)",
        ),
        CheckResult(
            f"V17.{level}.linear.info",
            f"settled max cylinder force per leg - linear static solution ({level}), info",
            mx, lin, V17_LINEAR_INFO_W4_FRACTION * w4_N, "info", "N",
            bool(np.all(np.abs(mx - lin) <= V17_LINEAR_INFO_W4_FRACTION * w4_N)),
            deviation=mx - lin, note="1 % W/4 recorded",
        ),
    ]


# --- sensor truth ---------------------------------------------------------------------------


def _rel_dev(value: NDArray, ref: NDArray, scale: NDArray | float) -> float:
    return float(np.max(np.abs(value - ref) / scale))


def sensor_truth_checks(
    arrays: Mapping[str, ArrayLike],
    *,
    gravity_m_s2: float,
    head_area_m2: float | Sequence[float],
    k_oil_N_m: Sequence[float],
    case: str,
    stroke_m: float,
    imu_static: bool = True,
) -> list[CheckResult]:
    """Sensor-truth checks on ideal Record arrays (``meas.*`` with an ideal sensor suite).

    Args:
        arrays: Record arrays (``meas.specific_force``, ``meas.angular_rate``,
            ``meas.head_pressure``, ``meas.stroke``, ``meas.stroke_corrected``,
            ``body_quat_wxyz``, ``F_cyl``, ``s_motor``, ``stroke_true``).
        head_area_m2: Head area, one value or per leg (P-15).
        stroke_m: YAML ``actuator.stroke_m``; the stroke tolerances are 1e-6 x stroke.
        imu_static: Judge ``f = R^T (0, 0, g)`` and ``omega = 0`` (body at rest); False =
            leave the IMU out (use :func:`imu_static_residual` to record it).
    """
    f = np.asarray(arrays["meas.specific_force"], dtype=float)
    w = np.asarray(arrays["meas.angular_rate"], dtype=float)
    q = np.asarray(arrays["body_quat_wxyz"], dtype=float)
    p = np.asarray(arrays["meas.head_pressure"], dtype=float)
    fc = np.asarray(arrays["F_cyl"], dtype=float)
    sm = np.asarray(arrays["s_motor"], dtype=float)
    stroke_scale_m = float(stroke_m)
    ref_f = np.array([quat_to_matrix(qq).T @ np.array([0.0, 0.0, gravity_m_s2]) for qq in q])
    out: list[CheckResult] = []
    if imu_static:
        out.append(
            check_max(
                f"truth.{case}.imu_specific_force",
                f"IMU specific force vs R^T (0,0,g), max |diff| / g ({case})",
                _rel_dev(f, ref_f, gravity_m_s2),
                SENSOR_TRUTH_TOL_REL,
                "1",
                note="R from the recorded body quaternion (mounting-point rotation)",
            )
        )
        out.append(
            check_max(
                f"truth.{case}.gyro_at_rest",
                f"gyro truth max |omega| at rest ({case})",
                float(np.max(np.abs(w))),
                SENSOR_TRUTH_TOL_REL * gravity_m_s2,
                "rad/s",
                note="tolerance 1e-6 x g in rad/s (no natural scale at rest)",
            )
        )
    scale_f = np.maximum(np.abs(fc), 1.0)
    out.append(
        check_max(
            f"truth.{case}.pressure",
            f"head pressure x A_head vs cylinder force, max relative ({case})",
            _rel_dev(p * head_area_m2, fc, scale_f),
            SENSOR_TRUTH_TOL_REL,
            "1",
        )
    )
    corrected = np.asarray(arrays["meas.stroke_corrected"], dtype=float)
    expect = sm - fc / np.asarray(k_oil_N_m, dtype=float)
    out.append(
        check_max(
            f"truth.{case}.stroke_corrected",
            f"stroke_corrected vs s_motor - F_cyl / k_oil, max |diff| (m) ({case})",
            float(np.max(np.abs(corrected - expect))),
            SENSOR_TRUTH_TOL_REL * stroke_scale_m,
            "m",
            note="tolerance 1e-6 x stroke",
        )
    )
    out.append(
        check_max(
            f"truth.{case}.stroke_motor",
            f"meas.stroke vs s_motor, max |diff| (m) ({case})",
            float(np.max(np.abs(np.asarray(arrays["meas.stroke"]) - sm))),
            SENSOR_TRUTH_TOL_REL * stroke_scale_m,
            "m",
        )
    )
    if "stroke_true" in arrays:
        out.append(
            check_max(
                f"truth.{case}.stroke_true_record",
                f"Record stroke_true = meas.stroke_corrected (ideal sensors) ({case})",
                float(np.max(np.abs(np.asarray(arrays["stroke_true"]) - corrected))),
                SENSOR_TRUTH_TOL_REL * stroke_scale_m,
                "m",
            )
        )
    return out


def imu_static_residual(arrays: Mapping[str, ArrayLike], gravity_m_s2: float) -> dict[str, Any]:
    """``f - R^T (0, 0, g)`` statistics of a settled (not exactly static) run, body axes."""
    f = np.asarray(arrays["meas.specific_force"], dtype=float)
    q = np.asarray(arrays["body_quat_wxyz"], dtype=float)
    ref = np.array([quat_to_matrix(qq).T @ np.array([0.0, 0.0, gravity_m_s2]) for qq in q])
    d = f - ref
    return {
        "max_abs_over_g": float(np.max(np.abs(d)) / gravity_m_s2),
        "mean_m_s2": d.mean(axis=0).tolist(),
        "rms_m_s2": np.sqrt((d**2).mean(axis=0)).tolist(),
        "max_abs_m_s2": np.abs(d).max(axis=0).tolist(),
    }


# --- V13 ------------------------------------------------------------------------------------


def v13_checks(
    arrays: Mapping[str, ArrayLike], monitor: Mapping[str, Any], case: str
) -> list[CheckResult]:
    """No NaN in the zero-order-hold run: per-step monitor and every float Record array."""
    bad = [
        name
        for name, a in arrays.items()
        if np.asarray(a).dtype.kind == "f"
        and name != "bushing_anchor"
        and not np.all(np.isfinite(np.asarray(a)))
    ]
    anchors = np.asarray(arrays.get("bushing_anchor", np.zeros((1, 4, 3))))
    contact = np.asarray(arrays.get("pad_in_contact", np.ones(anchors.shape[:2], dtype=bool)))
    anchor_bad = bool(np.any(~np.isfinite(anchors[contact]))) if anchors.size else False
    return [
        check_equal(
            f"V13.{case}.step_monitor",
            f"non-finite steps in the per-step monitor ({case})",
            int(monitor["nonfinite_steps"]),
            0,
            "steps",
        ),
        check_equal(
            f"V13.{case}.record",
            f"Record float arrays with non-finite values ({case})",
            bad + (["bushing_anchor(in contact)"] if anchor_bad else []),
            [],
        ),
    ]


__all__ = [
    "SENSOR_TRUTH_TOL_REL",
    "V11B_FORCE_TOL_REL",
    "V11B_MOTION_TOL_M",
    "imu_static_residual",
    "locked_mask",
    "sensor_truth_checks",
    "v11b_analysis",
    "v11b_checks",
    "v13_checks",
    "v17_checks",
    "v17_pdelta_checks",
    "v17_reports",
]
