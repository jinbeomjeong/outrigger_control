"""D1'' of ``control/two_pressure`` (U-S8-31, P-S8-14, control spec rev. 48 218.4, 218.15).

Synthetic cases: the IMU residual head rule (a vertical bounce is explained, a sensor jump is
not), its fall-backs to the D1' sum rule (crawler on the ground, no ``M_eff`` yet, no IMU input
with one warning), the rod-side reason ``lock_load_regain``, the head fault reasons, and
monitors / settings pickled before P-S8-14.

Record replays of ``07_results/S8`` (git-ignored; skipped without it), the inputs the
controller's monitor saw: ``record/record.npz`` ``meas.*`` at the 10 Hz sample, ``r8_series``
``issued_u`` one period late, ``leg_band_N`` and ``phase`` of the period before, the body-z
specific force of the last 10 ms IMU sample (``imu_samples[:, -1, 2]``). An ML episode starts
from its base's ``branch.pkl`` monitor with the settings refreshed (as the ML runner does); a
base starts from a fresh monitor with the zero offsets of its calibration.
"""

from __future__ import annotations

import copy
import json
import math
import pickle
import re
from dataclasses import dataclass, field, replace
from functools import cache
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from outrigger_sim.control.two_pressure import (
    IMU_GYRO_SAMPLE_PERIOD_S,
    IMU_RULE_META_KEYS,
    LoadEstimate,
    StepRule,
    TwoPressureMonitor,
    TwoPressureSettings,
)

BAR = 1e5
PERIOD_S = 0.1
HEAD_AREA = np.array([1.3273229e-2, 1.3273229e-2, 9.50331778e-3, 9.50331778e-3])
ANNULUS = np.array([3.76991118e-3, 3.76991118e-3, 3.14159265e-3, 3.14159265e-3])
V_MAX = 0.020924
F_MIN_N = 9414.59
GRAVITY_M_S2 = 9.80665
LOAD_N = np.array([118e3, 118e3, 72e3, 72e3])
BODY_MASS_KG = float(LOAD_N.sum()) / GRAVITY_M_S2
STILL = np.zeros(4)
FL, FR, RL, RR = 0, 1, 2, 3
STROKE_M = 0.552
LIFTED_PHASES = frozenset({"level", "done", "reanchor", "probe", "ready"})
"""``C2Phase`` values of ``c2.CRAWLER_LIFTED_PHASES`` as recorded in ``r8_series`` ``phase``."""


def _monitor(**changes) -> TwoPressureMonitor:
    settings = replace(TwoPressureSettings().with_r8_period(), **changes)
    return TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN_N, PERIOD_S, settings=settings,
                              stroke_max_m=0.70)


def _pressures(load_N, rod_bar=2.0):
    rod = np.full(4, rod_bar * BAR)
    return (np.asarray(load_N, dtype=float) + rod * ANNULUS) / HEAD_AREA, rod


@dataclass
class _Bench:
    """Feeds one monitor period by period (strokes still unless given)."""

    monitor: TwoPressureMonitor
    t_s: float = 0.0
    names: list[str] = field(default_factory=list)

    def read(self, head, rod, *, f_z=GRAVITY_M_S2, locked=False, lifted=True,
             stroke=None, command=STILL, gyro=None):
        stroke = np.full(4, STROKE_M) if stroke is None else stroke
        self.monitor.read(self.t_s, head, rod, command, locked, 2e3, stroke_m=stroke,
                          imu_specific_force_z_m_s2=f_z, is_crawler_lifted=lifted,
                          imu_gyro_rad_s=gyro)
        self.t_s += PERIOD_S
        self.names += [name for name, _ in self.monitor.pop_events()]

    def ready_stay(self, samples=5, load_N=LOAD_N, gyro=None):
        """READY samples at rest: ``M_eff`` = ``sum load_N / g``."""
        for _ in range(samples):
            self.read(*_pressures(load_N), locked=True, gyro=gyro)


def _faults(names):
    return [name for name in names if "FALLBACK" in name or "FAULT" in name]


def _steps(names):
    return [name for name in names if name.startswith("INFO_PRESSURE_STEP")]


# --- D1'' head rule ---------------------------------------------------------------------------


BOUNCE_SCALE = 1.4
"""Vertical bounce: the four-leg sum and ``f_z`` both 1.4 times the static value."""


def _bounce(bench, *, previous_f_z=GRAVITY_M_S2, lifted=True):
    """Body bounce after a front sinkage (218.2): every leg load and the IMU ``f_z`` grow by
    ``BOUNCE_SCALE`` while 99 kN moves from FL to FR, so FR's head steps +110 bar. The sum
    changes by 151 kN against FR's 146 kN step (D1' ratio 1.03), the IMU residual by 0."""
    bench.read(*_pressures(LOAD_N), f_z=previous_f_z, lifted=lifted)
    after_N = LOAD_N * BOUNCE_SCALE
    moved_N = LOAD_N[FR] + 110.0 * BAR * HEAD_AREA[FR] - after_N[FR]
    after_N += np.array([-moved_N, moved_N, 0.0, 0.0])
    bench.read(*_pressures(after_N), f_z=BOUNCE_SCALE * GRAVITY_M_S2, lifted=lifted)


