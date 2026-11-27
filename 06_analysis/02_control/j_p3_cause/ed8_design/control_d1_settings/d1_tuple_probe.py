"""D-1 probe on synthetic rows only (no run output read): which edition 8 setting names the
shared J-P3 tuples take, and whether a judge-side context override reaches both consumers
(j_p3_inputs._revision_5_judgement / is_p3_expected and jp3_tjr_judge._check_lines)."""
from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

JUDGE = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed8-judge2")
COUPLED = JUDGE / "04_scripts" / "04_hydraulic" / "coupled"
for path in (COUPLED, JUDGE / "03_src"):
    sys.path.insert(0, str(path))

import j_p3_inputs as inputs  # noqa: E402
import jp3_tjr_judge as tjr  # noqa: E402
import run_v5  # noqa: E402

ED8_ON_TAG = "final_C4G2_P3X_LAS_K1_LSB_ED8"
ED8_OFF_TAG = "final_C4G2_LAS_K1_LSB_ED8"
ED8_JP3_JUDGED = ("VBN", "LSN1", "LSN2", "LSN3", "LSN4", "VBKN", "VBNslow", "VBNfast",
                  "VBNc005", "VBNc04")
ED8_P3_OFF = ("VBN0", "VBKN0")


def stub_judge(records, rods, heads):
    return {"status": "pass", "runs_judged": len(records)}


def split(names):
    rows = [{"setting": name, "extend_bound_check": {}} for name in names]
    out = inputs._revision_5_judgement(rows, stub_judge, label="rev7")
    return {"judged": out["rev7"]["runs_judged"], "status": out["rev7"]["status"],
            "unjudged": out["rev7_unjudged_setting_runs"]}


@contextlib.contextmanager
def ed8_jp3_settings():
    saved = (inputs.REV5_JUDGED_SETTINGS, inputs.P3_OFF_SETTINGS, tjr.REV5_JUDGED_SETTINGS)
    inputs.REV5_JUDGED_SETTINGS = (*saved[0], *ED8_JP3_JUDGED)
    inputs.P3_OFF_SETTINGS = (*saved[1], *ED8_P3_OFF)
    tjr.REV5_JUDGED_SETTINGS = (*saved[2], *ED8_JP3_JUDGED)
    try:
        yield
    finally:
        inputs.REV5_JUDGED_SETTINGS, inputs.P3_OFF_SETTINGS, tjr.REV5_JUDGED_SETTINGS = saved


ed8_all = list(run_v5.ED8_SETTINGS)
judged_sens = list(run_v5.ED8_SENSITIVITY_SETTINGS)
record_sens = list(run_v5.ED8_SENSITIVITY_RECORD_SETTINGS)
before_tuple = tuple(inputs.REV5_JUDGED_SETTINGS)
before_off = tuple(inputs.P3_OFF_SETTINGS)
result = {
    "run_v5_ED8_SETTINGS": ed8_all,
    "run_v5_ED8_SENSITIVITY_SETTINGS": judged_sens,
    "run_v5_ED8_SENSITIVITY_RECORD_SETTINGS": record_sens,
    "ed8_names_in_REV5_now": [n for n in ed8_all if n in inputs.REV5_JUDGED_SETTINGS],
    "ed8_names_in_P3_OFF_now": [n for n in ed8_all if n in inputs.P3_OFF_SETTINGS],
    "tjr_binding_is_same_object": tjr.REV5_JUDGED_SETTINGS is inputs.REV5_JUDGED_SETTINGS,
    "is_p3_expected_now": {n: inputs.is_p3_expected(ED8_OFF_TAG if n in ED8_P3_OFF
                                                     else ED8_ON_TAG, n) for n in ed8_all},
    "is_p3_expected_off_tag_now": {n: inputs.is_p3_expected(ED8_OFF_TAG, n) for n in ED8_P3_OFF},
    "split_now": {
        "cases_VBN_LSN": split(run_v5.ED8_JUDGED_SETTINGS * 2),
        "CS_judged4": split(judged_sens),
        "CD_VBN_VBNslow": split(["VBN"] * 12 + ["VBNslow"] * 12),
        "record6": split(record_sens),
    },
    "ed8_names_absent_from_older_tuples": all(
        n not in (*inputs.ED6_JUDGED_SETTINGS, *inputs.ED7_JUDGED_SETTINGS,
                  "VBJ", "LSJ1", "LSJ2", "LSJ3", "LSJ4", "VBK") for n in ed8_all),
    "proposed_names_are_run_v5_settings": all(n in run_v5.ED8_SETTINGS
                                              for n in (*ED8_JP3_JUDGED, *ED8_P3_OFF)),
    "proposed_equals_rule_sets": sorted(ED8_JP3_JUDGED) == sorted(
        [*run_v5.ED8_JUDGED_SETTINGS, "VBKN", *judged_sens]),
}
with ed8_jp3_settings():
    result["split_override"] = {
        "cases_VBN_LSN": split(run_v5.ED8_JUDGED_SETTINGS * 2),
        "CS_judged4": split(judged_sens),
        "CD_VBN_VBNslow": split(["VBN"] * 12 + ["VBNslow"] * 12),
        "record6": split(record_sens),
        "ed7_names": split(list(inputs.ED7_JUDGED_SETTINGS)),
    }
    result["is_p3_expected_off_tag_override"] = {
        n: inputs.is_p3_expected(ED8_OFF_TAG, n) for n in ED8_P3_OFF}
    result["tjr_line_check_takes"] = {n: n in tjr.REV5_JUDGED_SETTINGS for n in ("VBN", "VBN0")}
result["restored"] = (tuple(inputs.REV5_JUDGED_SETTINGS) == before_tuple
                      and tuple(inputs.P3_OFF_SETTINGS) == before_off
                      and tjr.REV5_JUDGED_SETTINGS is inputs.REV5_JUDGED_SETTINGS)
result["split_after_exit_ed7"] = split(list(inputs.ED7_JUDGED_SETTINGS))
print(json.dumps(result, indent=1))
