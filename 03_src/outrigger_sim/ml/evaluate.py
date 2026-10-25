"""Score an ML judge against the replayed physics judge J_C on the same records (spec 205.6).

ML flags (ASSUMPTION, the spec leaves the mapping to python):

* decision level: ``P(U) + P(L) >= threshold`` (default 0.5; spec rev. 52 233 picks it on the
  validation share, :func:`select_threshold`);
* load estimate: the predicted window minimum of the rod force (M4, E2), or its lower quantile
  when the model has one (``Prediction.load_estimate_kN``, spec rev. 52 233);
* action level: the rising edge of (decision, or the estimate below ``F_min + 7.5 kN`` for the
  P5 confirmation count) - the ML counterpart of P5 / R-5.

J_C is replayed with the run's own controller settings and the recorded phases
(:attr:`WatchMode.CONTROLLER`): the records come from J_C closed loops (205.6 limitation:
open-loop evaluation only).

Scored samples (spec 212.7 R42-1..5, U-S8-10): E1-E4 leave out the rigid-crawler lift-off
transient, with the same function as the training exclusion
(:func:`~outrigger_sim.ml.dataset.liftoff_transient_rows`), for ML and J_C alike
(:func:`ml_scored_samples`). Truth episodes count by their ``t_on``. The left-out samples are
scored apart as the record row E7. The control gate I1 keeps them: ``watched_samples`` and
``verify.s8_control`` are unchanged. With the ML masks of ``verify_S8ML.json``
(:func:`~outrigger_sim.ml.dataset.load_ml_masks`, C-S8-27 ④: FAULT entry .. run end) the
masked samples are scored by neither judge, in E1-E4 and E7 alike.

Tags (spec rev. 51 223.2, P-S8-18, :func:`~outrigger_sim.ml.dataset.load_episode_tags`): E1-E4
keep the ``plant_rod_collapse``, ``plant_release_rod_step`` (rows where any leg is in its
window) and ``reapproach_pingpong`` windows. They are scored again apart
(:attr:`SetScores.tagged`): each window alone, and the scored samples without the ping-pong
windows, for ML and J_C alike.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.contact_episode import LEG_COUNT, LEG_NAMES, Episode
from outrigger_sim.control.contact_replay import (
    Judge,
    ReplaySettings,
    record_judgement,
    replay_both,
    watched_samples,
)
from outrigger_sim.ml.dataset import (
    TAG_PINGPONG,
    TAG_RELEASE_STEP,
    TAG_ROD_COLLAPSE,
    EpisodeTags,
    Examples,
    MlMask,
    build_examples,
    is_low_class,
    liftoff_transient_rows,
    masked_rows,
    pingpong_rows,
    release_step_rows,
    rod_collapse_rows,
)
from outrigger_sim.verify.contact_metrics import (
    NEAR_FMIN_BAND_N,
    JudgeScore,
    RecordJudgement,
    expected_calibration_error,
    score_judge,
    scored_detections,
    truth_classes,
)

DECISION_THRESHOLD = 0.5
NONINFERIORITY_FORCE_N = 500.0
"""E2: ML M4 risk-side maximum <= J_C + 0.5 kN."""
EARLIER_DELAY_S = 0.2
"""E3: ML median action delay at least this much earlier."""
FALSE_FLAG_RATIO = 0.5
ECE_LIMIT = 0.05
LATENCY_P99_LIMIT_MS = 1.0
MODEL_SIZE_LIMIT_BYTES = 5 * 1024 * 1024
WITHOUT_PINGPONG = f"without_{TAG_PINGPONG}"
"""Tagged score set: the E1-E4 samples less the ping-pong windows."""


def ml_record_judgement(
    episode: Episode,
    rows: NDArray[np.int64],
    legs: NDArray[np.int64],
    probabilities: NDArray[np.float64],
    min_force_kN: NDArray[np.float64],
    settings: ReplaySettings,
    threshold: float = DECISION_THRESHOLD,
) -> RecordJudgement:
    """Per-sample ML flags of one episode from its example predictions."""
    count = episode.sample_count
    low_probability = np.zeros((count, LEG_COUNT))
    estimate = np.full((count, LEG_COUNT), np.nan)
    low_probability[rows, legs] = probabilities[:, 1] + probabilities[:, 2]
    estimate[rows, legs] = min_force_kN * 1e3
    decision = low_probability >= threshold
    is_low_estimate = np.nan_to_num(estimate, nan=np.inf) < settings.relevel_level_N
    confirmed = np.zeros_like(is_low_estimate)
    run = np.zeros(LEG_COUNT, dtype=int)
    for row in range(count):
        run = np.where(is_low_estimate[row], run + 1, 0)
        confirmed[row] = run >= settings.relevel_samples
    wants_action = decision | confirmed
    action = wants_action.copy()
    action[1:] &= ~wants_action[:-1]
    return RecordJudgement(
        t_s=np.asarray(episode["t_s"], dtype=float),
        classes=truth_classes(episode["true_force_min_N"], episode.rod_weight_N,
                              episode.F_min_N),
        decision_flags=decision,
        action_flags=action,
        estimate_N=estimate,
        true_force_N=np.asarray(episode["true_force_N"], dtype=float),
        true_force_min_N=np.asarray(episode["true_force_min_N"], dtype=float),
        watched=watched_samples(episode),
    )


def ml_scored_samples(
    episode: Episode, masks: Mapping[str, MlMask] | None = None
) -> NDArray[np.bool_]:
    """Samples scored by E1-E4 (R42-1 / R42-5): the 203.3 ``watched_samples`` without the
    rigid-crawler lift-off transient (the training exclusion of ``ml.dataset``) and without
    the run's ML mask."""
    return (watched_samples(episode) & ~liftoff_transient_rows(episode)
            & ~masked_rows(episode, masks))


