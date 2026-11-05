"""Second pass on the K1 soil batch: full P3 check differences, completion timeline, force minima after W with their times,
pre-event C4G2 effect (hold rows), P3-4 window of the Fs8 on row. Read-only. Prints text and writes analyze2.json."""
import json
from pathlib import Path

import numpy as np

BATCH = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_k1soil_G1_20261105")
HERE = Path(__file__).resolve().parent
LEGS = ("FL", "FR", "RL", "RR")
TAGS = ("FLFs0", "FLFs8", "RRFs0")
F_MIN = 9414.6
out = {}


def short(v, n=260):
    return json.dumps(v, default=str, ensure_ascii=False)[:n]


for tag in TAGS:
    print("=" * 10, tag)
    res = {s: json.loads((BATCH / f"S9EV_G1_{tag}_{s}" / "result.json").read_text(encoding="utf-8")) for s in ("base", "RE1bF_off", "RE1bF_on")}
    on, off, base = res["RE1bF_on"], res["RE1bF_off"], res["base"]
    co, cf, cb = on["p3b"]["checks"], off["p3b"]["checks"], base["p3b"]["checks"]
    keys = sorted(set(co) | set(cf))
    print("check keys", len(keys))
    for k in keys:
        if co.get(k) != cf.get(k) or k in ("P3-3_within", "P3-5_within", "P3-7_within", "P3-8_pass", "P3-6_within"):
            print(f"  {k}: on={short(co.get(k), 200)} off={short(cf.get(k), 200)} base={short(cb.get(k), 120)}")
    print(" flags-like", {k: (co[k], cf[k]) for k in keys if ("flag" in k.lower()) and k in co and k in cf})
    for name, r in (("on", on), ("off", off), ("base", base)):
        print(" ", name, "P3-3", short({k: v for k, v in r["p3b"]["P3-3_leg_force"].items() if k not in ("rule", "criterion", "basis")}, 700))
        print(" ", name, "P3-7", short({k: v for k, v in r["p3b"]["P3-7_plateau"].items() if k not in ("rule", "criterion", "basis")}, 300))
        print(" ", name, "P3-8", short({k: v for k, v in r["p3b"]["P3-8_false_triggers"].items() if k not in ("rule", "criterion", "basis")}, 500))
        print(" ", name, "P3-9", short({k: v for k, v in r["p3b"]["P3-9_deferred"].items() if k not in ("rule", "criterion", "basis")}, 1500))
        print(" ", name, "creep", short(r["p3b"]["creep_stop"], 500))
        print(" ", name, "P3-4", short({k: v for k, v in r["p3b"]["P3-4_attitude"].items() if k not in ("rule", "criterion", "basis")}, 500))
        print(" ", name, "rec S1,S2,S3", short(r["p3_records"].get("S1_after_departure"), 300), short(r["p3_records"].get("S2_hold_settlement"), 300), short(r["p3_records"].get("S3_attitude_after_done"), 300))

    # completion timeline
    tev = float(off["soil_event"]["driver"]["t_ev_s"])
    tl = {}
    for s in ("RE1bF_off", "RE1bF_on"):
        z = np.load(BATCH / f"S9EV_G1_{tag}_{s}" / "completion_series.npz", allow_pickle=True)
        t = np.asarray(z["t_s"]) - tev
        rec = {}
        for k in ("ok_attitude", "ok_clearance", "ok_twist", "ok_loc", "ok_twist_strict", "on_target"):
            v = np.asarray(z[k]).astype(bool)
            m = t > 0
            last_false = t[m][~v[m]]
            rec[k + "_last_false_s"] = round(float(last_false.max()), 2) if last_false.size else None
        dev = np.degrees(np.asarray(z["deviation_rad"], float))
        for lo, hi in ((0, 2), (2, 5), (5, 10), (10, 15), (15, 20), (20, 25), (25, 30)):
            mm = (t >= lo) & (t < hi)
            rec[f"dev_max_deg_{lo}_{hi}"] = round(float(np.nanmax(np.abs(dev[mm]))), 4)
            rec[f"Dloop_abs_max_kN_{lo}_{hi}"] = round(float(np.nanmax(np.abs(np.asarray(z["D_loop_N"], float)[mm]))) / 1e3, 3)
        rec["relaxed_any"] = bool(np.asarray(z["twist_relaxed"]).astype(bool)[t > 0].any())
        tl[s] = rec
        print(" completion", s, rec)
    # forces after W
    rows = {}
    for s in ("RE1bF_off", "RE1bF_on"):
        j = res[s]["soil_event"]["judgement"]
        z = np.load(BATCH / f"S9EV_G1_{tag}_{s}" / "soil_event_series.npz")
        r = np.asarray(z["rows"], float)
        t = r[:, 0] - tev
        F = r[:, 5:9]
        post = t > j["W_end_s"]
        rec = {"W_end_s": j["W_end_s"]}
        for i, leg in enumerate(LEGS):
            k = int(np.argmin(F[post, i]))
            rec[leg] = {"min_after_W_kN": round(float(F[post, i][k]) / 1e3, 3), "t_s": round(float(t[post][k]), 3),
                        "below_14p41_after_W_s": round(float((F[post, i] < F_MIN + 5e3).sum() * 1e-3), 3),
                        "below_Fmin_after_W_s": round(float((F[post, i] < F_MIN).sum() * 1e-3), 3)}
        # common window: larger of the two W ends is filled below
        rows[s] = rec
        print(" afterW", s, rec)
    wc = max(res["RE1bF_on"]["soil_event"]["judgement"]["W_end_s"], res["RE1bF_off"]["soil_event"]["judgement"]["W_end_s"])
    common = {}
    for s in ("RE1bF_off", "RE1bF_on"):
        z = np.load(BATCH / f"S9EV_G1_{tag}_{s}" / "soil_event_series.npz")
        r = np.asarray(z["rows"], float)
        t = r[:, 0] - tev
        common[s] = {leg: round(float(r[t > wc, 5 + i].min()) / 1e3, 2) for i, leg in enumerate(LEGS)}
    print(" common window t >", wc, common)
    # D on 10 Hz after event: twist + first differences of u
    # pre-event section from the 1 ms step series
    pre = {}
    for s in ("RE1bF_off", "RE1bF_on"):
        z = np.load(BATCH / f"S9EV_G1_{tag}_{s}" / "step_series.npz")
        t = np.asarray(z["t_s"], float)
        F = np.asarray(z["F_cyl_N"], float)
        sm = np.asarray(z["s_motor_m"], float)
        D = (F[:, 0] + F[:, 3]) - (F[:, 1] + F[:, 2])
        tau = (sm[:, 0] + sm[:, 3] - sm[:, 1] - sm[:, 2]) / 4
        sn = np.asarray(z["pad_sinkage_geometric_m"], float)
        rec = {"dt_ms": float(np.median(np.diff(t)) * 1e3)}
        for lab, tt in (("TE31.7", 31.7), ("31.4", 31.4), ("33.2", 33.2), ("LOC33.3", 33.3), ("35", 35.0), ("ev", tev)):
            k = int(np.argmin(np.abs(t - tt)))
            win = (t > tt - 0.3) & (t <= tt)
            rec[lab] = {"D_kN": round(float(D[win].mean()) / 1e3, 3), "tau_mm": round(float(tau[k]) * 1e3, 4), "F_kN": [round(float(x) / 1e3, 2) for x in F[win].mean(axis=0)]}
        m = (t >= 31.7) & (t < tev)
        rec["min_F_31.7_to_ev_kN"] = {leg: round(float(F[m, i].min()) / 1e3, 2) for i, leg in enumerate(LEGS)}
        rec["sink_at_ev_mm"] = (sn[int(np.argmin(np.abs(t - tev)))] * 1e3).round(3).tolist()
        pre[s] = rec
        print(" pre-event", s, rec)
    print(" hold", short(on["controller_meta"]["touch_twist_hold"], 600))
    out[tag] = {"completion": tl, "after_W": rows, "common_window": {"t_gt_s": wc, **common}, "pre_event": pre}
(HERE / "analyze2.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
