"""Verify the C8 simplified shapes (01_cad/09_sim_shapes) by re-reading every OBJ.

Checks (results in 01_cad/09_sim_shapes/sim_shapes_verification.json):
    files       every OBJ of the index exists; vertex / face / piece counts as in the index
    pads        bottom area vs the pad-type table 02_params/pad_variants.json (the C8 index pads are
                type dwg_rear250: front 330 = 0.1071 m^2, rear 250 = 0.0607 m^2; U-PAD 2026-10-25;
                the YAML pad area (pad_shapes default type, bundle 2026-10-25) is recorded, not
                judged here: the table is checked against the YAML in pad_variants), outward normal
                (-z), side angle (47.1 / 3.4 deg, YAML), bottom height (YAML, 0.1 mm rounding),
                simple plate vs B-rep plate (volume, COM, inertia), down-facing area of the OBJ,
                inertia validity
    pad_variants every pad type of the table: hull / simple OBJ exist with the table SHA-256,
                down-facing area = table area, table polygon area = table area, b = 2 A / perimeter,
                bottom height (YAML), convex, table shapes = YAML pad_shapes (every type and leg;
                before the bundle: CAD-type polygons = YAML legs.<leg>.pad), via
                outrigger_sim.pad_variants.check_table_against_params
    legs        rod / pad / moving-part meshes vs B-rep (volume, COM, inertia), COM inside bbox,
                YAML moving-part COM inside the moving-part mesh bbox (attach offset sanity)
    visual      superstructure meshes vs B-rep: volume and bbox (recomputed from the OBJ)
    collision   every convex piece is convex (volume = its hull volume), pieces stay within the
                B-rep bbox of their input (+ margin), volume ratio to the B-rep

Criteria: house table (B-rep vs mesh volume <= 1 % accepted, <= 0.1 % match; mass properties
1e-6 for exact shapes). Visual-only superstructure meshes are reported with the same criterion
but do not feed mass properties.

Usage (project root): python -I 04_scripts/00_cad/verify_sim_shapes.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_sim_shapes import (  # noqa: E402
    INDEX_JSON,
    LEG_ORDER,
    OUT_DIR,
    PROJECT_ROOT,
    read_obj,
    rel,
    signed_volume,
    source_record,
)

sys.path.insert(0, str(PROJECT_ROOT / "03_src"))
from outrigger_sim.pad_variants import (  # noqa: E402
    DEFAULT_PAD_VARIANT,
    check_table_against_params,
    load_pad_variants,
)
from outrigger_sim.params import load_params  # noqa: E402

VERIFICATION_JSON = OUT_DIR / "sim_shapes_verification.json"
CLAUDE_PAD_ANGLE_DEG = {"FL": 47.1, "FR": 47.1, "RL": 3.4, "RR": 3.4}  # CLAUDE.md '다리 기하' (0.1 deg)
INDEX_PAD_VARIANT = DEFAULT_PAD_VARIANT  # the C8 index pads (front CAD 330, rear 250 synthesis) = type B
TOL = {
    "pad_area_rel": 1e-6, "pad_tilt_deg": 0.01, "pad_angle_yaml_deg": 1e-4, "pad_angle_claude_deg": 0.05,
    "pad_bottom_yaml_m": 1e-4, "exact_mass_rel": 1e-6, "mesh_volume_accept": 1e-2, "mesh_volume_match": 1e-3,
    "convex_rel": 1e-4, "piece_bbox_margin_m": 0.05,
    # OBJ coordinates are written with 6 decimals (1 um): round-trip tolerances of the exact pad plate
    "obj_roundtrip_rel": 1e-5, "obj_roundtrip_com_m": 1e-6,
}


def verdict(value: float, match: float, accept: float) -> str:
    v = abs(value)
    return "일치" if v <= match else "허용" if v <= accept else "불일치"


def inertia_ok(inertia: np.ndarray) -> dict:
    i = np.asarray(inertia, float)
    eig = np.linalg.eigvalsh(0.5 * (i + i.T))
    return {"symmetric": bool(np.allclose(i, i.T, rtol=0, atol=1e-12 * np.abs(i).max())),
            "positive": bool(eig.min() > 0), "triangle": bool(eig[0] + eig[1] >= eig[2] * (1 - 1e-9)),
            "principal": eig.tolist()}


def check_files(index: dict) -> dict:
    out, failures = {}, []
    for role in ("visual", "collision"):
        for name, entry in index[role].items():
            if not entry.get("file"):
                continue
            path = PROJECT_ROOT / entry["file"]
            if not path.exists():
                failures.append(f"{name}: missing {entry['file']}")
                continue
            pieces = read_obj(path)
            faces = sum(len(f) for _, f in pieces)
            ok = faces == entry["faces"] and len(pieces) == entry.get("pieces", 1)
            out[name] = {"file": entry["file"], "bytes": path.stat().st_size, "faces": faces,
                         "pieces": len(pieces), "matches_index": ok}
            if not ok:
                failures.append(f"{name}: faces {faces} / pieces {len(pieces)} differ from the index")
    return {"items": out, "failures": failures}


def check_pads(index: dict, params, table) -> dict:
    out, failures = {}, []
    variant = table.variant(INDEX_PAD_VARIANT)
    for i, leg in enumerate(LEG_ORDER):
        shape = variant.leg(leg)
        if not shape.hull_in_c8_index or shape.hull_name != f"pad_{leg}_hull":
            failures.append(f"pad {leg}: table type {INDEX_PAD_VARIANT} does not use the C8 index hull")
        rec = index["legs"][leg]
        face = rec["pad_face"]
        v, f = read_obj(PROJECT_ROOT / index["visual"][f"pad_{leg}_simple"]["file"])[0]
        a, b, c = (v[f[:, k]] for k in range(3))
        n = np.cross(b - a, c - a)
        down = n[:, 2] < 0
        down_area = 0.5 * float(np.linalg.norm(n[down], axis=1).sum())
        mesh = trimesh.Trimesh(v, f, process=False)
        brep = rec["pad_simple"]["brep_plate"]
        yaml_bottom = np.asarray(params.legs[i].pad_bottom_center_retracted_m)
        obj_bottom = v[np.isclose(v[:, 2], v[:, 2].min(), atol=1e-9)].mean(0)
        table_poly = np.asarray(shape.polygon_xy_m) + yaml_bottom[:2]
        item = {
            "brep_area_m2": face["brep_area_m2"],
            "pad_variant": INDEX_PAD_VARIANT,
            "table_area_m2": shape.bottom_area_m2,
            "area_rel_to_table": face["brep_area_m2"] / shape.bottom_area_m2 - 1,
            "table_polygon_area_rel_to_brep": _shoelace(table_poly) / face["brep_area_m2"] - 1,
            "table_polygon_max_vertex_diff_m": float(np.abs(
                _nearest_diff(np.asarray(face["brep_polygon_xy_body_m"]), table_poly)).max()),
            "obj_down_area_rel_to_brep": down_area / face["brep_area_m2"] - 1,
            # YAML pad = pad_shapes default type (dwg_rear250 since the bundle 2026-10-25, before it the
            # CAD 330 rear pad): recorded, not judged (the table vs YAML check is in check_pad_variants)
            "yaml_area_rel_to_brep_info": face["yaml_polygon_area_m2"] / face["brep_area_m2"] - 1,
            "tilt_deg": face["brep_tilt_from_vertical_deg"],
            "side_angle_brep_deg": face["brep_side_angle_deg"],
            "side_angle_yaml_deg": face["yaml_side_angle_deg"],
            "side_angle_claude_deg": CLAUDE_PAD_ANGLE_DEG[leg],
            "obj_bottom_centre_m": obj_bottom.tolist(),
            "obj_bottom_minus_yaml_m": (obj_bottom - yaml_bottom).tolist(),
            "obj_convex": bool(abs(mesh.convex_hull.volume / mesh.volume - 1) <= TOL["convex_rel"]),
            "obj_volume_rel_to_brep_plate": mesh.volume / brep["volume_m3"] - 1,
            "obj_com_abs_m": float(np.linalg.norm(mesh.center_mass - brep["com_m"])),
            "obj_inertia_rel": float(np.linalg.norm(mesh.moment_inertia - brep["inertia_unit_density_m5"])
                                     / np.linalg.norm(brep["inertia_unit_density_m5"])),
            "inertia": inertia_ok(mesh.moment_inertia),
        }
        checks = {
            "area_vs_table": abs(item["area_rel_to_table"]) <= TOL["pad_area_rel"],
            "obj_area": abs(item["obj_down_area_rel_to_brep"]) <= TOL["pad_area_rel"],
            "table_polygon_area": abs(item["table_polygon_area_rel_to_brep"]) <= TOL["pad_area_rel"],
            "table_polygon_vertices": item["table_polygon_max_vertex_diff_m"] <= TOL["pad_bottom_yaml_m"],
            "normal": item["tilt_deg"] <= TOL["pad_tilt_deg"],
            "angle_yaml": abs(item["side_angle_brep_deg"] - item["side_angle_yaml_deg"]) <= TOL["pad_angle_yaml_deg"],
            "angle_claude": abs(item["side_angle_brep_deg"] - item["side_angle_claude_deg"]) <= TOL["pad_angle_claude_deg"],
            "bottom_vs_yaml": float(np.abs(item["obj_bottom_minus_yaml_m"]).max()) <= TOL["pad_bottom_yaml_m"],
            "convex": item["obj_convex"],
            "volume": abs(item["obj_volume_rel_to_brep_plate"]) <= TOL["obj_roundtrip_rel"],
            "com": item["obj_com_abs_m"] <= TOL["obj_roundtrip_com_m"],
            "inertia_rel": item["obj_inertia_rel"] <= TOL["obj_roundtrip_rel"],
            "inertia_valid": all(item["inertia"][k] for k in ("symmetric", "positive", "triangle")),
        }
        item["checks"] = checks
        failures += [f"pad {leg}: {k}" for k, ok in checks.items() if not ok]
        out[leg] = item
    return {"items": out, "failures": failures}


def _shoelace(xy: np.ndarray) -> float:
    x, y = xy[:, 0], xy[:, 1]
    return abs(0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def _nearest_diff(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Vertex differences after matching every vertex of ``a`` to the nearest of ``b`` (and back)."""
    d = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
    return np.concatenate([a - b[d.argmin(1)], b - a[d.argmin(0)]])


