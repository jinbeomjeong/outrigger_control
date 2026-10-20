"""Beam properties of the upright mast for the first bending frequency (roadmap C9).

CAD extraction only; the frequency figures at the end are a rough reference for
dynamics-expert, not a verdict.

Reads only cached data (no STEP parsing):
    01_cad/06_brep/                         B-rep cache (brep_cache.py), exact geometry
    01_cad/01_parts/parts_classified.csv    per-part volume, centroid, inertia, density
    01_cad/04_mast/mast_parts.csv           rotating set of the mast (fold study)
    01_cad/04_mast/mast_summary.json        hinge pin, backstay pivots and cylinder geometry
    01_cad/03_auger/auger_parts.csv         auger moving set (drive + tool)
    01_cad/03_auger/auger_levels.json       travel of the three auger levels
    02_params/rexome33.yaml                 moving set at the CAD pose (check only)

Writes:
    01_cad/04_mast/mast_beam_properties.json   members, supports, attachments, beam table,
                                               checks, reference frequency estimates
    01_cad/04_mast/mast_beam_properties.csv    one row per 50 mm slice along the mast
    01_cad/04_mast/mast_sections.png           representative cross-sections
    01_cad/04_mast/mast_sections_distribution.png   A, I, J and mass per length vs height

Frames and units. CAD root frame in mm, Y up. Body frame (CLAUDE.md): x = Z_cad
(forward), y = X_cad (left), z = Y_cad (up), origin = CAD origin; outputs are SI.
The mast axis is parallel to body z (rack-bar fit tilt 2.3e-5 deg,
auger_levels.json), so a cut "at height z" is the plane Y_cad = 1000 z.

Section properties are taken about the centroid of the cut, in body axes:
    Iy  = integral (x - x_c)^2 dA  -> bending in the x-z plane (fore-aft deflection)
    Ix  = integral (y - y_c)^2 dA  -> bending in the y-z plane (lateral deflection)
    Ixy = integral (x - x_c)(y - y_c) dA (product, not the tensor sign)
J is the Saint-Venant torsion constant from a finite-difference Prandtl stress
function on a 1 mm raster of the cut (closed cells handled as rigid plates that
carry the same pressure, i.e. the membrane analogy).

Method. Each welded mast segment (MAST, MAST-2 .. MAST-5) is a compound of plate
solids. Every solid gets a role from its bounding box (channel, front plate,
corner rail, rack bar, local plate, flange, diaphragm, ladder) and the roles
decide whether it counts for stiffness. A section is the union of the planar
faces that ``BRepAlgoAPI_Common(solid, thin slab)`` leaves on the cutting plane.
Mass per slice comes from half-space volumes of every solid (exact B-rep).

Usage:
    python -I 04_scripts/00_cad/extract_mast_beam.py [--raster-mm 1.0] [--skip-plots]
"""

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.sparse as sparse
import scipy.sparse.linalg as sparse_linalg
import yaml
from matplotlib.collections import PolyCollection
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Core.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
from OCC.Core.gp import gp_Pnt
from OCC.Core.GProp import GProp_GProps
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_SOLID
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.TopoDS import TopoDS_Shape, topods
from scipy import linalg, ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brep_cache
from cad_common import AUGER_DIR, MAST_DIR, PARTS_DIR, PROJECT_ROOT

# --------------------------------------------------------------------------
# Inputs, outputs, constants
# --------------------------------------------------------------------------
PARTS_CLASSIFIED_CSV = PARTS_DIR / "parts_classified.csv"
MAST_PARTS_CSV = MAST_DIR / "mast_parts.csv"
MAST_SUMMARY_JSON = MAST_DIR / "mast_summary.json"
AUGER_PARTS_CSV = AUGER_DIR / "auger_parts.csv"
AUGER_LEVELS_JSON = AUGER_DIR / "auger_levels.json"
PARAMS_YAML = PROJECT_ROOT / "02_params" / "rexome33.yaml"

OUT_JSON = MAST_DIR / "mast_beam_properties.json"
OUT_CSV = MAST_DIR / "mast_beam_properties.csv"
OUT_SECTIONS_PNG = MAST_DIR / "mast_sections.png"
OUT_DISTRIBUTION_PNG = MAST_DIR / "mast_sections_distribution.png"

CAD_TO_BODY = np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
MM = 1e-3
GRAVITY = 9.80665  # m/s^2, same value as the other CAD scripts

# Material. The mast plates are "강, 연강" 7.85 g/cm^3 in the STEP file (case A = C here).
STEEL_DENSITY_KG_M3 = 7850.0
STEEL_E_PA = 210e9  # ASSUMPTION: structural steel, not in the STEP file
STEEL_POISSON = 0.3  # ASSUMPTION
STEEL_G_PA = STEEL_E_PA / (2.0 * (1.0 + STEEL_POISSON))  # 80.8 GPa
# Hydraulic oil bulk modulus: project decision 1.0 GPa, sensitivity 0.69 .. 1.6 GPa (CLAUDE.md).
BULK_MODULUS_PA = {"low": 0.69e9, "reference": 1.0e9, "high": 1.6e9}

# Slices along the mast (CAD Y, mm). Edges every 50 mm; sections are cut at slice centres.
SLICE_MM = 50.0
SLICE_START_MM = -700.0
SLICE_END_MM = 9900.0

MAST_TOP = "MAST ASSY:1"
SEGMENTS = ("MAST", "MAST-2", "MAST-3", "MAST-4", "MAST-5")  # welded segments, bottom to top
TOPSHEAVE_TOP = "TOPSHEAVE(조립) ASSY:1"
LOWER_GUIDE_TOP = "LOWER GUIDE_ASSY:1"
WINCH_TOP = "윈치:1"
BACKSTAY_TOP = "BACKSTAY CYL:1"
BOOM_CYL_TOP = "BOOM CYL:1"
DRIVE_TOP = "0. DRIVE AUGER ASSY:1"
TOOL_TOP = "AUGER TOOL:1"
LEVELS = ("top", "middle", "bottom")

# Roles of the solids inside the mast segments.
CONTINUOUS_ROLES = (
    "channel",
    "front_plate",
    "corner_rail",
    "rack_bar",
    "longitudinal_other",
    "local",
)
TRANSVERSE_ROLES = ("flange", "diaphragm")
# Transverse plates carry the load through their thickness in the joint zones, so they count
# for stiffness; their effect is only over their thickness (see the slice-effective values).
STIFFNESS_ROLES = CONTINUOUS_ROLES + TRANSVERSE_ROLES
SUBCUT_MM = 5.0  # sub-cuts per slice for the slice-effective (harmonic mean) properties
ROLE_NOTES = {
    "channel": "bent C channel, rear web + two side flanges (main box)",
    "front_plate": "front plate closing the channel into a box (main box)",
    "corner_rail": "square bar on the front corners; guide rail of the drive shoes",
    "rack_bar": "bar on the front centre that carries the rack gears",
    "longitudinal_other": "other plate running along most of the segment",
    "local": "welded local plate (hinge plates, boss, lugs, gussets, end blocks)",
    "flange": "segment end flange (bolted joint), transverse plate; stiffness over its thickness",
    "diaphragm": "transverse diaphragm inside the box; stiffness over its thickness",
    "ladder": "ladder rails, rungs and brackets on the +y side: non-structural, mass only",
    "rack": "rack gear bars, 995 mm long with 5 mm gaps: mass only",
    "pin_bush": "pins, bushes, key plates, space rings: mass only",
}

SECTION_PANELS_MM = (-525.0, 275.0, 1325.0, 2025.0, 4125.0, 4875.0, 7025.0, 9325.0)


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def body_point(point_cad_mm) -> np.ndarray:
    """CAD point (mm) -> body point (m)."""
    return CAD_TO_BODY @ (np.asarray(point_cad_mm, dtype=float) * MM)


def body_inertia(inertia_cad_kg_mm2: np.ndarray) -> np.ndarray:
    """Inertia tensor CAD axes (kg mm^2) -> body axes (kg m^2)."""
    return CAD_TO_BODY @ (inertia_cad_kg_mm2 * 1e-6) @ CAD_TO_BODY.T


def round_list(values, digits: int = 6) -> list:
    return [float(f"{float(v):.{digits}g}") for v in np.asarray(values, dtype=float).ravel()]


def tensor_checks(inertia: np.ndarray) -> dict:
    eigenvalues = np.sort(np.linalg.eigvalsh(0.5 * (inertia + inertia.T)))
    return {
        "symmetric": bool(
            np.allclose(inertia, inertia.T, rtol=0, atol=1e-9 * np.abs(inertia).max())
        ),
        "positive_definite": bool(eigenvalues[0] > 0),
        "triangle_inequality": bool(
            eigenvalues[0] + eigenvalues[1] >= eigenvalues[2] * (1 - 1e-12)
        ),
        "principal_kg_m2": round_list(eigenvalues),
    }


def bounding_box(shape: TopoDS_Shape) -> np.ndarray:
    box = Bnd_Box()
    brepbndlib.AddOptimal(shape, box, False, False)
    return np.array(box.Get())  # xmin, ymin, zmin, xmax, ymax, zmax (CAD mm)


def volume_properties(shape: TopoDS_Shape) -> tuple[float, np.ndarray]:
    props = GProp_GProps()
    brepgprop.VolumeProperties(shape, props)
    centre = props.CentreOfMass()
    return props.Mass(), np.array([centre.X(), centre.Y(), centre.Z()])


def slab(y_low: float, y_high: float) -> TopoDS_Shape:
    """Box covering the whole mast footprint between two CAD Y values (mm)."""
    return BRepPrimAPI_MakeBox(
        gp_Pnt(-3000.0, y_low, -1000.0), gp_Pnt(3000.0, y_high, 7000.0)
    ).Shape()


# --------------------------------------------------------------------------
# Mast solids and their roles
# --------------------------------------------------------------------------
@dataclass
class MastSolid:
    part: str  # short part name inside MAST ASSY (e.g. "MAST-3:1")
    segment: str | None  # product name of the welded segment, None for loose parts
    index: int  # solid index inside the part
    shape: TopoDS_Shape = field(repr=False)
    bbox: np.ndarray  # CAD mm
    volume_mm3: float
    centroid_mm: np.ndarray
    role: str = ""

    @property
    def stiffness(self) -> bool:
        return self.role in STIFFNESS_ROLES

    @property
    def y_range(self) -> tuple[float, float]:
        return float(self.bbox[1]), float(self.bbox[4])


