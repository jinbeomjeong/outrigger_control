"""C-S8-33 (``s6_control_spec.md`` rev. 50 220.6 ① ... ⑥, U-S8-41 ... 43): fast settlement of
``result.event`` as a floor-event case (U-S8-32 window), item-4 moving threshold, expected rod
fallback of the injected leg, C-S8-29 h* per lock window, C-S8-24 round-start lower bounds, and
the MLJ batch rejudge (spec 220.2 / 220.3 / 220.4 values)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.verify import s6_control as s6
from outrigger_sim.verify import s8_control as s8

ROOT = Path(__file__).resolve().parents[2]
MLJ = ROOT / "07_results" / "S8" / "mlj_20261025_080212"


def _case(spec, *, settings_event=None, t_ev=47.7):
    return {"result": {"settings": {"event": settings_event, "level": "top"},
                       "event": {"name": "X", "spec": spec}, "event_t_s": t_ev,
                       "phases": [[0.1, "check"], [42.7, "ready"], [47.8, "level"],
                                  [71.7, "ready"]]}}


# --- ① fast settlement ---------------------------------------------------------------------------


def test_fast_settle_event_speed_rule() -> None:
    fs24 = s6.fast_settle_event(_case({"kind": "settle", "leg": "FR", "depth_m": 0.024,
                                       "ramp_s": 0.3}), 20.924e-3)
    assert fs24 is not None and fs24["event_legs"] == ["FR", "RL"]
    assert fs24["adjacent_legs"] == ["FL", "RR"] and fs24["speed_mm_s"] == pytest.approx(80.0)
    # G4 5.75 mm/s and SS9 0.45 mm/s keep the event-free rules
    assert s6.fast_settle_event(_case({"kind": "settle", "leg": "RR", "depth_m": 0.0115,
                                       "ramp_s": 2.0}), 20.924e-3) is None
    assert s6.fast_settle_event(_case({"kind": "settle", "leg": "RR", "depth_m": 0.009,
                                       "ramp_s": 20.0}), 20.924e-3) is None
    # an RR floor event of settings.event keeps the legacy path; a retract is not a settlement
    assert s6.fast_settle_event(_case({"kind": "settle", "leg": "RR", "depth_m": 0.03,
                                       "ramp_s": 0.1}, settings_event="settle_RR_30")) is None
    assert s6.fast_settle_event(_case({"kind": "retract", "leg": "RR", "depth_m": 0.03,
                                       "ramp_s": 0.1})) is None
    # a step settlement (ramp 0) is infinitely fast; the default v_max is the YAML value
    step = s6.fast_settle_event(_case({"kind": "settle", "leg": "RL", "depth_m": 0.01,
                                       "ramp_s": 0.0}))
    assert step is not None and step["event_legs"] == ["RL", "FR"] and step["speed_mm_s"] is None
    assert s6._is_floor_event_case({"event": None, "floor_event": step})
    assert not s6._is_floor_event_case({"event": "settle_RR"})


def test_fast_settle_window_is_the_u_s8_32_window() -> None:
    t = np.arange(40.0, 60.0, 1e-3)
    air = np.zeros((t.size, 4), bool)
    air[(t >= 47.9) & (t < 49.0), 2] = True  # RL (diagonal) lifted 1.1 s
    air[(t >= 47.8) & (t < 48.1), 1] = True  # FR
    z = np.zeros((t.size, 4, 3))
    case = _case({"kind": "settle", "leg": "FR", "depth_m": 0.024, "ramp_s": 0.3})
    case["pads"] = {"t": t + 3.0, "airborne": air, "ball_centre_world": z}
    fast = s6.fast_settle_event(case, 20.924e-3)
    w = s6.fast_settle_window(case, {"t0": 3.0}, fast)
    sp = s8.settle_lift_split(t, air, z[:, :, 2], 47.7, "FR", 0.024, 0.3, t3_s=0.82)
    assert w["lift_end_s"] == pytest.approx(47.7 + sp["window_end_rel_s"])
    assert w["lift_end_s"] == pytest.approx(49.0 + 0.82, abs=2e-3)
    assert w["primary_event_leg"] == "RL" and w["re_ready_s"] == pytest.approx(71.7)
    assert w["pressure_end_s"] == w["lift_end_s"]


# --- ② moving threshold --------------------------------------------------------------------------


def test_moving_threshold() -> None:
    assert s6._motion_state(1.75e-23) == "locked"
    assert s6._motion_state(-5e-7) == "locked"
    assert s6._motion_state(2e-6) == "extend" and s6._motion_state(-2e-6) == "retract"
    assert s6.MOVING_EPS_M_S == 1e-6


# --- ③ expected rod fallback ----------------------------------------------------------------------


def test_expected_rod_fallback_rows() -> None:
    ev = [{"t_s": 80.9000000017, "leg": "FR", "reason": "D1", "in_forced_window": False},
          {"t_s": 81.3, "leg": "FR", "reason": "D1", "in_forced_window": False},
          {"t_s": 80.9, "leg": "RL", "reason": "D1", "in_forced_window": False}]
    s8.mark_expected_rod_fallback(ev, "FR", 80.9000000016, 0.1)
    assert [e["expected_injected"] for e in ev] == [True, False, False]
    rows = [{"item": s8.WARN_ITEM, "case": "A", "value": 0, "passed": True, "note": "x"},
            {"item": s8.WARN_ITEM, "case": "B", "value": 0, "passed": True, "note": "x"}]
    fb_a = {"events": ev[:1], "injected": True, "fault_leg": "FR", "fault_t_s": 80.9,
            "expected_window_s": [80.9, 81.1]}
    fb_b = {"events": ev, "injected": True, "fault_leg": "FR", "fault_t_s": 80.9,
            "expected_window_s": [80.9, 81.1]}
    extra = s8.apply_rev46_rows(rows, {"A": {"s8": {}, "rod_fallback": fb_a},
                                       "B": {"s8": {}, "rod_fallback": fb_b}})
    assert extra == []
    assert rows[0]["passed"] is True and rows[0]["value"] == 0 and "FLAG" not in rows[0]["note"]
    assert len(rows[0]["rod_fallback_expected"]) == 1
    assert rows[1]["passed"] is None and rows[1]["value"] == 2 and "FLAG" in rows[1]["note"]


def test_rod_fault_of() -> None:
    res = {"settings": {"s8": {"event_spec": {"rod_fault": {"leg": "FR"}}}},
           "rod_fault_t_s": 80.9}
    assert s8.rod_fault_of(res) == ("FR", 80.9)
    res = {"settings": {}, "event": {"spec": {"rod_fault": {"leg": "RL"}}},
           "rod_fault_t_s": None}
    assert s8.rod_fault_of(res) == ("RL", None)
    assert s8.rod_fault_of({"settings": {}}) == (None, None)


# --- ④ h* ------------------------------------------------------------------------------------------


def test_h_star_matches_spec_219_4() -> None:
    """219.4: h* = (14.41 + 13 + 4.90 + 249.1) kN / (0.013273 + 2.99 x 0.00377) m^2 = 114.6
    bar."""
    a_p, a_a, r = 0.013273, 0.00377, 2.99
    hs = s8.h_star_Pa(9410.0, 13000.0, 4900.0 / a_a, r, 249100.0 / (r * a_a), a_p, a_a)
    assert hs / 1e5 == pytest.approx(114.6, abs=0.05)


# --- ⑤ requested probe rounds ----------------------------------------------------------------------


def test_requested_probe_round_lower() -> None:
    t = 3.0 + np.arange(0.0, 100.0, 0.1)
    low = np.full((t.size, 4), 70e3)
    low[:, 3] = 30e3
    series = {"t": t, "F_hat_N": low + 13e3, "F_band_N": np.full(t.size, 13e3),
              "F_lower_est_N": low}
    probes = [[{"t_move_start_s": 3.0 + 40.0}], [{"t_move_start_s": 3.0 + 86.75}]]
    rq = s8.requested_probe_round_lower(probes, series, 3.0, 86.6, 9414.59)
    assert [r["round"] for r in rq["rounds"]] == [1]
    assert rq["rounds"][0]["lower_kN"]["RR"] == pytest.approx(30.0)
    assert rq["threshold_kN"] == pytest.approx(24.41459) and rq["below_threshold"] is False


# --- MLJ batch rejudge (spec 220.2 / 220.3 / 220.4) ------------------------------------------------


@pytest.mark.skipif(not (MLJ / "batch.json").exists(), reason="MLJ batch not present")
def test_mlj_rejudge_rev50(tmp_path: Path) -> None:
    out = s8.judge_batch(MLJ, tmp_path / "v.json")
    doc = json.loads(out.read_text(encoding="utf-8"))
    rows = doc["rows"]
    assert doc["meta"]["failed"] == 0
    # rev. 52 (C-S8-37) prefixes its own revision to the chain
    assert "spec rev. 50 220.6" in doc["meta"]["judge_revision"]
    assert not [r for r in rows if "FLAG" in str(r.get("note") or "")]

    def val(case, item):
        r = [r for r in rows if r["case"] == case and r["item"] == item]
        assert len(r) == 1, (case, item)
        return r[0]

    for case, out4, tr4, rr in (("MLJ_FS24_Fs0", 130.9, 191.8, 69.83),
                                ("MLJ_FS24_Fs8", 117.5, 193.5, 65.84)):
        assert val(case, "3 F_min (1 ms)")["passed"] is None
        r = val(case, "4 max moving pressure outside the event transient")
        assert r["passed"] and r["value"] == pytest.approx(out4, abs=0.05)
        r = val(case, "4 max pressure in the event transient")
        assert r["passed"] and r["value"] == pytest.approx(tr4, abs=0.05)
        r = val(case, "3 F_min after the re-READY")
        assert r["passed"] and r["value"] == pytest.approx(rr, abs=0.005)
        assert val(case, "RE1b re-READY <= 60 s")["passed"]
        assert val(case, "5a rocking amplitude after the re-READY")["passed"]
    r = val("MLJ_FS24_Fs0", "3 F_min window end .. re-READY (record, F_min + 5 kN reference)")
    assert r["value"] == pytest.approx(18.01, abs=0.005)
    for case in ("MLJ_K0V_fdown3.5_G4RF_Fs0", "MLJ_K0V_fdown3.5_G4RF_Fs8"):
        w = val(case, "5.24.2 unexpected warnings")
        assert w["value"] == 0 and w["passed"] is True and len(w["rod_fallback_expected"]) == 1
        c29 = next(r for r in rows if r["case"] == case
                   and r["item"].startswith("C-S8-29 rod-sensor fault + G4"))
        assert c29["value"]["guard_cap_s"] == 0.0
        assert c29["value"]["push_cap_s"] == pytest.approx(0.8)
        lw = c29["lock_windows"]
        assert len(lw) == 5 and all(w["h_star_below_h_a"] for w in lw)
    lw0 = next(r for r in rows if r["case"] == "MLJ_K0V_fdown3.5_G4RF_Fs0"
               and r["item"].startswith("C-S8-29 rod-sensor fault + G4"))["lock_windows"]
    assert min(w["h_star_bar"] for w in lw0) == pytest.approx(76.1, abs=0.05)
    assert max(w["h_star_bar"] for w in lw0) == pytest.approx(84.1, abs=0.05)
    rq = next(r for r in rows if r["case"] == "MLJ_SS9P_Fs0"
              and r["item"].startswith("C-S8-24"))["requested_probe_rounds"]
    lo = rq["rounds"][0]["lower_kN"]
    assert [round(lo[k], 1) for k in ("FL", "FR", "RL", "RR")] == [114.6, 114.9, 71.1, 66.6]
