"""J-P3 inputs of the replay tools (v5 criteria revision 9, ``v5_criteria_rev9.md`` 3).

Which runs J-P3 must cover, and what each run declares:

* expected: a VB / LS run, i.e. controller tag ``final_C4G2_P3`` or job setting ``VB`` /
  ``LS<n>`` (revision 8 3.1). An expected run whose own ③ rule is not ``tracked_bound`` (or not
  recorded) is a setting defect: it cannot drop out of J-P3 silently.
* ``has_rod_reading``: a rod-side pressure reached the controller (revision 9 3.1).
* ``head_only_declared``: the run was set up without rod readings (revision 9 3.1): the T4h meta
  key ``head_only_declared`` when present, else the harness path of a ``verdict_cases`` case
  (steady = head-only). Chrono runs read both pressures and are never declared.

:func:`j_p3_over_rows` applies ``extend_start_bound.j_p3_judgement`` (the five-row table) to the
expected rows and adds ``runs_expected``, ``runs_judged`` and ``rule_missing_runs``.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from outrigger_sim.hydraulics.v5_options import (  # noqa: E402
    EXTEND_START_TAGS,
    is_extend_start_tag,
)

P3_CONTROLLER_TAG = "final_C4G2_P3"
P3_CONTROLLER_TAGS = EXTEND_START_TAGS
"""③-on tags before and after the LAS-b / K1 switches (``v5_options.EXTEND_START_TAGS``), a
list for records; :func:`is_p3_expected` judges by the base tag instead."""
P3_RULE = "tracked_bound"
P3_SETTING_PREFIXES = ("VB", "LS")
P3_OFF_SETTINGS = ("VBJ0", "VBK0")
"""436.9 VBJ0: the VBJ plant with ③ off by definition (T8 / H-7 pair), never a J-P3 row;
edition 5 VBK0 (VBJ0 with a rod fault plan) likewise."""
RULE_KEY = "run_extend_start_rule"
REVISION_KEY = "run_extend_start_revision"
"""Row key of a ③ revision 5 or 6 record (present only then: revision 4 rows keep their
keys)."""
HOLD_REVISION = 5
HOLD_REVISIONS = (5, 6)
"""The hold revisions (``extend_start_bound.HOLD_REVISIONS``): edition 4a revision 5 and
edition 5 revision 6, each judged apart (edition 5 4.6, 6.1)."""
TEST_ONLY_SETTINGS = ("VBG4", "VBG5", "VBG6")
"""Case replay settings under a test constant (``jp3_case_replay.py``: C and D; D is VBG6 from
edition 5, VBG5 the edition 4a records)."""
TEST_ONLY_SETTING_SUFFIX = "_X11"
"""Edition 4a 13.3 counterexample arm (both test-only rules, its own folder)."""
REV5_JUDGED_SETTINGS = ("VBJ", "LSJ1", "LSJ2", "LSJ3", "LSJ4", "VBK")
"""436.9 spec 6.1 / 13.2, addendum 4a-2 R6: the hold revision rows J-P3 judges (edition 5
6.3.7 (4): the VBK lines too); the other hold revision rows (VBH, LSH1 .. 4, a row without a
setting) are recorded apart."""
REVISION_5_RECORD_KEY = "rule_revision"
"""``extend_bound_check`` key of a hold revision record (value 5 or 6)."""


ROD_READING_EVIDENCE_KEYS = ("rod_reading_truth_calls", "two_pressure_reads")
"""Addendum 4a-2 B2, counted at two places of a harness run (``hydraulics_record``, record
only): ``rod_reading_truth_calls`` inside the P4 reading
(``harness_hydraulics.with_plant_truth_pressures``), ``two_pressure_reads`` at the monitor input
(controller reads with a rod-side pressure). A run with ``rod_reading_truth`` has 1 = 2 > 0; a
run without P4 has 1 = 0."""


def rod_reading_evidence_problems(record: dict | None, options: dict | None) -> list[str]:
    """Addendum 4a-2 B2: why a result row's P4 evidence does not fit its options (empty = it
    fits; anything else makes its bundle a ``setting_defect``).

    Args:
        record: The row's ``hydraulics_record``.
        options: The row's ``hydraulic_options`` (``HydraulicOptions.to_dict``; None = none).
    """
    record = record or {}
    missing = [key for key in ROD_READING_EVIDENCE_KEYS if key not in record]
    if missing:
        return [f"P4 evidence keys missing: {missing}"]
    truth_calls, monitor_reads = (int(record[key]) for key in ROD_READING_EVIDENCE_KEYS)
    if (options or {}).get("rod_reading_truth"):
        if truth_calls < 1 or truth_calls != monitor_reads:
            return [f"rod_reading_truth: {truth_calls} truth readings, {monitor_reads} monitor "
                    "rod reads (equal and > 0 needed)"]
        return []
    if truth_calls != 0:
        return [f"P4 off but {truth_calls} truth readings"]
    return []


def is_test_only_setting(setting: str | None) -> bool:
    """Edition 4a R6 / 13.6: a setting built under a test constant; never a judged row (the
    ``VB`` / ``LS`` prefix test alone would take it)."""
    return setting is not None and (setting in TEST_ONLY_SETTINGS
                                    or setting.endswith(TEST_ONLY_SETTING_SUFFIX))


L1_REFERENCE_LEVEL = "L1"
"""Erratum 2 2-1 (audit warning 5): an L1 line is a grade reference, never a judged row."""


def is_l1_reference_line(row: dict) -> bool:
    """An r79 L1 line (``level`` L1, or a key whose level token is L1)."""
    key = str(row.get("key") or "")
    plain = key.split("#", 1)[1] if "#" in key else key
    return row.get("level") == L1_REFERENCE_LEVEL or plain.startswith(f"{L1_REFERENCE_LEVEL}|")


def l1_reference_file_problem(path, label: str) -> str | None:
    """Why the run file ``path`` may not be a J-P3 / j9_main / T-JR-12 judged input: it holds
    L1 reference lines only (the 12b ``l1ref`` runs, the T-JR-12a L1 runs; erratum 2 2-1).
    None: not such a file (or not a run file: other checks name it)."""
    import json
    from pathlib import Path

    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    rows = document.get("results") if isinstance(document, dict) else document
    if isinstance(rows, list) and rows and all(isinstance(row, dict) and is_l1_reference_line(row)
                                               for row in rows):
        return f"{label} {path} is an L1 reference run (no judged input, erratum 2 2-1)"
    return None


def is_p3_expected(controller_tag: str | None, setting: str | None) -> bool:
    """A VB / LS run: a tag whose base is ``final_C4G2_P3`` or ``final_C4G2_P3H`` with any
    LAS-b / K1 suffixes (``v5_options.is_extend_start_tag``), or setting ``VB`` / ``LS<n>`` /
    the 436.9 ``VBH``, ``VBJ``, ``LSH<n>``, ``LSJ<n>`` (not :data:`P3_OFF_SETTINGS`, ③ off)."""
    if is_extend_start_tag(controller_tag):
        return True
    if setting in P3_OFF_SETTINGS:
        return False
    return setting is not None and setting.startswith(P3_SETTING_PREFIXES)


def harness_head_only_declared(meta: dict) -> bool:
    """Revision 9 3.1 declaration of a harness T4h record: the meta key, else the steady path of
    its ``verdict_cases`` case (False for jobs without a known case)."""
    if meta.get("head_only_declared") is not None:
        return bool(meta["head_only_declared"])
    case_id = (meta.get("job") or {}).get("case")
    if case_id is None:
        return False
    import verdict_cases

    case = verdict_cases.CASES.get(case_id)
    return case is not None and case.path == verdict_cases.PATH_STEADY


def is_revision_5_record(row: dict) -> bool:
    """The row's ``extend_bound_check`` is a hold revision record (``rule_revision`` 5 or 6;
    a revision 6 row is never read as revision 4)."""
    return record_revision(row) in HOLD_REVISIONS


def record_revision(row: dict) -> object:
    """``rule_revision`` of the row's ``extend_bound_check`` (None without one)."""
    record = row.get("extend_bound_check") or {}
    return record.get(REVISION_5_RECORD_KEY)


