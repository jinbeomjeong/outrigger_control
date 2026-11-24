"""436.9 edition 7 condition 3 adoption tool (``ed7_condition3_adoption.py``, spec v7 4 step 2).

Synthetic lines only: the three criteria, the open readings and their conclusion, the J7
stiffness exception reading, the strict blind / D6 record reads (a missing count is never 0),
the Q7-C4 WARN facts, the line checks, the status order and ``main`` end to end on
producer-form rows (bare T4h names, ``<stem>_t4h`` folder, run identity beside them) from
another working folder.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
for _path in (COUPLED_DIR, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import ed7_condition3_adoption as adoption  # noqa: E402
import jp3_ed7_rules as rules  # noqa: E402

ALL_PLANTS = (*adoption.VBM_PLANTS, adoption.CONTROL_PLANT)
STIFF = rules.STIFFNESS_WARNING


# ------------------------------------------------------------------------------ helpers
def _blind(shots_grew=(True, False), four_leg=0, n_rev=0, latches=0) -> dict:
    legs = {leg: {"n_rev": 0, "latches": 0, "triggers": 0} for leg in adoption.LEGS}
    legs["FL"].update(n_rev=n_rev, latches=latches)
    return {"legs": legs, "shots": [{"twist_grew": grew} for grew in shots_grew],
            "four_leg_twist_triggers": four_leg}


def _group(fails: dict[str, list[tuple[str, str]]] | None = None, *, no_reference=(),
           not_judgeable=False, lines=1) -> dict:
    items = [{"key": key, "item": item, "detail": detail, "kind": "fail", "row": key,
              "phase": 0.0} for key, pairs in (fails or {}).items() for item, detail in pairs]
    unjudged = [{"item": "J7", "kind": "not_judgeable"}] if not_judgeable else []
    group = {"lines": lines, "no_reference": [list(entry) for entry in no_reference],
             "keys_without_reference": [entry[0] for entry in no_reference],
             "r15_failed_keys": [], "fail_items": {"ed6_share": items, "ed7_new": items},
             "not_judgeable_items": {"ed6_share": unjudged, "ed7_new": unjudged}}
    group["failed_keys"] = {reading: sorted(adoption.failed_keys(group, reading, False))
                            for reading in ("ed6_share", "ed7_new")}
    return group


def _twist(grew=(True, False)) -> adoption.TwistRecord:
    return adoption.twist_record({"lsb_record": {"blind": _blind(grew)}})


def _evidence(fails_by_arm: dict[str, dict[str, dict]], grew_by_arm=None,
              **group_options) -> dict[str, adoption.ArmEvidence]:
    """``fails_by_arm[arm][plant] = {key: [(item, detail)]}``; every plant has one line."""
    evidence = {}
    for arm in adoption.COMPARED_ARMS:
        arm_evidence = adoption.ArmEvidence()
        for plant in ALL_PLANTS:
            fails = fails_by_arm.get(arm, {}).get(plant, {})
            arm_evidence.groups[plant] = _group(fails, **group_options)
            grew = (grew_by_arm or {}).get(arm, (True, False))
            arm_evidence.twist[plant] = [_twist(grew)]
        evidence[arm] = arm_evidence
    return evidence


A2_FAILS = {"Mc04": {"R12_k": [("J1", "gate end_att")]}, "M": {"S7_k": [("J3", "t_ready")]}}


# ------------------------------------------------------------------------------ twist
def test_twist_record_reads_the_blind_block_and_refuses_a_missing_count() -> None:
    record = {"lsb_record": {"blind": _blind((True, None, False), four_leg=2, n_rev=3,
                                             latches=1)}}
    twist = adoption.twist_record(record)
    assert twist == adoption.TwistRecord(shots=3, shots_known=2, shots_grew=1,
                                         four_leg_triggers=2, n_rev=3, latches=1)
    for drop in ("four_leg_twist_triggers", "shots", "legs"):
        broken = _blind()
        del broken[drop]
        assert adoption.twist_record({"lsb_record": {"blind": broken}}) is None
    broken = _blind()
    del broken["legs"]["RR"]["n_rev"]
    assert adoption.twist_record({"lsb_record": {"blind": broken}}) is None
    broken = _blind()
    del broken["shots"][0]["twist_grew"]
    assert adoption.twist_record({"lsb_record": {"blind": broken}}) is None
    assert adoption.twist_record({"lsb_record": {}}) is None


def test_twist_indicators_under_the_ratio_and_n_rev_readings() -> None:
    records = [adoption.TwistRecord(4, 3, 2, 1, 2, 0), adoption.TwistRecord(2, 2, 0, 0, 5, 1)]
    known = adoption.twist_indicators(records, "known_shots", "sum")
    assert known["twist_grew_ratio"] == pytest.approx(2 / 5)
    assert (known["four_leg_twist_triggers"], known["n_rev"], known["latches"]) == (1, 7, 1)
    every = adoption.twist_indicators(records, "all_shots", "line_max")
    assert every["twist_grew_ratio"] == pytest.approx(2 / 6) and every["n_rev"] == 5
    empty = adoption.twist_indicators([adoption.TwistRecord(0, 0, 0, 0, 0, 0)], "known_shots",
                                      "sum")
    assert empty["twist_grew_ratio"] is None


def test_is_not_worse() -> None:
    assert adoption.is_not_worse(1, 1) is True
    assert adoption.is_not_worse(0.5, 0.6) is True
    assert adoption.is_not_worse(0.7, 0.6) is False
    assert adoption.is_not_worse(None, None) is True
    assert adoption.is_not_worse(None, 0.1) is None and adoption.is_not_worse(0.1, None) is None


# ------------------------------------------------------------------------------ units
def test_stiffness_exception_is_the_single_condition() -> None:
    group = _group({"only_stiff": [("J7", f"{STIFF}:0.4")],
                    "stiff_and_other_warn": [("J7", STIFF), ("J7", "WARN_X:FL")],
                    "stiff_and_j3": [("J7", STIFF), ("J3", "t_ready")],
                    "other": [("J1", "gate end_att")]})
    group["r15_failed_keys"] = ["R15_o0.0"]
    assert adoption.failed_keys(group, "ed6_share", exempt_stiffness=False) == {
        "only_stiff", "stiff_and_other_warn", "stiff_and_j3", "other", "R15_o0.0"}
    assert adoption.failed_keys(group, "ed6_share", exempt_stiffness=True) == {
        "stiff_and_other_warn", "stiff_and_j3", "other", "R15_o0.0"}


def test_failed_units_apply_the_exception_on_the_sensitivity_plants_only() -> None:
    evidence = _evidence({"a2": {"M": {"k": [("J7", STIFF)]}, "Mslow": {"k": [("J7", STIFF)]}}})
    reading = adoption.Reading("ed6_share", "sens_exempt", "vbm5", "known_shots", "sum")
    assert adoption.failed_units(evidence["a2"], reading) == {("M", "k")}
    none = adoption.Reading("ed6_share", "none", "vbm5", "known_shots", "sum")
    assert adoption.failed_units(evidence["a2"], none) == {("M", "k"), ("Mslow", "k")}
    assert set(adoption.SENSITIVITY_PLANTS) == {"Mslow", "Mfast", "Mc005", "Mc04"}


def test_j7_ed7_items_replace_the_period_comparison() -> None:
    def metric(setting, events):
        return {"setting": setting, "row": "R12", "phase": 0.0, "group": "g",
                "events_full": events, "events_capped": False, "bad_436": []}

    fallback = "WARN_ROD_PRESSURE_FALLBACK:FL"
    v0 = metric("V0", [(10.0, fallback), (10.0, "INFO_ROD_PRESSURE_FAULT_REASON:FL:D6")])
    same_reason = metric("VB", [(10.5, fallback), (10.5, "INFO_ROD_PRESSURE_FAULT_REASON:FL:D6")])
    other_reason = metric("VB", [(10.0, fallback), (10.0, "INFO_ROD_PRESSURE_FAULT_REASON:FL:R5")])
    items = adoption._j7_ed7_items({"V0": [v0], "VB": [same_reason]})
    assert [item["kind"] for item in items] == ["record"]
    items = adoption._j7_ed7_items({"V0": [v0], "VB": [other_reason]})
    assert [item["kind"] for item in items] == ["fail"] and items[0]["row"] == "R12"


# ------------------------------------------------------------------------------ rule
def _decision(fails_by_arm, grew_by_arm=None, *, with_grid=False, **group_options) -> dict:
    return adoption.adoption(_evidence(fails_by_arm, grew_by_arm, **group_options),
                             with_grid=with_grid)


def test_the_fixed_reading_is_the_user_decision() -> None:
    assert adoption.FIXED_READING == adoption.Reading(
        j7="ed7_new", stiffness="sens_exempt", plants="vbm5", ratio="known_shots", n_rev="sum")
    assert adoption.FIXED_READING in adoption.all_readings()
    assert len(adoption.all_readings()) == 32


def test_arm_3_adopted_when_all_three_criteria_hold() -> None:
    decision = _decision({"a2": A2_FAILS, "a3": {"M": {"S7_k": [("J3", "t_ready")]}},
                          "a4": A2_FAILS}, with_grid=True)
    assert decision["status"] == "decided" and decision["conclusion"] == "a3"
    fixed = decision["fixed_reading"]
    assert fixed["outcome"] == "a3" and fixed["reading"] == adoption.FIXED_READING_VALUES
    comparison = fixed["comparisons"]["a3"]
    assert comparison["criteria"] == {"fewer_failed_units": True, "no_new_failed_units": True,
                                      "twist_not_worse": True}
    assert fixed["comparisons"]["a4"]["criteria"]["fewer_failed_units"] is False
    assert decision["interp_grid"]["outcomes"] == {"a3": 32}
    assert decision["interp_grid"]["record_only"] is True


def test_without_the_grid_flag_no_grid_is_recorded() -> None:
    decision = _decision({"a2": A2_FAILS, "a3": A2_FAILS, "a4": A2_FAILS})
    assert "interp_grid" not in decision and decision["conclusion"] == "a2"


def test_a_new_failed_unit_keeps_arm_2_even_with_fewer_failures() -> None:
    decision = _decision({"a2": A2_FAILS, "a3": {"Mfast": {"new": [("J4", "final")]}},
                          "a4": A2_FAILS})
    comparison = decision["fixed_reading"]["comparisons"]["a3"]
    assert comparison["criteria"]["fewer_failed_units"] is True
    assert comparison["new_failed_units"] == [["Mfast", "new"]]
    assert decision["status"] == "decided" and decision["conclusion"] == "a2"


@pytest.mark.parametrize("indicator, worse", [
    ("twist_grew_ratio", {"lsb_record": {"blind": _blind((True, True))}}),
    ("four_leg_twist_triggers", {"lsb_record": {"blind": _blind(four_leg=1)}}),
    ("n_rev", {"lsb_record": {"blind": _blind(n_rev=1)}}),
    ("latches", {"lsb_record": {"blind": _blind(latches=1)}}),
])
def test_a_worse_twist_indicator_keeps_arm_2(indicator, worse) -> None:
    evidence = _evidence({"a2": A2_FAILS, "a3": {}, "a4": A2_FAILS})
    evidence["a3"].twist["M"] = [adoption.twist_record(worse)]
    decision = adoption.adoption(evidence)
    comparison = decision["fixed_reading"]["comparisons"]["a3"]
    assert comparison["twist_by_indicator"][indicator] is False
    assert comparison["criteria"]["twist_not_worse"] is False
    assert decision["conclusion"] == "a2" and decision["status"] == "decided"


def test_both_candidates_qualifying_is_not_decided() -> None:
    """Spec revision 5 (control-expert) decides; until then ``undecided``."""
    decision = _decision({"a2": A2_FAILS, "a3": {}, "a4": {}})
    assert decision["fixed_reading"]["outcome"] == "both_qualify"
    assert decision["status"] == "undecided" and decision["conclusion"] is None


def test_the_grid_is_a_record_and_never_the_status() -> None:
    """A difference on the control plant L only: the fixed reading (vbm5) keeps arm 2 and
    is decided; the grid's all6 readings would adopt arm 3 (record)."""
    l_fail = {"L": {"k": [("J1", "gate end_att")]}}
    decision = _decision({"a2": l_fail, "a3": {}, "a4": l_fail}, with_grid=True)
    assert decision["status"] == "decided" and decision["conclusion"] == "a2"
    assert decision["interp_grid"]["outcomes"] == {"a2": 16, "a3": 16}
    by_plants = {result["reading"]["plants"] for result in decision["interp_grid"]["readings"]
                 if result["outcome"] == "a3"}
    assert by_plants == {"all6"}


