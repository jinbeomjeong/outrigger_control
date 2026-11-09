"""LAS-b K1 re-measure judge: batch ``V5-LAS-K1-REM`` (Chrono SCM, K1 gate off / on, forced block).

Rules: the sealed original ``las_k1_rules_adopt2.md`` (control-expert, sha256 :data:`RULES_SHA256`).
The rules text wins where this code differs; section and check numbers in the comments are the
rules'. The identity code (git queries, row head / dirty fallback, hull hook, placement) is copied
from ``las_k1_sch_judge.py`` (rules 9.1), not imported.

Sub-commands
  prelaunch  K-0 / K-1 / K-2 / K-3 records right before the launch -> ``rem_prelaunch.json``
  postrun    the same records after the batch, compared with the prelaunch record
             -> ``rem_postrun.json``
  judge      K-0 .. K-9, rules 3-6 and the 2.3 diagnostic records -> ``judge_REM.json``

The grade is PROVISIONAL: ``k10`` is ``null`` and the grade is confirmed in the judgement document
after the independent recount (rules 9.2, K-10, lesson 2). The F1 / F2 diagnostic rows never change
the grade or the exit code (rules 2.3, 4.2).

Read only: the only child processes are git queries (``rev-parse``, ``diff --quiet``,
``diff --name-only``, ``status --porcelain``, ``show``). Standard library only; no project module
and no other judging tool is imported. The output file is the only write.

Usage (dynamics-dev, PowerShell, project root):
  C:\\ProgramData\\miniforge3\\envs\\dynamics-dev\\python.exe -I -B
      06_analysis/02_control/verif_matrix/scripts/las_k1_rem_judge.py
      prelaunch --batch-plan <rows.json> [--audit-report rem_prelaunch_audit.md]
          [--allow-dirty P ...]
      postrun --batch <folder> [--prelaunch F]
      judge --batch <folder> --expect-tool-sha <sha> [--prelaunch F] [--postrun F] [--rules F]
      [--root R] [--out F]

Exit codes: 0 pass (prelaunch / postrun: every item true; judge: provisional ``통과``), 1 judge
``미달`` / ``판정 불가`` / ``부분 통과``, 2 stop or an input error, 3 tool error. The first
stdout line says the grade is provisional; the last stdout line is JSON.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import struct
import subprocess
import sys
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

TOOL_PATH = Path(__file__).resolve()
DEFAULT_ROOT = TOOL_PATH.parents[4]
OUT_DIR_RELATIVE = Path("06_analysis/03_hydraulic/coupled/v5/las/k1")
PRELAUNCH_NAME = "rem_prelaunch.json"
POSTRUN_NAME = "rem_postrun.json"
JUDGE_NAME = "judge_REM.json"
AUDIT_REPORT_NAME = "rem_prelaunch_audit.md"
"""Lesson 1: the verif-protocol-auditor pre-run report, saved verbatim by the main session."""

# ---------------------------------------------------------------- sealed identity (K-0, K-2, K-3)
RULES_RELATIVE = Path("06_analysis/02_control/verif_matrix/las_k1_rules_adopt2.md")
RULES_SHA256 = "fb3a5696f24385e81acc9c564500b5e5a0547db45a5335272e7d18400f1e68e8"
CODE_DIFF_PATHS = ("03_src", "02_params", "04_scripts")
K2_CODE_FILES = (
    "04_scripts/02_chrono/run_S9.py",
    "04_scripts/02_chrono/s9_batch.py",
    "04_scripts/02_chrono/las_k1_rem_chrono_rows.py",
    "04_scripts/02_chrono/k1_forced_block.py",
    "03_src/outrigger_sim/control/c2.py",
    "03_src/outrigger_sim/control/zero_calibration.py",
    "03_src/outrigger_sim/chrono/hull_hook.py",
    "04_scripts/03_control/s9/late_loc_rule.py",
    "03_src/outrigger_sim/hydraulics/v5_options.py",
)
"""K-2: work-tree raw sha256 (CRLF) and HEAD blob sha256 (LF) of these files."""
C2_PATH = "03_src/outrigger_sim/control/c2.py"
FORCED_BLOCK_PATH = "04_scripts/02_chrono/k1_forced_block.py"
C2_BASE_COMMIT = "859deef"
"""K-2: the ``c2.py`` blob must be the blob of this commit (the variant did not change c2.py)."""
RECORDED_CONTROLLER_FILES = (
    ("outrigger_sim.control.c2", C2_PATH),
    ("outrigger_sim.control.zero_calibration", "03_src/outrigger_sim/control/zero_calibration.py"),
)
"""(result.json ``files_at_start`` module key, batch.json ``code_at_launch.files`` path)."""
DLL_PATH = "03_src/outrigger_sim/native/chrono_hull/bin/chrono_hull_hook.dll"
DLL_SHA256 = "cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15"

# ---------------------------------------------------------------- rows (rules 2.1 - 2.3)
TAG_VB = "final_C4G2_P3_LAS"
TAG_V0 = "final_C4G2_LAS"
GATE_OFF, GATE_ON = "off", "on"
FORCED_OFF, FORCED_FIRST = "off", "first"
ROLE_JUDGE, ROLE_DIAG = "judge", "diag"


@dataclass(frozen=True)
class RowSpec:
    """One row of the rules 2.2 / 2.3 tables."""

    rem_key: str
    case: str
    soil: str
    level: str
    mass_scale: float
    setting: str
    gate: str
    forced: str = FORCED_OFF

    @property
    def tag(self) -> str:
        return TAG_V0 if self.setting == "V0" else TAG_VB

    @property
    def role(self) -> str:
        return ROLE_DIAG if self.forced != FORCED_OFF else ROLE_JUDGE


ROW_SPECS = (
    RowSpec("R1", "REM_J2_B_top_Fs4_VB_gateoff", "J2", "top", 1.0, "VB", GATE_OFF),
    RowSpec("R2", "REM_J2_B_middle_Fs4_VB_gateoff", "J2", "middle", 1.0, "VB", GATE_OFF),
    RowSpec("R3", "REM_J2_B_bottom_Fs4_VB_gateoff", "J2", "bottom", 1.0, "VB", GATE_OFF),
    RowSpec("R4", "REM_J2_B_top_Fs4_m1p1_VB_gateoff", "J2", "top", 1.1, "VB", GATE_OFF),
    RowSpec("R5", "REM_J2_B_top_Fs4_m1p1_V0_gateoff", "J2", "top", 1.1, "V0", GATE_OFF),
    RowSpec("R6", "REM_J1_B_top_Fs4_m1p1_VB_gateoff", "J1", "top", 1.1, "VB", GATE_OFF),
    RowSpec("R7", "REM_J2_B_top_Fs4_VB_gateon", "J2", "top", 1.0, "VB", GATE_ON),
    RowSpec("R8", "REM_J2_B_top_Fs4_m1p1_VB_gateon", "J2", "top", 1.1, "VB", GATE_ON),
    RowSpec(
        "F1", "REM_J2_B_top_Fs4_VB_gateon_forced1", "J2", "top", 1.0, "VB", GATE_ON, FORCED_FIRST
    ),
    RowSpec(
        "F2",
        "REM_J2_B_top_Fs4_m1p1_VB_gateon_forced1",
        "J2",
        "top",
        1.1,
        "VB",
        GATE_ON,
        FORCED_FIRST,
    ),
)
SPEC_BY_KEY = {spec.rem_key: spec for spec in ROW_SPECS}
GATEOFF_KEYS = ("R1", "R2", "R3", "R4", "R5", "R6")
JUDGE_KEYS = (*GATEOFF_KEYS, "R7", "R8")
DIAG_KEYS = ("F1", "F2")
GATE_PAIRS = (("R7", "R1"), ("R8", "R4"))
"""(gate on, gate off): K-5 argv difference, K-7 L1 tuple, condition ③."""
FORCED_PAIRS = (("F1", "R7", "R1"), ("F2", "R8", "R4"))
"""(variant, its gate-on argv twin, its L1 pair row)."""
POOL_GROUPS = (("R1", "R7", "F1"), ("R4", "R8", "F2"))
"""K-4: each group runs on the same pool kind."""
MASS_KEYS = ("R4", "R5")
"""Condition ①: J2 x1.1 rows of which at least one must be ``POS``."""

FIXED_ARGS = {
    "seed": 20261026,
    "pressure_grade": "normal",
    "imu_grade": "ideal",
    "fs_kN": 4.0,
    "pad_variant": "dwg_rear250",
    "duration": 120.0,
    "soil_patch": None,
    "threads": 4,
}
"""K-5 fixed values (rules 2.1) read from result.json ``args``."""
FLAT_FLOOR_ARGS = ("floor_roll", "floor_pitch")
"""Rules 2.1 level floor: 0 when present."""
VB_OPTION_TOKENS = (
    "--flow-eta-v",
    "--flow-dp-comp-bar",
    "--flow-dp-unload-bar",
    "--flow-width-bar",
    "--flow-law",
    "--valve-tau-s",
    "--rod-release-force",
    "--lock-overlap-ratio",
    "--lock-closing-delay-s",
    "--lock-window-follows-plant",
    "--extend-start-tracked",
)
"""``s9_batch.v5_vb_argv()`` option names: every VB row has them, the V0 row none (rules 2.2)."""
VB_ARG_KEYS = (
    "flow_eta_v",
    "flow_dp_comp_bar",
    "flow_dp_unload_bar",
    "flow_width_bar",
    "flow_law",
    "valve_tau_s",
    "rod_release_force",
    "lock_overlap_ratio",
    "lock_closing_delay_s",
    "lock_window_follows_plant",
    "extend_start_tracked",
)
CASE_OPTION = "--case"
GATE_OPTION = "--k1-order-gate"
FORCED_OPTION = "--k1-forced-block"
EXPECT_OPTION = "--expect-controller"
MASS_OPTION = "--mass-scale"
LEVEL_OPTION = "--level"
SOIL_OPTION = "--soil"
THREADS = 4

# ---------------------------------------------------------------- judging constants (rules 3 - 8)
PERIOD_S = 0.1
THIN_MARGIN_PERIODS = 12
"""Adopt 7 FLAG threshold, inherited unchanged (rules 0.1 3)."""
MIN_POS_ROWS = 4
MAX_REVOKES = 2
READY_PHASE, DONE_PHASE, FAULT_PHASE = "ready", "done", "fault"
LOC_EVENT = "crawler_liftoff_confirmed"
SOIL_MODE_EVENT = "soil_mode_start"
SLOPE_MARGIN_EVENT = "INFO_LOC_CLEARANCE_MARGIN"
"""E3c10 (P-S8-31) LOC: no decision is written for it (rules 1.2)."""
MARGIN_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN"
"""R4c30 applied: ``INFO_LOC_FLAT_SOIL_MARGIN:<mm>`` (base name by exact match)."""
SKIP_ORDER_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order"
REVOKE_EVENT = "INFO_LOC_REVOKED"
NEW_EVENT_PREFIXES = ("FAULT_", "WARN_")
FORCED_CLASS_NAME = "K1ForcedBlockC2Controller"
PLAIN_CLASS_NAME = "C2Controller"

OLD_CONTROLLER_VALUES = {
    "R1": (451, 332),
    "R2": (451, 332),
    "R3": (451, 332),
    "R4": (553, 333),
    "R5": (553, 333),
    "R6": (492, 333),
    "R7": (451, 332),
    "R8": (553, 333),
}
"""Rules 1.1 (n_R, n_S) of the old controller rows (``OLD_CTRL_SHIFT`` record; R5 = J2 top x1.1)."""
HARNESS_DP = {"R1": (92, 93), "R2": (94, 94), "R3": (94, 95), "R6": (36, 38)}
"""Rules 1.3 harness first-LOC dP ranges (R6 against J1 x1.0, comparison only)."""

STATE_POS, STATE_NONPOS, STATE_LATE_STRUCT = "POS", "NONPOS", "LATE_STRUCT"
STATE_NO_R4, STATE_MISSING = "NO_R4", "MISSING"
PATH_L1_APPLIED, PATH_LATE, PATH_NEVER = "L1_APPLIED", "R4_APPLIED_LATE", "R4_NEVER"
FORCED_NO_REVOKE, FORCED_NEVER, FORCED_LATE = (
    "FORCED_NO_REVOKE",
    "FORCED_R4_NEVER",
    "FORCED_R4_LATE",
)
FORCED_REVOKED_NO_REEVAL = "FORCED_REVOKED_NO_REEVAL"
"""Not named by the rules: a revocation after the forced L1 but no later R4 decision."""

GRADE_PASS, GRADE_FAIL, GRADE_UNDECIDABLE = "통과", "미달", "판정 불가"
GRADE_PARTIAL, GRADE_STOP, GRADE_ERROR = "부분 통과", "stop", "error"
GRADE_CODES = {
    GRADE_PASS: "pass",
    GRADE_FAIL: "fail",
    GRADE_UNDECIDABLE: "undecidable",
    GRADE_PARTIAL: "partial",
    GRADE_STOP: "stop",
    GRADE_ERROR: "error",
}
EXIT_CODES = {
    GRADE_PASS: 0,
    GRADE_FAIL: 1,
    GRADE_UNDECIDABLE: 1,
    GRADE_PARTIAL: 1,
    GRADE_STOP: 2,
    GRADE_ERROR: 3,
}
PRELAUNCH_STATUS_OK, PRELAUNCH_STATUS_STOP = "pass", "stop"
GIT_TIMEOUT_S = 60.0
MISSING = object()


class InputError(Exception):
    """Bad command-line input (exit 2)."""


# ================================================================ small helpers
def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    return sha256_bytes(path.read_bytes()) if path.is_file() else None


def period_of(t_s: float | None) -> int | None:
    """Rules 0: whole control periods ``round(t / 0.1)`` (Python round, ties to even)."""
    return None if t_s is None else round(float(t_s) / PERIOD_S)


def event_base_name(name: str) -> str:
    """Lesson 9: the event name before ``:`` (compared by exact match)."""
    return str(name).split(":", 1)[0]


def dig(data: Any, *keys: Any) -> Any:
    """``data[k0][k1]...`` or :data:`MISSING` when any level is absent."""
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        elif isinstance(data, list) and isinstance(key, int) and -len(data) <= key < len(data):
            data = data[key]
        else:
            return MISSING
    return data


def is_error_block(value: Any) -> bool:
    """A run_S9 ``_record_or_error`` failure block ``{"error": ...}``."""
    return isinstance(value, dict) and set(value) == {"error"}


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def scalar(value: Any) -> Any:
    """A one-element argparse list read as its element."""
    if isinstance(value, (list, tuple)) and len(value) == 1:
        return value[0]
    return value


def plain(value: Any) -> Any:
    """JSON-ready copy (MISSING, tuples, non-finite floats)."""
    if value is MISSING:
        return "<missing>"
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def check(check_id: str, ok: bool | None, **detail: Any) -> dict[str, Any]:
    """One check record; ``ok`` None = not evaluated (not a stop)."""
    return {"id": check_id, "ok": ok, **plain(detail)}


def read_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def tool_record() -> dict[str, Any]:
    return {"path": TOOL_PATH.as_posix(), "sha256": sha256_file(TOOL_PATH)}


# ================================================================ git queries (copied from S-Ch)
@dataclass(frozen=True)
class GitResult:
    returncode: int | None
    stdout: bytes
    error: str | None


def run_git(root: Path, *args: str) -> GitResult:
    """One read-only git query in ``root``; a time-out or launch failure is returned, not raised."""
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
        return GitResult(None, b"", f"{type(error).__name__}: {error}")
    stderr = done.stderr.decode("utf-8", "replace").strip()
    return GitResult(done.returncode, done.stdout, stderr or None)


def git_head(root: Path) -> dict[str, Any]:
    result = run_git(root, "rev-parse", "HEAD")
    sha = result.stdout.decode("ascii", "replace").strip() if result.returncode == 0 else None
    return {"sha": sha or None, "ok": bool(sha), "error": None if sha else result.error}


def git_diff_is_empty(root: Path, base: str, head: str) -> bool | None:
    """``git diff --quiet <base> <head> -- 03_src 02_params 04_scripts``: True = no change,
    False = changed, None = the query failed."""
    result = run_git(root, "diff", "--quiet", base, head, "--", *CODE_DIFF_PATHS)
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    return None


def git_diff_names(root: Path, base: str, head: str) -> list[str] | None:
    result = run_git(root, "diff", "--name-only", base, head, "--", *CODE_DIFF_PATHS)
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.decode("utf-8", "replace").splitlines() if line]


def porcelain_path(line: str) -> str:
    """Path of one ``--porcelain=v1`` line (the new name of a rename)."""
    path = line[3:]
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    return path.strip().strip('"')


def status_record(root: Path, allowed: Iterable[str]) -> dict[str, Any]:
    """K-1 / lesson 4: ``git status --porcelain=v1 --untracked-files=no`` against the allow list."""
    allowed_set = frozenset(allowed)
    result = run_git(root, "status", "--porcelain=v1", "--untracked-files=no")
    if result.returncode != 0:
        return {"lines": None, "unexpected": None, "ok": False, "error": result.error}
    text = result.stdout.decode("utf-8", "replace")
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    unexpected = [line for line in lines if porcelain_path(line) not in allowed_set]
    return {
        "basis": "--untracked-files=no",
        "lines": lines,
        "allowed": sorted(allowed_set),
        "unexpected": unexpected,
        "ok": not unexpected,
        "error": None,
    }


def blob_sha256(root: Path, revision: str | None, path: str) -> str | None:
    """sha256 of ``git show <revision>:<path>`` (the LF blob, no filters)."""
    if revision is None:
        return None
    result = run_git(root, "show", f"{revision}:{path}")
    return sha256_bytes(result.stdout) if result.returncode == 0 else None


# ================================================================ controller_commands.npz (stdlib)
@dataclass(frozen=True)
class CommandDigest:
    """``controller_commands.npz`` ``t_s`` / ``issued_u_m_s`` as ``<f8`` bytes (P-8 record)."""

    sha256: str
    t_s: tuple[float, ...]
    rows: tuple[bytes, ...]
    """One ``issued_u_m_s`` row (all legs) per command, raw ``<f8`` bytes."""


def read_npy_f8(data: bytes) -> tuple[tuple[int, ...], bytes]:
    """Shape and raw data of one ``.npy`` member holding a C-order ``<f8`` array."""
    if data[:6] != b"\x93NUMPY":
        raise ValueError("not an .npy member")
    major = data[6]
    if major == 1:
        (header_length,) = struct.unpack("<H", data[8:10])
        start = 10
    else:
        (header_length,) = struct.unpack("<I", data[8:12])
        start = 12
    header = ast.literal_eval(data[start : start + header_length].decode("latin1"))
    if header.get("descr") != "<f8" or header.get("fortran_order"):
        raise ValueError(f"unsupported npy header {header}")
    shape = tuple(int(n) for n in header["shape"])
    count = math.prod(shape)
    body = data[start + header_length : start + header_length + 8 * count]
    if len(body) != 8 * count:
        raise ValueError("truncated npy data")
    return shape, body


def read_commands(path: Path) -> CommandDigest | None:
    """The command digest of ``path``; None when absent or not readable (record only)."""
    if not path.is_file():
        return None
    try:
        with zipfile.ZipFile(path) as archive:
            t_shape, t_bytes = read_npy_f8(archive.read("t_s.npy"))
            u_shape, u_bytes = read_npy_f8(archive.read("issued_u_m_s.npy"))
    except (OSError, KeyError, ValueError, SyntaxError, zipfile.BadZipFile):
        return None
    n_rows = t_shape[0] if t_shape else 0
    if len(u_shape) != 2 or u_shape[0] != n_rows:
        return None
    width = 8 * u_shape[1]
    t_values = struct.unpack(f"<{n_rows}d", t_bytes)
    rows = tuple(u_bytes[i * width : (i + 1) * width] for i in range(n_rows))
    return CommandDigest(sha256_bytes(t_bytes + u_bytes), t_values, rows)


def first_command_difference(first: CommandDigest, second: CommandDigest) -> int | None:
    """Period of the first command row that differs (None when the files are the same)."""
    for t_a, t_b, row_a, row_b in zip(first.t_s, second.t_s, first.rows, second.rows, strict=False):
        if t_a != t_b or row_a != row_b:
            return period_of(t_a)
    if len(first.t_s) == len(second.t_s):
        return None
    longer = first if len(first.t_s) > len(second.t_s) else second
    return period_of(longer.t_s[min(len(first.t_s), len(second.t_s))])


# ================================================================ prelaunch / postrun
def rules_record(root: Path, rules_path: Path | None = None) -> dict[str, Any]:
    """K-0: rules file sha256, its ``.sha256`` record and the sealed constant."""
    path = rules_path or root / RULES_RELATIVE
    digest = sha256_file(path)
    record_path = path.with_suffix(".sha256")
    recorded = None
    if record_path.is_file():
        tokens = record_path.read_text(encoding="utf-8", errors="replace").split()
        recorded = tokens[0].lower() if tokens else None
    return {
        "path": path.as_posix(),
        "sha256": digest,
        "sha256_file_record": recorded,
        "sealed": RULES_SHA256,
        "ok": digest == RULES_SHA256 and recorded == RULES_SHA256,
    }


def code_file_records(root: Path, head_sha: str | None) -> dict[str, Any]:
    """K-2: work-tree raw sha256 and HEAD blob sha256 of :data:`K2_CODE_FILES`; the ``c2.py``
    blob against :data:`C2_BASE_COMMIT`."""
    files = {
        path: {
            "worktree_sha256": sha256_file(root / path),
            "blob_sha256": blob_sha256(root, head_sha, path),
        }
        for path in K2_CODE_FILES
    }
    base_blob = blob_sha256(root, C2_BASE_COMMIT, C2_PATH)
    is_complete = all(r["worktree_sha256"] and r["blob_sha256"] for r in files.values())
    is_c2_base = base_blob is not None and files[C2_PATH]["blob_sha256"] == base_blob
    return {
        "files": files,
        "c2_base_commit": C2_BASE_COMMIT,
        "c2_base_blob_sha256": base_blob,
        "c2_blob_is_base": is_c2_base,
        "ok": is_complete and is_c2_base,
    }


def dll_record(root: Path) -> dict[str, Any]:
    digest = sha256_file(root / DLL_PATH)
    return {"path": DLL_PATH, "sha256": digest, "expected": DLL_SHA256, "ok": digest == DLL_SHA256}


def audit_record(audit_path: Path) -> dict[str, Any]:
    """K-0 / lesson 1: the pre-run audit report file sha256."""
    digest = sha256_file(audit_path)
    return {"path": audit_path.as_posix(), "sha256": digest, "ok": digest is not None}


def plan_rows_of(document: Any) -> list[dict[str, Any]] | None:
    """The row list of a batch plan JSON: a list, or ``rows`` / ``cases`` of an object."""
    if isinstance(document, dict):
        document = document.get("rows", document.get("cases"))
    if not isinstance(document, list):
        return None
    return [row for row in document if isinstance(row, dict)]


def batch_plan_record(plan_path: Path) -> dict[str, Any]:
    """The batch plan: its sha256, the cases against rules 2.2 / 2.3 and the planned pools."""
    digest = sha256_file(plan_path)
    try:
        document = json.loads(plan_path.read_text(encoding="utf-8")) if digest else None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        document = None
    rows = plan_rows_of(document)
    if rows is None:
        return {
            "path": plan_path.as_posix(),
            "sha256": digest,
            "rows": None,
            "ok": False,
            "problems": ["batch plan missing, unreadable or without a row list"],
        }
    by_case = {str(row.get("case")): row for row in rows}
    problems = []
    want = {spec.case for spec in ROW_SPECS}
    if set(by_case) != want or len(rows) != len(ROW_SPECS):
        problems.append(f"plan cases {sorted(by_case)} != rules 2.2 / 2.3 cases {sorted(want)}")
    for spec in ROW_SPECS:
        key = by_case.get(spec.case, {}).get("rem_key")
        if key is not None and key != spec.rem_key:
            problems.append(f"{spec.case}: rem_key {key!r} != {spec.rem_key!r}")
    pools = {case: row.get("pool", row.get("planned_pool")) for case, row in by_case.items()}
    return {
        "path": plan_path.as_posix(),
        "sha256": digest,
        "cases": sorted(by_case),
        "planned_pool": pools,
        "ok": not problems,
        "problems": problems,
    }


def identity_snapshot(root: Path, allowed_dirty: list[str], audit_path: Path) -> dict[str, Any]:
    """The K-0 .. K-3 records at this moment (prelaunch and postrun)."""
    head = git_head(root)
    return {
        "tool": tool_record(),
        "taken_utc": utc_now(),
        "root": root.as_posix(),
        "head": head,
        "git_status": status_record(root, allowed_dirty),
        "code_files": code_file_records(root, head["sha"]),
        "dll": dll_record(root),
        "rules": rules_record(root),
        "audit_report": audit_record(audit_path),
    }


def snapshot_checks(snapshot: dict[str, Any]) -> dict[str, bool]:
    return {
        "head": snapshot["head"]["ok"],
        "git_status_allowed": snapshot["git_status"]["ok"],
        "code_files": snapshot["code_files"]["ok"],
        "dll": snapshot["dll"]["ok"],
        "rules": snapshot["rules"]["ok"],
        "audit_report": snapshot["audit_report"]["ok"],
    }


def prelaunch_document(
    root: Path, plan_path: Path, audit_path: Path, allowed_dirty: list[str]
) -> dict[str, Any]:
    snapshot = identity_snapshot(root, allowed_dirty, audit_path)
    snapshot["kind"] = "prelaunch"
    snapshot["batch_plan"] = batch_plan_record(plan_path)
    checks = snapshot_checks(snapshot)
    checks["batch_plan"] = snapshot["batch_plan"]["ok"]
    snapshot["checks"] = checks
    snapshot["all_ok"] = all(checks.values())
    snapshot["status"] = PRELAUNCH_STATUS_OK if snapshot["all_ok"] else PRELAUNCH_STATUS_STOP
    return snapshot


def comparable_values(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Values the postrun record must repeat from the prelaunch record (no time stamps)."""
    files = dig(snapshot, "code_files", "files")
    return {
        "code_files": files if isinstance(files, dict) else None,
        "c2_base_blob_sha256": dig(snapshot, "code_files", "c2_base_blob_sha256"),
        "dll": dig(snapshot, "dll", "sha256"),
        "tool": dig(snapshot, "tool", "sha256"),
        "rules": dig(snapshot, "rules", "sha256"),
        "audit_report": dig(snapshot, "audit_report", "sha256"),
    }


