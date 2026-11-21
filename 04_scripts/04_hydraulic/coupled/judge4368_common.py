"""Shared parts of the 436.8 path 1 new judge versions (``*_4368.py``, rules rev5 R5-A1).

Rules: ``v5_resume_4368_rules.md`` (sealed 9019b405) and its revisions rev1 .. rev25 (R4 common
block RD-2). Rev5 R5-A1 makes the ``*_4368.py`` judges the path 1 of the harness bundles. Each new
judge:

1. implements the rev3 / rev4 definitions of its bundle,
2. takes every input and output path as an argument,
3. discloses ``git diff --no-index <old tool> <new judge>`` (line counts) and the R5-A3 items
   D-01 .. D-25 of its bundle (:data:`DEFINITION_CHANGES`),
4. checks the sealed rules raw before judging (:func:`seal_report`; any problem is S-1),
5. follows the CLI contract: exit 0 judged without a finding, 1 a finding (stop, mismatch,
   ``판정 불가``), 2 input error, 3 internal error; the last stdout line is a JSON summary.

The judges only read; they never run a simulation.

R4 (436.8 harness re-judgement, R4 common block sha256 e451f067): this module also holds the
shared readings of the R4 block that more than one path 1 tool applies, so they cannot drift
apart: RD-8 ``breach_reads`` form and the RD-7 3 J-P3 input field (:func:`assess_j_p3`), rev16
R16-6 J11 with RD-10 (:func:`assess_j11`), and the RD-7 3 list notation (result file, location,
key and setting fields, sort order: :func:`list_location`, :func:`key_and_setting`,
:func:`list_sort_key`).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
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
    (
        "v5_resume_4368_rules_rev6.md",
        "809e563971ea451aba7c9d0787c660bdcab1c495af39c513c8f158e09b4fe6c9",
    ),
    (
        "v5_resume_4368_rules_rev7.md",
        "e81f7d31779b0d69a140c9d90aa4684f3c9299e84aec6af06b13d48d58631502",
    ),
    (
        "v5_resume_4368_rules_rev8.md",
        "3ecafaaf33d84bb6f34a8cef5401771832a4999e4930f3644caff56eed640e56",
    ),
    (
        "v5_resume_4368_rules_rev9.md",
        "4cf7843ce469df511d7b99c7236f0b245afae9fb4ba5ad903e1c2da823a59a6d",
    ),
    (
        "v5_resume_4368_rules_rev10.md",
        "62a0bd8dd6644f78bf37d052e884061d8c14e1cc96e2babc72a6ac0618f12c29",
    ),
    (
        "v5_resume_4368_rules_rev11.md",
        "9bac452470faf74f921aa7474b3dabad781dac1ba6c3493aff998e69e430617f",
    ),
    (
        "v5_resume_4368_rules_rev12.md",
        "78f1f99b1bb27473d6e3317c58af195cc3b477829ca1439f390aeeaf32565140",
    ),
    (
        "v5_resume_4368_rules_rev13.md",
        "383bffc1f2d920dbba5b5a8c0871786a43e983d83e2d5c1e477718257f70973b",
    ),
    (
        "v5_resume_4368_rules_rev14.md",
        "baedeab499133214804167dede4c4674f9edba4e67bd711dd6418a561f60ac3f",
    ),
    (
        "v5_resume_4368_rules_rev15.md",
        "0162561c3866412f06ef3be0b3a62434e4a9ba5a37c9003be4df2f373af545ef",
    ),
    (
        "v5_resume_4368_rules_rev16.md",
        "b38991943a565a020488d1046dd6e0b5c71276cf925715fa5ba844d8819d0683",
    ),
    (
        "v5_resume_4368_rules_rev17.md",
        "9400660e2f228c3bdfaf26b1eb36cf08a753e7ebc49fbcdedc4a8ab4e0b92422",
    ),
    (
        "v5_resume_4368_rules_rev18.md",
        "3693a69c3f04eb6c5b26556ec5997d081e38f8f6fa6a581aee66ba512d122a9e",
    ),
    (
        "v5_resume_4368_rules_rev19.md",
        "7f87b8bb091d23c1bdcd2bf356b732a77bea12c4cfc4853d0ea58f7d239c92b2",
    ),
    (
        "v5_resume_4368_rules_rev20.md",
        "615a8fbd82f4ef93f1ca76b3fb4d5c24a2e602e63a997c7c56119fcc73fb5531",
    ),
    (
        "v5_resume_4368_rules_rev21.md",
        "ecd709495f203eae1769ae42e67b5ae5bf2fb457146b558c12e46d636ed03f9a",
    ),
    (
        "v5_resume_4368_rules_rev22.md",
        "a48a81f9a71091aab40f643d48ae65ba559a5c0c629e02ef3145745a095f9328",
    ),
    (
        "v5_resume_4368_rules_rev23.md",
        "fa72e1726f87f686093e36f2f3f489d5b135df6392de6aae7fe91b8739b56f97",
    ),
    (
        "v5_resume_4368_rules_rev24.md",
        "f475cf77bc610802aa36026394cbe8dbae74745c8889ac203b53a6430e1e1e15",
    ),
    (
        "v5_resume_4368_rules_rev25.md",
        "c0b778fd3f53996a2caed37e373975afea591b3c798784843cb9e7eeaac6f233",
    ),
)
"""The original and rev1 .. rev25 (26 revisions), compared raw (rev2 R2-9: sealed rule files are
``-text``; rev7 R7-7 .. rev12 R12-6 for rev7 .. rev12; R4 common block RD-2, rev16 R16-13 and the
R4 bullets of rev17 .. rev25: the R4 harness tools check the 26 revisions)."""

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


T4H_FILE_KEY = "t4h_file"
"""Run record key with the name of the run's T4h file (``run_v5``, ``r79_sensor_screen``)."""
T4H_DIR_SUFFIX = "_t4h"
"""``<result stem>_t4h/``: the T4h folder of ``run_v5`` / ``resume_k1_steps`` / r79 outputs."""
T4H_SIBLING_DIR = "t4h"
"""``t4h/`` next to the result file: the T4h folder of ``las_t3`` runs."""
T4H_FOUND = "found"
T4H_NO_RECORD = "no_t4h_file"
T4H_STOP = "S-2"


