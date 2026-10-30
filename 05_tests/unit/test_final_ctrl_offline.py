"""E3 reuse check of ``final_ctrl_offline.py`` (control spec 432.4, final controller 429.11).

Synthetic 10 Hz records cover the four feature checks (SGS any_loc, R4c30, L1gs, DSb75), the
two replays (LOC revocation watch, differential-sinkage trigger) and the case class. The replay
timing follows ``C2Controller``: the L1gs watch includes the LOC period, the DSb75 trigger is
judged from the period after the first LOC up to the first DONE.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "04_scripts" / "03_control" / "s9"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import final_ctrl_offline as src  # noqa: E402

PERIOD_S = 0.1
WEIGHT_N = 390_000.0
REFERENCE_WEIGHT_N = 376_583.6
LOC_S = 1.0
SAMPLES = 60


@pytest.fixture(scope="module")
def settings() -> src.FinalSettings:
    return src.final_settings()


def _times(samples: int = SAMPLES) -> np.ndarray:
    return np.round(np.arange(samples) * PERIOD_S, 10)


def _level_phases(samples: int = SAMPLES) -> np.ndarray:
    return np.full(samples, src.LEVEL_PHASE)


def _facts(
    *,
    soil_mode_s: float | None = None,
    clearance_at_P_m: float = 0.003,
    tilt_deg: float = 0.15,
    loc_times_s: tuple[float, ...] = (LOC_S,),
) -> src.LocFacts:
    return src.LocFacts(
        loc_times_s=loc_times_s,
        soil_mode_start_s=soil_mode_s,
        plateau_start_s=LOC_S - 0.5,
        clearance_at_P_m=clearance_at_P_m,
        settle_tilt_rad=math.radians(tilt_deg),
        weight_estimate_N=WEIGHT_N,
        reference_weight_N=REFERENCE_WEIGHT_N,
    )


def _record(
    facts: src.LocFacts,
    *,
    stroke_m: float | np.ndarray = 0.45,
    events: list[tuple[float, str]] | None = None,
    controller_meta: dict | None = None,
) -> src.CaseRecord:
    """Flat LEVEL record: constant strokes and pressures that sum to ``W_hat``."""
    t_s = _times()
    strokes = np.broadcast_to(np.asarray(stroke_m, dtype=float), (SAMPLES, 4)).copy()
    head_Pa = np.full((SAMPLES, 4), WEIGHT_N / 4) / np.array([0.0133, 0.0133, 0.0095, 0.0095])
    return src.CaseRecord(
        case_dir=Path("synthetic"),
        result={"phases": [{"t_s": 0.0, "phase": src.LEVEL_PHASE}]},
        events=events or [(LOC_S, src.SOIL_EVENT_LIFTOFF_CONFIRMED)],
        controller_meta=controller_meta or {},
        facts=facts,
        t_s=t_s,
        phase=_level_phases(),
        stroke_m=strokes,
        gyro_roll_rad_s=np.zeros(SAMPLES),
        head_pressure_Pa=head_Pa,
        rod_pressure_Pa=np.zeros((SAMPLES, 4)),
    )


def test_final_settings_match_spec(settings: src.FinalSettings) -> None:
    assert settings.guard_stroke_m == pytest.approx(0.6828)
    assert settings.guard_lookahead_s == pytest.approx(0.2)
    assert settings.slope_tilt_min_rad == pytest.approx(math.radians(1.0))
    assert settings.revoke_stroke_limit_m == pytest.approx(0.6428)
    assert settings.revoke_confirm_periods == 2
    assert settings.sink_threshold_m_s == pytest.approx(0.003)
    assert settings.sink_confirm_periods == 10
    assert settings.sink_track_w_m == pytest.approx((2.648, 2.411))


# --- L1gs replay ---


def _stepped_load(step_N: float, step_s: float = 2.0) -> np.ndarray:
    return np.where(_times() >= step_s - 1e-9, WEIGHT_N + step_N, WEIGHT_N)


def test_revoke_replay_fires_on_second_period_above(settings: src.FinalSettings) -> None:
    # 1 s mean of a 3 kN step passes 2 kN with 7 high samples (t 2.6 s); the second period
    # above confirms at 2.7 s.
    strokes = np.full((SAMPLES, 4), 0.45)
    replay = src.replay_loc_revoke(
        _times(),
        _level_phases(),
        strokes,
        _stepped_load(3000.0),
        LOC_S,
        WEIGHT_N,
        REFERENCE_WEIGHT_N,
        settings,
    )
    assert replay.kind == "REVOKE"
    assert replay.fired_t_s == pytest.approx(2.7)


def test_revoke_replay_skips_near_the_guard_stroke(settings: src.FinalSettings) -> None:
    strokes = np.full((SAMPLES, 4), 0.45)
    strokes[:, 2] = 0.65  # above s_g - 40 mm = 0.6428 m
    replay = src.replay_loc_revoke(
        _times(),
        _level_phases(),
        strokes,
        _stepped_load(3000.0),
        LOC_S,
        WEIGHT_N,
        REFERENCE_WEIGHT_N,
        settings,
    )
    assert replay.kind == "SKIP"


def test_revoke_replay_ends_after_the_watch_stroke(settings: src.FinalSettings) -> None:
    strokes = np.full((SAMPLES, 4), 0.45) + np.clip(_times() - LOC_S, 0.0, None)[:, None] * 0.02
    replay = src.replay_loc_revoke(
        _times(),
        _level_phases(),
        strokes,
        _stepped_load(3000.0),
        LOC_S,
        WEIGHT_N,
        REFERENCE_WEIGHT_N,
        settings,
    )
    assert replay.kind is None
    assert replay.end_reason.startswith("stroke +watch")


def test_revoke_replay_keeps_a_small_rise(settings: src.FinalSettings) -> None:
    strokes = np.full((SAMPLES, 4), 0.45)
    replay = src.replay_loc_revoke(
        _times(),
        _level_phases(),
        strokes,
        _stepped_load(1500.0),
        LOC_S,
        WEIGHT_N,
        REFERENCE_WEIGHT_N,
        settings,
    )
    assert replay.kind is None
    assert replay.peak_rise_N == pytest.approx(1500.0)


# --- DSb75 replay ---


def _sinking_front_left(rate_m_s: float) -> np.ndarray:
    strokes = np.full((SAMPLES, 4), 0.45)
    strokes[:, 0] += rate_m_s * _times()
    return strokes


def test_sink_replay_holds_after_one_second_above(settings: src.FinalSettings) -> None:
    # Evaluation starts at 1.1 s (period after the LOC); ten periods above -> hold at 2.0 s.
    replay = src.replay_diff_sink(
        _times(), _level_phases(), _sinking_front_left(0.004), np.zeros(SAMPLES), LOC_S, settings
    )
    assert replay.hold_t_s == pytest.approx(2.0)
    assert replay.rate_at_hold_m_s == pytest.approx(0.004)


def test_sink_replay_ignores_a_slow_rate(settings: src.FinalSettings) -> None:
    replay = src.replay_diff_sink(
        _times(), _level_phases(), _sinking_front_left(0.002), np.zeros(SAMPLES), LOC_S, settings
    )
    assert replay.hold_t_s is None
    assert replay.max_rate_m_s == pytest.approx(0.002)


def test_sink_replay_removes_the_body_roll(settings: src.FinalSettings) -> None:
    roll_rate = 0.004 / settings.sink_track_w_m[0]
    strokes = _sinking_front_left(0.004)
    strokes[:, 2] += 0.004 * settings.sink_track_w_m[1] / settings.sink_track_w_m[0] * _times()
    replay = src.replay_diff_sink(
        _times(), _level_phases(), strokes, np.full(SAMPLES, roll_rate), LOC_S, settings
    )
    assert replay.hold_t_s is None


def test_sink_replay_stops_at_the_first_done(settings: src.FinalSettings) -> None:
    phases = _level_phases()
    phases[_times() >= 1.5 - 1e-9] = src.DONE_PHASE
    replay = src.replay_diff_sink(
        _times(), phases, _sinking_front_left(0.004), np.zeros(SAMPLES), LOC_S, settings
    )
    assert replay.hold_t_s is None


def test_sink_replay_holds_off_near_the_guard_stroke(settings: src.FinalSettings) -> None:
    strokes = _sinking_front_left(0.004)
    strokes[:, 3] = 0.66
    replay = src.replay_diff_sink(
        _times(), _level_phases(), strokes, np.zeros(SAMPLES), LOC_S, settings
    )
    assert replay.hold_t_s is None


# --- feature checks ---


def test_r4_fires_on_flat_soil_mode_loc(settings: src.FinalSettings) -> None:
    check = src.check_r4(_record(_facts(soil_mode_s=0.5, tilt_deg=0.1)), settings)
    assert check.fires is True
    assert check.values["due_at_loc_s"] == [LOC_S]


def test_r4_waits_for_the_soil_mode(settings: src.FinalSettings) -> None:
    assert src.check_r4(_record(_facts(soil_mode_s=None)), settings).fires is False
    late = _facts(soil_mode_s=LOC_S + 0.5)  # soil mode after the LOC: not used at the LOC
    assert src.check_r4(_record(late), settings).fires is False


def test_r4_yields_to_p31_by_its_conditions(settings: src.FinalSettings) -> None:
    tilted = _facts(soil_mode_s=0.5, clearance_at_P_m=0.05, tilt_deg=2.0)
    check = src.check_r4(_record(tilted), settings)
    assert check.fires is False
    assert check.values["p31_applied_at_loc"] == [True]


def test_r4_yields_to_a_recorded_p31(settings: src.FinalSettings) -> None:
    events = [(LOC_S, src.SOIL_EVENT_LIFTOFF_CONFIRMED), (LOC_S, f"{src.SLOPE_MARGIN_EVENT}:80")]
    record = _record(_facts(soil_mode_s=0.5, tilt_deg=0.1), events=events)
    assert src.check_r4(record, settings).fires is False


def test_sgs_uses_the_recorded_guard_periods(settings: src.FinalSettings) -> None:
    meta = {"lift_stroke_guard": {"periods": 3}}
    check = src.check_sgs(_record(_facts(), controller_meta=meta), settings)
    assert check.fires is True
    assert check.confidence == "high"


def test_sgs_stroke_bound_without_the_guard(settings: src.FinalSettings) -> None:
    assert src.check_sgs(_record(_facts(), stroke_m=0.50), settings).fires is False
    unsure = src.check_sgs(_record(_facts(), stroke_m=0.68), settings)
    assert unsure.fires is None
    assert unsure.confidence == "low"


def test_l1gs_gate_closed_without_soil_sign(settings: src.FinalSettings) -> None:
    check = src.check_l1gs(_record(_facts()), settings)
    assert check.fires is False
    assert check.values["soil_sign"] is None


def test_l1gs_recorded_revocation_decides(settings: src.FinalSettings) -> None:
    meta = {"loc_revoke": {"settings": {"enable": True}, "revokes": 1, "t_skip_s": []}}
    check = src.check_l1gs(_record(_facts(soil_mode_s=0.5), controller_meta=meta), settings)
    assert check.fires is True
    assert check.basis == "rule in the recorded run"


def test_dsb_gate_closed_on_a_tilted_settle(settings: src.FinalSettings) -> None:
    tilted = _facts(clearance_at_P_m=0.02, tilt_deg=3.0)  # soil sign by clearance and tilt
    record = _record(tilted, stroke_m=0.45)
    record.stroke_m = _sinking_front_left(0.004)
    check = src.check_dsb(record, settings)
    assert check.values["soil_sign"] == "clearance_tilt"
    assert check.fires is False
    assert check.values["replay"]["hold_t_s"] is not None  # would fire if the gate were open


def test_classify_rules() -> None:
    off = src.FeatureCheck(False, "high", "")
    assert src.classify({"a": off, "b": off}) == src.CLASS_REUSE
    assert src.classify({"a": off, "b": src.FeatureCheck(True, "high", "")}) == src.CLASS_RERUN
    assert src.classify({"a": off, "b": src.FeatureCheck(None, "low", "")}) == src.CLASS_UNDECIDED


# --- case folders ---


def _write_case(case_dir: Path, *, with_controller: bool) -> None:
    case_dir.mkdir(parents=True)
    result: dict = {"action": "level" if with_controller else "p3a", "events": [], "phases": []}
    if with_controller:
        result["phases"] = [{"t_s": 0.0, "phase": "level"}, {"t_s": 4.0, "phase": "done"}]
        result["events"] = [{"t_s": LOC_S, "name": src.SOIL_EVENT_LIFTOFF_CONFIRMED}]
        result["c2_soil"] = {
            "t_P_s": 0.5,
            "clearance_at_P_m": 0.002,
            "settle_attitude_rad": [0.0, 0.0026],
            "W_hat_N": WEIGHT_N,
            "W_ref_N": REFERENCE_WEIGHT_N,
            "soil_mode_t_s": None,
        }
        (case_dir / "record").mkdir()
        np.savez(
            case_dir / "record" / "record.npz",
            **{
                "t": _times(),
                "meas.stroke": np.full((SAMPLES, 4), 0.45),
                "meas.angular_rate": np.zeros((SAMPLES, 3)),
                "meas.head_pressure": np.full((SAMPLES, 4), 7.0e6),
                "meas.rod_pressure": np.zeros((SAMPLES, 4)),
            },
        )
    (case_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")


def test_judge_case_reuses_a_rigid_like_record(tmp_path: Path, settings: src.FinalSettings) -> None:
    case_dir = tmp_path / "batch_X" / "G1_case"
    _write_case(case_dir, with_controller=True)
    row = src.judge_case(case_dir, settings)
    assert row["class"] == src.CLASS_REUSE
    assert row["confidence"] == "high"
    assert row["loc"]["times_s"] == [LOC_S]


def test_judge_case_open_loop_record(tmp_path: Path, settings: src.FinalSettings) -> None:
    case_dir = tmp_path / "batch_P3a" / "P3a_case"
    _write_case(case_dir, with_controller=False)
    row = src.judge_case(case_dir, settings)
    assert row["class"] == src.CLASS_REUSE
    assert all(check["fires"] is False for check in row["checks"].values())
