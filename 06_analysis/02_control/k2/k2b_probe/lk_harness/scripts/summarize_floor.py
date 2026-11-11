"""Compare the front-FLOOR harness S (on / off) with Chrono E2_b16 and the all-LOCK on arm.

Usage: python -I -B summarize_floor.py <floor_on.json> <floor_off.json> <b16_on_l1r.json>
           <e2_summary.json> <out.json>
"""

import json
import sys
from pathlib import Path

import numpy as np

FL, FR, RL, RR = range(4)
WINDOW = "S_hold2s_kN_per_mm"


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def items(s: np.ndarray) -> dict:
    diag_rr = s[RR, FR] + s[RR, RL]
    received = s[FR, FR] + s[FR, RL] + s[RL, FR] + s[RL, RL]
    return {"S_FL_RR": s[FL, RR], "diag_pair_FRRL_on_FL": s[FL, FR] + s[FL, RL],
            "S_RR_RL": s[RR, RL], "diag_pair_FRRL_on_RR": diag_rr,
            "loss_per_received_kN": -diag_rr / received,
            "alpha_adj_rear_RR_from_RL": -s[RR, RL] / s[RL, RL],
            "S_FL_FL": s[FL, FL], "S_FR_FR": s[FR, FR], "S_RL_RL": s[RL, RL], "S_RR_RR": s[RR, RR]}


floor_on, floor_off, lock_on, e2 = (load(p) for p in sys.argv[1:5])
matrices = {"chrono": np.asarray(e2["S_chrono_kN_per_mm"], float),
            "floor_on": np.asarray(floor_on["measured"][WINDOW], float),
            "floor_off": np.asarray(floor_off["measured"][WINDOW], float),
            "all_lock_on": np.asarray(lock_on["measured"][WINDOW], float)}
table = {name: {key: float(value) for key, value in items(s).items()} for name, s in matrices.items()}
rms = {name: float(np.sqrt(np.mean((s - matrices["chrono"]) ** 2)))
       for name, s in matrices.items() if name != "chrono"}
front_columns = {name: matrices[name][:, [FL, FR]].round(3).tolist()
                 for name in ("floor_on", "floor_off", "all_lock_on")}
record = {"window": WINDOW, "items": table, "rms_vs_chrono": rms, "front_columns": front_columns,
          "matrices": {name: s.round(4).tolist() for name, s in matrices.items()},
          "states": {"floor_on": [floor_on["state"]["pad_force_kN"], floor_on["modes"],
                                  floor_on["state"]["crawler_spheres_active"]],
                     "floor_off": [floor_off["state"]["pad_force_kN"], None,
                                   floor_off["state"]["crawler_spheres_active"]],
                     "chrono_base_kN": floor_on["chrono_base_kN"]},
          "diag_pair_run_dF_kN": {"floor_on": floor_on["diag_pair_FR_RL_dF_kN"],
                                  "floor_off": floor_off["diag_pair_FR_RL_dF_kN"],
                                  "chrono": e2["diag_FRRL"]["measured_dF_kN"]}}
Path(sys.argv[5]).write_text(json.dumps(record, indent=1), encoding="utf-8")
names = list(matrices)
print("item".ljust(28) + "".join(n.rjust(13) for n in names))
for key in table["chrono"]:
    print(key.ljust(28) + "".join(f"{table[n][key]:13.4f}" for n in names))
print("rms_vs_chrono", {k: round(v, 4) for k, v in rms.items()})
for name in names:
    print(name)
    for row in matrices[name]:
        print("  " + " ".join(f"{v:8.3f}" for v in row))
print("diag run dF", record["diag_pair_run_dF_kN"])