def test_the_fixed_reading_exempts_the_stiffness_warning_only_on_sensitivity_plants() -> None:
    """J7 stiffness-only units on Mslow do not count; on M they do; a retract-not-opened
    WARN counts everywhere (Q7-C4)."""
    retract = f"{adoption.WARN_EVENT}:RL"
    a2 = {"Mslow": {"k": [("J7", STIFF)]}, "M": {"k": [("J7", STIFF)]},
          "Mc04": {"r": [("J7", retract)]}}
    a3 = {"M": {"k": [("J7", STIFF)]}, "Mc04": {"r": [("J7", retract)]}}
    fixed = _decision({"a2": a2, "a3": a3, "a4": a2})["fixed_reading"]
    assert fixed["indicators"]["a2"]["failed_unit_list"] == [["M", "k"], ["Mc04", "r"]]
    assert fixed["comparisons"]["a3"]["criteria"]["fewer_failed_units"] is False
    assert fixed["outcome"] == "a2"


@pytest.mark.parametrize("options", [{"no_reference": [("k", 0.0)]}, {"not_judgeable": True}])
def test_an_unpaired_or_unjudgeable_group_is_not_judgeable(options) -> None:
    decision = _decision({"a2": A2_FAILS}, **options)
    assert decision["fixed_reading"]["outcome"] == "not_judgeable"
    assert decision["status"] == "not_judgeable" and decision["conclusion"] is None
    assert decision["fixed_reading"]["problems"]


