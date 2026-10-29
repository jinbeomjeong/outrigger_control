"""S9 ``run_S9.py`` records and judgement for the 2026-10-29 controller rules (control spec 414 /
416 / 419.8 / 420): the P3-2 late-LOC FLAG (``p32_late_loc_block``, decision 13), the code state
(``code_state_from_meta`` / ``code_state_files``), the zero calibration variant D keys, the rule event
counts of ``p3b_ext``, the 420.4 equivalence table (``s9_batch_summary.py E420``), unchanged case
definitions, and (when on disk) unchanged re-judgement of stored Chrono results. No Chrono."""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "04_scripts" / "02_chrono"
RESULTS = ROOT / "07_results" / "S9"
W = 380e3
T_LIM = 2.91165
V_MAX = 0.0209243016
SETTINGS = {"enable": True, "plateau_window_m": 0.01, "plateau_mean_speed_fraction": 0.15,
            "plateau_rise_max_N": 2000.0, "plausibility_fraction": 0.85, "push_speed_fraction": 0.25}


def _import(name: str):
    sys.path.insert(0, str(SCRIPTS))
    try:
        return importlib.import_module(name)
    finally:
        sys.path.remove(str(SCRIPTS))


r9 = _import("run_S9")


# --- P3-2 late LOC (spec 419.8) ---------------------------------------------------------------------------


def _series(t_dep: float = 35.0, loaded_around: float | None = None, loaded_lo: float = 0.0, loaded_hi: float = 0.0):
    t = np.round(np.arange(30.001, 70.0, 1e-3), 6)
    cn = np.where(t < t_dep, 0.3 * W, 0.0)
    if loaded_around is not None:
        cn[(t > loaded_around + loaded_lo) & (t < loaded_around + loaded_hi)] = 0.02 * W
    return t, cn


def _block(d: float = 4.0, events=None, *, t_done: float | None = 60.0, p33_within: bool | None = True,
           phases=None, cn_mod=None, t_dep: float = 35.0, lwa_on: bool | None = True):
    t, cn = _series(t_dep)
    if cn_mod is not None:
        cn = cn_mod(t, cn)
    t_loc = t_dep + d
    if events is None:
        events = [(36.0, "leg_reapproach_start:FL"), (36.1, "INFO_LOC_WINDOW_RESTART:FL"),
                  (37.5, "leg_reapproach_contact:FL")]
    events = sorted(events + [(t_loc, r9.SOIL_LOC_EVENT)])
    p32 = r9.p32_loc_block(t, cn, W, t_loc=t_loc, t_dep=t_dep, t_done=t_done, t_soil_mode=None,
                           soil_meta={"settings": SETTINGS, "t_P_s": t_loc - 1.0}, v_max_m_s=V_MAX)
    phases = phases or [(31.0, "level"), (60.0, "done")]
    return p32, r9.p32_late_loc_block(t, cn, W, events, phases, p32, {"within": p33_within}, period_s=0.1,
                                      lwa_on=lwa_on)


def test_late_loc_flag_all_conditions_true() -> None:
    p32, b = _block()
    assert p32["within"] is False and p32["loc_minus_departure_s"] == pytest.approx(4.0)
    assert b["time_clause_violated"] and b["flag"] and b["verdict"] == "flag"
    assert all(b["conditions"].values()) and b["t_off_s"] == 35.0
    assert b["t_reapproach_end_s"] == pytest.approx(37.5) and b["late_loc_reapproach_s"] == pytest.approx(4.0)
    assert b["loc_minus_reapproach_end_s"] == pytest.approx(1.5) and b["overlapping_reapproach_legs"] == ["FL"]
    assert b["reapproach_intervals"] == [{"leg": "FL", "start_s": 36.0, "end_s": 37.5, "overlaps_off_to_loc": True,
                                          "window_restarts_s": [36.1]}]
    assert b["restart_events_off_to_loc"] == 1 and b["crawler_normal_loc_period_max_N"] == 0.0
    assert b["limit_s"] == pytest.approx(T_LIM, abs=1e-5) and b["judgement_error"] is None and b["lwa_on"]


