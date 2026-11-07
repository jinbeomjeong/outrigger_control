"""v5 option frame (spec ``v5_hydraulic_impl_spec.md`` 2.0, F-3, W-3): all off by default."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from outrigger_sim.hydraulics.flow_limit_run import add_flow_limit_arguments
from outrigger_sim.hydraulics.flow_share import FlowShareAssumptions
from outrigger_sim.hydraulics.v5_options import (
    CheckDelaySetting,
    HydraulicOptions,
    LockClosureSetting,
    add_hydraulic_arguments,
    hydraulic_options_from_args,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = PROJECT_ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "golden_off"
STORED_OFF_R1_DIGEST = "8b559936468481e55594cbcfc5193f53feec325672e731dbd1caca100e7d50de"
"""``definition_sha256`` of the off run R1; the harness flow tests pin the same value."""


def _parse(*argv: str, with_valve_tau: bool = True) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_flow_limit_arguments(parser)
    add_hydraulic_arguments(parser, with_valve_tau=with_valve_tau)
    return parser.parse_args(list(argv))


def test_f3_no_option_means_everything_off() -> None:
    args = _parse()
    assert vars(args) == {}
    options = hydraulic_options_from_args(args)
    assert options == HydraulicOptions()
    assert not options.is_any_on
    assert options.flow is None
    assert FlowShareAssumptions(eta_v=0.85).is_enabled is False


def test_all_options_parse_to_their_settings() -> None:
    options = hydraulic_options_from_args(_parse(
        "--flow-eta-v", "0.85", "--valve-tau-s", "0.1", "--rod-release-force",
        "--check-delay", "VN", "--check-delay-volume-scale", "0.5", "--check-delay-cv", "0.01",
        "--lock-overlap-ratio", "0.02", "--lock-closing-delay-s", "0.05",
        "--lock-window-follows-plant"))
    assert options.flow.eta_v == 0.85
    assert options.valve_tau_s == 0.1
    assert options.rod_release_force is True
    assert options.check_delay == CheckDelaySetting("VN", 0.5, 0.01)
    assert options.lock_closure == LockClosureSetting(0.02, 0.05)
    assert options.lock_window_follows_plant is True


def test_valve_tau_exists_only_where_asked() -> None:
    with pytest.raises(SystemExit):
        _parse("--valve-tau-s", "0.1", with_valve_tau=False)


@pytest.mark.parametrize("argv", [
    ("--check-delay-volume-scale", "0.5"),
    ("--check-delay-cv", "0.01"),
    ("--lock-overlap-ratio", "0.02"),
    ("--lock-closing-delay-s", "0.05"),
])
def test_an_option_without_its_partner_stops_the_run(argv) -> None:
    with pytest.raises(SystemExit):
        hydraulic_options_from_args(_parse(*argv))


def test_w3_controller_window_alone_stops_the_run() -> None:
    with pytest.raises(SystemExit):
        hydraulic_options_from_args(_parse("--lock-window-follows-plant"))
    with pytest.raises(SystemExit):
        HydraulicOptions(lock_window_follows_plant=True)


@pytest.mark.parametrize("ratio, delay", [(0.0, 0.05), (1.0, 0.05), (0.02, -1.0)])
def test_lock_closure_ranges(ratio, delay) -> None:
    with pytest.raises(ValueError):
        LockClosureSetting(ratio, delay)


def test_overlap_speed_is_the_ratio_of_v_max() -> None:
    assert LockClosureSetting(0.02, 0.05).overlap_speed_m_s(0.020924) == pytest.approx(0.41848e-3)


def test_m2_law_is_in_the_dict_of_m2_runs_only() -> None:
    """User decision 2026-11-06: ``m2_law`` only with M2 on (digests and metas of M2-off runs,
    final_C4G2 and the golden values stay bit for bit)."""
    with_m2 = HydraulicOptions(rod_release_force=True, lock_closure=LockClosureSetting(0.02, 0.05))
    assert with_m2.to_dict()["m2_law"] == "flow_limited_r5"
    assert HydraulicOptions.from_dict(with_m2.to_dict()) == with_m2
    without = HydraulicOptions(valve_tau_s=0.1, lock_closure=LockClosureSetting(0.02, 0.05))
    assert "m2_law" not in without.to_dict()
    assert "m2_law" not in HydraulicOptions().to_dict()


@pytest.mark.parametrize("stored_law", ["lag_only", "flow_limited_r3", "flow_limited_r4"])
def test_a_stored_other_m2_law_is_refused(stored_law: str) -> None:
    """User decision 2026-11-07: only revision 5 runs; stored revision 3 and 4 jobs are
    refused."""
    stored = {**HydraulicOptions(rod_release_force=True).to_dict(), "m2_law": stored_law}
    with pytest.raises(ValueError, match="M2 law"):
        HydraulicOptions.from_dict(stored)


@pytest.mark.parametrize("stored_law", ["flow_limited_r3", "flow_limited_r4", "flow_limited_r5"])
def test_a_stored_record_of_an_earlier_law_is_read(stored_law: str) -> None:
    """``from_stored`` (read only, ``t4h_replay``) keeps the settings of an earlier law."""
    options = HydraulicOptions(rod_release_force=True, lock_closure=LockClosureSetting(0.02, 0.05),
                               lock_window_follows_plant=True)
    assert HydraulicOptions.from_stored({**options.to_dict(), "m2_law": stored_law}) == options
    with pytest.raises(ValueError, match="M2 law"):
        HydraulicOptions.from_stored({**options.to_dict(), "m2_law": "lag_only"})


def test_b3_golden_digest_is_the_stored_definition() -> None:
    stored = json.loads((GOLDEN_DIR / "OFF_R1.json").read_text(encoding="utf-8"))
    assert stored["definition_sha256"] == STORED_OFF_R1_DIGEST
