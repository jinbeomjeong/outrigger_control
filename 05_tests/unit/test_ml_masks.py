"""ML masks of ``verify_S8ML.json`` in ``ml.dataset`` / ``ml.evaluate`` (C-S8-27 ④, spec rev. 48
218.13 ④): rows from the FAULT entry to the run end are no training examples and are scored by
neither judge. numpy only (synthetic episodes)."""

from __future__ import annotations

import json

import numpy as np
import pytest

from outrigger_sim.contact_episode import LEG_COUNT, Episode
from outrigger_sim.control.contact_replay import ReplaySettings
from outrigger_sim.ml.dataset import (
    MlMask,
    build_examples,
    episode_examples,
    load_ml_masks,
    masked_rows,
)
from outrigger_sim.ml.evaluate import ml_scored_samples, score_set
from outrigger_sim.ml.synthetic import F_MIN_N, LIFT_S, SyntheticCase, synthetic_episode

FAULT_S = LIFT_S + 20.0


def _episode() -> Episode:
    """Hold episode with a 0.5 s U run on FL at lift-off + 12 s and at lift-off + 25 s (the
    second after the FAULT entry of the mask)."""
    case = SyntheticCase(
        base_id="SYN_M", episode_id="SYN_M_ep0", level="top",
        seal_friction_N=np.zeros(LEG_COUNT), event="hold", event_leg=0, sink_m=0.0,
        ramp_s=1.0, floor_roll_deg=0.0, seed=5,
    )
    episode = synthetic_episode(case, duration_s=40.0)
    arrays = dict(episode.arrays)
    t_s = np.asarray(episode["t_s"])
    true_min = np.array(episode["true_force_min_N"], dtype=float)
    for start_s in (LIFT_S + 12.0, LIFT_S + 25.0):
        rows = (t_s >= start_s - 1e-9) & (t_s <= start_s + 0.5 + 1e-9)
        true_min[rows, 0] = 0.5 * F_MIN_N
    arrays["true_force_min_N"] = true_min
    return Episode(arrays, {**episode.meta, "crawler_contact": "nsc_compliant",
                            "crawler_check_passed": True})


def _masks(episode: Episode) -> dict[str, MlMask]:
    end_s = float(np.asarray(episode["t_s"])[-1])
    return {"SYN_M_ep0": MlMask(FAULT_S, end_s, ("fault",))}


def test_load_ml_masks_reads_the_engine_times(tmp_path) -> None:
    path = tmp_path / "verify_S8ML.json"
    path.write_text(json.dumps({"ml_masks": {"ML10_ep4": {
        "start_s": 62.0, "end_s": 89.0, "start_engine_s": 65.0, "end_engine_s": 92.0,
        "reasons": ["fault"], "fault_t_s": 62.0, "rule": "C-S8-27"}}}), encoding="utf-8")
    assert load_ml_masks(path) == {"ML10_ep4": MlMask(65.0, 92.0, ("fault",))}
    path.write_text(json.dumps({"rows": []}), encoding="utf-8")
    assert load_ml_masks(path) == {}


def test_masked_rows_follow_the_episode_id() -> None:
    episode = _episode()
    rows = masked_rows(episode, _masks(episode))
    t_s = np.asarray(episode["t_s"])
    np.testing.assert_array_equal(rows, t_s >= FAULT_S - 1e-6)
    assert not masked_rows(episode, {"other": MlMask(0.0, 1e9)}).any()
    assert not masked_rows(episode, None).any()


def test_masked_rows_are_no_examples() -> None:
    episode = _episode()
    masks = _masks(episode)
    examples = episode_examples(episode, masks=masks)
    times = np.asarray(episode["t_s"])[examples.row]
    assert examples.count > 0 and np.all(times < FAULT_S)
    unmasked = build_examples([episode])
    assert build_examples([episode], masks=masks).count == examples.count < unmasked.count


def _predict_labels(examples):
    class Prediction:
        probabilities = np.eye(3)[examples.labels]
        min_force_kN = examples.target_min_kN.astype(float)
    return Prediction()


def _settings(episode: Episode) -> ReplaySettings:
    return ReplaySettings.from_controller_meta(episode.meta["controller"], episode.F_min_N)


def test_masked_samples_are_scored_by_neither_judge() -> None:
    episode = _episode()
    masks = _masks(episode)
    assert not (ml_scored_samples(episode, masks) & masked_rows(episode, masks)).any()
    unmasked = score_set([episode], _predict_labels, _settings)
    masked = score_set([episode], _predict_labels, _settings, masks)
    assert unmasked.ml.episode_count == unmasked.combined.episode_count == 2
    assert masked.ml.episode_count == masked.combined.episode_count == 1
    assert masked.examples < unmasked.examples


@pytest.mark.parametrize("name", ["start_engine_s", "end_engine_s"])
def test_entry_without_engine_times_is_rejected(tmp_path, name) -> None:
    entry = {"start_engine_s": 1.0, "end_engine_s": 2.0}
    del entry[name]
    path = tmp_path / "verify_S8ML.json"
    path.write_text(json.dumps({"ml_masks": {"A": entry}}), encoding="utf-8")
    with pytest.raises(KeyError):
        load_ml_masks(path)
