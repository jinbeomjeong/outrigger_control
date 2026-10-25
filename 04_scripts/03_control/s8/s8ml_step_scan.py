"""ML-2: one-period (10 Hz) pressure steps in every run of the given batches.

For each run folder with pads.npz + r8_series.npz: the largest one-period step of the true rod
and head pressure at the controller samples (exact alignment: searchsorted, no -1), the D1 limit
100 bar, D1 fallback / head-fault events, the lock valve, rod dead length and the event kind.
The step uses the 1 ms record value at the sample (no sensor error: the error model adds
offset / noise of a few bar, small against 100 bar).

Usage: python -I s8ml_step_scan.py <out_csv> <batch_dir> [<batch_dir> ...]
A batch may be an ML batch (runs under bases/ and episodes/) or a flat batch.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

LIMIT_BAR = 100.0
LEGS = ("FL", "FR", "RL", "RR")


def runs(batch: Path):
    for sub in (batch, batch / "bases", batch / "episodes"):
        if not sub.is_dir():
            continue
        for d in sorted(sub.iterdir()):
            if d.is_dir() and (d / "pads.npz").exists() and (d / "r8_series.npz").exists():
                yield d


def scan(d: Path) -> dict:
    r8 = np.load(d / "r8_series.npz", allow_pickle=True)
    pads = np.load(d / "pads.npz", allow_pickle=True)
    t, tp = r8["t"], pads["t"]
    idx = np.clip(np.searchsorted(tp, t), 0, len(tp) - 1)
    pr = pads["rod_pressure"][idx] / 1e5
    ph = pads["head_pressure"][idx] / 1e5
    dpr, dph = np.diff(pr, axis=0), np.diff(ph, axis=0)
    out = {"run": d.name, "batch": d.parent.name if d.parent.name not in ("bases", "episodes")
           else d.parent.parent.name}
    for name, dp in (("rod", dpr), ("head", dph)):
        k, leg = np.unravel_index(np.argmax(np.abs(dp)), dp.shape)
        out[f"max_step_{name}_bar"] = round(float(dp[k, leg]), 1)
        out[f"max_step_{name}_leg"] = LEGS[leg]
        out[f"max_step_{name}_t"] = round(float(t[k + 1]), 2)
        out[f"n_over_{name}"] = int((np.abs(dp) > LIMIT_BAR).sum())
    res = {}
    if (d / "result.json").exists():
        res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    st = res.get("settings", {})
    meta = st.get("ml_meta", {})
    out["event"] = (st.get("episode", {}) or {}).get("kind") or meta.get("event") or st.get("event")
    if isinstance(out["event"], dict):
        out["event"] = out["event"].get("kind") or out["event"].get("name")
    out["rod_dead_m"] = (meta.get("rod_dead_length_m") or [None])[0]
    ev = []
    if (d / "controller_events.json").exists():
        ev = json.loads((d / "controller_events.json").read_text(encoding="utf-8"))
    ev = [str(e) for e in ev]
    out["d1_rod"] = ";".join(e.split("name='")[1].rstrip("')") for e in ev if "FAULT_REASON" in e)
    out["head_fault"] = ";".join(e.split("name='")[1].rstrip("')") for e in ev if "FAULT_HEAD" in e)
    return out


rows = []
for b in sys.argv[2:]:
    for d in runs(Path(b)):
        try:
            rows.append(scan(d))
        except Exception as exc:  # report and continue
            print("skip", d, exc)
with open(sys.argv[1], "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
for batch in sorted({r["batch"] for r in rows}):
    sel = [r for r in rows if r["batch"] == batch]
    mr = max(sel, key=lambda r: abs(r["max_step_rod_bar"]))
    mh = max(sel, key=lambda r: abs(r["max_step_head_bar"]))
    print(f"{batch}: runs {len(sel)}, rod step>100: {sum(r['n_over_rod'] > 0 for r in sel)} runs, "
          f"head step>100: {sum(r['n_over_head'] > 0 for r in sel)} runs; max rod {mr['max_step_rod_bar']} "
          f"({mr['run']} {mr['max_step_rod_leg']} {mr['max_step_rod_t']}), max head {mh['max_step_head_bar']} "
          f"({mh['run']} {mh['max_step_head_leg']} {mh['max_step_head_t']})")
    for r in sel:
        if r["n_over_rod"] or r["n_over_head"] or r["d1_rod"] or r["head_fault"]:
            print(f"   {r['run']:32s} ev={r['event']} L0r={r['rod_dead_m']} rod {r['max_step_rod_bar']:+7.1f} "
                  f"{r['max_step_rod_leg']} @{r['max_step_rod_t']} n{r['n_over_rod']} | head "
                  f"{r['max_step_head_bar']:+7.1f} {r['max_step_head_leg']} @{r['max_step_head_t']} "
                  f"n{r['n_over_head']} | {r['d1_rod']} {r['head_fault']}")
