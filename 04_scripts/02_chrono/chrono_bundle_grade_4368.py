"""436.8 Chrono path 1 bundle grades (rules rev18 R18-2 as rewritten by rev19 R19-1 .. R19-6;
python-expert 2026-11-15).

Aggregates the row grades of one Chrono bundle from inputs other path 1 tools already wrote;
it runs no simulation and no other judge:

* L2b / L1-R rows: the runner judge output (``run_S8C.py judge`` -> ``verify_S8C``,
  ``run_S6C.py judge`` -> ``verify_S6C``), one file per row named
  ``<C1|C2|C5>_<case>.verify_S8C.json`` / ``.verify_S6C.json`` in ``--runner-judge-dir`` (the form
  of ``judge_b9f5707/chrono_path1/runner_judge/``). Rev23 R23-1: inside that file the row's runner
  rows (``case``) and its ``s8_metrics`` key are the inner name of the judged row ``dir`` (last path
  name, exact match; :func:`row_inner_name`), ``*`` rows as before; checks 1 .. 4 (``dir`` set,
  ``dir`` unique in the bundle, no other runner row ``case``, no other ``s8_metrics`` key) are
  S-11 stops, record ``runner_name_map_R23_1`` (:func:`runner_name_map`). Rev19 R19-4: the
  runner's own count decides
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
  :func:`p3_items`); every replaced item keeps its runner and re-computed values. Rules rev24
  CD-2: a runner item is replaced only on a whole-name match with the closed table, on the rows
  of its line (``4 max moving pressure`` event-free rows, ``... outside the event transient`` and
  ``4 max pressure in the event transient`` event rows by the row judge's CD-3 test, ``4
  saturation steps`` every L2b row); a W end more than 0.1 s from the original judge's, or one
  that changes a verdict, stops the bundle (:func:`event_window_stop`).
* Rules rev24 CD-5 (:func:`p3_items`): a run without a first READY judges P3-1 on the recontact
  condition only, P3-4 / P3-5 are ``해당 없음(READY 없음)``, P3-6 fails; an SCM row without a
  graded item is not judgeable. CD-7 (:func:`reason_check`): every not-judgeable, runner-unjudged
  or not-applicable item and not-judgeable row carries a reason, a replaced item the reason of
  the change; a missing one stops the bundle. CD-11 (:func:`item_list`): the graded items of
  every row (``item_list_CD_11``); an empty row or another row count stops the bundle.
* Rules rev25 (common block replacing rev24's): CD-4 P3-6 against the spec 421.1 limit of the run
  args (:func:`p36_item`; a limit unlike the runner P3b ``limit_s`` stops), graded on C-5 SCM
  rows only and a record elsewhere; P3-9 a record on every row; CD-5 P3-6 without READY fails
  where graded and is ``해당 없음(READY 없음)`` where recorded; CD-8 values 1 / 7 / 8 / 9 from the
  1 ms record (:func:`scm_force_minima`, :func:`scm_d8_values`, :func:`g6_record_values`; O-C5
  P3-5 ``해당 없음(rigid_base)``); CD-11 classes (graded / gate / record), clause ids, the C-3
  G6 table and the 427.9 conditions one id each, ``[case *]`` runner items, record rows exempt
  from ">= 1 graded item". The C-4 record bundle stops on an empty reason (CD-7, a rev24 fix).
* S-01 .. S-04 (rev19 R19-1): a row whose first ``FAULT*`` event is the soil guard is graded by
  the five 427.9 conditions alone, computed here from the run files with the R19-1 windows
  (:func:`safe_stop_conditions`); every P3 / G6 item becomes a record.
* Bundle rules (:func:`bundle_grade`): C-1 / C-2 / C-3 = ``d1_selection_rules.md`` 11 (+ rev1),
  C-5 = v5 criteria revision 12 / 12a / 12b (T4 / T5 from ``chrono_t45_replay`` ``--t45``, J11,
  J-P3, D2 record, P3 items, exactly the six VB / V0 pairs of revision 12 2.1 or S-15); the t45
  rows are paired with the judged rows by the t45 input folder order, not by name (rev22 R22-1,
  :func:`t45_pairing`: list rebuilt from ``judge_C5.json``, fixed against the R3c one
  ``--t45-reference-judge``, ``$T45Cases`` of ``--t45-cases-script``, optional ``--t45-folders``;
  record ``t45_pairing_R22_1``; a count mismatch is S-15, any other mismatch S-11); bundle
  status by original 8.1 (not judgeable > fail > pass), the row phrase counts the safe stops
  apart.
* Record bundles: C-6 / C-7 ``result.json`` ``p3a`` (P3a-1 .. 5, spec 11047 FLAG), C-8 the
  ``resume4368_judge.py oc5`` and ``fmin-time`` outputs (``--oc5``, ``--fmin-time``) with the
  rules rev24 CD-8 record values (:func:`c8_record_values`; P3 values from ``--rows-judge``), C-4
  the rules rev24 CD-9 record rows (:func:`c4_row`, ``--rows-judge``; P3-5 on a rigid base
  ``해당 없음(rigid_base)``).
* Row count (S-15): rows from the ``batch.json`` ``cases[]`` of the bundle criteria, each one a
  row of the manifest bundle, against :data:`EXPECTED_ROWS`; a mismatch is S-15 and the bundle
  gets no grade, a bundle without rows gets no grade either. A missing row input makes that row
  not judgeable (original 9.3).

CLI (Chrono-dev or python-dev, no simulation)::

    python -I -B -X utf8 04_scripts/02_chrono/chrono_bundle_grade_4368.py grade --bundle C-1 \
        --git-at-start <R2> --batch <07_results/S9/batch_...> [--batch ...] \
        --rows-judge <judge_C1.json> --runner-judge-dir <runner_judge> --out <out.json>
    ... grade --bundle C-5 ... --t45 <t45_C5.json> --t45-reference-judge <R3c judge_C5.json> \
        --t45-cases-script <R3c run_path1_r3c.ps1> [--t45-folders <list>]
    ... grade --bundle C-6C7 --git-at-start <R2> --batch <...C6C7...> --out <out.json>
    ... grade --bundle C-8 --git-at-start <R2> --batch <...OC5...> --oc5 <a.json> --oc5 <b.json> \
        --fmin-time <a.json> --fmin-time <b.json> --rows-judge <judge_OC5.json> --out <out.json>
    ... grade --bundle C-4 --git-at-start <R2> --batch <...C4...> --rows-judge <judge_C4.json> \
        --out <out.json>
    ... seals [--rules-dir <verif_matrix>]

Exit codes: 0 done without a stop; 1 a stop (S-15, S-12, H-7, R40-2 hold, S-2, J11, T4-0,
VB-specific failure, S-9 / S-10 record, rev23 R23-1 S-11, rev24 CD-3 window end, CD-7 reason,
CD-11 item list) or a seal mismatch; 2 an input is missing or invalid; 3 internal error. The
last stdout line is JSON, the line before it ``errors N``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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

TOOL_VERSION = ("chrono_bundle_grade_4368 v7 (python-expert 2026-11-16, rules rev18 R18-2, rev19, "
                "rev21, rev22 R22-1, rev23 R23-1, rev24 CD-2 / CD-5 / CD-7 / CD-8 / CD-9 / "
                "CD-11, rev25 CD-4 P3-6 / CD-5 / CD-8 / CD-11)")
RULES_TEXT = ("rules rev18 R18-2 (bundle grades of path 1), R18-2a, R18-4, rewritten by rev19 "
              "R19-1 .. R19-6, rev21 R21-1 / R21-2, rev22 R22-1 (t45 pairing by input folder "
              "order), rev23 R23-1 (runner rows and s8_metrics by the inner name of the judged "
              "row dir), rev24 R24-2 path 1 (common definitions CD-2 override table, CD-3 window "
              "stop, CD-5 READY missing, CD-7 reasons, CD-8 C-8 record values, CD-9 C-4 record "
              "bundle, CD-11 item list), rev25 R25-2 path 1 (common block rev25: CD-4 P3-6 role "
              "and spec 421.1 limit, CD-5 P3-6 lines, P3-9 record, CD-8 values 1 / 7 / 8 / 9, "
              "CD-11 classes, clause ids, G6 table, [case *]; C-4 CD-7 stop); original 5.2 / "
              "7.4 / 7.5 / 8.1 / 8.2 / 9.3; "
              "d1_selection_rules.md 7 / 11 + rev1; v5 criteria revision 6 4.6, 12 / 12a / 12b; "
              "rev6 R6-A / R6-B4 / R6-B5 / R6-B8 / R6-B9; seal list of chrono_rows_judge_4368.py")

# --- bundles ---------------------------------------------------------------------------------
EXPECTED_ROWS = {"C-1": 10, "C-2": 6, "C-3": 2, "C-4": 4, "C-5": 35, "C-6C7": 3, "C-8": 2}
"""Rules rev18 R18-2 row count check (S-15); C-4 4 rows by rules rev24 CD-9."""
BUNDLE_CRITERIA = {"C-1": ("C-1",), "C-2": ("C-2",), "C-3": ("C-3",), "C-4": ("C-4",),
                   "C-5": ("C-5",), "C-6C7": ("C-6", "C-7", "C-7a", "C-7b"),
                   "C-8": ("C-8a", "C-8b")}
"""``batch.json`` ``criteria_id`` values of each bundle (original 5.2 table, rev4 R4-A3)."""
GRADED_BUNDLES = ("C-1", "C-2", "C-3", "C-5")
RECORD_BUNDLES = ("C-4", "C-6C7", "C-8")
RUNNER_FILE_PREFIX = {"C-1": "C1", "C-2": "C2", "C-5": "C5"}
"""Runner judge file name prefix (``judge_b9f5707/chrono_path1/runner_judge/C1_<case>...``)."""
RUNNER_FILE_SUFFIX = {"L2b": "verify_S8C", "L1R": "verify_S6C"}
R23_1_RULE = "rev23 R23-1"
R23_1_CHECKS = ("1_dir_set", "2_dir_unique", "3_runner_row_cases", "4_s8_metrics_keys")
"""Rev23 R23-1 checks 1 .. 4 of a row that reads a runner judge file (a false one is S-11)."""

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
C1_D8_ITEM = ("C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) "
              ">= F_min + 5 kN")
MOVING_ITEM = "4 max moving pressure"
OUTSIDE_W_ITEM = "4 max moving pressure outside the event transient"
INSIDE_W_ITEM = "4 max pressure in the event transient"
SATURATION_ITEM = "4 saturation steps"
ROWS_ALL, ROWS_EVENT_FREE, ROWS_EVENT = "all L2b rows", "event-free rows", "event rows"
RIGID_OVERRIDES = (
    (C1_D8_ITEM, "C1_R40", "D-31 / D-39", ROWS_ALL),
    (MOVING_ITEM, "moving_pressure_D-32", "D-32", ROWS_EVENT_FREE),
    (OUTSIDE_W_ITEM, "moving_pressure_D-32", "D-32 CD-3 outside W", ROWS_EVENT),
    (INSIDE_W_ITEM, "moving_pressure_D-32", "D-32 CD-3 inside W", ROWS_EVENT),
    (SATURATION_ITEM, "moving_pressure_D-32", "D-32", ROWS_ALL),
)
"""Rules rev24 CD-2 table (closed): (runner item name, ``chrono_rows_judge`` item, rule label,
rows it applies to). A runner item is replaced only when its whole name is equal; on other rows
the runner count stays (the saturation of an event row is the outside-W one, CD-3)."""
D8_OVERRIDE_ITEMS = ("D8 min true cylinder force >= F_min + 5 kN", "D8 no pad lift-off")
"""Rules rev24 CD-2: the two pads D8 items re-computed from the D-29 t_lift (whole-name match)."""
NOT_APPLICABLE_STATUS = "not_applicable"
READY_MISSING = rows_judge.READY_MISSING
INPUT_MISSING = "원 입력 결측"
RUNNER_HOLD = "원 판정기 보류"
CD7_RULE = ("rules rev24 CD-7: every not-judgeable / runner-unjudged / not-applicable item and "
            "every not-judgeable row has a one-line reason, a replaced item the reason of the "
            "change")
CD11_RULE = ("rules rev25 CD-11: per row the items (common id, class graded / gate / record, "
             "item name, clause id, description, method, interval, verdict, reason); one list row "
             "per bundle row, >= 1 graded item each except record rows")
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
R3C_JUDGE_C5_SHA256 = "c1ba93823eee39c47b099042193ad54e29ae513bb7cbda3ae52a8437b27ad76a"
"""Rev22 R22-1: sha256 of the R3c ``judge_C5.json`` the t45 input folder list was built from
(``--t45-reference-sha256`` default)."""
T45_SCRIPT_RE = re.compile(r"\$T45Cases\s*=\s*@\((.*?)\)", re.S)
R22_1_RULE = ("rev22 R22-1: t45 row i <-> i-th t45 input folder (judge_C5.json rows in order, "
              "case in T45_CASES, their dir) <-> the judged row with that dir; checks 1 (count, "
              "S-15) and 2 .. 4 (dir, inner name, unique, target set; S-11)")
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
T_LIFT_1MS_BASIS = rows_judge.T_LIFT_SUS_BASIS
"""``chrono_rows_judge`` ``D8_t_lift_basis`` of the 1 ms D-29 t_lift,sus (rev21 R21-1; else the
R15-3 bracket dict)."""
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
    runner_name_map: dict[str, Any] | None = None
    """Rev23 R23-1 entry of an L2b / L1-R row (:func:`runner_name_entry`), None otherwise."""


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


def runner_items(doc: dict[str, Any], inner: str | None) -> list[dict[str, Any]]:
    """Runner judge rows of the row and of the whole batch (``*``) as row items.

    The row's runner rows are those whose ``case`` is ``inner``, the inner name of the judged
    row ``dir`` (rev23 R23-1, exact match); without an inner name only the ``*`` rows.
    """
    wanted = ("*",) if inner is None else (inner, "*")
    items = []
    for runner_row in doc.get("rows") or []:
        if runner_row.get("case") not in wanted:
            continue
        verdict, branch = runner_verdict(runner_row)
        entry = item(str(runner_row.get("item")), verdict, "runner",
                     value=runner_row.get("value"), limit=runner_row.get("limit"),
                     kind=runner_row.get("kind"), passed=runner_row.get("passed"),
                     branch=branch, note=runner_row.get("note"))
        if runner_row.get("case") == "*":  # rules rev25 CD-11: common id + " [case *]"
            entry["case_star"] = True
        reason = _runner_reason(branch, runner_row)
        if reason:
            entry["reason"] = reason
        items.append(entry)
    return items


def _runner_reason(branch: str, runner_row: dict[str, Any]) -> str | None:
    """Rules rev24 CD-7 reason of a held or runner-unjudged runner row (None otherwise)."""
    detail = runner_row.get("note") or f"kind {runner_row.get('kind')!r}"
    if branch == "hold":
        return f"{RUNNER_HOLD}(hold): {detail}"
    if branch in UNJUDGED_BRANCHES:
        return f"{RUNNER_UNJUDGED}: {detail}"
    return None


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


def recomputed_verdict(judge_key: str, runner_name: str, judged_items: dict[str, Any]
                       ) -> tuple[str, Any, str | None]:
    """(verdict, value, reason when not judgeable) of a re-computed item standing in for a
    runner item (rules rev24 CD-2 table, CD-3 for the item 4 rows)."""
    block = judged_items.get(judge_key)
    if not isinstance(block, dict):
        return NOT_JUDGEABLE, None, f"{INPUT_MISSING}: chrono_rows_judge {judge_key}"
    if judge_key == "C1_R40":
        if block.get("status") != "judged":
            reason = (f"{RUNNER_HOLD}: R40-2 hold not resolved" if block.get("hold")
                      else f"{INPUT_MISSING}: {block.get('reason') or 'C1_R40 not judged'}")
            return NOT_JUDGEABLE, block.get("raw_min_N"), reason
        return (PASS if block.get("verdict") == "pass" else FAIL), block.get("raw_min_N"), None
    if block.get("status") != "judged":
        return NOT_JUDGEABLE, None, str(block.get("reason") or f"{judge_key} not judged")
    if runner_name == SATURATION_ITEM:
        count = block.get("saturated_samples")
        return (PASS if count == 0 else FAIL), count, None
    if runner_name in (OUTSIDE_W_ITEM, INSIDE_W_ITEM):
        part = block["outside_extension" if runner_name == OUTSIDE_W_ITEM else "inside"]
        return (PASS if part.get("within") else FAIL), part.get("max_bar"), None
    value = block.get("max_moving_bar")
    if value is None:  # no moving sample: nothing exceeds the limit
        return PASS, None, None
    return (PASS if rows_judge.le(float(value), MOVING_PRESSURE_MAX_BAR) else FAIL), value, None


def is_event_row(judged_items: dict[str, Any]) -> bool:
    """Rules rev24 CD-3 event row (floor event or fast settlement) as the row judge decided it."""
    block = judged_items.get("moving_pressure_D-32")
    return isinstance(block, dict) and block.get("row_kind") is not None


def _override_applies(rows: str, event_row: bool) -> bool:
    if rows == ROWS_EVENT:
        return event_row
    if rows == ROWS_EVENT_FREE:
        return not event_row
    return True


def apply_rigid_overrides(items: list[dict[str, Any]], judged_items: dict[str, Any]
                          ) -> list[dict[str, Any]]:
    """Replace the runner items of :data:`RIGID_OVERRIDES` (whole-name match, on the rows of the
    table line); returns the before / after log."""
    log = []
    event_row = is_event_row(judged_items)
    for runner_item in items:
        for name, judge_key, rule, rows in RIGID_OVERRIDES:
            if runner_item["item"] != name or not _override_applies(rows, event_row):
                continue
            verdict, value, reason = recomputed_verdict(judge_key, name, judged_items)
            extra = {} if reason is None else {"reason_not_judgeable": reason}
            _override(runner_item, verdict, value, rule, log, **extra)
            break
    return log


def _override(runner_item: dict[str, Any], verdict: str, value: Any, rule: str,
              log: list[dict[str, Any]], **extra: Any) -> None:
    """Replace one runner item (a runner record row stays a record, its value logged); the
    replaced item carries the reason of the change (rules rev24 CD-7)."""
    before = {"verdict": runner_item["verdict"], "value": runner_item.get("value")}
    entry = {"item": runner_item["item"], "rule": rule, "runner": before,
             "recomputed": {"verdict": verdict, "value": value}, **extra}
    if runner_item["verdict"] is None:
        log.append({**entry, "applied": False, "reason": "runner record row"})
        return
    change = f"CD-2 table: re-computed value replaces the runner's ({rule})"
    runner_item.update(verdict=verdict, value=value, source=f"recomputed {rule}",
                       override_reason=change)
    if verdict == NOT_JUDGEABLE:
        runner_item["reason"] = str(extra.get("reason_not_judgeable") or change)
    log.append({**entry, "applied": True, "override_reason": change})


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
            if runner_item["item"] != name:  # rules rev24 CD-2: whole-name match
                continue
            value, detail = d8_value(name, pads, t_lift)
            if value is None:
                verdict = NOT_JUDGEABLE
                detail["reason_not_judgeable"] = f"{INPUT_MISSING}: {detail.get('reason')}"
            elif name.startswith("D8 min"):
                limit = runner_item.get("limit")
                limit = float(limit) if isinstance(limit, (int, float)) else None
                verdict = NOT_JUDGEABLE if limit is None else (
                    PASS if rows_judge.ge(value, limit) else FAIL)
                if limit is None:
                    detail["reason_not_judgeable"] = f"{INPUT_MISSING}: runner item limit"
            else:
                verdict = PASS if value == 0 else FAIL
            _override(runner_item, verdict, value, f"rev19 R19-5 ({rule})", log,
                      t_lift_D29_s=t_lift, **detail)
            break
    return log


def t_lift_difference(doc: dict[str, Any], row: RowInput, judged_items: dict[str, Any],
                      record: dict[str, np.ndarray] | None, inner: str | None
                      ) -> dict[str, Any]:
    """Rev19 R19-5 with rev21 R21-2: |runner t_lift - D-29 t_lift| on the 10 Hz grid.

    Runner t_lift = ``verify_S8C`` ``s8_metrics.<inner>.liftoff_s`` (``inner`` = the inner name
    of the judged row ``dir``, rev23 R23-1; ``_times`` ``liftoff``, relative to
    ``settings.start_t_s``) + the row's ``t0_s`` (engine absolute time); the 1 ms
    t_lift,sus (basis ``1ms_sus``) is raised to the first 10 Hz ``record.npz`` ``t`` >= it - 1e-9
    s (picked from the array, no ``ceil``), a 10 Hz bracket (R15-3) t_b is used as it is. Not
    computable (an unknown basis included) or > 0.1 s + 1e-9 s = a stop.
    """
    judged = row.judged or {}
    metrics = {} if inner is None else (doc.get("s8_metrics") or {}).get(inner) or {}
    runner_rel = metrics.get("liftoff_s")
    t0 = judged.get("t0_s")
    d29 = judged_items.get("D8_t_lift_s_D-29_D-30")
    basis = judged_items.get("D8_t_lift_basis")
    is_bracket = isinstance(basis, dict) and basis.get("basis") == "bracket_10Hz"
    out: dict[str, Any] = {"runner_liftoff_rel_s": runner_rel, "t0_s": t0, "t_lift_D29_s": d29,
                           "basis": T_LIFT_1MS_BASIS if basis == T_LIFT_1MS_BASIS else (
                               "bracket_10Hz" if is_bracket else str(basis)),
                           "t_lift_sus_record_R21_1": judged_items.get("D8_t_lift_sus_R21_1")}
    if basis != T_LIFT_1MS_BASIS and not is_bracket:
        return {**out, "ok": False,
                "stop": f"t_lift difference not computable: D-29 basis {basis!r} (rev21 R21-2)"}
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
    name_map: dict[str, Any] | None = None
    """Rev23 R23-1 entry of the row (:func:`runner_name_entry`)."""
    reason: str | None = None
    """Rules rev24 CD-7 reason of a not-judgeable runner part (:func:`runner_part_reason`)."""


def row_inner_name(row: RowInput) -> str | None:
    """Rev23 R23-1: last path name of the judged row ``dir`` (None without a judged row or with
    an empty ``dir``)."""
    folder = (row.judged or {}).get("dir")
    return inner_name(str(folder)) if folder else None


def runner_name_entry(row: RowInput, path: Path | None, doc: dict[str, Any] | None,
                      inner: str | None) -> dict[str, Any]:
    """Rev23 R23-1 record entry and checks 1, 3, 4 of one row that reads a runner judge file.

    Check 2 (``dir`` unique in the bundle) and ``ok`` are set by :func:`runner_name_map`. A check
    that does not apply is None: all four without a judged row, 3 and 4 without the file.
    """
    folder = (row.judged or {}).get("dir")
    entry: dict[str, Any] = {
        "case": row.case, "dir": str(folder) if folder else None, "inner_name": inner,
        "name_differs": None if inner is None else row.case != inner,
        "runner_file": None if path is None else path.name, "runner_meta_batch_name": None,
        "runner_row_cases": None, "runner_rows_found": None, "s8_metrics_keys": None,
        "checks": dict.fromkeys(R23_1_CHECKS), "ok": None}
    if row.judged is None:
        return entry
    entry["checks"].update({"1_dir_set": inner is not None, "2_dir_unique": True})
    if doc is None:
        return entry
    batch = (doc.get("meta") or {}).get("batch")
    row_cases = [runner_row.get("case") for runner_row in doc.get("rows") or []
                 if runner_row.get("case") != "*"]
    metrics = doc.get("s8_metrics")
    metric_keys = sorted(str(key) for key in metrics) if isinstance(metrics, dict) else None
    entry.update(runner_meta_batch_name=None if batch is None else Path(str(batch)).name,
                 runner_row_cases=sorted({str(case) for case in row_cases}),
                 runner_rows_found=sum(1 for case in row_cases if case == inner),
                 s8_metrics_keys=metric_keys)
    entry["checks"].update({
        "3_runner_row_cases": all(case == inner for case in row_cases),
        "4_s8_metrics_keys": metric_keys is None or all(key == inner for key in metric_keys)})
    return entry


def runner_name_map(inputs: list[RowInput]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Rev23 R23-1 record ``runner_name_map_R23_1`` of a bundle and its S-11 stops.

    Check 2: no two entries share the full ``dir`` path (entries without a ``dir`` left out).
    Every false check is a stop of that row (case = judged row name).
    """
    entries = [row.runner_name_map for row in inputs if row.runner_name_map is not None]
    dir_counts = Counter(entry["dir"] for entry in entries if entry["dir"] is not None)
    stops: list[dict[str, str]] = []
    for entry in entries:
        checks = entry["checks"]
        if checks["2_dir_unique"] is not None:
            checks["2_dir_unique"] = entry["dir"] is None or dir_counts[entry["dir"]] == 1
        entry["ok"] = all(value for value in checks.values() if value is not None)
        stops += [{"case": entry["case"], "reason": f"S-11: check {name} false ({R23_1_RULE})"}
                  for name, value in checks.items() if value is False]
    block = {"rule": R23_1_RULE, "rows": entries,
             "name_differs_count": sum(1 for entry in entries if entry["name_differs"] is True),
             "ok": all(entry["ok"] for entry in entries)}
    return block, stops


