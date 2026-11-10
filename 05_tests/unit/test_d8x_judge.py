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
    assert set(report) == {"original", "rev1", "rev2", "rev3", "rev4", "rev5", "rev6"}
    assert report["rev2"]["sealed"].startswith("5f3fa620")
    assert report["rev3"]["sealed"].startswith("2318fb5c")
    assert report["rev4"]["sealed"].startswith("5233c517")
    assert report["rev5"]["sealed"].startswith("63437019")
    assert report["rev6"]["sealed"].startswith("d584c8da")
    assert all(entry["ok"] for entry in report.values()), report


def test_stage2_rules_constants_match_the_spec() -> None:
    sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))
    import s6_stage2 as st  # noqa: PLC0415

    sealed = {rev: sha for rev, _, sha in spec.RULES_FILES}
    assert st.D8X_RULES_REV == spec.LATEST_RULES_REV == "rev6"
    assert st.D8X_RULES_REV3_SHA256 == sealed["rev3"]
    assert st.D8X_RULES_REV4_SHA256 == sealed["rev4"]
    assert st.D8X_RULES_REV5_SHA256 == sealed["rev5"]
    assert st.D8X_RULES_REV6_SHA256 == sealed["rev6"]


def test_rev3_rev4_have_no_point_tables_and_keep_the_point_file() -> None:
    tables = spec.rules_point_tables()
    assert set(tables["sources"].values()) <= {"original", "rev1"}
    stored = json.loads(spec.POINTS_PATH.read_text(encoding="utf-8"))
    assert set(stored["rules"]) == set(spec.POINT_FILE_RULES)


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
    row = judge._judge_ra_run(_ra_run(gate, tag), k1, {}, F_D8, spec.EXPECTED_TAGS["ra"][k1],
                              set(), [])
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
    eligibility = judge._w_eligibility(spec.build_points(), rows)
    assert all(entry["pass"] for entry in eligibility.values())
    assert eligibility["d45++"]["R_v_true"] == pytest.approx(1.008505, abs=1e-6)
    assert eligibility["d45++"]["for_level_record"]["pass"] is False
    assert eligibility["r+p+0.25"]["for_level_record"] is None


def test_g0_4_gate_scope_is_the_four_l1r_floors() -> None:
    assert spec.G0_4_JUDGED == {"top": ("pitch+", "pitch-", "roll+", "rpX"), "middle": (),
                                "bottom": ()}


G0_CLOSURE = ("04_scripts/01_dynamics/run_s6_slope_boundary_check.py",
              "03_src/outrigger_sim/control/target.py", "02_params/rexome33.yaml")


def _rev3_meta(**overrides) -> dict:
    blobs = judge.tree_blobs("HEAD")
    meta = {"rules_rev": "rev3", "reuse": 0, "recompute": 60, "run_commit": "abc", "clean": True,
            "closure": {"files": {name: blobs[name] for name in G0_CLOSURE}},
            "rules_seals": {path.name: {"sha256": sha} for _, path, sha in spec.RULES_FILES}}
    return {**meta, **overrides}


def _write_g0(path: Path, rows: list[dict], meta: dict) -> None:
    summary = {"reused": meta.get("reuse"), "recomputed": meta.get("recompute")}
    path.write_text(json.dumps({"meta": meta, "summary": summary, "rows": rows}),
                    encoding="utf-8")


def _g0_rows_all(ok=True) -> list[dict]:
    points = spec.build_points()
    return [{**_g0_row(level, tag, spec.points_by_name(points)[tag], ok=ok),
             "source": "recomputed (rev3)"}
            for level in spec.LEVELS for tag in points["g0_points"]]


def test_judge_g0_rev3_recompute_passes(tmp_path) -> None:
    """Rev3 4 / 5: 60 recomputed evaluations, reuse 0, clean run, closure blobs at HEAD."""
    path = tmp_path / "d8x_g0_rev3.json"
    _write_g0(path, _g0_rows_all(), _rev3_meta())
    status, result = judge.cmd_judge_g0(_Args(g0=str(path), at_commit="HEAD"))
    assert status == judge.EXIT_PASS, result["problems"]
    assert result["count"] == 60 and result["closure"]["ok"] is True
    assert {e["source"] for e in result["evaluations"]} == {"recomputed (rev3)"}
    assert len(result["w_eligibility"]) == 11


