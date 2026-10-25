"""H-S8-2: spot checks of statements in the report (reads h_s8_2_lock_ratio.json).

Usage: python -I h_s8_2_checks.py <json>
"""
import json
import sys

d = json.loads(open(sys.argv[1], encoding="utf-8").read())
runs, st = d["runs"], d["stretches"]
for case, leg, t0 in (("E_G4_Fs8", "FL", 6.4), ("CB_H4V_fdown3.5_Fs0", "RR", 26.3),
                      ("CB_H4V_fdown3.5_Fs0", "RR", 26.6), ("K0_top_rpBop_Fs0", "FR", 4.2)):
    for r in st:
        if r["case"] == case and r["leg"] == leg and abs(r["t0"] - t0) < 0.05:
            print(case, leg, t0, "cur", r["cur_err_max_kN"], "prop", r["prop_err_max_kN"],
                  "read", r["prop_reading_err_max_kN"], r["batch"][:6])
for side, legs in (("front", ("FL", "FR")), ("rear", ("RL", "RR"))):
    s = [r["s_lock"] for r in runs if r["leg"] in legs and r["max_drop_bar"] >= 10]
    print(side, "s_lock of runs with drop >= 10 bar:", min(s), max(s), len(s))
dl = [r["lock_delay_s"] for r in st if r["lock_delay_s"] is not None and r["lock_delay_s"] > 0]
print("lock delay range (>0):", min(dl), max(dl), len(dl))
neg = [r for r in st if r["lock_delay_s"] is not None and r["lock_delay_s"] <= 0]
print("stretches with lock before first command-free sample:", len(neg))
p1f = [r for r in st if r["batch"].startswith("p1r") and r["leg"] in ("FL", "FR") and r["cur_err_max_kN"] > 0.6]
print("p1r front current > 0.6:", len(p1f), "of which t0 < 10 s:", sum(r["t0"] < 10 for r in p1f),
      "start retract:", sum(r["start_sign"] < 0 for r in p1f))
for b in ("p1r", "cb_", "ml_"):
    for legs in (("FL", "FR"), ("RL", "RR")):
        x = [r for r in st if r["batch"].startswith(b) and r["leg"] in legs and r["cur_err_max_kN"] > 0.6]
        print(b, legs, "current >0.6:", len(x), "early(t0<10)", sum(r["t0"] < 10 for r in x),
              "retract start", sum(r["start_sign"] < 0 for r in x))
