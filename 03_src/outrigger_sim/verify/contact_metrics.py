"""Truth classes and judge metrics of the contact-judge comparison (spec rev. 39 203.1, 203.3).

Shared by the offline judge replay (J_P / J_C, :mod:`outrigger_sim.control.contact_replay`), the
S8 verdict code and the ML evaluation (spec 205.6), so that every judge is scored the same way.
numpy only (the ML environment imports it too).

* Truth class per leg and 10 Hz sample (window ``(t_{k-1}, t_k]``): **L** lifted if the window
  minimum of the rod force plus the moving-part weight is at most 0.5 kN (ASSUMPTION, 203.1),
  **U** under-loaded if not L and the minimum is below ``F_min``, **G** grounded otherwise.
* Boundary samples: both samples around a class change (used for delays, left out of rates).
* Episode: a run of U or L samples on one leg; its start ``t_on`` is the first such sample.
* M1 missed episodes (+ one-sided 95 % Clopper-Pearson upper bound), M1' late detections,
  M2 false action flags, M3 action delay, M4 estimate error near ``F_min``.
* Optional scoring mask (:attr:`RecordJudgement.scored`): the ML evaluation leaves the rigid
  crawler lift-off transient out by ``t_on`` (spec 212.7 R42-3); the control gates do not.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum

import numpy as np
from numpy.typing import NDArray

LIFT_LIMIT_N = 500.0
"""203.1: rod force + moving weight at or below this = lifted (ASSUMPTION)."""
LATE_DETECTION_S = 0.3
"""M1' tau_d: one sensing period + d + tau_v (ASSUMPTION, 203.3)."""
FALSE_FLAG_MARGIN_N = 7500.0 + 2000.0
"""M2: an action flag is false when the truth stays at or above F_min + this (207)."""
FALSE_FLAG_HOLD_S = 2.0
NEAR_FMIN_BAND_N = (-5000.0, 10000.0)
"""M4: samples whose true force is in [F_min - 5 kN, F_min + 10 kN]."""
EARLY_FLAG_LOOKBACK_S = 5.0
"""M3: action flags this long before ``t_on`` count as early (negative delay; ASSUMPTION)."""
CONFIDENCE = 0.95


class ContactClass(IntEnum):
    """Truth class codes (also the ML class indices)."""

    GROUNDED = 0
    UNDER_LOADED = 1
    LIFTED = 2
    UNKNOWN = -1
    """No truth (missing pad record) or excluded (crawler-supported phase)."""


def truth_classes(
    true_force_min_N: NDArray[np.float64],
    rod_weight_N: NDArray[np.float64],
    F_min_N: float,
) -> NDArray[np.int64]:
    """Class code per sample and leg (n, 4); NaN truth -> UNKNOWN."""
    force = np.asarray(true_force_min_N, dtype=float)
    classes = np.full(force.shape, ContactClass.GROUNDED, dtype=np.int64)
    classes[force < F_min_N] = ContactClass.UNDER_LOADED
    classes[force + np.asarray(rod_weight_N, dtype=float) <= LIFT_LIMIT_N] = ContactClass.LIFTED
    classes[~np.isfinite(force)] = ContactClass.UNKNOWN
    return classes


def boundary_mask(classes: NDArray[np.int64]) -> NDArray[np.bool_]:
    """Samples on either side of a class change, per leg (n, 4)."""
    change = np.zeros(classes.shape, dtype=bool)
    changed = classes[1:] != classes[:-1]
    change[1:] |= changed
    change[:-1] |= changed
    return change


@dataclass(frozen=True)
class ContactEpisode:
    """A run of U or L samples on one leg (rows inclusive)."""

    leg: int
    on_row: int
    off_row: int
    is_lift: bool
    """At least one L sample."""


def contact_episodes(classes: NDArray[np.int64]) -> list[ContactEpisode]:
    """U / L runs per leg, in time order."""
    episodes = []
    is_low = (classes == ContactClass.UNDER_LOADED) | (classes == ContactClass.LIFTED)
    for leg in range(classes.shape[1]):
        row = 0
        rows = is_low[:, leg]
        while row < rows.size:
            if not rows[row]:
                row += 1
                continue
            start = row
            while row < rows.size and rows[row]:
                row += 1
            is_lift = bool(np.any(classes[start:row, leg] == ContactClass.LIFTED))
            episodes.append(ContactEpisode(leg, start, row - 1, is_lift))
    return sorted(episodes, key=lambda episode: (episode.on_row, episode.leg))


