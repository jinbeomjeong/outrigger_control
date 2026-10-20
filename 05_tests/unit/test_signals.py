"""Unit tests for the boundary signal types and the Record schema (plan 3.2-3.3)."""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from outrigger_sim import signals
from outrigger_sim.params import LEG_ORDER
from outrigger_sim.signals import (
    BUSHING_EVENT_FIELDS,
    BUSHING_EVENTS_NAME,
    ENERGY_FIELD_PREFIX,
    LEG_COUNT,
    RECORD_FIELDS,
    BushingEventKind,
    Command,
    InvalidSignalError,
    Measurements,
    TruthState,
    record_row,
    validate_record_arrays,
)

PLAN_RECORD_LINE_START = "- `Record`는 고정 이름 배열이다:"


def _measurement_values() -> dict[str, Any]:
    return {
        "t_s": 0.02,
        "specific_force_m_s2": [0.0, 0.0, 9.80665],
        "angular_rate_rad_s": [0.0, 0.0, 0.0],
        "head_pressure_Pa": [9.0e6, 9.1e6, 8.0e6, 8.1e6],
        "stroke_m": [0.10, 0.10, 0.12, 0.12],
    }


def _truth_values() -> dict[str, Any]:
    return {
        "t_s": 1.5,
        "body_pos_m": [0.0, 0.0, 0.2],
        "body_quat_wxyz": [1.0, 0.0, 0.0, 0.0],
        "body_vel_m_s": [0.0, 0.0, 0.0],
        "body_omega_rad_s": [0.0, 0.0, 0.0],
        "s_motor_m": [0.1, 0.1, 0.1, 0.1],
        "s_ref_m": [0.1, 0.1, 0.1, 0.1],
        "u_applied_m_s": [0.0, 0.0, 0.0, 0.0],
        "F_cyl_N": [1.0e5, 1.0e5, 0.9e5, 0.9e5],
        "F_contact_n_N": [1.05e5, 1.05e5, 0.95e5, 0.95e5],
        "F_contact_t_N": np.zeros((4, 2)),
        "is_pad_in_contact": [True, True, True, False],
        "F_crawler_N": [0.0, 0.0, 0.0],
        "bushing_anchor_m": [[1, 2, 0], [1, -2, 0], [-1, 2, 0], [np.nan] * 3],
    }


def _command() -> Command:
    return Command(t_s=1.5, leg_speed_m_s=[0.01, 0.01, -0.01, 0.0])


def _plan_record_names(project_root: Path) -> list[str]:
    plan = project_root / "00_docs" / "03_chrono" / "chrono_build_plan.md"
    for line in plan.read_text(encoding="utf-8").splitlines():
        if line.startswith(PLAN_RECORD_LINE_START):
            return re.findall(r"`([^`]+)`", line.removeprefix(PLAN_RECORD_LINE_START))
    raise AssertionError(f"plan line {PLAN_RECORD_LINE_START!r} not found")


# --- construction and validation ---------------------------------------------------------


def test_command_holds_four_leg_speeds_in_leg_order() -> None:
    command = _command()
    assert LEG_COUNT == len(LEG_ORDER) == 4
    assert command.leg_speed_m_s.shape == (4,)
    assert command.leg_speed_m_s.dtype == np.float64
    assert command.t_s == 1.5


def test_command_accepts_values_beyond_the_actuator_limit() -> None:
    # Saturation is the actuator model's job, not the type's.
    assert Command(t_s=0.0, leg_speed_m_s=[1.0, -1.0, 0.0, 0.0]).leg_speed_m_s[0] == 1.0


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("specific_force_m_s2", [0.0, 9.8]),
        ("angular_rate_rad_s", np.zeros((3, 1))),
        ("head_pressure_Pa", [1.0, 2.0, 3.0]),
        ("stroke_m", [0.1, 0.1, 0.1, np.nan]),
        ("head_pressure_Pa", [1.0, 2.0, 3.0, np.inf]),
        ("stroke_m", ["a", "b", "c", "d"]),
    ],
)
def test_measurements_reject_bad_arrays(field_name: str, bad_value: Any) -> None:
    values = _measurement_values() | {field_name: bad_value}
    with pytest.raises(InvalidSignalError, match=field_name) as caught:
        Measurements(**values)
    assert caught.value.field_name == field_name