def postrun_document(root: Path, prelaunch_path: Path) -> dict[str, Any]:
    prelaunch = read_json(prelaunch_path)
    allowed = dig(prelaunch, "git_status", "allowed")
    audit_path = dig(prelaunch, "audit_report", "path")
    snapshot = identity_snapshot(
        root,
        allowed if isinstance(allowed, list) else [],
        Path(audit_path) if isinstance(audit_path, str) else root / OUT_DIR_RELATIVE / "missing",
    )
    snapshot["kind"] = "postrun"
    snapshot["prelaunch"] = {
        "path": prelaunch_path.as_posix(),
        "found": prelaunch is not None,
        "sha256": sha256_file(prelaunch_path),
    }
    checks = snapshot_checks(snapshot)
    if prelaunch is None:
        checks["prelaunch_found"] = False
    else:
        before, after = comparable_values(prelaunch), comparable_values(snapshot)
        differences = [key for key in before if before[key] != after[key]]
        prelaunch_head = dig(prelaunch, "head", "sha")
        quiet = None
        if isinstance(prelaunch_head, str) and snapshot["head"]["sha"]:
            quiet = git_diff_is_empty(root, prelaunch_head, snapshot["head"]["sha"])
        snapshot["code_diff_since_prelaunch"] = {
            "base": prelaunch_head,
            "head": snapshot["head"]["sha"],
            "paths": list(CODE_DIFF_PATHS),
            "quiet": quiet,
            "changed_paths": None
            if quiet is not False
            else git_diff_names(root, prelaunch_head, snapshot["head"]["sha"]),
        }
        snapshot["differences_to_prelaunch"] = differences
        checks["same_as_prelaunch"] = not differences
        checks["code_diff_since_prelaunch_empty"] = quiet is True
    snapshot["checks"] = checks
    snapshot["all_ok"] = all(checks.values())
    snapshot["status"] = PRELAUNCH_STATUS_OK if snapshot["all_ok"] else PRELAUNCH_STATUS_STOP
    return snapshot


