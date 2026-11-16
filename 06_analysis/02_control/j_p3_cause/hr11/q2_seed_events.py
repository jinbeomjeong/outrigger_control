"""Q2: operating point of the P1 retract M2 seed steps in the 436.9 case replays (read only).

The harness records only the count and the largest seed step (``p1_retract_seed_step_max_bar``).
This script rebuilds every retract release from the per-lock ``lock_log`` (release time, locked
truth at the release = p_tr_after + dp_tr_lock) and the per-read arrays (true force, seal band,
acting command), and evaluates the seed with the worktree ``retract_dead`` at the plant inputs
(VN, volume scale 1, beta 1 GPa, L0 0.05 m). The step is seed - locked truth (the harness
definition in ``_start_release``). Inputs between reads are linearly interpolated (estimate).

Also inverts the seed step: the head pressure that gives a step of 19 / 33.9 bar.
Usage: python -I q2_seed_events.py <jsonl> [<jsonl> ...]
Units SI inside; printed bar (gauge), kN, mm. Valve values are ASSUMPTIONS (CheckValveValues).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, r"C:\workspace\z4369-jp3\03_src")
from outrigger_sim.hydraulics.check_open_delay import RetractConfig, retract_dead  # noqa: E402

BAR = 1e5
P_T = 2e5
S_MAX, L0, BETA = 0.70, 0.05, 1.0e9
A_H = np.array([0.013273229] * 2 + [math.pi / 4 * 0.11**2] * 2)
A_ANN = np.array([0.00376991118] * 2 + [math.pi / 4 * (0.11**2 - 0.09**2)] * 2)
CFG = RetractConfig(rod_forward=True, volume_scale=1.0, v_line_m3=285e-6, beta_hose_Pa=0.5e9,
                    psi=3.5, p_crack_Pa=3e5)
OUT = Path(__file__).with_suffix(".json")


def seed_step(leg, p_h, p_r, band, stroke):
    r = retract_dead(CFG, p_h, p_r, band, stroke, 0.0, float(A_H[leg]), float(A_ANN[leg]),
                     S_MAX, L0, L0, BETA, P_T)
    return float(r["p_rod"]), float(r["p_rod"]) - p_r, float(r["need"])


def invert(leg, step_bar, p_r, band):
    lo, hi = 0.0, 400e5
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if seed_step(leg, mid, p_r, band, 0.35)[1] < step_bar * BAR:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi) / BAR


def events(path):
    rows = []
    for line in map(json.loads, Path(path).read_text(encoding="utf-8").splitlines()):
        setting = line["job"]["setting"]
        rec = line["hydraulics_record"]
        cols = rec["lock_log_columns"]
        t4h = Path(path).with_name(f"{Path(path).stem}_t4h") / line["t4h_file"]
        with np.load(t4h, allow_pickle=False) as z:
            t = z["t_s"]
            force = z["true_force_N"]
            band = z["seal_band_N"]
            stroke = z["motor_stroke_m"]
            u_act = z["jp3_u_m_s"]
            jt = z["jp3_t_s"]
        found = []
        for raw in rec["lock_log"]:
            row = dict(zip(cols, raw))
            t_rel = row["t_release_s"]
            if t_rel is None:
                continue
            leg = int(row["leg"])
            k = int(np.searchsorted(jt, t_rel - 1e-9))
            if k >= len(jt):
                continue
            u = float(u_act[k, leg])  # acting command over (t_{k-1}, t_k]
            if u >= 0.0:
                continue
            p_r = row["p_tr_after_Pa"] + row["dp_tr_lock_Pa"]
            f = float(np.interp(t_rel, t, force[:, leg]))
            b = max(float(np.interp(t_rel, t, band[:, leg])), 0.0)
            s = float(np.interp(t_rel, t, stroke[:, leg]))
            p_h = (f + A_ANN[leg] * p_r) / A_H[leg]
            seed, step, need = seed_step(leg, p_h, p_r, b, s)
            found.append({"setting": setting, "t_release_s": t_rel, "leg": leg,
                          "u_mm_s": round(u * 1e3, 4), "F_kN": round(f / 1e3, 3),
                          "p_h_bar": round(p_h / BAR, 2), "p_r_locked_bar": round(p_r / BAR, 2),
                          "band_kN": round(b / 1e3, 3), "seed_bar": round(seed / BAR, 2),
                          "step_bar": round(step / BAR, 2), "need_mm": round(need * 1e3, 3)})
        rows.append({"setting": setting,
                     "recorded_count": rec.get("p1_retract_seed_count"),
                     "recorded_step_max_bar": rec.get("p1_retract_seed_step_max_bar"),
                     "rebuilt_retract_releases": len(found),
                     "rebuilt_step_max_bar": max((e["step_bar"] for e in found), default=None),
                     "events": found})
    return rows


def main():
    res = {"replays": {}, "inverse": {}}
    for p in sys.argv[1:]:
        res["replays"][p] = events(p)
    for leg, name in ((0, "front"), (2, "rear")):
        for pr in (P_T, 0.0, 5e5):
            for band in (0.0, 4e3):
                res["inverse"][f"{name}:p_r{pr / BAR:g}:band{band / 1e3:g}kN"] = {
                    "p_h_for_step19_bar": round(invert(leg, 19.0, pr, band), 2),
                    "p_h_for_step33.9_bar": round(invert(leg, 33.9, pr, band), 2),
                    "step_at_p_h77_bar": round(seed_step(leg, 77e5, pr, band, 0.35)[1] / BAR, 2)}
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    for p, reps in res["replays"].items():
        for r in reps:
            print(r["setting"], "recorded", r["recorded_count"],
                  round(r["recorded_step_max_bar"] or 0, 3), "rebuilt", r["rebuilt_retract_releases"],
                  r["rebuilt_step_max_bar"])
            for e in sorted(r["events"], key=lambda e: -e["step_bar"])[:4]:
                print("   ", e)
    for k, v in res["inverse"].items():
        print(k, v)


if __name__ == "__main__":
    main()
