"""Measure the 4 jack cylinders from the cached leg BREPs (CAD mm, Y-up).

Read-only on the project. Writes a JSON next to this script.
"""
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np
from OCC.Core.BRep import BRep_Builder, BRep_Tool
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.BRepTools import breptools
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.GProp import GProp_GProps
from OCC.Core.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_SOLID, TopAbs_VERTEX, TopAbs_REVERSED
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import TopoDS_Shape, topods
from OCC.Core.BRepTools import BRepTools_WireExplorer
from OCC.Core.ShapeAnalysis import shapeanalysis

# Moved from the 2026-10-22 cad scratchpad (cad-run/) on 2026-10-25: inputs and the output JSON
# are project paths relative to this script (output 01_cad/02_legs/drawing_check/).
_PROJECT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
ROOT = os.path.join(_PROJECT, "01_cad", "02_legs", "legs")
OUT = os.path.join(_PROJECT, "01_cad", "02_legs", "drawing_check", "cyl_measure.json")
RHO = 7850.0  # kg/m^3, SS400 (STEP material of solid 10 / 17)

AXIS = {"FL": (1323.8, 2293.8), "FR": (-1323.8, 2293.8),
        "RL": (1167.9, -2556.0), "RR": (-1242.9, -2556.0)}
FILES = {"FL": "FRONT_JACK_CYL_1", "FR": "FRONT_JACK_CYL_2",
         "RL": "REAR_JACK_CYL_1", "RR": "REAR_JACK_CYL_2"}


def load(path):
    s = TopoDS_Shape()
    breptools.Read(s, path, BRep_Builder())
    return s


def faces(shape):
    ex = TopExp_Explorer(shape, TopAbs_FACE)
    while ex.More():
        yield topods.Face(ex.Current())
        ex.Next()


def nsolids(shape):
    n = 0
    ex = TopExp_Explorer(shape, TopAbs_SOLID)
    while ex.More():
        n += 1
        ex.Next()
    return n


def bbox(shape):
    b = Bnd_Box()
    b.SetGap(0.0)
    brepbndlib.AddOptimal(shape, b, False, False)
    return [round(v, 3) for v in b.Get()]


def mass_props(shape):
    p = GProp_GProps()
    brepgprop.VolumeProperties(shape, p)
    c = p.CentreOfMass()
    m = p.MatrixOfInertia()
    I = np.array([[m.Value(i, j) for j in (1, 2, 3)] for i in (1, 2, 3)])
    return p.Mass(), (c.X(), c.Y(), c.Z()), I


def face_info(f):
    a = BRepAdaptor_Surface(f, True)
    b = Bnd_Box()
    b.SetGap(0.0)
    brepbndlib.AddOptimal(f, b, False, False)
    bb = b.Get()
    p = GProp_GProps()
    brepgprop.SurfaceProperties(f, p)
    t = a.GetType()
    d = {"bbox": bb, "area": p.Mass(), "type": t}
    if t == GeomAbs_Cylinder:
        cy = a.Cylinder()
        ax = cy.Axis()
        loc = ax.Location()
        dr = ax.Direction()
        d.update(r=cy.Radius(), loc=(loc.X(), loc.Y(), loc.Z()),
                 dir=(dr.X(), dr.Y(), dr.Z()))
    elif t == GeomAbs_Plane:
        pl = a.Plane()
        n = pl.Axis().Direction()
        if f.Orientation() == TopAbs_REVERSED:
            n = n.Reversed()
        d.update(n=(n.X(), n.Y(), n.Z()))
    return d


def outer_polygon(face):
    w = shapeanalysis.OuterWire(face)
    pts = []
    ex = BRepTools_WireExplorer(w)
    while ex.More():
        v = ex.CurrentVertex()
        q = BRep_Tool.Pnt(v)
        pts.append((q.X(), q.Y(), q.Z()))
        ex.Next()
    return pts


def min_rect(xy):
    """Minimum-area enclosing rectangle by edge-angle search (convex polygon)."""
    best = None
    n = len(xy)
    for i in range(n):
        dx, dz = xy[(i + 1) % n] - xy[i]
        th = math.atan2(dz, dx)
        R = np.array([[math.cos(th), math.sin(th)], [-math.sin(th), math.cos(th)]])
        r = xy @ R.T
        w = r[:, 0].ptp() if hasattr(r[:, 0], "ptp") else np.ptp(r[:, 0])
        h = np.ptp(r[:, 1])
        if best is None or w * h < best[0]:
            best = (w * h, w, h, math.degrees(th))
    return best


