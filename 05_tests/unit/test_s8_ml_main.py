"""C-S8-27 ... 30 (``s6_control_spec.md`` rev. 48 218.13 / 218.15, U-S8-32 ... 35; pilot rejudge
expectations of rev. 49 / 50): event-leg /
adjacent-leg split of a settlement, ML mask (FAULT tail, no forced-window mask), forced-retract
record, main ML design (retract speed from a separate generator), the MLJ judged cases, the
lock-window valve lag and the rod-sensor fault wrapper."""

from __future__ import annotations

import dataclasses
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.verify import s8_control as s8

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))
PILOT = ROOT / "07_results" / "S8" / "ml_pilot_20261025_002044"


# --- settle_lift_split ------------------------------------------------------------------------


def _record(lifts, t_end=10.0, dt=1e-3):
    """1 ms record with ``lifts`` = {leg: [(start, end), ...]} airborne, ball z rises 1 mm per
    lift (adjacent) or 10 mm (event legs)."""
    t = np.arange(0.0, t_end, dt)
    air = np.zeros((t.size, 4), bool)
    z = np.zeros((t.size, 4))
    for leg, iv in lifts.items():
        j = s8.LEGS.index(leg)
        for a, b in iv:
            sel = (t >= a) & (t < b)
            air[sel, j] = True
            amp = 0.001 if leg in ("FL", "RR") else 0.010
            z[sel, j] = amp * (t[sel] - a) / (b - a - dt)  # rises to amp at the last sample
    return t, air, z


def test_front_settlement_split_passes() -> None:
    # FR settles at 2 s: event legs FR + RL, adjacent FL + RR
    t, air, z = _record({"RL": [(2.2, 3.0), (3.5, 3.8)], "FL": [(2.3, 2.5)], "RR": [(2.6, 2.7)]})
    sp = s8.settle_lift_split(t, air, z, 2.0, "FR", 0.0, 0.3, t3_s=0.82)
    assert sp["event_legs"] == ["FR", "RL"] and sp["adjacent_legs"] == ["FL", "RR"]
    assert sp["primary"] == "RL"
    assert sp["event_cum_max_s"] == pytest.approx(1.1, abs=2e-3)
    assert sp["event_recontact_max_rel_s"] == pytest.approx(1.8, abs=2e-3)
    assert sp["window_end_rel_s"] == pytest.approx(1.8 + 0.82, abs=2e-3)
    assert sp["adjacent_sum_s"] == pytest.approx(0.3, abs=2e-3)
    assert sp["adjacent_gap_max_m"] == pytest.approx(0.001, abs=1e-9)
    assert sp["u57_pass"] and sp["event_pass"]
    rows = s8.u_s8_32_rows("X", sp)
    assert [r["passed"] for r in rows] == [True, True] and rows[1]["kind"] == "judged"


def test_split_failures() -> None:
    # adjacent lift after the window, event leg lifted to the record end, FAULT
    t, air, z = _record({"RL": [(2.2, 10.0)], "FL": [(9.0, 9.2)]})
    sp = s8.settle_lift_split(t, air, z, 2.0, "FR", 0.0, 0.3, t3_s=0.82, fault_t_s=5.0)
    assert sp["event_recontact_max_rel_s"] is None and sp["window_capped"]
    assert sp["adjacent_outside_window_s"] == pytest.approx(0.2, abs=2e-3)
    assert not sp["u57_pass"] and not sp["event_pass"]
    # no event-leg lift: window = event + T3; an adjacent lift of 0.6 s fails U57
    t, air, z = _record({"FR": [(2.1, 2.7)]})
    sp = s8.settle_lift_split(t, air, z, 2.0, "RR", 0.0, 0.3, t3_s=0.82)
    assert sp["primary"] is None and sp["window_end_rel_s"] == pytest.approx(0.82)
    assert sp["event_legs"] == ["RR", "FL"] and sp["adjacent_legs"] == ["FR", "RL"]
    assert sp["adjacent_sum_s"] == pytest.approx(0.6, abs=2e-3)
    assert not sp["u57_pass"] and sp["event_pass"]
    # the same lift on FL (diagonal of RR) is an event-leg lift
    t, air, z = _record({"FL": [(2.1, 2.7)]})
    sp = s8.settle_lift_split(t, air, z, 2.0, "RR", 0.0, 0.3, t3_s=0.82)
    assert sp["primary"] == "FL" and sp["u57_pass"] and sp["event_pass"]


