"""Episode -> causal windows, labels and weights for the ground-contact models (spec 205.1-205.2).

One example = one leg ``i`` at one 10 Hz sample ``k``: the window of the last
:data:`WINDOW_SAMPLES` samples (H = 3 s, ASSUMPTION 205.2) up to and including ``k``. Leg channels
are stacked in the order (self, diagonal, same side, same axle) so one model serves every leg.
Inputs are only what the machine knows (pressures, strokes, commands, IMU, controller context);
the truth, the seal-friction state and the engine tags are never inputs (205.2).

Scaling is by fixed physical units (kN, mm, mm/s, deg), not fitted, so the ONNX model needs no
separate scaler. numpy only.

Exclusions (205.1): rows before the crawler lift-off are not examples. In a rigid-crawler run
(spec rev. 40 R40-4, dynamics 5.26.7 D-S8-4) the rows up to :data:`LIFTOFF_EXCLUSION_S` after
the lift-off are examples with weight 0: their label carries the rigid-pivot release transient.
Rows inside the run's ML mask of ``verify_S8ML.json`` (``ml_masks``, C-S8-27 ④ / spec rev. 48
218.13: FAULT entry .. run end; the forced-retract window is no longer masked, U-S8-34) are no
examples either (:func:`load_ml_masks`, :func:`masked_rows`).

Tags (spec rev. 51 223.2 / 226, P-S8-18, :func:`load_episode_tags`): ``fault_tail`` is the ML
mask above. ``plant_rod_collapse`` (locked lift-off whose rod pressure collapsed, a suspected
plant artefact) gives the rows within :data:`ROD_COLLAPSE_HALF_WINDOW_S` of that lift-off weight
0 on every leg (the cue reaches the other legs' windows as neighbour channels; ASSUMPTION);
three lift-offs keep weight 0 until re-grounding + 0.1 s (hydraulics H-S8-4 12.6,
:data:`ROD_COLLAPSE_END_OVERRIDES_S`). ``reapproach_pingpong`` changes no weight;
:func:`pingpong_rows` marks its window for the separate evaluation rows.
``plant_release_rod_step`` (H-S8-4 12.6: rod-reading step > 20 bar when a locked leg is
released, ``releases_big``) marks ``[t_b, t_b + 0.3 s]`` of that leg. It weighs only individual
head / rod pressure features (:data:`INDIVIDUAL_PRESSURE_CHANNELS`); the net force, stroke, IMU
and labels stay. :data:`LEG_CHANNELS` carries no individual pressure, so it changes no weight
here (:func:`release_step_rows` still marks it for the evaluation rows).

Window history: a branched episode starts at its READY snapshot, so its first
``WINDOW_SAMPLES - 1`` rows have no full window of their own. When the base run it branched from
is in the same episode list and ends one period before the branch, the base's last rows fill the
window (:func:`build_examples`). The history is identical up to the snapshot, so the windows stay
causal; examples still come from the episode's own rows only.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from numpy.typing import NDArray

from outrigger_sim.contact_episode import LEG_COUNT, LEG_NAMES, Episode
from outrigger_sim.verify.contact_metrics import ContactClass, boundary_mask, truth_classes

WINDOW_SAMPLES = 30
"""H = 3 s at 10 Hz (ASSUMPTION, spec 205.2 / 207)."""
BOUNDARY_WEIGHT = 0.5
"""Training weight of a boundary sample (ASSUMPTION, spec 205.1)."""
LIFTOFF_EXCLUSION_S = 8.0
"""Rigid-crawler lift-off transient window, weight 0 (spec rev. 40 R40-4, dynamics 5.26.7)."""
RIGID_CRAWLER = "nsc_rigid"
"""``meta["crawler_contact"]`` of a rigid NSC crawler; an absent value means rigid (R40-6)."""
CLASS_COUNT = 3

FORCE_SCALE_N = 1e4
"""10 kN per unit (F_min is 9.41 kN)."""
STROKE_SCALE_M = 1e-3
SPEED_SCALE_M_S = 1e-3
ACCELERATION_SCALE_M_S2 = 9.81
RATE_SCALE_RAD_S = np.radians(1.0)

PHASES = ("level", "done", "probe", "ready", "reanchor")
"""Phase one-hot columns; any other phase is all zeros."""

LEG_CHANNELS = (
    "lower_reading",
    "estimate_minus_band",
    "seal_band",
    "stroke_corrected",
    "oil_compression",
    "command",
)
GLOBAL_CHANNELS = (
    *(f"specific_force_{axis}" for axis in "xyz"),
    *(f"angular_rate_{axis}" for axis in "xyz"),
    *(f"imu_sample_std_{axis}" for axis in "xyz"),
    *(f"phase_{name}" for name in PHASES),
)
PROBE_CONTEXT = ("probe_is_grounded", "probe_load_estimate", "probe_stiffness_ratio",
                 "probe_attitude_ratio", "probe_age", "has_probe")


ML_MASK_TIME_TOLERANCE_S = 1e-6
"""Mask bounds are inclusive; the tolerance absorbs the float sum ``relative + t0``."""

ROD_COLLAPSE_HALF_WINDOW_S = 0.3
"""``plant_rod_collapse`` window: lift-off +- 0.3 s, 3 samples at 10 Hz (ASSUMPTION, 226)."""
ROD_COLLAPSE_DROP_BAR = 50.0
"""Rod-pressure drop within 10 ms of a locked lift-off that marks a collapse (C-S8-34 ④)."""
PINGPONG_LATE_START_S = 1.5
"""Re-approach starts later than event + 1.5 s count for the ping-pong tag (226)."""
PINGPONG_MIN_LATE_STARTS = 3
PINGPONG_END_ALLOWANCE_S = 1.0
"""Ping-pong window: event + 1.5 s .. end of the last re-approach + 1 s (223.2)."""
ROD_COLLAPSE_END_OVERRIDES_S = {
    ("ML28_ep6", "RL"): 67.39,
    ("ML81_ep5", "RR"): 69.91,
    ("ML88_ep0", "RR"): 63.66,
}
"""Collapse windows that end at re-grounding + 0.1 s instead of lift-off + 0.3 s (engine time;
hydraulics ``s8_seal_friction_counterbalance.md`` 12.6: the trajectory up to re-grounding is
an artefact too)."""
RELEASE_STEP_WINDOW_S = 0.3
"""``plant_release_rod_step`` window ``[t_b, t_b + 0.3 s]`` (H-S8-4 12.6)."""
LIFTOFF_ROD_FILE = "s8_ml_rev51_liftoff_rod.json"
REAPPROACH_SCAN_FILE = "s8_ml_rev51_reapp_scan.json"
RELEASE_SCAN_PATH = Path("06_analysis/03_hydraulic/s8/h_s8_4_release_scan.json")
"""Hydraulics release scan (``releases_big``), relative to the project root."""
TAG_ROD_COLLAPSE = "plant_rod_collapse"
TAG_PINGPONG = "reapproach_pingpong"
TAG_RELEASE_STEP = "plant_release_rod_step"
INDIVIDUAL_PRESSURE_CHANNELS: tuple[str, ...] = ()
"""Channels of :data:`LEG_CHANNELS` built from one pressure sensor alone (``p_h`` or ``p_r``);
``plant_release_rod_step`` sets their examples' weight to 0. Empty: every leg channel uses the
net force ``p_h A_p - p_r A_ann`` or no pressure at all."""
HISTORY_GAP_TOLERANCE = 0.25
"""Base end must be one period before the branch, within this fraction of a period."""

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MlMask:
    """ML exclusion interval of one run (``verify_S8ML.json`` ``ml_masks`` entry).

    Attributes:
        start_engine_s: Start in engine time (the episode ``t_s`` time base).
        end_engine_s: End in engine time (the run end).
        reasons: Why the run is masked (``fault``; ``forced_hold_all_legs`` for old runs).
    """

    start_engine_s: float
    end_engine_s: float
    reasons: tuple[str, ...] = ()


def load_ml_masks(verify_path: Path) -> dict[str, MlMask]:
    """``ml_masks`` of a ``verify_S8ML.json`` by run name (episode folder name).

    Raises:
        KeyError: An entry without ``start_engine_s`` / ``end_engine_s``.
    """
    data = json.loads(Path(verify_path).read_text(encoding="utf-8"))
    masks = {}
    for run, entry in (data.get("ml_masks") or {}).items():
        masks[run] = MlMask(float(entry["start_engine_s"]), float(entry["end_engine_s"]),
                            tuple(entry.get("reasons") or ()))
    return masks


def masked_rows(episode: Episode, masks: Mapping[str, MlMask] | None) -> NDArray[np.bool_]:
    """Rows of ``episode`` inside its run's mask (matched by ``meta["episode_id"]``)."""
    t_s = np.asarray(episode["t_s"], dtype=float)
    mask = (masks or {}).get(str(episode.meta.get("episode_id")))
    if mask is None:
        return np.zeros(t_s.size, dtype=bool)
    return ((t_s >= mask.start_engine_s - ML_MASK_TIME_TOLERANCE_S)
            & (t_s <= mask.end_engine_s + ML_MASK_TIME_TOLERANCE_S))


