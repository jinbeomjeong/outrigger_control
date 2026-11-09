"""LAS-b K1 conditional adoption judge: the shadow dP over stored Chrono SCM result.json files.

Rules: the sealed ``las_k1_rules_adopt.md`` (control-expert, sha256 :data:`RULES_SHA256`),
path 1 of its section 10.1. The rules text wins where this code differs; section numbers in
the comments are the rules'.

Sub-commands
  list   sections 2.1-2.4: population U, sets A / B / E, their canonical list sha256 and the
         per-file classification (metadata only: no t_P, t_S, decision or event value is
         written) -> ``adopt_list.json``
  judge  K-0..K-8 and sections 3-8 on the 74 rows of appendix A (plus the set B record of
         section 7) -> ``judge_adopt.json``. K-9 (the two-path recount) is the comparison with
         control-expert's path 2 and is recorded as external.

Read only: the result.json files are only read. The only write is ``--out``. The only child
processes are ``git rev-parse HEAD`` and ``git status --porcelain`` (skipped with
``--no-git``). Standard library only; no project module and no other judge is imported.

Usage (dynamics-dev, PowerShell, project root):
  C:\\ProgramData\\miniforge3\\envs\\dynamics-dev\\python.exe -I -B
      06_analysis/02_control/verif_matrix/scripts/las_k1_adopt_judge.py
      list  [--results-root R] [--rules F] [--out F]
      judge --expect-tool-sha <sha256 of this file from the pre-run audit>
            [--results-root R] [--rules F] [--out F] [--root P] [--no-git]

Exit codes: 0 pass (``list``: every 2.3 value reproduced), 1 fail / undecidable / partial
pass, 2 stop (``list``: a 2.3 value not reproduced; also argparse usage errors), 3 internal
error. The last stdout line is JSON (ASCII).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
import traceback
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

TOOL_PATH = Path(__file__).resolve()
DEFAULT_ROOT = TOOL_PATH.parents[4]
RULES_DIR_RELATIVE = Path("06_analysis/02_control/verif_matrix")
RULES_NAME = "las_k1_rules_adopt.md"
RULES_SHA_FILE_NAME = "las_k1_rules_adopt.sha256"
OUT_DIR_RELATIVE = Path("06_analysis/03_hydraulic/coupled/v5/las/k1")
LIST_OUT_NAME = "adopt_list.json"
JUDGE_OUT_NAME = "judge_adopt.json"
TOOL_NAME = "las_k1_adopt_judge"

# ---------------------------------------------------------------- sealed identity (2.3, K-0)
RULES_SHA256 = "864836d852b4a783a577f01f738536b7c30c574bf4bebb3b0219e68e59b07ea8"
SET_U, SET_A, SET_B, SET_E = "U", "A", "B", "E"
EXPECTED_SET_COUNTS = {SET_U: 300, SET_A: 74, SET_B: 43, SET_E: 183}
EXPECTED_LIST_SHA256 = {
    SET_U: "41e01c20e45400151120e3667f3805c0fad98a279ba50fb02c054d162a1ccd79",
    SET_A: "2e7a1a5f70231e4662fbb985aa8e50c3983d6788bfb889800b27a086457aa9d2",
    SET_B: "50622923473e9b05aec58513d7a76b739a040a5cd063c519f751bc9926b561c9",
    SET_E: "ae171b438318ada7a128adc26885a869d34345080fa6a99f362467a5d73bd473",
}
EXPECTED_E_REASONS = {"not_run_S9_level": 150, "soil_response_off": 33}
EXPECTED_A_FLOORS = {"UNIFORM_SOFT": 50, "PATCH": 6, "UNIFORM_G1": 18}
EXPECTED_A_SOFT_FLAT_SLOPE = {"flat": 32, "slope": 18}
EXPECTED_A_TAGS = {
    "final_SGS_R4": 31,
    "final_C4G2": 24,
    "-": 15,
    "final_C4G2_P3": 2,
    "final_C4G2_P3_LAS": 2,
}
EXPECTED_B_FLOORS = {"UNIFORM_SOFT": 31, "PATCH": 10, "UNIFORM_G1": 2}

# ---------------------------------------------------------------- population and selection (2)
POPULATION_DIRS = ("S9", "S9_merge")
RESULT_FILE_NAME = "result.json"
APPENDIX_ROW_DIR = "S9"
"""10.1: appendix A / B paths are ``<batch>/<row>`` under ``07_results/S9/``."""
SCM_SOILS = frozenset({"G1", "J1", "J2", "S1"})
SOFT_SOILS = frozenset({"J1", "J2", "S1"})
SOIL_META_KEYS = ("t_P_s", "soil_mode_t_s", "t_loc_s")
R4_FLAT_SOIL_MARGIN_M = 0.03
REASON_LOAD_ERROR = "load_error"
REASON_NOT_LEVEL = "not_run_S9_level"
REASON_NO_SCM_SOIL = "no_scm_soil_arg"
REASON_SOIL_OFF = "soil_response_off"
REASON_SOIL_FIELDS = "soil_meta_fields_missing"

# ---------------------------------------------------------------- shadow dP (3-4)
PERIOD_S = 0.1
LOC_EVENT = "crawler_liftoff_confirmed"
SOIL_MODE_EVENT = "soil_mode_start"
R4_APPLIED_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN"
R4_ORDER_SKIP_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order"
R4_SKIPPED_PREFIX = "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED"
SLOPE_MARGIN_EVENT = "INFO_LOC_CLEARANCE_MARGIN"
LOC_REVOKE_EVENT = "INFO_LOC_REVOKED"
GATE_PAIR_SUFFIXES = ("_gateoff", "_gateon")

# ---------------------------------------------------------------- records (7) and predictions (8)
THIN_MARGIN_PERIODS = 12
HISTOGRAM_BIN_PERIODS = 5
KNOWN_A_ROWS = frozenset(
    {
        "S9/batch_V5-LAS-K1-CHRONO_20261109_193952/SCh_G1_J2FL_B_top_Fs4_VB_gateoff/result.json",
        "S9/batch_V5-LAS-K1-CHRONO_20261109_193952/SCh_G1_J2FL_B_top_Fs4_VB_gateon/result.json",
    }
)
"""1.1: A rows whose t_P / t_S were seen before sealing (set A, PATCH)."""
KNOWN_B_ROWS = frozenset({"S9/batch_G6P_20261028_154030/G6_G1_B_top_Fs4_spJ2FL/result.json"})
"""1.1: the set B row seen before sealing (old controller, dP -20)."""

K_IDS = ("K-0", "K-1", "K-2", "K-3", "K-4", "K-5", "K-6", "K-7", "K-8")
GIT_TIMEOUT_S = 60.0
EXIT_INTERNAL_ERROR = 3
MISSING = object()


class Floor(StrEnum):
    """2.2 floor classification (from the row's ``args`` only)."""

    PATCH = "PATCH"
    UNIFORM_SOFT = "UNIFORM_SOFT"
    UNIFORM_G1 = "UNIFORM_G1"


class RowClass(StrEnum):
    """3.2 row classification of set A."""

    MUST = "MUST"
    PATCH = "PATCH"
    NEUTRAL_G1 = "NEUTRAL_G1"
    NONE = "NONE"


class Source(StrEnum):
    """4.3 where the t_P of one R4-evaluated LOC comes from."""

    DECISION = "a"
    FINAL_LOC = "b"
    NOT_STORED = "c"


class LocState(StrEnum):
    """4.5 state of one R4-evaluated LOC."""

    OK = "OK"
    BLOCKED_MISSING = "BLOCKED_MISSING"
    UNRECOVERABLE = "UNRECOVERABLE"


class Grade(StrEnum):
    """6.2 grades (the rules' words)."""

    STOP = "stop"
    FAIL = "미달"
    UNDECIDABLE = "판정 불가"
    PARTIAL = "부분 통과"
    PASS = "통과"


GRADE_CODES = {
    Grade.STOP: "stop",
    Grade.FAIL: "fail",
    Grade.UNDECIDABLE: "undecidable",
    Grade.PARTIAL: "partial",
    Grade.PASS: "pass",
}
GRADE_EXIT_CODES = {
    Grade.PASS: 0,
    Grade.FAIL: 1,
    Grade.UNDECIDABLE: 1,
    Grade.PARTIAL: 1,
    Grade.STOP: 2,
}
R4_KIND_APPLIED = "applied"
R4_KIND_GATE_BLOCKED = "gate_blocked"


# ================================================================ small helpers
def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    return sha256_bytes(path.read_bytes()) if path.is_file() else None


def is_number(value: Any) -> bool:
    """A finite JSON number (``bool`` is not a number here)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value)


def period_of(t_s: float) -> int:
    """4.1: whole control periods ``round(t / 0.1)`` on the stored float (round half to even,
    the same expression as ``c2.py`` ``_flat_soil_order_periods``)."""
    return round(t_s / PERIOD_S)


def event_base_name(name: str) -> str:
    """3.1: the event name before the first ``:`` (compared by exact equality)."""
    return name.split(":", 1)[0]


def dig(data: Any, *keys: str) -> Any:
    """``data[k0][k1]...`` or :data:`MISSING` when a level is absent or not a dict."""
    for key in keys:
        if not isinstance(data, dict) or key not in data:
            return MISSING
        data = data[key]
    return data


def is_error_block(value: Any) -> bool:
    """K-3: a run_S9 ``_record_or_error`` failure block ``{"error": ...}`` instead of the block."""
    return isinstance(value, dict) and set(value) == {"error"}


def plain(value: Any) -> Any:
    """JSON-ready copy (MISSING and non-finite floats as strings)."""
    if value is MISSING:
        return "<missing>"
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [plain(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def canonical_list_sha256(entries: Iterable[tuple[str, str]]) -> str:
    """2.4: sha256 of the byte-sorted ``<path>\\t<sha256>\\n`` lines (UTF-8, no BOM)."""
    lines = sorted(f"{path}\t{sha}\n".encode() for path, sha in entries)
    return sha256_bytes(b"".join(lines))


def appendix_result_path(batch_row: str) -> str:
    """10.1: appendix ``<batch>/<row>`` -> ``S9/<batch>/<row>/result.json`` (07_results based)."""
    return f"{APPENDIX_ROW_DIR}/{batch_row}/{RESULT_FILE_NAME}"


def min_median_max(values: list[int]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "min": None, "median": None, "max": None}
    return {
        "n": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
    }


def histogram(values: list[int]) -> dict[str, int]:
    """7: dP histogram in 5-period bins ``[a, a+5)``."""
    bins = Counter((value // HISTOGRAM_BIN_PERIODS) * HISTOGRAM_BIN_PERIODS for value in values)
    return {f"[{start},{start + HISTOGRAM_BIN_PERIODS})": bins[start] for start in sorted(bins)}


# ================================================================ git queries (read only)
def run_git(root: Path, *args: str) -> tuple[int | None, str, str | None]:
    """One read-only git query; (return code, stdout, error). Failures are returned."""
    kwargs: dict[str, Any] = {
        "cwd": str(root),
        "capture_output": True,
        "timeout": GIT_TIMEOUT_S,
        "stdin": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        done = subprocess.run(["git", *args], check=False, **kwargs)  # noqa: S603, S607
    except (OSError, subprocess.SubprocessError) as error:
        return None, "", f"{type(error).__name__}: {error}"
    stderr = done.stderr.decode("utf-8", "replace").strip()
    return done.returncode, done.stdout.decode("utf-8", "replace"), stderr or None


def git_record(root: Path, is_disabled: bool) -> dict[str, Any]:
    """10.1: ``git rev-parse HEAD`` and ``git status --porcelain`` (record only)."""
    if is_disabled:
        return {"queried": False}
    head_code, head_out, head_error = run_git(root, "rev-parse", "HEAD")
    status_code, status_out, status_error = run_git(root, "status", "--porcelain")
    return {
        "queried": True,
        "head": head_out.strip() if head_code == 0 else None,
        "head_error": None if head_code == 0 else head_error,
        "status_porcelain": status_out.splitlines() if status_code == 0 else None,
        "status_error": None if status_code == 0 else status_error,
    }


# ================================================================ sealed appendices (2.3, 10.1)
@dataclass(frozen=True)
class AppendixRow:
    """One row of appendix A or B."""

    number: int
    path: str
    """``07_results`` based ``S9/<batch>/<row>/result.json``."""
    floor: str
    sha256: str


@dataclass
class SealedLists:
    """Appendices A, B and C parsed from the rules file."""

    rows_a: list[AppendixRow] = field(default_factory=list)
    rows_b: list[AppendixRow] = field(default_factory=list)
    rows_e: list[tuple[str, str, str]] = field(default_factory=list)
    """(reason, path, sha256) of appendix C."""
    problems: list[str] = field(default_factory=list)

    def sealed_paths(self) -> set[str]:
        paths = {row.path for row in self.rows_a} | {row.path for row in self.rows_b}
        return paths | {path for _, path, _ in self.rows_e}


def is_sha256_hex(text: str) -> bool:
    return len(text) == 64 and all(char in "0123456789abcdef" for char in text)


def section_lines(lines: list[str], heading_prefix: str) -> list[str]:
    """The lines after the heading that starts with ``heading_prefix`` up to the next ``## ``."""
    for index, line in enumerate(lines):
        if line.startswith(heading_prefix):
            body: list[str] = []
            for following in lines[index + 1 :]:
                if following.startswith("## "):
                    break
                body.append(following)
            return body
    return []


def strip_code(cell: str) -> str:
    return cell.strip().strip("`")


def parse_appendix_table(
    lines: list[str], heading_prefix: str, problems: list[str]
) -> list[AppendixRow]:
    """Appendix A / B: ``| # | path | floor | ... | sha256 |`` rows (12 cells)."""
    rows: list[AppendixRow] = []
    for line in section_lines(lines, heading_prefix):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 12 or not cells[0].isdigit():
            continue
        batch_row = strip_code(cells[1])
        sha = strip_code(cells[11])
        number = int(cells[0])
        if number != len(rows) + 1:
            problems.append(f"{heading_prefix}: row number {number} out of order")
        if batch_row.count("/") != 1 or batch_row.startswith(("/", APPENDIX_ROW_DIR + "/")):
            problems.append(f"{heading_prefix} #{number}: path not <batch>/<row>: {batch_row}")
        if not is_sha256_hex(sha):
            problems.append(f"{heading_prefix} #{number}: sha256 not 64 lowercase hex: {sha}")
        rows.append(AppendixRow(number, appendix_result_path(batch_row), cells[2], sha))
    return rows


def parse_appendix_c(lines: list[str], problems: list[str]) -> list[tuple[str, str, str]]:
    """Appendix C: ``reason<TAB>path<TAB>sha256`` lines."""
    rows: list[tuple[str, str, str]] = []
    for line in section_lines(lines, "## 부록 C"):
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        reason, path, sha = parts
        if not is_sha256_hex(sha):
            problems.append(f"appendix C: sha256 not 64 lowercase hex: {path}")
        rows.append((reason, path, sha))
    return rows


def parse_sealed_lists(rules_text: str) -> SealedLists:
    """Parse appendices A, B, C and check their counts and canonical list sha256."""
    lines = rules_text.splitlines()
    sealed = SealedLists()
    sealed.rows_a = parse_appendix_table(lines, "## 부록 A", sealed.problems)
    sealed.rows_b = parse_appendix_table(lines, "## 부록 B", sealed.problems)
    sealed.rows_e = parse_appendix_c(lines, sealed.problems)
    parsed = {
        SET_A: [(row.path, row.sha256) for row in sealed.rows_a],
        SET_B: [(row.path, row.sha256) for row in sealed.rows_b],
        SET_E: [(path, sha) for _, path, sha in sealed.rows_e],
    }
    for set_name, entries in parsed.items():
        if len(entries) != EXPECTED_SET_COUNTS[set_name]:
            sealed.problems.append(
                f"appendix {set_name}: {len(entries)} rows, want {EXPECTED_SET_COUNTS[set_name]}"
            )
        if canonical_list_sha256(entries) != EXPECTED_LIST_SHA256[set_name]:
            sealed.problems.append(f"appendix {set_name}: canonical list sha256 differs from 2.3")
    return sealed


def read_rules(rules_path: Path) -> tuple[bytes | None, str | None]:
    if not rules_path.is_file():
        return None, None
    data = rules_path.read_bytes()
    return data, data.decode("utf-8")


# ================================================================ selection rules (2.1-2.2)
def floor_class(args: dict[str, Any]) -> Floor | None:
    """2.2 floor classification from ``args.soil`` / ``args.soil_patch``; None outside SCM soils."""
    soil = args.get("soil")
    patch = args.get("soil_patch")
    if isinstance(patch, str) and patch.strip():
        patch_soils = {item.split(":", 1)[-1].strip() for item in patch.split(",")}
        if patch_soils != {soil}:
            return Floor.PATCH
    if soil in SOFT_SOILS:
        return Floor.UNIFORM_SOFT
    if soil == "G1":
        return Floor.UNIFORM_G1
    return None


def selection(document: Any) -> tuple[str, str | None]:
    """2.2 S0-S5: (set name, exclusion reason). ``document`` None = not readable JSON."""
    if document is None:
        return SET_E, REASON_LOAD_ERROR
    if not isinstance(document, dict) or document.get("action") != "level":
        return SET_E, REASON_NOT_LEVEL
    args = document.get("args")
    if not isinstance(args, dict) or args.get("soil") not in SCM_SOILS:
        return SET_E, REASON_NO_SCM_SOIL
    soil = dig(document, "controller_meta", "soil")
    if dig(soil, "settings", "enable") is not True:
        return SET_E, REASON_SOIL_OFF
    if not all(key in soil for key in SOIL_META_KEYS):
        return SET_E, REASON_SOIL_FIELDS
    margin_m = dig(document, "controller_meta", "slope_clearance_margin", "settings")
    margin_m = dig(margin_m, "flat_soil_margin_m")
    is_r4_controller = is_number(margin_m) and margin_m == R4_FLAT_SOIL_MARGIN_M
    return (SET_A if is_r4_controller else SET_B), None


def args_record(args: Any) -> dict[str, Any]:
    """Run-condition arguments recorded per row (7); never t_P, t_S or event values."""
    if not isinstance(args, dict):
        return {}
    keys = (
        "case",
        "soil",
        "soil_patch",
        "pad_variant",
        "level",
        "floor_roll",
        "floor_pitch",
        "mass_scale",
        "fs_kN",
        "expect_controller",
    )
    return {key: args.get(key) for key in keys}


def is_sloped(args: dict[str, Any]) -> bool:
    return any(
        is_number(args.get(key)) and args.get(key) != 0 for key in ("floor_roll", "floor_pitch")
    )


def load_json_bytes(data: bytes) -> Any:
    """The document, or None when the bytes are not UTF-8 JSON (S0)."""
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


# ================================================================ list: scan of U (2.1-2.4)
@dataclass(frozen=True)
class ScanEntry:
    """One result.json of U: metadata only."""

    path: str
    sha256: str
    set_name: str
    reason: str | None
    floor: str | None
    args: dict[str, Any]
    is_sealed: bool


def population_files(results_root: Path) -> list[Path]:
    """2.1: every file named exactly ``result.json`` at any depth under S9 and S9_merge."""
    files: list[Path] = []
    for directory_name in POPULATION_DIRS:
        top = results_root / directory_name
        if not top.is_dir():
            continue
        for directory, _, names in os.walk(top):
            files.extend(Path(directory) / name for name in names if name == RESULT_FILE_NAME)
    return files


def relative_result_path(results_root: Path, path: Path) -> str:
    return path.relative_to(results_root).as_posix()


def scan_population(results_root: Path, sealed_paths: set[str]) -> list[ScanEntry]:
    """Read and classify every file of U; documents are dropped after classification."""
    entries: list[ScanEntry] = []
    for path in population_files(results_root):
        data = path.read_bytes()
        document = load_json_bytes(data)
        set_name, reason = selection(document)
        args = document.get("args") if isinstance(document, dict) else None
        floor = floor_class(args) if isinstance(args, dict) else None
        relative = relative_result_path(results_root, path)
        entries.append(
            ScanEntry(
                path=relative,
                sha256=sha256_bytes(data),
                set_name=set_name,
                reason=reason,
                floor=None if floor is None else str(floor),
                args=args_record(args),
                is_sealed=relative in sealed_paths,
            )
        )
    return sorted(entries, key=lambda entry: entry.path.encode("utf-8"))


def compare_counts(name: str, got: dict[str, int], want: dict[str, int]) -> dict[str, Any]:
    return {"name": name, "got": dict(sorted(got.items())), "want": want, "ok": got == want}


def list_comparisons(sealed_entries: list[ScanEntry]) -> list[dict[str, Any]]:
    """2.3: counts, canonical list sha256 and the breakdowns of A, B, E (sealed population)."""
    by_set = {
        name: [e for e in sealed_entries if e.set_name == name] for name in (SET_A, SET_B, SET_E)
    }
    comparisons: list[dict[str, Any]] = []
    for set_name, entries in by_set.items():
        sha = canonical_list_sha256((entry.path, entry.sha256) for entry in entries)
        comparisons.append(
            {
                "name": f"{set_name}_list",
                "count": len(entries),
                "want_count": EXPECTED_SET_COUNTS[set_name],
                "sha256": sha,
                "want_sha256": EXPECTED_LIST_SHA256[set_name],
                "ok": len(entries) == EXPECTED_SET_COUNTS[set_name]
                and sha == EXPECTED_LIST_SHA256[set_name],
            }
        )
    rows_a, rows_b = by_set[SET_A], by_set[SET_B]
    soft_a = [entry for entry in rows_a if entry.floor == Floor.UNIFORM_SOFT]
    comparisons += [
        compare_counts("E_reasons", Counter(e.reason for e in by_set[SET_E]), EXPECTED_E_REASONS),
        compare_counts("A_floors", Counter(e.floor for e in rows_a), EXPECTED_A_FLOORS),
        compare_counts(
            "A_soft_flat_slope",
            Counter("slope" if is_sloped(e.args) else "flat" for e in soft_a),
            EXPECTED_A_SOFT_FLAT_SLOPE,
        ),
        compare_counts(
            "A_tags",
            Counter(e.args.get("expect_controller") or "-" for e in rows_a),
            EXPECTED_A_TAGS,
        ),
        compare_counts("B_floors", Counter(e.floor for e in rows_b), EXPECTED_B_FLOORS),
    ]
    return comparisons


def build_list_report(results_root: Path, sealed: SealedLists) -> dict[str, Any]:
    """Sections 2.1-2.4 independently of the scan tool of 2.5.

    2.6: files that appear after sealing are recorded but kept out of A / B / E, so K-1
    compares the sealed population only. U is recorded (count and sha) and not judged.
    """
    sealed_paths = sealed.sealed_paths()
    entries = scan_population(results_root, sealed_paths)
    sealed_entries = [entry for entry in entries if entry.is_sealed]
    present = {entry.path for entry in entries}
    comparisons = list_comparisons(sealed_entries)
    u_sha = canonical_list_sha256((entry.path, entry.sha256) for entry in entries)
    return {
        "results_root": str(results_root),
        "population": {
            "count": len(entries),
            "sha256": u_sha,
            "sealed_count": EXPECTED_SET_COUNTS[SET_U],
            "sealed_sha256": EXPECTED_LIST_SHA256[SET_U],
            "same_as_sealed": u_sha == EXPECTED_LIST_SHA256[SET_U],
        },
        "comparisons": comparisons,
        "ok": all(item["ok"] for item in comparisons) and not sealed.problems,
        "appendix_problems": sealed.problems,
        "post_seal_new_files": [asdict(entry) for entry in entries if not entry.is_sealed],
        "sealed_files_missing": sorted(sealed_paths - present),
        "files": [asdict(entry) for entry in sealed_entries],
    }


# ================================================================ judge: one row of A (3-5)
@dataclass
class LocRecord:
    """One R4-evaluated LOC (7)."""

    row: str
    floor: str
    row_class: str
    kind: str
    t_R_s: float
    n_R: int
    source: str
    state: str
    t_P_s: float | None
    t_S_s: float | None
    n_P: int | None
    n_S: int | None
    dP: int | None
    loc_revokes: int
    is_known_row: bool
    case: str
    tag: str
    level: Any
    floor_roll: Any
    floor_pitch: Any
    mass_scale: Any
    fs_kN: Any
    n_R_minus_n_S: int | None


@dataclass
class RowRecord:
    """One row of A (7)."""

    row: str
    floor: str
    row_class: str
    r4_locs: int
    e3c10_locs: int
    soil_mode_starts: int
    locs: int
    loc_revokes: int
    none_reason: str | None
    is_known_row: bool
    gate_on: bool
    has_decisions: bool
    case: str
    tag: str
    git_head: Any
    flags: list[str] = field(default_factory=list)


@dataclass
class RowAnalysis:
    record: RowRecord | None
    locs: list[LocRecord]
    problems: dict[str, list[str]]


def new_problem_map() -> dict[str, list[str]]:
    return {check_id: [] for check_id in K_IDS}


def structure_problems(document: Any) -> list[str]:
    """K-3: the blocks are dict / list (no ``{"error": ...}``), ``restored_from`` is None,
    and every event is ``{t_s: finite number, name: str}``."""
    if not isinstance(document, dict):
        return ["document is not an object"]
    problems: list[str] = []
    meta = document.get("controller_meta")
    soil = dig(document, "controller_meta", "soil")
    if not isinstance(meta, dict) or is_error_block(meta):
        problems.append("controller_meta not a block")
    if not isinstance(soil, dict) or is_error_block(soil):
        problems.append("controller_meta.soil not a block")
    elif soil.get("restored_from") is not None:
        problems.append("controller_meta.soil.restored_from is not None")
    events = document.get("events")
    if not isinstance(events, list):
        problems.append("events not a list")
    elif not all(
        isinstance(event, dict)
        and is_number(event.get("t_s"))
        and isinstance(event.get("name"), str)
        for event in events
    ):
        problems.append("events item not {t_s: number, name: str}")
    if not isinstance(document.get("args"), dict):
        problems.append("args not an object")
    return problems


def event_pairs(document: dict[str, Any]) -> list[tuple[float, str]]:
    return [(float(event["t_s"]), event["name"]) for event in document["events"]]


def r4_evaluated_events(
    events: list[tuple[float, str]], is_gate_on: bool
) -> tuple[list[tuple[float, str]], int]:
    """3.1: (t_R, kind) of the R4-evaluated LOC events, and the count of ``_SKIPPED:order``
    events in a gate-off row (a K-6 contradiction, not an R4 LOC)."""
    found: list[tuple[float, str]] = []
    gate_off_skips = 0
    for t_s, name in events:
        if event_base_name(name) == R4_APPLIED_EVENT:
            found.append((t_s, R4_KIND_APPLIED))
        elif name == R4_ORDER_SKIP_EVENT:
            if is_gate_on:
                found.append((t_s, R4_KIND_GATE_BLOCKED))
            else:
                gate_off_skips += 1
    return found, gate_off_skips


def periods_of_event(events: list[tuple[float, str]], full_name: str) -> list[int]:
    return [period_of(t_s) for t_s, name in events if name == full_name]


def latest_before(times: list[float], n_R: int) -> tuple[int, float] | None:
    """4.4: the latest (period, time) with period < n_R (a start in the LOC period comes
    after the LOC); None when there is none."""
    earlier = [(period_of(t_s), t_s) for t_s in times if period_of(t_s) < n_R]
    return max(earlier) if earlier else None


def soil_start_path_2(
    soil: dict[str, Any], event_start: tuple[int, float] | None, n_R: int
) -> tuple[int | None, str | None]:
    """4.4 path 2: ``mode_starts``, else ``soil_mode_t_s`` (falling back to the events when
    the last start is in or after the LOC period). (n_S, problem)."""
    mode_starts = soil.get("mode_starts")
    if isinstance(mode_starts, list):
        times = [start.get("t_s") for start in mode_starts if isinstance(start, dict)]
        if not all(is_number(t_s) for t_s in times) or len(times) != len(mode_starts):
            return None, "mode_starts item without a numeric t_s"
        found = latest_before([float(t_s) for t_s in times], n_R)
        return (None if found is None else found[0]), None
    last_start = soil.get("soil_mode_t_s")
    if not is_number(last_start):
        return None, None
    n_last = period_of(float(last_start))
    if n_last < n_R:
        return n_last, None
    if event_start is not None and not n_last > event_start[0]:
        return None, "soil_mode_t_s period not after the latest earlier soil_mode_start"
    return (None if event_start is None else event_start[0]), None


def decision_period(decision: Any) -> int | None:
    t_loc_s = dig(decision, "t_loc_s")
    return period_of(float(t_loc_s)) if is_number(t_loc_s) else None


def decisions_for(decisions: list[Any], n_loc: int) -> list[dict[str, Any]]:
    """4.3 (a): decisions of the LOC period with ``r4_due_without_gate`` true."""
    return [
        decision
        for decision in decisions
        if isinstance(decision, dict)
        and decision_period(decision) == n_loc
        and decision.get("r4_due_without_gate") is True
    ]


def k6_row_problems(
    decisions: list[Any] | None,
    is_gate_on: bool,
    r4_events: list[tuple[float, str]],
    gate_off_skips: int,
) -> list[str]:
    """K-6 row-level part: decision set = R4 LOC set, gate-off skips, gate-on applied LOCs."""
    problems: list[str] = []
    if gate_off_skips:
        problems.append(f"{gate_off_skips} {R4_ORDER_SKIP_EVENT} event(s) in a gate-off row")
    if decisions is None:
        if is_gate_on:
            problems.append("gate on without order_gate.decisions")
        return problems
    if not all(decision_period(d) is not None for d in decisions):
        problems.append("decision without a numeric t_loc_s")
    due_periods = {
        decision_period(d)
        for d in decisions
        if isinstance(d, dict) and d.get("r4_due_without_gate") is True
    }
    r4_periods = {period_of(t_s) for t_s, _ in r4_events}
    if due_periods != r4_periods:
        problems.append(
            f"r4_due decision periods {sorted(due_periods)} != R4 LOC {sorted(r4_periods)}"
        )
    if is_gate_on:
        for t_s, kind in r4_events:
            matches = decisions_for(decisions, period_of(t_s))
            if kind == R4_KIND_APPLIED and any(d.get("would_block") is not False for d in matches):
                problems.append(f"gate on, applied at n={period_of(t_s)} but would_block not false")
    return problems


def k7_problems(document: dict[str, Any], decisions: list[Any] | None) -> list[str]:
    """K-7: ``controller_meta.soil`` = ``c2_soil`` on the three keys; the final-LOC decision
    t_P_s = ``controller_meta.soil.t_P_s``."""
    soil = document["controller_meta"]["soil"]
    copy = document.get("c2_soil")
    if not isinstance(copy, dict):
        return ["c2_soil not an object"]
    problems = [
        f"{key}: controller_meta.soil {soil.get(key)!r} != c2_soil {copy.get(key, MISSING)!r}"
        for key in SOIL_META_KEYS
        if key not in copy or copy[key] != soil.get(key)
    ]
    final_t_loc = soil.get("t_loc_s")
    if decisions is not None and is_number(final_t_loc):
        n_final = period_of(float(final_t_loc))
        for decision in decisions:
            if decision_period(decision) == n_final and decision.get("t_P_s") != soil.get("t_P_s"):
                problems.append(
                    f"final-LOC decision t_P_s != controller_meta.soil.t_P_s (n={n_final})"
                )
    return problems


@dataclass
class TPResolution:
    source: Source
    t_P_s: float | None
    decision: dict[str, Any] | None
    problem_k3: str | None = None
    problem_k6: str | None = None


def resolve_t_P(soil: dict[str, Any], decisions: list[Any] | None, n_R: int) -> TPResolution:
    """4.3: t_P of one R4-evaluated LOC by source (a), (b) or (c)."""
    if decisions is not None:
        matches = decisions_for(decisions, n_R)
        if len(matches) != 1:
            return TPResolution(
                Source.DECISION, None, None, problem_k6=f"{len(matches)} decisions for n={n_R}"
            )
        return checked_t_P(Source.DECISION, matches[0].get("t_P_s"), matches[0])
    final_t_loc = soil.get("t_loc_s")
    if is_number(final_t_loc) and period_of(float(final_t_loc)) == n_R:
        return checked_t_P(Source.FINAL_LOC, soil.get("t_P_s"), None)
    return TPResolution(Source.NOT_STORED, None, None)


def checked_t_P(source: Source, value: Any, decision: dict[str, Any] | None) -> TPResolution:
    if value is None or is_number(value):
        return TPResolution(source, None if value is None else float(value), decision)
    return TPResolution(source, None, decision, problem_k3=f"t_P_s not a number: {value!r}")


def loc_state(resolution: TPResolution) -> LocState:
    """4.5: (c) -> UNRECOVERABLE, t_P None -> BLOCKED_MISSING, else OK."""
    if resolution.source is Source.NOT_STORED or resolution.problem_k6 or resolution.problem_k3:
        return LocState.UNRECOVERABLE
    if resolution.t_P_s is None:
        return LocState.BLOCKED_MISSING
    return LocState.OK


def row_class_of(floor: Floor | None, r4_count: int) -> RowClass:
    """3.2."""
    if r4_count == 0:
        return RowClass.NONE
    if floor is Floor.UNIFORM_SOFT:
        return RowClass.MUST
    if floor is Floor.PATCH:
        return RowClass.PATCH
    return RowClass.NEUTRAL_G1


def none_reason(row_class: RowClass, soil_starts: int, e3c10_locs: int) -> str | None:
    """7: why a row has no R4-evaluated LOC."""
    if row_class is not RowClass.NONE:
        return None
    if soil_starts == 0:
        return "no_soil_mode"
    if e3c10_locs:
        return "e3c10"
    return "other"


def k5_problems(r4_events: list[tuple[float, str]], loc_periods: list[int]) -> list[str]:
    """K-5: every n_R is a LOC period and carries one R4 event only."""
    problems: list[str] = []
    counts = Counter(period_of(t_s) for t_s, _ in r4_events)
    for n_R, count in sorted(counts.items()):
        if n_R not in loc_periods:
            problems.append(f"R4 event n={n_R} is not a {LOC_EVENT} period")
        if count > 1:
            problems.append(f"{count} R4 events at n={n_R}")
    return problems


def analyze_row(path: str, document: Any, is_known: bool) -> RowAnalysis:
    """K-3..K-8 and the LOC records of one row of A."""
    problems = new_problem_map()
    problems["K-3"] = [f"{path}: {text}" for text in structure_problems(document)]
    if problems["K-3"]:
        return RowAnalysis(None, [], problems)
    meta = document["controller_meta"]
    soil = meta["soil"]
    args = document["args"]
    if meta.get("period_s") != PERIOD_S:
        problems["K-4"].append(f"{path}: period_s {meta.get('period_s')!r}")
    events = event_pairs(document)
    order_gate = dig(meta, "slope_clearance_margin", "order_gate")
    is_gate_on = isinstance(order_gate, dict) and order_gate.get("enabled") is True
    decisions = order_gate.get("decisions") if isinstance(order_gate, dict) else None
    if decisions is not None and not isinstance(decisions, list):
        problems["K-6"].append(f"{path}: order_gate.decisions not a list")
        decisions = None
    r4_events, gate_off_skips = r4_evaluated_events(events, is_gate_on)
    loc_periods = periods_of_event(events, LOC_EVENT)
    problems["K-5"] += [f"{path}: {t}" for t in k5_problems(r4_events, loc_periods)]
    problems["K-6"] += [
        f"{path}: {t}" for t in k6_row_problems(decisions, is_gate_on, r4_events, gate_off_skips)
    ]
    problems["K-7"] += [f"{path}: {t}" for t in k7_problems(document, decisions)]
    floor = floor_class(args)
    record = build_row_record(path, document, floor, events, r4_events, is_known, is_gate_on)
    record.has_decisions = decisions is not None
    soil_start_times = [t_s for t_s, name in events if name == SOIL_MODE_EVENT]
    locs = [
        analyze_loc(path, record, soil, decisions, soil_start_times, t_R, kind, args, problems)
        for t_R, kind in r4_events
    ]
    return RowAnalysis(record, locs, problems)


def build_row_record(
    path: str,
    document: dict[str, Any],
    floor: Floor | None,
    events: list[tuple[float, str]],
    r4_events: list[tuple[float, str]],
    is_known: bool,
    is_gate_on: bool,
) -> RowRecord:
    args = document["args"]
    bases = Counter(event_base_name(name) for _, name in events)
    row_class = row_class_of(floor, len(r4_events))
    soil_starts = sum(1 for _, name in events if name == SOIL_MODE_EVENT)
    return RowRecord(
        row=path,
        floor="-" if floor is None else str(floor),
        row_class=str(row_class),
        r4_locs=len(r4_events),
        e3c10_locs=bases[SLOPE_MARGIN_EVENT],
        soil_mode_starts=soil_starts,
        locs=sum(1 for _, name in events if name == LOC_EVENT),
        loc_revokes=bases[LOC_REVOKE_EVENT],
        none_reason=none_reason(row_class, soil_starts, bases[SLOPE_MARGIN_EVENT]),
        is_known_row=is_known,
        gate_on=is_gate_on,
        has_decisions=False,
        case=str(args.get("case") or Path(path).parent.name),
        tag=str(args.get("expect_controller") or "-"),
        git_head=dig(document, "code_state", "git_at_start", "head"),
    )


def analyze_loc(
    path: str,
    record: RowRecord,
    soil: dict[str, Any],
    decisions: list[Any] | None,
    soil_start_times: list[float],
    t_R: float,
    kind: str,
    args: dict[str, Any],
    problems: dict[str, list[str]],
) -> LocRecord:
    """4.3-4.5 for one R4-evaluated LOC; K-3 / K-6 / K-8 problems are added to ``problems``."""
    n_R = period_of(t_R)
    resolution = resolve_t_P(soil, decisions, n_R)
    if resolution.problem_k3:
        problems["K-3"].append(f"{path} n={n_R}: {resolution.problem_k3}")
    if resolution.problem_k6:
        problems["K-6"].append(f"{path} n={n_R}: {resolution.problem_k6}")
    event_start = latest_before(soil_start_times, n_R)
    problems["K-8"] += [
        f"{path} n={n_R}: {text}"
        for text in k8_problems(soil, event_start, resolution.decision, n_R)
    ]
    state = loc_state(resolution)
    n_S = None if event_start is None else event_start[0]
    n_P = None if resolution.t_P_s is None else period_of(resolution.t_P_s)
    dP = n_P - n_S if state is LocState.OK and n_P is not None and n_S is not None else None
    return LocRecord(
        row=path,
        floor=record.floor,
        row_class=record.row_class,
        kind=kind,
        t_R_s=t_R,
        n_R=n_R,
        source=str(resolution.source),
        state=str(state),
        t_P_s=resolution.t_P_s,
        t_S_s=None if event_start is None else event_start[1],
        n_P=n_P,
        n_S=n_S,
        dP=dP,
        loc_revokes=record.loc_revokes,
        is_known_row=record.is_known_row,
        case=record.case,
        tag=record.tag,
        level=args.get("level"),
        floor_roll=args.get("floor_roll"),
        floor_pitch=args.get("floor_pitch"),
        mass_scale=args.get("mass_scale"),
        fs_kN=args.get("fs_kN"),
        n_R_minus_n_S=None if n_S is None else n_R - n_S,
    )


def k8_problems(
    soil: dict[str, Any],
    event_start: tuple[int, float] | None,
    decision: dict[str, Any] | None,
    n_R: int,
) -> list[str]:
    """K-8: a soil-mode start before n_R exists; path 1 = path 2; = decision t_S_s period."""
    if event_start is None:
        return [f"no {SOIL_MODE_EVENT} with period < {n_R}"]
    problems: list[str] = []
    n_S_path_2, path_2_problem = soil_start_path_2(soil, event_start, n_R)
    if path_2_problem:
        problems.append(path_2_problem)
    if n_S_path_2 != event_start[0]:
        problems.append(f"n_S path 1 {event_start[0]} != path 2 {n_S_path_2}")
    if decision is not None:
        t_S = decision.get("t_S_s")
        n_S_decision = period_of(float(t_S)) if is_number(t_S) else None
        if n_S_decision != event_start[0]:
            problems.append(f"n_S path 1 {event_start[0]} != decision t_S_s period {n_S_decision}")
    return problems


# ================================================================ judge: summary, grade (6-8)
def is_k1_block(loc: LocRecord) -> bool:
    """K1 on would have blocked R4: OK with dP <= 0, or BLOCKED_MISSING."""
    if loc.state == LocState.BLOCKED_MISSING:
        return True
    return loc.state == LocState.OK and loc.dP is not None and loc.dP <= 0


def locs_of(locs: list[LocRecord], row_class: RowClass) -> list[LocRecord]:
    return [loc for loc in locs if loc.row_class == row_class]


def state_counts(locs: list[LocRecord]) -> dict[str, int]:
    counts = Counter(loc.state for loc in locs)
    return {str(state): counts[str(state)] for state in LocState}


def patch_condition(patch_locs: list[LocRecord]) -> dict[str, Any]:
    """6.1 ②: >= 1 OK / BLOCKED_MISSING LOC and every LOC blocked (OK dP <= 0 or missing)."""
    countable = [loc for loc in patch_locs if loc.state != LocState.UNRECOVERABLE]
    return {
        "locs": len(patch_locs),
        "countable": len(countable),
        "all_blocked": all(is_k1_block(loc) for loc in patch_locs),
        "ok": bool(countable) and all(is_k1_block(loc) for loc in patch_locs),
    }


def decide_grade(
    k_checks: list[dict[str, Any]], locs: list[LocRecord]
) -> tuple[Grade, list[str], dict[str, Any]]:
    """6.2: the first grade whose condition holds, its reasons and the 6.1 conditions."""
    must = locs_of(locs, RowClass.MUST)
    patch = locs_of(locs, RowClass.PATCH)
    must_ok = [loc for loc in must if loc.state == LocState.OK]
    condition_1 = bool(must_ok) and all(
        loc.state == LocState.OK and loc.dP is not None and loc.dP > 0 for loc in must
    )
    condition_2 = patch_condition(patch)
    unknown_patch = patch_condition([loc for loc in patch if not loc.is_known_row])
    conditions = {
        "condition_1_must": condition_1,
        "condition_2_patch": condition_2,
        "condition_2_patch_without_known_rows": unknown_patch,
        "condition_2_known_rows_only": condition_2["ok"] and unknown_patch["locs"] == 0,
    }
    failed = [check["id"] for check in k_checks if check["ok"] is False]
    if failed:
        return Grade.STOP, [f"{check_id} false" for check_id in failed], conditions
    must_blocked = [loc for loc in must if is_k1_block(loc)]
    if must_blocked:
        return (
            Grade.FAIL,
            [f"MUST LOC blocked: {loc.row} n={loc.n_R}" for loc in must_blocked],
            conditions,
        )
    must_unrecoverable = [loc for loc in must if loc.state == LocState.UNRECOVERABLE]
    if not must_ok or must_unrecoverable:
        reasons = ["MUST OK LOC 0"] if not must_ok else []
        reasons += [f"MUST LOC UNRECOVERABLE: {loc.row} n={loc.n_R}" for loc in must_unrecoverable]
        return Grade.UNDECIDABLE, reasons, conditions
    if not condition_2["ok"]:
        return Grade.PARTIAL, ["condition 2 (PATCH) false"], conditions
    reasons = ["conditions 1 and 2 true"]
    if conditions["condition_2_known_rows_only"]:
        reasons.append("condition 2 rests on the rows known before sealing only (6.1)")
    return Grade.PASS, reasons, conditions


def class_summary(locs: list[LocRecord]) -> dict[str, Any]:
    ok_dP = [loc.dP for loc in locs if loc.state == LocState.OK and loc.dP is not None]
    unique_locs = {(Path(loc.row).parent.parent.name, pair_case(loc.case), loc.n_R) for loc in locs}
    return {
        "locs": len(locs),
        "unique_locs": len(unique_locs),
        "rows": len({loc.row for loc in locs}),
        "states": state_counts(locs),
        "dP": min_median_max(ok_dP),
        "histogram": histogram(ok_dP),
    }


def pair_case(case: str) -> str:
    """3 / 11 #3: the S-Ch gateoff / gateon pair is one LOC (case without the gate suffix)."""
    for suffix in GATE_PAIR_SUFFIXES:
        if case.endswith(suffix):
            return case[: -len(suffix)]
    return case


def minimum_by(locs: list[LocRecord], key_of: Any) -> list[dict[str, Any]]:
    groups: dict[Any, list[int]] = {}
    for loc in locs:
        if loc.state == LocState.OK and loc.dP is not None:
            groups.setdefault(key_of(loc), []).append(loc.dP)
    return [
        {"key": list(key) if isinstance(key, tuple) else key, "dP_min": min(values)}
        for key, values in sorted(groups.items())
    ]


def build_summary(locs: list[LocRecord], rows: list[RowRecord]) -> dict[str, Any]:
    must = locs_of(locs, RowClass.MUST)
    none_rows = [row for row in rows if row.row_class == RowClass.NONE]
    return {
        "by_class": {
            str(rc): class_summary(locs_of(locs, rc)) for rc in RowClass if rc is not RowClass.NONE
        },
        "rows_by_class": dict(Counter(row.row_class for row in rows)),
        "must_row_min": minimum_by(must, lambda loc: loc.row),
        "must_case_tag_min": minimum_by(must, lambda loc: (loc.case, loc.tag)),
        "e3c10_locs": sum(row.e3c10_locs for row in rows),
        "rows_with_soil_mode": sum(1 for row in rows if row.soil_mode_starts > 0),
        "none_reasons": dict(Counter(row.none_reason for row in none_rows)),
    }


def build_flags(
    locs: list[LocRecord], rows: list[RowRecord], set_b: dict[str, Any]
) -> dict[str, Any]:
    """7 FLAG (no effect on the grade)."""
    thin = [
        {"row": loc.row, "n_R": loc.n_R, "dP": loc.dP}
        for loc in locs_of(locs, RowClass.MUST)
        if loc.state == LocState.OK and loc.dP is not None and loc.dP <= THIN_MARGIN_PERIODS
    ]
    neutral_block = [loc for loc in locs_of(locs, RowClass.NEUTRAL_G1) if is_k1_block(loc)]
    revoked_after = [row.row for row in rows if "REVOKED_AFTER_R4" in row.flags]
    return {
        "THIN_MARGIN": thin,
        "NEUTRAL_G1_BLOCK": len(neutral_block),
        "MULTI_LOC": [row.row for row in rows if row.r4_locs >= 2],
        "REVOKED_AFTER_R4": revoked_after,
        "B_SOFT_NONPOS": set_b["B_SOFT_NONPOS"],
    }


def mark_revoked_after_r4(
    document: dict[str, Any], record: RowRecord, locs: list[LocRecord]
) -> None:
    """7 REVOKED_AFTER_R4: a LOC revocation in a period after an R4-evaluated LOC."""
    revoke_periods = [
        period_of(t_s)
        for t_s, name in event_pairs(document)
        if event_base_name(name) == LOC_REVOKE_EVENT
    ]
    if any(n_rev > loc.n_R for loc in locs for n_rev in revoke_periods):
        record.flags.append("REVOKED_AFTER_R4")


def inside(value: Any, low: float, high: float) -> bool:
    return value is not None and low <= value <= high


def build_predictions(
    locs: list[LocRecord],
    rows: list[RowRecord],
    flags: dict[str, Any],
    set_b: dict[str, Any],
    grade: Grade,
    is_k_all_true: bool,
    row_args: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """8 P-1..P-10: inside / outside the prediction (not a criterion)."""
    must_rows = [row for row in rows if row.row_class == RowClass.MUST]
    must_flat = [row for row in must_rows if not is_sloped(row_args[row.row])]
    must_slope = [row for row in must_rows if is_sloped(row_args[row.row])]
    must = locs_of(locs, RowClass.MUST)
    must_dP = min_median_max(
        [loc.dP for loc in must if loc.state == LocState.OK and loc.dP is not None]
    )
    patch_new = [loc for loc in locs_of(locs, RowClass.PATCH) if not loc.is_known_row]
    patch_new_ok = [loc.dP for loc in patch_new if loc.state == LocState.OK]
    neutral = locs_of(locs, RowClass.NEUTRAL_G1)
    unrecoverable = [
        loc for loc in must + locs_of(locs, RowClass.PATCH) if loc.state == LocState.UNRECOVERABLE
    ]
    blocked = [loc for loc in locs if loc.state == LocState.BLOCKED_MISSING]
    known_b = set_b["known_row_dP"]
    return [
        prediction(
            "P-1",
            {"must_flat": len(must_flat), "must_slope": len(must_slope)},
            inside(len(must_flat), 26, 32) and not must_slope,
        ),
        prediction(
            "P-2",
            must_dP,
            bool(must)
            and all(loc.state == LocState.OK and loc.dP is not None and loc.dP > 0 for loc in must)
            and inside(must_dP["min"], 15, 60)
            and inside(must_dP["median"], 30, 90),
        ),
        prediction("P-3", len(flags["THIN_MARGIN"]), not flags["THIN_MARGIN"]),
        prediction(
            "P-4",
            {"rows": len({loc.row for loc in patch_new}), "dP": patch_new_ok},
            inside(len({loc.row for loc in patch_new}), 0, 4)
            and all(inside(value, -30, -1) for value in patch_new_ok),
        ),
        prediction("P-5", len(neutral), inside(len(neutral), 0, 3)),
        prediction("P-6", len(unrecoverable), inside(len(unrecoverable), 0, 2)),
        prediction("P-7", len(blocked), not blocked),
        prediction("P-8", is_k_all_true, is_k_all_true),
        prediction(
            "P-9",
            {"B_SOFT_NONPOS": len(set_b["B_SOFT_NONPOS"]), "known_row_dP": known_b},
            inside(len(set_b["B_SOFT_NONPOS"]), 0, 2) and known_b == [-20],
        ),
        prediction("P-10", str(grade), grade is Grade.PASS),
    ]


def prediction(prediction_id: str, value: Any, is_inside: bool) -> dict[str, Any]:
    return {"id": prediction_id, "value": value, "inside": bool(is_inside)}


# ================================================================ judge: set B record (7)
def set_b_row(path: str, document: Any) -> dict[str, Any]:
    """7: the final-LOC shadow dP of one old-controller row (record only)."""
    if structure_problems(document):
        return {"row": path, "status": "unreadable"}
    soil = document["controller_meta"]["soil"]
    floor = floor_class(document["args"])
    record: dict[str, Any] = {
        "row": path,
        "floor": "-" if floor is None else str(floor),
        "is_known_row": path in KNOWN_B_ROWS,
        "case": document["args"].get("case"),
    }
    t_loc_s, t_P_s = soil.get("t_loc_s"), soil.get("t_P_s")
    if not is_number(t_loc_s) or not is_number(t_P_s):
        return {**record, "status": "no_loc"}
    n_final = period_of(float(t_loc_s))
    soil_times = [t_s for t_s, name in event_pairs(document) if name == SOIL_MODE_EVENT]
    start = latest_before(soil_times, n_final)
    if start is None:
        return {**record, "status": "no_soil_mode", "n_fin": n_final}
    n_P = period_of(float(t_P_s))
    return {
        **record,
        "status": "ok",
        "n_fin": n_final,
        "t_P_s": float(t_P_s),
        "t_S_s": start[1],
        "n_P": n_P,
        "n_S": start[0],
        "dP": n_P - start[0],
    }


def build_set_b(records: list[dict[str, Any]]) -> dict[str, Any]:
    soft_nonpos = [
        record["row"]
        for record in records
        if record.get("floor") == Floor.UNIFORM_SOFT
        and record.get("status") == "ok"
        and record["dP"] <= 0
    ]
    known = [record.get("dP") for record in records if record.get("is_known_row")]
    return {
        "rows": records,
        "status_counts": dict(Counter(record["status"] for record in records)),
        "B_SOFT_NONPOS": soft_nonpos,
        "known_row_dP": known,
    }


# ================================================================ judge: identity (K-0..K-2)
def k0_check(
    rules_path: Path, rules_bytes: bytes | None, tool_sha_start: str, expect_tool_sha: str
) -> dict[str, Any]:
    """K-0: rules sha256 = sealed = ``.sha256`` record; tool sha256 = audit = now."""
    rules_sha = None if rules_bytes is None else sha256_bytes(rules_bytes)
    sha_file = rules_path.with_name(RULES_SHA_FILE_NAME)
    recorded = None
    if sha_file.is_file():
        tokens = sha_file.read_text(encoding="utf-8").split()
        recorded = tokens[0] if tokens else None
    tool_sha_end = sha256_file(TOOL_PATH)
    problems = []
    if rules_sha != RULES_SHA256:
        problems.append(f"rules sha256 {rules_sha} != sealed {RULES_SHA256}")
    if recorded != rules_sha:
        problems.append(f".sha256 record {recorded} != rules {rules_sha}")
    if expect_tool_sha.lower() != tool_sha_start:
        problems.append(f"tool sha256 {tool_sha_start} != audit record {expect_tool_sha}")
    if tool_sha_end != tool_sha_start:
        problems.append("tool file changed during the run")
    return {
        "id": "K-0",
        "ok": not problems,
        "problems": problems,
        "rules_sha256": rules_sha,
        "sha256_record": recorded,
        "tool_sha256_start": tool_sha_start,
        "tool_sha256_end": tool_sha_end,
        "expect_tool_sha256": expect_tool_sha,
    }


def appendix_floor_problems(sealed: SealedLists, list_report: dict[str, Any]) -> list[str]:
    """K-1 part: the floor class of every A / B row equals the appendix column."""
    floor_by_path = {item["path"]: item["floor"] for item in list_report["files"]}
    return [
        f"{row.path}: floor {floor_by_path.get(row.path)} != appendix {row.floor}"
        for row in sealed.rows_a + sealed.rows_b
        if floor_by_path.get(row.path) != row.floor
    ]


def k1_check(sealed: SealedLists, list_report: dict[str, Any]) -> dict[str, Any]:
    """K-1: recomputed A / B / E lists = 2.3; appendix A parsed (74 rows, list sha)."""
    problems = list(sealed.problems)
    problems += [
        f"{item['name']} not reproduced" for item in list_report["comparisons"] if not item["ok"]
    ]
    a_files = {
        (item["path"], item["sha256"]) for item in list_report["files"] if item["set_name"] == SET_A
    }
    if a_files != {(row.path, row.sha256) for row in sealed.rows_a}:
        problems.append("recomputed set A differs from appendix A")
    problems += appendix_floor_problems(sealed, list_report)
    return {
        "id": "K-1",
        "ok": not problems,
        "problems": problems,
        "post_seal_new_files": len(list_report["post_seal_new_files"]),
        "population": list_report["population"],
    }


@dataclass
class LoadedRow:
    path: str
    document: Any
    sha256: str | None


def load_rows(results_root: Path, rows: list[AppendixRow]) -> tuple[list[LoadedRow], list[str]]:
    """K-2: every row file exists and its sha256 equals the appendix (read once)."""
    loaded: list[LoadedRow] = []
    problems: list[str] = []
    for row in rows:
        file_path = results_root / row.path
        if not file_path.is_file():
            problems.append(f"{row.path}: missing")
            loaded.append(LoadedRow(row.path, None, None))
            continue
        data = file_path.read_bytes()
        sha = sha256_bytes(data)
        if sha != row.sha256:
            problems.append(f"{row.path}: sha256 {sha} != appendix {row.sha256}")
        loaded.append(LoadedRow(row.path, load_json_bytes(data), sha))
    return loaded, problems


# ================================================================ commands
def resolve_out(out: str | None, root: Path, default_name: str) -> Path:
    return Path(out) if out else root / OUT_DIR_RELATIVE / default_name


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(plain(payload), ensure_ascii=False, indent=1)
    path.write_text(text + "\n", encoding="utf-8")


def print_last_line(payload: dict[str, Any]) -> None:
    print(json.dumps(plain(payload), ensure_ascii=True))


def command_list(arguments: argparse.Namespace) -> int:
    root = Path(arguments.root).resolve()
    results_root = Path(arguments.results_root).resolve()
    rules_path = Path(arguments.rules).resolve()
    rules_bytes, rules_text = read_rules(rules_path)
    sealed = parse_sealed_lists(rules_text or "")
    if rules_text is None:
        sealed.problems.append(f"rules file missing: {rules_path}")
    report = build_list_report(results_root, sealed)
    out_path = resolve_out(arguments.out, root, LIST_OUT_NAME)
    payload = {
        "tool": TOOL_NAME,
        "command": "list",
        "tool_sha256": sha256_file(TOOL_PATH),
        "rules_sha256": None if rules_bytes is None else sha256_bytes(rules_bytes),
        "taken_utc": utc_now(),
        **report,
    }
    write_json(out_path, payload)
    exit_code = 0 if report["ok"] else 2
    print_last_line(
        {
            "tool": TOOL_NAME,
            "command": "list",
            "ok": report["ok"],
            "exit_code": exit_code,
            "out": str(out_path),
            "comparisons": {item["name"]: item["ok"] for item in report["comparisons"]},
            "population": report["population"]["count"],
            "post_seal_new_files": len(report["post_seal_new_files"]),
        }
    )
    return exit_code


def aggregate_problems(target: dict[str, list[str]], source: dict[str, list[str]]) -> None:
    for check_id, problems in source.items():
        target[check_id].extend(problems)


def judge_set_a(
    loaded: list[LoadedRow],
) -> tuple[list[RowRecord], list[LocRecord], dict[str, list[str]], dict[str, dict[str, Any]]]:
    rows: list[RowRecord] = []
    locs: list[LocRecord] = []
    problems = new_problem_map()
    row_args: dict[str, dict[str, Any]] = {}
    for item in loaded:
        if item.document is None:
            problems["K-3"].append(f"{item.path}: not loaded")
            continue
        analysis = analyze_row(item.path, item.document, item.path in KNOWN_A_ROWS)
        aggregate_problems(problems, analysis.problems)
        if analysis.record is None:
            continue
        mark_revoked_after_r4(item.document, analysis.record, analysis.locs)
        rows.append(analysis.record)
        locs.extend(analysis.locs)
        row_args[item.path] = item.document["args"]
    return rows, locs, problems, row_args


def judge_set_b(
    results_root: Path, list_report: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, str | None], list[str]]:
    """Set B record; a file that changed since the list scan is a K-1 problem."""
    scanned = {
        item["path"]: item["sha256"] for item in list_report["files"] if item["set_name"] == SET_B
    }
    records: list[dict[str, Any]] = []
    files_read: dict[str, str | None] = {}
    problems: list[str] = []
    for path, scanned_sha in sorted(scanned.items()):
        data = (results_root / path).read_bytes()
        files_read[path] = sha256_bytes(data)
        if files_read[path] != scanned_sha:
            problems.append(f"{path}: changed since the list scan")
        records.append(set_b_row(path, load_json_bytes(data)))
    return build_set_b(records), files_read, problems


def k_check_list(
    k0: dict[str, Any], k1: dict[str, Any], problems: dict[str, list[str]]
) -> list[dict[str, Any]]:
    checks = [k0, k1]
    checks += [
        {"id": check_id, "ok": not problems[check_id], "problems": problems[check_id]}
        for check_id in K_IDS[2:]
    ]
    checks.append(
        {
            "id": "K-9",
            "ok": None,
            "problems": [],
            "note": "external: path 2 recount (control-expert, 10.2) compared after this run",
        }
    )
    return checks


def command_judge(arguments: argparse.Namespace, tool_sha_start: str) -> int:
    root = Path(arguments.root).resolve()
    results_root = Path(arguments.results_root).resolve()
    rules_path = Path(arguments.rules).resolve()
    taken_utc = utc_now()
    rules_bytes, rules_text = read_rules(rules_path)
    sealed = parse_sealed_lists(rules_text or "")
    list_report = build_list_report(results_root, sealed)
    loaded, k2_problems = load_rows(results_root, sealed.rows_a)
    rows, locs, problems, row_args = judge_set_a(loaded)
    problems["K-2"] += k2_problems
    set_b, files_read_b, b_problems = judge_set_b(results_root, list_report)
    k1 = k1_check(sealed, list_report)
    k1["problems"] += b_problems
    k1["ok"] = not k1["problems"]
    k0 = k0_check(rules_path, rules_bytes, tool_sha_start, arguments.expect_tool_sha)
    k_checks = k_check_list(k0, k1, problems)
    grade, reasons, conditions = decide_grade(k_checks, locs)
    flags = build_flags(locs, rows, set_b)
    is_k_all_true = all(check["ok"] is not False for check in k_checks)
    payload = {
        "tool": TOOL_NAME,
        "command": "judge",
        "rules_sha256": k0["rules_sha256"],
        "tool_sha256": tool_sha_start,
        "git_head": git_record(root, arguments.no_git),
        "taken_utc": taken_utc,
        "results_root": str(results_root),
        "files_read_sha256": {
            str(rules_path): k0["rules_sha256"],
            **{item.path: item.sha256 for item in loaded},
            **files_read_b,
        },
        "list": {key: list_report[key] for key in ("population", "comparisons", "ok")},
        "k_checks": k_checks,
        "locs": [asdict(loc) for loc in locs],
        "rows": [asdict(row) for row in rows],
        "summary": {**build_summary(locs, rows), "conditions": conditions},
        "flags": flags,
        "set_B": set_b,
        "grade": str(grade),
        "grade_code": GRADE_CODES[grade],
        "grade_reasons": reasons,
        "predictions": build_predictions(locs, rows, flags, set_b, grade, is_k_all_true, row_args),
    }
    out_path = resolve_out(arguments.out, root, JUDGE_OUT_NAME)
    write_json(out_path, payload)
    exit_code = GRADE_EXIT_CODES[grade]
    print_last_line(
        {
            "tool": TOOL_NAME,
            "command": "judge",
            "grade": str(grade),
            "grade_code": GRADE_CODES[grade],
            "exit_code": exit_code,
            "out": str(out_path),
            "k_failed": [check["id"] for check in k_checks if check["ok"] is False],
            "tool_sha256": tool_sha_start,
        }
    )
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("list", "judge"):
        command = sub.add_parser(name)
        command.add_argument(
            "--root", default=str(DEFAULT_ROOT), help="project root (git, default out)"
        )
        command.add_argument(
            "--results-root", default=str(DEFAULT_ROOT / "07_results"), help="07_results folder"
        )
        command.add_argument(
            "--rules",
            default=str(DEFAULT_ROOT / RULES_DIR_RELATIVE / RULES_NAME),
            help="sealed rules",
        )
        command.add_argument("--out", "--json-out", dest="out", default=None, help="output JSON")
    judge_parser = sub.choices["judge"]
    judge_parser.add_argument(
        "--expect-tool-sha", required=True, help="K-0: tool sha256 in the pre-run audit record"
    )
    judge_parser.add_argument("--no-git", action="store_true", help="skip the git queries")
    return parser


def main(argv: list[str] | None = None) -> int:
    tool_sha_start = sha256_file(TOOL_PATH) or ""
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.command == "list":
            return command_list(arguments)
        return command_judge(arguments, tool_sha_start)
    except Exception as error:  # noqa: BLE001 - every unexpected failure is exit 3 with a JSON line
        traceback.print_exc(file=sys.stderr)
        print_last_line(
            {
                "tool": TOOL_NAME,
                "command": arguments.command,
                "exit_code": EXIT_INTERNAL_ERROR,
                "error": f"{type(error).__name__}: {error}",
            }
        )
        return EXIT_INTERNAL_ERROR


if __name__ == "__main__":
    sys.exit(main())
