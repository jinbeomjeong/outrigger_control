"""LAS-b K1 S-Ch judge: the Chrono SCM patch pair ``gateon`` against ``gateoff``.

Rules: the sealed supplementary plan ``las_k1_sch_plan.md`` (control-expert, sha256
:data:`PLAN_SHA256`) and its addendum ``las_k1_sch_plan_rev1.md`` (:data:`PLAN_REV1_SHA256`,
wins where the two differ), on top of ``las_k1_rules.md`` and ``las_k1_rules_rev1.md``.
The plan text wins where this code differs; section numbers in the comments are the plan's.

rev1 in this code: code diff base 92d22e0 (R1-1, :data:`BASE_COMMIT`), empty dirty allow list
(R1-2), K-0k tool sha256 equality prelaunch = postrun = judge (R1-3), a missing judged value
(E-6b ``grid_end_m``, empty E-6a end window, ``s_motor_max_m``, ``F_min_after_N``) is
``incomplete``, not a fail or a pass (R1-5); a K-0 / K-S / C-P stop still wins (T-9).

Sub-commands
  prelaunch  plan 2.3 items (1)-(6) right before the batch launch -> ``sch_prelaunch.json``
  postrun    the same items after both result.json exist, plus the differences to the
             prelaunch record -> ``sch_postrun.json``
  judge      plan 2-4 on ``07_results/S9/batch_V5-LAS-K1-CHRONO_<stamp>`` -> ``judge_SCh.json``

Read only: the only child processes are git queries (``rev-parse``, ``diff --quiet``,
``diff --name-only``, ``status --porcelain``, ``show``). No project module, ``run_S9`` or
``s9_batch`` is imported; json, hashlib and numpy only. The output files are the only writes.

Usage (dynamics-dev, PowerShell, project root):
  C:\\ProgramData\\miniforge3\\envs\\dynamics-dev\\python.exe -I -B
      06_analysis/02_control/verif_matrix/scripts/las_k1_sch_judge.py
      prelaunch | postrun [--prelaunch F] | judge --batch <folder> [--prelaunch F] [--postrun F]
      [--root R] [--out F] [--format json|md]

Exit codes: 0 pass (prelaunch / postrun: every item true), 1 fail, 2 stop, k1_inactive, a
prelaunch / postrun mismatch or an input error, 3 incomplete or an internal error. The last
stdout line is JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

TOOL_PATH = Path(__file__).resolve()
DEFAULT_ROOT = TOOL_PATH.parents[4]
OUT_DIR_RELATIVE = Path("06_analysis/03_hydraulic/coupled/v5/las/k1")
PRELAUNCH_NAME = "sch_prelaunch.json"
POSTRUN_NAME = "sch_postrun.json"
JUDGE_NAME = "judge_SCh.json"

# ---------------------------------------------------------------- sealed identity (plan 2)
RULES_DIR_RELATIVE = Path("06_analysis/02_control/verif_matrix")
PLAN_SHA256 = "b0fe744feca6fd2e2b792a0c000e08c18eb1005f30278d1d0eeaeb2f40d46d9d"
PLAN_REV1_SHA256 = "d8f957cbedd39ffec5bc36127dc3a2ec91e1d71335a464ba370dd87643069295"
PLAN_SHA256_BY_FILE = {
    "las_k1_sch_plan.md": PLAN_SHA256,
    "las_k1_sch_plan_rev1.md": PLAN_REV1_SHA256,
}
"""Both plan editions (rev1 R1-3 / T-3): every output records both."""
SEALED_RULES = {
    "las_k1_rules.md": "2742c9760ad55a87eccbf73e84025aafe0171a3555e1f54ab19fab24d888e4a0",
    "las_k1_rules_rev1.md": "eeee4ab9661babff50117b8ff579aa41e27a98d083f1fc13f46fb5c733e0b4d3",
    **PLAN_SHA256_BY_FILE,
}
"""K-0j / 2.3 (6): raw-byte sha256 of the K1 rules, their rev1 and both plan editions
(``-text`` files)."""

BASE_COMMIT = "92d22e0ea5fe527ec87bdbc7ed08fa477329345f"
"""Plan rev1 R1-1: code diff base (``f25b043`` in the original plan; the seven sealed blobs
of plan 2.1 are the same in both commits)."""
CODE_DIFF_PATHS = ("03_src", "02_params", "04_scripts")
ALLOWED_DIRTY: frozenset[str] = frozenset()
"""Plan rev1 R1-2: ``git status --porcelain`` of the code paths must be empty."""


@dataclass(frozen=True)
class SealedCodeFile:
    """One row of plan 2.1: canonical LF blob digest and the CRLF work-tree digest."""

    path: str
    blob_lf_sha256: str
    worktree_crlf_sha256: str


CODE_FILES = (
    SealedCodeFile(
        "04_scripts/02_chrono/run_S9.py",
        "914f2678f0399ba59f2616412add81c8339a9791e12210a989b9338fd6a9e3d7",
        "f672622a37041f6e1b848987a677b22c8993286f586d65fbb1cd81f4c6fd23db",
    ),
    SealedCodeFile(
        "04_scripts/02_chrono/las_k1_chrono_rows.py",
        "594198eab169715c62ca1e6fd3f06d836f099859d957c5e66a1d599459324569",
        "7e1d01ec86e4cff9d4e7c495ca7474c37efe612269cab03a614008457f2c20e0",
    ),
    SealedCodeFile(
        "04_scripts/02_chrono/s9_batch.py",
        "18aee56052c90df4b919168bf6bcd203c2663606359c2ed2ac74208f7ff646b4",
        "13e32ccad018984ffd0f0bdbc4df05dcf33a04098f3847a33384a966db99402e",
    ),
    SealedCodeFile(
        "03_src/outrigger_sim/control/c2.py",
        "254921d1a8b0c6764ef9f5266be05fad61b7d5e7c73a6e0110802491e8aaa1de",
        "a75d278030fffdeba3d3d88376a9d26eca80b79cb87c48fbb5b0ede3857fe0ed",
    ),
    SealedCodeFile(
        "03_src/outrigger_sim/control/zero_calibration.py",
        "e55d3dd646db62bfe7409857b8467ab09713df9feedfe599b97047246e038132",
        "b63a7a4713bc5be53098c08a375c348aca5769c11ac9fe5e6b085f39bcc0ffb1",
    ),
    SealedCodeFile(
        "03_src/outrigger_sim/chrono/hull_hook.py",
        "aae8495824089e7932ec5f677f85d313ecc81a23db21e4747aedfb472be65ece",
        "afef13ec8f75d42d95ddaf3342273c2ec476ae35450c665055f40100a5e3bdc3",
    ),
    SealedCodeFile(
        "04_scripts/03_control/s9/late_loc_rule.py",
        "76b549108ca39b9970e4906c5f4fe2de4ff71a6abc25989765ed552400075ee4",
        "76b549108ca39b9970e4906c5f4fe2de4ff71a6abc25989765ed552400075ee4",
    ),
)
RECORDED_CONTROLLER_FILES = (
    ("outrigger_sim.control.c2", "03_src/outrigger_sim/control/c2.py"),
    ("outrigger_sim.control.zero_calibration", "03_src/outrigger_sim/control/zero_calibration.py"),
)
"""K-0c: (result.json ``files_at_start`` module key, batch.json ``code_at_launch.files`` path)."""
CRLF_SHA256_BY_PATH = {f.path: f.worktree_crlf_sha256 for f in CODE_FILES}

DLL_PATH = "03_src/outrigger_sim/native/chrono_hull/bin/chrono_hull_hook.dll"
DLL_SHA256 = "cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15"

# ---------------------------------------------------------------- rows and run conditions (plan 1)
CASE_GATEOFF = "SCh_G1_J2FL_B_top_Fs4_VB_gateoff"
CASE_GATEON = "SCh_G1_J2FL_B_top_Fs4_VB_gateon"
GATE_OF_CASE = {CASE_GATEOFF: "off", CASE_GATEON: "on"}
ROW_FILES = ("result.json", "step_series.npz", "controller_commands.npz")
CONTROLLER_TAG = "final_C4G2_P3_LAS"
THREADS = 4
EXPECTED_ARGS = {
    "seed": 20261026,
    "pressure_grade": "normal",
    "imu_grade": "ideal",
    "fs_kN": 4.0,
    "duration": 200.0,
    "soil": "G1",
    "soil_patch": "FL:J2",
    "level": "top",
    "expect_controller": CONTROLLER_TAG,
}
ALLOWED_ARG_DIFFERENCES = frozenset({"k1_order_gate", "case"})
VALUE_OPTIONS_ALLOWED_TO_DIFFER = ("--k1-order-gate", "--case")
PROGRESS_TOKENS = ("START", "END", "RESUME_SKIP", "SKIP", "MIXED_HULL_MODE")
RERUN_FOLDER = "attempt1"

# ---------------------------------------------------------------- criteria (plan 3-4)
PERIOD_S = 0.1
PERIOD_ALIGNMENT_TOLERANCE = 1e-6
"""4.1: |t / 0.1 - round(t / 0.1)| of every command row."""
CLEARANCE_TARGET_BASE_M = 0.05
FLAT_SOIL_MARGIN_M = 0.03
CLEARANCE_TOLERANCE_M = 1e-12
END_WINDOW_S = 1.0
END_CRAWLER_LIMIT_N = 0.0
WINDOW_EDGE_TOLERANCE_S = 1e-9
"""Same edge tolerance as run_S9 ``P3B_END_WINDOW_S`` windows."""
GAP_FLAG_LIMIT_M = 0.025
CORNER_FLAG_EXTRA_M = 0.005
STROKE_INCREASE_LIMIT_M = 0.001
FORCE_FLOOR_N = 10414.589

C2_CHECK_KEYS = (
    "P3-1_crawler_zero_after_ready",
    "P3-1_recontact_pass",
    "P3-2_within",
    "P3-3_within",
    "P3-4_within_0p2",
    "P3-5_within",
    "P3-6_within",
    "P3-7_within",
    "P3-8_within",
)
Q_C2_FORCE_DELTA_N = 5000.0
"""6.1 Q-C2: |F_min delta| <= 5 kN when the minimum after the departure is after the LOC."""
P3_KEYS = ("P3-1_crawler_zero_after_ready", "P3-1_recontact_pass", "P3-5_within")
E6_GRADED_ITEMS = ("E-6a", "E-6b", "E-6c", "E-6d")

READY_PHASE = "ready"
LOC_EVENT = "crawler_liftoff_confirmed"
SOIL_MODE_EVENT = "soil_mode_start"
MARGIN_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN"
MARGIN_SKIPPED_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED"
MARGIN_80_EVENT_FULL = "INFO_LOC_FLAT_SOIL_MARGIN:80"
MARGIN_SKIPPED_EVENT_FULL = "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order"
NEW_EVENT_PREFIXES = ("FAULT_", "WARN_")

STATUS_PASS, STATUS_FAIL, STATUS_STOP = "pass", "fail", "stop"
STATUS_K1_INACTIVE, STATUS_INCOMPLETE, STATUS_ERROR = "k1_inactive", "incomplete", "error"
EXIT_CODES = {
    STATUS_PASS: 0,
    STATUS_FAIL: 1,
    STATUS_STOP: 2,
    STATUS_K1_INACTIVE: 2,
    STATUS_INCOMPLETE: 3,
    STATUS_ERROR: 3,
}
GRADE_WORDS = {
    STATUS_PASS: "통과",
    STATUS_FAIL: "미달",
    STATUS_STOP: "stop",
    STATUS_K1_INACTIVE: "K1 미작동(정보)",
    STATUS_INCOMPLETE: "incomplete",
    STATUS_ERROR: "error",
}
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
    """Plan 0 / rules 5.0.2: whole control periods ``round(t / 0.1)``."""
    return None if t_s is None else round(float(t_s) / PERIOD_S)


def event_base_name(name: str) -> str:
    """rev1 R1-5 2: the event name before ``:`` (counted by exact match)."""
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


def as_bool_or_none(value: Any) -> bool | None:
    """True / False for a JSON boolean, None for anything else (absent included)."""
    return value if isinstance(value, bool) else None


def scalar(value: Any) -> Any:
    """A one-element argparse list read as its element."""
    if isinstance(value, (list, tuple)) and len(value) == 1:
        return value[0]
    return value


def check(check_id: str, ok: bool, **detail: Any) -> dict[str, Any]:
    return {"id": check_id, "ok": bool(ok), **detail}


def plain(value: Any) -> Any:
    """JSON-ready copy (numpy scalars and arrays, MISSING)."""
    if value is MISSING:
        return "<missing>"
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return plain(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


# ================================================================ git queries (read only)
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
    """2.3 (1): ``git rev-parse HEAD``."""
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
    """The changed paths behind a false :func:`git_diff_is_empty` (record only)."""
    result = run_git(root, "diff", "--name-only", base, head, "--", *CODE_DIFF_PATHS)
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.decode("utf-8", "replace").splitlines() if line]


def code_diff_record(root: Path, head_sha: str | None) -> dict[str, Any]:
    """2.3 (2) / K-0a: the code diff between :data:`BASE_COMMIT` and ``head_sha``."""
    if head_sha is None:
        return {"base": BASE_COMMIT, "head": None, "quiet": None, "changed_paths": None}
    quiet = git_diff_is_empty(root, BASE_COMMIT, head_sha)
    changed = None if quiet is not False else git_diff_names(root, BASE_COMMIT, head_sha)
    return {
        "base": BASE_COMMIT,
        "head": head_sha,
        "paths": list(CODE_DIFF_PATHS),
        "quiet": quiet,
        "changed_paths": changed,
    }


def porcelain_path(line: str) -> str:
    """Path of one ``--porcelain=v1`` line (the new name of a rename)."""
    path = line[3:]
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    return path.strip().strip('"')


def status_record(root: Path) -> dict[str, Any]:
    """2.3 (3): ``git status --porcelain=v1`` of the code paths against :data:`ALLOWED_DIRTY`."""
    result = run_git(root, "status", "--porcelain=v1", "--", *CODE_DIFF_PATHS)
    if result.returncode != 0:
        return {"lines": None, "unexpected": None, "ok": False, "error": result.error}
    lines = [
        ln.rstrip() for ln in result.stdout.decode("utf-8", "replace").splitlines() if ln.strip()
    ]
    unexpected = [ln for ln in lines if porcelain_path(ln) not in ALLOWED_DIRTY]
    return {
        "lines": lines,
        "allowed": sorted(ALLOWED_DIRTY),
        "unexpected": unexpected,
        "ok": not unexpected,
        "error": None,
    }


def blob_sha256(root: Path, head_sha: str | None, path: str) -> str | None:
    """sha256 of ``git show <head>:<path>`` (the LF blob, no filters)."""
    if head_sha is None:
        return None
    result = run_git(root, "show", f"{head_sha}:{path}")
    return sha256_bytes(result.stdout) if result.returncode == 0 else None


# ================================================================ prelaunch / postrun (plan 2.3)
def code_file_records(root: Path, head_sha: str | None) -> list[dict[str, Any]]:
    """2.3 (4): work-tree raw sha256 (= 2.1 CRLF column) and the HEAD blob sha256 (= LF column)."""
    records = []
    for sealed in CODE_FILES:
        worktree = sha256_file(root / sealed.path)
        blob = blob_sha256(root, head_sha, sealed.path)
        worktree_ok = worktree == sealed.worktree_crlf_sha256
        blob_ok = blob == sealed.blob_lf_sha256
        records.append(
            {
                "path": sealed.path,
                "worktree_sha256": worktree,
                "expected_worktree_crlf": sealed.worktree_crlf_sha256,
                "worktree_ok": worktree_ok,
                "blob_sha256": blob,
                "expected_blob_lf": sealed.blob_lf_sha256,
                "blob_ok": blob_ok,
                "ok": worktree_ok and blob_ok,
            }
        )
    return records


def dll_record(root: Path) -> dict[str, Any]:
    """2.3 (5): the hull hook DLL sha256 against the validated build."""
    path = root / DLL_PATH
    digest = sha256_file(path)
    return {
        "path": DLL_PATH,
        "sha256": digest,
        "expected": DLL_SHA256,
        "size_B": path.stat().st_size if path.is_file() else None,
        "ok": digest == DLL_SHA256,
    }


def sealed_rules_record(root: Path) -> dict[str, Any]:
    """2.3 (6) / K-0j: raw sha256 of the original rules, rev1 and the plan."""
    files = {}
    for name, expected in SEALED_RULES.items():
        digest = sha256_file(root / RULES_DIR_RELATIVE / name)
        files[name] = {"sha256": digest, "expected": expected, "ok": digest == expected}
    return {"files": files, "ok": all(f["ok"] for f in files.values())}


def identity_snapshot(root: Path, kind: str) -> dict[str, Any]:
    """Plan 2.3 items (1)-(6) at this moment, with one boolean per item."""
    head = git_head(root)
    items = {
        "head": head,
        "code_diff": code_diff_record(root, head["sha"]),
        "git_status": status_record(root),
        "code_files": code_file_records(root, head["sha"]),
        "dll": dll_record(root),
        "sealed_rules": sealed_rules_record(root),
    }
    checks = {
        "(1) head": head["ok"],
        "(2) code_diff_empty": items["code_diff"]["quiet"] is True,
        "(3) status_allowed": items["git_status"]["ok"],
        "(4) code_files": all(r["ok"] for r in items["code_files"]),
        "(5) dll": items["dll"]["ok"],
        "(6) sealed_rules": items["sealed_rules"]["ok"],
    }
    return {
        "kind": kind,
        "tool": tool_record(),
        "taken_utc": utc_now(),
        "root": root.as_posix(),
        "plan_sha256": dict(PLAN_SHA256_BY_FILE),
        **items,
        "checks": checks,
        "argv_check": "not part of prelaunch: building the rows needs run_S9 (not imported); "
        "the row argv difference is K-0g of judge (batch.json argv, result.json args)",
        "all_ok": all(checks.values()),
    }


def snapshot_fingerprint(snapshot: dict[str, Any]) -> dict[str, Any]:
    """The values of items (1)-(5) that postrun must repeat (no time stamps)."""
    return {
        "(1) head": dig(snapshot, "head", "sha"),
        "(2) code_diff": [
            dig(snapshot, "code_diff", "quiet"),
            dig(snapshot, "code_diff", "changed_paths"),
        ],
        "(3) status": dig(snapshot, "git_status", "lines"),
        "(4) code_files": {
            r.get("path"): [r.get("worktree_sha256"), r.get("blob_sha256")]
            for r in (snapshot.get("code_files") or [])
            if isinstance(r, dict)
        },
        "(5) dll": dig(snapshot, "dll", "sha256"),
    }


def snapshot_differences(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    """Items (1)-(5) whose values differ between two snapshots."""
    first, second = snapshot_fingerprint(before), snapshot_fingerprint(after)
    return [
        {"item": key, "prelaunch": plain(first[key]), "postrun": plain(second[key])}
        for key in first
        if first[key] != second[key]
    ]


def postrun_snapshot(root: Path, prelaunch_path: Path) -> dict[str, Any]:
    """Postrun record: the same items plus the differences to the prelaunch record."""
    snapshot = identity_snapshot(root, "postrun")
    snapshot["prelaunch_path"] = prelaunch_path.as_posix()
    prelaunch = read_json(prelaunch_path)
    if prelaunch is None:
        snapshot["prelaunch_found"] = False
        snapshot["differences_to_prelaunch"] = None
        snapshot["checks"]["same_as_prelaunch"] = False
    else:
        snapshot["prelaunch_found"] = True
        snapshot["prelaunch_sha256"] = sha256_file(prelaunch_path)
        differences = snapshot_differences(prelaunch, snapshot)
        snapshot["differences_to_prelaunch"] = differences
        snapshot["checks"]["same_as_prelaunch"] = not differences
    snapshot["all_ok"] = all(snapshot["checks"].values())
    return snapshot


# ================================================================ judge inputs
def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


@dataclass
class RowData:
    """One batch row: its result.json, the needed npz arrays and its batch.json entry."""

    case: str
    gate: str
    result: dict[str, Any]
    step: dict[str, np.ndarray]
    commands: dict[str, np.ndarray]
    entry: dict[str, Any]


REQUIRED_BLOCKS = (
    ("code_state",),
    ("p3b",),
    ("p3b", "checks"),
    ("p3b", "departure"),
    ("p3b", "P3-1_crawler", "recontact_events"),
    ("p3b_ext", "crawler_gap"),
    ("controller_meta", "slope_clearance_margin"),
    ("controller_meta", "slope_clearance_margin", "order_gate"),
    ("controller_meta", "slope_clearance_margin", "order_gate", "decisions"),
    ("hull_hook",),
    ("args",),
    ("phases",),
    ("events",),
)
"""5 judge input check: absent or ``{"error": ...}`` -> incomplete."""
STEP_KEYS = ("t_s", "scm_crawler_normal_N")
COMMAND_KEYS = ("t_s", "issued_u_m_s")


def block_problems(result: dict[str, Any]) -> list[str]:
    problems = []
    for path in REQUIRED_BLOCKS:
        value = dig(result, *path)
        name = ".".join(path)
        if value is MISSING or value is None:
            problems.append(f"{name}: missing")
        elif is_error_block(value):
            problems.append(f"{name}: {value['error']}")
    return problems


def load_npz(path: Path, keys: tuple[str, ...]) -> tuple[dict[str, np.ndarray], list[str]]:
    with np.load(path, allow_pickle=False) as data:
        missing = [k for k in keys if k not in data.files]
        arrays = {k: np.asarray(data[k]) for k in data.files if k in (*keys, "scm_crawler_patches")}
    return arrays, missing


def load_row(batch_dir: Path, case: str, entry: dict[str, Any]) -> tuple[RowData | None, list[str]]:
    """The row's files, or the reasons it is incomplete."""
    folder = batch_dir / case
    missing_files = [name for name in ROW_FILES if not (folder / name).is_file()]
    if missing_files:
        return None, [f"{case}: missing {name}" for name in missing_files]
    result = read_json(folder / "result.json")
    if result is None:
        return None, [f"{case}: result.json unreadable"]
    problems = [f"{case}: {p}" for p in block_problems(result)]
    try:
        step, missing_step = load_npz(folder / "step_series.npz", STEP_KEYS)
        commands, missing_commands = load_npz(folder / "controller_commands.npz", COMMAND_KEYS)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        return None, [*problems, f"{case}: npz unreadable ({type(error).__name__}: {error})"]
    problems += [f"{case}: step_series.npz has no {k}" for k in missing_step]
    problems += [f"{case}: controller_commands.npz has no {k}" for k in missing_commands]
    if problems:
        return None, problems
    return RowData(case, GATE_OF_CASE[case], result, step, commands, entry), []


