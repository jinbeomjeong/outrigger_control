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
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.contact_episode import LEG_COUNT, Episode
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


def usable_rows(episode: Episode, window: int = WINDOW_SAMPLES) -> NDArray[np.bool_]:
    """Rows with a full window, lifted (205.1 exclusion) and a truth on every leg."""
    rows = np.asarray(episode["is_lifted"], dtype=bool).copy()
    rows &= np.all(np.isfinite(episode["true_force_min_N"]), axis=1)
    rows[: window - 1] = False
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


def episode_examples(
    episode: Episode,
    record_index: int = 0,
    window: int = WINDOW_SAMPLES,
    masks: Mapping[str, MlMask] | None = None,
) -> Examples:
    """Every usable (row, leg) example of one episode, without the rows of its ML mask."""
    leg_series = leg_channel_series(episode)
    global_series = global_channel_series(episode)
    probe = probe_context_series(episode)
    classes = truth_classes(episode["true_force_min_N"], episode.rod_weight_N, episode.F_min_N)
    row_weights = example_weights(boundary_mask(classes), liftoff_transient_rows(episode))
    rows = np.flatnonzero(usable_rows(episode, window) & ~masked_rows(episode, masks))
    sequences, contexts, labels, targets, weights, legs, out_rows = [], [], [], [], [], [], []
    for leg in range(LEG_COUNT):
        order = list(related_legs(leg))
        for row in rows:
            span = slice(row - window + 1, row + 1)
            legs_part = leg_series[span][:, order, :].reshape(window, -1)
            sequences.append(np.concatenate([legs_part, global_series[span]], axis=1))
            contexts.append(probe[row, leg])
            labels.append(classes[row, leg])
            targets.append(episode["true_force_min_N"][row, leg] / 1e3)
            weights.append(row_weights[row, leg])
            legs.append(leg)
            out_rows.append(row)
    count = len(labels)
    channel_count = len(channel_names())
    return Examples(
        sequences=np.asarray(sequences, dtype=np.float32).reshape(count, window, channel_count),
        context=np.asarray(contexts, dtype=np.float32).reshape(count, len(PROBE_CONTEXT)),
        labels=np.asarray(labels, dtype=np.int64),
        target_min_kN=np.asarray(targets, dtype=np.float32),
        weights=np.asarray(weights, dtype=np.float32),
        record_index=np.full(count, record_index, dtype=np.int64),
        row=np.asarray(out_rows, dtype=np.int64),
        leg=np.asarray(legs, dtype=np.int64),
    )


def concatenate(parts: list[Examples]) -> Examples:
    """One :class:`Examples` of several."""
    return Examples(*(
        np.concatenate([getattr(part, name) for part in parts])
        for name in Examples.__dataclass_fields__
    ))


def build_examples(
    episodes: list[Episode],
    window: int = WINDOW_SAMPLES,
    masks: Mapping[str, MlMask] | None = None,
) -> Examples:
    """Examples of every episode (``record_index`` = position in ``episodes``); ``masks``
    (:func:`load_ml_masks`) removes the masked rows.

    Raises:
        ValueError: ``episodes`` is empty.
    """
    if not episodes:
        raise ValueError("no episodes: the split share is empty (more base runs needed)")
    return concatenate([episode_examples(e, index, window, masks)
                        for index, e in enumerate(episodes)])


def tabular_features(examples: Examples) -> NDArray[np.float32]:
    """Hand features of the windows for the gradient-boosting baseline.

    Per sequence channel: last value, changes over 1 / 5 / 10 samples and the whole window,
    window minimum, maximum and least-squares slope; then the probe context.
    """
    sequences = examples.sequences.astype(np.float64)
    window = sequences.shape[1]
    last = sequences[:, -1, :]
    columns = [last]
    for lag in (1, 5, 10, window - 1):
        columns.append(last - sequences[:, -1 - lag, :])
    columns += [sequences.min(axis=1), sequences.max(axis=1)]
    time = np.arange(window) - (window - 1) / 2.0
    columns.append(np.einsum("t,ntc->nc", time, sequences) / np.sum(time**2))
    columns.append(examples.context.astype(np.float64))
    return np.concatenate(columns, axis=1).astype(np.float32)


def is_low_class(labels: NDArray[np.int64]) -> NDArray[np.bool_]:
    """U or L."""
    return (labels == ContactClass.UNDER_LOADED) | (labels == ContactClass.LIFTED)
