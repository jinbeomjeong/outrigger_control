"""Rev. 51: U / L event count of the main ML batch (203.1 definition: 10 Hz windows, 1 ms
minimum of the true cylinder force F_cyl_min_interval < F_min = U-or-L, airborne in the window =
L), per episode kind, masked tail after a FAULT excluded. Expected test-share size for E1.

Usage: python -I s8main_events.py <batch_dir> <out_json>
Reads pads.npz members 't' (only its length / spacing check is not needed), 'sample_s',
'F_cyl_min_interval' and 'airborne' is not read (1 ms); L is taken from record 'pad_in_contact'
== 0 at any 10 Hz sample of the window (approximation, flagged as such).
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
F_MIN = 9414.59
batch = Path(sys.argv[1])
out = Path(sys.argv[2])
v = json.loads((batch / "verify_S8ML.json").read_text(encoding="utf-8"))
masks = v.get("ml_masks", {})
rows = []
for case in sorted((batch / "episodes").iterdir()):
    if not case.is_dir() or case.name.startswith("_"):
        continue
    cj = json.loads((case / "case.json").read_text(encoding="utf-8"))
    ep = cj["settings"]["episode"]
    res = json.loads((case / "result.json").read_text(encoding="utf-8"))
    t_ev = float(res.get("event_t_s") or res.get("branch_t_s"))
    with np.load(case / "pads.npz", allow_pickle=True) as p:
        fmin1 = p["F_cyl_min_interval"]
        air1 = p["airborne"].astype(bool)
        tp = p["t"]
    rec = np.load(case / "record" / "record.npz", allow_pickle=True)
    t10 = rec["t"]
    # 10 Hz window (t_{k-1}, t_k]: 1 ms minimum (203.1) and any airborne sample
    hi = np.searchsorted(tp, t10 + 1e-9, side="right")
    lo = np.r_[0, hi[:-1]]
    fmin = np.full((len(t10), 4), np.inf)
    contact = np.ones((len(t10), 4))
    for k in range(len(t10)):
        if hi[k] > lo[k]:
            fmin[k] = fmin1[lo[k]:hi[k]].min(axis=0)
            contact[k] = ~air1[lo[k]:hi[k]].any(axis=0)
    keep = t10 >= t_ev - 1e-9
    mk = masks.get(case.name)
    if mk is not None:
        keep &= t10 < float(mk["start_engine_s"]) - 1e-9
    u = (fmin < F_MIN) & keep[:, None]
    lft = (contact < 0.5) & keep[:, None]
    # count events = rising edges of the per-leg U-or-L indicator
    ev_ul = int(sum(np.count_nonzero(np.diff(np.r_[0, u[:, L].astype(int)]) == 1) for L in range(4)))
    ev_l = int(sum(np.count_nonzero(np.diff(np.r_[0, lft[:, L].astype(int)]) == 1) for L in range(4)))
    rows.append({"case": case.name, "base": cj["settings"]["base"]["base_id"], "kind": ep.get("kind"),
                 "ul_events": ev_ul, "l_events": ev_l, "any_ul": ev_ul > 0, "any_l": ev_l > 0,
                 "samples_ul": int(u.sum()), "fmin_shape": list(fmin.shape)})
json.dump({"rows": rows}, open(out, "w", encoding="utf-8"), indent=1)
by = defaultdict(Counter)
for r in rows:
    by[r["kind"]]["episodes"] += 1
    by[r["kind"]]["ep_with_UL"] += r["any_ul"]
    by[r["kind"]]["ep_with_L"] += r["any_l"]
    by[r["kind"]]["UL_events"] += r["ul_events"]
    by[r["kind"]]["L_events"] += r["l_events"]
for k, c in by.items():
    print(k, dict(c))
tot_ep = sum(r["any_ul"] for r in rows)
tot_ev = sum(r["ul_events"] for r in rows)
print(f"episodes with U-or-L {tot_ep} of {len(rows)}; U-or-L events {tot_ev}; L events {sum(r['l_events'] for r in rows)}")
for share in (0.15,):
    n_ep = tot_ep * share
    print(f"test share {share:.0%}: ~{n_ep:.0f} event episodes, ~{tot_ev*share:.0f} events; zero-miss 95 % upper bound per episode {1-0.05**(1/n_ep):.3f}, per event {1-0.05**(1/(tot_ev*share)):.3f}")
print("fmin shape example", rows[0]["fmin_shape"])