def test_gap_removes_the_ground_drop() -> None:
    # the settled leg follows the patch down: no gap
    t = np.arange(0.0, 4.0, 1e-3)
    air = np.zeros((t.size, 4), bool)
    air[(t >= 1.0) & (t < 1.5), 1] = True
    z = np.zeros((t.size, 4))
    z[:, 1] = -0.02 * s8.poly345((t - 1.0) / 0.3)
    sp = s8.settle_lift_split(t, air, z, 1.0, "FR", 0.02, 0.3, t3_s=0.82)
    assert abs(sp["event"]["FR"]["gap_max_m"]) < 1e-12


# --- mask / forced record -----------------------------------------------------------------------


def test_ml_episode_mask() -> None:
    fw_c = {"start_s": 58.0, "end_s": 60.0, "others": "controller"}
    fw_z = {"start_s": 58.0, "end_s": 89.0, "others": "zero"}
    assert s8.ml_episode_mask(fw_c, None, 89.0, 3.0) is None  # U-S8-34
    m = s8.ml_episode_mask(None, 62.0, 89.0, 3.0)
    assert (m["start_s"], m["end_s"], m["reasons"]) == (62.0, 89.0, ["fault"])
    assert m["start_engine_s"] == 65.0 and m["fault_t_s"] == 62.0
    m = s8.ml_episode_mask(fw_z, 62.0, 89.0, 3.0)
    assert m["start_s"] == 58.0 and set(m["reasons"]) == {"fault", "forced_hold_all_legs"}
    assert s8.ml_episode_mask(fw_c, 62.0, 89.0, 3.0)["reasons"] == ["fault"]


def test_forced_event_record() -> None:
    t = np.arange(0.0, 20.0, 1e-3)
    f = np.full((t.size, 4), 50e3)
    f[(t >= 5.0) & (t < 6.0), 2] = 5e3  # inside the window
    f[(t >= 9.5) & (t < 9.6), 0] = 8e3  # after the tail
    pads = {"t": t + 3.0, "F_cyl_min_interval": f, "airborne": np.zeros((t.size, 4), bool)}
    res = {"forced_retract": {"speed_m_s": 0.015},
           "settings": {"episode": {"depth_m": 0.02, "speed_fraction": 0.7}}}
    fw = {"start_s": 4.0, "end_s": 6.0, "leg": "RL", "done_s": 6.0, "others": "controller"}
    r = s8.forced_event_record(res, fw, pads, 3.0, 20.0, 9414.59)
    assert r["window_below_F_min"] and r["window_below_F_min_legs"] == ["RL"]
    assert not r["tail_below_F_min"] and r["after_below_F_min"]
    assert r["after_below_F_min_legs"] == ["FL"] and r["after_min_kN"] == pytest.approx(8.0)
    assert r["speed_fraction"] == 0.7 and not r["window_lift"]


def test_ml_rows_u_s8_32_and_fault_reason() -> None:
    t, air, z = _record({"RL": [(2.2, 3.0)], "FL": [(2.3, 2.5)]})
    sp = s8.settle_lift_split(t, air, z, 2.0, "FR", 0.024, 0.3, t3_s=0.82)
    ep = {"kind": "settle", "fault_entry_s": 3.0, "fault_injected": False,
          "head_faults": [{"t_s": 3.0, "leg": "FR", "detail": None}],
          "head_fault_reasons": [{"t_s": 3.0, "leg": "FR", "detail": "D1 step"}],
          "lift": {"lifted_legs": ["RL", "FL"], "max_s": 0.8}, "u_s8_32": sp,
          "step_rule": "explained_imu"}
    rows = s8.ml_rows({"ML00_ep5": ep}, None, None)
    gate = next(r for r in rows if r["item"].startswith("ML-0 no FAULT"))
    assert gate["fault"]["ML00_ep5"]["reasons"] == [("FR", 3.0, "D1 step")]
    rep = next(r for r in rows if r["item"].startswith("ML-2 head-pressure"))
    assert "D1 step" in rep["note"]
    adj = next(r for r in rows if r["item"].startswith("U-S8-32 adjacent"))
    ev = next(r for r in rows if r["item"].startswith("U-S8-32 event"))
    assert adj["passed"] is True and ev["passed"] is True  # sp computed without the FAULT
    rule = next(r for r in rows if r["item"].startswith("ML-0 D1 step rule"))
    assert rule["value"] == {"explained_imu": 1}


