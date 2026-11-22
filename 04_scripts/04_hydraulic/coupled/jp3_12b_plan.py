"""436.9 edition 5 X-11 (``jp3_remedy_spec_v5.md`` 6.3.1, 6.3.10): T-JR-12b selection and plans.

From the fixed case source (``v5/resume_k1/h8_noise_VB.json``, sha256 of
``jp3_fixed_inputs.NOISE_VB_SHA256``) the 167 L2 cases in first-appearance order (rank 0 ..
166; case = the key without its seed token), the block seeds, the cell table and one rod fault
plan per block, all before any run:

* blocks b1 .. b4 = seed_index 40, 41, 42, 43 (user decision 2026-11-22 after the erratum 1
  audit E-1; b1 / b2 the base blocks, b3 the N top-up, b4 the witness top-up); a block is the
  167 cases with its seed.
* seed rule: the generated keys ``L2|s<seed>|<case rest>`` of every block must be absent from
  the scan (every r79 ``"key"`` value under ``--scan-root``, the whole ``06_analysis/`` with
  ``j9_runs`` and the dry outputs: nothing is left out, 4a-4 1; and every r79 key string
  literal of each ``--scan-extra`` root: the run worktree's ``05_tests/`` and probe records,
  E-1). Any collision raises all four seeds by 10, repeated until none; the record names the
  repeat count. Test and probe keys use seeds outside the judged set (``s9x``, not 90 / 91).
* cell = rank mod 8 of :data:`CELLS` (leg-major: FL tau_C, FL tau_R, FR tau_C, ... RR tau_R),
  the same for every block; b4 keeps the cell's leg with the phase TRw for all its pairs.
* anchors: tau_C ``phase_exit:CHECK``, tau_R ``retract_start_after:LEVEL``, TRw
  ``retract_witness_after:LEVEL``; STUCK -100 bar, ``delay_reads`` 0 (6.3.2).
* the c dry check (6.3.10): seeds 90 and 91, outside the judged set, 160 pairs = 20 per cell
  (seed 90: ranks 0 .. 79, seed 91: ranks 80 .. 159; the same cell table). A dry seed found in
  the scan stops (exit 2): the spec fixes those two seeds. One plan per dry seed (prelaunch
  audit B-1 (a)): a dry run takes one seed's key file, and the runner's X-10 guard needs the
  plan keys to be exactly the run's job keys.

One plan serves both arms of a block (VBK0 and VBK, ``R79_ROD_FAULT_PLAN``): the pair identity
(다) is the plan sha256 by construction. Per block a key file (one ``L2|s<seed>|...`` key per
line, LF) for ``r79_L3L4_final.py run --keys-file``.

Outputs in ``--out-dir`` (a new or empty folder; an existing file is never overwritten):
``b<j>_plan.json``, ``b<j>_keys.txt`` (j = 1 .. 4), ``c90_plan.json``, ``c90_keys.txt``,
``c91_plan.json``, ``c91_keys.txt``, ``selection.json`` (``dry.runs`` names each dry run's plan
and key file; inputs and their sha256, the scan evidence: files
scanned, per-file sha256 and key count, the largest seed; the seeds and repeat count, the cell
table, every output file with its sha256 and the run commands).

Usage (python-dev or Chrono-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_12b_plan.py --noise <h8_noise_VB.json>
      --scan-root <repo>/06_analysis --scan-extra <run worktree>/05_tests --out-dir <folder>

Exit codes (the stdout's last line is JSON with ``status`` and the output folder):

======  ================  ======================================================================
exit    status            meaning
======  ================  ======================================================================
0       ``written``       every output written
2       ``not_usable``    the case source is not the fixed file or has not 167 L2 cases, the
                          output folder has files, a dry seed is in the scan, or no seed without
                          a collision below the limit
3       ``error``         a tool error (unreadable file, broken JSON)
======  ================  ======================================================================
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import jp3_fixed_inputs as fixed  # noqa: E402

LEGS = ("FL", "FR", "RL", "RR")
PHASE_TAU_C, PHASE_TAU_R, PHASE_TRW = "tau_C", "tau_R", "TRw"
CELLS = tuple((leg, phase) for leg in LEGS for phase in (PHASE_TAU_C, PHASE_TAU_R))
"""Cell index 0 .. 7 (rank mod 8): leg-major, tau_C before tau_R."""
ANCHOR_OF_PHASE = {PHASE_TAU_C: "phase_exit:CHECK", PHASE_TAU_R: "retract_start_after:LEVEL",
                   PHASE_TRW: "retract_witness_after:LEVEL"}
BLOCK_SEEDS = (40, 41, 42, 43)
"""b1 .. b4 before any collision step (6.3.1; user decision 2026-11-22 after the erratum 1
audit E-1: 40 .. 43, because the X-10 unit tests and a probe had run b1's former ``s30``
keys)."""
BLOCK_PHASES = ("cell", "cell", "cell", PHASE_TRW)
"""b1 .. b3 take the cell's phase, b4 the TRw phase on the cell's leg."""
SEED_STEP = 10
SEED_LIMIT = 900
"""No seed above this (a scan full of keys would never end)."""
DRY_SEEDS = (90, 91)
DRY_PAIRS_PER_SEED = 80
CASE_COUNT = 167
LEVEL = "L2"
CANDIDATE_PREFIX = "cand=current#"
FAULT_VALUE_BAR = -100.0
PLAN_SCHEMA = "r79_rod_fault_plan/1"
R79_KEY_PATTERN = re.compile(rb'"key"\s*:\s*"((?:cand=[^"#]*#)?L\d+[A-Za-z]*\|s(\d+)\|[^"]*)"')
"""4a-4 1 with X-3: an r79 ``"key"`` value (level token ``L``, digits, letters)."""
SCAN_SUFFIXES = (".json", ".jsonl")
SOURCE_KEY_PATTERN = re.compile(
    rb"""["']((?:cand=[^"'#\s]*#)?L\d+[A-Za-z]*\|s(\d+)\|[^"'\s]*)["']""")