def clopper_pearson_upper(failures: int, trials: int, confidence: float = CONFIDENCE) -> float:
    """One-sided upper confidence bound of a binomial rate (``1`` for no trials).

    Solves ``P(X <= failures; trials, p) = 1 - confidence`` for ``p`` by bisection (exact,
    no scipy); 0 failures in 75 trials gives 3.9 % (spec 205.4).
    """
    if trials <= 0:
        return 1.0
    if failures >= trials:
        return 1.0
    alpha = 1.0 - confidence

    def cdf(p: float) -> float:
        return sum(
            math.comb(trials, k) * p**k * (1.0 - p) ** (trials - k) for k in range(failures + 1)
        )

    low, high = 0.0, 1.0
    for _ in range(80):
        middle = 0.5 * (low + high)
        if cdf(middle) > alpha:
            low = middle
        else:
            high = middle
    return high


@dataclass(frozen=True)
class EpisodeDetection:
    """How one judge saw one truth episode."""

    episode: ContactEpisode
    first_decision_s: float | None
    """Time of the first decision flag in ``[t_on, t_off]`` (None = missed, M1)."""
    action_delay_s: float | None
    """First action flag in ``[t_on - lookback, t_off]`` minus ``t_on`` (M3)."""


def detect_episodes(
    t_s: NDArray[np.float64],
    episodes: list[ContactEpisode],
    decision_flags: NDArray[np.bool_],
    action_flags: NDArray[np.bool_],
) -> list[EpisodeDetection]:
    """Decision and action detection of every truth episode."""
    detections = []
    for episode in episodes:
        on_s = float(t_s[episode.on_row])
        rows = slice(episode.on_row, episode.off_row + 1)
        decided = np.flatnonzero(decision_flags[rows, episode.leg])
        first_decision = None if decided.size == 0 else float(t_s[episode.on_row + decided[0]])
        early_start = int(np.searchsorted(t_s, on_s - EARLY_FLAG_LOOKBACK_S - 1e-9))
        acted = np.flatnonzero(action_flags[early_start:episode.off_row + 1, episode.leg])
        delay = None if acted.size == 0 else float(t_s[early_start + acted[0]]) - on_s
        detections.append(EpisodeDetection(episode, first_decision, delay))
    return detections


def false_action_flags(
    t_s: NDArray[np.float64],
    action_flags: NDArray[np.bool_],
    true_force_min_N: NDArray[np.float64],
    F_min_N: float,
) -> int:
    """M2: action flags after which the true force stays >= F_min + 9.5 kN for 2 s."""
    level = F_min_N + FALSE_FLAG_MARGIN_N
    count = 0
    for row, leg in zip(*np.nonzero(action_flags), strict=True):
        last = int(np.searchsorted(t_s, t_s[row] + FALSE_FLAG_HOLD_S + 1e-9))
        window = true_force_min_N[row:last, leg]
        if window.size and np.all(window >= level):
            count += 1
    return count


def near_fmin_errors_N(
    estimate_N: NDArray[np.float64], true_force_N: NDArray[np.float64], F_min_N: float
) -> NDArray[np.float64]:
    """M4 samples: estimate - truth where the truth is within the F_min band (samples without
    an estimate, NaN, are left out)."""
    low, high = NEAR_FMIN_BAND_N
    truth = np.asarray(true_force_N, dtype=float)
    estimate = np.asarray(estimate_N, dtype=float)
    near = np.isfinite(truth) & (truth >= F_min_N + low) & (truth <= F_min_N + high)
    near &= np.isfinite(estimate)
    return (estimate - truth)[near]


@dataclass(frozen=True)
class JudgeScore:
    """203.3 M1-M4 of one judge over one or more records."""

    episode_count: int
    missed: int
    missed_upper_95: float
    late: int
    false_action_flags: int
    watched_hours: float
    action_delays_s: tuple[float, ...]
    near_fmin_error_max_N: float | None
    near_fmin_error_percentiles_N: tuple[float, float, float] | None
    """5 / 50 / 95 %."""

    @property
    def false_flags_per_hour(self) -> float | None:
        return None if self.watched_hours <= 0 else self.false_action_flags / self.watched_hours

    @property
    def median_action_delay_s(self) -> float | None:
        return float(np.median(self.action_delays_s)) if self.action_delays_s else None

    def to_dict(self) -> dict:
        return {
            "episodes": self.episode_count,
            "M1_missed": self.missed,
            "M1_missed_upper_95": self.missed_upper_95,
            "M1p_late": self.late,
            "M2_false_action_flags": self.false_action_flags,
            "M2_per_watched_hour": self.false_flags_per_hour,
            "M3_median_delay_s": self.median_action_delay_s,
            "M3_delays_s": list(self.action_delays_s),
            "M4_max_N": self.near_fmin_error_max_N,
            "M4_p5_p50_p95_N": self.near_fmin_error_percentiles_N,
        }