def test_vertical_bounce_is_explained_by_the_imu_residual() -> None:
    bench = _Bench(_monitor())
    bench.ready_stay()
    assert bench.monitor._imu_mass_kg == pytest.approx(BODY_MASS_KG)
    _bounce(bench)
    assert bench.monitor.head_fault_legs == []
    assert _steps(bench.names) == ["INFO_PRESSURE_STEP:FR:head:imu_residual"]


def test_d1_prime_faults_on_the_same_bounce() -> None:
    """The sum rule (``explained``) does not know the vertical acceleration (218.2)."""
    bench = _Bench(_monitor(step_rule="explained"))
    bench.ready_stay()
    _bounce(bench)
    assert bench.monitor.head_fault_legs == [FR]


HEAVY_LOAD_N = 2.0 * LOAD_N
"""Leg loads with every head above 150 bar, so a -150 bar jump stays inside the range."""


@pytest.mark.parametrize("jump_bar", [100.5, -100.5, 150.0, -150.0])
def test_head_sensor_jump_is_a_fault_with_its_reason(jump_bar) -> None:
    bench = _Bench(_monitor())
    bench.ready_stay(load_N=HEAVY_LOAD_N)
    head, rod = _pressures(HEAVY_LOAD_N)
    head[RL] += jump_bar * BAR
    bench.read(head, rod)
    assert bench.monitor.head_fault_legs == [RL]
    assert _faults(bench.names) == ["FAULT_HEAD_PRESSURE:RL",
                                    "INFO_HEAD_PRESSURE_FAULT_REASON:RL:D1_step"]


@pytest.mark.parametrize("case", ["crawler_on_ground", "no_ready_stay", "first_imu_sample"])
def test_bounce_falls_back_to_the_sum_rule(case) -> None:
    """Crawler not lifted (CHECK / TOUCH), no ``M_eff`` (``median``: no READY stay yet) or no
    IMU value of the period before: the D1' sum rule, silently."""
    bench = _Bench(_monitor(imu_mass_calibration="median"))
    if case != "no_ready_stay":
        bench.ready_stay()
    previous_f_z = None if case == "first_imu_sample" else GRAVITY_M_S2
    _bounce(bench, previous_f_z=previous_f_z, lifted=case != "crawler_on_ground")
    assert bench.monitor.head_fault_legs == [FR]
    assert "WARN_D1_IMU_INPUT_MISSING" not in bench.names


def test_missing_imu_input_falls_back_with_one_warning() -> None:
    """218.15 (e): no IMU partial mean -> D1' and ``WARN_D1_IMU_INPUT_MISSING`` once."""
    bench = _Bench(_monitor())
    bench.ready_stay(load_N=HEAVY_LOAD_N)
    moved_N = 110.0 * BAR * HEAD_AREA[FL]
    load_N = HEAVY_LOAD_N.copy()
    for sign in (1.0, -1.0, 1.0):  # three redistribution steps, explained by the sum rule
        load_N = load_N + sign * np.array([-moved_N, moved_N, 0.0, 0.0])
        bench.read(*_pressures(load_N), f_z=None)
    assert bench.monitor.head_fault_legs == []
    assert bench.names.count("WARN_D1_IMU_INPUT_MISSING") == 1
    assert _steps(bench.names)[0] == "INFO_PRESSURE_STEP:FL:head:load_redistribution"


def test_a_new_ready_stay_replaces_m_eff_after_three_samples() -> None:
    bench = _Bench(_monitor(imu_mass_calibration="median"))
    bench.ready_stay()
    bench.read(*_pressures(LOAD_N))  # LEVEL
    heavier = LOAD_N * 1.2
    for count in range(1, 4):
        bench.read(*_pressures(heavier), locked=True)
        expected = BODY_MASS_KG if count < 3 else 1.2 * BODY_MASS_KG
        assert bench.monitor._imu_mass_kg == pytest.approx(expected)
        assert bench.monitor._imu_mass_estimate_kg() == pytest.approx(expected)


# --- M_eff options (dynamics rev. 41 R41-1; U-S8-36 keeps the READY median) -----------------


def test_nominal_mass_option_is_the_body_mass_and_needs_no_ready_stay() -> None:
    """``nominal`` (option, not the default): the superstructure mass given to the monitor
    (or ``imu_mass_nominal_kg``) from the first lifted period on."""
    monitor = _monitor(imu_mass_calibration="nominal")
    assert monitor._imu_mass_estimate_kg() == pytest.approx(38400.8366)
    settings = replace(TwoPressureSettings().with_r8_period(), imu_mass_calibration="nominal")
    bench = _Bench(TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN_N, PERIOD_S,
                                      settings=settings, body_mass_kg=BODY_MASS_KG))
    _bounce(bench)
    assert bench.monitor.head_fault_legs == []
    explicit = _monitor(imu_mass_calibration="nominal", imu_mass_nominal_kg=40000.0)
    assert explicit._imu_mass_estimate_kg() == 40000.0


