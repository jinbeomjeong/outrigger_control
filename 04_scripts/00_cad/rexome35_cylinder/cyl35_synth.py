"""REXOME35 cylinder shapes (drawing DWG REXOME35-9206 Rev.0) and their mass properties.

One job per call (``--job NAME``), run in parallel by cyl35_run.py on the E-cores.

Jobs
    synth_moving_<leg>   drawing-chain synthesis of the leg moving part (pad assembly + rod assembly, ball joint)
    synth_barrel_<leg>   drawing-chain synthesis of the barrel (tube, gland, cap, mounting plate with bolt holes)
    cadmod_moving_<leg>  CAD solid 10 with the piston enlarged D115 -> D130 (front only)
    cadmod_barrel_<leg>  CAD solid 17 with the bore enlarged D115 -> D130 over the 700 mm bore (front only)

Frames and units
    Built in the machine body frame (x forward, y left, z up), millimetres, origin = CAD origin.
    Moving parts in the RETRACTED state (pad bottom at YAML legs.<leg>.pad_bottom_center_retracted_m z).
    BREP files are written in the CAD frame (X_cad = y, Y_cad = z, Z_cad = x, mm) at the CAD pose
    (retracted - legs.<leg>.retracted_offset_from_cad_m along +z), i.e. the convention of 01_cad/02_legs/legs/*.brep,
    so build_sim_shapes.py / export_params.py read them unchanged.
    Mass properties: kg, m, kg m^2; inertia about the CoM, body axes (OCCT MatrixOfInertia, products with minus sign).

Every dimension that is not a drawing dimension is marked ASSUMPTION or READ (read off the drawing picture, the
drawing has no dimension there; uncertainty about +-3 mm).
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import yaml

PROJECT = Path(__file__).resolve().parents[3]  # moved from the cad scratchpad 2026-10-25
YAML_PATH = PROJECT / "02_params" / "rexome33.yaml"
LEGS_BREP = PROJECT / "01_cad" / "02_legs" / "legs"
CSV_PARTS = PROJECT / "01_cad" / "01_parts" / "parts_classified.csv"
RHO_KG_MM3 = 7.85e-6  # ASSUMPTION: steel 7,850 kg/m^3 (CAD material SS400 7.85 g/cm^3); drawing has no material
LEG_ORDER = ("FL", "FR", "RL", "RR")
CAD_FILES = {"FL": "FRONT_JACK_CYL_1", "FR": "FRONT_JACK_CYL_2", "RL": "REAR_JACK_CYL_1", "RR": "REAR_JACK_CYL_2"}
R_BODY_FROM_CAD = np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])

# ---------------------------------------------------------------------------------------------------------------
# Drawing dimensions (mm). h = height above the pad bottom along the cylinder axis (retracted), h_b = above the
# barrel bottom (head end). D = drawing dimension, R = READ off the picture (no dimension), A = ASSUMPTION.
# ---------------------------------------------------------------------------------------------------------------
DIMS = {
    "front": {
        "source": "08_test_data/datasheets/cylinder_front_extract.md (DWG REXOME35-9206 Rev.0 FRONT, p.1)",
        "bore": 130.0, "rod": 110.0, "tube_od": 160.0,                     # D (phi130H9 / phi110f8 / phi160)
        "pad_portion": 170.0, "body": 965.0, "head": 125.0, "stroke_zone": 700.0, "cap": 140.0,  # D
        "pad_side": 330.0,                                                 # D (SECTION A-A' 330 x 330)
        "pad_chamfer": 30.0,                                               # A (CAD 30; picture about 28)
        "pad_thickness": 25.0, "pad_side_height": 20.0,                    # A (CAD / YAML pad.thickness_m; picture 25.6)
        "rib_t": 15.0, "rib_len": 100.0,                                   # D (rib 15 x 100)
        "rib_h_in": 36.0, "rib_h_out": 9.0,                                # R (side view triangle)
        "housing_r": 85.0, "housing_top": 83.0, "retainer_top": 115.0,     # R (block h 25.6-83, retainer 83-115, OD ~170)
        "ball_r": 50.0, "ball_h": 84.0,                                    # R (ball D100, centre 84 above pad bottom)
        "neck_r": 39.0, "neck_top": 139.0, "rod_start": 158.6,             # R (neck R39 to 139, cone to the rod at 158.6)
        "piston_t": 30.0,                                                  # R (picture 29.5; CAD 20)
        "flange_from_pad": 520.0, "flange_len": 345.0, "flange_height": 280.0,  # D
        "flange_face": 98.0, "flange_t": 20.0, "flange_step": None,        # D (98 axis -> mounting face, plate 20)
        "bolt_d": 26.0, "bolt_rows": 230.0,                                # D (2x6-phi26, rows 230)
        "bolt_axial_from_flange_start": [25.0, 75.0, 125.0, 220.0, 270.0, 320.0],  # D (25-50-50-(95)-50-50-25)
    },
    "rear": {
        "source": "08_test_data/datasheets/cylinder_rear_extract.md (DWG REXOME35-9206 Rev.0 REAR, p.1)",
        "bore": 110.0, "rod": 90.0, "tube_od": 137.0,                      # D (phi110H9 / phi90f8 / phi137)
        "pad_portion": 170.0, "body": 945.0, "head": 105.0, "stroke_zone": 700.0, "cap": 140.0,  # D
        "pad_side": 250.0,                                                 # D (SECTION A-A' 250 x 250)
        "pad_chamfer": 30.0,                                               # A (picture 25-30)
        "pad_thickness": 25.0, "pad_side_height": 20.0,                    # A (as front; picture 27.7)
        "rib_t": 15.0, "rib_len": 65.0,                                    # D (rib 15, 65)
        "rib_h_in": 31.0, "rib_h_out": 9.0,                                # R
        "housing_r": 85.0, "housing_top": 84.0, "retainer_top": 116.0,     # R (section ring OD ~172)
        "ball_r": 45.0, "ball_h": 84.0,                                    # R (ball D90, centre 83.9)
        "neck_r": 36.0, "neck_top": 150.4, "rod_start": 150.4,             # R (neck R36, rod D90 from 150.4)
        "piston_t": 30.0,                                                  # R (picture 32.7)
        "flange_from_pad": 525.0, "flange_len": 340.0, "flange_height": 250.0,  # D
        "flange_face": 89.0, "flange_t": 25.0,                             # R/D (main face ~89, plate 25)
        "flange_step": {"len_cap_side": 135.0, "depth": 5.0},              # D (135 x 5, face 84 on the step)
        "bolt_d": 22.0, "bolt_rows": 210.0,                                # D (10-phi22, rows 210)
        "bolt_axial_from_flange_start": [30.0, 100.0, 170.0, 240.0, 310.0],  # D (30-70-70-70-70-30)
    },
}
# Piston position (ASSUMPTION, consistent with the mechanical stroke 700 = user decision Q-U4): retracted piston
# bottom = top of the 700 zone, so that at full extension the piston bottom reaches the gland top. The picture
# shows the retracted piston at the 700 / 140 boundary (front 994-1023, rear 972-1005 read).
# Bore cavity runs from the gland top to the retracted piston top; cap = solid from there to the cap end
# (ASSUMPTION: cushion / port bores in the cap ignored). Not modelled (ASSUMPTION): bellows, 8 pad bolts (housing
# counted solid), valve block (purchased, 'sa-geup'), pipes, seals, oil.


def side(leg: str) -> str:
    return "front" if leg[0] == "F" else "rear"


def load_yaml() -> dict:
    with open(YAML_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def pad_side_angle_deg(poly: np.ndarray) -> float:
    """Direction of the long pad sides from body x, folded to [0, 90) (same rule as build_sim_shapes)."""
    angles = []
    for a, b in zip(poly, np.roll(poly, -1, axis=0)):
        d = b - a
        if np.hypot(*d) >= 0.2:
            angles.append(math.degrees(math.atan2(d[1], d[0])) % 90.0)
    return float(np.degrees(np.angle(np.exp(1j * np.radians(np.array(angles)) * 4).mean())) / 4 % 90.0)


# ---------------------------------------------------------------------------------------------------------------
# OCC helpers
# ---------------------------------------------------------------------------------------------------------------
def gp_ax2(x, y, z, d=(0, 0, 1)):
    from OCC.Core.gp import gp_Ax2, gp_Dir, gp_Pnt
    return gp_Ax2(gp_Pnt(float(x), float(y), float(z)), gp_Dir(*map(float, d)))


def cylinder(x, y, z0, r, h):
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    return BRepPrimAPI_MakeCylinder(gp_ax2(x, y, z0), float(r), float(h)).Shape()


def cone(x, y, z0, r1, r2, h):
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCone
    return BRepPrimAPI_MakeCone(gp_ax2(x, y, z0), float(r1), float(r2), float(h)).Shape()


def sphere(x, y, z, r):
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeSphere
    from OCC.Core.gp import gp_Pnt
    return BRepPrimAPI_MakeSphere(gp_Pnt(float(x), float(y), float(z)), float(r)).Shape()


def polygon_wire(points3):
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakePolygon
    from OCC.Core.gp import gp_Pnt
    poly = BRepBuilderAPI_MakePolygon()
    for p in points3:
        poly.Add(gp_Pnt(*map(float, p)))
    poly.Close()
    return poly.Wire()


def prism(points3, vec):
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCC.Core.gp import gp_Vec
    face = BRepBuilderAPI_MakeFace(polygon_wire(points3)).Face()
    return BRepPrimAPI_MakePrism(face, gp_Vec(*map(float, vec))).Shape()


def loft(points_a, points_b):
    from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_ThruSections
    ts = BRepOffsetAPI_ThruSections(True, True, 1e-6)
    ts.AddWire(polygon_wire(points_a))
    ts.AddWire(polygon_wire(points_b))
    ts.Build()
    return ts.Shape()


def fuse(*shapes):
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Fuse
    out = shapes[0]
    for s in shapes[1:]:
        op = BRepAlgoAPI_Fuse(out, s)
        op.SimplifyResult()
        out = op.Shape()
    return out


def cut(a, *tools):
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
    out = a
    for t in tools:
        op = BRepAlgoAPI_Cut(out, t)
        op.SimplifyResult()
        out = op.Shape()
    return out


def compound(shapes):
    from OCC.Core.BRep import BRep_Builder
    from OCC.Core.TopoDS import TopoDS_Compound
    c = TopoDS_Compound()
    b = BRep_Builder()
    b.MakeCompound(c)
    for s in shapes:
        b.Add(c, s)
    return c


def solids_of(shape):
    from OCC.Core.TopAbs import TopAbs_SOLID
    from OCC.Core.TopExp import TopExp_Explorer
    out = []
    ex = TopExp_Explorer(shape, TopAbs_SOLID)
    while ex.More():
        out.append(ex.Current())
        ex.Next()
    return out


def read_brep(path: Path):
    from OCC.Core.BRep import BRep_Builder
    from OCC.Core.BRepTools import breptools
    from OCC.Core.TopoDS import TopoDS_Shape
    s = TopoDS_Shape()
    if not breptools.Read(s, str(path), BRep_Builder()):
        raise SystemExit(f"cannot read {path}")
    return s


def transform(shape, R: np.ndarray, t):
    """p' = R p + t (R orthonormal, mm)."""
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCC.Core.gp import gp_Trsf
    tr = gp_Trsf()
    tr.SetValues(*(float(v) for v in (R[0, 0], R[0, 1], R[0, 2], t[0], R[1, 0], R[1, 1], R[1, 2], t[1],
                                       R[2, 0], R[2, 1], R[2, 2], t[2])))
    return BRepBuilderAPI_Transform(shape, tr, True).Shape()


