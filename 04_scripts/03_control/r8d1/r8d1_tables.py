"""Collect the numbers for spec rev. 30 tables from the sweep JSONs (channel worst M_s, PM min, w_gc range)."""
import json
import re

FILES = ["r8d1_base.json", "r8d1_comp.json", "r8d1_tv.json", "r8d1_des2.json", "r8d1_rate2.json", "r8d1_harn.json",
         "r8d1_final.json", "r8d1_fin_guardref.json", "r8d1_guardkg.json", "r8d1_nolate.json"]
want = ["d1_A8_tv0.1", "d1_A8_tv0", "d1_G7_tv0.1", "d0_A8_tv0.1", "d1_LO_tv0.1", "d1_A8_tv0.1_smTW", "d1_A8_tv0.1_smALL",
        "d1_A8_tv0.1_late9", "d1_A8_tv0.1_smALL_late9", "d1_G7_tv0.1_late9", "d1_G7_tv0.1_smALL",
        "C1_tv0.05", "C1_tv0.1", "C1_tv0.15", "C1_tv0.2", "C1_tv0.1_q2", "C1_tv0.1_p2", "C1_tv0.1_q2p2",
        "C2_tv0.05", "C2_tv0.1", "C2_tv0.15", "C2_tv0.2", "C2_tv0.1_q2", "C2_tv0.1_p2", "C2_tv0.1_q2p2",
        "R7_50Hz", "A8k08_tv0.1", "M6L_tv0.1", "M5L_tv0.1"]
rows = {}
summ = {}
for f in FILES:
    try:
        d = json.load(open(f))
    except FileNotFoundError:
        continue
    summ.update(d["summary"])
    for t, r in d["rows"]:
        for k, v in r.items():
            rows.setdefault(k, []).append((t, v))
for w in want:
    if w not in rows:
        print(w, "missing"); continue
    good = [(t, v) for t, v in rows[w] if "error" not in v]
    pm = min(min(x for x in v["PM"].values() if x is not None) for _, v in good)
    wgc = [v["wgc"]["phi"] for _, v in good if v["wgc"]["phi"]]
    s = summ[w]
    print(f"{w:26s} Ms {s['Ms_worst']:.3f} {s['ch']:5s} @{s['w_Ms']:.2f} ({s['plant']}) n>1.5 {s['over1.5']} PMmin {pm:.1f} "
          f"att wgc {min(wgc):.3f}-{max(wgc):.3f} rad/s chw {s['ch_worst']}")
for base in ("C1_tv0.1_G", "C2_tv0.1_G", "C1_tv0.15_G", "C2_tv0.15_G", "C1_tv0.05_G"):
    vals = [summ[k] for k in summ if re.fullmatch(re.escape(base) + r"_g\d", k)]
    if vals:
        v = max(vals, key=lambda x: x["Ms_worst"])
        print(base, v["Ms_worst"], v["plant"], v["ch"], v["w_Ms"])
