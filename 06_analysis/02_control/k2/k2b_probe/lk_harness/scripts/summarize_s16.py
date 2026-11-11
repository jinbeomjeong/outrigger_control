"""Judge the beta 1.6 on / off harness S against the Chrono M2 items (criteria of the request)."""
import json
import sys
from pathlib import Path

import numpy as np

on, off = (json.loads(Path(p).read_text(encoding="utf-8")) for p in sys.argv[1:3])
chrono = on["chrono_m2"]
items = ("S_RR_RL", "diag_pair_FRRL_on_RR", "loss_per_received_kN", "alpha_adj_rear_RR_from_RL")


def error(name: str, value: float) -> float:
    ref = chrono[name]
    return abs(value - ref) if name.startswith("alpha") else abs(value - ref) / abs(ref)


for arm in (on, off):
    print("arm", arm["lk_mode"], "k_n", np.round(np.asarray(arm["k_n_N_m"]) / 1e6, 4).tolist())
    if arm["lock_records"]:
        record = arm["lock_records"][0]
        print("  k_lock", np.round(np.asarray(record["k_lock_N_m"]) / 1e6, 4).tolist(),
              "k_rs", np.round(np.asarray(record["k_rs_N_m"]) / 1e6, 4).tolist())
    print("  state", arm["state"]["pad_force_kN"], "spheres", arm["state"]["crawler_spheres_active"],
          "modes", arm["lock_modes"])
    for window in ("S_hold2s_kN_per_mm", "S_late_kN_per_mm"):
        print(f"  {window} RMS {arm['rms_vs_chrono_' + window]:.4f}")
    print("  S hold2s:")
    for row in arm["measured"]["S_hold2s_kN_per_mm"]:
        print("   ", " ".join(f"{v:8.3f}" for v in row))
    print("  diag run", arm["diag_pair_run"])
judgement = {"window": "S_hold2s_kN_per_mm (E1/E2 specification); late window reported",
             "criteria": "rel err <= 0.10 (S_RR_RL, diag pair on RR, loss per kN), abs err <= 0.03 "
                         "(alpha_adj); discrimination err_on <= 0.5 err_off per item",
             "chrono": {name: chrono[name] for name in items}, "items": {}}
for name in items:
    e_on = error(name, on["m2_S_hold2s_kN_per_mm"][name])
    e_off = error(name, off["m2_S_hold2s_kN_per_mm"][name])
    tol = 0.03 if name.startswith("alpha") else 0.10
    judgement["items"][name] = {"on": on["m2_S_hold2s_kN_per_mm"][name],
                                "off": off["m2_S_hold2s_kN_per_mm"][name], "err_on": e_on,
                                "err_off": e_off, "tolerance": tol, "on_pass": e_on <= tol,
                                "off_pass": e_off <= tol, "discrimination_pass": e_on <= 0.5 * e_off}
judgement["rms_hold2s"] = {"on": on["rms_vs_chrono_S_hold2s_kN_per_mm"],
                           "off": off["rms_vs_chrono_S_hold2s_kN_per_mm"]}
judgement["state"] = {"on": [on["state"], on["lock_modes"]], "off": [off["state"], None]}
if len(sys.argv) > 3:
    Path(sys.argv[3]).write_text(json.dumps(judgement, indent=1, default=float), encoding="utf-8")
for name in items:
    e_on = error(name, on["m2_S_hold2s_kN_per_mm"][name])
    e_off = error(name, off["m2_S_hold2s_kN_per_mm"][name])
    tol = 0.03 if name.startswith("alpha") else 0.10
    print(f"{name}: chrono {chrono[name]:.4f} on {on['m2_S_hold2s_kN_per_mm'][name]:.4f} "
          f"off {off['m2_S_hold2s_kN_per_mm'][name]:.4f} err_on {e_on:.4f} err_off {e_off:.4f} "
          f"on_pass {e_on <= tol} off_pass {e_off <= tol} discrim {e_on <= 0.5 * e_off} "
          f"ratio {e_on / e_off:.3f}")
print("late window m2 on", on["m2_S_late_kN_per_mm"], "off", off["m2_S_late_kN_per_mm"])
