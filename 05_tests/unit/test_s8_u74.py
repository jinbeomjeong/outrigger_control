"""U-S8-74 (a) (``s6_control_spec.md`` rev. 68 354, user decision 2026-10-27): judge changes in
``verify.s8_control``.

* C-S8-72 fast-event F_min row: per leg the 0.5 s moving-mean minimum (windows ending at >= W
  end + 0.5 s) >= F_min AND no pad lift after the window end; the 1 ms instantaneous minimum is a
  record row, FLAG when < F_min; not judgeable when the run ends before W end + 0.5 s.
* C-S8-72 slow-event F_min row: unchanged (1 ms minimum after the event >= F_min).
* G4-4 (b): "instantaneous minimum > 0" -> "no pad lift-off (airborne 0)"; records without
  ``airborne`` fall back to judged force > 0.

The numbered tests follow the 354.2 list (① ... ⑥)."""

from __future__ import annotations

import numpy as np
import pytest
from test_s8_c_s8_68 import F_MIN, _synthetic  # same test folder

from outrigger_sim.verify import s8_control as s8

DT_S = 0.001
RUN_END_S = 10.0
W_END_S = 3.0
NOMINAL_FORCE_N = 40e3


def _record(run_end_s: float = RUN_END_S) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """1 ms times, judged force (all legs 40 kN) and airborne flags (none) of a run."""
    tp = np.round(np.arange(0.0, run_end_s + 1e-9, DT_S), 10)
    force = np.full((tp.size, 4), NOMINAL_FORCE_N)
    airborne = np.zeros((tp.size, 4), bool)
    return tp, force, airborne


def _span(tp: np.ndarray, start_s: float, length_s: float) -> np.ndarray:
    return (tp >= start_s - 1e-9) & (tp < start_s + length_s - 1e-9)


def _fast_rows(fm: dict) -> tuple[dict, dict | None]:
    rows = s8.g1_fmin_fast_rows("X", fm)
    judged = [r for r in rows if r["item"] == s8.G1_FMIN_ITEM]
    record = [r for r in rows if r["item"] == s8.G1_FMIN_RECORD_ITEM]
    assert len(judged) == 1 and len(record) <= 1
    return judged[0], (record[0] if record else None)


def test_1_contact_with_negative_instant_passes_and_flags() -> None:
    """① pad in contact, 1 ms judged force -0.6 kN, 0.5 s mean ~40 kN: passes, FLAG record."""
    tp, force, airborne = _record()
    force[_span(tp, 5.0, DT_S), 1] = -0.6e3
    fm = s8.g1_fmin_after_window(tp, force, airborne, W_END_S, F_MIN)
    assert fm["status"] == "judged" and fm["passed"] is True
    assert fm["no_lift"] is True and fm["airborne_total_s"] == 0.0
    assert fm["airborne_source"] == "pads.airborne"
    assert fm["instant_min_kN"] == pytest.approx(-0.6)
    assert (fm["instant_leg"], fm["instant_t_s"]) == ("FR", pytest.approx(5.0))
    assert fm["instant_below_F_min"] is True
    assert fm["below_zero_s"]["FR"] == pytest.approx(DT_S)
    assert fm["longest_below_s"]["FR"] == pytest.approx(DT_S)
    assert fm["mean05_min_kN"]["FR"] == pytest.approx(40.0 - 40.6 / 500, abs=1e-6)
    judged, record = _fast_rows(fm)
    assert judged["kind"] == "judged" and judged["passed"] is True
    assert judged["value"] == [pytest.approx(fm["mean05_min_all_kN"]), 0.0]
    assert judged["limit"] == [pytest.approx(F_MIN / 1e3), 0.0]
    assert record["kind"] == "record" and record["passed"] is None
    assert record["flag"] is True and record["note"].startswith("FLAG")
    assert record["value"]["instant_min_kN"] == pytest.approx(-0.6)


def test_1b_instant_above_f_min_is_not_flagged() -> None:
    tp, force, airborne = _record()
    fm = s8.g1_fmin_after_window(tp, force, airborne, W_END_S, F_MIN)
    _judged, record = _fast_rows(fm)
    assert record["flag"] is False and not record["note"].startswith("FLAG")


def test_2_pad_lift_fails() -> None:
    """② 0.05 s of pad lift after the window end fails although the mean stays high."""
    tp, force, airborne = _record()
    airborne[_span(tp, 6.0, 0.05), 2] = True
    fm = s8.g1_fmin_after_window(tp, force, airborne, W_END_S, F_MIN)
    assert fm["mean05_min_all_kN"] >= F_MIN / 1e3
    assert fm["airborne_s"]["RL"] == pytest.approx(0.05)
    assert fm["no_lift"] is False and fm["passed"] is False
    judged, _record_row = _fast_rows(fm)
    assert judged["passed"] is False and judged["value"][1] == pytest.approx(0.05)


