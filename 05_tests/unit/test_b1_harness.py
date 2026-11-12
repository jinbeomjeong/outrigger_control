"""B1 creep basis harness support (``04_scripts/03_control/b1``): record hooks and job list.

``b1_record``: the period record wraps ``update`` once and returns the command unchanged, its
clearance estimate equals the controller's own without creating the soil state, and the H-M0
research subclass keeps E3c10 ``enable`` with ``margin_m`` 0. ``b1_harness``: the 32 jobs of
rules 2.2, run ids, the ``run_v5`` job (``mass_scale`` only when not 1) and the shadow pairs.
The job list needs the harness modules (numba); the rest runs anywhere with numpy.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
B1_DIR = ROOT / "04_scripts" / "03_control" / "b1"
if str(B1_DIR) not in sys.path:
    sys.path.insert(0, str(B1_DIR))

import b1_harness  # noqa: E402
import b1_record  # noqa: E402

from outrigger_sim.control.c2 import C2Config, C2Controller  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402


# ------------------------------------------------------------------------- b1_record
class _FakeController:
    """Just what ``_period_entry`` reads."""

    def __init__(self) -> None:
        self.calls = 0
        self.config = SimpleNamespace(soil=SimpleNamespace(enable=True), period_s=0.1)
        self.geometry = SimpleNamespace(
            clearance_corners_m=lambda stroke: np.asarray(stroke, float)[:4] * 0.1)
        self._state = SimpleNamespace(
            soil=SimpleNamespace(has_corner_bias=True, corner_bias_m=np.full(4, 0.001)),
            last_reading=SimpleNamespace(rod_stroke_m=np.array([0.5, 0.4, 0.3, 0.2])),
            last_cylinder_force_N=np.array([1.0, 2.0, 3.0, 4.0]))
        self.phase = "level"
        self.filtered_attitude_rad = (0.01, -0.02)

    def update(self, measurements):
        self.calls += 1
        return ("command", measurements.t_s)

    def _clearance_target_m(self) -> float:
        return 0.08

    def _period_raw_attitude_rad(self) -> tuple[float, float]:
        return (0.003, -0.004)


def test_period_record_wraps_once_and_keeps_the_command() -> None:
    cls = type("Fake", (_FakeController,), {})
    assert b1_record.install_period_record(cls) is True
    assert b1_record.install_period_record(cls) is False
    controller = cls()
    for k in range(3):
        measurements = SimpleNamespace(t_s=0.1 * (k + 1), stroke_m=np.full(4, 0.3 + k))
        assert controller.update(measurements) == ("command", measurements.t_s)
    assert controller.calls == 3
    arrays = b1_record.period_record_arrays(controller)
    assert arrays["n"].tolist() == [1, 2, 3]
    assert arrays["c_hat_m"][0] == pytest.approx(0.02 - 0.001)
    assert arrays["c_hat_corner_m"][0] == pytest.approx([0.049, 0.039, 0.029, 0.019])
    assert arrays["c_target_m"].tolist() == [0.08] * 3
    assert arrays["att_raw_rad"][0].tolist() == [0.003, -0.004]  # rules 7.1 / R-C1
    assert arrays["load_read_N"].shape == (3, 4) and arrays["att_filt_rad"].shape == (3, 2)


def test_period_record_has_the_r_c1_names() -> None:
    cls = type("FakeNames", (_FakeController,), {})
    b1_record.install_period_record(cls)
    controller = cls()
    controller.update(SimpleNamespace(t_s=0.1, stroke_m=np.zeros(4)))
    arrays = b1_record.period_record_arrays(controller)
    for name in ("n", "load_read_N", "att_raw_rad", "c_hat_m", "c_hat_corner_m", "c_target_m"):
        assert name in arrays, name


def test_subclass_of_a_recorded_class_records_once_per_period() -> None:
    """The harness installs on the base class only; its subclasses (LoggedController, the
    H-M0 class) inherit one wrapper, so one entry per period."""
    base = type("FakeBase", (_FakeController,), {})
    b1_record.install_period_record(base)

    class Child(base):
        def update(self, measurements):
            return super().update(measurements)

    controller = Child()
    controller.update(SimpleNamespace(t_s=0.1, stroke_m=np.zeros(4)))
    assert len(controller.__dict__[b1_record.PERIOD_RECORD_ATTRIBUTE]) == 1


@pytest.fixture(scope="module")
def preset_controller() -> C2Controller:
    controller = C2Controller.from_params(load_params(), C2Config().with_10hz_d1())
    controller.reset()
    return controller


def test_clearance_estimate_matches_the_controller(preset_controller) -> None:
    stroke = np.array([0.30, 0.31, 0.29, 0.28])
    assert b1_record._clearance_estimate_m(preset_controller, stroke) == (
        preset_controller._clearance_estimate_m(stroke))


def test_clearance_estimate_does_not_create_the_soil_state(preset_controller) -> None:
    import copy

    controller = copy.deepcopy(preset_controller)
    controller._state.soil = None
    stroke = np.array([0.30, 0.31, 0.29, 0.28])
    value = b1_record._clearance_estimate_m(controller, stroke)
    assert controller._state.soil is None
    assert value == float(np.min(controller.geometry.clearance_corners_m(stroke)))


def test_margin_zero_subclass_keeps_enable_and_sets_margin_zero() -> None:
    cls = b1_record.make_margin_zero_class(C2Controller)
    preset = C2Config().with_10hz_d1()
    controller = cls.from_params(load_params(), preset)
    margin = controller.config.slope_clearance_margin
    assert type(controller).__name__ == b1_record.MARGIN_ZERO_CLASS_NAME
    assert margin.enable is True and margin.margin_m == 0.0
    assert margin.flat_soil_margin_m == preset.slope_clearance_margin.flat_soil_margin_m
    assert margin.tilt_min_rad == preset.slope_clearance_margin.tilt_min_rad
    record = b1_record.controller_record(controller)
    assert record["is_margin_zero_class"] is True and record["slope_margin_m"] == 0.0


def test_margin_zero_subclass_refuses_a_config_without_e3c10() -> None:
    cls = b1_record.make_margin_zero_class(C2Controller)
    with pytest.raises(ValueError, match="enable"):
        cls.from_params(load_params(), C2Config())


# ------------------------------------------------------------------------- b1_harness
def test_run_ids_and_npz_names() -> None:
    assert b1_harness.run_id("H-P", "C1", "VB", 2e-3) == "H-P|C1|VB|e0.002"
    assert b1_harness.npz_name("H-P|C1|VB|e0.002") == "H-P_C1_VB_e0p002.npz"


def test_run_v5_job_carries_mass_only_when_scaled() -> None:
    job = {"b1": {"mass_scale": 1.0}, "d1": {"key": "k"}, "setting": "VB", "eps": 0.0}
    assert "mass_scale" not in b1_harness.run_v5_job(job)
    job["b1"]["mass_scale"] = 1.1
    assert b1_harness.run_v5_job(job)["mass_scale"] == 1.1


def test_shadow_pair_check_states() -> None:
    lines = [{"run_id": "H-P|C1|VB|e0", "commands_sha256": "a"},
             {"run_id": "H-SH0|C1|VB|e0", "commands_sha256": "a"},
             {"run_id": "H-P|C2|VB|e0", "commands_sha256": "a"},
             {"run_id": "H-SH0|C2|VB|e0", "commands_sha256": "b"}]
    result = b1_harness.shadow_pair_check(lines)
    assert result["pairs"] == {"C1": "same", "C2": "DIFF", "C4": "missing", "C5": "missing"}
    assert result["all_same"] is False


def test_slope_mismatch_is_reported() -> None:
    job = {"b1": {"run_id": "H-P|C4|VB|e0", "row_id": "C4"},
           "d1": {"roll_deg": 1.925, "pitch_deg": 1.4002}}
    assert b1_harness.slope_mismatches([job])


def test_job_list_is_rules_2_2() -> None:
    pytest.importorskip("numba")
    jobs = b1_harness.b1_jobs()
    groups = [job["b1"]["group"] for job in jobs]
    assert {g: groups.count(g) for g in set(groups)} == {"H-P": 20, "H-W": 4, "H-M0": 4,
                                                         "H-SH0": 4}
    assert len({job["b1"]["run_id"] for job in jobs}) == 32
    assert not b1_harness.slope_mismatches(jobs)
    assert all(job["b1"]["shadow"] is (job["b1"]["group"] != "H-SH0") for job in jobs)
    assert all(job["b1"]["mass_scale"] == (1.1 if job["b1"]["group"] == "H-W" else 1.0)
               for job in jobs)
    assert {job["d1"]["key"] for job in jobs if job["b1"]["group"] == "H-M0"} == {
        "D1|H-S-0|J2|B|fdown-rec|K1", "D1|H-S-0|J2|T|fup-rec|K1"}
