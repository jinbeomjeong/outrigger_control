"""Lock window alignment n_late of a harness run (v5 criteria J11, X-10; control-expert A).

The controller's lock window (``two_pressure._open_lock_stretch``) ends at
``W = ((t_o + tau_v ln(max(|u_last|, eps) / eps)) + t_c) + T`` after the first 10 Hz sample t_o of
a command-free stretch. The plant locks by its law (``plant.lock_events``, 1 ms, all legs locked
at arm). A stretch is late when the plant leg is not locked at ``W + 1e-6 s``.

The stretches are rebuilt from the command record (acting command of sample k = the applied
output of sample k - 1, ``d = 1``; zero before the first sample), the windows recomputed from
the monitor settings; for the fallback legs the monitor's own stretch log (meta
``fallback_lock_log`` and ``fallback_lock_current``) must name the same stretches and windows
(two paths; a difference is an implementation defect and raises).

Times in s, speeds in m/s. Values only; the gates (VB > 0 -> H-7, LS -> L-e) are the criteria's.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

LEGS = ("FL", "FR", "RL", "RR")
TIME_TOL_S = 1.0e-6
"""Plant lock state read at ``W + TIME_TOL_S`` (control-expert A)."""
WINDOW_MATCH_TOL_S = 1.0e-12
MAX_LATE_ROWS = 50
FALLBACK_EVENT = "WARN_ROD_PRESSURE_FALLBACK"
FAULT_REASON_EVENT = "INFO_ROD_PRESSURE_FAULT_REASON"


class LockWindowMismatchError(RuntimeError):
    """The monitor's fallback stretches differ from the stretches rebuilt from the commands."""


@dataclass(frozen=True)
class WindowSettings:
    """Window inputs of the monitor (``two_pressure`` settings meta and the period)."""

    valve_tau_s: float
    eps_m_s: float
    closing_delay_s: float
    period_s: float

    @classmethod
    def from_meta(cls, settings: dict, period_s: float) -> WindowSettings:
        return cls(float(settings["lock_window_valve_tau_s"]),
                   float(settings["lock_window_eps_m_s"]),
                   float(settings.get("lock_window_closing_delay_s") or 0.0), float(period_s))

    def window_end_s(self, start_s: float, last_command_m_s: float) -> float:
        """The monitor's sum in its own order (bit for bit the same float)."""
        decay_s = self.valve_tau_s * math.log(
            max(abs(last_command_m_s), self.eps_m_s) / self.eps_m_s)
        return start_s + decay_s + self.closing_delay_s + self.period_s


@dataclass
class Stretch:
    """One command-free stretch of one leg."""

    leg: int
    start_s: float
    window_end_s: float
    close_s: float | None = None
    """First sample with a non-zero acting command again; None = open to the run end."""


def acting_commands(applied_output_m_s: np.ndarray) -> np.ndarray:
    """Acting command per sample: the applied output of the sample before (0 at the first)."""
    applied = np.asarray(applied_output_m_s, float).reshape(-1, len(LEGS))
    acting = np.zeros_like(applied)
    acting[1:] = applied[:-1]
    return acting


def rebuild_stretches(t_s: np.ndarray, acting_m_s: np.ndarray,
                      settings: WindowSettings) -> list[Stretch]:
    """Command-free stretches of every leg as the monitor opens and closes them."""
    stretches = []
    for leg in range(len(LEGS)):
        last_command_m_s = 0.0
        current = None
        for t_k, command in zip(t_s, acting_m_s[:, leg], strict=True):
            if command != 0.0:
                if current is not None:
                    current.close_s = float(t_k)
                    current = None
                last_command_m_s = float(command)
            elif current is None:
                current = Stretch(leg, float(t_k),
                                  settings.window_end_s(float(t_k), last_command_m_s))
                stretches.append(current)
    return stretches