S = "leg_reapproach_start:"
C = "leg_reapproach_contact:"
R = "INFO_LOC_WINDOW_RESTART:"


@pytest.mark.parametrize("name, kwargs, cond", [
    ("no restart", {"events": [(36.0, S + "FL"), (37.5, C + "FL")]}, "1_restart"),
    ("re-approach over before t_off", {"events": [(33.9, S + "FL"), (34.0, R + "FL"), (34.5, C + "FL")]},
     "1_restart"),
    ("restart outside the overlapping re-approach", {"events": [(33.0, S + "RL"), (33.1, R + "RL"), (33.5, C + "RL"),
                                                                (36.0, S + "FL"), (37.5, C + "FL")]}, "1_restart"),
    ("re-approach ended too early", {"events": [(35.4, S + "FL"), (35.5, R + "FL"), (35.6, C + "FL")]},
     "2_delay_by_reapproach"),
    ("no end event", {"events": [(36.0, S + "FL"), (36.1, R + "FL")]}, "2_delay_by_reapproach"),
    ("end of another leg only", {"events": [(36.0, S + "FL"), (36.1, R + "FL"), (37.5, C + "RR")]},
     "2_delay_by_reapproach"),
    ("P3-3 fails", {"p33_within": False}, "4_load_strict"),
    ("FAULT event", {"events": [(36.0, S + "FL"), (36.1, R + "FL"), (37.5, C + "FL"),
                                (50.0, "FAULT_STROKE_END:RL")]}, "4_load_strict"),
    ("fault phase", {"phases": [(31.0, "level"), (55.0, "fault")]}, "4_load_strict"),
    ("fault_reground phase", {"phases": [(31.0, "level"), (55.0, "fault_reground")]}, "4_load_strict"),
    ("LOC after the first DONE", {"t_done": 38.0}, "5_loc_before_first_done"),
])
def test_late_loc_each_condition_false_is_a_failure(name, kwargs, cond) -> None:
    p32, b = _block(**kwargs)
    assert b["time_clause_violated"], name
    assert b["conditions"][cond] is False, name
    assert not b["flag"] and b["verdict"] == "fail", name


def test_late_loc_crawler_over_the_loc_period() -> None:
    # crawler 0.02 W during (t_LOC - 0.1, t_LOC) but 0 at the LOC sample: P3-2 load clause passes, condition 3 not
    def mod(t, cn):
        cn = cn.copy()
        cn[(t > 39.0 - 0.05) & (t < 39.0 - 0.001)] = 0.02 * W
        return cn
    p32, b = _block(cn_mod=mod)
    assert p32["crawler_loaded_at_loc"] is False
    assert b["conditions"]["3_not_false_loc"] is False and b["verdict"] == "fail"
    assert b["crawler_normal_loc_period_max_N"] == pytest.approx(0.02 * W) and b["crawler_normal_at_loc_N"] == 0.0

    # load only in the following period: record, not judged
    def nxt(t, cn):
        cn = cn.copy()
        cn[(t > 39.02) & (t < 39.08)] = 0.02 * W
        return cn
    _p, b2 = _block(cn_mod=nxt)
    assert b2["flag"] and b2["crawler_normal_next_period_max_N"] == pytest.approx(0.02 * W)
    # exactly 0.01 W over the period is "loaded" (strict <)
    _p, b3 = _block(cn_mod=lambda t, cn: np.where((t > 38.95) & (t <= 39.0), 0.01 * W, cn))
    assert b3["conditions"]["3_not_false_loc"] is False


