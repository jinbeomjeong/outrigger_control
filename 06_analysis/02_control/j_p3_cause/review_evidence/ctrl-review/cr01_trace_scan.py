"""Scan rev 5 per-read J-P3 arrays of the case replays (read only).

Usage: python -I -B cr01_trace_scan.py <out.json> <npz> [<npz> ...]

Per file and leg: gap = used bound - p_tr per class (min, p10, median), hold/lock reads that
follow a ret or carry_ret run (the "lock after retraction" path), and the HOLD over-bound
(used - p_tr) distribution. Pressures in bar (gauge).
"""

import json
import sys
from pathlib import Path

import numpy as np

LEGS = ("FL", "FR", "RL", "RR")


def scan(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as data:
        names = [str(n) for n in data["jp3_class_names"]]
        cls = data["jp3_class"]
        state = data["jp3_plant_state"]
        state_names = ([str(n) for n in data["jp3_plant_state_names"]]
                       if "jp3_plant_state_names" in data.files else None)
        t = data["jp3_t_s"]
        used = data["jp3_used_bound_Pa"] / 1e5
        p_tr = data["jp3_p_tr_Pa"] / 1e5
        u = data["jp3_u_m_s"] * 1e3
        gate = data["jp3_gate_open"]
        keys = sorted(data.files)
    out = {"file": path.name, "class_names": names, "plant_state_names": state_names,
           "n_reads": int(t.size), "legs": {}}
    for leg in range(4):
        c = cls[:, leg]
        gap = used[:, leg] - p_tr[:, leg]
        per_class = {}
        for k, name in enumerate(names):
            sel = (c == k) & np.isfinite(gap)
            if not sel.any():
                continue
            g = gap[sel]
            j = int(np.flatnonzero(sel)[np.argmin(g)])
            per_class[name] = {"reads": int(sel.sum()), "min_gap_bar": float(g.min()),
                               "min_gap_t_s": float(t[j]), "p10_gap_bar": float(np.percentile(g, 10)),
                               "median_gap_bar": float(np.median(g)),
                               "max_gap_bar": float(g.max())}
        # lock / hold reads whose previous non-lock/hold class was ret or carry_ret
        after_ret = []
        last_moving = None
        last_gate = False
        for r in range(t.size):
            name = names[c[r]]
            if name in ("lock", "hold"):
                if last_moving in ("ret", "carry_ret"):
                    after_ret.append({"t_s": float(t[r]), "class": name,
                                      "prev": last_moving, "prev_gate_open": bool(last_gate),
                                      "gap_bar": float(gap[r]), "p_tr_bar": float(p_tr[r, leg]),
                                      "used_bar": float(used[r, leg]),
                                      "plant_state": int(state[r, leg])})
            else:
                last_moving = name
                last_gate = bool(gate[r, leg])
        after_ret.sort(key=lambda row: row["gap_bar"])
        out["legs"][LEGS[leg]] = {"per_class": per_class,
                                  "lock_hold_after_ret_reads": len(after_ret),
                                  "lock_hold_after_ret_worst5": after_ret[:5]}
    out["keys"] = keys
    return out


def main() -> None:
    out_path = Path(sys.argv[1])
    rows = [scan(Path(p)) for p in sys.argv[2:]]
    out_path.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    for row in rows:
        print(row["file"])
        for leg, info in row["legs"].items():
            pc = info["per_class"]
            text = " ".join(f"{k}:{v['reads']}/{v['min_gap_bar']:.1f}@{v['min_gap_t_s']:.1f}/"
                            f"med{v['median_gap_bar']:.0f}" for k, v in pc.items())
            worst = info["lock_hold_after_ret_worst5"][:1]
            print(f"  {leg} {text} | after_ret {info['lock_hold_after_ret_reads']} "
                  f"worst {worst}")


if __name__ == "__main__":
    main()