@pytest.mark.parametrize(("override", "message"), [
    ({"rules_rev": "rev1"}, "rules_rev"),
    ({"reuse": 33}, "reuse"),
    ({"clean": False}, "clean"),
    ({"run_commit": None}, "run_commit"),
    ({"closure": {"files": {G0_CLOSURE[1]: "0" * 40}}}, "closure blobs differ"),
    ({"rules_seals": {"d8x_rules.md": {"sha256": spec.RULES_FILES[0][2]}}}, "rev6 4"),
])
def test_judge_g0_rev3_source_problems_are_not_judgeable(tmp_path, override, message) -> None:
    path = tmp_path / "d8x_g0_rev3.json"
    _write_g0(path, _g0_rows_all(), _rev3_meta(**override))
    status, result = judge.cmd_judge_g0(_Args(g0=str(path), at_commit="HEAD"))
    assert status == judge.EXIT_NOT_JUDGEABLE
    assert any(message in p for p in result["problems"]), result["problems"]


def test_judge_g0_rev3_item_failure_is_a_fail(tmp_path) -> None:
    path = tmp_path / "d8x_g0_rev3.json"
    _write_g0(path, _g0_rows_all(ok=False), _rev3_meta())
    status, result = judge.cmd_judge_g0(_Args(g0=str(path), at_commit="HEAD"))
    assert status == judge.EXIT_FAIL and len(result["failed"]) == 60


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


def _e6_codes(problems: list[str]) -> list[str]:
    return sorted(p.split()[0] for p in problems)


def test_tag_problems_e6_a_to_f() -> None:
    """Rev3 3.1: E-6a exact tag, b LAS-b tag (is_liftoff_slow_tag, accepts _LAS_K1), c K1
    suffix = arm, e LAS-b record, f not a LAS-b off tag."""
    tp = judge._tag_problems
    assert tp("final_C4G2_LAS_K1", "final_C4G2_LAS_K1", True, True) == []
    assert tp("final_C4G2_P3_LAS_K1", "final_C4G2_P3_LAS_K1", True, True) == []
    assert tp("final_C4G2_LAS", "final_C4G2_LAS", True, False) == []  # off arm
    assert _e6_codes(tp("final_C4G2", "final_C4G2", True, False)) == ["E-6b", "E-6f"]
    assert _e6_codes(tp("final_C4G2_K1", "final_C4G2_K1", True, True)) == ["E-6b", "E-6f"]
    assert _e6_codes(tp("final_C4G2_LAS_K1", "final_C4G2_LAS_K1", None, True)) == ["E-6e"]
    assert _e6_codes(tp("final_C4G2_P3_LAS_K1", "final_C4G2_LAS_K1", True, True)) == ["E-6a"]
    # the off arm's tag on an on-arm row: wrong tag and wrong K1 suffix
    assert _e6_codes(tp("final_C4G2_LAS", "final_C4G2_LAS_K1", True, True)) == ["E-6a", "E-6c"]


def test_expected_tags_are_the_rev3_table() -> None:
    from outrigger_sim.hydraulics import v5_options as v5

    assert spec.EXPECTED_TAGS["chrono"] == v5.LAS_K1_CONTROLLER_TAG
    for bundle, preset in (("ra", "ra"), ("VB", "VB"), ("V0", "V0")):
        for k1 in ("off", "on"):
            assert spec.EXPECTED_TAGS[bundle][k1] == spec.arm_tag(spec.DEFAULT_TAGS[preset], k1)
    doc = spec.path2_expect_doc()  # rev3 3.3 --expect content
    assert doc == {"ra": {"off": "final_C4G2_LAS", "on": "final_C4G2_LAS_K1"},
                   "rc": {"VB": {"off": "final_C4G2_P3_LAS", "on": "final_C4G2_P3_LAS_K1"},
                          "V0": {"off": "final_C4G2_LAS", "on": "final_C4G2_LAS_K1"}},
                   "chrono": "final_C4G2_LAS_K1"}
    assert not hasattr(spec, "LAS_TAG_SUFFIX")  # rev3 5: no suffix test left


