"""Rev. 55: deferred-leg windows (C-S8-41 definition) recomputed from raw records, with
reference-batch comparison, below-F_min duration, lift, leg role and controller lower bound.

Independent of the judge: reads pads.npz / r8_series.npz / controller_events.json directly.
Windows: deferral .. same leg next leg_reapproach_start + 0.3 s; no restart -> several end
candidates (run end, deferral + T_o + 0.3 s, first return of the judged force >= 1.4 F_min).
"""
import json
import os
import re
import sys
import numpy as np

# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import os as _os
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s8" / "rev53_56" / "rev55"
OUT_DIR.mkdir(parents=True, exist_ok=True)
# ---
ROOT = str(REPO / r"07_results\S8")
C36 = ROOT + r"\c36_20261025_155317"
REF768 = ROOT + r"\ml_main_20261025_090131\episodes"
MLJ = ROOT + r"\mlj_20261025_080212"
LEGS = ["FL", "FR", "RL", "RR"]
DIAG = {"FL": "RR", "RR": "FL", "FR": "RL", "RL": "FR"}
TAIL = 0.3
T_O = 0.8
F_MIN = 9414.58911

CASES = [("A", c, os.path.join(C36, "A_rt", "episodes", c), os.path.join(REF768, c), 0.0)
         for c in ("ML00_ep5", "ML34_ep7", "ML78_ep0", "ML78_ep1", "ML78_ep3")]
CASES += [("D", "MLJ_FS24_Fs0", os.path.join(C36, "D_fs24", "MLJ_FS24_Fs0"),
           os.path.join(MLJ, "MLJ_FS24_Fs0"), 3.0)]
if len(sys.argv) > 1:
    # usage: c55_defer.py <ML episodes dir> [<ref episodes dir>] : every run with a deferral
    _b = sys.argv[1]
    _r = sys.argv[2] if len(sys.argv) > 2 else REF768
    CASES = [("X", c, os.path.join(_b, c), os.path.join(_r, c), 0.0) for c in sorted(os.listdir(_b))
             if os.path.isfile(os.path.join(_b, c, "controller_events.json"))
             and "leg_reapproach_deferred" in open(os.path.join(_b, c, "controller_events.json"),
                                                   encoding="utf-8").read()]


def events(path):
    out = []
    for s in json.load(open(os.path.join(path, "controller_events.json"), encoding="utf-8")):
        m = re.match(r"C2Event\(t_s=([-0-9.e]+), name='([^']*)'\)", s)
        if m:
            out.append((float(m.group(1)), m.group(2)))
    return out


def judged(p):
    j = p["F_cyl_min_interval"].astype(float).copy()
    air = p["airborne"].astype(bool)
    j[air] = p["F_cyl_mean_20ms"][air]
    return j


def load(path, rec_off):
    r = json.load(open(os.path.join(path, "result.json"), encoding="utf-8"))
    te = float(r["event_t_s"])
    p = np.load(os.path.join(path, "pads.npz"))
    t = p["t"] - (te + rec_off)
    s = np.load(os.path.join(path, "r8_series.npz"), allow_pickle=True)
    ts = s["t"] - (te + rec_off)
    ev = [(x - (te + rec_off), n) for x, n in events(path)]
    ep = (r.get("episode") or r.get("settings", {}).get("s8", {}).get("event_spec") or {})
    return dict(t=t, J=judged(p) / 1e3, raw=p["F_cyl_min_interval"] / 1e3, N=p["N_raw"] / 1e3,
                air=p["airborne"].astype(bool), ts=ts, Flo=s["F_lower_N"] / 1e3,
                Fest=s["F_lower_est_N"] / 1e3, u=s["cmp_reapproach_u"], ev=ev,
                leg=ep.get("leg"), dt=float(np.median(np.diff(p["t"]))))


def wstats(d, k, a, b):
    w = (d["t"] >= a - 1e-9) & (d["t"] <= b + 1e-9)
    if not w.any():
        return None
    J, t = d["J"][w, k], d["t"][w]
    i = int(np.argmin(J))
    below = float((J < F_MIN / 1e3).sum() * d["dt"])
    neg = float((d["N"][w, k] <= 0).sum() * d["dt"])
    air = float(d["air"][w, k].sum() * d["dt"])
    return dict(min=round(float(J[i]), 3), t_min=round(float(t[i]), 3), below_Fmin_s=round(below, 3),
                N0_s=round(neg, 3), air_s=round(air, 3))


out = {}
for grp, c, pa, pr, off in CASES:
    A = load(pa, off)
    R = load(pr, off)
    starts = [(x, n.split(":")[1]) for x, n in A["ev"] if n.startswith("leg_reapproach_start:") and x >= -1e-6]
    defs = [(x, n.split(":")[1]) for x, n in A["ev"] if n.startswith("leg_reapproach_deferred:") and x >= -1e-6]
    rstarts = [(round(x, 2), n.split(":")[1]) for x, n in R["ev"] if n.startswith("leg_reapproach_start:") and x >= -1e-6]
    rows = []
    for td, leg in defs:
        k = LEGS.index(leg)
        nxt = min((x for x, l in starts if l == leg and x > td + 1e-6), default=None)
        role = "event" if leg == A["leg"] else ("diagonal" if DIAG.get(A["leg"]) == leg else "adjacent")
        # controller lower bound at the deferral sample
        js = int(np.argmin(abs(A["ts"] - td)))
        f_at = float(A["J"][int(np.argmin(abs(A["t"] - td))), k])
        ends = {}
        if nxt is not None:
            ends["next+0.3"] = nxt + TAIL
        else:
            ends["run_end"] = float(A["t"][-1])
            ends["defer+T_o+0.3"] = td + T_O + TAIL
            after = (A["t"] > td) & (A["J"][:, k] >= 1.4 * F_MIN / 1e3)
            ends["recover_1.4Fmin"] = float(A["t"][after][0]) if after.any() else float(A["t"][-1])
        row = dict(leg=leg, role=role, deferred_s=round(td, 2), next_start_s=None if nxt is None else round(nxt, 2),
                   F_true_at_defer=round(f_at, 2), F_lower_ctrl_at_defer=round(float(A["Flo"][js, k]), 2),
                   F_lower_est_at_defer=round(float(A["Fest"][js, k]), 2), windows={})
        for name, b in ends.items():
            row["windows"][name] = dict(end=round(b, 3), A=wstats(A, k, td, b), ref=wstats(R, k, td, b))
        rows.append(row)
    # whole post-event leg minimum (0..3 s) for context: A and ref, all legs
    ctx = {}
    for k, leg in enumerate(LEGS):
        ctx[leg] = dict(A=wstats(A, k, 0.0, 4.0), ref=wstats(R, k, 0.0, 4.0))
    out[c] = dict(group=grp, event_leg=A["leg"], deferrals=rows,
                  starts=[(round(x, 2), l) for x, l in starts][:20], ref_starts=rstarts[:20], ctx_0_3s=ctx)

dst = os.environ.get("C55_DEFER_OUT") or os.path.join(str(OUT_DIR), "c55_defer.json")
json.dump(out, open(dst, "w", encoding="utf-8"), indent=1)
for c, v in out.items():
    print("==", c, "event leg", v["event_leg"], "starts", v["starts"])
    print("   ref starts", v["ref_starts"])
    for r in v["deferrals"]:
        print("  ", {k: r[k] for k in r if k != "windows"})
        for n, w in r["windows"].items():
            print("      ", n, w)
    for leg, x in v["ctx_0_3s"].items():
        print("   ctx 0-4 s", leg, "A", x["A"], "ref", x["ref"])
