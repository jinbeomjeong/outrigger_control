"""G1 regression detail: 1 ms pads.npz comparison of two S6 batches (spec rev. 29, section 121).

Moved from a one-off scratchpad script (g1diff.py, 2026-10-24) so that the numbers quoted in
`00_docs/04_control/s6_control_spec.md` section 121 have a reproducible source.

The whole-array comparison is `06_analysis/01_chrono/16_S6/verify_S6_L1_regression_fix110.json`
(first differing index, max abs diff). This script adds the event detail around the first
difference: first-contact and separation times of the leg, cylinder force at separation,
and the max difference over the last 5 s.

Units: time s (absolute simulation time), force kN (cylinder net force, + = compression).

Usage (dynamics-dev):
    conda run -n dynamics-dev python -I 04_scripts/03_control/s6_g1_regression_detail.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "07_results" / "S6"
OUT_DEFAULT = ROOT / "06_analysis" / "01_chrono" / "16_S6" / "verify_S6_L1_regression_fix110_G1_detail.json"
LEGS = ("FL", "FR", "RL", "RR")


def first_true(mask: np.ndarray) -> int | None:
    idx = np.flatnonzero(mask)
    return int(idx[0]) if idx.size else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--old-batch", default="stage2_L1R_20261022_102159")
    ap.add_argument("--new-batch", default="stage2_L1R_20261022_142037")
    ap.add_argument("--case", default="G1_top_flat")
    ap.add_argument("--tail-s", type=float, default=5.0)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    a = np.load(RESULTS / args.old_batch / args.case / "pads.npz")
    b = np.load(RESULTS / args.new_batch / args.case / "pads.npz")
    t = b["t"]
    n = min(len(t), len(a["t"]))
    t = t[:n]
    if not np.array_equal(t, a["t"][:n]):
        raise SystemExit("time bases differ between batches")
    fa, fb = a["F_cyl"][:n], b["F_cyl"][:n]
    na, nb = a["N"][:n], b["N"][:n]
    d = np.abs(fa - fb)

    diff_idx = np.argwhere(d > 0)
    if diff_idx.size == 0:
        result = {"identical": True}
    else:
        i0, leg0 = int(diff_idx[0][0]), int(diff_idx[0][1])
        imax, legmax = np.unravel_index(int(d.argmax()), d.shape)
        dt = float(np.median(np.diff(t)))
        n_tail = int(round(args.tail_s / dt))

        # First contact (N > 0) and first separation (N <= 0 after contact) of the first-diff leg.
        c0 = first_true(nb[:, leg0] > 0)
        sep_new = sep_old = None
        if c0 is not None:
            s = first_true(nb[c0:, leg0] <= 0)
            sep_new = None if s is None else c0 + s
            s = first_true(na[c0:, leg0] <= 0)
            sep_old = None if s is None else c0 + s

        def window(f: np.ndarray, k: int | None) -> list[float] | None:
            if k is None:
                return None
            w = f[max(k - 2, 0): k + 3, leg0] / 1e3
            return [float(w.min()), float(w.max())]

        result = {
            "identical": False,
            "sample_dt_s": dt,
            "first_diff": {"index": i0, "t_s": float(t[i0]), "leg": LEGS[leg0]},
            "max_abs_diff_kN": float(d.max() / 1e3),
            "max_abs_diff_at": {"index": int(imax), "t_s": float(t[imax]), "leg": LEGS[int(legmax)]},
            "tail_max_abs_diff_kN": float(d[-n_tail:].max() / 1e3),
            "tail_s": args.tail_s,
            "first_contact_t_s": {LEGS[k]: (None if (c := first_true(nb[:, k] > 0)) is None else float(t[c]))
                                  for k in range(4)},
            "first_diff_leg_separation": {
                "new_t_s": None if sep_new is None else float(t[sep_new]),
                "old_t_s": None if sep_old is None else float(t[sep_old]),
                "F_cyl_new_kN_range_pm2ms": window(fb, sep_new),
                "F_cyl_old_kN_range_pm2ms": window(fa, sep_old),
            },
        }

    out = {
        "generated_by": "04_scripts/03_control/s6_g1_regression_detail.py",
        "old_batch": args.old_batch,
        "new_batch": args.new_batch,
        "case": args.case,
        "units": {"t": "s (absolute)", "force": "kN, cylinder net force, + = compression"},
        "whole_array_comparison": "06_analysis/01_chrono/16_S6/verify_S6_L1_regression_fix110.json",
        "result": result,
    }
    args.out.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out["result"], indent=1))


if __name__ == "__main__":
    main()
