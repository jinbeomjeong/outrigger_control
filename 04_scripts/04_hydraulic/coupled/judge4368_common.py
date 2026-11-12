"""Shared parts of the 436.8 path 1 new judge versions (``*_4368.py``, rules rev5 R5-A1).

Rules: ``v5_resume_4368_rules.md`` (sealed 9019b405) and its revisions rev1 .. rev5. Rev5 R5-A1
makes the ``*_4368.py`` judges the path 1 of the harness bundles. Each new judge:

1. implements the rev3 / rev4 definitions of its bundle,
2. takes every input and output path as an argument,
3. discloses ``git diff --no-index <old tool> <new judge>`` (line counts) and the R5-A3 items
   D-01 .. D-25 of its bundle (:data:`DEFINITION_CHANGES`),
4. checks the sealed rules raw before judging (:func:`seal_report`; any problem is S-1),
5. follows the CLI contract: exit 0 judged without a finding, 1 a finding (stop, mismatch,
   ``판정 불가``), 2 input error, 3 internal error; the last stdout line is a JSON summary.

The judges only read; they never run a simulation.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RULES_DIR = ROOT / "06_analysis" / "02_control" / "verif_matrix"

SEALED_RULES = (
    ("v5_resume_4368_rules.md", "9019b405b7a196f28a756e7ca91f443f6241a58bd8e1eee0361483066cb19524"),
    (
        "v5_resume_4368_rules_rev1.md",
        "d9094fda104e25ac7eb7aea44d7c34d8215a839fc3771aa50b224d43082f02c7",
    ),
    (
        "v5_resume_4368_rules_rev2.md",
        "497e4614d6780c3201027b3946e3c21da05e2fefe9a3609436bc35ea664c3199",
    ),
    (
        "v5_resume_4368_rules_rev3.md",
        "dad8dfa68da7a988971f4d687706465289ec7dd95d09079c92215c64e5eae557",
    ),
    (
        "v5_resume_4368_rules_rev4.md",
        "7ea87a30b08a00263c597d42d3450dc56f68952e8d3205604cb2c5bab5dce14b",
    ),
    (
        "v5_resume_4368_rules_rev5.md",
        "452a8436c547e4da8d78205556cbb37633842d42cb98c18849cb883d827b3aca",
    ),
)
"""The original and rev1 .. rev5, compared raw (rev2 R2-9: sealed rule files are ``-text``)."""

F_MIN_N = 9414.589
"""Rules 2 / rev3 R3-C4: YAML ``control.F_min_cylinder_N`` (9.415 kN is its rounded display)."""
F_MIN_PLUS_5KN_N = F_MIN_N + 5000.0
"""Rev3 R3-C4 / R3-G6: the rigid spec-shortfall mark 14,414.589 N."""
COMPARE_EPS = 1e-9
"""Rules 7.6 / rev3 R3-D4: comparison allowance in the unit of the value."""
CONTROL_PERIOD_S = 0.1
"""Rules 2: T_s of the R8 C2 controller (integer periods n = round(t / T_s))."""

NOT_JUDGEABLE = "판정 불가"

DEFINITION_CHANGES = {
    "D-01": (
        "H-3",
        "정착 v2 기준",
        "저장 v4 재판정 파일 기준",
        "그 실행의 settle_v2 기록으로 398.3 재계산(R3-B6, R4-C2)",
    ),
    "D-02": ("H-3", "h9·연구 D의 v2", "하지 않음", "적용(R3-B6)"),
    "D-03": ("H-3", "연구 D 시작 틈 목표", "표 목표", "시작 틈 목표(R3-B7)"),
    "D-04": ("H-3", "settle_v2.status·gate 처리", "없음", "R3-B6 상태·gate 규칙"),
    "D-05": (
        "H-3",
        "연구 B 입력·셈",
        "finB2_x426b_rejudged.json, suite 필터",
        "finB2_x426b.json 키 집합, suite 이름 안 씀(R3-B2). 두 파일 키 집합이 같은지 기록",
    ),
    "D-06": ("H-3", "재사용 대조", "개수만", "meta.v5.reuse_d1 개수·d1_key 유일성(R3-B3)"),
    "D-07": (
        "H-9·H-10",
        "J1",
        "pass <-> stroke_limited_stop 이동을 실패로 셈",
        "기록(S8 예외만 실패)(R3-C3)",
    ),
    "D-08": (
        "H-9·H-10",
        "J2 F_min",
        "9.415 kN, 14.415 kN",
        "9,414.589 N, 14,414.589 N(R3-C4). 강체 사건 행은 E-3 창 뒤 1 ms 값",
    ),
    "D-09": ("H-9·H-10", "J7 이름", "첫 구획만", "수치 구획만 뗌(R3-C6)"),
    "D-10": ("H-9·H-10", "J11 None", "건너뜀", "대체 다리 줄은 판정 불가(R3-C7)"),
    "D-11": (
        "H-9·H-10",
        "J3 강체 FLAG",
        "없음",
        "경사 120 / 평지 90 s FLAG, 바닥 각 F-3(R3-C5, R4-C5)",
    ),
    "D-12": ("H-9·H-10", "P-7", "같은 키 목록 기록만", "모든 L1 줄이 같을 때만 위반(Q-S4)"),
    "D-13": ("H-9·H-10", "13.1 순서", "값만", "완전 역순만 실패(Q-S5)"),
    "D-14": ("H-9·H-10", "SA-4", "일부 항목", "일곱 항목 전부(Q-S6, F-4)"),
    "D-15": (
        "H-9·H-10",
        "H-8 FL 가드 시각",
        "없음",
        "첫 WARN_LIFT_STROKE_LIMITED:(FL 포함) 정수 주기 비교(Q-S7)",
    ),
    "D-16": ("H-9·H-10", "L-d", "1 kN·1 s만", "+ 위상 산포 정의(Q-S9)"),
    "D-17": ("H-10", "U-9 VB 28줄", "셈 없음", "S-15 줄 수만, 등급은 H-5(Q-S10)"),
    "D-18": (
        "H-5",
        "H0 ① 기준",
        "저장 p3_hash.jsonl",
        "같은 커밋 H-10 main VB 같은 (사례, ε)(R3-C1)",
    ),
    "D-19": ("H-6", "등급", "없음", "개정 8 #6 항목(R4-B6)"),
    "D-20": ("H-0", "dg3 폴더", "키 목록 항목", "기록의 extend_start_rule(R3-D1)"),
    "D-21": ("H-0", "K-0", "줄·헤더 정체성 키", ".identity.json 필드 표(R4-C4)"),
    "D-22": ("H-0", "K-6 허용", "엄격 비교", "원판 7.6 10⁻⁹(R3-D4)"),
    "D-23": (
        "H-1·H-2",
        "G-3 면제 줄 기록",
        "S2 선별 때만",
        '면제한 fup-rec 줄 전부에 "가정 경계 미성립"(R3-A1)',
    ),
    "D-24": ("H-1·H-2", "377 강등", "없음", "R5-D1"),
    "D-25": ("H-1·H-2", "READY 원점", "없음", "F-1 또는 하네스 정의(R4-C1)"),
}
"""Rev5 R5-A3: the definition-change items, numbered as the rules number them."""


class InputError(Exception):
    """A missing or unreadable input (exit code 2)."""


# ------------------------------------------------------------------------------------- reading
def read_json(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"{path}: {exc}") from exc


def read_jsonl(path: Path) -> list[dict]:
    """Lines of a run file (blank lines skipped)."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"{path}: {exc}") from exc
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------- comparison
def is_at_least(value: float | None, limit: float, eps: float = COMPARE_EPS) -> bool:
    """``value >= limit`` within the rules 7.6 allowance (None is not at least anything)."""
    return value is not None and math.isfinite(float(value)) and float(value) >= limit - eps