def t4h_folders(result_path: Path, records: list[dict],
                extra_dirs: list[Path] | tuple[Path, ...] = ()) -> list[Path]:
    """Rev11 R11-2 as widened by rev12 R12-1: the folders searched for the T4h files of one
    result file (every judgement that reads a T4h).

    The runner convention folders that exist (``<stem>_t4h/``, ``t4h/``); only when none
    exists, the one given folder. A file without ``t4h_file`` records needs no folder.

    Raises:
        InputError: Two or more folders given, or one given for a result file with T4h records
            that has a convention folder (exit 2, the bundle is not judged, S-11).
    """
    extra = [Path(d) for d in extra_dirs]
    if len(extra) > 1:
        raise InputError(f"{len(extra)} --t4h-dir folders given; at most one "
                         "(rev11 R11-2 / rev12 R12-1, S-11)")
    if not any(T4H_FILE_KEY in record for record in records):
        return []
    path = Path(result_path)
    conventions = [path.with_name(f"{path.stem}{T4H_DIR_SUFFIX}"), path.parent / T4H_SIBLING_DIR]
    existing = [folder for folder in conventions if folder.is_dir()]
    if existing and extra:
        raise InputError(f"--t4h-dir {extra[0]} given but {path} has the runner convention "
                         f"folder {existing[0]} (rev11 R11-2 / rev12 R12-1, S-11)")
    return existing or extra


