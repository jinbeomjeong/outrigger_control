"""h06: per-read series of the probe first move (extend) of chosen keys, settings h05 / VBM-like
/ h15, to see where the seal stick ends against the K1 mid read (read only).

Per read k in [i0 - 1, iext]: command [mm/s], oil stroke s - s_start [mm], read force F - F_start
[kN] (p_h A_h - p_r A_ann), incremental slope dF/ds [MN/m], locked, gate open.
A stuck seal (harness: massless rod, rigid stick, ``run_control_comparison.physics`` form)
gives dF/ds = k_oil (oil column alone); a sliding seal gives series(k_oil, k_ground).

Usage: python -I -B h06_window_series.py  -> h06_series.csv, h06_out.txt
"""
import csv
import math
import os

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
J9 = r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\8a2a52ce"
SENS = os.path.join(J9, r"sens_a1\sens_t4h")
MAIN = os.path.join(J9, r"j9main_a1\j9_main_t4h")
A_H = np.array([math.pi / 4 * 0.13 ** 2] * 2 + [math.pi / 4 * 0.11 ** 2] * 2)
A_ROD = np.array([math.pi / 4 * 0.11 ** 2] * 2 + [math.pi / 4 * 0.09 ** 2] * 2)
A_ANN = A_H - A_ROD
LEGS = ("FL", "FR", "RL", "RR")
CASES = [
    (SENS, "R12_o0.0", ("VBMh05", "VBMh15", "VBMfast", "VBMslow", "VBMd15")),
    (SENS, "R12_top-FL-Fs8-o0.0", ("VBMh05", "VBMh15", "VBMd15")),
    (MAIN, "R12_top-FL-Fs8-o0.0", ("VBM",)),
    (MAIN, "R12_o0.0", ("VBM",)),
]


def first_moves(z):
    t = z["t_s"]
    ph = np.char.lower(z["phase"].astype(str))
    cmd = z["command_m_s"]
    n = len(t)
    i, rnd = 0, 0
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
            blocks = []
            for k in pos:
                if blocks and k == blocks[-1][-1] + 1:
                    blocks[-1].append(k)
                else:
                    blocks.append([k])
            blocks = [b for b in blocks if len(b) >= 5]
            if not blocks:
                continue
            blk = blocks[0]
            neg = [k for k in range(blk[-1], j) if cmd[k, leg] < -1e-9]
            if neg and neg[0] < blk[0]:
                continue
            iext = (neg[0] - 1) if neg else blk[-1] + 1
            yield rnd, leg, blk[0], blk[0] + len(blk) // 2, iext
        i = j


rows, lines = [], []
for folder, key, settings in CASES:
    for s in settings:
        path = os.path.join(folder, f"{key}_{s}.npz")
        if not os.path.exists(path):
            continue
        z = np.load(path, allow_pickle=False)
        cmd, st = z["command_m_s"], z["motor_stroke_m"]
        F = z["head_pressure_Pa"] * A_H - z["rod_pressure_Pa"] * A_ANN
        lk, gt = z["locked"], z["jp3_gate_open"]
        t = z["t_s"]
        for rnd, leg, i0, imid, iext in first_moves(z):
            if rnd > 2:
                continue
            seq = []
            for k in range(i0 - 1, iext + 1):
                ds = (st[k, leg] - st[k - 1, leg]) * 1e3
                dF = (F[k, leg] - F[k - 1, leg]) / 1e3
                slope = dF / ds if abs(ds) > 1e-3 else float("nan")
                tag = "M" if k == imid else ("E" if k == iext else "")
                rows.append({"key": key, "setting": s, "round": rnd, "leg": LEGS[leg],
                             "k": k - i0, "tag": tag, "t_s": round(float(t[k]), 2),
                             "cmd_mm_s": round(float(cmd[k, leg]) * 1e3, 3),
                             "ds_mm": round(float(st[k, leg] - st[i0 - 1, leg]) * 1e3, 3),
                             "dF_kN": round(float(F[k, leg] - F[i0 - 1, leg]) / 1e3, 3),
                             "slope_MN_m": None if math.isnan(slope) else round(slope, 2),
                             "locked": bool(lk[k, leg]), "gate": bool(gt[k, leg])})
                seq.append(f"{tag}{'' if math.isnan(slope) else round(slope, 1)}")
            lines.append(f"{key} {s} r{rnd} {LEGS[leg]} ds_mid "
                         f"{(st[imid, leg] - st[i0 - 1, leg]) * 1e3:.3f} slopes: " + " ".join(seq))
with open(os.path.join(OUT, "h06_series.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
with open(os.path.join(OUT, "h06_out.txt"), "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lines) + "\n")
print(len(lines))
