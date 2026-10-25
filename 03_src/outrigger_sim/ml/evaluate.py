"""Score an ML judge against the replayed physics judge J_C on the same records (spec 205.6).

ML flags (ASSUMPTION, the spec leaves the mapping to python):

* decision level: ``P(U) + P(L) >= threshold`` (default 0.5);
* load estimate: the predicted window minimum of the rod force (M4, E2);
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
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.contact_episode import LEG_COUNT, Episode
from outrigger_sim.control.contact_replay import (
    Judge,
    ReplaySettings,
    record_judgement,
    replay_both,
    watched_samples,
)
from outrigger_sim.ml.dataset import (
    Examples,
    MlMask,
    build_examples,
    is_low_class,
    liftoff_transient_rows,
    masked_rows,
)
from outrigger_sim.verify.contact_metrics import (
    JudgeScore,
    RecordJudgement,
    expected_calibration_error,
    score_judge,
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
    """

    ml: JudgeScore
    combined: JudgeScore
    ece: float
    examples: int
    transient: SetScores | None = None

    def to_dict(self) -> dict[str, Any]:
        transient = None if self.transient is None else self.transient.to_dict()
        return {"ML": self.ml.to_dict(), "J_C": self.combined.to_dict(), "ECE": self.ece,
                "examples": self.examples, "E7_liftoff_transient": transient}


def _judgements(
    episodes: Sequence[Episode],
    examples: Examples,
    prediction: Any,
    settings_for: Callable[[Episode], ReplaySettings],
) -> tuple[list[RecordJudgement], list[RecordJudgement]]:
    """Unmasked ML and replayed J_C judgements of every episode."""
    ml_records, jc_records = [], []
    for index, episode in enumerate(episodes):
        settings = settings_for(episode)
        mask = examples.record_index == index
        ml_records.append(ml_record_judgement(
            episode, examples.row[mask], examples.leg[mask],
            prediction.probabilities[mask], prediction.min_force_kN[mask], settings,
        ))
        replay = replay_both(episode, settings)[Judge.COMBINED]
        jc_records.append(record_judgement(episode, replay))
    return ml_records, jc_records


def _scored_examples(examples: Examples, sample_masks: list[NDArray[np.bool_]]) -> NDArray:
    """Examples whose (episode, row) sample is in that episode's mask."""
    selected = np.zeros(examples.count, dtype=bool)
    for index, sample_mask in enumerate(sample_masks):
        in_record = examples.record_index == index
        selected[in_record] = sample_mask[examples.row[in_record]]
    return selected


def _masked_scores(
    ml_records: list[RecordJudgement],
    jc_records: list[RecordJudgement],
    sample_masks: list[NDArray[np.bool_]],
    examples: Examples,
    prediction: Any,
    F_min_N: float,
) -> SetScores:
    """ML and J_C scores restricted to the same per-episode sample masks."""

    def masked(records: list[RecordJudgement]) -> list[RecordJudgement]:
        return [replace(record, scored=sample_mask)
                for record, sample_mask in zip(records, sample_masks, strict=True)]

    selected = _scored_examples(examples, sample_masks)
    probabilities = prediction.probabilities[selected]
    low_probability = probabilities[:, 1] + probabilities[:, 2]
    ece = expected_calibration_error(low_probability, is_low_class(examples.labels[selected]))
    return SetScores(score_judge(masked(ml_records), F_min_N),
                     score_judge(masked(jc_records), F_min_N), ece, int(selected.sum()))


def score_set(
    episodes: Sequence[Episode],
    predict: Callable[[Examples], Any],
    settings_for: Callable[[Episode], ReplaySettings],
    masks: Mapping[str, MlMask] | None = None,
) -> SetScores:
    """ML and replayed J_C scores on the same episodes (``predict`` -> ``Prediction``).

    E1-E4 scores use :func:`ml_scored_samples` for both judges; the left-out lift-off transient
    is scored apart in :attr:`SetScores.transient` (E7). ``masks`` (``verify_S8ML.json``
    ``ml_masks``) removes the masked rows from the examples and from both judges' scores.
    """
    examples = build_examples(list(episodes), masks=masks)
    prediction = predict(examples)
    ml_records, jc_records = _judgements(episodes, examples, prediction, settings_for)
    F_min_N = episodes[0].F_min_N if episodes else 0.0
    scored = [ml_scored_samples(episode, masks) for episode in episodes]
    transient = [liftoff_transient_samples(episode, masks) for episode in episodes]
    transient_scores = None
    if any(sample_mask.any() for sample_mask in transient):
        transient_scores = _masked_scores(ml_records, jc_records, transient, examples,
                                          prediction, F_min_N)
    scores = _masked_scores(ml_records, jc_records, scored, examples, prediction, F_min_N)
    return replace(scores, transient=transient_scores)


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
    return rows


def _record_metrics(score: JudgeScore) -> dict[str, Any]:
    return {"episodes": score.episode_count, "M1_missed": score.missed,
            "M2_false_action_flags": score.false_action_flags,
            "M4_max_N": score.near_fmin_error_max_N}


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
