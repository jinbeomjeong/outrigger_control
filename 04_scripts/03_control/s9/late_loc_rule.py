"""Spec 419.8 / 419.8.1 (decision 13, 2026-10-29): a LOC made late by the LWa window restart,
for the reduced harness judges (``r72_g6_screen.py`` G6-2, ``s9_soil_slope.py`` P3-2).

The five conditions are evaluated by cad's ``run_S9.p32_late_loc_block`` itself (imported, not
copied), so the harness and the Chrono judge give the same result on the same inputs:

1. a re-approach interval (``leg_reapproach_start:<leg>`` to that leg's next
   ``leg_reapproach_contact`` / ``WARN_LEG_REAPPROACH_NO_CONTACT``) overlaps [t_off, t_LOC] and has
   an LWa window restart (``INFO_LOC_WINDOW_RESTART`` or the wrapper ``FIX_LW_RESTART``) during it;
2. ``t_LOC - max(t_off, t_re_end) <= T_lim``, ``t_re_end`` = latest end of those intervals (an
   open one makes it false);
3. true crawler force < 0.01 W over the 1 ms samples of (t_LOC - 0.1 s, t_LOC] and at t_LOC;
4. true F_cyl minimum after the lift-off >= F_min and no FAULT in the whole run (``FAULT*``
   event or a fault / fault_reground phase);
5. the LOC comes before the first DONE.

The harness inputs: ``t_off`` = the lift-off time its delay row (``loc_delay_s``) uses, the 1 ms
crawler force of the plant chunks in place of the SCM crawler normal. Times in s, forces in N.

Also the harness P3-1 / G6-1 crawler row of spec 420.2b (U-S9-G6d (가), ``run_S9.py``
``recontact_events``) with the spec 423.3 threshold-chatter class (decision Q-G, constants
``CHATTER_*``): :func:`crawler_recontact_record`, :func:`reclassify_recontacts`,
:func:`crawler_gate`.

Spec 424.8.1 (user decision 2026-10-29, question 1): with a LOC revocation (L1), the judged LOC
is the last confirmed one, t_LOC^fin (:func:`loc_timeline`); a P3-2 / G6-2 time-clause violation
is the FLAG ``P3-2_late_loc_revoked`` / ``G6-2_late_loc_revoked`` when six conditions hold
(:func:`late_loc_revoked`, :func:`is_late_loc_revoked`; own code, no ``run_S9`` import, so
``run_S9.py`` can import it):

1. a LOC revocation in [t_off, t_LOC^fin];
2. ``t_LOC^fin - max(t_off, t_revoke_last) <= T_lim``; when the spec 419.8 condition 1 also holds
   the later event counts, ``max(t_off, t_revoke_last, t_re_end)`` (an open re-approach interval
   or one ending after t_LOC^fin makes it false);
3. true crawler force < 0.01 W over the t_LOC^fin control period (419.8.1 period);
4. true F_cyl minimum after the lift-off >= F_min and no FAULT;
5. t_LOC^fin before the first DONE;
6. (spec 424.9 decision 1) total delay ``t_LOC^fin - t_off <= (1 + n_revoke) T_lim``: one more
   S-1 window (at most T_lim) per revocation; n_revoke = the revocations in [t_off, t_LOC^fin]
   (condition 1's set) unless given. Re-approach window restarts add nothing (419.8 condition 2
   judges that delay).
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

import numpy as np

RUN_S9_DIR = Path(__file__).resolve().parents[2] / "02_chrono"
LOC_DELAY_MAX_S = 2.9
"""``T_lim`` of P3-2 / G6-2."""
CONTROL_PERIOD_S = 0.1
TIME_TOLERANCE_S = 1e-9
P32_FLAG = "P3-2_late_loc_reapproach"
G62_FLAG = "G6-2_late_loc_reapproach"

# Spec 423.3 (user decision Q-G, 2026-10-29): threshold chatter just after the LOC. Shared with
# cad's run_S9.py (one place for the three constants).
CHATTER_AFTER_LOC_S = 1.0
"""A chatter event starts after t_LOC and at most this long after it."""
CHATTER_MAX_DURATION_S = 0.1
CHATTER_MAX_OVER_THRESHOLD = 1.2
"""Peak crawler normal at most this times the departure threshold (0.01 W)."""
CLASS_TRANSIENT = "transient_flag"
CLASS_STRICT = "strict_fail"
CLASS_CHATTER = "threshold_chatter"
P31_TRANSIENT_FLAG = "P3-1_transient_recontact"
P31_CHATTER_FLAG = "P3-1_threshold_chatter"
DEPARTURE_FRACTION_OF_W = 0.01
"""P3-1 / P3a-2 departure threshold as a fraction of W (run_S9 ``P3A_OFF_FRACTION``)."""

# Spec 424.8.1 (user decision 2026-10-29): LOC revoked and confirmed again
P32_REVOKED_FLAG = "P3-2_late_loc_revoked"
G62_REVOKED_FLAG = "G6-2_late_loc_revoked"
LOC_EVENT = "crawler_liftoff_confirmed"
"""C2 LOC event (``SOIL_EVENT_LIFTOFF_CONFIRMED``)."""
LOC_REVOKE_EVENTS = ("FIX_LOC_REVOKE", "INFO_LOC_REVOKED")
"""LOC revocation events (``<name>[:<rise kN>]``): the s9_slope_fix_candidates L1 wrapper event
and the project P-S8-33 event (``c2.LOC_REVOKE_EVENT``, spec 424.10)."""


def is_threshold_chatter(event: dict, t_loc_s: float | None, threshold_N: float,
                         t_ready_s: float | None = None) -> bool:
    """Spec 423.3: a recontact that starts in (t_LOC, t_LOC + 1.0 s], lasts at most 0.1 s, peaks
    at most 1.2 x the departure threshold and (READY recontacts stay strict) starts before READY.
    Open events (no end) are not chatter."""
    if t_loc_s is None or event.get("t_end_s") is None:
        return False
    t_start_s = event["t_start_s"]
    return bool(t_loc_s + TIME_TOLERANCE_S < t_start_s <= t_loc_s + CHATTER_AFTER_LOC_S
                + TIME_TOLERANCE_S
                and event["duration_s"] <= CHATTER_MAX_DURATION_S + TIME_TOLERANCE_S
                and event["max_normal_N"] <= CHATTER_MAX_OVER_THRESHOLD * threshold_N
                and (t_ready_s is None or t_start_s < t_ready_s))


def reclassify_recontacts(events: dict, t_loc_s: float | None, threshold_N: float,
                          t_ready_s: float | None = None) -> dict:
    """``recontact_events`` (run_S9 form) with the 423.3 class: each ``strict_fail`` event that is
    threshold chatter becomes ``threshold_chatter``; ``pass`` = no ``strict_fail`` left; flags
    ``P3-1_transient_recontact`` / ``P3-1_threshold_chatter`` per class present. Idempotent."""
    reclassified = []
    for event in events["events"]:
        is_chatter = (event["class"] == CLASS_STRICT
                      and is_threshold_chatter(event, t_loc_s, threshold_N, t_ready_s))
        reclassified.append({**event, "class": CLASS_CHATTER} if is_chatter else dict(event))
    classes = [event["class"] for event in reclassified]
    flags = [flag for flag, name in ((P31_TRANSIENT_FLAG, CLASS_TRANSIENT),
                                     (P31_CHATTER_FLAG, CLASS_CHATTER)) if name in classes]
    return {**events, "events": reclassified, "pass": CLASS_STRICT not in classes,
            "flags": flags, "chatter_rule": "spec 423.3 (Q-G): (t_LOC, t_LOC + "
            f"{CHATTER_AFTER_LOC_S:g} s], <= {CHATTER_MAX_DURATION_S:g} s, <= "
            f"{CHATTER_MAX_OVER_THRESHOLD:g} x threshold, before READY"}


def _run_s9():
    if str(RUN_S9_DIR) not in sys.path:
        sys.path.insert(0, str(RUN_S9_DIR))
    import run_S9

    return run_S9


def install_crawler_recorder(cl, series_of_run) -> None:
    """Wrap ``cl._lagged_step`` once (record only): every chunk appends (plant t, crawler force)
    to the list ``series_of_run()`` returns (``None``: not recording).

    The wrapper keeps the attributes of the function it wraps, so the other one-time hooks
    (``s9_slope_fix_candidates`` ``is_truth_hook``) still see themselves installed."""
    current = cl._lagged_step
    if getattr(current, "is_crawler_recorder", False):
        return

    def lagged_step_with_crawler_record(plant, command, valve, steps):
        accumulated = current(plant, command, valve, steps)
        series = series_of_run()
        if series is not None:
            series.append((float(plant.t), float(accumulated[15])))
        return accumulated

    # one-time hook markers only (``current`` may be a probe object with its own state)
    markers = {name: value for name, value in getattr(current, "__dict__", {}).items()
               if name.startswith("is_")}
    lagged_step_with_crawler_record.__dict__.update(markers)
    lagged_step_with_crawler_record.is_crawler_recorder = True
    cl._lagged_step = lagged_step_with_crawler_record


def crawler_recontact_record(series, weight_N: float | None, t_loc_s: float | None,
                             t_ready_s: float | None = None) -> dict | None:
    """U-S9-G6d input from the 1 ms crawler series: the P3-1 / P3a-2 departure and every
    recontact after its confirmation with start, end, duration, maximum and class
    (``run_S9.py`` ``crawler_departure`` / ``recontact_events``, the Chrono P3b definition; the
    harness crawler force in place of the SCM crawler normal), then the spec 423.3 threshold
    chatter class (:func:`reclassify_recontacts`). ``None`` without a series or a weight."""
    if not series or not weight_N:
        return None
    run_s9 = _run_s9()
    times_s = np.array([t for t, _ in series], dtype=float)
    crawler_N = np.array([force for _, force in series], dtype=float)
    departure = run_s9.crawler_departure(times_s, crawler_N, weight_N)
    recontact = reclassify_recontacts(
        run_s9.recontact_events(times_s, crawler_N, weight_N, departure, t_loc_s), t_loc_s,
        DEPARTURE_FRACTION_OF_W * weight_N, t_ready_s)
    return {"departure": departure, "recontact_events": recontact,
            "series_step_s": float(np.median(np.diff(times_s))) if len(times_s) > 1 else None}


def crawler_gate(is_crawler_zero_after_ready: bool, recontact: dict | None,
                 legacy_recontact_count: int | None) -> tuple[bool, list[str]]:
    """G6-1 / P3-1 of the harness (spec 420.2b, U-S9-G6d (가) + 423.3 Q-G): crawler load 0 after
    READY and no ``strict_fail`` recontact; ``transient_flag`` / ``threshold_chatter`` recontacts
    pass with the FLAGs ``P3-1_transient_recontact`` / ``P3-1_threshold_chatter`` (``recontact``
    is a :func:`crawler_recontact_record`, already reclassified). Without the 1 ms record
    (``recontact`` None) the old rule (no recontact after the first lift-off) is kept. Returns
    (passes, flags)."""
    if recontact is None:
        return bool(is_crawler_zero_after_ready and legacy_recontact_count == 0), []
    events = recontact["recontact_events"]
    passes = bool(is_crawler_zero_after_ready and events["pass"])
    return passes, (list(events["flags"]) if passes else [])


def is_delay_row_pass(t_off_s: float | None, t_loc_s: float | None, t_done_s: float | None,
                      t_lim_s: float = LOC_DELAY_MAX_S) -> bool:
    """The harness delay row as before: LOC before the first DONE and t_LOC - t_off <= T_lim."""
    return bool(t_loc_s is not None and (t_done_s is None or t_loc_s <= t_done_s + TIME_TOLERANCE_S)
                and t_off_s is not None and t_loc_s - t_off_s <= t_lim_s + TIME_TOLERANCE_S)


def late_loc_reapproach(
    events: Sequence[tuple[float, str]],
    phases: Sequence[tuple[float, str]],
    crawler_series: Sequence[tuple[float, float]],
    weight_N: float | None,
    *,
    t_off_s: float | None,
    t_loc_s: float | None,
    t_done_s: float | None,
    min_force_after_off_kN: float | None,
    f_min_kN: float,
    t_revoke_last_s: float | None = None,
    t_lim_s: float = LOC_DELAY_MAX_S,
) -> dict:
    """``run_S9.p32_late_loc_block`` on harness inputs; ``is_flag`` = its ``flag``.

    ``t_lim_s`` is T_lim of the delay row and of the FLAG condition 2 (default 2.9 s: the former
    result bit for bit).

    With a LOC revocation (spec 424.8.1) pass ``t_loc_s`` = t_LOC^fin and ``t_revoke_last_s``:
    the block then takes its condition 2 from the later of the re-approach end and the
    revocation. ``None`` (no revocation) calls the block exactly as before.

    Args:
        events: (t_s, name) controller events of the run.
        phases: (t_s, phase) entries of the run (the harness phase path and the final phase).
        crawler_series: (t_s, true crawler force N) of every 1 ms plant chunk.
        weight_N: Machine weight m g (``None``: not judged, no flag).
        t_off_s: Lift-off time of the harness delay row.
        t_loc_s: LOC time.
        t_done_s: First DONE time.
        min_force_after_off_kN: True F_cyl minimum after the lift-off.
        f_min_kN: F_min.
    """
    is_within = is_delay_row_pass(t_off_s, t_loc_s, t_done_s, t_lim_s)
    if not weight_N:
        return {"is_flag": False, "verdict": "pass" if is_within else "fail",
                "note": "no plant weight: spec 419.8 rule not judged"}
    p32 = {"t_loc_s": t_loc_s, "t_departure_s": t_off_s, "limit_s": t_lim_s,
           "loc_minus_departure_s": None if t_loc_s is None or t_off_s is None
           else t_loc_s - t_off_s,
           "within": is_within,
           "loc_before_first_done": bool(t_loc_s is not None and (
               t_done_s is None or t_loc_s <= t_done_s + TIME_TOLERANCE_S))}
    p33 = {"within": bool(min_force_after_off_kN is not None
                          and min_force_after_off_kN >= f_min_kN)}
    times_s = np.array([t for t, _ in crawler_series], dtype=float)
    crawler_N = np.array([force for _, force in crawler_series], dtype=float)
    revoke_option = {} if t_revoke_last_s is None else {"t_revoke_last_s": t_revoke_last_s}
    block = _run_s9().p32_late_loc_block(
        times_s, crawler_N, float(weight_N), list(events), list(phases), p32, p33,
        period_s=CONTROL_PERIOD_S, **revoke_option)
    return {**block, "is_flag": bool(block["flag"])}


# ------------------------------------------------------------------ spec 424.8.1 final LOC
def _is_named(name: str, kinds: Sequence[str]) -> bool:
    return any(name == kind or name.startswith(f"{kind}:") for kind in kinds)


def loc_timeline(events: Sequence[tuple[float, str]]) -> dict:
    """Spec 424.8.1: LOC events and revocations of a run, and the judged LOC t_LOC^fin.

    A revocation cancels the latest LOC at or before it; t_LOC^fin = the first LOC after the last
    revocation (None when none follows). Without a revocation t_LOC^fin = the first LOC event
    (the former definition). Same rule as ``run_S9.loc_timeline``.

    Returns:
        ``t_loc_first_s``, ``t_loc_final_s``, ``loc_events_s``, ``revoke_times_s``,
        ``revoked_loc_s``, ``t_revoke_last_s`` (absolute times, s).
    """
    loc_times_s = [float(t) for t, name in events if _is_named(name, (LOC_EVENT,))]
    revoke_times_s = sorted(float(t) for t, name in events if _is_named(name, LOC_REVOKE_EVENTS))
    t_first_s = loc_times_s[0] if loc_times_s else None
    timeline = {"t_loc_first_s": t_first_s, "t_loc_final_s": t_first_s,
                "loc_events_s": loc_times_s, "revoke_times_s": revoke_times_s,
                "revoked_loc_s": [], "t_revoke_last_s": None}
    if not revoke_times_s:
        return timeline
    revoked_s: list[float] = []
    for t_revoke_s in revoke_times_s:
        live = [t for t in sorted(loc_times_s)
                if t <= t_revoke_s + TIME_TOLERANCE_S and t not in revoked_s]
        if live:
            revoked_s.append(live[-1])
    t_last_s = revoke_times_s[-1]
    after = [t for t in sorted(loc_times_s) if t > t_last_s + TIME_TOLERANCE_S]
    timeline.update(revoked_loc_s=revoked_s, t_revoke_last_s=t_last_s,
                    t_loc_final_s=after[0] if after else None)
    return timeline


def judged_loc_times(events: Sequence[tuple[float, str]]) -> list[float]:
    """LOC event times that were not revoked (spec 424.8.1; every LOC without a revocation)."""
    timeline = loc_timeline(events)
    return [t for t in timeline["loc_events_s"] if t not in timeline["revoked_loc_s"]]


def loc_period_crawler_max_N(crawler_series: Sequence[tuple[float, float]],
                             t_loc_s: float | None) -> float | None:
    """Spec 419.8.1 condition 3 input: the largest true crawler force over the LOC control period,
    the 1 ms samples in (t_LOC - 0.1 s, t_LOC] and the sample nearest t_LOC. None without data."""
    if t_loc_s is None or not crawler_series:
        return None
    times_s = np.array([t for t, _ in crawler_series], dtype=float)
    crawler_N = np.array([force for _, force in crawler_series], dtype=float)
    in_period = ((times_s > t_loc_s - CONTROL_PERIOD_S + TIME_TOLERANCE_S)
                 & (times_s <= t_loc_s + TIME_TOLERANCE_S))
    at_loc_N = crawler_N[int(np.argmin(np.abs(times_s - t_loc_s)))]
    return float(max(crawler_N[in_period].max() if in_period.any() else -np.inf, at_loc_N))


def _later_event_s(t_off_s: float, t_revoke_last_s: float, reapproach_restart: bool,
                   t_reapproach_end_s: float | None, t_loc_s: float) -> float | None:
    """Condition 2 basis: max(t_off, t_revoke_last[, t_re_end]); None when the re-approach that
    the 419.8 rule names is open or ends after t_LOC^fin (condition 2 false)."""
    later_s = max(t_off_s, t_revoke_last_s)
    if not reapproach_restart:
        return later_s
    if t_reapproach_end_s is None or t_reapproach_end_s > t_loc_s + TIME_TOLERANCE_S:
        return None
    return max(later_s, t_reapproach_end_s)


def _is_total_delay_within(loc_minus_departure_s: float | None, n_revokes: int,
                           t_lim_s: float) -> bool:
    """Spec 424.9 condition 6: t_LOC^fin - t_off <= (1 + n_revoke) T_lim."""
    return bool(loc_minus_departure_s is not None
                and loc_minus_departure_s <= (1 + n_revokes) * t_lim_s + TIME_TOLERANCE_S)


def late_loc_revoked(
    *,
    t_off_s: float | None,
    t_loc_final_s: float | None,
    t_done_s: float | None,
    revoke_times_s: Sequence[float],
    crawler_loc_period_max_N: float | None,
    weight_N: float | None,
    min_force_after_off_kN: float | None,
    f_min_kN: float,
    has_fault: bool,
    reapproach_restart: bool = False,
    t_reapproach_end_s: float | None = None,
    t_lim_s: float = LOC_DELAY_MAX_S,
    n_revokes: int | None = None,
) -> dict:
    """Spec 424.8.1 FLAG record of a P3-2 / G6-2 time-clause violation after a LOC revocation.

    Args:
        t_off_s: Crawler lift-off time of the delay row (P3-2 ``t_departure_s``).
        t_loc_final_s: t_LOC^fin, the last confirmed LOC (:func:`loc_timeline`).
        t_done_s: First DONE time (None: no DONE).
        revoke_times_s: Every LOC revocation time of the run.
        crawler_loc_period_max_N: True crawler force maximum over the t_LOC^fin control period
            (:func:`loc_period_crawler_max_N`).
        weight_N: Machine weight m g of the 0.01 W threshold (None: condition 3 false).
        min_force_after_off_kN: True F_cyl minimum after the lift-off.
        f_min_kN: F_min.
        has_fault: Any FAULT event or fault phase in the run.
        reapproach_restart: Spec 419.8 condition 1 holds at t_LOC^fin (both FLAG rules apply).
        t_reapproach_end_s: Spec 419.8 ``t_re_end`` (latest end of the overlapping re-approach
            intervals; None = open or none).
        t_lim_s: T_lim of the time clause and of condition 2 (the caller's P3-2 / G6-2
            ``limit_s``; default 2.9 s).
        n_revokes: n_revoke of condition 6 (spec 424.9). None: the revocations in
            [t_off, t_LOC^fin] (condition 1's set, ``revokes_off_to_loc_s``).

    Returns:
        ``is_flag``, ``time_clause_violated``, ``conditions`` (``1_revoke`` ..
        ``6_total_delay``), ``t_revoke_last_s``, ``loc_minus_departure_s``,
        ``loc_minus_later_event_s``, ``condition_2_basis``, ``n_revokes``,
        ``total_delay_limit_s``.
    """
    has_times = t_off_s is not None and t_loc_final_s is not None
    revokes_in_window = [t for t in revoke_times_s if has_times
                         and t_off_s - TIME_TOLERANCE_S <= t <= t_loc_final_s + TIME_TOLERANCE_S]
    revokes_before_loc = [t for t in revoke_times_s
                          if t_loc_final_s is not None and t <= t_loc_final_s + TIME_TOLERANCE_S]
    t_revoke_last_s = max(revokes_before_loc) if revokes_before_loc else None
    later_s = None
    if has_times and t_revoke_last_s is not None:
        later_s = _later_event_s(t_off_s, t_revoke_last_s, reapproach_restart,
                                 t_reapproach_end_s, t_loc_final_s)
    loc_minus_later_s = None if later_s is None else t_loc_final_s - later_s
    is_not_false_loc = (crawler_loc_period_max_N is not None and bool(weight_N)
                        and crawler_loc_period_max_N < DEPARTURE_FRACTION_OF_W * weight_N)
    loc_minus_departure_s = t_loc_final_s - t_off_s if has_times else None
    if n_revokes is None:
        n_revokes = len(revokes_in_window)
    conditions = {
        "1_revoke": bool(revokes_in_window),
        "2_delay_by_revoke": bool(loc_minus_later_s is not None
                                  and loc_minus_later_s <= t_lim_s + TIME_TOLERANCE_S),
        "3_not_false_loc": bool(is_not_false_loc),
        "4_load_strict": bool(min_force_after_off_kN is not None
                              and min_force_after_off_kN >= f_min_kN and not has_fault),
        "5_loc_before_first_done": bool(t_loc_final_s is not None and (
            t_done_s is None or t_loc_final_s <= t_done_s + TIME_TOLERANCE_S)),
        "6_total_delay": _is_total_delay_within(loc_minus_departure_s, n_revokes, t_lim_s),
    }
    is_violated = bool(loc_minus_departure_s is not None
                       and loc_minus_departure_s > t_lim_s + TIME_TOLERANCE_S)
    return {"is_flag": is_violated and all(conditions.values()),
            "time_clause_violated": is_violated, "conditions": conditions,
            "t_loc_final_s": t_loc_final_s, "t_off_s": t_off_s, "limit_s": t_lim_s,
            "t_revoke_last_s": t_revoke_last_s, "revokes_off_to_loc_s": revokes_in_window,
            "loc_minus_departure_s": loc_minus_departure_s,
            "loc_minus_later_event_s": loc_minus_later_s,
            "n_revokes": n_revokes, "total_delay_limit_s": (1 + n_revokes) * t_lim_s,
            "crawler_loc_period_max_N": crawler_loc_period_max_N,
            "condition_2_basis": ("max(t_off, t_revoke_last, t_re_end) (419.8 condition 1 true)"
                                  if reapproach_restart else "max(t_off, t_revoke_last)")}


def is_late_loc_revoked(
    *,
    t_off_s: float | None,
    t_loc_final_s: float | None,
    t_done_s: float | None,
    revoke_times_s: Sequence[float],
    crawler_loc_period_max_N: float | None,
    weight_N: float | None,
    min_force_after_off_kN: float | None,
    f_min_kN: float,
    has_fault: bool,
    reapproach_restart: bool = False,
    t_reapproach_end_s: float | None = None,
    t_lim_s: float = LOC_DELAY_MAX_S,
    n_revokes: int | None = None,
) -> bool:
    """Spec 424.8.1 / 424.9: True when the P3-2 / G6-2 time clause is violated and all six
    conditions of :func:`late_loc_revoked` hold (the FLAG ``P3-2_late_loc_revoked``); same
    arguments."""
    return late_loc_revoked(
        t_off_s=t_off_s, t_loc_final_s=t_loc_final_s, t_done_s=t_done_s,
        revoke_times_s=revoke_times_s, crawler_loc_period_max_N=crawler_loc_period_max_N,
        weight_N=weight_N, min_force_after_off_kN=min_force_after_off_kN, f_min_kN=f_min_kN,
        has_fault=has_fault, reapproach_restart=reapproach_restart,
        t_reapproach_end_s=t_reapproach_end_s, t_lim_s=t_lim_s, n_revokes=n_revokes)["is_flag"]