class PlantLockHistory:
    """Plant lock state per leg from ``lock_events`` ``(t, leg, locked)`` (locked at arm)."""

    def __init__(self, lock_events) -> None:
        self._events = [[] for _ in LEGS]
        for t_s, leg, is_locked in lock_events:
            self._events[int(leg)].append((float(t_s), bool(is_locked)))

    def is_locked_at(self, leg: int, t_s: float) -> bool:
        state = True
        for event_t_s, is_locked in self._events[leg]:
            if event_t_s > t_s:
                break
            state = is_locked
        return state

    def last_lock_at_or_before(self, leg: int, t_s: float) -> float | None:
        times = [t for t, is_locked in self._events[leg] if is_locked and t <= t_s]
        return times[-1] if times else None

    def first_lock_after(self, leg: int, t_from_s: float, t_to_s: float | None) -> float | None:
        for event_t_s, is_locked in self._events[leg]:
            if event_t_s <= t_from_s or not is_locked:
                continue
            if t_to_s is not None and event_t_s >= t_to_s:
                return None
            return event_t_s
        return None

    def unlocks_between(self, leg: int, t_from_s: float, t_to_s: float) -> int:
        return sum(1 for t, is_locked in self._events[leg]
                   if not is_locked and t_from_s < t < t_to_s - TIME_TOL_S)


def fallback_legs(events) -> dict[str, dict]:
    """``{leg: {t_fallback_s, reason}}`` from the controller events."""
    reasons = {}
    for _, name in events:
        parts = name.split(":")
        if name.startswith(FAULT_REASON_EVENT) and len(parts) >= 3:
            reasons.setdefault(parts[1], parts[2])
    out = {}
    for t_s, name in events:
        parts = name.split(":")
        if name.startswith(FALLBACK_EVENT) and len(parts) >= 2 and parts[1] not in out:
            out[parts[1]] = {"t_fallback_s": round(float(t_s), 6), "reason": reasons.get(parts[1])}
    return out


def _match_monitor_log(stretches: list[Stretch], monitor_entries: list[dict]) -> dict:
    """Second path: every monitor fallback stretch is a rebuilt one with the same window."""
    by_key = {(LEGS[s.leg], s.start_s): s for s in stretches}
    mismatched, differences, matched = [], [], set()
    for entry in monitor_entries:
        stretch = by_key.get((entry["leg"], float(entry["t_start_s"])))
        if stretch is None:
            mismatched.append(entry)
            continue
        matched.add(id(stretch))
        differences.append(abs(stretch.window_end_s - float(entry["window_end_s"])))
    max_diff = max(differences, default=0.0)
    if mismatched or max_diff > WINDOW_MATCH_TOL_S:
        raise LockWindowMismatchError(
            f"stretch_mismatch {mismatched[:5]}, window max |diff| {max_diff} s")
    return {"matched_ids": matched,
            "window_check": {"compared": len(differences), "max_abs_diff_s": max_diff}}


def _stretch_row(stretch: Stretch, history: PlantLockHistory, t_end_s: float,
                 is_fallback: bool, period_s: float) -> dict:
    t_w = stretch.window_end_s
    # the acting command of sample t_c drove the plant from t_c - T on: the plant may unlock
    # from there, so unlocks are counted up to t_c - T
    zero_until_s = t_end_s if stretch.close_s is None else stretch.close_s - period_s
    is_judged = t_w <= t_end_s if stretch.close_s is None else t_w < stretch.close_s
    row = {"leg": LEGS[stretch.leg], "t_start_s": stretch.start_s, "window_end_s": t_w,
           "t_close_s": stretch.close_s, "fallback": is_fallback, "judged": is_judged}
    if not is_judged:
        return row
    is_late = not history.is_locked_at(stretch.leg, t_w + TIME_TOL_S)
    if is_late:
        t_lock = history.first_lock_after(stretch.leg, t_w, stretch.close_s)
    else:
        t_lock = history.last_lock_at_or_before(stretch.leg, t_w + TIME_TOL_S)
    lock_in_stretch = t_lock if t_lock is not None and t_lock >= stretch.start_s else None
    unlock_from = stretch.start_s if lock_in_stretch is None else lock_in_stretch
    # recorded beside the definition: the next command already drove the plant at t_w
    resumed = stretch.close_s is not None and t_w > zero_until_s + TIME_TOL_S
    row.update(late=is_late, t_lock_s=t_lock, command_resumed_before_window_end=resumed,
               margin_s=None if t_lock is None else t_w - t_lock,
               unlocks=(history.unlocks_between(stretch.leg, unlock_from, zero_until_s)
                        if t_lock is not None else 0))
    return row


