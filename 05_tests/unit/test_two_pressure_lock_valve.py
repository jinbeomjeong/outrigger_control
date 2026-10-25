"""``control/two_pressure`` with the lock valve of the run (P-S8-11, U-S8-23, control spec
rev. 46 216.10; hydraulics H-S8-1, ``s8_seal_friction_counterbalance.md`` 9.5 / 9.6): the
counterbalance (CB) D2 upper bound, the CB fallback estimate, the measured-stroke check of
D2 / D3, the pilot-check path unchanged, and monitors pickled before P-S8-11 (ML
``branch.pkl``).

The record replays at the end use ``07_results/S8`` (git-ignored) and are skipped without it.
"""

from __future__ import annotations

import copy
import json
import pickle
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.control.c2 import C2Config
from outrigger_sim.control.two_pressure import (
    CounterbalanceRodModel,
    LoadEstimate,
    LockValve,
    TwoPressureMonitor,
    TwoPressureSettings,
)
from outrigger_sim.hydraulics.counterbalance import cb_rod_pressure_Pa
from outrigger_sim.hydraulics.rod_chamber import RodChamberMode
from outrigger_sim.params import load_params
from outrigger_sim.signals import Measurements

BAR = 1e5
PERIOD_S = 0.1
HEAD_AREA = np.array([1.3273e-2, 1.3273e-2, 9.5033e-3, 9.5033e-3])
ANNULUS = np.array([3.7699e-3, 3.7699e-3, 3.1416e-3, 3.1416e-3])
V_MAX = 0.020924
F_MIN = load_params().control.F_min_cylinder_N
CB_PARAMS = load_params(level="top", model="L2b_NSC").l2b.counterbalance
EXTEND = np.full(4, 0.5 * V_MAX)
STILL = np.zeros(4)
MOVING_LOAD_N = np.array([118e3, 118e3, 60e3, 60e3])
"""Rear legs below their static 72 kN: the CB regulates the rear rod side to about 33 bar."""
GRAVITY_M_S2 = 9.80665

RESULTS = Path(__file__).resolve().parents[2] / "07_results" / "S8"
CB_CASES = [RESULTS / "cb_20261025_000840" / name for name in ("CB_G4_Fs0", "CB_RE1bF_Fs0")]
PILOT_CASE = RESULTS / "p1r_20261024_222013" / "E_G4_Fs0"
ROLL_CASE = RESULTS / "p1r_20261024_222013" / "K0V_top_roll5.5_Fs0"
ML_BRANCH = RESULTS / "ml_pilot_20261025_002044" / "bases" / "ML04" / "branch.pkl"


def _cb_settings(**changes) -> TwoPressureSettings:
    settings = TwoPressureSettings().with_r8_period().with_lock_valve("counterbalance", CB_PARAMS)
    return replace(settings, **changes)


def _monitor(settings: TwoPressureSettings) -> TwoPressureMonitor:
    return TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN, PERIOD_S, settings=settings)


def _cb_extend_pressures(load_N=MOVING_LOAD_N, rod_offset_bar=0.0):
    """Head and rod pressures of extending legs whose rod side the CB regulates (spec 4.3):
    ``p_r = max(p_back, p_set - psi p_h)`` and ``p_h A_p - p_r A_ann = F``."""
    law = CounterbalanceRodModel.from_params(CB_PARAMS)
    regulated_head = (load_N + law.p_set_Pa * ANNULUS) / (HEAD_AREA + law.pilot_ratio * ANNULUS)
    rod = np.array([law.extend_rod_pressure_Pa(p_h) for p_h in regulated_head])
    head = (load_N + rod * ANNULUS) / HEAD_AREA
    return head, rod + rod_offset_bar * BAR


def _run(monitor, seconds, head, rod, command, start_s=0.0, stroke_rate_m_s=None):
    """Read for ``seconds``; the measured stroke follows the command unless
    ``stroke_rate_m_s`` is given (0 = a leg that does not move)."""
    rate = command if stroke_rate_m_s is None else stroke_rate_m_s
    stroke = np.full(4, 0.2)
    for k in range(round(seconds / PERIOD_S)):
        stroke = stroke + rate * PERIOD_S
        monitor.read(start_s + k * PERIOD_S, head, rod, command, False, 2e3, stroke_m=stroke)


