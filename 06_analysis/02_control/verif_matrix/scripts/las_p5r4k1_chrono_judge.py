"""LAS-b P5r4 + K1 re-judgement, path 1 Chrono judge: batch ``V5-LAS-P5R4-K1`` (12 rows).

Rules: the sealed new original ``las_p5r4_k1_rules.md`` (control-expert, LF sha256
:data:`RULES_SHA256`) and the ten rules files of its section 0 table. The rules text wins
where this code differs; section numbers in the comments are the rules'. The identity code
(git queries, row head / dirty fallback, hull hook, placement, command digest, argv options,
the adopt2 decision table and K-8) is copied from ``las_k1_rem_judge.py`` (git blob
:data:`REM_JUDGE_BLOB`, LF sha256 :data:`REM_JUDGE_LF_SHA256`), not imported.

Sub-commands
  prelaunch  K-0 / K-1 / K-2 / K-6 records right before the launch -> ``p5k_chrono_prelaunch.json``
  postrun    the same records after the batch, compared with the prelaunch record
  judge      K-0 .. K-9, BT-C (4.4) and 6.3 (CC-2, CC-F, G-2'C, CC-S, CK-1C, CC-R, the
             observation requirement) with 16.6 priority -> ``judge_p5k_chrono.json``
  fields     16.2 (나) G-S field check of a batch folder: progress END ``rc=0``, the row files
             and every key path the judge reads; presence only, no value is printed

Rows are found by the ``p5k_id`` of their ``batch.json`` entry (A1 .. C4, rules 4.3); the case
names are cad-expert's. The grade is PROVISIONAL: ``k10`` is ``null`` until the path 2 recount
agrees (10.2). Read only: the only child processes are git queries. Standard library only.

Usage (python-dev or dynamics-dev, PowerShell, project root):
  python -I -B 06_analysis/02_control/verif_matrix/scripts/las_p5r4k1_chrono_judge.py
      prelaunch --batch-plan <rows.json> --audit-report <md> [--allow-dirty P ...]
          [--path2-sha NAME=SHA ...] [--gs-list-sha SHA]
      postrun --batch <folder> [--prelaunch F]
      judge --batch <folder> --expect-tool-sha <sha> [--prelaunch F] [--postrun F]
          [--rem-batch <REM batch folder>]
      fields --batch <folder>
      [--root R] [--out F] [--rules-rev3 <rev3 md>]   (global options, before the sub-command)
Thresholds (rev3 RV3-1): within 1e-9 of a threshold (field unit) equals it; BT-C keeps the
rows with n(t_s) <= 1280 (rev3 RV3-6 W-4).
Exit codes: 0 pass (prelaunch / postrun / fields: every item true; judge: provisional 통과),
1 judge 미달 / 판정 불가 or a fields item false, 2 stop or input error, 3 tool error. The last
stdout line is JSON.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import statistics
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
OUT_DIR_RELATIVE = Path("06_analysis/03_hydraulic/coupled/v5/las/p5r4k1")
PRELAUNCH_NAME = "p5k_chrono_prelaunch.json"
POSTRUN_NAME = "p5k_chrono_postrun.json"
JUDGE_NAME = "judge_p5k_chrono.json"
FIELDS_NAME = "p5k_chrono_gs_fields.json"
REM_JUDGE_BLOB = "e00a68a06c72fc3cbde0878e4826b3d2c51393f7"
REM_JUDGE_LF_SHA256 = "49be3d10968cac46e24d31255e2d9cad9221626076f664c9e2bfbe4bf8d6e7d5"

# ---------------------------------------------------------------- sealed identity (K-0, K-2)
RULES_DIR_RELATIVE = Path("06_analysis/02_control/verif_matrix")
RULES_NAME = "las_p5r4_k1_rules.md"
RULES_SHA256 = "5ee2bac0451f0ca00139a5a2d238c38d13a6b0f430efc5b44fe0e8b929c2f979"
INHERITED_RULES = {
    "las_rev_targeted_rules.md":
        "bb235f27567240b205a544ed7cfd10237827e4627088e0eab1f62b318416ff60",
    "las_rev_targeted_rules_rev1.md":
        "672bc8f81ba75419e5a201e05a94e2f9aead2de3c205f80c2661e7474cd9fd51",
    "las_revA_targeted_rules.md":
        "b09d004bb2f641db40cdd139a6fb2b1645651e4a3e45a9b16e81a5c938d5778f",
    "las_revA_targeted_rules_rev1.md":
        "c02518021c00b69a9d02ec6bceddbea18b9686ef6de96bafe5e55b716b023960",
    "las_revA_targeted_rules_rev2.md":
        "9f478b7fbc5aa0bd8859716b056bf2d531ac02057dc36d218bada7d7f13e4565",
    "las_revA_targeted_rules_rev3.md":
        "98082a368da626f90ce3b0a41f5c74145b4095c155f14b2b2f63eb319352d709",
    "las_k1_rules.md": "2742c9760ad55a87eccbf73e84025aafe0171a3555e1f54ab19fab24d888e4a0",
    "las_k1_rules_rev1.md": "eeee4ab9661babff50117b8ff579aa41e27a98d083f1fc13f46fb5c733e0b4d3",
    "las_k1_rules_adopt.md": "864836d852b4a783a577f01f738536b7c30c574bf4bebb3b0219e68e59b07ea8",
    "las_k1_rules_adopt2.md": "fb3a5696f24385e81acc9c564500b5e5a0547db45a5335272e7d18400f1e68e8",
}
RULES_ADDENDA = {
    "las_p5r4_k1_rules_rev1.md":
        "f39846d6067a7bd409b4ac930d73ebde58a721728ec7d93703ff4627bf21e4b6",
    "las_p5r4_k1_rules_rev2.md":
        "e0a7d1e56b57df5336fc2fd40835624d93585fb224063f6c8068c2b1ba7b10fc",
    "las_p5r4_k1_rules_rev3.md":
        "31ba01dff9defb4b7274b27b9df1a427c460fa9ccc5efd84f5a3145e0d3ef8f6",
}
"""Sealed addenda (rev1, before any result: RV1-1 .. RV1-4 records, RV1-6 identity)."""
CODE_DIFF_PATHS = ("03_src", "02_params", "04_scripts")
K2_CODE_FILES = (
    "04_scripts/02_chrono/run_S9.py",
    "04_scripts/02_chrono/s9_batch.py",
    "04_scripts/02_chrono/las_p5r4_k1_chrono_rows.py",
    "03_src/outrigger_sim/control/c2.py",
    "03_src/outrigger_sim/control/zero_calibration.py",
    "03_src/outrigger_sim/chrono/hull_hook.py",
    "04_scripts/03_control/s9/late_loc_rule.py",
    "03_src/outrigger_sim/hydraulics/v5_options.py",
    "03_src/outrigger_sim/chrono/rigid_base.py",
)
"""Rules 5.2: work-tree raw sha256 (CRLF) and HEAD blob sha256 (LF) of these files."""
BLOB_CHECK_FILES = ("03_src/outrigger_sim/control/c2.py",
                    "03_src/outrigger_sim/hydraulics/v5_options.py")
RECORDED_CONTROLLER_FILES = (
    ("outrigger_sim.control.c2", "03_src/outrigger_sim/control/c2.py"),
    ("outrigger_sim.control.zero_calibration", "03_src/outrigger_sim/control/zero_calibration.py"),
)
DLL_PATH = "03_src/outrigger_sim/native/chrono_hull/bin/chrono_hull_hook.dll"
DLL_SHA256 = "cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15"

# ---------------------------------------------------------------- rows (rules 4.3)
TAG_VB, TAG_V0 = "final_C4G2_P3_LAS_K1", "final_C4G2_LAS_K1"
ARM_REF, ARM_CAND = "ref", "cand"
ARM_CANDIDATE = {ARM_REF: "P0", ARM_CAND: "P5r4"}


@dataclass(frozen=True)
class RowSpec:
    """One row of the rules 4.3 table."""

    p5k_id: str
    group: str
    arm: str
    setting: str
    duration_s: float
    mass_scale: float
    pair: str

    @property
    def tag(self) -> str:
        return TAG_V0 if self.setting == "V0" else TAG_VB


ROW_SPECS = (
    RowSpec("A1", "A", ARM_REF, "VB", 160.0, 1.0, "A2"),
    RowSpec("A2", "A", ARM_CAND, "VB", 160.0, 1.0, "A1"),
    RowSpec("A3", "A", ARM_REF, "VB", 160.0, 1.0, "A4"),
    RowSpec("A4", "A", ARM_CAND, "VB", 160.0, 1.0, "A3"),
    RowSpec("A5", "A", ARM_REF, "V0", 160.0, 1.0, "A6"),
    RowSpec("A6", "A", ARM_CAND, "V0", 160.0, 1.0, "A5"),
    RowSpec("B1", "B", ARM_REF, "VB", 200.0, 1.0, "B2"),
    RowSpec("B2", "B", ARM_CAND, "VB", 200.0, 1.0, "B1"),
    RowSpec("C1", "C", ARM_REF, "VB", 120.0, 1.0, "C2"),
    RowSpec("C2", "C", ARM_CAND, "VB", 120.0, 1.0, "C1"),
    RowSpec("C3", "C", ARM_REF, "VB", 180.0, 1.1, "C4"),
    RowSpec("C4", "C", ARM_CAND, "VB", 180.0, 1.1, "C3"),
)
SPEC_BY_ID = {spec.p5k_id: spec for spec in ROW_SPECS}
PAIRS = (("A1", "A2"), ("A3", "A4"), ("A5", "A6"), ("B1", "B2"), ("C1", "C2"), ("C3", "C4"))
"""(ref, cand) pairs of rules 4.3."""
G2PC_ROWS = ("A2", "A4", "A6")
CK1C_PAIRS = (("B1", "B2"), ("C1", "C2"), ("C3", "C4"))
FIXED_ARGS = {"seed": 20261026, "pressure_grade": "normal", "imu_grade": "ideal",
              "fs_kN": 4.0, "pad_variant": "dwg_rear250", "threads": 4}
"""K-7 fixed values (rules 4.3) read from result.json ``args``."""
CASE_OPTION = "--case"
CANDIDATE_OPTION = "--las-candidate"
FORBIDDEN_OPTIONS = ("--k1-order-gate", "--k1-forced-block", "--las-off")
THREADS = 4

# ---------------------------------------------------------------- BT-C (rules 4.4)
BT_C_REFERENCES = {
    "C1": ("REM_J2_B_top_Fs4_VB_gateon/controller_commands.npz",
           "ebf86d1d40af464e2e4e23d4ea79ad56721829e65d70cb4efb1d2cc072e4b559", None),
    "C3": ("REM_J2_B_top_Fs4_m1p1_VB_gateon/controller_commands.npz",
           "97aace614a534a6aa95f67857947dcd541f9ecca1e9974eb5105fc017bf7c8aa", 128.0),
}
"""Row -> (REM batch-relative npz, its raw file sha256, end of the compared span [s] or None
for the whole file). The comparison is on the ``t_s`` / ``issued_u_m_s`` contents."""
DEFAULT_REM_BATCH = Path("07_results/S9/batch_V5-LAS-K1-REM_20261109_235554")

# ---------------------------------------------------------------- judging constants (6.3)
PERIOD_S = 0.1
F_MIN_N = 9414.589
CC_FLOOR_N = F_MIN_N + 1000.0
G2PC_FLOOR_N = F_MIN_N + 2000.0
STROKE_LIMIT_M = 0.001
READY_MEDIAN_LIMIT_S = 1.0
READY_MAX_LIMIT_S = 5.0
THRESHOLD_TOLERANCE = 1e-9
"""rev3 RV3-1: a value within 1e-9 (field unit) of a threshold equals it."""
RULES_PATH_OVERRIDES: dict[str, Path] = {}
"""Rules file name -> path that replaces the rules folder copy (``--rules-rev3``; set by
:func:`main` before anything is read)."""
THIN_MARGIN_PERIODS = 12
RANGE_IN, RANGE_OUT_REF_NONE, RANGE_OUT = "in", "ref_none", "out"
"""rev2 RV2-2 scope of a CC-F / CC-S pair (judged / outside: ref None / outside: ref below)."""
PATH_CORNER_BIAS, PATH_ANCHOR, PATH_BOTH, PATH_NONE = "1", "2", "1+2", "3"
ANCHOR_PATHS = (PATH_CORNER_BIAS, PATH_ANCHOR, PATH_BOTH)
BIAS_EVENT = "INFO_CLEARANCE_BIAS"
ANCHOR_EVENT = "INFO_LOC_CLEARANCE_ANCHOR"
ITEM_KEYS = ("P3-1_recontact_pass", "P3-1_crawler_zero_after_ready", "P3-2_within",
             "P3-3_within", "P3-4_within_0p2", "P3-5_within", "P3-6_within", "P3-7_within",
             "P3-8_within")
"""Rules 6.3: the judged item set I in ``p3b.checks``."""
LATE_LOC_KEYS = ("P3-2_late_loc_reapproach", "P3-2_late_loc_revoked")
WINDOW_SHORT_KEY = "P3-4_window_short"
READY_PHASE, FAULT_PHASE = "ready", "fault"
LOC_EVENT = "crawler_liftoff_confirmed"
SLOPE_MARGIN_EVENT = "INFO_LOC_CLEARANCE_MARGIN"
MARGIN_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN"
SKIP_ORDER_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order"
REVOKE_EVENT = "INFO_LOC_REVOKED"
NEW_EVENT_PREFIXES = ("FAULT", "WARN")
PLAIN_CLASS_NAME = "C2Controller"
B0_VALUES = {"light_leg_fraction_of_F_min": 3.5, "min_active_periods": 0,
             "end_ramp_periods": 0}
P5R4_VALUES = {"light_leg_fraction_of_F_min": 4.5, "min_active_periods": 0,
               "end_ramp_periods": 4}

STATUS_STOP, STATUS_UNDECIDABLE, STATUS_FAIL, STATUS_PASS = "stop", "undecidable", "fail", "pass"
STATUS_RANK = {STATUS_STOP: 0, STATUS_UNDECIDABLE: 1, STATUS_FAIL: 2, STATUS_PASS: 3}
GRADES = {STATUS_STOP: "stop", STATUS_UNDECIDABLE: "판정 불가", STATUS_FAIL: "미달",
          STATUS_PASS: "통과"}
EXIT_CODES = {STATUS_PASS: 0, STATUS_FAIL: 1, STATUS_UNDECIDABLE: 1, STATUS_STOP: 2}
GIT_TIMEOUT_S = 60.0
MISSING = object()

FIELD_PATHS = (
    ("p3b", "checks"),
    ("p3b", "P3-3_leg_force", "F_min_after_N"),
    ("p3b", "P3-3_leg_force", "F_min_transient_N"),
    ("p3b", "P3-5_clearance_stroke", "s_motor_max_m"),
    ("p3b", "P3-6_ready", "t_ready_after_loop_start_s"),
    ("controller_meta", "liftoff_approach_slow", "settings"),
    ("controller_meta", "liftoff_approach_slow", "start_s"),
    ("controller_meta", "liftoff_approach_slow", "ramp"),
    ("controller_meta", "slope_clearance_margin", "order_gate", "enabled"),
    ("controller_meta", "slope_clearance_margin", "order_gate", "decisions"),
    ("controller_meta", "soil", "mode_starts"),
    ("controller_meta", "loc_revoke", "t_revoke_s"),
    ("controller_meta", "touch_creep_latch", "settings"),
    ("c2_setup", "las_candidate", "requested"),
    ("c2_setup", "las_candidate", "settings"),
    ("c2_setup", "k1_order_gate"),
    ("c2_setup", "expect_controller", "ok"),
    ("hull_hook", "mode"),
    ("hull_hook", "requested"),
    ("hull_hook", "fallback_reason"),
    ("hull_hook", "dll_sha256"),
    ("placement", "mode"),
    ("placement", "affinity_ok"),
    ("placement", "power_throttling_off_ok"),
    ("code_state", "git_at_start", "head"),
    ("code_state", "git_at_start", "dirty"),
    ("code_files_at_start", "files"),
    ("c2_setup", "k1_order_gate_effective"),
    ("c2_setup", "touch_creep_effective"),
    ("args", "las_candidate"),
    ("args", "threads"),
    ("num_threads_chrono",),
    ("events",),
    ("phases",),
)
"""16.2 (나): key paths the judge reads in ``result.json`` (presence only)."""
AFTER_DEPARTURE_PATHS = (("p3b", "P3-3_leg_force", "F_min_after_N"),
                         ("p3b", "P3-3_leg_force", "F_min_transient_N"))
"""run_S9 writes these only after the crawler departure (``p3b.departure.departed``)."""
BATCH_ENTRY_FIELDS = ("rc", "argv", "pool", "omp_wait_policy", "hull_hook_requested",
                      "hull_hook_effective", "p5k_id")


class InputError(Exception):
    """Bad command-line input (exit 2)."""


# ================================================================ small helpers (copied)
def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    return sha256_bytes(path.read_bytes()) if path.is_file() else None


def lf_sha256_file(path: Path) -> str | None:
    return sha256_bytes(path.read_bytes().replace(b"\r\n", b"\n")) if path.is_file() else None


def is_below(value: float, limit: float) -> bool:
    """rev3 RV3-1.1: ``value < limit`` with the tolerance, ``value < limit - 1e-9``."""
    return value < limit - THRESHOLD_TOLERANCE


def is_above(value: float, limit: float) -> bool:
    """rev3 RV3-1.1: ``value > limit`` with the tolerance, ``value > limit + 1e-9``."""
    return value > limit + THRESHOLD_TOLERANCE


def period_of(t_s: float | None) -> int | None:
    """Rules 0: whole control periods ``round(t / 0.1)`` (Python round)."""
    return None if t_s is None else round(float(t_s) / PERIOD_S)


def event_base_name(name: str) -> str:
    """The event name before ``:`` (compared by exact match)."""
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
    return isinstance(value, dict) and set(value) == {"error"}


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def scalar(value: Any) -> Any:
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
    return {"path": TOOL_PATH.as_posix(), "sha256": sha256_file(TOOL_PATH),
            "lf_sha256": lf_sha256_file(TOOL_PATH),
            "copied_from": {"las_k1_rem_judge.py": {"git_blob": REM_JUDGE_BLOB,
                                                    "lf_sha256": REM_JUDGE_LF_SHA256}}}


def worst_status(statuses: Iterable[str]) -> str:
    """16.6: ``stop`` > ``undecidable`` > ``fail`` > ``pass``."""
    found = [status for status in statuses if status in STATUS_RANK]
    return min(found, key=lambda s: STATUS_RANK[s]) if found else STATUS_PASS


def status_of(ok: bool | None) -> str:
    return STATUS_UNDECIDABLE if ok is None else (STATUS_PASS if ok else STATUS_FAIL)


# ================================================================ git queries (copied)
@dataclass(frozen=True)
class GitResult:
    returncode: int | None
    stdout: bytes
    error: str | None


def run_git(root: Path, *args: str) -> GitResult:
    """One read-only git query in ``root``; a time-out or launch failure is returned."""
    kwargs: dict[str, Any] = {"cwd": str(root), "capture_output": True,
                              "timeout": GIT_TIMEOUT_S, "stdin": subprocess.DEVNULL}
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
    path = line[3:]
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    return path.strip().strip('"')


def status_record(root: Path, allowed: Iterable[str]) -> dict[str, Any]:
    """K-1: ``git status --porcelain=v1 --untracked-files=no`` against the allow list."""
    allowed_set = frozenset(allowed)
    result = run_git(root, "status", "--porcelain=v1", "--untracked-files=no")
    if result.returncode != 0:
        return {"lines": None, "unexpected": None, "ok": False, "error": result.error}
    text = result.stdout.decode("utf-8", "replace")
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    unexpected = [line for line in lines if porcelain_path(line) not in allowed_set]
    return {"basis": "--untracked-files=no", "lines": lines, "allowed": sorted(allowed_set),
            "unexpected": unexpected, "ok": not unexpected, "error": None}


def blob_sha256(root: Path, revision: str | None, path: str) -> str | None:
    if revision is None:
        return None
    result = run_git(root, "show", f"{revision}:{path}")
    return sha256_bytes(result.stdout) if result.returncode == 0 else None


# ================================================================ controller_commands.npz (copied)
@dataclass(frozen=True)
class CommandDigest:
    """``controller_commands.npz`` ``t_s`` / ``issued_u_m_s`` as ``<f8`` bytes."""

    sha256: str
    t_s: tuple[float, ...]
    rows: tuple[bytes, ...]
    width: int = 4
    """``issued_u_m_s`` columns (both arrays are ``<f8``: other dtypes are not read)."""

    def prefix_sha256(self, t_end_s: float | None) -> str:
        """rev2 RV2-13 with rev3 RV3-6 W-4: digest of the shape, dtype and values of the rows
        with ``n(t_s) <= n(t_end_s)`` (whole periods, 128 s = 1280, no tolerance); None: the
        whole arrays."""
        if t_end_s is None:
            count = len(self.t_s)
        else:
            last_period = period_of(t_end_s)
            count = sum(1 for t in self.t_s if period_of(t) <= last_period)
        t_bytes = struct.pack(f"<{count}d", *self.t_s[:count])
        shape = f"<f8 t_s ({count},) issued_u_m_s ({count}, {self.width})".encode("ascii")
        return sha256_bytes(shape + t_bytes + b"".join(self.rows[:count]))


def read_npy_f8(data: bytes) -> tuple[tuple[int, ...], bytes]:
    if data[:6] != b"\x93NUMPY":
        raise ValueError("not an .npy member")
    major = data[6]
    if major == 1:
        (header_length,) = struct.unpack("<H", data[8:10])
        start = 10
    else:
        (header_length,) = struct.unpack("<I", data[8:12])
        start = 12
    header = ast.literal_eval(data[start: start + header_length].decode("latin1"))
    if header.get("descr") != "<f8" or header.get("fortran_order"):
        raise ValueError(f"unsupported npy header {header}")
    shape = tuple(int(n) for n in header["shape"])
    count = math.prod(shape)
    body = data[start + header_length: start + header_length + 8 * count]
    if len(body) != 8 * count:
        raise ValueError("truncated npy data")
    return shape, body


def read_commands(path: Path) -> CommandDigest | None:
    """The command digest of ``path``; None when absent or not readable."""
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
    rows = tuple(u_bytes[i * width: (i + 1) * width] for i in range(n_rows))
    return CommandDigest(sha256_bytes(t_bytes + u_bytes), t_values, rows, u_shape[1])


# ================================================================ prelaunch / postrun
def sealed_rules() -> dict[str, str]:
    return {RULES_NAME: RULES_SHA256, **RULES_ADDENDA, **INHERITED_RULES}


def rules_record(root: Path) -> dict[str, Any]:
    """K-0 / S-1: every rules file's LF sha256 and ``.sha256`` record against the seal."""
    files = {}
    for name, sealed in sealed_rules().items():
        path = RULES_PATH_OVERRIDES.get(name, root / RULES_DIR_RELATIVE / name)
        record_path = path.with_suffix(".sha256")
        tokens = record_path.read_text(encoding="utf-8", errors="replace").split() \
            if record_path.is_file() else []
        digest = lf_sha256_file(path)
        files[name] = {"lf_sha256": digest, "sha256_file_record": tokens[0].lower()
                       if tokens else None, "sealed": sealed,
                       "ok": digest == sealed and bool(tokens) and tokens[0].lower() == sealed}
    return {"files": files, "ok": all(record["ok"] for record in files.values())}