def progress_counts(batch_dir: Path) -> dict[str, Any]:
    """5: START / END / RESUME_SKIP / SKIP / MIXED_HULL_MODE lines of progress.log."""
    path = batch_dir / "progress.log"
    if not path.is_file():
        return {"found": False}
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    counts = {
        token: sum(1 for ln in lines if ln.split(" ", 1)[0] == token) for token in PROGRESS_TOKENS
    }
    return {"found": True, "sha256": sha256_file(path), **counts}


def rerun_record(batch_dir: Path) -> dict[str, Any]:
    """6 SC-2: whether a first attempt was kept in ``<case>/attempt1/``."""
    out = {}
    for case in GATE_OF_CASE:
        folder = batch_dir / case / RERUN_FOLDER
        out[case] = {
            "attempt1_folder": folder.is_dir(),
            "attempt1_result_json": (folder / "result.json").is_file(),
        }
    return out


def batch_structure_problems(batch: dict[str, Any]) -> list[str]:
    """5 / lesson 1: exactly the two rows of 1.1, pointing at each other (else stop)."""
    entries = batch.get("cases")
    if not isinstance(entries, list):
        return ["batch.json has no cases list"]
    names = [e.get("case") for e in entries if isinstance(e, dict)]
    problems = []
    if sorted(names) != sorted(GATE_OF_CASE):
        problems.append(f"batch rows {sorted(map(str, names))} != {sorted(GATE_OF_CASE)}")
        return problems
    by_case = {e["case"]: e for e in entries}
    if by_case[CASE_GATEOFF].get("pair_case") != CASE_GATEON:
        problems.append(f"{CASE_GATEOFF}.pair_case = {by_case[CASE_GATEOFF].get('pair_case')!r}")
    if by_case[CASE_GATEON].get("pair_case") != CASE_GATEOFF:
        problems.append(f"{CASE_GATEON}.pair_case = {by_case[CASE_GATEON].get('pair_case')!r}")
    return problems