def check_pad_variants(params, table) -> dict:
    """Every pad type of 02_params/pad_variants.json: hull / simple OBJ vs the table."""
    import hashlib

    out, failures = {}, []
    try:
        check_table_against_params(table, params)
        out["cad_polygons_equal_yaml"] = True
    except ValueError as error:
        out["cad_polygons_equal_yaml"] = False
        failures.append(f"pad_variants: {error}")
    for variant in table.variants.values():
        vout = {}
        for i, shape in enumerate(variant.legs):
            yaml_bottom = np.asarray(params.legs[i].pad_bottom_center_retracted_m)
            poly = np.asarray(shape.polygon_xy_m)
            perimeter = float(np.linalg.norm(np.roll(poly, -1, axis=0) - poly, axis=1).sum())
            item = {"hull": shape.hull_name, "in_c8_index": shape.hull_in_c8_index,
                    "table_area_m2": shape.bottom_area_m2, "bekker_b_m": shape.bekker_b_m,
                    "table_polygon_area_rel": _shoelace(poly) / shape.bottom_area_m2 - 1,
                    "bekker_b_rel": shape.bekker_b_m / (2 * shape.bottom_area_m2 / perimeter) - 1}
            checks = {"polygon_area": abs(item["table_polygon_area_rel"]) <= TOL["pad_area_rel"],
                      "bekker_b": abs(item["bekker_b_rel"]) <= TOL["pad_area_rel"]}
            for role, path in (("hull", shape.hull_file), ("visual_simple", shape.visual_simple_file)):
                if not path.exists():
                    failures.append(f"pad_variants {variant.name}.{shape.leg}: {role} {path} missing")
                    continue
                v, f = read_obj(path)[0]
                mesh = trimesh.Trimesh(v, f, process=False)
                a, b, c = (v[f[:, k]] for k in range(3))
                n = np.cross(b - a, c - a)
                down_area = 0.5 * float(np.linalg.norm(n[n[:, 2] < 0], axis=1).sum())
                bottom = v[np.isclose(v[:, 2], v[:, 2].min(), atol=1e-9)].mean(0)
                item[role] = {
                    "file": rel(path),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "down_area_rel_to_table": down_area / shape.bottom_area_m2 - 1,
                    "bottom_minus_yaml_m": (bottom - yaml_bottom).tolist(),
                    "convex": bool(abs(mesh.convex_hull.volume / mesh.volume - 1) <= TOL["convex_rel"]),
                }
                checks[f"{role}_area"] = abs(item[role]["down_area_rel_to_table"]) <= TOL["pad_area_rel"]
                checks[f"{role}_bottom"] = float(np.abs(item[role]["bottom_minus_yaml_m"]).max()) <= TOL["pad_bottom_yaml_m"]
                checks[f"{role}_convex"] = item[role]["convex"]
            item["checks"] = checks
            failures += [f"pad_variants {variant.name}.{shape.leg}: {k}" for k, ok in checks.items() if not ok]
            vout[shape.leg] = item
        out[variant.name] = vout
    return {"items": out, "failures": failures}


