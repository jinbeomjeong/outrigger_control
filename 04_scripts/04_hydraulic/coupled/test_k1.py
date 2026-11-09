"""Tests of ``k1_targeted.py`` (K1 wrappers, jobs, gates) and ``k1_judge.py`` (rules 4).

The key lists are recomputed from the main checkout's stored files (read only; skipped when
they cannot be found); the judge runs on hand-made lines over a small synthetic key set; the
order-gate wrapper and the LOC witness on the real ``C2Controller`` (forced LOC benches of
``05_tests/unit/test_c2_k1.py``).
"""
from __future__ import annotations

import copy
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(ROOT / "05_tests" / "unit"))

import k1_judge as kj  # noqa: E402
import k1_targeted as kt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
from test_c2_k1 import bench_outputs, k1_config, loc_at  # noqa: E402

from outrigger_sim.control import c2  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

V5_RELATIVE = Path("06_analysis") / "03_hydraulic" / "coupled" / "v5"
KA1 = "D1|H-S-A|G1+J1@RL|T|flat|K1|VB|e0"
KA2 = "D1|H-S-0|J1|T|flat|K1|VB|e0"
KB1 = "D1|H-S-0|G1|T|flat|K1|VB|e0"
KC3 = "D1|H-S-0|J2|T|flat|K1|VB|e0"
KD1 = "D1|H-R-0|rigid|T|roll-op|K1|VB|e0"
PATCH, BOUNDARY = kj.J2_PATCH_KEY, kj.BOUNDARY_KEY
C_KEYS = sorted([PATCH, BOUNDARY, KC3])
SHA_OF = {"SC": "a" * 64, "RS": "b" * 64, "RT": "c" * 64, "F-3": "d" * 64}
IDENTITY = {"git_head": "f" * 40, "git_dirty": False, "dirty_files": [],
            "code_diff_sha256": kj.EMPTY_SHA256, "sha256": {"c2.py": "e" * 64},
            "budget_rule": "x", "threads": {**dict.fromkeys(kj.THREAD_VARIABLES, "1"),
                                            "MKL_THREADING_LAYER": "TBB"}}


# ------------------------------------------------------------------------------- main files
def main_v5_dir() -> Path | None:
    """The v5 folder holding the stored files: this checkout's, else the main checkout's."""
    if (ROOT / V5_RELATIVE / kj.BASE_FILES["SC"][0]).exists():
        return ROOT / V5_RELATIVE
    try:
        common = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--path-format=absolute",
                                 "--git-common-dir"], capture_output=True, text=True,
                                check=True, timeout=60).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    candidate = Path(common).parent / V5_RELATIVE
    return candidate if (candidate / kj.BASE_FILES["SC"][0]).exists() else None


@pytest.fixture(scope="module")
def main_bases() -> kj.Bases:
    v5_dir = main_v5_dir()
    if v5_dir is None:
        pytest.skip("stored base files not found (main checkout v5)")
    bases, problems = kj.load_bases(v5_dir)
    assert problems == []
    return bases


def test_lists_recomputed_from_the_main_files_are_the_appendix_lists(main_bases) -> None:
    assert {name: len(keys) for name, keys in main_bases.lists.items()} == kj.LIST_COUNTS
    for name, keys in main_bases.lists.items():
        assert kj.key_list_sha256(keys) == kj.LIST_SHA256[name]
    assert kj.list_problems(main_bases.lists) == []
    assert set(main_bases.lists["A5"]) <= set(main_bases.lists["A"])
    assert set(main_bases.lists["C_SB2"]) <= set(main_bases.lists["C"])


def test_list_bundles_on_the_main_files() -> None:
    v5_dir = main_v5_dir()
    if v5_dir is None:
        pytest.skip("stored base files not found (main checkout v5)")
    report, problems = kt.list_bundles(list(kj.BUNDLES), v5_dir)
    assert problems == []
    for bundle, count in kj.BUNDLE_COUNTS.items():
        assert any(text.startswith(f"{bundle}: {count} runs") for text in report)