def test_tag_histogram_outside_the_arm_is_a_problem() -> None:
    assert judge._tag_histogram_problems("f", ["final_C4G2_LAS", None], {"final_C4G2_LAS"}) == []
    assert judge._tag_histogram_problems("f", ["final_C4G2_LAS_K1"], {"final_C4G2_LAS"})


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
GATES_ALL_TRUE = {"k1_order_gate": True, "controller_meta_order_gate": True,
                  "k1_order_gate_matches_meta": True, "settings": True}
"""The four run records of rev5 5 (``settings`` = controller_meta ... flat_soil_margin_order_gate);
``_MISSING`` drops a key."""
_MISSING = object()


def _chrono_case(batch: Path, name: str, *, ready_s: float | None, end_s: float,
                 gates: dict | None = None) -> None:
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
                      "scenario_group": "D8"},
              "controller_meta": {"slope_clearance_margin": {"settings": {}}}}
    for key, value in {**GATES_ALL_TRUE, **(gates or {})}.items():
        if value is _MISSING:
            continue
        if key == "settings":
            result["controller_meta"]["slope_clearance_margin"]["settings"][
                "flat_soil_margin_order_gate"] = value
        else:
            result["d8x"][key] = value
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
                                    "final_C4G2_LAS_K1", prelaunch_k1=True)
    assert judged["verdict"] == verdict, judged
    if verdict == "fail":
        assert "J5" in judged["fail_items"]


def _judge_gate_case(tmp_path, gates: dict, prelaunch_k1=True) -> dict:
    name = "D8X_K24_top_fup3.6_Fs4"
    _chrono_case(tmp_path, name, ready_s=60.0, end_s=80.0, gates=gates)
    row = next(r for r in spec.chrono_rows(None, None) if r["name"] == name)
    metrics = json.loads((tmp_path / "verify_S8C.json").read_text(encoding="utf-8"))["metrics"]
    return judge.judge_chrono_row(row, metrics[0], tmp_path / name, F_D8, (0.0, -3.6),
                                  spec.EXPECTED_TAGS["chrono"], prelaunch_k1=prelaunch_k1)


def test_judge_chrono_e6d_all_five_true_passes(tmp_path) -> None:
    assert _judge_gate_case(tmp_path, {})["verdict"] == "pass"


@pytest.mark.parametrize("key", sorted(GATES_ALL_TRUE))
@pytest.mark.parametrize("value", [False, None])
def test_judge_chrono_e6d_each_record_on_its_own(tmp_path, key, value) -> None:
    """Rev5 5: each of the five gate records is read on its own; one not True = not judgeable
    (the other four true do not stand in for it)."""
    judged = _judge_gate_case(tmp_path, {key: value})
    assert judged["verdict"] == "not_judgeable"
    assert any(r.startswith("E-6d") for r in judged["not_judgeable"])


@pytest.mark.parametrize("key", sorted(GATES_ALL_TRUE))
def test_judge_chrono_e6d_missing_record_is_not_judgeable(tmp_path, key) -> None:
    with pytest.raises(judge.NotJudgeable, match="verify keys missing"):
        _judge_gate_case(tmp_path, {key: _MISSING})


@pytest.mark.parametrize("prelaunch_k1", [None, False])
def test_judge_chrono_e6d_needs_the_prelaunch_row_k1(tmp_path, prelaunch_k1) -> None:
    judged = _judge_gate_case(tmp_path, {}, prelaunch_k1=prelaunch_k1)
    assert judged["verdict"] == "not_judgeable"
    assert any("prelaunch.rows[case].k1_order_gate" in r for r in judged["not_judgeable"])


