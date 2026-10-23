"""Unit tests of the L1-R rod-chamber state machine (``outrigger_sim.hydraulics.rod_chamber``).

References: ``00_docs/02_hydraulic/rod_side_pressure.md`` 14.4 (T1-T15, H1-H6), 14.5 (no step
at the lock, step-cut release contrast) and ``00_docs/01_dynamics/dynamics_model.md`` 5.12.5 /
5.12.8 (interface requirements, V5-type load exchange, probe secants).

Expected values of the T cases are recomputed here from the closed-form linear law with the
geometry of ``04_scripts/04_hydraulic/l1r_rod_spring_spec.py`` (relative 1e-9), compared with
the rounded table values, and with the exact log law of 14.2 (0.5 %).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np
import pytest

from outrigger_sim.hydraulics.rod_chamber import (
    STATE_KEYS,
    CylinderOilColumns,
    LockPressureSource,
    RodChamberLegParams,
    RodChamberMode,
    RodChamberOptions,
    RodChamberStateMachine,
    RodChamberStep,
    RodSideMechanics,
)

BAR = 1.0e5
GRAVITY_M_S2 = 9.80665
BULK_MODULUS_PA = 1.0e9
STROKE_MAX_M = 0.70
DEAD_LENGTH_M = 0.05
FLOOR_GAUGE_PA = 0.1e5 - 1.01325e5
STEP_S = 2.0e-4
MOVING_SPEED_M_S = 1.0e-3
LEG_KIND = ("front", "front", "rear", "rear")
FRONT, REAR = 0, 2
LOCK_FORCE_N = {"front": 118.25e3, "rear": 72.8e3}
"""Cylinder force at the lock (14.4: ``F_lock`` is the net cylinder force)."""

# l1r_rod_spring_spec.py: bore, rod, e_op [m]; k_out [N/m]; moving mass [kg]
GEOMETRY = {"front": (0.130, 0.110, 0.4011), "rear": (0.110, 0.090, 0.3909)}
OUTER_STIFFNESS_N_M = {"front": 2.166e8, "rear": 2.051e8}
ROD_MASS_KG = {"front": 106.784, "rear": 71.5}


def oil_columns(kind: str) -> CylinderOilColumns:
    bore_m, rod_m, extension_m = GEOMETRY[kind]
    return CylinderOilColumns(
        bore_m=bore_m,
        rod_m=rod_m,
        extension_m=extension_m,
        stroke_max_m=STROKE_MAX_M,
        head_dead_length_m=DEAD_LENGTH_M,
        rod_dead_length_m=DEAD_LENGTH_M,
        bulk_modulus_Pa=BULK_MODULUS_PA,
    )


def leg_params(kind: str) -> RodChamberLegParams:
    return RodChamberLegParams.from_oil_columns(
        oil_columns(kind), OUTER_STIFFNESS_N_M[kind], ROD_MASS_KG[kind] * GRAVITY_M_S2
    )


@dataclass(frozen=True)
class ClosedForm:
    """Independent closed-form quantities of one leg (written out, not taken from the module)."""

    head_area_m2: float
    annulus_area_m2: float
    k_head: float
    k_rod: float
    k_outer: float
    rod_weight_N: float
    extension_m: float

    @classmethod
    def of(cls, kind: str) -> ClosedForm:
        bore_m, rod_m, extension_m = GEOMETRY[kind]
        head_area = math.pi / 4 * bore_m**2
        annulus = math.pi / 4 * (bore_m**2 - rod_m**2)
        return cls(
            head_area_m2=head_area,
            annulus_area_m2=annulus,
            k_head=BULK_MODULUS_PA * head_area / (DEAD_LENGTH_M + extension_m),
            k_rod=BULK_MODULUS_PA * annulus / (STROKE_MAX_M - extension_m + DEAD_LENGTH_M),
            k_outer=OUTER_STIFFNESS_N_M[kind],
            rod_weight_N=ROD_MASS_KG[kind] * GRAVITY_M_S2,
            extension_m=extension_m,
        )

    @property
    def share(self) -> float:
        return self.k_rod / (self.k_head + self.k_rod)

    @property
    def k_head_only(self) -> float:
        return 1 / (1 / self.k_head + 1 / self.k_outer)

    @property
    def k_locked(self) -> float:
        return 1 / (1 / (self.k_head + self.k_rod) + 1 / self.k_outer)

    def knee_N(self, rod_pressure_lock_Pa: float) -> float:
        return (rod_pressure_lock_Pa - FLOOR_GAUGE_PA) * self.annulus_area_m2 / self.share

    def retract_lock_pressure_Pa(self, cylinder_force_N: float) -> float:
        psi, cracking, back = 3.5, 3 * BAR, 5 * BAR
        ratio = self.head_area_m2 / self.annulus_area_m2
        head = max(
            back,
            (cylinder_force_N / self.annulus_area_m2 + cracking + back * (1 - 1 / psi))
            / (ratio - 1 / psi),
        )
        return (head * self.head_area_m2 - cylinder_force_N) / self.annulus_area_m2

    def deflection_change_m(self, force_change_N: float, knee_N: float) -> float:
        if force_change_N <= knee_N:
            return force_change_N / self.k_locked
        return knee_N / self.k_locked + (force_change_N - knee_N) / self.k_head_only

    def linear_rod_pressure_Pa(self, p_r0_Pa: float, force_change_N: float) -> float:
        return max(p_r0_Pa - self.share * force_change_N / self.annulus_area_m2, FLOOR_GAUGE_PA)

    def log_rod_pressure_Pa(self, p_r0_Pa: float, force_change_N: float) -> float:
        travel_m = -force_change_N / (self.k_head + self.k_rod)
        volume_m3 = self.annulus_area_m2 * (STROKE_MAX_M - self.extension_m + DEAD_LENGTH_M)
        pressure = p_r0_Pa + BULK_MODULUS_PA * math.log(
            volume_m3 / (volume_m3 - self.annulus_area_m2 * travel_m)
        )
        return max(pressure, FLOOR_GAUGE_PA)


# --- machine drivers -------------------------------------------------------------------------


def make_machine(**option_values: object) -> RodChamberStateMachine:
    options = RodChamberOptions(**option_values)  # type: ignore[arg-type]
    return RodChamberStateMachine([leg_params(kind) for kind in LEG_KIND], options)


def lock_deflections_m() -> np.ndarray:
    """Head-only pad deflection that carries the lock force plus the rod weight."""
    values = []
    for kind in LEG_KIND:
        form = ClosedForm.of(kind)
        values.append((LOCK_FORCE_N[kind] + form.rod_weight_N) / form.k_head_only)
    return np.array(values)


def rod_weights_N() -> np.ndarray:
    return np.array([ClosedForm.of(kind).rod_weight_N for kind in LEG_KIND])


def drive(
    machine: RodChamberStateMachine,
    time_s: float,
    speed_m_s: float | np.ndarray,
    deflection_m: np.ndarray,
    *,
    rate_m_s: float | np.ndarray = 0.0,
    cylinder_force_N: np.ndarray | None = None,
) -> RodChamberStep:
    """One step with the quasi-static cylinder force ``N - m g`` unless given."""
    if cylinder_force_N is None:
        normal_N = np.array(
            [leg.normal_force_at(d) for leg, d in zip(machine.legs, deflection_m, strict=True)]
        )
        cylinder_force_N = normal_N - rod_weights_N()
    return machine.step(
        time_s=time_s,
        step_s=STEP_S,
        applied_speed_m_s=speed_m_s,
        pad_deflection_m=deflection_m,
        pad_deflection_rate_m_s=rate_m_s,
        motor_position_m=0.4,
        cylinder_force_N=cylinder_force_N,
    )


def lock_after(machine: RodChamberStateMachine, lock_from: str) -> np.ndarray:
    """Move (EXT or RET) at the lock deflection, then lock at t = 0.01 s; returns delta_lock."""
    deflection = lock_deflections_m()
    sign = 1.0 if lock_from == "EXT" else -1.0
    drive(machine, 0.0, sign * MOVING_SPEED_M_S, deflection)
    drive(machine, 0.01, 0.0, deflection)
    return deflection


def p_r0_Pa(kind: str, lock_from: str) -> float:
    if lock_from == "EXT":
        return 2.0 * BAR
    return ClosedForm.of(kind).retract_lock_pressure_Pa(LOCK_FORCE_N[kind])


# --- T1-T15 ----------------------------------------------------------------------------------

LIFT = None


@dataclass(frozen=True)
class TableCase:
    name: str
    kind: str
    lock_from: str
    force_change_kN: float | None  # None = lift-off
    mode: RodChamberMode
    deflection_mm: float | None
    rod_pressure_bar: float
    log_pressure_bar: float | None
    stiffness_N_m: float
    floor_force_kN: float | None = None


L, F, U = RodChamberMode.LOCK, RodChamberMode.FLOOR, RodChamberMode.LIFT
TABLE = [
    TableCase("T1", "front", "EXT", -10, L, -0.2947, 9.125, 9.127, 3.3928e7),
    TableCase("T2", "front", "EXT", 3, L, 0.0884, -0.137, None, 3.3928e7),
    TableCase("T3", "front", "EXT", 10, F, 0.3487, -0.913, None, 2.5905e7, 122.34),
    TableCase("T4", "front", "EXT", 60, F, 2.2788, -0.913, None, 2.5905e7),
    TableCase("T5", "front", "EXT", LIFT, U, None, 86.99, 87.36, 0.0),
    TableCase("T6", "front", "RET", -10, L, -0.2947, 41.98, None, 3.3928e7),
    TableCase("T7", "front", "RET", 10, L, 0.2947, 27.73, None, 3.3928e7, 168.45),
    TableCase("T8", "front", "RET", 60, F, 1.8579, -0.913, None, 2.5905e7),
    TableCase("T9", "front", "RET", LIFT, U, None, 119.85, 120.21, 0.0),
    TableCase("T10", "rear", "EXT", -10, L, -0.3788, 11.190, None, 2.6402e7),
    TableCase("T11", "rear", "EXT", 3, L, 0.1136, -0.757, None, 2.6402e7, 75.97),
    TableCase("T12", "rear", "EXT", 10, F, 0.4702, -0.913, None, 1.9505e7),
    TableCase("T13", "rear", "EXT", LIFT, U, None, 69.55, 69.77, 0.0),
    TableCase("T14", "rear", "RET", 10, L, 0.3788, 22.24, None, 2.6402e7, 107.99),
    TableCase("T15", "rear", "RET", 60, F, 2.6048, -0.913, None, 1.9505e7),
]
TABLE_PRESSURE_TOL_BAR = 0.006
"""Table pressures are rounded to 0.01 bar (floor -0.913 vs -0.91325)."""
TABLE_DEFLECTION_TOL_MM = 6e-5


def force_change_N(case: TableCase) -> float:
    """Oil (= cylinder) force change; lift-off brings the pad force to 0 (``-F_lock - m g``)."""
    if case.force_change_kN is None:
        return -(LOCK_FORCE_N[case.kind] + ClosedForm.of(case.kind).rod_weight_N)
    return case.force_change_kN * 1e3


def target_deflections_m(case: TableCase, delta_lock: np.ndarray) -> np.ndarray:
    """Deflection of every leg after the change (lift: just below the zero-force point)."""
    form = ClosedForm.of(case.kind)
    pressure = p_r0_Pa(case.kind, case.lock_from)
    change = form.deflection_change_m(force_change_N(case), form.knee_N(pressure))
    if case.force_change_kN is None:
        change -= 1e-9
    leg = FRONT if case.kind == "front" else REAR
    deflection = delta_lock.copy()
    deflection[leg] += change
    return deflection


@pytest.mark.parametrize("case", TABLE, ids=[case.name for case in TABLE])
def test_reference_case(case: TableCase) -> None:
    machine = make_machine()
    delta_lock = lock_after(machine, case.lock_from)
    deflection = target_deflections_m(case, delta_lock)
    out = drive(machine, 0.02, 0.0, deflection)
    leg = FRONT if case.kind == "front" else REAR
    form = ClosedForm.of(case.kind)
    pressure_lock = p_r0_Pa(case.kind, case.lock_from)
    change_N = force_change_N(case)

    assert RodChamberMode(out.mode[leg]) is case.mode
    expected_pressure = form.linear_rod_pressure_Pa(pressure_lock, change_N)
    assert out.rod_pressure_Pa[leg] == pytest.approx(expected_pressure, rel=1e-9)
    assert out.rod_pressure_Pa[leg] / BAR == pytest.approx(
        case.rod_pressure_bar, abs=TABLE_PRESSURE_TOL_BAR
    )
    log_pressure = form.log_rod_pressure_Pa(pressure_lock, change_N)
    assert out.rod_pressure_Pa[leg] == pytest.approx(log_pressure, rel=5e-3)
    if case.log_pressure_bar is not None:
        assert log_pressure / BAR == pytest.approx(case.log_pressure_bar, abs=0.006)
    assert out.pad_stiffness_N_m[leg] == pytest.approx(case.stiffness_N_m, rel=1e-4, abs=1e-9)
    if case.deflection_mm is not None:
        moved_mm = (deflection[leg] - delta_lock[leg]) * 1e3
        assert moved_mm == pytest.approx(case.deflection_mm, abs=TABLE_DEFLECTION_TOL_MM)
        expected_normal = LOCK_FORCE_N[case.kind] + form.rod_weight_N + change_N
        assert out.normal_force_N[leg] == pytest.approx(expected_normal, rel=1e-9)
    else:
        assert out.normal_force_N[leg] == 0.0
    if case.floor_force_kN is not None:
        knee_kN = machine.legs[leg].params.knee_force_increment_N(pressure_lock) / 1e3
        assert LOCK_FORCE_N[case.kind] / 1e3 + knee_kN == pytest.approx(
            case.floor_force_kN, abs=0.006
        )


def test_retract_lock_pressure_matches_the_table() -> None:
    front = leg_params("front").retract_threshold_rod_pressure_Pa(LOCK_FORCE_N["front"])
    rear = leg_params("rear").retract_threshold_rod_pressure_Pa(LOCK_FORCE_N["rear"])
    assert front / BAR == pytest.approx(34.85, abs=0.006)
    assert rear / BAR == pytest.approx(31.43, abs=0.006)


def test_lift_deflection_includes_the_rod_weight() -> None:
    """14.4 table T5 / T13 give ``-F_lock / k_n'``; the consistent value adds ``m g`` (report)."""
    machine = make_machine()
    delta_lock = lock_after(machine, "EXT")
    for leg, kind in ((FRONT, "front"), (REAR, "rear")):
        form = ClosedForm.of(kind)
        zero_force_m = delta_lock[leg] - (LOCK_FORCE_N[kind] + form.rod_weight_N) / form.k_locked
        assert machine.legs[leg].normal_force_at(zero_force_m) == pytest.approx(0.0, abs=1e-6)
        table_mm = {"front": -3.4853, "rear": -2.7574}[kind]
        assert -LOCK_FORCE_N[kind] / form.k_locked * 1e3 == pytest.approx(table_mm, abs=1e-4)


