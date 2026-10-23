"""S6 spec revision 4: H4 re-evaluation with the Chrono-type pad friction decomposition (fric_mode 1, dyn rev. 26).

Re-uses 04_scripts/01_dynamics/run_pad_friction_mode_check.py case() / one() by import (no edits): the dynamics C2RA
re-anchoring implementation with an explicit P_stop staircase, rigid mast, pressure judge, delay 1, seed 12345.
Variants (rear targets RR/RL in the twist mode unless noted):
  off      : no re-anchoring
  H4       : adopted, P_stop = max(45/30/20/20, 20, F_min + F_band 13 + 10) = 45 / 32.45 / 32.45 / 32.45 kN
  H4lb     : same staircase after a probe-validated band (F_band 1 kN): 45 / 30 / 20.45 / 20.45 kN
  H4lb6    : H4lb with two more 20.45 kN steps (6 steps)
  front    : targets FR / FL (downhill axle on a nose-down floor), P_stop 95 / 80 / 70 / 70 kN (feasibility probe)
Floors: top V:pitch+-3.5, P:pitch+-3.2 (YAML / secant k_t); middle / bottom V:pitch+3.5 (YAML / secant).
Metrics: rod lateral load L per leg at the end (body-xy of N n + T), max over legs, rear / front max, min true cylinder
force, t_ready, and the closed form L_max ~ mu (P_stop,last + W_rod) + N_front sin(beta) check.
Run: conda run -n dynamics-dev python -I s6r4_h4_fric1.py <project_root> <out_json> [workers]
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import run_pad_friction_mode_check as pfm  # noqa: E402

F_MIN = pfm.F_MIN
BASE = dict(pfm.H4_SPEC)
VAR = {
    "H4": dict(BASE),
    "H4lb": dict(BASE, P_stop_N=[45e3, 30e3, F_MIN + 1e3 + 10e3, F_MIN + 1e3 + 10e3]),
    "H4lb6": dict(BASE, steps=["RR", "RL", "RR", "RL", "RR", "RL"],
                  P_stop_N=[45e3, 30e3] + [F_MIN + 1e3 + 10e3] * 4),
    "front": dict(BASE, steps=["FR", "FL", "FR", "FL"], P_stop_N=[95e3, 80e3, 70e3, 70e3]),
}


def mk(cid, level, ang, kt, var):
    c = pfm.case(cid, level, ang, fmode=1, kt_mode=kt, h4=(var != "off"), t_hold=60.0 if var != "off" else None)
    if var != "off":
        c["rcfg"]["reanchor"] = dict(VAR[var])
    return c


def cases():
    C = []
    for tg, ang in (("V:pitch+3.5", (0.0, 3.5)), ("V:pitch-3.5", (0.0, -3.5)), ("P:pitch+3.2", (0.0, 3.2)),
                    ("P:pitch-3.2", (0.0, -3.2))):
        for kt in ("yaml", "ext"):
            vs = ["off", "H4", "H4lb", "H4lb6"] + (["front"] if "+" in tg else [])
            for v in vs:
                C.append(mk(f"top|{tg}|{kt}|{v}", "top", ang, kt, v))
    for lv in ("middle", "bottom"):
        for kt in ("yaml", "ext"):
            for v in ("off", "H4", "H4lb"):
                C.append(mk(f"{lv}|V:pitch+3.5|{kt}|{v}", lv, (0.0, 3.5), kt, v))
    return C


def main():
    out_json = Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    from multiprocessing import get_context
    C = cases()
    t0 = time.time()
    with get_context("spawn").Pool(workers) as p:
        runs = p.map(pfm.one, C, chunksize=1)
    rows = []
    for c, r in zip(C, runs):
        if "error" in r:
            rows.append({"id": c["id"], "error": r["error"]}); print(c["id"], r["error"]); continue
        L = r["fm"]["end"]["L_kN"]; T = r["fm"]["end"]["T_kN"]
        row = {"id": c["id"], "L_kN": L, "T_kN": T, "L_max": max(L), "L_front": max(L[:2]), "L_rear": max(L[2:]),
               "minF_kN": r.get("min_true_cyl_force_kN"), "t_ready_s": r.get("t_ready_s"),
               "util": r["fm"]["end"]["util"], "fails": r.get("fails"),
               "ra_steps": [(s.get("leg"), s.get("reason"), s.get("P_stop_reading_kN"), s.get("min_true_cyl_kN"))
                            for s in (r.get("ra") or {}).get("steps", [])]}
        rows.append(row)
        print(f"{c['id']:32s} Lmax {row['L_max']:6.2f} front {row['L_front']:6.2f} rear {row['L_rear']:6.2f} "
              f"minF {row['minF_kN']} ready {row['t_ready_s']} steps {[(a, b) for a, b, _, _ in row['ra_steps']]}")
    out_json.write_text(json.dumps({"rows": rows, "variants": VAR, "runtime_s": time.time() - t0}, indent=1,
                                   default=float))


if __name__ == "__main__":
    main()
