"""S8 CB rerun rows (U-S8-23, ``s6_control_spec.md`` rev. 46 216.8): controller lock-valve
premise, rod-pressure fallback 0, pilot-check twin regression, F2, CB_G4_Fs0 C8 floor."""

from __future__ import annotations

from outrigger_sim.verify import s8_control as s8


def _sm(cid, *, ctrl_lv="counterbalance", fallback=(), f2=0, plant_lv="counterbalance"):
    cm = {"two_pressure": {"settings": {} if ctrl_lv is None else {"lock_valve": ctrl_lv}}}
    return {"case": cid, "s8": {"lock_valve": plant_lv},
            "lock_valve": s8.lock_valve_premise({"lock_valve": plant_lv}, cm),
            "rod_fallback": {"events": list(fallback), "injected": False},
            "F2": {"violations": f2}}


def _m(cid, d8, ready, reanchor=None):
    return {"case": cid, "min_cyl_excl_reanchor_kN": d8, "min_cyl_reanchor_kN": reanchor,
            "times_s": {"ready": ready}}


def test_lock_valve_premise_keys() -> None:
    pilot = s8.lock_valve_premise({"lock_valve": "pilot_check"},
                                  {"two_pressure": {"settings": {}}})
    assert pilot["plant"] == "pilot_check" and pilot["cb_aware"] is None
    old = s8.lock_valve_premise({"lock_valve": "counterbalance"},
                                {"two_pressure": {"settings": {"load_estimate": "net"}}})
    assert old["cb_aware"] is False and old["controller"] is None
    new = s8.lock_valve_premise({"lock_valve": "counterbalance"},
                                {"two_pressure": {"settings": {"lock_valve": "counterbalance",
                                                               "moving_stroke_check": True}}})
    assert new["cb_aware"] is True and new["moving_stroke_check"] is True


def test_no_cb_case_gives_no_rows() -> None:
    sms = {"E_G4_Fs0": _sm("E_G4_Fs0", ctrl_lv=None, plant_lv="pilot_check")}
    assert s8.cb_rerun_rows(sms, {}, []) == []


def test_cb_rows_pass_with_twin_from_reference() -> None:
    sms = {"CB_G4_Fs0": _sm("CB_G4_Fs0")}
    by_id = {"CB_G4_Fs0": _m("CB_G4_Fs0", 40.0, 30.00)}
    rows = [s8._row("6 min after settlement", "CB_G4_Fs0", 12.10, 9.41, True)]
    ref = ("batch p1r", {"metrics": [_m("E_G4_Fs0", 40.1, 30.05)],
                         "rows": [s8._row("6 min after settlement", "E_G4_Fs0", 12.19, 9.41,
                                          True)]})
    out = s8.cb_rerun_rows(sms, by_id, rows, [ref])
    items = {r["item"]: r for r in out}
    assert items[s8.CB_PREMISE_ITEM]["passed"] is True
    assert items[s8.CB_NO_FALLBACK_ITEM]["passed"] is True
    assert items[s8.CB_F2_ITEM]["passed"] is True
    reg = items[s8.CB_REG_ITEM]
    assert reg["passed"] is True and abs(reg["value"]["event_min_kN"] + 0.09) < 1e-9
    assert items[s8.CB_G4_ITEM]["passed"] is True and items[s8.CB_G4_ITEM]["limit"] == 11.99
    assert items[s8.CB_ACCEPT_ITEM]["passed"] is True


def test_cb_unaware_controller_and_fallback_fail() -> None:
    fb = [{"t_s": 29.2, "leg": "RR", "reason": "D2", "in_forced_window": False}]
    sms = {"CB_G4_Fs0": _sm("CB_G4_Fs0", ctrl_lv=None, fallback=fb)}
    by_id = {"CB_G4_Fs0": _m("CB_G4_Fs0", 40.0, 30.0)}
    rows = [s8._row("6 min after settlement", "CB_G4_Fs0", 10.44, 9.41, True)]
    ref = ("batch p1r", {"metrics": [_m("E_G4_Fs0", 40.0, 30.0)],
                         "rows": [s8._row("6 min after settlement", "E_G4_Fs0", 12.18, 9.41,
                                          True)]})
    out = s8.cb_rerun_rows(sms, by_id, rows, [ref])
    items = {r["item"]: r for r in out}
    assert items[s8.CB_PREMISE_ITEM]["passed"] is False
    assert s8.CB_UNAWARE in items[s8.CB_PREMISE_ITEM]["note"]
    assert items[s8.CB_NO_FALLBACK_ITEM]["passed"] is False
    assert items[s8.CB_REG_ITEM]["passed"] is False  # event -1.74 kN
    assert items[s8.CB_G4_ITEM]["passed"] is False
    acc = items[s8.CB_ACCEPT_ITEM]
    assert acc["passed"] is False and acc["value"]["cb_unaware"] == ["CB_G4_Fs0"]


def test_missing_twin_is_hold_and_other_failed_row_counts() -> None:
    sms = {"CB_RE1bF_Fs8": _sm("CB_RE1bF_Fs8")}
    by_id = {"CB_RE1bF_Fs8": _m("CB_RE1bF_Fs8", 40.0, 30.0)}
    rows = [s8._row("C8 something", "CB_RE1bF_Fs8", 1.0, 2.0, False)]
    out = s8.cb_rerun_rows(sms, by_id, rows, [])
    items = {r["item"]: r for r in out}
    assert items[s8.CB_REG_ITEM]["kind"] == "hold" and items[s8.CB_REG_ITEM]["passed"] is None
    acc = items[s8.CB_ACCEPT_ITEM]
    assert acc["passed"] is False and acc["other_failed_rows"] == [
        "CB_RE1bF_Fs8: C8 something"]
