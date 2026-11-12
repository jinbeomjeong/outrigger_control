"""Values of one harness run for the coupling verdict (criteria 6 V-2, 7.1 T inputs, 7.2, 7.3).

Pure numpy on the 1 ms chunk record of ``harness_flow`` and the 10 Hz controller log. Only values
come out: no threshold of the criteria is applied here (the verdict is control-expert's). The
limits inside definitions (r < 0.93, 1 s moving means, the 0.5 bar residual tie, the 1 s persistence
of T-4 inputs) are part of what the criteria measure, not verdicts.
"""
from __future__ import annotations

import numpy as np
from flow_share import SUPPLY_REL_TOL
from harness_flow import COLUMN, OIL_FORCE, P_LOAD, TRUE_FORCE, U, V, Y

LEGS = ("FL", "FR", "RL", "RR")
L_MIN_PER_M3_S = 6.0e4
PA_PER_BAR = 1e5
MM_PER_M = 1e3
KN_PER_N = 1e-3
CHUNK_S = 1e-3
MOVING_SPEED_EPS_M_S = 1e-6
"""A leg with a larger request counts as moving (``soil_guard_stop_rule``)."""
RELIEF_BAR = 210.0
LIFTOFF_RECORD_WINDOW_S = 8.0
"""S8 C1: rigid crawler lift-off transient window (spec rev. 40)."""
LAST_WINDOW_S = 5.0
"""Item 2: the last 5 s of the run after the first READY."""
MOVING_MEAN_S = 1.0
SPEED_RATIO_LIMIT = 0.93
SPEED_RATIO_MIN_REQUEST = 0.1
"""Criteria sec. 1: r_i only where the 1 s mean request is at least 0.1 v_max."""
DEADBAND_DEG = 0.03
SATURATION_PERSIST_S = 1.0
"""Criteria T-4: saturated legs and sets of at least this duration."""
PROBE_REFERENCE_S = 0.5
PHASE_READY = "ready"
PHASE_DONE = "done"
PHASE_TOUCH = "touch"
PHASE_PROBE = "probe"


def _rounded(value, digits: int = 6):
    if value is None:
        return None
    return round(float(value), digits)


def _leg_list(values, digits: int = 6) -> dict:
    return {leg: _rounded(value, digits) for leg, value in zip(LEGS, values, strict=True)}


def mask_legs(mask: int) -> list[str]:
    return [leg for i, leg in enumerate(LEGS) if int(mask) >> i & 1]


def contiguous_runs(flags: np.ndarray) -> list[tuple[int, int]]:
    """(first, last) index of the unbroken True runs of a bool array."""
    edges = np.diff(np.concatenate(([0], flags.astype(int), [0])))
    return list(zip(np.flatnonzero(edges == 1).tolist(),
                    (np.flatnonzero(edges == -1) - 1).tolist(), strict=True))


def moving_ratio(u: np.ndarray, v: np.ndarray, v_max: float) -> np.ndarray:
    """r = 1 s mean v / 1 s mean u; NaN below 0.1 v_max of request (criteria sec. 1)."""
    window = max(1, round(MOVING_MEAN_S / CHUNK_S))
    if len(u) < window:
        return np.full(len(u), np.nan)
    kernel = np.ones(window) / window
    mean_u, mean_v = np.convolve(u, kernel, "valid"), np.convolve(v, kernel, "valid")
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = np.where(np.abs(mean_u) >= SPEED_RATIO_MIN_REQUEST * v_max, mean_v / mean_u, np.nan)
    return np.concatenate([np.full(window - 1, np.nan), ratio])


def chunk_phases(rows: np.ndarray, period_t: np.ndarray, period_phase: np.ndarray) -> np.ndarray:
    """Phase of each chunk: the phase the controller ended the previous period with."""
    if len(period_t) == 0:
        return np.full(len(rows), "unknown", dtype=object)
    index = np.searchsorted(period_t, rows[:, COLUMN["t"]], side="left") - 1
    return np.where(index < 0, period_phase[0], period_phase[np.clip(index, 0, None)])


# ------------------------------------------------------------------------------------- V-2 (a)
def flow_conservation(rows: np.ndarray, supply_m3_s: float, counters: dict) -> dict:
    """Criteria V-2 (a): max sum Q_i / Q_sup - 1 and |v_i - u_i| on the demand-met chunks."""
    demand = rows[:, COLUMN["Q_dem"]]
    delivered = rows[:, COLUMN["Q_sum"]]
    is_met = demand <= supply_m3_s * (1.0 + SUPPLY_REL_TOL)
    speed_error = np.abs(rows[:, V] - rows[:, U])
    return {"max_sum_Q_over_supply_minus_1": _rounded((delivered / supply_m3_s - 1.0).max(), 12),
            "chunks": len(rows), "demand_met_chunks": int(is_met.sum()),
            "max_abs_v_minus_u_on_demand_met_m_s":
                float(speed_error[is_met].max()) if is_met.any() else None,
            **counters}


# --------------------------------------------------------------------------------- E-1 .. E-4
def exposure_by_phase(rows: np.ndarray, phases: np.ndarray, supply_m3_s: float) -> dict:
    """E-1: time with Q_dem > Q_sup and largest deficit per phase."""
    demand = rows[:, COLUMN["Q_dem"]]
    is_short = demand > supply_m3_s * (1.0 + SUPPLY_REL_TOL)
    table = {}
    for phase in sorted(set(phases.tolist())):
        in_phase = phases == phase
        deficit = float(max(0.0, (demand[in_phase] - supply_m3_s).max()))
        table[str(phase)] = {"duration_s": _rounded(in_phase.sum() * CHUNK_S, 3),
                             "short_s": _rounded((in_phase & is_short).sum() * CHUNK_S, 3),
                             "max_deficit_L_min": _rounded(deficit * L_MIN_PER_M3_S, 4)}
    return table


