"""H-S8-2: print parts of the h_s8_2_lock_ratio.py JSON.

Usage: python -I h_s8_2_show.py <json> [runs|stretches|a|summary] [case filter]
"""
import json
import sys

d = json.loads(open(sys.argv[1], encoding="utf-8").read())
what = sys.argv[2] if len(sys.argv) > 2 else "summary"
flt = sys.argv[3] if len(sys.argv) > 3 else ""
if what == "a":
    a = d["part_a"]
    print("s grid", a["s_grid_m"])
    for row in a["R_table"]:
        print(f"L0h {row['L0h']:.2f} L0r {row['L0r']:.4f}:", " ".join(f"{v:6.3f}" for v in row["R"]))
    print("R_ub      :", " ".join(f"{v:6.3f}" for v in a["R_ub_grid"]))
    for row in a["liftoff"]:
        print(row)
    for row in a["beta_sensitivity"]:
        print(row)
elif what in ("runs", "stretches"):
    for r in d[what]:
        if flt in r["case"]:
            print(r)
else:
    import collections
    runs = d["runs"]
    print("runs", len(runs), "stretches", len(d["stretches"]), "skipped", len(d["skipped"]))
    for s in d["skipped"][:5]:
        print("  skipped", s)
    by = collections.defaultdict(list)
    for r in runs:
        by[(r["batch"][:6], r["leg"][0])].append(r)
    for k, rs in sorted(by.items()):
        res = max(r["law_resid_bar"] for r in rs)
        obs = [r["R_obs_max"] for r in rs if r["R_obs_max"] is not None]
        fr = [r["R_fit"] / r["R_model"] for r in rs if r.get("R_fit") is not None]
        ou = [r["R_obs_max"] / r["R_ub"] for r in rs if r["R_obs_max"] is not None]
        print(k, "R_fit/R_model", (round(min(fr), 3), round(max(fr), 3)) if fr else None,
              "R_obs/R_ub max", round(max(ou), 3) if ou else None, "n_fit", len(fr))
        print(k, "n", len(rs), "s_lock", min(r["s_lock"] for r in rs), max(r["s_lock"] for r in rs),
              "max law resid", res, "R_obs max", max(obs) if obs else None,
              "under_fb max kN", max(r["under_fb_kN"] for r in rs),
              "under_ub max bar", max(r["under_ub_bar"] for r in rs),
              "p_r max", max(r["p_r_max"] for r in rs))
    over = [r for r in runs if r["R_obs_max"] is not None and r["R_obs_max"] > r["R_ub"]]
    print("runs with R_obs_max > R_ub:", len(over))
    for r in over[:12]:
        print("  ", r["batch"][:10], r["case"], r["leg"], r["t0"], r["t1"], "s", r["s_lock"], "R_model", r["R_model"],
              "R_ub", r["R_ub"], "R_obs", r["R_obs_max"], "R_fit", r.get("R_fit"), "drop", r["max_drop_bar"],
              "resid", r["law_resid_bar"], "under_ub", r["under_ub_bar"])
    st = d["stretches"]
    by = collections.defaultdict(list)
    for r in st:
        by[(r["batch"][:6], r["leg"][0])].append(r)
    for k, rs in sorted(by.items()):
        dl = [r["lock_delay_s"] - r["window_s"] for r in rs if r["lock_delay_s"] is not None]
        ms = [r["anchor_miss_bar"] for r in rs if r["anchor_miss_bar"] is not None]
        print(k, "n", len(rs),
              "cur err max kN", max(r["cur_err_max_kN"] for r in rs),
              "prop err max kN", max(r["prop_err_max_kN"] for r in rs),
              "prop reading err max kN", max(r["prop_reading_err_max_kN"] for r in rs),
              "delay-window max s", max(dl) if dl else None,
              "anchor miss max bar", max(ms) if ms else None,
              "over median (median) kN", sorted(r["prop_over_median_kN"] for r in rs)[len(rs) // 2],
              "over end max kN", max(r["prop_over_end_kN"] for r in rs))
    cc = d.get("lift_cap_check", [])
    if cc:
        w = min(cc, key=lambda r: r["min_Fp_plus_Wrod_kN"])
        print("lift cap check worst", w)
    bad = [r for r in st if r["cur_err_max_kN"] > 0.6]
    print("stretches with current err > 0.6 kN:", len(bad))
    for r in sorted(bad, key=lambda r: -r["cur_err_max_kN"])[:25]:
        print("  ", r["batch"][:14], r["case"], r["leg"], r["t0"], "cur", r["cur_err_max_kN"],
              "prop", r["prop_err_max_kN"], "read", r["prop_reading_err_max_kN"], "pr max", r["p_r_true_max_bar"])
    badp = [r for r in st if r["prop_err_max_kN"] > 0.0 or r["prop_reading_err_max_kN"] > 0.0]
    print("stretches with proposal err > 0:", len(badp))
    for r in sorted(badp, key=lambda r: -max(r["prop_err_max_kN"], r["prop_reading_err_max_kN"]))[:25]:
        print("  ", r)
