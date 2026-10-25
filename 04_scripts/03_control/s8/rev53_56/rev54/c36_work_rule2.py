"""Candidate rule 'recurrence': twist work bins (rev. 52 definition, 0.5 s from the event) with the
forced-retraction window [event, done + 0.1 s] masked out; bins starting >= event + 1.5 s;
clusters = maximal runs of consecutive bins with W > L; pumping if >= 2 clusters.

Usage: python -I c36_work_rule2.py <affected_json> <case_dir_or_parent> [...]
"""
import json
import sys
from pathlib import Path

import numpy as np

N_TW = np.array([0.5, -0.5, -0.5, 0.5])
SPAN = 8.0
pp = {"ML78_ep0", "ML78_ep1", "ML78_ep3", "ML00_ep5", "ML21_ep1", "ML90_ep1"}
aff = set(json.loads(open(sys.argv[1], encoding="utf-8").read())["affected"])


def bins_for(case: Path):
    res = json.loads((case / "result.json").read_text(encoding="utf-8"))
    if res.get("event_t_s") is None:
        return None
    t_ev = float(res["event_t_s"])
    st = res.get("settings") or {}
    if (st.get("s8") or {}).get("event") is not None:  # run_S8C cases: event_t_s relative
        t_ev += float(st.get("start_t_s") or 0.0)
    ep = res.get("episode") or (res.get("event") or {}).get("spec") or st.get("episode") or {}
    pads = np.load(case / "pads.npz", allow_pickle=True)
    rec = np.load(case / "record" / "record.npz", allow_pickle=True)
    tp = np.asarray(pads["t"], float)
    m = (tp >= t_ev - 0.5) & (tp <= t_ev + SPAN + 1e-9)
    t = tp[m] - t_ev
    f = np.asarray(pads["F_cyl"], float)[m]
    d = (f[:, 0] + f[:, 3]) - (f[:, 1] + f[:, 2])
    d0 = float(np.median(d[t < 0]))
    tr = np.asarray(rec["t"], float) - t_ev
    u = (np.asarray(rec["u_applied"], float) @ N_TW)[
        np.clip(np.searchsorted(tr, t, side="right") - 1, 0, tr.size - 1)]
    p = 0.5 * (d - d0) * u
    fr = res.get("forced_retract") or {}
    done = None
    if ep.get("kind") == "retract":
        done = (float(fr["done_t_s"]) - t_ev) if fr.get("done_t_s") is not None else float(t[-1])
        p = np.where((t >= 0.0) & (t <= done + 0.1), 0.0, p)
    edges = np.arange(0.0, min(SPAN, float(t[-1])) - 1e-9, 0.5)
    b = [float(np.sum(p[(t >= a) & (t < a + 0.5)]) * 1e-3) for a in edges]
    return {"case": case.name, "kind": ep.get("kind"), "done": done, "bins": b}


def clusters(b, lim, a0=1.5):
    out, cur = [], None
    for i, w in enumerate(b):
        if 0.5 * i < a0 - 1e-9 or w <= lim:
            if cur:
                out.append(cur)
            cur = None
            continue
        cur = [0.5 * i, w] if cur is None else [cur[0], cur[1] + w]
    if cur:
        out.append(cur)
    return out


cases = []
for a in sys.argv[2:]:
    pa = Path(a)
    if (pa / "result.json").exists():
        cases.append(pa)
    else:
        cases.extend(sorted(q for q in pa.iterdir() if (q / "result.json").exists()))
rs = [r for r in (bins_for(c) for c in cases) if r]
for lim in (15.0, 20.0, 30.0, 40.0):
    hit = [(r["case"], [(c[0], round(c[1], 1)) for c in clusters(r["bins"], lim)])
           for r in rs if len(clusters(r["bins"], lim)) >= 2]
    single = sorted(((max(c[1] for c in clusters(r["bins"], lim)), r["case"]) for r in rs
                     if len(clusters(r["bins"], lim)) == 1), reverse=True)
    print(f"L {lim}: >=2 clusters {len(hit)} (aff {sum(h[0] in aff for h in hit)}, "
          f"pp {sum(h[0] in pp for h in hit)}): {hit}")
    print(f"     single-cluster runs {len(single)}, top: {[(round(v,1), c) for v, c in single[:8]]}")
print("retract masked runs:", sum(1 for r in rs if r["done"] is not None))
for r in rs:
    if r["case"] in ("ML36_ep1", "ML05_ep5", "ML94_ep4") or len(rs) < 5:
        print("  ", r["case"], r["kind"], r["done"], [round(x, 1) for x in r["bins"]])