def rigid_row(row: RowInput, bundle: str, runner_dir: Path | None) -> RigidResult:
    """An L2b / L1-R row: runner items (R19-4) found by the inner name of the judged row ``dir``
    (R23-1), re-computed items (D-31 / D-32 / D-39), the D8 items from the D-29 t_lift and the
    t_lift difference (R19-5, L2b rows)."""
    out = RigidResult()
    inner = row_inner_name(row)
    path = runner_judge_file(runner_dir, bundle, row)
    if path is None:
        row.missing.append(f"runner judge {RUNNER_FILE_SUFFIX[row.engine]}")
        out.name_map = runner_name_entry(row, None, None, inner)
        out.reason = runner_part_reason([], 0, row.missing)
        return out
    doc = read_json(path, "runner judge output")
    row.files[path.name] = rows_judge.sha256_file(path)
    _check_runner_batch(doc, row, path)
    out.name_map = runner_name_entry(row, path, doc, inner)
    out.items = runner_items(doc, inner)
    if inner is None or not any(runner_row.get("case") == inner
                                for runner_row in doc.get("rows") or []):
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
        if judged_items.get("D8_t_lift_basis") == T_LIFT_1MS_BASIS and t_lift is None:
            out.stops.append("no t_lift,sus: D8 / D-39 not judgeable (rev21 R21-1)")
        if out.t_lift_items:
            out.t_lift_check = t_lift_difference(doc, row, judged_items, record, inner)
            if out.t_lift_check.get("stop"):
                out.stops.append(out.t_lift_check["stop"])
        window_stop = event_window_stop(judged_items)
        if window_stop:
            out.stops.append(window_stop)
    out.grade = runner_part_grade(out.items, out.judged_true)
    if out.grade == NOT_JUDGEABLE:
        out.reason = runner_part_reason(out.items, out.judged_true, row.missing)
    return out