def row_labels(batch: dict[str, Any]) -> dict[str, Any]:
    """Lesson 5: ``las_candidate`` / ``k1_candidate`` / ``k1_order_gate`` per row (record)."""
    labels = {}
    for entry in batch.get("cases") or []:
        if isinstance(entry, dict):
            labels[str(entry.get("case"))] = {
                k: entry.get(k) for k in ("las_candidate", "k1_candidate", "k1_order_gate")
            }
    return labels


def files_read(batch_dir: Path, extra: list[Path]) -> dict[str, str | None]:
    paths = [batch_dir / "batch.json", batch_dir / "progress.log"]
    for case in GATE_OF_CASE:
        paths += [batch_dir / case / name for name in ROW_FILES]
    return {p.as_posix(): sha256_file(p) for p in [*paths, *extra]}


# ================================================================ K-0 identity (plan 2.2)
def row_head(row: RowData) -> tuple[str | None, str]:
    """K-0a source: result.json ``git_at_start.head``, else batch.json
    ``code_at_launch.git.head``."""
    head = dig(row.result, "code_state", "git_at_start", "head")
    if isinstance(head, str) and head:
        return head, "result.json code_state.git_at_start.head"
    head = dig(row.entry, "code_at_launch", "git", "head")
    if isinstance(head, str) and head:
        return head, "batch.json code_at_launch.git.head (git_at_start unusable)"
    return None, "none"


def row_dirty(row: RowData) -> tuple[Any, str]:
    """K-0b source with the same fallback as K-0a (lesson 3)."""
    dirty = dig(row.result, "code_state", "git_at_start", "dirty")
    if isinstance(dirty, list):
        return dirty, "result.json code_state.git_at_start.dirty"
    dirty = dig(row.entry, "code_at_launch", "git", "dirty")
    if isinstance(dirty, list):
        return dirty, "batch.json code_at_launch.git.dirty (git_at_start unusable)"
    return MISSING, "none"


def check_k0a(rows: list[RowData], root: Path) -> dict[str, Any]:
    heads = {row.case: row_head(row) for row in rows}
    values = {head for head, _ in heads.values()}
    same = len(values) == 1 and None not in values
    head = next(iter(values)) if same else None
    diff_empty = git_diff_is_empty(root, BASE_COMMIT, head) if head else None
    return check(
        "K-0a",
        same and diff_empty is True,
        heads={case: {"head": h, "source": s} for case, (h, s) in heads.items()},
        code_diff_empty=diff_empty,
        base=BASE_COMMIT,
    )


def check_k0b(rows: list[RowData]) -> dict[str, Any]:
    dirty = {row.case: row_dirty(row) for row in rows}
    ok = all(value == [] for value, _ in dirty.values())
    return check(
        "K-0b", ok, dirty={c: {"dirty": plain(v), "source": s} for c, (v, s) in dirty.items()}
    )


def check_k0c(rows: list[RowData]) -> dict[str, Any]:
    found = []
    for row in rows:
        for module, path in RECORDED_CONTROLLER_FILES:
            expected = CRLF_SHA256_BY_PATH[path]
            in_result = dig(row.result, "code_state", "files_at_start", module, "sha256")
            in_batch = dig(row.entry, "code_at_launch", "files", path)
            found.append(
                {
                    "case": row.case,
                    "path": path,
                    "expected_crlf": expected,
                    "result_json": plain(in_result),
                    "batch_json": plain(in_batch),
                    "ok": in_result == expected and in_batch == expected,
                }
            )
    return check("K-0c", all(f["ok"] for f in found), files=found)


def check_k0d(prelaunch_path: Path, postrun_path: Path) -> dict[str, Any]:
    prelaunch, postrun = read_json(prelaunch_path), read_json(postrun_path)
    detail: dict[str, Any] = {
        "prelaunch": prelaunch_path.as_posix(),
        "postrun": postrun_path.as_posix(),
        "prelaunch_found": prelaunch is not None,
        "postrun_found": postrun is not None,
    }
    if prelaunch is None or postrun is None:
        return check("K-0d", False, **detail)
    differences = snapshot_differences(prelaunch, postrun)
    detail.update(
        prelaunch_all_ok=prelaunch.get("all_ok") is True,
        postrun_all_ok=postrun.get("all_ok") is True,
        prelaunch_taken_utc=prelaunch.get("taken_utc"),
        postrun_taken_utc=postrun.get("taken_utc"),
        prelaunch_head=dig(prelaunch, "head", "sha"),
        differences=differences,
        prelaunch_sha256=sha256_file(prelaunch_path),
        postrun_sha256=sha256_file(postrun_path),
    )
    ok = detail["prelaunch_all_ok"] and detail["postrun_all_ok"] and not differences
    return check("K-0d", ok, **detail)


def check_k0e(rows: list[RowData], batch: dict[str, Any]) -> dict[str, Any]:
    per_row = []
    for row in rows:
        hull = row.result.get("hull_hook") or {}
        values = {
            "mode": hull.get("mode"),
            "requested": hull.get("requested"),
            "fallback_reason": hull.get("fallback_reason"),
            "dll_sha256": hull.get("dll_sha256"),
            "dll_sha_validated": hull.get("dll_sha_validated"),
            "batch_hull_hook_requested": row.entry.get("hull_hook_requested"),
            "batch_hull_hook_effective_mode": dig(row.entry, "hull_hook_effective", "mode"),
        }
        ok = (
            values["mode"] == "fast"
            and values["requested"] == "fast"
            and values["fallback_reason"] is None
            and values["dll_sha256"] == DLL_SHA256
            and values["dll_sha_validated"] is True
            and values["batch_hull_hook_requested"] == "fast"
            and values["batch_hull_hook_effective_mode"] == "fast"
        )
        per_row.append({"case": row.case, **plain(values), "ok": ok})
    mixed = batch.get("mixed_hull_mode")
    return check(
        "K-0e",
        all(r["ok"] for r in per_row) and mixed is False,
        rows=per_row,
        mixed_hull_mode=mixed,
    )


def check_k0f(rows: list[RowData]) -> dict[str, Any]:
    per_row = []
    for row in rows:
        placement = row.result.get("placement") or {}
        values = {
            "args.threads": scalar(dig(row.result, "args", "threads")),
            "num_threads_chrono": row.result.get("num_threads_chrono"),
            "batch.omp_wait_policy": row.entry.get("omp_wait_policy"),
            "batch.pool": row.entry.get("pool"),
            "placement.mode": placement.get("mode"),
            "placement.affinity_ok": placement.get("affinity_ok"),
            "placement.power_throttling_off_ok": placement.get("power_throttling_off_ok"),
        }
        ok = (
            values["args.threads"] == THREADS
            and values["num_threads_chrono"] == THREADS
            and values["batch.omp_wait_policy"] == "PASSIVE"
            and values["batch.pool"] == "pcore"
            and values["placement.mode"] == "pcore"
            and values["placement.affinity_ok"] is True
            and values["placement.power_throttling_off_ok"] is True
        )
        per_row.append({"case": row.case, **plain(values), "ok": ok})
    return check("K-0f", all(r["ok"] for r in per_row), rows=per_row)


