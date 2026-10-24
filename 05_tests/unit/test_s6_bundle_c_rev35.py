"""Spec rev. 35 188.1 cad work: C-R13 (rerun35 set: H2 + crawler k_t x3 record case, H2 leak rows
against the 1st batch with the REANCHOR minimum), C-R14 (7c "truth undefined (ringing)"),
C-R15 (``leak_screened`` marks of the 181.3 screened beta cases); R8Series P-R8-15 getattr."""

from __future__ import annotations

import importlib.util
import math
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from outrigger_sim.verify import s6_bundle_c as bc

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "04_scripts" / "02_chrono"
CRAWLER_KT_BETA1_N_M = 1.942438e6
"""``(kt/kn)_pad`` 0.2331 x ``kn_per_sphere`` 8.333e6 N/m (YAML, beta 1.0 GPa)."""


@pytest.fixture(scope="module")
def run_s6c():
    """Load the script as a module; its import-time env settings are undone afterwards."""
    env = dict(os.environ)
    path = list(sys.path)
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("run_S6C_test35", SCRIPTS / "run_S6C.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        os.environ.clear()
        os.environ.update(env)
    yield mod
    sys.modules.pop(spec.name, None)
    sys.path[:] = path


# --- C-R13 -----------------------------------------------------------------------------------


def test_rerun35_set(run_s6c) -> None:
    groups = run_s6c.rerun35_groups()
    assert {g: [c.case_id for c in v] for g, v in groups.items()} == {
        "H2": ["C1_D8_top_fdown3.5_b0.69", "C1_D8_top_fdown3.5_b1.6",
               "C1_D8_top_fup3.5_b1.6", "C1_D8_top_roll5.5_b0.69"],
        "K": ["C1_D8_top_rpB_b1.6_crkt3"]}
    first = {c.case_id: c for c in run_s6c.bundle_c_cases()}
    for c in groups["H2"]:
        assert c == first[c.case_id]  # same definition as the 1st batch (direct comparison)
    assert set(run_s6c.RERUN35_ROLES) == {c.case_id for c in run_s6c.rerun35_cases()}
    assert [k for k, v in run_s6c.RERUN35_ROLES.items() if v == "gate"] == [
        "C1_D8_top_fdown3.5_b0.69", "C1_D8_top_fdown3.5_b1.6"]
    run_s6c.case_table()  # one definition per id across every set


def test_crawler_kt_x3_case(run_s6c) -> None:
    from outrigger_sim.chrono.crawler_bushing import crawler_bushing_values
    from outrigger_sim.params import load_params

    table = run_s6c.case_table()
    case, base = table["C1_D8_top_rpB_b1.6_crkt3"], table["C1_D8_top_rpB_b1.6"]
    assert case.crawler_kt_factor == 3.0 and base.crawler_kt_factor == 1.0
    assert case.scenario.floor == base.scenario.floor == "rpB"
    assert case.beta_GPa == 1.6 and case.duration_s == base.duration_s
    lv = case.scenario.level
    p = load_params(level=lv, overrides=run_s6c.param_overrides(case))
    pc = load_params(level=lv, overrides=run_s6c.controller_param_overrides(case) or None)
    s = run_s6c.crawler_kt_scales(case, p, p, pc)
    s1 = run_s6c.crawler_kt_scales(base, p, p, pc)
    assert s["sensitivity"] == 3.0 and s1["sensitivity"] == 1.0
    assert s["total"] == pytest.approx(3.0 * s1["total"], rel=1e-15)
    v = crawler_bushing_values(p, s["total"])
    v1 = crawler_bushing_values(p, s1["total"])
    assert v.kt_N_m == pytest.approx(3.0 * CRAWLER_KT_BETA1_N_M, rel=1e-6)
    assert v.ct_N_s_m == pytest.approx(math.sqrt(3.0) * v1.ct_N_s_m, rel=1e-12)


def test_rerun34_cases_unchanged_by_factor(run_s6c) -> None:
    for case in run_s6c.rerun34_cases():
        assert case.crawler_kt_factor == 1.0


def _m(cid, group, d8, reanchor=None):
    return {"case": cid, "rerun_group": group, "min_cyl_after_liftoff_kN": d8,
            "min_cyl_reanchor_kN": reanchor}


def test_h2_leak_rows_first_batch_only() -> None:
    refs = {"C1_D8_top_fdown3.5_b0.69": {"1st": 30.0, "rerun32": 10.0}}
    rrefs = {"C1_D8_top_fdown3.5_b0.69": {"1st": 19.78, "rerun32": 1.0}}
    rows = bc._leak_rows(_m("C1_D8_top_fdown3.5_b0.69", "H2", 31.0, 18.0), refs, rrefs)
    assert [r["leak_quantity"] for r in rows] == ["min_cyl_after_liftoff_kN",
                                                    "min_cyl_reanchor_kN"]
    assert rows[0]["leak_diff_kN"] == {"1st": pytest.approx(1.0)}
    assert rows[0]["leak_flag"] is False
    assert rows[1]["leak_diff_kN"] == {"1st": pytest.approx(-1.78)}
    assert all(r["passed"] is None and r["kind"] == "leak_compare" for r in rows)
    # H keeps its three runs and no REANCHOR row
    rows_h = bc._leak_rows(_m("x", "H", 31.0), {"x": {"1st": 30.0, "rerun32": 20.0}})
    assert len(rows_h) == 1 and rows_h[0]["leak_flag"] is True


def test_sensitivity_row() -> None:
    rows = bc._sens_rows(_m("C1_D8_top_rpB_b1.6_crkt3", "K", 30.0),
                         {"C1_D8_top_rpB_b1.6": {"rerun34": 38.55}})
    assert len(rows) == 1 and rows[0]["value"] == pytest.approx(-8.55)
    assert rows[0]["passed"] is None and rows[0]["kind"] == "report"
    assert bc._sens_rows(_m("C1_D8_top_rpB_b1.6", "H2", 30.0), None) == []


# --- C-R14 -----------------------------------------------------------------------------------


def _ringing_case():
    t = np.arange(0.0, 20.0, 1e-3)
    f = np.full((t.size, 4), 100e3)
    f[:, 0] += 8e3 * np.sin(2 * np.pi * t / 0.82)  # FL ringing (std ~ 5.7 kN)
    case = {"result": {"settings": {"start_t_s": 0.0}, "phases": [[0.0, "level"]]},
            "rec": {"t": t[::100], "F_crawler": np.zeros((t[::100].size, 3))},
            "pads": {"t": t, "F_cyl": f}}
    legs = []
    for rnd, t_move in ((0, 5.0), (1, 15.0)):
        for i, leg in enumerate(bc.LEGS):
            err = -18.0 if (rnd == 1 and leg == "FL") else 1.0
            legs.append({"round": rnd, "leg": leg, "probe_times_s": [t_move, t_move + 0.5,
                                                                    t_move + 1.0],
                         "truth_cyl_kN": 100.0, "load_estimate_kN": 100.0 + err,
                         "event_class": "post", "is_skipped": False,
                         "zero_cal_deduction": False})
    legs[0]["event_class"] = "pre"
    # round 0 FL: no ringing in its truth window (constant force)
    case["pads"]["F_cyl"][(t >= 4.5) & (t < 5.0), 0] = 100e3
    return case, {"legs": legs, "load_error_margin_kN": 8.0}


def test_truth_ringing_7c() -> None:
    case, pr = _ringing_case()
    ringing = bc.probe_truth_ringing(case, pr)
    assert [(r["round"], r["leg"]) for r in ringing] == [(1, "FL")]
    assert pr["legs"][0]["truth_undefined"] is False  # round 0 row unchanged
    assert pr["legs"][4]["truth_window_std_kN"] > 0.25 * 10.0
    assert pr["load_error_margin_with_ringing_kN"] == 8.0
    assert pr["load_error_margin_kN"] == pytest.approx(1.0 - 10.0)
    rows = bc._ringing_rows("c", pr)
    assert len(rows) == 1 and rows[0]["kind"] == "report" and rows[0]["passed"] is None
    assert rows[0]["value"] == pytest.approx(-18.0)
    assert "truth undefined (ringing)" in rows[0]["item"]


# --- C-R15 -----------------------------------------------------------------------------------


def test_leak_screened_ids_exist(run_s6c) -> None:
    table = run_s6c.case_table()
    for cid, cls in bc.LEAK_SCREENED_CASES.items():
        assert cid in table and cls in ("(a)", "(b)")
        assert table[cid].beta_GPa != 1.0 and table[cid].scenario.floor in bc.D8_FLOORS


def test_leak_screened_marks_only_prefix_runs() -> None:
    cid = "C4b_D8_bottom_rpB_b1.6"
    base = {"case": cid, "F_min_N": 9414.59, "floor": "rpB", "group": "D8"}
    pre = {**base, "bundle_c": {"beta_leak_fixed": False}}
    post = {**base, "bundle_c": {"beta_leak_fixed": True}}

    def marks(m):
        rows = [{"case": cid, "item": "x", "value": 1.0}, {"case": "other", "item": "x"}]
        bc.mark_leak_screened(rows, [m])
        assert "leak_screened" not in rows[1] and rows[0]["value"] == 1.0
        return rows[0].get("leak_screened"), rows[0].get("leak_screened_class")

    assert marks(pre) == ("rev35 181.3", "(a)")
    assert marks(post) == (None, None)


# --- P-R8-15 ---------------------------------------------------------------------------------


def test_r8_series_reads_p_r8_15(run_s6c, tmp_path) -> None:
    model = SimpleNamespace(actuator=SimpleNamespace(valve_state_m_s=np.zeros(4),
                                                     amp_output_m_s=np.zeros(4)))
    c2 = SimpleNamespace(
        probe_history=[], meta=lambda: {}, _state=None, events=[],
        phase=SimpleNamespace(value="level"),
        computed_output_m_s={"computed_u": np.ones(4), "raw_u": 2 * np.ones(4),
                             "increment_limited": [True, False, False, False]},
        command_components_m_s={})
    s = run_s6c.R8Series(model, c2)
    meas = SimpleNamespace(t_s=1.0, imu_specific_force_samples_m_s2=None)
    s(meas, SimpleNamespace(leg_speed_m_s=np.zeros(4)))
    info = s.save(tmp_path / "r8.npz")
    arr = np.load(tmp_path / "r8.npz")
    assert np.array_equal(arr["computed_u"][0], np.ones(4))
    assert np.array_equal(arr["raw_u"][0], 2 * np.ones(4))
    assert "increment_limited" in str(arr["limit_flags"][0])
    assert info["raw_u_available"] is True
    # absent names -> NaN / empty
    c2b = SimpleNamespace(**{**c2.__dict__, "computed_output_m_s": np.ones(4)})
    s2 = run_s6c.R8Series(model, c2b)
    s2(meas, SimpleNamespace(leg_speed_m_s=np.zeros(4)))
    s2.save(tmp_path / "r8b.npz")
    arr2 = np.load(tmp_path / "r8b.npz")
    assert np.isnan(arr2["raw_u"]).all() and arr2["limit_flags"][0] == ""
