"""RV3 (spec 426 gap studies, user decision 2026-10-30): the ``s9_batch.py run RV3`` rows of ``run_S9.rv3_cases``
(B = S1 B roll_pos k0.75 F_s 0 in the S9SL form, C = G1 + S1@FL pad A in the G6P form). No Chrono run."""

from __future__ import annotations

import contextlib
import dataclasses
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT / "04_scripts" / "02_chrono", ROOT / "04_scripts" / "03_control" / "s9",
           ROOT / "04_scripts" / "03_control" / "s8"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import run_S9  # noqa: E402

B_NAME = "S9SL_RV3B_S1_B_top_Fs0_r3p3_p0"
C_NAME = "G6_G1_A_top_Fs4_spS1FL"
RV3_NAMES = [B_NAME, C_NAME]
G6P_S1FL = "G6_G1_B_top_Fs4_spS1FL"
C3_NAME = "S9SL_C3_J1_B_top_Fs4_r3p3_p0"


def _batches():
    import s9_batch

    return s9_batch, s9_batch.batches()


def test_rv3_rows_names_pools_and_estimates() -> None:
    _, b = _batches()
    rows = b["RV3"]
    assert [r["case"] for r in rows] == RV3_NAMES
    assert [r["planned_pool"] for r in rows] == ["ecore", "pcore"]
    assert [r["est_s"] for r in rows] == [9800.0, 8500.0]
    for r in rows:
        assert r["est_s"] == r["est_pool_s"][r["planned_pool"]]
        assert r["note"].startswith("RV3 ") and "harness" in r["note"]
    for c in run_S9.rv3_cases():
        assert c["group"] == "RV3" and c["expected"] is run_S9.RV3_EXPECTED[c["cid"]]
        assert c["harness_case"] == run_S9.RV3_HARNESS[c["cid"]]["id"]
        assert c["sim_s"] == run_S9.CRAWLER_SETTLE_S + 160.0


def test_b_argv_is_s9sl_c3_with_soil_floor_and_fs_changed() -> None:
    """B = the S9SL C-3 argv (pad B, top, 160 s, record_only, R8 preset) with --soil S1, --grid 0.02 (S1 pad grid),
    --fs-kN 0; the floor (3.3, 0) deg is the C-3 floor too (k 0.75 x roll_pos)."""
    s9_batch, b = _batches()
    c3 = next(r for r in b["S9SL"] if r["case"] == C3_NAME)["argv"]
    argv = b["RV3"][0]["argv"]
    assert len(argv) == len(c3) and "--note" not in argv and "--soil-patch" not in argv
    diff = {i for i, (x, y) in enumerate(zip(argv, c3)) if x != y}
    assert diff == {argv.index("--soil") + 1, argv.index("--grid") + 1, argv.index("--fs-kN") + 1}
    a = run_S9.build_parser().parse_args(argv[len(s9_batch.RUN):] + ["--case", B_NAME, "--out-root", "x"])
    assert (a.soil, a.pad_variant, a.level, a.fs_kN, a.grid, a.crawler_grid) == (
        "S1", "dwg_rear250", "top", 0.0, 0.02, 0.04)
    assert (a.duration, a.start_limit, a.mass_scale, a.twist_relax) == (160.0, "record_only", 1.0, "preset")
    assert (a.pressure_grade, a.imu_grade, a.seed, a.threads) == ("normal", "ideal", 20261026, 4)
    assert (a.floor_roll, a.floor_pitch) == (3.3, 0.0)
    rc = abs(a.floor_roll) / run_S9.OPERATING_START_SPAN_DEG[0] + abs(a.floor_pitch) / run_S9.OPERATING_START_SPAN_DEG[1]
    assert math.isclose(rc, run_S9.RV3_B_K, abs_tol=1e-12)
    assert run_S9.p36_ready_limit(vars(a))["limit_s"] == 120.0


