"""``outrigger_sim.hydraulics.flow_share``: bit identity with the coupled script and the laws.

The numerics were moved from ``04_scripts/04_hydraulic/coupled/flow_share.py``, which stays for
``model.py``, ``hand_calc.py`` and ``replay_share.py``; the identity tests keep the two equal.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

from outrigger_sim.hydraulics.flow_share import (
    FlowCircuit,
    FlowShareAssumptions,
    FlowShareLaw,
    PumpFlowLimiter,
    flow_circuit_from_params,
    share_flow,
    soft_min,
)
from outrigger_sim.params import load_params

COUPLED_DIR = Path(__file__).resolve().parents[2] / "04_scripts" / "04_hydraulic" / "coupled"
RANDOM_SEED = 20261104
RANDOM_CASES = 300
ETA_DESIGN = 0.95
ETA_LOW = 0.85
MAX_LOAD_PA = 150e5
MIN_FORCE_N = -2e3
MAX_FORCE_N = 150e3
TYPICAL_LOADS_PA = np.array([89.8e5, 88.3e5, 76.9e5, 75.0e5])


def _load_coupled_flow_share() -> ModuleType:
    """The script under a private name, so that no module called ``flow_share`` stays imported."""
    spec = importlib.util.spec_from_file_location(
        "_coupled_flow_share_for_test", COUPLED_DIR / "flow_share.py"
    )
    module = importlib.util.module_from_spec(spec)
    # dataclass(frozen=True) with ``from __future__ import annotations`` reads sys.modules
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


COUPLED = _load_coupled_flow_share()


@pytest.fixture(scope="module")
def circuit() -> FlowCircuit:
    return flow_circuit_from_params(load_params())


def _assumptions(eta_v: float, **changes) -> FlowShareAssumptions:
    return FlowShareAssumptions(eta_v=eta_v, is_enabled=True, **changes)


def _coupled_config(circuit: FlowCircuit, assumptions: FlowShareAssumptions):
    return COUPLED.FlowShareConfig(
        A_h=circuit.head_area_m2,
        A_r=circuit.annulus_area_m2,
        dp_c=assumptions.compensator_drop_Pa,
        dp_ls=assumptions.unloading_drop_Pa,
        width=assumptions.smoothing_width_Pa,
        law=assumptions.law.value,
        enabled=assumptions.is_enabled,
        X_comp=assumptions.compensator_open_coefficient,
        Cs_unl=assumptions.unloading_spring_coefficient,
        Cf_unl=assumptions.unloading_flow_force_coefficient,
        X_unl=assumptions.unloading_open_coefficient,
        p_T=assumptions.tank_pressure_Pa,
        p_relief=circuit.relief_pressure_Pa,
    )


def _random_request(rng: np.random.Generator, v_max: float) -> np.ndarray:
    if rng.random() < 0.5:  # all legs near v_max: the saturated chunks of TOUCH and LEVEL
        return rng.uniform(0.9 * v_max, v_max, 4)
    return rng.uniform(-v_max, v_max, 4) * rng.choice([0.0, 1.0], 4, p=[0.2, 0.8])


def _assert_same_bits(new, old) -> None:
    pairs = (
        (new.speed_m_s, old.v),
        (new.flow_m3_s, old.Q),
        (new.spool_drop_Pa, old.y),
        (new.is_limited, old.limited),
    )
    for new_array, old_array in pairs:
        assert new_array.tobytes() == old_array.tobytes()
    assert new.gallery_pressure_Pa == old.p_P
    assert new.bypass_flow_m3_s == old.Q_byp
    assert new.load_sense_Pa == old.ls
    assert new.demand_m3_s == old.Q_dem


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"law": FlowShareLaw.PROPORTIONAL},
        {"compensator_drop_Pa": 6e5, "unloading_drop_Pa": 12e5},
        {"compensator_drop_Pa": 20e5, "unloading_drop_Pa": 30e5},
        {"smoothing_width_Pa": 0.5e5},
        {"smoothing_width_Pa": 2e5},
        {"smoothing_width_Pa": 0.0},
    ],
)
@pytest.mark.parametrize("eta_v", [ETA_DESIGN, 0.90, ETA_LOW])
def test_same_bits_as_the_coupled_script(circuit, eta_v, changes):
    assumptions = _assumptions(eta_v, **changes)
    config = _coupled_config(circuit, assumptions)
    supply = circuit.pump_flow_m3_s * eta_v
    rng = np.random.default_rng(RANDOM_SEED)
    limited_cases = 0
    for _ in range(RANDOM_CASES):
        request = _random_request(rng, circuit.max_speed_m_s)
        load = rng.uniform(0.0, MAX_LOAD_PA, 4)
        new = share_flow(request, load, circuit, assumptions)
        _assert_same_bits(new, COUPLED.share(request, load, supply, config))
        limited_cases += int(new.is_limited.any())
    if eta_v < ETA_DESIGN:
        assert limited_cases > 0, "the comparison must reach the limited branch"


def test_same_bits_with_the_option_off(circuit):
    assumptions = FlowShareAssumptions(eta_v=ETA_LOW)
    config = _coupled_config(circuit, assumptions)
    request = np.full(4, circuit.max_speed_m_s)
    new = share_flow(request, TYPICAL_LOADS_PA, circuit, assumptions)
    old = COUPLED.share(request, TYPICAL_LOADS_PA, circuit.pump_flow_m3_s * ETA_LOW, config)
    _assert_same_bits(new, old)


def test_option_is_off_by_default_and_returns_the_request_bits(circuit):
    assert FlowShareAssumptions(eta_v=ETA_LOW).is_enabled is False
    limiter = PumpFlowLimiter(circuit, FlowShareAssumptions(eta_v=ETA_LOW))
    request = np.full(4, circuit.max_speed_m_s)
    delivered = limiter.delivered_speeds_m_s(request, np.full(4, 90e3))
    assert delivered.tobytes() == request.tobytes()
    assert delivered is not request


def test_soft_min_is_exact_outside_the_band():
    assert soft_min(10.0, 13.0, 2.0) == 10.0
    assert soft_min(13.0, 10.0, 2.0) == 10.0
    assert soft_min(10.0, 10.0, 2.0) == pytest.approx(10.0 - 0.5)


def test_circuit_comes_from_the_yaml_values():
    params = load_params()
    circuit = flow_circuit_from_params(params)
    assert circuit.pump_flow_m3_s == params.get("actuator.pump_flow_m3_s")
    assert circuit.head_area_m2[3] == params.get("legs.RR.cylinder.head_area_m2")
    assert circuit.annulus_area_m2[0] == params.get("legs.FL.cylinder.annulus_area_m2")


def test_four_legs_at_v_max_are_met_at_the_design_point(circuit):
    """Criteria V-1: eta 0.95 is the design point of v_max, inside the supply tolerance."""
    limiter = PumpFlowLimiter(circuit, _assumptions(ETA_DESIGN))
    request = np.full(4, circuit.max_speed_m_s)
    delivered = limiter.delivered_speeds_m_s(request, np.full(4, 90e3))
    assert delivered.tobytes() == request.tobytes()
    result = limiter.solve(request, limiter.load_pressures_Pa(request, np.full(4, 90e3)))
    assert result.speed_m_s.tobytes() == request.tobytes()


def test_supply_is_never_exceeded_and_a_met_demand_is_delivered(circuit):
    """Criteria V-2 on random requests."""
    limiter = PumpFlowLimiter(circuit, _assumptions(ETA_LOW))
    rng = np.random.default_rng(RANDOM_SEED)
    for _ in range(RANDOM_CASES):
        request = _random_request(rng, circuit.max_speed_m_s)
        result = limiter.solve(request, rng.uniform(0.0, MAX_LOAD_PA, 4))
        assert result.flow_m3_s.sum() <= limiter.supply_m3_s * (1.0 + 1e-6)
        assert np.all(np.abs(result.speed_m_s) <= np.abs(request) + 1e-15)
        if result.demand_m3_s <= limiter.supply_m3_s * 0.999:
            assert np.allclose(result.speed_m_s, request, atol=1e-12)


def test_priority_slows_the_highest_load_first(circuit):
    request = np.full(4, circuit.max_speed_m_s)
    result = share_flow(request, TYPICAL_LOADS_PA, circuit, _assumptions(0.90))
    assert result.speed_m_s[0] < result.speed_m_s[1] < result.speed_m_s[2]


def test_proportional_scales_all_legs_alike(circuit):
    request = np.full(4, circuit.max_speed_m_s)
    assumptions = _assumptions(ETA_LOW, law=FlowShareLaw.PROPORTIONAL)
    result = share_flow(request, TYPICAL_LOADS_PA, circuit, assumptions)
    assert np.ptp(result.speed_m_s) == pytest.approx(0.0, abs=1e-9)
    speed_ratio = result.speed_m_s[0] / circuit.max_speed_m_s
    assert speed_ratio == pytest.approx(ETA_LOW / ETA_DESIGN, rel=1e-4)


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"law": FlowShareLaw.PROPORTIONAL},
        {"compensator_drop_Pa": 6e5, "unloading_drop_Pa": 12e5},
        {"smoothing_width_Pa": 2e5},
    ],
)
@pytest.mark.parametrize("eta_v", [ETA_DESIGN, ETA_LOW])
def test_cheap_path_agrees_with_the_full_solution(circuit, eta_v, changes):
    limiter = PumpFlowLimiter(circuit, _assumptions(eta_v, **changes))
    rng = np.random.default_rng(RANDOM_SEED)
    cheap_cases = 0
    for _ in range(RANDOM_CASES):
        request = rng.uniform(-circuit.max_speed_m_s, circuit.max_speed_m_s, 4)
        request = request * rng.choice([0.0, 0.1, 1.0], 4)
        force = rng.uniform(MIN_FORCE_N, MAX_FORCE_N, 4)
        load = limiter.load_pressures_Pa(request, force)
        if limiter.is_demand_met_with_margin(request, load):
            cheap_cases += 1
            assert limiter.solve(request, load).speed_m_s.tobytes() == request.tobytes()
        delivered = limiter.delivered_speeds_m_s(request, force)
        assert delivered.tobytes() == limiter.solve(request, load).speed_m_s.tobytes()
    assert cheap_cases > 0


def test_extending_rod_pressure_is_the_meter_out_value(circuit):
    limiter = PumpFlowLimiter(circuit, _assumptions(ETA_LOW))
    assumptions = limiter.assumptions
    speed = circuit.max_speed_m_s
    request = np.array([speed, -speed, 0.0, speed / 2])
    force = np.array([100e3, 100e3, 100e3, 50e3])
    load = limiter.load_pressures_Pa(request, force)
    area_ratio = circuit.annulus_area_m2 / circuit.head_area_m2
    meter_out = area_ratio**2 * assumptions.compensator_drop_Pa
    rod_pressure = assumptions.tank_pressure_Pa + meter_out
    expected_extending = (force + circuit.annulus_area_m2 * rod_pressure) / circuit.head_area_m2
    assert load[0] == pytest.approx(expected_extending[0])
    assert load[3] == pytest.approx(expected_extending[3])
    assert load[1] == assumptions.pilot_pressure_Pa


def test_load_pressure_follows_the_force_of_the_chunk(circuit):
    """Condition 2: a force change moves the load, and with it the delivered speeds."""
    limiter = PumpFlowLimiter(circuit, _assumptions(ETA_LOW))
    request = np.full(4, circuit.max_speed_m_s)
    balanced = limiter.delivered_speeds_m_s(request, np.full(4, 60e3))
    front_heavy = limiter.delivered_speeds_m_s(request, np.array([200e3, 200e3, 60e3, 60e3]))
    assert not np.array_equal(balanced, front_heavy)