def lock_window_alignment(t_s, applied_output_m_s, lock_events, monitor_meta: dict,
                          period_s: float, events, t_end_s: float) -> dict:
    """The ``lock_window_alignment`` record of one run (module docstring).

    Args:
        t_s: 10 Hz sample times of the controller updates.
        applied_output_m_s: Applied output after each update (n, 4), before the return clip.
        lock_events: ``plant.lock_events`` (not cut).
        monitor_meta: ``controller.meta()["two_pressure"]``.
        period_s: Controller period T.
        events: All controller events ``(t, name)``.
        t_end_s: Last sample time of the run.

    Raises:
        LockWindowMismatchError: The two paths differ (implementation defect).
    """
    settings_meta = monitor_meta.get("settings") or {}
    reason = None
    if not monitor_meta.get("has_rod_sensor"):
        reason = "no rod reading"
    elif monitor_meta.get("load_estimate") == "head_only":
        reason = "load estimate head_only"
    elif settings_meta.get("locked_ratio_rule") == "fixed":
        reason = "locked_ratio_rule fixed (no lock stretches)"
    if reason is not None:
        return {"n_late": None, "reason": reason}
    settings = WindowSettings.from_meta(settings_meta, period_s)
    t = np.asarray(t_s, float)
    stretches = rebuild_stretches(t, acting_commands(applied_output_m_s), settings)
    monitor_entries = (list(monitor_meta.get("fallback_lock_log") or [])
                       + list(monitor_meta.get("fallback_lock_current") or []))
    match = _match_monitor_log(stretches, monitor_entries)
    history = PlantLockHistory(lock_events)
    rows = [_stretch_row(s, history, float(t_end_s), id(s) in match["matched_ids"],
                         settings.period_s) for s in stretches]
    return _summary(rows, match["window_check"], fallback_legs(events))


def _per_leg(rows, condition) -> dict[str, int]:
    return {leg: sum(1 for row in rows if row["leg"] == leg and condition(row)) for leg in LEGS}


def _summary(rows: list[dict], window_check: dict, fallback: dict) -> dict:
    judged = [row for row in rows if row["judged"]]
    late = [row for row in judged if row["late"]]
    margins = {}
    for leg in LEGS:
        values = [row["margin_s"] for row in judged
                  if row["leg"] == leg and row["margin_s"] is not None]
        margins[leg] = min(values) if values else None
    n_late_fallback = _per_leg(late, lambda row: row["fallback"])
    fallback_margins = [row["margin_s"] for row in judged
                        if row["fallback"] and row["margin_s"] is not None]
    return {"stretches_by_leg": _per_leg(rows, lambda row: True),
            "judged_by_leg": _per_leg(judged, lambda row: True),
            "unjudged_by_leg": _per_leg(rows, lambda row: not row["judged"]),
            "n_late_by_leg": _per_leg(late, lambda row: True),
            "n_late_fallback_by_leg": n_late_fallback,
            "n_late_fallback": sum(n_late_fallback.values()),
            "fallback_legs": fallback, "margin_min_s_by_leg": margins,
            "margin_min_s_fallback": min(fallback_margins, default=None),
            "late_after_command_resumed": sum(
                row["command_resumed_before_window_end"] for row in late),
            "late": [{key: row[key] for key in ("leg", "t_start_s", "window_end_s", "t_close_s",
                                                "t_lock_s", "margin_s", "fallback",
                                                "command_resumed_before_window_end")}
                     for row in late[:MAX_LATE_ROWS]],
            "window_check": window_check,
            "unlock_in_stretch": sum(row.get("unlocks", 0) for row in judged),
            "time_tol_s": TIME_TOL_S}
