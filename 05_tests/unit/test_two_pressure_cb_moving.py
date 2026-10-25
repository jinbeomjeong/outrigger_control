"""P-S8-15 CB moving fallback estimate of ``control/two_pressure`` (hydraulics H-S8-3,
``00_docs/02_hydraulic/s8_seal_friction_counterbalance.md`` 11.2 ①-⑥, tests (a)-(d)).

(b) Synthetic: a 1 ms plant with the CB law behind the rod-side lag ``tau_cb`` 0.05 s and the
spool lag ``tau_v`` 0.1 s, read every 0.1 s (head step +13 bar in 60 ms, a head dip
between two samples, a command reversal). (c) The pilot-check path and the ``fixed`` rule do
not depend on the CB moving rule. (d) Settings and monitors pickled before P-S8-15.
(a) Record replays of the two CB batches (``07_results/S8``, git-ignored; skipped without
them): every leg forced to fallback from the start, the lower bound of every moving sample
against the true pressure force (the inputs of ``h_s8_3_cb_moving_rules.py``: ``record.npz``
``meas.*``, ``issued_u`` one period late, ``pads.npz`` truth at the sample instant).
"""

from __future__ import annotations

import copy
import json
import math
import pickle
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from outrigger_sim.control.two_pressure import (
    CbMovingRule,
    CounterbalanceRodModel,
    LoadEstimate,
    RodSensorState,
    TwoPressureMonitor,
    TwoPressureSettings,
)
from outrigger_sim.params import load_params

BAR = 1e5
PERIOD_S = 0.1
STEP_S = 1e-3
HEAD_AREA = np.array([1.3273229e-2, 1.3273229e-2, 9.50331778e-3, 9.50331778e-3])
ANNULUS = np.array([3.76991118e-3, 3.76991118e-3, 3.14159265e-3, 3.14159265e-3])
V_MAX = 0.020924
F_MIN_N = 9414.59
CB_PARAMS = load_params(level="top", model="L2b_NSC").l2b.counterbalance
CB_LAG_TAU_S = 0.05
VALVE_TAU_S = 0.1
OPTIMISM_LIMIT_N = 600.0
"""11.2 test (a): the lower bound may lie at most 0.6 kN above the true force."""
RR = 3


def _cb_settings(**changes) -> TwoPressureSettings:
    settings = TwoPressureSettings().with_r8_period().with_lock_valve("counterbalance", CB_PARAMS)
    return replace(settings, **changes)


def _monitor(settings: TwoPressureSettings) -> TwoPressureMonitor:
    return TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN_N, PERIOD_S, settings=settings,
                              stroke_max_m=0.70, counterbalance_lag_tau_s=CB_LAG_TAU_S)


# --- (b) synthetic plant -----------------------------------------------------------------------


@dataclass(frozen=True)
class Scenario:
    """Head reading path [bar] and per-period applied commands [m/s] of one leg."""

    head_bar: object
    commands_m_s: tuple[float, ...]


def _cb_target_Pa(law: CounterbalanceRodModel, spool_m_s: float, head_Pa: float) -> float:
    if spool_m_s >= 0.0:
        return law.extend_rod_pressure_Pa(head_Pa)
    return law.retract_rod_pressure_Pa(head_Pa)


