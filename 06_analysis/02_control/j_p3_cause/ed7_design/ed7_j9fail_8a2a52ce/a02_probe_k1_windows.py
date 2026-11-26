"""a02: per-leg probe first-move (extension) windows from T4h, edition 7 vs edition 6 / 5.

For every PROBE phase and leg: the first block of positive commands (the trapezoid first
move), the K1 mid index (i0 + n_pos // 2, ``ground_contact._step_trapezoid`` records the mid
reading when ``len(sent_speeds) == half``), the extended index (last read before the first
negative command, ``_end_stage`` FIRST_MOVE), the P1 gate-open index, force reads
``p_h A_h - p_r A_ann`` (T4h logged controller inputs) and motor (oil) strokes. The
"motor K" is dF_read / ds_motor over [mid, ext]; the controller K1 uses the piston stroke
reading, which is not in T4h, so motor K is a proxy (same in every plant).

Usage: a02_probe_k1_windows.py  (fixed key list below). Output: a02_probe_k1.csv/json.
"""
import csv
import json
import math
import os

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
J9 = r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
DIRS = {
    "VBM": J9 + r"\8a2a52ce\j9main_a1\j9_main_t4h",
    "VBL": J9 + r"\79495405\records_after_stop\B_a1\j9_main_t4h",
    "VBJ": J9 + r"\606f8713\j9main_a1\j9_main_t4h",
    "VBMslow": J9 + r"\8a2a52ce\sens_a1\sens_t4h",
    "VBMfast": J9 + r"\8a2a52ce\sens_a1\sens_t4h",
    "VBMh15": J9 + r"\8a2a52ce\sens_a1\sens_t4h",
    "VBMh05": J9 + r"\8a2a52ce\sens_a1\sens_t4h",
}
A_H = np.array([math.pi / 4 * 0.13 ** 2] * 2 + [math.pi / 4 * 0.11 ** 2] * 2)
A_ROD = np.array([math.pi / 4 * 0.11 ** 2] * 2 + [math.pi / 4 * 0.09 ** 2] * 2)
A_ANN = A_H - A_ROD
LEGS = ("FL", "FR", "RL", "RR")
MIN_BLOCK = 5
KEYS = [
    "R12_top-FR-Fs8-o0.0", "R12_top-FL-Fs8-o0.0", "R12_top-RL-Fs8-o0.05",
    "R14_o0.0", "R7_e0.0", "R12_top-FR-Fs0-o0.0", "R12_top-FL-Fs4-o0.0", "R12_o0.0",
]


def windows(z):
    t = z["t_s"]
    ph = np.char.lower(z["phase"].astype(str))
    cmd = z["command_m_s"]
    head, rod = z["head_pressure_Pa"], z["rod_pressure_Pa"]
    force = head * A_H - rod * A_ANN
    stroke = z["motor_stroke_m"]
    gate = z["jp3_gate_open"] if "jp3_gate_open" in z.files else None
    fill = z["jp3_gate_fill_m"] if "jp3_gate_fill_m" in z.files else None
    locked = z["locked"]
    out = []
    n = len(t)
    i = 0
    rnd = 0
    while i < n:
        if ph[i] != "probe":
            i += 1
            continue
        j = i
        while j < n and ph[j] == "probe":
            j += 1
        rnd += 1
        for leg in range(4):
            pos = [k for k in range(i, j) if cmd[k, leg] > 1e-9]
            if not pos:
                continue
            # contiguous positive blocks; the trapezoid first move is the first block of
            # >= MIN_BLOCK periods (single stray positive periods at the phase start are not
            # the probe of this leg)
            blocks = []
            for k in pos:
                if blocks and k == blocks[-1][-1] + 1:
                    blocks[-1].append(k)
                else:
                    blocks.append([k])
            long_blocks = [b for b in blocks if len(b) >= MIN_BLOCK]
            if not long_blocks:
                continue
            blk = long_blocks[0]
            i0 = blk[0]
            npos = len(blk)
            neg = [k for k in range(blk[-1], j) if cmd[k, leg] < -1e-9]
            iext = (neg[0] - 1) if neg else blk[-1] + 1
            imid = i0 + npos // 2
            # gate open index after first command (+1 = acting)
            iopen = None
            if gate is not None:
                for k in range(i0, iext + 1):
                    if gate[k, leg] and not locked[k, leg]:
                        iopen = k
                        break
            iunlock = None
            for k in range(i0, iext + 1):
                if not locked[k, leg]:
                    iunlock = k
                    break
            cum = np.cumsum(cmd[i0:iext + 1, leg]) * 0.1
            dF = force[iext, leg] - force[imid, leg]
            ds = stroke[iext, leg] - stroke[imid, leg]
            dF_all = force[iext, leg] - force[i0 - 1, leg]
            ds_all = stroke[iext, leg] - stroke[i0 - 1, leg]
            out.append({
                "round": rnd, "leg": LEGS[leg], "t_start_s": round(float(t[i0]), 2),
                "n_pos": npos, "t_mid_s": round(float(t[imid]), 2),
                "t_ext_s": round(float(t[iext]), 2),
                "t_unlock_s": None if iunlock is None else round(float(t[iunlock]), 2),
                "t_gate_open_s": None if iopen is None else round(float(t[iopen]), 2),
                "cmd_to_mid_mm": round(float(np.sum(cmd[i0:imid, leg]) * 0.1e3), 3),
                "cmd_total_mm": round(float(np.sum(cmd[i0:iext + 1, leg]) * 0.1e3), 3),
                "cmd_to_unlock_mm": None if iunlock is None else round(
                    float(np.sum(cmd[i0:iunlock, leg]) * 0.1e3), 3),
                "fill_at_mid_mm": None if fill is None else round(float(fill[imid, leg]) * 1e3, 3),
                "F_start_kN": round(float(force[i0 - 1, leg]) / 1e3, 3),
                "F_mid_kN": round(float(force[imid, leg]) / 1e3, 3),
                "F_ext_kN": round(float(force[iext, leg]) / 1e3, 3),
                "s_mid_minus_start_mm": round(float(stroke[imid, leg] - stroke[i0 - 1, leg]) * 1e3, 3),
                "s_ext_minus_start_mm": round(float(ds_all) * 1e3, 3),
                "Kmotor_half_MN_m": round(dF / ds / 1e6, 3) if abs(ds) > 1e-6 else None,
                "Kmotor_all_MN_m": round(dF_all / ds_all / 1e6, 3) if abs(ds_all) > 1e-6 else None,
                "Ftrue_mid_kN": round(float(z["true_force_N"][imid, leg]) / 1e3, 3),
                "Ftrue_ext_kN": round(float(z["true_force_N"][iext, leg]) / 1e3, 3),
                "rod_start_bar": round(float(rod[i0 - 1, leg]) / 1e5, 2),
                "rod_mid_bar": round(float(rod[imid, leg]) / 1e5, 2),
                "rod_ext_bar": round(float(rod[iext, leg]) / 1e5, 2),
            })
        i = j
    return out


rows = []
for setting, d in DIRS.items():
    for key in KEYS:
        path = os.path.join(d, f"{key}_{setting}.npz")
        if not os.path.exists(path):
            continue
        z = np.load(path, allow_pickle=False)
        for w in windows(z):
            w = {"setting": setting, "key": key, **w}
            rows.append(w)
fields = list(rows[0].keys())
with open(os.path.join(OUT, "a02_probe_k1.csv"), "w", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, fieldnames=fields)
    wr.writeheader()
    wr.writerows(rows)
for r in rows:
    print(",".join(str(r[k]) for k in fields))
