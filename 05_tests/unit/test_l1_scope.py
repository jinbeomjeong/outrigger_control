"""M4 fast lift-off windows (``verify/l1_scope``, dynamics_model.md 5.15.2) on synthetic
pad records: event detection, window end, held quantities, closed-form report, and the
untouched path of cases without the inputs."""

from __future__ import annotations

import numpy as np
import pytest

from outrigger_sim.hydraulics.rod_chamber import RodChamberMode
from outrigger_sim.params import load_params
from outrigger_sim.verify import l1_scope

SAMPLE_S = 1.0e-3
LIFT_SAMPLE = 100
LOCK, FLOOR, LIFT, RET = (int(RodChamberMode.LOCK), int(RodChamberMode.FLOOR),
                          int(RodChamberMode.LIFT), int(RodChamberMode.RET))


@pytest.fixture(scope="module")
def legs():
    return l1_scope.rod_oil_legs_from_params(load_params(level="top"))


def _synthetic_modes(samples: int = 200) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """FL slow lift (control motion), FR lift from RET (moving), RL fast lift with re-contact
    after 10 ms, RR fast lift (RE1b-F) staying lifted."""
    t = 50.0 + SAMPLE_S * np.arange(samples)
    mode = np.full((samples, 4), LOCK)
    speed = np.zeros((samples, 4))
    mode[LIFT_SAMPLE:, 0] = LIFT
    speed[:, 0] = 1.0e-3
    mode[:LIFT_SAMPLE, 1] = RET
    mode[LIFT_SAMPLE:, 1] = LIFT
    speed[:, 1] = 0.5
    mode[LIFT_SAMPLE - 5:LIFT_SAMPLE, 2] = FLOOR
    mode[LIFT_SAMPLE:LIFT_SAMPLE + 10, 2] = LIFT
    speed[:, 2] = 0.3
    mode[LIFT_SAMPLE:, 3] = LIFT
    speed[:, 3] = 0.580
    return t, mode, speed


def test_threshold_from_the_yaml(legs) -> None:
    thresholds = [leg.separation_threshold_m_s for leg in legs]
    assert thresholds[0] == pytest.approx(0.0153, abs=1e-4)
    assert thresholds[3] == pytest.approx(0.0212, abs=1e-4)
    assert legs[3].mode_frequency_Hz == pytest.approx(102.4, abs=0.1)


def test_detects_fast_lifts_from_lock_or_floor_only(legs) -> None:
    t, mode, speed = _synthetic_modes()
    windows = l1_scope.detect_scope_windows(t, mode, speed, legs)
    assert [w.leg for w in windows] == ["RL", "RR"]
    rl, rr = windows
    assert rl.t_from_s == t[LIFT_SAMPLE]
    assert rl.ended_by_recontact and rl.t_to_s == t[LIFT_SAMPLE + 10]
    assert not rr.ended_by_recontact
    assert rr.t_to_s == pytest.approx(t[LIFT_SAMPLE] + l1_scope.WINDOW_S, abs=1e-12)
    assert rr.to_meta()["reason"] == l1_scope.REASON


def test_held_samples_hide_the_window_only(legs) -> None:
    t, mode, speed = _synthetic_modes()
    windows = l1_scope.detect_scope_windows(t, mode, speed, legs)
    force = np.full((len(t), 4), 70.0e3)
    force[LIFT_SAMPLE:LIFT_SAMPLE + 5, 3] = -18.0e3  # model transient inside the RR window
    force[LIFT_SAMPLE + 5:, 3] = -0.7e3
    mask = l1_scope.exclusion_mask(t, windows)
    held = l1_scope.hold_excluded(force, mask)
    np.testing.assert_array_equal(held[~mask], force[~mask])
    assert np.all(held[mask[:, 3], 3] == force[LIFT_SAMPLE - 1, 3])
    assert held[:, 3].min() == force[~mask[:, 3], 3].min()


def test_closed_form_matches_the_re1bf_example(legs) -> None:
    window = l1_scope.ScopeWindow(3, 1.0, 1.03, 0.580, False)
    report = l1_scope.closed_form_report(window, legs[3], 67.4e5, 21.0e5)
    by_zeta = {row["zeta"]: row for row in report["estimates"]}
    assert by_zeta[0.1]["F_ten_N"] == pytest.approx(-23.6e3, rel=0.01)
    assert by_zeta[0.1]["p_r_max_Pa"] - 67.4e5 == pytest.approx(21.7e5, rel=0.01)
    assert 21.0e5 - by_zeta[0.1]["p_h_min_Pa"] == pytest.approx(17.7e5, rel=0.01)
    assert by_zeta[0.1]["pad_acceleration_m_s2"] == pytest.approx(320.0, rel=0.03)
    assert by_zeta[0.0]["F_ten_N"] == pytest.approx(-0.580 * legs[3].impedance_N_s_m)
    assert report["first_trough_t"] - 1.0 == pytest.approx(2.44e-3, abs=0.05e-3)


def _case(t, mode=None, speed=None) -> dict:
    force = np.full((len(t), 4), 70.0e3)
    force[LIFT_SAMPLE:LIFT_SAMPLE + 5, 3] = -18.0e3
    pads = {"t": t, "F_cyl": force, "F_cyl_min_interval": force.copy(), "N": force.copy()}
    rec_t = t[::20]
    rec = {"t": rec_t, "F_cyl": force[::20].copy(), "body_pos": np.zeros((len(rec_t), 3))}
    case = {"result": {"settings": {"start_t_s": 50.0}}, "pads": pads, "rec": rec}
    if mode is not None:  # settle_velocity.npz: up-positive normal speeds, v_rel = ball - patch
        case[l1_scope.CASE_KEY] = {
            "t": t, "mode": mode.astype(np.int8),
            "v_ball_n": np.zeros_like(speed), "v_patch_n": -speed,
        }
    return case


def test_separation_speed_sign() -> None:
    velocity = {"v_ball_n": np.array([[-0.01]]), "v_patch_n": np.array([[-0.59]])}
    assert l1_scope.separation_speed_m_s(velocity)[0, 0] == pytest.approx(0.58)


def test_case_without_inputs_or_events_is_untouched() -> None:
    params = load_params(level="top")
    t, mode, _speed = _synthetic_modes()
    plain = _case(t)
    assert l1_scope.apply_to_case(plain, params) == (plain, None)
    slow = _case(t, mode, np.full((len(t), 4), 1.0e-3))
    same, scope = l1_scope.apply_to_case(slow, params)
    assert same is slow and scope is None


def test_case_with_an_event_is_held_and_reported() -> None:
    params = load_params(level="top")
    t, mode, speed = _synthetic_modes()
    case = _case(t, mode, speed)
    held, scope = l1_scope.apply_to_case(case, params)
    assert [e["leg"] for e in scope["outside_L1_scope"]] == ["RL", "RR"]
    assert scope["outside_L1_scope"][1]["t_from"] == pytest.approx(LIFT_SAMPLE * SAMPLE_S)
    assert held["pads"]["F_cyl_min_interval"][:, 3].min() == 70.0e3
    np.testing.assert_array_equal(held["pads"]["N"], case["pads"]["N"])  # not an excluded key
    np.testing.assert_array_equal(case["pads"]["F_cyl"][LIFT_SAMPLE, 3], -18.0e3)  # input kept
    sanity_rr = scope["sanity_M1"][1]
    assert sanity_rr["min_F_cyl_N"] == -18.0e3 and sanity_rr["passed"] is False
