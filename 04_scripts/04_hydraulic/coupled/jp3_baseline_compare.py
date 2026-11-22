"""436.9 edition 4a J4a-9: the re-implementation's case replays against the clean ``221456d``
baseline (``jp3_remedy_spec.md`` 5.7 P4-1 .. P4-4, P4-9, 13.1; addendum 4a-1 section 1;
addendum 4a-2 sections 2, 3 and table 4: J4a-9 R1 .. R4, B2, B3, X11).

Checks (every problem is collected; the status: failed > setting defect > not judgeable):

1. Baseline: the sha256 of ``SHA256SUMS`` is :data:`BASELINE_SUMS_SHA256`; every listed file
   has its hash; no baseline file outside the list is opened (CRLF lines: ``\\r`` cut). A
   broken baseline stops at once (not judgeable).
2. Pairs: every baseline row (``j9_cases.jsonl``, ``cd.jsonl``) has exactly one new row of the
   same job. Setting defects (13.6, 4a-2 R3 / X11 / B2): a ``*_X11`` row in the compared set; a
   new revision 5 row (VBG5 included) without the sealed identity (``spec_edition``,
   ``carry_end_rule``, ``retract_start_rule``); a new row whose P4 evidence does not fit its
   options (:func:`rod_evidence_problems`, ① = k x ② with the k of addendum 4a-8 2); a
   VBJ / LSJ1 .. 4 row (a J-P3 line) whose evidence is not ① = k x ② > 0 (event path) or
   ① = ② = 0 (declared head-only; :func:`judged_line_evidence_problems`, addendum 4a-7
   erratum 1 9).
3. P4-1: ``commands_sha256`` equal per pair (T8).
4. P4-2 per read (T4h npz, 4a-2 section 2): ``jp3_t_s`` of equal length and value; used bound
   new >= baseline - 1 Pa and the same NaN pattern; class changes only EXT -> CARRY_ext and
   RET -> CARRY_ret; every raised read explained by the chain of 4a-2 2.2
   (:func:`chain_explanation`). A revision 5 pair (B, D, E) without one of the input columns is
   not judgeable (R4); a revision 4 pair (A, C) without a trace is "not applicable".
5. Judged rows (``jp3_judged_row`` of VBJ, LSJ1 .. 4 only, R2) > 0; per class reads > 0 (lock,
   hold, carry_ext, carry_ret, ext) over the revision 5 rows.
6. P4-3a on VBJ, LSJ1 .. 4: the J-P3a / b / c judged keys 0 and ``relock_step_over_1bar_count``
   0; a missing key is not judgeable (R2), never 0.
7. P4-4: ``p1_retract_seed_count`` and the largest seed step equal to the baseline (else
   failed); the seed net force (4a-2 3.4): every ``p1_retract_seed_log`` row has
   ``|net_force_seed_step_N|`` <= 1 N (else failed). Not judgeable: the column missing, rows !=
   count, zero rows, an ``m2_shift_clipped`` row.
8. P4-9: ``retract_tracker_dominated_reads`` 0 and an empty stretch log (no fallback leg); a
   revision 5 row without either key is not judgeable, never 0 (prelaunch audit M-5).

Exit codes and ``status`` (the J4a-9 rows of 13.1 and 4a-2 R3):

======  =================  ===================================================================
exit    status             meaning
======  =================  ===================================================================
0       ``pass``           every check passes
1       ``failed``         a prediction (P4-1 .. P4-4, P4-9) failed; it outranks the other
                           kinds, which stay in the report (edition 5 erratum 2 2-10)
2       ``not_judgeable``  no failure, no defect: baseline, pairing, a missing column / key,
                           zero judged rows or seed rows, an ``m2_shift_clipped`` seed row
                           (13.1, 4a-2 2.2 / 3.4)
2       ``setting_defect`` no failure: a test-only setting, a non-default identity or P4
                           evidence (13.6, 4a-2 R3, B2, X11); it outranks not_judgeable
3       ``error``          an unexpected input error (file missing, malformed JSON)
======  =================  ===================================================================

The stdout's last line is JSON with ``status``, the problem counts and the report path only.

Usage (python-dev or dynamics-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_baseline_compare.py <baseline folder>
      --new <jsonl> [<jsonl> ...] --out <report.json>
The T4h of a ``--new`` row is ``<jsonl folder>/<jsonl stem>_t4h/<t4h_file>`` (run_v5 writes the
name only), as the baseline's own rows; the working folder plays no part.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import jp3_fixed_inputs as fixed  # noqa: E402
from j_p3_inputs import ROD_READING_EVIDENCE_KEYS, harness_head_only_declared  # noqa: E402

BASELINE_SUMS_SHA256 = fixed.BASELINE_SUMS_SHA256
"""Edition 4a 13.1 / addendum 4a-1: the sealed baseline list."""
SPEC_EDITION = "8be9de22"
DEFAULT_IDENTITY = {"spec_edition": SPEC_EDITION, "carry_end_rule": "inherit_when_gate_shut",
                    "retract_start_rule": "with_tracker"}
SPEC_EDITION_V5 = "fe6f5844"
"""Edition 5 (``jp3_remedy_spec_v5.md``): the ``spec_edition`` of a ③ revision 6 record."""
HOLD_REVISIONS = (5, 6)
"""③ hold revisions (``extend_start_bound.HOLD_REVISIONS``); a revision 6 row is never read
as a revision 4 or 5 row (edition 5 4.6)."""
IDENTITY_OF_REVISION = {5: DEFAULT_IDENTITY,
                        6: {**DEFAULT_IDENTITY, "spec_edition": SPEC_EDITION_V5}}
"""The sealed identity of each hold revision's record (13.6, edition 5 4.6)."""
BASELINE_ROW_FILES = ("j9_cases.jsonl", "cd.jsonl")
JUDGED_SETTINGS = ("VBJ", "LSJ1", "LSJ2", "LSJ3", "LSJ4")
JUDGED_KEYS = ("jp3a_breach_reads", "jp3b_breach_over_tol_reads", "jp3c_breach_reads")
RELOCK_KEY = "relock_step_over_1bar_count"
RETRACT_TRACKER_READS_KEY = "retract_tracker_dominated_reads"
RETRACT_TRACKER_LOG_KEY = "retract_tracker_stretch_log"
"""P4-9 keys of a revision 5 record (``extend_start_bound`` writes both on every rev 5 row)."""
CLASS_NAMES = ("lock", "hold", "carry_ext", "carry_ret", "ext", "ret")
REQUIRED_CLASSES = ("lock", "hold", "carry_ext", "carry_ret", "ext")
LOCK_CLASSES = ("lock", "hold")
ALLOWED_CLASS_CHANGES = (("ext", "carry_ext"), ("ret", "carry_ret"))
RETRACT_TRACKER_SOURCE = "retract_tracker"
BOUND_TOLERANCE_PA = 1.0
"""4a-2 2.2 ``epsilon_p`` (the J-P3a allowance)."""
LOOKBACK_S = 0.3
"""4a-2 2.2 ``T_lb`` = ``two_pressure.LOCKED_START_LOOKBACK_S`` (fixed by the rule here)."""
LOOKBACK_SLACK_S = 1.0e-6
NET_FORCE_TOLERANCE_N = 1.0
SEED_FORCE_COLUMN = "net_force_seed_step_N"
SEED_CLIPPED_COLUMN = "m2_shift_clipped"
NEW_TRACE_COLUMNS = ("jp3_t_s", "jp3_class", "jp3_class_names", "jp3_used_bound_Pa",
                     "jp3_ext_bound_Pa", "jp3_model_bound_source", "jp3_source_names",
                     "jp3_model_bound_inherited")