@pytest.mark.parametrize("bad_time", [float("nan"), "0.02", None, True])
def test_time_must_be_a_finite_number(bad_time: Any) -> None:
    with pytest.raises(InvalidSignalError, match="t_s"):
        Command(t_s=bad_time, leg_speed_m_s=[0.0] * 4)


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("F_contact_t_N", np.zeros(4)),
        ("F_contact_t_N", np.zeros((2, 4))),
        ("bushing_anchor_m", np.zeros((4, 2))),
        ("is_pad_in_contact", [1, 1, 1, 0]),
        ("is_pad_in_contact", [True, True, True]),
        ("body_quat_wxyz", [0.0, 0.0, 0.0, 0.0]),
        ("body_quat_wxyz", [1.0, 0.0, 0.0]),
        ("F_crawler_N", [np.inf, 0.0, 0.0]),
    ],
)
def test_truth_state_rejects_bad_arrays(field_name: str, bad_value: Any) -> None:
    with pytest.raises(InvalidSignalError, match=field_name):
        TruthState(**(_truth_values() | {field_name: bad_value}))


def test_bushing_anchor_allows_nan_for_legs_without_a_bushing() -> None:
    truth = TruthState(**_truth_values())
    assert np.isnan(truth.bushing_anchor_m[3]).all()
    assert truth.is_pad_in_contact.dtype == np.bool_


# --- immutability ------------------------------------------------------------------------


def test_arrays_are_read_only_and_copied() -> None:
    caller_pressure = np.array([1.0, 2.0, 3.0, 4.0])
    measurements = Measurements(**(_measurement_values() | {"head_pressure_Pa": caller_pressure}))
    caller_pressure[0] = -1.0
    assert measurements.head_pressure_Pa[0] == 1.0
    with pytest.raises(ValueError, match="read-only"):
        measurements.head_pressure_Pa[0] = 0.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        measurements.stroke_m = np.zeros(4)  # type: ignore[misc]


def test_every_truth_array_is_read_only() -> None:
    truth = TruthState(**_truth_values())
    for field in dataclasses.fields(TruthState):
        value = getattr(truth, field.name)
        if isinstance(value, np.ndarray):
            assert not value.flags.writeable, field.name


def test_truth_and_measurements_do_not_share_field_names() -> None:
    truth_names = {field.name for field in dataclasses.fields(TruthState)}
    measurement_names = {field.name for field in dataclasses.fields(Measurements)}
    assert truth_names & measurement_names == {"t_s"}
    assert not issubclass(TruthState, Measurements)
    assert not issubclass(Measurements, TruthState)


# --- Record schema -----------------------------------------------------------------------


def test_record_schema_names_match_the_plan(project_root: Path) -> None:
    plan_names = _plan_record_names(project_root)
    schema_names = [field.name for field in RECORD_FIELDS]
    plan_arrays = [name.split("[")[0] for name in plan_names]
    assert BUSHING_EVENTS_NAME in plan_arrays
    assert f"{ENERGY_FIELD_PREFIX}*" in plan_arrays
    per_sample_plan_names = [
        name for name in plan_arrays if name not in {BUSHING_EVENTS_NAME, f"{ENERGY_FIELD_PREFIX}*"}
    ]
    core_schema_names = [name for name in schema_names if not name.startswith(ENERGY_FIELD_PREFIX)]
    assert core_schema_names == per_sample_plan_names


def test_record_schema_shapes_match_the_plan(project_root: Path) -> None:
    fields_by_name = {field.name: field for field in RECORD_FIELDS}
    for plan_name in _plan_record_names(project_root):
        match = re.fullmatch(r"(\w+)\[([\d,]+)\]", plan_name)
        if match is None:
            continue
        name, shape_text = match.groups()
        expected_shape = tuple(int(size) for size in shape_text.split(","))
        assert fields_by_name[name].sample_shape == expected_shape, name


