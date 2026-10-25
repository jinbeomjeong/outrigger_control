"""Evaluate candidate twist-work judge rules on c36_work_def.py output (orig_bins, 0.5 s).

Usage: python -I c36_work_rules.py <work_json> <affected_json> <episodes_dir> [extra_case_dir ...]
Forced window: settle ramp end (ramp_s) / forced retraction end (depth / (speed_fraction v_max)).
"""
import json
import sys
from pathlib import Path

V_MAX = 0.020924
LIM = 20.0
rows = json.loads(open(sys.argv[1], encoding="utf-8").read())
aff = set(json.loads(open(sys.argv[2], encoding="utf-8").read())["affected"])
eps = Path(sys.argv[3])
pp = {"ML78_ep0", "ML78_ep1", "ML78_ep3", "ML00_ep5", "ML21_ep1", "ML90_ep1"}


def forced_end(case):
    ep = json.loads((eps / case / "result.json").read_text(encoding="utf-8")).get("episode") or {}
    k = ep.get("kind")
    if k == "settle":
        return float(ep.get("ramp_s") or 0.0), k
    if k == "retract":
        return float(ep["depth_m"]) / (float(ep.get("speed_fraction") or 1.0) * V_MAX), k
    return 0.0, k


def clusters(bins, a0, lim):
    """Clusters of consecutive bins (start >= a0) with W > lim; returns list of (start, sum)."""
    out, cur = [], None
    for i, w in enumerate(bins):
        a = 0.5 * i
        if a < a0 - 1e-9 or w <= lim:
            if cur:
                out.append(cur)
                cur = None
            continue
        cur = [a, w] if cur is None else [cur[0], cur[1] + w]
    if cur:
        out.append(cur)
    return out


res = []
for r in rows:
    if "error" in r or not r.get("orig_bins"):
        continue
    fe, kind = forced_end(r["case"])
    b = r["orig_bins"]
    a_r1 = 1.5
    a_r2 = max(1.5, fe + 1.5) if kind in ("settle", "retract") else 1.5   # ramp end + 1.5
    a_r3 = max(1.5, fe)  # exclude forced window only
    def mx(a0):
        v = [w for i, w in enumerate(b) if 0.5 * i >= a0 - 1e-9]
        return max(v) if v else None
    c1 = clusters(b, a_r3, LIM)
    res.append({"case": r["case"], "kind": kind, "fe": round(fe, 2),
                "R0": mx(1.5), "R2": mx(a_r2), "R3": mx(a_r3),
                "clusters": c1, "n_clusters": len(c1),
                "second": c1[1][1] if len(c1) > 1 else 0.0,
                "aff": r["case"] in aff, "pp": r["case"] in pp})
for key, desc in (("R0", "rev52: max bin >= 1.5 s"),
                  ("R2", "max bin >= forced end + 1.5 s"),
                  ("R3", "max bin >= max(1.5, forced end)")):
    over = [x for x in res if x[key] is not None and x[key] > LIM]
    print(f"{desc}: over {len(over)} (aff {sum(x['aff'] for x in over)}, pp {sum(x['pp'] for x in over)}, "
          f"non-aff {sum(not x['aff'] for x in over)})")
    print("   non-aff:", [(x["case"], x["kind"], x["fe"], round(x[key], 1)) for x in over if not x["aff"]])
over = [x for x in res if x["n_clusters"] >= 2]
print(f"two+ clusters > {LIM} J after max(1.5, forced end): {len(over)} "
      f"(aff {sum(x['aff'] for x in over)}, pp {sum(x['pp'] for x in over)})")
for x in sorted(over, key=lambda x: -x["second"]):
    print("   ", x["case"], x["kind"], "aff" if x["aff"] else "-", "PP" if x["pp"] else "",
          [(c[0], round(c[1], 1)) for c in x["clusters"]])
print("pingpong cases detail:")
for x in res:
    if x["pp"] or x["case"] in ("ML24_ep7", "ML42_ep6", "ML33_ep1", "ML90_ep7", "ML80_ep2", "ML74_ep7", "ML33_ep4"):
        r = next(r for r in rows if r["case"] == x["case"])
        print("   ", x["case"], "fe", x["fe"], "bins", r["orig_bins"][:16], "clusters",
              [(c[0], round(c[1], 1)) for c in x["clusters"]])
# second-cluster threshold scan
for lim in (10.0, 15.0, 20.0):
    n = [x["case"] for x in res
         if len([c for c in clusters(next(r for r in rows if r["case"] == x["case"])["orig_bins"],
                                     max(1.5, x["fe"]), lim)]) >= 2]
    print(f"lim {lim}: two+ clusters {len(n)}: {n}")