@pytest.mark.skipif(not (PILOT / "ml_plan.json").exists(), reason="ML pilot batch not present")
def test_pilot_rejudge_matches_rev50(tmp_path: Path) -> None:
    """C-S8-27 / 28 / 33 test (spec rev. 49 219.3 / 219.9, rev. 50 220.6): after the C-S8-28
    rerun of the head-step episodes the pilot has no FAULT episode, so with the U-S8-37 gate
    (last re-contact <= event + 3.0 s) the event-leg failures are 0 and no ML mask is left;
    adjacent U57 failures 0 (worst ML00_ep5 0.374 s / 1.57 mm), 37 rows each, the latest
    event-leg re-contact is ML00_ep5 2.438 s (219.3 prediction, inside the 3.0 s gate and the
    2.5 s flag column)."""
    out = s8.judge_ml_batch(PILOT, tmp_path / "v.json")
    import json

    doc = json.loads(out.read_text(encoding="utf-8"))
    assert "spec rev. 50" in doc["meta"]["judge_revision"]  # rev. 51 (C-S8-34) builds on it
    adj = [r for r in doc["rows"] if r["item"].startswith("U-S8-32 adjacent")]
    ev = [r for r in doc["rows"] if r["item"].startswith("U-S8-32 event")]
    assert len(adj) == 37 and len(ev) == 37
    assert all(r["passed"] for r in adj)
    worst = max(adj, key=lambda r: r["value"][0])
    assert worst["case"] == "ML00_ep5" and worst["value"][:2] == [0.374, 1.57]
    assert [r["case"] for r in ev if r["passed"] is False] == []
    latest = max((r for r in ev if r["value"][1] is not None), key=lambda r: r["value"][1])
    assert latest["case"] == "ML00_ep5" and latest["value"][1] == pytest.approx(2.438, abs=1e-3)
    assert latest["value"][3] is True  # within the 2.5 s nominal-damping flag column
    assert doc["ml_masks"] == {}
    assert doc["meta"]["failed"] == 0


# --- runner (run_S8C) ------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def run_s8c():
    import run_S8C

    return run_S8C


def test_ml_design_main_keeps_the_pilot_draws(run_s8c) -> None:
    bases = run_s8c.ml_bases(run_s8c.ML_MAIN_BASES)
    assert [b.base_id for b in bases[:24]] == [b.base_id for b in run_s8c.ml_bases()]
    assert bases[:24] == run_s8c.ml_bases()
    speeds = []
    for b in bases:
        pilot = run_s8c.ml_episodes(b)
        main = run_s8c.ml_episodes(b, design="main")
        for p, m in zip(pilot, main, strict=True):
            extra = {k: v for k, v in m.items() if k not in p}
            assert {k: m[k] for k in p} == p
            if m["kind"] == "retract":
                assert set(extra) == {"speed_fraction"}
                speeds.append(extra["speed_fraction"])
            else:
                assert extra == {}
            assert "speed_fraction" not in p
    assert len(speeds) > 100 and 0.5 <= min(speeds) and max(speeds) <= 1.0
    with pytest.raises(ValueError):
        run_s8c.ml_episodes(bases[0], design="other")


def test_mlj_cases_and_end_rule(run_s8c) -> None:
    cases = run_s8c.case_set("mlj")
    assert sorted(c.case_id for c in cases) == sorted(
        f"MLJ_{n}_Fs{fs}" for n in ("FS24", "SS9P", "K0V_fdown3.5_G4RF") for fs in (0, 8))
    by = {c.case_id: c for c in cases}
    assert run_s8c.end_rule(by["MLJ_SS9P_Fs0"])["after_s"] == 60.0
    assert run_s8c.end_rule(by["MLJ_FS24_Fs8"])["after_s"] == 45.0
    fs = by["MLJ_FS24_Fs8"].event_spec()
    assert (fs["leg"], fs["depth_m"], fs["ramp_s"], fs["fine"]) == ("FR", 0.024, 0.3, True)
    assert by["MLJ_FS24_Fs0"].fine_s() == 10.0
    assert by["MLJ_K0V_fdown3.5_G4RF_Fs0"].floor == "fdown3.5"
    assert by["MLJ_K0V_fdown3.5_G4RF_Fs0"].event_spec()["rod_fault"]["leg"] == "FR"
    # existing cases unchanged
    tab = run_s8c.case_table()
    assert run_s8c.end_rule(tab["E_G4_Fs0"])["after_s"] == 45.0
    assert tab["E_RE1bF_Fs0"].fine_s() == 10.0
    assert [c.case_id for c in run_s8c.case_set("mlj_c29")] == [
        "MLJ_K0V_fdown3.5_G4RF_Fs0", "MLJ_K0V_fdown3.5_G4RF_Fs8"]


