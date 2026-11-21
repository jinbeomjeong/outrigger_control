"""436.9 addenda 4a-6 G-4 and 4a-7 2: do the steps (1) .. (4b) of a new run commit reproduce
the earlier attempt (4a-7 2.1: ``j9_runs/fa997f4c/`` only)? Only these values are read,
compared in memory and never written:

======== ==============================================================================
item     values compared (old attempt against new attempt)
======== ==============================================================================
p1       sha256 of ``h6_base_judge.json`` and ``h6_base_judge_L1_reference.json``; the
         exit codes ``tool:base_judge_compare`` and ``tool:t12_selfcheck``
dry      the two evidence keys (``rod_reading_truth_calls``, ``two_pressure_reads``) of
         every record of the five dry runs; the exit code ``tool:summarize``
fpath    ``harness_commands_sha256`` of the three F-A path rows (by ``offset_s``); the exit
         code ``tool:case_f_path``
x11      ``commands_sha256`` of the ``LSJ4_X11`` row, the class and ``p_tr - ④`` gap of its
         FL 49.0 s read (``jp3_case_judge._x11_read``); the exit code ``tool:x11``
cases_ae (4a-7 2.1, step 4a) per row of ``j9_cases.jsonl`` / ``cd.jsonl`` (by job): the
         64-character ``commands_sha256``, the P4-3a sums of ``jp3a_breach_reads``,
         ``jp3b_breach_over_tol_reads``, ``jp3c_breach_reads`` and
         ``relock_step_over_1bar_count``, P4-4 ``p1_retract_seed_count`` and
         ``p1_retract_seed_step_max_bar``, the P4-9 ``retract_tracker_dominated_reads``
         sum; per pair of ``judge/baseline_compare.json`` the P4-2 ``lowered_reads``,
         ``unexplained_raised_reads``, ``bad_class_changes`` and the seed rows over the net
         force limit (``seed.over_1N_rows``); its ``status``; the code
         ``tool:baseline_compare``
casef    (4a-7 2.1, step 4b) ``commands_sha256`` of the 15 rows of ``j9_case_f.jsonl`` and
         the VB ``harness_commands_sha256``; the F-A, F-B, F-E statuses (judged again by
         the ``jp3_case_judge`` part functions on the rows and the fixed grid named in
         ``judge/case_f.json``); its ``status``; the code ``tool:case_f``
dry5     (edition 5 erratum 1 9.3, against 78fd5d2d ``dry_a1``) the g6 r79 VBJ / VBH lines:
         ``key`` without its prefix, ``seed_index``, the two evidence keys, and
         ``commands_sha256`` under the P5-1 rule (equal when neither side has
         ``WARN_ROD_PRESSURE_FALLBACK``, else recorded only: ``recorded_only``); the event
         lines VBJ / VBH: the hash under the P5-1 rule, VBJ0: the hash whatever the
         fallbacks. Not compared: ``extend_bound_check``, ``jp3_*`` arrays, run meta; g8 /
         ref (not run in edition 4a). No exit code compared
dry5_retry (9.3, a retry ``dry_a<k>`` of the same commit, ``--old-folder dry_a<k-1>``) every
         result line of the folder without the run meta keys (``wall_s``, ``mask``,
         ``t4h_dir``), one sha256 per line
======== ==============================================================================

A step's folder is the ``folder`` of ``<root>/<step>.done`` (else of the newest
``<step>.stop*``), taken by name under ``<root>``; its exit codes are those of its
``step_record.json``. Inside a running step (before its record exists) the new side is given
by ``--new-folder`` and ``--new-codes`` (a JSON file of the step's codes so far).

The report names each compared value and whether it is the same; no value is written. The
stdout's last line is JSON with ``status`` and counts. ``--old`` may be given more than once:
each item is compared with every earlier attempt (``by_old``), its status is the worst of
them. The run steps pass ``fa997f4c`` alone (4a-7 2.1: b51ed6e1 is not read again).

Exit codes: 0 all the same, 1 a value differs, 2 an input missing (a folder, file, key or
code) or other value names on the two sides (another pair or row count), 3 a tool error.

Usage (dynamics-dev, worktree root; the run steps call it after each judgement):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_rerun_match.py --old <j9_runs>/fa997f4c
      --new <j9_runs>/<new commit 8> --items p1,dry,fpath,x11,cases_ae,casef --out <report.json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

ITEM_STEPS = {"p1": "p1", "dry": "dry", "fpath": "fpath", "x11": "cases", "cases_ae": "cases",
              "casef": "casef", "dry5": "dry", "dry5_retry": "dry"}
"""Item -> the run step whose folder holds it."""
CASE_ROW_FILES = ("j9_cases.jsonl", "cd.jsonl")
"""4a-7 2.1 (4a) A .. E: the ``jp3_baseline_compare`` ``--new`` rows of step 4a."""
CASE_REPORT = "judge/baseline_compare.json"
P4_3A_KEYS = ("jp3a_breach_reads", "jp3b_breach_over_tol_reads", "jp3c_breach_reads")
P4_2_KEYS = ("lowered_reads", "unexplained_raised_reads", "bad_class_changes")
CASE_F_ROWS = "j9_case_f.jsonl"
CASE_F_REPORT = "judge/case_f.json"
CASE_F_PARTS = ("F-A", "F-B", "F-E")
P1_FILES = ("h6_base_judge.json", "h6_base_judge_L1_reference.json")
P1_CODES = ("tool:base_judge_compare", "tool:t12_selfcheck")
DRY_EVENT_FILES = ("event_VBJ.jsonl", "event_VBH.jsonl", "event_VBJ0.jsonl")
DRY_R79_FILES = ("r79_VBJ.json", "r79_VBH.json")
EVIDENCE_KEYS = ("rod_reading_truth_calls", "two_pressure_reads")
FPATH_ROWS = "j9_case_f_path.jsonl"
X11_ROWS = "lsj4_x11.jsonl"
X11_SETTING = "LSJ4_X11"
ITEM_CODES = {"p1": P1_CODES, "dry": ("tool:summarize",), "fpath": ("tool:case_f_path",),
              "x11": ("tool:x11",), "cases_ae": ("tool:baseline_compare",),
              "casef": ("tool:case_f",), "dry5": (), "dry5_retry": ()}
EXIT_SAME, EXIT_DIFFERS, EXIT_MISSING, EXIT_ERROR = 0, 1, 2, 3


class Missing(Exception):
    """An input of an item is missing (exit 2)."""


@dataclass
class Side:
    """One attempt: its runs root and, for a running step, its folder and codes."""

    root: Path
    folder: Path | None = None
    codes: dict | None = None
    cache: dict = field(default_factory=dict)

    def step_folder(self, step: str) -> Path:
        if self.folder is not None:
            return self.folder
        return _marked_folder(self.root, step)

    def step_codes(self, step: str) -> dict:
        if self.codes is not None:
            return self.codes
        record = self.step_folder(step) / "step_record.json"
        if not record.is_file():
            raise Missing(f"{record} missing")
        return json.loads(record.read_text(encoding="utf-8")).get("codes") or {}


def _marked_folder(root: Path, step: str) -> Path:
    """The folder of ``<step>.done``, else of the newest ``<step>.stop*`` (by name under root)."""
    markers = [root / f"{step}.done"]
    markers += sorted(root.glob(f"{step}.stop*"), key=lambda path: path.stat().st_mtime,
                      reverse=True)
    for marker in markers:
        if marker.is_file():
            folder = json.loads(marker.read_text(encoding="utf-8")).get("folder")
            if folder:
                return root / Path(folder).name
    raise Missing(f"no {step}.done / {step}.stop under {root}")


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise Missing(f"{path} missing")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_lines(path: Path) -> list[dict]:
    if not path.is_file():
        raise Missing(f"{path} missing")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _evidence(records: list[dict]) -> list:
    return [[(record.get("hydraulics_record") or {}).get(key) for key in EVIDENCE_KEYS]
            for record in records]


def _codes(side: Side, item: str) -> dict:
    if not ITEM_CODES[item]:
        return {}
    codes = side.step_codes(ITEM_STEPS[item])
    missing = [name for name in ITEM_CODES[item] if name not in codes]
    if missing:
        raise Missing(f"{item}: codes {missing} missing")
    return {f"code {name}": codes[name] for name in ITEM_CODES[item]}


def item_values(side: Side, item: str) -> dict:
    """The named values of one item on one side (module docstring)."""
    folder = side.step_folder(ITEM_STEPS[item])
    values = {}
    if item == "p1":
        values.update({f"sha256 {name}": _sha256(folder / name) for name in P1_FILES})
    elif item == "dry":
        for name in DRY_EVENT_FILES:
            values[f"evidence {name}"] = _evidence(_read_lines(folder / name))
        for name in DRY_R79_FILES:
            path = folder / name
            if not path.is_file():
                raise Missing(f"{path} missing")
            values[f"evidence {name}"] = _evidence(
                json.loads(path.read_text(encoding="utf-8")).get("results") or [])
    elif item == "fpath":
        for row in _read_lines(folder / FPATH_ROWS):
            offset = (row.get("job") or {}).get("offset_s")
            values[f"harness_commands_sha256 offset {offset}"] = row.get(
                "harness_commands_sha256")
    elif item == "x11":
        values.update(_x11_values(folder))
    elif item == "cases_ae":
        values.update(_cases_ae_values(folder))
    elif item == "casef":
        values.update(_case_f_values(folder))
    elif item == "dry5":
        values.update(_dry5_values(folder))
    elif item == "dry5_retry":
        values.update(_dry5_retry_values(folder))
    values.update(_codes(side, item))
    return values


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise Missing(f"{path} missing")
    return json.loads(path.read_text(encoding="utf-8"))


def _list_sum(value):
    """The sum of a per-leg list; anything else (None = the key is absent) as it is."""
    if isinstance(value, list) and all(isinstance(item, (int, float)) for item in value):
        return sum(value)
    return value


def _case_row_values(row: dict) -> dict:
    """4a-7 2.1 (4a) of one new row: its hash, the P4-3a sums, P4-4 seeds, the P4-9 sum."""
    hydraulics = row.get("hydraulics_record") or {}
    check = hydraulics.get("extend_bound_check") or {}
    values = {"commands_sha256": row.get("commands_sha256")}
    for key in P4_3A_KEYS:
        values[f"P4-3a {key} sum"] = _list_sum(check.get(key))
    for key in ("relock_step_over_1bar_count", "p1_retract_seed_count",
                "p1_retract_seed_step_max_bar"):
        values[f"{'P4-3a' if key.startswith('relock') else 'P4-4'} {key}"] = hydraulics.get(key)
    values["P4-9 retract_tracker_dominated_reads sum"] = _list_sum(
        check.get("retract_tracker_dominated_reads"))
    return values


def _cases_ae_values(folder: Path) -> dict:
    """4a-7 2.1 (4a) A .. E: per new row (by file and job) :func:`_case_row_values`; per
    ``baseline_compare`` pair (by file, setting and its place in the baseline order) the P4-2
    counts and the P4-4 rows over the net-force limit; the report's status."""
    values = {}
    for name in CASE_ROW_FILES:
        for row in _read_lines(folder / name):
            label = f"{name} {json.dumps(row.get('job'), sort_keys=True)}"
            values.update({f"{label} {key}": value
                           for key, value in _case_row_values(row).items()})
    report = _read_json(folder / CASE_REPORT)
    places: dict[tuple, int] = {}
    for pair in report.get("pairs") or []:
        where = (pair.get("row_file"), pair.get("setting"))
        places[where] = places.get(where, 0) + 1
        label = f"pair {where[0]} {where[1]} #{places[where]}"
        reads = pair.get("reads") or {}
        values.update({f"{label} P4-2 {key}": reads.get(key) for key in P4_2_KEYS})
        values[f"{label} P4-4 over_1N_rows"] = (pair.get("seed") or {}).get("over_1N_rows")
    values["baseline_compare status"] = report.get("status")
    return values


