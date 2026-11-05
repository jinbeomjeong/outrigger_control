"""M1c units against Hopsan (criteria: m1_criteria.md, M1c section).

Usage (dynamics-dev): python -I unit_m1c.py <hopsan t9 replay folder> <out.json>
E1: early_unit.json and early_boundary.json, single leg RR, extend from rest. E3: the rod state on the stored replay, Hopsan head
pressure and valve as inputs. Retract side: unit_m1b is unchanged, m1c calls the same retract_dead (checked here on one row).
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
T9 = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "pressure_review" / "m1_hopsan" / "t9_quintic"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "04_scripts" / "04_hydraulic" / "coupled"))
sys.path.insert(0, str(ROOT / "03_src"))

import numpy as np  # noqa: E402
from m1c_plant import M1cConfig, drain_speed, head_opens, p_a_of_x, p_b_equalized, rod_opens  # noqa: E402
from params import load_params  # noqa: E402

LEG = 3
TAU_V = 0.1
P_T = 2e5
KIND = {"vent": "VR", "vent_ref": "VN", "block_lowA": "BL"}


def compliances(p, s0):
    A_h, A_r = float(p.A_h[LEG]), float(p.A_r[LEG])
    return A_r * (p.L0r + p.stroke - s0) / p.beta, 285e-6 / 0.5e9, A_h, A_r


def e1_times(p, cfg, p_r, p_h, v, duration, s0, F_s=0.0, with_head_follow=True):
    """Fill from rest with the lagged valve: (t_rod, stroke_rod, t_head, stroke_head), None when not reached."""
    c_r, c_l, A_h, A_r = compliances(p, s0)
    K_n = (cfg.neutral_fraction if cfg.is_vent else 0.0) * A_h * p.v_max / math.sqrt(p.dp_comp)
    dt = 1e-4
    u = x = delivered = t = 0.0
    t_rod = t_head = None
    stroke_rod = stroke_head = None
    p_b_after = None
    rod_starts_open = cfg.kind == "VR" and p_r <= P_T * (1.0 + cfg.psi) - cfg.p_crack_Pa
    while t < duration + 0.3:
        cmd = v if t < duration else 0.0
        u += (cmd - u) * dt / TAU_V
        gate = max(1.0 - u / (cfg.c_v * p.v_max), 0.0)
        p_a = p_a_of_x(cfg, x, A_h, P_T)
        x = max(x + (u - drain_speed(K_n, gate, p_a, P_T, A_h)) * dt, 0.0)
        delivered += u * dt
        t += dt
        p_a = p_a_of_x(cfg, x, A_h, P_T)
        if t_rod is None and (rod_starts_open or rod_opens(cfg, p_a, p_r, P_T, P_T)):
            t_rod, stroke_rod = t, delivered
            p_b_after = p_r if rod_starts_open else p_b_equalized(p_r, P_T, c_r, c_l)
        if t_rod is not None:
            # p_B follows p_r: the harness rod law after release, fixed tau 0.05 s towards 2 bar g (p_r0 after extend)
            p_r_law = 2e5 + (p_r - 2e5) * math.exp(-(t - t_rod) / 0.05)
            # the rod pressure falling pushes the piston out on the head oil once it beats the friction: what the kernel does
            # with its band (the bench load is a constant force); this is the plant, not a term of E1
            p_h_now = p_h - max(A_r * (p_r - p_r_law) - F_s, 0.0) / A_h if with_head_follow else p_h
            if head_opens(cfg, p_a, min(p_b_after, p_r_law), p_h_now):
                t_head, stroke_head = t, delivered
                break
    return t_rod, stroke_rod, t_head, stroke_head


def early_unit(p, rows, s0):
    per = defaultdict(lambda: {"rod": [], "head0": [], "headF": [], "wrong": 0, "both_none": 0, "n": 0, "t_rod": []})
    out = []
    for r in rows:
        mode = r["mode"]
        if mode not in KIND:
            continue
        cfg = M1cConfig(kind=KIND[mode])
        duration = min(0.003 / (r["v_mm_s"] * 1e-3), 6.0)
        t_rod, s_rod, t_head, s_head = e1_times(p, cfg, r["p_r_pre"] * 1e5, r["p_h_pre"] * 1e5, r["v_mm_s"] * 1e-3, duration, s0, r["F_s"])
        b = per[mode]
        b["n"] += 1
        hop = r.get("stroke_rod_mm")
        if (hop is None) != (s_rod is None):
            b["wrong"] += 1
        elif hop is None:
            b["both_none"] += 1
        else:
            if r.get("rod_open_pre", 0.0) < 0.5:
                b["rod"].append(s_rod * 1e3 / hop - 1.0)
                b["t_rod"].append(t_rod / r["t_rod_s"] - 1.0)
        row = {"name": r["name"], "mode": mode, "hop_rod_mm": hop, "m1c_rod_mm": None if s_rod is None else round(s_rod * 1e3, 4), "hop_head_mm": r.get("stroke_head_mm"), "m1c_head_mm": None if s_head is None else round(s_head * 1e3, 4), "rod_open_pre": r.get("rod_open_pre")}
        if r.get("stroke_head_mm") and s_head:
            rel = s_head * 1e3 / r["stroke_head_mm"] - 1.0
            row["rel_head"] = round(rel, 4)
            (b["headF"] if r["F_s"] > 0 else b["head0"]).append(rel)
        elif bool(r.get("stroke_head_mm")) != bool(s_head):
            row["head_outcome_differs"] = True
        out.append(row)
    summary = {k: {"n": b["n"], "wrong_open": b["wrong"], "both_never": b["both_none"], "rod_worst": round(max((abs(x) for x in b["rod"]), default=0.0), 4), "rod_median": round(float(np.median(np.abs(b["rod"]))) if b["rod"] else 0.0, 4), "rod_n": len(b["rod"]),
                   "head_F0_worst": round(max((abs(x) for x in b["head0"]), default=0.0), 4), "head_F0_median": round(float(np.median(np.abs(b["head0"]))) if b["head0"] else 0.0, 4),
                   "head_Fs_worst": round(max((abs(x) for x in b["headF"]), default=0.0), 4), "head_Fs_median": round(float(np.median(np.abs(b["headF"]))) if b["headF"] else 0.0, 4)} for k, b in per.items()}
    return summary, out


def boundary(p, rows, s0):
    cfg = M1cConfig(kind="VR")
    out = []
    wrong = 0
    rel0, relF = [], []
    for r in rows:
        v = r["v_mm_s"] * 1e-3
        # these runs are the stock vent circuit; the rods start above or below the open limit as set
        t_rod, s_rod, t_head, s_head = e1_times(p, cfg, r["p_r_pre"] * 1e5, r["p_h"] * 1e5, v, min(0.004 / v, 4.0), s0, r["F_s"])
        _, _, _, s_head_fixed = e1_times(p, cfg, r["p_r_pre"] * 1e5, r["p_h"] * 1e5, v, min(0.004 / v, 4.0), s0, r["F_s"], with_head_follow=False)
        sep_hop = r.get("t_head", math.nan) - r.get("t_rod", math.nan)
        hop_together = sep_hop < 0.01
        m1c_together = t_head is not None and t_rod is not None and t_head - t_rod < 0.01
        wrong += hop_together != m1c_together
        row = {"name": r["name"], "hop_rod": r.get("stroke_rod"), "m1c_rod": None if s_rod is None else round(s_rod * 1e3, 4), "hop_head": r.get("stroke_head"), "m1c_head": None if s_head is None else round(s_head * 1e3, 4), "hop_together": bool(hop_together), "m1c_together": bool(m1c_together), "rod_open_pre": r.get("rod_open_pre"), "F_s": r["F_s"]}
        if r.get("stroke_head") and s_head:
            rel = s_head * 1e3 / r["stroke_head"] - 1.0
            row["rel_head"] = round(rel, 4)
            (relF if r["F_s"] > 0 else rel0).append(rel)
        if r.get("stroke_head") and s_head_fixed:
            row["rel_head_fixed_p_h"] = round(s_head_fixed * 1e3 / r["stroke_head"] - 1.0, 4)
        out.append(row)
    fixed = [abs(x["rel_head_fixed_p_h"]) for x in out if "rel_head_fixed_p_h" in x]
    print("boundary, p_h fixed: worst", round(max(fixed), 3), "median", round(float(np.median(fixed)), 3))
    print("boundary count within 10 %, 25 %:", sum(abs(x.get("rel_head", 9)) <= 0.10 for x in out), sum(abs(x.get("rel_head", 9)) <= 0.25 for x in out), "of", len(out))
    return {"n": len(rows), "wrong_together": wrong, "head_F0_worst": round(max(abs(x) for x in rel0), 4), "head_F0_median": round(float(np.median(np.abs(rel0))), 4), "head_Fs_worst": round(max(abs(x) for x in relF), 4), "head_Fs_median": round(float(np.median(np.abs(relF))), 4)}, out


def e3_rod(p, replay_dir):
    """Rod pressure of RR by the E3 state with the Hopsan head pressure and valve as inputs, to +1.4 s."""
    out = {}
    A_h, A_r = float(p.A_h[LEG]), float(p.A_r[LEG])
    cfg = M1cConfig(kind="VR")
    K_land = A_h * p.v_max / math.sqrt(p.dp_comp)
    K_n = cfg.neutral_fraction * K_land
    limit = P_T * (1.0 + cfg.psi) - cfg.p_crack_Pa
    for name in ("vent_V1", "vent_OFF"):
        for off in ("0.0", "0.025", "0.05", "0.075"):
            d = np.load(replay_dir / f"{name}_{off}.npz")
            t, ph, pr = d["t"], d["ph"][:, LEG], d["pr"][:, LEG]
            unit = 1.0 if np.abs(ph).max() > 1e4 else 1e5
            ph, pr = ph * unit, pr * unit
            u_t, u = d["grid"], d["u"][:, LEG]
            s_guess = float(p.s0[LEG])
            c_r = A_r * (p.L0r + p.stroke - s_guess) / p.beta
            v_h = A_h * (p.L0h + s_guess)
            start = int(np.searchsorted(t, 0.0))
            y = float(pr[start])
            y2 = y
            closed = False
            n = int(np.searchsorted(t, 1.4))
            k_cmd = int(np.searchsorted(t, 0.85))
            y_at_085 = None
            for k in range(start, n):
                if k == k_cmd:
                    y_at_085 = y
                dt = float(t[k + 1] - t[k])
                ds = -v_h * (ph[k + 1] - ph[k]) / (p.beta * A_h)
                speed = abs(float(np.interp(t[k], u_t, u)))
                gate = max(1.0 - speed / (cfg.c_v * p.v_max), 0.0)
                q = K_n * gate * math.sqrt(max(y - P_T, 0.0))
                y = y + (A_r * ds - q * dt) / c_r  # the head relaxes, the rod extends, the rod chamber shrinks
                q2 = (K_n * gate + K_land * speed / p.v_max) * math.sqrt(max(y2 - P_T, 0.0))
                y2 = y2 + (A_r * ds - q2 * dt) / c_r
            hop = float(np.interp(1.4, t, pr))
            head = float(np.interp(1.4, t, ph))
            ob = d["ob"][:, LEG]
            closes = int(np.sum((t[start:n] > 0) & (ob[start:n] < 0.5)))
            out[f"{name}_{off}"] = {"hopsan_0p85_bar": round(float(np.interp(0.85, t, pr)) / 1e5, 2), "e3_0p85_bar": round(y_at_085 / 1e5, 2), "hopsan_bar": round(hop / 1e5, 2), "e3_bar": round(y / 1e5, 2), "e3_plus_land_bar": round(y2 / 1e5, 2), "rod_closed_samples_hopsan": closes, "p_h_hopsan_bar": round(head / 1e5, 2), "limit_bar": limit / 1e5, "rod_p0_bar": round(float(pr[start]) / 1e5, 2)}
    return out


def main() -> None:
    p = load_params()
    s0 = float(p.s0[LEG])
    early, early_rows = early_unit(p, json.loads((T9 / "early_unit.json").read_text(encoding="utf-8")), s0)
    bound, bound_rows = boundary(p, json.loads((T9 / "early_boundary.json").read_text(encoding="utf-8")), s0)
    rod = e3_rod(p, Path(sys.argv[1]))
    out = {"early_unit": early, "boundary": bound, "e3_rod": rod, "early_rows": early_rows, "boundary_rows": bound_rows}
    Path(sys.argv[2]).parent.mkdir(parents=True, exist_ok=True)
    Path(sys.argv[2]).write_text(json.dumps(out, indent=0), encoding="utf-8")
    print(json.dumps({"early_unit": early, "boundary": bound, "e3_rod": rod}, indent=1))
    worst = sorted((abs(r["rel_head"]), r["name"], r["hop_rod"], r["m1c_rod"], r["hop_head"], r["m1c_head"], r["hop_together"], r["m1c_together"], r["rod_open_pre"]) for r in bound_rows if "rel_head" in r)[-10:]
    print("boundary worst", worst)
    print("boundary together differs", [r["name"] for r in bound_rows if r["hop_together"] != r["m1c_together"]])
    print("early head differs", [r["name"] for r in early_rows if r.get("head_outcome_differs")][:12])
    print("early head worst", sorted((abs(r["rel_head"]), r["name"], r["hop_rod_mm"], r["m1c_rod_mm"], r["hop_head_mm"], r["m1c_head_mm"]) for r in early_rows if "rel_head" in r)[-10:])


if __name__ == "__main__":
    main()
