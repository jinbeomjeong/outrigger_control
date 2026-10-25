"""D-S8-5 (2): does the lost H4 relief at F_s 8 kN change the nose-down 3.2 deg rod judgement?

Reads S8 p1r records (L2b-NSC, top, combined contact; Chrono not re-run) and, per case and leg:
  levelling end (0.5 s mean before the first DONE), H4 window (reanchor_started ..
  reanchor_completed) 1 ms Pareto front of (L, F_cyl), READY (mean from READY + 1 s to the end),
  pad utilisation max in the H4 window and READY, then the rod-yield SF of each candidate with the
  same beam model as dynamics_model.md 5.19 (04_scripts/00_cad/leg_rod_lateral_check.py,
  imported unmodified: allowable_lateral, swivel load point, axial P = max(F_cyl, N_pad static)),
  extension e = s_motor (Chrono e).
L = pad horizontal reaction (20 ms mean of the NSC contact force, world xy; deck level at the end
of levelling, 5.19 convention), F_cyl = rod axial force (+ = pushes the pad down), kN.
Usage: python -I ds85_h4_sf.py <out json> <case dir> [<case dir> ...]
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, r"C:\workspace\outrigger_control\04_scripts\00_cad")
import leg_rod_lateral_check as lr  # noqa: E402

LEGS = ("FL", "FR", "RL", "RR")
p = lr.load_params()
geo = lr.leg_geometry(p)
g0 = float(p["meta"]["gravity_m_s2"])
W_rod = np.array([float(p["legs"][n]["moving_part"]["mass_kg"]) * g0 for n in LEGS])
Npad = lr.static_cylinder_forces_kn(p) + W_rod
SY = lr.ASSUMPTIONS["rod_yield_Pa"]
SF_REQ = lr.ASSUMPTIONS["required_yield_safety_factor"]
cache = {}


def sf(leg, e, L_N, P_N, mat):
    P = max(P_N, Npad[leg])
    key = (leg, round(e, 4), round(P, -2), mat)
    if key not in cache:
        cache[key] = lr.allowable_lateral(geo[LEGS[leg]], p, round(e, 4), round(P, -2), "swivel", SY[mat], SF_REQ)
    return SF_REQ * cache[key] / L_N if L_N > 0 else float("inf")


def pareto(L, F):
    order = np.lexsort((-F, -L))  # L descending, then F descending
    front, best_F = [], -np.inf
    for k in order:
        if F[k] > best_F:
            front.append(k)
            best_F = F[k]
    return np.array(front, dtype=int)


def analyse(d):
    with open(os.path.join(d, "result.json"), encoding="utf-8") as fh:
        res = json.load(fh)
    with open(os.path.join(d, "controller_events.json"), encoding="utf-8") as fh:
        ev = json.load(fh)
    off = float(res["settings"]["start_t_s"])
    phases = [(float(t) + off, name) for t, name in res["phases"]]
    t_done = next(t for t, n in phases if n == "done")
    t_ready = next((t for t, n in phases if n == "ready"), None)
    t_rs = t_rc = None
    for e in ev:
        t = float(e.split("t_s=")[1].split(",")[0])
        if "reanchor_started" in e:
            t_rs = t
        if "reanchor_completed" in e:
            t_rc = t
    pads = np.load(os.path.join(d, "pads.npz"))
    t = pads["t"]
    L = pads["L"] / 1e3
    F = pads["F_cyl"] / 1e3
    s = pads["s_motor"]
    util = pads["utilisation"]
    out = {"case": os.path.basename(d), "t_done": t_done, "t_ready": t_ready, "h4_window": [t_rs, t_rc],
           "h4": res.get("h4", {}).get("outcome"), "legs": {}}
    m_end = (t >= t_done - 0.5) & (t <= t_done)
    m_h4 = (t >= t_rs) & (t <= t_rc) if t_rs else np.zeros_like(t, bool)
    m_rdy = (t >= t_ready + 1.0) if t_ready else np.zeros_like(t, bool)
    for j, g in enumerate(LEGS):
        rec = {}
        for mat in SY:
            le = sf(j, float(s[m_end, j].mean()), L[m_end, j].mean() * 1e3, F[m_end, j].mean() * 1e3, mat)
            rec[f"SF_levelling_end_{mat}"] = le
            if m_h4.any():
                k = np.flatnonzero(m_h4)
                fr = k[pareto(L[k, j], F[k, j])]
                vals = [(sf(j, float(s[i, j]), L[i, j] * 1e3, F[i, j] * 1e3, mat), float(t[i]), float(L[i, j]), float(F[i, j]))
                        for i in fr]
                w = min(vals)
                rec[f"SF_h4_min_{mat}"] = w[0]
                rec[f"h4_governing_{mat}"] = {"t": w[1], "L_kN": w[2], "F_kN": w[3]}
            if m_rdy.any():
                rec[f"SF_ready_{mat}"] = sf(j, float(s[m_rdy, j].mean()), L[m_rdy, j].mean() * 1e3,
                                            F[m_rdy, j].mean() * 1e3, mat)
        rec.update({
            "L_end_kN": float(L[m_end, j].mean()), "F_end_kN": float(F[m_end, j].mean()),
            "L_h4_max_kN": float(L[m_h4, j].max()) if m_h4.any() else None,
            "util_h4_max": float(util[m_h4, j].max()) if m_h4.any() else None,
            "L_ready_kN": float(L[m_rdy, j].mean()) if m_rdy.any() else None,
            "F_ready_kN": float(F[m_rdy, j].mean()) if m_rdy.any() else None,
            "L_ready_max_kN": float(L[m_rdy, j].max()) if m_rdy.any() else None,
            "util_ready_max": float(util[m_rdy, j].max()) if m_rdy.any() else None,
            "s_end_m": float(s[m_end, j].mean()),
        })
        out["legs"][g] = rec
    return out


def main():
    rep = {"rod_yield_Pa": SY, "SF_req": SF_REQ, "N_pad_static_N": Npad.tolist(), "cases": []}
    for d in sys.argv[2:]:
        o = analyse(d)
        rep["cases"].append(o)
        print(f"== {o['case']}  DONE {o['t_done']:.1f} H4 {o['h4']} {o['h4_window']} READY {o['t_ready']}")
        for g, r in o["legs"].items():
            parts = [f"{g}: L end {r['L_end_kN']:.2f}@{r['F_end_kN']:.1f}"]
            if r["L_h4_max_kN"] is not None:
                parts.append(f"H4 Lmax {r['L_h4_max_kN']:.2f} util {r['util_h4_max']:.2f}")
            if r["L_ready_kN"] is not None:
                parts.append(f"READY L {r['L_ready_kN']:.2f} (max {r['L_ready_max_kN']:.2f}) @ {r['F_ready_kN']:.1f} util {r['util_ready_max']:.2f}")
            for mat in SY:
                sfs = [f"end {r[f'SF_levelling_end_{mat}']:.3f}"]
                if f"SF_h4_min_{mat}" in r:
                    gv = r[f"h4_governing_{mat}"]
                    sfs.append(f"H4 {r[f'SF_h4_min_{mat}']:.3f} ({gv['L_kN']:.2f}@{gv['F_kN']:.1f} t {gv['t']:.2f})")
                if f"SF_ready_{mat}" in r:
                    sfs.append(f"READY {r[f'SF_ready_{mat}']:.3f}")
                parts.append(f"[{mat}] " + " ".join(sfs))
            print("  " + " | ".join(parts))
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    print("wrote", sys.argv[1])


if __name__ == "__main__":
    main()