def test_late_loc_wrapper_event_names_multi_leg_and_boundary() -> None:
    ev = [(35.9, S + "FL"), (35.95, S + "RR"), (36.0, "FIX_LW_RESTART:FL,RR"), (36.5, C + "FL"),
          (37.2, "WARN_LEG_REAPPROACH_NO_CONTACT:RR")]
    _p, b = _block(events=ev)
    assert b["flag"] and b["overlapping_reapproach_legs"] == ["FL", "RR"]
    assert b["t_reapproach_end_s"] == pytest.approx(37.2)
    # a later re-approach still open at the LOC -> condition 2 false, LWa judgement error
    _p, b2 = _block(events=ev + [(37.7, S + "RL")])
    assert b2["t_reapproach_end_s"] is None and b2["open_overlapping_interval"] and b2["verdict"] == "fail"
    assert "no end event" in b2["judgement_error"]
    # loc - max(t_off, t_re_end) exactly T_lim passes (<=)
    lim = r9.p32_time_limit_s(SETTINGS, V_MAX)
    ev3 = [(35.9, S + "FL"), (36.0, R + "FL"), (round(39.0 - lim, 9), C + "FL")]
    _p, b3 = _block(events=ev3)
    assert b3["conditions"]["2_delay_by_reapproach"] and b3["flag"]


def test_late_loc_reapproach_from_before_the_departure() -> None:
    """419.8.1: re-approach starts before the departure and ends after it; the only window-clear
    event is before the departure (LWa writes it once, when it clears a non-empty window)."""
    ev = [(34.0, S + "FL"), (34.1, R + "FL"), (36.5, C + "FL")]
    _p, b = _block(events=ev)
    assert b["restart_events_off_to_loc"] == 0  # the former reading (event inside [t_off, t_LOC]) would fail
    assert b["conditions"]["1_restart"] and b["t_reapproach_end_s"] == pytest.approx(36.5)
    assert b["loc_minus_reapproach_end_s"] == pytest.approx(2.5) and b["flag"] and b["verdict"] == "flag"


def test_late_loc_second_leg_starts_while_the_window_is_empty() -> None:
    """419.8.1: a second re-approach starting while the window is empty is not named in any restart
    event; t_re_end is still the latest end of all intervals overlapping [t_off, t_LOC]."""
    ev = [(36.0, S + "FL"), (36.1, R + "FL"), (36.8, S + "RR"), (37.0, C + "FL"), (37.6, C + "RR")]
    _p, b = _block(events=ev)
    assert b["overlapping_reapproach_legs"] == ["FL", "RR"] and b["t_reapproach_end_s"] == pytest.approx(37.6)
    assert b["loc_minus_reapproach_end_s"] == pytest.approx(1.4) and b["flag"]
    rr = next(iv for iv in b["reapproach_intervals"] if iv["leg"] == "RR")
    assert rr["window_restarts_s"] == [] and rr["overlaps_off_to_loc"]
    # the delay that counts comes from RR: FL (named in the event) ends 3.5 s before the LOC (> T_lim),
    # RR (not named) ends 0.5 s before it -> FLAG; the event-string reading would have failed it
    ev2 = [(35.2, S + "FL"), (35.3, R + "FL"), (35.4, S + "RR"), (35.5, C + "FL"), (38.5, C + "RR")]
    _p, b2 = _block(events=ev2)
    assert b2["t_reapproach_end_s"] == pytest.approx(38.5) and b2["flag"]
    assert 39.0 - 35.5 > r9.p32_time_limit_s(SETTINGS, V_MAX)
    # RR ends after the LOC on an LWa run -> judgement error, condition 2 false
    ev3 = ev[:4] + [(39.5, C + "RR")]
    _p, b3 = _block(events=ev3)
    assert b3["t_reapproach_end_s"] == pytest.approx(39.5) and not b3["conditions"]["2_delay_by_reapproach"]
    assert "after t_LOC" in b3["judgement_error"] and b3["verdict"] == "fail"
    _p, b4 = _block(events=ev3, lwa_on=False)
    assert b4["judgement_error"] is None and not b4["flag"]