@dataclass(frozen=True)
class EpisodeTags:
    """Spec rev. 51 223.2 tags of one run (``fault_tail`` is the :class:`MlMask`).

    Attributes:
        rod_collapse_windows_s: ``(start_s, end_s)`` engine-time windows around the locked
            lift-offs whose rod pressure collapsed (``plant_rod_collapse``).
        is_reapproach_pingpong: At least three re-approach starts later than event + 1.5 s.
        release_steps: ``(t_b_s, leg_index)`` of the releases with a rod-reading step
            (``plant_release_rod_step``); the window is ``[t_b, t_b + 0.3 s]`` of that leg.
    """

    rod_collapse_windows_s: tuple[tuple[float, float], ...] = ()
    is_reapproach_pingpong: bool = False
    release_steps: tuple[tuple[float, int], ...] = ()


def rod_collapse_window_s(run: str, leg: str, liftoff_s: float) -> tuple[float, float]:
    """Lift-off +- 0.3 s, or up to the H-S8-4 re-grounding end for the three listed legs."""
    end_s = ROD_COLLAPSE_END_OVERRIDES_S.get((run, leg), liftoff_s + ROD_COLLAPSE_HALF_WINDOW_S)
    return liftoff_s - ROD_COLLAPSE_HALF_WINDOW_S, max(end_s, liftoff_s)


