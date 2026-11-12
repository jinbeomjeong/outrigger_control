"""436.8 v5 resume tools (rules ``v5_resume_4368_rules.md``): record block, path 1 judge, steps, u3_judge_k1.

Synthetic inputs only; no harness or Chrono run.
"""

from __future__ import annotations

import difflib
import importlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
SCRIPTS = ROOT / "06_analysis" / "02_control" / "verif_matrix" / "scripts"
for _path in (COUPLED, SCRIPTS, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import resume4368_judge as judge  # noqa: E402
import resume_k1_record as record  # noqa: E402
import run_v5  # noqa: E402


# ------------------------------------------------------------------------------------------- fakes
@dataclass
class _Event:
    t_s: float
    name: str


@dataclass
class _Margin:
    flat_soil_margin_order_gate: bool = True


@dataclass
class _Config:
    slope_clearance_margin: _Margin = field(default_factory=_Margin)


class _Controller:
    def __init__(self, *, start_s=None, decisions=(), events=(), gate=True) -> None:
        self.config = _Config(_Margin(gate))
        self.events = [_Event(1.0, name) for name in events]
        self._meta = {
            "liftoff_approach_slow": {
                "settings": dict(judge.LAS_PRESET, end_ramp_periods=3),
                "start_s": start_s,
                "end_s": None,
                "end_reason": None,
            },
            "slope_clearance_margin": {
                "settings": {"flat_soil_margin_order_gate": gate, "flat_soil_margin_m": 0.03},
                "order_gate": {"enabled": gate, "decisions": list(decisions)},
            },
        }

    def meta(self) -> dict:
        return self._meta


def _decision(*, would_block=False, due=False, applied=False) -> dict:
    return {
        "t_loc_s": 10.0,
        "would_block": would_block,
        "r4_due_without_gate": due,
        "applied": applied,
    }


def _line(block: dict, *, group: str = "H-R-0", sha: str = "a") -> dict:
    return {
        "job": {"d1": {"key": "D1|x", "group": group}, "setting": "VB", "eps": 0.0},
        "commands_sha256": sha,
        "controller_tag": judge.TAG_P3,
        judge.RECORD_KEY: block,
    }


# ------------------------------------------------------------------------------------ record block
def test_record_block_reads_meta_and_counts_events() -> None:
    names = (
        "INFO_LOC_FLAT_SOIL_MARGIN:80",
        "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order",
        "soil_mode_start",
    )
    block = record.controller_record(
        _Controller(start_s=3.2, decisions=[_decision()], events=names)
    )
    assert block["applicable"] is True and block["k1_order_gate_request"] == "preset"
    assert block["k1_order_gate_effective"] is True
    assert block["liftoff_approach_slow"]["start_s"] == 3.2
    assert set(block["liftoff_approach_slow"]["settings"]) == set(record.LAS_SETTING_NAMES)
    assert block["event_counts"] == {
        "flat_soil_margin_applied": 1,
        "flat_soil_margin_skipped_order": 1,
        "soil_mode_start": 1,
    }
    json.dumps(block)


def test_record_block_keeps_a_missing_start_missing() -> None:
    controller = _Controller()
    del controller._meta["liftoff_approach_slow"]["start_s"]
    block = record.controller_record(controller)
    assert "start_s" not in block["liftoff_approach_slow"]
    assert judge.classification_inputs(block)[1] == "liftoff_approach_slow.start_s missing"


def test_record_block_without_c2_config() -> None:
    class Ind:
        events: list = []

    assert record.controller_record(Ind())["applicable"] is False


def test_record_key_constants_match() -> None:
    assert record.RECORD_KEY == judge.RECORD_KEY == run_v5.RESUME_K1_KEY


def test_las_preset_is_the_c2_preset() -> None:
    c2 = pytest.importorskip("outrigger_sim.control.c2")
    preset = c2.C2Config().with_10hz_d1().liftoff_approach_slow
    assert {name: getattr(preset, name) for name in judge.LAS_PRESET} == judge.LAS_PRESET
    assert c2.C2Config().with_10hz_d1().slope_clearance_margin.flat_soil_margin_order_gate is True


# ------------------------------------------------------------------------------------ 4.2 check
def test_harness_record_check() -> None:
    good = _line(record.controller_record(_Controller()))
    assert judge.harness_record_problems(good) == []
    off = _line(record.controller_record(_Controller(gate=False)))
    assert any("k1_order_gate_effective" in p for p in judge.harness_record_problems(off))
    token = {**good, "job": {**good["job"], "candidate": "K1on"}}
    assert any("K1on" in p for p in judge.harness_record_problems(token))
    assert judge.harness_record_problems({"job": {}}) == [f"{judge.RECORD_KEY} block missing"]


def test_block_under_v5_is_found() -> None:
    screen = {
        "id": "H1|J1|B|top|flat",
        "v5": {
            "controller_tag": judge.TAG_V0,
            judge.RECORD_KEY: record.controller_record(_Controller()),
        },
    }
    runs = list(judge.run_records({"records": [screen]}))
    assert [r for _, r in runs] == [screen]
    assert judge.harness_record_problems(screen) == []


def test_chrono_argv_problems() -> None:
    base = ["run_S9.py", "level", "--threads", "4", "--expect-controller", judge.TAG_P3]
    assert (
        judge.chrono_argv_problems(
            base, {"OMP_WAIT_POLICY": "PASSIVE"}, is_c4_off=False, is_scm=True
        )
        == []
    )
    bad = judge.chrono_argv_problems(
        base + ["--k1-order-gate", "preset"],
        {"OUTRIGGER_HULL_HOOK": "fast"},
        is_c4_off=False,
        is_scm=True,
    )
    assert bad == [
        "forbidden option --k1-order-gate preset",
        "forbidden env OUTRIGGER_HULL_HOOK='fast'",
    ]
    off = base + ["--las-off", "--k1-order-gate", "on"]
    assert judge.chrono_argv_problems(off, {}, is_c4_off=True, is_scm=True) == []
    assert judge.chrono_argv_problems(base + ["--las-off"], {}, is_c4_off=True, is_scm=True) == [
        "C-4 off arm needs --k1-order-gate on"
    ]
    runner = ["x/05_tests/unit/pre_k1_preset_runner.py", *base]
    assert judge.chrono_argv_problems(runner, {}, is_c4_off=False, is_scm=True) == [
        "pre_*_preset_runner.py in the argv"
    ]


def test_chrono_result_problems() -> None:
    result = {
        "c2_setup": {"k1_order_gate": "preset", "k1_order_gate_effective": True},
        "controller_meta": {
            "slope_clearance_margin": {"settings": {"flat_soil_margin_order_gate": True}},
            "liftoff_approach_slow": {"settings": dict(judge.LAS_PRESET)},
        },
    }
    assert judge.chrono_result_problems(result, is_c4_off=False) == []
    result["c2_setup"]["k1_order_gate"] = "on"
    assert judge.chrono_result_problems(result, is_c4_off=False) == [
        "c2_setup.k1_order_gate 'on' != 'preset'"
    ]


# ------------------------------------------------------------------------------------------- 7.2
@pytest.mark.parametrize(
    ("start_s", "decisions", "klass"),
    [
        (None, [], judge.CLASS_INACTIVE),
        (None, [_decision(due=True, applied=True)], judge.CLASS_INACTIVE),
        (4.0, [], judge.CLASS_LAS),
        (None, [_decision(would_block=True, due=True)], judge.CLASS_K1),
        (4.0, [_decision(would_block=True, due=True)], judge.CLASS_BOTH),
        (None, [_decision(would_block=True, due=False)], judge.CLASS_UNDECIDABLE),
    ],
)
def test_classify(start_s, decisions, klass) -> None:
    assert judge.classify({"start_s": start_s, "decisions": decisions})[0] == klass


def test_class_row_stops() -> None:
    blocked = record.controller_record(
        _Controller(decisions=[_decision(would_block=True, due=True)])
    )
    row = judge._class_row("k", blocked, "patch_or_sink", None, 1, {})
    assert row["class"] == judge.CLASS_K1 and row["stops"] == []
    row = judge._class_row("k", blocked, "patch_or_sink", None, 0, {})
    assert row["stops"] == ["S-5 _SKIPPED:order events 0 != blocked decisions 1"]
    row = judge._class_row("k", blocked, "uniform", None, 1, {})
    assert row["class"] == judge.CLASS_K1_UNIFORM and row["stops"] == [
        "S-6 K1 block on a uniform soft-soil family"
    ]
    both = record.controller_record(
        _Controller(decisions=[_decision(would_block=True, due=True, applied=True)])
    )
    assert (
        "S-5 applied and would_block together"
        in judge._class_row("k", both, None, None, 1, {})["stops"]
    )


def test_las_off_arm_is_its_own_class() -> None:
    """436.8 Q-6: a LAS-off run (no start_s) is 'LAS 없음' with its basis keys, not 판정 불가."""
    controller = _Controller(decisions=[_decision(would_block=True, due=True)],
                             events=["INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order"])
    del controller._meta["liftoff_approach_slow"]["start_s"]
    controller._meta["liftoff_approach_slow"]["settings"]["enable"] = False
    block = record.controller_record(controller)
    row = judge._class_row("k", block, "patch_or_sink", None, 1, {})
    assert row["class"] == judge.CLASS_NO_LAS and row["k1_state"] == judge.K1_STATE_BLOCKED
    assert row["las_absent_basis"] == {judge.LAS_ENABLE_PATH: False} and row["stops"] == []
    meta = {"liftoff_approach_slow": {"settings": {}},
            "slope_clearance_margin": {"order_gate": {"decisions": []}}}
    row = judge._class_row("c4off", meta, "patch_or_sink", None, 0, {}, las_off_flag=True)
    assert row["class"] == judge.CLASS_NO_LAS and row["las_absent_basis"] == {"args.las_off": True}
    assert row["k1_state"] == judge.K1_STATE_INACTIVE
    assert judge._class_row("x", meta, None, None, 0, {})["class"] == judge.CLASS_UNDECIDABLE


def test_inactive_hash_check() -> None:
    block = record.controller_record(_Controller())
    row = judge._class_row("k", block, "patch_or_sink", "a", 0, {"k": "b"})
    assert row["hash_check"] == {"anchor": "b", "run": "a", "same": False}
    assert row["stops"] == ["S-5 미작동 run hash differs from its anchor"]


def test_families() -> None:
    assert judge.harness_family(_line({}, group="H-S-0")) == "uniform"
    assert judge.harness_family(_line({}, group="H-S-A")) == "patch_or_sink"
    assert judge.harness_family({"id": "x"}) is None
    scm = {"argv": ["run_S9.py", "level", "--soil", "J2"]}
    assert judge.chrono_family(scm) == "uniform"
    assert judge.chrono_family({"argv": [*scm["argv"], "--soil-patch", "FL:J1"]}) == "patch_or_sink"
    assert judge.chrono_family({"argv": ["run_S8C.py", "run"]}) == "rigid"


def test_k1_class_cli(tmp_path) -> None:
    path = tmp_path / "h1_d1.jsonl"
    lines = [
        _line(record.controller_record(_Controller())),
        _line(
            record.controller_record(
                _Controller(
                    decisions=[_decision(would_block=True, due=True)],
                    events=["INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order"],
                )
            ),
            group="H-S-0",
        ),
    ]
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    out = tmp_path / "k1.json"
    assert judge.main(["k1-class", "--harness", str(path), "--out", str(out)]) == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["counts"] == {judge.CLASS_INACTIVE: 1, judge.CLASS_K1_UNIFORM: 1}


# ------------------------------------------------------------------------------------------- 7.3
def test_parse_controller_events() -> None:
    items = [
        "C2Event(t_s=7.1999999999965585, name='INFO_PRESSURE_ZERO_CALIBRATED:FL')",
        "C2Event(t_s=30.1, name='INFO_LOC_FLAT_SOIL_MARGIN:80')",
    ]
    events, bad = judge.parse_controller_events(items)
    assert bad == [] and events[1] == (30.1, "INFO_LOC_FLAT_SOIL_MARGIN:80")
    assert judge.jp_row_conditions(events)["k1_no_effect"] is False
    assert judge.parse_controller_events(["garbage"])[0] is None
    skipped = [(1.0, "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order")]
    assert judge.jp_row_conditions(skipped)["k1_no_effect"] is True


def test_jp_reuse_cli(tmp_path) -> None:
    rows = []
    shadow = []
    for index in range(2):
        folder = tmp_path / f"v5jp_VB_{index}" / "N_G4_Fs0_pressure"
        folder.mkdir(parents=True)
        events = ["C2Event(t_s=1.0, name='crawler_liftoff_confirmed')"]
        if index == 1:
            events.append("C2Event(t_s=2.0, name='soil_mode_start')")
        (folder / "controller_events.json").write_text(json.dumps(events), encoding="utf-8")
        shadow.append(
            {
                "job": {"chrono_run": f"v5jp_VB_{index}/N_G4_Fs0_pressure"},
                "status": "silent",
                "first_fire_t_s": None,
            }
        )
        rows.append(str(folder))
    shadow_path = tmp_path / "shadow.jsonl"
    shadow_path.write_text("".join(json.dumps(s) + "\n" for s in shadow), encoding="utf-8")
    out = tmp_path / "jp.json"
    code = judge.main(
        [
            "jp-reuse",
            "--shadow",
            str(shadow_path),
            "--rows",
            *rows,
            "--expected",
            "2",
            "--out",
            str(out),
        ]
    )
    report = json.loads(out.read_text(encoding="utf-8"))
    assert code == 1 and report["decision"] == "묶음 JP 재실행"
    assert [r["reusable"] for r in report["rows"]] == [True, False]


# ------------------------------------------------------------------------------------------- 7.4
def test_oc5_class_boundaries() -> None:
    assert judge.oc5_class(judge.F_MIN_N - 1e-6) == "stop_S9"
    assert judge.oc5_class(judge.F_MIN_N) == "record_with_margin"
    assert judge.oc5_class(judge.F_MIN_N + 1999.0) == "record_with_margin"
    assert judge.oc5_class(judge.F_MIN_N + 2000.0) == "record"


def test_oc5_cli(tmp_path) -> None:
    result = {
        "p3b": {
            "P3-3_leg_force": {
                "F_min_after_N": [20000.0, 15000.0, 9000.0, 30000.0],
                "F_min_transient_N": [1.0] * 4,
                "t_min_after_s": [1.0] * 4,
                "within": False,
            }
        },
        "p3b_ext": {
            "start_condition": {"R_c_operating": 0.951, "crawler_attitude_deg": [2.1, 1.3]}
        },
        "args": {"floor_roll": 2.1434, "floor_pitch": 1.3784},
        "controller_meta": {
            "liftoff_approach_slow": {"start_s": None, "end_s": None, "end_reason": None},
            "slope_clearance_margin": {"order_gate": {"decisions": []}},
        },
    }
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    out = tmp_path / "oc5.json"
    assert judge.main(["oc5", "--result", str(path), "--out", str(out)]) == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["class"] == "stop_S9" and report["min_leg"] == "RL" and report["missing"] == []


# ------------------------------------------------------------------------------------- run_v5 CLI
def test_run_v5_out_and_settings(tmp_path) -> None:
    args = run_v5._parse_args(
        ["main", "--out", str(tmp_path / "h10.jsonl"), "--settings", "VB,LS1"]
    )
    assert args.settings == ("VB", "LS1")
    path, t4h = run_v5.output_paths(args)
    assert path == tmp_path / "h10.jsonl" and t4h == tmp_path / "h10_t4h"
    jobs = run_v5.select_settings(run_v5.batch_jobs("main"), args.settings)
    assert {job["setting"] for job in jobs} == {"VB", "LS1"}
    stored = run_v5.output_paths(run_v5._parse_args(["item8"]))
    assert stored == (run_v5.OUT_DIR / "item8.jsonl", run_v5.OUT_DIR / "item8" / "t4h")
    with pytest.raises(SystemExit):
        run_v5._parse_args(["main", "--settings", "XX"])
    with pytest.raises(SystemExit):
        run_v5._parse_args(["main", "--k1", "on"])


def test_run_v5_one_per_setting() -> None:
    jobs = run_v5.first_job_per_setting(run_v5.u9_targeted_jobs())
    assert [(job["setting"], job.get("eta_v")) for job in jobs] == [("V0", None), ("VB", 0.85)]
    with pytest.raises(SystemExit, match="needs --out"):
        run_v5.main(["u9_targeted", "--one-per-setting", "--list"])


# ------------------------------------------------------------------------------------------ steps
@pytest.fixture(scope="module")
def built(tmp_path_factory):
    steps = importlib.import_module("resume_k1_steps")
    out = tmp_path_factory.mktemp("steps")
    args = steps.argparse.Namespace(
        root=r"C:\workspace\outrigger_control", data_root=str(out), workers=24, mask="0x0FFFFFFF"
    )
    return steps, steps.write(out, steps.build(args)), out


def test_steps_counts_and_names(built) -> None:
    steps, report, out = built
    counts = report["counts"]
    for name in ("H-1", "H-3", "H-4", "H-5"):
        assert counts[name]["differs_S15"] is False, (name, counts[name])
    assert (
        counts["H-9"]["parts"]["main V0..V8 L1 L2"] == 812
        and counts["H-9"]["parts"]["pressure_only"] == 96
    )
    doc = json.loads((out / "steps_h2.json").read_text(encoding="utf-8"))
    for step in doc["steps"]:
        meta = step["resume_k1"]
        assert "scratchpad" not in step["cmd"].lower()
        assert "v5_rerun/las/" not in step["cmd"] and "d1_las.jsonl" not in step["cmd"]  # rules A-9
        assert meta["output"].startswith(
            (
                "06_analysis/03_hydraulic/coupled/v5/resume_k1/",
                "06_analysis/02_control/v5_rerun/las_k1/",
            )
        )
    # rev1 RV1-3: steps exist; a data root without the stored key sources blocks these (S-1)
    assert sorted(report["blocked"]) == ["H-6", "H-7", "H-8", "H-9 grid"]


def test_steps_overlap_table_clean(built, tmp_path) -> None:
    _, _, out = built
    report_path = tmp_path / "overlap.json"
    assert (
        judge.main(["overlap", "--steps", str(out / "steps_h2.json"), "--out", str(report_path)])
        == 0
    )


def test_gs_presence(tmp_path) -> None:
    good = tmp_path / "good.jsonl"
    good.write_text(
        json.dumps(_line(record.controller_record(_Controller()))) + "\n", encoding="utf-8"
    )
    bad = tmp_path / "bad.jsonl"
    bad.write_text(
        json.dumps({"job": {"setting": "VB"}, "controller_tag": judge.TAG_P3}) + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "gs.json"
    assert judge.main(["gs", "--harness", str(good), "--out", str(out)]) == 0
    assert judge.main(["gs", "--harness", str(bad), "--out", str(out)]) == 1


# ------------------------------------------------------------------------------------ u3_judge_k1
def test_u3_judge_k1_differs_only_in_tags_and_paths() -> None:
    old = (COUPLED / "u3_judge.py").read_text(encoding="utf-8").splitlines()
    new = (COUPLED / "u3_judge_k1.py").read_text(encoding="utf-8").splitlines()
    changed = [
        line[1:]
        for line in difflib.unified_diff(old, new, lineterm="", n=0)
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    ]
    code = [
        line
        for line in changed
        if line.strip()
        and not line.lstrip().startswith(('"""', "``"))
        and not line.startswith(" " * 2 + "python")
        and not line.startswith(" " * 6 + "[--")
    ]
    allowed = (
        "DEFAULT_U3_DIR",
        "EXPECTED_TAGS",
        "U6_TAGS",
        "RULES_REVISIONS",
        "v5_rerun.RULES_PATH",
    )
    prose = (
        "436.8",
        "a copy of",
        "tags V0",
        "the run files",
        "sealed ``u3_judge.py``",
        "Judgement of",
    )
    for line in code:
        assert line.strip().startswith(allowed) or any(p in line for p in prose), line
    u3k = importlib.import_module("u3_judge_k1")
    assert u3k.EXPECTED_TAGS == {"V0": "final_C4G2_LAS_K1", "VB": "final_C4G2_P3_LAS_K1"}
    assert u3k.U6_TAGS == {"C2": "final_C4G2_P3_LAS_K1", "ABL": "ABL_LAS_K1", "IND": "IND"}
    assert u3k.DEFAULT_U3_DIR.name == "las_k1"
    assert u3k.RULES_REVISIONS[-1].name == "v5_resume_4368_rules.md"