def _case_f_values(folder: Path) -> dict:
    """4a-7 2.1 (4b): the 15 rows' hashes (VB: also the harness hash), the F-A / F-B / F-E
    statuses (judged again here on the rows and the report's grid input) and the report's
    status."""
    import jp3_case_judge as case_judge

    rows = _read_lines(folder / CASE_F_ROWS)
    values = {}
    for row in rows:
        setting = (row.get("job") or {}).get("setting")
        values[f"{setting} commands_sha256"] = row.get("commands_sha256")
        if setting == "VB":
            values["VB harness_commands_sha256"] = row.get(case_judge.HARNESS_HASH_KEY)
    report = _read_json(folder / CASE_F_REPORT)
    values.update(_case_f_part_statuses(rows, _case_f_grid(report)))
    values["case_f status"] = report.get("status")
    return values


def _case_f_grid(report: dict) -> dict:
    """The grid input named in the ``case-f`` report (its sha256 checked)."""
    import jp3_fixed_inputs as fixed

    for entry in report.get("inputs") or []:
        path = Path(entry.get("path") or "")
        if entry.get("sha256") == fixed.GRID_SHA256 and path.is_file():
            if hashlib.sha256(path.read_bytes()).hexdigest() != fixed.GRID_SHA256:
                raise Missing(f"{path}: not the fixed grid any more")
            return json.loads(path.read_text(encoding="utf-8"))
    raise Missing("case-f report without the fixed grid input")