def props(shapes) -> dict:
    """Per-solid GProp sum (unit density), mm: volume, CoM, inertia about the CoM (mm^5), bbox, validity."""
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.BRepCheck import BRepCheck_Analyzer
    from OCC.Core.BRepGProp import brepgprop
    from OCC.Core.GProp import GProp_GProps
    total = GProp_GProps()
    valid = True
    n = 0
    box = Bnd_Box()
    for s in shapes:
        for so in solids_of(s):
            p = GProp_GProps()
            brepgprop.VolumeProperties(so, p)
            total.Add(p, 1.0)
            valid &= bool(BRepCheck_Analyzer(so).IsValid())
            brepbndlib.AddOptimal(so, box, False, False)
            n += 1
    c = total.CentreOfMass()
    m = total.MatrixOfInertia()
    return {"volume_mm3": total.Mass(), "com_mm": np.array([c.X(), c.Y(), c.Z()]),
            "inertia_mm5": np.array([[m.Value(r, k) for k in (1, 2, 3)] for r in (1, 2, 3)]),
            "bbox_mm": np.array(box.Get()).reshape(2, 3), "valid": valid, "solids": n}


def si(p: dict, rho=RHO_KG_MM3) -> dict:
    """mm unit-density properties -> SI mass properties (kg, m, kg m^2)."""
    I = 0.5 * (p["inertia_mm5"] + p["inertia_mm5"].T) * rho * 1e-6
    return {"volume_m3": p["volume_mm3"] * 1e-9, "mass_kg": p["volume_mm3"] * rho,
            "com_m": (p["com_mm"] * 1e-3).tolist(), "inertia_kg_m2": I.tolist(),
            "bbox_m": (p["bbox_mm"] * 1e-3).tolist(), "valid": p["valid"], "solids": p["solids"]}


