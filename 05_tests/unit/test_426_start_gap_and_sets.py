"""Spec 426.7 B, C, D: the study-1 extensions of ``s9_soil_slope.py`` (H8 start-gap cases, settle
targets, TOUCH record, ``--fs-kn`` / ``--level``), the r72 set ``x426`` with the ``|PA`` key field,
and T-5 (``s9_soil_closed_loop.apply_pad_start_gap``: start gap within 0.1 mm after the settle,
soil and rigid). The harness tests need numba."""

from __future__ import annotations

import contextlib
import json
import sys
from argparse import Namespace
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT / "04_scripts" / "03_control" / "s9", ROOT / "04_scripts" / "03_control" / "s8",
              ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import s9_soil_slope as ss  # noqa: E402

SETTLE_TABLE = ROOT / "06_analysis" / "00_dynamics" / "slope_crawler_settle.json"
START_GAP_TOL_MM = 0.1


@contextlib.contextmanager
def _argv_as_root():
    saved = sys.argv
    sys.argv = [saved[0] if saved else "", str(ROOT)]
    try:
        yield
    finally:
        sys.argv = saved


# ------------------------------------------------------------------------------ H8 (study D)
def test_h8_cases_of_spec_426_6() -> None:
    cases = ss.build_cases(("H8",))
    ids = [c.case_id for c in cases]
    assert len(cases) == ss.H8_SIZE == 33 and len(set(ids)) == 33
    assert {"H8|G1|B|top|flat", "H8|J2|B|top|flat", "H8|rigid|B|top|flat"} <= set(ids)
    assert "H8|J2|B|top|flat|FL:g55" in ids and "H8|rigid|B|top|flat|RR:d150" in ids
    assert sum(c.start_gap is None for c in cases) == 3
    assert all(c.pad == "B" and c.level == "top" and c.fs_kN == 4.0 for c in cases)
    assert len(ss.build_cases()) == 177  # H8 runs only when named


def test_former_case_dicts_have_no_start_gap_key() -> None:
    for case in ss.build_cases() + ss.build_cases(("H6",)):
        as_dict = case.to_dict()
        assert "start_gap" not in as_dict
        assert "pad_start_gap" not in ss.run_case_input(as_dict)


def test_start_gap_run_input() -> None:
    by_id = {c.case_id: c.to_dict() for c in ss.build_cases(("H8",))}
    assert ss.run_case_input(by_id["H8|J2|B|top|flat|FL:g55"])["pad_start_gap"] == {
        "leg": "FL", "gap_m": pytest.approx(0.055)}
    assert ss.run_case_input(by_id["H8|G1|B|top|flat|RR:d60"])["pad_start_gap"] == {
        "leg": "RR", "delta_m": pytest.approx(0.060)}
    as_json = json.loads(json.dumps(by_id["H8|G1|B|top|flat|RR:d60"]))  # list after a JSON trip
    assert ss.run_case_input(as_json)["pad_start_gap"]["leg"] == "RR"


def test_settle_gap_targets_follow_the_start_gap() -> None:
    table = (341.0, 342.0, 346.0, 347.0)
    assert ss.start_gap_targets_mm(table, None) == list(table)
    assert ss.start_gap_targets_mm(table, ("FL", "gap", 55.0)) == [55.0, 342.0, 346.0, 347.0]
    assert ss.start_gap_targets_mm(table, ["RR", "delta", 150.0]) == [341.0, 342.0, 346.0, 497.0]


def _touch_log(n: int, contact_from: int, latch_from: int) -> dict:
    t = [round(0.1 * (k + 1), 1) for k in range(n)]
    phases = ["check"] * 2 + ["touch"] * (n - 4) + ["level"] * 2
    fmin = [[-1.0] * 4 if k < contact_from else [5.0] * 4 for k in range(n)]
    stroke = [[2.0 * (k + 1)] * 4 for k in range(n)]
    att = [[0.0, 0.01 * k] for k in range(n)]
    touched = [[k >= latch_from] * 4 for k in range(n)]
    return {"t_s": t, "phase": phases, "fmin_kN": fmin, "touched": touched, "stroke_mm": stroke,
            "att_deg": att, "clear_est_mm": [30.0] * n}


def test_touch_record_flags() -> None:
    """Leg k first in contact over period 10 (start 1.0 s), latched at period 40 (4.1 s): stroke
    60 mm (> 40 mm T-3'), delay 3.1 s (> 3 s T-2'); attitude change 0.37 deg (no T-4)."""
    record = {"log": _touch_log(42, 10, 40), "case": {"start_gap": ("FL", "gap", 55.0)},
              "rod_weight_kN": [0.5] * 4, "rut_end_mm": 60.0}
    touch = ss.touch_record(record)
    leg = touch["legs"]["FL"]
    assert leg["first_contact_s"] == pytest.approx(1.0) and leg["latch_s"] == pytest.approx(4.1)
    assert leg["post_contact_stroke_mm"] == pytest.approx(82.0 - 20.0)
    assert leg["latch_after_contact_s"] == pytest.approx(3.1)
    assert touch["flags"] == ["T-3'", "T-2'"]
    assert touch["clearance_end_mm"]["true_minus_estimate"] == pytest.approx(30.0)
    reference = ss.touch_record({**record, "case": {"start_gap": None}})
    assert reference["flags"] == [] and reference["leg_k"] is None
    assert ss.touch_record({"log": {"t_s": []}, "case": {}}) is None  # other groups


