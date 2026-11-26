"""S8-R design, part 2: floor evidence for G' (no ed8 results).

(a) V0-vs-V0 A/A proxy on the stored V0 grid (11-05, old offsets): ordered pairs (o, o'') of the same
    cluster, opportunity = V0(o) pass, A/A failure = V0(o'') fail (r67 gate pass only; J1~J11 items
    other than the gates are not in the stored grid).
(b) Published ed6 VBL grid (treatment arm, judged against stored V0 per unit): failure rate among
    V0-pass units and its clustering by cluster / family (ANOVA ICC on the 0/1 indicator).

Usage: python -I -B s8r_floor.py <out_folder>
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control")
GRID = ROOT / "touch_phase" / "acceptance" / "c4g2_only" / "grid"
GRID_FILES = ["grid_r67_main.json", "grid_r67_top.json", "grid_r69_bottom.json", "grid_r69_top.json"]
SCAN6 = ROOT / "j_p3_cause" / "ed8_design" / "dynamics_u832_o00" / "u01_scan_ed6.csv"
DIAG = {"FL": "RR", "RR": "FL", "FR": "RL", "RL": "FR"}
out = Path(sys.argv[1])
res, txt = {}, []

v0 = {}
for fn in GRID_FILES:
    d = json.loads((GRID / fn).read_text(encoding="utf-8"))
    for job in d["results"]:
        runs = job.get("runs") or []
        for r in (runs.values() if isinstance(runs, dict) else runs):
            ck = (job["level"], float(job["fs_kN"]), job["timing"], job["leg"], r.get("event"))
            key = ck + (round(float(r["offset_s"]), 4),)
            if key in v0:
                continue
            st = r.get("reapproach_starts") or []
            ds = [float(t) for t, lg in st if lg == DIAG[job["leg"]]]
            v0[key] = {"pass": bool(r.get("pass")), "E": bool(ds) and min(ds) <= 0.45 + 1e-9}

by_cluster = defaultdict(dict)
for key, v in v0.items():
    by_cluster[key[:5]][key[5]] = v


def aa(clusters):
    opp = fail = 0
    oppE = failE = 0
    for c in clusters:
        offs = by_cluster[c]
        for o, vo in offs.items():
            for o2, vo2 in offs.items():
                if o2 == o or not vo["pass"]:
                    continue
                opp += 1
                fail += (not vo2["pass"])
                if vo["E"]:
                    oppE += 1
                    failE += (not vo2["pass"])
    return opp, fail, oppE, failE


allc = list(by_cluster)
clean = [c for c in allc if all(v["pass"] for v in by_cluster[c].values())]
mixed = [c for c in allc if c not in clean and any(v["pass"] for v in by_cluster[c].values())]
for name, cl in [("all_clusters", allc), ("excl_mixed_or_fail", clean), ("mixed_only", mixed)]:
    o, f, oe, fe = aa(cl)
    res[f"aa_{name}"] = {"clusters": len(cl), "ordered_pairs_opp": o, "aa_fail": f,
                         "E_opp": oe, "E_fail": fe}
    txt.append(f"A/A {name}: clusters {len(cl)}, ordered pairs {o}, fail {f} ({f / max(o, 1):.4f}); "
               f"E opp {oe}, fail {fe}")
txt.append("mixed clusters: " + "; ".join("|".join(map(str, c)) + " " +
                                          str({o: v['pass'] for o, v in by_cluster[c].items()}) for c in mixed))

# ---------------------------------------------------------------- (b) ed6 VBL grid failures
rows = [r for r in csv.DictReader(SCAN6.open(encoding="utf-8")) if r["src"] == "ed6_grid"]
units = []
for r in rows:
    key = (r["level"], float(r["fs_kN"]), r["timing"], r["leg"], r["event"], round(float(r["offset_s"]), 4))
    v = v0.get(key)
    if v is None or not v["pass"]:
        continue
    fam = (r["level"], r["timing"], r["leg"], r["event"])
    units.append({"cluster": key[:5], "family": fam, "fail": r["pass"] != "True",
                  "gates": r["failed_gates"], "E": v["E"], "off": key[5]})
y = np.array([u["fail"] for u in units], float)
res["ed6_vbl"] = {"opp": len(units), "fail": int(y.sum())}
txt.append(f"\ned6 VBL grid: V0-pass opportunities {len(units)}, failures {int(y.sum())}")
for u in units:
    if u["fail"]:
        txt.append(f"  fail {'|'.join(map(str, u['family']))} Fs{u['cluster'][1]} o{u['off']} E={u['E']} {u['gates']}")


def anova_icc(groups):
    """One-way ANOVA ICC for 0/1 data with unequal group sizes."""
    g = [np.asarray(x, float) for x in groups if len(x) > 0]
    n = sum(len(x) for x in g)
    k = len(g)
    grand = np.concatenate(g).mean()
    ssb = sum(len(x) * (x.mean() - grand) ** 2 for x in g)
    ssw = sum(((x - x.mean()) ** 2).sum() for x in g)
    msb = ssb / max(k - 1, 1)
    msw = ssw / max(n - k, 1)
    n0 = (n - sum(len(x) ** 2 for x in g) / n) / max(k - 1, 1)
    s2b = max((msb - msw) / n0, 0.0)
    return s2b / (s2b + msw) if (s2b + msw) > 0 else float("nan"), n0


for lvl in ["cluster", "family"]:
    grp = defaultdict(list)
    for u in units:
        grp[u[lvl]].append(u["fail"])
    icc, n0 = anova_icc(list(grp.values()))
    nf = sum(1 for v in grp.values() if any(v))
    res[f"ed6_icc_{lvl}"] = {"icc": icc, "groups": len(grp), "groups_with_fail": nf, "n0": n0}
    txt.append(f"ed6 VBL failure ICC by {lvl}: {icc:.3f} (groups {len(grp)}, with a failure {nf}, n0 {n0:.2f})")

(out / "s8r_floor.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
(out / "s8r_floor.txt").write_text("\n".join(txt), encoding="utf-8")
print("status ok")
