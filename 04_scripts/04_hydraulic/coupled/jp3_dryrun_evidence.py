"""436.9 B2 dry check (addendum 4a-3 5.1, K-6; addendum 4a-4 1 .. 3, 5): five runs outside every
judged set, of which only the two P4 evidence keys (``rod_reading_truth_calls``,
``two_pressure_reads``) and the error flag are read. The outputs belong to an own folder
(``dryrun_evidence/``) and no judgement uses them.

Sub-commands:

``select``     Reads stored files only. Checks the fixed inputs (4a-4 5: ``--noise``, ``--dg3``,
               ``--main-jsonl`` and the baseline ``SHA256SUMS``), then:
               * event path: the union of the judged job sets (run_v5 ``j9_main``,
                 ``j9_cases``, ``j9_case_f``, ``j9_t8`` of ``--main-jsonl``; the jobs of the
                 baseline's rows) and the first job of :data:`EVENT_CANDIDATES` outside it
                 (normalised job = ``job`` without ``setting``, ``mask``, ``t4h_dir``);
               * r79 (4a-4 1, 2): every r79 key of every ``.json`` / ``.jsonl`` under
                 ``--scan-root`` (the working tree's ``06_analysis/``; addendum 4a-6 G-1: the
                 J-P3 run outputs, relative paths starting with ``02_control/j_p3_cause/
                 j9_runs/``, are left out and listed under ``scan.excluded`` with sha256, key
                 count and whether they hold the generated key; G-3 (b): the ``s25`` key
                 outside them stops, not judgeable; ``"key"`` values
                 ``L<n>|s<n>|...``, a ``cand=...#`` prefix cut), the base key (the first L2 key
                 of ``--noise`` that is not a Dg-3 key) and the generated key: its seed token
                 only set to ``s25``, raised by 1 while the key is in the scan.
               The output shows the scan evidence (files scanned, per-file sha256 and key
               count, the largest seed), the base and generated key, ``n``, that the generated
               key is neither in the scan nor a Dg-3 key, the one-line key file for the runner
               and the five commands. No event candidate outside the union, or no r79 key in
               the scan, stops (exit 2, 4a-3 5.1 / 4a-4 1: never a judged job instead).
``run-event``  One event-path run of the selected job under ``--setting`` (VBJ, VBH or VBJ0) in
               a spawned worker (``run_v5.run_one``), one JSON line to ``--out``. The main
               session launches it (a simulation).
``summarize``  The five outputs against the table (4a-3 5.1 rows 1 .. 3, 4a-4 3 rows 4 .. 5):
               per run only the evidence keys and whether it ran without an error; for the r79
               runs also that the runner took the generated key (4a-4 2: its ``key`` without the
               prefix = the generated key, ``seed_index`` = ``n``; 4a-4 erratum 1: the output
               meta's ``keys_file.sha256`` = the selection's key file sha = the fixed
               ``DRY_KEYS_FILE_SHA256`` and ``keys_file.n_keys`` = 1). A miss of that is not
               judgeable with the reason "다시 묻기" (ask the user again, no judged key instead).
               Record only (prelaunch audit R-b): whether each r79 line carries the keys
               T-JR-14 / 15 read later (``record_keys_present``; no value is read).

``select --keys-file <path>`` names the key file the commands use: absent = written, present
(the repository copy ``j4a_remedy_b06e409e/dryrun_selection_r79_key.txt``) = it must hold the
generated key; either way its sha256 must be the fixed one.

The r79 runs use the T-JR-12 runner and environment (4a-4 3): ``las_t3_dg3.py`` with
``R79_V5_SETTING``, ``R79_T4H_DIR``, ``LAS_T3_DG3_LAS/K1/P3=on`` (VBJ also
``R79_ROD_MODEL=plant_truth``). The runner (``r79_L3L4_final.cmd_run``) takes ``--keys`` only
for jobs of its default seed list, so the generated key goes in through ``--keys-file`` (any
seed >= 0 of a table-rule case, ``keys_file_problems``; the 436.8 seedext path).

Exit codes: 0 done / all five as expected (``summarize``), 1 an expectation missed
(``summarize``), 2 not judgeable (a fixed input differs, no candidate outside the union, an
output missing or without the keys, the runner did not take the key, an existing ``--out``),
3 error. The stdout's last line is JSON with ``status`` and the output path only.

Usage (dynamics-dev, project root; <m> = <main checkout>/06_analysis):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_dryrun_evidence.py select --out <sel.json>
      --scan-root <m> --main-jsonl <m>/03_hydraulic/coupled/v5/main.jsonl
      --baseline <m>/02_control/j_p3_cause/baseline_221456d
      --dg3 <m>/03_hydraulic/coupled/v5/resume_k1/h6_dg3_v4on.json
      --noise <m>/03_hydraulic/coupled/v5/resume_k1/h8_noise_VB.json
      [--keys-file <m>/02_control/j_p3_cause/j4a_remedy_b06e409e/dryrun_selection_r79_key.txt]
  python -I -B ... run-event --selection <sel.json> --setting VBJ
      --out <dryrun_evidence/event_VBJ.jsonl>
  python -I -B ... summarize --selection <sel.json> --out <summary.json>
      --event VBJ=<jsonl> VBH=<jsonl> VBJ0=<jsonl> --r79 VBJ=<json> VBH=<json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import jp3_baseline_compare as compare  # noqa: E402
import jp3_fixed_inputs as fixed  # noqa: E402
from j_p3_inputs import ROD_READING_EVIDENCE_KEYS  # noqa: E402

JUDGED_BATCHES = ("j9_main", "j9_cases", "j9_case_f", "j9_t8")
RUNTIME_KEYS = ("setting", "mask", "t4h_dir")
EVENT_CANDIDATES = (
    {"case": "R14", "eps": 0.0, "offset_s": 0.025},
    {"case": "R16", "eps": 0.0, "offset_s": 0.0125},
    {"case": "R15", "eps": 0.0, "offset_s": 0.025},
)
"""Event-path rows with rod readings (R12 / R14 .. R16 family) at offsets no batch runs."""
EVENT_SETTINGS = ("VBJ", "VBH", "VBJ0")
R79_SETTINGS = ("VBJ", "VBH")
R79_LEVEL = "L2"
R79_KEY_PATTERN = re.compile(rb'"key"\s*:\s*"((?:cand=[^"#]*#)?L\d+\|s(\d+)\|[^"]*)"')
"""4a-4 1: an r79 key is a ``"key"`` value ``L<level>|s<seed>|...`` (prefix ``cand=...#``)."""
CANDIDATE_PREFIX = re.compile(r"^cand=[^#]*#")
SCAN_SUFFIXES = (".json", ".jsonl")
DRY_SEED_START = 25
"""4a-4 2: the generated key's seed token starts at ``s25`` (above every stored seed)."""
SEED_TOKEN = re.compile(r"^s\d+$")
EXPECTED = {("event", "VBJ"): "equal", ("event", "VBH"): "truth_zero_monitor_positive",
            ("event", "VBJ0"): "equal", ("r79", "VBJ"): "equal",
            ("r79", "VBH"): "truth_zero_monitor_positive"}
"""4a-3 5.1 rows 1 .. 3, 4a-4 3 rows 4 .. 5: equal = 1 = 2 > 0; truth_zero_monitor_positive =
1 = 0 and 2 > 0."""
ASK_AGAIN = "다시 묻기(4a-4 2: the runner did not take the generated key)"
KEYS_FILE_LINE_END = "\r\n"
"""The fixed key file (4a-4 erratum 1, ``DRY_KEYS_FILE_SHA256``) was written by
``Path.write_text`` on Windows, so its one line ends in CRLF; the runner strips line ends
(``r79_L3L4_final.read_keys_file``). Written as bytes so the sha is the same on any OS."""
DG3_RUNNER = "04_scripts/04_hydraulic/coupled/las_t3_dg3.py"
EXIT_DONE, EXIT_MISSED, EXIT_NOT_JUDGEABLE, EXIT_ERROR = 0, 1, 2, 3


class Stop(Exception):
    """A not-judgeable condition (exit 2)."""


@dataclass(frozen=True)
class KeyScan:
    """4a-4 1 scan of the stored r79 keys.

    Attributes:
        keys: Every r79 key found, without its candidate prefix.
        files: (relative path, sha256, r79 keys in it) of every scanned file.
        seed_max: The largest seed token found (None without keys).
    """

    keys: frozenset[str]
    files: tuple[tuple[str, str, int], ...]
    seed_max: int | None
    excluded: tuple[tuple[str, str, int, frozenset[str]], ...] = ()
    """(relative path, sha256, r79 key count, r79 keys) of each file under
    :data:`SCAN_EXCLUDED_FOLDER`; its keys never enter :attr:`keys`."""


SCAN_EXCLUDED_FOLDER = "02_control/j_p3_cause/j9_runs/"
"""Addendum 4a-6 5 G-1 (user decision 2026-11-21): the J-P3 run outputs below
``<scan-root>`` are left out of the key scan (their dry r79 runs carry the dry key itself).
A file is left out when its scan-root relative path, ``/`` separated, starts with this string,
case as it is; nothing else of the scan root is left out."""


def is_scan_excluded(relative: str) -> bool:
    """4a-6 G-1: a scan-root relative ``/`` path under :data:`SCAN_EXCLUDED_FOLDER`."""
    return relative.startswith(SCAN_EXCLUDED_FOLDER)


def normalised_job(job: dict) -> str:
    """4a-3 5.1: ``job`` without the setting and the run keys, as sorted JSON."""
    return json.dumps({k: v for k, v in job.items() if k not in RUNTIME_KEYS}, sort_keys=True)


def plain_key(key: str) -> str:
    """The r79 key without a ``cand=...#`` prefix."""
    return CANDIDATE_PREFIX.sub("", key)


def scan_r79_keys(scan_root: Path) -> KeyScan:
    """Every r79 key of every ``.json`` / ``.jsonl`` under ``scan_root`` (raw bytes, so a file
    of any encoding is read; the key strings hold no escapes). The files under
    :data:`SCAN_EXCLUDED_FOLDER` are recorded apart (sha256, keys) and their keys are not part
    of the scan (4a-6 G-1)."""
    keys: set[str] = set()
    files = []
    excluded = []
    seed_max = None
    for path in sorted(p for p in scan_root.rglob("*") if p.suffix in SCAN_SUFFIXES
                       and p.is_file()):
        relative = path.relative_to(scan_root).as_posix()
        data = path.read_bytes()
        found = R79_KEY_PATTERN.findall(data)
        if is_scan_excluded(relative):
            excluded.append((relative, hashlib.sha256(data).hexdigest(), len(found),
                             frozenset(plain_key(key.decode("utf-8")) for key, _ in found)))
            continue
        for key, seed in found:
            keys.add(plain_key(key.decode("utf-8")))
            seed_max = int(seed) if seed_max is None else max(seed_max, int(seed))
        files.append((relative, hashlib.sha256(data).hexdigest(), len(found)))
    return KeyScan(frozenset(keys), tuple(files), seed_max, tuple(excluded))


def generated_key(base_key: str, scanned: frozenset[str]) -> tuple[str, int]:
    """4a-4 2: the base key with its seed token only set to ``s<n>``, ``n`` from 25 up while the
    key is in the scan.

    Raises:
        Stop: The base key's second token is not a seed token.
    """
    tokens = base_key.split("|")
    if len(tokens) < 3 or not SEED_TOKEN.match(tokens[1]):
        raise Stop(f"base key {base_key!r} has no seed token")
    seed = DRY_SEED_START
    while "|".join([tokens[0], f"s{seed}", *tokens[2:]]) in scanned:
        seed += 1
    return "|".join([tokens[0], f"s{seed}", *tokens[2:]]), seed


def judged_union(main_jsonl: Path, baseline_folder: Path) -> dict:
    """The event-path job union (normalised) of the judged batches and the baseline."""
    import run_v5

    run_v5.P3_HASH_SOURCE_OVERRIDE[0] = main_jsonl
    jobs = {name: {normalised_job(job) for job in run_v5.batch_jobs(name)}
            for name in JUDGED_BATCHES}
    baseline = compare.Baseline(baseline_folder)
    rows = [row for name in baseline.hashes if name.endswith(".jsonl")
            for row in baseline.rows(name)]
    jobs["baseline_221456d"] = {normalised_job(row["job"]) for row in rows}
    return {"event_union": set().union(*jobs.values()),
            "sizes": {name: len(found) for name, found in jobs.items()}}


@dataclass(frozen=True)
class SelectInputs:
    """The ``select`` inputs (stored files, 4a-4 5 fixed)."""

    scan_root: Path
    main_jsonl: Path
    baseline: Path
    dg3: Path
    noise: Path


def fixed_input_problems(inputs: SelectInputs) -> list[str]:
    """4a-4 5 for ``select`` (the baseline SUMS is checked by ``compare.Baseline``)."""
    checks = ((inputs.noise, fixed.NOISE_VB_SHA256, "--noise"),
              (inputs.dg3, fixed.H6_SHA256, "--dg3"),
              (inputs.main_jsonl, fixed.MAIN_JSONL_SHA256, "--main-jsonl"))
    return [problem for path, expected, label in checks
            if (problem := fixed.sha_problem(path, expected, label)) is not None]


def select(inputs: SelectInputs) -> dict:
    """The ``select`` output (module docstring).

    Raises:
        Stop: A fixed input differs, no event candidate outside the union, no r79 key in the
            scan or no base key.
    """
    problems = fixed_input_problems(inputs)
    if problems:
        raise Stop("; ".join(problems))
    union = judged_union(inputs.main_jsonl, inputs.baseline)
    proof = [{"job": job, "in_union": normalised_job(job) in union["event_union"]}
             for job in EVENT_CANDIDATES]
    event_job = next((row["job"] for row in proof if not row["in_union"]), None)
    if event_job is None:
        raise Stop("no event-path candidate outside the judged union (4a-3 5.1: 확인 필요)")
    scan = scan_r79_keys(inputs.scan_root)
    if not scan.keys:
        raise Stop(f"no r79 key under {inputs.scan_root} (4a-4 1: the scan found nothing)")
    dg3_keys = {plain_key(run["key"]) for run in _read_json(inputs.dg3)["results"]}
    base_key = next((plain_key(run["key"]) for run in _read_json(inputs.noise)["results"]
                     if run.get("level") == R79_LEVEL and plain_key(run["key"]) not in dg3_keys),
                    None)
    if base_key is None:
        raise Stop("no L2 noise key outside the Dg-3 135 keys")
    key, seed = generated_key(base_key, scan.keys)
    if seed != DRY_SEED_START:  # 4a-6 G-3 (b): the key outside the run outputs stops
        raise Stop(f"the s{DRY_SEED_START} key of the base key is in the scan outside "
                   f"{SCAN_EXCLUDED_FOLDER} (generated s{seed}; 4a-6 G-3: not judgeable)")
    return {"event_job": event_job, "event_candidates": proof,
            "event_union_sizes": union["sizes"],
            "r79_base_key": base_key, "r79_key": key, "r79_seed": seed,
            "r79_key_in_scan": key in scan.keys, "r79_key_in_dg3": key in dg3_keys,
            "scan": {"root": str(inputs.scan_root), "files_scanned": len(scan.files),
                     "files_with_r79_keys": sum(count > 0 for _, _, count in scan.files),
                     "r79_keys": len(scan.keys), "seed_max": scan.seed_max,
                     "files": [{"path": path, "sha256": digest, "r79_keys": count}
                               for path, digest, count in scan.files],
                     "excluded_folder": SCAN_EXCLUDED_FOLDER,
                     "files_excluded": len(scan.excluded),
                     "excluded": [{"path": path, "sha256": digest, "r79_keys": count,
                                   "has_generated_key": key in found}
                                  for path, digest, count, found in scan.excluded]}}


def _commands(event_job: dict, keys_file: Path) -> dict:
    """The five commands (4a-3 5.1, 4a-4 3)."""
    script = "04_scripts/04_hydraulic/coupled/jp3_dryrun_evidence.py"
    commands = {f"event_{setting}": f"python -I -B {script} run-event --selection <sel.json> "
                f"--setting {setting} --out dryrun_evidence/event_{setting}.jsonl"
                for setting in EVENT_SETTINGS}
    for setting in R79_SETTINGS:
        commands[f"r79_{setting}"] = (
            f"env {' '.join(r79_environment(setting))} python -I -B {DG3_RUNNER} <root> run "
            f"dryrun_evidence/r79_{setting}.json --levels {R79_LEVEL} --keys-file {keys_file} "
            "--workers 1")
    commands["event_job"] = event_job
    return commands


def r79_environment(setting: str) -> list[str]:
    """4a-4 3: the T-JR-12 environment of one r79 dry run (``NAME=value`` words)."""
    words = [f"R79_V5_SETTING={setting}", f"R79_T4H_DIR=dryrun_evidence/{setting}_t4h",
             "LAS_T3_DG3_LAS=on", "LAS_T3_DG3_K1=on", "LAS_T3_DG3_P3=on"]
    if setting == "VBJ":
        words.append("R79_ROD_MODEL=plant_truth")
    return words


def run_event(selection: dict, setting: str, out: Path) -> None:
    """One event-path run of the selected job (a simulation: the main session runs it)."""
    import run_v5

    job = {**selection["event_job"], "setting": setting}
    with get_context("spawn").Pool(1, maxtasksperchild=1) as pool:
        record = pool.apply(run_v5.run_one, (job,))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, default=lambda v: v.item() if hasattr(v, "item")
                              else str(v)) + "\n", encoding="utf-8")