# --- parameters vs the specs -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "k_locked", "share", "knee_kN"),
    [("front", 3.3928e7, 0.2686, 4.089), ("rear", 2.6402e7, 0.2887, 3.170)],
)
def test_derived_parameters(kind: str, k_locked: float, share: float, knee_kN: float) -> None:
    params = leg_params(kind)
    form = ClosedForm.of(kind)
    assert params.pad_stiffness_locked_N_m == pytest.approx(form.k_locked, rel=1e-12)
    assert params.pad_stiffness_locked_N_m == pytest.approx(k_locked, rel=1e-4)
    assert params.rod_share == pytest.approx(share, abs=1e-4)
    assert params.knee_force_increment_N(2 * BAR) / 1e3 == pytest.approx(knee_kN, abs=1e-3)


def test_from_pad_stiffness_reproduces_the_engine_stiffness() -> None:
    columns = oil_columns("front")
    params = RodChamberLegParams.from_pad_stiffness(columns, 2.5905e7, 1047.0)
    assert params.pad_stiffness_head_only_N_m == pytest.approx(2.5905e7, rel=1e-12)
    with pytest.raises(ValueError, match="below the head"):
        RodChamberLegParams.from_pad_stiffness(columns, 1e9, 1047.0)


# --- transitions -----------------------------------------------------------------------------