def event_window_stop(judged_items: dict[str, Any]) -> str | None:
    """Rules rev24 CD-3: the row judge's W end against the original judge's ``pressure_end_s``;
    > 0.1 s or a verdict changed by the difference stops the bundle before its grade."""
    block = judged_items.get("moving_pressure_D-32")
    check = block.get("runner_window_CD_3") if isinstance(block, dict) else None
    if not isinstance(check, dict) or not check.get("stop"):
        return None
    return (f"CD-3: event window end differs from the original judge's pressure_end_s by "
            f"{check.get('difference_s')} s (changed verdicts {check.get('verdicts_changed')})")


def runner_part_reason(items: list[dict[str, Any]], judged_true: int,
                       missing: list[str]) -> str:
    """Rules rev24 CD-7 reason of a not-judgeable runner part: missing runner input, the reasons
    of its not-judgeable items, or no judged item passed (empty pass)."""
    if missing:
        return f"{INPUT_MISSING}: {', '.join(missing)}"
    reasons = [entry.get("reason") or entry["item"] for entry in items
               if entry["verdict"] == NOT_JUDGEABLE]
    if reasons:
        return "; ".join(reasons)
    if judged_true == 0:
        return "no judged-kind runner item with passed True (empty pass, rev19 R19-4)"
    return ""


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
def has_first_ready(judged_items: dict[str, Any]) -> bool | None:
    """Whether the run reached a first READY (``chrono_rows_judge`` D-27 / D-28 block); None when
    the block is missing."""
    ready = judged_items.get("ready_D-27_D-28")
    if not isinstance(ready, dict):
        return None
    return ready.get("t_ready_rel_s") is not None


def missing_reason(what: str) -> str:
    return f"{INPUT_MISSING}: {what}"


def checked_item(name: str, check: Any, source: str, what: str, **detail: Any) -> dict[str, Any]:
    """An item judged from a true / false ``check``; a missing one is not judgeable with the
    rules rev24 CD-7 reason ``원 입력 결측``."""
    verdict = bool_verdict(check)
    if verdict == NOT_JUDGEABLE:
        detail["reason"] = missing_reason(what)
    return item(name, verdict, source, **detail)


def word_item(name: str, word: Any, source: str, what: str, **detail: Any) -> dict[str, Any]:
    """An item judged from a pass / flag / fail word (anything else: not judgeable, CD-7)."""
    verdict = _verdict_word(word)
    if verdict == NOT_JUDGEABLE:
        detail["reason"] = missing_reason(what)
    return item(name, verdict, source, **detail)


def not_applicable_item(name: str, source: str, why: str) -> dict[str, Any]:
    """A ``해당 없음(<why>)`` item (rules rev24 CD-5 / CD-9): no grade, the text as its value."""
    text = f"해당 없음({why})"
    return item(name, None, source, status=NOT_APPLICABLE_STATUS, value=text, reason=text)


def p3_items(p3b: dict[str, Any], judged_items: dict[str, Any], *,
             rigid_base: bool = False, args: dict[str, Any] | None = None,
             p36_graded: bool = False) -> list[dict[str, Any]]:
    """P3-1 .. P3-9 and FAULT0 of an SCM row; the D items of ``chrono_rows_judge`` stand in for
    P3-1 (D-36), P3-2 (D-37 / D-38), P3-3 (t_D, R6-B4) and P3-8 (D-34 / D-35).

    Rules rev25 CD-5: without a first READY, P3-1 judges only the recontact condition, P3-4 and
    P3-5 are not applicable, P3-6 fails where it is graded (``p36_graded``: C-5 SCM rows) and is
    not applicable where it is a record. CD-9 / CD-8 7: P3-5 of a ``rigid_base`` row is not
    applicable. CD-4: P3-6 against the spec 421.1 limit of the run ``args`` (:func:`p36_item`).
    Which items grade the row is decided by the caller (:func:`_scm_items`).
    """
    checks = p3b.get("checks") or {}
    recontact = judged_items.get("P3-1_recontact_D-36") or {}
    p32 = judged_items.get("P3-2_D-37_D-38") or {}
    p33 = judged_items.get("P3-3_after_t_D") or {}
    p38 = judged_items.get("P3-8_D-34_D-35") or {}
    no_ready = has_first_ready(judged_items) is False
    return [
        _p31_item(checks, recontact, no_ready),
        _p32_item(checks, p32),
        checked_item("P3-3", p33.get("within"), "recomputed R6-B4 t_D",
                     "chrono_rows_judge P3-3_after_t_D within",
                     value=p33.get("F_min_after_departure_N")),
        not_applicable_item("P3-4", "p3b checks", READY_MISSING) if no_ready else word_item(
            "P3-4", checks.get("P3-4_verdict"), "p3b checks", "p3b checks P3-4_verdict"),
        _p35_item(checks, no_ready, rigid_base),
        p36_item(p3b, args, no_ready=no_ready, graded=p36_graded),
        checked_item("P3-7", checks.get("P3-7_within"), "p3b checks", "p3b checks P3-7_within"),
        word_item("P3-8", p38.get("verdict"), "recomputed D-34 / D-35",
                  "chrono_rows_judge P3-8_D-34_D-35 verdict", flags=p38.get("flags")),
        _p39_item(checks),
        _fault_item(p38),
    ]


