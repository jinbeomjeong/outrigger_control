"""Harness 1 mm step S at beta 1.6 (lock_stiffness on / off) against the E2_b16 Chrono L1-R summary.

Args: <patched E1 probe> <E2_b16 e2_summary.json> <out json>; env LK_MODE=l1r for the on arm.
Preload matched per leg to the Chrono base pad loads (as LK_MATCH=1 of run_s.py).
"""
import copy
import ctypes
import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np

kernel32 = ctypes.WinDLL("kernel32")
kernel32.GetCurrentProcess.restype = ctypes.c_void_p
kernel32.SetProcessAffinityMask.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
kernel32.SetProcessAffinityMask(kernel32.GetCurrentProcess(), 0x0FFF0000)

BETA_PA = 1.6e9
FR, RL, RR = 1, 2, 3
REL_TOL = 0.10
ALPHA_ABS_TOL = 0.03

probe_path, e2_path, out_path = (Path(a) for a in sys.argv[1:4])
spec = importlib.util.spec_from_file_location("e1probe", probe_path)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
e2 = json.loads(e2_path.read_text(encoding="utf-8"))
base_N = np.asarray(e2["base_N_kN"]["FL"], float) * 1e3
probe.PRELOAD_TARGET_N = base_N
probe.PRELOAD_BAND_N = (base_N - 500.0, base_N + 500.0)
probe.TRIM_SPEED_M_S = 1.0e-4
probe.PRELOAD_TIMEOUT_S = 400.0


def m2_items(s_kn_mm: np.ndarray) -> dict:
    diag_on_rr = s_kn_mm[RR, FR] + s_kn_mm[RR, RL]
    received = s_kn_mm[FR, FR] + s_kn_mm[FR, RL] + s_kn_mm[RL, FR] + s_kn_mm[RL, RL]
    return {"S_RR_RL": float(s_kn_mm[RR, RL]), "diag_pair_FRRL_on_RR": float(diag_on_rr),
            "loss_per_received_kN": float(-diag_on_rr / received),
            "alpha_adj_rear_RR_from_RL": float(-s_kn_mm[RR, RL] / s_kn_mm[RL, RL])}


def diag_pair_run(snapshot) -> dict:
    """FR and RL extended together by 1 mm (same ramp / window as the single-leg columns)."""
    base = probe.run_from_snapshot(snapshot, None)
    plant = copy.deepcopy(snapshot)
    ramp_chunks = int(round(probe.STEP_RAMP_S / 1e-3))
    hold_chunks = int(round(probe.HOLD_S / 1e-3))
    speed = np.zeros(4)
    speed[[FR, RL]] = probe.STEP_M / probe.STEP_RAMP_S
    pads = np.empty((ramp_chunks + hold_chunks, 4))
    for k in range(ramp_chunks + hold_chunks):
        pads[k] = probe.advance(plant, speed if k < ramp_chunks else np.zeros(4))[11:15]
    start = probe.STEP_RAMP_S + probe.HOLD2S_WINDOW_S[0]
    end = probe.STEP_RAMP_S + probe.HOLD2S_WINDOW_S[1]
    delta_kN = probe.window_mean(pads - base.pad_N, base.t_s, start, end) / 1e3
    received = delta_kN[FR] + delta_kN[RL]
    return {"dF_kN": delta_kN.round(4).tolist(), "diag_pair_FRRL_on_RR": float(delta_kN[RR]),
            "loss_per_received_kN": float(-delta_kN[RR] / received)}


def lock_modes(plant) -> list:
    if plant.lockm == 0:
        return None
    modes = []
    for i in range(4):
        spring = plant.krs[i] * (plant.xlk[i] - plant.x[i])
        if plant.rlock[i] != 1:
            modes.append("MOVING")
        elif plant.acc[11 + i] <= 0.0:
            modes.append("LIFT")
        else:
            modes.append("FLOOR" if spring >= plant.fcap[i] else "LOCK")
    return modes


plant = probe.build_plant(BETA_PA, 1.0)
preparation = probe.preload_on_crawler(plant)
snapshot = copy.deepcopy(plant)
measured = probe.measure_matrix(snapshot)
s_chrono = np.asarray(e2["S_chrono_kN_per_mm"], float)
chrono_m2 = e2["m2"]["chrono_superposition"]
result = {"lk_mode": os.environ.get("LK_MODE"), "beta_Pa": BETA_PA,
          "lock_records": probe.LOCK_RECORDS, "rmf_file": probe.rmf.__file__,
          "k_n_N_m": (1.0 / (1.0 / np.asarray(plant.ko) + 1.0 / plant.ks)).tolist(),
          "preparation": preparation, "state": probe.state_record(snapshot),
          "lock_modes": lock_modes(snapshot), "measured": measured,
          "diag_pair_run": diag_pair_run(snapshot)}
for window in ("S_hold2s_kN_per_mm", "S_late_kN_per_mm"):
    s = np.asarray(measured[window], float)
    result[f"rms_vs_chrono_{window}"] = float(np.sqrt(np.mean((s - s_chrono) ** 2)))
    result[f"m2_{window}"] = m2_items(s)
result["chrono_m2"] = chrono_m2
out_path.write_text(json.dumps(result, indent=1, default=float), encoding="utf-8")
print(json.dumps({"mode": result["lk_mode"], "rms_hold2s": result["rms_vs_chrono_S_hold2s_kN_per_mm"],
                  "m2": result["m2_S_hold2s_kN_per_mm"], "state": result["state"]["pad_force_kN"],
                  "spheres": result["state"]["crawler_spheres_active"], "modes": result["lock_modes"]}))