"""An r79 key written as a string literal in a test or probe source (a ``"key"`` field is not
needed there; an f-string seed ``s{seed}`` does not match)."""
SOURCE_SUFFIXES = (".py", ".ps1", ".json", ".jsonl", ".txt")
"""The files of an ``--scan-extra`` root (tests, probe records)."""
EXIT_WRITTEN, EXIT_NOT_USABLE, EXIT_ERROR = 0, 2, 3


class NotUsable(Exception):
    """An input or output condition that stops the selection (exit 2)."""


@dataclass(frozen=True)
class KeyScan:
    """Every r79 key under the scan root (plain, without a candidate prefix)."""

    keys: frozenset[str]
    files: tuple[tuple[str, str, int], ...]
    seed_max: int | None


def plain_key(key: str) -> str:
    return key.split("#", 1)[1] if "#" in key else key


def case_of(key: str) -> str:
    """The key without its seed token (``L2|g6|0|...``)."""
    tokens = plain_key(key).split("|")
    return "|".join([tokens[0], *tokens[2:]])


def key_of(case: str, seed: int) -> str:
    level, rest = case.split("|", 1)
    return f"{level}|s{seed}|{rest}"


def l2_cases(noise: dict) -> list[str]:
    """The L2 cases of the case source in first-appearance order."""
    cases: list[str] = []
    seen: set[str] = set()
    for line in noise["results"]:
        if line.get("level") != LEVEL:
            continue
        case = case_of(line["key"])
        if case not in seen:
            seen.add(case)
            cases.append(case)
    return cases


def scan_r79_keys(scan_root: Path) -> KeyScan:
    """Every r79 key of every ``.json`` / ``.jsonl`` under ``scan_root`` (raw bytes; nothing
    left out, 6.3.1: ``j9_runs`` and the dry outputs included)."""
    keys: set[str] = set()
    files = []
    seed_max = None
    for path in sorted(p for p in scan_root.rglob("*") if p.suffix in SCAN_SUFFIXES
                       and p.is_file()):
        data = path.read_bytes()
        found = R79_KEY_PATTERN.findall(data)
        for key, seed in found:
            keys.add(plain_key(key.decode("utf-8")))
            seed_max = int(seed) if seed_max is None else max(seed_max, int(seed))
        files.append((path.relative_to(scan_root).as_posix(),
                      hashlib.sha256(data).hexdigest(), len(found)))
    return KeyScan(frozenset(keys), tuple(files), seed_max)


