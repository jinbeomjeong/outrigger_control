"""Ground-contact ML pipeline (P-S8-2, spec rev. 39 205) on synthetic episodes.

The dataset and split tests need numpy only. The training and ONNX tests need the ML environment
(torch, lightgbm, onnxruntime; onnxscript for the dynamo export, onnxmltools for the LightGBM
export) and are skipped elsewhere:

    C:\\ProgramData\\miniforge3\\envs\\pytorch_214_cuda_python_313\\python.exe -m pytest \\
        05_tests/unit/test_ml_pipeline.py -p no:cacheprovider
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from outrigger_sim.contact_episode import LEG_COUNT, Episode
from outrigger_sim.control.contact_replay import (
    Judge,
    ReplaySettings,
    record_judgement,
    replay_both,
    watched_samples,
)
from outrigger_sim.ml.dataset import (
    GLOBAL_CHANNELS,
    LEG_CHANNELS,
    LIFTOFF_EXCLUSION_S,
    WINDOW_SAMPLES,
    build_examples,
    channel_names,
    episode_examples,
    liftoff_transient_rows,
    related_legs,
    tabular_features,
    usable_rows,
)
from outrigger_sim.ml.evaluate import (
    liftoff_transient_samples,
    ml_scored_samples,
    score_set,
    verdict_rows,
)
from outrigger_sim.ml.split import split_by_base
from outrigger_sim.ml.synthetic import (
    F_MIN_N,
    LIFT_S,
    SyntheticCase,
    synthetic_cases,
    synthetic_episode,
)
from outrigger_sim.verify.contact_metrics import ContactClass, score_judge

COMPLIANT_PASSED = {"crawler_contact": "nsc_compliant", "crawler_check_passed": True}


@pytest.fixture(scope="module")
def episodes():
    return [synthetic_episode(case, duration_s=40.0) for case in synthetic_cases(8, 3, seed=11)]


def _with_meta(episode: Episode, **meta) -> Episode:
    return Episode(episode.arrays, {**episode.meta, **meta})


def _example_times(episode: Episode, examples) -> np.ndarray:
    return np.asarray(episode["t_s"])[examples.row]


def test_related_legs_order():
    assert related_legs(0) == (0, 3, 2, 1)  # FL: RR diagonal, RL same side, FR same axle
    assert related_legs(3) == (3, 0, 1, 2)


def test_examples_are_causal_and_lifted_only(episodes):
    episode = episodes[0]
    examples = episode_examples(episode)
    rows = usable_rows(episode)
    assert examples.count == LEG_COUNT * int(rows.sum())
    assert examples.row.min() >= WINDOW_SAMPLES - 1
    assert np.all(episode["is_lifted"][examples.row])
    channel_count = 4 * len(LEG_CHANNELS) + len(GLOBAL_CHANNELS)
    assert examples.sequences.shape[1:] == (WINDOW_SAMPLES, channel_count)
    assert len(channel_names()) == channel_count
    # The last window sample of leg i is its own lower reading at the row (causal, self first).
    first = 0
    leg, row = examples.leg[first], examples.row[first]
    expected = episode["lower_reading_N"][row, leg] / 1e4
    assert examples.sequences[first, -1, 0] == pytest.approx(expected, rel=1e-6)


def test_events_produce_every_class(episodes):
    examples = build_examples(episodes)
    present = set(np.unique(examples.labels).tolist())
    assert {ContactClass.GROUNDED, ContactClass.UNDER_LOADED, ContactClass.LIFTED} <= present
    assert set(np.unique(examples.weights).tolist()) <= {0.0, 0.5, 1.0}
    assert tabular_features(examples).shape[0] == examples.count


def test_rigid_crawler_liftoff_transient_has_weight_zero(episodes):
    # Synthetic meta has no crawler_contact: rigid (R40-6), lift-off latch at LIFT_S.
    episode = episodes[0]
    assert "crawler_contact" not in episode.meta
    examples = episode_examples(episode)
    times = _example_times(episode, examples)
    in_transient = times <= LIFT_S + LIFTOFF_EXCLUSION_S + 1e-9
    assert in_transient.any() and (~in_transient).any()
    assert np.all(examples.weights[in_transient] == 0.0)
    assert np.all(examples.weights[~in_transient] > 0.0)
    # The row at exactly lift-off + 8 s is still excluded; the next one is not.
    t_s = np.asarray(episode["t_s"])
    excluded = liftoff_transient_rows(episode)
    last = int(np.flatnonzero(excluded)[-1])
    assert t_s[last] == pytest.approx(LIFT_S + LIFTOFF_EXCLUSION_S)
    assert not excluded[last + 1]
    # Weight 0 keeps the examples (labels and evaluation rows are unchanged).
    assert examples.count == LEG_COUNT * int(usable_rows(episode).sum())


@pytest.mark.parametrize(
    ("meta", "is_excluded"),
    [
        ({"crawler_contact": "nsc_rigid"}, True),
        ({"crawler_contact": "nsc_compliant", "crawler_check_passed": None}, True),
        (COMPLIANT_PASSED, False),
    ],
)
def test_liftoff_exclusion_follows_the_crawler_meta(episodes, meta, is_excluded):
    episode = _with_meta(episodes[0], **meta)
    assert liftoff_transient_rows(episode).any() == is_excluded
    weights = episode_examples(episode).weights
    assert (weights == 0.0).any() == is_excluded


def test_episode_that_starts_lifted_has_no_liftoff_transient(episodes):
    # A branch from a READY snapshot took off before its first row.
    episode = episodes[0]
    arrays = dict(episode.arrays)
    arrays["is_lifted"] = np.ones_like(episode["is_lifted"], dtype=bool)
    branched = Episode(arrays, episode.meta)
    assert not liftoff_transient_rows(branched).any()


@dataclass(frozen=True)
class _LabelPrediction:
    probabilities: np.ndarray
    min_force_kN: np.ndarray


def _predict_labels(examples) -> _LabelPrediction:
    """A perfect stand-in model: one-hot truth classes and the true window minimum."""
    return _LabelPrediction(np.eye(3)[examples.labels], examples.target_min_kN.astype(float))


def _episode_with_two_under_loads(meta: dict) -> Episode:
    """Hold episode with a 0.5 s U run on FL at lift-off + 3 s and at lift-off + 20 s."""
    case = SyntheticCase(
        base_id="SYN_E7", episode_id="SYN_E7_ep0", level="top",
        seal_friction_N=np.zeros(LEG_COUNT), event="hold", event_leg=0, sink_m=0.0,
        ramp_s=1.0, floor_roll_deg=0.0, seed=5,
    )
    episode = synthetic_episode(case, duration_s=40.0)
    arrays = dict(episode.arrays)
    t_s = np.asarray(episode["t_s"])
    true_min = np.array(episode["true_force_min_N"], dtype=float)
    for start_s in (LIFT_S + 3.0, LIFT_S + 20.0):
        rows = (t_s >= start_s - 1e-9) & (t_s <= start_s + 0.5 + 1e-9)
        true_min[rows, 0] = 0.5 * F_MIN_N
    arrays["true_force_min_N"] = true_min
    return Episode(arrays, {**episode.meta, **meta})


def _settings_from_meta(episode: Episode) -> ReplaySettings:
    return ReplaySettings.from_controller_meta(episode.meta["controller"], episode.F_min_N)


def test_ml_scores_leave_out_the_liftoff_transient_and_report_it_as_e7():
    # P-S8-4 test (spec 212.10): rigid crawler, U at lift-off + 3 s (left out) and + 20 s.
    episode = _episode_with_two_under_loads({})
    scores = score_set([episode], _predict_labels, _settings_from_meta)
    assert scores.ml.episode_count == 1
    assert scores.combined.episode_count == 1  # same mask for J_C (R42-2)
    assert scores.transient is not None
    assert scores.transient.ml.episode_count == 1
    assert scores.transient.combined.episode_count == 1
    rows = verdict_rows(scores, latency_p99_ms=None, model_bytes=None)
    e1 = next(row for row in rows if row["item"] == "E1")
    assert e1["value"]["episodes"] == 1
    e7 = next(row for row in rows if row["item"] == "E7")
    assert e7["kind"] == "record" and e7["passed"] is None
    assert e7["value"]["ML"]["episodes"] == 1 and e7["value"]["J_C"]["episodes"] == 1
    # P-S8-9: J_C is a decision judge, its ECE is undefined (None) and the note says why.
    assert e7["value"]["ECE"]["J_C"] is None
    assert "J_C deterministic" in e7["note"] and "probability outputs only" in e7["note"]
    # The ECE rows split the examples between E4 and E7.
    total = episode_examples(episode).count
    assert scores.examples + scores.transient.examples == total
    # The control gate I1 keeps the transient (R42-5): both episodes count.
    replay = replay_both(episode, _settings_from_meta(episode))[Judge.COMBINED]
    assert score_judge([record_judgement(episode, replay)], episode.F_min_N).episode_count == 2


def test_compliant_crawler_that_passed_has_no_e7():
    episode = _episode_with_two_under_loads(COMPLIANT_PASSED)
    assert not liftoff_transient_samples(episode).any()
    assert np.array_equal(ml_scored_samples(episode), watched_samples(episode))
    scores = score_set([episode], _predict_labels, _settings_from_meta)
    assert scores.ml.episode_count == 2
    assert scores.transient is None
    rows = verdict_rows(scores, latency_p99_ms=None, model_bytes=None)
    assert "E7" not in [row["item"] for row in rows]


def test_split_keeps_bases_together_and_out_of_distribution_apart(episodes):
    metas = [episode.meta for episode in episodes]
    split = split_by_base(metas, seed=3)
    shares = [split.train, split.validation, split.test, split.ood_level, split.ood_roll]
    flat = [index for share in shares for index in share]
    assert sorted(flat) == list(range(len(episodes)))
    for share in shares:
        bases = {metas[i]["base_id"] for i in share}
        for other in shares:
            if other is not share:
                assert not bases & {metas[i]["base_id"] for i in other}
    assert all(metas[i]["level"] == "middle" for i in split.ood_level)
    assert split == split_by_base(metas, seed=3)


# --- ML environment: training, ONNX export and ONNX-vs-model equality ------------------------

GRU_BATCHES = (1, 4, 7, 300)
PROBABILITY_TOLERANCE = 1e-5
GRU_FORCE_TOLERANCE_KN = 1e-4
LIGHTGBM_FORCE_TOLERANCE_KN = 1e-3
"""float32 sums of ~20 leaf values of order 100 kN in the ONNX trees."""


@pytest.fixture(scope="module")
def trained(episodes):
    pytest.importorskip("torch")
    pytest.importorskip("lightgbm")
    pytest.importorskip("onnxruntime")
    from outrigger_sim.ml.models import GruSettings, LightGbmSettings, train_gru, train_lightgbm

    train = build_examples(episodes[:6])
    validation = build_examples(episodes[6:])
    return {
        "train": train,
        "validation": validation,
        "lightgbm": train_lightgbm(train, validation, LightGbmSettings(rounds=20)),
        "gru": train_gru(train, validation, GruSettings(epochs=2, device="cpu")),
    }


def _assert_same_prediction(original, onnx, force_tolerance_kN: float) -> None:
    np.testing.assert_allclose(onnx.probabilities, original.probabilities, rtol=0.0,
                               atol=PROBABILITY_TOLERANCE)
    np.testing.assert_allclose(onnx.min_force_kN, original.min_force_kN, rtol=0.0,
                               atol=force_tolerance_kN)
    assert np.array_equal(onnx.probabilities.argmax(axis=1),
                          original.probabilities.argmax(axis=1))


def _assert_gru_onnx_matches(trained, path) -> None:
    from outrigger_sim.ml.models import GruOnnxModel

    validation = trained["validation"]
    onnx_model = GruOnnxModel(path)
    for batch in GRU_BATCHES:
        rows = validation.subset(np.arange(validation.count) < batch)
        _assert_same_prediction(trained["gru"].predict(rows), onnx_model.predict(rows),
                                GRU_FORCE_TOLERANCE_KN)


def test_gru_onnx_dynamo_export_matches_torch(trained, tmp_path):
    pytest.importorskip("onnxscript")
    from outrigger_sim.ml.models import export_gru_onnx

    export = export_gru_onnx(trained["gru"], trained["train"], tmp_path / "gru.onnx")
    assert export.exporter == "dynamo"
    assert export.fallback_reason is None
    _assert_gru_onnx_matches(trained, export.paths[0])


def test_gru_onnx_falls_back_to_torchscript(trained, tmp_path, monkeypatch):
    from outrigger_sim.ml import models

    def failing_dynamo_export(*_args):
        raise RuntimeError("dynamo unavailable in this test")

    monkeypatch.setattr(models, "_export_gru_dynamo", failing_dynamo_export)
    export = models.export_gru_onnx(trained["gru"], trained["train"], tmp_path / "gru.onnx")
    assert export.exporter == "torchscript"
    assert export.fallback_reason == "RuntimeError: dynamo unavailable in this test"
    _assert_gru_onnx_matches(trained, export.paths[0])


def test_float32_thresholds_keep_every_booster_decision(trained):
    from outrigger_sim.ml.models import _booster_with_float32_thresholds

    features = tabular_features(trained["validation"])
    for booster in (trained["lightgbm"].classifier, trained["lightgbm"].regressor):
        rounded = _booster_with_float32_thresholds(booster)
        assert np.array_equal(rounded.predict(features), booster.predict(features))


def test_lightgbm_onnx_export_matches_booster(trained, tmp_path):
    pytest.importorskip("onnxmltools")
    from outrigger_sim.ml.models import (
        LightGbmOnnxModel,
        export_lightgbm_onnx,
        lightgbm_onnx_latency,
    )

    export = export_lightgbm_onnx(trained["lightgbm"], tmp_path)
    assert export.exporter == "onnxmltools"
    assert [path.name for path in export.paths] == ["lgbm_classifier.onnx",
                                                     "lgbm_regressor.onnx"]
    validation = trained["validation"]
    _assert_same_prediction(trained["lightgbm"].predict(validation),
                            LightGbmOnnxModel(export).predict(validation),
                            LIGHTGBM_FORCE_TOLERANCE_KN)
    latency = lightgbm_onnx_latency(export, validation, calls=20)
    assert latency.p99_ms > 0.0
    assert latency.model_bytes == export.model_bytes


def test_training_export_and_scoring_run_end_to_end(episodes, trained, tmp_path):
    from outrigger_sim.ml.models import export_gru_onnx, onnx_latency

    export = export_gru_onnx(trained["gru"], trained["train"], tmp_path / "gru.onnx")
    latency = onnx_latency(export.paths[0], trained["validation"], calls=50)
    assert latency.p99_ms > 0.0

    def settings_for(episode):
        return ReplaySettings.from_controller_meta(episode.meta["controller"], episode.F_min_N)

    for model in (trained["lightgbm"], trained["gru"]):
        scores = score_set(episodes[6:], model.predict, settings_for)
        rows = verdict_rows(scores, latency.p99_ms, latency.model_bytes)
        # Rigid-crawler synthetic runs: the lift-off transient is the E7 record row (R42-4).
        assert [row["item"] for row in rows] == ["E1", "E2", "E3", "E4", "E5", "E7"]
        assert scores.combined.episode_count == scores.ml.episode_count
