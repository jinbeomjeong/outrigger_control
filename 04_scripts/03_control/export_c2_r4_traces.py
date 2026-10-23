"""Export closed-loop traces of the C2 R4 / R4.1 defaults for the regression test (spec 18.1 P3).

The R2 / R3 traces (``export_c2_regression_traces.py``) come from the reduced-model reference
controllers, which have neither the trapezoid probe (P1) nor the joint integrator band (P2);
their replays keep the R2 / R3 settings. This script records the new defaults instead: the
``outrigger_sim.control.c2`` controller with its R4 defaults closes the loop around the reduced
6-DoF plant (``04_scripts/01_dynamics/run_control_comparison.Plant``, imported read-only), and
every control period's measurements, command and phase are stored. ``05_tests/unit/test_c2.py``
replays them; any change of the R4 behaviour shows up as a mismatch (self-regression, not an
independent reference).

Sensors: ideal (period-averaged specific force at C1, body angular rate, pressure, motor and
rod strokes, no noise); delay none; command ramp from the YAML.

Sets: ``r41`` (default) = the R4.1 defaults (spec 21.3 Q1 / Q2, 29 K1 / GE1), written to
``c2_r41_traces``; ``r4`` = the R4 settings (R4.1 judge changes off), written to
``c2_r4_traces``; the GE1 shadow events are left out of the ``r4`` event lists.

Run (project root, needs numba, Chrono-dev or dynamics-dev):
  <Chrono-dev python.exe> -I 04_scripts/03_control/export_c2_r4_traces.py [--set r41|r4]
Writes 05_tests/data/<stem>.npy and <stem>.json (about 1 min).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "03_src"))
sys.path.insert(0, str(PROJECT_ROOT / "04_scripts" / "01_dynamics"))
import run_control_comparison as reduced_model  # noqa: E402

from outrigger_sim.control.c2 import (  # noqa: E402
    C2_REVISION,
    C2Config,
    C2Controller,
    ProbeSettings,
    TargetSettings,
)
from outrigger_sim.control.ground_contact import RegroundRule, StiffnessWindow  # noqa: E402
from outrigger_sim.control.target import (  # noqa: E402
    AttitudeTarget,
    CrawlerSettleMap,
    SlopeLimitMode,
)
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.signals import Measurements  # noqa: E402

OUT_DIR = PROJECT_ROOT / "05_tests" / "data"
SHADOW_EVENT_PREFIX = "shadow_"
R4_PROBE = ProbeSettings(
    reground_rule=RegroundRule.VERDICT,
    attitude_ripple_ratio=None,
    attitude_drift_ratio=None,
    stiffness_window=StiffnessWindow.FULL,
)
TRACE_SETS = {
    "r41": ("c2_r41_traces", ProbeSettings(), "R4.1"),
    "r4": ("c2_r4_traces", R4_PROBE, "R4"),
}
HOLD_AFTER_READY_S = 5.0
RUN_LIMIT_S = 150.0
TARGET_CHANGE_AFTER_READY_S = 2.0

ROW_DTYPE = np.dtype(
    [
        ("case", np.int64),
        ("t_s", np.float64),
        ("specific_force_m_s2", np.float64, (3,)),
        ("angular_rate_rad_s", np.float64, (3,)),
        ("head_pressure_Pa", np.float64, (4,)),
        ("stroke_m", np.float64, (4,)),
        ("stroke_corrected_m", np.float64, (4,)),
        ("leg_speed_m_s", np.float64, (4,)),
        ("phase", "U10"),
    ]
)


@dataclass(frozen=True)
class TraceCase:
    name: str
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    is_verification: bool = False
    """Verification mode with the top settle map (slopes beyond the operating limit)."""
    target_change_deg: tuple[float, float] | None = None
    """READY change requested 2 s after the first READY (ramp + re-anchor)."""


CASES = (
    TraceCase("top_flat"),
    TraceCase("top_pitch+3.5", pitch_deg=3.5, is_verification=True),
    TraceCase("top_roll+5.5", roll_deg=5.5, is_verification=True),
    TraceCase("top_flat_change_pitch-3", target_change_deg=(0.0, -3.0)),
)


def _controller(case: TraceCase, probe: ProbeSettings) -> C2Controller:
    params = load_params()
    ramp_s = params.actuator.command_ramp_s
    target = TargetSettings()
    if case.is_verification:
        target = TargetSettings(
            slope_limit_mode=SlopeLimitMode.VERIFICATION,
            crawler_settle_map=CrawlerSettleMap.for_level("top"),
        )
    config = C2Config(target=target, probe=probe, output_ramp_time_s=ramp_s if ramp_s > 0 else None)
    # C2 R5 changed the defaults; both sets here are R4.1-or-older behaviour.
    return C2Controller.from_params(params, config.with_r41_behaviour())


def _settled_plant(case: TraceCase) -> reduced_model.Plant:
    plant = reduced_model.Plant("top", case.roll_deg, case.pitch_deg)
    plant.step(np.zeros(4), int(round(reduced_model.SETTLE_ON_CRAWLER_S / reduced_model.DT)))
    plant.t = 0.0
    return plant


def _measure(plant, accumulated, head_area_m2: float) -> Measurements:
    return Measurements(
        t_s=plant.t,
        specific_force_m_s2=accumulated[0:3] / reduced_model.N_SUB,
        angular_rate_rad_s=plant.w.copy(),
        head_pressure_Pa=plant.pressure() / head_area_m2,
        stroke_m=plant.sref.copy(),
        stroke_corrected_m=plant.x.copy(),
    )


def run_case(
    index: int, case: TraceCase, probe: ProbeSettings, keeps_shadow_events: bool
) -> tuple[list[tuple], dict]:
    plant = _settled_plant(case)
    controller = _controller(case, probe)
    head_area = controller.geometry.head_area_m2
    command = np.zeros(4)
    rows: list[tuple] = []
    ready_count = 0
    first_ready_s = change_s = None
    while plant.t < RUN_LIMIT_S:
        accumulated = plant.step(command, reduced_model.N_SUB)
        measurements = _measure(plant, accumulated, head_area)
        if (
            case.target_change_deg is not None
            and change_s is None
            and first_ready_s is not None
            and plant.t >= first_ready_s + TARGET_CHANGE_AFTER_READY_S
        ):
            change_s = plant.t
            controller.request_target(AttitudeTarget.from_degrees(*case.target_change_deg))
        command = np.array(controller.update(measurements).leg_speed_m_s)
        phase = str(controller.phase)
        rows.append(
            (
                index,
                measurements.t_s,
                measurements.specific_force_m_s2,
                measurements.angular_rate_rad_s,
                measurements.head_pressure_Pa,
                measurements.stroke_m,
                measurements.stroke_corrected_m,
                command,
                phase,
            )
        )
        if phase == "ready":
            first_ready_s = plant.t if first_ready_s is None else first_ready_s
            ready_count += 1
        else:
            ready_count = 0
        is_settled = case.target_change_deg is None or change_s is not None
        if is_settled and ready_count * reduced_model.T_CTRL >= HOLD_AFTER_READY_S:
            break
    roll, pitch = plant.attitude()
    summary = {
        "name": case.name,
        "case": {
            "roll_deg": case.roll_deg,
            "pitch_deg": case.pitch_deg,
            "is_verification": case.is_verification,
            "target_change_deg": case.target_change_deg,
        },
        "target_change_t_s": change_s,
        "events": [
            [event.t_s, event.name]
            for event in controller.events
            if keeps_shadow_events or not event.name.startswith(SHADOW_EVENT_PREFIX)
        ],
        "probe_rounds": len(controller.probe_history),
        "reanchor_outcomes": controller.meta()["reanchor"]["outcomes"],
        "final_phase": str(controller.phase),
        "final_true_attitude_deg": [math.degrees(roll), math.degrees(pitch)],
        "rows": len(rows),
    }
    return rows, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", choices=sorted(TRACE_SETS), default="r41", dest="trace_set")
    trace_set = parser.parse_args().trace_set
    out_stem, probe, revision = TRACE_SETS[trace_set]
    all_rows: list[tuple] = []
    summaries = []
    for index, case in enumerate(CASES):
        rows, summary = run_case(index, case, probe, keeps_shadow_events=trace_set == "r41")
        all_rows.extend(rows)
        summaries.append(summary)
        print(case.name, summary["final_phase"], summary["rows"], flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(OUT_DIR / f"{out_stem}.npy", np.array(all_rows, dtype=ROW_DTYPE), allow_pickle=False)
    meta = {
        "generator": "04_scripts/03_control/export_c2_r4_traces.py",
        "revision": revision,
        "controller_revision": C2_REVISION,
        "plant": "run_control_comparison.Plant (top, layout D crawler), ideal sensors, no delay",
        "config": (
            f"C2Config {revision} settings; slopes in the verification mode with the top settle map"
        ),
        "cases": summaries,
        "row_count": len(all_rows),
    }
    (OUT_DIR / f"{out_stem}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"wrote {len(all_rows)} rows to {out_stem}")


if __name__ == "__main__":
    main()