def liftoff_transient_samples(
    episode: Episode, masks: Mapping[str, MlMask] | None = None
) -> NDArray[np.bool_]:
    """Watched samples that :func:`ml_scored_samples` leaves out for the lift-off transient:
    the E7 record row (R42-4), also without the run's ML mask."""
    return (watched_samples(episode) & liftoff_transient_rows(episode)
            & ~masked_rows(episode, masks))


@dataclass(frozen=True)
class SetScores:
    """Scores of one evaluation set.

    Attributes:
        ml: ML M1-M4 on the scored samples.
        combined: Replayed J_C M1-M4 on the same samples (R42-2).
        ece: ML ECE of the scored examples (E4).
        examples: Number of scored examples.
        transient: The same scores on the left-out lift-off transient only (E7); ``None`` when
            no episode of the set has one (compliant crawler that passed S8-L4, or branches).
        tagged: Scores on the tag windows (:data:`TAG_ROD_COLLAPSE`, :data:`TAG_RELEASE_STEP`,
            :data:`TAG_PINGPONG`) and
            on the E1-E4 samples without the ping-pong windows (:data:`WITHOUT_PINGPONG`);
            only the tags present in the set.
    """

    ml: JudgeScore
    combined: JudgeScore
    ece: float
    examples: int
    transient: SetScores | None = None
    tagged: Mapping[str, SetScores] | None = None

    def to_dict(self) -> dict[str, Any]:
        transient = None if self.transient is None else self.transient.to_dict()
        tagged = {name: scores.to_dict() for name, scores in (self.tagged or {}).items()}
        return {"ML": self.ml.to_dict(), "J_C": self.combined.to_dict(), "ECE": self.ece,
                "examples": self.examples, "E7_liftoff_transient": transient,
                "tagged": tagged}


