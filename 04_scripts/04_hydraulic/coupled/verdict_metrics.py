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


def pressure_values(rows: np.ndarray, head_area_m2: np.ndarray) -> dict:
    """Item 4: largest moving pressure F_cyl / A_p and extending chunks at the relief pressure."""
    pressure_bar = rows[:, TRUE_FORCE] / head_area_m2 / PA_PER_BAR
    moving = np.abs(rows[:, U]) > MOVING_SPEED_EPS_M_S
    extending = rows[:, U] > MOVING_SPEED_EPS_M_S
    return {"max_moving_bar": _rounded(pressure_bar[moving].max(), 3) if moving.any() else None,
            "saturation_leg_chunks": int((extending & (pressure_bar >= RELIEF_BAR)).sum())}


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