# ================================================================ judge inputs
@dataclass
class RowInput:
    """One batch row: its rules spec, result.json, batch.json entry and the command digest."""

    spec: RowSpec
    result: dict[str, Any] | None
    entry: dict[str, Any] | None
    commands: CommandDigest | None = None
    missing_reasons: list[str] = field(default_factory=list)

    @property
    def is_missing(self) -> bool:
        return bool(self.missing_reasons)


@dataclass
class JudgeInputs:
    """Everything ``judge`` reads, so the judging itself does no I/O (unit tests build this)."""

    rows: dict[str, RowInput]
    batch: dict[str, Any]
    prelaunch: dict[str, Any] | None
    postrun: dict[str, Any] | None
    rules: dict[str, Any]
    tool_sha256: str | None
    expect_tool_sha256: str | None
    audit_sha256_now: str | None
    code_diff_quiet: Callable[[str, str], bool | None]
    """``git diff --quiet <prelaunch HEAD> <postrun HEAD> -- 03_src 02_params 04_scripts``."""


def missing_reasons_of(result: dict[str, Any] | None, entry: dict[str, Any] | None) -> list[str]:
    """Rules 7 / K-9: why a row is ``MISSING`` (empty = the row is usable)."""
    reasons = []
    if entry is None:
        reasons.append("no batch.json entry")
    elif entry.get("rc") != 0:
        reasons.append(f"rc {entry.get('rc')!r}")
    if result is None:
        return [*reasons, "result.json missing or unreadable"]
    for path in (("controller_meta",), ("controller_meta", "soil"), ("events",)):
        value = dig(result, *path)
        name = ".".join(path)
        if value is MISSING or value is None:
            reasons.append(f"{name}: missing")
        elif is_error_block(value):
            reasons.append(f"{name}: {value['error']}")
        elif path == ("events",) and not isinstance(value, list):
            reasons.append("events: not a list")
    restored = dig(result, "controller_meta", "soil", "restored_from")
    if restored not in (MISSING, None):
        reasons.append(f"controller_meta.soil.restored_from {restored!r}")
    return list(dict.fromkeys(reasons))


def load_judge_inputs(
    root: Path,
    batch_dir: Path,
    prelaunch_path: Path,
    postrun_path: Path,
    rules_path: Path,
    expect_tool_sha256: str,
) -> tuple[JudgeInputs, dict[str, Any]]:
    """Read the batch folder, the records and the rules; return the inputs and the file digests."""
    batch = read_json(batch_dir / "batch.json") or {}
    entries = {str(e.get("case")): e for e in batch.get("cases") or [] if isinstance(e, dict)}
    rows: dict[str, RowInput] = {}
    read_paths = [
        batch_dir / "batch.json",
        batch_dir / "progress.log",
        prelaunch_path,
        postrun_path,
        rules_path,
    ]
    for spec in ROW_SPECS:
        folder = batch_dir / spec.case
        result = read_json(folder / "result.json")
        entry = entries.get(spec.case)
        row = RowInput(spec, result, entry, read_commands(folder / "controller_commands.npz"))
        row.missing_reasons = missing_reasons_of(result, entry)
        if not batch:
            row.missing_reasons.insert(0, "batch.json missing or unreadable")
        rows[spec.rem_key] = row
        read_paths += [folder / "result.json", folder / "controller_commands.npz"]
    prelaunch = read_json(prelaunch_path)
    audit_path = dig(prelaunch, "audit_report", "path")
    audit_now = sha256_file(Path(audit_path)) if isinstance(audit_path, str) else None
    if isinstance(audit_path, str):
        read_paths.append(Path(audit_path))
    inputs = JudgeInputs(
        rows=rows,
        batch=batch,
        prelaunch=prelaunch,
        postrun=read_json(postrun_path),
        rules=rules_record(root, rules_path),
        tool_sha256=sha256_file(TOOL_PATH),
        expect_tool_sha256=expect_tool_sha256,
        audit_sha256_now=audit_now,
        code_diff_quiet=lambda base, head: git_diff_is_empty(root, base, head),
    )
    files_read = {path.as_posix(): sha256_file(path) for path in read_paths}
    return inputs, files_read


# ================================================================ row analysis (rules 3.1, 3.2)
@dataclass(frozen=True)
class Decision:
    """One ``order_gate.decisions`` entry with the rules 3.1 labels."""

    index: int
    t_loc_s: float | None
    n_loc: int | None
    t_P_s: float | None
    t_S_s: float | None
    n_P: int | None
    n_S: int | None
    dP: int | None
    is_r4_due: bool
    would_block: bool
    is_applied: bool
    is_post_revoke: bool
    last_revoke_n: int | None
    restart_n: int | None
    is_struct_zero: bool
    recorded_periods_match: bool

    def l1_tuple(self) -> tuple[Any, ...]:
        """Rules 3.4 / K-7: (n_loc, n_P, n_S, dP, t_P_s, t_S_s), floats compared exactly."""
        return (self.n_loc, self.n_P, self.n_S, self.dP, self.t_P_s, self.t_S_s)

    def to_record(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "t_loc_s": self.t_loc_s,
            "n_loc": self.n_loc,
            "t_P_s": self.t_P_s,
            "t_S_s": self.t_S_s,
            "n_P": self.n_P,
            "n_S": self.n_S,
            "dP": self.dP,
            "r4_due_without_gate": self.is_r4_due,
            "would_block": self.would_block,
            "applied": self.is_applied,
            "post_revoke": self.is_post_revoke,
            "last_revoke_n": self.last_revoke_n,
            "restart_n": self.restart_n,
            "struct_zero": self.is_struct_zero,
            "recorded_periods_match": self.recorded_periods_match,
        }