def test_2b_lift_before_the_window_end_is_not_counted() -> None:
    tp, force, airborne = _record()
    airborne[_span(tp, 2.0, 0.5), 2] = True  # ends before W end
    fm = s8.g1_fmin_after_window(tp, force, airborne, W_END_S, F_MIN)
    assert fm["passed"] is True and fm["airborne_s"]["RL"] == 0.0


def test_3_mean_below_f_min_without_lift_fails() -> None:
    """③ a leg holding 8 kN (< F_min 9.415 kN) after the window end, no lift: fails."""
    tp, force, airborne = _record()
    force[tp >= 4.0, 3] = 8e3
    fm = s8.g1_fmin_after_window(tp, force, airborne, W_END_S, F_MIN)
    assert fm["no_lift"] is True and fm["passed"] is False
    assert fm["mean05_min_kN"]["RR"] == pytest.approx(8.0)
    assert fm["below_F_min_s"]["RR"] == pytest.approx(RUN_END_S - 4.0 + DT_S, abs=2 * DT_S)
    assert fm["longest_below_s"]["RR"] == pytest.approx(fm["below_F_min_s"]["RR"])


def test_3b_mean_windows_end_at_or_after_w_plus_half_second() -> None:
    """A dip just after W end only enters windows ending >= W end + 0.5 s partly (354.2)."""
    tp, force, airborne = _record()
    force[_span(tp, W_END_S, 0.25), 0] = 0.0  # inside the first full window only
    fm = s8.g1_fmin_after_window(tp, force, airborne, W_END_S, F_MIN)
    # the first window ending at W + 0.5 s holds 0.249 s of 0 N: 40 * (0.251 / 0.5)
    assert fm["mean05_min_kN"]["FL"] == pytest.approx(40.0 * 0.251 / 0.5, abs=0.1)


def test_4_g4_4_instant_positive_no_lift_passes() -> None:
    """④ C-S8-71 ``MLJ_G4H_FS24_RL_Fs0`` form: instantaneous 4.12 kN, no lift, mean >= F_min."""
    d = _synthetic(reground=True, lifted_leg="RL", rl_after_kN=60.0)
    tp = d["tp"]
    d["judged_force_N"][_span(tp, 16.0, 0.02), 2] = 4.12e3
    g = s8.g4_metrics(expect="reground", **d)["g4_4"]
    assert g["passed"] is True and g["no_lift"] is True
    assert g["airborne_source"] == "pads.airborne"
    assert g["instant_min_positive"] is True and g["instant_min_ge_F_min"] is False
    assert g["min_from_fault_plus_1s_kN"]["RL"] == pytest.approx(4.12)
    row = [r for r in s8.g4_rows("X", s8.g4_metrics(expect="reground", **d))
           if "G4-4" in r["item"]][0]
    assert row["kind"] == "judged" and row["passed"] is True
    assert "no pad lift-off" in row["item"] and "no pad lift-off True" in row["note"]


def test_4b_g4_4_lift_fails_and_force_sign_is_only_recorded() -> None:
    """④ (b) is the pad lift: a 20 ms lift fails; a 0 N dip without lift only sets the record."""
    d = _synthetic(reground=True, lifted_leg="RL", rl_after_kN=60.0)
    tp = d["tp"]
    d["airborne"][_span(tp, 16.0, 0.02), 2] = True
    g = s8.g4_metrics(expect="reground", **d)["g4_4"]
    assert g["mean05_passed"] is True and g["no_lift"] is False and g["passed"] is False
    d2 = _synthetic(reground=True, lifted_leg="RL", rl_after_kN=60.0)
    d2["judged_force_N"][_span(tp, 16.0, 0.02), 2] = 0.0
    g2 = s8.g4_metrics(expect="reground", **d2)["g4_4"]
    assert g2["instant_min_positive"] is False and g2["no_lift"] is True
    assert g2["passed"] is True


def test_4c_g4_4_force_sign_fallback_without_airborne() -> None:
    """354.1: an old record without ``airborne`` judges (b) on judged force > 0."""
    d = _synthetic(reground=True, lifted_leg="RL", rl_after_kN=60.0)
    d["airborne"] = None
    g = s8.g4_metrics(expect="reground", **d)["g4_4"]
    assert g["airborne_source"] == "force_sign_fallback" and g["passed"] is True
    d["judged_force_N"][_span(d["tp"], 16.0, 0.02), 2] = 0.0
    g0 = s8.g4_metrics(expect="reground", **d)["g4_4"]
    assert g0["no_lift"] is False and g0["passed"] is False


