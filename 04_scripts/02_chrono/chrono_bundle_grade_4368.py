"""436.8 Chrono path 1 bundle grades (rules rev18 R18-2 as rewritten by rev19 R19-1 .. R19-6;
python-expert 2026-11-15).

Aggregates the row grades of one Chrono bundle from inputs other path 1 tools already wrote;
it runs no simulation and no other judge:

* L2b / L1-R rows: the runner judge output (``run_S8C.py judge`` -> ``verify_S8C``,
  ``run_S6C.py judge`` -> ``verify_S6C``), one file per row named
  ``<C1|C2|C5>_<case>.verify_S8C.json`` / ``.verify_S6C.json`` in ``--runner-judge-dir`` (the form
  of ``judge_b9f5707/chrono_path1/runner_judge/``). Rev19 R19-4: the runner's own count decides
  (``passed`` False = fail, else ``kind`` hold = not judgeable, else pass; no judged-kind item
  with ``passed`` True = not judgeable); a judged kind with ``passed`` None is ``러너 미판정``
  (recorded), and the counts must equal ``meta.failed`` / ``meta.hold`` (S-11).
* Rev19 R19-5: the three D8 items windowed from the runner lift-off are re-computed from the
  D-29 t_lift (:func:`d8_override`); the four other runner lift-off items keep the runner value
  and the runner / D-29 t_lift difference on the 10 Hz grid must be <= 0.1 s + 1e-9 s, else
  (or when it cannot be computed) the bundle stops (:func:`t_lift_difference`).
* SCM rows: ``result.json`` ``p3b`` (P3-1 .. P3-9, :func:`p3_items`).
* Over both: the re-computed items (D-26 .. D-39) of ``chrono_rows_judge_4368.py judge``
  (``--rows-judge``) replace the items of the same name (:data:`RIGID_OVERRIDES`,
  :func:`p3_items`); every replaced item keeps its runner and re-computed values.
* S-01 .. S-04 (rev19 R19-1): a row whose first ``FAULT*`` event is the soil guard is graded by
  the five 427.9 conditions alone, computed here from the run files with the R19-1 windows
  (:func:`safe_stop_conditions`); every P3 / G6 item becomes a record.
* Bundle rules (:func:`bundle_grade`): C-1 / C-2 / C-3 = ``d1_selection_rules.md`` 11 (+ rev1),
  C-5 = v5 criteria revision 12 / 12a / 12b (T4 / T5 from ``chrono_t45_replay`` ``--t45``, J11,
  J-P3, D2 record, P3 items, exactly the six VB / V0 pairs of revision 12 2.1 or S-15); bundle
  status by original 8.1 (not judgeable > fail > pass), the row phrase counts the safe stops
  apart.
* Record bundles: C-6 / C-7 ``result.json`` ``p3a`` (P3a-1 .. 5, spec 11047 FLAG), C-8 the
  ``resume4368_judge.py oc5`` and ``fmin-time`` outputs (``--oc5``, ``--fmin-time``).
* Row count (S-15): rows from the ``batch.json`` ``cases[]`` of the bundle criteria, each one a
  row of the manifest bundle, against :data:`EXPECTED_ROWS`; a mismatch is S-15 and the bundle
  gets no grade, a bundle without rows gets no grade either. A missing row input makes that row
  not judgeable (original 9.3).

CLI (Chrono-dev or python-dev, no simulation)::

    python -I -B -X utf8 04_scripts/02_chrono/chrono_bundle_grade_4368.py grade --bundle C-1 \
        --git-at-start <R2> --batch <07_results/S9/batch_...> [--batch ...] \
        --rows-judge <judge_C1.json> --runner-judge-dir <runner_judge> --out <out.json>
    ... grade --bundle C-5 ... --t45 <t45_C5.json>
    ... grade --bundle C-6C7 --git-at-start <R2> --batch <...C6C7...> --out <out.json>
    ... grade --bundle C-8 --git-at-start <R2> --batch <...OC5...> --oc5 <a.json> --oc5 <b.json> \
        --fmin-time <a.json> --fmin-time <b.json> --out <out.json>
    ... seals [--rules-dir <verif_matrix>]

Exit codes: 0 done without a stop; 1 a stop (S-15, S-12, H-7, R40-2 hold, S-2, J11, T4-0,
VB-specific failure, S-9 / S-10 record) or a seal mismatch; 2 an input is missing or invalid;
3 internal error. The last stdout line is JSON, the line before it ``errors N``.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:  # -I drops the script folder from sys.path
    sys.path.insert(0, str(HERE))

import chrono_rows_judge_4368 as rows_judge  # noqa: E402 - needs the path above

InputError = rows_judge.InputError

TOOL_VERSION = "chrono_bundle_grade_4368 v2 (python-expert 2026-11-15, rules rev18 R18-2, rev19)"
RULES_TEXT = ("rules rev18 R18-2 (bundle grades of path 1), R18-2a, R18-4, rewritten by rev19 "
              "R19-1 .. R19-6; original 5.2 / 7.4 / 7.5 / 8.1 / 8.2 / 9.3; d1_selection_rules.md "
              "7 / 11 + rev1; v5 criteria revision 6 4.6, 12 / 12a / 12b; rev6 R6-A / R6-B4 / "
              "R6-B5 / R6-B8 / R6-B9; seal list of chrono_rows_judge_4368.py")

# --- bundles ---------------------------------------------------------------------------------
EXPECTED_ROWS = {"C-1": 10, "C-2": 6, "C-3": 2, "C-5": 35, "C-6C7": 3, "C-8": 2}
"""Rules rev18 R18-2 row count check (S-15)."""
BUNDLE_CRITERIA = {"C-1": ("C-1",), "C-2": ("C-2",), "C-3": ("C-3",), "C-5": ("C-5",),
                   "C-6C7": ("C-6", "C-7", "C-7a", "C-7b"), "C-8": ("C-8a", "C-8b")}
"""``batch.json`` ``criteria_id`` values of each bundle (original 5.2 table, rev4 R4-A3)."""
GRADED_BUNDLES = ("C-1", "C-2", "C-3", "C-5")
RECORD_BUNDLES = ("C-6C7", "C-8")
RUNNER_FILE_PREFIX = {"C-1": "C1", "C-2": "C2", "C-5": "C5"}
"""Runner judge file name prefix (``judge_b9f5707/chrono_path1/runner_judge/C1_<case>...``)."""
RUNNER_FILE_SUFFIX = {"L2b": "verify_S8C", "L1R": "verify_S6C"}

# --- grades ----------------------------------------------------------------------------------
PASS, FLAG, FAIL = "pass", "flag", "fail"
NOT_JUDGEABLE, ALLOWED_STOP, RECORD = "not_judgeable", "allowed_stop", "record"
GRADE_RANK = {PASS: 0, ALLOWED_STOP: 0, FLAG: 1, FAIL: 2, NOT_JUDGEABLE: 3}
"""Original 8.1 order (not judgeable > fail > pass); a FLAG is no fail (rev3 R3-G7), the 427.9
safe stop counts as an allowed end (spec 427.9, d1_selection_rules 11)."""
BUNDLE_STATUS = {NOT_JUDGEABLE: "판정 불가", FAIL: "미달", FLAG: "통과", PASS: "통과",
                 ALLOWED_STOP: "통과"}
RECORD_COMPLETE, RECORD_INCOMPLETE = "기록 완료", "기록 불완전"

ROLE_JUDGED, ROLE_RECORD = "judged", "record"
RECORD_ROLES = ("record", "timing base")
"""``batch.json`` ``d1_role`` values of record rows (d1_selection_rules 11: C1-09 .. 12 record,
D1-PSC base = the event's timing base); ``judge ...`` or no role = a judged row."""

# --- items -----------------------------------------------------------------------------------
RIGID_OVERRIDES = (
    ("C1 D8 min true rod force", "C1_R40", "D-31 / D-39"),
    ("4 max moving pressure", "moving_pressure_D-32", "D-32"),
    ("4 saturation steps", "moving_pressure_D-32", "D-32"),
)
"""(runner item name prefix, ``chrono_rows_judge`` item, rev6 R6-A number): the re-computed
items with a runner item of the same meaning (R18-2 "같은 이름 항목에 덮어쓴다")."""
MOVING_PRESSURE_MAX_BAR = rows_judge.MOVING_PRESSURE_MAX_BAR
SAFE_STOP_ROWS = ("S-01", "S-02", "S-03", "S-04")
"""Rev6 R6-B8 (D-26): rows of the 427.9 safe stop."""
SOIL_EVENT_SERIES = "soil_event_series.npz"
"""``run_S9.SOIL_EVENT_SERIES_NAME``: the 1 ms event rows of a PS-c event run."""
SOIL_STOP_PREFIX = "FAULT_LIFT_STROKE_LIMIT:soil:"
"""Rev19 R19-1 condition 1: the first ``FAULT*`` event name starts with this."""
SAFE_STOP_RECORDED = ("P3-1 .. P3-9 (sub-keys, P3-3_within, P3-6_ready, READY <= 120 s D-28, "
                      "P3-6 FLAG D-27)", "FAULT0", "G6-1 .. G6-7 (S-03 / S-04)",
                      "items on READY / DONE / end attitude")
"""Rev19 R19-1: what a soil-guard row records instead of grading."""
G6_EXTRA_P3 = ("P3-7",)
"""C-3 (P3 + G6, d1_selection_rules 11): the P3 item the G6 gates do not cover."""
PSC_STROKE_LIMIT_MM = 684.8
"""d1_selection_rules 11 D1-PSC: run maximum stroke <= 684.8 mm."""
SOIL_EVENT_GROUPS = ("E-1", "E-2", "E-3", "E-4", "E-5", "E-6", "E-7")
SLOW_EVENT_NOT_APPLICABLE = ("E-2",)
"""Spec 426.3: E-2 (adjacent legs, U57) is a fast-event row; a slow event has no E-2 gate."""
T45_CASES = (
    "K0V_top_fup3.5_Fs0", "K0_top_fup3.2_Fs0", "K0V_top_roll5.5_Fs0", "K0_top_fdown3.2_Fs0",
    "K0V_top_fdown3.5_Fs0", "E_G4_Fs8", "K0_top_rpBop_Fs0", "E_RE1bF_Fs0", "E_RE1bF_Fs8",
    "K8_top_rpB_Fs8", "S_top_fdown3.5_wika_Fs8", "K8_top_fdown3.5_Fs8",
    "K0V_top_fup3.5_Fs0_LS1", "E_G4_Fs8_LS1", "E_RE1bF_Fs8_LS1",
    "K0V_top_fup3.5_Fs0_LS4", "E_G4_Fs8_LS4", "E_RE1bF_Fs8_LS4",
)
"""v5 criteria revision 6 3 rows 1 .. 18 (VB 12 + LS 6): the T4 / T5 rows."""
T45_CRITERIA = "rev7"
"""v5 criteria revision 7 (E exclusion, guard, B1) applies from the next Chrono T4 judgement."""
J11_PASS_STATES = ("pass", "no_fallback_leg", "not_computed")
J11_STOP_STATES = (rows_judge.J11_STOP_VB, rows_judge.J11_STOP_LS)
V0_PAIR_SUFFIXES = ("_V0", "_v0v")
"""Revision 12 2.1: the V0 / V0v pair of a VB row is its case name + one of these."""
C5_VB_V0_PAIRS = (
    ("E_G4_Fs4", "E_G4_Fs4_V0"),
    ("E_G4_Fs4_ph0.05", "E_G4_Fs4_ph0.05_V0"),
    ("G1R_FS24_FL_top_o050_Fs0", "G1R_FS24_FL_top_o050_Fs0_V0"),
    ("P3b_J1_B_top_Fs4", "P3b_J1_B_top_Fs4_v0v"),
    ("P3b_J2_B_top_Fs4_m1p1_t180", "P3b_J2_B_top_Fs4_m1p1_t180_v0v"),
    ("S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0", "S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0_v0v"),
)
"""v5 criteria revision 12 2.1 (33 .. 51): the six VB / V0(V0v) pairs of C-5 (names as in the
manifest and the C-5 batches); the pairs found must be exactly these, else S-15 (no grade)."""
RUNNER_RECORD_KINDS = ("record", "report", "info", "consistency", "comparison", "pair",
                       "sensitivity", "superseded", "leak_compare")
"""Runner row kinds that are never judged (record whatever ``passed`` says)."""
RUNNER_JUDGED_KINDS = ("function", "judged", "anomaly", "replay", "quality")
"""Runner row kinds that are judged (rev19 R19-4); ``passed`` None of these is ``러너 미판정``."""
RUNNER_UNJUDGED = "러너 미판정"
D8_ITEMS = (
    ("C1 D8 min true rod force", "D-39 (chrono_rows_judge C1_R40)"),
    ("D8 min true cylinder force >= F_min + 5 kN", "D-29 t_lift, pads.npz F_cyl_min_interval"),
    ("D8 no pad lift-off", "D-29 t_lift, pads.npz N <= 0 1 ms samples (rev3 Q-14)"),
)
"""Rev19 R19-5: the D8 items re-computed from the D-29 t_lift (window end and threshold as the
runner item)."""
RUNNER_T_LIFT_KEPT = ("3 F_min (1 ms)", "3 F_min before the event", "5a rocking amplitude",
                      "F2 lower-bound soundness")
"""Rev19 R19-5: runner lift-off items that keep the runner value (the t_lift difference is
checked instead)."""
RUNNER_T_LIFT_ITEMS = tuple(name for name, _ in D8_ITEMS) + RUNNER_T_LIFT_KEPT
T_LIFT_MAX_DIFF_S = 0.1
"""Rev19 R19-5: one control period; a difference > 0.1 s + 1e-9 s stops the bundle."""
T_LIFT_1MS_BASIS = "pads.npz crawler_normal_N 1 ms"
"""``chrono_rows_judge`` ``D8_t_lift_basis`` of the 1 ms D-29 t_lift (else the R15-3 bracket)."""
S9_HANDLED_CRITERIA = ("C-8a",)
S9_HANDLED_TEXT = ("S-9 handled by rules rev18 R18-5 (user decision 60 (A)): L-5 known limit, "
                   "cause to 436.9; C-8 is a record bundle, no grade")
"""Rev18 R18-5 decided the C-8a S-9; an S-9 of another row is still a stop (original 8.2)."""
OPENLOOP_CHECKS = ("P3a-1_within", "P3a-2_lifted", "P3a-3_within", "P3a-4_within",
                   "P3a-5_within")
"""Original 7.5: the P3a-1 .. 5 results of ``result.json`` ``p3a.checks``."""


@dataclass
class RowInput:
    """One row of the bundle and the inputs read for it."""

    case: str
    criteria_id: str
    engine: str
    role: str
    row_id: str | None
    entry: dict[str, Any]
    batch: Path
    result: dict[str, Any] | None = None
    result_path: Path | None = None
    judged: dict[str, Any] | None = None
    missing: list[str] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)


