"""Stable-READY comparison of ``stable_ready_compare.py`` (control spec 429.8, ZIC Z-1 .. Z-4).

Synthetic records cover the stable-READY rule (last READY entry kept to the end), the fallback
for records without phase events, the four criteria and the kept fail -> pass rows. Two stored
cases of the stage 1 regression (spec 429.8) pin the correction: x426b
``H3|J1|B|middle|roll_pos@k0.75`` (first-READY delay +19 s) and slope
``H3|J2|A|top|roll_pos@k0.75`` (end attitude +0.05 deg) are ``incomparable`` because "current"
ends in a re-level / probe. Their record values are copied from ``rev85/p37c_x426b.json`` and
``rev85/p37c_harness_cmp.json``; the phase transitions from the control-expert traces
(``ctrl-zic/tr_x426b.json``, ``tr_z3.json``).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "04_scripts" / "03_control" / "s9"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import stable_ready_compare as src  # noqa: E402

COMBINATION = "P36sa+P37t+R4c30+P38z"
X426B_ID = "H3|J1|B|middle|roll_pos@k0.75"
Z3_ID = "H3|J2|A|top|roll_pos@k0.75"


def make_record(
    case_id: str = "H3|J1|B|top|flat",
    candidate: str = "current",
    *,
    suite: str = "slope",
    passed: bool = True,
    verdict: str | None = None,
    hash_value: str = "h0",
    t_ready_s: float | None = 50.0,
    final_phase: str = "ready",
    att_end_deg: tuple[float, float] = (0.01, -0.01),
    clamp_count: int = 0,
    flat_margins: tuple = (),
    t_first_done_s: float | None = 40.0,
    phase_events: list | None = None,
    stable_ready_att_mean_deg: tuple[float, float] | None = None,
    guard_stop: bool = False,
) -> dict:
    """Wrapper record with the fields the comparison reads."""
    metrics = {
        "t_first_done_s": t_first_done_s,
        "p36s": {"stop": {"t_s": 40.0} if guard_stop else None},
        "p37": None if not flat_margins else {"applied": [], "flat_margins": list(flat_margins)},
        "p38": {"clamp_count": clamp_count, "clamps": []} if candidate != "current" else None,
        "fix_events": [],
    }
    record = {
        "suite": suite,
        "id": case_id,
        "candidate": candidate,
        "verdict": verdict or ("pass" if passed else "fail"),
        "passed": passed,
        "hash": hash_value,
        "t_ready_s": t_ready_s,
        "final_phase": final_phase,
        "att_end_deg": list(att_end_deg),
        "metrics": metrics,
    }
    if phase_events is not None:
        record["phase_events"] = phase_events
    if stable_ready_att_mean_deg is not None:
        record["stable_ready_att_mean_deg"] = list(stable_ready_att_mean_deg)
    return record


def compare(before: dict, after: dict, focus_part: str = "P38z") -> dict:
    return src.compare_outcomes(src.wrapper_outcome(before), src.wrapper_outcome(after), focus_part)


def summary_of(pairs: list[tuple[dict, dict]], kept_ids: tuple[str, ...] = ()) -> dict:
    rows = [compare(before, after) for before, after in pairs]
    return src.summarize_candidate(rows, kept_ids)


# -------------------------------------------------------------------- stable READY rule
def test_stable_ready_is_last_transition_into_ready():
    events = [[19.9, "level"], [47.0, "done"], [59.0, "ready"], [59.6, "level"], [78.0, "ready"]]
    assert src.stable_ready_from_phase_events(events) == 78.0


def test_no_stable_ready_when_run_ends_outside_ready():
    events = [[47.0, "done"], [59.0, "ready"], [59.6, "level"]]
    assert src.stable_ready_from_phase_events(events) is None
    assert src.stable_ready_from_phase_events([]) is None


def test_fallback_uses_first_ready_only_when_run_ends_in_ready():
    assert src.stable_ready("ready", 61.0, None) == (61.0, src.BASIS_FIRST_READY)
    assert src.stable_ready("probe", 61.0, None) == (None, src.BASIS_NO_STABLE_READY)
    assert src.stable_ready("ready", None, None) == (None, src.BASIS_NO_STABLE_READY)


def test_phase_events_override_first_ready():
    record = make_record(
        t_ready_s=59.0,
        phase_events=[[59.0, "ready"], [59.6, "level"], [66.0, "done"], [78.0, "ready"]],
    )
    outcome = src.wrapper_outcome(record)
    assert outcome.t_stable_ready_s == 78.0
    assert outcome.ready_basis == src.BASIS_PHASE_EVENTS


def test_ready_mean_preferred_over_end_instant():
    record = make_record(att_end_deg=(0.08, 0.0), stable_ready_att_mean_deg=(0.02, -0.01))
    outcome = src.wrapper_outcome(record)
    assert outcome.end_attitude_deg == (0.02, -0.01)
    assert outcome.attitude_basis == src.ATTITUDE_BASIS_MEAN


# ----------------------------------------------------------------------------- criteria
def test_delay_measured_between_stable_ready_entries():
    before = make_record(phase_events=[[59.0, "ready"], [59.6, "level"], [80.0, "ready"]])
    after = make_record(
        candidate=COMBINATION,
        hash_value="h1",
        clamp_count=1,
        t_ready_s=78.0,
        phase_events=[[78.0, "ready"]],
    )
    row = compare(before, after)
    assert row["d_first_ready_s"] == pytest.approx(28.0)
    assert row["d_stable_ready_s"] == pytest.approx(-2.0)


def test_z1_idle_run_must_keep_hash():
    before = make_record(hash_value="h0")
    same = make_record(candidate=COMBINATION, hash_value="h0")
    differs = make_record("H3|J1|B|top|other", COMBINATION, hash_value="hX")
    differs_before = make_record("H3|J1|B|top|other", hash_value="h0")
    result = summary_of([(before, same), (differs_before, differs)])
    assert result["criteria"]["Z-1"]["pass"] is False
    assert result["criteria"]["Z-1"]["idle_hash_differs"] == ["slope|H3|J1|B|top|other"]


def test_z2_counts_pass_to_fail_and_new_fault_but_not_safe_stop():
    before = make_record()
    to_fail = make_record(
        candidate=COMBINATION, passed=False, final_phase="fault", hash_value="h1", clamp_count=1
    )
    result = summary_of([(before, to_fail)])
    assert result["criteria"]["Z-2"]["pass_to_fail"] == ["slope|H3|J1|B|top|flat"]
    assert result["criteria"]["Z-2"]["new_fault"] == ["slope|H3|J1|B|top|flat"]

    to_stop = make_record(
        candidate=COMBINATION,
        passed=False,
        verdict="stroke_limited_stop",
        final_phase="fault",  # a guard stop ends in a FAULT phase by design
        hash_value="h1",
        guard_stop=True,
    )
    result = summary_of([(before, to_stop)])
    assert result["criteria"]["Z-2"]["pass"] is True
    assert result["criteria"]["Z-2"]["new_fault"] == []
    assert result["criteria"]["Z-2"]["new_fault_guard_stop"] == ["slope|H3|J1|B|top|flat"]
    assert result["criteria"]["Z-2"]["pass_to_safe_stop"] == ["slope|H3|J1|B|top|flat"]


def test_z2_guard_stop_fault_after_failing_baseline_is_not_new_fault():
    before = make_record(passed=False, verdict="settle_check_fail", final_phase="level")
    stopped = make_record(
        candidate=COMBINATION,
        passed=False,
        verdict="settle_check_fail",
        final_phase="fault",
        hash_value="h1",
        guard_stop=True,
    )
    z2 = summary_of([(before, stopped)])["criteria"]["Z-2"]
    assert z2["pass"] is True
    assert z2["new_fault_guard_stop"] == ["slope|H3|J1|B|top|flat"]


def test_z3_limit_on_stable_ready_mean():
    before = make_record(stable_ready_att_mean_deg=(0.010, 0.0))
    within = make_record(
        candidate=COMBINATION,
        hash_value="h1",
        clamp_count=1,
        stable_ready_att_mean_deg=(0.030, 0.0),
        att_end_deg=(0.2, 0.0),
    )
    assert summary_of([(before, within)])["criteria"]["Z-3"]["pass"] is True
    over = make_record(
        candidate=COMBINATION,
        hash_value="h1",
        clamp_count=1,
        stable_ready_att_mean_deg=(0.0, -0.031),
    )
    z3 = summary_of([(before, over)])["criteria"]["Z-3"]
    assert z3["pass"] is False
    assert z3["max_increase_deg"] == pytest.approx(0.021)


def test_z4_row_limit_and_median():
    before = make_record(t_ready_s=50.0)
    slow = make_record(candidate=COMBINATION, hash_value="h1", clamp_count=1, t_ready_s=55.5)
    z4 = summary_of([(before, slow)])["criteria"]["Z-4"]
    assert z4["pass"] is False
    assert len(z4["over_limit"]) == 1

    slightly_late = make_record(
        candidate=COMBINATION, hash_value="h1", clamp_count=1, t_ready_s=51.0
    )
    z4 = summary_of([(before, slightly_late)])["criteria"]["Z-4"]
    assert z4["over_limit"] == []
    assert z4["median_s"] == pytest.approx(1.0)
    assert z4["pass"] is False  # median > 0


def test_z3_z4_judge_focus_part_rows_only():
    before = make_record(t_ready_s=50.0)
    other_part = make_record(
        candidate=COMBINATION,
        hash_value="h1",
        flat_margins=(1,),
        t_ready_s=70.0,
        att_end_deg=(0.15, 0.0),
    )
    result = summary_of([(before, other_part)])
    assert result["other_acted"] == 1
    assert result["criteria"]["Z-3"]["n"] == 0
    assert result["criteria"]["Z-4"]["pass"] is True


def test_focus_only_record_splits_combined_rows():
    before = make_record(t_ready_s=50.0)
    combined = make_record(
        candidate=COMBINATION, hash_value="h1", clamp_count=1, flat_margins=(1,), t_ready_s=60.0
    )
    alone = make_record(
        "H3|J1|B|top|other", COMBINATION, hash_value="h2", clamp_count=1, t_ready_s=50.5
    )
    alone_before = make_record("H3|J1|B|top|other", t_ready_s=50.0)
    result = summary_of([(before, combined), (alone_before, alone)])
    assert result["criteria"]["Z-4"]["pass"] is False  # the R4c+P38z row is +10 s
    assert result["focus_only"]["Z-4"]["n"] == 1
    assert result["focus_only"]["Z-4"]["max_s"] == pytest.approx(0.5)


def test_incomparable_row_kept_with_first_done_and_end_phase():
    before = make_record(final_phase="probe", t_first_done_s=47.0)
    after = make_record(
        candidate=COMBINATION, hash_value="h1", clamp_count=1, t_ready_s=78.0, t_first_done_s=47.0
    )
    row = compare(before, after)
    assert row["comparable"] is False
    assert row["d_stable_ready_s"] is None and row["d_att_abs_deg"] is None
    assert (row["t_first_done_before_s"], row["t_first_done_after_s"]) == (47.0, 47.0)
    assert (row["final_phase_before"], row["final_phase_after"]) == ("probe", "ready")
    result = src.summarize_candidate([row], ())
    assert result["focus_incomparable"] == [f"slope|{row['id']} (probe/ready)"]
    assert result["criteria"]["Z-4"]["n"] == 0


@pytest.mark.parametrize(
    ("after_passed", "expected_status", "expected_pass"),
    [(True, "kept", True), (False, "lost", False)],
)
def test_kept_fail_to_pass(after_passed, expected_status, expected_pass):
    case_id = "H6|J2|B|top|flat|m1.1"
    before = make_record(case_id, suite="h6", passed=False)
    after = make_record(
        case_id, COMBINATION, suite="h6", passed=after_passed, hash_value="h1", clamp_count=1
    )
    kept = summary_of([(before, after)], (case_id,))["criteria"]["kept_fail_to_pass"]
    assert kept["rows"][case_id] == expected_status
    assert kept["pass"] is expected_pass


def test_kept_fail_to_pass_missing_row_is_incomplete():
    result = summary_of([(make_record(), make_record(candidate=COMBINATION))], ("H6|absent",))
    assert result["criteria"]["kept_fail_to_pass"]["pass"] is None
    assert result["verdict"] == "incomplete"


# ------------------------------------------------------------ stored cases of spec 429.8
def x426b_records() -> tuple[dict, dict]:
    """Stored x426b records (p37c_x426b.json): "current" ends in PROBE after a quick re-level."""
    before = make_record(
        X426B_ID,
        suite="x426b",
        hash_value="cde4ae5a7ac82a142042dae3172d8db1e649429342ebd0807441ebf1069e2253",
        t_ready_s=59.0,
        final_phase="probe",
        att_end_deg=(0.037644, -0.005429),
        t_first_done_s=47.0,
    )
    after = make_record(
        X426B_ID,
        COMBINATION,
        suite="x426b",
        hash_value="37eb080def18f77725ecc97411ff742922f15c6e82e5e07cb62ad228a3cf121c",
        t_ready_s=78.0,
        final_phase="ready",
        att_end_deg=(-0.023351, -0.018957),
        clamp_count=2,
        t_first_done_s=47.0,
    )
    return before, after


def z3_records() -> tuple[dict, dict]:
    """Stored slope records (p37c_harness_cmp.json): "current" ends in a re-level."""
    before = make_record(
        Z3_ID,
        hash_value="77fe699be4fe1567263c31134cd14907e43fe376064230611e375134930a7650",
        t_ready_s=73.9,
        final_phase="level",
        att_end_deg=(0.012356, -0.014111),
        t_first_done_s=61.9,
    )
    after = make_record(
        Z3_ID,
        COMBINATION,
        hash_value="9ce9b65e7712423dbfc3b9670dcbf4233d3bf7adb85fd972efddfc2372cd56bd",
        t_ready_s=72.0,
        final_phase="ready",
        att_end_deg=(-0.063756, 0.037245),
        clamp_count=1,
        t_first_done_s=60.0,
    )
    return before, after


X426B_PHASES = {  # control-expert trace tr_x426b.json (current, P38z1 = same order as P38z)
    "current": [
        [19.9, "level"],
        [47.0, "done"],
        [47.1, "probe"],
        [59.0, "ready"],
        [59.6, "level"],
        [65.8, "done"],
        [65.9, "probe"],
    ],
    "candidate": [
        [19.9, "level"],
        [47.0, "done"],
        [47.1, "probe"],
        [58.8, "level"],
        [66.0, "done"],
        [66.1, "probe"],
        [78.0, "ready"],
    ],
}
Z3_PHASES = {  # control-expert trace tr_z3.json
    "current": [[19.8, "level"], [61.9, "done"], [62.0, "probe"], [73.9, "ready"], [75.3, "level"]],
    "candidate": [[19.8, "level"], [60.0, "done"], [60.1, "probe"], [72.0, "ready"]],
}


@pytest.mark.parametrize("records", [x426b_records, z3_records], ids=["x426b", "z3"])
def test_stored_cases_are_incomparable(records):
    before, after = records()
    row = compare(before, after)
    assert row["status"] == src.STATUS_FOCUS
    assert row["comparable"] is False
    result = src.summarize_candidate([row], ())
    assert result["criteria"]["Z-3"]["pass"] is True
    assert result["criteria"]["Z-4"]["pass"] is True
    assert result["focus_incomparable"]


def test_stored_cases_were_violations_under_first_ready_rule():
    """The 429.7 numbers the correction removes: +19.0 s first READY, +0.05 deg end attitude."""
    x426b_row = compare(*x426b_records())
    assert x426b_row["d_first_ready_s"] == pytest.approx(19.0)
    before, after = z3_records()
    old_increase = max(map(abs, after["att_end_deg"])) - max(map(abs, before["att_end_deg"]))
    assert old_increase == pytest.approx(0.0496, abs=1e-4)


@pytest.mark.parametrize(
    ("records", "phases", "after_stable_s"),
    [(x426b_records, X426B_PHASES, 78.0), (z3_records, Z3_PHASES, 72.0)],
    ids=["x426b", "z3"],
)
def test_stored_cases_with_traced_phase_events(records, phases, after_stable_s):
    before, after = records()
    before["phase_events"] = phases["current"]
    after["phase_events"] = phases["candidate"]
    row = compare(before, after)
    assert row["t_stable_ready_before_s"] is None
    assert row["t_stable_ready_after_s"] == after_stable_s
    assert row["comparable"] is False
    assert row["ready_basis"] == f"{src.BASIS_NO_STABLE_READY}/{src.BASIS_PHASE_EVENTS}"


# --------------------------------------------------------------- files, screens, outputs
def screen_payload(candidate: str, *, final_phase: str, hash_value: str, acted: bool) -> dict:
    run = {
        "timing": "ready",
        "event": "G4",
        "pass": True,
        "final_phase": final_phase,
        "t_ready_back_s": 33.9,
        "att_end_deg": [0.02, -0.01],
        "commands_sha256": hash_value,
        "prefix_commands_sha256": "prefix",
        "candidate_record": {"acted": acted, "acted_parts": ["P38z"] if acted else []},
    }
    return {
        "meta": {},
        "results": [{"key": "A|G1|FL|Fs0|two", "candidate": candidate, "runs": [run]}],
    }


def write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_build_comparison_end_to_end(tmp_path):
    x426b_before, x426b_after = x426b_records()
    idle_before = make_record("H5|rigid|B|top|flat", hash_value="same")
    idle_after = make_record("H5|rigid|B|top|flat", COMBINATION, hash_value="same")
    combined = write_json(
        tmp_path / "cmp.json", {"records": [x426b_before, x426b_after, idle_before, idle_after]}
    )
    screen_current = write_json(
        tmp_path / "screen_A_current.json",
        screen_payload("current", final_phase="ready", hash_value="b", acted=False),
    )
    screen_candidate = write_json(
        tmp_path / "cand_A.json",
        screen_payload(COMBINATION, final_phase="ready", hash_value="c", acted=True),
    )

    result = src.build_comparison([combined], [combined], [(screen_current, screen_candidate)])

    assert result["meta"]["no_baseline"] == []
    rows = {(row["suite"], row["id"]): row for row in result["rows"]}
    assert rows[("x426b", X426B_ID)]["comparable"] is False
    assert rows[("slope", "H5|rigid|B|top|flat")]["status"] == src.STATUS_IDLE
    screen_row = rows[("screen:cand_A", "A|G1|FL|Fs0|two|ready|G4")]
    assert screen_row["comparable"] is True
    assert screen_row["d_stable_ready_s"] == pytest.approx(0.0)
    summary = result["summary"][COMBINATION]
    assert summary["criteria"]["Z-1"]["pass"] is True
    assert summary["focus_acted"] == 2 and summary["focus_comparable"] == 1

    out_path = tmp_path / "out" / "compare.json"
    src.write_outputs(out_path, result)
    assert json.loads(out_path.read_text(encoding="utf-8"))["summary"]
    assert (tmp_path / "out" / "compare_rows.csv").read_text(encoding="utf-8").startswith("suite,")


def test_missing_baseline_is_listed(tmp_path):
    lonely = write_json(tmp_path / "cand.json", {"records": [make_record(candidate=COMBINATION)]})
    result = src.build_comparison([lonely], [], [])
    assert result["rows"] == []
    assert result["meta"]["no_baseline"] == [f"{COMBINATION}:slope|H3|J1|B|top|flat"]
