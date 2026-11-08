"""Checks of the T-3 tool and judge (``las_targeted_rules_rev3.md`` 2 .. 4), no harness run, and
of the audit fixes of 2026-11-08 in ``las_targeted`` / ``las_judge`` / ``las_shadow``.

Run (dynamics-dev): python -I -B -m pytest <this file> -p no:cacheprovider
The key-list checks read the sealed key list of the project (skipped when absent).
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import las_h7  # noqa: E402
import las_judge as lj  # noqa: E402
import las_t3  # noqa: E402
import las_t3_judge as tj  # noqa: E402
import las_targeted as lt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

IDENTITY = {"git_head": "c" * 40, "sha256": {"las_t3.py": "a" * 64}, "c2_sha256": "b" * 64,
            "threads": {"OMP_NUM_THREADS": "1"}, "workers": 4, "affinity": "0xF"}
HASH = "1" * 64


def _entry(key: str = "D1|H-S-0|G1|T|flat|K1|V0|e0", base: str = "G1") -> dict:
    return {"line_key": key, "kind": las_t3.KIND_D1, "key": key, "base": base}


def _dg3_entry(folder: str = "v4_on") -> dict:
    key = "cand=current#L3|s2|ref|14|G1|B|0,0"
    return {"line_key": las_t3.dg3_line_key(folder, key), "kind": las_t3.KIND_DG3,
            "key": key, "folder": folder, "shadow_commands_sha256_all_folders": [HASH]}


def _line(entry: dict, bundle: str = "T-3a", *, setting: str = "V0", tag=tj.TAG_V0_LAS,
          sha: str = HASH, fired: bool = False, enable: bool = True, ready=60.0,
          p32=True, identity=None) -> dict:
    names = {"INFO_LIFTOFF_SLOW": 1} if fired else {}
    return {"job": {"setting": setting}, "commands_sha256": sha, "controller_tag": tag,
            "event_names": names,
            "t3": {"bundle": bundle, "line_key": entry["line_key"],
                   "identity": dict(IDENTITY if identity is None else identity)},
            "d1": {"verdict": "pass", "fail_items": [], "items": {"P3-2": p32},
                   "t_ready_s": ready, "stroke_max_m": 0.4, "F_judged_min_N": 20_000.0},
            "las_t3": {"fired": fired, "enable": enable, "start_s": 30.0 if fired else None}}


def _baseline(entry: dict, ready=60.0) -> dict:
    line = _line(entry, sha=HASH, ready=ready)
    return {entry["line_key"]: {k: v for k, v in line.items() if k != "t3"}}


# ------------------------------------------------------------------------------- K-1 .. K-6
def test_silent_line_with_the_stored_hash_passes() -> None:
    entry = _entry()
    criteria, k7 = tj.t3_criteria([_line(entry)], {"T-3a": [entry], "T-3b": [], "T-3c": []},
                                  _baseline(entry))
    assert criteria["K-4"] == {} and criteria["K-5"] == {} and criteria["K-6"] == {}
    assert criteria["K-1"] == ["T-3b: empty key set", "T-3c: empty key set"]  # empty != pass
    assert k7 == []


def test_g1_uniform_line_that_fires_fails_k4_and_is_judged_by_k6() -> None:
    entry = _entry()
    line = _line(entry, fired=True, sha="2" * 64, ready=None)
    criteria, k7 = tj.t3_criteria([line], {"T-3a": [entry], "T-3b": [], "T-3c": []},
                                  _baseline(entry))
    assert criteria["K-4"] == {entry["line_key"]: "fired"}
    assert criteria["K-5"] == {}  # K-5 is for silent lines only
    assert "C5'-R" in criteria["K-6"][entry["line_key"]]  # READY lost (K-6d: None fails)
    assert len(k7) == 1 and k7[0]["start_s"] == 30.0


def test_silent_g1_hash_change_is_k5_not_k4() -> None:
    """rev4a 3: a fired G1 line is H-T3-4; a silent line with another hash is H-T3-5."""
    entry = _entry()
    criteria, _ = tj.t3_criteria([_line(entry, sha="5" * 64)],
                                 {"T-3a": [entry], "T-3b": [], "T-3c": []}, _baseline(entry))
    assert criteria["K-4"] == {} and entry["line_key"] in criteria["K-5"]
    assert tj.first_stop({"K-5": criteria["K-5"]}) == "H-T3-5"


def _stored_dg3(tmp_path: Path, folder: str, options: dict, rule: str) -> dict:
    entry = {**_dg3_entry(folder), "result_file": f"dg3\\{folder}\\r.json"}
    record = {"key": entry["key"], "v5_setting": "VB", "hydraulic_options": options,
              "controller_settings": {"soil.enable": True, "two_pressure.extend_start_rule": rule}}
    path = tmp_path / "dg3" / folder / "r.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"meta": {"preset_settings": {
        "two_pressure.extend_start_rule": rule}}, "results": [record]}), encoding="utf-8")
    return entry


def test_dg3_run_condition_against_the_stored_record(tmp_path: Path) -> None:
    stored_options = {"rod_release_force": True, "m2_law": "flow_limited_r5"}
    entry = _stored_dg3(tmp_path, "v4_on", stored_options, "tracked_bound")
    line = {**_line(entry, "T-3b", tag=tj.TAG_P3_LAS), "v5_setting": "VB",
            "hydraulic_options": {**stored_options, "extend_start_tracked": True},
            "extend_start_rule": "tracked_bound",
            "controller_settings": {"soil.enable": True,
                                    "two_pressure.extend_start_rule": "tracked_bound",
                                    "liftoff_approach_slow.enable": True,
                                    "full_config": {"x": 1}, "full_config_sha256": "f" * 64}}
    assert tj.condition_problems(entry, line, True, tmp_path) == []
    changed = {**line, "controller_settings": {**line["controller_settings"],
                                               "soil.enable": False}}
    assert "controller_settings differ" in tj.condition_problems(entry, changed, True,
                                                                  tmp_path)[0]
    other = {**line, "hydraulic_options": {"rod_release_force": False}}
    assert "hydraulic_options" in tj.condition_problems(entry, other, True, tmp_path)[0]
    off = _stored_dg3(tmp_path, "off", stored_options, "constant")
    wrong = {**line, "t3": {**line["t3"], "line_key": off["line_key"]},
             "controller_tag": tj.TAG_V0_LAS, "hydraulic_options": stored_options}
    problems = tj.condition_problems(off, wrong, True, tmp_path)
    assert any("③ rule tracked_bound != stored preset constant" in p for p in problems)
    # rev4b 1: the off folder allows no option difference (③ as an option is a difference)
    off_line = {**wrong, "extend_start_rule": "constant",
                "controller_settings": {"soil.enable": True,
                                        "two_pressure.extend_start_rule": "constant"}}
    assert tj.condition_problems(off, off_line, True, tmp_path) == []
    with_p3 = {**off_line, "hydraulic_options": {**stored_options, "extend_start_tracked": True}}
    assert "hydraulic_options" in tj.condition_problems(off, with_p3, True, tmp_path)[0]
    assert tj.DG3_OPTION_REPRESENTATION == {"v4_on": {"extend_start_tracked": True}}


def test_k6_p32_none_fails_and_silent_hash_change_is_k5() -> None:
    entry = _entry(base="J1")
    fired = _line(entry, fired=True, p32=None)
    criteria, _ = tj.t3_criteria([fired], {"T-3a": [entry], "T-3b": [], "T-3c": []},
                                 _baseline(entry))
    assert list(criteria["K-6"][entry["line_key"]]) == ["P3-2"]
    assert criteria["K-4"] == {}  # J1 base: not a K-4 line
    silent = _line(entry, sha="3" * 64)
    criteria, _ = tj.t3_criteria([silent], {"T-3a": [entry], "T-3b": [], "T-3c": []},
                                 _baseline(entry))
    assert entry["line_key"] in criteria["K-5"]


def test_key_set_mismatch_and_unresolved_errors() -> None:
    entry, other = _entry(), _entry("D1|H-S-0|G1|T|flat|K1|VB|e0")
    error = {"t3": {"bundle": "T-3a", "line_key": other["line_key"]}, "error": "boom"}
    stray = _line(_entry("D1|X"), "T-3a")
    criteria, _ = tj.t3_criteria([_line(entry), error, stray],
                                 {"T-3a": [entry, other], "T-3b": [_dg3_entry()],
                                  "T-3c": [entry]}, {**_baseline(entry), **_baseline(other)})
    text = " ".join(criteria["K-1"])
    assert "keys without a good line" in text and "not in the key list" in text
    assert criteria["errors"] == [other["line_key"]]
    retried = [error, _line(other, setting="VB", tag=tj.TAG_P3_LAS)]
    assert tj.good_lines(retried)[1] == []  # the retry resolves the error


def test_tags_of_t3_and_r0_lines() -> None:
    entry = _entry()
    assert tj.tag_problems(entry, _line(entry), is_las_on=True) == []
    vb = _line(entry, setting="VB", tag=tj.TAG_P3_LAS)
    assert tj.tag_problems(entry, vb, is_las_on=True) == []
    assert tj.tag_problems(entry, _line(entry, tag="final_C4G2_LAS_FB"), True)[0].endswith(
        "has _FB")
    assert tj.tag_problems(entry, _line(entry, tag=None), True) == ["tag None != final_C4G2_LAS"]
    r0 = _line(entry, tag=None, enable=False)
    assert tj.tag_problems(entry, r0, is_las_on=False) == []
    assert tj.tag_problems(entry, _line(entry, enable=False), False)[0].startswith("tag")
    dg3 = _dg3_entry("off")
    line = {**_line(dg3, "T-3b", tag=tj.TAG_V0_LAS), "extend_start_rule": "tracked_bound"}
    assert tj.tag_problems(dg3, line, True) == ["③ start rule tracked_bound != folder off"]


def test_r0_gate_stops_on_a_hash_difference() -> None:
    entry = _entry()
    good = _line(entry, "R-0", tag=None, enable=False)
    criteria = tj.r0_criteria([good], [entry], _baseline(entry))
    assert tj.first_stop(criteria) is None
    bad = _line(entry, "R-0", tag=None, enable=False, sha="4" * 64)
    assert tj.first_stop(tj.r0_criteria([bad], [entry], _baseline(entry))) == "H-T3-1"
    assert tj.first_stop(tj.r0_criteria([], [entry], _baseline(entry))) == "H-T3-3"


def test_identity_of_every_line_must_equal_the_header() -> None:
    entry = _entry()
    header = {"identity": IDENTITY}
    assert tj.identity_problems("T-3", header, [_line(entry)]) == []
    other = _line(entry, identity={**IDENTITY, "c2_sha256": "d" * 64})
    assert "c2_sha256" in tj.identity_problems("T-3", header, [other])[0]
    assert tj.identity_problems("T-3", None, []) == ["T-3: no header line"]


def test_exit_codes() -> None:
    assert tj.exit_code({"stops": []}) == 0
    assert tj.exit_code({"stops": ["H-T3-6"]}) == 1
    assert tj.exit_code({"stops": ["H-T3-3", "H-T3-6"]}) == 2


def test_judge_refuses_to_overwrite_its_outputs(tmp_path: Path) -> None:
    out = tmp_path / "las_T3.md"
    out.write_text("old", encoding="utf-8")
    args = SimpleNamespace(jsonl=tmp_path / "las_T3.jsonl", r0=None, keys=None, rules=None,
                           baseline=tmp_path / "d1.jsonl", out=out, json_out=None)
    assert tj.main_t3(args) == 2
    assert out.read_text(encoding="utf-8") == "old"


# ------------------------------------------------------------------------------- tool
def _copy_seals(target: Path) -> None:
    for seal in lt.SEALS.values():
        for name in (seal.file_name, seal.sha_file_name):
            source = lt.RULES_PATH.parent / name
            if source.exists() and not (target / name).exists():
                shutil.copy(source, target / name)


HAS_SEALS = all((lt.RULES_PATH.parent / seal.file_name).exists() for seal in lt.SEALS.values())


@pytest.mark.skipif(not HAS_SEALS, reason="sealed rules absent")
def test_seal_mismatch_is_found(tmp_path: Path) -> None:
    _copy_seals(tmp_path)
    assert lt.seal_problems(tmp_path, las_t3.T3_REQUIRED_SEALS) == []
    keys = tmp_path / lt.SEALS["rev3_keys"].file_name
    keys.write_bytes(keys.read_bytes() + b" ")
    problems = lt.seal_problems(tmp_path, las_t3.T3_REQUIRED_SEALS)
    assert len(problems) == 1 and problems[0].startswith("rev3_keys:")
    (tmp_path / lt.SEALS["rev4"].file_name).unlink()
    assert any("missing" in p for p in lt.seal_problems(tmp_path, las_t3.T3_REQUIRED_SEALS))
    assert lt.seal_problems(tmp_path, ("original",), ("rev4",)) == []  # optional and absent


@pytest.mark.skipif(not las_t3.KEYS_PATH.exists(), reason="sealed key list absent")
def test_key_list_bundles_have_the_sealed_counts() -> None:
    entries = las_t3.bundle_entries(las_t3.load_key_list())
    assert las_t3.count_problems(entries) == []
    assert {b: len(g) for b, g in entries.items()} == las_t3.EXPECTED_COUNTS
    assert sum(e.get("base") == "G1" for e in entries["T-3a"]) + len(entries["T-3b"]) == 76
    with pytest.raises(KeyError):
        las_t3.select_keys(entries, ["no such key"])


def test_preflight_refuses_an_existing_output(tmp_path: Path) -> None:
    (tmp_path / las_t3.T3_FILE).write_text("", encoding="utf-8")
    problems = las_t3.preflight(tmp_path)
    assert f"output exists: {tmp_path / las_t3.T3_FILE}" in problems


def test_run_bundles_does_not_append(tmp_path: Path) -> None:
    path = tmp_path / las_t3.R0_FILE
    path.write_text("kept\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        las_t3.run_bundles([], path, {"header": {}}, {})
    assert path.read_text(encoding="utf-8") == "kept\n"


def test_foreign_methods_are_reported() -> None:
    class Base:
        def step(self):
            return 1

    Base.__module__ = "home"
    Base.step.__module__ = "home"
    assert las_t3.foreign_functions(Base, "home") == []
    Base.step = lambda self: 2  # defined here: another module
    assert las_t3.foreign_functions(Base, "home") == [f"Base.step from {__name__}"]
    assert las_t3.foreign_functions(Base, "home", ("step",)) == []


def test_fb_block_on_is_refused() -> None:
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class Block:
        enable: bool

    @dataclass(frozen=True)
    class Config:
        command_flow_budget: Block = Block(True)
        soil: Block = Block(True)

    assert las_t3.fb_problems(Config()) == ["config.command_flow_budget.enable is True"]
    assert las_t3.fb_problems(Config(command_flow_budget=Block(False))) == []


def test_capture_passes_arguments_and_result_through(monkeypatch) -> None:
    """The record-only wrapper cannot change a command (hash invariance of the capture)."""
    import d1_runs

    calls = []

    def original(row, setting_name, eps, result, plant, controller, harness):
        calls.append((row, setting_name, eps, result, plant, controller, harness))
        return {"d1": "record"}

    monkeypatch.setattr(d1_runs, "d1_record", original)
    las_t3.capture_d1_record()
    args = ("row", "VB", 0.0, {"r": 1}, "plant", "ctrl", {"h": 2})
    assert d1_runs.d1_record(*args) == {"d1": "record"}
    assert calls == [args]
    assert las_t3._CAPTURE["controller"] == "ctrl" and las_t3._CAPTURE["harness"] == {"h": 2}


def test_las_record_reads_the_meta_and_events_only() -> None:
    events = [SimpleNamespace(t_s=31.2, name="INFO_LIFTOFF_SLOW:RR"),
              SimpleNamespace(t_s=32.0, name="INFO_LIFTOFF_SLOW_END:loc"),
              SimpleNamespace(t_s=33.0, name="crawler_liftoff_confirmed")]
    meta = {"settings": {"enable": True}, "start_s": 31.2, "active_periods": 7,
            "scaled_periods": 5, "start_rho": 0.3}
    controller = SimpleNamespace(
        events=events, meta=lambda: {"liftoff_approach_slow": meta},
        config=SimpleNamespace(liftoff_approach_slow=SimpleNamespace(enable=True)))
    record = las_t3.las_record(controller, {"rows": {"P3-2": {"loc_delay_s": 0.8}}})
    assert record["fired"] and record["events"] == [[31.2, "INFO_LIFTOFF_SLOW:RR"],
                                                     [32.0, "INFO_LIFTOFF_SLOW_END:loc"]]
    assert record["active_periods"] == 7 and record["loc_minus_t_off_s"] == 0.8


def test_v5_run_record_las_events_leave_the_hashes_alone(monkeypatch) -> None:
    """rev4b 3: the record-only ``las_events`` field is built from the events after the run;
    the record with it and the one without it carry the same command hashes."""
    import v5_rerun

    logged = {"t": np.array([0.0, 0.1]), "command": np.zeros((2, 4)), "phase": np.array(["a"] * 2)}
    fake_verdict_runs = SimpleNamespace(period_arrays=lambda controller: logged,
                                        _command_digest=lambda command: "d" * 64)
    monkeypatch.setattr(v5_rerun, "setting_name", lambda: "V0")
    monkeypatch.setattr(v5_rerun, "_coupled_modules", lambda: (None, fake_verdict_runs))
    monkeypatch.setattr(v5_rerun, "installed_options", lambda: None)
    monkeypatch.setattr(v5_rerun, "definition_sha256", lambda name, controller: "def")
    monkeypatch.setattr(v5_rerun, "_worker_code_commit", lambda: {"head": "c"})
    events = [SimpleNamespace(t_s=30.0, name="INFO_LIFTOFF_SLOW:RR"),
              SimpleNamespace(t_s=40.0, name="FAULT_STROKE_END:FL")]
    controller = SimpleNamespace(events=events, _v5_rod_seen=False)
    with_field = v5_rerun.run_record(None, controller, harness_commands_sha256=HASH)
    monkeypatch.setattr(v5_rerun, "las_events_of", lambda controller: None)
    without_field = v5_rerun.run_record(None, controller, harness_commands_sha256=HASH)
    del without_field[v5_rerun.LAS_EVENTS_KEY]
    las_events = with_field.pop(v5_rerun.LAS_EVENTS_KEY)
    assert with_field == without_field
    assert with_field["commands_sha256"] == HASH
    assert las_events["liftoff_slow"] == [[30.0, "INFO_LIFTOFF_SLOW:RR"]]
    assert las_events["fault_names"] == ["FAULT_STROKE_END:FL"]


# ------------------------------------------------------------------------------- audit fixes
def test_c3_and_c5_missing_values_fail() -> None:
    base = {"event_names": {}, "d1": {"t_ready_s": 60.0, "stroke_max_m": 0.4}}
    no_events = {"event_names": None, "d1": base["d1"], "las": {"start_t_s": 1.0}}
    assert "missing" in lj.c3_problem(no_events, base)
    started = {"las": {"start_t_s": 1.0}}
    no_stroke = {**started, "d1": {"t_ready_s": 60.0, "stroke_max_m": None}}
    assert "stroke missing" in lj.c5_problem(no_stroke, base)
    both_none = {"d1": {"t_ready_s": None, "stroke_max_m": 0.4}}
    assert lj.c5_problem({**started, **both_none}, both_none) is None
    assert lj.c5_problem({**started, **both_none}, base) == "READY lost"


def test_t1_key_set_is_the_sealed_appendix() -> None:
    def line(key: str) -> dict:
        return {"job": {}, "commands_sha256": HASH, "event_names": {},
                "d1": {"key": key, "verdict": "pass", "F_judged_min_N": 20_000.0,
                       "fail_items": [], "items": {"G6-2_loc": True}, "t_ready_s": 60.0,
                       "stroke_max_m": 0.6},
                "las": {"key": key, "candidate": "b0", "start_t_s": None}}

    keys = [f"k{i}" for i in range(8)]
    baseline = {key: line(key) for key in keys}
    sealed = {*keys[:7], "other"}
    result = lj.judge_t1([line(key) for key in keys], baseline, sealed)
    assert result["stop"] == "H-3" and "b0" in result["incomplete_variants"]
    assert lj.judge_t1([line(key) for key in keys], baseline, set(keys))["selected"] == "b0"


def test_shadow_record_without_a_level_step_is_undecidable() -> None:
    import las_shadow as ls

    record = ls.ShadowRecord(
        name="r.npz", t_s=np.array([0.0, 0.1, 0.2]),
        phase=np.array(["touch", "touch", "touch"]), lower_estimate_N=np.full((3, 4), 1e5),
        events=[], F_min_N=9414.589, weight_ref_N=376_600.0, soil_enable=True, job=None,
        commands_sha256=None)
    result = ls.shadow_judge(record, lt.CANDIDATES["b0"])
    assert result["status"] == ls.UNDECIDABLE and result["reason"] == "no LEVEL step"
    assert result["params"] == lt.CANDIDATES["b0"].to_dict()


def test_shadow_paths_are_repository_relative() -> None:
    import las_shadow as ls

    path = lt.ROOT / "06_analysis" / "x" / "r.npz"
    assert ls.repository_path(path) == "06_analysis/x/r.npz"
    assert ls.repository_path(None) is None


def test_t4h_request_tag_is_corrected_to_the_run_controller() -> None:
    """``run_v5._t4h_request`` builds its meta before the controller exists (options only);
    ``verdict_runs._finish`` writes the record with the tag of the run's controller config."""
    import run_v5
    import verdict_runs

    from outrigger_sim.control import c2

    flow, options = run_v5.options_of("VB")
    job = {"case": "R12", "setting": "VB", "eps": 0.0, "t4h_dir": "unused"}
    request = run_v5._t4h_request(job, flow, options)["meta"]
    assert request["controller_tag"] == tj.TAG_P3  # request time: no config yet
    las_on = c2.C2Config().with_10hz_d1()
    las_off = c2.C2Config().with_10hz_d1(liftoff_approach_slow=False)
    assert verdict_runs._meta_with_controller_tag(request, las_on)["controller_tag"] == \
        tj.TAG_P3_LAS
    assert verdict_runs._meta_with_controller_tag(request, las_off)["controller_tag"] == \
        tj.TAG_P3


