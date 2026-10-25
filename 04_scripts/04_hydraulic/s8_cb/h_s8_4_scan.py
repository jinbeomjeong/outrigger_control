"""H-S8-4: locked lift-off rod/head collapse in the ML main batch -- release-event scan.

Hypothesis (checked here, read-only, no Chrono):
  * the plant valve is a first-order lag (tau_v) on the issued command, which enters at the
    10 Hz boundary t_b; a locked leg is released when |u_valve| first exceeds the numerical lock
    threshold eps = 1e-6 m/s, i.e. at t_b + t_x with t_x = -tau_v ln(1 - eps / |u_new|);
  * at that release the rod-side law (L2bRodSide) switches its rod pressure from the locked law
    value to the state machine's tracked pressure, which was last written at the lock instant
    (the machine is skipped while locked) -> the rod reading steps to ~p_r0 of that lock and
    the head reading follows through the force identity / S8-A1 floor.

Per episode: reconstruct u_valve(t) from r8_series (valve_u, issued_u, tau_v), list lock and
release instants, measure the rod-pressure step at each release, and re-detect the locked
lift-offs with a > 50 bar rod drop within 10 ms.

Usage: h_s8_4_scan.py <batch_dir> <out.json>
"""

import json
import math
import sys
from pathlib import Path

import numpy as np

BAR = 1.0e5
LEGS = ("FL", "FR", "RL", "RR")


def load_meta(ep: Path) -> dict:
    return json.loads((ep / "record" / "meta.json").read_text(encoding="utf-8"))