def test_slope_mass_needs_samples_and_excitation_then_drops_the_preload() -> None:
    """R41-1 ``slope``: ``d sum F = M d f_z`` over lifted moving periods; a constant seal
    preload in the sum is an intercept and drops out (the READY median would keep it)."""
    bench = _Bench(_monitor(imu_mass_calibration="slope"))
    preload_N = 20e3
    rng = np.random.default_rng(5)
    command = np.full(4, 0.1 * V_MAX)
    assert bench.monitor._imu_mass_estimate_kg() is None
    for _ in range(60):
        f_z = GRAVITY_M_S2 + rng.normal(0.0, 0.1)
        bench.read(*_pressures((LOAD_N + preload_N / 4) * f_z / GRAVITY_M_S2),
                   f_z=f_z, command=command)
    mass_kg = bench.monitor._imu_mass_estimate_kg()
    assert mass_kg == pytest.approx(BODY_MASS_KG * (1 + preload_N / LOAD_N.sum()), rel=1e-6)
    quiet = _Bench(_monitor(imu_mass_calibration="slope"))
    for _ in range(60):
        quiet.read(*_pressures(LOAD_N), command=command)
    assert quiet.monitor._imu_mass_estimate_kg() is None  # no excitation


# --- P-S8-14 ⑤ gyro lever correction (U-S8-36, control rev. 49 219) ----------------------------

ROLL_ACCELERATION_RAD_S2 = 1.5
"""(f): roll angular acceleration; lever share ``M alpha r_y`` = 38.4 t x 1.5 x 0.881 m =
50.7 kN, above the 47.8 kN threshold of a 100.5 bar rear step."""


def _rear_step_with_roll_kick(gyro_bias_rad_s=(0.0, 0.0, 0.0), *, is_corrected=True,
                              has_gyro=True) -> _Bench:
    """(f): a physical +100.5 bar RL step (load moved from RR, sum unchanged) while the
    body starts to roll: the IMU at C1 reads ``f_z + (alpha x r)_z``."""
    bench = _Bench(_monitor(imu_lever_correction=is_corrected))
    still = np.tile(np.asarray(gyro_bias_rad_s, dtype=float), (2, 1))
    bench.ready_stay(load_N=HEAVY_LOAD_N, gyro=still if has_gyro else None)
    arm = bench.monitor._imu_lever_arm_m
    alpha = np.array([ROLL_ACCELERATION_RAD_S2, 0.0, 0.0])
    lever_z = alpha[0] * arm[1] - alpha[1] * arm[0]
    kicked = still.copy()
    kicked[-1] += alpha * IMU_GYRO_SAMPLE_PERIOD_S  # last 10 ms mean one interval later
    moved_N = 100.5 * BAR * HEAD_AREA[RL]
    load_N = HEAVY_LOAD_N + np.array([0.0, 0.0, moved_N, -moved_N])
    bench.read(*_pressures(load_N), f_z=GRAVITY_M_S2 + lever_z,
               gyro=kicked if has_gyro else None)
    return bench


def test_lever_arm_is_the_imu_mount_minus_the_centre_of_mass() -> None:
    assert _monitor()._imu_lever_arm_m == pytest.approx((-0.150, 0.881, -2.143), abs=1e-3)
    assert TwoPressureSettings().imu_lever_correction is True


def test_roll_kick_is_explained_only_with_the_lever_correction() -> None:
    """(f): corrected -> both rear steps explained (``imu_residual``); uncorrected -> both
    rear legs faulted by the 50.7 kN lever share."""
    corrected = _rear_step_with_roll_kick()
    assert corrected.monitor.head_fault_legs == []
    assert _steps(corrected.names) == ["INFO_PRESSURE_STEP:RL:head:imu_residual",
                                       "INFO_PRESSURE_STEP:RR:head:imu_residual"]
    uncorrected = _rear_step_with_roll_kick(is_corrected=False)
    assert uncorrected.monitor.head_fault_legs == [RL, RR]


def test_constant_gyro_bias_does_not_change_the_result() -> None:
    """(g): a constant bias cancels in the difference of the two partial means."""
    plain = _rear_step_with_roll_kick()
    biased = _rear_step_with_roll_kick(np.array([0.02, -0.01, 0.005]))
    assert biased.names == plain.names
    assert biased.monitor.head_fault_legs == plain.monitor.head_fault_legs == []