def test_late_loc_pass_none_and_not_late() -> None:
    p32, b = _block(d=2.0)
    assert p32["within"] and b["verdict"] == "pass" and not b["flag"] and not b["time_clause_violated"]
    # within None (no T_lim): verdict None
    t, cn = _series()
    p32n = r9.p32_loc_block(t, cn, W, t_loc=39.0, t_dep=35.0, t_done=None, t_soil_mode=None, soil_meta={},
                            v_max_m_s=None)
    bn = r9.p32_late_loc_block(t, cn, W, [], [], p32n, {"within": True})
    assert bn["verdict"] is None and not bn["flag"]
    # LOC before the departure (d < 0): never a FLAG
    p32m, bm = _block(d=-0.5, events=[(34.0, "INFO_LOC_WINDOW_RESTART:FL"), (34.2, "leg_reapproach_contact:FL")])
    assert p32m["within"] is False and not bm["time_clause_violated"] and bm["verdict"] == "fail"
    # no LOC
    p32x = r9.p32_loc_block(t, cn, W, t_loc=None, t_dep=35.0, t_done=None, t_soil_mode=None,
                            soil_meta={"settings": SETTINGS}, v_max_m_s=V_MAX)
    bx = r9.p32_late_loc_block(t, cn, W, [], [], p32x, {"within": True})
    assert bx["verdict"] == "fail" and bx["conditions"]["3_not_false_loc"] is False


