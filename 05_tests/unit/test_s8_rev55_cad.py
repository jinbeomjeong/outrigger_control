"""C-S8-41 (spec rev. 54 260.5 / 261 / 264, U-S8-56 (a) / U-S8-57 (a)): ML-0 gate row "no
rod-pressure fallback without a sensor-fault injection", the RT deferred-leg minimum record row
(deferral .. next start + 0.3 s, FLAG below F_min), the summary with the ML-1 count, and (data
tests) the C-S8-36 bundle A list of spec 260.1 and the bundle D deferred minimum."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.verify import s8_control as v

ROOT = Path(__file__).resolve().parents[2]
C36 = ROOT / "07_results" / "S8" / "c36_20261025_155317"
FALLBACK_17 = {"ML00_ep5", "ML10_ep0", "ML21_ep1", "ML24_ep6", "ML25_ep7", "ML33_ep4", "ML34_ep7",
               "ML39_ep5", "ML42_ep6", "ML51_ep4", "ML54_ep0", "ML59_ep7", "ML71_ep6", "ML81_ep5",
               "ML87_ep1", "ML87_ep5", "ML89_ep0"}
"""Spec rev. 54 260.1: the 17 bundle-A runs with WARN_ROD_PRESSURE_FALLBACK (reason D1)."""
F_MIN = 9415.0
T0 = 3.0


def _pads(t_end: float = 10.0) -> dict[str, np.ndarray]:
    """1 ms pad record (engine time from T0), 50 kN on every leg, no lift."""
    t = np.round(np.arange(T0 + 1e-3, T0 + t_end + 1e-9, 1e-3), 6)
    f = np.full((t.size, 4), 50_000.0)
    return {"t": t, "F_cyl": f.copy(), "F_cyl_min_interval": f.copy(),
            "F_cyl_mean_20ms": f.copy(), "airborne": np.zeros((t.size, 4), bool)}


def _dip(pads, leg: int, t_rel: float, value_N: float, *, mean_N: float | None = None,
         air: bool = False) -> None:
    k = int(np.argmin(np.abs(pads["t"] - (t_rel + T0))))
    pads["F_cyl_min_interval"][k, leg] = value_N
    pads["F_cyl"][k, leg] = value_N
    if mean_N is not None:
        pads["F_cyl_mean_20ms"][k, leg] = mean_N
    pads["airborne"][k, leg] = air


def test_deferred_window_ends_at_next_start_plus_0p3_s() -> None:
    te = 2.0  # event, relative to the run start
    names = [(te + 2.0, "leg_reapproach_deferred:RR"), (te + 2.6, "leg_reapproach_deferred:RR"),
             (te + 2.7, "leg_reapproach_start:RR"), (te + 3.4, "leg_reapproach_deferred:RL")]
    pads = _pads()
    _dip(pads, 3, te + 2.95, 7_000.0)   # inside RR [2.0, 3.0]
    _dip(pads, 3, te + 3.05, 1_000.0)   # after next start + 0.3 s: outside
    _dip(pads, 3, te + 1.90, 500.0)     # before the deferral: outside
    # RL never starts again: C-S8-42 (spec rev. 55 267) window = deferral + T_o 0.8 + 0.3 s
    # (rev. 55: the run end)
    _dip(pads, 2, te + 4.4, 12_000.0)   # inside RL [3.4, 4.5]
    _dip(pads, 2, te + 5.0, 1_000.0)    # after deferral + 1.1 s: outside since rev. 56
    out = v.deferred_leg_minimum(names, te, T0, pads, F_MIN)
    by = {w["leg"]: w for w in out["windows"]}
    assert set(by) == {"RR", "RL"} and out["n_windows"] == 2
    assert by["RR"]["deferred_s"] == [2.0, 2.6]          # merged: overlapping windows
    assert by["RR"]["window_s"] == [2.0, 3.0] and by["RR"]["next_start_s"] == 2.7
    assert by["RR"]["min_kN"] == pytest.approx(7.0) and by["RR"]["min_t_s"] == pytest.approx(2.95)
    assert by["RR"]["below_F_min"] is True
    assert by["RL"]["window_s"] == [3.4, 4.5]
    assert by["RL"]["next_start_s"] is None and by["RL"]["min_kN"] == pytest.approx(12.0)
    assert by["RL"]["below_F_min"] is False
    assert out["flag"] is True and out["worst"]["leg"] == "RR"


def test_airborne_sample_uses_the_20_ms_mean_raw_kept() -> None:
    te = 1.0
    names = [(te + 2.0, "leg_reapproach_deferred:FR"), (te + 2.5, "leg_reapproach_start:FR")]
    pads = _pads()
    _dip(pads, 1, te + 2.2, -3_000.0, mean_N=10_000.0, air=True)
    out = v.deferred_leg_minimum(names, te, T0, pads, F_MIN)
    w = out["windows"][0]
    assert w["min_kN"] == pytest.approx(10.0) and w["raw_min_kN"] == pytest.approx(-3.0)
    assert w["lift"] is True and w["below_F_min"] is False and out["flag"] is False


def test_deferrals_before_the_event_are_ignored_and_rt_record_carries_the_minimum() -> None:
    te = 4.0
    names = [(te - 1.0, "leg_reapproach_deferred:FL"), (te + 1.0, "leg_reapproach_start:FL")]
    pads = _pads()
    rec = v.reapproach_rt_record(names, te, T0, {}, pads, None, f_min_N=F_MIN)
    assert rec["deferred"] == 0 and rec["deferred_min"] is None
    names.append((te + 0.5, "leg_reapproach_deferred:FL"))
    rec = v.reapproach_rt_record(names, te, T0, {}, pads, None, f_min_N=F_MIN)
    assert rec["deferred_min"]["windows"][0]["window_s"] == [0.5, 1.3]


def _cm(variant, windows):
    return {"reapproach_variant": variant,
            "rt": {"deferred_min": {"windows": windows, "n_windows": len(windows),
                                    "worst": min(windows, key=lambda x: x["min_kN"]),
                                    "f_min_kN": F_MIN / 1e3}}}


def _w(leg, kN):
    return {"leg": leg, "deferred_s": [2.0], "next_start_s": 2.5, "window_s": [2.0, 2.8],
            "min_kN": kN, "min_t_s": 2.1, "raw_min_kN": kN, "lift": False,
            "below_F_min": kN < F_MIN / 1e3}


def test_deferred_min_rows_record_rt_runs_only_and_flag() -> None:
    cms = {"a": _cm("rt", [_w("RR", 0.59)]), "b": _cm("rt", [_w("RL", 11.7)]),
           "c": _cm(None, [_w("FR", -5.0)])}
    (row,) = v.deferred_min_rows(cms)
    assert row["kind"] == "record" and row["passed"] is None
    assert row["value"]["rt_runs"] == 2 and row["value"]["flagged_runs"] == 1
    assert row["flag"] is True and row["flagged"] == ["a"]
    assert row["value"]["worst"] == ["a", "RR", 0.59]
    assert v.deferred_min_rows({"c": cms["c"]}) == []


def test_rod_fallback_gate_counts_uninjected_runs_incl_forced_window() -> None:
    ev = [{"leg": "FR", "t_s": 58.3, "reason": "D1", "in_forced_window": False}]
    fw = [{"leg": "RR", "t_s": 40.0, "reason": "D1", "in_forced_window": True}]
    cms = {"ok": {"rod_fallback": {"events": [], "injected": False}},
           "bad": {"rod_fallback": {"events": ev, "injected": False}},
           "forced": {"rod_fallback": {"events": fw, "injected": False}},
           "inj": {"rod_fallback": {"events": ev, "injected": True}},
           "head": {"fault_injected": True, "rod_fallback": {"events": ev, "injected": False}}}
    g = v.rod_fallback_gate(cms)
    assert g["checked"] == 3 and set(g["runs"]) == {"bad", "forced"}
    assert g["runs"]["forced"][0][3] is True


def test_summary_carries_gate_ml1_count_and_deferred_flag() -> None:
    rows = [v._row("ML-0 no rod-pressure fallback without a sensor-fault injection (gate)", "*",
                   17, 0, False),
            v._row("ML-1 runs with a rod-pressure fallback warning (record)", "*", 17, None,
                   None, kind="record"),
            *v.deferred_min_rows({"a": _cm("rt", [_w("RR", 0.59)])})]
    s = v.judge_summary(rows)
    assert s["ml0_rod_fallback_gate"] == {"runs": 17, "passed": False}
    assert s["ml1_rod_fallback_runs"] == 17
    assert s["deferred_leg_below_F_min"] == {"flagged_runs": 1, "runs": ["a"]}
    assert len(s["failed"]) == 1 and s["flag_rows"]


@pytest.mark.skipif(not (C36 / "A_rt" / "episodes").is_dir(),
                    reason="C-S8-36 bundle A records not present")
def test_bundle_a_gate_lists_the_17_runs_of_spec_260_1(tmp_path) -> None:
    out = v.judge_ml_batch(C36 / "A_rt", tmp_path / "verify_S8ML.json")
    doc = json.loads(out.read_text(encoding="utf-8"))
    (gate,) = [r for r in doc["rows"] if r["item"].startswith("ML-0 no rod-pressure fallback")]
    assert gate["passed"] is False and set(gate["runs"]) == FALLBACK_17
    assert doc["meta"]["summary"]["ml1_rod_fallback_runs"] == 17
    assert "C-S8-41" in doc["meta"]["judge_revision"]


@pytest.mark.skipif(not (C36 / "D_fs24" / "MLJ_FS24_Fs0").is_dir(),
                    reason="C-S8-36 bundle D records not present")
def test_bundle_d_fs0_rr_deferred_minimum() -> None:
    d = C36 / "D_fs24" / "MLJ_FS24_Fs0"
    case, _m, _pr, params = v._load(d)
    rt = v._rt_of_case(case, d, f_min_N=float(params.control.F_min_cylinder_N))["rt"]
    (w,) = rt["deferred_min"]["windows"]
    assert w["leg"] == "RR" and w["deferred_s"] == [2.6] and w["next_start_s"] == 3.2
    # spec rev. 54 261 window (deferral .. next start + 0.3 s): 0.59 kN at event + 2.66 s;
    # the 6.97 kN of 261 / 257.2 is the later U-S8-32 window end .. re-READY minimum (+3.21 s)
    assert w["min_kN"] == pytest.approx(0.592, abs=0.01) and w["min_t_s"] == pytest.approx(
        2.663, abs=0.002)
    assert w["below_F_min"] is True and w["lift"] is False