def _namespace(**kwargs) -> Namespace:
    defaults = {"groups": "H1,H3", "filter": "|B|top|nose_down@k0.5,H1|G1|B|top|edge_nd",
                "settle_corrections": None, "settle_table": SETTLE_TABLE,
                "settle_key": "hook_harness", "plateau_rise_max_n": None, "mass_scale": None,
                "fs_kn": None, "level": None}
    return Namespace(**{**defaults, **kwargs})


def test_fs_and_level_are_applied_after_the_filter() -> None:
    plain = ss.select_cases(_namespace())
    assert [c.case_id for c in plain] == [
        "H1|G1|B|top|edge_nd", "H3|J1|B|top|nose_down@k0.5", "H3|J2|B|top|nose_down@k0.5",
        "H3|S1|B|top|nose_down@k0.5"]
    fs0 = ss.select_cases(_namespace(fs_kn=0.0))
    assert [c.case_id for c in fs0] == [f"{c.case_id}|Fs0" for c in plain]
    middle = ss.select_cases(_namespace(level="middle"))
    assert [c.level for c in middle] == ["middle"] * 4
    assert all(c.settle_table_status == "applied" for c in middle)
    assert middle[1].harness_settle_key == "J1|middle|0|1.6"
    assert middle[1].settle_table != plain[1].settle_table
    old_namespace = _namespace()
    del old_namespace.fs_kn, old_namespace.level  # callers built before spec 426
    assert ss.select_cases(old_namespace) == plain
    with pytest.raises(SystemExit):  # settle corrections are keyed per level
        ss._with_level(plain, "middle", _namespace(settle_corrections=Path("x.json")))


# --------------------------------------------------------------------------- r72 x426 (study C)
@pytest.fixture(scope="module")
def r72():
    pytest.importorskip("numba")
    with _argv_as_root():
        import r72_g6_screen
    return r72_g6_screen


def test_x426_set_of_spec_426_5(r72) -> None:
    keys = r72.all_jobs("x426")
    assert len(keys) == len(set(keys)) == 51
    assert sum(k.startswith("ref|") for k in keys) == 15
    assert "g6|G1+J1@FL|top|Fs4|PA" in keys and "g6r|rigid+S1@RR|middle|Fs4" in keys
    assert "ref|rigid|top|Fs8" in keys and "ref|S1|top|Fs4|PA" in keys
    former = set()
    for name in ("main", "ref", "all", "rigid", "rigidref", "rigid_all"):
        former |= set(r72.all_jobs(name))
    assert not former & set(keys)


def test_former_r72_sets_unchanged(r72) -> None:
    sizes = {n: len(r72.all_jobs(n)) for n in ("main", "ref", "all", "rigid", "rigidref",
                                               "rigid_all")}
    assert sizes == {"main": 48, "ref": 16, "all": 64, "rigid": 48, "rigidref": 4,
                     "rigid_all": 52}
    assert r72.all_jobs("all")[0] == "g6|G1+J1@FL|top|Fs0"
    assert r72.all_jobs("all")[-1] == "ref|S1|bottom|Fs4"


def test_pad_field_of_the_key(r72) -> None:
    assert r72.pad_of_key("g6|G1+J1@RR|top|Fs4") == "B"
    assert r72.pad_of_key("ref|G1|top|Fs4|PA") == "A"
    for bad in ("ref|G1|top|Fs4|PB", "ref|G1|top|Fs4|PA|x"):
        with pytest.raises(ValueError):
            r72.pad_of_key(bad)


# ----------------------------------------------------------------------------- T-5 start gap
@pytest.fixture(scope="module")
def harness():
    pytest.importorskip("numba")
    import s9_soil_closed_loop as sl

    cl, _, _ = sl._imports()
    return sl, cl


def _settled(sl, cl, soil: str):
    cl.rmf.CONFIG.clear()
    cl.rpt.RCFG.clear()
    plant = sl.make_plant(cl, "top", soil, "B", 4.0, settle_hook=sl.SETTLE_HOOK_HARNESS)
    plant.step(np.zeros(4), int(round(cl.rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
    return plant


@pytest.mark.parametrize(("soil", "spec"), [("J2", {"leg": "FL", "gap_m": 0.055}),
                                            ("rigid", {"leg": "RR", "delta_m": 0.060})])
def test_t5_start_gap_after_the_settle(harness, soil, spec) -> None:
    sl, cl = harness
    plant = _settled(sl, cl, soil)
    gaps_before = sl.pad_floor_gaps_m(cl, plant)
    record = sl.apply_pad_start_gap(cl, plant, spec)
    leg = sl.LEGS.index(spec["leg"])
    target_mm = spec["gap_m"] * 1e3 if "gap_m" in spec else gaps_before[leg] * 1e3 + 60.0
    gaps_after = sl.pad_floor_gaps_m(cl, plant)
    assert abs(gaps_after[leg] * 1e3 - target_mm) <= START_GAP_TOL_MM
    assert abs(record["g_start_mm"] - target_mm) <= START_GAP_TOL_MM
    others = [i for i in range(4) if i != leg]
    assert np.array_equal(gaps_after[others], gaps_before[others])


def test_start_gap_spec_errors(harness) -> None:
    sl, cl = harness
    for bad in ({"leg": "XX", "gap_m": 0.05}, {"leg": "FL"},
                {"leg": "FL", "gap_m": 0.05, "delta_m": 0.01}):
        with pytest.raises(ValueError):
            sl.apply_pad_start_gap(cl, None, bad)