def locate_t4h(record: dict, folders: list[Path] | tuple[Path, ...]) -> dict:
    """Rev12 R12-1 (Q-R12-1 = A): the T4h file of one run record.

    Returns:
        ``status`` ``no_t4h_file`` (no ``t4h_file`` key: the caller's configuration rule,
        rev3 R3-C8), ``found`` (exactly one file, ``path``) or ``S-2`` (a recorded name found
        0 or 2+ times, or not a usable name: never replaced by the configuration rule).
    """
    if T4H_FILE_KEY not in record:
        return {"status": T4H_NO_RECORD, "path": None}
    name = record[T4H_FILE_KEY]
    if not isinstance(name, str) or not name:
        return {"status": T4H_STOP, "path": None,
                "reason": f"{T4H_FILE_KEY} {name!r} is not a file name (rev12 R12-1)"}
    hits = [Path(folder) / name for folder in folders if (Path(folder) / name).is_file()]
    if len(hits) != 1:
        return {"status": T4H_STOP, "path": None, "hits": [str(hit) for hit in hits],
                "reason": (f"{T4H_FILE_KEY} {name} found {len(hits)} times in "
                           f"{[str(f) for f in folders]} (rev12 R12-1, Q-R12-1 = A)")}
    return {"status": T4H_FOUND, "path": hits[0]}


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


# --------------------------------------------------------------------- R4 shared J-P3 (RD-7, RD-8)
LEGS = ("FL", "FR", "RL", "RR")
MARKER_JP3_FORM = "J-P3 입력 형식(RD-8)"
"""RD-8: the bundle gate marker of a J-P3 input form defect (both paths use this name)."""
STOP_H7 = "멈춤 H-7"
"""RD-4 / RD-7: the v5 criteria stop (J-P3 breach, J11 VB fallback leg late, H-12 locked sample)."""
STOP_LE = "L-e"
"""Rev5 R5-B3: the J11 stop of an LS setting."""

J_P3_NOT_APPLICABLE = "not_applicable"
J_P3_PASS = "pass"
J_P3_H7 = "H-7"
J_P3_NO_ROD_READING = "no_rod_reading"
J_P3_SETTING_DEFECT = "setting_defect"
J_P3_S2 = "S-2"
J_P3_INPUT_FIELD = "hydraulics_record.extend_bound_check"
"""RD-7 3: the J-P3 input of a line or run (u3 / u6 items: under ``v5``)."""


def j_p3_bound(item: dict) -> tuple[dict | None, str | None]:
    """RD-7 3 J-P3 input of one line, run or u3 / u6 item.

    The input is ``hydraulics_record.extend_bound_check`` (``v5.hydraulics_record...`` for a U-3 /
    U-6 item, whose ``v5`` block holds the plant record). When the same item also has a top-level
    ``extend_bound_check`` (r79 results copy it there), its ``breach_reads`` must equal the input's.

    Returns:
        (bound, problem): the recorded bound (None or {} = no record) and a 판정 불가 reason
        when the two ``breach_reads`` differ (else None).
    """
    v5 = item.get("v5")
    owner = v5 if isinstance(v5, dict) and "hydraulics_record" not in item else item
    record = owner.get("hydraulics_record")
    bound = record.get("extend_bound_check") if isinstance(record, dict) else None
    if "extend_bound_check" not in item:
        return bound, None
    top = item["extend_bound_check"]
    top_reads = top.get("breach_reads") if isinstance(top, dict) else None
    reads = bound.get("breach_reads") if isinstance(bound, dict) else None
    if top_reads != reads:
        return bound, (f"top-level extend_bound_check.breach_reads {top_reads!r} != "
                       f"{J_P3_INPUT_FIELD}.breach_reads {reads!r} (RD-7 3: 판정 불가)")
    return bound, None


def breach_reads_problem(bound: Any) -> str | None:
    """RD-8: ``breach_reads`` must be a list of 4 integers >= 0 (FL, FR, RL, RR); else the
    reason (the J-P3 of that line is 판정 불가, never a sum-0 pass)."""
    reads = bound.get("breach_reads") if isinstance(bound, dict) else None
    if not isinstance(reads, list) or len(reads) != len(LEGS):
        return f"breach_reads {reads!r} is not a list of {len(LEGS)} (RD-8)"
    bad = [v for v in reads if isinstance(v, bool) or not isinstance(v, int) or v < 0]
    if bad:
        return f"breach_reads {reads!r} has elements that are not integers >= 0 (RD-8)"
    return None


