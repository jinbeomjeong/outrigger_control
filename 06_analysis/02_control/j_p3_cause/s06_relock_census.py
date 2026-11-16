"""Step 6: census of the J-P3 precursor in every stored T4h record of the 436.8 harness runs.

Precursor ("hidden retract relock"): a leg that unlocks with a retract command and, before the
next controller read after a reversal to an extension command, locks again in the plant for a
short time and unlocks with the extension. In the plant a lock with last direction < 0 anchors
the rod pressure at p_ret; the locked law then follows the load, while the controller's
monitor never sees a zero acting command, so it opens no lock stretch (no ④, no revision-4 seed).

For every record (npz with ``lock_events``, ``command_m_s``, ``true_force_N``, meta
``extend_bound_check``) and leg this prints / writes:
  * short relocks: plant lock -> unlock pairs shorter than 0.3 s whose unlock follows a read
    with acting command > 0 and whose lock follows a read with acting command < 0,
  * the true force change over the lock (linear interpolation of the 10 Hz true force),
  * the record's ext_moving breach_reads and min_gap of that leg.

Usage: python -I -B s06_relock_census.py <out.json> <t4h folder> [<t4h folder> ...]
Read-only on the inputs; writes only <out.json>.
"""
import json
import sys
from pathlib import Path

import numpy as np

SHORT_S = 0.3
LEGS = ("FL", "FR", "RL", "RR")


def acting_command(t, u, t_query):
    """Acting command at plant time t_query: the output of the last read strictly before it
    (d = 1: the output of read k acts from read k on to read k+1)."""
    i = np.searchsorted(t, t_query - 1e-9) - 1
    return float(u[i]) if i >= 0 else 0.0


def scan(path):
    z = np.load(path, allow_pickle=True)
    if "lock_events" not in z.files:
        return None
    meta = json.loads(str(z["meta_json"]))
    ebc = meta.get("extend_bound_check") or {}
    t = z["t_s"]
    u = z["command_m_s"]
    f = z["true_force_N"]
    ev = sorted((float(r[0]), int(r[1]), bool(r[2])) for r in z["lock_events"])
    out = []
    for leg in range(4):
        e = [(tt, lk) for tt, l, lk in ev if l == leg]
        for k in range(1, len(e) - 1):
            t_lock, is_lock = e[k]
            t_unlock, is_unlock = e[k + 1]
            t_prev, was_unlock = e[k - 1]
            if not (is_lock and not is_unlock and not was_unlock):
                continue
            if t_unlock - t_lock > SHORT_S:
                continue
            # The valve lags the command (tau_v 0.1 s): the relock can come after the acting
            # command is already > 0. Take the acting commands from the previous unlock on.
            reads = (t > t_prev - 1e-9) & (t < t_unlock + 1e-9)
            acting = [acting_command(t, u[:, leg], tq) for tq in t[reads]] + [
                acting_command(t, u[:, leg], t_prev + 1e-6)]
            u_before = min(acting)
            u_after = acting_command(t, u[:, leg], t_unlock + 1e-6)
            if not (u_before < 0.0 < u_after) or t_lock - t_prev > 1.0:
                continue
            f_lock = float(np.interp(t_lock, t, f[:, leg]))
            f_unlock = float(np.interp(t_unlock, t, f[:, leg]))
            out.append({"leg": LEGS[leg], "t_prev_unlock_s": t_prev, "t_lock_s": t_lock,
                        "t_unlock_s": t_unlock, "lock_s": round(t_unlock - t_lock, 6),
                        "u_before_mm_s": u_before * 1e3, "u_after_mm_s": u_after * 1e3,
                        "dF_lock_kN": (f_unlock - f_lock) / 1e3,
                        "breach_reads_leg": (ebc.get("breach_reads") or [None] * 4)[leg],
                        "min_gap_bar_leg": (ebc.get("min_gap_bar") or [None] * 4)[leg],
                        "first_breach_t_s_leg": (ebc.get("first_breach_t_s") or [None] * 4)[leg]})
    breach = ebc.get("breach_reads")
    return {"file": str(path), "extend_start_rule":
            meta.get("two_pressure_settings", {}).get("extend_start_rule"),
            "lock_closure": meta.get("hydraulic_options", {}).get("lock_closure"),
            "breach_reads": breach, "episodes": out}


def main():
    out_path = Path(sys.argv[1])
    records = []
    for folder in sys.argv[2:]:
        for p in sorted(Path(folder).glob("*.npz")):
            r = scan(p)
            if r is not None:
                records.append(r)
    on = [r for r in records if r["extend_start_rule"] == "tracked_bound"]
    eps = [(r, e) for r in on for e in r["episodes"]]
    breach_runs = [r for r in on if r["breach_reads"] and sum(r["breach_reads"]) > 0]
    print("records", len(records), "tracked_bound", len(on), "with breach", len(breach_runs))
    print("short retract->extend relock episodes (tracked_bound):", len(eps))
    dfs = np.array([e["dF_lock_kN"] for _, e in eps])
    if dfs.size:
        print("  dF over the relock [kN]: min %.2f, p5 %.2f, median %.2f, max %.2f; "
              "episodes with dF < -0.5 kN: %d" % (dfs.min(), np.percentile(dfs, 5),
                                                 np.median(dfs), dfs.max(), int((dfs < -0.5).sum())))
    print("  episodes with dF < -0.5 kN or a breach on that leg:")
    for r, e in eps:
        if not (e["dF_lock_kN"] < -0.5 or (e["breach_reads_leg"] or 0) > 0):
            continue
        print(f"  {Path(r['file']).name:45s} {e['leg']} lock {e['t_lock_s']:.3f}-{e['t_unlock_s']:.3f}"
              f" ({e['lock_s']*1e3:5.1f} ms) u {e['u_before_mm_s']:+.5f}->{e['u_after_mm_s']:+.5f}"
              f" dF {e['dF_lock_kN']:+6.2f} kN  breach {e['breach_reads_leg']}"
              f" gap {e['min_gap_bar_leg']}")
    print("breach runs without a listed episode:")
    for r in breach_runs:
        legs = [i for i, b in enumerate(r["breach_reads"]) if b]
        has = {e["leg"] for e in r["episodes"]}
        for i in legs:
            if LEGS[i] not in has:
                print("  ", Path(r["file"]).name, LEGS[i], r["breach_reads"])
    out_path.write_text(json.dumps({"records": len(records), "tracked_bound": len(on),
                                    "breach_runs": len(breach_runs), "rows": records},
                                   indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
