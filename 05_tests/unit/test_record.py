"""Unit tests for the Record and snapshot file I/O (plan 3.1-3.2, R16)."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra import numpy as hnp

from outrigger_sim import record as record_module
from outrigger_sim.engine import EngineInfo, Snapshot, SnapshotMismatchError
from outrigger_sim.params import LEG_ORDER, Params, load_params
from outrigger_sim.record import (
    BUSHING_EVENT_DTYPES,
    DEFAULT_INPUT_LAG_STEPS,
    DEFAULT_STATES_DIR,
    MEASUREMENT_FIELDS,
    STROKE_TRUE_FIELD,
    Record,
    Recorder,
    RecordError,
    SensorSetup,
    load_record,
    load_snapshot,
    make_run_meta,
    record_paths,
    save_record,
    save_snapshot,
    snapshot_paths,
)
from outrigger_sim.signals import (
    ENERGY_TERMS,
    RECORD_FIELDS,
    BushingEventKind,
    Command,
    InvalidSignalError,
    Measurements,
    TruthState,
)

ENGINE = EngineInfo(name="fake", version="0.1", model="L1")
SNAPSHOT_SHA256 = "a" * 64
OTHER_SHA256 = "b" * 64

# database=None: no .hypothesis/ example database is left in the project.
FILE_IO_SETTINGS = settings(max_examples=25, deadline=None, database=None)


# --- builders ----------------------------------------------------------------------------


def _truth(t_s: float, *, stroke_true_m: Any = None) -> TruthState:
    return TruthState(
        t_s=t_s,
        body_pos_m=[0.01 * t_s, 0.0, 0.2],
        body_quat_wxyz=[1.0, 0.0, 0.0, 0.0],
        body_vel_m_s=[0.0, 0.0, 0.0],
        body_omega_rad_s=[0.0, 1e-3, 0.0],
        s_motor_m=[0.10, 0.10, 0.12, 0.12],
        s_ref_m=[0.10, 0.10, 0.12, 0.12],
        u_applied_m_s=[0.0, 0.0, 0.0, 0.0],
        F_cyl_N=[1.0e5, 1.0e5, 0.9e5, 0.9e5],
        F_contact_n_N=[1.05e5, 1.05e5, 0.95e5, 0.95e5],
        F_contact_t_N=np.full((4, 2), t_s),
        is_pad_in_contact=[True, True, True, False],
        F_crawler_N=[0.0, 0.0, 0.0],
        bushing_anchor_m=[[1, 2, 0], [1, -2, 0], [-1, 2, 0], [np.nan] * 3],
        stroke_true_m=stroke_true_m,
    )


def _command(t_s: float) -> Command:
    return Command(t_s=t_s, leg_speed_m_s=[0.01, 0.01, -0.01, 0.0])


def _measurements(t_s: float) -> Measurements:
    return Measurements(
        t_s=t_s,
        specific_force_m_s2=[0.01, -0.02, 9.80665],
        angular_rate_rad_s=[1e-4, 0.0, -1e-4],
        head_pressure_Pa=[9.0e6, 9.1e6, 8.0e6, 8.1e6],
        stroke_m=[0.105, 0.105, 0.125, 0.125],
    )


def _energy(t_s: float) -> dict[str, float]:
    return {term: 1.0 + t_s for term in ENERGY_TERMS}


def _engine_meta(params: Params) -> dict[str, Any]:
    return {
        "engine": "fake",
        "engine_version": "0.1",
        "model": "L1",
        "dt_s": 1e-4,
        "params_sha256": params.sha256,
        "solver": {"type": "SPARSE_LU", "lock_sparsity_pattern": True},
    }


def _run_meta(params: Params) -> dict[str, Any]:
    return make_run_meta(
        params,
        _engine_meta(params),
        scenario="settle",
        scenario_settings={"start": "on_pads", "duration_s": 10.0},
        sensors=SensorSetup(
            config={"imu_grade": "good", "mount_m": [0.31, 0.88, 0.04]}, noise_seed=1234
        ),
    )


def _full_record(params: Params, sample_count: int = 4) -> Record:
    """Record with every optional group: stroke_true, meas.*, energy.* and events."""
    recorder = Recorder(_run_meta(params))
    for index in range(sample_count):
        t_s = 0.02 * index
        recorder.append(
            _truth(t_s, stroke_true_m=[0.095, 0.095, 0.115, 0.115]),
            _command(t_s),
            _measurements(t_s),
            _energy(t_s),
        )
    recorder.add_bushing_event(0.0, 0, BushingEventKind.CREATED)
    recorder.add_bushing_event(0.04, 3, BushingEventKind.REMOVED)
    return recorder.finish()


def _snapshot(time_s: float = 0.1 + 0.2, sha256: str = SNAPSHOT_SHA256) -> Snapshot:
    return Snapshot(
        engine=ENGINE,
        params_sha256=sha256,
        time_s=time_s,
        held_command=Command(t_s=0.28, leg_speed_m_s=[0.0226, -0.0226, 1e-17, 0.0]),
        payload={
            "body_state": np.linspace(-1.0, 1.0, 13) / 3.0,
            "bushing_active": np.array([True, False, True, True]),
            "lift_counter": np.array([0, 3, 7, 10], dtype=np.int32),
            "s_ref_m": np.array([0.1, 0.2, 0.3, 0.4]) * (1.0 / 7.0),
        },
    )


def _assert_bit_identical(expected: Mapping[str, np.ndarray], actual: Mapping[str, np.ndarray]):
    assert sorted(actual) == sorted(expected)
    for name, array in expected.items():
        assert actual[name].dtype == array.dtype, name
        assert actual[name].shape == array.shape, name
        assert actual[name].tobytes() == array.tobytes(), name


@pytest.fixture(scope="module")
def params(params_path: Path) -> Params:
    return load_params(params_path)


# --- Record round trip -------------------------------------------------------------------


def test_record_round_trip_is_bit_identical(params: Params, tmp_path: Path) -> None:
    original = _full_record(params)
    save_record(original, tmp_path)
    loaded = load_record(tmp_path, params_sha256=params.sha256)
    _assert_bit_identical(original.arrays, loaded.arrays)
    _assert_bit_identical(original.bushing_events, loaded.bushing_events)
    assert json.dumps(loaded.run_meta, default=dict) == json.dumps(original.run_meta, default=dict)
    assert loaded.run_meta["input_lag_steps"] == 1
    assert loaded.has_measurements


@pytest.mark.parametrize("sample_count", [0, 1])
def test_empty_and_single_sample_records_round_trip(
    params: Params, tmp_path: Path, sample_count: int
) -> None:
    recorder = Recorder(_run_meta(params))
    for index in range(sample_count):
        recorder.append(_truth(float(index)), _command(float(index)))
    original = recorder.finish()
    save_record(original, tmp_path)
    loaded = load_record(tmp_path)
    assert loaded.n_samples == sample_count
    assert not loaded.has_measurements
    required = [field for field in RECORD_FIELDS if not field.is_optional]
    assert sorted(loaded.arrays) == sorted(field.name for field in required)
    for field in required:
        assert loaded.arrays[field.name].shape == (sample_count, *field.sample_shape)
    assert all(column.shape == (0,) for column in loaded.bushing_events.values())
    _assert_bit_identical(original.arrays, loaded.arrays)


def test_field_shapes_and_dtypes(params: Params) -> None:
    finished = _full_record(params, sample_count=3)
    expected_fields = [*RECORD_FIELDS, STROKE_TRUE_FIELD, *MEASUREMENT_FIELDS]
    assert sorted(finished.arrays) == sorted(field.name for field in expected_fields)
    for field in expected_fields:
        array = finished.arrays[field.name]
        assert array.shape == (3, *field.sample_shape), field.name
        assert array.dtype == np.dtype(field.dtype), field.name
        assert not array.flags.writeable, field.name
    assert finished.arrays["pad_in_contact"].dtype == np.bool_
    np.testing.assert_array_equal(finished.arrays["meas.stroke"][0], [0.105, 0.105, 0.125, 0.125])
    np.testing.assert_array_equal(finished.arrays["stroke_true"][0], [0.095, 0.095, 0.115, 0.115])
    np.testing.assert_array_equal(finished.arrays["t"], [0.0, 0.02, 0.04])
    for name, dtype in BUSHING_EVENT_DTYPES.items():
        assert finished.bushing_events[name].dtype == np.dtype(dtype)
    np.testing.assert_array_equal(finished.bushing_events["leg"], [0, 3])
    np.testing.assert_array_equal(finished.bushing_events["kind"], [1, 2])


def test_record_meta_file_contents(params: Params, tmp_path: Path) -> None:
    save_record(_full_record(params), tmp_path)
    npz_path, meta_path = record_paths(tmp_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    assert meta["format"] == "outrigger_sim.record"
    assert meta["format_version"] == 1
    assert meta["n_samples"] == 4
    assert meta["n_bushing_events"] == 2
    assert meta["leg_order"] == list(LEG_ORDER)
    assert meta["fields"]["F_cyl"] == {
        "sample_shape": [4],
        "dtype": "float64",
        "unit": "N",
        "source": "TruthState.F_cyl_N",
    }
    assert meta["fields"]["meas.head_pressure"]["unit"] == "Pa"
    assert meta["fields"]["pad_in_contact"]["dtype"] == "bool"
    assert meta["npz_sha256"] == hashlib.sha256(npz_path.read_bytes()).hexdigest()

    run = meta["run"]
    assert run["params_sha256"] == params.sha256
    assert run["params_file_sha256"] == params.file_sha256
    assert run["auger_level"] == params.level.value
    assert run["dt_s"] == 1e-4
    assert run["input_lag_steps"] == 1
    assert run["solver"] == {"type": "SPARSE_LU", "lock_sparsity_pattern": True}
    assert run["engine"]["model"] == "L1"
    assert run["scenario"] == {
        "name": "settle",
        "settings": {"start": "on_pads", "duration_s": 10.0},
    }
    assert run["sensors"]["noise_seed"] == 1234
    assert run["sensors"]["config"]["imu_grade"] == "good"
    assert run["reference_sha256"] is None
    assert run["versions"]["numpy"] == np.__version__
    assert run["versions"]["engine"] == "0.1"


# --- run metadata ------------------------------------------------------------------------


def test_make_run_meta_rejects_a_foreign_engine_fingerprint(params: Params) -> None:
    engine_meta = _engine_meta(params) | {"params_sha256": OTHER_SHA256}
    with pytest.raises(RecordError, match="params_sha256"):
        make_run_meta(params, engine_meta, scenario="settle")


def test_make_run_meta_needs_the_time_step(params: Params) -> None:
    engine_meta = _engine_meta(params)
    del engine_meta["dt_s"]
    with pytest.raises(RecordError, match="dt_s"):
        make_run_meta(params, engine_meta, scenario="settle")


def test_make_run_meta_keeps_reference_fingerprints(params: Params) -> None:
    references = {"reference.json": "c" * 64}
    run_meta = make_run_meta(
        params, _engine_meta(params), scenario="lift", reference_sha256=references
    )
    assert run_meta["reference_sha256"] == references
    assert run_meta["sensors"] is None


def test_make_run_meta_input_lag_defaults_to_one_step(params: Params) -> None:
    assert DEFAULT_INPUT_LAG_STEPS == 1
    default_meta = make_run_meta(params, _engine_meta(params), scenario="settle")
    assert default_meta["input_lag_steps"] == 1
    immediate_meta = make_run_meta(
        params, _engine_meta(params), scenario="settle", input_lag_steps=0
    )
    assert immediate_meta["input_lag_steps"] == 0


@pytest.mark.parametrize("bad_lag", [-1, True, 1.0, "1", None])
def test_make_run_meta_rejects_a_bad_input_lag(params: Params, bad_lag: Any) -> None:
    with pytest.raises(RecordError, match="input_lag_steps"):
        make_run_meta(params, _engine_meta(params), scenario="settle", input_lag_steps=bad_lag)


def test_record_without_input_lag_still_loads(params: Params, tmp_path: Path) -> None:
    """Records saved before input_lag_steps existed keep loading (FORMAT_VERSION 1)."""
    save_record(_full_record(params, sample_count=2), tmp_path)
    meta_path = record_paths(tmp_path)[1]
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    del meta["run"]["input_lag_steps"]
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    loaded = load_record(tmp_path, params_sha256=params.sha256)
    assert "input_lag_steps" not in loaded.run_meta
    assert loaded.n_samples == 2


def test_recorder_rejects_metadata_that_is_not_json() -> None:
    with pytest.raises(RecordError, match="JSON"):
        Recorder({"bad": float("nan")})
    with pytest.raises(RecordError, match="JSON"):
        Recorder({"bad": object()})


def test_record_meta_is_read_only(params: Params) -> None:
    finished = _full_record(params, sample_count=1)
    with pytest.raises(TypeError):
        finished.run_meta["scenario"]["name"] = "other"  # type: ignore[index]


# --- recorder sample rules ---------------------------------------------------------------


def test_recorder_rejects_time_that_does_not_increase(params: Params) -> None:
    recorder = Recorder(_run_meta(params))
    recorder.append(_truth(0.1), _command(0.1))
    for repeated_t_s in (0.1, 0.05):
        with pytest.raises(RecordError, match="not after"):
            recorder.append(_truth(repeated_t_s), _command(0.0))
    assert recorder.n_samples == 1


def test_recorder_rejects_a_command_from_the_future(params: Params) -> None:
    with pytest.raises(RecordError, match="command"):
        Recorder(_run_meta(params)).append(_truth(0.1), _command(0.2))


def test_measurements_must_share_the_truth_time_axis(params: Params) -> None:
    with pytest.raises(RecordError, match="time axis"):
        Recorder(_run_meta(params)).append(_truth(0.1), _command(0.1), _measurements(0.08))


@pytest.mark.parametrize(
    "second_sample_extras",
    [
        {"measurements": None, "stroke_true_m": [0.1] * 4},
        {"measurements": _measurements(0.02), "stroke_true_m": None},
    ],
)
def test_optional_groups_must_not_change_between_samples(
    params: Params, second_sample_extras: dict[str, Any]
) -> None:
    recorder = Recorder(_run_meta(params))
    recorder.append(_truth(0.0, stroke_true_m=[0.1] * 4), _command(0.0), _measurements(0.0))
    truth = _truth(0.02, stroke_true_m=second_sample_extras["stroke_true_m"])
    with pytest.raises(RecordError, match="optional fields"):
        recorder.append(truth, _command(0.02), second_sample_extras["measurements"])


def test_unknown_energy_term_is_rejected(params: Params) -> None:
    with pytest.raises(RecordError, match="energy term"):
        Recorder(_run_meta(params)).append(_truth(0.0), _command(0.0), energy={"heat": 1.0})


@pytest.mark.parametrize(
    ("t_s", "leg", "kind", "message"),
    [
        (float("nan"), 0, BushingEventKind.CREATED, "not finite"),
        (1.0, 4, BushingEventKind.CREATED, "LEG_ORDER"),
        (1.0, -1, BushingEventKind.CREATED, "LEG_ORDER"),
        (1.0, 0, 9, "kind"),
        (0.5, 0, BushingEventKind.CREATED, "before the previous"),
    ],
)
def test_bad_bushing_events_are_rejected(
    params: Params, t_s: float, leg: int, kind: Any, message: str
) -> None:
    recorder = Recorder(_run_meta(params))
    recorder.add_bushing_event(1.0, 0, BushingEventKind.CREATED)
    with pytest.raises(RecordError, match=message):
        recorder.add_bushing_event(t_s, leg, kind)


def test_record_rejects_a_partial_measurement_group(params: Params) -> None:
    complete = _full_record(params, sample_count=2)
    arrays = dict(complete.arrays)
    del arrays["meas.stroke"]
    with pytest.raises(RecordError, match="all-or-nothing"):
        Record(arrays=arrays, bushing_events=complete.bushing_events, run_meta={})


@pytest.mark.parametrize(
    ("name", "bad_value", "message"),
    [
        ("F_cyl", np.zeros((2, 4), dtype=np.float32), "dtype"),
        ("meas.stroke", np.zeros((3, 4)), "shape"),
        ("stroke", np.zeros((2, 4)), "unknown"),
    ],
)
def test_record_rejects_bad_arrays(
    params: Params, name: str, bad_value: np.ndarray, message: str
) -> None:
    complete = _full_record(params, sample_count=2)
    arrays = dict(complete.arrays) | {name: bad_value}
    with pytest.raises(RecordError, match=message):
        Record(arrays=arrays, bushing_events=complete.bushing_events, run_meta={})


def test_record_rejects_a_missing_required_field(params: Params) -> None:
    complete = _full_record(params, sample_count=2)
    arrays = dict(complete.arrays)
    del arrays["F_cyl"]
    with pytest.raises(RecordError, match="F_cyl"):
        Record(arrays=arrays, bushing_events=complete.bushing_events, run_meta={})


@pytest.mark.parametrize(
    ("events", "message"),
    [
        ({"t": np.zeros(1), "leg": np.zeros(1, dtype=np.int64)}, "columns"),
        (
            {"t": np.zeros(2), "leg": np.zeros(1, np.int64), "kind": np.ones(1, np.int64)},
            "equal length",
        ),
        (
            {"t": np.array([np.nan]), "leg": np.zeros(1, np.int64), "kind": np.ones(1, np.int64)},
            "finite",
        ),
        ({"t": np.zeros(1), "leg": np.array([4]), "kind": np.ones(1, np.int64)}, "legs"),
        ({"t": np.zeros(1), "leg": np.zeros(1, np.int64), "kind": np.array([7])}, "kinds"),
    ],
)
def test_record_rejects_bad_event_tables(
    params: Params, events: dict[str, np.ndarray], message: str
) -> None:
    complete = _full_record(params, sample_count=1)
    with pytest.raises(RecordError, match=message):
        Record(arrays=complete.arrays, bushing_events=events, run_meta={})


def test_record_rejects_event_columns_of_the_wrong_dtype(params: Params) -> None:
    complete = _full_record(params, sample_count=1)
    events = dict(complete.bushing_events) | {"leg": np.array([0, 3], dtype=np.float64)}
    with pytest.raises(RecordError, match="leg"):
        Record(arrays=complete.arrays, bushing_events=events, run_meta={})


# --- Record files ------------------------------------------------------------------------


def test_load_record_refuses_another_parameter_set(params: Params, tmp_path: Path) -> None:
    save_record(_full_record(params), tmp_path)
    with pytest.raises(RecordError, match="params_sha256"):
        load_record(tmp_path, params_sha256=OTHER_SHA256)


def test_load_record_detects_a_mixed_file_pair(params: Params, tmp_path: Path) -> None:
    save_record(_full_record(params, sample_count=4), tmp_path / "a")
    save_record(_full_record(params, sample_count=2), tmp_path / "b")
    record_paths(tmp_path / "b")[0].replace(record_paths(tmp_path / "a")[0])
    with pytest.raises(RecordError, match="SHA-256"):
        load_record(tmp_path / "a")


def test_save_record_does_not_overwrite_by_default(params: Params, tmp_path: Path) -> None:
    save_record(_full_record(params, sample_count=1), tmp_path)
    with pytest.raises(FileExistsError):
        save_record(_full_record(params, sample_count=2), tmp_path)
    save_record(_full_record(params, sample_count=2), tmp_path, overwrite=True)
    assert load_record(tmp_path).n_samples == 2
    assert sorted(path.name for path in tmp_path.iterdir()) == ["meta.json", "record.npz"]


def test_load_record_rejects_a_snapshot_meta(tmp_path: Path) -> None:
    save_snapshot(_snapshot(), "state", directory=tmp_path)
    (tmp_path / "state.meta.json").replace(tmp_path / "meta.json")
    with pytest.raises(RecordError, match="outrigger_sim.record"):
        load_record(tmp_path)


# --- snapshot files (R16) ----------------------------------------------------------------


def test_snapshot_round_trip_is_bit_identical(tmp_path: Path) -> None:
    original = _snapshot()
    npz_path = save_snapshot(original, "L1_top_settled", directory=tmp_path, note={"settle_s": 10})
    assert npz_path == tmp_path / "L1_top_settled.npz"
    loaded = load_snapshot(
        "L1_top_settled", params_sha256=SNAPSHOT_SHA256, directory=tmp_path, engine=ENGINE
    )
    assert loaded.engine == original.engine
    assert loaded.params_sha256 == original.params_sha256
    assert loaded.time_s == original.time_s == 0.1 + 0.2
    assert loaded.held_command.t_s == original.held_command.t_s
    _assert_bit_identical(
        {"speed": original.held_command.leg_speed_m_s}, {"speed": loaded.held_command.leg_speed_m_s}
    )
    _assert_bit_identical(original.payload, loaded.payload)


def test_snapshot_with_another_fingerprint_is_refused_before_reading_arrays(
    tmp_path: Path,
) -> None:
    npz_path = save_snapshot(_snapshot(), "stale", directory=tmp_path)
    npz_path.unlink()  # the fingerprint check must not need the arrays
    with pytest.raises(SnapshotMismatchError) as caught:
        load_snapshot("stale", params_sha256=OTHER_SHA256, directory=tmp_path)
    assert caught.value.field_name == "params_sha256"
    assert caught.value.expected == OTHER_SHA256
    assert caught.value.actual == SNAPSHOT_SHA256


@pytest.mark.parametrize(
    ("engine", "field_name"),
    [
        (EngineInfo(name="mujoco", version="0.1", model="L1"), "engine name"),
        (EngineInfo(name="fake", version="0.1", model="L2b_NSC"), "engine model"),
    ],
)
def test_snapshot_from_another_engine_is_refused(
    tmp_path: Path, engine: EngineInfo, field_name: str
) -> None:
    save_snapshot(_snapshot(), "state", directory=tmp_path)
    with pytest.raises(SnapshotMismatchError) as caught:
        load_snapshot("state", params_sha256=SNAPSHOT_SHA256, directory=tmp_path, engine=engine)
    assert caught.value.field_name == field_name


def test_snapshot_engine_version_does_not_block_loading(tmp_path: Path) -> None:
    save_snapshot(_snapshot(), "state", directory=tmp_path)
    newer = EngineInfo(name="fake", version="9.9", model="L1")
    loaded = load_snapshot("state", params_sha256=SNAPSHOT_SHA256, directory=tmp_path, engine=newer)
    assert loaded.engine.version == "0.1"


def test_snapshot_meta_file_contents(tmp_path: Path) -> None:
    save_snapshot(_snapshot(), "state", directory=tmp_path, note={"scenario": "settle"})
    meta = json.loads((tmp_path / "state.meta.json").read_text(encoding="utf-8"))
    assert meta["format"] == "outrigger_sim.snapshot"
    assert meta["engine"] == {"name": "fake", "version": "0.1", "model": "L1"}
    assert meta["params_sha256"] == SNAPSHOT_SHA256
    assert meta["time_s"] == 0.1 + 0.2
    assert meta["leg_order"] == list(LEG_ORDER)
    assert meta["payload"]["lift_counter"] == {"shape": [4], "dtype": "int32"}
    assert meta["note"] == {"scenario": "settle"}


def test_snapshot_does_not_overwrite_by_default(tmp_path: Path) -> None:
    save_snapshot(_snapshot(), "state", directory=tmp_path)
    with pytest.raises(FileExistsError):
        save_snapshot(_snapshot(time_s=1.0), "state", directory=tmp_path)
    save_snapshot(_snapshot(time_s=1.0), "state", directory=tmp_path, overwrite=True)
    loaded = load_snapshot("state", params_sha256=SNAPSHOT_SHA256, directory=tmp_path)
    assert loaded.time_s == 1.0
    assert not [path for path in tmp_path.iterdir() if path.name.endswith(".tmp")]


def test_snapshot_detects_a_mixed_file_pair(tmp_path: Path) -> None:
    save_snapshot(_snapshot(), "first", directory=tmp_path)
    other_state = dataclasses.replace(_snapshot(), payload={"body_state": np.zeros(13)})
    second_npz = save_snapshot(other_state, "second", directory=tmp_path)
    second_npz.replace(tmp_path / "first.npz")
    with pytest.raises(RecordError, match="SHA-256"):
        load_snapshot("first", params_sha256=SNAPSHOT_SHA256, directory=tmp_path)


@pytest.mark.parametrize("bad_name", ["", "a/b", "a\\b", ".hidden", "state.npz", "state.json"])
def test_snapshot_names_must_be_plain_stems(bad_name: str) -> None:
    with pytest.raises(ValueError, match="plain file stem"):
        snapshot_paths(bad_name)


def test_default_snapshot_directory_is_results_states(project_root: Path) -> None:
    assert DEFAULT_STATES_DIR == project_root / "07_results" / "states"
    npz_path, meta_path = snapshot_paths("x")
    assert npz_path.parent == meta_path.parent == DEFAULT_STATES_DIR


# --- property tests ----------------------------------------------------------------------

_finite_floats = st.floats(allow_nan=False, allow_infinity=False, width=64)


@st.composite
def _record_arrays(draw: st.DrawFn) -> dict[str, np.ndarray]:
    """Random per-sample arrays for every required field (any float bits, NaN included)."""
    sample_count = draw(st.integers(min_value=0, max_value=5))
    arrays = {}
    for field in RECORD_FIELDS:
        if field.is_optional:
            continue
        shape = (sample_count, *field.sample_shape)
        if field.dtype is np.bool_:
            arrays[field.name] = draw(hnp.arrays(np.bool_, shape))
        else:
            arrays[field.name] = draw(hnp.arrays(np.float64, shape, elements=st.floats(width=64)))
    return arrays


@FILE_IO_SETTINGS
@given(arrays=_record_arrays(), event_times=st.lists(_finite_floats, max_size=4))
def test_any_record_round_trips_bit_identically(
    arrays: dict[str, np.ndarray], event_times: list[float]
) -> None:
    events = {
        "t": np.array(sorted(event_times), dtype=np.float64),
        "leg": np.arange(len(event_times), dtype=np.int64) % 4,
        "kind": np.ones(len(event_times), dtype=np.int64),
    }
    original = Record(arrays=arrays, bushing_events=events, run_meta={"note": "property"})
    with tempfile.TemporaryDirectory() as directory:
        save_record(original, directory)
        loaded = load_record(directory)
    _assert_bit_identical(original.arrays, loaded.arrays)
    _assert_bit_identical(original.bushing_events, loaded.bushing_events)


_payload_dtypes = st.sampled_from([np.float64, np.float32, np.int64, np.int8, np.uint16, np.bool_])
_payloads = st.dictionaries(
    keys=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_", min_size=1, max_size=12),
    values=_payload_dtypes.flatmap(
        lambda dtype: hnp.arrays(dtype, hnp.array_shapes(min_dims=0, max_dims=3, max_side=4))
    ),
    max_size=5,
)


@FILE_IO_SETTINGS
@given(
    payload=_payloads,
    time_s=_finite_floats,
    speeds=hnp.arrays(np.float64, 4, elements=_finite_floats),
)
def test_any_snapshot_round_trips_bit_identically(
    payload: dict[str, np.ndarray], time_s: float, speeds: np.ndarray
) -> None:
    original = Snapshot(
        engine=ENGINE,
        params_sha256=SNAPSHOT_SHA256,
        time_s=time_s,
        held_command=Command(t_s=time_s, leg_speed_m_s=speeds),
        payload=payload,
    )
    with tempfile.TemporaryDirectory() as directory:
        save_snapshot(original, "state", directory=directory)
        loaded = load_snapshot("state", params_sha256=SNAPSHOT_SHA256, directory=directory)
    assert loaded.time_s == original.time_s
    _assert_bit_identical(original.payload, loaded.payload)
    _assert_bit_identical(
        {"speed": original.held_command.leg_speed_m_s}, {"speed": loaded.held_command.leg_speed_m_s}
    )


# --- truth field and module boundary -----------------------------------------------------


def test_truth_stroke_true_is_optional_frozen_and_checked() -> None:
    assert _truth(0.0).stroke_true_m is None
    truth = _truth(0.0, stroke_true_m=[0.1, 0.2, 0.3, 0.4])
    assert truth.stroke_true_m is not None
    assert truth.stroke_true_m.dtype == np.float64
    assert not truth.stroke_true_m.flags.writeable
    with pytest.raises(InvalidSignalError, match="stroke_true_m"):
        _truth(0.0, stroke_true_m=[0.1, 0.2, 0.3])
    with pytest.raises(InvalidSignalError, match="stroke_true_m"):
        _truth(0.0, stroke_true_m=[0.1, 0.2, 0.3, np.nan])


def test_module_has_no_engine_dependency() -> None:
    source = Path(record_module.__file__).read_text(encoding="utf-8")
    for forbidden in ("import pychrono", "from pychrono"):
        assert forbidden not in source
