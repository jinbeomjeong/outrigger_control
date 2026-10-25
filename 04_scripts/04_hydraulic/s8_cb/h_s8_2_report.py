"""H-S8-2: numbers for the report from h_s8_2_lock_ratio.json.

Usage: python -I h_s8_2_report.py <json>
"""
import collections
import json
import sys

import numpy as np

d = json.loads(open(sys.argv[1], encoding="utf-8").read())
runs, st = d["runs"], d["stretches"]


def side(leg):
    return "front" if leg in ("FL", "FR") else "rear"


def bname(b):
    return {"p1r_20261024_222013": "p1r", "cb_20261025_000840": "cb"}.get(b, "ml")


print("== Part B: lock runs (1 ms, >= 0.2 s) ==")
g = collections.defaultdict(list)
for r in runs:
    g[(bname(r["batch"]), side(r["leg"]))].append(r)
for k, rs in sorted(g.items()):
    big = [r for r in rs if r["max_drop_bar"] >= 10]
    fit = [r["R_fit"] / r["R_model"] for r in rs if r.get("R_fit") is not None
           and r["max_drop_bar"] >= 10]
    ou = [r["R_obs_max"] / r["R_ub"] for r in rs if r["R_obs_max"] is not None]
    om = [r["R_obs_max"] / r["R_model"] for r in rs if r["R_obs_max"] is not None]
    print(f"{k}: runs {len(rs)}, drop>=10 bar {len(big)}, s_lock {min(r['s_lock'] for r in rs):.3f}"
          f"..{max(r['s_lock'] for r in rs):.3f}, R_model {min(r['R_model'] for r in rs):.3f}.."
          f"{max(r['R_model'] for r in rs):.3f}, R_fit/R_model(drop>=10) max {max(fit) if fit else None},"
          f" R_obs/R_model max {max(om) if om else None:.3f}, R_obs/R_ub max {max(ou) if ou else None:.3f},"
          f" under_fb max {max(r['under_fb_kN'] for r in rs):.2f} kN,"
          f" under_ub max {max(r['under_ub_bar'] for r in rs):.2f} bar,"
          f" airborne runs {sum(r['airborne'] for r in rs)}, p_r max {max(r['p_r_max'] for r in rs):.1f}")
print("runs with R_obs_max > R_ub:")
for r in runs:
    if r["R_obs_max"] is not None and r["R_obs_max"] > r["R_ub"]:
        print("  ", r)
print("runs with R_obs_max > R_model x 1.05 (drop >= 10 bar):")
for r in runs:
    if r["R_obs_max"] is not None and r["R_obs_max"] > 1.05 * r["R_model"]:
        print("  ", {k: r[k] for k in ("batch", "case", "leg", "t0", "t1", "s_lock", "R_model",
                                       "R_ub", "R_obs_max", "R_fit", "max_drop_bar",
                                       "law_resid_bar", "under_ub_bar", "dir_before")})

print("\n== reference observations ==")
for case, leg in (("K0V_top_fdown3.5_Fs0", "FR"), ("CB_H4V_fdown3.5_Fs0", "FR"),
                  ("CB_H4V_fdown3.5_Fs0", "FL"), ("ML00_ep5", "FR"), ("ML22_ep4", "FL"),
                  ("CB_G4_Fs0", "RR")):
    print(f"-- {case} {leg}")
    for r in runs:
        if r["case"] == case and r["leg"] == leg and r["max_drop_bar"] >= 3:
            print("   run", {k: r[k] for k in ("t0", "t1", "s_lock", "L0r", "p_h0", "p_r0", "R_model",
                                               "R_ub", "R_obs_max", "R_fit", "max_drop_bar",
                                               "p_r_max", "under_fb_bar", "under_fb_kN",
                                               "under_ub_bar", "airborne")})
    for r in st:
        if r["case"] == case and r["leg"] == leg and (r["cur_err_max_kN"] > 0.3 or r["p_r_true_max_bar"] > 30):
            print("   stretch", {k: r[k] for k in ("t0", "t1", "start_sign", "p_h_anchor_bar",
                                                   "p_h_max_window_bar", "p_r_true_max_bar",
                                                   "F_true_min_kN", "cur_err_max_kN",
                                                   "t_cur_err_max", "prop_err_max_kN",
                                                   "prop_over_end_kN", "lock_delay_s",
                                                   "window_s")})

print("\n== Part C: 10 Hz replica ==")
g = collections.defaultdict(list)
for r in st:
    g[(bname(r["batch"]), side(r["leg"]))].append(r)
for k, rs in sorted(g.items()):
    cur = np.array([r["cur_err_max_kN"] for r in rs])
    prop = np.array([r["prop_err_max_kN"] for r in rs])
    read = np.array([r["prop_reading_err_max_kN"] for r in rs])
    vb = np.array([r["varB_err_max_kN"] for r in rs])
    over = np.array([r["prop_over_end_kN"] for r in rs])
    overm = np.array([r["prop_over_median_kN"] for r in rs])
    curo = np.array([r["cur_over_end_kN"] for r in rs])
    dl = [r["lock_delay_s"] - r["window_s"] for r in rs if r["lock_delay_s"] is not None and r["lock_delay_s"] > 0]
    ms = [r["anchor_miss_bar"] for r in rs if r["anchor_miss_bar"] is not None]
    print(f"{k}: n {len(rs)} | current err max {cur.max():.2f} kN, >0.6 kN {int((cur > 0.6).sum())}"
          f" | proposal err max {prop.max():.2f} (reading {read.max():.2f}), >0.6 kN"
          f" {int((prop > 0.6).sum())} | varB err max {vb.max():.2f}, >0.6 {int((vb > 0.6).sum())}"
          f" | over end p50/p90/p99/max {np.percentile(over, 50):.2f}/{np.percentile(over, 90):.2f}/"
          f"{np.percentile(over, 99):.2f}/{over.max():.2f}, >20 kN {int((over > 20).sum())}"
          f" | over median p50 {np.percentile(overm, 50):.2f}"
          f" | current over end p50/p90 {np.percentile(curo, 50):.2f}/{np.percentile(curo, 90):.2f}"
          f" | lock delay - window max {max(dl) if dl else None}, anchor miss max {max(ms) if ms else None}")
allc = np.array([r["cur_err_max_kN"] for r in st])
allp = np.array([r["prop_err_max_kN"] for r in st])
print(f"all: n {len(st)}, current >0.6 kN {int((allc > 0.6).sum())} (max {allc.max():.2f}),"
      f" proposal >0.6 kN {int((allp > 0.6).sum())} (max {allp.max():.2f})")
big = sorted(st, key=lambda r: -r["prop_over_end_kN"])[:8]
print("largest end over-conservatism:")
for r in big:
    print("  ", {k: r[k] for k in ("batch", "case", "leg", "t0", "start_sign", "p_h_anchor_bar",
                                   "p_h_max_window_bar", "p_h_lock_1ms_bar", "prop_over_end_kN",
                                   "varB_over_end_kN", "cur_err_max_kN")})
print("lift-off cap check (min F_p + m_rod g):", min(d["lift_cap_check"], key=lambda r: r["min_Fp_plus_Wrod_kN"]))