def check_legs(index: dict, params) -> dict:
    out, failures = {}, []
    for i, leg in enumerate(LEG_ORDER):
        rec = index["legs"][leg]
        legout = {}
        for key, name in (("rod", f"rod_{leg}"), ("pad_cad", f"pad_{leg}_cad")):
            v, f = read_obj(PROJECT_ROOT / index["visual"][name]["file"])[0]
            mesh = trimesh.Trimesh(v, f, process=False)
            brep = rec[key]["brep"]
            vol_rel = signed_volume(v, f) / brep["volume_m3"] - 1
            box = np.array([v.min(0), v.max(0)])
            com = mesh.center_mass
            legout[key] = {
                "faces": int(len(f)), "volume_rel_to_brep": vol_rel,
                "volume_verdict": verdict(vol_rel, TOL["mesh_volume_match"], TOL["mesh_volume_accept"]),
                "com_abs_m": float(np.linalg.norm(com - brep["com_m"])),
                "inertia_rel": float(np.linalg.norm(mesh.moment_inertia - brep["inertia_unit_density_m5"])
                                     / np.linalg.norm(brep["inertia_unit_density_m5"])),
                "com_in_bbox": bool(np.all(com >= box[0]) and np.all(com <= box[1])),
                "bbox_abs_diff_m": float(np.abs(box - np.array(rec[key]["brep_bbox_body_m"])).max()),
                "inertia": inertia_ok(mesh.moment_inertia),
            }
            if legout[key]["volume_verdict"] == "불일치" or not legout[key]["com_in_bbox"]:
                failures.append(f"{name}: volume {vol_rel:+.2e} / com_in_bbox {legout[key]['com_in_bbox']}")
        # attach offset sanity: YAML moving-part COM inside rod + pad bbox, near the B-rep COM
        yaml_com = np.asarray(params.legs[i].moving_part.com_m)
        brep_com = np.asarray(rec["moving"]["brep"]["com_m"])
        legout["yaml_moving_com_minus_brep_m"] = (yaml_com - brep_com).tolist()
        if np.abs(yaml_com - brep_com).max() > 1e-6:
            failures.append(f"{leg}: YAML moving_part.com_m differs from the B-rep COM by "
                            f"{np.abs(yaml_com - brep_com).max():.2e} m")
        out[leg] = legout
    return {"items": out, "failures": failures}