@dataclass(frozen=True)
class ExampleKeys:
    """Where each example sits (no window data): enough to score a prediction."""

    labels: NDArray[np.int64]
    record_index: NDArray[np.int64]
    row: NDArray[np.int64]
    leg: NDArray[np.int64]
    target_min_kN: NDArray[np.float32]
    weights: NDArray[np.float32]

    @classmethod
    def of(cls, examples: Examples) -> ExampleKeys:
        return cls(examples.labels, examples.record_index, examples.row, examples.leg,
                   examples.target_min_kN, examples.weights)

    @property
    def count(self) -> int:
        return int(self.labels.size)


@dataclass(frozen=True)
class ScoringContext:
    """Model-independent part of scoring one set: built once, used for every model, seed and
    threshold (:func:`prepare_scoring`, :func:`score_prediction`).

    Attributes:
        episodes: Episodes the ML examples come from (truth, phases, sample masks).
        keys: Example positions of the set's examples.
        settings: Replay settings per episode.
        jc_records: Replayed J_C judgements per episode, unmasked.
        scored: E1-E4 sample mask per episode (:func:`ml_scored_samples`).
        transient: E7 sample mask per episode (:func:`liftoff_transient_samples`).
        tag_masks: Per tagged score set, the sample masks (``None`` without tags).
        F_min_N: Minimum cylinder force of the set.
    """

    episodes: tuple[Episode, ...]
    keys: ExampleKeys
    settings: tuple[ReplaySettings, ...]
    jc_records: tuple[RecordJudgement, ...]
    scored: tuple[NDArray[np.bool_], ...]
    transient: tuple[NDArray[np.bool_], ...]
    tag_masks: Mapping[str, list[NDArray[np.bool_]]] | None
    F_min_N: float


def replay_combined(
    episodes: Sequence[Episode], settings_for: Callable[[Episode], ReplaySettings]
) -> list[RecordJudgement]:
    """Replayed J_C judgement of every episode (unmasked)."""
    records = []
    for episode in episodes:
        replay = replay_both(episode, settings_for(episode))[Judge.COMBINED]
        records.append(record_judgement(episode, replay))
    return records


def prepare_scoring(
    episodes: Sequence[Episode],
    examples: Examples,
    settings_for: Callable[[Episode], ReplaySettings],
    masks: Mapping[str, MlMask] | None = None,
    tags: Mapping[str, EpisodeTags] | None = None,
    jc_episodes: Sequence[Episode] | None = None,
) -> ScoringContext:
    """The :class:`ScoringContext` of one set.

    Args:
        episodes: Episodes whose readings the ML examples were built from.
        examples: ``build_examples(episodes, masks=masks, tags=tags)``.
        settings_for: Replay settings of an episode.
        masks: ML masks by run.
        tags: Episode tags by run (adds the tagged score sets).
        jc_episodes: Episodes the J_C replay reads (same runs and truth, possibly another
            reading basis, :mod:`outrigger_sim.ml.reading_basis`); ``None`` = ``episodes``.
    """
    episodes = tuple(episodes)
    replayed = episodes if jc_episodes is None else tuple(jc_episodes)
    if len(replayed) != len(episodes):
        raise ValueError("jc_episodes must hold the same runs as episodes")
    scored = tuple(ml_scored_samples(episode, masks) for episode in episodes)
    tag_masks = _tag_sample_masks(episodes, list(scored), tags) if tags else None
    return ScoringContext(
        episodes=episodes,
        keys=ExampleKeys.of(examples),
        settings=tuple(settings_for(episode) for episode in episodes),
        jc_records=tuple(replay_combined(replayed, settings_for)),
        scored=scored,
        transient=tuple(liftoff_transient_samples(episode, masks) for episode in episodes),
        tag_masks=tag_masks,
        F_min_N=episodes[0].F_min_N if episodes else 0.0,
    )


