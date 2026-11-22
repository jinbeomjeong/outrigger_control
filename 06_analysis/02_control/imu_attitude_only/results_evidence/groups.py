"""Compact per-group tables from analysis.json; plus the CHECK-length split of the gyro-free arms."""
import json
import sys

a = json.load(open(sys.argv[1], encoding="utf-8"))
arms = ("A-k", "A-g", "B-k", "B-r", "C-k", "A-g-2x1", "A-g-bw5", "B-r-q10", "B-r-cold", "C-r")
for lv in ("L1", "L2"):
    for arm in arms:
        for g in ("g6core", "g8", "ref", "lvl"):
            c = a["pairs_group"].get(f"{arm}|{lv}|{g}")
            if not c:
                continue
            m2 = c["d_M2"]
            m1 = c["d_M1"]
            m3 = c["d_M3"]
            print(lv, arm, g, c["n"], f'W{c["worse"]}/E{c["equal"]}/B{c["better"]}',
                  "dM2 med", m2 and m2["med"], "max", m2 and m2["max"], "| dM1 med", m1 and m1["med"],
                  "max", m1 and m1["max"], "| dM3 min", m3 and m3["min"])
print("== abs M2 / M1 / gate per group (L2)")
for arm in ("R0", "A-k", "A-g", "B-k", "B-r", "C-k"):
    for g in ("g6core", "g8", "ref", "lvl"):
        c = a["abs_group"].get(f"{arm}|L2|{g}")
        if c:
            print(arm, g, "M2", c["M2"] and (c["M2"]["med"], c["M2"]["max"]), "M1", c["M1"] and
                  (c["M1"]["med"], c["M1"]["max"]), "M3min", c["M3"] and c["M3"]["min"],
                  "gate", c["M8_gate"] and c["M8_gate"]["med"], "abst", c["M4_abstain_rate"] and
                  c["M4_abstain_rate"]["med"], "chk", c["check_s"] and (c["check_s"]["min"], c["check_s"]["max"]))
