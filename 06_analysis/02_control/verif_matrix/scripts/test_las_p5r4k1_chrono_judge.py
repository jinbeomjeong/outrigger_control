"""Unit tests of the path 1 Chrono judge (synthetic rows, no batch folder)."""
from __future__ import annotations

import copy
import struct
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import las_p5r4k1_chrono_judge as cj  # noqa: E402


def make_result(arm: str, *, started: float | None = 30.0, ramp: int = 2,
                f_after: float = 12000.0, stroke: float = 0.5, ready: float = 60.0,
                items=None, decisions=None, events=None) -> dict:
    settings = dict(cj.P5R4_VALUES if arm == cj.ARM_CAND else cj.B0_VALUES)
    checks = {key: True for key in cj.ITEM_KEYS}
    checks.update(items or {})
    return {
        "p3b": {"checks": checks,
                "P3-3_leg_force": {"F_min_after_N": [f_after, 20000.0],
                                   "F_min_transient_N": [f_after, 20000.0]},
                "P3-5_clearance_stroke": {"s_motor_max_m": [stroke, 0.1]},
                "P3-6_ready": {"t_ready_after_loop_start_s": ready}},
        "controller_meta": {
            "liftoff_approach_slow": {"settings": settings, "start_s": started,
                                      "ramp": {"periods_applied": ramp}},
            "slope_clearance_margin": {"order_gate": {"enabled": True,
                                                      "decisions": decisions or []}},
            "soil": {"t_P_s": 39.0, "bias_corner_raw_m": [0.0] * 4, "bias_corner_m": [0.0] * 4,
                     "loc_anchor_bias_mm": None, "loc_anchor_applied": False,
                     "mode_starts": []}},
        "events": events if events is not None else [
            {"t_s": 40.0, "name": "crawler_liftoff_confirmed"}],
        "phases": [{"t_s": 10.0, "phase": "touch"}, {"t_s": 70.0, "phase": "ready"}],
    }


def commands(values: list[float]) -> cj.CommandDigest:
    t = tuple(0.1 * i for i in range(len(values)))
    rows = tuple(struct.pack("<4d", v, v, v, v) for v in values)
    t_bytes = struct.pack(f"<{len(t)}d", *t)
    return cj.CommandDigest(cj.sha256_bytes(t_bytes + b"".join(rows)), t, rows)


def make_inputs(results: dict[str, dict], cmds: dict[str, cj.CommandDigest] | None = None
                ) -> cj.JudgeInputs:
    rows = {}
    for spec in cj.ROW_SPECS:
        result = results.get(spec.p5k_id) or make_result(spec.arm)
        digest = (cmds or {}).get(spec.p5k_id, commands([1.0, 2.0]))
        rows[spec.p5k_id] = cj.RowInput(spec, spec.p5k_id, result, {"rc": 0}, digest)
    return cj.JudgeInputs(rows=rows, batch={}, prelaunch=None, postrun=None, rules={},
                          tool_sha256=None, expect_tool_sha256=None, audit_sha256_now=None,
                          code_diff_quiet=lambda a, b: None)


def criteria_of(inputs: cj.JudgeInputs) -> dict:
    analyses = {key: cj.analyze_row(row) for key, row in inputs.rows.items()}
    return cj.criteria_6_3(inputs, analyses)


def test_all_equal_rows_pass_the_6_3_criteria():
    out = criteria_of(make_inputs({}))
    assert {name: c["status"] for name, c in out["criteria"].items()} == {
        name: cj.STATUS_PASS for name in out["criteria"]}


def test_missing_item_key_makes_the_criteria_undecidable():
    result = make_result(cj.ARM_CAND)
    del result["p3b"]["checks"]["P3-7_within"]
    out = criteria_of(make_inputs({"A2": result}))
    assert out["criteria"]["CC-2"]["status"] == cj.STATUS_UNDECIDABLE
    assert out["undecidable"]


def test_late_loc_exception_turns_p32_into_a_flag():
    late = make_result(cj.ARM_CAND, items={"P3-2_within": False,
                                           "P3-2_late_loc_reapproach": True})
    out = criteria_of(make_inputs({"B2": late}))
    assert out["criteria"]["CC-2"]["ok"] is True
    assert out["flags"]["LATE_LOC_P32"] == ["B1/B2"]
    plain_fail = make_result(cj.ARM_CAND, items={"P3-2_within": False})
    assert criteria_of(make_inputs({"B2": plain_fail}))["criteria"]["CC-2"]["ok"] is False