def test_missing_gyro_warns_once_and_judges_uncorrected() -> None:
    """(h): no gyro samples -> ``WARN_D1_IMU_GYRO_MISSING`` once and the D1'' judgement of
    the uncorrected ``f_z`` (the rev. 48 rule): the same events as with the correction off."""
    missing = _rear_step_with_roll_kick(has_gyro=False)
    off = _rear_step_with_roll_kick(is_corrected=False, has_gyro=False)
    for bench in (missing, off):  # a second judged step: the warning stays single
        head, rod = _pressures(HEAVY_LOAD_N)
        head[FL] += 101 * BAR
        bench.read(head, rod)
    assert missing.names.count("WARN_D1_IMU_GYRO_MISSING") == 1
    assert [name for name in missing.names if name != "WARN_D1_IMU_GYRO_MISSING"] == off.names
    assert missing.monitor.head_fault_legs == off.monitor.head_fault_legs == [FL, RL, RR]


def test_seal_ambiguity_band_is_not_accepted() -> None:
    """U-S8-36: no seal ambiguity band; the key exists with 0 only."""
    assert TwoPressureSettings().imu_seal_band_factor == 0.0
    with pytest.raises(ValueError, match="imu_seal_band_factor"):
        TwoPressureSettings(imu_seal_band_factor=2.0)


# --- D1'' rod side: lock_load_regain -----------------------------------------------------------


def _regain(bench, *, rod_after_bar=26.1, stroke_change_m=0.0):
    """ML17_ep4 FR 66.20 s: locked FR touches again, head 40.0 -> 80.4 bar, rod 143.7 ->
    26.1 bar (ratio 2.93), stroke 0.552 m still."""
    head, rod = _pressures(LOAD_N)
    head[FR], rod[FR] = 40.0 * BAR, 143.7 * BAR
    bench.read(head, rod)
    head_after, rod_after = head.copy(), rod.copy()
    head_after[FR], rod_after[FR] = 80.4 * BAR, rod_after_bar * BAR
    stroke = np.full(4, STROKE_M)
    stroke[FR] += stroke_change_m
    bench.read(head_after, rod_after, stroke=stroke)


def test_locked_leg_regaining_load_is_explained() -> None:
    bench = _Bench(_monitor())
    _regain(bench)
    assert bench.monitor.fallback_legs == []
    assert _steps(bench.names) == ["INFO_PRESSURE_STEP:FR:rod:lock_load_regain"]


@pytest.mark.parametrize(("changes", "stroke_change_m"), [
    ({"step_rule": "explained"}, 0.0),
    ({}, 1.5e-3),
    ({"regain_ratio_margin": 0.5}, 0.0),
], ids=["d1_prime", "stroke_moved", "ratio_above_band"])
def test_rod_fall_outside_lock_load_regain_is_a_fault(changes, stroke_change_m) -> None:
    """D1' keeps the fallback (217.5); a stroke change of 1.5 mm, or a ratio 2.91 above
    ``0.5 R_ub(0.552 m)`` = 2.15, is not the lock law."""
    bench = _Bench(_monitor(**changes))
    _regain(bench, stroke_change_m=stroke_change_m)
    assert bench.monitor.fallback_legs == [FR]
    assert "INFO_ROD_PRESSURE_FAULT_REASON:FR:D1" in bench.names


def test_regain_without_a_stroke_reading_is_a_fault() -> None:
    bench = _Bench(_monitor())
    head, rod = _pressures(LOAD_N)
    head[FR], rod[FR] = 40.0 * BAR, 143.7 * BAR
    bench.monitor.read(0.0, head, rod, STILL, False, 2e3, imu_specific_force_z_m_s2=9.8,
                       is_crawler_lifted=True)
    head[FR], rod[FR] = 80.4 * BAR, 26.1 * BAR
    bench.monitor.read(0.1, head, rod, STILL, False, 2e3, imu_specific_force_z_m_s2=9.8,
                       is_crawler_lifted=True)
    assert bench.monitor.fallback_legs == [FR]


# --- head fault reasons ------------------------------------------------------------------------


@pytest.mark.parametrize(("value", "reason"), [
    (math.nan, "D1_nonfinite"), (450 * BAR, "D1_range"), (-20 * BAR, "D1_range")])
def test_head_fault_reason_of_a_bad_reading(value, reason) -> None:
    bench = _Bench(_monitor())
    head, rod = _pressures(LOAD_N)
    head[FL] = value
    bench.read(head, rod)
    assert f"INFO_HEAD_PRESSURE_FAULT_REASON:FL:{reason}" in bench.names


def test_head_fault_reason_of_the_current_check() -> None:
    """Inside a widened pressure range but outside the 3.8-20.5 mA band (U72)."""
    bench = _Bench(_monitor(sensor_range_Pa=(-50 * BAR, 500 * BAR)))
    head, rod = _pressures(LOAD_N)
    head[FL] = -15 * BAR  # 3.4 mA on the 0-400 bar sensor
    bench.read(head, rod)
    assert "INFO_HEAD_PRESSURE_FAULT_REASON:FL:D1_current" in bench.names