def code_file_records(root: Path, head_sha: str | None) -> dict[str, Any]:
    """K-2: work-tree raw sha256 and HEAD blob sha256 of :data:`K2_CODE_FILES`."""
    files = {path: {"worktree_sha256": sha256_file(root / path),
                    "blob_sha256": blob_sha256(root, head_sha, path)} for path in K2_CODE_FILES}
    is_complete = all(r["worktree_sha256"] and r["blob_sha256"] for r in files.values())
    return {"files": files, "ok": is_complete}


def dll_record(root: Path) -> dict[str, Any]:
    digest = sha256_file(root / DLL_PATH)
    return {"path": DLL_PATH, "sha256": digest, "expected": DLL_SHA256, "ok": digest == DLL_SHA256}


def audit_record(audit_path: Path) -> dict[str, Any]:
    digest = sha256_file(audit_path)
    return {"path": audit_path.as_posix(), "sha256": digest, "ok": digest is not None}


def plan_rows_of(document: Any) -> list[dict[str, Any]] | None:
    if isinstance(document, dict):
        document = document.get("rows", document.get("cases"))
    if not isinstance(document, list):
        return None
    return [row for row in document if isinstance(row, dict)]


def batch_plan_record(plan_path: Path) -> dict[str, Any]:
    """The batch plan: its sha256, the 12 ``p5k_id`` rows and the planned pools."""
    digest = sha256_file(plan_path)
    try:
        document = json.loads(plan_path.read_text(encoding="utf-8")) if digest else None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        document = None
    rows = plan_rows_of(document)
    if rows is None:
        return {"path": plan_path.as_posix(), "sha256": digest, "rows": None, "ok": False,
                "problems": ["batch plan missing, unreadable or without a row list"]}
    by_id = {str(row.get("p5k_id")): row for row in rows}
    problems = []
    if set(by_id) != set(SPEC_BY_ID) or len(rows) != len(ROW_SPECS):
        problems.append(f"plan p5k_id {sorted(by_id)} != rules 4.3 {sorted(SPEC_BY_ID)}")
    pools = {key: row.get("pool", row.get("planned_pool")) for key, row in by_id.items()}
    for ref_id, cand_id in PAIRS:
        if pools.get(ref_id) != pools.get(cand_id):
            problems.append(f"{ref_id}/{cand_id}: planned pools {pools.get(ref_id)!r} / "
                            f"{pools.get(cand_id)!r} differ (K-6: same kind per pair)")
    return {"path": plan_path.as_posix(), "sha256": digest,
            "cases": {key: row.get("case") for key, row in by_id.items()},
            "planned_pool": pools, "ok": not problems, "problems": problems}


