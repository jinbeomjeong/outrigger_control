"""Tests of ``las_revA_targeted.py`` (candidates, jobs, gates) and ``las_revA_judge.py`` for
the revA addendum rev2 (P5r4 only, G-2', R-0A, R-Q).

The judge is checked on hand-made lines (no simulation): status order, the empty candidate,
H-6', H-11', H-12, H-13, the K-A checks, G-2' at its floor, the R-Q clusters and Q-1 .. Q-5,
foreign (P5r6) lines and the bit tests. ``las_phase_diag`` gets its half / quarter steps and
the ramp period values checked here too.
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "03_src"))

import las_phase_diag  # noqa: E402
import las_rev_judge as rj  # noqa: E402
import las_revA_judge as judge  # noqa: E402
import las_revA_targeted as reva  # noqa: E402
import pytest  # noqa: E402

from outrigger_sim.control import c2  # noqa: E402

LAMBDA_0 = 0.25
T_END_S = 23.0
T_LIFT_S = 23.05
REACCEL_OUTPUT_S = T_END_S + 0.1
P5_KN = 11.0
P5R4_KN = 12.0
LOW_KN, HIGH_KN = 12.5, 14.9
FIRST_GAP_S, AFTER_GAP_S = -0.02, 0.1


# ------------------------------------------------------------------------------- line builders
def _identity(head="c0"):
    return {"git_head": head, "code_diff_sha256": rj.EMPTY_SHA256,
            "dirty_files": [".gitattributes"], "sha256": {"c2.py": "1"}}


def _ramp(n_r, applied=None, end="done", start=LAMBDA_0):
    if n_r == 0:
        return reva.no_ramp(0)
    applied = n_r if applied is None else applied
    return {"n_r": n_r, "start_factor": start, "periods_applied": applied,
            "scaled_periods": applied, "end_t_s": T_END_S + 0.1 * (applied - 1),
            "end_reason": end}


def _periods(ramp: dict) -> list[dict]:
    """An acted period, then the end period and the ramp periods (m = 1 .. applied)."""
    acted = {"active_after": True, "is_scaled": True, "input_mm_s": [20.0] * 4,
             "output_mm_s": [20.0 * LAMBDA_0] * 4}
    periods = [{"t_s": 22.9, "cmd_mm_s": [5.0] * 4, "las": acted}]
    applied = ramp["periods_applied"]
    if not applied:
        return periods + [{"t_s": T_END_S, "cmd_mm_s": [20.0] * 4,
                           "las": {"active_after": False}}]
    for m in range(1, applied + 1):
        periods.append({"t_s": T_END_S + 0.1 * (m - 1), "cmd_mm_s": [6.0] * 4,
                        "las": {"active_after": False, "ramp_m": m, "ramp_scaled": True}})
    return periods


def _line(bundle, candidate, point, f_rl=P5_KN, sha=None, end_reason="sum", start=21.0,
          ramp=None, label=None, gap_s=0.3):
    """A grid line whose LAS-b, periods and force window are those of the P5 pair."""
    beta, n_min, n_r = judge.CANDIDATE_VALUES.get(candidate, (4.5, 0, 6))
    setting, centre, j = point
    settings = {"light_leg_fraction_of_F_min": beta, "min_active_periods": n_min,
                "end_ramp_periods": n_r}
    tag = rj.CONTROLLER_TAG_BY_SETTING[setting]
    sha = sha or hashlib.sha256(f"{candidate}{point}".encode()).hexdigest()
    ramp = ramp if ramp is not None else _ramp(n_r)
    las = {"start_t_s": start, "end_t_s": T_END_S, "end_reason": end_reason,
           "active_periods": 9, "scaled_periods": 9, "start_leg": 2,
           "params": {"beta": beta, "n_min": n_min, "n_r": n_r}, "ramp": ramp}
    rows = [[T_END_S + 0.001 * k, 1.0, 2.0] for k in range(-50, 150)]
    rules = dict(zip(judge.RULES_FIELDS, judge.RULES_VALUES, strict=True))
    return {"job": {"setting": setting, "d1": {}}, "commands_sha256": sha,
            "controller_tag": tag, "las": las,
            "rev": {"bundle": bundle, "candidate": candidate,
                    "label": label or f"{candidate}-{bundle}-{point}", "key": f"k{setting}",
                    "grid_point": [centre, j], "settings": settings, "settings_match": True,
                    **rules, "controller_tag": tag, "identity": _identity()},
            "diag": {"summary": {"F_RL_kN": f_rl, "F_judged_min_kN": f_rl,
                                 "gate_consistent": True, "t_lift_s": T_LIFT_S,
                                 "t_RL_min_s": REACCEL_OUTPUT_S + gap_s},
                     "touch_budget": {"level_budget_periods": 0}, "periods": _periods(ramp),
                     "force_window": {"rows": rows}}}


def _cand_rows(line):
    """Candidate rows equal to P5 before t_e + 0.1 s, different after (the ramp)."""
    line["diag"]["force_window"]["rows"] = [
        row if row[0] < REACCEL_OUTPUT_S else [row[0], 9.0, 9.0]
        for row in line["diag"]["force_window"]["rows"]]
    return line


def _points(steps):
    return sorted(judge.expected_points(steps), key=str)


def reference(f_rl=P5_KN):
    return {point: _line("R-G", "P5", point, f_rl, label="P5-LT") for point in
            _points(judge.GRID_STEPS)}


def half_p5(f_rl=P5_KN):
    return {point: _line("R-H", "P5", point, f_rl, label="P5-LH") for point in
            _points(judge.HALF_STEPS)}


def r0a_lines(f_rl=P5R4_KN):
    return [_cand_rows(_line("R-0A", "P5r4", point, f_rl))
            for point in _points(judge.GRID_STEPS) + _points(judge.HALF_STEPS)]


def stored_reva(lines=None):
    """The stored P5r4 54 lines (the hash reference) and the R-H P5 pairs."""
    p5r4 = {judge.grid_point_of(line): line for line in (lines or r0a_lines())}
    return judge.StoredRevA(p5r4, half_p5())


def quarter_value(point) -> tuple[float, float]:
    """(F_RL, gap): VB 1 / VB 0.94 the Q-1 values, the other cells low / high alternately."""
    setting, centre, j = point
    if (setting, centre) == ("VB", "1"):
        return 14.15, -0.08
    if (setting, centre) == ("VB", "0.94"):
        return 14.62, 0.44
    is_low = judge.QUARTER_STEPS.index(j) % 2 == 0
    return (LOW_KN, FIRST_GAP_S) if is_low else (HIGH_KN, AFTER_GAP_S)


def quarter_lines(override=None):
    out = []
    for point in _points(judge.QUARTER_STEPS):
        f_rl, gap = (override or {}).get(point, quarter_value(point))
        out.append(_line("R-Q", "P5r4", point, f_rl, gap_s=gap))
    return out


def r0_lines():
    lines = []
    for (key, label), sha in rj.R0_EXPECTED.items():
        setting = "V0" if "|V0|" in key else "VB"
        line = _line("R-0", "P0", (setting, "1", 0), sha=sha, label=label)
        line["rev"]["key"] = key
        lines.append(line)
    return lines


def r0p5_lines(ref):
    out = []
    for ref_line in ref.values():
        line = json.loads(json.dumps(ref_line))
        line["rev"]["bundle"] = "R-0P5"
        out.append(line)
    return out


def full_lines(ref, r0a=None, rq=None):
    return r0_lines() + r0p5_lines(ref) + (r0a or r0a_lines()) + (rq or quarter_lines())


def _copy(lines):
    return json.loads(json.dumps(lines))


# ------------------------------------------------------------------------------- runner pieces
def test_candidates_and_labels():
    preset = reva.rev.preset_las_settings()
    assert reva.CANDIDATES["P0"].settings_from(preset) is preset
    assert "P5r6" not in reva.CANDIDATES and judge.JUDGED_CANDIDATES == ("P5r4",)
    p5r4 = reva.CANDIDATES["P5r4"].settings_from(preset)
    assert (p5r4.light_leg_fraction_of_F_min, p5r4.min_active_periods,
            p5r4.end_ramp_periods) == (4.5, 0, 4)
    assert replace(p5r4, light_leg_fraction_of_F_min=3.5, end_ramp_periods=0) == preset
    assert reva.grid_label("P5r4", "nom", 1.5, "LH") == "P5r4-LH-cnom-j1p5"
    assert reva.grid_label("P5r4", "0.94", 0.25, "LQ") == "P5r4-LQ-c0.94-j0p25"
    assert reva.grid_label("P5", "0.94", 0, "LT") == "P5-LT-c0.94-j0"


def test_bundle_counts_and_grid_points():
    assert len(reva.bundle_jobs("R-0", ("P0",))) == 6
    assert len(reva.bundle_jobs("R-0P5", ("P5",))) == 30
    r0a = reva.bundle_jobs("R-0A", ("P5r4",))
    assert len(r0a) == 54
    assert {job["rev"]["grid_point"][1] for job in r0a} == {*judge.GRID_STEPS,
                                                            *judge.HALF_STEPS}
    assert sum("-LH-" in job["rev"]["label"] for job in r0a) == 24
    quarter = reva.bundle_jobs("R-Q", ("P5r4",))
    assert len(quarter) == 48
    assert {job["rev"]["grid_point"][1] for job in quarter} == set(judge.QUARTER_STEPS)
    assert all("-LQ-" in job["rev"]["label"] and job["rev"]["candidate"] == "P5r4"
               for job in quarter)


def test_touch_budget_fraction_steps():
    base = las_phase_diag.touch_budget_for("1", 1, 1.0, 0.9)
    half = las_phase_diag.touch_budget_for("1", 1.5, 1.0, 0.9)
    quarter = las_phase_diag.touch_budget_for("1", 0.75, 1.0, 0.9)
    assert half.record()["j"] == 1.5 and half.budget_m3_s < base.budget_m3_s
    centre_time_s = las_phase_diag.T1_S
    assert half.budget_m3_s == centre_time_s / (centre_time_s + 1.5 * 0.025)
    assert quarter.record()["j"] == 0.75
    assert quarter.budget_m3_s == centre_time_s / (centre_time_s + 0.75 * 0.025)
    for bad in (0.125, 5, True, 1.0, 4.25):
        with pytest.raises(ValueError):
            las_phase_diag.touch_budget_for("1", bad, 1.0, 0.9)


def test_ramp_period_values():
    config = SimpleNamespace(liftoff_approach_slow=SimpleNamespace(end_ramp_periods=4))
    slow = SimpleNamespace(ramp_periods_applied=2, ramp_scaled_periods=2, ramp_step=3,
                           ramp_start_factor=0.2)
    controller = SimpleNamespace(_state=SimpleNamespace(liftoff_slow=slow), config=config)
    before = las_phase_diag._SlowSnapshot(False, False, None, 23.0, 1, 1)
    values = las_phase_diag.ramp_period_values(controller, before)
    assert values == {"ramp_m": 2, "ramp_factor": c2.liftoff_ramp_factor(0.2, 2, 4),
                      "ramp_scaled": True}
    same = las_phase_diag._SlowSnapshot(False, False, None, 23.0, 2, 2)
    assert las_phase_diag.ramp_period_values(controller, same)["ramp_m"] is None


def test_out_names_and_candidates():
    assert reva.default_out("R-0P5", ("P5",), ("P5",)).name == "revA_R0P5.jsonl"
    assert reva.default_out("R-0A", ("P5r4",), ("P5r4",)).name == "revA_R0A.jsonl"
    assert reva.default_out("R-Q", ("P5r4",), ("P5r4",)).parent.name == "revA2"
    assert reva.resolve_candidates("R-T", None) == ("P5r4",)
    for bundle, text in (("R-T", "P5r6"), ("R-S", "P5"), ("R-0A", "P5r4,P5r6")):
        with pytest.raises(ValueError):
            reva.resolve_candidates(bundle, text)


def test_identity_records_the_five_rules():
    block = reva.rules_block()
    assert list(block) == list(judge.RULES_FIELDS)
    assert block["rules_revA_rev1_sha256"].startswith("c0251802")
    assert block["rules_revA_rev2_sha256"].startswith("9f478b7f")


def _write(path: Path, lines) -> None:
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")


def test_bit_test_gate_order(tmp_path):
    ref = reference()
    stored = stored_reva()
    current = {"git_head": "c0", "sha256": {"c2.py": "1"}}
    assert reva.bit_test_problems("R-0", current, ref, stored, tmp_path) == []
    assert reva.bit_test_problems("R-0P5", current, ref, stored, tmp_path)  # no R-0 file
    _write(tmp_path / "revA_R0.jsonl", r0_lines())
    assert reva.bit_test_problems("R-0P5", current, ref, stored, tmp_path) == []
    assert reva.bit_test_problems("R-0A", current, ref, stored, tmp_path)  # no R-0P5 file
    _write(tmp_path / "revA_R0P5.jsonl", r0p5_lines(ref))
    assert reva.bit_test_problems("R-0A", current, ref, stored, tmp_path) == []
    assert reva.bit_test_problems("R-Q", current, ref, stored, tmp_path)  # no R-0A file
    _write(tmp_path / "revA_R0A.jsonl", r0a_lines())
    assert reva.bit_test_problems("R-Q", current, ref, stored, tmp_path) == []
    assert reva.bit_test_problems("R-Q", {**current, "git_head": "c1"}, ref, stored, tmp_path)
    assert reva.bit_test_problems("R-Q", {**current, "sha256": {"c2.py": "2"}}, ref, stored,
                                  tmp_path)
    old_rules = r0_lines()
    old_rules[0]["rev"]["rules_revA_rev1_sha256"] = None
    _write(tmp_path / "revA_R0.jsonl", old_rules)
    problems = reva.bit_test_problems("R-0P5", current, ref, stored, tmp_path)
    assert problems == ["R-0: 1 lines with other rules sha256"]


def test_r0a_hash_mismatch_stops(tmp_path):
    ref = reference()
    lines = r0a_lines()
    stored = stored_reva(_copy(lines))
    lines[5]["commands_sha256"] = "0" * 64
    result = judge.judge_r0a(lines, stored)
    assert not result["pass"] and sum(not row["equal"] for row in result["rows"]) == 1
    assert any(text.startswith("H-2 R-0A") for text in
               judge.r0a_gate_problems(lines, ref, stored))
    full = judge.judge(full_lines(ref, r0a=lines), {}, ref, stored)
    assert any(text.startswith("H-2 R-0A") for text in full["stops"])
    assert judge.is_stop_result(full)
    _write(tmp_path / "revA_R0.jsonl", r0_lines())
    _write(tmp_path / "revA_R0P5.jsonl", r0p5_lines(ref))
    _write(tmp_path / "revA_R0A.jsonl", lines)
    current = {"git_head": "c0", "sha256": {"c2.py": "1"}}
    assert reva.bit_test_problems("R-Q", current, ref, stored, tmp_path)
    check = reva.make_checker(ref, stored)
    state = reva.rev.BatchState()
    record = _copy(lines[5])
    record["rev"]["identity"] = {}
    check(record, "R-0A", state, {}, {}, {})
    assert state.stop  # identity first; the hash check is below
    state = reva.rev.BatchState()
    check(_copy(lines[5]), "R-0A", state, {}, {}, _identity())
    assert state.stop and "H-2" in state.stop


def test_batch_check_r_q_k_mismatch_stops():
    ref = reference()
    check = reva.make_checker(ref, stored_reva())
    line = quarter_lines()[0]
    state = reva.rev.BatchState()
    check(_copy(line), "R-Q", state, {}, {}, _identity())
    assert state.stop is None
    line["las"]["ramp"]["start_factor"] = 0.4
    check(line, "R-Q", state, {}, {}, _identity())
    assert state.stop.startswith("H-13")


def test_earlier_identity_and_foreign_lines(tmp_path):
    ref = reference()
    current = {"git_head": "c0", "sha256": {"c2.py": "1"}}
    assert reva.earlier_identity_problems("R-T", current, tmp_path)  # no R-0A / R-Q files
    _write(tmp_path / "revA_R0A.jsonl", r0a_lines())
    _write(tmp_path / "revA_RQ.jsonl", quarter_lines())
    _write(tmp_path / "revA_R0.jsonl", r0_lines())
    _write(tmp_path / "revA_R0P5.jsonl", r0p5_lines(ref))
    assert reva.earlier_identity_problems("R-T", current, tmp_path) == []
    assert reva.earlier_identity_problems("R-T", {**current, "git_head": "c1"}, tmp_path)
    p5r6 = _line("R-0A", "P5r6", ("VB", "1", 0), 12.0)
    _write(tmp_path / "revA_RG_P5r6.jsonl", [p5r6])
    problems = reva.earlier_identity_problems("R-T", current, tmp_path)
    assert any("P5r6" in text and "not a rev2 line" in text for text in problems)


def test_prime_gate_before_na_da(tmp_path):
    ref = reference()
    stored = stored_reva()
    for name, lines in (("R0", r0_lines()), ("R0P5", r0p5_lines(ref)), ("R0A", r0a_lines()),
                        ("RQ", quarter_lines())):
        _write(tmp_path / f"revA_{name}.jsonl", lines)
    assert reva.prime_gate_problems({}, ref, stored, tmp_path) == []
    (tmp_path / "revA_RQ.jsonl").unlink()
    missed = quarter_lines({("VB", "1", 0.25): (14.3, -0.08)})  # Q-1 misses
    _write(tmp_path / "revA_RQ.jsonl", missed)
    problems = reva.prime_gate_problems({}, ref, stored, tmp_path)
    assert any(text.startswith("H-12") for text in problems)


def test_reference_is_needed(tmp_path):
    missing = tmp_path / "rev_RG.jsonl"
    paths = reva.ReferencePaths(missing, tmp_path / "a.jsonl", tmp_path / "b.jsonl")
    assert reva.load_references_for("R-0", paths) == (None, None)
    for bundle in ("R-0P5", "R-0A", "R-Q", "R-T", "R-P0", "R-X"):
        with pytest.raises(ValueError, match="H-10"):
            reva.load_references_for(bundle, paths)


def test_r0p5_line_check():
    ref = reference()
    line = r0p5_lines(ref)[0]
    assert reva.r0p5_problems(line, ref) == []
    line["diag"]["summary"]["F_RL_kN"] = 11.000000000000002
    assert reva.r0p5_problems(line, ref)


# ------------------------------------------------------------------------------- judge
def test_reference_problems(tmp_path):
    path = tmp_path / "rev_RG.jsonl"
    assert judge.reference_problems(path)[0].startswith("H-10 missing")
    path.write_text("x", encoding="utf-8")
    assert judge.reference_problems(path)[0].startswith("H-10 rev_RG.jsonl sha256")
    assert judge.reference_problems(path, hashlib.sha256(b"x").hexdigest()) == []
    problems = judge.stored_reva_problems(path, tmp_path / "none.jsonl")
    assert len(problems) == 2 and judge.STORED_REVA_RG_SHA256 in problems[0]


def test_sealed_rules_include_rev1_and_rev2():
    names = [path.name for path, _, _ in judge.SEALED_RULES]
    assert names[-3:] == ["las_revA_targeted_rules.md", "las_revA_targeted_rules_rev1.md",
                          "las_revA_targeted_rules_rev2.md"] and len(names) == 5
    assert judge.sealed_rules_problems() == []


def test_constants_of_rev1_and_rev2():
    assert judge.M2_P5_MAX_RANGE_KN == 1.1049128292761132
    source = Path(judge.__file__).read_text(encoding="utf-8")
    assert "11.418 (V0 nom j3,\nhash acfe58346d29; 11.314 was VB nom j3, rev1 RA1-1)" in source
    assert "rev1 RA1-2: stored P5 max R_c (V0 c0.94, j <= 3), not the rounded 1.105" in source
    assert judge.G2P_FLOOR_KN == 11.414589
    assert judge.G2P_FLOOR_KN == pytest.approx(rj.F_MIN_N / 1e3 + 2.0, abs=1e-12)


def test_m2_uses_the_stored_p5_maximum():
    ref = reference()
    lines = r0a_lines()
    by_point = {judge.grid_point_of(line): line for line in lines}
    for j, value in zip(judge.RANGE_STEPS, (12.0, 12.0, 12.0, 12.0 + 1.1049128292761132),
                        strict=True):
        by_point[("V0", "1", j)]["diag"]["summary"]["F_RL_kN"] = value
    assert judge.mechanism(lines, ref, stored_reva(_copy(lines)))["M-2"] == "rejected"
    by_point[("V0", "1", 3)]["diag"]["summary"]["F_RL_kN"] = 12.0 + 1.1049128292761
    assert judge.mechanism(lines, ref, stored_reva(_copy(lines)))["M-2"] == "confirmed"


def test_full_grid_passes_and_waits_for_na_da():
    ref = reference()
    stored = stored_reva()
    result = judge.judge(full_lines(ref), {}, ref, stored)
    assert result["R-0"]["pass"] and result["R-0P5"]["pass"] and result["R-0A"]["pass"]
    grid = result["grid"]
    assert grid["status"] == judge.STATUS_PASS, grid
    assert (grid["R-G_lines"], grid["R-H_lines"], grid["R-Q_lines"]) == (30, 24, 48)
    assert grid["records"]["Q"]["missed"] == []
    assert result["candidates"]["P5r4"]["verdict"] == judge.STATUS_INCOMPLETE
    assert result["stops"] == [] and result["asks"] == []
    assert judge.na_da_gate_problems(result) == []
    mech = result["mechanism"]
    assert mech["complete"] and mech["M-1"] == "confirmed" and mech["M-3"] == "confirmed"
    assert mech["M-1_median_kN"] == pytest.approx(P5R4_KN - P5_KN)
    assert len(grid["records"]["union16_cells"]) == 6
    assert all(cell["R_c"] is not None for cell in grid["records"]["union16_cells"])


def test_g2_prime_floor_boundary():
    ref = reference()
    stored = stored_reva()
    floor = judge.G2P_FLOOR_KN
    above = quarter_lines()
    above[0]["diag"]["summary"]["F_judged_min_kN"] = floor
    result = judge.judge(full_lines(ref, rq=above), {}, ref, stored)
    assert result["grid"][judge.G2P_KEY] is True
    below = quarter_lines()
    below[0]["diag"]["summary"]["F_judged_min_kN"] = 11.414588999999
    result = judge.judge(full_lines(ref, rq=below), {}, ref, stored)
    grid = result["grid"]
    assert grid[judge.G2P_KEY] is False and grid["status"] == judge.STATUS_FAIL
    failure = grid[judge.G2P_FAIL_KEY][0]
    assert failure["part"] == "R-Q" and failure["F_judged_min_kN"] == 11.414588999999
    assert any(text.startswith("H-6'") for text in result["stops"])
    assert result["candidates"]["P5r4"]["verdict"] == judge.STATUS_FAIL
    r0a = r0a_lines(f_rl=11.414589)
    result = judge.judge(full_lines(ref, r0a=r0a), {}, ref, stored_reva(_copy(r0a)))
    assert result["grid"][judge.G2P_KEY] is True


def test_old_g2_is_a_record_only():
    ref = reference()
    lines = r0a_lines()
    by_point = {judge.grid_point_of(line): line for line in lines}
    by_point[("V0", "1", 2)]["diag"]["summary"]["F_RL_kN"] = 14.0  # R_c 2 kN > 0.5
    result = judge.judge(full_lines(ref, r0a=lines), {}, ref, stored_reva(_copy(lines)))
    cell = [c for c in result["grid"]["records"]["G-2_cells"]
            if (c["setting"], c["centre"]) == ("V0", "1")][0]
    assert cell["ok"] is False and cell["R_c"] == pytest.approx(2.0)
    assert result["grid"]["status"] == judge.STATUS_PASS


def test_trough_and_value_clusters():
    assert judge.trough_kind(0.05) == judge.TROUGH_FIRST
    assert judge.trough_kind(0.0500001) == judge.TROUGH_AFTER
    assert judge.trough_kind(None) is None
    assert judge.value_cluster(12.2) == judge.CLUSTER_LOW
    assert judge.value_cluster(13.5) == judge.CLUSTER_LOW
    assert judge.value_cluster(13.7) == judge.CLUSTER_BETWEEN
    assert judge.value_cluster(14.0) == judge.CLUSTER_HIGH
    assert judge.value_cluster(16.1) == judge.CLUSTER_OUTSIDE
    line = _line("R-Q", "P5r4", ("V0", "1", 0.25), 12.5, gap_s=-0.02)
    assert judge.trough_gap_s(line) == pytest.approx(-0.02)


def _q_of(override):
    quarter = judge.part_lines_of(quarter_lines(override), judge.PART_RQ)
    return judge.q_predictions(quarter)


def test_q_predictions_hold_and_miss():
    assert _q_of({})["missed"] == []
    assert _q_of({("VB", "1", 0.25): (14.2, -0.08)})["missed"] == ["Q-1"]
    third = _q_of({("V0", "nom", 0.75): (13.7, -0.02)})
    assert "Q-2" in third["missed"] and third["Q-2"]["third_cluster"]
    low_after = _q_of({("V0", "nom", 0.25): (12.6, 0.2)})
    assert "Q-2" in low_after["missed"] and "Q-4" in low_after["missed"]
    few_low = {point: (HIGH_KN, AFTER_GAP_S) for point in _points(judge.QUARTER_STEPS)
               if point[:2] in judge.Q2_CELLS}
    few_low[("V0", "1", 0.25)] = (12.5, FIRST_GAP_S)
    assert _q_of(few_low)["missed"] == ["Q-3"]
    assert _q_of({("V0", "1", 0.25): (12.8, FIRST_GAP_S),
                  ("V0", "1", 1.25): (12.8, FIRST_GAP_S),
                  ("V0", "1", 2.25): (12.8, FIRST_GAP_S),
                  ("V0", "1", 3.25): (12.8, FIRST_GAP_S),
                  ("V0", "0.94", 0.25): (12.8, FIRST_GAP_S),
                  ("V0", "0.94", 1.25): (12.8, FIRST_GAP_S),
                  ("V0", "0.94", 2.25): (12.8, FIRST_GAP_S),
                  ("V0", "0.94", 3.25): (12.8, FIRST_GAP_S),
                  **{(s, c, j): (12.8, FIRST_GAP_S) for s, c in (("V0", "nom"), ("VB", "nom"))
                     for j in (0.25, 1.25, 2.25, 3.25)}})["missed"] == ["Q-5"]
    reaccel = _q_of({("VB", "0.94", 0.75): (14.62, 0.44), ("V0", "1", 0.75): (13.9, 0.1)})
    assert {"Q-2", "Q-4"} <= set(reaccel["missed"])
    incomplete = judge.q_predictions(judge.part_lines_of(quarter_lines()[:-1], judge.PART_RQ))
    assert incomplete["complete"] is False and incomplete["missed"] == []


def test_h12_asks_before_na_da_even_after_a_g2_prime_pass():
    ref = reference()
    rq = quarter_lines({("V0", "nom", 0.75): (13.7, -0.02)})
    result = judge.judge(full_lines(ref, rq=rq), {}, ref, stored_reva())
    assert result["grid"]["status"] == judge.STATUS_PASS
    assert any(text.startswith("H-12") for text in result["asks"])
    assert result["candidates"]["P5r4"]["verdict"] == judge.VERDICT_ASK
    assert judge.is_stop_result(result)
    assert any(text.startswith("H-12") for text in judge.na_da_gate_problems(result))


def test_empty_parts_are_incomplete():
    ref = reference()
    result = judge.judge(r0_lines() + r0p5_lines(ref) + r0a_lines(), {}, ref, stored_reva())
    assert result["grid"]["status"] == judge.STATUS_INCOMPLETE
    assert result["grid"]["not_run"] == ["R-Q"]
    assert result["candidates"]["P5r4"]["not_run"] is True
    assert not any(text.startswith("H-6") for text in result["stops"])
    assert judge.is_stop_result(result)


def test_status_order_stop_undecidable_fail():
    ref = reference()
    stored = stored_reva()
    low_rq = quarter_lines({("V0", "nom", 0.25): (11.0, -0.02)})
    base = full_lines(ref, rq=low_rq)
    assert judge.judge(base, {}, ref, stored)["candidates"]["P5r4"]["verdict"] == (
        judge.STATUS_FAIL)
    missing = [line for line in base if not (
        line["rev"]["bundle"] == "R-Q" and line["rev"]["grid_point"] == ["1", 0.75]
        and line["job"]["setting"] == "VB")]
    result = judge.judge(missing, {}, ref, stored)
    assert result["candidates"]["P5r4"]["verdict"] == judge.STATUS_UNDECIDABLE
    k_lines = _copy(missing)
    for line in k_lines:
        if line["rev"]["bundle"] == "R-0A":
            line["las"]["active_periods"] = 8  # K-A1
            break
    assert judge.judge(k_lines, {}, ref, stored)["candidates"]["P5r4"]["verdict"] == (
        judge.STATUS_STOP)


def _na_result(*, complete: bool = True, c_s: bool = True, r1: bool | None = True) -> dict:
    return {"complete": complete, "exception_excess": False,
            "checks": {"C-2": True, "C-1": True, "C-F": True, "C-S": c_s, "A-3": True,
                       "R-1": r1, "R-2": r1}}


def _da_result(*, complete: bool = True, c_s: bool = True) -> dict:
    return {"complete": complete, "checks": {"C-2": True, "C-S": c_s}}


def test_pair_verdict_undecidable_before_fail():
    """Rules 5.4: a missing pair or an empty population beats a failed check."""
    rp0_pass = {"pass": True}
    missing_na = judge._pair_verdict(_na_result(complete=False), _da_result(c_s=False), rp0_pass)
    assert missing_na["verdict"] == judge.STATUS_UNDECIDABLE
    missing_da = judge._pair_verdict(_na_result(c_s=False), _da_result(complete=False), rp0_pass)
    assert missing_da["verdict"] == judge.STATUS_UNDECIDABLE
    empty = judge._pair_verdict(_na_result(r1=None), _da_result(c_s=False), rp0_pass)
    assert empty["verdict"] == judge.STATUS_UNDECIDABLE
    not_run = judge._pair_verdict(None, _da_result(c_s=False), rp0_pass)
    assert not_run["verdict"] == judge.STATUS_INCOMPLETE
    failed = judge._pair_verdict(_na_result(), _da_result(c_s=False), rp0_pass)
    assert failed == {"verdict": judge.STATUS_FAIL, "at": ["(da) C-S"]}
    adopt = judge._pair_verdict(_na_result(), _da_result(), rp0_pass)
    assert adopt["verdict"] == "adopt_recommended"
    assert judge._pair_verdict(_na_result(), _da_result(), {"pass": False})["verdict"] == (
        judge.STATUS_INCOMPLETE)


def test_k_a_checks_on_r0a():
    ref = reference()
    point = ("V0", "1", 2)
    pair = ref[point]
    cand = _cand_rows(_line("R-0A", "P5r4", point, P5R4_KN))
    assert judge.grid_k_problems(cand, pair, "R-G") == []
    same_hash = {**cand, "commands_sha256": pair["commands_sha256"]}
    assert any(text.startswith("K-A5") for text in judge.grid_k_problems(same_hash, pair, "R-G"))
    wrong_start = _cand_rows(_line("R-0A", "P5r4", point, ramp=_ramp(4, start=0.3)))
    assert any("start_factor" in text for text in judge.grid_k_problems(wrong_start, pair, "R-G"))
    loc_end = _line("R-0A", "P5r4", point, end_reason="loc", ramp=_ramp(4, applied=1))
    loc_pair = _line("R-G", "P5", point, end_reason="loc")
    assert any(text.startswith("K-A6") for text in
               judge.grid_k_problems(loc_end, loc_pair, "R-G"))
    late_cmd = _copy(cand)
    late_cmd["diag"]["periods"][0]["cmd_mm_s"] = [5.5] * 4
    assert any(text.startswith("K-A2") for text in judge.grid_k_problems(late_cmd, pair, "R-G"))
    early_row = _copy(cand)
    early_row["diag"]["force_window"]["rows"][10][1] = 1.5
    assert any(text.startswith("K-A4") for text in
               judge.grid_k_problems(early_row, pair, "R-G"))
    lift = _copy(cand)
    lift["diag"]["summary"]["t_lift_s"] = 23.2
    assert any(text.startswith("K-A3") for text in judge.grid_k_problems(lift, pair, "R-G"))
    assert not any(text.startswith("K-A3") for text in judge.grid_k_problems(lift, pair, "R-H"))
    wrong_n_r = _copy(cand)
    wrong_n_r["rev"]["settings"]["end_ramp_periods"] = 6
    assert any(text.startswith("K-A8") for text in judge.grid_k_problems(wrong_n_r, pair, "R-G"))
    not_started = _line("R-0A", "P5r4", point, start=None)
    assert any(text.startswith("K-A7") for text in
               judge.grid_k_problems(not_started, pair, "R-G"))
    gap_in_steps = _copy(cand)
    gap_in_steps["diag"]["periods"][2]["las"]["ramp_m"] = 3
    assert any("ramp steps" in text for text in
               judge.grid_k_problems(gap_in_steps, pair, "R-G"))


def test_k_a_checks_on_r_q_without_a_pair():
    line = quarter_lines()[0]
    assert judge.quarter_k_problems(line) == []
    never_scaled = _copy(line)
    never_scaled["las"]["ramp"]["scaled_periods"] = 0
    for period in never_scaled["diag"]["periods"]:
        if "ramp_scaled" in period["las"]:
            period["las"]["ramp_scaled"] = False
    assert any("never scaled" in text for text in judge.quarter_k_problems(never_scaled))
    wrong_lambda = _copy(line)
    wrong_lambda["las"]["ramp"]["start_factor"] = 0.3
    found = judge.quarter_k_problems(wrong_lambda)
    assert any(text.startswith("K-A5 start_factor") for text in found)
    assert all(judge.is_h13(text) for text in found)
    loc = _line("R-Q", "P5r4", ("VB", "1", 0.25), end_reason="loc", ramp=_ramp(4, applied=2))
    assert any(text.startswith("K-A6") for text in judge.quarter_k_problems(loc))


def test_h13_stop_in_judge():
    ref = reference()
    rq = quarter_lines()
    rq[3]["rev"]["settings"]["end_ramp_periods"] = 6
    result = judge.judge(full_lines(ref, rq=rq), {}, ref, stored_reva())
    assert any(text.startswith("H-13") for text in result["stops"])
    assert result["candidates"]["P5r4"]["verdict"] == judge.STATUS_STOP


def test_r_t_k_a7_and_h4():
    stored = {"T-1": {"kT": {"commands_sha256": "l" * 64}}}
    line = _line("R-T", "P5r4", ("VB", "1", 0), sha="m" * 64, start=None)
    line["rev"]["key"] = "kT"
    assert any(text.startswith("kT: K-A7") for text in judge.pair_k_problems([line], stored,
                                                                              "P5r4"))
    del line["las"]["params"]
    assert judge.pair_k_problems([line], stored, "P5r4")[0].startswith("H-4")


def test_mechanism_rejection_is_h11_prime():
    ref = reference()
    r0a = r0a_lines(f_rl=10.9)
    for line in r0a:
        line["diag"]["summary"]["F_judged_min_kN"] = 12.0
    result = judge.judge(full_lines(ref, r0a=r0a), {}, ref, stored_reva(_copy(r0a)))
    assert result["mechanism"]["M-1"] == "rejected"
    assert result["mechanism"]["M-3"] == "rejected"
    assert any(text.startswith("H-11'") for text in result["stops"])
    assert judge.is_stop_result(result)
    assert any("H-11'" in text for text in
               judge.r0a_gate_problems(r0a, ref, stored_reva(_copy(r0a))))


def test_r0p5_judge_and_h2():
    ref = reference()
    lines = r0_lines() + r0p5_lines(ref)
    assert judge.judge_r0p5(lines, ref)["pass"]
    lines[-1]["commands_sha256"] = "0" * 64
    assert not judge.judge_r0p5(lines, ref)["pass"]
    result = judge.judge(lines, {}, ref, stored_reva())
    assert any(text.startswith("H-2 R-0 / R-0P5") for text in result["stops"])


def test_identity_needs_the_five_rules_and_one_commit():
    ref = reference()
    lines = full_lines(ref)
    for line in lines:
        if line["rev"]["bundle"] == "R-Q":
            line["rev"]["identity"] = _identity("c1")
            break
    lines[-1]["rev"]["rules_revA_rev2_sha256"] = None
    result = judge.judge(lines, {}, ref, stored_reva())
    assert any("2 commits" in text for text in result["identity"]["P5r4"])
    assert any("rules sha256" in text for text in result["identity"]["P5r4"])
    assert result["candidates"]["P5r4"]["verdict"] == judge.STATUS_UNDECIDABLE


def test_p5r6_lines_are_reported_not_ignored():
    ref = reference()
    p5r6 = [_line("R-0A", "P5r6", ("VB", "1", 0), 12.0), _line("R-G", "P5r6", ("V0", "1", 1))]
    result = judge.judge(full_lines(ref) + p5r6, {}, ref, stored_reva())
    foreign = result["identity"]["foreign"]
    assert len(foreign) == 2 and all("P5r6" in text for text in foreign)
    assert any(text.startswith("H-4 identity foreign") for text in result["stops"])
    assert result["candidates"]["P5r4"]["verdict"] == judge.STATUS_UNDECIDABLE
    assert any("K-A8 candidate 'P5r6'" in text
               for text in judge.settings_problems(p5r6[0]))


def test_ramp_end_for_the_exception_rule():
    assert judge.ramp_end_s({"las": {"end_t_s": 23.0, "ramp": _ramp(4)}}) == pytest.approx(23.3)
    assert judge.ramp_end_s({"las": {"end_t_s": 23.0, "ramp": reva.no_ramp(4)}}) == 23.0