@dataclass
class RowAnalysis:
    """Rules 3.1 decision table, $L_1$, the row state and the record items of rules 6."""

    rem_key: str
    events: list[tuple[float, str]]
    loc_periods: list[int]
    e3c10_loc_periods: list[int]
    revoke_periods: list[int]
    revoke_event_periods: list[int]
    mode_starts: list[tuple[int, float, Any]]
    decisions: list[Decision] | None
    """None when ``order_gate.decisions`` is absent (K-6 stop, rules 7)."""

    @property
    def r4_decisions(self) -> list[Decision]:
        return [d for d in self.decisions or [] if d.is_r4_due]

    @property
    def l1(self) -> Decision | None:
        r4 = self.r4_decisions
        return r4[0] if r4 else None


def mode_starts_of(result: dict[str, Any]) -> list[tuple[int, float, Any]]:
    starts = dig(result, "controller_meta", "soil", "mode_starts")
    out = []
    for start in starts if isinstance(starts, list) else []:
        t_s = start.get("t_s") if isinstance(start, dict) else None
        if is_number(t_s):
            out.append((period_of(t_s), float(t_s), start.get("source")))
    return out


def revoke_periods_of(result: dict[str, Any]) -> list[int]:
    """Rules 0: revocations from ``controller_meta.loc_revoke.t_revoke_s``."""
    times = dig(result, "controller_meta", "loc_revoke", "t_revoke_s")
    return [period_of(t) for t in times if is_number(t)] if isinstance(times, list) else []


def events_of(result: dict[str, Any]) -> list[tuple[float, str]]:
    out = []
    for event in result.get("events") or []:
        if isinstance(event, dict) and is_number(event.get("t_s")):
            out.append((float(event["t_s"]), str(event.get("name"))))
    return out


def periods_with_base(events: list[tuple[float, str]], base_name: str) -> list[int]:
    return [period_of(t) for t, name in events if event_base_name(name) == base_name]


def periods_with_full(events: list[tuple[float, str]], full_name: str) -> list[int]:
    return [period_of(t) for t, name in events if name == full_name]


def as_int_or_none(value: Any) -> int | None:
    return int(value) if is_number(value) and float(value).is_integer() else None


def labelled_decision(
    index: int,
    raw: dict[str, Any],
    revoke_periods: list[int],
    mode_starts: list[tuple[int, float, Any]],
) -> Decision:
    """Rules 3.1: periods from the recorded times, ``post_revoke``, ``restart_n`` and
    ``struct_zero``."""
    t_loc = raw.get("t_loc_s") if is_number(raw.get("t_loc_s")) else None
    t_P = raw.get("t_P_s") if is_number(raw.get("t_P_s")) else None
    t_S = raw.get("t_S_s") if is_number(raw.get("t_S_s")) else None
    n_loc, n_P, n_S = period_of(t_loc), period_of(t_P), period_of(t_S)
    dP = n_P - n_S if n_P is not None and n_S is not None else None
    earlier = [n for n in revoke_periods if n_loc is not None and n < n_loc]
    last_revoke = max(earlier) if earlier else None
    restart = None
    if last_revoke is not None:
        restart = next((n for n, _, _ in mode_starts if n >= last_revoke), None)
    is_struct_zero = last_revoke is not None and n_S is not None and n_S == restart and n_P == n_S
    is_match = (as_int_or_none(raw.get("n_P")), as_int_or_none(raw.get("n_S"))) == (n_P, n_S)
    return Decision(
        index=index,
        t_loc_s=t_loc,
        n_loc=n_loc,
        t_P_s=t_P,
        t_S_s=t_S,
        n_P=n_P,
        n_S=n_S,
        dP=dP,
        is_r4_due=raw.get("r4_due_without_gate") is True,
        would_block=raw.get("would_block") is True,
        is_applied=raw.get("applied") is True,
        is_post_revoke=last_revoke is not None,
        last_revoke_n=last_revoke,
        restart_n=restart,
        is_struct_zero=is_struct_zero,
        recorded_periods_match=is_match,
    )


def analyze_row(row: RowInput) -> RowAnalysis:
    result = row.result or {}
    events = events_of(result)
    loc_periods = periods_with_base(events, LOC_EVENT)
    slope_periods = set(periods_with_base(events, SLOPE_MARGIN_EVENT))
    revokes = revoke_periods_of(result)
    starts = mode_starts_of(result)
    raw = dig(result, "controller_meta", "slope_clearance_margin", "order_gate", "decisions")
    decisions = None
    if isinstance(raw, list):
        decisions = [
            labelled_decision(i, d if isinstance(d, dict) else {}, revokes, starts)
            for i, d in enumerate(raw)
        ]
    return RowAnalysis(
        rem_key=row.spec.rem_key,
        events=events,
        loc_periods=loc_periods,
        e3c10_loc_periods=[n for n in loc_periods if n in slope_periods],
        revoke_periods=revokes,
        revoke_event_periods=periods_with_base(events, REVOKE_EVENT),
        mode_starts=starts,
        decisions=decisions,
    )


def row_state(analysis: RowAnalysis) -> str:
    """Rules 3.2 for a usable row."""
    l1 = analysis.l1
    if l1 is None:
        return STATE_NO_R4
    if l1.is_post_revoke and l1.is_struct_zero:
        return STATE_LATE_STRUCT
    if l1.dP is not None and l1.dP > 0:
        return STATE_POS
    return STATE_NONPOS


def no_r4_reason(analysis: RowAnalysis, result: dict[str, Any]) -> str | None:
    """Record: why a row has no R4-evaluated LOC."""
    if analysis.l1 is not None:
        return None
    if not analysis.loc_periods:
        return f"no LOC (last phase {last_phase(result)!r})"
    if not analysis.mode_starts:
        return "no soil-mode start"
    if len(analysis.e3c10_loc_periods) == len(analysis.loc_periods):
        return "every LOC is an E3c10 LOC"
    return "no decision with r4_due_without_gate (settle tilt > 1 deg or a target already set)"


def phases_of(result: dict[str, Any]) -> list[tuple[float, str]]:
    out = []
    for phase in result.get("phases") or []:
        if isinstance(phase, dict) and is_number(phase.get("t_s")):
            out.append((float(phase["t_s"]), str(phase.get("phase"))))
    return out


def last_phase(result: dict[str, Any]) -> str | None:
    phases = phases_of(result)
    return phases[-1][1] if phases else None


def first_phase_time(result: dict[str, Any], name: str) -> float | None:
    return next((t for t, phase in phases_of(result) if phase == name), None)


def end_record(row: RowInput) -> dict[str, Any]:
    """Rules 2.3 / 6 row-end record: stroke, crawler gap, DONE / READY, phase, FAULT / WARN."""
    result = row.result or {}
    legs = dig(result, "p3b", "P3-5_clearance_stroke", "s_motor_max_m")
    numbers = [v for v in legs if is_number(v)] if isinstance(legs, list) else []
    names = sorted(
        {
            event_base_name(n)
            for _, n in events_of(result)
            if event_base_name(n).startswith(NEW_EVENT_PREFIXES)
        }
    )
    return {
        "s_motor_max_m": max(numbers) if numbers else None,
        "crawler_gap_grid_end_m": plain(dig(result, "p3b_ext", "crawler_gap", "grid_end_m")),
        "first_done_s": first_phase_time(result, DONE_PHASE),
        "first_ready_s": first_phase_time(result, READY_PHASE),
        "last_phase": last_phase(result),
        "fault_warn_events": names,
    }


def row_record(row: RowInput, analysis: RowAnalysis | None) -> dict[str, Any]:
    """Rules 6 row record (``rows`` of the output)."""
    spec = row.spec
    record: dict[str, Any] = {
        "rem_key": spec.rem_key,
        "case": spec.case,
        "role": spec.role,
        "gate": spec.gate,
        "forced": spec.forced,
        "setting": spec.setting,
        "tag": spec.tag,
        "missing_reasons": list(row.missing_reasons),
        "rerun_of": dig(row.entry, "rerun_of") if row.entry else None,
    }
    if analysis is None:
        return {**record, "state": STATE_MISSING}
    l1 = analysis.l1
    record.update(
        state=row_state(analysis),
        no_r4_reason=no_r4_reason(analysis, row.result or {}),
        L1=None
        if l1 is None
        else {
            **l1.to_record(),
            "n_loc_minus_n_P": None if l1.n_P is None or l1.n_loc is None else l1.n_loc - l1.n_P,
        },
        decisions=[d.to_record() for d in analysis.decisions or []],
        revoke_periods=analysis.revoke_periods,
        mode_starts=[{"n": n, "t_s": t, "source": s} for n, t, s in analysis.mode_starts],
        loc_periods=analysis.loc_periods,
        e3c10_locs=len(analysis.e3c10_loc_periods),
        end=end_record(row),
    )
    return record


# ================================================================ K-0 .. K-5 (identity)
def check_k0(inputs: JudgeInputs) -> dict[str, Any]:
    """Rules sha256 = ``.sha256`` = sealed; tool sha256 = audit = prelaunch = postrun = judge;
    audit report sha256 now = prelaunch record."""
    tool = {
        "expected (audit)": inputs.expect_tool_sha256,
        "prelaunch": dig(inputs.prelaunch, "tool", "sha256"),
        "postrun": dig(inputs.postrun, "tool", "sha256"),
        "judge": inputs.tool_sha256,
    }
    is_tool_ok = (
        all(isinstance(v, str) and v for v in tool.values()) and len(set(tool.values())) == 1
    )
    audit_recorded = dig(inputs.prelaunch, "audit_report", "sha256")
    is_audit_ok = isinstance(audit_recorded, str) and audit_recorded == inputs.audit_sha256_now
    rules_at_prelaunch = dig(inputs.prelaunch, "rules", "sha256")
    is_rules_ok = inputs.rules.get("ok") is True and rules_at_prelaunch == RULES_SHA256
    return check(
        "K-0",
        is_tool_ok and is_audit_ok and is_rules_ok,
        rules=inputs.rules,
        rules_at_prelaunch=rules_at_prelaunch,
        tool_sha256=tool,
        audit_report={"prelaunch": audit_recorded, "now": inputs.audit_sha256_now},
    )


def row_head(row: RowInput) -> tuple[Any, str]:
    """K-1 source: result.json ``git_at_start.head``, else batch.json
    ``code_at_launch.git.head``."""
    head = dig(row.result, "code_state", "git_at_start", "head")
    if isinstance(head, str) and head:
        return head, "result.json code_state.git_at_start.head"
    head = dig(row.entry, "code_at_launch", "git", "head")
    if isinstance(head, str) and head:
        return head, "batch.json code_at_launch.git.head (git_at_start unusable)"
    return None, "none"


