"""RV1 (paper review S2 / S3, user approval 2026-10-30): the ``s9_batch.py run RV1`` rows of ``run_S9.rv1_cases``
(X4 = J1 B slope k 0.875 x 3 directions in the S9SL form, X5 = J2 B top x1.1 in the MS1 form). No Chrono run."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s9"))

import run_S9  # noqa: E402

X4_NAMES = ["S9SL_X4nd_J1_B_top_Fs4_r0_p2p8", "S9SL_X4rp_J1_B_top_Fs4_r3p85_p0",
            "S9SL_X4ed_J1_B_top_Fs4_r1p925_p1p4"]
X5_NAME = "P3b_J2_B_top_Fs4_m1p1"
RV1_NAMES = X4_NAMES + [X5_NAME]
C3_NAME = "S9SL_C3_J1_B_top_Fs4_r3p3_p0"
X4_FLOOR_DEG = {X4_NAMES[0]: (0.0, 2.8), X4_NAMES[1]: (3.85, 0.0), X4_NAMES[2]: (1.925, 1.4)}


def _batches():
    import s9_batch

    return s9_batch, s9_batch.batches()


def test_rv1_rows_names_and_planned_pools() -> None:
    _, b = _batches()
    rows = b["RV1"]
    assert [r["case"] for r in rows] == RV1_NAMES
    assert [r["planned_pool"] for r in rows] == ["pcore", "pcore", "ecore", "ecore"]
    for r in rows:
        assert r["est_s"] == r["est_pool_s"][r["planned_pool"]]
        assert r["note"].startswith("RV1 X")
    assert [r["est_s"] for r in rows] == [11000.0, 11000.0, 16500.0, 10600.0]
    for c in run_S9.rv1_cases():
        assert c["group"] == "RV1" and c["expected"] is run_S9.RV1_EXPECTED[c["cid"]]


def test_x4_argv_is_s9sl_c3_with_the_floor_changed() -> None:
    """X4 = the S9SL C-3 row (J1, pad B, top, F_s 4, 160 s, record_only) with only --floor-roll / --floor-pitch
    changed; the floor is k 0.875 x the harness direction."""
    s9_batch, b = _batches()
    c3 = next(r for r in b["S9SL"] if r["case"] == C3_NAME)["argv"]
    ap = run_S9.build_parser()
    for r in b["RV1"][:3]:
        argv = r["argv"]
        assert len(argv) == len(c3) and "--note" not in argv and "--mass-scale" not in argv
        diff = {i for i, (x, y) in enumerate(zip(argv, c3)) if x != y}
        allowed = {argv.index("--floor-roll") + 1, argv.index("--floor-pitch") + 1}
        assert diff <= allowed
        a = ap.parse_args(argv[len(s9_batch.RUN):] + ["--case", r["case"], "--out-root", "x"])
        assert (a.soil, a.pad_variant, a.level, a.fs_kN, a.grid, a.crawler_grid) == (
            "J1", "dwg_rear250", "top", 4.0, 0.01, 0.04)
        assert (a.duration, a.start_limit, a.mass_scale, a.twist_relax) == (160.0, "record_only", 1.0, "preset")
        assert (a.pressure_grade, a.imu_grade, a.seed, a.threads) == ("normal", "ideal", 20261026, 4)
        assert (a.floor_roll, a.floor_pitch) == X4_FLOOR_DEG[r["case"]]
        rc = abs(a.floor_roll) / run_S9.OPERATING_START_SPAN_DEG[0] + abs(a.floor_pitch) / run_S9.OPERATING_START_SPAN_DEG[1]
        assert math.isclose(rc, run_S9.RV1_X4_K, abs_tol=1e-12)
        assert run_S9.p36_ready_limit(vars(a))["limit_s"] == 120.0


def test_x4_matches_the_harness_h3_cases() -> None:
    """Direction table copy = harness SLOPES_DEG; floor, soil, pad, level, F_s, mass = the H3 case (and the H4 twin
    of nose_down)."""
    import s9_soil_slope as ss

    for d, slope in run_S9.RV1_X4_DIRECTION_SLOPES_DEG.items():
        assert ss.SLOPES_DEG[d] == slope and d in ss.BOUNDARY_DIRECTIONS
        assert run_S9.rv1_x4_slope_deg(d) == ss._scaled_slope(d, run_S9.RV1_X4_K)
    assert run_S9.RV1_X4_K in ss.BOUNDARY_K
    h = {c.case_id: c for c in ss.build_cases(("H3", "H4", "H6"))}
    for c in run_S9.rv1_cases():
        hc = h[c["harness_case"]]
        floor = c.get("floor_deg", (0.0, 0.0))
        assert (hc.roll_deg, hc.pitch_deg) == floor
        assert (hc.soil, run_S9.P3B_PAD[hc.pad], hc.level, hc.fs_kN, hc.mass_scale) == (
            c["soil"], c["pad_variant"], c["level"], c["fs_kN"], float(c.get("mass_scale", 1.0)))
        if c["harness_twin"]:
            tw = h[c["harness_twin"]]
            assert tw.reanchor and (tw.roll_deg, tw.pitch_deg) == floor and tw.soil == hc.soil and tw.pad == hc.pad


def test_x5_argv_is_ms1_with_j2() -> None:
    """X5 = the MS1 / D424R ① row with --soil J2 and its own note; P3-6 limit 100 s (421.1)."""
    s9_batch, b = _batches()
    ms1 = b["MS1"][0]["argv"]
    x5 = b["RV1"][3]
    argv = x5["argv"]
    assert len(argv) == len(ms1)
    i_soil, i_note = argv.index("--soil") + 1, argv.index("--note") + 1
    assert {i for i, (x, y) in enumerate(zip(argv, ms1)) if x != y} == {i_soil, i_note}
    assert argv[i_soil] == "J2" and argv[argv.index("--mass-scale") + 1] == "1.1"
    a = run_S9.build_parser().parse_args(argv[len(s9_batch.RUN):] + ["--case", X5_NAME, "--out-root", "x"])
    assert (a.soil, a.pad_variant, a.level, a.fs_kN, a.grid, a.duration, a.mass_scale, a.start_limit) == (
        "J2", "dwg_rear250", "top", 4.0, 0.01, 120.0, 1.1, "preset")
    assert (a.floor_roll, a.floor_pitch) == (0.0, 0.0)
    assert run_S9.p36_ready_limit(vars(a))["limit_s"] == 100.0
    # same grid as the x1.0 P3b-3 pair row
    pair = {r["case"]: r for r in b["P3b"]}["P3b_J2_B_top_Fs4"]["argv"]
    j = argv.index("--note")
    assert argv[:j] + argv[-1:] == pair


@pytest.mark.parametrize("e_tokens", [["S9SL_X4ed_J1_B_top_Fs4_r1p925_p1p4,P3b_J2_B_top_Fs4_m1p1"],
                                      ["S9SL_X4ed_J1_B_top_Fs4_r1p925_p1p4", "P3b_J2_B_top_Fs4_m1p1"]])
def test_rv1_schedule_command(e_tokens) -> None:
    """The documented command: X4-nd / X4-rp on 2 P slots, X4-ed / X5 on 2 E slots."""
    s9_batch, b = _batches()
    argv = ["run", "RV1", "--parallel", "2", "--parallel-e", "2", "--e-cases", *e_tokens]
    kw = s9_batch.schedule_args(s9_batch.build_parser().parse_args(argv), argv)
    assert (kw["parallel"], kw["parallel_e"]) == (2, 2)
    q = s9_batch.schedule_cases(b["RV1"], e_cases=kw["e_cases"], parallel_e=kw["parallel_e"])
    assert [c["case"] for c in q["pcore"]] == X4_NAMES[:2]
    assert [c["case"] for c in q["ecore"]] == [X4_NAMES[2], X5_NAME]
    assert all(c["planned_pool"] == pool for pool in q for c in q[pool])


def test_rv1_not_in_case_plan_and_x5_is_a_rejudge_target(tmp_path) -> None:
    """case_plan stays as it was (MS1 / D424R are not there either); the batch-folder rejudge picks P3b_* only, so the
    X4 folders are re-judged by their case folder path (as the S9SL rows)."""
    assert not set(RV1_NAMES) & {r["case"] for r in run_S9.case_plan()}
    for n in RV1_NAMES:
        (tmp_path / n).mkdir()
        (tmp_path / n / "result.json").write_text("{}", "utf-8")
    assert [p.name for p in run_S9.rejudge_targets([str(tmp_path)])] == [X5_NAME]
    assert [p.name for p in run_S9.rejudge_targets([str(tmp_path / X4_NAMES[0])])] == [X4_NAMES[0]]