# =============================================================================== small helpers
def worst(grades: list[str]) -> str:
    """The original 8.1 worst grade of ``grades`` (pass for an empty list)."""
    return max(grades, key=lambda grade: GRADE_RANK[grade], default=PASS)


def item(name: str, verdict: str | None, source: str, **detail: Any) -> dict[str, Any]:
    """One row item (``verdict`` None = a record item)."""
    return {"item": name, "verdict": verdict, "source": source, **detail}


def bool_verdict(value: Any) -> str:
    """True / false -> pass / fail; anything else (None, missing) is not judgeable (9.3)."""
    if value is True:
        return PASS
    if value is False:
        return FAIL
    return NOT_JUDGEABLE


def read_json(path: Path, what: str) -> Any:
    """A JSON input file (InputError when missing or not JSON)."""
    if not path.is_file():
        raise InputError(f"{what} missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"{what} unreadable: {path}: {exc}") from exc


def engine_of(entry: dict[str, Any]) -> str:
    """Engine kind (SCM / L2b / L1R) from the ``batch.json`` row record (z4372)."""
    record = rows_judge.recorded_engine(entry, {})
    if record["kind"] is None:
        raise InputError(f"{entry.get('case')}: batch.json records no engine")
    return record["kind"]


def role_of(entry: dict[str, Any]) -> str:
    """Judged or record row from ``batch.json`` ``d1_role`` (:data:`RECORD_ROLES`)."""
    role = entry.get("d1_role")
    if role is None or str(role).startswith("judge"):
        return ROLE_JUDGED
    if role in RECORD_ROLES:
        return ROLE_RECORD
    raise InputError(f"{entry.get('case')}: unknown d1_role {role!r}")


# =============================================================================== rows of a bundle
def bundle_entries(bundle: str, batches: list[Path], manifest: dict[str, Any]
                   ) -> tuple[list[tuple[Path, dict[str, Any]]], dict[str, Any]]:
    """The bundle rows of the batches and the R18-2 row count check (S-15)."""
    wanted = BUNDLE_CRITERIA[bundle]
    found: list[tuple[Path, dict[str, Any]]] = []
    not_in_manifest, batch_names = [], {}
    all_manifest_cases: set[str] = set()
    for batch in batches:
        doc = read_json(batch / "batch.json", "batch.json")
        name = rows_judge.batch_full_name(batch, doc, manifest)
        batch_names[str(batch)] = name
        manifest_cases = _manifest_cases(manifest, name.get("name"))
        all_manifest_cases |= manifest_cases
        for entry in doc.get("cases") or []:
            if str(entry.get("criteria_id")) not in wanted:
                continue
            found.append((batch, entry))
            if str(entry.get("case")) not in manifest_cases:
                not_in_manifest.append(str(entry.get("case")))
    cases = [str(entry.get("case")) for _, entry in found]
    duplicates = sorted(case for case, n in Counter(cases).items() if n > 1)
    check = {"rule": "rules rev18 R18-2 row count (S-15)", "expected": EXPECTED_ROWS[bundle],
             "found": len(found), "criteria_ids": list(wanted), "batches": batch_names,
             "not_in_manifest": not_in_manifest, "duplicates": duplicates,
             "manifest_cases": sorted(all_manifest_cases)}
    check["ok"] = bool(len(found) == EXPECTED_ROWS[bundle] and not not_in_manifest
                       and not duplicates)
    return found, check


def _manifest_cases(manifest: dict[str, Any], batch_name: str | None) -> set[str]:
    if batch_name is None:
        return set()
    rows = (manifest["batches"].get(batch_name) or {}).get("rows") or []
    return {str(row.get("case")) for row in rows}


def judged_rows_by_case(doc: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """``chrono_rows_judge`` ``rows[]`` by case (InputError on a repeated case)."""
    if doc is None:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in doc.get("rows") or []:
        case = str(row.get("case"))
        if case in out:
            raise InputError(f"rows judge output lists {case} twice")
        out[case] = row
    return out


def load_row_input(batch: Path, entry: dict[str, Any], judged: dict[str, Any] | None,
                   bundle: str) -> RowInput:
    """Engine, role, result.json and the judge row of one bundle row.

    SCM and open-loop rows live in ``<batch>/<case>/``; an L2b / L1-R row lives in the runner
    folder ``chrono_rows_judge`` found for it (its ``rows[].dir``).
    """
    case = str(entry.get("case"))
    engine = "openloop" if bundle == "C-6C7" else engine_of(entry)
    row = RowInput(case=case, criteria_id=str(entry.get("criteria_id")), engine=engine,
                   role=role_of(entry), row_id=entry.get("d1_id"), entry=entry, batch=batch,
                   judged=judged)
    if engine in ("SCM", "openloop"):
        row.result_path = batch / case / "result.json"
    elif judged is not None and judged.get("dir"):
        row.result_path = Path(judged["dir"]) / "result.json"
    if row.result_path is not None and row.result_path.is_file():
        row.result = read_json(row.result_path, "result.json")
        row.files["result.json"] = rows_judge.sha256_file(row.result_path)
    else:
        row.missing.append("result.json")
    if judged is None and bundle in GRADED_BUNDLES:
        row.missing.append("chrono_rows_judge row")
    return row


# =============================================================================== rigid rows
def runner_judge_file(directory: Path | None, bundle: str, row: RowInput) -> Path | None:
    """``<C1|C2|C5>_<case>.verify_S8C.json`` / ``.verify_S6C.json`` of a rigid row."""
    if directory is None:
        return None
    name = f"{RUNNER_FILE_PREFIX[bundle]}_{row.case}.{RUNNER_FILE_SUFFIX[row.engine]}.json"
    path = directory / name
    return path if path.is_file() else None


def runner_items(doc: dict[str, Any], case: str) -> list[dict[str, Any]]:
    """Runner judge rows of the case and of the whole batch (``*``) as row items."""
    items = []
    for runner_row in doc.get("rows") or []:
        if runner_row.get("case") not in (case, "*"):
            continue
        verdict, branch = runner_verdict(runner_row)
        items.append(item(str(runner_row.get("item")), verdict, "runner",
                          value=runner_row.get("value"), limit=runner_row.get("limit"),
                          kind=runner_row.get("kind"), passed=runner_row.get("passed"),
                          branch=branch, note=runner_row.get("note")))
    return items


def runner_verdict(runner_row: dict[str, Any]) -> tuple[str | None, str]:
    """(verdict, branch name) of one runner judge row (rev19 R19-4, README 9 table).

    hold = not judgeable; a record kind is a record; ``passed`` False = fail, True = pass (FLAG
    when an anomaly note or the row carries a FLAG); a judged kind with ``passed`` None and an
    unknown kind are ``러너 미판정`` (the runner does not count them: no fail, no not judgeable).
    """
    kind, passed = runner_row.get("kind"), runner_row.get("passed")
    note = str(runner_row.get("note"))
    is_flag = bool(kind == "anomaly" and "FLAG" in note) or runner_row.get("flag") is True
    if kind == "hold":
        return NOT_JUDGEABLE, "hold"
    if kind in RUNNER_RECORD_KINDS:
        return None, "record_kind"
    if kind is not None and kind not in RUNNER_JUDGED_KINDS:
        return None, "unknown_kind"
    if passed is False:
        return FAIL, "passed_false"
    if passed is True:
        return (FLAG, "passed_true_flag") if is_flag else (PASS, "passed_true")
    if is_flag:
        return FLAG, "anomaly_flag"
    return None, "runner_unjudged"


UNJUDGED_BRANCHES = ("runner_unjudged", "unknown_kind")
JUDGED_TRUE_BRANCHES = ("passed_true", "passed_true_flag")


def runner_count_check(doc: dict[str, Any]) -> dict[str, Any]:
    """Rev19 R19-4: this tool's ``passed`` False / ``hold`` counts against ``meta.failed`` /
    ``meta.hold`` (no ``hold`` key = 0, ``verify_S6C``); a difference is S-11."""
    rows = doc.get("rows") or []
    meta = doc.get("meta") or {}
    counted = {"failed": sum(1 for r in rows if r.get("passed") is False),
               "hold": sum(1 for r in rows if r.get("kind") == "hold")}
    recorded = {"failed": meta.get("failed"), "hold": meta.get("hold", 0)}
    return {"counted": counted, "meta": recorded, "ok": counted == recorded}


def runner_part_grade(items: list[dict[str, Any]], judged_true: int) -> str:
    """Rev19 R19-4 (user decision 64): any fail = fail, else any not judgeable (hold or a
    re-computed item without input) = not judgeable, else no judged-kind item with ``passed``
    True = not judgeable (empty pass), else FLAG / pass."""
    verdicts = [entry["verdict"] for entry in items]
    if FAIL in verdicts:
        return FAIL
    if NOT_JUDGEABLE in verdicts:
        return NOT_JUDGEABLE
    if judged_true == 0:
        return NOT_JUDGEABLE
    return FLAG if FLAG in verdicts else PASS


def runner_t_lift_items(items: list[dict[str, Any]]) -> list[str]:
    """Runner items of the row whose window starts at the runner lift-off
    (:data:`RUNNER_T_LIFT_ITEMS`), as the table name."""
    names = [entry["item"] for entry in items]
    return [prefix for prefix in RUNNER_T_LIFT_ITEMS
            if any(name.startswith(prefix) for name in names)]


def recomputed_verdict(judge_key: str, runner_name: str,
                       judged_items: dict[str, Any]) -> tuple[str, Any]:
    """(verdict, value) of a re-computed item standing in for a runner item."""
    block = judged_items.get(judge_key)
    if not isinstance(block, dict):
        return NOT_JUDGEABLE, None
    if judge_key == "C1_R40":
        if block.get("status") != "judged":
            return NOT_JUDGEABLE, block.get("raw_min_N")
        return (PASS if block.get("verdict") == "pass" else FAIL), block.get("raw_min_N")
    if block.get("status") != "judged":
        return NOT_JUDGEABLE, None
    if runner_name.startswith("4 saturation steps"):
        count = block.get("saturated_samples")
        return (PASS if count == 0 else FAIL), count
    value = block.get("max_moving_bar")
    if value is None:  # no moving sample: nothing exceeds the limit
        return PASS, None
    return (PASS if rows_judge.le(float(value), MOVING_PRESSURE_MAX_BAR) else FAIL), value


def apply_rigid_overrides(items: list[dict[str, Any]], judged_items: dict[str, Any]
                          ) -> list[dict[str, Any]]:
    """Replace the runner items of :data:`RIGID_OVERRIDES`; returns the before / after log."""
    log = []
    for runner_item in items:
        for prefix, judge_key, number in RIGID_OVERRIDES:
            if not runner_item["item"].startswith(prefix):
                continue
            verdict, value = recomputed_verdict(judge_key, runner_item["item"], judged_items)
            _override(runner_item, verdict, value, number, log)
            break
    return log


def _override(runner_item: dict[str, Any], verdict: str, value: Any, rule: str,
              log: list[dict[str, Any]], **extra: Any) -> None:
    """Replace one runner item (a runner record row stays a record, its value logged)."""
    before = {"verdict": runner_item["verdict"], "value": runner_item.get("value")}
    entry = {"item": runner_item["item"], "rule": rule, "runner": before,
             "recomputed": {"verdict": verdict, "value": value}, **extra}
    if runner_item["verdict"] is None:
        log.append({**entry, "applied": False, "reason": "runner record row"})
        return
    runner_item.update(verdict=verdict, value=value, source=f"recomputed {rule}")
    log.append({**entry, "applied": True})


def load_npz(path: Path) -> dict[str, np.ndarray] | None:
    """The arrays of an npz file (None when the file is missing)."""
    return rows_judge.npz(path) if path.is_file() else None


def d8_value(name: str, pads: dict[str, np.ndarray] | None, t_lift: float | None
             ) -> tuple[Any, dict[str, Any]]:
    """Rev19 R19-5 re-computed value of a D8 item from ``t_lift`` (absolute, as the pads time):
    D8 minimum force [kN] over ``F_cyl_min_interval``, or the ``N <= 0`` sample count."""
    if pads is None or t_lift is None:
        return None, {"reason": "pads.npz or the D-29 t_lift missing"}
    key = "F_cyl_min_interval" if name.startswith("D8 min") else "N"
    if key not in pads or "t" not in pads:
        return None, {"reason": f"pads.npz {key} / t missing"}
    t = np.asarray(pads["t"], float)
    after = t >= t_lift - rows_judge.CMP_EPS
    if not after.any():
        return None, {"reason": "no pads sample after the D-29 t_lift"}
    values = np.asarray(pads[key], float)[after]
    if key == "N":
        return int((values <= 0.0).sum()), {"pad_N_min_kN": float(values.min()) / 1e3}
    return float(values.min()) / 1e3, {}


def apply_d8_overrides(items: list[dict[str, Any]], judged_items: dict[str, Any],
                       pads: dict[str, np.ndarray] | None, t_lift: float | None
                       ) -> list[dict[str, Any]]:
    """Rev19 R19-5: the two pads D8 items from the D-29 t_lift (C1 D8 is D-39 in
    :data:`RIGID_OVERRIDES`); without a t_lift they are not judgeable (original 9.3)."""
    log: list[dict[str, Any]] = []
    for runner_item in items:
        for name, rule in D8_ITEMS[1:]:
            if not runner_item["item"].startswith(name):
                continue
            value, detail = d8_value(name, pads, t_lift)
            if value is None:
                verdict = NOT_JUDGEABLE
            elif name.startswith("D8 min"):
                limit = runner_item.get("limit")
                limit = float(limit) if isinstance(limit, (int, float)) else None
                verdict = NOT_JUDGEABLE if limit is None else (
                    PASS if rows_judge.ge(value, limit) else FAIL)
            else:
                verdict = PASS if value == 0 else FAIL
            _override(runner_item, verdict, value, f"rev19 R19-5 ({rule})", log,
                      t_lift_D29_s=t_lift, **detail)
            break
    return log


def t_lift_difference(doc: dict[str, Any], row: RowInput, judged_items: dict[str, Any],
                      record: dict[str, np.ndarray] | None) -> dict[str, Any]:
    """Rev19 R19-5: |runner t_lift - D-29 t_lift| on the 10 Hz grid.

    Runner t_lift = ``verify_S8C`` ``s8_metrics.<case>.liftoff_s`` (``_times`` ``liftoff``,
    relative to ``settings.start_t_s``) + the row's ``t0_s``; a 1 ms D-29 t_lift is raised to the
    first 10 Hz ``record.npz`` ``t`` at or after it, a 10 Hz bracket (R15-3) one is used as it
    is. Not computable or > 0.1 s + 1e-9 s = a stop.
    """
    judged = row.judged or {}
    metrics = (doc.get("s8_metrics") or {}).get(row.case) or {}
    runner_rel = metrics.get("liftoff_s")
    t0 = judged.get("t0_s")
    d29 = judged_items.get("D8_t_lift_s_D-29_D-30")
    basis = judged_items.get("D8_t_lift_basis")
    out: dict[str, Any] = {"runner_liftoff_rel_s": runner_rel, "t0_s": t0, "t_lift_D29_s": d29,
                           "basis": "1ms" if basis == T_LIFT_1MS_BASIS else "bracket_10Hz"}
    if runner_rel is None or t0 is None or d29 is None:
        return {**out, "ok": False, "stop": "t_lift difference not computable (rev19 R19-5)"}
    aligned = float(d29)
    if basis == T_LIFT_1MS_BASIS:
        times = None if record is None or "t" not in record else np.asarray(record["t"], float)
        later = None if times is None else times[times >= aligned - rows_judge.CMP_EPS]
        if later is None or not later.size:
            return {**out, "ok": False,
                    "stop": "t_lift difference not computable: no 10 Hz record row (R19-5)"}
        aligned = float(later[0])
    runner_abs = float(runner_rel) + float(t0)
    diff = abs(runner_abs - aligned)
    ok = diff <= T_LIFT_MAX_DIFF_S + rows_judge.CMP_EPS
    out.update(runner_t_lift_s=runner_abs, t_lift_D29_10Hz_s=aligned, difference_s=diff, ok=ok)
    if not ok:
        out["stop"] = f"t_lift difference {diff:.4f} s > 0.1 s (rev19 R19-5)"
    return out


@dataclass
class RigidResult:
    """Items and runner checks of an L2b / L1-R row."""

    items: list[dict[str, Any]] = field(default_factory=list)
    overrides: list[dict[str, Any]] = field(default_factory=list)
    grade: str = NOT_JUDGEABLE
    judged_true: int = 0
    unjudged: list[dict[str, Any]] = field(default_factory=list)
    count_check: dict[str, Any] | None = None
    t_lift_items: list[str] = field(default_factory=list)
    t_lift_check: dict[str, Any] | None = None
    stops: list[str] = field(default_factory=list)


def rigid_row(row: RowInput, bundle: str, runner_dir: Path | None) -> RigidResult:
    """An L2b / L1-R row: runner items (R19-4), re-computed items (D-31 / D-32 / D-39), the D8
    items from the D-29 t_lift and the t_lift difference (R19-5, L2b rows)."""
    out = RigidResult()
    path = runner_judge_file(runner_dir, bundle, row)
    if path is None:
        row.missing.append(f"runner judge {RUNNER_FILE_SUFFIX[row.engine]}")
        return out
    doc = read_json(path, "runner judge output")
    row.files[path.name] = rows_judge.sha256_file(path)
    _check_runner_batch(doc, row, path)
    out.items = runner_items(doc, row.case)
    if not any(runner_row.get("case") == row.case for runner_row in doc.get("rows") or []):
        row.missing.append(f"runner judge rows of {row.case}")
    out.judged_true = sum(1 for entry in out.items if entry["branch"] in JUDGED_TRUE_BRANCHES)
    out.unjudged = [{"item": entry["item"], "branch": entry["branch"],
                     "note": entry.get("note")} for entry in out.items
                    if entry["branch"] in UNJUDGED_BRANCHES]
    out.count_check = runner_count_check(doc)
    if not out.count_check["ok"]:
        out.stops.append("S-11: runner failed / hold counts differ from meta (rev19 R19-4)")
    judged_items = (row.judged or {}).get("items") or {}
    out.t_lift_items = runner_t_lift_items(out.items)
    out.overrides = apply_rigid_overrides(out.items, judged_items)
    if row.engine == "L2b":
        folder = Path((row.judged or {}).get("dir") or row.batch)
        pads = load_npz(folder / "pads.npz")
        record = load_npz(folder / "record" / "record.npz")
        t_lift = judged_items.get("D8_t_lift_s_D-29_D-30")
        out.overrides += apply_d8_overrides(out.items, judged_items, pads, t_lift)
        if out.t_lift_items:
            out.t_lift_check = t_lift_difference(doc, row, judged_items, record)
            if out.t_lift_check.get("stop"):
                out.stops.append(out.t_lift_check["stop"])
    out.grade = runner_part_grade(out.items, out.judged_true)
    return out


def _check_runner_batch(doc: dict[str, Any], row: RowInput, path: Path) -> None:
    """The runner judge must have judged this row's runner folder (S-11 otherwise)."""
    runner_batch = Path(str((doc.get("meta") or {}).get("batch") or ""))
    if row.result_path is None:
        return
    expected = row.result_path.parent.parent
    if runner_batch.name != expected.name:
        raise InputError(f"{path.name}: meta.batch {runner_batch} is not the row's runner folder "
                         f"{expected} (S-11)")


# =============================================================================== SCM rows
def p3_items(p3b: dict[str, Any], judged_items: dict[str, Any]) -> list[dict[str, Any]]:
    """P3-1 .. P3-9 and FAULT0 of an SCM row; the D items of ``chrono_rows_judge`` stand in for
    P3-1 (D-36), P3-2 (D-37 / D-38), P3-3 (t_D, R6-B4) and P3-8 (D-34 / D-35)."""
    checks = p3b.get("checks") or {}
    recontact = judged_items.get("P3-1_recontact_D-36") or {}
    p32 = judged_items.get("P3-2_D-37_D-38") or {}
    p33 = judged_items.get("P3-3_after_t_D") or {}
    p38 = judged_items.get("P3-8_D-34_D-35") or {}
    return [
        _p31_item(checks, recontact),
        _p32_item(checks, p32),
        item("P3-3", bool_verdict(p33.get("within")), "recomputed R6-B4 t_D",
             value=p33.get("F_min_after_departure_N")),
        item("P3-4", _verdict_word(checks.get("P3-4_verdict")), "p3b checks"),
        item("P3-5", bool_verdict(checks.get("P3-5_within")), "p3b checks"),
        item("P3-6", bool_verdict(checks.get("P3-6_within")), "p3b checks"),
        item("P3-7", bool_verdict(checks.get("P3-7_within")), "p3b checks"),
        item("P3-8", _verdict_word(p38.get("verdict")), "recomputed D-34 / D-35",
             flags=p38.get("flags")),
        _p39_item(checks),
        item("FAULT0", _fault_verdict(p38), "recomputed (chrono_rows_judge has_fault)"),
    ]


def _verdict_word(word: Any) -> str:
    return word if word in (PASS, FLAG, FAIL) else NOT_JUDGEABLE


def _p31_item(checks: dict[str, Any], recontact: dict[str, Any]) -> dict[str, Any]:
    zero = checks.get("P3-1_crawler_zero_after_ready")
    passed = recontact.get("pass")
    if zero is None or passed is None:
        verdict = NOT_JUDGEABLE
    elif not zero or not passed:
        verdict = FAIL
    else:
        verdict = FLAG if recontact.get("flags") else PASS
    return item("P3-1", verdict, "p3b crawler zero + recomputed D-36",
                crawler_zero_after_ready=zero, flags=recontact.get("flags"))


def _p32_item(checks: dict[str, Any], p32: dict[str, Any]) -> dict[str, Any]:
    within = p32.get("within")
    late_flag = bool(checks.get("P3-2_late_loc_reapproach") or checks.get(
        "P3-2_late_loc_revoked"))
    if within is True:
        verdict = PASS
    elif within is False:
        verdict = FLAG if late_flag else FAIL
    else:
        verdict = NOT_JUDGEABLE
    return item("P3-2", verdict, "recomputed D-37 / D-38 + p3b late-LOC FLAG",
                late_loc_flag=late_flag)


def _p39_item(checks: dict[str, Any]) -> dict[str, Any]:
    flags = checks.get("P3-9_flags")
    if not isinstance(flags, int):
        return item("P3-9", NOT_JUDGEABLE, "p3b checks", value=flags)
    return item("P3-9", FLAG if flags > 0 else PASS, "p3b checks (FLAG record)", value=flags)


def _fault_verdict(p38: dict[str, Any]) -> str:
    fault = p38.get("fault")
    if fault is None:
        return NOT_JUDGEABLE
    return FAIL if fault else PASS


def first_fault(events: list[Any]) -> str | None:
    """Name of the first ``FAULT*`` event of ``result.json`` ``events`` (None without one)."""
    names = [str(event.get("name", "")) for event in events if isinstance(event, dict)]
    return next((name for name in names if name.startswith("FAULT")), None)


def level_start_s(s9_rows: list[Any]) -> float | None:
    """Time of the first ``s9_rows`` row with ``c2_phase`` = level (rev19 R19-1 condition 3)."""
    for entry in s9_rows:
        if isinstance(entry, dict) and entry.get("c2_phase") == "level":
            return float(entry["t_s"])
    return None


def _safe_stop_inputs(row: RowInput) -> tuple[dict[str, Any], list[str]]:
    """The R19-1 inputs of an SCM row and the names of the missing ones."""
    res = row.result or {}
    folder = row.batch / row.case
    series = load_npz(folder / "step_series.npz") or {}
    record = load_npz(folder / "record" / "record.npz") or {}
    found = {"s9_rows": res.get("s9_rows"), "weight_N": (res.get("p3b") or {}).get("weight_N"),
             "series": series, "record": record}
    missing = [] if isinstance(res.get("s9_rows"), list) else ["result.json s9_rows"]
    missing += [f"step_series.npz {key}" for key in
                ("t_s", "scm_pad_normal_N", "F_cyl_N", "scm_crawler_normal_N")
                if key not in series]
    missing += [f"record/record.npz {key}" for key in ("u_applied", "F_cyl") if key not in record]
    if not isinstance(found["weight_N"], (int, float)):
        missing.append("result.json p3b.weight_N")
    return found, missing


def safe_stop_conditions(row: RowInput, params: dict[str, Any]
                         ) -> tuple[str | None, dict[str, Any]]:
    """Rev19 R19-1: (``allowed_stop`` / ``fail`` / not judgeable, block) of a soil-guard row,
    (None, block) when the first ``FAULT*`` event is not the soil guard.

    1. first ``FAULT*`` event starts with ``FAULT_LIFT_STROKE_LIMIT:soil:``;
    2. no ``FAULT_STROKE_END`` event in the run;
    3. no ``scm_pad_normal_N`` <= 0 1 ms sample from the first LEVEL ``s9_rows`` row to the end;
    4. from t_D (rev6 R6-B4, 100 samples; none = false) each leg's 1 ms F_cyl minimum >= F_min;
    5. 10 Hz ``record.npz`` rows of the whole run: moving maximum <= 180 bar, saturation 0.
    A missing input is not judgeable (original 9.3).
    """
    events = (row.result or {}).get("events")
    if not isinstance(events, list):
        return NOT_JUDGEABLE, {"applies": None, "missing_inputs": ["result.json events"]}
    fault = first_fault(events)
    if fault is None or not fault.startswith(SOIL_STOP_PREFIX):
        return None, {"applies": False, "first_fault": fault}
    found, missing = _safe_stop_inputs(row)
    t_level = level_start_s(found["s9_rows"]) if not missing else None
    if not missing and t_level is None:
        missing.append("result.json s9_rows LEVEL row")
    if missing:
        return NOT_JUDGEABLE, {"applies": True, "first_fault": fault, "missing_inputs": missing}
    series = found["series"]
    t = np.asarray(series["t_s"], float)
    pads = np.asarray(series["scm_pad_normal_N"], float)
    lifted = int(((pads <= 0.0) & (t >= t_level - rows_judge.CMP_EPS)[:, None]).sum())
    dep = rows_judge.departure(t, np.asarray(series["scm_crawler_normal_N"], float),
                               float(found["weight_N"]), "count")
    t_dep = dep.get("t_departure_s")
    force = np.asarray(series["F_cyl_N"], float)
    minima = None if t_dep is None else \
        force[t >= t_dep - rows_judge.CMP_EPS].min(axis=0).tolist()
    moving = rows_judge.moving_pressure(found["record"], params["head_area_m2"], event_row=False)
    conditions = {
        "1_soil_stop_first": True,
        "2_no_stroke_end": not any(str(e.get("name", "")).startswith(
            rows_judge.STROKE_END_FAULT) for e in events if isinstance(e, dict)),
        "3_no_lift_after_level": lifted == 0,
        "4_F_after_departure": bool(minima is not None and all(
            rows_judge.ge(value, params["F_min_N"]) for value in minima)),
        "5_moving_pressure": moving.get("within") is True,
    }
    block = {"applies": True, "first_fault": fault, "conditions": conditions,
             "t_level_start_s": t_level, "lifted_samples_after_level": lifted,
             "t_departure_s": t_dep, "F_min_after_departure_N_by_leg": minima,
             "moving_max_bar": moving.get("max_moving_bar"),
             "saturated_rows": moving.get("saturated_samples"),
             "moving_rows": moving.get("moving_samples"),
             "rule": "rev19 R19-1 (spec 427.9 conditions 1 .. 5, D-26)"}
    return (ALLOWED_STOP if all(conditions.values()) else FAIL), block


def after_branch_record(row: RowInput, judgement: dict[str, Any]) -> dict[str, Any]:
    """Rev19 R19-3 record: per leg minimum F_cyl and lifted sample count of the 1 ms event rows
    after the branch end (``soil_event_series.npz`` ``rows``: t, contact 4, F_cyl 4, ...)."""
    series = load_npz(row.batch / row.case / SOIL_EVENT_SERIES)
    t_ev, stop_rel = judgement.get("t_ev_s"), judgement.get("stop_rel_s")
    if series is None or "rows" not in series or t_ev is None or stop_rel is None:
        return {"status": "not computed (soil_event_series.npz / t_ev_s / stop_rel_s missing)"}
    rows = np.asarray(series["rows"], float)
    after = rows[:, 0] - float(t_ev) > float(stop_rel) + rows_judge.CMP_EPS
    if not after.any():
        return {"samples": 0}
    return {"samples": int(after.sum()),
            "F_cyl_min_N": rows[after, 5:9].min(axis=0).tolist(),
            "lifted_samples": (rows[after, 1:5] <= 0.0).sum(axis=0).astype(int).tolist()}


def soil_event_items(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Spec 426.3 E-1 .. E-7 (``soil_event.judgement.gates``) and the 684.8 mm stroke of a PS-c
    event row; a group without a gate is not judgeable (R18-2), E-2 of a slow event is not
    applicable (:data:`SLOW_EVENT_NOT_APPLICABLE`)."""
    judgement = (result.get("soil_event") or {}).get("judgement") or {}
    gates = judgement.get("gates") or {}
    flags = judgement.get("flags") or []
    is_fast = judgement.get("fast")
    items = []
    for group in SOIL_EVENT_GROUPS:
        values = {name: value for name, value in gates.items() if name.startswith(f"{group}_")}
        if not values and is_fast is False and group in SLOW_EVENT_NOT_APPLICABLE:
            continue
        verdicts = [bool_verdict(value) for value in values.values()] or [NOT_JUDGEABLE]
        verdict = worst(verdicts)
        group_flags = [name for name in flags if str(name).startswith(f"{group}_")]
        if verdict == PASS and group_flags:
            verdict = FLAG
        items.append(item(group, verdict, "result.json soil_event.judgement.gates",
                          gates=values, flags=group_flags))
    stroke = judgement.get("stroke_max_run_mm")
    stroke_ok = None if stroke is None else rows_judge.le(float(stroke), PSC_STROKE_LIMIT_MM)
    items.append(item("stroke_le_684.8mm", bool_verdict(stroke_ok), "soil_event.judgement",
                      value=stroke))
    if is_fast is None:
        items.append(item("event_kind", NOT_JUDGEABLE, "soil_event.judgement.fast missing"))
    return items


def is_soil_event_row(row: RowInput) -> bool:
    """A PS-c event row (``batch.json`` ``d1_select`` psc with a judge role)."""
    return row.entry.get("d1_select") == "psc" and row.role == ROLE_JUDGED


# =============================================================================== bundle items
def j_p3_item(judged_items: dict[str, Any]) -> dict[str, Any] | None:
    """J-P3 (rev8 R8-2): only ③ rows; H-7 = fail, setting defect / S-2 = not judgeable."""
    block = judged_items.get("J-P3_R8-2")
    if not isinstance(block, dict):
        return item("J-P3", NOT_JUDGEABLE, "chrono_rows_judge J-P3_R8-2 missing")
    status = block.get("status")
    if status == rows_judge.J_P3_NOT_APPLICABLE:
        return None
    verdict = {"pass": PASS, "H-7": FAIL}.get(str(status), NOT_JUDGEABLE)
    return item("J-P3", verdict, "recomputed rev8 R8-2", status=status,
                breach_reads=block.get("breach_reads"))


def j11_item(judged_items: dict[str, Any], is_judged: bool) -> dict[str, Any]:
    """J11 (rev8 R8-3): judged on C-5 rows, recorded on the others."""
    block = judged_items.get("J11_R8-3")
    if not isinstance(block, dict):
        return item("J11", NOT_JUDGEABLE if is_judged else None, "J11_R8-3 missing")
    status = block.get("status")
    if not is_judged:
        return item("J11", None, "recomputed rev8 R8-3 (record)", status=status)
    if status in J11_PASS_STATES:
        verdict = PASS
    elif status in J11_STOP_STATES:
        verdict = FAIL
    else:
        verdict = NOT_JUDGEABLE
    return item("J11", verdict, "recomputed rev8 R8-3", status=status,
                n_late=block.get("n_late_fallback_R6_B7"))


def t45_rows(doc: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """``chrono_t45_replay`` rows by case (revision 7 output with ``--t5``)."""
    if doc is None:
        return {}
    if doc.get("criteria") != T45_CRITERIA:
        raise InputError(f"--t45: criteria {doc.get('criteria')!r}, revision 7 output needed "
                         "(v5 criteria revision 7 94)")
    out: dict[str, dict[str, Any]] = {}
    for row in doc.get("rows") or []:
        case = str(row.get("case"))
        if case in out:
            raise InputError(f"--t45 lists {case} twice")
        out[case] = row
    return out


def t45_item(row: dict[str, Any] | None) -> dict[str, Any]:
    """T4-0 / T4 / T5 of one row (revision 6 4.2 .. 4.6 with revision 7)."""
    if row is None:
        return item("T4_T5", NOT_JUDGEABLE, "chrono_t45_replay row missing")
    if not row.get("settings_equal"):
        return item("T4_T5", NOT_JUDGEABLE, "chrono_t45_replay", stop="H-12 monitor setting",
                    setting_differences=row.get("setting_differences"))
    if not row.get("t4_0"):
        return item("T4_T5", NOT_JUDGEABLE, "chrono_t45_replay", stop="T4-0 failed (tool defect)")
    if "T4" not in row or "T5" not in row:
        return item("T4_T5", NOT_JUDGEABLE, "chrono_t45_replay T4 / T5 missing (--t5)")
    over_t4 = int(row["T4"].get("over_0p6kN") or 0)
    over_t5 = int(row["T5"].get("over_0p6kN") or 0)
    verdict = PASS if over_t4 == 0 and over_t5 == 0 else FAIL
    return item("T4_T5", verdict, "chrono_t45_replay (revision 7)", T4_over_0p6kN=over_t4,
                T5_over_0p6kN=over_t5, stop="H-7" if verdict == FAIL else None)


def d2_record(row: RowInput) -> dict[str, Any]:
    """Revision 6 14.5 D2 record (fallback legs, D2 violation start ratio); not a grade."""
    judged = row.judged or {}
    fallback = ((judged.get("origin_check_R5_B1") or {}).get("fallback") or {})
    review = ((((row.result or {}).get("controller_meta") or {}).get("two_pressure") or {})
              .get("review_record") or {})
    return item("D2", None, "record (revision 6 14.5)",
                fallback_event_legs=fallback.get("event_legs"),
                fallback_log_entries=fallback.get("log_entries"),
                d2_violation_start_ratio=review.get("d2_violation_start_ratio"))


# =============================================================================== row grade
def grade_row(row: RowInput, bundle: str, runner_dir: Path | None,
              t45: dict[str, dict[str, Any]], params: dict[str, Any]) -> dict[str, Any]:
    """Grade and items of one row of a graded bundle."""
    judged_items = (row.judged or {}).get("items") or {}
    items: list[dict[str, Any]] = []
    record_items: list[dict[str, Any]] = []
    note = ""
    rigid: RigidResult | None = None
    if row.engine in RUNNER_FILE_SUFFIX:
        rigid = rigid_row(row, bundle, runner_dir)
        items = [item("runner", rigid.grade, "runner judge (rev19 R19-4)",
                      judged_true_items=rigid.judged_true,
                      stop="; ".join(rigid.stops) or None)]
    elif row.result is not None and is_soil_event_row(row):
        items = soil_event_items(row.result)
        record_items += _event_records(row)
    elif row.result is not None:
        note, items, record_items = _scm_items(row, bundle, judged_items, params)
    j_p3 = j_p3_item(judged_items) if row.judged is not None else None
    if j_p3 is not None:
        items.append(j_p3)
    if bundle == "C-5":
        items.append(j11_item(judged_items, is_judged=True))
        if row.case in T45_CASES:
            items.append(t45_item(t45.get(row.case)))
        record_items.append(d2_record(row))
    elif row.judged is not None:
        record_items.append(j11_item(judged_items, is_judged=False))
    grade = _row_grade(row, items)
    out = {"case": row.case, "criteria_id": row.criteria_id, "row_id": row.row_id,
           "engine": row.engine, "role": row.role, "grade": grade, "grade_note": note,
           "items": items, "record_items": record_items, "overrides": [],
           "runner_items": [], "runner_unjudged": [], "runner_count_check_R19_4": None,
           "runner_t_lift_items": [], "t_lift_check_R19_5": None,
           "missing_inputs": row.missing, "inputs_sha256": row.files,
           "result_path": None if row.result_path is None else str(row.result_path)}
    if row.role == ROLE_RECORD:
        out["record_status"] = RECORD_INCOMPLETE if grade == NOT_JUDGEABLE else RECORD_COMPLETE
    if rigid is not None:
        out.update(overrides=rigid.overrides, runner_items=rigid.items,
                   runner_unjudged=rigid.unjudged, runner_count_check_R19_4=rigid.count_check,
                   runner_t_lift_items=rigid.t_lift_items, t_lift_check_R19_5=rigid.t_lift_check)
    return out


def _event_records(row: RowInput) -> list[dict[str, Any]]:
    """Record items of a PS-c event row: the ``p3b`` note, the branch window (rev19 R19-3) and
    the 1 ms rows after it."""
    judgement = ((row.result or {}).get("soil_event") or {}).get("judgement") or {}
    window = {key: judgement.get(key) for key in ("t_ev_s", "stop_rel_s", "stop_reason")}
    return [item("p3b", None, "record (event row judged by 426.3)"),
            item("branch_window", None, "run_S9.judge_chrono_soil_event (rev19 R19-3)",
                 start_rel_s=-0.5, **window),
            item("after_branch", None, "soil_event_series.npz after the branch end (R19-3)",
                 **after_branch_record(row, judgement))]


def as_record(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The entries as record items (their verdict kept under ``verdict_recorded``)."""
    return [{**entry, "verdict_recorded": entry["verdict"], "verdict": None} for entry in entries]


def _scm_items(row: RowInput, bundle: str, judged_items: dict[str, Any], params: dict[str, Any]
               ) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    """(note, items, record items) of an SCM row; a soil-guard S-01 .. S-04 row is graded by
    the five 427.9 conditions alone (rev19 R19-1), its P3 / G6 items recorded."""
    p3b = (row.result or {}).get("p3b")
    if not isinstance(p3b, dict):
        row.missing.append("result.json p3b")
        return "", [], []
    items = p3_items(p3b, judged_items)
    if row.row_id in SAFE_STOP_ROWS:
        grade, block = safe_stop_conditions(row, params)
        if grade is not None:
            safe = item("SGS_427_9", grade, "rev19 R19-1 (427.9 conditions 1 .. 5)", **block)
            recorded = as_record(items)
            if bundle == "C-3":
                recorded.append({**item("G6", None, "chrono_rows_judge g6_grade (record)"),
                                 "verdict_recorded": (row.judged or {}).get("grade"),
                                 "gates": (row.judged or {}).get("gates")})
            note = ("soil-guard stop: the five 427.9 conditions decide the row (rev19 R19-1); "
                    f"recorded: {', '.join(SAFE_STOP_RECORDED)}")
            return note, [safe], recorded
    if bundle == "C-3":
        return _g6_items(row, items)
    return "", items, []


def _g6_items(row: RowInput, p3: list[dict[str, Any]]
              ) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    """C-3 (P3 + G6) without a soil-guard stop: the G6 grade of ``chrono_rows_judge`` and the
    P3 items G6 does not cover (:data:`G6_EXTRA_P3`)."""
    judged = row.judged or {}
    g6 = judged.get("grade")
    if g6 is None:
        row.missing.append("chrono_rows_judge G6 grade")
        return "", [], []
    word = ALLOWED_STOP if g6 == "stroke_limited_stop" else _verdict_word(g6)
    g6_entry = item("G6", word, "chrono_rows_judge g6_grade", gates=judged.get("gates"),
                    grade_note=judged.get("grade_note"))
    extra = [entry for entry in p3 if entry["item"] in G6_EXTRA_P3]
    covered = [entry for entry in p3 if entry["item"] not in G6_EXTRA_P3]
    return "", [g6_entry, *extra], as_record(covered)


def _row_grade(row: RowInput, items: list[dict[str, Any]]) -> str:
    """Original 8.1 worst of the judged items; a missing input = not judgeable (9.3)."""
    if row.missing:
        return NOT_JUDGEABLE
    verdicts = [entry["verdict"] for entry in items if entry["verdict"] is not None]
    if not verdicts:
        row.missing.append("no judged item")
        return NOT_JUDGEABLE
    return worst(verdicts)


# =============================================================================== bundle grade
def row_stops(rows: list[dict[str, Any]], judge_doc: dict[str, Any] | None
              ) -> list[dict[str, str]]:
    """Stops of the bundle rows: the judge doc's stops of these cases and the item stops."""
    cases = {row["case"] for row in rows}
    stops = [dict(stop) for stop in (judge_doc or {}).get("stops") or []
             if stop.get("case") in cases]
    for row in rows:
        for entry in row["items"]:
            if entry.get("stop"):
                stops.append({"case": row["case"], "reason": f"{entry['item']}: {entry['stop']}"})
    return stops


def vb_specific_failures(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Revision 12 2.2: a VB row failing while its V0 / V0v pair passes is asked."""
    by_case = {row["case"]: row for row in rows}
    found = []
    for case, row in by_case.items():
        for suffix in V0_PAIR_SUFFIXES:
            pair = by_case.get(case + suffix)
            if pair is None:
                continue
            if row["grade"] == FAIL and pair["grade"] in (PASS, FLAG, ALLOWED_STOP):
                found.append({"case": case, "reason": f"VB-specific failure: {case} fail, "
                                                      f"{pair['case']} {pair['grade']} "
                                                      "(revision 12 2.2, ask)"})
    return found


def found_vb_v0_pairs(cases: set[str]) -> list[tuple[str, str]]:
    """(VB case, V0 / V0v case) pairs among the names (:data:`V0_PAIR_SUFFIXES`)."""
    return sorted((case, case + suffix) for case in cases for suffix in V0_PAIR_SUFFIXES
                  if case + suffix in cases)


def c5_pair_check(rows: list[dict[str, Any]], manifest_cases: list[str]) -> dict[str, Any]:
    """Rev19 R19-6: the VB / V0 pairs found in the union of the C-5 ``batch.json`` cases and
    the manifest C-5 rows against :data:`C5_VB_V0_PAIRS` (revision 12 2.1; S-15)."""
    batch_cases = {row["case"] for row in rows}
    found = set(found_vb_v0_pairs(batch_cases | set(manifest_cases)))
    expected = set(C5_VB_V0_PAIRS)
    return {"rule": "rev19 R19-6 / v5 criteria revision 12 2.1: exactly the six VB / V0 pairs "
                    "(S-15), names from batch.json cases and the manifest",
            "expected": sorted(expected), "found": sorted(found),
            "found_in_batch_json": sorted(found_vb_v0_pairs(batch_cases)),
            "missing": sorted(expected - found), "extra": sorted(found - expected),
            "ok": found == expected}


def t_lift_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Rev19 R19-5 per bundle: runner lift-off items, the D8 items re-computed, the t_lift
    differences and the rows that stop."""
    by_case = {row["case"]: row["runner_t_lift_items"] for row in rows
               if row.get("runner_t_lift_items")}
    checks = {row["case"]: row["t_lift_check_R19_5"] for row in rows
              if row.get("t_lift_check_R19_5")}
    differences = [c["difference_s"] for c in checks.values() if c.get("difference_s") is not None]
    return {"recomputed_D8": [name for name, _ in D8_ITEMS],
            "runner_value_kept": list(RUNNER_T_LIFT_KEPT),
            "present": sorted({name for names in by_case.values() for name in names}),
            "by_case": by_case, "checks": checks,
            "max_difference_s": max(differences) if differences else None,
            "stop_rows": sorted(case for case, c in checks.items() if c.get("stop"))}


def unjudged_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Rev19 R19-4: ``러너 미판정`` items per bundle (count, rows, names; unknown kinds apart)."""
    by_case = {row["case"]: row["runner_unjudged"] for row in rows if row.get("runner_unjudged")}
    entries = [entry for found in by_case.values() for entry in found]
    return {"label": RUNNER_UNJUDGED, "count": len(entries), "rows": sorted(by_case),
            "items": dict(sorted(Counter(entry["item"] for entry in entries).items())),
            "unknown_kind_items": sorted({entry["item"] for entry in entries
                                          if entry["branch"] == "unknown_kind"}),
            "by_case": by_case}


def pair_record(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """C-5 pairs (VB / V0, LS - VB) side by side (record)."""
    by_case = {row["case"]: row["grade"] for row in rows}
    pairs = []
    for case, grade in by_case.items():
        for suffix in (*V0_PAIR_SUFFIXES, "_LS1", "_LS4"):
            if case + suffix in by_case:
                pairs.append({"base": case, "base_grade": grade, "pair": case + suffix,
                              "pair_grade": by_case[case + suffix]})
    return pairs


PHRASE_PARTS = (("통과", (PASS, FLAG)), ("안전 종료", (ALLOWED_STOP,)), ("미달", (FAIL,)),
                ("판정 불가", (NOT_JUDGEABLE,)))
"""Row count phrase: spec 427.9 counts the safe stop separately from the pass ("따로 센다");
the bundle status still counts it on the pass side."""


def row_phrase(judged: list[dict[str, Any]]) -> str:
    """``통과 4 / 안전 종료 2`` (a part with 0 rows is left out, except 통과)."""
    parts = []
    for label, grades in PHRASE_PARTS:
        count = sum(1 for row in judged if row["grade"] in grades)
        if count or label == "통과":
            parts.append(f"{label} {count}")
    return " / ".join(parts)


def unique_stops(stops: list[dict[str, str]]) -> list[dict[str, str]]:
    """The stops without repeats (the judge doc and this tool can name the same stop)."""
    seen, out = set(), []
    for stop in stops:
        key = (stop.get("case"), stop.get("reason"))
        if key not in seen:
            seen.add(key)
            out.append(stop)
    return out


def bundle_grade(rows: list[dict[str, Any]], count_ok: bool, has_stop: bool) -> dict[str, Any]:
    """Original 8.1 bundle status over the judged rows (record rows reported only).

    A stop (original 8.2) withholds the grade: it is kept as ``grade_without_stop`` and the
    judgement asks first.
    """
    judged = [row for row in rows if row["role"] == ROLE_JUDGED]
    record = [row for row in rows if row["role"] == ROLE_RECORD]
    out: dict[str, Any] = {
        "judged_rows": len(judged), "record_rows": len(record),
        "grade_counts": dict(sorted(Counter(row["grade"] for row in judged).items())),
        "allowed_stop_rows": [row["case"] for row in judged if row["grade"] == ALLOWED_STOP],
        "flag_rows": [row["case"] for row in judged if row["grade"] == FLAG],
        "record_rows_reported": [{"case": row["case"], "grade": row["grade"]} for row in record
                                 if row["grade"] in (FAIL, NOT_JUDGEABLE)],
        "missing_count": sum(len(row["missing_inputs"]) for row in rows),
        "row_phrase": row_phrase(judged)}
    if not count_ok:
        out.update(grade=None, status=None, reason="S-15: row count differs, no grade")
    elif not judged:
        out.update(grade=None, status=None, reason="no judged row, no grade")
    else:
        grade = worst([row["grade"] for row in judged])
        out["grade_without_stop"] = grade
        if has_stop:
            out.update(grade=None, status=None, reason="stop (original 8.2): ask before a grade")
        else:
            out.update(grade=grade, status=BUNDLE_STATUS[grade])
    return out


# =============================================================================== record bundles
def openloop_row(row: RowInput) -> dict[str, Any]:
    """C-6 / C-7 (original 7.5): P3a-1 .. 5 and the spec 11047 FLAG of one row."""
    p3a = (row.result or {}).get("p3a")
    if not isinstance(p3a, dict):
        row.missing.append("result.json p3a")
        return {"case": row.case, "criteria_id": row.criteria_id, "complete": False,
                "missing_inputs": row.missing, "inputs_sha256": row.files}
    checks = p3a.get("checks") or {}
    values = {name: checks.get(name) for name in OPENLOOP_CHECKS}
    before = ((p3a.get("P3a-9_min_cylinder_force") or {}).get("before_liftoff") or {})
    flag = before.get("any_flag")
    missing = [name for name, value in values.items() if not isinstance(value, bool)]
    if not isinstance(flag, bool):
        missing.append("P3a-9_min_cylinder_force.before_liftoff.any_flag")
    row.missing += missing
    return {"case": row.case, "criteria_id": row.criteria_id, "checks": values,
            "abort": checks.get("abort"), "spec_11047_flag": flag,
            "report_separately": bool(values.get("P3a-1_within") is False or checks.get("abort")),
            "complete": not row.missing, "missing_inputs": row.missing,
            "inputs_sha256": row.files}


def oc5_rows(paths: list[Path]) -> dict[str, tuple[dict[str, Any], Path]]:
    """``resume4368_judge.py oc5`` outputs by case (the case = folder of ``result``)."""
    out: dict[str, tuple[dict[str, Any], Path]] = {}
    for path in paths:
        doc = read_json(path, "--oc5 output")
        case = Path(str(doc.get("result") or "")).parent.name
        if case in out:
            raise InputError(f"--oc5: two outputs of {case}")
        out[case] = (doc, path)
    return out


def fmin_rows(paths: list[Path]) -> dict[str, tuple[dict[str, Any], Path]]:
    """``resume4368_judge.py fmin-time`` outputs by case (the case = folder ``case``)."""
    out: dict[str, tuple[dict[str, Any], Path]] = {}
    for path in paths:
        doc = read_json(path, "--fmin-time output")
        case = Path(str(doc.get("case") or "")).name
        if case in out:
            raise InputError(f"--fmin-time: two outputs of {case}")
        out[case] = (doc, path)
    return out


def oc5_row(row: RowInput, oc5: dict[str, tuple[dict[str, Any], Path]],
            fmin: dict[str, tuple[dict[str, Any], Path]]) -> dict[str, Any]:
    """C-8 (original 7.4, rev1 RV1-7, rev2 R2-5 / R2-6): m, class and the two times."""
    out: dict[str, Any] = {"case": row.case, "criteria_id": row.criteria_id}
    stops = []
    oc5_doc = _attach(row, oc5, "oc5", out)
    if oc5_doc is not None:
        out.update(m_N=oc5_doc.get("m_N"), min_leg=oc5_doc.get("min_leg"),
                   margin_N=oc5_doc.get("margin_N"), oc5_class=oc5_doc.get("class"),
                   oc5_status=oc5_doc.get("status"),
                   R_c_operating=(oc5_doc.get("values") or {}).get("R_c_operating"))
        if oc5_doc.get("class") is None:
            row.missing.append(f"oc5 class ({oc5_doc.get('status')})")
        if oc5_doc.get("class") == "stop_S9" and row.criteria_id in S9_HANDLED_CRITERIA:
            out["S-9_handled"] = S9_HANDLED_TEXT
        elif oc5_doc.get("class") == "stop_S9":
            stops.append({"case": row.case, "reason": "S-9 (original 7.4)"})
        if str(oc5_doc.get("status", "")).startswith("R_c > 1"):
            stops.append({"case": row.case, "reason": "S-10 (R_c > 1)"})
    fmin_doc = _attach(row, fmin, "fmin-time", out)
    if fmin_doc is not None:
        out["fmin_time"] = {key: fmin_doc.get(key) for key in
                            ("t_D_s", "window_complete", "F_below_F_min",
                             "F_below_F_min_plus_2kN", "status")}
        if fmin_doc.get("status") != "기록":
            row.missing.append(f"fmin-time ({fmin_doc.get('status')})")
    out.update(complete=not row.missing, missing_inputs=row.missing, stops=stops,
               inputs_sha256=row.files)
    return out


def _attach(row: RowInput, docs: dict[str, tuple[dict[str, Any], Path]], what: str,
            out: dict[str, Any]) -> dict[str, Any] | None:
    found = docs.get(row.case)
    if found is None:
        row.missing.append(f"{what} output")
        return None
    doc, path = found
    row.files[f"{what}:{path.name}"] = rows_judge.sha256_file(path)
    out[f"{what}_file"] = str(path)
    return doc


# =============================================================================== command
def load_rows_judge(path: str | None, git_at_start: str) -> dict[str, Any] | None:
    """The ``chrono_rows_judge_4368.py judge`` output (sealed, rev6 definitions, same commit)."""
    if path is None:
        return None
    doc = read_json(Path(path), "--rows-judge output")
    if not (doc.get("seals") or {}).get("ok"):
        raise InputError(f"--rows-judge {path}: its seal check is not ok (S-1)")
    if doc.get("deviates_from_rev6"):
        raise InputError(f"--rows-judge {path}: --assume output is not a path 1 result")
    recorded = str((doc.get("commit_identity_R11_4") or {}).get("git_at_start") or "")
    if not (recorded.startswith(git_at_start) or git_at_start.startswith(recorded)) or not recorded:
        raise InputError(f"--rows-judge {path}: git_at_start {recorded!r} is not {git_at_start}")
    return doc


def commit_stops(rows: list[RowInput], git_at_start: str) -> tuple[list[dict], dict[str, Any]]:
    """Rev11 R11-4 commit identity of every row (S-12)."""
    stops, by_case = [], {}
    for row in rows:
        identity = rows_judge.commit_identity_of(row.entry, row.result,
                                                 is_open_loop=row.engine == "openloop",
                                                 git_at_start=git_at_start)
        by_case[row.case] = identity["status"]
        if identity["status"] == rows_judge.COMMIT_STOP:
            stops.append({"case": row.case, "reason": f"S-12: {'; '.join(identity['problems'])}"})
    return stops, by_case


def cmd_grade(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    """The ``grade`` subcommand: bundle rows, row grades, bundle grade and stops."""
    bundle = args.bundle
    git_at_start = rows_judge.parse_git_at_start(args.git_at_start)
    seals = rows_judge.seal_check(Path(args.rules_dir))
    if seals["missing"]:
        raise InputError(f"rules files missing: {seals['missing']}")
    manifest_path = Path(args.manifest)
    manifest = rows_judge.load_manifest(manifest_path)
    if not args.batch:
        raise InputError("no --batch given")
    entries, count = bundle_entries(bundle, [Path(b) for b in args.batch], manifest)
    judge_doc = load_rows_judge(args.rows_judge, git_at_start)
    if bundle in GRADED_BUNDLES and judge_doc is None:
        raise InputError(f"{bundle}: --rows-judge is required")
    judged_by_case = judged_rows_by_case(judge_doc)
    is_record = bundle in RECORD_BUNDLES
    inputs = [load_row_input(batch, entry, judged_by_case.get(str(entry.get("case"))), bundle)
              for batch, entry in entries]
    stops, identity = commit_stops(inputs, git_at_start)
    if not count["ok"]:
        stops.append({"case": "*", "reason": f"S-15: {count['found']} rows, expected "
                                             f"{count['expected']} (rules rev18 R18-2)"})
    doc: dict[str, Any] = {
        "tool": TOOL_VERSION, "rules": RULES_TEXT, "bundle": bundle, "git_at_start": git_at_start,
        "seals": seals, "row_count_S15": count, "commit_identity_R11_4": identity,
        "manifest": {"path": str(manifest_path), "sha256": rows_judge.sha256_file(manifest_path)},
        "inputs": _input_files(args, judge_doc)}
    if is_record:
        stops = unique_stops(stops + _record_bundle(doc, bundle, inputs, args, count["ok"]))
    else:
        stops = _graded_bundle(doc, bundle, inputs, args, judge_doc, count["ok"], stops)
    doc["stops"] = stops
    code = 0 if seals["ok"] and not stops else 1
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(doc, indent=1, ensure_ascii=False,
                                         default=rows_judge._json_default) + "\n",
                              encoding="utf-8", newline="\n")
    summary = {"bundle": bundle, "rows": len(inputs), "seals_ok": seals["ok"],
               "row_count_ok": count["ok"], "stops": len(stops),
               "result": doc.get("bundle_grade") or doc.get("record_status"), "out": str(args.out)}
    return code, summary


def _graded_bundle(doc: dict[str, Any], bundle: str, inputs: list[RowInput],
                   args: argparse.Namespace, judge_doc: dict[str, Any] | None,
                   count_ok: bool, prior_stops: list[dict[str, str]]) -> list[dict[str, str]]:
    """Row grades, C-5 extras and the bundle grade into ``doc``; returns every stop."""
    runner_dir = Path(args.runner_judge_dir) if args.runner_judge_dir else None
    t45_doc = read_json(Path(args.t45), "--t45 output") if args.t45 else None
    t45 = t45_rows(t45_doc)
    params = rows_judge.load_params(Path(args.params))
    doc["params"] = {key: params[key] for key in ("path", "sha256", "head_area_m2", "F_min_N")}
    rows = [grade_row(row, bundle, runner_dir, t45, params) for row in inputs]
    stops = row_stops(rows, judge_doc)
    if bundle == "C-5":
        pairs = c5_pair_check(rows, doc["row_count_S15"]["manifest_cases"])
        doc["vb_v0_pairs_S15"] = pairs
        if not pairs["ok"]:
            count_ok = False
            stops.append({"case": "*", "reason": f"S-15: VB / V0 pairs differ from revision 12 "
                                                 f"2.1 (missing {pairs['missing']}, extra "
                                                 f"{pairs['extra']})"})
        stops += vb_specific_failures(rows)
        doc["pairs_record"] = pair_record(rows)
        doc["t4_t5_phrase"] = _t45_phrase(rows)
    stops = unique_stops(prior_stops + stops)
    doc["rows"] = rows
    doc["runner_t_lift_R19_5"] = t_lift_summary(rows)
    doc["runner_unjudged_R19_4"] = unjudged_summary(rows)
    doc["bundle_grade"] = bundle_grade(rows, count_ok, has_stop=bool(stops))
    return stops


def _t45_phrase(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Revision 6 4.6 result phrase over the 18 T4 / T5 rows."""
    entries = [entry for row in rows for entry in row["items"] if entry["item"] == "T4_T5"]
    verdicts = Counter(entry["verdict"] for entry in entries)
    if len(entries) != len(T45_CASES) or verdicts.get(NOT_JUDGEABLE):
        phrase = "판정 안 함 (T4-0 / 설정 / 입력)"
    elif verdicts.get(FAIL):
        phrase = "불일치 (H-7)"
    else:
        phrase = "일치 (등급 부분: ML 216 없음, Chrono 18행)"
    return {"rows": len(entries), "expected": len(T45_CASES), "verdicts": dict(verdicts),
            "phrase": phrase}


def _record_bundle(doc: dict[str, Any], bundle: str, inputs: list[RowInput],
                   args: argparse.Namespace, count_ok: bool) -> list[dict[str, str]]:
    stops: list[dict[str, str]] = []
    if bundle == "C-6C7":
        rows = [openloop_row(row) for row in inputs]
    else:
        oc5 = oc5_rows([Path(p) for p in args.oc5 or []])
        fmin = fmin_rows([Path(p) for p in args.fmin_time or []])
        rows = [oc5_row(row, oc5, fmin) for row in inputs]
        stops = [stop for row in rows for stop in row["stops"]]
    doc["rows"] = rows
    if not count_ok or not rows:
        doc["record_status"] = None
    else:
        doc["record_status"] = RECORD_COMPLETE if all(r["complete"] for r in rows) else \
            RECORD_INCOMPLETE
    return stops


def _input_files(args: argparse.Namespace, judge_doc: dict[str, Any] | None) -> dict[str, Any]:
    files: dict[str, Any] = {}
    for name in ("rows_judge", "t45"):
        value = getattr(args, name, None)
        if value:
            files[name] = {"path": value, "sha256": rows_judge.sha256_file(Path(value))}
    if judge_doc is not None:
        files["rows_judge_tool"] = judge_doc.get("tool")
    if args.runner_judge_dir:
        files["runner_judge_dir"] = args.runner_judge_dir
    return files


def build_parser() -> argparse.ArgumentParser:
    """Command line (``grade``, ``seals``)."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    grade = sub.add_parser("grade", help="bundle grade (graded) or record status of one bundle")
    grade.add_argument("--bundle", required=True, choices=tuple(EXPECTED_ROWS))
    grade.add_argument("--git-at-start", required=True, help="run commit R2 (rev18 R18-4)")
    grade.add_argument("--batch", action="append", help="S9 batch folder with batch.json")
    grade.add_argument("--rows-judge", help="chrono_rows_judge_4368.py judge output (C-1 .. C-5)")
    grade.add_argument("--runner-judge-dir",
                       help="folder of <C1|C2|C5>_<case>.verify_S8C.json / .verify_S6C.json")
    grade.add_argument("--t45", help="chrono_t45_replay output (--t5, rev7) for C-5")
    grade.add_argument("--oc5", action="append", help="resume4368_judge.py oc5 output (C-8)")
    grade.add_argument("--fmin-time", action="append",
                       help="resume4368_judge.py fmin-time output (C-8)")
    grade.add_argument("--params", default=str(rows_judge.ROOT / "02_params" / "rexome33.yaml"),
                       help="params YAML (head areas, F_min) for the 427.9 conditions (R19-1)")
    grade.add_argument("--manifest", default=str(rows_judge.MANIFEST_DEFAULT))
    grade.add_argument("--rules-dir", default=str(rows_judge.RULES_DIR_DEFAULT))
    grade.add_argument("--out", required=True)
    seals = sub.add_parser("seals", help="rules seal check (the chrono_rows_judge seal list)")
    seals.add_argument("--rules-dir", default=str(rows_judge.RULES_DIR_DEFAULT))
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point; prints ``errors N`` and a final JSON line."""
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        code = 0 if exc.code == 0 else 2
        print("errors", 0 if code == 0 else 1)
        print(json.dumps({"exit": code, "error": "argument error" if code else None}))
        return code
    try:
        if args.cmd == "grade":
            code, summary = cmd_grade(args)
        else:
            summary = rows_judge.seal_check(Path(args.rules_dir))
            code = 2 if summary["missing"] else (0 if summary["ok"] else 1)
    except InputError as exc:
        print("errors 1")
        print(json.dumps({"exit": 2, "error": str(exc)}, ensure_ascii=False))
        return 2
    except Exception as exc:  # noqa: BLE001 - exit 3 with the trace on stderr
        traceback.print_exc()
        print("errors 1")
        print(json.dumps({"exit": 3, "error": f"{type(exc).__name__}: {exc}"},
                         ensure_ascii=False))
        return 3
    print("errors", 0 if code == 0 else 1)
    print(json.dumps({"exit": code, **summary}, ensure_ascii=False,
                     default=rows_judge._json_default))
    return code


if __name__ == "__main__":
    sys.exit(main())