def check_visual(index: dict) -> dict:
    out = {}
    for name, entry in index["visual"].items():
        if entry["attach"] != "superstructure" or name not in index["groups"]:
            continue
        group = index["groups"][name]
        path = PROJECT_ROOT / entry["file"]
        if not path.exists():
            out[name] = {"missing": entry["file"]}
            continue
        v, f = read_obj(path)[0]
        vol_rel = signed_volume(v, f) / group["brep_volume_m3"] - 1
        box = np.array([v[np.unique(f)].min(0), v[np.unique(f)].max(0)])
        diff = np.abs(box - np.array(group["brep_bbox_body_m"]))
        out[name] = {
            "faces_source": group["source_mesh"]["faces"], "faces": int(len(f)),
            "face_ratio": len(f) / group["source_mesh"]["faces"],
            "source_volume_rel_to_brep": group["source_mesh"]["volume_rel_to_brep"],
            "volume_rel_to_brep": vol_rel,
            "volume_verdict": verdict(vol_rel, TOL["mesh_volume_match"], TOL["mesh_volume_accept"]),
            "bbox_abs_diff_mm": float(diff.max() * 1e3), "bbox_abs_diff_xyz_mm": (diff.max(0) * 1e3).tolist(),
            "dropped_small_components": group["dropped_small_components"],
            "component_methods": group["component_methods"],
            "obj_mb": path.stat().st_size / 1e6,
        }
    return {"items": out}