COLLAPSE_LIFTOFF_KEYS = ("t_engine_s", "liftoff_engine_s")
"""Lift-off time keys of a judge ``plant_rod_collapse`` item: the planned format and the one
``verify.s8_control`` writes (C-S8-34 ④, also ``start_engine_s`` / ``end_engine_s``)."""


def _collapse_liftoff_s(item: Mapping[str, Any]) -> float:
    for key in COLLAPSE_LIFTOFF_KEYS:
        if key in item:
            return float(item[key])
    raise KeyError(f"plant_rod_collapse item without {' / '.join(COLLAPSE_LIFTOFF_KEYS)}")


def _collapse_windows_from_verify(run: str, items) -> tuple[tuple[float, float], ...]:
    windows = []
    for item in items or ():
        liftoff_s = _collapse_liftoff_s(item)
        start_s, end_s = rod_collapse_window_s(run, str(item.get("leg")), liftoff_s)
        windows.append((start_s, float(item.get("end_engine_s", end_s))))
    return tuple(windows)


def _tags_from_verify(metrics: Mapping[str, Any]) -> dict[str, EpisodeTags]:
    """Tags written by the judge into ``ml_metrics`` (C-S8-34 ④ format, see
    :func:`load_episode_tags`)."""
    tags = {}
    for run, entry in metrics.items():
        windows = _collapse_windows_from_verify(run, entry.get(TAG_ROD_COLLAPSE))
        is_pingpong = bool(entry.get(TAG_PINGPONG))
        if windows or is_pingpong:
            tags[run] = EpisodeTags(windows, is_pingpong)
    return tags


def _rod_collapse_windows(path: Path) -> dict[str, list[tuple[float, float]]]:
    """Locked lift-offs with a rod drop > 50 bar of ``s8main_liftoff_rod.py`` (rev. 51 222.4)."""
    windows: dict[str, list[tuple[float, float]]] = {}
    for item in json.loads(path.read_text(encoding="utf-8"))["liftoffs"]:
        drop_bar = float(item["rod_before"]) - float(item["rod_after"])
        if item["locked"] and drop_bar > ROD_COLLAPSE_DROP_BAR:
            run = str(item["case"])
            window = rod_collapse_window_s(run, str(item["leg"]), float(item["t_s"]))
            windows.setdefault(run, []).append(window)
    return windows