def scan_source_keys(root: Path) -> KeyScan:
    """Every r79 key string literal of the test and probe sources under ``root``
    (:data:`SOURCE_SUFFIXES`; the erratum 1 audit E-1: test keys run a seed too). File paths
    are relative to ``root``'s parent (``05_tests/...``)."""
    keys: set[str] = set()
    files = []
    seed_max = None
    for path in sorted(p for p in root.rglob("*") if p.suffix in SOURCE_SUFFIXES
                       and p.is_file()):
        data = path.read_bytes()
        found = SOURCE_KEY_PATTERN.findall(data)
        for key, seed in found:
            keys.add(plain_key(key.decode("utf-8")))
            seed_max = int(seed) if seed_max is None else max(seed_max, int(seed))
        files.append((path.relative_to(root.parent).as_posix(),
                      hashlib.sha256(data).hexdigest(), len(found)))
    return KeyScan(frozenset(keys), tuple(files), seed_max)


def merged_scan(scan_root: Path, extra_roots: tuple[Path, ...]) -> KeyScan:
    """The ``--scan-root`` scan and every ``--scan-extra`` source scan together."""
    scans = [scan_r79_keys(scan_root), *(scan_source_keys(root) for root in extra_roots)]
    seeds = [scan.seed_max for scan in scans if scan.seed_max is not None]
    return KeyScan(frozenset().union(*(scan.keys for scan in scans)),
                   tuple(item for scan in scans for item in scan.files),
                   max(seeds) if seeds else None)


def block_seeds(cases: list[str], scanned: frozenset[str]) -> tuple[tuple[int, ...], int]:
    """``(seeds of b1 .. b4, repeat count)``: 40 + j, all four +10 while any generated key is
    in the scan (6.3.1).

    Raises:
        NotUsable: No collision-free seeds below :data:`SEED_LIMIT`.
    """
    seeds, repeats = BLOCK_SEEDS, 0
    while any(key_of(case, seed) in scanned for seed in seeds for case in cases):
        seeds = tuple(seed + SEED_STEP for seed in seeds)
        repeats += 1
        if max(seeds) > SEED_LIMIT:
            raise NotUsable(f"no collision-free seeds up to {SEED_LIMIT}")
    return seeds, repeats


def cell_table(cases: list[str]) -> list[dict]:
    """Rank, case, cell index, leg and phase per case (rank mod 8 of :data:`CELLS`)."""
    table = []
    for rank, case in enumerate(cases):
        leg, phase = CELLS[rank % len(CELLS)]
        table.append({"rank": rank, "case": case, "cell": rank % len(CELLS), "leg": leg,
                      "phase": phase})
    return table


def fault_entry(fault_id: str, leg: str, phase: str) -> dict:
    return {"fault_id": fault_id, "leg": leg, "kind": "STUCK", "value_bar": FAULT_VALUE_BAR,
            "anchor": ANCHOR_OF_PHASE[phase], "delay_reads": 0}


def block_plan(table: list[dict], block: int, seed: int, phase_rule: str) -> dict:
    """The plan of block ``block`` (1 .. 4): every case once, keyed as the runner gets it."""
    faults = {}
    for row in table:
        phase = row["phase"] if phase_rule == "cell" else phase_rule
        key = CANDIDATE_PREFIX + key_of(row["case"], seed)
        faults[key] = fault_entry(f"12b-b{block}-s{seed}-r{row['rank']:03d}-{row['leg']}-"
                                  f"{phase}", row["leg"], phase)
    return {"schema": PLAN_SCHEMA, "faults": faults}


def dry_run_name(seed: int) -> str:
    """The dry run of one seed (``c90``, ``c91``): its plan and key file names start with it."""
    return f"c{seed}"