def _simulate(scenario: Scenario, settings: TwoPressureSettings):
    """1 ms plant (spool lag ``tau_v``, rod side behind the CB target with ``tau_cb``), the
    monitor read at every 0.1 s sample with leg RR fallen back. Returns per sample (true rod
    pressure, ``p_r_hat``) for the samples with a non-zero command."""
    law = CounterbalanceRodModel.from_params(CB_PARAMS)
    monitor = _monitor(settings)
    monitor.rod_state[RR] = RodSensorState.FALLBACK
    spool = scenario.commands_m_s[0]
    rod_Pa = _cb_target_Pa(law, spool, scenario.head_bar(0.0) * BAR)
    steps_per_period = round(PERIOD_S / STEP_S)
    rows = []
    for k, command in enumerate(scenario.commands_m_s):
        for j in range(1, steps_per_period + 1):
            t_s = k * PERIOD_S + j * STEP_S
            spool += STEP_S / VALVE_TAU_S * (command - spool)
            target_Pa = _cb_target_Pa(law, spool, scenario.head_bar(t_s) * BAR)
            rod_Pa += STEP_S / CB_LAG_TAU_S * (target_Pa - rod_Pa)
        t_s = (k + 1) * PERIOD_S
        head = np.full(4, scenario.head_bar(t_s) * BAR)
        commanded = np.full(4, command)
        monitor.read(t_s, head, np.full(4, rod_Pa), commanded, False, 2e3,
                     stroke_m=np.full(4, 0.3))
        if command != 0.0:
            rows.append((rod_Pa, monitor._legs[RR].rod_estimate_Pa))
    return np.array(rows)


def _ramp(t_s, start_s, duration_s, low, high):
    return low + (high - low) * min(max((t_s - start_s) / duration_s, 0.0), 1.0)


EXTEND_SLOW = 0.2 * V_MAX
SCENARIOS = {
    # CB_H4V RR 26.0 s: the air extension ends on the floor, the head rises 13 bar in 60 ms.
    "head_step": Scenario(lambda t: _ramp(t, 2.03, 0.06, 45.8, 59.2), (EXTEND_SLOW,) * 40),
    # RE1bF rocking: the head dips 20 bar between two samples and is back at the sample.
    "head_trough": Scenario(
        lambda t: 60.0 - 20.0 * max(0.0, 1.0 - abs(t - 2.05) / 0.03), (EXTEND_SLOW,) * 40),
    # RE1bF FL 52.6 s: retraction commanded while the spool still extends.
    "reversal": Scenario(lambda t: 60.0, (EXTEND_SLOW,) * 20 + (-EXTEND_SLOW,) * 20),
}


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_lag_bound_covers_the_lagged_rod_side(name) -> None:
    """11.2 (b): ``p_r_hat >= p_r,true`` on every moving sample (no sensor error here, so the
    sensor share of the margin is spare)."""
    rows = _simulate(SCENARIOS[name], _cb_settings())
    truth, estimate = rows[:, 0], rows[:, 1]
    assert np.all(estimate >= truth)


@pytest.mark.parametrize("name", ["head_step", "reversal"])
def test_cb_law_estimate_misses_the_same_cases(name) -> None:
    """The 9.6 law (before P-S8-15) is optimistic beyond its 11.4 bar margin (11.1)."""
    rows = _simulate(SCENARIOS[name], _cb_settings().with_cb_law_estimate())
    assert np.max(rows[:, 0] - rows[:, 1]) > 5 * BAR


def test_first_moving_sample_starts_from_the_locked_bound() -> None:
    """② After a command-free stretch the first moving ``Y`` decays from the last ``p_r_hat``:
    ``Y = max(L, a p_hat + (1 - a) max(L_prev, L))`` with both laws (start = uncertain)."""
    settings = _cb_settings()
    monitor = _monitor(settings)
    head, rod, stroke = np.full(4, 60 * BAR), np.full(4, 120 * BAR), np.full(4, 0.3)
    for k in range(5):
        monitor.read(k * PERIOD_S, head, rod, np.zeros(4), False, 2e3, stroke_m=stroke)
    locked_Pa = monitor._legs[RR].rod_estimate_Pa
    monitor.read(0.5, head, rod, np.full(4, EXTEND_SLOW), False, 2e3, stroke_m=stroke)
    law = settings.counterbalance
    extend_Pa, retract_Pa = law.extend_rod_pressure_Pa(60 * BAR), law.retract_rod_pressure_Pa(
        60 * BAR)
    larger_Pa = max(extend_Pa, retract_Pa)
    margin_Pa = max(settings.counterbalance_extend_estimate_margin_Pa,
                    settings.counterbalance_retract_estimate_margin_Pa)
    decay = math.exp(-PERIOD_S / CB_LAG_TAU_S)
    expected = max(larger_Pa, decay * locked_Pa + (1 - decay) * larger_Pa) + margin_Pa
    assert monitor._legs[RR].rod_estimate_Pa == pytest.approx(expected, rel=1e-12)


