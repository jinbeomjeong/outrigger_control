"""Classify the CAD parts into superstructure and legs and compute mass properties.

Reads only the cached tables (no STEP parsing):
    01_cad/01_parts/parts.csv       from extract_parts.py
    01_cad/00_step/step_products.csv, 01_cad/00_step/step_header.json   from step_text_index.py
    01_cad/02_legs/leg_faces.csv    from inspect_legs.py

Writes:
    01_cad/01_parts/parts_classified.csv  parts.csv plus resolved density, mass and group
    01_cad/01_parts/cad_summary.json      units, axes, leg geometry, mass properties
    01_cad/01_parts/layout_views.png      top/side/front bbox layout with legs highlighted

Frames. CAD coordinates are the STEP root frame in mm (Inventor, Y up). The
proposed body frame of CLAUDE.md (x forward, y left, z up) is a pure axis
permutation of the CAD frame with the same origin:
    x_body = Z_cad, y_body = X_cad, z_body = Y_cad.
The forward direction comes from the FRONT/REAR JACK CYL positions.

Usage:
    python -I 04_scripts/00_cad/analyze_parts.py
"""

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cad_common import (
    LEGS_DIR,
    PARTS_CSV,
    PARTS_DIR,
    PRODUCTS_CSV,
    STEP_HEADER_JSON,
    SUMMARY_JSON,
)

LEG_FACES_CSV = LEGS_DIR / "leg_faces.csv"
CLASSIFIED_CSV = PARTS_DIR / "parts_classified.csv"
LAYOUT_PNG = PARTS_DIR / "layout_views.png"

STEEL_DENSITY_G_CM3 = 7.85
GLASS_DENSITY_G_CM3 = 2.5
# Inventor's "일반" (Generic) material has density 1.0 g/cm^3: a placeholder.
PLACEHOLDER_DENSITY_G_CM3 = 1.0
KG_PER_MM3_PER_G_CM3 = 1e-6
M2_PER_MM2 = 1e-6
GLASS_NAME_PATTERN = re.compile(r"glass|window", re.IGNORECASE)

# User-provided: FRONT JACK CYL is the hydraulic outrigger cylinder.
JACK_PATTERN = re.compile(r"(FRONT|REAR) JACK CYL:(\d+)")
ROD_PAD_SOLID = "솔리드10"  # rod + piston + foot pad (moves with the stroke)
BARREL_SOLID = "솔리드17"  # barrel + mounting bracket (fixed to the deck)
ROD_RADIUS_MM = 55.0
BORE_RADIUS_MM = 57.5
BARREL_OUTER_RADIUS_MM = 80.0
BRACKET_HOLE_RADIUS_MM = 13.0
RADIUS_TOLERANCE_MM = 0.05

# Rows: body axes (x, y, z); columns: CAD axes (X, Y, Z).
CAD_TO_BODY = np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
LEG_ORDER = ("FL", "FR", "RL", "RR")
LEG_COLORS = {"FL": "#2a78d6", "FR": "#eb6834", "RL": "#1baf7a", "RR": "#eda100"}
OTHER_PART_COLOR = "#a8a7a0"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
SURFACE = "#fcfcfb"

INERTIA_COLUMNS = {
    (0, 0): "inertia_xx_mm5",
    (1, 1): "inertia_yy_mm5",
    (2, 2): "inertia_zz_mm5",
    (0, 1): "inertia_xy_mm5",
    (0, 2): "inertia_xz_mm5",
    (1, 2): "inertia_yz_mm5",
}
CENTROID_COLUMNS = ["centroid_x_mm", "centroid_y_mm", "centroid_z_mm"]
BBOX_MIN_COLUMNS = ["bbox_min_x_mm", "bbox_min_y_mm", "bbox_min_z_mm"]
BBOX_MAX_COLUMNS = ["bbox_max_x_mm", "bbox_max_y_mm", "bbox_max_z_mm"]