def test_lock_entry_does_not_step_the_force() -> None:
    machine = make_machine()
    deflection = lock_deflections_m()
    moving = drive(machine, 0.0, MOVING_SPEED_M_S, deflection)
    locked = drive(machine, 0.01, 0.0, deflection)
    assert np.all(locked.mode == RodChamberMode.LOCK)
    assert np.max(np.abs(locked.normal_force_N - moving.normal_force_N)) < 1e-9  # 0.000 kN
    assert np.max(np.abs(locked.extra_force_N)) < 1e-9


def test_step_release_after_lift_jumps_about_28_kN_and_the_decay_does_not() -> None:
    for lag_s, expect_jump in ((0.05, False), (0.0, True)):
        machine = make_machine(rod_pressure_lag_s=lag_s)
        delta_lock = lock_after(machine, "EXT")
        lifted = target_deflections_m(TABLE[4], delta_lock)  # T5
        before = drive(machine, 0.02, 0.0, lifted)
        after = drive(machine, 0.03, MOVING_SPEED_M_S, lifted)
        jump_kN = (after.normal_force_N[FRONT] - before.normal_force_N[FRONT]) / 1e3
        if expect_jump:
            assert 27.5 < jump_kN < 28.6
        else:
            assert abs(jump_kN) < 1e-9


