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
  repeat count. Test and probe keys use seeds outside the judged set (``s95`` .. ``s99``, not
  the dry seeds).
* cell = rank mod 8 of :data:`CELLS` (leg-major: FL tau_C, FL tau_R, FR tau_C, ... RR tau_R),
  the same for every block; b4 keeps the cell's leg with the phase TRw for all its pairs.
* anchors: tau_C ``phase_exit:CHECK``, tau_R ``retract_start_after:LEVEL``, TRw
  ``retract_witness_after:LEVEL``; STUCK -100 bar, ``delay_reads`` 0 (6.3.2).
* the c dry check (6.3.10): seeds 92 and 93 (edition 5 erratum 6 6-3; ``ae9d0b2d`` ran 90 / 91,
  whose results were seen), outside the judged set, 160 pairs = 20 per cell (seed 92: ranks
  0 .. 79, seed 93: ranks 80 .. 159; the same cell table). A dry seed found in
  the scan stops (exit 2): the spec fixes those two seeds. One plan per dry seed (prelaunch
  audit B-1 (a)): a dry run takes one seed's key file, and the runner's X-10 guard needs the
  plan keys to be exactly the run's job keys.

One plan serves both arms of a block (VBK0 and VBK, ``R79_ROD_FAULT_PLAN``): the pair identity
(다) is the plan sha256 by construction. Per block a key file (one ``L2|s<seed>|...`` key per
line, LF) for ``r79_L3L4_final.py run --keys-file``.

Outputs in ``--out-dir`` (a new or empty folder; an existing file is never overwritten):
``b<j>_plan.json``, ``b<j>_keys.txt`` (j = 1 .. 4), ``c92_plan.json``, ``c92_keys.txt``,
``c93_plan.json``, ``c93_keys.txt``, ``selection.json`` (``dry.runs`` names each dry run's plan
and key file; inputs and their sha256, the scan evidence: files
scanned, per-file sha256 and key count, the largest seed; the seeds and repeat count, the cell
table, every output file with its sha256 and the run commands).