def check_collision(index: dict) -> dict:
    out, failures = {}, []
    for name, entry in index["collision"].items():
        if not entry.get("file"):
            out[name] = {"kind": entry["kind"], "primitive": True}
            continue
        pieces = read_obj(PROJECT_ROOT / entry["file"])
        worst_convex = 0.0
        total = 0.0
        lo = np.full(3, np.inf)
        hi = np.full(3, -np.inf)
        for v, f in pieces:
            m = trimesh.Trimesh(v, f, process=False)
            vol = signed_volume(v, f, v.mean(0))
            hull = m.convex_hull.volume
            worst_convex = max(worst_convex, abs(vol / hull - 1) if hull > 0 else 1.0)
            total += vol
            lo, hi = np.minimum(lo, v.min(0)), np.maximum(hi, v.max(0))
        ref_box = _reference_bbox(index, name, entry)
        excess = None
        if ref_box is not None:
            excess = float(max((ref_box[0] - lo).max(), (hi - ref_box[1]).max(), 0.0))
        item = {"kind": entry["kind"], "pieces": len(pieces), "faces": int(sum(len(f) for _, f in pieces)),
                "max_convexity_defect_rel": worst_convex, "sum_volume_m3": total,
                "volume_ratio_to_brep": entry.get("volume_ratio_to_brep") or (1 + entry.get("volume_rel_to_brep_plate", 0)),
                "bbox_excess_over_brep_m": excess}
        out[name] = item
        if worst_convex > TOL["convex_rel"]:
            failures.append(f"{name}: piece not convex ({worst_convex:.2e})")
        if excess is not None and excess > TOL["piece_bbox_margin_m"]:
            failures.append(f"{name}: pieces extend {excess:.3f} m beyond the B-rep bbox")
    return {"items": out, "failures": failures}


