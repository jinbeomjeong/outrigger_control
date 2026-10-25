"""Aggregate cyl35 jobs -> 01_cad/02_legs/rexome35/rexome35_cylinder_mass_properties.json (+ csv, cache meta),
judge the verification criteria and print a summary."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
# Moved from the 2026-10-22 cad scratchpad (cad-run/cyl35/) on 2026-10-25: project root from the
# script location; job results read from 01_cad/02_legs/rexome35/jobs/ (cyl35_run.py output).
PROJECT = Path(__file__).resolve().parents[3]
CACHE = PROJECT / "01_cad" / "02_legs" / "rexome35"
JOBS_DIR = CACHE / "jobs"
Y = yaml.safe_load(open(PROJECT / "02_params" / "rexome33.yaml", encoding="utf-8"))
J = json.loads((JOBS_DIR / "all_jobs.json").read_text(encoding="utf-8"))["jobs"]
G = 9.80665


def sha(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def rel(p) -> str:
    try:
        return Path(p).resolve().relative_to(PROJECT).as_posix()
    except ValueError:
        return str(p)


checks = {}


def check(name, ok, value):
    checks[name] = {"ok": bool(ok), "value": value}


def judge_part(job, d):
    w = d["whole"]
    check(f"{job}.valid", w["valid"], w["solids"])
    check(f"{job}.tensor_pd_triangle", w["tensor"]["positive_definite"] and w["tensor"]["triangle_ok"],
          w["tensor"]["principal_kg_m2"])
    check(f"{job}.com_inside_bbox", w["com_inside_bbox"], w["com_m"])
    mc = d["mesh_check"]
    check(f"{job}.mesh_volume_rel<=1e-3", abs(mc["volume_rel"]) <= 1e-3, mc["volume_rel"])
    check(f"{job}.brep_read_back_rel<=1e-9", abs(d["brep"]["read_back_volume_rel"]) <= 1e-9, d["brep"]["read_back_volume_rel"])
    if "splits" in d:
        for k, s in d["splits"].items():
            r = s["recombined_vs_whole"]
            check(f"{job}.split_{k}_recombine<=1e-9", max(abs(r["mass_rel"]), r["inertia_frobenius_rel"]) <= 1e-9, r)
    if "delta_mass_kg" in d:
        rr = d["delta_mass_kg"] / d["delta_mass_analytic_kg"] - 1
        check(f"{job}.ring_delta_vs_analytic<=1e-6", abs(rr) <= 1e-6, [d["delta_mass_kg"], d["delta_mass_analytic_kg"]])


for job, d in J.items():
    judge_part(job, d)
# mirror symmetry RL/RR, FL/FR: same mass, |com| relation
for a, b in (("synth_moving_RL", "synth_moving_RR"), ("synth_barrel_RL", "synth_barrel_RR"),
             ("cadmod_moving_FL", "cadmod_moving_FR"), ("cadmod_barrel_FL", "cadmod_barrel_FR")):
    r = J[a]["whole"]["mass_kg"] / J[b]["whole"]["mass_kg"] - 1
    check(f"mirror_mass_{a}_{b}<=1e-9", abs(r) <= 1e-9, r)
# synthesis method calibration on the front: synthesized front (drawing chain) vs CAD solid 10 (same pad)
cad_fl = float(Y["legs"]["FL"]["moving_part"]["mass_kg"])
calib = J["synth_moving_yamlpad_FL"]["whole"]["mass_kg"] / cad_fl - 1

legs_out = {}
for leg in ("FL", "FR", "RL", "RR"):
    front = leg[0] == "F"
    mj = J[f"cadmod_moving_{leg}" if front else f"synth_moving_{leg}"]
    bj = J[f"cadmod_barrel_{leg}" if front else f"synth_barrel_{leg}"]
    zb = float(Y["legs"][leg]["pad_bottom_center_retracted_m"][2])
    mp = {"mass_kg": mj["whole"]["mass_kg"], "com_retracted_m": mj["whole"]["com_m"],
          "com_above_pad_bottom_m": mj["whole"]["com_m"][2] - zb, "inertia_kg_m2": mj["whole"]["inertia_kg_m2"],
          "principal_kg_m2": mj["whole"]["tensor"]["principal_kg_m2"]}
    entry = {
        "basis": ("CAD solid 10 with the piston D115 -> D130 x 20 (CAD position), drawing bore" if front else
                  "drawing-chain synthesis (DWG REXOME35-9206 REAR): pad 250 x 250 + ribs + socket housing | ball D90 + "
                  "neck + rod D90 + piston D110 x 30"),
        "moving_part": mp,
        "yaml_now": {"mass_kg": float(Y["legs"][leg]["moving_part"]["mass_kg"]),
                     "com_above_pad_bottom_m": float(Y["legs"][leg]["moving_part"]["com_above_pad_bottom_m"]),
                     "inertia_diag_kg_m2": np.diag(np.array(Y["legs"][leg]["moving_part"]["inertia_kg_m2"])).tolist()},
        "barrel": {"basis": ("CAD solid 17 with the bore D115 -> D130 over the 700 mm bore" if front else
                             "drawing-chain synthesis: tube D137/D110, gland 105, cavity to the retracted piston top, "
                             "solid cap 110, mounting plate 340 x 250 x 25 (step 135 x 5) with 10 x D22"),
                   "mass_kg": bj["whole"]["mass_kg"], "com_m": bj["whole"]["com_m"],
                   "inertia_kg_m2": bj["whole"]["inertia_kg_m2"],
                   "cad_solid17_mass_kg": (J[f"cadmod_barrel_{leg}"]["cad_original"]["mass_kg"] if front else None)},
        "brep": {"moving": rel(mj["brep"]["file"]), "barrel": rel(bj["brep"]["file"])},
    }
    if not front:
        sp = mj["splits"]
        entry["pad_body_rod_body"] = {
            k: {b: {"mass_kg": sp[k][b]["mass_kg"], "com_m": sp[k][b]["com_m"],
                    "com_above_pad_bottom_m": sp[k][b]["com_above_pad_bottom_m"],
                    "inertia_kg_m2": sp[k][b]["inertia_kg_m2"]} for b in ("pad_body", "rod_body")}
            for k in sp}
        entry["pad"] = {"polygon_xy_m": (np.array(mj["geometry"]["pad_polygon_xy_mm"]) * 1e-3
                                         - np.array(Y["legs"][leg]["cylinder_axis_xy_m"])).tolist(),
                        "bottom_area_m2": mj["geometry"]["pad_area_mm2"] * 1e-6,
                        "side_angle_deg": mj["geometry"]["pad_side_angle_deg"],
                        "swivel_center_above_pad_bottom_m_read": 0.084}
        entry["pieces_kg"] = {k: v["mass_kg"] for k, v in mj["pieces"].items()}
        entry["barrel"]["pieces_kg"] = {k: v["mass_kg"] for k, v in bj["pieces"].items()}
        # CAD solid 17 of the rear leg (superstructure mass difference)
        import pandas as pd
        parts = pd.read_csv(PROJECT / "01_cad" / "01_parts" / "parts_classified.csv", encoding="utf-8-sig")
        row = parts[(parts["leg"] == leg) & (parts["group"] == "leg_barrel")]
        entry["barrel"]["cad_solid17_mass_kg"] = float(row["volume_mm3"].iloc[0]) * 7.85e-6
    else:
        entry["moving_part_cad_original_kg"] = J[f"cadmod_moving_{leg}"]["cad_original"]["mass_kg"]
    entry["barrel"]["delta_vs_cad_kg"] = entry["barrel"]["mass_kg"] - entry["barrel"]["cad_solid17_mass_kg"]
    legs_out[leg] = entry

out = {
    "schema": 1,
    "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
    "generated_by": "scratchpad cad-run/cyl35/cyl35_synth.py + cyl35_run.py + cyl35_aggregate.py (cad-expert, 2026-10-22)",
    "purpose": "REXOME35 cylinder replacement (dynamics_model.md rev. 29 5.11.10, CLAUDE.md '실린더 치수 기준 교체'): "
               "rear moving part / barrel by drawing-chain synthesis, front bore D130 by CAD modification",
    "frame": "machine body axes (x forward, y left, z up), origin = CAD origin, SI; moving parts retracted "
             "(pad bottom at YAML legs.<leg>.pad_bottom_center_retracted_m, geometry held: Q-C2); inertia about the CoM, "
             "body axes; BREP files in CAD frame mm at the CAD pose (01_cad/02_legs/legs convention)",
    "density_kg_m3": 7850.0, "density_status": "ASSUMPTION: steel (CAD material SS400 7.85); drawing has no material",
    "assumptions": [
        "front / rear dimensions marked R in cyl35_synth.DIMS are read off the drawing picture (+-3 mm): ball D100 / D90 "
        "centre 84 above the pad bottom, socket housing D170 h 25..83/84 + retainer to 115/116, neck R39 / R36, rib heights",
        "pad corner chamfer 30 mm, pad thickness 25 / side height 20 (CAD values)",
        "piston thickness 30 (picture), retracted piston bottom at the top of the 700 zone (mechanical stroke 700, Q-U4)",
        "rod solid (no gun-drill), bellows / pad bolts / valve block / pipes / seals / oil not modelled",
        "rear pad side direction = CAD (3.376 deg), ribs on the diagonals",
        "barrel: cap end at the CAD cap end (CAD Y max of solid 17), cavity to the retracted piston top, cap solid; "
        "rear mounting plate main face 89 / step face 84 from the axis, normal towards the superstructure centre (CAD side)",
        "geometry held (user Q-C2): the drawing pad portion 170 is not imposed on the leg pose; the synthesized barrel "
        "(anchored at the cap end) and the synthesized moving part (anchored at the pad bottom) are 54.3 (front) / "
        "74.3 (rear) mm apart from a drawing-consistent assembly; only the moving-part mass properties relative to "
        "its pad bottom are used",
    ],
    "synthesis_calibration_front": {
        "synth_front_with_cad_pad_kg": J["synth_moving_yamlpad_FL"]["whole"]["mass_kg"], "cad_solid10_kg": cad_fl,
        "rel": calib,
        "note": "same drawing-chain method applied to the front (CAD pad 330) vs CAD solid 10: indicates the method bias"},
    "legs": legs_out,
    "checks": checks,
    "all_checks_ok": all(c["ok"] for c in checks.values()),
    "jobs_wall_s": json.loads((JOBS_DIR / "all_jobs.json").read_text(encoding="utf-8"))["wall_s"],
}
CACHE.mkdir(parents=True, exist_ok=True)
(CACHE / "rexome35_cylinder_mass_properties.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
# job details (full records) next to the cache
(CACHE / "rexome35_cylinder_jobs.json").write_text(json.dumps(J, indent=1, ensure_ascii=False), encoding="utf-8")
# CSV
rows = ["leg,part,basis,mass_kg,com_x_m,com_y_m,com_z_m,com_above_pad_bottom_m,Ixx_kg_m2,Iyy_kg_m2,Izz_kg_m2,Ixy_kg_m2,Ixz_kg_m2,Iyz_kg_m2"]
for leg, e in legs_out.items():
    for part, rec in (("moving_part", e["moving_part"]), ("barrel", e["barrel"])):
        I = np.array(rec["inertia_kg_m2"])
        c = rec.get("com_retracted_m", rec.get("com_m"))
        rows.append(",".join(map(str, [leg, part, "cadmod" if leg[0] == "F" else "synth", rec["mass_kg"], *c,
                                       rec.get("com_above_pad_bottom_m", ""), I[0, 0], I[1, 1], I[2, 2], I[0, 1], I[0, 2], I[1, 2]])))
    if "pad_body_rod_body" in e:
        for split, pr in e["pad_body_rod_body"].items():
            for b, rec in pr.items():
                I = np.array(rec["inertia_kg_m2"])
                rows.append(",".join(map(str, [leg, f"{b}[{split}]", "synth", rec["mass_kg"], *rec["com_m"],
                                               rec["com_above_pad_bottom_m"], I[0, 0], I[1, 1], I[2, 2], I[0, 1], I[0, 2], I[1, 2]])))
(CACHE / "rexome35_cylinder_mass_properties.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
# cache meta
inputs = [PROJECT / "02_params" / "rexome33.yaml", PROJECT / "01_cad" / "01_parts" / "parts_classified.csv",
          *[PROJECT / "01_cad" / "02_legs" / "legs" / f for f in ("FRONT_JACK_CYL_1___10_1.brep", "FRONT_JACK_CYL_2___10_1.brep",
                                                                   "FRONT_JACK_CYL_1___17_1.brep", "FRONT_JACK_CYL_2___17_1.brep")],
          PROJECT / "08_test_data" / "datasheets" / "cylinder_front_extract.md",
          PROJECT / "08_test_data" / "datasheets" / "cylinder_rear_extract.md"]
meta = {"generated_at": out["generated_at"], "generator": out["generated_by"],
        "generator_scripts": {p.name: sha(p) for p in (HERE / "cyl35_synth.py", HERE / "cyl35_run.py", Path(__file__))},
        "inputs": [{"path": rel(p), "bytes": p.stat().st_size, "mtime": dt.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"),
                    "sha256": sha(p)} for p in inputs],
        "files": {p.name: {"bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(CACHE.glob("*")) if p.name != "cache_meta.json"},
        "brep_convention": "ASCII BREP, CAD frame (X_cad = y, Y_cad = z, Z_cad = x), mm, CAD pose = retracted - "
                           "legs.<leg>.retracted_offset_from_cad_m (YAML now: front 0, rear 0.002 m)",
        "tessellation_check": "BRepMesh linear 0.05 mm, angular 0.1 rad; trimesh volume / CoM / inertia vs B-rep",
        "cpu": "children pinned to logical 16-27 (E-cores, mask 0x0FFF0000), below-normal priority"}
(CACHE / "cache_meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")

# summary print
print("all checks ok:", out["all_checks_ok"])
for k, c in checks.items():
    if not c["ok"]:
        print("FAIL", k, c["value"])
print("calibration front synth vs CAD:", f"{calib:+.4f}")
for leg, e in legs_out.items():
    m = e["moving_part"]
    print(leg, f"moving {m['mass_kg']:.3f} kg (yaml {e['yaml_now']['mass_kg']:.3f}), com_above {m['com_above_pad_bottom_m']:.4f} "
          f"(yaml {e['yaml_now']['com_above_pad_bottom_m']:.4f}), I diag {np.round(np.diag(np.array(m['inertia_kg_m2'])), 4)} "
          f"(yaml {np.round(e['yaml_now']['inertia_diag_kg_m2'], 4)})")
    print("   barrel", f"{e['barrel']['mass_kg']:.3f} kg, CAD {e['barrel']['cad_solid17_mass_kg']:.3f}, d {e['barrel']['delta_vs_cad_kg']:+.3f}",
          "com", np.round(e["barrel"]["com_m"], 4))
    if "pad_body_rod_body" in e:
        for k, s in e["pad_body_rod_body"].items():
            print("  ", k, {b: (round(v["mass_kg"], 3), round(v["com_above_pad_bottom_m"], 4), np.round(np.diag(np.array(v["inertia_kg_m2"])), 4).tolist()) for b, v in s.items()})
        print("   pad", e["pad"]["bottom_area_m2"], e["pieces_kg"], e["barrel"]["pieces_kg"])
for job, d in J.items():
    print(job, "mesh", {k: (f"{v:.2e}" if isinstance(v, float) else v) for k, v in d["mesh_check"].items()}, f"{d['time_s']:.1f}s",
          d.get("cpu_affinity", [None])[0], f"{d.get('peak_wset_mb', 0):.0f}MB")