def speed_ratio_table(rows: np.ndarray, phases: np.ndarray, v_max: float) -> dict:
    """E-2: min r_i per leg and phase, longest r_i < 0.93 per leg."""
    table = {}
    for i, leg in enumerate(LEGS):
        ratio = moving_ratio(rows[:, U][:, i], rows[:, V][:, i], v_max)
        valid = np.isfinite(ratio)
        by_phase = {}
        for phase in sorted(set(phases.tolist())):
            selected = valid & (phases == phase)
            if selected.any():
                by_phase[str(phase)] = _rounded(ratio[selected].min(), 5)
        low_runs = contiguous_runs(valid & (ratio < SPEED_RATIO_LIMIT))
        longest = max((last - first + 1 for first, last in low_runs), default=0) * CHUNK_S
        table[leg] = {"min_r_by_phase": by_phase, "longest_below_0p93_s": _rounded(longest, 3)}
    return table


def tracking_error(rows: np.ndarray) -> dict:
    """E-3: integral of (u - v) per leg and its largest spread between legs [mm]."""
    integral_mm = np.cumsum((rows[:, U] - rows[:, V]) * CHUNK_S, axis=0) * MM_PER_M
    spread = integral_mm.max(axis=1) - integral_mm.min(axis=1)
    return {"max_abs_integral_mm": _leg_list(np.abs(integral_mm).max(axis=0), 3),
            "max_between_legs_mm": _rounded(spread.max(), 3)}


def count_disjoint_swaps(residual_masks: np.ndarray) -> tuple[int, np.ndarray]:
    """E-4 (revision 3): a swap = a residual group sharing no leg with the group before it.

    Non-saturated chunks (mask 0) are passed over: the comparison is with the last group seen.
    Returns the count and the chunk indices of the swaps.
    """
    indices = []
    previous = 0
    for index, mask in enumerate(residual_masks.astype(int)):
        if mask == 0:
            continue
        if previous != 0 and (mask & previous) == 0:
            indices.append(index)
        previous = mask
    return len(indices), np.array(indices, int)


def residual_groups(rows: np.ndarray) -> dict:
    """E-4: residual groups, swaps with their largest rate, gallery pressure, sample period."""
    masks = rows[:, COLUMN["residual_mask"]]
    count, swap_indices = count_disjoint_swaps(masks)
    max_per_second = 0
    if count:
        swap_times = rows[swap_indices, COLUMN["t"]]
        ends = np.searchsorted(swap_times, swap_times + 1.0, side="left")
        max_per_second = int((ends - np.arange(count)).max())
    time_by_group = {}
    for mask in np.unique(masks[masks > 0]).astype(int):
        name = "+".join(mask_legs(mask))
        time_by_group[name] = _rounded((masks == mask).sum() * CHUNK_S, 3)
    gallery = rows[:, COLUMN["p_P"]][masks > 0]
    return {"sample_period_s": CHUNK_S, "tie_width_bar": 0.5, "group_time_s": time_by_group,
            "disjoint_swaps": count, "max_disjoint_swaps_in_1s": max_per_second,
            "saturated_s": _rounded((masks > 0).sum() * CHUNK_S, 3),
            "gallery_bar_while_saturated": None if gallery.size == 0 else
            [_rounded(gallery.min() / PA_PER_BAR, 3), _rounded(gallery.max() / PA_PER_BAR, 3)]}


# ---------------------------------------------------------------------------------- T-4 inputs
def _operating_point(rows: np.ndarray, index: int) -> dict:
    row = rows[index]
    return {"t_s": _rounded(row[COLUMN["t"]], 3), "u_m_s": _leg_list(row[U], 9),
            "v_m_s": _leg_list(row[V], 9), "p_P_Pa": _rounded(row[COLUMN["p_P"]], 1),
            "p_load_Pa": _leg_list(row[P_LOAD], 1), "spool_drop_Pa": _leg_list(row[Y], 1),
            "Q_byp_m3_s": _rounded(row[COLUMN["Q_byp"]], 9)}