def _release_steps(path: Path) -> dict[str, list[tuple[float, int]]]:
    """``releases_big`` of the hydraulics release scan (H-S8-4 12.6) by run."""
    steps: dict[str, list[tuple[float, int]]] = {}
    for item in json.loads(path.read_text(encoding="utf-8"))["releases_big"]:
        leg = LEG_NAMES.index(str(item["leg"]))
        steps.setdefault(str(item["case"]), []).append((float(item["t_boundary_s"]), leg))
    return steps


def _pingpong_runs(path: Path) -> set[str]:
    """Runs with >= 3 late re-approach starts of ``s8main_reapp_scan.py`` (rev. 51 222.3)."""
    rows = json.loads(path.read_text(encoding="utf-8"))["rows"]
    return {str(row["case"]) for row in rows
            if len(row.get("late_starts") or ()) >= PINGPONG_MIN_LATE_STARTS}


def _tags_from_control_results(folder: Path) -> dict[str, EpisodeTags]:
    windows = _rod_collapse_windows(folder / LIFTOFF_ROD_FILE)
    pingpong = _pingpong_runs(folder / REAPPROACH_SCAN_FILE)
    return {run: EpisodeTags(tuple(windows.get(run, ())), run in pingpong)
            for run in sorted(set(windows) | pingpong)}


def _with_release_steps(tags: dict[str, EpisodeTags], release_scan: Path
                        ) -> dict[str, EpisodeTags]:
    merged = dict(tags)
    for run, steps in _release_steps(release_scan).items():
        tag = merged.get(run, EpisodeTags())
        merged[run] = EpisodeTags(tag.rod_collapse_windows_s, tag.is_reapproach_pingpong,
                                  tuple(sorted(steps)))
    return dict(sorted(merged.items()))


def load_episode_tags(
    verify_path: Path,
    control_folder: Path | None = None,
    release_scan: Path | None = None,
) -> dict[str, EpisodeTags]:
    """Tags by run name, from the judge record or else from the rev. 51 control results.

    The judge writes the tags into ``verify_S8ML.json`` ``ml_metrics[run]`` (C-S8-34 ④):
    ``plant_rod_collapse`` = list of ``{"t_engine_s"`` or ``"liftoff_engine_s": ..., "leg": ...,
    "end_engine_s" (optional)}`` lift-offs, ``reapproach_pingpong`` = bool or a window dict
    (truthy = tagged). When no run carries them, one
    warning is logged and the tags are derived from ``control_folder``
    (``s8_ml_rev51_liftoff_rod.json``, ``s8_ml_rev51_reapp_scan.json``). ``release_scan``
    (hydraulics ``h_s8_4_release_scan.json``) adds ``plant_release_rod_step``.

    Raises:
        FileNotFoundError: Neither source has the tags (no ``control_folder`` given).
    """
    data = json.loads(Path(verify_path).read_text(encoding="utf-8"))
    metrics = data.get("ml_metrics") or {}
    has_judge_tags = any(TAG_ROD_COLLAPSE in entry or TAG_PINGPONG in entry
                         for entry in metrics.values())
    if has_judge_tags:
        tags = _tags_from_verify(metrics)
    else:
        logger.warning("%s has no %s / %s tags in ml_metrics (C-S8-34 ④ pending); using the "
                       "rev. 51 control results in %s", verify_path, TAG_ROD_COLLAPSE,
                       TAG_PINGPONG, control_folder)
        if control_folder is None:
            raise FileNotFoundError("no tag source: the judge record has no tags and no "
                                    "control result folder was given")
        tags = _tags_from_control_results(Path(control_folder))
    if release_scan is not None:
        tags = _with_release_steps(tags, Path(release_scan))
    return tags


def _tags_of(episode: Episode, tags: Mapping[str, EpisodeTags] | None) -> EpisodeTags:
    return (tags or {}).get(str(episode.meta.get("episode_id")), EpisodeTags())


def _rows_in(t_s: NDArray[np.float64], start_s: float, end_s: float) -> NDArray[np.bool_]:
    return ((t_s >= start_s - ML_MASK_TIME_TOLERANCE_S)
            & (t_s <= end_s + ML_MASK_TIME_TOLERANCE_S))


