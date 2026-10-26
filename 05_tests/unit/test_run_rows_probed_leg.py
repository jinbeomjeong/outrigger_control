"""(가) control 2026-10-26: the 10 Hz runner rows record ``probed_leg`` (record only, no Chrono).

* :func:`outrigger_sim.chrono.run_rows.probed_leg` follows ``C2Controller._probed_leg`` (also
  through an ``inner`` wrapper) and is ``None`` outside PROBE;
* ``run_S6C.R8Series`` (S6C, S7C, S8C ``S8Series``) stores it as int8 with -1 = none and leaves
  the command untouched;
* on the reduced 6-DoF plant (numba) a C2 closed loop through PROBE issues bit-identical
  commands with and without the reads, and the recorded leg is set exactly in the PROBE periods
  of a running round.
"""

from __future__ import annotations

import copy
import importlib.util
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from outrigger_sim.chrono import run_rows
from outrigger_sim.control.c2 import C2Config, C2Controller, C2Phase
from outrigger_sim.params import load_params

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "04_scripts" / "02_chrono"


class _FakeC2:
    def __init__(self, leg):
        self.leg = leg
        self.phase = C2Phase.PROBE if leg is not None else C2Phase.LEVEL
        self.probe_history: list = []
        self.events: list = []
        self.calls = 0

    def _probed_leg(self):
        self.calls += 1
        return self.leg

    def meta(self):
        return {}


def test_probed_leg_reads_the_controller_rule() -> None:
    assert run_rows.probed_leg(_FakeC2(2)) == 2
    assert run_rows.probed_leg(_FakeC2(None)) is None
    assert run_rows.probed_leg(SimpleNamespace(inner=_FakeC2(1))) == 1  # wrapper unwrapped
    assert run_rows.probed_leg(SimpleNamespace()) is None  # no method: getattr rule
    assert run_rows.probed_leg_code(_FakeC2(None)) == run_rows.PROBED_LEG_NONE == -1
    assert run_rows.probed_leg_code(_FakeC2(3)) == 3


def test_fresh_controller_has_the_method_and_no_probed_leg() -> None:
    c2 = C2Controller.from_params(load_params(level="top"), C2Config().with_10hz_d1())
    assert callable(getattr(c2, "_probed_leg", None))
    assert run_rows.probed_leg(c2) is None  # not in PROBE