def classify_solid(solid: MastSolid, segment_length_mm: float) -> str:
    """Role of one solid from its part, segment and bounding box (CAD mm)."""
    if solid.segment is None:
        return "rack" if solid.part.startswith("RACK GEAR") else "pin_bush"
    dx, dy, dz = solid.bbox[3:] - solid.bbox[:3]
    x_min, x_max = solid.bbox[0], solid.bbox[3]
    if dy <= 40.0 and dx >= 400.0:
        return "flange" if dy >= 30.0 else "diaphragm"
    one_side = x_min >= 270.0 or x_max <= -270.0
    if solid.segment != "MAST" and one_side and max(abs(x_min), abs(x_max)) >= 379.9:
        return "ladder"
    if dy >= 0.5 * segment_length_mm:
        if dx >= 550.0 and dz >= 400.0:
            return "channel"
        if dz <= 12.0 and dx >= 500.0:
            return "front_plate"
        if abs(dx - 80.0) < 1.0 and abs(dz - 80.0) < 1.0:
            return "corner_rail"
        if dx <= 40.5 and dz >= 80.0:
            return "rack_bar"
        return "longitudinal_other"
    return "local"


def load_mast_solids() -> list[MastSolid]:
    """All solids of MAST ASSY from the B-rep cache, placed in the CAD frame, with roles."""
    solids: list[MastSolid] = []
    for instance in brep_cache.iter_instances(top_assembly=MAST_TOP):
        part = instance.instance_path.split(" / ")[-1]
        product = instance.product_name
        segment = product if product in SEGMENTS else None
        shape = brep_cache.load_part(instance.instance_path)
        explorer = TopExp_Explorer(shape, TopAbs_SOLID)
        index = 0
        while explorer.More():
            solid_shape = explorer.Current()
            volume, centroid = volume_properties(solid_shape)
            solids.append(
                MastSolid(
                    part, segment, index, solid_shape, bounding_box(solid_shape), volume, centroid
                )
            )
            index += 1
            explorer.Next()
    lengths = {}
    for solid in solids:
        if solid.segment is not None:
            low, high = lengths.get(solid.segment, (math.inf, -math.inf))
            lengths[solid.segment] = (min(low, solid.bbox[1]), max(high, solid.bbox[4]))
    for solid in solids:
        length = (
            0.0 if solid.segment is None else lengths[solid.segment][1] - lengths[solid.segment][0]
        )
        solid.role = classify_solid(solid, length)
    return solids


def segment_ranges(solids: list[MastSolid]) -> dict:
    ranges = {}
    for solid in solids:
        if solid.segment is not None:
            low, high = ranges.get(solid.segment, (math.inf, -math.inf))
            ranges[solid.segment] = (min(low, solid.bbox[1]), max(high, solid.bbox[4]))
    return {name: ranges[name] for name in SEGMENTS}


def overlap_check(solids: list[MastSolid]) -> dict:
    """Common volume of every pair of mast solids whose boxes overlap by more than 0.5 mm."""
    pairs, total, worst = 0, 0.0, []
    for i in range(len(solids)):
        for j in range(i + 1, len(solids)):
            a, b = solids[i].bbox, solids[j].bbox
            overlap = np.minimum(a[3:], b[3:]) - np.maximum(a[:3], b[:3])
            if np.any(overlap <= 0.5):
                continue
            pairs += 1
            volume, _ = volume_properties(
                BRepAlgoAPI_Common(solids[i].shape, solids[j].shape).Shape()
            )
            if volume > 1.0:
                total += volume
                worst.append(
                    (
                        volume,
                        f"{solids[i].part}#{solids[i].index}",
                        f"{solids[j].part}#{solids[j].index}",
                    )
                )
    worst.sort(reverse=True)
    return {
        "pairs_checked": pairs,
        "overlap_volume_mm3": round(total, 1),
        "overlap_mass_kg": round(total * STEEL_DENSITY_KG_M3 * 1e-9, 3),
        "largest": [{"volume_mm3": round(v, 1), "a": a, "b": b} for v, a, b in worst[:8]],
    }


def flange_holes(solids: list[MastSolid]) -> list[dict]:
    """Cylindrical holes along the mast axis in the segment flanges (bolted joints)."""
    found = []
    for solid in solids:
        if solid.role != "flange":
            continue
        radii = []
        explorer = TopExp_Explorer(solid.shape, TopAbs_FACE)
        while explorer.More():
            surface = BRepAdaptor_Surface(topods.Face(explorer.Current()))
            if surface.GetType() == GeomAbs_Cylinder:
                cylinder = surface.Cylinder()
                direction = cylinder.Axis().Direction()
                if abs(direction.Y()) > 0.999:
                    radii.append(round(cylinder.Radius(), 2))
            explorer.Next()
        values, counts = np.unique(radii, return_counts=True)
        found.append(
            {
                "part": solid.part,
                "solid": solid.index,
                "y_cad_mm": [round(solid.bbox[1], 1), round(solid.bbox[4], 1)],
                "cylindrical_faces_along_axis": {
                    f"R{v:g}": int(c) for v, c in zip(values, counts, strict=True)
                },
            }
        )
    return found


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------
@dataclass
class SectionPiece:
    area_mm2: float
    centroid_xz_mm: np.ndarray  # (X_cad, Z_cad) of the piece
    moments_mm4: np.ndarray  # OCCT matrix about the piece centroid (CAD axes)
    triangles: np.ndarray  # (n, 3, 2) in body (x, y) mm = (Z_cad, X_cad)
    perimeter_mm: float
    bbox_body_mm: np.ndarray  # x_min, y_min, x_max, y_max
    role: str
    part: str


def section_pieces(solid: MastSolid, y0: float) -> list[SectionPiece]:
    """Planar faces of ``solid`` on the plane Y_cad = y0 (via Common with a 1 mm slab)."""
    common = BRepAlgoAPI_Common(solid.shape, slab(y0, y0 + 1.0)).Shape()
    pieces = []
    explorer = TopExp_Explorer(common, TopAbs_FACE)
    while explorer.More():
        face = topods.Face(explorer.Current())
        surface = BRepAdaptor_Surface(face)
        if surface.GetType() == GeomAbs_Plane:
            normal = surface.Plane().Axis().Direction()
            props = GProp_GProps()
            brepgprop.SurfaceProperties(face, props)
            centre = props.CentreOfMass()
            if abs(abs(normal.Y()) - 1.0) < 1e-9 and abs(centre.Y() - y0) < 1e-6:
                matrix = props.MatrixOfInertia()
                moments = np.array([[matrix.Value(r, c) for c in (1, 2, 3)] for r in (1, 2, 3)])
                line = GProp_GProps()
                brepgprop.LinearProperties(face, line)
                triangles = face_triangles(face)
                bbox = bounding_box(face)
                pieces.append(
                    SectionPiece(
                        area_mm2=props.Mass(),
                        centroid_xz_mm=np.array([centre.X(), centre.Z()]),
                        moments_mm4=moments,
                        triangles=triangles,
                        perimeter_mm=line.Mass(),
                        bbox_body_mm=np.array([bbox[2], bbox[0], bbox[5], bbox[3]]),
                        role=solid.role,
                        part=f"{solid.part}#{solid.index}",
                    )
                )
        explorer.Next()
    return pieces


def face_triangles(face) -> np.ndarray:
    """Triangulation of a planar section face in body (x, y) mm = (Z_cad, X_cad)."""
    BRepMesh_IncrementalMesh(face, 0.05, False, 0.1, True)
    location = TopLoc_Location()
    triangulation = BRep_Tool.Triangulation(face, location)
    if triangulation is None:
        return np.zeros((0, 3, 2))
    transform = location.Transformation()
    nodes = []
    for k in range(1, triangulation.NbNodes() + 1):
        point = triangulation.Node(k).Transformed(transform)
        nodes.append((point.Z(), point.X()))
    nodes = np.asarray(nodes)
    triangles = np.array(
        [triangulation.Triangle(k).Get() for k in range(1, triangulation.NbTriangles() + 1)]
    )
    return nodes[triangles - 1]


def combine_pieces(pieces: list[SectionPiece]) -> dict:
    """Area, centroid and second moments (body axes, about the joint centroid), SI units."""
    area = sum(p.area_mm2 for p in pieces)
    if area <= 0.0:
        return {"A_m2": 0.0}
    # body x = Z_cad, body y = X_cad
    x = np.array([p.centroid_xz_mm[1] for p in pieces])
    y = np.array([p.centroid_xz_mm[0] for p in pieces])
    a = np.array([p.area_mm2 for p in pieces])
    x_c, y_c = a @ x / area, a @ y / area
    # OCCT matrix about the piece centroid: M_XX = int (Z-Zc)^2, M_ZZ = int (X-Xc)^2,
    # M_XZ = -int (X-Xc)(Z-Zc)
    iy = sum(p.moments_mm4[0, 0] for p in pieces) + a @ (x - x_c) ** 2
    ix = sum(p.moments_mm4[2, 2] for p in pieces) + a @ (y - y_c) ** 2
    ixy = sum(-p.moments_mm4[0, 2] for p in pieces) + a @ ((x - x_c) * (y - y_c))
    centre, radius = 0.5 * (iy + ix), math.hypot(0.5 * (iy - ix), ixy)
    angle = 0.5 * math.degrees(math.atan2(-2.0 * ixy, iy - ix))
    return {
        "A_m2": area * 1e-6,
        "x_c_m": x_c * MM,
        "y_c_m": y_c * MM,
        "Iy_m4": iy * 1e-12,
        "Ix_m4": ix * 1e-12,
        "Ixy_m4": ixy * 1e-12,
        "I_max_m4": (centre + radius) * 1e-12,
        "I_min_m4": (centre - radius) * 1e-12,
        "principal_angle_deg": angle,
    }