def rod_collapse_rows(
    episode: Episode, tags: Mapping[str, EpisodeTags] | None
) -> NDArray[np.bool_]:
    """Rows inside a tagged rod-collapse window (:func:`rod_collapse_window_s`)."""
    t_s = np.asarray(episode["t_s"], dtype=float)
    rows = np.zeros(t_s.size, dtype=bool)
    for start_s, end_s in _tags_of(episode, tags).rod_collapse_windows_s:
        rows |= _rows_in(t_s, start_s, end_s)
    return rows


def release_step_rows(
    episode: Episode, tags: Mapping[str, EpisodeTags] | None
) -> NDArray[np.bool_]:
    """(n, 4): rows of each leg inside ``[t_b, t_b + 0.3 s]`` of a tagged release step."""
    t_s = np.asarray(episode["t_s"], dtype=float)
    rows = np.zeros((t_s.size, LEG_COUNT), dtype=bool)
    for boundary_s, leg in _tags_of(episode, tags).release_steps:
        rows[:, leg] |= _rows_in(t_s, boundary_s, boundary_s + RELEASE_STEP_WINDOW_S)
    return rows


def uses_individual_pressures() -> bool:
    """Whether a sequence channel is built from one pressure sensor alone."""
    return bool(set(INDIVIDUAL_PRESSURE_CHANNELS) & set(LEG_CHANNELS))


def pingpong_window_s(episode: Episode) -> tuple[float, float] | None:
    """Ping-pong window (engine time) from the episode meta, ``None`` without an event time.

    Start = event + 1.5 s; end = end of the last re-approach that started after the event,
    + 1 s (``meta["reapproach_windows_s"]``, written by ``contact_episode.build_episode``).
    """
    event_s = episode.meta.get("event_t_s")
    if event_s is None:
        return None
    ends = [float(end) for start, end, _ in episode.meta.get("reapproach_windows_s") or ()
            if float(start) >= float(event_s) - ML_MASK_TIME_TOLERANCE_S]
    if not ends:
        return None
    return float(event_s) + PINGPONG_LATE_START_S, max(ends) + PINGPONG_END_ALLOWANCE_S


def pingpong_rows(
    episode: Episode, tags: Mapping[str, EpisodeTags] | None
) -> NDArray[np.bool_]:
    """Rows of the ``reapproach_pingpong`` window; every row when the meta has no timing."""
    t_s = np.asarray(episode["t_s"], dtype=float)
    if not _tags_of(episode, tags).is_reapproach_pingpong:
        return np.zeros(t_s.size, dtype=bool)
    window = pingpong_window_s(episode)
    if window is None:
        logger.warning("%s: ping-pong tag without event / re-approach times; whole episode "
                       "marked", episode.meta.get("episode_id"))
        return np.ones(t_s.size, dtype=bool)
    start_s, end_s = window
    return ((t_s >= start_s - ML_MASK_TIME_TOLERANCE_S)
            & (t_s <= end_s + ML_MASK_TIME_TOLERANCE_S))


def related_legs(leg: int) -> tuple[int, int, int, int]:
    """(self, diagonal, same side, same axle) for the FL, FR, RL, RR order."""
    return leg, LEG_COUNT - 1 - leg, leg ^ 2, leg ^ 1


def leg_channel_series(episode: Episode) -> NDArray[np.float32]:
    """Per sample and leg the :data:`LEG_CHANNELS`, scaled: (n, 4, C_leg)."""
    lower = np.asarray(episode["lower_reading_N"], dtype=float)
    band = np.asarray(episode["seal_band_N"], dtype=float)
    stroke = np.asarray(episode["stroke_corrected_m"], dtype=float)
    motor = np.asarray(episode["motor_stroke_m"], dtype=float)
    channels = np.stack(
        [
            lower / FORCE_SCALE_N,
            (lower - band) / FORCE_SCALE_N,
            band / FORCE_SCALE_N,
            stroke / (100 * STROKE_SCALE_M),
            (motor - stroke) / STROKE_SCALE_M,
            np.asarray(episode["command_m_s"], dtype=float) / SPEED_SCALE_M_S,
        ],
        axis=-1,
    )
    return np.nan_to_num(channels).astype(np.float32)