def evidence_of(record: dict) -> dict:
    """Only the error flag and the two evidence keys of one output line / r79 result."""
    hydraulics = record.get("hydraulics_record") or {}
    return {"error": "error" in record,
            **{key: hydraulics.get(key) for key in ROD_READING_EVIDENCE_KEYS}}


def meets(expectation: str, evidence: dict) -> bool | None:
    """The table's expectation of one run (None: the keys are missing)."""
    truth, monitor = (evidence.get(key) for key in ROD_READING_EVIDENCE_KEYS)
    if evidence["error"] or truth is None or monitor is None:
        return None
    if expectation == "equal":
        return truth == monitor > 0
    return truth == 0 and monitor > 0


def key_taken(selection: dict, record: dict) -> bool:
    """4a-4 2: the r79 runner ran the generated key (prefix-free key and seed record)."""
    return (plain_key(str(record.get("key", ""))) == selection["r79_key"]
            and record.get("seed_index") == selection["r79_seed"])


def keys_file_problems(selection: dict, meta: dict) -> list[str]:
    """4a-4 erratum 1: the r79 output meta's ``keys_file`` is the selection's key file (sha256
    = the selection record = the fixed value) with one key."""
    record = (meta or {}).get("keys_file") or {}
    expected = (selection.get("r79_keys_file") or {}).get("sha256")
    problems = []
    if expected != fixed.DRY_KEYS_FILE_SHA256:
        problems.append(f"selection key file sha256 {str(expected)[:12]} is not the fixed one")
    if record.get("sha256") != expected:
        problems.append(f"r79 meta keys_file.sha256 {str(record.get('sha256'))[:12]} is not "
                        "the selection's")
    if record.get("n_keys") != 1:
        problems.append(f"r79 meta keys_file.n_keys {record.get('n_keys')!r}, 1 expected")
    return problems


