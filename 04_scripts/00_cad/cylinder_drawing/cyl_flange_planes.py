"""Flange plate faces of the barrel solids: planes whose normal is the bolt-hole axis.

Reports the signed distance of each plane from the cylinder axis (CAD mm).
"""
import math
import os

from OCC.Core.BRep import BRep_Builder
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.BRepTools import breptools
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.GProp import GProp_GProps
from OCC.Core.GeomAbs import GeomAbs_Plane
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import TopoDS_Shape, topods

# Moved from the 2026-10-22 cad scratchpad (cad-run/) on 2026-10-25; project root from the script.
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "01_cad", "02_legs",
                    "legs")
CASES = {
    "FL": ("FRONT_JACK_CYL_1___17_1.brep", (1323.8, 2293.8), (-0.70710678, -0.70710678)),
    "RL": ("REAR_JACK_CYL_1___17_1.brep", (1167.9, -2556.0), (-1.0, 0.0)),
}
for leg, (fn, (ax, az), (nx, nz)) in CASES.items():
    s = TopoDS_Shape()
    breptools.Read(s, os.path.join(ROOT, fn), BRep_Builder())
    ex = TopExp_Explorer(s, TopAbs_FACE)
    rows = []
    while ex.More():
        f = topods.Face(ex.Current())
        a = BRepAdaptor_Surface(f, True)
        if a.GetType() == GeomAbs_Plane:
            pl = a.Plane()
            d = pl.Axis().Direction()
            if abs(abs(d.X() * nx + d.Z() * nz) - 1) < 1e-6 and abs(d.Y()) < 1e-6:
                o = pl.Location()
                dist = (o.X() - ax) * nx + (o.Z() - az) * nz
                b = Bnd_Box()
                brepbndlib.AddOptimal(f, b, False, False)
                bb = b.Get()
                p = GProp_GProps()
                brepgprop.SurfaceProperties(f, p)
                # in-plane extent perpendicular to Y: project bbox corners on tangent (-nz, nx)
                tx, tz = -nz, nx
                ts = [(x - ax) * tx + (z - az) * tz for x in (bb[0], bb[3]) for z in (bb[2], bb[5])]
                rows.append((round(dist, 2), round(p.Mass(), 1), round(bb[1], 1), round(bb[4], 1),
                             round(min(ts), 1), round(max(ts), 1)))
        ex.Next()
    print(leg, "planes normal to the bolt axis: dist_from_axis_mm, area_mm2, y_min, y_max, t_min, t_max")
    for r in sorted(set(rows)):
        print("  ", r)