def test_a_line_without_its_blind_record_is_not_judgeable() -> None:
    evidence = _evidence({"a2": A2_FAILS})
    evidence["a4"].twist["Mc005"] = []
    decision = adoption.adoption(evidence)
    assert decision["status"] == "not_judgeable"
    assert any("blind record" in problem
               for problem in decision["fixed_reading"]["problems"])


def test_two_missing_ratios_compare_equal_one_missing_is_not_judgeable() -> None:
    no_shots = {arm: () for arm in adoption.COMPARED_ARMS}
    decision = _decision({"a2": A2_FAILS, "a3": {}, "a4": A2_FAILS}, no_shots)
    assert decision["conclusion"] == "a3"
    decision = _decision({"a2": A2_FAILS, "a3": {}, "a4": A2_FAILS}, {"a3": ()})
    assert decision["status"] == "not_judgeable"
    comparison = decision["fixed_reading"]["comparisons"]["a3"]
    assert comparison["criteria"]["twist_not_worse"] is None


# ------------------------------------------------------------------------------ Q7-C4
def _round(leg, opened, reversed_=False):
    return {"leg": leg, "is_opened": opened, "is_reversed": reversed_}


def test_warn_legs_from_event_names_and_events() -> None:
    record = {"event_names": {f"{adoption.WARN_EVENT}:RL": 1, "WARN_X:FL": 1},
              "events": [[3.0, f"{adoption.WARN_EVENT}:FR"]]}
    assert adoption.warn_legs(record) == ["FR", "RL"]
    assert adoption.warn_legs({}) == []


