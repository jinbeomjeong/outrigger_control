"""Check whether the crawler CAD has upper (carrier) rollers or another upper-run support.

Reads only caches (no STEP): the crawler prototype ``0:1:1:746`` from the
B-rep cache, ``crawler_solids.csv`` / ``crawler_wheels.csv`` (derived crawler
cache), the part and STEP product tables and the face style table.

Steps:
1. Name search (STEP product list, parts table) for roller / guide / slide /
   pad words, English and decoded Korean.
2. Chain members are found as repeated-volume solids next to the shoe plates.
   The upper-run pitch line comes from the pin centres; it is fitted with
   straight lines on each side of the highest pin.
3. Every non-chain solid in the upper zone (Y -450 ... +100 mm, Z -1,400 ...
   +1,400 mm) is listed with its surface types, cylinder axes and the minimum
   distance to the chain (BRepExtrema).
4. Round solids are recounted with relaxed rules (any cylinder or torus face
   with an axis along X and radius >= 20 mm) and compared with
   ``crawler_wheels.csv``.

Outputs (new files only):
    01_cad/06_brep/derived/crawler/upper_run_check.json
    01_cad/06_brep/derived/crawler/upper_run_check.png

Frames: CAD world mm, Y up, track length along Z; body m: x = +Z_cad,
y = +X_cad, z = +Y_cad.

Usage:
    python -I 04_scripts/00_cad/check_upper_run.py
"""

import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import psutil
from matplotlib.collections import PolyCollection
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.BRepExtrema import BRepExtrema_DistShapeShape
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.GeomAbs import (
    GeomAbs_BSplineSurface,
    GeomAbs_Cone,
    GeomAbs_Cylinder,
    GeomAbs_Plane,
    GeomAbs_Torus,
)
from OCC.Core.GProp import GProp_GProps
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_REVERSED, TopAbs_SOLID
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.TopoDS import topods

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brep_cache
from build_style_index import place_one_pcore
from cad_common import CAD_DIR, MM_PER_M, PROJECT_ROOT

CRAWLER_ENTRY = "0:1:1:746"
CRAWLER_DIR = brep_cache.DERIVED_DIR / "crawler"
SOLIDS_CSV = CRAWLER_DIR / "crawler_solids.csv"
WHEELS_CSV = CRAWLER_DIR / "crawler_wheels.csv"
SUMMARY_JSON = CRAWLER_DIR / "crawler_summary.json"
OUT_JSON = CRAWLER_DIR / "upper_run_check.json"
OUT_PNG = CRAWLER_DIR / "upper_run_check.png"
PARTS_CSV = CAD_DIR / "01_parts" / "parts_classified.csv"
PRODUCTS_CSV = CAD_DIR / "00_step" / "step_products.csv"
FACE_STYLES_CSV = CAD_DIR / "08_style" / "face_styles.csv.gz"

ZONE_Y_MM = (-450.0, 100.0)  # upper search zone (track frame top ... above shoes)
ZONE_Z_MM = (-1400.0, 1400.0)  # between the end wheel axes
CHAIN_CLASS_MIN = 44  # shoes per side; chain parts repeat at least this often
CHAIN_NEAR_SHOE_MM = 40.0  # bbox gap to a shoe plate for a chain member
CONTACT_MM = 5.0  # "touching" threshold for the upper-run support
END_GROUP_Z_MM = 1000.0  # large solids entirely beyond this |Z| = end wheel groups
ROUND_MIN_RADIUS_MM = 20.0
AXIS_TOL = 1e-3
NAME_WORDS = (
    "CARRIER", "UPPER ROLLER", "TOP ROLLER", "ROLLER", "GUIDE", "GUID", "SLIDE",
    "PAD", "WEAR", "IDLER", "SPROCKET", "TRACK", "SHOE", "CRAWLER", "LINK",
    "캐리어", "롤러", "상부", "가이드", "슬라이드", "패드", "트랙", "크롤러", "아이들러",
    "스프로킷", "마모",
)
CAD_TO_BODY = np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
SURFACE_NAMES = {
    GeomAbs_Plane: "plane",
    GeomAbs_Cylinder: "cylinder",
    GeomAbs_Cone: "cone",
    GeomAbs_Torus: "torus",
    GeomAbs_BSplineSurface: "bspline",
}


