"""Study ③ (p3b_aug) and study ① (slope level options) on the S9 runner (cad, control design 2026-10-28):
the batch rows, ``level --start-limit``, the REANCHOR / start-condition / settle-slope record blocks (no Chrono run)."""

from __future__ import annotations

import math
import sys
from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

import run_S9  # noqa: E402

AUG_NAMES = ["P3b_J2_B_middle_Fs4", "P3b_J2_B_bottom_Fs4", "P3b_J2_A_middle_Fs4", "P3b_J2_A_bottom_Fs4",
             "P3b_S1_A_middle_Fs4", "P3b_S1_A_bottom_Fs4", "P3b_S1_B_middle_Fs4", "P3b_S1_B_bottom_Fs4"]


def _preset():
    from outrigger_sim.control.c2 import C2Config

    return C2Config().with_10hz_d1()


# --- study ③ --------------------------------------------------------------------------------------------


def test_p3b_aug_cases_and_argv() -> None:
    cases = run_S9.p3b_aug_cases()
    assert [c["case"] for c in cases] == AUG_NAMES
    assert [c["est_s"] for c in cases] == [11500.0] * 4 + [7000.0] * 4
    p3b = {c["case"]: c for c in run_S9.p3b_cases()}
    assert len(p3b) == 24 and not set(p3b) & set(AUG_NAMES)
    ap = run_S9.build_parser()
    for c in cases:
        assert c["pair_case"] in p3b  # the P3b-3 top case of the same soil / pad
        top = run_S9.p3b_level_argv(p3b[c["pair_case"]])
        argv = run_S9.p3b_level_argv(c)
        i = argv.index("--level")
        assert argv[:i + 1] + argv[i + 2:] == top[:i + 1] + top[i + 2:] and argv[i + 1] == c["level"]
        a = ap.parse_args(argv + ["--case", c["case"], "--out-root", "x"])
        assert (a.fs_kN, a.crawler_grid, a.settle_dashpot, a.threads, a.duration) == (4.0, 0.04, "zrp", 4, 120.0)
        assert (a.pressure_grade, a.imu_grade, a.seed, a.approved) == ("normal", "ideal", 20261026, True)
        assert a.grid == {"J2": 0.01, "S1": 0.02}[c["soil"]] and a.start_limit == "preset"
        assert a.floor_roll == 0.0 and a.floor_pitch == 0.0 and a.twist_relax == "preset"
    plan = {r["case"]: r for r in run_S9.case_plan()}
    assert all(plan[c["case"]]["wall_est_s"] == c["est_s"] for c in cases)


def test_s9_batch_new_rows() -> None:
    import s9_batch

    b = s9_batch.batches()
    assert [r["case"] for r in b["p3b_aug"]] == AUG_NAMES
    assert all(r["note"].startswith("pair P3b_") for r in b["p3b_aug"])
    assert [r["case"] for r in b["S9SL"]] == ["S9SL_C1_G1_B_top_Fs4_r0_p3p2", "S9SL_C2_J1_A_top_Fs4_r4p4_p0",
                                              "S9SL_C3_J1_B_top_Fs4_r3p3_p0", "S9SL_C4_J1_A_top_Fs4_r0_p3p2"]
    assert [r["est_s"] for r in b["S9SL"]] == [8600.0, 14600.0, 14600.0, 18100.0]
    want = [("G1", "dwg_rear250", 0.0, 3.2, 0.02, 160.0), ("J1", "cad330", 4.4, 0.0, 0.01, 160.0),
            ("J1", "dwg_rear250", 3.3, 0.0, 0.01, 160.0), ("J1", "cad330", 0.0, 3.2, 0.01, 200.0)]
    for r, w in zip(b["S9SL"], want, strict=True):
        a = run_S9.build_parser().parse_args(r["argv"][len(s9_batch.RUN):])
        assert a.start_limit == "record_only" and a.level == "top" and a.fs_kN == 4.0
        assert (a.soil, a.pad_variant, a.floor_roll, a.floor_pitch, a.grid, a.duration) == w
        assert (a.seed, a.threads, a.pressure_grade, a.imu_grade, a.twist_relax) == (
            20261026, 4, "normal", "ideal", "preset")
    q = s9_batch.schedule_cases(b["p3b_aug"], order="lpt")
    assert [c["case"] for c in q["pcore"]][:4] == AUG_NAMES[:4]


