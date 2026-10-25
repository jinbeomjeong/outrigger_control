"""C-S8-42 (spec rev. 55 267 / 269.3, judge rev. 56): deferred-leg window end
min(next start, deferral + T_o) + 0.3 s cut at the run end, overlapping windows merged, T_o from
the controller meta; per-leg reference columns (event + 0..4 s, FLAG text > 0.5 kN / 0.1 s);
PROBE -> LEVEL return and re-READY record rows (= control c55_avail.py); data test: the
C-S8-36 A / D values of spec 266.1 / 266.2 do not change."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.verify import s8_control as v

ROOT = Path(__file__).resolve().parents[2]
C36 = ROOT / "07_results" / "S8" / "c36_20261025_155317"
REF768 = ROOT / "07_results" / "S8" / "ml_main_20261025_090131" / "episodes"
MLJ = ROOT / "07_results" / "S8" / "mlj_20261025_080212"
F_MIN = 9415.0
T0 = 3.0


def _pads(t_end: float = 10.0, value_N: float = 50_000.0) -> dict[str, np.ndarray]:
    """1 ms pad record (engine time from T0), ``value_N`` on every leg, no lift."""
    t = np.round(np.arange(T0 + 1e-3, T0 + t_end + 1e-9, 1e-3), 6)
    f = np.full((t.size, 4), value_N)
    return {"t": t, "F_cyl": f.copy(), "F_cyl_min_interval": f.copy(),
            "F_cyl_mean_20ms": f.copy(), "airborne": np.zeros((t.size, 4), bool)}


def _span(pads, leg: int, a_rel: float, b_rel: float, value_N: float, *,
          air: bool = False) -> None:
    sel = (pads["t"] >= a_rel + T0 - 1e-9) & (pads["t"] < b_rel + T0 - 1e-9)
    pads["F_cyl_min_interval"][sel, leg] = value_N
    pads["F_cyl"][sel, leg] = value_N
    pads["F_cyl_mean_20ms"][sel, leg] = value_N
    pads["airborne"][sel, leg] = air


def _win(names, te=0.0, pads=None, **kw):
    out = v.deferred_leg_minimum(names, te, T0, pads or _pads(), F_MIN, **kw)
    return {w["leg"]: w for w in out["windows"]}, out


# --- 269.3 #5 (i) .. (iii): window end --------------------------------------------------------


def test_i_no_restart_window_is_deferral_plus_t_o_plus_tail() -> None:
    by, out = _win([(2.2, "leg_reapproach_deferred:FR")])
    assert by["FR"]["window_s"] == [2.2, 3.3] and by["FR"]["next_start_s"] is None
    assert out["t_o_s"] == 0.8 and out["window_rule"] == "spec rev. 55 267"


def test_ii_next_start_before_t_o_ends_at_next_start_plus_tail() -> None:
    by, _ = _win([(2.4, "leg_reapproach_deferred:RL"), (2.5, "leg_reapproach_start:RL")])
    assert by["RL"]["window_s"] == [2.4, 2.8] and by["RL"]["next_start_s"] == 2.5


def test_iii_next_start_after_t_o_is_cut_at_deferral_plus_1p1_s() -> None:
    by, _ = _win([(2.0, "leg_reapproach_deferred:RR"), (3.5, "leg_reapproach_start:RR")])
    assert by["RR"]["window_s"] == [2.0, 3.1] and by["RR"]["next_start_s"] == 3.5


def test_window_is_cut_at_the_run_end() -> None:
    by, _ = _win([(9.5, "leg_reapproach_deferred:FL")])  # record ends at engine T0 + 10 s
    assert by["FL"]["window_s"] == [9.5, 10.0]


def test_t_o_from_the_controller_meta() -> None:
    assert v.deferred_t_o_s({"r8": {"lifted_reapproach": {"opposite_window_s": 0.5}}}) == 0.5
    assert v.deferred_t_o_s({}) == 0.8 and v.deferred_t_o_s(None) == 0.8
    assert v.deferred_t_o_s({"r8": {"lifted_reapproach": {"opposite_window_s": None}}}) == 0.8
    # the top-level controller meta lifted_reapproach is the run list, not the settings
    assert v.deferred_t_o_s({"lifted_reapproach": [{"start_s": 1.0}]}) == 0.8
    names = [(1.0, "leg_reapproach_deferred:FL")]
    cm = {"r8": {"lifted_reapproach": {"opposite_window_s": 0.5}}}
    rec = v.reapproach_rt_record(names, 0.0, T0, cm, _pads(), None, f_min_N=F_MIN)
    assert rec["deferred_min"]["windows"][0]["window_s"] == [1.0, 1.8]
    assert rec["deferred_min"]["t_o_s"] == 0.5


def test_overlapping_windows_of_a_leg_merge_separate_ones_stay() -> None:
    names = [(2.0, "leg_reapproach_deferred:RR"),   # -> [2.0, 3.1]
             (2.9, "leg_reapproach_deferred:RR"),   # -> [2.9, 3.4] (next 3.1): merged
             (3.1, "leg_reapproach_start:RR"),
             (5.0, "leg_reapproach_deferred:RR"),   # -> [5.0, 6.1]: separate
             (2.5, "leg_reapproach_deferred:FL")]   # other leg: separate
    _, out = _win(names)
    ws = [(w["leg"], w["deferred_s"], w["window_s"], w["next_start_s"]) for w in out["windows"]]
    assert ws == [("RR", [2.0, 2.9], [2.0, 3.4], 3.1), ("FL", [2.5], [2.5, 3.6], None),
                  ("RR", [5.0], [5.0, 6.1], None)]


# --- 269.3 #2: per-leg reference columns ---------------------------------------------------------


def test_leg_0_4s_stats_count_time_below_f_min_and_airborne() -> None:
    te = 1.0
    pads = _pads()
    _span(pads, 3, te + 1.0, te + 1.2, 5_000.0)             # 0.2 s below F_min
    _span(pads, 3, te + 1.2, te + 1.25, -2_000.0, air=True)  # 0.05 s airborne, below F_min
    _span(pads, 3, te + 4.5, te + 5.0, -9_000.0)             # after event + 4 s: outside
    by, _ = _win([(te + 2.0, "leg_reapproach_deferred:RR")], te, pads)
    ctx = by["RR"]["leg_0_4s"]
    assert ctx["min_kN"] == pytest.approx(-2.0) and ctx["min_t_s"] == pytest.approx(1.2)
    assert ctx["below_F_min_s"] == pytest.approx(0.25) and ctx["air_s"] == pytest.approx(0.05)


def _write_ref(d: Path, pads, *, event_t_s: float, ml: bool) -> Path:
    d.mkdir(parents=True)
    np.savez(d / "pads.npz", **pads)
    res = {"settings": {"start_t_s": T0}, "event_t_s": event_t_s}
    if ml:
        res.update({"episode": {"leg": "FR"}, "branch_t_s": event_t_s - 2.0})
    (d / "result.json").write_text(json.dumps(res), encoding="utf-8")
    return d


@pytest.mark.parametrize("ml", [True, False])
def test_reference_columns_and_flags(tmp_path, ml) -> None:
    te = 1.0  # event relative to the run start in both runs
    run = _pads()
    _span(run, 3, te + 1.0, te + 1.3, 3_000.0)    # min 3 kN, 0.3 s below F_min
    ref = _pads()
    _span(ref, 3, te + 1.0, te + 1.1, 3_600.0)    # min 3.6 kN, 0.1 s below F_min
    _span(ref, 2, te + 0.5, te + 0.6, 1_000.0)
    d = _write_ref(tmp_path / "ref" / "X", ref, event_t_s=(te + T0) if ml else te, ml=ml)
    _, dm = _win([(te + 1.5, "leg_reapproach_deferred:RR"),
                  (te + 1.6, "leg_reapproach_deferred:RL")], te, run)
    v.attach_deferred_reference(dm, d, ref_label="ref")
    by = {w["leg"]: w for w in dm["windows"]}
    assert by["RR"]["ref_0_4s"]["min_kN"] == pytest.approx(3.6)
    assert by["RR"]["ref_0_4s"]["below_F_min_s"] == pytest.approx(0.1)
    # deeper by 0.6 kN (> 0.5) and longer below F_min by 0.2 s (> 0.1): FLAG text
    assert by["RR"]["ref_flag"] == ["min 3.00 vs 3.60 kN", "below F_min 0.300 vs 0.100 s"]
    assert by["RL"]["ref_flag"] == [] and dm["ref_flag"] is True
    assert dm["reference"] == {"dir": str(d), "label": "ref"}


def test_reference_flag_thresholds_are_exclusive() -> None:
    run = {"min_kN": 1.0, "below_F_min_s": 0.2, "air_s": 0.1}
    ref = {"min_kN": 1.5, "below_F_min_s": 0.1, "air_s": 0.0}
    assert v.deferred_ref_flags(run, ref) == []          # exactly 0.5 kN / 0.1 s: no FLAG
    assert v.deferred_ref_flags(run, None) == [] and v.deferred_ref_flags(None, ref) == []
    assert v.deferred_ref_flags({**run, "air_s": 0.201}, ref) == ["airborne 0.201 vs 0.000 s"]


def test_missing_reference_keeps_none_columns(tmp_path) -> None:
    _, dm = _win([(1.0, "leg_reapproach_deferred:FL")])
    v.attach_deferred_reference(dm, tmp_path / "nothing")
    assert dm["reference"] is None and dm["windows"][0]["ref_0_4s"] is None
    assert dm["windows"][0]["ref_flag"] == [] and dm["ref_flag"] is False


def _cm(windows, reference=True):
    return {"reapproach_variant": "rt",
            "rt": {"deferred_min": {"windows": windows, "n_windows": len(windows),
                                    "worst": min(windows, key=lambda x: x["min_kN"]),
                                    "f_min_kN": F_MIN / 1e3,
                                    "reference": {"dir": "r"} if reference else None}}}


def _w(leg, kN, ref_flag=()):
    return {"leg": leg, "deferred_s": [2.0], "next_start_s": 2.5, "window_s": [2.0, 2.8],
            "min_kN": kN, "min_t_s": 2.1, "raw_min_kN": kN, "lift": False,
            "below_F_min": kN < F_MIN / 1e3, "leg_0_4s": {"min_kN": kN},
            "ref_0_4s": {"min_kN": kN}, "ref_flag": list(ref_flag)}


def test_deferred_min_rows_reference_flag_goes_into_the_text_only() -> None:
    (row,) = v.deferred_min_rows({"a": _cm([_w("RR", 12.0, ["min 12.00 vs 13.00 kN"])]),
                                  "b": _cm([_w("RL", 15.0)], reference=False)})
    assert row["passed"] is None and row["kind"] == "record"
    assert row["flagged"] == [] and row["ref_flagged"] == ["a"] and row["flag"] is True
    assert row["note"].startswith("no deferred leg below F_min | reference FLAG")
    assert row["runs_without_reference"] == ["b"] and row["window_rule"] == "spec rev. 55 267"
    assert row["item"].startswith("C-S8-41 RT deferral: true minimum of the deferred leg")
    (row2,) = v.deferred_min_rows({"a": _cm([_w("RR", 12.0)])})
    assert row2["flag"] is False and row2["note"] == "no deferred leg below F_min"


# --- 269.3 #3: PROBE -> LEVEL returns and re-READY ------------------------------------------------


def _episode(d: Path, te: float, phases: list[str], events: list[tuple[float, str]]) -> Path:
    d.mkdir(parents=True)
    t = te - 0.2 + 0.1 * np.arange(len(phases))
    np.savez(d / "r8_series.npz", t=t, phase=np.array(phases))
    (d / "result.json").write_text(json.dumps({"event_t_s": te}), encoding="utf-8")
    (d / "controller_events.json").write_text(json.dumps(
        [f"C2Event(t_s={x}, name='{n}')" for x, n in events]), encoding="utf-8")
    return d


def test_availability_record_probe_returns_and_re_ready(tmp_path) -> None:
    ph = ["probe", "level", "level", "probe", "level", "done", "done", "ready", "ready"]
    d = _episode(tmp_path / "e", 10.0, ph,
                 [(9.0, "probe_aborted_low_load:FL"), (10.12, "probe_aborted_low_load:RR"),
                  (10.3, "WARN_ROD_PRESSURE_FALLBACK:FR:D1")])
    r = v.availability_record(d)
    # the first probe -> level change is before the event (t = -0.1 s): not counted
    assert r["probe_returns_s"] == [0.2] and r["re_ready_s"] == 0.5
    assert r["probe_aborts"] == [[0.1, "probe_aborted_low_load:RR"]]
    assert r["rod_fallback"] == [[0.3, "WARN_ROD_PRESSURE_FALLBACK:FR:D1"]]


def test_availability_compare_matches_the_c55_rules() -> None:
    def rec(pr=(), rr=None, fb=()):
        return {"probe_returns_s": list(pr), "probe_aborts": [], "rod_fallback": list(fb),
                "re_ready_s": rr, "t_end_s": 28.0}

    new = {"a": rec(rr=5.0), "b": rec(rr=6.0), "c": rec(pr=[2.0]), "d": rec(), "e": rec(rr=3.0)}
    ref = {"a": rec(rr=5.2), "b": rec(rr=5.9), "c": rec(rr=7.0), "d": rec(rr=8.0), "e": None}
    s = v.availability_compare(new, ref)
    assert s["ids"] == 4 and s["missing_in_reference"] == ["e"]
    assert s["probe_return_runs_new"] == ["c"] and s["probe_return_ok"] is False
    assert s["median_delta_s"] == pytest.approx(-0.05) and s["re_ready_both"] == 2
    assert s["reached_only_in_ref_with_probe_return_or_fallback"] == ["c"]
    assert s["reached_only_in_ref_done_tail_record"] == ["d"]
    assert s["re_ready_ok"] is False and s["passed"] is False
    rows = v.availability_rows(new, ref, "768")
    assert [r["passed"] for r in rows] == [None, None]
    assert [r["criterion_met"] for r in rows] == [False, False]
    assert v.availability_rows(new, None, None) == []


# --- run_S8C c36 --bundle E --extra-ids (spec rev. 55 269.1) ----------------------------------


@pytest.mark.skipif(not (ROOT / "06_analysis" / "02_control" / "s8"
                         / "s8_rev52_r51_affected.json").exists(),
                    reason="C-S8-36 affected list not present")
def test_extra_ids_must_be_bundle_a_outside_the_17() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))
    import run_S8C

    a = run_S8C.c36_affected_ids()
    extra = [c for c in a if c not in run_S8C.C37_IDS][:2]
    assert run_S8C.c37_extra_problems(extra) == []
    probs = run_S8C.c37_extra_problems(["ML00_ep5", "ML99_ep9", extra[0], extra[0]])
    assert any("ML99_ep9" in p for p in probs) and any("ML00_ep5" in p for p in probs)
    assert any("duplicates" in p for p in probs)
    assert run_S8C.C37_D_DEFERRED_REF.as_posix() == "07_results/S8/mlj_20261025_080212"


# --- 269.3 #5 (iv): C-S8-36 A / D values unchanged (spec 266.1 / 266.2) ----------------------

A_EXPECTED = {  # run -> {leg: deferred-window judged minimum [kN]} (spec 266.1 / 266.2 / 266.2 note)
    "ML00_ep5": {"RR": -1.079, "RL": 11.70}, "ML34_ep7": {"RL": 22.67},
    "ML78_ep0": {"FR": 0.071, "RL": -1.186, "RR": 14.55},
    "ML78_ep1": {"RR": -0.974, "FL": 17.99, "RL": 18.22}, "ML78_ep3": {"RR": -0.689}}


@pytest.mark.skipif(not (C36 / "A_rt" / "episodes").is_dir() or not REF768.is_dir(),
                    reason="C-S8-36 bundle A / 768 records not present")
def test_iv_bundle_a_deferred_minima_unchanged_with_768_reference() -> None:
    from outrigger_sim.contact_episode import MachineConstants
    from outrigger_sim.control.c2 import C2Geometry
    from outrigger_sim.params import load_params

    params = load_params(level="top")
    mc = MachineConstants.from_geometry(C2Geometry.from_params(params))
    flagged = set()
    for run, legs in A_EXPECTED.items():
        m = v.ml_case_metrics(C36 / "A_rt" / "episodes" / run, params, mc)
        dm = m["rt"]["deferred_min"]
        assert dm["t_o_s"] == 0.8
        got = {}
        for w in dm["windows"]:
            got[w["leg"]] = min(got.get(w["leg"], 1e9), w["min_kN"])
        assert set(got) == set(legs), run
        for leg, kN in legs.items():
            assert got[leg] == pytest.approx(kN, abs=0.006), (run, leg)
        v.attach_deferred_reference(dm, REF768 / run, event_engine_time=True)
        assert dm["reference"] is not None, run
        flagged |= {(run, w["leg"]) for w in dm["windows"] if w["ref_flag"]}
        if run == "ML78_ep0":  # spec 266.2 rows (RT+F1 / 768)
            by = {w["leg"]: w for w in dm["windows"]}
            assert by["FR"]["leg_0_4s"] == {"min_kN": 0.071, "min_t_s": 2.212,
                                            "below_F_min_s": 0.053, "air_s": 0.0}
            assert by["RL"]["ref_0_4s"]["min_kN"] == pytest.approx(-1.244, abs=1e-3)
            assert by["RL"]["ref_0_4s"]["below_F_min_s"] == pytest.approx(0.438, abs=1e-3)
            assert by["RL"]["ref_0_4s"]["air_s"] == pytest.approx(0.298, abs=1e-3)
    # the six spec 266.2 legs stay inside the thresholds; the only reference FLAG is the
    # ML78_ep0 RR diagonal window (deferral +3.2 s, 11.7 kN above F_min in the window) with a
    # 0..4 s airborne time 1.082 vs 0.935 s (event transient at +0.1 s, before the deferral)
    assert flagged == {("ML78_ep0", "RR")}


@pytest.mark.skipif(not (C36 / "D_fs24" / "MLJ_FS24_Fs0").is_dir()
                    or not (MLJ / "MLJ_FS24_Fs0").is_dir(),
                    reason="C-S8-36 bundle D / original MLJ records not present")
def test_iv_bundle_d_fs0_rr_unchanged_with_mlj_reference() -> None:
    d = C36 / "D_fs24" / "MLJ_FS24_Fs0"
    case, _m, _pr, params = v._load(d)
    rt = v._rt_of_case(case, d, f_min_N=float(params.control.F_min_cylinder_N))["rt"]
    dm = rt["deferred_min"]
    (w,) = dm["windows"]
    assert w["window_s"] == [2.6, 3.5] and w["min_kN"] == pytest.approx(0.592, abs=0.01)
    v.attach_deferred_reference(dm, MLJ / "MLJ_FS24_Fs0")  # run_S8C convention, detected
    # spec 266.2: RT+F1 0.21 kN / 0.252 s / 0 s, original MLJ -0.87 kN / 0.194 s / 0.053 s
    assert w["leg_0_4s"]["min_kN"] == pytest.approx(0.21, abs=0.01)
    assert w["leg_0_4s"]["below_F_min_s"] == pytest.approx(0.252, abs=0.002)
    assert w["leg_0_4s"]["air_s"] == pytest.approx(0.0, abs=1e-9)
    assert w["ref_0_4s"]["min_kN"] == pytest.approx(-0.87, abs=0.01)
    assert w["ref_0_4s"]["below_F_min_s"] == pytest.approx(0.194, abs=0.002)
    assert w["ref_0_4s"]["air_s"] == pytest.approx(0.053, abs=0.002)
    assert w["ref_flag"] == []  # +0.058 s below F_min: under the 0.1 s threshold
