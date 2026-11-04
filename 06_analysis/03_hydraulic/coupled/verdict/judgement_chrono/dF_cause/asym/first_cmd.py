"""Re-approach component at the first command sample, all legs, new off run and stored off run."""
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
runs = {"off_ph0": Path(r"C:\workspace\outrigger_control\07_results\S8\final_E_G4_Fs4_20261030_233941\E_G4_Fs4"),
        "off_ph005": sorted(HERE.glob("final_E_G4_Fs4_ph0.05_off_*"))[-1] / "E_G4_Fs4_ph0.05"}
for n, d in runs.items():
    z = np.load(d / "r8_series.npz", allow_pickle=False)
    u, t = z["cmp_reapproach_u"], z["t"]
    k = int(np.flatnonzero((t > 50.0) & (np.abs(u).max(axis=1) > 0.0))[0])
    print(n, "t_abs", round(float(t[k]), 2), "reapproach u mm/s", np.round(u[k] * 1e3, 3), "issued mm/s", np.round(z["issued_u"][k] * 1e3, 3),
          "F_lower prev kN", np.round(z["F_lower_N"][k - 1] / 1e3, 2), "F_lower at kN", np.round(z["F_lower_N"][k] / 1e3, 2))