def _per_leg(bound: dict, name: str, index: int) -> Any:
    """R4 supplement 3-3: one leg's element of a recorded per-leg list, copied as recorded (no
    rounding, no conversion); None when it is missing, not a number or not finite."""
    values = bound.get(name)
    if not isinstance(values, list) or len(values) != len(LEGS):
        return None
    value = values[index]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) else None


def min_gap_bar(bound: dict, index: int) -> float | None:
    """R4 supplement 3-3 (RD-7 3 read anew, user decision 126): the minimum gap [bar] of one leg
    is the element of the record's ``min_gap_bar`` moved without a calculation (the harness
    record has no Pa key)."""
    return _per_leg(bound, "min_gap_bar", index)


def breach_leg_rows(bound: dict) -> list[dict]:
    """RD-7 1 J-P3 violation rows of one judged line: the legs with ``breach_reads`` >= 1."""
    rows = []
    for index, leg in enumerate(LEGS):
        reads = bound["breach_reads"][index]
        if reads >= 1:
            rows.append({"leg": leg, "breach_reads": reads,
                         "min_gap_bar": min_gap_bar(bound, index),
                         "first_breach_t_s": _per_leg(bound, "first_breach_t_s", index)})
    return rows


def assess_j_p3(item: dict, *, tag: str | None, rod_reading: bool | None, rod_basis: str,
                head_only_declared: bool, rod_stop: str | None = None) -> dict:
    """J-P3 of one ③ line or run: rev3 R3-C8 / rev4 R4-A2 / rev8 R8-2 with the R4 readings.

    Args:
        item: The line, run or u3 / u6 item (its J-P3 input: :func:`j_p3_bound`).
        tag: The controller tag that decides ③ (``v5_options.is_extend_start_tag`` only).
        rod_reading: Rod reading present (R3-C8 1); None = neither a T4h reading nor a
            configuration rule (판정 불가).
        rod_basis: Where ``rod_reading`` came from (recorded).
        head_only_declared: The head-only declaration (R3-C8 2).
        rod_stop: A T4h lookup S-2 reason (rev12 R12-1), never replaced by a configuration rule.

    Returns:
        ``status`` (``not_applicable`` / ``판정 불가`` / ``S-2`` / ``pass`` / ``H-7`` /
        ``no_rod_reading`` / ``setting_defect``), ``reason``, ``rd8_problem`` (the RD-8 form
        defect, else None), ``rows`` (RD-7 legs of an ``H-7`` line) and ``breach_reads_sum``.
    """
    from outrigger_sim.control import extend_start_bound as bound_rules
    from outrigger_sim.hydraulics.v5_options import (
        extend_start_revision_of_tag,
        is_extend_start_tag,
    )

    out: dict[str, Any] = {"rod_reading_basis": rod_basis, "rd8_problem": None, "rows": [],
                           "breach_reads_sum": None, "reason": None}
    if not is_extend_start_tag(tag):
        return {**out, "status": J_P3_NOT_APPLICABLE, "reason": f"tag {tag!r} is not ③ (R8-2)"}
    if extend_start_revision_of_tag(tag) != bound_rules.EXTEND_START_REVISION:
        # 436.9 6.1: a ③ revision 5 row is judged by j_p3_judgement_rev5, never here
        return {**out, "status": NOT_JUDGEABLE,
                "reason": f"tag {tag!r} is ③ revision 5 (436.9 J-P3), not the 436.8 definition"}
    if rod_stop is not None:
        return {**out, "status": J_P3_S2, "reason": rod_stop}
    bound, problem = j_p3_bound(item)
    if problem is not None:
        return {**out, "status": NOT_JUDGEABLE, "reason": problem}
    if rod_reading is None:
        return {**out, "status": NOT_JUDGEABLE,
                "reason": "no T4h rod reading record and no configuration rule (R3-C8 1)"}
    case = bound_rules.j_p3_run_case(bound, rod_reading, head_only_declared)
    out["case"] = case
    if case == bound_rules.J_P3_JUDGED:
        form = breach_reads_problem(bound)
        if form is not None:
            return {**out, "status": NOT_JUDGEABLE, "rd8_problem": form, "reason": form}
        total = sum(bound["breach_reads"])
        status = J_P3_H7 if total else J_P3_PASS
        return {**out, "status": status, "breach_reads_sum": total,
                "rows": breach_leg_rows(bound) if total else []}
    if case == bound_rules.J_P3_NO_ROD_READING:
        return {**out, "status": J_P3_NO_ROD_READING}
    return {**out, "status": J_P3_SETTING_DEFECT, "reason": case}