def differing_arg_keys(first: dict[str, Any], second: dict[str, Any]) -> list[str]:
    keys = set(first) | set(second)
    return sorted(
        k for k in keys if scalar(first.get(k, MISSING)) != scalar(second.get(k, MISSING))
    )


def argv_difference_ok(off_argv: Any, on_argv: Any) -> tuple[bool, list[dict[str, Any]]]:
    """K-0g on batch.json ``argv``: same length, differences only in the value of
    ``--k1-order-gate`` (``off`` / ``on``) or ``--case``, and the gate value does differ."""
    if (
        not isinstance(off_argv, list)
        or not isinstance(on_argv, list)
        or len(off_argv) != len(on_argv)
    ):
        return False, [{"reason": "argv missing or of different length"}]
    differences = []
    is_gate_different = False
    for i, (a, b) in enumerate(zip(off_argv, on_argv, strict=True)):
        if a == b:
            continue
        option = off_argv[i - 1] if i > 0 else None
        differences.append({"index": i, "option": option, "gateoff": a, "gateon": b})
        if option == "--k1-order-gate" and (a, b) == ("off", "on"):
            is_gate_different = True
    is_allowed = all(d["option"] in VALUE_OPTIONS_ALLOWED_TO_DIFFER for d in differences)
    return is_allowed and is_gate_different, differences


def check_k0g(off: RowData, on: RowData) -> dict[str, Any]:
    off_args, on_args = off.result.get("args") or {}, on.result.get("args") or {}
    differing = differing_arg_keys(off_args, on_args)
    gates_ok = (
        scalar(off_args.get("k1_order_gate")) == "off"
        and scalar(on_args.get("k1_order_gate")) == "on"
    )
    expected_values = []
    for row, args in ((off, off_args), (on, on_args)):
        for key, want in EXPECTED_ARGS.items():
            got = scalar(args.get(key, MISSING))
            expected_values.append(
                {"case": row.case, "key": key, "want": want, "got": plain(got), "ok": got == want}
            )
    argv_ok, argv_differences = argv_difference_ok(off.entry.get("argv"), on.entry.get("argv"))
    ok = (
        set(differing) == ALLOWED_ARG_DIFFERENCES
        and gates_ok
        and argv_ok
        and all(v["ok"] for v in expected_values)
    )
    return check(
        "K-0g",
        ok,
        args_differing_keys=differing,
        gates_ok=gates_ok,
        argv_ok=argv_ok,
        argv_differences=plain(argv_differences),
        expected_values=expected_values,
    )


def check_k0h(rows: list[RowData]) -> dict[str, Any]:
    per_row = []
    for row in rows:
        values = {
            "controller_tag": dig(row.result, "v5_hydraulics", "controller_tag"),
            "expect_controller_ok": dig(row.result, "c2_setup", "expect_controller", "ok"),
            "c2_setup_k1_order_gate": dig(row.result, "c2_setup", "k1_order_gate"),
        }
        ok = (
            values["controller_tag"] == CONTROLLER_TAG
            and values["expect_controller_ok"] is True
            and values["c2_setup_k1_order_gate"] == row.gate
        )
        per_row.append({"case": row.case, **plain(values), "ok": ok})
    return check("K-0h", all(r["ok"] for r in per_row), rows=per_row)


def check_k0i(rows: list[RowData], batch: dict[str, Any]) -> dict[str, Any]:
    rcs = {row.case: row.entry.get("rc") for row in rows}
    failed = batch.get("failed")
    ok = all(rc == 0 for rc in rcs.values()) and failed is False
    return check("K-0i", ok, rc=rcs, batch_failed=failed)


def check_k0j(root: Path) -> dict[str, Any]:
    record = sealed_rules_record(root)
    return check("K-0j", record["ok"], files=record["files"])


def check_k0k(prelaunch_path: Path, postrun_path: Path) -> dict[str, Any]:
    """Plan rev1 R1-3: tool sha256 of prelaunch = postrun = this judging tool; a missing
    record is false."""
    recorded = {
        "prelaunch": dig(read_json(prelaunch_path), "tool", "sha256"),
        "postrun": dig(read_json(postrun_path), "tool", "sha256"),
        "judge": sha256_file(TOOL_PATH),
    }
    values = set(recorded.values())
    is_complete = all(isinstance(v, str) and v for v in recorded.values())
    return check("K-0k", is_complete and len(values) == 1, tool_sha256=plain(recorded))


def identity_checks(
    off: RowData,
    on: RowData,
    batch: dict[str, Any],
    root: Path,
    prelaunch_path: Path,
    postrun_path: Path,
) -> list[dict[str, Any]]:
    rows = [off, on]
    return [
        check_k0a(rows, root),
        check_k0b(rows),
        check_k0c(rows),
        check_k0d(prelaunch_path, postrun_path),
        check_k0e(rows, batch),
        check_k0f(rows),
        check_k0g(off, on),
        check_k0h(rows),
        check_k0i(rows, batch),
        check_k0j(root),
        check_k0k(prelaunch_path, postrun_path),
    ]


# ================================================================ K1 activity, structure (plan 3)
def margin_meta(row: RowData) -> dict[str, Any]:
    return row.result["controller_meta"]["slope_clearance_margin"]


def decisions_of(row: RowData) -> list[dict[str, Any]]:
    return list(margin_meta(row)["order_gate"]["decisions"])


def event_list(row: RowData) -> list[tuple[float, str]]:
    return [(float(e["t_s"]), str(e["name"])) for e in row.result["events"]]


def count_base_events(row: RowData, base_name: str) -> int:
    return sum(1 for _, name in event_list(row) if event_base_name(name) == base_name)


def count_full_events(row: RowData, full_name: str) -> int:
    return sum(1 for _, name in event_list(row) if name == full_name)


def first_event_time(row: RowData, base_name: str) -> float | None:
    return next((t for t, name in event_list(row) if event_base_name(name) == base_name), None)


def phase_list(row: RowData) -> list[tuple[float, str]]:
    return [(float(p["t_s"]), str(p["phase"])) for p in row.result["phases"]]


def first_ready_time(row: RowData) -> float | None:
    return next((t for t, phase in phase_list(row) if phase == READY_PHASE), None)


def last_phase(row: RowData) -> str | None:
    phases = phase_list(row)
    return phases[-1][1] if phases else None


def k1_activity(off: RowData) -> dict[str, Any]:
    """3.2: the K1 active LOC = the first gateoff decision with ``r4_due_without_gate`` and
    ``would_block``; otherwise the reason K1 is inactive."""
    decisions = decisions_of(off)
    active = next(
        (
            d
            for d in decisions
            if d.get("r4_due_without_gate") is True and d.get("would_block") is True
        ),
        None,
    )
    record: dict[str, Any] = {"active": active is not None, "n_decisions": len(decisions)}
    if active is not None:
        record.update(
            decision=plain(active),
            t_loc_s=active.get("t_loc_s"),
            n_loc=period_of(active.get("t_loc_s")),
        )
        return record
    if not decisions:
        reason = "decisions empty"
        record["empty_detail"] = {
            "soil_mode_start_events": count_base_events(off, SOIL_MODE_EVENT),
            "loc_events": count_base_events(off, LOC_EVENT),
            "slope_margin_E3c10_applied": margin_meta(off).get("is_applied"),
        }
    elif not any(d.get("r4_due_without_gate") is True for d in decisions):
        reason = "no decision with r4_due_without_gate"
    else:
        reason = "every r4_due decision has would_block false (n_P > n_S)"
    record["inactive_reason"] = reason
    return record


def check_ks1(off: RowData, on: RowData) -> dict[str, Any]:
    values = {
        row.case: {
            "order_gate.enabled": margin_meta(row)["order_gate"].get("enabled"),
            "c2_setup.k1_order_gate": dig(row.result, "c2_setup", "k1_order_gate"),
        }
        for row in (off, on)
    }
    ok = (
        values[off.case]["order_gate.enabled"] is False
        and values[on.case]["order_gate.enabled"] is True
        and values[off.case]["c2_setup.k1_order_gate"] == "off"
        and values[on.case]["c2_setup.k1_order_gate"] == "on"
    )
    return check("K-S1", ok, values=plain(values))


def applied_count(row: RowData) -> int:
    return sum(1 for d in decisions_of(row) if d.get("applied") is True)


def check_ks2(off: RowData) -> dict[str, Any]:
    decisions = decisions_of(off)
    rule_ok = all(d.get("applied") is d.get("r4_due_without_gate") for d in decisions)
    skipped = count_base_events(off, MARGIN_SKIPPED_EVENT)
    margins = count_base_events(off, MARGIN_EVENT)
    ok = rule_ok and skipped == 0 and margins == applied_count(off)
    return check(
        "K-S2",
        ok,
        applied_equals_r4_due=rule_ok,
        skipped_events=skipped,
        margin_events=margins,
        applied_true=applied_count(off),
    )


def check_ks3(on: RowData) -> dict[str, Any]:
    decisions = decisions_of(on)
    rule_ok = all(
        d.get("applied")
        is (d.get("r4_due_without_gate") is True and d.get("would_block") is not True)
        for d in decisions
    )
    blocked = sum(
        1
        for d in decisions
        if d.get("r4_due_without_gate") is True and d.get("would_block") is True
    )
    skipped = count_base_events(on, MARGIN_SKIPPED_EVENT)
    margins = count_base_events(on, MARGIN_EVENT)
    ok = rule_ok and skipped == blocked and margins == applied_count(on)
    return check(
        "K-S3",
        ok,
        applied_rule_ok=rule_ok,
        r4_due_and_would_block=blocked,
        skipped_events=skipped,
        margin_events=margins,
        applied_true=applied_count(on),
    )


def recomputed_decision(decision: dict[str, Any]) -> dict[str, Any]:
    """K-S4: n_P, n_S, dP and would_block from ``t_P_s`` / ``t_S_s``."""
    n_plateau, n_soil = period_of(decision.get("t_P_s")), period_of(decision.get("t_S_s"))
    has_both = n_plateau is not None and n_soil is not None
    is_blocked = n_plateau is None or n_soil is None or n_plateau <= n_soil
    return {
        "n_P": n_plateau,
        "n_S": n_soil,
        "dP": n_plateau - n_soil if has_both else None,
        "would_block": decision.get("r4_due_without_gate") is True and is_blocked,
    }


