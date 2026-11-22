"""436.9 J-P3 edition 5 erratum 6 (``jp3_remedy_spec_v5_erratum6.md``, sealed ``9a92bd34``):
6-1 the VBG6 -> VBG5 pairing, 6-2 the revision 6 P4-2 / P4-4 / P4-9 records, 6-2A the case B / D
conditions (``case_bd_conditions``) and the 6-6 dry check of ``jp3_baseline_compare main``.

Synthetic input (6-6): the stored baseline ``221456d`` rows and T4h, copied; only the setting
name (VBG5 -> VBG6), the ③ identity (revision 6, ``spec_edition`` fe6f5844) and the edition 5
output form (P4 evidence keys, the trace columns edition 5 adds, ``head_only_declared``) are
changed, then each test sets the one item it checks. No edition 5 run output is read.
Every test asserts the exact exit code and every problem class (6-6 (가) .. (바)).
"""

from __future__ import annotations

import copy
import json
import math
import os
import sys
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
SRC_DIR = ROOT / "03_src"
for _path in (COUPLED_DIR, SRC_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import jp3_baseline_compare as compare  # noqa: E402
import jp3_p51_compare as p51  # noqa: E402

DATA_ROOT = Path(os.environ.get("OUTRIGGER_RECORDS_ROOT") or ROOT)
BASELINE = DATA_ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "baseline_221456d"
pytestmark = pytest.mark.skipif(not (BASELINE / "SHA256SUMS").is_file(),
                                reason="stored baseline_221456d not present")

BAR = 1.0e5
REV6_SETTINGS = ("VBH", "LSH1", "LSH2", "LSH3", "LSH4", "VBJ", "LSJ1", "LSJ2", "LSJ3", "LSJ4",
                 "VBG6")
REV4_SETTINGS = ("VB", "LS1", "LS2", "LS3", "LS4", "VBG4")
E_SETTINGS = ("VBJ", "LSJ1", "LSJ2", "LSJ3", "LSJ4")
SEED_COLUMNS = ["net_force_seed_step_N", "m2_shift_clipped"]
BREACH_TIME_S = 49.2
"""The synthetic C breach read (RR) and the VBG6 read that must cover it."""

RowEdit = Callable[[str, dict], None]
ArraysEdit = Callable[[str, dict], None]


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _arrays(npz: Path) -> dict:
    with np.load(npz, allow_pickle=False) as data:
        return {name: data[name] for name in data.files}


def _edition5_row(row: dict, arrays: dict) -> dict:
    """A baseline row in the edition 5 output form with the sealed revision 6 identity."""
    new = copy.deepcopy(row)
    if new["job"]["setting"] == "VBG5":
        new["job"]["setting"] = "VBG6"
    hydraulics = new.setdefault("hydraulics_record", {})
    check = hydraulics.setdefault("extend_bound_check", {})
    has_truth = bool((new.get("hydraulic_options") or {}).get("rod_reading_truth"))
    hydraulics["rod_reading_truth_calls"] = 100 if has_truth else 0
    hydraulics["two_pressure_reads"] = 100
    if check.get("rule_revision") == 5:
        check.update(compare.IDENTITY_OF_REVISION[6], rule_revision=6)
        for key in (*compare.JUDGED_KEYS, compare.RETRACT_TRACKER_READS_KEY,
                    *compare.REVISION_6_REASON_KEYS):
            check[key] = [0, 0, 0, 0]
        check[compare.RETRACT_TRACKER_LOG_KEY] = []
        check["class_reads"] = {name: [1, 0, 0, 0] for name in compare.CLASS_NAMES}
        check["jp3_judged_row"] = new["job"]["setting"] in E_SETTINGS
        hydraulics[compare.RELOCK_KEY] = 0
        count = hydraulics.get("p1_retract_seed_count") or 1
        hydraulics["p1_retract_seed_count"] = count
        hydraulics["p1_retract_seed_log_columns"] = SEED_COLUMNS
        hydraulics["p1_retract_seed_log"] = [[0.0, False] for _ in range(count)]
    if new["job"]["setting"] == "VBG6":
        new.setdefault("lock_window_alignment", {}).setdefault("monitor_stretch_rule", {})[
            "hold_speed_m_s"] = compare.u_hold_m_s()
    if new["job"]["setting"] == "VBG4":
        read = _read_near(arrays["t_s"], BREACH_TIME_S)
        check["breach_reads"] = [0, 0, 0, 1]
        check["first_breach_t_s"] = [None, None, None, round(float(arrays["t_s"][read]), 6)]
    return new


def _edition5_arrays(setting: str, arrays: dict) -> dict:
    """The baseline T4h with the columns edition 5 writes on a hold revision row."""
    out = dict(arrays)
    meta = json.loads(str(out["meta_json"]))
    meta["head_only_declared"] = False
    out["meta_json"] = np.array(json.dumps(meta))
    if "jp3_t_s" in out:
        shape = out["jp3_used_bound_Pa"].shape
        out["jp3_model_bound_source"] = np.full(shape, -1, dtype=np.int8)
        out["jp3_source_names"] = np.array(["model", compare.RETRACT_TRACKER_SOURCE])
        out["jp3_model_bound_inherited"] = np.zeros(shape, dtype=bool)
    if setting == "VBG6":  # the C breach read is covered (by at least +5 bar)
        read = _read_near(out["jp3_t_s"], BREACH_TIME_S)
        used = out["jp3_used_bound_Pa"].copy()
        used[read, compare.RR_LEG] = max(
            used[read, compare.RR_LEG], out["jp3_p_tr_Pa"][read, compare.RR_LEG] + 5.0 * BAR)
        out["jp3_used_bound_Pa"] = used
    return out


def _read_near(times: np.ndarray, t_s: float) -> int:
    return int(np.argmin(np.abs(np.asarray(times, float) - t_s)))


def _world(tmp_path: Path, row_edit: RowEdit | None = None,
           arrays_edit: ArraysEdit | None = None) -> list[Path]:
    """The two ``--new`` row files and their ``_t4h`` folders (edition 5 form, then the
    edits by setting); returns the row files."""
    news = []
    for name in compare.BASELINE_ROW_FILES:
        rows_out = []
        folder = tmp_path / "run" / f"{Path(name).stem}_t4h"
        folder.mkdir(parents=True, exist_ok=True)
        for row in _rows(BASELINE / name):
            arrays = _arrays(BASELINE / f"{Path(name).stem}_t4h" / Path(row["t4h_file"]).name)
            new = _edition5_row(row, arrays)
            setting = new["job"]["setting"]
            new_arrays = _edition5_arrays(setting, arrays)
            if row_edit is not None:
                row_edit(setting, new)
            if arrays_edit is not None:
                arrays_edit(setting, new_arrays)
            np.savez(folder / Path(row["t4h_file"]).name, **new_arrays)
            rows_out.append(new)
        path = tmp_path / "run" / name
        path.write_text("".join(json.dumps(row) + "\n" for row in rows_out), encoding="utf-8")
        news.append(path)
    return news


def _run(tmp_path: Path, monkeypatch, row_edit: RowEdit | None = None,
         arrays_edit: ArraysEdit | None = None) -> tuple[int, dict]:
    news = _world(tmp_path, row_edit, arrays_edit)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    out = tmp_path / "report.json"
    code = compare.main([str(BASELINE), "--new", *map(str, news), "--out", str(out)])
    return code, json.loads(out.read_text(encoding="utf-8"))


def _classes(report: dict) -> dict[str, list[str]]:
    return {kind: report.get(kind) for kind in ("failures", "setting_defects", "not_judgeable")}


def _only(setting: str, edit: Callable[[dict], None]) -> RowEdit:
    return lambda name, row: edit(row) if name == setting else None


def _check(row: dict) -> dict:
    return row["hydraulics_record"]["extend_bound_check"]


# --- 6-1 pairing, 6-2 records, the passing synthetic set ------------------------------------------

def test_vbg6_pairs_with_the_baseline_vbg5_row_and_the_set_passes(tmp_path, monkeypatch) -> None:
    """6-1: the VBG6 row is the VBG5 row's pair (17 pairs, A .. E); the synthetic set with zero
    judged keys and a covered C breach read passes with no problem of any class (exit 0)."""
    code, report = _run(tmp_path, monkeypatch)
    assert code == compare.EXIT_PASS and report["status"] == "pass"
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": []}
    settings = [pair["setting"] for pair in report["pairs"]]
    assert len(settings) == 17 and sorted(settings) == sorted((*REV6_SETTINGS, *REV4_SETTINGS))
    assert "VBG5" not in settings
    assert report["case_bd"]["D"]["covering"]["judged_reads"] == 1
    assert report["case_bd"]["D"]["numeric"]["status"] == "record"  # C's own command order


def test_pairing_map_is_the_p51_constant() -> None:
    assert compare.SETTING_OF_PREVIOUS_EDITION is p51.SETTING_OF_PREVIOUS_EDITION
    assert compare.SETTING_OF_PREVIOUS_EDITION == {"VBG6": "VBG5"}
    row = {"job": {"case": "R12", "setting": "VBG6"}}
    assert json.loads(compare._baseline_job_key(row))["setting"] == "VBG5"
    assert json.loads(compare._baseline_job_key({"job": {"setting": "VBG4"}}))["setting"] == "VBG4"


def test_rev4_unchanged_and_rev6_p4_records(tmp_path, monkeypatch) -> None:
    """6-2: the revision 4 pairs (A, C) keep P4-2 / 4 / 9 judged; the eleven revision 6 pairs
    (B, D, E) have them as records with the revision 6 reason counts."""
    code, report = _run(tmp_path, monkeypatch)
    assert code == compare.EXIT_PASS
    marks = {pair["setting"]: pair["p4_2_4_9"] for pair in report["pairs"]}
    assert {s for s, mark in marks.items() if mark == "judged"} == set(REV4_SETTINGS)
    assert {s for s, mark in marks.items() if mark == "record"} == set(REV6_SETTINGS)
    records = {record["setting"]: record for record in report["p4_records"]}
    assert set(records) == set(REV6_SETTINGS)
    for record in records.values():
        assert record["items"] == ["P4-2", "P4-4", "P4-9"]
        assert record["record_status"] == "recorded"
        assert record["findings"] == {"setting_defects": [], "not_judgeable": [], "failures": []}
        assert record["revision_6_reasons"] == dict.fromkeys(compare.REVISION_6_REASON_KEYS,
                                                             [0, 0, 0, 0])


@pytest.mark.parametrize("label, setting, edit, expected", [
    ("P4-2", "VBH", "lower", "VBH: P4-2 a read's used bound below the baseline"),
    ("P4-9", "VBJ", "tracker", "VBJ: P4-9 retract_tracker records without fallback"),
    ("P4-4", "LSJ2", "seed", "LSJ2: P4-4 p1_retract_seed_count differs from the baseline"),
])
def test_rev6_p4_records_do_not_change_the_status(tmp_path, monkeypatch, label, setting, edit,
                                                  expected) -> None:
    """6-6 (바): a synthetic P4-2 / P4-4 / P4-9 violation on a revision 6 row is a record: exit
    and status unchanged (0, pass), the finding in that row's ``p4_records``."""
    def row_edit(name: str, row: dict) -> None:
        if name != setting:
            return
        if edit == "tracker":
            _check(row)[compare.RETRACT_TRACKER_READS_KEY] = [1, 0, 0, 0]
        elif edit == "seed":
            hydraulics = row["hydraulics_record"]
            hydraulics["p1_retract_seed_count"] += 1
            hydraulics["p1_retract_seed_log"].append([0.0, False])

    def arrays_edit(name: str, arrays: dict) -> None:
        if name == setting and edit == "lower":
            used = arrays["jp3_used_bound_Pa"].copy()
            used[10, 0] -= 2.0 * BAR
            arrays["jp3_used_bound_Pa"] = used

    code, report = _run(tmp_path, monkeypatch, row_edit, arrays_edit)
    assert code == compare.EXIT_PASS and report["status"] == "pass", label
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": []}
    findings = {r["setting"]: r["findings"] for r in report["p4_records"]}
    assert findings[setting]["failures"] == [expected]
    assert all(not any(f.values()) for s, f in findings.items() if s != setting)


# --- 6-6 (라): every judged item caught -----------------------------------------------------------

def _set_key(key: str, values: list[int]) -> Callable[[dict], None]:
    return lambda row: _check(row).__setitem__(key, values)


def _other_hash(row: dict) -> None:
    row["commands_sha256"] = "f" * 64


@pytest.mark.parametrize("item, setting, edit, failure", [
    ("E P4-1", "VBJ", _other_hash, "VBJ: P4-1 commands_sha256 differs"),
    ("E P4-3a", "LSJ3", _set_key("jp3a_breach_reads", [0, 1, 0, 0]),
     "LSJ3: P4-3a jp3a_breach_reads [0, 1, 0, 0]"),
    ("A P4-1", "LS2", _other_hash, "LS2: P4-1 commands_sha256 differs"),
    ("C P4-1", "VBG4", _other_hash, "VBG4: P4-1 commands_sha256 differs"),
    ("B J-P3a", "LSH1", _set_key("jp3a_breach_reads", [1, 0, 0, 0]),
     "LSH1: 6-2A B J-P3a jp3a_breach_reads sum 1 (0 needed)"),
    ("B J-P3b", "VBH", _set_key("jp3b_breach_over_tol_reads", [0, 0, 2, 0]),
     "VBH: 6-2A B J-P3b jp3b_breach_over_tol_reads sum 2 (0 needed)"),
    ("D (D-가)", "VBG6", _set_key("jp3c_breach_reads", [0, 0, 0, 1]),
     "VBG6: 6-2A (D-가) jp3c_breach_reads sum 1 (0 needed)"),
])
def test_each_judged_item_fails_alone(tmp_path, monkeypatch, item, setting, edit,
                                      failure) -> None:
    code, report = _run(tmp_path, monkeypatch, _only(setting, edit))
    assert code == compare.EXIT_FAILED and report["status"] == "failed", item
    assert _classes(report) == {"failures": [failure], "setting_defects": [],
                                "not_judgeable": []}, item


def test_a_and_c_p4_evidence_is_judged(tmp_path, monkeypatch) -> None:
    """A / C: the P4 evidence (B2) stays judged - truth readings with P4 off is a defect."""
    def edit(row: dict) -> None:
        row["hydraulics_record"]["rod_reading_truth_calls"] = 3

    code, report = _run(tmp_path, monkeypatch, _only("VB", edit))
    assert code == compare.EXIT_NOT_JUDGEABLE and report["status"] == "setting_defect"
    assert _classes(report) == {"failures": [], "not_judgeable": [],
                                "setting_defects": ["VB: P4 off but 3 truth readings"]}


def test_case_b_lsh3_jp3b_and_jp3c_are_records(tmp_path, monkeypatch) -> None:
    def edit(name: str, row: dict) -> None:
        if name == "LSH3":
            _check(row)["jp3b_breach_over_tol_reads"] = [0, 0, 0, 4]
        if name == "LSH2":
            _check(row)["jp3c_breach_reads"] = [1, 0, 0, 0]

    code, report = _run(tmp_path, monkeypatch, edit)
    assert code == compare.EXIT_PASS and report["status"] == "pass"
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": []}
    records = report["case_bd"]["B"]["records"]
    assert records["LSH3 jp3b_breach_over_tol_reads"] == 4
    assert records["LSH2 jp3c_breach_reads"] == 1


def test_covering_fails_when_the_vbg6_gap_is_not_positive(tmp_path, monkeypatch) -> None:
    """(D-나): gap = used - p_tr <= 0 at the C breach read is a failure (exit 1)."""
    def arrays_edit(name: str, arrays: dict) -> None:
        if name == "VBG6":
            read = _read_near(arrays["jp3_t_s"], BREACH_TIME_S)
            used = arrays["jp3_used_bound_Pa"].copy()
            used[read, compare.RR_LEG] = arrays["jp3_p_tr_Pa"][read, compare.RR_LEG]
            arrays["jp3_used_bound_Pa"] = used

    code, report = _run(tmp_path, monkeypatch, None, arrays_edit)
    assert code == compare.EXIT_FAILED and report["status"] == "failed"
    t_s = report["case_bd"]["D"]["covering"]["rows"][0]["t_s"]
    assert _classes(report) == {"setting_defects": [], "not_judgeable": [], "failures": [
        f"6-2A (D-나): VBG6 does not cover the C breach read at {t_s} s leg 3"]}


# --- (D-다) under C's command order -------------------------------------------------------------

EXTENSION_M_S = 4.71e-3
"""The 4a 5.3 C premise: RR 49.0 -> 49.1 s a 4.71 mm/s extension (erratum 7 7-1)."""


def _same_order_arrays(carry_gap_bar: float, hold_gap_bar: float, carry_class: str = "carry_ext",
                       carry_acting_m_s: float = EXTENSION_M_S) -> ArraysEdit:
    """C's RR acting commands in 48.7 .. 49.0 s set to 0 and at 49.1 s to
    ``carry_acting_m_s`` (same order when above u_hold, erratum 7 7-1); VBG6 RR 49.1 s
    ``carry_class`` with ``carry_gap_bar``, the window reads HOLD with ``hold_gap_bar``."""
    def edit(name: str, arrays: dict) -> None:
        if name == "VBG4":
            times = arrays["t_s"]
            commands = arrays["command_m_s"].copy()
            for read in np.flatnonzero((times >= 48.7 - 1e-6) & (times <= 49.0 + 1e-6)):
                commands[read - 1, compare.RR_LEG] = 0.0
            commands[_read_near(times, compare.CARRY_READ_S) - 1, compare.RR_LEG] = carry_acting_m_s
            arrays["command_m_s"] = commands
        if name == "VBG6":
            names = [str(item) for item in arrays["jp3_class_names"].tolist()]
            times = arrays["jp3_t_s"]
            classes = arrays["jp3_class"].copy()
            used = arrays["jp3_used_bound_Pa"].copy()
            truth = arrays["jp3_p_tr_Pa"]
            for read in np.flatnonzero((times >= 48.7 - 1e-6) & (times <= 49.0 + 1e-6)):
                classes[read, compare.RR_LEG] = names.index("hold")
                used[read, compare.RR_LEG] = truth[read, compare.RR_LEG] + hold_gap_bar * BAR
            carry = _read_near(times, compare.CARRY_READ_S)
            classes[carry, compare.RR_LEG] = names.index(carry_class)
            used[carry, compare.RR_LEG] = truth[carry, compare.RR_LEG] + carry_gap_bar * BAR
            arrays["jp3_class"], arrays["jp3_used_bound_Pa"] = classes, used
    return edit


def test_numeric_conditions_judged_under_the_same_order(tmp_path, monkeypatch) -> None:
    code, report = _run(tmp_path, monkeypatch, None, _same_order_arrays(20.0, 12.0))
    assert code == compare.EXIT_PASS and report["status"] == "pass"
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": []}
    numeric = report["case_bd"]["D"]["numeric"]
    assert numeric["status"] == "judged" and numeric["same_order"] is True
    assert numeric["carry_read"]["class"] == "carry_ext" and numeric["hold_reads"] >= 1


def test_numeric_conditions_fail_under_the_same_order(tmp_path, monkeypatch) -> None:
    code, report = _run(tmp_path, monkeypatch, None, _same_order_arrays(10.0, 12.0))
    assert code == compare.EXIT_FAILED and report["status"] == "failed"
    assert _classes(report) == {"setting_defects": [], "not_judgeable": [], "failures": [
        "6-2A (D-다): RR 49.1 s gap below +15 bar"]}


def test_numeric_conditions_are_records_in_another_order(tmp_path, monkeypatch) -> None:
    """Not the same order (an RR acting command above u_hold): the same failing gaps are a
    record - exit and status unchanged."""
    def arrays_edit(name: str, arrays: dict) -> None:
        _same_order_arrays(10.0, 1.0)(name, arrays)
        if name == "VBG4":
            times = arrays["t_s"]
            read = int(np.flatnonzero((times >= 48.7 - 1e-6) & (times <= 49.0 + 1e-6))[0])
            commands = arrays["command_m_s"].copy()
            commands[read - 1, compare.RR_LEG] = -5.0e-4
            arrays["command_m_s"] = commands

    code, report = _run(tmp_path, monkeypatch, None, arrays_edit)
    assert code == compare.EXIT_PASS and report["status"] == "pass"
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": []}
    numeric = report["case_bd"]["D"]["numeric"]
    assert numeric["status"] == "record" and numeric["same_order"] is False
    failures = numeric["record_failures"]
    assert failures[0] == "6-2A (D-다): RR 49.1 s gap below +15 bar" and len(failures) >= 2
    assert all(text.startswith("6-2A (D-다): RR HOLD read ") for text in failures[1:])


def test_case_bd_d_numeric_requires_extension_at_49_1(tmp_path, monkeypatch) -> None:
    """Erratum 7 7-1: the window micro commands alone are not the same order - with C's RR
    49.1 s acting command at or below u_hold the failing gaps stay a record (exit 0)."""
    code, report = _run(tmp_path, monkeypatch, None,
                        _same_order_arrays(10.0, 1.0, carry_acting_m_s=0.0))
    assert code == compare.EXIT_PASS and report["status"] == "pass"
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": []}
    numeric = report["case_bd"]["D"]["numeric"]
    assert numeric["status"] == "record" and numeric["same_order"] is False
    assert "49.1 s extension False" in numeric["basis"] and numeric["record_failures"]


def test_case_bd_d_carry_ret_fails_numeric_when_same_order(tmp_path, monkeypatch) -> None:
    """Erratum 7 7-1: under the same order a 49.1 s ``carry_ret`` is no 49.1 s CARRY - a
    failure (exit 1) even with every gap met."""
    code, report = _run(tmp_path, monkeypatch, None,
                        _same_order_arrays(20.0, 12.0, carry_class="carry_ret"))
    assert code == compare.EXIT_FAILED and report["status"] == "failed"
    assert _classes(report) == {"setting_defects": [], "not_judgeable": [], "failures": [
        "6-2A (D-다): RR 49.1 s class 'carry_ret', carry_ext needed"]}
    assert report["case_bd"]["D"]["numeric"]["status"] == "judged"


def _shift_read(column: str, t_s: float, to_s: float) -> Callable[[dict], None]:
    def edit(arrays: dict) -> None:
        times = np.asarray(arrays[column], float).copy()
        times[_read_near(times, t_s)] = to_s
        arrays[column] = times
    return edit


@pytest.mark.parametrize("case, setting, reason", [
    ("VBG6 49.1 s read missing", "VBG6", "not exactly one VBG6 RR read at 49.1 s"),
    ("no HOLD read in the window", "VBG6", "no VBG6 RR HOLD read in 48.7 .. 49.0 s"),
    ("C 49.1 s read missing", "VBG4", "not exactly one C RR read at 49.1 s"),
])
def test_case_bd_d_numeric_unjudgeable_is_record(tmp_path, monkeypatch, case, setting,
                                                 reason) -> None:
    """Erratum 7 7-2: under the same order a missing VBG6 49.1 s read, zero HOLD reads in the
    window or a missing C read makes (D-다) "not computed" with its reason - status and exit
    unchanged (0), (D-가) / (D-나) still judged, and (D-다) never written as judged or pass."""
    def arrays_edit(name: str, arrays: dict) -> None:
        _same_order_arrays(10.0, 1.0)(name, arrays)  # failing gaps: must not count
        if name != setting:
            return
        if case == "VBG6 49.1 s read missing":
            _shift_read("jp3_t_s", compare.CARRY_READ_S, 49.15)(arrays)
        elif case == "no HOLD read in the window":
            names = [str(item) for item in arrays["jp3_class_names"].tolist()]
            classes = arrays["jp3_class"].copy()
            for read in compare._window_reads(arrays["jp3_t_s"]):
                classes[read, compare.RR_LEG] = names.index("ext")
            arrays["jp3_class"] = classes
        else:
            _shift_read("t_s", compare.CARRY_READ_S, 49.15)(arrays)

    code, report = _run(tmp_path, monkeypatch, None, arrays_edit)
    assert code == compare.EXIT_PASS and report["status"] == "pass", case
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": []}
    numeric = report["case_bd"]["D"]["numeric"]
    assert numeric["status"] == compare.NUMERIC_NOT_COMPUTED and numeric["reason"] == reason
    assert "failures" not in numeric and numeric["status"] not in ("judged", "pass")
    assert report["case_bd"]["D"]["covering"]["judged_reads"] == 1  # (D-나) still judged


def test_rev6_p4_2_not_computed_is_no_pass(tmp_path, monkeypatch) -> None:
    """Erratum 7 7-2: a revision 6 P4-2 that cannot be computed (a trace column missing) is
    ``not_computed`` in ``p4_records`` with its reason; status and exit unchanged."""
    def arrays_edit(name: str, arrays: dict) -> None:
        if name == "LSH4":
            del arrays["jp3_model_bound_inherited"]

    code, report = _run(tmp_path, monkeypatch, None, arrays_edit)
    assert code == compare.EXIT_PASS and report["status"] == "pass"
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": []}
    records = {record["setting"]: record for record in report["p4_records"]}
    assert records["LSH4"]["record_status"] == "not_computed"
    assert len(records["LSH4"]["findings"]["not_judgeable"]) == 1
    assert "jp3_model_bound_inherited" in records["LSH4"]["findings"]["not_judgeable"][0]
    assert all(r["record_status"] == "recorded" for s, r in records.items() if s != "LSH4")


def test_u_hold_and_the_vbg6_hold_speed_record(tmp_path, monkeypatch) -> None:
    """(D-다): u_hold = 0.01 x YAML v_max (the controller constant); another recorded
    ``hold_speed_m_s`` on the VBG6 row is a setting defect (exit 2)."""
    from outrigger_sim.control import extend_start_bound

    assert compare.HOLD_SPEED_RATIO == extend_start_bound.HOLD_SPEED_RATIO
    assert math.isclose(compare.u_hold_m_s(), 0.01 * 0.0209243016, rel_tol=1e-12)

    def edit(row: dict) -> None:
        row["lock_window_alignment"]["monitor_stretch_rule"]["hold_speed_m_s"] = 3.0e-4

    code, report = _run(tmp_path, monkeypatch, _only("VBG6", edit))
    assert code == compare.EXIT_NOT_JUDGEABLE and report["status"] == "setting_defect"
    assert _classes(report)["failures"] == [] and _classes(report)["not_judgeable"] == []
    assert len(report["setting_defects"]) == 1
    assert report["setting_defects"][0].startswith("6-2A (D-다): VBG6 hold_speed_m_s 0.0003")


# --- 6-6 (마): the not-judgeable cases of 6-2A ---------------------------------------------------

@pytest.mark.parametrize("case, counts, first, reason", [
    ("C breach 0", [0, 0, 0, 0], None,
     "6-2A (D-나): C has no moving-extension breach read (no covering row)"),
    ("C count 2", [0, 0, 0, 2], None,
     "6-2A (D-나): a C leg with 2 or more breach reads (their places are unknown; erratum 7)"),
    ("first missing", [0, 0, 0, 1], "none",
     "6-2A (D-나): C leg 3 has 1 breach read and no first_breach_t_s"),
])
def test_not_judgeable_breach_records(tmp_path, monkeypatch, case, counts, first,
                                      reason) -> None:
    def edit(row: dict) -> None:
        check = _check(row)
        check["breach_reads"] = counts
        if first == "none":
            check["first_breach_t_s"] = [None, None, None, None]

    code, report = _run(tmp_path, monkeypatch, _only("VBG4", edit))
    assert code == compare.EXIT_NOT_JUDGEABLE and report["status"] == "not_judgeable", case
    assert _classes(report) == {"failures": [], "setting_defects": [],
                                "not_judgeable": [reason]}, case


def test_not_judgeable_without_a_vbg6_read_at_the_breach_time(tmp_path, monkeypatch) -> None:
    def edit(row: dict) -> None:
        check = _check(row)
        check["first_breach_t_s"] = [None, None, None, check["first_breach_t_s"][3] + 0.05]

    code, report = _run(tmp_path, monkeypatch, _only("VBG4", edit))
    assert code == compare.EXIT_NOT_JUDGEABLE and report["status"] == "not_judgeable"
    assert len(report["not_judgeable"]) == 1 and report["failures"] == []
    assert report["not_judgeable"][0].startswith("6-2A (D-나): not exactly one VBG6 read at ")
    assert report["setting_defects"] == []


def test_a_failure_outranks_a_not_judgeable_reason(tmp_path, monkeypatch) -> None:
    """Erratum 2 2-10: a failure (B J-P3a) with a not-judgeable reason (C breach 0) is exit 1,
    and both stay in the report."""
    def edit(name: str, row: dict) -> None:
        if name == "VBH":
            _check(row)["jp3a_breach_reads"] = [1, 0, 0, 0]
        if name == "VBG4":
            _check(row)["breach_reads"] = [0, 0, 0, 0]

    code, report = _run(tmp_path, monkeypatch, edit)
    assert code == compare.EXIT_FAILED and report["status"] == "failed"
    assert report["failures"] == ["VBH: 6-2A B J-P3a jp3a_breach_reads sum 1 (0 needed)"]
    assert report["not_judgeable"] == [
        "6-2A (D-나): C has no moving-extension breach read (no covering row)"]


def test_rev6_identity_defect_is_a_setting_defect(tmp_path, monkeypatch) -> None:
    """13.6 / erratum 6 6-2: a revision 6 row of another ``spec_edition`` is a setting defect
    (exit 2) - P4-1 and the identity stay judged on revision 6 rows."""
    def edit(row: dict) -> None:
        _check(row)["spec_edition"] = "8be9de22"

    code, report = _run(tmp_path, monkeypatch, _only("LSJ1", edit))
    assert code == compare.EXIT_NOT_JUDGEABLE and report["status"] == "setting_defect"
    assert _classes(report) == {"failures": [], "not_judgeable": [],
                                "setting_defects": ["LSJ1: spec_edition '8be9de22'"]}


def test_baseline_row_without_a_new_row_is_not_judgeable(tmp_path, monkeypatch) -> None:
    """6-1: the baseline VBG5 row without its VBG6 pair (the ``ae9d0b2d`` stop) is not
    judgeable (exit 2) before any P4 item."""
    news = _world(tmp_path)
    cd = next(path for path in news if path.name == "cd.jsonl")
    kept = [line for line in cd.read_text(encoding="utf-8").splitlines()
            if json.loads(line)["job"]["setting"] != "VBG6"]
    cd.write_text("".join(line + "\n" for line in kept), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "report.json"
    code = compare.main([str(BASELINE), "--new", *map(str, news), "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert code == compare.EXIT_NOT_JUDGEABLE and report["status"] == "not_judgeable"
    assert report["not_judgeable"] == ["VBG5: 0 new rows"] and "pairs" not in report


def test_case_bd_rows_missing_is_not_judgeable() -> None:
    problems = compare.Problems()
    report = compare.case_bd_conditions([{"job": {"setting": "VBH"}}], problems)
    assert report["missing"] == ["LSH1", "LSH2", "LSH3", "LSH4", "VBG4", "VBG6"]
    assert problems.as_dict() == {"setting_defects": [], "failures": [], "not_judgeable": [
        "6-2A: rows ['LSH1', 'LSH2', 'LSH3', 'LSH4', 'VBG4', 'VBG6'] missing (B five, C and D "
        "needed)"]}