ROD_BASIS_T4H = "T4h rod_pressure_Pa"
ROD_BASIS_CONFIGURATION = "구성 규칙(r79 두 압력 판독)"
ROD_BASIS_GRID = "구성 규칙(r67 축소 스크린 두 압력 판독, R3-C8 1)"


def r79_rod_reading(run: dict, t4h_folders: list[Path] | tuple[Path, ...]
                    ) -> tuple[bool | None, str]:
    """Rev3 R3-C8 1 with rev12 R12-1 for an r79 result (H-6 .. H-8): the line's own T4h
    ``rod_pressure_Pa`` finite somewhere.

    A line without ``t4h_file`` uses the configuration rule (the r79 adapter reads head and rod
    pressure: "있음"). A recorded ``t4h_file`` found 0 or 2+ times is S-2: ``(None, "S-2: ...")``,
    never the configuration rule (Q-R12-1 = A). A found file without ``rod_pressure_Pa`` keeps the
    configuration rule.
    """
    located = locate_t4h(run, t4h_folders)
    if located["status"] == T4H_NO_RECORD:
        return True, ROD_BASIS_CONFIGURATION
    if located["status"] == T4H_STOP:
        return None, f"S-2: {located['reason']}"
    import numpy as np

    with np.load(located["path"], allow_pickle=False) as data:
        if "rod_pressure_Pa" in data.files:
            return bool(np.isfinite(data["rod_pressure_Pa"]).any()), ROD_BASIS_T4H
    return True, ROD_BASIS_CONFIGURATION


def r79_j_p3(run: dict, t4h_folders: list[Path] | tuple[Path, ...]) -> dict:
    """:func:`assess_j_p3` of one r79 result (H-6, H-8): tag ``controller_tag``, rod reading
    :func:`r79_rod_reading`, declaration ``head_only_declared`` (r79 writes False)."""
    has_reading, basis = r79_rod_reading(run, t4h_folders)
    rod_stop = basis if has_reading is None else None
    declared = run.get("head_only_declared")
    return assess_j_p3(run, tag=run.get("controller_tag"), rod_reading=has_reading,
                       rod_basis=basis, head_only_declared=bool(declared),
                       rod_stop=rod_stop)


def grid_j_p3(document: dict) -> list[dict]:
    """R16-7: J-P3 of every ``results[i].runs[j]`` of a grid file (r67 / r69 reduced screens).

    The tag is the job record's ``controller_tag`` (a run has none of its own), the rod reading the
    configuration rule (two pressure readings, rev3 R3-C8 1) and the declaration the run's
    ``head_only_declared`` (absent = not declared: no steady-path case).

    Returns:
        One entry per run: ``index``, ``run_index``, ``job`` (the ``results[i]`` record) and
        ``j_p3`` (:func:`assess_j_p3`).
    """
    out = []
    for index, job in enumerate(document.get("results") or []):
        for run_index, run in enumerate(job.get("runs") or []):
            assessed = assess_j_p3(run, tag=job.get("controller_tag"), rod_reading=True,
                                   rod_basis=ROD_BASIS_GRID,
                                   head_only_declared=bool(run.get("head_only_declared")))
            out.append({"index": index, "run_index": run_index, "job": job, "j_p3": assessed})
    return out


def j_p3_list_rows(assessed: dict, *, bundle: str, result_file: str, location: str, key: Any,
                   setting: Any) -> list[dict]:
    """RD-7 1 / 3 J-P3 violation rows of one assessed line or run (``H-7`` only)."""
    if assessed["status"] != J_P3_H7:
        return []
    return [{"bundle": bundle, "result_file": result_file, "location": location,
             "leg": row["leg"], "key": key, "setting": setting,
             "breach_reads": row["breach_reads"], "min_gap_bar": row["min_gap_bar"],
             "first_breach_t_s": row["first_breach_t_s"]}
            for row in assessed["rows"]]