def test_warn_path_of_the_streak_that_raised_it() -> None:
    rounds = [_round("FL", False, True), _round("FR", False), _round("FL", True),
              _round("FL", False, True), _round("FL", False, True), _round("FR", False, True)]
    assert adoption.warn_path(adoption.warn_streak(rounds, "FL", 2)) == "reversed_all"
    assert adoption.warn_path(adoption.warn_streak(rounds, "FR", 2)) == "reversed_some"
    plain = [_round("RL", False), _round("RL", False)]
    assert adoption.warn_path(adoption.warn_streak(plain, "RL", 2)) == "not_reversed"
    assert adoption.warn_path(adoption.warn_streak(plain, "RR", 2)) == "streak_not_in_rounds"


def test_warn_j7_effect_categories() -> None:
    warn = f"{adoption.WARN_EVENT}:FL"
    only = _group({"k": [("J7", warn)]})
    assert adoption.warn_j7_effect(only, "k", "FL") == "warn_is_the_only_fail_item"
    both = _group({"k": [("J7", warn), ("J3", "t_ready")]})
    assert adoption.warn_j7_effect(both, "k", "FL") == "other_fail_items_too"
    other_key = _group({"x": [("J7", warn)]})
    assert adoption.warn_j7_effect(other_key, "k", "FL") == "warn_not_a_j7_fail"
    unpaired = _group(no_reference=[("k", 0.0)])
    assert adoption.warn_j7_effect(unpaired, "k", "FL") == "no_v0_reference"
    assert adoption.warn_j7_effect(None, "k", "FL") == "not_computed"


