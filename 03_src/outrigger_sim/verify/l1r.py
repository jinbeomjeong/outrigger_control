"""L1-R checks of the locked rod-side chamber cases: V7a, V7b, V5 +0.3 mm (V9-1) and V9-2.

``dynamics_model.md`` rev. 32: 5.14.6 (V7a cases and validity gate), 5.14.7 (V7b free vibration
through the knee, record judgement), 5.14.8 (V5 +0.3 mm at 0.5 mm/s, the V9-1 smooth test with
and without the predictor, V9-2 redefined as the V7a top roll run), 5.14.12 (rev. 32 suppl. 5:
V9-1 order ratio recorded when the run-dt error is small, predictor-off two-dt ratio judged).
Reference values come from
the ``L1R_rod_side_reference_rev32`` block (``verify.reference`` ``L1R_*`` keys).

Engine independent: the inputs are the per-step module records (``N``, state) and the sampled
rigid displacement ``q`` the run script saved, plus the identification rows of the S4 rule
(``verify.s4.ModeRow``). Automatic pass / fail is a pre-check; the physical judgement is the
dynamics-expert's. Check ids: ``V7a gate`` / ``V7a`` (judged), ``V7b`` (record judgement,
5.12.5: a miss sends the case to dynamics before S6), ``V5p3 gate``, ``V9`` and ``V5``.

"Module elastic N change" is the module normal force minus its value at the first step of the
run (5.14.6 "모듈 N − 시작값"). Knee crossings are LOCK <-> FLOOR state changes of the module.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.hydraulics.rod_chamber import RodChamberMode
from outrigger_sim.params import LEG_ORDER
from outrigger_sim.verify.checks import CheckResult, check_abs, check_equal, check_max, check_rel
from outrigger_sim.verify.metrics import fit_damped_sine
from outrigger_sim.verify.s3 import (
    V9_ORDER_RATIO,
    V9_ORDER_RATIO_REL_TOL,
    V9_TRANSIENT_REL_TOL,
    order_ratio,
    v5_l1r_checks,
    v9_checks,
)
from outrigger_sim.verify.s4 import ModeRow, mode_checks

# --- V7a (5.14.6) --------------------------------------------------------------------------------
V7A_GATE_PEAK_OVER_KNEE_MAX = 0.5
"""Validity (2): per-leg max module elastic N increase <= 0.5 knee load (front 2,044.5 N, rear
1,585.1 N after an extension)."""

# --- V7b (5.14.7, record judgement) --------------------------------------------------------------
V7B_MAX_DN_REL_TOL = 0.03
V7B_MEAN_PERIOD_REL_TOL = 0.01
V7B_ETA_PEAK_REL_TOL = 0.03
V7B_FLOOR_DWELL_REL_TOL = 0.10
V7B_FLOOR_DWELL_ABS_TOL_S = 0.005
"""FLOOR dwell: +-10 % or +-5 ms, whichever is larger."""
V7B_KNEE_COUNT_REL_TOL = 0.10
V7B_FIRST_KNEE_TOL_S = 1.0e-3
V7B_N_PERIODS = 10
V7B_N_PEAKS = 3
V7B_REPLICA_BY_DT: Mapping[float, str] = {
    2.0e-4: "with_zeta_num_2e-4 (judge the 2e-4 s run)",
    1.0e-5: "physical (judge the 1e-5 s run)",
}
"""Replica variant each run time step is compared with (5.14.7)."""

# --- V5 +0.3 mm / V9-1 (5.14.8) ------------------------------------------------------------------
V5P3_DELTA_MM = 0.3
V5P3_RR_PEAK_OVER_KNEE_MAX = 0.8
"""Smoothness (validity): RR max module elastic N increase <= 0.8 knee (2,536 N)."""
V5P3_TRANSIENT_WINDOW_S = (0.5, 3.6)
"""Transient window of the replica (``transient V9 [0.5, 3.6] s``), time from the run start."""
V5P3_END_PERIODS = 3
"""End values: mean over the last three LOCK first-mode periods of the run."""
V5P3_TRANSIENT_MATCH_REL_TOL = 0.03
V5P3_TRANSIENT_MATCH_TIME_TOL_S = 0.010
"""Replica transient match (record): RL min elastic dN +-3 %, its time +-10 ms."""
V9_1_ORDER_RECORD_ONLY_FRACTION = 0.1
"""5.14.12 rule (rev. 32 suppl. 5, L1-R V9-1 only): when the error of the run dt (the largest
dt, 2e-4 s) against the reference run is at most this fraction of the V9 transient tolerance
(1 %), the successive error ratio is recorded and the order is confirmed by the predictor-off
two-dt ratio (judged here) and the V9-2 ratio (judged in ``v9_free_checks``)."""
RL = LEG_ORDER.index("RL")
RR = LEG_ORDER.index("RR")

# --- V9-2 L1-R (5.14.8 last item) -----------------------------------------------------------------
V9_FREE_AT_S = 5.0
"""Mode-1 amplitude / phase read at t = 5 s of the 6 s V7a top roll run."""

_LOCK = int(RodChamberMode.LOCK)
_FLOOR = int(RodChamberMode.FLOOR)
_LIFT = int(RodChamberMode.LIFT)


def _legs(values: ArrayLike) -> list[float]:
    return [float(v) for v in np.asarray(values, dtype=float).reshape(-1)]


# --- module records ------------------------------------------------------------------------------


@dataclass(frozen=True)
class ModuleRecord:
    """Per-step module record of one L1-R run (``series.npz`` ``t_step``, ``N_step``,
    ``mode_step``)."""

    t_s: NDArray[np.float64]
    """End time of every step from the run start (s)."""
    normal_N: NDArray[np.float64]
    """Module elastic normal force per step and leg, (n_steps, 4)."""
    mode: NDArray[np.int_]
    """``RodChamberMode`` value per step and leg, (n_steps, 4)."""
    dt_s: float

    @classmethod
    def from_arrays(
        cls, t_s: ArrayLike, normal_N: ArrayLike, mode: ArrayLike, dt_s: float
    ) -> ModuleRecord:
        return cls(
            np.asarray(t_s, dtype=float),
            np.asarray(normal_N, dtype=float),
            np.asarray(mode, dtype=int),
            float(dt_s),
        )

    @property
    def elastic_change_N(self) -> NDArray[np.float64]:
        """Module N minus its value at the first step (5.14.6), (n_steps, 4)."""
        return self.normal_N - self.normal_N[0]


@dataclass(frozen=True)
class KneeRecord:
    """Knee-related quantities of one run (V7b, V5 smoothness)."""

    max_dN_N: list[float]
    min_dN_N: list[float]
    floor_dwell_s: list[float]
    """FLOOR steps x dt per leg."""
    floor_or_lift_steps: list[int]
    lift_steps: list[int]
    n_knee_crossings: int
    """LOCK <-> FLOOR changes over all legs."""
    first_knee_crossing_s: float | None
    first_knee_crossing_leg: str | None
    end_all_lock: bool


def knee_record(module: ModuleRecord) -> KneeRecord:
    """Knee crossings, FLOOR dwell and module elastic N extremes of a run."""
    dN = module.elastic_change_N
    mode = module.mode
    is_floor = mode == _FLOOR
    is_lift = mode == _LIFT
    knee_pairs = {(_LOCK, _FLOOR), (_FLOOR, _LOCK)}
    crossings: list[tuple[float, int]] = []
    for k in range(1, len(mode)):
        for leg in np.flatnonzero(mode[k] != mode[k - 1]):
            if (int(mode[k - 1, leg]), int(mode[k, leg])) in knee_pairs:
                crossings.append((float(module.t_s[k]), int(leg)))
    first = crossings[0] if crossings else None
    return KneeRecord(
        max_dN_N=_legs(dN.max(axis=0)),
        min_dN_N=_legs(dN.min(axis=0)),
        floor_dwell_s=_legs(is_floor.sum(axis=0) * module.dt_s),
        floor_or_lift_steps=[int(v) for v in (is_floor | is_lift).sum(axis=0)],
        lift_steps=[int(v) for v in is_lift.sum(axis=0)],
        n_knee_crossings=len(crossings),
        first_knee_crossing_s=None if first is None else first[0],
        first_knee_crossing_leg=None if first is None else LEG_ORDER[first[1]],
        end_all_lock=bool(np.all(mode[-1] == _LOCK)),
    )


# --- modal coordinate records --------------------------------------------------------------------


def local_maxima(t: ArrayLike, y: ArrayLike) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Local maxima of ``y`` refined by a parabola through three samples (the replica rule,
    ``l1r_reference._peaks``): ``(t_peak, y_peak)``."""
    tt = np.asarray(t, dtype=float)
    yy = np.asarray(y, dtype=float)
    index = np.flatnonzero((yy[1:-1] > yy[:-2]) & (yy[1:-1] >= yy[2:])) + 1
    t_peak, y_peak = [], []
    for k in index:
        y0, y1, y2 = yy[k - 1], yy[k], yy[k + 1]
        curvature = y0 - 2.0 * y1 + y2
        shift = 0.5 * (y0 - y2) / curvature if curvature != 0.0 else 0.0
        t_peak.append(tt[k] + shift * (tt[k + 1] - tt[k]))
        y_peak.append(y1 - 0.25 * (y0 - y2) * shift)
    return np.asarray(t_peak), np.asarray(y_peak)


