"""Spec rev. 33 172.2 cad work: C-R8 (R-5 justified firing on floor-event cases, lift-interval
note), C-R10 (C-11 front frame stiffness override, rerun33 set)."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.verify import s6_bundle_c as bc

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "04_scripts" / "02_chrono"


@pytest.fixture(scope="module")
def run_s6c():
    """Load the script as a module; its import-time env settings are undone afterwards."""
    env = dict(os.environ)
    path = list(sys.path)
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("run_S6C_test33", SCRIPTS / "run_S6C.py")
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


# --- C-R8 ------------------------------------------------------------------------------------


def _pads(t0: float, rr_force) -> dict:
    t = np.round(np.arange(0.0, 4.0, 1e-3), 9) + t0
    f = np.full((t.size, 4), 70e3)
    f[:, 3] = rr_force(t - t0)
    n = np.full((t.size, 4), 70e3)
    return {"t": t, "F_cyl": f, "N": n}


def _case(pads, t0=10.0) -> dict:
    return {"pads": pads, "result": {"settings": {"start_t_s": t0}}}


def test_justified_firing_rate_and_order() -> None:
    t0 = 10.0
    # RR falls at 50 kN/s from t = 1 s (relative)
    pads = _pads(t0, lambda t: np.where(t < 1.0, 70e3, 70e3 - 50e3 * (t - 1.0)))
    rv = {"other": [{"t_s": 1.5, "leg": "RR", "phase_before": "ready"}], "probe_abort": []}
    out = bc.relevel_justification(_case(pads, t0), {"t0": t0}, rv, t_event_s=1.0)
    f = out["firings"][0]
    assert f["rate_N_s"] == pytest.approx(50e3, rel=1e-6)
    assert f["justified"] is True
    # before the event: not justified even when the force falls
    out = bc.relevel_justification(_case(pads, t0), {"t0": t0}, rv, t_event_s=1.6)
    assert out["firings"][0]["justified"] is False
    # slow decline (10 kN/s) is not justified
    pads = _pads(t0, lambda t: np.where(t < 1.0, 70e3, 70e3 - 10e3 * (t - 1.0)))
    out = bc.relevel_justification(_case(pads, t0), {"t0": t0}, rv, t_event_s=1.0)
    assert out["firings"][0]["justified"] is False


def _rv(n_other: int) -> dict:
    other = [{"t_s": 1.0, "leg": "RR", "phase_before": "ready"}] * n_other
    return {"counts": {"other": n_other, "probe_abort": 0}, "other": other, "probe_abort": []}


def test_relevel_rows_split_by_floor_event() -> None:
    # floor event: justified-firing row, never the "= 0" row
    m = {"case": "E", "rerun_group": "D", "floor_event_t_s": 0.5, "relevel_predicted": _rv(1),
         "relevel_justification": {"firings": [
             {"t_s": 1.0, "leg": "RR", "phase_before": "ready", "rate_N_s": 48e3,
              "F_start_kN": 50.0, "F_end_kN": 36.0, "justified": True}]}}
    (row,) = bc._relevel_rows(m)
    assert row["item"].startswith("R-5 justified firing")
    assert row["passed"] is True and row["value"] == pytest.approx(48.0)
    # no floor event in a regression group: "= 0" judged
    for g in ("D", "F"):
        m = {"case": "N", "rerun_group": g, "floor_event_t_s": None, "relevel_predicted": _rv(1)}
        (row,) = bc._relevel_rows(m)
        assert "outside PROBE abort = 0" in row["item"] and row["passed"] is False
    # other groups: report only
    m = {"case": "N", "rerun_group": "G", "floor_event_t_s": None, "relevel_predicted": _rv(1)}
    (row,) = bc._relevel_rows(m)
    assert row["kind"] == "report"


def test_lift_note_lists_intervals_and_rr() -> None:
    li = {"intervals": {"FL": [{"start_after_event_s": 0.27, "length_s": 0.17, "rise_m": 1.5e-3}],
                        "FR": [], "RL": []},
          "RR": {"lifted": True, "first_recontact_after_event_s": 3.21,
                 "last_recontact_after_event_s": 4.88, "lifted_total_s": 4.08}}
    note = bc._lift_note(li)
    assert "FL 1x" in note and "(0.27, 0.170, 1.50)" in note
    assert "3.21 / 4.88" in note


# --- C-R10 -----------------------------------------------------------------------------------


def test_front_frame_formula(run_s6c) -> None:
    kn = {"FL": 25905744.2, "FR": 25905744.2, "RL": 19504614.9, "RR": 19504614.9}
    out = run_s6c.front_frame_overrides(kn, 1e9, 1.1e8)
    assert set(out) == {f"{run_s6c.KN_KEY}.FL", f"{run_s6c.KN_KEY}.FR"}
    k = out[f"{run_s6c.KN_KEY}.FL"]
    assert 1.0 / k == pytest.approx(1.0 / kn["FL"] - 1e-9 + 1.0 / 1.1e8, rel=1e-12)
    assert k / kn["FL"] - 1.0 == pytest.approx(-0.173, abs=2e-3)  # cad 2.5: -17.3 %


def test_rerun33_set(run_s6c) -> None:
    groups = run_s6c.rerun33_groups()
    assert {g: len(v) for g, v in groups.items()} == {"E": 3, "F": 4, "G": 8}
    roles = [c.c11_role for c in groups["G"]]
    assert roles.count("gate") == 4 and roles.count("record") == 4
    for c in groups["G"]:
        assert c.config == "C-11"
        assert c.front_frame_stiffness_N_m == run_s6c.C11_FRAME_N_M[c.c11_role]
        assert c.scenario.case_id == c.case_id
    for c in groups["E"] + groups["F"]:
        assert c.front_frame_stiffness_N_m is None
    assert len(run_s6c.case_table()) >= 15
    # the C-11 override touches only the front pad stiffness; the controller set has none
    gate = next(c for c in groups["G"] if c.c11_role == "gate" and "G4" in c.case_id)
    over = run_s6c.param_overrides(gate)
    assert set(over) == {f"{run_s6c.KN_KEY}.FL", f"{run_s6c.KN_KEY}.FR"}
    assert run_s6c.param_overrides(gate, include_frame=False) == {}