def saturation_inputs(rows: np.ndarray, valve_constants: dict) -> dict:
    """T-4 inputs: legs s and sets P saturated >= 1 s, with their operating points (u, p_P, p_i).

    The operating point is the middle chunk of the longest run. A leg counts as saturated on a
    chunk where the flow limit gave it less than its request and it was moving.
    """
    limited_masks = rows[:, COLUMN["limited_mask"]].astype(int)
    min_chunks = round(SATURATION_PERSIST_S / CHUNK_S)
    legs = {}
    for i, leg in enumerate(LEGS):
        moving = np.abs(rows[:, U][:, i]) > MOVING_SPEED_EPS_M_S
        runs = contiguous_runs(((limited_masks >> i) & 1).astype(bool) & moving)
        long_runs = [run for run in runs if run[1] - run[0] + 1 >= min_chunks]
        if not long_runs:
            continue
        first, last = max(long_runs, key=lambda run: run[1] - run[0])
        middle = (first + last) // 2
        legs[leg] = {"longest_s": _rounded((last - first + 1) * CHUNK_S, 3),
                     "runs_ge_1s": len(long_runs),
                     "set_at_operating_point": mask_legs(limited_masks[middle]),
                     "operating_point": _operating_point(rows, middle)}
    sets = {}
    for mask in np.unique(limited_masks[limited_masks > 0]):
        runs = contiguous_runs(limited_masks == mask)
        long_runs = [run for run in runs if run[1] - run[0] + 1 >= min_chunks]
        if not long_runs:
            continue
        first, last = max(long_runs, key=lambda run: run[1] - run[0])
        sets["+".join(mask_legs(mask))] = {
            "longest_s": _rounded((last - first + 1) * CHUNK_S, 3), "runs_ge_1s": len(long_runs),
            "operating_point": _operating_point(rows, (first + last) // 2)}
    return {"persist_s": SATURATION_PERSIST_S, "legs": legs, "sets": sets,
            "valve_constants": valve_constants}


# ------------------------------------------------------------------------------ run quantities
def _first_lift_index(rows: np.ndarray, phases: np.ndarray) -> int | None:
    """First chunk outside the pre-level phases with a crawler force of 0."""
    after_touch = ~np.isin(phases, ("idle", "check", PHASE_TOUCH))
    hits = np.flatnonzero((rows[:, COLUMN["crawler"]] == 0.0) & after_touch)
    return int(hits[0]) if hits.size else None


def first_lift_time_s(rows: np.ndarray, period_t: np.ndarray,
                      period_phase: np.ndarray) -> float | None:
    """First crawler lift-off of a run [s], the ``values.forces.t_lift_s`` rule and rounding.

    For runners without :func:`run_values` (``r79_sensor_screen``, v5 criteria rev. 2 2.1).

    Args:
        rows: The 1 ms chunk record of ``harness_flow``.
        period_t: Controller update times.
        period_phase: Controller phase after each update.

    Returns:
        The lift-off time, or None without a lift-off.
    """
    lift_index = _first_lift_index(rows, chunk_phases(rows, period_t, period_phase))
    if lift_index is None:
        return None
    return _rounded(rows[lift_index, COLUMN["t"]], 3)


def _force_minimum(rows: np.ndarray, selected: np.ndarray) -> dict | None:
    if not selected.any():
        return None
    force = rows[:, TRUE_FORCE]
    masked = np.where(selected[:, None], force, np.inf)
    index, leg = np.unravel_index(int(np.argmin(masked)), masked.shape)
    return {"min_kN": _rounded(force[index, leg] * KN_PER_N, 4), "leg": LEGS[int(leg)],
            "t_s": _rounded(rows[index, COLUMN["t"]], 3)}


def _attitude_deg(rows: np.ndarray) -> np.ndarray:
    return np.degrees(rows[:, [COLUMN["roll"], COLUMN["pitch"]]])


def _remove_moving_mean(values: np.ndarray, window: int) -> np.ndarray:
    if len(values) < window:
        return values - values.mean(axis=0)
    kernel = np.ones(window) / window
    mean = np.column_stack([np.convolve(values[:, k], kernel, "same")
                            for k in range(values.shape[1])])
    return (values - mean)[window // 2: len(values) - window // 2]


def attitude_values(rows: np.ndarray, phases: np.ndarray, lift_index: int | None,
                    period_filtered_deg: np.ndarray, period_t: np.ndarray,
                    t_ready_s: float | None) -> dict:
    """Items 2 and 5, R-2, R-7: true attitude of the last 5 s, after the lift-off, rocking."""
    attitude = _attitude_deg(rows)
    t = rows[:, COLUMN["t"]]
    out = {"end_abs_deg": _leg_axes(np.abs(attitude[-1])), "max_abs_last_5s_deg": None,
           "max_abs_after_liftoff_deg": None, "rocking_amplitude_deg": None,
           "filter_residual_last_5s_deg": None}
    if t_ready_s is not None:
        last = (t >= max(t[-1] - LAST_WINDOW_S, t_ready_s))
        out["max_abs_last_5s_deg"] = _rounded(np.abs(attitude[last]).max(), 5)
        in_tail = period_t >= max(period_t[-1] - LAST_WINDOW_S, t_ready_s)
        if in_tail.sum() >= 3:
            samples_per_second = round(MOVING_MEAN_S / 0.1)
            residual = _remove_moving_mean(period_filtered_deg[in_tail], samples_per_second)
            out["filter_residual_last_5s_deg"] = _rounded(np.abs(residual).max(), 5)
    if lift_index is not None:
        after = attitude[lift_index:]
        out["max_abs_after_liftoff_deg"] = _rounded(np.abs(after).max(), 5)
        window = round(MOVING_MEAN_S / CHUNK_S)
        out["rocking_amplitude_deg"] = _rounded(np.abs(_remove_moving_mean(after, window)).max(), 5)
    return out


def _leg_axes(values) -> dict:
    return {"roll": _rounded(values[0], 5), "pitch": _rounded(values[1], 5)}


def probe_attitude_change_deg(rows: np.ndarray, phases: np.ndarray) -> float | None:
    """Item 7 (1): largest attitude change in a probe against the 0.5 s mean before it."""
    attitude = _attitude_deg(rows)
    window = round(PROBE_REFERENCE_S / CHUNK_S)
    change = None
    for first, last in contiguous_runs(phases == PHASE_PROBE):
        if first < window:
            continue
        reference = attitude[first - window: first].mean(axis=0)
        peak = float(np.abs(attitude[first: last + 1] - reference).max())
        change = peak if change is None else max(change, peak)
    return _rounded(change, 5)


SATURATION_RULE = (
    "spec 320 item 4 (2) 'saturation stop 0 in a levelling run': number of (row, leg) samples "
    "with the leg extending (row speed U > MOVING_SPEED_EPS_M_S) and the true pressure "
    "TRUE_FORCE / A_p >= RELIEF_BAR (210 bar); a saturation stop needs an extending leg at the "
    "relief pressure, so 0 samples = 0 saturation stops (436.8 rules rev6 R6-C1 2)"
)
"""Rev6 R6-C1 2: the field description of ``values.pressure.saturation_leg_chunks`` (G-S reads
``values.pressure.saturation_rule``; record only)."""


def pressure_values(rows: np.ndarray, head_area_m2: np.ndarray) -> dict:
    """Item 4: largest moving pressure F_cyl / A_p and extending chunks at the relief pressure
    (:data:`SATURATION_RULE`)."""
    pressure_bar = rows[:, TRUE_FORCE] / head_area_m2 / PA_PER_BAR
    moving = np.abs(rows[:, U]) > MOVING_SPEED_EPS_M_S
    extending = rows[:, U] > MOVING_SPEED_EPS_M_S
    return {"max_moving_bar": _rounded(pressure_bar[moving].max(), 3) if moving.any() else None,
            "saturation_leg_chunks": int((extending & (pressure_bar >= RELIEF_BAR)).sum()),
            "saturation_rule": SATURATION_RULE}


def twist_values(rows: np.ndarray, phases: np.ndarray, lift_index: int | None,
                 twist_vector: np.ndarray) -> dict:
    """R-3: D = n^T F: largest |D| after the lift-off and |D| at the first DONE [kN]."""
    twist_kN = rows[:, TRUE_FORCE] @ np.asarray(twist_vector, float) * KN_PER_N
    done = np.flatnonzero(phases == PHASE_DONE)
    return {"peak_abs_after_liftoff_kN":
            None if lift_index is None else _rounded(np.abs(twist_kN[lift_index:]).max(), 3),
            "abs_at_first_done_kN": _rounded(abs(twist_kN[done[0]]), 3) if done.size else None}


def force_values(rows: np.ndarray, lift_index: int | None) -> dict:
    """Items 3, S8 C1, T-3 (a), R-1: true F_cyl minimum after the lift-off and around 8 s."""
    if lift_index is None:
        return {"after_liftoff": None, "first_8s": None, "after_8s": None, "t_lift_s": None}
    t = rows[:, COLUMN["t"]]
    t_lift = t[lift_index]
    after = t >= t_lift
    first = after & (t < t_lift + LIFTOFF_RECORD_WINDOW_S)
    return {"t_lift_s": _rounded(t_lift, 3), "after_liftoff": _force_minimum(rows, after),
            "first_8s": _force_minimum(rows, first),
            "after_8s": _force_minimum(rows, after & ~first)}


def integral_values(rows: np.ndarray, period_t: np.ndarray, period_integral: np.ndarray,
                    period_filtered_deg: np.ndarray, integral_limit: float) -> dict:
    """E-5: |I| at the end of the last saturation and the time back inside the 0.03 deg band."""
    limited = rows[:, COLUMN["limited_mask"]] > 0
    largest = float(np.abs(period_integral).max()) if len(period_integral) else 0.0
    out = {"integral_limit_rad_s": integral_limit, "max_abs_integral_rad_s": _rounded(largest, 6),
           "abs_integral_at_saturation_end_rad_s": None, "back_in_band_after_saturation_s": None}
    if not limited.any() or len(period_t) == 0:
        return out
    t_end = rows[np.flatnonzero(limited)[-1], COLUMN["t"]]
    index = min(int(np.searchsorted(period_t, t_end)), len(period_t) - 1)
    out["abs_integral_at_saturation_end_rad_s"] = _rounded(np.abs(period_integral[index]).max(), 6)
    in_band = np.abs(period_filtered_deg[index:]).max(axis=1) <= DEADBAND_DEG
    if in_band.any():
        back = period_t[index + int(np.argmax(in_band))] - t_end
        out["back_in_band_after_saturation_s"] = _rounded(max(back, 0.0), 2)
    return out


def period_phase_times(period_t: np.ndarray, period_phase: np.ndarray) -> dict:
    """First end of TOUCH, first DONE, first READY [s]; None when not reached."""
    def first(phase):
        hits = np.flatnonzero(period_phase == phase)
        return _rounded(period_t[hits[0]], 3) if hits.size else None

    not_touch = np.flatnonzero(~np.isin(period_phase, ("idle", "check", PHASE_TOUCH)))
    return {"t_touch_end_s": _rounded(period_t[not_touch[0]], 3) if not_touch.size else None,
            "t_first_done_s": first(PHASE_DONE), "t_first_ready_s": first(PHASE_READY)}


def event_counts(events: list[tuple[float, str]], t_lift_s: float | None) -> dict:
    """R-5, R-6, T-2: event name sets and counts."""
    names = [name for _, name in events]
    after_lift = [name for t, name in events if t_lift_s is not None and t >= t_lift_s]
    loc_times = [t for t, name in events if name == "crawler_liftoff_confirmed"]
    return {
        "fault_events": sorted({n for n in names if n.startswith("FAULT")}),
        "warn_events": sorted({n.split(":")[0] for n in names if n.startswith("WARN")}),
        "info_rule_events": sorted({n.split(":")[0] for n in names if n.startswith((
            "INFO_LOC_", "INFO_DIFF_SINK", "INFO_TWIST_UNSETTLED", "INFO_LIFT_PAUSED"))}),
        "soil_mode_started": any(n.startswith("soil_mode_start") for n in names),
        "t_loc_first_s": _rounded(loc_times[0], 3) if loc_times else None,
        "t_loc_last_s": _rounded(loc_times[-1], 3) if loc_times else None,
        "reapproach_starts_after_liftoff":
            sum(n.startswith("leg_reapproach_start") for n in after_lift),
        "p5_relevels_after_liftoff": sum(n.startswith(("relevel_predicted", "relevel_low"))
                                         for n in after_lift),
        "probe_aborts": sum(n.startswith("probe_aborted") for n in names),
    }


def flow_saturation_time(rows: np.ndarray, period_t: np.ndarray, period_phase: np.ndarray,
                         supply_m3_s: float) -> dict:
    """Criteria 13.3 (③) reference time t_a of a base run: the first chunk after the first
    lift-off with Q_dem > Q_sup; without one the LEVEL chunk with the largest Q_dem / Q_sup."""
    phases = chunk_phases(rows, period_t, period_phase)
    lift_index = _first_lift_index(rows, phases)
    t = rows[:, COLUMN["t"]]
    ratio = rows[:, COLUMN["Q_dem"]] / supply_m3_s
    out = {"t_lift_s": None if lift_index is None else _rounded(t[lift_index], 3),
           "supply_L_min": _rounded(supply_m3_s * L_MIN_PER_M3_S, 4)}
    if lift_index is not None:
        over = np.flatnonzero(ratio[lift_index:] > 1.0)
        if over.size:
            index = lift_index + int(over[0])
            return {**out, "t_a_s": float(t[index]), "basis": "first_overlap_after_liftoff",
                    "ratio_at_t_a": _rounded(ratio[index], 6)}
    level = np.flatnonzero(phases == "level")
    if not level.size:
        return {**out, "t_a_s": None, "basis": "no_level_chunk", "ratio_at_t_a": None}
    index = int(level[np.argmax(ratio[level])])
    return {**out, "t_a_s": float(t[index]), "basis": "largest_level_ratio",
            "ratio_at_t_a": _rounded(ratio[index], 6)}


def overlap_in_window(rows: np.ndarray, supply_m3_s: float, t_start_s: float,
                      t_end_s: float) -> dict:
    """Criteria 13.3 ``overlap_found``: chunks of [t_start, t_end] with Q_dem > Q_sup [ms] and
    the largest shortfall Q_dem - Q_sup [L/min]."""
    t = rows[:, COLUMN["t"]]
    window = (t >= t_start_s) & (t <= t_end_s)
    shortfall = rows[window, COLUMN["Q_dem"]] - supply_m3_s
    over = shortfall > 0.0
    return {"window_s": [_rounded(t_start_s, 3), _rounded(t_end_s, 3)],
            "over_ms": int(over.sum()),  # one chunk = CHUNK_S = 1 ms
            "max_shortfall_L_min": _rounded(shortfall[over].max() * L_MIN_PER_M3_S, 4)
            if over.any() else 0.0,
            "found": bool(over.any())}


TRAILING_MEAN_S = 0.5
"""Criteria 3.1 (⑦): trailing (not centred) moving mean of the 1 ms true F_cyl."""


def _longest_true_run(flags: np.ndarray) -> int:
    runs = contiguous_runs(flags)
    return max((last - first + 1 for first, last in runs), default=0)


def after_window_force_values(t_rel_s: np.ndarray, force_N: np.ndarray, contact_N: np.ndarray,
                              window_end_s: float, f_min_N: float) -> dict:
    """Criteria 3.1 (⑦) values after the event window (1 ms rows, times relative to the event).

    The trailing 0.5 s mean uses samples after the window only (its first value is 0.5 s after
    the window end). ``FLAG_E3_1ms`` = the 1 ms minimum after the window is below F_min (with
    the leg, the summed and the longest time below F_min over all legs [ms]). Lift = pad contact
    force <= 0 after the window [ms, summed over the legs]. No verdict here.
    """
    after = t_rel_s > window_end_s
    out = {"window_end_s": _rounded(window_end_s, 3), "samples_after": int(after.sum())}
    if not after.any():
        return out
    force = force_N[after]
    index, leg = np.unravel_index(int(np.argmin(force)), force.shape)
    below = force < f_min_N
    window = round(TRAILING_MEAN_S / CHUNK_S)
    trailing = None
    if len(force) >= window:
        kernel = np.ones(window) / window
        trailing = np.column_stack([np.convolve(force[:, k], kernel, "valid")
                                    for k in range(force.shape[1])])
    out.update({
        "min_1ms_kN": _rounded(force[index, leg] * KN_PER_N, 4), "min_1ms_leg": LEGS[int(leg)],
        "min_1ms_t_rel_s": _rounded(t_rel_s[after][index], 3),
        "below_f_min_ms_sum": int(below.sum()),
        "below_f_min_ms_longest": max(_longest_true_run(below[:, k]) for k in range(4)),
        "min_trailing_0p5s_kN": None if trailing is None
        else _rounded(trailing.min() * KN_PER_N, 4),
        "lift_ms_after_window": int((contact_N[after] <= 0.0).sum()),
        "FLAG_E3_1ms": bool(force[index, leg] < f_min_N)})
    return out


HOLD_TIME_TOL_S = 1e-9


def hold_period_values(row_t_s: np.ndarray, period_t_s: np.ndarray,
                       period_values: np.ndarray) -> np.ndarray:
    """Zero-order hold of 10 Hz controller values on the 1 ms rows.

    A value computed from the reading taken at ``t_k`` (the end of a control period) holds for
    the rows in ``(t_k, t_{k+1}]``; rows at or before the first reading get NaN.
    """
    values = np.asarray(period_values, float).reshape(len(period_t_s), -1)
    index = np.searchsorted(np.asarray(period_t_s, float),
                            np.asarray(row_t_s, float) - HOLD_TIME_TOL_S, side="right") - 1
    held = np.full((len(row_t_s), values.shape[1]), np.nan)
    has_value = index >= 0
    held[has_value] = values[index[has_value]]
    return held


def lower_bound_miss_values(t_rel_s: np.ndarray, force_N: np.ndarray, lower_N: np.ndarray,
                            window_end_s: float, f_min_N: float) -> dict:
    """Criteria 13.4 (⑥) misses after the event window (1 ms rows, times relative to the event).

    A miss sample is a leg whose true F_cyl is below F_min while the controller's lower load
    estimate (held from its last 10 Hz reading, ``lower_N``) is above F_min. A miss interval is
    a run of such samples on one leg. Rows without an estimate do not count. No verdict here.
    """
    after = t_rel_s > window_end_s
    out = {"window_end_s": _rounded(window_end_s, 3), "samples_after": int(after.sum())}
    if not after.any():
        return out
    force, lower = force_N[after], lower_N[after]
    has_estimate = np.isfinite(lower)
    miss = (force < f_min_N) & has_estimate & (lower > f_min_N)
    intervals_per_leg = [len(contiguous_runs(miss[:, k])) for k in range(force.shape[1])]
    estimate_at_true_minimum = None
    index, leg = np.unravel_index(int(np.argmin(force)), force.shape)
    if has_estimate[index, leg]:
        estimate_at_true_minimum = _rounded(lower[index, leg] * KN_PER_N, 4)
    out.update({
        "miss_intervals": int(sum(intervals_per_leg)),
        "miss_intervals_by_leg": dict(zip(LEGS, intervals_per_leg, strict=True)),
        "miss_ms_sum": int(miss.sum()),
        "miss_ms_longest": max(_longest_true_run(miss[:, k]) for k in range(force.shape[1])),
        "lower_at_true_min_kN": estimate_at_true_minimum,
        "min_lower_kN": None if not has_estimate.any()
        else _rounded(np.min(lower[has_estimate]) * KN_PER_N, 4)})
    return out


REF_10HZ_LIFT_CONTACT_N = 500.0
"""Criteria 13.4 reference value (control-expert 2026-11-06 C): a 10 Hz interval whose 1 ms pad
contact minimum is at most this counts as lift (L)."""
REF_10HZ_DETECT_DELAY_S = 0.3
"""An episode first flagged later than this after its start is ``late``."""
REF_10HZ_BASIS = ("spec 203.1-203.3 decision level (Chrono N_*_pressure J_P style), 10 Hz "
                  "estimate < F_min; reference only; no spec 232 +0.5 kN (L2b-NSC only)")
REF_10HZ_UNIT_STATUS = "below_criteria_reference_only"


def _interval_minima(t_rel_s: np.ndarray, values: np.ndarray, starts_s: np.ndarray,
                     ends_s: np.ndarray) -> np.ndarray:
    """Per 10 Hz interval (start, end] the 1 ms minimum per leg (NaN without rows)."""
    first = np.searchsorted(t_rel_s, starts_s + HOLD_TIME_TOL_S, side="left")
    last = np.searchsorted(t_rel_s, ends_s + HOLD_TIME_TOL_S, side="right")
    minima = np.full((len(starts_s), values.shape[1]), np.nan)
    for k, (lo, hi) in enumerate(zip(first, last, strict=True)):
        if hi > lo:
            minima[k] = values[lo:hi].min(axis=0)
    return minima


def ref_10hz_episode_values(t_rel_s: np.ndarray, contact_N: np.ndarray, force_N: np.ndarray,
                            period_t_rel_s: np.ndarray, lower_N: np.ndarray,
                            window_end_s: float, f_min_N: float, judge: str) -> dict:
    """Criteria 13.4 reference value next to ``lower_bound_miss`` (Chrono J_P style, 10 Hz).

    Samples k whose interval (t_{k-1}, t_k] lies after the event window. Per leg: L = the 1 ms
    pad contact minimum in the interval <= 0.5 kN, U = not L and the 1 ms F_cyl minimum below
    F_min. An episode is a run of consecutive U or L samples of one leg; it is ``missed`` when
    the lower estimate of no sample in [t_on, t_off] is below F_min and ``late`` when the first
    such sample comes more than 0.3 s after t_on. Reference only, not judged.
    """
    out = {"basis": REF_10HZ_BASIS, "judge": judge, "estimate": "lower_estimate_N",
           "scope": "10 Hz samples whose (t_k-1, t_k] lies after the event window end",
           "f_min_N": f_min_N, "lift_contact_N": REF_10HZ_LIFT_CONTACT_N,
           "detect_delay_s": REF_10HZ_DETECT_DELAY_S, "unit_status": REF_10HZ_UNIT_STATUS}
    if judge == "COMBINED":
        out["partial_jc"] = True
    starts, ends = period_t_rel_s[:-1], period_t_rel_s[1:]
    in_scope = starts >= window_end_s - HOLD_TIME_TOL_S
    starts, ends, lower = starts[in_scope], ends[in_scope], lower_N[1:][in_scope]
    contact_min = _interval_minima(t_rel_s, contact_N, starts, ends)
    force_min = _interval_minima(t_rel_s, force_N, starts, ends)
    has_rows = np.isfinite(force_min).all(axis=1)
    ends, lower = ends[has_rows], lower[has_rows]
    lifted = contact_min[has_rows] <= REF_10HZ_LIFT_CONTACT_N
    under = ~lifted & (force_min[has_rows] < f_min_N)
    flagged = np.nan_to_num(lower, nan=np.inf) < f_min_N
    by_leg = {leg: 0 for leg in LEGS}
    missed_by_leg = {leg: 0 for leg in LEGS}
    n_lift = n_late = 0
    delays = []
    for k, leg in enumerate(LEGS):
        for first, last in contiguous_runs(lifted[:, k] | under[:, k]):
            by_leg[leg] += 1
            n_lift += bool(lifted[first:last + 1, k].any())
            flag_index = np.flatnonzero(flagged[first:last + 1, k])
            if flag_index.size == 0:
                missed_by_leg[leg] += 1
                continue
            delay_s = float(ends[first + flag_index[0]] - ends[first])
            delays.append(delay_s)
            n_late += delay_s > REF_10HZ_DETECT_DELAY_S + HOLD_TIME_TOL_S
    out.update(samples_after=int(len(ends)), episodes=sum(by_leg.values()),
               episodes_by_leg=by_leg, episodes_lift=n_lift,
               missed=sum(missed_by_leg.values()), missed_by_leg=missed_by_leg, late=n_late,
               first_flag_delay_s_max=_rounded(max(delays), 3) if delays else None)
    return out


STOP_BEFORE_WINDOW_S = 1.0
STOP_SAMPLE_HALF_WINDOW_S = 0.1
CRAWLER_LOADED_WEIGHT_FRACTION = 0.01


def stop_crawler_values(rows: np.ndarray, stop_t_s: float, weight_N: float) -> dict:
    """Criteria 6 (S8 F-5) values of a soil-guard stop from the 1 ms true crawler force.

    Clause: crawler load after the stop <= load at the stop + 0.01 W. The stop value is one
    chunk (the one at or just before the stop), so the 1 s maximum before the stop and the
    chunks within +-0.1 s of the stop are recorded with it. Margins = allowed - maximum after
    the stop [kN] (negative: the clause fails on that basis). A run that ends at the stop (the
    reduced harness stops at the FAULT) has no after-stop chunk: the after-stop values and the
    margins are None and ``after_stop_chunks`` is 0.
    """
    t = rows[:, COLUMN["t"]]
    crawler = rows[:, COLUMN["crawler"]]
    threshold_N = CRAWLER_LOADED_WEIGHT_FRACTION * weight_N
    at_or_before = np.flatnonzero(t <= stop_t_s + 1e-9)
    if not at_or_before.size:
        return {"stop_t_s": _rounded(stop_t_s, 3), "note": "no chunk at or before the stop"}
    at_stop_N = float(crawler[at_or_before[-1]])
    before = (t >= stop_t_s - STOP_BEFORE_WINDOW_S) & (t <= stop_t_s + 1e-9)
    near = np.abs(t - stop_t_s) <= STOP_SAMPLE_HALF_WINDOW_S + 1e-9
    after = t > stop_t_s + 1e-9
    max_before_N = float(crawler[before].max())
    max_after_N = float(crawler[after].max()) if after.any() else None

    def margin_kN(reference_N: float) -> float | None:
        if max_after_N is None:
            return None
        return _rounded((reference_N + threshold_N - max_after_N) * KN_PER_N, 3)

    return {"stop_t_s": _rounded(stop_t_s, 3), "threshold_kN": _rounded(threshold_N * KN_PER_N, 3),
            "at_stop_kN": _rounded(at_stop_N * KN_PER_N, 3),
            "max_before_1s_kN": _rounded(max_before_N * KN_PER_N, 3),
            "near_stop_pm0p1s_kN": [_rounded(crawler[near].min() * KN_PER_N, 3),
                                    _rounded(crawler[near].max() * KN_PER_N, 3)],
            "after_stop_chunks": int(after.sum()),
            "max_after_stop_kN": None if max_after_N is None
            else _rounded(max_after_N * KN_PER_N, 3),
            "end_kN": _rounded(crawler[-1] * KN_PER_N, 3),
            "margin_at_stop_kN": margin_kN(at_stop_N),
            "margin_vs_max_before_1s_kN": margin_kN(max_before_N)}


# ------------------------------------------------------------------- U-9 targeted runs (U9)
U9_LEG_COUNTS = (1, 2, 3, 4)
U9_MIN_RUN_S = 0.1
"""``ge3_runs``: LEVEL k >= 3 runs of at least this duration."""
U9_MAX_RUNS = 50
PHASE_LEVEL = "level"
PRE_LEVEL_PHASES = ("idle", "check", PHASE_TOUCH)
PERIOD_TIME_TOL_S = 1e-9


def moving_limited_masks(rows: np.ndarray) -> np.ndarray:
    """Per chunk: bit mask of the legs the flow limit cut that were moving (|u| > 1e-6 m/s)."""
    limited = rows[:, COLUMN["limited_mask"]].astype(int)
    moving = np.abs(rows[:, U]) > MOVING_SPEED_EPS_M_S
    moving_bits = (moving.astype(int) << np.arange(len(LEGS))).sum(axis=1)
    return limited & moving_bits


def _bit_counts(masks: np.ndarray) -> np.ndarray:
    return ((masks[:, None] >> np.arange(len(LEGS))) & 1).sum(axis=1)


def _time_by_count(counts: np.ndarray, selected: np.ndarray) -> dict:
    return {str(k): _rounded((selected & (counts == k)).sum() * CHUNK_S, 3)
            for k in U9_LEG_COUNTS}


def _post_touch_flags(phases: np.ndarray) -> np.ndarray:
    """True from the first chunk after the first TOUCH end (the ``t_touch_end_s`` rule) on."""
    after = np.zeros(len(phases), bool)
    outside = np.flatnonzero(~np.isin(phases, PRE_LEVEL_PHASES))
    if outside.size:
        after[outside[0]:] = True
    return after


def _attitude_rate_deg_s(rows: np.ndarray, attitude_deg: np.ndarray) -> np.ndarray:
    """True roll / pitch rate on the 1 ms rows (``np.gradient``: central differences inside,
    one-sided at the ends; zero for fewer than two rows)."""
    if len(rows) < 2:
        return np.zeros_like(attitude_deg)
    return np.gradient(attitude_deg, rows[:, COLUMN["t"]], axis=0)


def _filtered_at(period_t: np.ndarray, filtered_deg: np.ndarray, t_s: float,
                 is_before: bool) -> dict | None:
    """10 Hz filtered attitude of the nearest period at or before (or at or after) ``t_s``."""
    if is_before:
        index = int(np.searchsorted(period_t, t_s + PERIOD_TIME_TOL_S, side="right")) - 1
    else:
        index = int(np.searchsorted(period_t, t_s - PERIOD_TIME_TOL_S, side="left"))
    if index < 0 or index >= len(period_t):
        return None
    return {"t_s": _rounded(period_t[index], 3), **_leg_axes(filtered_deg[index])}


def _ge3_run_record(rows: np.ndarray, first: int, last: int, masks: np.ndarray,
                    attitude_deg: np.ndarray, rate_deg_s: np.ndarray, period: dict) -> dict:
    t = rows[:, COLUMN["t"]]
    start_deg = attitude_deg[first]
    delta_deg = np.abs(attitude_deg[first: last + 1] - start_deg).max(axis=0)
    rate_max = np.abs(rate_deg_s[first: last + 1]).max(axis=0)
    return {"t_start_s": _rounded(t[first], 3), "dur_s": _rounded((last - first + 1) * CHUNK_S, 3),
            "set_at_middle": mask_legs(masks[(first + last) // 2]),
            "attitude_start_deg": _leg_axes(start_deg),
            "max_abs_delta_deg": _leg_axes(delta_deg),
            "filtered_start_deg": _filtered_at(period["t"], period["filtered_deg"], t[first],
                                               is_before=True),
            "filtered_end_deg": _filtered_at(period["t"], period["filtered_deg"], t[last],
                                             is_before=False),
            "max_abs_rate_deg_s": _leg_axes(rate_max)}


def u9_values(rows: np.ndarray, phases: np.ndarray, period: dict, *,
              is_flow_on: bool = True) -> dict:
    """U-9 targeted-run values (``u9_targeted_rules_rev1.md`` 3.3); no verdict here.

    k = number of legs the flow limit cut while they moved (:func:`moving_limited_masks`).

    Args:
        rows: The 1 ms chunk record of ``harness_flow``.
        phases: Phase of each chunk (:func:`chunk_phases`).
        period: Controller log arrays with ``t`` and ``filtered_deg`` (roll, pitch).
        is_flow_on: False (a run without the flow limit) gives an empty dict.

    Returns:
        ``level_count_s`` and ``post_touch_count_s`` (time per k = 1 .. 4), ``longest_ge3_s``,
        ``longest_eq4_s`` (LEVEL), ``ge3_runs`` (LEVEL k >= 3 runs of at least 0.1 s, the
        first 50 in time; ``ge3_runs_count`` counts them all) and
        ``level_sat_rate_max_deg_s`` (largest true attitude rate on LEVEL chunks with k >= 1,
        None without such a chunk).
    """
    if not is_flow_on:
        return {}
    masks = moving_limited_masks(rows)
    counts = _bit_counts(masks)
    is_level = phases == PHASE_LEVEL
    attitude_deg = _attitude_deg(rows)
    rate_deg_s = _attitude_rate_deg_s(rows, attitude_deg)
    min_chunks = round(U9_MIN_RUN_S / CHUNK_S)
    long_runs = [(first, last) for first, last in contiguous_runs(is_level & (counts >= 3))
                 if last - first + 1 >= min_chunks]
    saturated_level = is_level & (counts >= 1)
    level_sat_rate = None
    if saturated_level.any():
        level_sat_rate = _leg_axes(np.abs(rate_deg_s[saturated_level]).max(axis=0))
    return {
        "level_count_s": _time_by_count(counts, is_level),
        "post_touch_count_s": _time_by_count(counts, _post_touch_flags(phases)),
        "longest_ge3_s": _rounded(_longest_true_run(is_level & (counts >= 3)) * CHUNK_S, 3),
        "longest_eq4_s": _rounded(_longest_true_run(is_level & (counts == 4)) * CHUNK_S, 3),
        "ge3_runs_count": len(long_runs),
        "ge3_runs": [_ge3_run_record(rows, first, last, masks, attitude_deg, rate_deg_s, period)
                     for first, last in long_runs[:U9_MAX_RUNS]],
        "level_sat_rate_max_deg_s": level_sat_rate,
    }


def run_values(rows: np.ndarray, period: dict, events: list[tuple[float, str]], limiter,
               twist_vector: np.ndarray, head_area_m2: np.ndarray, integral_limit: float) -> dict:
    """All values of one run. ``period``: arrays t, phase, integral, filtered_deg, guard."""
    period_t, period_phase = period["t"], period["phase"]
    phases = chunk_phases(rows, period_t, period_phase)
    lift_index = _first_lift_index(rows, phases)
    times = period_phase_times(period_t, period_phase)
    forces = force_values(rows, lift_index)
    values = {
        "times": times, "forces": forces,
        "attitude": attitude_values(rows, phases, lift_index, period["filtered_deg"], period_t,
                                    times["t_first_ready_s"]),
        "probe_attitude_change_deg": probe_attitude_change_deg(rows, phases),
        "pressure": pressure_values(rows, head_area_m2),
        "twist": twist_values(rows, phases, lift_index, twist_vector),
        "events": event_counts(events, forces["t_lift_s"]),
        "guard_active_s": _rounded(period["guard"].sum() * 0.1, 2),
        "oil_force_max_kN": _leg_list(rows[:, OIL_FORCE].max(axis=0) * KN_PER_N, 3),
    }
    if not limiter.setting.is_enabled:
        return values
    params = limiter.params
    supply = limiter.supply_m3_s
    values.update({
        "supply_L_min": _rounded(supply * L_MIN_PER_M3_S, 4),
        "V2_a": flow_conservation(rows, supply, limiter.counters()),
        "E1": exposure_by_phase(rows, phases, supply),
        "E2": speed_ratio_table(rows, phases, params.v_max),
        "E3": tracking_error(rows),
        "E4": residual_groups(rows),
        "E5": integral_values(rows, period_t, period["integral"], period["filtered_deg"],
                              integral_limit),
        "T4_inputs": saturation_inputs(rows, {
            "X_comp": params.X_comp, "dp_comp_Pa": params.dp_comp, "dp_unload_Pa": params.dp_unl,
            "width_Pa": params.width, "law": params.law, "A_h_m2": params.A_h.tolist(),
            "A_r_m2": params.A_r.tolist(), "v_max_m_s": params.v_max, "Q_sup_m3_s": supply}),
    })
    return values