def up_crossing_times(t: ArrayLike, y: ArrayLike) -> NDArray[np.float64]:
    """Linearly interpolated times where ``y`` crosses zero upwards (replica rule)."""
    tt = np.asarray(t, dtype=float)
    yy = np.asarray(y, dtype=float)
    i = np.flatnonzero((yy[:-1] < 0.0) & (yy[1:] >= 0.0))
    return tt[i] - yy[i] * (tt[i + 1] - tt[i]) / (yy[i + 1] - yy[i])


@dataclass(frozen=True)
class ModalRecord:
    """Period and peaks of the dominant LOCK modal coordinate ``eta`` (V7b)."""

    periods_s: list[float]
    """First :data:`V7B_N_PERIODS` up-crossing periods."""
    mean_period_s: float
    positive_peaks: list[float]
    """First :data:`V7B_N_PEAKS` positive local maxima (sqrt(kg) m)."""


def modal_record(t: ArrayLike, eta: ArrayLike) -> ModalRecord:
    """Up-crossing periods and positive peaks of one modal coordinate."""
    periods = np.diff(up_crossing_times(t, eta))[:V7B_N_PERIODS]
    _, peaks = local_maxima(t, eta)
    positive = peaks[peaks > 0.0][:V7B_N_PEAKS]
    return ModalRecord(
        periods_s=_legs(periods),
        mean_period_s=float(periods.mean()) if periods.size else math.nan,
        positive_peaks=_legs(positive),
    )


