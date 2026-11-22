"""Design inputs for the v5paper A-type (inclinometer) bundle review.

Sources (allowed): the two public check runs (imua_check, imua_check_a2; 50 keys x 2 arms each)
and 436.8 stored *record items* (READY times, identifiers) of H-1 (D-1), H-3 (U-3), H-4 (U-6).
No 436.8 H-3/H-4 grade fields are read (only id / t_ready_s / limit fields).

Outputs a JSON file with:
  check.*   : per-row table summary, A - R0 READY deltas, ICC within case cluster, E-2 event rows
  d1.*      : D-1 structure (rows, clusters, eps variants), READY ICC within key, READY margins
  u3.*, u6.*: structure (rows, heuristic clusters), READY ICC within heuristic cluster
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control")
V5 = ROOT / "06_analysis/03_hydraulic/coupled/v5"
LAS = ROOT / "06_analysis/02_control/v5_rerun/las_k1"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def icc_oneway(groups: list[list[float]]) -> dict:
    """ANOVA ICC(1) for unbalanced groups (groups with >= 1 member; needs >= 2 groups of size >= 2)."""
    g = [np.asarray(x, float) for x in groups if len(x) >= 1]
    g = [x[np.isfinite(x)] for x in g]
    g = [x for x in g if len(x) >= 1]
    k = len(g)
    n = np.array([len(x) for x in g])
    N = n.sum()
    if k < 2 or (n >= 2).sum() < 2:
        return {"icc": None, "k": int(k), "N": int(N)}
    allv = np.concatenate(g)
    gm = allv.mean()
    ssb = sum(len(x) * (x.mean() - gm) ** 2 for x in g)
    ssw = sum(((x - x.mean()) ** 2).sum() for x in g)
    msb = ssb / (k - 1)
    msw = ssw / (N - k) if N > k else np.nan
    n0 = (N - (n ** 2).sum() / N) / (k - 1)
    icc = (msb - msw) / (msb + (n0 - 1) * msw) if np.isfinite(msw) else np.nan
    return {"icc": float(icc), "k": int(k), "N": int(N), "n0": float(n0), "msb": float(msb), "msw": float(msw)}


def check_runs() -> dict:
    out = {"sources": {}}
    arms = {
        "A-v5": (V5 / "imua_check/imua_check_R0.jsonl", V5 / "imua_check/imua_check_A-v5.jsonl"),
        "A2": (V5 / "imua_check_a2/imua_check_R0.jsonl", V5 / "imua_check_a2/imua_check_A2.jsonl"),
    }
    for arm, (r0p, ap) in arms.items():
        out["sources"][arm] = {str(r0p): sha(r0p)[:16], str(ap): sha(ap)[:16]}
        r0 = load_jsonl(r0p)
        aa = load_jsonl(ap)

        def jid(r):
            j = r["job"]
            return (j["case"], float(j["eps"]), j["setting"], j.get("eta_v"))

        r0m = {jid(r): r for r in r0}
        rows = []
        for r in aa:
            k = jid(r)
            b = r0m.get(k)
            ta = r["values"]["times"].get("t_first_ready_s")
            tb = b["values"]["times"].get("t_first_ready_s") if b else None
            fp = r.get("final_phase")
            ev_lost = (ta is not None) and (fp != "READY")
            ev_lost_r0 = (tb is not None) and (b.get("final_phase") != "READY") if b else None
            rows.append({
                "case": k[0], "eps": k[1], "setting": k[2], "eta": k[3],
                "cluster": f"{k[0]}|{k[2]}|{k[3]}",
                "group": ("VB-eta" if k[3] is not None else ("V0" if k[2] == "V0" else "normal-VB")),
                "t_ready_A": ta, "t_ready_R0": tb,
                "delta": (ta - tb) if (ta is not None and tb is not None) else None,
                "final_phase_A": fp, "ready_lost_A": ev_lost, "ready_lost_R0": ev_lost_r0,
                "n_ready_relevels_A": r.get("imua_check_g5", {}).get("n_ready_relevels"),
                "probe_att_change_R0": b["values"].get("probe_attitude_change_deg") if b else None,
                "probe_att_change_A": r["values"].get("probe_attitude_change_deg"),
            })
        d = [x["delta"] for x in rows if x["delta"] is not None]
        summ = {}
        for grp in ("V0", "VB-eta", "normal-VB", "all"):
            vals = [x["delta"] for x in rows if x["delta"] is not None and (grp == "all" or x["group"] == grp)]
            if vals:
                v = np.asarray(vals)
                summ[grp] = {"n": len(v), "median": float(np.median(v)), "p90": float(np.percentile(v, 90)),
                             "min": float(v.min()), "max": float(v.max()), "frac_pos": float((v > 0).mean())}
        clusters = defaultdict(list)
        for x in rows:
            if x["delta"] is not None:
                clusters[x["cluster"]].append(x["delta"])
        ev_rows = [f"{x['cluster']}|e{x['eps']}" for x in rows if x["ready_lost_A"]]
        ev_clusters = sorted({x["cluster"] for x in rows if x["ready_lost_A"]})
        vb_rows = [x for x in rows if x["setting"] == "VB"]
        vb_clusters = sorted({x["cluster"] for x in vb_rows})
        # within-cluster concordance of the binary event (VB rows)
        cl_ev = defaultdict(list)
        for x in vb_rows:
            cl_ev[x["cluster"]].append(1.0 if x["ready_lost_A"] else 0.0)
        out[arm] = {
            "n_rows": len(rows), "n_vb_rows": len(vb_rows), "n_vb_clusters": len(vb_clusters),
            "cluster_sizes_vb": {c: len(v) for c, v in cl_ev.items()},
            "delta_summary": summ, "delta_icc_within_cluster": icc_oneway(list(clusters.values())),
            "ready_lost_rows": ev_rows, "ready_lost_clusters": ev_clusters,
            "ready_lost_icc_vb": icc_oneway(list(cl_ev.values())),
            "ready_lost_R0_rows": [f"{x['cluster']}|e{x['eps']}" for x in rows if x["ready_lost_R0"]],
            "rows": rows,
        }
    return out


def d1_struct() -> dict:
    p = V5 / "resume_k1/h1_d1.jsonl"
    rows = load_jsonl(p)
    out = {"source": str(p), "sha16": sha(p)[:16]}
    j0 = rows[0]["job"].get("d1")
    out["job_d1_fields"] = sorted(j0.keys()) if isinstance(j0, dict) else str(type(j0))
    out["d1_fields"] = sorted(rows[0].get("d1", {}).keys()) if isinstance(rows[0].get("d1"), dict) else None
    recs = []
    for r in rows:
        jd = r["job"].get("d1")
        if isinstance(jd, dict):
            key = jd.get("key") or jd.get("id") or jd.get("row") or json.dumps(jd, sort_keys=True)
            fam = jd.get("family") or jd.get("group")
        else:
            key, fam = str(jd), None
        d1 = r.get("d1", {}) if isinstance(r.get("d1"), dict) else {}
        recs.append({"key": key, "family": fam, "eps": float(r["job"]["eps"]), "setting": r["job"]["setting"],
                     "t_ready": d1.get("t_ready_s"), "t_ready_limit": d1.get("t_ready_limit_s")})
    out["n_rows"] = len(recs)
    by_set = defaultdict(list)
    for x in recs:
        by_set[x["setting"]].append(x)
    out["per_setting"] = {}
    for s, xs in by_set.items():
        cl = defaultdict(list)
        for x in xs:
            cl[x["key"]].append(x)
        sizes = [len(v) for v in cl.values()]
        fam_cl = defaultdict(set)
        for x in xs:
            fam_cl[x["family"]].add(x["key"])
        tr = [[y["t_ready"] for y in v if y["t_ready"] is not None] for v in cl.values()]
        margins = [x["t_ready_limit"] - x["t_ready"] for x in xs if x["t_ready"] is not None and x["t_ready_limit"] is not None]
        m = np.asarray(margins) if margins else np.asarray([np.nan])
        out["per_setting"][s] = {
            "rows": len(xs), "clusters_key": len(cl),
            "cluster_size_hist": {str(k): sizes.count(k) for k in sorted(set(sizes))},
            "eps_values": sorted({x["eps"] for x in xs}),
            "families": {str(f): len(v) for f, v in fam_cl.items()},
            "ready_null_rows": sum(1 for x in xs if x["t_ready"] is None),
            "t_ready_icc_within_key": icc_oneway(tr),
            "ready_margin_s": {"n": int(np.isfinite(m).sum()), "p10": float(np.nanpercentile(m, 10)),
                               "median": float(np.nanmedian(m)),
                               "n_le_10": int((m <= 10).sum()), "n_le_20": int((m <= 20).sum()),
                               "n_le_30": int((m <= 30).sum()), "n_le_45": int((m <= 45).sum())},
        }
    out["recs"] = recs
    return out


def u3_cluster(idv: str) -> str:
    """Heuristic case cluster: strip magnitude / variant tokens (k@, Fs, m1.x, raised height, leg patch)."""
    t = idv.split("|")
    t = [re.sub(r"@k[0-9.]+$", "", x) for x in t]
    t = [x for x in t if not re.fullmatch(r"Fs[0-9]+", x) and not re.fullmatch(r"m[0-9.]+", x)]
    t = [x for x in t if not re.fullmatch(r"[0-9]+\.[0-9]+", x)]
    t = [x for x in t if not re.fullmatch(r"(FL|FR|RL|RR):[a-z]+[0-9]+", x)]
    return "|".join(t)


def u3_struct() -> dict:
    out = {"files": {}}
    allrows = defaultdict(list)
    for f in sorted(LAS.glob("u3_*.json")):
        obj = json.loads(f.read_text(encoding="utf-8"))
        rows = obj.get("records") or obj.get("results") or []
        setting = "VB" if f.stem.endswith("_VB") else "V0"
        suite = f.stem[3:].rsplit("_", 1)[0]
        out["files"][f.name] = {"sha16": sha(f)[:16], "rows": len(rows)}
        for r in rows:
            idv = r.get("id") or r.get("key")
            t = r.get("t_ready_s")
            if not isinstance(t, (int, float)) or isinstance(t, bool):
                t = None
            allrows[setting].append({"suite": suite, "id": idv, "cluster": suite + "::" + u3_cluster(idv), "t_ready": t})
    for s, xs in allrows.items():
        cl = defaultdict(list)
        for x in xs:
            cl[x["cluster"]].append(x["t_ready"])
        sizes = [len(v) for v in cl.values()]
        per_suite = defaultdict(lambda: [0, set()])
        for x in xs:
            per_suite[x["suite"]][0] += 1
            per_suite[x["suite"]][1].add(x["cluster"])
        m = np.asarray(sizes, float)
        out[s] = {"rows": len(xs), "clusters": len(cl),
                  "per_suite": {k: {"rows": v[0], "clusters": len(v[1])} for k, v in per_suite.items()},
                  "size_mean": float(m.mean()), "size_max": int(m.max()),
                  "kish_cluster_neff_if_icc1": float(m.sum() ** 2 / (m ** 2).sum()),
                  "t_ready_icc_within_cluster": icc_oneway([[y for y in v if y is not None] for v in cl.values()])}
    return out


def u6_struct() -> dict:
    out = {}
    cases = defaultdict(set)
    n = 0
    for f in sorted(LAS.glob("u6_*.json")):
        obj = json.loads(f.read_text(encoding="utf-8"))
        for r in obj.get("records", []):
            cases[r["case"]].add(r["controller"])
            n += 1
    out["rows"] = n
    out["cases"] = len(cases)
    out["controllers_per_case_hist"] = {str(k): sum(1 for v in cases.values() if len(v) == k) for k in range(1, 6)}
    fam = defaultdict(int)
    for c in cases:
        fam[c.split("|")[0] if "|" in c else c.split("-")[0]] += 1
    out["case_prefix_counts"] = dict(fam)
    return out


def main() -> None:
    res = {"check": check_runs(), "d1": d1_struct(), "u3": u3_struct(), "u6": u6_struct()}
    Path(sys.argv[1]).write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print("ok")


if __name__ == "__main__":
    main()
