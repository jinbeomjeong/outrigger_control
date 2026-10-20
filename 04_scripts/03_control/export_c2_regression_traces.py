"""Export controller input/output traces of the reduced-model C2 for the c2.py regression test.

Runs a few closed-loop cases of ``run_c2_timedomain.py`` (gain set ``it3_proposal``, the design
proposal of ``00_docs/04_control/c2_design.md`` section 9) and records, for every control step,
what the reduced-model controller ``C2D`` received and what it returned. Both scripts are
imported read-only; this file only wraps their sensor and controller classes to record.

Recorded per control step (one row of a structured array):

* ``case`` - case index into the meta ``cases`` list,
* ``t_s`` - measurement time (s),
* ``specific_force_m_s2`` (3) - averaged specific force with bias and noise (the IMU input),
* ``cylinder_force_N`` (4) - pressure reading as cylinder force (with noise),
* ``rod_stroke_m`` (4) - stroke reading (rod position, with noise),
* ``leg_speed_m_s`` (4) - command returned by ``C2D.update`` (before the plant-side delay
  and valve ramp),
* ``phase_code`` - controller phase after the update (see ``PHASE_CODES``),
* ``guard_steps`` - cumulative number of steps with the F_min guard active.

The meta JSON also stores the controller context (support matrix, twist vector, nominal pad
stiffness, ...) so the test can check the geometry derived from the YAML.

Run (project root, needs numba -> dynamics-dev):
  conda run -n dynamics-dev python -I 04_scripts/03_control/export_c2_regression_traces.py
Writes 05_tests/data/c2_reduced_model_traces.npy and c2_reduced_model_traces.json.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "01_dynamics"))
sys.path.insert(0, str(HERE))
import run_c2_timedomain as td  # noqa: E402
import run_control_comparison as rcc  # noqa: E402

PROJECT_ROOT = HERE.parents[1]
OUT_DIR = PROJECT_ROOT / "05_tests" / "data"
OUT_STEM = "c2_reduced_model_traces"
GAINSET = "it3_proposal"

# Phase after an update, in the names of outrigger_sim.control.c2.C2Phase.
PHASE_CODES = {"TOUCH": 0, "LEVEL": 1, "DONE": 2, "PROBE": 3, "READY": 4, "FAULT": 5}

# Subset of the base matrix (section 8.1) plus cases that exercise the guard, the combined
# contact judge with the probe, and re-levelling after a sinking pad (section 8.2).
CASES = (
    {"name": "top_flat", "level": "top"},
    {"name": "top_diag3", "level": "top", "roll": 2.1213, "pitch": 2.1213},
    {"name": "bottom_pitch+3.7", "level": "bottom", "pitch": 3.7},
    {"name": "middle_roll+5.7", "level": "middle", "roll": 5.7},
    {"name": "top_softFL_diag3", "level": "top", "roll": 2.1213, "pitch": 2.1213, "soft_FL": True},
    {
        "name": "top_settle_Fs12_combined",
        "level": "top",
        "Fs": 12e3,
        "contact": "combined",
        "settle": True,
    },
)

ROW_DTYPE = np.dtype(
    [
        ("case", np.int64),
        ("t_s", np.float64),
        ("specific_force_m_s2", np.float64, (3,)),
        ("cylinder_force_N", np.float64, (4,)),
        ("rod_stroke_m", np.float64, (4,)),
        ("leg_speed_m_s", np.float64, (4,)),
        ("phase_code", np.int64),
        ("guard_steps", np.int64),
    ]
)

_rows: list[tuple] = []
_contexts: list[object] = []
_case_index = 0


class RecordingSensors(rcc.Sensors):
    """``rcc.Sensors.read`` (same random draws, same order) that also returns the specific force."""

    def read(self, plant, acc, nsub):
        fb = acc[0:3] / nsub + self.bias + self.rng.normal(0, self.sig, 3)
        phi = math.atan2(fb[1], fb[2])
        th = math.atan2(-fb[0], math.hypot(fb[1], fb[2]))
        P = plant.pressure() + self.rng.normal(0, rcc.CA["pressure_noise_N"], 4)
        x = plant.x + self.rng.normal(0, rcc.CA["stroke_noise_m"], 4)
        return {"phi": phi, "theta": th, "P": P, "x": x, "sat_ext": acc[3:7] > 0, "fb": fb.copy()}


def _phase_code(ctrl) -> int:
    if getattr(ctrl, "fault", False):
        return PHASE_CODES["FAULT"]
    if ctrl.phase == "touch":
        return PHASE_CODES["TOUCH"]
    if not ctrl.done:
        return PHASE_CODES["LEVEL"]
    if ctrl.ready:
        return PHASE_CODES["READY"]
    if ctrl.probe is not None or ctrl.rg is not None:
        return PHASE_CODES["PROBE"]
    return PHASE_CODES["DONE"]


class RecordingC2D(td.C2D):
    """``C2D`` that records its inputs and outputs every update."""

    def __init__(self, ctx, contact="pressure"):
        super().__init__(ctx, contact=contact)
        _contexts.append(ctx)

    def update(self, m, t):
        u = np.array(super().update(m, t), dtype=float)
        _rows.append(
            (
                _case_index,
                t,
                m["fb"],
                np.array(m["P"], dtype=float),
                np.array(m["x"], dtype=float),
                u,
                _phase_code(self),
                getattr(self, "guard_steps", 0),
            )
        )
        return u


def _context_meta(ctx) -> dict:
    return {
        "A": ctx.A.tolist(),
        "n": ctx.n.tolist(),
        "k_nom_N_m": ctx.k_nom,
        "S_nom_diag_N_m": np.diag(ctx.S_nom).tolist(),
        "F_min_N": ctx.F_min,
        "v_max_m_s": ctx.vmax,
        "stroke_max_m": ctx.smax,
        "pad_xy_m": ctx.xy.tolist(),
        "pad_z_retracted_m": ctx.zp.tolist(),
        "crawler_corners_xy_m": ctx.corners.tolist(),
        "crawler_bottom_z_m": ctx.zcb,
        "piston_area_m2": rcc.dm.piston_area(),
    }


def main() -> None:
    global _case_index
    td.C2D = RecordingC2D
    rcc.Sensors = RecordingSensors
    summaries = []
    for index, case in enumerate(CASES):
        _case_index = index
        rcc.CA.update(td.OPTION_DEFAULTS)
        rcc.CA.update(td.GAINSETS[GAINSET])
        kwargs = {key: value for key, value in case.items() if key != "name"}
        result = td.run_case(**kwargs)
        summary = {
            key: result.get(key)
            for key in ("t_touch_s", "t_done_s", "t_ready_s", "probe_rounds", "events", "fails")
        }
        summary["name"] = case["name"]
        summary["kwargs"] = kwargs
        summary["guard_active_s"] = result.get("guard_active_s")
        summaries.append(summary)
        print(case["name"], summary, flush=True)

    rows = np.array(_rows, dtype=ROW_DTYPE)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(OUT_DIR / f"{OUT_STEM}.npy", rows, allow_pickle=False)
    meta = {
        "generator": "04_scripts/03_control/export_c2_regression_traces.py",
        "gainset": GAINSET,
        "gains_and_options": td.GAINSETS[GAINSET],
        "reduced_model_assumptions": {
            key: rcc.CA[key]
            for key in (
                "Fs_band_N",
                "rod_weight_N",
                "P_touch_N",
                "clearance_target_m",
                "done_att_deg",
                "relevel_att_deg",
                "done_hold_s",
                "twist_deadband_N",
                "probe_speed_frac",
                "probe_depth_m",
                "probe_hold_s",
                "imu_lpf_tau_s",
                "imu_lpf_order",
                "done_filter_tau_s",
            )
        },
        "phase_codes": PHASE_CODES,
        "context": _context_meta(_contexts[0]),
        "cases": summaries,
        "row_count": int(rows.size),
    }
    meta_path = OUT_DIR / f"{OUT_STEM}.json"
    meta_path.write_text(json.dumps(meta, indent=1, default=float), encoding="utf-8")
    print(f"wrote {rows.size} rows")


if __name__ == "__main__":
    main()