def check_ks4(off: RowData, on: RowData) -> dict[str, Any]:
    mismatches = []
    for row in (off, on):
        for index, decision in enumerate(decisions_of(row)):
            again = recomputed_decision(decision)
            different = {
                k: {"recorded": decision.get(k), "recomputed": v}
                for k, v in again.items()
                if decision.get(k) != v
            }
            if different:
                mismatches.append({"case": row.case, "index": index, "fields": different})
    return check("K-S4", not mismatches, mismatches=mismatches)


def check_ks5(off_decision: dict[str, Any], on: RowData, n_loc: int) -> dict[str, Any]:
    match = next((d for d in decisions_of(on) if period_of(d.get("t_loc_s")) == n_loc), None)
    if match is None:
        return check("K-S5", False, reason=f"gateon has no decision at period {n_loc}")
    same = match.get("t_P_s") == off_decision.get("t_P_s") and match.get(
        "t_S_s"
    ) == off_decision.get("t_S_s")
    return check("K-S5", same, gateon_decision=plain(match), gateoff_decision=plain(off_decision))


def expected_clearance_target(row: RowData) -> float:
    """K-S6: 0.08 m when any R4c30 decision applied, 0.05 m when every R4 LOC was blocked."""
    if applied_count(row) > 0:
        return CLEARANCE_TARGET_BASE_M + FLAT_SOIL_MARGIN_M
    return CLEARANCE_TARGET_BASE_M


def check_ks6(off: RowData, on: RowData) -> dict[str, Any]:
    rows = []
    for row in (off, on):
        got = margin_meta(row).get("clearance_target_m")
        want = expected_clearance_target(row)
        ok = isinstance(got, (int, float)) and abs(float(got) - want) <= CLEARANCE_TOLERANCE_M
        rows.append(
            {
                "case": row.case,
                "clearance_target_m": got,
                "expected_m": want,
                "ok": ok,
                "slope_margin_E3c10_applied": margin_meta(row).get("is_applied"),
            }
        )
    return check(
        "K-S6",
        all(r["ok"] for r in rows),
        rows=rows,
        gateoff_r4c30_applied=applied_count(off) > 0,
        gateon_late_r4c30_applied=applied_count(on) > 0,
    )


# ================================================================ commands (plan 4.1, K-4)
@dataclass(frozen=True)
class CommandSeries:
    t_s: np.ndarray
    u_m_s: np.ndarray
    periods: np.ndarray
    is_aligned: bool


def command_series(row: RowData) -> CommandSeries:
    t_s = np.ascontiguousarray(row.commands["t_s"], dtype="<f8")
    u_m_s = np.ascontiguousarray(row.commands["issued_u_m_s"], dtype="<f8")
    ratio = t_s / PERIOD_S
    periods = np.rint(ratio).astype(np.int64)
    is_aligned = bool(np.all(np.abs(ratio - periods) <= PERIOD_ALIGNMENT_TOLERANCE))
    return CommandSeries(t_s, u_m_s, periods, is_aligned)


def commands_sha256(t_s: np.ndarray, u_m_s: np.ndarray) -> str:
    """4.1: sha256 of ``t_s`` then ``issued_u_m_s`` as ``<f8`` C-contiguous bytes, file order."""
    t_bytes = np.ascontiguousarray(t_s, dtype="<f8").tobytes()
    u_bytes = np.ascontiguousarray(u_m_s, dtype="<f8").tobytes()
    return sha256_bytes(t_bytes + u_bytes)


def first_difference_period(off: CommandSeries, on: CommandSeries) -> int | None:
    """Record: the period of the first row where the two command files differ."""
    n_common = min(len(off.t_s), len(on.t_s))
    differs = off.t_s[:n_common] != on.t_s[:n_common]
    differs |= np.any(off.u_m_s[:n_common] != on.u_m_s[:n_common], axis=1)
    hits = np.flatnonzero(differs)
    if hits.size:
        return int(off.periods[hits[0]])
    if len(off.t_s) == len(on.t_s):
        return None
    longer = off if len(off.t_s) > len(on.t_s) else on
    return int(longer.periods[n_common])


def events_before(row: RowData, n_loc: int) -> list[tuple[str, int]]:
    return [(name, period_of(t)) for t, name in event_list(row) if period_of(t) < n_loc]


def check_command_prefix(off_row: RowData, on_row: RowData, n_loc: int) -> dict[str, Any]:
    """4.1 C-P (= K-S7): commands of the periods before ``n_loc`` are the same."""
    off, on = command_series(off_row), command_series(on_row)
    off_prefix, on_prefix = off.periods < n_loc, on.periods < n_loc
    off_hash = commands_sha256(off.t_s[off_prefix], off.u_m_s[off_prefix])
    on_hash = commands_sha256(on.t_s[on_prefix], on.u_m_s[on_prefix])
    n_off, n_on = int(off_prefix.sum()), int(on_prefix.sum())
    is_equal = (
        n_off == n_on
        and np.array_equal(off.t_s[off_prefix], on.t_s[on_prefix])
        and np.array_equal(off.u_m_s[off_prefix], on.u_m_s[on_prefix])
    )
    ok = (
        off.is_aligned
        and on.is_aligned
        and n_off == n_on
        and n_off >= 1
        and off_hash == on_hash
        and is_equal
    )
    k_diff = first_difference_period(off, on)
    loc_off, loc_on = off.periods == n_loc, on.periods == n_loc
    loc_equal = np.array_equal(off.t_s[loc_off], on.t_s[loc_on]) and np.array_equal(
        off.u_m_s[loc_off], on.u_m_s[loc_on]
    )
    return check(
        "K-S7",
        ok,
        n_loc=n_loc,
        periods_aligned={"gateoff": off.is_aligned, "gateon": on.is_aligned},
        prefix_rows={"gateoff": n_off, "gateon": n_on},
        prefix_sha256={"gateoff": off_hash, "gateon": on_hash},
        array_equal=is_equal,
        k_diff=k_diff,
        k_diff_minus_n_loc=None if k_diff is None else k_diff - n_loc,
        loc_period_commands_equal=loc_equal,
        full_sha256={
            "gateoff": commands_sha256(off.t_s, off.u_m_s),
            "gateon": commands_sha256(on.t_s, on.u_m_s),
        },
        events_before_n_loc_equal=events_before(off_row, n_loc) == events_before(on_row, n_loc),
    )


def check_all_commands_equal(off_row: RowData, on_row: RowData) -> dict[str, Any]:
    """3.2 K-4 type (K1 inactive): the whole command files are bit-identical."""
    off, on = command_series(off_row), command_series(on_row)
    off_hash, on_hash = commands_sha256(off.t_s, off.u_m_s), commands_sha256(on.t_s, on.u_m_s)
    is_equal = (
        off.t_s.shape == on.t_s.shape
        and off.u_m_s.shape == on.u_m_s.shape
        and np.array_equal(off.t_s, on.t_s)
        and np.array_equal(off.u_m_s, on.u_m_s)
    )
    return check(
        "K-4",
        is_equal and off_hash == on_hash,
        full_sha256={"gateoff": off_hash, "gateon": on_hash},
        rows={"gateoff": len(off.t_s), "gateon": len(on.t_s)},
        k_diff=first_difference_period(off, on),
    )


# ================================================================ E-6 type (plan 4.2)
def e6a_end_crawler(row: RowData) -> dict[str, Any]:
    """E-6a; an empty end window is ``missing`` (rev1 R1-5 / T-6), neither fail nor pass."""
    t_s = np.asarray(row.step["t_s"], dtype=float)
    crawler_n = np.asarray(row.step["scm_crawler_normal_N"], dtype=float)
    if t_s.size == 0 or crawler_n.size != t_s.size:
        return {
            "ok": False,
            "failed": False,
            "missing": "E-6a: empty step series",
            "window_max_N": None,
            "window_samples": 0,
        }
    t_end = float(t_s[-1])
    window = t_s >= t_end - END_WINDOW_S - WINDOW_EDGE_TOLERANCE_S
    if not window.any():
        return {
            "ok": False,
            "failed": False,
            "missing": "E-6a: empty end window",
            "window_max_N": None,
            "window_samples": 0,
        }
    window_max = float(crawler_n[window].max())
    patches = row.step.get("scm_crawler_patches")
    patches_max = float(np.asarray(patches)[window].max()) if patches is not None else None
    ok = window_max <= END_CRAWLER_LIMIT_N
    return {
        "ok": ok,
        "failed": not ok,
        "missing": None,
        "window_max_N": window_max,
        "end_N": float(crawler_n[-1]),
        "window_samples": int(window.sum()),
        "window_s": [t_end - END_WINDOW_S, t_end],
        "patches_max": patches_max,
    }


def e6b_end_gap(row: RowData, is_crawler_zero: bool) -> dict[str, Any]:
    gap = row.result["p3b_ext"]["crawler_gap"]
    grid_end = gap.get("grid_end_m")
    if not isinstance(grid_end, (int, float)) or not math.isfinite(float(grid_end)):
        # rev1 R1-5 / T-5: a missing judged value is incomplete, not an E-6b fail
        return {
            "ok": False,
            "failed": False,
            "missing": "E-6b: grid_end_m missing or not finite",
            "outcome": "no_value",
            "grid_end_m": plain(grid_end),
            "flag": None,
        }
    grid_end = float(grid_end)
    if grid_end >= GAP_FLAG_LIMIT_M:
        outcome, flag = "ge_25mm", None
    elif grid_end > 0.0:
        # rev1 R1-4.2 (I-8): with a crawler load the band is recorded only; E-6a carries the fail
        outcome = "flag" if is_crawler_zero else "below_25mm_with_crawler_load"
        flag = "E-6_post_event_clearance" if is_crawler_zero else None
    else:
        outcome, flag = "le_0", None
    failed = grid_end <= 0.0
    return {
        "ok": not failed,
        "failed": failed,
        "missing": None,
        "outcome": outcome,
        "grid_end_m": grid_end,
        "flag": flag,
    }


