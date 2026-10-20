"""Time-history Record and snapshot files: npz arrays + JSON metadata (engine independent).

``00_docs/03_chrono/chrono_build_plan.md`` 3.1-3.2 (``record``), R16 and S0. This module
never imports a physics engine; it sees only :mod:`outrigger_sim.signals` and
:class:`outrigger_sim.engine.Snapshot`.

Record (one run, one directory)::

    <run_dir>/record.npz   per-sample arrays + the bushing event table
    <run_dir>/meta.json    file format, field schema, npz SHA-256 and the run metadata

Snapshot (one settled state, R16)::

    <directory>/<name>.npz         payload arrays + held command speeds
    <directory>/<name>.meta.json   engine, Params.sha256, time, npz SHA-256

The default snapshot directory is ``07_results/states/`` (plan 2, initial-condition rule 3).

Record contents (all SI, per-leg arrays in LEG_ORDER FL, FR, RL, RR):

* the fixed Record arrays of :data:`outrigger_sim.signals.RECORD_FIELDS`;
* ``stroke_true`` - actual stroke from ``TruthState.stroke_true_m``, kept apart from
  ``s_motor`` (user decision 2026-10-20 (1)); present when the engine provides it;
* ``meas.*`` - the sensor outputs (:class:`Measurements`) on the same time axis as the
  truth (user decision 2026-10-20 (2)); the sensor settings and noise seed go to the meta;
* ``bushing_events.t`` / ``.leg`` / ``.kind`` - the event table of plan 3.2.

Optional groups (``stroke_true``, ``meas.*``, ``energy.*``) are all-or-nothing per Record:
the first sample decides which are present and every later sample must match.

Both file pairs are written through temporary files and renamed into place, and the meta
stores the SHA-256 of the npz bytes, so a torn or mixed pair is detected on load. Arrays
load bit for bit as saved (``allow_pickle=False``).
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import platform
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.engine import (
    EngineInfo,
    Snapshot,
    SnapshotMismatchError,
    ensure_snapshot_compatible,
)
from outrigger_sim.params import LEG_ORDER, Params
from outrigger_sim.signals import (
    BUSHING_EVENT_FIELDS,
    BUSHING_EVENTS_NAME,
    ENERGY_FIELD_PREFIX,
    ENERGY_TERMS,
    LEG_COUNT,
    RECORD_FIELDS,
    RECORD_FIELDS_BY_NAME,
    BushingEventKind,
    Command,
    InvalidSignalError,
    Measurements,
    RecordField,
    TruthState,
    record_row,
    validate_record_arrays,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATES_DIR = PROJECT_ROOT / "07_results" / "states"

RECORD_NPZ_NAME = "record.npz"
RECORD_META_NAME = "meta.json"
SNAPSHOT_META_SUFFIX = ".meta.json"

RECORD_FORMAT = "outrigger_sim.record"
SNAPSHOT_FORMAT = "outrigger_sim.snapshot"
FORMAT_VERSION = 1

MEASUREMENT_FIELD_PREFIX = "meas."
BUSHING_EVENTS_KEY_PREFIX = f"{BUSHING_EVENTS_NAME}."
PAYLOAD_KEY_PREFIX = "payload."
HELD_COMMAND_KEY = "held_command.leg_speed_m_s"

# Inputs set by a post-step Python hook act from the next step on (pychrono 10); kept as
# the model convention, ``00_docs/01_dynamics/dynamics_model.md`` 4.6 (plan R15).
DEFAULT_INPUT_LAG_STEPS = 1

STROKE_TRUE_FIELD = RecordField(
    "stroke_true", (LEG_COUNT,), "m", "TruthState.stroke_true_m", is_optional=True
)
MEASUREMENT_FIELDS: tuple[RecordField, ...] = tuple(
    RecordField(name, shape, unit, source, is_optional=True)
    for name, shape, unit, source in (
        ("meas.specific_force", (3,), "m/s^2", "Measurements.specific_force_m_s2"),
        ("meas.angular_rate", (3,), "rad/s", "Measurements.angular_rate_rad_s"),
        ("meas.head_pressure", (LEG_COUNT,), "Pa", "Measurements.head_pressure_Pa"),
        ("meas.stroke", (LEG_COUNT,), "m", "Measurements.stroke_m"),
    )
)
SUPPLEMENTARY_FIELDS: tuple[RecordField, ...] = (STROKE_TRUE_FIELD, *MEASUREMENT_FIELDS)
"""Record arrays added by this module on top of :data:`signals.RECORD_FIELDS`."""

ALL_FIELDS_BY_NAME: Mapping[str, RecordField] = MappingProxyType(
    {**RECORD_FIELDS_BY_NAME, **{field.name: field for field in SUPPLEMENTARY_FIELDS}}
)

# Columns of the bushing event table; leg and kind are integers, unlike the float default
# of RecordField.dtype.
BUSHING_EVENT_DTYPES: Mapping[str, type[np.generic]] = MappingProxyType(
    {"t": np.float64, "leg": np.int64, "kind": np.int64}
)


class RecordError(ValueError):
    """A Record or snapshot file pair, sample or metadata is inconsistent or malformed."""


# --- value types -------------------------------------------------------------------------


@dataclass(frozen=True)
class SensorSetup:
    """Sensor-model settings of a run, stored in the run meta to reproduce ``meas.*``.

    Attributes:
        config: JSON-serialisable sensor settings (IMU grade, mounting point, filter, ...).
        noise_seed: Seed of the sensor noise generator, ``None`` for noise-free sensors.
    """

    config: Mapping[str, Any]
    noise_seed: int | None


@dataclass(frozen=True, eq=False)
class Record:
    """A finished time history: per-sample arrays, bushing events and run metadata.

    Built by :meth:`Recorder.finish` or :func:`load_record`. Arrays are copied into
    read-only arrays on construction; the metadata becomes read-only mappings and tuples.

    Attributes:
        arrays: Record name -> array of shape ``(n_samples, *sample_shape)``; the names of
            :data:`signals.RECORD_FIELDS` plus any of :data:`SUPPLEMENTARY_FIELDS`.
        bushing_events: Column -> 1-D array: ``t`` (s, float64), ``leg`` (LEG_ORDER index,
            int64), ``kind`` (:class:`BushingEventKind`, int64).
        run_meta: JSON-compatible run metadata, normally from :func:`make_run_meta`.
    """

    arrays: Mapping[str, NDArray[Any]]
    bushing_events: Mapping[str, NDArray[Any]]
    run_meta: Mapping[str, Any]

    def __post_init__(self) -> None:
        arrays = _read_only_arrays(self.arrays)
        _validate_sample_arrays(arrays)
        events = _read_only_arrays(self.bushing_events)
        _validate_bushing_events(events)
        object.__setattr__(self, "arrays", arrays)
        object.__setattr__(self, "bushing_events", events)
        object.__setattr__(self, "run_meta", _frozen_json(self.run_meta))

    @property
    def n_samples(self) -> int:
        """Number of samples (rows of every per-sample array)."""
        return int(self.arrays["t"].shape[0])

    @property
    def has_measurements(self) -> bool:
        """Whether the sensor outputs (``meas.*``) were recorded."""
        return MEASUREMENT_FIELDS[0].name in self.arrays


# --- JSON helpers ------------------------------------------------------------------------


def _json_default(value: Any) -> Any:
    # Frozen metadata holds MappingProxyType, which json does not know.
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError(f"{type(value).__name__} is not JSON-serialisable")


def _json_text(document: Mapping[str, Any]) -> str:
    try:
        return json.dumps(
            document, indent=2, ensure_ascii=False, allow_nan=False, default=_json_default
        )
    except (TypeError, ValueError) as error:
        raise RecordError(f"metadata is not JSON-serialisable: {error}") from None


def _deep_freeze(node: Any) -> Any:
    if isinstance(node, dict):
        return MappingProxyType({key: _deep_freeze(value) for key, value in node.items()})
    if isinstance(node, list):
        return tuple(_deep_freeze(item) for item in node)
    return node


def _frozen_json(document: Mapping[str, Any]) -> Mapping[str, Any]:
    """Read-only copy of ``document`` exactly as it reads back from JSON."""
    return _deep_freeze(json.loads(_json_text(document)))


def _utc_now_text() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# --- array validation --------------------------------------------------------------------


def _read_only_arrays(arrays: Mapping[str, Any]) -> Mapping[str, NDArray[Any]]:
    frozen: dict[str, NDArray[Any]] = {}
    for name, value in arrays.items():
        array = np.array(value, copy=True)
        array.setflags(write=False)
        frozen[name] = array
    return MappingProxyType(frozen)


def _check_exact_dtype(name: str, array: NDArray[Any], expected: type[np.generic]) -> None:
    if array.dtype != np.dtype(expected):
        raise RecordError(f"{name}: expected dtype {np.dtype(expected)}, got {array.dtype}")


def _check_optional_groups(names: set[str]) -> None:
    """Measurements are recorded as a whole group or not at all."""
    measurement_names = {field.name for field in MEASUREMENT_FIELDS}
    present = names & measurement_names
    if present and present != measurement_names:
        missing = sorted(measurement_names - present)
        raise RecordError(f"measurement fields are all-or-nothing; missing {missing}")


def _validate_sample_arrays(arrays: Mapping[str, NDArray[Any]]) -> int:
    """Check names, shapes, exact dtypes and a common sample count; return the count."""
    unknown = sorted(set(arrays) - set(ALL_FIELDS_BY_NAME))
    if unknown:
        raise RecordError(f"unknown Record fields {unknown}")
    core = {name: array for name, array in arrays.items() if name in RECORD_FIELDS_BY_NAME}
    try:
        sample_count = validate_record_arrays(core)
    except InvalidSignalError as error:
        raise RecordError(str(error)) from None
    for name, array in arrays.items():
        field = ALL_FIELDS_BY_NAME[name]
        expected_shape = (sample_count, *field.sample_shape)
        if array.shape != expected_shape:
            raise RecordError(f"{name}: expected shape {expected_shape}, got {array.shape}")
        _check_exact_dtype(name, array, field.dtype)
    _check_optional_groups(set(arrays))
    return sample_count


def _validate_bushing_events(events: Mapping[str, NDArray[Any]]) -> None:
    expected_columns = [column.name for column in BUSHING_EVENT_FIELDS]
    if sorted(events) != sorted(expected_columns):
        raise RecordError(f"bushing events need columns {expected_columns}, got {list(events)}")
    lengths = {events[name].shape for name in expected_columns}
    if len(lengths) != 1 or len(next(iter(lengths))) != 1:
        raise RecordError(f"bushing event columns must be 1-D of equal length, got {lengths}")
    for name, dtype in BUSHING_EVENT_DTYPES.items():
        _check_exact_dtype(f"{BUSHING_EVENTS_KEY_PREFIX}{name}", events[name], dtype)
    if not np.all(np.isfinite(events["t"])):
        raise RecordError("bushing event times must be finite")
    if np.any((events["leg"] < 0) | (events["leg"] >= LEG_COUNT)):
        raise RecordError(f"bushing event legs must be 0-{LEG_COUNT - 1}")
    valid_kinds = [kind.value for kind in BushingEventKind]
    if not np.all(np.isin(events["kind"], valid_kinds)):
        raise RecordError(f"bushing event kinds must be one of {valid_kinds}")


# --- recorder ----------------------------------------------------------------------------


def _check_sample_times(
    truth: TruthState,
    command: Command,
    measurements: Measurements | None,
    previous_t_s: float | None,
) -> None:
    if previous_t_s is not None and truth.t_s <= previous_t_s:
        raise RecordError(
            f"sample time {truth.t_s!r} s is not after the previous sample {previous_t_s!r} s"
        )
    if command.t_s > truth.t_s:
        raise RecordError(
            f"command issued at {command.t_s!r} s, after the sample time {truth.t_s!r} s"
        )
    if measurements is not None and measurements.t_s != truth.t_s:
        raise RecordError(
            f"measurements at {measurements.t_s!r} s must share the truth time axis "
            f"({truth.t_s!r} s)"
        )


def _energy_columns(energy: Mapping[str, float]) -> dict[str, NDArray[np.float64]]:
    columns: dict[str, NDArray[np.float64]] = {}
    for term, value in energy.items():
        if term not in ENERGY_TERMS:
            raise RecordError(f"unknown energy term {term!r}, expected one of {ENERGY_TERMS}")
        if not math.isfinite(value):
            raise RecordError(f"energy term {term!r} is not finite: {value!r}")
        columns[f"{ENERGY_FIELD_PREFIX}{term}"] = np.asarray(value, dtype=np.float64)
    return columns


def _optional_columns(
    truth: TruthState,
    measurements: Measurements | None,
    energy: Mapping[str, float] | None,
) -> dict[str, NDArray[Any]]:
    columns: dict[str, NDArray[Any]] = {}
    if truth.stroke_true_m is not None:
        columns[STROKE_TRUE_FIELD.name] = truth.stroke_true_m
    if measurements is not None:
        for field in MEASUREMENT_FIELDS:
            attribute = field.source.split(".")[1]
            columns[field.name] = getattr(measurements, attribute)
    if energy is not None:
        columns.update(_energy_columns(energy))
    return columns


def _empty_core_arrays() -> dict[str, NDArray[Any]]:
    return {
        field.name: np.empty((0, *field.sample_shape), dtype=field.dtype)
        for field in RECORD_FIELDS
        if not field.is_optional
    }


class Recorder:
    """Collects Record samples in memory during a run; :meth:`finish` returns the Record.

    The runner calls :meth:`append` at every record instant with the truth state, the held
    command and (from the sensor stage on) the measurements of the same instant, and
    :meth:`add_bushing_event` from the ground bushing hook.
    """

    def __init__(self, run_meta: Mapping[str, Any]) -> None:
        """Start an empty Record.

        Args:
            run_meta: JSON-serialisable run metadata, normally from :func:`make_run_meta`.

        Raises:
            RecordError: ``run_meta`` is not JSON-serialisable (checked now, not at save).
        """
        self._run_meta = _frozen_json(run_meta)
        self._rows: list[dict[str, NDArray[Any]]] = []
        self._events: list[tuple[float, int, int]] = []
        self._optional_names: frozenset[str] | None = None

    @property
    def n_samples(self) -> int:
        """Number of samples appended so far."""
        return len(self._rows)

    def append(
        self,
        truth: TruthState,
        command: Command,
        measurements: Measurements | None = None,
        energy: Mapping[str, float] | None = None,
    ) -> None:
        """Add one sample.

        Args:
            truth: True state at the sample time.
            command: Command held at the sample time (issued at or before it).
            measurements: Sensor outputs at the same time as ``truth``, or ``None`` when
                the run has no sensor model. Must be given for all samples or none.
            energy: Energy terms (J) by :data:`signals.ENERGY_TERMS` name, same set every
                sample, or ``None``.

        Raises:
            RecordError: Time not increasing, command after the sample, measurements at
                another time, or a different set of optional fields than the first sample.
        """
        previous_t_s = float(self._rows[-1]["t"]) if self._rows else None
        _check_sample_times(truth, command, measurements, previous_t_s)
        optional = _optional_columns(truth, measurements, energy)
        optional_names = frozenset(optional)
        if self._optional_names is None:
            self._optional_names = optional_names
        elif optional_names != self._optional_names:
            raise RecordError(
                f"sample at {truth.t_s!r} s has optional fields {sorted(optional_names)}, "
                f"earlier samples {sorted(self._optional_names)}"
            )
        self._rows.append(record_row(truth, command) | optional)

    def add_bushing_event(self, t_s: float, leg: int, kind: BushingEventKind) -> None:
        """Add a ground bushing event (plan R15); times must not decrease.

        Raises:
            RecordError: Non-finite or decreasing time, leg outside 0-3, unknown kind.
        """
        if not math.isfinite(t_s):
            raise RecordError(f"bushing event time is not finite: {t_s!r}")
        if self._events and t_s < self._events[-1][0]:
            raise RecordError(f"bushing event at {t_s!r} s is before the previous event")
        if not 0 <= leg < LEG_COUNT:
            raise RecordError(f"bushing event leg {leg!r} is not a LEG_ORDER index")
        try:
            kind_value = int(BushingEventKind(kind))
        except ValueError:
            raise RecordError(f"unknown bushing event kind {kind!r}") from None
        self._events.append((float(t_s), int(leg), kind_value))

    def finish(self) -> Record:
        """Stack the samples into a :class:`Record` (zero samples give empty arrays)."""
        if self._rows:
            names = list(self._rows[0])
            arrays = {name: np.stack([row[name] for row in self._rows]) for name in names}
        else:
            arrays = _empty_core_arrays()
        columns = list(zip(*self._events, strict=True)) or [(), (), ()]
        events = {
            name: np.array(values, dtype=BUSHING_EVENT_DTYPES[name])
            for name, values in zip(BUSHING_EVENT_DTYPES, columns, strict=True)
        }
        return Record(arrays=arrays, bushing_events=events, run_meta=self._run_meta)


# --- run metadata ------------------------------------------------------------------------


def _check_input_lag_steps(input_lag_steps: int) -> None:
    # bool is an int subclass; True would silently be stored as true, not 1.
    is_int = isinstance(input_lag_steps, int) and not isinstance(input_lag_steps, bool)
    if not is_int or input_lag_steps < 0:
        raise RecordError(f"input_lag_steps must be a non-negative int, got {input_lag_steps!r}")


def make_run_meta(
    params: Params,
    engine_meta: Mapping[str, Any],
    *,
    scenario: str,
    scenario_settings: Mapping[str, Any] | None = None,
    sensors: SensorSetup | None = None,
    reference_sha256: Mapping[str, str] | None = None,
    input_lag_steps: int = DEFAULT_INPUT_LAG_STEPS,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run metadata for a Record's ``meta.json`` (plan S3 meta, R16).

    Records written before ``input_lag_steps`` existed have no such key; the format
    version is unchanged because the key is only added.

    Args:
        params: Parameters the engine was built from.
        engine_meta: ``SimEngine.meta()``; must hold ``dt_s`` and, if it holds
            ``params_sha256``, the same fingerprint as ``params``.
        scenario: Scenario name, for example ``"settle"``.
        scenario_settings: Scenario arguments (JSON-serialisable).
        sensors: Sensor settings and noise seed, ``None`` for a run without sensors.
        reference_sha256: Reference file name -> SHA-256 (``References.sha256_by_file()``),
            ``None`` until the run is checked against reference values.
        input_lag_steps: Steps between a hook setting an input (bushing anchor, damping,
            external force, motor function) and the input acting; 1 for pychrono 10
            (``00_docs/01_dynamics/dynamics_model.md`` 4.6).
        extra: Free-form JSON-serialisable notes.

    Returns:
        A new JSON-serialisable dict; ``solver`` is ``None`` if the engine meta has none.

    Raises:
        RecordError: ``dt_s`` missing, the engine fingerprint differs from ``params``, or
            ``input_lag_steps`` is not a non-negative int.
    """
    _check_input_lag_steps(input_lag_steps)
    if "dt_s" not in engine_meta:
        raise RecordError("engine meta has no 'dt_s'")
    engine_sha256 = engine_meta.get("params_sha256", params.sha256)
    if engine_sha256 != params.sha256:
        raise RecordError(
            f"engine params_sha256 {engine_sha256!r} differs from Params.sha256 {params.sha256!r}"
        )
    sensor_meta = None
    if sensors is not None:
        sensor_meta = {"config": dict(sensors.config), "noise_seed": sensors.noise_seed}
    return {
        "params_sha256": params.sha256,
        "params_file_sha256": params.file_sha256,
        "params_source_path": str(params.source_path),
        "auger_level": params.level.value,
        "params_overrides": dict(params.overrides),
        "dt_s": engine_meta["dt_s"],
        "input_lag_steps": input_lag_steps,
        "solver": engine_meta.get("solver"),
        "engine": dict(engine_meta),
        "scenario": {"name": scenario, "settings": dict(scenario_settings or {})},
        "sensors": sensor_meta,
        "reference_sha256": None if reference_sha256 is None else dict(reference_sha256),
        "versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "engine": engine_meta.get("engine_version"),
        },
        "extra": dict(extra or {}),
    }


