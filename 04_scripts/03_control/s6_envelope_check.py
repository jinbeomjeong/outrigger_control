"""S6 control spec, static part: target acceptance rule A on the stored envelope maps.

Reads 06_analysis/00_dynamics/target_envelope.json (dynamics-expert, revision 21; not modified) and the YAML
geometry, and computes
  1. rule A (+ axis caps pitch 3 deg / roll 4 deg) acceptance per floor map, worst accepted motor stroke and
     its location, stroke left to the 680 mm end (path A: the full quasi-static envelope solution),
  2. the heave-target sensitivity ds_max / d(clearance) from the c50 / c20 / c0 maps inside the accepted set,
  3. a linear kinematic stroke predictor (path B, independent of the envelope solver):
        s_i' = s_i + dz + y_i dphi - x_i dtheta,  dz = 50 mm - min_c(clr_c + y_c dphi - x_c dtheta)
     starting from the levelled state on each floor (per-leg strokes of the stored (0, 0) point), compared to the
     envelope s_max over the accepted set and over the whole grid.
Conventions: body x fwd, y left, z up; roll > 0 left side up, pitch > 0 nose down; leg extension > 0;
floor plane z = -tan(theta_g) x + tan(phi_g) y. Units: m / rad inside, mm / deg in the output.

Run: conda run -n dynamics-dev python -I s6_envelope_check.py <project_root> <out_json>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(sys.argv[1])
OUT = Path(sys.argv[2])
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402

DEG = math.pi / 180.0
FLOORS = {
    "flat": (0.0, 0.0),
    "P:pitch+3.2": (0.0, 3.2), "P:pitch-3.2": (0.0, -3.2), "P:roll+4.4": (4.4, 0.0), "P:roll-4.4": (-4.4, 0.0),
    "P:diag++": (2.2, 1.6), "P:diag+-": (2.2, -1.6), "P:diag-+": (-2.2, 1.6), "P:diag--": (-2.2, -1.6),
    "V:pitch+3.5": (0.0, 3.5), "V:pitch-3.5": (0.0, -3.5), "V:roll+5.5": (5.5, 0.0), "V:roll-5.5": (-5.5, 0.0),
}
PHI_R, THETA_R = 4.4, 3.2          # rule A diamond half-axes [deg]
CAP_PITCH, CAP_ROLL = 3.0, 4.0     # axis caps (user decision 2026-10-21) [deg]
S_END = 0.68
CLR_TARGET = 0.05


def rule_a(phi_t, th_t, phi_g, th_g, caps=True):
    rel = np.abs(phi_t - phi_g) / PHI_R + np.abs(th_t - th_g) / THETA_R <= 1.0 + 1e-9
    ab = np.abs(phi_t) / PHI_R + np.abs(th_t) / THETA_R <= 1.0 + 1e-9
    ok = rel & ab
    if caps:
        ok &= (np.abs(th_t) <= CAP_PITCH + 1e-9) & (np.abs(phi_t) <= CAP_ROLL + 1e-9)
    return ok


def main():
    d = json.load(open(ROOT / "06_analysis" / "00_dynamics" / "target_envelope.json"))
    roll = np.array(d["meta"]["grid_roll_deg"]); pitch = np.array(d["meta"]["grid_pitch_deg"])
    R, P = np.meshgrid(roll, pitch)                      # maps are [pitch, roll]
    geo = dm.geometry_from_params(dm.load_params())
    xy = geo.pad_xy
    (x0, x1), (y0, y1) = geo.crawler_xy_box
    corners = np.array([[x0, y0], [x0, y1], [x1, y0], [x1, y1]])
    out = {"meta": {"source": "06_analysis/00_dynamics/target_envelope.json (read only)",
                    "rule": f"|phi_t-phi_g|/{PHI_R}+|theta_t-theta_g|/{THETA_R}<=1 and |phi_t|/{PHI_R}+|theta_t|/{THETA_R}"
                            f"<=1, caps |theta_t|<={CAP_PITCH}, |phi_t|<={CAP_ROLL} deg",
                    "pad_xy_m": xy.tolist(), "crawler_box_m": [list(geo.crawler_xy_box[0]), list(geo.crawler_xy_box[1])]},
           "floors": {}}
    worst = {"s_mm": -1}
    pred_err_acc = []; pred_err_all = []
    for key, m in d["maps"].items():
        lvl, fk = key.split("|", 1)
        rg, pg = FLOORS[fk]
        s50 = np.array(m["s_max_c50_m"]); s20 = np.array(m["s_max_c20_m"]); s0 = np.array(m["s_max_c0_m"])
        Fmin = np.array(m["F_cyl_min_N"])
        ok_nocap = rule_a(R, P, rg, pg, caps=False)
        ok = rule_a(R, P, rg, pg, caps=True)
        rec = {"floor_deg": [rg, pg], "accepted_points": int(ok.sum()), "accepted_points_nocap": int(ok_nocap.sum())}
        if ok.any():
            j = np.unravel_index(np.argmax(np.where(ok, s50, -1)), s50.shape)
            rec["worst_s_max_mm"] = round(float(s50[j]) * 1e3, 2)
            rec["worst_target_deg"] = [float(R[j]), float(P[j])]
            rec["left_to_end_mm"] = round((S_END - float(s50[j])) * 1e3, 2)
            rec["min_F_cyl_kN_accepted"] = round(float(Fmin[ok].min()) / 1e3, 2)
            ds = (s50 - s20)[ok] * 1e3 / 30.0
            ds0 = (s50 - s0)[ok] * 1e3 / 50.0
            rec["ds_dclr_c50_c20"] = [round(float(ds.min()), 4), round(float(ds.max()), 4)]
            rec["ds_dclr_c50_c0"] = [round(float(ds0.min()), 4), round(float(ds0.max()), 4)]
            if float(s50[j]) * 1e3 > worst["s_mm"]:
                worst = {"s_mm": round(float(s50[j]) * 1e3, 2), "map": key, "target_deg": [float(R[j]), float(P[j])]}
        # ---- path B: linear predictor from the levelled state (target 0, 0) on this floor
        base = d["user_box_points"].get(key, {}).get("+0.00,+0.00")
        if base is not None:
            s_base = np.array(base["s_motor_mm"]) / 1e3
            # corner clearances at the levelled state: deck level, min corner = 50 mm
            zf = -math.tan(pg * DEG) * corners[:, 0] + math.tan(rg * DEG) * corners[:, 1]
            clr = CLR_TARGET + (zf.max() - zf)
            dphi = (R - 0.0) * DEG; dth = (P - 0.0) * DEG
            c_new = clr[None, None, :] + corners[:, 1] * dphi[..., None] - corners[:, 0] * dth[..., None]
            dz = CLR_TARGET - c_new.min(axis=-1)
            s_new = s_base[None, None, :] + dz[..., None] + xy[:, 1] * dphi[..., None] - xy[:, 0] * dth[..., None]
            s_pred = s_new.max(axis=-1)
            err = (s_pred - s50) * 1e3
            rec["predictor_err_mm_accepted"] = [round(float(err[ok].min()), 2), round(float(err[ok].max()), 2)] if ok.any() else None
            box = (np.abs(R) <= 6.0) & (np.abs(P) <= 4.0)
            rec["predictor_err_mm_box6x4"] = [round(float(err[box].min()), 2), round(float(err[box].max()), 2)]
            near = ok & (s50 > 0.60)
            rec["predictor_err_mm_accepted_s>600"] = ([round(float(err[near].min()), 2), round(float(err[near].max()), 2)]
                                                     if near.any() else None)
            if ok.any():
                pred_err_acc.append(err[ok])
            pred_err_all.append(err[box])
        out["floors"][key] = rec
    out["worst_accepted"] = worst
    ea = np.concatenate(pred_err_acc); eb = np.concatenate(pred_err_all)
    out["predictor_summary"] = {
        "accepted_err_mm": {"min": round(float(ea.min()), 2), "max": round(float(ea.max()), 2),
                            "p1": round(float(np.percentile(ea, 1)), 2), "p99": round(float(np.percentile(ea, 99)), 2)},
        "box6x4_err_mm": {"min": round(float(eb.min()), 2), "max": round(float(eb.max()), 2)},
        "note": "err = linear predictor - envelope s_max(c50); positive = conservative",
    }
    # stroke left at the worst accepted point for heave targets other than 50 mm (slope ds/dclr ~ 1)
    acc = [r["ds_dclr_c50_c20"] for r in out["floors"].values() if "ds_dclr_c50_c20" in r]
    out["heave_target_rule"] = {
        "ds_dclr_range": [min(a[0] for a in acc), max(a[1] for a in acc)],
        "max_clearance_target_mm_for_10mm_margin": round(50 + (S_END * 1e3 - 10 - worst["s_mm"]) / max(a[1] for a in acc), 1),
        "max_clearance_target_mm_for_0mm_margin": round(50 + (S_END * 1e3 - worst["s_mm"]) / max(a[1] for a in acc), 1),
    }
    OUT.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("worst_accepted", "predictor_summary", "heave_target_rule")}, indent=1))
    for k, r in out["floors"].items():
        print(k, r.get("accepted_points"), r.get("worst_s_max_mm"), r.get("worst_target_deg"), r.get("left_to_end_mm"),
              r.get("predictor_err_mm_accepted"), r.get("predictor_err_mm_accepted_s>600"), r.get("ds_dclr_c50_c20"))


if __name__ == "__main__":
    main()