def log(text: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {text}", flush=True)


def body_m(point_mm) -> list[float]:
    return (CAD_TO_BODY @ np.asarray(point_mm, dtype=float) / MM_PER_M).round(4).tolist()


# --------------------------------------------------------------------------
# 1. Names
# --------------------------------------------------------------------------
def name_search(track_box: dict) -> dict:
    products = pd.read_csv(PRODUCTS_CSV).fillna("")
    parts = pd.read_csv(PARTS_CSV).fillna({"instance_path": "", "product_name": ""})
    crawler = products[products["product_name"].str.contains("5J286105")]

    def hit(text: str) -> list[str]:
        upper = text.upper()
        return [word for word in NAME_WORDS if word in upper]

    product_hits = []
    for _, row in products.iterrows():
        words = hit(f"{row['product_name']} {row['product_description']}")
        if words:
            product_hits.append({"product_name": row["product_name"],
                                 "description": row["product_description"], "words": words})
    # Parts (any name) whose bbox reaches into the track zone of either side.
    inside = parts[
        (parts["bbox_max_y_mm"] > track_box["y"][0]) & (parts["bbox_min_y_mm"] < track_box["y"][1])
        & (parts["bbox_max_z_mm"] > track_box["z"][0]) & (parts["bbox_min_z_mm"] < track_box["z"][1])
        & ((parts["bbox_max_x_mm"] > track_box["x"][0]) | (parts["bbox_min_x_mm"] < -track_box["x"][0]))
    ]
    part_hits = parts[parts["instance_path"].apply(lambda t: bool(hit(t)))]
    part_hits_in_zone = part_hits[part_hits.index.isin(inside.index)]
    return {
        "crawler_product": crawler[["product_name", "product_description", "child_count"]]
        .to_dict("records"),
        "crawler_instances_in_parts_table": parts.loc[
            parts["instance_path"].str.contains("5J286105"),
            ["instance_path", "product_name", "solid_count", "shell_count"],
        ].to_dict("records"),
        "keyword_products_all": product_hits,
        "keyword_parts_count_all": len(part_hits),
        "parts_in_track_zone": inside[["instance_path", "product_name", "solid_count"]]
        .to_dict("records"),
        "keyword_parts_in_track_zone": part_hits_in_zone["instance_path"].tolist(),
        "words": list(NAME_WORDS),
        "track_zone_mm": track_box,
    }


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------
def solids_of(shape) -> list:
    out, explorer = [], TopExp_Explorer(shape, TopAbs_SOLID)
    while explorer.More():
        out.append(topods.Solid(explorer.Current()))
        explorer.Next()
    return out


def face_summary(solid) -> dict:
    """Area per surface type, X-axis cylinders/tori and the top plane (normal +Y)."""
    areas: dict[str, float] = {}
    rounds, top_planes = [], []
    explorer = TopExp_Explorer(solid, TopAbs_FACE)
    while explorer.More():
        face = topods.Face(explorer.Current())
        explorer.Next()
        adaptor = BRepAdaptor_Surface(face, True)
        kind = SURFACE_NAMES.get(adaptor.GetType(), "other")
        props = GProp_GProps()
        brepgprop.SurfaceProperties(face, props)
        area = props.Mass()
        areas[kind] = areas.get(kind, 0.0) + area
        if kind in ("cylinder", "torus"):
            surface = adaptor.Cylinder() if kind == "cylinder" else adaptor.Torus()
            axis = surface.Axis()
            direction = np.array([axis.Direction().X(), axis.Direction().Y(), axis.Direction().Z()])
            location = surface.Location()
            radius = surface.Radius() if kind == "cylinder" else surface.MajorRadius()
            box = Bnd_Box()
            brepbndlib.AddOptimal(face, box, False, False)
            extent = box.Get()
            rounds.append({
                "x_extent_mm": [round(extent[0], 2), round(extent[3], 2)],
                "kind": kind, "radius_mm": round(radius, 3),
                "minor_radius_mm": None if kind == "cylinder" else round(surface.MinorRadius(), 3),
                "axis": direction.round(4).tolist(),
                "location_mm": [round(location.X(), 2), round(location.Y(), 2), round(location.Z(), 2)],
                "area_mm2": round(area, 1),
            })
        elif kind == "plane":
            plane = adaptor.Plane()
            position = plane.Position()
            normal = position.XDirection().Crossed(position.YDirection())
            n = np.array([normal.X(), normal.Y(), normal.Z()])
            if face.Orientation() == TopAbs_REVERSED:
                n = -n
            if n[1] > 0.99:
                centre = props.CentreOfMass()
                top_planes.append({"y_mm": round(centre.Y(), 3), "area_mm2": round(area, 1),
                                   "centre_mm": [round(centre.X(), 2), round(centre.Y(), 2),
                                                 round(centre.Z(), 2)]})
    return {"area_by_type_mm2": {k: round(v, 1) for k, v in sorted(areas.items())},
            "rounds": rounds, "top_planes": sorted(top_planes, key=lambda p: -p["y_mm"])}


def distance(a, b) -> tuple[float, list, list]:
    tool = BRepExtrema_DistShapeShape(a, b)
    tool.Perform()
    if not tool.IsDone():
        return float("nan"), [], []
    p1, p2 = tool.PointOnShape1(1), tool.PointOnShape2(1)
    return (tool.Value(), [round(p1.X(), 2), round(p1.Y(), 2), round(p1.Z(), 2)],
            [round(p2.X(), 2), round(p2.Y(), 2), round(p2.Z(), 2)])


def bbox_gap(a: pd.Series, b: pd.DataFrame) -> np.ndarray:
    gaps = []
    for axis in "xyz":
        low = np.maximum(b[f"bbox_min_{axis}_mm"].to_numpy(), a[f"bbox_min_{axis}_mm"])
        high = np.minimum(b[f"bbox_max_{axis}_mm"].to_numpy(), a[f"bbox_max_{axis}_mm"])
        gaps.append(np.clip(low - high, 0, None))
    return np.sqrt(np.sum(np.square(gaps), axis=0))


_MESHED: set[int] = set()


def mesh_outline(solid, columns=(2, 1), deflection: float = 1.0) -> list[np.ndarray]:
    """Triangles of a solid projected on two CAD axes (default Z-Y, side view)."""
    if id(solid) not in _MESHED:
        BRepMesh_IncrementalMesh(solid, deflection, False, 0.3, False)
        _MESHED.add(id(solid))
    triangles = []
    explorer = TopExp_Explorer(solid, TopAbs_FACE)
    while explorer.More():
        face = topods.Face(explorer.Current())
        explorer.Next()
        location = TopLoc_Location()
        triangulation = BRep_Tool.Triangulation(face, location)
        if triangulation is None:
            continue
        trsf = location.Transformation()
        nodes = np.array([
            [p.X(), p.Y(), p.Z()]
            for p in (triangulation.Node(i + 1).Transformed(trsf)
                      for i in range(triangulation.NbNodes()))
        ])
        for i in range(triangulation.NbTriangles()):
            a, b, c = triangulation.Triangle(i + 1).Get()
            triangles.append(nodes[[a - 1, b - 1, c - 1]][:, list(columns)])
    return triangles


# --------------------------------------------------------------------------
# 2. Chain and pitch line
# --------------------------------------------------------------------------
def classify_chain(solids: pd.DataFrame) -> pd.DataFrame:
    solids = solids.copy()
    solids["volume_class"] = solids["volume_mm3"].round(0)
    solids["dx"] = solids["bbox_max_x_mm"] - solids["bbox_min_x_mm"]
    solids["is_chain"] = False
    solids["chain_role"] = ""
    for side in ("left", "right"):
        rows = solids[solids["side"] == side]
        counts = rows["volume_class"].value_counts()
        shoes = rows[(rows["dx"] > 400) & rows["volume_class"].map(counts).ge(CHAIN_CLASS_MIN)]
        for index, row in rows.iterrows():
            if counts[row["volume_class"]] < CHAIN_CLASS_MIN:
                continue
            if bbox_gap(row, shoes).min() <= CHAIN_NEAR_SHOE_MM:
                solids.loc[index, "is_chain"] = True
    # Roles by the left-side pattern (both sides share volumes to < 1e-6).
    plates = solids["is_chain"] & (solids["dx"] > 400)
    big_plate = solids.loc[plates, "volume_mm3"].max()
    solids.loc[plates & (solids["volume_mm3"] > 0.9 * big_plate), "chain_role"] = "shoe_plate"
    solids.loc[plates & (solids["volume_mm3"] <= 0.9 * big_plate), "chain_role"] = "shoe_grouser"
    width = solids["dx"]
    solids.loc[solids["is_chain"] & width.between(200, 400), "chain_role"] = "pin"
    solids.loc[solids["is_chain"] & width.between(100, 200), "chain_role"] = "bushing"
    solids.loc[solids["is_chain"] & width.between(55, 70), "chain_role"] = "link"
    solids.loc[solids["is_chain"] & (solids["chain_role"] == ""), "chain_role"] = "small"
    return solids


def pitch_line(solids: pd.DataFrame, side: str, wheel_axis_y: float) -> dict:
    pins = solids[(solids["side"] == side) & (solids["chain_role"] == "pin")]
    upper = pins[pins["centroid_y_mm"] > wheel_axis_y].sort_values("centroid_z_mm")
    z, y = upper["centroid_z_mm"].to_numpy(), upper["centroid_y_mm"].to_numpy()
    inner = (z > ZONE_Z_MM[0]) & (z < ZONE_Z_MM[1])
    zi, yi = z[inner], y[inner]
    apex = int(np.argmax(yi))
    fits = {}
    for name, sel in (("rear", slice(0, apex + 1)), ("front", slice(apex, None))):
        coeff = np.polyfit(zi[sel], yi[sel], 1)
        residual = yi[sel] - np.polyval(coeff, zi[sel])
        fits[name] = {
            "pins": int(len(zi[sel])),
            "z_range_mm": [round(float(zi[sel].min()), 1), round(float(zi[sel].max()), 1)],
            "slope_deg": round(float(np.degrees(np.arctan(coeff[0]))), 4),
            "max_abs_residual_mm": round(float(np.abs(residual).max()), 4),
            "coeff": coeff.tolist(),
        }
    # Sag test: straight chord from the first to the last inner pin.
    chord = np.interp(zi, [zi[0], zi[-1]], [yi[0], yi[-1]])
    pitch = np.hypot(np.diff(z), np.diff(y))
    return {
        "side": side,
        "upper_pins_total": int(len(upper)),
        "pins_between_end_wheels": int(inner.sum()),
        "pitch_mm_median": round(float(np.median(pitch)), 3),
        "apex_pin_mm": {"z": round(float(zi[apex]), 2), "y": round(float(yi[apex]), 2)},
        "apex_above_end_pin_chord_mm": round(float(yi[apex] - chord[apex]), 2),
        "pins_below_chord": int((yi < chord - 0.01).sum()),
        "segments": fits,
        "pins_zy_mm": np.column_stack([z, y]).round(2).tolist(),
    }


# --------------------------------------------------------------------------
# 4. Round solids recount
# --------------------------------------------------------------------------
def round_recount(solids: pd.DataFrame, shapes: list, wheels: pd.DataFrame) -> dict:
    found = []
    for index, row in solids[~solids["is_chain"] & (solids["side"] != "center")].iterrows():
        summary = face_summary(shapes[int(row["solid"])])
        x_rounds = [r for r in summary["rounds"]
                    if abs(abs(r["axis"][0]) - 1) < AXIS_TOL and r["radius_mm"] >= ROUND_MIN_RADIUS_MM]
        if not x_rounds:
            continue
        biggest = max(x_rounds, key=lambda r: r["radius_mm"])
        found.append({"solid": int(row["solid"]), "side": row["side"],
                      "axis_y_mm": biggest["location_mm"][1], "axis_z_mm": biggest["location_mm"][2],
                      "max_radius_mm": biggest["radius_mm"],
                      "bbox_dy_mm": round(row["bbox_max_y_mm"] - row["bbox_min_y_mm"], 2),
                      "bbox_dz_mm": round(row["bbox_max_z_mm"] - row["bbox_min_z_mm"], 2),
                      "volume_mm3": round(row["volume_mm3"], 1)})
    table = pd.DataFrame(found)
    # Station match: same side, axis within 15 mm of a crawler_wheels.csv station.
    matched = []
    for _, row in table.iterrows():
        same = wheels[wheels["side"] == row["side"]]
        gap = np.hypot(same["axis_y_mm"] - row["axis_y_mm"], same["axis_z_mm"] - row["axis_z_mm"])
        matched.append(bool((gap < 15).any()))
    table["in_wheel_station"] = matched
    above = table[table["axis_y_mm"] > -583.3 + 1]  # axis above the end wheel axes
    return {
        "rule": (f"non-chain solid with a cylinder/torus face, axis along X (|ax|>{1 - AXIS_TOL}), "
                 f"radius >= {ROUND_MIN_RADIUS_MM} mm; station match = axis within 15 mm"),
        "count_by_side": table.groupby("side").size().to_dict(),
        "not_in_station": table[~table["in_wheel_station"]].to_dict("records"),
        "axis_above_end_wheel_axis": above.to_dict("records"),
    }


# --------------------------------------------------------------------------
# 3. Upper-zone candidates
# --------------------------------------------------------------------------
def upper_candidates(solids: pd.DataFrame, shapes: list, styles: pd.DataFrame) -> list[dict]:
    zone = solids[
        ~solids["is_chain"] & (solids["side"] != "center")
        & (solids["bbox_max_y_mm"] > ZONE_Y_MM[0]) & (solids["bbox_min_y_mm"] < ZONE_Y_MM[1])
        & (solids["bbox_max_z_mm"] > ZONE_Z_MM[0]) & (solids["bbox_min_z_mm"] < ZONE_Z_MM[1])
    ]
    chain_upper = solids[solids["is_chain"] & (solids["centroid_y_mm"] > -583.0)]
    out = []
    for _, row in zone.iterrows():
        index = int(row["solid"])
        # The bbox gap is a lower bound of the distance: exact BRepExtrema only
        # where the boxes are within CONTACT_MM (one pair takes about 1 s).
        gaps = bbox_gap(row, chain_upper)
        # End-wheel / idler hardware (large solids entirely beyond |Z| 1,000 mm)
        # carries the chain at the wrap by design; exact distances there cost
        # 5-30 s per pair, so they keep the bbox lower bound only.
        end_group = (row["volume_mm3"] > 1e6
                     and (row["bbox_min_z_mm"] > END_GROUP_Z_MM
                          or row["bbox_max_z_mm"] < -END_GROUP_Z_MM))
        near = chain_upper[(gaps <= CONTACT_MM) & (not end_group)]
        best = (float("inf"), None, [], [])
        bbox_lower_bound = round(float(gaps.min()), 3) if len(gaps) else None
        for _, other in near.iterrows():
            value, p1, p2 = distance(shapes[index], shapes[int(other["solid"])])
            if value < best[0]:
                best = (value, other, p1, p2)
        summary = face_summary(shapes[index])
        colours = styles.loc[styles["solid_order"] == index, "rgb_hex"].value_counts()
        record = {
            "solid": index, "side": row["side"], "volume_mm3": round(row["volume_mm3"], 1),
            "bbox_min_mm": [round(row[f"bbox_min_{a}_mm"], 2) for a in "xyz"],
            "bbox_max_mm": [round(row[f"bbox_max_{a}_mm"], 2) for a in "xyz"],
            "centroid_mm": [round(row[f"centroid_{a}_mm"], 2) for a in "xyz"],
            "centroid_body_m": body_m([row[f"centroid_{a}_mm"] for a in "xyz"]),
            "colours": colours.to_dict(),
            **summary,
            "min_distance_to_upper_chain_mm": None if best[1] is None else round(best[0], 3),
            "bbox_gap_lower_bound_to_upper_chain_mm": bbox_lower_bound,
            "end_wheel_group_exact_skipped": bool(end_group),
        }
        if best[1] is not None:
            record["nearest_chain_solid"] = {"solid": int(best[1]["solid"]),
                                             "role": best[1]["chain_role"],
                                             "point_on_candidate_mm": best[2],
                                             "point_on_chain_mm": best[3]}
        out.append(record)
    return sorted(out, key=lambda r: (r["side"], r["min_distance_to_upper_chain_mm"]
                                      if r["min_distance_to_upper_chain_mm"] is not None else 1e9))


def contact_detail(candidate: dict, solids: pd.DataFrame, shapes: list) -> dict:
    """All chain solids within CONTACT_MM + 10 of a candidate, with distances."""
    row = solids.loc[solids["solid"] == candidate["solid"]].iloc[0]
    chain = solids[solids["is_chain"] & solids["chain_role"].isin(["link", "pin", "bushing"])]
    near = chain[bbox_gap(row, chain) < CONTACT_MM + 10]
    rows = []
    for _, other in near.iterrows():
        value, p1, p2 = distance(shapes[candidate["solid"]], shapes[int(other["solid"])])
        rows.append({"chain_solid": int(other["solid"]), "role": other["chain_role"],
                     "distance_mm": round(value, 3), "point_on_candidate_mm": p1,
                     "point_on_chain_mm": p2})
    return sorted(rows, key=lambda r: r["distance_mm"])


def roller_geometry(candidate: dict) -> dict:
    """Revolved faces about X of a support: diameters, X spans and the axis (Y, Z)."""
    x_rounds = [r for r in candidate["rounds"]
                if abs(abs(r["axis"][0]) - 1) < AXIS_TOL and r["radius_mm"] >= ROUND_MIN_RADIUS_MM]
    if not x_rounds:
        return {"is_roller": False}
    axis_y = float(np.median([r["location_mm"][1] for r in x_rounds]))
    axis_z = float(np.median([r["location_mm"][2] for r in x_rounds]))
    bands = sorted(({"diameter_mm": round(2 * r["radius_mm"], 2), "x_from_mm": r["x_extent_mm"][0],
                     "x_to_mm": r["x_extent_mm"][1],
                     "width_mm": round(r["x_extent_mm"][1] - r["x_extent_mm"][0], 2)}
                    for r in x_rounds), key=lambda b: b["x_from_mm"])
    touching = [c for c in candidate.get("contacts", []) if c["distance_mm"] <= CONTACT_MM]
    contact_radius = [round(float(np.hypot(c["point_on_candidate_mm"][1] - axis_y,
                                           c["point_on_candidate_mm"][2] - axis_z)), 2)
                      for c in touching]
    return {
        "is_roller": True,
        "axis_mm": {"y": round(axis_y, 3), "z": round(axis_z, 3)},
        "axis_body_m": body_m([candidate["centroid_mm"][0], axis_y, axis_z]),
        "x_spans_by_diameter": bands,
        "touching_chain_parts": len(touching),
        "contact_radius_mm": contact_radius,
        "top_of_largest_tread_y_mm": round(axis_y + max(b["diameter_mm"] for b in bands) / 2, 3),
    }


# --------------------------------------------------------------------------
# Figure
# --------------------------------------------------------------------------
def _draw(ax, rows, shapes, support_ids, columns, window) -> None:
    """Fill projected triangles: frame/wheels grey, chain blue, support red."""
    (u_lim, v_lim), (cu, cv) = window, columns
    names = "xyz"
    rows = rows[(rows[f"bbox_max_{names[cu]}_mm"] > u_lim[0]) & (rows[f"bbox_min_{names[cu]}_mm"] < u_lim[1])
                & (rows[f"bbox_max_{names[cv]}_mm"] > v_lim[0]) & (rows[f"bbox_min_{names[cv]}_mm"] < v_lim[1])]
    groups = (("frame / wheels", "#c9c9c9", 1, ~rows["is_chain"] & ~rows["solid"].isin(support_ids)),
              ("chain", "#8aa8c8", 2, rows["is_chain"]),
              ("carrier roller", "#d1495b", 3, rows["solid"].isin(support_ids)))
    for label, colour, order, mask in groups:
        polys = []
        for index in rows.loc[mask, "solid"].astype(int):
            polys.extend(mesh_outline(shapes[index], columns))
        ax.add_collection(PolyCollection(polys, facecolors=colour, edgecolors="none",
                                         zorder=order, label=label))
    ax.set_xlim(*u_lim)
    ax.set_ylim(*v_lim)
    ax.set_aspect("equal")
    ax.grid(True, lw=0.3, color="#dddddd", zorder=0)


def figure(solids, shapes, lines, supports, wheels) -> None:
    side = "left"
    rows = solids[(solids["side"] == side) & (solids["bbox_max_y_mm"] > -760)]
    support_ids = {s["solid"] for s in supports if s["side"] == side}
    fig = plt.figure(figsize=(15, 10.5))
    grid = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.25], width_ratios=[1.9, 1.0])
    ax_side, ax_zoom, ax_front = (fig.add_subplot(grid[0, :]), fig.add_subplot(grid[1, 0]),
                                  fig.add_subplot(grid[1, 1]))
    pins = np.array(lines[side]["pins_zy_mm"])
    for ax, window in ((ax_side, ((-1900, 1900), (-1080, -60))),
                       (ax_zoom, ((-560, 560), (-440, -90)))):
        _draw(ax, rows, shapes, support_ids, (2, 1), window)
        ax.plot(pins[:, 0], pins[:, 1], "o-", color="#1f3b5c", ms=3, lw=0.8, zorder=4,
                label="upper-run pin centres (pitch line)")
        for name, seg in lines[side]["segments"].items():
            zz = np.array(seg["z_range_mm"])
            ax.plot(zz, np.polyval(seg["coeff"], zz), "--", color="#e08a00", lw=1.2, zorder=5,
                    label=None if name == "front" else "straight-line fits (rear / front of apex)")
        for _, wheel in wheels[wheels["side"] == side].iterrows():
            if wheel["max_round_diameter_mm"] >= 150:
                ax.add_patch(plt.Circle((wheel["axis_z_mm"], wheel["axis_y_mm"]),
                                        wheel["max_round_diameter_mm"] / 2, fill=False,
                                        ec="#555555", lw=0.8, ls=":", zorder=6))
        ax.set_xlabel("Z_cad (mm)   [body x = +Z_cad]")
        ax.set_ylabel("Y_cad (mm)   [body z = +Y_cad]")
    for support in supports:
        roller = support.get("roller", {})
        if support["side"] == side and roller.get("is_roller"):
            axis = roller["axis_mm"]
            ax_zoom.plot(axis["z"], axis["y"], "+", color="k", ms=10, zorder=7)
            ax_zoom.annotate(
                f"carrier roller axis Y {axis['y']:.1f}, Z {axis['z']:.1f} mm\n"
                f"treads/flange D {', '.join(str(b['diameter_mm']) for b in roller['x_spans_by_diameter'])} mm",
                (axis["z"], axis["y"]), xytext=(axis["z"] + 90, axis["y"] - 75), fontsize=8,
                arrowprops={"arrowstyle": "-", "lw": 0.6}, zorder=8)
            ax_side.annotate("carrier roller", (axis["z"], axis["y"]),
                             xytext=(axis["z"] + 250, axis["y"] - 330), fontsize=9,
                             arrowprops={"arrowstyle": "->", "lw": 0.8}, zorder=8)
    ax_side.set_title("Left track, side view (from +X_cad). Upper run: straight from each end wheel "
                      "up to the apex over one carrier roller at Z 0", fontsize=10)
    ax_side.legend(loc="lower center", fontsize=8, ncol=5)
    apex = lines[side]["apex_pin_mm"]
    ax_zoom.set_title(f"Zoom: apex pin Z {apex['z']:.1f} mm, Y {apex['y']:.1f} mm; "
                      "link rails rest on the roller treads", fontsize=10)
    # Front view (looking along -Z_cad) of a 200 mm slab around the roller.
    slab = rows[(rows["bbox_max_z_mm"] > -100) & (rows["bbox_min_z_mm"] < 100)]
    _draw(ax_front, slab, shapes, support_ids, (0, 1), ((700, 1390), (-440, -60)))
    ax_front.set_xlabel("X_cad (mm)   [body y = +X_cad]")
    ax_front.set_ylabel("Y_cad (mm)")
    ax_front.set_title("Front view, solids with |Z_cad| < 100 mm", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=130)
    plt.close(fig)