P36_GRADED_BUNDLE = "C-5"
"""Rules rev25 CD-4: P3-6 is graded on C-5 SCM rows only (a record elsewhere)."""
P3_RECORDED = ("P3-9",)
"""Rules rev25 CD-11: P3-9 (RT deferral) is a record on every row."""
P36_SLOPE_LIMIT_S, P36_SOFT_PAD_B_LIMIT_S, P36_FLAT_LIMIT_S = 120.0, 100.0, 90.0
P36_SOFT_SOILS = ("J1", "J2", "S1")
P36_PAD_B = "dwg_rear250"


def p36_limit(args: dict[str, Any] | None) -> dict[str, Any]:
    """Rules rev25 CD-4 P3-6 limit (spec 421.1, first matching row): floor slope (``floor_roll``
    or ``floor_pitch`` not 0) 120 s; flat, pad B and both rear pads (RL, RR; ``soil_patch``
    ``LEG:SET`` when it covers the leg, else ``soil``) on J1 / J2 / S1 100 s; other flat 90 s."""
    run = args or {}
    roll, pitch = float(run.get("floor_roll") or 0.0), float(run.get("floor_pitch") or 0.0)
    patch_leg, _, patch_set = str(run.get("soil_patch") or "").partition(":")
    rear = [patch_set if patch_leg == leg and patch_set else run.get("soil")
            for leg in ("RL", "RR")]
    if roll != 0.0 or pitch != 0.0:
        return {"limit_s": P36_SLOPE_LIMIT_S, "row": "slope", "rear_pad_soils": rear}
    if run.get("pad_variant") == P36_PAD_B and all(soil in P36_SOFT_SOILS for soil in rear):
        return {"limit_s": P36_SOFT_PAD_B_LIMIT_S, "row": "flat, pad B, rear pads J1 / J2 / S1",
                "rear_pad_soils": rear}
    return {"limit_s": P36_FLAT_LIMIT_S, "row": "flat, other", "rear_pad_soils": rear}


def p36_item(p3b: dict[str, Any], args: dict[str, Any] | None, *, no_ready: bool,
             graded: bool) -> dict[str, Any]:
    """Rules rev25 CD-4 P3-6: first READY after the closed-loop start <= the spec 421.1 limit
    (+ 1e-9 s); the limit is checked against the runner's P3b ``P3-6_ready.limit_s``
    (``limit_matches_runner``, False stops the bundle). Without a first READY (CD-5): fail where
    P3-6 is graded, ``해당 없음(READY 없음)`` where it is a record."""
    source = "rules rev25 CD-4 P3-6 (spec 421.1 limit, p3b P3-6_ready)"
    if no_ready:
        if graded:
            return item("P3-6", FAIL, source, reason=f"{READY_MISSING}: READY 도달 항목 = 미달")
        return not_applicable_item("P3-6", source, READY_MISSING)
    block = p3b.get("P3-6_ready")
    if not isinstance(block, dict):  # no P3b block: the runner's check, limit not compared
        return checked_item("P3-6", (p3b.get("checks") or {}).get("P3-6_within"), "p3b checks",
                            "p3b checks P3-6_within", limit_matches_runner=None)
    limit = p36_limit(args)
    runner_limit = block.get("limit_s")
    matches = runner_limit is not None and abs(float(runner_limit) - limit["limit_s"]) <= \
        rows_judge.CMP_EPS
    t_ready = block.get("t_ready_after_loop_start_s")
    within = None if t_ready is None else rows_judge.le(float(t_ready), limit["limit_s"])
    return checked_item("P3-6", within, source, "p3b P3-6_ready.t_ready_after_loop_start_s",
                        value=t_ready, limit_s=limit["limit_s"], limit_row=limit["row"],
                        runner_limit_s=runner_limit, limit_matches_runner=matches)


def _p35_item(checks: dict[str, Any], no_ready: bool, rigid_base: bool) -> dict[str, Any]:
    if rigid_base:
        return not_applicable_item("P3-5", "rules rev24 CD-9", "rigid_base")
    if no_ready:
        return not_applicable_item("P3-5", "p3b checks", READY_MISSING)
    return checked_item("P3-5", checks.get("P3-5_within"), "p3b checks", "p3b checks P3-5_within")


def _verdict_word(word: Any) -> str:
    return word if word in (PASS, FLAG, FAIL) else NOT_JUDGEABLE


def _p31_item(checks: dict[str, Any], recontact: dict[str, Any],
              no_ready: bool = False) -> dict[str, Any]:
    """P3-1 = crawler zero READY .. READY + 10 s and no recontact after the first departure;
    without a READY (rules rev24 CD-5) the first condition is not applicable."""
    zero = checks.get("P3-1_crawler_zero_after_ready")
    passed = recontact.get("pass")
    detail: dict[str, Any] = {}
    if no_ready:
        zero = f"해당 없음({READY_MISSING})"
        if passed is None:
            verdict = NOT_JUDGEABLE
            detail["reason"] = missing_reason("chrono_rows_judge P3-1_recontact_D-36")
        else:
            verdict = (FLAG if recontact.get("flags") else PASS) if passed else FAIL
        detail["condition_note"] = (f"{READY_MISSING}: READY .. READY + 10 s crawler condition "
                                    "not applicable, recontact condition judged (CD-5)")
    elif zero is None or passed is None:
        verdict = NOT_JUDGEABLE
        detail["reason"] = missing_reason("p3b P3-1_crawler_zero_after_ready / D-36 recontact")
    elif not zero or not passed:
        verdict = FAIL
    else:
        verdict = FLAG if recontact.get("flags") else PASS
    return item("P3-1", verdict, "p3b crawler zero + recomputed D-36",
                crawler_zero_after_ready=zero, flags=recontact.get("flags"), **detail)


def _p32_item(checks: dict[str, Any], p32: dict[str, Any]) -> dict[str, Any]:
    within = p32.get("within")
    late_flag = bool(checks.get("P3-2_late_loc_reapproach") or checks.get(
        "P3-2_late_loc_revoked"))
    detail: dict[str, Any] = {}
    if within is True:
        verdict = PASS
    elif within is False:
        verdict = FLAG if late_flag else FAIL
    else:
        verdict = NOT_JUDGEABLE
        detail["reason"] = missing_reason("chrono_rows_judge P3-2_D-37_D-38 within")
    return item("P3-2", verdict, "recomputed D-37 / D-38 + p3b late-LOC FLAG",
                late_loc_flag=late_flag, **detail)


def _p39_item(checks: dict[str, Any]) -> dict[str, Any]:
    flags = checks.get("P3-9_flags")
    if not isinstance(flags, int):
        return item("P3-9", NOT_JUDGEABLE, "p3b checks", value=flags,
                    reason=missing_reason("p3b checks P3-9_flags"))
    return item("P3-9", FLAG if flags > 0 else PASS, "p3b checks (FLAG record)", value=flags)


def _fault_item(p38: dict[str, Any]) -> dict[str, Any]:
    fault = p38.get("fault")
    source = "recomputed (chrono_rows_judge has_fault)"
    if fault is None:
        return item("FAULT0", NOT_JUDGEABLE, source,
                    reason=missing_reason("chrono_rows_judge P3-8_D-34_D-35 fault"))
    return item("FAULT0", FAIL if fault else PASS, source)


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
    items.append(checked_item("stroke_le_684.8mm", stroke_ok, "soil_event.judgement",
                              "soil_event.judgement.stroke_max_run_mm", value=stroke))
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


def check_t45_criteria(doc: dict[str, Any]) -> None:
    """The ``--t45`` output must be the revision 7 replay (v5 criteria revision 7 94)."""
    if doc.get("criteria") != T45_CRITERIA:
        raise InputError(f"--t45: criteria {doc.get('criteria')!r}, revision 7 output needed "
                         "(v5 criteria revision 7 94)")


def t45_folder_list(judge_doc: dict[str, Any] | None, *, ignore_case: bool = False
                    ) -> tuple[list[str], list[str], list[str]]:
    """Rev22 R22-1: (folders, cases, empty-dir cases) of the t45 input list rebuilt from a
    ``judge_C5.json``: its ``rows`` in order, the rows whose ``case`` is in :data:`T45_CASES`
    (exact match; ``ignore_case`` mimics PowerShell ``-in``), their ``dir``."""
    wanted = {case.casefold() for case in T45_CASES} if ignore_case else set(T45_CASES)
    folders, cases, empty = [], [], []
    for row in (judge_doc or {}).get("rows") or []:
        case = str(row.get("case"))
        if (case.casefold() if ignore_case else case) not in wanted:
            continue
        folder = row.get("dir")
        if not folder:
            empty.append(case)
        folders.append("" if not folder else str(folder))
        cases.append(case)
    return folders, cases, empty


def folder_list_sha256(folders: list[str]) -> str:
    """sha256 of a folder list written as UTF-8 text, one path per line, each ending in ``\\n``."""
    return hashlib.sha256("".join(f"{folder}\n" for folder in folders).encode("utf-8")).hexdigest()


def read_folder_list(path: Path) -> list[str]:
    """A t45 input folder list file: a JSON list of paths, or one path per line."""
    text = path.read_text(encoding="utf-8-sig")
    try:
        value = json.loads(text)
    except ValueError:
        return [line.strip() for line in text.splitlines() if line.strip()]
    if not isinstance(value, list):
        raise InputError(f"--t45-folders {path}: a JSON list of paths needed")
    return [str(folder) for folder in value]


def script_t45_cases(path: Path) -> list[str]:
    """The ``$T45Cases = @(...)`` names of a run_path1 PowerShell script (single-quoted)."""
    text = path.read_text(encoding="utf-8-sig")
    match = T45_SCRIPT_RE.search(text)
    if match is None:
        raise InputError(f"--t45-cases-script {path}: no $T45Cases = @(...) list")
    return re.findall(r"'([^']*)'", match.group(1))


def inner_name(folder: str) -> str:
    """Last name of a path written with \\ or / (the run folder's ``--only`` case)."""
    return re.split(r"[\\/]", folder.rstrip("\\/"))[-1]


