"""Derive small use-specific crawler results from the B-rep cache (no STEP read).

The crawler is one prototype (``0:1:1:746``, ``REX33-REX33 - 5J286105``,
3,214 solids, 156,614 faces). Its STEP description names another machine
(REXOME25), so its geometry stands for the undercarriage only as drawn.
Reading the prototype takes about 3 s (binary); walking all faces takes
several minutes, so the results below are kept in
``01_cad/06_brep/derived/crawler/``. All coordinates are the CAD world frame
(mm, Y up, crawler placement applied); ``*_body_m`` values use the body axes
(x = +Z_cad, y = +X_cad, z = +Y_cad) with the CAD origin, in metres.

* ``crawler_summary.json`` (C7): ground level, track centre spacing, shoe
  width, track length, flat ground length per height band, wheel stations,
  comparison with the earlier review values, provenance.
* ``crawler_ground_faces.csv`` (C7): every face whose lowest point is within
  ``FACE_LIST_BAND_MM`` of the ground level.
* ``crawler_grouser_tips.csv`` (C7): downward horizontal planar faces up to
  ``TIP_SEARCH_MM`` above ground (grouser tips; height profile along the track).
* ``crawler_wheels.csv`` (C7): round solids grouped into wheel stations.
* ``crawler_solids.csv`` (C5/C8): per solid volume, centroid, bbox, side.
* ``crawler_face_stats.json`` (C5): face counts by height band, surface type
  and side (basis for indexing only the faces near the ground).
* ``crawler_collision.json`` + ``track_left_hull.obj``, ``track_right_hull.obj``,
  ``crawler_lowres.obj`` (C8): convex hull per track, box approximations and
  a low-res visual mesh (decimated large solids), with volume and bbox
  differences to the B-rep.

Usage:
    python -I 04_scripts/00_cad/derive_crawler_cache.py
"""

import json
import sys
import tempfile
import time
from pathlib import Path

import fast_simplification
import numpy as np
import pandas as pd
import psutil
import trimesh
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRep import BRep_Builder
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
from OCC.Core.GProp import GProp_GProps
from OCC.Core.StlAPI import StlAPI_Writer
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_REVERSED, TopAbs_SOLID
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import TopoDS_Compound, topods

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brep_cache
from cad_common import MM_PER_M, PROJECT_ROOT
from check_cache import sha256_file
from inspect_legs import SURFACE_TYPE_NAMES

CRAWLER_ENTRY = "0:1:1:746"
OUT_DIR = brep_cache.DERIVED_DIR / "crawler"
LOG_PATH = OUT_DIR / "derive.log"

GROUND_BANDS_MM = (1.0, 3.0, 5.0, 10.0)  # flat ground length per band
FACE_LIST_BAND_MM = 3.0  # crawler_ground_faces.csv
TIP_SEARCH_MM = 120.0  # crawler_grouser_tips.csv
STATS_BANDS_MM = (1, 3, 10, 50, 100, 200, 400)
DOWN_NORMAL_Y = -0.99  # downward plane: normal y below this
SIDE_SPLIT_MM = 600.0  # solid fully beyond |X| > this belongs to a track side
SHOE_MIN_WIDTH_MM = 400.0  # track shoes are wider than this in X
ROUND_TOLERANCE_MM = 1.0  # |dy - dz| for a solid of revolution about X
STATION_TOLERANCE_MM = 5.0  # coaxial solids within this form one wheel station
MESH_LINEAR_MM = 5.0
MESH_ANGULAR_RAD = 0.5
# Low-res visual mesh: the largest solids of each group up to this share of
# the group volume (bolts and pins dropped), each fine mesh decimated with
# fast-simplification. Thin plates stop decimating early, so the face count
# is reported rather than fixed.
LOWRES_VOLUME_SHARE = 0.95
LOWRES_TARGET_REDUCTION = 0.9
# CAD -> body axes (x = +Z_cad, y = +X_cad, z = +Y_cad), CAD origin.
CAD_TO_BODY = np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
# Values from the earlier review (00_docs/00_cad/cad_origin_mass_imu.md 2.6).
PREVIOUS = {
    "track_centre_m": 1.045,
    "shoe_ground_width_m": 0.423,
    "flat_length_1mm_m": 1.64,
    "flat_length_3mm_m": 1.84,
    "flat_x_range_1mm_m": [-0.826, 0.813],
}


