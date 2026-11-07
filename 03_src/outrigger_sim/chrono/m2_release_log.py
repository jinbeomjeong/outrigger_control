"""M2 release record of an L2b run (v5 stage 3 R-1 / R-2, ``stage3_impl_spec.md`` 1).

Read-only observer of ``L2bForceActuator._shift_reference_for_rod_pressure``: it exists only with
M2 on, reads the rod-side law and the shift of each hook and never feeds anything back, so the
plant values stay bit for bit. One entry per release (lock -> moving) of a leg, closed at the
next lock of that leg (``end_reason`` ``lock``), at a disarm (``disarm``) or at the run end
(``run_end``, :meth:`M2ReleaseLog.finish`).

Fields per release (pressures gauge [Pa], times [s] absolute Chrono time, shifts [m] with the
sign of ``s_ref`` (the actuator moves ``s_ref`` by ``+shift``)):

* ``leg``, ``t_rel_s`` (hook of the release), ``t_lock_start_s`` (start of the lock it ends;
  NaN when the leg was moving at the arming), ``p_r0_Pa`` (lock anchor), ``p_rel_Pa`` (locked
  law rod pressure of the release hook = ``p_r0 - delta_used``);
* ``delta_used_Pa`` = ``ReleaseStart.drop_Pa`` (what M2 used), ``delta_ref_Pa`` =
  ``G_r k_h / (k_2 A_ann)`` with ``G_r = r0`` the residual the base release decay carries from
  this hook (hydraulics-expert H-b (b), 2026-11-07: ``= G_r / A_ann`` when ``k_out`` is
  infinite);
* ``p_start_Pa`` (lag start, the M1c seed when there is one), ``p_hat_start_Pa`` =
  ``p_start + delta_used``, ``k_h_at_rel_N_m`` / ``k_2_at_rel_N_m`` / ``s_ref_rel_m`` at the
  release;
* ``t_end_s``, ``end_reason``, ``p_end_Pa`` / ``w_end`` (rod pressure and release weight of the
  last moving hook), ``shift_sum_m`` = ``S_meas`` (hook-exact sum of the shifts of the interval,
  H-b), ``p_hat_variation_Pa`` = ``V = sum |d p_hat|``, ``s_ref_excursion_m`` = ``D = max |s_ref -
  s_ref(t_rel)|``, ``clipped_steps``;
* ``was_lifted``: filled by the runner from its 1 ms pad record
  (:func:`fill_was_lifted`; None until then).

``S_M2 = A_ann (p_hat_start - (p_end + delta_used w_end)) / k_h_at_rel`` is the criteria rev. 5
3.1 value the judge compares ``shift_sum_m`` with (:func:`expected_shift_m`).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

MAX_CLIP_TIMES_PER_LEG = 20000
"""Clip times kept per leg in the result (the count is always complete)."""


class M2ReleaseLog:
    """Per-release record of one L2b actuator (module docstring).

    Args:
        annulus_area_m2: ``A_ann`` per leg.
    """

    def __init__(self, annulus_area_m2: ArrayLike) -> None:
        self._a_ann = np.array(annulus_area_m2, dtype=float).reshape(-1)
        n = self._a_ann.size
        self._prev_locked = np.zeros(n, dtype=bool)
        self._lock_start_s = np.full(n, np.nan)
        self._open: list[dict[str, Any] | None] = [None] * n
        self.releases: list[dict[str, Any]] = []
        self._last_t_s = math.nan

    def observe(self, t_s: float, oil: Any, releases: dict[int, Any],
                shift_m: NDArray[np.float64], clipped: NDArray[np.bool_],
                head_stiffness_N_m: NDArray[np.float64],
                weight: NDArray[np.float64], *, p_hat_Pa: NDArray[np.float64],
                s_ref_now_m: NDArray[np.float64], s_ref_after_m: NDArray[np.float64]) -> None:
        """One M2 hook: the releases of this hook, the shift and the lock transitions.

        Args:
            t_s: Hook time.
            oil: The rod-side law the M2 shift reads (``L2bRodSide``), after its call.
            releases: ``oil.releases_of_last_call``.
            shift_m: Shift of this hook per leg (``s_ref += shift``).
            clipped: Legs whose shift was clipped in this hook.
            head_stiffness_N_m: ``k_h`` per leg of this hook.
            weight: Release weight ``w`` per leg of this hook.
            p_hat_Pa: ``p_hat`` of this hook (after the M2 shift call).
            s_ref_now_m: ``s_ref`` the law of this hook was evaluated at (column coordinate).
            s_ref_after_m: ``s_ref`` after the M2 shift of this hook.
        """
        self._last_t_s = float(t_s)
        locked = np.asarray(oil.locked, dtype=bool)
        p_r = np.asarray(oil.rod_pressure_Pa, dtype=float)
        anchor = oil.lock_anchor_rod_pressure_Pa
        residual = oil.release_residual_N
        for leg, start in releases.items():
            self._close(leg, t_s, "lock")  # defensive: a release without the lock seen
            p_r0 = float(anchor[leg])
            drop = float(start.drop_Pa)
            s_rel = float(s_ref_now_m[leg])
            k_h = float(head_stiffness_N_m[leg])
            k_2 = float(oil.k2_N_m(int(leg), s_rel))
            self._open[leg] = {
                "leg": int(leg), "t_rel_s": float(t_s),
                "t_lock_start_s": float(self._lock_start_s[leg]),
                "p_r0_Pa": p_r0, "p_rel_Pa": p_r0 - drop,
                "delta_used_Pa": drop,
                # H-b (b): G_r k_h / (k_2 A_ann) at the release c (= G_r / A_ann with k_out inf)
                "delta_ref_Pa": float(residual[leg]) * k_h / (k_2 * float(self._a_ann[leg])),
                "p_start_Pa": float(start.start_pressure_Pa),
                "p_hat_start_Pa": float(start.start_pressure_Pa) + drop,
                "k_h_at_rel_N_m": k_h, "k_2_at_rel_N_m": k_2,
                "s_ref_rel_m": s_rel,
                "was_lifted": None,
                "t_end_s": None, "end_reason": None, "p_end_Pa": None, "w_end": None,
                "shift_sum_m": 0.0, "p_hat_variation_Pa": 0.0, "s_ref_excursion_m": 0.0,
                "clipped_steps": 0, "clip_times_s": [],
                "_p_hat_prev": float(start.start_pressure_Pa) + drop}
        for leg in range(self._a_ann.size):
            entry = self._open[leg]
            if locked[leg] and not self._prev_locked[leg]:
                self._lock_start_s[leg] = float(t_s)
                self._close(leg, t_s, "lock")
                continue
            if entry is None or locked[leg]:
                continue
            entry["shift_sum_m"] += float(shift_m[leg])
            p_hat = float(p_hat_Pa[leg])
            entry["p_hat_variation_Pa"] += abs(p_hat - entry["_p_hat_prev"])
            entry["_p_hat_prev"] = p_hat
            entry["s_ref_excursion_m"] = max(entry["s_ref_excursion_m"],
                                             abs(float(s_ref_after_m[leg]) - entry["s_ref_rel_m"]))
            entry["p_end_Pa"] = float(p_r[leg])
            entry["w_end"] = float(weight[leg])
            if clipped[leg]:
                entry["clipped_steps"] += 1
                if len(entry["clip_times_s"]) < MAX_CLIP_TIMES_PER_LEG:
                    entry["clip_times_s"].append(float(t_s))
        self._prev_locked = locked.copy()

    def disarmed(self, t_s: float) -> None:
        """The rod-side law is not armed: open releases end, lock state restarts."""
        for leg in range(self._a_ann.size):
            self._close(leg, t_s, "disarm")
        self._prev_locked[:] = False
        self._lock_start_s[:] = np.nan

    def _close(self, leg: int, t_s: float, reason: str) -> None:
        entry = self._open[leg]
        if entry is None:
            return
        entry["t_end_s"] = float(t_s)
        entry["end_reason"] = reason
        entry.pop("_p_hat_prev", None)
        self.releases.append(entry)
        self._open[leg] = None

    def finish(self) -> list[dict[str, Any]]:
        """Close the open releases at the last hook (``run_end``); the release list."""
        for leg in range(self._a_ann.size):
            self._close(leg, self._last_t_s, "run_end")
        return self.releases


def expected_shift_m(entry: dict[str, Any], annulus_area_m2: float) -> float:
    """``S_M2`` of criteria rev. 5 3.1 for one release entry (``k_h`` at the release)."""
    if entry["p_end_Pa"] is None:
        return 0.0
    p_hat_end = entry["p_end_Pa"] + entry["delta_used_Pa"] * entry["w_end"]
    return annulus_area_m2 * (entry["p_hat_start_Pa"] - p_hat_end) / entry["k_h_at_rel_N_m"]


def hook_lag_shift_m(entry: dict[str, Any], annulus_area_m2: float) -> float:
    """Criteria rev. 6 7 (b): ``A_ann (delta_used - delta_ref) / k_h`` of one release."""
    return (annulus_area_m2 * (entry["delta_used_Pa"] - entry["delta_ref_Pa"])
            / entry["k_h_at_rel_N_m"])


SUM_FLOOR_M = 1.0e-6
"""H-b (a): 1 um plus the ``k_h`` variation bound (hydraulics-expert 2026-11-07)."""
HOOK_LIMIT_M = 5.0e-6
"""H-b (b): one-hook lag as a shift, ``FLAG_M2_HOOK`` above 5 um."""
LIFTED_REAPPROACH_LIMIT_M = 0.5e-3
"""Criteria rev. 6 7 (c): shift sum of a lifted-leg release at most +0.5 mm (else stop)."""


def judge_release(entry: dict[str, Any], annulus_area_m2: float, head_area_m2: float,
                  bulk_modulus_Pa: float) -> dict[str, Any]:
    """Criteria rev. 6 7 (a)-(c) with the H-b tolerances for one release entry.

    (a) ``|S_meas - S_M2| > 1 um + A_ann / (beta A_h) V D`` -> ``FLAG_M2_SUM`` (an interval with a
    clipped step is recorded only); (b) ``A_ann |delta_used - delta_ref| / k_h > 5 um`` ->
    ``FLAG_M2_HOOK``; (c) lifted release with ``S_meas > +0.5 mm`` -> ``STOP_M2_LIFTED``.
    """
    s_meas = float(entry["shift_sum_m"])
    s_m2 = expected_shift_m(entry, annulus_area_m2)
    bound = SUM_FLOOR_M + (annulus_area_m2 / (bulk_modulus_Pa * head_area_m2)
                           * entry["p_hat_variation_Pa"] * entry["s_ref_excursion_m"])
    hook = abs(hook_lag_shift_m(entry, annulus_area_m2))
    flags = []
    if abs(s_meas - s_m2) > bound and entry["clipped_steps"] == 0:
        flags.append("FLAG_M2_SUM")
    if hook > HOOK_LIMIT_M:
        flags.append("FLAG_M2_HOOK")
    if entry.get("was_lifted") and s_meas > LIFTED_REAPPROACH_LIMIT_M:
        flags.append("STOP_M2_LIFTED")
    return {"leg": entry["leg"], "t_rel_s": entry["t_rel_s"], "S_meas_m": s_meas,
            "S_M2_m": s_m2, "sum_bound_m": bound, "hook_shift_m": hook,
            "sum_recorded_only": entry["clipped_steps"] > 0, "flags": flags}


def fill_was_lifted(releases: list[dict[str, Any]], t_s: ArrayLike,
                    lifted: ArrayLike) -> None:
    """Set ``was_lifted`` of each release: a 1 ms pad sample of its leg inside
    ``[t_lock_start_s, t_rel_s]`` with the pad off the ground (``lifted`` per sample and leg,
    e.g. ``airborne`` of ``pads.npz``). A release without a lock start reads from the record
    start."""
    t = np.asarray(t_s, dtype=float)
    air = np.asarray(lifted, dtype=bool)
    for entry in releases:
        lo = entry["t_lock_start_s"]
        lo = -math.inf if not math.isfinite(lo) else lo
        inside = (t >= lo - 1e-9) & (t <= entry["t_rel_s"] + 1e-9)
        entry["was_lifted"] = bool(np.any(air[inside, entry["leg"]]))


def release_record(log: M2ReleaseLog, flow_law_meta: dict[str, Any],
                   clip_times_s: list[list[float]], clipped_total: list[int],
                   shift_total_mm: list[float]) -> dict[str, Any]:
    """The ``hydraulics_record`` block of a Chrono run (harness key names; the clip split at
    the lift-off is made by the judge with ``harness_hydraulics.clipped_steps_by_lift``)."""
    return {"m2_law": flow_law_meta,
            "m2_shift_total_mm": list(shift_total_mm),
            "m2_clipped_steps": list(clipped_total),
            "m2_clip_times_s": [list(times[:MAX_CLIP_TIMES_PER_LEG]) for times in clip_times_s],
            "m2_clip_times_complete": all(len(times) <= MAX_CLIP_TIMES_PER_LEG
                                          for times in clip_times_s),
            "m2_releases": log.finish(),
            "m2_releases_rule": "v5 stage 3 R-1 (chrono/m2_release_log.py); shifts in s_ref "
                                "sign; delta_ref = r0 / A_ann of the release hook"}


__all__ = ["HOOK_LIMIT_M", "LIFTED_REAPPROACH_LIMIT_M", "SUM_FLOOR_M", "M2ReleaseLog",
           "expected_shift_m", "fill_was_lifted", "hook_lag_shift_m", "judge_release",
           "release_record"]