def test_chrono_prelaunch_records_k1_per_case(tmp_path) -> None:
    states = tmp_path / "states.json"
    states.write_text("{}", encoding="utf-8")
    record = judge._chrono_prelaunch(_Args(expected_tag=spec.EXPECTED_TAGS["chrono"],
                                           start_states=str(states), threads=1, selection=None))
    assert isinstance(record["rows"], dict) and record["rows"]
    assert {row["k1_order_gate"] for row in record["rows"].values()} == {True}
    assert all(name == row["name"] for name, row in record["rows"].items())


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


# --- rev4 F-1: G1 over both K1 arms ----------------------------------------------------------
def _part(label: str, arm: str, verdicts: list[str], expected: int | None = None,
          problems: list[str] | None = None) -> dict:
    rows = [{"id": f"{arm}{i}", "key": f"{arm}{i}", "k1": arm, "verdict": v, "values": {}}
            for i, v in enumerate(verdicts)]
    summary = judge._summarise(rows, len(rows) if expected is None else expected,
                               f"{label}_{arm}")
    return {"summary": summary, "rows": rows, "problems": problems or []}


def test_g1_k1_on_fail_with_k1_off_pass_fails_the_bundle() -> None:
    status, result = judge._bundle_result({"off": _part("ra", "off", ["pass"] * 3),
                                           "on": _part("ra", "on", ["pass", "fail"])}, "ra")
    assert status == judge.EXIT_FAIL
    assert result["k1_rows_failed"] == ["on1"]  # kept for the rev4 1.4 manual check
    assert result["gate_rows_on"]["fail"] == 1


def test_g1_k1_on_count_mismatch_with_a_fail_is_not_judgeable() -> None:
    """A-3 provisional (rev5 pending): not judgeable wins over a K1-on fail."""
    status, result = judge._bundle_result(
        {"off": _part("rc", "off", ["pass"] * 2), "on": _part("rc", "on", ["fail"], expected=96)},
        "rc")
    assert status == judge.EXIT_NOT_JUDGEABLE
    assert result["k1_rows_failed"] == ["on0"]


def test_g1_k1_on_file_missing_is_exit_2(tmp_path, capsys) -> None:
    off = tmp_path / "ra_off.json"
    off.write_text(json.dumps({"meta": {"d8x": {"stages": ["main", "robust", "kt"], "k1": "off"}},
                               "runs": []}), encoding="utf-8")
    status = judge.run(["judge-ra", "--off", str(off), "--on", str(tmp_path / "ra_on.json")])
    assert status == judge.EXIT_NOT_JUDGEABLE
    assert "file not found" in json.loads(capsys.readouterr().out.strip().splitlines()[-1])[
        "error"]


def _judgement(off: list[str], on: list[str] | None) -> dict:
    status, result = judge._bundle_result({"off": _part("ra", "off", off),
                                           "on": _part("ra", "on", on or [])}, "ra")
    if on is None:  # a judgement written without the K1-on arm summary
        result.pop("gate_rows_on")
    return result


