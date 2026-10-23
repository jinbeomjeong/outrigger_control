"""S6 stage 2: where the levelling time goes (items 1a roll 3 deg, 3 roll 5.5 deg), Chrono vs reduced model.

Chrono: 07_results/S6/stage2_*/<case>/record/record.npz (20 ms truth), phases from result.json.
Reduced: s6_target_sim.run_tgt (C2 R2 + H4 rel, pressure-only, delay 1, ramp 0.1 s), same floor and level.
Milestones after the LEVEL start: crawler lift-off, |att| < 1 / 0.2 / 0.05 deg (true, worst axis), DONE; plus the
max true leg speed share at v_max (saturation fraction) during LEVEL, and the final corrective A+F / twist.
Run: conda run -n dynamics-dev python -I s6s2_level_time.py <project_root> <out_json>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(sys.argv[1])
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control"))
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import s6_target_sim as sts  # noqa: E402

VMAX = 0.68 / 30
CASES = {"G1_top_roll3": ("stage2_20261021_213235", (3.0, 0.0), "pressure"),
         "G1_top_diag3": ("stage2_20261021_213235", (3 / math.sqrt(2), 3 / math.sqrt(2)), "pressure"),
         "G1_top_flat": ("stage2_20261021_213235", (0.0, 0.0), "pressure"),
         "G2_top_roll5.5": ("stage2_20261021_214443", (5.5, 0.0), "combined"),
         "G2_bottom_roll5.5": ("stage2_20261021_214443", (5.5, 0.0), "combined")}


def quat_rp(q):
    w, x, y, z = q.T
    return (np.degrees(np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))),
            np.degrees(np.arcsin(np.clip(2 * (w * y - z * x), -1, 1))))


def milestones(t, att, t_level, t_off, t_done, v=None):
    m = t >= t_level
    e = np.max(np.abs(att), axis=1)
    out = {"lift_after_level_s": None if t_off is None else round(t_off - t_level, 2),
           "done_after_level_s": None if t_done is None else round(t_done - t_level, 2)}
    for lim in (1.0, 0.2, 0.05):
        idx = np.where(m & (e < lim))[0]
        # first time it stays below lim until DONE
        ok = None
        for i in idx:
            j = (t >= t[i]) & (t <= (t_done if t_done else t[-1]))
            if np.all(e[j] < lim):
                ok = t[i]; break
        out[f"below_{lim}_after_level_s"] = None if ok is None else round(float(ok - t_level), 2)
    if v is not None:
        ml = m & (t <= (t_done if t_done else t[-1]))
        out["vmax_share_in_level"] = round(float(np.mean(np.max(np.abs(v[ml]), axis=1) > 0.98 * VMAX)), 3)
    return out


def chrono(name, batch):
    d = ROOT / "07_results" / "S6" / batch / name
    r = json.loads((d / "result.json").read_text())
    t0 = r["settings"]["start_t_s"]
    z = np.load(d / "record" / "record.npz")
    t = z["t"] - t0
    ro, pi = quat_rp(z["body_quat_wxyz"])
    ph = r["phases"]
    t_level = next(tt for tt, n in ph if n == "level")
    t_done = next((tt for tt, n in ph if n == "done"), None)
    return milestones(t, np.column_stack([ro, pi]), t_level, r["crawler_off_t_s"], t_done, z["u_applied"])


_LAST = {}


def reduced(floor, level="top", contact="pressure"):
    import run_c2_timedomain as c2t
    orig = c2t.run_case

    def wrapped(*a, **k):
        rr = orig(*a, **k); _LAST["S"] = rr.get("_series"); return rr
    c2t.run_case = wrapped
    try:
        out = sts.run_tgt(dict(id=f"red|{floor}|{contact}", floor_deg=floor, level=level, contact=contact,
                               tgt={"target_deg": (0.0, 0.0), "ra_mode": "rel"}, t_hold=10.0))
    finally:
        c2t.run_case = orig
    S = _LAST["S"]
    t = np.asarray(S["t"]); att = np.degrees(np.column_stack([S["phi"], S["theta"]]))
    u = np.asarray(S["u"])
    ms = milestones(t, att, out["t_touch_s"], out["t_crawler_liftoff_s"], out["t_done_s"], u)
    ms["reduced_t_touch_s"] = out["t_touch_s"]
    return ms


def main():
    res = {}
    for name, (batch, floor, contact) in CASES.items():
        lvl = name.split("_")[1]
        res[name] = {"chrono": chrono(name, batch), "reduced": reduced(floor, lvl, contact)}
        print(name, json.dumps(res[name]))
    Path(sys.argv[2]).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