def check_upper_rollers(index: dict) -> dict:
    """Upper rollers: OBJ vs B-rep (volume about the B-rep COM, bbox), roller-solid mass
    properties, primitive cylinders vs the crawler_upper_rollers.csv values, duplicate
    removal from the crawler visual."""
    import pandas as pd

    upper = index.get("upper_rollers") or {}
    if not upper:
        return {"items": {}, "failures": ["upper rollers missing from the index"]}
    csv = {r.side: r for r in pd.read_csv(PROJECT_ROOT / upper["source"]["path"], encoding="utf-8-sig").itertuples()}
    out, failures = {}, []
    for side, rec in upper["rollers"].items():
        v, f = read_obj(PROJECT_ROOT / index["visual"][f"upper_roller_{side}"]["file"])[0]
        brep = rec["brep_props"]
        com = np.array(brep["com_m"])
        vol_rel = signed_volume(v, f, com) / brep["volume_m3"] - 1
        box = np.array([v.min(0), v.max(0)])
        bbox_diff = float(np.abs(box - np.array(rec["brep_bbox_body_m"])).max())
        row = csv[side]
        cyl = index["collision"][f"upper_roller_{side}_cylinders"]["cylinders"]
        treads = sorted((c for c in cyl if abs(c["radius_m"] - 0.06) < 1e-6), key=lambda c: abs(c["centre_m"][1]))
        flange = [c for c in cyl if abs(c["radius_m"] - 0.07) < 1e-6]
        spans = sorted(sorted(float(t) for t in s.split("..")) for s in row.tread_spans_x_cad_mm.split(";"))
        tread_spans = sorted(sorted(c["x_cad_span_mm"]) for c in treads)
        hull_v, hull_f = read_obj(PROJECT_ROOT / index["collision"][f"upper_roller_{side}_hull"]["file"])[0]
        hull_box = np.array([hull_v.min(0), hull_v.max(0)])
        item = {
            "faces": int(len(f)), "volume_rel_to_brep": vol_rel,
            "volume_verdict": verdict(vol_rel, TOL["mesh_volume_match"], TOL["mesh_volume_accept"]),
            "bbox_abs_diff_mm": bbox_diff * 1e3,
            "brep_volume_rel_to_csv": rec["brep_volume_rel_to_csv"],
            "roller_solid_mesh_vs_brep": rec["roller_solid"]["mesh_vs_brep"],
            "roller_solid_watertight": rec["roller_solid"]["mesh"]["watertight"],
            "skipped_faces_whole_part": rec["tessellation"]["skipped_faces"],
            "tread_count": len(treads), "flange_count": len(flange),
            "tread_diameter_mm": [2e3 * c["radius_m"] for c in treads],
            "tread_width_mm": [1e3 * c["height_m"] for c in treads],
            "tread_span_diff_mm": float(np.abs(np.array(tread_spans) - np.array(spans)).max()),
            "flange_diameter_mm": [2e3 * c["radius_m"] for c in flange],
            "flange_width_diff_mm": abs(1e3 * flange[0]["height_m"] - float(row.flange_width_mm)) if flange else None,
            "cylinders_on_axis_m": float(max(np.hypot(c["centre_m"][0] - rec["axis_body_m"][0],
                                                      c["centre_m"][2] - rec["axis_body_m"][2]) for c in cyl)),
            "hull_bbox_abs_diff_mm": float(np.abs(hull_box - np.array(rec["brep_bbox_body_m"])).max() * 1e3),
            "crawler_duplicate": rec["crawler_overlap"],
        }
        checks = {
            "volume": item["volume_verdict"] != "불일치",
            "bbox": item["bbox_abs_diff_mm"] <= 1.0,
            "brep_vs_csv": abs(item["brep_volume_rel_to_csv"]) <= 1e-6,
            "roller_solid_mass": abs(item["roller_solid_mesh_vs_brep"]["volume_rel"]) <= TOL["mesh_volume_accept"]
            and item["roller_solid_watertight"],
            "cylinder_counts": item["tread_count"] == 2 and item["flange_count"] == 1,
            "tread_diameter": all(abs(d - float(row.tread_diameter_mm)) <= 1e-6 for d in item["tread_diameter_mm"]),
            "tread_width": all(abs(w - float(row.tread_width_mm)) <= 1e-3 for w in item["tread_width_mm"]),
            "tread_spans": item["tread_span_diff_mm"] <= 0.01,
            "flange": bool(flange) and abs(item["flange_diameter_mm"][0] - float(row.flange_diameter_mm)) <= 1e-6
            and item["flange_width_diff_mm"] <= 1e-3,
            "on_axis": item["cylinders_on_axis_m"] <= 1e-9,
            "hull_bbox": item["hull_bbox_abs_diff_mm"] <= 1.0,
            "duplicate_volume": abs(rec["crawler_overlap"]["volume_rel_to_roller_brep"]) <= 0.05,
        }
        item["checks"] = checks
        failures += [f"upper roller {side}: {k}" for k, ok in checks.items() if not ok]
        out[side] = item
    variant = upper["crawler_variant"]
    crawler_faces = index["visual"]["crawler"]["faces"]
    removed = sum(r["crawler_overlap"]["faces"] for r in upper["rollers"].values())
    out["crawler_no_upper_rollers"] = {"faces": variant["visual_mesh"]["faces"], "crawler_faces": crawler_faces,
                                       "removed_faces": removed,
                                       "faces_consistent": variant["visual_mesh"]["faces"] + removed == crawler_faces,
                                       "volume_rel_to_brep": variant["visual_mesh"]["volume_rel_to_brep"]}
    if not out["crawler_no_upper_rollers"]["faces_consistent"]:
        failures.append("crawler_no_upper_rollers: faces + removed != crawler faces")
    return {"items": out, "failures": failures}