def e6b_corner_record(row: RowData) -> dict[str, Any]:
    """E-6b' (record): all-point end gap against the grid end gap minus the nearby sinkage."""
    gap = row.result["p3b_ext"]["crawler_gap"]
    end_all, grid_end = gap.get("end_m"), gap.get("grid_end_m")
    near = dig(row.result, "s9_rows", -1, "crawler_gap_point_near_sinkage_m")
    near_value = (
        float(near) if isinstance(near, (int, float)) and math.isfinite(float(near)) else 0.0
    )
    is_flagged = (
        isinstance(end_all, (int, float))
        and isinstance(grid_end, (int, float))
        and float(end_all) < float(grid_end) - (near_value + CORNER_FLAG_EXTRA_M)
    )
    return {
        "end_m": plain(end_all),
        "grid_end_m": plain(grid_end),
        "near_sinkage_m": plain(near),
        "near_sinkage_used_m": near_value,
        "flag": "SCh_end_corner_gap" if is_flagged else None,
    }


def e6c_recontact(row: RowData) -> dict[str, Any]:
    departure = row.result["p3b"]["departure"]
    events = row.result["p3b"]["P3-1_crawler"]["recontact_events"].get("events") or []
    has_departure = departure.get("departed") is True and departure.get("t_confirmed_s") is not None
    strict = sum(1 for e in events if e.get("class") == "strict_fail")
    ok = has_departure and strict == 0
    return {
        "ok": ok,
        "failed": not ok,
        "departed": departure.get("departed"),
        "t_confirmed_s": departure.get("t_confirmed_s"),
        "strict_fail": strict,
    }


def e6c_short_recontacts(row: RowData) -> dict[str, Any]:
    """E-6c' (FLAG record): transient and chatter recontacts."""
    events = row.result["p3b"]["P3-1_crawler"]["recontact_events"].get("events") or []
    listed = [
        {
            "class": e.get("class"),
            "t_start_s": e.get("t_start_s"),
            "duration_s": e.get("duration_s"),
            "max_normal_N": e.get("max_normal_N"),
        }
        for e in events
        if e.get("class") in ("transient_flag", "threshold_chatter")
    ]
    flags = []
    if any(e["class"] == "transient_flag" for e in listed):
        flags.append("P3-1_transient_recontact")
    if any(e["class"] == "threshold_chatter" for e in listed):
        flags.append("P3-1_threshold_chatter")
    return {
        "transient_flag": sum(1 for e in listed if e["class"] == "transient_flag"),
        "threshold_chatter": sum(1 for e in listed if e["class"] == "threshold_chatter"),
        "events": listed,
        "flags": flags,
    }


def e6d_ready(row: RowData) -> dict[str, Any]:
    has_ready = first_ready_time(row) is not None
    final = last_phase(row)
    ok = has_ready and final == READY_PHASE
    return {"ok": ok, "failed": not ok, "has_ready": has_ready, "last_phase": final}


def e6_row(row: RowData) -> dict[str, Any]:
    e6a = e6a_end_crawler(row)
    return {
        "E-6a": e6a,
        "E-6b": e6b_end_gap(row, e6a["ok"]),
        "E-6b'": e6b_corner_record(row),
        "E-6c": e6c_recontact(row),
        "E-6c'": e6c_short_recontacts(row),
        "E-6d": e6d_ready(row),
    }


def e6_grade(off: dict[str, Any], on: dict[str, Any]) -> dict[str, Any]:
    """4.2: gateon-only failure = fail; the same item failed in both rows = stop."""
    gateon_only = [i for i in E6_GRADED_ITEMS if on[i]["failed"] and not off[i]["failed"]]
    both = [i for i in E6_GRADED_ITEMS if on[i]["failed"] and off[i]["failed"]]
    gateoff_only = [i for i in E6_GRADED_ITEMS if off[i]["failed"] and not on[i]["failed"]]
    return {
        "gateon_only_failed": gateon_only,
        "both_failed": both,
        "gateoff_only_failed_record": gateoff_only,
    }


def e6_flags(e6: dict[str, Any]) -> list[str]:
    flags = [e6["E-6b"]["flag"], e6["E-6b'"]["flag"], *e6["E-6c'"]["flags"]]
    return [f for f in flags if f]


# ================================================================ pair comparison (plan 4.3)
def checks_of(row: RowData) -> dict[str, Any]:
    return row.result["p3b"]["checks"]


def c2_type(off: RowData, on: RowData) -> dict[str, Any]:
    """C-2 type with the rev1 R1-2 union rule on the nine ``p3b.checks`` booleans."""
    violations = []
    for key in C2_CHECK_KEYS:
        base, cand = (
            as_bool_or_none(checks_of(off).get(key)),
            as_bool_or_none(checks_of(on).get(key)),
        )
        if (base is not False and cand is False) or (base is True and cand is None):
            violations.append({"rule": "(a)", "item": key, "gateoff": base, "gateon": cand})
    if last_phase(off) == READY_PHASE and last_phase(on) != READY_PHASE:
        violations.append(
            {
                "rule": "(b)",
                "item": "last phase",
                "gateoff": last_phase(off),
                "gateon": last_phase(on),
            }
        )
    if first_ready_time(off) is not None and first_ready_time(on) is None:
        violations.append(
            {"rule": "(b)", "item": "first READY", "gateoff": first_ready_time(off), "gateon": None}
        )
    base_names = {event_base_name(n) for _, n in event_list(off)}
    new_names = sorted(
        {
            event_base_name(n)
            for _, n in event_list(on)
            if event_base_name(n).startswith(NEW_EVENT_PREFIXES)
        }
        - base_names
    )
    violations += [
        {"rule": "(c)", "item": name, "gateoff": None, "gateon": "new"} for name in new_names
    ]
    return {"violations": violations, "ok": not violations}


def p3_pairwise(off: RowData, on: RowData) -> dict[str, Any]:
    """P3 with the rev1 R1-1 pair rule."""
    violations, baseline_false, not_applicable = [], [], []
    for key in P3_KEYS:
        base, cand = (
            as_bool_or_none(checks_of(off).get(key)),
            as_bool_or_none(checks_of(on).get(key)),
        )
        # baseline true -> candidate false or None; baseline None -> candidate false
        is_worse = (base is True and cand is not True) or (base is None and cand is False)
        if is_worse:
            violations.append({"item": key, "gateoff": base, "gateon": cand})
        elif base is False:
            baseline_false.append(key)
        elif base is None and cand is None:
            not_applicable.append(key)
    return {
        "violations": violations,
        "P3_baseline_false": baseline_false,
        "not_applicable": not_applicable,
        "ok": not violations,
    }


def stroke_max_m(row: RowData) -> tuple[float | None, list[Any]]:
    per_leg = dig(row.result, "p3b", "P3-5_clearance_stroke", "s_motor_max_m")
    if not isinstance(per_leg, list) or not per_leg:
        return None, []
    return float(max(per_leg)), per_leg


def stroke_comparison(off: RowData, on: RowData) -> dict[str, Any]:
    """C-S: candidate - baseline maximum motor stroke <= 1 mm."""
    off_max, off_legs = stroke_max_m(off)
    on_max, on_legs = stroke_max_m(on)
    if off_max is None or on_max is None:
        # rev1 R1-5 / T-7: ok None = not judged (incomplete), not a fail
        return {
            "ok": None,
            "missing": "C-S: s_motor_max_m missing or empty",
            "gateoff_m": off_max,
            "gateon_m": on_max,
        }
    increase = on_max - off_max
    return {
        "ok": increase <= STROKE_INCREASE_LIMIT_M,
        "missing": None,
        "gateoff_m": off_max,
        "gateon_m": on_max,
        "increase_m": increase,
        "per_leg_m": {"gateoff": off_legs, "gateon": on_legs},
    }


def force_min_n(row: RowData) -> tuple[float | None, Any]:
    block = dig(row.result, "p3b", "P3-3_leg_force")
    per_leg = dig(block, "F_min_after_N")
    if not isinstance(per_leg, list) or not per_leg:
        return None, None
    leg = int(np.argmin(per_leg))
    times = dig(block, "t_min_after_s")
    t_min = times[leg] if isinstance(times, list) and len(times) > leg else None
    return float(per_leg[leg]), {"per_leg_N": per_leg, "leg_index": leg, "t_min_s": t_min}


def force_comparison(off: RowData, on: RowData) -> dict[str, Any]:
    """C-F: a baseline at or above the floor needs a candidate at or above it. A missing
    ``F_min_after_N`` in either row is ``missing`` (rev1 R1-5 / T-8); "not applicable" only
    for a baseline value below the floor."""
    off_min, off_detail = force_min_n(off)
    on_min, on_detail = force_min_n(on)
    detail = {
        "gateoff_N": off_min,
        "gateon_N": on_min,
        "floor_N": FORCE_FLOOR_N,
        "gateoff": off_detail,
        "gateon": on_detail,
        "note": "Chrono F_min_after_N (true cylinder force after the departure), "
        "not the harness F_judged_min_N",
    }
    if off_min is None or on_min is None:
        return {
            "ok": None,
            "applicable": None,
            "missing": "C-F: F_min_after_N missing or empty",
            **detail,
        }
    if off_min < FORCE_FLOOR_N:
        return {"ok": True, "applicable": False, "missing": None, **detail}
    return {"ok": on_min >= FORCE_FLOOR_N, "applicable": True, "missing": None, **detail}


def ready_delta(off: RowData, on: RowData) -> dict[str, Any]:
    t_off, t_on = first_ready_time(off), first_ready_time(on)
    if t_off is None or t_on is None:
        return {"gateoff_s": t_off, "gateon_s": t_on, "delta_s": None, "delta_periods": None}
    return {
        "gateoff_s": t_off,
        "gateon_s": t_on,
        "delta_s": t_on - t_off,
        "delta_periods": period_of(t_on) - period_of(t_off),
    }


def row_record(row: RowData) -> dict[str, Any]:
    """4.3 record row (no judgement)."""
    checks = checks_of(row)
    after_ready = dig(row.result, "p3b_ext", "crawler_gap", "after_first_ready")
    return plain(
        {
            "clearance_target_m": margin_meta(row).get("clearance_target_m"),
            "rut_clearance_min_after_first_ready_m": checks.get(
                "P3-5_rut_clearance_min_after_first_ready_m"
            ),
            "crawler_gap_after_first_ready_grid_min_m": dig(after_ready, "grid_min_m"),
            "crawler_gap_after_first_ready_all_min_m": dig(after_ready, "all_min_m"),
            "t_loc_s": first_event_time(row, LOC_EVENT),
            "t_soil_mode_start_s": first_event_time(row, SOIL_MODE_EVENT),
            "t_departure_s": dig(row.result, "p3b", "departure", "t_departure_s"),
            "P3-4_end_absmax_roll_pitch_deg": dig(
                row.result, "p3b", "P3-4_attitude", "end_absmax_roll_pitch_deg"
            ),
            "s_motor_max_m": stroke_max_m(row)[1],
            "flags": {
                "P3-1": checks.get("P3-1_flags"),
                "P3-2_verdict": checks.get("P3-2_verdict"),
                "P3-4": checks.get("P3-4_flags"),
            },
            "info_event_names": sorted(
                {
                    event_base_name(n)
                    for _, n in event_list(row)
                    if event_base_name(n).startswith("INFO_")
                }
            ),
        }
    )


