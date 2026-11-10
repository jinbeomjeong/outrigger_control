"""Checks of the T-3 tool and judge in the ``rev5`` mode (sealed ``las_targeted_rules_rev5.md``,
design note ``las_t3_k1_design_note.md`` 4 and 6: tests T1 .. T6), no harness run.

The harness smoke T2-c (one R-0K key against its stored hash) is a CLI run of ``las_t3.py``
(``--only R-0K --keys ...``), not a test here.

Run (Chrono-dev or dynamics-dev): python -I -B -m pytest <this file> -p no:cacheprovider
The stored-data checks read the v5 folder of ``LAS_T3_STORED_V5`` (default: this checkout's
``06_analysis/03_hydraulic/coupled/v5``; skipped when ``d1.jsonl`` or the Dg-3 records are
absent, e.g. in a worktree).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import las_t3  # noqa: E402
import las_t3_judge as tj  # noqa: E402
import las_targeted as lt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

from outrigger_sim.control import c2  # noqa: E402
from outrigger_sim.hydraulics import v5_options  # noqa: E402

STORED_V5 = Path(os.environ.get("LAS_T3_STORED_V5", str(las_t3.V5_DIR)))
HAS_D1 = (STORED_V5 / "d1.jsonl").exists()
HAS_DG3 = (STORED_V5 / "dg3").exists()
HASH = "1" * 64
OTHER = "2" * 64
IDENTITY = {"git_head": "c" * 40, "sha256": {"las_t3.py": "a" * 64}, "c2_sha256": "b" * 64,
            "threads": {"OMP_NUM_THREADS": "1"}, "workers": 1, "affinity": "0xFFF0000"}
G1_KEY = "D1|H-S-0|G1|T|flat|K1|V0|e0"
UNIFORM_KEY = "D1|H-S-0|J1|T|flat|K1|V0|e0"
OUTSIDE_KEY = "D1|H-S-0|J1|T|fup-rec|K1|V0|e0"
MAKE_SCRIPT = las_t3.RULES_DIR / "scripts" / "make_las_rev5_r0k_keys.py"
MAKE_SCRIPT_SHA256 = "54e6eff29b7b393dacfabf8774a5b609aa2ac849160d1c7d0ecbc60e457dbe24"


def _config(las: bool, gate: bool):
    return c2.C2Config().with_10hz_d1(liftoff_approach_slow=las,
                                      flat_soil_margin_order_gate=gate)


def _entry(key: str = G1_KEY, cls: str | None = None, base: str = "J1") -> dict:
    entry = {"line_key": key, "kind": las_t3.KIND_D1, "key": key, "base": base}
    if cls is not None:
        entry["class"] = cls
    return entry


def _r0k_entry(key: str, cls: str) -> dict:
    """An R-0K entry whose stored fields match :func:`_stored` (the ``key-list`` check)."""
    return {**_entry(key, cls), "stored_commands_sha256": HASH, "stored_controller_tag": None,
            "stored_verdict": "pass", "stored_r4c30_count": 0,
            "predicted_would_block": cls == "patch_r4"}


def _k1(enabled: bool, blocked: bool = False, applied: int = 0) -> dict:
    decisions = [{"t_loc_s": 30.0, "dP": -5 if blocked else 40, "n_P": 300, "n_S": 305,
                  "would_block": blocked, "applied": applied > 0}] if (blocked or applied) else []
    return las_t3.k1_record({"enabled": enabled, "decisions": decisions})


def _line(entry: dict, bundle: str, *, setting: str = "V0", tag: str | None,
          sha: str = HASH, fired: bool = False, las: bool = False, gate: bool = True,
          blocked: bool = False, ready=60.0) -> dict:
    return {"job": {"setting": setting}, "commands_sha256": sha, "controller_tag": tag,
            "event_names": {"INFO_LIFTOFF_SLOW": 1} if fired else {},
            "t3": {"bundle": bundle, "line_key": entry["line_key"], "identity": dict(IDENTITY)},
            "d1": {"verdict": "pass", "fail_items": [], "items": {"P3-2": True, "G6-2_loc": True},
                   "t_ready_s": ready, "stroke_max_m": 0.4, "F_judged_min_N": 20_000.0},
            "las_t3": {"fired": fired, "enable": las, "start_s": 30.0 if fired else None,
                       "k1": _k1(gate, blocked)}}


def _stored(entry: dict, sha: str = HASH, ready=60.0) -> dict:
    line = _line(entry, "stored", tag=None, sha=sha, ready=ready)
    record = {key: value for key, value in line.items() if key not in ("t3", "las_t3")}
    return {entry["line_key"]: record}


# ------------------------------------------------------------------------------- T1
def test_t1a_preset_has_the_gate_and_r4c30() -> None:
    assert las_t3.preset_problems(gate_expected=True) == []
    assert las_t3.preset_problems() == []  # rev4c: LAS-b b0 only
    gate_off = c2.C2Config().with_10hz_d1(flat_soil_margin_order_gate=False)
    problems = las_t3.config_problems(gate_off, las_t3.LAS_ON, las_t3.GATE_ON)
    assert len(problems) == 1 and las_t3.GATE_SETTING_KEY in problems[0]
    assert len(las_t3.preset_problems(gate_expected=False)) == 1


def test_t1a_gate_without_r4c30_is_refused() -> None:
    from dataclasses import replace

    config = c2.C2Config().with_10hz_d1()
    no_margin = replace(config, slope_clearance_margin=replace(
        config.slope_clearance_margin, flat_soil_margin_m=0.02))
    problems = las_t3.gate_problems(no_margin, las_t3.GATE_ON)
    assert problems == ["slope_clearance_margin.flat_soil_margin_m 0.02 != 0.03"]
    disabled = replace(config, slope_clearance_margin=replace(
        config.slope_clearance_margin, enable=False))
    assert las_t3.gate_problems(disabled, las_t3.GATE_ON) == [
        "slope_clearance_margin.enable is False"]


BUNDLE_CONDITIONS = {las_t3.R0: (False, las_t3.LAS_OFF), las_t3.R0K: (False, las_t3.LAS_OFF),
                     "T-3a": (True, las_t3.LAS_ON)}


@pytest.mark.parametrize("gate_value", [False, True], ids=["gate_off", "gate_on"])
@pytest.mark.parametrize("bundle", [las_t3.R0, las_t3.R0K, "T-3a"])
def test_t1b_controller_condition_per_bundle(bundle: str, gate_value: bool) -> None:
    las_value, las = BUNDLE_CONDITIONS[bundle]
    controller = SimpleNamespace(config=_config(las_value, gate_value))
    gate = las_t3.BUNDLE_GATE[bundle]
    problems = las_t3.controller_problems(controller, las, gate)
    if gate_value == (gate == las_t3.GATE_ON):
        assert problems == []
    else:
        assert len(problems) == 1 and las_t3.GATE_SETTING_KEY in problems[0]
    assert las_t3.controller_problems(controller, las) == []  # rev4c: no gate check


def _t4h(path: Path, events) -> Path:
    meta = {"commands_sha256": HASH} if events is None else {"commands_sha256": HASH,
                                                             "events": events}
    np.savez(path, meta_json=np.array(json.dumps(meta)))
    return path


def test_t1c_dg3_r4c30_check_finds_events(tmp_path: Path) -> None:
    entries = {"T-3b": []}
    for name, events in (("clean", [[4.0, "INFO_PRESSURE_ZERO_CALIBRATED:FL"]]),
                         ("r4", [[30.0, "INFO_LOC_FLAT_SOIL_MARGIN:1080"]]), ("none", None)):
        _t4h(tmp_path / f"{name}.npz", events)
        entries["T-3b"].append({"line_key": name, "t4h_file": f"{name}.npz"})
    counts = las_t3.dg3_r4c30_counts(entries["T-3b"], tmp_path)
    assert counts == {"clean": 0, "r4": 1, "none": None}
    problems = las_t3.dg3_r4c30_problems(entries, tmp_path)
    assert len(problems) == 2 and "r4" in problems[0] and "none" in problems[1]
    missing = {"T-3b": [{"line_key": "x", "t4h_file": "dg3\\absent.npz"}]}
    assert "not readable" in las_t3.dg3_r4c30_problems(missing, tmp_path)[0]


@pytest.mark.skipif(not HAS_DG3, reason="stored Dg-3 records absent")
def test_t1c_stored_dg3_records_have_no_r4c30() -> None:
    entries = las_t3.rules_entries(las_t3.RULES_REV5)
    counts = las_t3.dg3_r4c30_counts(entries["T-3b"], STORED_V5)
    assert len(counts) == 4 and set(counts.values()) == {0}
    assert las_t3.dg3_r4c30_problems(entries, STORED_V5) == []


def test_t1d_k1_block_keeps_shadow_decisions_with_the_gate_off() -> None:
    decision = {"t_loc_s": 41.2, "dP": -6, "n_P": 406, "n_S": 412, "would_block": True,
                "applied": True, "r4_due_without_gate": True}
    meta = {"liftoff_approach_slow": {"settings": {"enable": False}},
            "slope_clearance_margin": {"order_gate": {"enabled": False,
                                                      "decisions": [decision]}}}
    controller = SimpleNamespace(
        events=[], meta=lambda: meta,
        config=SimpleNamespace(liftoff_approach_slow=SimpleNamespace(enable=False)))
    record = las_t3.las_record(controller, None, with_k1=True)
    assert record["k1"] == {"enabled": False, "decisions": [decision], "would_block_any": True,
                            "applied_any": True, "applied_count": 1, "first_dP": -6,
                            "blocked_t_loc_s": [41.2]}
    assert "k1" not in las_t3.las_record(controller, None)  # rev4c record unchanged
    assert las_t3.k1_record(None)["would_block_any"] is None


def test_t1d_real_controller_meta_has_the_order_gate_record() -> None:
    from outrigger_sim.control.c2 import C2Controller, C2Geometry
    from outrigger_sim.params import load_params

    geometry = C2Geometry.from_params(load_params())
    for gate in (False, True):
        meta = C2Controller(geometry, _config(False, gate)).meta()["slope_clearance_margin"]
        record = las_t3.k1_record(meta["order_gate"])
        assert record["enabled"] is gate and record["decisions"] == []
        assert record["would_block_any"] is False


# ------------------------------------------------------------------------------- T2
class _Probe:
    def with_10hz_d1(self):
        return 1


@pytest.mark.parametrize(
    ("module", "bundle", "is_allowed"),
    [("las_t3_presets", las_t3.R0K, True), ("pre_k1_preset_runner", las_t3.R0K, False),
     ("pre_las_preset_runner", las_t3.R0K, False), ("pre_las_preset_runner", las_t3.R0, True),
     ("las_t3_presets", las_t3.R0, False), ("las_t3_presets", "T-3a", False)],
)
def test_t2a_preset_patch_is_allowed_only_from_the_bundle_module(
        module: str, bundle: str, is_allowed: bool) -> None:
    probe = type("Probe", (), {"with_10hz_d1": _Probe.with_10hz_d1})
    probe.with_10hz_d1.__module__ = module
    found = las_t3.foreign_functions(probe, "home", las_t3.ALLOWED_PRESET_PATCHES[bundle])
    assert (found == []) is is_allowed
    assert las_t3.foreign_functions(probe, "home", ("with_10hz_d1",)) == []  # name-only form


def _run_snippet(code: str) -> dict:
    """Run ``code`` in a new interpreter (a preset patch must not reach this process)."""
    prelude = (f"import sys, json; sys.path[:0] = [{str(HERE)!r}, "
               f"{str(las_t3.ROOT / '03_src')!r}]\n")
    completed = subprocess.run([sys.executable, "-I", "-B", "-c", prelude + code],
                               capture_output=True, text=True, encoding="utf-8",
                               timeout=300, check=False, cwd=str(las_t3.ROOT))
    assert completed.returncode == 0, completed.stderr[-2000:]
    return json.loads(completed.stdout.strip().splitlines()[-1])


def test_t2b_r0k_switch_turns_las_off_and_keeps_the_gate() -> None:
    result = _run_snippet(
        "import las_t3, las_t3_presets\n"
        "from outrigger_sim.control import c2\n"
        "las_t3_presets.install_las_off_gate_on(); las_t3_presets.install_las_off_gate_on()\n"
        "config = c2.C2Config().with_10hz_d1()\n"
        "explicit = c2.C2Config().with_10hz_d1(liftoff_approach_slow=True)\n"
        "print(json.dumps({'las': config.liftoff_approach_slow.enable,\n"
        "  'gate': config.slope_clearance_margin.flat_soil_margin_order_gate,\n"
        "  'explicit_las': explicit.liftoff_approach_slow.enable,\n"
        "  'module': c2.C2Config.with_10hz_d1.__module__,\n"
        "  'r0k': las_t3.wrapper_problems(las_t3.ALLOWED_PRESET_PATCHES['R-0K']),\n"
        "  't3': las_t3.wrapper_problems(las_t3.ALLOWED_PRESET_PATCHES['T-3a']),\n"
        "  'condition': las_t3.config_problems(config, 'off', 'on')}))\n")
    assert result["las"] is False and result["gate"] is True and result["explicit_las"] is True
    assert result["module"] == "las_t3_presets" and result["r0k"] == []
    assert result["condition"] == []
    assert result["t3"] == ["C2Config.with_10hz_d1 from las_t3_presets"]


def test_t2b_r0_switch_turns_both_off() -> None:
    result = _run_snippet(
        "import las_t3\n"
        "from outrigger_sim.control import c2\n"
        "las_t3.switch_preset('R-0')\n"
        "config = c2.C2Config().with_10hz_d1()\n"
        "print(json.dumps({'condition': las_t3.config_problems(config, 'off', 'off'),\n"
        "  'r0': las_t3.wrapper_problems(las_t3.ALLOWED_PRESET_PATCHES['R-0']),\n"
        "  'r0k': las_t3.wrapper_problems(las_t3.ALLOWED_PRESET_PATCHES['R-0K'])}))\n")
    assert result["condition"] == [] and result["r0"] == []
    assert result["r0k"] == ["C2Config.with_10hz_d1 from pre_las_preset_runner"]


def test_build_jobs_carry_the_bundle_condition(tmp_path: Path) -> None:
    entries = [_entry(G1_KEY)]
    conditions = {}
    for bundle in (las_t3.R0, las_t3.R0K, "T-3a"):
        job = las_t3.build_jobs(entries, bundle, "c" * 40, 1, None, tmp_path,
                                rules=las_t3.RULES_REV5)[0]
        conditions[bundle] = (job["t3"]["las"], job["t3"]["gate"], job["t3"]["rules"])
    assert conditions == {las_t3.R0: ("off", "off", "rev5"), las_t3.R0K: ("off", "on", "rev5"),
                          "T-3a": ("on", "on", "rev5")}


# ------------------------------------------------------------------------------- T3
def _run_dg3(env_extra: dict) -> subprocess.CompletedProcess:
    env = {key: value for key, value in os.environ.items() if not key.startswith("LAS_T3_DG3")}
    env.update(env_extra)
    # -X utf8: the condition line prints ③ (-I ignores PYTHONIOENCODING)
    return subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", str(las_t3.DG3_RUNNER),
                           str(las_t3.ROOT),
                           "run", "unused.json"], capture_output=True, text=True,
                          encoding="utf-8", env=env, timeout=600, check=False,
                          cwd=str(las_t3.ROOT))


@pytest.mark.parametrize("value", [None, "", "maybe"], ids=["absent", "empty", "bad"])
def test_t3a_k1_variable_is_required(value: str | None) -> None:
    env = {"LAS_T3_DG3_LAS": "on", "LAS_T3_DG3_P3": "on"}
    if value is not None:
        env["LAS_T3_DG3_K1"] = value
    completed = _run_dg3(env)
    assert completed.returncode != 0
    assert "LAS_T3_DG3_K1 must be one of" in completed.stderr


def test_t3b_gate_on_asked_with_the_r0_switch_is_refused() -> None:
    completed = _run_dg3({"LAS_T3_DG3_LAS": "off", "LAS_T3_DG3_P3": "on",
                          "LAS_T3_DG3_K1": "on"})
    assert completed.returncode != 0
    assert "K1 gate on (preset False)" in completed.stdout
    assert "the preset has the K1 gate False, LAS_T3_DG3_K1=on" in completed.stderr


def test_t3c_recorded_settings_carry_the_gate_key() -> None:
    code =(f"import os; os.environ.update(LAS_T3_DG3_LAS='on', LAS_T3_DG3_P3='on')\n"
            f"sys.path.insert(0, {str(las_t3.DG3_RUNNER.parent)!r})\n"
            "import las_t3_dg3 as d\n"
            "from outrigger_sim.control import c2\n"
            "s = d.final.controller_settings(c2.C2Config().with_10hz_d1())\n"
            "print(json.dumps({'gate': s.get(d.GATE_SETTING_KEY),\n"
            "  'listed': d.GATE_SETTING_KEY in d.final.RECORDED_SETTINGS,\n"
            "  'margin': s.get('slope_clearance_margin.flat_soil_margin_m')}))\n")
    result = _run_snippet(code)
    assert result == {"gate": True, "listed": True, "margin": 0.03}


# ------------------------------------------------------------------------------- T4
def test_t4a_tag_constants_are_the_v5_options_tags() -> None:
    assert tj.TAG_V0_K1 == v5_options.with_order_gate_tag(None)
    assert tj.TAG_P3_K1 == v5_options.with_order_gate_tag(
        v5_options.EXTEND_START_CONTROLLER_TAG)
    assert tj.TAG_V0_LAS_K1 == v5_options.LAS_K1_CONTROLLER_TAG
    assert tj.TAG_P3_LAS_K1 == v5_options.EXTEND_START_LAS_K1_CONTROLLER_TAG
    assert tj.TAG_V0_K1 == v5_options.with_switch_tags(None, _config(False, True))
    assert tj.TAG_P3_LAS_K1 == v5_options.with_switch_tags(tj.TAG_P3, _config(True, True))
    assert las_t3.GATE_SETTING_KEY == "slope_clearance_margin.flat_soil_margin_order_gate"


def _stored_dg3(tmp_path: Path, folder: str, settings: dict) -> dict:
    key = "cand=current#L3|s2|ref|14|G1|B|0,0"
    entry = {"line_key": las_t3.dg3_line_key(folder, key), "kind": las_t3.KIND_DG3, "key": key,
             "folder": folder, "result_file": f"dg3\\{folder}\\r.json",
             "shadow_commands_sha256_all_folders": [HASH]}
    record = {"key": key, "v5_setting": "VB", "hydraulic_options": {}, "controller_settings":
              settings}
    path = tmp_path / "dg3" / folder / "r.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"meta": {"preset_settings": {
        "two_pressure.extend_start_rule": "constant"}}, "results": [record]}), encoding="utf-8")
    return entry


def test_t4b_only_the_exact_gate_key_is_left_out(tmp_path: Path) -> None:
    stored = {"slope_clearance_margin.enable": True,
              "slope_clearance_margin.flat_soil_margin_m": 0.03,
              "two_pressure.extend_start_rule": "constant"}
    entry = _stored_dg3(tmp_path, "off", stored)
    settings = {**stored, las_t3.GATE_SETTING_KEY: True, "liftoff_approach_slow.enable": True}
    line = {"job": {}, "controller_tag": tj.TAG_V0_LAS_K1, "v5_setting": "VB",
            "hydraulic_options": {}, "extend_start_rule": "constant",
            "controller_settings": settings, "las_t3": {"enable": True}}
    assert tj.condition_problems(entry, line, True, tmp_path, gate_on=True) == []
    assert tj.condition_problems(entry, line, True, tmp_path) != []  # rev4c: _LAS tag
    changed = {**line, "controller_settings": {
        **settings, "slope_clearance_margin.flat_soil_margin_m": 0.02}}
    problems = tj.condition_problems(entry, changed, True, tmp_path, gate_on=True)
    assert len(problems) == 1 and "flat_soil_margin_m" in problems[0]
    assert tj.first_stop({"K-3": {entry["line_key"]: problems}}) == "H-T3-3"
    gate_off = {**line, "controller_settings": {**settings, las_t3.GATE_SETTING_KEY: False}}
    assert tj.condition_problems(entry, gate_off, True, tmp_path, gate_on=True) == [
        "K1 gate False != bundle True"]


# ------------------------------------------------------------------------------- T5
TAG_CELLS = [
    # (kind, setting / folder, las_on, gate_on, expected)
    ("d1", "V0", False, False, None), ("d1", "VB", False, False, tj.TAG_P3),
    ("dg3", "off", False, False, None), ("dg3", "v4_on", False, False, tj.TAG_P3),
    ("d1", "V0", False, True, tj.TAG_V0_K1), ("d1", "VB", False, True, tj.TAG_P3_K1),
    ("d1", "V0", True, True, tj.TAG_V0_LAS_K1), ("d1", "VB", True, True, tj.TAG_P3_LAS_K1),
    ("dg3", "off", True, True, tj.TAG_V0_LAS_K1), ("dg3", "v4_on", True, True, tj.TAG_P3_LAS_K1),
]


def _tag_entry(kind: str, where: str) -> tuple[dict, dict]:
    if kind == "d1":
        return _entry(), {"job": {"setting": where}}
    return {"kind": las_t3.KIND_DG3, "folder": where, "line_key": "dg3"}, {"job": {}}


@pytest.mark.parametrize(("kind", "where", "las_on", "gate_on", "expected"), TAG_CELLS)
def test_t5a_expected_tags_of_rev5(kind, where, las_on, gate_on, expected) -> None:
    entry, line = _tag_entry(kind, where)
    assert tj.expected_tag(entry, line, las_on, gate_on) == expected


def test_t5a_conditions_without_a_tag_raise() -> None:
    entry, line = _tag_entry("dg3", "off")
    with pytest.raises(ValueError, match="no Dg-3 line in R-0K"):
        tj.expected_tag(entry, line, False, True)
    with pytest.raises(ValueError, match="LAS-b True and the gate False"):
        tj.expected_tag(*_tag_entry("d1", "V0"), True, False)
    assert tj.expected_tag(*_tag_entry("d1", "V0"), True) == tj.TAG_V0_LAS  # rev4c table


def test_t5a_las_without_k1_and_fb_tags_are_refused() -> None:
    entry = _entry()
    good = _line(entry, "T-3a", tag=tj.TAG_V0_LAS_K1, las=True)
    assert tj.tag_problems(entry, good, True, True) == []
    las_only = _line(entry, "T-3a", tag=tj.TAG_V0_LAS, las=True)
    problems = tj.tag_problems(entry, las_only, True, True)
    assert problems[0] == "tag final_C4G2_LAS has _LAS without _K1"
    fb = _line(entry, "T-3a", tag="final_C4G2_LAS_FB_K1", las=True)
    assert tj.tag_problems(entry, fb, True, True)[0].endswith("has _FB")
    no_record = {**good, "las_t3": {"enable": True}}
    assert tj.tag_problems(entry, no_record, True, True) == ["K1 gate state not recorded"]


def test_t5b_k5_against_the_baseline_of_each_key() -> None:
    inside, outside = _entry(UNIFORM_KEY, "uniform_r4"), _entry(OUTSIDE_KEY)
    r0k_line = _line(inside, las_t3.R0K, tag=tj.TAG_V0_K1, sha=OTHER)
    baseline = {**_stored(inside, sha=HASH), **_stored(outside, sha=HASH)}
    b_of_k = tj.baseline_lines([r0k_line], [inside], baseline)
    entries = {"T-3a": [inside, outside], "T-3b": [], "T-3c": []}
    keys = frozenset({UNIFORM_KEY})

    def k5(lines):
        criteria, _ = tj.t3_criteria(lines, entries, b_of_k, gate_on=True, r0k_keys=keys)
        return criteria["K-5"]

    silent = dict(tag=tj.TAG_V0_LAS_K1, las=True)
    assert k5([_line(inside, "T-3a", sha=OTHER, **silent),
               _line(outside, "T-3a", sha=HASH, **silent)]) == {}
    found = k5([_line(inside, "T-3a", sha=HASH, **silent),  # stored hash, not the R-0K one
                _line(outside, "T-3a", sha=HASH, blocked=True, **silent)])
    assert set(found) == {UNIFORM_KEY, OUTSIDE_KEY}
    assert "premise G-c" in found[OUTSIDE_KEY]
    blocked_inside = k5([_line(inside, "T-3a", sha=OTHER, blocked=True, **silent),
                         _line(outside, "T-3a", sha=HASH, **silent)])
    assert blocked_inside == {}  # a blocked R-0K key is judged by its R-0K hash only
    assert tj.first_stop({"K-5": found}, tj.STOP_ORDER_REV5) == "H-T3-5"


def _r0k(entries, lines, baseline):
    criteria, rows = tj.r0k_criteria(lines, entries, baseline)
    return criteria, rows, tj.first_stop(criteria, tj.STOP_ORDER_REV5)


def test_t5c_r0k_stops() -> None:
    uniform, no_r4 = _r0k_entry(UNIFORM_KEY, "uniform_r4"), _r0k_entry(G1_KEY, "r0_no_r4")
    entries = [uniform, no_r4]
    baseline = {**_stored(uniform), **_stored(no_r4)}
    good = [_line(uniform, las_t3.R0K, tag=tj.TAG_V0_K1),
            _line(no_r4, las_t3.R0K, tag=tj.TAG_V0_K1)]
    criteria, rows, stop = _r0k(entries, good, baseline)
    assert stop is None and len(rows) == 2 and rows[0]["stored_hash"] is True
    blocked = [_line(uniform, las_t3.R0K, tag=tj.TAG_V0_K1, sha=OTHER, blocked=True), good[1]]
    criteria, _, stop = _r0k(entries, blocked, baseline)
    assert stop == "H-T3-1Q" and tj.stop_exit_code(stop) == 2
    assert criteria["K-2K-iv"][UNIFORM_KEY]["blocked"][0]["dP"] == -5
    assert criteria["K-2K-iv"][UNIFORM_KEY]["hash"] == [OTHER, HASH]
    moved = [good[0], _line(no_r4, las_t3.R0K, tag=tj.TAG_V0_K1, sha=OTHER)]
    criteria, _, stop = _r0k(entries, moved, baseline)
    assert stop == "H-T3-1K" and tj.stop_exit_code(stop) == 1
    assert set(criteria["K-2K-ii"]) == set(criteria["K-2K-iii"]) == {G1_KEY}
    no_r4_blocked = [good[0], _line(no_r4, las_t3.R0K, tag=tj.TAG_V0_K1, blocked=True)]
    assert _r0k(entries, no_r4_blocked, baseline)[2] == "H-T3-1K"
    wrong_tag = [_line(uniform, las_t3.R0K, tag=None), good[1]]
    criteria, _, stop = _r0k(entries, wrong_tag, baseline)
    assert stop == "H-T3-3" and "tag None != final_C4G2_K1" in criteria["K-2K-i"][UNIFORM_KEY]
    gate_off = [_line(uniform, las_t3.R0K, tag=tj.TAG_V0_K1, gate=False), good[1]]
    assert _r0k(entries, gate_off, baseline)[2] == "H-T3-3"
    assert _r0k(entries, [good[1]], baseline)[2] == "H-T3-3"  # K-1K: a key without a line


def test_t5c_patch_keys_may_block_and_order_of_stops() -> None:
    patch = _r0k_entry("D1|H-S-A-J2|G1+J2@FL|T|flat|K1|V0|e0", "patch_r4")
    baseline = _stored(patch)
    line = _line(patch, las_t3.R0K, tag=tj.TAG_V0_K1, sha=OTHER, blocked=True)
    assert _r0k([patch], [line], baseline)[2] is None  # patch_r4: recorded only
    both = {"K-2K-ii": {"a": "x"}, "K-2K-iv": {"b": {}}, "K-5": {"c": "y"}}
    assert tj.first_stop(both, tj.STOP_ORDER_REV5) == "H-T3-1K"
    assert tj.exit_code({"stops": ["H-T3-1Q", "H-T3-5"]}) == 2
    assert tj.exit_code({"stops": ["H-T3-1K"]}) == 1


def test_t5d_k6_reads_the_r0k_line_for_an_r0k_key() -> None:
    entry = _entry(UNIFORM_KEY, "uniform_r4")
    r0k_line = _line(entry, las_t3.R0K, tag=tj.TAG_V0_K1, sha=OTHER, ready=60.0)
    r0k_line["d1"]["items"]["G6-2_loc"] = False
    baseline = _stored(entry, ready=100.0)
    b_of_k = tj.baseline_lines([r0k_line], [entry], baseline)
    assert b_of_k[UNIFORM_KEY] is r0k_line
    fired = _line(entry, "T-3a", tag=tj.TAG_V0_LAS_K1, sha="3" * 64, fired=True, las=True,
                  ready=70.0)
    entries = {"T-3a": [entry], "T-3b": [], "T-3c": []}
    keys = frozenset({UNIFORM_KEY})
    criteria, k7 = tj.t3_criteria([fired], entries, b_of_k, gate_on=True, r0k_keys=keys)
    assert "C5'-R" in criteria["K-6"][UNIFORM_KEY]  # READY 70 s against the R-0K 60 s
    stored_only, _ = tj.t3_criteria([fired], entries, baseline, gate_on=True)
    assert UNIFORM_KEY not in stored_only["K-6"]  # against d1.jsonl (100 s) it would pass
    assert k7[0]["baseline_source"] == las_t3.R0K and k7[0]["would_block_any"] is False
    missing = tj.baseline_lines([], [entry], baseline)
    criteria, _ = tj.t3_criteria([fired], entries, missing, gate_on=True, r0k_keys=keys)
    assert UNIFORM_KEY in criteria["K-6-undecidable"]


def test_r0_gate_of_rev5_checks_the_gate_off(tmp_path: Path) -> None:
    entry = _entry(G1_KEY)
    good = _line(entry, las_t3.R0, tag=None, gate=False)
    assert tj.first_stop(tj.r0_criteria([good], [entry], _stored(entry), gate_on=False)) is None
    gate_on = _line(entry, las_t3.R0, tag=None, gate=True)
    criteria = tj.r0_criteria([gate_on], [entry], _stored(entry), gate_on=False)
    assert criteria["K-2"][G1_KEY] == ["K1 gate True != bundle False"]
    assert tj.first_stop(tj.r0_criteria([gate_on], [entry], _stored(entry))) is None  # rev4c


def _write_jsonl(path: Path, header: dict, lines: list[dict]) -> Path:
    text = "".join(json.dumps(record) + "\n" for record in [{"header": header}, *lines])
    path.write_text(text, encoding="utf-8")
    return path


def test_judge_t3_rev5_end_to_end_on_a_small_key_list(tmp_path: Path) -> None:
    """A three-key list through ``judge_t3`` (counts and seals are not the sealed ones, so K-0
    and K-1K fail by design; the other criteria are the point)."""
    inside, outside = _entry(UNIFORM_KEY, "uniform_r4"), _entry(OUTSIDE_KEY)
    r0_entry = _entry(G1_KEY)
    baseline = {**_stored(inside), **_stored(outside), **_stored(r0_entry)}
    baseline_path = tmp_path / "d1.jsonl"
    baseline_path.write_text("".join(json.dumps({**record, "d1": {**record["d1"], "key": key}})
                                     + "\n" for key, record in baseline.items()),
                             encoding="utf-8")
    keys = {"d1_baseline": {"sha256": hashlib.sha256(baseline_path.read_bytes()).hexdigest()},
            "R-0": {"d1": [G1_KEY], "dg3": []}, "T-3b": [], "T-3c": [],
            "T-3a": [{"key": key, "base": "J1", "commands_sha256": HASH, "verdict": "pass",
                      "fail_items": [], "P3-2": True, "t_ready_s": 60.0, "stroke_max_m": 0.4,
                      "fault_names": []} for key in (UNIFORM_KEY, OUTSIDE_KEY)]}
    keys_path = tmp_path / "keys.json"
    keys_path.write_text(json.dumps(keys), encoding="utf-8")
    r0k_keys_path = tmp_path / "r0k.json"
    r0k_keys_path.write_text(json.dumps({"R-0K": [{
        "key": UNIFORM_KEY, "class": "uniform_r4", "stored_commands_sha256": HASH,
        "stored_controller_tag": None, "stored_verdict": "pass", "stored_r4c30_count": 0}]}),
        encoding="utf-8")
    header = {"identity": IDENTITY}
    r0 = _write_jsonl(tmp_path / las_t3.R0_FILE, header,
                      [_line(r0_entry, las_t3.R0, tag=None, gate=False)])
    _write_jsonl(tmp_path / las_t3.R0K_FILE, header,
                 [_line(inside, las_t3.R0K, tag=tj.TAG_V0_K1, sha=OTHER)])
    t3 = _write_jsonl(tmp_path / las_t3.T3_FILE, header, [
        _line(inside, "T-3a", tag=tj.TAG_V0_LAS_K1, las=True, sha=OTHER),
        _line(outside, "T-3a", tag=tj.TAG_V0_LAS_K1, las=True, blocked=True)])
    result = tj.judge_t3(r0, t3, keys_path, baseline_path, las_t3.RULES_DIR,
                         r0k_keys_path=r0k_keys_path)
    criteria = result["criteria"]
    assert result["rules"] == "rev5" and result["counts"]["R-0K"] == 1
    assert criteria["K-2K-ii"] == {UNIFORM_KEY: criteria["K-2K-ii"][UNIFORM_KEY]}
    assert set(criteria["K-5"]) == {OUTSIDE_KEY}  # inside: R-0K hash; outside: blocked
    assert criteria["K-2"] == {} and criteria["K-3"] == {} and criteria["K-6"] == {}
    assert result["stops"][:2] == ["H-T3-0", "H-T3-3"] and tj.exit_code(result) == 2
    assert "R-0K record" in "\n".join(tj.report_lines(result))


# ------------------------------------------------------------------------------- T6
def test_t6a_sealed_r0k_list_shape() -> None:
    entries = las_t3.rules_entries(las_t3.RULES_REV5)
    assert las_t3.r0k_key_problems(entries[las_t3.R0K], entries) == []
    assert las_t3.key_list_digest([e["line_key"] for e in entries[las_t3.R0K]]) == \
        las_t3.R0K_LIST_SHA256
    doc = las_t3.load_r0k_key_list()
    assert doc["count"] == 45 and doc["class_counts"] == las_t3.R0K_CLASS_COUNTS
    assert doc["run_condition"]["tags"] == {"V0": tj.TAG_V0_K1, "VB": tj.TAG_P3_K1}
    relabelled = [*entries[las_t3.R0K][:-1], {**entries[las_t3.R0K][-1], "class": "uniform_r4"}]
    assert len(las_t3.r0k_key_problems(relabelled, entries)) == 1  # classes
    dropped = entries[las_t3.R0K][:-1]
    assert len(las_t3.r0k_key_problems(dropped, entries)) == 3  # count, digest, classes
    foreign = [*dropped, {**entries[las_t3.R0K][-1], "line_key": "D1|X"}]
    assert any("not D-1 keys" in p for p in las_t3.r0k_key_problems(foreign, entries))


def test_t6a_seals_of_rev5() -> None:
    assert las_t3.T3_REQUIRED_SEALS[-2:] == ("rev5", "rev5_r0k_keys")
    assert len(las_t3.T3_REQUIRED_SEALS) == 11 and len(las_t3.REV4C_REQUIRED_SEALS) == 9
    assert lt.seal_problems(las_t3.RULES_DIR, las_t3.T3_REQUIRED_SEALS) == []
    assert hashlib.sha256(MAKE_SCRIPT.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == \
        MAKE_SCRIPT_SHA256


@pytest.mark.skipif(not HAS_D1, reason="stored d1.jsonl absent")
def test_t6a_r0k_list_is_rebuilt_from_d1(tmp_path: Path) -> None:
    root = tmp_path / "root"
    rules = root / "06_analysis" / "02_control" / "verif_matrix"
    v5 = root / "06_analysis" / "03_hydraulic" / "coupled" / "v5"
    rules.mkdir(parents=True)
    v5.mkdir(parents=True)
    shutil.copy(las_t3.KEYS_PATH, rules / las_t3.KEYS_PATH.name)
    shutil.copy(STORED_V5 / "d1.jsonl", v5 / "d1.jsonl")
    out = tmp_path / "r0k.json"
    subprocess.run([sys.executable, "-I", "-B", str(MAKE_SCRIPT), str(root), str(out)],
                   capture_output=True, check=True, timeout=300)
    rebuilt = json.loads(out.read_text(encoding="utf-8"))
    sealed = las_t3.load_r0k_key_list()
    assert rebuilt == sealed
    assert [(e["key"], e["class"]) for e in rebuilt["R-0K"]] == [
        (e["key"], e["class"]) for e in sealed["R-0K"]]


def test_t6b_r0_baseline_is_the_same_in_both_modes() -> None:
    rev4c = las_t3.rules_entries(las_t3.RULES_REV4C)
    rev5 = las_t3.rules_entries(las_t3.RULES_REV5)
    assert rev4c[las_t3.R0] == rev5[las_t3.R0] and las_t3.R0K not in rev4c
    assert {bundle: len(group) for bundle, group in rev4c.items()} == las_t3.EXPECTED_COUNTS
    dg3 = [e for e in rev5[las_t3.R0] if e["kind"] == las_t3.KIND_DG3]
    assert [tj.baseline_hash(e, {}) for e in dg3] == [
        e["shadow_commands_sha256_all_folders"][0] for e in dg3]


@pytest.mark.skipif(not HAS_D1, reason="stored d1.jsonl absent")
def test_t6b_r0_d1_baselines_and_r0k_stored_fields_equal_d1() -> None:
    baseline = tj.load_baseline(STORED_V5 / "d1.jsonl")
    rev5 = las_t3.rules_entries(las_t3.RULES_REV5)
    assert tj.r0k_key_list_problems(rev5[las_t3.R0K], baseline) == []
    r0_hashes = {e["line_key"]: tj.baseline_hash(e, baseline) for e in rev5[las_t3.R0]}
    assert None not in r0_hashes.values() and r0_hashes[G1_KEY].startswith("f805759d")
    b_of_k = tj.baseline_lines([], rev5[las_t3.R0K], baseline)
    assert {e["line_key"] for e in rev5[las_t3.R0K]}.isdisjoint(b_of_k)


# ------------------------------------------------------------------------------- tool
def test_rev5_output_paths_and_header(tmp_path: Path) -> None:
    (tmp_path / las_t3.R0K_FILE).write_text("", encoding="utf-8")
    problems = las_t3.preflight(tmp_path, las_t3.RULES_REV5, entries=None)
    assert f"output exists: {tmp_path / las_t3.R0K_FILE}" in problems
    assert las_t3.R0K_FILE not in [p.name for p in las_t3.output_paths(tmp_path)]  # rev4c
    header = las_t3.header_record(IDENTITY, tmp_path, (las_t3.R0K,), las_t3.RULES_REV5)["header"]
    assert len(header["seals"]) == 11 and header["expected_counts"] == {las_t3.R0K: 45}
    assert header["conditions"] == {las_t3.R0K: {"las": "off", "gate": "on"}}
    old = las_t3.header_record(IDENTITY, tmp_path, (las_t3.R0,))["header"]
    assert len(old["seals"]) == 9 and "conditions" not in old
    assert las_t3.OUT_DIR_REV5.as_posix().endswith("v5/las/t3_k1")


def test_cli_modes(capsys) -> None:
    assert las_t3.main(["list", "--rules", "rev5"]) == 0
    counts = json.loads(capsys.readouterr().out.strip().splitlines()[-1])["counts"]
    assert counts == {**las_t3.EXPECTED_COUNTS, las_t3.R0K: 45}
    with pytest.raises(SystemExit):
        las_t3.main(["run", "--workers", "1", "--rules", "rev4c", "--only", "R-0K"])
    args = las_t3._parse_args(["run", "--workers", "1"])
    assert args.rules == "rev5" and args.out_dir == las_t3.OUT_DIR_REV5
    assert las_t3._parse_args(["run", "--workers", "1", "--rules", "rev4c"]).out_dir == \
        las_t3.OUT_DIR
    judge_argv = las_t3._judge_argv(args)
    assert judge_argv[judge_argv.index("--t3-rules") + 1] == "rev5" and "--r0k" in judge_argv
