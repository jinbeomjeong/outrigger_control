"""Tests of ``las_revA_targeted.py`` (candidates, jobs, gates) and ``las_revA_judge.py``.

The judge is checked on hand-made lines (no simulation): status order, the empty candidate,
H-6, the K-A checks, M-1 .. M-3 and the bit tests. ``las_phase_diag`` gets its R-H half steps
and the ramp period values checked here too.
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


def _line(bundle, candidate, point, f_rl=11.0, sha=None, end_reason="sum", start=21.0,
          ramp=None, label=None):
    """A grid line whose LAS-b, periods and force window are those of the P5 pair."""
    beta, n_min, n_r = judge.CANDIDATE_VALUES[candidate]
    setting, centre, j = point
    settings = {"light_leg_fraction_of_F_min": beta, "min_active_periods": n_min,
                "end_ramp_periods": n_r}
    tag = rj.CONTROLLER_TAG_BY_SETTING[setting]
    sha = sha or hashlib.sha256(f"{candidate}{point}".encode()).hexdigest()
    las = {"start_t_s": start, "end_t_s": T_END_S, "end_reason": end_reason,
           "active_periods": 9, "scaled_periods": 9, "start_leg": 2,
           "params": {"beta": beta, "n_min": n_min, "n_r": n_r},
           "ramp": ramp if ramp is not None else _ramp(n_r)}
    acted = {"active_after": True, "is_scaled": True, "input_mm_s": [20.0] * 4,
             "output_mm_s": [20.0 * LAMBDA_0] * 4}
    periods = [{"t_s": 22.9, "cmd_mm_s": [5.0] * 4, "las": acted},
               {"t_s": T_END_S, "cmd_mm_s": [6.0 if n_r else 20.0] * 4,
                "las": {"active_after": False}}]
    rows = [[T_END_S + 0.001 * k, 1.0, 2.0] for k in range(-50, 150)]
    return {"job": {"setting": setting, "d1": {}}, "commands_sha256": sha,
            "controller_tag": tag, "las": las,
            "rev": {"bundle": bundle, "candidate": candidate,
                    "label": label or f"{candidate}-{bundle}-{point}", "key": f"k{setting}",
                    "grid_point": [centre, j], "settings": settings, "settings_match": True,
                    "rules_sha256": rj.RULES_SHA256, "rules_rev1_sha256": rj.RULES_REV1_SHA256,
                    "rules_revA_sha256": judge.RULES_REVA_SHA256, "controller_tag": tag,
                    "identity": _identity()},
            "diag": {"summary": {"F_RL_kN": f_rl, "F_judged_min_kN": f_rl,
                                 "gate_consistent": True, "t_lift_s": T_LIFT_S},
                     "touch_budget": {"level_budget_periods": 0}, "periods": periods,
                     "force_window": {"rows": rows}}}


def _cand_rows(line, n_r):
    """Candidate rows equal to P5 before t_e + 0.1 s, different after (the ramp)."""
    if n_r:
        line["diag"]["force_window"]["rows"] = [
            row if row[0] < T_END_S + 0.1 else [row[0], 9.0, 9.0]
            for row in line["diag"]["force_window"]["rows"]]
    return line


def _points(steps):
    return sorted(judge.expected_points(steps), key=str)


def reference(f_rl=11.0):
    return {point: _line("R-G", "P5", point, f_rl, label="P5-LT") for point in
            _points(judge.GRID_STEPS)}


def grid(candidate, f_rl=11.2, bundle="R-G"):
    steps = judge.HALF_STEPS if bundle == "R-H" else judge.GRID_STEPS
    n_r = judge.CANDIDATE_VALUES[candidate][2]
    return [_cand_rows(_line(bundle, candidate, point, f_rl), n_r) for point in _points(steps)]


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


def full_lines(ref, p5r4=11.2, p5r6=11.3):
    return (r0_lines() + r0p5_lines(ref) + grid("P5r4", p5r4) + grid("P5r6", p5r6)
            + grid("P5", 11.0, "R-H") + grid("P5r4", p5r4, "R-H") + grid("P5r6", p5r6, "R-H"))


# ------------------------------------------------------------------------------- runner pieces
def test_candidates_and_labels():
    preset = reva.rev.preset_las_settings()
    assert reva.CANDIDATES["P0"].settings_from(preset) is preset
    p5r6 = reva.CANDIDATES["P5r6"].settings_from(preset)
    assert (p5r6.light_leg_fraction_of_F_min, p5r6.min_active_periods,
            p5r6.end_ramp_periods) == (4.5, 0, 6)
    assert replace(p5r6, light_leg_fraction_of_F_min=3.5, end_ramp_periods=0) == preset
    assert reva.grid_label("P5r4", "nom", 1.5, True) == "P5r4-LH-cnom-j1p5"
    assert reva.grid_label("P5", "0.94", 0, False) == "P5-LT-c0.94-j0"


def test_bundle_counts_and_half_points():
    assert len(reva.bundle_jobs("R-0", ("P0",))) == 6
    assert len(reva.bundle_jobs("R-0P5", ("P5",))) == 30
    assert len(reva.bundle_jobs("R-G", judge.JUDGED_CANDIDATES)) == 60
    half = reva.bundle_jobs("R-H", judge.HALF_CANDIDATES)
    assert len(half) == 72
    assert {job["rev"]["grid_point"][1] for job in half} == set(judge.HALF_STEPS)
    assert [job["rev"]["candidate"] for job in half[:3]] == ["P5", "P5r4", "P5r6"]


def test_touch_budget_half_steps():
    base = las_phase_diag.touch_budget_for("1", 1, 1.0, 0.9)
    half = las_phase_diag.touch_budget_for("1", 1.5, 1.0, 0.9)
    assert half.record()["j"] == 1.5 and half.budget_m3_s < base.budget_m3_s
    centre_time_s = las_phase_diag.T1_S
    assert half.budget_m3_s == centre_time_s / (centre_time_s + 1.5 * 0.025)
    for bad in (0.75, 5, True, 1.0):
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
    assert reva.default_out("R-T", ("P5r4",), None).name == "revA_RT_P5r4.jsonl"
    with pytest.raises(ValueError):
        reva.resolve_candidates("R-T", None)
    with pytest.raises(ValueError):
        reva.resolve_candidates("R-S", "P5")
    assert reva.resolve_candidates("R-H", None) == ("P5", "P5r4", "P5r6")


def _write(path: Path, lines) -> None:
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")


def test_bit_test_gate(tmp_path):
    ref = reference()
    current = {"sha256": {"c2.py": "1"}}
    assert reva.bit_test_problems("R-0", current, ref, tmp_path) == []
    assert reva.bit_test_problems("R-0P5", current, ref, tmp_path)  # no R-0 file
    _write(tmp_path / "revA_R0.jsonl", r0_lines())
    assert reva.bit_test_problems("R-0P5", current, ref, tmp_path) == []
    assert reva.bit_test_problems("R-G", current, ref, tmp_path)  # no R-0P5 file
    _write(tmp_path / "revA_R0P5.jsonl", r0p5_lines(ref))
    assert reva.bit_test_problems("R-G", current, ref, tmp_path) == []
    assert reva.bit_test_problems("R-G", {"sha256": {"c2.py": "2"}}, ref, tmp_path)


def test_grid_gate_and_earlier_identity(tmp_path):
    ref = reference()
    _write(tmp_path / "revA_RG.jsonl", grid("P5r4") + grid("P5r6", 10.0))
    _write(tmp_path / "revA_RH.jsonl", grid("P5", 11.0, "R-H") + grid("P5r4", 11.2, "R-H"))
    problems = reva.grid_gate_problems(("P5r4", "P5r6"), ref, tmp_path)
    assert problems == ["P5r6: R-G / R-H lines (30, 0), expected (30, 24)"]
    assert reva.grid_gate_problems(("P5r4",), ref, tmp_path) == []
    current = {"git_head": "c0", "sha256": {"c2.py": "1"}}
    assert reva.earlier_identity_problems("R-T", current, tmp_path) == []
    assert reva.earlier_identity_problems("R-T", {**current, "git_head": "c1"}, tmp_path)


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


def test_sealed_rules_include_reva():
    names = [path.name for path, _, _ in judge.SEALED_RULES]
    assert names[-1] == "las_revA_targeted_rules.md" and len(names) == 3
    assert judge.sealed_rules_problems() == []


def test_full_grid_passes_and_waits_for_na_da():
    ref = reference()
    result = judge.judge(full_lines(ref), {}, ref)
    assert result["R-0"]["pass"] and result["R-0P5"]["pass"]
    for name in judge.JUDGED_CANDIDATES:
        assert result["grid"][name]["status"] == judge.STATUS_PASS, result["grid"][name]
        assert result["candidates"][name]["verdict"] == judge.STATUS_INCOMPLETE
    assert result["stops"] == [] and not judge.is_stop_result(result)
    mech = result["mechanism"]["P5r4"]
    assert mech["complete"] and mech["M-1"] == "confirmed" and mech["M-3"] == "confirmed"
    assert mech["M-1_median_kN"] == pytest.approx(0.2)


def test_empty_candidate_is_incomplete_and_not_counted_by_h6():
    ref = reference()
    lines = (r0_lines() + r0p5_lines(ref) + grid("P5r4", 10.0) + grid("P5", 11.0, "R-H")
             + grid("P5r4", 10.0, "R-H"))
    result = judge.judge(lines, {}, ref)
    assert result["grid"]["P5r4"]["status"] == judge.STATUS_FAIL
    assert result["candidates"]["P5r6"]["not_run"] is True
    assert not any(text.startswith("H-6") for text in result["stops"])
    assert judge.is_stop_result(result)
    both = judge.judge(lines + grid("P5r6", 10.0) + grid("P5r6", 10.0, "R-H"), {}, ref)
    assert any(text.startswith("H-6") for text in both["stops"])


def test_status_order_stop_undecidable_fail():
    ref = reference()
    base = full_lines(ref, p5r4=10.0)
    assert judge.judge(base, {}, ref)["candidates"]["P5r4"]["verdict"] == judge.STATUS_FAIL
    missing = [line for line in base if not (
        line["rev"]["candidate"] == "P5r4" and line["rev"]["bundle"] == "R-H"
        and line["rev"]["grid_point"] == ["1", 0.5] and line["job"]["setting"] == "VB")]
    result = judge.judge(missing, {}, ref)
    assert result["candidates"]["P5r4"]["verdict"] == judge.STATUS_UNDECIDABLE
    k_lines = json.loads(json.dumps(missing))
    for line in k_lines:
        if line["rev"]["candidate"] == "P5r4" and line["rev"]["bundle"] == "R-G":
            line["las"]["active_periods"] = 8  # K-A1
            break
    assert judge.judge(k_lines, {}, ref)["candidates"]["P5r4"]["verdict"] == judge.STATUS_STOP


def test_k_a_checks():
    ref = reference()
    point = ("V0", "1", 2)
    pair = ref[point]
    cand = _cand_rows(_line("R-G", "P5r4", point), 4)
    assert judge.grid_k_problems(cand, pair, "R-G") == []
    same_hash = {**cand, "commands_sha256": pair["commands_sha256"]}
    assert any(text.startswith("K-A5") for text in judge.grid_k_problems(same_hash, pair, "R-G"))
    wrong_start = _cand_rows(_line("R-G", "P5r4", point, ramp=_ramp(4, start=0.3)), 4)
    assert any("start_factor" in text for text in judge.grid_k_problems(wrong_start, pair, "R-G"))
    loc_end = _line("R-G", "P5r4", point, end_reason="loc", ramp=_ramp(4, applied=1))
    loc_pair = _line("R-G", "P5", point, end_reason="loc")
    assert any(text.startswith("K-A6") for text in
               judge.grid_k_problems(loc_end, loc_pair, "R-G"))
    late_cmd = json.loads(json.dumps(cand))
    late_cmd["diag"]["periods"][0]["cmd_mm_s"] = [5.5] * 4
    assert any(text.startswith("K-A2") for text in judge.grid_k_problems(late_cmd, pair, "R-G"))
    early_row = json.loads(json.dumps(cand))
    early_row["diag"]["force_window"]["rows"][10][1] = 1.5
    assert any(text.startswith("K-A4") for text in
               judge.grid_k_problems(early_row, pair, "R-G"))
    lift = json.loads(json.dumps(cand))
    lift["diag"]["summary"]["t_lift_s"] = 23.2
    assert any(text.startswith("K-A3") for text in judge.grid_k_problems(lift, pair, "R-G"))
    assert not any(text.startswith("K-A3") for text in judge.grid_k_problems(lift, pair, "R-H"))
    wrong_n_r = json.loads(json.dumps(cand))
    wrong_n_r["rev"]["settings"]["end_ramp_periods"] = 6
    assert any(text.startswith("K-A8") for text in judge.grid_k_problems(wrong_n_r, pair, "R-G"))
    not_started = _line("R-G", "P5r4", point, start=None)
    assert any(text.startswith("K-A7") for text in
               judge.grid_k_problems(not_started, pair, "R-G"))


def test_r_t_k_a7_and_h4():
    stored = {"T-1": {"kT": {"commands_sha256": "l" * 64}}}
    line = _line("R-T", "P5r4", ("VB", "1", 0), sha="m" * 64, start=None)
    line["rev"]["key"] = "kT"
    assert any(text.startswith("kT: K-A7") for text in judge.pair_k_problems([line], stored,
                                                                              "P5r4"))
    del line["las"]["params"]
    assert judge.pair_k_problems([line], stored, "P5r4")[0].startswith("H-4")


def test_mechanism_rejections_and_h11():
    ref = reference()
    lines = full_lines(ref, p5r4=10.9, p5r6=10.95)
    result = judge.judge(lines, {}, ref)
    for name in judge.JUDGED_CANDIDATES:
        assert result["mechanism"][name]["M-1"] == "rejected"
        assert result["mechanism"][name]["M-3"] == "rejected"
    assert result["asks"] and judge.is_stop_result(result)


def test_r0p5_judge_and_h2():
    ref = reference()
    lines = r0_lines() + r0p5_lines(ref)
    assert judge.judge_r0p5(lines, ref)["pass"]
    lines[-1]["commands_sha256"] = "0" * 64
    assert not judge.judge_r0p5(lines, ref)["pass"]
    result = judge.judge(lines, {}, ref)
    assert any(text.startswith("H-2") for text in result["stops"])


def test_identity_needs_the_three_rules_and_one_commit():
    ref = reference()
    lines = full_lines(ref)
    for line in lines:
        if line["rev"]["candidate"] == "P5r6" and line["rev"]["bundle"] == "R-H":
            line["rev"]["identity"] = _identity("c1")
            break
    lines[-1]["rev"]["rules_revA_sha256"] = None
    result = judge.judge(lines, {}, ref)
    assert any("2 commits" in text for text in result["identity"]["P5r6"])
    assert any("rules sha256" in text for text in result["identity"]["P5r6"])
    assert result["candidates"]["P5r6"]["verdict"] == judge.STATUS_UNDECIDABLE


def test_ramp_end_for_the_exception_rule():
    assert judge.ramp_end_s({"las": {"end_t_s": 23.0, "ramp": _ramp(4)}}) == pytest.approx(23.3)
    assert judge.ramp_end_s({"las": {"end_t_s": 23.0, "ramp": reva.no_ramp(4)}}) == 23.0
