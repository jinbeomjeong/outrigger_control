"""S matrix of the harness (E1 procedure, beta 1.0, kn x1) with lock_stiffness, RMS against the E2 Chrono S."""
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

probe_path, e2_path, out_path = (Path(a) for a in sys.argv[1:4])
spec = importlib.util.spec_from_file_location("e1probe", probe_path)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

e2 = json.loads(e2_path.read_text(encoding="utf-8"))
s_chrono = np.asarray(e2["S_chrono_kN_per_mm"], float)
if os.environ.get("LK_MATCH"):  # preload to the E2 Chrono TOUCH-end pad loads (per leg)
    base_N = np.asarray(e2["base_N_kN"]["FL"], float) * 1e3
    probe.PRELOAD_TARGET_N = base_N
    probe.PRELOAD_BAND_N = (base_N - 500.0, base_N + 500.0)
    probe.TRIM_SPEED_M_S = 1.0e-4
    probe.PRELOAD_TIMEOUT_S = 400.0
combo = probe.run_combination(1.0e9, 1.0)
result = {"lk_mode": os.environ.get("LK_MODE"), "lk_l0r": os.environ.get("LK_L0R"),
          "lk_match": os.environ.get("LK_MATCH"),
          "lock_records": probe.LOCK_RECORDS, "rmf_file": probe.rmf.__file__, "combo": combo}
for window in ("S_hold2s_kN_per_mm", "S_late_kN_per_mm"):
    s = np.asarray(combo["states"]["on_crawler"]["measured"][window], float)
    diff = s - s_chrono
    result[f"rms_vs_E2_{window}"] = float(np.sqrt(np.mean(diff ** 2)))
    result[f"maxabs_vs_E2_{window}"] = float(np.abs(diff).max())
    print(window, "RMS", round(result[f"rms_vs_E2_{window}"], 4), "max", round(result[f"maxabs_vs_E2_{window}"], 4))
    print(np.round(s, 3))
print("state", combo["states"]["on_crawler"]["state"]["pad_force_kN"], "rmf", probe.rmf.__file__)
out_path.write_text(json.dumps(result, indent=1, default=float), encoding="utf-8")
