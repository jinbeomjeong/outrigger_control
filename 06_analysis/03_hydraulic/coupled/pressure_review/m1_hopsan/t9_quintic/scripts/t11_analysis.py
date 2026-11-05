"""Unit statistics of the early release runs, a sqrt-orifice release law against the measured rod fall, trajectories, convergence."""
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np
import bench
import t4_replay as t4
import t9_replay as t9
from bench import BETA_HOSE, TAU_V, V_LINE, Bench, geometry, load_params, pin, run

BASE = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\pressure_review")
OUT = BASE / "m1_hopsan" / "t9_quintic"


def release_law(p, leg, p_r0, v, line_b_fill=True, dt=1e-4):
    """Time for p_r to fall 63 % towards p_T after the rod check opens, extending at v. Rod, line B and head compliance in parallel."""
    A_h, A_r, s0, _ = geometry(p, leg)
    C = A_r * (p.L0r + p.stroke - s0) / p.beta + V_LINE / BETA_HOSE + A_r**2 * A_h * (p.L0h + s0) / (p.beta * A_h**2)
    k_land = A_h * p.v_max / np.sqrt(p.dp_comp)
    p_T = 2e5
    target = p_T + 0.37 * (p_r0 - p_T)
    # the command is near its value (lag elapsed for all but the fastest); oil driven out by the extension itself: A_r v
    y, t = p_r0, 0.0
    while y > target and t < 10.0:
        q = k_land * (v / p.v_max) * np.sqrt(max(y - p_T, 0.0))
        y += (A_r * v - q) / C * dt
        t += dt
    return t if y <= target else None


