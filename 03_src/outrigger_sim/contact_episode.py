"""S8 contact-judge episode record: one run (or one ML episode) on the 10 Hz control grid.

``00_docs/04_control/s6_control_spec.md`` rev. 39: 203 (item 9, offline J_P / J_C replay) and
205 (ground-contact ML data). This module is the **only** place that knows

* the episode npz schema (:data:`FIELDS`) read by :mod:`outrigger_sim.control.contact_replay`,
  :mod:`outrigger_sim.verify.contact_metrics` and :mod:`outrigger_sim.ml`, and
* the Chrono case-folder files and keys it is built from (:func:`build_episode`): the runner
  record ``record/record.npz``, ``r8_series.npz``, the S8 ``s8_series.npz`` (when present),
  ``pads.npz`` (1 ms truth), ``result.json``, ``controller_events.json`` and
  ``probe_history.json``.

When the S8 runner (``04_scripts/02_chrono/run_S8C.py``) changes a file or key, only this module
changes. The episode npz needs numpy alone, so the ML environment (Python 3.13) reads what the
Chrono environment (Python 3.12) wrote.

Time convention: row ``k`` is control period ``k`` closing at ``t_s[k]``. Measurements are those
the controller read at ``t_s[k]``. Controller state fields (``phase``, ``seal_band_N``,
``is_lifted``, ``touched``, ``probed_leg``) are the state **after** the update of period ``k``
(what ``R8Series`` records); a replay of update ``k`` uses row ``k - 1`` of them.

Truth: ``true_force_min_N[k]`` = minimum over the window ``(t[k-1], t[k]]`` of the rod axial force
(L2b: oil + seal friction; L1: cylinder force), from the 1 ms pad record (spec 203.1).

Fields the bundle-C (S6) and S7 folders do not carry are reconstructed and named in
``meta["reconstructed"]``: the seal band (probe round ends), the lifted latch (stroke clearance),
the probed leg (probe history). The S8 folders give the band and the lower reading directly.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

LEG_NAMES = ("FL", "FR", "RL", "RR")
LEG_COUNT = len(LEG_NAMES)
NO_LEG = -1
"""``probed_leg`` value when no leg is probed."""

FORMAT_NAME = "outrigger_sim.contact_episode"
FORMAT_VERSION = 1

# --- Chrono case folder: file names and keys (runner / run_S6C / run_S7C / run_S8C) ---------

RECORD_FILE = Path("record") / "record.npz"
R8_SERIES_FILE = "r8_series.npz"
S8_SERIES_FILE = "s8_series.npz"
PADS_FILE = "pads.npz"
RESULT_FILE = "result.json"
EVENTS_FILE = "controller_events.json"
PROBE_HISTORY_FILE = "probe_history.json"

_EVENT_PATTERN = re.compile(r"C2Event\(t_s=([-+0-9.eE]+), name='([^']*)'")
ZERO_CALIBRATED_EVENT = "INFO_PRESSURE_ZERO_CALIBRATED"
LIFT_SHADOW_EVENT = "shadow_G1L"
SUPPORT_CHANGED_EVENT = "WARN_SUPPORT_CHANGED"
PRE_LIFT_PHASES = frozenset({"idle", "check", "touch"})
PROBE_PHASE = "probe"


@dataclass(frozen=True)
class FieldSpec:
    """One episode array: shape after the sample axis, dtype kind, whether it must exist."""

    name: str
    tail_shape: tuple[int | None, ...]
    """Shape after the sample axis; ``None`` = any length."""
    kind: str
    """numpy dtype kind: ``f`` float, ``b`` bool, ``i`` int, ``U`` str."""
    required: bool
    description: str


FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("t_s", (), "f", True, "period end time [s]"),
    FieldSpec("phase", (), "U", True, "C2 phase after the update (r8_series.phase)"),
    FieldSpec("head_pressure_Pa", (LEG_COUNT,), "f", True, "delivered head pressure"),
    FieldSpec("rod_pressure_Pa", (LEG_COUNT,), "f", False, "delivered rod-side pressure"),
    FieldSpec("net_force_N", (LEG_COUNT,), "f", True,
              "delivered p_h A_p - p_r A_ann (no zero offset removed)"),
    FieldSpec("lower_reading_N", (LEG_COUNT,), "f", True,
              "controller forces.lower: net force minus zero offset and E-6 allowance"),
    FieldSpec("seal_band_N", (LEG_COUNT,), "f", True, "per-leg F_band after the update"),
    FieldSpec("motor_stroke_m", (LEG_COUNT,), "f", True, "measured stroke (motor / s_ref)"),
    FieldSpec("stroke_corrected_m", (LEG_COUNT,), "f", True, "built-in stroke sensor"),
    FieldSpec("command_m_s", (LEG_COUNT,), "f", True, "issued leg command of the period"),
    FieldSpec("specific_force_m_s2", (3,), "f", True, "IMU period mean specific force"),
    FieldSpec("angular_rate_rad_s", (3,), "f", True, "IMU period mean angular rate"),
    FieldSpec("imu_specific_force_samples_m_s2", (None, 3), "f", False,
              "IMU-rate (100 Hz) specific force samples of the period, oldest first"),
    FieldSpec("is_lifted", (), "b", True, "lifted latch after the update"),
    FieldSpec("touched", (LEG_COUNT,), "b", True, "touch latch after the update"),
    FieldSpec("probed_leg", (), "i", True, "leg probed after the update, -1 = none"),
    FieldSpec("ge2_lift_mark", (LEG_COUNT,), "b", True, "shadow_G1L:<leg> raised this period"),
    FieldSpec("ge2_trigger_mark", (LEG_COUNT,), "b", True,
              "WARN_SUPPORT_CHANGED this period (G2: every leg)"),
    FieldSpec("probe_round_end", (), "b", True, "a probe round finished this period"),
    FieldSpec("probe_is_grounded", (LEG_COUNT,), "f", True,
              "last probe verdict per leg: 1 grounded, 0 not, NaN none yet"),
    FieldSpec("probe_load_estimate_N", (LEG_COUNT,), "f", True, "last probe midpoint load"),
    FieldSpec("probe_stiffness_ratio", (LEG_COUNT,), "f", True,
              "last probe incremental stiffness / nominal S_ii"),
    FieldSpec("probe_attitude_ratio", (LEG_COUNT,), "f", True, "last probe attitude ratio"),
    FieldSpec("probe_age_s", (LEG_COUNT,), "f", True, "time since that probe ended"),
    FieldSpec("true_force_N", (LEG_COUNT,), "f", True, "rod axial force at t_s (truth)"),
    FieldSpec("true_force_min_N", (LEG_COUNT,), "f", True,
              "window minimum of the rod axial force (truth, spec 203.1)"),
    FieldSpec("true_force_mean_N", (LEG_COUNT,), "f", True, "window mean (truth)"),
)
FIELD_BY_NAME = {spec.name: spec for spec in FIELDS}

META_KEYS = (
    "source", "case_id", "base_id", "episode_id", "engine", "period_s", "F_min_N",
    "rod_weight_N", "zero_offset_N", "seal_friction_N", "initial_seal_state_N", "beta_Pa",
    "floor", "floor_roll_deg", "floor_pitch_deg", "level", "sensor_grade", "zero_calibration",
    "sensor_condition", "rod_dead_length_m", "event", "seed", "controller", "reconstructed",
    "crawler_contact", "crawler_check_passed",
)
"""Meta keys; values may be ``None`` when unknown. ``seal_friction_N`` = per-leg Coulomb limit
F_s (spec 205.3, hydraulics U-S8-H1: rear = 0.833 x front), ``initial_seal_state_N`` = f at the
branch, ``controller`` = the replay settings source (``result.json`` controller meta).

