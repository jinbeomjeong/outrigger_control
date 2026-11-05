"""v5 options of the Chrono runners (spec ``v5_hydraulic_impl_spec.md`` 2.2, V-1, V-2, B-6 rows)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.actuation import SpeedReference
from outrigger_sim.hydraulics.v5_options import (
    CheckDelaySetting,
    HydraulicOptions,
    LockClosureSetting,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHRONO_SCRIPTS = PROJECT_ROOT / "04_scripts" / "02_chrono"
V_MAX = 0.020924
DT_S = 1.0e-4
V5_KEYS = {"valve_tau_s", "rod_release_force", "check_delay", "check_delay_volume_scale",
           "check_delay_cv", "lock_overlap_ratio", "lock_closing_delay_s",
           "lock_window_follows_plant"}


def test_v1_valve_step_response_at_tau() -> None:
    """Spec V-1: tau_v 0.1 s, step to v_max: at 0.1 s u / v_max 0.632, s_ref 0.770 mm."""
    reference = SpeedReference([0.0] * 4, [(0.0, 0.7)] * 4, max_speed_m_s=V_MAX, ramp_s=0.1)
    reference.configure_valve(tau_s=0.1, amp_ramp="none")
    reference.set_command([V_MAX] * 4)
    for k in range(round(0.1 / DT_S)):
        reference.advance(DT_S, t_s=k * DT_S)
    assert reference.valve_state_m_s[0] / V_MAX == pytest.approx(0.632, abs=0.0005)
    assert reference.s_ref_m[0] * 1e3 == pytest.approx(0.770, abs=0.0005)


@pytest.fixture(scope="module")
def run_s9():
    pytest.importorskip("pychrono")
    sys.path.insert(0, str(CHRONO_SCRIPTS))
    try:
        import run_S9
    finally:
        sys.path.remove(str(CHRONO_SCRIPTS))
    return run_S9


def test_v2_run_s9_without_options_has_no_keys_and_no_options(run_s9) -> None:
    """Spec V-2: no option = no args key, no v5 block (the valve stays off, the ramp on)."""
    args = run_s9.build_parser().parse_args(
        ["level", "--soil", "J1", "--case", "x", "--out-root", "x"])
    assert not V5_KEYS & set(vars(args))
    assert run_s9.v5_hydraulic_options(args, params=None) is None
    reference = SpeedReference([0.0] * 4, [(0.0, 0.7)] * 4, max_speed_m_s=V_MAX, ramp_s=0.1)
    assert reference.valve_meta()["valve_model_on"] is False
    assert reference.command_ramp_active is True


def test_run_s9_lc_without_the_valve_option_stops(run_s9) -> None:
    from outrigger_sim.params import load_params

    args = run_s9.build_parser().parse_args(
        ["level", "--soil", "J1", "--case", "x", "--out-root", "x", "--lock-overlap-ratio", "0.02",
         "--lock-closing-delay-s", "0.05"])
    with pytest.raises(SystemExit, match="valve"):
        run_s9.v5_hydraulic_options(args, load_params(model="L2b_NSC"))


def test_options_survive_the_job_dictionary() -> None:
    options = HydraulicOptions(valve_tau_s=0.1, rod_release_force=True,
                               check_delay=CheckDelaySetting("VN", 0.5, 0.01),
                               lock_closure=LockClosureSetting(0.02, 0.05),
                               lock_window_follows_plant=True)
    assert HydraulicOptions.from_dict(options.to_dict()) == options
    assert options.without_flow() == options


def test_v5_vb_rows_carry_exactly_the_vb_arguments() -> None:
    sys.path.insert(0, str(CHRONO_SCRIPTS))
    try:
        import s9_batch
    finally:
        sys.path.remove(str(CHRONO_SCRIPTS))
    rows = s9_batch.batches()[s9_batch.V5_VB_BATCH]
    assert len(rows) == 3
    for row in rows:
        assert row["argv"][-len(s9_batch.v5_vb_argv()):] == s9_batch.v5_vb_argv()
        assert row["source_expected_diffs"] == s9_batch.V5_VB_ARGS
        assert np.sum([token.startswith("--flow-eta-v") for token in row["argv"]]) == 1