def test_a_changed_list_mismatch_is_a_problem(main_bases) -> None:
    lists = {**main_bases.lists, "A5": main_bases.lists["A5"][:4]}
    assert any(text.startswith("list A5") for text in kj.list_problems(lists))


# ------------------------------------------------------------------------------- small facts
def test_period_numbers() -> None:
    assert kj.period_of(29.999999999975) == 300
    assert kj.period_of(None) is None
    assert kj.key_list_sha256(["b", "a"]) == kj.key_list_sha256(["a", "b"])


def test_rules_rev3_digest_is_the_diag_one() -> None:
    import las_revA_diag as diag

    assert kj.RULES_REVA_REV3_SHA256 == diag.RULES_REVA_REV3_SHA256
    assert kj.RULES_FIELDS[:6] == diag.RULES_FIELDS
    assert kj.seal_problems() == []


def test_identity_files_cover_the_inherited_harness() -> None:
    assert set(kt.IDENTITY_FILES) == {
        "c2.py", "fb_targeted.py", "las_targeted.py", "las_phase_diag.py", "las_rev_targeted.py",
        "las_rev_judge.py", "las_revA_targeted.py", "las_revA_judge.py", "las_revA_diag.py",
        "s2_defer_targeted.py", "s2_defer_judge.py", "k1_targeted.py", "k1_judge.py"}


# ------------------------------------------------------------------------------- synthetic set
def synthetic_bases() -> kj.Bases:
    def stored(key: str, sha: str) -> dict:
        return make_line(key, sha)

    bases = kj.Bases()
    bases.lists = {"A": sorted([KA1, KA2]), "A5": [KA1], "B": [KB1], "C": C_KEYS,
                   "C_SB2": sorted([PATCH, BOUNDARY]), "C_SA1": [PATCH], "D": [KD1]}
    bases.by_file = {"SC": {key: stored(key, f"sc-{key}") for key in (KA1, KA2, KB1)},
                     "RS": {key: stored(key, f"rs-{key}") for key in C_KEYS},
                     "RT": {KD1: stored(KD1, f"rt-{KD1}")}, "RP0": {}}
    bases.stored_l = {"F-3": {key: stored(key, f"l-{key}") for key in C_KEYS}}
    bases.sha256 = dict(SHA_OF)
    bases.paths = {name: Path(f"{name}.jsonl") for name in SHA_OF}
    return bases


def make_line(key: str, sha: str, *, stroke_m: float = 0.40, force_N: float = 60000.0) -> dict:
    return {"job": {"setting": "VB", "d1": {}}, "commands_sha256": sha, "final_phase": "ready",
            "controller_tag": "final_C4G2_P3_LAS", "event_names": {},
            "values": {"times": {"t_first_ready_s": 40.0}},
            "d1": {"key": key, "verdict": "pass", "fail_items": [],
                   "items": {"P3-1_crawler": True, "P3-5_gap": True}, "stroke_max_m": stroke_m,
                   "F_judged_min_N": force_N, "t_ready_s": 40.0},
            "rev": {"key": key, "controller_tag": "final_C4G2_P3_LAS"}}


def decision(d_p: int, *, due: bool = True, is_on: bool) -> dict:
    t_S_s = 23.8
    n_S = kj.period_of(t_S_s)
    t_P_s = (n_S + d_p) * kj.PERIOD_S
    would_block = due and d_p <= 0
    return {"t_loc_s": 25.0, "t_P_s": t_P_s, "t_S_s": t_S_s, "n_P": n_S + d_p, "n_S": n_S,
            "dP": d_p, "r4_due_without_gate": due, "would_block": would_block,
            "applied": due and not (is_on and would_block)}


