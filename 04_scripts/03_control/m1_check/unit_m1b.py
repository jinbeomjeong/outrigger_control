"""M1b units against the Hopsan tables t1_floor.json and t2_chop.json (criteria: m1_criteria.md, M1b section).

Usage (dynamics-dev): python -I unit_m1b.py <out.json>
t1: dead stroke from the pre-command state of each Hopsan run, compared with the delivered stroke at the head check opening.
t2: the line state of rule 3 on the chopped command, open / not open within 12 s and the opening time.
"""
from __future__ import annotations

import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MKL_THREADING_LAYER", "TBB")
os.environ.setdefault("MKL_NUM_THREADS", "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HOP = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "pressure_review" / "m1_hopsan"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "04_scripts" / "04_hydraulic" / "coupled"))
sys.path.insert(0, str(ROOT / "03_src"))

import numpy as np  # noqa: E402
from m1b_plant import M1bConfig, retract_dead  # noqa: E402
from params import load_params  # noqa: E402

TAU_V = 0.1
TS_CMD = 0.1
EPS = 1e-6
PATTERNS = {
    "const0.84": [0.84], "const0.45": [0.45], "const0.35": [0.35], "alt0.84_0": [0.84, 0.0], "alt1.05_0.3": [1.05, 0.3],
    "5h1z": [1.05] * 5 + [0.0], "5h3z": [1.05] * 5 + [0.0] * 3, "5h5z": [1.05] * 5 + [0.0] * 5, "5h3low": [1.05] * 5 + [0.3] * 3,
    "5h5low": [1.05] * 5 + [0.3] * 5, "alt0.5_0.35": [0.5, 0.35], "alt0.6_0.25": [0.6, 0.25], "10h5z": [0.84] * 10 + [0.0] * 5,
    "guard3_rel": [5.2] * 2 + [0.3] * 3}
"""Command magnitudes per 0.1 s [mm/s], copied from t2_chop.py."""


def geometry(p, leg):
    return float(p.A_h[leg]), float(p.A_r[leg]), float(p.s0[leg])


def k_land(p, leg):
    return float(p.A_h[leg]) * p.v_max / math.sqrt(p.dp_comp)


def rod_state_after_ramp(p, leg, creep_mm, crack_b):
    """Rod pressure [Pa] and void [m] after the 1 s load ramp and 0.2 s hold, vent refill of rule 2 (bench timing)."""
    A_ann = float(p.A_r[leg])
    _, _, s0 = geometry(p, leg)
    v_rod = A_ann * (p.L0r + p.stroke - s0)
    K_n = 0.05 * k_land(p, leg)
    y, dt, rate, floor = 2e5, 1e-3, creep_mm * 1e-3, -1e5
    for k in range(1200):
        sdot = rate if k < 1000 else 0.0
        q = K_n * math.sqrt(max(2e5 - max(y, floor) - crack_b, 0.0))
        y = min(y + (-A_ann * sdot + q) * p.beta / v_rod * dt, 2e5)
    return max(y, floor), max(floor - y, 0.0) * v_rod / p.beta / A_ann


def t1_need(p, row):
    mode, leg = row["mode"], row["leg"]
    A_h, A_ann, s0 = geometry(p, leg)
    p_T = 0.0 if "pT0" in mode else 2e5
    f_band = row["F_s_N"] if mode == "IC_floor" else 0.0  # the load rise has taken the friction up (review)
    rod_forward = mode in ("IC_floor", "ramp_floor_ref", "ramp_vent_pT0", "ramp_lowcrack")
    if mode in ("ramp_vent", "ramp_vent_stock", "ramp_lowcrack"):
        crack_b = 0.5e5 if mode == "ramp_lowcrack" else 0.0
        p_r, void = rod_state_after_ramp(p, leg, row["creep_ramp_mm"], crack_b)
        rod_forward = False
    else:
        p_r, void = row["p_r_pre"] * 1e5, row["void_mm"] * 1e-3
    cfg = M1bConfig(rod_forward=rod_forward)
    return retract_dead(cfg, row["p_h_pre"] * 1e5, p_r, f_band, s0, void, A_h, A_ann, p.stroke, p.L0r, p.L0h, p.beta, p_T)


def t2_open_time(p, pattern, need, rise, leg, c_v, is_block):
    """Open time [s] of rule 3 on the 0.1 s command; None = not within the command length."""
    dt = 1e-3
    commands = np.resize(np.array(PATTERNS[pattern]) * 1e-3, 120)
    A_ann = float(p.A_r[leg])
    K_n = 0.0 if is_block else 0.05 * k_land(p, leg)
    u = x = 0.0
    keep = math.exp(-dt / TAU_V)
    for k in range(int(120 * TS_CMD / dt)):
        cmd = commands[k // 100]
        u = cmd + (u - cmd) * keep
        gate = max(1.0 - u / (c_v * p.v_max), 0.0)
        drain = K_n * gate * math.sqrt(rise * min(x / need, 1.0)) / A_ann
        x = max(x + (u - drain) * dt, 0.0)
        if x >= need:
            return (k + 1) * dt
    return None


def main() -> None:
    p = load_params()
    t1 = json.loads((HOP / "t1_floor.json").read_text(encoding="utf-8"))
    per_mode = defaultdict(list)
    rows1 = []
    voids = {}
    for row in t1:
        if row["stroke_open_mm"] != row["stroke_open_mm"]:
            continue
        need = t1_need(p, row)["need"] * 1e3
        rel = row["stroke_open_mm"] / need - 1.0
        per_mode[row["mode"]].append(rel)
        rows1.append({"name": row["name"], "mode": row["mode"], "hopsan_mm": row["stroke_open_mm"], "m1b_mm": round(need, 4), "m1_mm": row["formula_mm"], "rel": round(rel, 4)})
        if row["leg"] == 2 and row["p_h_target"] == 115.0:
            voids[(row["mode"], row["fs0_kN"])] = row["void_mm"]
    t1_summary = {m: {"n": len(v), "min": round(min(v), 4), "max": round(max(v), 4), "worst": round(max(abs(a) for a in v), 4)} for m, v in per_mode.items()}

    t2 = json.loads((HOP / "t2_chop.json").read_text(encoding="utf-8"))
    leg = 2
    A_h, A_ann, s0 = geometry(p, leg)
    mode_of = {"vent": "ramp_vent", "vent_close1pc": "ramp_vent", "vent_close5pc": "ramp_vent", "vent_ref": "ramp_floor_ref", "block": "ramp_block"}
    c_of = {"vent_close1pc": 0.01, "vent_close5pc": 0.05}
    rows2 = []
    for row in t2:
        variant = row["variant"]
        mode = mode_of[variant]
        void = voids.get((mode, row["fs0_kN"]), 0.0) * 1e-3 if mode != "ramp_vent" else 0.0
        cfg = M1bConfig(rod_forward=variant == "vent_ref")
        values = retract_dead(cfg, row["p_h_pre"] * 1e5, row["p_r_pre"] * 1e5, 0.0, s0, void, A_h, A_ann, p.stroke, p.L0r, p.L0h, p.beta, 2e5)
        t_open = t2_open_time(p, row["pattern"], values["need"], max(values["p_open"] - 2e5, 0.0), leg, c_of.get(variant, 0.02), variant == "block")
        hop = row["t_open_hopsan"]
        hop_open = hop == hop and hop is not None
        rel = None if not (hop_open and t_open) else t_open / hop - 1.0
        rows2.append({"variant": variant, "pattern": row["pattern"], "fs0_kN": row["fs0_kN"], "hopsan_s": None if not hop_open else hop, "m1b_s": t_open,
                      "rule_s": row["t_open_rule"], "need_mm": round(values["need"] * 1e3, 3), "rel": None if rel is None else round(rel, 4), "outcome_ok": hop_open == (t_open is not None)})
    by = defaultdict(lambda: {"n": 0, "wrong": 0, "rels": [], "old_wrong": 0})
    for r in rows2:
        b = by[r["variant"]]
        b["n"] += 1
        b["wrong"] += not r["outcome_ok"]
        b["old_wrong"] += (r["hopsan_s"] is not None) != (r["rule_s"] is not None)
        if r["rel"] is not None:
            b["rels"].append(abs(r["rel"]))
    t2_summary = {k: {"n": b["n"], "wrong_outcome": b["wrong"], "rule_2pc_wrong_outcome": b["old_wrong"], "time_n": len(b["rels"]), "time_worst": round(max(b["rels"]), 4) if b["rels"] else None, "time_median": round(float(np.median(b["rels"])), 4) if b["rels"] else None} for k, b in by.items()}
    out = {"t1_summary": t1_summary, "t2_summary": t2_summary, "t1": rows1, "t2": rows2}
    Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)
    Path(sys.argv[1]).write_text(json.dumps(out, indent=0), encoding="utf-8")
    print(json.dumps({"t1": t1_summary, "t2": t2_summary}, indent=1))
    for r in rows2:
        if not r["outcome_ok"] or (r["rel"] is not None and abs(r["rel"]) > 0.15):
            print(r)


if __name__ == "__main__":
    main()