def is_above(value: float | None, limit: float, eps: float = COMPARE_EPS) -> bool:
    """``value > limit`` beyond the rules 7.6 allowance (``(X, X + eps]`` is not above)."""
    return value is not None and float(value) > limit + eps


def control_period_index(t_s: float) -> int:
    """Rules 2: integer controller period of a time."""
    return round(float(t_s) / CONTROL_PERIOD_S)


# --------------------------------------------------------------------------------------- seals
def seal_report(rules_dir: Path | None = None) -> dict:
    """Every sealed rule file and its ``.sha256`` first field equal the pinned value (S-1)."""
    folder = RULES_DIR if rules_dir is None else Path(rules_dir)
    revisions, problems = {}, []
    for name, pinned in SEALED_RULES:
        rules_path = folder / name
        seal_path = rules_path.with_suffix(".sha256")
        entry: dict[str, Any] = {"pinned_sha256": pinned}
        if rules_path.is_file():
            entry["file_sha256"] = file_sha256(rules_path)
            if entry["file_sha256"] != pinned:
                problems.append(f"{name}: sha256 {entry['file_sha256'][:16]} is not the sealed one")
        else:
            problems.append(f"{name} missing in {folder}")
        if seal_path.is_file():
            fields = seal_path.read_text(encoding="utf-8").split()
            entry["seal_file_sha256"] = fields[0] if fields else None
            if entry["seal_file_sha256"] != pinned:
                problems.append(f"{seal_path.name}: value is not the sealed one")
        else:
            problems.append(f"{seal_path.name} missing in {folder}")
        revisions[name] = entry
    return {
        "rules_dir": str(folder),
        "revisions": revisions,
        "problems": problems,
        "stop_S1": bool(problems),
    }