# --- V7a -----------------------------------------------------------------------------------------


def v7a_gate_checks(
    case: str,
    *,
    non_lock_steps: Sequence[int],
    dN_max_N: Sequence[float],
    knee_N: Sequence[float],
    yield_steps: Sequence[int],
    predicted_peak_N: Sequence[float] | None = None,
) -> list[CheckResult]:
    """V7a validity gate (5.14.6): (1) LOCK at every step and leg, (2) per-leg max module elastic
    N increase <= 0.5 knee, (3) no bushing yield step. A failed gate makes the case invalid
    (rerun at half the amplitude).

    Args:
        dN_max_N: Per-leg maximum of module N minus its start value (an increase approaches the
            knee; the decrease side is recorded by the caller).
        predicted_peak_N: Linear LOCK prediction per leg (``predicted_peak_elastic_dN_N``); the
            measured / predicted ratio goes into the note.
    """
    limit = np.asarray(knee_N, dtype=float) * V7A_GATE_PEAK_OVER_KNEE_MAX
    peak = np.asarray(dN_max_N, dtype=float)
    note = "ratio to the knee " + ", ".join(
        f"{r:.3f}" for r in peak / np.asarray(knee_N, dtype=float)
    )
    if predicted_peak_N is not None:
        ratio = peak / np.asarray(predicted_peak_N, dtype=float)
        note += "; measured / predicted " + ", ".join(f"{r:.3f}" for r in ratio)
    return [
        check_equal(
            "V7a gate", f"{case}: non-LOCK steps per leg (FLOOR / LIFT entries)",
            [int(v) for v in non_lock_steps], [0] * len(LEG_ORDER),
        ),
        CheckResult(
            "V7a gate", f"{case}: max module elastic dN per leg <= 0.5 knee",
            _legs(peak), _legs(limit), V7A_GATE_PEAK_OVER_KNEE_MAX, "max (per leg)", "N",
            bool(np.all(np.isfinite(peak)) and np.all(peak <= limit)),
            deviation=_legs(peak / limit), note=note,
        ),
        check_equal(
            "V7a gate", f"{case}: bushing yield steps per leg",
            [int(v) for v in yield_steps], [0] * len(LEG_ORDER),
        ),
    ]