def test_cb_law_in_head_pressure_equals_the_hydraulics_force_form() -> None:
    """Spec 4.3 with ``F_p = p_h A_p - p_r A_ann``: extend ``max(p_back, p_set - psi p_h)``,
    retract ``(p_set - p_h) / psi`` (the plant's ``cb_rod_pressure_Pa``)."""
    law = CounterbalanceRodModel.from_params(CB_PARAMS)
    for leg in (0, 2):
        for head_bar in (40.0, 74.0, 80.0, 150.0):
            head = head_bar * BAR
            for mode, mine in ((RodChamberMode.EXT, law.extend_rod_pressure_Pa),
                               (RodChamberMode.RET, law.retract_rod_pressure_Pa)):
                rod = mine(head)
                force = head * HEAD_AREA[leg] - rod * ANNULUS[leg]
                plant = cb_rod_pressure_Pa(mode, force, HEAD_AREA[leg], ANNULUS[leg],
                                           CB_PARAMS.p_set_Pa, CB_PARAMS.pilot_ratio,
                                           CB_PARAMS.back_pressure_Pa, -1e5, 400e5)
                assert plant == pytest.approx(rod, rel=1e-9, abs=1.0)


def test_cb_regulated_rod_side_is_no_d2_fault_with_the_counterbalance_setting() -> None:
    """216.5: rear rod side 33 bar while extending is the CB law; the pilot-check D2 range
    (<= 12 bar) falls the rear legs back, the CB setting does not."""
    head, rod = _cb_extend_pressures()
    assert rod[2] > 30 * BAR and rod[0] == pytest.approx(CB_PARAMS.back_pressure_Pa)
    pilot = _monitor(TwoPressureSettings().with_r8_period())
    _run(pilot, 3.0, head, rod, EXTEND)
    assert pilot.fallback_legs == [2, 3]
    counterbalance = _monitor(_cb_settings())
    _run(counterbalance, 3.0, head, rod, EXTEND)
    assert counterbalance.fallback_legs == []


@pytest.mark.parametrize(("offset_bar", "falls_back"), [(10.0, False), (20.0, True)])
def test_cb_d2_bound_is_the_law_plus_15_bar(offset_bar, falls_back) -> None:
    """H-S8-1 9.5: D2 bound ``max(12 bar, p_set - psi p_h) + 15 bar``; a rear reading 20 bar
    above the law held 1 s is a fault, 10 bar is not (front: 27 bar bound, not reached)."""
    head, rod = _cb_extend_pressures(rod_offset_bar=offset_bar)
    monitor = _monitor(_cb_settings())
    _run(monitor, 3.0, head, rod, EXTEND)
    assert (monitor.fallback_legs == [2, 3]) is falls_back


def test_cb_fallback_estimate_locks_at_the_cb_rod_pressure() -> None:
    """H-S8-1 9.6 with ``locked_ratio_rule = "fixed"`` (the estimate before P-S8-13):
    ``p_r_hat`` while extending = CB law + 11.4 bar, the lock starts there and rises with the
    locked head drop (1.296 / 1.232). The 9.6 margins via ``with_cb_law_estimate``
    (P-S8-15 raised the defaults)."""
    settings = _cb_settings(locked_ratio_rule="fixed").with_cb_law_estimate()
    head, rod = _cb_extend_pressures()
    monitor = _monitor(settings)
    _run(monitor, 0.5, head, rod, EXTEND)
    law = settings.counterbalance
    expected = np.array([law.extend_rod_pressure_Pa(p_h) for p_h in head]) + 11.4 * BAR
    np.testing.assert_allclose(monitor.meta()["fallback_rod_estimate_Pa"], expected)
    _run(monitor, 0.1, head, rod, STILL, start_s=0.5)  # lock instant
    _run(monitor, 0.3, head - 10 * BAR, rod, STILL, start_s=0.6)
    ratio = np.array(settings.fallback_locked_ratio)
    np.testing.assert_allclose(monitor.meta()["fallback_rod_estimate_Pa"],
                               expected + ratio * 10 * BAR)