@dataclass(frozen=True)
class MassProperties:
    """Rigid-body mass properties in the CAD frame (kg, mm, kg*mm^2)."""

    mass_kg: float
    cog_mm: np.ndarray
    inertia_kg_mm2: np.ndarray

    def to_report(self) -> dict:
        """Return SI values in both CAD and body frames."""
        cog_m = self.cog_mm / 1000.0
        inertia_kg_m2 = self.inertia_kg_mm2 * M2_PER_MM2
        inertia_body = CAD_TO_BODY @ inertia_kg_m2 @ CAD_TO_BODY.T
        return {
            "mass_kg": round(self.mass_kg, 1),
            "cog_cad_m": _rounded(cog_m),
            "cog_body_m": _rounded(CAD_TO_BODY @ cog_m),
            "inertia_about_cog_body_kg_m2": _rounded(inertia_body, 1),
            "principal_moments_kg_m2": _rounded(np.linalg.eigvalsh(inertia_body), 1),
        }


def _rounded(values: np.ndarray, digits: int = 4) -> list:
    return np.round(np.asarray(values, dtype=float), digits).tolist()


# --------------------------------------------------------------------------
# Density resolution
# --------------------------------------------------------------------------
def _unique_material_by_product(products: pd.DataFrame) -> dict[str, tuple]:
    """Map product name -> (material, density) when the name is unambiguous."""
    leaves = products[products["child_count"] == 0]
    resolved = {}
    for name, group in leaves.groupby("product_name"):
        pairs = set(zip(group["material"].fillna(""), group["density_g_cm3"]))
        if len(pairs) == 1:
            resolved[name] = pairs.pop()
    return resolved


def _parent_product_name(instance_path: str) -> str:
    parent_instance = instance_path.split(" / ")[-2]
    return re.sub(r":\d+$", "", parent_instance)


