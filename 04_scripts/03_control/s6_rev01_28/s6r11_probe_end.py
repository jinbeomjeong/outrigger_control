"""Probe end direction vs the L1 one-sided rod-chamber spring (user decision, hydraulics 13 (b)).

Rigid body (heave, roll, pitch) on four leg springs. Each locked leg has a bilinear axial
stiffness: k_par (head + rod chamber) while the load change since locking is below the
symmetric band (load increase side), k_head beyond it; unload side always k_par. The moving
leg has k_head (valve open, rod side is not a spring). Pads: YAML pad_bottom_center (x, y).
Outputs the probe load sensitivity S_ii (secant over +d / -d) for lock histories and the
midpoint / seal-friction estimate error when the controller uses the head-only nominal S.
"""

import json
import sys
from pathlib import Path

import numpy as np

# --- paths (migrated from the 2026-10-22 session scratchpad ctrl-run on 2026-10-25) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[3]  # 04_scripts/03_control/s6_rev01_28/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s6_rev01_28"  # results of these scripts
OUT_DIR.mkdir(parents=True, exist_ok=True)
_sys.path.append(str(REPO / "04_scripts" / "03_control"))  # siblings migrated earlier
# ---
XY = np.array([[2.2938, 1.3238], [2.2938, -1.3238], [-2.556, 1.1679], [-2.556, -1.2429]])
LEGS = ("FL", "FR", "RL", "RR")
K_HEAD = np.array([2.591e7, 2.591e7, 1.950e7, 1.950e7])  # dynamics 5.11.2 (head only)
K_PAR = np.array([3.393e7, 3.393e7, 2.640e7, 2.640e7])  # hydraulics 13.1 (+rod parallel)
BAND = {"extend_lock": np.array([4.08e3, 4.08e3, 3.16e3, 3.16e3]),  # hydraulics 12.2
        "retract_lock": np.array([50.2e3, 50.2e3, 35.2e3, 35.2e3])}  # hydraulics 13.1
B = np.column_stack([np.ones(4), XY[:, 1], -XY[:, 0]])
D = 2e-3
DELTA_TAIL = 0.3e-3


def tangent(dF, moving, states):
    k = np.empty(4)
    for j in range(4):
        if j == moving or states[j] == "head_only":
            k[j] = K_HEAD[j]
        elif dF[j] <= 0.0 or dF[j] < BAND[states[j]][j]:
            k[j] = K_PAR[j]
        else:
            k[j] = K_HEAD[j]
    return k


def path(leg, states, moves, n=400):
    """Integrate force changes over successive moves of one leg (list of displacements)."""
    dF = np.zeros(4)
    out = []
    for move in moves:
        for _ in range(n):
            ds = np.zeros(4)
            ds[leg] = move / n
            k = tangent(dF, leg, states)
            K = np.diag(k)
            # body displacement w = B q, equilibrium B^T K (ds - B q) = 0
            q = np.linalg.solve(B.T @ K @ B, B.T @ K @ ds)
            dF += K @ (ds - B @ q)
        out.append(dF.copy())
    return out


def s_nominal(leg):
    K = np.diag(K_HEAD)
    e = np.zeros(4)
    e[leg] = 1.0
    q = np.linalg.solve(B.T @ K @ B, B.T @ K @ e)
    return float((K @ (e - B @ q))[leg])


case = sys.argv[1] if len(sys.argv) > 1 else "all"
result = {}
for leg in range(4):
    s_nom = s_nominal(leg)
    row = {"S_nominal_head_only_N_m": s_nom}
    for label, st in (("C1_others_extend_locked", "extend_lock"),
                      ("C2_others_retract_locked", "retract_lock")):
        states = [st] * 4
        # current order: +d, -d (returns to start)
        f_ext, f_back = path(leg, states, [D, -D])
        s_ext = f_ext[leg] / D
        mid_err = 0.5 * (s_ext - s_nom) * D
        # R-H4 order: +d, -(d + delta), +delta; readings at +d and at -delta
        g_ext, g_ret, g_end = path(leg, states, [D, -(D + DELTA_TAIL), DELTA_TAIL])
        e_r = g_ext[leg]
        r_r = g_ret[leg]
        gap = D + DELTA_TAIL
        mid_err_tail = 0.5 * (e_r + r_r) - 0.5 * s_nom * (D - DELTA_TAIL) - 0.0
        # midpoint estimate: 0.5(E + R) - 0.5 S (x_E + x_R) referred to the start
        mid_err_tail = 0.5 * (e_r + r_r) - 0.5 * s_nom * (D + (-DELTA_TAIL))
        fs_err_tail = 0.5 * (e_r - r_r - s_nom * gap)
        row[label] = {
            "S_secant_extend_N_m": s_ext,
            "S_ratio": s_ext / s_nom,
            "midpoint_error_current_order_N": mid_err,
            "seal_friction_error_current_order_N": mid_err,
            "midpoint_error_tail_order_N": float(mid_err_tail),
            "seal_friction_error_tail_order_N": float(fs_err_tail),
            "other_leg_dF_at_plus_d_kN": [float(x) / 1e3 for x in f_ext],
            "tail_min_load_below_start_kN": float(r_r) / 1e3,
        }
    result[LEGS[leg]] = row
path_out = (OUT_DIR / _Path(__file__).name).with_suffix(".json")
path_out.write_text(json.dumps(result, indent=1))
print(json.dumps(result, indent=1))