def test_s9sl_all_confirmed() -> None:
    allc = run_S9.s9sl_cases(include_draft=True)
    assert [c["cid"] for c in allc] == ["C-1", "C-2", "C-3", "C-4"] and all(c["confirmed"] for c in allc)
    assert allc == run_S9.s9sl_cases()
    assert [c["sim_s"] for c in allc] == [168.0, 168.0, 168.0, 208.0]


# --- study ① start limit ----------------------------------------------------------------------------------


def test_start_limit_modes() -> None:
    preset = _preset()
    same, meta = run_S9.apply_start_limit(preset, "preset")
    assert same is preset and meta["overrides"] == {} and meta["slope_limit_mode"] == "operating"
    assert meta["relative_span_deg"] == pytest.approx([4.4, 3.2])
    ver, mv = run_S9.apply_start_limit(preset, "verification")
    assert mv["slope_limit_mode"] == "verification" and mv["relative_span_deg"] == pytest.approx([5.5, 3.5])
    assert mv["usage_tolerance"] == 0.01 and mv["acceptance"] == "reject"
    assert mv["crawler_settle_map"] == {"theta0_deg": 0.0, "k_dn": 0.0, "k_up": 0.0, "k_phi": 0.0}
    for f in fields(preset):
        if f.name != "target":
            assert getattr(ver, f.name) == getattr(preset, f.name), f.name
    for f in fields(preset.target):
        if f.name != "slope_limit_mode":
            assert getattr(ver.target, f.name) == getattr(preset.target, f.name), f.name
    vm, mm = run_S9.apply_start_limit(preset, "verification_map", "top")
    assert mm["slope_limit_mode"] == "verification" and mm["crawler_settle_map"]["k_dn"] == pytest.approx(0.04298)
    assert mm["overrides"]["target.crawler_settle_map"] == "CrawlerSettleMap.for_level('top')"
    # the G1 B (0, +3.2) settle smoke: crawler pitch 3.5427 deg -> floor estimate inside 3.5 deg with the map
    fl = vm.target.settle_map.floor_from_crawler((0.0, math.radians(3.5427)))
    assert math.degrees(fl[1]) == pytest.approx((3.5427 - 0.17366) / 1.04298) and math.degrees(fl[1]) < 3.5
    assert run_S9.apply_start_limit(preset, "verification_map", "bottom")[1]["crawler_settle_map"]["k_dn"] == \
        pytest.approx(0.01742)
    with pytest.raises(ValueError):
        run_S9.apply_start_limit(preset, "operating")
    with pytest.raises(SystemExit):
        run_S9.build_parser().parse_args(["level", "--start-limit", "loose"])


def test_run_level_applies_start_limit(monkeypatch) -> None:
    seen = {}

    def stop(config, engine):
        seen["config"] = config
        raise RuntimeError("stop")

    import outrigger_sim.chrono.fallback_ratio as fr

    monkeypatch.setattr(fr, "with_engine_fallback_ratio", stop)
    args = run_S9.build_parser().parse_args(["level", "--start-limit", "verification", "--approved"])
    with pytest.raises(RuntimeError, match="stop"):
        run_S9.run_level(args)
    assert str(seen["config"].target.slope_limit_mode) == "verification"
    args = SimpleNamespace(**{**vars(args), "start_limit": "preset"})
    with pytest.raises(RuntimeError, match="stop"):
        run_S9.run_level(args)
    assert str(seen["config"].target.slope_limit_mode) == "operating"
    assert seen["config"].target == _preset().target  # default path: the preset target settings unchanged


def test_start_condition_record() -> None:
    tm = {"crawler_attitude_rad": [math.radians(2.2), math.radians(1.6)], "slope_limit_mode": "verification",
          "floor_estimate_rad": [0.0, 0.0]}
    r = run_S9.start_condition_record(tm, [(10.0, "REJ_SLOPE_D8"), (11.0, "x")], 8.0)
    assert r["R_c_operating"] == pytest.approx(2.2 / 4.4 + 1.6 / 3.2) and r["operating_rule_rejects"] is False
    assert r["rejections_rel_s"] == [[2.0, "REJ_SLOPE_D8"]]
    tm["crawler_attitude_rad"] = [0.0, math.radians(3.3)]
    assert run_S9.start_condition_record(tm, [], 0.0)["operating_rule_rejects"] is True
    assert run_S9.start_condition_record(None, [], 0.0)["R_c_operating"] is None


# --- REANCHOR record --------------------------------------------------------------------------------------