def log(message: str) -> None:
    rss_gb = psutil.Process().memory_info().rss / 1e9
    line = f"[{time.strftime('%H:%M:%S')} | rss {rss_gb:5.2f} GB] {message}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def body_m(point_cad_mm) -> list[float]:
    return (CAD_TO_BODY @ np.asarray(point_cad_mm, dtype=float) / MM_PER_M).round(6).tolist()


def _bbox(shape) -> tuple[float, ...]:
    box = Bnd_Box()
    brepbndlib.AddOptimal(shape, box, False, False)
    return box.Get()


def side_of(x_min: float, x_max: float) -> str:
    """Track side from the CAD X extent (+X_cad = body +y = left)."""
    if x_min > SIDE_SPLIT_MM:
        return "left"
    if x_max < -SIDE_SPLIT_MM:
        return "right"
    return "center"


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------
def tabulate(shape) -> tuple[pd.DataFrame, pd.DataFrame, list]:
    """Solid table, face table (bbox, type, normal) and the solid shapes."""
    solid_rows, face_rows, solid_shapes = [], [], []
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    while explorer.More():
        solid = topods.Solid(explorer.Current())
        explorer.Next()
        index = len(solid_shapes)
        solid_shapes.append(solid)
        properties = GProp_GProps()
        brepgprop.VolumeProperties(solid, properties)
        centre = properties.CentreOfMass()
        box = _bbox(solid)
        solid_rows.append(
            {
                "solid": index,
                "side": side_of(box[0], box[3]),
                "volume_mm3": properties.Mass(),
                "centroid_x_mm": centre.X(),
                "centroid_y_mm": centre.Y(),
                "centroid_z_mm": centre.Z(),
                **dict(zip(_BOX_COLUMNS, box, strict=True)),
            }
        )
        face_explorer = TopExp_Explorer(solid, TopAbs_FACE)
        while face_explorer.More():
            face = topods.Face(face_explorer.Current())
            face_explorer.Next()
            face_rows.append({"solid": index, "face": face, **_face_record(face)})
        if (index + 1) % 500 == 0:
            log(f"  tabulated {index + 1} solids, {len(face_rows)} faces")
    return pd.DataFrame(solid_rows), pd.DataFrame(face_rows), solid_shapes


_BOX_COLUMNS = ("bbox_min_x_mm", "bbox_min_y_mm", "bbox_min_z_mm") + (
    "bbox_max_x_mm",
    "bbox_max_y_mm",
    "bbox_max_z_mm",
)


def _face_record(face) -> dict:
    surface = BRepAdaptor_Surface(face, True)
    surface_type = surface.GetType()
    normal = (np.nan, np.nan, np.nan)
    radius = np.nan
    if surface_type == GeomAbs_Plane:
        direction = surface.Plane().Axis().Direction()
        sign = -1.0 if face.Orientation() == TopAbs_REVERSED else 1.0
        normal = (sign * direction.X(), sign * direction.Y(), sign * direction.Z())
    elif surface_type == GeomAbs_Cylinder:
        radius = surface.Cylinder().Radius()
    return {
        "surface_type": SURFACE_TYPE_NAMES.get(surface_type, str(surface_type)),
        "normal_x": normal[0],
        "normal_y": normal[1],
        "normal_z": normal[2],
        "radius_mm": radius,
        **dict(zip(_BOX_COLUMNS, _bbox(face), strict=True)),
    }


