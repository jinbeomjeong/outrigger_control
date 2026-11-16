"""Harness-plant checks of the 436.9 plant options P1 and P2 (``jp3_remedy_spec.md`` 5.2 T-JR-06,
T-JR-07); writes one JSON. Helper of ``test_jp3_harness_units.py`` (the plant needs dynamics-dev).

The plant is the v5 adapter on the body-fixed kernel stand-in of ``v5_harness_unit_runner``
(massless rods, FR on a floor that drops): no controller runs, the checks drive single legs.

Usage:
  python -I -B jp3_harness_unit_runner.py <check> <out.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:  # -I leaves the script folder out of sys.path
    sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
import v5_harness_unit_runner as base  # noqa: E402  (sets the checkout sys.path first)

BAR = 1.0e5
MICRO_SPEED_M_S = 2.0e-6
"""Spec T-JR-06: +-2 um/s micro command."""
MICRO_FLIP_S = 0.1
MICRO_RUN_S = 1.0
RELEASE_SPEED_M_S = 4.71e-3
RELEASE_LIMIT_S = 0.1
SHORT_MOVE_S = 0.02
"""T-JR-07: a 20 ms move leaves ``G_r,lock = r0 exp(-0.4)`` at the relock (tau 0.05 s)."""
SHORT_MOVE_FRACTION = 0.05
RELOCK_RUN_S = 0.3
RR = 3
V_MAX_M_S = 0.020924
"""YAML ``actuator.max_speed_m_s``."""


def _options(**changes):
    from outrigger_sim.hydraulics.v5_options import CheckDelaySetting, HydraulicOptions

    values = {"rod_release_force": True}
    if changes.pop("gate", False):
        values["line_fill_gate"] = CheckDelaySetting("VN")
    values.update(changes)
    return HydraulicOptions(**values)


def _drive(plant, leg: int, speeds_m_s) -> list[dict]:
    """One kernel step per speed on ``leg``; per step the lock state and the lock transitions
    with the M2 truth just before and after."""
    rows = []
    for speed_m_s in speeds_m_s:
        command = np.zeros(4)
        command[leg] = speed_m_s
        lag_before = plant.rod_pressure_lag.pressure_Pa.copy()
        was_locked = np.asarray(plant.locked, bool).copy()
        plant.step(command, 1)
        locked = np.asarray(plant.locked, bool)
        row = {"t_s": float(plant.t), "locked": bool(locked[leg])}
        gate = getattr(plant, "line_fill_gate", None)
        if gate is not None:
            row["rod_released"] = bool(gate.rod_released[leg])
        if locked[leg] and not was_locked[leg]:
            truth_after = float(plant.p_r0[leg] - plant.Gr_lock[leg] / plant.A_ann[leg])
            row.update(relock=True, lag_before_Pa=float(lag_before[leg]),
                       truth_after_Pa=truth_after, Gr_lock_N=float(plant.Gr_lock[leg]),
                       head_step_Pa=(truth_after - float(lag_before[leg]))
                       * float(plant.A_ann[leg]) / float(plant.flow_limiter.params.A_h[leg]))
        rows.append(row)
    return rows


def _micro_then_release(options, leg: int) -> dict:
    plant = base._lifted_leg_plant(options)
    steps = round(MICRO_RUN_S / base.KERNEL_STEP_S)
    flip = round(MICRO_FLIP_S / base.KERNEL_STEP_S)
    micro = [MICRO_SPEED_M_S if (k // flip) % 2 == 0 else -MICRO_SPEED_M_S for k in range(steps)]
    micro_rows = _drive(plant, leg, micro)
    t_start = plant.t
    rod_Pa = float(plant.p_r0[leg] - plant.Gr[leg] / plant.A_ann[leg])
    head_Pa = float((plant.pressure()[leg] + rod_Pa * plant.A_ann[leg])
                    / plant.flow_limiter.params.A_h[leg])
    ramp = [RELEASE_SPEED_M_S * (1.0 - np.exp(-(k + 1) * base.KERNEL_STEP_S / base.VALVE_TAU_S))
            for k in range(round(0.3 / base.KERNEL_STEP_S))]
    release_rows = _drive(plant, leg, ramp)
    t_release = next((row["t_s"] for row in release_rows if not row["locked"]), None)
    t_rod_check = next((row["t_s"] for row in release_rows if row.get("rod_released")), None)
    head_area = float(plant.flow_limiter.params.A_h[leg])
    return {"micro_unlocked_steps": sum(not row["locked"] for row in micro_rows),
            "release_after_s": None if t_release is None else t_release - t_start,
            "rod_check_release_after_s": None if t_rod_check is None else t_rod_check - t_start,
            "head_bar": head_Pa / BAR, "rod_bar": rod_Pa / BAR,
            "hand_head_check_open_s": _hand_fill_time_s(head_Pa, head_area),
            "hand_head_check_open_drain_s": _hand_fill_time_s(head_Pa, head_area, True),
            "gate_summary_mode": (None if plant.line_fill_gate is None
                                  else plant.line_fill_gate.summary()["mode"])}


LINE_VOLUME_M3, HOSE_BULK_MODULUS_PA = 285e-6, 0.5e9
CRACK_PRESSURE_PA, TANK_PRESSURE_PA = 3e5, 2e5
NEUTRAL_FRACTION, COMPENSATOR_DROP_PA, VENT_CLOSING_OPENING = 0.05, 10e5, 0.02
DRAIN_STEP_S = 1e-6


def _hand_fill_time_s(head_Pa: float, head_area_m2: float, with_drain: bool = False) -> float:
    """Path B of the release time (edition 4 T-JR-06): the line oil ``V_line (p_h + p_cr -
    p_T) / beta_hose`` delivered by ``A_h u_v``, ``u_v`` the 0.1 s lag of the 4.71 mm/s step
    from rest, no ``psi p_B`` help; ``with_drain`` subtracts the VN neutral drain ``K_n g
    sqrt(p_A - p_T) / A_h`` (continuous ODE, 1 us Euler steps; review ``cr04``: 87 bar front
    160.16 ms with the drain, 160.08 ms without, 35.2 bar rear 94.02 ms)."""
    target_Pa = head_Pa + CRACK_PRESSURE_PA
    stiffness_Pa_m = head_area_m2 * HOSE_BULK_MODULUS_PA / LINE_VOLUME_M3
    drain_coefficient = (NEUTRAL_FRACTION * head_area_m2 * V_MAX_M_S
                         / np.sqrt(COMPENSATOR_DROP_PA)) if with_drain else 0.0
    fill_m, t_s = 0.0, 0.0
    while TANK_PRESSURE_PA + fill_m * stiffness_Pa_m < target_Pa:
        t_mid_s = t_s + 0.5 * DRAIN_STEP_S
        valve_m_s = RELEASE_SPEED_M_S * (1.0 - np.exp(-t_mid_s / base.VALVE_TAU_S))
        gate = max(1.0 - valve_m_s / (VENT_CLOSING_OPENING * V_MAX_M_S), 0.0)
        drain_m_s = drain_coefficient * gate * np.sqrt(fill_m * stiffness_Pa_m) / head_area_m2
        fill_m = max(fill_m + (valve_m_s - drain_m_s) * DRAIN_STEP_S, 0.0)
        t_s += DRAIN_STEP_S
    return t_s


def check_p1_gate() -> dict:
    """T-JR-06: a locked leg under +-2 um/s for 1 s stays locked with P1 (and releases
    without it); 4.7 mm/s through the valve lag releases within 0.1 s with P1."""
    out = {}
    for name, options in (("p1", _options(gate=True)), ("off", _options())):
        out[name] = _micro_then_release(options, base.FRONT_LEFT)
    front_area, rear_area = 1.3273229e-2, 9.50331778e-3
    out["path_b_reference_s"] = {
        "front_87bar_drain": _hand_fill_time_s(87.0 * BAR, front_area, True),
        "front_87bar_no_drain": _hand_fill_time_s(87.0 * BAR, front_area, False),
        "front_area_35p2bar_drain": _hand_fill_time_s(35.2 * BAR, front_area, True),
        "rear_area_35p2bar_drain": _hand_fill_time_s(35.2 * BAR, rear_area, True)}
    return out


def check_p1_seed() -> dict:
    """T-JR-15 / T-JR-18 (edition 4): a loaded locked leg released by a retraction with P1,
    P2 and P3: the retract M2 seed rows of ``p1_retract_seed_log`` (one per counted seed) and
    the net force step of each."""
    options = _options(gate=True, lock_anchor_continuous=True, rod_flow_cap_all=True)
    plant = base._lifted_leg_plant(options)
    leg = base.FRONT_LEFT
    _drive(plant, leg, [0.0] * round(0.2 / base.KERNEL_STEP_S))
    ramp = [-RELEASE_SPEED_M_S * (1.0 - np.exp(-(k + 1) * base.KERNEL_STEP_S
                                                / base.VALVE_TAU_S))
            for k in range(round(0.6 / base.KERNEL_STEP_S))]
    _drive(plant, leg, ramp)
    record = plant.lock_log.record()
    return {"seed_count": record["p1_retract_seed_count"],
            "seed_log": record["p1_retract_seed_log"],
            "seed_log_columns": record["p1_retract_seed_log_columns"]}


def _relock_after_short_move(options) -> dict:
    """The lifted FR: locked through the floor drop (its rod spring takes the load change),
    a 20 ms extension, then zero: the relock keeps ``G_r,lock`` of the release decay."""
    plant = base._lifted_leg_plant(options)
    leg = base.LIFTED_LEG
    _drive(plant, leg, [0.0] * round(base.RELEASE_AT_S / base.KERNEL_STEP_S))
    speed = SHORT_MOVE_FRACTION * V_MAX_M_S
    rows = _drive(plant, leg, [speed] * round(SHORT_MOVE_S / base.KERNEL_STEP_S)
                  + [0.0] * round(RELOCK_RUN_S / base.KERNEL_STEP_S))
    relocks = [row for row in rows if row.get("relock")]
    out = {"relocks": len(relocks), "relock": relocks[0] if relocks else None,
           "knee_truth_minus_floor_Pa": None}
    if relocks and options.lock_anchor_continuous:
        knee_m = plant._locked_knee_m(leg)
        gr_at_knee = plant.Gr_lock[leg] + plant.kr[leg] * knee_m
        truth_at_knee = plant.p_r0[leg] - gr_at_knee / plant.A_ann[leg]
        out["knee_truth_minus_floor_Pa"] = float(truth_at_knee - plant.p_floor)
    out["rr_locked_ratio"] = float(plant.kr[RR] * plant.flow_limiter.params.A_h[RR]
                                   / (plant.kh[RR] * plant.A_ann[RR]))
    if getattr(plant, "lock_log", None) is not None:
        record = plant.lock_log.record()
        out["lock_log_rows"] = record["lock_log"]
        out["lock_log_columns"] = record["lock_log_columns"]
        out["relock_step_over_1bar_count"] = record["relock_step_over_1bar_count"]
    return out


def check_p2_anchor() -> dict:
    """T-JR-07: the relock step of the locked truth with P2 and with the r5 anchor."""
    return {"p2": _relock_after_short_move(_options(lock_anchor_continuous=True)),
            "r5": _relock_after_short_move(_options())}


CHECKS = {"p1_gate": check_p1_gate, "p2_anchor": check_p2_anchor, "p1_seed": check_p1_seed}


def main() -> None:
    check, out_path = sys.argv[1], Path(sys.argv[2])
    report = CHECKS[check]()
    report["foreign_modules"] = base._modules_outside_project()
    out_path.write_text(json.dumps(report, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
