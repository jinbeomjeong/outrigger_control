"""Post-hoc SCM grid-phase reconstruction of stored S9 level rows (no dynamics run, read-only).

For each case folder (``run_S9.py level`` result: ``result.json`` + ``record/record.npz``) and each pad,
at the times LOC (P3-2 ``t_loc_s``), first READY (P3-5), t_max (max reading stroke over the legs after
LOC), the run end and, when present, the first stroke-guard / SGS event:

* recorded SCM node state of the pad (``s9_rows[k].pad_nodes[i]``, 10 Hz, live ``node_stats_in_outline``):
  contact nodes ``N_h``, hull area / perimeter -> ``b_hull = 2 A_h / P_h``; geometric sinkage ``z``
  (``s9_rows[k].pad_sinkage_geometric_m``, + = deeper);
* grid factor (terramechanics review 2026-11-10)
  ``f = [N_h d^2 (Kc/b_hull + Kphi) / (A (Kc/b_poly + Kphi))]^(-1/n)``, A = ``bottom_area_m2`` and
  b_poly = ``bekker_b_m`` of ``02_params/pad_variants.json``; grid share ``delta = z (1 - 1/f)``
  (z / f = continuum-equivalent sinkage at the same load; SCM sigma = (Kc/b + Kphi) z^n with node area d^2,
  SCMTerrain.cpp patch b = 2A/L, vehicle_terrain.md:94);
* phase band: the pad bottom outline is placed in the SCM plane frame from the recorded body pose and
  motor extension (ball centre = body_pos + R pad_sphere_centre_body_m(s_motor), projected on the plane,
  pad parallel to the plane with the start yaw; ASSUMPTION: pad tilt and yaw drift neglected). The
  reconstruction is checked against the recorded ``n_inside``. The outline is then shifted over a
  ``--phases`` x ``--phases`` grid of offsets in [0, d)^2, giving f' and the alternative sinkage
  ``z' = (z / f) f'``;
* first-order effect on the reading stroke (body pose held by the controller: each leg absorbs its own
  pad sinkage along the leg axis): ``ds = dz / cos(alpha)``, alpha = angle between the leg axis and the
  plane normal. Guard margin ``g = s_guard - max_i s_i(t_max)`` (reading stroke ``meas.stroke``,
  s_guard 0.6828 m): continuum ``g_c = g + delta_i* / cos``; phase band ``g' = g - (z'_i* - z_i*) / cos``
  (i* = leg of the max). For guard-limited rows the clearance takes the change instead:
  ``dc ~ -(mean_i dz_i)`` (heave only, indication).

Units SI (m, N, s); lengths printed in mm. Last stdout line = JSON summary; ``--out`` = full JSON.
Exit 0 ok, 2 input error.

Run (Chrono-dev, imports outrigger_sim; OUTRIGGER_HULL_HOOK forced off, no SCM step is taken):
    python -I 04_scripts/02_chrono/b1_grid_conv/grid_phase_recon.py <case_dir> [...] [--phases 24] [--out x.json]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

os.environ["OUTRIGGER_HULL_HOOK"] = "off"  # geometry only; never load the DLL here
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "03_src"))

S_GUARD_M = 0.6828
GUARD_EVENT_KEYS = ("STROKE_LIMIT", "LIFT_STROKE", "SGS", "STROKE_END")


def quat_to_mat(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def hull_b(pts, convex_hull_2d):
    h = pts[convex_hull_2d(pts)]
    hn = np.roll(h, -1, axis=0)
    area = 0.5 * abs(np.sum(h[:, 0] * hn[:, 1] - hn[:, 0] * h[:, 1]))
    per = float(np.sum(np.hypot(*(hn - h).T)))
    return 2.0 * area / per


def factor(n_h, d, b_hull, area, b_poly, soil):
    kh = soil["Kc"] / b_hull + soil["Kphi"]
    kp = soil["Kc"] / b_poly + soil["Kphi"]
    return ((n_h * d * d * kh) / (area * kp)) ** (-1.0 / soil["n"])


def analyse(case: Path, n_phase: int) -> dict:
    from outrigger_sim.chrono.scm_model import (
        convex_hull_2d, inside_convex_polygon, pad_bottom_outline_local_m, plane_frame)
    from outrigger_sim.geometry import extension_direction, pad_sphere_centre_body_m
    from outrigger_sim.pad_variants import apply_pad_variant
    from outrigger_sim.params import LEG_ORDER, load_params
    from outrigger_sim.scenarios.slope import floor_normal

    rp = case / "result.json"
    if not rp.is_file():
        raise SystemExit(f"missing {rp}")
    r = json.loads(rp.read_text(encoding="utf-8"))
    a = r["args"]
    d = float(a["grid"])
    params = apply_pad_variant(load_params(level=a["level"], model="L2b_NSC"), a["pad_variant"])
    roll, pitch = float(a.get("floor_roll") or 0.0), float(a.get("floor_pitch") or 0.0)
    normal = None if (roll == 0.0 and pitch == 0.0) else floor_normal(roll, pitch)
    p0, rpl = plane_frame(params, normal)
    nrm = rpl[:, 2]
    soil = json.loads((ROOT / "02_params" / "scm_soil_sets.json").read_text(encoding="utf-8"))
    soil = soil["sets"][a["soil"]]["chrono"]
    pv = json.loads((ROOT / "02_params" / "pad_variants.json").read_text(encoding="utf-8"))
    legs_pv = pv["variants"][a["pad_variant"]]["legs"]
    rows = r["s9_rows"]
    t_rows = np.array([row["t_s"] for row in rows])
    rec = np.load(case / "record" / "record.npz")
    t_rec = rec["t"]
    stroke = rec["meas.stroke"]
    p3 = r["p3b"]
    t_loc = p3["P3-2_loc"].get("t_loc_s")
    t_ready = p3["P3-5_clearance_stroke"].get("t_first_ready_s")
    after = t_rec >= (t_loc if t_loc is not None else 0.0)
    smax_leg = stroke.max(axis=1)
    k_max = int(np.flatnonzero(after)[np.argmax(smax_leg[after])])
    t_max = float(t_rec[k_max])
    guard = [e for e in r.get("events", []) if any(s in str(e.get("name", "")) for s in GUARD_EVENT_KEYS)]
    times = {"t_L": t_loc, "t_ready": t_ready, "t_max": t_max, "t_end": float(t_rows[-1])}
    if guard:
        times["t_guard"] = float(guard[0]["t_s"])
    direction = extension_direction(params)
    outlines_body = [pad_bottom_outline_local_m(a["pad_variant"], i, np.zeros(3))[:, :2] for i in range(4)]
    centres_body = [np.asarray(params.legs[i].pad_bottom_center_retracted_m, float) for i in range(4)]
    offs = [(ox, oy) for ox in np.arange(n_phase) * d / n_phase for oy in np.arange(n_phase) * d / n_phase]
    out = {"case": case.name, "folder": str(case), "soil": a["soil"], "level": a["level"], "grid_m": d,
           "floor_roll_deg": roll, "floor_pitch_deg": pitch, "mass_scale": a.get("mass_scale"),
           "soil_n": soil["n"], "times_s": times, "guard_events": guard[:5], "s_guard_m": S_GUARD_M,
           "pads": {}, "at": {}}
    for i, leg in enumerate(LEG_ORDER):
        out["pads"][leg] = {"A_poly_m2": legs_pv[leg]["bottom_area_m2"], "b_poly_m": legs_pv[leg]["bekker_b_m"]}
    for name, tt in times.items():
        if tt is None:
            continue
        kr = int(np.argmin(np.abs(t_rows - tt)))
        kc = int(np.argmin(np.abs(t_rec - tt)))
        row = rows[kr]
        R = quat_to_mat(rec["body_quat_wxyz"][kc])
        body = rec["body_pos"][kc]
        s_mot = rec["s_motor"][kc]
        s_read = stroke[kc]
        per = {}
        for i, leg in enumerate(LEG_ORDER):
            nd = row["pad_nodes"][i]
            z = float(row["pad_sinkage_geometric_m"][i])
            A, bp = legs_pv[leg]["bottom_area_m2"], legs_pv[leg]["bekker_b_m"]
            leg_w = R @ direction
            cosa = abs(float(leg_w @ nrm))
            item = {"z_m": z, "n_contact": nd["n_contact"], "n_inside_rec": nd["n_inside"],
                    "reading_stroke_m": float(s_read[i]), "cos_leg_normal": cosa}
            if nd["n_contact"] >= 3 and nd.get("contact_hull_area_m2"):
                bh = 2.0 * nd["contact_hull_area_m2"] / nd["contact_hull_perimeter_m"]
                f = factor(nd["n_contact"], d, bh, A, bp, soil)
                item.update(b_hull_m=bh, A_eff_over_A=nd["n_contact"] * d * d / A, f=f, delta_grid_m=z * (1 - 1 / f),
                            z_cont_m=z / f)
                # kinematic outline in plane coordinates
                ball = body + R @ pad_sphere_centre_body_m(params, i, float(s_mot[i]))
                q = rpl.T @ (ball - p0)
                poly = q[:2] + (outlines_body[i] - centres_body[i][:2])
                poly = poly[convex_hull_2d(poly)]
                lo, hi = poly.min(axis=0), poly.max(axis=0)

                def count(shift, poly=poly, lo=lo, hi=hi):
                    pp = poly + shift
                    i0, i1 = math.floor((lo[0] + shift[0]) / d) - 1, math.ceil((hi[0] + shift[0]) / d) + 1
                    j0, j1 = math.floor((lo[1] + shift[1]) / d) - 1, math.ceil((hi[1] + shift[1]) / d) + 1
                    ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1), indexing="ij")
                    nodes = np.column_stack([ii.ravel() * d, jj.ravel() * d])
                    nodes = nodes[inside_convex_polygon(pp, nodes)]
                    return len(nodes), hull_b(nodes, convex_hull_2d)

                n0, b0 = count(np.zeros(2))
                item.update(n_inside_kinematic=n0, b_hull_kinematic_m=b0,
                            kinematic_matches_record=bool(n0 == nd["n_inside"]))
                fs = np.array([factor(nn, d, bb, A, bp, soil) for nn, bb in (count(np.array(o)) for o in offs)])
                # with the recorded node set as the reference phase
                zc = z / f
                zp = zc * fs
                item.update(f_phase_min=float(fs.min()), f_phase_max=float(fs.max()),
                            f_phase_mean=float(fs.mean()), f_phase_sd=float(fs.std()),
                            z_phase_min_m=float(zp.min()), z_phase_max_m=float(zp.max()),
                            dz_phase_min_m=float(zp.min() - z), dz_phase_max_m=float(zp.max() - z))
            per[leg] = item
        entry = {"t_s": float(t_rows[kr]), "t_record_s": float(t_rec[kc]), "c2_phase": row.get("c2_phase"),
                 "rut_clearance_m": row.get("rut_clearance_m"), "pads": per}
        if name == "t_max":
            i_star = int(np.argmax(s_read))
            g = S_GUARD_M - float(s_read[i_star])
            it = per[LEG_ORDER[i_star]]
            entry["guard"] = {"leg": LEG_ORDER[i_star], "g_m": g}
            if "f" in it:
                c = it["cos_leg_normal"]
                entry["guard"].update(g_continuum_m=g + it["delta_grid_m"] / c,
                                      g_phase_min_m=g - it["dz_phase_max_m"] / c,
                                      g_phase_max_m=g - it["dz_phase_min_m"] / c)
            # other legs: margin per leg under the phase band (another leg can become the max)
            g_all = []
            for j, lg in enumerate(LEG_ORDER):
                pj = per[lg]
                if "f" in pj:
                    gj = S_GUARD_M - float(s_read[j])
                    g_all.append({"leg": lg, "g_m": gj, "g_phase_min_m": gj - pj["dz_phase_max_m"] / pj["cos_leg_normal"],
                                  "g_continuum_m": gj + pj["delta_grid_m"] / pj["cos_leg_normal"]})
            entry["guard_all_legs"] = g_all
            if g_all:
                entry["guard"]["g_phase_min_any_leg_m"] = min(x["g_phase_min_m"] for x in g_all)
                entry["guard"]["g_continuum_min_any_leg_m"] = min(x["g_continuum_m"] for x in g_all)
        if name == "t_guard" or name == "t_end":
            ds = [per[lg]["dz_phase_min_m"] for lg in LEG_ORDER if "f" in per[lg]]
            dl = [per[lg]["dz_phase_max_m"] for lg in LEG_ORDER if "f" in per[lg]]
            dg = [per[lg]["delta_grid_m"] for lg in LEG_ORDER if "f" in per[lg]]
            if ds:
                entry["clearance_if_strokes_fixed"] = {
                    "dc_continuum_m": float(np.mean(dg)), "dc_phase_min_m": -float(np.mean(dl)),
                    "dc_phase_max_m": -float(np.mean(ds)), "note": "heave only, indication"}
        out["at"][name] = entry
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cases", nargs="+", type=Path)
    ap.add_argument("--phases", type=int, default=24)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    res = [analyse(c, a.phases) for c in a.cases]
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    for c in res:
        print(f"== {c['case']}  {c['soil']} n={c['soil_n']} grid {c['grid_m']} roll {c['floor_roll_deg']} "
              f"pitch {c['floor_pitch_deg']} times {json.dumps({k: (None if v is None else round(v, 1)) for k, v in c['times_s'].items()})}")
        for name, e in c["at"].items():
            cells = []
            for lg, p in e["pads"].items():
                if "f" in p:
                    cells.append(f"{lg} N{p['n_contact']}{'' if p['kinematic_matches_record'] else '*' + str(p['n_inside_kinematic'])} "
                                 f"z{p['z_m']*1e3:6.1f} f-1 {p['f']-1:+.4f} d{p['delta_grid_m']*1e3:+5.1f} "
                                 f"[{p['dz_phase_min_m']*1e3:+5.1f},{p['dz_phase_max_m']*1e3:+5.1f}]")
                else:
                    cells.append(f"{lg} N{p['n_contact']} (no contact)")
            print(f"  {name:8s} t={e['t_s']:6.1f} " + " | ".join(cells))
            if "guard" in e:
                g = e["guard"]
                print(f"           guard leg {g['leg']} g {g['g_m']*1e3:.2f} mm, continuum {g.get('g_continuum_m', float('nan'))*1e3:.2f}, "
                      f"phase [{g.get('g_phase_min_m', float('nan'))*1e3:.2f}, {g.get('g_phase_max_m', float('nan'))*1e3:.2f}] mm, "
                      f"min any leg phase {g.get('g_phase_min_any_leg_m', float('nan'))*1e3:.2f} / continuum "
                      f"{g.get('g_continuum_min_any_leg_m', float('nan'))*1e3:.2f} mm")
            if "clearance_if_strokes_fixed" in e:
                cc = e["clearance_if_strokes_fixed"]
                print(f"           clearance (strokes fixed) continuum {cc['dc_continuum_m']*1e3:+.1f}, phase "
                      f"[{cc['dc_phase_min_m']*1e3:+.1f}, {cc['dc_phase_max_m']*1e3:+.1f}] mm; rut clearance "
                      f"{(e['rut_clearance_m'] or float('nan'))*1e3:.1f} mm")
    print(json.dumps({"n_cases": len(res), "kinematic_all_match": all(
        p.get("kinematic_matches_record", True) for c in res for e in c["at"].values() for p in e["pads"].values())}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