def add_face_details(faces: pd.DataFrame, ground_y: float) -> pd.DataFrame:
    """Height above ground for all faces; area and centroid for low faces."""
    faces["height_mm"] = faces["bbox_min_y_mm"] - ground_y
    low = faces["height_mm"] <= TIP_SEARCH_MM
    areas, centres = [], []
    for face in faces.loc[low, "face"]:
        properties = GProp_GProps()
        brepgprop.SurfaceProperties(face, properties)
        centre = properties.CentreOfMass()
        areas.append(properties.Mass())
        centres.append((centre.X(), centre.Y(), centre.Z()))
    centres = np.asarray(centres)
    faces["area_mm2"] = np.nan
    for column in ("centroid_x_mm", "centroid_y_mm", "centroid_z_mm"):
        faces[column] = np.nan
    faces.loc[low, "area_mm2"] = areas
    faces.loc[low, ["centroid_x_mm", "centroid_y_mm", "centroid_z_mm"]] = centres
    return faces


# --------------------------------------------------------------------------
# C7: ground contact and wheels
# --------------------------------------------------------------------------
def grouser_tips(faces: pd.DataFrame, solids: pd.DataFrame) -> pd.DataFrame:
    """Downward horizontal planes near the ground (grouser tips and shoe plates)."""
    tips = faces[
        (faces["surface_type"] == "plane")
        & (faces["normal_y"] < DOWN_NORMAL_Y)
        & (faces["height_mm"] <= TIP_SEARCH_MM)
    ].copy()
    tips["side"] = solids.set_index("solid").loc[tips["solid"], "side"].to_numpy()
    tips["plane_height_mm"] = tips["centroid_y_mm"] - faces["bbox_min_y_mm"].min()
    return tips.sort_values(["side", "centroid_z_mm"])


def ground_patches(tips: pd.DataFrame) -> dict:
    """Per side and band: contact rectangle of grouser tips, length, width, centre."""
    patches = {}
    for band in GROUND_BANDS_MM:
        for side in ("left", "right"):
            selected = tips[(tips["side"] == side) & (tips["plane_height_mm"] <= band)]
            if selected.empty:
                continue
            x0, x1 = selected["bbox_min_x_mm"].min(), selected["bbox_max_x_mm"].max()
            z0, z1 = selected["bbox_min_z_mm"].min(), selected["bbox_max_z_mm"].max()
            patches.setdefault(f"{band:g}mm", {})[side] = {
                "face_count": len(selected),
                "tip_area_mm2": float(selected["area_mm2"].sum()),
                "x_range_mm": [float(x0), float(x1)],
                "z_range_mm": [float(z0), float(z1)],
                "width_mm": float(x1 - x0),
                "length_mm": float(z1 - z0),
                "centre_x_mm": float((x0 + x1) / 2),
                "centre_z_mm": float((z0 + z1) / 2),
            }
    return patches


def shoe_pitch(tips: pd.DataFrame) -> dict:
    """Pitch from the spacing of grouser tip planes at ground level (left side)."""
    level = tips[(tips["side"] == "left") & (tips["plane_height_mm"] <= 1.0)]
    centres = np.sort(level["centroid_z_mm"].round(1).unique())
    # Several faces per grouser: merge centres closer than 50 mm.
    merged: list[float] = []
    for value in centres:
        if merged and value - merged[-1] < 50.0:
            continue
        merged.append(float(value))
    spacing = np.diff(merged)
    return {
        "grousers_on_ground_left": len(merged),
        "pitch_mm_median": float(np.median(spacing)) if len(spacing) else None,
        "pitch_mm_min_max": [float(spacing.min()), float(spacing.max())] if len(spacing) else None,
    }


