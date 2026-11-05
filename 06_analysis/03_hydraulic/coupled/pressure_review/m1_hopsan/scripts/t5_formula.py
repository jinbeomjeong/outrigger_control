"""Proposed retract dead stroke (M1b) against the Hopsan runs of t1_floor.json; the current formula beside it."""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from bench import BETA_HOSE, PSI, V_LINE, geometry, load_params

OUT = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\pressure_review\m1_hopsan")
P_CRACK = 3e5


def need_m1b(p, leg, p_h, p_r, F_s_eff, p_T, void_m, rod_forward):
    """Dead stroke [m]; pressures gauge Pa. rod_forward: the rod check passes forward only (rod = line - crack)."""
    A_h, A_r, s0, _ = geometry(p, leg)
    delta = P_CRACK if rod_forward else 0.0
    # p_T + psi p_B - p_h - dp_h - p_cr = 0, dp_h = (A_r (p_B - delta - p_r) - F_s)+ / A_h
    drive = p_h + P_CRACK - p_T
    p_free = drive / PSI
    rising = A_r * (p_free - delta - p_r) > F_s_eff
    p_b = (drive - (A_r * (delta + p_r) + F_s_eff) / A_h) / (PSI - A_r / A_h) if rising else p_free
    p_rod = max(p_b - delta, p_r)
    dp_h = max(A_r * (p_rod - p_r) - F_s_eff, 0.0) / A_h
    v_h = A_h * (p.L0h + s0)
    v_r = A_r * (p.L0r + p.stroke - s0)
    vol = V_LINE * max(p_b - p_T, 0.0) / BETA_HOSE + v_r * (p_rod - p_r) / p.beta + A_r * v_h * dp_h / (p.beta * A_h)
    return vol / A_r + void_m, p_b


rows = json.loads((OUT / "t1_floor.json").read_text(encoding="utf-8"))
p = load_params()
agg = defaultdict(lambda: {"cur": [], "new": []})
out = []
for r in rows:
    if r["stroke_open_mm"] != r["stroke_open_mm"]:
        continue
    mode = r["mode"]
    p_T = 0.0 if "pT0" in mode else 2e5
    fresh = mode == "IC_floor"
    F_s_eff = r["F_s_N"] if fresh else 0.0  # the load rise has already taken the friction up in the retract direction
    rod_forward = mode in ("IC_floor", "ramp_floor_ref", "ramp_vent_pT0", "ramp_lowcrack")
    # block neutral: line A pilots the rod check open before the command, rod = line
    if mode in ("ramp_vent", "ramp_vent_stock", "ramp_lowcrack"):
        # refill through the neutral vent: rod state with the void kept (one more state of M1b)
        A_h, A_r, s0, _ = geometry(p, r["leg"])
        crack = 0.5e5 if mode == "ramp_lowcrack" else 0.0
        k_v = 0.05 * A_h * p.v_max / np.sqrt(p.dp_comp)
        v_r = A_r * (p.L0r + p.stroke - s0)
        y = 2e5
        dt = 1e-3
        rate = r["creep_ramp_mm"] * 1e-3 / 1.0
        floor = -1e5
        for k in range(1200):
            sdot = rate if k < 1000 else 0.0
            dp = 2e5 - max(y, floor) - crack
            q = k_v * np.sqrt(max(dp, 0.0))
            y += (-A_r * sdot + q) * p.beta / v_r * dt
            y = min(y, 2e5)
        void_state = max(floor - y, 0.0) * v_r / p.beta / A_r
        p_start = max(y, floor)
        need, p_b = need_m1b(p, r["leg"], r["p_h_pre"] * 1e5, p_start, F_s_eff, p_T, void_state, False)
    else:
        need, p_b = need_m1b(p, r["leg"], r["p_h_pre"] * 1e5, r["p_r_pre"] * 1e5, F_s_eff, p_T, r["void_mm"] * 1e-3, rod_forward)
    cur = r["stroke_open_mm"] / r["formula_mm"] - 1.0
    new = r["stroke_open_mm"] / (need * 1e3) - 1.0
    agg[mode]["cur"].append(cur)
    agg[mode]["new"].append(new)
    out.append({"name": r["name"], "mode": mode, "stroke_hopsan_mm": r["stroke_open_mm"], "m1_mm": r["formula_mm"], "m1b_mm": need * 1e3, "m1b_p_open_bar": p_b / 1e5, "hopsan_p_b_open_bar": r["p_b_open"], "rel_m1": cur, "rel_m1b": new})
summary = {}
print("mode | Hopsan/M1-1 range | Hopsan/M1b-1 range")
for mode, a in agg.items():
    c, n = np.array(a["cur"]), np.array(a["new"])
    summary[mode] = {"n": len(c), "rel_m1_min": float(c.min()), "rel_m1_max": float(c.max()), "rel_m1b_min": float(n.min()), "rel_m1b_max": float(n.max())}
    print(mode, len(c), f"{c.min():+.3f} {c.max():+.3f} | {n.min():+.3f} {n.max():+.3f}")
(OUT / "t5_formula.json").write_text(json.dumps({"summary": summary, "rows": out}, indent=0), encoding="utf-8")