def run_line(sub_name: str, key: str, sha: str, decisions=(), **values) -> dict:
    """A finished K1 line whose K-0 .. K-3 hold for its decisions."""
    sub = kj.SUB_BUNDLES[sub_name]
    is_on = sub.k1_candidate == kj.K1_ON
    line = make_line(key, sha, **values)
    decisions = [dict(item) for item in decisions]
    applied = sum(1 for item in decisions if item["applied"])
    skipped = sum(1 for item in decisions if item["would_block"] and is_on)
    if applied:
        line["event_names"][kj.FLAT_SOIL_MARGIN_EVENT] = applied
    if skipped:
        line["event_names"][kj.SKIP_EVENT] = skipped
    loc_calls = [{"t_s": item["t_loc_s"], "slope_margin_fired": False, "r4_on": True,
                  "t_S_s": item["t_S_s"], "t_P_s": item["t_P_s"]} for item in decisions]
    _, base_sha = kj.reference_file_of(sub, key, synthetic_bases())
    line["k1"] = {"bundle": sub.bundle, "sub_bundle": sub.name,
                  "las_candidate": sub.las_candidate, "k1_candidate": sub.k1_candidate,
                  "enabled": is_on, "setting": is_on, "decisions": decisions,
                  "r4_applied": applied > 0,
                  "would_block_any": any(item["would_block"] for item in decisions),
                  "loc_calls": loc_calls, "identity": IDENTITY,
                  **dict(zip(kj.RULES_FIELDS, kj.RULES_VALUES, strict=True)),
                  "base_file_sha256": base_sha, "resume": False,
                  "s2d_settings": {"mode_defer_periods": 0, "mode_defer_stroke_m": 0.0,
                                   "mode_defer_rise_factor": 4.0, "mode_defer_shadow": False}}
    return line


def passing_lines() -> list[dict]:
    """Every sub-bundle as the rules 5 predictions say (the gate blocks KA1 and PATCH, and
    BOUNDARY on P5r4)."""
    lines = [run_line("Y-0a", KA1, f"sc-{KA1}", [decision(0, is_on=False)]),
             run_line("Y-0d", KB1, f"sc-{KB1}"),
             run_line("Y-Pa", KA1, "new-KA1", [decision(0, is_on=True)], stroke_m=0.37),
             run_line("Y-Pa", KA2, f"sc-{KA2}", [decision(31, is_on=True)]),
             run_line("Y-Pb", KB1, f"sc-{KB1}"),
             run_line("Y-T", KD1, f"rt-{KD1}")]
    p5r4_blocked = {PATCH, BOUNDARY}
    for key in C_KEYS:
        p0_d = [decision(-5 if key == PATCH else 30, is_on=False)]
        p5_d = [decision(-5 if key in p5r4_blocked else 30, is_on=False)]
        lines.append(run_line("Y-0c", key, f"l-{key}", p0_d))
        lines.append(run_line("Y-0b", key, f"rs-{key}", p5_d))
        on_p0 = [decision(-5 if key == PATCH else 30, is_on=True)]
        on_p5 = [decision(-5 if key in p5r4_blocked else 30, is_on=True)]
        sa_sha = "sa-patch" if key == PATCH else f"l-{key}"
        sb_sha = f"sb-{key}" if key in p5r4_blocked else f"rs-{key}"
        lines.append(run_line("Y-Sa", key, sa_sha, on_p0))
        lines.append(run_line("Y-Sb", key, sb_sha, on_p5))
    return lines


def judged(lines: list[dict]) -> dict:
    return kj.judge(lines, synthetic_bases())


def replace_line(lines: list[dict], sub_name: str, key: str, new: dict) -> list[dict]:
    return [new if (kj.k1_of(line)["sub_bundle"], kj.key_of(line)) == (sub_name, key)
            else line for line in lines]


def test_predicted_lines_pass() -> None:
    result = judged(passing_lines())
    problems = {name: (sub["stops"], sub["fails"], sub["incomplete"])
                for name, sub in result["subs"].items()
                if sub["stops"] or sub["fails"] or sub["incomplete"]}
    assert problems == {}
    assert result["status"] == kj.STATUS_PASS
    assert {name: entry["status"] for name, entry in result["bundles"].items()} == dict.fromkeys(
        kj.BUNDLES, kj.STATUS_PASS)


