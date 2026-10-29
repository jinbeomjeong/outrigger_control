"""G6P paper evidence set on the S9 runner (cad, user decision 2026-10-28): ``level --twist-relax`` /
``--note``, the six ``run_S9.g6p_cases`` rows and the ``s9_batch`` G6P rows (no Chrono run)."""

from __future__ import annotations

import sys
from dataclasses import asdict, fields
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

import run_S9  # noqa: E402

G6P_NAMES = ["G6_G1_B_top_Fs4_spJ1RR_noTR", "G6_G1_B_top_Fs4_spJ1RR", "G6_G1_B_top_Fs4_spJ1FL",
             "G6_G1_B_top_Fs4_spJ2RR", "G6_G1_B_top_Fs4_spJ2FL", "G6_G1_B_top_Fs4_spS1FL"]


def _preset():
    from outrigger_sim.control.c2 import C2Config

    return C2Config().with_10hz_d1()


def test_twist_relax_off_changes_only_the_enable_flag() -> None:
    preset = _preset()
    assert preset.twist_completion_relax.enable and preset.twist_completion_relax.rise_tol_N == 600.0
    off, meta = run_S9.apply_twist_relax(preset, "off")
    assert meta["mode"] == "off" and meta["overrides"] == {"twist_completion_relax.enable": False}
    assert meta["settings"] == {**asdict(preset.twist_completion_relax), "enable": False}
    for f in fields(preset):  # every other C2Config field is the very same object / value
        if f.name != "twist_completion_relax":
            assert getattr(off, f.name) == getattr(preset, f.name), f.name
    tr_p, tr_o = asdict(preset.twist_completion_relax), asdict(off.twist_completion_relax)
    assert {k for k in tr_p if tr_p[k] != tr_o[k]} == {"enable"}
    same, meta_p = run_S9.apply_twist_relax(preset, "preset")
    assert same is preset and meta_p["overrides"] == {} and meta_p["settings"]["enable"] is True
    with pytest.raises(ValueError):
        run_S9.apply_twist_relax(preset, "on")


def test_level_parser_twist_relax_and_note() -> None:
    ap = run_S9.build_parser()
    d = ap.parse_args(["level"])
    assert d.twist_relax == "preset" and d.note is None
    a = ap.parse_args(["level", "--twist-relax", "off", "--note", "a b"])
    assert a.twist_relax == "off" and a.note == "a b"
    with pytest.raises(SystemExit):
        ap.parse_args(["level", "--twist-relax", "on"])


def test_g6p_cases() -> None:
    cases = run_S9.g6p_cases()
    assert [c["case"] for c in cases] == G6P_NAMES
    want = [("RR", "J1", 0.01, 240.0, 10800.0), ("RR", "J1", 0.01, 160.0, 6950.0), ("FL", "J1", 0.01, 200.0, 8540.0),
            ("RR", "J2", 0.01, 200.0, 9500.0), ("FL", "J2", 0.01, 200.0, 9500.0), ("FL", "S1", 0.02, 160.0, 6600.0)]
    ap = run_S9.build_parser()
    for c, (leg, key, grid, dur, est) in zip(cases, want, strict=True):
        assert c["soil_patch"] == {"leg": leg, "set": key, "grid_m": grid} and c["group"] == "G6P"
        assert (c["soil"], c["pad"], c["level"], c["fs_kN"], c["grid_m"], c["crawler_grid_m"]) == \
            ("G1", "B", "top", 4.0, 0.02, 0.04)
        assert c["duration_s"] == dur and c["est_s"] == est and c["sim_s"] == dur + 8.0
        argv = run_S9.p3b_level_argv(c)
        assert argv[-1] == "--approved"
        a = ap.parse_args(argv + ["--case", c["case"], "--out-root", "x"])
        assert a.soil_patch == f"{leg}:{key}" and a.soil_patch_grid == pytest.approx(grid)
        assert a.duration == dur and a.threads == 4 and a.seed == 20261026 and a.pad_variant == "dwg_rear250"
        assert a.fs_kN == 4.0 and a.pressure_grade == "normal" and a.imu_grade == "ideal" and a.approved
        assert a.twist_relax == ("off" if c["case"].endswith("_noTR") else "preset")
    assert "noTR" not in "".join(run_S9.p3b_level_argv(cases[1]))
    assert "Bekker" in cases[5]["note"] and run_S9.build_parser().parse_args(
        run_S9.p3b_level_argv(cases[5])).note == run_S9.S1_MODEL_LIMIT_NOTE
    assert all("note" not in c for c in cases[1:5])
    plan = {r["case"]: r for r in run_S9.case_plan()}
    assert all(plan[n]["wall_est_s"] == c["est_s"] for n, c in zip(G6P_NAMES, cases, strict=True))


def test_g6p_argv_of_the_g6_rows_unchanged() -> None:
    """The G6 J1 rows of G6P give the G6 batch argv (same settings), only the duration / relax mode differ."""
    g6 = {c["case"]: run_S9.p3b_level_argv(c) for c in run_S9.g6_cases()}
    p = {c["case"]: run_S9.p3b_level_argv(c) for c in run_S9.g6p_cases()}
    assert p["G6_G1_B_top_Fs4_spJ1RR"] == g6["G6_G1_B_top_Fs4_spJ1RR"]
    assert p["G6_G1_B_top_Fs4_spJ1FL"] == g6["G6_G1_B_top_Fs4_spJ1FL"]
    off = p["G6_G1_B_top_Fs4_spJ1RR_noTR"]
    i = off.index("--twist-relax")
    base = off[:i] + off[i + 2:]
    j = base.index("--note")
    base = base[:j] + base[j + 2:]
    ref = list(g6["G6_G1_B_top_Fs4_spJ1RR"])
    ref[ref.index("--duration") + 1] = "240"
    assert base == ref


def test_s9_batch_g6p_rows_and_lpt_order() -> None:
    import s9_batch

    rows = s9_batch.batches()["G6P"]
    assert [r["case"] for r in rows] == G6P_NAMES
    assert [r["est_s"] for r in rows] == [10800.0, 6950.0, 8540.0, 9500.0, 9500.0, 6600.0]
    assert [bool(r.get("note")) for r in rows] == [True, False, False, False, False, True]
    q = s9_batch.schedule_cases(rows, e_cases=None, order="lpt", order_cases=None, parallel_e=0)
    assert [c["case"] for c in q["pcore"]][0] == "G6_G1_B_top_Fs4_spJ1RR_noTR"
    assert [c["case"] for c in q["pcore"]][-1] == "G6_G1_B_top_Fs4_spS1FL"


def test_run_level_records_the_relax_mode(monkeypatch) -> None:
    """run_level applies the mode right after the preset guard (no model build: stop at the next call)."""
    seen = {}

    def stop(config, engine):
        seen["config"] = config
        raise RuntimeError("stop")

    import outrigger_sim.chrono.fallback_ratio as fr

    monkeypatch.setattr(fr, "with_engine_fallback_ratio", stop)
    args = run_S9.build_parser().parse_args(["level", "--twist-relax", "off", "--approved"])
    with pytest.raises(RuntimeError, match="stop"):
        run_S9.run_level(args)
    assert seen["config"].twist_completion_relax.enable is False
    args = SimpleNamespace(**{**vars(args), "twist_relax": "preset"})
    with pytest.raises(RuntimeError, match="stop"):
        run_S9.run_level(args)
    assert seen["config"].twist_completion_relax.enable is True