def test_h1_recontact_keeps_the_anchor() -> None:
    machine = make_machine()
    delta_lock = lock_after(machine, "EXT")
    anchor_before = machine.state_arrays()["l1r_delta_lock_m"].copy()
    drive(machine, 0.02, 0.0, target_deflections_m(TABLE[4], delta_lock))  # T5 lift
    out = drive(machine, 0.03, 0.0, target_deflections_m(TABLE[0], delta_lock))  # T1 load
    form = ClosedForm.of("front")
    assert RodChamberMode(out.mode[FRONT]) is RodChamberMode.LOCK
    expected = form.linear_rod_pressure_Pa(2 * BAR, -10e3)
    assert out.rod_pressure_Pa[FRONT] == pytest.approx(expected, rel=1e-9)
    assert out.rod_pressure_Pa[FRONT] / BAR == pytest.approx(9.125, abs=0.006)
    assert np.array_equal(machine.state_arrays()["l1r_delta_lock_m"], anchor_before)


def test_h2_return_from_the_floor_is_history_free() -> None:
    machine = make_machine()
    delta_lock = lock_after(machine, "EXT")
    floor = drive(machine, 0.02, 0.0, target_deflections_m(TABLE[3], delta_lock))  # T4
    assert RodChamberMode(floor.mode[FRONT]) is RodChamberMode.FLOOR
    back = drive(machine, 0.03, 0.0, delta_lock)
    assert RodChamberMode(back.mode[FRONT]) is RodChamberMode.LOCK
    assert back.rod_pressure_Pa[FRONT] == 2 * BAR
    assert back.piston_travel_m[FRONT] == 0.0
    form = ClosedForm.of("front")
    assert back.normal_force_N[FRONT] == pytest.approx(
        LOCK_FORCE_N["front"] + form.rod_weight_N, rel=1e-12
    )


