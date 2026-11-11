"""LAS-b P5r4 + K1 (cad 2026-11-11): ``run_S9 level --las-candidate {P0,P5r4}`` and the batches ``V5-LAS-P5R4-K1`` /
``V5-LAS-P5R4-K1-GS`` (``04_scripts/02_chrono/las_p5r4_k1_chrono_rows.py``; rules ``las_p5r4_k1_rules.md`` sha256
``5ee2bac0`` 2 / 4.3 / 11.2 / 16.2).

No Chrono run: argv / config / controller build checks, the LOC-correction probe on a stand-in controller and the
G-S field check on a synthetic batch folder.
"""

from __future__ import annotations

import json
import pickle
import sys
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHRONO_SCRIPTS = PROJECT_ROOT / "04_scripts" / "02_chrono"
BATCH, GS_BATCH = "V5-LAS-P5R4-K1", "V5-LAS-P5R4-K1-GS"
IDS = ("A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "C1", "C2", "C3", "C4")
PAIRS = (("A1", "A2"), ("A3", "A4"), ("A5", "A6"), ("B1", "B2"), ("C1", "C2"), ("C3", "C4"))
B0 = {"enable": True, "sum_on_fraction_W": 0.6, "light_leg_fraction_of_F_min": 3.5, "slow_mean_fraction": 0.16,
      "sum_off_fraction_W": 0.85, "off_periods": 5, "max_s": 1.5, "rho_on": 0.18, "require_soil_response": True,
      "min_active_periods": 0, "end_ramp_periods": 0}
"""Rules 2 / 436.3: LAS-b b0, written out here (not taken from run_S9)."""
P5R4 = {**B0, "light_leg_fraction_of_F_min": 4.5, "end_ramp_periods": 4}


def _import(name: str, folder: Path):
    sys.path.insert(0, str(folder))
    try:
        return __import__(name)
    finally:
        sys.path.remove(str(folder))


@pytest.fixture(scope="module")
def run_s9():
    pytest.importorskip("pychrono")
    return _import("run_S9", CHRONO_SCRIPTS)


@pytest.fixture(scope="module")
def s9_batch():
    pytest.importorskip("pychrono")
    return _import("s9_batch", CHRONO_SCRIPTS)


@pytest.fixture(scope="module")
def p5k(s9_batch):
    return _import("las_p5r4_k1_chrono_rows", CHRONO_SCRIPTS)


@pytest.fixture(scope="module")
def all_batches(s9_batch):
    return s9_batch.batches()


@pytest.fixture(scope="module")
def rows(all_batches):
    return all_batches[BATCH]


@pytest.fixture(scope="module")
def gs_rows(all_batches):
    return all_batches[GS_BATCH]


def _level_args(run_s9, tokens: list[str]):
    return run_s9.build_parser().parse_args([*tokens, "--case", "x", "--out-root", "x"])


def _preset():
    from outrigger_sim.control.c2 import C2Config

    return C2Config().with_10hz_d1()


def _same_bits(a, b) -> bool:
    return a == b and pickle.dumps(a, protocol=4) == pickle.dumps(b, protocol=4) and repr(a) == repr(b)


def _exit_code(fn) -> int | None:
    with pytest.raises(SystemExit) as e:
        fn()
    return e.value.code


# ------------------------------------------------------------------------------------------- run_S9 level
def test_absent_option_no_attribute_and_preset_unchanged(run_s9) -> None:
    args = _level_args(run_s9, ["level", "--soil", "J2"])
    assert not hasattr(args, "las_candidate")
    assert run_s9.las_candidate_of_args(args) is None
    config, meta = run_s9.level_c2_config_of_args(args)
    out, record = run_s9.apply_las_candidate(config, args)
    assert out is config and record is None and "las_candidate" not in meta


def test_p0_config_bits_equal_no_option(run_s9) -> None:
    """Rules 11.2 #3: ``--las-candidate P0`` and no option give the same config bit for bit (P0 = no override)."""
    plain = _level_args(run_s9, ["level", "--soil", "J2"])
    p0 = _level_args(run_s9, ["level", "--soil", "J2", "--las-candidate", "P0"])
    c_plain, _ = run_s9.level_c2_config_of_args(plain)
    c_p0, _ = run_s9.level_c2_config_of_args(p0)
    out, record = run_s9.apply_las_candidate(c_p0, p0)
    assert out is c_p0 and _same_bits(out, c_plain) and _same_bits(out, _preset())
    assert record["requested"] == "P0" and record["override"] == {} and record["settings"] == B0
    assert {k: v for k, v in vars(p0).items() if k != "las_candidate"} == vars(plain)


def test_p5r4_is_one_replace_of_the_preset(run_s9) -> None:
    args = _level_args(run_s9, ["level", "--soil", "J2", "--las-candidate", "P5r4"])
    config, _ = run_s9.level_c2_config_of_args(args)
    assert _same_bits(config, _preset())  # the override is not in level_c2_config_of_args
    out, record = run_s9.apply_las_candidate(config, args)
    preset = _preset()
    want = replace(preset, liftoff_approach_slow=replace(preset.liftoff_approach_slow,
                                                         light_leg_fraction_of_F_min=4.5, end_ramp_periods=4))
    assert _same_bits(out, want)
    assert asdict(out.liftoff_approach_slow) == P5R4 == record["settings"]
    assert record["override"] == {"light_leg_fraction_of_F_min": 4.5, "end_ramp_periods": 4}
    assert out.slope_clearance_margin.flat_soil_margin_order_gate is True
    assert out.liftoff_approach_slow.enable is True  # the tag suffix _LAS stays (v5_options.with_switch_tags)
    from outrigger_sim.hydraulics.v5_options import with_switch_tags

    assert with_switch_tags("final_C4G2_P3", out) == "final_C4G2_P3_LAS_K1" == with_switch_tags("final_C4G2_P3",
                                                                                                    preset)


def test_b0_table_matches_run_s9(run_s9) -> None:
    assert run_s9.LAS_B0_SETTINGS == B0
    assert set(B0) == set(asdict(_preset().liftoff_approach_slow))  # a new field must be added here (loud)


@pytest.mark.parametrize("tokens", [
    ["--las-off"],
    ["--k1-order-gate", "on", "--k1-forced-block", "first"],
    ["--k2", "on"],
])
def test_misuse_exits_2(run_s9, tokens) -> None:
    for cand in ("P0", "P5r4"):
        args = _level_args(run_s9, ["level", "--soil", "J2", "--las-candidate", cand, *tokens])
        assert _exit_code(lambda a=args: run_s9.las_candidate_of_args(a)) == 2
        assert _exit_code(lambda a=args: run_s9.level_c2_config_of_args(a)) == 2


def test_gate_off_fails_the_preset_check(run_s9) -> None:
    args = _level_args(run_s9, ["level", "--soil", "J2", "--las-candidate", "P5r4", "--k1-order-gate", "off"])
    config, _ = run_s9.level_c2_config_of_args(args)
    assert _exit_code(lambda: run_s9.apply_las_candidate(config, args)) == 2


def test_non_b0_preset_fails_the_preset_check(run_s9) -> None:
    args = _level_args(run_s9, ["level", "--soil", "J2", "--las-candidate", "P0"])
    config, _ = run_s9.level_c2_config_of_args(args)
    bad = replace(config, liftoff_approach_slow=replace(config.liftoff_approach_slow, light_leg_fraction_of_F_min=4.5))
    assert _exit_code(lambda: run_s9.apply_las_candidate(bad, args)) == 2
    bad_nr = replace(config, liftoff_approach_slow=replace(config.liftoff_approach_slow, end_ramp_periods=4))
    assert _exit_code(lambda: run_s9.apply_las_candidate(bad_nr, args)) == 2


def test_bad_value_refused_by_argparse(run_s9) -> None:
    assert _exit_code(lambda: _level_args(run_s9, ["level", "--las-candidate", "P5"])) == 2


def test_settings_diffs_strict(run_s9) -> None:
    las = _preset().liftoff_approach_slow
    assert run_s9.las_settings_diffs(las, B0) == []
    assert [d["field"] for d in run_s9.las_settings_diffs(las, {**B0, "off_periods": 5.0})] == ["off_periods"]
    assert [d["field"] for d in run_s9.las_settings_diffs(las, {**B0, "extra": 1})] == ["extra"]
    short = {k: v for k, v in B0.items() if k != "rho_on"}
    assert [d["field"] for d in run_s9.las_settings_diffs(las, short)] == ["rho_on"]


def test_built_controller_check(run_s9) -> None:
    from outrigger_sim.control.c2 import C2Controller
    from outrigger_sim.params import load_params

    args = _level_args(run_s9, ["level", "--soil", "J2", "--las-candidate", "P5r4"])
    config, record = run_s9.apply_las_candidate(run_s9.level_c2_config_of_args(args)[0], args)
    built = C2Controller.from_params(load_params(level="top"), config)
    run_s9.check_built_las_candidate(built, record)
    assert record["built_check"] == {"ok": True}
    run_s9.check_built_las_candidate(built, None)  # no option: nothing
    other = C2Controller.from_params(load_params(level="top"), _preset())
    assert _exit_code(lambda: run_s9.check_built_las_candidate(other, dict(record))) == 2


def test_run_level_order(run_s9) -> None:
    """Rules 11.2: tag check -> candidate -> controller class -> build -> built check -> c2_setup."""
    src = Path(run_s9.__file__).read_text(encoding="utf-8")
    i_cfg = src.index("config, c2_meta = level_c2_config_of_args(args)")
    i_expect = src.index('c2_meta["expect_controller"] = controller_expectation(config, expect)')
    i_cand = src.index("config, las_candidate_record = apply_las_candidate(config, args)")
    i_cls = src.index('controller_cls, c2_meta["k1_forced_block"] = level_controller_class(args)')
    i_build = src.index("model = build_machine(args, params, pv, soil)", i_cand)
    i_from = src.index("c2 = controller_cls.from_params(params_ctrl, config)")
    i_built = src.index("check_built_las_candidate(c2, las_candidate_record)")
    i_setup = src.index('c2_setup = {**c2_meta, "lifted_reapproach"')
    assert i_cfg < i_expect < i_cand < i_cls < i_build < i_from < i_built < i_setup


def test_code_files_record_structure(run_s9) -> None:
    rec = run_s9.code_files_record()
    assert set(rec["files"]) == set(run_s9.LAS_CANDIDATE_CODE_FILES) and len(run_s9.LAS_CANDIDATE_CODE_FILES) == 9
    for rel, v in rec["files"].items():
        assert set(v) == {"worktree_sha256", "head_blob_sha256"}
        assert v["worktree_sha256"] is not None, rel
    assert rec["head"] and len(rec["head"]) == 40


# ------------------------------------------------------------------------------------------- LOC probe
def _fake_controller(dz=0.02):
    soil = SimpleNamespace(liftoff_s=None, plateau_start_s=None, clearance_at_plateau_start_m=None,
                           clearance_at_liftoff_m=None, corner_bias_raw_m=None, corner_bias_m=np.zeros(4),
                           is_loc_anchor_applied=False, soil_mode_start_s=None)
    cfg = SimpleNamespace(period_s=0.1, soil=SimpleNamespace(corner_bias_deadzone_m=dz, loc_anchor_enable=True,
                                                             loc_anchor_deadzone_m=0.02, loc_anchor_offset_m=0.005))
    return SimpleNamespace(_state=SimpleNamespace(soil=soil, clearance_target_m=None), config=cfg), soil


def test_loc_probe_paths_and_revocation(run_s9) -> None:
    c2, soil = _fake_controller()
    probe = run_s9.LocCorrectionProbe(c2)
    m = lambda t: SimpleNamespace(t_s=t)  # noqa: E731
    probe(m(10.0), None)
    assert probe.locs == []
    # LOC 1: c_min(t_P) 30 mm > 20 mm -> path 1
    soil.liftoff_s, soil.plateau_start_s, soil.clearance_at_plateau_start_m = 20.3, 19.1, 0.03
    soil.clearance_at_liftoff_m, soil.corner_bias_raw_m = 0.031, np.array([0.03, 0.01, -0.01, 0.0])
    soil.corner_bias_m = np.maximum(soil.corner_bias_raw_m, 0.0)
    probe(m(20.3), None)
    probe(m(20.4), None)  # same LOC: no new entry
    # revoked, then LOC 2 with the anchor -> path 2
    soil.liftoff_s = None
    probe(m(25.0), None)
    soil.liftoff_s, soil.plateau_start_s, soil.clearance_at_plateau_start_m = 30.0, 28.9, -0.03
    soil.is_loc_anchor_applied, soil.corner_bias_raw_m = True, np.array([-0.03, -0.02, 0.0, 0.01])
    soil.corner_bias_m = soil.corner_bias_raw_m + 0.005
    probe(m(30.0), None)
    # LOC 3 inside the dead zone -> path 3
    soil.liftoff_s, soil.plateau_start_s, soil.clearance_at_plateau_start_m = 40.0, 39.0, 0.01
    soil.is_loc_anchor_applied, soil.corner_bias_m = False, np.zeros(4)
    probe(m(40.0), None)
    meta = probe.meta([(20.3, "INFO_CRAWLER_LIFTOFF_CONFIRMED"), (30.0, "INFO_LOC_CLEARANCE_ANCHOR:x"), (5.0, "X")])
    assert meta["n_locs"] == 3 and meta["corner_order"] == ["RR", "RL", "FR", "FL"]
    a, b, c = meta["locs"]
    assert (a["path"], b["path"], c["path"]) == (1, 2, 3)
    assert (a["path_name"], b["path_name"], c["path_name"]) == ("positive_bias", "loc_anchor", "zero")
    assert (a["t_L_s"], a["t_P_s"], a["n_L"], a["n_P"]) == (20.3, 19.1, 203, 191)
    assert a["revoked_seen_t_s"] == 25.0 and b["revoked_seen_t_s"] is None
    assert a["bias_raw_m"] == [0.03, 0.01, -0.01, 0.0] and a["bias_applied_m"] == [0.03, 0.01, 0.0, 0.0]
    assert b["loc_anchor_applied"] is True and b["bias_applied_m"] == pytest.approx([-0.025, -0.015, 0.005, 0.015])
    assert a["events_at_loc"] == ["INFO_CRAWLER_LIFTOFF_CONFIRMED"] and c["events_at_loc"] == []
    assert (a["bias_event"], b["bias_event"], c["bias_event"]) == (None, "INFO_LOC_CLEARANCE_ANCHOR:x", None)
    assert a["bias_corner_raw_m"] == a["bias_raw_m"] and b["bias_corner_m"] == b["bias_applied_m"]
    assert a["loc_anchor_bias_mm"] is None and c["loc_anchor_bias_mm"] is None
    # corner order RR, RL, FR, FL -> FL, FR, RL, RR in mm (c2's own conversion)
    assert b["loc_anchor_bias_mm"] == pytest.approx({"FL": 15.0, "FR": 5.0, "RL": -15.0, "RR": -25.0})
    assert meta["first"] == {"index": 0, "path": 1, "t_L_s": 20.3, "t_P_s": 19.1, "n_L": 203, "n_P": 191}
    assert meta["last"]["index"] == 2 and meta["last"]["t_L_s"] == 40.0
    json.dumps(meta)


def test_rows_function_matches_the_batches(rows, gs_rows, p5k) -> None:
    for gs, want in ((False, rows), (True, gs_rows)):
        got = p5k.rows(gs=gs)
        assert [(r["p5k_id"], r["case"], r["argv"]) for r in got] == [(r["p5k_id"], r["case"], r["argv"]) for r in want]


def test_rerun_of_on_every_p5k_entry(s9_batch) -> None:
    src = Path(s9_batch.__file__).read_text(encoding="utf-8")
    assert 'if rerun_of is not None or c.get("p5k_id"):' in src and 'entry["rerun_of"] = rerun_of' in src
    a = s9_batch.main.__code__  # the CLI option exists
    assert a is not None and '"--rerun-of"' in src


def test_loc_probe_never_creates_the_soil_state(run_s9) -> None:
    c2 = SimpleNamespace(_state=SimpleNamespace(soil=None), config=SimpleNamespace(period_s=0.1))
    probe = run_s9.LocCorrectionProbe(c2)
    probe(SimpleNamespace(t_s=1.0), None)
    assert c2._state.soil is None and probe.locs == []


def test_loc_probe_wired_in_run_level(run_s9) -> None:
    src = Path(run_s9.__file__).read_text(encoding="utf-8")
    assert "loc_probe = LocCorrectionProbe(c2)" in src and "        loc_probe(meas, command)\n" in src
    assert 'summary["loc_corrections"] = _record_or_error(lambda: loc_probe.meta(events))' in src


# ------------------------------------------------------------------------------------------- batch rows
def test_twelve_rows_fields(rows, gs_rows) -> None:
    by = {r["p5k_id"]: r for r in rows}
    assert [r["p5k_id"] for r in rows] == list(IDS) == [r["p5k_id"] for r in gs_rows]
    assert len({r["case"] for r in rows}) == 12
    assert [r["case"] for r in rows] == [r["case"] for r in gs_rows]  # same names in the G-S folder
    for r in rows:
        assert r["group"] == BATCH and r["role"] == "judge" and r["p5k_gs"] is False
        assert r["planned_pool"] == "pcore"
        assert r["start_env"] == {"OMP_WAIT_POLICY": "PASSIVE", "OUTRIGGER_HULL_HOOK": "fast"}
        assert r["controller"] == ("final_C4G2_LAS_K1" if r["v5_setting"] == "V0" else "final_C4G2_P3_LAS_K1")
        assert r["est_pool_s"]["ecore"] == pytest.approx(r["est_pool_s"]["pcore"] * 1.5, abs=5)
        assert r["est_s"] == r["est_pool_s"]["pcore"]
    assert [by[i]["las_candidate"] for i in IDS] == ["P0", "P5r4"] * 6
    assert [by[i]["v5_setting"] for i in IDS] == ["VB"] * 4 + ["V0"] * 2 + ["VB"] * 6
    assert [by[i]["p5k_judge_duration_s"] for i in IDS] == [160.0] * 6 + [200.0] * 2 + [120.0] * 2 + [180.0] * 2
    assert [by[i]["p5k_crawler"] for i in IDS] == ["Kc1", "Kc1", "Kc3", "Kc3"] + ["Kc1"] * 8
    assert [by[i]["p5k_mass_scale"] for i in IDS] == [1.0] * 10 + [1.1] * 2
    assert [by[i]["p5k_stage"] for i in IDS] == ["A-Kc1-VB"] * 2 + ["A-Kc3-VB"] * 2 + ["A-Kc1-V0"] * 2 + \
        ["B"] * 2 + ["C-m1p0"] * 2 + ["C-m1p1"] * 2
    assert [r["est_s"] for r in rows] == [5600.0] * 6 + [6800.0] * 2 + [6500.0] * 2 + [9700.0] * 2
    for a, b in PAIRS:
        assert by[a]["pair_case"] == by[b]["case"] and by[b]["pair_case"] == by[a]["case"]
    assert by["B1"]["harness_case"] == "D1|H-S-A|G1+J1@FL|T|flat|K1|VB|e0"
    for r in gs_rows:
        assert r["group"] == GS_BATCH and r["role"] == "gs" and r["p5k_gs"] is True and r["p5k_duration_s"] == 10.0


def _val(argv, opt):
    return argv[argv.index(opt) + 1]


def test_row_argv_defined(rows, s9_batch) -> None:
    common = ["--pad-variant", "dwg_rear250", "--level", "top", "--fs-kN", "4"]
    tail = ["--settle-dashpot", "zrp", "--threads", "4"]
    grades = ["--pressure-grade", "normal", "--imu-grade", "ideal", "--seed", "20261026"]
    by = {r["p5k_id"]: r for r in rows}
    for pid, r in by.items():
        argv = r["argv"]
        assert argv[:len(s9_batch.RUN)] == s9_batch.RUN
        lv = argv[len(s9_batch.RUN):]
        dur = f"{r['p5k_judge_duration_s']:g}"
        ctrl = ["--expect-controller", r["controller"], "--approved"]
        vb = s9_batch.v5_vb_argv() if r["v5_setting"] == "VB" else []
        cand = ["--las-candidate", r["las_candidate"]]
        if pid[0] == "A":
            kc = [] if r["p5k_crawler"] == "Kc1" else ["--crawler-kn-scale", "3"]
            want = (["level", "--soil", "J1", "--rigid-base", "FR", *kc, *common, "--grid", "0.01", *tail,
                     "--duration", dur, *grades, "--floor-roll", "2.3351", "--floor-pitch", "1.5017",
                     "--start-limit", "record_only", *ctrl])
        elif pid[0] == "B":
            want = (["level", "--soil", "G1", *common, "--grid", "0.02", "--crawler-grid", "0.04", *tail,
                     "--duration", dur, *grades, "--soil-patch", "FL:J1", "--soil-patch-grid", "0.01", *ctrl])
        else:
            mass = [] if r["p5k_mass_scale"] == 1.0 else ["--mass-scale", "1.1"]
            want = (["level", "--soil", "J2", *common, "--grid", "0.01", "--crawler-grid", "0.04", *tail,
                     "--duration", dur, *grades, *mass, *ctrl])
        assert lv == want + vb + cand, pid
        for opt in ("--k1-order-gate", "--k1-forced-block", "--las-off", "--k2", "--no-controller-check"):
            assert opt not in argv


def test_pairs_differ_only_in_candidate(rows, gs_rows, p5k) -> None:
    for rs in (rows, gs_rows):
        by = {r["p5k_id"]: r for r in rs}
        for a, b in PAIRS:
            ra, rb = by[a], by[b]
            assert p5k.option_diff(ra["argv"], rb["argv"]) == ["--las-candidate"]
            assert len(ra["argv"]) == len(rb["argv"])
            d = [i for i, (x, y) in enumerate(zip(ra["argv"], rb["argv"], strict=True)) if x != y]
            assert [ra["argv"][i] for i in d] == ["P0"] and [rb["argv"][i] for i in d] == ["P5r4"]
    assert p5k.batch_check(rows)["status"] == "ok" == p5k.batch_check(gs_rows)["status"]


def test_gs_rows_differ_in_duration_only(rows, gs_rows, p5k) -> None:
    for r, g in zip(rows, gs_rows, strict=True):
        assert p5k.option_diff(r["argv"], g["argv"]) == ["--duration"]
        assert _val(g["argv"], "--duration") == "10"


def test_c3_c4_180s(rows) -> None:
    by = {r["p5k_id"]: r for r in rows}
    assert [_val(by[i]["argv"], "--duration") for i in ("C1", "C2", "C3", "C4")] == ["120", "120", "180", "180"]


def test_batch_check_flags_a_second_difference(rows, p5k) -> None:
    bad = [dict(r) for r in rows]
    bad[1] = {**bad[1], "argv": [*bad[1]["argv"], "--k1-order-gate", "on"]}
    chk = p5k.batch_check(bad)
    assert chk["status"] == "differs" and {d["key"] for d in chk["diffs"]} == {"pair_argv_diff"}


def test_check_sources_both_batches_ok(all_batches, s9_batch) -> None:
    for name in (BATCH, GS_BATCH):
        res = s9_batch.check_sources(name, all_batches[name])
        assert res["ok"], [r for r in res["rows"] if r["status"] != "ok"]
        assert len(res["rows"]) == 13 and res["rows"][-1]["case"] == "<batch>"
        cands = [r["las_settings"] for r in res["rows"][:12]]
        assert cands == [B0, P5R4] * 6


def test_argv_check_flags_old_tag_and_forbidden_option(rows, s9_batch, p5k) -> None:
    r = dict(rows[0])
    r["argv"] = s9_batch.with_expected_controller(r["argv"], "final_C4G2_P3_LAS")
    r["controller"] = "final_C4G2_P3_LAS"
    chk = p5k.argv_check(r, s9_batch)
    assert chk["status"] == "differs" and "level_config" in [d["key"] for d in chk["diffs"]]
    r2 = dict(rows[1])
    r2["argv"] = [*r2["argv"], "--k1-order-gate", "on"]
    chk = p5k.argv_check(r2, s9_batch)
    assert {"--k1-order-gate", "k1_order_gate"} <= {d["key"] for d in chk["diffs"]}


def test_entry_meta_keys(s9_batch) -> None:
    for k in ("p5k_id", "p5k_stage", "p5k_gs", "las_candidate", "pair_case", "start_env", "planned_pool",
              "est_pool_s", "role", "v5_setting"):
        assert k in s9_batch.ENTRY_META_KEYS


# ------------------------------------------------------------------------------------------- G-S field check
def _write_folder(tmp: Path, rows, p5k, drop: str | tuple[str, ...] | None = None, rc_case: str | None = None,
                  departed: bool | None = None) -> Path:
    folder = tmp / "batch_V5-LAS-P5R4-K1-GS_x"
    folder.mkdir()
    entries, lines = [], []
    drops = (drop,) if isinstance(drop, str) else tuple(drop or ())
    for r in rows:
        doc: dict = {}
        for path in p5k.RESULT_KEY_PATHS:
            if path in drops:
                continue
            node = doc
            parts = path.split(".")
            for part in parts[:-1]:
                if not isinstance(node.get(part), dict):
                    node[part] = {}
                node = node[part]
            node.setdefault(parts[-1], 123456.789 if "F_min" in path else
                            (departed if path == "p3b.departure.departed" else None))
        d = folder / r["case"]
        d.mkdir()
        (d / "result.json").write_text(json.dumps(doc), "utf-8")
        np.savez(d / "controller_commands.npz", t_s=np.arange(3.0), issued_u_m_s=np.zeros((3, 4)))
        rc = 1 if r["case"] == rc_case else 0
        entries.append({**{k: None for k in p5k.BATCH_ENTRY_KEYS}, "case": r["case"], "rc": rc})
        lines.append(f"END {r['case']} 2026-11-11T10:00:00 rc={rc} wall_s=100")
    (folder / "batch.json").write_text(json.dumps({"batch": GS_BATCH, "cases": entries, "mixed_hull_mode": False,
                                                   "failed": False}), "utf-8")
    (folder / "progress.log").write_text("\n".join(lines) + "\n", "utf-8")
    return folder


def test_field_check_ok_and_no_values(tmp_path, gs_rows, p5k) -> None:
    folder = _write_folder(tmp_path, gs_rows, p5k)
    doc = p5k.field_check(folder)
    assert doc["ok"] and doc["n_ok"] == 12 and doc["batch"] == GS_BATCH
    assert "123456" not in json.dumps(doc)  # presence only, no values


def test_field_check_missing_key_and_rc(tmp_path, gs_rows, p5k) -> None:
    folder = _write_folder(tmp_path, gs_rows, p5k, drop="p3b.P3-3_leg_force.F_min_transient_N",
                           rc_case=gs_rows[3]["case"])
    doc = p5k.field_check(folder)
    assert not doc["ok"] and doc["n_ok"] == 0
    assert all(c["result_missing"] == ["p3b.P3-3_leg_force.F_min_transient_N"] for c in doc["cases"])
    bad = next(c for c in doc["cases"] if c["case"] == gs_rows[3]["case"])
    assert bad["progress_end_rc0"] is False and bad["batch_entry_rc0"] is False


@pytest.mark.parametrize("departed,ok", [(False, True), (True, False), (None, False)])
def test_field_check_departure_conditional_keys(tmp_path, gs_rows, p5k, departed, ok) -> None:
    """run_S9 writes P3-3 F_min_after_N / F_min_transient_N only after a departure (10 s G-S smoke: none)."""
    cond = ("p3b.P3-3_leg_force.F_min_after_N", "p3b.P3-3_leg_force.F_min_transient_N")
    folder = _write_folder(tmp_path, gs_rows, p5k, drop=cond, departed=departed)
    doc = p5k.field_check(folder)
    assert doc["ok"] is ok
    c = doc["cases"][0]
    assert c["conditional_absent"] == (list(cond) if departed is False else [])
    assert c["result_missing"] == ([] if departed is False else list(cond))


def test_field_check_missing_files(tmp_path, gs_rows, p5k) -> None:
    folder = _write_folder(tmp_path, gs_rows, p5k)
    (folder / gs_rows[0]["case"] / "controller_commands.npz").unlink()
    (folder / gs_rows[1]["case"] / "result.json").unlink()
    doc = p5k.field_check(folder)
    assert doc["n_ok"] == 10
    by = {c["case"]: c for c in doc["cases"]}
    assert by[gs_rows[0]["case"]]["controller_commands_npz"] is False
    assert by[gs_rows[1]["case"]]["result_json"] is False


def test_field_check_cli_errors_line(tmp_path, gs_rows, p5k, capsys) -> None:
    folder = _write_folder(tmp_path, gs_rows, p5k)
    assert p5k.main(["gs-check", str(folder)]) == 0
    assert capsys.readouterr().out.rstrip().endswith("errors 0")
    assert p5k.main(["gs-check", str(tmp_path / "nope")]) == 2