def _reference_bbox(index: dict, name: str, entry: dict):
    key = entry.get("input") or index.get("decompositions", {}).get(name, {}).get("input") \
        or index.get("hulls", {}).get(name, {}).get("input")
    if name.startswith("upper_roller_") and name.endswith("_hull"):
        return np.array(index["upper_rollers"]["rollers"][name[13]]["brep_bbox_body_m"])
    if name.startswith("pad_") and name.endswith("_hull"):
        leg = name[4:6]
        return np.array(index["legs"][leg]["pad_simple"]["stats"]["bbox_min"]), \
            np.array(index["legs"][leg]["pad_simple"]["stats"]["bbox_max"])
    if key is None:
        return None
    if key in index["groups"]:
        return np.array(index["groups"][key]["brep_bbox_body_m"])
    if key.startswith("track_"):
        return np.array(index["groups"]["crawler"]["tracks"][key[-1]]["brep_bbox_body_m"])
    for prefix in ("rod", "pad_cad", "moving"):
        if key.startswith(prefix + "_"):
            return np.array(index["legs"][key[-2:]][prefix]["brep_bbox_body_m"])
    return None


def _plain(obj):
    if isinstance(obj, (np.bool_, np.integer, np.floating)):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(type(obj))


def main() -> None:
    started = time.perf_counter()
    index = json.loads(INDEX_JSON.read_text(encoding="utf-8"))
    params = load_params()
    table = load_pad_variants()
    result = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "index": source_record(INDEX_JSON),
        "script": source_record(Path(__file__)),
        "pad_variants_table": {**source_record(table.path), "default": table.default,
                               "index_pad_variant": INDEX_PAD_VARIANT},
        "tolerances": TOL,
        "files": check_files(index),
        "pads": check_pads(index, params, table),
        "pad_variants": check_pad_variants(params, table),
        "legs": check_legs(index, params),
        "visual": check_visual(index),
        "collision": check_collision(index),
        "upper_rollers": check_upper_rollers(index),
    }
    failures = [f for k in ("files", "pads", "pad_variants", "legs", "collision", "upper_rollers")
                for f in result[k]["failures"]]
    visual_verdicts = {k: v.get("volume_verdict") for k, v in result["visual"]["items"].items()}
    result["failures"] = failures
    result["verdict"] = {
        "pads_rods_collision": "통과" if not failures else "실패",
        "superstructure_visual_volume": visual_verdicts,
        "note": "superstructure visual meshes are display only; their volume is not used for mass",
    }
    result["time_s"] = time.perf_counter() - started
    VERIFICATION_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=1, default=_plain), encoding="utf-8")
    print(f"wrote {rel(VERIFICATION_JSON)}: {len(failures)} failure(s) {failures[:10]}; visual {visual_verdicts}; "
          f"{result['time_s']:.0f} s")


if __name__ == "__main__":
    main()
