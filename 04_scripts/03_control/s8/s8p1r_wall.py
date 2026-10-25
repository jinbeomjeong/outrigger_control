"""Spec rev. 44: P / E core wall-time rates of the S8 p1 and p1r batches.

Per case: start / finish (case.log), placement (case.log), simulated time (result.json s8_end
end_t_s, else last r8 sample) and wall per simulated second. Concurrency: mean number of cases
running on P and on E cores over the case's wall interval (1 s grid). Rates are compared on
cases that ran while the pool was full (mean total concurrency >= 14), where P-core HT sharing
and E-core load are both at their batch level.
Usage: python -I s8p1r_wall.py <out json> <batch dir> [<batch dir> ...]
"""
import sys, os, re, json
from datetime import datetime
import numpy as np

OUT = sys.argv[1]
res = {}
for base in sys.argv[2:]:
    cases = {}
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        log = os.path.join(d, "case.log")
        if not os.path.isfile(log):
            continue
        txt = open(log, encoding="utf-8", errors="replace").read().splitlines()
        t_start = datetime.strptime(txt[0][:23], "%Y-%m-%d %H:%M:%S,%f")
        t_end = datetime.strptime([l for l in txt if "finished" in l][-1][:23], "%Y-%m-%d %H:%M:%S,%f")
        mode = re.search(r"'mode': '(\w+)'", txt[0]).group(1)
        r8 = np.load(os.path.join(d, "r8_series.npz"))
        sim = float(r8["t"][-1])
        cases[name] = dict(start=t_start.timestamp(), end=t_end.timestamp(), mode=mode, sim_s=sim)
    t0 = min(c["start"] for c in cases.values())
    t1 = max(c["end"] for c in cases.values())
    grid = np.arange(t0, t1, 1.0)
    runP = np.zeros(grid.size)
    runE = np.zeros(grid.size)
    for c in cases.values():
        on = (grid >= c["start"]) & (grid < c["end"])
        if c["mode"] == "pcore":
            runP += on
        else:
            runE += on
    for c in cases.values():
        on = (grid >= c["start"]) & (grid < c["end"])
        c["wall_s"] = c["end"] - c["start"]
        c["rate"] = c["wall_s"] / c["sim_s"]
        c["conc_P"] = float(runP[on].mean())
        c["conc_E"] = float(runE[on].mean())
    full = {m: [c["rate"] for c in cases.values() if c["mode"] == m and c["conc_P"] + c["conc_E"] >= 14.0]
            for m in ("pcore", "ecore")}
    allr = {m: [c["rate"] for c in cases.values() if c["mode"] == m] for m in ("pcore", "ecore")}
    summ = {}
    for key, src in (("full_pool", full), ("all", allr)):
        summ[key] = {m: dict(n=len(v), median=float(np.median(v)) if v else None,
                             p25=float(np.percentile(v, 25)) if v else None,
                             p75=float(np.percentile(v, 75)) if v else None) for m, v in src.items()}
        if summ[key]["pcore"]["median"] and summ[key]["ecore"]["median"]:
            summ[key]["E_over_P"] = summ[key]["ecore"]["median"] / summ[key]["pcore"]["median"]
    res[os.path.basename(base)] = dict(batch_wall_s=t1 - t0, summary=summ, cases=cases)
    print(os.path.basename(base), f"wall {t1 - t0:.0f} s", json.dumps(summ))
    for n, c in sorted(cases.items(), key=lambda x: x[1]["start"]):
        print(f"   {n:26s} {c['mode']:5s} start+{c['start'] - t0:6.0f} wall {c['wall_s']:6.0f} sim {c['sim_s']:6.1f} "
              f"rate {c['rate']:5.2f} concP {c['conc_P']:4.1f} concE {c['conc_E']:4.1f}")
json.dump(res, open(OUT, "w", encoding="utf-8"), indent=1)