def _pairing_sources(args: argparse.Namespace, judge_doc: dict[str, Any] | None,
                     folders: list[str]) -> tuple[dict[str, Any], list[str]]:
    """Rev22 R22-1 evidence chain: script case list, case-insensitive list, reference judge
    (R3c ``judge_C5.json``) list and the optional list file; returns (record, S-11 reasons)."""
    reasons: list[str] = []
    record: dict[str, Any] = {}
    if args.t45_cases_script:
        script_cases = script_t45_cases(Path(args.t45_cases_script))
        record["script"] = {"path": args.t45_cases_script,
                            "sha256": rows_judge.sha256_file(Path(args.t45_cases_script)),
                            "cases": script_cases, "equal": script_cases == list(T45_CASES)}
        if not record["script"]["equal"]:
            reasons.append("run script $T45Cases differs from T45_CASES")
    else:
        reasons.append("no --t45-cases-script: $T45Cases not compared with T45_CASES")
    folded, _, _ = t45_folder_list(judge_doc, ignore_case=True)
    record["case_insensitive_list_equal"] = folded == folders
    if folded != folders:
        reasons.append("case-insensitive selection gives another folder list")
    if args.t45_reference_judge:
        ref_path = Path(args.t45_reference_judge)
        ref_sha = rows_judge.sha256_file(ref_path)
        ref_folders, _, _ = t45_folder_list(read_json(ref_path, "--t45-reference-judge"))
        record["reference_judge"] = {"path": str(ref_path), "sha256": ref_sha,
                                     "sha256_expected": args.t45_reference_sha256,
                                     "sha256_equal": ref_sha == args.t45_reference_sha256,
                                     "list_equal": ref_folders == folders,
                                     "list_sha256": folder_list_sha256(ref_folders)}
        if ref_sha != args.t45_reference_sha256:
            reasons.append("reference judge_C5.json sha256 is not the R3c one")
        if ref_folders != folders:
            reasons.append("folder list of the reference judge_C5.json differs (source fix)")
    else:
        reasons.append("no --t45-reference-judge: the source list is not fixed")
    if args.t45_folders:
        listed = read_folder_list(Path(args.t45_folders))
        record["list_file"] = {"path": args.t45_folders,
                               "sha256": rows_judge.sha256_file(Path(args.t45_folders)),
                               "equal": listed == folders}
        if listed != folders:
            reasons.append("--t45-folders list differs from the rebuilt list")
    return record, reasons


def _pairing_checks(t45_doc: dict[str, Any], judge_doc: dict[str, Any] | None,
                    folders: list[str], cases: list[str]) -> tuple[dict[str, Any], list[str],
                                                                   list[str]]:
    """Rev22 R22-1 checks 1 .. 4: (record, S-15 reasons, S-11 reasons)."""
    t45 = t45_doc.get("rows") or []
    dirs = {str(row.get("case")): row.get("dir") for row in (judge_doc or {}).get("rows") or []}
    count_ok = len(t45) == len(folders)
    pairs = [{"index": i, "case": case, "folder": folder,
              "t45_case": str(row.get("case")) if count_ok else None,
              "dir_equal": dirs.get(case) == folder,
              "inner_name_equal": count_ok and str(row.get("case")) == inner_name(folder)}
             for i, (case, folder, row) in enumerate(zip(cases, folders, t45 if count_ok
                                                         else [{}] * len(folders),
                                                         strict=True))]
    checks = {"1_row_count": {"t45_rows": len(t45), "folders": len(folders), "ok": count_ok},
              "2_dir_equal": all(p["dir_equal"] for p in pairs),
              "3_inner_name_equal": count_ok and all(p["inner_name_equal"] for p in pairs),
              "4_unique_folders": len(set(folders)) == len(folders),
              "4_unique_cases": len(set(cases)) == len(cases),
              "4_cases_equal_target": set(cases) == set(T45_CASES)}
    s15 = [] if count_ok else [f"t45 rows {len(t45)} != input folders {len(folders)}"]
    s11 = [name for name, ok in checks.items() if name != "1_row_count" and not ok]
    return {"checks": checks, "pairs": pairs}, s15, s11


def t45_pairing(t45_doc: dict[str, Any], judge_doc: dict[str, Any] | None,
                args: argparse.Namespace) -> tuple[dict[str, dict[str, Any]], dict[str, Any],
                                                   list[dict[str, str]]]:
    """Rev22 R22-1: t45 rows paired with the judged rows by the t45 input folder order.

    i-th t45 row <-> i-th folder of the list rebuilt from ``judge_C5.json``
    (:func:`t45_folder_list`) <-> the judged row with that ``dir``. Returns (t45 row by judged
    case, the pairing record, stops); any stop leaves the pairing empty (the T4 / T5 items are
    then not judgeable).
    """
    check_t45_criteria(t45_doc)
    folders, cases, empty = t45_folder_list(judge_doc)
    record: dict[str, Any] = {"rule": R22_1_RULE, "target_cases": len(T45_CASES),
                              "folders": folders, "folders_sha256": folder_list_sha256(folders),
                              "empty_dir_cases": empty}
    sources, s11 = _pairing_sources(args, judge_doc, folders)
    checked, s15, failed = _pairing_checks(t45_doc, judge_doc, folders, cases)
    record.update(sources=sources, **checked)
    if empty:
        s11.append(f"judged rows without dir: {empty}")
    s11 += [f"check {name} false" for name in failed]
    stops = [{"case": "*", "reason": f"S-15: {text} (rev22 R22-1)"} for text in s15]
    stops += [{"case": "*", "reason": f"S-11: {text} (rev22 R22-1)"} for text in s11]
    record["ok"] = not stops
    if stops:
        return {}, record, stops
    by_case = {pair["case"]: row for pair, row in zip(record["pairs"], t45_doc["rows"],
                                                      strict=True)}
    return by_case, record, stops


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
        row.runner_name_map = rigid.name_map
        items = [item("runner", rigid.grade, "runner judge (rev19 R19-4)",
                      judged_true_items=rigid.judged_true,
                      stop="; ".join(rigid.stops) or None)]
        if rigid.reason:
            items[0]["reason"] = rigid.reason
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
    for entry in [*items, *record_items, *out["runner_items"]]:
        add_derived_reason(entry)
    if grade == NOT_JUDGEABLE:
        out["grade_reason"] = row_grade_reason(row.missing, items)
    return out


NO_GRADED_ITEM = "no judged item"


def needs_reason(entry: dict[str, Any]) -> bool:
    """Rules rev24 CD-7: a not-judgeable item (graded or recorded), a not-applicable item and a
    runner-unjudged or held runner row carry a reason."""
    return (NOT_JUDGEABLE in (entry.get("verdict"), entry.get("verdict_recorded"))
            or entry.get("status") == NOT_APPLICABLE_STATUS
            or entry.get("branch") in (*UNJUDGED_BRANCHES, "hold"))


def derived_reason(entry: dict[str, Any]) -> str | None:
    """The reason an item's own record states (missing inputs, its stop, a missing source, a
    status word); None when the record states none."""
    missing = entry.get("missing_inputs")
    if missing:
        return missing_reason(", ".join(map(str, missing)))
    if entry.get("stop"):
        return str(entry["stop"])
    source = str(entry.get("source", ""))
    if source.endswith(" missing"):
        return missing_reason(source.removesuffix(" missing"))
    if entry.get("item") in SOIL_EVENT_GROUPS and not entry.get("gates"):
        return missing_reason(f"soil_event.judgement.gates {entry['item']}_*")
    if entry.get("status") is not None:
        return f"{entry['item']} status {entry['status']}"
    return None


def add_derived_reason(entry: dict[str, Any]) -> None:
    if needs_reason(entry) and not entry.get("reason"):
        reason = derived_reason(entry)
        if reason:
            entry["reason"] = reason


def row_grade_reason(missing: list[str], items: list[dict[str, Any]]) -> str:
    """Rules rev24 CD-7 reason of a not-judgeable row."""
    if missing == [NO_GRADED_ITEM]:
        return "no graded item besides not-applicable and record items (original 9.3, CD-4)"
    if missing:
        return missing_reason(", ".join(missing))
    return "; ".join(str(entry.get("reason") or entry["item"]) for entry in items
                     if entry["verdict"] == NOT_JUDGEABLE)


