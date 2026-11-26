"""Diagnosis case 2: R15 o0.05, V0 / A / H3 - the r67 twist-work recurrence gate.

r67_g1_screen.twist_work (C 8a2a52ce 04_scripts/03_control/s8/r67_g1_screen.py 284-306):
S = (F_FL + F_RR) - (F_FR + F_RL) (1 ms true cylinder force), S_0 = median over [-0.5, 0) s,
P = 1/2 (S - S_0) (n . valve) with n = N_TWIST, 0.5 s bins from the event to 8 s, judged bins
start >= 1.5 s, bundle = consecutive judged bins > +20 J, gate recurrence = bundles <= 1.

Recomputes the bins from the stored 1 ms rows (check against the judge dict), splits each judged
bin > 0 J into 0.1 s sub-bins, and lists the re-approach runs (start, end, leg, retrigger flag,
H-3 extension) next to them.

Usage: conda run -n dynamics-dev python -I -B diag_case2.py
Output: diag_case2_out.txt
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed7-impl")
sys.path.insert(0, str(WT / "04_scripts" / "03_control" / "s8"))
STEMS = {"V0": "R15_o0.05_V0", "A": "R15_o0.05_P89-A-VBM", "H3": "R15_o0.05_P89-H3-VBM"}
recs = {json.loads(x)["diag"]["stem"]: json.loads(x)
        for x in (RAW / "runs.jsonl").read_text("utf-8").splitlines()}
src = (WT / "04_scripts" / "03_control" / "s8" / "r67_g1_screen.py").read_text("utf-8")
line = [x for x in src.splitlines() if x.startswith("N_TWIST")]
out = [f"N_TWIST source line: {line}"]
N_TWIST = None
for x in line:
    try:
        N_TWIST = np.array(eval(x.split("=", 1)[1], {"np": np}), float)  # noqa: S307
    except Exception as exc:  # record
        out.append(f"N_TWIST eval failed: {exc!r}")
for arm, stem in STEMS.items():
    r = recs[stem]
    te = float(r["t_event_s"])
    z = np.load(RAW / "logs" / f"{stem}_rows.npz")
    rows = z["rows"]
    j = json.loads((RAW / "logs" / f"{stem}_judge.json").read_text("utf-8"))
    t = rows[:, 0] - te
    F, valve = rows[:, 5:9], rows[:, 9:13]
    S = (F[:, 0] + F[:, 3]) - (F[:, 1] + F[:, 2])
    m0 = (t >= -0.5) & (t < 0)
    S0 = float(np.median(S[m0]))
    P = 0.5 * (S - S0) * (valve @ N_TWIST)
    bins = [round(float(P[(t >= lo) & (t < lo + 0.5)].sum() * 1e-3), 1) for lo in np.arange(0, 8, 0.5)]
    out.append(f"===== {arm} t_event {te}  judge bins {j['twist']['bins_J']}")
    out.append(f"  recomputed bins equal: {bins == j['twist']['bins_J']}  bundles {j['twist']['bundles']}")
    for k, b in enumerate(bins[3:]):
        lo = 1.5 + 0.5 * k
        if b > 0:
            sub = [round(float(P[(t >= s) & (t < s + 0.1)].sum() * 1e-3), 1)
                   for s in np.arange(lo, lo + 0.5 - 1e-9, 0.1)]
            mid = (t >= lo) & (t < lo + 0.5)
            out.append(f"  bin {lo:.1f} {b:+.1f} J  sub 0.1 s {sub}  mean S-S0 {np.mean(S[mid]-S0)/1e3:+.2f} kN"
                       f"  mean n.valve {np.mean(valve[mid] @ N_TWIST)*1e3:+.4f} mm/s")
    p = json.loads((RAW / "logs" / f"{stem}_p89.json").read_text("utf-8"))
    ends = {(round(e["start_s"] - te, 3), e["leg"]): e for e in p["ends"] if e["start_s"] is not None}
    runs = []
    for s in p["starts"]:
        if s["t"] < te - 1e-9:
            continue
        e = ends.get((round(s["t"] - te, 3), s["leg"]))
        runs.append((round(s["t"] - te, 3), None if e is None else round(e["t"] - te, 3), s["leg"],
                     "retrig" if s["retrigger"] else "first",
                     None if e is None else e["outcome"]))
    out.append(f"  runs (start, end, leg, retrigger, outcome): {runs}")
    out.append(f"  H-3 extensions (t, leg): {[(round(h['t'] - te, 3), h['leg']) for h in p['h3']]}")
    eo = r["event_output"]
    out.append(f"  gates failed {[g for g, ok in eo['gates'].items() if not ok]}  sign_changes {eo['sign_changes']}"
               f"  n_late {eo['n_late_starts']}  lifts {json.dumps(eo['lifts'])}")
text = "\n".join(out)
(HERE / "diag_case2_out.txt").write_text(text, "utf-8")
print(text.encode("ascii", "replace").decode())
