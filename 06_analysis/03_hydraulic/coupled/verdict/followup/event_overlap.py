"""Criteria 9.1: demand around the event of R16 and R12 against the eta 0.85 supply (stored Chrono).

The record time runs ahead of the result's simulation time by the pre-start offset; the offset is
read from the two files (last record sample - s8_end.end_t_s), not assumed.

Usage: <Chrono-dev python> -I -B event_overlap.py <out json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(ROOT / "03_src"))

from outrigger_sim.hydraulics.flow_share import (  # noqa: E402
    SUPPLY_REL_TOL,
    FlowShareAssumptions,
    PumpFlowLimiter,
    flow_circuit_from_params,
)
from outrigger_sim.params import load_params  # noqa: E402

CASES = {
    "R16": ROOT / "07_results/S8/final_G1L_RE1bF_FL_top_o050_Fs4_20261031_004637"
                  "/G1L_RE1bF_FL_top_o050_Fs4",
    "R12": ROOT / "07_results/S8/final_E_G4_Fs4_20261030_233941/E_G4_Fs4",
}
ETA_V = 0.85
L_MIN_PER_M3_S = 6.0e4
SAMPLE_S = 0.1
AROUND_WINDOWS_S = ((-20.0, -10.0), (-10.0, -5.0), (-5.0, 0.0), (5.0, 10.0), (10.0, 20.0),
                    (20.0, 45.0))


def saturated_runs(is_short: np.ndarray) -> list[tuple[int, int]]:
    edges = np.diff(np.concatenate(([0], is_short.astype(int), [0])))
    return list(zip(np.flatnonzero(edges == 1).tolist(),
                    (np.flatnonzero(edges == -1) - 1).tolist(), strict=True))


def window_row(t, demand, is_short, first_s: float, last_s: float, supply_L_min: float) -> dict:
    selected = (t >= first_s) & (t < last_s)
    if not selected.any():
        return {"samples": 0}
    peak = float(demand[selected].max())
    return {"samples": int(selected.sum()), "max_Q_dem_L_min": round(peak, 3),
            "margin_to_supply_L_min": round(supply_L_min - peak, 3),
            "short_s": round(float(is_short[selected].sum()) * SAMPLE_S, 2)}


def analyse(case_dir: Path, limiter: PumpFlowLimiter) -> dict:
    result = json.loads((case_dir / "result.json").read_text(encoding="utf-8"))
    with np.load(case_dir / "record" / "record.npz", allow_pickle=False) as record:
        t, speeds = record["t"], record["u_applied"]
    with np.load(case_dir / "s8_series.npz", allow_pickle=False) as series:
        phase = series["phase"]
    offset_s = float(t[-1]) - float(result["s8_end"]["end_t_s"])
    event_s = float(result["event_t_s"]) + offset_s
    ramp_s = float(result["event"]["spec"]["ramp_s"])
    demand = np.array([limiter.demand_m3_s(row) for row in speeds]) * L_MIN_PER_M3_S
    supply = limiter.supply_m3_s * L_MIN_PER_M3_S
    is_short = demand > supply * (1.0 + SUPPLY_REL_TOL)

    windows = {}
    for start, stop in AROUND_WINDOWS_S:
        windows[f"{start:+g}..{stop:+g}"] = window_row(
            t, demand, is_short, event_s + start, event_s + stop, supply)
    windows["event 0..ramp"] = window_row(t, demand, is_short, event_s, event_s + ramp_s, supply)
    windows["ramp..+5"] = window_row(t, demand, is_short, event_s + ramp_s, event_s + 5.0, supply)

    runs = []
    for first, last in saturated_runs(is_short):
        start, stop = float(t[first]), float(t[last]) + SAMPLE_S
        overlaps = start < event_s + ramp_s and stop > event_s
        gap = 0.0 if overlaps else min(abs(start - (event_s + ramp_s)), abs(event_s - stop))
        runs.append({"start_s": round(start, 2), "stop_s": round(stop, 2),
                     "duration_s": round(stop - start, 2),
                     "phases": sorted(set(phase[first: last + 1].tolist())),
                     "max_Q_dem_L_min": round(float(demand[first: last + 1].max()), 3),
                     "overlaps_event_ramp": overlaps, "gap_to_event_ramp_s": round(gap, 2),
                     "relative_to_event_s": [round(start - event_s, 2), round(stop - event_s, 2)]})
    at_event = int(np.searchsorted(t, event_s - 1e-6))
    return {"supply_L_min": round(supply, 3), "record_sample_s": float(np.median(np.diff(t))),
            "record_end_s": float(t[-1]), "result_end_s": result["s8_end"]["end_t_s"],
            "record_minus_result_offset_s": round(offset_s, 6),
            "event_t_result_s": result["event_t_s"], "event_t_record_s": round(event_s, 3),
            "ramp_s": ramp_s, "phase_at_event_result": result["event_state"]["phase_at_event"],
            "phase_at_event_series": str(phase[at_event]),
            "Q_dem_at_event_L_min": round(float(demand[at_event]), 3),
            "u_applied_at_event_mm_s": np.round(speeds[at_event] * 1e3, 3).tolist(),
            "whole_run_short_s": round(float(is_short.sum()) * SAMPLE_S, 2),
            "whole_run_max_Q_dem_L_min": round(float(demand.max()), 3),
            "windows": windows, "saturated_runs": runs}


def main() -> None:
    params = load_params()
    assumptions = FlowShareAssumptions(eta_v=ETA_V, is_enabled=True)
    limiter = PumpFlowLimiter(flow_circuit_from_params(params), assumptions)
    report = {name: analyse(case_dir, limiter) for name, case_dir in CASES.items()}
    Path(sys.argv[1]).write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