def row_dirty(row: RowInput) -> tuple[Any, str]:
    dirty = dig(row.result, "code_state", "git_at_start", "dirty")
    if isinstance(dirty, list):
        return dirty, "result.json code_state.git_at_start.dirty"
    dirty = dig(row.entry, "code_at_launch", "git", "dirty")
    if isinstance(dirty, list):
        return dirty, "batch.json code_at_launch.git.dirty (git_at_start unusable)"
    return MISSING, "none"


def k1_batch_items(inputs: JudgeInputs) -> dict[str, Any]:
    """K-1 items shared by every row: the code diff and both ``git status`` records."""
    prelaunch_head = dig(inputs.prelaunch, "head", "sha")
    postrun_head = dig(inputs.postrun, "head", "sha")
    quiet = None
    if isinstance(prelaunch_head, str) and isinstance(postrun_head, str):
        quiet = inputs.code_diff_quiet(prelaunch_head, postrun_head)
    return {
        "prelaunch_head": prelaunch_head,
        "postrun_head": postrun_head,
        "code_diff_quiet_now": quiet,
        "code_diff_quiet_postrun": dig(inputs.postrun, "code_diff_since_prelaunch", "quiet"),
        "prelaunch_status_ok": dig(inputs.prelaunch, "git_status", "ok"),
        "postrun_status_ok": dig(inputs.postrun, "git_status", "ok"),
    }


def k1_row_problems(row: RowInput, shared: dict[str, Any]) -> list[str]:
    head, _ = row_head(row)
    dirty, _ = row_dirty(row)
    problems = []
    if head is None or head != shared["prelaunch_head"]:
        problems.append(f"head {head!r} != prelaunch {shared['prelaunch_head']!r}")
    if dirty != []:
        problems.append(f"dirty {plain(dirty)!r}")
    return problems


def k1_shared_ok(shared: dict[str, Any]) -> bool:
    return (
        shared["code_diff_quiet_now"] is True
        and shared["code_diff_quiet_postrun"] is True
        and shared["prelaunch_status_ok"] is True
        and shared["postrun_status_ok"] is True
    )


def prelaunch_file_sha(inputs: JudgeInputs, path: str) -> Any:
    return dig(inputs.prelaunch, "code_files", "files", path, "worktree_sha256")


def k2_batch_problems(inputs: JudgeInputs) -> list[str]:
    problems = []
    if dig(inputs.prelaunch, "code_files", "ok") is not True:
        problems.append("prelaunch code_files not ok (missing file or c2.py blob != 859deef blob)")
    if (
        comparable_values(inputs.prelaunch or {})["code_files"]
        != comparable_values(inputs.postrun or {})["code_files"]
    ):
        problems.append("postrun code file sha256 != prelaunch")
    return problems


def k2_row_problems(inputs: JudgeInputs, row: RowInput) -> list[str]:
    problems = []
    for module, path in RECORDED_CONTROLLER_FILES:
        want = prelaunch_file_sha(inputs, path)
        in_result = dig(row.result, "code_state", "files_at_start", module, "sha256")
        in_batch = dig(row.entry, "code_at_launch", "files", path)
        if in_result != want or in_batch != want:
            problems.append(
                f"{path}: result {plain(in_result)!r} / batch {plain(in_batch)!r} != "
                f"prelaunch {plain(want)!r}"
            )
    recorded = dig(row.result, "c2_setup", "k1_forced_block", "module_sha256")
    want_forced = prelaunch_file_sha(inputs, FORCED_BLOCK_PATH)
    if row.spec.forced != FORCED_OFF or recorded not in (MISSING, None):
        if recorded != want_forced:
            problems.append(
                f"c2_setup.k1_forced_block.module_sha256 {plain(recorded)!r} != "
                f"prelaunch {plain(want_forced)!r}"
            )
    return problems


def k3_row_problems(row: RowInput) -> list[str]:
    hull = dig(row.result, "hull_hook")
    hull = hull if isinstance(hull, dict) else {}
    values = {
        "mode": hull.get("mode"),
        "requested": hull.get("requested"),
        "fallback_reason": hull.get("fallback_reason"),
        "dll_sha256": hull.get("dll_sha256"),
        "batch.hull_hook_requested": dig(row.entry, "hull_hook_requested"),
        "batch.hull_hook_effective.mode": dig(row.entry, "hull_hook_effective", "mode"),
    }
    want = {
        "mode": "fast",
        "requested": "fast",
        "fallback_reason": None,
        "dll_sha256": DLL_SHA256,
        "batch.hull_hook_requested": "fast",
        "batch.hull_hook_effective.mode": "fast",
    }
    return [f"{k} {plain(values[k])!r} != {want[k]!r}" for k in want if values[k] != want[k]]


def planned_pool(inputs: JudgeInputs, row: RowInput) -> Any:
    """The pool of the prelaunch batch plan, else the row's ``planned_pool`` (None = unknown)."""
    pool = dig(inputs.prelaunch, "batch_plan", "planned_pool", row.spec.case)
    if isinstance(pool, str):
        return pool
    pool = dig(row.entry, "planned_pool")
    return pool if isinstance(pool, str) else None


def k4_row_problems(inputs: JudgeInputs, row: RowInput) -> list[str]:
    result, entry = row.result or {}, row.entry or {}
    placement = result.get("placement") if isinstance(result.get("placement"), dict) else {}
    problems = []
    threads = scalar(dig(result, "args", "threads"))
    if threads != THREADS or result.get("num_threads_chrono") != THREADS:
        problems.append(
            f"threads {threads!r} / num_threads_chrono "
            f"{result.get('num_threads_chrono')!r} != {THREADS}"
        )
    if entry.get("omp_wait_policy") != "PASSIVE":
        problems.append(f"omp_wait_policy {entry.get('omp_wait_policy')!r}")
    pool, mode = entry.get("pool"), placement.get("mode")
    plan = planned_pool(inputs, row)
    if mode != pool or (plan is not None and pool != plan):
        problems.append(f"placement {mode!r} / batch pool {pool!r} / plan {plan!r}")
    for key in ("affinity_ok", "power_throttling_off_ok"):
        if placement.get(key) is not True:
            problems.append(f"placement.{key} {placement.get(key)!r}")
    return problems


def pool_group_problems(rows: dict[str, RowInput]) -> list[str]:
    problems = []
    for group in POOL_GROUPS:
        modes = {
            key: dig(rows[key].result, "placement", "mode")
            for key in group
            if not rows[key].is_missing
        }
        if len({plain(m) for m in modes.values()}) > 1:
            problems.append(f"pool kinds differ in {group}: {plain(modes)}")
    return problems


def option_values(argv: list[str], names: Iterable[str]) -> tuple[list[str], dict[str, Any]]:
    """``argv`` without the named options (``--x v`` or ``--x=v``) and their values."""
    wanted = set(names)
    rest: list[str] = []
    values: dict[str, Any] = {}
    i = 0
    while i < len(argv):
        token = str(argv[i])
        name, has_equals, value = token.partition("=")
        if name in wanted and has_equals:
            values[name] = value
        elif token in wanted and i + 1 < len(argv):
            values[token] = str(argv[i + 1])
            i += 1
        else:
            rest.append(token)
        i += 1
    return rest, values


def argv_of(row: RowInput) -> list[str] | None:
    argv = dig(row.entry, "argv")
    return [str(t) for t in argv] if isinstance(argv, list) else None


def argv_pair_problems(
    first: RowInput,
    second: RowInput,
    option: str,
    want: tuple[str, str],
    default: str,
) -> list[str]:
    """K-5: the two argv differ in ``--case`` and the value of ``option`` only
    (absent = ``default``)."""
    argv_a, argv_b = argv_of(first), argv_of(second)
    if argv_a is None or argv_b is None:
        return [f"{first.spec.rem_key}/{second.spec.rem_key}: argv missing"]
    rest_a, values_a = option_values(argv_a, (CASE_OPTION, option))
    rest_b, values_b = option_values(argv_b, (CASE_OPTION, option))
    problems = []
    if rest_a != rest_b:
        problems.append(
            f"{first.spec.rem_key}/{second.spec.rem_key}: argv differ beyond "
            f"{CASE_OPTION} and {option}"
        )
    got = (values_a.get(option, default), values_b.get(option, default))
    if got != want:
        problems.append(f"{first.spec.rem_key}/{second.spec.rem_key}: {option} {got} != {want}")
    return problems


def k5_row_problems(row: RowInput) -> list[str]:
    """K-5: result.json ``args`` against rules 2.1 - 2.3 and the VB / V0 argv rule."""
    spec, args = row.spec, dig(row.result, "args")
    args = args if isinstance(args, dict) else {}
    want = {
        **FIXED_ARGS,
        "case": spec.case,
        "soil": spec.soil,
        "level": spec.level,
        "mass_scale": spec.mass_scale,
        "k1_order_gate": spec.gate,
        "k1_forced_block": spec.forced,
        "expect_controller": spec.tag,
    }
    problems = [
        f"args.{k} {plain(scalar(args.get(k, MISSING)))!r} != {v!r}"
        for k, v in want.items()
        if scalar(args.get(k, MISSING)) != v
    ]
    problems += [
        f"args.{k} {args[k]!r} != 0"
        for k in FLAT_FLOOR_ARGS
        if k in args and scalar(args[k]) != 0.0
    ]
    argv = argv_of(row) or []
    has_vb = [token for token in VB_OPTION_TOKENS if token in argv]
    if spec.setting == "VB" and len(has_vb) != len(VB_OPTION_TOKENS):
        problems.append(f"VB argv lacks {sorted(set(VB_OPTION_TOKENS) - set(has_vb))}")
    if spec.setting == "V0" and has_vb:
        problems.append(f"V0 argv has v5 options {has_vb}")
    return problems


def vb_consistency_problems(rows: dict[str, RowInput]) -> list[str]:
    """K-5: every VB row has the same v5 arguments; R4 and R5 differ in the plant and tag only."""
    problems = []
    vb_values = {
        key: tuple(plain(scalar(dig(row.result, "args", k))) for k in VB_ARG_KEYS)
        for key, row in rows.items()
        if row.spec.setting == "VB" and not row.is_missing
    }
    if len(set(vb_values.values())) > 1:
        problems.append("v5 VB argument values differ between the VB rows")
    r4, r5 = rows["R4"], rows["R5"]
    if not r4.is_missing and not r5.is_missing:
        argv_r4, argv_r5 = argv_of(r4), argv_of(r5)
        if argv_r4 is None or argv_r5 is None:
            problems.append("R4/R5: argv missing")
        else:
            rest_r4 = strip_vb_argv(option_values(argv_r4, (CASE_OPTION, EXPECT_OPTION))[0])
            rest_r5 = option_values(argv_r5, (CASE_OPTION, EXPECT_OPTION))[0]
            if rest_r4 != rest_r5:
                problems.append("R4/R5: argv differ beyond the v5 options, case and tag")
    return problems


def strip_vb_argv(argv: list[str]) -> list[str]:
    """``argv`` without the ``v5_vb_argv`` options (flags and ``--x value`` pairs)."""
    flags = {"--rod-release-force", "--lock-window-follows-plant", "--extend-start-tracked"}
    valued = set(VB_OPTION_TOKENS) - flags
    rest, _ = option_values(argv, valued)
    return [token for token in rest if token not in flags]


