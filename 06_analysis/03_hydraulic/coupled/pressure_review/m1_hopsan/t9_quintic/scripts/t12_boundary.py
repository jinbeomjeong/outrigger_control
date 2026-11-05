"""Does the head check open together with the rod check? Prediction written before the run:

together if p_A,rod + psi p_B,eq >= p_h + p_cr, p_A,rod = (p_r + p_cr - p_T) / psi, p_B,eq = (C_r p_r + C_l p_T) / (C_r + C_l),
C_r = V_r / beta, C_l = V_line / beta_h. Otherwise the head check waits for its own line pressure p_h + F_s / A_h + p_cr.
Also the rod fall time: step to p_B,eq, then C dp/dt = A_r v - K_land (v / v_max) sqrt(p - p_T), C = C_r + C_l + C_h.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from bench import BETA_HOSE, PSI, REAR_FS_SCALE, V_LINE, Bench, geometry, load_params, pin, run_many

OUT = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\pressure_review\m1_hopsan\t9_quintic")
HERE = Path(__file__).resolve().parent
LEG = 3
P_T, P_CR = 2e5, 3e5
STATES = ((8e5, 30e5), (12e5, 50e5), (12e5, 30e5), (20e5, 80e5), (20e5, 60e5), (20e5, 40e5), (30e5, 100e5), (30e5, 80e5), (30e5, 60e5), (45e5, 100e5))
SPEEDS = (1.05e-3, 5.2e-3)


def compliances(p):
    A_h, A_r, s0, _ = geometry(p, LEG)
    c_r = A_r * (p.L0r + p.stroke - s0) / p.beta
    c_l = V_LINE / BETA_HOSE
    c_h = A_r**2 * (p.L0h + s0) / (p.beta * A_h)
    return A_h, A_r, c_r, c_l, c_h


def predict(p, p_r, p_h, fs):
    A_h, A_r, c_r, c_l, _ = compliances(p)
    p_a = (p_r + P_CR - P_T) / PSI
    p_eq = (c_r * p_r + c_l * P_T) / (c_r + c_l)
    together = p_a + PSI * p_eq >= p_h + P_CR
    d_rod = V_LINE * max(p_a - P_T, 0.0) / BETA_HOSE / A_h
    d_head = V_LINE * max(p_h + fs / A_h + P_CR - P_T, 0.0) / BETA_HOSE / A_h
    return {"together": bool(together), "p_A_rod_bar": p_a / 1e5, "p_B_eq_bar": p_eq / 1e5, "d_rod_mm": d_rod * 1e3, "d_head_mm": d_head * 1e3, "d_head_effective_mm": (d_rod if together else max(d_rod, d_head)) * 1e3}


def fall_law(p, p_r, v):
    A_h, A_r, c_r, c_l, c_h = compliances(p)
    k_land = A_h * p.v_max / np.sqrt(p.dp_comp)
    y = (c_r * p_r + c_l * P_T) / (c_r + c_l)
    target = P_T + 0.37 * (p_r - P_T)
    t, dt = 0.0, 1e-4
    while y > target and t < 10.0:
        y += (A_r * v - k_land * (v / p.v_max) * np.sqrt(max(y - P_T, 0.0))) / (c_r + c_l + c_h) * dt
        t += dt
    return t


def main():
    pin()
    p = load_params()
    A_h, A_r, *_ = compliances(p)
    jobs = []
    for p_r, p_h in STATES:
        for fs0 in (0.0, 4e3):
            fs = fs0 * REAR_FS_SCALE
            for v in SPEEDS:
                F = A_h * p_h - A_r * p_r
                b = Bench(f"B_pr{p_r / 1e5:g}_ph{p_h / 1e5:g}_Fs{fs0 / 1e3:g}_v{v * 1e3:g}", LEG, None, F_s=fs, start="static", p_r0=p_r, F_load=F, cmd_t=np.array([0.0, min(0.004 / v, 4.0)]), cmd_u=np.array([v, 0.0]), t_after=0.3)
                jobs.append((b, p_r, p_h, fs, v))
    results = run_many([j[0] for j in jobs], p, HERE / "t12")
    rows = []
    for (b, p_r, p_h, fs, v), (_, res) in zip(jobs, results):
        t, tc = res["t"], res["t_cmd"]
        grid, u = res["grid"], res["u"]
        delivered = np.concatenate([[0.0], np.cumsum(0.5 * (np.abs(u[1:]) + np.abs(u[:-1])) * np.diff(grid))])
        after = t >= tc
        pre = (t >= tc - 0.05) & (t < tc)
        pr_pre = res["p_r"][pre].mean()
        row = {"name": b.name, "p_r": p_r / 1e5, "p_h": p_h / 1e5, "F_s": fs, "v_mm_s": v * 1e3, "p_r_pre": float(pr_pre), "rod_open_pre": float(res["open_b"][pre].mean()), "predict": predict(p, p_r, p_h, fs)}
        jr = np.flatnonzero(after & (res["open_b"] > 0.5))
        ja = np.flatnonzero(after & (res["open_a"] > 0.5))
        if jr.size:
            row.update({"t_rod": float(t[jr[0]] - tc), "stroke_rod": float(np.interp(t[jr[0]], grid, delivered) * 1e3), "line_a_rod": float(res["line_a"][jr[0]])})
        if ja.size:
            row.update({"t_head": float(t[ja[0]] - tc), "stroke_head": float(np.interp(t[ja[0]], grid, delivered) * 1e3), "line_a_head": float(res["line_a"][ja[0]]), "line_b_head": float(res["line_b"][ja[0]]), "p_h_head": float(res["p_h"][ja[0]])})
        if jr.size:
            target = P_T / 1e5 + 0.37 * (p_r / 1e5 - P_T / 1e5)
            k = np.flatnonzero((t > t[jr[0]]) & (res["p_r"] < target))
            row["fall63"] = float(t[k[0]] - t[jr[0]]) if k.size else None
            row["fall63_law"] = float(fall_law(p, p_r, v))
        rows.append(row)
    (OUT / "early_boundary.json").write_text(json.dumps(rows, indent=0), encoding="utf-8")
    print("p_r p_h Fs v | predict together, d_rod, d_head | hopsan rod stroke, head stroke, sep_s | stroke_head / d_eff | fall63, law")
    bad = 0
    errs = []
    ratios = []
    for r in rows:
        q = r["predict"]
        sep = r.get("t_head", np.nan) - r.get("t_rod", np.nan)
        actual_together = sep < 0.01
        bad += actual_together != q["together"]
        e = r.get("stroke_head", np.nan) / q["d_head_effective_mm"] - 1.0
        errs.append(e)
        if r.get("fall63") and r.get("fall63_law"):
            ratios.append(r["fall63"] / r["fall63_law"])
        print(r["p_r"], r["p_h"], int(r["F_s"]), r["v_mm_s"], "|", q["together"], round(q["d_rod_mm"], 3), round(q["d_head_mm"], 3), "|", round(r.get("stroke_rod", np.nan), 3), round(r.get("stroke_head", np.nan), 3), round(sep, 3), "|", round(e, 3), "|", r.get("fall63") and round(r["fall63"], 3), round(r.get("fall63_law", np.nan), 3))
    print("wrong together/separate", bad, "of", len(rows), "head stroke rel max", round(float(np.nanmax(np.abs(errs))), 3), "fall ratio", round(min(ratios), 2), round(max(ratios), 2))
    # re-check the fall law on the earlier unit table
    early = json.loads((OUT / "early_unit.json").read_text(encoding="utf-8"))
    q = [r["rod_fall_63_s"] / fall_law(p, r["p_r_set"] * 1e5, r["v_mm_s"] * 1e-3) for r in early if r.get("rod_fall_63_s") and r["mode"] in ("vent", "vent_ref", "block_lowA")]
    print("early table fall ratio", len(q), round(min(q), 2), round(float(np.median(q)), 2), round(max(q), 2))
    print("law at 0.25 mm/s p_r 65", round(fall_law(p, 65e5, 0.25e-3), 2), " 0.5:", round(fall_law(p, 65e5, 0.5e-3), 2), " 1.05:", round(fall_law(p, 65e5, 1.05e-3), 2), " 5.2:", round(fall_law(p, 65e5, 5.2e-3), 3))


if __name__ == "__main__":
    main()
