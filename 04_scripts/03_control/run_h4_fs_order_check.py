"""H4 re-anchoring stair under seal friction F_s, step order / depth, and the rod lateral load of the target pad
(00_docs/04_control/s6_control_spec.md rev. 17-18).

Parts (each writes its own JSON in 06_analysis/02_control/):
  F   F_s sensitivity (dynamics_model.md 5.13.7): spec 'A' = run_pad_friction_mode_check.H4_SPEC (P_stop 45 / 32.41 /
      32.41 / 32.41 kN = the R2-era floor with F_band fixed at 13 kN, margin 10 kN) and 'B' = R5/R6 rule (H5a measured
      band ~ max(F_s, 1.3 kN) + 1 kN, floor margin 11.5 kN, U69), F_s 0 / 3.7 / 12 kN, V/P pitch +-3.5 / 3.2,
      rigid (YAML and secant k_t, seeds 12345..12347) + stiff / upper / lower masts (YAML, seed 12345).
  O   first step / order (cad leg_rod_lateral_check rev. 3.1): spec A base and variants (first P_stop 55 / 65 kN, RL
      first, uniform 45 kN), rigid, YAML / secant k_t.
  O2  pre-pass variants (45-45 / 55-55 then the floor, 6 steps).
  S   sensitivity bundle at P:pitch-3.2 (masts, beta, seeds, F_s, auger levels, delay 0) for specs A / A6 / R6.
  L   H4 off at P:pitch-3.2: levelling-end lateral load vs F_s 0 / 3.7 / 12 kN and an L1-R upper-bound proxy
      (rod-side spring always in parallel with the oil column; the L1-R reduced plant itself is not in this harness).
  N   nose-down pairs under the R7 default (H4 only nose down): R6 stair, P:pitch+3.2 13-variant bundle + V:pitch+3.5.
      --series adds per-step 20 ms series (t, Fl, Ft per leg) to step_pairs.
  O3  spec A6 (R6 pressure-only, floor 33.91 kN) and spec R6 (= B at F_s 0: 45 / 30 / 23.2 / 23.2 kN) and its depth / speed / order variants, rod lateral load of the
      unloaded target pad (cad rev. 3.2 7.1).
Outputs per run 'x': Ft_* = |pad force component perpendicular to the rod| (body x / y at the pad, = rod lateral load),
  Fl_* = pad axial contact force, per-step pairs 'step_pairs' (max axial with its lateral, max lateral with its axial,
  max axial while the lateral is still >= start - 1 kN), stop readings, reasons, min true cylinder force.
Harness: run_pad_friction_mode_check.case (fric_mode 1, beta 1.0 GPa, t_hold 60 s) -> run_pad_tangential_check.run_one
  (reduced L1 plant + pad tangential bushings mu 0.5, C2 R1 'R:BS_hold', discrete T = 20 ms, extra delay 1 step,
  negative feedback). Read-only imports, nothing else is modified.
Run (project root, dynamics-dev activated; the parent pins itself to the P-cores 0-15 and the Pool workers inherit):
  conda run -n dynamics-dev python -I 04_scripts/03_control/run_h4_fs_order_check.py --part F|O|O2|O3 [--workers 8]
Each part < 10 min with 8 workers (F 256 cases ~ 8.5 min, O 48 ~ 1 min, O2 32 ~ 40 s, O3 48 ~ 1 min).
Units in the outputs: kN / mm / s; legs FL, FR, RL, RR; body x fwd, y left, z up; pitch > 0 nose down.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
PROJECT = SCRIPTS.parent
for sub in ("01_dynamics", "03_control", "00_cad"):
    sys.path.insert(0, str(SCRIPTS / sub))

import numpy as np  # noqa: E402
import run_pad_friction_mode_check as rpf  # noqa: E402
import run_pad_tangential_check as rpt  # noqa: E402
import run_mast_flex_c2_check as rmf  # noqa: E402
import dyn_model as dm  # noqa: E402

OUT_DIR = PROJECT / "06_analysis" / "02_control"
LEGS = ("FL", "FR", "RL", "RR")
F_MIN = rpf.F_MIN
GUARD_KN = (F_MIN + 5e3) / 1e3
SLOPES = {"V:pitch+3.5": (0.0, 3.5), "V:pitch-3.5": (0.0, -3.5), "P:pitch+3.2": (0.0, 3.2), "P:pitch-3.2": (0.0, -3.2)}
P_CORES = list(range(16))
BAND_FS0_N = 2.3e3            # measured band at F_s 0 (spec 44.3: 2.2-2.4 kN)
R6_FLOOR_N = F_MIN + BAND_FS0_N + 11.5e3


def stair(first, floor):
    return [max(s, 20e3, floor) for s in (first, 30e3, 20e3, 20e3)]


def spec(p_stop, steps=("RR", "RL", "RR", "RL"), speed_frac=None):
    s = dict(rpf.H4_SPEC)
    s["P_stop_N"] = list(p_stop); s["steps"] = list(steps)
    if speed_frac is not None:
        s["speed_frac"] = float(speed_frac)
    return s


def spec_B(Fs):
    band = max(Fs, 1.3e3) + 1e3            # measured band ~ F_s (F_s 0: 2.2-2.4 kN measured, spec 44.3) + 1 kN margin
    return spec(stair(45e3, F_MIN + band + 11.5e3))


def mk(cid, tag, mast, km, Fs, sp, seed=12345, level="top", beta=1.0e9, gainset=rpt.R1):
    c = rpf.case(cid, level, SLOPES[tag], mast, fmode=1, gainset=gainset, kt_mode=km, h4=True, t_hold=60.0, seed=seed,
                 beta=beta)
    c["rcfg"]["reanchor"] = sp
    c["Fs"] = float(Fs)
    return c


A6_FLOOR_N = F_MIN + 13e3 + 11.5e3     # R6 pressure-only judge: band stays at the initial 13 kN (no H5a probe)


def cases_S(tag="P:pitch-3.2", spec_names=("A", "A6", "R6"), prefix="S"):
    """Sensitivity bundle at P:pitch-3.2 (dynamics_model.md 5.13.5 suppl. 3, item 4): specs A (R5 pressure-only,
    45 / 32.41), A6 (R6 pressure-only, 45 / 33.91) and R6 (combined judge, H5a measured band, 45 / 30 / 23.2 / 23.2;
    with F_s the band follows F_s + 1 kN), YAML / secant k_t; one change at a time from the nominal case."""
    specs = {"A": lambda Fs: spec(rpf.H4_SPEC["P_stop_N"]),
             "A6": lambda Fs: spec(stair(45e3, A6_FLOOR_N)),
             "R6": lambda Fs: spec_B(Fs) if Fs > 0 else spec(stair(45e3, R6_FLOOR_N))}
    C = []
    for sn in spec_names:
        sf = specs[sn]
        for km in ("yaml", "ext"):
            base = dict(tag=tag, mast="rigid", km=km, Fs=0.0, seed=12345, level="top", beta=1.0e9, gainset=rpt.R1)
            var = [("nominal", {})]
            var += [(f"seed{s}", {"seed": s}) for s in (12346, 12347)]
            var += [(f"mast_{m}", {"mast": m}) for m in ("stiff", "upper", "lower")]
            var += [(f"beta{b:g}", {"beta": b}) for b in (0.69e9, 1.6e9)]
            var += [(f"Fs{f / 1e3:g}", {"Fs": f}) for f in (3.7e3, 12e3)]
            var += [(f"level_{lv}", {"level": lv}) for lv in ("middle", "bottom")]
            var += [("delay0", {"gainset": rpt.R1 + "_d0"})]
            for vn, ch in var:
                p = dict(base, **ch)
                C.append(mk(f"{prefix}|{sn}|{vn}|{tag}|{p['mast']}|{km}|Fs{p['Fs'] / 1e3:g}|{p['level']}", p["tag"], p["mast"],
                            km, p["Fs"], sf(p["Fs"]), seed=p["seed"], level=p["level"], beta=p["beta"],
                            gainset=p["gainset"]))
    return C


def cases(part):
    C = []
    if part == "S":
        return cases_S()
    if part == "L":    # H4 off, levelling-end lateral load at P:pitch-3.2 (dynamics 5.13.5 suppl. 4, conditions 3 / 4)
        C = []
        for km in ("yaml", "ext"):
            for s in (12345, 12346, 12347):
                for Fs in (0.0, 3.7e3, 12e3):
                    c = rpf.case(f"L|base|P:pitch-3.2|rigid|{km}|Fs{Fs / 1e3:g}|{s}", "top", SLOPES["P:pitch-3.2"], "rigid",
                                 fmode=1, kt_mode=km, h4=False, seed=s)
                    c["Fs"] = float(Fs)
                    C.append(c)
                c = rpf.case(f"L|lockproxy|P:pitch-3.2|rigid|{km}|Fs0|{s}", "top", SLOPES["P:pitch-3.2"], "rigid",
                             fmode=1, kt_mode=km, h4=False, seed=s)
                c["rcfg"]["ko_add_N_m"] = list(K_ROD_SIDE)
                C.append(c)
        return C
    if part == "N":    # nose-down pairs under the R7 default (H4 only nose down, spec 86)
        C = cases_S("P:pitch+3.2", ("R6",), "N")
        for km in ("yaml", "ext"):
            C.append(mk(f"N|R6|nominal|V:pitch+3.5|rigid|{km}|Fs0|top", "V:pitch+3.5", "rigid", km, 0.0,
                        spec(stair(45e3, R6_FLOOR_N))))
        return C
    if part == "F":
        spA = spec(rpf.H4_SPEC["P_stop_N"])
        for tag in SLOPES:
            for Fs in (0.0, 3.7e3, 12e3):
                for sn, sp in (("A", spA), ("B", spec_B(Fs))):
                    for km in ("yaml", "ext"):
                        for s in range(3):
                            C.append(mk(f"F|{sn}|{tag}|rigid|{km}|Fs{Fs / 1e3:g}|{s}", tag, "rigid", km, Fs, sp, 12345 + s))
                    for mast in ("stiff", "upper", "lower"):
                        C.append(mk(f"F|{sn}|{tag}|{mast}|yaml|Fs{Fs / 1e3:g}|0", tag, mast, "yaml", Fs, sp))
        return C
    floor = F_MIN + 13e3 + 10e3
    var = {"base": spec(stair(45e3, floor)),
           "first55": spec(stair(55e3, floor)),
           "first65": spec(stair(65e3, floor)),
           "RLfirst": spec(stair(45e3, floor), ("RL", "RR", "RL", "RR")),
           "RLfirst55": spec(stair(55e3, floor), ("RL", "RR", "RL", "RR")),
           "uniform45": spec([45e3, 45e3, 45e3, 45e3]),
           "pre45": spec([45e3, 45e3, floor, floor]),
           "pre55": spec([55e3, 55e3, floor, floor]),
           "pre55x6": spec([55e3, 55e3, floor, floor, floor, floor], ("RR", "RL") * 3),
           "R6": spec(stair(45e3, R6_FLOOR_N)),
           "R6_v0.05": spec(stair(45e3, R6_FLOOR_N), speed_frac=0.05),
           "R6_RLfirst": spec(stair(45e3, R6_FLOOR_N), ("RL", "RR", "RL", "RR")),
           "R6_floor30": spec([45e3, 30e3, 30e3, 30e3]),
           "R6_floor40": spec([45e3, 40e3, 40e3, 40e3]),
           "R6_x6": spec([45e3, 30e3] + [R6_FLOOR_N] * 4, ("RR", "RL") * 3),
           "A6": spec(stair(45e3, A6_FLOOR_N))}
    pick = {"O": ("base", "first55", "first65", "RLfirst", "RLfirst55", "uniform45"),
            "O2": ("base", "pre45", "pre55", "pre55x6"),
            "O3": ("A6", "R6", "R6_v0.05", "R6_RLfirst", "R6_floor30", "R6_floor40", "R6_x6")}[part]
    for tag in SLOPES:
        for km in ("yaml", "ext"):
            for vn in pick:
                C.append(mk(f"O|{vn}|{tag}|rigid|{km}|Fs0|0", tag, "rigid", km, 0.0, var[vn]))
    return C


K_ROD_SIDE = [float(dm.load_params()["contact"]["rigid_floor"]["L1"]["derivation"]["k_rod_side_N_m"][nm])
              for nm in LEGS]


class LockProxyPlant(rpt.TPlant):
    """TPlant + RCFG['ko_add_N_m'] added to the oil stiffness of every leg at all times: an upper-bound proxy of the
    L1-R rod-side parallel spring (the real L1-R adds it only while locked and inside its band; not the L1-R model)."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        add = rpt.RCFG.get("ko_add_N_m")
        if add is not None:
            self.ko = self.ko + np.asarray(add, float)


