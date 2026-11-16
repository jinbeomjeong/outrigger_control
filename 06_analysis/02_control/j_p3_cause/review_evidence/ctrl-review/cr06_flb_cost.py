"""First-order Dg-3 cost indicator of the rev 5 bound in the case replays (read only).

Usage: python -I -B cr06_flb_cost.py <out.json> <npz> [<npz> ...]

For every lock / hold / carry read: the fallback lower force the bound would give,
F_lb = p_h,read A_h - used A_ann, against the true cylinder force F_true (T4h true_force_N).
over_kN = F_true - F_lb (= (used - p_tr) A_ann when the head reading is exact, P4 / ideal).
false_low = F_true >= F_min while F_lb < F_min (F_min 9.415 kN, YAML control.F_min_cylinder_N;
the controller's own margin above F_min is not applied here: ASSUMPTION, counts are a floor).
These runs have no fallback leg: the numbers say what a fallback leg would have seen.
"""

import json
import sys
from pathlib import Path

import numpy as np

LEGS = ("FL", "FR", "RL", "RR")
A_H = np.array([1.327e-2, 1.327e-2, 9.503e-3, 9.503e-3])
A_ANN = np.array([3.770e-3, 3.770e-3, 3.142e-3, 3.142e-3])
F_MIN_N = 9.415e3


def scan(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as d:
        names = [str(n) for n in d["jp3_class_names"]]
        tj = d["jp3_t_s"]
        t = d["t_s"]
        idx = np.clip(np.searchsorted(t, tj - 1e-6), 0, t.size - 1)
        head = d["head_pressure_Pa"][idx]
        f_true = d["true_force_N"][idx]
        used = d["jp3_used_bound_Pa"]
        cls = d["jp3_class"]
    out = {"file": path.name, "legs": {}}
    for leg in range(4):
        f_lb = head[:, leg] * A_H[leg] - used[:, leg] * A_ANN[leg]
        over = (f_true[:, leg] - f_lb) / 1e3
        row = {}
        for name in ("lock", "hold", "carry_ext", "carry_ret"):
            sel = (cls[:, leg] == names.index(name)) & np.isfinite(over)
            if not sel.any():
                continue
            o = over[sel]
            false_low = int(np.sum((f_true[sel, leg] >= F_MIN_N) & (f_lb[sel] < F_MIN_N)))
            row[name] = {"reads": int(sel.sum()), "over_p50_kN": float(np.percentile(o, 50)),
                         "over_p90_kN": float(np.percentile(o, 90)),
                         "over_max_kN": float(o.max()), "false_low_reads": false_low}
        out["legs"][LEGS[leg]] = row
    return out


def main() -> None:
    rows = [scan(Path(p)) for p in sys.argv[2:]]
    Path(sys.argv[1]).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    for row in rows:
        print(row["file"])
        for leg, info in row["legs"].items():
            text = " ".join(f"{k}:n{v['reads']} p50 {v['over_p50_kN']:.1f} p90 "
                            f"{v['over_p90_kN']:.1f} max {v['over_max_kN']:.1f} "
                            f"FL<{v['false_low_reads']}" for k, v in info.items())
            print(f"  {leg} {text}")


if __name__ == "__main__":
    main()