def test_4d_g1_force_sign_fallback_without_airborne() -> None:
    tp, force, _airborne = _record()
    force[_span(tp, 5.0, 0.01), 0] = 0.0
    fm = s8.g1_fmin_after_window(tp, force, None, W_END_S, F_MIN)
    assert fm["airborne_source"] == "force_sign_fallback"
    assert fm["airborne_s"]["FL"] == pytest.approx(0.01) and fm["passed"] is False


def test_5_short_tail_after_the_window_is_not_judgeable() -> None:
    """⑤ the run ends < 0.5 s after W end: not judgeable (row kind not_judgeable)."""
    tp, force, airborne = _record(run_end_s=W_END_S + 0.4)
    fm = s8.g1_fmin_after_window(tp, force, airborne, W_END_S, F_MIN)
    assert fm["status"] == "not_judgeable" and fm["passed"] is None
    assert fm["mean05_min_kN"] is None and "before the window end" in fm["reason"]
    judged, record = _fast_rows(fm)
    assert judged["kind"] == "not_judgeable" and judged["passed"] is None
    assert record is not None and record["kind"] == "record"
    # exactly W end + 0.5 s is judgeable
    tp2, force2, air2 = _record(run_end_s=W_END_S + 0.5)
    assert s8.g1_fmin_after_window(tp2, force2, air2, W_END_S, F_MIN)["status"] == "judged"


def _g1_case(fast: bool, f_min_after: dict, *, mismatch: bool = False) -> dict:
    """Minimal ``sm['g1']`` for :func:`s8.g1_rows` (U-S8-32 rows stubbed out)."""
    sp = {"any_lift": False, "cum_lift_s": 0.0}
    return {"g1": {"fast": fast, "phase_mismatch": mismatch, "event_state": {},
                   "u_s8_32": sp, "F_min_after": f_min_after,
                   "u58": {"passed": True, "s6_metrics": {}}, "final_phase": "ready",
                   "end_att_deg": [0.0, 0.0], "work": {}, "reapproach": {}, "harness": {}}}


def test_6_slow_event_row_unchanged(monkeypatch) -> None:
    """⑥ slow event: value = 1 ms minimum, limit F_min, the same pass rule and note."""
    monkeypatch.setattr(s8, "u_s8_32_rows", lambda *args, **kwargs: [])
    for min_kN, expected in ((9.0, False), (12.0, True)):
        fm = {"from_s": 5.0, "min_kN": min_kN, "leg": "RR", "t_s": 7.25,
              "per_leg_kN": {"FL": 30.0, "FR": 31.0, "RL": 32.0, "RR": min_kN},
              "F_min_kN": F_MIN / 1e3}
        rows = [r for r in s8.g1_rows({"S": _g1_case(False, fm)})
                if r["item"].startswith("C-S8-72 F_min")]
        assert len(rows) == 1
        row = rows[0]
        assert row["item"] == s8.G1_FMIN_ITEM and row["kind"] == "judged"
        assert (row["value"], row["limit"], row["passed"]) == (min_kN, F_MIN / 1e3, expected)
        assert row["note"] == (f"from 5.0 s; min RR at 7.25 s; per leg "
                               f"{ {'FL': 30.0, 'FR': 31.0, 'RL': 32.0, 'RR': min_kN} } kN")


def test_6b_fast_rows_in_g1_rows_and_phase_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(s8, "u_s8_32_rows", lambda *args, **kwargs: [])
    tp, force, airborne = _record()
    fm = s8.g1_fmin_after_window(tp, force, airborne, W_END_S, F_MIN)
    rows = [r for r in s8.g1_rows({"F": _g1_case(True, fm)})
            if r["item"].startswith("C-S8-72 F_min")]
    assert [r["kind"] for r in rows] == ["judged", "record"]
    rows_na = [r for r in s8.g1_rows({"F": _g1_case(True, fm, mismatch=True)})
               if r["item"].startswith("C-S8-72 F_min")]
    assert [r["kind"] for r in rows_na] == ["not_judgeable", "record"]
    summary = s8.g1_summary(rows)
    assert summary["F"]["passed"] == 1 and summary["F"]["records"] == 1


def test_rule_strings_and_revision() -> None:
    assert "U-S8-74 (a)" in s8.G1_FMIN_RULE and s8.G1_FMIN_RULE in s8.G1_RULE
    assert "no pad lift-off (airborne samples 0" in s8.G4_4_RULE
    assert "instantaneous minimum > 0 (no pad lift-off)" not in s8.G4_4_RULE
    assert "U-S8-74 (a)" in s8.JUDGE_REVISION_U74
    assert s8.G1_FMIN_ITEM.startswith("C-S8-72") and s8.G1_FMIN_RECORD_ITEM.startswith("C-S8-72")
