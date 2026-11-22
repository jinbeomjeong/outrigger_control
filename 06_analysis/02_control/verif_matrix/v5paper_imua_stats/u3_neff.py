"""Kish effective sample size of the U-3 resample units (per setting) for a few ICC values."""
import csv
from collections import Counter

rows = list(csv.DictReader(open(r"C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba"
                                r"\bd7ff3b9-880c-4e9e-afd1-7024158f16f4\scratchpad\control-imuacheck"
                                r"\u3_cluster_map_r1.csv", encoding="utf-8")))
for col in ("cluster", "resample_unit"):
    sizes = list(Counter(r[col] for r in rows).values())
    n = sum(sizes)
    mw = sum(s * s for s in sizes) / n
    kish = n * n / sum(s * s for s in sizes)
    out = {icc: round(n / (1 + (mw - 1) * icc), 1) for icc in (0.90, 0.92, 0.93, 0.946)}
    print(col, "units", len(sizes), "n", n, "line-weighted mean size", round(mw, 2), "Kish units", round(kish, 1),
          "n_eff by ICC", out)