def _case_f_part_statuses(rows: list[dict], grid: dict) -> dict:
    """The status of each of F-A, F-B, F-E (``jp3_case_judge`` part functions, own findings)."""
    import jp3_baseline_compare as compare
    import jp3_case_judge as case_judge

    by_setting = case_judge._rows_by_setting(rows, compare.Problems())
    expected = {setting for group in case_judge.CASE_F_GROUPS.values() for setting in group}
    if set(by_setting) != expected:
        raise Missing(f"case F rows of settings {sorted(by_setting)}, the 15 expected")
    parts = {"F-A": lambda found: case_judge._f_a(by_setting["VB"], grid, found),
             "F-B": lambda found: case_judge._f_b(by_setting, found),
             "F-E": lambda found: case_judge._f_e(by_setting, found)}
    statuses = {}
    for part, judge in parts.items():
        found = compare.Problems()
        judge(found)
        statuses[f"{part} status"] = found.status()
    return statuses


DRY5_R79_FILES = {"r79_VBJ.json": "VBJ", "r79_VBH.json": "VBH"}
"""Edition 5 erratum 1 9.3: the g6 r79 lines compared with 78fd5d2d (g8 / ref were not run in
edition 4a: no comparison, 9.2 only)."""
DRY5_EVENT_FILES = {"event_VBJ.jsonl": False, "event_VBH.jsonl": False,
                    "event_VBJ0.jsonl": True}