def test_every_record_field_has_a_unit_and_valid_source() -> None:
    known_types = {"TruthState": TruthState, "Command": Command}
    for field in RECORD_FIELDS:
        assert field.unit
        if field.is_optional:
            assert field.name.startswith(ENERGY_FIELD_PREFIX)
            continue
        type_name, attribute = field.source.split(".")
        attribute_names = {item.name for item in dataclasses.fields(known_types[type_name])}
        assert attribute in attribute_names, field.source
    assert [column.name for column in BUSHING_EVENT_FIELDS] == ["t", "leg", "kind"]
    assert {kind.value for kind in BushingEventKind} == {1, 2}


def test_record_row_has_every_required_field_with_its_shape() -> None:
    row = record_row(TruthState(**_truth_values()), _command())
    required = [field for field in RECORD_FIELDS if not field.is_optional]
    assert list(row) == [field.name for field in required]
    for field in required:
        assert row[field.name].shape == field.sample_shape, field.name
    np.testing.assert_array_equal(row["u_cmd"], [0.01, 0.01, -0.01, 0.0])
    assert row["pad_in_contact"].dtype == np.bool_


def test_validate_record_arrays_accepts_stacked_rows() -> None:
    rows = [record_row(TruthState(**_truth_values()), _command()) for _ in range(3)]
    stacked = {name: np.stack([row[name] for row in rows]) for name in rows[0]}
    stacked["energy.kinetic"] = np.zeros(3)
    assert validate_record_arrays(stacked) == 3


def _valid_stack(sample_count: int = 2) -> dict[str, np.ndarray]:
    row = record_row(TruthState(**_truth_values()), _command())
    return {name: np.stack([value] * sample_count) for name, value in row.items()}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda arrays: arrays.pop("F_cyl"), "F_cyl"),
        (lambda arrays: arrays.update(F_contact_t=np.zeros((2, 4))), "F_contact_t"),
        (lambda arrays: arrays.update(t=np.zeros(3)), "samples"),
        (lambda arrays: arrays.update(stroke=np.zeros((2, 4))), "stroke"),
        (lambda arrays: arrays.update({"energy.heat": np.zeros(2)}), "energy.heat"),
        (lambda arrays: arrays.update(pad_in_contact=np.ones((2, 4))), "pad_in_contact"),
    ],
)
def test_validate_record_arrays_rejects_bad_sets(change, message: str) -> None:
    arrays = _valid_stack()
    change(arrays)
    with pytest.raises(InvalidSignalError, match=re.escape(message)):
        validate_record_arrays(arrays)


def test_module_has_no_engine_dependency() -> None:
    source = Path(signals.__file__).read_text(encoding="utf-8")
    for forbidden in ("import pychrono", "from pychrono"):
        assert forbidden not in source


# --- S6 additions: corrected stroke, stopped command, control period ---------------------


def test_corrected_stroke_is_optional_frozen_and_checked() -> None:
    assert Measurements(**_measurement_values()).stroke_corrected_m is None
    measurements = Measurements(
        **(_measurement_values() | {"stroke_corrected_m": [0.095, 0.095, 0.115, 0.115]})
    )
    assert measurements.stroke_corrected_m is not None
    assert measurements.stroke_corrected_m.dtype == np.float64
    assert not measurements.stroke_corrected_m.flags.writeable
    for bad_value in ([0.1, 0.1, 0.1], [0.1, 0.1, 0.1, np.nan]):
        with pytest.raises(InvalidSignalError, match="stroke_corrected_m"):
            Measurements(**(_measurement_values() | {"stroke_corrected_m": bad_value}))


def test_stopped_command_holds_every_leg() -> None:
    command = Command.stopped(1.25)
    assert command.t_s == 1.25
    assert command.leg_speed_m_s.tolist() == [0.0] * LEG_COUNT
    assert not command.leg_speed_m_s.flags.writeable


def test_default_control_period_is_20_ms() -> None:
    assert signals.DEFAULT_CONTROL_PERIOD_S == 0.02
