"""Ed. 7 dynamics review Q7-D1, step 3 (dynamics-expert, 2026-11-24; analysis only, read only).

What the leg commands look like in the last seconds of every LEVEL segment that ends in a
non-LEVEL phase (records B j9_main / sens, C), per period:
  - "all-zero"   : u = 0 on all four legs
  - "blind-only" : every nonzero |u| <= u_hold (at least one nonzero)
  - "moving"     : some |u| > u_hold
For the blind-only periods: whether the nonzero sign pattern is the twist pattern +-n (all four
nonzero), and the twist load D = n . F_true. Also the count of LEVEL segments whose last 2.0 s
(20 periods) before leaving LEVEL are blind-only with the same sign on some leg (a would-be
A(i)-b trigger right at completion, i.e. what trigger condition 3 must exclude).
Output: TXT at --out. stdout ASCII.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405"
           r"\records_after_stop")
DIRS = {"B_j9_main": RUN / "B_a1" / "j9_main_t4h", "B_sens": RUN / "B_a1" / "sens_t4h",
        "C_cf": RUN / "C_a2" / "counterfactual_t4h"}
B3_JSON = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design"
               r"\dynamics_v6\b3_twist_stiffness.json")
U_HOLD = 2.09243016e-4
TAIL = 100   # periods (10 s) before leaving LEVEL


def segments(phase):
    out, start = [], 0
    for i in range(1, len(phase) + 1):
        if i == len(phase) or phase[i] != phase[start]:
            out.append((str(phase[start]), start, i - 1))
            start = i
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    n = np.array(json.loads(B3_JSON.read_text(encoding="utf-8"))["n"])
    L = []
    for tag, folder in DIRS.items():
        tot = {"all_zero": 0, "blind_only": 0, "moving": 0}
        twist_pat = 0
        D_blind = []
        seg_n = seg_trig_at_end = seg_next = 0
        nxt = {}
        for path in sorted(folder.glob("*.npz")):
            with np.load(path, allow_pickle=False) as d:
                ph, u, F, lk = d["phase"], d["command_m_s"], d["true_force_N"], d["locked"]
            segs = segments(ph)
            for si, (name, i0, i1) in enumerate(segs):
                if name != "level" or si == len(segs) - 1:
                    continue
                seg_n += 1
                nxt[segs[si + 1][0]] = nxt.get(segs[si + 1][0], 0) + 1
                a = max(i0, i1 - TAIL + 1)
                for k in range(a, i1 + 1):
                    au = np.abs(u[k])
                    if np.all(au <= 1e-12):
                        tot["all_zero"] += 1
                    elif np.all(au <= U_HOLD):
                        tot["blind_only"] += 1
                        D_blind.append(float(n @ F[k]) / 1e3)
                        if np.all(au > 1e-12) and (np.all(np.sign(u[k]) == np.sign(n))
                                                   or np.all(np.sign(u[k]) == -np.sign(n))):
                            twist_pat += 1
                    else:
                        tot["moving"] += 1
                # would-be trigger in the last 20 periods: some leg locked, same sign, blind
                b = i1 - 19
                if b >= i0:
                    win = u[b:i1 + 1]
                    for leg in range(4):
                        w = win[:, leg]
                        if (np.all(lk[b:i1 + 1, leg]) and np.all(np.abs(w) > 1e-12)
                                and np.all(np.abs(w) <= U_HOLD)
                                and np.all(np.sign(w) == np.sign(w[0]))):
                            seg_trig_at_end += 1
                            break
        Db = np.array(D_blind) if D_blind else np.zeros(1)
        L.append(f"[{tag}] LEVEL segments followed by another phase: {seg_n}; next phase {nxt}")
        L.append(f"   last {TAIL} periods: {tot}; blind-only with twist sign pattern: {twist_pat}")
        L.append(f"   D in blind-only periods kN: p05 {np.percentile(Db, 5):.2f} median "
                 f"{np.median(Db):.2f} p95 {np.percentile(Db, 95):.2f}")
        L.append(f"   segments whose last 20 periods hold a would-be A(i)-b trigger "
                 f"(locked, one sign, blind): {seg_trig_at_end}")
    Path(args.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