def v7a_mode_checks(
    rows: Sequence[ModeRow], *, level: str, ref_key_f: str, ref_key_zeta: str
) -> list[CheckResult]:
    """V7a natural frequency +-3 % and zeta (``- r omega dt / 2``) +-30 % of the LOCK modes,
    judged value of the S4 rule (``verify.s4.judged_value``), id ``V7a``."""
    return mode_checks(rows, check_id="V7a", ref_key_f=ref_key_f, ref_key_zeta=ref_key_zeta,
                       label=f"{level} LOCK")


def floor_distance_record(f_identified_Hz: Sequence[float],
                          f_floor_Hz: Sequence[float]) -> list[float]:
    """Identified f / FLOOR f - 1 per mode (record: knee-state confusion diagnosis, 5.14.6)."""
    return [float(f) / float(g) - 1.0 for f, g in zip(f_identified_Hz, f_floor_Hz, strict=True)]


# --- V7b -----------------------------------------------------------------------------------------


def _floor_dwell_tolerance_s(reference_s: float) -> float:
    return max(V7B_FLOOR_DWELL_REL_TOL * abs(reference_s), V7B_FLOOR_DWELL_ABS_TOL_S)


def _floor_dwell_check(case: str, measured_s: Sequence[float],
                       reference_s: Sequence[float]) -> CheckResult:
    measured = np.asarray(measured_s, dtype=float)
    reference = np.asarray(reference_s, dtype=float)
    tolerance = np.array([_floor_dwell_tolerance_s(r) for r in reference])
    deviation = measured - reference
    return CheckResult(
        "V7b", f"{case}: FLOOR dwell per leg (module FLOOR steps x dt)",
        _legs(measured), _legs(reference), _legs(tolerance), "abs (max(10 %, 5 ms))", "s",
        bool(np.all(np.isfinite(measured)) and np.all(np.abs(deviation) <= tolerance)
             and np.all(measured > 0.0)),
        deviation=_legs(deviation), note="0 means the knee is not implemented",
    )


def _first_knee_check(case: str, knee: KneeRecord,
                      replica_crossings: Sequence[Sequence[Any]]) -> CheckResult:
    reference_s = float(replica_crossings[0][0]) if replica_crossings else math.nan
    measured_s = math.nan if knee.first_knee_crossing_s is None else knee.first_knee_crossing_s
    reference_leg = str(replica_crossings[0][1]) if replica_crossings else None
    return check_abs(
        "V7b", f"{case}: first knee crossing time (record)", measured_s, reference_s,
        V7B_FIRST_KNEE_TOL_S, "s",
        note=f"leg {knee.first_knee_crossing_leg} (replica {reference_leg}); the module "
        "reports the crossing at the end of its step",
    )


def v7b_checks(
    case: str,
    *,
    knee: KneeRecord,
    modal: ModalRecord,
    replica: Mapping[str, Any],
    yield_steps: Sequence[int],
    ref_key: str,
) -> list[CheckResult]:
    """V7b record judgement (5.14.7) of one run against its replica variant.

    Args:
        replica: ``V7b_cases / <case> / replica / <variant>`` (:data:`V7B_REPLICA_BY_DT`).
        yield_steps: Bushing yield steps per leg of the run.
    """
    peaks_ref = [float(p[1]) for p in replica["eta_peaks_first10 (t_s, sqrt(kg) m)"]]
    peaks_ref = peaks_ref[:V7B_N_PEAKS]
    measured_peaks = list(modal.positive_peaks) + [math.nan] * V7B_N_PEAKS
    lift_or_yield = [a + b for a, b in zip(knee.lift_steps, yield_steps, strict=True)]
    return [
        check_rel("V7b", f"{case}: max module elastic dN per leg", knee.max_dN_N,
                  replica["max_elastic_dN_N"], V7B_MAX_DN_REL_TOL, "N", ref_key=ref_key),
        check_rel("V7b", f"{case}: mean period of the first {V7B_N_PERIODS} eta up-crossings",
                  modal.mean_period_s, replica["mean_period_first10_s"],
                  V7B_MEAN_PERIOD_REL_TOL, "s", ref_key=ref_key,
                  note=f"dominant LOCK mode {replica['dominant_LOCK_mode (1-based)']}, LOCK Phi"),
        check_rel("V7b", f"{case}: first {V7B_N_PEAKS} positive eta peaks",
                  measured_peaks[:V7B_N_PEAKS], peaks_ref, V7B_ETA_PEAK_REL_TOL, "sqrt(kg) m",
                  ref_key=ref_key),
        _floor_dwell_check(case, knee.floor_dwell_s, replica["FLOOR_dwell_s (dN > knee)"]),
        check_rel("V7b", f"{case}: knee crossings (record)", knee.n_knee_crossings,
                  replica["n_knee_crossings"], V7B_KNEE_COUNT_REL_TOL, "1", ref_key=ref_key),
        _first_knee_check(case, knee, replica["knee_crossings (t_s, leg)"]),
        check_equal("V7b", f"{case}: lift-off (LIFT steps) + bushing yield steps per leg",
                    lift_or_yield, [0] * len(LEG_ORDER)),
        check_equal("V7b", f"{case}: all four legs LOCK at the window end", knee.end_all_lock,
                    True),
    ]


