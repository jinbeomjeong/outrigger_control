"""G6 soil patch on the S9 runner (cad, user decision 2026-10-27): the G6 case set and its
``level`` arguments, the P3b set unchanged, ``--soil-patch`` parsing, the P3b extension record
(:func:`run_S9.p3b_ext_records`, :class:`run_S9.CompletionProbe`) and the ``s9_batch`` G6 rows."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

import run_S9  # noqa: E402


def test_p3b_set_unchanged() -> None:
    """No P3b row carries the new key; argv of every P3b row has no soil-patch option."""
    cases = run_S9.p3b_cases()
    assert len(cases) == 24 and all("soil_patch" not in c for c in cases)
    assert all("--soil-patch" not in run_S9.p3b_level_argv(c) for c in cases)


def test_g6_cases() -> None:
    cases = run_S9.g6_cases()
    assert [c["case"] for c in cases] == ["G6_G1_B_top_Fs4_spJ1RR", "G6_G1_B_top_Fs4_spJ1FL",
                                         "G6_G1_B_top_Fs4_spG1RR"]
    want = [("RR", "J1", 0.01, "G6"), ("FL", "J1", 0.01, "G6"), ("RR", "G1", 0.02, "G6-ref")]
    for c, (leg, key, grid, group) in zip(cases, want, strict=True):
        assert c["soil_patch"] == {"leg": leg, "set": key, "grid_m": grid} and c["group"] == group
        assert (c["soil"], c["pad"], c["level"], c["fs_kN"], c["grid_m"], c["crawler_grid_m"]) == \
            ("G1", "B", "top", 4.0, 0.02, 0.04)
        argv = run_S9.p3b_level_argv(c)
        i = argv.index("--soil-patch")
        assert argv[i + 1] == f"{leg}:{key}" and argv[i + 2:i + 4] == ["--soil-patch-grid", f"{grid:g}"]
        assert argv[-1] == "--approved"
        args = run_S9.build_parser().parse_args(argv)
        assert args.soil_patch == f"{leg}:{key}" and args.soil_patch_grid == pytest.approx(grid)
    # user decision 2026-10-28: J1@RR 160 s, J1@FL 200 s, G1 control 120 s (closed loop after the 8 s settle)
    assert [c["duration_s"] for c in cases] == [160.0, 200.0, 120.0]
    assert [run_S9.p3b_level_argv(c)[run_S9.p3b_level_argv(c).index("--duration") + 1] for c in cases] == \
        ["160", "200", "120"]
    assert [c["est_s"] for c in cases] == [11800.0, 14600.0, 7000.0]
    groups = {r["case"]: r for r in run_S9.case_plan()}
    assert all(c["case"] in groups for c in cases)
    assert [groups[c["case"]]["sim_s"] for c in cases] == [168.0, 208.0, 128.0]


def test_g6_open_loop_rows_use_the_p3a_arguments() -> None:
    import s9_batch

    p3a = {r["case"]: r for r in s9_batch.batches()["P3a"]}["P3a_G1_B"]["argv"]
    rows = run_S9.g6_open_loop_cases()
    assert [(r["case"], r["optional"]) for r in rows] == [("G6-0a_G1_B_lift_spG1RR", False),
                                                          ("G6-0b_G1_B_lift_spJ1RR", True)]
    for r, (key, grid) in zip(rows, (("G1", "0.02"), ("J1", "0.01")), strict=True):
        argv = run_S9.g6_machine_argv(r)
        assert argv[:-4] == p3a[p3a.index("machine"):]  # the P3a G1 B arguments unchanged
        assert argv[-4:] == ["--soil-patch", f"RR:{key}", "--soil-patch-grid", grid]
        run_S9.build_parser().parse_args(argv)
    b = s9_batch.batches()
    assert [r["case"] for r in b["G6"]] == ["G6-0a_G1_B_lift_spG1RR", *[c["case"] for c in run_S9.g6_cases()]]
    assert [r["case"] for r in b["G6_opt"]] == ["G6-0b_G1_B_lift_spJ1RR"]


@pytest.mark.parametrize(("key", "variant", "leg", "kN"), [
    ("J1", "dwg_rear250", "RR", 49.0), ("J1", "dwg_rear250", "FL", 85.1), ("J1", "cad330", "RR", 85.1),
    ("J2", "dwg_rear250", "RR", 34.8), ("J2", "dwg_rear250", "FL", 60.2)])
def test_virgin_crossover_force(key, variant, leg, kN) -> None:
    """dynamics 2026-10-28: F_x = K A s_x (J1 B rear 49.0 / front 85.1 kN, J2 34.8 / 60.2 kN)."""
    assert run_S9.virgin_crossover_force_N(key, variant, leg) / 1e3 == pytest.approx(kN, abs=0.05)


def test_virgin_crossover_force_linear_set() -> None:
    assert run_S9.virgin_crossover_force_N("G1", "dwg_rear250", "RR") is None


def test_virgin_branch_record() -> None:
    t = 100.0 + np.arange(0, 30.0, 0.001)
    n = np.zeros((t.size, 4))
    n[:, 3] = np.clip((t - 110.0) * 10e3, 0.0, None)  # RR load rises 10 kN/s from 110 s -> 49 kN at 114.9 s
    series = {"t_s": t, "scm_pad_normal_N": n, "pad_sinkage_geometric_m": np.zeros((t.size, 4))}
    rows = [{"t_s": 113.0, "probed_leg": None}, {"t_s": 116.0, "probed_leg": 3}]
    soil = {"t_P_s": 114.0, "t_loc_s": 115.5}
    phases = [(100.0, "check"), (105.0, "touch"), (112.0, "level")]
    out = run_S9.virgin_branch_record(series, rows, soil, phases, leg="RR", fx_N=49.0e3, t_loop_start_s=100.0)
    assert out["t_first_over_F_x_rel_s"] == pytest.approx(14.9, abs=2e-3)
    assert out["virgin_branch_window"] == {"t_P_s": True, "t_L_s": False, "first_probe_s": False}
    assert out["any_in_window"] and out["uncertainty_if_in_window"] == {"stroke_mm": 2.5, "force_fraction": 0.2}
    assert out["decisions_rel_s"]["first_probe_s"] == pytest.approx(16.0)
    assert len(out["touch_record"]) == 1 and out["touch_record"][0]["t_rel_s"] == [5.0, 12.0]
    never = run_S9.virgin_branch_record(series, rows, soil, phases, leg="RR", fx_N=1e9, t_loop_start_s=100.0)
    assert never["t_first_over_F_x_rel_s"] is None and all(never["virgin_branch_window"].values())
    lin = run_S9.virgin_branch_record(series, rows, soil, phases, leg="RR", fx_N=None, t_loop_start_s=100.0)
    assert not lin["any_in_window"]


@pytest.mark.parametrize("text", ["RR", "XX:J1", "RR:Z9", "RR-J1"])
def test_parse_soil_patch_refuses(text) -> None:
    with pytest.raises(ValueError):
        run_S9.parse_soil_patch(text)


def test_parse_soil_patch() -> None:
    assert run_S9.parse_soil_patch(None) is None and run_S9.parse_soil_patch("") is None
    assert run_S9.parse_soil_patch("FL:J1") == ("FL", "J1")


def _completion(rows):
    probe = run_S9.CompletionProbe(None)
    probe.rows = rows
    return probe.arrays()


def _row(t, phase, d, ok):
    return {"t_s": t, "phase": phase, "D_raw_N": d, "D_loop_N": d, "deviation_rad": 1e-4, "on_target": 1,
            "clearance_filtered_m": 0.05, "ok_attitude": ok[0], "ok_clearance": ok[1], "ok_twist": ok[2],
            "ok_loc": ok[3], "complete_since_s": math.nan}


def test_p3b_ext_records() -> None:
    comp = _completion([_row(1.0, "C2Phase.TOUCH", 0.0, (1, 1, 1, 1)),
                        _row(2.0, "C2Phase.LEVEL", 5000.0, (1, 1, 0, 1)),
                        _row(3.0, "C2Phase.LEVEL", -4000.0, (0, 1, 0, 1)),
                        _row(4.0, "C2Phase.LEVEL", 2000.0, (1, 0, 1, -1))])
    t = np.arange(5) * 1.0
    sink = np.array([[0, 0, 0, 0], [1, 1, 1, 3], [2, 2, 2, 8]] + [[2, 2, 2, 8]] * 2, float) * 1e-3
    series = {"t_s": t, "pad_sinkage_geometric_m": sink}
    events = [(1.0, "INFO_LOC_CLEARANCE_ANCHOR"), (2.0, "INFO_TWIST_UNSETTLED:RR"),
              (2.1, "INFO_TWIST_UNSETTLED_x"), (3.0, "WARN_LIFT_STROKE_LIMITED:FR")]
    soil = {"t_P_s": 110.0, "t_loc_s": 112.5, "clearance_at_P_m": -0.012, "loc": True,
            "loc_anchor_applied": False}
    out = run_S9.p3b_ext_records(series, events, soil, comp, done_twist_N=3000.0, soil_patch_leg="RR",
                                 t_loop_start_s=100.0)
    assert out["event_counts"]["INFO_LOC_CLEARANCE_ANCHOR"] == 1
    assert out["event_counts"]["INFO_TWIST_UNSETTLED"] == 1
    assert out["event_counts"]["WARN_LIFT_STROKE_LIMITED"] == 1 and out["event_counts"]["FAULT_STROKE_END"] == 0
    assert out["soil_times_rel_s"] == {"t_P_s": 10.0, "t_L_s": 12.5} and out["c_min_at_P_m"] == -0.012
    c = out["completion"]
    assert c["level_samples"] == 3
    assert c["blocked_share"] == pytest.approx({"attitude": 1 / 3, "clearance": 1 / 3, "twist": 2 / 3, "loc": 0.0})
    assert c["unknown_share"]["loc"] == pytest.approx(1 / 3)
    assert c["last_level_t_s"] == 4.0 and c["last_level_blocking"] == ["clearance"]
    assert c["D_level_N"] == {"min": -4000.0, "max": 5000.0, "abs_last": 2000.0}
    ps = out["pad_sinkage"]
    assert ps["soft_leg"] == "RR" and ps["soft_minus_others_mean_end_mm"] == pytest.approx(6.0)
    none = run_S9.p3b_ext_records(series, [], None, comp, done_twist_N=3000.0, soil_patch_leg=None,
                                  t_loop_start_s=0.0)
    assert "soft_leg" not in none["pad_sinkage"] and none["soil_times_rel_s"] == {"t_P_s": None, "t_L_s": None}


class _Filt:
    def __init__(self, v):
        self._stages = [np.array([v])]


def test_completion_probe_mirrors_the_conditions() -> None:
    th = SimpleNamespace(done_attitude_rad=0.0005, done_twist_N=3000.0)
    c2 = SimpleNamespace(
        config=SimpleNamespace(thresholds=th, soil=SimpleNamespace(enable=True)),
        geometry=SimpleNamespace(twist_vector=np.array([0.5, -0.5, -0.5, 0.5])),
        _state=SimpleNamespace(last_reading=SimpleNamespace(cylinder_force_N=np.array([10e3, 0, 0, 0])),
                               complete_since_s=None),
        _twist_load_filter=_Filt(4000.0), _clearance_filter=_Filt(0.049), phase="C2Phase.LEVEL",
        _completion_deviation_rad=lambda: 0.0001, _is_reference_on_target=lambda: True,
        _is_clearance_done=lambda c: abs(c - 0.05) < 0.002, _is_liftoff_confirmed=lambda: True)
    probe = run_S9.CompletionProbe(c2)
    probe(SimpleNamespace(t_s=5.0))
    r = probe.rows[-1]
    assert r["D_raw_N"] == pytest.approx(5000.0) and r["D_loop_N"] == pytest.approx(4000.0)
    assert (r["ok_attitude"], r["ok_clearance"], r["ok_twist"], r["ok_loc"]) == (1, 1, 0, 1)
    assert math.isnan(r["complete_since_s"])
    del c2._is_clearance_done  # a member the controller no longer has reads unknown, not an error
    c2._state.last_reading = None
    probe(SimpleNamespace(t_s=5.1))
    r = probe.rows[-1]
    assert r["ok_clearance"] == -1 and r["ok_twist"] == -1 and math.isnan(r["D_raw_N"])


def test_s9_batch_g6_rows() -> None:
    import s9_batch

    rows = s9_batch.batches()["G6"]
    assert [r["case"] for r in rows][1:] == [c["case"] for c in run_S9.g6_cases()]
    assert all("--soil-patch" in r["argv"] for r in rows)
    assert "machine" in rows[0]["argv"] and all("level" in r["argv"] for r in rows[1:])