def reason_gaps(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Rules rev24 CD-7: the items and rows that need a reason and have none (a stop)."""
    gaps = []
    for row in rows:
        if row.get("grade") == NOT_JUDGEABLE and not row.get("grade_reason"):
            gaps.append({"case": row["case"], "item": "(row grade)"})
        for entry in [*row.get("items", []), *row.get("record_items", []),
                      *row.get("runner_items", [])]:
            if needs_reason(entry) and not entry.get("reason"):
                gaps.append({"case": row["case"], "item": str(entry.get("item"))})
        for entry in row.get("runner_items", []):
            replaced = str(entry.get("source", "")).startswith("recomputed")
            if replaced and not entry.get("override_reason"):
                gaps.append({"case": row["case"], "item": f"{entry.get('item')} (change)"})
    return gaps


# =============================================================================== CD-11 item list
METHOD_RUNNER, METHOD_RECOMPUTED = "원 판정기 실행", "재계산"
CLASS_GRADED, CLASS_GATE, CLASS_RECORD = "등급 항목", "관문", "기록"
RECOMPUTED_SOURCES = ("recomputed", "rev19", "chrono_rows_judge", "chrono_t45_replay",
                      "rules rev24", "rules rev25")
"""Sources of the items this path re-computes (everything else is the original judge's result)."""
ITEM_INTERVALS = {
    C1_D8_ITEM: "after the D-29 t_lift (a), outside REANCHOR, before a numeric event_t_s (1 ms)",
    D8_OVERRIDE_ITEMS[0]: "after the D-29 t_lift (a), window end of the runner item (1 ms)",
    D8_OVERRIDE_ITEMS[1]: "after the D-29 t_lift (a) to the record end (1 ms)",
    MOVING_ITEM: "10 Hz rows with |u_applied| > 1e-9 m/s (whole run)",
    OUTSIDE_W_ITEM: "10 Hz extension rows outside W",
    INSIDE_W_ITEM: "10 Hz rows inside W, any state",
}
CD2_TABLE_LINES = {
    C1_D8_ITEM: 1, D8_OVERRIDE_ITEMS[0]: 2, D8_OVERRIDE_ITEMS[1]: 3, MOVING_ITEM: 4,
    OUTSIDE_W_ITEM: 5, INSIDE_W_ITEM: 6, SATURATION_ITEM: 7,
    ("C-S8-72 U58: head F/A_p in the window <= 350 bar, outside extension samples <= 180 bar "
     "(slow event: whole-run any-state peak <= 350)"): 8,
    "R/D8 min force >= F_min + 5 kN": 9, "R/D8 no pad lift-off": 9,
    "D8 attitude last 5 s + mount <= 0.2 deg": 10, "2 attitude +-0.2 (+mount)": 10,
}
"""Rules rev25 CD-11 clause ids of the CD-2 table lines (whole names; line 11 is the t_lift
prefix line, line 12 every other runner item, ``[case *]`` items included)."""
CD2_PREFIX_LINE, CD2_OTHER_LINE = 11, 12
CD2_PREFIX_ITEMS = ("3 F_min (1 ms)", "3 F_min before the event", "5a rocking amplitude",
                    "F2 lower-bound soundness F_hat_cal - F_band - F <= sensor share "
                    "(after lift-off)")
CASE_STAR_SUFFIX = " [case *]"
G6_GATE_IDS = (("G6-1_crawler", "P3-1"), ("G6-2_loc", "P3-2"), ("G6-3_Fmin", "P3-3"),
               ("G6-4_att", "P3-4"), ("G6-5_rut_stroke", "P3-5"),
               ("G6-6_fault_ready", "G6-6"), ("G6-7_preloc", "P3-8"),
               ("READY_le_120s", "READY_le_120s"))
"""Rules rev25 CD-11 G6 table: the ``chrono_rows_judge`` G6 gate -> its common item id."""
SGS_CONDITION_IDS = ("427.9-1", "427.9-2", "427.9-3", "427.9-4", "427.9-5")
OUTSIDE_TOOL_GATES = (("identity", "original 4.2 record-check (resume4368_judge.py view stage)"),
                      ("K1_class", "original 7.2 k1-class (resume4368_judge.py view stage)"))
"""Gates path 1 checks in the run script's view stage, not in this tool (listed for CD-11)."""


def _interval(entry: dict[str, Any], method: str, event_row: bool) -> str:
    name = entry["item"]
    if name == SATURATION_ITEM and method == METHOD_RECOMPUTED:
        return ("10 Hz extension rows outside W" if event_row
                else "10 Hz extension rows (whole run)")
    if name in ITEM_INTERVALS and method == METHOD_RECOMPUTED:
        return ITEM_INTERVALS[name]
    if method == METHOD_RUNNER:
        return "original judge interval"
    return f"re-computed definition ({entry.get('source')})"


def cd2_clause(name: str, case_star: bool) -> str:
    """``CD-2 표 n줄`` of a runner item (whole name, the prefix line, else line 12)."""
    if case_star:
        return f"CD-2 표 {CD2_OTHER_LINE}줄"
    if name in CD2_TABLE_LINES:
        return f"CD-2 표 {CD2_TABLE_LINES[name]}줄"
    if name.startswith(CD2_PREFIX_ITEMS):
        return f"CD-2 표 {CD2_PREFIX_LINE}줄"
    return f"CD-2 표 {CD2_OTHER_LINE}줄"


def list_entry(entry: dict[str, Any], event_row: bool, *, common_id: str | None = None,
               cls: str = CLASS_GRADED, clause: str | None = None) -> dict[str, Any]:
    """One CD-11 item row (common id, class, item, clause id, description, method, interval,
    verdict, reason)."""
    source = str(entry.get("source", ""))
    method = METHOD_RECOMPUTED if source.startswith(RECOMPUTED_SOURCES) else METHOD_RUNNER
    name = entry["item"]
    shown = entry["verdict"]
    if cls == CLASS_RECORD:
        shown = entry.get("verdict_recorded", entry.get("value"))
    return {"common_id": common_id or name, "class": cls, "item": name,
            "clause_id": clause or ("CD-11 기록" if cls == CLASS_RECORD else name),
            "description": source, "method": method,
            "interval": _interval(entry, method, event_row), "verdict": shown,
            "reason": entry.get("reason") or entry.get("override_reason") or ""}


def _runner_entries(row: dict[str, Any], event_row: bool) -> list[dict[str, Any]]:
    """Runner items: graded (a verdict), records (record kinds, runner-unjudged rows)."""
    entries = []
    for entry in row.get("runner_items", []):
        star = bool(entry.get("case_star"))
        common = entry["item"] + (CASE_STAR_SUFFIX if star else "")
        if entry["verdict"] is None:
            entries.append(list_entry(entry, event_row, common_id=common, cls=CLASS_RECORD))
        else:
            entries.append(list_entry(entry, event_row, common_id=common,
                                      clause=cd2_clause(entry["item"], star)))
    return entries


def _t45_entries(entry: dict[str, Any], event_row: bool) -> list[dict[str, Any]]:
    """T4_T5 as the two common items T4 and T5, and the T4-0 gate."""
    t4_0 = FAIL if str(entry.get("stop") or "").startswith("T4-0") else (
        None if entry.get("source") == "chrono_t45_replay row missing" else PASS)
    gate = list_entry({**entry, "verdict": t4_0}, event_row, common_id="T4-0", cls=CLASS_GATE,
                      clause="CD-11 관문")
    if entry["verdict"] == NOT_JUDGEABLE:
        return [*(list_entry(entry, event_row, common_id=name, clause="CD-6")
                  for name in ("T4", "T5")), gate]
    return [*(list_entry({**entry, "verdict": PASS if entry.get(f"{name}_over_0p6kN") == 0
                          else FAIL}, event_row, common_id=name, clause="CD-6")
              for name in ("T4", "T5")), gate]


def _g6_entries(entry: dict[str, Any], event_row: bool) -> list[dict[str, Any]]:
    """The C-3 G6 item as the eight G6 table ids (CD-11 G6 대응표)."""
    gates = entry.get("gates") or {}
    reasons = entry.get("gate_reasons_CD_5") or {}
    out = []
    for gate, common in G6_GATE_IDS:
        value = gates.get(gate)
        verdict = None if value == rows_judge.NOT_APPLICABLE else _verdict_word(value)
        line = {**entry, "item": gate, "verdict": verdict, "reason": reasons.get(gate) or (
            missing_reason(f"chrono_rows_judge gate {gate}") if verdict == NOT_JUDGEABLE else "")}
        out.append(list_entry(line, event_row, common_id=common, clause="CD-11 G6 대응표"))
    return out


def _sgs_entries(entry: dict[str, Any], event_row: bool) -> list[dict[str, Any]]:
    """The 427.9 safe-stop item as its five conditions (명세 427.9 조건 n)."""
    conditions = list((entry.get("conditions") or {}).values())
    out = []
    for n, common in enumerate(SGS_CONDITION_IDS):
        value = conditions[n] if n < len(conditions) else None
        line = {**entry, "item": common, "verdict": bool_verdict(value)}
        out.append(list_entry(line, event_row, common_id=common,
                              clause=f"명세 427.9 조건 {n + 1}"))
    return out


ITEM_CLAUSES = {"J11": "CD-1 ①", "J-P3": "CD-1 ①", "FAULT0": "CD-4 FAULT0"}
PSC_STROKE_ITEM = "stroke_le_684.8mm"
PSC_STROKE_CLAUSE = "명세 426.3 E-5 (stroke limit 684.8 mm, record under E-5)"
"""Rules rev25 CD-11: the graded ids of a PS-c event row are E-1 .. E-7 only; the stroke limit is
part of E-5, so the separate stroke item is listed as a record under E-5 (row grading unchanged)."""


def _item_entries(row: dict[str, Any], event_row: bool, has_runner: bool
                  ) -> list[dict[str, Any]]:
    entries = []
    for entry in row["items"]:
        name = entry["item"]
        if name == "runner" and has_runner:
            continue
        if name == "T4_T5":
            entries += _t45_entries(entry, event_row)
        elif name == "G6":
            entries += _g6_entries(entry, event_row)
        elif name == "SGS_427_9":
            entries += _sgs_entries(entry, event_row)
        elif name.startswith("P3-"):
            entries.append(list_entry(entry, event_row, clause=f"CD-4 {name}"))
        elif name in SOIL_EVENT_GROUPS:
            entries.append(list_entry(entry, event_row, clause=f"명세 426.3 {name}"))
        elif name == PSC_STROKE_ITEM:
            entries.append(list_entry({**entry, "verdict_recorded": entry["verdict"]}, event_row,
                                      cls=CLASS_RECORD, clause=PSC_STROKE_CLAUSE))
        else:
            entries.append(list_entry(entry, event_row, clause=ITEM_CLAUSES.get(name, name)))
    return entries


def _gate_entries(row: dict[str, Any], row_input: RowInput, identity: Any
                  ) -> list[dict[str, Any]]:
    """Per-row gates (not graded; a failing gate stops the bundle where this tool checks it)."""
    judged_items = (row_input.judged or {}).get("items") or {}
    tag = ((judged_items.get("J-P3_R8-2") or {}).get("tag") or {})
    gates = [("R11-4", PASS if identity not in (None, rows_judge.COMMIT_STOP) else (
                 None if identity is None else FAIL), "commit identity (rev11 R11-4)"),
             ("R9-1", None if not tag else (PASS if tag.get("expect_check_ok") else FAIL),
              "expect_controller check (rev9 R9-1)")]
    gates += [(name, None, source) for name, source in OUTSIDE_TOOL_GATES]
    check = row.get("t_lift_check_R19_5")
    if check:
        gates.append(("t_lift 차 확인", PASS if check.get("ok") else FAIL, "rev19 R19-5"))
    window = (judged_items.get("moving_pressure_D-32") or {}).get("runner_window_CD_3")
    if isinstance(window, dict) and window.get("status") == "found":
        gates.append(("사건 창 끝 차 확인", FAIL if window.get("stop") else PASS, "CD-3"))
    return [{"common_id": name, "class": CLASS_GATE, "item": name, "clause_id": "CD-11 관문",
             "description": source, "method": METHOD_RECOMPUTED,
             "interval": "row", "verdict": verdict,
             "reason": "" if verdict is not None else "checked outside this tool / no input"}
            for name, verdict, source in gates]


def row_item_list(row: dict[str, Any], event_row: bool, row_input: RowInput | None = None,
                  identity: Any = None) -> list[dict[str, Any]]:
    """The CD-11 item rows of one bundle row: graded items (runner rows itemised; the runner part
    only when the row has no runner item), records and gates."""
    runner = _runner_entries(row, event_row)
    entries = [*runner, *_item_entries(row, event_row, has_runner=bool(runner))]
    entries += [list_entry(entry, event_row, cls=CLASS_RECORD)
                for entry in row.get("record_items", [])]
    if row_input is not None:
        if row_input.judged is not None and not any(e["item"] == "J-P3" for e in row["items"]):
            status = ((row_input.judged.get("items") or {}).get("J-P3_R8-2") or {}).get("status")
            if status == rows_judge.J_P3_NOT_APPLICABLE:
                entries.append({"common_id": "J-P3", "class": CLASS_GRADED, "item": "J-P3",
                                "clause_id": "CD-1 ①", "description": "recomputed rev8 R8-2",
                                "method": METHOD_RECOMPUTED, "interval": "row",
                                "verdict": None, "reason": "해당 없음(③ 끔)"})
        entries += _gate_entries(row, row_input, identity)
    return entries


def graded_count(entries: list[dict[str, Any]]) -> int:
    return sum(1 for e in entries if e["class"] == CLASS_GRADED and e["verdict"] is not None)


def item_list(inputs: list[RowInput], rows: list[dict[str, Any]],
              doc: dict[str, Any] | None = None) -> dict[str, Any]:
    """Rules rev25 CD-11 item list of a graded bundle: class (graded / gate / record), clause id,
    description per item. A row (record rows apart) without a graded item or a list whose row
    count is not the bundle's stops the bundle; bundle gates: the row count check."""
    identities = (doc or {}).get("commit_identity_R11_4") or {}
    listed = []
    for row_input, row in zip(inputs, rows, strict=True):
        event_row = is_event_row((row_input.judged or {}).get("items") or {})
        entries = row_item_list(row, event_row, row_input, identities.get(row["case"]))
        listed.append({"case": row["case"], "role": row["role"], "engine": row["engine"],
                       "event_row_CD_3": event_row, "graded_items": graded_count(entries),
                       "items": entries})
    empty = [entry["case"] for entry in listed
             if not entry["graded_items"] and entry["role"] != ROLE_RECORD]
    count = (doc or {}).get("row_count_S15") or {}
    return {"rule": CD11_RULE, "rows": listed, "list_rows": len(listed),
            "bundle_rows": len(rows), "empty_rows": empty,
            "bundle_gates": [{"common_id": "행 수 검사", "class": CLASS_GATE,
                              "clause_id": "CD-11 관문", "verdict": (
                                  None if not count else (PASS if count.get("ok") else FAIL))}],
            "ok": len(listed) == len(rows) and not empty}


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
    the five 427.9 conditions alone (rev19 R19-1), its P3 / G6 items recorded. Rules rev25
    CD-4 / CD-11: P3-9 is a record on every row, P3-6 is graded on C-5 SCM rows only."""
    p3b = (row.result or {}).get("p3b")
    if not isinstance(p3b, dict):
        row.missing.append("result.json p3b")
        return "", [], []
    items = p3_items(p3b, judged_items, args=(row.result or {}).get("args"),
                     p36_graded=bundle == P36_GRADED_BUNDLE)
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
    recorded = P3_RECORDED if bundle == P36_GRADED_BUNDLE else (*P3_RECORDED, "P3-6")
    return ("", [entry for entry in items if entry["item"] not in recorded],
            as_record([entry for entry in items if entry["item"] in recorded]))


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
    if judged.get("gate_reasons_CD_5"):
        g6_entry["gate_reasons_CD_5"] = judged["gate_reasons_CD_5"]
    if word == NOT_JUDGEABLE:
        open_gates = [name for name, value in (judged.get("gates") or {}).items()
                      if value == NOT_JUDGEABLE]
        g6_entry["reason"] = f"G6 gates not judgeable: {open_gates or g6}"
    extra = [entry for entry in p3 if entry["item"] in G6_EXTRA_P3]
    covered = [entry for entry in p3 if entry["item"] not in G6_EXTRA_P3]
    return "", [g6_entry, *extra], as_record(covered)


def _row_grade(row: RowInput, items: list[dict[str, Any]]) -> str:
    """Original 8.1 worst of the judged items; a missing input = not judgeable (9.3)."""
    if row.missing:
        return NOT_JUDGEABLE
    verdicts = [entry["verdict"] for entry in items if entry["verdict"] is not None]
    if not verdicts:
        row.missing.append(NO_GRADED_ITEM)
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
    out["record_values_CD_8"] = c8_record_values(row, oc5_doc, fmin_doc)
    row.missing += [f"CD-8 record value {name}" for name in out["record_values_CD_8"]["missing"]]
    out.update(complete=not row.missing, missing_inputs=row.missing, stops=stops,
               inputs_sha256=row.files)
    if row.missing:
        out["record_reason"] = missing_reason(", ".join(row.missing))
    return out


C8_OC5_VALUES = ("F_min_after_N", "F_min_transient_N", "t_min_after_s", "las_start_s",
                 "las_end_s", "las_end_reason", "k1_decisions", "R_c_operating",
                 "crawler_attitude_deg", "floor_roll_deg", "floor_pitch_deg")
"""Rules rev24 CD-8: the ``resume4368_judge.py oc5`` values a C-8 row must record (the after-
departure minimum force a / t per leg and its time, LAS-b start / end / reason, K1 decisions,
run R_c, crawler attitude, floor angles)."""
C8_FMIN_VALUES = ("F_below_F_min", "F_below_F_min_plus_2kN")
P3_RECORD_ITEMS = tuple(f"P3-{n}" for n in range(1, 10))
LIFTOFF_TRANSIENT_S = 8.0
"""Original 1 / rules rev25 CD-8 1: the t minimum is over [t_D, t_D + 8 s)."""
END_ATTITUDE_WINDOW_S = 5.0
MOUNT_ALLOWANCE_DEG = 0.02
"""Rules rev25 CD-8 8 ③: last 5 s of the 1 ms true deck roll / pitch + the 0.02 deg mount share."""


def _present(value: Any) -> bool:
    """A recorded value (an empty list counts, None does not)."""
    return value is not None


def crawler_stiffness_scale(result: dict[str, Any] | None) -> Any:
    """Crawler stiffness multiplier k of a run (``result.json``
    ``meta.rigid_base.crawler_kn_scale``)."""
    return (((result or {}).get("meta") or {}).get("rigid_base") or {}).get("crawler_kn_scale")


def p3_record_values(items: list[dict[str, Any]], names: tuple[str, ...]
                     ) -> tuple[dict[str, Any], list[str]]:
    """(value by P3 item, missing names): the verdict, or the ``해당 없음`` text; a not-judgeable
    item has no value."""
    by_name = {entry["item"]: entry for entry in items}
    values, missing = {}, []
    for name in names:
        entry = by_name.get(name)
        if entry is None or entry["verdict"] == NOT_JUDGEABLE:
            missing.append(name)
            values[name] = None
            continue
        values[name] = entry["value"] if entry.get("status") == NOT_APPLICABLE_STATUS else \
            entry["verdict"]
    return values, missing


def c8_record_values(row: RowInput, oc5_doc: dict[str, Any] | None,
                     fmin_doc: dict[str, Any] | None) -> dict[str, Any]:
    """Rules rev25 CD-8 record values of a C-8 row and the missing ones (a missing one makes the
    row ``기록 불완전``): the oc5 / fmin-time values, the per-leg a / t minima with their times,
    P3-1 .. P3-9 (P3-5 ``해당 없음(rigid_base)``), the SCM D8 values ① .. ④ and the G6 values."""
    oc5_values = (oc5_doc or {}).get("values") or {}
    values: dict[str, Any] = {name: oc5_values.get(name) for name in C8_OC5_VALUES}
    for name in C8_FMIN_VALUES:
        values[f"{name}.ms"] = ((fmin_doc or {}).get(name) or {}).get("ms")
    result = row.result or {}
    p3b = result.get("p3b") or {}
    values["P3-3_within"] = (p3b.get("checks") or {}).get("P3-3_within")
    values["crawler_stiffness_scale_k"] = crawler_stiffness_scale(result)
    judged_items = (row.judged or {}).get("items") or {}
    series = load_npz(row.batch / row.case / "step_series.npz")
    values.update(scm_force_minima(series, (p3b.get("departure") or {}).get("t_departure_s"),
                                   oc5_values))
    values.update(scm_d8_values(series, result.get("phases")))
    values.update(g6_record_values(judged_items))
    missing = [name for name, value in values.items() if not _present(value)]
    p3, p3_missing = p3_record_values(
        p3_items(p3b, judged_items, rigid_base=is_rigid_base(result), args=result.get("args")),
        P3_RECORD_ITEMS)
    values.update(p3)
    return {"values": values, "missing": missing + p3_missing,
            "crawler_normal_series": "step_series.npz scm_crawler_normal_N (the t_D series)",
            "rule": "rules rev25 CD-8 (original 7.4 record items)"}


def _leg_minima(t: np.ndarray, force: np.ndarray, mask: np.ndarray
                ) -> tuple[list[float] | None, list[float] | None]:
    """Per-leg minimum of ``force`` over ``mask`` and its sample time (None when empty)."""
    if not mask.any():
        return None, None
    masked = np.where(mask[:, None], force, np.inf)
    k = np.argmin(masked, axis=0)
    return masked.min(axis=0).tolist(), [float(t[i]) for i in k]


def scm_force_minima(series: dict[str, np.ndarray] | None, t_dep: Any,
                     oc5_values: dict[str, Any]) -> dict[str, Any]:
    """Rules rev25 CD-8 1: per-leg 1 ms true F_cyl minimum a (t_D .. record end) and t
    ([t_D, t_D + 8 s)) with their times (the runner P3b ``P3-3_leg_force`` definitions; the
    agreement with the oc5 values is recorded)."""
    out: dict[str, Any] = dict.fromkeys(("F_a_min_N_by_leg", "t_a_s_by_leg", "F_t_min_N_by_leg",
                                         "t_t_s_by_leg"))
    if series is None or t_dep is None or "t_s" not in series or "F_cyl_N" not in series:
        return out
    t = np.asarray(series["t_s"], float)
    force = np.asarray(series["F_cyl_N"], float)
    after = t >= float(t_dep) - rows_judge.CMP_EPS
    transient = after & (t < float(t_dep) + LIFTOFF_TRANSIENT_S)
    out["F_a_min_N_by_leg"], out["t_a_s_by_leg"] = _leg_minima(t, force, after)
    out["F_t_min_N_by_leg"], out["t_t_s_by_leg"] = _leg_minima(t, force, transient)
    out["a_t_match_oc5"] = {
        "F_min_after_N": _close_lists(out["F_a_min_N_by_leg"], oc5_values.get("F_min_after_N")),
        "F_min_transient_N": _close_lists(out["F_t_min_N_by_leg"],
                                          oc5_values.get("F_min_transient_N")),
        "t_min_after_s": _close_lists(out["t_a_s_by_leg"], oc5_values.get("t_min_after_s"))}
    return out


def _close_lists(a: Any, b: Any) -> bool | None:
    if not isinstance(a, list) or not isinstance(b, list) or len(a) != len(b):
        return None
    return all(abs(float(x) - float(y)) <= rows_judge.CMP_EPS * max(1.0, abs(float(x)))
               for x, y in zip(a, b, strict=True))


def scm_d8_values(series: dict[str, np.ndarray] | None, phases: Any) -> dict[str, Any]:
    """Rules rev25 CD-8 8 (SCM row D8): ① t_lift,sus on the 1 ms crawler normal (the t_D series;
    first sample, phase not idle / check / touch, from which it stays <= 0.01 W), ② the minimum
    true F_cyl after it with leg and time, ③ last 5 s max |roll|, |pitch| (true deck, target 0)
    + 0.02 deg mount, ④ ``scm_pad_normal_N`` <= 0 samples after it."""
    keys = ("D8_t_lift_s", "D8_F_min_after_t_lift_N", "D8_F_min_leg", "D8_F_min_t_s",
            "D8_end_attitude_plus_mount_deg", "D8_pad_lift_samples")
    out: dict[str, Any] = dict.fromkeys(keys)
    needed = ("t_s", "scm_crawler_normal_N", "F_cyl_N", "roll_pitch_deg", "scm_pad_normal_N")
    if series is None or any(key not in series for key in needed):
        return out
    t = np.asarray(series["t_s"], float)
    phases_abs = sorted((float(p["t_s"]), str(p["phase"])) for p in phases or []
                        if isinstance(p, dict))
    threshold = rows_judge.SUSTAINED_LIFT_FRACTION * rows_judge.SUSTAINED_LIFT_WEIGHT_N
    end = t >= t[-1] - END_ATTITUDE_WINDOW_S - rows_judge.CMP_EPS
    attitude = float(np.abs(np.asarray(series["roll_pitch_deg"], float)[end]).max())
    out["D8_end_attitude_plus_mount_deg"] = attitude + MOUNT_ALLOWANCE_DEG
    t_lift = rows_judge.sustained_lift_time(t, series["scm_crawler_normal_N"], phases_abs,
                                            threshold)
    if t_lift is None:
        return out
    after = t >= t_lift - rows_judge.CMP_EPS
    force = np.where(after[:, None], np.asarray(series["F_cyl_N"], float), np.inf)
    k, leg = np.unravel_index(int(np.argmin(force)), force.shape)
    pads = np.asarray(series["scm_pad_normal_N"], float)[after]
    out.update(D8_t_lift_s=t_lift, D8_F_min_after_t_lift_N=float(force[k, leg]),
               D8_F_min_leg=rows_judge.LEGS[leg], D8_F_min_t_s=float(t[k]),
               D8_pad_lift_samples=int((pads <= 0.0).sum()),
               D8_pad_lift_samples_by_leg=(pads <= 0.0).sum(axis=0).astype(int).tolist())
    return out


def g6_record_values(judged_items: dict[str, Any]) -> dict[str, Any]:
    """Rules rev25 CD-8 9: the two G6 gates not replaced by a P3 value: G6-6 (no FAULT and READY
    reached) and READY <= 120 s (``chrono_rows_judge`` D-28 / D-34 records)."""
    ready = judged_items.get("ready_D-27_D-28")
    fault = (judged_items.get("P3-8_D-34_D-35") or {}).get("fault")
    reached = has_first_ready(judged_items)
    g6_6 = None if fault is None or reached is None else (
        PASS if not fault and reached else FAIL)
    within = ready.get("READY_le_120s") if isinstance(ready, dict) else None
    return {"G6-6": g6_6, "READY_le_120s": None if within is None else (PASS if within else FAIL)}


def is_rigid_base(result: dict[str, Any] | None) -> bool:
    """A run on the rigid base (``result.json`` ``args.rigid_base`` set)."""
    value = ((result or {}).get("args") or {}).get("rigid_base")
    return value not in (None, False, "", "none", "off", 0)


def c4_row(row: RowInput) -> dict[str, Any]:
    """Rules rev24 CD-9 C-4 record row: P3-1 .. P3-9 and FAULT0 (CD-5, P3-5 not applicable on a
    rigid base), t_D, per-leg minimum force after the departure with the minimum leg and time,
    run R_c; all present = ``기록 완료``."""
    judged_items = (row.judged or {}).get("items") or {}
    if row.judged is None:
        row.missing.append("chrono_rows_judge row")
    p3b = (row.result or {}).get("p3b")
    if not isinstance(p3b, dict):
        row.missing.append("result.json p3b")
        p3b = {}
    items = p3_items(p3b, judged_items, rigid_base=is_rigid_base(row.result),
                     args=(row.result or {}).get("args"))
    values, missing = p3_record_values(items, (*P3_RECORD_ITEMS, "FAULT0"))
    leg_force = p3b.get("P3-3_leg_force") or {}
    forces, times = leg_force.get("F_min_after_N"), leg_force.get("t_min_after_s")
    values.update({
        "t_D_s": (judged_items.get("departure_t_D") or {}).get("t_departure_s"),
        "F_min_after_departure_N_by_leg": forces, "t_min_after_departure_s_by_leg": times,
        "R_c_operating": (((row.result or {}).get("p3b_ext") or {}).get("start_condition")
                          or {}).get("R_c_operating")})
    if isinstance(forces, list) and len(forces) == len(rows_judge.LEGS) and None not in forces:
        k = int(np.argmin(forces))
        values["min_leg"] = rows_judge.LEGS[k]
        values["t_min_s"] = times[k] if isinstance(times, list) and len(times) > k else None
    missing += [name for name in ("t_D_s", "F_min_after_departure_N_by_leg", "min_leg",
                                  "t_min_s", "R_c_operating") if not _present(values.get(name))]
    row.missing += [f"CD-9 record value {name}" for name in missing]
    out = {"case": row.case, "criteria_id": row.criteria_id,
           "rigid_base": is_rigid_base(row.result), "items": items, "values": values,
           "complete": not row.missing, "missing_inputs": row.missing,
           "record_status": RECORD_COMPLETE if not row.missing else RECORD_INCOMPLETE,
           "inputs_sha256": row.files}
    for entry in items:
        add_derived_reason(entry)
    if row.missing:
        out["record_reason"] = missing_reason(", ".join(row.missing))
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
    t45: dict[str, dict[str, Any]] = {}
    pairing_stops: list[dict[str, str]] = []
    if bundle == "C-5" and t45_doc is not None:
        t45, doc["t45_pairing_R22_1"], pairing_stops = t45_pairing(t45_doc, judge_doc, args)
    params = rows_judge.load_params(Path(args.params))
    doc["params"] = {key: params[key] for key in ("path", "sha256", "head_area_m2", "F_min_N")}
    rows = [grade_row(row, bundle, runner_dir, t45, params) for row in inputs]
    name_map, name_stops = runner_name_map(inputs)
    stops = pairing_stops + name_stops + row_stops(rows, judge_doc)
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
    reasons, items_cd11 = reason_check(rows), item_list(inputs, rows, doc)
    stops += cd7_cd11_stops(reasons, items_cd11) + p36_limit_stops(rows)
    stops = unique_stops(prior_stops + stops)
    doc["rows"] = rows
    doc["runner_t_lift_R19_5"] = t_lift_summary(rows)
    doc["runner_unjudged_R19_4"] = unjudged_summary(rows)
    doc["runner_name_map_R23_1"] = name_map
    doc["reasons_CD_7"] = reasons
    doc["item_list_CD_11"] = items_cd11
    doc["bundle_grade"] = bundle_grade(rows, count_ok, has_stop=bool(stops))
    return stops


def reason_check(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Rules rev24 CD-7 block: the items and rows without a needed reason."""
    gaps = reason_gaps(rows)
    return {"rule": CD7_RULE, "gaps": gaps, "ok": not gaps}


def record_reason_check(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Rules rev24 / rev25 CD-7 on the C-4 record bundle (a rev24 defect fix): every item that
    needs a reason has one, every ``기록 불완전`` row has its ``record_reason``."""
    gaps = [{"case": row["case"], "item": str(entry.get("item"))} for row in rows
            for entry in row.get("items", []) if needs_reason(entry) and not entry.get("reason")]
    gaps += [{"case": row["case"], "item": "(record status)"} for row in rows
             if not row.get("complete") and not row.get("record_reason")]
    return {"rule": CD7_RULE, "gaps": gaps, "ok": not gaps}


def p36_limit_stops(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Rules rev25 CD-4: a P3-6 limit that differs from the runner's P3b ``limit_s`` is a
    definition difference; the bundle stops before its grade."""
    stops = []
    for row in rows:
        for entry in [*row.get("items", []), *row.get("record_items", [])]:
            if entry.get("item") == "P3-6" and entry.get("limit_matches_runner") is False:
                stops.append({"case": row["case"], "reason": (
                    f"CD-4 P3-6 limit {entry.get('limit_s')} s differs from the runner P3b "
                    f"limit {entry.get('runner_limit_s')} s (rules rev25)")})
    return stops


def cd7_cd11_stops(reasons: dict[str, Any], items_cd11: dict[str, Any]) -> list[dict[str, str]]:
    """Stops before the bundle grade: an empty reason (CD-7), an item list with an empty row or
    another row count (CD-11)."""
    stops = []
    if not reasons["ok"]:
        stops.append({"case": "*", "reason": f"CD-7: {len(reasons['gaps'])} items / rows without "
                                             "a reason (rules rev24)"})
    if not items_cd11["ok"]:
        stops.append({"case": "*", "reason": f"CD-11: item list rows {items_cd11['list_rows']} / "
                                             f"bundle rows {items_cd11['bundle_rows']}, rows "
                                             f"without a graded item {items_cd11['empty_rows']}"})
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
    elif bundle == "C-4":
        rows = [c4_row(row) for row in inputs]
        doc["reasons_CD_7"] = record_reason_check(rows)
        stops = cd7_cd11_stops(doc["reasons_CD_7"], {"ok": True}) + p36_limit_stops(rows)
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
    grade.add_argument("--rows-judge",
                       help="chrono_rows_judge_4368.py judge output (C-1 .. C-5; C-4 record rows "
                            "and the C-8 P3 record values, rules rev24 CD-8 / CD-9)")
    grade.add_argument("--runner-judge-dir",
                       help="folder of <C1|C2|C5>_<case>.verify_S8C.json / .verify_S6C.json")
    grade.add_argument("--t45", help="chrono_t45_replay output (--t5, rev7) for C-5; rows paired "
                                     "by the input folder order (rev22 R22-1)")
    grade.add_argument("--t45-reference-judge",
                       help="C-5: the R3c judge_C5.json the t45 input folders came from (rev22 "
                            "R22-1 source fix; its list must equal the one from --rows-judge)")
    grade.add_argument("--t45-reference-sha256", default=R3C_JUDGE_C5_SHA256,
                       help="sha256 the --t45-reference-judge file must have (default: R3c)")
    grade.add_argument("--t45-cases-script",
                       help="C-5: the run script whose $T45Cases must equal T45_CASES (R22-1)")
    grade.add_argument("--t45-folders",
                       help="C-5: optional t45 input folder list (JSON list or one per line); "
                            "must equal the rebuilt list (R22-1)")
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
