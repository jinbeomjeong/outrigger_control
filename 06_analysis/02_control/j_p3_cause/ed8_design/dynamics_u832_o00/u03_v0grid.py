"""Stored V0 grid (touch_phase/acceptance/c4g2_only/grid, the files used by stats s30): pair union
and lift timing per (cluster, offset), within-cluster offset effect.

Usage: python -I -B u03_v0grid.py <out_folder>
"""
import json
import sys
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 500)
GRID = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance\c4g2_only\grid")
FILES = ["grid_r67_main.json", "grid_r67_top.json", "grid_r69_bottom.json", "grid_r69_top.json"]
out = Path(sys.argv[1])
rows = []
for fn in FILES:
    d = json.loads((GRID / fn).read_text(encoding="utf-8"))
    meta = d.get("meta", {})
    for job in d["results"]:
        runs = job.get("runs") or []
        items = runs.items() if isinstance(runs, dict) else enumerate(runs)
        for _, r in items:
            lifts = r.get("lifts") or {}
            pair = r.get("pair") or []
            row = {"file": fn, "level": job.get("level"), "fs_kN": job.get("fs_kN"),
                   "timing": job.get("timing"), "leg": job.get("leg"), "event": r.get("event"),
                   "offset_s": r.get("offset_s"), "t_ev_s": r.get("t_ev_s"),
                   "branch_t_s": job.get("branch_t_s"), "branch_phase": job.get("branch_phase"),
                   "phase_at_event": r.get("phase_at_event"), "pass": r.get("pass"),
                   "failed": "|".join(k for k, v in (r.get("gates") or {}).items() if not v),
                   "pair_union_s": r.get("pair_union_s"), "pair_last_touch_s": r.get("pair_last_touch_s"),
                   "sha": (r.get("commands_sha256") or "")[:12], "candidate": meta.get("candidate"),
                   "v5_setting": meta.get("v5_setting")}
            for k, leg in enumerate(pair):
                lf = lifts.get(leg) or {}
                row[f"p{k}_leg"] = leg
                row[f"p{k}_first_s"] = lf.get("first_s")
                row[f"p{k}_sum_s"] = lf.get("sum_s")
                row[f"p{k}_last_s"] = lf.get("last_touch_s")
                row[f"p{k}_n"] = lf.get("n")
                row[f"p{k}_gap_mm"] = lf.get("max_gap_mm")
            rows.append(row)
df = pd.DataFrame(rows)
df.to_csv(out / "u03_v0grid_rows.csv", index=False)
print("rows", len(df), "files", df.groupby("file").size().to_dict())
print("candidates", df["candidate"].unique(), "settings", df["v5_setting"].unique())
print("offsets", sorted(df["offset_s"].dropna().unique()))
fast = df[df["event"].isin(["RE1bF", "FS24"])]
piv = fast.pivot_table(index=["file", "event", "timing", "level", "leg", "fs_kN"], columns="offset_s",
                       values="pair_union_s", aggfunc="first")
piv.to_csv(out / "u03_v0grid_pair_union_pivot.csv")
print(piv.to_string())
# within-cluster difference o0.0 minus mean of others
cols = [c for c in piv.columns if c != 0.0]
dd = piv[0.0] - piv[cols].mean(axis=1)
summ = dd.groupby(level=["event", "timing", "level"]).agg(["count", "mean", "min", "max"])
print("\n== pair_union(o0.0) - mean(other offsets), V0, by event/timing/level ==")
print(summ.to_string())
summ.to_csv(out / "u03_v0grid_o0_minus_other.csv")
# argmax offset per cluster
am = piv.idxmax(axis=1)
print("\n== offset with the largest pair union, per cluster (counts) ==")
print(am.groupby(level=["event", "timing", "level"]).value_counts().to_string())
