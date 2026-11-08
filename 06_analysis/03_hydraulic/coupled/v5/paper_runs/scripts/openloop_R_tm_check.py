"""Cross-check of terramechanics-expert figures for V5-OPENLOOP-R (no new runs).

Per pad: max SCM pad normal force after lift start, final sinkage, Bekker scaling constant
C = z_end / F_max^(1/n) (n = 0.13, J1; same b and area across rows -> C should be row-independent if the
final sinkage is set by the max-load Bekker sinkage), and the lag at crawler lift-off
lag = C * F_lo^(1/n) - z_lo (Bekker sinkage of the lift-off load minus actual sinkage).
Units mm, kN. Output JSON to argv[1].
"""
import json
import sys
from pathlib import Path

import numpy as np

R = Path(r"C:\workspace\outrigger_control\07_results\S9")
B = R / "batch_V5-OPENLOOP-R_20261108_231840"
RUNS = {"V0_R992k": R / "batch_V5-OPENLOOP-V0_20261108_123517/P3a_J1_B_V0",
        "R888k": B / "P3a_J1_B_V0_R888k", "R600k": B / "P3a_J1_B_V0_R600k", "R300k": B / "P3a_J1_B_V0_R300k"}
N = 0.13
out = {}
for name, p in RUNS.items():
    res = json.loads((p / "result.json").read_text("utf-8"))
    z = np.load(p / "series.npz")
    t = z["t_s"]; pn = z["scm_pad_normal_N"]; sink = z["pad_sinkage_geometric_m"]
    tlo = res["p3a"]["P3a-2_liftoff"]["t_liftoff_s"]
    klo = int(np.searchsorted(t, tlo))
    lift = t > 8.0
    fmax = pn[lift].max(axis=0)
    zend = sink[-1]
    C = zend / fmax ** (1 / N)
    lag = C * pn[klo] ** (1 / N) - sink[klo]
    out[name] = {"F_max_kN": (fmax / 1e3).tolist(), "z_end_mm": (zend * 1e3).tolist(),
                 "C_rel": None, "C": C.tolist(),
                 "F_lo_kN": (pn[klo] / 1e3).tolist(), "z_lo_mm": (sink[klo] * 1e3).tolist(),
                 "lag_lo_mm": (lag * 1e3).tolist()}
c0 = np.array(out["V0_R992k"]["C"])
f0 = np.array(out["V0_R992k"]["F_max_kN"])
for name in out:
    out[name]["C_rel"] = (np.array(out[name]["C"]) / c0).tolist()
    out[name]["F_max_rel"] = (np.array(out[name]["F_max_kN"]) / f0).tolist()
Path(sys.argv[1]).write_text(json.dumps(out, indent=1), "utf-8")
for name, o in out.items():
    print(name, "Fmax", [round(v, 2) for v in o["F_max_kN"]], "Fmax_rel", [round(v, 4) for v in o["F_max_rel"]],
          "zend", [round(v, 2) for v in o["z_end_mm"]], "C_rel", [round(v, 3) for v in o["C_rel"]],
          "lag_lo", [round(v, 2) for v in o["lag_lo_mm"]])