def identity_snapshot(root: Path, allowed_dirty: list[str], audit_path: Path) -> dict[str, Any]:
    head = git_head(root)
    return {"tool": tool_record(), "taken_utc": utc_now(), "root": root.as_posix(),
            "head": head, "git_status": status_record(root, allowed_dirty),
            "code_files": code_file_records(root, head["sha"]), "dll": dll_record(root),
            "rules": rules_record(root), "audit_report": audit_record(audit_path)}


def snapshot_checks(snapshot: dict[str, Any]) -> dict[str, bool]:
    return {"head": snapshot["head"]["ok"], "git_status_allowed": snapshot["git_status"]["ok"],
            "code_files": snapshot["code_files"]["ok"], "dll": snapshot["dll"]["ok"],
            "rules": snapshot["rules"]["ok"], "audit_report": snapshot["audit_report"]["ok"]}


def prelaunch_document(root: Path, plan_path: Path, audit_path: Path, allowed_dirty: list[str],
                       path2_sha: dict[str, str], gs_list_sha: str | None) -> dict[str, Any]:
    snapshot = identity_snapshot(root, allowed_dirty, audit_path)
    snapshot["kind"] = "prelaunch"
    snapshot["batch_plan"] = batch_plan_record(plan_path)
    snapshot["path2_sha256"] = dict(path2_sha)
    snapshot["gs_list_sha256"] = gs_list_sha
    checks = snapshot_checks(snapshot)
    checks["batch_plan"] = snapshot["batch_plan"]["ok"]
    checks["path2_sha_recorded"] = bool(path2_sha)
    snapshot["checks"] = checks
    snapshot["all_ok"] = all(checks.values())
    snapshot["status"] = STATUS_PASS if snapshot["all_ok"] else STATUS_STOP
    return snapshot


def comparable_values(snapshot: dict[str, Any]) -> dict[str, Any]:
    files = dig(snapshot, "code_files", "files")
    return {"code_files": files if isinstance(files, dict) else None,
            "dll": dig(snapshot, "dll", "sha256"), "tool": dig(snapshot, "tool", "sha256"),
            "rules": dig(snapshot, "rules", "files"),
            "audit_report": dig(snapshot, "audit_report", "sha256")}


def postrun_document(root: Path, prelaunch_path: Path) -> dict[str, Any]:
    prelaunch = read_json(prelaunch_path)
    allowed = dig(prelaunch, "git_status", "allowed")
    audit_path = dig(prelaunch, "audit_report", "path")
    snapshot = identity_snapshot(root, allowed if isinstance(allowed, list) else [],
                                 Path(audit_path) if isinstance(audit_path, str)
                                 else root / OUT_DIR_RELATIVE / "missing")
    snapshot["kind"] = "postrun"
    snapshot["prelaunch"] = {"path": prelaunch_path.as_posix(), "found": prelaunch is not None,
                             "sha256": sha256_file(prelaunch_path)}
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
            "base": prelaunch_head, "head": snapshot["head"]["sha"],
            "paths": list(CODE_DIFF_PATHS), "quiet": quiet,
            "changed_paths": None if quiet is not False
            else git_diff_names(root, prelaunch_head, snapshot["head"]["sha"])}
        snapshot["differences_to_prelaunch"] = differences
        checks["same_as_prelaunch"] = not differences
        checks["code_diff_since_prelaunch_empty"] = quiet is True
    snapshot["checks"] = checks
    snapshot["all_ok"] = all(checks.values())
    snapshot["status"] = STATUS_PASS if snapshot["all_ok"] else STATUS_STOP
    return snapshot


# ================================================================ judge inputs
@dataclass
class RowInput:
    """One batch row: its rules spec, result.json, batch.json entry and the command digest."""

    spec: RowSpec
    case: str | None
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
    bt_c_references: dict[str, dict[str, Any]] = field(default_factory=dict)
    """Row -> {"file_sha256": raw sha256 of the REM npz, "digest": its CommandDigest}."""


def missing_reasons_of(result: dict[str, Any] | None, entry: dict[str, Any] | None) -> list[str]:
    """10.1 / K-9: why a row is unusable (rc, result.json, the blocks the judge reads)."""
    reasons = []
    if entry is None:
        reasons.append("no batch.json entry")
    elif entry.get("rc") != 0:
        reasons.append(f"rc {entry.get('rc')!r}")
    if result is None:
        return [*reasons, "result.json missing or unreadable"]
    for path in (("controller_meta",), ("controller_meta", "soil"), ("events",), ("p3b",)):
        value = dig(result, *path)
        name = ".".join(path)
        if value is MISSING or value is None:
            reasons.append(f"{name}: missing")
        elif is_error_block(value):
            reasons.append(f"{name}: {value['error']}")
    restored = dig(result, "controller_meta", "soil", "restored_from")
    if restored not in (MISSING, None):
        reasons.append(f"controller_meta.soil.restored_from {restored!r}")
    if dig(result, "restored_from") not in (MISSING, None):
        reasons.append("result restored_from is not None")
    return list(dict.fromkeys(reasons))


def entries_by_id(batch: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(e.get("p5k_id")): e for e in batch.get("cases") or []
            if isinstance(e, dict) and e.get("p5k_id") is not None}


def load_bt_c_references(rem_batch: Path) -> dict[str, dict[str, Any]]:
    out = {}
    for row_id, (relative, _sha, _end) in BT_C_REFERENCES.items():
        path = rem_batch / relative
        out[row_id] = {"path": path.as_posix(), "file_sha256": sha256_file(path),
                       "digest": read_commands(path)}
    return out


def load_judge_inputs(root: Path, batch_dir: Path, prelaunch_path: Path, postrun_path: Path,
                      expect_tool_sha256: str, rem_batch: Path) -> JudgeInputs:
    batch = read_json(batch_dir / "batch.json") or {}
    entries = entries_by_id(batch)
    rows: dict[str, RowInput] = {}
    for spec in ROW_SPECS:
        entry = entries.get(spec.p5k_id)
        case = None if entry is None else str(entry.get("case"))
        folder = batch_dir / (case or "<no case>")
        result = read_json(folder / "result.json") if case else None
        row = RowInput(spec, case, result, entry, read_commands(folder / "controller_commands.npz"))
        row.missing_reasons = missing_reasons_of(result, entry)
        if not batch:
            row.missing_reasons.insert(0, "batch.json missing or unreadable")
        rows[spec.p5k_id] = row
    prelaunch = read_json(prelaunch_path)
    audit_path = dig(prelaunch, "audit_report", "path")
    return JudgeInputs(
        rows=rows, batch=batch, prelaunch=prelaunch, postrun=read_json(postrun_path),
        rules=rules_record(root), tool_sha256=sha256_file(TOOL_PATH),
        expect_tool_sha256=expect_tool_sha256,
        audit_sha256_now=sha256_file(Path(audit_path)) if isinstance(audit_path, str) else None,
        code_diff_quiet=lambda base, head: git_diff_is_empty(root, base, head),
        bt_c_references=load_bt_c_references(rem_batch))


# ================================================================ decision table (copied, adopt2)
@dataclass(frozen=True)
class Decision:
    """One ``order_gate.decisions`` entry with the adopt2 3.1 labels."""

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
    recorded_periods_match: bool

    def to_record(self) -> dict[str, Any]:
        return {"index": self.index, "t_loc_s": self.t_loc_s, "n_loc": self.n_loc,
                "t_P_s": self.t_P_s, "t_S_s": self.t_S_s, "n_P": self.n_P, "n_S": self.n_S,
                "dP": self.dP, "r4_due_without_gate": self.is_r4_due,
                "would_block": self.would_block, "applied": self.is_applied,
                "recorded_periods_match": self.recorded_periods_match}


@dataclass
class RowAnalysis:
    """Events, LOCs, revocations, mode starts and decisions of one usable row."""

    events: list[tuple[float, str]]
    loc_periods: list[int]
    e3c10_loc_periods: list[int]
    revoke_periods: list[int]
    revoke_event_periods: list[int]
    mode_starts: list[tuple[int, float, Any]]
    decisions: list[Decision] | None

    @property
    def r4_decisions(self) -> list[Decision]:
        return [d for d in self.decisions or [] if d.is_r4_due]

    @property
    def l1(self) -> Decision | None:
        r4 = self.r4_decisions
        return r4[0] if r4 else None


def as_int_or_none(value: Any) -> int | None:
    return int(value) if is_number(value) and float(value).is_integer() else None


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


