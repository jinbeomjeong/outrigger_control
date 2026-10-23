"""``sensors/rod_side``: rod-side pressure synthesis (rod_side_pressure.md 7.4) and the
two-pressure force helper (R6-P P-14)."""

from __future__ import annotations

import numpy as np
import pytest

from outrigger_sim.sensors.rod_side import (
    ForceEstimate,
    RodSideParams,
    RodSideSynth,
    cylinder_force_from_pressures,
)

BAR = 1e5
HEAD_AREA = 1.0387e-2  # the 7.4 worked examples use the YAML cylinder
ANNULUS = 8.836e-4
STROKE_MAX = 0.68
DEAD = 0.05
PERIOD_S = 0.02


def _synth(**params) -> RodSideSynth:
    return RodSideSynth(RodSideParams(**params), HEAD_AREA, ANNULUS, STROKE_MAX, DEAD, PERIOD_S)


def test_locked_after_extension_reads_the_back_pressure() -> None:
    """7.4 check: grounded front leg locked after an extension, 118.25 kN -> p_r 2.0,
    p_h 114.0 bar; the two-sensor force equals F_cyl."""
    synth = _synth()
    force = np.full(4, 118.25e3)
    head, rod = synth.update(force, np.zeros(4), np.full(4, 0.40))
    assert rod[0] == pytest.approx(2.0 * BAR)
    assert head[0] / BAR == pytest.approx(114.0, abs=0.05)
    net, mode = cylinder_force_from_pressures(head, rod, HEAD_AREA, ANNULUS)
    assert mode is ForceEstimate.TWO_SENSOR
    np.testing.assert_allclose(net, force, rtol=1e-9)


@pytest.mark.parametrize(("speed", "expected_rod_bar"), [(0.005, 11.85), (-0.005, 70.6)])
def test_airborne_moving_leg_targets(speed, expected_rod_bar) -> None:
    """7.4: airborne extension -> the rod side carries the weight (11.85 bar); airborne
    retraction with p_bA 5 bar -> (p_bA A_p + m_rod g) / A_ann = 70.6 bar."""
    synth = _synth()
    force = np.full(4, -1047.0)
    for _ in range(100):  # 2 s >> tau_v 0.05 s
        head, rod = synth.update(force, np.full(4, speed), np.full(4, 0.4))
    assert rod[0] / BAR == pytest.approx(expected_rod_bar, abs=0.1)
    np.testing.assert_allclose(head * HEAD_AREA - rod * ANNULUS, force, rtol=1e-9)


def test_locked_unloading_moves_the_share_r_to_the_rod_side() -> None:
    """Locked: a load decrease dF raises p_r A_ann by r dF, r = k_r / (k_h + k_r)."""
    synth = _synth()
    stroke = 0.40
    k_head = 1e9 * HEAD_AREA / (DEAD + stroke)
    k_rod = 1e9 * ANNULUS / (STROKE_MAX - stroke + 0.05)
    share = k_rod / (k_head + k_rod)
    synth.update(np.full(4, 118e3), np.zeros(4), np.full(4, stroke))
    unload = 10e3  # the L1 stroke_true moves by dF / k_oil = dF / k_head
    _, rod = synth.update(np.full(4, 108e3), np.zeros(4), np.full(4, stroke + unload / k_head))
    assert (rod[0] - 2.0 * BAR) * ANNULUS == pytest.approx(share * unload, rel=5e-3)


def test_head_floor_keeps_the_force_identity() -> None:
    synth = _synth()
    head, rod = synth.update(np.full(4, -20e3), np.zeros(4), np.full(4, 0.4))
    assert head[0] == pytest.approx(0.1e5 - 1.01325e5)
    np.testing.assert_allclose(head * HEAD_AREA - rod * ANNULUS, -20e3, rtol=1e-9)