def cut_at(
    solids: list["MastSolid"], y0: float, torsion_cache: dict, raster_mm: float
) -> tuple[list[SectionPiece], dict, dict]:
    """Structural cut at CAD Y = y0: pieces, combined properties and torsion (cached by shape)."""
    pieces = []
    for solid in solids:
        low, high = solid.y_range
        if solid.stiffness and low < y0 < high:
            pieces += section_pieces(solid, y0)
    props = combine_pieces(pieces)
    if not pieces:
        return pieces, props, {"J_mm4": 0.0, "closed_cells": 0, "raster_area_rel_diff": 0.0}
    signature = section_signature(pieces)
    if signature not in torsion_cache:
        mask, _, _ = rasterize(np.concatenate([p.triangles for p in pieces]), raster_mm)
        result = torsion_constant(mask, raster_mm)
        result["raster_area_rel_diff"] = (
            result["material_cells"] * raster_mm**2 / (props["A_m2"] * 1e6) - 1.0
        )
        torsion_cache[signature] = result
    return pieces, props, torsion_cache[signature]


def section_signature(pieces: list[SectionPiece]) -> tuple:
    """Shape key that is the same for identical cuts at different heights."""
    return tuple(
        sorted(
            (round(p.area_mm2, 0), round(p.centroid_xz_mm[0], 0), round(p.centroid_xz_mm[1], 0))
            for p in pieces
        )
    )


# --------------------------------------------------------------------------
# Torsion constant (Prandtl stress function on a raster)
# --------------------------------------------------------------------------
def rasterize(triangles: np.ndarray, cell_mm: float) -> tuple[np.ndarray, float, float]:
    """Boolean mask of cells whose centres lie inside any triangle; grid aligned to integer mm."""
    points = triangles.reshape(-1, 2)
    x0 = math.floor(points[:, 0].min()) - 3.0 * cell_mm
    y0 = math.floor(points[:, 1].min()) - 3.0 * cell_mm
    nx = int(math.ceil((points[:, 0].max() + 3.0 * cell_mm - x0) / cell_mm))
    ny = int(math.ceil((points[:, 1].max() + 3.0 * cell_mm - y0) / cell_mm))
    mask = np.zeros((nx, ny), dtype=bool)
    for tri in triangles:
        lo = np.floor((tri.min(axis=0) - (x0, y0)) / cell_mm).astype(int)
        hi = np.ceil((tri.max(axis=0) - (x0, y0)) / cell_mm).astype(int)
        ix = np.arange(max(lo[0], 0), min(hi[0] + 1, nx))
        iy = np.arange(max(lo[1], 0), min(hi[1] + 1, ny))
        if ix.size == 0 or iy.size == 0:
            continue
        gx, gy = np.meshgrid(x0 + (ix + 0.5) * cell_mm, y0 + (iy + 0.5) * cell_mm, indexing="ij")
        (ax, ay), (bx, by), (cx, cy) = tri
        d1 = (gx - bx) * (ay - by) - (ax - bx) * (gy - by)
        d2 = (gx - cx) * (by - cy) - (bx - cx) * (gy - cy)
        d3 = (gx - ax) * (cy - ay) - (cx - ax) * (gy - ay)
        negative = (d1 < 0) | (d2 < 0) | (d3 < 0)
        positive = (d1 > 0) | (d2 > 0) | (d3 > 0)
        inside = ~(negative & positive)
        mask[np.ix_(ix, iy)] |= inside
    return mask, x0, y0


def torsion_constant(mask: np.ndarray, cell_mm: float) -> dict:
    """Saint-Venant J of a rasterised section (mm^4) and the number of closed cells.

    Prandtl stress function: -laplace(phi) = 2 in the material, phi = 0 on the outer
    boundary. Each hole is one unknown (constant phi) whose equation is the
    equilibrium of a rigid plate loaded by the same pressure (membrane analogy),
    which is the single-valued warping condition. J = 2 * integral(phi) over the
    material and the holes. Boundaries sit on cell faces (half a cell from the
    centres), so a boundary face has conductance 2.
    """
    labels, count = ndimage.label(~mask)
    border = set(np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])))
    holes = [k for k in range(1, count + 1) if k not in border]
    index = -np.ones(mask.shape, dtype=np.int64)
    n_material = int(mask.sum())
    index[mask] = np.arange(n_material)
    hole_index = {k: n_material + i for i, k in enumerate(holes)}
    for k, unknown in hole_index.items():
        index[labels == k] = unknown
    exterior = index < 0
    n = n_material + len(holes)
    rows, cols, vals = [], [], []
    diagonal = np.zeros(n)
    rhs = np.zeros(n)
    rhs[:n_material] = 2.0 * cell_mm**2
    for k in holes:
        rhs[hole_index[k]] = 2.0 * cell_mm**2 * int((labels == k).sum())
    # faces between neighbouring cells along both grid directions
    for axis in (0, 1):
        a = index.take(range(0, mask.shape[axis] - 1), axis=axis)
        b = index.take(range(1, mask.shape[axis]), axis=axis)
        ma = mask.take(range(0, mask.shape[axis] - 1), axis=axis)
        mb = mask.take(range(1, mask.shape[axis]), axis=axis)
        ea = exterior.take(range(0, mask.shape[axis] - 1), axis=axis)
        eb = exterior.take(range(1, mask.shape[axis]), axis=axis)
        # material-material and material-hole: conductance 1 (centre to centre) or 2 (to hole face)
        both = (ma | mb) & ~ea & ~eb & (a != b)
        conductance = np.where(ma & mb, 1.0, 2.0)[both]
        ia, ib = a[both], b[both]
        np.add.at(diagonal, ia, conductance)
        np.add.at(diagonal, ib, conductance)
        rows += [ia, ib]
        cols += [ib, ia]
        vals += [-conductance, -conductance]
        # material next to the exterior: Dirichlet phi = 0 on the face
        to_outside = (ma & eb) | (mb & ea)
        inner = np.where(ma, a, b)[to_outside]
        np.add.at(diagonal, inner, 2.0)
    matrix = sparse.csr_matrix(
        (np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)
    ) + sparse.diags(diagonal)
    phi = sparse_linalg.spsolve(matrix.tocsc(), rhs)
    j_mm4 = (
        2.0
        * cell_mm**2
        * (
            phi[:n_material].sum()
            + sum(phi[hole_index[k]] * int((labels == k).sum()) for k in holes)
        )
    )
    return {"J_mm4": float(j_mm4), "closed_cells": len(holes), "material_cells": n_material}


def torsion_self_test(cell_mm: float) -> dict:
    """FD solver against closed forms: solid square and a thin rectangular tube (Bredt)."""

    def rect(x0, y0, x1, y1):
        return np.array(
            [[(x0, y0), (x1, y0), (x1, y1)], [(x0, y0), (x1, y1), (x0, y1)]], dtype=float
        )

    side = 100.0
    square = torsion_constant(rasterize(rect(0, 0, side, side), cell_mm)[0], cell_mm)["J_mm4"]
    square_exact = 0.140577 * side**4  # Timoshenko, b/a = 1
    outer_w, outer_h, t = 560.0, 430.0, 10.0
    tube = np.concatenate(
        [
            rect(0, 0, outer_w, t),
            rect(0, outer_h - t, outer_w, outer_h),
            rect(0, t, t, outer_h - t),
            rect(outer_w - t, t, outer_w, outer_h - t),
        ]
    )
    tube_fd = torsion_constant(rasterize(tube, cell_mm)[0], cell_mm)
    mid_w, mid_h = outer_w - t, outer_h - t
    bredt = 4.0 * (mid_w * mid_h) ** 2 * t / (2.0 * (mid_w + mid_h))
    return {
        "cell_mm": cell_mm,
        "solid_square_100mm": {
            "fd_mm4": square,
            "exact_mm4": square_exact,
            "rel_diff": square / square_exact - 1.0,
        },
        "box_560x430x10": {
            "fd_mm4": tube_fd["J_mm4"],
            "bredt_mm4": bredt,
            "rel_diff": tube_fd["J_mm4"] / bredt - 1.0,
            "closed_cells": tube_fd["closed_cells"],
        },
    }


# --------------------------------------------------------------------------
# Mass per slice
# --------------------------------------------------------------------------
def slice_masses(solids: list[MastSolid], edges: np.ndarray) -> dict:
    """Exact volume and first moments of every solid between consecutive edges (CAD Y mm).

    Uses the volume below each edge (Common with a half-space box); differences give the slices.
    Returns arrays per role group: volume (mm^3) and volume-weighted X, Z (mm^4).
    """
    groups = ("plates", "flange_diaphragm", "ladder", "rack_pin")
    out = {
        g: {
            "V": np.zeros(len(edges) - 1),
            "VX": np.zeros(len(edges) - 1),
            "VZ": np.zeros(len(edges) - 1),
        }
        for g in groups
    }
    total_from_solids = 0.0
    for solid in solids:
        group = (
            "plates"
            if solid.role in CONTINUOUS_ROLES
            else "flange_diaphragm"
            if solid.role in TRANSVERSE_ROLES
            else "ladder"
            if solid.role == "ladder"
            else "rack_pin"
        )
        y_low, y_high = solid.y_range
        below = np.zeros((len(edges), 3))  # V, VX, VZ below each edge
        for k, edge in enumerate(edges):
            if edge <= y_low:
                continue
            if edge >= y_high:
                below[k] = (
                    solid.volume_mm3,
                    solid.volume_mm3 * solid.centroid_mm[0],
                    solid.volume_mm3 * solid.centroid_mm[2],
                )
                continue
            volume, centre = volume_properties(
                BRepAlgoAPI_Common(solid.shape, slab(y_low - 10.0, edge)).Shape()
            )
            below[k] = (volume, volume * centre[0], volume * centre[2])
        pieces = np.diff(below, axis=0)
        out[group]["V"] += pieces[:, 0]
        out[group]["VX"] += pieces[:, 1]
        out[group]["VZ"] += pieces[:, 2]
        total_from_solids += solid.volume_mm3
    out["solid_volume_total_mm3"] = total_from_solids
    return out


