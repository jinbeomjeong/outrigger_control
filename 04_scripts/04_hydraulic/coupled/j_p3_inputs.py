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

P3_CONTROLLER_TAG = "final_C4G2_P3"
P3_RULE = "tracked_bound"
P3_SETTING_PREFIXES = ("VB", "LS")
RULE_KEY = "run_extend_start_rule"


def is_p3_expected(controller_tag: str | None, setting: str | None) -> bool:
    """A VB / LS run (tag ``final_C4G2_P3`` or setting ``VB`` / ``LS<n>``)."""
    if controller_tag == P3_CONTROLLER_TAG:
        return True
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
    ``has_rod_reading`` (default True), ``head_only_declared`` (default False).
    """
    from outrigger_sim.control.extend_start_bound import j_p3_judgement

    expected = [row for row in rows
                if row.get("p3_expected") or row.get(RULE_KEY) == P3_RULE]
    with_rule = [row for row in expected if row.get(RULE_KEY) == P3_RULE]
    rule_missing = len(expected) - len(with_rule)
    judgement = j_p3_judgement([row.get("extend_bound_check") for row in with_rule],
                               [bool(row.get("has_rod_reading", True)) for row in with_rule],
                               [bool(row.get("head_only_declared", False)) for row in with_rule])
    if rule_missing:
        judgement["status"] = "setting_defect"
    judgement.update(runs_expected=len(expected), rule_missing_runs=rule_missing)
    return judgement
