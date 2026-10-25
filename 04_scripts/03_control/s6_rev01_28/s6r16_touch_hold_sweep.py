"""Sensitivity of the C2 R1 touch confirmation time (touch_hold_s) -- s6_control_spec.md rev. 16.

Background: dynamics_model.md rev. 31, 5.13.2. Without the touch confirmation (it3) the touchdown event
(20 ms sample of P >= 1.5 F_min) splits into two branches (E: touch ~16.62 s, L: ~16.90 s) depending on the
rocking phase; branch L gave 8.36 / 2.10 kN (RR) at top, rigid mast, diag 3 / 3.2 deg, beta 1.6 GPa. R1
(hold 0.5 s + re-approach 0.25 v_max) removes it (>= 37.9 kN). Question: down to which hold time does the worst
case stay above the guard threshold F_min + 5 kN?

Harness (read-only imports, nothing in the project is modified):
  run_s6_slope_boundary_check.td_one -> run_pad_tangential_check.run_one -> run_c2_revision.C2R (reduced plant
  with pad tangential bushings, crawler, 1-mode flexible mast option). Gain sets 'R:TH<h>' = 'R:BS_hold' with
  touch_hold_s = h (approach 0.25 v_max, B fixes and stroke source unchanged); '_d0' = no extra delay.

Run (project root, dynamics-dev activated):
  conda run -n dynamics-dev python -I <this file> --dry-run        # case list + checks only (seconds)
  conda run -n dynamics-dev python -I <this file> --stage sweep    # ~1216 cases, 12 workers, ~20-30 min
  conda run -n dynamics-dev python -I <this file> --stage report
Output: <this folder>/s6r16_touch_hold_sweep.json
Conventions: body x fwd, y left, z up; roll + = left up, pitch + = nose down; floor angles in deg; SI inside,
kN / s in outputs; legs FL, FR, RL, RR; controller period T = 20 ms (discrete), plant continuous (L1 reduced).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# --- paths (migrated from the 2026-10-22 session scratchpad ctrl-run on 2026-10-25) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[3]  # 04_scripts/03_control/s6_rev01_28/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s6_rev01_28"  # results of these scripts
OUT_DIR.mkdir(parents=True, exist_ok=True)
_sys.path.append(str(REPO / "04_scripts" / "03_control"))  # siblings migrated earlier
# ---
PROJECT = REPO
sys.path.insert(0, str(PROJECT / "04_scripts" / "01_dynamics"))
sys.path.insert(0, str(PROJECT / "04_scripts" / "03_control"))
sys.path.insert(0, str(PROJECT / "04_scripts" / "00_cad"))

import run_s6_slope_boundary_check as rsb  # noqa: E402  (imports rpt, rmf, rcc, run_c2_revision)
import run_c2_timedomain as c2t  # noqa: E402

OUT = OUT_DIR / "s6r16_touch_hold_sweep.json"
HOLDS = (0.0, 0.10, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50)
FLEX_HOLDS = (0.30, 0.40, 0.50)
SEEDS = tuple(12345 + k for k in range(8))
BETAS = (0.69e9, 1.0e9, 1.6e9)
FLOORS = {"diag3": (2.1213, 2.1213), "diag3.2": (2.2627, 2.2627), "pitch+3.3": (0.0, 3.3)}
GUARD_KN = rsb.GUARD / 1e3   # F_min (YAML) + 5 kN


def gs(h, d0=False):
    return f"R:TH{h:.2f}" + ("_d0" if d0 else "")


# register the hold variants at import (spawned workers re-import this module as __mp_main__)
for _h in HOLDS:
    c2t.GAINSETS[gs(_h)] = dict(c2t.GAINSETS["R:BS_hold"], touch_hold_s=float(_h))
    c2t.GAINSETS[gs(_h, True)] = dict(c2t.GAINSETS["R:BS_hold_d0"], touch_hold_s=float(_h))


def floors(d):
    f = dict(FLOORS)
    f["N:r+p+0.5"] = tuple(d["crawler"]["D_compliance"]["top"]["boundary_floor_image"]["r+p+0.5"]["floor"])
    return f


def cases(d):
    fl = floors(d)
    C = []
    for h in HOLDS:                                   # A: rigid mast, 4 floors x 3 beta x 8 seeds
        for tag, ang in fl.items():
            for b in BETAS:
                for s in SEEDS:
                    C.append(rsb.mkc(f"A|{h:.2f}|{tag}|{b:g}|{s}", "top", ang, "rigid", gs(h), seed=s, beta=b))
    for h in HOLDS:                                   # B: no extra delay, beta 1.6
        for tag in ("diag3.2", "N:r+p+0.5"):
            for s in SEEDS:
                C.append(rsb.mkc(f"B|{h:.2f}|{tag}|1.6e+09|{s}", "top", fl[tag], "rigid", gs(h, True), seed=s,
                                 beta=1.6e9))
    for h in FLEX_HOLDS:                              # C: flexible masts, beta 1.6
        for mast in ("stiff", "upper", "lower"):
            for tag in ("diag3.2", "N:r+p+0.5"):
                for s in SEEDS:
                    C.append(rsb.mkc(f"C|{h:.2f}|{mast}|{tag}|{s}", "top", fl[tag], mast, gs(h), seed=s, beta=1.6e9))
    for tag, ang in fl.items():                       # R: it3 reference (branch existence in this harness)
        for b in (1.0e9, 1.6e9):
            for s in SEEDS:
                C.append(rsb.mkc(f"R|it3|{tag}|{b:g}|{s}", "top", ang, "rigid", "R:it3", seed=s, beta=b))
    return C


def checks(d, C):
    ref = dict(c2t.GAINSETS["R:BS_hold"])
    assert c2t.GAINSETS[gs(0.5)] == ref, "hold 0.50 must equal R:BS_hold"
    assert ref["touch_hold_s"] == 0.5 and ref["touch_approach_frac"] == 0.25
    ids = [c["id"] for c in C]
    assert len(ids) == len(set(ids))
    # regression anchor: same case as td_robust 'seed|top|rigid|r+p+0.5|1' (seed 12346, beta default 1.0 GPa)
    anchor = next(r for r in d["td_robust"]["runs"] if r.get("id") == "seed|top|rigid|r+p+0.5|1")
    return {"n_cases": len(C), "by_group": {g: sum(1 for i in ids if i.startswith(g + "|")) for g in "ABCR"},
            "guard_kN": GUARD_KN, "anchor_td_robust_min_kN": anchor.get("min_true_cyl_force_substep_kN"),
            "floor_N:r+p+0.5_deg": floors(d)["N:r+p+0.5"]}


def summarize(runs):
    out = {}
    for r in runs:
        if "error" in r:
            continue
        g, h = r["id"].split("|")[:2]
        key = f"{g}|{h}"
        e = out.setdefault(key, {"n": 0, "min_kN": 1e9, "worst": None, "fails": 0, "below_guard": 0,
                                 "t_touch_s": []})
        e["n"] += 1
        m = r.get("min_true_cyl_force_substep_kN")
        if m is not None and m < e["min_kN"]:
            e["min_kN"] = m
            e["worst"] = {"id": r["id"], "leg": r.get("min_true_leg_substep"),
                          "t_after_liftoff_s": r.get("t_min_after_liftoff_s")}
        e["fails"] += int(bool(r.get("fails")))
        e["below_guard"] += int(m is None or m < GUARD_KN)
        e["t_touch_s"].append(r.get("t_touch_s"))
    for e in out.values():
        tt = sorted(t for t in e["t_touch_s"] if t is not None)
        e["t_touch_range_s"] = [tt[0], tt[-1]] if tt else None
        del e["t_touch_s"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("sweep", "report"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--anchor", action="store_true", help="run the one regression-anchor case (~15 s)")
    a = ap.parse_args()
    d = rsb.load()
    C = cases(d)
    info = checks(d, C)
    if a.anchor:
        ang = floors(d)["N:r+p+0.5"]
        r = rsb.td_one(rsb.mkc("anchor|0.50", "top", ang, "rigid", gs(0.5), seed=12346))
        info["anchor_this_min_kN"] = r.get("min_true_cyl_force_substep_kN")
        info["anchor_this_t_touch_s"] = r.get("t_touch_s")
    if a.dry_run or a.stage is None:
        print(json.dumps(info, indent=1))
        return
    if a.stage == "sweep":
        t0 = time.perf_counter()
        r0 = rsb.td_one(C[0])
        from multiprocessing import Pool
        with Pool(rsb.WORKERS) as pool:
            runs = [r0] + pool.map(rsb.td_one, C[1:], chunksize=1)
        res = {"meta": dict(info, wall_s=round(time.perf_counter() - t0, 1), holds=HOLDS, seeds=SEEDS),
               "runs": runs}
        OUT.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    res = json.loads(OUT.read_text(encoding="utf-8"))
    print(json.dumps(summarize(res["runs"]), indent=1))


if __name__ == "__main__":
    main()