# --------------------------------------------------------------------------
# Lumped attachments from the parts table
# --------------------------------------------------------------------------
def load_parts() -> pd.DataFrame:
    parts = pd.read_csv(PARTS_CLASSIFIED_CSV, encoding="utf-8-sig")
    auger = pd.read_csv(AUGER_PARTS_CSV, encoding="utf-8-sig")[["instance_path", "motion"]]
    parts = parts.merge(auger, on="instance_path", how="left")
    # Case C (CLAUDE.md): STEP densities, the five AUGER TOOL rows as steel.
    is_tool = parts["top_assembly"] == TOOL_TOP
    parts["density_c_g_cm3"] = parts["density_step_g_cm3"].where(~is_tool, 7.85)
    parts["mass_c_kg"] = (
        parts["volume_used_mm3"].fillna(0.0) * parts["density_c_g_cm3"].fillna(0.0) * 1e-6
    )
    return parts


def mass_properties(rows: pd.DataFrame, offset_y_mm: float = 0.0) -> dict:
    """Mass, CoG and inertia about the CoG (body axes) of parts-table rows, case C."""
    rows = rows[rows["volume_used_mm3"].fillna(0.0) > 0.0]
    rho = rows["density_c_g_cm3"].to_numpy() * 1e-6  # kg/mm^3
    mass = rows["volume_used_mm3"].to_numpy() * rho
    centroid = rows[["centroid_x_mm", "centroid_y_mm", "centroid_z_mm"]].to_numpy().copy()
    centroid[:, 1] += offset_y_mm
    total = float(mass.sum())
    com = mass @ centroid / total
    inertia = np.zeros((3, 3))
    columns = {
        (0, 0): "inertia_xx_mm5",
        (1, 1): "inertia_yy_mm5",
        (2, 2): "inertia_zz_mm5",
        (0, 1): "inertia_xy_mm5",
        (0, 2): "inertia_xz_mm5",
        (1, 2): "inertia_yz_mm5",
    }
    for (i, j), column in columns.items():
        inertia[i, j] = inertia[j, i] = float((rows[column].to_numpy() * rho).sum())
    d = centroid - com
    inertia += (mass * (d * d).sum(axis=1)).sum() * np.eye(3) - np.einsum("k,ki,kj->ij", mass, d, d)
    bbox_min = rows[["bbox_min_x_mm", "bbox_min_y_mm", "bbox_min_z_mm"]].min().to_numpy(copy=True)
    bbox_max = rows[["bbox_max_x_mm", "bbox_max_y_mm", "bbox_max_z_mm"]].max().to_numpy(copy=True)
    bbox_min[1] += offset_y_mm
    bbox_max[1] += offset_y_mm
    corners = np.array([body_point(bbox_min), body_point(bbox_max)])
    return {
        "mass_kg": total,
        "com_m": body_point(com),
        "inertia_kg_m2": body_inertia(inertia),
        "bbox_body_m": [corners.min(axis=0), corners.max(axis=0)],
        "rows": int(len(rows)),
    }


def attachment_record(name: str, props: dict, connection: str, source: str) -> dict:
    return {
        "name": name,
        "mass_kg": round(props["mass_kg"], 3),
        "com_m": round_list(props["com_m"]),
        "inertia_about_com_body_kg_m2": [round_list(row) for row in props["inertia_kg_m2"]],
        "bbox_body_m": [round_list(props["bbox_body_m"][0]), round_list(props["bbox_body_m"][1])],
        "tensor_checks": tensor_checks(props["inertia_kg_m2"]),
        "connection": connection,
        "source": source,
    }


def cylinder_radii(instance_path_pattern: str) -> list[float]:
    """Unique radii of the cylindrical faces of the matching parts (mm)."""
    radii = set()
    for instance in brep_cache.iter_instances(instance_path_pattern):
        shape = brep_cache.load_part(instance.instance_path)
        explorer = TopExp_Explorer(shape, TopAbs_FACE)
        while explorer.More():
            surface = BRepAdaptor_Surface(topods.Face(explorer.Current()))
            if surface.GetType() == GeomAbs_Cylinder:
                radii.add(round(surface.Cylinder().Radius(), 2))
            explorer.Next()
    return sorted(radii)


def check_solid_validity(instance_path_pattern: str) -> bool:
    ok = True
    for instance in brep_cache.iter_instances(instance_path_pattern):
        ok &= BRepCheck_Analyzer(brep_cache.load_part(instance.instance_path)).IsValid()
    return bool(ok)


# --------------------------------------------------------------------------
# Supports
# --------------------------------------------------------------------------
def backstay_support(summary: dict, parts: pd.DataFrame) -> dict:
    """Backstay pivots, oil columns, locked axial stiffness and the equivalent link mass."""
    backstay = summary["backstay"]
    lower = np.array(backstay["lower_pivot_body_m"])
    upper = np.array(backstay["upper_pivot_body_m"])
    length = float(np.linalg.norm(upper - lower))
    axis = (upper - lower) / length
    bore_r = backstay["bore_radius_mm"] * MM
    rod_r = backstay["rod_radius_mm"] * MM
    pos = backstay["axial_positions_from_lower_pivot_mm"]
    head_column = (pos["piston_bottom"] - pos["bore_floor"]) * MM
    rod_column = (pos["gland_inner_face"] - pos["piston_top"]) * MM
    head_area = math.pi * bore_r**2
    rod_area = math.pi * (bore_r**2 - rod_r**2)
    stiffness = {
        name: {
            "head_side_N_m": beta * head_area / head_column,
            "rod_side_N_m": beta * rod_area / rod_column,
            "both_locked_N_m": beta * (head_area / head_column + rod_area / rod_column),
        }
        for name, beta in BULK_MODULUS_PA.items()
    }
    # Equivalent mass of the backstay at the upper pivot: rigid link turning about the lower pin.
    rows = parts[parts["top_assembly"] == BACKSTAY_TOP]
    props = mass_properties(rows)
    r = props["com_m"] - lower
    inertia_lower_y = props["inertia_kg_m2"][1, 1] + props["mass_kg"] * (r[0] ** 2 + r[2] ** 2)
    return {
        "lower_pivot_body_m": round_list(lower),
        "upper_pivot_body_m": round_list(upper),
        "pin_axes": "body y (CAD X) at both eyes",
        "pin_to_pin_m": round(length, 5),
        "axis_unit_body": round_list(axis),
        "angle_from_vertical_deg": round(math.degrees(math.acos(axis[2])), 3),
        "bore_radius_m": bore_r,
        "rod_radius_m": rod_r,
        "head_area_m2": head_area,
        "rod_side_annulus_area_m2": rod_area,
        "head_column_m": round(head_column, 5),
        "rod_column_m": round(rod_column, 5),
        "locked_oil_stiffness_by_bulk_modulus": {
            k: {kk: float(f"{vv:.4g}") for kk, vv in v.items()} for k, v in stiffness.items()
        },
        "stiffness_note": (
            "ASSUMPTION: oil in the cylinder only (hoses, valve block and steel compliance "
            "not included -> upper bound); both chambers locked (pilot check valves assumed "
            "like the legs; backstay valve not in the circuit drawing)"
        ),
        "mass_kg": round(props["mass_kg"], 3),
        "inertia_about_lower_pin_y_kg_m2": round(inertia_lower_y, 3),
        "equivalent_mass_at_upper_pivot_kg": round(inertia_lower_y / length**2, 3),
        "equivalent_mass_note": "rigid link turning about the lower pin (axial sliding of "
        "the rod ignored)",
    }


def boom_support(summary: dict) -> dict:
    """Boom-to-deck roll pin and the boom cylinder that hold the mast laterally."""
    joints = summary["joints_between_assemblies"]

    def find(assemblies: set[str], y_cad: float | None = None) -> dict:
        for joint in joints:
            if set(joint["assemblies"]) == assemblies and (
                y_cad is None or abs(joint["point_cad_mm"][1] - y_cad) < 1.0
            ):
                return joint
        raise KeyError(assemblies)

    pin = find({"BASE DECK:1", "BOOM:1"})
    cyl_low = find({"BASE DECK:1", "BOOM CYL:1"})
    cyl_up = find({"BOOM CYL:1", "BOOM:1"})
    pin_point = body_point(pin["point_cad_mm"])
    cyl_low_point = body_point(cyl_low["point_cad_mm"])
    cyl_up_point = body_point(cyl_up["point_cad_mm"])
    return {
        "boom_roll_pin": {
            "point_body_m": round_list(pin_point),
            "axis_body": [1.0, 0.0, 0.0],
            "axial_range_body_x_m": round_list(np.array(pin["axial_range_mm"]) * MM),
            "pin_radius_mm": pin["max_radius_by_assembly_mm"],
        },
        "boom_cylinder": {
            "lower_eye_body_m": round_list([cyl_low_point[0], cyl_low_point[1], cyl_low_point[2]]),
            "upper_eye_body_m": round_list([cyl_up_point[0], cyl_up_point[1], cyl_up_point[2]]),
            "pin_to_pin_m": round(float(np.linalg.norm(cyl_up_point - cyl_low_point)), 4),
            "lever_arm_about_roll_pin_m": round(abs(pin_point[1] - cyl_low_point[1]), 4),
            "cylindrical_face_radii_mm": cylinder_radii(r"BOOM CYL:1"),
            "note": (
                "vertical cylinder; boom roll stiffness = k_cyl * lever^2. Bore not confirmed "
                "(face radii listed); hydraulic stiffness unknown"
            ),
        },
    }


# --------------------------------------------------------------------------
# Reference frequency estimates (planar frame FE + Rayleigh quotient)
# --------------------------------------------------------------------------
@dataclass
class LumpedBody:
    name: str
    mass_kg: float
    com_m: np.ndarray  # body
    inertia_kg_m2: np.ndarray  # about the com, body axes