def j_p3_over_rows(rows: list[dict], *, edition5_order: bool = False) -> dict:
    """J-P3 of the expected rows (``p3_expected`` True, or a ``tracked_bound`` own rule).

    Row keys read: ``p3_expected``, :data:`RULE_KEY`, :data:`REVISION_KEY`,
    ``extend_bound_check``, ``has_rod_reading`` (default True), ``head_only_declared`` (default
    False), ``setting`` (a test-only setting, :func:`is_test_only_setting`, makes the whole set
    a setting defect: edition 4a 13.6; the revision 5 rule identity is checked by
    ``j_p3_judgement_rev5``).

    Addendum 4a-2 R6: the revision 5 judgement takes the :data:`REV5_JUDGED_SETTINGS` rows only
    (the other revision 5 rows are ``rev5_record_only``, never judged); a row with a revision 5
    record but without :data:`REVISION_KEY` is refused (``revision_key_missing_runs``, a setting
    defect), it never goes to the revision 4 judgement, which itself refuses a revision 5
    record. ``status_by_revision`` keeps both statuses apart (``no_judged_runs`` of revision 5
    does not hide a revision 4 H-7).

    ``edition5_order`` (edition 5 erratum 2 2-10.1 5; the j9_main judge): a hold revision whose
    judged rows have a breach (:func:`has_judged_breach`) counts as H-7 in
    ``status_by_revision`` and in the combination, which takes :data:`STATUS_ORDER_ED5` (H-7 >
    setting_defect > not judgeable > pass), the row-level defects included; the revision's own
    judgement (``rev<n>``) keeps its status and the defect counts stay in the result. Default
    False: the order of the sealed tools, unchanged.
    """
    order = STATUS_ORDER_ED5 if edition5_order else STATUS_ORDER
    from outrigger_sim.control.extend_start_bound import j_p3_judgement, j_p3_judgement_rev5

    test_only_runs = sum(is_test_only_setting(row.get("setting")) for row in rows)
    l1_reference_runs = sum(is_l1_reference_line(row) for row in rows)  # erratum 2 2-1
    expected = [row for row in rows
                if row.get("p3_expected") or row.get(RULE_KEY) == P3_RULE]
    with_rule = [row for row in expected if row.get(RULE_KEY) == P3_RULE]
    rule_missing = len(expected) - len(with_rule)
    by_revision = {revision: [row for row in with_rule if row.get(REVISION_KEY) == revision]
                   for revision in HOLD_REVISIONS}
    keyed = [row for rows_of in by_revision.values() for row in rows_of]
    unkeyed_hold = [row for row in with_rule
                    if not _is_keyed(row, keyed) and is_revision_5_record(row)]
    # edition 5 4.6: a row key that names another revision than its record is a defect (a
    # row without a record goes to the run-case table of its revision as before)
    key_record_mismatch = [row for row in keyed if record_revision(row) is not None
                           and record_revision(row) != row.get(REVISION_KEY)]
    revision_4 = [row for row in with_rule
                  if not _is_keyed(row, keyed) and not is_revision_5_record(row)]
    judgement = j_p3_judgement(*_judgement_inputs(revision_4))
    status_by_revision = {"4": judgement["status"]}
    for revision, hold_rows in by_revision.items():
        if not hold_rows:
            continue
        # 436.9 6.1 / edition 5 4.6: each hold revision apart, never mixed into one sum
        judgement.update(_revision_5_judgement(hold_rows, j_p3_judgement_rev5,
                                               label=f"rev{revision}"))
        revision_status = judgement[f"rev{revision}"]["status"]
        if edition5_order and has_judged_breach(judgement[f"rev{revision}"]):
            revision_status = "H-7"
        status_by_revision[str(revision)] = revision_status
        judgement["status"] = _worse_status(judgement["status"], revision_status, order)
    if rule_missing or test_only_runs or unkeyed_hold or key_record_mismatch or l1_reference_runs:
        judgement["status"] = _worse_status(judgement["status"], "setting_defect", order)
    judgement.update(runs_expected=len(expected), rule_missing_runs=rule_missing,
                     test_only_setting_runs=test_only_runs, l1_reference_runs=l1_reference_runs,
                     revision_key_missing_runs=len(unkeyed_hold),
                     revision_key_mismatch_runs=len(key_record_mismatch),
                     status_by_revision=status_by_revision)
    return judgement