RECORD_KEY_PATHS = (("hydraulics_record", "relock_step_over_1bar_count"),
                    ("hydraulics_record", "p1_retract_seed_log_columns"),
                    ("lock_window_alignment", "n_late_fallback"))
"""Prelaunch audit R-b (a record, no value read): the keys T-JR-14 / T-JR-15 read later."""


def record_keys_present(record: dict) -> dict[str, bool]:
    """Whether each :data:`RECORD_KEY_PATHS` key is on the r79 line (record only)."""
    present = {}
    for outer, inner in RECORD_KEY_PATHS:
        block = record.get(outer)
        present[f"{outer}.{inner}"] = isinstance(block, dict) and inner in block
    return present


def summarize(selection: dict, event_files: dict[str, Path],
              r79_files: dict[str, Path]) -> tuple[dict, int]:
    """The ``summarize`` output and its exit code."""
    rows, code = [], EXIT_DONE
    for (path_kind, setting), expectation in EXPECTED.items():
        files = event_files if path_kind == "event" else r79_files
        path = files.get(setting)
        if path is None or not path.is_file():
            rows.append({"run": f"{path_kind}_{setting}", "output": "missing"})
            code = EXIT_NOT_JUDGEABLE
            continue
        document = None if path_kind == "event" else _read_json(path)
        records = _read_lines(path) if document is None else document["results"]
        row = {"run": f"{path_kind}_{setting}", "expected": expectation,
               "evidence": [evidence_of(record) for record in records]}
        row["meets"] = [meets(expectation, item) for item in row["evidence"]]
        if document is not None:
            row["record_keys_present"] = [record_keys_present(record) for record in records]
            row["key_taken"] = [key_taken(selection, record) for record in records]
            row["keys_file_problems"] = keys_file_problems(selection, document.get("meta"))
            if not all(row["key_taken"]) or len(records) != 1 or row["keys_file_problems"]:
                row["stop"] = ASK_AGAIN
        rows.append(row)
        if len(records) != 1 or None in row["meets"] or "stop" in row:
            code = EXIT_NOT_JUDGEABLE
        elif not all(row["meets"]) and code == EXIT_DONE:
            code = EXIT_MISSED
    return {"rows": rows}, code