def frame_model(
    plane: str,
    z_nodes: np.ndarray,
    beam: pd.DataFrame,
    axis_t_m: float,
    bodies: list[tuple[LumpedBody, float]],
) -> tuple[np.ndarray, np.ndarray]:
    """Planar Euler-Bernoulli frame along body z; dofs per node (u_t, u_z, beta).

    plane "xz": u_t = x (fore-aft), beta = d u_x / dz, uses Iy and the CoG inertia about y.
    plane "yz": u_t = y (lateral), beta = d u_y / dz, uses Ix and the CoG inertia about x.
    A point at offset (d_t, d_z) from a node moves by (u_t + beta d_z, u_z - beta d_t).
    Lumped bodies are rigidly attached to the node at the given height.
    """
    n = len(z_nodes)
    stiffness = np.zeros((3 * n, 3 * n))
    mass = np.zeros((3 * n, 3 * n))
    bending = "Iy_eff_m4" if plane == "xz" else "Ix_eff_m4"
    cut = beam[(beam["Iy_eff_m4"] > 0) & (beam["Ix_eff_m4"] > 0)]  # nearest slice fully cut
    centres = cut["z_center_m"].to_numpy()
    for e in range(n - 1):
        z0, z1 = z_nodes[e], z_nodes[e + 1]
        length = z1 - z0
        mid = 0.5 * (z0 + z1)
        row = cut.iloc[int(np.argmin(np.abs(centres - mid)))]
        ei = STEEL_E_PA * row[bending]
        ea = STEEL_E_PA * row["A_eff_m2"]
        # distributed mass: slice mass per length of every slice overlapping the element
        overlap = np.clip(
            np.minimum(beam["z_hi_m"], z1) - np.maximum(beam["z_lo_m"], z0), 0.0, None
        )
        m_e = float((overlap / (beam["z_hi_m"] - beam["z_lo_m"]) * beam["slice_mass_kg"]).sum())
        mu = m_e / length
        dofs = [3 * e, 3 * e + 1, 3 * e + 2, 3 * e + 3, 3 * e + 4, 3 * e + 5]
        k = np.zeros((6, 6))
        k[np.ix_([1, 4], [1, 4])] = ea / length * np.array([[1, -1], [-1, 1]])
        b = [0, 2, 3, 5]
        k[np.ix_(b, b)] = (
            ei
            / length**3
            * np.array(
                [
                    [12, 6 * length, -12, 6 * length],
                    [6 * length, 4 * length**2, -6 * length, 2 * length**2],
                    [-12, -6 * length, 12, -6 * length],
                    [6 * length, 2 * length**2, -6 * length, 4 * length**2],
                ]
            )
        )
        m = np.zeros((6, 6))
        m[np.ix_([1, 4], [1, 4])] = mu * length / 6 * np.array([[2, 1], [1, 2]])
        m[np.ix_(b, b)] = (
            mu
            * length
            / 420
            * np.array(
                [
                    [156, 22 * length, 54, -13 * length],
                    [22 * length, 4 * length**2, 13 * length, -3 * length**2],
                    [54, 13 * length, 156, -22 * length],
                    [-13 * length, -3 * length**2, -22 * length, 4 * length**2],
                ]
            )
        )
        stiffness[np.ix_(dofs, dofs)] += k
        mass[np.ix_(dofs, dofs)] += m
    t_index = 0 if plane == "xz" else 1
    rot_index = 1 if plane == "xz" else 0
    for body, z_attach in bodies:
        node = int(np.argmin(np.abs(z_nodes - z_attach)))
        d_t = body.com_m[t_index] - axis_t_m
        d_z = body.com_m[2] - z_nodes[node]
        transform = np.array([[1.0, 0.0, d_z], [0.0, 1.0, -d_t]])
        block = body.mass_kg * transform.T @ transform
        block[2, 2] += body.inertia_kg_m2[rot_index, rot_index]
        dofs = [3 * node, 3 * node + 1, 3 * node + 2]
        mass[np.ix_(dofs, dofs)] += block
    return stiffness, mass


def add_point_spring(stiffness, z_nodes, plane, axis_t_m, point_m, direction, k_value):
    """Spring of stiffness k along ``direction`` at a point rigidly offset from the nearest node."""
    t_index = 0 if plane == "xz" else 1
    node = int(np.argmin(np.abs(z_nodes - point_m[2])))
    d_t = point_m[t_index] - axis_t_m
    d_z = point_m[2] - z_nodes[node]
    transform = np.array([[1.0, 0.0, d_z], [0.0, 1.0, -d_t]])
    u = np.array([direction[t_index], direction[2]])
    g = u @ transform
    dofs = [3 * node, 3 * node + 1, 3 * node + 2]
    stiffness[np.ix_(dofs, dofs)] += k_value * np.outer(g, g)


def solve_modes(stiffness, mass, fixed_dofs, plane_t_dofs) -> dict:
    """First eigenfrequency (FE) and the Rayleigh quotient with the static gravity-like shape."""
    n = stiffness.shape[0]
    free = np.setdiff1d(np.arange(n), fixed_dofs)
    k = stiffness[np.ix_(free, free)]
    m = mass[np.ix_(free, free)]
    eigenvalues, vectors = linalg.eigh(k, m, subset_by_index=[0, 2])
    influence = np.zeros(n)
    influence[plane_t_dofs] = 1.0
    load = (mass @ influence)[free] * GRAVITY
    shape = np.linalg.solve(k, load)
    omega2_rayleigh = float(load @ shape / (shape @ m @ shape))
    full = np.zeros(n)
    full[free] = vectors[:, 0]
    return {
        "f1_fe_hz": float(math.sqrt(max(eigenvalues[0], 0.0)) / (2 * math.pi)),
        "f2_fe_hz": float(math.sqrt(max(eigenvalues[1], 0.0)) / (2 * math.pi)),
        "f1_rayleigh_hz": float(math.sqrt(omega2_rayleigh) / (2 * math.pi)),
        "mode1": full,
    }


def frequency_estimates(
    beam,
    support,
    bodies_common,
    drive_levels,
    z_hinge,
    axis_x,
    axis_y,
    hinge_point,
    backstay,
    backstay_body,
) -> dict:
    """Reference f1 for the cantilever (clamped at the hinge height) and fore-aft pin + backstay."""
    z_edges = np.unique(np.concatenate([beam["z_lo_m"], beam["z_hi_m"]]))
    results = {}
    for level, drive in drive_levels.items():
        shoe_centre = drive["shoe_span_centre_z_m"]
        drive_body = LumpedBody(
            "drive_tool",
            drive["mass_kg"],
            np.array(drive["com_m"]),
            np.array(drive["inertia_kg_m2"]),
        )
        level_result = {}
        # (1) cantilever clamped at the hinge height; parts below the clamp do not move
        top = beam["z_hi_m"][beam["slice_mass_kg"] > 0].max()
        nodes = np.unique(
            np.concatenate([[z_hinge], z_edges[(z_edges > z_hinge) & (z_edges <= top)]])
        )
        part = beam[beam["z_hi_m"] > z_hinge]
        bodies = [(b, z) for b, z in bodies_common if z > z_hinge]
        drive_included = shoe_centre > z_hinge + 0.1
        if drive_included:
            bodies.append((drive_body, shoe_centre))
        for plane, axis_t in (("xz", axis_x), ("yz", axis_y)):
            k, m = frame_model(plane, nodes, part, axis_t, bodies)
            t_dofs = np.arange(0, 3 * len(nodes), 3)
            out = solve_modes(k, m, [0, 1, 2], t_dofs)
            out.pop("mode1")
            level_result[f"cantilever_{'fore_aft' if plane == 'xz' else 'lateral'}"] = out
        level_result["cantilever_drive_included"] = bool(drive_included)
        # (2) fore-aft: pin at the hinge point + locked backstay spring, whole mast and lower guide
        nodes = np.unique(
            np.concatenate([z_edges[(z_edges <= top)], [z_hinge, backstay_body["z"]]])
        )
        nodes = nodes[nodes >= beam["z_lo_m"][beam["slice_mass_kg"] > 0].min()]
        bodies = list(bodies_common) + [(drive_body, shoe_centre)]
        bodies.append(
            (
                LumpedBody(
                    "backstay_equivalent",
                    backstay["equivalent_mass_at_upper_pivot_kg"],
                    np.array(backstay["upper_pivot_body_m"]),
                    np.zeros((3, 3)),
                ),
                backstay_body["z"],
            )
        )
        for name, k_axial in (
            (
                "pin_backstay_beta_1GPa",
                backstay["locked_oil_stiffness_by_bulk_modulus"]["reference"]["both_locked_N_m"],
            ),
            ("pin_backstay_rigid", 1e13),
        ):
            k, m = frame_model("xz", nodes, beam, axis_x, bodies)
            penalty = 1e14
            add_point_spring(k, nodes, "xz", axis_x, hinge_point, np.array([1.0, 0, 0]), penalty)
            add_point_spring(k, nodes, "xz", axis_x, hinge_point, np.array([0, 0, 1.0]), penalty)
            add_point_spring(
                k,
                nodes,
                "xz",
                axis_x,
                np.array(backstay["upper_pivot_body_m"]),
                np.array(backstay["axis_unit_body"]),
                k_axial,
            )
            t_dofs = np.arange(0, 3 * len(nodes), 3)
            out = solve_modes(k, m, [], t_dofs)
            out.pop("mode1")
            out["backstay_axial_stiffness_N_m"] = float(f"{k_axial:.4g}")
            level_result[f"fore_aft_{name}"] = out
        results[level] = {
            key: (
                {kk: round(vv, 4) if isinstance(vv, float) else vv for kk, vv in val.items()}
                if isinstance(val, dict)
                else val
            )
            for key, val in level_result.items()
        }
    return results