def tensor_checks(I) -> dict:
    I = np.asarray(I, float)
    ev = np.linalg.eigvalsh(0.5 * (I + I.T))
    return {"symmetric_rel": float(np.abs(I - I.T).max() / np.abs(I).max()), "principal_kg_m2": ev.tolist(),
            "positive_definite": bool(ev.min() > 0),
            "triangle_ok": bool(ev[0] + ev[1] >= ev[2] * (1 - 1e-9))}


def mesh_check(shapes, linear_mm=0.05, angular_rad=0.1) -> dict:
    """BRepMesh tessellation -> trimesh volume / CoM / inertia vs the B-rep (per solid, summed)."""
    import trimesh
    from OCC.Core.BRep import BRep_Tool
    from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
    from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_REVERSED
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopLoc import TopLoc_Location
    from OCC.Core.TopoDS import topods
    vol = 0.0
    mom1 = np.zeros(3)
    I_origin = np.zeros((3, 3))
    watertight = True
    for s in shapes:
        for so in solids_of(s):
            BRepMesh_IncrementalMesh(so, linear_mm, False, angular_rad, True).Perform()
            V, T, off = [], [], 0
            ex = TopExp_Explorer(so, TopAbs_FACE)
            while ex.More():
                f = topods.Face(ex.Current())
                ex.Next()
                loc = TopLoc_Location()
                tri = BRep_Tool.Triangulation(f, loc)
                if tri is None:
                    watertight = False
                    continue
                tr = loc.Transformation()
                for k in range(1, tri.NbNodes() + 1):
                    q = tri.Node(k).Transformed(tr)
                    V.append((q.X(), q.Y(), q.Z()))
                for k in range(1, tri.NbTriangles() + 1):
                    a, b, c = tri.Triangle(k).Get()
                    T.append((a - 1 + off, c - 1 + off, b - 1 + off) if f.Orientation() == TopAbs_REVERSED
                             else (a - 1 + off, b - 1 + off, c - 1 + off))
                off = len(V)
            m = trimesh.Trimesh(np.array(V), np.array(T), process=False)
            m.merge_vertices(digits_vertex=6)
            watertight &= bool(m.is_watertight)
            v = float(m.volume)
            c = np.asarray(m.center_mass)
            Ic = np.asarray(m.moment_inertia)  # unit density, about the CoM
            vol += v
            mom1 += v * c
            I_origin += Ic + v * (np.dot(c, c) * np.eye(3) - np.outer(c, c))
    com = mom1 / vol
    I_com = I_origin - vol * (np.dot(com, com) * np.eye(3) - np.outer(com, com))
    return {"linear_deflection_mm": linear_mm, "angular_deflection_rad": angular_rad, "volume_mm3": vol,
            "com_mm": com, "inertia_mm5": I_com, "watertight": watertight}