def ml_judgements(
    context: ScoringContext, prediction: Any, threshold: float = DECISION_THRESHOLD
) -> list[RecordJudgement]:
    """Unmasked ML judgements of every episode of the set (estimate =
    ``prediction.load_estimate_kN`` when the prediction has it, else ``min_force_kN``)."""
    estimate_kN = getattr(prediction, "load_estimate_kN", prediction.min_force_kN)
    keys = context.keys
    records = []
    for index, (episode, settings) in enumerate(zip(context.episodes, context.settings,
                                                    strict=True)):
        in_record = keys.record_index == index
        records.append(ml_record_judgement(
            episode, keys.row[in_record], keys.leg[in_record],
            prediction.probabilities[in_record], estimate_kN[in_record], settings, threshold,
        ))
    return records


def episode_detections(
    context: ScoringContext, records: Sequence[RecordJudgement]
) -> list[dict[str, Any]]:
    """Every truth episode scored by E1 (``t_on`` in the E1-E4 samples) and the judge's first
    decision in it (``None`` = missed), for the per-run miss lists."""
    rows = []
    for episode, record, sample_mask in zip(context.episodes, records, context.scored,
                                            strict=True):
        t_s = record.t_s
        for detection in scored_detections(replace(record, scored=sample_mask)):
            truth = detection.episode
            rows.append({"run": str(episode.meta.get("episode_id")),
                         "leg": LEG_NAMES[truth.leg],
                         "t_on_s": float(t_s[truth.on_row]),
                         "t_off_s": float(t_s[truth.off_row]),
                         "is_lift": truth.is_lift,
                         "first_decision_s": detection.first_decision_s})
    return rows


def _scored_examples(keys: ExampleKeys, sample_masks: Sequence[NDArray[np.bool_]]) -> NDArray:
    """Examples whose (episode, row) sample is in that episode's mask."""
    selected = np.zeros(keys.count, dtype=bool)
    for index, sample_mask in enumerate(sample_masks):
        in_record = keys.record_index == index
        selected[in_record] = sample_mask[keys.row[in_record]]
    return selected


def _masked_scores(
    ml_records: Sequence[RecordJudgement],
    jc_records: Sequence[RecordJudgement],
    sample_masks: Sequence[NDArray[np.bool_]],
    keys: ExampleKeys,
    prediction: Any,
    F_min_N: float,
) -> SetScores:
    """ML and J_C scores restricted to the same per-episode sample masks."""

    def masked(records: Sequence[RecordJudgement]) -> list[RecordJudgement]:
        return [replace(record, scored=sample_mask)
                for record, sample_mask in zip(records, sample_masks, strict=True)]

    selected = _scored_examples(keys, sample_masks)
    probabilities = prediction.probabilities[selected]
    low_probability = probabilities[:, 1] + probabilities[:, 2]
    ece = expected_calibration_error(low_probability, is_low_class(keys.labels[selected]))
    return SetScores(score_judge(masked(ml_records), F_min_N),
                     score_judge(masked(jc_records), F_min_N), ece, int(selected.sum()))


def score_prediction(
    context: ScoringContext, prediction: Any, threshold: float = DECISION_THRESHOLD
) -> SetScores:
    """ML (``prediction`` on ``context.keys``) and J_C scores of one set; see
    :func:`score_set`."""
    ml_records = ml_judgements(context, prediction, threshold)
    jc_records = context.jc_records
    keys, F_min_N = context.keys, context.F_min_N
    transient_scores = None
    if any(sample_mask.any() for sample_mask in context.transient):
        transient_scores = _masked_scores(ml_records, jc_records, context.transient, keys,
                                          prediction, F_min_N)
    tagged = None
    if context.tag_masks is not None:
        tagged = {name: _masked_scores(ml_records, jc_records, sample_masks, keys, prediction,
                                       F_min_N)
                  for name, sample_masks in context.tag_masks.items()}
    scores = _masked_scores(ml_records, jc_records, context.scored, keys, prediction, F_min_N)
    return replace(scores, transient=transient_scores, tagged=tagged)