def per_row_check(
    check_id: str,
    keys: Iterable[str],
    rows: dict[str, RowInput],
    problems_of: Callable[[RowInput], list[str]],
) -> dict[str, Any]:
    """One K check over the usable rows of ``keys`` (MISSING rows are not checked, K-9)."""
    found = {key: problems_of(rows[key]) for key in keys if not rows[key].is_missing}
    return check(
        check_id,
        all(not p for p in found.values()),
        rows={k: v for k, v in found.items() if v},
        checked=sorted(found),
    )


def identity_checks(inputs: JudgeInputs, keys: Iterable[str]) -> list[dict[str, Any]]:
    """K-1 .. K-5 over ``keys`` (the judge rows, or one diagnostic row)."""
    keys = tuple(keys)
    rows = inputs.rows
    shared = k1_batch_items(inputs)
    k1 = per_row_check("K-1", keys, rows, lambda r: k1_row_problems(r, shared))
    k1.update(shared=plain(shared), ok=k1["ok"] and k1_shared_ok(shared))
    k2 = per_row_check("K-2", keys, rows, lambda r: k2_row_problems(inputs, r))
    k2_batch = k2_batch_problems(inputs)
    k2.update(batch_problems=k2_batch, ok=k2["ok"] and not k2_batch)
    k3 = per_row_check("K-3", keys, rows, k3_row_problems)
    is_mixed = inputs.batch.get("mixed_hull_mode")
    k3.update(
        mixed_hull_mode=is_mixed,
        prelaunch_dll=dig(inputs.prelaunch, "dll", "sha256"),
        ok=k3["ok"] and is_mixed is False and dig(inputs.prelaunch, "dll", "sha256") == DLL_SHA256,
    )
    k4 = per_row_check("K-4", keys, rows, lambda r: k4_row_problems(inputs, r))
    groups = pool_group_problems(rows)
    k4.update(pool_groups=groups, ok=k4["ok"] and not groups)
    k5 = per_row_check("K-5", keys, rows, k5_row_problems)
    k5_extra = vb_consistency_problems(rows) + pair_argv_problems(rows, keys)
    k5.update(batch_problems=k5_extra, ok=k5["ok"] and not k5_extra)
    return [k1, k2, k3, k4, k5]


def pair_argv_problems(rows: dict[str, RowInput], keys: tuple[str, ...]) -> list[str]:
    problems = []
    for on_key, off_key in GATE_PAIRS:
        if {on_key, off_key} <= set(keys) and not (
            rows[on_key].is_missing or rows[off_key].is_missing
        ):
            problems += argv_pair_problems(
                rows[off_key], rows[on_key], GATE_OPTION, (GATE_OFF, GATE_ON), "<absent>"
            )
    for forced_key, on_key, _ in FORCED_PAIRS:
        if forced_key in keys and not (rows[forced_key].is_missing or rows[on_key].is_missing):
            problems += argv_pair_problems(
                rows[on_key],
                rows[forced_key],
                FORCED_OPTION,
                (FORCED_OFF, FORCED_FIRST),
                FORCED_OFF,
            )
    return problems


# ================================================================ K-6 .. K-9 (consistency)
def forced_setup(result: dict[str, Any]) -> tuple[Any, Any]:
    """(requested mode, class name) of ``c2_setup.k1_forced_block`` (a dict or a bare mode)."""
    setup = dig(result, "c2_setup", "k1_forced_block")
    if isinstance(setup, dict):
        return setup.get("requested"), setup.get("class")
    return setup, MISSING


def class_tail(name: Any) -> Any:
    return str(name).rsplit(".", 1)[-1] if isinstance(name, str) else name


def k6_row_problems(row: RowInput, analysis: RowAnalysis) -> list[str]:
    """K-6 for a judge row."""
    result, spec = row.result or {}, row.spec
    meta = result.get("controller_meta") or {}
    requested, class_name = forced_setup(result)
    values = {
        "c2_setup.expect_controller.ok": dig(result, "c2_setup", "expect_controller", "ok"),
        "c2_setup.k1_order_gate": dig(result, "c2_setup", "k1_order_gate"),
        "order_gate.enabled": dig(meta, "slope_clearance_margin", "order_gate", "enabled"),
        "loc_revoke.keep_slope_margin_on_revoke": dig(
            meta, "loc_revoke", "settings", "keep_slope_margin_on_revoke"
        ),
        "loc_revoke.max_revokes": dig(meta, "loc_revoke", "settings", "max_revokes"),
        "controller_meta.period_s": dig(meta, "period_s"),
        "controller_meta.k1_forced_block": "present" if "k1_forced_block" in meta else "absent",
        "c2_setup.k1_forced_block": requested,
        "controller class": class_tail(class_name),
        "order_gate.decisions": "present" if analysis.decisions is not None else "absent",
    }
    want = {
        "c2_setup.expect_controller.ok": True,
        "c2_setup.k1_order_gate": spec.gate,
        "order_gate.enabled": spec.gate == GATE_ON,
        "loc_revoke.keep_slope_margin_on_revoke": True,
        "loc_revoke.max_revokes": MAX_REVOKES,
        "controller_meta.period_s": PERIOD_S,
        "controller_meta.k1_forced_block": "absent",
        "c2_setup.k1_forced_block": FORCED_OFF,
        "controller class": PLAIN_CLASS_NAME,
        "order_gate.decisions": "present",
    }
    problems = [f"{k} {plain(values[k])!r} != {want[k]!r}" for k in want if values[k] != want[k]]
    if spec.gate == GATE_OFF:
        if len(analysis.r4_decisions) > 1:
            problems.append(f"gate off: {len(analysis.r4_decisions)} R4 decisions (keep assumed)")
        skipped = periods_with_full(analysis.events, SKIP_ORDER_EVENT)
        if skipped:
            problems.append(f"gate off: {len(skipped)} {SKIP_ORDER_EVENT} events")
    return problems


def k8_row_problems(analysis: RowAnalysis, is_gate_on_judge: bool) -> list[str]:
    """K-8 (a) - (f) on one usable row with decisions."""
    decisions = analysis.decisions
    if decisions is None:
        return ["no decisions (K-6)"]
    problems = []
    first_start = min((n for n, _, _ in analysis.mode_starts), default=None)
    e3c10 = set(analysis.e3c10_loc_periods)
    expected_locs = [
        n
        for n in analysis.loc_periods
        if first_start is not None and first_start < n and n not in e3c10
    ]
    if len(decisions) != len(expected_locs):  # (a)
        problems.append(
            f"(a) {len(decisions)} decisions != {len(expected_locs)} LOCs after the "
            "soil-mode start without E3c10"
        )
    loc_set = set(analysis.loc_periods)
    for d in decisions:
        if d.n_loc not in loc_set:  # (b)
            problems.append(f"(b) decision {d.index} period {d.n_loc} has no LOC event")
        earlier = [t for n, t, _ in analysis.mode_starts if d.n_loc is not None and n < d.n_loc]
        if not earlier or d.t_S_s != earlier[-1]:  # (c)
            problems.append(
                f"(c) decision {d.index} t_S_s {d.t_S_s!r} != last earlier mode "
                f"start {earlier[-1] if earlier else None!r}"
            )
    if sorted(analysis.revoke_periods) != sorted(analysis.revoke_event_periods):  # (d)
        problems.append(
            f"(d) revocations meta {analysis.revoke_periods} != events "
            f"{analysis.revoke_event_periods}"
        )
    problems += k8_event_problems(analysis)
    l1 = analysis.l1
    if is_gate_on_judge and l1 is not None and l1.is_applied:  # (f) = rules 3.3 #5
        later = [d for d in analysis.r4_decisions if d.index > l1.index]
        skips = periods_with_full(analysis.events, SKIP_ORDER_EVENT)
        if later or skips:
            problems.append(
                f"(f) L1 applied but {len(later)} later R4 decisions / "
                f"{len(skips)} {SKIP_ORDER_EVENT} events"
            )
    return problems


def k8_event_problems(analysis: RowAnalysis) -> list[str]:
    """K-8 (e): applied <-> one ``INFO_LOC_FLAT_SOIL_MARGIN:`` event, blocked <-> one
    ``..._SKIPPED:order`` event, in the decision's period and in total."""
    margins = periods_with_base(analysis.events, MARGIN_EVENT)
    skips = periods_with_full(analysis.events, SKIP_ORDER_EVENT)
    decisions = analysis.decisions or []
    applied = [d for d in decisions if d.is_applied]
    blocked = [d for d in decisions if d.would_block and not d.is_applied]
    problems = [
        f"(e) applied decision {d.index}: {margins.count(d.n_loc)} margin events"
        for d in applied
        if margins.count(d.n_loc) != 1
    ]
    problems += [
        f"(e) blocked decision {d.index}: {skips.count(d.n_loc)} skip events"
        for d in blocked
        if skips.count(d.n_loc) != 1
    ]
    if len(margins) != len(applied) or len(skips) != len(blocked):
        problems.append(
            f"(e) events margin {len(margins)} / skip {len(skips)} != decisions "
            f"applied {len(applied)} / blocked {len(blocked)}"
        )
    return problems


def ends_by_fault_before(row: RowInput, n_loc: int | None) -> bool:
    """4.2 ``부분 통과`` example: the gate-on row ended by a FAULT before the pair's $L_1$."""
    result = row.result or {}
    if n_loc is None or last_phase(result) != FAULT_PHASE:
        return False
    faults = [period_of(t) for t, n in events_of(result) if event_base_name(n).startswith("FAULT_")]
    return bool(faults) and min(faults) < n_loc


def check_k7(rows: dict[str, RowInput], analyses: dict[str, RowAnalysis]) -> dict[str, Any]:
    """K-7: $L_1$ tuples of R7 / R1 and R8 / R4 identical (both NO_R4: same first LOC period).
    A missing row or a gate-on row ended by a FAULT before the pair $L_1$ leaves the pair
    unevaluated (``ok`` None, condition ③ false)."""
    pairs = {}
    for on_key, off_key in GATE_PAIRS:
        if rows[on_key].is_missing or rows[off_key].is_missing:
            pairs[on_key] = {"ok": None, "reason": "row missing"}
            continue
        on, off = analyses[on_key], analyses[off_key]
        if on.l1 is not None and off.l1 is not None:
            ok = on.l1.l1_tuple() == off.l1.l1_tuple()
            pairs[on_key] = {"ok": ok, "gate_on": on.l1.l1_tuple(), "gate_off": off.l1.l1_tuple()}
        elif on.l1 is None and off.l1 is None:
            first = (on.loc_periods[:1], off.loc_periods[:1])
            pairs[on_key] = {"ok": first[0] == first[1], "first_loc_periods": first}
        elif on.l1 is None and ends_by_fault_before(rows[on_key], off.l1.n_loc):
            pairs[on_key] = {"ok": None, "reason": "gate-on row ended by a FAULT before L1"}
        else:
            pairs[on_key] = {"ok": False, "reason": "L1 in one row only"}
    values = [p["ok"] for p in pairs.values()]
    return check("K-7", False if False in values else True, pairs=pairs)


def check_k9(rows: dict[str, RowInput]) -> dict[str, Any]:
    """K-9: ``MISSING`` was given by the rules 7 conditions (re-derived here)."""
    mismatches = [
        key
        for key, row in rows.items()
        if bool(missing_reasons_of(row.result, row.entry)) != row.is_missing
        and "batch.json missing or unreadable" not in row.missing_reasons
    ]
    return check(
        "K-9",
        not mismatches,
        mismatches=mismatches,
        missing={k: r.missing_reasons for k, r in rows.items() if r.is_missing},
    )