def test_snapshot_round_trip_and_meta() -> None:
    synth = _synth()
    synth.update(np.full(4, 50e3), np.full(4, 0.003), np.full(4, 0.3))
    state = synth.state_arrays()
    other = _synth()
    other.restore_state(state)
    a = synth.update(np.full(4, 50e3), np.zeros(4), np.full(4, 0.3))
    b = other.update(np.full(4, 50e3), np.zeros(4), np.full(4, 0.3))
    np.testing.assert_array_equal(a[1], b[1])
    assert synth.meta()["params"]["retract_regime"] == "meter_in"


def test_free_air_is_not_implemented() -> None:
    with pytest.raises(ValueError, match="not implemented"):
        RodSideParams(air_fraction_at_1bar=0.001)


def test_force_helper_falls_back_to_head_only() -> None:
    force, mode = cylinder_force_from_pressures(np.full(4, 100 * BAR), None, HEAD_AREA, ANNULUS)
    assert mode is ForceEstimate.HEAD_ONLY
    np.testing.assert_array_equal(force, np.full(4, 100 * BAR) * HEAD_AREA)


# --- 14.7: flow-dependent extend target and the u = 0 lock value ---------------------------------


def _drive(synth, force, speed, periods=100, stroke=0.4):
    for _ in range(periods):
        head, rod = synth.update(np.full(4, force), np.full(4, speed), np.full(4, stroke))
    return head, rod


@pytest.mark.parametrize(("fraction", "expected_bar"), [(1.0, 5.0), (0.5, 2.75), (0.0, 2.0)])
def test_extend_target_depends_on_the_flow(fraction, expected_bar) -> None:
    """p_r* = max(p_T0 + (p_bB - p_T0) (u / v_max)^2, -F / A_ann), grounded (p_T0 2 bar,
    p_bB 5 bar)."""
    synth = _synth()
    v_max = RodSideParams().max_speed_m_s
    target = synth.moving_target_Pa(np.full(4, 50e3), np.full(4, 1), np.full(4, fraction * v_max))
    assert target[0] / BAR == pytest.approx(expected_bar)


def test_lock_after_an_extension_takes_p_t0_not_the_lag() -> None:
    """A leg extending at v_max (rod side 5 bar) that stops locks at p_T0 = 2 bar at once."""
    synth = _synth()
    _drive(synth, 50e3, RodSideParams().max_speed_m_s)
    _, rod = _drive(synth, 50e3, 0.0, periods=1)
    assert rod[0] == pytest.approx(2.0 * BAR)


def test_lock_after_a_retraction_keeps_the_pilot_threshold() -> None:
    synth = _synth()
    _drive(synth, 100e3, -0.005)
    threshold = synth.moving_target_Pa(np.full(4, 100e3), np.full(4, 2))
    assert synth.lock_pressure_Pa[0] == pytest.approx(threshold[0])
    _, rod = _drive(synth, 100e3, 0.0, periods=1)
    assert rod[0] == pytest.approx(threshold[0])


# --- L1-R sensor source and the three paths --------------------------------------------------


class _FakeMachine:
    """Stands in for ``RodChamberStateMachine`` (records the step arguments)."""

    def __init__(self, source="rule") -> None:
        from outrigger_sim.hydraulics.rod_chamber import RodChamberOptions

        self.options = RodChamberOptions(lock_pressure_source=source)
        self.calls = []

    def step(self, **kwargs):
        from types import SimpleNamespace

        self.calls.append(kwargs)
        return SimpleNamespace(head_pressure_Pa=np.full(4, 100 * BAR),
                               rod_pressure_Pa=np.full(4, 3 * BAR))

    def state_arrays(self):
        return {"l1r_state": np.zeros(4)}

    def restore_state(self, arrays):
        self.restored = arrays

    def meta(self):
        return {"model": "fake"}