def _tag_sample_masks(
    episodes: Sequence[Episode],
    scored: list[NDArray[np.bool_]],
    tags: Mapping[str, EpisodeTags],
) -> dict[str, list[NDArray[np.bool_]]]:
    """Per tagged score set, the per-episode sample masks (sets without a sample left out)."""
    collapse = [rod_collapse_rows(episode, tags) for episode in episodes]
    pingpong = [pingpong_rows(episode, tags) for episode in episodes]
    release = [release_step_rows(episode, tags).any(axis=1) for episode in episodes]
    candidates = {
        TAG_ROD_COLLAPSE: [s & rows for s, rows in zip(scored, collapse, strict=True)],
        TAG_RELEASE_STEP: [s & rows for s, rows in zip(scored, release, strict=True)],
        TAG_PINGPONG: [s & rows for s, rows in zip(scored, pingpong, strict=True)],
        WITHOUT_PINGPONG: [s & ~rows for s, rows in zip(scored, pingpong, strict=True)],
    }
    if not any(rows.any() for rows in pingpong):
        del candidates[WITHOUT_PINGPONG]
    return {name: sample_masks for name, sample_masks in candidates.items()
            if any(sample_mask.any() for sample_mask in sample_masks)}


def score_set(
    episodes: Sequence[Episode],
    predict: Callable[[Examples], Any],
    settings_for: Callable[[Episode], ReplaySettings],
    masks: Mapping[str, MlMask] | None = None,
    tags: Mapping[str, EpisodeTags] | None = None,
    threshold: float = DECISION_THRESHOLD,
    jc_episodes: Sequence[Episode] | None = None,
) -> SetScores:
    """ML and replayed J_C scores on the same episodes (``predict`` -> ``Prediction``).

    E1-E4 scores use :func:`ml_scored_samples` for both judges; the left-out lift-off transient
    is scored apart in :attr:`SetScores.transient` (E7). ``masks`` (``verify_S8ML.json``
    ``ml_masks``) removes the masked rows from the examples and from both judges' scores.
    ``tags`` (:func:`~outrigger_sim.ml.dataset.load_episode_tags`) adds
    :attr:`SetScores.tagged`. ``threshold`` is the ML decision level on ``P(U) + P(L)``;
    ``jc_episodes`` lets J_C read another reading basis (:func:`prepare_scoring`).
    """
    examples = build_examples(list(episodes), masks=masks, tags=tags)
    prediction = predict(examples)
    context = prepare_scoring(episodes, examples, settings_for, masks, tags, jc_episodes)
    return score_prediction(context, prediction, threshold)