def wheel_stations(solids: pd.DataFrame) -> pd.DataFrame:
    """Group solids of revolution about X (round in the YZ plane) into stations."""
    rows = solids[solids["side"] != "center"].copy()
    rows["dy"] = rows["bbox_max_y_mm"] - rows["bbox_min_y_mm"]
    rows["dz"] = rows["bbox_max_z_mm"] - rows["bbox_min_z_mm"]
    rows["dx"] = rows["bbox_max_x_mm"] - rows["bbox_min_x_mm"]
    rows["axis_y"] = (rows["bbox_max_y_mm"] + rows["bbox_min_y_mm"]) / 2
    rows["axis_z"] = (rows["bbox_max_z_mm"] + rows["bbox_min_z_mm"]) / 2
    # Shoes (about 600 mm wide in X) can look round in YZ at the track ends.
    round_rows = rows[
        ((rows["dy"] - rows["dz"]).abs() < ROUND_TOLERANCE_MM)
        & (rows["dy"] > 100)
        & (rows["dx"] < SHOE_MIN_WIDTH_MM)
    ]
    stations = []
    for side, group in round_rows.groupby("side"):
        remaining = group.sort_values("dy", ascending=False)
        while not remaining.empty:
            seed = remaining.iloc[0]
            near = (remaining["axis_y"] - seed["axis_y"]).abs() < STATION_TOLERANCE_MM
            near &= (remaining["axis_z"] - seed["axis_z"]).abs() < STATION_TOLERANCE_MM
            members = remaining[near]
            stations.append(
                {
                    "side": side,
                    "axis_y_mm": float(seed["axis_y"]),
                    "axis_z_mm": float(seed["axis_z"]),
                    "max_round_diameter_mm": float(seed["dy"]),
                    "width_x_mm": float(
                        members["bbox_max_x_mm"].max() - members["bbox_min_x_mm"].min()
                    ),
                    "centre_x_mm": float(
                        (members["bbox_max_x_mm"].max() + members["bbox_min_x_mm"].min()) / 2
                    ),
                    "solid_count": len(members),
                    "volume_mm3": float(members["volume_mm3"].sum()),
                }
            )
            remaining = remaining[~near]
    table = pd.DataFrame(stations)
    table["bottom_height_mm"] = (
        table["axis_y_mm"] - table["max_round_diameter_mm"] / 2 - solids["bbox_min_y_mm"].min()
    )
    table["toothed_ring_diameter_mm"] = [
        _toothed_ring(rows, station) for _, station in table.iterrows()
    ]
    table["role"] = table.apply(_wheel_role, axis=1, args=(table,))
    for index, row in table.iterrows():
        table.loc[index, ["axis_x_body_m", "axis_y_body_m", "axis_z_body_m"]] = body_m(
            [row["centre_x_mm"], row["axis_y_mm"], row["axis_z_mm"]]
        )
    return table.sort_values(["side", "axis_z_mm"]).reset_index(drop=True)


def _toothed_ring(rows: pd.DataFrame, station: pd.Series) -> float:
    """Largest nearly-round (not round) coaxial solid, e.g. sprocket teeth; NaN if none."""
    out_of_round = (rows["dy"] - rows["dz"]).abs()
    coaxial = rows[
        (rows["side"] == station["side"])
        & ((rows["axis_y"] - station["axis_y_mm"]).abs() < STATION_TOLERANCE_MM)
        & ((rows["axis_z"] - station["axis_z_mm"]).abs() < STATION_TOLERANCE_MM)
        & (out_of_round >= ROUND_TOLERANCE_MM)
        & (out_of_round < 5.0)
        & (rows["dx"] < SHOE_MIN_WIDTH_MM)
    ]
    return float(coaxial[["dy", "dz"]].max(axis=1).max()) if len(coaxial) else float("nan")


def _wheel_role(row: pd.Series, table: pd.DataFrame) -> str:
    """Heuristic role (inferred from size and position, not from names)."""
    same_side = table[table["side"] == row["side"]]
    if row["max_round_diameter_mm"] >= 400:
        end = "front (+Z_cad)" if row["axis_z_mm"] > 0 else "rear (-Z_cad)"
        return f"end wheel {end}: idler or sprocket"
    similar = same_side[
        ((same_side["max_round_diameter_mm"] - row["max_round_diameter_mm"]).abs() < 2)
        & ((same_side["axis_y_mm"] - row["axis_y_mm"]).abs() < 2)
    ]
    end_axis_y = same_side.loc[same_side["max_round_diameter_mm"] >= 400, "axis_y_mm"].mean()
    if len(similar) >= 3:
        lower = row["axis_y_mm"] < end_axis_y
        return "track roller (lower run)" if lower else "carrier roller (upper run)"
    return "other round part"