def _read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _pairs(values: list[str]) -> dict[str, Path]:
    """``SETTING=path`` arguments."""
    out = {}
    for value in values:
        setting, _, path = value.partition("=")
        out[setting] = Path(path)
    return out


EXIT_TABLE = """exit codes (addendum 4a-5 5.1):
  0  done           select / run-event written; summarize: all five as expected
  1  missed         summarize: an expectation missed; stop
  2  not_judgeable  a fixed input differs, no candidate outside the union, an output missing
                    or without the keys, the runner did not take the key, an existing --out
  3  error          a tool error (unexpected input: file missing, broken JSON)"""


def _parser() -> argparse.ArgumentParser:
    raw_help = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], epilog=EXIT_TABLE,
                                     formatter_class=raw_help)
    commands = parser.add_subparsers(dest="command", required=True)
    chosen = commands.add_parser("select", epilog=EXIT_TABLE, formatter_class=raw_help)
    chosen.add_argument("--out", type=Path, required=True)
    for name in ("scan-root", "main-jsonl", "baseline", "dg3", "noise"):
        chosen.add_argument(f"--{name}", type=Path, required=True)
    chosen.add_argument("--keys-file", type=Path, default=None,
                        help="the r79 key file the commands name (default <out stem>_r79_key.txt "
                             "next to --out); an existing file must hold the same key (4a-4 "
                             "erratum 1: the repository copy in j4a_remedy_b06e409e/)")
    event = commands.add_parser("run-event", epilog=EXIT_TABLE, formatter_class=raw_help)
    event.add_argument("--selection", type=Path, required=True)
    event.add_argument("--setting", choices=EVENT_SETTINGS, required=True)
    event.add_argument("--out", type=Path, required=True)
    summary = commands.add_parser("summarize", epilog=EXIT_TABLE, formatter_class=raw_help)
    summary.add_argument("--selection", type=Path, required=True)
    summary.add_argument("--out", type=Path, required=True)
    summary.add_argument("--event", nargs="*", default=[])
    summary.add_argument("--r79", nargs="*", default=[])
    return parser


