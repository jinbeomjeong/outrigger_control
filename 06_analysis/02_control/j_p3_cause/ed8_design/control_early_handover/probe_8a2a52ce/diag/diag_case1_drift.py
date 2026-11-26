"""Diagnosis case 1, twist drift path in the post-event LEVEL tail (d08 way): per 5 s window the
twist load rate dD/dt (T4h lsb_ib_twist_load_N = nu^T F), the executed rates nu^T v_s (plant
sref, oil volume coordinate) and nu^T v_x (plant x, piston), per-leg force rates, the plant fields
of the locked legs (line_fill_gate, seal), and the twist relax test inputs (|D| window rise).

Usage: conda run -n dynamics-dev python -I -B diag_case1_drift.py
Output: diag_case1_drift_out.txt
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed7-impl")
LEGS = ("FL", "FR", "RL", "RR")
STEMS = {"A": "R12_bottom-FR-Fs4-o0.075-RE1bF-ready_P89-A-VBM",
         "H3": "R12_bottom-FR-Fs4-o0.075-RE1bF-ready_P89-H3-VBM"}


def geometry():
    sys.path.insert(0, str(WT / "03_src"))
    from outrigger_sim.control.c2 import C2Geometry
    from outrigger_sim.params import load_params

    return np.asarray(C2Geometry.from_params(load_params()).twist_vector, float)


def longest(path: Path, tkey: str) -> dict:
    z = np.load(path, allow_pickle=False)
    objs = sorted({k.split("|")[0] for k in z.files})
    best = max(objs, key=lambda o: len(z[f"{o}|{tkey}"]) if f"{o}|{tkey}" in z.files else 0)
    return {k.split("|", 1)[1]: z[k] for k in z.files if k.startswith(best + "|")}


nu = geometry()
recs = {json.loads(x)["diag"]["stem"]: json.loads(x)
        for x in (RAW / "runs.jsonl").read_text("utf-8").splitlines()}
out = [f"nu {np.round(nu, 4).tolist()}"]
for arm, stem in STEMS.items():
    te = float(recs[stem]["t_event_s"])
    z = dict(np.load(RAW / "t4h" / f"{stem}.npz", allow_pickle=False))
    plant = longest(RAW / "logs" / f"{stem}_plant.npz", "t")
    out.append(f"===== {arm}: plant fields {sorted(k for k in plant if not k.startswith('_'))[:80]}")
    t = z["t_s"]
    D = z["lsb_ib_twist_load_N"]
    F = z["true_force_N"]
    tp = plant["t"]
    for w0 in np.arange(10.0, 60.0, 5.0):
        a, b = te + w0, te + w0 + 5.0
        m = (t >= a) & (t < b)
        if m.sum() < 10:
            continue
        ia, ib = int(np.argmin(np.abs(tp - a))), int(np.argmin(np.abs(tp - b)))
        dt = tp[ib] - tp[ia]
        vs = (plant["sref"][ib] - plant["sref"][ia]) / dt
        vx = (plant["x"][ib] - plant["x"][ia]) / dt
        k = np.flatnonzero(m)
        dD = (D[k[-1]] - D[k[0]]) / (t[k[-1]] - t[k[0]])
        dF = (F[k[-1]] - F[k[0]]) / (t[k[-1]] - t[k[0]])
        row = {"w0": float(w0), "D_kN": [round(float(D[k[0]]) / 1e3, 2), round(float(D[k[-1]]) / 1e3, 2)],
               "dD_kN_s": round(float(dD) / 1e3, 4),
               "nu_vs_mm_s": round(float(nu @ vs) * 1e3, 5), "nu_vx_mm_s": round(float(nu @ vx) * 1e3, 5),
               "k_eff_vs_MN_m": round(float(dD / (nu @ vs)) / 1e6, 2) if abs(nu @ vs) > 1e-10 else None,
               "vs_mm_s": np.round(vs * 1e3, 4).tolist(), "vx_mm_s": np.round(vx * 1e3, 4).tolist(),
               "dF_kN_s": np.round(dF / 1e3, 4).tolist(),
               "F_kN_end": np.round(F[k[-1]] / 1e3, 2).tolist()}
        for key in ("line_fill_gate.x", "line_fill_gate.fill_m", "locked"):
            if key in plant:
                row[key] = np.round(np.asarray(plant[key][ib], float), 6).tolist()
        out.append("  " + json.dumps(row))
text = "\n".join(out)
(HERE / "diag_case1_drift_out.txt").write_text(text, "utf-8")
print(text.encode("ascii", "replace").decode())