def test_cb_slow_extension_uses_the_cb_law_below_the_d2_speed() -> None:
    """9.4 / 9.6: a re-extension at 0.2-1 mm/s (below the D2 speed) still takes the CB law
    (122.6 bar at p_h 52 bar in CB_G4_Fs0), not the 8 bar pilot value (9.6 law; the P-S8-15
    lag bound is in ``test_two_pressure_cb_moving.py``)."""
    monitor = _monitor(_cb_settings().with_cb_law_estimate())
    head = np.full(4, 52.0 * BAR)
    _run(monitor, 0.2, head, np.full(4, 122.0 * BAR), np.full(4, 0.5e-3))
    estimate = monitor.meta()["fallback_rod_estimate_Pa"][3]
    assert estimate == pytest.approx(330e5 - 4 * 52e5 + 11.4 * BAR)


def test_cb_retract_estimate_follows_the_head_cb() -> None:
    """While retracting the head CB meters: ``p_r_hat = (p_set - p_h) / psi + 0.7 bar`` (9.6
    law)."""
    monitor = _monitor(_cb_settings().with_cb_law_estimate())
    _run(monitor, 0.2, np.full(4, 90 * BAR), np.full(4, 60 * BAR), -EXTEND)
    expected = (CB_PARAMS.p_set_Pa - 90 * BAR) / CB_PARAMS.pilot_ratio + 0.7 * BAR
    np.testing.assert_allclose(monitor.meta()["fallback_rod_estimate_Pa"], expected)


def test_lock_valve_settings_and_meta() -> None:
    """``pilot_check`` is the default (same settings, no lock-valve meta keys; the stroke check
    on since U-S8-28); ``counterbalance`` needs its parameters, keeps the stroke check on and
    shows them in the meta; C2Config touches only ``two_pressure``."""
    default = TwoPressureSettings()
    assert default.with_lock_valve("pilot_check", CB_PARAMS) == default
    assert "lock_valve" not in default.to_meta()
    assert default.to_meta()["moving_stroke_check"] is True
    assert "moving_stroke_check" not in replace(default, moving_stroke_check=False).to_meta()
    settings = _cb_settings()
    assert settings.moving_stroke_check
    assert settings.counterbalance_rod_margin_Pa == 15 * BAR
    meta = settings.to_meta()
    assert meta["lock_valve"] == "counterbalance"
    assert meta["counterbalance"]["pilot_ratio"] == CB_PARAMS.pilot_ratio
    json.dumps(meta)
    with pytest.raises(ValueError, match="counterbalance"):
        default.with_lock_valve("counterbalance")
    with pytest.raises(ValueError):
        default.with_lock_valve("needle")
    with pytest.raises(ValueError, match="pilot_ratio"):
        CounterbalanceRodModel(330e5, 0.0, 2e5)
    config = C2Config().with_10hz_d1()
    cb_config = config.with_lock_valve("counterbalance", CB_PARAMS)
    assert cb_config.two_pressure.lock_valve is LockValve.COUNTERBALANCE
    assert replace(cb_config, two_pressure=config.two_pressure) == config


@pytest.mark.parametrize(("stroke_rate_fraction", "falls_back"), [(0.0, False), (0.5, True)])
def test_stroke_check_judges_d2_only_on_a_measured_move(stroke_rate_fraction, falls_back) -> None:
    """P-S8-11 ③ (on for the pilot check too since U-S8-28): a commanded extension whose
    stroke does not move (stuck valve, RE1c forced hold) is not judged; a real move with a
    wrong rod reading still is. Turned off, the unmoved leg is judged as before."""
    head, rod = _cb_extend_pressures(rod_offset_bar=20.0)
    settings = TwoPressureSettings().with_r8_period()
    assert settings.moving_stroke_check
    checked = _monitor(settings)
    _run(checked, 3.0, head, rod, EXTEND, stroke_rate_m_s=stroke_rate_fraction * V_MAX)
    assert (checked.fallback_legs == [0, 1, 2, 3]) is falls_back
    unchecked = _monitor(replace(settings, moving_stroke_check=False))
    _run(unchecked, 3.0, head, rod, EXTEND, stroke_rate_m_s=0.0)
    assert unchecked.fallback_legs == [0, 1, 2, 3]


