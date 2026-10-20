"""S2a checks: V7 diagnosis (bushing dynamics), V12 (sloped-floor statics), V13 (solver health).

``00_docs/03_chrono/chrono_build_plan.md`` S2a table; ``dynamics_model.md`` 5 (V7 rows rev. 7
supplement / rev. 9, V12, V13), 3.6, 4.5, 5.2 ruling 2. Engine independent: inputs are the
sample arrays of ``chrono/runs`` (``Series.arrays()``) and the fit results of
``verify/metrics``. Automatic pass / fail is a pre-check; the physical judgement is the
dynamics-expert's.

V7 diagnosis (plan S2a V7 row, rev. 10 option A: ball-centre bushing): the thresholds are
read from ``V7_ball_centre_bushing_rev13 / V7_diagnostic / thresholds`` (``dynamics_model.md``
5.4 table); zeta after subtracting the numerical damping ``r_i omega_i dt / 2``:

1. normal: zeta1 and zeta2 within their bands (nominal +-10 %);
2. ``g_n`` / floor-mass error: zeta1 <= its maximum;
3. vertical damping too large: zeta1 >= its minimum;
4. ``c_t`` input doubled suspected: between 2 and 3, and zeta2 >= its minimum;
5. case 4 or none of 1-4: yaw initial velocity (2 s), corrected zeta3: >= the c_t-doubled
   minimum -> ``c_t`` doubled, <= the missing maximum -> bushing damping missing.

The 1st / 2nd frequencies are also checked against the rev. 13 values within +-0.3 %
(bushing moved to the ball centre; near the old 1.786 / 2.986 Hz it was not moved). Every
frequency check compares the identified natural frequency ``f_d / sqrt(1 - zeta_fit^2)`` with
the reference ``f_damped_Hz``, which is ``|lambda| / 2 pi`` (:func:`v7_frequency_checks`).

V12 (per leg, means over the last 3 s): total floor -> rod reaction (SMC contact + bushing)
in world axes vs ``slope_V12 / <case> / L1``: vertical +-1 % W/4; horizontal x, y +-10 % or
+-0.2 kN (the larger); slip (bushing anchor movement) < 0.1 mm; elastic bushing deformation
+-10 % of the reference in-plane force / kt. Diagnosis (rev. 10, not judged): Chrono -
reference within 3 N per leg of the option-A expectation (P-delta only,
``L1_plan_A_expected_chrono_minus_reference_rev13``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.frames import roll_pitch_from_quat
from outrigger_sim.params import LEG_ORDER, Params
from outrigger_sim.scenarios.slope import reference_reaction_world_N, split_normal_tangential
from outrigger_sim.verify.checks import CheckResult, check_abs, check_equal, check_max, check_rel
from outrigger_sim.verify.metrics import DampedFit
from outrigger_sim.verify.reference import (
    L1_BALL_CENTRE_REV13_V7_DIAGNOSTIC_THRESHOLDS,
    L1_BALL_CENTRE_REV13_ZETA,
    SLOPE_V12_L1,
    SLOPE_V12_L1_PLAN_A_EXPECTED_DIFF_REV13,
    TOTAL_WEIGHT_INCL_RODS_N,
    References,
)

# --- V7 ----------------------------------------------------------------------------------

V7_FREQ_REL_TOL = 0.03
V7_ZETA_REL_TOL = 0.30
V7_FORCE_POINT_FREQ_REL_TOL = 0.003
"""Plan rev. 10: 1st / 2nd frequency within +-0.3 % of the ball-centre (rev. 13) value."""
V7_FORCE_POINT_MODES = (1, 2)
YAW_MODE_INDEX = 2
"""0-based index of mode 3 (yaw-sway), the diagnosis-5 mode."""
FIT_RESIDUAL_REL_MAX = 0.05
"""Fit-quality gate (RMS residual / RMS signal) for the judged mode; above it the fit of
one decaying cosine does not describe the modal coordinate."""
LOG_DECREMENT_REL_TOL = 0.10
"""Cross-check: zeta of the peak envelope within 10 % of the fitted zeta (identification
uncertainty of the plan's +-10 % band)."""


@dataclass(frozen=True)
class V7Thresholds:
    """Diagnosis thresholds of one level (``V7_diagnostic / thresholds``, rev. 13)."""

    normal_zeta1_band: tuple[float, float]
    normal_zeta2_band: tuple[float, float]
    gn_error_zeta1_max: float
    vertical_damping_excess_zeta1_min: float
    ct_double_suspect_zeta2_min: float
    ct_double_confirmed_zeta3_min: float
    bushing_damping_missing_zeta3_max: float
    nominal_zeta3: float
    """Reference zeta of mode 3 (yaw-sway), for the item-5 message."""
    key: str


def _band(values: Sequence[float]) -> tuple[float, float]:
    low, high = values
    return float(low), float(high)


def v7_thresholds(refs: References, level: str = "top") -> V7Thresholds:
    """Read the V7 diagnosis thresholds of ``level`` (ball-centre bushing, rev. 13)."""
    table = refs.get(L1_BALL_CENTRE_REV13_V7_DIAGNOSTIC_THRESHOLDS, level=level)
    return V7Thresholds(
        normal_zeta1_band=_band(table["1_normal_zeta1_band"]),
        normal_zeta2_band=_band(table["1_normal_zeta2_band"]),
        gn_error_zeta1_max=float(table["2_gn_or_floor_mass_error_zeta1_max"]),
        vertical_damping_excess_zeta1_min=float(table["3_vertical_damping_excess_zeta1_min"]),
        ct_double_suspect_zeta2_min=float(
            table["4_ct_x2_suspect_zeta2_min (with zeta1_max(2) < zeta1 < zeta1_min(3))"]
        ),
        ct_double_confirmed_zeta3_min=float(table["5_ct_x2_confirmed_zeta3_min"]),
        bushing_damping_missing_zeta3_max=float(table["5_bushing_damping_missing_zeta3_max"]),
        nominal_zeta3=float(refs.get(L1_BALL_CENTRE_REV13_ZETA, level=level)[YAW_MODE_INDEX]),
        key=L1_BALL_CENTRE_REV13_V7_DIAGNOSTIC_THRESHOLDS.resolve(level=level).notation(),
    )


@dataclass(frozen=True)
class V7Diagnosis:
    code: str
    """``"1"`` ... ``"4"``, ``"none"`` (none of 1-4)."""
    text: str
    needs_yaw: bool


def _within(value: float, band: tuple[float, float]) -> bool:
    return band[0] <= value <= band[1]


def v7_diagnosis(zeta1: float, zeta2: float, limits: V7Thresholds) -> V7Diagnosis:
    """Classify the corrected modes 1-2 damping ratios (plan S2a V7 row, items 1-5)."""
    if _within(zeta1, limits.normal_zeta1_band) and _within(zeta2, limits.normal_zeta2_band):
        return V7Diagnosis(
            "1",
            f"normal (zeta1 in {limits.normal_zeta1_band}, zeta2 in {limits.normal_zeta2_band})",
            False,
        )
    if zeta1 <= limits.gn_error_zeta1_max:
        return V7Diagnosis(
            "2", f"g_n / floor mass error (zeta1 <= {limits.gn_error_zeta1_max:g})", False
        )
    if zeta1 >= limits.vertical_damping_excess_zeta1_min:
        return V7Diagnosis(
            "3",
            f"vertical damping too large (zeta1 >= {limits.vertical_damping_excess_zeta1_min:g})",
            False,
        )
    if zeta2 >= limits.ct_double_suspect_zeta2_min:
        return V7Diagnosis(
            "4",
            f"c_t input doubled suspected (zeta2 >= {limits.ct_double_suspect_zeta2_min:g})"
            " -> yaw test",
            True,
        )
    return V7Diagnosis("none", "none of 1-4 -> yaw test (item 5)", True)


def v7_yaw_verdict(zeta3_corrected: float, limits: V7Thresholds) -> str:
    """Item 5: corrected zeta3 against the c_t-doubled / bushing-damping-missing thresholds."""
    doubled_min = limits.ct_double_confirmed_zeta3_min
    missing_max = limits.bushing_damping_missing_zeta3_max
    if zeta3_corrected >= doubled_min:
        return f"c_t doubled (zeta3 >= {doubled_min:g})"
    if zeta3_corrected <= missing_max:
        return f"bushing damping missing (zeta3 <= {missing_max:g})"
    return (
        f"c_t as intended ({missing_max:g} < zeta3 < {doubled_min:g}; "
        f"nominal {limits.nominal_zeta3:g})"
    )


@dataclass(frozen=True)
class ModeResult:
    """Identified mode of one excitation run."""

    mode: int
    """1-based."""
    fit: DampedFit
    zeta_num: float
    zeta_corrected: float
    zeta_log_decrement: float | None
    f_ref_Hz: float
    zeta_ref: float


def v7_frequency_checks(
    run: str, mode: int, f_natural_Hz: float, f_ref_Hz: float
) -> list[CheckResult]:
    """Frequency checks of one mode: +-3 % (general V7 row), +-0.3 % for modes 1-2.

    The reference ``V7_ball_centre_bushing_rev13 / f_damped_Hz`` is ``|lambda| / 2 pi`` of the
    damped eigenvalue, which equals the undamped natural frequency of that mode, so it is
    compared with the identified ``f_n = f_d / sqrt(1 - zeta_fit^2)``
    (:attr:`DampedFit.f_undamped_Hz`), not with the damped frequency ``f_d``.

    Args:
        run: Case name for the item text.
        mode: 1-based mode number.
        f_natural_Hz: Identified natural frequency ``f_d / sqrt(1 - zeta_fit^2)``.
        f_ref_Hz: Reference ``|lambda| / 2 pi``.
    """
    note = "f_n = f_d / sqrt(1 - zeta_fit^2) vs V7_ball_centre_bushing_rev13 / f_damped_Hz "
    note += "(|lambda| / 2 pi)"
    out = [
        check_rel(
            "V7",
            f"{run}: mode {mode} natural frequency",
            f_natural_Hz,
            f_ref_Hz,
            V7_FREQ_REL_TOL,
            "Hz",
            note=note,
        )
    ]
    if mode in V7_FORCE_POINT_MODES:
        out.append(
            check_rel(
                "V7",
                f"{run}: mode {mode} natural frequency, bushing at the ball centre (+-0.3 %)",
                f_natural_Hz,
                f_ref_Hz,
                V7_FORCE_POINT_FREQ_REL_TOL,
                "Hz",
                note="plan rev. 10 option A; near the contact-point values the bushing "
                "was not moved; " + note,
            )
        )
    return out


def v7_mode_checks(run: str, result: ModeResult) -> list[CheckResult]:
    """Frequency (:func:`v7_frequency_checks`), corrected zeta +-30 %, fit quality, cross-check."""
    i = result.mode
    out = [
        *v7_frequency_checks(run, i, result.fit.f_undamped_Hz, result.f_ref_Hz),
        check_rel(
            "V7",
            f"{run}: mode {i} zeta (identified - r omega dt/2)",
            result.zeta_corrected,
            result.zeta_ref,
            V7_ZETA_REL_TOL,
            "-",
            note=f"zeta_fit {result.fit.zeta:.6g} - zeta_num {result.zeta_num:.3g}",
        ),
        check_max(
            "V7",
            f"{run}: mode {i} fit residual (RMS rel.)",
            result.fit.residual_rms_rel,
            FIT_RESIDUAL_REL_MAX,
            "-",
        ),
    ]
    if result.zeta_log_decrement is not None:
        out.append(
            check_rel(
                "V7",
                f"{run}: mode {i} zeta cross-check (peak envelope vs fit)",
                result.zeta_log_decrement,
                result.fit.zeta,
                LOG_DECREMENT_REL_TOL,
                "-",
            )
        )
    return out


def run_health_checks(
    run: str,
    series: Mapping[str, NDArray[Any]],
    *,
    n_events: int,
    yield_steps: Sequence[int],
) -> list[CheckResult]:
    """V13 items over a whole dynamic run + no bushing event / yield (V7 premise)."""
    cb = np.asarray(series["cb_count"])
    cb = cb[cb[:, 0] >= 0][:, 1:]  # rows with a callback count, legs only
    finite = all(
        np.all(np.isfinite(series[k]))
        for k in ("origin", "quat", "pad_contact_world", "bushing_force_world", "motor_force")
    )
    return [
        check_equal("V13", f"{run}: no NaN", not finite, False),
        check_max(
            "V13",
            f"{run}: motor constraint violation",
            float(np.max(series["motor_violation"])),
            1.0e-6,
            "m",
        ),
        check_equal(
            "V13",
            f"{run}: one contact per leg (callback min, max)",
            [cb.min(axis=0).tolist(), cb.max(axis=0).tolist()],
            [[1] * len(LEG_ORDER), [1] * len(LEG_ORDER)],
        ),
        check_max(
            "V13",
            f"{run}: crawler contact force (must stay 0)",
            float(np.abs(series["crawler_force"]).max()),
            0.0,
            "N",
        ),
        check_equal("V7", f"{run}: no bushing event (R15)", n_events, 0),
        check_equal("V7", f"{run}: no yield step", list(yield_steps), [0] * len(LEG_ORDER)),
    ]


# --- V12 / V13 on the slope ---------------------------------------------------------------

V12_VERTICAL_FRACTION_OF_QUARTER_WEIGHT = 1.0e-2
V12_HORIZONTAL_REL_TOL = 0.10
V12_HORIZONTAL_ABS_TOL_N = 200.0
V12_SLIP_MAX_M = 1.0e-4
V12_ELASTIC_REL_TOL = 0.10
V12_START_DEFORMATION_MAX_M = 1.0e-9
V12_ATTITUDE_ABS_TOL_DEG = 0.002
"""Information only (V3 tolerance): attitude change vs the linear reference."""
V13_DRIFT_DEG = 1.0e-4
V13_FORCE_FRACTION_OF_QUARTER_WEIGHT = 1.0e-3


def window(series: Mapping[str, NDArray[Any]], t_from_s: float) -> dict[str, NDArray[Any]]:
    """Rows with ``t >= t_from_s`` (``t`` in the series' time base)."""
    mask = np.asarray(series["t"]) >= t_from_s - 1e-9
    return {k: np.asarray(v)[mask] for k, v in series.items()}


@dataclass(frozen=True)
class SlopeWindowStats:
    """Means over the V12 window and spans over the V13 window (world axes, SI)."""

    reaction_world_mean_N: NDArray[np.float64]
    """(4, 3) SMC contact + bushing force on each rod."""
    normal_mean_N: NDArray[np.float64]
    tangential_mean_N: NDArray[np.float64]
    bushing_disp_mean_m: NDArray[np.float64]
    """In-plane bushing deformation magnitude per leg."""
    motor_force_mean_N: NDArray[np.float64]
    roll_mean_deg: float
    pitch_mean_deg: float
    roll_span_deg: float
    pitch_span_deg: float
    normal_span_N: NDArray[np.float64]
    motor_violation_max_m: float
    contacts_min: NDArray[np.int64]
    contacts_max: NDArray[np.int64]
    crawler_force_max_N: float
    any_nan: bool
    mean_window_s: tuple[float, float]
    still_window_s: tuple[float, float]


def slope_window_stats(
    series: Mapping[str, NDArray[Any]],
    normal: Sequence[float],
    *,
    mean_from_s: float,
    still_from_s: float,
) -> SlopeWindowStats:
    n = np.asarray(normal, dtype=float)
    m = window(series, mean_from_s)
    s = window(series, still_from_s)
    reaction = m["pad_contact_world"] + m["bushing_force_world"]
    r_mean = reaction.mean(axis=0)
    nn, tt = split_normal_tangential(r_mean, n)
    roll_m, pitch_m = roll_pitch_from_quat(m["quat"])
    roll_s, pitch_s = roll_pitch_from_quat(s["quat"])
    cb = s["cb_count"]
    cb = cb[cb[:, 0] >= 0][:, 1:]
    s_reaction = s["pad_contact_world"] + s["bushing_force_world"]
    finite = all(
        np.all(np.isfinite(v))
        for v in (s["origin"], s["quat"], s_reaction, s["motor_force"], m["bushing_disp"])
    )
    return SlopeWindowStats(
        reaction_world_mean_N=r_mean,
        normal_mean_N=nn,
        tangential_mean_N=tt,
        bushing_disp_mean_m=np.linalg.norm(m["bushing_disp"], axis=2).mean(axis=0),
        motor_force_mean_N=m["motor_force"].mean(axis=0),
        roll_mean_deg=float(np.degrees(roll_m).mean()),
        pitch_mean_deg=float(np.degrees(pitch_m).mean()),
        roll_span_deg=float(np.ptp(np.degrees(roll_s))),
        pitch_span_deg=float(np.ptp(np.degrees(pitch_s))),
        normal_span_N=np.ptp(s_reaction @ n, axis=0),
        motor_violation_max_m=float(np.max(s["motor_violation"])),
        contacts_min=cb.min(axis=0),
        contacts_max=cb.max(axis=0),
        crawler_force_max_N=float(np.abs(s["crawler_force"]).max()),
        any_nan=not finite,
        mean_window_s=(float(m["t"][0]), float(m["t"][-1])),
        still_window_s=(float(s["t"][0]), float(s["t"][-1])),
    )


def slope_reference(refs: References, case: str, normal: Sequence[float]) -> dict[str, Any]:
    """Reference reaction (world), its normal / in-plane split and the other L1 arrays."""
    block = refs.get(SLOPE_V12_L1, case=case)
    reaction = reference_reaction_world_N(
        block["contact_vertical_N"], block["contact_horizontal_xy_N"]
    )
    nn, tt = split_normal_tangential(reaction, normal)
    return {
        "reaction_world_N": reaction,
        "normal_N": nn,
        "tangential_N": tt,
        "cylinder_force_N": np.asarray(block["cylinder_force_N"], dtype=float),
        "friction_utilisation": np.asarray(block["friction_utilisation_T_over_N"], dtype=float),
        "attitude_change_deg": np.asarray(block["attitude_change_deg (roll, pitch)"], dtype=float),
        "key": SLOPE_V12_L1.resolve(case=case).notation(),
    }


def v12_checks(
    params: Params,
    refs: References,
    case: str,
    normal: Sequence[float],
    stats: SlopeWindowStats,
    *,
    slip_total_m: NDArray[np.float64],
    start_deformation_m: float,
    start_gap_m: Sequence[float],
) -> tuple[list[CheckResult], list[CheckResult]]:
    """V12 checks (judged) and information items (not judged by the plan).

    Returns:
        ``(checks, info)``.
    """
    ref = slope_reference(refs, case, normal)
    quarter = float(refs.get(TOTAL_WEIGHT_INCL_RODS_N)) / 4.0
    key = ref["key"]
    r_ref = ref["reaction_world_N"]
    r_got = stats.reaction_world_mean_N
    kt = np.asarray(params.contact.rigid_floor.L1.bushing_stiffness_per_pad_N_m, dtype=float)
    horiz_tol = np.maximum(V12_HORIZONTAL_REL_TOL * np.abs(r_ref[:, :2]), V12_HORIZONTAL_ABS_TOL_N)
    horiz_dev = r_got[:, :2] - r_ref[:, :2]
    horizontal = CheckResult(
        "V12",
        f"{case}: horizontal reaction x, y per leg (+-10 % or +-0.2 kN)",
        r_got[:, :2],
        r_ref[:, :2],
        horiz_tol,
        "abs (per element)",
        "N",
        bool(np.all(np.isfinite(r_got)) and np.all(np.abs(horiz_dev) <= horiz_tol)),
        ref_key=f"{key} / contact_horizontal_xy_N",
        deviation=horiz_dev,
    )
    slip = np.linalg.norm(slip_total_m, axis=1)
    checks = [
        check_max(
            "V12",
            f"{case}: input - bushing deformation at the ramp start",
            start_deformation_m,
            V12_START_DEFORMATION_MAX_M,
            "m",
            note="dynamics_model.md 5.2 ruling 2 input item (<= 1e-9 m)",
        ),
        check_max(
            "V12",
            f"{case}: input - pad sphere gap to the slope at the start |gap|",
            np.abs(np.asarray(start_gap_m, dtype=float)),
            V12_START_DEFORMATION_MAX_M,
            "m",
            note="pads placed with zero force (3.6)",
        ),
        check_abs(
            "V12",
            f"{case}: vertical reaction per leg (+-1 % W/4)",
            r_got[:, 2],
            r_ref[:, 2],
            V12_VERTICAL_FRACTION_OF_QUARTER_WEIGHT * quarter,
            "N",
            ref_key=f"{key} / contact_vertical_N",
        ),
        horizontal,
        check_max(
            "V12",
            f"{case}: slip (bushing anchor accumulated movement)",
            slip,
            V12_SLIP_MAX_M,
            "m",
        ),
        check_rel(
            "V12",
            f"{case}: elastic bushing deformation (+-10 % of reference in-plane force / kt)",
            stats.bushing_disp_mean_m,
            ref["tangential_N"] / kt,
            V12_ELASTIC_REL_TOL,
            "m",
            ref_key=f"{key} (R . n split)",
            note="reference in-plane force |R - (R.n) n| of the linear 10-DoF solution / kt "
            "(contact.rigid_floor.L1.bushing_stiffness_per_pad_N_m)",
        ),
    ]
    att_ref = ref["attitude_change_deg"]
    info = [
        check_abs(
            "V12-info",
            f"{case}: cylinder force (motor force) per leg (+-1 % W/4)",
            stats.motor_force_mean_N,
            ref["cylinder_force_N"],
            V12_VERTICAL_FRACTION_OF_QUARTER_WEIGHT * quarter,
            "N",
            ref_key=f"{key} / cylinder_force_N",
        ),
        check_abs(
            "V12-info",
            f"{case}: attitude change roll, pitch (V3 tolerance 0.002 deg)",
            [stats.roll_mean_deg, stats.pitch_mean_deg],
            att_ref,
            V12_ATTITUDE_ABS_TOL_DEG,
            "deg",
            ref_key=f"{key} / attitude_change_deg (roll, pitch)",
        ),
        check_rel(
            "V12-info",
            f"{case}: friction utilisation T/N per leg (+-10 %)",
            stats.tangential_mean_N / stats.normal_mean_N,
            ref["friction_utilisation"],
            0.10,
            "-",
            ref_key=f"{key} / friction_utilisation_T_over_N",
        ),
        check_abs(
            "V12-info",
            f"{case}: horizontal reaction sum x, y (static balance)",
            r_got[:, :2].sum(axis=0),
            [0.0, 0.0],
            1.0,
            "N",
        ),
    ]
    return checks, info


V12_PLAN_A_DIAGNOSTIC_TOL_N = 3.0
"""Plan rev. 10: Chrono - reference within 3 N per leg of the option-A expectation means the
difference is explained by the bushing move + P-delta (diagnosis; V12 tolerances unchanged)."""


def v12_plan_a_diagnosis(
    refs: References, case: str, reaction_world_mean_N: ArrayLike
) -> list[CheckResult]:
    """Compare Chrono - reference with the expected option-A difference (vertical, x, y).

    Args:
        reaction_world_mean_N: (4, 3) mean floor -> rod reaction in world axes
            (:attr:`SlopeWindowStats.reaction_world_mean_N`).

    Returns:
        Two diagnostic results (``V12-diag``, not part of the V12 verdict): vertical and
        horizontal x, y, each ``|(Chrono - reference) - expected| <= 3 N`` per leg.
    """
    reference_block = refs.get(SLOPE_V12_L1, case=case)
    reference_N = reference_reaction_world_N(
        reference_block["contact_vertical_N"], reference_block["contact_horizontal_xy_N"]
    )
    expected_key = SLOPE_V12_L1_PLAN_A_EXPECTED_DIFF_REV13.resolve(case=case).notation()
    expected = refs.get(SLOPE_V12_L1_PLAN_A_EXPECTED_DIFF_REV13, case=case)[
        "expected_chrono_minus_reference"
    ]
    expected_N = reference_reaction_world_N(
        expected["contact_vertical_N"], expected["contact_horizontal_xy_N"]
    )
    chrono_minus_reference_N = np.asarray(reaction_world_mean_N, dtype=float) - reference_N
    note = "diagnosis only (plan rev. 10); V12 tolerances unchanged"
    return [
        check_abs(
            "V12-diag",
            f"{case}: vertical Chrono - reference vs option-A expectation (<= 3 N)",
            chrono_minus_reference_N[:, 2],
            expected_N[:, 2],
            V12_PLAN_A_DIAGNOSTIC_TOL_N,
            "N",
            ref_key=f"{expected_key} / expected_chrono_minus_reference / contact_vertical_N",
            note=note,
        ),
        check_abs(
            "V12-diag",
            f"{case}: horizontal x, y Chrono - reference vs option-A expectation (<= 3 N)",
            chrono_minus_reference_N[:, :2],
            expected_N[:, :2],
            V12_PLAN_A_DIAGNOSTIC_TOL_N,
            "N",
            ref_key=f"{expected_key} / expected_chrono_minus_reference / contact_horizontal_xy_N",
            note=note,
        ),
    ]


def hold_checks(
    case: str,
    *,
    release_t_s: Sequence[float],
    max_tangential_N: Sequence[float],
    ramp_end_s: float,
    friction: float,
    touch_threshold_N: float,
) -> list[CheckResult]:
    """Initial-hold safety items (``dynamics_model.md`` 5.3 ruling 1, conditions 2-3).

    Args:
        release_t_s: Hold release time per leg, ramp time base [s] (NaN = never released).
        max_tangential_N: Largest bushing force per leg while held [N]
            (``GroundBushingCoulomb.hold_max_tangential_N``).
        ramp_end_s: End of the gravity ramp, same time base [s].
        friction: Coulomb coefficient ``mu``; touch_threshold_N: ``N_th`` [N].

    Returns:
        Two judged checks: every leg released by the ramp end (NaN fails), and
        ``max |T|_hold <= mu N_th`` (50 N with the current values).
    """
    release = np.asarray(release_t_s, dtype=float)
    limit = float(friction) * float(touch_threshold_N)
    return [
        check_max(
            "V12",
            f"{case}: initial hold released by the end of the gravity ramp (release time)",
            release,
            float(ramp_end_s),
            "s",
            note="dynamics_model.md 5.3 ruling 1 condition 2 (NaN = still held -> fail)",
        ),
        check_max(
            "V12",
            f"{case}: max tangential bushing force while held (<= mu N_th)",
            np.asarray(max_tangential_N, dtype=float),
            limit,
            "N",
            note=f"mu {friction:g} x N_th {touch_threshold_N:g} N "
            "(dynamics_model.md 5.3 ruling 1 condition 3)",
        ),
    ]


def slope_v13_checks(refs: References, case: str, stats: SlopeWindowStats) -> list[CheckResult]:
    """V13 / 4.5 item 1 on the last 5 s of a slope run."""
    quarter = float(refs.get(TOTAL_WEIGHT_INCL_RODS_N)) / 4.0
    return [
        check_max(
            "V13",
            f"{case}: attitude drift in the still window (roll, pitch span)",
            [stats.roll_span_deg, stats.pitch_span_deg],
            V13_DRIFT_DEG,
            "deg",
        ),
        check_max(
            "V13",
            f"{case}: normal force variation per leg (span)",
            stats.normal_span_N,
            V13_FORCE_FRACTION_OF_QUARTER_WEIGHT * quarter,
            "N",
            note="tol = 0.1 % W/4",
        ),
        check_equal("V13", f"{case}: no NaN", stats.any_nan, False),
        check_max(
            "V13",
            f"{case}: motor constraint violation",
            stats.motor_violation_max_m,
            1.0e-6,
            "m",
        ),
        check_equal(
            "V13",
            f"{case}: one contact per leg (callback min, max)",
            [stats.contacts_min.tolist(), stats.contacts_max.tolist()],
            [[1] * len(LEG_ORDER), [1] * len(LEG_ORDER)],
        ),
        check_max(
            "V13",
            f"{case}: crawler contact force (must stay 0)",
            stats.crawler_force_max_N,
            0.0,
            "N",
        ),
    ]