def test_h7_and_k6_share_one_function() -> None:
    entry = _entry(base="J1")
    line = _line(entry, fired=True, ready=70.0)
    criteria, _ = tj.t3_criteria([line], {"T-3a": [entry], "T-3b": [], "T-3c": []},
                                 _baseline(entry))
    assert criteria["K-6"][entry["line_key"]] == las_h7.h7_violations(
        line, _baseline(entry)[entry["line_key"]], las_h7.D1_FORMAT)


def test_key_list_entries_are_compared_with_d1_lines(tmp_path: Path) -> None:
    entry = {**_entry(), "commands_sha256": HASH, "verdict": "pass", "P3-2": True,
             "t_ready_s": 60.0, "stroke_max_m": 0.4, "fault_names": [], "G6-2": None,
             "fail_items": []}
    record = {"commands_sha256": HASH, "event_names": {},
              "d1": {"verdict": "pass", "items": {"P3-2": True, "G6-2_loc": True},
                     "t_ready_s": 60.0, "stroke_max_m": 0.4, "fail_items": []}}
    assert tj._entry_differences(entry, record) == []  # the void G6-2 field is not compared
    assert tj._entry_differences({**entry, "verdict": "fail"}, record)[0].endswith(
        "!= d1.jsonl 'pass'")
    assert "fail_items" in tj._entry_differences({**entry, "fail_items": ["READY"]}, record)[0]
    assert tj.CRITERION_STOP["key-list"] == "H-T3-3"
    baseline_path = tmp_path / "d1.jsonl"
    baseline_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    keys = {"d1_baseline": {"sha256": "0" * 64}}
    entries = {"T-3a": [entry], "T-3c": [], "R-0": [], "T-3b": []}
    problems, notes = tj.key_list_problems(keys, entries, {entry["line_key"]: record},
                                           baseline_path)
    assert problems[0].startswith("d1.jsonl sha256") and "G6-2" in notes[0]
