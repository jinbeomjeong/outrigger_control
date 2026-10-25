"""S8 V15 judge: seal friction on the L2b-NSC legs, FL up-sweep and 10 mm round trip (engine independent).

``00_docs/01_dynamics/dynamics_model.md`` rev. 39 5.26 (5.26.2 reference values, 5.26.8 ledger, 5.26.9
judged rows and tolerances); reference ``06_analysis/00_dynamics/s8_v15_reference.json / V15_rev39``
(quasi-static, key ``rod_side`` / ``head_only``) and ``s8_v15_dynamic_check.json`` (``runs``: D_f of
the time-domain check). The Chrono runner is ``04_scripts/02_chrono/run_S8V15.py`` with the recorder
``outrigger_sim.chrono.s8_v15_recorder``. Automatic pass / fail is a pre-check; the physical ruling
is dynamics-expert's.

Quantities (5.26 symbols; legs FL FR RL RR; compression +):

* ``lam`` = FL ``s_ref`` increment since the motion start [m] (``lambda`` of 5.26);
* ``F`` = true rod axial force (force-law output, ``L2bForceActuator.acting_force_N``) [N];
* ``G = F - f`` = two-sensor net reading (``acting_pressure_force_N``) [N];
* ``f`` = seal friction (+ pushes the piston outward) [N];
* ``N`` = pad normal contact force [N].

Series come as 1 ms block means; every threshold is read on a centred moving mean of
:data:`SMOOTH_S` (NSC per-step contact noise, ``dynamics_model.md`` 5.22.3), crossing points are
linearly interpolated between two smoothed samples.

Rows (5.26.9, revised by rev. 42 5.29.7 A-1..A-4, L-1..L-2; user decision U-S8-48, 2026-10-25):

* V15(a): first-leg crossings ``F <= F_min``, ``G <= F_min``, ``N <= 0`` in ``lam`` [mm]: +-5 %
  (expected <= 1 %), leg = the reference leg (RL);
* A-1 sliding, judged on the window W1 = true ``F_min`` crossing .. ``timeline.fine_start_t_s``
  (before the NSC near-zero-contact chatter), per leg: mean band-edge deficit
  ``delta_i = F_s,i - sigma_i f_i <= max(0.02 F_s,i, 50 N)``, net piston slip sign
  (FL +, FR +, RL +, RR -) and ``|Delta s_p| >= 10 um``;
* A-2 lifting-leg reading split in three: (i) true force at lift-off ``F + m g`` +-0.3 kN
  (reference ``-m g``), (ii) W1 mean ``G - (F + F_s)`` +-0.3 kN (band-edge tracking),
  (iii) at lift-off ``F - F_s <= G <= F + F_s + 0.3 kN`` (upper side = miss side);
* A-3 records only: stuck fraction and ``delta_i`` at lift-off, deficit ``F + F_s - G``, 1 ms
  rod-force high-frequency sigma over the last 0.1 mm, count of ``N_min = 0`` blocks in the last
  0.2 s (lifting leg);
* A-4 friction sign at lift-off (FL -, FR -, RL -, RR +) unchanged;
* V15(b): residual (after the return and the hold) of the true and net readings per leg:
  +-max(10 % |ref|, 0.3 kN); minimum contact force along the path > 0 (recorded value);
* D_f: +-5 % against the time-domain check (``s8_v15_dynamic_check.json``);
* speed 0.05 vs 0.1 mm/s (Chrono pair): thresholds +-1 %, residuals +-0.3 kN;
* V8(b) ledger (L-1): (1) max of the 20 ms mean of ``R`` <= 1e-3 E_ref (raw max recorded, flagged
  above 10x the limit); (4) ``R_mech = R - D_visc`` (axial dashpot and lateral bushing channels
  removed): ``|R_mech,end| <= 0.01 D_f`` (20 ms mean, raw recorded);
  ``E_ref = max(E_kin0, D_f + max(D_visc, 0) + D_cb)``; a negative ``D_visc`` is recorded as the
  "lagged dashpot - NSC noise loop" with its rate [W] (5.29.5); rule (i): F_s 0 cases recorded
  only. (L-2) both ledger rows count in :func:`summarize`.

Units SI inside, mm / kN / um only in names.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

LEGS = ("FL", "FR", "RL", "RR")
REFERENCE_FILE = Path("06_analysis") / "00_dynamics" / "s8_v15_reference.json"
DYNAMIC_CHECK_FILE = Path("06_analysis") / "00_dynamics" / "s8_v15_dynamic_check.json"
REFERENCE_BLOCK = "V15_rev39"

SMOOTH_S = 0.020
"""Centred moving mean of the 1 ms block series before any threshold (20 ms, NSC noise rule)."""
THRESHOLD_REL_TOL = 0.05
"""V15(a) thresholds +-5 % (5.26.9; expected <= 1 %)."""
RESIDUAL_REL_TOL = 0.10
RESIDUAL_ABS_TOL_N = 300.0
"""V15(b) residual +-max(10 %, 0.3 kN)."""
DF_REL_TOL = 0.05
SPEED_THRESHOLD_REL_TOL = 0.01
SPEED_RESIDUAL_TOL_N = 300.0
V8B_CREATION_REL_MAX = 1.0e-3
V8B_RAW_FLAG_FACTOR = 10.0
"""L-1: the raw ``R`` max is reported separately when above this x the (smoothed) limit."""
V8B_MECH_END_FRACTION_MAX = 0.01
"""L-1 (4): ``|R_mech,end| <= 0.01 D_f``."""
FRICTION_SIGN_AT_LIFTOFF = (-1.0, -1.0, -1.0, 1.0)
"""5.26.2: FL -L (extending), FR -L and RL -0.833 L (unloading), RR +0.833 L (loading)."""
PISTON_SLIP_SIGN = (1.0, 1.0, 1.0, -1.0)
"""A-1: expected sign of the net piston slip in W1 (the piston slides opposite to ``f``)."""
W1_DEFICIT_REL = 0.02
W1_DEFICIT_ABS_N = 50.0
"""A-1: mean band-edge deficit in W1 <= max(0.02 F_s, 50 N) (5.29.10: assumed rule, 4x the max)."""
W1_SLIP_MIN_M = 10.0e-6
"""A-1: |net piston slip in W1| >= 10 um."""
LIFTOFF_TRUE_TOL_N = 300.0
"""A-2 (i): true lifting-leg force at lift-off vs ``-m g`` +-0.3 kN."""
EDGE_TRACK_TOL_N = 300.0
"""A-2 (ii): W1 mean ``G - (F + F_s)`` +-0.3 kN."""
LIFTOFF_UPPER_MARGIN_N = 300.0
"""A-2 (iii): ``G <= F + F_s + 0.3 kN`` at lift-off (miss side)."""
HF_LAST_M = 1.0e-4
"""A-3: rod-force high-frequency sigma over the last 0.1 mm of ``lam`` before lift-off."""
NMIN_LAST_S = 0.2
"""A-3: blocks with a zero in-block minimum contact force in the last 0.2 s before lift-off."""
B_TOP_TOL_M = 1.0e-6
"""(b) the outbound leg counts as reaching +10 mm when the 1 ms block mean of ``lam`` is within
1 um of it (the stop falls inside a block: the block mean sits up to ``v * block / 2`` below)."""
DT_FINE_SPLIT_S = 5.0e-5
"""Ledger rates: blocks with ``dt < 5e-5 s`` are the 1e-5 s lift-off window."""


# --- reference -----------------------------------------------------------------------------


def level_key(fs_front_N: float) -> str:
    """``L0`` / ``L2`` / ``L4`` / ``L8`` of a front friction level [N]."""
    return f"L{int(round(fs_front_N / 1000.0))}"


def load_reference(root: Path) -> dict[str, Any]:
    return json.loads((root / REFERENCE_FILE).read_text(encoding="utf-8"))


def load_dynamic_check(root: Path) -> dict[str, Any]:
    return json.loads((root / DYNAMIC_CHECK_FILE).read_text(encoding="utf-8"))


def reference_a(ref: Mapping[str, Any], variant: str, fs_front_N: float) -> dict[str, Any]:
    return dict(ref[REFERENCE_BLOCK][variant]["a_upsweep_unilateral"][level_key(fs_front_N)])


def reference_b(ref: Mapping[str, Any], variant: str, fs_front_N: float) -> dict[str, Any]:
    return dict(ref[REFERENCE_BLOCK][variant]["b_roundtrip_10mm"][level_key(fs_front_N)])


def dynamic_df_J(dyn: Mapping[str, Any], variant: str, fs_front_N: float, kind: str,
                 speed_m_s: float = 1.0e-4, dt_s: float = 1.0e-4) -> float | None:
    """``D_f`` of the time-domain check run (``runs``) with the same variant / level / kind."""
    for r in dyn["runs"]:
        if (r["variant"] == variant and r["kind"] == kind
                and math.isclose(r["F_s_front_N"], fs_front_N, abs_tol=1e-6)
                and math.isclose(r["u_m_s"], speed_m_s, rel_tol=1e-9)
                and math.isclose(r["dt_s"], dt_s, rel_tol=1e-9)):
            led = r.get("ledger")
            return None if not isinstance(led, Mapping) else float(led["D_f_J"])
    return None


# --- series helpers ------------------------------------------------------------------------


def moving_mean(x: ArrayLike, window: int) -> NDArray[np.float64]:
    """Centred moving mean along axis 0 (window samples, shrinking at the ends)."""
    a = np.asarray(x, dtype=float)
    w = max(int(window), 1)
    if w == 1 or a.shape[0] < 2:
        return a.copy()
    flat = a.reshape(a.shape[0], -1)
    c = np.vstack([np.zeros((1, flat.shape[1])), np.cumsum(flat, axis=0)])
    n = flat.shape[0]
    lo = np.clip(np.arange(n) - w // 2, 0, n)
    hi = np.clip(np.arange(n) - w // 2 + w, 0, n)
    out = (c[hi] - c[lo]) / (hi - lo)[:, None]
    return out.reshape(a.shape)


def smooth_window(t_s: ArrayLike) -> int:
    t = np.asarray(t_s, dtype=float)
    if t.size < 2:
        return 1
    return max(1, int(round(SMOOTH_S / float(np.median(np.diff(t))))))


@dataclass(frozen=True)
class Crossing:
    """First downward crossing of ``level`` by any leg: interpolated abscissa and time."""

    x: float
    t_s: float
    leg: str
    index: int
    frac: float


def first_crossing(x: ArrayLike, t_s: ArrayLike, y: ArrayLike, level: float,
                   *, start: int = 0) -> Crossing | None:
    """First index ``k >= start`` where any column of ``y`` is ``<= level`` (and > at ``k - 1``);
    ``x`` / ``t`` linearly interpolated between ``k - 1`` and ``k``."""
    xa = np.asarray(x, dtype=float)
    ta = np.asarray(t_s, dtype=float)
    ya = np.asarray(y, dtype=float)
    if ya.ndim == 1:
        ya = ya[:, None]
    below = ya <= level
    best: Crossing | None = None
    for j in range(ya.shape[1]):
        idx = np.flatnonzero(below[start:, j])
        if idx.size == 0:
            continue
        k = int(idx[0]) + start
        if k == 0:
            frac = 0.0
            xc, tc = float(xa[0]), float(ta[0])
        else:
            y0, y1 = ya[k - 1, j], ya[k, j]
            frac = 1.0 if y1 == y0 else float((y0 - level) / (y0 - y1))
            frac = min(max(frac, 0.0), 1.0)
            xc = float(xa[k - 1] + frac * (xa[k] - xa[k - 1]))
            tc = float(ta[k - 1] + frac * (ta[k] - ta[k - 1]))
        if best is None or tc < best.t_s:
            best = Crossing(xc, tc, LEGS[j] if ya.shape[1] == 4 else str(j), k, frac)
    return best


def value_at(c: Crossing, y: ArrayLike) -> NDArray[np.float64]:
    """Row of ``y`` interpolated at the crossing (``k - 1`` .. ``k``)."""
    ya = np.asarray(y, dtype=float)
    k = c.index
    if k == 0:
        return ya[0].copy()
    return ya[k - 1] + c.frac * (ya[k] - ya[k - 1])


def _mm(c: Crossing | None) -> float | None:
    return None if c is None else 1e3 * c.x


# --- metrics ---------------------------------------------------------------------------------


def metrics_a(series: Mapping[str, Any], F_min_N: float, limits_N: Sequence[float], *,
              fine_start_t_s: float | None = None) -> dict[str, Any]:
    """V15(a) quantities of one Chrono run (series of :class:`~outrigger_sim.chrono.
    s8_v15_recorder.V15Recorder`, motion window only).

    ``fine_start_t_s`` (``timeline.fine_start_t_s``) closes the window W1 of A-1 / A-2 (ii); when
    absent W1 ends at the lift-off crossing (noted in ``W1.end_source``)."""
    t = np.asarray(series["t_s"], dtype=float)
    lam = np.asarray(series["lam_m"], dtype=float)
    lim = np.asarray(limits_N, dtype=float)
    sigma = np.asarray(FRICTION_SIGN_AT_LIFTOFF)
    w = smooth_window(t)
    F_raw = np.asarray(series["F_N"], dtype=float)
    F = moving_mean(F_raw, w)
    G = moving_mean(series["Fp_N"], w)
    N = moving_mean(series["N_N"], w)
    f = moving_mean(series["f_N"], w)
    stuck = moving_mean(series["stuck_frac"], w)
    c_true = first_crossing(lam, t, F, F_min_N)
    c_net = first_crossing(lam, t, G, F_min_N)
    c_lift = first_crossing(lam, t, N, 0.0)
    out: dict[str, Any] = {
        "smooth_window_samples": w,
        "F_min_N": float(F_min_N),
        "F_min_true": None if c_true is None else {"mm": _mm(c_true), "leg": c_true.leg,
                                                   "t_s": c_true.t_s},
        "F_min_net_reading": None if c_net is None else {"mm": _mm(c_net), "leg": c_net.leg,
                                                         "t_s": c_net.t_s},
        "liftoff": None if c_lift is None else {"mm": _mm(c_lift), "leg": c_lift.leg,
                                                "t_s": c_lift.t_s},
        "lam_end_mm": float(1e3 * lam[-1]) if lam.size else None,
    }
    if c_lift is None:
        return out
    li = LEGS.index(c_lift.leg)
    F_l, G_l, f_l = value_at(c_lift, F), value_at(c_lift, G), value_at(c_lift, f)
    out["at_liftoff"] = {
        "true_N": F_l.tolist(),
        "net_N": G_l.tolist(),
        "f_N": f_l.tolist(),
        "N_N": value_at(c_lift, N).tolist(),
        # A-3 records (smoothed values at the interpolated crossing)
        "stuck_fraction": value_at(c_lift, stuck).tolist(),
        "edge_deficit_N": (lim - sigma * f_l).tolist(),
        "lifting_leg": c_lift.leg,
        "lifting_leg_deficit_vs_upper_N (F + F_s - G)": float(F_l[li] + lim[li] - G_l[li]),
    }
    # A-3: last 0.1 mm of lam (1 ms rod-force high-frequency part) and the last 0.2 s N_min
    hf = F_raw - F
    sel = (lam >= c_lift.x - HF_LAST_M) & (lam < c_lift.x)
    out["last_0p1mm"] = {"n_blocks": int(sel.sum()),
                         "hf_rod_force_std_1ms_N": (np.std(hf[sel], axis=0).tolist()
                                                    if np.any(sel) else None)}
    if "N_min_N" in series:
        t_k = float(t[c_lift.index])
        sel = (t > t_k - NMIN_LAST_S) & (t <= t_k)
        nmin = np.asarray(series["N_min_N"], dtype=float)[sel, li]
        out["last_0p2s"] = {"leg": c_lift.leg, "n_blocks": int(sel.sum()),
                            "n_blocks_N_min_zero": int(np.sum(nmin <= 0.0))}
    if c_true is not None:
        out["W1"] = metrics_w1(series, lim, t_from_s=c_true.t_s,
                               t_to_s=fine_start_t_s if fine_start_t_s is not None else c_lift.t_s)
        out["W1"]["end_source"] = ("timeline.fine_start_t_s" if fine_start_t_s is not None
                                   else "lift-off crossing (no fine window)")
    return out


def metrics_w1(series: Mapping[str, Any], limits_N: ArrayLike, *, t_from_s: float, t_to_s: float
               ) -> dict[str, Any]:
    """A-1 / A-2 (ii) quantities on the raw 1 ms blocks with ``t_from_s <= t < t_to_s``:
    band-edge deficit ``delta_i = F_s,i - sigma_i f_i`` (mean, max), net piston slip
    ``s_p(end) - s_p(start)``, mean ``G - (F - sigma_i F_s,i)`` (= ``G - (F + F_s)`` on the
    unloading legs FL FR RL), mean stuck fraction (record)."""
    t = np.asarray(series["t_s"], dtype=float)
    m = (t >= t_from_s) & (t < t_to_s)
    lim = np.asarray(limits_N, dtype=float)
    sigma = np.asarray(FRICTION_SIGN_AT_LIFTOFF)
    out: dict[str, Any] = {"t_s": [float(t_from_s), float(t_to_s)], "n_blocks": int(m.sum())}
    if m.sum() < 2:
        return out
    lam = np.asarray(series["lam_m"], dtype=float)[m]
    f = np.asarray(series["f_N"], dtype=float)[m]
    F = np.asarray(series["F_N"], dtype=float)[m]
    G = np.asarray(series["Fp_N"], dtype=float)[m]
    dfc = lim - sigma * f
    out.update({
        "lam_mm": [float(1e3 * lam[0]), float(1e3 * lam[-1])],
        "edge_deficit_mean_N": dfc.mean(axis=0).tolist(),
        "edge_deficit_max_1ms_N": dfc.max(axis=0).tolist(),
        "edge_track_mean_N (G - (F - sigma F_s))": (G - (F - sigma * lim)).mean(axis=0).tolist(),
        "stuck_fraction_mean": np.asarray(series["stuck_frac"], dtype=float)[m].mean(axis=0).tolist(),
    })
    if "s_p_m" in series:
        sp = np.asarray(series["s_p_m"], dtype=float)[m]
        out["piston_slip_um"] = (1e6 * (sp[-1] - sp[0])).tolist()
    return out


def _window_mean(t: NDArray[np.float64], y: NDArray[np.float64], t0: float, t1: float
                 ) -> NDArray[np.float64]:
    m = (t >= t0) & (t <= t1)
    if not np.any(m):
        raise ValueError(f"no samples in [{t0}, {t1}] s")
    return y[m].mean(axis=0)


def metrics_b(series: Mapping[str, Any], F_min_N: float, *, t_start_s: float, t_end_s: float,
              mean_s: float = 1.0) -> dict[str, Any]:
    """V15(b): residual = mean of the last ``mean_s`` before ``t_end_s`` minus the mean of the
    ``mean_s`` before the motion start ``t_start_s`` (true ``F``, net ``G``, head-only reading
    when ``head_reading_N`` is present); minimum contact force along the path (smoothed)."""
    t = np.asarray(series["t_s"], dtype=float)
    lam = np.asarray(series["lam_m"], dtype=float)
    out: dict[str, Any] = {"mean_s": mean_s, "t_start_s": t_start_s, "t_end_s": t_end_s}
    for key, name in (("F_N", "residual_true_N"), ("Fp_N", "residual_net_N"),
                      ("head_reading_N", "residual_head_N"), ("f_N", "friction_change_N")):
        if key not in series:
            continue
        y = np.asarray(series[key], dtype=float)
        before = _window_mean(t, y, t_start_s - mean_s, t_start_s)
        after = _window_mean(t, y, t_end_s - mean_s, t_end_s)
        out[name] = (after - before).tolist()
    w = smooth_window(t)
    m = t >= t_start_s
    N = moving_mean(np.asarray(series["N_N"], dtype=float)[m], w)
    out["min_contact_force_N"] = float(N.min())
    out["min_contact_leg"] = LEGS[int(np.argmin(N.min(axis=0)))]
    F = moving_mean(np.asarray(series["F_N"], dtype=float)[m], w)
    c = first_crossing(lam[m], t[m], F, F_min_N)
    out["F_min_true_on_the_way"] = None if c is None else {"mm": _mm(c), "leg": c.leg}
    out["lam_max_mm"] = float(1e3 * lam[m].max())
    out["lam_end_mm"] = float(1e3 * lam[m][-1])
    return out


def round_trip_complete(mb: Mapping[str, Any], target_m: float) -> bool:
    """(b) residual rows are judged when the 1 ms block mean of ``lam`` reached the target within
    :data:`B_TOP_TOL_M` and came back to 0 (same tolerance)."""
    return bool(mb["lam_max_mm"] >= 1e3 * (target_m - B_TOP_TOL_M)
                and abs(mb["lam_end_mm"]) <= 1e3 * B_TOP_TOL_M)


# --- checks ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Check:
    row: str
    name: str
    value: Any
    reference: Any
    tolerance: Any
    passed: bool | None
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _rel_check(row: str, name: str, value: float | None, ref: float | None, tol: float,
               note: str = "") -> Check:
    if value is None or ref is None:
        return Check(row, name, value, ref, f"+-{tol:.0%}", (value is None) == (ref is None),
                     note or "both absent = pass")
    rel = (value - ref) / ref
    return Check(row, name, value, ref, f"+-{tol:.0%}", bool(abs(rel) <= tol),
                 note or f"rel {rel:+.4%}")


def judge_a(m: Mapping[str, Any], ref_a: Mapping[str, Any],
            limits_N: Sequence[float] | None = None) -> list[Check]:
    """V15(a) rows of one run against ``a_upsweep_unilateral / L*`` (``limits_N`` = Coulomb
    limits ``F_s,i`` of the run, FL FR RL RR; default from the reference ``F_s_front_rear_N``)."""
    if limits_N is None:
        fr = ref_a.get("F_s_front_rear_N", [0.0, 0.0])
        limits_N = [float(fr[0]), float(fr[0]), float(fr[1]), float(fr[1])]
    out: list[Check] = []
    for key, label in (("F_min_true", "true F_min threshold [mm]"),
                       ("F_min_net_reading", "net reading F_min threshold [mm]"),
                       ("liftoff", "lift-off threshold [mm]")):
        got = m.get(key)
        exp = ref_a.get(key)
        out.append(_rel_check("V15(a)", label, None if got is None else got["mm"],
                              None if exp is None else exp["mm"], THRESHOLD_REL_TOL))
        if got is not None and exp is not None:
            out.append(Check("V15(a)", f"{label}: leg", got["leg"], exp["leg"], "equal",
                             got["leg"] == exp["leg"]))
    at = m.get("at_liftoff")
    exp_at = ref_a.get("at_liftoff")
    if at is None or exp_at is None:
        return out
    leg = exp_at["lifting_leg"]
    i = LEGS.index(leg)
    lim = np.asarray(limits_N, dtype=float)
    exp_f = np.asarray(exp_at["all_legs_f_N"], dtype=float)
    with_friction = bool(np.any(exp_f != 0.0) and np.any(lim > 0.0))
    # A-2 (i): true force at lift-off vs -m g
    got_F = float(at["true_N"][i])
    exp_F = float(exp_at["true_cyl_force_N (= -m_rod g)"])
    out.append(Check("V15(a) A-2(i)", f"{leg} true force at lift-off F + m g [N]",
                     got_F - exp_F, 0.0, f"+-{LIFTOFF_TRUE_TOL_N:.0f} N",
                     bool(abs(got_F - exp_F) <= LIFTOFF_TRUE_TOL_N),
                     f"F {got_F:.1f} N, -m g {exp_F:.1f} N"))
    if with_friction:
        # A-2 (ii): W1 band-edge tracking of the lifting leg
        w1 = m.get("W1", {})
        track = w1.get("edge_track_mean_N (G - (F - sigma F_s))")
        out.append(Check("V15(a) A-2(ii)", f"{leg} W1 mean G - (F + F_s) [N]",
                         None if track is None else float(track[i]), 0.0,
                         f"+-{EDGE_TRACK_TOL_N:.0f} N",
                         bool(track is not None and abs(track[i]) <= EDGE_TRACK_TOL_N),
                         f"W1 {w1.get('t_s')} s, {w1.get('n_blocks')} blocks"))
        # A-2 (iii): at lift-off F - F_s <= G <= F + F_s + 0.3 kN
        g = float(at["net_N"][i])
        lo, hi = got_F - lim[i], got_F + lim[i] + LIFTOFF_UPPER_MARGIN_N
        out.append(Check("V15(a) A-2(iii)", f"{leg} net reading at lift-off in the band [N]", g,
                         [lo, hi], f"F - F_s <= G <= F + F_s + {LIFTOFF_UPPER_MARGIN_N:.0f} N",
                         bool(lo <= g <= hi),
                         f"deficit F + F_s - G {got_F + lim[i] - g:+.1f} N "
                         f"(reference G {float(exp_at['net_reading_N (G = F - f)']):.1f} N)"))
        # A-4: friction sign at lift-off (unchanged)
        signs = [float(np.sign(v)) for v in at["f_N"]]
        out.append(Check("V15(a)", "friction sign at lift-off (FL FR RL RR)", signs,
                         list(FRICTION_SIGN_AT_LIFTOFF), "equal",
                         signs == list(FRICTION_SIGN_AT_LIFTOFF)))
        out += judge_w1_sliding(m.get("W1", {}), lim)
    # A-3 records
    out.append(Check("V15(a) A-3 record", "stuck fraction at lift-off (FL FR RL RR)",
                     at.get("stuck_fraction"), None, "record", None))
    out.append(Check("V15(a) A-3 record", "band-edge deficit at lift-off (FL FR RL RR) [N]",
                     at.get("edge_deficit_N"), None, "record", None))
    out.append(Check("V15(a) A-3 record", f"{leg} deficit F + F_s - G at lift-off [N]",
                     float(at["true_N"][i] + lim[i] - at["net_N"][i]), None, "record", None,
                     "5.29.2: NSC contact-chatter ratchet, about 0.45 kN expected"))
    hf = m.get("last_0p1mm", {})
    out.append(Check("V15(a) A-3 record", "1 ms rod-force HF sigma, last 0.1 mm (FL FR RL RR) [N]",
                     hf.get("hf_rod_force_std_1ms_N"), None, "record", None,
                     f"{hf.get('n_blocks')} blocks"))
    nz = m.get("last_0p2s")
    if nz is not None:
        out.append(Check("V15(a) A-3 record", f"{nz['leg']} blocks with N_min = 0, last 0.2 s",
                         nz["n_blocks_N_min_zero"], nz["n_blocks"], "record", None))
    return out


def judge_w1_sliding(w1: Mapping[str, Any], limits_N: ArrayLike) -> list[Check]:
    """A-1: per leg, W1 mean deficit <= max(0.02 F_s, 50 N), net piston slip sign
    (FL +, FR +, RL +, RR -) and ``|slip| >= 10 um``."""
    lim = np.asarray(limits_N, dtype=float)
    dfc = w1.get("edge_deficit_mean_N")
    slip = w1.get("piston_slip_um")
    out: list[Check] = []
    for i, leg in enumerate(LEGS):
        tol = max(W1_DEFICIT_REL * lim[i], W1_DEFICIT_ABS_N)
        if dfc is None or slip is None:
            out.append(Check("V15(a) A-1", f"{leg} sliding in W1", None, None, "", False,
                             "W1 empty or no piston record"))
            continue
        d, s = float(dfc[i]), float(slip[i])
        ok_d = d <= tol
        ok_sign = float(np.sign(s)) == PISTON_SLIP_SIGN[i]
        ok_len = abs(s) >= 1e6 * W1_SLIP_MIN_M
        out.append(Check("V15(a) A-1", f"{leg} sliding in W1",
                         {"deficit_mean_N": d, "piston_slip_um": s},
                         {"deficit_max_N": tol, "slip_sign": PISTON_SLIP_SIGN[i],
                          "slip_min_um": 1e6 * W1_SLIP_MIN_M},
                         "deficit <= max(0.02 F_s, 50 N), sign, |slip| >= 10 um",
                         bool(ok_d and ok_sign and ok_len),
                         f"deficit {'ok' if ok_d else 'FAIL'}, sign {'ok' if ok_sign else 'FAIL'}, "
                         f"length {'ok' if ok_len else 'FAIL'}"))
    return out


def judge_b(m: Mapping[str, Any], ref_b: Mapping[str, Any]) -> list[Check]:
    out: list[Check] = []
    for key, ref_key in (("residual_true_N", "residual_true_load_change_after_return_N"),
                         ("residual_net_N", "residual_net_reading_change_after_return_N"),
                         ("residual_head_N", "residual_head_reading_change_after_return_N")):
        if key not in m or ref_key not in ref_b:
            continue
        for i, leg in enumerate(LEGS):
            got = float(m[key][i])
            exp = float(ref_b[ref_key][i])
            tol = max(RESIDUAL_REL_TOL * abs(exp), RESIDUAL_ABS_TOL_N)
            row = "V15(b)" if key != "residual_head_N" else "V15(b) record"
            out.append(Check(row, f"{key} {leg} [N]", got, exp, f"+-{tol:.0f} N",
                             bool(abs(got - exp) <= tol) if key != "residual_head_N" else None,
                             f"diff {got - exp:+.1f} N"))
    out.append(Check("V15(b)", "min contact force along the path [N] (> 0, no lift-off)",
                     m["min_contact_force_N"], ref_b.get("min_contact_force_along_path_N"),
                     "> 0", bool(m["min_contact_force_N"] > 0.0),
                     f"leg {m['min_contact_leg']} (reference value recorded only)"))
    return out


def judge_df(df_J: float, ref_df_J: float | None, label: str) -> Check:
    if ref_df_J is None or ref_df_J == 0.0:
        return Check("V15 D_f", label, df_J, ref_df_J, "record (no reference / F_s 0)", None)
    return _rel_check("V15 D_f", label, df_J, ref_df_J, DF_REL_TOL)


def judge_speed_a(fast: Mapping[str, Any], slow: Mapping[str, Any]) -> list[Check]:
    out: list[Check] = []
    for key in ("F_min_true", "F_min_net_reading", "liftoff"):
        a, b = fast.get(key), slow.get(key)
        out.append(_rel_check("V15 speed", f"{key} 0.05 vs 0.1 mm/s [mm]",
                              None if b is None else b["mm"], None if a is None else a["mm"],
                              SPEED_THRESHOLD_REL_TOL))
    return out


def judge_speed_b(fast: Mapping[str, Any], slow: Mapping[str, Any]) -> list[Check]:
    out: list[Check] = []
    for key in ("residual_true_N", "residual_net_N"):
        for i, leg in enumerate(LEGS):
            d = float(slow[key][i]) - float(fast[key][i])
            out.append(Check("V15 speed", f"{key} {leg} 0.05 - 0.1 mm/s [N]", d, 0.0,
                             "+-300 N", bool(abs(d) <= SPEED_RESIDUAL_TOL_N)))
    return out


# --- V8(b) ledger (5.26.8) ------------------------------------------------------------------


def oil_energy_moving_J(k2_N_m: float, c_m: float) -> float:
    """``1/2 k_2(s_ref) c^2`` (moving / head-only leg; the release residual is booked as work)."""
    return 0.5 * k2_N_m * c_m * c_m


def oil_energy_locked_J(*, k1_N_m: float, k2_N_m: float, knee_c_m: float, c_lock_m: float,
                        F_lock_N: float, c_m: float) -> float:
    """``U(c_lock) + int_{c_lock}^{c} G``, ``G = F_lock + k_2 dc + (k_1 - k_2) min(dc, dc_knee)``,
    ``U(c_lock) = 1/2 k_2 c_lock^2`` (= the moving value at the lock instant: no jump on locking)."""
    dc = c_m - c_lock_m
    u = 0.5 * k2_N_m * c_lock_m * c_lock_m + F_lock_N * dc + 0.5 * k2_N_m * dc * dc
    if dc < knee_c_m:
        u += 0.5 * (k1_N_m - k2_N_m) * dc * dc
    else:
        u += (k1_N_m - k2_N_m) * (knee_c_m * dc - 0.5 * knee_c_m * knee_c_m)
    return u


def ledger_residual(columns: Mapping[str, ArrayLike]) -> NDArray[np.float64]:
    """``R = dE + D_visc + D_f + D_cb - W_m - W_L - W_res - W_switch`` from cumulative columns
    (row 0 = ledger start). ``E`` = kinetic + gravity + lateral springs + axial (``U_out + U_oil``);
    ``W_res`` = work of the rod-side release residual, ``W_switch`` = law-switch energy jumps
    (locked -> moving), both bookkeeping of the L2b law (recorded separately)."""
    c = {k: np.asarray(v, dtype=float) for k, v in columns.items()}
    e = c["E_kin_J"] + c["E_grav_J"] + c["U_lat_J"] + c["U_ax_J"]
    r = (e - e[0]) + (c["D_visc_J"] - c["D_visc_J"][0]) + (c["D_f_J"] - c["D_f_J"][0])
    if "D_cb_J" in c:
        r = r + c["D_cb_J"] - c["D_cb_J"][0]
    for k in ("W_m_J", "W_L_J", "W_res_J", "W_switch_J"):
        if k in c:
            r = r - (c[k] - c[k][0])
    return r


def _rate_W(t: NDArray[np.float64], y: NDArray[np.float64], sel: NDArray[np.bool_]
            ) -> tuple[float | None, float]:
    """Mean rate of the cumulative ``y`` over the block increments flagged by ``sel`` (the
    increment of block ``k`` is ``y[k] - y[k-1]`` over ``t[k] - t[k-1]``): (rate [W], time [s])."""
    if t.size < 2:
        return None, 0.0
    dy = np.diff(y)
    dt = np.diff(t)
    s = sel[1:]
    span = float(dt[s].sum())
    return (float(dy[s].sum() / span) if span > 0 else None), span


def ledger_summary(t_s: ArrayLike, columns: Mapping[str, ArrayLike], *, judged: bool,
                   dt_s: ArrayLike | None = None) -> dict[str, Any]:
    """V8(b) ledger, L-1 rule (``dynamics_model.md`` 5.29.5 / 5.29.7).

    * ``R`` (:func:`ledger_residual`) raw and as its :data:`SMOOTH_S` centred mean (the axial
      spring energy carries the NSC per-step force noise); (1) on the smoothed max, raw recorded
      and flagged above :data:`V8B_RAW_FLAG_FACTOR` x the limit;
    * ``R_mech = R - D_visc`` (both dashpot channels removed: the explicit one-step-lag dashpot
      does work on the NSC per-step noise that the NSC contact absorbs outside the ledger);
      (4) ``|R_mech,end| <= 0.01 D_f`` on the smoothed end value, raw recorded;
    * ``E_ref = max(E_kin0, D_f + max(D_visc, 0) + D_cb)``;
    * ``D_visc`` split ``D_visc_ax_J`` / ``D_visc_lat_J`` when the recorder wrote them, and its
      rate [W] over the whole ledger and per dt regime (``dt_s`` per block, 1e-5 s window =
      ``dt < 5e-5 s``)."""
    t = np.asarray(t_s, dtype=float)
    w = smooth_window(t)
    r = ledger_residual(columns)
    rs = moving_mean(r, w)
    col = {k: np.asarray(v, dtype=float) for k, v in columns.items()}
    change = {k: float(v[-1] - v[0]) for k, v in col.items()}
    d_visc_c = col["D_visc_J"] - col["D_visc_J"][0]
    d_visc = float(d_visc_c[-1])
    d_f = change["D_f_J"]
    d_cb = change.get("D_cb_J", 0.0)
    d_total = d_visc + d_f + d_cb
    e_ref = max(float(col["E_kin_J"][0]), d_f + max(d_visc, 0.0) + d_cb)
    r_mech = r - d_visc_c
    rms = moving_mean(r_mech, w)
    out: dict[str, Any] = {
        "rule": "L-1 (dynamics_model.md 5.29.7)",
        "change_J": change, "dissipation_J": d_total, "D_f_J": d_f, "D_visc_J": d_visc,
        "D_cb_J": d_cb, "E_ref_J": e_ref,
        "R_end_J": float(r[-1]), "R_max_J": float(r.max()), "R_min_J": float(r.min()),
        "R_smooth_end_J": float(rs[-1]), "R_smooth_max_J": float(rs.max()),
        "creation_rel_raw": float(r.max() / e_ref) if e_ref > 0 else math.nan,
        "creation_rel_smooth": float(rs.max() / e_ref) if e_ref > 0 else math.nan,
        "R_mech_end_J": float(r_mech[-1]), "R_mech_max_J": float(r_mech.max()),
        "R_mech_min_J": float(r_mech.min()), "R_mech_smooth_end_J": float(rms[-1]),
        "R_mech_end_over_D_f": float(abs(rms[-1]) / d_f) if d_f > 0 else math.nan,
        "R_mech_end_over_D_f_raw": float(abs(r_mech[-1]) / d_f) if d_f > 0 else math.nan,
        "judged": judged,
    }
    out["creation_raw_flag"] = bool(e_ref > 0
                                    and out["creation_rel_raw"]
                                    > V8B_RAW_FLAG_FACTOR * V8B_CREATION_REL_MAX)
    visc: dict[str, Any] = {"D_visc_J": d_visc}
    for k in ("D_visc_ax_J", "D_visc_lat_J"):
        visc[k] = change.get(k)
    if visc["D_visc_ax_J"] is None:
        visc["split_note"] = "record has no axial / lateral split (recorder before L-1)"
    rate, span = _rate_W(t, d_visc_c, np.ones(t.shape, dtype=bool))
    visc["rate_W"] = rate
    if dt_s is not None:
        dts = np.asarray(dt_s, dtype=float)
        for name, sel in (("coarse", dts >= DT_FINE_SPLIT_S), ("fine_1e-5", dts < DT_FINE_SPLIT_S)):
            rr, sp = _rate_W(t, d_visc_c, sel)
            visc[f"rate_{name}_W"] = rr
            visc[f"time_{name}_s"] = sp
    if d_visc < 0.0:
        visc["note"] = ("negative D_visc: lagged dashpot - NSC noise loop (5.29.5); excluded from "
                        "E_ref, removed in R_mech")
    out["D_visc"] = visc
    if judged:
        out["check_1"] = bool(out["creation_rel_smooth"] <= V8B_CREATION_REL_MAX)
        out["check_4"] = bool(d_f > 0 and out["R_mech_end_over_D_f"] <= V8B_MECH_END_FRACTION_MAX)
    return out


def judge_ledger(led: Mapping[str, Any]) -> list[Check]:
    """L-2: the ledger rows (1) and (4) as checks (``passed`` None = recorded, F_s 0 rule (i))."""
    judged = bool(led.get("judged"))
    note1 = (f"raw max R {led['R_max_J']:+.4g} J (rel {led['creation_rel_raw']:.3g})"
             + (" ABOVE 10x the limit" if led.get("creation_raw_flag") else ""))
    return [
        Check("V8(b) (1)", "creation: max 20 ms mean R / E_ref", led["creation_rel_smooth"],
              V8B_CREATION_REL_MAX, f"<= {V8B_CREATION_REL_MAX:g}",
              bool(led["check_1"]) if judged else None,
              note1 + ("" if judged else "; F_s 0: recorded only")),
        Check("V8(b) (4)", "end: |R_mech,end| / D_f (R_mech = R - D_visc)",
              led["R_mech_end_over_D_f"], V8B_MECH_END_FRACTION_MAX,
              f"<= {V8B_MECH_END_FRACTION_MAX:g}", bool(led["check_4"]) if judged else None,
              f"R_mech end {led['R_mech_smooth_end_J']:+.4g} J (raw {led['R_mech_end_J']:+.4g} J), "
              f"D_f {led['D_f_J']:.4g} J, D_visc {led['D_visc_J']:+.4g} J"
              + ("" if judged else "; F_s 0: recorded only")),
    ]


def summarize(checks: Sequence[Check]) -> dict[str, Any]:
    judged = [c for c in checks if c.passed is not None]
    return {"n_checks": len(judged), "n_failed": sum(1 for c in judged if not c.passed),
            "failed": [c.as_dict() for c in judged if not c.passed]}


__all__ = [
    "Check", "Crossing", "LEGS", "SMOOTH_S", "first_crossing", "judge_a", "judge_b", "judge_df",
    "judge_ledger", "judge_speed_a", "judge_speed_b", "judge_w1_sliding", "ledger_residual",
    "ledger_summary", "level_key", "load_dynamic_check", "load_reference", "metrics_a",
    "metrics_b", "metrics_w1", "moving_mean", "round_trip_complete",
    "oil_energy_locked_J", "oil_energy_moving_J", "reference_a", "reference_b", "summarize",
    "value_at", "dynamic_df_J",
]