def test_lock_window_tau(run_s8c) -> None:
    from outrigger_sim.control.c2 import C2Config

    cfg = C2Config().with_10hz_d1()
    key = run_s8c.LOCK_WINDOW_TAU_KEY
    if key not in {f.name for f in dataclasses.fields(cfg.two_pressure)}:
        pytest.skip("TwoPressureSettings without lock_window_valve_tau_s")
    default = getattr(cfg.two_pressure, key)
    assert run_s8c.with_lock_window_tau(cfg, default) is cfg  # bit-identical path
    new = run_s8c.with_lock_window_tau(cfg, 0.05)
    assert getattr(new.two_pressure, key) == 0.05
    assert dataclasses.replace(new.two_pressure, **{key: default}) == cfg.two_pressure


@dataclass
class _M:
    t_s: float
    rod_pressure_Pa: np.ndarray | None


class _Inner:
    period_s = 0.1

    def __init__(self) -> None:
        self.seen = []

    def update(self, m):
        self.seen.append(m)
        return "cmd"

    def reset(self) -> None:
        pass

    def meta(self):
        return {}


def test_rod_fault_injection(run_s8c) -> None:
    inner = _Inner()
    w = run_s8c.RodFaultInjection(inner, leg=1, fault="dropout")
    rod = np.array([1e5, 2e5, 3e5, 4e5])
    w.update(_M(1.0, rod))
    w.arm(2.0)
    w.update(_M(1.9, rod))
    w.update(_M(2.0, rod))
    w.update(_M(2.1, None))
    assert np.array_equal(inner.seen[0].rod_pressure_Pa, rod)
    assert np.array_equal(inner.seen[1].rod_pressure_Pa, rod)
    got = inner.seen[2].rod_pressure_Pa
    assert math.isnan(got[1]) and np.array_equal(np.delete(got, 1), np.delete(rod, 1))
    meta = w.meta()
    assert meta["applied_periods"] == 1 and meta["periods_without_rod_reading"] == 1
    assert meta["leg"] == "FR" and meta["fault"] == "dropout" and w.period_s == 0.1


def test_refresh_records_lock_window_tau(run_s8c) -> None:
    @dataclass(frozen=True)
    class _TP:
        lock_window_valve_tau_s: float = 0.1

    class _Mon:
        __module__ = "outrigger_sim.fake"

        def __init__(self, tau) -> None:
            self.settings = _TP(tau)

    class _Ctrl:
        __module__ = "outrigger_sim.fake"

        def __init__(self, tau) -> None:
            self._pressures = _Mon(tau)

    old, fresh = _Ctrl(0.1), _Ctrl(0.05)
    meta = run_s8c.refresh_restored_controller(old, fresh)
    assert old._pressures.settings.lock_window_valve_tau_s == 0.05
    assert meta["lock_window_valve_tau_s"] == 0.05
    assert meta["lock_window_valve_tau_s_fresh"] == 0.05


def test_ml_plan_main(run_s8c) -> None:
    p = run_s8c.ml_plan("main")
    assert (p["bases"], p["episodes"], len(p["judged_cases"])) == (96, 768, 6)
    assert sum(p["episodes_by_kind"].values()) == 768
    assert 0.5 <= p["retract_speed_fraction"]["min"] <= p["retract_speed_fraction"]["max"] <= 1.0
    pilot = run_s8c.ml_plan("pilot")
    assert pilot["episodes_by_kind"]["settle"] == 86  # spec rev. 48 218.5: 86 settlements
    assert pilot["makespan"]["p7e8"]["calibrated_total_s"] == pytest.approx(
        sum(run_s8c.ML_PILOT_MEASURED_S.values()))