def test_monitor_without_the_new_attributes_reads_unchanged() -> None:
    """A monitor pickled before P-S8-11 / P-S8-12 has no stroke or previous-command attributes
    (ML ``branch.pkl``); the class defaults keep it reading bit for bit like a new one."""
    settings = TwoPressureSettings().with_r8_period()
    new = _monitor(settings)
    old = copy.deepcopy(new)
    del old.__dict__["_previous_stroke_m"], old.__dict__["_stroke_rate_m_s"]
    del old.__dict__["_previous_commanded_m_s"]
    restored = pickle.loads(pickle.dumps(old))
    head, rod = _cb_extend_pressures()
    for k in range(30):
        stroke = np.full(4, 0.2 + 1e-3 * k)
        command = EXTEND if k < 20 else STILL
        a = new.read(k * PERIOD_S, head, rod, command, k >= 20, 2e3, stroke_m=stroke)
        b = restored.read(k * PERIOD_S, head, rod, command, k >= 20, 2e3, stroke_m=stroke)
        np.testing.assert_array_equal(np.stack([a.nominal, a.lower, a.upper]),
                                      np.stack([b.nominal, b.lower, b.upper]))
    assert new.pop_events() == restored.pop_events()


# --- record replays (07_results/S8, git-ignored) -------------------------------------------


def _cb_equivalent(head, rod, commanded, area_head, area_rod):
    """H-S8-1 9.2 "CB equivalent" of a pilot-check record: same pressure force, rod side on
    the CB law while the leg is commanded to extend."""
    force = head * area_head - rod * area_rod
    psi, p_set = CB_PARAMS.pilot_ratio, CB_PARAMS.p_set_Pa
    rod_cb = np.maximum(CB_PARAMS.back_pressure_Pa,
                        (p_set * area_head - psi * force) / (area_head + psi * area_rod))
    extending = commanded > 0.0
    head_cb = (force + rod_cb * area_rod) / area_head
    return np.where(extending, head_cb, head), np.where(extending, rod_cb, rod)


def _replay(case: Path, settings: TwoPressureSettings, *, cb_equivalent: bool = False):
    """Feed the monitor the 10 Hz readings of a recorded run: pad-record pressures and true
    strokes at the sample instant (ideal sensors: equal to the recorded ``F_hat_N``), the
    applied command (``issued_u`` of the period before), READY and the band; the zero offsets
    from the calibration end. Returns (fallback events, nominal and lower readings)."""
    result = json.loads((case / "result.json").read_text(encoding="utf-8"))
    controller = result["controller_meta"]
    meta = controller["two_pressure"]
    if cb_equivalent:  # the pilot -> CB switch of the transform is a step no record has
        settings = replace(settings, max_step_Pa=1e12)
    monitor = TwoPressureMonitor(
        meta["head_area_m2"], meta["annulus_area_m2"], controller["geometry"]["max_speed_m_s"],
        controller["geometry"]["F_min_N"], controller["period_s"],
        LoadEstimate(meta["load_estimate"]), settings, meta["rod_weight_N"])
    calibration_end_s = controller["zero_calibration"]["result"]["t_end_s"]
    with np.load(case / "r8_series.npz") as r8, np.load(case / "pads.npz") as pads:
        t = r8["t"]
        index = np.clip(np.searchsorted(pads["t"], t), 0, len(pads["t"]) - 1)
        head, rod = pads["head_pressure"][index], pads["rod_pressure"][index]
        stroke = pads["stroke_true"][index]
        issued, phase, band, f_hat = r8["issued_u"], r8["phase"], r8["F_band_N"], r8["F_hat_N"]
    area_head, area_rod = np.array(meta["head_area_m2"]), np.array(meta["annulus_area_m2"])
    np.testing.assert_allclose(head * area_head - rod * area_rod, f_hat, atol=1e-6)
    commanded = np.vstack([np.zeros((1, 4)), issued[:-1]])
    if cb_equivalent:
        head, rod = _cb_equivalent(head, rod, commanded, area_head, area_rod)
    fallback, readings = [], []
    for k in range(len(t)):
        locked = bool(k) and phase[k - 1] == "READY"
        bands = monitor.leg_seal_bands_N(band[k - 1] if k else band[0])
        forces = monitor.read(t[k], head[k], rod[k], commanded[k], locked, bands,
                              stroke_m=stroke[k])
        readings.append(np.concatenate([forces.nominal, forces.lower]))
        fallback += [(round(t[k], 1), name) for name, _ in monitor.pop_events()
                     if name.startswith("INFO_ROD_PRESSURE_FAULT_REASON")]
        if t[k] >= calibration_end_s - 1e-9 and not monitor.zero_offsets_N.any():
            monitor.set_zero_offsets_N(controller["zero_calibration"]["offsets_N"])
    return fallback, np.array(readings)


