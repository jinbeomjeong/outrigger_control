"""WARN_PROBE_STIFFNESS_OUT_OF_RANGE census on the edition 6 probe T4h (read only).

For every probe line: the raw median stiffness-ratio warnings (time, ratio) from T4h meta
events and the phase at that time; also the same for the D0 run (390f88a9) and the j9_main
VBJ T4h of the same keys as references. The warning band is (0.8, 2.3)
(``R8Settings.stiffness_warning_range``). Output: p2_stiffness_warn.json (this folder).
control-expert 2026-11-24.
"""
import json
from pathlib import Path

import numpy as np

J = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs")
OUT = Path(__file__).resolve().parent
SRC = {"probe": J / "1bd405c8/ed6_probe_a1/ed6_probe_t4h",
       "d0": J / "390f88a9/d0_plant_split_a1/d0_plant_split_t4h",
       "j9main": J / "606f8713/j9main_a1/j9_main_t4h"}
res = {}
for name, folder in SRC.items():
    for p in sorted(folder.glob("R12*.npz")):
        if name == "j9main" and not p.stem.endswith("_VBJ"):
            continue
        z = np.load(p, allow_pickle=False)
        ev = json.loads(str(z["meta_json"]))["events"]
        t = z["t_s"]
        ph = z["phase"]
        out = []
        probes = [round(e[0], 1) for e in ev if e[1].startswith("probe_") or e[1].startswith("INFO_PROBE")]
        for e in ev:
            if e[1].startswith("WARN_PROBE_STIFFNESS_OUT_OF_RANGE"):
                i = int(np.searchsorted(t, e[0] - 1e-9))
                out.append({"t_s": round(e[0], 2), "ratio": float(e[1].split(":")[1]),
                            "phase": str(ph[min(i, len(ph) - 1)])})
        res[f"{name}:{p.stem}"] = out
(OUT / "p2_stiffness_warn.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
for k, v in res.items():
    if v:
        print(k, v)
print("files", len(res), "with warning", sum(1 for v in res.values() if v))
