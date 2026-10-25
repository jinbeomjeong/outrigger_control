"""H4 re-anchoring (adopted stair P_stop) under seal friction F_s, and the first-step rear axial rise (spec rev. 17).

Part F (F_s sensitivity, dynamics_model.md 5.13.7 / spec rev. 15 suppl. 1):
  adopted H4 'A' = run_pad_friction_mode_check.H4_SPEC (P_stop 45 / 32.41 / 32.41 / 32.41 kN, F_band 13 kN fixed,
  margin 10 kN) and 'B' = R6 rule (measured band ~ F_s + 1 kN, floor margin 11.5 kN, U69), F_s 0 / 3.7 / 12 kN.
Part O (order / first step, cad leg_rod_lateral_check rev. 3.1 sections 6-7): steps RR,RL,RR,RL vs RL,RR,RL,RR and
  first P_stop 45 / 55 / 65 kN; per-leg max tangential force and the simultaneous axial force.
Harness: run_pad_friction_mode_check.case (fric_mode 1, beta 1.0 GPa, t_hold 60 s) -> run_pad_tangential_check.run_one
  (reduced L1 plant + pad tangential bushings, C2 R1 'R:BS_hold', discrete T = 20 ms, extra delay 1). Read-only imports.
Run (project root, dynamics-dev activated; P-cores pinned by this script, workers inherit):
  conda run -n dynamics-dev python -I <this file> [--part F|O|all] [--workers 8]
Output: <this folder>/s6r17_h4_fs_order.json. Units kN / mm / s / deg in the outputs; legs FL, FR, RL, RR.
"""
from __future__ import annotations

import argparse
import json
import os
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
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
PROJECT = REPO
for sub in ("01_dynamics", "03_control", "00_cad"):
    sys.path.insert(0, str(PROJECT / "04_scripts" / sub))

import numpy as np  # noqa: E402
import run_pad_friction_mode_check as rpf  # noqa: E402
import run_pad_tangential_check as rpt  # noqa: E402
import run_mast_flex_c2_check as rmf  # noqa: E402

OUT = OUT_DIR / "s6r17_h4_fs_order.json"
LEGS = ("FL", "FR", "RL", "RR")
F_MIN = rpf.F_MIN
GUARD_KN = (F_MIN + 5e3) / 1e3
SLOPES = {"V:pitch+3.5": (0.0, 3.5), "V:pitch-3.5": (0.0, -3.5), "P:pitch+3.2": (0.0, 3.2), "P:pitch-3.2": (0.0, -3.2)}
P_CORES = list(range(16))


def stair(first, floor):
    return [max(s, 20e3, floor) for s in (first, 30e3, 20e3, 20e3)]


def spec(p_stop, steps=("RR", "RL", "RR", "RL")):
    s = dict(rpf.H4_SPEC)
    s["P_stop_N"] = list(p_stop); s["steps"] = list(steps)
    return s


def spec_B(Fs):
    band = max(Fs, 1.3e3) + 1e3            # measured band ~ F_s (F_s 0: 2.2-2.4 kN measured, spec 44.3) + 1 kN margin
    return spec(stair(45e3, F_MIN + band + 11.5e3))


def mk(cid, tag, mast, km, Fs, sp, seed=12345):
    c = rpf.case(cid, "top", SLOPES[tag], mast, fmode=1, kt_mode=km, h4=True, t_hold=60.0, seed=seed)
    c["rcfg"]["reanchor"] = sp
    c["Fs"] = float(Fs)
    return c


def cases(part):
    C = []
    if part in ("F", "all"):
        spA = spec(rpf.H4_SPEC["P_stop_N"])
        for tag in SLOPES:
            for Fs in (0.0, 3.7e3, 12e3):
                for sn, sp in (("A", spA), ("B", spec_B(Fs))):
                    for km in ("yaml", "ext"):
                        for s in range(3):
                            C.append(mk(f"F|{sn}|{tag}|rigid|{km}|Fs{Fs / 1e3:g}|{s}", tag, "rigid", km, Fs, sp, 12345 + s))
                    for mast in ("stiff", "upper", "lower"):
                        C.append(mk(f"F|{sn}|{tag}|{mast}|yaml|Fs{Fs / 1e3:g}|0", tag, mast, "yaml", Fs, sp))
    if part in ("O", "O2", "all"):
        floor = F_MIN + 13e3 + 10e3
        var = {"base": spec(stair(45e3, floor)),
               "first55": spec(stair(55e3, floor)),
               "first65": spec(stair(65e3, floor)),
               "RLfirst": spec(stair(45e3, floor), ("RL", "RR", "RL", "RR")),
               "RLfirst55": spec(stair(55e3, floor), ("RL", "RR", "RL", "RR")),
               "uniform45": spec([45e3, 45e3, 45e3, 45e3]),
               "pre45": spec([45e3, 45e3, floor, floor]),
               "pre55": spec([55e3, 55e3, floor, floor]),
               "pre55x6": spec([55e3, 55e3, floor, floor, floor, floor], ("RR", "RL") * 3)}
        if part == "O2":
            var = {k: var[k] for k in ("base", "pre45", "pre55", "pre55x6")}
        for tag in SLOPES:
            for km in ("yaml", "ext"):
                for vn, sp in var.items():
                    C.append(mk(f"O|{vn}|{tag}|rigid|{km}|Fs0|0", tag, "rigid", km, 0.0, sp))
    return C