def keys_file_of(out: Path) -> Path:
    """The one-line r79 key file ``select`` writes next to its output."""
    return out.with_name(f"{out.stem}_r79_key.txt")


def place_keys_file(keys_file: Path, key: str) -> dict:
    """The one-line key file of ``key`` at ``keys_file``: written when absent; an existing file
    (the repository copy of 4a-4 erratum 1) must hold exactly that line. Its sha256 must be the
    fixed :data:`jp3_fixed_inputs.DRY_KEYS_FILE_SHA256`.

    Raises:
        Stop: An existing file of other content, or another sha256 (the selection changed).
    """
    content = (key + KEYS_FILE_LINE_END).encode("utf-8")
    if keys_file.exists():
        if keys_file.read_bytes() != content:
            raise Stop(f"{keys_file} exists with another key (never overwritten)")
        reused = True
    else:
        keys_file.parent.mkdir(parents=True, exist_ok=True)
        keys_file.write_bytes(content)
        reused = False
    digest = fixed.file_sha256(keys_file)
    if digest != fixed.DRY_KEYS_FILE_SHA256:
        raise Stop(f"key file sha256 {digest[:12]} is not the fixed "
                   f"{fixed.DRY_KEYS_FILE_SHA256[:12]} (4a-4 erratum 1)")
    return {"path": str(keys_file), "sha256": digest, "reused_existing_file": reused}