# --- V5 +0.3 mm / V9-1 ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SmoothStepRecord:
    """V5 +0.3 mm at 0.5 mm/s quantities of one run (5.14.8)."""

    knee: KneeRecord
    transient_min_dN_RL_N: float
    transient_t_min_RL_s: float
    end_dN_N: list[float]
    """Mean module elastic dN per leg over the end window."""
    end_attitude_deg: list[float]
    """Mean (roll, pitch) over the end window."""
    end_dattitude_deg: list[float]
    """End attitude minus the attitude of the first sample."""
    end_window_s: tuple[float, float]


def smooth_step_record(
    module: ModuleRecord,
    *,
    t_s: ArrayLike,
    attitude_deg: ArrayLike,
    end_window_s: tuple[float, float],
) -> SmoothStepRecord:
    """Transient RL minimum, end values and knee record of a V5 +0.3 mm run.

    Args:
        t_s: Sample times of ``attitude_deg`` from the run start.
        attitude_deg: (roll, pitch) per sample.
        end_window_s: Mean window of the end values (last three LOCK first-mode periods).
    """
    dN = module.elastic_change_N
    lo, hi = V5P3_TRANSIENT_WINDOW_S
    transient = (module.t_s >= lo) & (module.t_s <= hi)
    k_min = int(np.argmin(np.where(transient, dN[:, RL], np.inf)))
    end_steps = (module.t_s >= end_window_s[0]) & (module.t_s <= end_window_s[1])
    tt = np.asarray(t_s, dtype=float)
    attitude = np.asarray(attitude_deg, dtype=float)
    end_samples = (tt >= end_window_s[0]) & (tt <= end_window_s[1])
    end_attitude = attitude[end_samples].mean(axis=0)
    return SmoothStepRecord(
        knee=knee_record(module),
        transient_min_dN_RL_N=float(dN[k_min, RL]),
        transient_t_min_RL_s=float(module.t_s[k_min]),
        end_dN_N=_legs(dN[end_steps].mean(axis=0)),
        end_attitude_deg=_legs(end_attitude),
        end_dattitude_deg=_legs(end_attitude - attitude[0]),
        end_window_s=(float(end_window_s[0]), float(end_window_s[1])),
    )


def smooth_validity_checks(label: str, record: SmoothStepRecord,
                           knee_N: Sequence[float]) -> list[CheckResult]:
    """Smoothness (5.14.8 validity): no FLOOR / LIFT step, RR max elastic dN <= 0.8 knee."""
    limit = V5P3_RR_PEAK_OVER_KNEE_MAX * float(knee_N[RR])
    rr_peak = record.knee.max_dN_N[RR]
    return [
        check_equal("V5p3 gate", f"{label}: FLOOR / LIFT steps per leg",
                    record.knee.floor_or_lift_steps, [0] * len(LEG_ORDER)),
        check_max("V5p3 gate", f"{label}: RR max module elastic dN <= 0.8 knee", rr_peak, limit,
                  "N", note=f"{rr_peak / float(knee_N[RR]):.4f} knee"),
    ]