def one(c):
    c = dict(c); c["keep_series"] = True
    fm = c.pop("fmode")
    try:
        import psutil
        aff = psutil.Process().cpu_affinity()
    except Exception:  # noqa: BLE001
        aff = None
    out = rpt.run_one(c)
    out["worker_affinity"] = aff
    if "error" in out:
        return out
    pl = rmf.LAST["plant"]
    if pl.fmode != fm or pl.case_id != c["id"]:
        raise RuntimeError("friction-mode / case identity check failed")
    ser = out.pop("_series")
    t, H = ser["t"], ser["H"]
    Fl = H[:, 0:4]; Ft = np.hypot(H[:, 17:21], H[:, 21:25])
    ra = out.get("reanchor", {})
    log = ra.get("log", [])
    m = {}
    if log:
        t0 = log[0]["t"]; ends = [e["t"] for e in log if e["what"] == "end"]
        t1 = ends[0] if ends else t[-1]
        w = (t >= t0) & (t <= t1)
        jft = np.argmax(np.where(w[:, None], Ft, -1), axis=0)
        jfl = np.argmax(np.where(w[:, None], Fl, -1), axis=0)
        j0 = int(np.searchsorted(t, t0))
        m = {"Ft_start_kN": (Ft[j0] / 1e3).round(2).tolist(), "Fl_start_kN": (Fl[j0] / 1e3).round(2).tolist(),
             "Ft_max_kN": [round(Ft[jft[i], i] / 1e3, 2) for i in range(4)],
             "Fl_at_Ft_max_kN": [round(Fl[jft[i], i] / 1e3, 2) for i in range(4)],
             "Fl_max_kN": [round(Fl[jfl[i], i] / 1e3, 2) for i in range(4)],
             "Ft_at_Fl_max_kN": [round(Ft[jfl[i], i] / 1e3, 2) for i in range(4)],
             "Ft_final_kN": (Ft[-1] / 1e3).round(2).tolist()}
        # per-step pairs (axial, tangential) per leg; 'Fl_max_Ft_held' = max axial while Ft >= Ft(start) - 1 kN
        bnd = [e["t"] for e in log if e["what"] in ("start", "next")] + [t1]
        m["step_pairs"] = []
        for k in range(len(bnd) - 1):
            ws = (t >= bnd[k]) & (t <= bnd[k + 1])
            if not ws.any():
                continue
            Fs_, Ts_ = Fl[ws], Ft[ws]
            ia, it_ = Fs_.argmax(axis=0), Ts_.argmax(axis=0)
            held = Ts_ >= (Ft[j0] - 1e3)[None, :]
            flh = np.where(held, Fs_, -1.0).max(axis=0)
            m["step_pairs"].append({
                "k": k, "Fl_max_kN": [round(Fs_[ia[i], i] / 1e3, 2) for i in range(4)],
                "Ft_at_Fl_max_kN": [round(Ts_[ia[i], i] / 1e3, 2) for i in range(4)],
                "Ft_max_kN": [round(Ts_[it_[i], i] / 1e3, 2) for i in range(4)],
                "Fl_at_Ft_max_kN": [round(Fs_[it_[i], i] / 1e3, 2) for i in range(4)],
                "Fl_max_Ft_held_kN": [None if v < 0 else round(v / 1e3, 2) for v in flh]})
        steps = []
        for s in ra.get("steps", []):
            if s.get("P_stop_reading_kN") is None:
                continue
            steps.append({"k": s["k"], "leg": s["leg"], "reason": s["reason"], "P_stop_reading_kN": s["P_stop_reading_kN"],
                          "min_true_kN": s["min_true_cyl_kN"],
                          "gap_kN": round(s["P_stop_reading_kN"] - s["min_cyl_by_phase"].get("hold", {}).get(
                              "min_kN", s["min_true_cyl_kN"]), 2),
                          "by_phase": s["min_cyl_by_phase"], "max_true_kN": s["max_true_cyl_kN"]})
        m["steps"] = steps
        m["completed"] = ra.get("completed"); m["relevel_events"] = len(ra.get("relevel_events", []))
        m["min_true_ra_kN"] = ra.get("min_true_cyl_kN"); m["duration_s"] = ra.get("duration_s")
        m["reasons"] = [e.get("reason") for e in log if e["what"] == "hold"]
    out["x"] = m
    out.pop("reanchor", None); out.pop("tang", None)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="all", choices=("F", "O", "O2", "all"))
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    import psutil
    pr = psutil.Process(); pr.cpu_affinity(P_CORES)      # P-cores 0-15; spawned workers inherit
    C = cases(a.part)
    print(f"cases {len(C)}, affinity {pr.cpu_affinity()}", flush=True)
    if a.dry_run:
        return
    t0 = time.perf_counter()
    r0 = one(C[0])
    from multiprocessing import Pool
    with Pool(a.workers) as p:
        runs = [r0] + p.map(one, C[1:], chunksize=1)
    res = {"meta": {"n": len(C), "wall_s": round(time.perf_counter() - t0, 1), "guard_kN": GUARD_KN,
                    "F_min_N": F_MIN, "parent_affinity": pr.cpu_affinity(), "workers": a.workers,
                    "errors": sum(1 for r in runs if "error" in r)}, "runs": runs}
    out_path = OUT if a.part == "all" else OUT.with_name(f"s6r17_part{a.part}.json")
    out_path.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(json.dumps(res["meta"]), flush=True)


if __name__ == "__main__":
    main()