def poly_area(xy):
    x, y = xy[:, 0], xy[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


res = {}
for leg, stem in FILES.items():
    ax_x, ax_z = AXIS[leg]
    out = {}
    for sid in ("10", "17"):
        path = os.path.join(ROOT, f"{stem}___{sid}_1.brep")
        s = load(path)
        vol, com, I = mass_props(s)
        rec = {"file": path, "valid": bool(BRepCheck_Analyzer(s).IsValid()),
               "n_solids": nsolids(s), "volume_mm3": vol,
               "mass_kg_at_7850": vol * 1e-9 * RHO,
               "com_cad_mm": com, "bbox_cad_mm": bbox(s)}
        # coaxial (vertical) cylinders: radius -> list of Y ranges
        coax = defaultdict(list)
        holes = []
        planes_y = []
        for f in faces(s):
            d = face_info(f)
            if d["type"] == GeomAbs_Cylinder:
                dr = np.array(d["dir"])
                if abs(abs(dr[1]) - 1) < 1e-6:
                    off = math.hypot(d["loc"][0] - ax_x, d["loc"][2] - ax_z)
                    if off < 1.0:
                        coax[round(d["r"], 2)].append(
                            (round(d["bbox"][1], 2), round(d["bbox"][4], 2), round(d["area"], 1)))
                    else:
                        holes.append(("vertical_offaxis", round(d["r"], 2),
                                      [round(v, 1) for v in d["loc"]], round(off, 1)))
                else:
                    # hole axis horizontal: centre = bbox centre of the face
                    bb = d["bbox"]
                    c = [(bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, (bb[2] + bb[5]) / 2]
                    holes.append(("horizontal", round(d["r"], 2), [round(v, 1) for v in c],
                                  [round(v, 3) for v in dr]))
            elif d["type"] == GeomAbs_Plane:
                n = d["n"]
                if abs(abs(n[1]) - 1) < 1e-6:
                    planes_y.append((round(d["bbox"][1], 2), round(n[1]), round(d["area"], 1)))
        rec["coaxial_cyl_faces"] = {str(k): sorted(v) for k, v in sorted(coax.items())}
        # unique horizontal holes
        uh = {}
        for h in holes:
            if h[0] == "horizontal":
                key = (h[1], tuple(round(v / 2) * 2 for v in h[2]))
                uh[key] = h
        rec["horizontal_holes"] = sorted([(h[1], h[2], h[3]) for h in uh.values()],
                                          key=lambda t: (t[0], t[1][1]))
        rec["offaxis_vertical_cyl"] = sorted({(h[1], tuple(h[2]), h[3]) for h in holes
                                              if h[0] == "vertical_offaxis"})
        rec["y_planes"] = sorted(set(planes_y))
        if sid == "10":
            # pad bottom = lowest -Y plane
            low = None
            for f in faces(s):
                d = face_info(f)
                if d["type"] == GeomAbs_Plane and d["n"][1] < -0.999:
                    if low is None or d["bbox"][1] < low[1]["bbox"][1]:
                        low = (f, d)
            pts = np.array(outer_polygon(low[0]))
            xz = pts[:, [0, 2]]
            area, w, h, th = min_rect(xz)
            rec["pad_bottom"] = {"y_mm": low[1]["bbox"][1], "area_mm2": low[1]["area"],
                                 "n_vertices": len(pts),
                                 "min_rect_mm": [w, h], "min_rect_angle_deg": th,
                                 "polygon_area_mm2": poly_area(xz),
                                 "edge_lengths_mm": [float(np.linalg.norm(xz[(i + 1) % len(xz)] - xz[i]))
                                                     for i in range(len(xz))]}
        rec["inertia_cad_mm2_unit_density_about_com"] = I.tolist()
        out[sid] = rec
    res[leg] = out

with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=1, ensure_ascii=False, default=float)
print("written", OUT)
for leg in res:
    for sid in ("10", "17"):
        r = res[leg][sid]
        print(leg, sid, "valid", r["valid"], "nsol", r["n_solids"], "V mm3 %.0f" % r["volume_mm3"],
              "m %.3f kg" % r["mass_kg_at_7850"], "bbox", r["bbox_cad_mm"])
        print("   coax:", r["coaxial_cyl_faces"])
        print("   holes:", r["horizontal_holes"][:20], "n", len(r["horizontal_holes"]))
        print("   offaxis vertical:", r["offaxis_vertical_cyl"][:12])
        print("   y planes:", r["y_planes"])
        if sid == "10":
            print("   pad:", {k: v for k, v in r["pad_bottom"].items()})