def j11_list_rows(assessed: dict, *, bundle: str, result_file: str, location: str, key: Any,
                  setting: Any) -> list[dict]:
    """RD-7 1 / 3 J11 stop rows of one assessed line (one per late fallback leg)."""
    if assessed["state"] != J11_STOP:
        return []
    marker = "H-7" if assessed["marker"] == STOP_H7 else assessed["marker"]
    return [{"bundle": bundle, "result_file": result_file, "location": location, "leg": leg,
             "key": key, "setting": setting,
             "n_late_fallback_by_leg": assessed["late_by_leg"][leg], "marker": marker}
            for leg in assessed["late_legs"]]


# ------------------------------------------------------------------- R4 shared J11 (R16-6, RD-10)
J11_STOP_SETTINGS = ("VB", "LS1", "LS2", "LS3", "LS4")
"""Rev16 R16-6 2: the settings whose fallback leg n_late > 0 stops (item8 and overlap VB lines have
setting VB); every other setting's J11 is a record."""
LS_SETTINGS = ("LS1", "LS2", "LS3", "LS4")
J11_STOP = "stop"
J11_PASS = "pass"
J11_RECORD = "record"
J11_NO_INPUT = "입력 없음"
"""RD-10: a record-setting line without the ``lock_window_alignment`` block."""


def fallback_legs_of(block: dict) -> list[str]:
    """The actual fallback legs of a ``lock_window_alignment`` block (``fallback_legs``: a dict
    leg -> details, or a list of legs), in the FL, FR, RL, RR order."""
    legs = block.get("fallback_legs") or {}
    names = set(legs) if isinstance(legs, (dict, list, tuple)) else set()
    return [leg for leg in LEGS if leg in names]


def assess_j11(block: Any, setting: str | None) -> dict:
    """J11 of one harness line: rev16 R16-6 (``n_late_fallback_by_leg`` of the actual fallback
    legs) with RD-10 (a stop setting without the block is 판정 불가).

    Returns:
        ``state`` (``stop`` / ``pass`` / ``판정 불가`` for a stop setting; ``record`` /
        ``입력 없음`` for a record setting), ``marker`` (``멈춤 H-7`` / ``L-e`` on a stop),
        ``late_by_leg`` (the fallback legs' values), ``late_legs`` (> 0) and ``reason``.
    """
    is_stop_setting = setting in J11_STOP_SETTINGS
    out: dict[str, Any] = {"setting": setting, "stop_setting": is_stop_setting, "marker": None,
                           "fallback_legs": [], "late_by_leg": {}, "late_legs": [],
                           "reason": None}
    if setting is None:  # R4 supplement 3-6: whether J11 stops cannot be decided
        return {**out, "state": NOT_JUDGEABLE,
                "reason": "setting missing: J11 scope undecidable (supplement 3-6)"}
    if not isinstance(block, dict):
        if is_stop_setting:
            return {**out, "state": NOT_JUDGEABLE,
                    "reason": "lock_window_alignment block missing or not an object (RD-10)"}
        return {**out, "state": J11_NO_INPUT}
    legs = fallback_legs_of(block)
    by_leg = block.get("n_late_fallback_by_leg")
    values = {leg: by_leg.get(leg) if isinstance(by_leg, dict) else None for leg in legs}
    missing = [leg for leg, value in values.items()
               if isinstance(value, bool) or not isinstance(value, int)]
    late = [leg for leg, value in values.items() if leg not in missing and value > 0]
    out.update(fallback_legs=legs, late_by_leg=values, late_legs=late)
    if not is_stop_setting:
        return {**out, "state": J11_RECORD, "missing_legs": missing}
    if missing:
        return {**out, "state": NOT_JUDGEABLE,
                "reason": f"n_late_fallback_by_leg missing or None on fallback legs {missing} "
                          "(R16-6 1)"}
    if late:
        marker = STOP_LE if setting in LS_SETTINGS else STOP_H7
        return {**out, "state": J11_STOP, "marker": marker}
    return {**out, "state": J11_PASS}