"""Event line -> its hash is equal whatever the fallbacks (VBJ0: ③ off); else the P5-1 rule."""
RUN_META_KEYS = frozenset({"wall_s", "wall_s_this_start", "mask", "t4h_dir"})
"""Run meta left out of the same-commit retry comparison (9.3: time, mask, paths)."""
DRY5_ITEMS = ("dry5", "dry5_retry")
HASH_EXEMPT_SUFFIX = " commands_sha256"
FALLBACK_SUFFIX = " rod_fallback"
ALWAYS_EQUAL_SUFFIX = " hash_always_equal"


def _dry5_line(label: str, record: dict, folder: Path | None, always: bool) -> dict:
    """The 9.3 values of one dry line: its hash and the fallback flag of the P5-1 rule
    (``jp3_p51_compare.has_fallback`` on the line's T4h record when its folder is given)."""
    import jp3_p51_compare as p51

    fallback = p51.has_fallback(record, folder)
    if fallback is None and not always:
        raise Missing(f"{label}: the event list is at the cap without a T4h record")
    return {f"{label}{HASH_EXEMPT_SUFFIX}": record.get("commands_sha256"),
            f"{label}{FALLBACK_SUFFIX}": fallback, f"{label}{ALWAYS_EQUAL_SUFFIX}": always}


def _dry5_values(folder: Path) -> dict:
    """Erratum 1 9.3 compared values: per g6 r79 line the key without its prefix, the seed,
    the two evidence keys (per leg) and its hash; per event line its hash (each hash with its
    fallback flag). Not read: the ``extend_bound_check`` contents, the ``jp3_*`` arrays, run
    meta."""
    values = {}
    for name, setting in DRY5_R79_FILES.items():
        records = _read_json(folder / name).get("results") or []
        if len(records) != 1:
            raise Missing(f"{folder / name}: {len(records)} r79 lines, 1 expected")
        record = records[0]
        key = str(record.get("key", ""))
        values[f"{name} key"] = key.split("#", 1)[1] if "#" in key else key
        values[f"{name} seed_index"] = record.get("seed_index")
        values[f"{name} evidence"] = _evidence([record])
        values.update(_dry5_line(name, record, folder / f"{setting}_t4h", always=False))
    for name, always in DRY5_EVENT_FILES.items():
        records = _read_lines(folder / name)
        if len(records) != 1:
            raise Missing(f"{folder / name}: {len(records)} lines, 1 expected")
        values.update(_dry5_line(name, records[0], None, always))
    return values