Sensor condition (spec rev. 44 214.5 question 3-5, P-S8-9): ``sensor_grade`` is the pressure
sensor grade alone (ideal / normal / conservative / old_worst), ``zero_calibration`` whether the
CHECK zero calibration ran (bool), ``sensor_condition`` the combined display string
(``"normal"``, ``"normal_no_cal"``). Group or filter on the first two, never on the string.

Crawler model (spec rev. 45 215.8, P-S8-10): ``crawler_contact`` is the crawler contact model of
the run (``"nsc_rigid"``, ``"nsc_compliant"``, ``"l1r_flexible"``; str) and
``crawler_check_passed`` whether its S8-L4 check passed (bool), both from ``result.json
settings.s8``. Records before S8 carry neither and stay ``None``; the ML exclusion rule
(``ml.dataset.has_liftoff_transient``, R40-6) reads an absent model as rigid."""

UNRECORDED_CRAWLER = "unrecorded"
""":func:`count_by_crawler_contact` key of episodes without ``crawler_contact``."""

NO_CALIBRATION_SUFFIX = "_no_cal"
"""Suffix of the combined ``sensor_condition`` (and of the legacy ``sensor_grade``) when the
zero calibration was off."""


RUNNER_META_KEY = "ml_meta"
"""``result.json settings.ml_meta``: the runner's values of :data:`META_KEYS` (base id of the
branch, per-leg F_s, L_0r, f at the branch, floor angles ...); they override the defaults."""


class EpisodeError(ValueError):
    """An episode npz or a case folder does not match the schema."""


@dataclass(frozen=True)
class Episode:
    """Validated episode arrays (``arrays[name]``, sample axis first) and meta."""

    arrays: Mapping[str, NDArray[Any]]
    meta: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_arrays(self.arrays)

    @property
    def sample_count(self) -> int:
        return int(self.arrays["t_s"].shape[0])

    def __getitem__(self, name: str) -> NDArray[Any]:
        return self.arrays[name]

    def has(self, name: str) -> bool:
        return name in self.arrays

    @property
    def rod_weight_N(self) -> NDArray[np.float64]:
        return np.asarray(self.meta["rod_weight_N"], dtype=float)

    @property
    def F_min_N(self) -> float:
        return float(self.meta["F_min_N"])


def validate_arrays(arrays: Mapping[str, NDArray[Any]]) -> None:
    """Check presence, shape and dtype kind of every schema field.

    Raises:
        EpisodeError: A required field is missing or a field has the wrong shape or dtype.
    """
    if "t_s" not in arrays:
        raise EpisodeError("missing required field 't_s'")
    count = np.shape(arrays["t_s"])[0]
    for spec in FIELDS:
        if spec.name not in arrays:
            if spec.required:
                raise EpisodeError(f"missing required field {spec.name!r}")
            continue
        value = np.asarray(arrays[spec.name])
        expected = (count, *spec.tail_shape)
        is_shape_ok = value.ndim == len(expected) and all(
            want is None or got == want for got, want in zip(value.shape, expected, strict=True)
        )
        if not is_shape_ok:
            raise EpisodeError(f"{spec.name}: shape {value.shape}, expected {expected}")
        kind_ok = value.dtype.kind == spec.kind or (spec.kind == "f" and value.dtype.kind == "i")
        if not kind_ok:
            raise EpisodeError(f"{spec.name}: dtype {value.dtype}, expected kind {spec.kind!r}")


def _controller_calibration_flag(meta: Mapping[str, Any]) -> bool | None:
    """``is_active`` of the controller's zero calibration meta (``None`` when not recorded)."""
    controller = meta.get("controller") or {}
    calibration = controller.get("zero_calibration") if isinstance(controller, Mapping) else None
    if not isinstance(calibration, Mapping) or calibration.get("is_active") is None:
        return None
    return bool(calibration["is_active"])