@pytest.fixture(scope="module")
def run_s6c():
    env = dict(os.environ)
    path = list(sys.path)
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("run_S6C_test_probed", SCRIPTS / "run_S6C.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        os.environ.clear()
        os.environ.update(env)
    yield mod
    sys.modules.pop(spec.name, None)
    sys.path[:] = path


def _meas(t):
    return SimpleNamespace(t_s=t, imu_specific_force_samples_m_s2=None,
                           imu_angular_rate_samples_rad_s=None)


def test_r8series_records_probed_leg_and_keeps_the_command(run_s6c, tmp_path) -> None:
    model = SimpleNamespace(actuator=SimpleNamespace(valve_state_m_s=np.zeros(4),
                                                     amp_output_m_s=np.zeros(4)))
    c2 = _FakeC2(None)
    series = run_s6c.R8Series(model, c2)
    issued = []
    for k, leg in enumerate([None, 0, 0, 3, None]):
        c2.leg = leg
        command = SimpleNamespace(leg_speed_m_s=(0.001 * k, -0.002, 0.0, 0.003))
        before = copy.deepcopy(command)
        series(_meas(0.1 * k), command)
        assert command == before  # record only
        issued.append(command.leg_speed_m_s)
    info = series.save(tmp_path / "r8_series.npz")
    with np.load(tmp_path / "r8_series.npz") as arr:
        assert arr["probed_leg"].dtype == np.int8
        np.testing.assert_array_equal(arr["probed_leg"], [-1, 0, 0, 3, -1])
        np.testing.assert_array_equal(arr["issued_u"], np.asarray(issued))
    assert "probed_leg" in info and "-1" in info["probed_leg"]


# --- closed loop on the reduced plant: commands unchanged by the reads ---------------------------


def _closed_loop(read_probed_leg: bool, limit_s: float = 200.0):
    pytest.importorskip("numba", reason="the reduced plant kernel needs numba")
    sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
    import run_control_comparison as reduced_model

    from outrigger_sim.control.c2 import TargetSettings
    from outrigger_sim.control.target import CrawlerSettleMap, SlopeLimitMode
    from outrigger_sim.signals import Measurements

    params = load_params()
    target = TargetSettings(slope_limit_mode=SlopeLimitMode.VERIFICATION,
                            crawler_settle_map=CrawlerSettleMap.for_level("top"))
    config = C2Config(target=target,
                      output_ramp_time_s=params.actuator.command_ramp_s).with_r5_behaviour()
    controller = C2Controller.from_params(params, config)
    plant = reduced_model.Plant("top", 0.0, 3.5)
    plant.step(np.zeros(4), int(round(reduced_model.SETTLE_ON_CRAWLER_S / reduced_model.DT)))
    plant.t = 0.0
    command = np.zeros(4)
    commands, legs, phases = [], [], []
    left_probe = False
    while plant.t < limit_s and not left_probe:
        acc = plant.step(command, reduced_model.N_SUB)
        meas = Measurements(
            t_s=plant.t, specific_force_m_s2=acc[0:3] / reduced_model.N_SUB,
            angular_rate_rad_s=plant.w.copy(),
            head_pressure_Pa=plant.pressure() / controller.geometry.head_area_m2,
            stroke_m=plant.sref.copy(), stroke_corrected_m=plant.x.copy())
        command = np.array(controller.update(meas).leg_speed_m_s)
        commands.append(command.copy())
        phases.append(controller.phase)
        if read_probed_leg:
            legs.append(run_rows.probed_leg(controller))
        left_probe = (len(phases) > 1 and phases[-2] is C2Phase.PROBE
                      and phases[-1] is not C2Phase.PROBE)
    return np.asarray(commands), legs, phases


def test_closed_loop_commands_unchanged_and_leg_only_in_probe() -> None:
    with_reads, legs, phases = _closed_loop(True)
    without, _, phases2 = _closed_loop(False)
    assert phases == phases2
    np.testing.assert_array_equal(with_reads, without)  # bit-identical commands
    assert any(p is C2Phase.PROBE for p in phases), "the run did not reach PROBE"
    probe_legs = [leg for leg, p in zip(legs, phases, strict=True) if p is C2Phase.PROBE]
    assert any(leg is not None for leg in probe_legs)
    assert all(leg is None for leg, p in zip(legs, phases, strict=True) if p is not C2Phase.PROBE)
    assert {leg for leg in probe_legs if leg is not None} <= {0, 1, 2, 3}


# --- S9 level: r8_series.npz with the same probed_leg key --------------------------------------


def test_minimal_r8_series_matches_the_r8series_keys(run_s6c, tmp_path) -> None:
    """run_S9 level writes ``r8_series.npz`` via ``MinimalR8Series``: the keys the O-4 replay
    reads (``computed_u``, ``probed_leg``) with the R8Series dtypes / meaning."""
    from outrigger_sim.control.r5_fallback_replay import RECORDED_PROBED_LEG_KEY

    c2 = _FakeC2(None)
    c2.computed_output_m_s = lambda: np.array([0.001, 0.0, -0.001, 0.0])
    mini = run_rows.MinimalR8Series(c2)
    model = SimpleNamespace(actuator=SimpleNamespace(valve_state_m_s=np.zeros(4),
                                                     amp_output_m_s=np.zeros(4)))
    full = run_s6c.R8Series(model, c2)
    for k, leg in enumerate([None, 2, None]):
        c2.leg = leg
        c2.phase = C2Phase.PROBE if leg is not None else C2Phase.LEVEL
        command = SimpleNamespace(leg_speed_m_s=(0.0, 0.001 * k, 0.0, 0.0))
        before = copy.deepcopy(command)
        mini(_meas(0.1 * k), command)
        full(_meas(0.1 * k), command)
        assert command == before
    info = mini.save(tmp_path / run_rows.R8_SERIES_NAME)
    full.save(tmp_path / "full.npz")
    assert info["keys"] == ["computed_u", "issued_u", "phase", "probed_leg", "t"]
    with np.load(tmp_path / run_rows.R8_SERIES_NAME) as a, np.load(tmp_path / "full.npz") as b:
        assert RECORDED_PROBED_LEG_KEY in a.files
        for key in info["keys"]:
            assert a[key].dtype == b[key].dtype, key
            np.testing.assert_array_equal(a[key], b[key])
        np.testing.assert_array_equal(a["probed_leg"], [-1, 2, -1])


def test_s9_level_writes_r8_series_with_probed_leg() -> None:
    """Static check of the run_S9 level path (no Chrono run): the recorder is called in
    ``observe`` and saved as ``r8_series.npz``; ``s9_rows`` keeps ``probed_leg`` as well."""
    text = (SCRIPTS / "run_S9.py").read_text(encoding="utf-8")
    assert "r8_rows = MinimalR8Series(c2)" in text
    assert "r8_rows(meas, command)" in text
    assert "r8_rows.save(d / R8_SERIES_NAME)" in text
    assert 'row["probed_leg"] = probed_leg(c2)' in text


# --- C-2: S7 L2b pads fields --------------------------------------------------------------------


def test_s7c_l2b_pads_seal_fields_meta() -> None:
    env = dict(os.environ)
    path = list(sys.path)
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("run_S7C_test_pads", SCRIPTS / "run_S7C.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        os.environ.clear()
        os.environ.update(env)
    try:
        params = load_params(level="top", model="L2b_NSC")
        assert float(params.l2b.seal_friction.level_N) == 0.0  # YAML: F_s = 0 on the S7 path
        meta = mod.l2b_pads_seal_fields_meta(
            params, SimpleNamespace(actuator=SimpleNamespace(friction_path=False)))
        assert meta["added"] is False and meta["F_s_front_N"] == 0.0
        assert "F_s = 0" in meta["reason"] and "f_seal" in meta["fields_s8"]
        with pytest.raises(RuntimeError, match="run_S8C"):
            mod.l2b_pads_seal_fields_meta(
                params, SimpleNamespace(actuator=SimpleNamespace(friction_path=True)))
    finally:
        sys.modules.pop(spec.name, None)
        sys.path[:] = path