# ================================================================ pairs, flags, diagnostics
def gate_on_path(analysis: RowAnalysis) -> dict[str, Any]:
    """Rules 3.3 #4 / ``GATEON_PATH``: the R4 decisions of a gate-on row and the outcome."""
    r4 = analysis.r4_decisions
    if not r4:
        outcome = STATE_NO_R4
    elif r4[0].is_applied:
        outcome = PATH_L1_APPLIED
    elif any(d.is_applied for d in r4[1:]):
        outcome = PATH_LATE
    else:
        outcome = PATH_NEVER
    return {
        "outcome": outcome,
        "r4_decisions": [
            {"n_loc": d.n_loc, "dP": d.dP, "applied": d.is_applied, "struct_zero": d.is_struct_zero}
            for d in r4
        ],
    }


def condition_3(
    rows: dict[str, RowInput],
    analyses: dict[str, RowAnalysis],
    states: dict[str, str],
    k7: dict[str, Any],
) -> dict[str, Any]:
    """Condition ③ per gate pair."""
    pairs = {}
    for on_key, off_key in GATE_PAIRS:
        pair_k7 = k7["pairs"][on_key]
        if rows[on_key].is_missing:
            pairs[on_key] = {"ok": False, "reason": "gate-on row missing"}
        elif pair_k7["ok"] is not True:
            pairs[on_key] = {"ok": False, "reason": f"K-7 {pair_k7.get('reason', pair_k7['ok'])}"}
        elif states.get(off_key) != STATE_POS:
            pairs[on_key] = {
                "ok": True,
                "checked": False,
                "reason": f"gate-off state {states.get(off_key)} (not checked)",
            }
        else:
            on = analyses[on_key]
            l1 = on.l1
            margins = periods_with_base(on.events, MARGIN_EVENT)
            is_ok = l1 is not None and l1.is_applied and l1.n_loc in margins
            pairs[on_key] = {
                "ok": is_ok,
                "checked": True,
                "L1_applied": l1 is not None and l1.is_applied,
                "margin_event_at_L1": l1 is not None and l1.n_loc in margins,
            }
    return {"ok": all(p["ok"] for p in pairs.values()), "pairs": pairs}


def pair_commands(rows: dict[str, RowInput], first: str, second: str) -> dict[str, Any]:
    """P-8 / ``PAIR_DIVERGE`` record: command digests of two rows and the first differing period."""
    a, b = rows[first].commands, rows[second].commands
    if a is None or b is None:
        return {"rows": [first, second], "same": None, "reason": "controller_commands.npz unread"}
    is_same = a.sha256 == b.sha256
    return {
        "rows": [first, second],
        "same": is_same,
        "sha256": [a.sha256, b.sha256],
        "first_difference_period": None if is_same else first_command_difference(a, b),
    }


def shadow_relocs(analyses: dict[str, RowAnalysis]) -> dict[str, Any]:
    """``SHADOW_RELOC``: gate-off rows' post-revocation decisions that are not R4 evaluations."""
    items = [
        {"row": key, "n_loc": d.n_loc, "dP": d.dP, "struct_zero": d.is_struct_zero}
        for key in GATEOFF_KEYS
        if key in analyses
        for d in analyses[key].decisions or []
        if d.is_post_revoke and not d.is_r4_due
    ]
    zeros = sum(1 for item in items if item["struct_zero"])
    return {
        "count": len(items),
        "struct_zero": zeros,
        "struct_zero_ratio": zeros / len(items) if items else None,
        "items": items,
    }


def build_flags(
    rows: dict[str, RowInput],
    analyses: dict[str, RowAnalysis],
    states: dict[str, str],
) -> dict[str, Any]:
    """Rules 6 FLAG records of the judge rows (no grade effect)."""
    thin, late, shift, harness = [], [], {}, {}
    for key in GATEOFF_KEYS:
        l1 = analyses[key].l1 if key in analyses else None
        if states.get(key) == STATE_POS and l1 is not None:
            if l1.dP <= THIN_MARGIN_PERIODS:
                thin.append({"row": key, "dP": l1.dP})
            if l1.is_post_revoke:
                late.append({"row": key, "n_loc": l1.n_loc, "dP": l1.dP})
        if key in HARNESS_DP:
            harness[key] = {
                "harness_dP": list(HARNESS_DP[key]),
                "chrono_dP": None if l1 is None else l1.dP,
            }
    for key in JUDGE_KEYS:
        l1 = analyses[key].l1 if key in analyses else None
        old_n_R, old_n_S = OLD_CONTROLLER_VALUES[key]
        shift[key] = (
            None
            if l1 is None or l1.n_loc is None or l1.n_S is None
            else {"n_loc_minus_old_n_R": l1.n_loc - old_n_R, "n_S_minus_old_n_S": l1.n_S - old_n_S}
        )
    diverge = [pair_commands(rows, off, on) for on, off in GATE_PAIRS]
    return {
        "THIN_MARGIN": thin,
        "LATE_R4": late,
        "SHADOW_RELOC": shadow_relocs(analyses),
        "PAIR_DIVERGE": [d for d in diverge if d["same"] is False],
        "pair_commands": diverge,
        "GATEON_PATH": {
            key: gate_on_path(analyses[key]) for key in ("R7", "R8") if key in analyses
        },
        "OLD_CTRL_SHIFT": shift,
        "harness_comparison": harness,
    }


def forced_meta_problems(inputs: JudgeInputs, row: RowInput, analysis: RowAnalysis) -> list[str]:
    """Rules 5 F1 / F2-only items."""
    result = row.result or {}
    meta = dig(result, "controller_meta", "k1_forced_block")
    meta = meta if isinstance(meta, dict) else {}
    requested, class_name = forced_setup(result)
    want_sha = prelaunch_file_sha(inputs, FORCED_BLOCK_PATH)
    calls = meta.get("calls") if isinstance(meta.get("calls"), list) else []
    forced_calls = sum(1 for c in calls if isinstance(c, dict) and c.get("forced") is True)
    problems = []
    if meta.get("mode") != FORCED_FIRST:
        problems.append(f"k1_forced_block.mode {meta.get('mode')!r}")
    if class_tail(meta.get("class")) != FORCED_CLASS_NAME or meta.get("class") != class_name:
        problems.append(f"class meta {meta.get('class')!r} / c2_setup {plain(class_name)!r}")
    if meta.get("module_sha256") != want_sha:
        problems.append(f"module_sha256 {meta.get('module_sha256')!r} != K-2 {want_sha!r}")
    if requested != FORCED_FIRST:
        problems.append(f"c2_setup.k1_forced_block {plain(requested)!r}")
    if (
        dig(result, "controller_meta", "slope_clearance_margin", "order_gate", "enabled")
        is not True
    ):
        problems.append("order gate not enabled")
    if forced_calls != 1:
        problems.append(f"{forced_calls} forced calls")
    if analysis.decisions is None:
        problems.append("no decisions")
    return problems


def forced_path(analysis: RowAnalysis) -> dict[str, Any]:
    """Rules 2.3 path classification after the forced block at $L_1$."""
    l1 = analysis.l1
    if l1 is None:
        return {"path": None, "reason": "no R4-evaluated LOC"}
    revokes_after = [n for n in analysis.revoke_periods if l1.n_loc is not None and n > l1.n_loc]
    reevaluations = [d for d in analysis.r4_decisions if d.index > l1.index]
    applied = [d for d in reevaluations if d.is_applied]
    if not revokes_after:
        path = FORCED_NO_REVOKE
    elif applied:
        path = FORCED_LATE
    elif reevaluations:
        path = FORCED_NEVER
    else:
        path = FORCED_REVOKED_NO_REEVAL
    return {
        "path": path,
        "revokes_after_L1": revokes_after,
        "reevaluations": [
            {"n_loc": d.n_loc, "dP": d.dP, "applied": d.is_applied, "struct_zero": d.is_struct_zero}
            for d in reevaluations
        ],
        "late_applied": None if not applied else {"n_loc": applied[0].n_loc, "dP": applied[0].dP},
    }


def diagnostic_record(
    inputs: JudgeInputs, key: str, analyses: dict[str, RowAnalysis]
) -> dict[str, Any]:
    """Rules 2.3 information record of one F row (never graded)."""
    row = inputs.rows[key]
    if row.is_missing:
        return {
            "rem_key": key,
            "valid": False,
            "information": "none (row missing)",
            "missing_reasons": row.missing_reasons,
        }
    analysis = analyses[key]
    identity = identity_checks(inputs, (key,))
    own = forced_meta_problems(inputs, row, analysis)
    is_valid = all(c["ok"] for c in identity) and not own
    meta = dig(row.result, "controller_meta", "k1_forced_block")
    forced_n_loc = meta.get("forced_n_loc") if isinstance(meta, dict) else None
    _, _, pair_key = next(p for p in FORCED_PAIRS if p[0] == key)
    pair = analyses.get(pair_key)
    l1 = analysis.l1
    pair_l1 = None if pair is None or pair.l1 is None else pair.l1.l1_tuple()
    is_pair_same = l1 is not None and pair_l1 is not None and l1.l1_tuple() == pair_l1
    return {
        "rem_key": key,
        "valid": is_valid,
        "K-1..K-5": identity,
        "forced_items": {"ok": not own, "problems": own},
        "FORCED_AT_L1": l1 is not None and forced_n_loc == l1.n_loc,
        "FORCED_PAIR_L1": is_pair_same,
        "pair_row": pair_key,
        "trajectory_note": None if is_pair_same else "짝과 다른 궤적 (not interpreted)",
        "L1": None if l1 is None else l1.to_record(),
        "L1_blocked": l1 is not None and l1.would_block and not l1.is_applied,
        **forced_path(analysis),
        "end": end_record(row),
    }


# ================================================================ grade (rules 4)
def decide_grade(
    k_checks: list[dict[str, Any]], states: dict[str, str], cond3: dict[str, Any]
) -> tuple[str, list[str], bool]:
    """Rules 4.2 (first match); returns (grade, reasons, condition ①)."""
    failed = [c["id"] for c in k_checks if c["ok"] is False]
    gateoff = {key: states[key] for key in GATEOFF_KEYS}
    pos = [k for k, s in gateoff.items() if s == STATE_POS]
    is_cond1 = (
        all(s in (STATE_POS, STATE_NO_R4) for s in gateoff.values())
        and len(pos) >= MIN_POS_ROWS
        and any(gateoff[k] == STATE_POS for k in MASS_KEYS)
    )
    if failed:
        return GRADE_STOP, [f"{c} false" for c in failed], is_cond1
    nonpos = [f"MEASURED_NONPOS {k}" for k, s in gateoff.items() if s == STATE_NONPOS]
    struct = [f"STRUCT_ZERO {k}" for k, s in gateoff.items() if s == STATE_LATE_STRUCT]
    if nonpos or struct:
        return GRADE_FAIL, nonpos + struct, is_cond1
    undecidable = [f"MISSING {k}" for k, s in gateoff.items() if s == STATE_MISSING]
    if len(pos) < MIN_POS_ROWS:
        undecidable.append(f"POS {len(pos)} < {MIN_POS_ROWS}")
    if all(gateoff[k] == STATE_NO_R4 for k in MASS_KEYS):
        undecidable.append("R4 and R5 both NO_R4")
    if undecidable:
        return GRADE_UNDECIDABLE, undecidable, is_cond1
    if not cond3["ok"]:
        reasons = [
            f"③ {k}: {p.get('reason', 'L1 not applied')}"
            for k, p in cond3["pairs"].items()
            if not p["ok"]
        ]
        return GRADE_PARTIAL, reasons, is_cond1
    return GRADE_PASS, [], is_cond1