def main():
    pin()
    p = load_params()
    rows = json.loads((OUT / "early_unit.json").read_text(encoding="utf-8"))
    out = {}
    st = defaultdict(list)
    none_ok = none_bad = 0
    same = []
    fall = defaultdict(list)
    table = []
    for r in rows:
        ru = r["rule"]
        if r["mode"] == "block_trapA":
            continue
        hop = r.get("stroke_rod_mm")
        if hop is None and ru["stroke_rod_mm"] is None:
            none_ok += 1
        elif hop is None or ru["stroke_rod_mm"] is None:
            none_bad += 1
        else:
            st[r["mode"]].append(abs(hop / ru["stroke_rod_mm"] - 1.0))
            same.append((r["stroke_head_mm"], ru["stroke_head_mm"], hop, r["t_head_s"] - r["t_rod_s"]))
            law = release_law(p, 3, r["p_r_at_rod"] * 1e5, r["v_mm_s"] * 1e-3)
            if r.get("rod_fall_63_s") and law:
                fall[r["F_s"] > 0].append((r["rod_fall_63_s"], law))
                table.append({"name": r["name"], "fall63": r["rod_fall_63_s"], "law": law})
    out["rod_stroke_rel"] = {m: {"n": len(x), "max": max(x), "median": float(np.median(x))} for m, x in st.items()}
    out["open_outcome"] = {"both_never": none_ok, "wrong": none_bad}
    same = np.array(same)
    out["head_with_rod"] = {"n": len(same), "head_after_rod_s_max": float(same[:, 3].max()), "hopsan_head_stroke_mm_mean": float(same[:, 0].mean()), "rule_head_stroke_mm_mean": float(same[:, 1].mean()),
                            "ratio_hopsan_head_to_rule_head_max": float((same[:, 0] / same[:, 1]).max())}
    print(json.dumps(out, indent=1))
    for k, v in fall.items():
        a = np.array(v)
        print("friction" if k else "no friction", "n", len(a), "measured/law min max", np.round((a[:, 0] / a[:, 1]).min(), 2), np.round((a[:, 0] / a[:, 1]).max(), 2))
    out["fall_vs_law"] = table
    print("rod fall 63 % by speed, RR p_r 65, F_s 0, vent [s]: measured / law")
    for r in rows:
        if r["p_r_set"] in (30, 65) and r["F_s"] == 0 and r["mode"] == "vent" and r.get("rod_fall_63_s"):
            print("  ", r["p_r_set"], r["v_mm_s"], round(r["rod_fall_63_s"], 3), round(release_law(p, 3, r["p_r_at_rod"] * 1e5, r["v_mm_s"] * 1e-3), 3), "t_rod", round(r["t_rod_s"], 3), "move0.2", r.get("t_move_0p2_s"), "line at head", round(r["line_a_at_head"], 1), "lb at head", round(r["line_b_at_head"], 1))
    print("p_r 30, 5.2, low p_r cross check: head with rod needs line B", {"p_r30": rows[16]["line_b_at_head"]})
    # harness and Hopsan no-check before and after the first command
    traj = {}
    for off in (0.0, 0.025, 0.05, 0.075):
        h = np.load(BASE / "m1b" / "series_r12" / f"R12_OFF_{off}.npz")
        d = np.load(HERE / "t9" / f"nocheck_OFF_{off}.npz")
        row = {}
        for v in (0.3, 0.5, 0.7, 0.85, 1.0, 1.2, 1.4, 1.5, 1.6, 1.8, 2.0):
            row[f"+{v:g}"] = (round(float(h["F"][int(np.searchsorted(h["t"], v)), 3] / 1e3), 2), round(float(d["F"][int(np.argmin(np.abs(d["t"] - v))), 3] / 1e3), 2))
        traj[off] = row
    out["RR_harness_vs_nocheck"] = traj
    print("RR load (harness, Hopsan no check), offset 0.025", traj[0.025])
    # convergence: half step
    for variant in ("OFF", "V1", "B1"):
        t9.FITS[(variant, 0.025)] = t9.event_fit(variant, 0.025)
    t4.TS = 5e-6
    work = HERE / "t9c"
    work.mkdir(exist_ok=True)
    base = {(r["circuit"], r["commands"], r["offset"]): r for r in json.loads((OUT / "replay.json").read_text(encoding="utf-8"))}
    jobs = [(f"c_{c}_{v}", c, v, 0.025) for c, v in (("nocheck", "OFF"), ("vent", "V1"), ("vent_ref", "V1"), ("block", "B1"))]
    with ThreadPoolExecutor(4) as pool:
        conv = list(pool.map(lambda j: t9.run_one(j, p, work), jobs))
    out["replay_conv"] = []
    for r in conv:
        b = base[(r["circuit"], r["commands"], 0.025)]
        row = {"case": r["name"], "RR_1e-5": b["F_min_kN"]["RR"], "RR_5e-6": r["F_min_kN"]["RR"], "pr_RR_1.4_1e-5": b["marks"]["+1.4"]["p_r"][3], "pr_RR_1.4_5e-6": r["marks"]["+1.4"]["p_r"][3]}
        out["replay_conv"].append(row)
        print(row)
    bench.TS = 5e-6
    A_h, A_r, _s, _ = geometry(p, 3)
    out["unit_conv"] = []
    for pr_, ph_, v, kw in ((65e5, 29e5, 1.05e-3, {}), (30e5, 50e5, 5.2e-3, {"pilot_ref_b": True})):
        b = Bench(f"cu_{pr_ / 1e5:g}", 3, None, F_s=0.0, start="static", p_r0=pr_, F_load=A_h * ph_ - A_r * pr_, cmd_t=np.array([0.0, min(0.003 / v, 6.0)]), cmd_u=np.array([v, 0.0]), t_after=0.3, **kw)
        res = run(b, p, HERE / "t10c")
        t, tc = res["t"], res["t_cmd"]
        delivered = np.concatenate([[0.0], np.cumsum(0.5 * (np.abs(res["u"][1:]) + np.abs(res["u"][:-1])) * np.diff(res["grid"]))])
        j = np.flatnonzero((t >= tc) & (res["open_b"] > 0.5))[0]
        ref = next(x for x in rows if x["p_r_set"] == pr_ / 1e5 and x["F_s"] == 0 and x["v_mm_s"] == v * 1e3 and x["mode"] == ("vent_ref" if kw else "vent"))
        row = {"case": b.name, "stroke_5e-6": float(np.interp(t[j], res["grid"], delivered) * 1e3), "stroke_1e-5": ref["stroke_rod_mm"]}
        out["unit_conv"].append(row)
        print(row)
    (OUT / "early_analysis.json").write_text(json.dumps(out, indent=0, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