# -------------------------------------------------------------------------------- disclosures
def diff_summary(old_path: Path, new_path: Path) -> dict:
    """Rev5 R5-A1 3: ``git diff --no-index --numstat <old> <new>`` line counts and both sha256."""
    old_path, new_path = Path(old_path), Path(new_path)
    out: dict[str, Any] = {
        "old": _relative(old_path),
        "new": _relative(new_path),
        "old_sha256": file_sha256(old_path) if old_path.is_file() else None,
        "new_sha256": file_sha256(new_path),
    }
    if not old_path.is_file():
        out["note"] = "기존 도구 없음"
        return out
    completed = subprocess.run(  # noqa: S603 (fixed git arguments, read only)
        ["git", "diff", "--no-index", "--numstat", str(old_path), str(new_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    fields = completed.stdout.split()
    if len(fields) >= 2 and fields[0].isdigit():
        out["added_lines"], out["removed_lines"] = int(fields[0]), int(fields[1])
    else:
        out["note"] = f"git diff gave no numstat (exit {completed.returncode})"
    return out


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def definition_changes(numbers: tuple[str, ...]) -> list[dict]:
    """The R5-A3 rows of one judge, in the rules' words."""
    rows = []
    for number in numbers:
        bundle, item, old, new = DEFINITION_CHANGES[number]
        rows.append(
            {"id": number, "bundle": bundle, "item": item, "old_tool": old, "new_version": new}
        )
    return rows


# ------------------------------------------------------------------------------- CLI contract
def run_judge(
    judge: Callable[[Any], dict],
    args: Any,
    *,
    script: Path,
    old_tools: tuple[Path, ...],
    changes: tuple[str, ...],
) -> int:
    """Seal check, the judge, disclosures, the report file and the last-line summary.

    ``judge(args)`` returns a report with ``findings`` (list of str); findings give exit 1.
    """
    seal = seal_report(getattr(args, "rules_dir", None))
    report: dict[str, Any] = {
        "script": _relative(script),
        "script_sha256": file_sha256(script),
        "rules_seal": seal,
        "definition_changes": definition_changes(changes),
        "diff_vs_existing": [diff_summary(old, script) for old in old_tools],
    }
    if seal["stop_S1"]:
        report.update(findings=["S-1: sealed rules check failed"], exit_code=1)
        return _finish(report, args.out)
    try:
        report.update(judge(args))
    except InputError as exc:
        print(json.dumps({"exit_code": 2, "error": str(exc)}, ensure_ascii=True))
        return 2
    except Exception as exc:  # contract form; the trace goes to stderr
        print(traceback.format_exc(), file=sys.stderr)
        print(json.dumps({"exit_code": 3, "error": repr(exc)}, ensure_ascii=True))
        return 3
    report["exit_code"] = 1 if report.get("findings") else 0
    return _finish(report, args.out)


def _finish(report: dict, out: Path) -> int:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    summary = {
        "exit_code": report["exit_code"],
        "n_findings": len(report.get("findings") or []),
        "findings": (report.get("findings") or [])[:10],
        "out": str(out),
    }
    print(json.dumps(summary, ensure_ascii=True, default=str))
    return int(report["exit_code"])


def add_common_arguments(parser) -> None:
    parser.add_argument("--out", type=Path, required=True, help="report JSON")
    parser.add_argument(
        "--rules-dir",
        type=Path,
        default=RULES_DIR,
        help="folder of the sealed 436.8 rules (default: verif_matrix)",
    )
