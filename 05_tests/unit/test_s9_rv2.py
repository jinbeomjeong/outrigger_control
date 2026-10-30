"""RV2 (user approval 2026-10-30): the ``s9_batch.py run RV2`` rows of ``run_S9.rv2_cases`` = the P3b rows
J1 B top F_s 0 / 4 / 8 and J2 B top F_s 4 (DSb75 fires on the final controller), argv unchanged. No Chrono run."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

import run_S9  # noqa: E402

RV2_NAMES = ["P3b_J1_B_top_Fs0", "P3b_J1_B_top_Fs4", "P3b_J1_B_top_Fs8", "P3b_J2_B_top_Fs4"]
FORMER_ARGV_TAIL = ["level", "--soil", None, "--pad-variant", "dwg_rear250", "--level", "top", "--fs-kN", None,
                    "--grid", "0.01", "--crawler-grid", "0.04", "--settle-dashpot", "zrp", "--threads", "4",
                    "--duration", "120", "--pressure-grade", "normal", "--imu-grade", "ideal", "--seed", "20261026",
                    "--approved"]
"""argv after the interpreter / run_S9.py of the former runs (batch_P3b_20261027_174330 batch.json, 4790e2b)."""


def _batches():
    import s9_batch

    return s9_batch, s9_batch.batches()


def test_rv2_rows_names_estimates_and_notes() -> None:
    _, b = _batches()
    rows = b["RV2"]
    assert [r["case"] for r in rows] == RV2_NAMES
    assert all(r["planned_pool"] == "pcore" for r in rows)
    assert [r["est_s"] for r in rows] == [7000.0, 7100.0, 6900.0, 6900.0]
    assert [r["est_pool_s"]["ecore"] for r in rows] == [10500.0, 10600.0, 10300.0, 10300.0]
    for r in rows:
        assert r["est_s"] == r["est_pool_s"][r["planned_pool"]]
        assert r["note"].startswith("RV2 ") and run_S9.RV2_SOURCE_BATCH in r["note"]
    for c in run_S9.rv2_cases():
        assert c["group"] == "RV2" and c["expected"] is run_S9.RV2_EXPECTED
        assert c["harness_case"] == run_S9.RV2_HARNESS[c["case"]]["id"]
        assert c["original"] == run_S9.RV2_ORIGINAL[c["case"]]


def test_rv2_argv_equals_the_p3b_rows() -> None:
    """argv bit-equal to the P3b batch rows (no --note, no --mass-scale / floor / start-limit)."""
    s9_batch, b = _batches()
    p3b = {r["case"]: r["argv"] for r in b["P3b"]}
    for r in b["RV2"]:
        assert r["argv"] == p3b[r["case"]]
        for flag in ("--note", "--mass-scale", "--floor-roll", "--floor-pitch", "--start-limit", "--twist-relax",
                     "--soil-patch"):
            assert flag not in r["argv"]


def test_rv2_argv_equals_the_former_runs() -> None:
    """Same arguments as the former runs (batch.json of batch_P3b_20261027_174330; the 10-26 result.json args agree)."""
    s9_batch, b = _batches()
    for r in b["RV2"]:
        c = next(x for x in run_S9.rv2_cases() if x["case"] == r["case"])
        want = list(FORMER_ARGV_TAIL)
        want[2], want[8] = c["soil"], f"{c['fs_kN']:g}"
        assert r["argv"][len(s9_batch.RUN):] == want


def test_rv2_parsed_settings_and_p36_limit() -> None:
    s9_batch, b = _batches()
    ap = run_S9.build_parser()
    fs = {"P3b_J1_B_top_Fs0": 0.0, "P3b_J1_B_top_Fs4": 4.0, "P3b_J1_B_top_Fs8": 8.0, "P3b_J2_B_top_Fs4": 4.0}
    for r in b["RV2"]:
        a = ap.parse_args(r["argv"][len(s9_batch.RUN):] + ["--case", r["case"], "--out-root", "x"])
        assert (a.soil, a.pad_variant, a.level, a.fs_kN, a.grid, a.crawler_grid) == (
            r["case"].split("_")[1], "dwg_rear250", "top", fs[r["case"]], 0.01, 0.04)
        assert (a.duration, a.mass_scale, a.floor_roll, a.floor_pitch) == (120.0, 1.0, 0.0, 0.0)
        assert (a.pressure_grade, a.imu_grade, a.seed, a.threads) == ("normal", "ideal", 20261026, 4)
        lim = run_S9.p36_ready_limit(vars(a))
        assert lim["limit_s"] == 100.0 and lim["rear_pad_soils"] == [a.soil, a.soil]


@pytest.mark.parametrize("argv", [["run", "RV2", "--parallel", "4"],
                                  ["run", "RV2", "--parallel", "2", "--parallel-e", "2", "--e-cases",
                                   "P3b_J1_B_top_Fs8,P3b_J2_B_top_Fs4"]])
def test_rv2_schedule_command(argv) -> None:
    s9_batch, b = _batches()
    kw = s9_batch.schedule_args(s9_batch.build_parser().parse_args(argv), argv)
    q = s9_batch.schedule_cases(b["RV2"], e_cases=kw["e_cases"], parallel_e=kw["parallel_e"])
    if kw["parallel_e"]:
        assert [c["case"] for c in q["pcore"]] == RV2_NAMES[:2]
        assert [c["case"] for c in q["ecore"]] == RV2_NAMES[2:]
    else:
        assert kw["parallel"] == 4 and [c["case"] for c in q["pcore"]] == RV2_NAMES and not q["ecore"]


def test_rv2_batch_folder_rejudge_picks_all(tmp_path) -> None:
    """The batch-folder rejudge picks every RV2 folder (P3b_* names)."""
    for n in RV2_NAMES:
        (tmp_path / n).mkdir()
        (tmp_path / n / "result.json").write_text("{}", "utf-8")
    assert [p.name for p in run_S9.rejudge_targets([str(tmp_path)])] == sorted(RV2_NAMES)


def test_rv2_harness_values_match_the_rev83_records() -> None:
    """RV2_HARNESS READY values = R2_p3b.json (L1gs) / R2DS_p3b.json (DSb75); DSb75 fired (HOLD event) in each."""
    import json

    base = ROOT / "06_analysis" / "02_control" / "s9" / "rev83"
    if not (base / "R2DS_p3b.json").is_file():
        pytest.skip("rev83 harness records not present")
    rec = {n: {r["id"]: r for r in json.loads((base / n).read_text("utf-8"))["records"]}
           for n in ("R2_p3b.json", "R2DS_p3b.json")}
    for name, h in run_S9.RV2_HARNESS.items():
        a, d = rec["R2_p3b.json"][h["id"]], rec["R2DS_p3b.json"][h["id"]]
        assert round(a["t_ready_s"], 1) == h["ready_L1gs_s"] and round(d["t_ready_s"], 1) == h["ready_DSb75_s"]
        assert a["passed"] and d["passed"]
        assert d["t_ready_s"] - a["t_ready_s"] <= 2.2
        assert any(str(e[1]).startswith("INFO_DIFF_SINK_HOLD") for e in d["metrics"]["fix_events"])