@dataclass(frozen=True)
class RecordJudgement:
    """Inputs of one judge on one record for :func:`score_judge`."""

    t_s: NDArray[np.float64]
    classes: NDArray[np.int64]
    decision_flags: NDArray[np.bool_]
    action_flags: NDArray[np.bool_]
    estimate_N: NDArray[np.float64]
    true_force_N: NDArray[np.float64]
    true_force_min_N: NDArray[np.float64]
    watched: NDArray[np.bool_]
    """Samples that count (lifted, truth known), (n,)."""
    scored: NDArray[np.bool_] | None = None
    """Optional narrower scoring mask (n,), e.g. the ML evaluation mask (spec 212.7 R42).

    Episodes are still found on the ``watched`` samples (their full extent); an episode counts
    only when its ``t_on`` sample is scored (R42-3), and the sample metrics (M2 flags, watched
    hours, M4) use only scored samples. ``None`` = every watched sample (control gates, I1).
    """


def _scored_samples(record: RecordJudgement) -> NDArray[np.bool_]:
    if record.scored is None:
        return record.watched
    return record.watched & record.scored


def score_judge(records: list[RecordJudgement], F_min_N: float) -> JudgeScore:
    """M1-M4 summed over the records of one judge."""
    episode_count = missed = late = false_flags = 0
    watched_s = 0.0
    delays: list[float] = []
    errors: list[NDArray[np.float64]] = []
    for record in records:
        scored = _scored_samples(record)
        classes = np.where(record.watched[:, None], record.classes, ContactClass.UNKNOWN)
        episodes = [episode for episode in contact_episodes(classes) if scored[episode.on_row]]
        detections = detect_episodes(
            record.t_s, episodes, record.decision_flags, record.action_flags
        )
        for detection in detections:
            episode_count += 1
            on_s = float(record.t_s[detection.episode.on_row])
            if detection.first_decision_s is None:
                missed += 1
            elif detection.first_decision_s > on_s + LATE_DETECTION_S + 1e-9:
                late += 1
            if detection.action_delay_s is not None:
                delays.append(detection.action_delay_s)
        watched_flags = record.action_flags & scored[:, None]
        false_flags += false_action_flags(
            record.t_s, watched_flags, record.true_force_min_N, F_min_N
        )
        period_s = float(np.median(np.diff(record.t_s))) if record.t_s.size > 1 else 0.0
        watched_s += float(np.count_nonzero(scored)) * period_s
        rows = scored
        errors.append(near_fmin_errors_N(record.estimate_N[rows], record.true_force_N[rows],
                                         F_min_N))
    all_errors = np.concatenate(errors) if errors else np.zeros(0)
    percentiles = None
    if all_errors.size:
        p5, p50, p95 = np.percentile(all_errors, [5, 50, 95])
        percentiles = (float(p5), float(p50), float(p95))
    return JudgeScore(
        episode_count=episode_count,
        missed=missed,
        missed_upper_95=clopper_pearson_upper(missed, episode_count),
        late=late,
        false_action_flags=false_flags,
        watched_hours=watched_s / 3600.0,
        action_delays_s=tuple(delays),
        near_fmin_error_max_N=float(all_errors.max()) if all_errors.size else None,
        near_fmin_error_percentiles_N=percentiles,
    )


def expected_calibration_error(
    probabilities: NDArray[np.float64], outcomes: NDArray[np.bool_], bins: int = 10
) -> float:
    """ECE of a binary probability (equal-width bins, sample-weighted; spec 205.6 E4)."""
    probabilities = np.asarray(probabilities, dtype=float)
    outcomes = np.asarray(outcomes, dtype=bool)
    if probabilities.size == 0:
        return 0.0
    edges = np.linspace(0.0, 1.0, bins + 1)
    bin_index = np.clip(np.digitize(probabilities, edges[1:-1]), 0, bins - 1)
    total = 0.0
    for index in range(bins):
        members = bin_index == index
        if not members.any():
            continue
        gap = abs(probabilities[members].mean() - outcomes[members].mean())
        total += gap * members.sum()
    return total / probabilities.size
