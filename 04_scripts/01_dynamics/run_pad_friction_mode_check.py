"""Pad friction decomposition option of the reduced plant (dynamics_model.md 3.15, rev. 26, user decision U20).

fric_mode 0 = original reduced plant (pad force F_l e_z + T, |T| <= mu F_l (a.n)); fric_mode 1 = Chrono L1 decomposition
(N along the floor normal, |T| <= mu N on the whole floor-plane force, rod axial load N (a.n) + T.e_z, rod lateral load
L = body-xy of N n + T). Option lives in run_control_comparison.physics / run_mast_flex_c2_check.physics_flex
(CONFIG['fric_mode']); default 0 is bit-identical to the code before rev. 26 (scratchpad regression).

Stages (each rewrites its own key of the output JSON):
  check    flat-floor equivalence (mode 1 vs 0) and stuck (mu 5) levelling-end forces vs the independent quasi-static
           model run_target_envelope.evaluate (Chrono-type decomposition, YAML k_t) on the D8 vertices
  g6       Chrono stage-2 G6 replica (top, rigid mast, pressure judge, H4 off / on with the adopted H4 P_stop
           staircase max(45/30/20/20, 20, F_min + F_band + 10 kN)), both modes, vs s6_stage2_check.json
  main     3.10.5 / 3.10.6 matrix in mode 1 (3 levels x 4 masts x 24 diamond points, delay 1, seed 12345)
  robust   top: delay 0 x 3 seeds, seeds 12346/12347, beta 0.69 / 1.6 GPa on the verification diamond, mode 1
  h4       adopted H4 on the fore-aft vertices (verification 3.5, provisional 3.2), rigid / stiff mast, YAML / secant
           k_t, both modes
  report   tables from the JSON (and the 3.10 mode-0 values from pad_tangential_check.json)

Run (project root):  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_pad_friction_mode_check.py --stage <s>
Output: 06_analysis/00_dynamics/pad_friction_mode_check.json
Frames: body x forward, y left, z up; roll + left up, pitch + nose down; forces in kN in outputs.
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import argparse  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "03_control"))
sys.path.insert(0, str(HERE.parent / "00_cad"))
import dyn_model as dm  # noqa: E402
import run_pad_tangential_check as rpt  # noqa: E402
import run_mast_flex_c2_check as rmf  # noqa: E402

ROOT = dm.PROJECT_ROOT
OUT = ROOT / "06_analysis/00_dynamics/pad_friction_mode_check.json"
PTC = ROOT / "06_analysis/00_dynamics/pad_tangential_check.json"
S2 = ROOT / "06_analysis/00_dynamics/s6_stage2_check.json"
LEGS = dm.LEG_NAMES
WORKERS = 12
F_MIN = float(dm.load_params()["control"]["F_min_cylinder_N"])  # YAML (rev. 30; was the literal 9452.55)
F_BAND = 13000.0
H4_SPEC = {"wait_s": 2.0, "speed_frac": 0.1, "hold_s": 1.0, "hold2_s": 1.0, "max_stroke_m": 0.008,
           "steps": ["RR", "RL", "RR", "RL"], "mode": "twist",
           "P_stop_N": [max(s, 20e3, F_MIN + F_BAND + 10e3) for s in (45e3, 30e3, 20e3, 20e3)]}


def case(cid, level, ang, mast="rigid", fmode=1, gainset=rpt.R1, seed=12345, mu=None, kt_mode="yaml", h4=False,
         beta=1.0e9, t_hold=None):
    c = rpt.mk(cid, "fm", level, f"X:{cid}", mast, gainset, seed=seed, mu=mu)
    c["angles"] = (float(ang[0]), float(ang[1]))
    c["cfg"]["fric_mode"] = int(fmode)
    c["beta"] = beta
    c["fmode"] = int(fmode)
    if kt_mode == "ext":
        lev = rpt.kin_internal(level, float(ang[0]), float(ang[1]), "ext")["levelled_ext_m"]
        c["rcfg"]["kt_per_pad"] = rpt.kt_of_ext(lev).tolist(); c["kt_mode"] = "ext"
    if h4:
        c["rcfg"]["reanchor"] = dict(H4_SPEC)
        c["t_hold"] = 60.0 if t_hold is None else t_hold
    elif t_hold is not None:
        c["t_hold"] = t_hold
    return c


def one(c):
    """run_one + identity check of the friction mode + Chrono-type pad metrics from the 1 ms record."""
    c = dict(c); c["keep_series"] = True
    fm = c.pop("fmode")
    out = rpt.run_one(c)
    if "error" in out:
        return out
    pl = rmf.LAST["plant"]
    if pl.fmode != fm or pl.case_id != c["id"]:
        raise RuntimeError(f"friction-mode identity check failed: plant {pl.fmode} vs case {fm}")
    ser = out.pop("_series")
    t, H, C = ser["t"], ser["H"], ser["C"]
    Fax = H[:, 0:4]; Lx = H[:, 17:21]; Ly = H[:, 21:25]; slip = H[:, 30:34]
    L = np.hypot(Lx, Ly)
    an = float(pl.nrm @ rmf.rcc._R(pl.q)[:, 2])
    if fm == 1:
        T = H[:, 34:38]; N = H[:, 38:42]
    else:
        T = L.copy(); N = Fax * an
    mu = pl.mu_pad
    ut = T / np.maximum(mu * N, 1.0)
    tr = out.get("t_ready_s")
    k = int(np.clip(np.searchsorted(t, (tr if tr is not None else t[-1]) - 1e-9), 0, len(t) - 1))
    ke = len(t) - 1
    tl = out.get("t_crawler_liftoff_s")
    kl = int(np.searchsorted(t, tl)) if tl is not None else 0
    m = {"fmode": fm, "a_dot_n_end": an}
    for lab, j in (("ready", k), ("end", ke)):
        m[lab] = {"L_kN": (L[j] / 1e3).round(2).tolist(), "T_kN": (T[j] / 1e3).round(2).tolist(),
                  "N_kN": (N[j] / 1e3).round(2).tolist(), "F_ax_kN": (Fax[j] / 1e3).round(2).tolist(),
                  "util": ut[j].round(4).tolist()}
    post = slice(kl, None)
    m["L_dyn_max_kN"] = (L[post].max(axis=0) / 1e3).round(2).tolist()
    m["slip_mm_total"] = (C[-1] * 1e3).round(3).tolist()
    m["slip_mm_after_ready"] = ((C[-1] - C[k]) * 1e3).round(3).tolist()
    m["slip_time_after_liftoff_s"] = (slip[post].sum(axis=0) * float(np.median(np.diff(t)))).round(3).tolist()
    out["fm"] = m
    out.pop("tang", None)
    return out


def pool(cases):
    t0 = time.perf_counter()
    r0 = one(cases[0])
    if len(cases) == 1:
        return [r0], round(time.perf_counter() - t0, 1)
    from multiprocessing import Pool
    with Pool(WORKERS) as p:
        rest = p.map(one, cases[1:], chunksize=1)
    return [r0] + rest, round(time.perf_counter() - t0, 1)


# ------------------------------------------------------------------------------------------------ stages
def stage_check():
    import run_target_envelope as rte
    C = []
    for fm in (0, 1):
        C.append(case(f"chk|flat|m{fm}", "top", (0.0, 0.0), fmode=fm))
    verts = [("V:pitch+3.5", (0.0, 3.5)), ("V:pitch-3.5", (0.0, -3.5)), ("V:roll+5.5", (5.5, 0.0))]
    for tag, ang in verts:
        C.append(case(f"chk|stick|{tag}", "top", ang, fmode=1, mu=5.0))
        C.append(case(f"chk|stick0|{tag}", "top", ang, fmode=0, mu=5.0))
    runs, wall = pool(C)
    R = {r["id"]: r for r in runs}
    out = {"wall_s": wall, "runs": runs}
    a, b = R["chk|flat|m0"], R["chk|flat|m1"]
    out["flat_equivalence"] = {"min_force_kN": [a["min_true_cyl_force_kN"], b["min_true_cyl_force_kN"]],
                               "t_ready_s": [a["t_ready_s"], b["t_ready_s"]],
                               "L_ready_kN": [a["fm"]["ready"]["L_kN"], b["fm"]["ready"]["L_kN"]],
                               "F_ax_ready_kN": [a["fm"]["ready"]["F_ax_kN"], b["fm"]["ready"]["F_ax_kN"]]}
    qs = {}
    for tag, ang in verts:
        e = rte.evaluate("top", ang[0], ang[1], 0.0, 0.0, kt_mode="yaml", cap=False)
        n = rte.floor_normal(*ang)
        Nn = e["N_N"]; Tm = e["T_N"]
        qs[tag] = {"envelope_stick_L_kN": (np.array(e["L_N"]) / 1e3).round(2).tolist(),
                   "envelope_stick_T_kN": (np.array(Tm) / 1e3).round(2).tolist(),
                   "envelope_N_kN": (np.array(Nn) / 1e3).round(2).tolist(),
                   "envelope_util_mu0.5": (np.array(Tm) / (0.5 * np.array(Nn))).round(4).tolist(),
                   "mode1_ready": R[f"chk|stick|{tag}"]["fm"]["ready"],
                   "mode0_ready": R[f"chk|stick0|{tag}"]["fm"]["ready"], "n": n.tolist()}
    out["stick_vs_envelope"] = qs
    return out


def stage_g6():
    C = []
    for fm in (0, 1):
        for fl, ang in (("fdown3.5", (0.0, 3.5)), ("fup3.5", (0.0, -3.5))):
            for h4 in (False, True):
                C.append(case(f"g6|{fl}|H4{'on' if h4 else 'off'}|m{fm}", "top", ang, fmode=fm, h4=h4,
                              t_hold=60.0 if h4 else None))
    runs, wall = pool(C)
    return {"wall_s": wall, "runs": runs, "h4_spec": H4_SPEC}


def stage_main():
    C = []
    pts = [(t, r_, p_) for t, r_, p_ in rpt.ALL_PTS]
    for lv in dm.LEVELS:
        for mast in rpt.MASTS:
            for tg, r_, p_ in pts:
                C.append(case(f"main|{lv}|{mast}|{tg}", lv, (r_, p_), mast))
    runs, wall = pool(C)
    return {"wall_s": wall, "runs": runs}


def stage_robust():
    C = []
    for mast in rpt.MASTS:
        for tg, r_, p_ in rpt.VER:
            for s in range(3):
                C.append(case(f"d0|{mast}|{tg}|{s}", "top", (r_, p_), mast, gainset=rpt.R1 + "_d0", seed=12345 + s))
            for s in (1, 2):
                C.append(case(f"seed|{mast}|{tg}|{s}", "top", (r_, p_), mast, seed=12345 + s))
            for b in (0.69e9, 1.6e9):
                C.append(case(f"beta|{mast}|{tg}|{b:g}", "top", (r_, p_), mast, beta=b))
    runs, wall = pool(C)
    return {"wall_s": wall, "runs": runs}


def stage_h4():
    C = []
    for tg, ang in (("V:pitch+3.5", (0.0, 3.5)), ("V:pitch-3.5", (0.0, -3.5)), ("P:pitch+3.2", (0.0, 3.2)),
                    ("P:pitch-3.2", (0.0, -3.2))):
        for mast in ("rigid", "stiff"):
            for km in ("yaml", "ext"):
                for fm in (0, 1):
                    for h4 in (False, True):
                        C.append(case(f"h4|{tg}|{mast}|{km}|m{fm}|{'on' if h4 else 'off'}", "top", ang, mast, fmode=fm,
                                      kt_mode=km, h4=h4, t_hold=60.0 if h4 else None))
    runs, wall = pool(C)
    return {"wall_s": wall, "runs": runs, "h4_spec": H4_SPEC}


# ------------------------------------------------------------------------------------------------ report
def _ok(r):
    return r.get("min_true_cyl_force_kN") is not None and r["min_true_cyl_force_kN"] >= (F_MIN + 5e3) / 1e3 \
        and not r.get("fails")


def report(d):
    if "check" in d:
        c = d["check"]
        print("== check: flat equivalence", c["flat_equivalence"])
        for tg, v in c["stick_vs_envelope"].items():
            print(f"  {tg}: env L {v['envelope_stick_L_kN']} T {v['envelope_stick_T_kN']} util {v['envelope_util_mu0.5']}")
            print(f"        m1  L {v['mode1_ready']['L_kN']} T {v['mode1_ready']['T_kN']} util0.5 "
                  f"{np.round(np.array(v['mode1_ready']['T_kN']) / (0.5 * np.array(v['mode1_ready']['N_kN'])), 4).tolist()}")
            print(f"        m0  L {v['mode0_ready']['L_kN']} T {v['mode0_ready']['T_kN']}")
    if "g6" in d:
        s2 = json.loads(S2.read_text(encoding="utf-8"))["friction"] if S2.exists() else {}
        print("== g6 (READY): L / T / util / slip after ready, vs Chrono")
        for r in d["g6"]["runs"]:
            if "fm" not in r:
                print(r.get("id"), r.get("error")); continue
            m = r["fm"]["end" if "H4on" in r["id"] else "ready"]
            print(f"  {r['id']:28s} minF {r['min_true_cyl_force_kN']:6.2f} L {m['L_kN']} T {m['T_kN']} util {m['util']} "
                  f"slip {r['fm']['slip_mm_total']}")
        for k in ("G6_top_fdown3.5_H4off", "G6_top_fdown3.5_H4on", "G6_top_fup3.5_H4off", "G6_top_fup3.5_H4on"):
            if k in s2:
                v = s2[k]["ready"]
                print(f"  CHRONO {k:24s} L {np.round(v['L_kN'], 2).tolist()} T {np.round(v['T_kN'], 2).tolist()} "
                      f"util {np.round(v['util'], 4).tolist()} slip_end {np.round(s2[k]['end']['slip_mm'], 2).tolist()}")
    for st in ("main", "robust", "h4"):
        if st not in d:
            continue
        runs = d[st]["runs"]
        errs = [r for r in runs if "error" in r]
        bad = [r for r in runs if "error" not in r and not _ok(r)]
        print(f"== {st}: n {len(runs)} errors {len(errs)} not passing {len(bad)} wall {d[st]['wall_s']} s")
        for r in bad[:20]:
            print("   FAIL", r["id"], r.get("min_true_cyl_force_kN"), r.get("fails"))
        good = [r for r in runs if "error" not in r]
        lo = sorted(good, key=lambda r: r["min_true_cyl_force_kN"])[:6]
        print("   lowest", [(r["id"], r["min_true_cyl_force_kN"]) for r in lo])


def compare_main(d):
    """mode 1 (this file) vs mode 0 (pad_tangential_check.json main) per point: min force, L ready / dyn max."""
    p0 = json.loads(PTC.read_text(encoding="utf-8"))
    base = {r["id"]: r for r in p0["main"]["runs"]} if isinstance(p0.get("main"), dict) else \
        {r["id"]: r for r in p0.get("main", [])}
    rows = []
    for r in d["main"]["runs"]:
        if "error" in r:
            continue
        k0 = r["id"]
        b = base.get(k0)
        if b is None:
            continue
        L1 = r["fm"]["ready"]["L_kN"]; T1 = r["fm"]["ready"]["T_kN"]; U1 = r["fm"]["ready"]["util"]
        L0 = b["tang"]["ready"]["Ft_kN"] if "ready" in b.get("tang", {}) else None
        rows.append({"id": k0, "minF0": b.get("min_true_cyl_force_kN"), "minF1": r["min_true_cyl_force_kN"],
                     "L0": L0, "L1": L1, "T1": T1, "util1": U1, "Ldyn1": r["fm"]["L_dyn_max_kN"],
                     "Ldyn0": b["tang"].get("dyn_max_kN") if "tang" in b else None})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["check", "g6", "main", "robust", "h4", "report"])
    a = ap.parse_args()
    d = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    fn = {"check": stage_check, "g6": stage_g6, "main": stage_main, "robust": stage_robust, "h4": stage_h4}
    if a.stage in fn:
        d[a.stage] = fn[a.stage]()
        if a.stage == "main":
            d["main_vs_mode0"] = compare_main(d)
        d["meta"] = {"script": "04_scripts/01_dynamics/run_pad_friction_mode_check.py", "h4_spec": H4_SPEC}
        OUT.write_text(json.dumps(d, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o)),
                       encoding="utf-8")
    report(d)


if __name__ == "__main__":
    main()