def mode_starts_of(result: dict[str, Any]) -> list[tuple[int, float, Any]]:
    starts = dig(result, "controller_meta", "soil", "mode_starts")
    out = []
    for start in starts if isinstance(starts, list) else []:
        t_s = start.get("t_s") if isinstance(start, dict) else None
        if is_number(t_s):
            out.append((period_of(t_s), float(t_s), start.get("source")))
    return out


def revoke_periods_of(result: dict[str, Any]) -> list[int]:
    times = dig(result, "controller_meta", "loc_revoke", "t_revoke_s")
    return [period_of(t) for t in times if is_number(t)] if isinstance(times, list) else []


def labelled_decision(index: int, raw: dict[str, Any]) -> Decision:
    t_loc = raw.get("t_loc_s") if is_number(raw.get("t_loc_s")) else None
    t_P = raw.get("t_P_s") if is_number(raw.get("t_P_s")) else None
    t_S = raw.get("t_S_s") if is_number(raw.get("t_S_s")) else None
    n_P, n_S = period_of(t_P), period_of(t_S)
    is_match = (as_int_or_none(raw.get("n_P")), as_int_or_none(raw.get("n_S"))) == (n_P, n_S)
    return Decision(index=index, t_loc_s=t_loc, n_loc=period_of(t_loc), t_P_s=t_P, t_S_s=t_S,
                    n_P=n_P, n_S=n_S, dP=n_P - n_S if n_P is not None and n_S is not None
                    else None, is_r4_due=first_true(raw, "r4_due_without_gate",
                                                    "is_r4_due_without_gate"),
                    would_block=raw.get("would_block") is True,
                    is_applied=first_true(raw, "applied", "is_applied"),
                    recorded_periods_match=is_match)


def first_true(raw: dict[str, Any], *names: str) -> bool:
    """A decision flag under its ``to_meta`` name or its attribute name (``is_...``)."""
    for name in names:
        if name in raw:
            return raw[name] is True
    return False


def analyze_row(row: RowInput) -> RowAnalysis:
    result = row.result or {}
    events = events_of(result)
    loc_periods = periods_with_base(events, LOC_EVENT)
    slope_periods = set(periods_with_base(events, SLOPE_MARGIN_EVENT))
    raw = dig(result, "controller_meta", "slope_clearance_margin", "order_gate", "decisions")
    decisions = None
    if isinstance(raw, list):
        decisions = [labelled_decision(i, d if isinstance(d, dict) else {})
                     for i, d in enumerate(raw)]
    return RowAnalysis(events=events, loc_periods=loc_periods,
                       e3c10_loc_periods=[n for n in loc_periods if n in slope_periods],
                       revoke_periods=revoke_periods_of(result),
                       revoke_event_periods=periods_with_base(events, REVOKE_EVENT),
                       mode_starts=mode_starts_of(result), decisions=decisions)


def k8_row_problems(analysis: RowAnalysis) -> list[str]:
    """K-8 = adopt2 K-8 (a) .. (e) and the gate-on (f) (copied from the REM judge)."""
    decisions = analysis.decisions
    if decisions is None:
        return ["no decisions"]
    problems = []
    first_start = min((n for n, _, _ in analysis.mode_starts), default=None)
    e3c10 = set(analysis.e3c10_loc_periods)
    expected_locs = [n for n in analysis.loc_periods
                     if first_start is not None and first_start < n and n not in e3c10]
    if len(decisions) != len(expected_locs):
        problems.append(f"(a) {len(decisions)} decisions != {len(expected_locs)} LOCs after "
                        "the soil-mode start without E3c10")
    loc_set = set(analysis.loc_periods)
    for d in decisions:
        if d.n_loc not in loc_set:
            problems.append(f"(b) decision {d.index} period {d.n_loc} has no LOC event")
        earlier = [t for n, t, _ in analysis.mode_starts if d.n_loc is not None and n < d.n_loc]
        if not earlier or d.t_S_s != earlier[-1]:
            problems.append(f"(c) decision {d.index} t_S_s {d.t_S_s!r} != last earlier mode "
                            f"start {earlier[-1] if earlier else None!r}")
    if sorted(analysis.revoke_periods) != sorted(analysis.revoke_event_periods):
        problems.append(f"(d) revocations meta {analysis.revoke_periods} != events "
                        f"{analysis.revoke_event_periods}")
    margins = periods_with_base(analysis.events, MARGIN_EVENT)
    skips = periods_with_full(analysis.events, SKIP_ORDER_EVENT)
    applied = [d for d in decisions if d.is_applied]
    blocked = [d for d in decisions if d.would_block and not d.is_applied]
    problems += [f"(e) applied decision {d.index}: {margins.count(d.n_loc)} margin events"
                 for d in applied if margins.count(d.n_loc) != 1]
    problems += [f"(e) blocked decision {d.index}: {skips.count(d.n_loc)} skip events"
                 for d in blocked if skips.count(d.n_loc) != 1]
    if len(margins) != len(applied) or len(skips) != len(blocked):
        problems.append(f"(e) events margin {len(margins)} / skip {len(skips)} != decisions "
                        f"applied {len(applied)} / blocked {len(blocked)}")
    l1 = analysis.l1
    if l1 is not None and l1.is_applied:
        later = [d for d in analysis.r4_decisions if d.index > l1.index]
        if later or skips:
            problems.append(f"(f) L1 applied but {len(later)} later R4 decisions / "
                            f"{len(skips)} skip events")
    return problems


# ================================================================ K-0 .. K-9 (identity)
def check_k0(inputs: JudgeInputs) -> dict[str, Any]:
    tool = {"expected (audit)": inputs.expect_tool_sha256,
            "prelaunch": dig(inputs.prelaunch, "tool", "sha256"),
            "postrun": dig(inputs.postrun, "tool", "sha256"), "judge": inputs.tool_sha256}
    is_tool_ok = (all(isinstance(v, str) and v for v in tool.values())
                  and len(set(tool.values())) == 1)
    audit_recorded = dig(inputs.prelaunch, "audit_report", "sha256")
    is_audit_ok = isinstance(audit_recorded, str) and audit_recorded == inputs.audit_sha256_now
    is_rules_ok = inputs.rules.get("ok") is True and dig(inputs.prelaunch, "rules", "ok") is True
    return check("K-0", is_tool_ok and is_audit_ok and is_rules_ok, tool_sha256=tool,
                 audit_report={"prelaunch": audit_recorded, "now": inputs.audit_sha256_now},
                 rules_ok=is_rules_ok)


def row_head(row: RowInput) -> Any:
    head = dig(row.result, "code_state", "git_at_start", "head")
    if isinstance(head, str) and head:
        return head
    head = dig(row.entry, "code_at_launch", "git", "head")
    return head if isinstance(head, str) and head else None


def row_dirty(row: RowInput) -> Any:
    dirty = dig(row.result, "code_state", "git_at_start", "dirty")
    if isinstance(dirty, list):
        return dirty
    dirty = dig(row.entry, "code_at_launch", "git", "dirty")
    return dirty if isinstance(dirty, list) else MISSING


def k1_shared(inputs: JudgeInputs) -> dict[str, Any]:
    prelaunch_head = dig(inputs.prelaunch, "head", "sha")
    postrun_head = dig(inputs.postrun, "head", "sha")
    quiet = None
    if isinstance(prelaunch_head, str) and isinstance(postrun_head, str):
        quiet = inputs.code_diff_quiet(prelaunch_head, postrun_head)
    return {"prelaunch_head": prelaunch_head, "postrun_head": postrun_head,
            "code_diff_quiet_now": quiet,
            "code_diff_quiet_postrun": dig(inputs.postrun, "code_diff_since_prelaunch", "quiet"),
            "prelaunch_status_ok": dig(inputs.prelaunch, "git_status", "ok"),
            "postrun_status_ok": dig(inputs.postrun, "git_status", "ok")}


def k1_row_problems(row: RowInput, shared: dict[str, Any]) -> list[str]:
    problems = []
    head = row_head(row)
    if head is None or head != shared["prelaunch_head"]:
        problems.append(f"head {head!r} != prelaunch {shared['prelaunch_head']!r}")
    allowed = set(dig(shared, "allowed") or [])
    dirty = row_dirty(row)
    if dirty is MISSING or any(path not in allowed for path in dirty):
        problems.append(f"dirty {plain(dirty)!r}")
    return problems


def prelaunch_file(inputs: JudgeInputs, path: str, kind: str) -> Any:
    return dig(inputs.prelaunch, "code_files", "files", path, kind)


def k2_row_problems(inputs: JudgeInputs, row: RowInput) -> list[str]:
    """K-2: the row's ``code_files_at_start`` (work-tree and HEAD blob sha256 of every 5.2
    file, cad-expert key paths) = the prelaunch record, and its head = the prelaunch head."""
    problems = []
    files = dig(row.result, "code_files_at_start", "files")
    if not isinstance(files, dict):
        return ["code_files_at_start.files missing"]
    head = dig(row.result, "code_files_at_start", "head")
    if head != dig(inputs.prelaunch, "head", "sha"):
        problems.append(f"code_files_at_start.head {plain(head)!r} != prelaunch head")
    for path in K2_CODE_FILES:
        record = files.get(path) if isinstance(files.get(path), dict) else {}
        for kind, prelaunch_kind in (("worktree_sha256", "worktree_sha256"),
                                     ("head_blob_sha256", "blob_sha256")):
            want = prelaunch_file(inputs, path, prelaunch_kind)
            if record.get(kind) != want:
                problems.append(f"{path} {kind} {plain(record.get(kind, MISSING))!r} != "
                                f"prelaunch {plain(want)!r}")
    return problems


def k2_batch_problems(inputs: JudgeInputs) -> list[str]:
    """K-2: prelaunch code files complete, postrun = prelaunch, and the ``c2.py`` /
    ``v5_options.py`` blobs = the prelaunch HEAD blobs (re-read now)."""
    problems = []
    if dig(inputs.prelaunch, "code_files", "ok") is not True:
        problems.append("prelaunch code_files not ok (a file or blob missing)")
    if (comparable_values(inputs.prelaunch or {})["code_files"]
            != comparable_values(inputs.postrun or {})["code_files"]):
        problems.append("postrun code file sha256 != prelaunch")
    for path in BLOB_CHECK_FILES:
        pre = prelaunch_file(inputs, path, "blob_sha256")
        post = dig(inputs.postrun, "code_files", "files", path, "blob_sha256")
        if not isinstance(pre, str) or pre != post:
            problems.append(f"{path}: blob prelaunch {plain(pre)!r} / postrun {plain(post)!r}")
    return problems


def argv_of(row: RowInput) -> list[str] | None:
    argv = dig(row.entry, "argv")
    return [str(t) for t in argv] if isinstance(argv, list) else None


def option_values(argv: list[str], names: Iterable[str]) -> tuple[list[str], dict[str, Any]]:
    """``argv`` without the named options (``--x v`` or ``--x=v``) and their values (copied)."""
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


def k3_row_problems(row: RowInput) -> list[str]:
    """K-3: the setting's new tag (``--expect-controller``, its check ok), no ``--las-off``,
    no combination / old / ``_TCL`` tag."""
    spec, result = row.spec, row.result or {}
    tag = scalar(dig(result, "args", "expect_controller"))
    problems = []
    if tag != spec.tag:
        problems.append(f"args.expect_controller {plain(tag)!r} != {spec.tag!r}")
    if dig(result, "c2_setup", "expect_controller", "ok") is not True:
        problems.append("c2_setup.expect_controller.ok is not True")
    argv = argv_of(row) or []
    for option in FORBIDDEN_OPTIONS:
        if any(token == option or token.startswith(f"{option}=") for token in argv):
            problems.append(f"argv has {option}")
    _, values = option_values(argv, ("--expect-controller",))
    if values.get("--expect-controller", spec.tag) != spec.tag:
        problems.append(f"argv --expect-controller {values.get('--expect-controller')!r}")
    entry_tag = dig(row.entry, "controller")
    if entry_tag is not MISSING and entry_tag != spec.tag:
        problems.append(f"batch controller {plain(entry_tag)!r} != {spec.tag!r}")
    return problems


