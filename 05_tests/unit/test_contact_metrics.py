"""Truth classes and M1-M4 of the contact-judge comparison (spec rev. 39 203.1 / 203.3)."""

from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

from outrigger_sim.verify.contact_metrics import (
    ContactClass,
    RecordJudgement,
    boundary_mask,
    clopper_pearson_upper,
    contact_episodes,
    expected_calibration_error,
    false_action_flags,
    near_fmin_errors_N,
    score_judge,
    truth_classes,
)

F_MIN_N = 9414.59
ROD_WEIGHT_N = np.array([1047.2, 1047.2, 717.7, 717.7])
G, U, L = ContactClass.GROUNDED, ContactClass.UNDER_LOADED, ContactClass.LIFTED


def test_truth_classes_use_the_rod_weight_for_lift():
    forces = np.array([[50e3, F_MIN_N - 1.0, -1047.2 + 500.0, np.nan]])
    assert truth_classes(forces, ROD_WEIGHT_N, F_MIN_N).tolist() == [[G, U, L, -1]]
    just_above = np.array([[50e3, 50e3, 50e3, -717.7 + 501.0]])
    assert truth_classes(just_above, ROD_WEIGHT_N, F_MIN_N)[0, 3] == U


def test_boundary_marks_both_sides_and_episodes_join_u_and_l():
    classes = np.full((8, 4), G)
    classes[2:6, 1] = [U, L, L, U]
    boundary = boundary_mask(classes)
    assert np.flatnonzero(boundary[:, 1]).tolist() == [1, 2, 3, 4, 5, 6]
    episodes = contact_episodes(classes)
    assert [(e.leg, e.on_row, e.off_row, e.is_lift) for e in episodes] == [(1, 2, 5, True)]


@pytest.mark.parametrize(("failures", "trials"), [(0, 75), (0, 300), (2, 40), (5, 5)])
def test_clopper_pearson_upper(failures, trials):
    upper = clopper_pearson_upper(failures, trials)
    if failures == 0:
        assert upper == pytest.approx(1.0 - 0.05 ** (1.0 / trials), rel=1e-9)
    if failures == trials:
        assert upper == 1.0
    scipy_stats = pytest.importorskip("scipy.stats")
    if failures < trials:
        assert upper == pytest.approx(scipy_stats.beta.ppf(0.95, failures + 1, trials - failures),
                                      rel=1e-7)


def test_spec_value_zero_in_75_is_3_9_percent():
    assert clopper_pearson_upper(0, 75) == pytest.approx(0.039, abs=5e-4)


def judgement(classes, decision, action, *, true_min=None) -> RecordJudgement:
    count = classes.shape[0]
    true_min = np.full((count, 4), 50e3) if true_min is None else true_min
    return RecordJudgement(
        t_s=(np.arange(count) + 1) * 0.1,
        classes=classes,
        decision_flags=decision,
        action_flags=action,
        estimate_N=np.full((count, 4), 50e3),
        true_force_N=true_min,
        true_force_min_N=true_min,
        watched=np.ones(count, dtype=bool),
    )


def test_score_counts_missed_late_and_delay():
    classes = np.full((40, 4), G)
    classes[5:10, 0] = U  # episode A: decided late (0.4 s after t_on), acted early
    classes[20:25, 2] = L  # episode B: never decided, no action
    decision = np.zeros((40, 4), dtype=bool)
    decision[9, 0] = True
    action = np.zeros((40, 4), dtype=bool)
    action[3, 0] = True
    score = score_judge([judgement(classes, decision, action)], F_MIN_N)
    assert (score.episode_count, score.missed, score.late) == (2, 1, 1)
    assert score.action_delays_s == pytest.approx((-0.2,))
    assert score.missed_upper_95 == pytest.approx(clopper_pearson_upper(1, 2))


def test_false_action_flag_needs_two_seconds_of_high_truth():
    t_s = (np.arange(40) + 1) * 0.1
    action = np.zeros((40, 4), dtype=bool)
    action[[5, 30], 1] = True
    truth = np.full((40, 4), 30e3)
    assert false_action_flags(t_s, action, truth, F_MIN_N) == 2
    truth[12, 1] = F_MIN_N  # drops within 2 s after the first flag: a true alarm
    assert false_action_flags(t_s, action, truth, F_MIN_N) == 1


def test_near_fmin_errors_skip_far_and_missing_samples():
    truth = np.array([F_MIN_N, F_MIN_N + 20e3, F_MIN_N - 4e3, F_MIN_N])
    estimate = np.array([F_MIN_N + 300.0, 0.0, F_MIN_N - 4e3, np.nan])
    assert near_fmin_errors_N(estimate, truth, F_MIN_N).tolist() == pytest.approx([300.0, 0.0])


def test_expected_calibration_error():
    probabilities = np.array([0.1, 0.1, 0.9, 0.9])
    perfect = np.array([False, False, True, True])
    assert expected_calibration_error(probabilities, perfect) == pytest.approx(0.1)
    assert expected_calibration_error(np.array([0.5, 0.5]), np.array([True, False])) == 0.0
    assert math.isclose(expected_calibration_error(np.zeros(0), np.zeros(0, bool)), 0.0)


def test_scored_mask_counts_episodes_by_t_on_with_their_full_extent():
    # Spec 212.7 R42-3: rows 0-9 are left out (lift-off transient). Episode A starts there and
    # is not counted; episode B starts in the scored part and keeps its decision flag at row 25.
    classes = np.full((40, 4), G)
    classes[5:15, 0] = U  # A: t_on in the left-out rows, runs past them
    classes[20:30, 1] = U  # B: scored
    decision = np.zeros((40, 4), dtype=bool)
    decision[25, 1] = True
    action = np.zeros((40, 4), dtype=bool)
    record = judgement(classes, decision, action)
    scored = np.arange(40) >= 10
    assert score_judge([record], F_MIN_N).episode_count == 2
    masked = score_judge([dataclasses.replace(record, scored=scored)], F_MIN_N)
    assert (masked.episode_count, masked.missed, masked.late) == (1, 0, 1)
    assert masked.watched_hours == pytest.approx(30 * 0.1 / 3600.0)
    left_out = score_judge([dataclasses.replace(record, scored=~scored)], F_MIN_N)
    assert (left_out.episode_count, left_out.missed) == (1, 1)