def test_unpredicted_hash_change_is_a_stop() -> None:
    lines = replace_line(passing_lines(), "Y-Pb", KB1, run_line("Y-Pb", KB1, "other"))
    result = judged(lines)
    assert result["bundles"]["Y-P"]["status"] == kj.STATUS_STOP
    assert any(text.startswith("H-2 Y-Pb") for text in result["subs"]["Y-Pb"]["stops"])
    assert result["bundles"]["Y-S"]["status"] == kj.STATUS_PASS  # its lines judged as they are
    assert result["status"] == kj.STATUS_STOP


def test_stroke_increase_above_1_mm_is_a_fail() -> None:
    bad = run_line("Y-Pa", KA1, "new-KA1", [decision(0, is_on=True)], stroke_m=0.40 + 0.0011)
    result = judged(replace_line(passing_lines(), "Y-Pa", KA1, bad))
    assert result["bundles"]["Y-P"]["status"] == kj.STATUS_FAIL
    assert any("C-S" in text for text in result["subs"]["Y-Pa"]["fails"])
    assert result["status"] == kj.STATUS_FAIL


def test_stroke_increase_is_compared_without_tolerance() -> None:
    """Rules 4.3: the increase is compared as it is (a stored 1 mm step may round above)."""
    base = synthetic_bases().by_file["SC"][KA1]
    below = run_line("Y-Pa", KA1, "new", stroke_m=0.40 + 0.0009)
    above = run_line("Y-Pa", KA1, "new", stroke_m=0.40 + 0.0010001)
    assert not kj.pair_record(below, base)["cs_fail"]
    assert kj.pair_record(above, base)["cs_fail"]


def test_force_floor_and_p3_and_new_fault_fail() -> None:
    base = synthetic_bases().by_file["SC"][KA1]
    low = run_line("Y-Pa", KA1, "new", force_N=kj.F_FLOOR_N - 1.0)
    assert kj.pair_record(low, base)["cf_fail"]
    p3 = run_line("Y-Pa", KA1, "new")
    p3["d1"]["items"]["P3-5_gap"] = False
    assert kj.pair_record(p3, base)["P3"] is False
    fault = run_line("Y-Pa", KA1, "new")
    fault["event_names"]["FAULT_STROKE_END"] = 1
    assert kj.pair_record(fault, base)["c2"]


def test_verdict_leaving_pass_is_a_c2_violation() -> None:
    base = synthetic_bases().by_file["SC"][KA1]
    worse = run_line("Y-Pa", KA1, "new")
    worse["d1"]["verdict"] = "flag"
    assert any("verdict pass -> flag" in text for text in kj.pair_record(worse, base)["c2"])


def test_missing_decisions_is_a_stop() -> None:
    """Rules 7: an evaluated LOC (witness) without a decision is K-1."""
    bad = run_line("Y-Pa", KA2, f"sc-{KA2}", [decision(31, is_on=True)])
    bad["k1"]["decisions"] = []
    bad["k1"]["r4_applied"] = True  # the event is still there
    result = judged(replace_line(passing_lines(), "Y-Pa", KA2, bad))
    assert result["bundles"]["Y-P"]["status"] == kj.STATUS_STOP
    assert any(text.startswith("K-1") for text in result["subs"]["Y-Pa"]["stops"])


def test_decision_without_t_p_is_a_stop() -> None:
    bad = run_line("Y-Pa", KA2, f"sc-{KA2}", [decision(31, is_on=True)])
    bad["k1"]["decisions"][0]["t_P_s"] = None
    assert any("without t_P" in text for text in kj.k1_problems(bad))


def test_fail_wins_over_stop() -> None:
    fail = run_line("Y-Pa", KA1, "new-KA1", [decision(0, is_on=True)], stroke_m=0.45)
    lines = replace_line(passing_lines(), "Y-Pa", KA1, fail)
    lines = replace_line(lines, "Y-Pb", KB1, run_line("Y-Pb", KB1, "other"))
    result = judged(lines)
    assert result["subs"]["Y-Pb"]["stops"] and result["subs"]["Y-Pa"]["fails"]
    assert result["bundles"]["Y-P"]["status"] == kj.STATUS_FAIL
    assert result["status"] == kj.STATUS_FAIL
    assert kj.EXIT_CODES[result["status"]] == 1