def test_h3_release_decays_with_tau_v() -> None:
    machine = make_machine()
    delta_lock = lock_after(machine, "EXT")
    loaded = target_deflections_m(TABLE[0], delta_lock)  # T1
    locked = drive(machine, 0.02, 0.0, loaded)
    released = drive(machine, 0.02, MOVING_SPEED_M_S, loaded)
    assert released.normal_force_N[FRONT] == pytest.approx(locked.normal_force_N[FRONT], abs=1e-9)
    initial = released.extra_force_N[FRONT]
    assert initial != 0.0
    one_tau = drive(machine, 0.07, MOVING_SPEED_M_S, loaded)
    five_tau = drive(machine, 0.27, MOVING_SPEED_M_S, loaded)
    assert one_tau.extra_force_N[FRONT] / initial == pytest.approx(math.exp(-1), rel=1e-12)
    assert five_tau.extra_force_N[FRONT] / initial == pytest.approx(0.0067, abs=1e-4)


def test_h4_second_lock_after_retract_uses_the_threshold() -> None:
    machine = make_machine()
    delta_lock = lock_after(machine, "EXT")
    drive(machine, 0.02, -MOVING_SPEED_M_S, delta_lock)
    drive(machine, 1.02, -MOVING_SPEED_M_S, delta_lock)
    cylinder = np.array([LOCK_FORCE_N[kind] for kind in LEG_KIND])
    drive(machine, 1.03, 0.0, delta_lock, cylinder_force_N=cylinder)
    state = machine.state_arrays()
    assert state["l1r_p_r0_Pa"][FRONT] / BAR == pytest.approx(34.85, abs=0.006)
    knee_kN = machine.legs[FRONT].params.knee_force_increment_N(state["l1r_p_r0_Pa"][FRONT]) / 1e3
    assert LOCK_FORCE_N["front"] / 1e3 + knee_kN == pytest.approx(168.45, abs=0.01)