def order_record_only_rule(transient_by_dt: Mapping[float, float], *,
                           ref_dt_s: float) -> dict[str, Any]:
    """5.14.12 condition of the V9-1 order ratio: is the run-dt error small enough to record it?

    The run dt is the largest dt of ``transient_by_dt`` (the YAML L1 dt, 2e-4 s).

    Returns:
        The run dt, its relative error against ``ref_dt_s``, the limit (0.1 x 1 %) and
        ``applies`` (error <= limit: the successive ratio is recorded, not judged).
    """
    run_dt_s = max(transient_by_dt)
    relative_error = abs(transient_by_dt[run_dt_s] / transient_by_dt[ref_dt_s] - 1.0)
    limit = V9_1_ORDER_RECORD_ONLY_FRACTION * V9_TRANSIENT_REL_TOL
    return {"run_dt_s": run_dt_s, "run_dt_relative_error": relative_error,
            "limit_relative_error": limit, "applies": bool(relative_error <= limit)}


def predictor_off_order_check(
    label: str, off_transient_by_dt: Mapping[float, float], *, ref_transient_N: float,
) -> tuple[CheckResult, dict[str, Any]]:
    """Predictor-off two-dt error ratio of the transient RL minimum (5.14.12 (i), judged).

    ``e(dt) = off(dt) - ref`` with the predictor-on reference run; the ratio
    ``e(dt) / e(dt/2)`` of the two largest dt is judged 2 +- 20 % (as the S3 V9 order ratio).

    Raises:
        ValueError: If there are fewer than two dt or the two largest are not in a 2:1 ratio.
    """
    dts = sorted(off_transient_by_dt, reverse=True)
    if len(dts) < 2 or not math.isclose(dts[0], 2.0 * dts[1], rel_tol=1e-9):
        raise ValueError(f"need two time steps in a 2:1 ratio, got {dts}")
    coarse_dt, fine_dt = dts[:2]
    coarse_error = off_transient_by_dt[coarse_dt] - ref_transient_N
    fine_error = off_transient_by_dt[fine_dt] - ref_transient_N
    ratio = coarse_error / fine_error if fine_error != 0.0 else math.nan
    is_finite = math.isfinite(ratio)
    check = CheckResult(
        "V9",
        f"{label}: predictor-off error ratio vs reference, transient min elastic dN_RL "
        f"(dt {coarse_dt:g}/{fine_dt:g} s, 5.14.12)",
        ratio, V9_ORDER_RATIO, V9_ORDER_RATIO_REL_TOL, "rel", "1",
        bool(is_finite and abs(ratio - V9_ORDER_RATIO) <= V9_ORDER_RATIO_REL_TOL * V9_ORDER_RATIO),
        deviation=ratio / V9_ORDER_RATIO - 1.0 if is_finite else None,
        note=f"errors {coarse_error:.4e}, {fine_error:.4e} N",
    )
    record = {"dt_s": [coarse_dt, fine_dt], "error_N": [coarse_error, fine_error],
              "ratio": ratio}
    return check, record


def v9_smooth_checks(
    label: str, records_by_dt: Mapping[float, SmoothStepRecord], *, ref_dt_s: float,
    total_weight_N: float,
    predictor_off_by_dt: Mapping[float, SmoothStepRecord] | None = None,
) -> tuple[list[CheckResult], dict[str, Any]]:
    """V9-1 of the smooth test (5.14.8, rule of 5.14.12): differences to ``ref_dt_s``
    (transient <= 1 %, end dN <= 0.1 % W/4, end attitude <= 1e-4 deg, ``verify.s3.v9_checks``)
    and the order of the transient RL minimum.

    Order: the successive error ratio of the three largest dt is judged 2 +- 20 % unless the
    5.14.12 condition holds (:func:`order_record_only_rule`) and predictor-off runs are given;
    then it is recorded only. The predictor-off two-dt ratio
    (:func:`predictor_off_order_check`) is judged whenever two predictor-off runs are given.

    Args:
        predictor_off_by_dt: Predictor-off runs (at least the two largest dt, 2:1), or None.

    Returns:
        ``(checks, record)``; the record holds the ratio of the errors against the reference run
        (information) and the 5.14.12 rule outcome.
    """
    transient = {dt: r.transient_min_dN_RL_N for dt, r in records_by_dt.items()}
    coarse = {dt: v for dt, v in transient.items() if dt != ref_dt_s}
    order = order_ratio(coarse)
    rule = order_record_only_rule(transient, ref_dt_s=ref_dt_s)
    has_predictor_off = predictor_off_by_dt is not None and len(predictor_off_by_dt) >= 2
    is_order_judged = not (rule["applies"] and has_predictor_off)
    checks = v9_checks(
        label, dts_s=sorted(records_by_dt, reverse=True),
        static_force_N={dt: r.end_dN_N for dt, r in records_by_dt.items()},
        total_weight_N=total_weight_N,
        final_attitude_deg={dt: r.end_attitude_deg for dt, r in records_by_dt.items()},
        transient_peak_N=transient, ref_dt_s=ref_dt_s,
        order={"transient min elastic dN_RL (module N)": order} if is_order_judged else None,
    )
    errors = {dt: transient[dt] - transient[ref_dt_s] for dt in order["dt_s"]}
    dts = order["dt_s"]
    order_key = ("order_successive_differences (judged)" if is_order_judged
                 else "order_successive_differences (record, 5.14.12)")
    record: dict[str, Any] = {
        "transient_min_dN_RL_N": transient,
        "transient_minus_ref_N": {dt: v - transient[ref_dt_s] for dt, v in transient.items()},
        order_key: order,
        "error_ratio_vs_ref (information)": [
            errors[dts[0]] / errors[dts[1]] if errors[dts[1]] else math.nan,
            errors[dts[1]] / errors[dts[2]] if errors[dts[2]] else math.nan,
        ],
        "order_rule_5_14_12": {**rule, "predictor_off_given": has_predictor_off,
                               "order_ratio_judged": is_order_judged},
    }
    if has_predictor_off:
        off_check, off_record = predictor_off_order_check(
            label, {dt: r.transient_min_dN_RL_N for dt, r in predictor_off_by_dt.items()},
            ref_transient_N=transient[ref_dt_s])
        checks.append(off_check)
        record["predictor_off_order (judged)"] = off_record
    if not is_order_judged:
        record["order_rule_5_14_12"]["order_confirmed_by"] = [
            "predictor_off_order (judged here)", "V9-2 amplitude error ratio (v9_free_checks)"]
    return checks, record