# --------------------------------------------------------------------------
# C8: collision and visual shapes
# --------------------------------------------------------------------------
def _mesh_solids(solid_shapes: list, work: Path, name: str) -> trimesh.Trimesh:
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    for solid in solid_shapes:
        builder.Add(compound, solid)
    BRepMesh_IncrementalMesh(compound, MESH_LINEAR_MM, False, MESH_ANGULAR_RAD, True)
    path = work / f"{name}.stl"
    writer = StlAPI_Writer()
    writer.SetASCIIMode(False)
    if not writer.Write(compound, str(path)):
        raise RuntimeError(f"STL write failed for {name}")
    return trimesh.load_mesh(str(path), file_type="stl", process=True)


def _lowres_mesh(members: pd.DataFrame, solid_shapes: list, work: Path):
    """Decimated meshes of the largest solids (already meshed by the group pass)."""
    ordered = members.sort_values("volume_mm3", ascending=False)
    share = ordered["volume_mm3"].cumsum() / ordered["volume_mm3"].sum()
    kept = ordered[(share.shift(fill_value=0.0) < LOWRES_VOLUME_SHARE)]
    writer = StlAPI_Writer()
    writer.SetASCIIMode(False)
    path = work / "solid.stl"
    parts = []
    for index in kept["solid"]:
        if not writer.Write(solid_shapes[index], str(path)):
            continue
        mesh = trimesh.load_mesh(str(path), file_type="stl", process=True)
        vertices, faces = fast_simplification.simplify(
            mesh.vertices, mesh.faces, target_reduction=LOWRES_TARGET_REDUCTION
        )
        parts.append(trimesh.Trimesh(vertices, faces, process=False))
    return trimesh.util.concatenate(parts), len(kept), float(kept["volume_mm3"].sum())


def _bbox_record(bounds: np.ndarray) -> dict:
    return {
        "min_mm": bounds[0].round(3).tolist(),
        "max_mm": bounds[1].round(3).tolist(),
        "centre_mm": ((bounds[0] + bounds[1]) / 2).round(3).tolist(),
        "half_extents_mm": ((bounds[1] - bounds[0]) / 2).round(3).tolist(),
        "centre_body_m": body_m((bounds[0] + bounds[1]) / 2),
        "half_extents_body_m": (CAD_TO_BODY @ ((bounds[1] - bounds[0]) / 2) / MM_PER_M)
        .round(6)
        .tolist(),
    }


def collision_shapes(solids: pd.DataFrame, solid_shapes: list) -> tuple[dict, dict]:
    """Hull per track, boxes and decimated meshes; returns report and meshes to write."""
    report: dict = {
        "mesh": {
            "mesher": "BRepMesh_IncrementalMesh (absolute deflection)",
            "linear_deflection_mm": MESH_LINEAR_MM,
            "angular_deflection_rad": MESH_ANGULAR_RAD,
        },
        "groups": {},
    }
    outputs: dict[str, trimesh.Trimesh] = {}
    lowres_parts = []
    with tempfile.TemporaryDirectory() as work_dir:
        for side in ("left", "right", "center"):
            members = solids[solids["side"] == side]
            mesh = _mesh_solids([solid_shapes[i] for i in members["solid"]], Path(work_dir), side)
            brep_volume = float(members["volume_mm3"].sum())
            brep_bounds = np.array(
                [
                    members[list(_BOX_COLUMNS[:3])].min().to_numpy(),
                    members[list(_BOX_COLUMNS[3:])].max().to_numpy(),
                ]
            )
            lowres, kept, kept_volume = _lowres_mesh(members, solid_shapes, Path(work_dir))
            lowres_parts.append(lowres)
            entry = {
                "solid_count": len(members),
                "brep_volume_mm3": brep_volume,
                "brep_bbox": _bbox_record(brep_bounds),
                "fine_mesh": {
                    "faces": len(mesh.faces),
                    "volume_mm3": float(mesh.volume),
                    "volume_rel_to_brep": float(mesh.volume / brep_volume - 1),
                    "bbox_abs_diff_mm": float(np.abs(mesh.bounds - brep_bounds).max()),
                },
                "lowres_mesh": {
                    "method": "per-solid quadric decimation of the largest solids",
                    "volume_share": LOWRES_VOLUME_SHARE,
                    "target_reduction": LOWRES_TARGET_REDUCTION,
                    "solids_kept": kept,
                    "kept_brep_volume_mm3": kept_volume,
                    "solids_dropped": len(members) - kept,
                    "faces": len(lowres.faces),
                    "watertight": bool(lowres.is_watertight),
                    "volume_mm3": float(lowres.volume),
                    "volume_rel_to_brep": float(lowres.volume / brep_volume - 1),
                    "volume_rel_to_kept_brep": float(lowres.volume / kept_volume - 1),
                    "bbox_abs_diff_mm": float(np.abs(lowres.bounds - brep_bounds).max()),
                },
            }
            if side != "center":
                hull = mesh.convex_hull
                outputs[f"track_{side}_hull.obj"] = hull
                entry["convex_hull"] = {
                    "file": f"track_{side}_hull.obj",
                    "faces": len(hull.faces),
                    "volume_mm3": float(hull.volume),
                    "volume_ratio_to_brep": float(hull.volume / brep_volume),
                    "bbox_abs_diff_mm": float(np.abs(hull.bounds - brep_bounds).max()),
                }
                box_volume = float(np.prod(brep_bounds[1] - brep_bounds[0]))
                entry["box"] = {
                    **_bbox_record(brep_bounds),
                    "volume_ratio_to_brep": box_volume / brep_volume,
                }
            report["groups"][side] = entry
            log(f"  meshed {side}: {len(mesh.faces)} faces -> lowres {len(lowres.faces)}")
    outputs["crawler_lowres.obj"] = trimesh.util.concatenate(lowres_parts)
    report["lowres_file"] = "crawler_lowres.obj"
    return report, outputs