def test_h5_quick_reversal_inside_the_closing_delay_does_not_lock() -> None:
    machine = make_machine(poc_close_delay_s=0.03)
    deflection = lock_deflections_m()
    drive(machine, 0.00, MOVING_SPEED_M_S, deflection)
    drive(machine, 0.01, 0.0, deflection)
    reversed_out = drive(machine, 0.02, -MOVING_SPEED_M_S, deflection)
    assert np.all(reversed_out.mode == RodChamberMode.RET)
    assert np.all(np.isnan(machine.state_arrays()["l1r_F_lock_N"]))
    drive(machine, 0.03, 0.0, deflection)
    waiting = drive(machine, 0.05, 0.0, deflection)
    assert np.all(waiting.mode == RodChamberMode.RET)
    locked = drive(machine, 0.06, 0.0, deflection)
    assert np.all(locked.mode == RodChamberMode.LOCK)


@pytest.mark.skip(reason="gas separation after FLOOR (14.3 optional) is not implemented")
def test_h6_gas_separation() -> None:  # pragma: no cover
    """H6: T4 -> F_lock -> lift with 0.14 % free gas gives about 84 bar (12.4)."""


def test_relock_during_release_absorbs_the_residual() -> None:
    machine = make_machine()
    delta_lock = lock_after(machine, "EXT")
    loaded = target_deflections_m(TABLE[0], delta_lock)
    drive(machine, 0.02, 0.0, loaded)
    decaying = drive(machine, 0.03, MOVING_SPEED_M_S, loaded)
    relocked = drive(machine, 0.03, 0.0, loaded)
    assert machine.legs[FRONT].is_locked
    assert relocked.normal_force_N[FRONT] == pytest.approx(
        decaying.normal_force_N[FRONT], rel=1e-12
    )
    state = machine.state_arrays()
    assert state["l1r_F_lock_N"][FRONT] == pytest.approx(decaying.normal_force_N[FRONT], rel=1e-12)
    assert state["l1r_p_r0_Pa"][FRONT] == 2 * BAR


def test_airborne_lock_starts_the_law_at_zero_deflection() -> None:
    machine = make_machine()
    airborne = np.full(4, -0.01)
    drive(machine, 0.0, 0.0, airborne)
    assert np.all(machine.state_arrays()["l1r_delta_lock_m"] == 0.0)
    touching = drive(machine, 0.01, 0.0, np.full(4, 1e-4))
    expected = [leg.params.pad_stiffness_locked_N_m * 1e-4 for leg in machine.legs]
    assert np.allclose(touching.normal_force_N, expected, rtol=1e-12)


# --- predictor, same state, mechanics off, snapshot ------------------------------------------


@pytest.mark.parametrize("predictor", [False, True])
def test_predictor_moves_only_the_force_evaluation(predictor: bool) -> None:
    machine = make_machine(predictor=predictor)
    delta_lock = lock_after(machine, "EXT")
    form = ClosedForm.of("front")
    knee_m = form.knee_N(2 * BAR) / form.k_locked
    current = delta_lock.copy()
    current[FRONT] += 0.5 * knee_m
    rate = np.zeros(4)
    rate[FRONT] = knee_m / STEP_S  # predicted deflection is past the knee
    out = drive(machine, 0.02, 0.0, current, rate_m_s=rate)
    assert RodChamberMode(out.mode[FRONT]) is RodChamberMode.LOCK
    leg = machine.legs[FRONT]
    evaluated = current[FRONT] + (rate[FRONT] * STEP_S if predictor else 0.0)
    assert out.extra_force_N[FRONT] == leg.extra_force_at(evaluated)
    assert out.normal_force_N[FRONT] == leg.normal_force_at(current[FRONT])


def test_sensor_pressures_obey_the_force_identity_in_the_same_call() -> None:
    machine = make_machine()
    delta_lock = lock_after(machine, "EXT")
    for time_s, case in ((0.02, TABLE[0]), (0.03, TABLE[2]), (0.04, TABLE[4])):
        out = drive(machine, time_s, 0.0, target_deflections_m(case, delta_lock))
        params = machine.legs[FRONT].params
        net = (
            out.head_pressure_Pa * params.head_area_m2
            - out.rod_pressure_Pa * params.annulus_area_m2
        )
        assert net[FRONT] == pytest.approx(out.cylinder_force_N[FRONT], rel=1e-12, abs=1e-6)
        if RodChamberMode(out.mode[FRONT]) is RodChamberMode.FLOOR:
            assert out.rod_pressure_Pa[FRONT] == FLOOR_GAUGE_PA