def test_lock_start_values_of_moving_samples_are_the_lag_bound() -> None:
    """⑤: the lookback start ``M_j`` of a moving sample is ``Y_j + m`` (the moving estimate)."""
    monitor = _monitor(_cb_settings())
    head, stroke = np.full(4, 60 * BAR), np.full(4, 0.3)
    for k in range(6):
        monitor.read(k * PERIOD_S, head, np.full(4, 30 * BAR), np.full(4, EXTEND_SLOW), False,
                     2e3, stroke_m=stroke)
        stretch = monitor._lock_stretches[RR]
        assert stretch.moving_starts[-1][1] == monitor._legs[RR].rod_estimate_Pa


def test_settings_defaults_and_meta() -> None:
    settings = _cb_settings()
    assert settings.counterbalance_moving_rule is CbMovingRule.LAG_BOUND
    assert settings.counterbalance_extend_estimate_margin_Pa == pytest.approx(23.4 * BAR)
    assert settings.counterbalance_retract_estimate_margin_Pa == pytest.approx(1.2 * BAR)
    meta = settings.to_meta()
    assert meta["counterbalance_moving_rule"] == "lag_bound"
    assert meta["counterbalance_lag_tau_s"] is None
    pilot = TwoPressureSettings().to_meta()
    assert "counterbalance_moving_rule" not in pilot and "counterbalance_lag_tau_s" not in pilot
    law = settings.with_cb_law_estimate()
    assert law.counterbalance_moving_rule is CbMovingRule.LAW
    assert law.counterbalance_extend_estimate_margin_Pa == pytest.approx(11.4 * BAR)
    assert _monitor(settings).meta()["counterbalance_lag_tau_s_used"] == CB_LAG_TAU_S
    explicit = _monitor(replace(settings, counterbalance_lag_tau_s=0.2))
    assert explicit._cb_lag_tau_s == 0.2
    json.dumps(_monitor(settings).meta())


# --- (c) pilot-check path and the fixed rule -----------------------------------------------------


def _random_replay(settings: TwoPressureSettings, seed: int = 11, count: int = 300):
    """Readings of every leg fallen back from sample 20 on random commands and pressures."""
    rng = np.random.default_rng(seed)
    commands = rng.choice([-0.5 * V_MAX, 0.0, 0.0, 0.3 * V_MAX, 0.05 * V_MAX], size=(count, 4))
    commands = np.repeat(commands[::5], 5, axis=0)[:count]
    head = 40 * BAR + 80 * BAR * rng.random((count, 4))
    rod = 3 * BAR + 60 * BAR * rng.random((count, 4))
    monitor = _monitor(replace(settings, diagnostics=False))
    out = []
    for k in range(count):
        if k == 20:
            monitor.rod_state = [RodSensorState.FALLBACK] * 4
        forces = monitor.read(k * PERIOD_S, head[k], rod[k], commands[k], False, 2e3,
                              stroke_m=np.full(4, 0.3))
        out.append(np.stack([forces.nominal, forces.lower, forces.upper]))
    return np.array(out)


@pytest.mark.parametrize("locked_ratio_rule", ["column_bound", "fixed"])
def test_pilot_check_does_not_depend_on_the_cb_moving_rule(locked_ratio_rule) -> None:
    settings = replace(TwoPressureSettings().with_r8_period(), locked_ratio_rule=locked_ratio_rule)
    law = replace(settings, counterbalance_moving_rule="law")
    np.testing.assert_array_equal(_random_replay(settings), _random_replay(law))


def test_fixed_rule_with_the_counterbalance_keeps_the_cb_law() -> None:
    """The ``fixed`` rule (regression before P-S8-13) does not use the lag bound."""
    settings = _cb_settings(locked_ratio_rule="fixed")
    law = replace(settings, counterbalance_moving_rule="law")
    np.testing.assert_array_equal(_random_replay(settings), _random_replay(law))