def test_reanchor_probe() -> None:
    from enum import Enum

    class St(Enum):
        MOVE = "move"

    c2 = SimpleNamespace(phase="C2Phase.REANCHOR", _state=SimpleNamespace(reanchor=SimpleNamespace(stage=St.MOVE,
                                                                                                    step=2)))
    assert run_S9.reanchor_probe(c2) == ("move", 2)
    assert run_S9.reanchor_probe(SimpleNamespace(phase="C2Phase.LEVEL")) == (None, None)
    assert run_S9.reanchor_probe(SimpleNamespace(phase="reanchor")) == (None, None)  # no _state: record only


def _reanchor_fixture():
    t = np.arange(0.0, 20.0, 1e-3)
    f = np.full((t.size, 4), 60e3)
    f[(t >= 12.0) & (t < 13.0), 3] = 20e3  # RR unloaded in step 0 MOVE / HOLD
    sink = np.zeros((t.size, 4))
    sink[:, 0] = 1e-3 * np.clip(t - 10.0, 0.0, 6.0) / 6.0  # FL sinks 1 mm over the REANCHOR window
    rp = np.zeros((t.size, 2))
    rp[:, 1] = 0.05
    series = {"t_s": t, "F_cyl_N": f, "pad_sinkage_geometric_m": sink, "roll_pitch_deg": rp}
    stages = {10.0: ("wait", 0), 12.0: ("move", 0), 12.5: ("hold", 0), 13.5: ("return", 0), 14.0: ("hold2", 0),
              15.0: ("move", 1), 16.0: None}
    rows, cur = [], None
    for k in range(0, 200):
        tk = round(k * 0.1, 10)
        if tk in stages:
            cur = stages[tk]
        st = cur if 10.0 <= tk < 16.0 else None
        rows.append({"t_s": tk, "reanchor_stage": None if st is None else st[0],
                     "reanchor_step": None if st is None else st[1],
                     "pad_tangential_N": [[300.0, 0.0, 50.0]] * 4, "scm_pad_normal_N": [60e3, 60e3, 60e3, 60e3]})
    events = [(10.0, "reanchor_started"), (15.5, "reanchor_aborted:stroke_cap")]
    phases = [(0.0, "C2Phase.LEVEL"), (10.0, "C2Phase.REANCHOR"), (16.0, "C2Phase.LEVEL"), (18.0, "C2Phase.DONE")]
    meta = {"theta_crawler_rad": math.radians(3.2), "anchor_pitch_rad": math.radians(3.2),
            "outcome": "aborted:stroke_cap", "outcomes": ["aborted:stroke_cap"],
            "settings": {"targets": ["RR", "RL"]}}
    return series, rows, events, phases, meta


def test_reanchor_records_steps() -> None:
    series, rows, events, phases, meta = _reanchor_fixture()
    r = run_S9.reanchor_records(series, rows, events, phases, meta, [0.0, 0.0], F_min_N=9415.0,
                                normal_world=np.array([0.0, 0.0, 1.0]),
                                limit_fn=lambda n: 0.5 * np.asarray(n) + 1000.0, t_loop_start_s=8.0)
    assert r["started"] and r["relative_pitch_nose_down_deg"] == pytest.approx(3.2) and r["RA-1_ok"]
    assert r["events_rel_s"][0] == [2.0, "reanchor_started"] and r["RA-6_stroke_cap_aborts"] == 1
    assert [(s["step"], s["stage"]) for s in r["stages"]] == [(0, "wait"), (0, "move"), (0, "hold"), (0, "return"),
                                                             (0, "hold2"), (1, "move")]
    s0 = r["steps"][0]
    assert s0["step"] == 0 and s0["target_leg"] == "RR" and s0["min_F_cyl_N"]["RR"] == 20e3
    assert s0["t_rel_s"] == pytest.approx([4.0, 7.0])
    assert r["steps"][1]["target_leg"] == "RL" and r["steps"][1]["min_F_cyl_all_N"] == 60e3
    assert r["RA-2_min_F_cyl_all_N"] == 20e3 and r["RA-2_ok"] is True  # 20 kN >= 9.415 + 5 kN
    assert r["RA-5_pad_utilisation_max"]["FL"] == pytest.approx(300.0 / 31e3)  # normal part (50 N) removed
    assert r["RA-4_non_target_sinkage_increase_mm"]["FL"] == pytest.approx(1.0, abs=2e-3)
    assert set(r["RA-4_non_target_sinkage_increase_mm"]) == {"FL", "FR"}
    assert r["relevels_after"] == 1 and r["RA-3_ok"] is True and r["end_roll_pitch_deg"][1] == pytest.approx(0.05)