def test_b_matches_the_harness_case() -> None:
    """Harness id H3|S1|B|top|roll_pos@k0.75|Fs0 = the study ① H3 case with F_s 0 (spec 426.4 variant)."""
    import s9_soil_slope as ss

    assert run_S9.rv3_cases()[0]["floor_deg"] == ss._scaled_slope("roll_pos", run_S9.RV3_B_K)
    h = {c.case_id: c for c in ss.build_cases(("H3",))}
    pair = h[run_S9.RV3_HARNESS["RV3-B"]["pair_id"]]
    hc = dataclasses.replace(pair, fs_kN=0.0)
    assert hc.case_id == run_S9.RV3_HARNESS["RV3-B"]["id"]
    c = run_S9.rv3_cases()[0]
    assert (hc.roll_deg, hc.pitch_deg) == c["floor_deg"]
    assert (hc.soil, run_S9.P3B_PAD[hc.pad], hc.level, hc.fs_kN, hc.mass_scale) == (
        c["soil"], c["pad_variant"], c["level"], c["fs_kN"], 1.0)


def test_c_argv_is_g6p_s1fl_with_pad_a() -> None:
    """C = the G6P S1@FL argv (G1 base, S1 patch @FL grid 0.02, top, F_s 4, 160 s, model-limit note) with only
    --pad-variant cad330."""
    s9_batch, b = _batches()
    g6p = next(r for r in b["G6P"] if r["case"] == G6P_S1FL)["argv"]
    argv = b["RV3"][1]["argv"]
    assert len(argv) == len(g6p)
    assert {i for i, (x, y) in enumerate(zip(argv, g6p)) if x != y} == {argv.index("--pad-variant") + 1}
    a = run_S9.build_parser().parse_args(argv[len(s9_batch.RUN):] + ["--case", C_NAME, "--out-root", "x"])
    assert (a.soil, a.pad_variant, a.level, a.fs_kN, a.grid, a.duration) == ("G1", "cad330", "top", 4.0, 0.02, 160.0)
    assert (a.soil_patch, a.soil_patch_grid, a.note) == ("FL:S1", 0.02, run_S9.S1_MODEL_LIMIT_NOTE)
    assert (a.floor_roll, a.floor_pitch, a.start_limit, a.mass_scale) == (0.0, 0.0, "preset", 1.0)


@contextlib.contextmanager
def _argv_as_root():
    saved = sys.argv
    sys.argv = [saved[0] if saved else "", str(ROOT)]
    try:
        yield
    finally:
        sys.argv = saved


def test_c_key_is_in_the_x426_set() -> None:
    pytest.importorskip("numba")
    with _argv_as_root():
        import r72_g6_screen
    assert run_S9.RV3_HARNESS["RV3-C"]["id"] in r72_g6_screen.all_jobs("x426")


@pytest.mark.parametrize("argv", [["run", "RV3", "--parallel", "1", "--parallel-e", "1", "--e-cases", B_NAME],
                                  ["run", "RV3", "--parallel", "2"]])
def test_rv3_schedule_commands(argv) -> None:
    s9_batch, b = _batches()
    kw = s9_batch.schedule_args(s9_batch.build_parser().parse_args(argv), argv)
    q = s9_batch.schedule_cases(b["RV3"], e_cases=kw["e_cases"], parallel_e=kw["parallel_e"])
    if kw["parallel_e"]:
        assert [c["case"] for c in q["pcore"]] == [C_NAME] and [c["case"] for c in q["ecore"]] == [B_NAME]
        assert all(c["planned_pool"] == pool for pool in q for c in q[pool])
    else:
        assert [c["case"] for c in q["pcore"]] == RV3_NAMES and not q["ecore"]


def test_rv3_not_in_case_plan_and_folders_rejudged_by_path(tmp_path) -> None:
    """case_plan unchanged; the batch-folder rejudge picks P3b_* only, so both RV3 folders are re-judged by their
    case folder path (S9SL row) / by r76_g6_chrono_judge.py (G6 row)."""
    assert not set(RV3_NAMES) & {r["case"] for r in run_S9.case_plan()}
    for n in RV3_NAMES:
        (tmp_path / n).mkdir()
        (tmp_path / n / "result.json").write_text("{}", "utf-8")
    assert run_S9.rejudge_targets([str(tmp_path)]) == []
    assert [p.name for p in run_S9.rejudge_targets([str(tmp_path / B_NAME)])] == [B_NAME]
