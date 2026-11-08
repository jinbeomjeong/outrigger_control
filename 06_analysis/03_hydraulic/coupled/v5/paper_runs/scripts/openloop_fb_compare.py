"""Open-loop SCM lift J1 B, F-6 (FB flow budget: lift speed fraction 0.87684, lift 31.93 s, end 39.93 s):
VB_FB / V0_FB added to the v4 / V0 / VB priority / VB proportional comparison.

Table 7 items: ``openloop_compare.analyse`` (definition part of openloop_compare.py executed, SHA-256 recorded;
its windows use the series end, so the 39.93 s end of the FB rows is taken as is).
Speed ratio: flow_series.npz v/u, window 8.5 s < t <= series end, u >= 0.1 v_max (the 36 s end of
openloop_prop_compare.py replaced by the run end). V0-plant rows have no flow series: the speed is the
argv fraction (checked from ds_motor/dt in free extension).
Mechanism checks (dynamics-expert items 1-7 of the prop dip analysis, prop_dip_*.py): rear / front contact
(swivel events), commanded stroke between them, rear peak before front contact and ratio to V0, rear force at
front contact, crawler front-end sinkage (body point x = +1.30 m) at equal time after rear contact, dip from
front contact to the rear minimum, the pre-liftoff window start t_first_above (1.4 F_min), flow-limit activity,
valve ramp, lift-off time vs 19.086 / fraction, and the linear R*u estimate F_min_rear = 11.70 - 23.4 (1 - r).
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
FB = R / "batch_V5-OPENLOOP-FB_20261108_183849"
RUNS = {
    "J1_v4": (R / "batch_P3a_20261026_092653/P3a_J1_B", 1.0),
    "J1_V0": (R / "batch_V5-OPENLOOP-V0_20261108_123517/P3a_J1_B_V0", 1.0),
    "J1_VB": (R / "batch_V5-OPENLOOP-VB_20261108_112044/P3a_J1_B_VB", None),
    "J1_prop": (R / "batch_V5-OPENLOOP-VB-PROP_20261108_164953/P3a_J1_B_VB_prop", None),
    "J1_V0_FB": (FB / "P3a_J1_B_V0_FB", 0.87684),
    "J1_VB_FB": (FB / "P3a_J1_B_VB_FB", None),
}
LEGS = ("FL", "FR", "RL", "RR")
V_MAX = 0.020924
XF = 1.30
T_LIFTOFF_V0_AFTER_START = 19.085999999950214


def speed_metrics(path, t_end):
    f = np.load(path / "flow_series.npz")
    cols = [str(c) for c in f["columns"]]
    ci = {c: i for i, c in enumerate(cols)}
    rows = f["rows"]
    supply = float(f["supply_m3_s"])
    t = rows[:, 0]
    u = np.stack([rows[:, ci[f"u_{l}"]] for l in LEGS], axis=1)
    v = np.stack([rows[:, ci[f"v_{l}"]] for l in LEGS], axis=1)
    lim = rows[:, ci["limited_mask"]]
    lift = (t > T_LIFT + 0.5) & (t <= t_end)
    act = lift[:, None] & (u >= 0.1 * V_MAX)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = np.where(act, v / u, np.nan)
    all4 = act.all(axis=1)
    spread = np.ptp(r[all4], axis=1)
    # valve ramp: time from lift start until v >= 0.99 of its 10-20 s mean
    fe = (t >= 10.0) & (t < 20.0)
    vfree = v[fe].mean(axis=0)
    k99 = [int(np.nonzero((t > T_LIFT) & (v[:, i] >= 0.99 * vfree[i]))[0][0]) for i in range(4)]
    return {
        "supply_L_min": supply * 6e4,
        "Q_dem_max_L_min": float(np.nanmax(rows[lift, ci["Q_dem"]]) * 6e4),
        "Q_sum_max_L_min": float(np.nanmax(rows[lift, ci["Q_sum"]]) * 6e4),
        "limited_rows": int(np.count_nonzero(lim[lift])),
        "ratio_window": f"8.5 s < t <= {t_end:.2f} s, u >= 0.1 v_max",
        "u_median_mm_s": {l: float(np.nanmedian(np.where(act[:, i], u[:, i], np.nan)) * 1e3) for i, l in enumerate(LEGS)},
        "ratio_by_leg": {l: {"median": float(np.nanmedian(r[:, i])), "min": float(np.nanmin(r[:, i])),
                             "max": float(np.nanmax(r[:, i]))} for i, l in enumerate(LEGS)},
        "ratio_spread_all4_max": float(spread.max()) if spread.size else None,
        "free_speed_10_20s_mm_s": {l: float(vfree[i] * 1e3) for i, l in enumerate(LEGS)},
        "valve_ramp_to_99pct_s": [float(t[k] - T_LIFT) for k in k99],
    }


def mechanism(path, frac_hint):
    res = json.loads((path / "result.json").read_text("utf-8"))
    z = np.load(path / "series.npz")
    t, fc, sm = z["t_s"], z["F_cyl_N"], z["s_motor_m"]
    zb = z["body_pos_m"][:, 2]
    th = np.radians(z["roll_pitch_deg"][:, 1])
    cr = z["scm_crawler_normal_N"]
    ev = res["swivel"]["events"]
    tc = [min(e[0] for e in ev if e[1] == i) for i in range(4)]
    kr = int(np.searchsorted(t, tc[2]))
    kf = int(np.searchsorted(t, tc[0]))
    fe = (t >= 10.0) & (t < 20.0)
    v_free = np.gradient(sm, t, axis=0)[fe].mean(axis=0)
    u = float(v_free[2:].mean())
    zf = (zb - XF * th) - (zb[kr] - XF * th[kr])
    lo = np.nonzero((t > T_LIFT) & (cr < 0.01 * res["p3a"]["weight_N"]))[0][0]
    out = {"t_contact_s": tc, "free_speed_mm_s": (v_free * 1e3).tolist(), "speed_fraction_measured": u / V_MAX,
           "contact_gap_s": tc[0] - tc[2], "contact_gap_sref_mm": (tc[0] - tc[2]) * u * 1e3,
           "rear_peak_before_front_kN": (fc[kr:kf, 2:].max(axis=0) / 1e3).tolist(),
           "rear_at_front_contact_kN": (fc[kf, 2:] / 1e3).tolist(),
           "crawler_front_sink_mm_by_time": {f"{dt:.2f}": float(zf[int(np.searchsorted(t, tc[2] + dt))] * 1e3)
                                             for dt in (0.10, 0.14)}}
    rear = []
    for i in (2, 3):
        idx = np.nonzero((t > T_LIFT) & (fc[:, i] > 1.4 * F_MIN))[0]
        if not idx.size or idx[0] >= lo:
            rear.append({"t_first_above_s": None, "window_open": False,
                         "min_after_rear_contact_to_liftoff_kN": float(fc[kr:lo + 1, i].min() / 1e3)})
            continue
        k = idx[0] + int(np.argmin(fc[idx[0]:lo + 1, i]))
        rear.append({"t_first_above_s": float(t[idx[0]]), "window_open": True, "t_min_s": float(t[k]),
                     "F_min_kN": float(fc[k, i] / 1e3), "t_min_minus_front_contact_s": float(t[k] - tc[0]),
                     "dip_from_front_contact_kN": float((fc[k, i] - fc[kf, i]) / 1e3),
                     "min_after_rear_contact_to_liftoff_kN": float(fc[kr:lo + 1, i].min() / 1e3)})
    out["rear"] = rear
    out["t_liftoff_after_start_s"] = float(t[lo] - T_LIFT)
    out["t_liftoff_expected_s"] = T_LIFTOFF_V0_AFTER_START / (u / V_MAX)
    out["estimate_linear_Ru_kN"] = 11.70 - 23.4 * (1.0 - u / V_MAX)
    return out


out = {"definition_source": {"file": str(SRC), "sha256": hashlib.sha256(src_text.encode()).hexdigest()},
       "this_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
       "runs": {}, "speed": {}, "touch_stroke": {}, "mechanism": {}}
for name, (p, frac) in RUNS.items():
    o, z = analyse(p)
    res = json.loads((p / "result.json").read_text("utf-8"))
    a = res.get("args", {})
    o["args"] = {k: a.get(k) for k in ("flow_law", "lift_s", "lift_speed_fraction", "flow_eta_v", "valve_tau_s",
                                       "threads")}
    o["t_end_s"] = float(z["t_s"][-1])
    out["runs"][name] = o
    t, fc, sm = z["t_s"], z["F_cyl_N"], z["s_motor_m"]
    lift = t > T_LIFT + 1e-9
    sp = np.ptp(sm, axis=1) * 1e3
    out["touch_stroke"][name] = {"stroke_spread_end_mm": float(sp[-1]), "stroke_spread_max_lift_mm": float(sp[lift].max())}
    if (p / "flow_series.npz").exists():
        out["speed"][name] = speed_metrics(p, float(t[-1]))
    out["mechanism"][name] = mechanism(p, frac)
b = json.loads((FB / "batch.json").read_text("utf-8"))
out["batch_fb"] = {c["case"]: {"rc": c.get("rc"), "wall_s": c.get("wall_s"), "pool": c.get("pool")} for c in b["cases"]}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, default=float), "utf-8")
# ASCII summary
for n, o in out["runs"].items():
    m = out["mechanism"][n]
    print(f"{n:9s} end {o['t_end_s']:.2f} lo {o['t_liftoff_after_start_s']:.3f} (exp {m['t_liftoff_expected_s']:.3f}) "
          f"Fa {np.round(o['pre_liftoff_min_F_kN'], 2)} sink_end {np.round(o['sink_end_mm'], 1)} "
          f"creep {np.round(o['creep_after_liftoff_mm'], 1)} cstop {o['creep_stop_first_s']} "
          f"dRP {np.round(o['d_roll_pitch_end_deg'], 3)} Fpk {o['F_peak_ratio_max']:.3f} "
          f"spread {out['touch_stroke'][n]['stroke_spread_end_mm']:.2f}/{out['touch_stroke'][n]['stroke_spread_max_lift_mm']:.2f}")
    print(f"           frac {m['speed_fraction_measured']:.5f} gap {m['contact_gap_s']:.4f}s {m['contact_gap_sref_mm']:.3f}mm "
          f"peak {np.round(m['rear_peak_before_front_kN'], 2)} atF {np.round(m['rear_at_front_contact_kN'], 2)} "
          f"zf {m['crawler_front_sink_mm_by_time']} est {m['estimate_linear_Ru_kN']:.2f}")
    for r in m["rear"]:
        print("           ", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
for n, s in out["speed"].items():
    print(n, "Qdem", round(s["Q_dem_max_L_min"], 2), "Qsum", round(s["Q_sum_max_L_min"], 2), "sup",
          round(s["supply_L_min"], 2), "lim", s["limited_rows"], "u", {k: round(v, 3) for k, v in s["u_median_mm_s"].items()},
          "r", {k: round(v["median"], 5) for k, v in s["ratio_by_leg"].items()}, "rmin",
          {k: round(v["min"], 4) for k, v in s["ratio_by_leg"].items()}, "spread", s["ratio_spread_all4_max"],
          "ramp", np.round(s["valve_ramp_to_99pct_s"], 3))
print(out["batch_fb"])