# --------------------------------------------------------------------------
def main() -> None:
    started = time.time()
    pin_info = place_one_pcore()
    log(f"pin {pin_info}")
    instance = brep_cache.instances_of(CRAWLER_ENTRY)[0]
    shape = brep_cache.place(brep_cache.load_prototype(CRAWLER_ENTRY), instance)
    shapes = solids_of(shape)
    solids = pd.read_csv(SOLIDS_CSV)
    wheels = pd.read_csv(WHEELS_CSV)
    summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
    log(f"{len(shapes)} solids loaded ({time.time() - started:.1f} s)")
    # Index check: TopExp order must match crawler_solids.csv.
    check = []
    for index in (0, 234, 22, 848, len(shapes) - 1):
        props = GProp_GProps()
        brepgprop.VolumeProperties(shapes[index], props)
        table = float(solids.loc[solids["solid"] == index, "volume_mm3"].iloc[0])
        check.append(abs(props.Mass() - table) / table)
    if max(check) > 1e-9:
        raise RuntimeError(f"solid order differs from {SOLIDS_CSV}: {check}")

    track_box = {"x": [600.0, 1400.0], "y": [summary["ground_y_mm"], 100.0], "z": [-1900.0, 1900.0]}
    names = name_search(track_box)
    log(f"names: {len(names['keyword_products_all'])} keyword products, "
        f"{len(names['parts_in_track_zone'])} parts in the track zone")

    solids = classify_chain(solids)
    chain_counts = (solids[solids["is_chain"]].groupby(["side", "chain_role"]).size()
                    .unstack(fill_value=0).to_dict("index"))
    end_axis_y = float(wheels.loc[wheels["max_round_diameter_mm"] >= 400, "axis_y_mm"].mean())
    lines = {side: pitch_line(solids, side, end_axis_y) for side in ("left", "right")}
    log(f"pitch line apex L {lines['left']['apex_pin_mm']} R {lines['right']['apex_pin_mm']}")

    styles = pd.read_csv(FACE_STYLES_CSV)
    styles = styles[styles["prototype_entry"] == CRAWLER_ENTRY]
    candidates = upper_candidates(solids, shapes, styles)
    log(f"{len(candidates)} non-chain solids in the upper zone ({time.time() - started:.1f} s)")
    supports = [c for c in candidates if c["min_distance_to_upper_chain_mm"] is not None
                and c["min_distance_to_upper_chain_mm"] <= CONTACT_MM]
    for support in supports:
        support["contacts"] = contact_detail(support, solids, shapes)
        support["roller"] = roller_geometry(support)
    log(f"supports touching the upper chain: {[s['solid'] for s in supports]}")
    rounds = round_recount(solids, shapes, wheels)
    log(f"round recount {rounds['count_by_side']}")

    figure(solids, shapes, lines, supports, wheels)
    result = {
        "generator": "04_scripts/00_cad/check_upper_run.py",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "inputs": [str(p.relative_to(PROJECT_ROOT)) for p in
                   (brep_cache.prototype_path(CRAWLER_ENTRY), SOLIDS_CSV, WHEELS_CSV, PARTS_CSV,
                    PRODUCTS_CSV, FACE_STYLES_CSV)],
        "frames": "CAD world mm (Y up, Z along the track); *_body_m: x=+Z_cad, y=+X_cad, z=+Y_cad, m",
        "search": {"zone_y_mm": ZONE_Y_MM, "zone_z_mm": ZONE_Z_MM,
                   "chain_rule": f"volume class repeated >= {CHAIN_CLASS_MIN} per side and bbox "
                                 f"within {CHAIN_NEAR_SHOE_MM} mm of a shoe plate",
                   "contact_threshold_mm": CONTACT_MM},
        "names": names,
        "chain_member_counts": chain_counts,
        "pitch_line": lines,
        "upper_zone_non_chain_solids": candidates,
        "supports_touching_upper_chain": [c["solid"] for c in supports],
        "round_recount": rounds,
        "run": {"seconds": round(time.time() - started, 1),
                "peak_working_set_gb": round(psutil.Process().memory_info().peak_wset / 2**30, 2),
                "cpu": pin_info},
    }
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=1, default=float),
                        encoding="utf-8")
    log(f"wrote {OUT_JSON.name}, {OUT_PNG.name} ({time.time() - started:.1f} s)")


if __name__ == "__main__":
    main()