def test_shadow_set_other_than_q0b_is_a_stop() -> None:
    no_shadow = run_line("Y-0c", PATCH, f"l-{PATCH}", [decision(30, is_on=False)])
    result = judged(replace_line(passing_lines(), "Y-0c", PATCH, no_shadow))
    assert any(text.startswith("SK-3 Y-0c") for text in result["subs"]["Y-0c"]["stops"])


def test_k1off_skip_event_and_applied_rules() -> None:
    line = run_line("Y-0a", KA1, f"sc-{KA1}", [decision(0, is_on=False)])
    line["event_names"][kj.SKIP_EVENT] = 1
    assert any(text.startswith("K-2") for text in kj.k23_problems(line))
    blocked_on = run_line("Y-Pa", KA1, "x", [decision(0, is_on=True)])
    blocked_on["k1"]["decisions"][0]["applied"] = True
    assert any(text.startswith("K-3") for text in kj.k23_problems(blocked_on))


def test_k4_not_blocked_k1on_line_must_keep_the_k1off_hash() -> None:
    other = run_line("Y-Pa", KA2, "changed", [decision(31, is_on=True)])
    result = judged(replace_line(passing_lines(), "Y-Pa", KA2, other))
    assert any(text.startswith("K-4") for text in result["subs"]["Y-Pa"]["stops"])


def test_structure_duplicate_out_of_list_missing_and_not_run() -> None:
    lines = passing_lines()
    duplicate = copy.deepcopy([line for line in lines
                               if kj.k1_of(line)["sub_bundle"] == "Y-0d"][0])
    outside = run_line("Y-0d", KA2, f"sc-{KA2}")
    result = judged([*lines, duplicate, outside])
    stops = result["subs"]["Y-0d"]["stops"]
    assert any("duplicate" in text for text in stops) and any("outside" in text for text in stops)
    assert result["bundles"]["Y-0"]["status"] == kj.STATUS_STOP
    only_y0 = [line for line in lines if kj.k1_of(line)["bundle"] == "Y-0"]
    only_y0 = [line for line in only_y0 if kj.k1_of(line)["sub_bundle"] != "Y-0d"]
    result = judged(only_y0)
    assert result["bundles"]["Y-0"]["status"] == kj.STATUS_INCOMPLETE
    assert result["bundles"]["Y-P"]["status"] == kj.STATUS_NOT_RUN
    assert kj.EXIT_CODES[result["status"]] == 3


def test_error_keys_and_resume() -> None:
    error = {"job": {"setting": "VB"}, "error": "pool: x",
             "rev": {"key": KB1, "k1": {"bundle": "Y-0", "sub_bundle": "Y-0d",
                                        "las_candidate": "P0", "k1_candidate": kj.K1_OFF}}}
    lines = [line for line in passing_lines() if kj.k1_of(line)["sub_bundle"] != "Y-0d"]
    result = judged([*lines, error])
    assert result["bundles"]["Y-0"]["status"] == kj.STATUS_INCOMPLETE
    assert kj.resume_keys([*lines, error], "Y-0d") == [KB1]
    assert kj.resume_keys([*lines, error, error], "Y-0d") == []  # re-run inside the batch
    resumed = run_line("Y-0d", KB1, f"sc-{KB1}")
    resumed["k1"]["resume"] = True
    result = judged([*lines, error, resumed])
    assert result["subs"]["Y-0d"]["resumed"] == [KB1]
    assert result["bundles"]["Y-0"]["status"] == kj.STATUS_PASS