def test_stroke_true_uses_the_lock_based_increment() -> None:
    machine = make_machine()
    delta_lock = lock_after(machine, "EXT")
    form = ClosedForm.of("front")
    cylinder_lock = np.array([LOCK_FORCE_N[kind] for kind in LEG_KIND])
    for time_s, case in ((0.02, TABLE[0]), (0.03, TABLE[3])):
        out = drive(machine, time_s, 0.0, target_deflections_m(case, delta_lock))
        change = force_change_N(case)
        knee = form.knee_N(2 * BAR)
        below = min(change, knee)
        travel = -below / (form.k_head + form.k_rod) - max(change - knee, 0.0) / form.k_head
        expected = 0.4 - cylinder_lock[FRONT] / form.k_head + travel
        assert out.stroke_true_m[FRONT] == pytest.approx(expected, rel=1e-12, abs=1e-12)


def test_mechanics_off_is_the_present_l1_bit_for_bit() -> None:
    machine = make_machine(mechanics=RodSideMechanics.OFF)
    rng = np.random.default_rng(7)
    head_area = np.array([leg.params.head_area_m2 for leg in machine.legs])
    k_oil = np.array([leg.params.head_stiffness_N_m for leg in machine.legs])
    for index in range(50):
        speed = rng.choice([-MOVING_SPEED_M_S, 0.0, MOVING_SPEED_M_S], size=4)
        deflection = rng.uniform(-1e-3, 6e-3, size=4)
        motor = rng.uniform(0.0, 0.7, size=4)
        force = rng.uniform(-2e3, 3e5, size=4)
        out = machine.step(
            time_s=index * STEP_S,
            step_s=STEP_S,
            applied_speed_m_s=speed,
            pad_deflection_m=deflection,
            pad_deflection_rate_m_s=rng.normal(size=4),
            motor_position_m=motor,
            cylinder_force_N=force,
        )
        assert np.array_equal(out.extra_force_N, np.zeros(4))
        assert np.array_equal(out.head_pressure_Pa, force / head_area)  # truth.head_pressure_Pa
        assert np.array_equal(out.stroke_true_m, motor - force / k_oil)  # truth.stroke_true_m
        assert np.array_equal(out.rod_pressure_Pa, np.zeros(4))


def history(machine: RodChamberStateMachine, *, end_locked: bool = False) -> None:
    delta_lock = lock_after(machine, "EXT")
    drive(machine, 0.02, 0.0, target_deflections_m(TABLE[3], delta_lock))
    if not end_locked:
        drive(machine, 0.03, MOVING_SPEED_M_S, target_deflections_m(TABLE[0], delta_lock))


@pytest.mark.parametrize("end_locked", [False, True], ids=["releasing", "locked"])
def test_snapshot_restores_bit_identical_outputs(end_locked: bool) -> None:
    original = make_machine()
    history(original, end_locked=end_locked)
    state = original.to_state()
    assert tuple(state) == STATE_KEYS
    copy = make_machine()
    copy.from_state(state)
    deflection = lock_deflections_m() + 2e-4
    for time_s, speed in ((0.04, MOVING_SPEED_M_S), (0.05, 0.0), (0.06, 0.0)):
        a = drive(original, time_s, speed, deflection, rate_m_s=1e-3)
        b = drive(copy, time_s, speed, deflection, rate_m_s=1e-3)
        for name in RodChamberStep.__dataclass_fields__:
            assert np.array_equal(getattr(a, name), getattr(b, name), equal_nan=True), name


def test_snapshot_without_keys_defaults_to_locked_after_extend() -> None:
    machine = make_machine()
    history(machine)
    machine.restore_state({})
    assert machine.meta()["l1r_state_defaulted"] is True
    deflection = lock_deflections_m()
    out = drive(machine, 1.0, 0.0, deflection)
    assert np.all(out.mode == RodChamberMode.LOCK)
    assert np.array_equal(machine.state_arrays()["l1r_p_r0_Pa"], np.full(4, 2 * BAR))
    with pytest.raises(KeyError, match="lacks"):
        machine.restore_state({"l1r_state": np.ones(4)})


