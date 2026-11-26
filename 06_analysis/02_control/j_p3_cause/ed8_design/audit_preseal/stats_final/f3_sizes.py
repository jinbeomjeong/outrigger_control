"""Ed. 8 S8-R final review, part 3: expected G' stratum-E size under the two readings of spec 6.3.

Reading I (stated intent, user decision 4): E-eligible events = RE1bF (incl. Y8-9 depth/ramp variants); FS24 -> N.
Reading F (literal `fast`): `fast` = depth/ramp > v_max (r67_g1_screen.py:120-121) is True for RE1bF AND FS24
          (stored grid: fast True 256/256 FS24 runs), so FS24 units with an early diagonal start are E.
Model and phase probabilities are those of stats_s8r/s8r_sizes.py (same assumptions, seed 20261114):
  RE1bF E prob by phase: new {0.0125: 0.5, 0.0375: 0, 0.0625: 1, 0.0875: 1}, old {0: 15/16, 0.025: 0, 0.05: 4/16, 0.075: 1}
  FS24 (reading F only): old o0.05 -> 1 (stored V0 16/16), other old 0, new phases q_fs in {0, 0.125, 0.25}
  depth / F_s conditions shift the window: E probability x m_shift in {1.0, 0.7, 0.5}
Slots: (a) 4 clusters per E-candidate family (one new phase each), (b) RE1bF E families 4 clusters x one of
8 phases, (c) 3 new F_s per E-candidate family x one of 8 phases. E-candidate families: bottom-front
{level, ready} x {FL, FR} x {RE1bF, FS24}.
Also: census G1 V0-pass E count under each reading (from stats_s8r/s8r_frame.txt 100-118: 18 units, 8 FS24).
Usage: python -I -B f3_sizes.py <out_folder>
"""
import json
import sys
from pathlib import Path

import numpy as np

OUT = Path(sys.argv[1])
rng = np.random.default_rng(20261114)
REPS = 20000
NEW = [0.0125, 0.0375, 0.0625, 0.0875]
OLD = [0.0, 0.025, 0.05, 0.075]
ALL = NEW + OLD
P_RE = {0.0125: 0.5, 0.0375: 0.0, 0.0625: 1.0, 0.0875: 1.0, 0.0: 15 / 16, 0.025: 0.0, 0.05: 4 / 16, 0.075: 1.0}
P_FS_OLD = {0.0: 0.0, 0.025: 0.0, 0.05: 1.0, 0.075: 0.0}
N_MIN_E = 16


def draw(reading, q_fs, m_shift, reps):
    nE = np.zeros(reps, int)
    for rep in range(reps):
        c = 0
        for ev in ["RE1bF"] * 4 + ["FS24"] * 4:
            fs_on = reading == "F" and ev == "FS24"
            # (a) phase source, 4 clusters per family, new phases only
            for _ in range(4):
                phi = NEW[rng.integers(4)]
                p = P_RE[phi] if ev == "RE1bF" else (q_fs if fs_on else 0.0)
                c += rng.random() < p
            # (b) depth source: RE1bF families only
            if ev == "RE1bF":
                for _ in range(4):
                    phi = ALL[rng.integers(8)]
                    c += rng.random() < P_RE[phi] * m_shift
            # (c) F_s source: 3 new F_s per family
            for _ in range(3):
                phi = ALL[rng.integers(8)]
                if ev == "RE1bF":
                    p = P_RE[phi]
                elif fs_on:
                    p = q_fs if phi in NEW else P_FS_OLD[phi]
                else:
                    p = 0.0
                c += rng.random() < p * m_shift
        nE[rep] = c
    return nE


cases = []
txt = ["G' stratum-E size (assumption model of stats_s8r/s8r_sizes.py), n_min E = 16"]
for reading, qs in (("I", [0.0]), ("F", [0.0, 0.125, 0.25])):
    for q_fs in qs:
        for m_shift in (1.0, 0.7, 0.5):
            nE = draw(reading, q_fs, m_shift, REPS)
            p_lt = float((nE < N_MIN_E).mean())
            se = float(np.sqrt(p_lt * (1 - p_lt) / REPS))
            case = {"reading": reading, "q_fs": q_fs, "m_shift": m_shift, "nE_mean": float(nE.mean()),
                    "nE_p05": int(np.percentile(nE, 5)), "nE_p95": int(np.percentile(nE, 95)),
                    "P_nE_lt_16": p_lt, "mcse": se}
            cases.append(case)
            txt.append(f"reading {reading} q_fs {q_fs} m_shift {m_shift}: nE mean {case['nE_mean']:.1f} "
                       f"(5-95 % {case['nE_p05']}-{case['nE_p95']}), P(nE < 16) {p_lt:.4f} +- {se:.4f}")
census = {"I": {"E": 10, "N": 161}, "F": {"E": 18, "N": 153},
          "note": "G1 171 V0-pass units: 18 E under a 0.45 s diagonal rule, 8 of them FS24 (s8r_frame.txt 100-118)"}
txt.append(f"census G1 V0-pass E/N: reading I {census['I']}, reading F {census['F']}")
(OUT / "f3_sizes.json").write_text(json.dumps({"assumptions": __doc__, "seed": 20261114, "reps": REPS,
                                               "cases": cases, "census_g1": census}, indent=1), encoding="utf-8")
(OUT / "f3_sizes.txt").write_text("\n".join(txt), encoding="utf-8")
print(json.dumps({"status": "ok"}))