def test_head_fault_reason_of_a_stuck_sensor() -> None:
    bench = _Bench(_monitor(pressure_noise_std_Pa=0.3 * BAR))
    head, rod = _pressures(LOAD_N)
    rng = np.random.default_rng(3)
    for _ in range(round(10.0 / PERIOD_S) + 1):
        noisy_head = head + rng.normal(0.0, 0.3 * BAR, 4)
        noisy_head[RR] = head[RR]
        bench.read(noisy_head, rod + rng.normal(0.0, 0.3 * BAR, 4))
    assert "INFO_HEAD_PRESSURE_FAULT_REASON:RR:D1_stuck" in bench.names


# --- settings and pickles ----------------------------------------------------------------------


def test_default_rule_and_meta_keys() -> None:
    settings = TwoPressureSettings()
    assert settings.step_rule is StepRule.EXPLAINED_IMU
    meta = settings.to_meta()
    assert meta["step_rule"] == "explained_imu" and set(IMU_RULE_META_KEYS) <= set(meta)
    for rule in ("explained", "jump"):
        assert not set(IMU_RULE_META_KEYS) & set(replace(settings, step_rule=rule).to_meta())
    meta = _monitor().meta()
    assert meta["d1_imu_mass_kg"] is None  # median: no READY stay yet
    assert meta["d1_imu_median_mass_kg"] is None and meta["d1_imu_slope_mass_kg"] is None
    # U-S8-36: READY median, lever correction on, no seal band, threshold 0.5.
    assert settings.imu_mass_calibration == "median" and settings.imu_lever_correction
    assert settings.imu_seal_band_factor == 0.0
    assert settings.imu_residual_step_ratio == 0.5
    assert "d1_imu_mass_kg" not in _monitor(step_rule="explained").meta()


def test_settings_pickled_before_p_s8_14_read_the_defaults() -> None:
    state = dict(TwoPressureSettings().with_r8_period().__dict__)
    for key in IMU_RULE_META_KEYS:
        del state[key]
    state["step_rule"] = StepRule.EXPLAINED  # what the ML rerun pickled
    old = object.__new__(TwoPressureSettings)
    old.__dict__.update(state)
    restored = pickle.loads(pickle.dumps(old))
    assert restored.step_rule is StepRule.EXPLAINED
    assert restored.imu_residual_step_ratio == 0.5 and restored.regain_ratio_margin == 1.4
    json.dumps(restored.to_meta())


def test_monitor_pickled_before_p_s8_14_runs_and_builds_m_eff() -> None:
    new = _monitor()
    bench = _Bench(new)
    bench.ready_stay(2)
    old = copy.deepcopy(new)
    for name in ("_imu_mass_ratios_kg", "_imu_mass_kg", "_previous_imu_f_z_m_s2",
                 "_was_locked_phase"):
        del old.__dict__[name]
    restored = pickle.loads(pickle.dumps(old))
    assert restored._imu_mass_kg is None and restored._previous_imu_f_z_m_s2 is None
    old_bench = _Bench(restored, t_s=bench.t_s)
    old_bench.ready_stay(3)
    assert restored._imu_mass_kg == pytest.approx(BODY_MASS_KG)
    json.dumps(restored.meta())


# --- record replays (07_results/S8, git-ignored) -----------------------------------------------

RESULTS = Path(__file__).resolve().parents[2] / "07_results" / "S8"
ML_BATCH = RESULTS / "ml_pilot_20261025_002044"
ML_OLD = ML_BATCH / "episodes" / "_replaced_20261025_015059"
RECORDED_EVENT = re.compile(r"t_s=([-0-9.e+]+), name='([^']+)'")


@dataclass
class Replay:
    """Monitor outputs of one replayed run."""

    t_s: np.ndarray
    events: list[tuple[float, str]]
    forces: np.ndarray
    """(n, 4, 4): nominal, lower, upper, head_only per period."""
    head_fault_legs: list[int]
    fallback_legs: list[int]

    @property
    def names(self) -> list[str]:
        return [name for _, name in self.events]


@dataclass(frozen=True)
class RunInputs:
    t_s: np.ndarray
    head_Pa: np.ndarray
    rod_Pa: np.ndarray
    stroke_m: np.ndarray
    commanded_m_s: np.ndarray
    band_N: np.ndarray
    phase: np.ndarray
    f_z_m_s2: np.ndarray
    gyro_rad_s: np.ndarray | None = None
    """``r8_series`` ``imu_gyro_samples`` (period x 10 x 3, rad/s, body axes; C-S8-31);
    ``None`` for records before it (the ML pilot)."""