def resolve_densities(parts: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Fill materials XCAF missed, using the STEP text index.

    Order: XCAF value -> unique material of the same product name -> unique
    material of the parent product (for OCC sub-shape labels such as
    ``COMPOUND``) -> assumed steel.
    """
    by_name = _unique_material_by_product(products)
    materials, densities, sources = [], [], []
    for row in parts.itertuples():
        if pd.notna(row.density_g_cm3):
            material, density, source = row.material, row.density_g_cm3, "xcaf"
        elif row.product_name in by_name:
            (material, density), source = by_name[row.product_name], "step_text"
        elif _parent_product_name(row.instance_path) in by_name:
            parent = _parent_product_name(row.instance_path)
            (material, density), source = by_name[parent], "step_text_parent"
        else:
            material, density = "(assumed steel)", STEEL_DENSITY_G_CM3
            source = "assumed"
        materials.append(material)
        densities.append(density)
        sources.append(source)
    resolved = parts.copy()
    resolved["material_resolved"] = materials
    resolved["density_step_g_cm3"] = densities
    resolved["density_source"] = sources
    return resolved


def add_mass_columns(parts: pd.DataFrame) -> pd.DataFrame:
    """Add masses for the STEP densities and for the 'generic as steel' case."""
    result = parts.copy()
    has_solid = (result["solid_count"] > 0) & (result["volume_mm3"] > 0)
    result["volume_used_mm3"] = result["volume_mm3"].where(has_solid, 0.0)
    result["is_placeholder_density"] = np.isclose(
        result["density_step_g_cm3"], PLACEHOLDER_DENSITY_G_CM3
    )
    result["is_glass"] = result["product_name"].str.contains(GLASS_NAME_PATTERN)
    corrected = result["density_step_g_cm3"].where(
        ~result["is_placeholder_density"], STEEL_DENSITY_G_CM3
    )
    result["density_generic_as_steel_g_cm3"] = corrected.where(
        ~result["is_glass"], GLASS_DENSITY_G_CM3
    )
    for case in ("step", "generic_as_steel"):
        density = result[f"density_{case}_g_cm3"] * KG_PER_MM3_PER_G_CM3
        result[f"mass_{case}_kg"] = result["volume_used_mm3"] * density
    bbox_volume = np.prod(
        result[BBOX_MAX_COLUMNS].to_numpy() - result[BBOX_MIN_COLUMNS].to_numpy(),
        axis=1,
    )
    result["bbox_fill_ratio"] = result["volume_used_mm3"] / np.where(
        bbox_volume > 0, bbox_volume, np.nan
    )
    return result


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------
def _leg_name_from_position(x_cad_mm: float, z_cad_mm: float) -> str:
    """Name a leg from its CAD position (front = +Z, left = +X)."""
    longitudinal = "F" if z_cad_mm > 0 else "R"
    lateral = "L" if x_cad_mm > 0 else "R"
    return longitudinal + lateral


def classify_parts(parts: pd.DataFrame) -> pd.DataFrame:
    """Add ``jack_instance``, ``leg``, ``group`` columns."""
    result = parts.copy()
    jack = result["instance_path"].str.extract(JACK_PATTERN)
    result["jack_instance"] = (jack[0] + " JACK CYL:" + jack[1]).fillna("")
    is_jack = result["jack_instance"] != ""
    result["leg"] = ""
    for instance, rows in result[is_jack].groupby("jack_instance"):
        center = rows[CENTROID_COLUMNS].mean()
        name = _leg_name_from_position(center["centroid_x_mm"], center["centroid_z_mm"])
        result.loc[result["jack_instance"] == instance, "leg"] = name
    is_rod = is_jack & result["instance_name"].str.startswith(ROD_PAD_SOLID)
    is_barrel = is_jack & result["instance_name"].str.startswith(BARREL_SOLID)
    result["group"] = "body"
    result.loc[is_barrel, "group"] = "leg_barrel"
    result.loc[is_rod, "group"] = "leg_rod_pad"
    return result


def detect_low_parts_geometrically(parts: pd.DataFrame) -> dict:
    """Independent check: which parts reach lowest, apart from the ground body?

    The top assembly holding the global lowest point is taken as the ground
    contact body (crawler); among the remaining parts the four lowest top
    assemblies should be the four outriggers.
    """
    lowest = parts.loc[parts["bbox_min_y_mm"].idxmin()]
    ground_assembly = lowest["top_assembly"]
    others = parts[parts["top_assembly"] != ground_assembly]
    per_assembly = others.groupby("top_assembly")["bbox_min_y_mm"].min().nsmallest(6)
    return {
        "ground_contact_assembly": ground_assembly,
        "ground_y_cad_mm": round(float(lowest["bbox_min_y_mm"]), 1),
        "lowest_other_assemblies_min_y_mm": {
            name: round(float(value), 1) for name, value in per_assembly.items()
        },
    }


# --------------------------------------------------------------------------
# Leg geometry from faces
# --------------------------------------------------------------------------
def _faces_with_radius(faces: pd.DataFrame, radius_mm: float) -> pd.DataFrame:
    return faces[
        (faces["surface_type"] == "cylinder")
        & (np.abs(faces["radius_mm"] - radius_mm) < RADIUS_TOLERANCE_MM)
    ]


def _leg_geometry(rod_faces: pd.DataFrame, barrel_faces: pd.DataFrame) -> dict:
    rod = _faces_with_radius(rod_faces, ROD_RADIUS_MM)
    axis_x = float((rod["bbox_min_x_mm"].min() + rod["bbox_max_x_mm"].max()) / 2)
    axis_z = float((rod["bbox_min_z_mm"].min() + rod["bbox_max_z_mm"].max()) / 2)
    piston = _faces_with_radius(rod_faces, BORE_RADIUS_MM)
    bore = _faces_with_radius(barrel_faces, BORE_RADIUS_MM)
    barrel = _faces_with_radius(barrel_faces, BARREL_OUTER_RADIUS_MM)
    bracket = _faces_with_radius(barrel_faces, BRACKET_HOLE_RADIUS_MM)
    piston_bottom = float(piston["bbox_min_y_mm"].min())
    piston_top = float(piston["bbox_max_y_mm"].max())
    bore_bottom = float(bore["bbox_min_y_mm"].min())
    bore_top = float(bore["bbox_max_y_mm"].max())
    pad_bottom = float(rod_faces["bbox_min_y_mm"].min())
    return {
        "axis_cad_mm": {"X": round(axis_x, 1), "Z": round(axis_z, 1)},
        "axis_direction_cad": [0.0, 1.0, 0.0],
        "pad_bottom_y_cad_mm": round(pad_bottom, 1),
        "pad_footprint_cad_mm": {
            "x": [
                round(rod_faces["bbox_min_x_mm"].min(), 1),
                round(rod_faces["bbox_max_x_mm"].max(), 1),
            ],
            "z": [
                round(rod_faces["bbox_min_z_mm"].min(), 1),
                round(rod_faces["bbox_max_z_mm"].max(), 1),
            ],
        },
        "barrel_y_cad_mm": [
            round(float(barrel["bbox_min_y_mm"].min()), 1),
            round(float(barrel["bbox_max_y_mm"].max()), 1),
        ],
        "bracket_bolt_holes_y_cad_mm": [
            round(float(bracket["bbox_min_y_mm"].min()), 1),
            round(float(bracket["bbox_max_y_mm"].max()), 1),
        ],
        "bore_y_cad_mm": [round(bore_bottom, 1), round(bore_top, 1)],
        "piston_y_cad_mm": [round(piston_bottom, 1), round(piston_top, 1)],
        "stroke_estimate_mm": round(
            (bore_top - bore_bottom) - (piston_top - piston_bottom), 1
        ),
        "remaining_extension_mm": round(piston_bottom - bore_bottom, 1),
    }


def describe_legs(parts: pd.DataFrame, faces: pd.DataFrame) -> dict:
    """Return per-leg geometry keyed by FL/FR/RL/RR."""
    legs = {}
    jack_rows = parts[parts["leg"] != ""]
    for leg, rows in jack_rows.groupby("leg"):
        instance = rows["jack_instance"].iloc[0]
        leg_faces = faces[
            faces["instance_path"].str.contains(instance + " / ", regex=False)
        ]
        rod_faces = leg_faces[leg_faces["instance_path"].str.contains(ROD_PAD_SOLID)]
        barrel_faces = leg_faces[leg_faces["instance_path"].str.contains(BARREL_SOLID)]
        geometry = _leg_geometry(rod_faces, barrel_faces)
        axis = geometry["axis_cad_mm"]
        pad_cad_m = (
            np.array([axis["X"], geometry["pad_bottom_y_cad_mm"], axis["Z"]]) / 1000
        )
        geometry["jack_instance"] = instance
        geometry["pad_center_body_m"] = _rounded(CAD_TO_BODY @ pad_cad_m)
        legs[leg] = geometry
    return {leg: legs[leg] for leg in LEG_ORDER if leg in legs}


def leg_spacing(legs: dict) -> dict:
    """Track widths, wheelbases and lateral offsets of the leg axes (mm)."""

    def axis(leg: str) -> tuple[float, float]:
        return legs[leg]["axis_cad_mm"]["X"], legs[leg]["axis_cad_mm"]["Z"]

    (fl_x, fl_z), (fr_x, fr_z) = axis("FL"), axis("FR")
    (rl_x, rl_z), (rr_x, rr_z) = axis("RL"), axis("RR")
    return {
        "front_track_mm": round(fl_x - fr_x, 1),
        "rear_track_mm": round(rl_x - rr_x, 1),
        "left_wheelbase_mm": round(fl_z - rl_z, 1),
        "right_wheelbase_mm": round(fr_z - rr_z, 1),
        "front_pair_center_x_cad_mm": round((fl_x + fr_x) / 2, 1),
        "rear_pair_center_x_cad_mm": round((rl_x + rr_x) / 2, 1),
        "leg_rectangle_center_cad_mm": {
            "X": round((fl_x + fr_x + rl_x + rr_x) / 4, 1),
            "Z": round((fl_z + fr_z + rl_z + rr_z) / 4, 1),
        },
    }


# --------------------------------------------------------------------------
# Mass properties
# --------------------------------------------------------------------------
def _part_inertia_tensors(parts: pd.DataFrame) -> np.ndarray:
    tensors = np.zeros((len(parts), 3, 3))
    for (row, column), name in INERTIA_COLUMNS.items():
        tensors[:, row, column] = parts[name].to_numpy()
        tensors[:, column, row] = parts[name].to_numpy()
    return tensors


def combine_mass_properties(parts: pd.DataFrame, case: str) -> MassProperties:
    """Combine part mass properties with the parallel-axis theorem."""
    used = parts[parts["volume_used_mm3"] > 0]
    masses = used[f"mass_{case}_kg"].to_numpy()
    densities = used[f"density_{case}_g_cm3"].to_numpy() * KG_PER_MM3_PER_G_CM3
    centroids = used[CENTROID_COLUMNS].to_numpy()
    total_mass = masses.sum()
    cog = (masses[:, None] * centroids).sum(axis=0) / total_mass
    inertia = (densities[:, None, None] * _part_inertia_tensors(used)).sum(axis=0)
    offsets = centroids - cog
    for mass, offset in zip(masses, offsets):
        inertia += mass * (offset @ offset * np.eye(3) - np.outer(offset, offset))
    return MassProperties(total_mass, cog, inertia)


def mass_report(parts: pd.DataFrame) -> dict:
    """Mass properties of the part sets used by the simulation."""
    sets = {
        "total_assembly": parts,
        "superstructure": parts[parts["group"] != "leg_rod_pad"],
        "superstructure_without_crawler": parts[
            (parts["group"] != "leg_rod_pad") & ~parts["is_crawler"]
        ],
        "leg_rod_pad_each_FL": parts[
            (parts["group"] == "leg_rod_pad") & (parts["leg"] == "FL")
        ],
        "leg_barrel_each_FL": parts[
            (parts["group"] == "leg_barrel") & (parts["leg"] == "FL")
        ],
    }
    report = {}
    for case in ("step", "generic_as_steel"):
        report[case] = {
            name: combine_mass_properties(subset, case).to_report()
            for name, subset in sets.items()
        }
    return report


def density_flags(parts: pd.DataFrame) -> dict:
    """Parts whose STEP density is doubtful, with their mass in both cases."""
    columns = [
        "instance_path",
        "material_resolved",
        "density_step_g_cm3",
        "mass_step_kg",
        "mass_generic_as_steel_kg",
        "bbox_fill_ratio",
    ]
    placeholder = parts[
        parts["is_placeholder_density"] & (parts["volume_used_mm3"] > 0)
    ]
    heavy = parts.nlargest(12, "mass_step_kg")
    return {
        "density_source_counts": parts["density_source"].value_counts().to_dict(),
        "placeholder_density_parts": placeholder[columns].round(3).to_dict("records"),
        "glass_parts_count": int(parts["is_glass"].sum()),
        "parts_without_solid": int((parts["volume_used_mm3"] == 0).sum()),
        "heaviest_parts_step": heavy[columns].round(3).to_dict("records"),
    }


# --------------------------------------------------------------------------
# Figure
# --------------------------------------------------------------------------
def _body_bbox(parts: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    lower = parts[BBOX_MIN_COLUMNS].to_numpy() @ CAD_TO_BODY.T / 1000
    upper = parts[BBOX_MAX_COLUMNS].to_numpy() @ CAD_TO_BODY.T / 1000
    return lower, upper


def _label_legs(axes, parts, lower, upper, view_axes) -> None:
    first, second = view_axes
    for leg in LEG_ORDER:
        rows = (parts["leg"] == leg).to_numpy()
        label_point = (lower[rows].min(axis=0) + upper[rows].max(axis=0)) / 2
        axes.annotate(
            leg,
            (label_point[first], label_point[second]),
            color=INK_PRIMARY,
            fontsize=9,
            fontweight="bold",
            ha="center",
            va="center",
            xytext=(0, 14),
            textcoords="offset points",
        )


def _draw_view(axes, parts, view_axes, cogs, title) -> None:
    first, second = view_axes
    lower, upper = _body_bbox(parts)
    for index, leg in enumerate(parts["leg"]):
        color = LEG_COLORS.get(leg, OTHER_PART_COLOR)
        rectangle = Rectangle(
            (lower[index, first], lower[index, second]),
            upper[index, first] - lower[index, first],
            upper[index, second] - lower[index, second],
            fill=bool(leg),
            facecolor=color,
            edgecolor=color,
            linewidth=1.0 if leg else 0.4,
            alpha=0.9 if leg else 0.6,
        )
        axes.add_patch(rectangle)
    is_top_view = second != 2
    if is_top_view:
        # In side/front views left and right legs overlap; the top view names them.
        _label_legs(axes, parts, lower, upper, view_axes)
    else:
        ground_z_m = np.nanmin(lower[:, 2])  # parts without solids have NaN bboxes
        axes.axhline(ground_z_m, color=INK_SECONDARY, linestyle="--", linewidth=0.8)
        axes.annotate(
            "crawler bottom (ground)",
            (np.nanmin(lower[:, first]), ground_z_m),
            color=INK_SECONDARY,
            fontsize=8,
            xytext=(4, -12),
            textcoords="offset points",
        )
    # The CoGs can lie within a few mm of each other: each marker style keeps
    # its own size, fill and z-order so that both stay visible when they overlap.
    for label, (cog, style) in cogs.items():
        axes.plot(cog[first], cog[second], linestyle="none", label=label, **style)
    names = ("x (forward) [m]", "y (left) [m]", "z (up) [m]")
    axes.set_xlabel(names[first], color=INK_SECONDARY)
    axes.set_ylabel(names[second], color=INK_SECONDARY)
    axes.set_title(title, color=INK_PRIMARY, fontsize=11, loc="left")
    axes.set_aspect("equal")
    axes.autoscale_view()
    axes.grid(color="#e4e3df", linewidth=0.5)
    axes.set_facecolor(SURFACE)


def draw_layout(parts: pd.DataFrame, report: dict, png_path: Path) -> None:
    """Top, side and front views of the part bounding boxes (body frame)."""
    step_case = report["step"]
    # Superstructure: small filled X. Total: larger hollow ring drawn on top,
    # so it encircles the X instead of hiding under it.
    cogs = {
        "CoG superstructure": (
            np.array(step_case["superstructure"]["cog_body_m"]),
            {"marker": "X", "markersize": 8, "color": INK_PRIMARY, "zorder": 5},
        ),
        "CoG total": (
            np.array(step_case["total_assembly"]["cog_body_m"]),
            {
                "marker": "o",
                "markersize": 16,
                "markerfacecolor": "none",
                "markeredgecolor": INK_PRIMARY,
                "markeredgewidth": 1.6,
                "zorder": 6,
            },
        ),
    }
    figure, axes = plt.subplots(
        1,
        3,
        figsize=(18, 7),
        facecolor=SURFACE,
        gridspec_kw={"width_ratios": [1.6, 1.6, 1.0]},
    )
    _draw_view(axes[0], parts, (0, 1), cogs, "Top view (x-y), body frame")
    _draw_view(axes[1], parts, (0, 2), cogs, "Side view (x-z)")
    _draw_view(axes[2], parts, (1, 2), cogs, "Front view (y-z)")
    handles = [Rectangle((0, 0), 1, 1, color=LEG_COLORS[leg]) for leg in LEG_ORDER]
    handles.append(Rectangle((0, 0), 1, 1, fill=False, edgecolor=OTHER_PART_COLOR))
    labels = [f"{leg} jack cylinder" for leg in LEG_ORDER] + ["other part bbox"]
    marker_handles, marker_labels = axes[0].get_legend_handles_labels()
    figure.legend(
        handles + marker_handles,
        labels + marker_labels,
        loc="lower center",
        ncol=7,
        frameon=False,
        labelcolor=INK_SECONDARY,
    )
    figure.suptitle(
        "REXOME33 part bounding boxes  (x_body = Z_cad, y_body = X_cad, "
        "z_body = Y_cad; origin = CAD origin)",
        color=INK_PRIMARY,
    )
    figure.tight_layout(rect=(0, 0.06, 1, 0.95))
    figure.savefig(png_path, dpi=130, facecolor=SURFACE)
    plt.close(figure)


# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------
def overall_extent(parts: pd.DataFrame) -> dict:
    lower = parts[BBOX_MIN_COLUMNS].min().to_numpy()
    upper = parts[BBOX_MAX_COLUMNS].max().to_numpy()
    return {
        "bbox_min_cad_mm": _rounded(lower, 1),
        "bbox_max_cad_mm": _rounded(upper, 1),
        "size_cad_mm": {
            "X": round(upper[0] - lower[0], 1),
            "Y": round(upper[1] - lower[1], 1),
            "Z": round(upper[2] - lower[2], 1),
        },
    }


def build_summary(parts, header, legs, low_parts, report) -> dict:
    return {
        "source_step": header,
        "length_unit": "mm (all 753 geometric contexts use SI_UNIT(.MILLI.,.METRE.))",
        "extent": overall_extent(parts),
        "axes": {
            "cad_up": "+Y",
            "cad_forward": "+Z (FRONT JACK CYL side)",
            "cad_left": "+X",
            "cad_to_body_matrix": CAD_TO_BODY.tolist(),
        },
        "user_provided": "FRONT JACK CYL = hydraulic outrigger cylinder",
        "legs": legs,
        "leg_spacing": leg_spacing(legs),
        "geometric_low_part_check": low_parts,
        "mass_properties": report,
        "density_review": density_flags(parts),
        "mass_cases": {
            "step": "densities from STEP material properties (Inventor 'Generic' = 1.0 kept)",
            "generic_as_steel": "Generic 1.0 g/cm^3 replaced by steel 7.85, glass by 2.5",
        },
    }


def main() -> None:
    parts = pd.read_csv(PARTS_CSV, encoding="utf-8-sig")
    products = pd.read_csv(PRODUCTS_CSV, encoding="utf-8-sig")
    faces = pd.read_csv(LEG_FACES_CSV, encoding="utf-8-sig")
    header = json.loads(STEP_HEADER_JSON.read_text(encoding="utf-8"))

    parts = add_mass_columns(resolve_densities(parts, products))
    parts = classify_parts(parts)
    low_parts = detect_low_parts_geometrically(parts)
    parts["is_crawler"] = parts["top_assembly"] == low_parts["ground_contact_assembly"]
    legs = describe_legs(parts, faces)
    report = mass_report(parts)

    parts.to_csv(CLASSIFIED_CSV, index=False, encoding="utf-8-sig")
    summary = build_summary(parts, header, legs, low_parts, report)
    SUMMARY_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    draw_layout(parts, report, LAYOUT_PNG)
    print(f"wrote {CLASSIFIED_CSV.name}, {SUMMARY_JSON.name}, {LAYOUT_PNG.name}")


if __name__ == "__main__":
    main()