def find_key(obj, key):
    """Depth-first search of a nested dict for ``key``."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, key)
            if r is not None:
                return r
    return None


def valve_events(t10, valve, issued, tau, eps, t_end):
    """Lock / release instants of one leg from the exact exponential valve between rows.

    Between rows k and k+1 the valve relaxes from valve[k] towards issued[k]."""
    events = []  # (time, kind, u_target, row_time)
    locked = abs(valve[0]) <= eps
    for k in range(len(t10)):
        t0 = t10[k]
        t1 = t10[k + 1] if k + 1 < len(t10) else t_end
        u0 = valve[k]
        ut = issued[k]
        # check the start of the row (the record value) first
        if locked and abs(u0) > eps:
            events.append((t0, "release", ut, t0))
            locked = False
        elif not locked and abs(u0) <= eps:
            events.append((t0, "lock", ut, t0))
            locked = True
        # crossing inside (u monotone between u0 and ut)
        if locked and abs(ut) > eps:
            # |ut + (u0 - ut) e^{-x/tau}| = eps, same sign as ut
            # e^{-x/tau} = (|ut| - eps) / |ut - u0|  (u0 inside the band, so the signs agree)
            frac = (abs(ut) - eps) / abs(ut - u0)
            if 0.0 < frac < 1.0:
                x = -tau * math.log(frac)
                if t0 + x < t1:
                    events.append((t0 + x, "release", ut, t0))
                    locked = False
        elif not locked and abs(ut) <= eps:
            # relaxing into the band
            if abs(u0) > eps:
                if abs(ut - u0) > 0:
                    sgn = math.copysign(1.0, u0)
                    target_edge = sgn * eps
                    frac = (target_edge - ut) / (u0 - ut)
                    if 0.0 < frac < 1.0:
                        x = -tau * math.log(frac)
                        if t0 + x < t1:
                            events.append((t0 + x, "lock", ut, t0))
                            locked = True
    return events


def main() -> None:
    batch = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    eps_dir = sorted(p for p in (batch / "episodes").iterdir() if p.is_dir())
    releases = []
    liftoffs = []
    valve_check = []
    for ep in eps_dir:
        if not (ep / "pads.npz").exists() or not (ep / "r8_series.npz").exists():
            continue
        meta = load_meta(ep)
        tau = float(find_key(meta, "tau_v_s"))
        eps = float(find_key(meta, "lock_eps_m_s"))
        pr0_ext = find_key(meta, "p_r0_after_extend_Pa")
        pr0_ret = find_key(meta, "p_r0_after_retract_Pa")
        z = np.load(ep / "pads.npz", allow_pickle=True)
        r8 = np.load(ep / "r8_series.npz", allow_pickle=True)
        t = z["t"]
        rod = z["rod_pressure"] / BAR
        head = z["head_pressure"] / BAR
        air = z["airborne"]
        n_air = z["N"]
        s_link = z["s_link"]
        t10 = r8["t"]
        valve = r8["valve_u"]
        issued = r8["issued_u"]
        # valve reconstruction check: row k -> k+1
        for leg in range(4):
            pred = issued[:-1, leg] + (valve[:-1, leg] - issued[:-1, leg]) * np.exp(
                -np.diff(t10) / tau)
            err = np.abs(pred - valve[1:, leg])
            big = np.abs(valve[1:, leg]) > 1e-5
            if np.any(big):
                valve_check.append(float(np.max(err[big] / np.abs(valve[1:, leg][big]))))
        t_end = float(t[-1])
        for leg in range(4):
            ev = valve_events(t10, valve[:, leg], issued[:, leg], tau, eps, t_end)
            last_lock_t = None
            for (te, kind, ut, tb) in ev:
                if kind == "lock":
                    last_lock_t = te
                    continue
                if te < t[0] + 0.01 or te > t[-1] - 0.02:
                    last_lock_t = None
                    continue
                i_before = int(np.searchsorted(t, te, side="right")) - 1  # last ms <= te
                # first record sample at least one full ms after the release (the 1 ms grid is
                # time-sampled at hook ends, so the next sample can still precede the release step)
                i_after = i_before + 2
                if i_before < 1 or i_after + 3 >= t.size:
                    continue
                rec = {
                    "case": ep.name, "leg": LEGS[leg], "t_release_s": te,
                    "t_boundary_s": tb, "t_x_ms": (te - tb) * 1e3, "u_new_m_s": ut,
                    "rod_before_bar": float(rod[i_before, leg]),
                    "rod_after_bar": float(rod[i_after, leg]),
                    "head_before_bar": float(head[i_before, leg]),
                    "head_after_bar": float(head[i_after, leg]),
                    "airborne_before": bool(air[i_before, leg]),
                    "N_before_kN": float(n_air[i_before, leg] / 1e3),
                }
                rec["rod_jump_bar"] = rec["rod_after_bar"] - rec["rod_before_bar"]
                if last_lock_t is not None:
                    j = int(np.searchsorted(t, last_lock_t, side="left"))
                    j = min(j + 1, t.size - 1)
                    rec["t_lock_s"] = last_lock_t
                    rec["rod_at_lock_bar"] = float(rod[j, leg])
                    rec["lock_duration_s"] = te - last_lock_t
                rec["p_r0_ext_bar"] = float(pr0_ext[leg]) / BAR if pr0_ext else None
                rec["p_r0_ret_bar"] = float(pr0_ret[leg]) / BAR if pr0_ret else None
                releases.append(rec)
                last_lock_t = None
            # lift-offs (airborne false -> true)
            idx = np.flatnonzero(~air[:-1, leg] & air[1:, leg]) + 1
            locks = [(te, kind) for (te, kind, _, _) in ev]
            for i in idx:
                tl = float(t[i])
                if i < 2 or i + 12 >= t.size:
                    continue
                # valve state at lift-off: last event before tl
                # (state 10 ms before the lift-off: the 222.4 list classifies by the applied
                # command of the 10 Hz row, so a release a few ms before the lift-off counts as
                # locked there)
                prev = [k for (te, k) in locks if te <= tl - 0.010]
                state_locked = (prev[-1] == "lock") if prev else abs(valve[0, leg]) <= eps
                rb = float(rod[i - 1, leg])
                rmin = float(np.min(rod[i:i + 11, leg]))
                rel_near = [te for (te, k) in locks
                            if k == "release" and tl - 0.010 <= te <= tl + 0.010]
                kb = int(np.argmin(np.abs(t10 - tl)))
                liftoffs.append({
                    "case": ep.name, "leg": LEGS[leg], "t_s": tl, "locked": bool(state_locked),
                    "rod_before_bar": rb, "rod_min_10ms_bar": rmin,
                    "collapse": bool(state_locked and (rb - rmin) > 50.0),
                    "release_within_10ms": [round(x, 5) for x in rel_near],
                    "dt_to_boundary_ms": (tl - float(t10[kb])) * 1e3,
                })
    # summaries
    rel_big = [r for r in releases if abs(r["rod_jump_bar"]) > 20.0]
    stale = [r for r in releases if "rod_at_lock_bar" in r]
    stale_err = [abs(r["rod_after_bar"] - r["rod_at_lock_bar"]) for r in stale
                 if abs(r["rod_jump_bar"]) > 20.0]
    lk = [x for x in liftoffs if x["locked"]]
    col = [x for x in lk if x["collapse"]]
    col_with_rel = [x for x in col if x["release_within_10ms"]]
    nocol_with_rel = [x for x in lk if not x["collapse"] and x["release_within_10ms"]]
    summary = {
        "episodes": len(eps_dir),
        "valve_reconstruction_max_rel_err": max(valve_check) if valve_check else None,
        "releases": len(releases),
        "releases_rod_jump_gt20bar": len(rel_big),
        "releases_rod_jump_gt50bar": sum(abs(r["rod_jump_bar"]) > 50.0 for r in releases),
        "release_jump_abs_p50_p90_max_bar": (
            [float(np.percentile([abs(r["rod_jump_bar"]) for r in releases], q))
             for q in (50, 90, 100)] if releases else None),
        "big_jump_after_vs_rod_at_lock_abs_p50_p90_max_bar": (
            [float(np.percentile(stale_err, q)) for q in (50, 90, 100)] if stale_err else None),
        "big_jump_t_x_ms_p50_p90_max": (
            [float(np.percentile([r["t_x_ms"] for r in rel_big], q)) for q in (50, 90, 100)]
            if rel_big else None),
        "big_jump_airborne_before": sum(r["airborne_before"] for r in rel_big),
        "liftoffs": len(liftoffs),
        "locked_liftoffs": len(lk),
        "locked_liftoff_collapse": len(col),
        "collapse_with_release_within_10ms": len(col_with_rel),
        "no_collapse_with_release_within_10ms": len(nocol_with_rel),
        "collapse_list": col,
    }
    out = {"summary": summary, "releases_big": rel_big, "liftoffs_locked": lk}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "collapse_list"}, indent=1))
    for c in col:
        print(c)


if __name__ == "__main__":
    main()