def global_channel_series(episode: Episode) -> NDArray[np.float32]:
    """Per sample the :data:`GLOBAL_CHANNELS`: (n, C_global)."""
    count = episode.sample_count
    specific_force = np.asarray(episode["specific_force_m_s2"], dtype=float)
    rate = np.asarray(episode["angular_rate_rad_s"], dtype=float)
    if episode.has("imu_specific_force_samples_m_s2"):
        sample_std = np.asarray(episode["imu_specific_force_samples_m_s2"]).std(axis=1)
    else:
        sample_std = np.zeros((count, 3))
    phase = np.asarray(episode["phase"]).astype(str)
    phase_columns = np.stack([phase == name for name in PHASES], axis=-1).astype(float)
    channels = np.concatenate(
        [
            specific_force / ACCELERATION_SCALE_M_S2,
            rate / RATE_SCALE_RAD_S,
            sample_std / (1e-3 * ACCELERATION_SCALE_M_S2),
            phase_columns,
        ],
        axis=-1,
    )
    return np.nan_to_num(channels).astype(np.float32)


def probe_context_series(episode: Episode) -> NDArray[np.float32]:
    """Per sample and leg the :data:`PROBE_CONTEXT` (last probe; zeros before any): (n, 4, 6)."""
    grounded = np.asarray(episode["probe_is_grounded"], dtype=float)
    has_probe = np.isfinite(grounded)
    context = np.stack(
        [
            grounded,
            np.asarray(episode["probe_load_estimate_N"], dtype=float) / FORCE_SCALE_N,
            np.asarray(episode["probe_stiffness_ratio"], dtype=float),
            np.asarray(episode["probe_attitude_ratio"], dtype=float),
            np.asarray(episode["probe_age_s"], dtype=float) / 10.0,
            has_probe.astype(float),
        ],
        axis=-1,
    )
    return np.nan_to_num(context).astype(np.float32)


@dataclass(frozen=True)
class Examples:
    """Examples of one or more episodes (row = one leg at one sample).

    Attributes:
        sequences: (N, H, C) window: 4 related legs x leg channels, then the global channels.
        context: (N, 6) probe context of the leg itself at the sample.
        labels: (N,) :class:`ContactClass` code.
        target_min_kN: (N,) window minimum of the true rod force [kN] (regression target).
        weights: (N,) training weight (boundary 0.5, rigid-crawler lift-off transient 0).
        record_index: (N,) index of the episode in the input list.
        row: (N,) sample row in its episode.
        leg: (N,) leg index.
    """

    sequences: NDArray[np.float32]
    context: NDArray[np.float32]
    labels: NDArray[np.int64]
    target_min_kN: NDArray[np.float32]
    weights: NDArray[np.float32]
    record_index: NDArray[np.int64]
    row: NDArray[np.int64]
    leg: NDArray[np.int64]

    @property
    def count(self) -> int:
        return int(self.labels.size)

    def subset(self, mask: NDArray[np.bool_]) -> Examples:
        return Examples(*(getattr(self, name)[mask] for name in self.__dataclass_fields__))


def channel_names() -> list[str]:
    """Names of the sequence channels in :attr:`Examples.sequences` order."""
    names = []
    for role in ("self", "diagonal", "side", "axle"):
        names += [f"{role}_{channel}" for channel in LEG_CHANNELS]
    return names + list(GLOBAL_CHANNELS)


def usable_rows(
    episode: Episode, window: int = WINDOW_SAMPLES, history_rows: int = 0
) -> NDArray[np.bool_]:
    """Rows with a full window (``history_rows`` preceding rows included), lifted (205.1
    exclusion) and a truth on every leg."""
    rows = np.asarray(episode["is_lifted"], dtype=bool).copy()
    rows &= np.all(np.isfinite(episode["true_force_min_N"]), axis=1)
    rows[: max(0, window - 1 - history_rows)] = False
    return rows


def has_liftoff_transient(meta: Mapping[str, Any]) -> bool:
    """Whether the lift-off exclusion applies to a run with this episode meta.

    Same rule as ``verify.s8_control.lift_transient_rules_apply`` (R40-4 / R40-6): a rigid
    crawler (``crawler_contact`` absent or ``"nsc_rigid"``), or a compliant crawler whose S8-L4
    check has not passed (``crawler_check_passed`` not True).
    """
    is_rigid = str(meta.get("crawler_contact") or RIGID_CRAWLER) == RIGID_CRAWLER
    return is_rigid or meta.get("crawler_check_passed") is not True