def k4_row_problems(row: RowInput, analysis: RowAnalysis) -> list[str]:
    """K-4: the run controller's gate on, ``c2_setup.k1_order_gate`` = ``preset``, decisions
    there, touch creep latch off, no forced block, the plain controller class."""
    result = row.result or {}
    meta = result.get("controller_meta") or {}
    values = {
        "order_gate.enabled": dig(meta, "slope_clearance_margin", "order_gate", "enabled"),
        "settings.flat_soil_margin_order_gate": dig(
            meta, "slope_clearance_margin", "settings", "flat_soil_margin_order_gate"),
        "c2_setup.k1_order_gate": dig(result, "c2_setup", "k1_order_gate"),
        "k1_order_gate_effective": first_found(result, (("c2_setup", "k1_order_gate_effective"),
                                                        ("k1_order_gate_effective",))),
        "touch_creep_latch.settings.enable": dig(meta, "touch_creep_latch", "settings",
                                                 "enable"),
        "c2_setup.k1_forced_block": forced_mode(result),
        "controller class": class_tail(controller_class(row)),
        "order_gate.decisions": "present" if analysis.decisions is not None else "absent",
    }
    want = {"order_gate.enabled": True, "settings.flat_soil_margin_order_gate": True,
            "c2_setup.k1_order_gate": "preset", "k1_order_gate_effective": True,
            "touch_creep_latch.settings.enable": False, "c2_setup.k1_forced_block": "off",
            "controller class": PLAIN_CLASS_NAME, "order_gate.decisions": "present"}
    problems = [f"{k} {plain(values[k])!r} != {want[k]!r}" for k in want
                if values[k] != want[k]]
    effective = dig(result, "c2_setup", "touch_creep_effective")
    if effective not in (False, "off"):
        problems.append(f"c2_setup.touch_creep_effective {plain(effective)!r} is not off")
    return problems


def controller_class(row: RowInput) -> Any:
    """The controller class name: ``c2_setup.k1_forced_block.class`` (run_S9 4d165c2; the batch
    entry ``controller`` is the controller tag, checked in K-3)."""
    return first_found(row.result, (("c2_setup", "k1_forced_block", "class"),
                                    ("c2_setup", "controller_class")))


def first_found(data: Any, paths: Iterable[tuple]) -> Any:
    for path in paths:
        value = dig(data, *path)
        if value is not MISSING:
            return value
    return MISSING


def forced_mode(result: dict[str, Any]) -> Any:
    setup = dig(result, "c2_setup", "k1_forced_block")
    return setup.get("requested") if isinstance(setup, dict) else setup


def class_tail(name: Any) -> Any:
    return str(name).rsplit(".", 1)[-1] if isinstance(name, str) else name


def las_settings_of(row: RowInput) -> Any:
    return dig(row.result, "controller_meta", "liftoff_approach_slow", "settings")


def k5_row_problems(row: RowInput) -> list[str]:
    """K-5: ref settings b0, cand P5r4 (other fields equal), ``c2_setup.las_candidate``."""
    spec = row.spec
    settings = las_settings_of(row)
    want = B0_VALUES if spec.arm == ARM_REF else P5R4_VALUES
    if not isinstance(settings, dict):
        return ["controller_meta.liftoff_approach_slow.settings missing"]
    problems = [f"liftoff_approach_slow.{k} {settings.get(k)!r} != {v!r}"
                for k, v in want.items() if settings.get(k) != v]
    requested = dig(row.result, "c2_setup", "las_candidate", "requested")
    if requested != ARM_CANDIDATE[spec.arm]:
        problems.append(f"c2_setup.las_candidate.requested {plain(requested)!r} != "
                        f"{ARM_CANDIDATE[spec.arm]!r}")
    applied = dig(row.result, "c2_setup", "las_candidate", "settings")
    if applied != settings:
        problems.append("c2_setup.las_candidate.settings != controller_meta settings")
    return problems


def pair_settings_problems(rows: dict[str, RowInput]) -> list[str]:
    """K-5: a pair's LAS-b settings differ only in the two P5r4 fields."""
    problems = []
    for ref_id, cand_id in PAIRS:
        ref, cand = las_settings_of(rows[ref_id]), las_settings_of(rows[cand_id])
        if not isinstance(ref, dict) or not isinstance(cand, dict):
            continue
        other = sorted(k for k in set(ref) | set(cand)
                       if k not in ("light_leg_fraction_of_F_min", "end_ramp_periods")
                       and ref.get(k) != cand.get(k))
        if other:
            problems.append(f"{ref_id}/{cand_id}: LAS-b settings differ in {other}")
    return problems


def k6_row_problems(inputs: JudgeInputs, row: RowInput) -> list[str]:
    """K-6: threads 4, PASSIVE, hull fast + DLL + no fallback, pool = plan, affinity,
    power throttling off (copied K-3 / K-4 of the REM judge)."""
    result, entry = row.result or {}, row.entry or {}
    placement = result.get("placement") if isinstance(result.get("placement"), dict) else {}
    problems = []
    threads = scalar(dig(result, "args", "threads"))
    if threads != THREADS or result.get("num_threads_chrono") != THREADS:
        problems.append(f"threads {threads!r} / num_threads_chrono "
                        f"{result.get('num_threads_chrono')!r} != {THREADS}")
    if entry.get("omp_wait_policy") != "PASSIVE" or placement.get("omp_wait_policy") not in (
            None, "PASSIVE"):
        problems.append(f"omp_wait_policy {entry.get('omp_wait_policy')!r} / placement "
                        f"{placement.get('omp_wait_policy')!r}")
    hull = result.get("hull_hook") if isinstance(result.get("hull_hook"), dict) else {}
    hull_want = {"mode": "fast", "requested": "fast", "fallback_reason": None,
                 "dll_sha256": DLL_SHA256}
    problems += [f"hull_hook.{k} {plain(hull.get(k, MISSING))!r} != {v!r}"
                 for k, v in hull_want.items() if hull.get(k, MISSING) != v]
    if entry.get("hull_hook_requested") != "fast" or dig(entry, "hull_hook_effective",
                                                         "mode") != "fast":
        problems.append("batch hull_hook_requested / effective not fast")
    pool, mode = entry.get("pool"), placement.get("mode")
    plan = dig(inputs.prelaunch, "batch_plan", "planned_pool", row.spec.p5k_id)
    if mode != pool or (isinstance(plan, str) and pool != plan):
        problems.append(f"placement {mode!r} / batch pool {pool!r} / plan {plain(plan)!r}")
    for key in ("affinity_ok", "power_throttling_off_ok"):
        if placement.get(key) is not True:
            problems.append(f"placement.{key} {placement.get(key)!r}")
    return problems


def pair_pool_problems(rows: dict[str, RowInput]) -> list[str]:
    problems = []
    for ref_id, cand_id in PAIRS:
        modes = {key: dig(rows[key].result, "placement", "mode") for key in (ref_id, cand_id)
                 if not rows[key].is_missing}
        if len({plain(m) for m in modes.values()}) > 1:
            problems.append(f"pool kinds differ in {ref_id}/{cand_id}: {plain(modes)}")
    return problems


def k7_row_problems(row: RowInput) -> list[str]:
    """K-7: fixed values, the row's duration / mass scale, ``--las-candidate``."""
    spec, args = row.spec, dig(row.result, "args")
    args = args if isinstance(args, dict) else {}
    want = {**FIXED_ARGS, "duration": spec.duration_s, "las_candidate": ARM_CANDIDATE[spec.arm]}
    problems = [f"args.{k} {plain(scalar(args.get(k, MISSING)))!r} != {v!r}"
                for k, v in want.items() if scalar(args.get(k, MISSING)) != v]
    mass = scalar(args.get("mass_scale", dig(row.result, "mass_scale")))
    if isinstance(mass, dict):
        mass = mass.get("scale", mass.get("mass_scale", MISSING))
    if mass != spec.mass_scale:
        problems.append(f"mass_scale {plain(mass)!r} != {spec.mass_scale!r}")
    _, values = option_values(argv_of(row) or [], (CANDIDATE_OPTION,))
    if values.get(CANDIDATE_OPTION) != ARM_CANDIDATE[spec.arm]:
        problems.append(f"argv {CANDIDATE_OPTION} {values.get(CANDIDATE_OPTION)!r} != "
                        f"{ARM_CANDIDATE[spec.arm]!r}")
    return problems


def pair_argv_problems(rows: dict[str, RowInput]) -> list[str]:
    """K-7: a pair's argv differ in ``--case`` and ``--las-candidate`` only."""
    problems = []
    for ref_id, cand_id in PAIRS:
        ref_argv, cand_argv = argv_of(rows[ref_id]), argv_of(rows[cand_id])
        if rows[ref_id].is_missing or rows[cand_id].is_missing:
            continue
        if ref_argv is None or cand_argv is None:
            problems.append(f"{ref_id}/{cand_id}: argv missing")
            continue
        rest_ref, _ = option_values(ref_argv, (CASE_OPTION, CANDIDATE_OPTION))
        rest_cand, _ = option_values(cand_argv, (CASE_OPTION, CANDIDATE_OPTION))
        if rest_ref != rest_cand:
            problems.append(f"{ref_id}/{cand_id}: argv differ beyond {CASE_OPTION} and "
                            f"{CANDIDATE_OPTION}")
    return problems


def per_row_check(check_id: str, rows: dict[str, RowInput],
                  problems_of: Callable[[RowInput], list[str]]) -> dict[str, Any]:
    found = {key: problems_of(row) for key, row in rows.items() if not row.is_missing}
    return check(check_id, all(not p for p in found.values()),
                 rows={k: v for k, v in found.items() if v}, checked=sorted(found))


def identity_checks(inputs: JudgeInputs, analyses: dict[str, RowAnalysis]) -> list[dict]:
    rows = inputs.rows
    shared = k1_shared(inputs)
    shared["allowed"] = dig(inputs.prelaunch, "git_status", "allowed") or []
    k1 = per_row_check("K-1", rows, lambda r: k1_row_problems(r, shared))
    is_shared_ok = (shared["code_diff_quiet_now"] is True
                    and shared["code_diff_quiet_postrun"] is True
                    and shared["prelaunch_status_ok"] is True
                    and shared["postrun_status_ok"] is True)
    k1.update(shared=plain(shared), ok=k1["ok"] and is_shared_ok)
    k2 = per_row_check("K-2", rows, lambda r: k2_row_problems(inputs, r))
    k2_batch = k2_batch_problems(inputs)
    k2.update(batch_problems=k2_batch, ok=k2["ok"] and not k2_batch)
    k3 = per_row_check("K-3", rows, k3_row_problems)
    k4 = per_row_check("K-4", rows, lambda r: k4_row_problems(r, analyses[r.spec.p5k_id]))
    k5 = per_row_check("K-5", rows, k5_row_problems)
    k5_pairs = pair_settings_problems(rows)
    k5.update(pair_problems=k5_pairs, ok=k5["ok"] and not k5_pairs)
    k6 = per_row_check("K-6", rows, lambda r: k6_row_problems(inputs, r))
    is_mixed = inputs.batch.get("mixed_hull_mode")
    k6_pairs = pair_pool_problems(rows)
    k6.update(mixed_hull_mode=is_mixed, pair_pools=k6_pairs,
              ok=k6["ok"] and is_mixed is False and not k6_pairs)
    k7 = per_row_check("K-7", rows, k7_row_problems)
    k7_pairs = pair_argv_problems(rows)
    k7.update(pair_problems=k7_pairs, ok=k7["ok"] and not k7_pairs)
    k8 = per_row_check("K-8", rows, lambda r: k8_row_problems(analyses[r.spec.p5k_id]))
    mismatches = [key for key, row in rows.items()
                  if bool(missing_reasons_of(row.result, row.entry)) != row.is_missing
                  and "batch.json missing or unreadable" not in row.missing_reasons]
    k9 = check("K-9", not mismatches, mismatches=mismatches,
               missing={k: r.missing_reasons for k, r in rows.items() if r.is_missing})
    return [check_k0(inputs), k1, k2, k3, k4, k5, k6, k7, k8, k9]


