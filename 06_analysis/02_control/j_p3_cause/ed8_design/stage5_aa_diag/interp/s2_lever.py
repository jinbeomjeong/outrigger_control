"""Interp step 2: rigid-body split of the D1'' residual r = sum F - M_eff f_z at each traced
period of window_rows.csv (estimate, record only).

Model (ASSUMPTIONS): the four cylinder net forces F_i = p_h A_p - p_r A_ann act vertically at
the pad xy (pad_bottom_center_retracted_m), the body is rigid with the bottom-auger CoM and
inertia (rexome33.yaml superstructure.auger_levels.bottom), angular rates small (omega^2 r
dropped), body axes = world axes (tilt < 1 deg). Then
    alpha = I^-1 sum (p_i - c) x (0, 0, F_i),   lever_z = (alpha x r_imu)_z,
    r_imu = IMU - CoM, IMU at (0.31, 0.88, 0.040) m (CLAUDE.md, cad_origin_mass_imu.md 4),
and an ideal instantaneous IMU would read f_z,inst = sum F / M + lever_z. So
    r = -M lever_z  (lever share, what the lever correction would remove)
      + M (f_z,inst - f_z,mean)  (partial-mean share, the 10 ms window lag; also takes any
        pressure-vs-contact difference).
Writes interp/residual_split.csv."""
import csv
import sys
from pathlib import Path

import numpy as np

D = Path(sys.argv[1])
M = 38400.8366
COM = np.array([0.460190503, -0.00136232581, 0.782572771])
INERTIA = np.array([[176282.442, -941.461576, -46346.9348],
                    [-941.461576, 331469.51, 22.5263014],
                    [-46346.9348, 22.5263014, 192270.902]])
IMU = np.array([0.31, 0.88, 0.040])
PAD = {"FL": (2.2938, 1.3238), "FR": (2.2938, -1.3238), "RL": (-2.556, 1.1679), "RR": (-2.556, -1.2429)}
AP = {"FL": 0.013273229, "FR": 0.013273229, "RL": 0.00950331778, "RR": 0.00950331778}
AA = {"FL": 0.00376991118, "FR": 0.00376991118, "RL": 0.00314159265, "RR": 0.00314159265}
ROD_BAR = 2.0
r_imu = IMU - COM
I_inv = np.linalg.inv(INERTIA)
rows = list(csv.DictReader(open(D / "interp" / "window_rows.csv", encoding="utf-8")))
out = []
for r in rows:
    F = {leg: float(r[f"head_bar_{leg}"]) * 1e5 * AP[leg] - float(r[f"rod_bar_{leg}"] or ROD_BAR) * 1e5 * AA[leg]
         for leg in PAD}
    moment = np.zeros(3)
    for leg, (x, y) in PAD.items():
        arm = np.array([x, y, 0.0]) - np.array([COM[0], COM[1], 0.0])
        moment += np.cross(arm, [0.0, 0.0, F[leg]])
    alpha = I_inv @ moment
    lever_z = float(np.cross(alpha, r_imu)[2])
    sum_f = sum(F.values())
    resid = float(r["residual_kN"]) * 1e3 if r["residual_kN"] else float("nan")
    mass_used = float(r["M_f_z_kN"]) * 1e3 / float(r["f_z_used_m_s2"])
    lever_share = -mass_used * lever_z
    out.append({"label": r["label"][:2], "t_s": round(float(r["t_s"]), 3), "t_rel_lift_s": r["t_rel_lift_s"],
                "sum_F_kN_recomputed": round(sum_f / 1e3, 1), "net_sum_kN_trace": round(float(r["net_sum_kN"]), 1),
                "alpha_x_rad_s2": round(alpha[0], 3), "alpha_y_rad_s2": round(alpha[1], 3),
                "lever_z_m_s2": round(lever_z, 3), "residual_kN": round(resid / 1e3, 1),
                "lever_share_kN": round(lever_share / 1e3, 1),
                "window_share_kN": round((resid - lever_share) / 1e3, 1),
                "residual_change_kN": r["residual_change_kN"] and round(float(r["residual_change_kN"]), 1),
                "fault": r["head_fault_reasons"]})
with open(D / "interp" / "residual_split.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0]))
    w.writeheader()
    w.writerows(out)
print("r_imu - com", r_imu)
for o in out:
    print(o["label"], o["t_s"], o["t_rel_lift_s"], "S", o["sum_F_kN_recomputed"], o["net_sum_kN_trace"],
          "a", o["alpha_x_rad_s2"], o["alpha_y_rad_s2"], "lev", o["lever_z_m_s2"], "r", o["residual_kN"],
          "= lev", o["lever_share_kN"], "+ win", o["window_share_kN"], "dr", o["residual_change_kN"], o["fault"])
