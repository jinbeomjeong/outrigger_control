"""S9 C2 soil response (spec rev. 57): case sets of the reduced closed loop (s9_soil_closed_loop.py).

Sets (argv[1]):
  rigid    rigid-floor regression: 13 floor slopes x 3 auger levels x F_s {0, 4, 8} kN at beta 1.0 GPa, plus
           beta {0.69, 1.6} GPa on 3 slopes x 3 levels at F_s 4 kN; project C2 ("base") and soil rule ("loc").
           Pass: command SHA-256 equal per case (bit identical), else the judged metrics equal.
  soil     4 soil sets x pad A / B x 3 levels x F_s {0, 4, 8} kN, base and loc.
  sensor   soil set with the force-reading error model (calibrated "normal" grade, 3 seeds) at F_s 4 kN, loc only.
  beta     soil set at beta {0.69, 1.6} GPa, top, F_s 4 kN, loc only.
  sweep    LOC parameter sensitivity on the soil top cases (F_s 4 kN).
Output: 06_analysis/02_control/s9/<set>[_tag].json. Run: conda run -n dynamics-dev python -I s9_runs.py <set> [workers]
Seeds: sensor errors np.random.default_rng(20261025 + 1000 * seed + case index) (recorded per case).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s9_soil_closed_loop as h  # noqa: E402

OUT_DIR = h.ROOT / "06_analysis" / "02_control" / "s9"
SLOPES = [(0.0, 0.0), (4.4, 0.0), (-4.4, 0.0), (0.0, 3.2), (0.0, -3.2), (2.2, 1.6), (-2.2, 1.6), (2.2, -1.6),
          (-2.2, -1.6), (2.7355, 1.7592), (5.5, 0.0), (0.0, 3.5), (0.0, -3.5)]
LEVELS = ("top", "middle", "bottom")
SOILS = ("G1", "J1", "J2", "S1")
RULE = json.loads(os.environ.get("S9_RULE", "{}"))


def _variant(name):
    return {} if name == "base" else {"rule": RULE}


def rigid_cases():
    cs = []
    for v in ("base", "loc"):
        for sl in SLOPES:
            for lv in LEVELS:
                for fs in (0.0, 4.0, 8.0):
                    cs.append({"id": f"{v}|rigid|{sl[0]:g},{sl[1]:g}|{lv}|Fs{fs:g}|b1", "soil": "rigid", "pad": "B",
                               "level": lv, "fs_kN": fs, "slope": sl, "variant": _variant(v)})
        for sl in ((0.0, 0.0), (4.4, 0.0), (0.0, 3.2)):
            for lv in LEVELS:
                for b in (0.69e9, 1.6e9):
                    cs.append({"id": f"{v}|rigid|{sl[0]:g},{sl[1]:g}|{lv}|Fs4|b{b / 1e9:g}", "soil": "rigid",
                               "pad": "B", "level": lv, "fs_kN": 4.0, "slope": sl, "beta": b, "variant": _variant(v)})
    return cs


def soil_cases(variants=("base", "loc"), fs_list=(0.0, 4.0, 8.0), levels=LEVELS, extra=None, tag=""):
    cs = []
    for v in variants:
        for s in SOILS:
            for p in ("A", "B"):
                for lv in levels:
                    for fs in fs_list:
                        c = {"id": f"{v}{tag}|{s}|{p}|{lv}|Fs{fs:g}", "soil": s, "pad": p, "level": lv, "fs_kN": fs,
                             "variant": _variant(v), "trace": lv == "top" and fs == fs_list[0]}
                        if extra:
                            c.update(extra)
                        cs.append(c)
    return cs


def sensor_cases():
    import numpy as np
    cs = []
    k = 0
    for seed in range(3):
        for c in soil_cases(("loc",), (4.0,), tag=f"_sens{seed}"):
            rng = np.random.default_rng(20261025 + 1000 * seed + k)
            k += 1
            c["sensor"] = {"span": rng.uniform(-0.01, 0.01, 4).tolist(), "offset_N": rng.uniform(-500, 500, 4).tolist(),
                           "noise_N": 300.0, "seed": int(20261025 + 1000 * seed + k)}
            c["trace"] = False
            cs.append(c)
    return cs


def beta_cases():
    cs = []
    for b in (0.69e9, 1.6e9):
        cs += soil_cases(("loc",), (4.0,), ("top",), extra={"beta": b, "trace": False}, tag=f"_b{b / 1e9:g}")
    return cs


if __name__ == "__main__":
    which = sys.argv[1]
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    tag = os.environ.get("S9_OUT_TAG", "")
    cases = {"rigid": rigid_cases, "soil": soil_cases, "sensor": sensor_cases, "beta": beta_cases}[which]()
    flt = os.environ.get("S9_FILTER")
    if flt:
        cases = [c for c in cases if all(f in c["id"] for f in flt.split("&"))]
    out = OUT_DIR / f"{which}{tag}.json"
    r = h.run_batch(cases, out, workers, meta={"set": which, "rule": RULE, "n_cases": len(cases)})
    print("done", out, r["meta"]["wall_s"], "s", sum(1 for x in r["runs"] if "error" in x), "errors")