# --- file pair I/O -----------------------------------------------------------------------


def _npz_bytes(arrays: Mapping[str, NDArray[Any]]) -> bytes:
    buffer = io.BytesIO()
    np.savez(buffer, **arrays)
    return buffer.getvalue()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _refuse_existing(paths: tuple[Path, ...], overwrite: bool) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(f"refusing to overwrite {existing} (pass overwrite=True)")


def _write_files_atomically(contents: Mapping[Path, bytes]) -> None:
    """Write every file to a temporary sibling first, then rename them in order."""
    temporary_paths: dict[Path, Path] = {}
    try:
        for path, data in contents.items():
            temporary_path = path.with_name(f".{path.name}.tmp")
            temporary_path.write_bytes(data)
            temporary_paths[path] = temporary_path
        for path, temporary_path in temporary_paths.items():
            temporary_path.replace(path)
    finally:
        for temporary_path in temporary_paths.values():
            temporary_path.unlink(missing_ok=True)


def _read_meta_file(path: Path, expected_format: str) -> dict[str, Any]:
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RecordError(f"{path}: not valid JSON ({error})") from None
    if not isinstance(meta, dict) or meta.get("format") != expected_format:
        raise RecordError(f"{path}: not an {expected_format!r} meta file")
    if meta.get("format_version") != FORMAT_VERSION:
        raise RecordError(
            f"{path}: format_version {meta.get('format_version')!r}, "
            f"this code reads {FORMAT_VERSION}"
        )
    return meta