def dry_plans(table: list[dict], scanned: frozenset[str]
              ) -> tuple[dict[int, dict], dict[int, list[str]]]:
    """The c dry check plans (6.3.10), one per dry seed, and their keys (prelaunch audit B-1
    (a): a plan's keys are exactly its seed's key file, the run's job keys).

    Raises:
        NotUsable: A dry key is in the scan.
    """
    plans, keys = {}, {}
    for index, seed in enumerate(DRY_SEEDS):
        faults, keys[seed] = {}, []
        for row in table[index * DRY_PAIRS_PER_SEED:(index + 1) * DRY_PAIRS_PER_SEED]:
            plain = key_of(row["case"], seed)
            if plain in scanned:
                raise NotUsable(f"dry key {plain} is in the scan (seeds {DRY_SEEDS} are fixed)")
            keys[seed].append(plain)
            faults[CANDIDATE_PREFIX + plain] = fault_entry(
                f"12b-c-s{seed}-r{row['rank']:03d}-{row['leg']}-{row['phase']}", row["leg"],
                row["phase"])
        plans[seed] = {"schema": PLAN_SCHEMA, "faults": faults}
    return plans, keys


DRY_PAIRS = 160
DRY_PAIRS_PER_CELL = 20


def dry_union_check(plans: dict[int, dict]) -> dict:
    """Erratum 4 4-2: the two dry plans together are the 160 pairs of 6.3.10, 20 per cell (leg,
    anchor), each key in one plan only (a record of selection.json ``dry.union_check``).

    Raises:
        NotUsable: The union is not that.
    """
    per_cell: dict[str, int] = {}
    keys: list[str] = []
    for seed in DRY_SEEDS:
        for key, fault in plans[seed]["faults"].items():
            keys.append(key)
            cell = f"{fault['leg']} {fault['anchor']}"
            per_cell[cell] = per_cell.get(cell, 0) + 1
    check = {"pairs": len(keys), "distinct_keys": len(set(keys)), "cells": len(per_cell),
             "per_cell": dict(sorted(per_cell.items()))}
    check["ok"] = (check["pairs"] == check["distinct_keys"] == DRY_PAIRS
                   and check["cells"] == len(CELLS)
                   and set(per_cell.values()) == {DRY_PAIRS_PER_CELL})
    if not check["ok"]:
        raise NotUsable(f"the dry plans' union is not {DRY_PAIRS} pairs, {DRY_PAIRS_PER_CELL} per "
                        f"cell: {check}")
    return check


def _write_new(path: Path, text: str) -> str:
    """Write ``text`` (UTF-8, LF) to a new file; returns its sha256."""
    data = text.encode("utf-8")
    with path.open("xb") as handle:
        handle.write(data)
    return hashlib.sha256(data).hexdigest()


def _json_text(document: dict) -> str:
    return json.dumps(document, indent=1, ensure_ascii=False) + "\n"


def _keys_text(keys: list[str]) -> str:
    return "".join(f"{key}\n" for key in keys)