# ================================================================ 6.3 values of one row
def numbers(value: Any) -> list[float]:
    return [float(v) for v in value if is_number(v)] if isinstance(value, list) else []


FORCE_AFTER_PATH = ("p3b", "P3-3_leg_force", "F_min_after_N")
FORCE_TRANSIENT_PATH = ("p3b", "P3-3_leg_force", "F_min_transient_N")
STROKE_PATH = ("p3b", "P3-5_clearance_stroke", "s_motor_max_m")


def leg_extreme(result: dict[str, Any], path: tuple, pick) -> tuple[float | None, bool]:
    """rev2 RV2-2 5: (min / max over the legs, key present); a non-list value or one leg that
    is not a number makes the value None."""
    value = dig(result, *path)
    if value is MISSING:
        return None, False
    if not isinstance(value, list) or not value or not all(is_number(v) for v in value):
        return None, True
    return float(pick(value)), True


def force_after_N(result: dict[str, Any]) -> float | None:
    return leg_extreme(result, FORCE_AFTER_PATH, min)[0]


def force_transient_N(result: dict[str, Any]) -> float | None:
    return leg_extreme(result, FORCE_TRANSIENT_PATH, min)[0]


def stroke_max_m(result: dict[str, Any]) -> float | None:
    return leg_extreme(result, STROKE_PATH, max)[0]


def force_record(result: dict[str, Any]) -> dict[str, Any]:
    """rev2 RV2-3: the two force minima, ``no_departure`` (departed false and both keys
    absent: values None, judged) or ``undecidable`` (a key absent otherwise: CC-F and
    G-2'C only)."""
    after, has_after = leg_extreme(result, FORCE_AFTER_PATH, min)
    transient, has_transient = leg_extreme(result, FORCE_TRANSIENT_PATH, min)
    departed = dig(result, "p3b", "departure", "departed")
    out = {"after_N": after, "transient_N": transient, "no_departure": False,
           "undecidable": False}
    if has_after and has_transient:
        return out
    if departed is False and not has_after and not has_transient:
        return {**out, "no_departure": True}
    return {**out, "undecidable": True}


def ready_after_loop_s(result: dict[str, Any]) -> float | None:
    value = dig(result, "p3b", "P3-6_ready", "t_ready_after_loop_start_s")
    return float(value) if is_number(value) else None


def phases_of(result: dict[str, Any]) -> list[tuple[float, str]]:
    out = []
    for phase in result.get("phases") or []:
        if isinstance(phase, dict) and is_number(phase.get("t_s")):
            out.append((float(phase["t_s"]), str(phase.get("phase"))))
    return out


def fault_warn_names(result: dict[str, Any]) -> set[str]:
    return {event_base_name(n) for _, n in events_of(result)
            if event_base_name(n).startswith(NEW_EVENT_PREFIXES)}


def las_meta(result: dict[str, Any]) -> dict[str, Any]:
    meta = dig(result, "controller_meta", "liftoff_approach_slow")
    return meta if isinstance(meta, dict) else {}


def anchor_path_of(bias_events: int, anchor_events: int) -> str:
    """rev1 RV1-1: (1) ``INFO_CLEARANCE_BIAS``, (2) ``INFO_LOC_CLEARANCE_ANCHOR``, both
    ``1+2``, neither (3)."""
    if bias_events and anchor_events:
        return PATH_BOTH
    if bias_events:
        return PATH_CORNER_BIAS
    if anchor_events:
        return PATH_ANCHOR
    return PATH_NONE


def anchor_arm(result: dict[str, Any]) -> dict[str, Any]:
    """rev1 RV1-1 record of one arm from ``events`` and ``controller_meta.soil`` (t_P first
    from the decision of the first LOC period, else t_P last when there is one LOC). The
    per-LOC ``loc_corrections.locs`` of run_S9 is copied as a record only."""
    missing = []
    events = result.get("events")
    if not isinstance(events, list):
        missing.append("events")
    pairs = events_of(result)
    names = [event_base_name(name) for _, name in pairs]
    loc_times = [t for t, name in pairs if event_base_name(name) == LOC_EVENT]
    soil = dig(result, "controller_meta", "soil")
    if not isinstance(soil, dict):
        missing.append("controller_meta.soil")
        soil = {}
    values = {}
    for name, key in (("t_P_last_s", "t_P_s"), ("raw_bias_m", "bias_corner_raw_m"),
                      ("applied_bias_m", "bias_corner_m"),
                      ("loc_anchor_bias_mm", "loc_anchor_bias_mm"),
                      ("loc_anchor_applied", "loc_anchor_applied")):
        if key not in soil:
            missing.append(f"controller_meta.soil.{key}")
        values[name] = soil.get(key)
    path = anchor_path_of(names.count(BIAS_EVENT), names.count(ANCHOR_EVENT))
    t_p_first = first_t_p(result, loc_times, values["t_P_last_s"])
    if t_p_first is None and loc_times:
        missing.append("t_P first (decision of the first LOC period)")
    applied = numbers(values["applied_bias_m"])
    agree = None
    if isinstance(values["loc_anchor_applied"], bool):
        agree = ((path in (PATH_ANCHOR, PATH_BOTH)) == values["loc_anchor_applied"]) and (
            path == PATH_NONE or any(v != 0.0 for v in applied))
    t_l_first = loc_times[0] if loc_times else None
    t_l_last = loc_times[-1] if loc_times else None
    return {"anchor_path": path, "loc_count": len(loc_times), **plain(values),
            "t_L_first_s": t_l_first, "t_L_last_s": t_l_last, "t_P_first_s": t_p_first,
            "n_L_first": period_of(t_l_first), "n_L_last": period_of(t_l_last),
            "n_P_first": period_of(t_p_first), "n_P_last": period_of(values["t_P_last_s"])
            if is_number(values["t_P_last_s"]) else None,
            "anchor_meta_agree": agree, "run_s9_locs": plain(dig(result, "loc_corrections",
                                                                 "locs")),
            "ANCHOR_RECORD_MISSING": missing}


def first_t_p(result: dict[str, Any], loc_times: list[float], t_p_last: Any) -> float | None:
    decisions = dig(result, "controller_meta", "slope_clearance_margin", "order_gate",
                    "decisions")
    if loc_times and isinstance(decisions, list):
        first_n = period_of(loc_times[0])
        for decision in decisions:
            if isinstance(decision, dict) and is_number(decision.get("t_loc_s")) and period_of(
                    decision["t_loc_s"]) == first_n and is_number(decision.get("t_P_s")):
                return float(decision["t_P_s"])
    if len(loc_times) == 1 and is_number(t_p_last):
        return float(t_p_last)
    return None


def anchor_pair(ref: dict[str, Any], cand: dict[str, Any]) -> dict[str, Any]:
    """rev1 RV1-2: FLAG ``ANCHOR_SAMPLE_SHIFT`` (True / False / None) of one pair."""
    arms = {ARM_REF: anchor_arm(ref), ARM_CAND: anchor_arm(cand)}
    uses_anchor = any(arm["anchor_path"] in ANCHOR_PATHS for arm in arms.values())
    deltas = {}
    for slot in ("n_P_first", "n_P_last", "n_L_first", "n_L_last"):
        a, b = arms[ARM_REF][slot], arms[ARM_CAND][slot]
        deltas[slot] = None if a is None or b is None else b - a
    compared = [deltas[s] for s in ("n_P_first", "n_P_last") if deltas[s] is not None]
    flag = False if not uses_anchor else (None if not compared else any(d != 0
                                                                        for d in compared))
    missing = sorted({m for arm in arms.values() for m in arm["ANCHOR_RECORD_MISSING"]})
    return {"ref": arms[ARM_REF], "cand": arms[ARM_CAND], "delta": deltas,
            "ANCHOR_SAMPLE_SHIFT": flag, "ANCHOR_RECORD_MISSING": missing}


# ================================================================ 6.3 pairs
def item_violations(ref: dict[str, Any], cand: dict[str, Any]) -> tuple[list[str], list[str],
                                                                         list[str]]:
    """CC-2 (a): (violations, LATE_LOC_P32 flags, missing keys) over :data:`ITEM_KEYS`."""
    ref_checks = dig(ref, "p3b", "checks")
    cand_checks = dig(cand, "p3b", "checks")
    missing = [f"{side} {key}" for side, checks in (("ref", ref_checks), ("cand", cand_checks))
               for key in ITEM_KEYS if not isinstance(checks, dict) or key not in checks]
    if missing:
        return [], [], missing
    violations, flags = [], []
    for key in ITEM_KEYS:
        if ref_checks[key] is True and cand_checks[key] is not True:
            is_late = key == "P3-2_within" and any(cand_checks.get(k) is True
                                                   for k in LATE_LOC_KEYS)
            (flags if is_late else violations).append(f"{key} True -> {cand_checks[key]!r}")
    return violations, flags, []


def phase_violations(ref: dict[str, Any], cand: dict[str, Any]) -> list[str]:
    """CC-2 (b): ref ends ready -> cand ends ready; ref has a first READY -> cand has one."""
    ref_phases, cand_phases = phases_of(ref), phases_of(cand)
    out = []
    if ref_phases and ref_phases[-1][1] == READY_PHASE and (
            not cand_phases or cand_phases[-1][1] != READY_PHASE):
        out.append(f"last phase ready -> {cand_phases[-1][1] if cand_phases else None!r}")
    if any(p == READY_PHASE for _, p in ref_phases) and not any(
            p == READY_PHASE for _, p in cand_phases):
        out.append("first READY -> none")
    return out


def ck1c(ref_analysis: RowAnalysis, cand_analysis: RowAnalysis) -> dict[str, Any]:
    ref_l1 = ref_analysis.l1
    cand_applied = any(d.is_applied for d in cand_analysis.r4_decisions)
    ref_applied = any(d.is_applied for d in ref_analysis.r4_decisions)
    cand_l1 = cand_analysis.l1
    return {"R4_LOST": ref_l1 is not None and ref_l1.is_applied and not cand_applied,
            "R4_GAINED": not ref_applied and cand_applied,
            "ref_L1": None if ref_l1 is None else ref_l1.to_record(),
            "cand_L1": None if cand_l1 is None else cand_l1.to_record(),
            "THIN_MARGIN": cand_l1 is not None and cand_l1.dP is not None
            and cand_l1.dP <= THIN_MARGIN_PERIODS}


