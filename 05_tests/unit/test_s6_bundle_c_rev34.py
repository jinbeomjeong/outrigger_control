"""Spec rev. 34 179.2 cad work: C-R11 (beta leak fix of run_S6C: controller at beta 1.0, crawler
tangential bushing at the beta 1.0 ratio), C-R12 (rerun34 set, re-approach rows, H-group
leak comparison rows)."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

from outrigger_sim.verify import s6_bundle_c as bc

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "04_scripts" / "02_chrono"
K_NOM_YAML_N_M = 2.2705e7
"""Spec 176.1 / 179.2: mean L1 pad stiffness of the YAML (beta 1.0 GPa)."""
CRAWLER_KT_BETA1_N_M = 1.942438e6
"""``(kt/kn)_pad`` 0.2331 x ``kn_per_sphere`` 8.333e6 N/m (YAML, beta 1.0 GPa)."""


@pytest.fixture(scope="module")
def run_s6c():
    """Load the script as a module; its import-time env settings are undone afterwards."""
    env = dict(os.environ)
    path = list(sys.path)
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("run_S6C_test34", SCRIPTS / "run_S6C.py")
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


def _params_of(run_s6c, case):
    from outrigger_sim.params import load_params

    lv = case.scenario.level
    p = load_params(level=lv, overrides=run_s6c.param_overrides(case) or None)
    pnf = load_params(level=lv, overrides=run_s6c.param_overrides(case, include_frame=False)
                      or None)
    pc = load_params(level=lv, overrides=run_s6c.controller_param_overrides(case) or None)
    return p, pnf, pc


# --- C-R11 -----------------------------------------------------------------------------------


@pytest.mark.parametrize("cid", ["C1_D8_top_rpB_b0.69", "C1_D8_top_rpB_b1.6",
                                 "C11_kf1.1e8_D8_top_rpB_b0.69"])
def test_controller_and_crawler_at_beta_1(run_s6c, cid) -> None:
    from outrigger_sim.chrono.crawler_bushing import crawler_bushing_values
    from outrigger_sim.control.c2 import C2Geometry

    case = run_s6c.case_table()[cid]
    assert run_s6c.controller_param_overrides(case) == {}
    over = run_s6c.param_overrides(case)
    assert "actuator.oil_bulk_modulus_eff_Pa" in over  # the plant keeps the beta
    p, pnf, pc = _params_of(run_s6c, case)
    geo = C2Geometry.from_params(pc)
    assert geo.nominal_pad_stiffness_N_m == pytest.approx(K_NOM_YAML_N_M, rel=1e-4)
    assert geo.oil_bulk_modulus_Pa == pytest.approx(1.0e9, rel=1e-12)
    s = run_s6c.crawler_kt_scales(case, p, pnf, pc)
    assert s["total"] == pytest.approx(s["frame"] * s["beta"], rel=1e-15)
    kt = crawler_bushing_values(p, s["total"]).kt_N_m
    assert kt == pytest.approx(CRAWLER_KT_BETA1_N_M, rel=1e-6)
    if case.front_frame_stiffness_N_m is not None:
        assert s["frame"] == run_s6c.c11_meta(case, p, pnf)["crawler_kt_scale"]


def test_beta_1_cases_unchanged(run_s6c) -> None:
    """beta 1.0 cases: controller overrides = case overrides without the frame term (as before
    C-R11) and a crawler factor of exactly 1 (no frame) / the C-11 factor (frame)."""
    for case in run_s6c.rerun34_cases():
        if case.beta_GPa != 1.0:
            continue
        assert run_s6c.controller_param_overrides(case) == run_s6c.param_overrides(
            case, include_frame=False)
        p, pnf, pc = _params_of(run_s6c, case)
        s = run_s6c.crawler_kt_scales(case, p, pnf, pc)
        assert s["beta"] == 1.0
        if case.front_frame_stiffness_N_m is None:
            assert s["frame"] == 1.0 and s["total"] == 1.0
        else:
            assert s["total"] == s["frame"]


# --- C-R12 -----------------------------------------------------------------------------------


def test_rerun34_set(run_s6c) -> None:
    groups = run_s6c.rerun34_groups()
    assert {g: len(v) for g, v in groups.items()} == {"E": 5, "F": 4, "FS": 1, "H": 6}
    (ps,) = groups["FS"]
    assert ps.sensor_model and ps.scenario.group == "PS" and ps.scenario.floor == "flat"
    assert ps.scenario.level == "top" and ps.scenario.zero_calibration
    assert ps.scenario.pressure_grade == "normal" and ps.scenario.case_id == ps.case_id
    assert all(c.beta_GPa != 1.0 for c in groups["H"])
    assert set(run_s6c.RERUN34_ROLES) <= {c.case_id for c in groups["H"]}
    table = run_s6c.case_table()
    for c in run_s6c.rerun34_cases():
        assert table[c.case_id] == c


def test_rerun34_readiness_keys(run_s6c) -> None:
    out = run_s6c.rerun34_readiness()
    for k in ("P-R8-13_mode", "P-R8-13_settings", "P-R8-14_command_components_attr",
              "rerun34_ready"):
        assert k in out
    assert set(out["P-R8-13_settings"]) == set(run_s6c.RERUN34_KEYS["P-R8-13_settings"])


def test_reapproach_rows() -> None:
    ra = {"count": 1, "starts": [{"t_s": 30.0, "leg": "FL"}]}
    for g in ("F", "FS"):
        (row,) = bc._reapproach_rows({"case": "N", "rerun_group": g, "floor_event_t_s": None,
                                      "reapproach": ra})
        assert row["passed"] is False and "re-approach starts = 0" in row["item"]
    (row,) = bc._reapproach_rows({"case": "E", "rerun_group": "E", "floor_event_t_s": 1.0,
                                  "reapproach": ra})
    assert row["kind"] == "report"
    assert bc._reapproach_rows({"case": "E", "rerun_group": "E", "floor_event_t_s": 1.0,
                                "reapproach": {"count": 0, "starts": []}}) == []


def test_leak_rows() -> None:
    refs = {"X": {"1st": 50.0, "rerun32": 48.0}, "Y": {"rerun33": 40.0}}
    (row,) = bc._leak_rows({"case": "X", "rerun_group": "H", "min_cyl_after_liftoff_kN": 49.0},
                           refs)
    assert row["passed"] is None and row["kind"] == "leak_compare"
    assert row["leak_flag"] is False and row["value"] == pytest.approx(-1.0)
    (row,) = bc._leak_rows({"case": "Y", "rerun_group": "H", "min_cyl_after_liftoff_kN": 36.5},
                           refs)
    assert row["leak_flag"] is True and row["note"].startswith("FLAG")
    assert "drop beyond -3 kN" in row["note"]
    assert bc._leak_rows({"case": "Y", "rerun_group": "E", "min_cyl_after_liftoff_kN": 1.0},
                         refs) == []
    (row,) = bc._leak_rows({"case": "Z", "rerun_group": "H", "min_cyl_after_liftoff_kN": 1.0},
                           refs)
    assert row["value"] is None and "no pre-fix value" in row["note"]