def test_cb_lag_bound_is_never_below_the_cb_law() -> None:
    """``Y_k >= L_k``: with the same margins the lag bound never lowers the lower-bound
    reading's deduction, i.e. ``lower(lag_bound) <= lower(law)`` on every sample."""
    law_settings = _cb_settings().with_cb_law_estimate()
    lag_settings = replace(law_settings, counterbalance_moving_rule="lag_bound")
    lag, law = _random_replay(lag_settings), _random_replay(law_settings)
    assert np.all(lag[:, 1] <= law[:, 1] + 1e-6)


# --- (d) pickles written before P-S8-15 -------------------------------------------------------


def test_settings_pickled_before_p_s8_15_read_the_lag_bound() -> None:
    settings = _cb_settings()
    state = dict(settings.__dict__)
    del state["counterbalance_moving_rule"], state["counterbalance_lag_tau_s"]
    state["counterbalance_extend_estimate_margin_Pa"] = 11.4 * BAR  # what an old run stored
    old = object.__new__(TwoPressureSettings)
    old.__dict__.update(state)
    restored = pickle.loads(pickle.dumps(old))
    assert restored.counterbalance_moving_rule is CbMovingRule.LAG_BOUND
    assert restored.counterbalance_lag_tau_s is None
    json.dumps(restored.to_meta())


def test_monitor_pickled_before_p_s8_15_runs_the_lag_bound() -> None:
    new = _monitor(_cb_settings())
    head, stroke = np.full(4, 60 * BAR), np.full(4, 0.3)
    for k in range(3):
        new.read(k * PERIOD_S, head, np.full(4, 30 * BAR), np.zeros(4), False, 2e3,
                 stroke_m=stroke)
    old = copy.deepcopy(new)
    del old.__dict__["_cb_lag_tau_s"]
    for stretch in old._lock_stretches:
        for name in ("recent_commands_m_s", "previous_head_Pa", "lag_bound_Pa", "lag_law_Pa"):
            del stretch.__dict__[name]
    restored = pickle.loads(pickle.dumps(old))
    assert restored._cb_lag_tau_s == pytest.approx(0.05)
    restored.rod_state[RR] = RodSensorState.FALLBACK
    for k in range(3, 8):
        restored.read(k * PERIOD_S, head, np.full(4, 30 * BAR), np.full(4, EXTEND_SLOW), False,
                      2e3, stroke_m=stroke)
    assert math.isfinite(restored._legs[RR].rod_estimate_Pa)
    json.dumps(restored.meta())


# --- (a) record replays (07_results/S8, git-ignored) --------------------------------------------

RESULTS = Path(__file__).resolve().parents[2] / "07_results" / "S8"
CB_BATCHES = (RESULTS / "cb_20261025_000840", RESULTS / "cb_20261025_013946")
CB_CASES = sorted(case.parent for batch in CB_BATCHES if batch.is_dir()
                  for case in batch.glob("*/pads.npz"))
LEG_NAMES = ("FL", "FR", "RL", "RR")
NAMED_SAMPLES = (
    ("CB_H4V_fdown3.5_Fs0", "RR", (26.0, 26.4, 26.5)),
    ("CB_RE1bF_Fs0", "FL", (52.1, 52.2, 52.3, 52.4, 52.5, 52.6, 52.7)),
    ("CB_RE1bF_Fs0", "RR", (52.5,)),
)
"""11.2 test (a): the samples named by the hydraulics analysis."""


def _case_settings(case: Path) -> TwoPressureSettings:
    meta = json.loads((case / "record" / "meta.json").read_text(encoding="utf-8"))
    s8 = meta["run"]["engine"]["actuator"]["s8"]
    params = SimpleNamespace(**s8["counterbalance"]["params"])
    return TwoPressureSettings().with_r8_period().with_lock_valve("counterbalance", params)