def _d6_block(rounds) -> dict:
    return {"rounds": rounds, "not_opened_streak": [0] * 4, "not_judgeable_rounds": [1, 0, 0, 2],
            "reversed_rounds": {"not_substituted": [0, 1, 0, 0], "substituted": [2, 0, 0, 0]}}


def test_d6_facts_and_a_missing_witness_count() -> None:
    planned = adoption.PlannedLine("Mslow", "a2", "R12_k", "main")
    record = {"probe_d6_record": _d6_block([_round("RL", False, True), _round("RL", False, True)]),
              "probe_d6_settings": {"not_opened_warn_rounds": 2},
              "event_names": {f"{adoption.WARN_EVENT}:RL": 1}}
    fact = adoption.d6_facts(record, planned)
    assert (fact["rounds"], fact["is_reversed_rounds"], fact["not_judgeable_rounds"]) == (2, 2, 3)
    assert (fact["reversed_not_substituted"], fact["reversed_substituted"]) == (1, 2)
    assert fact["warn_legs"] == {"RL": "reversed_all"}
    assert fact["has_witness_record"] and not fact["witness_record_incomplete"]
    broken = _d6_block([])
    del broken["not_judgeable_rounds"]
    fact = adoption.d6_facts({"probe_d6_record": broken}, planned)
    assert fact["witness_record_incomplete"] is True
    no_setting = {**record, "probe_d6_settings": {}}
    assert adoption.d6_facts(no_setting, planned)["warn_legs"] == {
        "RL": "warn_rounds_setting_missing"}
    without = adoption.d6_facts({}, planned)
    assert not without["has_witness_record"] and not without["witness_record_incomplete"]


# ------------------------------------------------------------------------------ checks
KEYS_ARMS = {"a2": ["A_i", "A_ib", "A_ii", "B3"], "a3": ["A_i", "A_ib", "A_ii", "B3"],
             "a4": ["A_i", "A_ib", "A_ii", "B3"]}
KEYS_PARAMETERS = {"a3": {"ib_condition": "level_incomplete"},
                   "a4": {"ib_condition": "attitude_clearance"}}


def _line(plant: str, arm: str, key: str, part: str = "main", **extra) -> dict:
    components = KEYS_ARMS[arm]
    return {"job": {"case": key, "eps": 0.0, "setting": f"P7-{plant}-{arm}"},
            "controller_tag": adoption.EXPECTED_TAG, "lsb_components": components,
            "lsb_record": {"components": components, "blind": _blind()},
            "lsb_settings": {"ib_condition": adoption.EXPECTED_CONDITION[arm]},
            "hydraulic_options": {"plant": plant},
            "ed7_probe": {"plant": plant, "arm": arm, "part": part,
                          "lsb_parameters": KEYS_PARAMETERS.get(arm, {}),
                          "foreign_modules": []},
            "t4h_file": f"{key}_P7-{plant}-{arm}.npz", **extra}


def _options_of(setting: str) -> dict:
    return {"plant": setting.split("-")[1]}


