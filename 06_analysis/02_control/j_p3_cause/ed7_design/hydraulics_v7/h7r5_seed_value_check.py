"""Q7-H1: does the stale retract seed explain the size of each Part D breach?

For each breach leg (Part D T4h with the P1 read arrays) the moving retract opening before the
breach release (first read with p1 line_dir -1, is_open and the leg unlocked) is located. The
seed the plant stored there is ``retract_dead(...)["p_rod"]`` (``check_open_delay``, VN, nominal
P1 values) at that step's ``(p_h, p_r)``; the read gives the net force ``F`` of the read before
and at the opening, so the seed is bracketed with ``p_r`` in [floor, 5 bar]
(``p_r0 - G_r / A_ann`` of a moving leg decays to the last lock anchor; P2 anchors at the lag,
about 5 bar after an extension) and ``F`` of the two reads.

The release lag can only fall for a compressive force, so the first read after the release
brackets the start: ``p_after <= S <= p_bB + (p_after - p_bB) exp(dt / tau)`` (``dt`` = read
time - release time, ``tau`` 0.05 s; the right end ignores the flow cap that slows the fall).

Read only; imports ``retract_dead`` from the run commit worktree (pure function).
Run: hydraulics-dev python.exe -I -B h7r5_seed_value_check.py <D t4h dir> <worktree> <out.txt>
"""
import math
import sys
from pathlib import Path

import numpy as np

BAR = 1.0e5
LEGS = ["FL", "FR", "RL", "RR"]
A_H = [132.73e-4, 132.73e-4, 95.03e-4, 95.03e-4]
A_ANN = [37.70e-4, 37.70e-4, 31.42e-4, 31.42e-4]
TAU_S = 0.05
P_BB = 5.0e5
FLOOR = 0.1e5 - 1.01325e5


def main() -> None:
    folder, worktree, out_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    sys.path.insert(0, str(worktree / "03_src"))
    from outrigger_sim.hydraulics.check_open_delay import RetractConfig, retract_dead

    cfg = RetractConfig(rod_forward=True, volume_scale=1.0, v_line_m3=285e-6,
                        beta_hose_Pa=0.5e9, psi=3.5, p_crack_Pa=3e5)
    lines = []
    inside = 0
    total = 0
    for path in sorted(folder.glob("*.npz")):
        d = np.load(path, allow_pickle=False)
        t = d["t_s"]
        cls = d["jp3_class"]
        ptr = d["jp3_p_tr_Pa"]
        used = d["jp3_used_bound_Pa"]
        jt = d["jp3_t_s"]
        tidx = {round(v, 4): i for i, v in enumerate(t)}
        ev = d["lock_events"]
        for leg in range(4):
            with np.errstate(invalid="ignore"):
                hit = np.flatnonzero(((cls[:, leg] == 2) | (cls[:, leg] == 4))
                                     & (ptr[:, leg] > used[:, leg] + 1.0))
            if hit.size == 0:
                continue
            jr = int(hit[0])
            t_read = float(jt[jr])
            rel = [float(e[0]) for e in ev if int(e[1]) == leg and int(e[2]) == 0
                   and float(e[0]) <= t_read + 1e-9]
            t_rel = rel[-1]
            prev_rel = rel[-2] if len(rel) > 1 else -1e9
            win = np.flatnonzero((t > prev_rel) & (t < t_rel))
            opening = win[(d["p1_line_dir"][win, leg] == -1) & d["p1_is_open"][win, leg]
                          & ~d["locked"][win, leg]]
            if opening.size == 0:
                lines.append(f"{path.stem} {LEGS[leg]}: no moving retract opening found")
                continue
            k = int(opening[0])
            forces = [float(d["true_force_N"][max(k - 1, 0), leg]), float(d["true_force_N"][k, leg])]
            seeds = []
            for force in forces:
                for p_r in (FLOOR, P_BB):
                    p_h = (force + p_r * A_ANN[leg]) / A_H[leg]
                    s = float(d["motor_stroke_m"][k, leg])
                    res = retract_dead(cfg, p_h, p_r, 0.0, s, 0.0, A_H[leg], A_ANN[leg], 0.70,
                                       0.05, 0.05, 1.0e9, 2.0e5)
                    seeds.append(res["p_rod"])
            p_after = float(ptr[jr, leg])
            i_read = tidx[round(t_read, 4)]
            dt = t_read - t_rel
            s_hi = P_BB + (p_after - P_BB) * math.exp(dt / TAU_S)
            s_lo = p_after
            seed_lo, seed_hi = min(seeds), max(seeds)
            overlap = seed_hi >= s_lo and seed_lo <= s_hi
            total += 1
            inside += int(overlap)
            lines.append(
                f"{path.stem:50s} {LEGS[leg]} opening read {t[k]:6.1f} s (F {forces[0] / 1e3:6.1f}"
                f"/{forces[1] / 1e3:6.1f} kN) seed {seed_lo / BAR:5.1f}-{seed_hi / BAR:5.1f} bar | "
                f"release {t_rel:7.3f} read {t_read:5.1f} p_after {p_after / BAR:5.2f} -> start "
                f"{s_lo / BAR:5.1f}-{s_hi / BAR:5.1f} bar | overlap {'Y' if overlap else 'n'} | "
                f"locked truth before release {d['rod_pressure_Pa'][i_read - 1, leg] / BAR:5.2f}")
    lines.append(f"breach legs {total}, seed bracket overlaps the start bracket in {inside}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(lines[-1])


if __name__ == "__main__":
    main()
