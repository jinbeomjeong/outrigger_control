"""h09: S7 (soil row) probe first-move series, head-only force p_h A_h (the rod reading is NaN in
these T4h files), settings h05 / h15 / slow / VBM; round 2 is where the low ratios 0.59-0.70 were
recorded (read only).

Output: h09_out.txt
"""
import math
import os

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
J9 = r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\8a2a52ce"
SENS = os.path.join(J9, r"sens_a1\sens_t4h")
A_H = np.array([math.pi / 4 * 0.13 ** 2] * 2 + [math.pi / 4 * 0.11 ** 2] * 2)
LEGS = ("FL", "FR", "RL", "RR")
lines = []
for key in ("S7_e0.001", "S7_e0.002", "S7_e0.0"):
    for s in ("VBMh05", "VBMfast", "VBMd15", "VBMh15", "VBMslow"):
        path = os.path.join(SENS, f"{key}_{s}.npz")
        if not os.path.exists(path):
            continue
        z = np.load(path, allow_pickle=False)
        t = z["t_s"]
        ph = np.char.lower(z["phase"].astype(str))
        cmd, st = z["command_m_s"], z["motor_stroke_m"]
        rodnan = int(np.isnan(z["rod_pressure_Pa"]).sum())
        F = z["head_pressure_Pa"] * A_H
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
                i0, imid = blk[0], blk[0] + len(blk) // 2
                neg = [k for k in range(blk[-1], j) if cmd[k, leg] < -1e-9]
                iext = (neg[0] - 1) if neg else blk[-1] + 1
                if iext >= n:
                    continue
                seq = []
                for k in range(i0, iext + 1):
                    ds = (st[k, leg] - st[k - 1, leg]) * 1e3
                    dF = (F[k, leg] - F[k - 1, leg]) / 1e3
                    tag = "M" if k == imid else ("E" if k == iext else "")
                    seq.append(f"{tag}{dF / ds:.1f}" if abs(ds) > 1e-3 else f"{tag}(dF{dF:.1f})")
                dFh = (F[iext, leg] - F[imid, leg]) / 1e3
                dsh = (st[iext, leg] - st[imid, leg]) * 1e3
                lines.append(f"{key} {s} r{rnd} {LEGS[leg]} rodNaN {rodnan} ds_mid "
                             f"{(st[imid, leg] - st[i0 - 1, leg]) * 1e3:.3f} half dF {dFh:.2f} kN"
                             f" ds {dsh:.3f} mm K_oil {dFh / dsh:.2f} | " + " ".join(seq))
            i = j
with open(os.path.join(OUT, "h09_out.txt"), "w", encoding="utf-8", newline="\n") as fo:
    fo.write("\n".join(lines) + "\n")
print(len(lines))
