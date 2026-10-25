"""C / D regression: c37 vs c36. (1) raw record identity (pads.npz, r8_series.npz, s8_series.npz,
controller_events.json) per run; (2) verify rows keyed by (item, case): passed and value equality.
"""
import json
import os
import numpy as np

# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
# (the scratchpad original also named the cad-run55 re-judge folder but never read it)
# ---
ROOT = str(REPO / r"07_results\S8")
N37 = ROOT + r"\c37_20261025_180821"
N36 = ROOT + r"\c36_20261025_155317"

for grp, runs in (("C_gate", ("E_RE1bF_Fs0", "E_RE1bP_Fs0")), ("D_fs24", ("MLJ_FS24_Fs0", "MLJ_FS24_Fs8"))):
    for r in runs:
        a, b = os.path.join(N37, grp, r), os.path.join(N36, grp, r)
        rep = {}
        for f in ("pads.npz", "r8_series.npz", "s8_series.npz"):
            if not (os.path.isfile(os.path.join(a, f)) and os.path.isfile(os.path.join(b, f))):
                rep[f] = "missing"
                continue
            x, y = np.load(os.path.join(a, f), allow_pickle=True), np.load(os.path.join(b, f), allow_pickle=True)
            diff = []
            for k in x.files:
                if k not in y.files:
                    diff.append((k, "absent"))
                    continue
                u, v = x[k], y[k]
                if u.shape != v.shape:
                    diff.append((k, "shape", u.shape, v.shape))
                elif u.dtype.kind in "fc":
                    m = float(np.nanmax(np.abs(u - v))) if u.size else 0.0
                    if m > 0 or not np.array_equal(np.isnan(u), np.isnan(v)):
                        diff.append((k, m))
                elif not np.array_equal(u, v):
                    diff.append((k, "neq"))
            rep[f] = diff if diff else "identical"
        ea = json.load(open(os.path.join(a, "controller_events.json"), encoding="utf-8"))
        eb = json.load(open(os.path.join(b, "controller_events.json"), encoding="utf-8"))
        rep["events"] = "identical" if ea == eb else f"differ ({len(ea)} vs {len(eb)}); new-only " + str(
            [e for e in ea if e not in eb][:8]) + " old-only " + str([e for e in eb if e not in ea][:8])
        print(grp, r)
        for k, v in rep.items():
            print("   ", k, str(v)[:600])

    v37 = json.load(open(os.path.join(N37, grp, "verify_S8C.json"), encoding="utf-8"))
    cands = [os.path.join(N36, grp, "verify_S8C.json")]
    for old in cands:
        v36 = json.load(open(old, encoding="utf-8"))
        k36 = {(r["item"], r["case"]): r for r in v36["rows"]}
        new_only, changed, same = [], [], 0
        for r in v37["rows"]:
            key = (r["item"], r["case"])
            if key not in k36:
                new_only.append(key)
                continue
            o = k36[key]
            if o.get("passed") != r.get("passed") or json.dumps(o.get("value"), default=str) != json.dumps(r.get("value"), default=str):
                changed.append((key, o.get("passed"), r.get("passed"), str(o.get("value"))[:150], str(r.get("value"))[:150]))
            else:
                same += 1
        print("rows", grp, "vs", old, "| same", same, "changed", len(changed), "new-only", len(new_only),
              "old n", len(v36["rows"]), "judge", v36["meta"].get("judge_revision", "")[:40])
        for x in changed:
            print("   CHG", x)
        for x in new_only:
            print("   NEW", x[0][:120], x[1])