def verdict_rows(
    test: SetScores, latency_p99_ms: float | None, model_bytes: int | None,
    out_of_distribution: dict[str, SetScores] | None = None,
) -> list[dict[str, Any]]:
    """Rows E1-E6 of spec 205.6 and E7 of 212.7 (``passed`` None = not judged)."""
    ml, jc = test.ml, test.combined
    rows = [{
        "item": "E1", "kind": "required",
        "value": {"ML_upper": ml.missed_upper_95, "J_C_upper": jc.missed_upper_95,
                  "ML_missed": ml.missed, "episodes": ml.episode_count},
        "passed": ml.missed_upper_95 <= jc.missed_upper_95 + 1e-12,
    }]
    e2 = None
    if ml.near_fmin_error_max_N is not None and jc.near_fmin_error_max_N is not None:
        e2 = ml.near_fmin_error_max_N <= jc.near_fmin_error_max_N + NONINFERIORITY_FORCE_N
    rows.append({"item": "E2", "kind": "required",
                 "value": {"ML_M4_max_N": ml.near_fmin_error_max_N,
                           "J_C_M4_max_N": jc.near_fmin_error_max_N}, "passed": e2})
    earlier = (ml.median_action_delay_s is not None and jc.median_action_delay_s is not None
               and ml.median_action_delay_s <= jc.median_action_delay_s - EARLIER_DELAY_S)
    fewer_false = (jc.false_action_flags > 0
                   and ml.false_action_flags <= FALSE_FLAG_RATIO * jc.false_action_flags)
    rows.append({"item": "E3", "kind": "candidate advantage",
                 "value": {"earlier_median_delay": earlier, "fewer_false_flags": fewer_false,
                           "probe_saving": "not evaluated"},
                 "passed": bool(earlier or fewer_false)})
    rows.append({"item": "E4", "kind": "required", "value": test.ece,
                 "passed": test.ece <= ECE_LIMIT})
    e5 = None
    if latency_p99_ms is not None and model_bytes is not None:
        e5 = latency_p99_ms <= LATENCY_P99_LIMIT_MS and model_bytes <= MODEL_SIZE_LIMIT_BYTES
    rows.append({"item": "E5", "kind": "required",
                 "value": {"p99_ms": latency_p99_ms, "bytes": model_bytes}, "passed": e5})
    for name, scores in (out_of_distribution or {}).items():
        rows.append({"item": f"E6 {name}", "kind": "record",
                     "value": {"ML_upper": scores.ml.missed_upper_95,
                               "J_C_upper": scores.combined.missed_upper_95,
                               "episodes": scores.ml.episode_count},
                     "passed": (scores.ml.missed_upper_95 <= scores.combined.missed_upper_95
                                if scores.ml.episode_count else None)})
    if test.transient is not None:
        rows.append(transient_row(test.transient))
    for name, scores in (test.tagged or {}).items():
        rows.append(tag_row(name, scores))
    return rows


def _record_metrics(score: JudgeScore) -> dict[str, Any]:
    return {"episodes": score.episode_count, "M1_missed": score.missed,
            "M2_false_action_flags": score.false_action_flags,
            "M4_max_N": score.near_fmin_error_max_N}


def _tag_metrics(score: JudgeScore) -> dict[str, Any]:
    return {**_record_metrics(score), "M1_missed_upper_95": score.missed_upper_95,
            "M1p_late": score.late, "M3_median_delay_s": score.median_action_delay_s}


def tag_row(name: str, scores: SetScores) -> dict[str, Any]:
    """Record row of one tagged score set (spec rev. 51 223.2: E1 / E3 shown apart)."""
    return {"item": f"tag {name}", "kind": "record",
            "value": {"ML": _tag_metrics(scores.ml), "J_C": _tag_metrics(scores.combined),
                      "ECE": {"ML": scores.ece, "J_C": None}, "examples": scores.examples},
            "passed": None}


JC_ECE_NOTE = (
    "J_C deterministic, E4 applies to probability outputs only: J_C is a decision judge "
    "with 0/1 flags and no probability, so its ECE is undefined and recorded as None "
    "(spec rev. 44 214.5 question 3-1)"
)
"""Note of row E7 on the ``None`` ECE of J_C."""


def transient_row(transient: SetScores) -> dict[str, Any]:
    """Record row E7 (R42-4): M1, M2 and M4 of both judges and the ML ECE on the left-out
    lift-off transient.

    J_C is a deterministic decision judge: it gives 0/1 flags, not a probability. The ECE
    (E4) is defined for probability outputs only, so the J_C ECE is ``None`` (undefined, not
    zero and not missing data); the row ``note`` says so (spec rev. 44 214.5 question 3-1).
    """
    return {"item": "E7", "kind": "record",
            "value": {"ML": _record_metrics(transient.ml),
                      "J_C": _record_metrics(transient.combined),
                      "ECE": {"ML": transient.ece, "J_C": None},
                      "examples": transient.examples},
            "passed": None,
            "note": JC_ECE_NOTE}


# --- decision threshold (spec rev. 52 233) and quantile coverage -----------------------------

