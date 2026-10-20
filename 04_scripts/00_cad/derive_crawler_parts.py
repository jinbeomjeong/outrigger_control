"""Per-part B-rep files and an index of the crawler contact parts of layout D.

Layout D (CLAUDE.md '크롤러 접촉 배치', ``02_params/rexome33.yaml``
``contact.crawler.sphere_layout``) puts contact points at the six lower track
rollers of each track (gap 0) and at three raised end shoes per track end
(gapped). This script finds, per track side, the solids that make up

* each lower track roller (``roller``, 6 per side): the solids inside the
  roller station box (wheel, shaft, end brackets, mounting bolts, washers),
* each end shoe (``end_shoe``, 3 per end, 6 per side) and each flat ground
  shoe (``flat_shoe``, 10 per side): one track pitch unit, i.e. the ground
  shoe with its grouser pads, the shoe plate above it, the link pair bolted to
  the plate, the shoe bolts and nuts, the side blocks and their fasteners,
  and the track joint (pin, bushing, seal discs) nearest to the plate,

writes every part as one compound in a binary B-rep file (CAD world frame,
mm, Y up, crawler placement applied, identity placement), and indexes them in
``crawler_contact_parts.csv`` / ``.json`` (+ the solid membership table
``crawler_contact_part_solids.csv``). Only cache files are read (no STEP):
the crawler prototype ``0:1:1:746`` (``01_cad/06_brep/prototypes``), the
crawler derived cache (``crawler_solids.csv``, ``crawler_wheels.csv``,
``crawler_grouser_tips.csv``, ``crawler_summary.json``), the face index
(``01_cad/07_faces/instance_faces.csv.gz``), ``01_cad/01_parts/
parts_classified.csv`` (density) and the YAML (comparison only).

Shoe unit boundary: the ground shoe of a unit is the solid that carries the
four downward grouser pad planes (area 2108.5 mm^2). Its shoe plate is the
solid of the plate template volume right above it. Every chain solid (side
solid within ``CHAIN_RADIUS_MM`` of a shoe plate centroid, smaller than
``CHAIN_MAX_SIZE_MM``, not in a roller or wheel station) belongs to the shoe
whose plate centroid is nearest in 3D. The distance from a track joint to
its two neighbouring plates does not change when the track bends, so the
rule gives the same 26 solids per pitch on the straight run and around the
end wheels; the script checks that all units have the same volume signature.

Frames: ``*_cad_mm`` = CAD world (mm, Y up); ``*_body_m`` = body axes
(x = +Z_cad, y = +X_cad, z = +Y_cad, CAD origin, m). Side ``L`` = +X_cad =
body +y (left), ``R`` = right. Inertia is about the part centroid; body axes,
kg m^2; density = resolved prototype material (steel 7.85 g/cm^3, from the
parent product name; the crawler has no XCAF material).

Usage:
    python -I 04_scripts/00_cad/derive_crawler_parts.py
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import psutil
import yaml
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRep import BRep_Builder
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
from OCC.Core.GProp import GProp_GProps
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_REVERSED, TopAbs_SOLID
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import TopoDS_Compound, topods

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brep_cache
from cad_common import FACES_DIR, MM_PER_M, PARTS_DIR, PROJECT_ROOT
from check_cache import sha256_file

CRAWLER_ENTRY = "0:1:1:746"
CRAWLER_DIR = brep_cache.DERIVED_DIR / "crawler"
PARTS_OUT_DIR = CRAWLER_DIR / "parts"
INDEX_CSV = CRAWLER_DIR / "crawler_contact_parts.csv"
INDEX_JSON = CRAWLER_DIR / "crawler_contact_parts.json"
SOLIDS_OUT_CSV = CRAWLER_DIR / "crawler_contact_part_solids.csv"
LOG_PATH = CRAWLER_DIR / "derive_parts.log"
YAML_PATH = PROJECT_ROOT / "02_params" / "rexome33.yaml"
PARTS_CLASSIFIED_CSV = PARTS_DIR / "parts_classified.csv"
INSTANCE_FACES = FACES_DIR / "instance_faces.csv.gz"

# CAD -> body axes (x = +Z_cad, y = +X_cad, z = +Y_cad), CAD origin.
CAD_TO_BODY = np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
SIDES = {"L": "left", "R": "right"}

# Roller station box around a 'track roller' axis of crawler_wheels.csv (CAD mm).
ROLLER_ROLE = "track roller"
ROLLER_HALF_X_MM = 200.0  # across the track, from the station centre
ROLLER_HALF_Z_MM = 100.0  # along the track, from the axis
ROLLER_BOTTOM_TOL_MM = 1.0  # below the wheel bottom and above the wheel top
# Shoe units.
GROUSER_PAD_AREA_MM2 = 2108.515681  # same as export_params.py
GROUSER_PAD_AREA_TOL_MM2 = 1.0
GROUSER_PADS_PER_SHOE = 4
GROUND_SELECTIONS = ("ground_band", "grouser_tip")  # face index selections near the ground
FLAT_SHOE_TOL_MM = 1e-3  # lowest grouser point <= this above the floor = flat shoe
END_SHOES_PER_END = 3
TEMPLATE_VOLUME_REL_TOL = 1e-6  # same prototype solid repeated along the chain
PLATE_SEARCH_MM = 150.0  # shoe plate centroid within this of the ground shoe centroid
CHAIN_RADIUS_MM = 350.0  # chain solid candidates: centroid this close to a plate
CHAIN_MAX_SIZE_MM = 700.0  # bbox diagonal of a chain solid (shoe 600 mm wide)
# Checks.
YAML_X_DIGITS = 4  # export_params.py CRAWLER_X_DIGITS
YAML_GAP_DIGITS = 5  # export_params.py CRAWLER_GAP_DIGITS
SYMMETRY_TOL_MM = 0.01
SYMMETRY_VOLUME_REL_TOL = 1e-5  # right-side shoe solids differ by ~5e-7 .. 3e-6 (CAD)
SUM_VOLUME_REL_TOL = 1e-9

BOX_KEYS = ("min_x", "min_y", "min_z", "max_x", "max_y", "max_z")


def log(message: str) -> None:
    rss_gb = psutil.Process().memory_info().rss / 1e9
    line = f"[{time.strftime('%H:%M:%S')} | rss {rss_gb:5.2f} GB] {message}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def to_body(vector_cad_mm) -> np.ndarray:
    return CAD_TO_BODY @ np.asarray(vector_cad_mm, dtype=float) / MM_PER_M


def bbox(shape) -> np.ndarray:
    box = Bnd_Box()
    brepbndlib.AddOptimal(shape, box, False, False)
    return np.array(box.Get())


def make_compound(shapes) -> TopoDS_Compound:
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    for shape in shapes:
        builder.Add(compound, shape)
    return compound


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------
def load_solids(shape) -> tuple[list, np.ndarray]:
    """Solids in TopExp order (= crawler_solids.csv ``solid``) and their first face index.

    ``face_start[i]`` is the index of the first face of solid ``i`` in
    ``TopExp_Explorer(prototype, TopAbs_FACE)`` order (= face index
    ``face_index``); the faces of a solid are contiguous.
    """
    solids, counts = [], []
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    while explorer.More():
        solid = topods.Solid(explorer.Current())
        explorer.Next()
        solids.append(solid)
        count = 0
        face_explorer = TopExp_Explorer(solid, TopAbs_FACE)
        while face_explorer.More():
            count += 1
            face_explorer.Next()
        counts.append(count)
    counts = np.asarray(counts)
    return solids, np.concatenate([[0], np.cumsum(counts)])


def crawler_density() -> tuple[float, str]:
    table = pd.read_csv(PARTS_CLASSIFIED_CSV, encoding="utf-8-sig", low_memory=False)
    row = table[table["prototype_entry"] == CRAWLER_ENTRY].iloc[0]
    source = f"{row['material_resolved']} ({row['density_source']}, parts_classified.csv)"
    return float(row["density_step_g_cm3"]), source


def yaml_layout() -> dict:
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    return data["contact"]["crawler"]["sphere_layout"]


# --------------------------------------------------------------------------
# Identification
# --------------------------------------------------------------------------
def roller_parts(solids: pd.DataFrame, wheels: pd.DataFrame) -> list[dict]:
    """Solids fully inside each lower roller station box, per side, ascending body x."""
    parts = []
    rollers = wheels[wheels["role"].str.startswith(ROLLER_ROLE)]
    for code, side in SIDES.items():
        rows = rollers[rollers["side"] == side].sort_values("axis_z_mm")
        for order, station in enumerate(rows.itertuples()):
            bottom = station.axis_y_mm - station.max_round_diameter_mm / 2
            top = station.axis_y_mm + station.max_round_diameter_mm / 2
            inside = (
                (solids["side"] == side)
                & (solids["bbox_min_x_mm"] >= station.centre_x_mm - ROLLER_HALF_X_MM)
                & (solids["bbox_max_x_mm"] <= station.centre_x_mm + ROLLER_HALF_X_MM)
                & (solids["bbox_min_y_mm"] >= bottom - ROLLER_BOTTOM_TOL_MM)
                & (solids["bbox_max_y_mm"] <= top + ROLLER_BOTTOM_TOL_MM)
                & (solids["bbox_min_z_mm"] >= station.axis_z_mm - ROLLER_HALF_Z_MM)
                & (solids["bbox_max_z_mm"] <= station.axis_z_mm + ROLLER_HALF_Z_MM)
            )
            parts.append(
                {
                    "kind": "roller",
                    "side": code,
                    "order_index": order,
                    "solids": sorted(solids.loc[inside, "solid"].tolist()),
                    "station": station._asdict(),
                }
            )
    return parts


def _same_volume(solids: pd.DataFrame, volume: float) -> pd.Series:
    return (solids["volume_mm3"] / volume - 1).abs() < TEMPLATE_VOLUME_REL_TOL


def _matches_any(volumes: np.ndarray, template: np.ndarray) -> np.ndarray:
    """True where a volume equals one of the template volumes (relative tolerance)."""
    relative = np.abs(volumes[:, None] / template[None, :] - 1)
    return relative.min(axis=1) < TEMPLATE_VOLUME_REL_TOL


def shoe_parts(solids: pd.DataFrame, tips: pd.DataFrame, ground_y: float, taken: set) -> tuple:
    """End and flat ground shoe units per side and the data of the unit rule.

    1. Ground shoes = solids carrying the grouser pad planes; shoe plates =
       solids with the plate template volume (the biggest same-width solid
       right above a ground shoe).
    2. Candidates = side solids near a plate, smaller than a shoe, inside the
       run of chain blocks in the solid order (ground shoes repeat every
       period solids; +- one period), not in a roller station; each goes
       to its nearest plate (3D centroid distance).
    3. The unit of the middle flat shoe gives the chain template (volumes);
       candidates whose volume is not in the template (end wheel, frame
       pieces) are dropped and the assignment is repeated.
    """
    pads = tips[(tips["area_mm2"] - GROUSER_PAD_AREA_MM2).abs() < GROUSER_PAD_AREA_TOL_MM2]
    centroids = solids[["centroid_x_mm", "centroid_y_mm", "centroid_z_mm"]].to_numpy()
    parts, rule = [], {}
    for code, side in SIDES.items():
        side_solids = solids[solids["side"] == side]
        side_ids = side_solids["solid"].to_numpy()
        side_volumes = side_solids["volume_mm3"].to_numpy()
        side_pads = pads[pads["side"] == side]
        ground_ids = sorted(
            side_pads["solid"].unique(),
            key=lambda s: side_pads.loc[side_pads["solid"] == s, "centroid_z_mm"].mean(),
        )
        middle = ground_ids[len(ground_ids) // 2]
        width = solids.loc[middle, "bbox_max_x_mm"] - solids.loc[middle, "bbox_min_x_mm"]
        near = side_solids[
            (np.linalg.norm(centroids[side_ids] - centroids[middle], axis=1) < PLATE_SEARCH_MM)
            & (side_solids["solid"] != middle)
            & ((side_solids["bbox_max_x_mm"] - side_solids["bbox_min_x_mm"]) - width).abs().lt(1.0)
        ]
        plate_template = near.sort_values("volume_mm3").iloc[-1]
        plates = side_solids[_same_volume(side_solids, plate_template["volume_mm3"])]
        ground_shoes = side_solids[_same_volume(side_solids, solids.loc[middle, "volume_mm3"])]
        plate_ids = plates["solid"].to_numpy()
        plate_xyz = centroids[plate_ids]
        size = np.linalg.norm(
            side_solids[["bbox_max_x_mm", "bbox_max_y_mm", "bbox_max_z_mm"]].to_numpy()
            - side_solids[["bbox_min_x_mm", "bbox_min_y_mm", "bbox_min_z_mm"]].to_numpy(),
            axis=1,
        )
        distance = np.linalg.norm(centroids[side_ids][:, None, :] - plate_xyz[None, :, :], axis=2)
        order = np.argsort(distance, axis=1)
        rows = np.arange(len(distance))
        nearest, second = distance[rows, order[:, 0]], distance[rows, order[:, 1]]
        owner = plate_ids[order[:, 0]]
        # The chain is a run of identical blocks in the solid order (one block per pitch);
        # keep candidates inside that run (+- one block) to drop look-alike frame washers.
        shoe_order = np.sort(ground_shoes["solid"].to_numpy())
        period = int(np.median(np.diff(shoe_order)))
        in_run = (side_ids >= shoe_order[0] - period) & (side_ids <= shoe_order[-1] + period)
        candidate = (
            (nearest < CHAIN_RADIUS_MM)
            & (size < CHAIN_MAX_SIZE_MM)
            & in_run
            & ~np.isin(side_ids, list(taken))
        )

        plate_of = {
            int(g): int(plate_ids[np.argmin(np.linalg.norm(plate_xyz - centroids[g], axis=1))])
            for g in ground_ids
        }
        template = np.sort(side_volumes[candidate & (owner == plate_of[middle])])
        dropped = candidate & ~_matches_any(side_volumes, template)
        candidate &= ~dropped
        margins = []
        for ground_id in ground_ids:
            plate_id = plate_of[int(ground_id)]
            member_mask = candidate & (owner == plate_id)
            margins.append(float(np.min(second[member_mask] - nearest[member_mask])))
            planes = side_pads[side_pads["solid"] == ground_id]
            parts.append(
                {
                    "kind": "shoe",
                    "side": code,
                    "solids": sorted(int(s) for s in side_ids[member_mask]),
                    "ground_shoe_solid": int(ground_id),
                    "plate_solid": plate_id,
                    "grouser_planes": planes,
                    "station_x_cad_mm": float(planes["centroid_z_mm"].mean()),
                    "grouser_lowest_mm": float(planes["bbox_min_y_mm"].min() - ground_y),
                    "template_volumes": template,
                }
            )
        rule[side] = {
            "template_from_ground_shoe_solid": int(middle),
            "template_solid_count": len(template),
            "ground_shoe_volume_mm3": float(solids.loc[middle, "volume_mm3"]),
            "plate_template_solid": int(plate_template["solid"]),
            "plate_volume_mm3": float(plate_template["volume_mm3"]),
            "plates_on_side": len(plates),
            "ground_shoes_on_side": len(ground_shoes),
            "chain_block_period_solids": period,
            "chain_solid_range": [int(shoe_order[0] - period), int(shoe_order[-1] + period)],
            "chain_candidates_kept": int(candidate.sum()),
            "candidates_dropped_not_in_template": int(dropped.sum()),
            "min_assignment_margin_mm": float(min(margins)),
            "margin_note": "second-nearest minus nearest plate distance over the members",
        }
    _name_shoes(parts)
    return parts, rule


def _name_shoes(parts: list[dict]) -> None:
    """flat (gap 0) vs end shoe, ascending body x; end shoes keep the YAML order."""
    for code in SIDES:
        side_parts = sorted(
            (p for p in parts if p["side"] == code), key=lambda p: p["station_x_cad_mm"]
        )
        end = [p for p in side_parts if p["grouser_lowest_mm"] > FLAT_SHOE_TOL_MM]
        flat = [p for p in side_parts if p["grouser_lowest_mm"] <= FLAT_SHOE_TOL_MM]
        for order, part in enumerate(end):
            part["kind"] = "end_shoe"
            part["order_index"] = order
            part["end"] = "rear" if part["station_x_cad_mm"] < 0 else "front"
        for order, part in enumerate(flat):
            part["kind"] = "flat_shoe"
            part["order_index"] = order


# --------------------------------------------------------------------------
# Geometry of one part
# --------------------------------------------------------------------------
def mass_properties(solid_list, density_g_cm3: float) -> dict:
    """Mass properties of a set of solids, summed per solid (GProp_GProps.Add).

    VolumeProperties of the whole compound differs from the per-solid sum
    by up to ~2e-6 relative here (integration far from the origin); the per-solid
    sum matches crawler_solids.csv to ~1e-12, so it is used.
    """
    properties = GProp_GProps()
    for solid in solid_list:
        item = GProp_GProps()
        brepgprop.VolumeProperties(solid, item)
        properties.Add(item, 1.0)
    volume = properties.Mass()
    centre = properties.CentreOfMass()
    com_cad = np.array([centre.X(), centre.Y(), centre.Z()])
    matrix = properties.MatrixOfInertia()
    inertia_cad = np.array([[matrix.Value(i, j) for j in (1, 2, 3)] for i in (1, 2, 3)])
    kg_per_mm3 = density_g_cm3 * 1e-6
    inertia_body = CAD_TO_BODY @ inertia_cad @ CAD_TO_BODY.T * kg_per_mm3 * 1e-6  # kg m^2
    return {
        "volume_mm3": volume,
        "mass_kg": volume * kg_per_mm3,
        "com_cad_mm": com_cad,
        "com_body_m": to_body(com_cad),
        "inertia_body_kg_m2": inertia_body,
        "principal_kg_m2": np.linalg.eigvalsh(inertia_body),
    }


def roller_geometry(wheel) -> dict:
    """Tread: largest convex cylinder about X_cad of the wheel solid (exact surface data)."""
    cylinders = []
    explorer = TopExp_Explorer(wheel, TopAbs_FACE)
    index = 0
    while explorer.More():
        face = topods.Face(explorer.Current())
        explorer.Next()
        surface = BRepAdaptor_Surface(face, True)
        if surface.GetType() == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            axis = cylinder.Axis()
            direction = np.array([axis.Direction().X(), axis.Direction().Y(), axis.Direction().Z()])
            if abs(abs(direction[0]) - 1) < 1e-9:
                location = cylinder.Location()
                box = bbox(face)
                cylinders.append(
                    {
                        "local_face": index,
                        "radius_mm": cylinder.Radius(),
                        "axis_point_cad_mm": np.array([location.X(), location.Y(), location.Z()]),
                        "x_range_mm": (box[0], box[3]),
                        "reversed": face.Orientation() == TopAbs_REVERSED,
                    }
                )
        index += 1
    radius = max(c["radius_mm"] for c in cylinders)
    tread = [c for c in cylinders if abs(c["radius_mm"] - radius) < 1e-6]
    x0 = min(c["x_range_mm"][0] for c in tread)
    x1 = max(c["x_range_mm"][1] for c in tread)
    point = tread[0]["axis_point_cad_mm"]
    return {
        "tread_faces_local": [c["local_face"] for c in tread],
        "radius_mm": radius,
        "width_mm": x1 - x0,
        "axis_point_cad_mm": np.array([(x0 + x1) / 2, point[1], point[2]]),
        "axis_dir_cad": np.array([1.0, 0.0, 0.0]),
        "cylinder_radii_mm": sorted({round(c["radius_mm"], 3) for c in cylinders}),
    }


def ground_plane_geometry(faces: list[dict]) -> dict:
    """Area, area-weighted outward normal (body) and tilt of the grouser pad planes."""
    normals = np.array([face["normal_cad"] for face in faces])
    weights = np.array([face["area_mm2"] for face in faces])
    mean = (normals * weights[:, None]).sum(axis=0)
    mean /= np.linalg.norm(mean)
    normal_body = CAD_TO_BODY @ mean
    return {
        "area_mm2": float(weights.sum()),
        "normal_body": normal_body,
        "tilt_deg": float(np.degrees(np.arccos(np.clip(-normal_body[2], -1, 1)))),
    }


def face_ranges(solid_ids: list[int], face_start: np.ndarray) -> list[tuple[int, int]]:
    """Merged half-open face index ranges [start, stop) of the solids."""
    ranges: list[list[int]] = []
    for solid in sorted(solid_ids):
        start, stop = int(face_start[solid]), int(face_start[solid + 1])
        if ranges and ranges[-1][1] == start:
            ranges[-1][1] = stop
        else:
            ranges.append([start, stop])
    return [tuple(r) for r in ranges]


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def part_id(part: dict) -> str:
    width = 2 if part["kind"] == "flat_shoe" else 1
    return f"{part['kind']}_{part['side']}{part['order_index'] + 1:0{width}d}"


def describe(part: dict, shape, solid_shapes, face_start, density, ground_y, layout) -> dict:
    props = mass_properties([solid_shapes[s] for s in part["solids"]], density)
    whole = GProp_GProps()
    brepgprop.VolumeProperties(shape, whole)
    box = bbox(shape)
    box_body = np.sort(np.stack([to_body(box[:3]), to_body(box[3:])]), axis=0)
    ranges = face_ranges(part["solids"], face_start)
    row = {
        "part_id": part["id"],
        "kind": part["kind"],
        "side": part["side"],
        "end": part.get("end", ""),
        "order_index": part["order_index"],
        "yaml_key": {
            "roller": "roller_x_m",
            "end_shoe": "end_shoe_x_m",
        }.get(part["kind"], ""),
        "yaml_index": part["order_index"] if part["kind"] in ("roller", "end_shoe") else "",
        "solid_count": len(part["solids"]),
        "solids": ";".join(str(s) for s in part["solids"]),
        "file": part["file"].relative_to(PROJECT_ROOT).as_posix(),
        "file_bytes": part["file"].stat().st_size,
        "sha256": sha256_file(part["file"]),
        "density_g_cm3": density,
        "volume_mm3": props["volume_mm3"],
        "mass_kg": props["mass_kg"],
        "compound_volume_rel_diff": whole.Mass() / props["volume_mm3"] - 1,
    }
    for axis, value in zip("xyz", props["com_cad_mm"], strict=True):
        row[f"com_{axis}_cad_mm"] = value
    for axis, value in zip("xyz", props["com_body_m"], strict=True):
        row[f"com_{axis}_body_m"] = value
    inertia = props["inertia_body_kg_m2"]
    for name, (i, j) in {
        "xx": (0, 0),
        "yy": (1, 1),
        "zz": (2, 2),
        "xy": (0, 1),
        "xz": (0, 2),
        "yz": (1, 2),
    }.items():
        row[f"I{name}_body_kg_m2"] = inertia[i, j]
    for k, value in enumerate(props["principal_kg_m2"], start=1):
        row[f"I{k}_principal_kg_m2"] = value
    for key, value in zip(BOX_KEYS, box, strict=True):
        row[f"bbox_{key}_cad_mm"] = value
    for key, value in zip(BOX_KEYS, box_body.ravel(), strict=True):
        row[f"bbox_{key}_body_m"] = value
    row["lowest_above_ground_mm"] = box[1] - ground_y
    row["face_count"] = sum(stop - start for start, stop in ranges)
    row["face_ranges"] = ";".join(f"{a}-{b - 1}" for a, b in ranges)
    if part["kind"] == "roller":
        wheel = max(part["solids"], key=lambda s: part["volumes"][s])
        geometry = roller_geometry(solid_shapes[wheel])
        axis_body = to_body(geometry["axis_point_cad_mm"])
        row.update(
            {
                "roller_wheel_solid": wheel,
                "roller_axis_x_body_m": axis_body[0],
                "roller_axis_y_body_m": axis_body[1],
                "roller_axis_z_body_m": axis_body[2],
                "roller_axis_dir_body": "0 1 0",
                "roller_radius_mm": geometry["radius_mm"],
                "roller_width_mm": geometry["width_mm"],
                "roller_bottom_above_ground_mm": geometry["axis_point_cad_mm"][1]
                - geometry["radius_mm"]
                - ground_y,
                "roller_tread_face_indices": ";".join(
                    str(int(face_start[wheel]) + f) for f in geometry["tread_faces_local"]
                ),
                "station_x_body_m": axis_body[0],
                "yaml_value": layout["roller_x_m"][part["order_index"]],
                "station_x_rounded": round(axis_body[0], YAML_X_DIGITS),
            }
        )
    else:
        plane = ground_plane_geometry(part["grouser_faces"])
        gap_m = part["grouser_lowest_mm"] / MM_PER_M
        row.update(
            {
                "ground_shoe_solid": part["ground_shoe_solid"],
                "shoe_plate_solid": part["plate_solid"],
                "station_x_body_m": part["station_x_cad_mm"] / MM_PER_M,
                "grouser_lowest_above_ground_mm": part["grouser_lowest_mm"],
                "gap_m": gap_m,
                "ground_face_area_mm2": plane["area_mm2"],
                "ground_normal_x_body": plane["normal_body"][0],
                "ground_normal_y_body": plane["normal_body"][1],
                "ground_normal_z_body": plane["normal_body"][2],
                "ground_tilt_deg": plane["tilt_deg"],
                "ground_face_indices": ";".join(
                    str(int(face_start[part["ground_shoe_solid"]]) + int(f))
                    for f in (face["local_face"] for face in part["grouser_faces"])
                ),
                "station_x_rounded": round(part["station_x_cad_mm"] / MM_PER_M, YAML_X_DIGITS),
            }
        )
        if part["kind"] == "end_shoe":
            row["yaml_value"] = layout["end_shoe_x_m"][part["order_index"]]
            row["yaml_gap_m"] = layout["end_shoe_gap_m"][part["order_index"]]
            row["gap_rounded_m"] = round(gap_m, YAML_GAP_DIGITS)
    return row


def grouser_faces(ground_solid, planes: pd.DataFrame) -> list[dict]:
    """Grouser pad planes of a ground shoe: local face number, area, outward normal (CAD).

    Matched to the ``crawler_grouser_tips.csv`` rows by centroid; the outward
    normal is XDir x YDir of the plane, negated for a REVERSED face.
    """
    found = []
    explorer = TopExp_Explorer(ground_solid, TopAbs_FACE)
    index = 0
    targets = planes[["centroid_x_mm", "centroid_y_mm", "centroid_z_mm"]].to_numpy()
    while explorer.More():
        face = topods.Face(explorer.Current())
        explorer.Next()
        surface = BRepAdaptor_Surface(face, True)
        if surface.GetType() == GeomAbs_Plane:
            properties = GProp_GProps()
            brepgprop.SurfaceProperties(face, properties)
            centre = properties.CentreOfMass()
            point = np.array([centre.X(), centre.Y(), centre.Z()])
            if (
                abs(properties.Mass() - GROUSER_PAD_AREA_MM2) < GROUSER_PAD_AREA_TOL_MM2
                and np.min(np.linalg.norm(targets - point, axis=1)) < 1e-3
            ):
                position = surface.Plane().Position()
                x_dir, y_dir = position.XDirection(), position.YDirection()
                normal = np.cross(
                    [x_dir.X(), x_dir.Y(), x_dir.Z()], [y_dir.X(), y_dir.Y(), y_dir.Z()]
                )
                if face.Orientation() == TopAbs_REVERSED:
                    normal = -normal
                found.append(
                    {"local_face": index, "area_mm2": properties.Mass(), "normal_cad": normal}
                )
        index += 1
    return found


def verify(
    rows: pd.DataFrame,
    parts: list[dict],
    solids: pd.DataFrame,
    face_start,
    layout,
    summary: dict,
    shapes: dict,
) -> dict:
    checks: dict = {}
    # YAML correspondence.
    yaml_rows = rows[rows["kind"].isin(["roller", "end_shoe"])]
    checks["yaml_x_rounded_equal"] = {
        "rows": len(yaml_rows),
        "mismatches": int((yaml_rows["station_x_rounded"] != yaml_rows["yaml_value"]).sum()),
        "max_abs_exact_minus_yaml_m": float(
            (yaml_rows["station_x_body_m"] - yaml_rows["yaml_value"]).abs().max()
        ),
    }
    end = rows[rows["kind"] == "end_shoe"]
    checks["yaml_gap_rounded_equal"] = {
        "rows": len(end),
        "mismatches": int((end["gap_rounded_m"] != end["yaml_gap_m"]).sum()),
        "max_abs_exact_minus_yaml_m": float((end["gap_m"] - end["yaml_gap_m"]).abs().max()),
    }
    roller = rows[rows["kind"] == "roller"]
    checks["roller_abs_y_vs_track_centre"] = {
        "yaml_track_centre_y_m": layout["track_centre_y_m"],
        "max_abs_rounded_diff_m": float(
            (roller["roller_axis_y_body_m"].abs().round(YAML_X_DIGITS) - layout["track_centre_y_m"])
            .abs()
            .max()
        ),
        "max_abs_exact_diff_m": float(
            (roller["roller_axis_y_body_m"].abs() - layout["track_centre_y_m"]).abs().max()
        ),
    }
    checks["counts"] = rows.groupby(["kind", "side"]).size().to_dict()
    checks["counts"] = {f"{k[0]}_{k[1]}": int(v) for k, v in checks["counts"].items()}
    checks["counts_expected"] = {"roller": 6, "end_shoe": 6, "flat_shoe": 10, "per_side": True}
    end_per_end = end.groupby(["side", "end"]).size()
    checks["end_shoes_per_end"] = {f"{k[0]}_{k[1]}": int(v) for k, v in end_per_end.items()}
    # Disjoint solid sets.
    all_ids = [s for p in parts for s in p["solids"]]
    checks["solid_sets_disjoint"] = {
        "solids": len(all_ids),
        "unique": len(set(all_ids)),
        "pass": len(all_ids) == len(set(all_ids)),
    }
    # Volume of each compound vs the sum of crawler_solids.csv volumes.
    volume = solids.set_index("solid")["volume_mm3"]
    rel = []
    for p in parts:
        read_back = brep_cache.read_brep(p["file"])
        explorer = TopExp_Explorer(read_back, TopAbs_SOLID)
        read_solids = []
        while explorer.More():
            read_solids.append(topods.Solid(explorer.Current()))
            explorer.Next()
        read_volume = mass_properties(read_solids, 1.0)["volume_mm3"]
        rel.append(abs(read_volume / volume.loc[p["solids"]].sum() - 1))
    checks["volume_vs_solid_sum"] = {
        "max_rel": float(max(rel)),
        "tol": SUM_VOLUME_REL_TOL,
        "pass": max(rel) <= SUM_VOLUME_REL_TOL,
        "compound_volume_properties_max_rel": float(rows["compound_volume_rel_diff"].abs().max()),
        "note": "volume_mm3 = per-solid sum (GProp Add) of the solids read back from the part; "
        "compound_volume_properties = VolumeProperties of the whole compound (info)",
    }
    # Same composition: every shoe unit = the chain template of its side, every
    # roller = the first roller of its side (sorted solid volumes, relative tolerance).
    mismatched = []
    for p in parts:
        own = np.sort(volume.loc[p["solids"]].to_numpy())
        if p["kind"] == "roller":
            first = next(q for q in parts if q["kind"] == "roller" and q["side"] == p["side"])
            reference = np.sort(volume.loc[first["solids"]].to_numpy())
        else:
            reference = p["template_volumes"]
        same = len(own) == len(reference) and np.all(
            np.abs(own / reference - 1) < TEMPLATE_VOLUME_REL_TOL
        )
        if not same:
            mismatched.append(p["id"])
    checks["same_composition"] = {
        "roller_solids": sorted({len(p["solids"]) for p in parts if p["kind"] == "roller"}),
        "shoe_solids": sorted({len(p["solids"]) for p in parts if p["kind"] != "roller"}),
        "mismatched_parts": mismatched,
        "pass": not mismatched,
    }
    # Re-read files: vertices.
    vertex = []
    for p in parts:
        written = brep_cache.shape_vertices(shapes[p["id"]])
        read = brep_cache.shape_vertices(brep_cache.read_brep(p["file"]))
        same_shape = written.shape == read.shape
        vertex.append(float(np.abs(written - read).max()) if same_shape else np.inf)
    checks["reread_vertex_max_abs_mm"] = max(vertex)
    # Left-right symmetry (mirror X_cad).
    pairs = rows.set_index(["kind", "order_index", "side"])
    diffs = {
        "volume_rel": 0.0,
        "com_x_body_mm": 0.0,
        "com_z_body_mm": 0.0,
        "com_y_mirror_mm": 0.0,
        "station_x_mm": 0.0,
        "lowest_mm": 0.0,
    }
    for kind, order in {(k, o) for k, o, _ in pairs.index}:
        left, right = pairs.loc[(kind, order, "L")], pairs.loc[(kind, order, "R")]
        diffs["volume_rel"] = max(diffs["volume_rel"], abs(left.volume_mm3 / right.volume_mm3 - 1))
        diffs["com_x_body_mm"] = max(
            diffs["com_x_body_mm"], abs(left.com_x_body_m - right.com_x_body_m) * MM_PER_M
        )
        diffs["com_z_body_mm"] = max(
            diffs["com_z_body_mm"], abs(left.com_z_body_m - right.com_z_body_m) * MM_PER_M
        )
        mirror = (
            abs(
                (left.com_y_body_m - layout_centre(summary, "L"))
                + (right.com_y_body_m - layout_centre(summary, "R"))
            )
            * MM_PER_M
        )
        diffs["com_y_mirror_mm"] = max(diffs["com_y_mirror_mm"], mirror)
        diffs["station_x_mm"] = max(
            diffs["station_x_mm"], abs(left.station_x_body_m - right.station_x_body_m) * MM_PER_M
        )
        diffs["lowest_mm"] = max(
            diffs["lowest_mm"], abs(left.lowest_above_ground_mm - right.lowest_above_ground_mm)
        )
    checks["left_right_symmetry"] = {
        **diffs,
        "note": "com_y_mirror: (y_L - c_L) + (y_R - c_R) about each track centre line",
        "pass": diffs["volume_rel"] <= SYMMETRY_VOLUME_REL_TOL
        and all(diffs[k] <= SYMMETRY_TOL_MM for k in diffs if k != "volume_rel"),
    }
    # Face index correspondence.
    checks["face_index"] = face_index_check(rows, parts, face_start)
    checks["pass"] = bool(
        checks["yaml_x_rounded_equal"]["mismatches"] == 0
        and checks["yaml_gap_rounded_equal"]["mismatches"] == 0
        and checks["roller_abs_y_vs_track_centre"]["max_abs_rounded_diff_m"] == 0
        and checks["solid_sets_disjoint"]["pass"]
        and checks["volume_vs_solid_sum"]["pass"]
        and checks["reread_vertex_max_abs_mm"] == 0.0
        and checks["left_right_symmetry"]["pass"]
        and checks["face_index"]["pass"]
        and checks["same_composition"]["pass"]
    )
    return checks


def layout_centre(summary: dict, side: str) -> float:
    """Track centre line (body y, m) of one side from the ground patch of crawler_summary.json."""
    patch = summary["ground_patches_by_band"]["1mm"][SIDES[side]]
    return patch["centre_x_mm"] / MM_PER_M


def face_index_check(rows: pd.DataFrame, parts: list[dict], face_start: np.ndarray) -> dict:
    """Rows of the face index (07_faces) that belong to the parts, and the ground faces."""
    index = pd.read_csv(
        INSTANCE_FACES,
        low_memory=False,
        usecols=["prototype_entry", "face_index", "solid_index", "selection"],
    )
    index = index[index["prototype_entry"] == CRAWLER_ENTRY]
    solid_of_face = np.searchsorted(face_start, index["face_index"].to_numpy(), side="right") - 1
    numbering_ok = bool(np.all(solid_of_face == index["solid_index"].to_numpy()))
    by_solid = index.groupby("solid_index")
    counts, ground_ok = [], True
    for row, part in zip(rows.itertuples(), parts, strict=True):
        members = [s for s in part["solids"] if s in by_solid.groups]
        indexed = sum(len(by_solid.groups[s]) for s in members)
        counts.append(indexed)
        if part["kind"] != "roller":
            faces = {int(f) for f in str(row.ground_face_indices).split(";")}
            tip_rows = index[index["face_index"].isin(faces)]
            ground_ok &= len(faces) == GROUSER_PADS_PER_SHOE and len(tip_rows) == len(faces)
            ground_ok &= bool(tip_rows["selection"].isin(GROUND_SELECTIONS).all())
    rows["indexed_face_count"] = counts
    return {
        "crawler_rows_in_face_index": len(index),
        "solid_index_equals_solid_of_face_range": numbering_ok,
        "shoe_ground_faces_in_index": bool(ground_ok),
        "note": "ground faces are rows with selection ground_band (<= 50 mm) or grouser_tip; "
        "roller faces are above the band and not in the index",
        "roller_rows_indexed_faces": int(
            rows.loc[rows["kind"] == "roller", "indexed_face_count"].sum()
        ),
        "pass": numbering_ok and bool(ground_ok),
    }


def main() -> None:
    started = time.perf_counter()
    PARTS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("", encoding="utf-8")
    instance = brep_cache.instances_of(CRAWLER_ENTRY)[0]
    crawler = brep_cache.load_part(instance.instance_path)
    log(f"loaded crawler in {time.perf_counter() - started:.1f} s")
    solid_shapes, face_start = load_solids(crawler)
    solids = pd.read_csv(CRAWLER_DIR / "crawler_solids.csv", encoding="utf-8-sig")
    wheels = pd.read_csv(CRAWLER_DIR / "crawler_wheels.csv", encoding="utf-8-sig")
    tips = pd.read_csv(CRAWLER_DIR / "crawler_grouser_tips.csv", encoding="utf-8-sig")
    summary = json.loads((CRAWLER_DIR / "crawler_summary.json").read_text(encoding="utf-8"))
    if len(solid_shapes) != len(solids):
        raise RuntimeError(f"solid count {len(solid_shapes)} != crawler_solids.csv {len(solids)}")
    ground_y = float(summary["ground_y_mm"])
    density, density_source = crawler_density()
    layout = yaml_layout()
    log(f"{len(solid_shapes)} solids, {int(face_start[-1])} faces, density {density} g/cm3")

    parts = roller_parts(solids, wheels)
    taken = {s for p in parts for s in p["solids"]}
    shoes, rule = shoe_parts(solids, tips, ground_y, taken)
    parts += shoes
    volumes = solids.set_index("solid")["volume_mm3"].to_dict()
    shapes, records, membership = {}, [], []
    for part in parts:
        part["id"] = part_id(part)
        part["volumes"] = volumes
        part["file"] = PARTS_OUT_DIR / f"{part['id']}{brep_cache.BINARY_SUFFIX}"
        if part["kind"] != "roller":
            part["grouser_faces"] = grouser_faces(
                solid_shapes[part["ground_shoe_solid"]], part["grouser_planes"]
            )
        compound = make_compound(solid_shapes[s] for s in part["solids"])
        brep_cache.write_brep(compound, part["file"])
        shapes[part["id"]] = compound
        records.append(
            describe(part, compound, solid_shapes, face_start, density, ground_y, layout)
        )
        for solid in part["solids"]:
            membership.append(
                {
                    "part_id": part["id"],
                    "solid": solid,
                    "volume_mm3": volumes[solid],
                    "face_start": int(face_start[solid]),
                    "face_count": int(face_start[solid + 1] - face_start[solid]),
                }
            )
    order = {"roller": 0, "end_shoe": 1, "flat_shoe": 2}
    keyed = sorted(
        zip(records, parts, strict=True),
        key=lambda rp: (order[rp[0]["kind"]], rp[0]["side"], rp[0]["order_index"]),
    )
    records = [r for r, _ in keyed]
    parts = [p for _, p in keyed]
    rows = pd.DataFrame(records)
    log(f"wrote {len(parts)} part files in {time.perf_counter() - started:.1f} s")

    checks = verify(rows, parts, solids, face_start, layout, summary, shapes)
    log(f"verification pass = {checks['pass']}")
    for column in ["yaml_index", "roller_wheel_solid", "ground_shoe_solid", "shoe_plate_solid"]:
        rows[column] = pd.to_numeric(rows[column], errors="coerce").astype("Int64")
    rows.to_csv(INDEX_CSV, index=False, encoding="utf-8-sig", float_format="%.9g")
    pd.DataFrame(membership).sort_values(["part_id", "solid"]).to_csv(
        SOLIDS_OUT_CSV, index=False, encoding="utf-8-sig", float_format="%.6f"
    )
    script = Path(__file__).resolve()
    peak_gb = psutil.Process().memory_info().peak_wset / 1e9
    payload = {
        "provenance": {
            "source_prototype_entry": CRAWLER_ENTRY,
            "source_instance_path": instance.instance_path,
            "source_file": summary["provenance"]["source_file"],
            "source_sha256": summary["provenance"]["source_sha256"],
            "inputs_sha256": {
                path.name: sha256_file(path)
                for path in (
                    CRAWLER_DIR / "crawler_solids.csv",
                    CRAWLER_DIR / "crawler_wheels.csv",
                    CRAWLER_DIR / "crawler_grouser_tips.csv",
                    CRAWLER_DIR / "crawler_summary.json",
                    INSTANCE_FACES,
                    YAML_PATH,
                )
            },
            "generator": script.relative_to(PROJECT_ROOT).as_posix(),
            "generator_sha256": sha256_file(script),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "run_time_s": round(time.perf_counter() - started, 1),
            "peak_memory_gb": round(peak_gb, 2),
            "note": summary["provenance"]["note"],
        },
        "frames": {
            "brep_files": "CAD world frame, mm, Y up, crawler placement applied; "
            "placement of every part file = identity",
            "body_from_cad_rotation": CAD_TO_BODY.tolist(),
            "body_from_cad": "p_body_m = R @ p_cad_mm / 1000 (CAD origin = body origin)",
            "inertia": "about the part centroid, body axes, kg m^2",
            "ground_y_cad_mm": ground_y,
            "ground_z_body_m": ground_y / MM_PER_M,
        },
        "density": {"g_cm3": density, "source": density_source},
        "definitions": {
            "roller": "solids fully inside the station box around a crawler_wheels.csv "
            f"'{ROLLER_ROLE}' axis: |x - centre| <= {ROLLER_HALF_X_MM} mm, "
            f"|z - axis| <= {ROLLER_HALF_Z_MM} mm, y from the wheel bottom "
            f"- {ROLLER_BOTTOM_TOL_MM} mm to the wheel top + {ROLLER_BOTTOM_TOL_MM} mm "
            "(CAD; the same 12 solids for a top bound up to -500 mm); "
            "station x = tread cylinder axis (body x)",
            "shoe_unit": "ground shoe (carries the 4 grouser pad planes) + every chain solid "
            "whose nearest shoe plate centroid (3D) is the plate above it: shoe "
            "plate, link pair, shoe bolts and nuts, side blocks and fasteners, "
            "track joint (pin, bushing, seal discs)",
            "end_vs_flat": f"lowest grouser pad point > {FLAT_SHOE_TOL_MM} mm above the "
            "floor = end shoe (gapped), else flat shoe",
            "station_x": "shoes: mean centroid Z_cad of the grouser pad planes (export_params.py "
            "rule); rollers: tread axis",
            "gap": "lowest grouser pad point - floor (YAML end_shoe_gap_m rule); "
            "lowest_above_ground_mm = lowest point of the whole part",
            "order_index": "0-based, ascending body x; equals the index of the YAML array "
            "named in yaml_key (roller_x_m, end_shoe_x_m)",
            "face_ranges": "face_index ranges (inclusive) of TopExp_Explorer(prototype, FACE), "
            "same numbering as 01_cad/07_faces (only near-ground crawler faces "
            "are rows there)",
        },
        "shoe_rule_data": rule,
        "verification": checks,
        "parts": json.loads(rows.to_json(orient="records")),
    }
    INDEX_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, default=float), encoding="utf-8"
    )
    total = sum(p["file"].stat().st_size for p in parts)
    log(
        f"done in {time.perf_counter() - started:.0f} s, files {total / 1e6:.2f} MB, "
        f"peak memory {peak_gb:.2f} GB"
    )


if __name__ == "__main__":
    main()
