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
``recontact_events``): :func:`crawler_recontact_record` and :func:`crawler_gate`.
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

    lagged_step_with_crawler_record.__dict__.update(getattr(current, "__dict__", {}))
    lagged_step_with_crawler_record.is_crawler_recorder = True
    cl._lagged_step = lagged_step_with_crawler_record


def crawler_recontact_record(series, weight_N: float | None, t_loc_s: float | None) -> dict | None:
    """U-S9-G6d input from the 1 ms crawler series: the P3-1 / P3a-2 departure and every
    recontact after its confirmation with start, end, duration, maximum and class
    (``run_S9.py`` ``crawler_departure`` / ``recontact_events``, the Chrono P3b definition; the
    harness crawler force in place of the SCM crawler normal). ``None`` without a series or a
    weight."""
    if not series or not weight_N:
        return None
    run_s9 = _run_s9()
    times_s = np.array([t for t, _ in series], dtype=float)
    crawler_N = np.array([force for _, force in series], dtype=float)
    departure = run_s9.crawler_departure(times_s, crawler_N, weight_N)
    recontact = run_s9.recontact_events(times_s, crawler_N, weight_N, departure, t_loc_s)
    return {"departure": departure, "recontact_events": recontact,
            "series_step_s": float(np.median(np.diff(times_s))) if len(times_s) > 1 else None}


def crawler_gate(is_crawler_zero_after_ready: bool, recontact: dict | None,
                 legacy_recontact_count: int | None) -> tuple[bool, list[str]]:
    """G6-1 / P3-1 of the harness (spec 420.2b, U-S9-G6d (가)): crawler load 0 after READY and
    no ``strict_fail`` recontact; a ``transient_flag`` recontact passes with the FLAG
    ``P3-1_transient_recontact``. Without the 1 ms record (``recontact`` None) the old rule
    (no recontact after the first lift-off) is kept. Returns (passes, flags)."""
    if recontact is None:
        return bool(is_crawler_zero_after_ready and legacy_recontact_count == 0), []
    events = recontact["recontact_events"]
    passes = bool(is_crawler_zero_after_ready and events["pass"])
    return passes, (list(events["flags"]) if passes else [])


def is_delay_row_pass(t_off_s: float | None, t_loc_s: float | None, t_done_s: float | None) -> bool:
    """The harness delay row as before: LOC before the first DONE and t_LOC - t_off <= T_lim."""
    return bool(t_loc_s is not None and (t_done_s is None or t_loc_s <= t_done_s + TIME_TOLERANCE_S)
                and t_off_s is not None and t_loc_s - t_off_s <= LOC_DELAY_MAX_S + TIME_TOLERANCE_S)


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
) -> dict:
    """``run_S9.p32_late_loc_block`` on harness inputs; ``is_flag`` = its ``flag``.

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
    is_within = is_delay_row_pass(t_off_s, t_loc_s, t_done_s)
    if not weight_N:
        return {"is_flag": False, "verdict": "pass" if is_within else "fail",
                "note": "no plant weight: spec 419.8 rule not judged"}
    p32 = {"t_loc_s": t_loc_s, "t_departure_s": t_off_s, "limit_s": LOC_DELAY_MAX_S,
           "loc_minus_departure_s": None if t_loc_s is None or t_off_s is None
           else t_loc_s - t_off_s,
           "within": is_within,
           "loc_before_first_done": bool(t_loc_s is not None and (
               t_done_s is None or t_loc_s <= t_done_s + TIME_TOLERANCE_S))}
    p33 = {"within": bool(min_force_after_off_kN is not None
                          and min_force_after_off_kN >= f_min_kN)}
    times_s = np.array([t for t, _ in crawler_series], dtype=float)
    crawler_N = np.array([force for _, force in crawler_series], dtype=float)
    block = _run_s9().p32_late_loc_block(
        times_s, crawler_N, float(weight_N), list(events), list(phases), p32, p33,
        period_s=CONTROL_PERIOD_S)
    return {**block, "is_flag": bool(block["flag"])}