def _report(tmp_path, ra: dict, rc: dict) -> tuple[int, dict]:
    files = {}
    for name, doc in (("g0", {"gate_G0": "pass"}), ("ra", ra), ("rc", rc)):
        files[name] = tmp_path / f"{name}.json"
        files[name].write_text(json.dumps(doc), encoding="utf-8")
    return judge.run(["--out", str(tmp_path / "report.json"), "report",
                      "--g0-judgement", str(files["g0"]), "--ra-judgement", str(files["ra"]),
                      "--rc-judgement", str(files["rc"])]), json.loads(
        (tmp_path / "report.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("bundle", ["ra", "rc"])
def test_report_without_k1_rows_failed_is_exit_2(tmp_path, bundle) -> None:
    """Rev5 3.1-3 (B-4): a judgement without ``k1_rows_failed`` is a defective input, not 0."""
    docs = {"ra": _judgement(["pass"], ["pass"]), "rc": _judgement(["pass"], ["pass"])}
    docs[bundle].pop("k1_rows_failed")
    status, report = _report(tmp_path, docs["ra"], docs["rc"])
    assert status == judge.EXIT_NOT_JUDGEABLE
    assert report["k1_rows_failed"][{"ra": "R-a", "rc": "R-c"}[bundle]] is None
    assert report["gates"]["G1"] == "not_judgeable"


def test_report_g1_takes_both_arms_and_a_missing_on_summary_is_not_judgeable(tmp_path) -> None:
    def gate(ra_on):
        files = {}
        for name, doc in (("g0", {"gate_G0": "pass"}), ("ra", _judgement(["pass"], ra_on)),
                          ("rc", _judgement(["pass"], ["pass"]))):
            files[name] = tmp_path / f"{name}.json"
            files[name].write_text(json.dumps(doc), encoding="utf-8")
        args = _Args(g0_judgement=str(files["g0"]), ra_judgement=str(files["ra"]),
                     rc_judgement=str(files["rc"]), chrono_judgement=[], invariance=None,
                     audit_pre_clear=True, recount_agrees=True, audit_post_clear=True,
                     carry_over_confirmed=True)
        return judge.cmd_report(args)[1]

    assert gate(["pass"])["gates"]["G1"] == "pass"
    assert gate(["fail"])["gates"]["G1"] == "fail"
    assert gate(["fail"])["k1_rows_failed"]["R-a"] == ["on0"]
    assert gate(None)["gates"]["G1"] == "not_judgeable"


def test_flags_i_ii_stay_on_the_k1_off_arm() -> None:
    """Rev4 1.3: a K1-on row below F_D8 + 2 kN is a record, not a grade flag."""
    low = {"J1_N": F_D8 + 100.0}
    ra = {"rows": [{"id": "off0", "k1": "off", "values": {"J1_N": 50e3}},
                   {"id": "on0", "k1": "on", "values": low}]}
    assert judge._flags(ra, {"rows": []}, [], {}, None, F_D8) == []
    assert [f["row"] for f in judge._value_flags(judge._k1_on_rows(ra, {}), F_D8)] == ["on0"]


def _ra_las_run(point: str, slow: bool) -> dict:
    events = [[1.0, "INFO_LIFTOFF_SLOW:RR"]] if slow else []
    return {"id": point, "point": point, "level": "top", "d8x": {"events": events}}


def test_v2_las_only_in_the_k1_on_arm_is_las_dependent() -> None:
    """User decision 2026-11-10 (rev4 check A-2 (b)): V-2 counts both K1 arms."""
    v2 = judge._las_activity([_ra_las_run("pitch+", False)], [],
                             [_ra_las_run("pitch+", True)], [])
    assert v2["LAS_DEPENDENT"] == ["ra|pitch+|top"]
    assert v2["counts_by_arm"]["off"]["ra|pitch+|top"] == 0
    assert v2["counts_by_arm"]["on"]["ra|pitch+|top"] == 1


def test_v2_row_without_an_event_list_is_not_judgeable_and_empty_list_is_zero() -> None:
    """Rev6 2: (iii) no event key = not judgeable (never 0); [] = 0; (iv) driver error rows
    are recorded only."""
    no_key = {"id": "x", "point": "roll+", "level": "top", "d8x": {}}
    error_row = {"id": "e", "point": "roll-", "level": "top", "error": "boom"}
    v2 = judge._las_activity([_ra_las_run("pitch+", False), error_row], [], [no_key], [])
    assert v2["judgeable"] is False and v2["missing_events"] == ["on:x"]
    assert v2["record_only_rows"] == ["off:e"]
    assert v2["counts"]["ra|pitch+|top"] == 0 and "ra|pitch+|top" in v2["LAS_INACTIVE"]


# --- rev6 seal audit R-1 / R-2 / R-3 ---------------------------------------------------------
def _rc_error_line(k1: str) -> dict:
    return {"job": {"setting": "VB", "eps": 0.002, "k1": k1,
                    "d1": {"key": "D1|H-R-X|rigid|T|rpX|K3", "slope_name": "rpX",
                           "level": "top", "crawler_k_scale": 3.0}},
            "error": "boom"}


def test_error_rows_carry_the_arm_and_the_join_key() -> None:
    """R-2 / R-1: error and not-judgeable rows keep k1 and the rev6 1 join fields."""
    ra_row = judge._judge_ra_run({"id": "main|x", "point": "pitch+", "level": "top",
                                  "error": "boom"}, "on", {}, F_D8, "t", set(), [])
    assert ra_row["k1"] == "on" and ra_row["id"] == "main|x"
    assert ra_row["verdict"] == "not_judgeable"
    rc_row = judge._judge_rc_line(_rc_error_line("on"), "on", {}, F_D8, set(), [])
    assert rc_row["k1"] == "on" and rc_row["verdict"] == "not_judgeable"
    assert {f: rc_row[f] for f in judge.RC_JOIN_FIELDS} == {
        "slope_name": "rpX", "level": "top", "crawler_k_scale": 3.0, "setting": "VB",
        "eps": 0.002}


def test_not_judgeable_rows_carry_the_arm(monkeypatch) -> None:
    def missing(d8x, fails, f_d8):
        raise judge.NotJudgeable("J1 key missing")

    monkeypatch.setattr(judge, "judge_metrics", missing)
    line = {**_rc_error_line("on"), "d1": {"d8x": {}}}
    line.pop("error")
    row = judge._judge_rc_line(line, "on", {}, F_D8, set(), [])
    assert row["verdict"] == "not_judgeable" and row["k1"] == "on"
    assert row["slope_name"] == "rpX" and row["eps"] == 0.002


def test_bundle_rows_split_by_arm() -> None:
    _, result = judge._bundle_result({"off": _part("rc", "off", ["pass"]),
                                      "on": _part("rc", "on", ["not_judgeable"])}, "rc")
    assert [r["k1"] for r in result["rows_off"]] == ["off"]
    assert [r["k1"] for r in result["rows_on"]] == ["on"]
    assert result["rows"] == result["rows_off"] + result["rows_on"]


def test_seal_record_problems() -> None:
    assert judge._seal_record_problems("x", spec.seal_report()) == []
    assert judge._seal_record_problems("x", None)
    partial = {rev: entry for rev, entry in spec.seal_report().items() if rev != "rev6"}
    assert "rev6" in judge._seal_record_problems("x", partial)[0]


def test_run_identity_records_the_seals() -> None:
    """R-3: d8x_record.run_identity (R-a meta identity, R-c identity sidecar) carries the
    seal report original .. rev6."""
    seals = record.rules_seals()
    assert set(seals) == {rev for rev, _, _ in spec.RULES_FILES}
    assert all(entry["ok"] for entry in seals.values())


def test_rc_identity_sidecar_seals_are_checked(tmp_path) -> None:
    out = tmp_path / "hrx_on.jsonl"
    assert "missing" in judge._rc_identity_seal_problems(out)[0]
    sidecar = tmp_path / "hrx_on.identity.json"
    sidecar.write_text(json.dumps({"start": [{"rules_seals": spec.seal_report()}],
                                   "end": [{"rules_seals": spec.seal_report()}]}),
                       encoding="utf-8")
    assert judge._rc_identity_seal_problems(out) == []
    sidecar.write_text(json.dumps({"start": [{}]}), encoding="utf-8")
    assert judge._rc_identity_seal_problems(out)


def test_ra_file_without_seals_is_a_problem(tmp_path) -> None:
    path = tmp_path / "ra_on.json"
    path.write_text(json.dumps({"meta": {"d8x": {"stages": ["main"], "k1": "on"}}, "runs": []}),
                    encoding="utf-8")
    part = judge.judge_ra_file(path, "on", spec.build_points(), F_D8, spec.DEFAULT_TAGS["ra"])
    assert any("rules_seals" in p for p in part["problems"])
