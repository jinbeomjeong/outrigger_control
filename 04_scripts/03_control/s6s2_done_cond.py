"""S6 stage 2: which DONE condition finishes last (attitude 0.03 deg, twist 3 kN) - Chrono vs reduced.

Twist = n^T F_cyl (true cylinder force), n = (0.476, -0.476, -0.523, 0.523). Chrono from record.npz (20 ms),
reduced from s6_target_sim.run_tgt series (Ftrue). Reports, after the LEVEL start, the time the twist enters and
stays inside +-3 kN (DONE twist) and +-2 kN (deadband), and its value at 5 / 10 / 15 s; also the leg-speed
command in the twist direction (n^T u) RMS between attitude < 0.05 deg and DONE.
Run: conda run -n dynamics-dev python -I s6s2_done_cond.py <project_root> <out_json>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(sys.argv[1])
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control"))
import s6_target_sim as sts  # noqa: E402

N = np.array([0.476, -0.476, -0.523, 0.523])
CASES = {"G1_top_roll3": ("stage2_20261021_213235", (3.0, 0.0), "pressure"),
         "G1_top_diag3": ("stage2_20261021_213235", (3 / math.sqrt(2), 3 / math.sqrt(2)), "pressure"),
         "G2_top_roll5.5": ("stage2_20261021_214443", (5.5, 0.0), "combined")}


def stays(t, x, lim, t0, t1):
    m = (t >= t0) & (t <= t1)
    idx = np.where(m)[0]
    for i in idx:
        j = (t >= t[i]) & (t <= t1)
        if np.all(np.abs(x[j]) <= lim):
            return round(float(t[i] - t0), 2)
    return None


def summarise(t, F, u, t_level, t_done):
    tw = F @ N / 1e3
    out = {"twist_in_3kN_after_level_s": stays(t, tw, 3.0, t_level, t_done),
           "twist_in_2kN_after_level_s": stays(t, tw, 2.0, t_level, t_done),
           "twist_at_kN": {s: round(float(np.interp(t_level + s, t, tw)), 2) for s in (5, 10, 15, 18)},
           "twist_final_kN": round(float(tw[-1]), 2), "done_after_level_s": round(t_done - t_level, 2)}
    ut = u @ N * 1e3
    m = (t >= t_level + 8) & (t <= t_done)
    out["twist_cmd_rms_mm_s_8s_to_done"] = round(float(np.sqrt(np.mean(ut[m] ** 2))), 4) if m.any() else None
    return out


_LAST = {}


def main():
    res = {}
    import run_c2_timedomain as c2t
    orig = c2t.run_case

    def wrapped(*a, **k):
        rr = orig(*a, **k); _LAST["S"] = rr.get("_series"); return rr
    c2t.run_case = wrapped
    for name, (batch, floor, contact) in CASES.items():
        d = ROOT / "07_results" / "S6" / batch / name
        r = json.loads((d / "result.json").read_text())
        z = np.load(d / "record" / "record.npz")
        t = z["t"] - r["settings"]["start_t_s"]
        tl = next(tt for tt, n in r["phases"] if n == "level")
        td = next(tt for tt, n in r["phases"] if n == "done")
        ch = summarise(t, z["F_cyl"], z["u_cmd"], tl, td)
        o = sts.run_tgt(dict(id=f"red|{name}", floor_deg=floor, level="top", contact=contact,
                             tgt={"target_deg": (0.0, 0.0), "ra_mode": "rel"}, t_hold=10.0))
        S = _LAST["S"]
        ts = np.asarray(S["t"])
        rd = summarise(ts, np.asarray(S["Ftrue"]), np.asarray(S["u"]), o["t_touch_s"], o["t_done_s"])
        res[name] = {"chrono": ch, "reduced": rd}
        print(name, json.dumps(res[name]))
    c2t.run_case = orig
    Path(sys.argv[2]).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
