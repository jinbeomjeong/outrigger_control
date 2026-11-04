"""Flow limit behind ``SpeedReference`` and its run record (``hydraulics.flow_limit_run``).

Off = the former reference bit for bit; on at the design point = the request; on below it = the
supply holds and the opening of the command-ramp path stays the true opening.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.actuation import FLOW_OPEN_KEY, SpeedReference
from outrigger_sim.hydraulics.flow_limit_run import (
    COLUMN,
    COLUMNS,
    V,
    FlowLimitSetting,
    RecordedFlowLimiter,
    add_flow_limit_arguments,
    flow_setting_from_args,
)
from outrigger_sim.hydraulics.flow_share import SUPPLY_REL_TOL, flow_circuit_from_params
from outrigger_sim.params import load_params

DT_S = 1.0e-4
RAMP_S = 0.1
FREE_AIR_FORCE_N = np.array([-1.0e3, -1.0e3, -0.8e3, -0.8e3])
LOAD_FORCE_N = np.array([90.0e3, 90.0e3, 70.0e3, 70.0e3])
STROKE = (0.0, 0.7)
STEPS = 5000


@pytest.fixture(scope="module")
def params():
    return load_params()


def _reference(params, *, valve: bool) -> SpeedReference:
    reference = SpeedReference(
        [0.1] * 4, [STROKE] * 4, max_speed_m_s=float(params.get("actuator.max_speed_m_s")),
        ramp_s=RAMP_S, max_force_extend_N=[2.0e5] * 4, max_force_retract_N=[6.0e4] * 4)
    if valve:
        reference.configure_valve(tau_s=0.1)
    return reference


def _limiter(params, eta_v: float) -> RecordedFlowLimiter:
    return RecordedFlowLimiter(flow_circuit_from_params(params), FlowLimitSetting(eta_v=eta_v))


def _run(reference: SpeedReference, force: np.ndarray, steps: int = STEPS) -> np.ndarray:
    speeds = np.empty((steps, 4))
    for k in range(steps):
        reference.advance(DT_S, cylinder_force_N=force, t_s=k * DT_S)
        speeds[k] = reference.u_applied_m_s
    return speeds


@pytest.mark.parametrize("valve", [True, False])
def test_design_point_is_bit_identical_to_no_limit(params, valve) -> None:
    """Criteria V-1: eta_v 0.95, all legs at v_max: demand = supply, the request stays."""
    free = _reference(params, valve=valve)
    limited = _reference(params, valve=valve)
    limited.set_flow_limit(_limiter(params, 0.95))
    for reference in (free, limited):
        reference.set_command([reference.max_speed_m_s] * 4)
    speeds_free, speeds_limited = _run(free, FREE_AIR_FORCE_N), _run(limited, FREE_AIR_FORCE_N)
    assert np.array_equal(speeds_free, speeds_limited)
    assert np.array_equal(free.s_ref_m, limited.s_ref_m)


@pytest.mark.parametrize("valve", [True, False])
def test_short_supply_keeps_the_flow_sum_and_reaches_a_steady_speed(params, valve) -> None:
    """eta_v 0.85, all legs at v_max: sum A_p v <= Q_sup (1 + 1e-6), the sum reaches Q_sup."""
    reference = _reference(params, valve=valve)
    limiter = _limiter(params, 0.85)
    reference.set_flow_limit(limiter)
    reference.set_command([reference.max_speed_m_s] * 4)
    speeds = _run(reference, FREE_AIR_FORCE_N)
    head_area = limiter.circuit.head_area_m2
    flow = (speeds * head_area).sum(axis=1)
    assert flow.max() <= limiter.supply_m3_s * (1.0 + SUPPLY_REL_TOL)
    assert flow[-1] == pytest.approx(limiter.supply_m3_s, rel=1e-3)
    assert limiter.summary()["short_s"] > 0.0


def test_ramp_opening_is_the_true_opening_not_the_delivered_speed(params) -> None:
    """Command ramp: under a short supply the opening still ramps to the command, so the limiter
    sees the full request; the applied speed keeps following the shared flow."""
    reference = _reference(params, valve=False)
    limiter = _limiter(params, 0.85)
    reference.set_flow_limit(limiter)
    v_max = reference.max_speed_m_s
    reference.set_command([v_max] * 4)
    _run(reference, LOAD_FORCE_N)
    opening = reference.state_arrays()[FLOW_OPEN_KEY]
    assert np.array_equal(opening, np.full(4, v_max))
    assert reference.u_applied_m_s.min() < v_max
    assert limiter.rows()[-1, COLUMN["u_FL"]] == v_max


def test_limit_off_keeps_the_state_keys_and_on_adds_only_the_opening(params) -> None:
    off = _reference(params, valve=False).state_arrays()
    limited = _reference(params, valve=False)
    limited.set_flow_limit(_limiter(params, 0.85))
    assert FLOW_OPEN_KEY not in off
    assert set(limited.state_arrays()) - set(off) == {FLOW_OPEN_KEY}


def test_snapshot_round_trip_continues_bit_for_bit(params) -> None:
    first = _reference(params, valve=False)
    first.set_flow_limit(_limiter(params, 0.85))
    first.set_command([first.max_speed_m_s] * 4)
    _run(first, LOAD_FORCE_N, 1500)
    state = first.state_arrays()
    second = _reference(params, valve=False)
    second.set_flow_limit(_limiter(params, 0.85))
    second.restore_state(state)
    assert np.array_equal(_run(first, LOAD_FORCE_N, 500), _run(second, LOAD_FORCE_N, 500))


def test_retracting_leg_stays_limited_by_annulus_area(params) -> None:
    """A retracting leg draws A_ann |u|: sum of head and annulus flows stays at the supply."""
    limiter = _limiter(params, 0.5)
    u = np.array([0.02, 0.02, -0.02, -0.02])
    v = limiter.limit(0.0, DT_S, u, np.array([50.0e3, 50.0e3, -1.0e3, -1.0e3]))
    area = np.where(u < 0, limiter.circuit.annulus_area_m2, limiter.circuit.head_area_m2)
    assert (area * np.abs(v)).sum() <= limiter.supply_m3_s * (1.0 + SUPPLY_REL_TOL)
    assert np.all(np.sign(v) == np.sign(u))


def test_force_is_required_with_a_limit(params) -> None:
    reference = _reference(params, valve=True)
    reference.set_flow_limit(_limiter(params, 0.85))
    with pytest.raises(ValueError, match="cylinder force"):
        reference.advance(DT_S)


def test_plant_without_opening_is_refused(params) -> None:
    reference = SpeedReference([0.1] * 4, [STROKE] * 4, max_speed_m_s=0.02, ramp_s=0.0)
    with pytest.raises(ValueError, match="valve model or the command ramp"):
        reference.set_flow_limit(_limiter(params, 0.85))


def test_record_rows_summary_and_file(params, tmp_path) -> None:
    limiter = _limiter(params, 0.85)
    v_max = float(params.get("actuator.max_speed_m_s"))
    for k in range(25000):
        request = np.full(4, v_max if k * DT_S >= 1.0 else 0.0)
        limiter.limit(k * DT_S, DT_S, request, FREE_AIR_FORCE_N)
    rows = limiter.rows()
    assert rows.shape == (2500, len(COLUMNS))
    assert np.allclose(np.diff(rows[:, 0]), 1.0e-3)
    assert np.isnan(rows[0, COLUMN["p_P"]])
    assert np.isfinite(rows[-1, COLUMN["p_P"]])
    assert rows[-1, COLUMN["limited_mask"]] != 0
    summary = limiter.summary([0.0, 1.0], ("check", "touch"))
    assert summary["by_phase"]["check"]["short_s"] == 0.0
    assert summary["by_phase"]["touch"]["short_s"] == pytest.approx(1.5, abs=2e-3)
    assert summary["short_s"] == pytest.approx(1.5, abs=2e-3)
    assert summary["max_deficit_L_min"] == pytest.approx(57.19 - 51.17, abs=0.01)
    assert summary["steps"]["audit_mismatches"] == 0
    assert summary["speed_ratio"]["FL"]["longest_below_0p93_s"] >= 0.0
    assert json.dumps(summary)
    entry = limiter.save(tmp_path / "flow.npz")
    assert entry["rows"] == len(rows)
    with np.load(tmp_path / "flow.npz") as saved:
        assert np.array_equal(saved["rows"], rows, equal_nan=True)
        assert tuple(saved["columns"].tolist()) == COLUMNS
        assert np.array_equal(saved["rows"][:, V], rows[:, V])


def test_coupled_batch_rows_and_resume(tmp_path, monkeypatch) -> None:
    """COUPLED_eta085: ten rows = the stored argv + the flow arguments; --resume skips finished rows."""
    source = Path(__file__).resolve().parents[2] / "04_scripts" / "02_chrono"
    monkeypatch.syspath_prepend(str(source))
    import s9_batch  # noqa: PLC0415

    batches = s9_batch.batches()
    rows = batches[s9_batch.COUPLED_BATCH]
    flow = s9_batch.coupled_flow_argv()
    assert len(rows) == 10
    stored = {c["case"]: c["argv"] for name in ("FINAL-REP", "FINAL-REP-X", "FINAL-R-REP") for c in batches[name]}
    for row in rows:
        assert row["argv"][-len(flow):] == flow
        former = stored[row["case"]]
        kept = row["argv"][: -len(flow)]
        if row.get("s8c"):
            tag = kept.index("--tag") + 1
            assert kept[tag] == f"coupled_eta085_{row['case']}"
            assert kept[:tag] + kept[tag + 1:] == former[:tag] + former[tag + 1:]
        else:
            assert kept == former
            assert (Path(s9_batch.ROOT) / "07_results" / "S9" / row["source_run"] / "result.json").is_file()
    assert {row["criteria_id"] for row in rows} == {
        "S1", "S6", "S8", "R2", "R4", "R16", "R12", "R6", "R8", "R9"}

    python = [sys.executable, "-c", "import sys; sys.exit(0)"]
    trial = [{"case": name, "argv": python, "est_s": 1.0} for name in ("a", "b")]
    monkeypatch.setattr(s9_batch, "batches", lambda **_: {"T": trial})
    monkeypatch.setattr(s9_batch.time, "sleep", lambda _: None)
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "result.json").write_text("{}", "utf-8")
    folder = s9_batch.run_batch("T", parallel=1, resume=str(tmp_path))
    assert folder == tmp_path
    doc = json.loads((tmp_path / "batch.json").read_text("utf-8"))
    assert [(c["case"], c["rc"]) for c in doc["cases"]] == [("a", 0), ("b", 0)]
    assert doc["cases"][0]["pool"] == "earlier_launch"
    progress = (tmp_path / "progress.log").read_text("utf-8")
    assert "RESUME_SKIP a" in progress and "START b" in progress and "START a" not in progress


def test_cli_absent_stays_absent_and_nominal_defaults() -> None:
    parser = argparse.ArgumentParser()
    add_flow_limit_arguments(parser)
    args = parser.parse_args([])
    assert vars(args) == {}
    assert flow_setting_from_args(args) is None
    setting = flow_setting_from_args(parser.parse_args(["--flow-eta-v", "0.85"]))
    assumptions = setting.assumptions()
    assert assumptions.is_enabled and assumptions.eta_v == 0.85
    assert assumptions.compensator_drop_Pa == 10.0e5
    assert assumptions.unloading_drop_Pa == 20.0e5
    assert assumptions.smoothing_width_Pa == 1.0e5
    assert FlowLimitSetting.from_dict(setting.to_dict()) == setting
    with pytest.raises(SystemExit):
        flow_setting_from_args(parser.parse_args(["--flow-dp-comp-bar", "6"]))
