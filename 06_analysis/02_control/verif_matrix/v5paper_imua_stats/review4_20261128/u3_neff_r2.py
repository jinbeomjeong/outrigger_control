"""Kish / design-effect effective sample size of the U-3 bundle per setting (S-4 of stats review 3).

Replaces ``v5paper_imua_stats/u3_neff.py`` (left unchanged: it reads a control scratchpad copy of the map
and uses assumed ICC values). Changes:
  * the cluster map is a required argument and its SHA-256 is checked (sealed candidate
    ``u3_cluster_map_r1.csv``, prefix baf8aaa6);
  * the READY-time ICC is estimated from the stored 436.8 U-3 records (record items ``id`` / ``key``
    and ``t_ready_s`` only; lines without READY are left out), one-way ANOVA ICC(1) for unbalanced
    groups, per setting, for both columns ``cluster`` and ``resample_unit``;
  * the assumed-ICC grid of the old script is kept as a sensitivity (0.90 / 0.92 / 0.93 / 0.946);
  * optional ``--expect <u3_r1_neff.json>``: the ICC / n_eff values must equal the stats review 3 output
    (|diff| <= 1e-9), exit 1 otherwise.
n_eff = N / (1 + (m_w - 1) * ICC), m_w = line-weighted mean unit size; Kish units = N^2 / sum m_i^2.

Usage: python -I -B u3_neff_r2.py --map <u3_cluster_map_r1.csv> --las-dir <v5_rerun/las_k1> --out <json>
         [--expect <u3_r1_neff.json>]
Exit 0 = written (and equal to --expect), 1 = --expect mismatch, 2 = input / sha error.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

MAP_SHA_PREFIX = "baf8aaa6"
ICC_GRID = (0.90, 0.92, 0.93, 0.946)
STUDIES = ("slope", "h6", "h9", "g6", "g8", "p3b", "x426b", "C", "D")


def icc1(groups: list[list[float]]) -> tuple[float, int, int]:
    g = [np.asarray(x, float) for x in groups if len(x)]
    k = len(g)
    n = np.array([len(x) for x in g])
    big_n = n.sum()
    allv = np.concatenate(g)
    gm = allv.mean()
    ssb = sum(len(x) * (x.mean() - gm) ** 2 for x in g)
    ssw = sum(((x - x.mean()) ** 2).sum() for x in g)
    msb, msw = ssb / (k - 1), ssw / (big_n - k)
    n0 = (big_n - (n ** 2).sum() / big_n) / (k - 1)
    return float((msb - msw) / (msb + (n0 - 1) * msw)), int(k), int(big_n)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True)
    ap.add_argument("--las-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--expect")
    a = ap.parse_args()
    mp = Path(a.map)
    las = Path(a.las_dir)
    if not mp.is_file() or not las.is_dir():
        print(json.dumps({"status": "input_missing"}))
        return 2
    map_sha = hashlib.sha256(mp.read_bytes()).hexdigest()
    if not map_sha.startswith(MAP_SHA_PREFIX):
        print(json.dumps({"status": "map_sha_mismatch", "sha": map_sha[:16]}))
        return 2
    rows = list(csv.DictReader(mp.open(encoding="utf-8")))
    out: dict = {"map": str(mp), "map_sha256": map_sha, "rows": len(rows), "las_files": {}}
    for f in sorted(las.glob("u3_*_V0.json")) + sorted(las.glob("u3_*_VB.json")):
        out["las_files"][f.name] = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
    for col in ("cluster", "resample_unit"):
        unit = {(r["study"], r["key"]): r[col] for r in rows}
        sizes: dict[str, int] = defaultdict(int)
        for u in unit.values():
            sizes[u] += 1
        m = np.array(list(sizes.values()), float)
        big_n = m.sum()
        mw = float((m ** 2).sum() / big_n)
        rec = {"units": len(m), "max": int(m.max()), "kish_units": float(big_n ** 2 / (m ** 2).sum()),
               "m_weighted": mw}
        for setting in ("V0", "VB"):
            g: dict[str, list[float]] = defaultdict(list)
            missing = 0
            for st in STUDIES:
                obj = json.loads((las / f"u3_{st}_{setting}.json").read_text(encoding="utf-8"))
                for r in obj.get("records") or obj.get("results") or []:
                    key = r.get("id") or r.get("key")
                    t = r.get("t_ready_s")
                    if isinstance(t, (int, float)) and not isinstance(t, bool):
                        g[unit[(st, key)]].append(float(t))
                    else:
                        missing += 1
            rho, k, n_obs = icc1(list(g.values()))
            rec[setting] = {"icc_ready": rho, "units_with_ready": k, "rows_with_ready": n_obs,
                            "rows_ready_missing": missing, "deff": 1 + (mw - 1) * rho,
                            "n_eff": float(big_n / (1 + (mw - 1) * rho))}
        rec["n_eff_by_assumed_icc"] = {f"{r:g}": float(big_n / (1 + (mw - 1) * r)) for r in ICC_GRID}
        out[col] = rec
    status = "ok"
    if a.expect:
        exp = json.loads(Path(a.expect).read_text(encoding="utf-8"))
        diffs = {}
        for col in ("cluster", "resample_unit"):
            for fld in ("units", "kish_units", "m_weighted"):
                diffs[f"{col}.{fld}"] = abs(out[col][fld] - exp[col][fld])
            for s in ("V0", "VB"):
                for fld in ("icc_ready", "n_eff", "deff", "rows_with_ready", "rows_ready_missing"):
                    diffs[f"{col}.{s}.{fld}"] = abs(out[col][s][fld] - exp[col][s][fld])
        out["expect"] = {"file": a.expect, "max_abs_diff": max(diffs.values()),
                         "worst": max(diffs, key=diffs.get)}
        if out["expect"]["max_abs_diff"] > 1e-9:
            status = "expect_mismatch"
    out["status"] = status
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": status, "n_eff_resample_unit": {s: round(out["resample_unit"][s]["n_eff"], 1)
                                                               for s in ("V0", "VB")}}))
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
