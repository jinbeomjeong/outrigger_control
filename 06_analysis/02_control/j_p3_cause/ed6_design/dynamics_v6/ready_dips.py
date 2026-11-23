"""Where do the READY intra-period dips (F(t_k) - min over (t_k-1, t_k]) occur? j9_main VBJ rows.
Reports per row: dip, time, leg, reads since READY start, leg load, lock event within 0.2 s,
and the 10 Hz instantaneous swing (max - min of F over the next 6 reads) at that leg."""
import json
import sys
from pathlib import Path

import numpy as np

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\606f8713\j9main_a1")
LEGS = ("FL", "FR", "RL", "RR")
rec = []
for line in open(RUN / "j9_main.jsonl", encoding="utf-8"):
    d = json.loads(line)
    if d["job"]["setting"] != "VBJ":
        continue
    z = np.load(RUN / "j9_main_t4h" / d["t4h_file"], allow_pickle=False)
    t, F, Fm, ph, L = z["t_s"], z["true_force_N"], z["true_force_min_N"], z["phase"], z["locked"]
    rd = ph == "ready"
    if not rd.any():
        continue
    ok = np.isfinite(F) & np.isfinite(Fm)
    dip = np.where(rd[:, None] & ok, F - Fm, -np.inf)
    i, leg = np.unravel_index(int(np.argmax(dip)), dip.shape)
    # reads since this READY stretch began
    k = i
    while k > 0 and rd[k - 1]:
        k -= 1
    # dips excluding the first 5 reads of each READY stretch
    late = rd.copy()
    starts = np.flatnonzero(rd & ~np.r_[False, rd[:-1]])
    for s in starts:
        late[s:s + 5] = False
    dl = np.where(late[:, None] & ok, F - Fm, -np.inf)
    il, ll = np.unravel_index(int(np.argmax(dl)), dl.shape)
    swing = float(np.nanmax(F[i:i + 6, leg]) - np.nanmin(F[i:i + 6, leg]))
    rec.append((d["t4h_file"], dip[i, leg] / 1e3, float(t[i]), LEGS[leg], i - k, F[i, leg] / 1e3, swing / 1e3,
                (dl[il, ll] / 1e3) if np.isfinite(dl[il, ll]) else None, float(t[il]), LEGS[ll], F[il, ll] / 1e3))
rec.sort(key=lambda r: -r[1])
lines = ["file dip_kN t leg reads_into_ready F_kN swing6_kN | late_dip_kN t leg F_kN"]
for r in rec[:12]:
    lines.append(f"{r[0]} {r[1]:.2f} {r[2]:.2f} {r[3]} {r[4]} {r[5]:.1f} {r[6]:.2f} | "
                 + ("None" if r[7] is None else f"{r[7]:.2f} {r[8]:.2f} {r[9]} {r[10]:.1f}"))
late = np.array([r[7] for r in rec if r[7] is not None])
first = np.array([r[4] for r in rec])
lines.append(f"rows {len(rec)} max-dip read index into READY: median {np.median(first)} max {first.max()}")
lines.append(f"late (>= 5 reads into READY) dip kN: median {float(np.median(late)):.3f} max {float(late.max()):.3f}")
out = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if out is not None:
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