def forced_fallback_moving_errors(case: Path, settings: TwoPressureSettings):
    """``lower - F_true`` [N] per (sample, leg) with every leg fallen back from the start;
    NaN where the applied command is zero. Returns (t, errors)."""
    result = json.loads((case / "result.json").read_text(encoding="utf-8"))
    controller = result["controller_meta"]
    meta = controller["two_pressure"]
    run_meta = json.loads((case / "record" / "meta.json").read_text(encoding="utf-8"))
    tau_cb_s = float(run_meta["run"]["engine"]["actuator"]["rod_side"]["release_tau_s"])
    monitor = TwoPressureMonitor(
        meta["head_area_m2"], meta["annulus_area_m2"], controller["geometry"]["max_speed_m_s"],
        controller["geometry"]["F_min_N"], controller["period_s"],
        LoadEstimate(meta["load_estimate"]), settings, meta["rod_weight_N"],
        stroke_max_m=controller["geometry"]["stroke_max_m"], counterbalance_lag_tau_s=tau_cb_s)
    monitor.rod_state = [RodSensorState.FALLBACK] * 4
    with np.load(case / "r8_series.npz") as r8:
        t, issued, phase, band = r8["t"], r8["issued_u"], r8["phase"], r8["F_band_N"]
    with np.load(case / "record" / "record.npz") as record:
        index = np.clip(np.searchsorted(record["t"], t - 1e-9), 0, record["t"].size - 1)
        head = record["meas.head_pressure"][index]
        rod = record["meas.rod_pressure"][index]
        stroke = record["meas.stroke"][index]
    with np.load(case / "pads.npz") as pads:
        index = np.clip(np.searchsorted(pads["t"], t - 1e-9), 0, pads["t"].size - 1)
        f_true = pads["F_pressure"][index]
    commanded = np.vstack([np.zeros((1, 4)), issued[:-1]])
    calibration = controller.get("zero_calibration") or {}
    end_s = (calibration.get("result") or {}).get("t_end_s")
    if end_s is None:
        monitor.set_zero_offsets_N(meta["zero_offsets_N"])
    errors = np.full((t.size, 4), np.nan)
    for k in range(t.size):
        is_locked = bool(k) and str(phase[k - 1]).lower() == "ready"
        bands = monitor.leg_seal_bands_N(band[k - 1] if k else band[0])
        forces = monitor.read(t[k], head[k], rod[k], commanded[k], is_locked, bands,
                              stroke_m=stroke[k])
        moving = commanded[k] != 0.0
        errors[k, moving] = forces.lower[moving] - f_true[k, moving]
        if end_s is not None and t[k] >= end_s - 1e-9 and not monitor.zero_offsets_N.any():
            monitor.set_zero_offsets_N(calibration["offsets_N"])
    return t, errors


@pytest.mark.skipif(len(CB_CASES) != 12, reason="07_results/S8 CB batches not present")
def test_cb_record_moving_samples_are_never_optimistic() -> None:
    """11.2 (a): 12 runs, every leg, every moving sample: ``lower <= F_true + 0.6 kN``; the
    named samples are among them; the 9.6 law fails the same replay."""
    sample_count, worst_N = 0, -math.inf
    law_worst_N = -math.inf
    named = {}
    for case in CB_CASES:
        settings = _case_settings(case)
        t, errors = forced_fallback_moving_errors(case, settings)
        sample_count += int(np.isfinite(errors).sum())
        worst_N = max(worst_N, float(np.nanmax(errors)))
        _, law_errors = forced_fallback_moving_errors(case, settings.with_cb_law_estimate())
        law_worst_N = max(law_worst_N, float(np.nanmax(law_errors)))
        for name, leg, times in NAMED_SAMPLES:
            if case.name != name:
                continue
            for time_s in times:
                k = int(np.argmin(np.abs(t - time_s)))
                named[(case.parent.name, name, leg, time_s)] = errors[k, LEG_NAMES.index(leg)]
    assert sample_count == 22800
    assert worst_N <= OPTIMISM_LIMIT_N
    assert law_worst_N > 20e3  # 26.2 kN at CB_RE1bF_Fs0 FL 52.6 s (11.1)
    assert len(named) == 2 * 11
    assert all(math.isnan(error) or error <= OPTIMISM_LIMIT_N for error in named.values())