def test_reanchor_records_skipped_and_errors() -> None:
    series, rows, _ev, phases, meta = _reanchor_fixture()
    r = run_S9.reanchor_records(series, rows, [(9.0, "reanchor_skipped:stroke_margin")], phases,
                                {**meta, "outcome": "skipped:stroke_margin"}, [0.0, 0.0], F_min_N=9415.0,
                                normal_world=np.array([0.0, 0.0, 1.0]), limit_fn=None, t_loop_start_s=8.0)
    assert not r["started"] and r["skip_reasons"] == ["stroke_margin"] and r["RA-1_ok"] and "stages" not in r
    assert run_S9._record_or_error(lambda: 1 / 0)["error"].startswith("ZeroDivisionError")


# --- all-crawler-point gap ------------------------------------------------------------------------------------


def test_crawler_gap_points_and_probe() -> None:
    from outrigger_sim.chrono import scm_model as sm
    from outrigger_sim.params import load_params

    params = load_params(level="top", model="L2b_NSC")
    pts, labels = run_S9.crawler_gap_points_body_m(params)
    n_box = sum(1 for lab in labels if ":v" in lab)
    assert n_box == 48 and len(pts) == len(labels) and len(pts) > n_box
    z_block = float(params.ground.crawler_bottom_z_m) + sm.BLOCK_BOTTOM_ABOVE_CRAWLER_BOTTOM_M
    assert pts[:, 2].min() == pytest.approx(z_block)  # flat-box bottom corners / grid at the block bottom

    class Sup:  # pure translation: body COG frame -> world = local + offset
        def __init__(self, off):
            self.off = np.asarray(off, float)

        def TransformPointLocalToParent(self, p):  # noqa: N802 - Chrono name
            return sm.chvec(np.array([p.x, p.y, p.z]) + self.off)

    class Ter:  # 5 mm rut under the most forward point only
        def __init__(self, x_hot):
            self.x_hot = x_hot

        def GetNodeInfo(self, w):  # noqa: N802
            return SimpleNamespace(sinkage=0.005 if w.x > self.x_hot - 1e-9 else 0.0)

    com = np.array([0.1, 0.0, 0.3])
    lift = 0.02  # body 20 mm above the settle pose
    model = SimpleNamespace(params=params, sup_com_body_m=com, normal_world=np.array([0.0, 0.0, 1.0]),
                            plane_point_world_m=np.array([0.0, 0.0, z_block]),
                            superstructure=Sup(com + [0.0, 0.0, lift]), crawler_terrain=Ter(pts[:, 0].max()))
    probe = run_S9.CrawlerGapProbe(model)
    gap, where, gap_grid, near = probe()
    assert gap == pytest.approx(lift) and gap_grid == pytest.approx(lift)  # lowest points at z_block
    assert math.isfinite(near)
    model.crawler_terrain = Ter(-1e9)  # every node rutted 5 mm
    r = probe()
    assert r[0] == pytest.approx(lift + 0.005) and r[3] == pytest.approx(0.005) and where


def test_record_only_start_limit_is_the_harness_target_path() -> None:
    """S9SL (control-expert 2026-10-28): record_only changes target.acceptance to off and nothing else; the harness
    preset has the same acceptance / mode / settle map; CHECK then accepts the level target on the C-1 crawler
    attitude (3.5427 deg, rejected by the verification mode)."""
    from outrigger_sim.control.target import AttitudeTarget, TargetAcceptance, TargetCode, check_target

    preset = _preset()
    ro, meta = run_S9.apply_start_limit(preset, "record_only")
    assert meta["overrides"] == {"target.acceptance": "off"} and meta["acceptance"] == "off"
    assert meta["slope_limit_mode"] == "operating" and meta["crawler_settle_map"]["k_dn"] == 0.0
    for f in fields(preset):
        if f.name != "target":
            assert getattr(ro, f.name) == getattr(preset, f.name), f.name
    for f in fields(preset.target):
        if f.name != "acceptance":
            assert getattr(ro.target, f.name) == getattr(preset.target, f.name), f.name
    sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "r8d1"))
    try:
        import c2py_r8d1_closed_loop as h
    finally:
        sys.path.pop(0)
    from outrigger_sim.control.c2 import ContactJudge

    hc = h.preset_config(ContactJudge.COMBINED, True)
    assert hc.target.acceptance is TargetAcceptance.OFF
    assert (ro.target.acceptance, ro.target.slope_limit_mode, ro.target.settle_map) == (
        hc.target.acceptance, hc.target.slope_limit_mode, hc.target.settle_map)
    for name in ("soil", "lift_stroke_guard", "twist_completion_relax", "pre_loc_lift_pause"):  # LEVEL-path blocks
        assert getattr(ro, name) == getattr(hc, name), name
    crawler = (0.0, math.radians(3.5427))
    assert check_target(AttitudeTarget(), crawler, ro.target.limits, ro.target.acceptance).code is TargetCode.ACCEPTED
    ver, _ = run_S9.apply_start_limit(preset, "verification")
    assert check_target(AttitudeTarget(), crawler, ver.target.limits, ver.target.acceptance).code is \
        TargetCode.REJ_SLOPE_D8
    assert run_S9.S9SL_START_LIMIT == "record_only"


