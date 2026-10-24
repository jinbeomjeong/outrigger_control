"""S6 Chrono bundle C (C2 R8-D1, 10 Hz, d = 1): pre-judgement of the bundle-C runs.

``00_docs/04_control/s6_control_spec.md`` rev. 31: 146 (absolute criteria; the reduced-model
comparison is a consistency flag only), 148 R-8, 150 (cases and criteria). Inputs are the case
directories of ``04_scripts/02_chrono/run_S6C.py`` (stage-2 files + ``r8_series.npz``). The
per-case quantities come from :func:`outrigger_sim.verify.s6_control.case_metrics` (the same
definitions as S6 stage 2); this module adds the bundle-C rows. Automatic pass / fail is a
pre-check; control-expert / dynamics-expert judge.

Rows (``passed`` True / False judged, None = report):

* every case: the S6 stage-2 rows of :func:`s6_control.judge` (source ``s6``), marked with the
  case's ``record_rate_hz`` (10 in bundle C). Item 5a uses a 1 s moving mean of
  ``round(1 s x record rate)`` samples (spec rev. 32 163.2 C-R4; it was 50 samples = 5 s on
  the 10 Hz Record before);
* C-R5 (spec rev. 32 158 / 163.2): every case with a CHECK decision gets "CHECK attitude
  error <= 0.017 deg" (controller CHECK attitude - mean true body attitude over the same window,
  :func:`check_attitude_metrics`; judged for an ideal IMU only) and an A1 usage report row
  (controller / truth crawler through the settle map / nominal floor). The s6 "run" row of a
  case that ended IDLE after ``REJ_SLOPE_D8`` is re-classified: truth usage ``<= 1 + eps_u`` =
  false rejection (failed), above = correct rejection (``kind`` "info", U-R8-15);
* R-5 (spec rev. 33 168 / 172.2 C-R8): in a regression group (:data:`REGRESSION_GROUPS`, rev. 32
  D / rev. 33 F) a case **without** a floor event judges "R-5 ``relevel_predicted`` outside a
  PROBE abort = 0" (:func:`relevel_metrics`); every floor-event case
  (:data:`R5_FLOOR_EVENTS`, any group) judges "R-5 justified firing": each firing after
  ``t_event`` and the firing leg's 1 ms true cylinder force falling at
  ``>= 20 kN/s`` averaged over the 0.3 s before the firing (:func:`relevel_justification`);
  other cases get a report row when R-5 fired;
* re-approach (spec rev. 34 177 F / FS): a no-event case of a regression group judges
  "``leg_reapproach_start`` = 0" (1-sample watch false firing, :func:`reapproach_metrics`);
  other cases report the starts;
* H (spec rev. 34 177, beta cases after the C-R11 leak fix): one ``kind`` "leak_compare" row
  per case = D8 minimum true cylinder force minus the pre-fix value of the same case id in the
  1st / rerun32 / rerun33 batches (:data:`LEAK_REFERENCE_RUNS`), ``|diff| > 3 kN`` = FLAG
  (never a failure; listed in ``meta.leak_compare_flags``). Rows of a case with a batch
  ``roles`` entry carry ``rerun_role`` ("record" failures counted apart);
* H2 (spec rev. 35 185 C-R13): the same rows against the 1st batch only, plus the REANCHOR
  minimum (:data:`LEAK_GROUP_RUNS`, :data:`LEAK_REANCHOR_GROUPS`); K (186, U-R8-28): crawler
  ``k_t`` x3 D8 minimum against the rerun34 x1 run of the base id (report);
* C-R14 (spec rev. 35 182): a 7c probe row whose truth window std is above 25 % of its limit
  is left out of the judged 7c row and reported as "truth undefined (ringing)"
  (:func:`probe_truth_ringing`);
* C-R15 (181.3): rows of a pre-fix beta case screened by 181.3 (a) / (b) carry
  ``leak_screened`` "rev35 181.3" (:data:`LEAK_SCREENED_CASES`);
* C-R8 (2): the s6 item-3 row "3 lift-off other legs in the event transient" gets the per-leg
  lift-off intervals (start after ``t_event``, length, floor-point rise) and the RR first / last
  re-contact times appended to its note (:func:`lift_interval_metrics`; limits unchanged);
* C-11 (spec rev. 33 170): rows of a case with a ``bundle_c.c11`` record carry ``c11_role``
  ("gate" = the centre value, judged; "record" = the lower bound, failures listed in the meta
  separately);
* D8 floors (``roll5.5``, ``fdown3.5``, ``fup3.5``, ``rp05``, ``rpB``, ``fdown3.2``, ``roll4.4``): 1 ms
  minimum true cylinder force after the crawler lift-off ``>= F_min + 5 kN``; no pad lift-off
  (minimum pad normal force > 0); attitude error over the last 5 s ``+ 0.02 deg`` mount share
  ``<= 0.2 deg``;
* REANCHOR (a case with REANCHOR intervals): minimum true cylinder force inside them
  ``>= F_min + 5 kN + 2 kN`` (16.41 kN on the REXOME35 YAML);
* G4: item 6 (1) minimum after the settlement start ``>= F_min``;
* C-5 (``L0r`` cases, spec rev. 31 154.3):
  C-5a guard / twist loop ringing: issued leg speed commands (``r8_series.issued_u``, 10 Hz)
  with ``|u| > 0.02 v_max`` are kept and their sign reversals counted per leg; the maximum
  over every 4 s window from the first guard start to the run end (``<= 2`` pass, 3 review,
  ``>= 4`` fail);
  C-5b guard chattering: guard activation starts in any 10 s window (``<= 2`` pass, ``>= 3``
  fail);
  C-5c READY settling oscillation: in "quiet READY" windows (READY entry + 5 s, 3 s after the
  last non-zero command, guard activity and floor event, length ``>= 2 s``) the true roll /
  pitch minus a first-order trend; half range ``<= 0.015 deg`` passes, otherwise the
  residual zero-crossing frequency ``> 1.2 Hz`` is a structural (rocking) mode = review and
  ``<= 1.2 Hz`` fails; no quiet window = review ("no quiet READY"). The attitude source is a
  1 ms truth record when the case has one, else the 10 Hz Record (noted in the row);
  report (``kind`` "report"): the former load-oscillation ratio (1 ms true cylinder force minus
  its 1 s centred moving mean, ``[t_end + 1.5, t_end + 2] s`` against ``[t_end, t_end + 0.5] s``
  after every guard interval) for the structural-mode damping record;
* C-8 (C-1 records, 10 Hz diagnosis constants and the 1.5 s mean baseline): the live D5 / E-5
  warning count must be 0 (no injection in C-1 except PS-7 constant offsets), and an offline
  replay of the load-sum baseline on the 10 Hz record (:func:`diagnostic_replay`) is reported;
* consistency (146, 153; ``kind`` "consistency", never a failure): the reduced-harness file
  :data:`CONSISTENCY_REF_PATH` (used when no other file is given). Minimum force is flagged
  when the difference exceeds ``max(10 %, 5 kN)``; READY is recorded as Chrono
  ``t_ready_minus_touch_s`` against the reference ``ready_minus_touch_s`` (no tolerance); a
  reference entry with ``min_force_kN`` null gives one "not representable: <reason>" row;
* warnings (dyn rev. 37 5.24.2): Python warnings the run recorded (``bundle_c.warnings``) are
  classified with :func:`classify_warning`; the beta 1.6 law-C ``t_sat`` upper-bound warning of
  FL / FR (2 c_n / k_n = 1.779 ms) is an expected warning and is never counted; any other
  warning gives an ``anomaly`` row (``passed`` None, never a failure);
* law-C saturation (5.24.2, report): per leg saturation steps; a non-zero count carries the
  static end value minus the limit, ``<= 0.25 kN`` = mechanism share.

Run-script helpers (dyn rev. 37 5.24, used by ``run_S6C.py``): :func:`leg_zeta_effective`,
:func:`snapshot_retag_check` / :func:`retag_snapshot` (refuse a snapshot that is not "four legs
LIFT, F_lock 0, no pad contact, u 0" when an override changes ``Params.sha256``).

Units SI internally; kN / deg / s in the rows.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from outrigger_sim.frames import roll_pitch_from_quat
from outrigger_sim.verify import s6_control as s6

D8_FLOORS = ("roll5.5", "fdown3.5", "fup3.5", "rp05", "rpB", "fdown3.2", "roll4.4")
D8_MARGIN_N = 5000.0
REANCHOR_EXTRA_N = 2000.0
"""146 / 150: REANCHOR minimum >= F_min + 5 kN + 2 kN (14.41 + 2 = 16.41 kN)."""
MOUNT_SHARE_DEG = 0.02
ATT_TOL_DEG = 0.2
OSC_FLOOR_N = 500.0
"""ASSUMPTION: below this initial oscillation amplitude a guard interval counts as calm."""
OSC_MEAN_WINDOW_S = 1.0
ATT_OSC_LIMIT_DEG = 0.015
"""ASSUMPTION (154.3 C-5c): half the 0.03 deg completion deadband."""
# --- C-5 (spec rev. 31 154.3) ---------------------------------------------------------------
C5A_DEADBAND_FRACTION = 0.02
"""ASSUMPTION (154.3 C-5a): commands with ``|u| <= 0.02 v_max`` (0.42 mm/s) are not counted."""
C5A_WINDOW_S = 4.0
"""ASSUMPTION (154.3 C-5a): sliding window of the reversal count."""
C5A_PASS_MAX = 2
C5A_FAIL_MIN = 4
"""154.3 C-5a: ``<= 2`` pass, 3 review (None), ``>= 4`` fail."""
C5B_WINDOW_S = 10.0
"""ASSUMPTION (154.3 C-5b): sliding window of the guard-start count."""
C5B_PASS_MAX = 2
C5C_READY_DELAY_S = 5.0
"""154.3 C-5c: a quiet READY window starts no earlier than READY entry + 5 s."""
C5C_QUIET_AFTER_S = 3.0
"""154.3 C-5c: ... and 3 s after the last non-zero command, guard activity or floor event."""
C5C_MIN_LENGTH_S = 2.0
C5C_STRUCTURAL_HZ = 1.2
"""154.3 C-5c: residual zero-crossing frequency above this = structural (rocking) mode."""
SETTLE_RAMP_S = 2.0
"""155 C-R2: floor event end = settlement ramp start + 2 s (s6_stage2 ``settle_RR``)."""
CONSISTENCY_REL = 0.10
CONSISTENCY_ABS_N = 5000.0
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONSISTENCY_REF_PATH = (PROJECT_ROOT / "06_analysis" / "02_control" / "r8_10hz" / "d1"
                        / "bundle_c_consistency_ref.json")
"""153: reduced-harness values (control-expert); read by :func:`judge_batch` by default."""
DIAG_SETTLE_S = 0.5
DIAG_MEAN_S = 1.5
DIAG_LIMIT_N = 4000.0
DIAG_SUM_HOLD_S = 0.5
DIAG_DRIFT_HOLD_S = 30.0
RECORD_RATE_HZ = 10.0
LEGS = ("FL", "FR", "RL", "RR")

# --- dyn rev. 37 5.24 (run_S6C rules) -------------------------------------------------------

PAD_DAMPING_OVERRIDE = "none"
"""5.24.1: pad ``cn_per_pad_N_s_m`` / ``gn_per_pad_1_s`` stay at the YAML values for every beta."""
LEG_ZETA_NOMINAL = 0.03
"""YAML ``contact.rigid_floor.L1.derivation.damping_ratio`` (ASSUMPTION, damping_survey.md)."""
EXPECTED_SATURATION_WARNING = (
    "saturation stop 0.002 s > 2 c_n/k_n FL/FR 1.779 ms (dyn 5.24.2, static overshoot <= 89 N)")
"""5.24.4: the only expected warning (beta 1.6)."""
EXPECTED_WARNING_BETA_GPA = 1.6
EXPECTED_WARNING_LEGS = ("FL", "FR")
EXPECTED_T_SAT_MAX_S = 1.779e-3
EXPECTED_T_SAT_MAX_TOL_S = 1.0e-5
SATURATION_MECHANISM_SHARE_N = 250.0
"""5.24.2: static end value - limit <= 89 N + k_n v dt (162 N) ~ 0.25 kN is the law-C share."""
L1R_STATE_LIFT = 5
"""``hydraulics.rod_chamber.RodChamberMode.LIFT`` (kept literal: no hydraulics import here)."""
RETAG_KEYS = {
    "l1r_state_LIFT": "rod_chamber.l1r_state",
    "F_lock_zero": "rod_chamber.l1r_F_lock_N",
    "no_pad_contact": "ground_bushing.in_contact",
    "u_applied_zero": "l1_actuator.u_applied_m_s",
}
"""5.24.3: snapshot payload keys of the four re-tag conditions."""

_SAT_WARN = re.compile(
    r"saturation stop time (?P<t_sat>[-+0-9.eE]+) s outside 10 dt = (?P<ten_dt>[-+0-9.eE]+) s"
    r" \.\. 2 c_n / k_n = (?P<maxes>\[[^\]]*\]|None) s")


def leg_zeta_effective(k_beta_N_m: Sequence[float], k_nominal_N_m: Sequence[float],
                       zeta_nominal: float = LEG_ZETA_NOMINAL) -> list[float]:
    """5.24.1 one-DOF equivalent leg zeta with the YAML ``c_n`` fixed:
    ``zeta_nom * sqrt(k_nominal / k_beta)`` per leg (record only, not judged)."""
    return [float(zeta_nominal) * math.sqrt(float(kn) / float(kb))
            for kb, kn in zip(k_beta_N_m, k_nominal_N_m, strict=True)]


def classify_warning(message: str, category: str, beta_GPa: float | None) -> dict[str, Any]:
    """Classify one recorded warning (5.24.2).

    Expected only when all hold: a ``RuntimeWarning`` of
    ``L1SpeedActuator.check_saturation_stop``, beta 1.6 GPa, the lower bound ``10 dt <= t_sat``
    met, and the upper bound ``t_sat <= 2 c_n / k_n`` broken by exactly FL and FR with
    ``2 c_n / k_n`` = 1.779 ms (+- 0.01 ms). Everything else is unexpected.
    """
    out: dict[str, Any] = {"message": str(message), "category": str(category),
                           "expected": False, "label": None}
    m = _SAT_WARN.search(str(message))
    if m is None or category != "RuntimeWarning":
        out["reason"] = "not the law-C t_sat warning"
        return out
    t_sat = float(m["t_sat"])
    ten_dt = float(m["ten_dt"])
    maxes = None if m["maxes"] == "None" else [
        float(v) for v in m["maxes"].strip("[]").split(",") if v.strip()]
    out.update(t_sat_s=t_sat, ten_dt_s=ten_dt, t_sat_max_s=maxes)
    if beta_GPa is None or abs(float(beta_GPa) - EXPECTED_WARNING_BETA_GPA) > 1e-9:
        out["reason"] = f"beta {beta_GPa} GPa (expected only at {EXPECTED_WARNING_BETA_GPA})"
        return out
    if t_sat < ten_dt * (1.0 - 1e-9):
        out["reason"] = "lower bound 10 dt broken"
        return out
    if maxes is None or len(maxes) != len(LEGS):
        out["reason"] = "no per-leg upper bound"
        return out
    over = [leg for leg, mx in zip(LEGS, maxes, strict=True) if t_sat > mx * (1.0 + 1e-9)]
    out["legs_over"] = over
    if tuple(over) != EXPECTED_WARNING_LEGS:
        out["reason"] = f"upper bound broken by {over}, expected {list(EXPECTED_WARNING_LEGS)}"
        return out
    if any(abs(maxes[LEGS.index(leg)] - EXPECTED_T_SAT_MAX_S) > EXPECTED_T_SAT_MAX_TOL_S
           for leg in over):
        out["reason"] = "2 c_n / k_n differs from 1.779 ms"
        return out
    out.update(expected=True, label=EXPECTED_SATURATION_WARNING, reason="dyn rev. 37 5.24.2")
    return out


def snapshot_retag_check(payload: Mapping[str, Any]) -> dict[str, Any]:
    """5.24.3 conditions on a snapshot payload (arrays by name, without the ``payload.``
    prefix): four legs ``l1r_state`` = 5 (LIFT), ``l1r_F_lock_N`` = 0,
    ``ground_bushing.in_contact`` all False, ``l1_actuator.u_applied_m_s`` = 0.
    A missing key fails its condition."""
    conds: dict[str, Any] = {}
    tests = {
        "l1r_state_LIFT": lambda a: bool(np.all(a.astype(float) == float(L1R_STATE_LIFT))),
        "F_lock_zero": lambda a: bool(np.all(a.astype(float) == 0.0)),
        "no_pad_contact": lambda a: not bool(np.any(a.astype(bool))),
        "u_applied_zero": lambda a: bool(np.all(a.astype(float) == 0.0)),
    }
    for name, key in RETAG_KEYS.items():
        value = payload.get(key)
        if value is None:
            conds[name] = {"key": key, "value": None, "passed": False, "note": "missing"}
            continue
        arr = np.asarray(value).reshape(-1)
        ok = arr.size == len(LEGS) and tests[name](arr)
        conds[name] = {"key": key, "value": arr.tolist(), "passed": ok}
        if not ok:
            conds[name]["legs_failing"] = [
                leg for leg, v in zip(LEGS, arr.tolist(), strict=False)
                if not tests[name](np.asarray([v]))]
    return {"passed": all(c["passed"] for c in conds.values()), "conditions": conds,
            "rule": "dyn rev. 37 5.24.3: four legs LIFT, F_lock 0, no pad contact, u_applied 0"}


class SnapshotRetagRefused(RuntimeError):
    """A snapshot that does not meet 5.24.3 would be re-tagged to new parameters."""


def retag_snapshot(snapshot, params_sha256: str, *, name: str = "") -> tuple[Any, dict[str, Any]]:
    """Re-tag ``snapshot`` (``engine.Snapshot``) to ``params_sha256`` after the 5.24.3 check.

    Returns ``(snapshot, check)``; ``check["required"]`` is False (and the snapshot unchanged)
    when the fingerprint is already ``params_sha256``. Raises :class:`SnapshotRetagRefused` when
    a re-tag is needed and a condition fails."""
    check = snapshot_retag_check(snapshot.payload)
    check["snapshot"] = name
    check["required"] = snapshot.params_sha256 != params_sha256
    if not check["required"]:
        return snapshot, check
    if not check["passed"]:
        bad = {k: v for k, v in check["conditions"].items() if not v["passed"]}
        raise SnapshotRetagRefused(
            f"snapshot {name or '?'} cannot be re-tagged to new parameters (dyn rev. 37 5.24.3): "
            f"{json.dumps(bad, default=str)}")
    return replace(snapshot, params_sha256=params_sha256), check


def _row(item, case, value, limit, passed, note="", kind="judged", source="bundle_c"):
    return {"item": item, "case": case, "value": value, "limit": limit, "passed": passed,
            "note": note, "kind": kind, "source": source}


def load_r8_series(case_dir: Path) -> dict[str, np.ndarray] | None:
    path = Path(case_dir) / "r8_series.npz"
    if not path.exists():
        return None
    with np.load(path, allow_pickle=False) as data:
        return {k: data[k] for k in data.files}


def guard_intervals(series: Mapping[str, np.ndarray]) -> list[tuple[float, float]]:
    """(start, end) absolute times of the control periods with the guard active."""
    t = np.asarray(series["t"], dtype=float)
    g = np.asarray(series["guard_active"], dtype=bool)
    period = float(np.median(np.diff(t))) if t.size > 1 else 1.0 / RECORD_RATE_HZ
    # the guard command of instant t[b] acts until the next instant
    return [(float(t[a]), float(t[b]) + period) for a, b in s6._runs_of(g)]


def _centred_residual(t: np.ndarray, f: np.ndarray, window_s: float) -> np.ndarray:
    dt = float(np.median(np.diff(t))) if t.size > 1 else 1.0
    n = max(1, min(int(round(window_s / dt)), f.shape[0]))
    kernel = np.ones(n) / n
    out = np.empty_like(f)
    for j in range(f.shape[1]):
        mean = np.convolve(f[:, j], kernel, mode="same")
        out[:, j] = f[:, j] - mean
    return out


def guard_oscillation_metrics(pads: Mapping[str, np.ndarray],
                              series: Mapping[str, np.ndarray]) -> list[dict[str, Any]]:
    """C-5 (a): per guard interval, amplitude right after it and 1.5-2 s later (all legs)."""
    tp = np.asarray(pads["t"], dtype=float)
    res = _centred_residual(tp, np.asarray(pads["F_cyl"], dtype=float), OSC_MEAN_WINDOW_S)
    out = []
    for _a, end in guard_intervals(series):
        first = (tp >= end) & (tp <= end + 0.5)
        later = (tp >= end + 1.5) & (tp <= end + 2.0)
        if not first.any() or not later.any():
            out.append({"t_end_s": end, "status": "run ended"})
            continue
        a0 = float(np.max(np.abs(res[first])))
        a2 = float(np.max(np.abs(res[later])))
        out.append({"t_end_s": end, "amp0_kN": a0 / 1e3, "amp2_kN": a2 / 1e3,
                    "ratio": a2 / a0 if a0 > 0 else None,
                    "passed": a0 < OSC_FLOOR_N or a2 <= 0.5 * a0})
    return out


def command_reversal_metrics(series: Mapping[str, np.ndarray],
                             v_max_m_s: float) -> dict[str, Any]:
    """C-5a: maximum number of sign reversals of one leg's issued command (``|u| > 0.02 v_max``
    samples only) inside any :data:`C5A_WINDOW_S` window from the first guard start to the run
    end. Times are those of ``series["t"]``."""
    t = np.asarray(series["t"], dtype=float)
    u = np.asarray(series["issued_u"], dtype=float)
    guards = guard_intervals(series)
    thr = C5A_DEADBAND_FRACTION * float(v_max_m_s)
    out: dict[str, Any] = {"threshold_m_s": thr, "window_s": C5A_WINDOW_S,
                           "first_guard_s": guards[0][0] if guards else None}
    if not guards:
        out.update(max_reversals=None, status="no guard activation")
        return out
    t0 = guards[0][0]
    best, best_leg, best_start = 0, None, None
    per_leg = []
    for j, leg in enumerate(LEGS):
        keep = (t >= t0 - 1e-9) & (np.abs(u[:, j]) > thr)
        tk, sk = t[keep], np.sign(u[keep, j])
        rev = np.flatnonzero(sk[1:] != sk[:-1])
        pairs = [(float(tk[i]), float(tk[i + 1])) for i in rev]  # (previous, reversing) sample
        per_leg.append(len(pairs))
        for a, _b in pairs:
            n = sum(1 for p, q in pairs if p >= a - 1e-9 and q < a + C5A_WINDOW_S - 1e-9)
            if n > best:
                best, best_leg, best_start = n, leg, a
    out.update(max_reversals=best, leg=best_leg, window_start_s=best_start,
               reversals_total_per_leg=dict(zip(LEGS, per_leg, strict=True)))
    return out


def c5a_verdict(n: int | None) -> bool | None:
    if n is None:
        return None
    if n <= C5A_PASS_MAX:
        return True
    return False if n >= C5A_FAIL_MIN else None


def guard_restart_metrics(series: Mapping[str, np.ndarray]) -> dict[str, Any]:
    """C-5b: guard activation starts, total and the maximum in any :data:`C5B_WINDOW_S`
    window."""
    starts = [a for a, _b in guard_intervals(series)]
    worst = max((sum(1 for s in starts if a - 1e-9 <= s < a + C5B_WINDOW_S - 1e-9)
                 for a in starts), default=0)
    return {"starts_s": starts, "starts": len(starts), "max_in_window": worst,
            "window_s": C5B_WINDOW_S}


def quiet_ready_windows(ready_windows: Sequence[tuple[float, float]],
                        busy_until: Sequence[tuple[float, float]],
                        grid_t: np.ndarray) -> list[tuple[float, float]]:
    """C-5c windows on ``grid_t``: inside a READY interval from its entry +
    :data:`C5C_READY_DELAY_S`, outside every ``(start, end)`` of ``busy_until`` (already
    extended by :data:`C5C_QUIET_AFTER_S`), length ``>= C5C_MIN_LENGTH_S``."""
    t = np.asarray(grid_t, dtype=float)
    quiet = np.zeros(t.size, dtype=bool)
    for a, b in ready_windows:
        quiet |= (t >= a + C5C_READY_DELAY_S - 1e-9) & (t <= b + 1e-9)
    for a, b in busy_until:
        quiet &= ~((t >= a - 1e-9) & (t < b - 1e-9))
    out = []
    for i, j in s6._runs_of(quiet):
        if t[j] - t[i] >= C5C_MIN_LENGTH_S - 1e-9:
            out.append((float(t[i]), float(t[j])))
    return out


def attitude_residual_metrics(t: np.ndarray, rp_deg: np.ndarray,
                              windows: Sequence[tuple[float, float]]) -> dict[str, Any]:
    """C-5c: per quiet window and channel (roll, pitch) the half range of the attitude minus a
    first-order trend and the residual zero-crossing frequency; the worst one is reported."""
    t = np.asarray(t, dtype=float)
    rp = np.asarray(rp_deg, dtype=float)
    per = []
    for a, b in windows:
        sel = (t >= a - 1e-9) & (t <= b + 1e-9)
        if sel.sum() < 3:
            continue
        ts = t[sel]
        for c, name in enumerate(("roll", "pitch")):
            y = rp[sel, c]
            res = y - np.polyval(np.polyfit(ts - ts[0], y, 1), ts - ts[0])
            s = np.sign(res)
            s = s[s != 0]
            zc = int(np.count_nonzero(s[1:] != s[:-1])) if s.size > 1 else 0
            dur = float(ts[-1] - ts[0])
            per.append({"window_s": [float(a), float(b)], "channel": name,
                        "half_range_deg": float(np.ptp(res) / 2.0),
                        "zero_cross_hz": zc / (2.0 * dur) if dur > 0 else None})
    worst = max(per, key=lambda r: r["half_range_deg"], default=None)
    return {"windows": [list(w) for w in windows], "per_window": per, "worst": worst}


def c5c_verdict(half_deg: float | None, freq_hz: float | None) -> bool | None:
    if half_deg is None:
        return None
    if half_deg <= ATT_OSC_LIMIT_DEG:
        return True
    if freq_hz is not None and freq_hz > C5C_STRUCTURAL_HZ:
        return None
    return False


def _floor_event_intervals(case: Mapping[str, Any], tm: Mapping[str, Any],
                           m: Mapping[str, Any]) -> list[tuple[float, float]]:
    """Floor events as ``(start, end)`` relative to ``t0``: G4 ``settle_RR`` = first READY + 5 s
    (``s6_control.settle_checks``) + :data:`SETTLE_RAMP_S`; RE1b family = ``event_t_s`` +
    :data:`SETTLE_RAMP_S` (not a C-5 case; same rule)."""
    item6 = m.get("item6")
    if isinstance(item6, Mapping) and item6.get("settlement_start_s") is not None:
        a = float(item6["settlement_start_s"])
        return [(a, a + SETTLE_RAMP_S)]
    t_ev = s6._event_time_s(case, tm)
    return [] if t_ev is None else [(t_ev, t_ev + SETTLE_RAMP_S)]


def _attitude_truth(case: Mapping[str, Any], tm: Mapping[str, Any]
                    ) -> tuple[np.ndarray, np.ndarray, str]:
    """True roll / pitch [deg] relative to ``t0``: the 1 ms pad record when it carries
    ``body_quat_wxyz``, else the Record (10 Hz in bundle C)."""
    pads = case.get("pads")
    if pads is not None and "body_quat_wxyz" in pads:
        t, q, src = pads["t"], pads["body_quat_wxyz"], "pads 1 ms"
    else:
        rec = case["rec"]
        t, q = rec["t"], rec["body_quat_wxyz"]
        dt = float(np.median(np.diff(t))) if len(t) > 1 else float("nan")
        src = f"Record {1.0 / dt:.0f} Hz (1 ms attitude not recorded)" if dt > 0 else "Record"
    rp = np.degrees(np.array([roll_pitch_from_quat(qq) for qq in q])).reshape(-1, 2)
    return np.asarray(t, dtype=float) - tm["t0"], rp, src


def ready_settling_metrics(case: Mapping[str, Any], tm: Mapping[str, Any],
                           m: Mapping[str, Any], series: Mapping[str, np.ndarray] | None
                           ) -> dict[str, Any]:
    """C-5c on a case (times relative to ``t0``)."""
    if series is None:
        return {"status": "no r8_series"}
    st = np.asarray(series["t"], dtype=float) - tm["t0"]
    period = float(np.median(np.diff(st))) if st.size > 1 else 1.0 / RECORD_RATE_HZ
    u = np.asarray(series["issued_u"], dtype=float)
    busy = [(float(x), float(x) + period + C5C_QUIET_AFTER_S)
            for x in st[np.any(u != 0.0, axis=1)]]
    busy += [(a - tm["t0"], b - tm["t0"] + C5C_QUIET_AFTER_S) for a, b in guard_intervals(series)]
    events = _floor_event_intervals(case, tm, m)
    busy += [(a, b + C5C_QUIET_AFTER_S) for a, b in events]
    t, rp, src = _attitude_truth(case, tm)
    windows = quiet_ready_windows(s6._phase_windows(case, "ready", tm["end"]), busy, t)
    out = attitude_residual_metrics(t, rp, windows)
    out.update(source=src, floor_events_s=[list(e) for e in events])
    return out


def diagnostic_replay(case: Mapping[str, Any], params) -> dict[str, Any]:
    """C-8 offline replay: load-sum baseline (mean of the command-free net readings over
    :data:`DIAG_MEAN_S` after :data:`DIAG_SETTLE_S` of zero commands in each READY / DONE
    stay) and the longest run with ``|sum - baseline| > 4 kN`` while the commands stay zero."""
    from outrigger_sim.sensors.hydraulic import (
        leg_annulus_areas_from_params,
        leg_head_areas_from_params,
    )

    rec = case["rec"]
    tm = s6._times(case)
    t = rec["t"] - tm["t0"]
    head = np.asarray(rec["meas.head_pressure"], dtype=float)
    rod = rec.get("meas.rod_pressure")
    rod = np.zeros_like(head) if rod is None else np.nan_to_num(np.asarray(rod, dtype=float))
    net = head * leg_head_areas_from_params(params) - rod * leg_annulus_areas_from_params(params)
    total = net.sum(axis=1)
    u = np.asarray(rec["u_cmd"], dtype=float)
    zero = np.all(u == 0.0, axis=1)
    period = 1.0 / RECORD_RATE_HZ
    longest = 0.0
    max_dev = 0.0
    refs = []
    for phase in ("ready", "done"):
        for a, b in s6._phase_windows(case, phase, tm["end"]):
            sel = (t >= a) & (t <= b)
            idx = np.flatnonzero(sel)
            if idx.size == 0:
                continue
            # command-free since
            run_start = None
            ref = None
            buf: list[float] = []
            run = 0.0
            for i in idx:
                if not zero[i]:
                    run_start, ref, buf, run = None, None, [], 0.0
                    continue
                if run_start is None:
                    run_start = t[i]
                if ref is None:
                    if t[i] - run_start >= DIAG_SETTLE_S - 1e-9:
                        buf.append(total[i])
                        if len(buf) * period >= DIAG_MEAN_S - 1e-9:
                            ref = float(np.mean(buf))
                            refs.append({"t_s": float(t[i]), "sum_kN": ref / 1e3})
                    continue
                dev = abs(total[i] - ref)
                max_dev = max(max_dev, dev)
                run = run + period if dev > DIAG_LIMIT_N else 0.0
                longest = max(longest, run)
    passed: bool | None
    if longest >= DIAG_DRIFT_HOLD_S - 1e-9:
        passed = False
    elif longest < DIAG_SUM_HOLD_S - 1e-9:
        passed = True
    else:
        passed = None
    return {"baselines": refs, "longest_run_over_4kN_s": longest,
            "max_abs_dev_kN": max_dev / 1e3, "replay_passed": passed,
            "rule": f"settle {DIAG_SETTLE_S} s, mean {DIAG_MEAN_S} s, limit {DIAG_LIMIT_N} N, "
                    f"D5 hold {DIAG_SUM_HOLD_S} s, E-5 hold {DIAG_DRIFT_HOLD_S} s, 10 Hz record"}


CHECK_ATT_ERR_LIMIT_DEG = 0.017
"""ASSUMPTION (spec rev. 32 158.1 / 163.4, C-R5): CHECK attitude error (controller - truth over
the same window) limit = the U11 settling residual 0.017 deg."""
CHECK_WINDOW_META_KEY = "check_window"
"""P-R8-9 (``control/c2.py`` ``_raw_check_attitude_rad``): controller ``meta()["target"]``
dict ``{t_judged_s, t_first_sample_s, t_last_sample_s, sample_count, quiet_start_s,
last_nonzero_command_t_s, is_quiet_window_full}``. The times are the controller's
``Measurements.t_s`` = the engine time (absolute, the same clock as Record ``t``; runner
``on_step`` passes ``eng.imu_sample().t_s``). Each raw-tilt sample at ``t`` is the box mean of the
IMU over ``(t - T_imu, t]``, so the averaged interval is
``(t_first_sample_s - T_imu, t_last_sample_s]``. ``None`` while CHECK has not ended or on the
filtered (R7) path; then the window falls back to ``(t_decision - check_average_s, t_decision]``."""
CHECK_WINDOW_SAMPLE_KEYS = ("t_first_sample_s", "t_last_sample_s", "sample_count")
REJ_SLOPE_D8 = "REJ_SLOPE_D8"
REGRESSION_GROUPS = ("D", "F", "FS")
"""Re-run groups whose no-event cases judge "R-5 = 0" and "re-approach starts = 0" (rev. 32 160
D, rev. 33 169 F, rev. 34 177 F / FS = the PS sensor case)."""
REAPPROACH_EVENT = "leg_reapproach_start"
"""P-R8-12 / P-R8-13 event ``leg_reapproach_start:<leg>`` (control/c2.py)."""
LEAK_GROUP = "H"
"""Spec rev. 34 177 H: beta cases re-run after the C-R11 leak fix."""
LEAK_FLAG_KN = 3.0
"""Spec rev. 34 177: a minimum-force difference beyond 3 kN against a pre-fix run is flagged
(the spec's decision point is a drop beyond -3 kN; both signs are flagged, the note says which)."""
LEAK_REFERENCE_RUNS = (
    ("1st", "07_results/S6/bundleC_L1R_20261024_100736", "verify_S6C_CR4_CR5.json"),
    ("rerun32", "07_results/S6/bundleC_rerun32_L1R_20261024_114455", "verify_S6C_rev33_CR8.json"),
    ("rerun33", "07_results/S6/bundleC_rerun33_L1R_20261024_125604", "verify_S6C.json"),
)
"""Pre-fix (beta leak, spec 176) judged runs: label, batch directory (project relative), judge
file (the latest re-judgement of each batch; ``verify_S6C.json`` when the named file is absent).
The compared quantity is ``min_cyl_after_liftoff_kN`` (D8 minimum true cylinder force)."""
LEAK_GROUP_RUNS = {LEAK_GROUP: ("1st", "rerun32", "rerun33"), "H2": ("1st",)}
"""Re-run group -> pre-fix runs its ``leak_compare`` rows use (spec rev. 35 185 / C-R13: the H2
cases compare with the 1st batch only)."""
LEAK_REANCHOR_GROUPS = ("H2",)
"""Groups that also compare the REANCHOR minimum (H4 nose-down cases, spec rev. 35 181.3 (c))."""
LEAK_SCREENED_TAG = "rev35 181.3"
LEAK_SCREENED_CASES = {
    # (a) minimum in the crawler lift-off transient (< 2 s after lift-off)
    "C1_D8_top_roll5.5_b0.69": "(a)", "C4_tv0.05_D8_top_roll5.5_b1.6": "(a)",
    "C4_tv0.15_D8_top_roll5.5_b1.6": "(a)", "C4b_D8_top_roll5.5_b1.6": "(a)",
    "C4b_D8_bottom_rpB_b1.6": "(a)", "C7_sym0.1_D8_top_rp05_b1.6": "(a)",
    # (b) minimum after the lift-off (>= 29 s), only the controller gain leak reaches it
    "C1_D8_middle_rpB_b1.6": "(b)", "C1_D8_bottom_rpB_b1.6": "(b)",
    "C1_D8_top_fup3.5_b1.6": "(b)", "C4_tv0.05_D8_top_fup3.5_b1.6": "(b)",
    "C4_tv0.15_D8_top_fup3.5_b1.6": "(b)", "C6_D8_top_roll5.5_b1.6": "(b)",
    "C7_sym0.1_D8_top_roll5.5_b1.6": "(b)",
}
"""Spec rev. 35 181.3 / 188.1 C-R15 (U-R8-26): beta != 1.0 D8 cases of the 1st / rerun32 batches
kept by the minimum-location screening. Rows of such a case get ``leak_screened`` =
:data:`LEAK_SCREENED_TAG` (+ ``leak_screened_class``) only when the run predates the C-R11 fix
(``result.json`` without ``bundle_c.beta_leak_fix``); values are not changed."""
SENS_GROUP = "K"
SENS_REFERENCE_RUN = ("rerun34", "07_results/S6/bundleC_rerun34_L1R_20261024_141040",
                      "verify_S6C.json")
"""Spec rev. 35 186 / U-R8-28: the crawler ``k_t`` x3 record case is compared (report) with the
x1 run of its base case id after the C-R11 fix."""
SENS_SUFFIX = "_crkt3"
TRUTH_RINGING_FRACTION = 0.25
"""Spec rev. 35 182 / 188.1 C-R14 (ASSUMPTION): a 7c row whose truth window (0.5 s before the
first move) has a true cylinder force standard deviation above this fraction of its limit
``max(5 kN, 10 %)`` is a "truth undefined (ringing)" report row, not a judged one."""
R5_FLOOR_EVENTS = s6.GROUND_SETTLEMENT_EVENTS
"""Floor-event cases (G4 ``settle_RR`` and the RE1b family): R-5 judged as justified firing."""
R5_JUSTIFIED_RATE_N_S = 20.0e3
"""Spec rev. 33 168 / 172.5: firing leg's force decline rate >= R-5 ``rate_threshold_N_s``."""
R5_RATE_WINDOW_S = 0.3
"""Spec rev. 33 168: the decline rate is the mean over the 0.3 s before the firing."""
LIFT_ROW_ITEM = "3 lift-off other legs in the event transient"
"""The s6 item-3 row that gets the C-R8 lift-interval note."""
RELEVEL_EVENT = "relevel_predicted"
PROBE_ABORT_EVENT = "probe_aborted_low_load"
SAME_PERIOD_TOL_S = 1e-6
"""Events of one control period carry the same ``t_s`` (both are added in the same update)."""


def _target_limits(limits_rad: Mapping[str, Any]):
    from outrigger_sim.control.target import TargetLimits

    fields = TargetLimits.__dataclass_fields__
    return TargetLimits(**{k: v for k, v in limits_rad.items() if k in fields})


def _settle_map(meta: Mapping[str, Any] | None):
    from outrigger_sim.control.target import CrawlerSettleMap

    if not meta:
        return CrawlerSettleMap.identity()
    return CrawlerSettleMap(math.radians(float(meta["theta0_deg"])), float(meta["k_dn"]),
                            float(meta["k_up"]), float(meta["k_phi"]))


def check_attitude_metrics(case: Mapping[str, Any]) -> dict[str, Any] | None:
    """C-R5 (spec rev. 32 158 / 163.2): CHECK attitude of the controller against the true body
    attitude over the same window, and the A1 floor usage from (a) the controller value, (b) the
    true crawler attitude through the run's settle map, (c) the nominal floor of the case.

    Window: the controller's ``target.check_window`` (P-R8-9, :data:`CHECK_WINDOW_META_KEY`;
    absolute engine time) = ``(t_first_sample_s - T_imu, t_last_sample_s]`` with ``T_imu`` the
    raw-tilt sample period (``settings.bundle_c.imu_sample_period_s``, else from the window), else
    the Record samples (10 Hz control instants) in ``(t_dec - check_average_s, t_dec]`` with
    ``t_dec`` = the first control instant whose phase is no longer CHECK (``r8_series.phase``;
    the phase list as fallback). The truth is the mean of the instantaneous body roll / pitch in
    that window: the 1 ms pad record when it carries ``body_quat_wxyz``, else the Record
    (``body_quat_wxyz``, 10 Hz). ``None`` when the case has no CHECK decision."""
    res = case["result"]
    acc = res.get("acceptance") or {}
    lc = acc.get("last_check") or {}
    ctrl = lc.get("crawler_attitude_rad")
    tgt = (res.get("controller_meta") or {}).get("target") or {}
    if ctrl is None or not tgt:
        return None
    t0 = float(res["settings"]["start_t_s"])
    window, source, cw = None, None, tgt.get(CHECK_WINDOW_META_KEY)
    if isinstance(cw, Mapping) and all(cw.get(k) is not None for k in CHECK_WINDOW_SAMPLE_KEYS):
        a, b, n = (float(cw["t_first_sample_s"]), float(cw["t_last_sample_s"]),
                   int(cw["sample_count"]))
        t_imu = (res["settings"].get("bundle_c") or {}).get("imu_sample_period_s")
        if t_imu is None:
            t_imu = (b - a) / (n - 1) if n > 1 else 0.0
        window = (a - float(t_imu), b)
        source = (f"controller meta target.{CHECK_WINDOW_META_KEY} ({n} raw tilts at "
                  f"{float(t_imu) * 1e3:g} ms, quiet window full "
                  f"{cw.get('is_quiet_window_full')})")
    else:
        cw = None
    avg = float(tgt.get("check_average_s") or 1.0)
    t_dec = None
    series = load_r8_series(Path(case["dir"])) if case.get("dir") is not None else None
    if series is not None and "phase" in series:
        ph = np.asarray(series["phase"]).astype(str)
        idx = np.flatnonzero(ph == "check")
        if idx.size and idx[-1] + 1 < ph.size:
            t_dec = float(series["t"][idx[-1] + 1])
    if t_dec is None:
        phases = [(float(t), p) for t, p in res["phases"]]
        for (_t, p), (t2, _p2) in zip(phases[:-1], phases[1:], strict=False):
            if p == "check":
                t_dec = t2 + t0
    if window is None:
        if t_dec is None:
            return None
        window = (t_dec - avg, t_dec)
        source = f"(t_dec - {avg:g} s, t_dec] on the Record control instants (fallback)"
    pads = case.get("pads")
    if pads is not None and "body_quat_wxyz" in pads:
        t_abs, quats, truth_src = (np.asarray(pads["t"], dtype=float), pads["body_quat_wxyz"],
                                   "pads 1 ms")
    else:
        rec = case["rec"]
        t_abs, quats, truth_src = (np.asarray(rec["t"], dtype=float), rec["body_quat_wxyz"],
                                   "Record 10 Hz")
    sel = (t_abs > window[0] + 1e-9) & (t_abs <= window[1] + 1e-9)
    if not sel.any():
        return {"status": f"no {truth_src} sample in the CHECK window",
                "window_abs_s": list(window), "window_source": source, "check_window": cw}
    rp = np.array([roll_pitch_from_quat(q) for q in np.asarray(quats)[sel]])
    truth = (float(rp[:, 0].mean()), float(rp[:, 1].mean()))
    err_deg = [math.degrees(ctrl[0] - truth[0]), math.degrees(ctrl[1] - truth[1])]
    from outrigger_sim.control.target import floor_usage

    limits = _target_limits(tgt.get("limits_rad") or {})
    smap = _settle_map(tgt.get("crawler_settle_map"))
    use_ctrl = lc.get("floor_usage")
    use_truth = floor_usage(smap.floor_from_crawler(truth), limits)
    nominal = acc.get("floor_true_deg")
    use_nom = None if nominal is None else floor_usage(
        (math.radians(nominal[0]), math.radians(nominal[1])), limits)
    return {"code": lc.get("code"), "window_abs_s": list(window), "window_source": source,
            "check_window": cw, "truth_source": truth_src,
            "t_decision_s": None if t_dec is None else t_dec - t0,
            "n_samples": int(sel.sum()),
            "controller_deg": [math.degrees(v) for v in ctrl],
            "truth_deg": [math.degrees(v) for v in truth],
            "error_deg": err_deg, "error_maxabs_deg": max(abs(v) for v in err_deg),
            "usage_controller": use_ctrl, "usage_truth_crawler": use_truth,
            "usage_floor_nominal": use_nom, "usage_tolerance": limits.usage_tolerance,
            "settle_map": tgt.get("crawler_settle_map"),
            "note": f"truth = mean of the {truth_src} instantaneous body attitude"
                    + ("" if truth_src != "Record 10 Hz" else
                       " (rocking 1.6-2.4 Hz is sampled 4-6 times per cycle)")}


def _phase_at(phases: Sequence[tuple[float, str]], t_rel: float, *, before: bool) -> str | None:
    """Phase in force at ``t_rel`` (``before`` True: just before an entry at ``t_rel``)."""
    out = None
    for t, p in phases:
        if t < t_rel - SAME_PERIOD_TOL_S or (not before and t <= t_rel + SAME_PERIOD_TOL_S):
            out = p
    return out


def relevel_metrics(case: Mapping[str, Any]) -> dict[str, Any]:
    """R-5 ``relevel_predicted:<leg>`` events split by cause (spec rev. 32 160 D group).

    ``probe_abort``: in the same control period (same ``t_s``) the controller also logged
    ``probe_aborted_low_load:<leg>`` — R-5 fired while PROBE watched a non-probed leg
    (P-R8-11), a legitimate stop of the probe. ``other``: every other R-5 event (READY etc.),
    the D-group regression count. The phase before / at the event instant is recorded."""
    t0 = float(case["result"]["settings"]["start_t_s"])
    phases = [(float(t), str(p)) for t, p in case["result"].get("phases") or []]
    events = s6._events(case)
    aborts = [(t, n) for t, n in events if n.split(":")[0] == PROBE_ABORT_EVENT]
    out: dict[str, Any] = {"probe_abort": [], "other": [],
                           "probe_aborted_low_load": [
                               {"t_s": t - t0, "leg": n.partition(":")[2]} for t, n in aborts]}
    for t, n in events:
        if n.split(":")[0] != RELEVEL_EVENT:
            continue
        pair = [a for a in aborts if abs(a[0] - t) <= SAME_PERIOD_TOL_S]
        entry = {"t_s": t - t0, "leg": n.partition(":")[2],
                 "phase_before": _phase_at(phases, t - t0, before=True),
                 "phase_after": _phase_at(phases, t - t0, before=False)}
        if pair:
            entry["abort_legs"] = [a[1].partition(":")[2] for a in pair]
            out["probe_abort"].append(entry)
        else:
            out["other"].append(entry)
    out["counts"] = {"probe_abort": len(out["probe_abort"]), "other": len(out["other"])}
    return out


def floor_event_time_s(case: Mapping[str, Any], tm: Mapping[str, Any],
                       m: Mapping[str, Any] | None = None) -> float | None:
    """``t_event`` relative to ``t0`` of a floor-event case (:data:`R5_FLOOR_EVENTS`): G4 = the
    item-6 settlement start (else ``result.json`` ``event_t_s``), RE1b family =
    ``s6_control._event_time_s``; ``None`` without a floor event."""
    res = case["result"]
    if res["settings"].get("event") not in R5_FLOOR_EVENTS:
        return None
    item6 = (m or {}).get("item6")
    if isinstance(item6, Mapping) and item6.get("settlement_start_s") is not None:
        return float(item6["settlement_start_s"])
    t_ev = s6._event_time_s(case, tm)
    if t_ev is None and res.get("event_t_s") is not None:
        t_ev = float(res["event_t_s"])
    return t_ev


def relevel_justification(case: Mapping[str, Any], tm: Mapping[str, Any],
                          rv: Mapping[str, Any], t_event_s: float | None) -> dict[str, Any]:
    """C-R8 (spec rev. 33 168): per R-5 firing (both causes of :func:`relevel_metrics`) the
    firing leg's 1 ms true cylinder force decline rate ``(F(t - 0.3 s) - F(t)) / 0.3 s`` on the
    pad record (``pads.F_cyl``, the samples nearest to both ends) and ``t > t_event``.
    Times relative to ``t0``; rates in N/s (positive = falling)."""
    pads = case.get("pads")
    out: dict[str, Any] = {"t_event_s": t_event_s, "rate_window_s": R5_RATE_WINDOW_S,
                           "rate_limit_N_s": R5_JUSTIFIED_RATE_N_S, "firings": []}
    firings = list(rv.get("other") or []) + list(rv.get("probe_abort") or [])
    if pads is None:
        out["status"] = "no pad record"
        return out
    tp = np.asarray(pads["t"], dtype=float) - tm["t0"]
    force = np.asarray(pads["F_cyl"], dtype=float)
    for e in sorted(firings, key=lambda x: x["t_s"]):
        leg = e["leg"]
        entry = {"t_s": e["t_s"], "leg": leg, "phase_before": e.get("phase_before"),
                 "after_event": None if t_event_s is None else e["t_s"] > t_event_s + 1e-9}
        if leg not in LEGS:
            entry["status"] = f"unknown leg {leg!r}"
            out["firings"].append(entry)
            continue
        j = LEGS.index(leg)
        i1 = int(np.searchsorted(tp, e["t_s"] + 1e-9)) - 1
        i0 = int(np.searchsorted(tp, e["t_s"] - R5_RATE_WINDOW_S + 1e-9)) - 1
        if i1 < 0 or i0 < 0 or i1 <= i0:
            entry["status"] = "pad record does not cover the 0.3 s window"
            out["firings"].append(entry)
            continue
        span = float(tp[i1] - tp[i0])
        rate = float(force[i0, j] - force[i1, j]) / span
        entry.update(rate_N_s=rate, F_start_kN=float(force[i0, j]) / 1e3,
                     F_end_kN=float(force[i1, j]) / 1e3, window_s=[float(tp[i0]), float(tp[i1])],
                     t_after_event_s=None if t_event_s is None else e["t_s"] - t_event_s,
                     justified=bool(entry["after_event"]) and rate >= R5_JUSTIFIED_RATE_N_S)
        out["firings"].append(entry)
    return out


def lift_interval_metrics(case: Mapping[str, Any], tm: Mapping[str, Any], params,
                          t_event_s: float | None) -> dict[str, Any] | None:
    """C-R8 (2): lift-off intervals (true pad normal force ``<= 0``, 1 ms pad record) after
    ``t_event`` of FL / FR / RL as ``(start after t_event, length, floor-point rise)`` with the
    rise = maximum floor-point height inside the interval minus the mean over the
    ``PRE_EVENT_REFERENCE_S`` before the event (``s6_control._floor_point_heights_m``, L1 pad
    stiffness of the run's parameters); RR: first lift-off, first and last re-contact after the
    event. ``None`` without a floor event or pad record. s / m."""
    pads = case.get("pads")
    if pads is None or t_event_s is None:
        return None
    tp = np.asarray(pads["t"], dtype=float) - tm["t0"]
    lifted = np.asarray(pads["N"], dtype=float) <= 0.0
    after = tp >= t_event_s
    dt = np.diff(tp, append=tp[-1] + (tp[-1] - tp[-2] if tp.size > 1 else 0.0))
    kn = s6._pad_kn(params)
    rise = None
    before = (tp >= t_event_s - s6.PRE_EVENT_REFERENCE_S) & (tp < t_event_s)
    if kn is not None and "n_world" in pads and before.any():
        heights = s6._floor_point_heights_m(pads, kn)
        rise = heights - heights[before].mean(axis=0)
    idx = np.flatnonzero(after)
    out: dict[str, Any] = {"t_event_s": t_event_s, "intervals": {},
                           "rise_source": "floor point, pre-event mean" if rise is not None
                           else "not measured"}
    for j, leg in enumerate(LEGS[:3]):
        rows = []
        for a, b in s6._runs_of(lifted[idx, j]):
            ia, ib = idx[a], idx[b]
            rows.append({"start_after_event_s": float(tp[ia] - t_event_s),
                         "length_s": float(dt[ia:ib + 1].sum()),
                         "rise_m": None if rise is None else float(rise[ia:ib + 1, j].max())})
        out["intervals"][leg] = rows
    rr = lifted[idx, 3]
    first_lift = int(np.argmax(rr)) if rr.any() else None
    rr_out: dict[str, Any] = {"lifted": bool(rr.any())}
    if first_lift is not None:
        rr_out["first_lift_after_event_s"] = float(tp[idx[first_lift]] - t_event_s)
        back = np.flatnonzero(~rr[first_lift:])
        rr_out["first_recontact_after_event_s"] = (
            None if back.size == 0 else float(tp[idx[first_lift + back[0]]] - t_event_s))
        last_lift = int(np.flatnonzero(rr)[-1])
        rr_out["last_recontact_after_event_s"] = (
            None if last_lift + 1 >= idx.size else float(tp[idx[last_lift + 1]] - t_event_s))
        rr_out["lifted_total_s"] = float(dt[idx][rr].sum())
    out["RR"] = rr_out
    return out


def _lift_note(li: Mapping[str, Any]) -> str:
    """Note text of :func:`lift_interval_metrics` (s, mm)."""
    parts = []
    for leg, rows in li["intervals"].items():
        if not rows:
            continue
        txt = " ".join(
            f"({r['start_after_event_s']:.2f}, {r['length_s']:.3f}, "
            + ("-" if r["rise_m"] is None else f"{r['rise_m'] * 1e3:.2f}") + ")" for r in rows)
        parts.append(f"{leg} {len(rows)}x [start s, length s, rise mm] {txt}")
    rr = li.get("RR") or {}
    if rr.get("lifted"):
        f, last = rr.get("first_recontact_after_event_s"), rr.get("last_recontact_after_event_s")
        parts.append("RR first / last re-contact "
                     f"{'none' if f is None else f'{f:.2f}'} / "
                     f"{'none' if last is None else f'{last:.2f}'} s after t_event "
                     f"(lifted {rr.get('lifted_total_s', 0.0):.2f} s)")
    else:
        parts.append("RR never lifted after t_event")
    return "C-R8 lift intervals (report): " + ("; ".join(parts) if parts else "none")


def bundle_c_metrics(case: Mapping[str, Any], params) -> dict[str, Any]:
    """:func:`s6_control.case_metrics` + the bundle-C quantities."""
    m = s6.case_metrics(case, params)
    bc = case["result"]["settings"].get("bundle_c", {})
    m["bundle_c"] = {"config": bc.get("config"), "beta_GPa": bc.get("beta_GPa"),
                     "tau_v_s": bc.get("tau_v_s"), "amp_ramp": bc.get("amp_ramp"),
                     "L0r_m": bc.get("L0r_m"), "command_offset_s": bc.get("command_offset_s"),
                     "increment": bc.get("increment"),
                     "twist_reference": bc.get("twist_reference"),
                     "c2_implementation": bc.get("c2_implementation"),
                     "saturation_steps": bc.get("saturation_steps"),
                     "snapshot_retag_check": bc.get("snapshot_retag_check"),
                     "beta_leak_fixed": "beta_leak_fix" in bc,
                     "crawler_kt_factor": bc.get("crawler_kt_factor", 1.0)}
    # re-classify here so that the rule has one definition (classify_warning)
    m["bundle_c"]["warnings"] = [
        classify_warning(w.get("message", ""), w.get("category", ""), bc.get("beta_GPa"))
        for w in (bc.get("warnings") or [])]
    tm = m["times_s"]
    series = load_r8_series(Path(case["dir"]))
    if series is not None and case["pads"] is not None:
        m["guard_oscillation"] = guard_oscillation_metrics(case["pads"], series)
        m["guard_periods"] = int(np.sum(series["guard_active"]))
    if series is not None:
        v_max = float(params.get("actuator.max_speed_m_s"))
        m["c5a_command_reversals"] = command_reversal_metrics(series, v_max)
        m["c5b_guard_restarts"] = guard_restart_metrics(series)
    m["c5c_ready_settling"] = ready_settling_metrics(case, tm, m, series)
    m["check_attitude"] = check_attitude_metrics(case)
    m["relevel_predicted"] = relevel_metrics(case)
    m["reapproach"] = reapproach_metrics(case)
    t_ev = floor_event_time_s(case, tm, m)
    m["floor_event_t_s"] = t_ev
    if t_ev is not None:
        m["relevel_justification"] = relevel_justification(case, tm, m["relevel_predicted"], t_ev)
        m["lift_intervals"] = lift_interval_metrics(case, tm, params, t_ev)
    m["bundle_c"]["c11"] = bc.get("c11")
    m["diagnostic_replay"] = diagnostic_replay(case, params)
    m["ready_s"] = tm["ready"]
    return m


def _consistency_rows(m, ref: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    cid = m["case"]
    if ref is None:
        return [_row("146 consistency vs reduced (142 C)", cid, None, None, None,
                     "no reference file given", kind="consistency")]
    entry = ref.get(cid) or ref.get(m.get("scenario_key", ""))
    if entry is None:
        return [_row("146 consistency vs reduced (142 C)", cid, None, None, None,
                     "case not in the reference", kind="consistency")]
    r = entry.get("min_force_kN")
    if r is None:
        return [_row("146 consistency vs reduced (142 C)", cid, None, None, None,
                     f"not representable: {entry.get('reason') or 'no reason given'}",
                     kind="consistency")]
    out = []
    v = m.get("min_cyl_after_liftoff_kN")
    tol = max(CONSISTENCY_REL * abs(r), CONSISTENCY_ABS_N / 1e3)
    if v is None:
        note = "no Chrono value (no crawler lift-off)"
    else:
        note = "FLAG: explain the difference" if abs(v - r) > tol else "within"
    out.append(_row("146 consistency min force", cid, v, f"{r} +- {tol:.2f}", None, note,
                    kind="consistency"))
    v = m.get("t_ready_minus_touch_s")
    r = entry.get("ready_minus_touch_s")
    if r is None:
        note = "reference ready_minus_touch_s missing"
    elif v is None:
        note = "no Chrono value (no TOUCH end / READY)"
    else:
        note = f"Chrono - reduced {v - r:+.1f} s (record only, no tolerance)"
    out.append(_row("146 consistency READY - TOUCH end [s]", cid, v, r, None, note,
                    kind="consistency"))
    return out


def judge(metrics: list[dict[str, Any]], probes: dict[str, dict[str, Any]],
          consistency_ref: Mapping[str, Any] | None = None,
          leak_refs: Mapping[str, Mapping[str, float | None]] | None = None,
          reanchor_refs: Mapping[str, Mapping[str, float | None]] | None = None,
          sens_refs: Mapping[str, Mapping[str, float | None]] | None = None
          ) -> list[dict[str, Any]]:
    """Rows of the bundle (module docstring). ``leak_refs`` = :func:`load_leak_references`
    (used by the H / H2 rows only), ``reanchor_refs`` the same for the REANCHOR minimum (H2),
    ``sens_refs`` the x1 values of the K group (:data:`SENS_REFERENCE_RUN`). ``probes`` should
    have been passed through :func:`probe_truth_ringing` (C-R14) for the ringing rows."""
    rows = []
    rate = {m["case"]: m.get("record_rate_hz") or RECORD_RATE_HZ for m in metrics}
    for row in s6.judge(metrics, probes):
        row = dict(row)
        row["source"] = "s6"
        row["record_rate_hz"] = rate.get(row.get("case"), RECORD_RATE_HZ)
        rows.append(row)
    by_id = {m["case"]: m for m in metrics}
    for row in rows:
        if row["item"] == "run" and row["case"] in by_id:
            _a1_reject_run_row(row, by_id[row["case"]])
        if row["item"] == LIFT_ROW_ITEM and row["case"] in by_id:
            li = by_id[row["case"]].get("lift_intervals")
            if li is not None:
                row["note"] = f"{row.get('note') or ''}; {_lift_note(li)}".lstrip("; ")
                row["lift_intervals"] = li
    for m in metrics:
        cid = m["case"]
        fmin = float(m["F_min_N"])
        rows.extend(_check_attitude_rows(m))
        rows.extend(_relevel_rows(m))
        rows.extend(_reapproach_rows(m))
        rows.extend(_leak_rows(m, leak_refs, reanchor_refs))
        rows.extend(_sens_rows(m, sens_refs))
        rows.extend(_ringing_rows(cid, probes.get(cid)))
        if m["floor"] in D8_FLOORS and m.get("min_cyl_after_liftoff_kN") is not None:
            v = m["min_cyl_after_liftoff_kN"]
            lim = (fmin + D8_MARGIN_N) / 1e3
            rows.append(_row("D8 min true cylinder force >= F_min + 5 kN", cid, v, lim, v >= lim))
            pn = m.get("pad_N_min_after_liftoff_kN")
            if pn is not None:
                rows.append(_row("D8 no pad lift-off", cid, pn, "> 0", pn > 0.0))
            att = m.get("att_err_last5_maxabs_deg")
            if att is not None:
                rows.append(_row("D8 attitude last 5 s + mount <= 0.2 deg", cid,
                                 att + MOUNT_SHARE_DEG, ATT_TOL_DEG,
                                 att + MOUNT_SHARE_DEG <= ATT_TOL_DEG))
        if m.get("min_cyl_reanchor_kN") is not None:
            v = m["min_cyl_reanchor_kN"]
            lim = (fmin + D8_MARGIN_N + REANCHOR_EXTRA_N) / 1e3
            rows.append(_row("REANCHOR min >= F_min + 7 kN", cid, v, lim, v >= lim))
        if m["group"] == "G4" and isinstance(m.get("item6"), dict) \
                and "min_cyl_after_start_kN" in m["item6"]:
            v = m["item6"]["min_cyl_after_start_kN"]
            rows.append(_row("G4 item 6 (1) min after settlement >= F_min", cid, v,
                             fmin / 1e3, v >= fmin / 1e3))
        bc = m.get("bundle_c") or {}
        if bc.get("L0r_m") is not None:
            rows.extend(_c5_rows(m))
        if bc.get("config") == "C-1":
            dc = m.get("diagnostic_check") or {}
            counts = dc.get("counts") or {}
            n = sum(int(v) for v in counts.values())
            rows.append(_row("C-8 no false D5 / E-5 (10 Hz constants, live)", cid, n, 0,
                             n == 0 if not dc.get("injection") else None))
            rp = m.get("diagnostic_replay") or {}
            rows.append(_row("C-8 replay 1.5 s baseline (offline)", cid,
                             rp.get("longest_run_over_4kN_s"), "< 0.5 s",
                             rp.get("replay_passed"), kind="replay"))
        rows.extend(_warning_rows(m))
        rows.extend(_consistency_rows(m, consistency_ref))
        c11 = (m.get("bundle_c") or {}).get("c11")
        if c11:
            rows.append(_row("C-11 front frame stiffness override (report)", cid,
                             c11.get("front_frame_stiffness_N_m"), None, None,
                             f"role {c11.get('role')}; kn FL/FR {c11.get('kn_yaml_N_m')} -> "
                             f"{c11.get('kn_override_N_m')} N/m; controller nominal unchanged",
                             kind="report"))
    roles = {m["case"]: ((m.get("bundle_c") or {}).get("c11") or {}).get("role")
             for m in metrics}
    for row in rows:
        role = roles.get(row.get("case"))
        if role is not None:
            row["c11_role"] = role
    mark_leak_screened(rows, metrics)
    return rows


def mark_leak_screened(rows: list[dict[str, Any]], metrics: Sequence[Mapping[str, Any]]) -> None:
    """C-R15: ``leak_screened`` on every row of a :data:`LEAK_SCREENED_CASES` case whose run
    predates the C-R11 fix (``bundle_c.beta_leak_fixed`` False); values unchanged."""
    screened = {m["case"]: LEAK_SCREENED_CASES[m["case"]] for m in metrics
                if m["case"] in LEAK_SCREENED_CASES
                and not (m.get("bundle_c") or {}).get("beta_leak_fixed")}
    for row in rows:
        cls = screened.get(row.get("case"))
        if cls is not None:
            row["leak_screened"] = LEAK_SCREENED_TAG
            row["leak_screened_class"] = cls


def _a1_reject_run_row(row: dict[str, Any], m: Mapping[str, Any]) -> None:
    """C-R5: the s6 "run" row of a case that ended IDLE after an A1 ``REJ_SLOPE_D8`` is
    re-classified with the true usage (truth crawler attitude through the settle map):
    ``<= 1 + eps_u`` = false rejection (failed), above = correct rejection (``kind`` "info",
    the U-R8-15 function check of an out-of-diamond floor such as rp05)."""
    ca = m.get("check_attitude") or {}
    if m.get("final_phase") != "idle" or ca.get("code") != REJ_SLOPE_D8:
        return
    u_true, eps = ca.get("usage_truth_crawler"), ca.get("usage_tolerance")
    u_nom = ca.get("usage_floor_nominal")
    detail = (f"A1 {REJ_SLOPE_D8}: usage controller {ca.get('usage_controller'):.4f}, truth "
              f"crawler {u_true:.4f}, nominal floor "
              f"{float('nan') if u_nom is None else u_nom:.4f}"
              f", limit 1 + {eps:g}; CHECK error roll/pitch "
              f"{ca['error_deg'][0]:+.4f}/{ca['error_deg'][1]:+.4f} deg (C-R5)")
    row["value_raw"] = row["value"]
    row["value"] = {"final_phase": m.get("final_phase"), "usage_controller":
                    ca.get("usage_controller"), "usage_truth_crawler": u_true,
                    "usage_floor_nominal": ca.get("usage_floor_nominal")}
    if u_true <= 1.0 + eps:
        row["passed"] = False
        row["note"] = "false rejection (controller CHECK error): " + detail
    else:
        row["passed"] = None
        row["kind"] = "info"
        row["note"] = "correct rejection (floor outside the D8 diamond): " + detail


def _check_attitude_rows(m) -> list[dict[str, Any]]:
    """C-R5: CHECK attitude error row (every case with a CHECK decision) and an A1 usage
    report row. Judged only for an ideal IMU (a graded IMU adds its zero offset to the error;
    then ``passed`` None)."""
    ca = m.get("check_attitude")
    cid = m["case"]
    if ca is None:
        return []
    if "error_maxabs_deg" not in ca:
        return [_row("C-R5 CHECK attitude error <= 0.017 deg", cid, None, CHECK_ATT_ERR_LIMIT_DEG,
                     None, ca.get("status", ""))]
    err = ca["error_maxabs_deg"]
    ideal = m.get("grade", "ideal") == "ideal"
    passed = (err <= CHECK_ATT_ERR_LIMIT_DEG) if ideal else None
    note = (f"controller - truth roll/pitch {ca['error_deg'][0]:+.4f}/{ca['error_deg'][1]:+.4f} "
            f"deg, {ca['n_samples']} samples, window {ca['window_source']}; ASSUMPTION limit "
            "(U11 settling residual)")
    if not ideal:
        note += f"; IMU grade {m.get('grade')}: includes the sensor zero offset, not judged"
    out = [_row("C-R5 CHECK attitude error <= 0.017 deg", cid, err, CHECK_ATT_ERR_LIMIT_DEG,
                passed, note)]
    out.append(_row("C-R5 A1 floor usage (controller / truth crawler / nominal floor)", cid,
                    [ca.get("usage_controller"), ca.get("usage_truth_crawler"),
                     ca.get("usage_floor_nominal")], f"<= 1 + {ca.get('usage_tolerance')}",
                    None, f"code {ca.get('code')}", kind="report"))
    return out


def _r5_justified_row(m, base_note: str) -> dict[str, Any]:
    """Spec rev. 33 168 (C-R8): every R-5 firing of a floor-event case is after ``t_event`` and
    its leg's force falls at ``>= 20 kN/s`` (0.3 s mean). Value = the smallest rate [kN/s]."""
    cid = m["case"]
    rj = m.get("relevel_justification") or {}
    firings = rj.get("firings") or []
    limit = f"t > t_event and >= {R5_JUSTIFIED_RATE_N_S / 1e3:g} kN/s (0.3 s mean)"
    item = "R-5 justified firing (floor event)"
    if rj.get("status"):
        return _row(item, cid, None, limit, None, f"{rj['status']}; {base_note}")
    if not firings:
        return _row(item, cid, None, limit, True,
                    f"no R-5 firing; t_event {m.get('floor_event_t_s'):.2f} s")
    rates = [f.get("rate_N_s") for f in firings]
    value = None if any(r is None for r in rates) else min(rates) / 1e3
    passed = None if value is None else all(bool(f.get("justified")) for f in firings)
    detail = ", ".join(
        f"{f['leg']} +{f['t_s'] - m['floor_event_t_s']:.2f} s ({f.get('phase_before')}) "
        + ("rate n/a" if f.get("rate_N_s") is None
           else f"{f['rate_N_s'] / 1e3:.1f} kN/s, {f['F_start_kN']:.1f} -> {f['F_end_kN']:.1f} kN")
        for f in firings[:6])
    return _row(item, cid, value, limit, passed,
                f"{len(firings)} firing(s): {detail}; {base_note}; spec rev. 33 168 (C-R8)")


def _relevel_rows(m) -> list[dict[str, Any]]:
    """R-5 rows (spec rev. 33 168, C-R8): a floor-event case judges the justified firing
    (:func:`_r5_justified_row`); a no-event case of a regression group (:data:`REGRESSION_GROUPS`)
    judges ``relevel_predicted`` outside PROBE aborts = 0 (the PROBE-abort firings are listed in
    the note and never counted); other cases get a report row only when R-5 fired."""
    rv = m.get("relevel_predicted")
    if rv is None:
        return []
    cid = m["case"]
    n_other, n_probe = rv["counts"]["other"], rv["counts"]["probe_abort"]
    note = (f"{n_probe} with probe_aborted_low_load in the same period (PROBE, P-R8-11; not "
            f"counted)")
    if n_other:
        note += "; other: " + ", ".join(
            f"{e['leg']} {e['t_s']:.1f} s ({e['phase_before']})" for e in rv["other"][:5])
    if m.get("floor_event_t_s") is not None:
        return [_r5_justified_row(m, note)]
    if m.get("rerun_group") in REGRESSION_GROUPS:
        return [_row(f"{m['rerun_group']} R-5 relevel_predicted outside PROBE abort = 0 "
                     "(no floor event)", cid, n_other, 0, n_other == 0, note)]
    if n_other or n_probe:
        return [_row("R-5 relevel_predicted (report)", cid, n_other, None, None, note,
                     kind="report")]
    return []


def reapproach_metrics(case: Mapping[str, Any]) -> dict[str, Any]:
    """P-R8-12 / 13 re-approach starts (``leg_reapproach_start:<leg>``), t relative to ``t0``."""
    t0 = float(case["result"]["settings"]["start_t_s"])
    starts = [{"t_s": t - t0, "leg": n.partition(":")[2]} for t, n in s6._events(case)
              if n.split(":")[0] == REAPPROACH_EVENT]
    return {"starts": starts, "count": len(starts)}


def _reapproach_rows(m) -> list[dict[str, Any]]:
    """Spec rev. 34 177 F / FS: a no-floor-event case of a regression group judges "re-approach
    starts = 0" (1-sample watch false firing); other cases report the starts when any."""
    ra = m.get("reapproach")
    if ra is None:
        return []
    cid, n = m["case"], int(ra["count"])
    note = ", ".join(f"{e['leg']} {e['t_s']:.1f} s" for e in ra["starts"][:6])
    if m.get("floor_event_t_s") is None and m.get("rerun_group") in REGRESSION_GROUPS:
        return [_row(f"{m['rerun_group']} re-approach starts = 0 (no floor event)", cid, n, 0,
                     n == 0, note)]
    if n:
        return [_row("re-approach starts (report)", cid, n, None, None, note, kind="report")]
    return []


def load_leak_references(root: Path = PROJECT_ROOT, *,
                         key: str = "min_cyl_after_liftoff_kN",
                         runs: Sequence[tuple[str, str, str]] = LEAK_REFERENCE_RUNS
                         ) -> dict[str, dict[str, float | None]]:
    """case id -> {label: pre-fix ``key``} from ``runs`` (default :data:`LEAK_REFERENCE_RUNS`,
    the D8 minimum; a missing batch / file is skipped and listed under the key ``"_missing"``)."""
    out: dict[str, dict[str, float | None]] = {}
    missing = []
    for label, batch, name in runs:
        path = root / batch / name
        if not path.exists():
            path = root / batch / "verify_S6C.json"
        if not path.exists():
            missing.append(f"{label}: {batch}")
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        for mm in doc.get("metrics") or []:
            out.setdefault(mm["case"], {})[label] = mm.get(key)
    if missing:
        out["_missing"] = {k: None for k in missing}
    return out


def _leak_rows(m, refs: Mapping[str, Mapping[str, float | None]] | None,
               reanchor_refs: Mapping[str, Mapping[str, float | None]] | None = None
               ) -> list[dict[str, Any]]:
    """Spec rev. 34 177 H / rev. 35 185 H2: D8 minimum force after the leak fix minus the pre-fix
    value of the same case id in each run of the group (:data:`LEAK_GROUP_RUNS`); ``|diff| > 3
    kN`` = FLAG (``kind`` "leak_compare", never a failure). ``value`` = the largest-magnitude
    difference. H2 also compares the REANCHOR minimum (``reanchor_refs``)."""
    group = m.get("rerun_group")
    if group not in LEAK_GROUP_RUNS:
        return []
    labels = LEAK_GROUP_RUNS[group]
    out = [_leak_row(m, refs, labels, "min_cyl_after_liftoff_kN", "D8 min force",
                     "no post-fix value (no crawler lift-off)")]
    if group in LEAK_REANCHOR_GROUPS:
        out.append(_leak_row(m, reanchor_refs, labels, "min_cyl_reanchor_kN", "REANCHOR min",
                             "no post-fix value (no REANCHOR interval)"))
    return out


def _leak_row(m, refs, labels: Sequence[str], key: str, what: str, none_note: str
              ) -> dict[str, Any]:
    cid = m["case"]
    group = m.get("rerun_group")
    item = f"{group} beta-leak fix: {what} vs pre-fix ({' / '.join(labels)})"
    v = m.get(key)
    prior = {k: x for k, x in ((refs or {}).get(cid) or {}).items() if k in labels}
    if v is None:
        return _row(item, cid, None, None, None, none_note, kind="leak_compare")
    if not any(x is not None for x in prior.values()):
        return _row(item, cid, None, None, None,
                    "no pre-fix value of this case id" + (f" (runs: {sorted(prior)})"
                                                          if prior else ""),
                    kind="leak_compare")
    diffs = {k: v - x for k, x in prior.items() if x is not None}
    worst = max(diffs.values(), key=abs)
    flag = any(abs(d) > LEAK_FLAG_KN for d in diffs.values())
    parts = [f"{k} {prior[k]:.2f} -> {v:.2f} kN ({d:+.2f})" for k, d in diffs.items()]
    parts += [f"{k}: no value" for k, x in prior.items() if x is None]
    decide = ("; drop beyond -3 kN -> decide on the other beta cases (spec 177)"
              if group == LEAK_GROUP else "; record only (spec rev. 35 185)")
    note = ("FLAG: |diff| > 3 kN" + (decide if min(diffs.values()) < -LEAK_FLAG_KN else "")
            + "; " if flag else "within 3 kN; ") + "; ".join(parts)
    row = _row(item, cid, worst, f"+-{LEAK_FLAG_KN:g}", None, note, kind="leak_compare")
    row.update(leak_flag=flag, leak_post_kN=v, leak_pre_kN=prior, leak_diff_kN=diffs,
               leak_quantity=key)
    return row


def _sens_rows(m, sens_refs: Mapping[str, Mapping[str, float | None]] | None
               ) -> list[dict[str, Any]]:
    """Spec rev. 35 186 / U-R8-28 (report): crawler ``k_t`` x3 D8 minimum minus the x1 value of
    the base case id in :data:`SENS_REFERENCE_RUN`, with the time after the crawler lift-off."""
    if m.get("rerun_group") != SENS_GROUP:
        return []
    cid = m["case"]
    base = cid.removesuffix(SENS_SUFFIX)
    label = SENS_REFERENCE_RUN[0]
    ref = ((sens_refs or {}).get(base) or {}).get(label)
    v = m.get("min_cyl_after_liftoff_kN")
    item = "K crawler k_t x3 lift-off transient: D8 min vs x1 (report)"
    if v is None or ref is None:
        return [_row(item, cid, None, None, None,
                     f"x3 {v} kN, x1 ({label} {base}) {ref} kN: no difference", kind="report")]
    return [_row(item, cid, v - ref, None, None,
                 f"x1 ({label} {base}) {ref:.2f} -> x3 {v:.2f} kN ({v - ref:+.2f}); "
                 "record, not a gate (spec rev. 35 186)", kind="report")]


def probe_truth_ringing(case: Mapping[str, Any], pr: dict[str, Any]) -> list[dict[str, Any]]:
    """C-R14 (spec rev. 35 182 / 188.1): per 7c row of :func:`s6_control.probe_metrics` (``pr``,
    changed in place) the population standard deviation of the 1 ms true cylinder force over the
    truth window (0.5 s before the leg's first move) as ``truth_window_std_kN``; a row with
    ``std > TRUTH_RINGING_FRACTION x max(5 kN, 10 % truth)`` gets ``truth_undefined`` True and
    leaves the judged margin ``load_error_margin_kN`` (recomputed over the other non-overlap
    rows; the former value is kept as ``load_error_margin_with_ringing_kN``). Returns the
    ringing rows (judged ones only; overlap rows are already reported apart)."""
    legs = pr.get("legs") or []
    pads = case.get("pads")
    if pads is None or not legs:
        return []
    tm = s6._times(case)
    tp = np.asarray(pads["t"]) - float(tm["t0"])
    force = np.asarray(pads["F_cyl"])
    win = s6.PROBE_START_LOAD_WINDOW_S
    for r in legs:
        times, truth = r.get("probe_times_s"), r.get("truth_cyl_kN")
        if times is None or truth is None:
            continue
        sel = (tp >= times[0] - win) & (tp < times[0])
        if not sel.any():
            continue
        std = float(np.std(force[sel, LEGS.index(r["leg"])])) / 1e3
        limit = max(5.0, 0.1 * abs(truth))
        r["truth_window_std_kN"] = std
        r["truth_limit_kN"] = limit
        r["truth_undefined"] = bool(std > TRUTH_RINGING_FRACTION * limit)
    judged = [r for r in legs if r["event_class"] != s6.EventClass.OVERLAP]
    ringing = [r for r in judged if r.get("truth_undefined") and not r.get("is_skipped")]
    if ringing:
        pr["load_error_margin_with_ringing_kN"] = pr.get("load_error_margin_kN")
        kept = [r for r in judged if not r.get("truth_undefined")]
        margin = s6._load_error_margin_kN(kept)
        if margin is None:
            pr.pop("load_error_margin_kN", None)
        else:
            pr["load_error_margin_kN"] = margin
    pr["truth_ringing_rows"] = len(ringing)
    return ringing


def _ringing_rows(cid: str, pr: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """C-R14 report rows ("truth undefined (ringing)", ``kind`` "report")."""
    out = []
    for r in (pr or {}).get("legs") or []:
        if not r.get("truth_undefined") or r["event_class"] == s6.EventClass.OVERLAP \
                or r.get("is_skipped"):
            continue
        err = r["load_estimate_kN"] - r["truth_cyl_kN"]
        out.append(_row(
            "7c load estimate error: truth undefined (ringing)", cid, err,
            f"std <= {TRUTH_RINGING_FRACTION:g} x {r['truth_limit_kN']:.2f} kN", None,
            f"round {r['round']} leg {r['leg']}: estimate {r['load_estimate_kN']:.2f} kN, truth "
            f"{r['truth_cyl_kN']:.2f} kN (0.5 s mean), truth window std "
            f"{r['truth_window_std_kN']:.2f} kN > {TRUTH_RINGING_FRACTION:g} x limit "
            f"{r['truth_limit_kN']:.2f} kN (ASSUMPTION, spec rev. 35 182 / C-R14); error "
            f"{err:+.2f} kN, margin {s6._load_error_kN(r):+.2f} kN; left out of the 7c row",
            kind="report"))
    return out


def _c5_rows(m) -> list[dict[str, Any]]:
    """C-5a / C-5b / C-5c judged rows and the load-oscillation report row (154.3)."""
    cid = m["case"]
    out = []
    ra = m.get("c5a_command_reversals")
    if ra is None:
        out.append(_row("C-5a command sign reversals (4 s window)", cid, None,
                        "<= 2 pass, 3 review, >= 4 fail", None, "no r8_series"))
    else:
        n = ra.get("max_reversals")
        note = (ra.get("status") or f"leg {ra.get('leg')}, window from "
                f"{ra.get('window_start_s')} s, |u| > {ra['threshold_m_s'] * 1e3:.2f} mm/s")
        out.append(_row("C-5a command sign reversals (4 s window)", cid, n,
                        "<= 2 pass, 3 review, >= 4 fail", c5a_verdict(n),
                        note + "; ASSUMPTION thresholds (154.3)"))
    rb = m.get("c5b_guard_restarts")
    if rb is None:
        out.append(_row("C-5b guard restarts (10 s window)", cid, None, "<= 2", None,
                        "no r8_series"))
    else:
        k = rb["max_in_window"]
        out.append(_row("C-5b guard restarts (10 s window)", cid, k, "<= 2",
                        k <= C5B_PASS_MAX, f"{rb['starts']} guard start(s) in the run"))
    rc = m.get("c5c_ready_settling") or {}
    worst = rc.get("worst")
    if worst is None:
        note = rc.get("status") or "no quiet READY"
        out.append(_row("C-5c quiet READY attitude residual half range [deg]", cid, None,
                        ATT_OSC_LIMIT_DEG, None, f"{note}; {rc.get('source', '')}".rstrip("; ")))
    else:
        half, f = worst["half_range_deg"], worst["zero_cross_hz"]
        verdict = c5c_verdict(half, f)
        note = (f"{worst['channel']} in {worst['window_s']} s, zero crossings "
                f"{'n/a' if f is None else f'{f:.2f}'} Hz, "
                f"{len(rc.get('windows') or [])} quiet window(s); {rc.get('source')}")
        if half > ATT_OSC_LIMIT_DEG:
            note += ("; > 1.2 Hz: structural mode (review)" if verdict is None
                     else "; <= 1.2 Hz: control oscillation")
        out.append(_row("C-5c quiet READY attitude residual half range [deg]", cid, half,
                        ATT_OSC_LIMIT_DEG, verdict, note))
    osc = m.get("guard_oscillation")
    if osc is None:
        out.append(_row("C-5 guard load oscillation ratio (report)", cid, None, "ratio <= 0.5",
                        None, "no r8_series / pads", kind="report"))
    else:
        judged = [o for o in osc if "passed" in o]
        worst_r = max((o["ratio"] or 0.0 for o in judged), default=None)
        n_bad = sum(1 for o in judged if not o["passed"])
        out.append(_row("C-5 guard load oscillation ratio (report)", cid, worst_r,
                        "ratio <= 0.5", None,
                        f"{len(judged)} guard interval(s), {n_bad} above 0.5 (structural modes "
                        "dominate, 154.1; not judged)", kind="report"))
    return out


def _warning_rows(m) -> list[dict[str, Any]]:
    """5.24.2: expected warnings are listed but never counted; others flag an anomaly; law-C
    saturation steps are reported."""
    cid = m["case"]
    bc = m.get("bundle_c") or {}
    out = []
    warns = bc.get("warnings") or []
    unexpected = [w for w in warns if not w.get("expected")]
    n_exp = len(warns) - len(unexpected)
    out.append(_row("5.24.2 unexpected warnings", cid, len(unexpected), 0,
                    True if not unexpected else None,
                    f"{n_exp} expected (not counted)"
                    + ("" if not unexpected else "; FLAG: "
                       + " | ".join(w["message"][:160] for w in unexpected[:3])),
                    kind="anomaly"))
    sat = bc.get("saturation_steps")
    if isinstance(sat, Mapping):
        steps = sat.get("steps") or {}
        total = sum(int(v) for v in steps.values())
        worst = None
        for ep in sat.get("episodes") or []:
            ex = ep.get("static_excess_N")
            if ex is not None:
                worst = ex if worst is None else max(worst, ex)
        note = f"steps {steps}"
        if worst is not None:
            note += (f"; static end - limit max {worst:.0f} N "
                     + ("(mechanism share)" if worst <= SATURATION_MECHANISM_SHARE_N
                        else "(> 0.25 kN: look at the cause)"))
        out.append(_row("5.24.2 law-C saturation steps", cid, total, None, None, note,
                        kind="report"))
    return out


def rerun_groups(batch_dir: Path) -> dict[str, str]:
    """case id -> re-run group (spec rev. 32 160 A ... D, rev. 33 169 E ... G) from the batch's
    ``batch_meta.json`` (``run_S6C.py`` writes ``groups`` for ``--set rerun32`` / ``rerun33``);
    empty when absent."""
    path = Path(batch_dir) / "batch_meta.json"
    if not path.exists():
        return {}
    groups = json.loads(path.read_text(encoding="utf-8")).get("groups") or {}
    return {cid: str(g) for g, ids in groups.items() if g for cid in ids}


def rerun_roles(batch_dir: Path) -> dict[str, str]:
    """case id -> "gate" / "record" from ``batch_meta.json`` ``roles`` (spec rev. 34 177 H,
    ``run_S6C.py`` ``ROLE_SETS``); empty when absent."""
    path = Path(batch_dir) / "batch_meta.json"
    if not path.exists():
        return {}
    roles = json.loads(path.read_text(encoding="utf-8")).get("roles") or {}
    return {str(k): str(v) for k, v in roles.items()}


def judge_batch(batch_dir: Path, consistency_ref: Path | None = None,
                out_path: Path | None = None) -> Path:
    """Judge every case directory of a bundle-C batch; writes ``verify_S6C.json`` there (or
    ``out_path``). ``consistency_ref`` None reads :data:`CONSISTENCY_REF_PATH` when it exists."""
    if consistency_ref is None and CONSISTENCY_REF_PATH.exists():
        consistency_ref = CONSISTENCY_REF_PATH
    from outrigger_sim.params import load_params

    groups = rerun_groups(batch_dir)
    metrics, probes = [], {}
    for d in sorted(p for p in Path(batch_dir).iterdir() if (p / "result.json").exists()):
        case = s6.load_case(d)
        s = case["result"]["settings"]
        over = (s.get("bundle_c") or {}).get("param_overrides") or {}
        params = load_params(level=s["level"], overrides=over or None)
        m = bundle_c_metrics(case, params)
        m["rerun_group"] = groups.get(m["case"])
        metrics.append(m)
        pr = s6.probe_metrics(case)
        probe_truth_ringing(case, pr)
        probes[case["result"]["case"]] = pr
    ref = None
    if consistency_ref is not None:
        ref = json.loads(Path(consistency_ref).read_text(encoding="utf-8"))
    groups_present = {m.get("rerun_group") for m in metrics}
    leak_refs = (load_leak_references() if groups_present & set(LEAK_GROUP_RUNS) else None)
    reanchor_refs = (load_leak_references(key="min_cyl_reanchor_kN")
                     if groups_present & set(LEAK_REANCHOR_GROUPS) else None)
    sens_refs = (load_leak_references(runs=(SENS_REFERENCE_RUN,))
                 if SENS_GROUP in groups_present else None)
    rows = judge(metrics, probes, ref, leak_refs, reanchor_refs, sens_refs)
    roles = rerun_roles(batch_dir)
    for row in rows:
        role = roles.get(row.get("case"))
        if role is not None:
            row["rerun_role"] = role
    out = out_path or Path(batch_dir) / "verify_S6C.json"
    n_fail = sum(1 for r in rows if r["passed"] is False)
    n_fail_record = sum(1 for r in rows if r["passed"] is False and r.get("c11_role") == "record")
    n_fail_role_record = sum(1 for r in rows if r["passed"] is False
                             and r.get("rerun_role") == "record"
                             and r.get("c11_role") != "record")
    leak_flags = [r["case"] for r in rows if r.get("leak_flag")]
    doc = {"meta": {"batch": str(batch_dir), "module": __name__, "rows": len(rows),
                    "failed": n_fail, "failed_c11_record": n_fail_record,
                    "failed_rerun_record": n_fail_role_record,
                    "failed_excluding_c11_record": n_fail - n_fail_record,
                    "failed_excluding_record": n_fail - n_fail_record - n_fail_role_record,
                    "leak_compare_flags": leak_flags if leak_refs is not None else None,
                    "leak_reference_missing": None if leak_refs is None
                    else sorted((leak_refs.get("_missing") or {}).keys()),
                    "leak_screened": sorted({r["case"] for r in rows
                                             if r.get("leak_screened")}) or None,
                    "truth_undefined_7c": [
                        {"case": r["case"], "value_kN": r["value"], "note": r["note"]}
                        for r in rows if r["item"].startswith("7c load estimate error: truth "
                                                              "undefined")] or None,
                    "sensitivity_reference_missing": None if sens_refs is None
                    else sorted((sens_refs.get("_missing") or {}).keys()),
                    "consistency_ref": None if consistency_ref is None
                    else str(consistency_ref)},
           "rows": rows, "metrics": metrics}
    out.write_text(json.dumps(doc, indent=1, default=_json_default, ensure_ascii=False),
                   encoding="utf-8")
    return out


def _json_default(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return str(o)


__all__ = ["CONSISTENCY_REF_PATH", "EXPECTED_SATURATION_WARNING", "PAD_DAMPING_OVERRIDE",
           "SnapshotRetagRefused", "attitude_residual_metrics", "bundle_c_metrics",
           "c5a_verdict", "c5c_verdict", "classify_warning", "command_reversal_metrics",
           "diagnostic_replay", "floor_event_time_s", "guard_oscillation_metrics",
           "guard_restart_metrics", "judge", "judge_batch", "leg_zeta_effective",
           "lift_interval_metrics", "load_leak_references", "mark_leak_screened",
           "probe_truth_ringing",
           "quiet_ready_windows",
           "reapproach_metrics", "ready_settling_metrics",
           "relevel_justification", "relevel_metrics", "rerun_groups", "rerun_roles",
           "retag_snapshot",
           "snapshot_retag_check"]