def test_tracked_lock_pressure_option_uses_the_moving_lag() -> None:
    machine = make_machine(lock_pressure_source=LockPressureSource.TRACKED)
    deflection = lock_deflections_m()
    for index in range(200):  # 40 ms of extension: lag towards p_bB = 5 bar
        drive(machine, index * STEP_S, MOVING_SPEED_M_S, deflection)
    drive(machine, 200 * STEP_S, 0.0, deflection)
    expected = 5 * BAR + (2 * BAR - 5 * BAR) * math.exp(-STEP_S / 0.05) ** 200
    assert machine.state_arrays()["l1r_p_r0_Pa"] == pytest.approx(np.full(4, expected), rel=1e-12)


def test_lock_pressure_override_and_thermal_shift() -> None:
    thermal_Pa_per_K = 4.94 * BAR  # 14.3 front (option, default off)
    params = replace(leg_params("front"), thermal_rod_pressure_Pa_per_K=thermal_Pa_per_K)
    machine = RodChamberStateMachine([params], RodChamberOptions())
    deflection = np.array([lock_deflections_m()[FRONT]])
    common = {
        "step_s": STEP_S,
        "pad_deflection_m": deflection,
        "pad_deflection_rate_m_s": 0.0,
        "motor_position_m": 0.4,
        "cylinder_force_N": LOCK_FORCE_N["front"],
    }
    machine.step(
        time_s=0.0,
        applied_speed_m_s=0.0,
        oil_temperature_K=300.0,
        rod_pressure_at_lock_Pa=10 * BAR,
        **common,
    )
    warmer = machine.step(time_s=1.0, applied_speed_m_s=0.0, oil_temperature_K=301.0, **common)
    assert machine.state_arrays()["l1r_p_r0_Pa"][0] == 10 * BAR
    assert warmer.rod_pressure_Pa[0] == pytest.approx(10 * BAR + thermal_Pa_per_K, rel=1e-12)


def test_head_pressure_is_clipped_at_the_floor() -> None:
    machine = make_machine()
    deflection = np.zeros(4)
    lifted_force = -rod_weights_N() - 5e4  # e.g. a rod inertia pulse in the engine force
    out = drive(machine, 0.0, MOVING_SPEED_M_S, deflection, cylinder_force_N=lifted_force)
    params = machine.legs[FRONT].params
    assert out.head_pressure_Pa[FRONT] == FLOOR_GAUGE_PA
    net = out.head_pressure_Pa * params.head_area_m2 - out.rod_pressure_Pa * params.annulus_area_m2
    assert net[FRONT] == pytest.approx(lifted_force[FRONT], rel=1e-12)
    assert out.pad_stiffness_N_m[FRONT] == 0.0  # moving, no contact


def test_mechanics_off_reports_lock_without_regions() -> None:
    machine = make_machine(mechanics=RodSideMechanics.OFF)
    delta_lock = lock_after(machine, "EXT")
    out = drive(machine, 0.02, 0.0, target_deflections_m(TABLE[3], delta_lock))
    assert np.all(out.mode == RodChamberMode.LOCK)
    assert out.pad_stiffness_N_m[FRONT] == machine.legs[FRONT].params.pad_stiffness_head_only_N_m
    assert np.all(machine.state_arrays()["l1r_state"] == RodChamberMode.LOCK)


def test_meta_reports_the_per_leg_values() -> None:
    meta = make_machine().meta()
    assert meta["l1_rod_chamber_mechanics"] == "one_sided_parallel"
    assert meta["legs"][FRONT]["knee_after_extend_N"] == pytest.approx(4089.0, abs=0.1)
    assert meta["legs"][REAR]["pad_stiffness_locked_N_m"] == pytest.approx(2.6402e7, rel=1e-4)


def test_invalid_inputs_are_rejected() -> None:
    with pytest.raises(ValueError, match=">= 0"):
        RodChamberOptions(poc_close_delay_s=-1.0)
    with pytest.raises(ValueError, match="must exceed"):
        replace(leg_params("front"), head_area_m2=1e-4)
    with pytest.raises(ValueError, match="> 0"):
        replace(leg_params("front"), rod_stiffness_N_m=0.0)
    with pytest.raises(ValueError, match="empty"):
        RodChamberStateMachine([], RodChamberOptions())
    with pytest.raises(ValueError, match="shape"):
        drive(make_machine(), 0.0, np.zeros(3), lock_deflections_m())
