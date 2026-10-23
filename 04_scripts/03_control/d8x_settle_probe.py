"""Settled attitude on the crawler in the reduced 6-DoF plant vs the Chrono S6 stage-2 snapshots (Q12 bushing).

Reduced plant: run_control_comparison.Plant (layout D crawler, tangential stiffness per point = kn by default).
Variant 'kt0.40': crawler tangential stiffness per point = 0.402 x kn (Chrono Q12 basis kt/kn of the pads).
Settle 65.5 s with u = 0 (same as run_case). Prints settled roll/pitch [deg].
Run: conda run -n dynamics-dev python -I d8x_settle_probe.py <project_root> <out_json>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import run_control_comparison as rcc  # noqa: E402

FLOORS = [("flat", 0.0, 0.0), ("fdown3.5", 0.0, 3.5), ("fup3.5", 0.0, -3.5), ("roll5.5", 5.5, 0.0),
          ("diag3", 3 / math.sqrt(2), 3 / math.sqrt(2))]


def settle(level, roll, pitch, kt_ratio):
    pl = rcc.Plant(level, roll, pitch)
    if kt_ratio is not None:
        pl.ktcr = pl.kcr * kt_ratio
    pl.step([0, 0, 0, 0], int(round(rcc.SETTLE_ON_CRAWLER_S / pl.dt)))
    ph, th = pl.attitude()
    return math.degrees(ph), math.degrees(th)


def main():
    out = []
    for level in ("top", "bottom"):
        for name, r, p in FLOORS:
            for var, ktr in (("default", None), ("kt0.40", 0.402)):
                ph, th = settle(level, r, p, ktr)
                rec = dict(level=level, floor=name, floor_deg=[r, p], variant=var, att_deg=[ph, th],
                           rel_deg=[ph - r, th - p])
                print(rec, flush=True)
                out.append(rec)
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