def v5_smooth_checks(
    dt_s: float, record: SmoothStepRecord, *, final_ref: Mapping[str, Any], ref_key: str
) -> list[CheckResult]:
    """V5 +0.3 mm (5.14.8): end module elastic dN within 5 % of the largest component of the
    replica end value, attitude change 5 % per component (``verify.s3.v5_l1r_checks``)."""
    checks = v5_l1r_checks(
        V5P3_DELTA_MM, dN_N=record.end_dN_N, dN_ref_N=final_ref["dF_N"], key_dN=ref_key,
        dattitude_deg=record.end_dattitude_deg,
        dattitude_ref_deg=final_ref["dattitude_deg (roll, pitch)"], key_att=ref_key,
    )
    return [replace(c, item=f"dt {dt_s:g} s, {c.item}") for c in checks]


def transient_match_record(record: SmoothStepRecord,
                           transient_ref: Mapping[str, Any]) -> dict[str, Any]:
    """Replica transient match (record, 5.14.8): RL min elastic dN +-3 %, time +-10 ms."""
    ref_min = float(transient_ref["min_dF_N"][RL])
    ref_t = float(transient_ref["t_min_RL_s"])
    rel = record.transient_min_dN_RL_N / ref_min - 1.0
    dt_s = record.transient_t_min_RL_s - ref_t
    return {
        "min_dN_RL_N": record.transient_min_dN_RL_N, "replica_min_dN_RL_N": ref_min,
        "relative_difference": rel,
        "within_3_percent": bool(abs(rel) <= V5P3_TRANSIENT_MATCH_REL_TOL),
        "t_min_RL_s": record.transient_t_min_RL_s, "replica_t_min_RL_s": ref_t,
        "time_difference_s": dt_s,
        "within_10_ms": bool(abs(dt_s) <= V5P3_TRANSIENT_MATCH_TIME_TOL_S),
    }