def run_inputs(case: Path) -> RunInputs:
    with np.load(case / "r8_series.npz") as r8:
        t, issued, phase = r8["t"], r8["issued_u"], r8["phase"]
        # Older batches record the scalar band only, some no IMU samples (f_z NaN).
        band = (r8["leg_band_N"] if "leg_band_N" in r8.files
                else np.repeat(r8["F_band_N"][:, None], 4, axis=1))
        imu = (r8["imu_samples"] if "imu_samples" in r8.files
               else np.full((t.size, 1, 3), np.nan))
        gyro = r8["imu_gyro_samples"] if "imu_gyro_samples" in r8.files else None
    with np.load(case / "record" / "record.npz") as record:
        index = np.clip(np.searchsorted(record["t"], t - 1e-9), 0, record["t"].size - 1)
        head = record["meas.head_pressure"][index]
        rod = record["meas.rod_pressure"][index]
        stroke = record["meas.stroke"][index]
    commanded = np.vstack([np.zeros((1, 4)), issued[:-1]])
    band_before = np.vstack([band[:1], band[:-1]])
    phase_before = np.concatenate([[""], np.char.lower(phase[:-1].astype(str))])
    return RunInputs(t, head, rod, stroke, commanded, band_before, phase_before,
                     imu[:, -1, 2], gyro)


def case_settings(case: Path, step_rule: str) -> TwoPressureSettings:
    settings = replace(TwoPressureSettings().with_r8_period(), step_rule=step_rule)
    meta = json.loads((case / "record" / "meta.json").read_text(encoding="utf-8"))
    s8 = meta["run"]["engine"]["actuator"].get("s8") or {}
    if s8.get("lock_valve") != "counterbalance":
        return settings
    params = SimpleNamespace(**s8["counterbalance"]["params"])
    return settings.with_lock_valve("counterbalance", params)


@cache
def _branch_monitor(base: str) -> TwoPressureMonitor:
    with open(ML_BATCH / "bases" / base / "branch.pkl", "rb") as handle:
        blob = pickle.load(handle)  # noqa: S301 - own batch file
    controller = blob["controller"]
    return getattr(controller, "inner", controller)._pressures


def start_monitor(case: Path, settings: TwoPressureSettings):
    """(monitor, zero calibration (t_end_s, offsets) still to apply or ``None``)."""
    result = json.loads((case / "result.json").read_text(encoding="utf-8"))
    base = result.get("base")
    if isinstance(base, str):  # an episode names its base; a base run stores a dict
        monitor = copy.deepcopy(_branch_monitor(base))
        monitor.refresh_settings(settings)
        return monitor, None
    controller = result["controller_meta"]
    meta = controller["two_pressure"]
    monitor = TwoPressureMonitor(
        meta["head_area_m2"], meta["annulus_area_m2"], controller["geometry"]["max_speed_m_s"],
        controller["geometry"]["F_min_N"], controller["period_s"],
        LoadEstimate(meta["load_estimate"]), settings, meta["rod_weight_N"],
        stroke_max_m=controller["geometry"]["stroke_max_m"])
    calibration = controller.get("zero_calibration") or {}
    end_s = (calibration.get("result") or {}).get("t_end_s")
    if end_s is None:
        monitor.set_zero_offsets_N(meta["zero_offsets_N"])
        return monitor, None
    return monitor, (end_s, calibration["offsets_N"])


def read_period(monitor, inputs: RunInputs, k: int, head_Pa=None):
    """One monitor read of period ``k`` (``head_Pa`` replaces the recorded head reading)."""
    return monitor.read(
        inputs.t_s[k], inputs.head_Pa[k] if head_Pa is None else head_Pa, inputs.rod_Pa[k],
        inputs.commanded_m_s[k], inputs.phase[k] == "ready", inputs.band_N[k],
        stroke_m=inputs.stroke_m[k],
        imu_specific_force_z_m_s2=float(inputs.f_z_m_s2[k]),
        is_crawler_lifted=inputs.phase[k] in LIFTED_PHASES,
        imu_gyro_rad_s=None if inputs.gyro_rad_s is None else inputs.gyro_rad_s[k])


def replay(case: Path, step_rule: str) -> Replay:
    inputs = run_inputs(case)
    monitor, calibration = start_monitor(case, case_settings(case, step_rule))
    events, forces = [], []
    for k in range(inputs.t_s.size):
        out = read_period(monitor, inputs, k)
        forces.append(np.stack([out.nominal, out.lower, out.upper, out.head_only]))
        events += [(float(inputs.t_s[k]), name) for name, _ in monitor.pop_events()]
        if calibration is not None and inputs.t_s[k] >= calibration[0] - 1e-9:
            monitor.set_zero_offsets_N(calibration[1])
            calibration = None
    return Replay(inputs.t_s, events, np.array(forces), monitor.head_fault_legs,
                  monitor.fallback_legs)