def compare(mesh: dict, brep: dict) -> dict:
    return {"volume_rel": mesh["volume_mm3"] / brep["volume_mm3"] - 1.0,
            "com_abs_mm": float(np.linalg.norm(mesh["com_mm"] - brep["com_mm"])),
            "inertia_frobenius_rel": float(np.linalg.norm(mesh["inertia_mm5"] - brep["inertia_mm5"])
                                           / np.linalg.norm(brep["inertia_mm5"])),
            "watertight": mesh["watertight"]}


def write_cad_brep(shape, path: Path, offset_z_m: float) -> dict:
    """Body-frame retracted shape (mm) -> CAD frame at the CAD pose (mm), ASCII BREP."""
    from OCC.Core.BRepTools import breptools
    shifted = transform(shape, np.eye(3), (0.0, 0.0, -offset_z_m * 1e3))
    cad = transform(shifted, R_BODY_FROM_CAD.T, (0.0, 0.0, 0.0))
    path.parent.mkdir(parents=True, exist_ok=True)
    breptools.Write(cad, str(path))
    back = props([read_brep(path)])
    return {"file": str(path), "bytes": path.stat().st_size, "volume_mm3_read_back": back["volume_mm3"],
            "solids": back["solids"], "valid": back["valid"]}


# ---------------------------------------------------------------------------------------------------------------
# synthesis
# ---------------------------------------------------------------------------------------------------------------
def pad_polygon(centre_xy, a, c, angle_deg):
    """Square a x a with 45 deg corner chamfers of leg c, rotated by angle_deg; CCW (x, y), mm."""
    s = a / 2
    local = [(s - c, -s), (s, -s + c), (s, s - c), (s - c, s), (-s + c, s), (-s, s - c), (-s, -s + c), (-s + c, -s)]
    th = math.radians(angle_deg)
    R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
    return np.array(local) @ R.T + np.asarray(centre_xy)