BASELINE_TRACE_COLUMNS = ("jp3_t_s", "jp3_class", "jp3_used_bound_Pa", "jp3_ext_bound_Pa")
MAX_UNEXPLAINED_ROWS = 50
TEST_ONLY_SUFFIX = "_X11"
STATUS_PASS, STATUS_FAILED = "pass", "failed"
STATUS_NOT_JUDGEABLE, STATUS_SETTING_DEFECT, STATUS_ERROR = (
    "not_judgeable", "setting_defect", "error")
EXIT_PASS, EXIT_FAILED, EXIT_NOT_JUDGEABLE, EXIT_ERROR = 0, 1, 2, 3
TOOL_ERRORS = (Exception,)
"""Every unexpected error of the J-P3 judge tools (``KeyboardInterrupt`` and ``SystemExit`` are
not ``Exception``): status ``error``, exit 3 (addendum 4a-5 5.1: a tool error, not a judgement;
an uncaught one would leave Python's exit 1 = failed; prelaunch audit N-3: ``RuntimeError``,
``ZeroDivisionError``, ``StopIteration`` too)."""
EXIT_TABLE = """exit codes (addendum 4a-5 5.1, the J-P3 judge tools):
  0  pass             passed (a record tool: written as expected)
  1  failed           a prediction or judgement failed (base-judge-compare: grades differ,
                      a record), whatever else was found (erratum 2 2-10); stop
  2  not_judgeable /  no failure: not judgeable, a setting defect, or an argument error (an
     setting_defect   existing --out is refused); stop and find the cause
  3  error            a tool error (unexpected input: file missing, broken JSON); not a
                      judgement"""
STATUS_EXIT = {STATUS_PASS: EXIT_PASS, STATUS_FAILED: EXIT_FAILED,
               STATUS_NOT_JUDGEABLE: EXIT_NOT_JUDGEABLE,
               STATUS_SETTING_DEFECT: EXIT_NOT_JUDGEABLE, STATUS_ERROR: EXIT_ERROR}


class NotJudgeable(Exception):
    """Baseline or pairing broken (13.1: stop)."""