def recorded_sensor_faults(case: Path) -> list[str]:
    """Pressure fault events the run's controller recorded after its branch (in order)."""
    result = json.loads((case / "result.json").read_text(encoding="utf-8"))
    branch_s = float(result.get("branch_t_s") or -math.inf)
    lines = json.loads((case / "controller_events.json").read_text(encoding="utf-8"))
    names = []
    for line in lines:
        t_s, name = RECORDED_EVENT.search(line).groups()
        if float(t_s) > branch_s + 1e-6 and "PRESSURE" in name:
            names.append(name)
    return _faults(names)


def _ml_runs() -> list[Path]:
    if not ML_BATCH.is_dir():
        return []
    episodes = sorted(path for path in (ML_BATCH / "episodes").glob("ML*") if path.is_dir())
    return sorted((ML_BATCH / "bases").glob("ML*")) + episodes


ML_RUNS = _ml_runs()
HEAD_STEP_EPISODES = {
    "ML00_ep5": [], "ML08_ep4": [], "ML18_ep6": [], "ML21_ep1": [],
    "ML10_ep4": ["FAULT_HEAD_PRESSURE:FR"],
    "ML11_ep4": ["FAULT_HEAD_PRESSURE:FR"],
    "ML17_ep4": ["WARN_ROD_PRESSURE_FALLBACK:FR", "INFO_ROD_PRESSURE_FAULT_REASON:FR:D1",
                 "FAULT_HEAD_PRESSURE:FR"],
}
"""218.7 / C-S8-28: the seven rerun episodes with a head step above 100 bar and the sensor
faults the D1' run recorded (218.2, 218.3)."""
OLD_EPISODES = ("ML00_ep5", "ML02_ep1", "ML02_ep5", "ML22_ep4")
"""217.2: the four episodes of the first ML run with D1 faults (``_replaced_*``)."""


@pytest.mark.skipif(not ML_RUNS, reason="07_results/S8 ML pilot not present")
@pytest.mark.parametrize("episode", sorted(HEAD_STEP_EPISODES))
def test_rerun_head_step_episodes_d1_prime_replay_matches_the_record(episode) -> None:
    """Replay fidelity: the D1' monitor reproduces the recorded sensor faults."""
    case = ML_BATCH / "episodes" / episode
    replayed = replay(case, "explained")
    names = [name for name in _faults(replayed.names)
             if not name.startswith("INFO_HEAD_PRESSURE_FAULT_REASON")]
    assert names == recorded_sensor_faults(case) == HEAD_STEP_EPISODES[episode]


@pytest.mark.skipif(not ML_RUNS, reason="07_results/S8 ML pilot not present")
@pytest.mark.parametrize("episode", sorted(HEAD_STEP_EPISODES))
def test_rerun_head_step_episodes_have_no_fault_with_d1_double_prime(episode) -> None:
    """218.15 (a): no head fault, no rod fallback; every head step above 100 bar is an
    ``INFO_PRESSURE_STEP`` (ML17_ep4 FR rod: ``lock_load_regain``)."""
    replayed = replay(ML_BATCH / "episodes" / episode, "explained_imu")
    assert _faults(replayed.names) == []
    head_steps = [name for name in _steps(replayed.names) if ":head:" in name]
    assert head_steps
    if episode == "ML17_ep4":
        assert "INFO_PRESSURE_STEP:FR:rod:lock_load_regain" in replayed.names


@pytest.mark.skipif(not ML_OLD.is_dir(), reason="07_results/S8 old ML episodes not present")
@pytest.mark.parametrize("episode", OLD_EPISODES)
def test_old_d1_episodes_have_no_fault_with_d1_double_prime(episode) -> None:
    replayed = replay(ML_OLD / episode, "explained_imu")
    assert _faults(replayed.names) == []


def _detects(monitor, head, rod, imu_input, leg) -> bool:
    """Whether the monitor's D1 would fault ``leg`` on this period's readings, without
    changing the monitor (events and warnings rolled back)."""
    events, reported = len(monitor._events), set(monitor._reported)
    faults = monitor._sensor_fault_reasons(head)
    steps, _ = monitor._pressure_steps(head, rod, faults, {})
    unexplained = monitor._unexplained_head_steps(steps, head, rod, imu_input)
    del monitor._events[events:]
    monitor._reported = reported
    return leg in faults or leg in unexplained