def inset(poly, d):
    n = len(poly)
    lines = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        t = (b - a) / np.linalg.norm(b - a)
        lines.append((a + d * np.array([-t[1], t[0]]), t))
    out = []
    for i in range(n):
        (p1, d1), (p2, d2) = lines[i - 1], lines[i]
        k = np.linalg.solve(np.column_stack([d1, -d2]), p2 - p1)
        out.append(p1 + k[0] * d1)
    return np.array(out)


def synth_moving(leg: str, p: dict, pad_override=None) -> dict:
    d = DIMS[side(leg)]
    L = p["legs"][leg]
    x0, y0 = (np.array(L["cylinder_axis_xy_m"]) * 1e3).tolist()
    z0 = float(L["pad_bottom_center_retracted_m"][2]) * 1e3
    angle = pad_side_angle_deg(np.array(L["pad"]["polygon_xy_m"]))
    t, sh = d["pad_thickness"], d["pad_side_height"]
    if pad_override == "yaml":  # cross-check: CAD / YAML pad polygon
        poly = np.array(L["pad"]["polygon_xy_m"]) * 1e3 + [x0, y0]
    else:
        poly = pad_polygon((x0, y0), d["pad_side"], d["pad_chamfer"], angle)
    # pad plate: vertical sides up to the side height, 45 deg top-edge chamfer to the thickness (CAD style)
    plate = fuse(prism([(*q, z0) for q in poly], (0, 0, sh)),
                 loft([(*q, z0 + sh) for q in poly], [(*q, z0 + t) for q in inset(poly, t - sh)]))
    # 4 ribs on the diagonals (towards the chamfered corners): thickness rib_t, radial housing_r -> + rib_len,
    # height rib_h_in at the housing -> rib_h_out at the outer end (READ)
    ribs = []
    r_in, r_out = d["housing_r"] - 1.0, d["housing_r"] + d["rib_len"]
    for k in range(4):
        phi = math.radians(angle + 45.0 + 90.0 * k)
        u = np.array([math.cos(phi), math.sin(phi)])
        w = np.array([-u[1], u[0]]) * d["rib_t"] / 2
        prof = [(r_in, z0 + t), (r_out, z0 + t), (r_out, z0 + t + d["rib_h_out"]), (r_in, z0 + t + d["rib_h_in"])]
        pts = [(*(np.array([x0, y0]) + r * u - w), z) for r, z in prof]
        ribs.append(prism(pts, (*(2 * w), 0.0)))
    ball_c = z0 + d["ball_h"]
    ball = sphere(x0, y0, ball_c, d["ball_r"])
    block = cylinder(x0, y0, z0 + t, d["housing_r"], d["housing_top"] - t)
    retainer = cut(cylinder(x0, y0, z0 + d["housing_top"], d["housing_r"], d["retainer_top"] - d["housing_top"]),
                   cylinder(x0, y0, z0 + d["housing_top"] - 1, d["neck_r"], d["retainer_top"] - d["housing_top"] + 2))
    housing = cut(fuse(block, retainer, *ribs), ball)
    pad_assy = fuse(plate, housing)
    # rod assembly: ball + neck (+ cone) + rod + piston
    bore_top = d["pad_portion"] + d["head"] + d["stroke_zone"]  # top of the 700 zone (h)
    rod_top = bore_top                                            # = retracted piston bottom (ASSUMPTION)
    rod_parts = [ball, cylinder(x0, y0, ball_c, d["neck_r"], d["neck_top"] - d["ball_h"])]
    if d["rod_start"] > d["neck_top"] + 1e-6:
        rod_parts.append(cone(x0, y0, z0 + d["neck_top"], d["neck_r"], d["rod"] / 2, d["rod_start"] - d["neck_top"]))
    rod_parts.append(cylinder(x0, y0, z0 + d["rod_start"], d["rod"] / 2, rod_top - d["rod_start"]))
    rod_parts.append(cylinder(x0, y0, z0 + rod_top, d["bore"] / 2, d["piston_t"]))
    rod_assy = fuse(*rod_parts)
    # pieces for the reporting splits
    pieces = {"plate": [plate], "housing_ribs": [housing], "ball": [ball],
              "neck_rod_piston": [cut(rod_assy, ball)], "rod_assembly": [rod_assy], "pad_assembly": [pad_assy]}
    geo = {"axis_xy_mm": [x0, y0], "pad_bottom_z_mm": z0, "pad_side_angle_deg": angle,
           "pad_polygon_xy_mm": poly.tolist(), "ball_centre_above_pad_bottom_mm": d["ball_h"],
           "rod_top_above_pad_bottom_mm": rod_top, "piston_top_above_pad_bottom_mm": rod_top + d["piston_t"],
           "barrel_bottom_above_pad_bottom_mm_drawing": d["pad_portion"],
           "pad_area_mm2": 0.5 * abs(np.dot(poly[:, 0], np.roll(poly[:, 1], -1)) - np.dot(poly[:, 1], np.roll(poly[:, 0], -1)))}
    return {"whole": compound([pad_assy, rod_assy]), "pieces": pieces, "geometry": geo}


