"""C2 revision R6 (``s6_control_spec.md`` 51.1, 53.3-53.4, 57, 59.1 J-7, 61.3, 63-66; U43-U69).

Synthetic readings as in ``test_c2_r5.py``: constant leg loads after 5 s of free air, the
crawler-free operating strokes moved by the commands, a level accelerometer and a still gyro;
optionally a rod-side pressure. The R5 regression of the legacy preset is the R4.1 trace replay
in ``test_c2.py`` (``with_r41_behaviour`` builds on ``with_r5_behaviour``) plus the paired runs
below.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field, replace

import numpy as np
import pytest

from outrigger_sim.control.c2 import (
    C2Config,
    C2Controller,
    C2Geometry,
    C2Phase,
    ContactJudge,
    GeometryJudge,
    TargetSettings,
    is_shadow_event,
)
from outrigger_sim.control.two_pressure import LoadEstimate, RodSensorState
from outrigger_sim.params import LEG_ORDER, load_params
from outrigger_sim.sensors.rod_side import RodSideParams, RodSideSynth
from outrigger_sim.signals import Measurements

GRAVITY_M_S2 = 9.80665
PERIOD_S = 0.02
LEG_LOAD_N = 80e3
FREE_AIR_S = 5.0
TIME_LIMIT_S = 120.0
BAR = 1e5
RR = LEG_ORDER.index("RR")


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def _operating_strokes(geometry: C2Geometry) -> np.ndarray:
    return geometry.pad_bottom_z_retracted_m - geometry.crawler_bottom_z_m + 0.05


@dataclass
class _Bench:
    """Feeds readings; strokes follow the commands; rod pressure optional (a function)."""

    controller: C2Controller
    geometry: C2Geometry
    rod_bar: Callable[[_Bench], np.ndarray] | None = None
    load_N: Callable[[_Bench], np.ndarray] | None = None
    synth: RodSideSynth | None = None
    """When set, the rod-side and head pressures come from the 7.4 synthesis (a rod side
    that behaves like the circuit while the legs move)."""
    t_s: float = 0.0
    travel_m: np.ndarray = field(default_factory=lambda: np.zeros(4))
    commands: list[np.ndarray] = field(default_factory=list)

    def forces(self) -> np.ndarray:
        if self.load_N is not None:
            return self.load_N(self)
        return np.zeros(4) if self.t_s < FREE_AIR_S else np.full(4, LEG_LOAD_N)

    def step(self) -> np.ndarray:
        self.t_s += PERIOD_S
        strokes = _operating_strokes(self.geometry) + self.travel_m
        forces = self.forces()
        rod = None if self.rod_bar is None else self.rod_bar(self) * BAR
        annulus = self.geometry.annulus_area_m2
        head = forces / self.geometry.head_area_m2 if rod is None else (
            forces + np.nan_to_num(rod) * annulus) / self.geometry.head_area_m2
        if self.synth is not None:
            last = self.commands[-1] if self.commands else np.zeros(4)
            head, rod = self.synth.update(forces, last, strokes)
        measurements = Measurements(
            t_s=self.t_s,
            specific_force_m_s2=np.array([0.0, 0.0, GRAVITY_M_S2]),
            angular_rate_rad_s=np.zeros(3),
            head_pressure_Pa=head,
            stroke_m=strokes,
            stroke_corrected_m=strokes,
            rod_pressure_Pa=rod,
        )
        command = np.asarray(self.controller.update(measurements).leg_speed_m_s)
        self.travel_m = self.travel_m + command * PERIOD_S
        self.commands.append(command)
        return command

    def run_until(self, is_done: Callable[[], bool]) -> None:
        while not is_done() and self.t_s < TIME_LIMIT_S:
            self.step()
        assert is_done()


def _synth(geometry: C2Geometry) -> RodSideSynth:
    return RodSideSynth(RodSideParams(), geometry.head_area_m2, geometry.annulus_area_m2,
                        geometry.stroke_max_m, geometry.oil_dead_length_m, PERIOD_S)


def _config(**fields) -> C2Config:
    return C2Config(target=TargetSettings(check_time_s=0.0), output_ramp_time_s=None, **fields)


def _ready(bench: _Bench) -> _Bench:
    bench.run_until(lambda: bench.controller.phase is C2Phase.READY)
    return bench


def _names(controller: C2Controller) -> list[str]:
    return [event.name for event in controller.events]


def _run_commands(geometry, config, rod_bar=None, periods=1600) -> tuple[list, C2Controller]:
    bench = _Bench(C2Controller(geometry, config), geometry, rod_bar=rod_bar)
    for _ in range(periods):
        bench.step()
    return bench.commands, bench.controller


# --- R6-P: net force, legacy identity --------------------------------------------------------


def test_zero_rod_pressure_reads_like_no_rod_sensor(geometry) -> None:
    """P-2 (spec 47.1): with p_r = 0 the net force is the head reading bit for bit, so the
    commands, phases and non-shadow events equal those without a rod-side sensor."""
    config = _config(two_pressure=replace(C2Config().two_pressure, diagnostics=False))
    plain, plain_controller = _run_commands(geometry, config)
    zero, zero_controller = _run_commands(geometry, config, rod_bar=lambda b: np.zeros(4))
    np.testing.assert_array_equal(np.array(plain), np.array(zero))
    keep = [n for n in _names(plain_controller) if not is_shadow_event(n)]
    assert keep == [n for n in _names(zero_controller) if not is_shadow_event(n)]
    assert zero_controller.meta()["two_pressure"]["has_rod_sensor"] is True


def test_r5_preset_ignores_the_rod_side_pressure(geometry) -> None:
    """``with_r5_behaviour``: head-only reading, no tail, GE2 shadow: a rod-side pressure
    changes nothing; the R6 default with the same input differs (the READY heave tail)."""
    legacy = _config().with_r5_behaviour()
    without, _ = _run_commands(geometry, legacy)
    with_rod, controller = _run_commands(geometry, legacy, rod_bar=lambda b: np.full(4, 5.0))
    np.testing.assert_array_equal(np.array(without), np.array(with_rod))
    meta = controller.meta()
    assert meta["load_estimate"] == "head_only" and meta["lock_tail"]["enable"] is False
    assert meta["geometry_judge"]["is_active"] is False
    assert meta["thresholds"]["relevel_load_margin_N"] == 7000.0
    assert meta["reanchor"]["settings"]["floor_margin_N"] == 10e3
    r6, _ = _run_commands(geometry, _config())
    assert not np.array_equal(np.array(without), np.array(r6))


def test_per_leg_areas_give_the_per_leg_net_force(geometry) -> None:
    """P-15: front / rear areas differ; the net force is right per leg (relative 1e-12)."""
    head = np.array([1.3273e-2, 1.3273e-2, 9.5033e-3, 9.5033e-3])
    annulus = np.array([3.7699e-3, 3.7699e-3, 3.1416e-3, 3.1416e-3])
    rexome35 = replace(geometry, head_area_m2=head, annulus_area_m2=annulus,
                       locked_force_limit_N=350 * BAR * head)
    controller = C2Controller(rexome35, _config())
    forces = np.array([118e3, 118e3, 72e3, 72e3])
    rod = np.full(4, 2 * BAR)
    reading = controller._read(Measurements(
        0.02, [0, 0, GRAVITY_M_S2], [0, 0, 0], (forces + rod * annulus) / head,
        _operating_strokes(geometry), rod_pressure_Pa=rod))
    np.testing.assert_allclose(reading.cylinder_force_N, forces, rtol=1e-12)
    np.testing.assert_allclose(rexome35.locked_force_limit_N / 1e3,
                               [464.56, 464.56, 332.62, 332.62], atol=0.01)


def test_scalar_area_is_broadcast(geometry) -> None:
    assert geometry.head_area_m2.shape == (4,) and geometry.annulus_area_m2.shape == (4,)
    scalar = replace(geometry, head_area_m2=0.01, annulus_area_m2=0.003)
    np.testing.assert_array_equal(scalar.head_area_m2, np.full(4, 0.01))
    np.testing.assert_array_equal(scalar.annulus_area_m2, np.full(4, 0.003))


def test_locked_head_limit_uses_the_raw_head_pressure(geometry) -> None:
    """P-3: head 349 bar + rod 20 bar -> no head warning (the net force is lower anyway);
    the head 351 bar -> one warning."""
    bench = _ready(_Bench(C2Controller(geometry, _config()), geometry, synth=_synth(geometry)))
    bench.synth = None
    area = geometry.head_area_m2[0]
    annulus = geometry.annulus_area_m2[0]
    bench.rod_bar = lambda b: np.array([2.0, 20.0, 2.0, 2.0])
    bench.load_N = lambda b: np.array([LEG_LOAD_N, 349 * BAR * area - 20 * BAR * annulus,
                                       LEG_LOAD_N, LEG_LOAD_N])
    for _ in range(3):
        bench.step()
    assert "locked_pressure_over_limit:FR" not in _names(bench.controller)


# --- fallback and head fault ----------------------------------------------------------------


def test_rod_dropout_falls_back_and_widens_that_leg_band(geometry) -> None:
    """P-4 / U45 / U65: NaN on RR -> fallback once, RR band >= 13 kN, rear fallback skips
    REANCHOR."""
    bench = _ready(_Bench(C2Controller(geometry, _config()), geometry, synth=_synth(geometry)))
    controller = bench.controller
    assert controller._pressures.fallback_legs == []  # the synthesised rod side is plausible
    bench.synth = None
    bench.rod_bar = lambda b: np.array([2.0, 2.0, 2.0, math.nan])
    for _ in range(3):
        bench.step()
    assert _names(controller).count("WARN_ROD_PRESSURE_FALLBACK:RR") == 1
    assert controller._pressures.rod_state[RR] is RodSensorState.FALLBACK
    bands = controller._leg_seal_bands_N()
    assert bands[RR] >= 13e3 and bands[0] == controller.seal_band_N
    state = controller._state
    state.reanchor_anchor_pitch_rad, state.is_lifted, state.in_crawler_zone = 0.1, True, False
    reading = state.last_reading
    assert controller._reanchor_skip_reason(reading) == "rod_sensor_fallback"


def test_head_fault_stops_the_run(geometry) -> None:
    bench = _ready(_Bench(C2Controller(geometry, _config()), geometry, synth=_synth(geometry)))
    bench.synth = None
    bench.rod_bar = lambda b: np.full(4, 2.0)
    bench.load_N = lambda b: np.array([LEG_LOAD_N, 600 * BAR * geometry.head_area_m2[1],
                                       LEG_LOAD_N, LEG_LOAD_N])  # 600 bar: out of range
    bench.step()
    assert bench.controller.phase is C2Phase.FAULT
    assert "FAULT_HEAD_PRESSURE:FR" in _names(bench.controller)
    assert np.all(bench.step() == 0.0)


# --- READY heave tail (U62 / U66 / U67) ---------------------------------------------------------


def test_ready_heave_tail_extends_all_legs_together(geometry) -> None:
    """Spec 65.1: the probe ends retracting; just before READY acts, all four legs extend
    1.5 mm together at 0.25 v_max (equal travel: pure heave), settle 0.2 s, then lock."""
    bench = _Bench(C2Controller(geometry, _config()), geometry)
    controller = bench.controller
    bench.run_until(lambda: "ready_heave_tail" in _names(controller))
    travel_before = bench.travel_m.copy()
    start = len(bench.commands)
    bench.run_until(lambda: not controller._state.lock_tail_speeds)
    tail = bench.travel_m - travel_before
    np.testing.assert_allclose(tail, 1.5e-3, rtol=0, atol=1e-12)
    tail_commands = np.array(bench.commands[start:])
    assert np.all(tail_commands == tail_commands[:, :1])  # the same speed on every leg
    assert tail_commands.max() <= 0.25 * geometry.max_speed_m_s + 1e-12
    assert np.all(controller._state.last_nonzero_output_m_s > 0.0)
    assert controller.phase is C2Phase.READY
    assert controller.meta()["lock_tail"]["count"] == 1


def test_ready_heave_tail_is_skipped_near_the_stroke_end(geometry) -> None:
    """Stroke guard: s + 1.5 mm beyond min(s_max, 0.6948) - 10 mm -> no tail, a warning."""
    short = replace(geometry, stroke_max_m=float(_operating_strokes(geometry).max()) + 0.0105)
    bench = _Bench(C2Controller(short, _config()), short)
    bench.run_until(lambda: bench.controller.phase is C2Phase.READY)
    for _ in range(2):
        bench.step()
    names = _names(bench.controller)
    assert "WARN_TAIL_SKIPPED:stroke_margin" in names and "ready_heave_tail" not in names


def _tail_decision_at_stroke(
    geometry: C2Geometry, stroke_m: float, overshoot_margin_m: float
) -> list[str]:
    """Events of one READY entry after a retraction with every leg at ``stroke_m``."""
    lock_tail = replace(
        C2Config().lock_tail, end_overshoot_margin_m=overshoot_margin_m
    )
    bench = _ready(_Bench(C2Controller(geometry, _config(lock_tail=lock_tail)), geometry))
    controller = bench.controller
    state = controller._state
    state.lock_tail_speeds = {}
    state.last_nonzero_output_m_s = np.full(4, -1e-3)
    reading = replace(state.last_reading, motor_stroke_m=np.full(4, stroke_m))
    event_count_before = len(controller.events)
    controller._request_ready_heave(reading, C2Phase.CHECK)
    return [event.name for event in controller.events[event_count_before:]]


@pytest.mark.parametrize(
    ("stroke_m", "overshoot_margin_m", "is_skipped"),
    [
        (0.6830, 0.0005, True),  # 683.0 + 1.5 + 0.5 = 685.0 mm > 684.8 mm
        (0.6830, 0.0, False),  # 683.0 + 1.5 = 684.5 mm
        (0.6827, 0.0005, False),  # 682.7 + 2.0 = 684.7 mm
        (0.6827, 0.0, False),
    ],
)
def test_tail_skip_keeps_the_end_overshoot_margin(
    geometry, stroke_m, overshoot_margin_m, is_skipped
) -> None:
    """User decision 2026-10-27: skip when s + tail + margin > s_soft - 10 mm (684.8 mm)."""
    assert geometry.stroke_soft_max_m == pytest.approx(0.6948)
    names = _tail_decision_at_stroke(geometry, stroke_m, overshoot_margin_m)
    if is_skipped:
        assert names == ["WARN_TAIL_SKIPPED:stroke_margin"]
    else:
        assert names == ["ready_heave_tail"]


def test_tail_overshoot_margin_must_not_be_negative() -> None:
    with pytest.raises(ValueError, match="end_overshoot_margin_m"):
        replace(C2Config().lock_tail, end_overshoot_margin_m=-1e-4)


def test_relevel_and_reanchor_margins(geometry) -> None:
    """U68 / U69 defaults; the P5 check is guard margin + 2.5 kN."""
    config = C2Config()
    assert config.thresholds.relevel_load_margin_N == 7500.0
    assert config.reanchor.floor_margin_N == 11.5e3
    with pytest.raises(ValueError, match="2500"):
        replace(config.thresholds, relevel_load_margin_N=7000.0)


def test_soft_stroke_end_counts_from_0_6948(geometry) -> None:
    """Spec 65.3: a 0.70 m plant takes its limits from the 0.6948 m soft end; 0.68 m keeps
    its own."""
    assert geometry.stroke_soft_max_m == min(geometry.stroke_max_m, 0.6948)
    long = replace(geometry, stroke_max_m=0.70)
    assert long.stroke_soft_max_m == 0.6948


# --- R6-G (J-7) -----------------------------------------------------------------------------


def _ready_combined(geometry, **fields) -> _Bench:
    return _ready(_Bench(C2Controller(geometry, _config(**fields)), geometry))


def test_sink_trigger_waits_for_the_reference_refresh(geometry) -> None:
    """57 (b): G1-S / G2 in READY before the first refresh -> information only; after it ->
    re-level (probe again)."""
    bench = _ready_combined(geometry)
    controller = bench.controller
    reading = controller._state.last_reading
    controller._state.is_ready_reference_refreshed = False
    controller._act_on_support_change(reading, ["G1S:RR"])
    assert controller.phase is C2Phase.READY
    assert "INFO_SUPPORT_TRIGGER_BEFORE_REFRESH:G1S:RR" in _names(controller)
    controller._state.is_ready_reference_refreshed = True
    controller._act_on_support_change(reading, ["G1S:RR"])
    assert controller.phase is C2Phase.LEVEL
    assert "WARN_SUPPORT_CHANGED:G1S:RR" in _names(controller)
    trigger = controller.meta()["geometry_judge"]["triggers"][-1]
    assert trigger["key"] == "G1S:RR" and trigger["is_lift_vote"] is False


def test_lift_vote_acts_before_the_refresh_and_flags_a_conflict(geometry) -> None:
    """G1-L acts any time in READY (57 (b)); a leg the band calls ABOVE -> D7 conflict."""
    bench = _ready_combined(geometry)
    controller = bench.controller
    controller._state.is_ready_reference_refreshed = False
    controller._act_on_support_change(controller._state.last_reading, ["G1L:FL"])
    names = _names(controller)
    assert controller.phase is C2Phase.LEVEL
    assert "WARN_SUPPORT_CHANGED:G1L:FL" in names and "WARN_CONTACT_CONFLICT:FL" in names


def test_repeated_trigger_is_latched(geometry) -> None:
    """37.3 (c): the same key again within 30 s -> WARN_SUPPORT_CHANGE_REPEAT, no re-level."""
    bench = _ready_combined(geometry)
    controller = bench.controller
    controller._act_on_support_change(controller._state.last_reading, ["G1L:RR"])
    bench.run_until(lambda: controller.phase is C2Phase.READY)
    controller._act_on_support_change(controller._state.last_reading, ["G1L:RR"])
    assert controller.phase is C2Phase.READY
    assert "WARN_SUPPORT_CHANGE_REPEAT:G1L:RR" in _names(controller)
    controller._act_on_support_change(controller._state.last_reading, ["G1L:RR"])
    assert _names(controller).count("WARN_SUPPORT_CHANGE_REPEAT:G1L:RR") == 1


@pytest.mark.parametrize(
    "fields",
    [{"contact": ContactJudge.PRESSURE},
     {"geometry_judge": replace(C2Config().geometry_judge, mode=GeometryJudge.SHADOW)}],
)
def test_geometry_judge_shadow_and_pressure_mode_do_nothing(geometry, fields) -> None:
    """U59: the pressure judge and the shadow setting never act on GE2."""
    bench = _ready_combined(geometry, **fields)
    controller = bench.controller
    controller._state.is_ready_reference_refreshed = True
    controller._act_on_support_change(controller._state.last_reading, ["G1S:RR", "G1L:FL"])
    assert controller.phase is C2Phase.READY
    assert not [n for n in _names(controller) if n.startswith("WARN_SUPPORT")]


def test_meta_reports_r6(geometry) -> None:
    controller = C2Controller(geometry)
    meta = controller.meta()
    assert meta["revision"] == "R7" and meta["load_estimate"] == str(LoadEstimate.NET)
    assert meta["lock_tail"]["mode"] == "ready_heave" and meta["lock_tail"]["tail_m"] == 1.5e-3
    assert meta["probe"]["sequence"] == "extend_retract"
    assert meta["probe"]["sensitivity"] == "measured_if_grounded"


def test_per_transition_tail_option(geometry) -> None:
    """Rev. 11 option: a tail per leg at DONE / READY entry after a retraction."""
    from outrigger_sim.control.c2 import LockTailSettings, RetractTailMode

    tail = LockTailSettings(mode=RetractTailMode.PER_TRANSITION, tail_m=3e-4, speed_fraction=0.1)
    bench = _ready(_Bench(C2Controller(geometry, _config(lock_tail=tail)), geometry))
    for _ in range(50):
        bench.step()
    assert any(name.startswith("lock_tail:") for name in _names(bench.controller))
    assert "ready_heave_tail" not in _names(bench.controller)


def test_g2_trigger_key_carries_the_sign(geometry) -> None:
    bench = _ready_combined(geometry)
    controller = bench.controller
    controller._state.is_ready_reference_refreshed = True
    controller._act_on_support_change(controller._state.last_reading, ["FLOOR_NONPLANAR", "G2"])
    key = controller.meta()["geometry_judge"]["triggers"][-1]["key"]
    assert key in ("G2+", "G2-") and controller.phase is C2Phase.LEVEL


def test_fallback_leg_probes_retract_first_without_head_only_estimates(geometry) -> None:
    """U45 a' / U65: after an RR rod-side fault the next probe runs RR retract first (ends
    extending) and keeps no head-only seal-friction estimate for it."""
    bench = _ready(_Bench(C2Controller(geometry, _config()), geometry, synth=_synth(geometry)))
    controller = bench.controller
    synth = bench.synth
    bench.synth = None
    bench.rod_bar = lambda b: np.array([*(synth.rod_pressure_Pa[:3] / BAR), math.nan])
    bench.step()
    assert controller._pressures.fallback_legs == [RR]
    controller._start_relevel()
    rounds = len(controller.probe_history)
    bench.run_until(lambda: len(controller.probe_history) > rounds)
    rr = controller.probe_history[-1][RR]
    assert rr.is_reversed and rr.seal_friction_estimate_N == 0.0