@pytest.mark.skipif(not ML_RUNS, reason="07_results/S8 ML pilot not present")
def test_injected_head_jumps_are_detected_at_least_as_often_as_with_d1_prime() -> None:
    """218.15 (c) on the seven head-step episodes: a persistent jump of +-100 / +-150 bar on
    any leg after the event (not in FAULT) is flagged by the default D1'' at least as often
    as by the D1' sum rule (full 192-episode table in the P-S8-14 report)."""
    counts = {}
    for episode in HEAD_STEP_EPISODES:
        case = ML_BATCH / "episodes" / episode
        event_s = float(json.loads((case / "result.json").read_text(encoding="utf-8"))[
            "event_t_s"])
        inputs = run_inputs(case)
        with np.load(case / "r8_series.npz") as r8:
            phase_now = np.char.lower(r8["phase"].astype(str))
        monitor, _ = start_monitor(case, case_settings(case, "explained_imu"))
        for k in range(inputs.t_s.size):
            if (monitor._previous is not None and inputs.t_s[k] >= event_s
                    and phase_now[k] != "fault"):
                physical = inputs.head_Pa[k] - monitor._previous[0]
                f_z = float(inputs.f_z_m_s2[k])
                lifted = inputs.phase[k] in LIFTED_PHASES
                for jump_bar in (100.0, -100.0, 150.0, -150.0):
                    for leg in range(4):
                        if abs(physical[leg] + jump_bar * BAR) <= 100 * BAR:
                            continue
                        head = inputs.head_Pa[k].copy()
                        head[leg] += jump_bar * BAR
                        row = counts.setdefault(jump_bar, [0, 0])
                        gyro = None if inputs.gyro_rad_s is None else inputs.gyro_rad_s[k]
                        sum_rule = monitor._imu_input(f_z, False, gyro)
                        imu_rule = monitor._imu_input(f_z, lifted, gyro)
                        row[0] += _detects(monitor, head, inputs.rod_Pa[k], sum_rule, leg)
                        row[1] += _detects(monitor, head, inputs.rod_Pa[k], imu_rule, leg)
            read_period(monitor, inputs, k)
            monitor.pop_events()
    assert set(counts) == {100.0, -100.0, 150.0, -150.0}
    for d1_prime, d1_double_prime in counts.values():
        assert d1_double_prime >= d1_prime


def _one_base_per_level() -> list[Path]:
    """The first ML pilot base of each auger level (``case.json`` ``settings.base.level``)."""
    picked = {}
    for case in sorted((ML_BATCH / "bases").glob("ML*")) if ML_BATCH.is_dir() else []:
        level = json.loads((case / "case.json").read_text(encoding="utf-8"))[
            "settings"]["base"]["level"]
        picked.setdefault(level, case)
    return [picked[level] for level in sorted(picked)]


@pytest.mark.parametrize("base", _one_base_per_level(), ids=lambda path: path.name)
def test_restored_branch_gets_the_lever_arm_of_its_auger_level(base) -> None:
    """C-S8-31 (3): a ``branch.pkl`` written before P-S8-14 ⑤ lacks
    ``C2Geometry.imu_lever_arm_m`` and the monitor's ``_imu_lever_arm_m``; the ML runner's
    ``refresh_restored_controller`` copies them from the fresh controller of the case's
    params, i.e. IMU mount C1 minus the centre of mass of the base's auger level."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "04_scripts" / "02_chrono"))
    import run_S8C

    from outrigger_sim.control.c2 import C2Config, C2Controller
    from outrigger_sim.params import load_params
    from outrigger_sim.sensors.imu import IMU_MOUNT_C1_BODY_M

    with open(base / "branch.pkl", "rb") as handle:
        blob = pickle.load(handle)  # noqa: S301 - own batch file
    restored = getattr(blob["controller"], "inner", blob["controller"])
    assert "_imu_lever_arm_m" not in vars(restored._pressures)
    level = json.loads((base / "case.json").read_text(encoding="utf-8"))[
        "settings"]["base"]["level"]
    params = load_params(level=level)
    fresh = C2Controller.from_params(params, C2Config().with_10hz_d1())
    run_S8C.refresh_restored_controller(restored, fresh)
    expected = np.array(IMU_MOUNT_C1_BODY_M) - np.array(params.superstructure.mass_properties.com_m)
    np.testing.assert_allclose(restored.geometry.imu_lever_arm_m, expected, rtol=0, atol=1e-12)
    np.testing.assert_allclose(restored._pressures._imu_lever_arm_m, expected, rtol=0,
                               atol=1e-12)
    top = np.array(IMU_LEVER_ARM_TOP_M)
    assert (level == "top") is bool(np.allclose(expected, top))


IMU_LEVER_ARM_TOP_M = (0.31 - 0.460190503, 0.88 + 0.00136232581, 0.040 - 2.18347069)


@pytest.mark.skipif(not ML_RUNS, reason="07_results/S8 ML pilot not present")
def test_all_ml_pilot_runs_have_no_sensor_fault_and_match_d1_prime_elsewhere() -> None:
    """218.15 (a) / (b): the 216 runs of the pilot (24 bases, 192 rerun episodes) replay
    without a head fault or a rod fallback under D1''; every run without a D1' fault reads
    the same forces bit for bit under both rules."""
    faulty, differing = [], []
    for case in ML_RUNS:
        imu = replay(case, "explained_imu")
        if _faults(imu.names):
            faulty.append(case.name)
        sum_rule = replay(case, "explained")
        if not _faults(sum_rule.names) and not np.array_equal(imu.forces, sum_rule.forces):
            differing.append(case.name)
    assert len(ML_RUNS) == 216
    assert faulty == []
    assert differing == []