def flange_normal(leg: str, axis_xy) -> np.ndarray:
    """Outward normal of the mounting face (towards the superstructure centre), body xy (CAD check in report)."""
    if leg[0] == "F":
        n = -np.sign(np.asarray(axis_xy)) / math.sqrt(2)   # FL (+,+) -> (-,-)/sqrt2 ; FR (+,-) -> (-,+)/sqrt2
    else:
        n = np.array([0.0, -math.copysign(1.0, axis_xy[1])])  # RL -> -y ; RR -> +y
    return n


def synth_barrel(leg: str, p: dict, cap_end_z_mm: float) -> dict:
    d = DIMS[side(leg)]
    L = p["legs"][leg]
    x0, y0 = (np.array(L["cylinder_axis_xy_m"]) * 1e3).tolist()
    zb = cap_end_z_mm - d["body"]                      # barrel bottom (head end), ASSUMPTION: cap end = CAD cap end
    ro, rb, rr = d["tube_od"] / 2, d["bore"] / 2, d["rod"] / 2
    cav_top = d["head"] + d["stroke_zone"] + d["piston_t"]  # h_b of the retracted piston top
    tube = cut(cylinder(x0, y0, zb, ro, d["body"]),
               cylinder(x0, y0, zb - 1, rr, d["head"] + 2),
               cylinder(x0, y0, zb + d["head"], rb, cav_top - d["head"]))
    # mounting plate
    n = flange_normal(leg, (x0, y0))
    tvec = np.array([-n[1], n[0]])
    z1 = zb + d["flange_from_pad"] - d["pad_portion"]
    face, th = d["flange_face"], d["flange_t"]
    c0 = np.array([x0, y0])

    def plate_box(r_in, r_out, za, zl):
        pts = [(*(c0 + r_in * n - tvec * d["flange_height"] / 2), za), (*(c0 + r_out * n - tvec * d["flange_height"] / 2), za),
               (*(c0 + r_out * n + tvec * d["flange_height"] / 2), za), (*(c0 + r_in * n + tvec * d["flange_height"] / 2), za)]
        return prism(pts, (0, 0, zl))

    if d["flange_step"]:
        ls, dep = d["flange_step"]["len_cap_side"], d["flange_step"]["depth"]
        plate = fuse(plate_box(face - th, face, z1, d["flange_len"] - ls),
                     plate_box(face - th, face - dep, z1 + d["flange_len"] - ls, ls))
    else:
        plate = plate_box(face - th, face, z1, d["flange_len"])
    holes = []
    for zh in d["bolt_axial_from_flange_start"]:
        for s in (-1, 1):
            c = c0 + (face - th - 5) * n + s * tvec * d["bolt_rows"] / 2
            from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCylinder
            holes.append(BRepPrimAPI_MakeCylinder(gp_ax2(c[0], c[1], z1 + zh, (n[0], n[1], 0.0)),
                                                  d["bolt_d"] / 2, th + 10).Shape())
    plate = cut(plate, *holes)
    # remove the part of the plate inside the bore cavity / rod hole (plate inner face may cut the tube wall)
    plate = cut(plate, cylinder(x0, y0, zb - 1, rb, d["body"] + 2))
    whole = fuse(tube, plate)
    geo = {"axis_xy_mm": [x0, y0], "barrel_bottom_z_mm": zb, "cap_end_z_mm": cap_end_z_mm,
           "mount_normal_xy": n.tolist(), "plate_z_range_mm": [z1, z1 + d["flange_len"]],
           "bore_cavity_z_range_mm": [zb + d["head"], zb + cav_top]}
    return {"whole": whole, "pieces": {"tube": [tube], "plate": [plate]}, "geometry": geo}


def cad_axis(shape, radius: float):
    """Axis (X, Z) of the first cylindrical face of the given radius (CAD frame, axis along Y)."""
    from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
    from OCC.Core.GeomAbs import GeomAbs_Cylinder
    from OCC.Core.TopAbs import TopAbs_FACE
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopoDS import topods
    ex = TopExp_Explorer(shape, TopAbs_FACE)
    while ex.More():
        f = topods.Face(ex.Current())
        ex.Next()
        s = BRepAdaptor_Surface(f, True)
        if s.GetType() == GeomAbs_Cylinder and abs(s.Cylinder().Radius() - radius) < 1e-6:
            a = s.Cylinder().Axis()
            if abs(abs(a.Direction().Y()) - 1) < 1e-9:
                return a.Location().X(), a.Location().Z()
    raise SystemExit(f"no R{radius} face")


