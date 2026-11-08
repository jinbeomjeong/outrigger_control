"""Tests of ``las_rev_targeted.py`` (candidates, DONE record) and ``las_rev_judge.py``.

The DONE recorder is checked on the synthetic READY bench of ``05_tests/unit/test_c2_r8d1.py``
with the real controller: the commands stay bit for bit and the trace / clock are filled.
The judge is checked on hand-made lines (no simulation).
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "03_src"))
sys.path.insert(0, str(HERE.parents[2] / "05_tests" / "unit"))

import las_rev_judge as judge  # noqa: E402
import las_rev_targeted as rev  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

from outrigger_sim.control import c2  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

KEY_T1 = "D1|H-R-A|rigid+J1@FR|T|diag-op|K1|VB|e0"


@pytest.fixture(scope="module")
def geometry():
    return c2.C2Geometry.from_params(load_params())


@pytest.fixture(autouse=True)
def clean_install():
    yield
    rev.uninstall()


# ------------------------------------------------------------------------------- candidates
def test_candidate_settings_from_the_preset():
    preset = rev.preset_las_settings()
    assert rev.CANDIDATES["P0"].settings_from(preset) is preset
    p53 = rev.CANDIDATES["P53"].settings_from(preset)
    assert p53.light_leg_fraction_of_F_min == 4.5 and p53.min_active_periods == 8
    assert replace(p53, light_leg_fraction_of_F_min=3.5, min_active_periods=0) == preset
    assert rev.CANDIDATES["P5"].settings_from(preset).min_active_periods == 0
    assert rev.CANDIDATES["P3"].settings_from(preset).light_leg_fraction_of_F_min == 3.5


def test_candidate_config_replaces_b0_keeps_the_candidate_and_refuses_others():
    preset_config = c2.C2Config().with_10hz_d1()
    preset = preset_config.liftoff_approach_slow
    candidate = rev.CANDIDATES["P3"]
    changed = rev.candidate_config(preset_config, candidate, preset)
    assert changed.liftoff_approach_slow.min_active_periods == 8
    assert rev.candidate_config(changed, candidate, preset) is changed  # a rebuilt controller
    off = c2.C2Config()
    assert rev.candidate_config(off, candidate, preset) is off
    other = replace(preset_config, liftoff_approach_slow=replace(preset, rho_on=0.2))
    with pytest.raises(RuntimeError):
        rev.candidate_config(other, candidate, preset)


def test_install_candidate_reaches_every_controller(geometry):
    rev.install_candidate(rev.CANDIDATES["P53"])
    controller = c2.C2Controller.from_params(load_params(), c2.C2Config().with_10hz_d1())
    settings = controller.config.liftoff_approach_slow
    assert settings.light_leg_fraction_of_F_min == 4.5 and settings.min_active_periods == 8
    assert c2.C2Controller(geometry).config.liftoff_approach_slow.enable is False
    with pytest.raises(RuntimeError):
        rev.install_candidate(rev.CANDIDATES["P5"])
    rev.uninstall()
    plain = c2.C2Controller(geometry, c2.C2Config().with_10hz_d1())
    assert plain.config.liftoff_approach_slow.light_leg_fraction_of_F_min == 3.5


# ------------------------------------------------------------------------------- DONE record
def _ready_outputs(geometry, is_recording: bool):
    from test_c2_r8d1 import bench_config, ready_bench

    if is_recording:
        rev.install_done_recorder()
    bench = ready_bench(geometry, bench_config())
    return bench


def test_done_recorder_keeps_the_commands_and_fills_the_trace(geometry):
    recorded = _ready_outputs(geometry, True)
    rev.uninstall()
    plain = _ready_outputs(geometry, False)
    assert len(recorded.outputs) == len(plain.outputs)
    for got, want in zip(recorded.outputs, plain.outputs, strict=True):
        assert np.asarray(got).tobytes() == np.asarray(want).tobytes()
    assert recorded.controller.phase is plain.controller.phase is c2.C2Phase.READY
    rows, clock = rev.done_blocks(recorded.controller)
    assert rows and rows[0]["loc_ok"] is True  # soil response off on the bench: no LOC gate
    level_rows = [row for row in rows if row["level_step"] and row["phase_before"] == "level"]
    assert all(row["twist_path"] in ("relax", "plain") for row in level_rows)
    assert all(isinstance(row["ref_on_target"], bool) for row in level_rows)
    assert clock["t_first_done_s"] is not None and clock["t_first_ready_s"] is not None
    assert clock["clock_starts_s"] and clock["loss_s"] >= 0.0
    assert rows[-1]["t_s"] <= clock["t_first_ready_s"] + rev.READY_TAIL_S + 1e-9
    done_row = next(row for row in rows if row["phase"] == "done")
    assert done_row["complete_since_s"] is not None


def _row(t_s, since, **values):
    base = {"t_s": t_s, "phase": "level", "complete_since_s": since, "loc_ok": True,
            "ref_on_target": True, "attitude_in_band": True, "clearance_done": True,
            "twist_ok": True, "diff_sink_hold": False, "reapproaching": False}
    return {**base, **values}


def test_done_clock_counts_restarts_after_the_last_loc():
    rows = [_row(10.0, None, loc_ok=False), _row(10.1, None, attitude_in_band=False),
            _row(10.2, 10.2), _row(10.3, 10.2), _row(10.4, None, twist_ok=False),
            _row(10.5, None, reapproaching=True), _row(10.6, 10.6), _row(11.6, 10.6,
                                                                         phase="done")]
    clock = rev.done_clock_of(rows, [10.1], 11.6)
    assert clock["t_loc_last_before_done_s"] == 10.1
    assert clock["clock_starts_s"] == [10.2, 10.6]
    assert clock["resets"] == [{"t_s": 10.4, "names": ["twist_ok"]}]
    assert clock["loss_s"] == pytest.approx(0.4)
    assert rev.reset_names(_row(1.0, None, reapproaching=True, phase="reanchor")) == [
        "reapproaching", "phase:reanchor"]
    assert rev.done_clock_of(rows, [10.1], None)["loss_s"] is None


def test_done_row_early_return_and_paths():
    thresholds = c2.C2Config().with_10hz_d1().thresholds
    early = rev.done_row(1.0, "level", "level", {"completion": {"since_after": None,
                                                                 "twist_load_N": 0.0},
                                                 "values": {}, "level_ran": True}, thresholds)
    assert early["loc_ok"] is False and early["complete_now"] is False
    assert early["ref_on_target"] is None and early["twist_ok"] is None
    period = {"completion": {"since_after": 1.0, "twist_load_N": 1e9},
              "values": {"ref_on_target": True, "deviation_rad": 0.0,
                         "clearance_done": True}, "level_ran": True, "since_after_level": 1.0}
    plain = rev.done_row(1.0, "level", "level", period, thresholds)
    assert plain["twist_path"] == "plain" and plain["twist_ok"] is False
    assert plain["complete_now"] is True and plain["attitude_in_band"] is True
    no_level = rev.done_row(1.0, "ready", "ready", {}, thresholds)
    assert no_level["loc_ok"] is None and no_level["level_step"] is False


# ------------------------------------------------------------------------------- tool helpers
def test_default_out_and_out_path(tmp_path):
    assert rev.default_out("R-G", ("P5", "P3", "P53"), judge.GRID_CANDIDATES).name == (
        "rev_RG.jsonl")
    assert rev.default_out("R-T", ("P5",), None).name == "rev_RT_P5.jsonl"
    assert rev.out_path_problem(rev.ROOT / "x.jsonl") is not None
    existing = tmp_path / "a.jsonl"
    existing.write_text("", encoding="utf-8")
    assert rev.out_path_problem(existing) is not None
    assert rev.out_path_problem(tmp_path / "b.jsonl") is None


def test_resolve_candidates():
    assert rev.resolve_candidates("R-G", None) == ("P5", "P3", "P53")
    assert rev.resolve_candidates("R-0", None) == ("P0",)
    with pytest.raises(ValueError):
        rev.resolve_candidates("R-T", None)
    with pytest.raises(ValueError):
        rev.resolve_candidates("R-T", "P0")
    assert rev.resolve_candidates("R-S", "P53") == ("P53",)


def test_identity_problems():
    identity = {"dirty_files": [".gitattributes"], "code_diff_sha256": rev.fb.EMPTY_SHA256,
                "threads": {name: "1" for name in rev.fb.THREAD_VARIABLES}}
    assert rev.identity_problems(identity) == []
    bad = {**identity, "dirty_files": ["03_src/x.py"], "code_diff_sha256": "0" * 64}
    assert len(rev.identity_problems(bad)) == 2


# ------------------------------------------------------------------------------- judge
def _d1(verdict="pass", items=None, fail_items=(), F=12e3, ready=60.0, stroke=0.5):
    return {"verdict": verdict, "fail_items": list(fail_items), "F_judged_min_N": F,
            "items": items or {"READY": True, "G6-2_loc": True}, "t_ready_s": ready,
            "stroke_max_m": stroke}


def _line(sha="a" * 64, d1=None, events=None, phase="ready", **extra):
    out = {"job": {"d1": {}}, "commands_sha256": sha, "final_phase": phase,
           "event_names": events or {}, "d1": d1 or _d1()}
    return {**out, **extra}


def test_pair_violations():
    l_line = _line(sha="l" * 64)
    assert judge.pair_violations(_line(), l_line) == []
    worse = _line(d1=_d1("fail", {"READY": True, "G6-2_loc": False}, ["G6-2_loc"]),
                  events={"WARN_X:FL": 1, "INFO_Y": 2}, phase="fault")
    found = judge.pair_violations(worse, l_line)
    assert any("verdict" in text for text in found)
    assert any("G6-2_loc" in text for text in found)
    assert any("WARN_X" in text for text in found)
    assert any("final_phase" in text for text in found)
    none_l = _line(sha="l" * 64, d1=_d1(items={"READY": None, "G6-2_loc": True}))
    assert judge.pair_violations(_line(d1=_d1(items={"READY": False, "G6-2_loc": True})),
                                 none_l)
    case = {"job": {"case": "R12"}, "commands_sha256": "b", "final_phase": "ready",
            "event_names": {}, "values": {"times": {"t_first_ready_s": 40.0}}}
    late = {**case, "values": {"times": {"t_first_ready_s": None}}}
    assert judge.pair_violations(late, case) == ["READY time -> None"]


def test_items_key_union_rev1():
    """rev1 R1-1 / R1-2: a key on one side only reads None on the other."""
    l_line = _line(sha="l" * 64)
    harness = _line(d1=_d1(items={"READY": True, "G6-2_loc": True,
                                  "harness_stroke_limited_fail": False}))
    assert judge.pair_violations(harness, l_line) == [
        "item harness_stroke_limited_fail None -> False"]
    assert judge.items_only(harness, l_line) == {
        "items_only_L": [], "items_only_cand": ["harness_stroke_limited_fail"]}
    l_p3 = _line(sha="l" * 64, d1=_d1(items={"READY": True, "P3-1": True}))
    dropped = _line(d1=_d1(items={"READY": True}))
    assert judge.pair_violations(dropped, l_p3) == ["item P3-1 True -> None"]
    assert judge.items_only(dropped, l_p3)["items_only_L"] == ["P3-1"]
    l_false = _line(sha="l" * 64, d1=_d1(items={"READY": True, "P3-1": False}))
    assert judge.pair_violations(dropped, l_false) == []
    extra_true = _line(d1=_d1(items={"READY": True, "P3-1": False, "X": True}))
    assert judge.pair_violations(extra_true, l_false) == []


def test_h4_only_without_items_or_with_equal_hash_drift():
    """rev1 R1-3."""
    l_line = _line(sha="s" * 64)
    drift = _line(sha="s" * 64, d1=_d1(items={"READY": True}))
    with pytest.raises(judge.MissingField):
        judge.pair_violations(drift, l_line)
    value_drift = _line(sha="s" * 64, d1=_d1(items={"READY": True, "G6-2_loc": None}))
    with pytest.raises(judge.MissingField):
        judge.pair_violations(value_drift, l_line)
    assert judge.pair_violations(_line(sha="s" * 64), l_line) == []
    no_items = _line(d1={k: v for k, v in _d1().items() if k != "items"})
    with pytest.raises(judge.MissingField):
        judge.pair_violations(no_items, l_line)
    no_d1 = {k: v for k, v in _line().items() if k != "d1"}
    with pytest.raises(judge.MissingField):
        judge.pair_violations(no_d1, l_line)


def test_sealed_rules_include_rev1():
    names = [path.name for path, _, _ in judge.SEALED_RULES]
    assert names == ["las_rev_targeted_rules.md", "las_rev_targeted_rules_rev1.md"]
    assert judge.sealed_rules_problems() == []


def _pairs(*deltas, exception_keys=()):
    pairs = {}
    for index, delta in enumerate(deltas):
        key = f"k{index}"
        pair = {"changed": delta is not None, "dt_s": delta}
        if key in exception_keys:
            pair["exception"] = {"is_exception": True}
        pairs[key] = pair
    return pairs


def test_ready_population_empty_set_rules():
    same = {"k0": {"changed": False, "dt_s": 0.0}, "k1": {"changed": False, "dt_s": 0.0}}
    assert judge.ready_population(same)["R-1"] is True
    excepted = _pairs(3.0, exception_keys=("k0",))
    assert judge.ready_population(excepted)["R-1"] is None
    result = judge.ready_population(_pairs(0.5, 1.5, 0.2, 6.0, exception_keys=("k3",)))
    assert result["population"] == 3 and result["median_s"] == pytest.approx(0.5)
    assert result["R-1"] is True and result["R-2"] is True
    assert judge.ready_population(_pairs(2.0, 3.0))["R-1"] is False


def _clock(loss, resets=(), starts=(30.0, 32.0)):
    return {"loss_s": loss, "resets": list(resets), "clock_starts_s": list(starts),
            "t_loc_last_before_done_s": 25.0}


def test_exception_record():
    l_line = {**_line(sha="l" * 64, d1=_d1(ready=60.0))}
    cand = _line(d1=_d1(ready=63.0), done_clock=_clock(2.6, [{"t_s": 31.0, "names": []}]),
                 las={"start_t_s": 22.0, "end_t_s": 23.0})
    rx = {"commands_sha256": "l" * 64, "done_clock": _clock(0.0)}
    assert judge.exception_record(cand, l_line, rx)["is_exception"] is True
    assert judge.exception_record(cand, l_line, None)["is_exception"] is False
    small = {**cand, "done_clock": _clock(2.0, [{"t_s": 31.0, "names": []}])}
    assert judge.exception_record(small, l_line, rx)["reason"] == "E < 0.8 dt"
    early = {**cand, "las": {"start_t_s": 22.0, "end_t_s": 31.5}}
    assert judge.exception_record(early, l_line, rx)["is_exception"] is False
    other = {**rx, "commands_sha256": "x" * 64}
    assert judge.exception_record(cand, l_line, other).get("h5") is True


def _rev_line(candidate, point, sha, start, f_rl=11.0, f_judged=11.0, active=9, end="sum",
              setting=None):
    beta, n_min = judge.CANDIDATE_VALUES[candidate]
    setting = setting or point[0]
    return {"job": {"setting": setting, "d1": {}}, "commands_sha256": sha,
            "las": {"start_t_s": start, "active_periods": active, "end_reason": end,
                    "params": {"beta": beta, "n_min": n_min}},
            "rev": {"bundle": "R-G", "candidate": candidate, "key": "k",
                    "label": f"{candidate}-LT", "grid_point": [point[1], point[2]],
                    "settings": {"light_leg_fraction_of_F_min": beta,
                                 "min_active_periods": n_min},
                    "settings_match": True, "rules_sha256": judge.RULES_SHA256,
                    "controller_tag": "final_C4G2_LAS",
                    "identity": {"git_head": "c0", "code_diff_sha256": judge.EMPTY_SHA256,
                                 "dirty_files": [".gitattributes"],
                                 "rules_rev1_sha256": judge.RULES_REV1_SHA256}},
            "controller_tag": "final_C4G2_LAS",
            "diag": {"summary": {"F_RL_kN": f_rl, "F_judged_min_kN": f_judged,
                                 "gate_consistent": True, "las_start_period": 6,
                                 "t_lift_s": 23.0, "min_leg_after_lift": "RL"},
                     "touch_budget": {"level_budget_periods": 0}}}


def _grid(candidate, f_rl=11.0):
    lines = []
    for point, (sha, b0_start) in judge.D_B_LINES.items():
        predicted = judge.K2_PREDICTED_START_S.get(point)
        start = b0_start if predicted is None or candidate == "P3" else predicted
        lines.append(_rev_line(candidate, point, sha, start, f_rl=f_rl + 0.01 * point[2]))
    return lines


def test_k_problems_on_the_grid():
    line = _rev_line("P5", ("V0", "1", 1), "z" * 64, 20.9)
    assert judge.k_problems(line, None) == []
    late = _rev_line("P5", ("V0", "1", 1), "z" * 64, 21.1)
    assert any(text.startswith("K-2") for text in judge.k_problems(late, None))
    p3 = _rev_line("P3", ("V0", "1", 1), "z" * 64, 21.1)
    assert judge.k_problems(p3, None) == []
    group_a = _rev_line("P53", ("VB", "1", 0), "z" * 64, 22.4)
    assert any(text.startswith("K-1") for text in judge.k_problems(group_a, None))
    short = _rev_line("P3", ("V0", "1", 1), "z" * 64, 21.1, active=5)
    assert any("sum end" in text for text in judge.k_problems(short, None))
    unmatched = {**line, "rev": {**line["rev"], "settings_match": False}}
    assert judge.k_problems(unmatched, None)


def test_judge_grid_pass_and_failures():
    result = judge._grid_lines(_grid("P5"))["P5"]
    graded = judge.judge_grid(result)
    assert graded["pass"] and graded["G-3"] and len(graded["cells"]) == 6
    low = judge.judge_grid(judge._grid_lines(_grid("P5", f_rl=10.0))["P5"])
    assert not low["G-1"] and not low["pass"]
    missing = judge.judge_grid(judge._grid_lines(_grid("P5")[1:])["P5"])
    assert not missing["G-3"]


def test_judge_with_the_grid_only_and_identity():
    lines = _grid("P5") + _grid("P3")
    result = judge.judge(lines, {})
    assert result["candidates"]["P5"]["verdict"] == "incomplete"
    assert result["identity"] == {}
    lines[0]["rev"]["identity"] = {**lines[0]["rev"]["identity"], "git_head": "c1"}
    lines[1]["rev"]["identity"] = {**lines[1]["rev"]["identity"], "dirty_files": ["03_src/a"]}
    result = judge.judge(lines, {})
    problems = result["identity"]["P5"]
    assert any("2 commits" in text for text in problems)
    assert any("dirty" in text for text in problems)
    assert result["candidates"]["P5"]["verdict"] == "undecidable"
    assert any(text.startswith("H-4") for text in result["stops"])


def test_grid_outcome_order():
    """G-4 / H-3 stop and G-3 undecidable come before a G-1 / G-2 fail."""
    lines = _grid("P5", f_rl=10.0)[1:]  # G-1 short and a line missing
    assert judge.judge(lines, {})["candidates"]["P5"]["verdict"] == "undecidable"
    k_lines = _grid("P5", f_rl=10.0)
    group_a = next(line for line in k_lines
                   if tuple(judge.grid_point_of(line)) == ("VB", "1", 0))
    group_a["commands_sha256"] = "z" * 64  # K-1 mismatch, then the run stops the candidate
    result = judge.judge(k_lines[:-5], {})
    assert result["grid"]["P5"]["status"] == judge.GRID_STOP
    assert result["candidates"]["P5"]["verdict"] == "stop"
    short = judge.judge(_grid("P5", f_rl=10.0), {})
    assert short["candidates"]["P5"]["verdict"] == "fail"
    assert judge.grid_status(True, False, False) == judge.GRID_FAIL


def test_h6_counts_g1_g2_failures_only():
    undecided = [line for name in judge.GRID_CANDIDATES for line in _grid(name)[1:]]
    result = judge.judge(undecided, {})
    assert all(v["verdict"] == "undecidable" for v in result["candidates"].values())
    assert not any(text.startswith("H-6") for text in result["stops"])
    failed = [line for name in judge.GRID_CANDIDATES for line in _grid(name, f_rl=10.0)]
    assert any(text.startswith("H-6") for text in judge.judge(failed, {})["stops"])


def test_controller_tag_and_rev1_identity():
    line = _grid("P5")[0]
    assert judge.tag_problems(line) == []
    other = {**line, "controller_tag": "final_C4G2"}
    assert judge.tag_problems(other)
    lines = _grid("P5")
    lines[0] = other
    lines[1]["rev"]["identity"] = {**lines[1]["rev"]["identity"], "rules_rev1_sha256": None}
    problems = judge.judge(lines, {})["identity"]["P5"]
    assert any("controller_tag" in text for text in problems)
    assert any("rev1" in text for text in problems)


def test_earlier_identity_problems(tmp_path):
    current = {"git_head": "c0", "sha256": {"a.py": "1"}}
    assert rev.earlier_identity_problems("R-G", current, tmp_path) == []
    assert rev.earlier_identity_problems("R-T", current, tmp_path)  # no rev_RG file
    line = {"rev": {"key": "k", "identity": {"git_head": "c0", "sha256": {"a.py": "1"}}}}
    (tmp_path / "rev_RG.jsonl").write_text(json.dumps(line) + "\n", encoding="utf-8")
    assert rev.earlier_identity_problems("R-T", current, tmp_path) == []
    moved = {"rev": {"key": "k2", "identity": {"git_head": "c1", "sha256": {"a.py": "1"}}}}
    (tmp_path / "rev_RT_P5.jsonl").write_text(json.dumps(moved) + "\n", encoding="utf-8")
    assert rev.earlier_identity_problems("R-S", current, tmp_path) == [
        "rev_RT_P5.jsonl k2: git_head"]


def test_rank_rules():
    grid = {"P5": {"min_F_judged_kN": 11.0}, "P3": {"min_F_judged_kN": 11.2},
            "P53": {"min_F_judged_kN": 12.0}}
    t_res = {name: {"ready": {"changed": 3, "median_s": 0.1}} for name in grid}
    s_res = {name: {"pairs": {}} for name in grid}
    assert judge.rank(["P5", "P3", "P53"], grid, t_res, s_res)[0] == "P53"
    grid["P53"]["min_F_judged_kN"] = 11.1
    t_res["P3"]["ready"]["changed"] = 1
    assert judge.rank(["P5", "P3", "P53"], grid, t_res, s_res)[0] == "P3"
    t_res["P3"]["ready"]["changed"] = 3
    assert judge.rank(["P53", "P3", "P5"], grid, t_res, s_res)[0] == "P5"


def test_seal_problems(tmp_path):
    rules = tmp_path / "r.md"
    rules.write_bytes(b"a\r\nb\n")
    digest = judge.lf_sha256(rules)
    seal = tmp_path / "r.sha256"
    seal.write_text(f"{digest}  r.md  sealed\n", encoding="utf-8")
    assert judge.seal_problems(rules, seal, digest) == []
    assert judge.seal_problems(rules, seal, "0" * 64)
    assert judge.seal_problems(tmp_path / "none.md", seal, digest)


def test_r0_table_and_rules_constants():
    assert len(judge.R0_EXPECTED) == 6
    assert judge.R0_EXPECTED[(KEY_T1, "P0")] == rev.fb.S1_STORED_HASHES[KEY_T1]
    group_b = [point for point in judge.D_B_LINES if point in judge.K2_PREDICTED_START_S]
    assert len(judge.D_B_LINES) == 30 and len(group_b) == 12
    assert judge.C1_FORCE_FLOOR_N == pytest.approx(10414.589)
