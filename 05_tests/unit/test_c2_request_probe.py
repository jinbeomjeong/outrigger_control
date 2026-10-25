"""``C2Controller.request_probe``: a repeated probe round from READY (spec rev. 39 205.3).

The bench of ``test_c2_r6.py`` (constant leg loads, strokes follow the commands). Bit identity
of runs that never call it: the controller code path is untouched (the R8-D1 closed loop of
``04_scripts/03_control/r8d1/c2py_r8d1_closed_loop.py`` gave a byte-identical JSON before and
after the change, 2026-10-24).
"""

from __future__ import annotations

import pytest
from test_c2_r6 import _Bench, _config, _names, _ready  # same test folder

from outrigger_sim.control.c2 import C2Controller, C2Geometry, C2Phase, ContactJudge
from outrigger_sim.params import load_params


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def test_request_in_ready_runs_one_more_probe_round_and_returns(geometry):
    bench = _ready(_Bench(C2Controller(geometry, _config()), geometry))
    controller = bench.controller
    rounds_before = len(controller.probe_history)
    # READY entry starts a U67 lock tail; the request waits until it has run.
    for _ in range(100):
        if controller.request_probe():
            break
        bench.step()
    assert controller.phase is C2Phase.PROBE
    assert "probe_request_rejected:busy" in _names(controller)
    assert "probe_requested" in _names(controller)
    bench.step()
    assert controller.phase is C2Phase.PROBE
    bench.run_until(lambda: controller.phase is C2Phase.READY)
    assert len(controller.probe_history) == rounds_before + 1
    assert all(result.is_grounded for result in controller.probe_history[-1])


def test_request_outside_ready_or_with_the_pressure_judge_is_rejected(geometry):
    bench = _Bench(C2Controller(geometry, _config()), geometry)
    bench.step()
    assert not bench.controller.request_probe()
    assert bench.controller.phase is not C2Phase.PROBE
    assert any(name.startswith("probe_request_rejected:") for name in _names(bench.controller))

    pressure = _ready(_Bench(C2Controller(geometry, _config(contact=ContactJudge.PRESSURE)),
                             geometry))
    assert not pressure.controller.request_probe()
    assert pressure.controller.phase is C2Phase.READY