def cad_y_span(shape, radius: float):
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.GeomAbs import GeomAbs_Cylinder
    from OCC.Core.TopAbs import TopAbs_FACE
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopoDS import topods
    spans = []
    ex = TopExp_Explorer(shape, TopAbs_FACE)
    while ex.More():
        f = topods.Face(ex.Current())
        ex.Next()
        s = BRepAdaptor_Surface(f, True)
        if s.GetType() == GeomAbs_Cylinder and abs(s.Cylinder().Radius() - radius) < 1e-6:
            b = Bnd_Box()
            brepbndlib.AddOptimal(f, b, False, False)
            _, y0, _, _, y1, _ = b.Get()
            spans.append((y0, y1))
    return spans


def cadmod(kind: str, leg: str, p: dict) -> dict:
    """Front only: CAD solid with the bore / piston D115 -> D130 (drawing). CAD frame -> body frame (+offset)."""
    sid = "10" if kind == "moving" else "17"
    path = LEGS_BREP / f"{CAD_FILES[leg]}___{sid}_1.brep"
    shape = solids_of(read_brep(path))[0]
    X, Z = cad_axis(shape, 57.5)
    spans = cad_y_span(shape, 57.5)
    (ya, yb) = max(spans, key=lambda s: s[1] - s[0])
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    from OCC.Core.gp import gp_Ax2, gp_Dir, gp_Pnt
    rb_new = DIMS["front"]["bore"] / 2
    ring = cut(BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(X, ya, Z), gp_Dir(0, 1, 0)), rb_new, yb - ya).Shape(),
               BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(X, ya - 1, Z), gp_Dir(0, 1, 0)), 57.5, yb - ya + 2).Shape())
    new = fuse(shape, ring) if kind == "moving" else cut(shape, ring)
    offset = float(p["legs"][leg]["retracted_offset_from_cad_m"]) * 1e3 if kind == "moving" else 0.0
    to_body = lambda s: transform(transform(s, R_BODY_FROM_CAD, (0, 0, 0)), np.eye(3), (0, 0, offset))  # noqa: E731
    ring_p = props([ring])
    return {"whole": to_body(new), "pieces": {"cad_original": [to_body(shape)], "ring": [to_body(ring)]},
            "geometry": {"cad_brep": str(path), "axis_cad_XZ_mm": [X, Z], "r57.5_face_y_span_cad_mm": [ya, yb],
                         "ring_r_mm": [57.5, rb_new], "ring_volume_mm3": ring_p["volume_mm3"],
                         "ring_volume_analytic_mm3": math.pi * (rb_new**2 - 57.5**2) * (yb - ya),
                         "offset_z_mm": offset}}