def normalize_sensor_meta(meta: Mapping[str, Any]) -> dict[str, Any]:
    """Copy of ``meta`` with ``sensor_grade``, ``zero_calibration`` and ``sensor_condition``.

    Legacy meta (S8 runner before P-S8-9) carries one combined ``sensor_grade`` such as
    ``"normal_no_cal"``; the suffix is split off into ``zero_calibration=False``. Without a
    suffix or an explicit flag, ``zero_calibration`` falls back to the controller meta
    (``controller.zero_calibration.is_active``) and stays ``None`` when that is missing too.

    Raises:
        EpisodeError: The grade says ``_no_cal`` but ``zero_calibration`` is True.
    """
    normalized = dict(meta)
    grade = normalized.get("sensor_grade")
    is_calibrated = normalized.get("zero_calibration")
    if isinstance(grade, str) and grade.endswith(NO_CALIBRATION_SUFFIX):
        if is_calibrated is True:
            raise EpisodeError(
                f"sensor_grade {grade!r} says no zero calibration but zero_calibration is True"
            )
        grade = grade.removesuffix(NO_CALIBRATION_SUFFIX)
        is_calibrated = False
    if is_calibrated is None:
        is_calibrated = _controller_calibration_flag(normalized)
    normalized["sensor_grade"] = grade
    normalized["zero_calibration"] = None if is_calibrated is None else bool(is_calibrated)
    if normalized.get("sensor_condition") is None and grade is not None:
        suffix = NO_CALIBRATION_SUFFIX if is_calibrated is False else ""
        normalized["sensor_condition"] = f"{grade}{suffix}"
    return normalized