class Problems:
    """The three kinds of findings of one comparison (status order, edition 5 erratum 2 2-10:
    failed > defect > not judgeable; a failure never hides the other kinds, all are kept)."""

    def __init__(self) -> None:
        self.setting_defects: list[str] = []
        self.not_judgeable: list[str] = []
        self.failures: list[str] = []

    def status(self) -> str:
        if self.failures:
            return STATUS_FAILED
        if self.setting_defects:
            return STATUS_SETTING_DEFECT
        if self.not_judgeable:
            return STATUS_NOT_JUDGEABLE
        return STATUS_PASS

    def as_dict(self) -> dict:
        return {"setting_defects": self.setting_defects, "not_judgeable": self.not_judgeable,
                "failures": self.failures}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Baseline:
    """The sealed folder: only files of ``SHA256SUMS`` are opened, each hash checked."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        sums = folder / "SHA256SUMS"
        if file_sha256(sums) != BASELINE_SUMS_SHA256:
            raise NotJudgeable(f"{sums}: sha256 is not {BASELINE_SUMS_SHA256[:12]}")
        self.hashes: dict[str, str] = {}
        for line in sums.read_bytes().decode("utf-8").split("\n"):
            line = line.rstrip("\r")  # committed -text: CRLF lines (addendum 4a-1)
            if not line:
                continue
            digest, name = line.split(maxsplit=1)
            self.hashes[name.lstrip("*")] = digest
        for name, digest in self.hashes.items():
            if file_sha256(folder / name) != digest:
                raise NotJudgeable(f"baseline {name}: hash differs from SHA256SUMS")

    def path(self, name: str) -> Path:
        """A listed file; anything else is refused (addendum 4a-1)."""
        name = name.replace("\\", "/")
        if name not in self.hashes:
            raise NotJudgeable(f"baseline file {name} is not in SHA256SUMS")
        return self.folder / name

    def rows(self, name: str) -> list[dict]:
        return _read_rows(self.path(name))

    def t4h(self, row_file: str, record: dict) -> Path:
        stem = Path(row_file).stem
        return self.path(f"{stem}_t4h/{Path(record['t4h_file']).name}")


def _read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


NEW_T4H_PATH_KEY = "_new_t4h_path"
"""In-memory key of a ``--new`` row: its T4h file (never written; ``t4h_file`` stays as run)."""


def t4h_path_of(rows_file: Path, record: dict) -> Path:
    """The T4h file of a run_v5 row: ``<rows file folder>/<rows file stem>_t4h/<t4h_file name>``
    (run_v5 writes the name only, ``run_v5.py`` ``t4h_file``; the same rule as
    :meth:`Baseline.t4h`, j9 step 4a diagnosis 2026-11-21: the name was read from the CWD)."""
    return rows_file.with_name(f"{rows_file.stem}_t4h") / Path(record["t4h_file"]).name


def read_new_rows(paths: list[Path]) -> list[dict]:
    """The ``--new`` rows, each with its T4h path under :data:`NEW_T4H_PATH_KEY` (rows without
    ``t4h_file`` are left as they are: the compare reports them)."""
    rows = []
    for path in paths:
        for record in _read_rows(path):
            if record.get("t4h_file"):
                record[NEW_T4H_PATH_KEY] = str(t4h_path_of(Path(path), record))
            rows.append(record)
    return rows


def _new_t4h_path(record: dict) -> Path:
    """A ``--new`` row's T4h (:func:`read_new_rows`); a row given directly to :func:`compare`
    without that key keeps its ``t4h_file`` path as it is."""
    return Path(record.get(NEW_T4H_PATH_KEY) or record["t4h_file"])


def _job_key(record: dict) -> str:
    return json.dumps(record["job"], sort_keys=True)


def _check(record: dict) -> dict:
    return (record.get("hydraulics_record") or {}).get("extend_bound_check") or {}


def _is_revision_5(record: dict) -> bool:
    """A hold revision row (``rule_revision`` 5 or 6, edition 5 4.6): the revision 5 rules of
    this tool apply to both, each with its own sealed identity (:func:`identity_problems`)."""
    return _check(record).get("rule_revision") in HOLD_REVISIONS


def pair_rows(baseline: Baseline, new_rows: list[dict],
              problems: Problems) -> list[tuple[str, dict, dict]]:
    """(baseline row file, baseline record, new record) per baseline row; a test-only
    ``*_X11`` row in the compared set is a setting defect (13.6, 4a-2 X11).

    Raises:
        NotJudgeable: A baseline row without exactly one new row.
    """
    new_by_key: dict[str, list[dict]] = {}
    for record in new_rows:
        setting = record["job"]["setting"]
        if setting.endswith(TEST_ONLY_SUFFIX):
            problems.setting_defects.append(f"test-only setting {setting} in the compared set")
            continue
        new_by_key.setdefault(_job_key(record), []).append(record)
    pairs = []
    for row_file in BASELINE_ROW_FILES:
        for old in baseline.rows(row_file):
            matches = new_by_key.get(_job_key(old), [])
            if len(matches) != 1:
                raise NotJudgeable(f"{old['job']['setting']}: {len(matches)} new rows")
            pairs.append((row_file, old, matches[0]))
    return pairs


HEAD_ONLY_KEY = "head_only_declared"


def is_head_only_line(line: dict, meta: dict | None = None) -> bool:
    """Addendum 4a-7 1.1 with erratum 1 3: is a J-P3 input line a declared head-only run?

    A noise-run result line (it has ``level``) is an event-path line (both pressures read). A
    harness batch line: the T4h meta ``head_only_declared``, else the line's own, else the
    steady path of its ``verdict_cases`` case; a line still undecided is an event-path line.

    Args:
        line: The result line (``job``, maybe ``level`` / ``head_only_declared``).
        meta: The ``meta_json`` of the line's T4h (None = no T4h read).
    """
    if "level" in line:
        return False
    if meta is not None and meta.get(HEAD_ONLY_KEY) is not None:
        return bool(meta[HEAD_ONLY_KEY])
    if line.get(HEAD_ONLY_KEY) is not None:
        return bool(line[HEAD_ONLY_KEY])
    return harness_head_only_declared({"job": line.get("job") or {}})


def judged_line_evidence_problems(record: dict | None, is_declared: bool,
                                  multiplier: int = 1) -> list[str]:
    """Addendum 4a-7 erratum 1 9 with 4a-8 2: the P4 evidence of a J-P3 judged-setting line
    (VBJ, LSJ1 .. 4). An event-path line has ① truth reads = k x ② monitor rod reads > 0
    (``multiplier`` = k, :func:`evidence_multiplier`), a declared head-only line ① = ② = 0; a
    missing or non-integer evidence key is a setting defect too (never read as 0).

    Args:
        record: The line's ``hydraulics_record``.
        is_declared: :func:`is_head_only_line` of the line.
        multiplier: k of the line's run path (1 but on the r79 G8 path).
    """
    record = record or {}
    values = [record.get(key) for key in ROD_READING_EVIDENCE_KEYS]
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in values):
        return [f"J-P3 judged line: P4 evidence keys {list(ROD_READING_EVIDENCE_KEYS)} missing "
                "or not integers (erratum 1 9)"]
    truth_calls, monitor_reads = values
    if is_declared:
        if truth_calls or monitor_reads:
            return [f"J-P3 judged line declared head-only with rod reads ({truth_calls} truth, "
                    f"{monitor_reads} monitor; 0 and 0 needed, erratum 1 9)"]
        return []
    if monitor_reads <= 0 or truth_calls != multiplier * monitor_reads:
        return [f"J-P3 judged event line: {truth_calls} truth readings, {monitor_reads} monitor "
                f"rod reads (k = {multiplier}: truth = k x monitor > 0 needed, erratum 1 9, "
                "4a-8 2)"]
    return []


R79_KEY = re.compile(r"^L\d+[A-Za-z]*\|s\d+\|")
"""Addendum 4a-8 2: an r79 line's key (``L<level>|s<seed>|...``, ``cand=...#`` cut first);
edition 5 X-3: the level token is ``L`` and a digit then letters (``L2``, ``L2nocal``,
``L2imuideal``)."""
CANDIDATE_PREFIX = re.compile(r"^cand=[^#]*#")
DOUBLE_READ_FAMILY = "g8"
"""4a-8 2: the r79 G8 path reads the P4 truth twice per control period (the case step,
``r79_sensor_screen.py:844``, and the sensor delivery, ``:277``): k = 2."""


def evidence_multiplier(line: dict) -> int:
    """4a-8 2: k of a result line - 2 for an r79 line whose key's third token is ``g8``, 1 for
    every other line (other r79 families, run_v5 batch lines without an r79 key)."""
    key = line.get("key")
    if not isinstance(key, str):
        return 1
    plain = CANDIDATE_PREFIX.sub("", key)
    if not R79_KEY.match(plain):
        return 1
    return 2 if plain.split("|")[2] == DOUBLE_READ_FAMILY else 1


def rod_evidence_problems(record: dict | None, options: dict | None,
                          multiplier: int = 1) -> list[str]:
    """Addendum 4a-2 B2 with 4a-8 2 (k): why a result line's P4 evidence does not fit its
    options. With ``rod_reading_truth`` ① = k x ② > 0, without it ① = 0; a missing key is a
    setting defect (never read as 0). ``j_p3_inputs.rod_reading_evidence_problems`` is the
    same rule with k = 1; the judge tools use this one (4a-8 6.1: ``j_p3_inputs`` is in the
    runner's import closure and stays unchanged).

    Args:
        record: The line's ``hydraulics_record``.
        options: The line's ``hydraulic_options`` (None = none).
        multiplier: :func:`evidence_multiplier` of the line.
    """
    record = record or {}
    missing = [key for key in ROD_READING_EVIDENCE_KEYS if key not in record]
    if missing:
        return [f"P4 evidence keys missing: {missing}"]
    truth_calls, monitor_reads = (int(record[key]) for key in ROD_READING_EVIDENCE_KEYS)
    if (options or {}).get("rod_reading_truth"):
        if monitor_reads < 1 or truth_calls != multiplier * monitor_reads:
            return [f"rod_reading_truth: {truth_calls} truth readings, {monitor_reads} monitor "
                    f"rod reads (k = {multiplier}: truth = k x monitor > 0 needed)"]
        return []
    if truth_calls != 0:
        return [f"P4 off but {truth_calls} truth readings"]
    return []


def line_evidence_problems(line: dict) -> list[str]:
    """:func:`rod_evidence_problems` of a whole result line (its own k)."""
    return rod_evidence_problems(line.get("hydraulics_record"), line.get("hydraulic_options"),
                                 evidence_multiplier(line))


def judge_rows_problems(label: str, lines: list[dict], judge: dict,
                        excused_keys: frozenset[str] = frozenset()) -> list[str]:
    """Addendum 4a-8 5: an r79 judge file grades every input line - ``runs`` = the lines
    (count and plain-key set), ``unmatched`` 0, ``errors`` 0; else not judgeable (13.2: zero
    judged rows is never a pass).

    Args:
        label: Name of the judge file in the messages.
        lines: The judged Dg-3 lines (L2 / L3 results).
        judge: The r79 judge file document.
        excused_keys: Plain keys of lines judged elsewhere as they are (the T-JR-14
            ``LockWindowMismatchError`` failure lines, prelaunch audit N-1): left out of the
            expected rows, and their ``errors`` entries do not count.
    """
    runs = judge.get("runs")
    unmatched, errors = judge.get("unmatched"), judge.get("errors")
    if not isinstance(runs, list) or not isinstance(unmatched, list) or not isinstance(errors,
                                                                                    list):
        return [f"{label}: no runs / unmatched / errors lists (4a-8 5)"]
    errors = [item for item in errors
              if CANDIDATE_PREFIX.sub("", str((item or {}).get("key"))) not in excused_keys]
    lines = [line for line in lines
             if CANDIDATE_PREFIX.sub("", str(line.get("key"))) not in excused_keys]
    problems = []
    expected = {CANDIDATE_PREFIX.sub("", str(line.get("key"))) for line in lines}
    graded = [CANDIDATE_PREFIX.sub("", str(run.get("key"))) for run in runs]
    if len(graded) != len(lines) or set(graded) != expected:
        problems.append(f"{label}: {len(graded)} judged rows of {len(set(graded) & expected)} "
                        f"input keys, {len(lines)} input lines expected (4a-8 5)")
    if unmatched or errors:
        problems.append(f"{label}: {len(unmatched)} unmatched, {len(errors)} error lines, "
                        "0 and 0 needed (4a-8 5)")
    return problems


def identity_problems(record: dict) -> list[str]:
    """13.6 / 4a-2 R3: a new revision 5 row (VBG5 included) of the sealed edition with the
    default rules, a revision 6 row likewise with the edition 5 ``spec_edition`` (4.6);
    revision 4 rows have no identity."""
    if not _is_revision_5(record):
        return []
    check = _check(record)
    expected = IDENTITY_OF_REVISION[check.get("rule_revision")]
    return [f"{record['job']['setting']}: {key} {check.get(key)!r}"
            for key, value in expected.items() if check.get(key) != value]


# --- P4-2 (addendum 4a-2 section 2) ---------------------------------------------------------

def _lock_segments(is_lock: np.ndarray) -> list[tuple[int, int]]:
    """Maximal runs ``[a, b]`` of lock / hold reads of one leg."""
    segments, start = [], None
    for read, locked in enumerate(is_lock):
        if locked and start is None:
            start = read
        elif not locked and start is not None:
            segments.append((start, read - 1))
            start = None
    if start is not None:
        segments.append((start, len(is_lock) - 1))
    return segments


def chain_explanation(t_s: np.ndarray, is_lock: np.ndarray, is_tracker: np.ndarray,
                      is_inherited: np.ndarray, is_tracker_raised: np.ndarray) -> list[str | None]:
    """4a-2 2.2 chain mark ``C_k`` of one leg's reads, as the reason it holds.

    Args:
        t_s: Read times (ascending).
        is_lock: New class lock or hold.
        is_tracker: ``S_k``: a lock read whose source is ``retract_tracker``.
        is_inherited: ``jp3_model_bound_inherited`` of the read.
        is_tracker_raised: ``E_k``: ``jp3_ext_bound_Pa`` new > baseline + 1 Pa (NaN = False).

    Returns:
        Per read None (``C_k`` false) or the reason: ``"stretch_source"`` (i),
        ``"lookback"`` (ii), ``"inherit"`` (iii) for the reads of a stretch, ``"tracker_chain"``
        for a read outside a stretch (step 2).
    """
    count = len(t_s)
    reasons: list[str | None] = [None] * count
    segment_end = dict(_lock_segments(is_lock))
    previous_segment_reason: str | None = None
    read = 0
    while read < count:
        if not is_lock[read]:
            previous = reasons[read - 1] if read > 0 else None
            reasons[read] = "tracker_chain" if is_tracker_raised[read] and previous else None
            read += 1
            continue
        start, end = read, segment_end[read]
        reason = _segment_reason(t_s, is_lock, is_tracker, is_inherited, reasons, start, end,
                                 previous_segment_reason)
        for inside in range(start, end + 1):
            reasons[inside] = reason
        previous_segment_reason = reason
        read = end + 1
    return reasons


def _segment_reason(t_s, is_lock, is_tracker, is_inherited, reasons, start: int, end: int,
                    previous_segment_reason: str | None) -> str | None:
    """Step 1 of 4a-2 2.2 for the stretch ``[start, end]``: (i), (ii), (iii) in this order."""
    if is_tracker[start:end + 1].any():
        return "stretch_source"
    earliest_s = t_s[start] - LOOKBACK_S - LOOKBACK_SLACK_S
    for before in range(start - 1, -1, -1):
        if t_s[before] < earliest_s:
            break
        if not is_lock[before] and reasons[before] is not None:
            return "lookback"
    if is_inherited[start:end + 1].any() and previous_segment_reason is not None:
        return "inherit"
    return None


def _codes(names: np.ndarray, wanted: tuple[str, ...]) -> list[int]:
    listed = [str(name) for name in names.tolist()]
    return [listed.index(name) for name in wanted if name in listed]


def _check_columns(path: Path, data, columns: tuple[str, ...]) -> None:
    missing = [column for column in columns if column not in data.files]
    if missing:
        raise NotJudgeable(f"{path.name}: no {missing} (4a-2 2.2 / R4)")


def compare_reads(old_npz: Path, new_npz: Path, is_revision_5_pair: bool) -> dict:
    """Step 4 for one pair (module docstring).

    Raises:
        NotJudgeable: A revision 5 pair without the input columns, or another read time base.
    """
    with np.load(old_npz, allow_pickle=False) as old, np.load(new_npz, allow_pickle=False) as new:
        if not is_revision_5_pair and "jp3_t_s" not in old.files:
            return {"has_trace": False, "p4_2": "not_applicable (revision 4 pair, no trace)"}
        _check_columns(old_npz, old, BASELINE_TRACE_COLUMNS)
        _check_columns(new_npz, new, NEW_TRACE_COLUMNS)
        t_old, t_new = old["jp3_t_s"], new["jp3_t_s"]
        if t_old.shape != t_new.shape or not np.array_equal(t_old, t_new):
            raise NotJudgeable(f"{new_npz.name}: jp3_t_s differs from the baseline")
        if ("jp3_class_names" in old.files
                and old["jp3_class_names"].tolist() != new["jp3_class_names"].tolist()):
            raise NotJudgeable(f"{new_npz.name}: class names differ from the baseline")
        arrays = {name: new[name] for name in NEW_TRACE_COLUMNS}
        baseline = {name: old[name] for name in BASELINE_TRACE_COLUMNS}
    return _read_counts(arrays, baseline)


def _read_counts(new: dict, old: dict) -> dict:
    """P4-2 counts of one pair (4a-2 2.3 columns)."""
    used_new, used_old = new["jp3_used_bound_Pa"], old["jp3_used_bound_Pa"]
    with np.errstate(invalid="ignore"):
        lowered = used_new < used_old - BOUND_TOLERANCE_PA
        raised = used_new > used_old + BOUND_TOLERANCE_PA
        tracker_raised = new["jp3_ext_bound_Pa"] > old["jp3_ext_bound_Pa"] + BOUND_TOLERANCE_PA
    nan_changed = np.isnan(used_old) != np.isnan(used_new)
    class_codes = new["jp3_class"].astype(int)
    is_lock = np.isin(class_codes, _codes(new["jp3_class_names"], LOCK_CLASSES))
    tracker_codes = _codes(new["jp3_source_names"], (RETRACT_TRACKER_SOURCE,))
    is_tracker = is_lock & np.isin(new["jp3_model_bound_source"].astype(int), tracker_codes)
    inherited = new["jp3_model_bound_inherited"].astype(bool)
    reasons_by_leg = [chain_explanation(new["jp3_t_s"], is_lock[:, leg], is_tracker[:, leg],
                                        inherited[:, leg], tracker_raised[:, leg])
                      for leg in range(used_new.shape[1])]
    explained = dict.fromkeys(("stretch_source", "lookback", "inherit", "tracker_chain"), 0)
    unexplained_rows = []
    for read, leg in np.argwhere(raised):
        reason = reasons_by_leg[leg][read]
        if reason is not None:
            explained[reason] += 1
            continue
        unexplained_rows.append(_unexplained_row(new, old, int(read), int(leg)))
    return {"has_trace": True, "reads": int(new["jp3_t_s"].size),
            "raised_reads": int(raised.sum()),
            "unexplained_raised_reads": len(unexplained_rows),
            **{f"explained_by_{name}": value for name, value in explained.items()},
            "lowered_reads": int(lowered.sum()), "nan_changed_reads": int(nan_changed.sum()),
            "bad_class_changes": _bad_class_changes(old["jp3_class"], new["jp3_class"],
                                                     new["jp3_class_names"]),
            "class_changes": int((old["jp3_class"] != new["jp3_class"]).sum()),
            "unexplained_rows": unexplained_rows[:MAX_UNEXPLAINED_ROWS]}


def _unexplained_row(new: dict, old: dict, read: int, leg: int) -> dict:
    names = [str(name) for name in new["jp3_class_names"].tolist()]
    sources = [str(name) for name in new["jp3_source_names"].tolist()]
    class_code = int(new["jp3_class"][read, leg])
    source_code = int(new["jp3_model_bound_source"][read, leg])

    def difference_Pa(name: str) -> float:
        return float(new[name][read, leg] - old[name][read, leg])

    return {"t_s": float(new["jp3_t_s"][read]), "leg": leg,
            "class": names[class_code] if 0 <= class_code < len(names) else None,
            "du_Pa": difference_Pa("jp3_used_bound_Pa"),
            "de_Pa": difference_Pa("jp3_ext_bound_Pa"),
            "source": sources[source_code] if 0 <= source_code < len(sources) else None}


def _bad_class_changes(old: np.ndarray, new: np.ndarray, class_names: np.ndarray) -> int:
    """P4-2: allowed changes are EXT -> CARRY_ext and RET -> CARRY_ret (a later gate)."""
    names = [str(name) for name in class_names.tolist()]
    allowed = {(names.index(before), names.index(after))
               for before, after in ALLOWED_CLASS_CHANGES}
    changed = np.argwhere(old != new)
    return sum((int(old[r, c]), int(new[r, c])) not in allowed for r, c in changed)


# --- P4-3a, P4-4 ----------------------------------------------------------------------------

def judged_key_problems(setting: str, check: dict, hydraulics: dict,
                        problems: Problems) -> None:
    """P4-3a on a judged row; a missing key is not judgeable (4a-2 R2; addendum 4a-5 3.3
    names it ``judged_key_missing``)."""
    for key in JUDGED_KEYS:
        values = check.get(key)
        if not isinstance(values, list) or len(values) != 4:
            problems.not_judgeable.append(f"{setting}: P4-3a judged_key_missing {key}")
        elif sum(values):
            problems.failures.append(f"{setting}: P4-3a {key} {values}")
    if hydraulics.get(RELOCK_KEY) is None:
        problems.not_judgeable.append(f"{setting}: P4-3a {RELOCK_KEY} missing")
    elif hydraulics[RELOCK_KEY]:
        problems.failures.append(f"{setting}: P4-3a relock step over 1 bar")


def retract_tracker_problems(setting: str, check: dict, problems: Problems) -> None:
    """P4-9 on a revision 5 row: no ``retract_tracker`` read and no stretch row; a missing
    ``retract_tracker_dominated_reads`` (not a per-leg list) or ``retract_tracker_stretch_log``
    is not judgeable (prelaunch audit M-5: an empty count is never a pass, 5.7)."""
    reads = check.get(RETRACT_TRACKER_READS_KEY)
    stretches = check.get(RETRACT_TRACKER_LOG_KEY)
    if not isinstance(reads, list) or len(reads) != 4 or not isinstance(stretches, list):
        problems.not_judgeable.append(f"{setting}: P4-9 key {RETRACT_TRACKER_READS_KEY} / "
                                      f"{RETRACT_TRACKER_LOG_KEY} missing")
    elif sum(reads) or stretches:
        problems.failures.append(f"{setting}: P4-9 retract_tracker records without fallback")


def seed_force_check(hydraulics: dict) -> dict:
    """4a-2 3.4 on one row's ``p1_retract_seed_log``: rows, over 1 N, clipped and the reason it
    cannot be judged (``not_judgeable`` None = it can). Zero rows are reported (``rows`` 0); the
    caller decides whether its set has a judged row."""
    rows = hydraulics.get("p1_retract_seed_log") or []
    columns = hydraulics.get("p1_retract_seed_log_columns") or []
    count = hydraulics.get("p1_retract_seed_count")
    out = {"rows": len(rows), "count": count, "over_1N_rows": 0, "m2_shift_clipped_rows": 0,
           "not_judgeable": None}
    if SEED_FORCE_COLUMN not in columns or SEED_CLIPPED_COLUMN not in columns:
        out["not_judgeable"] = f"no {SEED_FORCE_COLUMN} / {SEED_CLIPPED_COLUMN} column"
        return out
    if len(rows) != count:
        out["not_judgeable"] = f"seed rows {len(rows)} != p1_retract_seed_count {count}"
        return out
    forces = [row[columns.index(SEED_FORCE_COLUMN)] for row in rows]
    out["m2_shift_clipped_rows"] = sum(bool(row[columns.index(SEED_CLIPPED_COLUMN)])
                                       for row in rows)
    if out["m2_shift_clipped_rows"]:
        out["not_judgeable"] = f"{out['m2_shift_clipped_rows']} m2_shift_clipped seed rows"
    elif any(value is None or not math.isfinite(value) for value in forces):
        out["not_judgeable"] = "a seed row without a force value"
    else:
        out["over_1N_rows"] = sum(abs(value) > NET_FORCE_TOLERANCE_N for value in forces)
    return out


def seed_problems(setting: str, old: dict, new: dict, problems: Problems) -> dict:
    """P4-4 of one judged pair (4a-2 3.4); returns its record. Zero seed rows on a judged pair
    is not judgeable (the baseline counts are 7 .. 11)."""
    old_h, new_h = old["hydraulics_record"], new["hydraulics_record"]
    for key in ("p1_retract_seed_count", "p1_retract_seed_step_max_bar"):
        if old_h.get(key) != new_h.get(key):
            problems.failures.append(f"{setting}: P4-4 {key} differs from the baseline")
    check = seed_force_check(new_h)
    if check["not_judgeable"] is None and check["rows"] == 0:
        check["not_judgeable"] = "zero seed rows (4a-2 3.4: not a pass)"
    if check["not_judgeable"] is not None:
        problems.not_judgeable.append(f"{setting}: P4-4 {check['not_judgeable']}")
    elif check["over_1N_rows"]:
        problems.failures.append(f"{setting}: P4-4 seed net force over 1 N")
    return check


# --- comparison ------------------------------------------------------------------------------

def compare(baseline: Baseline, new_rows: list[dict]) -> tuple[dict, Problems]:
    """All checks (module docstring); a broken baseline or pairing raises
    :class:`NotJudgeable`."""
    problems = Problems()
    pairs = pair_rows(baseline, new_rows, problems)
    report: dict = {"pairs": []}
    class_totals = dict.fromkeys(CLASS_NAMES, 0)
    judged_rows = 0
    for row_file, old, new in pairs:
        pair = _compare_pair(baseline, row_file, old, new, problems)
        report["pairs"].append(pair)
        check = _check(new)
        if _is_revision_5(new):
            for name in CLASS_NAMES:
                class_totals[name] += int(sum((check.get("class_reads") or {}).get(name, [])))
        if new["job"]["setting"] in JUDGED_SETTINGS:
            judged_rows += int(bool(check.get("jp3_judged_row")))
    if judged_rows == 0:
        problems.not_judgeable.append("no judged row of VBJ, LSJ1 .. 4 (13.1, 4a-2 R2)")
    missing = [name for name in REQUIRED_CLASSES if class_totals[name] == 0]
    if missing:
        problems.not_judgeable.append(f"no reads of class {missing} over the revision 5 rows")
    report.update(judged_rows=judged_rows, class_reads=class_totals)
    return report, problems


def _compare_pair(baseline: Baseline, row_file: str, old: dict, new: dict,
                  problems: Problems) -> dict:
    setting = new["job"]["setting"]
    problems.setting_defects += identity_problems(new)
    problems.setting_defects += [f"{setting}: {text}" for text in line_evidence_problems(new)]
    if old["commands_sha256"] != new["commands_sha256"]:
        problems.failures.append(f"{setting}: P4-1 commands_sha256 differs")
    new_npz = _new_t4h_path(new)
    if setting in JUDGED_SETTINGS:  # addendum 4a-7 erratum 1 9: the J-P3 lines' P4 evidence
        is_declared = is_head_only_line(new, _t4h_meta(new_npz))
        problems.setting_defects += [f"{setting}: {text}" for text in
                                     judged_line_evidence_problems(new.get("hydraulics_record"),
                                                                   is_declared,
                                                                   evidence_multiplier(new))]
    try:
        reads = compare_reads(baseline.t4h(row_file, old), new_npz, _is_revision_5(new))
    except NotJudgeable as exc:
        problems.not_judgeable.append(f"{setting}: {exc}")
        reads = {"has_trace": None}
    if reads.get("lowered_reads") or reads.get("nan_changed_reads"):
        problems.failures.append(f"{setting}: P4-2 a read's used bound below the baseline")
    if reads.get("unexplained_raised_reads") or reads.get("bad_class_changes"):
        problems.failures.append(f"{setting}: P4-2 an unexplained raise or class change")
    check, hydraulics = _check(new), new.get("hydraulics_record") or {}
    if _is_revision_5(new):
        retract_tracker_problems(setting, check, problems)
    seed = {}
    if setting in JUDGED_SETTINGS:
        judged_key_problems(setting, check, hydraulics, problems)
        seed = seed_problems(setting, old, new, problems)
    return {"setting": setting, "row_file": row_file,
            "commands_sha256": new["commands_sha256"][:12],
            "new_t4h_sha256": file_sha256(new_npz) if new_npz.is_file() else None,
            "reads": reads, "seed": seed}


def _t4h_meta(npz: Path) -> dict | None:
    """The ``meta_json`` of a T4h npz (None: no file or no meta)."""
    if not npz.is_file():
        return None
    with np.load(npz, allow_pickle=False) as data:
        return json.loads(str(data["meta_json"])) if "meta_json" in data.files else None


def _input_record(paths: list[Path]) -> list[dict]:
    return [{"path": str(path), "sha256": file_sha256(path)} for path in paths]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], epilog=EXIT_TABLE,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("--new", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error(f"{args.out} exists (a new report never overwrites one)")
    try:
        baseline = Baseline(args.baseline)
        new_rows = read_new_rows(args.new)
        report, problems = compare(baseline, new_rows)
        report.update(problems.as_dict())
        status = problems.status()
    except NotJudgeable as exc:
        report, status = {"not_judgeable": [str(exc)]}, STATUS_NOT_JUDGEABLE
    except TOOL_ERRORS as exc:
        report, status = {"error": f"{type(exc).__name__}: {exc}"}, STATUS_ERROR
    report["status"] = status
    report["baseline_sums_sha256"] = BASELINE_SUMS_SHA256
    report["inputs"] = _input_record([path for path in args.new if path.is_file()])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1, default=float), encoding="utf-8")
    print(json.dumps({"status": status, "out": str(args.out),
                      **{f"{kind}_count": len(report.get(kind) or [])
                         for kind in ("setting_defects", "not_judgeable", "failures")}}))
    return STATUS_EXIT[status]


if __name__ == "__main__":
    sys.exit(main())