THRESHOLD_GRID: tuple[float, ...] = tuple(round(0.01 * step, 2) for step in range(1, 100))
"""Candidate decision levels on ``P(U) + P(L)``."""
NEUTRAL_THRESHOLD = 0.5
"""Last tie-break: among equally good candidates the level closest to this (ASSUMPTION)."""


@dataclass(frozen=True)
class ThresholdChoice:
    """Decision level picked on the validation share (spec rev. 52 233).

    Rule: among the levels whose validation ML misses are at most the J_C validation misses,
    the fewest false action flags (M2); ties -> fewer ML misses, then closest to 0.5. When no
    level meets the miss condition, the fewest misses, then the fewest false flags
    (``is_constraint_met`` False).
    """

    threshold: float
    ml_missed: int
    jc_missed: int
    false_action_flags: int
    is_constraint_met: bool
    candidates: tuple[dict[str, float | int], ...]

    def to_dict(self) -> dict[str, Any]:
        return {"threshold": self.threshold, "ML_missed": self.ml_missed,
                "J_C_missed": self.jc_missed, "ML_false_action_flags": self.false_action_flags,
                "constraint_met": self.is_constraint_met, "candidates": list(self.candidates)}


def _scored_score(context: ScoringContext, records: Sequence[RecordJudgement]) -> JudgeScore:
    """M1-M4 on the E1-E4 samples only (no tag or transient sets)."""
    masked = [replace(record, scored=sample_mask)
              for record, sample_mask in zip(records, context.scored, strict=True)]
    return score_judge(masked, context.F_min_N)


def select_threshold(
    context: ScoringContext, prediction: Any, grid: Sequence[float] = THRESHOLD_GRID
) -> ThresholdChoice:
    """Decision level from the validation share ``context`` (see :class:`ThresholdChoice`)."""
    jc_missed = _scored_score(context, context.jc_records).missed
    candidates = []
    for threshold in grid:
        ml = _scored_score(context, ml_judgements(context, prediction, threshold))
        candidates.append({"threshold": float(threshold), "ML_missed": ml.missed,
                           "ML_false_action_flags": ml.false_action_flags})

    def closeness(item: dict) -> float:
        return abs(item["threshold"] - NEUTRAL_THRESHOLD)

    feasible = [item for item in candidates if item["ML_missed"] <= jc_missed]
    if feasible:
        best = min(feasible, key=lambda item: (item["ML_false_action_flags"],
                                               item["ML_missed"], closeness(item)))
    else:
        best = min(candidates, key=lambda item: (item["ML_missed"],
                                                 item["ML_false_action_flags"], closeness(item)))
    return ThresholdChoice(best["threshold"], best["ML_missed"], jc_missed,
                           best["ML_false_action_flags"], bool(feasible), tuple(candidates))


def quantile_coverage(
    keys: ExampleKeys, prediction: Any, F_min_N: float
) -> dict[str, float | int | None]:
    """Share of examples whose true window minimum is at or above the load estimate.

    Over the weighted examples (weight > 0) and over those whose truth lies in the M4 band
    ``[F_min - 5 kN, F_min + 10 kN]``. For a lower-5 % quantile the target is >= 0.95 (spec
    rev. 52 233).
    """
    estimate_kN = getattr(prediction, "load_estimate_kN", prediction.min_force_kN)
    target_kN = keys.target_min_kN.astype(float)
    weighted = keys.weights > 0
    low, high = NEAR_FMIN_BAND_N
    near = (weighted & (target_kN * 1e3 >= F_min_N + low)
            & (target_kN * 1e3 <= F_min_N + high))

    def share(rows: NDArray[np.bool_]) -> float | None:
        count = int(rows.sum())
        return None if count == 0 else float(np.mean(target_kN[rows] >= estimate_kN[rows]))

    return {"all_weighted": share(weighted), "near_F_min_band": share(near),
            "examples": int(weighted.sum()), "near_examples": int(near.sum())}