# ---------------------------------------------------------------------------------------------------------------
def run_job(job: str, out_dir: Path, cache_dir: Path | None) -> dict:
    t0 = time.perf_counter()
    p = load_yaml()
    kind, what, leg = job.split("_")[0], job.split("_")[1], job.split("_")[-1]
    variant = job.split("_")[2] if len(job.split("_")) == 4 else None
    if kind == "synth" and what == "moving":
        res = synth_moving(leg, p, pad_override="yaml" if variant == "yamlpad" else None)
    elif kind == "synth" and what == "barrel":
        import pandas as pd
        parts = pd.read_csv(CSV_PARTS, encoding="utf-8-sig")
        inst = {"FL": "FRONT JACK CYL:1", "FR": "FRONT JACK CYL:2", "RL": "REAR JACK CYL:1", "RR": "REAR JACK CYL:2"}[leg]
        row = parts[(parts["leg"] == leg) & (parts["group"] == "leg_barrel")]
        cap = float(row["bbox_max_y_mm"].iloc[0])  # CAD Y = body z (barrel has no offset)
        res = synth_barrel(leg, p, cap)
        res["geometry"]["cad_instance"] = inst
    else:
        res = cadmod(what, leg, p)
    whole = props([res["whole"]])
    out = {"job": job, "leg": leg, "kind": kind, "part": what, "variant": variant,
           "density_kg_m3": RHO_KG_MM3 * 1e9, "density_status": "ASSUMPTION (steel)",
           "frame": "body axes (x fwd, y left, z up), origin CAD origin, SI; moving parts retracted; inertia about CoM",
           "geometry": res["geometry"], "whole": si(whole), "pieces": {}}
    out["whole"]["tensor"] = tensor_checks(out["whole"]["inertia_kg_m2"])
    bb = whole["bbox_mm"]
    out["whole"]["com_inside_bbox"] = bool(np.all(whole["com_mm"] >= bb[0]) and np.all(whole["com_mm"] <= bb[1]))
    for k, v in res["pieces"].items():
        out["pieces"][k] = si(props(v))
    mc = mesh_check([res["whole"]])
    out["mesh_check"] = compare(mc, whole)
    if kind == "synth" and what == "moving":
        L = p["legs"][leg]
        zb = float(L["pad_bottom_center_retracted_m"][2])
        for name, pad_keys, rod_keys in (("ball_joint", ["pad_assembly"], ["rod_assembly"]),):
            pass
        # split A (ball joint, physical): pad body = plate + ribs + socket housing; rod body = ball + rod + piston
        # split B (plane 25 mm, current YAML definition): pad body = plate; rod body = everything above the plane
        pa, ra = props(res["pieces"]["pad_assembly"]), props(res["pieces"]["rod_assembly"])
        pb, rbp = props(res["pieces"]["plate"]), props([*res["pieces"]["housing_ribs"], *res["pieces"]["rod_assembly"]])
        out["splits"] = {}
        for name, a, b in (("ball_joint", pa, ra), ("plane_25mm", pb, rbp)):
            A, B = si(a), si(b)
            for X in (A, B):
                X["com_above_pad_bottom_m"] = X["com_m"][2] - zb
                X["tensor"] = tensor_checks(X["inertia_kg_m2"])
            # parallel-axis recombination check
            m = A["mass_kg"] + B["mass_kg"]
            c = (A["mass_kg"] * np.array(A["com_m"]) + B["mass_kg"] * np.array(B["com_m"])) / m
            I = np.zeros((3, 3))
            for X in (A, B):
                dd = np.array(X["com_m"]) - c
                I += np.array(X["inertia_kg_m2"]) + X["mass_kg"] * (dd @ dd * np.eye(3) - np.outer(dd, dd))
            W = out["whole"]
            out["splits"][name] = {"pad_body": A, "rod_body": B, "recombined_vs_whole": {
                "mass_rel": m / W["mass_kg"] - 1, "com_abs_m": float(np.linalg.norm(c - W["com_m"])),
                "inertia_frobenius_rel": float(np.linalg.norm(I - W["inertia_kg_m2"]) / np.linalg.norm(W["inertia_kg_m2"]))}}
        out["whole"]["com_above_pad_bottom_m"] = out["whole"]["com_m"][2] - zb
    if kind == "cadmod":
        o = props(res["pieces"]["cad_original"])
        out["cad_original"] = si(o)
        out["delta_mass_kg"] = out["whole"]["mass_kg"] - out["cad_original"]["mass_kg"]
        out["delta_mass_analytic_kg"] = (1 if what == "moving" else -1) * res["geometry"]["ring_volume_analytic_mm3"] * RHO_KG_MM3
        if what == "moving":
            zb = float(p["legs"][leg]["pad_bottom_center_retracted_m"][2])
            out["whole"]["com_above_pad_bottom_m"] = out["whole"]["com_m"][2] - zb
    # BREP outputs (CAD frame, CAD pose)
    offset = float(p["legs"][leg]["retracted_offset_from_cad_m"]) if what == "moving" else 0.0
    target = cache_dir if (cache_dir and variant is None and not (kind == "synth" and leg[0] == "F")) else out_dir
    brep_shape = res["whole"]
    out["brep"] = write_cad_brep(brep_shape, target / f"{what}_{leg}{'_' + variant if variant else ''}"
                                 f"{'_synth' if kind == 'synth' and leg[0] == 'F' else ''}.brep", offset)
    out["brep"]["offset_from_cad_m_removed"] = offset
    out["brep"]["read_back_volume_rel"] = out["brep"]["volume_mm3_read_back"] / whole["volume_mm3"] - 1
    out["time_s"] = time.perf_counter() - t0
    try:
        import psutil
        out["cpu_affinity"] = psutil.Process().cpu_affinity()
        out["peak_wset_mb"] = psutil.Process().memory_info().peak_wset / 1e6
    except Exception:  # noqa: BLE001
        pass
    return out


def _default(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    raise TypeError(type(o))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", default=None)
    a = ap.parse_args()
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    res = run_job(a.job, out_dir, Path(a.cache) if a.cache else None)
    (out_dir / f"{a.job}.json").write_text(json.dumps(res, indent=1, default=_default), encoding="utf-8")
    print(a.job, f"{res['whole']['mass_kg']:.3f} kg", f"{res['time_s']:.1f} s")


if __name__ == "__main__":
    main()