def count_by_crawler_contact(metas: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    """Episode count per ``crawler_contact`` (dataset summary, spec rev. 45 215.8).

    Episodes without the key (records before S8) count under :data:`UNRECORDED_CRAWLER`.
    Keys are sorted so the summary reads the same on every run.
    """
    counts = Counter(str(meta.get("crawler_contact") or UNRECORDED_CRAWLER) for meta in metas)
    return dict(sorted(counts.items()))


def save_episode(episode: Episode, path: Path) -> Path:
    """Write ``episode`` as a compressed npz (meta as a JSON string, no pickle)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = {"format": FORMAT_NAME, "format_version": FORMAT_VERSION, **episode.meta}
    np.savez_compressed(
        path, **{k: np.asarray(v) for k, v in episode.arrays.items()},
        meta_json=np.array(json.dumps(header, default=_json_default)),
    )
    return path


def load_episode(path: Path) -> Episode:
    """Read an episode npz written by :func:`save_episode` (``allow_pickle=False``).

    The sensor meta is normalized (:func:`normalize_sensor_meta`), so files written before
    P-S8-9 with a combined ``sensor_grade`` read as the two fields.

    Raises:
        EpisodeError: Wrong format name or version, or a schema mismatch.
    """
    with np.load(path, allow_pickle=False) as data:
        meta = json.loads(str(data["meta_json"]))
        arrays = {name: data[name] for name in data.files if name != "meta_json"}
    if meta.get("format") != FORMAT_NAME or meta.get("format_version") != FORMAT_VERSION:
        raise EpisodeError(
            f"{path}: format {meta.get('format')!r} v{meta.get('format_version')!r}, "
            f"expected {FORMAT_NAME!r} v{FORMAT_VERSION}"
        )
    return Episode(arrays, normalize_sensor_meta(meta))


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"not JSON serialisable: {type(value).__name__}")


# --- building an episode from a Chrono case folder ------------------------------------------


@dataclass(frozen=True)
class MachineConstants:
    """Machine values the reconstruction needs (from ``C2Geometry``; tests pass their own).

    Attributes:
        head_area_m2: Head area per leg.
        annulus_area_m2: Rod-side area per leg.
        F_min_N: Minimum cylinder force.
        rod_weight_N: Moving part weight ``m_i g`` per leg.
        clearance_m: Callable rod strokes (4,) -> crawler clearance estimate [m]
            (``C2Geometry.clearance_estimate_m``).
    """

    head_area_m2: NDArray[np.float64]
    annulus_area_m2: NDArray[np.float64]
    F_min_N: float
    rod_weight_N: NDArray[np.float64]
    clearance_m: Any

    @classmethod
    def from_geometry(cls, geometry: Any) -> MachineConstants:
        """From a ``outrigger_sim.control.c2.C2Geometry``."""
        return cls(
            np.asarray(geometry.head_area_m2, dtype=float),
            np.asarray(geometry.annulus_area_m2, dtype=float),
            float(geometry.F_min_N),
            np.asarray(geometry.rod_weight_N, dtype=float),
            geometry.clearance_estimate_m,
        )


def read_controller_events(path: Path) -> list[tuple[float, str]]:
    """``controller_events.json`` (a list of ``C2Event(...)`` reprs) -> (t_s, name)."""
    events = []
    for text in json.loads(Path(path).read_text(encoding="utf-8")):
        match = _EVENT_PATTERN.match(text)
        if match is None:
            raise EpisodeError(f"{path}: unreadable event {text!r}")
        events.append((float(match.group(1)), match.group(2)))
    return events


def _row_at(t_s: NDArray[np.float64], time_s: float, period_s: float) -> int:
    """Row whose period closes at ``time_s`` (events carry the period end time)."""
    row = int(np.argmin(np.abs(t_s - time_s)))
    if abs(t_s[row] - time_s) > 0.25 * period_s:
        raise EpisodeError(f"event time {time_s:.4f} s is not on the control grid")
    return row


def _leg_index(name: str) -> int | None:
    _, _, leg = name.partition(":")
    return LEG_NAMES.index(leg) if leg in LEG_NAMES else None


def _event_marks(
    events: list[tuple[float, str]], t_s: NDArray[np.float64], period_s: float
) -> dict[str, NDArray[np.bool_]]:
    count = t_s.size
    lift = np.zeros((count, LEG_COUNT), dtype=bool)
    trigger = np.zeros((count, LEG_COUNT), dtype=bool)
    for time_s, name in events:
        prefix = name.split(":", 1)[0]
        if prefix not in (LIFT_SHADOW_EVENT, SUPPORT_CHANGED_EVENT):
            continue
        if not t_s[0] - 0.25 * period_s <= time_s <= t_s[-1] + 0.25 * period_s:
            continue
        row = _row_at(t_s, time_s, period_s)
        leg = _leg_index(name.split(":", 1)[1] if prefix == SUPPORT_CHANGED_EVENT else name)
        if prefix == LIFT_SHADOW_EVENT and leg is not None:
            lift[row, leg] = True
        elif prefix == SUPPORT_CHANGED_EVENT:
            if leg is None:
                trigger[row, :] = True  # G2 names no leg
            else:
                trigger[row, leg] = True
    return {"ge2_lift_mark": lift, "ge2_trigger_mark": trigger}


def _zero_calibration(result: Mapping[str, Any]) -> tuple[NDArray, NDArray]:
    """(offsets_N, allowance_N) of the CHECK zero calibration; zeros when absent."""
    meta = (result.get("controller_meta") or {}).get("zero_calibration")
    if meta is None:
        report = result.get("zero_calibration_report") or {}
        meta = (report.get("controller_meta") or {}).get("zero_calibration") or {}
    offsets = np.asarray(meta.get("offsets_N") or np.zeros(LEG_COUNT), dtype=float)
    allowance = meta.get("pressure_offset_allowance_N") or np.zeros(LEG_COUNT)
    return offsets, np.asarray(allowance, dtype=float)


def _calibration_rows(events, t_s, period_s) -> NDArray[np.int64]:
    """Per leg, the first row whose reading has the offset removed (row after the event)."""
    first = np.full(LEG_COUNT, t_s.size, dtype=np.int64)
    for time_s, name in events:
        if name.startswith(ZERO_CALIBRATED_EVENT) and t_s[0] <= time_s <= t_s[-1]:
            leg = _leg_index(name)
            if leg is not None:
                first[leg] = min(first[leg], _row_at(t_s, time_s, period_s) + 1)
    return first


def _lower_reading(
    net_force_N: NDArray, offsets: NDArray, allowance: NDArray, first_rows: NDArray
) -> NDArray[np.float64]:
    """Controller ``forces.lower`` without a rod-side fallback (spec 76.2)."""
    lower = np.array(net_force_N, dtype=float)
    for leg in range(LEG_COUNT):
        rows = slice(int(first_rows[leg]), None)
        lower[rows, leg] -= offsets[leg] + allowance[leg]
    return lower


def _lifted_latch(
    phase: NDArray, stroke_corrected_m: NDArray, clearance_m: Any, threshold_m: float
) -> NDArray[np.bool_]:
    """``is_lifted`` after each update: LEVEL latches it once the clearance exceeds the limit."""
    lifted = np.zeros(phase.size, dtype=bool)
    is_lifted = False
    for row, name in enumerate(phase):
        if not is_lifted and str(name) not in PRE_LIFT_PHASES:
            is_lifted = clearance_m(stroke_corrected_m[row]) > threshold_m
        lifted[row] = is_lifted
    return lifted


def _touched_latch(phase: NDArray) -> NDArray[np.bool_]:
    """All legs touched once TOUCH has ended (TOUCH -> LEVEL needs all four)."""
    has_left_touch = np.zeros(phase.size, dtype=bool)
    seen_touch = False
    left = False
    for row, name in enumerate(phase):
        name = str(name)
        seen_touch |= name == "touch"
        left |= seen_touch and name not in PRE_LIFT_PHASES
        has_left_touch[row] = left
    return np.repeat(has_left_touch[:, None], LEG_COUNT, axis=1)


@dataclass(frozen=True)
class _ProbeRoundRecord:
    end_row: int
    results: list[Mapping[str, Any]]


def _probe_rounds(
    history: list[list[Mapping[str, Any]]], phase: NDArray, t_s: NDArray, period_s: float
) -> list[_ProbeRoundRecord]:
    """Match each recorded round to the period it finished in.

    A round finishes in the update where PROBE ends without a re-level (the next phase is not
    LEVEL), or where a re-ground step starts (still PROBE). The end row is the first PROBE row
    at or after the last leg's second hold end that leaves PROBE (or the last such row).
    """
    rounds = []
    for results in history:
        hold_ends = [r.get("t_second_hold_end_s") for r in results]
        latest_end = max((t for t in hold_ends if t is not None), default=None)
        if latest_end is None:
            continue
        start = int(np.searchsorted(t_s, latest_end - 0.25 * period_s))
        if start >= phase.size:
            continue
        end_row = start  # re-ground follows: the round ended while PROBE goes on
        for row in range(max(start, 1), phase.size):
            if str(phase[row - 1]) == PROBE_PHASE and str(phase[row]) != PROBE_PHASE:
                if str(phase[row]) != "level":  # LEVEL = a later round was interrupted
                    end_row = row
                break
        rounds.append(_ProbeRoundRecord(end_row, list(results)))
    return rounds


def _seal_band_timeline(
    rounds: list[_ProbeRoundRecord],
    count: int,
    initial_band_N: float,
    margin_N: float,
    min_band_N: float,
    is_measured_first: bool,
) -> NDArray[np.float64]:
    """D5 ``_update_seal_band`` replayed on the round end rows (band after each update)."""
    band = np.full(count, float(initial_band_N))
    current = float(initial_band_N)
    measured = False
    for record in rounds:
        largest = max(float(r["seal_friction_estimate_N"]) for r in record.results)
        candidate = largest + margin_N
        current = max(min_band_N, candidate) if is_measured_first and not measured else max(
            current, candidate
        )
        measured = True
        band[record.end_row:] = current
    return np.repeat(band[:, None], LEG_COUNT, axis=1)


def _probe_context(
    rounds: list[_ProbeRoundRecord], t_s: NDArray, nominal_stiffness_N_m: NDArray | None
) -> dict[str, NDArray]:
    count = t_s.size
    out = {
        name: np.full((count, LEG_COUNT), np.nan)
        for name in ("probe_is_grounded", "probe_load_estimate_N", "probe_stiffness_ratio",
                     "probe_attitude_ratio", "probe_age_s")
    }
    round_end = np.zeros(count, dtype=bool)
    ended_at = np.full(LEG_COUNT, np.nan)
    for record in rounds:
        rows = slice(record.end_row, None)
        round_end[record.end_row] = True
        for result in record.results:
            leg = int(result["leg_index"])
            out["probe_is_grounded"][rows, leg] = 1.0 if result.get("is_grounded") else 0.0
            out["probe_load_estimate_N"][rows, leg] = float(result["load_estimate_N"])
            stiffness = float(result.get("incremental_stiffness_N_m") or np.nan)
            if nominal_stiffness_N_m is not None:
                stiffness /= float(nominal_stiffness_N_m[leg])
            out["probe_stiffness_ratio"][rows, leg] = stiffness
            ratio = result.get("attitude_response_ratio")
            out["probe_attitude_ratio"][rows, leg] = np.nan if ratio is None else float(ratio)
            ended_at[leg] = t_s[record.end_row]
            out["probe_age_s"][rows, leg] = t_s[rows] - ended_at[leg]
    out["probe_round_end"] = round_end
    return out


def _probed_leg(rounds_history, phase: NDArray, t_s: NDArray) -> NDArray[np.int64]:
    """Leg the probe moves after each PROBE update (reconstructed from the probe history).

    Inside a PROBE stay the current leg is the first leg (LEG order) whose second hold has not
    ended; before the history has an entry for the stay, LEG 0. Re-ground steps are not
    recorded and count as the round's last leg.
    """
    probed = np.full(t_s.size, NO_LEG, dtype=np.int64)
    leg_end_times: list[tuple[float, int]] = []
    for results in rounds_history:
        for result in results:
            end = result.get("t_second_hold_end_s")
            if end is not None:
                leg_end_times.append((float(end), int(result["leg_index"])))
    leg_end_times.sort()
    for row in np.flatnonzero(phase == PROBE_PHASE):
        pending = [leg for end, leg in leg_end_times if end >= t_s[row] - 1e-9]
        probed[row] = pending[0] if pending else 0
    return probed


def _window_truth(
    pads_t_s: NDArray, force_N: NDArray, force_min_N: NDArray, t_s: NDArray
) -> dict[str, NDArray]:
    """Per period: rod force at ``t_k``, its minimum and mean over ``(t_{k-1}, t_k]``."""
    count = t_s.size
    at = np.full((count, LEG_COUNT), np.nan)
    low = np.full((count, LEG_COUNT), np.nan)
    mean = np.full((count, LEG_COUNT), np.nan)
    half_sample = 0.5 * float(np.median(np.diff(pads_t_s))) if pads_t_s.size > 1 else 0.0
    for row in range(count):
        t_end = t_s[row]
        t_start = t_s[row - 1] if row > 0 else t_end - (t_s[1] - t_s[0])
        first = int(np.searchsorted(pads_t_s, t_start + half_sample, side="left"))
        last = int(np.searchsorted(pads_t_s, t_end + half_sample, side="left"))
        if last <= first:
            continue
        at[row] = force_N[last - 1]
        low[row] = force_min_N[first:last].min(axis=0)
        mean[row] = force_N[first:last].mean(axis=0)
    return {"true_force_N": at, "true_force_min_N": low, "true_force_mean_N": mean}


def _crawler_meta(settings: Mapping[str, Any]) -> dict[str, Any]:
    """``crawler_contact`` / ``crawler_check_passed`` of ``settings.s8`` (``None`` when absent)."""
    s8 = settings.get("s8")
    if not isinstance(s8, Mapping):
        s8 = {}
    contact = s8.get("crawler_contact")
    is_check_passed = s8.get("crawler_check_passed")
    return {
        "crawler_contact": None if contact is None else str(contact),
        "crawler_check_passed": None if is_check_passed is None else bool(is_check_passed),
    }


def build_episode(
    case_dir: Path,
    machine: MachineConstants,
    *,
    meta: Mapping[str, Any] | None = None,
    nominal_stiffness_N_m: NDArray | None = None,
) -> Episode:
    """Episode of one Chrono case folder (bundle C, S7 ctrl3 or S8; see the module docstring).

    Args:
        case_dir: Case folder with the runner record, ``r8_series.npz`` and ``pads.npz``.
        machine: Areas, F_min, rod weights and the clearance estimate.
        meta: Extra meta (split unit ``base_id``, F_s per leg, ...), merged over the defaults.
        nominal_stiffness_N_m: ``S_ii`` per leg for ``probe_stiffness_ratio`` (``None`` = the
            raw incremental stiffness).

    Raises:
        EpisodeError: Missing files, or an event off the control grid.
    """
    case_dir = Path(case_dir)
    for name in (RECORD_FILE, R8_SERIES_FILE, PADS_FILE, RESULT_FILE, EVENTS_FILE):
        if not (case_dir / name).is_file():
            raise EpisodeError(f"{case_dir}: missing {name}")
    result = json.loads((case_dir / RESULT_FILE).read_text(encoding="utf-8"))
    events = read_controller_events(case_dir / EVENTS_FILE)
    controller = result.get("controller_meta") or {}
    period_s = float(controller.get("period_s", 0.1))
    reconstructed: list[str] = []

    with np.load(case_dir / RECORD_FILE, allow_pickle=False) as record:
        t_s = np.asarray(record["t"], dtype=float)
        head = np.asarray(record["meas.head_pressure"], dtype=float)
        rod = np.asarray(record["meas.rod_pressure"], dtype=float)
        arrays: dict[str, NDArray] = {
            "t_s": t_s,
            "head_pressure_Pa": head,
            "rod_pressure_Pa": rod,
            "motor_stroke_m": np.asarray(record["meas.stroke"], dtype=float),
            "stroke_corrected_m": np.asarray(record["meas.stroke_corrected"], dtype=float),
            "specific_force_m_s2": np.asarray(record["meas.specific_force"], dtype=float),
            "angular_rate_rad_s": np.asarray(record["meas.angular_rate"], dtype=float),
        }
    with np.load(case_dir / R8_SERIES_FILE, allow_pickle=False) as series:
        if not np.allclose(series["t"], t_s, atol=1e-9):
            raise EpisodeError(f"{case_dir}: r8_series and record times differ")
        arrays["phase"] = np.asarray(series["phase"]).astype("U16")
        arrays["command_m_s"] = np.asarray(series["issued_u"], dtype=float)
        if "imu_samples" in series.files:
            arrays["imu_specific_force_samples_m_s2"] = np.asarray(
                series["imu_samples"], dtype=float
            )
    arrays["net_force_N"] = head * machine.head_area_m2 - np.nan_to_num(rod) * (
        machine.annulus_area_m2
    )
    phase = arrays["phase"]
    history = []
    if (case_dir / PROBE_HISTORY_FILE).is_file():
        history = json.loads((case_dir / PROBE_HISTORY_FILE).read_text(encoding="utf-8"))
    rounds = _probe_rounds(history, phase, t_s, period_s)

    s8_path = case_dir / S8_SERIES_FILE
    if s8_path.is_file():
        with np.load(s8_path, allow_pickle=False) as s8:
            arrays["lower_reading_N"] = np.asarray(s8["F_lower_N"], dtype=float)
            arrays["seal_band_N"] = np.asarray(s8["leg_band_N"], dtype=float)
    else:
        offsets, allowance = _zero_calibration(result)
        first_rows = _calibration_rows(events, t_s, period_s)
        arrays["lower_reading_N"] = _lower_reading(
            arrays["net_force_N"], offsets, allowance, first_rows
        )
        probe = controller.get("probe") or {}
        arrays["seal_band_N"] = _seal_band_timeline(
            rounds,
            t_s.size,
            float(controller.get("initial_seal_band_N", 13000.0)),
            float(probe.get("seal_band_margin_N", 1000.0)),
            float(probe.get("seal_band_min_N", 1000.0)),
            probe.get("seal_band_rule", "measured_first") == "measured_first",
        )
        reconstructed += ["lower_reading_N", "seal_band_N"]

    thresholds = controller.get("thresholds") or {}
    arrays["is_lifted"] = _lifted_latch(
        phase, arrays["stroke_corrected_m"], machine.clearance_m,
        float(thresholds.get("lifted_clearance_m", 0.01)),
    )
    arrays["touched"] = _touched_latch(phase)
    arrays["probed_leg"] = _probed_leg(history, phase, t_s)
    reconstructed += ["is_lifted", "touched", "probed_leg"]
    arrays.update(_event_marks(events, t_s, period_s))
    arrays.update(_probe_context(rounds, t_s, nominal_stiffness_N_m))

    with np.load(case_dir / PADS_FILE, allow_pickle=False) as pads:
        arrays.update(
            _window_truth(
                np.asarray(pads["t"], dtype=float),
                np.asarray(pads["F_cyl"], dtype=float),
                np.asarray(pads["F_cyl_min_interval"], dtype=float),
                t_s,
            )
        )
    offsets, _ = _zero_calibration(result)
    settings = result.get("settings") or {}
    defaults: dict[str, Any] = {
        "source": str(case_dir),
        "case_id": settings.get("case_id", case_dir.name),
        "base_id": settings.get("case_id", case_dir.name),
        "episode_id": case_dir.name,
        "engine": (result.get("runner") or {}).get("engine"),
        "period_s": period_s,
        "F_min_N": machine.F_min_N,
        "rod_weight_N": machine.rod_weight_N.tolist(),
        "zero_offset_N": offsets.tolist(),
        "floor": settings.get("floor"),
        "level": settings.get("level"),
        "sensor_grade": settings.get("pressure_grade"),
        "zero_calibration": settings.get("zero_calibration"),
        "event": settings.get("event"),
        "seed": settings.get("seed"),
        "controller": controller,
        "reconstructed": reconstructed,
        **_crawler_meta(settings),
    }
    runner_meta = {k: v for k, v in (settings.get(RUNNER_META_KEY) or {}).items()
                   if k in META_KEYS}
    return Episode(arrays, normalize_sensor_meta({**defaults, **runner_meta, **(meta or {})}))
