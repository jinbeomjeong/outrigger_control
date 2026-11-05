"""Independent numpy path for the void result (F_s 0): same circuit as bench.py, raw chamber states kept below the floor.

Python loop, explicit, dt 2e-5 s. Floor -1 bar g (Hopsan 0 Pa abs). Compared with t1_floor.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from bench import BETA_HOSE, CQ, POC_KS, PSI, RHO, TAU_V, V_LINE, geometry, load_params, pin

OUT = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\pressure_review\m1_hopsan")
FLOOR = -1e5
P_CRACK = 3e5
FRONT_C, REAR_C = 34403.5, 30348.5


def qturb(k, dp):
    small = 1e4
    return k * (np.sqrt(dp) if dp > small else (-np.sqrt(-dp) if dp < -small else dp / np.sqrt(small)))


def sim(p, leg, ph_target, v_cmd, neutral, ref, p_T=2e5, dt=2e-5):
    A_h, A_r, s0, F_static = geometry(p, leg)
    k_st = float(p.k_st[leg])
    m_rod = float(p.m_rod[leg])
    M = F_static / 9.80665
    c = FRONT_C if leg < 2 else REAR_C
    p_h = (F_static + A_r * 2e5) / A_h
    F0 = F_static
    F1 = F0 + A_h * (ph_target - p_h)
    p_r = 2e5
    p_A = p_T if neutral == "vent" else p_h + P_CRACK
    p_B = p_T
    s = s0
    v = 0.0
    y = 0.0  # body position (extension positive is body up)
    vb = 0.0
    defl = F0 / k_st
    k_land = A_h * p.v_max / np.sqrt(p.dp_comp)
    k_n = 0.05 * k_land if neutral == "vent" else 0.0
    shift_b = PSI * p_T if ref else 0.0
    t_cmd = 0.5 + 1.0 + 0.2
    u = 0.0
    t = 0.0
    while t < t_cmd + 5.0:
        F = F0 + (F1 - F0) * min(max((t - 0.5) / 1.0, 0.0), 1.0)
        cmd = -v_cmd if t >= t_cmd else 0.0
        u += (cmd - u) * dt / TAU_V
        frac = abs(u) / p.v_max
        pa_, pb_, ph_, pr_ = max(p_A, FLOOR), max(p_B, FLOOR), max(p_h, FLOOR), max(p_r, FLOOR)
        open_a = pa_ + PSI * pb_ - ph_ - P_CRACK > 0.0
        open_b = pb_ + PSI * pa_ - pr_ - (P_CRACK + shift_b) > 0.0
        if t >= t_cmd and open_a:
            return t - t_cmd, abs(u), {"p_h": p_h / 1e5, "p_r_raw": p_r / 1e5, "p_B": p_B / 1e5}
        q_a = qturb(POC_KS, pa_ - ph_) if open_a else 0.0  # line -> head
        q_b = qturb(POC_KS, pb_ - pr_) if open_b else 0.0  # line -> rod
        vent = k_n * max(1.0 - frac / 0.02, 0.0)
        land = k_land * frac
        q_ta = qturb(vent + (land if u < 0 else 0.0), pa_ - p_T)
        q_tb = qturb(vent + (land if u > 0 else 0.0), pb_ - p_T)
        p_A += BETA_HOSE / V_LINE * (A_h * max(u, 0.0) - q_ta - q_a) * dt
        p_B += BETA_HOSE / V_LINE * (A_r * max(-u, 0.0) - q_tb - q_b) * dt
        p_h += p.beta / (A_h * (p.L0h + s)) * (q_a - A_h * v) * dt
        p_r += p.beta / (A_r * (p.L0r + p.stroke - s)) * (q_b + A_r * v) * dt
        f_oil = A_h * max(p_h, FLOOR) - A_r * max(p_r, FLOOR)
        f_k = k_st * ((s - s0) - y) + F0  # compression of k_st; load side
        a = (f_oil - c * v - f_k) / m_rod
        ab = (f_k - F) / M
        v += a * dt
        s += v * dt
        vb += ab * dt
        y += vb * dt
        t += dt
    return float("nan"), 0.0, {}


def stroke(v, t, tau=TAU_V):
    return v * (t - tau * (1.0 - np.exp(-t / tau))) * 1e3


def main():
    pin()
    p = load_params()
    t1 = {r["name"]: r for r in json.loads((OUT / "t1_floor.json").read_text(encoding="utf-8"))}
    rows = []
    for leg, name in ((2, "RL"), (1, "FR")):
        for ph in (115e5, 125e5):
            for mode, neutral, ref in (("ramp_vent", "vent", False), ("ramp_floor_ref", "vent", True), ("ramp_block", "block", False)):
                for tag, v in (("0.25vmax", 0.25 * p.v_max), ("0.05vmax", 0.05 * p.v_max)):
                    t_open, _u, state = sim(p, leg, ph, v, neutral, ref)
                    key = f"{name}_{ph / 1e5:g}_0_{mode}_{tag}"
                    h = t1[key]
                    row = {"case": key, "numpy_t_open_s": t_open, "numpy_stroke_mm": float(stroke(v, t_open)), "hopsan_t_open_s": h["t_open_s"], "hopsan_stroke_mm": h["stroke_open_mm"],
                           "rel_stroke": float(stroke(v, t_open)) / h["stroke_open_mm"] - 1.0, "numpy_state_at_open": state}
                    rows.append(row)
                    print(key, "numpy", round(t_open, 3), round(row["numpy_stroke_mm"], 2), "hopsan", round(h["t_open_s"], 3), round(h["stroke_open_mm"], 2), "rel", round(row["rel_stroke"], 3), {k: round(x, 1) for k, x in state.items()}, flush=True)
    (OUT / "t6_numpy.json").write_text(json.dumps(rows, indent=0), encoding="utf-8")
    print("max rel", max(abs(r["rel_stroke"]) for r in rows))


if __name__ == "__main__":
    main()