def test_l1r_source_reads_the_last_machine_step() -> None:
    from outrigger_sim.sensors.rod_side import RodChamberSensorSource

    machine = _FakeMachine()
    source = RodChamberSensorSource(machine)
    with pytest.raises(RuntimeError):
        source.update(np.zeros(4), np.zeros(4), np.zeros(4))
    source.step(time_s=0.0, step_s=2e-4)
    head, rod = source.update(np.full(4, 9e9), np.zeros(4), np.zeros(4))  # inputs not used
    assert head[0] == 100 * BAR and rod[0] == 3 * BAR
    assert "rod_pressure_at_lock_Pa" not in machine.calls[0]  # RULE: nothing handed over
    assert source.state_arrays() == {"l1r_state": pytest.approx(np.zeros(4))}
    source.restore_state({"l1r_state": np.ones(4)})
    assert source.last_step is None and machine.restored["l1r_state"][0] == 1.0
    assert source.meta()["sensor_source"].startswith("l1r_state_machine")


def test_tracked_lock_pressure_hands_over_the_u0_value() -> None:
    from outrigger_sim.sensors.rod_side import RodChamberSensorSource

    synth = _synth()
    machine = _FakeMachine("tracked")
    source = RodChamberSensorSource(machine, synth)
    source.step(time_s=0.0, step_s=2e-4)
    source.update(np.full(4, 50e3), np.full(4, RodSideParams().max_speed_m_s), np.full(4, 0.4))
    source.step(time_s=0.02, step_s=2e-4)
    np.testing.assert_allclose(machine.calls[-1]["rod_pressure_at_lock_Pa"], 2.0 * BAR)


def test_build_rod_pressure_source_paths() -> None:
    from outrigger_sim.sensors.rod_side import (
        PRESSURE_MODELS,
        RodChamberSensorSource,
        build_rod_pressure_source,
    )

    common = {"head_area_m2": HEAD_AREA, "annulus_area_m2": ANNULUS, "stroke_max_m": STROKE_MAX,
              "head_dead_length_m": DEAD, "period_s": PERIOD_S}
    assert PRESSURE_MODELS == ("net_equivalent", "two_chamber_synth", "l1r_state_machine")
    assert build_rod_pressure_source("net_equivalent", **common) is None
    assert isinstance(build_rod_pressure_source("two_chamber_synth", **common), RodSideSynth)
    with pytest.raises(ValueError, match="machine"):
        build_rod_pressure_source("l1r_state_machine", **common)
    source = build_rod_pressure_source("l1r_state_machine", machine=_FakeMachine(), **common)
    assert isinstance(source, RodChamberSensorSource) and source.lock_pressure_synth is None


def test_l1r_source_with_the_real_machine_keeps_the_force_identity() -> None:
    """With the hydraulics module's machine: the sensor returns that step's pressures, and
    ``p_h A_p - p_r A_ann`` is the passed cylinder force; a standstill lock after an extension
    reads the RULE p_r0 2 bar like the synthesis."""
    from outrigger_sim.hydraulics.rod_chamber import (
        RodChamberLegParams,
        RodChamberOptions,
        RodChamberStateMachine,
    )
    from outrigger_sim.sensors.rod_side import RodChamberSensorSource

    params = RodChamberLegParams(head_area_m2=HEAD_AREA, annulus_area_m2=ANNULUS,
                                 head_stiffness_N_m=2.3e7, rod_stiffness_N_m=2.69e6,
                                 outer_stiffness_N_m=2.17e8, rod_weight_N=1047.0)
    machine = RodChamberStateMachine([params] * 4, RodChamberOptions())
    source = RodChamberSensorSource(machine)
    force = np.full(4, 118.25e3)
    step = None
    for k in range(5):
        step = source.step(time_s=k * 2e-4, step_s=2e-4, applied_speed_m_s=np.zeros(4),
                           pad_deflection_m=np.full(4, 5e-3), pad_deflection_rate_m_s=np.zeros(4),
                           motor_position_m=np.full(4, 0.4), cylinder_force_N=force)
    head, rod = source.update(force, np.zeros(4), np.full(4, 0.4))
    np.testing.assert_array_equal(head, step.head_pressure_Pa)
    np.testing.assert_allclose(head * HEAD_AREA - rod * ANNULUS, force, rtol=1e-9)
    assert rod[0] == pytest.approx(2.0 * BAR)
    synth = _synth()
    _, synth_rod = synth.update(force, np.zeros(4), np.full(4, 0.4))
    assert synth_rod[0] == pytest.approx(rod[0])