# --------------------------------------------------------------------- R4 list notation (RD-7 3)
JSONL_KEY_FIELDS = {
    "h1_d1.jsonl": ("job.d1.key", "job.setting"),
    "h5_u9_v0.jsonl": ("job.case", "job.setting"),
    "h9_stage1.jsonl": ("job.case", "job.setting"),
    "h10_reuse_rerun.jsonl": ("job.case", "job.setting"),
}
"""RD-7 3: (key, setting) field paths of each jsonl result file."""
RESULTS_KEY_FILES = ("h6_dg3_v4on.json", "h7_dg3_off.json", "h8_noise_VB.json",
                     "h8_noise_V0.json", "h8_seedext_VB.json", "h8_seedext_V0.json",
                     "h9_family_F_VB.json", "h9_family_F_V0.json")
"""RD-7 3: files whose ``results[i]`` carry ``key`` / ``v5_setting`` (plus ``h9_grid/grid_*``)."""


def dotted(node: Any, path: str) -> Any:
    """The value at a dotted path, None when any part is missing."""
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


GRID_FOLDERS = ("", "h9_grid", "h9_grid_v0_sample")
"""Folders of the grid result files (RD-7 3 key / setting of ``results[i]``; supplement 4-2:
the H-9 V0 sample files have the same form)."""


def is_grid_file(name: str, parent: str = "") -> bool:
    return name.startswith("grid_") and name.endswith(".json") and parent in GRID_FOLDERS


def key_and_setting(file_name: str, item: dict, parent_dir: str = "") -> tuple[Any, Any]:
    """RD-7 3 key and setting of one line / item (``results[i]`` of a grid or r79 file; a grid
    run uses its ``results[i]``, so pass that). Unknown forms or missing fields give None."""
    if file_name in JSONL_KEY_FIELDS:
        key_path, setting_path = JSONL_KEY_FIELDS[file_name]
        return dotted(item, key_path), dotted(item, setting_path)
    if file_name in RESULTS_KEY_FILES or is_grid_file(file_name, parent_dir):
        return item.get("key"), item.get("v5_setting")
    if file_name.startswith("u3_") and file_name.endswith(".json"):
        key = item.get("key")
        if key is None and isinstance(item.get("id"), str):
            key = item["id"]
        return key, dotted(item, "v5.v5_setting")
    if file_name.startswith("u6_") and file_name.endswith(".json"):
        return item.get("case"), dotted(item, "v5.v5_setting")
    return None, None


def read_jsonl_numbered(path: Path) -> list[tuple[int, dict]]:
    """RD-7 3: (physical line number from 1, record) of a jsonl file; blank lines are counted
    but yield no record."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"{path}: {exc}") from exc
    numbered = []
    for number, line in enumerate(text.split("\n"), start=1):
        if line.strip():
            numbered.append((number, json.loads(line)))
    return numbered


def jsonl_location(number: int) -> str:
    return f"line {number}"


def json_location(container: str, index: int, run_index: int | None = None) -> str:
    location = f"{container}[{index}]"
    return location if run_index is None else f"{location}.runs[{run_index}]"


def repo_relative(path: Path, root: Path | None = None) -> str:
    """RD-7 3: a result file as a path relative to the repository root (``/`` separators); a
    path outside the root keeps its own form."""
    base = ROOT if root is None else Path(root)
    try:
        return Path(path).resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def bundle_number(bundle: str) -> tuple[int, str]:
    """``H-10`` -> (10, ``H``): bundles sort by their number, not as strings."""
    prefix, _, number = str(bundle).partition("-")
    return (int(number), prefix) if number.isdigit() else (10**6, str(bundle))


def list_sort_key(row: dict) -> tuple:
    """RD-7 3 order: bundle -> result file (string) -> location (numbers in order) -> leg -> k."""
    numbers = tuple(int(n) for n in re.findall(r"\d+", str(row.get("location", ""))))
    leg = row.get("leg")
    return (bundle_number(row.get("bundle", "")), str(row.get("result_file", "")), numbers,
            LEGS.index(leg) if leg in LEGS else -1, row.get("k", -1))


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