def pair_comparison(off: RowData, on: RowData) -> dict[str, Any]:
    off_record, on_record = row_record(off), row_record(on)
    info_off, info_on = set(off_record["info_event_names"]), set(on_record["info_event_names"])
    return {
        "C-2": c2_type(off, on),
        "P3": p3_pairwise(off, on),
        "C-S": stroke_comparison(off, on),
        "C-F": force_comparison(off, on),
        "READY": ready_delta(off, on),
        "records": {
            "gateoff": off_record,
            "gateon": on_record,
            "info_only_gateoff": sorted(info_off - info_on),
            "info_only_gateon": sorted(info_on - info_off),
        },
    }


# ================================================================ predictions (plan 6.1, record)
def in_range(value: float | None, low: float, high: float) -> bool | None:
    return None if value is None else bool(low <= value <= high)


def prediction_item(name: str, value: Any, expected: str, is_inside: bool | None) -> dict[str, Any]:
    return {"item": name, "value": plain(value), "expected": expected, "inside": is_inside}


def predictions_q_c1(off: RowData, k1: dict[str, Any]) -> list[dict[str, Any]]:
    decision = k1.get("decision") or {}
    n_loc, n_soil = k1.get("n_loc"), decision.get("n_S")
    lead = None if n_loc is None or n_soil is None else n_loc - n_soil
    target = margin_meta(off).get("clearance_target_m")
    return [
        prediction_item(
            "soil_mode_start events",
            count_base_events(off, SOIL_MODE_EVENT),
            ">= 1",
            count_base_events(off, SOIL_MODE_EVENT) >= 1,
        ),
        prediction_item(
            "INFO_LOC_FLAT_SOIL_MARGIN:80 events",
            count_full_events(off, MARGIN_80_EVENT_FULL),
            "= 1",
            count_full_events(off, MARGIN_80_EVENT_FULL) == 1,
        ),
        prediction_item(
            "end clearance_target_m",
            target,
            "0.08",
            None if target is None else abs(target - 0.08) <= CLEARANCE_TOLERANCE_M,
        ),
        prediction_item(
            "K1 decision dP", decision.get("dP"), "[-12, -1]", in_range(decision.get("dP"), -12, -1)
        ),
        prediction_item(
            "K1 decision would_block",
            decision.get("would_block"),
            "true",
            decision.get("would_block") is True if decision else None,
        ),
        prediction_item("n_LOC - n_S (decision)", lead, "[1, 10]", in_range(lead, 1, 10)),
        prediction_item(
            "t_LOC [s]", k1.get("t_loc_s"), "[30, 40]", in_range(k1.get("t_loc_s"), 30.0, 40.0)
        ),
    ]


def predictions_q_c2(
    on: RowData, prefix: dict[str, Any] | None, pair: dict[str, Any], t_loc_s: float | None
) -> list[dict[str, Any]]:
    target = margin_meta(on).get("clearance_target_m")
    stroke, force = pair["C-S"], pair["C-F"]
    off_mm = None if stroke.get("gateoff_m") is None else stroke["gateoff_m"] * 1e3
    on_mm = None if stroke.get("gateon_m") is None else stroke["gateon_m"] * 1e3
    delta_mm = None if stroke.get("increase_m") is None else stroke["increase_m"] * 1e3
    k_lead = None if prefix is None else prefix.get("k_diff_minus_n_loc")
    return [
        prediction_item(
            "_SKIPPED:order events",
            count_full_events(on, MARGIN_SKIPPED_EVENT_FULL),
            "= 1",
            count_full_events(on, MARGIN_SKIPPED_EVENT_FULL) == 1,
        ),
        prediction_item(
            "INFO_LOC_FLAT_SOIL_MARGIN events",
            count_base_events(on, MARGIN_EVENT),
            "= 0",
            count_base_events(on, MARGIN_EVENT) == 0,
        ),
        prediction_item(
            "end clearance_target_m",
            target,
            "0.05",
            None if target is None else abs(target - 0.05) <= CLEARANCE_TOLERANCE_M,
        ),
        prediction_item(
            "C-P",
            None if prefix is None else prefix["ok"],
            "true",
            None if prefix is None else prefix["ok"],
        ),
        prediction_item("k_diff - n_LOC", k_lead, "[0, 5]", in_range(k_lead, 0, 5)),
        prediction_item("gateoff s_max [mm]", off_mm, "[480, 530]", in_range(off_mm, 480.0, 530.0)),
        prediction_item("gateon s_max [mm]", on_mm, "[450, 500]", in_range(on_mm, 450.0, 500.0)),
        prediction_item(
            "s_max delta [mm]", delta_mm, "[-35, -25]", in_range(delta_mm, -35.0, -25.0)
        ),
        prediction_item("C-S", stroke["ok"], "pass", stroke["ok"]),
        *force_predictions(force, t_loc_s),
    ]


def force_predictions(force: dict[str, Any], t_loc_s: float | None) -> list[dict[str, Any]]:
    off_n, on_n = force.get("gateoff_N"), force.get("gateon_N")
    both_above = (
        None if off_n is None or on_n is None else off_n >= FORCE_FLOOR_N and on_n >= FORCE_FLOOR_N
    )
    delta = None if off_n is None or on_n is None else on_n - off_n
    t_min = dig(force, "gateoff", "t_min_s")
    is_before_loc = None if t_min in (MISSING, None) or t_loc_s is None else t_min < t_loc_s
    if delta is None or is_before_loc is None:
        delta_inside = None
    elif is_before_loc:
        delta_inside = delta == 0.0
    else:
        delta_inside = abs(delta) <= Q_C2_FORCE_DELTA_N
    expected = "0 (minimum before the LOC)" if is_before_loc else "|delta| <= 5 kN"
    return [
        prediction_item("F_min both >= 10,414.589 N", both_above, "true", both_above),
        prediction_item("F_min delta [N]", delta, expected, delta_inside),
    ]


def predictions_q_c3(
    e6_off: dict[str, Any],
    e6_on: dict[str, Any],
    pair: dict[str, Any],
    off: RowData,
    on: RowData,
    status: str,
) -> list[dict[str, Any]]:
    on_gap, off_gap = e6_on["E-6b"]["grid_end_m"], e6_off["E-6b"]["grid_end_m"]
    gap_delta = (
        (on_gap - off_gap) if isinstance(on_gap, float) and isinstance(off_gap, float) else None
    )
    rut_on = row_record(on)["rut_clearance_min_after_first_ready_m"]
    rut_off = row_record(off)["rut_clearance_min_after_first_ready_m"]
    ready = pair["READY"]["delta_s"]

    def mm(value: Any) -> float | None:
        return float(value) * 1e3 if isinstance(value, (int, float)) else None

    return [
        prediction_item(
            "gateon E-6a end 1 s crawler max [N]",
            e6_on["E-6a"]["window_max_N"],
            "0.0",
            e6_on["E-6a"]["ok"],
        ),
        prediction_item(
            "gateon grid_end [mm]", mm(on_gap), "[30, 70]", in_range(mm(on_gap), 30.0, 70.0)
        ),
        prediction_item(
            "gateoff grid_end [mm]", mm(off_gap), "[60, 100]", in_range(mm(off_gap), 60.0, 100.0)
        ),
        prediction_item(
            "grid_end delta [mm]",
            mm(gap_delta),
            "[-35, -25]",
            in_range(mm(gap_delta), -35.0, -25.0),
        ),
        prediction_item(
            "gateon E-6c", e6_on["E-6c"]["ok"], "departed, strict_fail 0", e6_on["E-6c"]["ok"]
        ),
        prediction_item("gateon E-6d", e6_on["E-6d"]["last_phase"], "ready", e6_on["E-6d"]["ok"]),
        prediction_item(
            "gateon rut min after READY [mm]",
            mm(rut_on),
            "[35, 70]",
            in_range(mm(rut_on), 35.0, 70.0),
        ),
        prediction_item(
            "gateoff rut min after READY [mm]",
            mm(rut_off),
            "[65, 100]",
            in_range(mm(rut_off), 65.0, 100.0),
        ),
        prediction_item(
            "C-2 / P3 violations",
            len(pair["C-2"]["violations"]) + len(pair["P3"]["violations"]),
            "0",
            not pair["C-2"]["violations"] and not pair["P3"]["violations"],
        ),
        prediction_item("READY delta [s]", ready, "[-5, +2]", in_range(ready, -5.0, 2.0)),
        prediction_item("overall status", status, "pass", status == STATUS_PASS),
    ]


def prediction_table(
    k1: dict[str, Any],
    off: RowData,
    on: RowData,
    prefix: dict[str, Any] | None,
    e6: dict[str, Any],
    pair: dict[str, Any],
    status: str,
    all_commands: dict[str, Any] | None,
) -> dict[str, Any]:
    """6.1 Q-C1 .. Q-C4: inside / outside the predicted range (not a criterion)."""
    q_c4 = {
        "applies": not k1["active"],
        "predicted": "K1 active (Q-C1 holds)",
        "k1_active": k1["active"],
        "all_commands_equal": None if all_commands is None else all_commands["ok"],
    }
    return {
        "note": "predictions are not criteria (rules 5.0.1)",
        "Q-C1": predictions_q_c1(off, k1),
        "Q-C2": predictions_q_c2(on, prefix, pair, k1.get("t_loc_s")),
        "Q-C3": predictions_q_c3(e6["gateoff"], e6["gateon"], pair, off, on, status),
        "Q-C4": q_c4,
    }


# ================================================================ grading (plan 4.4)
def failed_ids(checks: list[dict[str, Any]]) -> list[str]:
    return [c["id"] for c in checks if not c["ok"]]


def fail_reasons_of(e6: dict[str, Any], pair: dict[str, Any]) -> list[str]:
    reasons = [f"E-6 gateon only: {item}" for item in e6["grade"]["gateon_only_failed"]]
    reasons += [f"C-2 {v['rule']}: {v['item']}" for v in pair["C-2"]["violations"]]
    reasons += [f"P3: {v['item']}" for v in pair["P3"]["violations"]]
    if pair["C-S"]["ok"] is False:
        reasons.append("C-S")
    if pair["C-F"]["ok"] is False:
        reasons.append("C-F")
    return reasons