# --------------------------------------------------------------------------
# Plots
# --------------------------------------------------------------------------
def plot_sections(panels: list[dict], path: Path) -> None:
    columns = 4
    rows = math.ceil(len(panels) / columns)
    fig, axes = plt.subplots(rows, columns, figsize=(4.2 * columns, 4.6 * rows))
    colours = {"structural": "#2a6fb0", "non_structural": "#b9b6ad"}
    for ax, panel in zip(np.ravel(axes), panels, strict=False):
        for piece in panel["pieces"]:
            kind = "structural" if piece.role in STIFFNESS_ROLES else "non_structural"
            polys = piece.triangles * MM
            ax.add_collection(PolyCollection(polys, facecolors=colours[kind], edgecolors="none"))
        props = panel["props"]
        if props.get("A_m2", 0) > 0:
            ax.plot(props["x_c_m"], props["y_c_m"], marker="+", color="#d1495b", ms=10, mew=1.5)
        ax.set_xlim(1.85, 2.75)
        ax.set_ylim(-0.45, 0.45)
        ax.set_aspect("equal")
        ax.grid(color="#e6e4dc", lw=0.6)
        ax.set_xlabel("body x [m] (forward)")
        ax.set_ylabel("body y [m] (left)")
        text = (
            f"z = {panel['z_m']:.3f} m\nA = {props.get('A_m2', 0) * 1e4:.1f} cm²\n"
            f"Iy = {props.get('Iy_m4', 0) * 1e8:.0f} cm⁴\n"
            f"Ix = {props.get('Ix_m4', 0) * 1e8:.0f} cm⁴\n"
            f"J = {panel.get('J_m4', 0) * 1e8:.0f} cm⁴"
        )
        ax.text(
            0.02,
            0.98,
            text,
            transform=ax.transAxes,
            va="top",
            fontsize=8,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85},
        )
        ax.set_title(panel["title"], fontsize=9)
    for ax in np.ravel(axes)[len(panels) :]:
        ax.axis("off")
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=colours["structural"]),
        plt.Rectangle((0, 0), 1, 1, color=colours["non_structural"]),
        plt.Line2D([], [], marker="+", color="#d1495b", ls="none", ms=10),
    ]
    fig.legend(
        handles,
        [
            "structural (stiffness)",
            "non-structural (ladder, mass only)",
            "centroid of the structural cut",
        ],
        loc="lower center",
        ncol=3,
        frameon=False,
    )
    fig.suptitle(
        "Mast cross-sections (cut normal to body z, structural centroid axes)", fontsize=11
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_distribution(beam: pd.DataFrame, markers: dict, drive_levels: dict, path: Path) -> None:
    z = beam["z_center_m"].to_numpy()
    # slices without a structural cut (beyond the mast ends) are not drawn
    beam = beam.copy()
    empty = beam["A_m2"] <= 0
    for column in ("A_m2", "x_c_m", "y_c_m", "Iy_m4", "Ix_m4", "J_m4"):
        beam.loc[empty, column] = np.nan
    for column in ("A_eff_m2", "Iy_eff_m4", "Ix_eff_m4", "J_eff_m4"):
        beam.loc[beam[column] <= 0, column] = np.nan
    fig, axes = plt.subplots(1, 5, figsize=(17, 9), sharey=True)
    ink = "#2b2b2b"
    axes[0].plot(beam["A_m2"] * 1e4, z, color="#9cc3e6", lw=0.8, label="centre cut")
    axes[0].plot(beam["A_eff_m2"] * 1e4, z, color="#2a6fb0", lw=1.6, label="slice-effective")
    axes[0].set_xlim(0, 1200)
    axes[0].legend(loc="lower right", fontsize=8)
    axes[0].set_xlabel("A [cm²]")
    axes[1].plot(beam["Iy_m4"] * 1e8, z, color="#9cc3e6", lw=0.8, label="Iy centre cut")
    axes[1].plot(beam["Ix_m4"] * 1e8, z, color="#f0a8b2", lw=0.8, ls="--", label="Ix centre cut")
    axes[1].plot(
        beam["Iy_eff_m4"] * 1e8, z, color="#2a6fb0", lw=1.6, label="Iy slice-effective (fore-aft)"
    )
    axes[1].plot(
        beam["Ix_eff_m4"] * 1e8,
        z,
        color="#d1495b",
        lw=1.6,
        ls="--",
        label="Ix slice-effective (lateral)",
    )
    axes[1].set_xscale("log")
    axes[1].set_xlabel("second moment of area [cm⁴]")
    axes[1].legend(loc="lower right", fontsize=8)
    axes[2].plot(beam["J_m4"] * 1e8, z, color="#9fd9c3", lw=0.8, label="centre cut")
    axes[2].plot(beam["J_eff_m4"] * 1e8, z, color="#1baf7a", lw=1.6, label="slice-effective")
    axes[2].legend(loc="lower right", fontsize=8)
    axes[2].set_xscale("log")
    axes[2].set_xlabel("torsion constant J [cm⁴]")
    axes[3].plot(beam["x_c_m"], z, color="#2a6fb0", lw=1.4, label="x_c")
    axes[3].plot(beam["y_c_m"] + 2.45, z, color="#d1495b", lw=1.2, ls="--", label="y_c + 2.45 m")
    axes[3].set_xlabel("section centroid [m]")
    axes[3].legend(loc="lower right", fontsize=8)
    axes[4].step(
        beam["m_per_m_total_kg_m"], z, where="mid", color=ink, lw=1.0, label="total (mast assy)"
    )
    axes[4].step(
        beam["m_per_m_plates_kg_m"],
        z,
        where="mid",
        color="#2a6fb0",
        lw=1.0,
        label="structural plates",
    )
    axes[4].set_xscale("log")
    axes[4].set_xlabel("mass per length [kg/m] (50 mm slices)")
    axes[4].legend(loc="lower right", fontsize=8)
    for ax in axes:
        ax.grid(color="#e6e4dc", lw=0.6)
        for name, (value, colour) in markers.items():
            ax.axhline(value, color=colour, lw=0.8, ls=":")
            if ax is axes[0]:
                ax.text(
                    ax.get_xlim()[1],
                    value,
                    f" {name}",
                    va="center",
                    fontsize=7,
                    color=colour,
                    clip_on=False,
                )
    level_colours = {"top": "#eda100", "middle": "#8a5cc2", "bottom": "#1baf7a"}
    for level, drive in drive_levels.items():
        low, high = drive["shoe_span_z_m"]
        axes[4].axhspan(low, high, color=level_colours[level], alpha=0.18, lw=0)
        axes[4].text(
            axes[4].get_xlim()[0],
            0.5 * (low + high),
            f" shoes ({level})",
            fontsize=7,
            va="center",
            color=level_colours[level],
        )
    axes[0].set_ylabel("body z [m]")
    fig.suptitle(
        "Mast beam properties along the axis (E-independent geometry; mass with STEP steel 7.85)",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 0.97, 0.96))
    fig.savefig(path, dpi=120)
    plt.close(fig)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--raster-mm", type=float, default=1.0, help="raster cell for J (mm)")
    parser.add_argument("--skip-plots", action="store_true")
    args = parser.parse_args()
    t_start = time.perf_counter()
    timings = {}

    summary = json.loads(MAST_SUMMARY_JSON.read_text(encoding="utf-8"))
    levels = json.loads(AUGER_LEVELS_JSON.read_text(encoding="utf-8"))
    parts = load_parts()
    mast_parts = pd.read_csv(MAST_PARTS_CSV, encoding="utf-8-sig")

    # ---- solids, roles, member dimensions -------------------------------------------
    t0 = time.perf_counter()
    solids = load_mast_solids()
    ranges = segment_ranges(solids)
    timings["load_solids_s"] = time.perf_counter() - t0
    print(f"mast solids: {len(solids)} ({timings['load_solids_s']:.1f} s)")
    mast_rows = parts[parts["top_assembly"] == MAST_TOP]
    table_mass = float(mast_rows["mass_c_kg"].sum())
    solid_mass = sum(s.volume_mm3 for s in solids) * STEEL_DENSITY_KG_M3 * 1e-9
    role_table = (
        pd.DataFrame(
            [{"role": s.role, "mass_kg": s.volume_mm3 * STEEL_DENSITY_KG_M3 * 1e-9} for s in solids]
        )
        .groupby("role")["mass_kg"]
        .agg(["count", "sum"])
    )
    t0 = time.perf_counter()
    overlaps = overlap_check(solids)
    timings["overlap_check_s"] = time.perf_counter() - t0
    print(f"overlap check: {overlaps['pairs_checked']} pairs, {overlaps['overlap_volume_mm3']} mm3")

    # ---- slices: sections and masses -------------------------------------------------
    edges = np.arange(SLICE_START_MM, SLICE_END_MM + 0.5, SLICE_MM)
    centres = 0.5 * (edges[:-1] + edges[1:])
    t0 = time.perf_counter()
    masses = slice_masses(solids, edges)
    timings["slice_masses_s"] = time.perf_counter() - t0
    print(f"slice masses ({timings['slice_masses_s']:.1f} s)")

    t0 = time.perf_counter()
    torsion_cache: dict[tuple, dict] = {}
    station_rows, panels = [], []
    for k, y0 in enumerate(centres):
        stiff_pieces, props, torsion = cut_at(solids, y0, torsion_cache, args.raster_mm)
        other_pieces = []
        if y0 in SECTION_PANELS_MM:
            for solid in solids:
                low, high = solid.y_range
                if low < y0 < high and solid.role == "ladder":
                    other_pieces += section_pieces(solid, y0)
        row = {"z_center_m": y0 * MM, "z_lo_m": edges[k] * MM, "z_hi_m": edges[k + 1] * MM}
        row.update(
            {
                key: props.get(key, 0.0)
                for key in (
                    "A_m2",
                    "x_c_m",
                    "y_c_m",
                    "Iy_m4",
                    "Ix_m4",
                    "Ixy_m4",
                    "I_max_m4",
                    "I_min_m4",
                    "principal_angle_deg",
                )
            }
        )
        row["J_m4"] = torsion["J_mm4"] * 1e-12
        row["closed_cells"] = torsion["closed_cells"]
        row["raster_area_rel_diff"] = torsion["raster_area_rel_diff"]
        # slice-effective values: harmonic mean over sub-cuts (springs in series along the slice)
        sub = [
            cut_at(solids, y, torsion_cache, args.raster_mm)
            for y in np.arange(edges[k] + 0.5 * SUBCUT_MM, edges[k + 1], SUBCUT_MM)
        ]
        sub_a = np.array([s[1].get("A_m2", 0.0) for s in sub])
        row["A_mean_m2"] = float(sub_a.mean())
        for key, column in (("A_m2", "A_eff_m2"), ("Iy_m4", "Iy_eff_m4"), ("Ix_m4", "Ix_eff_m4")):
            values = np.array([s[1].get(key, 0.0) for s in sub])
            row[column] = float(len(values) / np.sum(1.0 / values)) if np.all(values > 0) else 0.0
        values = np.array([s[2]["J_mm4"] * 1e-12 for s in sub])
        row["J_eff_m4"] = float(len(values) / np.sum(1.0 / values)) if np.all(values > 0) else 0.0
        row["segments"] = "+".join(name for name, (lo, hi) in ranges.items() if lo < y0 < hi)
        row["stiffness_parts"] = "|".join(sorted({p.part for p in stiff_pieces}))
        row["stiffness_roles"] = "|".join(sorted({p.role for p in stiff_pieces}))
        station_rows.append(row)
        if y0 in SECTION_PANELS_MM:
            panels.append(
                {
                    "z_m": y0 * MM,
                    "pieces": stiff_pieces + other_pieces,
                    "props": props,
                    "J_m4": row["J_m4"],
                    "title": f"{row['segments']} at z = {y0 * MM:.3f} m",
                }
            )
    timings["sections_s"] = time.perf_counter() - t0
    print(
        f"sections: {len(centres)} cuts, {len(torsion_cache)} distinct shapes "
        f"({timings['sections_s']:.1f} s)"
    )

    beam = pd.DataFrame(station_rows)
    length_m = SLICE_MM * MM
    for group, column in (
        ("plates", "m_per_m_plates_kg_m"),
        ("flange_diaphragm", "m_per_m_flange_diaphragm_kg_m"),
        ("ladder", "m_per_m_ladder_kg_m"),
        ("rack_pin", "m_per_m_rack_pin_kg_m"),
    ):
        beam[column] = masses[group]["V"] * STEEL_DENSITY_KG_M3 * 1e-9 / length_m
    volume_all = sum(masses[g]["V"] for g in ("plates", "flange_diaphragm", "ladder", "rack_pin"))
    vx = sum(masses[g]["VX"] for g in ("plates", "flange_diaphragm", "ladder", "rack_pin"))
    vz = sum(masses[g]["VZ"] for g in ("plates", "flange_diaphragm", "ladder", "rack_pin"))
    beam["slice_mass_kg"] = volume_all * STEEL_DENSITY_KG_M3 * 1e-9
    beam["m_per_m_total_kg_m"] = beam["slice_mass_kg"] / length_m
    with np.errstate(invalid="ignore", divide="ignore"):
        beam["slice_com_x_m"] = np.where(volume_all > 0, vz / volume_all * MM, np.nan)
        beam["slice_com_y_m"] = np.where(volume_all > 0, vx / volume_all * MM, np.nan)
    # stiffness for a beam model: slice-effective (harmonic mean of the 5 mm sub-cuts)
    beam["EIy_eff_N_m2"] = STEEL_E_PA * beam["Iy_eff_m4"]
    beam["EIx_eff_N_m2"] = STEEL_E_PA * beam["Ix_eff_m4"]
    beam["GJ_eff_N_m2"] = STEEL_G_PA * beam["J_eff_m4"]
    beam["EA_eff_N"] = STEEL_E_PA * beam["A_eff_m2"]

    # ---- representative member dimensions at a typical cut (MAST-3 at z 4.125 m) ----
    typical_y = 4125.0
    member_dims = []
    for solid in solids:
        low, high = solid.y_range
        if low < typical_y < high:
            for piece in section_pieces(solid, typical_y):
                bb = piece.bbox_body_mm
                member_dims.append(
                    {
                        "part": piece.part,
                        "role": piece.role,
                        "area_mm2": round(piece.area_mm2, 1),
                        "extent_x_mm": round(bb[2] - bb[0], 2),
                        "extent_y_mm": round(bb[3] - bb[1], 2),
                        "x_range_m": round_list([bb[0] * MM, bb[2] * MM]),
                        "y_range_m": round_list([bb[1] * MM, bb[3] * MM]),
                        "thin_wall_thickness_2A_over_P_mm": round(
                            2 * piece.area_mm2 / piece.perimeter_mm, 2
                        ),
                    }
                )

    # ---- attachments and supports ----------------------------------------------------
    hinge = summary["hinge"]
    hinge_point = np.array(hinge["point_body_m"])
    z_hinge = float(hinge_point[2])
    backstay = backstay_support(summary, parts)
    boom = boom_support(summary)
    lumped = {}
    for key, top, connection in (
        (
            "topsheave",
            TOPSHEAVE_TOP,
            "sits on the MAST-5 top flange (CAD Y 9851), bolted (assumed rigid)",
        ),
        ("winch", WINCH_TOP, "4 bolts (R6.9) on the rear of MAST-2 (mast_summary joints)"),
        (
            "lower_guide",
            LOWER_GUIDE_TOP,
            "clamps the rails at the mast foot (FIX PIN, GUIDE PIN); "
            "no other support found (cad_mast_review 4)",
        ),
    ):
        lumped[key] = attachment_record(
            key,
            mass_properties(parts[parts["top_assembly"] == top]),
            connection,
            "parts_classified.csv rows, case C = STEP densities",
        )
    lumped["backstay_cylinder"] = attachment_record(
        "backstay_cylinder",
        mass_properties(parts[parts["top_assembly"] == BACKSTAY_TOP]),
        "two-force link boom (lower pin) -> mast lugs (upper pin, PIN-1)",
        "parts_classified.csv",
    )
    lumped["mast_assy_total"] = attachment_record(
        "mast_assy_total",
        mass_properties(mast_rows),
        "MAST ASSY:1 (segments, racks, pins, bushes); distributed in the beam table",
        "parts_classified.csv",
    )

    moving = parts[parts["motion"].isin(["moving_drive", "moving_tool"])]
    moving_cad = mass_properties(moving)
    params = yaml.safe_load(PARAMS_YAML.read_text(encoding="utf-8"))
    yaml_moving = params.get("superstructure", {}).get("auger_moving_set_at_cad_pose")
    shoes = parts[parts["instance_path"].str.contains("GUID CATCHER")]
    pads_rear = parts[parts["instance_path"].str.contains("CATHCER PAD-1")]
    pads_front_side = parts[parts["instance_path"].str.contains("CATCHER PAD-2")]
    pinions = parts[parts["instance_path"].str.contains("21. ELEVATION GEAR")]
    shoe_y = (shoes["bbox_min_y_mm"].min(), shoes["bbox_max_y_mm"].max())
    drive_levels = {}
    for level in LEVELS:
        travel = float(levels["levels"][level]["travel_mm"])
        props = mass_properties(moving, offset_y_mm=travel)
        drive_levels[level] = {
            "travel_m": travel * MM,
            "mass_kg": props["mass_kg"],
            "com_m": round_list(props["com_m"], 9),
            "inertia_kg_m2": [round_list(r, 9) for r in props["inertia_kg_m2"]],
            "tensor_checks": tensor_checks(props["inertia_kg_m2"]),
            "shoe_span_z_m": round_list(np.array(shoe_y) * MM + travel * MM),
            "shoe_span_centre_z_m": float((0.5 * (shoe_y[0] + shoe_y[1]) + travel) * MM),
            "shoe_rows_z_m": [
                round_list(np.array([r.bbox_min_y_mm, r.bbox_max_y_mm]) * MM + travel * MM)
                for r in shoes[shoes["bbox_min_x_mm"] > 0].sort_values("bbox_min_y_mm").itertuples()
            ],
            "pinion_z_m": round_list(
                np.array([pinions["bbox_min_y_mm"].min(), pinions["bbox_max_y_mm"].max()]) * MM
                + travel * MM
            ),
            "com_offset_from_mast_axis_x_m": None,  # filled below
        }

    # ---- checks ----------------------------------------------------------------------
    stiff_mass = sum(s.volume_mm3 for s in solids if s.stiffness) * STEEL_DENSITY_KG_M3 * 1e-9
    integral_area_mass = float((beam["A_mean_m2"] * length_m).sum() * STEEL_DENSITY_KG_M3)
    main_zone = beam[(beam["z_center_m"] > 3.1) & (beam["z_center_m"] < 4.3)]
    axis_x = float(main_zone["x_c_m"].median())
    axis_y = float(main_zone["y_c_m"].median())
    for drive in drive_levels.values():
        drive["com_offset_from_mast_axis_x_m"] = round(drive["com_m"][0] - axis_x, 5)
    mast_com = lumped["mast_assy_total"]["com_m"]
    checks = {
        "mass_closure_slices_vs_solids_rel": float(
            beam["slice_mass_kg"].sum()
            / (masses["solid_volume_total_mm3"] * STEEL_DENSITY_KG_M3 * 1e-9)
            - 1.0
        ),
        "mass_closure_solids_vs_parts_table_rel": float(solid_mass / table_mass - 1.0),
        "mast_assy_mass_parts_table_kg": round(table_mass, 3),
        "mast_parts_csv_mast_assy_mass_kg": round(
            float(mast_parts[mast_parts["top_assembly"] == MAST_TOP]["mass_step_kg"].sum()), 3
        ),
        "integral_A_dz_times_rho_kg": round(integral_area_mass, 3),
        "structural_solid_mass_kg": round(stiff_mass, 3),
        "integral_A_vs_structural_mass_rel": float(integral_area_mass / stiff_mass - 1.0),
        "integral_A_note": "mean area of the 5 mm sub-cuts x slice length x rho vs the B-rep "
        "mass of all stiffness solids (incl. flanges, diaphragms)",
        "overlap": overlaps,
        "symmetry": {
            "max_abs_section_centroid_y_m": float(beam.loc[beam["A_m2"] > 0, "y_c_m"].abs().max()),
            "max_abs_Ixy_over_sqrt_IxIy": float(
                (
                    beam["Ixy_m4"].abs() / np.sqrt(beam["Ix_m4"] * beam["Iy_m4"]).replace(0, np.nan)
                ).max()
            ),
            "mast_assy_com_y_m": mast_com[1],
            "note": "structure is symmetric about body y = 0; the ladder (+y side) shifts the mass",
        },
        "torsion_self_test": torsion_self_test(args.raster_mm),
        "raster_area_rel_diff_max": float(beam["raster_area_rel_diff"].abs().max()),
        "moving_set_vs_yaml": None,
        "solid_validity": {"mast_assy_parts_valid": check_solid_validity(r"MAST ASSY:1 / MAST")},
    }
    if yaml_moving is not None:
        checks["moving_set_vs_yaml"] = {
            "mass_rel": float(moving_cad["mass_kg"] / yaml_moving["mass_kg"] - 1.0),
            "com_max_abs_m": float(
                np.max(np.abs(moving_cad["com_m"] - np.array(yaml_moving["com_m"])))
            ),
            "inertia_max_rel": float(
                np.max(np.abs(moving_cad["inertia_kg_m2"] - np.array(yaml_moving["inertia_kg_m2"])))
                / np.max(np.abs(yaml_moving["inertia_kg_m2"]))
            ),
        }

    # ---- reference frequencies -------------------------------------------------------
    bodies_common = []
    for key in ("topsheave", "winch", "lower_guide"):
        record = lumped[key]
        com = np.array(record["com_m"])
        attach = {
            "topsheave": ranges["MAST-5"][1] * MM,
            "winch": com[2],
            "lower_guide": ranges["MAST"][0] * MM,
        }[key]
        bodies_common.append(
            (
                LumpedBody(
                    key, record["mass_kg"], com, np.array(record["inertia_about_com_body_kg_m2"])
                ),
                attach,
            )
        )
    drive_inputs = {
        level: {
            "mass_kg": d["mass_kg"],
            "com_m": d["com_m"],
            "inertia_kg_m2": d["inertia_kg_m2"],
            "shoe_span_centre_z_m": d["shoe_span_centre_z_m"],
        }
        for level, d in drive_levels.items()
    }
    t0 = time.perf_counter()
    frequencies = frequency_estimates(
        beam,
        None,
        bodies_common,
        drive_inputs,
        z_hinge,
        axis_x,
        axis_y,
        hinge_point,
        backstay,
        {"z": backstay["upper_pivot_body_m"][2]},
    )
    timings["frequencies_s"] = time.perf_counter() - t0

    # ---- outputs ---------------------------------------------------------------------
    timings["total_s"] = time.perf_counter() - t_start
    above_hinge = beam[beam["z_center_m"] > z_hinge]
    result = {
        "description": "Beam properties of the upright mast along body z for the first bending "
        "frequency (roadmap C9, CAD extraction). Frequencies are a reference only.",
        "generated_by": "04_scripts/00_cad/extract_mast_beam.py",
        "sources": {
            "geometry": "01_cad/06_brep (B-rep cache) via brep_cache.py",
            "parts": "01_cad/01_parts/parts_classified.csv",
            "supports": "01_cad/04_mast/mast_summary.json (hinge, backstay, joints)",
            "auger": "01_cad/03_auger/auger_parts.csv, auger_levels.json",
        },
        "frames": "body frame x forward = Z_cad, y left = X_cad, z up = Y_cad, origin = CAD "
        "origin; SI",
        "section_convention": {
            "Iy_m4": "integral (x - x_c)^2 dA: bending in the x-z plane (fore-aft deflection)",
            "Ix_m4": "integral (y - y_c)^2 dA: bending in the y-z plane (lateral deflection)",
            "Ixy_m4": "integral (x - x_c)(y - y_c) dA (product)",
            "principal_angle_deg": "angle of the I_max axis from body y towards body x",
            "J_m4": "Saint-Venant torsion constant (FD Prandtl stress function, closed cells "
            "included)",
            "centroid": "x_c_m, y_c_m: centroid of the structural cut (not the mass centre)",
            "stations": "cuts at the centres of 50 mm slices; slice mass from exact "
            "half-space volumes",
        },
        "assumptions": {
            "E_Pa": STEEL_E_PA,
            "G_Pa": STEEL_G_PA,
            "poisson": STEEL_POISSON,
            "density_kg_m3": STEEL_DENSITY_KG_M3,
            "list": [
                "ASSUMPTION E = 210 GPa, nu = 0.3 (G = 80.8 GPa) for all mast plates (not in "
                "the STEP file)",
                "density 7.85 g/cm^3 = STEP material of the mast plates (case C = STEP here)",
                "plates of one segment that touch are welded (continuous section)",
                "segment flanges are bolted and rigid (no joint flexibility); flange and diaphragm "
                "plates count as mass only",
                "rack gear bars (995 mm with 5 mm gaps, bolted) and the ladder are mass only",
                "local plates (hinge plates, boss, lugs, gussets, end blocks) count for stiffness "
                "where they are cut",
                "hoses, wire rope, oil not in the model (mass 0)",
            ],
        },
        "segments_cad_y_mm": {k: round_list(v) for k, v in ranges.items()},
        "members": {
            "roles": {
                role: {
                    "solids": int(r["count"]),
                    "mass_kg": round(float(r["sum"]), 3),
                    "stiffness": role in STIFFNESS_ROLES,
                    "note": ROLE_NOTES.get(role, ""),
                }
                for role, r in role_table.iterrows()
            },
            "typical_cut_z_m": typical_y * MM,
            "typical_cut_members": member_dims,
            "flange_holes": flange_holes(solids),
            "solid_roles": [
                {
                    "part": s.part,
                    "solid": s.index,
                    "role": s.role,
                    "mass_kg": round(s.volume_mm3 * STEEL_DENSITY_KG_M3 * 1e-9, 4),
                    "bbox_body_m_min": round_list(body_point(s.bbox[:3])),
                    "bbox_body_m_max": round_list(body_point(s.bbox[3:])),
                }
                for s in solids
            ],
        },
        "supports": {
            "hinge_pin": {
                "point_body_m": round_list(hinge_point),
                "axis_body": hinge["axis_body"],
                "pin_diameter_mm": 150.0,
                "bushes": "BUSH-1 x2, bore R75 / outer R85, body y +-0.110 .. +-0.310",
                "type": "pin about body y: free rotation in the fore-aft plane; the bush "
                "pair (span "
                "0.62 m) carries moments about x and z into the boom",
                "offset_from_mast_axis_x_m": round(hinge_point[0] - axis_x, 5),
            },
            "backstay": backstay,
            "boom_lateral": boom,
            "mast_foot": "free end at body z -0.649 m with the lower guide; no support to "
            "the deck found",
            "mast_top": "free end at body z 9.851 m with the top sheave",
            "joint_mast1_mast2": "MAST:1 (foot) and MAST-2 meet at flanges (CAD Y 1171) and "
            "PIN-2 R30 "
            "(body x 2.083, z 1.171); taken as bolted rigid",
        },
        "mast_axis_reference": {
            "x_m": round(axis_x, 5),
            "y_m": round(axis_y, 6),
            "note": "median centroid of the structural cut in MAST-3 (z 3.1..4.3 m)",
        },
        "attachments_lumped": lumped,
        "auger_drive_tool_levels": drive_levels,
        "auger_connection": {
            "guide_shoes": "6 GUID CATCHER (3 per side) wrap the front corner rails; pads: "
            "CATCHER PAD-2 on the rail front face (Z_cad 2653 = body x 2.653) and outer "
            "side faces (|y| 0.360), CATHCER PAD-1 on the rail rear face -> restrains "
            "x and y in both directions; the vertical span of the shoe rows carries moments",
            "shoe_span_cad_pose_z_m": round_list(np.array(shoe_y) * MM),
            "rear_pad_z_cad_range_mm": round_list(
                [pads_rear["bbox_min_z_mm"].min(), pads_rear["bbox_max_z_mm"].max()]
            ),
            "front_side_pad_count": int(len(pads_front_side)),
            "vertical": "4 ELEVATION GEAR pinions on the rack (Nabtesco motors) carry the weight",
            "model_hint": "rigid body attached to the mast over the shoe span; centre of the "
            "span used "
            "as one attachment node in the reference estimate",
        },
        "axial_load_info": {
            "mass_above_hinge_mast_assy_kg": round(float(above_hinge["slice_mass_kg"].sum()), 3),
            "note": "gravity pre-load (P-delta) lowers the bending frequency; not in the estimate",
        },
        "frequency_estimate_reference": {
            "warning": "reference only (not a verdict); dynamics-expert to verify",
            "method": "planar Euler-Bernoulli frame FE (50 mm elements, consistent mass, "
            "axial dof) and "
            "Rayleigh quotient with the static shape under a lateral 1 g load",
            "cases": {
                "cantilever": f"clamped at the hinge height z = {z_hinge:.3f} m, mast above "
                f"it; drive + tool, top "
                "sheave, winch as rigid bodies; backstay ignored",
                "fore_aft_pin_backstay": "whole mast incl. foot and lower guide; pin at the "
                "hinge point, "
                "locked backstay as an axial spring along its axis",
            },
            "results_hz": frequencies,
        },
        "checks": checks,
        "timings_s": {k: round(v, 1) for k, v in timings.items()},
        "raster_cell_mm": args.raster_mm,
        "csv": str(OUT_CSV.relative_to(PROJECT_ROOT)).replace("\\", "/"),
    }

    csv_columns = [
        "z_center_m",
        "z_lo_m",
        "z_hi_m",
        "segments",
        "A_m2",
        "x_c_m",
        "y_c_m",
        "Iy_m4",
        "Ix_m4",
        "Ixy_m4",
        "I_max_m4",
        "I_min_m4",
        "principal_angle_deg",
        "J_m4",
        "closed_cells",
        "A_mean_m2",
        "A_eff_m2",
        "Iy_eff_m4",
        "Ix_eff_m4",
        "J_eff_m4",
        "EA_eff_N",
        "EIy_eff_N_m2",
        "EIx_eff_N_m2",
        "GJ_eff_N_m2",
        "slice_mass_kg",
        "m_per_m_total_kg_m",
        "m_per_m_plates_kg_m",
        "m_per_m_flange_diaphragm_kg_m",
        "m_per_m_ladder_kg_m",
        "m_per_m_rack_pin_kg_m",
        "slice_com_x_m",
        "slice_com_y_m",
        "raster_area_rel_diff",
        "stiffness_roles",
        "stiffness_parts",
    ]
    beam[csv_columns].to_csv(OUT_CSV, index=False, float_format="%.9g", encoding="utf-8")
    OUT_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=1, default=float), encoding="utf-8"
    )
    print(f"wrote {OUT_JSON} and {OUT_CSV}")

    if not args.skip_plots:
        plot_sections(panels, OUT_SECTIONS_PNG)
        markers = {
            "hinge pin": (z_hinge, "#d1495b"),
            "backstay pivot": (backstay["upper_pivot_body_m"][2], "#8a5cc2"),
        }
        for lower, upper in zip(SEGMENTS[:-1], SEGMENTS[1:], strict=True):
            markers[f"joint {lower}/{upper}"] = (ranges[upper][0] * MM, "#7a7a7a")
        plot_distribution(beam, markers, drive_levels, OUT_DISTRIBUTION_PNG)
        print(f"wrote {OUT_SECTIONS_PNG.name}, {OUT_DISTRIBUTION_PNG.name}")
    print(json.dumps(frequencies, indent=1))
    print(f"total {time.perf_counter() - t_start:.1f} s")


if __name__ == "__main__":
    main()
