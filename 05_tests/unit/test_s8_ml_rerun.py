"""C-S8-25 / C-S8-26 (``s6_control_spec.md`` rev. 47 217.9, U-S8-27 / 29 / 30):
``ForcedRetract(others=...)`` (zero = RE1c bit-identical), restored-controller settings refresh,
forced window up to ``done``, FAULT / head-fault / pressure-step / lift rows of the ML judge."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.signals import Command
from outrigger_sim.verify import s8_control as s8

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))
import s6_stage2 as st  # noqa: E402


class _Inner:
    period_s = 0.1

    def __init__(self, rng) -> None:
        self.rng = rng

    def reset(self) -> None:
        pass

    def update(self, m):
        return Command(t_s=m.t_s, leg_speed_m_s=self.rng.normal(0.0, 5e-3, 4))

    def meta(self):
        return {}


@dataclass
class _Meas:
    t_s: float
    stroke_m: np.ndarray


class _OldForcedRetract:
    """``s6_stage2.ForcedRetract.update`` before C-S8-25 (verbatim logic)."""

    def __init__(self, inner, *, leg, depth_m, speed_m_s) -> None:
        self.inner, self.leg, self.depth_m, self.speed_m_s = inner, leg, depth_m, speed_m_s
        self.t_start = None
        self.s0 = None
        self.done = False

    def update(self, measurements):
        cmd = self.inner.update(measurements)
        if self.t_start is None or measurements.t_s < self.t_start:
            return cmd
        s = float(measurements.stroke_m[self.leg])
        if self.s0 is None:
            self.s0 = s
        u = np.zeros(4)
        if not self.done and self.s0 - s < self.depth_m:
            u[self.leg] = -self.speed_m_s
        else:
            self.done = True
        return Command(t_s=measurements.t_s, leg_speed_m_s=u)


def _strokes(n=200, seed=3):
    rng = np.random.default_rng(seed)
    s = 0.3 + np.cumsum(rng.normal(-5e-4, 1e-3, (n, 4)), axis=0)
    return [_Meas(0.1 * k, s[k]) for k in range(n)]


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_zero_mode_bit_identical_to_re1c(seed) -> None:
    meas = _strokes(seed=seed)
    new = st.ForcedRetract(_Inner(np.random.default_rng(seed)), leg=3, depth_m=0.02,
                           speed_m_s=5e-3)
    old = _OldForcedRetract(_Inner(np.random.default_rng(seed)), leg=3, depth_m=0.02,
                            speed_m_s=5e-3)
    new.t_start = old.t_start = 4.0
    for m in meas:
        a, b = new.update(m), old.update(m)
        assert a.t_s == b.t_s and np.array_equal(a.leg_speed_m_s, b.leg_speed_m_s)
    assert new.done == old.done and new.others == "zero"


def test_controller_mode_forced_leg_only_until_done() -> None:
    meas = _strokes(seed=5)
    inner_ref = _Inner(np.random.default_rng(5))
    fr = st.ForcedRetract(_Inner(np.random.default_rng(5)), leg=2, depth_m=0.01, speed_m_s=5e-3,
                          others="controller")
    fr.t_start = 2.0
    seen_done = False
    for m in meas:
        ref = inner_ref.update(m).leg_speed_m_s
        u = fr.update(m).leg_speed_m_s
        if m.t_s < 2.0 or fr.done:
            assert np.array_equal(u, ref)
            seen_done |= fr.done
        else:
            assert u[2] == -5e-3
            assert np.array_equal(np.delete(u, 2), np.delete(ref, 2))
    assert seen_done and fr.done_t_s is not None and fr.meta()["others"] == "controller"
    with pytest.raises(ValueError):
        st.ForcedRetract(_Inner(None), leg=0, depth_m=0.01, speed_m_s=1e-3, others="hold")


# --- settings refresh -----------------------------------------------------------------------


@dataclass(frozen=True)
class _Settings:
    a: float = 1.0
    step_rule: str = "explained"


@dataclass
class _RunState:
    x: int = 0


class _Monitor:
    __module__ = "outrigger_sim.fake"

    def __init__(self, settings, window) -> None:
        import collections

        self.settings = settings
        self.hist = collections.deque(maxlen=window)
        self.period_s = 0.1


class _Ctrl:
    __module__ = "outrigger_sim.fake"

    def __init__(self, settings, window) -> None:
        self.config = settings
        self._pressures = _Monitor(settings, window)
        self._state = _RunState()


def test_refresh_restored_controller() -> None:
    import run_S8C

    old = _Ctrl(_Settings(a=2.0, step_rule="plain"), 3)
    old._pressures.hist.extend([1, 2, 3])
    old._state.x = 7
    del old._pressures.period_s  # attribute of the new code missing after unpickling
    fresh = _Ctrl(_Settings(), 5)
    meta = run_S8C.refresh_restored_controller(old, fresh)
    assert old.config == _Settings() and old._pressures.settings == _Settings()
    assert {r["path"] for r in meta["replaced"]} == {"c2.config", "c2._pressures.settings"}
    assert meta["added"] == ["c2._pressures.period_s"] and old._pressures.period_s == 0.1
    assert old._pressures.hist.maxlen == 5 and list(old._pressures.hist) == [1, 2, 3]
    assert old._state.x == 7 and meta["scalar_differs"] == []


# --- judge helpers ----------------------------------------------------------------------------


def test_forced_window_controller_mode_ends_at_done() -> None:
    res = {"event_t_s": 61.0, "settings": {"start_t_s": 3.0, "episode": {"kind": "retract",
                                                                         "leg": "RL"}},
           "forced_retract": {"others": "controller", "done_t_s": 66.0}}
    fw = s8.forced_window(res, 89.0)
    assert fw["start_s"] == pytest.approx(58.0) and fw["end_s"] == pytest.approx(63.0)
    assert fw["done_s"] == pytest.approx(63.0) and fw["others"] == "controller"
    res["forced_retract"]["done_t_s"] = None
    assert s8.forced_window(res, 89.0)["end_s"] == 89.0
    old = {"event_t_s": 61.0, "settings": res["settings"]}
    assert s8.forced_window(old, 89.0)["end_s"] == 89.0


def test_named_events_and_lift_intervals() -> None:
    ev = [(61.4, "FAULT_HEAD_PRESSURE:FR"), (61.1, "INFO_PRESSURE_STEP:FR:rod:locked_rise"),
          (62.0, "WARN_ROD_PRESSURE_FALLBACK:FR")]
    hf = s8.named_events(ev, s8.HEAD_FAULT_EVENT)
    assert hf == [{"t_s": 61.4, "leg": "FR", "detail": None}]
    st_ = s8.named_events(ev, s8.PRESSURE_STEP_INFO)
    assert st_[0]["detail"] == "rod:locked_rise"
    t = np.arange(0.0, 3.0, 0.001)
    air = np.zeros((t.size, 4), bool)
    air[(t >= 1.0) & (t < 1.7), 1] = True
    air[(t >= 0.2) & (t < 0.4), 2] = True  # before the event: ignored
    air[t >= 2.9, 2] = True  # open at the record end
    li = s8.lift_intervals(t, air, 0.5)
    assert li["FL"] == [] and len(li["FR"]) == 1
    assert li["FR"][0][1] - li["FR"][0][0] == pytest.approx(0.7, abs=1e-9)
    assert len(li["RL"]) == 1 and li["RL"][0][1] == pytest.approx(3.0, abs=1e-6)


def test_ml_rows_fault_gate_head_fault_steps_and_lift() -> None:
    base = {"kind": "base", "ready_t_s": 30.0, "branched": True, "meta": None}
    ep5 = {"kind": "settle", "fault_entry_s": 61.4, "fault_injected": False,
           "head_faults": [{"t_s": 61.4, "leg": "FR", "detail": None}],
           "pressure_steps": [{"t_s": 61.1, "leg": "FR", "detail": "rod:x"}],
           "settings_refreshed": True,
           "first_period_compare": {"identical": True},
           "lift": {"deep_fast": True, "max_s": 27.0, "lifted_legs": ["FR", "RL"],
                    "diagonal": True, "longest_s": {"FL": 0.0, "FR": 27.0, "RL": 27.0,
                                                    "RR": 0.0},
                    "depth_m": 0.0239, "ramp_s": 0.305, "leg": "FR"}}
    ok = {"kind": "hold", "settings_refreshed": True,
          "first_period_compare": {"identical": False, "max_abs_command_diff_m_s": 1e-3}}
    rows = s8.ml_rows({"ML00": base, "ML00_ep5": ep5, "ML00_ep1": ok}, 1, 2)
    gate = next(r for r in rows if r["item"].startswith("ML-0 no FAULT entry"))
    assert gate["passed"] is False and gate["value"] == 1
    assert any(r["item"].startswith("ML-2 head-pressure fault") and r["case"] == "ML00_ep5"
               for r in rows)
    steps = next(r for r in rows if s8.PRESSURE_STEP_INFO in r["item"])
    assert steps["value"] == 1
    # C-S8-27 ①: U-S8-30 is one record row over every settlement episode with a lift
    lift = next(r for r in rows if r["item"].startswith("U-S8-30"))
    assert lift["value"] == {"episodes": 1, "over_flag": 1} and lift["kind"] == "record"
    cmp_ = next(r for r in rows if "1-period compare" in r["item"])
    assert cmp_["value"] == {"refreshed": 2, "compared": 2, "differ": 1}
