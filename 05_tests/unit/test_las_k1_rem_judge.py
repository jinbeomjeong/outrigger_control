"""Unit tests of ``las_k1_rem_judge.py`` on synthetic result.json documents (no Chrono, no git).

Tests 1-11 follow ``las_k1_rules_adopt2.md`` 9.1; the last test checks the stdlib ``.npy`` reader
against numpy. A full synthetic batch (10 rows that pass every K check, grade ``통과``) is built
first; each test changes the rows it needs.

Run (dynamics-dev, PowerShell, project root):
  $env:PYTHONDONTWRITEBYTECODE = '1'
  C:\\ProgramData\\miniforge3\\envs\\dynamics-dev\\python.exe -I -m pytest -q -p no:cacheprovider
      05_tests/unit/test_las_k1_rem_judge.py
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JUDGE_PATH = PROJECT_ROOT / "06_analysis/02_control/verif_matrix/scripts/las_k1_rem_judge.py"
_SPEC = importlib.util.spec_from_file_location("las_k1_rem_judge", JUDGE_PATH)
judge = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = judge  # dataclasses look the module up while the class is built
_SPEC.loader.exec_module(judge)

HEAD = "a" * 40
TOOL_SHA = "b" * 64
AUDIT_SHA = "c" * 64
FORCED_SHA = "d" * 64
FILE_SHA = "e" * 64
FORCED_CLASS = "k1_forced_block.K1ForcedBlockC2Controller"
APPLIED_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN:80"
SKIP_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order"
VB_ARGV = [
    "--flow-eta-v",
    "0.85",
    "--flow-dp-comp-bar",
    "5",
    "--flow-dp-unload-bar",
    "3",
    "--flow-width-bar",
    "2",
    "--flow-law",
    "proportional",
    "--valve-tau-s",
    "0.1",
    "--rod-release-force",
    "--lock-overlap-ratio",
    "0.02",
    "--lock-closing-delay-s",
    "0.05",
    "--lock-window-follows-plant",
    "--extend-start-tracked",
]
VB_ARGS = {
    "flow_eta_v": 0.85,
    "flow_dp_comp_bar": 5.0,
    "flow_dp_unload_bar": 3.0,
    "flow_width_bar": 2.0,
    "flow_law": "proportional",
    "valve_tau_s": 0.1,
    "rod_release_force": True,
    "lock_overlap_ratio": 0.02,
    "lock_closing_delay_s": 0.05,
    "lock_window_follows_plant": True,
    "extend_start_tracked": True,
}
SHAPE_BY_MASS = {
    # (soil-mode start, plateau start, LOC): dP +103 (x1.0), +204 (J2 x1.1), +143 (J1 x1.1)
    ("J2", 1.0): (33.2, 43.5, 45.1),
    ("J2", 1.1): (33.3, 53.7, 55.3),
    ("J1", 1.1): (33.3, 47.6, 49.2),
}


# ---------------------------------------------------------------- synthetic rows
def decision(
    t_loc: float,
    t_P: float | None,
    t_S: float | None,
    *,
    r4_due: bool = True,
    would_block: bool = False,
    applied: bool = True,
) -> dict[str, Any]:
    n_P = judge.period_of(t_P)
    n_S = judge.period_of(t_S)
    return {
        "t_loc_s": t_loc,
        "t_P_s": t_P,
        "t_S_s": t_S,
        "n_P": n_P,
        "n_S": n_S,
        "dP": None if n_P is None or n_S is None else n_P - n_S,
        "r4_due_without_gate": r4_due,
        "would_block": would_block,
        "applied": applied,
    }


def argv_of(spec: Any) -> list[str]:
    argv = [
        "python.exe",
        "-I",
        "run_S9.py",
        "level",
        "--soil",
        spec.soil,
        "--pad-variant",
        "dwg_rear250",
        "--level",
        spec.level,
        "--threads",
        "4",
        "--duration",
        "120",
    ]
    if spec.setting == "VB":
        argv += VB_ARGV
    argv += ["--k1-order-gate", spec.gate]
    if spec.forced != "off":
        argv += ["--k1-forced-block", spec.forced]
    if spec.mass_scale != 1.0:
        argv += ["--mass-scale", f"{spec.mass_scale:g}"]
    return [*argv, "--expect-controller", spec.tag, "--case", spec.case]


def base_story(spec: Any) -> dict[str, Any]:
    """One LOC: soil mode, plateau, LOC with R4c30 applied (gate on: not blocked, dP > 0)."""
    t_S, t_P, t_loc = SHAPE_BY_MASS[(spec.soil, spec.mass_scale)]
    story: dict[str, Any] = {
        "mode_starts": [t_S],
        "events": [
            (t_S, "soil_mode_start"),
            (t_loc, "crawler_liftoff_confirmed"),
            (t_loc, APPLIED_EVENT),
        ],
        "decisions": [decision(t_loc, t_P, t_S)],
        "revokes": [],
    }
    if spec.forced != "off":  # forced block at L1, then a revocation and a structural-zero re-LOC
        t_revoke, t_restart, t_reloc = t_loc + 0.3, t_loc + 0.4, t_loc + 1.4
        story["events"] = [
            (t_S, "soil_mode_start"),
            (t_loc, "crawler_liftoff_confirmed"),
            (t_loc, SKIP_EVENT),
            (t_revoke, "INFO_LOC_REVOKED:3.1"),
            (t_restart, "soil_mode_start"),
            (t_reloc, "crawler_liftoff_confirmed"),
            (t_reloc, SKIP_EVENT),
        ]
        story["mode_starts"] = [t_S, t_restart]
        story["decisions"] = [
            decision(t_loc, t_P, t_S, would_block=True, applied=False),
            decision(t_reloc, t_restart, t_restart, would_block=True, applied=False),
        ]
        story["revokes"] = [t_revoke]
    return story


def result_of(spec: Any, story: dict[str, Any]) -> dict[str, Any]:
    is_forced = spec.forced != "off"
    class_name = FORCED_CLASS if is_forced else "outrigger_sim.control.c2.C2Controller"
    args = {
        **judge.FIXED_ARGS,
        "case": spec.case,
        "soil": spec.soil,
        "level": spec.level,
        "mass_scale": spec.mass_scale,
        "k1_order_gate": spec.gate,
        "k1_forced_block": spec.forced,
        "expect_controller": spec.tag,
        "floor_roll": 0.0,
        "floor_pitch": 0.0,
        **(VB_ARGS if spec.setting == "VB" else {k: None for k in VB_ARGS}),
    }
    meta: dict[str, Any] = {
        "period_s": 0.1,
        "soil": {
            "restored_from": None,
            "mode_starts": [{"t_s": t, "source": "release"} for t in story["mode_starts"]],
        },
        "slope_clearance_margin": {
            "order_gate": {"enabled": spec.gate == "on", "decisions": story["decisions"]}
        },
        "loc_revoke": {
            "settings": {"keep_slope_margin_on_revoke": True, "max_revokes": 2},
            "t_revoke_s": list(story["revokes"]),
        },
    }
    if is_forced:
        first = story["decisions"][0]
        meta["k1_forced_block"] = {
            "mode": "first",
            "class": FORCED_CLASS,
            "module_sha256": FORCED_SHA,
            "forced_t_loc_s": first["t_loc_s"],
            "forced_n_loc": judge.period_of(first["t_loc_s"]),
            "natural_blocked": False,
            "n_P": first["n_P"],
            "n_S": first["n_S"],
            "dP": first["dP"],
            "calls": [{"t_s": first["t_loc_s"], "forced": True, "result": True}],
        }
    return {
        "args": args,
        "num_threads_chrono": 4,
        "placement": {"mode": "pcore", "affinity_ok": True, "power_throttling_off_ok": True},
        "hull_hook": {
            "mode": "fast",
            "requested": "fast",
            "fallback_reason": None,
            "dll_sha256": judge.DLL_SHA256,
        },
        "code_state": {
            "git_at_start": {"head": HEAD, "dirty": []},
            "files_at_start": {
                module: {"sha256": FILE_SHA} for module, _ in judge.RECORDED_CONTROLLER_FILES
            },
        },
        "c2_setup": {
            "expect_controller": {"ok": True},
            "k1_order_gate": spec.gate,
            "k1_forced_block": {
                "requested": spec.forced,
                "class": class_name,
                "module_sha256": FORCED_SHA,
            },
        },
        "controller_meta": meta,
        "events": [{"t_s": t, "name": n} for t, n in story["events"]],
        "phases": [{"t_s": 8.0, "phase": "check"}, {"t_s": 90.0, "phase": "ready"}],
        "p3b": {"P3-5_clearance_stroke": {"s_motor_max_m": [0.5, 0.51, 0.49, 0.5]}},
        "p3b_ext": {"crawler_gap": {"grid_end_m": 0.08}},
    }


def entry_of(spec: Any) -> dict[str, Any]:
    return {
        "case": spec.case,
        "argv": argv_of(spec),
        "rc": 0,
        "pool": "pcore",
        "omp_wait_policy": "PASSIVE",
        "hull_hook_requested": "fast",
        "hull_hook_effective": {"mode": "fast"},
        "code_at_launch": {
            "files": {path: FILE_SHA for _, path in judge.RECORDED_CONTROLLER_FILES}
        },
    }


def identity_record() -> dict[str, Any]:
    files = {
        path: {"worktree_sha256": FILE_SHA, "blob_sha256": FILE_SHA} for path in judge.K2_CODE_FILES
    }
    files[judge.FORCED_BLOCK_PATH]["worktree_sha256"] = FORCED_SHA
    return {
        "tool": {"sha256": TOOL_SHA},
        "head": {"sha": HEAD, "ok": True},
        "git_status": {"ok": True, "allowed": []},
        "code_files": {"ok": True, "files": files, "c2_base_blob_sha256": FILE_SHA},
        "dll": {"sha256": judge.DLL_SHA256},
        "rules": {"sha256": judge.RULES_SHA256},
        "audit_report": {"sha256": AUDIT_SHA, "path": "audit.md"},
    }


def make_inputs(stories: dict[str, dict[str, Any]] | None = None) -> Any:
    """The full 10-row batch; ``stories`` replaces the story of the named rows."""
    stories = stories or {}
    rows = {}
    for spec in judge.ROW_SPECS:
        story = stories.get(spec.rem_key) or base_story(spec)
        rows[spec.rem_key] = judge.RowInput(spec, result_of(spec, story), entry_of(spec))
    prelaunch = {
        **identity_record(),
        "batch_plan": {"planned_pool": {s.case: "pcore" for s in judge.ROW_SPECS}},
    }
    postrun = {**identity_record(), "code_diff_since_prelaunch": {"quiet": True}}
    return judge.JudgeInputs(
        rows=rows,
        batch={"cases": [r.entry for r in rows.values()], "mixed_hull_mode": False},
        prelaunch=prelaunch,
        postrun=postrun,
        rules={"ok": True, "sha256": judge.RULES_SHA256},
        tool_sha256=TOOL_SHA,
        expect_tool_sha256=TOOL_SHA,
        audit_sha256_now=AUDIT_SHA,
        code_diff_quiet=lambda base, head: True,
    )


def run(inputs: Any) -> dict[str, Any]:
    return judge.judge(inputs)


def mark_missing(inputs: Any, key: str, rc: int = 1) -> None:
    row = inputs.rows[key]
    row.entry["rc"] = rc
    row.missing_reasons = judge.missing_reasons_of(row.result, row.entry)


def failed_k(doc: dict[str, Any]) -> list[str]:
    return [c["id"] for c in doc["k_checks"] if c["ok"] is False]


def story_with(spec_key: str, **changes: Any) -> dict[str, Any]:
    story = base_story(judge.SPEC_BY_KEY[spec_key])
    story.update(changes)
    return story


def late_struct_story(spec_key: str, *, gate_on: bool) -> dict[str, Any]:
    """Path ②: the first LOC is no R4 LOC; revocation, soil-mode restart, re-LOC with t_P = t_S."""
    t_S = 33.2
    t_loc, t_revoke, t_restart, t_reloc = 40.0, 40.3, 40.4, 41.4
    r4_event = SKIP_EVENT if gate_on else APPLIED_EVENT
    return story_with(
        spec_key,
        mode_starts=[t_S, t_restart],
        events=[
            (t_S, "soil_mode_start"),
            (t_loc, "crawler_liftoff_confirmed"),
            (t_revoke, "INFO_LOC_REVOKED:3.1"),
            (t_restart, "soil_mode_start"),
            (t_reloc, "crawler_liftoff_confirmed"),
            (t_reloc, r4_event),
        ],
        decisions=[
            decision(t_loc, 39.0, t_S, r4_due=False, applied=False),
            decision(t_reloc, t_restart, t_restart, would_block=True, applied=not gate_on),
        ],
        revokes=[t_revoke],
    )


def test_baseline_batch_passes() -> None:
    """Fixture check: the synthetic batch passes every K check (grade ``통과``)."""
    doc = run(make_inputs())
    assert failed_k(doc) == []
    assert doc["grade_provisional"] == judge.GRADE_PASS
    assert doc["k10"] is None and doc["provisional"] is True
    assert {doc["states"][k] for k in judge.GATEOFF_KEYS} == {judge.STATE_POS}
    assert doc["flags"]["GATEON_PATH"]["R7"]["outcome"] == judge.PATH_L1_APPLIED


# ---------------------------------------------------------------- 9.1 #1
def test_01_pos_nonpos_no_r4_missing() -> None:
    t_S, _, t_loc = SHAPE_BY_MASS[("J2", 1.0)]
    nonpos = story_with("R2", decisions=[decision(t_loc, t_S, t_S, would_block=True)])
    no_r4 = story_with(
        "R3",
        events=[(t_S, "soil_mode_start"), (t_loc, "crawler_liftoff_confirmed")],
        decisions=[decision(t_loc, 43.5, t_S, r4_due=False, applied=False)],
    )
    inputs = make_inputs({"R2": nonpos, "R3": no_r4})
    mark_missing(inputs, "R6")
    doc = run(inputs)
    states = doc["states"]
    assert (states["R1"], states["R2"], states["R3"], states["R6"]) == (
        judge.STATE_POS,
        judge.STATE_NONPOS,
        judge.STATE_NO_R4,
        judge.STATE_MISSING,
    )
    assert failed_k(doc) == []
    assert doc["grade_provisional"] == judge.GRADE_FAIL  # 미달 comes before 판정 불가
    assert doc["grade_reasons"] == ["MEASURED_NONPOS R2"]


# ---------------------------------------------------------------- 9.1 #2
@pytest.mark.parametrize(("reloc_t_P", "is_struct_zero"), [(45.5, True), (45.8, False)])
def test_02_struct_zero(reloc_t_P: float, is_struct_zero: bool) -> None:
    """A re-LOC with t_P = t_S = the restart is structural zero; a window cut after the restart
    (plateau 3 periods later, dP > 0) is not."""
    story = story_with(
        "R1",
        mode_starts=[33.2, 45.5],
        events=[
            (33.2, "soil_mode_start"),
            (45.1, "crawler_liftoff_confirmed"),
            (45.1, APPLIED_EVENT),
            (45.4, "INFO_LOC_REVOKED:3.1"),
            (45.5, "soil_mode_start"),
            (46.5, "crawler_liftoff_confirmed"),
        ],
        decisions=[
            decision(45.1, 43.5, 33.2),
            decision(46.5, reloc_t_P, 45.5, r4_due=False, applied=False),
        ],
        revokes=[45.4],
    )
    inputs = make_inputs({"R1": story})
    analysis = judge.analyze_row(inputs.rows["R1"])
    reloc = analysis.decisions[1]
    assert (reloc.is_post_revoke, reloc.restart_n) == (True, 455)
    assert reloc.is_struct_zero is is_struct_zero
    assert reloc.dP == (0 if is_struct_zero else 3)
    shadow = run(inputs)["flags"]["SHADOW_RELOC"]
    assert shadow["count"] == 1 and shadow["struct_zero"] == int(is_struct_zero)


# ---------------------------------------------------------------- 9.1 #3
def test_03_late_struct_is_fail_struct_zero() -> None:
    stories = {
        "R1": late_struct_story("R1", gate_on=False),
        "R7": late_struct_story("R7", gate_on=True),
    }
    doc = run(make_inputs(stories))
    assert failed_k(doc) == []
    assert doc["states"]["R1"] == judge.STATE_LATE_STRUCT
    assert doc["grade_provisional"] == judge.GRADE_FAIL
    assert doc["grade_reasons"] == ["STRUCT_ZERO R1"]


# ---------------------------------------------------------------- 9.1 #4
def test_04_two_r4_decisions_in_a_gate_off_row_stop() -> None:
    story = base_story(judge.SPEC_BY_KEY["R2"])
    story["events"] += [
        (46.0, "INFO_LOC_REVOKED:3.1"),
        (46.1, "soil_mode_start"),
        (47.1, "crawler_liftoff_confirmed"),
        (47.1, APPLIED_EVENT),
    ]
    story["mode_starts"].append(46.1)
    story["decisions"].append(decision(47.1, 46.5, 46.1))
    story["revokes"] = [46.0]
    doc = run(make_inputs({"R2": story}))
    assert "K-6" in failed_k(doc)
    assert doc["grade_provisional"] == judge.GRADE_STOP


# ---------------------------------------------------------------- 9.1 #5
def test_05_pair_l1_one_ulp_apart_stops() -> None:
    story = base_story(judge.SPEC_BY_KEY["R7"])
    story["decisions"][0]["t_P_s"] = math.nextafter(43.5, math.inf)
    doc = run(make_inputs({"R7": story}))
    assert judge.period_of(story["decisions"][0]["t_P_s"]) == 435  # same period, other float
    assert failed_k(doc) == ["K-7"]
    assert doc["grade_provisional"] == judge.GRADE_STOP


# ---------------------------------------------------------------- 9.1 #6
def test_06_gate_on_block_revoke_reevaluate_never() -> None:
    t_S, _, t_loc = SHAPE_BY_MASS[("J2", 1.0)]
    gate_off = story_with("R1", decisions=[decision(t_loc, t_S, t_S, would_block=True)])
    gate_on = story_with(
        "R7",
        mode_starts=[t_S, 45.5],
        events=[
            (t_S, "soil_mode_start"),
            (t_loc, "crawler_liftoff_confirmed"),
            (t_loc, SKIP_EVENT),
            (45.4, "INFO_LOC_REVOKED:3.1"),
            (45.5, "soil_mode_start"),
            (46.5, "crawler_liftoff_confirmed"),
            (46.5, SKIP_EVENT),
        ],
        decisions=[
            decision(t_loc, t_S, t_S, would_block=True, applied=False),
            decision(46.5, 45.5, 45.5, would_block=True, applied=False),
        ],
        revokes=[45.4],
    )
    doc = run(make_inputs({"R1": gate_off, "R7": gate_on}))
    assert failed_k(doc) == []
    path = doc["flags"]["GATEON_PATH"]["R7"]
    assert path["outcome"] == judge.PATH_NEVER
    assert [d["struct_zero"] for d in path["r4_decisions"]] == [False, True]
    assert doc["observed_block_revoke_reeval_in_judge_rows"] is True
    assert doc["grade_provisional"] == judge.GRADE_FAIL  # the gate-off twin is NONPOS


# ---------------------------------------------------------------- 9.1 #7
def test_07_skipped_order_is_not_an_applied_event() -> None:
    events = [
        (45.1, SKIP_EVENT),
        (45.1, "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED"),
        (46.0, APPLIED_EVENT),
    ]
    assert judge.periods_with_base(events, judge.MARGIN_EVENT) == [460]
    assert judge.periods_with_full(events, judge.SKIP_ORDER_EVENT) == [451]
    # a gate-on row whose L1 claims "applied" with only the skip event fails K-8 (e)
    story = base_story(judge.SPEC_BY_KEY["R7"])
    story["events"] = [
        (33.2, "soil_mode_start"),
        (45.1, "crawler_liftoff_confirmed"),
        (45.1, SKIP_EVENT),
    ]
    doc = run(make_inputs({"R7": story}))
    k8 = next(c for c in doc["k_checks"] if c["id"] == "K-8")
    assert k8["ok"] is False and "R7" in k8["rows"]
    assert doc["pairs"]["condition_3"]["pairs"]["R7"]["margin_event_at_L1"] is False


# ---------------------------------------------------------------- 9.1 #8
@pytest.mark.parametrize(("t_S_recorded", "is_ok"), [(33.2, True), (45.1, False)])
def test_08_same_period_soil_mode_start_is_not_t_S(t_S_recorded: float, is_ok: bool) -> None:
    story = story_with(
        "R1",
        mode_starts=[33.2, 45.1],  # a start in the LOC period itself
        events=[
            (33.2, "soil_mode_start"),
            (45.1, "soil_mode_start"),
            (45.1, "crawler_liftoff_confirmed"),
            (45.1, APPLIED_EVENT),
        ],
        decisions=[decision(45.1, 43.5, t_S_recorded)],
    )
    inputs = make_inputs({"R1": story})
    problems = judge.k8_row_problems(judge.analyze_row(inputs.rows["R1"]), False)
    assert (not any(p.startswith("(c)") for p in problems)) is is_ok


# ---------------------------------------------------------------- 9.1 #9
def test_09_undecidable_on_too_few_pos_or_no_mass_row() -> None:
    passing = [{"id": "K-0", "ok": True}]
    cond3 = {"ok": True, "pairs": {}}
    pos, no_r4 = judge.STATE_POS, judge.STATE_NO_R4
    three_pos = {"R1": pos, "R2": no_r4, "R3": no_r4, "R4": pos, "R5": pos, "R6": no_r4}
    grade, reasons, _ = judge.decide_grade(passing, three_pos, cond3)
    assert grade == judge.GRADE_UNDECIDABLE and reasons == ["POS 3 < 4"]
    no_mass = {"R1": pos, "R2": pos, "R3": pos, "R4": no_r4, "R5": no_r4, "R6": pos}
    grade, reasons, is_cond1 = judge.decide_grade(passing, no_mass, cond3)
    assert grade == judge.GRADE_UNDECIDABLE and reasons == ["R4 and R5 both NO_R4"]
    assert is_cond1 is False
    assert judge.EXIT_CODES[grade] == 1


# ---------------------------------------------------------------- 9.1 #10
def test_10_period_rounding() -> None:
    assert judge.period_of(34.95) == 350
    assert judge.period_of(34.85) == 348


# ---------------------------------------------------------------- 9.1 #11
def test_11_forced_paths() -> None:
    inputs = make_inputs()
    analyses = {k: judge.analyze_row(r) for k, r in inputs.rows.items()}
    record = judge.diagnostic_record(inputs, "F1", analyses)
    assert record["valid"] is True
    assert (record["FORCED_AT_L1"], record["FORCED_PAIR_L1"]) == (True, True)
    assert record["path"] == judge.FORCED_NEVER
    assert [r["struct_zero"] for r in record["reevaluations"]] == [True]

    no_revoke = story_with(
        "F1", decisions=[decision(45.1, 43.5, 33.2, would_block=True, applied=False)], revokes=[]
    )
    assert (
        judge.forced_path(judge.analyze_row(make_inputs({"F1": no_revoke}).rows["F1"]))["path"]
        == judge.FORCED_NO_REVOKE
    )

    late = base_story(judge.SPEC_BY_KEY["F2"])
    late["decisions"][1] = decision(56.7, 56.2, 55.7, would_block=False, applied=True)
    path = judge.forced_path(judge.analyze_row(make_inputs({"F2": late}).rows["F2"]))
    assert path["path"] == judge.FORCED_LATE and path["late_applied"]["dP"] == 5


@pytest.mark.parametrize("variant", ["missing", "garbage", "never_late"])
def test_11_variant_rows_never_change_the_grade(variant: str) -> None:
    baseline = run(make_inputs())
    inputs = make_inputs()
    if variant == "missing":
        mark_missing(inputs, "F1")
        inputs.rows["F2"].result = None
        inputs.rows["F2"].missing_reasons = ["result.json missing or unreadable"]
    elif variant == "garbage":  # invalid variant identity and meta
        for key in judge.DIAG_KEYS:
            inputs.rows[key].result["controller_meta"]["k1_forced_block"]["mode"] = "x"
            inputs.rows[key].result["hull_hook"]["mode"] = "off"
            inputs.rows[key].entry["argv"] = ["changed"]
    else:
        late = base_story(judge.SPEC_BY_KEY["F2"])
        late["decisions"][1] = decision(56.7, 56.2, 55.7, would_block=False, applied=True)
        inputs = make_inputs({"F2": late})
    doc = run(inputs)
    assert doc["grade_provisional"] == baseline["grade_provisional"] == judge.GRADE_PASS
    assert failed_k(doc) == []
    if variant == "garbage":
        assert doc["diag"]["F1"]["valid"] is False


def test_11_judge_row_with_forced_meta_stops() -> None:
    inputs = make_inputs()
    inputs.rows["R7"].result["controller_meta"]["k1_forced_block"] = {"mode": "first"}
    doc = run(inputs)
    assert "K-6" in failed_k(doc)
    assert doc["grade_provisional"] == judge.GRADE_STOP
    assert judge.EXIT_CODES[doc["grade_provisional"]] == 2


# ---------------------------------------------------------------- extra: stdlib npy reader
def test_extra_command_reader_matches_numpy(tmp_path: Path) -> None:
    np = pytest.importorskip("numpy")
    t_s = np.arange(5) * 0.1
    u = np.arange(20, dtype=float).reshape(5, 4) * 1e-3
    np.savez(tmp_path / "a.npz", t_s=t_s, issued_u_m_s=u)
    u_changed = u.copy()
    u_changed[3, 2] += 1e-9
    np.savez(tmp_path / "b.npz", t_s=t_s, issued_u_m_s=u_changed)
    first = judge.read_commands(tmp_path / "a.npz")
    second = judge.read_commands(tmp_path / "b.npz")
    expected = judge.sha256_bytes(t_s.astype("<f8").tobytes() + u.astype("<f8").tobytes())
    assert first.sha256 == expected
    assert judge.first_command_difference(first, second) == 3
    assert judge.first_command_difference(first, first) is None
