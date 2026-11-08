"""Open-loop SCM lift J1 B: VB proportional law vs VB priority / V0 / v4-stored (user decision 2026-11-08 H-1).

The v4 table 7 items come from ``openloop_compare.analyse`` (same definitions: the definition part of
``openloop_compare.py`` is executed, so both comparisons share one definition). Added here: per-leg speed ratio v/u
from ``flow_series.npz`` (1 ms rows), leg touch-down times, stroke spread, and the hydraulics-expert prediction check
(proportional: one ratio on all legs = supply / demand, stroke spread 0, J_F 0).
argv: <out json>
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

SRC = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\paper_runs\scripts\openloop_compare.py")
src_text = SRC.read_text("utf-8")
ns: dict = {}
exec(compile(src_text.split('\nout = {"runs"')[0], str(SRC), "exec"), ns)  # definitions only
analyse, F_MIN, T_LIFT = ns["analyse"], ns["F_MIN"], ns["T_LIFT"]

R = Path(r"C:\workspace\outrigger_control\07_results\S9")
RUNS = {
    "J1_prop": R / "batch_V5-OPENLOOP-VB-PROP_20261108_164953/P3a_J1_B_VB_prop",
    "J1_VB": R / "batch_V5-OPENLOOP-VB_20261108_112044/P3a_J1_B_VB",
    "J1_V0": R / "batch_V5-OPENLOOP-V0_20261108_123517/P3a_J1_B_V0",
    "J1_v4": R / "batch_P3a_20261026_092653/P3a_J1_B",
}
if len(sys.argv) > 2:  # dry check of the script on another run folder
    RUNS["J1_prop"] = Path(sys.argv[2])
LEGS = ("FL", "FR", "RL", "RR")
V_MAX = 0.020924  # m/s, YAML actuator.max_speed_m_s
T_END = 36.0


def speed_metrics(path: Path) -> dict:
    f = np.load(path / "flow_series.npz")
    cols = [str(c) for c in f["columns"]]
    ci = {c: i for i, c in enumerate(cols)}
    rows = f["rows"]
    supply = float(f["supply_m3_s"])
    t = rows[:, 0]
    u = np.stack([rows[:, ci[f"u_{l}"]] for l in LEGS], axis=1)
    v = np.stack([rows[:, ci[f"v_{l}"]] for l in LEGS], axis=1)
    p = np.stack([rows[:, ci[f"p_load_{l}"]] for l in LEGS], axis=1)
    lift = (t > T_LIFT + 0.5) & (t <= T_END)  # skip the command ramp + valve lag start
    act = lift[:, None] & (u >= 0.1 * V_MAX)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = np.where(act, v / u, np.nan)
    all4 = act.all(axis=1)
    spread = np.ptp(r[all4], axis=1)
    out = {
        "supply_L_min": supply * 6e4,
        "Q_dem_max_L_min": float(np.nanmax(rows[lift, ci["Q_dem"]]) * 6e4),
        "ratio_window": "8.5 s < t <= 36 s, u >= 0.1 v_max",
        "ratio_by_leg": {l: {"median": float(np.nanmedian(r[:, i])), "min": float(np.nanmin(r[:, i])),
                             "max": float(np.nanmax(r[:, i])), "p01": float(np.nanpercentile(r[:, i], 1))}
                         for i, l in enumerate(LEGS)},
        "ratio_spread_all4": {"rows": int(all4.sum()), "max": float(spread.max()), "median": float(np.median(spread)),
                              "p99": float(np.percentile(spread, 99))},
        "Q_sum_over_supply_max": float(np.nanmax(rows[lift, ci["Q_sum"]]) / supply),
    }
    fe = (t >= 10.0) & (t < 20.0)
    out["free_speed_10_20s_mm_s"] = {l: float(v[fe, i].mean() * 1e3) for i, l in enumerate(LEGS)}
    snaps = {}
    for tq in (15.0, 26.0, 26.3, 27.0, 30.0, 33.0, 35.9):
        k = min(int(np.searchsorted(t, tq - 1e-9)), len(t) - 1)
        snaps[f"{t[k]:.3f}"] = {"v_mm_s": (v[k] * 1e3).round(3).tolist(),
                                "p_load_bar": (p[k] / 1e5).round(2).tolist()}
    out["snapshots"] = snaps
    # J_F proxy: least-squares slope of the per-leg ratio deviation on the per-leg load pressure deviation
    # (all-4-active rows); 0 when the ratio does not depend on the load pressure
    rr, pp = r[all4], p[all4]
    dr = rr - rr.mean(axis=1, keepdims=True)
    dp = pp - pp.mean(axis=1, keepdims=True)
    den = float(np.sum(dp * dp))
    out["J_F_proxy_ratio_per_bar"] = float(np.sum(dr * dp) / den * 1e5) if den > 0 else 0.0
    return out


def touch_and_stroke(path: Path) -> dict:
    z = np.load(path / "series.npz")
    t, fc, sm = z["t_s"], z["F_cyl_N"], z["s_motor_m"]
    lift = t > T_LIFT + 1e-9
    touch = {}
    for i, l in enumerate(LEGS):
        idx = np.nonzero(lift & (fc[:, i] > 1.4 * F_MIN))[0]
        touch[l] = float(t[idx[0]]) if idx.size else None
    sp = np.ptp(sm, axis=1) * 1e3
    gap = (None if None in touch.values()
           else 0.5 * (touch["FL"] + touch["FR"]) - 0.5 * (touch["RL"] + touch["RR"]))
    return {"touch_1p4Fmin_s": touch, "touch_gap_front_minus_rear_s": gap,
            "stroke_spread_end_mm": float(sp[-1]), "stroke_spread_max_lift_mm": float(sp[lift].max())}


out = {"definition_source": {"file": str(SRC), "sha256": hashlib.sha256(src_text.encode()).hexdigest()},
       "runs": {}, "speed": {}, "touch_stroke": {}}
for name, p in RUNS.items():
    o, _ = analyse(p)
    res = json.loads((p / "result.json").read_text("utf-8"))
    o["args_flow_law"] = res.get("args", {}).get("flow_law")
    out["runs"][name] = o
    out["touch_stroke"][name] = touch_and_stroke(p)
    if (p / "flow_series.npz").exists():
        out["speed"][name] = speed_metrics(p)
b = json.loads((RUNS["J1_prop"].parent / "batch.json").read_text("utf-8"))
out["batch_prop"] = {c["case"]: {"rc": c.get("rc"), "wall_s": c.get("wall_s"), "pool": c.get("pool")}
                     for c in b["cases"]}
sp = out["speed"]["J1_prop"]
pred = sp["supply_L_min"] / sp["Q_dem_max_L_min"]
out["prediction_check"] = {
    "source": "hydraulics-expert: proportional -> one ratio 0.8948 on all legs, stroke spread 0, J_F 0",
    "predicted_ratio_0p8948": 0.8948, "supply_over_demand_this_run": pred,
    "ratio_median_by_leg": {l: sp["ratio_by_leg"][l]["median"] for l in LEGS},
    "ratio_dev_from_0p8948_max": max(abs(sp["ratio_by_leg"][l]["median"] - 0.8948) for l in LEGS),
    "ratio_spread_all4_max": sp["ratio_spread_all4"]["max"],
    "stroke_spread_end_mm": out["touch_stroke"]["J1_prop"]["stroke_spread_end_mm"],
    "J_F_proxy_ratio_per_bar": sp["J_F_proxy_ratio_per_bar"],
}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, default=float), "utf-8")
print("ok")
