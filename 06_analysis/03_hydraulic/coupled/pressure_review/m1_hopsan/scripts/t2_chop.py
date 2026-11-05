"""Task 2: a 10 Hz chopped retract command around the 2 % spool opening: how much does the line really empty?

Hopsan single leg against three one-state rules: the harness M1 rule (empty below 2 %), the literal rule (empty only at
|u| <= eps), and the proposed drain state M1b.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from bench import REAR_FS_SCALE, Bench, formula, geometry, load_params, open_metrics, pin, run_many

OUT = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\pressure_review\m1_hopsan")
HERE = Path(__file__).resolve().parent
TS_CMD = 0.1
TAU_V = 0.1
EPS = 1e-6
CQ, RHO = 0.67, 860.0


def pattern(name: str, n_max: int = 120) -> np.ndarray:
    """Command magnitudes per 0.1 s sample [mm/s], retract."""
    base = {
        "const0.84": [0.84], "const0.45": [0.45], "const0.35": [0.35],
        "alt0.84_0": [0.84, 0.0], "alt1.05_0.3": [1.05, 0.3],
        "5h1z": [1.05] * 5 + [0.0], "5h3z": [1.05] * 5 + [0.0] * 3, "5h5z": [1.05] * 5 + [0.0] * 5,
        "5h3low": [1.05] * 5 + [0.3] * 3, "5h5low": [1.05] * 5 + [0.3] * 5, "alt0.5_0.35": [0.5, 0.35], "alt0.6_0.25": [0.6, 0.25],
        "10h5z": [0.84] * 10 + [0.0] * 5, "guard3_rel": [5.2] * 2 + [0.3] * 3,
    }[name]
    return np.resize(np.array(base), n_max) * 1e-3


def rules(cmd_mm: np.ndarray, need_mm: float, v_max: float, a_r: float, a_full: float, p_T: float, p_open: float, close=0.02, neutral_fraction=0.05):
    """Open times [s] of the one-state rules; all with the lagged valve output on a 1 ms chunk."""
    dt = 1e-3
    n = int(len(cmd_mm) * TS_CMD / dt)
    cmd = np.repeat(cmd_mm, int(TS_CMD / dt))[:n]
    need = need_mm * 1e-3
    u = 0.0
    keep = np.exp(-dt / TAU_V)
    k_n = neutral_fraction * CQ * a_full * np.sqrt(2.0 / RHO)
    fill_rule = fill_lit = fill_b = 0.0
    above = False
    t_rule = t_lit = t_b = None
    pl_rise = p_open - p_T
    for k in range(n):
        u = cmd[k] + (u - cmd[k]) * keep
        t = (k + 1) * dt
        # harness rule
        if u <= EPS or (above and u < close * v_max):
            fill_rule = 0.0
            above = False
        elif u >= close * v_max:
            above = True
        if t_rule is None and u > EPS:
            fill_rule += u * dt
            if fill_rule >= need:
                t_rule = t
        # literal rule
        if u <= EPS:
            fill_lit = 0.0
        elif t_lit is None:
            fill_lit += u * dt
            if fill_lit >= need:
                t_lit = t
        # drain state: pressure rises in proportion to the filled stroke
        frac = u / v_max
        k_v = k_n * max(1.0 - frac / close, 0.0)
        p_line = pl_rise * max(fill_b, 0.0) / need
        drain = k_v * np.sqrt(max(p_line, 0.0)) / a_r
        fill_b = max(fill_b + (u - drain) * dt, 0.0)
        if t_b is None and fill_b >= need:
            t_b = t
    return t_rule, t_lit, t_b


def main() -> None:
    pin()
    p = load_params()
    work = HERE / "t2"
    names = ["const0.84", "const0.45", "const0.35", "alt0.84_0", "alt1.05_0.3", "5h1z", "5h3z", "5h5z", "5h3low", "5h5low", "alt0.5_0.35", "alt0.6_0.25", "10h5z", "guard3_rel"]
    variants = {
        "vent": dict(),
        "vent_ref": dict(pilot_ref_b=True),
        "vent_close1pc": dict(vent_close=0.01),
        "vent_close5pc": dict(vent_close=0.05),
        "block": dict(neutral="block"),
    }
    leg = 2
    benches = []
    for vname, kw in variants.items():
        for pname in names:
            for fs0 in (0.0, 4e3):
                c = pattern(pname)
                # command ends at 12 s
                t = np.arange(len(c)) * TS_CMD
                b = Bench(f"RL_{vname}_{pname}_{fs0 / 1e3:g}", leg, 115e5, F_s=fs0 * REAR_FS_SCALE, cmd_t=np.append(t, t[-1] + TS_CMD), cmd_u=np.append(-c, 0.0), **kw)
                benches.append((b, vname, pname, fs0))
    print("runs", len(benches), flush=True)
    results = run_many([b for b, *_ in benches], p, work)
    rows = []
    for (b, vname, pname, fs0), (_, res) in zip(benches, results):
        m = open_metrics(b, res)
        A_h, A_r, s0, _ = geometry(p, b.leg)
        a_full = A_h * p.v_max / np.sqrt(p.dp_comp) / (CQ * np.sqrt(2.0 / RHO))
        t = res["t"]
        tc = res["t_cmd"]
        # Hopsan open uses delivered flow; need for the rules from the matching constant run (0.05 v_max, t1 table logic):
        f = formula(b, p, m["p_h_pre"], m["p_r_pre"])
        need = f["retract"]
        t_rule, t_lit, t_b = rules(pattern(pname), need, p.v_max, A_r, a_full, b.p_T, f["p_open"] * 1e5, close=b.vent_close)
        win = (t >= tc) & (t < tc + (m["t_open_s"] if m["t_open_s"] == m["t_open_s"] else 12.0))
        lb = res["line_b"][win]
        # line pressure drop after each local peak before the opening
        peak = np.maximum.accumulate(lb) if lb.size else np.array([0.0])
        drops = float(np.max(peak - lb)) if lb.size else 0.0
        rows.append({"variant": vname, "pattern": pname, "fs0_kN": fs0 / 1e3, "need_mm": need, "p_open": f["p_open"], "p_h_pre": m["p_h_pre"], "p_r_pre": m["p_r_pre"],
                     "t_open_hopsan": m["t_open_s"], "t_open_rule": t_rule, "t_open_literal": t_lit, "t_open_drain": t_b,
                     "line_b_max": float(lb.max()) if lb.size else None, "line_b_max_drop": drops, "p_r_max_before_open": float(res["p_r"][win].max()) if lb.size else None,
                     "wall_s": res["wall_s"]})
        np.savez_compressed(work / f"{b.name}.npz", t=t[::10], lb=res["line_b"][::10], pr=res["p_r"][::10], ph=res["p_h"][::10], a=res["open_a"][::10], u=np.interp(t[::10], res["grid"], res["u"]))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t2_chop.json").write_text(json.dumps(rows, indent=0), encoding="utf-8")
    for r in rows:
        if r["fs0_kN"] == 0.0:
            print(r["variant"], r["pattern"], "need", round(r["need_mm"], 2), "| hop", None if r["t_open_hopsan"] != r["t_open_hopsan"] else round(r["t_open_hopsan"], 2), "rule", r["t_open_rule"], "lit", r["t_open_literal"], "drain", r["t_open_drain"], "| lineB max", round(r["line_b_max"], 1), "drop", round(r["line_b_max_drop"], 1), "pr max", round(r["p_r_max_before_open"], 1), flush=True)


if __name__ == "__main__":
    main()
