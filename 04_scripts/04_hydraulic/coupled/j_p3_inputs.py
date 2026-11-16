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
P3_OFF_SETTINGS = ("VBJ0",)
"""436.9 VBJ0: the VBJ plant with ③ off by definition (T8 / H-7 pair), never a J-P3 row."""
RULE_KEY = "run_extend_start_rule"
REVISION_KEY = "run_extend_start_revision"
"""Row key of a ③ revision 5 record (present only then: revision 4 rows keep their keys)."""
HOLD_REVISION = 5
TEST_ONLY_SETTINGS = ("VBG4", "VBG5")
"""Case replay settings under a test constant (``jp3_case_replay.py``: C and D)."""
TEST_ONLY_SETTING_SUFFIX = "_X11"
"""Edition 4a 13.3 counterexample arm (both test-only rules, its own folder)."""


def is_test_only_setting(setting: str | None) -> bool:
    """Edition 4a R6 / 13.6: a setting built under a test constant; never a judged row (the
    ``VB`` / ``LS`` prefix test alone would take it)."""
    return setting is not None and (setting in TEST_ONLY_SETTINGS
                                    or setting.endswith(TEST_ONLY_SETTING_SUFFIX))


def is_p3_expected(controller_tag: str | None, setting: str | None) -> bool:
    """A VB / LS run: a tag whose base is ``final_C4G2_P3`` or ``final_C4G2_P3H`` with any
    LAS-b / K1 suffixes (``v5_options.is_extend_start_tag``), or setting ``VB`` / ``LS<n>`` /
    the 436.9 ``VBH``, ``VBJ``, ``LSH<n>``, ``LSJ<n>`` (not ``VBJ0``, ③ off)."""
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


def j_p3_over_rows(rows: list[dict]) -> dict:
    """J-P3 of the expected rows (``p3_expected`` True, or a ``tracked_bound`` own rule).

    Row keys read: ``p3_expected``, :data:`RULE_KEY`, ``extend_bound_check``,
    ``has_rod_reading`` (default True), ``head_only_declared`` (default False), ``setting``
    (a test-only setting, :func:`is_test_only_setting`, makes the whole set a setting defect:
    edition 4a 13.6; the revision 5 rule identity is checked by ``j_p3_judgement_rev5``).
    """
    from outrigger_sim.control.extend_start_bound import j_p3_judgement, j_p3_judgement_rev5

    test_only_runs = sum(is_test_only_setting(row.get("setting")) for row in rows)
    expected = [row for row in rows
                if row.get("p3_expected") or row.get(RULE_KEY) == P3_RULE]
    with_rule = [row for row in expected if row.get(RULE_KEY) == P3_RULE]
    rule_missing = len(expected) - len(with_rule)
    revision_4 = [row for row in with_rule if row.get(REVISION_KEY) != HOLD_REVISION]
    revision_5 = [row for row in with_rule if row.get(REVISION_KEY) == HOLD_REVISION]
    judgement = j_p3_judgement(*_judgement_inputs(revision_4))
    if revision_5:  # 436.9 6.1: the revision 5 rows apart, never mixed into one sum
        # decisions 147 / 148: the record's sensor_grade decides; conservative / old_worst rows
        # are recorded only, a row without a grade is a setting defect
        judgement["rev5"] = j_p3_judgement_rev5(*_judgement_inputs(revision_5))
        judgement["status"] = _worse_status(judgement["status"], judgement["rev5"]["status"])
    if rule_missing or test_only_runs:
        judgement["status"] = "setting_defect"
    judgement.update(runs_expected=len(expected), rule_missing_runs=rule_missing,
                     test_only_setting_runs=test_only_runs)
    return judgement


def _judgement_inputs(rows: list[dict]) -> tuple[list, list[bool], list[bool]]:
    return ([row.get("extend_bound_check") for row in rows],
            [bool(row.get("has_rod_reading", True)) for row in rows],
            [bool(row.get("head_only_declared", False)) for row in rows])


STATUS_ORDER = ("no_p3_runs", "pass", "H-7", "no_judged_runs", "setting_defect")


def _worse_status(first: str, second: str) -> str:
    """The more severe of two J-P3 statuses (``no_p3_runs`` < pass < H-7 < ``no_judged_runs``
    (edition 4a 13.2: not judgeable) < setting_defect)."""
    return max(first, second, key=STATUS_ORDER.index)