def liftoff_transient_rows(episode: Episode) -> NDArray[np.bool_]:
    """Rows within :data:`LIFTOFF_EXCLUSION_S` (inclusive) after a crawler lift-off.

    The lift-off is a rising edge of ``is_lifted``. An episode that starts lifted (a branch
    from a READY snapshot) took off before its first row; it has no excluded rows
    (ASSUMPTION: READY comes tens of seconds after the lift-off, dynamics 5.26.7).
    """
    t_s = np.asarray(episode["t_s"], dtype=float)
    excluded = np.zeros(t_s.size, dtype=bool)
    if not has_liftoff_transient(episode.meta):
        return excluded
    lifted = np.asarray(episode["is_lifted"], dtype=bool)
    liftoff_rows = np.flatnonzero(lifted[1:] & ~lifted[:-1]) + 1
    for row in liftoff_rows:
        # The tolerance keeps the row at exactly 8 s inside despite the 0.1 s grid rounding.
        excluded |= (t_s >= t_s[row]) & (t_s <= t_s[row] + LIFTOFF_EXCLUSION_S + 1e-9)
    return excluded


def example_weights(boundary: NDArray[np.bool_], transient: NDArray[np.bool_]) -> NDArray:
    """Per row and leg training weight: 0 in the lift-off transient, else boundary 0.5 or 1."""
    weights = np.where(boundary, BOUNDARY_WEIGHT, 1.0)
    weights[transient] = 0.0
    return weights


def _leg_view_series(episode: Episode, leg: int) -> NDArray[np.float32]:
    """Per sample the sequence channels seen by ``leg``: (n, C) in :func:`channel_names` order."""
    order = list(related_legs(leg))
    legs_part = leg_channel_series(episode)[:, order, :]
    legs_part = legs_part.reshape(legs_part.shape[0], -1)
    return np.concatenate([legs_part, global_channel_series(episode)], axis=1)


def _windows_at(series: NDArray[np.float32], end_rows: NDArray[np.int64], window: int
                ) -> NDArray[np.float32]:
    """``series[row - window + 1 : row + 1]`` for every row: (k, window, C)."""
    if end_rows.size == 0:
        return np.zeros((0, window, series.shape[1]), dtype=series.dtype)
    views = sliding_window_view(series, window, axis=0)  # (n - window + 1, C, window)
    return np.ascontiguousarray(views[end_rows - window + 1].transpose(0, 2, 1))


def episode_examples(
    episode: Episode,
    record_index: int = 0,
    window: int = WINDOW_SAMPLES,
    masks: Mapping[str, MlMask] | None = None,
    tags: Mapping[str, EpisodeTags] | None = None,
    history: Episode | None = None,
) -> Examples:
    """Every usable (row, leg) example of one episode, without the rows of its ML mask.

    Args:
        episode: The episode; examples come from its rows only.
        record_index: Value of :attr:`Examples.record_index`.
        window: Window length in samples.
        masks: ML masks by run (:func:`load_ml_masks`).
        tags: Tags by run (:func:`load_episode_tags`); ``plant_rod_collapse`` rows get weight 0.
        history: Rows that precede the episode's first row (the base run it branched from); its
            last ``window - 1`` rows complete the first windows.
    """
    history_rows = 0 if history is None else min(window - 1, history.sample_count)
    classes = truth_classes(episode["true_force_min_N"], episode.rod_weight_N, episode.F_min_N)
    row_weights = example_weights(boundary_mask(classes), liftoff_transient_rows(episode))
    row_weights[rod_collapse_rows(episode, tags)] = 0.0
    if uses_individual_pressures():
        # The stepped leg's pressures reach every leg's window as neighbour channels.
        row_weights[release_step_rows(episode, tags).any(axis=1)] = 0.0
    rows = np.flatnonzero(usable_rows(episode, window, history_rows)
                          & ~masked_rows(episode, masks))
    probe = probe_context_series(episode)
    true_min_N = np.asarray(episode["true_force_min_N"], dtype=float)
    parts = []
    for leg in range(LEG_COUNT):
        series = _leg_view_series(episode, leg)
        if history_rows:
            series = np.concatenate([_leg_view_series(history, leg)[-history_rows:], series])
        parts.append(Examples(
            sequences=_windows_at(series, rows + history_rows, window),
            context=probe[rows, leg].astype(np.float32),
            labels=classes[rows, leg].astype(np.int64),
            target_min_kN=(true_min_N[rows, leg] / 1e3).astype(np.float32),
            weights=row_weights[rows, leg].astype(np.float32),
            record_index=np.full(rows.size, record_index, dtype=np.int64),
            row=rows.astype(np.int64),
            leg=np.full(rows.size, leg, dtype=np.int64),
        ))
    return concatenate(parts)


