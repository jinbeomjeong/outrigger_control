"""Extract the K1 soil batch values into raw_values.json and print a text view. Read-only on the batch folder.

Stored judgement fields are copied; lift, union, last touch and minima are recomputed from the 1 ms rows here without the r67 judge,
so the stored judge and this script are two paths on the same rows. Adds a same-window comparison, smoothed force minima and F_min times.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

BATCH = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_k1soil_G1_20261105")
HERE = Path(__file__).resolve().parent
LEGS = ("FL", "FR", "RL", "RR")
F_MIN = 9414.6
DIAG = {"FL": "RR", "RR": "FL", "FR": "RL", "RL": "FR"}
PAIRS = {"FLFs0": ("FL", 0.0), "FLFs8": ("FL", 8.0), "RRFs0": ("RR", 0.0)}


def load(name):
    d = BATCH / name
    return d, json.loads((d / "result.json").read_text(encoding="utf-8"))


def intervals(mask, t):
    """Sum of lifted time as sample count x 1 ms and the time of the last lifted sample, independent of r51._intervals."""
    if not mask.any():
        return 0.0, 0.0, 0
    idx = np.flatnonzero(mask)
    n_runs = 1 + int((np.diff(idx) > 1).sum())
    return float(mask.sum() * 1e-3), float(t[idx[-1]]), n_runs


def series_values(d, t_ev, leg, w_end):
    z = np.load(d / "soil_event_series.npz")
    rows = np.asarray(z["rows"], float)
    cols = [str(c) for c in z["columns"]]
    t = rows[:, 0] - t_ev
    contact = rows[:, 1:5]
    F = rows[:, 5:9]
    gap = rows[:, 13:17]
    att = rows[:, 17:19]
    crawler = rows[:, 19]
    lifted = contact <= 0.0
    after = t >= 0.0
    out = {"t_end_rel_s": float(t[-1]), "columns_ok": cols[1] == "contact_FL" and cols[5] == "Fcyl_FL", "dt_ms": float(np.median(np.diff(rows[:, 0])) * 1e3)}
    per = {}
    for i, name in enumerate(LEGS):
        s, last, n = intervals(after & lifted[:, i], t)
        below = after & (F[:, i] < F_MIN)
        k = 50
        smooth = np.convolve(F[:, i], np.ones(k) / k, mode="same")
        m_after = after & (t > 0.03) & (t < t[-1] - 0.03)
        per[name] = {"lift_s": round(s, 3), "last_touch_s": round(last, 3), "n_lift": n, "max_gap_mm": round(float(gap[after & lifted[:, i], i].max() * 1e3), 2) if (after & lifted[:, i]).any() else 0.0,
                     "min_F_1ms_kN": round(float(F[after, i].min()) / 1e3, 2), "t_min_F_s": round(float(t[after][np.argmin(F[after, i])]), 3),
                     "min_F_50ms_kN": round(float(smooth[m_after].min()) / 1e3, 2), "t_min_F50_s": round(float(t[m_after][np.argmin(smooth[m_after])]), 3),
                     "below_Fmin_s": round(float(below.sum() * 1e-3), 3),
                     "below_Fmin_not_lifted_s": round(float((below & ~lifted[:, i]).sum() * 1e-3), 3),
                     "contact_min_N": round(float(contact[after, i].min()), 1)}
        per[name]["min_F_in_kN"] = {f"0-{hi:g}": round(float(F[after & (t <= hi), i].min()) / 1e3, 2) for hi in (0.5, 1, 2, 3, 5)}
        per[name]["min_F_after_kN"] = {f"{lo:g}-end": round(float(F[t > lo, i].min()) / 1e3, 2) for lo in (2, 3, 5, 8)}
        per[name]["F_pre_mean_kN"] = round(float(F[(t >= -0.5) & (t < 0), i].mean()) / 1e3, 2)
        per[name]["F_end_mean_kN"] = round(float(F[t >= t[-1] - 1, i].mean()) / 1e3, 2)
    out["legs"] = per
    pair = [LEGS.index(leg), LEGS.index(DIAG[leg])]
    union = after & lifted[:, pair].any(axis=1)
    out["pair_union_s"], out["pair_last_touch_s"], out["pair_n"] = (lambda a: (round(a[0], 3), round(a[1], 3), a[2]))(intervals(union, t))
    out["pair_overlap_s"] = round(float((after & lifted[:, pair].all(axis=1)).sum() * 1e-3), 3)
    out["max_att_change_deg"] = round(float(np.abs(att[after] - att[0]).max()), 4)
    out["att_at_start_deg"] = [round(float(a), 4) for a in att[0]]
    out["att_end_mean_deg"] = [round(float(a), 4) for a in att[t >= t[-1] - 1].mean(axis=0)]
    out["crawler_after_event_ms"] = int((crawler[after] > 0).sum())
    out["crawler_max_kN"] = round(float(crawler[after].max()) / 1e3, 3)
    D = (F[:, 0] + F[:, 3]) - (F[:, 1] + F[:, 2])
    out["D_pre_kN"] = round(float(D[(t >= -0.5) & (t < 0)].mean()) / 1e3, 3)
    out["sink_true_start_mm"] = (np.asarray(z["sink_true_m"], float)[0] * 1e3).round(2).tolist()
    out["sink_true_end_mm"] = (np.asarray(z["sink_true_m"], float)[-1] * 1e3).round(2).tolist()
    out["w_end_s"] = w_end
    return out


def first_diff(a, b):
    za, zb = np.load(a / "controller_commands.npz"), np.load(b / "controller_commands.npz")
    ta, ua, tb, ub = za["t_s"], za["issued_u_m_s"], zb["t_s"], zb["issued_u_m_s"]
    n = min(ta.size, tb.size)
    time_same = bool(np.array_equal(ta[:n], tb[:n]))
    neq = np.flatnonzero(np.any(ua[:n] != ub[:n], axis=1))
    close = np.flatnonzero(np.any(np.abs(ua[:n] - ub[:n]) > 1e-9, axis=1))
    return {"n": int(n), "time_same": time_same, "first_diff_t_s": float(ta[neq[0]]) if neq.size else None, "first_diff_gt1e-9_t_s": float(ta[close[0]]) if close.size else None}


def event_rows(res, t_ev):
    keep = []
    for e in res["events"]:
        n = str(e["name"])
        keep.append([round(float(e["t_s"]) - (t_ev if t_ev is not None else 0.0), 3), n])
    return keep


def main():
    out = {}
    for tag, (leg, fs) in PAIRS.items():
        base = f"S9EV_G1_{tag}_base"
        rows = {}
        for suffix in ("base", "RE1bF_off", "RE1bF_on"):
            name = f"S9EV_G1_{tag}_{suffix}"
            d, res = load(name)
            side = json.loads((d / "k1soil_job_side.json").read_text(encoding="utf-8"))
            se = res.get("soil_event")
            t_ev = float(se["driver"]["t_ev_s"]) if se else None
            r = {"case": name, "c2_sha256": side["c2_sha256"], "config": side["config"], "main_tree_modules_at_end": side["main_tree_modules_at_end"], "config_name": side["config_name"],
                 "hold": {k: v for k, v in res["controller_meta"]["touch_twist_hold"].items() if k != "settings"}, "hold_enabled": res["controller_meta"]["touch_twist_hold"]["settings"]["enable"],
                 "retrigger_samples": res["c2_lifted_reapproach"]["retrigger_samples"], "wall_s": res["wall_s"], "t_loop_start_s": res["t_loop_start_s"],
                 "phases": [[round(p["t_s"], 2), p["phase"]] for p in res["phases"]], "soil_mode": (res.get("c2_soil") or {}).get("soil_mode_t_s"),
                 "t_crawler_departure_rel_s": res["p3b_ext"].get("t_crawler_departure_rel_s"), "event_times_rel_s": res["p3b_ext"].get("event_times_rel_s"),
                 "event_counts": res["p3b_ext"].get("event_counts"), "p3b_checks": res["p3b"].get("checks"), "p3_6": res["p3b"].get("P3-6_ready"), "p3_1": res["p3b"].get("P3-1_crawler"), "p3_2": res["p3b"].get("P3-2_loc"), "p3_3": res["p3b"].get("P3-3_leg_force"),
                 "p3_4": res["p3b"].get("P3-4_attitude"), "p3_5": res["p3b"].get("P3-5_clearance_stroke"), "p3_7": res["p3b"].get("P3-7_plateau"), "p3_8": res["p3b"].get("P3-8_false_triggers"), "p3_9": res["p3b"].get("P3-9_deferred"), "W61": res["p3b"].get("W61_watch"), "reapproach_limit": res["p3b"].get("reapproach_limit"),
                 "pre_liftoff_min_F_cyl": res["p3b"].get("pre_liftoff_min_F_cyl"), "departure": res["p3b"].get("departure"),
                 "events_all": event_rows(res, None), "history": [{"leg": h["leg"], "start": round(h["start_s"], 2), "end": round(h["end_s"], 2), "travel_mm": round(h["travel_m"] * 1e3, 3), "outcome": h["outcome"], "retrigger": h["is_retrigger"], "protected": h["protected_periods"]} for h in res["c2_lifted_reapproach_history"]]}
            zc = np.load(d / "completion_series.npz")
            ts = np.asarray(zc["t_s"])
            if t_ev is not None:
                k = int(np.argmin(np.abs(ts - t_ev)))
                r["D_raw_at_ev_kN"] = round(float(zc["D_raw_N"][k]) / 1e3, 3)
                r["D_loop_at_ev_kN"] = round(float(zc["D_loop_N"][k]) / 1e3, 3)
                j = se["judgement"]
                r["t_ev_s"] = t_ev
                r["trigger"] = se["spec"]["text"]
                r["prefix_check"] = se.get("prefix_check")
                r["driver"] = {k2: se["driver"][k2] for k2 in ("t_ev_s", "n_frame_updates", "first_update_t_s", "last_update_t_s")}
                r["commands_sha"] = se.get("branch_commands_sha256")
                r["judgement"] = j
                r["series"] = series_values(d, t_ev, leg, j["W_end_s"])
                r["events_rel"] = [[round(float(e["t_s"]) - t_ev, 3), str(e["name"])] for e in res["events"] if float(e["t_s"]) >= t_ev - 0.5]
            rows[suffix] = r
        pair = {"on_vs_off": first_diff(BATCH / f"S9EV_G1_{tag}_RE1bF_on", BATCH / f"S9EV_G1_{tag}_RE1bF_off"), "on_vs_base": first_diff(BATCH / f"S9EV_G1_{tag}_RE1bF_on", BATCH / base), "off_vs_base": first_diff(BATCH / f"S9EV_G1_{tag}_RE1bF_off", BATCH / base)}
        out[tag] = {"rows": rows, "pair": pair, "leg": leg, "fs_kN": fs}
    log = HERE.parent / "cad_k1soil" / "logs" / "runner.log"
    out["runner_log_tail"] = log.read_text(encoding="utf-8").splitlines()[-30:] if log.exists() else None
    (HERE / "raw_values.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")

    for tag in PAIRS:
        o = out[tag]
        print("=" * 20, tag, json.dumps(o["pair"]))
        for suffix, r in o["rows"].items():
            print("--", suffix, r["c2_sha256"][:10], r["config_name"], "retrig", r["retrigger_samples"], "hold_en", r["hold_enabled"], json.dumps(r["hold"]), "main", r["main_tree_modules_at_end"], "wall", round(r["wall_s"]))
            print(" phases", r["phases"], "soil_mode", r["soil_mode"], "dep", r["t_crawler_departure_rel_s"])
            print(" evt_times", json.dumps(r["event_times_rel_s"])[:500])
            print(" counts", json.dumps(r["event_counts"])[:500])
            print(" checks", json.dumps(r["p3b_checks"])[:900])
            print(" P3-2", json.dumps(r["p3_2"])[:300])
            print(" P3-6", json.dumps(r["p3_6"])[:200], "P3-9", json.dumps(r["p3_9"])[:300], "W61", json.dumps(r["W61"])[:200])
            print(" prelift", json.dumps(r["pre_liftoff_min_F_cyl"])[:300])
            print(" events_all", [e for e in r["events_all"] if not e[1].startswith("INFO_PRESSURE_ZERO")])
            print(" history", r["history"])
            if "judgement" in r:
                print(" t_ev", r["t_ev_s"], r["trigger"], "prefix", r["prefix_check"], "D_raw", r["D_raw_at_ev_kN"], "D_loop", r["D_loop_at_ev_kN"], "sha", r["commands_sha"][:12])
                j = r["judgement"]
                print(" J", json.dumps({k: j[k] for k in j if k in ("pass", "lifts", "pair_union_s", "pair_last_touch_s", "W_end_s", "adj_lift_sum_W_s", "adj_min_F_in_W_kN", "min_F_after_W_kN", "min_F_after_event_kN", "fault_periods", "final_phase", "t_ready_back_s", "att_end_deg", "max_att_change_deg", "crawler_contact_after_event_ms", "reapproach_starts", "n_late_starts", "sign_changes", "warnings", "flags", "stop_rel_s", "stop_reason", "pressure", "crawler", "stroke_max_run_mm", "soil")}))
                print(" gates", j["gates"], "twist", j["twist"]["n_bundles"], j["twist"]["max_judged_bin_J"], j["twist"]["D0_kN"])
                s = r["series"]
                print(" S", json.dumps({k: v for k, v in s.items() if k != "legs"}))
                for leg, v in s["legs"].items():
                    print("   ", leg, json.dumps(v))
                print(" events_rel", [e for e in r["events_rel"]])
    print("LOG", "\n".join(out["runner_log_tail"] or []))


if __name__ == "__main__":
    sys.exit(main())