def select(noise_path: Path, scan_root: Path, out_dir: Path,
           noise_sha256: str = fixed.NOISE_VB_SHA256, *,
           extra_roots: tuple[Path, ...] = ()) -> dict:
    """Selection and plans (module docstring); returns the ``selection.json`` document.

    Args:
        noise_path: The case source.
        scan_root: Root of the r79 key scan.
        out_dir: New or empty output folder.
        noise_sha256: The case source's fixed sha256 (tests give their own file's).
        extra_roots: Test and probe source roots (``--scan-extra``, :func:`scan_source_keys`).

    Raises:
        NotUsable: Module docstring exit 2.
    """
    problem = fixed.sha_problem(noise_path, noise_sha256, "--noise")
    if problem is not None:
        raise NotUsable(problem)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise NotUsable(f"--out-dir {out_dir} has files (outputs are never overwritten)")
    cases = l2_cases(json.loads(noise_path.read_text(encoding="utf-8")))
    if len(cases) != CASE_COUNT:
        raise NotUsable(f"{len(cases)} L2 cases in the case source, {CASE_COUNT} expected")
    for root in extra_roots:
        if not root.is_dir():
            raise NotUsable(f"--scan-extra {root} is not a folder")
    scan = merged_scan(scan_root, tuple(extra_roots))
    seeds, repeats = block_seeds(cases, scan.keys)
    table = cell_table(cases)
    dry, dry_keys = dry_plans(table, scan.keys)
    union_check = dry_union_check(dry)
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for block, (seed, phase_rule) in enumerate(zip(seeds, BLOCK_PHASES, strict=True), start=1):
        plan = block_plan(table, block, seed, phase_rule)
        outputs[f"b{block}_plan.json"] = _write_new(out_dir / f"b{block}_plan.json",
                                                    _json_text(plan))
        outputs[f"b{block}_keys.txt"] = _write_new(
            out_dir / f"b{block}_keys.txt",
            _keys_text([plain_key(key) for key in plan["faults"]]))
    dry_runs = {}
    for seed in DRY_SEEDS:
        run = dry_run_name(seed)
        dry_runs[run] = {"seed": seed, "plan": f"{run}_plan.json", "keys": f"{run}_keys.txt"}
        outputs[f"{run}_plan.json"] = _write_new(out_dir / f"{run}_plan.json",
                                                 _json_text(dry[seed]))
        outputs[f"{run}_keys.txt"] = _write_new(out_dir / f"{run}_keys.txt",
                                                _keys_text(dry_keys[seed]))
    document = {
        "rule": "jp3_remedy_spec_v5.md 6.3.1 / 6.3.10 (X-11)",
        "inputs": {"noise": {"path": str(noise_path), "sha256": noise_sha256},
                   "scan_root": str(scan_root),
                   "scan_extra": [str(root) for root in extra_roots]},
        "scan": {"files_scanned": len(scan.files), "r79_keys": len(scan.keys),
                 "seed_max": scan.seed_max,
                 "files": [{"path": path, "sha256": sha, "r79_keys": count}
                           for path, sha, count in scan.files]},
        "cases": len(cases), "cells": [list(cell) for cell in CELLS],
        "blocks": {f"b{block}": {"seed_index": seed,
                                 "phase": "cell" if phase_rule == "cell" else phase_rule,
                                 "plan": f"b{block}_plan.json", "keys": f"b{block}_keys.txt"}
                   for block, (seed, phase_rule) in enumerate(zip(seeds, BLOCK_PHASES,
                                                                  strict=True), start=1)},
        "seed_repeats": repeats, "seed_step": SEED_STEP,
        "dry": {"seeds": list(DRY_SEEDS), "pairs": sum(len(keys) for keys in dry_keys.values()),
                "runs": dry_runs, "union_check": union_check},
        "cell_table": table, "outputs": outputs,
        "run_commands": _run_commands(seeds)}
    _write_new(out_dir / "selection.json", _json_text(document))
    return document


def _run_commands(seeds: tuple[int, ...]) -> list[str]:
    """The runner lines per block and arm (VBK0 blocks first, 8 4.(6); the main session
    launches them, ``R79_ROD_MODEL=plant_truth``)."""
    lines = []
    for arm in ("VBK0", "VBK"):
        for block, _ in enumerate(seeds, start=1):
            lines.append(f"R79_V5_SETTING={arm} R79_ROD_MODEL=plant_truth R79_T4H_DIR=<out>/"
                         f"{arm}_b{block}_t4h R79_ROD_FAULT_PLAN=<plans>/b{block}_plan.json "
                         f"r79_L3L4_final.py <root> run <out>/{arm}_b{block}.json --levels L2 "
                         f"--keys-file <plans>/b{block}_keys.txt")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--noise", type=Path, required=True)
    parser.add_argument("--scan-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--scan-extra", type=Path, action="append", required=True,
                        help="a test or probe source root (repeatable; at least the run "
                             "worktree's 05_tests, erratum 1 audit E-1)")
    args = parser.parse_args(argv)
    try:
        document = select(args.noise, args.scan_root, args.out_dir,
                          extra_roots=tuple(args.scan_extra))
    except NotUsable as exc:
        print(f"not usable: {exc}", file=sys.stderr)
        print(json.dumps({"status": "not_usable", "out_dir": str(args.out_dir)}))
        return EXIT_NOT_USABLE
    except Exception as exc:  # every other failure is a tool error, never a selection
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(json.dumps({"status": "error", "out_dir": str(args.out_dir)}))
        return EXIT_ERROR
    print(json.dumps({"status": "written", "out_dir": str(args.out_dir),
                      "seeds": [block["seed_index"] for block in document["blocks"].values()],
                      "seed_repeats": document["seed_repeats"]}))
    return EXIT_WRITTEN


if __name__ == "__main__":
    sys.exit(main())