# --------------------------------------------------------------------------
# C5: face statistics
# --------------------------------------------------------------------------
def face_statistics(faces: pd.DataFrame, solids: pd.DataFrame) -> dict:
    side_by_solid = solids.set_index("solid")["side"]
    sides = side_by_solid.loc[faces["solid"]].to_numpy()
    total = len(faces)
    bands = {
        f"<= {band} mm": {
            "faces": int((faces["height_mm"] <= band).sum()),
            "share": round(float((faces["height_mm"] <= band).mean()), 5),
        }
        for band in STATS_BANDS_MM
    }
    return {
        "total_faces": total,
        "total_solids": len(solids),
        "faces_by_type": faces["surface_type"].value_counts().to_dict(),
        "faces_by_side": pd.Series(sides).value_counts().to_dict(),
        "faces_by_height_band (lowest point above ground)": bands,
        "faces_per_solid": {
            "median": float(faces.groupby("solid").size().median()),
            "max": int(faces.groupby("solid").size().max()),
        },
        "recommendation": (
            "C5 face index: for the crawler keep only faces whose lowest point is within "
            "50 mm of the ground (contact candidates) plus the downward grouser tip planes; "
            "the rest (wheels, links, pins, frame) is not a mounting or ground surface"
        ),
    }


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------
def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    frame.to_csv(path, index=False, encoding="utf-8-sig", float_format="%.6f")


def _write_obj(path: Path, mesh: trimesh.Trimesh) -> None:
    text = trimesh.exchange.obj.export_obj(mesh, include_normals=False, digits=3)
    header = "# CAD world frame, mm, Y up (crawler placement applied)\n"
    path.write_text(header + text, encoding="utf-8")


def provenance(instance) -> dict:
    row = next(r for r in brep_cache.prototypes() if r["prototype_entry"] == CRAWLER_ENTRY)
    script = Path(__file__).resolve()
    return {
        "source_prototype_entry": CRAWLER_ENTRY,
        "source_instance_path": instance.instance_path,
        "source_file": f"01_cad/06_brep/prototypes/{row['prototype_file']}",
        "source_sha256": row["sha256"],
        "placement_world_from_prototype": np.asarray(instance.matrix).reshape(3, 4).tolist(),
        "generator": script.relative_to(PROJECT_ROOT).as_posix(),
        "generator_sha256": sha256_file(script),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "note": "Crawler model is described as REXOME25 (another machine) in the STEP file",
    }


