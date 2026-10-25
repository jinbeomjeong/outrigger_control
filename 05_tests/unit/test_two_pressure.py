"""``control/two_pressure``: net force, D1-D6, fallback, rod-side watch and the shadows (R6-P,
control spec 51.1, 53.3-53.4, 64.2)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from outrigger_sim.control.two_pressure import (
    LoadEstimate,
    RodSensorState,
    TwoPressureMonitor,
    TwoPressureSettings,
)
from outrigger_sim.params import load_params

BAR = 1e5
PERIOD_S = 0.02
HEAD_AREA = np.array([1.3273e-2, 1.3273e-2, 9.5033e-3, 9.5033e-3])
ANNULUS = np.array([3.7699e-3, 3.7699e-3, 3.1416e-3, 3.1416e-3])
V_MAX = 0.022026
F_MIN = load_params().control.F_min_cylinder_N  # the YAML value (spec rev. 13)
LOAD_N = np.array([118e3, 118e3, 72e3, 72e3])
STILL = np.zeros(4)


def _monitor(**settings) -> TwoPressureMonitor:
    return TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN, PERIOD_S,
                              settings=TwoPressureSettings(**settings))


def _pressures(load_N=LOAD_N, rod_bar=2.0):
    rod = np.full(4, rod_bar * BAR)
    return (load_N + rod * ANNULUS) / HEAD_AREA, rod


START_STROKE_M = 0.2


def _run(monitor, periods, *, start_s=0.0, load_N=LOAD_N, rod_bar=2.0, command=STILL,
         locked=True, band=2e3, rod_override=None):
    """Read ``periods`` samples; the measured stroke follows the command (U-S8-28 stroke
    check of D2 / D3)."""
    forces = None
    for k in range(periods):
        t_s = start_s + k * PERIOD_S
        head, rod = _pressures(load_N, rod_bar)
        if rod_override is not None:
            rod = rod_override(rod.copy())
        stroke = START_STROKE_M + command * t_s
        forces = monitor.read(t_s, head, rod, command, locked, band, stroke_m=stroke)
    return forces


def _names(monitor):
    return [name for name, _ in monitor.pop_events()]


def test_net_force_and_the_head_only_paths() -> None:
    """P-2: net = p_h A_p - p_r A_ann (to rounding); no rod sensor or head_only = p_h A_p."""
    monitor = _monitor()
    head, rod = _pressures()
    forces = monitor.read(0.0, head, rod, STILL, True, 2e3)
    np.testing.assert_allclose(forces.nominal, LOAD_N, rtol=1e-12)
    assert forces.lower is forces.nominal and forces.upper is forces.nominal
    without_rod = monitor.read(0.02, head, None, STILL, True, 2e3)
    np.testing.assert_array_equal(without_rod.nominal, head * HEAD_AREA)
    head_only = TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN, PERIOD_S,
                                   load_estimate=LoadEstimate.HEAD_ONLY)
    np.testing.assert_array_equal(head_only.read(0.0, head, rod, STILL, True, 2e3).nominal,
                                  head * HEAD_AREA)
    assert not head_only.has_rod_sensor


def test_airborne_leg_reads_minus_the_rod_weight() -> None:
    """P-2 synthetic: p_r 11.85 bar, p_h 0 -> F = -p_r A_ann (old areas: -1.047 kN)."""
    old_annulus = 8.836e-4
    monitor = TwoPressureMonitor(np.full(4, 1.0387e-2), np.full(4, old_annulus), V_MAX,
                                 F_MIN, PERIOD_S)
    forces = monitor.read(0.0, np.zeros(4), np.full(4, 11.85 * BAR), STILL, False, 2e3)
    assert forces.nominal[0] == pytest.approx(-1047.0, rel=1e-3)


@pytest.mark.parametrize("fault", ["nan", "range", "jump"])
def test_rod_side_d1_fault_falls_back_on_that_leg_only(fault) -> None:
    monitor = _monitor()
    _run(monitor, 3)

    def broken(rod):
        rod[3] = {"nan": math.nan, "range": 450 * BAR, "jump": 150 * BAR}[fault]
        return rod

    forces = _run(monitor, 1, start_s=0.06, rod_override=broken)
    assert monitor.rod_state[3] is RodSensorState.FALLBACK
    assert monitor.fallback_legs == [3]
    names = _names(monitor)
    assert names.count("WARN_ROD_PRESSURE_FALLBACK:RR") == 1
    head, _ = _pressures()
    assert forces.nominal[3] == pytest.approx(head[3] * HEAD_AREA[3])  # head reading
    assert forces.lower[3] < forces.nominal[3] < forces.upper[3]
    assert forces.lower[0] == forces.nominal[0]  # other legs unchanged
    np.testing.assert_allclose(monitor.leg_seal_bands_N(2e3), [2e3, 2e3, 2e3, 13e3])


def test_head_side_fault_is_reported_for_a_fault() -> None:
    monitor = _monitor()
    head, rod = _pressures()
    head[1] = math.nan
    monitor.read(0.0, head, rod, STILL, True, 2e3)
    assert monitor.head_fault_legs == [1]
    assert "FAULT_HEAD_PRESSURE:FR" in _names(monitor)


def test_stuck_reading_is_a_fault_only_with_sensor_noise() -> None:
    monitor = _monitor(pressure_noise_std_Pa=0.3 * BAR)
    _run(monitor, round(10.0 / PERIOD_S))
    assert set(monitor.fallback_legs) == {0, 1, 2, 3}  # every reading frozen
    ideal = _monitor()
    _run(ideal, round(10.0 / PERIOD_S))
    assert ideal.fallback_legs == []


def test_d2_rod_side_too_high_while_extending_a_grounded_leg() -> None:
    """D2: an extending grounded leg must read 1-8 bar (<= 12 bar); a +30 bar stuck offset
    held 1 s after the 1 s settle falls back; not within 2 s after a retraction."""
    command = np.full(4, 0.5 * V_MAX)
    monitor = _monitor()
    _run(monitor, round(1.5 / PERIOD_S), command=command, locked=False, rod_bar=32.0)
    assert monitor.fallback_legs == []  # settle 1 s + violation 1 s not yet reached
    _run(monitor, round(1.0 / PERIOD_S), start_s=1.5, command=command, locked=False,
         rod_bar=32.0)
    assert monitor.fallback_legs == [0, 1, 2, 3]
    recent = _monitor()
    _run(recent, 2, command=-command, locked=False, rod_bar=40.0)
    _run(recent, round(2.0 / PERIOD_S), start_s=0.04, command=command, locked=False,
         rod_bar=32.0)
    assert recent.fallback_legs == []  # reversal exclusion (R-H5)


def _rod_300_bar_on_rr(rod):
    rod[3] = 300 * BAR
    return rod


def _drop_transient_pressures():
    """RR head 4 bar and rod side 89 bar: net -24.2 kN, the M4 drop transient of spec 109.5
    as one sample (both jumps stay below the 100 bar D1 step)."""
    head, rod = _pressures()
    head[3] = 4.0 * BAR
    rod[3] = 89.0 * BAR
    return head, rod


def test_d4_physical_lower_bound_when_locked() -> None:
    """A rod reading 300 bar on a 72 kN leg gives a net force far below -(m_rod g + F_band);
    held 0.1 s (spec 110.2) the leg falls back."""
    monitor = _monitor()
    _run(monitor, round(0.2 / PERIOD_S), rod_override=_rod_300_bar_on_rr)
    assert monitor.fallback_legs == [3]
    names = _names(monitor)
    assert "INFO_ROD_PRESSURE_FAULT_REASON:RR:D4" in names
    assert names.count("INFO_ROD_D4_TRANSIENT:RR") == 1


def test_d4_single_sample_is_a_transient_not_a_fallback() -> None:
    """110.2: one sample at -24 kN (an M4 drop transient read by one sample) -> no fallback,
    ``INFO_ROD_D4_TRANSIENT``; the hold restarts after a good sample."""
    monitor = _monitor()
    normal, drop = _pressures(), _drop_transient_pressures()
    for k, (head, rod) in enumerate([normal, normal, drop, normal, normal, drop]):
        monitor.read(k * PERIOD_S, head, rod, STILL, True, 2e3)
    assert monitor.fallback_legs == []
    names = _names(monitor)
    assert names.count("INFO_ROD_D4_TRANSIENT:RR") == 2
    assert not [name for name in names if name.startswith("WARN_ROD_PRESSURE_FALLBACK")]


def test_d4_drop_reading_held_0_2_s_falls_back() -> None:
    """110.2: the same -24 kN reading for 0.2 s (10 samples) is a rod-side fault."""
    monitor = _monitor()
    normal, drop = _pressures(), _drop_transient_pressures()
    monitor.read(0.0, *normal, STILL, True, 2e3)
    for k in range(1, 11):
        monitor.read(k * PERIOD_S, *drop, STILL, True, 2e3)
    assert monitor.fallback_legs == [3]
    assert "INFO_ROD_PRESSURE_FAULT_REASON:RR:D4" in _names(monitor)


@pytest.mark.parametrize(("period_s", "samples", "falls_back"),
                         [(0.02, 4, False), (0.02, 5, True), (0.1, 1, False), (0.1, 2, True)])
def test_d4_hold_counts_samples_and_time(period_s, samples, falls_back) -> None:
    """110.2: >= 2 samples in a row and >= 0.1 s (samples x period): 5 samples at 50 Hz,
    2 samples at 10 Hz."""
    monitor = TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN, period_s)
    for k in range(samples):
        head, rod = _pressures()
        monitor.read(k * period_s, head, _rod_300_bar_on_rr(rod), STILL, True, 2e3)
    assert (monitor.fallback_legs == [3]) is falls_back


def test_d4_is_not_judged_outside_the_locked_phase() -> None:
    """The hold restarts when READY is left (the samples must be consecutive locked ones)."""
    monitor = _monitor()
    _run(monitor, 4, rod_override=_rod_300_bar_on_rr)
    _run(monitor, 1, start_s=0.08, rod_override=_rod_300_bar_on_rr, locked=False)
    _run(monitor, 4, start_s=0.10, rod_override=_rod_300_bar_on_rr)
    assert monitor.fallback_legs == []


def test_rod_side_limits_warn_once_per_leg() -> None:
    """P-13: 351 bar locked -> over limit and pre-warning once; head 349 + rod 20 bar is no
    head event here (the head limit is the controller's)."""
    monitor = _monitor()
    _run(monitor, 3, rod_bar=351.0)
    names = _names(monitor)
    for leg in ("FL", "FR", "RL", "RR"):
        assert names.count(f"rod_pressure_over_limit:{leg}") == 1
        assert names.count(f"rod_pressure_prewarning:{leg}") == 1


def test_predicted_lift_off_pressure_warning() -> None:
    """P-13 (3): p_r + r (F + m_rod g) / A_ann > 350 bar: front boundary 486.7 kN (spec 64.1);
    118 kN -> none, 500 kN -> warning."""
    monitor = _monitor()
    _run(monitor, 1, load_N=np.array([118e3, 118e3, 72e3, 72e3]))
    assert not [n for n in _names(monitor) if "LIFTOFF" in n]
    heavy = _monitor()  # a fresh monitor: a 260 bar jump in one period would be a D1 fault
    _run(heavy, 1, load_N=np.array([500e3, 118e3, 72e3, 72e3]))
    assert _names(heavy) == ["WARN_ROD_LIFTOFF_OVERPRESSURE_RISK:FL"]


def test_load_drop_shadow_and_sum_check() -> None:
    """P-6: Delta F < -20 kN against the GE1' baseline for 0.5 s -> shadow_load_drop; the sum
    of the changes beyond 4 F_band + 2.5 kN -> WARN_LOAD_SUM_MISMATCH (both once)."""
    monitor = _monitor()
    monitor.store_load_reference(0.0, LOAD_N)
    dropped = LOAD_N - np.array([0.0, 0.0, 0.0, 30e3])
    _run(monitor, round(0.6 / PERIOD_S), load_N=dropped)
    names = _names(monitor)
    assert names.count("shadow_load_drop:RR") == 1
    assert names.count("WARN_LOAD_SUM_MISMATCH") == 1
    np.testing.assert_allclose(monitor.load_change_N(dropped), [0, 0, 0, -30e3])


def test_retraction_lift_off_shadow() -> None:
    """P-11 (U50): an airborne retraction reads -m_rod g - F_s -> confirmed after settle +
    average; a grounded 20 kN retraction is not."""
    command = np.full(4, -0.2 * V_MAX)
    load = np.array([20e3, 20e3, -0.7e3 - 5e3, -0.7e3])
    monitor = _monitor(diagnostics=True, retract_check=False)
    _run(monitor, round(1.0 / PERIOD_S), command=command, locked=False, load_N=load,
         rod_bar=40.0)
    names = _names(monitor)
    assert "shadow_retract_liftoff:RL" in names and "shadow_retract_liftoff:RR" in names
    assert "shadow_retract_liftoff:FL" not in names


def test_d6_probe_consistency() -> None:
    """D6: the rod side must rise from the E hold end to the R hold end; two misses in a row
    fall the leg back."""
    from outrigger_sim.control.ground_contact import ProbeResult

    monitor = _monitor()
    _run(monitor, 50, rod_bar=2.0)
    result = ProbeResult(0, 118e3, 0.0, 6e6, True, t_first_hold_end_s=0.2,
                         t_second_hold_end_s=0.8)
    for _ in range(2):
        monitor.probe_round_finished([result])
    assert monitor.fallback_legs == [0]


# --- load baseline of D5 / E-5 (spec 110.1) -----------------------------------------------------

SETTLE_S = 0.5
MOVING = np.full(4, 0.1 * V_MAX)


def _settled_monitor(band_N=1.5e3):
    """A monitor that saw a command, then 0.5 s of zero commands, and stored its baseline."""
    monitor = _monitor()
    _run(monitor, 1, command=MOVING, band=band_N)
    _run(monitor, round(SETTLE_S / PERIOD_S), start_s=PERIOD_S, band=band_N)
    monitor.store_load_reference(SETTLE_S + PERIOD_S, LOAD_N, "ready")
    _names(monitor)
    return monitor


def test_command_free_time_counts_the_zero_commands() -> None:
    monitor = _monitor()
    assert monitor.command_free_s == math.inf  # no command seen yet
    _run(monitor, 1, command=MOVING)
    assert monitor.command_free_s == 0.0
    _run(monitor, 25, start_s=PERIOD_S)
    assert monitor.command_free_s == pytest.approx(0.5)


def test_sum_step_of_minus_10_kN_warns_once() -> None:
    """D5 with F_band 1.5 kN (limit 4 x 1.5 + 2.5 = 8.5 kN): a -10 kN sum step warns once and
    the meta keeps the sum, the baseline sum and the limit."""
    monitor = _settled_monitor()
    stepped = LOAD_N - np.array([10e3, 0.0, 0.0, 0.0])
    _run(monitor, 50, start_s=1.0, load_N=stepped, band=1.5e3)
    assert _names(monitor).count("WARN_LOAD_SUM_MISMATCH") == 1
    (logged,) = monitor.meta()["load_sum_events"]
    assert logged["sum_N"] - logged["reference_sum_N"] == pytest.approx(-10e3, abs=1e-6)
    assert logged["allowed_N"] == pytest.approx(8.5e3)


def test_sum_step_while_commanded_is_not_judged() -> None:
    """110.1 (4): the same step while the legs move (and for 0.5 s after) raises nothing."""
    monitor = _settled_monitor()
    stepped = LOAD_N - np.array([10e3, 0.0, 0.0, 0.0])
    _run(monitor, 50, start_s=1.0, load_N=stepped, band=1.5e3, command=MOVING)
    _run(monitor, round(SETTLE_S / PERIOD_S) - 1, start_s=2.0, band=1.5e3)
    assert "WARN_LOAD_SUM_MISMATCH" not in _names(monitor)


def test_no_baseline_and_suspended_baseline_are_not_judged() -> None:
    """Before the first store, and between a new READY stay and its store, nothing is judged."""
    monitor = _monitor()
    stepped = LOAD_N - np.array([30e3, 0.0, 0.0, 0.0])
    _run(monitor, 100, load_N=stepped, band=1.5e3)
    assert not [n for n in _names(monitor) if "LOAD_SUM" in n or "shadow_load_drop" in n]
    settled = _settled_monitor()
    settled.suspend_load_reference()
    assert not settled.is_load_watch_open
    _run(settled, 100, start_s=1.0, load_N=stepped, band=1.5e3)
    assert not [n for n in _names(settled) if "LOAD_SUM" in n or "shadow_load_drop" in n]


def _drifting_head(t_s: float) -> tuple[np.ndarray, np.ndarray]:
    """FL head +2 bar per minute from t = 0 (zero drift after the calibration, PS-5)."""
    head, rod = _pressures()
    head[0] += 2.0 * BAR * t_s / 60.0
    return head, rod


def test_fl_drift_of_2_bar_per_minute_warns_once() -> None:
    """E-5: FL +2 bar/min = +2.65 kN/min on the sum; above 4 kN after about 91 s, held 30 s
    -> one ``WARN_PRESSURE_DRIFT`` near 121 s, with its meta entry."""
    monitor = _monitor()
    monitor.store_load_reference(0.0, LOAD_N, "ready")
    times_s = np.arange(round(150.0 / PERIOD_S)) * PERIOD_S
    warned_at_s = None
    for t_s in times_s:
        monitor.read(float(t_s), *_drifting_head(float(t_s)), STILL, True, 2e3)
        if warned_at_s is None and "WARN_PRESSURE_DRIFT" in _names(monitor):
            warned_at_s = float(t_s)
    assert warned_at_s == pytest.approx(4000.0 / (2.0 * BAR * HEAD_AREA[0] / 60.0) + 30.0,
                                        abs=0.1)
    (logged,) = monitor.meta()["load_sum_events"]
    assert logged["event"] == "WARN_PRESSURE_DRIFT" and logged["allowed_N"] == 4000.0


def test_drift_hold_restarts_on_a_command() -> None:
    """110.1 (4): a command every 20 s restarts the E-5 hold, so the 30 s hold never ends."""
    monitor = _monitor()
    monitor.store_load_reference(0.0, LOAD_N, "ready")
    for k in range(round(150.0 / PERIOD_S)):
        t_s = k * PERIOD_S
        command = MOVING if k % round(20.0 / PERIOD_S) == 0 else STILL
        monitor.read(t_s, *_drifting_head(t_s), command, True, 2e3)
    assert "WARN_PRESSURE_DRIFT" not in _names(monitor)


def test_store_logs_the_sum_change_against_the_previous_baseline() -> None:
    """110.1 (5): a re-store records ``sum - previous sum`` (the sum should not change)."""
    monitor = _monitor()
    monitor.store_load_reference(1.0, LOAD_N, "ready")
    monitor.store_load_reference(9.0, LOAD_N + 500.0, "done")
    first, second = monitor.meta()["load_reference"]
    assert first["previous_sum_N"] is None and first["source"] == "ready"
    assert second["sum_change_N"] == pytest.approx(2000.0)


# --- baseline mean (spec rev. 29 120) ------------------------------------------------------------

HEAVE_HZ = 8.7
HEAVE_ZETA = 0.03
RINGING_AT_STORE_N = 3e3
"""Sum ringing amplitude at the store (decaying 8.7 Hz heave, zeta 0.03, spec 120)."""
MEAN_BIAS_LIMIT_N = 0.5e3


def _ringing_sum_N(t_s: np.ndarray, store_t_s: float, phase_rad: float) -> np.ndarray:
    """Heave ringing of the load sum whose envelope is ``RINGING_AT_STORE_N`` at the store."""
    omega = 2.0 * math.pi * HEAVE_HZ
    envelope = RINGING_AT_STORE_N * np.exp(-HEAVE_ZETA * omega * (t_s - store_t_s))
    damped = omega * math.sqrt(1.0 - HEAVE_ZETA**2)
    return envelope * np.cos(damped * (t_s - store_t_s) + phase_rad)


def _baseline_bias_N(mean_s: float, phase_rad: float) -> float:
    """Stored baseline sum minus the true (ringing-free) sum after 0.5 s without commands."""
    monitor = _monitor(load_reference_mean_s=mean_s)
    _run(monitor, 1, command=MOVING)
    periods = round(SETTLE_S / PERIOD_S)
    times_s = PERIOD_S * (1 + np.arange(periods))
    ringing = _ringing_sum_N(times_s, times_s[-1], phase_rad)
    for t_s, extra_N in zip(times_s, ringing, strict=True):
        loads = LOAD_N + extra_N * LOAD_N / LOAD_N.sum()
        monitor.read(float(t_s), *_pressures(loads), STILL, True, 2e3)
    monitor.store_load_reference(float(times_s[-1]), loads, "ready")
    return monitor.meta()["load_reference"][-1]["sum_N"] - float(LOAD_N.sum())


PHASES_RAD = np.linspace(0.0, 2.0 * math.pi, 24, endpoint=False)


def test_baseline_mean_over_heave_ringing_has_small_bias() -> None:
    """120: on 8.7 Hz ringing of +-3 kN at the store, the 0.5 s mean is within 0.5 kN of the
    true sum at every phase; one sample (the 110.1 baseline) is off by up to 3 kN."""
    mean_bias = [abs(_baseline_bias_N(0.5, phase)) for phase in PHASES_RAD]
    single_bias = [abs(_baseline_bias_N(PERIOD_S, phase)) for phase in PHASES_RAD]
    assert max(mean_bias) <= MEAN_BIAS_LIMIT_N
    assert max(single_bias) == pytest.approx(RINGING_AT_STORE_N, rel=1e-6)


def test_baseline_meta_records_window_and_sample_count() -> None:
    """120: meta ``load_reference`` keeps the window, the samples averaged and the last one."""
    monitor = _settled_monitor()
    (stored,) = monitor.meta()["load_reference"]
    assert stored["mean_window_s"] == 0.5
    assert stored["sample_count"] == 25
    assert stored["sum_N"] == pytest.approx(LOAD_N.sum(), rel=1e-12)
    assert monitor.meta()["settings"]["load_reference_mean_s"] == 0.5


def test_baseline_mean_drops_readings_before_the_stay_and_under_commands() -> None:
    """120: a command empties the buffer; a new stay keeps only the reading that entered it."""
    monitor = _monitor()
    _run(monitor, 10, load_N=LOAD_N + 4e3)
    _run(monitor, 1, start_s=0.2, command=MOVING)
    _run(monitor, 10, start_s=0.22, load_N=LOAD_N + 8e3)
    monitor.suspend_load_reference()
    _run(monitor, 4, start_s=0.42)
    monitor.store_load_reference(0.5, LOAD_N, "ready")
    (stored,) = monitor.meta()["load_reference"]
    assert stored["sample_count"] == 5
    assert stored["sum_N"] == pytest.approx(LOAD_N.sum() + 4 * 8e3 / 5, rel=1e-12)


def test_without_buffered_reading_the_given_loads_are_the_baseline() -> None:
    monitor = _monitor()
    monitor.store_load_reference(1.0, LOAD_N + 500.0, "ready")
    (stored,) = monitor.meta()["load_reference"]
    assert stored["sum_N"] == pytest.approx(LOAD_N.sum() + 2000.0)
    assert stored["sample_count"] == 1


def test_r8_period_preset_sets_the_10_hz_diagnosis_constants() -> None:
    """Spec rev. 29 126 #3: settle 0.5 s, mean 1.5 s (15 samples at 0.1 s), D4 2 samples =
    0.2 s, D5 hold 0.5 s, E-5 hold 30 s; nothing else changes."""
    default = TwoPressureSettings()
    r8 = default.with_r8_period()
    assert (r8.load_reference_settle_s, r8.load_reference_mean_s) == (0.5, 1.5)
    assert (r8.d4_min_samples, r8.d4_hold_s) == (2, 0.2)
    assert (r8.sum_hold_s, r8.drift_hold_s) == (0.5, 30.0)
    changed = {key for key, value in r8.to_meta().items() if default.to_meta()[key] != value}
    assert changed == {"load_reference_mean_s", "d4_hold_s"}
    r8_period_s = 0.1
    monitor = TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN, r8_period_s, settings=r8)
    for k in range(20):
        monitor.read(k * r8_period_s, *_pressures(), STILL, True, 2e3)
    monitor.store_load_reference(2.0, LOAD_N, "ready")
    assert monitor.meta()["load_reference"][-1]["sample_count"] == 15


@pytest.mark.parametrize(("duration_s", "warns"), [(0.3, False), (0.6, True)])
def test_sum_mismatch_must_hold_while_judged(duration_s, warns) -> None:
    """``sum_hold_s`` 0.5 s (ASSUMPTION): a floor-event transient (RE1b-F: sum -63 kN while the
    body drops, before the re-level command) does not warn; a lasting mismatch does."""
    monitor = _settled_monitor()
    dropped = LOAD_N - np.array([0.0, 0.0, 0.0, 63e3])
    _run(monitor, round(duration_s / PERIOD_S), start_s=1.0, load_N=dropped, band=1.5e3)
    _run(monitor, 50, start_s=2.0, band=1.5e3)
    assert ("WARN_LOAD_SUM_MISMATCH" in _names(monitor)) is warns
