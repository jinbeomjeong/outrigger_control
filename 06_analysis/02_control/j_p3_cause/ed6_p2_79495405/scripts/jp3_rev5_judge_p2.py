"""436.9 J-P3 (③ revision 5) judgement, path 2 (independent of the path-1 tool).

Written by dynamics-expert from the definition sentences of the sealed rules only:
``06_analysis/02_control/j_p3_cause/jp3_remedy_spec.md`` edition 4a (sha256 ``8be9de22...``)
sections 6.1, 6.2, 6.3, 13.2, 13.4, 13.6 and 5.5 (T-JR-12, J-P3 part), the addenda 4a-1 .. 4a-6
with their errata, and the path-2 handoff of addendum 4a-7 (sections 1 and 4 only,
``jp3_rev5_p2_handoff_4a7.md``). No path-1 code, output or recorded judgement key is used for
the verdict; the recorded keys are only echoed in a separate comparison block.

Per judged row and leg, from the per-read T4h columns (plant truth ``jp3_p_tr_Pa``; the judged
sets are the recorded classes ``jp3_class``, 4a-7 4.4 / spec 6.2; comparison columns per the
4a-7 erratum 1, section 2, which overrides 4a-7 4.2):

* J-P3a  ``ext`` + ``carry_ext`` reads: breach if p_tr - ``jp3_ext_bound_Pa`` > 1 Pa.
* J-P3b  ``hold`` reads only (erratum 1, 1): breach if p_tr - ``jp3_model_bound_Pa`` (4)
  > 0.6 kN / A_ann (strictly greater; A_ann = YAML exact value, 4a-7 4.11); reads within
  1e-9 bar of the allowance are recorded as near the boundary.
* J-P3c  ``carry_ret`` reads that are trapped (plant ``locked_ext`` / ``locked_ret``, or
  p_tr > ``jp3_p_star_ret_Pa``, or ``jp3_p_star_ret_Pa`` NaN, erratum 2, 2): breach if
  p_tr - ``jp3_used_bound_Pa`` > 1 Pa. On every ``carry_ret`` read used >= ``jp3_ext_bound_Pa``
  - 1 Pa must hold (else ``record_defect``).
* Column agreement (erratum 2, 1): on J-P3a reads |used - ext| > 1 Pa, on J-P3b reads
  |used - model| > 1 Pa (a NaN used next to a finite column included) is ``record_defect``; the
  counts are reported (``jp3a_used_ne_ext_reads``, ``jp3b_used_ne_model_reads``).

P4 evidence (erratum 1, 9; ``hydraulics_record`` ``rod_reading_truth_calls`` (1),
``two_pressure_reads`` (2)): event-path VBJ / LSJ1..4 lines (P4 on) need (1) = k (2) > 0 with
k = 2 for an ``L<n>|s<m>|g8|...`` key and k = 1 otherwise (addendum 4a-8, 8.1), head-only
declared lines (1) = (2) = 0, missing keys = ``setting_defect``; VBH / LSH lines (P4 off,
(1) = 0 and (2) > 0) are checked as notes only (erratum 1, 9).
A noise-run line (with ``level``) is the event path (erratum 1, 3). The check applies to the
harness run lines only (erratum 2, 3): files given with ``--record-input`` (a stored-T4h replay
report, Chrono rows) are read as record rows, never judged, without the evidence check and
without counting their issues (their layout is the run_v5 / r79 layout this tool reads; other
layouts are a tool error).

Checks that make a row not judgeable: code tables (4a-7 4.1), class vs acting command table
with +-1e-12 m/s (4a-7 4.4), NaN comparison value or truth on a judged read (4a-7 4.4),
``hydraulics_record.extend_bound_check`` vs a top-level copy and the r79 ``t4h_file`` name
(4a-7 4.8), a named T4h file that is absent (4a-7 4.8), head-only declaration consistency
(4a-7 1.2 / 4.5; declared rows are not judged rows but ``no_rod_reading_runs``), grade
(4a-7 4.3), tag / revision / identity (spec 4.3, 13.6), test settings ``*_X11`` / ``VBG4`` /
``VBG5`` anywhere in the input = the whole bundle ``setting_defect`` (4a-7 4.9).

``--with-relock`` adds spec 13.4 P4-3a / 4a-7 4.6 / erratum 1, 5 for every VBJ / LSJ1..4 result
row (any grade, declared or not): the logged locks with |``dp_tr_step_Pa``| > 1e5 Pa (non-finite
rows are not counted, their number is reported); >= 1 is a failure; a missing or non-integer
``relock_step_over_1bar_count`` or a missing ``lock_log`` is ``judged_key_missing``; a path-2
count != the recorded count, or a ``lock_log`` at the 2,000-row cap, is ``record_defect``.

A ``stretch_mismatch`` (``LockWindowMismatchError``) error line, whatever its grade or setting,
is a T-JR-14 (a) failure: the bundle status is ``stretch_mismatch`` (class fail, exit 1), its
J-P3 is not graded (``totals`` null, judged rows not recounted, no run_error), the keys are
listed in ``stretch_mismatch_rows``, and the relock (T-JR-15) block is not judgeable
(4a-8 erratum 2, 1). Other error lines stay ``run_error`` on VBJ / LSJ lines.

Status (one per bundle, 4a-7 4.10): ``setting_defect`` > ``run_error`` > ``record_defect`` >
``judged_key_missing`` > ``no_judged_runs`` > ``judged_row_count_mismatch`` (spec 13.2 / 13.9,
with ``--expect-judged-rows``) > ``fail`` (H-7, and the relock block if asked) > ``pass``.

Exit codes (addendum 4a-5 5.1): 0 pass, 1 fail, 2 not judgeable, 3 tool error (unreadable or
missing records file, broken JSON, missing ``--t4h-dir`` for an r79 file, report present,
unexpected exception).

Inputs:

* run_v5 ``.jsonl`` files: the npz named by ``t4h_file`` is in ``<stem>_t4h/`` next to the
  jsonl (4a-7 4.8), never relative to the working directory.
* r79 ``.json`` files (``meta`` + ``results``): the T4h folder is an argument,
  ``--t4h-dir <records file>=<dir>`` (4a-7 4.8; also accepted for a jsonl file).

Usage (python-dev or dynamics-dev, ``python -I -B``)::

    jp3_rev5_judge_p2.py judge <records ...> --out <report.json>
        [--t4h-dir <records file>=<dir> ...] [--expect-judged-rows N] [--with-relock]
        [--record-input <replay / Chrono file> ...]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

TOOL_NAME = "jp3_rev5_judge_p2"
TOOL_VERSION = "6"

LEGS = ("FL", "FR", "RL", "RR")
ANNULUS_AREA_M2 = (0.00376991118, 0.00376991118, 0.00314159265, 0.00314159265)
"""4a-7 4.11: YAML ``legs.<leg>.cylinder.annulus_area_m2`` (front ø130/ø110, rear ø110/ø90)."""
V_MAX_M_S = 0.0209243016
"""YAML ``actuator.max_speed_m_s``."""
HOLD_SPEED_RATIO = 0.01
U_HOLD_M_S = HOLD_SPEED_RATIO * V_MAX_M_S
"""4a-7 4.4: u_hold = 0.01 v_max = 2.0924e-4 m/s."""
CLASS_BOUNDARY_BAND_M_S = 1e-12
"""4a-7 4.4: boundary comparison allowance +-1e-12 m/s."""
BREACH_TOL_PA = 1.0
HOLD_TOL_FORCE_N = 600.0
HOLD_TOL_NEAR_PA = 1e-9 * 1e5
"""4a-7 4.11: within 1e-9 bar of the allowance = near the boundary (record)."""
DELTA_M_PA = 0.5e5
"""Spec 12: delta_m 0.5 bar (J-P3a margin FLAG p_tr > p_hat only)."""
RELOCK_STEP_PA = 1.0e5
MAX_LOGGED_LOCK_EVENTS = 2000
"""Spec 6.3: the lock_log row cap."""

JUDGED_SETTINGS = ("VBJ", "LSJ1", "LSJ2", "LSJ3", "LSJ4")
RECORD_REV5_SETTINGS = ("VBH", "LSH1", "LSH2", "LSH3", "LSH4")
TEST_SETTINGS = ("VBG4", "VBG5")
TEST_SETTING_SUFFIX = "_X11"
JUDGED_GRADES = ("ideal", "normal")
RECORD_GRADES = ("conservative", "old_worst")
R79_LEVEL_GRADE = {"L0": "ideal", "L1": "ideal", "L2": "normal", "L2nocal": "normal",
                   "L2imuideal": "normal", "L3": "conservative", "L4": "old_worst"}
SEALED_SPEC_EDITION = "8be9de22"
DEFAULT_CARRY_END_RULE = "inherit_when_gate_shut"
DEFAULT_RETRACT_START_RULE = "with_tracker"
JUDGED_KEYS = ("jp3a_breach_reads", "jp3b_breach_over_tol_reads", "jp3c_breach_reads")
STEADY_CASES = tuple(f"R{i}" for i in range(1, 12)) + ("S1", "S2", "S3", "S4", "S5", "S7", "S8")
"""4a-7 1.1: head-only declared (steady) cases."""
EVENT_CASES = ("R12", "R14", "R15", "R16")
TRUTH_CALLS_KEY = "rod_reading_truth_calls"  # (1), 4a-2 B2
ROD_READS_KEY = "two_pressure_reads"  # (2), 4a-2 B2

CLASS_NAMES = ("lock", "hold", "carry_ext", "carry_ret", "ext", "ret")
PLANT_STATE_NAMES = ("moving_ext", "moving_ret", "locked_ext", "locked_ret")
SOURCE_NAMES_HEAD = ("extend_bound", "pilot_model", "previous_moving", "retract_hold")
SOURCE_NAMES_LAST = "retract_tracker"
LOCKED_STATES = ("locked_ext", "locked_ret")
MOVING_STATES = ("moving_ext", "moving_ret")
TRACE_COLUMNS_N4 = ("jp3_class", "jp3_plant_state", "jp3_u_m_s", "jp3_ext_bound_Pa",
                    "jp3_model_bound_Pa", "jp3_used_bound_Pa", "jp3_p_tr_Pa",
                    "jp3_p_star_ret_Pa")
TRACE_TIME = "jp3_t_s"
TABLE_KEYS = ("jp3_class_names", "jp3_plant_state_names", "jp3_source_names")
T4H_NAME_CHARACTERS = re.compile(r"[^A-Za-z0-9._-]")
CAND_PREFIX = re.compile(r"^cand=[^#]*#")
TAG_SUFFIX = re.compile(r"(_LAS)?(_K1)?(_TCL)?")

ISSUE_PRIORITY = ("setting_defect", "run_error", "record_defect", "judged_key_missing")
"""4a-7 4.10 (then no_judged_runs > H-7 > pass)."""

EXIT_PASS, EXIT_FAIL, EXIT_NOT_JUDGEABLE, EXIT_TOOL_ERROR = 0, 1, 2, 3


class ToolError(Exception):
    """Unexpected input (exit 3)."""


def hold_tolerance_Pa(leg: int) -> float:
    """J-P3b allowance of a leg [Pa] (0.6 kN / A_ann)."""
    return HOLD_TOL_FORCE_N / ANNULUS_AREA_M2[leg]


def revision_of_tag(tag: Any) -> int | None:
    """Spec 4.3: ``final_C4G2_P3H*`` -> 5, ``final_C4G2_P3*`` -> 4 (suffixes ``_LAS`` ->
    ``_K1`` -> ``_TCL`` in this order), anything else None."""
    if not isinstance(tag, str):
        return None
    for base, revision in (("final_C4G2_P3H", 5), ("final_C4G2_P3", 4)):
        if tag.startswith(base) and TAG_SUFFIX.fullmatch(tag[len(base):]):
            return revision
    return None


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def t4h_name_of_key(key: str) -> str:
    """4a-7 4.8: the full key (with any ``cand=...#`` prefix), [^A-Za-z0-9._-] -> '_', + .npz."""
    return T4H_NAME_CHARACTERS.sub("_", key) + ".npz"


def bare_key(key: str) -> str:
    """4a-7 4.8: the key without its ``cand=...#`` prefix (pairing and key comparison)."""
    return CAND_PREFIX.sub("", key)


STRETCH_MISMATCH_MARKERS = ("stretch_mismatch", "LockWindowMismatchError")
"""4a-5 1 (T-JR-14 (a)): the lock-window alignment mismatch error of a run line."""


def is_stretch_mismatch(error: Any) -> bool:
    text = error if isinstance(error, str) else json.dumps(error, default=str)
    return any(marker in text for marker in STRETCH_MISMATCH_MARKERS)


def is_test_setting(setting: Any) -> bool:
    return isinstance(setting, str) and (setting.endswith(TEST_SETTING_SUFFIX)
                                         or setting in TEST_SETTINGS)


# --------------------------------------------------------------------------------------------
# input rows


@dataclass
class Row:
    source: Path
    index: int
    kind: str  # "run_v5" | "r79"
    raw: dict
    setting: Any
    t4h_dir: Path | None
    record_only: bool = False  # --record-input (replay report / Chrono rows, erratum 2, 3)

    @property
    def label(self) -> str:
        ident = self.raw.get("key") if self.kind == "r79" else self.raw.get("job")
        return f"{self.source.name}#{self.index} {self.setting} {json.dumps(ident, sort_keys=True)}"

    @property
    def hydraulics(self) -> dict:
        record = self.raw.get("hydraulics_record")
        return record if isinstance(record, dict) else {}

    @property
    def case(self) -> Any:
        job = self.raw.get("job")
        return job.get("case") if isinstance(job, dict) else None


def read_rows(records_file: Path, overrides: dict[Path, Path]) -> list[Row]:
    """Rows of one records file (exit 3 on a missing or broken file)."""
    if not records_file.is_file():
        raise ToolError(f"records file not found: {records_file}")
    text = records_file.read_text(encoding="utf-8")
    override = overrides.get(records_file.resolve())
    rows: list[Row] = []
    if records_file.suffix == ".jsonl":
        folder = override or records_file.parent / f"{records_file.stem}_t4h"
        for number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ToolError(f"{records_file}:{number}: broken JSON ({exc})") from exc
            if not isinstance(raw, dict) or not isinstance(raw.get("job"), dict):
                raise ToolError(f"{records_file}:{number}: not a run_v5 line (no job object)")
            rows.append(Row(records_file, number, "run_v5", raw, raw["job"].get("setting"),
                            folder))
        return rows
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ToolError(f"{records_file}: broken JSON ({exc})") from exc
    if not isinstance(document, dict) or not isinstance(document.get("results"), list):
        raise ToolError(f"{records_file}: neither a run_v5 .jsonl nor an r79 results file")
    if override is None:
        raise ToolError(f"{records_file}: an r79 results file needs --t4h-dir {records_file}=<dir>")
    meta = document.get("meta") if isinstance(document.get("meta"), dict) else {}
    for number, raw in enumerate(document["results"]):
        if not isinstance(raw, dict) or not isinstance(raw.get("key"), str):
            raise ToolError(f"{records_file}: results[{number}] has no key")
        rows.append(Row(records_file, number, "r79", raw,
                        raw.get("v5_setting", meta.get("v5_setting")), override))
    return rows


# --------------------------------------------------------------------------------------------
# T4h trace


@dataclass
class Trace:
    path: Path
    sha256: str
    t_s: np.ndarray | None
    columns: dict[str, np.ndarray]
    meta: dict
    tables: dict[str, tuple[str, ...] | None]
    missing: list[str]
    shape_problems: list[str]


def load_trace(path: Path) -> Trace:
    try:
        data = np.load(path, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise ToolError(f"{path}: unreadable npz ({exc})") from exc
    with data:
        meta: dict = {}
        if "meta_json" in data.files:
            try:
                meta = json.loads(str(np.asarray(data["meta_json"])[()]))
            except json.JSONDecodeError as exc:
                raise ToolError(f"{path}: broken meta_json ({exc})") from exc
        missing = [k for k in (TRACE_TIME, *TRACE_COLUMNS_N4) if k not in data.files]
        columns = {k: np.asarray(data[k]) for k in TRACE_COLUMNS_N4 if k in data.files}
        t_s = np.asarray(data[TRACE_TIME], dtype=float) if TRACE_TIME in data.files else None
        tables: dict[str, tuple[str, ...] | None] = {}
        for key in TABLE_KEYS:
            if key in data.files:
                tables[key] = tuple(str(v) for v in np.asarray(data[key]).ravel())
            elif isinstance(meta.get(key), list):
                tables[key] = tuple(str(v) for v in meta[key])
            else:
                tables[key] = None
    problems: list[str] = []
    if t_s is not None:
        if t_s.ndim != 1:
            problems.append(f"{TRACE_TIME} shape {t_s.shape}")
        else:
            for k, v in columns.items():
                if v.shape != (t_s.size, len(LEGS)):
                    problems.append(f"{k} shape {v.shape} != ({t_s.size}, 4)")
            if t_s.size > 1 and not np.all(np.diff(t_s) > 0):
                problems.append(f"{TRACE_TIME} not strictly increasing")
    return Trace(path, sha256_of(path), t_s, columns, meta, tables, missing, problems)


def table_problems(tables: dict[str, tuple[str, ...] | None]) -> list[str]:
    """4a-7 4.1: the recorded tables must exist and match the edition 4a tables."""
    out = []
    for key, expected in (("jp3_class_names", CLASS_NAMES),
                          ("jp3_plant_state_names", PLANT_STATE_NAMES)):
        if tables.get(key) is None:
            out.append(f"{key} not recorded")
        elif tables[key] != expected:
            out.append(f"{key} {tables[key]} != {expected}")
    source = tables.get("jp3_source_names")
    if source is None:
        out.append("jp3_source_names not recorded")
    elif source[:4] != SOURCE_NAMES_HEAD or source[-1] != SOURCE_NAMES_LAST:
        out.append(f"jp3_source_names {source}: first four != {SOURCE_NAMES_HEAD} or last != "
                   f"{SOURCE_NAMES_LAST!r}")
    return out


# --------------------------------------------------------------------------------------------
# per-leg judgement


def _member(values: np.ndarray, names: tuple[str, ...]) -> np.ndarray:
    return np.array([v in names for v in values], dtype=bool)


def _decode(codes: np.ndarray, names: tuple[str, ...]) -> np.ndarray:
    """Code = position in the recorded table; -1 (no class) and anything else -> None."""
    out = np.full(codes.shape, None, dtype=object)
    ints = codes.astype(np.int64)
    valid = (ints >= 0) & (ints < len(names))
    out[valid] = np.asarray(names, dtype=object)[ints[valid]]
    return out


def allowed_classes(u: float) -> frozenset[str]:
    """4a-7 4.4 table with the +-1e-12 m/s boundary allowance (NaN: nothing allowed)."""
    if not math.isfinite(u):
        return frozenset()
    a, band = abs(u), CLASS_BOUNDARY_BAND_M_S
    out: set[str] = set()
    if a <= band:  # u = 0
        out.add("lock")
    if 0.0 < a <= U_HOLD_M_S + band:  # 0 < |u| <= u_hold (u exactly 0 is never hold)
        out.add("hold")
    if a >= U_HOLD_M_S - band:  # |u| > u_hold
        out |= {"carry_ext", "ext"} if u > 0 else {"carry_ret", "ret"}
    return frozenset(out)


def _min_gap(gap_Pa: np.ndarray, t_s: np.ndarray) -> tuple[float | None, float | None]:
    if gap_Pa.size == 0:
        return None, None
    j = int(np.argmin(gap_Pa))
    return float(gap_Pa[j]) / 1e5, float(t_s[j])


@dataclass
class LegResult:
    counts: dict[str, Any] = field(default_factory=dict)
    defects: dict[str, int] = field(default_factory=dict)


def judge_leg(leg: int, t_s: np.ndarray, rec: np.ndarray, state: np.ndarray,
              cols: dict[str, np.ndarray]) -> LegResult:
    """J-P3a / b / c of one leg of one row (values in Pa, gaps reported in bar)."""
    res = LegResult()
    u = cols["jp3_u_m_s"][:, leg].astype(float)
    p_tr = cols["jp3_p_tr_Pa"][:, leg].astype(float)
    used = cols["jp3_used_bound_Pa"][:, leg].astype(float)
    ext = cols["jp3_ext_bound_Pa"][:, leg].astype(float)
    model = cols["jp3_model_bound_Pa"][:, leg].astype(float)
    p_star = cols["jp3_p_star_ret_Pa"][:, leg].astype(float)

    allowed = [allowed_classes(float(v)) for v in u]
    outside = np.array([c is None or c not in ok for c, ok in zip(rec, allowed, strict=True)])
    near_hold = np.isfinite(u) & (np.abs(np.abs(u) - U_HOLD_M_S) <= CLASS_BOUNDARY_BAND_M_S)
    res.defects["class_outside_table_reads"] = int(outside.sum())
    res.counts["class_boundary_reads"] = int(near_hold.sum())

    in_a = _member(rec, ("ext", "carry_ext"))
    in_b = rec == "hold"
    in_c = rec == "carry_ret"
    ok = np.isfinite(p_tr) & np.isfinite(used)
    finite_tr = np.isfinite(p_tr)

    # J-P3a: p_tr > jp3_ext_bound_Pa (p_hat + delta_m) + 1 Pa (4a-7 erratum 1, 2)
    a_ok = finite_tr & np.isfinite(ext)
    res.defects["jp3a_nan_reads"] = int((in_a & ~a_ok).sum())
    a = in_a & a_ok
    a_excess = p_tr[a] - ext[a]
    gap, t_gap = _min_gap(ext[a] - p_tr[a], t_s[a])
    breach_t = t_s[a][a_excess > BREACH_TOL_PA]
    # erratum 2, 1: on these reads the record defines used == ext; > 1 Pa apart (or a NaN used
    # next to a finite ext) is a record defect
    with np.errstate(invalid="ignore"):
        a_used_diff = ~(np.abs(used[a] - ext[a]) <= BREACH_TOL_PA)
    res.defects["jp3a_used_ne_ext_reads"] = int(a_used_diff.sum())
    res.counts.update(
        jp3a_reads=int(a.sum()), jp3a_breach_reads=int((a_excess > BREACH_TOL_PA).sum()),
        jp3a_min_gap_bar=gap, jp3a_min_gap_t_s=t_gap,
        jp3a_first_breach_t_s=float(breach_t[0]) if breach_t.size else None,
        jp3a_margin_used_reads=int((p_tr[a] > ext[a] - DELTA_M_PA).sum()),
        jp3a_used_ne_ext_reads=int(a_used_diff.sum()))  # also reported as a count
    res.counts["jp3a_by_plant_state"] = {
        name: {"reads": int((a & (state == name)).sum()),
               "breach_reads": int((p_tr[a & (state == name)] - ext[a & (state == name)]
                                    > BREACH_TOL_PA).sum())} for name in PLANT_STATE_NAMES}

    # J-P3b: p_tr > jp3_model_bound_Pa (4) + 0.6 kN / A_ann (4a-7 erratum 1, 2)
    tol = hold_tolerance_Pa(leg)
    b_ok = finite_tr & np.isfinite(model)
    res.defects["jp3b_nan_reads"] = int((in_b & ~b_ok).sum())
    b = in_b & b_ok
    b_excess = p_tr[b] - model[b]
    gap, t_gap = _min_gap(model[b] - p_tr[b], t_s[b])
    with np.errstate(invalid="ignore"):
        b_used_diff = ~(np.abs(used[b] - model[b]) <= BREACH_TOL_PA)  # erratum 2, 1
    res.defects["jp3b_used_ne_model_reads"] = int(b_used_diff.sum())
    res.counts.update(
        jp3b_reads=int(b.sum()), jp3b_breach_reads=int((b_excess > BREACH_TOL_PA).sum()),
        jp3b_breach_over_tol_reads=int((b_excess > tol).sum()),
        jp3b_tol_near_reads=int((np.abs(b_excess - tol) <= HOLD_TOL_NEAR_PA).sum()),
        jp3b_max_excess_bar=float(b_excess.max()) / 1e5 if b_excess.size else None,
        jp3b_min_gap_bar=gap, jp3b_min_gap_t_s=t_gap,
        jp3b_used_ne_model_reads=int(b_used_diff.sum()))

    # J-P3c: trapped (judged) / fill (record) shares of carry_ret
    locked = _member(state, LOCKED_STATES)
    moving = _member(state, MOVING_STATES)
    res.defects["jp3c_nan_reads"] = int((in_c & ~(ok & np.isfinite(ext))).sum())
    res.defects["jp3c_plant_state_invalid_reads"] = int((in_c & ~locked & ~moving).sum())
    c_ok = in_c & ok & np.isfinite(ext)
    res.defects["jp3c_used_below_ext_reads"] = int((c_ok & (used < ext - BREACH_TOL_PA)).sum())
    c_base = c_ok & (locked | moving)
    star_nan = ~np.isfinite(p_star)
    with np.errstate(invalid="ignore"):
        above_target = p_tr > p_star
    # erratum 2, 2: locked, or p_tr > p*_last, or p*_last NaN = trapped (judged)
    trapped = c_base & (locked | above_target | star_nan)
    fill = c_base & moving & ~star_nan & ~above_target
    res.counts["jp3c_p_star_nan_trapped_reads"] = int((c_base & moving & star_nan).sum())
    c_excess = p_tr[trapped] - used[trapped]
    gap, t_gap = _min_gap(used[trapped] - p_tr[trapped], t_s[trapped])
    fill_excess = p_tr[fill] - used[fill]
    res.counts.update(
        jp3c_reads=int(trapped.sum()), jp3c_breach_reads=int((c_excess > BREACH_TOL_PA).sum()),
        jp3c_min_gap_bar=gap, jp3c_min_gap_t_s=t_gap,
        jp3c_fill_reads=int(fill.sum()),
        jp3c_fill_breach_reads=int((fill_excess > BREACH_TOL_PA).sum()),
        jp3c_fill_max_excess_bar=float(fill_excess.max()) / 1e5 if fill_excess.size else None)

    # records (spec 6.2 rows that are not judged)
    lock = (rec == "lock") & np.isfinite(p_tr) & np.isfinite(model)
    lock_ext, lock_ret = lock & (state == "locked_ext"), lock & (state == "locked_ret")
    ret = (rec == "ret") & ok
    ret_excess = p_tr[ret] - used[ret]
    res.counts.update(
        lock_ext_reads=int(lock_ext.sum()),
        lock_ext_breach_over_tol_reads=int((p_tr[lock_ext] - model[lock_ext] > tol).sum()),
        lock_ret_reads=int(lock_ret.sum()),
        lock_ret_breach_reads=int((p_tr[lock_ret] - model[lock_ret] > BREACH_TOL_PA).sum()),
        ret_reads=int(ret.sum()), ret_breach_reads=int((ret_excess > BREACH_TOL_PA).sum()),
        ret_max_excess_bar=float(ret_excess.max()) / 1e5 if ret_excess.size else None,
        class_reads={name: int((rec == name).sum()) for name in CLASS_NAMES})
    return res


# --------------------------------------------------------------------------------------------
# per-row judgement


@dataclass
class RowOutcome:
    label: str
    role: str  # judged | record | no_rod_reading | excluded
    counted: bool = False  # issues count for the bundle (a VBJ / LSJ row not demoted to record)
    issue: str | None = None  # one of ISSUE_PRIORITY
    reasons: list[str] = field(default_factory=list)
    key_missing: list[str] = field(default_factory=list)
    declaration: dict | None = None
    grade: str | None = None
    grade_source: str | None = None
    t4h: dict | None = None
    legs: dict[str, dict] | None = None
    leg_defects: dict[str, dict] | None = None
    recorded_comparison: dict | None = None
    recorded_judged_row: Any = None
    relock: dict | None = None
    notes: list[str] = field(default_factory=list)
    identity: dict | None = None
    tag: Any = None

    def add(self, kind: str, reason: str) -> None:
        """Record an issue: on a counted row it sets the row issue, otherwise it is a note."""
        if self.counted:
            if self.issue is None or ISSUE_PRIORITY.index(kind) < ISSUE_PRIORITY.index(self.issue):
                self.issue = kind
            self.reasons.append(f"{kind}: {reason}")
        else:
            self.notes.append(f"({kind}) {reason}")


def _reference_ebc(row: Row, out: RowOutcome) -> dict | None:
    """4a-7 4.8: ``hydraulics_record.extend_bound_check`` is the record; a top-level copy must
    equal it."""
    ebc = row.hydraulics.get("extend_bound_check")
    top = row.raw.get("extend_bound_check")
    if "extend_bound_check" in row.raw and top != ebc:
        out.add("record_defect", "top-level extend_bound_check != hydraulics_record one")
    return ebc if isinstance(ebc, dict) else None


def _declaration(row: Row, trace: Trace | None) -> dict:
    """4a-7 erratum 1, 3: a noise-run result line (with ``level``) is the event path without
    looking at a declaration; a harness line goes by 4a-7 1.1 (T4h meta ``head_only_declared``
    -> line ``head_only_declared`` -> case table); otherwise undeclared (event path)."""
    if row.raw.get("level") is not None:
        return {"declared": False, "source": "level_line_event_path"}
    if trace is not None and isinstance(trace.meta.get("head_only_declared"), bool):
        return {"declared": trace.meta["head_only_declared"], "source": "t4h_meta"}
    if isinstance(row.raw.get("head_only_declared"), bool):
        return {"declared": row.raw["head_only_declared"], "source": "line"}
    if row.case in STEADY_CASES:
        return {"declared": True, "source": "case_steady"}
    if row.case in EVENT_CASES:
        return {"declared": False, "source": "case_event"}
    return {"declared": False, "source": "no_declaration_case_not_listed"}


def _count(row: Row, key: str) -> Any:
    """A P4 evidence key of ``hydraulics_record`` (4a-2 B2; 4a-7 erratum 1, 9)."""
    return row.hydraulics.get(key)


R79_KEY_LEVELS = tuple(R79_LEVEL_GRADE)
"""4a-8 erratum 1, 8: L0 .. L4, L2nocal, L2imuideal."""
R79_KEY_SEED = re.compile(r"s[0-9]+")


def is_r79_key(key: Any) -> bool:
    """4a-8 erratum 1, 8: without ``cand=...#``, first token a level name, second ``s<digits>``."""
    if not isinstance(key, str):
        return False
    tokens = bare_key(key).split("|")
    return len(tokens) >= 2 and tokens[0] in R79_KEY_LEVELS \
        and R79_KEY_SEED.fullmatch(tokens[1]) is not None


def p4_truth_calls_per_read(row: Row) -> int:
    """Addendum 4a-8 8.1 / erratum 1, 8: k = 2 for an r79 key whose third token is ``g8``
    (whatever the level name), otherwise k = 1 (a harness batch line has no key: k = 1)."""
    key = row.raw.get("key")
    if not is_r79_key(key):
        return 1
    tokens = bare_key(key).split("|")
    if len(tokens) >= 3 and tokens[2] == "g8":
        return 2
    return 1


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def row_grade(row: Row, ebc: dict | None, out: RowOutcome) -> str | None:
    """4a-7 4.3: rev 5 record ``sensor_grade`` -> r79 ``level`` -> a ``job`` line without
    ``level`` = ideal; disagreement or no rule = setting_defect."""
    grade = ebc.get("sensor_grade") if ebc else None
    level = row.raw.get("level")
    level_grade = R79_LEVEL_GRADE.get(str(level)) if level is not None else None
    if grade is not None and grade not in JUDGED_GRADES + RECORD_GRADES:
        out.add("setting_defect", f"unknown sensor_grade {grade!r}")
        return None
    if level is not None and level_grade is None:
        out.add("setting_defect", f"unknown level {level!r}")
        return None
    if grade is not None and level_grade is not None and grade != level_grade:
        out.add("setting_defect", f"sensor_grade {grade!r} != level {level!r} ({level_grade})")
        return None
    if grade is not None:
        out.grade_source = "sensor_grade"
        return grade
    if level_grade is not None:
        out.grade_source = "level"
        return level_grade
    if isinstance(row.raw.get("job"), dict):
        out.grade_source = "job_line_without_level"
        return "ideal"
    out.add("setting_defect", "no sensor_grade, no level and not a job line")
    return None


def _identity_problems(ebc: dict) -> list[str]:
    """Spec 13.6 / 4a-5 2: spec_edition, carry_end_rule, retract_start_rule."""
    return [f"{key} {ebc.get(key)!r} != {expected!r}"
            for key, expected in (("spec_edition", SEALED_SPEC_EDITION),
                                  ("carry_end_rule", DEFAULT_CARRY_END_RULE),
                                  ("retract_start_rule", DEFAULT_RETRACT_START_RULE))
            if ebc.get(key) != expected]


def relock_block(row: Row) -> dict:
    """4a-7 4.6: locks with |dp_tr_step_Pa| > 1e5 Pa (path-2 count from ``lock_log``) and the
    recorded ``relock_step_over_1bar_count``."""
    hyd = row.hydraulics
    recorded = hyd.get("relock_step_over_1bar_count")
    out: dict[str, Any] = {"recorded_relock_step_over_1bar_count": recorded}
    if not isinstance(recorded, int) or isinstance(recorded, bool):
        return {**out, "status": "judged_key_missing",
                "reason": "relock_step_over_1bar_count missing or not an integer"}
    rows, columns = hyd.get("lock_log"), hyd.get("lock_log_columns")
    if not isinstance(rows, list) or not isinstance(columns, list) \
            or "dp_tr_step_Pa" not in columns:
        return {**out, "status": "judged_key_missing",
                "reason": "lock_log / lock_log_columns / dp_tr_step_Pa missing"}
    j = columns.index("dp_tr_step_Pa")
    steps = [r[j] if isinstance(r, list) and len(r) > j else None for r in rows]
    finite = [float(s) for s in steps
              if isinstance(s, (int, float)) and not isinstance(s, bool) and math.isfinite(s)]
    over = sum(abs(s) > RELOCK_STEP_PA for s in finite)  # equal to 1 bar is not over
    out.update(logged_locks=len(rows), p2_steps_over_1bar=over,
               non_finite_step_rows=len(steps) - len(finite),  # not counted (erratum 1, 5)
               p2_max_abs_step_bar=max((abs(s) for s in finite), default=0.0) / 1e5)
    defects = []
    if len(rows) >= MAX_LOGGED_LOCK_EVENTS:
        defects.append(f"lock_log at the {MAX_LOGGED_LOCK_EVENTS}-row cap: cannot recount")
    if recorded != over:
        defects.append(f"recorded count {recorded} != path-2 count {over}")
    out["defects"] = defects
    if defects:
        out["reason"] = "; ".join(defects)
    status = "record_defect" if defects else "fail" if over >= 1 else "pass"
    return {**out, "status": status}


def judge_row(row: Row, with_relock: bool, expected_revision: int = 5,
              tag_revision=None, check_identity: bool = True) -> RowOutcome:
    """J-P3 of one row. The defaults are the revision-5 rules; the revision-6 path-2 judge
    (``jp3_rev6_judge_p2``) passes ``expected_revision`` 6, its tag map and
    ``check_identity=False`` (identity recorded, not judged)."""
    tag_revision = tag_revision or revision_of_tag
    setting = row.setting
    if row.record_only and setting in JUDGED_SETTINGS + RECORD_REV5_SETTINGS:
        # erratum 2, 3: a stored-T4h replay report or a Chrono row is not a judged row and has
        # no P4 evidence keys; its J-P3 values are record / comparison only
        out = RowOutcome(row.label, "record")
        out.notes.append("record-only input (replay / Chrono): no P4 evidence check")
    elif setting in JUDGED_SETTINGS:
        out = RowOutcome(row.label, "judged", counted=True)
    elif setting in RECORD_REV5_SETTINGS:
        out = RowOutcome(row.label, "record")
    else:
        out = RowOutcome(row.label, "excluded")
        out.notes.append(f"setting {setting!r} outside VBJ / LSJ / VBH / LSH")
        return out
    if row.raw.get("error") is not None:
        if is_stretch_mismatch(row.raw["error"]) and not row.record_only:
            # 4a-8 erratum 2, 1: a T-JR-14 (a) failure line; the bundle's J-P3 is not graded
            out.role, out.counted = "stretch_mismatch", False
            out.notes.append(f"stretch_mismatch error line: {str(row.raw['error'])[:200]}")
            return out
        out.add("run_error", f"error line: {str(row.raw['error'])[:200]}")
        return out
    if with_relock and setting in JUDGED_SETTINGS and not row.record_only:
        out.relock = relock_block(row)
    ebc = _reference_ebc(row, out)

    # T4h (4a-7 4.8: the folder is given; a named file that is absent is not judgeable)
    trace: Trace | None = None
    name = row.raw.get("t4h_file")
    if row.kind == "r79" and name is not None \
            and Path(str(name)).name != t4h_name_of_key(row.raw["key"]):
        out.add("record_defect", f"t4h_file {name!r} != {t4h_name_of_key(row.raw['key'])!r}")
    t4h_path = None if name is None or row.t4h_dir is None else row.t4h_dir / Path(str(name)).name
    if t4h_path is not None:
        if t4h_path.is_file():
            trace = load_trace(t4h_path)
            out.t4h = {"path": str(trace.path), "sha256": trace.sha256,
                       "reads": None if trace.t_s is None else int(trace.t_s.size)}
        else:
            out.t4h = {"path": str(t4h_path), "missing": True}

    # head-only declaration (4a-7 1.1 / 1.2 / 4.5)
    out.declaration = _declaration(row, trace)
    calls, reads = _count(row, TRUTH_CALLS_KEY), _count(row, ROD_READS_KEY)
    out.declaration.update({TRUTH_CALLS_KEY: calls, ROD_READS_KEY: reads})
    evidence = f"{TRUTH_CALLS_KEY} {calls!r}, {ROD_READS_KEY} {reads!r}"
    check_evidence = not row.record_only  # erratum 2, 3: harness run lines only
    if check_evidence and not (_is_count(calls) and _is_count(reads)):
        # 4a-7 erratum 1, 9: a line without the P4 evidence keys is a setting defect
        out.add("setting_defect", f"P4 evidence keys missing or not integers ({evidence})")
    if out.declaration["declared"]:
        if ebc is not None:
            out.add("setting_defect", "head-only declared line with a ③ record")
        if check_evidence and _is_count(calls) and _is_count(reads) \
                and (calls != 0 or reads != 0):
            out.add("setting_defect", f"head-only declared line needs (1) = (2) = 0 ({evidence})")
        out.role = "no_rod_reading"  # not a judged row, not a defect by itself (4a-7 4.5)
        return out
    if ebc is None:
        out.add("setting_defect", "line without head-only declaration and without a ③ record")
    if check_evidence and _is_count(calls) and _is_count(reads):
        if setting in JUDGED_SETTINGS:  # P4 on (addendum 4a-8, 8.1): (1) = k (2) > 0
            k = p4_truth_calls_per_read(row)
            out.declaration["p4_k"] = k
            if not (calls == k * reads and reads > 0):
                out.add("setting_defect",
                        f"event-path P4 line needs (1) = {k} x (2) > 0 ({evidence})")
        elif not (calls == 0 and reads > 0):  # P4 off (VBH / LSH): a note only
            out.add("setting_defect", f"P4-off line needs (1) = 0 and (2) > 0 ({evidence})")
    if ebc is None:
        return out

    # tag, revision, grade, identity (spec 4.3, 6.1, 13.6; 4a-7 4.3)
    meta_tag = trace.meta.get("controller_tag") if trace else None
    tag = row.raw.get("controller_tag") or meta_tag
    if meta_tag is not None and row.raw.get("controller_tag") is not None \
            and meta_tag != row.raw["controller_tag"]:
        out.add("setting_defect",
                f"line tag {row.raw['controller_tag']!r} != T4h meta {meta_tag!r}")
    meta_setting = (trace.meta.get("job") or {}).get("setting") if trace else None
    if meta_setting is not None and meta_setting != setting:
        out.add("setting_defect", f"T4h meta setting {meta_setting!r} != {setting!r}")
    if tag_revision(tag) != expected_revision:
        out.add("setting_defect", f"controller tag {tag!r} is not ③ revision {expected_revision}")
    if ebc.get("rule_revision") != expected_revision:
        out.add("setting_defect",
                f"rule_revision {ebc.get('rule_revision')!r} != {expected_revision}")
    out.identity = {k: ebc.get(k) for k in ("spec_edition", "carry_end_rule",
                                            "retract_start_rule")}
    out.tag = tag
    if check_identity:
        for problem in _identity_problems(ebc):
            out.add("setting_defect", problem)
    out.grade = row_grade(row, ebc, out)
    out.recorded_judged_row = ebc.get("jp3_judged_row")
    if out.role == "judged" and out.grade in RECORD_GRADES:
        out.role, out.counted = "record", False
        out.notes.append(f"grade {out.grade}: J-P3 recorded only (decision 147)")
    if out.issue in ("setting_defect", "run_error"):
        return out

    # judged inputs (4a-5 3.3: absent is not zero)
    for key in JUDGED_KEYS:
        value = ebc.get(key)
        if not (isinstance(value, list) and len(value) == len(LEGS)):
            out.key_missing.append(f"extend_bound_check.{key}")
    if name is None:
        out.key_missing.append("t4h_file")
    if out.t4h is not None and out.t4h.get("missing"):
        out.add("record_defect", f"T4h file not found: {out.t4h['path']}")
    if trace is None:
        return _finish_key_missing(out)
    out.key_missing += [f"npz:{k}" for k in trace.missing]
    if out.key_missing:
        return _finish_key_missing(out)
    problems = trace.shape_problems + table_problems(trace.tables)
    for problem in problems:
        out.add("record_defect", problem)
    if out.issue is not None or problems:
        return out

    rec = _decode(trace.columns["jp3_class"], CLASS_NAMES)
    state = _decode(trace.columns["jp3_plant_state"], PLANT_STATE_NAMES)
    out.legs, out.leg_defects = {}, {}
    for i, leg in enumerate(LEGS):
        res = judge_leg(i, trace.t_s, rec[:, i], state[:, i], trace.columns)
        out.legs[leg], out.leg_defects[leg] = res.counts, res.defects
        for defect, n in res.defects.items():
            if n:
                out.add("record_defect", f"{leg} {defect} = {n}")
    out.recorded_comparison = recorded_comparison(ebc, out.legs)
    return out


def _finish_key_missing(out: RowOutcome) -> RowOutcome:
    if out.key_missing:
        out.add("judged_key_missing", ", ".join(out.key_missing))
    return out


COMPARED_KEYS = ("jp3a_reads", "jp3a_breach_reads", "jp3b_reads", "jp3b_breach_reads",
                 "jp3b_breach_over_tol_reads", "jp3c_reads", "jp3c_breach_reads",
                 "jp3c_fill_reads", "jp3c_fill_breach_reads")


def recorded_comparison(ebc: dict, legs: dict[str, dict]) -> dict:
    """Echo of the recorded per-leg keys next to the path-2 values (not used for the status)."""
    out = {}
    for key in COMPARED_KEYS:
        recorded = ebc.get(key)
        mine = [legs[leg][key] for leg in LEGS]
        out[key] = {"recorded": recorded, "path2": mine,
                    "equal": isinstance(recorded, list) and list(recorded) == mine}
    return out


# --------------------------------------------------------------------------------------------
# bundle verdict


def judge(records: list[Path], overrides: dict[Path, Path], expect_judged_rows: int | None,
          with_relock: bool, record_inputs: list[Path] | None = None,
          expected_revision: int = 5, tag_revision=None, check_identity: bool = True) -> dict:
    inputs, rows = [], []
    for path, record_only in [(p, False) for p in records] + \
            [(p, True) for p in record_inputs or []]:
        found = read_rows(path, overrides)
        for row in found:
            row.record_only = record_only
        inputs.append({"path": str(path.resolve()), "sha256": sha256_of(path),
                       "rows": len(found), "record_only": record_only})
        rows += found
    test_rows = [r.label for r in rows if is_test_setting(r.setting)]
    outcomes = [judge_row(r, with_relock, expected_revision, tag_revision, check_identity)
                for r in rows if not is_test_setting(r.setting)]
    issues = [(o.issue, o.label) for o in outcomes if o.issue is not None]
    if test_rows:
        issues.append(("setting_defect", f"test settings in the input: {test_rows[:20]}"))
    relock = None
    relock_failures: list[str] = []
    if with_relock:
        blocks = [(o.label, o.relock) for o in outcomes if o.relock is not None]
        for label, block in blocks:
            if block.get("p2_steps_over_1bar", 0) >= 1:
                relock_failures.append(label)
            if block["status"] not in ("pass", "fail"):
                issues.append((block["status"], f"relock: {label}: {block.get('reason')}"))
        relock = {"rows": len(blocks), "failures": relock_failures,
                  "status": ("not_judgeable" if not blocks else
                             "fail" if relock_failures else
                             "pass" if all(b["status"] == "pass" for _, b in blocks)
                             else "not_judgeable")}
        if not blocks:
            issues.append(("judged_key_missing", "relock: no VBJ / LSJ result row"))
    clean = [o for o in outcomes if o.role == "judged" and o.issue is None]
    totals = {key: sum(o.legs[leg][key] for o in clean for leg in LEGS) for key in JUDGED_KEYS}
    flags = {key: sum(o.legs[leg][key] for o in clean for leg in LEGS)
             for key in ("jp3b_breach_reads", "jp3b_tol_near_reads", "jp3a_margin_used_reads",
                         "jp3c_fill_reads", "jp3c_fill_breach_reads",
                         "jp3a_used_ne_ext_reads", "jp3b_used_ne_model_reads")}
    kinds = {kind for kind, _ in issues}
    fail_reasons = []
    if sum(totals.values()) > 0:
        fail_reasons.append("J-P3 H-7")
    if relock_failures:
        fail_reasons.append("P4-3a relock")
    stretch_rows = [o for o in outcomes if o.role == "stretch_mismatch"]
    if stretch_rows:
        # 4a-8 erratum 2, 1: T-JR-14 (a) failure; J-P3 is not graded, judged rows are not
        # recounted and nothing is turned into run_error / not judgeable
        status = "stretch_mismatch"
        fail_reasons = ["T-JR-14 (a) stretch_mismatch"]
        if relock is not None:
            relock["status"] = "not_judgeable"  # T-JR-15: no seed / relock columns on the line
            relock["stretch_mismatch_rows"] = len(stretch_rows)
    elif kinds:
        status = next(k for k in ISSUE_PRIORITY if k in kinds)
    elif not clean:
        status = "no_judged_runs"
    elif expect_judged_rows is not None and len(clean) != expect_judged_rows:
        status = "judged_row_count_mismatch"
    elif fail_reasons:
        status = "fail"
    else:
        status = "pass"
    exit_code = {"pass": EXIT_PASS, "fail": EXIT_FAIL,
                 "stretch_mismatch": EXIT_FAIL}.get(status, EXIT_NOT_JUDGEABLE)
    stretch_keys = [o.label for o in stretch_rows]
    if stretch_rows:
        totals = None  # not graded (4a-8 erratum 2, 1)
    judged_row_differences = [
        {"row": o.label, "recorded_jp3_judged_row": o.recorded_judged_row, "path2_role": o.role}
        for o in outcomes if o.recorded_judged_row is not None
        and bool(o.recorded_judged_row) != (o.role == "judged")]
    return {
        "tool": TOOL_NAME, "tool_version": TOOL_VERSION, "path": 2,
        "rules": {"spec": "jp3_remedy_spec.md edition 4a (sha256 8be9de22...)",
                  "addenda": ["4a-1", "4a-2", "4a-3", "4a-4", "4a-4 erratum 1", "4a-5",
                              "4a-5 erratum 1", "4a-6", "4a-7 1 and 4 (path-2 handoff)",
                              "4a-7 erratum 1 (path-2 handoff 2)",
                              "4a-7 erratum 2 sections 1-3, 5 (path-2 handoff 3)",
                              "4a-7 erratum 3 (path-2 handoff 4)",
                              "4a-8 section 8.1 (path-2 handoff 5)",
                              "4a-8 erratum 1 section 8 (path-2 handoff 6)",
                              "4a-8 erratum 2 section 1 (path-2 handoff 7)"]},
        "constants": {"u_hold_m_s": U_HOLD_M_S, "breach_tol_Pa": BREACH_TOL_PA,
                      "hold_tol_bar": [hold_tolerance_Pa(i) / 1e5 for i in range(len(LEGS))],
                      "class_boundary_band_m_s": CLASS_BOUNDARY_BAND_M_S,
                      "spec_edition": SEALED_SPEC_EDITION},
        "inputs": inputs,
        "status": status, "exit_code": exit_code, "class": _status_class(status),
        "fail_reasons": fail_reasons if status in ("fail", "stretch_mismatch") else [],
        "stretch_mismatch_rows": stretch_keys,
        "issues": [{"kind": k, "where": w} for k, w in issues],
        "judged_runs": len(clean),
        "judged_key_missing_runs": sum(o.issue == "judged_key_missing" for o in outcomes),
        "no_rod_reading_runs": sum(o.role.startswith("no_rod_reading") for o in outcomes),
        "record_runs": sum(o.role == "record" for o in outcomes),
        "record_input_rows": sum(r.record_only for r in rows),
        "excluded_runs": sum(o.role == "excluded" for o in outcomes),
        "test_setting_rows": test_rows,
        "expect_judged_rows": expect_judged_rows,
        "totals": totals, "flags": flags, "relock": relock,
        "judged_row_differences": judged_row_differences,
        "rows": [o.__dict__ for o in outcomes],
    }


def _status_class(status: str) -> str:
    """4a-7 4.10: the two-path comparison class."""
    if status in ("setting_defect", "run_error", "record_defect"):
        return "defect"
    if status == "stretch_mismatch":
        return "fail"
    return {"pass": "pass", "fail": "fail"}.get(status, "not_judgeable")


def _parse_overrides(items: list[str]) -> dict[Path, Path]:
    out = {}
    for item in items:
        if "=" not in item:
            raise ToolError(f"--t4h-dir needs <records file>=<dir>: {item!r}")
        records, folder = item.split("=", 1)
        out[Path(records).resolve()] = Path(folder).resolve()
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("judge", help="J-P3 (436.9, ③ rev 5) path-2 verdict")
    p.add_argument("records", nargs="*", type=Path)
    p.add_argument("--record-input", action="append", default=[], type=Path,
                   help="record-only file (stored-T4h replay report, Chrono rows): never judged")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--t4h-dir", action="append", default=[])
    p.add_argument("--expect-judged-rows", type=int)
    p.add_argument("--with-relock", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.out.exists():
            raise ToolError(f"report exists, not overwritten: {args.out}")
        if not args.records and not args.record_input:
            raise ToolError("no input file")
        report = judge(args.records, _parse_overrides(args.t4h_dir), args.expect_judged_rows,
                       args.with_relock, args.record_input)
    except ToolError as exc:
        print(f"[{TOOL_NAME}] tool error: {exc}", file=sys.stderr)
        print(f"status=tool_error exit={EXIT_TOOL_ERROR}")
        return EXIT_TOOL_ERROR
    except Exception:  # an unexpected input shape must never read as exit 1 (fail)
        import traceback

        traceback.print_exc()
        print(f"status=tool_error exit={EXIT_TOOL_ERROR}")
        return EXIT_TOOL_ERROR
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    t = report["totals"] or {key: "-" for key in JUDGED_KEYS}
    print(f"status={report['status']} exit={report['exit_code']} "
          f"judged_runs={report['judged_runs']} no_rod_reading={report['no_rod_reading_runs']} "
          f"jp3a={t['jp3a_breach_reads']} jp3b={t['jp3b_breach_over_tol_reads']} "
          f"jp3c={t['jp3c_breach_reads']} report={args.out.resolve()}")
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
