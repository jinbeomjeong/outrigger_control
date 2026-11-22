"""436.9 edition 5 erratum 2 2-9.5: the T-CK and DROPOUT record bundles (spec v5 6.4) - seeds,
keys and rod fault plans, all before any run (a record; no judgement).

* cases: ranks 0 and 1 of the 12b cell table (the X-11 ``selection.json``, its sha256 given);
* seeds: T-CK 80, DROPOUT 81, each raised by 1 while a key of it is in the scan (the 12b scan:
  ``--scan-root`` 06_analysis and ``--scan-extra`` 05_tests) or the seed is taken (the 12b
  block seeds of the selection, the c dry seeds 90 / 91 and 92 / 93, the dry seed 25, the test seeds
  95 .. 99, the other bundle's seed); the repeat counts are recorded;
* one plan per bundle and leg (a plan holds one fault per key): both case keys with the fault
  on that leg, anchor ``phase_enter:CHECK``, ``delay_reads`` 0; T-CK STUCK -100 bar, DROPOUT
  ``kind`` DROPOUT (NaN);
* one key file per bundle (the two keys, LF).
A bundle is 2 cases x 4 legs x 2 arms (VBK0, VBK) = 16 lines (``step7b_ckdrop.ps1``).

Outputs in ``--out-dir`` (new or empty; never overwritten): ``tck_keys.txt``,
``dropout_keys.txt``, ``<bundle>_<leg>_plan.json`` (8), ``ckdrop_selection.json`` (inputs,
seeds and repeats, the cases, every output with its sha256).

Usage (python-dev or Chrono-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_ckdrop_plan.py --selection <x11>/selection.json
      --selection-sha256 <sha> --scan-root <repo>/06_analysis --scan-extra <worktree>/05_tests
      --out-dir <folder>
Exit 0 written, 2 not usable (another selection sha256, a used output folder, no free seed),
3 a tool error. The stdout's last line is JSON with ``status`` and the folder.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import jp3_12b_plan as plan  # noqa: E402

LEGS = ("FL", "FR", "RL", "RR")
CASE_RANKS = (0, 1)
BUNDLES = {"tck": {"seed": 80, "kind": "STUCK", "value_bar": -100.0},
           "dropout": {"seed": 81, "kind": "DROPOUT", "value_bar": None}}
"""2-9.5: the start seed and the fault of each bundle."""
ANCHOR = "phase_enter:CHECK"
TAKEN_SEEDS = frozenset({25, 90, 91, *plan.DRY_SEEDS, *range(95, 100)})
"""Dry 25, the ``ae9d0b2d`` c dry seeds 90 / 91 and the c dry seeds 92 / 93 (edition 5 erratum
6 6-3: added, :data:`jp3_12b_plan.DRY_SEEDS`), harness test keys 95 .. 99 (the 12b seeds come
from the selection)."""
SEED_LIMIT = 900
EXIT_WRITTEN, EXIT_NOT_USABLE, EXIT_ERROR = 0, 2, 3


def bundle_seed(start: int, cases: list[str], scanned: frozenset[str],
                taken: set[int]) -> tuple[int, int]:
    """(seed, repeats): ``start`` raised by 1 while taken or a case key of it is scanned.

    Raises:
        plan.NotUsable: No seed below :data:`SEED_LIMIT`.
    """
    seed, repeats = start, 0
    while seed in taken or any(plan.key_of(case, seed) in scanned for case in cases):
        seed += 1
        repeats += 1
        if seed > SEED_LIMIT:
            raise plan.NotUsable(f"no free seed from {start}")
    return seed, repeats


def fault(bundle: str, seed: int, rank: int, leg: str) -> dict:
    spec = BUNDLES[bundle]
    return {"fault_id": f"{bundle}-s{seed}-r{rank:03d}-{leg}", "leg": leg, "kind": spec["kind"],
            "value_bar": spec["value_bar"], "anchor": ANCHOR, "delay_reads": 0}


def select(selection_path: Path, selection_sha256: str, scan_root: Path,
           extra_roots: tuple[Path, ...], out_dir: Path) -> dict:
    """The outputs (module docstring); returns ``ckdrop_selection.json``.

    Raises:
        plan.NotUsable: Module docstring exit 2.
    """
    if hashlib.sha256(selection_path.read_bytes()).hexdigest() != selection_sha256:
        raise plan.NotUsable("--selection is not of the given sha256")
    if out_dir.exists() and any(out_dir.iterdir()):
        raise plan.NotUsable(f"--out-dir {out_dir} has files (never overwritten)")
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    table = {row["rank"]: row for row in selection["cell_table"]}
    cases = [table[rank]["case"] for rank in CASE_RANKS]
    scan = plan.merged_scan(scan_root, tuple(extra_roots))
    taken = set(TAKEN_SEEDS) | {block["seed_index"] for block in selection["blocks"].values()}
    seeds = {}
    for bundle, spec in BUNDLES.items():
        seed, repeats = bundle_seed(spec["seed"], cases, scan.keys, taken)
        seeds[bundle] = {"start": spec["seed"], "seed": seed, "repeats": repeats}
        taken.add(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for bundle in BUNDLES:
        seed = seeds[bundle]["seed"]
        keys = [plan.key_of(case, seed) for case in cases]
        outputs[f"{bundle}_keys.txt"] = plan._write_new(out_dir / f"{bundle}_keys.txt",
                                                        plan._keys_text(keys))
        for leg in LEGS:
            faults = {plan.CANDIDATE_PREFIX + key: fault(bundle, seed, rank, leg)
                      for key, rank in zip(keys, CASE_RANKS, strict=True)}
            name = f"{bundle}_{leg}_plan.json"
            outputs[name] = plan._write_new(out_dir / name, plan._json_text(
                {"schema": plan.PLAN_SCHEMA, "faults": faults}))
    document = {"rule": "jp3_remedy_spec_v5_erratum2.md 2-9.5 (spec v5 6.4, a record)",
                "inputs": {"selection": {"path": str(selection_path), "sha256": selection_sha256},
                           "scan_root": str(scan_root),
                           "scan_extra": [str(root) for root in extra_roots]},
                "scan": {"files_scanned": len(scan.files), "r79_keys": len(scan.keys),
                         "seed_max": scan.seed_max},
                "cases": [{"rank": rank, "case": table[rank]["case"]} for rank in CASE_RANKS],
                "taken_seeds": sorted(taken), "seeds": seeds, "legs": list(LEGS),
                "anchor": ANCHOR, "delay_reads": 0, "outputs": outputs,
                "lines_per_bundle": len(CASE_RANKS) * len(LEGS) * 2}
    plan._write_new(out_dir / "ckdrop_selection.json", plan._json_text(document))
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--selection-sha256", required=True)
    parser.add_argument("--scan-root", type=Path, required=True)
    parser.add_argument("--scan-extra", type=Path, action="append", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        document = select(args.selection, args.selection_sha256, args.scan_root,
                          tuple(args.scan_extra), args.out_dir)
    except plan.NotUsable as exc:
        print(f"not usable: {exc}", file=sys.stderr)
        print(json.dumps({"status": "not_usable", "out_dir": str(args.out_dir)}))
        return EXIT_NOT_USABLE
    except Exception as exc:  # noqa: BLE001 (every other failure is a tool error)
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(json.dumps({"status": "error", "out_dir": str(args.out_dir)}))
        return EXIT_ERROR
    print(json.dumps({"status": "written", "seeds": {b: s["seed"] for b, s in
                                                     document["seeds"].items()},
                      "out_dir": str(args.out_dir)}))
    return EXIT_WRITTEN


if __name__ == "__main__":
    sys.exit(main())
