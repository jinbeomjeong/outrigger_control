"""D8x judge path 1 and its run-side record (``04_scripts/03_control/d8x``).

Rules ``06_analysis/02_control/d8x/d8x_rules.md`` with ``d8x_rules_rev1.md``: seals, the rev1
point tables (I-3), expected keys (E-1 / E-5), the J items (4.1), E-8, G0 / W eligibility
(rev1 4.3 / 5.1) and the CLI contract (exit 0 / 1 / 2 / 3, last line JSON).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
D8X_DIR = ROOT / "04_scripts" / "03_control" / "d8x"
sys.path.insert(0, str(D8X_DIR))

import d8x_judge as judge  # noqa: E402
import d8x_record as record  # noqa: E402
import d8x_spec as spec  # noqa: E402

F_D8 = judge.f_d8_N()


# --- seals and points -----------------------------------------------------------------------
def test_all_rules_files_match_their_seals() -> None:
    report = spec.seal_report()
    assert set(report) == {"original", "rev1", "rev2"}
    assert report["rev2"]["sealed"].startswith("5f3fa620")
    assert all(entry["ok"] for entry in report.values()), report


def test_committed_point_file_equals_the_rev1_tables() -> None:
    stored = json.loads(spec.POINTS_PATH.read_text(encoding="utf-8"))
    assert stored == spec.build_points()
    assert stored["rules_rev"] == "rev1"
    assert stored["rules"]["rev1"]["sha256"].startswith("ad16f452")
    assert stored["rules"]["original"]["sha256"].startswith("a377b9bb")
    assert spec.point_table_problems(stored) == []


def test_rev1_points_and_asymmetric_usage() -> None:
    angles = spec.points_by_name(spec.build_points())
    assert angles["pitch-"] == (0.0, -3.6)
    assert angles["fup3.6"] == (0.0, -3.6)
    assert angles["rpX+-"] == (2.8242, -1.8162)
    assert angles["d45+-"] == (2.2064, -2.2064)
    assert "fup3.7" not in angles
    assert spec.verification_usage(0.0, -3.6) == pytest.approx(1.0)
    assert spec.verification_usage(0.0, -3.7) == pytest.approx(3.7 / 3.6)
    assert spec.verification_usage(2.2627, 2.2627) == pytest.approx(1.008505, abs=1e-6)


def test_tables_of_a_later_file_replace_the_earlier_ones() -> None:
    text = "\n".join([
        "**(A) points", "| tag | phi | theta | R_v |", "|---|---|---|---|",
        "| **`pitch-`** | 0 | **−3.6** | 1.000000 |", "", "## 2. next",
        "| `ignored` | 1 | 1 | 1 |", "### 5.1 W", "| `r+p-0.5` | `dxpm050` |",
    ])
    tables = spec.parse_rules_tables(text)
    assert tables["A"] == [("pitch-", 0.0, -3.6, "1.000000")]
    assert tables["W"] == [("r+p-0.5", "dxpm050")]
    assert "B" not in tables


def test_points_check_detects_an_edited_file(tmp_path) -> None:
    path = tmp_path / "points.json"
    assert judge.run(["--points-file", str(path), "points"]) == judge.EXIT_PASS
    assert judge.run(["--points-file", str(path), "points", "--check"]) == judge.EXIT_PASS
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["ra_points"][1]["pitch_deg"] = -3.7
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert judge.run(["--points-file", str(path), "points", "--check"]) == judge.EXIT_FAIL


def test_runners_refuse_a_point_file_of_the_original_rules(tmp_path) -> None:
    doc = spec.build_points()
    doc["rules_rev"] = "original"
    path = tmp_path / "old.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="rules_rev"):
        record.load_points(path)


# --- expected keys ----------------------------------------------------------------------------
def test_expected_counts_of_the_bundles() -> None:
    points = spec.build_points()
    off = spec.expected_ra_ids(points, ("main", "robust", "kt"))
    on = spec.expected_ra_ids(points, ("main",))
    assert (len(off), len(set(off)), len(on)) == (910, 910, 192)
    assert len(spec.expected_rc_keys(points, "off")) == 192
    assert len(spec.expected_rc_keys(points, "on")) == 96
    by_stage = {}
    for run_id in off:
        by_stage[run_id.split("|")[0]] = by_stage.get(run_id.split("|")[0], 0) + 1
    assert by_stage["main"] == 192
    assert by_stage["kt"] + by_stage["ktd0"] == 126
    assert by_stage["seed"] + by_stage["d0"] + by_stage["beta"] == 448 + 144


def test_chrono_rows_use_the_rev1_names() -> None:
    rows = spec.chrono_rows("dxpm050", "rpX")
    names = [row["name"] for row in rows]
    assert len(rows) == 19 and sum(row["order"] == 1 for row in rows) == 18
    assert names[1] == "D8X_K24_top_fup3.6_Fs4"
    assert names[7] == "D8X_C1_D8_top_fup3.6_b1.6"
    assert names[14] == "D8X_K0V_top_fup3.6_Fs0"
    assert names[5] == "D8X_K24_top_dxpm050_Fs4"
    assert names[10] == "D8X_C1_H4V_top_fdown3.7"
    assert names[18] == "D8X_K8_top_rpX_Fs8"


# --- run metrics and the row judgement -----------------------------------------------------
def _metrics(**overrides) -> dict:
    t = np.arange(0.0, 30.0, 0.001)
    cyl = np.full((t.size, 4), 40e3)
    cyl[(t > 12.0) & (t < 12.01), 2] = 15e3
    cyl[(t > 20.0) & (t < 20.01), 1] = 20e3
    att = np.zeros((t.size, 2))
    att[t > 25.0, 0] = 0.05
    kwargs = {"t_s": t, "cyl_force_N": cyl, "rod_weight_N": np.full(4, 600.0), "t_att_s": t,
              "att_deg": att, "t_touch_s": 5.0, "t_crawler_off_s": 11.0, "t_ready_s": 22.0,
              "events": [[10.5, "crawler_liftoff_confirmed"], [19.0, "reanchor_started"],
                         [21.0, "reanchor_completed"]],
              "max_moving_bar": 150.0, "stroke_max_m": 0.66}
    kwargs.update(overrides)
    return record.run_metrics(**kwargs)


def test_run_metrics_windows() -> None:
    metrics = _metrics()
    assert metrics["t_lift_s"] == 10.5  # the LOC event is earlier than the crawler load zero
    assert metrics["J1_min_cyl_after_lift_N"] == 15e3
    assert metrics["J1_leg"] == 2
    assert metrics["reanchor_intervals_s"] == [[19.0, 21.0]]
    assert metrics["J2_min_cyl_reanchor_N"] == 20e3
    assert metrics["J3_pad_lift_samples"] == 0
    assert metrics["J4_att_max_after_ready_deg"] == pytest.approx(0.05)
    assert metrics["J1_window_s"] == pytest.approx(30.0 - 0.001 - 10.5)


def test_pad_lift_counts_after_touch_only() -> None:
    t = np.arange(0.0, 10.0, 0.001)
    cyl = np.full((t.size, 4), 30e3)
    cyl[t < 2.0, 0] = -600.0          # before the TOUCH end: not counted
    cyl[(t > 6.0) & (t < 6.005), 3] = -700.0
    metrics = _metrics(t_s=t, cyl_force_N=cyl, t_att_s=t, att_deg=np.zeros((t.size, 2)),
                       t_ready_s=8.0, events=[])
    assert metrics["J3_pad_lift_samples"] == 4
    assert metrics["J3_pad_normal_min_N"] == pytest.approx(-100.0)


def test_judge_metrics_items() -> None:
    passed = judge.judge_metrics(_metrics(), [], F_D8)
    assert passed["fail_items"] == []
    low = judge.judge_metrics(_metrics(cyl_force_N=np.full((30000, 4), 14e3)), [], F_D8)
    assert {"J1", "J2"} <= set(low["fail_items"])
    events = [[1.0, "WARN_PROBE_STIFFNESS_OUT_OF_RANGE:FL"], [2.0, "FAULT_LIFT_STROKE_LIMIT:soil"],
              [3.0, "WARN_X"], [4.0, "REJ_SLOPE_D8"], [5.0, "FAULT_OTHER"]]
    flagged = judge.judge_metrics(_metrics(events=events), ["Fmin_true"], F_D8)
    assert set(flagged["fail_items"]) >= {"J7", "J8", "J9", "J11", "E-3"}
    assert "J2" not in flagged["items"]  # no H4 interval in this event list


def test_missing_values_fail_and_short_windows_are_not_judgeable() -> None:
    no_ready = judge.judge_metrics(_metrics(t_ready_s=None), [], F_D8)
    assert {"J4", "J5", "E-2"} <= set(no_ready["fail_items"])
    short = judge.judge_metrics(_metrics(t_crawler_off_s=29.5, events=[]), [], F_D8)
    assert short["not_judgeable"]
    with pytest.raises(judge.NotJudgeable, match="d8x keys missing"):
        judge.judge_metrics({"t_touch_s": 1.0}, [], F_D8)


def test_event_names_of_chrono_strings() -> None:
    names = judge._event_names(["C2Event(t_s=26.9, name='floor_estimate_touch')",
                                [1.0, "INFO_LIFTOFF_SLOW:RR"]])
    assert names == ["floor_estimate_touch", "INFO_LIFTOFF_SLOW:RR"]
    assert judge.event_counts(names)["liftoff_slow_count"] == 1


def test_k1_gate_wrapper() -> None:
    from dataclasses import dataclass, field

    @dataclass(frozen=True)
    class Margin:
        flat_soil_margin_order_gate: bool = False

    @dataclass(frozen=True)
    class Config:
        slope_clearance_margin: Margin = field(default_factory=Margin)

    class Controller:
        def __init__(self, geometry, config=None):
            self.config = config

    original_init = Controller.__init__
    record._K1_INSTALLED.clear()
    try:
        record.install_k1_order_gate(True, Controller)
        assert record.effective_k1(Controller(None, Config()))
        record.install_k1_order_gate(True, Controller)  # same value: no-op
        with pytest.raises(RuntimeError, match="installed with True"):
            record.install_k1_order_gate(False, Controller)
    finally:
        record._K1_INSTALLED.clear()
        Controller.__init__ = original_init


def test_k1_gate_off_arm_is_installed_against_a_gate_on_preset() -> None:
    """Since the K1 switch the preset has the gate on: the off arm must turn it off explicitly
    (before, installing nothing left the off arm running with the gate on)."""
    from dataclasses import dataclass, field

    @dataclass(frozen=True)
    class Margin:
        flat_soil_margin_order_gate: bool = True  # the R8 preset since the K1 switch

    @dataclass(frozen=True)
    class Config:
        slope_clearance_margin: Margin = field(default_factory=Margin)

    class Controller:
        def __init__(self, geometry, config=None):
            self.config = config

    record._K1_INSTALLED.clear()
    try:
        record.install_k1_order_gate(record.k1_arm_is_on("off"), Controller)
        assert record.effective_k1(Controller(None, Config())) is False
    finally:
        record._K1_INSTALLED.clear()


def test_k1_arm_needs_off_or_on() -> None:
    assert record.k1_arm_is_on("on") is True and record.k1_arm_is_on("off") is False
    with pytest.raises(ValueError, match="K1 arm"):
        record.k1_arm_is_on(None)


def test_real_preset_off_arm_gives_the_las_tag_and_gate_off() -> None:
    """The real C2 preset: off arm -> gate off, tag ``final_C4G2_LAS`` (= ``spec.arm_tag``);
    on arm -> gate on, tag ``final_C4G2_LAS_K1`` (the preset tag, ``DEFAULT_TAGS['ra']``)."""
    from dataclasses import replace

    from outrigger_sim.control.c2 import C2Config
    from outrigger_sim.hydraulics.v5_options import controller_tag

    preset = C2Config().with_10hz_d1()
    assert controller_tag(None, preset) == spec.DEFAULT_TAGS["ra"] == "final_C4G2_LAS_K1"
    for k1 in ("off", "on"):
        margin = replace(preset.slope_clearance_margin,
                         flat_soil_margin_order_gate=record.k1_arm_is_on(k1))
        config = replace(preset, slope_clearance_margin=margin)
        assert controller_tag(None, config) == spec.arm_tag(spec.DEFAULT_TAGS["ra"], k1)


def test_arm_tags() -> None:
    assert spec.DEFAULT_TAGS == {"ra": "final_C4G2_LAS_K1", "VB": "final_C4G2_P3_LAS_K1",
                                 "V0": "final_C4G2_LAS_K1"}
    assert spec.arm_tag("final_C4G2_LAS_K1", "off") == "final_C4G2_LAS"
    assert spec.arm_tag("final_C4G2_P3_LAS_K1", "on") == "final_C4G2_P3_LAS_K1"
    assert spec.arm_tag("final_C4G2_LAS", "on") == "final_C4G2_LAS_K1"
    with pytest.raises(ValueError):
        spec.arm_tag("final_C4G2_LAS_K1", "preset")


def _ra_run(k1_gate: bool, tag: str) -> dict:
    return {"id": "x", "point": "pitch+", "angles_deg": None, "controller_tag": tag,
            "liftoff_slow_enabled": True, "k1_order_gate": k1_gate, "d8x": {}}


@pytest.mark.parametrize(("k1", "gate", "tag", "is_flagged"), [
    ("off", True, "final_C4G2_LAS_K1", True),   # off arm that ran the preset: E-6
    ("off", False, "final_C4G2_LAS", False),
    ("on", True, "final_C4G2_LAS_K1", False),
    ("on", False, "final_C4G2_LAS", True),
])
def test_ra_e6_checks_the_effective_gate_and_the_arm_tag(monkeypatch, k1, gate, tag,
                                                         is_flagged) -> None:
    def judged_clean(d8x, fails, f_d8):
        return {"items": {}, "fail_items": [], "not_judgeable": [],
                "counts": {"liftoff_slow_count": 0}, "values": {}}

    monkeypatch.setattr(judge, "judge_metrics", judged_clean)
    row = judge._judge_ra_run(_ra_run(gate, tag), k1, {}, F_D8, spec.DEFAULT_TAGS["ra"], set(),
                              [])
    e6 = [reason for reason in row["not_judgeable"] if reason.startswith("E-6")]
    assert bool(e6) is is_flagged, e6


@pytest.mark.parametrize(("setting", "k1", "gate", "tag", "is_flagged"), [
    ("VB", "off", True, "final_C4G2_P3_LAS_K1", True),  # off arm that ran the preset: E-6
    ("VB", "off", False, "final_C4G2_P3_LAS", False),
    ("V0", "on", True, "final_C4G2_LAS_K1", False),
    ("V0", "off", False, "final_C4G2_LAS_K1", True),  # tag of the other arm
])
def test_rc_e6_checks_the_effective_gate_and_the_arm_tag(monkeypatch, setting, k1, gate, tag,
                                                         is_flagged) -> None:
    def judged_clean(d8x, fails, f_d8):
        return {"items": {}, "fail_items": [], "not_judgeable": [],
                "counts": {"liftoff_slow_count": 0}, "values": {}}

    monkeypatch.setattr(judge, "judge_metrics", judged_clean)
    line = {"job": {"setting": setting, "eps": 0.0, "k1": k1,
                    "d1": {"key": "k", "slope_name": "rpX", "roll_deg": 0.0, "pitch_deg": 0.0}},
            "controller_tag": tag,
            "d1": {"d8x": {"k1_order_gate": gate, "liftoff_slow_enabled": True}}}
    row = judge._judge_rc_line(line, k1, {}, F_D8, set(), [])
    e6 = [reason for reason in row["not_judgeable"] if reason.startswith("E-6")]
    assert bool(e6) is is_flagged, e6


# --- G0 and W ------------------------------------------------------------------------------------
def _g0_row(level, tag, floor_hat, err=(0.0, 0.0), ok=True) -> dict:
    return {"level": level, "tag": tag, "floor_deg": list(spec.points_by_name(
        spec.build_points())[tag]),
        "G0": {name: {"pass": ok} for name in ("G0-1", "G0-2", "G0-3")}
        | {"G0-4": {"floor_hat_deg": list(floor_hat), "err_deg": list(err)}}}


def test_g0_4_uses_the_asymmetric_usage() -> None:
    nose_up = judge._g0_4(_g0_row("top", "pitch-", (0.0, -3.61)), spec.G0_4_RV_HAT_MAX)
    assert nose_up["Rv_hat_rev1"] == pytest.approx(3.61 / 3.6)
    assert nose_up["pass"] is True


def test_w_eligibility_is_the_true_usage_and_for_level_is_a_record() -> None:
    """Rev2 3: true R_v <= 1.01, all 11 candidates eligible; for_level R_v hat recorded."""
    d45 = (2.2627 * 1.02, 2.2627 * 1.02)  # a for_level estimate beyond 1.01
    rows = {("top", "d45++"): _g0_row("top", "d45++", d45)}
    eligibility = judge._w_eligibility(spec.build_points(), rows, rows)
    assert all(entry["pass"] for entry in eligibility.values())
    assert eligibility["d45++"]["R_v_true"] == pytest.approx(1.008505, abs=1e-6)
    assert eligibility["d45++"]["for_level_record"]["pass"] is False
    assert eligibility["r+p+0.25"]["for_level_record"] is None


def test_g0_4_gate_scope_is_the_four_l1r_floors() -> None:
    assert spec.G0_4_JUDGED == {"top": ("pitch+", "pitch-", "roll+", "rpX"), "middle": (),
                                "bottom": ()}


def _write_g0(path: Path, rows: list[dict], blobs: dict) -> None:
    path.write_text(json.dumps({"meta": {"identity": {"script_blobs_HEAD": blobs}},
                                "rows": rows}), encoding="utf-8")


def test_judge_g0_counts_and_sources(tmp_path) -> None:
    points = spec.build_points()
    rows = [_g0_row(level, tag, spec.points_by_name(points)[tag])
            for level in spec.LEVELS for tag in points["g0_points"]]
    rerun = tmp_path / "rerun.json"
    _write_g0(rerun, rows, {})
    status, result = judge.cmd_judge_g0(_Args(reuse=str(rerun), rerun=str(rerun)))
    assert result["count"] == 60
    # the reused file here is not the 3da8daa blob and the path blobs are not recorded
    assert status == judge.EXIT_NOT_JUDGEABLE
    assert any("reused G0 blob" in p for p in result["problems"])
    assert result["reuse_condition"]["ok"] is False
    assert {e["source"] for e in result["evaluations"]} == {"rerun"}


class _Args:
    def __init__(self, **values):
        self.points_file = str(spec.POINTS_PATH)
        self.__dict__.update(values)


def test_select_w_takes_the_worst_eligible_candidate(tmp_path) -> None:
    points = spec.build_points()
    runs = []
    for index, candidate in enumerate(points["w_candidates"]):
        value = 30e3 + 1e3 * index
        if candidate["ra_point"] == "d45++":
            value = 16e3  # the worst; eligible by its true R_v 1.0085 (rev2 3)
        runs.append({"level": "top", "mast": "rigid", "point": candidate["ra_point"],
                     "d8x": {"J1_min_cyl_after_lift_N": value}})
    runs.append({"level": "top", "mast": "stiff", "point": "r+p+0.75",
                 "d8x": {"J1_min_cyl_after_lift_N": 1e3}})  # not a rigid-mast row: ignored
    ra = tmp_path / "ra_off.json"
    ra.write_text(json.dumps({"runs": runs}), encoding="utf-8")
    rc = tmp_path / "hrx_off.jsonl"
    rc.write_text("\n".join(json.dumps({"job": {"d1": {"level": "top", "slope_name": mirror}},
                                        "d1": {"d8x": {"J1_min_cyl_after_lift_N": 50e3}}})
                            for mirror in points["w_mirrors"].values()), encoding="utf-8")
    out = tmp_path / "selection.json"
    status, result = judge.cmd_select_w(_Args(g0_judgement=None, ra_off=str(ra),
                                             rc_off=str(rc), selection_out=str(out)))
    assert status == judge.EXIT_PASS
    assert result["skipped_ineligible"] == []
    assert result["W"]["ra_point"] == "d45++"
    assert result["W"]["chrono_floor"] == "d45pp"
    assert result["W"]["angles_deg"] == [2.2627, 2.2627]
    assert json.loads(out.read_text(encoding="utf-8"))["W"]["chrono_floor"] == "d45pp"


def test_tag_problems_need_the_expected_las_tag() -> None:
    assert judge._tag_problems("final_C4G2_LAS_K1", "final_C4G2_LAS_K1", True) == []
    assert judge._tag_problems("final_C4G2_P3_LAS_K1", "final_C4G2_P3_LAS_K1", True) == []
    assert judge._tag_problems("final_C4G2_LAS", "final_C4G2_LAS", True) == []  # off arm
    assert len(judge._tag_problems("final_C4G2", "final_C4G2", True)) == 1
    assert len(judge._tag_problems("final_C4G2_K1", "final_C4G2_K1", True)) == 1  # LAS-b off
    assert len(judge._tag_problems("final_C4G2_LAS_K1", "final_C4G2_LAS_K1", None)) == 1
    assert len(judge._tag_problems("final_C4G2_P3_LAS_K1", "final_C4G2_LAS_K1", True)) == 1


def test_settle_map_by_engine() -> None:
    from outrigger_sim.control.target import CrawlerSettleMap

    l2b = {"engine": "L2b", "level": "top", "number": 1}
    l1r = {"engine": "L1-R", "level": "middle", "number": 7}
    identity = {"kind": "identity", "coefficients": CrawlerSettleMap.identity().to_meta()}
    level = {"kind": "level", "coefficients": CrawlerSettleMap.for_level("middle").to_meta()}
    assert judge._settle_map_problems(l2b, identity) == []
    assert judge._settle_map_problems(l1r, level) == []
    assert judge._settle_map_problems(l1r, identity)
    assert judge._settle_map_problems({**l1r, "level": "top"}, level)
    assert judge._settle_map_problems(l2b, None)


def test_scenario_groups() -> None:
    assert judge._scenario_problems({"number": 1}, "G2-R") == []
    assert judge._scenario_problems({"number": 1}, "D8")
    assert judge._scenario_problems({"number": 5}, "D8") == []
    assert judge._scenario_problems({"number": 5}, None)


# --- judge-chrono ------------------------------------------------------------------------------
def _chrono_case(batch: Path, name: str, *, ready_s: float | None, end_s: float) -> None:
    from outrigger_sim.control.target import CrawlerSettleMap

    case_dir = batch / name
    case_dir.mkdir(parents=True)
    t = np.arange(0.1, end_s, 0.1)
    phase = np.where((ready_s is not None) & (t >= (ready_s or 0.0) - 1e-9), "ready", "level")
    np.savez(case_dir / "r8_series.npz", t=t, phase=phase.astype("<U16"))
    result = {"d8x": {"row": 2, "slope_limit_mode": "verification_ext",
                      "floor_true_deg": [0.0, -3.6], "half_spans_deg": dict(
                          spec.VERIFICATION_EXT_HALF_SPANS_DEG),
                      "level": "top", "beta_GPa": 1.0, "fs_kN": 4.0,
                      "controller_tag": "final_C4G2_LAS_K1", "liftoff_slow_enabled": True,
                      "settle_map": {"kind": "identity",
                                     "coefficients": CrawlerSettleMap.identity().to_meta()},
                      "scenario_group": "D8"}}
    (case_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")
    metrics = {"case": name, "times_s": {"touch": 20.0, "liftoff": 22.0, "ready": ready_s,
                                         "end": end_s},
               "min_cyl_after_liftoff_kN": 30.0, "pad_N_min_after_liftoff_kN": 25.0,
               "att_err_after_ready_maxabs_deg": 0.05, "max_moving_pressure_bar": 150.0,
               "crawler_recontact_after_loc_count": 0,
               "events": ["C2Event(t_s=22.0, name='crawler_liftoff_confirmed')"]}
    (batch / "verify_S8C.json").write_text(json.dumps({"metrics": [metrics]}), encoding="utf-8")


@pytest.mark.parametrize(("ready_s", "end_s", "verdict"),
                         [(60.0, 80.0, "pass"), (None, 100.0, "not_judgeable"),
                          (None, 125.0, "fail")])
def test_judge_chrono_row_and_the_e2_exception(tmp_path, ready_s, end_s, verdict) -> None:
    name = "D8X_K24_top_fup3.6_Fs4"
    _chrono_case(tmp_path, name, ready_s=ready_s, end_s=end_s)
    row = next(r for r in spec.chrono_rows(None, None) if r["name"] == name)
    metrics = json.loads((tmp_path / "verify_S8C.json").read_text(encoding="utf-8"))["metrics"]
    judged = judge.judge_chrono_row(row, metrics[0], tmp_path / name, F_D8, (0.0, -3.6),
                                    "final_C4G2_LAS_K1")
    assert judged["verdict"] == verdict, judged
    if verdict == "fail":
        assert "J5" in judged["fail_items"]


def test_judge_chrono_missing_key_is_not_judgeable(tmp_path) -> None:
    name = "D8X_K24_top_fup3.6_Fs4"
    _chrono_case(tmp_path, name, ready_s=60.0, end_s=80.0)
    row = next(r for r in spec.chrono_rows(None, None) if r["name"] == name)
    with pytest.raises(judge.NotJudgeable, match="J4_deg"):
        judge.judge_chrono_row(row, {"case": name}, tmp_path / name, F_D8, (0.0, -3.6),
                               "final_C4G2_LAS_K1")


# --- CLI contract --------------------------------------------------------------------------------
def test_cli_missing_input_is_exit_2_with_a_json_last_line(tmp_path, capsys) -> None:
    out = tmp_path / "report.json"
    status = judge.run(["--out", str(out), "judge-ra", "--off", str(tmp_path / "none.json"),
                        "--on", str(tmp_path / "none2.json")])
    assert status == judge.EXIT_NOT_JUDGEABLE
    last = capsys.readouterr().out.strip().splitlines()[-1]
    assert json.loads(last)["exit"] == 2
    assert "file not found" in json.loads(out.read_text(encoding="utf-8"))["error"]


def test_cli_internal_error_is_exit_3(monkeypatch, capsys) -> None:
    def broken(args):
        raise ZeroDivisionError("boom")

    monkeypatch.setitem(judge.COMMANDS, "points", broken)
    assert judge.run(["points"]) == judge.EXIT_INTERNAL
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["exit"] == 3


def test_f_d8_is_the_yaml_f_min_plus_5_kn() -> None:
    assert math.isclose(F_D8, 9414.58911 + 5000.0)