def test_observation_requirement_needs_one_acting_a_pair():
    not_acting = {key: make_result(cj.ARM_CAND, started=None, ramp=0)
                  for key in ("A2", "A4", "A6")}
    out = criteria_of(make_inputs(not_acting))
    assert out["criteria"]["observation"]["status"] == cj.STATUS_UNDECIDABLE
    assert out["criteria"]["observation"]["reason"] == "NO_P5R4_OBSERVATION"
    one = {**not_acting, "A4": make_result(cj.ARM_CAND, started=30.0, ramp=1)}
    assert criteria_of(make_inputs(one))["criteria"]["observation"]["ok"] is True


def test_ready_criterion_empty_population_two_cases():
    assert cj.ready_criterion({}, False)["status"] == cj.STATUS_PASS
    changed = {"x": {"changed": True, "dt_s": None}}
    assert cj.ready_criterion(changed, False)["status"] == cj.STATUS_UNDECIDABLE


def test_pair_diverge_needs_a_not_started_cand_with_other_commands():
    cand = make_result(cj.ARM_CAND, started=None, ramp=0)
    out = criteria_of(make_inputs({"C2": cand}, {"C2": commands([1.0, 3.0])}))
    assert out["PAIR_DIVERGE"] == ["C1/C2"]
    started = criteria_of(make_inputs({}, {"C2": commands([1.0, 3.0])}))
    assert started["PAIR_DIVERGE"] == [] and started["PAIR_CMD_DIFF"] == ["C1/C2"]


def test_ck1c_r4_lost_with_the_is_prefixed_decision_keys():
    applied = {"t_loc_s": 40.0, "t_P_s": 39.0, "t_S_s": 30.0, "n_P": 390, "n_S": 300,
               "is_r4_due_without_gate": True, "would_block": False, "is_applied": True}
    blocked = {**applied, "is_applied": False, "would_block": True}
    out = criteria_of(make_inputs({"C1": make_result(cj.ARM_REF, decisions=[applied]),
                                   "C2": make_result(cj.ARM_CAND, decisions=[blocked])}))
    assert out["criteria"]["CK-1C"]["ok"] is False


def test_g2pc_uses_the_after_and_transient_minima():
    low = make_result(cj.ARM_CAND, f_after=11000.0)
    out = criteria_of(make_inputs({"A6": low}))
    assert out["criteria"]["G-2'C"]["ok"] is False


def test_force_keys_absent_before_departure_read_as_none():
    result = make_result(cj.ARM_REF)
    del result["p3b"]["P3-3_leg_force"]
    assert cj.force_after_N(result) is None


def test_anchor_flag_from_events_and_decisions():
    ref = make_result(cj.ARM_REF, events=[{"t_s": 40.0, "name": "crawler_liftoff_confirmed"},
                                          {"t_s": 40.0, "name": "INFO_CLEARANCE_BIAS:1,2"}])
    cand = copy.deepcopy(make_result(cj.ARM_CAND))
    cand["controller_meta"]["soil"]["t_P_s"] = 39.2
    pair = cj.anchor_pair(ref, cand)
    assert pair["ref"]["anchor_path"] == cj.PATH_CORNER_BIAS
    assert pair["ANCHOR_SAMPLE_SHIFT"] is True
    assert cj.anchor_pair(make_result(cj.ARM_REF), cand)["ANCHOR_SAMPLE_SHIFT"] is False


def test_bt_c_prefix_compares_contents_up_to_the_span_end():
    long_run = commands([1.0, 2.0, 3.0])
    short = commands([1.0, 2.0])
    assert long_run.prefix_sha256(0.1) == short.prefix_sha256(0.1)
    assert long_run.prefix_sha256(None) != short.prefix_sha256(None)


def test_k4_reads_forced_block_dict_and_class():
    result = make_result(cj.ARM_REF)
    result["controller_meta"]["slope_clearance_margin"]["settings"] = {
        "flat_soil_margin_order_gate": True}
    result["controller_meta"]["touch_creep_latch"] = {"settings": {"enable": False}}
    result["c2_setup"] = {"k1_order_gate": "preset", "k1_order_gate_effective": True,
                          "touch_creep_effective": False,
                          "k1_forced_block": {"requested": "off",
                                              "class": "outrigger_sim.control.c2.C2Controller",
                                              "module_sha256": None}}
    row = cj.RowInput(cj.SPEC_BY_ID["A1"], "A1", result,
                      {"rc": 0, "controller": "final_C4G2_P3_LAS_K1"})
    assert cj.k4_row_problems(row, cj.analyze_row(row)) == []
    result["c2_setup"]["k1_forced_block"]["class"] = "x.K1ForcedBlockC2Controller"
    assert cj.k4_row_problems(row, cj.analyze_row(row))