def missing_values_of(e6: dict[str, Any], pair: dict[str, Any]) -> list[str]:
    """Rev1 R1-5: judged values that are absent in a row (E-6a window, E-6b, C-S, C-F)."""
    reasons = []
    for row_name in ("gateoff", "gateon"):
        for item in ("E-6a", "E-6b"):
            if e6[row_name][item].get("missing"):
                reasons.append(f"{row_name} {e6[row_name][item]['missing']}")
    reasons += [pair[item]["missing"] for item in ("C-S", "C-F") if pair[item].get("missing")]
    return reasons


def final_status(
    is_active: bool, stop_reasons: list[str], fail_reasons: list[str], missing: list[str]
) -> str:
    """4.4 with rev1 T-9: a K-0 / K-S / C-P stop wins; then a missing judged value gives
    incomplete (no fail can be issued without the value); then fail over the E-6 both-fail
    stop; an inactive K1 is info unless something stops."""
    if not is_active:
        return STATUS_STOP if stop_reasons else STATUS_K1_INACTIVE
    structural_stops = [r for r in stop_reasons if not r.startswith("E-6 both")]
    if missing:
        return STATUS_STOP if structural_stops else STATUS_INCOMPLETE
    if fail_reasons:
        return STATUS_FAIL
    return STATUS_STOP if stop_reasons else STATUS_PASS


def judge_rows(
    off: RowData,
    on: RowData,
    batch: dict[str, Any],
    root: Path,
    prelaunch_path: Path,
    postrun_path: Path,
) -> dict[str, Any]:
    """Plan 2-4 on the loaded pair."""
    identity = identity_checks(off, on, batch, root, prelaunch_path, postrun_path)
    k1 = k1_activity(off)
    structure = [check_ks1(off, on), check_ks2(off)]
    prefix = all_commands = None
    if k1["active"]:
        prefix = check_command_prefix(off, on, k1["n_loc"])
        structure += [
            check_ks3(on),
            check_ks4(off, on),
            check_ks5(k1["decision"], on, k1["n_loc"]),
            check_ks6(off, on),
            prefix,
        ]
    else:
        all_commands = check_all_commands_equal(off, on)
        structure.append(all_commands)
    e6 = {"gateoff": e6_row(off), "gateon": e6_row(on)}
    e6["grade"] = e6_grade(e6["gateoff"], e6["gateon"])
    pair = pair_comparison(off, on)
    stop_reasons = failed_ids(identity) + failed_ids(structure)
    stop_reasons += (
        [f"E-6 both: {item}" for item in e6["grade"]["both_failed"]] if k1["active"] else []
    )
    fail_reasons = fail_reasons_of(e6, pair) if k1["active"] else []
    # rev1 R1-5 applies to judged values; with K1 inactive they are info only (I-6)
    missing = missing_values_of(e6, pair)
    status = final_status(k1["active"], stop_reasons, fail_reasons, missing if k1["active"] else [])
    return {
        "status": status,
        "stop_reasons": stop_reasons,
        "fail_reasons": fail_reasons,
        "incomplete_reasons": missing if k1["active"] else [],
        "missing_values_info": [] if k1["active"] else missing,
        "info_only": not k1["active"],
        "flags": {"gateon": e6_flags(e6["gateon"]), "gateoff": e6_flags(e6["gateoff"])},
        "k1": k1,
        "identity": identity,
        "structure": structure,
        "e6": e6,
        "pair": pair,
        "predictions": prediction_table(k1, off, on, prefix, e6, pair, status, all_commands),
    }


def judge_batch(
    batch_dir: Path, root: Path, prelaunch_path: Path, postrun_path: Path
) -> dict[str, Any]:
    """``judge``: input checks (5), then :func:`judge_rows`."""
    doc: dict[str, Any] = {
        "kind": "judge",
        "tool": tool_record(),
        "taken_utc": utc_now(),
        "batch": batch_dir.as_posix(),
        "root": root.as_posix(),
        "plan_sha256": dict(PLAN_SHA256_BY_FILE),
        "progress_log": progress_counts(batch_dir),
        "rerun": rerun_record(batch_dir),
        "files_read_sha256": files_read(batch_dir, [prelaunch_path, postrun_path]),
    }
    batch = read_json(batch_dir / "batch.json")
    if batch is None:
        return {
            **doc,
            "status": STATUS_INCOMPLETE,
            "incomplete_reasons": ["batch.json missing or unreadable"],
        }
    doc["row_labels"] = row_labels(batch)
    structure_problems = batch_structure_problems(batch)
    if structure_problems:
        return {**doc, "status": STATUS_STOP, "stop_reasons": structure_problems}
    entries = {e["case"]: e for e in batch["cases"]}
    rows, problems = {}, []
    for case in GATE_OF_CASE:
        row, row_problems = load_row(batch_dir, case, entries[case])
        rows[case] = row
        problems += row_problems
    if problems:
        return {**doc, "status": STATUS_INCOMPLETE, "incomplete_reasons": problems}
    return {
        **doc,
        **judge_rows(
            rows[CASE_GATEOFF], rows[CASE_GATEON], batch, root, prelaunch_path, postrun_path
        ),
    }


# ================================================================ output
def tool_record() -> dict[str, Any]:
    return {"path": TOOL_PATH.as_posix(), "sha256": sha256_file(TOOL_PATH)}


def markdown_of(doc: dict[str, Any]) -> str:
    """A short human-readable view of a record (the JSON file is the full record)."""
    lines = [
        f"# LAS-b K1 S-Ch {doc.get('kind')}",
        "",
        f"- status: `{doc.get('status')}` ({GRADE_WORDS.get(str(doc.get('status')), '')})",
        f"- taken (UTC): {doc.get('taken_utc')}",
        f"- tool sha256: `{dig(doc, 'tool', 'sha256')}`",
    ]
    for key in ("stop_reasons", "fail_reasons", "incomplete_reasons"):
        if doc.get(key):
            lines.append(f"- {key}: " + "; ".join(map(str, doc[key])))
    if isinstance(doc.get("checks"), dict):
        lines += ["", "| item | ok |", "|---|---|"]
        lines += [f"| {name} | {ok} |" for name, ok in doc["checks"].items()]
    for section in ("identity", "structure"):
        if isinstance(doc.get(section), list):
            lines += ["", f"## {section}", "", "| id | ok |", "|---|---|"]
            lines += [f"| {c['id']} | {c['ok']} |" for c in doc[section]]
    if isinstance(doc.get("predictions"), dict):
        lines += [
            "",
            "## predictions (record)",
            "",
            "| Q | item | value | expected | inside |",
            "|---|---|---|---|---|",
        ]
        for q in ("Q-C1", "Q-C2", "Q-C3"):
            for item in doc["predictions"][q]:
                cells = (q, item["item"], item["value"], item["expected"], item["inside"])
                lines.append("| " + " | ".join(map(str, cells)) + " |")
    return "\n".join(lines) + "\n"


def write_output(doc: dict[str, Any], out_path: Path, output_format: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "md":
        out_path.write_text(markdown_of(doc), encoding="utf-8")
    else:
        out_path.write_text(
            json.dumps(plain(doc), indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )


def summary_line(doc: dict[str, Any], out_path: Path) -> str:
    summary = {
        "kind": doc.get("kind"),
        "status": doc.get("status"),
        "exit_code": doc.get("exit_code"),
        "out": out_path.as_posix(),
    }
    for key in ("stop_reasons", "fail_reasons", "incomplete_reasons"):
        if doc.get(key):
            summary[key] = doc[key]
    if "checks" in doc:
        summary["failed_checks"] = [name for name, ok in doc["checks"].items() if not ok]
    return json.dumps(plain(summary), ensure_ascii=True)


# ================================================================ command line
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LAS-b K1 S-Ch judge (las_k1_sch_plan.md)")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prelaunch", "postrun", "judge"):
        cmd = sub.add_parser(name)
        cmd.add_argument(
            "--root",
            type=Path,
            default=DEFAULT_ROOT,
            help="project root (git queries, sealed files)",
        )
        cmd.add_argument(
            "--out", type=Path, default=None, help="output file (default under v5/las/k1)"
        )
        cmd.add_argument("--format", choices=("json", "md"), default="json")
        if name in ("postrun", "judge"):
            cmd.add_argument("--prelaunch", type=Path, default=None)
        if name == "judge":
            cmd.add_argument("--postrun", type=Path, default=None)
            cmd.add_argument(
                "--batch",
                type=Path,
                required=True,
                help="07_results/S9/batch_V5-LAS-K1-CHRONO_<stamp>",
            )
    return parser


def default_path(root: Path, name: str) -> Path:
    return root / OUT_DIR_RELATIVE / name


def run_command(args: argparse.Namespace) -> tuple[dict[str, Any], Path]:
    root = args.root.resolve()
    if not root.is_dir():
        raise InputError(f"--root {root}: no such folder")
    prelaunch_path = getattr(args, "prelaunch", None) or default_path(root, PRELAUNCH_NAME)
    if args.command == "prelaunch":
        doc = identity_snapshot(root, "prelaunch")
        doc["status"] = STATUS_PASS if doc["all_ok"] else STATUS_STOP
        return doc, args.out or default_path(root, PRELAUNCH_NAME)
    if args.command == "postrun":
        doc = postrun_snapshot(root, prelaunch_path)
        doc["status"] = STATUS_PASS if doc["all_ok"] else STATUS_STOP
        return doc, args.out or default_path(root, POSTRUN_NAME)
    if not args.batch.is_dir():
        raise InputError(f"--batch {args.batch}: no such folder")
    postrun_path = args.postrun or default_path(root, POSTRUN_NAME)
    doc = judge_batch(args.batch.resolve(), root, prelaunch_path, postrun_path)
    doc["grade_word"] = GRADE_WORDS[doc["status"]]
    return doc, args.out or default_path(root, JUDGE_NAME)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        doc, out_path = run_command(args)
    except InputError as error:
        print(json.dumps({"status": STATUS_STOP, "exit_code": 2, "input_error": str(error)}))
        return 2
    except Exception as error:  # noqa: BLE001 - the contract: last line JSON, exit 3
        print(
            json.dumps(
                {
                    "status": STATUS_ERROR,
                    "exit_code": 3,
                    "internal_error": f"{type(error).__name__}: {error}",
                }
            )
        )
        return 3
    doc["exit_code"] = EXIT_CODES[doc["status"]]
    write_output(doc, out_path, args.format)
    print(summary_line(doc, out_path))
    return doc["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