def test_line_problems_name_every_difference() -> None:
    planned = adoption.PlannedLine("M", "a3", "k", "main")
    keys = {"arms": KEYS_ARMS, "arm_parameters": KEYS_PARAMETERS}
    assert adoption.line_problems(_line("M", "a3", "k"), planned, keys, _options_of) == []
    bad = _line("M", "a3", "k")
    bad.update(controller_tag="other", lsb_settings={"ib_condition": "with_twist"},
               hydraulic_options={"plant": "L"})
    bad["ed7_probe"].update(foreign_modules=["x"], arm="a2")
    del bad["lsb_record"]["blind"]["shots"]
    problems = adoption.line_problems(bad, planned, keys, _options_of)
    for name in ("controller_tag", "ib_condition", "hydraulic_options",
                 "ed7_probe plant / arm / part", "another checkout", "blind block"):
        assert any(name in problem for problem in problems), name
    assert len(problems) == 6


def test_run_identity_problems() -> None:
    clean = {"git": {"head": "abc", "is_clean": True}}
    assert adoption.run_identity_problems({"start": [clean], "end": [clean]}) == []
    other = {"git": {"head": "def", "is_clean": True}}
    assert adoption.run_identity_problems({"start": [clean], "end": [other]})
    dirty = {"git": {"head": "abc", "is_clean": False}}
    assert adoption.run_identity_problems({"start": [clean], "end": [dirty]}) == [
        "run identity not clean"]
    assert adoption.run_identity_problems(None) == ["no run identity file"]
    assert adoption.run_identity_problems({})


def test_status_order() -> None:
    empty = {name: [] for name in (*adoption.DEFECT_CHECKS, *adoption.INCOMPLETE_CHECKS)}
    decided = {"status": "decided"}
    assert adoption.status_of(empty, decided) == "decided"
    assert adoption.status_of(empty, {"status": "undecided"}) == "undecided"
    assert adoption.status_of({**empty, "missing_jobs": ["x"]}, decided) == "incomplete"
    for name in adoption.DEFECT_CHECKS:
        both = {**empty, "missing_jobs": ["x"], name: ["y"]}
        assert adoption.status_of(both, decided) == "setting_defect", name


# ------------------------------------------------------------------------------ main
def _fake_line_metric(record: dict, t4h_dir: Path) -> dict:
    assert (t4h_dir / record["t4h_file"]).is_file()  # the producer folder, not the CWD
    return {"fails": record.get("test_fails", []), "part": record["ed7_probe"]["part"]}


def _fake_group_judgement(metrics_by_key: dict, v0_rows: list) -> dict:
    fails = {key: metric["fails"] for key, metric in metrics_by_key.items()}
    unpaired = [(key, 0.0) for key, metric in metrics_by_key.items() if metric["part"] == "d"]
    group = _group(fails, no_reference=unpaired, lines=len(metrics_by_key))
    return group


def _write_run(folder: Path, lines: list[dict], keys_lines: list[dict]) -> tuple[Path, Path]:
    t4h = folder / "ed7_probe_t4h"
    t4h.mkdir(parents=True)
    for line in lines:
        (t4h / line["t4h_file"]).write_bytes(b"npz")
    rows = folder / "ed7_probe.jsonl"
    rows.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    git = {"git": {"head": "6bfb2560", "is_clean": True}}
    (folder / "ed7_probe.identity.json").write_text(json.dumps({"start": [git], "end": [git]}),
                                                    encoding="utf-8")
    keys = folder / "probe_keys_ed7.json"
    keys.write_text(json.dumps({"lines": keys_lines, "expected_lines": len(keys_lines),
                                "arms": KEYS_ARMS, "arm_parameters": KEYS_PARAMETERS}),
                    encoding="utf-8")
    return rows, keys