def test_k3_batch_controller_tag_and_k7_mass_scale():
    result = make_result(cj.ARM_CAND)
    result["args"] = {**cj.FIXED_ARGS, "duration": 180.0, "las_candidate": "P5r4",
                      "mass_scale": 1.1, "expect_controller": "final_C4G2_P3_LAS_K1"}
    result["mass_scale"] = {"mass_scale": 1.1}
    entry = {"rc": 0, "controller": "final_C4G2_LAS_K1",
             "argv": ["python", "run_S9.py", "--las-candidate", "P5r4"]}
    row = cj.RowInput(cj.SPEC_BY_ID["C4"], "C4", result, entry)
    assert cj.k7_row_problems(row) == []
    assert any("batch controller" in text for text in cj.k3_row_problems(row))


def test_rv2_3_no_departure_cand_fails_cc_f_and_g2pc():
    cand = make_result(cj.ARM_CAND)
    del cand["p3b"]["P3-3_leg_force"]
    cand["p3b"]["departure"] = {"departed": False}
    out = criteria_of(make_inputs({"A2": cand}))
    assert out["criteria"]["CC-F"]["ok"] is False and out["criteria"]["G-2'C"]["ok"] is False
    assert out["no_departure"] == ["A1/A2"]


def test_rv2_3_no_departure_ref_is_outside_cc_f():
    ref = make_result(cj.ARM_REF)
    del ref["p3b"]["P3-3_leg_force"]
    ref["p3b"]["departure"] = {"departed": False}
    out = criteria_of(make_inputs({"A1": ref}))
    assert out["criteria"]["CC-F"]["ok"] is True
    assert out["criteria"]["CC-F"]["ref_none"] == ["A1/A2"]


def test_rv2_3_departed_with_a_missing_key_opens_only_cc_f_and_g2pc():
    cand = make_result(cj.ARM_CAND)
    del cand["p3b"]["P3-3_leg_force"]["F_min_transient_N"]
    cand["p3b"]["departure"] = {"departed": True}
    out = criteria_of(make_inputs({"A2": cand}))
    assert out["criteria"]["CC-F"]["status"] == cj.STATUS_UNDECIDABLE
    assert out["criteria"]["G-2'C"]["status"] == cj.STATUS_UNDECIDABLE
    assert out["criteria"]["CC-S"]["ok"] is True and out["criteria"]["CC-2"]["ok"] is True


def test_rv2_2_one_none_leg_makes_the_value_none():
    result = make_result(cj.ARM_CAND)
    result["p3b"]["P3-5_clearance_stroke"]["s_motor_max_m"] = [0.5, None]
    assert cj.stroke_max_m(result) is None
    out = criteria_of(make_inputs({"C2": result}))
    assert out["criteria"]["CC-S"]["ok"] is False


def test_rv2_4_missing_phases_opens_the_whole_pair_and_leaves_cc_r_population():
    cand = make_result(cj.ARM_CAND, ready=80.0)
    del cand["phases"]
    out = criteria_of(make_inputs({"C2": cand}, {"C2": commands([1.0, 3.0])}))
    assert all(c["status"] == cj.STATUS_UNDECIDABLE for name, c in out["criteria"].items()
               if name != "observation")
    assert out["criteria"]["CC-R"]["population"] == 0


def test_rv2_13_boundary_row_is_included():
    digest = commands([1.0, 2.0, 3.0])
    shorter = commands([1.0, 2.0])
    assert digest.prefix_sha256(0.1) == shorter.prefix_sha256(0.1)
    assert digest.prefix_sha256(0.2) != shorter.prefix_sha256(0.2)


@pytest.mark.parametrize(("statuses", "expected"), [
    ([cj.STATUS_FAIL], cj.STATUS_FAIL), ([cj.STATUS_UNDECIDABLE], cj.STATUS_UNDECIDABLE),
    ([cj.STATUS_FAIL, cj.STATUS_UNDECIDABLE], cj.STATUS_UNDECIDABLE)])
def test_priority_three_cases(statuses, expected):
    assert cj.worst_status(statuses) == expected