def predictor_off_record(
    off_by_dt: Mapping[float, SmoothStepRecord],
    on_by_dt: Mapping[float, SmoothStepRecord],
    *,
    ref_dt_s: float,
) -> dict[str, Any]:
    """V9-1 without the predictor (record, 5.14.8 / 5 V9 row): differences of the transient RL
    minimum and the end values to the predictor-on run of the same dt and to the reference."""
    ref = on_by_dt[ref_dt_s]
    out: dict[str, Any] = {}
    for dt, off in sorted(off_by_dt.items(), reverse=True):
        on = on_by_dt.get(dt)
        out[f"dt {dt:g} s"] = {
            "transient_min_dN_RL_N": off.transient_min_dN_RL_N,
            "transient_minus_ref_rel": off.transient_min_dN_RL_N / ref.transient_min_dN_RL_N
            - 1.0,
            "transient_minus_predictor_on_N": None if on is None
            else off.transient_min_dN_RL_N - on.transient_min_dN_RL_N,
            "end_dN_minus_ref_N": _legs(np.subtract(off.end_dN_N, ref.end_dN_N)),
            "end_attitude_minus_ref_deg": _legs(
                np.subtract(off.end_attitude_deg, ref.end_attitude_deg)),
            "within_V9_transient_1_percent": bool(
                abs(off.transient_min_dN_RL_N / ref.transient_min_dN_RL_N - 1.0)
                <= V9_TRANSIENT_REL_TOL),
            "FLOOR_or_LIFT_steps": off.knee.floor_or_lift_steps,
            "RR_max_dN_N": off.knee.max_dN_N[RR],
        }
    return out


# --- V9-2 L1-R ----------------------------------------------------------------------------------


def mode_amplitude_phase_at(t: ArrayLike, eta: ArrayLike, f_guess_Hz: float,
                            at_s: float = V9_FREE_AT_S) -> dict[str, float]:
    """Damped-cosine fit of one modal coordinate over the whole run; amplitude and unwrapped
    phase at ``at_s`` (the S3 V9-2 rule, fit time origin = first sample)."""
    tt = np.asarray(t, dtype=float)
    fit = fit_damped_sine(tt, eta, f_guess_Hz)
    tau = at_s - float(tt[0])
    return {
        "amplitude_at_s": fit.amplitude * math.exp(-fit.sigma_1_s * tau),
        "phase_at_s_rad_unwrapped": fit.phase_rad + 2.0 * math.pi * fit.f_damped_Hz * tau,
        "f_damped_Hz": fit.f_damped_Hz, "zeta": fit.zeta,
        "residual_rms_rel": fit.residual_rms_rel,
    }


def v9_free_checks(
    label: str, amplitude_by_dt: Mapping[float, float], phase_by_dt: Mapping[float, float], *,
    ref_dt_s: float,
) -> tuple[list[CheckResult], dict[str, Any]]:
    """V9-2 L1-R (V7a top roll, 6 s): error ratio of the mode-1 amplitude at 5 s judged
    (2 +- 20 %, as S3 V9-2); the amplitude difference to the reference run (1 % flag) and the
    phase are recorded."""
    coarse = {dt: a for dt, a in amplitude_by_dt.items() if dt != ref_dt_s}
    order_amplitude = order_ratio(coarse)
    checks = v9_checks(
        label, dts_s=sorted(amplitude_by_dt, reverse=True), static_force_N=None,
        total_weight_N=1.0, final_attitude_deg=None, transient_peak_N=None, ref_dt_s=ref_dt_s,
        order={"mode-1 amplitude at 5 s (LOCK Phi)": order_amplitude},
    )
    ref_amplitude = amplitude_by_dt[ref_dt_s]
    rel = {dt: a / ref_amplitude - 1.0 for dt, a in amplitude_by_dt.items()}
    record = {
        "amplitude_at_5s": dict(amplitude_by_dt),
        "amplitude_rel_to_ref": rel,
        "amplitude_within_1_percent (record)": {
            dt: bool(abs(r) <= V9_TRANSIENT_REL_TOL) for dt, r in rel.items()},
        "phase_at_5s_rad": dict(phase_by_dt),
        "phase_minus_ref_rad": {dt: p - phase_by_dt[ref_dt_s] for dt, p in phase_by_dt.items()},
        "order_amplitude (judged)": order_amplitude,
        "order_phase (record)": order_ratio(
            {dt: p for dt, p in phase_by_dt.items() if dt != ref_dt_s}),
    }
    return checks, record


__all__ = [
    "KneeRecord",
    "ModalRecord",
    "ModuleRecord",
    "SmoothStepRecord",
    "floor_distance_record",
    "knee_record",
    "local_maxima",
    "modal_record",
    "mode_amplitude_phase_at",
    "order_record_only_rule",
    "predictor_off_order_check",
    "predictor_off_record",
    "smooth_step_record",
    "smooth_validity_checks",
    "transient_match_record",
    "up_crossing_times",
    "v5_smooth_checks",
    "v7a_gate_checks",
    "v7a_mode_checks",
    "v7b_checks",
    "v9_free_checks",
    "v9_smooth_checks",
]
