"""Exact comparison of a short eps = 0 run with the stored flow-off run: raw signals up to the shorter record.

Usage: python -I bit_compare.py <short case folder>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

STORED = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_FINAL-REP_20261030_223359\S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0")
NEW = Path(sys.argv[1])
FILES = ("record/record.npz", "r8_series.npz", "step_series.npz", "completion_series.npz", "controller_commands.npz")
TIME_KEYS = ("t", "t_s")
SERIES_EXCLUDED_TAIL = 0
out = {"new": str(NEW), "stored": str(STORED), "files": {}}
all_same = True
for rel in FILES:
    pa, pb = NEW / rel, STORED / rel
    if not pa.exists():
        out["files"][rel] = {"missing_in_new": True}
        continue
    a, b = np.load(pa, allow_pickle=False), np.load(pb, allow_pickle=False)
    row = {"arrays": 0, "values": 0, "same": [], "different": {}, "not_time_series": []}
    tkey = next((k for k in TIME_KEYS if k in a.files), None)
    n_t = None if tkey is None else min(len(a[tkey]), len(b[tkey]))
    for k in a.files:
        if k not in b.files:
            row["different"][k] = "absent in stored"
            continue
        x, y = a[k], b[k]
        if x.dtype.kind not in "fiubU" or x.ndim == 0:
            continue
        if tkey is None or not len(x) or len(x) != len(a[tkey]):
            row["not_time_series"].append(k)
            continue
        x, y = x[:n_t], y[:n_t]
        row["arrays"] += 1
        row["values"] += x.size
        if x.dtype.kind == "f":
            same = (x == y) | (np.isnan(x) & np.isnan(y))
        else:
            same = x == y
        if same.all():
            row["same"].append(k)
        else:
            mask = same.reshape(n_t, -1).all(axis=1)
            i = int(np.argmin(mask))
            row["different"][k] = {"first_index": i, "t": float(a[tkey][i]), "n_rows_diff": int((~mask).sum()),
                                   "max_abs": None if x.dtype.kind == "U" else float(np.nanmax(np.abs((x.astype(float) - y.astype(float)))))}
    row["time_key"], row["compared_rows"] = tkey, n_t
    row["t_last"] = None if tkey is None else float(a[tkey][n_t - 1])
    all_same &= not row["different"]
    out["files"][rel] = row
sa, sb = None, None
ra = json.loads((NEW / "result.json").read_text(encoding="utf-8")) if (NEW / "result.json").exists() else {}
rb = json.loads((STORED / "result.json").read_text(encoding="utf-8"))
if ra:
    diff = {k: (ra["args"].get(k), rb["args"].get(k)) for k in set(ra["args"]) | set(rb["args"]) if ra["args"].get(k) != rb["args"].get(k)}
    out["args_diff"] = diff
    out["settle_reference_same"] = ra.get("settle_reference") == rb.get("settle_reference")
    out["rut_reference_same"] = ra.get("rut_reference") == rb.get("rut_reference")
    n = min(len(ra["s9_rows"]), len(rb["s9_rows"]))
    bad = [k for k in ra["s9_rows"][0] if any(ra["s9_rows"][i].get(k) != rb["s9_rows"][i].get(k) for i in range(n))]
    out["s9_rows"] = {"compared": n, "keys_different": bad}
    out["params_sha_same"] = ra["meta"].get("params_sha256") == rb["meta"].get("params_sha256")
    out["scm_run_sha_same"] = ra["meta"].get("scm_run_sha256") == rb["meta"].get("scm_run_sha256")
    out["us_per_step"] = ra.get("us_per_step")
    out["wall_s"] = ra.get("wall_s")
    out["settle_wall_s"] = ra.get("settle_wall_s")
    all_same &= not bad and out["settle_reference_same"] and out["params_sha_same"]
out["all_same"] = bool(all_same)
(NEW.parent / "bit_compare.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
for rel, row in out["files"].items():
    print(rel, {k: (v if k != "same" else len(v)) for k, v in row.items()})
print({k: out.get(k) for k in ("args_diff", "s9_rows", "settle_reference_same", "rut_reference_same", "params_sha_same", "scm_run_sha_same", "wall_s", "settle_wall_s", "us_per_step", "all_same")})