def _is_keyed(row: dict, keyed: list[dict]) -> bool:
    return any(row is other for other in keyed)


def _revision_5_judgement(revision_5: list[dict], judge_rev5, label: str = "rev5") -> dict:
    """``<label>`` (the judged settings) and ``<label>_record_only`` (the other rows of that
    hold revision; ``label`` ``rev5`` or ``rev6``)."""
    judged = [row for row in revision_5 if row.get("setting") in REV5_JUDGED_SETTINGS]
    others = [row for row in revision_5 if row.get("setting") not in REV5_JUDGED_SETTINGS]
    out = {label: judge_rev5(*_judgement_inputs(judged)),
           f"{label}_unjudged_setting_runs": len(others)}
    if not judged:  # 13.2: hold revision rows but no judged one = not judgeable, never a pass
        out[label]["status"] = "no_judged_runs"
    if others:
        out[f"{label}_record_only"] = judge_rev5(*_judgement_inputs(others))
    return out


def _judgement_inputs(rows: list[dict]) -> tuple[list, list[bool], list[bool]]:
    return ([row.get("extend_bound_check") for row in rows],
            [bool(row.get("has_rod_reading", True)) for row in rows],
            [bool(row.get("head_only_declared", False)) for row in rows])


STATUS_ORDER = ("no_p3_runs", "pass", "H-7", "no_judged_runs", "judged_key_missing",
                "setting_defect")
STATUS_ORDER_ED5 = ("no_p3_runs", "pass", "no_judged_runs", "judged_key_missing",
                    "setting_defect", "H-7")
"""Edition 5 erratum 2 2-10.1 5: H-7 > setting_defect > not judgeable > pass, for the
edition 5 judges only (``j_p3_over_rows(..., edition5_order=True)``); :data:`STATUS_ORDER`
stays the order of the sealed tools that share this module (436.8 / edition 4a replays)."""


def _worse_status(first: str, second: str, order: tuple[str, ...] = STATUS_ORDER) -> str:
    """The more severe of two J-P3 statuses in ``order`` (default :data:`STATUS_ORDER`:
    ``no_p3_runs`` < pass < H-7 < ``no_judged_runs`` (edition 4a 13.2: not judgeable) <
    ``judged_key_missing`` (addendum 4a-5 3.3) < setting_defect)."""
    return max(first, second, key=order.index)


def has_judged_breach(judgement: dict | None) -> bool:
    """Edition 5 erratum 2 2-10.1 5: a judged row of a hold revision judgement
    (``j_p3_judgement_rev5``) has a judged key > 0 (``runs_with_breach``) - H-7 read from the
    judged rows whatever its combined status (defect rows are no judged rows)."""
    return bool((judgement or {}).get("runs_with_breach"))