def _rev60_case_helper():
    spec = importlib.util.spec_from_file_location("_t_rev60", Path(__file__).with_name("test_s9_p3b_rev60.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_p3b_records_and_rejudge_carry_the_flag(tmp_path) -> None:
    mod = _rev60_case_helper()
    d = mod._case(tmp_path / "P3b_J1_B_top_Fs4")
    res = r9.rejudge_case(d, write=False)
    c, p32 = res["p3b"]["checks"], res["p3b"]["P3-2_loc"]
    assert res["unchanged_blocks_equal"]
    assert c["P3-2_within"] and c["P3-2_verdict"] == "pass" and c[r9.P32_LATE_LOC_FLAG] is False
    late = p32["late_loc_reapproach"]
    assert late["restart_events_before_loc"] == 0 and late["control_period_s"] == r9.CONTROL_PERIOD_DEFAULT_S
    assert set(late["conditions"]) == {"1_restart", "2_delay_by_reapproach", "3_not_false_loc", "4_load_strict",
                                       "5_loc_before_first_done"}
    # a stored block without the rule reads None in checks
    old = r9.p3b_checks({**res["p3b"], "P3-2_loc": {k: v for k, v in p32.items() if k != "late_loc_reapproach"}})
    assert old[r9.P32_LATE_LOC_FLAG] is None and old["P3-2_verdict"] is None


# --- code state, zero calibration, event counts ----------------------------------------------------------


def _meta(scm=True, lw=True, tol=True):
    m: dict = {"period_s": 0.1, "zero_calibration": {"settings": {"mode": "round_trip"}, "result": None}}
    if scm:
        m["slope_clearance_margin"] = {"settings": {"enable": True, "margin_m": 0.03}, "is_applied": False,
                                       "settle_attitude_deg": None}
    if lw:
        m["liftoff_window_reapproach"] = {"mode": "restart", "restarts": 0}
    if tol:
        m["zero_calibration"]["settings"]["return_timeout_tolerance_m"] = 0.0005
    return m


def test_code_state_from_meta() -> None:
    assert r9.code_state_from_meta({})["state"] == "pre_impl"
    assert r9.code_state_from_meta(_meta(False, False, False))["state"] == "pre_impl"
    f = r9.code_state_from_meta(_meta())
    assert f["state"] == "impl_final_rules" and f["missing"] == []
    p = r9.code_state_from_meta(_meta(lw=False))
    assert p["state"] == "impl_partial" and p["missing"] == ["liftoff_window_reapproach"]
    off = _meta()
    off["liftoff_window_reapproach"]["mode"] = "off"
    assert r9.code_state_from_meta(off)["missing"] == ["liftoff_window_reapproach"]


def test_code_state_files_hash_the_imported_modules() -> None:
    cs = r9.code_state_files()
    import outrigger_sim.control.c2 as c2

    assert cs["outrigger_sim.control.c2"]["sha256"] == hashlib.sha256(Path(c2.__file__).read_bytes()).hexdigest()
    assert cs["outrigger_sim.control.zero_calibration"]["path"].endswith("control/zero_calibration.py")


def test_preset_meta_reads_final_rules() -> None:
    from outrigger_sim.control.c2 import C2Config, C2Controller
    from outrigger_sim.params import load_params

    c2 = C2Controller.from_params(load_params(level="top"), C2Config().with_10hz_d1())
    cs = r9.code_state_from_meta(c2.meta())
    assert cs["state"] == "impl_final_rules", cs
    assert cs["zero_calibration_return_timeout_tolerance_m"] == pytest.approx(0.0005)
    z = r9.zero_calibration_outcome(c2.meta())
    assert z["return_timeout_tolerance_m"] == pytest.approx(0.0005) and z["move_skipped_legs"] == []
    assert r9.code_state_from_meta(C2Controller.from_params(load_params(level="top"), C2Config()).meta())["state"] \
        != "impl_final_rules"


def test_zero_calibration_outcome_variant_d_keys() -> None:
    meta = {"zero_calibration": {"is_active": True, "settings": {"return_timeout_tolerance_m": 0.0005},
                                 "result": {"legs": {"FL": {"status": "calibrated"},
                                                     "FR": {"status": "skipped", "reason": "move"},
                                                     "RL": {"status": "skipped", "reason": "grounded"},
                                                     "RR": {"status": "calibrated"}},
                                            "return_within_tolerance_m": {"FL": 0.00012}}}}
    z = r9.zero_calibration_outcome(meta)
    assert z["move_skipped_legs"] == ["FR"] and z["return_within_tolerance_m"] == {"FL": 0.00012}
    assert z["return_timeout_tolerance_m"] == 0.0005
    old = r9.zero_calibration_outcome({"zero_calibration": {"result": {"legs": {}}}})
    assert old["return_timeout_tolerance_m"] is None and old["return_within_tolerance_m"] is None


def test_p3b_ext_counts_the_rule_events() -> None:
    ev = [(101.0, "INFO_PRESSURE_ZERO_RETURN_TOL:RL:0.120"), (102.0, "WARN_PRESSURE_ZERO_SKIPPED:FR:move"),
          (110.0, "leg_reapproach_start:FL"), (110.5, "INFO_LOC_WINDOW_RESTART:FL"),
          (115.0, "INFO_LOC_CLEARANCE_MARGIN:80")]
    comp = {"phase": np.array(["C2Phase.TOUCH"])}  # no LEVEL sample: completion summary only counts
    out = r9.p3b_ext_records({}, ev, {}, comp, done_twist_N=3000.0, soil_patch_leg=None, t_loop_start_s=100.0)
    cnt = out["event_counts"]
    assert cnt["INFO_LOC_CLEARANCE_MARGIN"] == 1 and cnt["INFO_LOC_WINDOW_RESTART"] == 1
    assert cnt["INFO_PRESSURE_ZERO_RETURN_TOL"] == 1 and cnt["WARN_PRESSURE_ZERO_SKIPPED"] == 1
    assert cnt["leg_reapproach_start"] == 1
    rt = out["rule_event_times_rel_s"]
    assert rt["INFO_LOC_CLEARANCE_MARGIN"] == [[15.0, "INFO_LOC_CLEARANCE_MARGIN:80"]]
    assert rt["INFO_LOC_WINDOW_RESTART"] == [[10.5, "INFO_LOC_WINDOW_RESTART:FL"]]
    assert out["event_times_rel_s"] == {"INFO_LIFT_PAUSED": []}  # former block keys unchanged


# --- 420.4 equivalence table ------------------------------------------------------------------------------


def _result(meta: dict, events: list[tuple[float, str]], t_loc: float = 50.0, legs=None) -> dict:
    meta = json.loads(json.dumps(meta))
    meta["zero_calibration"]["result"] = {"legs": legs or {g: {"status": "calibrated"} for g in r9.LEGS}}
    meta["zero_calibration"]["is_active"] = True
    return {"action": "level", "controller_meta": meta, "c2_soil": {"t_loc_s": t_loc},
            "events": [{"t_s": t, "name": n} for t, n in events + [(t_loc, r9.SOIL_LOC_EVENT)]],
            "settle_reference": {"end_roll_pitch_deg": [0.1, -0.2]}}


def test_equivalence_420_4_rows(tmp_path) -> None:
    s = _import("s9_batch_summary")
    pre = _meta(False, False, False)
    ok = s.equivalence_420_4(tmp_path / "a", _result(pre, [(20.0, "INFO_PRESSURE_ZERO_CALIBRATED:FL")]))
    assert ok["equivalent"] and ok["code_state"]["state"] == "pre_impl"
    assert ok["a_loc_clearance_margin"]["status"] == "not_applicable"
    assert ok["a_loc_clearance_margin"]["tilt_le_1deg"] and ok["c_pre_loc_reapproach"]["count"] == 0
    legs = {**{g: {"status": "calibrated"} for g in r9.LEGS}, "RL": {"status": "skipped", "reason": "move"}}
    skip = s.equivalence_420_4(tmp_path / "b", _result(pre, [(20.0, "WARN_PRESSURE_ZERO_SKIPPED:RL:move")], legs=legs))
    assert not skip["equivalent"] and skip["b_zero_calibration"]["status"] == "rerun_with_new_code"
    assert skip["b_zero_calibration"]["move_skipped_legs"] == ["RL"]
    early = s.equivalence_420_4(tmp_path / "c", _result(pre, [(40.0, "leg_reapproach_start:FL"),
                                                              (60.0, "leg_reapproach_start:RR")]))
    assert not early["equivalent"] and early["c_pre_loc_reapproach"]["count"] == 1
    partial = _meta(lw=False)
    margin = s.equivalence_420_4(tmp_path / "d", _result(partial, [(50.0, "INFO_LOC_CLEARANCE_MARGIN:80")]))
    assert not margin["equivalent"] and margin["a_loc_clearance_margin"]["status"] == "not_equivalent"
    assert margin["code_state"]["state"] == "impl_partial"
    final = s.equivalence_420_4(tmp_path / "e", _result(_meta(), [(20.0, "INFO_PRESSURE_ZERO_RETURN_TOL:RL:0.1"),
                                                                  (40.0, "leg_reapproach_start:FL"),
                                                                  (41.0, "INFO_LOC_WINDOW_RESTART:FL")]))
    assert final["equivalent"] and final["c_pre_loc_reapproach"]["status"] == "final_code"
    assert len(final["b_zero_calibration"]["return_tol_events"]) == 1
    # the run's own code_state record wins over the meta
    own = _result(pre, [])
    own["code_state"] = {**r9.code_state_from_meta(_meta()), "files_at_start": {"x": 1}}
    assert s.equivalence_420_4(tmp_path / "f", own)["code_state"]["source"] == "result.code_state"


def test_summary_e420_folder(tmp_path) -> None:
    s = _import("s9_batch_summary")
    (tmp_path / "P3b_X").mkdir()
    (tmp_path / "P3b_X" / "result.json").write_text(json.dumps(_result(_meta(), [])), "utf-8")
    (tmp_path / "progress.log").write_text("# batch\nSTART P3b_X 2026-10-29T13:50:00 pid=1 est_s=1 pool=pcore\n"
                                           "START P3b_Y 2026-10-29T13:50:00 pid=2 est_s=1 pool=pcore\n", "utf-8")
    res = s.summary_e420(tmp_path)
    assert res["all_equivalent"] and res["missing"] == ["P3b_Y"]
    assert res["rows"]["P3b_X"]["started_local"] == "2026-10-29T13:50:00"
    assert s.summary_e420(tmp_path / "P3b_X")["rows"]["P3b_X"]["equivalent"]


# --- unchanged case definitions ---------------------------------------------------------------------------

CASE_DIGEST = {  # 2026-10-29, run_S9.py before the rev. 420 record changes (scratch case_digest.py)
    "case_plan": (77, "94fb6b4fc3c928e90050433fac8e51935a9fc812fe2e1600a097e78fba9ded27"),
    "p3b_cases": (24, "d500c3b0ffdd82d61e7443fe8b72373e275b2e884810607216d6a6eeed3afd07"),
    "p3b_aug_cases": (8, "bdd0b1bf10c172352cf43a02582ecac138d12e0212c265ae0533ae8591fec177"),
    "g6_cases": (3, "c7ef4a782e9f3de80f43c0c5b9d7106bc2f8110392fb3a57b29b02e71b7c6e64"),
    "g6p_cases": (6, "fa68218eaa67bdc5b3ab3be3c13420340996bb5b3b3f0ac46b35b8dc18ba7c7e"),
    "g6_open_loop_cases": (2, "ce8cf15e47e04d57677c53fe4442e6d5d382d63141a8d60f071c9e2c6ddc85ae"),
    "s9sl_cases": (4, "aa58b494839f36e08031a1bc3d63c6ce8b8c9a326892b8f70ca04c814a37454f"),
}


def test_case_definitions_unchanged() -> None:
    fns = {"case_plan": r9.case_plan, "p3b_cases": r9.p3b_cases, "p3b_aug_cases": r9.p3b_aug_cases,
           "g6_cases": r9.g6_cases, "g6p_cases": r9.g6p_cases, "g6_open_loop_cases": r9.g6_open_loop_cases,
           "s9sl_cases": lambda: r9.s9sl_cases(include_draft=True)}
    for name, fn in fns.items():
        cases = fn()
        argv = []
        for c in cases:
            try:
                argv.append(r9.p3b_level_argv(c))
            except Exception as e:  # noqa: BLE001 - same rule as the digest script
                argv.append(f"err {type(e).__name__}")
        blob = json.dumps(r9._plain([cases, argv]), sort_keys=True, ensure_ascii=False, default=str)
        assert (len(cases), hashlib.sha256(blob.encode()).hexdigest()) == CASE_DIGEST[name], name


# --- stored Chrono results: re-judgement unchanged except the added keys ----------------------------------

STORED = ["batch_p3b_aug_20261029_002839/P3b_J2_B_bottom_Fs4",
          "batch_G6P_20261028_154030/G6_G1_B_top_Fs4_spJ1FL",
          "batch_S9SL_20261028_194403/S9SL_C2_J1_A_top_Fs4_r4p4_p0"]
ADDED_P32 = {"late_loc_reapproach"}
ADDED_CHECKS = {r9.P32_LATE_LOC_FLAG, "P3-2_verdict"}


@pytest.mark.parametrize("rel", STORED)
def test_stored_case_rejudge_unchanged(rel) -> None:
    d = RESULTS / rel
    if not (d / "result.json").exists():
        pytest.skip(f"{rel} not on disk")
    stored = json.loads((d / "result.json").read_text("utf-8"))["p3b"]
    res = r9.rejudge_case(d, write=False)
    new = res["p3b"]
    assert res["unchanged_blocks_equal"], res["unchanged_block_diffs"]
    for block, added in (("P3-2_loc", ADDED_P32), ("checks", ADDED_CHECKS)):
        old_b, new_b = stored[block], json.loads(json.dumps(r9._plain(new[block])))
        assert set(new_b) - set(old_b) == added, (rel, block)
        assert {k: new_b[k] for k in old_b} == old_b, (rel, block)
    late = new["P3-2_loc"]["late_loc_reapproach"]
    assert late["restart_events_before_loc"] == 0 and not late["flag"]
    verdict = new["checks"]["P3-2_verdict"]
    w = new["checks"]["P3-2_within"]
    assert verdict == (None if w is None else ("pass" if w else "fail"))


@pytest.mark.skipif(not (RESULTS / "batch_G6P_20261028_154030").exists(), reason="G6P batch 20261028 not on disk")
def test_e420_on_the_stored_pre_implementation_g6p_batch() -> None:
    s = _import("s9_batch_summary")
    res = s.summary_e420(RESULTS / "batch_G6P_20261028_154030")
    assert len(res["rows"]) == 4 and res["all_equivalent"], {k: v["reasons"] for k, v in res["rows"].items()}
    for row in res["rows"].values():
        assert row["code_state"]["state"] == "pre_impl"
        assert row["b_zero_calibration"]["all_calibrated"] and row["c_pre_loc_reapproach"]["count"] == 0