def _select_command(args: argparse.Namespace) -> dict:
    inputs = SelectInputs(args.scan_root, args.main_jsonl, args.baseline, args.dg3, args.noise)
    report = select(inputs)
    keys_file = args.keys_file or keys_file_of(args.out)
    report["r79_keys_file"] = place_keys_file(keys_file, report["r79_key"])
    report["commands"] = _commands(report["event_job"], keys_file)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error(f"{args.out} exists (a new output never overwrites one)")
    try:
        if args.command == "select":
            report, code = _select_command(args), EXIT_DONE
        elif args.command == "run-event":
            run_event(_read_json(args.selection), args.setting, args.out)
            print(json.dumps({"status": "done", "out": str(args.out)}))
            return EXIT_DONE
        else:
            report, code = summarize(_read_json(args.selection), _pairs(args.event),
                                     _pairs(args.r79))
    except (Stop, compare.NotJudgeable) as exc:
        report, code = {"stop": str(exc)}, EXIT_NOT_JUDGEABLE
    except compare.TOOL_ERRORS as exc:
        report, code = {"error": f"{type(exc).__name__}: {exc}"}, EXIT_ERROR
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1, default=float), encoding="utf-8")
    status = {EXIT_DONE: "done", EXIT_MISSED: "missed", EXIT_NOT_JUDGEABLE: "not_judgeable",
              EXIT_ERROR: "error"}[code]
    print(json.dumps({"status": status, "out": str(args.out)}))
    return code


if __name__ == "__main__":
    sys.exit(main())