def test_crawler_gap_after_first_ready_and_corner_flag() -> None:
    rows = []
    for k in range(10):
        rows.append({"t_s": 8.0 + 0.1 * k, "crawler_gap_point": "crawler_L_front:v0" if k == 7 else "grid_L",
                     "crawler_gap_grid_min_m": 0.030 - 0.001 * k, "crawler_gap_min_m": 0.030 - 0.001 * k
                     - (0.012 if k == 7 else 0.0), "crawler_gap_point_near_sinkage_m": 0.004})
    phases = [(8.0, "level"), (8.5, "ready"), (8.8, "level"), (8.85, "ready")]
    assert run_S9.first_ready_time(phases) == 8.5
    s = run_S9.crawler_gap_summary(rows, 8.2, 8.0, run_S9.first_ready_time(phases))["after_first_ready"]
    assert s["grid_min_m"] == pytest.approx(0.021) and s["all_min_m"] == pytest.approx(0.011)
    assert s["all_min_point"] == "crawler_L_front:v0" and s["corner_flag_margin_m"] == pytest.approx(0.009)
    assert s["corner_flag"] is True  # 0.011 < 0.021 - 0.009
    rows[7]["crawler_gap_point_near_sinkage_m"] = 0.008
    assert run_S9.crawler_gap_summary(rows, 8.2, 8.0, 8.5)["after_first_ready"]["corner_flag"] is False
    assert run_S9.crawler_gap_summary(rows, 8.2, 8.0, None)["after_first_ready"] is None


def test_crawler_gap_summary() -> None:
    rows = [{"t_s": 8.0 + 0.1 * k, "crawler_gap_min_m": g, "crawler_gap_point": f"p{k}",
             "crawler_gap_grid_min_m": g + 0.004} for k, g in enumerate([0.0, 0.0, 0.01, 0.03, 0.025, 0.04])]
    s = run_S9.crawler_gap_summary(rows, 8.2, 8.0)
    assert s["start_m"] == 0.0 and s["end_m"] == 0.04 and s["at_loc_m"] == 0.01
    assert s["grid_at_loc_m"] == pytest.approx(0.014) and s["grid_min_after_loc_m"] == pytest.approx(0.014)
    assert s["min_after_loc_m"] == 0.01 and s["min_after_loc_t_rel_s"] == pytest.approx(0.2)
    assert run_S9.crawler_gap_summary([], None, 0.0)["n_rows"] == 0


# --- settle on a slope -------------------------------------------------------------------------------------


def test_settle_slope_record() -> None:
    from outrigger_sim.scenarios.slope import floor_normal

    n = floor_normal(0.0, 3.2)
    w = 4.0e5
    t = np.arange(7.0, 8.0, 1e-3)
    s = {"t_s": t, "roll_pitch_deg": np.column_stack([np.zeros_like(t), 3.4 + 0.005 * np.sin(6 * t)]),
         "scm_crawler_normal_N": np.full(t.size, w * math.cos(math.radians(3.2)) * 0.9),
         "scm_pad_normal_N": np.full((t.size, 4), w * math.cos(math.radians(3.2)) * 0.025)}
    r = run_S9.settle_slope_record(s, w, n, n, (0.0, 0.0, -9.80665), {"n_points": 10})
    assert r["plane_tilt_deg"] == pytest.approx(3.2) and r["plane_vs_requested_angle_deg"] == pytest.approx(0.0)
    assert r["gravity_vs_minus_z_angle_deg"] == pytest.approx(0.0)
    assert r["normal_over_weight_cos_tilt"] == pytest.approx(1.0) and r["P2-d_ok"]
    assert r["pitch_pp_deg"] == pytest.approx(0.01, abs=1e-3) and r["P2-c_ok"]
    flat = run_S9.settle_slope_record({}, w, np.array([0.0, 0.0, 1.0]), None, (0.0, 0.0, -9.8), None)
    assert flat["plane_tilt_deg"] == 0.0 and flat["plane_vs_requested_angle_deg"] == pytest.approx(0.0)
