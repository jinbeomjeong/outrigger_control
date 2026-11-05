"""Early rod release, single leg RR: extend from rest with a high rod pressure. Hopsan against the m1b rule.

m1b rule: p_A = (p_r + p_cr - p_T) / psi, stroke = V_line (p_A - p_T) / (beta_h A_h), with the line state of M1b for the drain.
Formula written before the runs (criteria.json). Modes: vent, vent_ref (rod check pilot referenced to tank), block with line A
trapped at the head pressure, block with line A at tank pressure. Output t9_quintic/early_unit.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from bench import BETA_HOSE, PSI, REAR_FS_SCALE, TAU_V, V_LINE, Bench, geometry, load_params, pin, run_many

OUT = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\pressure_review\m1_hopsan\t9_quintic")
HERE = Path(__file__).resolve().parent
LEG = 3
STATES = ((30e5, 50e5), (50e5, 40e5), (65e5, 29e5))  # p_r, p_h, bar gauge, near the RR states of the replay and the harness
SPEEDS = (0.25e-3, 0.5e-3, 1.05e-3, 2.6e-3, 5.2e-3)
P_T, P_CR = 2e5, 3e5
MODES = {"vent": dict(), "vent_ref": dict(pilot_ref_b=True), "block_trapA": dict(neutral="block"), "block_lowA": dict(neutral="block", line_a0_g=2e5)}


def rule(p, p_r, p_h, F_s, v, mode, A_h):
    """Time and stroke of the m1b rule; one line state, drain as in m1b_plant, spool lag included."""
    p_a = (p_r + P_CR - P_T) / PSI
    if mode == "vent_ref":
        p_a_ref = p_a + P_T  # the same law with the pilot back at tank; not in m1b, shown beside it
    else:
        p_a_ref = p_a
    d_rod = V_LINE * max(p_a_ref - P_T, 0.0) / BETA_HOSE / A_h
    p_head = p_h + F_s / A_h + P_CR
    d_head = V_LINE * max(p_head - P_T, 0.0) / BETA_HOSE / A_h
    k_land = A_h * p.v_max / np.sqrt(p.dp_comp)
    k_n = 0.05 * k_land if mode in ("vent", "vent_ref") else 0.0
    dt = 1e-3
    u = x = delivered = 0.0
    t = t_rod = t_head = None, None, None
    t = 0.0
    t_rod = t_head = None
    while t < 8.0:
        u += (v - u) * dt / TAU_V
        gate = max(1.0 - u / (0.02 * p.v_max), 0.0)
        p_l = x * A_h * BETA_HOSE / V_LINE
        x = max(x + (u - k_n * gate * np.sqrt(max(p_l, 0.0)) / A_h) * dt, 0.0)
        delivered += u * dt
        t += dt
        if t_rod is None and x >= d_rod:
            t_rod = (t, delivered)
        if t_head is None and x >= d_head:
            t_head = (t, delivered)
        if t_rod and t_head:
            break
    return {"p_A_rule": p_a_ref, "d_rod_mm": d_rod * 1e3, "d_head_mm": d_head * 1e3, "t_rod_s": t_rod[0] if t_rod else None, "stroke_rod_mm": t_rod[1] * 1e3 if t_rod else None,
            "t_head_s": t_head[0] if t_head else None, "stroke_head_mm": t_head[1] * 1e3 if t_head else None}


def main():
    pin()
    p = load_params()
    A_h, A_r, s0, _ = geometry(p, LEG)
    jobs = []
    for p_r, p_h in STATES:
        for fs0 in (0.0, 4e3):
            fs = fs0 * REAR_FS_SCALE
            for v in SPEEDS:
                for mode, kw in MODES.items():
                    F = A_h * p_h - A_r * p_r
                    dur = min(0.003 / v, 6.0)
                    name = f"RR_pr{p_r / 1e5:g}_Fs{fs0 / 1e3:g}_v{v * 1e3:g}_{mode}"
                    b = Bench(name, LEG, None, F_s=fs, start="static", p_r0=p_r, F_load=F, cmd_t=np.array([0.0, dur]), cmd_u=np.array([v, 0.0]), t_after=0.3, **kw)
                    jobs.append((b, p_r, p_h, fs, v, mode))
    print("runs", len(jobs), flush=True)
    results = run_many([j[0] for j in jobs], p, HERE / "t10")
    rows = []
    for (b, p_r, p_h, fs, v, mode), (_, res) in zip(jobs, results):
        t, t_cmd = res["t"], res["t_cmd"]
        grid, u = res["grid"], res["u"]
        delivered = np.concatenate([[0.0], np.cumsum(0.5 * (np.abs(u[1:]) + np.abs(u[:-1])) * np.diff(grid))])
        after = t >= t_cmd
        pre = (t >= t_cmd - 0.05) & (t < t_cmd)
        row = {"name": b.name, "p_r_set": p_r / 1e5, "p_h_set": p_h / 1e5, "F_s": fs, "v_mm_s": v * 1e3, "mode": mode, "p_r_pre": float(res["p_r"][pre].mean()), "p_h_pre": float(res["p_h"][pre].mean()),
               "line_a_pre": float(res["line_a"][pre].mean()), "line_b_pre": float(res["line_b"][pre].mean()), "rod_open_pre": float(res["open_b"][pre].mean()), "F_pre_kN": float(res["F"][pre].mean() / 1e3)}
        j_rod = np.flatnonzero(after & (res["open_b"] > 0.5))
        if j_rod.size:
            j = j_rod[0]
            row.update({"t_rod_s": float(t[j] - t_cmd), "stroke_rod_mm": float(np.interp(t[j], grid, delivered) * 1e3), "line_a_at_rod": float(res["line_a"][j]), "line_b_at_rod": float(res["line_b"][j]), "p_r_at_rod": float(res["p_r"][j])})
            # rod fall after the opening: 63 % of the way to line B at tank
            p0 = float(res["p_r"][j])
            target = P_T / 1e5 + 0.37 * (p0 - P_T / 1e5)
            k = np.flatnonzero((t > t[j]) & (res["p_r"] < target))
            row["rod_fall_63_s"] = float(t[k[0]] - t[j]) if k.size else None
        j_head = np.flatnonzero(after & (res["open_a"] > 0.5))
        if j_head.size:
            j = j_head[0]
            row.update({"t_head_s": float(t[j] - t_cmd), "stroke_head_mm": float(np.interp(t[j], grid, delivered) * 1e3), "line_a_at_head": float(res["line_a"][j]), "line_b_at_head": float(res["line_b"][j]), "p_h_at_head": float(res["p_h"][j]), "p_r_at_head": float(res["p_r"][j])})
        x = res["x"]
        moved = np.flatnonzero(after & ((x - x[pre].mean()) > 2e-4))
        row["t_move_0p2_s"] = float(t[moved[0]] - t_cmd) if moved.size else None
        Fw = res["F"][after] / 1e3
        row.update({"F_min_kN": float(Fw.min()), "F_max_kN": float(Fw.max()), "F_end_kN": float(Fw[-1]), "p_h_min": float(res["p_h"][after].min()), "p_r_end": float(res["p_r"][after][-1])})
        # force change at the rod opening: 0.2 s window
        if j_rod.size:
            w = (t >= t[j_rod[0]]) & (t <= t[j_rod[0]] + 0.2)
            row["dF_max_0p2s_kN"] = float(res["F"][w].max() / 1e3 - row["F_pre_kN"])
            row["dF_min_0p2s_kN"] = float(res["F"][w].min() / 1e3 - row["F_pre_kN"])
        row["rule"] = rule(p, p_r, p_h, fs, v, mode, A_h)
        if row.get("stroke_rod_mm") and row["rule"]["stroke_rod_mm"]:
            row["rel_stroke_rod"] = row["stroke_rod_mm"] / row["rule"]["stroke_rod_mm"] - 1.0
        rows.append(row)
    (OUT / "early_unit.json").write_text(json.dumps(rows, indent=0), encoding="utf-8")
    print("name | rod_pre t_rod stroke rule_stroke pA pA_rule | t_head stroke_head rule_head | fall63 dF+ dF- | p_h_min F_end")
    def fmt(x, n=2):
        return "None" if x is None else f"{x:.{n}f}"
    for r in rows:
        ru = r["rule"]
        print(r["name"], "|", fmt(r["rod_open_pre"], 1), fmt(r.get("t_rod_s"), 3), fmt(r.get("stroke_rod_mm"), 3), fmt(ru["stroke_rod_mm"], 3), fmt(r.get("line_a_at_rod"), 1), f"{ru['p_A_rule'] / 1e5:.1f}", "|", fmt(r.get("t_head_s"), 3), fmt(r.get("stroke_head_mm"), 3), fmt(ru["stroke_head_mm"], 3), fmt(r.get("line_a_at_head"), 1), "|", fmt(r.get("rod_fall_63_s"), 3), fmt(r.get("dF_max_0p2s_kN"), 1), fmt(r.get("dF_min_0p2s_kN"), 1), "|", fmt(r["p_h_min"], 1), fmt(r["F_end_kN"], 1), flush=True)


if __name__ == "__main__":
    main()
