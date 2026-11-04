"""V-5 check of the rigid rows: where on and off first differ, per key, with the size of the first differences, and the
first flow-limited time. Reads the run folders only. Writes rigid_prefix.json.

Run: conda run -n dynamics-dev python -I rigid_prefix.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control")
HERE = ROOT / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono"
S8 = ROOT / "07_results/S8"
CASES = {"R2": "K24_top_fdown3.5_Fs4", "R4": "K24_top_roll5.5_Fs4", "R16": "G1L_RE1bF_FL_top_o050_Fs4", "R12": "E_G4_Fs4",
         "R6": "K0V_top_rpB_Fs0", "R8": "A_middle_rpB_Fs0", "R9": "A_bottom_rpB_Fs0"}
out = {}
for cid, case in CASES.items():
    on = sorted(S8.glob(f"coupled_eta085_{case}_2*"))[-1] / case
    off = sorted(S8.glob(f"final_{case}_2*"))[-1] / case
    res = json.loads((on / "result.json").read_text(encoding="utf-8"))
    row = {"start_t_s": res["runner"]["start_t_s"]}
    with np.load(on / "flow_series.npz", allow_pickle=True) as z:
        rows, cols = z["rows"], [str(c) for c in z["columns"]]
    t = rows[:, cols.index("t")]
    lim = rows[:, cols.index("limited_mask")].astype(int) > 0
    row["flow_t_first"] = float(t[0])
    row["first_limited_t"] = float(t[np.argmax(lim)])
    qd = rows[:, cols.index("Q_dem")]
    row["first_Qdem_positive_t"] = float(t[np.argmax(qd > 0)])
    keys = {}
    for fname in ("r8_series.npz", "s8_series.npz"):
        with np.load(on / fname, allow_pickle=False) as a, np.load(off / fname, allow_pickle=False) as b:
            for k in sorted(set(a.files) & set(b.files)):
                x, y = a[k], b[k]
                if x.dtype.kind not in "fiub" or x.ndim == 0:
                    continue
                n = min(len(x), len(y))
                same = ((x[:n] == y[:n]) | (np.isnan(x[:n]) & np.isnan(y[:n]))) if x.dtype.kind == "f" else x[:n] == y[:n]
                same = same.reshape(n, -1).all(axis=1)
                if same.all():
                    continue
                i = int(np.argmin(same))
                tk = a["t"][i]
                dx = np.nan_to_num(np.abs(x[i].astype(float) - y[i].astype(float))).max()
                keys[f"{fname[:2]}:{k}"] = [float(tk), float(dx)]
    row["first_diff"] = dict(sorted(keys.items(), key=lambda kv: kv[1][0])[:12])
    with np.load(on / "record/record.npz", allow_pickle=False) as a, np.load(off / "record/record.npz", allow_pickle=False) as b:
        rec = {}
        for k in ("u_applied", "F_cyl", "s_motor"):
            x, y = a[k], b[k]
            n = min(len(x), len(y))
            same = (x[:n] == y[:n]).reshape(n, -1).all(axis=1)
            i = int(np.argmin(same)) if not same.all() else None
            rec[k] = None if i is None else [float(a["t"][i]), float(np.abs(x[i] - y[i]).max())]
        row["record_first_diff"] = rec
    out[cid] = row
(HERE / "rigid_prefix.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out, indent=0))