def _read_npz_file(path: Path, expected_sha256: str) -> dict[str, NDArray[Any]]:
    data = path.read_bytes()
    actual_sha256 = _sha256(data)
    if actual_sha256 != expected_sha256:
        raise RecordError(
            f"{path}: SHA-256 {actual_sha256} differs from its meta ({expected_sha256}); "
            "the npz and meta files were not written together"
        )
    with np.load(io.BytesIO(data), allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


# --- Record files ------------------------------------------------------------------------


def record_paths(run_dir: str | Path) -> tuple[Path, Path]:
    """Return ``(record.npz, meta.json)`` inside ``run_dir``."""
    directory = Path(run_dir)
    return directory / RECORD_NPZ_NAME, directory / RECORD_META_NAME


def _field_schema(arrays: Mapping[str, NDArray[Any]]) -> dict[str, dict[str, Any]]:
    schema: dict[str, dict[str, Any]] = {}
    for name in arrays:
        field = ALL_FIELDS_BY_NAME[name]
        schema[name] = {
            "sample_shape": list(field.sample_shape),
            "dtype": str(np.dtype(field.dtype)),
            "unit": field.unit,
            "source": field.source,
        }
    return schema


def save_record(record: Record, run_dir: str | Path, *, overwrite: bool = False) -> Path:
    """Write ``record`` as ``record.npz`` + ``meta.json`` in ``run_dir`` (created if needed).

    Returns:
        ``run_dir`` as a :class:`Path`.

    Raises:
        FileExistsError: A file of the pair exists and ``overwrite`` is false.
    """
    npz_path, meta_path = record_paths(run_dir)
    npz_path.parent.mkdir(parents=True, exist_ok=True)
    _refuse_existing((npz_path, meta_path), overwrite)

    event_arrays = {
        f"{BUSHING_EVENTS_KEY_PREFIX}{name}": column
        for name, column in record.bushing_events.items()
    }
    npz_data = _npz_bytes({**record.arrays, **event_arrays})
    meta = {
        "format": RECORD_FORMAT,
        "format_version": FORMAT_VERSION,
        "saved_utc": _utc_now_text(),
        "n_samples": record.n_samples,
        "n_bushing_events": int(record.bushing_events["t"].shape[0]),
        "leg_order": list(LEG_ORDER),
        "fields": _field_schema(record.arrays),
        "npz_sha256": _sha256(npz_data),
        "run": record.run_meta,
    }
    meta_data = _json_text(meta).encode("utf-8")
    _write_files_atomically({npz_path: npz_data, meta_path: meta_data})
    return npz_path.parent


def load_record(run_dir: str | Path, *, params_sha256: str | None = None) -> Record:
    """Read a Record written by :func:`save_record`.

    Args:
        run_dir: Directory holding ``record.npz`` and ``meta.json``.
        params_sha256: If given, the Record must come from parameters with this
            ``Params.sha256``.

    Raises:
        FileNotFoundError: A file of the pair is missing.
        RecordError: Wrong format or version, npz/meta mismatch, inconsistent arrays, or a
            different ``params_sha256``.
    """
    npz_path, meta_path = record_paths(run_dir)
    meta = _read_meta_file(meta_path, RECORD_FORMAT)
    run_meta = meta["run"]
    if params_sha256 is not None and run_meta.get("params_sha256") != params_sha256:
        raise RecordError(
            f"{meta_path}: params_sha256 {run_meta.get('params_sha256')!r} "
            f"is not the expected {params_sha256!r}"
        )
    stored = _read_npz_file(npz_path, meta["npz_sha256"])
    events = {
        name.removeprefix(BUSHING_EVENTS_KEY_PREFIX): array
        for name, array in stored.items()
        if name.startswith(BUSHING_EVENTS_KEY_PREFIX)
    }
    arrays = {
        name: array
        for name, array in stored.items()
        if not name.startswith(BUSHING_EVENTS_KEY_PREFIX)
    }
    if sorted(arrays) != sorted(meta["fields"]):
        raise RecordError(f"{npz_path}: arrays {sorted(arrays)} differ from the meta field list")
    record = Record(arrays=arrays, bushing_events=events, run_meta=run_meta)
    if record.n_samples != meta["n_samples"]:
        raise RecordError(f"{npz_path}: {record.n_samples} samples, meta says {meta['n_samples']}")
    return record


# --- snapshot files (R16) ----------------------------------------------------------------


def snapshot_paths(name: str, directory: str | Path = DEFAULT_STATES_DIR) -> tuple[Path, Path]:
    """Return ``(<name>.npz, <name>.meta.json)`` in ``directory``.

    Raises:
        ValueError: ``name`` is empty, contains a path separator, starts with a dot or
            already ends in ``.npz`` / ``.json``.
    """
    is_plain_name = bool(name) and Path(name).name == name and "/" not in name
    if not is_plain_name or name.startswith(".") or name.endswith((".npz", ".json")):
        raise ValueError(f"snapshot name must be a plain file stem, got {name!r}")
    folder = Path(directory)
    return folder / f"{name}.npz", folder / f"{name}{SNAPSHOT_META_SUFFIX}"


def save_snapshot(
    snapshot: Snapshot,
    name: str,
    *,
    directory: str | Path = DEFAULT_STATES_DIR,
    overwrite: bool = False,
    note: Mapping[str, Any] | None = None,
) -> Path:
    """Write ``snapshot`` as ``<name>.npz`` + ``<name>.meta.json`` (R16).

    Args:
        snapshot: State from ``SimEngine.snapshot()``.
        name: File stem, for example ``"L1_top_on_pads_settled"``.
        directory: Target directory, created if needed; default ``07_results/states/``.
        overwrite: Replace an existing pair.
        note: Free-form JSON-serialisable notes (scenario, settle time, ...).

    Returns:
        Path of the npz file.

    Raises:
        FileExistsError: A file of the pair exists and ``overwrite`` is false.
    """
    npz_path, meta_path = snapshot_paths(name, directory)
    npz_path.parent.mkdir(parents=True, exist_ok=True)
    _refuse_existing((npz_path, meta_path), overwrite)

    npz_arrays = {f"{PAYLOAD_KEY_PREFIX}{key}": array for key, array in snapshot.payload.items()}
    npz_arrays[HELD_COMMAND_KEY] = snapshot.held_command.leg_speed_m_s
    npz_data = _npz_bytes(npz_arrays)
    payload_schema = {
        key: {"shape": list(array.shape), "dtype": str(array.dtype)}
        for key, array in snapshot.payload.items()
    }
    meta = {
        "format": SNAPSHOT_FORMAT,
        "format_version": FORMAT_VERSION,
        "saved_utc": _utc_now_text(),
        "engine": {
            "name": snapshot.engine.name,
            "version": snapshot.engine.version,
            "model": snapshot.engine.model,
        },
        "params_sha256": snapshot.params_sha256,
        # JSON writes Python's shortest round-trip float repr, so the times load bit-exact.
        "time_s": snapshot.time_s,
        "held_command_t_s": snapshot.held_command.t_s,
        "leg_order": list(LEG_ORDER),
        "payload": payload_schema,
        "npz_sha256": _sha256(npz_data),
        "note": dict(note or {}),
    }
    meta_data = _json_text(meta).encode("utf-8")
    _write_files_atomically({npz_path: npz_data, meta_path: meta_data})
    return npz_path


def load_snapshot(
    name: str,
    *,
    params_sha256: str,
    directory: str | Path = DEFAULT_STATES_DIR,
    engine: EngineInfo | None = None,
) -> Snapshot:
    """Read a snapshot written by :func:`save_snapshot`, refusing a stale one (R16).

    The fingerprint is checked from the meta file before the arrays are read.

    Args:
        name: File stem used when saving.
        params_sha256: ``Params.sha256`` of the engine that will restore the state.
        directory: Directory of the pair; default ``07_results/states/``.
        engine: If given, the engine name and model must match as well
            (:func:`engine.ensure_snapshot_compatible`).

    Raises:
        FileNotFoundError: A file of the pair is missing.
        SnapshotMismatchError: Different ``params_sha256`` (or engine name / model).
        RecordError: Wrong format or version, npz/meta mismatch, or missing arrays.
    """
    npz_path, meta_path = snapshot_paths(name, directory)
    meta = _read_meta_file(meta_path, SNAPSHOT_FORMAT)
    if meta["params_sha256"] != params_sha256:
        raise SnapshotMismatchError("params_sha256", params_sha256, meta["params_sha256"])

    stored = _read_npz_file(npz_path, meta["npz_sha256"])
    payload = {
        key.removeprefix(PAYLOAD_KEY_PREFIX): array
        for key, array in stored.items()
        if key.startswith(PAYLOAD_KEY_PREFIX)
    }
    if HELD_COMMAND_KEY not in stored or sorted(payload) != sorted(meta["payload"]):
        raise RecordError(f"{npz_path}: arrays do not match the meta payload list")
    held_command = Command(t_s=meta["held_command_t_s"], leg_speed_m_s=stored[HELD_COMMAND_KEY])
    snapshot = Snapshot(
        engine=EngineInfo(**meta["engine"]),
        params_sha256=meta["params_sha256"],
        time_s=meta["time_s"],
        held_command=held_command,
        payload=payload,
    )
    if engine is not None:
        ensure_snapshot_compatible(snapshot, engine=engine, params_sha256=params_sha256)
    return snapshot