def main() -> None:
    started_s = time.perf_counter()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("", encoding="utf-8")
    instance = brep_cache.instances_of(CRAWLER_ENTRY)[0]
    shape = brep_cache.load_part(instance.instance_path)
    log(f"loaded crawler in {time.perf_counter() - started_s:.1f} s")

    solids, faces, solid_shapes = tabulate(shape)
    ground_y = float(faces["bbox_min_y_mm"].min())
    faces = add_face_details(faces, ground_y)
    log(f"{len(solids)} solids, {len(faces)} faces, ground Y {ground_y:.4f} mm")

    tips = grouser_tips(faces, solids)
    patches = ground_patches(tips)
    wheels = wheel_stations(solids)
    shoes = solids[
        (solids["side"] != "center")
        & (solids["bbox_min_y_mm"] - ground_y < 60)
        & ((solids["bbox_max_x_mm"] - solids["bbox_min_x_mm"]) > 400)
    ]
    centre_1mm = patches["1mm"]
    track_centre = (centre_1mm["left"]["centre_x_mm"] - centre_1mm["right"]["centre_x_mm"]) / 2
    flat_1mm = centre_1mm["left"]["z_range_mm"]
    summary = {
        "provenance": provenance(instance),
        "frames": "CAD world mm (Y up); *_body_m: body axes x=+Z_cad, y=+X_cad, z=+Y_cad, m",
        "ground_y_mm": ground_y,
        "ground_z_body_m": round(ground_y / MM_PER_M, 6),
        "track_centre_half_spacing_mm": track_centre,
        "shoe_ground_width_mm": centre_1mm["left"]["width_mm"],
        "track_overall_length_mm": float(
            solids.loc[solids["side"] != "center", "bbox_max_z_mm"].max()
            - solids.loc[solids["side"] != "center", "bbox_min_z_mm"].min()
        ),
        "ground_shoe_solids": {
            "count": len(shoes),
            "note": "solids wider than 400 mm in X whose lowest point is < 60 mm above ground",
        },
        "shoe_pitch": shoe_pitch(tips),
        "ground_patches_by_band": patches,
        "flat_ground_length_1mm_body_x_m": [round(v / MM_PER_M, 4) for v in flat_1mm],
        "comparison_with_previous_review": {
            **PREVIOUS,
            "now_track_centre_m": round(track_centre / MM_PER_M, 4),
            "now_shoe_ground_width_m": round(centre_1mm["left"]["width_mm"] / MM_PER_M, 4),
            **{
                f"now_flat_length_{band}_m": round(patches[band]["left"]["length_mm"] / MM_PER_M, 4)
                for band in patches
            },
        },
        "wheel_stations_file": "crawler_wheels.csv",
    }
    log("C7 values done; meshing for C8")
    collision, meshes = collision_shapes(solids, solid_shapes)
    collision["provenance"] = summary["provenance"]
    stats = face_statistics(faces, solids)
    stats["provenance"] = summary["provenance"]

    face_columns = [c for c in faces.columns if c != "face"]
    _write_csv(
        OUT_DIR / "crawler_ground_faces.csv",
        faces.loc[faces["height_mm"] <= FACE_LIST_BAND_MM, face_columns],
    )
    _write_csv(
        OUT_DIR / "crawler_grouser_tips.csv", tips[face_columns + ["side", "plane_height_mm"]]
    )
    _write_csv(OUT_DIR / "crawler_wheels.csv", wheels)
    _write_csv(OUT_DIR / "crawler_solids.csv", solids)
    for name, mesh in meshes.items():
        _write_obj(OUT_DIR / name, mesh)
    for name, payload in (
        ("crawler_summary.json", summary),
        ("crawler_collision.json", collision),
        ("crawler_face_stats.json", stats),
    ):
        (OUT_DIR / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=1, default=float), encoding="utf-8"
        )
    peak_gb = psutil.Process().memory_info().peak_wset / 1e9
    log(f"done in {time.perf_counter() - started_s:.0f} s, peak memory {peak_gb:.2f} GB")


if __name__ == "__main__":
    main()
