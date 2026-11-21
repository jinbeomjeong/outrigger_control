"""Summarise vbk_gate_sim.json: floor false rejection and MDE80 per (m, k)."""
import json
import sys
from pathlib import Path

import numpy as np

j = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
R = j["rows"]
DS = [0.0, 0.0025, 0.005, 0.01, 0.02, 0.03]


def get(**kw):
    out = [r for r in R if all(r[a] == b for a, b in kw.items())]
    assert len(out) == 1, kw
    return out[0]


def mde80(m, k, c, f, g, conc, dm):
    ys = []
    for d in DS:
        r = get(m=m, k=k, c=c, f=f, g=g, conc=conc, delta=d, dmodel=("D1" if d == 0.0 else dm))
        ys.append(r["p_pass"])
    ys = np.array(ys)
    if ys[0] <= 0.2:
        return 0.0
    if ys.min() > 0.2:
        return None
    i = int(np.argmax(ys <= 0.2))
    y0, y1 = max(ys[i - 1], 1e-9), max(ys[i], 1e-9)
    t = (np.log(0.2) - np.log(y0)) / (np.log(y1) - np.log(y0))
    return DS[i - 1] + t * (DS[i] - DS[i - 1])


L = [f"reps {j['reps']} seed {j['seed']} cases {j['n_case']}", "checks " + json.dumps(j["checks"]), ""]
for conc in (False, True):
    for g in (0.0, 0.0036):
        L += [f"## floor false rejection 1-P(pass | delta 0), conc={conc}, g={g}",
              "| m | N | k | " + " | ".join(f"c{c}/f{f*100:g}%" for c in (0.3, 0.5, 0.8) for f in (0.001, 0.0035, 0.01)) + " |",
              "|---" * 12 + "|"]
        for m in (1, 2, 3, 4, 6, 8):
            for k in (0, 1, 2, 3):
                cells = [f"{1 - get(m=m, k=k, c=c, f=f, g=g, conc=conc, delta=0.0, dmodel='D1')['p_pass']:.3f}"
                         for c in (0.3, 0.5, 0.8) for f in (0.001, 0.0035, 0.01)]
                L.append(f"| {m} | {m*167} | {k} | " + " | ".join(cells) + " |")
        L.append("")
L += ["## MDE80 (delta per pair at which P(pass) <= 0.2); floor c0.5 f0.35% conc, g as column",
      "| m | N | k | D1 g0 | D2 g0 | D1 g0.36% | D2 g0.36% | P(pass) d=1% D1 g0 | P(pass) d=2% D1 g0 | floor rej c0.5 f0.35% conc g0 | c0.8 f1% conc g0.36% |",
      "|---" * 11 + "|"]
for m in (1, 2, 3, 4, 6, 8):
    for k in (0, 1, 2, 3):
        md = []
        for g in (0.0, 0.0036):
            for dm in ("D1", "D2"):
                v = mde80(m, k, 0.5, 0.0035, g, True, dm)
                md.append("-" if v is None else f"{v*100:.2f}%")
        p1 = get(m=m, k=k, c=0.5, f=0.0035, g=0.0, conc=True, delta=0.01, dmodel="D1")["p_pass"]
        p2 = get(m=m, k=k, c=0.5, f=0.0035, g=0.0, conc=True, delta=0.02, dmodel="D1")["p_pass"]
        fr = 1 - get(m=m, k=k, c=0.5, f=0.0035, g=0.0, conc=True, delta=0.0, dmodel="D1")["p_pass"]
        fr2 = 1 - get(m=m, k=k, c=0.8, f=0.01, g=0.0036, conc=True, delta=0.0, dmodel="D1")["p_pass"]
        L.append(f"| {m} | {m*167} | {k} | " + " | ".join(md) + f" | {p1:.3f} | {p2:.3f} | {fr:.3f} | {fr2:.3f} |")
Path(sys.argv[2]).write_text("\n".join(L), encoding="utf-8")
print("ok")
