"""Exact (bitwise) trajectory comparison of S6 stage-2 cases between batches.

For every listed case, compares all arrays of ``record/record.npz`` (20 ms
controller record) and ``pads.npz`` (1 ms pad record) of the new batch with the
same case of an old batch. Floats use exact equality (NaN == NaN); for differing
arrays the max abs difference, its index, the count and the first differing index
are reported, and the time of the first record difference is given.

Usage (Chrono-dev python, from any directory)::

    python -I 04_scripts/02_chrono/s6_regression_compare.py \
        --out <out.json> --new <new batch> \
        --compare <old batch> <case>[,<case>...] [--compare ...] \
        [--results-root <dir>] [--note "<text>"]

Batch arguments are directory paths; a bare name that is not an existing path
is resolved against ``--results-root`` (default ``<repo>/07_results/S6``).
The JSON stores batch directory names only, so output is location independent.

Example (spec 110.2 regression, rerun 142037 vs B2 123223 and G1 vs bundle B)::

    python -I 04_scripts/02_chrono/s6_regression_compare.py \
        --out 06_analysis/01_chrono/16_S6/verify_S6_L1_regression_fix110.json \
        --new stage2_L1R_20261022_142037 \
        --compare stage2_L1R_20261022_123223 G4_top_flat_settleRR_pressure,RE1bF_top_flat_dropRR30,PS2_RE1bF_conservative_nocal,PS4_RE1bF_FLp4_RRm4_nocal \
        --compare stage2_L1R_20261022_102159 G1_top_flat
"""
import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS = ROOT / "07_results" / "S6"
SCRIPT_REL = Path(__file__).resolve().relative_to(ROOT).as_posix()


def compare_npz(a_path, b_path):
    """Compare all arrays of two npz files; a = new, b = old."""
    a, b = np.load(a_path), np.load(b_path)
    out = {}
    keys = sorted(set(a.files) | set(b.files))
    for k in keys:
        if k not in a.files or k not in b.files:
            out[k] = {"status": "missing_in_" + ("new" if k not in a.files else "old")}
            continue
        x, y = a[k], b[k]
        if x.shape != y.shape:
            out[k] = {"status": "shape", "new": list(x.shape), "old": list(y.shape)}
            continue
        if x.dtype == bool or x.dtype.kind in "iu":
            nd = int(np.count_nonzero(x != y))
            out[k] = {"status": "identical" if nd == 0 else "differs", "n_diff": nd}
            continue
        if np.array_equal(x, y, equal_nan=True):
            out[k] = {"status": "identical"}
        else:
            d = np.abs(x - y)
            d = np.where(np.isnan(d), 0.0, d)
            idx = np.unravel_index(int(np.argmax(d)), d.shape)
            neq = ~((x == y) | (np.isnan(x) & np.isnan(y)))
            first = np.argwhere(neq)[0].tolist()
            out[k] = {"status": "differs", "max_abs": float(d.max()), "at": [int(i) for i in idx],
                      "n_diff": int(neq.sum()), "first_diff_index": first}
    return out


def resolve_batch(arg, results_root):
    p = Path(arg)
    if not p.is_dir():
        p = results_root / arg
    if not p.is_dir():
        raise SystemExit(f"batch directory not found: {arg}")
    return p.resolve()


def compare_case(new_batch, old_batch, case):
    n, o = new_batch / case, old_batch / case
    entry = {"old_batch": old_batch.name}
    for rel in ("record/record.npz", "pads.npz"):
        entry[rel] = compare_npz(n / rel, o / rel)
    rec = entry["record/record.npz"]
    t = np.load(n / "record/record.npz")["t"]
    firsts = [v["first_diff_index"][0] for v in rec.values()
              if v.get("status") == "differs" and "first_diff_index" in v]
    entry["record_first_diff_t_s"] = float(t[min(firsts)]) if firsts else None
    entry["record_all_identical"] = all(v.get("status") == "identical" for v in rec.values())
    entry["pads_all_identical"] = all(v.get("status") == "identical"
                                      for v in entry["pads.npz"].values())
    return entry


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, type=Path, help="output JSON path")
    ap.add_argument("--new", required=True, help="new batch directory (or name)")
    ap.add_argument("--compare", nargs=2, action="append", required=True,
                    metavar=("OLD_BATCH", "CASES"),
                    help="old batch directory (or name) and comma-separated case list")
    ap.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS,
                    help="directory for bare batch names (default: <repo>/07_results/S6)")
    ap.add_argument("--note", default=None, help="free-text note stored in the JSON")
    args = ap.parse_args(argv)

    new_batch = resolve_batch(args.new, args.results_root)
    res = {"new_batch": new_batch.name, "cases": {}}
    for old_arg, cases in args.compare:
        old_batch = resolve_batch(old_arg, args.results_root)
        for case in cases.split(","):
            entry = compare_case(new_batch, old_batch, case)
            res["cases"][f"{case}@{old_batch.name}"] = entry
            print(case, old_batch.name, "record identical:", entry["record_all_identical"],
                  "pads identical:", entry["pads_all_identical"],
                  "first diff t:", entry["record_first_diff_t_s"])
            for k, v in entry["record/record.npz"].items():
                if v.get("status") != "identical":
                    print("   ", k, v)
    if args.note:
        res["note"] = args.note
    res["generated_by"] = SCRIPT_REL
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