def whole_pair_missing(ref: dict[str, Any], cand: dict[str, Any]) -> list[str]:
    """rev2 RV2-4: absences that make the whole pair undecidable (an I key, ``phases``,
    ``p3b.P3-6_ready``) in either row."""
    missing = item_violations(ref, cand)[2]
    for side, result in (("ref", ref), ("cand", cand)):
        if not isinstance(result.get("phases"), list):
            missing.append(f"{side} phases")
        if dig(result, "p3b", "P3-6_ready") is MISSING:
            missing.append(f"{side} p3b.P3-6_ready")
    return missing


def ccf_state(f_ref: float | None, f_cand: float | None) -> tuple[str, bool]:
    """rev2 RV2-2 1: (scope, violation) of CC-F; a ref None is outside (``ref_none``)."""
    if f_ref is None:
        return RANGE_OUT_REF_NONE, False
    if is_below(f_ref, CC_FLOOR_N):
        return RANGE_OUT, False
    return RANGE_IN, f_cand is None or is_below(f_cand, CC_FLOOR_N)


def ccs_state(s_ref: float | None, s_cand: float | None) -> tuple[str, bool]:
    """rev2 RV2-2 2: (scope, violation) of CC-S; ref None (both None included) is outside,
    cand None with a ref value is a violation."""
    if s_ref is None:
        return RANGE_OUT_REF_NONE, False
    if s_cand is None:
        return RANGE_IN, True
    return RANGE_IN, is_above(s_cand - s_ref, STROKE_LIMIT_M)


def pair_record(ref_row: RowInput, cand_row: RowInput, analyses: dict[str, RowAnalysis]
                ) -> dict[str, Any]:
    """Every 6.3 quantity of one pair; ``whole_missing`` makes the pair undecidable for every
    criterion, ``undecided`` names the criteria a missing field blocks (rev2 RV2-3 / RV2-4)."""
    ref, cand = ref_row.result or {}, cand_row.result or {}
    violations, late_flags, _ = item_violations(ref, cand)
    cand_las = las_meta(cand)
    ramp = cand_las.get("ramp") if isinstance(cand_las.get("ramp"), dict) else {}
    is_started = cand_las.get("start_s") is not None
    has_commands = ref_row.commands is not None and cand_row.commands is not None
    is_changed = has_commands and ref_row.commands.sha256 != cand_row.commands.sha256
    extra = sorted(fault_warn_names(cand) - fault_warn_names(ref))
    ref_force, cand_force = force_record(ref), force_record(cand)
    s_ref, has_s_ref = leg_extreme(ref, STROKE_PATH, max)
    s_cand, has_s_cand = leg_extreme(cand, STROKE_PATH, max)
    undecided = []
    if ref_force["undecidable"] or cand_force["undecidable"]:
        undecided.append("CC-F")
    if cand_force["undecidable"]:
        undecided.append("G-2'C")
    if not (has_s_ref and has_s_cand):
        undecided.append("CC-S")
    f_ref, f_cand = ref_force["after_N"], cand_force["after_N"]
    ccf_scope, ccf_violation = ccf_state(f_ref, f_cand)
    ccs_scope, ccs_violation = ccs_state(s_ref, s_cand)
    g2pc_violation = (f_cand is None or is_below(f_cand, G2PC_FLOOR_N)
                      or cand_force["transient_N"] is None
                      or is_below(cand_force["transient_N"], G2PC_FLOOR_N))
    r_ref, r_cand = ready_after_loop_s(ref), ready_after_loop_s(cand)
    return {
        "ref": ref_row.spec.p5k_id, "cand": cand_row.spec.p5k_id,
        "whole_missing": whole_pair_missing(ref, cand), "undecided": undecided,
        "items": violations, "LATE_LOC_P32": late_flags,
        "phases": phase_violations(ref, cand),
        "events": [f"new events {extra}"] if extra else [],
        "F_after_ref_N": f_ref, "F_after_cand_N": f_cand,
        "F_transient_cand_N": cand_force["transient_N"],
        "no_departure": {"ref": ref_force["no_departure"], "cand": cand_force["no_departure"]},
        "CC-F_scope": ccf_scope, "CC-F_violation": ccf_violation,
        "G-2'C_violation": g2pc_violation,
        "s_max_ref_m": s_ref, "s_max_cand_m": s_cand,
        "stroke_increase_m": None if s_ref is None or s_cand is None else s_cand - s_ref,
        "CC-S_scope": ccs_scope, "CC-S_violation": ccs_violation,
        "ready_ref_s": r_ref, "ready_cand_s": r_cand,
        "dt_s": None if r_ref is None or r_cand is None else r_cand - r_ref,
        "commands_present": has_commands, "changed": is_changed,
        "cand_las_started": is_started,
        "ramp_periods_applied": ramp.get("periods_applied"),
        "PAIR_DIVERGE": has_commands and not is_started and is_changed,
        "PAIR_CMD_DIFF": is_changed and is_started,
        "CK1": ck1c(analyses[ref_row.spec.p5k_id], analyses[cand_row.spec.p5k_id]),
        "window_short": {side: dig(row.result, "p3b", "checks", WINDOW_SHORT_KEY)
                         for side, row in (("ref", ref_row), ("cand", cand_row))},
        "first_command_difference_period": first_difference(ref_row, cand_row),
        "record": {"cand_las": plain({k: cand_las.get(k) for k in
                                      ("start_s", "end_s", "end_reason", "active_periods")}),
                   "ramp": plain(ramp),
                   "anchor": anchor_pair(ref, cand)},
    }


def first_difference(ref_row: RowInput, cand_row: RowInput) -> int | None:
    if ref_row.commands is None or cand_row.commands is None:
        return None
    for t_a, t_b, row_a, row_b in zip(ref_row.commands.t_s, cand_row.commands.t_s,
                                      ref_row.commands.rows, cand_row.commands.rows,
                                      strict=False):
        if t_a != t_b or row_a != row_b:
            return period_of(t_a)
    return None


def criteria_6_3(inputs: JudgeInputs, analyses: dict[str, RowAnalysis]) -> dict[str, Any]:
    """CC-2, CC-F, G-2'C, CC-S, CK-1C, CC-R and the observation requirement; a missing row or
    a whole-pair absence opens every criterion, a field absence only its criterion (rev2
    RV2-3 / RV2-4, 16.6 layer 1)."""
    rows = inputs.rows
    pairs, undecidable = {}, []
    for ref_id, cand_id in PAIRS:
        if rows[ref_id].is_missing or rows[cand_id].is_missing:
            undecidable.append(f"{ref_id}/{cand_id}: row missing")
            continue
        pair = pair_record(rows[ref_id], rows[cand_id], analyses)
        if pair["whole_missing"]:
            undecidable.append(f"{ref_id}/{cand_id}: whole pair, missing {pair['whole_missing']}")
        undecidable += [f"{ref_id}/{cand_id} {name}: field missing" for name in pair["undecided"]]
        pair["ANCHOR_SAMPLE_SHIFT"] = pair["record"]["anchor"]["ANCHOR_SAMPLE_SHIFT"]
        pairs[f"{ref_id}/{cand_id}"] = pair
    is_open = any(text.endswith("row missing") or "whole pair" in text for text in undecidable)

    def make(items, name, **extra):
        open_pairs = sorted(k for k, p in pairs.items() if name in p["undecided"])
        ok = None if (is_open or open_pairs) else not items
        return {"ok": ok, "status": status_of(ok), "items": items, "count": len(items),
                "undecidable_pairs": open_pairs, **extra}

    def ref_none(name):
        return sorted(k for k, p in pairs.items() if p[f"{name}_scope"] == RANGE_OUT_REF_NONE)

    cc2 = [f"{k}: {p['items'] + p['phases'] + p['events']}" for k, p in pairs.items()
           if p["items"] or p["phases"] or p["events"]]
    ccf = [f"{k}: ref {p['F_after_ref_N']} -> {p['F_after_cand_N']}" for k, p in pairs.items()
           if "CC-F" not in p["undecided"] and p["CC-F_violation"]]
    g2pc = [f"{k}: after {p['F_after_cand_N']} transient {p['F_transient_cand_N']}"
            for k, p in pairs.items() if p["cand"] in G2PC_ROWS
            and "G-2'C" not in p["undecided"] and p["G-2'C_violation"]]
    g2pc_open = sorted(k for k, p in pairs.items()
                       if p["cand"] in G2PC_ROWS and "G-2'C" in p["undecided"])
    ccs = [f"{k}: {p['s_max_ref_m']} -> {p['s_max_cand_m']}" for k, p in pairs.items()
           if "CC-S" not in p["undecided"] and p["CC-S_violation"]]
    ck1 = [f"{k}: R4_LOST" for k, p in pairs.items()
           if (p["ref"], p["cand"]) in CK1C_PAIRS and p["CK1"]["R4_LOST"]]
    g2pc_ok = None if (is_open or g2pc_open) else not g2pc
    out = {"CC-2": make(cc2, "CC-2"), "CC-F": make(ccf, "CC-F", ref_none=ref_none("CC-F")),
           "G-2'C": {"ok": g2pc_ok, "status": status_of(g2pc_ok), "items": g2pc,
                     "count": len(g2pc), "undecidable_pairs": g2pc_open},
           "CC-S": make(ccs, "CC-S", ref_none=ref_none("CC-S")), "CK-1C": make(ck1, "CK-1C")}
    population_pairs = {k: p for k, p in pairs.items() if not p["whole_missing"]}
    out["CC-R"] = ready_criterion(population_pairs, is_open)
    out["observation"] = observation_requirement(pairs, is_open)
    violating = {k: p for k, p in pairs.items() if p["items"] or p["CC-S_violation"]}
    return {"criteria": out, "pairs": pairs, "undecidable": undecidable,
            "anchor_effect_possible": sorted(k for k, p in violating.items()
                                             if p["ANCHOR_SAMPLE_SHIFT"] is True),
            "anchor_effect_unknown": sorted(k for k, p in violating.items()
                                            if p["ANCHOR_SAMPLE_SHIFT"] is None),
            "no_departure": sorted(k for k, p in pairs.items()
                                   if True in p["no_departure"].values()),
            "PAIR_DIVERGE": sorted(k for k, p in pairs.items() if p["PAIR_DIVERGE"]),
            "PAIR_CMD_DIFF": sorted(k for k, p in pairs.items() if p["PAIR_CMD_DIFF"]),
            "flags": {"R4_GAINED": sorted(k for k, p in pairs.items() if p["CK1"]["R4_GAINED"]),
                      "THIN_MARGIN": sorted(k for k, p in pairs.items()
                                            if p["CK1"]["THIN_MARGIN"]),
                      "LATE_LOC_P32": sorted(k for k, p in pairs.items() if p["LATE_LOC_P32"]),
                      "ANCHOR_SAMPLE_SHIFT": sorted(k for k, p in pairs.items()
                                                    if p["ANCHOR_SAMPLE_SHIFT"] is True),
                      "ANCHOR_SAMPLE_SHIFT_none": sorted(
                          k for k, p in pairs.items() if p["ANCHOR_SAMPLE_SHIFT"] is None),
                      "ANCHOR_RECORD_MISSING": sorted(
                          k for k, p in pairs.items()
                          if p["record"]["anchor"]["ANCHOR_RECORD_MISSING"]),
                      "P3-4_window_short": sorted(k for k, p in pairs.items()
                                                  if True in p["window_short"].values())},
            "p5r4_not_acting": sorted(k for k, p in pairs.items()
                                      if not k.startswith("A") and not p["cand_las_started"])}