def one_L(c):
    """H4-off run: levelling-end and end pad lateral loads (tang metrics), min true cylinder force."""
    rpt.TPlant = LockProxyPlant           # re-assert in this (possibly spawned) process
    c = dict(c)
    c.pop("fmode", None)
    out = rpt.run_one(c)
    if "error" in out:
        return out
    pl = rmf.LAST["plant"]
    if not isinstance(pl, LockProxyPlant) or pl.case_id != c["id"]:
        raise RuntimeError("plant identity check failed")
    tg = out.get("tang", {})
    out["x"] = {"Ft_ready_kN": tg.get("ready", {}).get("Ft_kN"), "Fl_ready_kN": tg.get("ready", {}).get("Fl_kN"),
                "Ft_end_kN": tg.get("end", {}).get("Ft_kN"), "Ft_dyn_max_post_liftoff_kN": tg.get("dyn_max_post_liftoff_kN"),
                "ko_N_m": pl.ko.round(0).tolist(), "slip_mm_post_liftoff": tg.get("slip_mm_post_liftoff")}
    out.pop("tang", None)
    return out


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
        # per-step pairs (axial, lateral) per leg; 'Fl_max_Ft_held' = max axial while Ft >= Ft(start) - 1 kN
        bnd = [e["t"] for e in log if e["what"] in ("start", "next")] + [t1]
        m["step_pairs"] = []
        for k in range(len(bnd) - 1):
            ws = (t >= bnd[k]) & (t <= bnd[k + 1])
            if not ws.any():
                continue
            Fs_, Ts_ = Fl[ws], Ft[ws]
            ia, it_ = Fs_.argmax(axis=0), Ts_.argmax(axis=0)
            held = Ts_ >= (Ft[j0] - 1e3)[None, :]
            heldF = np.where(held, Fs_, -1.0)
            ih = heldF.argmax(axis=0)
            flh = heldF.max(axis=0)
            tt = t[ws]
            m["step_pairs"].append({
                "k": k, "Fl_max_kN": [round(Fs_[ia[i], i] / 1e3, 2) for i in range(4)],
                "Ft_at_Fl_max_kN": [round(Ts_[ia[i], i] / 1e3, 2) for i in range(4)],
                "Ft_max_kN": [round(Ts_[it_[i], i] / 1e3, 2) for i in range(4)],
                "Fl_at_Ft_max_kN": [round(Fs_[it_[i], i] / 1e3, 2) for i in range(4)],
                "Fl_max_Ft_held_kN": [None if v < 0 else round(v / 1e3, 2) for v in flh],
                "Ft_at_Fl_max_Ft_held_kN": [None if flh[i] < 0 else round(Ts_[ih[i], i] / 1e3, 2) for i in range(4)],
                "t_Fl_max_s": [round(float(tt[ia[i]]), 4) for i in range(4)],
                "t_Ft_max_s": [round(float(tt[it_[i]]), 4) for i in range(4)],
                "t_Fl_max_Ft_held_s": [None if flh[i] < 0 else round(float(tt[ih[i]]), 4) for i in range(4)]})
            if os.environ.get("H4CHK_SERIES") == "1":
                dec = max(1, int(round(0.02 / float(np.median(np.diff(tt)))))) if len(tt) > 1 else 1
                m["step_pairs"][-1]["series_20ms"] = {"t_s": np.round(tt[::dec], 4).tolist(),
                                                     "Fl_kN": np.round(Fs_[::dec] / 1e3, 3).tolist(),
                                                     "Ft_kN": np.round(Ts_[::dec] / 1e3, 3).tolist()}
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
        m["P_stop_spec_kN"] = [round(v / 1e3, 3) for v in c["rcfg"]["reanchor"]["P_stop_N"]]
        m["completed"] = ra.get("completed"); m["relevel_events"] = len(ra.get("relevel_events", []))
        m["min_true_ra_kN"] = ra.get("min_true_cyl_kN"); m["duration_s"] = ra.get("duration_s")
        m["reasons"] = [e.get("reason") for e in log if e["what"] == "hold"]
    out["x"] = m
    out.pop("reanchor", None); out.pop("tang", None)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True, choices=("F", "O", "O2", "O3", "S", "N", "L"))
    ap.add_argument("--series", action="store_true", help="store per-step 20 ms series of Fl / Ft (all legs)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.series:
        os.environ["H4CHK_SERIES"] = "1"     # inherited by the spawned workers
    import psutil
    pr = psutil.Process(); pr.cpu_affinity(P_CORES)      # P-cores 0-15; spawned workers inherit
    C = cases(a.part)
    print(f"cases {len(C)}, affinity {pr.cpu_affinity()}", flush=True)
    if a.dry_run:
        return
    t0 = time.perf_counter()
    fn = one_L if a.part == "L" else one
    r0 = fn(C[0])
    from multiprocessing import Pool
    with Pool(a.workers) as p:
        runs = [r0] + p.map(fn, C[1:], chunksize=1)
    res = {"meta": {"script": "04_scripts/03_control/run_h4_fs_order_check.py", "part": a.part, "n": len(C),
                    "wall_s": round(time.perf_counter() - t0, 1), "guard_kN": GUARD_KN, "F_min_N": F_MIN,
                    "R6_floor_N": R6_FLOOR_N, "parent_affinity": pr.cpu_affinity(), "workers": a.workers,
                    "errors": sum(1 for r in runs if "error" in r)}, "runs": runs}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"h4_fs_order_check_{a.part}.json"
    out_path.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(out_path, json.dumps(res["meta"]), flush=True)


if __name__ == "__main__":
    main()
