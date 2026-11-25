"""Ed. 7 empirical anchors from public ed. 6 record-only tables (judged, design inputs O7-1/O7-2).
stats-design-expert, 2026-11-24.

Inputs (ed6_design/ed6_confirm_stop_79495405/, public analysis outputs of judged ed. 6 runs):
  rb_b5_records_B.csv  - j9_main 388 + sens 184 lines: longest A(i) blind-band dwell per line
                         (locked leg, 0 < |u| <= u_hold, any LEVEL segment, sign NOT checked)
  cf_f3_blind_band.csv - counterfactual 60 lines: longest post-event blind-band dwell
Outputs (argv[1]): s40_records_empirical.json / .txt
  (1) share of lines whose longest dwell would reach N cycles, for N in 10..60 (A_ib opportunity
      under the ed. 6 controller; an upper-bound proxy, see notes)
  (2) gap between 'short' and 'tail' dwell groups in the counterfactual
  (3) offset concordance of long dwell (>= 6.3 s) / no-READY for row pairs o0.0 vs o0.05
stdout: status only.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

SRC = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design"
           r"\ed6_confirm_stop_79495405")
NS = (10, 15, 20, 21, 22, 25, 30, 40, 50, 60)
TAIL_S = 6.3


def main() -> int:
    out_dir = Path(sys.argv[1])
    rb = list(csv.DictReader((SRC / "rb_b5_records_B.csv").open(encoding="utf-8")))
    cf = list(csv.DictReader((SRC / "cf_f3_blind_band.csv").open(encoding="utf-8")))
    res = {"n_rb": len(rb), "n_cf": len(cf)}
    groups = defaultdict(list)
    for r in rb:
        g = "VBL" if r["setting"] == "VBL" else ("LSL" if r["setting"].startswith("LSL") else "sens")
        groups[g].append(float(r["band_longest_s"]))
        groups["all572"].append(float(r["band_longest_s"]))
    for r in cf:
        groups["cf60"].append(float(r["blind_band_longest_s"]))
    reach = {}
    for g, v in groups.items():
        a = np.round(np.array(v) / 0.1).astype(int)          # cycles
        reach[g] = {"n": int(a.size), **{f"ge{n}": int((a >= n).sum()) for n in NS},
                    "between_N_and_tail": {str(n): int(((a >= n) & (a < round(TAIL_S / 0.1))).sum())
                                           for n in NS if n < round(TAIL_S / 0.1)}}
    res["reach_by_group"] = reach
    # histogram of dwell (s) for the 572 records-B lines, 0.5 s bins up to 10 s
    a = np.array(groups["all572"])
    edges = [0, 0.05, 1, 2, 2.2, 3, 4, 5, 6.3, 10, 20, 100]
    res["hist572_edges_s"] = edges
    res["hist572"] = np.histogram(a, bins=edges)[0].tolist()
    # counterfactual: short vs tail groups
    cfv = np.array(groups["cf60"])
    res["cf_short_max_s"] = float(cfv[cfv < 5].max())
    res["cf_tail_min_s"] = float(cfv[cfv >= 5].min())
    # offset concordance o0.0 vs o0.05 (same setting, same row) - records B and counterfactual
    pairs = defaultdict(dict)
    for r in rb:
        m = re.match(r"^(.*) o(0\.0|0\.05)$", r["key"])
        if m:
            tail = float(r["band_longest_s"]) >= TAIL_S
            nr = r["final"] != "ready"
            pairs[(r["file"], r["setting"], m.group(1))][m.group(2)] = (tail, nr)
    for r in cf:
        m = re.match(r"^(R12_top-..-Fs0)-o(0\.0|0\.05)_(P6-.*)$", r["file"])
        if m:
            tail = float(r["blind_band_longest_s"]) >= TAIL_S
            nr = r["end_phase"] != "ready"
            pairs[("cf", m.group(3), m.group(1))][m.group(2)] = (tail, nr)
    tab = {"tail": [0, 0, 0, 0], "noready": [0, 0, 0, 0]}   # (both, only0, only05, neither)
    for d in pairs.values():
        if "0.0" in d and "0.05" in d:
            for j, name in enumerate(("tail", "noready")):
                x, y = d["0.0"][j], d["0.05"][j]
                tab[name][0 if (x and y) else 1 if x else 2 if y else 3] += 1
    conc = {}
    for name, (b, o1, o2, nn) in tab.items():
        n = b + o1 + o2 + nn
        p1, p2 = (b + o1) / n, (b + o2) / n
        phi_den = np.sqrt(p1 * (1 - p1) * p2 * (1 - p2))
        phi = ((b / n) - p1 * p2) / phi_den if phi_den > 0 else float("nan")
        conc[name] = {"both": b, "only_o0.0": o1, "only_o0.05": o2, "neither": nn, "n_pairs": n,
                      "P(other|one)": (2 * b) / (2 * b + o1 + o2) if (2 * b + o1 + o2) else None,
                      "phi": float(phi)}
    res["offset_concordance"] = conc
    (out_dir / "s40_records_empirical.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    L = [f"lines rb {res['n_rb']} cf {res['n_cf']}"]
    for g, v in reach.items():
        L.append(f"{g:7s} n {v['n']:3d} " + " ".join(f"N{n}:{v[f'ge{n}']}" for n in NS)
                 + "  | fire-but-<6.3s " + json.dumps(v["between_N_and_tail"]))
    L.append(f"hist572 edges {edges} counts {res['hist572']}")
    L.append(f"cf short max {res['cf_short_max_s']} s, tail min {res['cf_tail_min_s']} s")
    L.append("offset concordance " + json.dumps(conc))
    (out_dir / "s40_records_empirical.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    ok = len(rb) == 572 and len(cf) == 60
    print("ok" if ok else "input_mismatch")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
