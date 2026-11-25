"""H-7 breach reads of the Part D T4h (record-only runs, judged edition 6): per breach leg the
read series around the carry_ext run that breached (Q7-H1 input).

Breach (as the ③ record, jp3a): class carry_ext or ext and rod reading > used bound + 1 Pa.
Rod reading here is the P4 truth (rod_reading_truth on). Pressures gauge, printed in bar.

Read only. Run: hydraulics-dev python.exe -I -B h7r1_breach_series.py <t4h dir> [out.txt]
"""
import sys
from pathlib import Path

import numpy as np

BAR = 1.0e5
CLASS = ["lock", "hold", "c_ext", "c_ret", "ext", "ret"]
STATE = ["mv_ext", "mv_ret", "lk_ext", "lk_ret"]
SRC = ["ext_bnd", "pilot", "prev_mv", "ret_hold", "ret_trk"]
LEGS = ["FL", "FR", "RL", "RR"]


def name_of(table, code):
    return "-" if code < 0 else table[code]


def series(path: Path, out) -> list[tuple]:
    d = np.load(path, allow_pickle=False)
    t = d["jp3_t_s"]
    cls = d["jp3_class"]
    used = d["jp3_used_bound_Pa"]
    ptr = d["jp3_p_tr_Pa"]
    rows = []
    with np.errstate(invalid="ignore"):
        breach = ((cls == 2) | (cls == 4)) & (ptr > used + 1.0)
    tt = d["t_s"]
    idx_of = {round(v, 4): i for i, v in enumerate(tt)}
    for leg in range(4):
        reads = np.flatnonzero(breach[:, leg])
        if reads.size == 0:
            continue
        first = int(reads[0])
        start = first
        while start > 0 and cls[start - 1, leg] in (2, 3):
            start -= 1
        lo = max(start - 6, 0)
        hi = min(int(reads[-1]) + 4, len(t))
        print(f"\n== {path.stem} leg {LEGS[leg]} breach reads {reads.size} "
              f"first t {t[first]:.1f} carry start t {t[start]:.1f}", file=out)
        print("  t     ph    cls   state   u[mm/s] stroke[mm] lk  p_tr  rodrd  head  used  carry "
              "model  extb  src     inh  gfill[mm] p1held p1x[mm] p1need F[kN]", file=out)
        for r in range(lo, hi):
            i = idx_of.get(round(float(t[r]), 4))
            ph = str(d["phase"][i])[:5] if i is not None else "?"
            stroke = d["motor_stroke_m"][i, leg] * 1e3 if i is not None else np.nan
            locked = int(d["locked"][i, leg]) if i is not None else -1
            rod_rd = d["rod_pressure_Pa"][i, leg] / BAR if i is not None else np.nan
            head = d["head_pressure_Pa"][i, leg] / BAR if i is not None else np.nan
            held = int(d["p1_gate_held"][i, leg]) if i is not None else -1
            p1x = d["p1_x_m"][i, leg] * 1e3 if i is not None else np.nan
            p1need = d["p1_need_m"][i, leg] * 1e3 if i is not None else np.nan
            force = d["true_force_N"][i, leg] / 1e3 if i is not None else np.nan
            mark = "*" if breach[r, leg] else " "
            print(f"{mark}{t[r]:5.1f} {ph:5s} {name_of(CLASS, cls[r, leg]):5s} "
                  f"{name_of(STATE, d['jp3_plant_state'][r, leg]):6s} "
                  f"{d['jp3_u_m_s'][r, leg] * 1e3:7.3f} {stroke:9.3f} {locked:2d} "
                  f"{ptr[r, leg] / BAR:6.2f} {rod_rd:6.2f} {head:6.2f} "
                  f"{used[r, leg] / BAR:6.2f} {d['jp3_carry_bound_Pa'][r, leg] / BAR:6.2f} "
                  f"{d['jp3_model_bound_Pa'][r, leg] / BAR:6.2f} "
                  f"{d['jp3_ext_bound_Pa'][r, leg] / BAR:6.2f} "
                  f"{name_of(SRC, d['jp3_model_bound_source'][r, leg]):8s} "
                  f"{int(d['jp3_model_bound_inherited'][r, leg])} "
                  f"{d['jp3_gate_fill_m'][r, leg] * 1e3:7.3f} {held:2d} {p1x:7.3f} {p1need:7.3f} "
                  f"{force:7.2f}", file=out)
        for r in reads:
            rows.append((path.stem, LEGS[leg], float(t[r]), float(ptr[r, leg] / BAR),
                         float(used[r, leg] / BAR)))
    return rows


def main() -> None:
    folder = Path(sys.argv[1])
    out = open(sys.argv[2], "w", encoding="utf-8", newline="\n") if len(sys.argv) > 2 else sys.stdout
    total = []
    for path in sorted(folder.glob("*.npz")):
        total += series(path, out)
    print(f"\nbreach reads total {len(total)}", file=out)
    if out is not sys.stdout:
        out.close()
        print(f"breach reads total {len(total)}")


if __name__ == "__main__":
    main()