def _producer_run(tmp_path: Path, monkeypatch, drop_last: bool = False) -> tuple[Path, Path]:
    monkeypatch.setattr(adoption, "line_metric", _fake_line_metric)
    monkeypatch.setattr(adoption, "group_judgement", _fake_group_judgement)
    monkeypatch.setattr(adoption, "v0_metric_rows", lambda path, sha: [])
    monkeypatch.setattr(adoption, "expected_options", _options_of)
    lines = []
    for plant in ALL_PLANTS:
        for arm in adoption.COMPARED_ARMS:
            fails = [["J1", "gate end_att"]] if (plant, arm) == ("Mc04", "a2") else []
            fails = [["J1", "gate end_att"]] if (plant, arm) == ("Mc04", "a4") else fails
            lines.append(_line(plant, arm, "R12_k", test_fails=fails))
    warn = _line("M", "a2", "R12_d", part="d",
                 event_names={f"{adoption.WARN_EVENT}:RL": 1},
                 probe_d6_settings={"not_opened_warn_rounds": 2},
                 probe_d6_record=_d6_block([_round("RL", False, True),
                                            _round("RL", False, True)]))
    lines.append(warn)
    keys_lines = [{"job": line["job"], "key": line["job"]["case"],
                   "part": line["ed7_probe"]["part"]} for line in lines]
    rows, keys = _write_run(tmp_path / "run", lines[:-2] + lines[-1:] if drop_last else lines,
                            keys_lines)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    return rows, keys


def _main(rows: Path, keys: Path, out: Path, *extra: str) -> int:
    return adoption.main(["--rows", str(rows), "--keys", str(keys), "--v0", str(rows),
                          "--v0-sha256", "x", "--out", str(out), *extra])


def test_main_on_producer_rows_from_another_folder(tmp_path, monkeypatch, capsys) -> None:
    rows, keys = _producer_run(tmp_path, monkeypatch)
    out = tmp_path / "adoption.json"
    code = _main(rows, keys, out, "--keys-sha256", adoption.file_sha256(keys))
    report = json.loads(out.read_text(encoding="utf-8"))
    assert code == adoption.EXIT_DECIDED and report["status"] == "decided"
    assert report["decision"]["conclusion"] == "a3"
    assert report["decision"]["fixed_reading"]["outcome"] == "a3"
    assert "interp_grid" not in report["decision"]
    assert all(not value for value in report["checks"].values()), report["checks"]
    q7c4 = report["q7c4"]
    assert q7c4["totals"]["lines"] == 19 and q7c4["totals"]["warn_lines"] == 1
    assert q7c4["warn_paths"] == {"reversed_all": 1}
    assert q7c4["warn_j7_effects"] == {"no_v0_reference": 1}
    last = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert last["status"] == "decided" and last["probe_lines"] == 19
    assert "conclusion" not in last and last["grid_readings"] is None


def test_main_with_the_interp_grid_records_it(tmp_path, monkeypatch) -> None:
    rows, keys = _producer_run(tmp_path, monkeypatch)
    out = tmp_path / "adoption.json"
    assert _main(rows, keys, out, "--interp-grid") == adoption.EXIT_DECIDED
    decision = json.loads(out.read_text(encoding="utf-8"))["decision"]
    assert decision["conclusion"] == "a3" and len(decision["interp_grid"]["readings"]) == 32


def test_main_missing_job_is_incomplete(tmp_path, monkeypatch) -> None:
    rows, keys = _producer_run(tmp_path, monkeypatch, drop_last=True)
    out = tmp_path / "adoption.json"
    assert _main(rows, keys, out) == adoption.EXIT_STOP
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["status"] == "incomplete" and len(report["checks"]["missing_jobs"]) == 1


def test_main_refuses_an_existing_out_and_another_keys_sha(tmp_path, monkeypatch, capsys) -> None:
    rows, keys = _producer_run(tmp_path, monkeypatch)
    out = tmp_path / "adoption.json"
    out.write_text("kept", encoding="utf-8")
    assert _main(rows, keys, out) == adoption.EXIT_STOP
    assert out.read_text(encoding="utf-8") == "kept"
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["status"] == "input_error"
    other = tmp_path / "other.json"
    assert _main(rows, keys, other, "--keys-sha256", "0" * 64) == adoption.EXIT_STOP
    assert not other.exists()


def test_main_unexpected_failure_is_a_tool_error(tmp_path, monkeypatch, capsys) -> None:
    rows, keys = _producer_run(tmp_path, monkeypatch)

    def broken(record, t4h_dir):
        raise KeyError("values")

    monkeypatch.setattr(adoption, "line_metric", broken)
    out = tmp_path / "adoption.json"
    assert _main(rows, keys, out) == adoption.EXIT_TOOL and not out.exists()
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["status"] == "tool_error"