def test_identity_problems() -> None:
    line = run_line("Y-0d", KB1, f"sc-{KB1}")
    line["k1"]["identity"] = {**IDENTITY, "code_diff_sha256": "1" * 64}
    assert kj.identity_value_problems(line["k1"]) == ["code_diff_sha256 not empty"]
    other_head = run_line("Y-T", KD1, f"rt-{KD1}")
    other_head["k1"]["identity"] = {**IDENTITY, "git_head": "0" * 40}
    result = judged(replace_line(passing_lines(), "Y-T", KD1, other_head))
    assert result["k0_cross"] and result["status"] == kj.STATUS_STOP


def test_s2d_on_is_a_stop() -> None:
    line = run_line("Y-T", KD1, f"rt-{KD1}")
    line["k1"]["s2d_settings"]["mode_defer_shadow"] = True
    result = judged(replace_line(passing_lines(), "Y-T", KD1, line))
    assert any("S2D not off" in text for text in result["subs"]["Y-T"]["stops"])


def test_predictions_table_on_the_predicted_lines() -> None:
    rows = {row["id"]: row for row in judged(passing_lines())["predictions"]}
    assert rows["Q-0b"]["holds"] is True and rows["Q-P1"]["holds"] is True
    assert rows["Q-S2"]["holds"] is True  # both sides blocked, delta 0 mm


# ------------------------------------------------------------------------------- harness parts
@pytest.fixture
def installed():
    yield
    kt.uninstall()
    kt._INSTALLED.clear()


@pytest.fixture(scope="module")
def geometry() -> c2.C2Geometry:
    return c2.C2Geometry.from_params(load_params())


def test_order_gate_wrapper_sets_only_the_gate(geometry, installed) -> None:
    kt.install_order_gate(True)
    controller = c2.C2Controller(geometry, k1_config(False))
    assert controller.config.slope_clearance_margin.flat_soil_margin_order_gate is True
    expected = k1_config(True)
    assert controller.config == expected
    with pytest.raises(RuntimeError):
        kt.install_order_gate(False)


def test_witness_records_each_loc_and_keeps_the_commands(geometry, installed) -> None:
    plain = bench_outputs(geometry, k1_config(True), soil_mode_offset_s=0.0)
    kt.install_loc_witness()
    witnessed = bench_outputs(geometry, k1_config(True), soil_mode_offset_s=0.0)
    np.testing.assert_array_equal(plain, witnessed)
    controller = c2.C2Controller(geometry, k1_config(True))
    loc_at(controller, geometry, 3.0)
    (call,) = controller.__dict__[kt.WITNESS_ATTRIBUTE]
    assert call == {"t_s": 3.0, "slope_margin_fired": False, "r4_on": True, "t_S_s": 3.0,
                    "t_P_s": 3.0}


def test_run_names_and_out_names() -> None:
    assert kt.run_names("Y-0") == ["Y-0a", "Y-0b", "Y-0c", "Y-0d"]
    assert kt.run_names("Y-Sb") == ["Y-Sb"]
    assert kt.out_name("Y-0") == "k1_Y0.jsonl"
    assert kt.out_name("Y-Pa", is_resume=True) == "k1_YPa_resume.jsonl"


def test_keys_and_limit_need_a_trial_file(capsys) -> None:
    assert kt.main(["run", "--bundle", "Y-0", "--keys", KB1]) == 2
    assert kt.main(["run", "--bundle", "Y-0", "--limit", "1"]) == 2
    assert "--trial-out" in capsys.readouterr().out


def test_order_gate_problems_after_an_earlier_stop() -> None:
    bases = synthetic_bases()
    lines = replace_line(passing_lines(), "Y-0d", KB1, run_line("Y-0d", KB1, "other"))
    assert kt.order_gate_problems("Y-0", lines, bases, None) == []
    assert kt.order_gate_problems("Y-P", lines, bases, None)
    assert kt.order_gate_problems("Y-Pa", lines, bases, "user said go on 2026-11-09") == []
    assert kt.existing_line_problems("Y-0", lines)
    assert kt.existing_line_problems("Y-T", [line for line in lines
                                             if kj.k1_of(line)["bundle"] != "Y-T"]) == []