def ready_criterion(pairs: dict[str, dict], is_open: bool) -> dict[str, Any]:
    """CC-R over the changed pairs with both READY values (empty population: undecidable)."""
    changed = [k for k, p in pairs.items() if p["changed"]]
    values = [pairs[k]["dt_s"] for k in changed if pairs[k]["dt_s"] is not None]
    out = {"changed": len(changed), "population": len(values), "median_s": None, "max_s": None}
    if not changed:
        ok = None if is_open else True
        return {**out, "ok": ok, "status": status_of(ok), "basis": "no changed pair",
                "items": [], "count": 0}
    if not values:
        return {**out, "ok": None, "status": STATUS_UNDECIDABLE,
                "basis": "changed pairs but empty population", "items": [], "count": 0}
    median, maximum = statistics.median(values), max(values)
    items = []
    if is_above(median, READY_MEDIAN_LIMIT_S):
        items.append(f"median {median}")
    if is_above(maximum, READY_MAX_LIMIT_S):
        items.append(f"max {maximum}")
    ok = None if is_open else not items
    return {**out, "median_s": median, "max_s": maximum, "ok": ok, "status": status_of(ok),
            "basis": "population", "items": items, "count": len(items)}


def observation_requirement(pairs: dict[str, dict], is_open: bool) -> dict[str, Any]:
    """6.3: at least one A pair whose cand LAS-b started and whose ramp acted
    (``NO_P5R4_OBSERVATION`` otherwise: undecidable)."""
    observed = sorted(k for k, p in pairs.items() if k.startswith("A") and p["cand_las_started"]
                      and is_number(p["ramp_periods_applied"]) and p["ramp_periods_applied"] >= 1)
    ok = True if observed else None
    return {"ok": ok, "status": status_of(ok), "observed_pairs": observed,
            "reason": None if observed else "NO_P5R4_OBSERVATION", "items": [],
            "count": len(observed), "open_rows": is_open}


def bt_c(inputs: JudgeInputs) -> dict[str, Any]:
    """BT-C (4.4): C1 commands = REM R7, C3 up to t <= 128 s = REM R8 (contents)."""
    out = {}
    for row_id, (_relative, file_sha, t_end_s) in BT_C_REFERENCES.items():
        reference = inputs.bt_c_references.get(row_id) or {}
        digest = reference.get("digest")
        row = inputs.rows[row_id]
        problems = []
        if reference.get("file_sha256") != file_sha or digest is None:
            problems.append(f"REM reference {reference.get('path')} sha256 "
                            f"{reference.get('file_sha256')} != {file_sha}")
        if row.commands is None:
            problems.append("row commands missing")
        is_equal = (not problems and row.commands.prefix_sha256(t_end_s)
                    == digest.prefix_sha256(t_end_s))
        out[row_id] = {"t_end_s": t_end_s, "equal": is_equal if not problems else None,
                       "problems": problems}
    is_mismatch = any(record["equal"] is False for record in out.values())
    is_open = any(record["equal"] is None for record in out.values())
    return {"rows": out, "ok": None if is_open and not is_mismatch else not is_mismatch}


# ================================================================ grade (8, 16.6)
def judge(inputs: JudgeInputs) -> dict[str, Any]:
    analyses = {key: analyze_row(row) for key, row in inputs.rows.items()}
    identity = identity_checks(inputs, analyses)
    bits = bt_c(inputs)
    result = criteria_6_3(inputs, analyses)
    reasons = []
    if any(c["ok"] is False for c in identity):
        reasons.append("stop: K " + ",".join(c["id"] for c in identity if c["ok"] is False))
    if result["PAIR_DIVERGE"]:
        reasons.append(f"stop: PAIR_DIVERGE {result['PAIR_DIVERGE']}")
    if bits["ok"] is False:
        reasons.append("stop: BT-C (S-7: Chrono judgement stops, pair results for information)")
    statuses = [c["status"] for c in result["criteria"].values()]
    if bits["ok"] is None:
        statuses.append(STATUS_UNDECIDABLE)
        result["undecidable"].append("BT-C not evaluated (a reference or row file missing)")
    criteria_status = worst_status(statuses)
    status = STATUS_STOP if reasons else criteria_status
    reasons += [f"{name}: {c['status']}" for name, c in result["criteria"].items()
                if c["status"] != STATUS_PASS]
    return {"provisional": True, "k10": None, "status": status, "grade": GRADES[status],
            "criteria_status": criteria_status, "reasons": reasons, "identity": identity,
            "BT-C": bits, **result,
            "rows": {key: {"p5k_id": key, "case": row.case, "arm": row.spec.arm,
                           "missing_reasons": row.missing_reasons,
                           "rerun_of": dig(row.entry, "rerun_of") if row.entry else None,
                           "decisions": [d.to_record() for d in analyses[key].decisions or []],
                           "loc_periods": analyses[key].loc_periods,
                           "mode_starts": [{"n": n, "t_s": t, "source": s}
                                           for n, t, s in analyses[key].mode_starts]}
                     for key, row in inputs.rows.items()}}


# ================================================================ fields (16.2 (나))
def progress_rc(batch_dir: Path) -> dict[str, Any]:
    """END lines of ``progress.log``: case -> rc (as text)."""
    path = batch_dir / "progress.log"
    out = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "END":
            rc = next((p.split("=", 1)[1] for p in parts if p.startswith("rc=")), None)
            out[parts[1]] = rc
    return out


def fields_document(batch_dir: Path) -> dict[str, Any]:
    """Presence of every row file and key path the judge reads (never a value)."""
    batch = read_json(batch_dir / "batch.json")
    entries = entries_by_id(batch or {})
    rc = progress_rc(batch_dir)
    rows = {}
    for spec in ROW_SPECS:
        entry = entries.get(spec.p5k_id)
        case = None if entry is None else str(entry.get("case"))
        folder = batch_dir / (case or "<no case>")
        result = read_json(folder / "result.json") if case else None
        commands = read_commands(folder / "controller_commands.npz") if case else None
        is_departed = dig(result, "p3b", "departure", "departed") is not False
        missing = [".".join(map(str, path)) for path in FIELD_PATHS
                   if (result is None or dig(result, *path) is MISSING)
                   and (is_departed or path not in AFTER_DEPARTURE_PATHS)]
        entry_missing = [name for name in BATCH_ENTRY_FIELDS
                         if entry is None or name not in entry]
        checks_missing = [key for key in ITEM_KEYS
                          if not isinstance(dig(result, "p3b", "checks"), dict)
                          or key not in dig(result, "p3b", "checks")]
        rows[spec.p5k_id] = {
            "case_present": case is not None, "progress_end_rc0": rc.get(case) == "0",
            "result_json": result is not None, "commands_npz": commands is not None,
            "missing_result_fields": missing, "missing_batch_fields": entry_missing,
            "missing_item_keys": checks_missing}
        rows[spec.p5k_id]["ok"] = (rows[spec.p5k_id]["case_present"]
                                   and rows[spec.p5k_id]["progress_end_rc0"]
                                   and rows[spec.p5k_id]["result_json"]
                                   and rows[spec.p5k_id]["commands_npz"]
                                   and not missing and not entry_missing and not checks_missing)
    return {"kind": "fields", "batch": batch_dir.as_posix(), "batch_json": batch is not None,
            "rows": rows, "ok": batch is not None and all(r["ok"] for r in rows.values())}


# ================================================================ CLI
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--rules-rev3", type=Path, default=None,
                        help="las_p5r4_k1_rules_rev3.md to check (next to its .sha256)")
    sub = parser.add_subparsers(dest="command", required=True)
    pre = sub.add_parser("prelaunch")
    pre.add_argument("--batch-plan", type=Path, required=True)
    pre.add_argument("--audit-report", type=Path, required=True)
    pre.add_argument("--allow-dirty", nargs="*", default=[])
    pre.add_argument("--path2-sha", nargs="*", default=[], help="NAME=SHA of path 2 scripts")
    pre.add_argument("--gs-list-sha", default=None)
    post = sub.add_parser("postrun")
    post.add_argument("--batch", type=Path, required=True)
    post.add_argument("--prelaunch", type=Path, default=None)
    jud = sub.add_parser("judge")
    jud.add_argument("--batch", type=Path, required=True)
    jud.add_argument("--expect-tool-sha", required=True)
    jud.add_argument("--prelaunch", type=Path, default=None)
    jud.add_argument("--postrun", type=Path, default=None)
    jud.add_argument("--rem-batch", type=Path, default=None)
    fld = sub.add_parser("fields")
    fld.add_argument("--batch", type=Path, required=True)
    return parser


def default_path(root: Path, name: str) -> Path:
    return root / OUT_DIR_RELATIVE / name


def parse_path2(items: list[str]) -> dict[str, str]:
    out = {}
    for item in items:
        name, separator, sha = item.partition("=")
        is_hex = all(c in "0123456789abcdefABCDEF" for c in sha)
        if not separator or not name or not is_hex or len(sha) not in (40, 64):
            raise InputError(f"--path2-sha {item!r} is not NAME=<40 hex git blob | 64 hex sha256>")
        out[name] = sha.lower()
    return out


def run_command(args: argparse.Namespace) -> tuple[dict[str, Any], Path]:
    root = args.root.resolve()
    if args.command == "prelaunch":
        doc = prelaunch_document(root, args.batch_plan, args.audit_report, args.allow_dirty,
                                 parse_path2(args.path2_sha), args.gs_list_sha)
        return doc, args.out or default_path(root, PRELAUNCH_NAME)
    if args.command == "postrun":
        prelaunch = args.prelaunch or default_path(root, PRELAUNCH_NAME)
        doc = postrun_document(root, prelaunch)
        doc["batch"] = args.batch.as_posix()
        return doc, args.out or default_path(root, POSTRUN_NAME)
    if args.command == "fields":
        return fields_document(args.batch), args.out or default_path(root, FIELDS_NAME)
    if not args.batch.is_dir():
        raise InputError(f"--batch {args.batch} is not a folder")
    inputs = load_judge_inputs(root, args.batch,
                               args.prelaunch or default_path(root, PRELAUNCH_NAME),
                               args.postrun or default_path(root, POSTRUN_NAME),
                               args.expect_tool_sha, args.rem_batch or root / DEFAULT_REM_BATCH)
    doc = judge(inputs)
    doc.update(tool=tool_record(), batch=args.batch.as_posix(), rules=sealed_rules())
    return doc, args.out or default_path(root, JUDGE_NAME)


def exit_code(doc: dict[str, Any]) -> int:
    if doc.get("kind") in ("prelaunch", "postrun"):
        return 0 if doc.get("all_ok") else 2
    if doc.get("kind") == "fields":
        return 0 if doc.get("ok") else 1
    return EXIT_CODES.get(doc.get("status"), 3)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    RULES_PATH_OVERRIDES.clear()
    if args.rules_rev3 is not None:
        RULES_PATH_OVERRIDES["las_p5r4_k1_rules_rev3.md"] = args.rules_rev3
    print("PROVISIONAL (k10 null until the path 2 recount agrees, rules 10.2)")
    try:
        doc, out_path = run_command(args)
    except InputError as exc:
        print(f"input error: {exc}")
        print(json.dumps({"tool": "las_p5r4k1_chrono_judge", "input_error": str(exc)}))
        return 2
    except (OSError, ValueError) as exc:
        print(f"tool error: {exc!r}")
        print(json.dumps({"tool": "las_p5r4k1_chrono_judge", "tool_error": repr(exc)}))
        return 3
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(plain(doc), ensure_ascii=False, indent=1), encoding="utf-8")
    code = exit_code(doc)
    print(json.dumps({"tool": "las_p5r4k1_chrono_judge", "command": args.command,
                      "status": doc.get("status", "ok" if code == 0 else "not ok"),
                      "exit": code, "out": out_path.as_posix()}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