def _without_run_meta(value):
    if isinstance(value, dict):
        return {key: _without_run_meta(item) for key, item in value.items()
                if key not in RUN_META_KEYS}
    if isinstance(value, list):
        return [_without_run_meta(item) for item in value]
    return value


def _dry5_retry_values(folder: Path) -> dict:
    """9.3 same-commit retry: every result line of the dry folder (the three event lines, the
    r79 lines of every family) without :data:`RUN_META_KEYS`, as a sha256 per line."""
    values = {}
    for name in DRY5_EVENT_FILES:
        for index, record in enumerate(_read_lines(folder / name)):
            values[f"{name} #{index}"] = _canonical_sha(_without_run_meta(record))
    for path in sorted(folder.glob("r79_*.json")):
        for index, record in enumerate(_read_json(path).get("results") or []):
            values[f"{path.name} #{index}"] = _canonical_sha(_without_run_meta(record))
    if not values:
        raise Missing(f"{folder}: no dry result line")
    return values


def _canonical_sha(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def p51_exempt_names(before: dict, after: dict) -> list[str]:
    """The hash names of the P5-1 rule recorded only (a fallback on either side; never on a
    line whose hash is equal whatever the fallbacks)."""
    exempt = []
    for name in before:
        if not name.endswith(HASH_EXEMPT_SUFFIX):
            continue
        label = name.removesuffix(HASH_EXEMPT_SUFFIX)
        if after.get(f"{label}{ALWAYS_EQUAL_SUFFIX}"):
            continue
        flags = (before.get(f"{label}{FALLBACK_SUFFIX}"), after.get(f"{label}{FALLBACK_SUFFIX}"))
        if any(flags):
            exempt.append(name)
    return exempt


def _dry5_judged(before: dict, after: dict) -> tuple[dict, dict, list[str]]:
    """The compared values of 9.3: the fallback flags only decide (P5-1), they are not
    compared; a hash with a fallback on either side is recorded only."""
    exempt = p51_exempt_names(before, after)

    def judged(values: dict) -> dict:
        return {name: value for name, value in values.items()
                if name not in exempt and not name.endswith((FALLBACK_SUFFIX,
                                                             ALWAYS_EQUAL_SUFFIX))}

    return judged(before), judged(after), exempt


def _x11_values(folder: Path) -> dict:
    import jp3_baseline_compare as compare
    import jp3_case_judge as case_judge

    rows = [row for row in _read_lines(folder / X11_ROWS)
            if (row.get("job") or {}).get("setting") == X11_SETTING]
    if len(rows) != 1 or not rows[0].get("t4h_file"):
        raise Missing(f"{folder / X11_ROWS}: {len(rows)} {X11_SETTING} rows")
    npz = folder / f"{Path(X11_ROWS).stem}_t4h" / Path(rows[0]["t4h_file"]).name
    problems = compare.Problems()
    read = case_judge._x11_read(npz, problems)
    if read is None:
        raise Missing(f"{npz}: no FL 49.0 s read ({problems.not_judgeable})")
    return {"commands_sha256 LSJ4_X11": rows[0].get("commands_sha256"),
            "FL 49.0 s class": read["class"], "FL 49.0 s gap_bar": read["gap_bar"]}


STATUS_RANK = {"same": 0, "differs": 1, "missing": 2}


def _compare_one(before: dict, after: dict) -> dict:
    """Same / differs per value name; other names on the two sides (another pair or row
    count) are a missing input (4a-7 5 H-3: exit 2)."""
    if set(before) != set(after):
        return {"status": "missing", "compared": sorted(set(before) & set(after)),
                "differing": [], "one_side_only": sorted(set(before) ^ set(after))[:10],
                "reason": "value names on one side only (another pair or row count)"}
    names = sorted(set(before) | set(after))
    differing = [name for name in names if before.get(name) != after.get(name)]
    return {"status": "differs" if differing else "same", "compared": names,
            "differing": differing}


def compare_items(olds: list[Side], new: Side, items: list[str]) -> tuple[dict, int]:
    """Per item and per earlier attempt the names of the same and the differing values (no
    value in the report); the item's ``status`` is the worst over the attempts (missing >
    differs > same) and ``differing`` the union of the differing names."""
    report, code = {"items": {}}, EXIT_SAME
    for item in items:
        entry: dict = {"by_old": {}}
        try:
            after = item_values(new, item)
        except Missing as exc:
            entry.update(status="missing", reason=f"new: {exc}")
            report["items"][item] = entry
            code = max(code, EXIT_MISSING)
            continue
        for old in olds:
            try:
                before = item_values(old, item)
                found_after = after
                if item == "dry5":
                    before, found_after, recorded = _dry5_judged(before, after)
                found = _compare_one(before, found_after)
                if item == "dry5":
                    found["recorded_only"] = recorded
                entry["by_old"][old.root.name] = found
            except Missing as exc:
                entry["by_old"][old.root.name] = {"status": "missing", "reason": str(exc)}
        statuses = [found["status"] for found in entry["by_old"].values()]
        entry["status"] = max(statuses, key=STATUS_RANK.__getitem__)
        entry["compared"] = sorted({name for found in entry["by_old"].values()
                                    for name in found.get("compared", [])})
        entry["differing"] = sorted({name for found in entry["by_old"].values()
                                     for name in found.get("differing", [])})
        report["items"][item] = entry
        code = max(code, STATUS_RANK[entry["status"]])
    return report, code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="exit codes: 0 same, 1 differs, 2 input missing, "
                                            "3 tool error")
    parser.add_argument("--old", type=Path, action="append", required=True,
                        help="runs root of an earlier attempt (repeatable; the run steps "
                             "pass fa997f4c alone, addendum 4a-7 2.1)")
    parser.add_argument("--new", type=Path, required=True, help="runs root of the new commit")
    parser.add_argument("--items", default=",".join(name for name in ITEM_STEPS
                                                    if name not in DRY5_ITEMS),
                        help=f"comma list of {sorted(ITEM_STEPS)}")
    parser.add_argument("--new-folder", type=Path, default=None,
                        help="the running step's folder (one item only)")
    parser.add_argument("--new-codes", type=Path, default=None,
                        help="JSON file of the running step's codes (with --new-folder)")
    parser.add_argument("--old-folder", type=Path, default=None,
                        help="the earlier attempt's step folder (one --old, one item of "
                             f"{list(DRY5_ITEMS)}: the same-commit retry dry_a<k-1>)")
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    items = [item for item in args.items.split(",") if item]
    unknown = sorted(set(items) - set(ITEM_STEPS))
    if unknown or not items:
        parser.error(f"--items takes {sorted(ITEM_STEPS)}, got {args.items!r}")
    if (args.new_folder is None) != (args.new_codes is None) or (
            args.new_folder is not None and len(items) != 1):
        parser.error("--new-folder and --new-codes go together, with one item")
    if args.old_folder is not None and (len(args.old) != 1 or len(items) != 1
                                        or items[0] not in DRY5_ITEMS):
        parser.error(f"--old-folder takes one --old and one item of {list(DRY5_ITEMS)}")
    if args.out.exists():
        parser.error(f"{args.out} exists (a new report never overwrites one)")
    try:
        codes = None if args.new_codes is None else json.loads(
            args.new_codes.read_text(encoding="utf-8"))
        olds = [Side(root, args.old_folder, None if args.old_folder is None else {})
                for root in args.old]
        report, code = compare_items(olds, Side(args.new, args.new_folder, codes), items)
    except Exception as exc:  # noqa: BLE001 (any error is a tool error, exit 3)
        report, code = {"error": f"{type(exc).__name__}: {exc}"}, EXIT_ERROR
    status = {EXIT_SAME: "same", EXIT_DIFFERS: "differs", EXIT_MISSING: "missing",
              EXIT_ERROR: "error"}[code]
    report.update(status=status, old=[str(root) for root in args.old], new=str(args.new),
                  items_asked=items)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({"status": status, "out": str(args.out),
                      "differing_items": sum(entry.get("status") == "differs"
                                             for entry in report.get("items", {}).values())}))
    return code


if __name__ == "__main__":
    sys.exit(main())