def inside(value: Any, low: float, high: float) -> bool | None:
    return None if not is_number(value) else bool(low <= value <= high)


def predictions(
    analyses: dict[str, RowAnalysis],
    states: dict[str, str],
    flags: dict[str, Any],
    grade: str,
    diag: dict[str, Any],
) -> list[dict[str, Any]]:
    """Rules 8 P-1 .. P-11: inside / outside (record, not a criterion)."""

    def dP(key: str) -> Any:
        l1 = analyses[key].l1 if key in analyses else None
        return None if l1 is None else l1.dP

    def all_inside(keys: tuple[str, ...], low: float, high: float) -> bool | None:
        results = [inside(dP(k), low, high) for k in keys]
        return None if None in results else all(results)

    gateoff_states = [states[k] for k in GATEOFF_KEYS]
    revoked = sum(
        1
        for k in GATEOFF_KEYS
        if k in analyses
        and analyses[k].l1 is not None
        and any(n > analyses[k].l1.n_loc for n in analyses[k].revoke_periods)
    )
    n_loc_gap = None
    if all(k in analyses and analyses[k].l1 for k in MASS_KEYS):
        n_loc_gap = abs(analyses["R5"].l1.n_loc - analyses["R4"].l1.n_loc)
    dP_gap = None if dP("R4") is None or dP("R5") is None else abs(dP("R4") - dP("R5"))
    ratio = flags["SHADOW_RELOC"]["struct_zero_ratio"]
    paths = flags["GATEON_PATH"]
    commands = [p["same"] for p in flags["pair_commands"]]
    return [
        {
            "id": "P-1",
            "value": [dP(k) for k in ("R1", "R2", "R3")],
            "inside": all_inside(("R1", "R2", "R3"), 60, 140),
        },
        {
            "id": "P-2",
            "value": {"dP": [dP("R4"), dP("R5")], "n_loc_gap": n_loc_gap},
            "inside": None
            if all_inside(MASS_KEYS, 120, 240) is None or n_loc_gap is None
            else all_inside(MASS_KEYS, 120, 240) and n_loc_gap <= 20,
        },
        {"id": "P-3", "value": dP("R6"), "inside": inside(dP("R6"), 90, 180)},
        {
            "id": "P-4",
            "value": gateoff_states,
            "inside": all(s == STATE_POS for s in gateoff_states),
        },
        {"id": "P-5", "value": revoked, "inside": 4 <= revoked <= 6},
        {"id": "P-6", "value": ratio, "inside": None if ratio is None else ratio >= 0.7},
        {
            "id": "P-7",
            "value": dP_gap,
            "inside": None
            if dP_gap is None
            else states["R4"] == states["R5"] == STATE_POS and dP_gap <= 30,
        },
        {
            "id": "P-8",
            "value": {
                "paths": {k: v["outcome"] for k, v in paths.items()},
                "commands_same": commands,
            },
            "inside": all(v["outcome"] == PATH_L1_APPLIED for v in paths.values())
            and len(paths) == len(GATE_PAIRS)
            and all(c is True for c in commands),
        },
        {"id": "P-9", "value": len(flags["THIN_MARGIN"]), "inside": not flags["THIN_MARGIN"]},
        {"id": "P-10", "value": grade, "inside": grade == GRADE_PASS},
        {
            "id": "P-11",
            "value": {
                k: (d.get("FORCED_AT_L1"), d.get("FORCED_PAIR_L1"), d.get("path"))
                for k, d in diag.items()
            },
            "inside": all(
                d.get("FORCED_AT_L1") is True and d.get("FORCED_PAIR_L1") is True
                for d in diag.values()
            ),
        },
    ]


def judge(inputs: JudgeInputs) -> dict[str, Any]:
    """K-0 .. K-9, rules 3 - 6 and the 2.3 records on the loaded inputs (no I/O)."""
    rows = inputs.rows
    analyses = {key: analyze_row(row) for key, row in rows.items() if not row.is_missing}
    states = {
        key: STATE_MISSING if rows[key].is_missing else row_state(analyses[key])
        for key in JUDGE_KEYS
    }
    k_checks = [check_k0(inputs), *identity_checks(inputs, JUDGE_KEYS)]
    k6 = per_row_check(
        "K-6", JUDGE_KEYS, rows, lambda r: k6_row_problems(r, analyses[r.spec.rem_key])
    )
    k7 = check_k7(rows, analyses)
    k8 = per_row_check(
        "K-8",
        JUDGE_KEYS,
        rows,
        lambda r: k8_row_problems(analyses[r.spec.rem_key], r.spec.gate == GATE_ON),
    )
    k_checks += [k6, k7, k8, check_k9(rows)]
    cond3 = condition_3(rows, analyses, states, k7)
    diag = {key: diagnostic_record(inputs, key, analyses) for key in DIAG_KEYS}
    flags = build_flags(rows, analyses, states)
    grade, reasons, is_cond1 = decide_grade(k_checks, states, cond3)
    return {
        "rows": {key: row_record(rows[key], analyses.get(key)) for key in rows},
        "states": states,
        "k_checks": k_checks,
        "pairs": {"condition_3": cond3, "K-7": k7},
        "conditions": {
            "①": is_cond1,
            "②": {"ok": True, "note": "기지 행뿐 (adopt ②, S-Ch 2 rows dP -20; no patch row here)"},
            "③": cond3["ok"],
        },
        "flags": flags,
        "diag": diag,
        "grade_provisional": grade,
        "grade_code": GRADE_CODES[grade],
        "grade_reasons": reasons,
        "observed_block_revoke_reeval_in_judge_rows": any(
            v["outcome"] in (PATH_LATE, PATH_NEVER) for v in flags["GATEON_PATH"].values()
        ),
        "predictions": predictions(analyses, states, flags, grade, diag),
        "k10": None,
        "provisional": True,
        "provisional_note": "grade provisional: K-10 (two-path recount, rules 9.2) is confirmed "
        "in the judgement document, not by this tool",
    }


# ================================================================ output and command line
def summary_line(doc: dict[str, Any], out_path: Path) -> str:
    summary = {
        "kind": doc.get("kind"),
        "status": doc.get("status"),
        "exit_code": doc.get("exit_code"),
        "out": out_path.as_posix(),
    }
    if doc.get("kind") == "judge":
        summary.update(grade_provisional=doc.get("grade_code"), k10=doc.get("k10"))
    if isinstance(doc.get("checks"), dict):
        summary["failed_checks"] = [k for k, ok in doc["checks"].items() if not ok]
    if doc.get("grade_reasons"):
        summary["grade_reasons"] = doc["grade_reasons"]
    return json.dumps(plain(summary), ensure_ascii=True)


def write_output(doc: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(plain(doc), indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="LAS-b K1 re-measure judge (las_k1_rules_adopt2.md)"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prelaunch", "postrun", "judge"):
        command = sub.add_parser(name)
        command.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="project root")
        command.add_argument(
            "--out", type=Path, default=None, help="output file (default under v5/las/k1)"
        )
        if name == "prelaunch":
            command.add_argument(
                "--batch-plan",
                type=Path,
                required=True,
                help="row list JSON of the batch to launch",
            )
            command.add_argument(
                "--audit-report",
                type=Path,
                default=None,
                help=f"pre-run audit report (default v5/las/k1/{AUDIT_REPORT_NAME})",
            )
            command.add_argument(
                "--allow-dirty",
                action="append",
                default=[],
                help="git status path allowed to differ (repeatable; default none)",
            )
        else:
            command.add_argument("--prelaunch", type=Path, default=None)
            command.add_argument(
                "--batch",
                type=Path,
                required=True,
                help="07_results/S9/batch_V5-LAS-K1-REM_<stamp>",
            )
        if name == "judge":
            command.add_argument("--postrun", type=Path, default=None)
            command.add_argument("--rules", type=Path, default=None)
            command.add_argument(
                "--expect-tool-sha", required=True, help="tool sha256 of the pre-run audit record"
            )
    return parser


def default_path(root: Path, name: str) -> Path:
    return root / OUT_DIR_RELATIVE / name


def run_command(args: argparse.Namespace) -> tuple[dict[str, Any], Path]:
    root = args.root.resolve()
    if not root.is_dir():
        raise InputError(f"--root {root}: no such folder")
    if args.command == "prelaunch":
        if not args.batch_plan.is_file():
            raise InputError(f"--batch-plan {args.batch_plan}: no such file")
        audit = args.audit_report or default_path(root, AUDIT_REPORT_NAME)
        doc = prelaunch_document(root, args.batch_plan.resolve(), audit.resolve(), args.allow_dirty)
        doc["exit_code"] = 0 if doc["all_ok"] else 2
        return doc, args.out or default_path(root, PRELAUNCH_NAME)
    if not args.batch.is_dir():
        raise InputError(f"--batch {args.batch}: no such folder")
    prelaunch_path = args.prelaunch or default_path(root, PRELAUNCH_NAME)
    if args.command == "postrun":
        doc = postrun_document(root, prelaunch_path)
        doc["batch"] = args.batch.resolve().as_posix()
        doc["exit_code"] = 0 if doc["all_ok"] else 2
        return doc, args.out or default_path(root, POSTRUN_NAME)
    postrun_path = args.postrun or default_path(root, POSTRUN_NAME)
    rules_path = args.rules or root / RULES_RELATIVE
    inputs, files_read = load_judge_inputs(
        root,
        args.batch.resolve(),
        prelaunch_path,
        postrun_path,
        rules_path,
        args.expect_tool_sha.lower(),
    )
    doc = {
        "kind": "judge",
        "rules_sha256": inputs.rules["sha256"],
        "tool_sha256": inputs.tool_sha256,
        "git_head": dig(inputs.prelaunch, "head", "sha"),
        "taken_utc": utc_now(),
        "batch": args.batch.resolve().as_posix(),
        "files_read_sha256": files_read,
        **judge(inputs),
    }
    doc["status"] = doc["grade_code"]
    doc["exit_code"] = EXIT_CODES[doc["grade_provisional"]]
    return doc, args.out or default_path(root, JUDGE_NAME)


def main(argv: list[str] | None = None) -> int:
    print(
        "PROVISIONAL: judge grades are provisional (k10 null); the judgement document confirms "
        "them after the two-path recount"
    )
    args = build_parser().parse_args(argv)
    try:
        doc, out_path = run_command(args)
    except InputError as error:
        print(json.dumps({"status": "stop", "exit_code": 2, "input_error": str(error)}))
        return 2
    except Exception as error:  # noqa: BLE001 - the contract: last line JSON, exit 3
        print(
            json.dumps(
                {
                    "status": "error",
                    "exit_code": 3,
                    "internal_error": f"{type(error).__name__}: {error}",
                }
            )
        )
        return 3
    write_output(doc, out_path)
    print(summary_line(doc, out_path))
    return doc["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