@pytest.mark.parametrize("case", CB_CASES, ids=lambda case: case.name)
def test_cb_record_replay_has_no_false_rod_fallback(case) -> None:
    """216.8 / 9.8: the CB F_s 0 runs with the pilot-check diagnosis reproduce the recorded RR
    D2 fallback at 29.2 s; with ``lock_valve = counterbalance`` there is none."""
    if not case.is_dir():
        pytest.skip("07_results/S8 CB batch not present")
    pilot_events, _ = _replay(case, TwoPressureSettings().with_r8_period())
    assert pilot_events == [(29.2, "INFO_ROD_PRESSURE_FAULT_REASON:RR:D2")]
    cb_events, _ = _replay(case, _cb_settings())
    assert cb_events == []


@pytest.mark.skipif(not ROLL_CASE.is_dir(), reason="07_results/S8 p1r batch not present")
def test_cb_equivalent_roll_record_has_no_false_rl_fallback() -> None:
    """9.2 / 9.8: the roll 5.5 deg run made CB-equivalent drives RL past 12 bar for over 1 s
    (pilot-check D2 falls it back); the CB setting does not."""
    pilot_events, _ = _replay(ROLL_CASE, TwoPressureSettings().with_r8_period(),
                              cb_equivalent=True)
    assert [name for _, name in pilot_events] == ["INFO_ROD_PRESSURE_FAULT_REASON:RL:D2"]
    cb_events, _ = _replay(ROLL_CASE, _cb_settings(), cb_equivalent=True)
    assert cb_events == []


@pytest.mark.skipif(not PILOT_CASE.is_dir(), reason="07_results/S8 p1r batch not present")
def test_pilot_check_record_replay_is_bit_identical_through_with_lock_valve() -> None:
    """The pilot-check path through ``with_lock_valve("pilot_check")`` reads every sample of a
    recorded run bit for bit like the default settings."""
    default = TwoPressureSettings().with_r8_period()
    events, readings = _replay(PILOT_CASE, default)
    same_events, same_readings = _replay(PILOT_CASE, default.with_lock_valve("pilot_check"))
    assert events == same_events
    np.testing.assert_array_equal(readings, same_readings)


@pytest.mark.skipif(not ML_BRANCH.is_file(), reason="07_results/S8 ML pilot bases not present")
def test_controller_from_a_branch_pickled_before_p_s8_11_keeps_running() -> None:
    """The ML episodes restore the controller from ``branch.pkl`` written by the code before
    P-S8-11 (00:48 failures: ``_previous_stroke_m`` missing); a few updates must run."""
    with open(ML_BRANCH, "rb") as handle:
        blob = pickle.load(handle)  # noqa: S301 - own batch file
    controller = blob["controller"]
    inner = getattr(controller, "inner", controller)
    head = np.asarray(inner._state.last_forces.head_only) / inner._pressures.head_area_m2
    stroke = np.asarray(inner._state.last_reading.motor_stroke_m, dtype=float)
    level = np.array([0.0, 0.0, GRAVITY_M_S2])
    for k in range(5):
        command = controller.update(Measurements(
            t_s=float(blob["t_s"]) + (k + 1) * PERIOD_S,
            specific_force_m_s2=level,
            angular_rate_rad_s=np.zeros(3),
            head_pressure_Pa=head,
            stroke_m=stroke,
            rod_pressure_Pa=np.full(4, 5e5),
            imu_specific_force_samples_m_s2=np.tile(level, (10, 1)),
        ))
        assert np.all(np.isfinite(command.leg_speed_m_s))