Edition 6 (``--edition 6``, ``jp3_remedy_spec_v6.md`` 6.4 revision 9, user decision
2026-11-24): blocks b1 .. b4 = seed_index 50, 51, 52, 53 with the same +10 collision rule, also
raised while a block seed is one of the other seeds of the procedure (:data:`ED6_RESERVED_SEEDS`:
T-CK 80, DROPOUT 81, c dry 90 .. 93, dry 25, tests 95 .. 99); no c dry plans (not run in
edition 6). ``--scan-exclude <glob>`` leaves files out of the scan without opening them
(``fnmatch`` on the path relative to ``--scan-root``; the blinded edition 5 c dry outputs), and
``--scan-keys-file <txt>`` adds plain key lists (one key per line; the c dry key files that list
exactly the excluded runs' keys). ``selection.json`` names the excluded files and the key files.

Edition 7 (``--edition 7``, ``jp3_remedy_spec_v7.md`` 6.4, Y7-7, stats question 9): the
edition 6 seeds 50 .. 53, reserved seeds and +10 rule unchanged (they were never run), the
scan widened by ``--scan-required <root>`` (repeatable, at least one: the edition 6 run
outputs, records B / C / D and the edition 7 outputs with the probe): every file kind of
:data:`ED7_SCAN_SUFFIXES` under the root, ``.npz`` string arrays included, with the ``"key"``,
string-literal and plain-line patterns; a required root without a file stops (exit 2). The
plans carry the arms VBKM0 / VBKM. Every edition 7 walk (``--scan-root``, ``--scan-extra``,
``--scan-required``, the ``--scan-exclude`` listing) drops the blind prefixes of
:data:`ED7_BLIND_PREFIXES` by name before it lists, stats or opens anything (user decision
2026-11-24); a root or key file inside one stops (exit 2). No output names a blind path or
counts its files: ``selection.json`` records only ``blind_prefixes_applied`` (the number of
prefixes). Editions 5 and 6 keep their ``rglob`` scan unchanged.

Usage (python-dev or Chrono-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_12b_plan.py --noise <h8_noise_VB.json>
      --scan-root <repo>/06_analysis --scan-extra <run worktree>/05_tests --out-dir <folder>
      [--edition 6|7] [--scan-exclude <glob> ...] [--scan-keys-file <txt> ...]
      [--scan-required <root> ...]

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
import fnmatch
import hashlib
import json
import os
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
ED6_BLOCK_SEEDS = (50, 51, 52, 53)
"""Edition 6 b1 .. b4 before any collision step (spec v6 6.4 revision 9, G-1)."""
ED6_RESERVED_SEEDS = (25, 80, 81, 90, 91, 92, 93, 95, 96, 97, 98, 99)
"""Spec v6 6.4: the other seeds of the procedure no block seed may take (dry 25, T-CK 80,
DROPOUT 81, c dry 90 .. 93, tests 95 .. 99)."""
BLOCK_PHASES = ("cell", "cell", "cell", PHASE_TRW)
"""b1 .. b3 take the cell's phase, b4 the TRw phase on the cell's leg."""
SEED_STEP = 10
SEED_LIMIT = 900
"""No seed above this (a scan full of keys would never end)."""
DRY_SEEDS = (92, 93)
"""Edition 5 erratum 6 6-3: the c dry seeds of a new run commit (90 / 91 ran at ``ae9d0b2d`` and
their gate result was seen, so they are no seeds fixed before the result)."""
DRY_PAIRS_PER_SEED = 80
CASE_COUNT = 167
LEVEL = "L2"
CANDIDATE_PREFIX = "cand=current#"
FAULT_VALUE_BAR = -100.0
PLAN_SCHEMA = "r79_rod_fault_plan/1"
R79_KEY_PATTERN = re.compile(rb'"key"\s*:\s*"((?:cand=[^"#]*#)?L\d+[A-Za-z]*\|s(\d+)\|[^"]*)"')
"""4a-4 1 with X-3: an r79 ``"key"`` value (level token ``L``, digits, letters)."""
SCAN_SUFFIXES = (".json", ".jsonl")
PLAIN_KEY_LINE = re.compile(r"^(?:cand=[^#\s]*#)?(L\d+[A-Za-z]*\|s(\d+)\|\S*)$")
"""One r79 key per line of a ``--scan-keys-file`` list (edition 6)."""
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


def is_excluded(relative: str, excludes: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatchcase(relative, pattern) for pattern in excludes)


ED7_BLIND_PREFIXES = (
    "06_analysis/02_control/j_p3_cause/j9_runs/606f8713/cdry_a1/VBK_c92*",
    "06_analysis/02_control/j_p3_cause/j9_runs/606f8713/cdry_a1/VBK_c93*",
    "06_analysis/02_control/j_p3_cause/j9_runs/606f8713/cdry_a1/logs",
)
"""Edition 7 blind paths (user decision 2026-11-24): path-component patterns (``fnmatch``,
case-insensitive) matched anywhere in a path's absolute components. A matching entry is never
opened, listed or stat-ed, nothing below it is walked, and no output names it or counts it
(``selection.json`` says only how many prefixes were applied)."""


def is_blind(path: Path, prefixes: tuple[str, ...]) -> bool:
    """``path`` (or one of its ancestors) matches a blind prefix; string work only, the file
    system is not touched (``os.path.abspath`` does not resolve links)."""
    parts = [part.casefold() for part in Path(os.path.abspath(path)).parts]
    for prefix in prefixes:
        pattern = prefix.casefold().split("/")
        for start in range(len(parts) - len(pattern) + 1):
            window = parts[start:start + len(pattern)]
            if all(fnmatch.fnmatchcase(part, item)
                   for part, item in zip(window, pattern, strict=True)):
                return True
    return False


def _unblinded_files(root: Path, suffixes: tuple[str, ...],
                     blind: tuple[str, ...]) -> list[Path]:
    """The files of ``suffixes`` under ``root`` in sorted order, walked with ``os.scandir`` so
    that a blind entry is dropped by its name before anything else touches it (the
    ``rglob`` of editions 5 / 6 would list and stat inside it).

    Raises:
        NotUsable: ``root`` itself lies in a blind prefix (nothing is opened).
    """
    if is_blind(root, blind):
        raise NotUsable("a scan root lies inside an edition 7 blind prefix (not scanned)")
    files: list[Path] = []
    pending = [root]
    while pending:
        folder = pending.pop()
        with os.scandir(folder) as entries:
            children = [folder / entry.name for entry in entries
                        if not is_blind(folder / entry.name, blind)]
        for child in children:
            if child.is_dir() and not child.is_symlink():
                pending.append(child)
            elif child.suffix in suffixes and child.is_file():
                files.append(child)
    return sorted(files)


def _scan_files(root: Path, suffixes: tuple[str, ...],
                blind: tuple[str, ...] = ()) -> list[Path]:
    """The scanned files of one root: the edition 5 / 6 ``rglob`` unchanged without blind
    prefixes, the pruned walk with them (edition 7)."""
    if not blind:
        return sorted(p for p in root.rglob("*") if p.suffix in suffixes and p.is_file())
    return _unblinded_files(root, suffixes, blind)


def scan_r79_keys(scan_root: Path, excludes: tuple[str, ...] = (),
                  blind: tuple[str, ...] = ()) -> KeyScan:
    """Every r79 key of every ``.json`` / ``.jsonl`` under ``scan_root`` (raw bytes, only the
    ``"key"`` values are taken; nothing left out, 6.3.1: ``j9_runs`` and the dry outputs
    included), but the files ``excludes`` names, which are not opened, and (edition 7) the
    ``blind`` prefixes, which are not even walked."""
    keys: set[str] = set()
    files = []
    seed_max = None
    for path in _scan_files(scan_root, SCAN_SUFFIXES, blind):
        if is_excluded(path.relative_to(scan_root).as_posix(), excludes):
            continue
        data = path.read_bytes()
        found = R79_KEY_PATTERN.findall(data)
        for key, seed in found:
            keys.add(plain_key(key.decode("utf-8")))
            seed_max = int(seed) if seed_max is None else max(seed_max, int(seed))
        files.append((path.relative_to(scan_root).as_posix(),
                      hashlib.sha256(data).hexdigest(), len(found)))
    return KeyScan(frozenset(keys), tuple(files), seed_max)


def scan_source_keys(root: Path, blind: tuple[str, ...] = ()) -> KeyScan:
    """Every r79 key string literal of the test and probe sources under ``root``
    (:data:`SOURCE_SUFFIXES`; the erratum 1 audit E-1: test keys run a seed too). File paths
    are relative to ``root``'s parent (``05_tests/...``)."""
    keys: set[str] = set()
    files = []
    seed_max = None
    for path in _scan_files(root, SOURCE_SUFFIXES, blind):
        data = path.read_bytes()
        found = SOURCE_KEY_PATTERN.findall(data)
        for key, seed in found:
            keys.add(plain_key(key.decode("utf-8")))
            seed_max = int(seed) if seed_max is None else max(seed_max, int(seed))
        files.append((path.relative_to(root.parent).as_posix(),
                      hashlib.sha256(data).hexdigest(), len(found)))
    return KeyScan(frozenset(keys), tuple(files), seed_max)


def excluded_files(scan_root: Path, excludes: tuple[str, ...],
                   blind: tuple[str, ...] = ()) -> list[str]:
    """The scan files ``excludes`` leaves out (paths only; the files are not opened). Blind
    files (edition 7) are never listed here: they are not walked at all."""
    if blind:
        return [path.relative_to(scan_root).as_posix()
                for path in _scan_files(scan_root, SCAN_SUFFIXES, blind)
                if is_excluded(path.relative_to(scan_root).as_posix(), excludes)]
    return [path.relative_to(scan_root).as_posix() for path in sorted(scan_root.rglob("*"))
            if path.suffix in SCAN_SUFFIXES and path.is_file()
            and is_excluded(path.relative_to(scan_root).as_posix(), excludes)]


def scan_key_lists(paths: tuple[Path, ...]) -> KeyScan:
    """Plain key lists (one r79 key per line, ``--scan-keys-file``)."""
    keys: set[str] = set()
    files = []
    seed_max = None
    for path in paths:
        data = path.read_bytes()
        found = [PLAIN_KEY_LINE.match(line.strip()) for line in data.decode("utf-8").splitlines()]
        found = [match for match in found if match]
        for match in found:
            keys.add(match.group(1))
            seed = int(match.group(2))
            seed_max = seed if seed_max is None else max(seed_max, seed)
        files.append((str(path), hashlib.sha256(data).hexdigest(), len(found)))
    return KeyScan(frozenset(keys), tuple(files), seed_max)


def merged_scan(scan_root: Path, extra_roots: tuple[Path, ...],
                excludes: tuple[str, ...] = (), key_lists: tuple[Path, ...] = (),
                blind: tuple[str, ...] = ()) -> KeyScan:
    """The ``--scan-root`` scan (less ``excludes``), every ``--scan-extra`` source scan and the
    ``--scan-keys-file`` lists together (edition 7: every walk skips the ``blind`` prefixes)."""
    scans = [scan_r79_keys(scan_root, excludes, blind),
             *(scan_source_keys(root, blind) for root in extra_roots)]
    if key_lists:
        scans.append(scan_key_lists(key_lists))
    seeds = [scan.seed_max for scan in scans if scan.seed_max is not None]
    return KeyScan(frozenset().union(*(scan.keys for scan in scans)),
                   tuple(item for scan in scans for item in scan.files),
                   max(seeds) if seeds else None)


ED7_SCAN_SUFFIXES = (".json", ".jsonl", ".txt", ".csv", ".ps1", ".py", ".npz")
"""Edition 7 (spec v7 6.4, stats question 9): every file kind of a ``--scan-required`` root;
an ``.npz`` is read member by member (its string arrays, e.g. a T4h ``meta_json``)."""


def _keys_in_bytes(data: bytes) -> list[tuple[str, int]]:
    """Every r79 key of one text: ``"key"`` values, string literals and plain key lines."""
    found = [(key.decode("utf-8"), int(seed)) for key, seed in R79_KEY_PATTERN.findall(data)]
    found += [(key.decode("utf-8"), int(seed)) for key, seed in SOURCE_KEY_PATTERN.findall(data)]
    for line in data.decode("utf-8", "replace").splitlines():
        match = PLAIN_KEY_LINE.match(line.strip())
        if match:
            found.append((match.group(1), int(match.group(2))))
    return [(plain_key(key), seed) for key, seed in found]


def _npz_texts(path: Path) -> list[bytes]:
    """The string arrays of an ``.npz`` as UTF-8 texts (numeric arrays hold no key)."""
    import numpy as np

    texts = []
    with np.load(path, allow_pickle=False) as data:
        for name in data.files:
            array = data[name]
            if array.dtype.kind in ("U", "S"):
                texts.append("\n".join(str(item) for item in array.ravel()).encode("utf-8"))
    return texts


def scan_required_root(root: Path, scan_root: Path, excludes: tuple[str, ...] = (),
                       blind: tuple[str, ...] = ED7_BLIND_PREFIXES) -> KeyScan:
    """Edition 7: every r79 key of every :data:`ED7_SCAN_SUFFIXES` file under ``root`` (the
    edition 6 run outputs, records B / C / D, the edition 7 outputs and probe); a file the
    ``excludes`` name (relative to ``scan_root`` when ``root`` lies in it) is not opened, and
    nothing in a ``blind`` prefix is walked."""
    keys: set[str] = set()
    files = []
    seed_max = None
    for path in _scan_files(root, ED7_SCAN_SUFFIXES, blind):
        if path.is_relative_to(scan_root) and is_excluded(
                path.relative_to(scan_root).as_posix(), excludes):
            continue
        data = path.read_bytes()
        texts = _npz_texts(path) if path.suffix == ".npz" else [data]
        found = [item for text in texts for item in _keys_in_bytes(text)]
        for key, seed in found:
            keys.add(key)
            seed_max = seed if seed_max is None else max(seed_max, seed)
        files.append((str(path), _sha256_hex(data), len(found)))
    return KeyScan(frozenset(keys), tuple(files), seed_max)


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def block_seeds(cases: list[str], scanned: frozenset[str],
                base: tuple[int, ...] = BLOCK_SEEDS,
                reserved: tuple[int, ...] = ()) -> tuple[tuple[int, ...], int]:
    """``(seeds of b1 .. b4, repeat count)``: ``base`` (40 + j; edition 6 50 + j), all four +10
    while any generated key is in the scan (6.3.1) or a seed is ``reserved`` (edition 6).

    Raises:
        NotUsable: No collision-free seeds below :data:`SEED_LIMIT`.
    """
    seeds, repeats = tuple(base), 0
    while (any(seed in reserved for seed in seeds)
           or any(key_of(case, seed) in scanned for seed in seeds for case in cases)):
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
    """The dry run of one seed (``c92``, ``c93``): its plan and key file names start with it."""
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
           extra_roots: tuple[Path, ...] = (), edition: int = 5,
           excludes: tuple[str, ...] = (), key_lists: tuple[Path, ...] = (),
           required_roots: tuple[Path, ...] = ()) -> dict:
    """Selection and plans (module docstring); returns the ``selection.json`` document.

    Args:
        noise_path: The case source.
        scan_root: Root of the r79 key scan.
        out_dir: New or empty output folder.
        noise_sha256: The case source's fixed sha256 (tests give their own file's).
        extra_roots: Test and probe source roots (``--scan-extra``, :func:`scan_source_keys`).
        edition: 5 (seeds 40 + j and the c dry plans), 6 or 7 (module docstring).
        excludes: ``--scan-exclude`` globs; key_lists: ``--scan-keys-file`` paths.
        required_roots: Edition 7 ``--scan-required`` roots (:func:`scan_required_root`).

    Raises:
        NotUsable: Module docstring exit 2.
    """
    _check_edition_inputs(edition, excludes, key_lists, required_roots)
    problem = fixed.sha_problem(noise_path, noise_sha256, "--noise")
    if problem is not None:
        raise NotUsable(problem)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise NotUsable(f"--out-dir {out_dir} has files (outputs are never overwritten)")
    cases = l2_cases(json.loads(noise_path.read_text(encoding="utf-8")))
    if len(cases) != CASE_COUNT:
        raise NotUsable(f"{len(cases)} L2 cases in the case source, {CASE_COUNT} expected")
    blind = ED7_BLIND_PREFIXES if edition == 7 else ()
    if any(is_blind(root, blind) for root in (scan_root, *extra_roots)):
        raise NotUsable("--scan-root / --scan-extra lies inside an edition 7 blind prefix")
    for root in extra_roots:
        if not root.is_dir():
            raise NotUsable(f"--scan-extra {root} is not a folder")
    for path in key_lists:
        if is_blind(path, blind):
            raise NotUsable("a --scan-keys-file lies inside an edition 7 blind prefix")
        if not path.is_file():
            raise NotUsable(f"--scan-keys-file {path} not found")
    scan = merged_scan(scan_root, tuple(extra_roots), tuple(excludes), tuple(key_lists),
                       blind)
    required_scans = [scan_required_root(root, scan_root, tuple(excludes), blind)
                      for root in required_roots]
    empty = [str(root) for root, found in zip(required_roots, required_scans, strict=True)
             if not found.files]
    if empty:
        raise NotUsable(f"--scan-required roots without a file: {empty}")
    scan = _with_required(scan, required_scans)
    if edition in (6, 7):
        seeds, repeats = block_seeds(cases, scan.keys, ED6_BLOCK_SEEDS, ED6_RESERVED_SEEDS)
    else:
        seeds, repeats = block_seeds(cases, scan.keys)
    table = cell_table(cases)
    dry, dry_keys = ({}, {}) if edition in (6, 7) else dry_plans(table, scan.keys)
    union_check = None if edition in (6, 7) else dry_union_check(dry)
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
    for seed in dry:
        run = dry_run_name(seed)
        dry_runs[run] = {"seed": seed, "plan": f"{run}_plan.json", "keys": f"{run}_keys.txt"}
        outputs[f"{run}_plan.json"] = _write_new(out_dir / f"{run}_plan.json",
                                                 _json_text(dry[seed]))
        outputs[f"{run}_keys.txt"] = _write_new(out_dir / f"{run}_keys.txt",
                                                _keys_text(dry_keys[seed]))
    document = {
        "rule": RULE_OF_EDITION[edition],
        "inputs": {"noise": {"path": str(noise_path), "sha256": noise_sha256},
                   "scan_root": str(scan_root),
                   "scan_extra": [str(root) for root in extra_roots],
                   **_edition_6_inputs(edition, scan_root, excludes, key_lists, blind),
                   **({"scan_required": [str(root) for root in required_roots],
                       "blind_prefixes_applied": len(blind),
                       "blind_note": f"excluded prefixes applied: {len(blind)} (never walked; "
                                     "no path or count of them is written)"}
                      if edition == 7 else {})},
        **({"edition": edition, "reserved_seeds": list(ED6_RESERVED_SEEDS)}
           if edition in (6, 7) else {}),
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
        "dry": {"seeds": list(dry), "pairs": sum(len(keys) for keys in dry_keys.values()),
                "runs": dry_runs, "union_check": union_check},
        "cell_table": table, "outputs": outputs,
        "run_commands": _run_commands(seeds, ARMS_OF_EDITION[edition])}
    _write_new(out_dir / "selection.json", _json_text(document))
    return document


RULE_OF_EDITION = {5: "jp3_remedy_spec_v5.md 6.3.1 / 6.3.10 (X-11)",
                   6: "jp3_remedy_spec_v6.md 6.4 revision 9 (G-1)",
                   7: "jp3_remedy_spec_v7.md 6.4 (Y7-7: the edition 6 seeds, scan widened)"}
ARMS_OF_EDITION = {5: ("VBK0", "VBK"), 6: ("VBKL0", "VBKL"), 7: ("VBKM0", "VBKM")}


def _check_edition_inputs(edition: int, excludes: tuple[str, ...],
                          key_lists: tuple[Path, ...],
                          required_roots: tuple[Path, ...]) -> None:
    """Which options an edition takes (edition 7 needs at least one ``--scan-required``).

    Raises:
        NotUsable: An unknown edition, an option of another edition, a missing required root.
    """
    if edition not in RULE_OF_EDITION:
        raise NotUsable(f"edition {edition}: one of {sorted(RULE_OF_EDITION)}")
    if edition == 5 and (excludes or key_lists):
        raise NotUsable("--scan-exclude / --scan-keys-file are edition 6 options (and 7)")
    if edition != 7 and required_roots:
        raise NotUsable("--scan-required is an edition 7 option")
    if edition == 7 and not required_roots:
        raise NotUsable("edition 7 needs --scan-required (the edition 6 run outputs, records "
                        "B / C / D and the edition 7 outputs, spec v7 6.4)")
    if edition == 7 and any(is_blind(root, ED7_BLIND_PREFIXES) for root in required_roots):
        raise NotUsable("a --scan-required root lies inside an edition 7 blind prefix")
    for root in required_roots:
        if not root.is_dir():
            raise NotUsable(f"--scan-required {root} is not a folder")


def _with_required(scan: KeyScan, required: list[KeyScan]) -> KeyScan:
    if not required:
        return scan
    scans = [scan, *required]
    seeds = [item.seed_max for item in scans if item.seed_max is not None]
    return KeyScan(frozenset().union(*(item.keys for item in scans)),
                   tuple(entry for item in scans for entry in item.files),
                   max(seeds) if seeds else None)


def _edition_6_inputs(edition: int, scan_root: Path, excludes: tuple[str, ...],
                      key_lists: tuple[Path, ...], blind: tuple[str, ...] = ()) -> dict:
    """The edition 6 / 7 scan inputs of ``selection.json`` (an edition 5 document keeps its
    former keys)."""
    if edition not in (6, 7):
        return {}
    return {"scan_exclude": list(excludes),
            "scan_excluded_files": excluded_files(scan_root, tuple(excludes), blind),
            "scan_keys_files": [str(path) for path in key_lists]}


def _run_commands(seeds: tuple[int, ...], arms: tuple[str, str] = ("VBK0", "VBK")
                  ) -> list[str]:
    """The runner lines per block and arm (the reference arm first, 8 4.(6); the main session
    launches them, ``R79_ROD_MODEL=plant_truth``; edition 6: VBKL0 / VBKL)."""
    lines = []
    for arm in arms:
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
    parser.add_argument("--edition", type=int, default=5, choices=(5, 6, 7))
    parser.add_argument("--scan-exclude", action="append", default=[],
                        help="glob relative to --scan-root: files left out, never opened")
    parser.add_argument("--scan-keys-file", type=Path, action="append", default=[],
                        help="a plain key list added to the scan (one key per line)")
    parser.add_argument("--scan-required", type=Path, action="append", default=[],
                        help="edition 7: a root scanned in every file kind, .npz included "
                             "(the edition 6 run outputs, records B / C / D, the edition 7 "
                             "outputs and probe; repeatable, at least one)")
    args = parser.parse_args(argv)
    try:
        document = select(args.noise, args.scan_root, args.out_dir,
                          extra_roots=tuple(args.scan_extra), edition=args.edition,
                          excludes=tuple(args.scan_exclude),
                          key_lists=tuple(args.scan_keys_file),
                          required_roots=tuple(args.scan_required))
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