def concatenate(parts: list[Examples]) -> Examples:
    """One :class:`Examples` of several."""
    return Examples(*(
        np.concatenate([getattr(part, name) for part in parts])
        for name in Examples.__dataclass_fields__
    ))


def _is_base_run(episode: Episode) -> bool:
    return str(episode.meta.get("episode_id")) == str(episode.meta.get("base_id"))


def branch_history(episode: Episode, candidates: Sequence[Episode]) -> Episode | None:
    """The base run ``episode`` branched from, when it ends one period before its first row.

    Base runs (``episode_id == base_id``) have no history themselves.
    """
    if _is_base_run(episode):
        return None
    period_s = float(episode.meta.get("period_s") or 0.1)
    first_s = float(np.asarray(episode["t_s"])[0])
    for candidate in candidates:
        if not _is_base_run(candidate) or candidate.meta.get("base_id") != episode.meta.get(
                "base_id"):
            continue
        gap_s = first_s - float(np.asarray(candidate["t_s"])[-1])
        if abs(gap_s - period_s) <= HISTORY_GAP_TOLERANCE * period_s:
            return candidate
    return None


def build_examples(
    episodes: list[Episode],
    window: int = WINDOW_SAMPLES,
    masks: Mapping[str, MlMask] | None = None,
    tags: Mapping[str, EpisodeTags] | None = None,
) -> Examples:
    """Examples of every episode (``record_index`` = position in ``episodes``).

    ``masks`` (:func:`load_ml_masks`) removes the masked rows, ``tags``
    (:func:`load_episode_tags`) sets the ``plant_rod_collapse`` weights to 0. A branched episode
    whose base run is also in ``episodes`` takes its window history from it
    (:func:`branch_history`).

    Raises:
        ValueError: ``episodes`` is empty.
    """
    if not episodes:
        raise ValueError("no episodes: the split share is empty (more base runs needed)")
    base_runs = [episode for episode in episodes if _is_base_run(episode)]
    return concatenate([
        episode_examples(episode, index, window, masks, tags, branch_history(episode, base_runs))
        for index, episode in enumerate(episodes)
    ])


FEATURE_CHUNK_ROWS = 50_000
"""Rows per chunk of :func:`tabular_features` (bounds the float64 working copy)."""


def tabular_features(examples: Examples) -> NDArray[np.float32]:
    """Hand features of the windows for the gradient-boosting baseline.

    Per sequence channel: last value, changes over 1 / 5 / 10 samples and the whole window,
    window minimum, maximum and least-squares slope; then the probe context. Computed in row
    chunks; every feature depends on its own row only, so chunking does not change a value.
    """
    if examples.count <= FEATURE_CHUNK_ROWS:
        return _tabular_features_of(examples.sequences, examples.context)
    return np.concatenate([
        _tabular_features_of(examples.sequences[start:start + FEATURE_CHUNK_ROWS],
                             examples.context[start:start + FEATURE_CHUNK_ROWS])
        for start in range(0, examples.count, FEATURE_CHUNK_ROWS)
    ])


def _tabular_features_of(sequences_f32: NDArray[np.float32], context: NDArray[np.float32]
                         ) -> NDArray[np.float32]:
    sequences = sequences_f32.astype(np.float64)
    window = sequences.shape[1]
    last = sequences[:, -1, :]
    columns = [last]
    for lag in (1, 5, 10, window - 1):
        columns.append(last - sequences[:, -1 - lag, :])
    columns += [sequences.min(axis=1), sequences.max(axis=1)]
    time = np.arange(window) - (window - 1) / 2.0
    columns.append(np.einsum("t,ntc->nc", time, sequences) / np.sum(time**2))
    columns.append(context.astype(np.float64))
    return np.concatenate(columns, axis=1).astype(np.float32)


def is_low_class(labels: NDArray[np.int64]) -> NDArray[np.bool_]:
    """U or L."""
    return (labels == ContactClass.UNDER_LOADED) | (labels == ContactClass.LIFTED)
