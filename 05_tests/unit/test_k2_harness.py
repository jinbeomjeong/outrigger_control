"""K-2 harness side (``k2_touch_creep_rules.md`` 9.1-3 .. 9.1-5, 9.2): KPlant dissipation options, the row
records of ``k2_record.py`` and the path-1 judge ``k2_judge.py`` on synthetic inputs.

No simulation runs here. The KPlant tests import the reduced harness (numba, dynamics-dev); they skip in an
interpreter without it. The hash tests (T-K2-1 / T-K2-2 / I-8) are ``test_k2_hashes.py`` (slow).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
K2_SCRIPTS = ROOT / "04_scripts" / "03_control" / "k2"
for _folder in (K2_SCRIPTS, ROOT / "04_scripts" / "03_control" / "d8x"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

import k2_judge  # noqa: E402
import k2_record  # noqa: E402

LEGS = ("FL", "FR", "RL", "RR")


@pytest.fixture(scope="module")
def rsb():
    pytest.importorskip("numba")
    sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
    import run_s6_slope_boundary_check as module

    return module


# --- KPlant options --------------------------------------------------------------------------------------
def test_presets_expand_to_the_dynamics_spec(rsb) -> None:
    presets = rsb._diss_presets()
    assert set(presets) == set(rsb.DISS_PRESET_NAMES)
    assert presets["none"] == {}
    assert presets["l1eq"] == {"crawler_kt_rel": "chrono_l1"}
    assert presets["aug"] == {"crawler_kt_rel": "chrono_l1", "seal_fs_front_N": 4000.0,
                              "pad_zeta_moving": 0.10}
    assert presets["aug_crc2"]["crawler_c_scale"] == 2.0
    assert presets["aug_eps"]["valve_open_eps_m_s"] == pytest.approx(0.1 * 20.924e-3, rel=1e-3)


def test_chrono_l1_ratio_is_the_yaml_value(rsb) -> None:
    assert rsb.crawler_kt_rel_chrono_l1(rsb.dm.load_params()) == pytest.approx(0.233093, abs=5e-7)
    assert rsb.KT_REL_CHRONO == rsb.KT_REL_PRE_REXOME35_YAML == 0.4021968558889507  # name only


@pytest.mark.parametrize("rcfg", [
    {"diss_preset": "aug", "seal_fs_front_N": 1.0},
    {"diss_preset": "nope"},
])
def test_preset_conflicts_are_refused(rsb, rcfg) -> None:
    with pytest.raises(ValueError):
        rsb.expand_diss_options(rcfg)


def test_explicit_options_keep_their_source(rsb) -> None:
    options, source = rsb.expand_diss_options({"pad_zeta_moving": 0.1, "case_id": "x"})
    assert options == {"pad_zeta_moving": 0.1}
    assert source == {"pad_zeta_moving": "rcfg"}
    assert rsb.expand_diss_options({"case_id": "x"}) == ({}, {})


def test_aug_arm_names_map_to_presets() -> None:
    assert k2_record.AUG_ARMS == {"H0": "none", "L1eq": "l1eq", "L1eq_fs": "l1eq_fs", "L1eq_zm": "l1eq_zm",
                                  "AUG": "aug", "AUG_crc2": "aug_crc2", "AUG_eps": "aug_eps"}
    with pytest.raises(ValueError):
        k2_record.aug_preset("aug")


# --- row records -----------------------------------------------------------------------------------------
def _series(n: int = 2000, dt: float = 1e-3):
    t = (np.arange(n) + 1) * dt
    pad = np.full((n, 4), 20e3)
    return t, pad


def test_sh1_counts_lift_after_the_own_latch_only() -> None:
    t, pad = _series()
    pad[500:510, 0] = -1.0   # FL lifted at 0.501 .. 0.510 s
    pad[100:105, 1] = 0.0    # FR lifted before its latch
    events = [[0.4, "INFO_TOUCH_CREEP_LATCH:FL"], [0.6, "INFO_TOUCH_CREEP_LATCH:FR"],
              [0.7, "INFO_TOUCH_CREEP_LATCH:RL"], [0.7, "INFO_TOUCH_CREEP_LATCH:RR"]]
    assert k2_record.sh1_lift_chunks_after_latch(t, pad, events, 0.8) == [10, 0, 0, 0]
    assert k2_record.sh1_lift_chunks_after_latch(t, pad, events[:1], 0.8) == [10, None, None, None]


def test_sh2_window_is_the_03_s_before_touch() -> None:
    t = (np.arange(2000) + 1) * 1e-3
    rates = np.zeros((2000, 3))
    rates[1500:1700, 0] = np.radians(1.0)  # inside [1.5, 1.8) only
    rates[1800:, 1] = np.radians(5.0)       # after t_touch = 1.8: outside
    amp = k2_record.sh2_rate_amplitude_deg_s(t, rates, 1.8)
    expected = 200 / 300  # 200 ones and 100 zeros: the zeros are 2/3 from the mean
    assert amp == pytest.approx(expected, rel=1e-6)
    assert k2_record.sh2_rate_amplitude_deg_s(t, rates, None) is None


def test_j3_from_the_first_four_pad_contact() -> None:
    t, pad = _series()
    pad[:300, 2] = 0.0       # RL not in contact before 0.301 s
    pad[1000:1003, 3] = -5.0
    count, t_first = k2_record.j3_from_first_all4(t, pad)
    assert (count, t_first) == (3, pytest.approx(0.301))


def test_series_file_name_is_the_diag_slug() -> None:
    assert k2_record.series_file_name("main|C2_tv0.1|top|upper|pitch+") == "main__C2_tv0.1__top__upper__pitchP.npz"


# --- path-1 judge ----------------------------------------------------------------------------------------
def test_tags_of_the_arms() -> None:
    assert k2_judge.expected_tag(False, False) == "final_C4G2_LAS"
    assert k2_judge.expected_tag(False, True) == "final_C4G2_LAS_TCL"
    assert k2_judge.expected_tag(True, True) == "final_C4G2_LAS_K1_TCL"


def test_points_follow_diamond_points_and_flag_the_d45_table() -> None:
    doc = k2_judge.build_points()
    by_tag = {p["tag"]: (p["roll_deg"], p["pitch_deg"]) for p in doc["ra_points"]}
    assert len(by_tag) == 16
    assert by_tag["r+p+0.25"] == (1.375, 2.625)
    assert by_tag["d45++"] == (2.1389, 2.1389)  # diamond_points rounds to 4 decimals
    check = doc["table_check"]  # rules rev1 2: d45 within 2e-5 deg of 19.25 / 9, the rest exact
    assert check["ok"] is True and check["failing"] == {}
    assert check["d45_max_difference_deg"] == pytest.approx(1.1111e-5, abs=1e-8)
    assert check["other_max_difference_deg"] == 0.0


def test_point_rule_rev1_rejects_a_far_d45_and_a_moved_point() -> None:
    differences = {f"d45{s}": 1.1e-5 for s in ("++", "+-", "-+", "--")}
    differences.update({f"p{i}": 0.0 for i in range(12)})
    assert k2_judge.table_check(differences)["ok"] is True
    assert k2_judge.table_check({**differences, "d45++": 3e-5})["ok"] is False
    assert k2_judge.table_check({**differences, "p3": 1e-15})["ok"] is False


def test_point_file_check_compares_the_angles(tmp_path) -> None:
    doc = k2_judge.build_points()
    path = tmp_path / "points.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert k2_judge.point_file_problems(path) == []
    doc["ra_points"][0]["pitch_deg"] += 1e-9
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert k2_judge.point_file_problems(path)


def test_dhat_window_record() -> None:
    t = (np.arange(1000) + 1) * 1e-3              # chunks end at 0.001 .. 1.000 s
    valves = np.zeros((1000, 4))
    strokes = np.zeros((1000, 4))
    valves[750:760, 1] = 1e-3                      # FR open at 0.751 .. 0.760 s
    valves[600:650, 2] = 1e-3                      # RL open before the window only
    strokes[:, 1] = np.where(t > 0.75, 0.002, 0.0)  # FR gains 2 mm inside the window
    open_legs, gained = k2_record.dhat_window_record(t, valves, strokes, 1.0)
    assert open_legs == ["FR"]
    assert gained == [None, pytest.approx(2.0), None, None]
    assert k2_record.dhat_window_record(t, valves, strokes, None) == (None, None)


def test_dhat_quantiles_and_the_large_rows() -> None:
    k2 = {("a", False): 10e3, ("b", False): 2e3, ("c", False): None}
    off = {("a", False): 4e3, ("b", False): 3e3, ("c", False): 1e3, ("d", False): 0.0}
    record = k2_judge.dhat_record(k2, off, "t")
    assert record["pairs"] == 2 and record["n_missing"] == 2
    assert record["quantiles_kN"]["p0"] == pytest.approx(-1.0)
    assert record["quantiles_kN"]["p100"] == pytest.approx(6.0)
    assert record["quantiles_kN"]["p50"] == pytest.approx(2.5)
    assert [row["key"] for row in record["abs_ge_5kN"]] == [["a", False]]


def test_v3_key_rule() -> None:
    rows = [{"id": "a", "level": "middle", "point": "roll-", "d8x": {"J3_pad_lift_samples": 3}},
            {"id": "b", "level": "top", "point": "pitch+", "d8x": {"J3_pad_lift_samples": 0}},
            {"id": "c", "level": "top", "point": "pitch-", "d8x": {"J3_pad_lift_samples": 0}},
            {"id": "d", "level": "middle", "point": "pitch+", "d8x": {"J3_pad_lift_samples": 0}}]
    assert k2_judge.v3_keys(rows) == ["a", "b"]


def _row(k2_on: bool, **changes) -> dict:
    legs = LEGS if k2_on else ()
    events = [[1.0 + i * 0.1, f"INFO_TOUCH_CREEP_LATCH:{leg}"] for i, leg in enumerate(legs)]
    row = {"id": "main|C2_tv0.1|top|rigid|pitch+", "point": "pitch+", "angles_deg": [0.0, 3.7],
           "k1_order_gate": False, "controller_tag": k2_judge.expected_tag(False, k2_on),
           "touch_creep_latch": k2_on, "fails": [], "commands_sha256": "x", "series_file": "s.npz",
           "k2": {"SH1_lift_chunks_after_latch": [0, 0, 0, 0], "SH2_rate_amp_deg_s": 0.2,
                  "event_counts": {"INFO_TOUCH_CREEP_CAP": 0}},
           "d8x": {"t_touch_s": 20.0, "t_lift_s": 25.0, "t_ready_s": 43.0, "J1_min_cyl_after_lift_N": 50e3,
                   "J1_window_s": 20.0, "reanchor_intervals_s": [], "J2_min_cyl_reanchor_N": None,
                   "J3_pad_lift_samples": 0, "J4_att_max_after_ready_deg": 0.05, "J6_max_moving_bar": 150.0,
                   "events": events, "J3_pad_normal_min_N": 9e3}}
    row.update(changes)
    return row


def test_judge_row_pass_and_the_k2_evidence() -> None:
    f_d8 = 14414.589
    angles = {"pitch+": (0.0, 3.7)}
    assert k2_judge.judge_harness_row(_row(True), k2_on=True, angles_by_point=angles, f_d8=f_d8)["verdict"] == "pass"
    assert k2_judge.judge_harness_row(_row(False), k2_on=False, angles_by_point=angles, f_d8=f_d8)["verdict"] == "pass"
    no_latch = _row(True)
    no_latch["d8x"]["events"] = no_latch["d8x"]["events"][:3]
    judged = k2_judge.judge_harness_row(no_latch, k2_on=True, angles_by_point=angles, f_d8=f_d8)
    assert judged["verdict"] == "not_judgeable" and any("E-4" in p for p in judged["not_judgeable"])
    wrong_tag = k2_judge.judge_harness_row(_row(True, controller_tag="final_C4G2_LAS"), k2_on=True,
                                           angles_by_point=angles, f_d8=f_d8)
    assert any("E-6" in p for p in wrong_tag["not_judgeable"])
    lifted = _row(True)
    lifted["d8x"]["J3_pad_lift_samples"] = 5
    assert k2_judge.judge_harness_row(lifted, k2_on=True, angles_by_point=angles, f_d8=f_d8)["fail_items"] == ["J3"]


def test_shadow_flags() -> None:
    f_d8 = 14414.589
    k2_rows = [{"id": "a", "k1_on": False, "sh1": [0, 1, 0, 0], "cap": 1, "sh2": 0.5, "t_ready_s": 50.0,
                "values": {"J1_N": 15e3, "J2_N": None}}]
    off_rows = [{"id": "a", "k1_on": False, "sh2": 0.3, "t_ready_s": 45.0, "values": {"J1_N": 20e3}}]
    flags = {f["flag"] for f in k2_judge.sh_flags(k2_rows, off_rows, f_d8, "t")["flags"]}
    assert flags == {"SH-1", "SH-2", "SH-3", "SH-4", "SH-5", "SH-6"}
    unpaired = k2_judge.sh_flags(k2_rows, [], f_d8, "t")
    assert "E-11" in unpaired["not_judgeable"]


def test_v5_bundles(tmp_path) -> None:
    off = tmp_path / "off.json"
    tcl = tmp_path / "tcl.json"
    off.write_text(json.dumps({"runs": [{"key": "a", "pass": True}, {"key": "b", "pass": False}]}), "utf-8")
    tcl.write_text(json.dumps({"runs": [{"key": "a", "pass": False}, {"key": "b", "pass": True}]}), "utf-8")
    spec = {"kind": "pass_to_fail", "off": [str(off)], "tcl": [str(tcl)], "key": "key", "status": "pass"}
    result = k2_judge.v5_bundle(spec)
    assert result["pass_to_fail"] == ["a"] and result["passed"] is False
    g8_off = tmp_path / "g8_off.jsonl"
    g8_tcl = tmp_path / "g8_tcl.jsonl"
    g8_off.write_text(json.dumps({"key": "k", "final": "READY", "wf": ["FAULT_X:1"]}) + "\n", "utf-8")
    g8_tcl.write_text(json.dumps({"key": "k", "final": "READY", "wf": ["FAULT_X:2"]}) + "\n", "utf-8")
    g8 = {"kind": "g8", "off": [str(g8_off)], "tcl": [str(g8_tcl)], "key": "key", "ready": "final",
          "faults": "wf"}
    assert k2_judge.v5_bundle(g8)["passed"] is True


def test_grade_order() -> None:
    gates = {"G-A": "pass", "G-B": "pass", "G-C": "pass", "G-D": "pass", "G-E": "pass", "G-F": "pass"}
    assert k2_judge._grade(gates, [], []) == "pass"
    assert k2_judge._grade(gates, [{"flag": "SH-2"}], []) == "conditional"
    assert k2_judge._grade({**gates, "G-A": "fail"}, [], []) == "conditional_range"
    assert k2_judge._grade({**gates, "G-C": "fail", "G-A": "fail"}, [], []) == "fail"
    assert k2_judge._grade(gates, [], ["x"]) == "not_judgeable"


def test_cli_contract_last_line_json(capsys) -> None:
    status = k2_judge.run(["points", "--check"])
    last = capsys.readouterr().out.strip().splitlines()[-1]
    assert json.loads(last)["exit"] == status == k2_judge.EXIT_PASS  # rules rev1 2
    assert isinstance(argparse.Namespace, type)
