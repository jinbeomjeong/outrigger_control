"""Export controller input/output traces of the reduced-model C2 for the c2.py regression test.

Runs a few closed-loop cases of ``run_c2_timedomain.py`` with the revised controller ``C2R`` of
``run_c2_revision.py`` (gain set ``R:BS_hold`` = design section 9 gains + revision R1 of
``00_docs/04_control/c2_design.md`` section 16: latched crawler-zone rule on the motor-stroke /
low-passed-compression clearance, touch confirmation, stroke ends on the motor stroke) and records,
for every control step, what the controller received and what it returned. The scripts are
imported read-only; this file only wraps their sensor and controller classes to record.
(Before revision R1 the gain set was ``it3_proposal`` with ``C2D``; that data had no motor stroke.)

Recorded per control step (one row of a structured array):

* ``case`` - case index into the meta ``cases`` list,
* ``t_s`` - measurement time (s),
* ``specific_force_m_s2`` (3) - averaged specific force with bias and noise (the IMU input),
* ``cylinder_force_N`` (4) - pressure reading as cylinder force (with noise),
* ``rod_stroke_m`` (4) - stroke reading (rod position, with noise),
* ``motor_stroke_m`` (4) - motor stroke (L1 ``stroke_m``, own noise stream, revision R1),
* ``leg_speed_m_s`` (4) - command returned by ``C2D.update`` (before the plant-side delay
  and valve ramp),
* ``phase_code`` - controller phase after the update (see ``PHASE_CODES``),
* ``guard_steps`` - cumulative number of steps with the F_min guard active.

The meta JSON also stores the controller context (support matrix, twist vector, nominal pad
stiffness, ...) so the test can check the geometry derived from the YAML.

Revision R2 set (``--set r2``, design section 17, decision G9): the same rows from the
re-anchoring controller ``C2RN`` of ``run_c2_reanchor.py`` with its final option set ``H4``, on
that script's plant (``run_pad_tangential_check.TPlant``, pad tangential bushing) and with its
seal band (D5 start value 13 kN). The phase code adds ``REANCHOR`` (see ``R2_PHASE_CODES``); the
meta JSON also stores the re-anchoring log and metrics of every case (the design's regression
values, 17.7 Q11). ``run_c2_reanchor.py`` is imported lazily because importing it replaces the
plant class of ``run_control_comparison`` in this process.

Run (project root, needs numba -> dynamics-dev):
  conda run -n dynamics-dev python -I 04_scripts/03_control/export_c2_regression_traces.py
  conda run -n dynamics-dev python -I 04_scripts/03_control/export_c2_regression_traces.py --set r2
Writes 05_tests/data/c2_reduced_model_traces.npy and c2_reduced_model_traces.json (R1), or
c2_reanchor_traces.npy and c2_reanchor_traces.json (R2).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "01_dynamics"))
sys.path.insert(0, str(HERE))
import run_c2_revision as rv  # noqa: E402  (imports run_c2_timedomain; FlexPlant flex 0 = original kernel)
import run_c2_timedomain as td  # noqa: E402
import run_control_comparison as rcc  # noqa: E402

PROJECT_ROOT = HERE.parents[1]
OUT_DIR = PROJECT_ROOT / "05_tests" / "data"
OUT_STEM = "c2_reduced_model_traces"
GAINSET = "R:BS_hold"

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
    # revision R1: crawler-zone latch (front-down slope), touch confirmation, stroke-end fault on the motor stroke
    {"name": "top_pitch+3.5", "level": "top", "pitch": 3.5},
    {"name": "top_pitch-3.7_stroke_end", "level": "top", "pitch": -3.7},
)

# Revision R2 (design section 17): REANCHOR between the first DONE and PROBE / READY.
R2_OUT_STEM = "c2_reanchor_traces"
R2_VARIANT = "H4"  # final option set of run_c2_reanchor.VARIANTS (decision G9)
R2_SEAL_BAND_N = 13e3  # D5 start value, as run_c2_reanchor.run_one
R2_HOLD_AFTER_READY_S = 10.0
R2_PHASE_CODES = {**PHASE_CODES, "REANCHOR": 6}
R2_CASES = (
    # design 17.7 Q11: top, nose-down 3.5 deg, rigid mast, seed 12345, delay 1, pressure judge
    {"name": "top_pitch+3.5_reanchor", "level": "top", "pitch": 3.5, "seed": 12345},
    # combined judge with seal friction: load estimate P - F_band, probe after the trim
    {
        "name": "top_pitch+3.5_reanchor_Fs12_combined",
        "level": "top",
        "pitch": 3.5,
        "Fs": 12e3,
        "contact": "combined",
        "seed": 12345,
    },
)

ROW_DTYPE = np.dtype(
    [
        ("case", np.int64),
        ("t_s", np.float64),
        ("specific_force_m_s2", np.float64, (3,)),
        ("cylinder_force_N", np.float64, (4,)),
        ("rod_stroke_m", np.float64, (4,)),
        ("motor_stroke_m", np.float64, (4,)),
        ("leg_speed_m_s", np.float64, (4,)),
        ("phase_code", np.int64),
        ("guard_steps", np.int64),
    ]
)

_rows: list[tuple] = []
_contexts: list[object] = []
_case_index = 0


class RecordingSensors(rv.SensorsS):
    """``rv.SensorsS.read`` (same random draws, same order) that also returns the specific force."""

    def read(self, plant, acc, nsub):
        fb = acc[0:3] / nsub + self.bias + self.rng.normal(0, self.sig, 3)
        phi = math.atan2(fb[1], fb[2])
        th = math.atan2(-fb[0], math.hypot(fb[1], fb[2]))
        P = plant.pressure() + self.rng.normal(0, rcc.CA["pressure_noise_N"], 4)
        x = plant.x + self.rng.normal(0, rcc.CA["stroke_noise_m"], 4)
        s = plant.sref + self.rng_s.normal(0, rcc.CA["stroke_noise_m"], 4)
        return {"phi": phi, "theta": th, "P": P, "x": x, "s": s, "sat_ext": acc[3:7] > 0, "fb": fb.copy()}


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


class RecordingC2D(rv.C2R):
    """``C2D`` that records its inputs and outputs every update."""

    def __init__(self, ctx, contact="pressure"):
        super().__init__(ctx, contact=contact)
        _contexts.append(ctx)

    def update(self, m, t):
        u = np.array(super().update(m, t), dtype=float)
        _record_row(self, m, t, u, _phase_code(self))
        return u


def _record_row(ctrl, m, t, u, phase_code: int) -> None:
    _rows.append(
        (
            _case_index,
            t,
            m["fb"],
            np.array(m["P"], dtype=float),
            np.array(m["x"], dtype=float),
            np.array(m["s"], dtype=float),
            u,
            phase_code,
            getattr(ctrl, "guard_steps", 0),
        )
    )


def _phase_code_r2(ctrl) -> int:
    """``_phase_code`` plus REANCHOR while the re-anchoring sequence of ``C2RN`` runs."""
    reanchor = ctrl.ra
    if reanchor is not None and reanchor["st"] != "finished":
        return R2_PHASE_CODES["REANCHOR"]
    return _phase_code(ctrl)


def _recording_reanchor_controller(base):
    """``C2RN`` subclass that records like ``RecordingC2D`` (built lazily, see the docstring)."""

    class RecordingC2RN(base):
        def __init__(self, ctx, contact="pressure"):
            super().__init__(ctx, contact=contact)
            _contexts.append(ctx)

        def update(self, m, t):
            u = np.array(super().update(m, t), dtype=float)
            _record_row(self, m, t, u, _phase_code_r2(self))
            return u

    return RecordingC2RN


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
        # per leg (4,) in LEG_NAMES order; piston_area() is per leg once the bores differ (rev. 30)
        "piston_area_m2": np.broadcast_to(np.asarray(rcc.dm.piston_area(), float), (4,)).tolist(),
    }


def _reanchor_summary(rcn, result, ctrl) -> dict:
    """Re-anchoring outcome, log and metrics of one R2 case (``run_c2_reanchor`` formats)."""
    series = result.pop("_series")
    plant = rcn.rmf.LAST["plant"]
    result.update(rcn.rmf.extra_metrics(series, result, plant))
    metrics = rcn.ra_metrics(series, result, plant, ctrl)
    reanchor = ctrl.ra or {}
    return {
        "outcome": reanchor.get("outcome"),
        "P_stop_N": reanchor.get("P_stop_N"),
        "theta_ground_deg": metrics.get("theta_ground_deg"),
        "events": ctrl.ra_events,
        "log": ctrl.ra_log,
        "steps": metrics.get("steps"),
        "t_start_s": metrics.get("t_start_s"),
        "t_end_s": metrics.get("t_end_s"),
        "Ft_maxleg_start_kN": metrics.get("Ft_maxleg_start_kN"),
        "Ft_maxleg_final_kN": metrics.get("Ft_maxleg_final_kN"),
        "min_true_cyl_force_substep_kN": result.get("min_true_cyl_force_substep_kN"),
        "seal_band_end_N": ctrl.fs_band,
    }


def export_r2() -> None:
    """Record the R2 cases (REANCHOR, option set H4) into ``R2_OUT_STEM``."""
    global _case_index
    import run_c2_reanchor as rcn  # replaces rcc.Plant in this process

    recording_controller = _recording_reanchor_controller(rcn.C2RN)
    summaries = []
    for index, case in enumerate(R2_CASES):
        _case_index = index
        rcn.rmf.CONFIG.clear()
        rcn.rmf.CONFIG["record"] = True  # 1 ms plant record for the re-anchoring metrics
        rcn.ptc.RCFG.clear()
        rcn.ptc.RCFG["case_id"] = case["name"]
        rcn.RA.clear()
        rcn.RA.update(rcn.VARIANTS[R2_VARIANT])
        rcc.Plant = rcn.ptc.TPlant
        rcc.Sensors = RecordingSensors
        td.C2D = recording_controller
        rcc.CA.update(td.OPTION_DEFAULTS)
        rcc.CA.update(td.GAINSETS[GAINSET])
        rcc.CA["Fs_band_N"] = R2_SEAL_BAND_N
        rcc.T_HOLD = R2_HOLD_AFTER_READY_S
        kwargs = {key: value for key, value in case.items() if key != "name"}
        result = td.run_case(keep_series=True, **kwargs)
        ctrl = rcn.rmf.LAST["ctrl"]
        if not isinstance(ctrl, recording_controller):
            raise RuntimeError("the run did not use the recording C2RN")
        summary = {
            key: result.get(key)
            for key in ("t_touch_s", "t_done_s", "t_ready_s", "probe_rounds", "events", "fails")
        }
        summary["reanchor"] = _reanchor_summary(rcn, result, ctrl)
        summary["name"] = case["name"]
        summary["kwargs"] = kwargs
        summaries.append(summary)
        print(case["name"], summary["reanchor"]["outcome"], summary["t_ready_s"], flush=True)

    meta = {
        "generator": "04_scripts/03_control/export_c2_regression_traces.py --set r2",
        "gainset": GAINSET,
        "reanchor_variant": R2_VARIANT,
        "reanchor_options": rcn.VARIANTS[R2_VARIANT],
        "seal_band_N": R2_SEAL_BAND_N,
        "plant": "run_pad_tangential_check.TPlant (FlexPlant + pad tangential bushing, mu 0.5)",
        "revision": "R2 (00_docs/04_control/c2_design.md section 17, decision G9)",
        "phase_codes": R2_PHASE_CODES,
        "cases": summaries,
    }
    _write(R2_OUT_STEM, meta)


def _write(stem: str, meta: dict) -> None:
    rows = np.array(_rows, dtype=ROW_DTYPE)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(OUT_DIR / f"{stem}.npy", rows, allow_pickle=False)
    meta = {**meta, "context": _context_meta(_contexts[0]), "row_count": int(rows.size)}
    meta_path = OUT_DIR / f"{stem}.json"
    meta_path.write_text(json.dumps(meta, indent=1, default=float), encoding="utf-8")
    print(f"wrote {rows.size} rows to {stem}")


def export_r1() -> None:
    """Record the R1 cases into ``OUT_STEM`` (unchanged since revision R1)."""
    global _case_index
    td.C2D = RecordingC2D
    rcc.Sensors = RecordingSensors
    rv.CONFIG.clear()  # rigid mast: FlexPlant with flex 0 (= the original reduced kernel bit for bit)
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
        "revision": "R1 (00_docs/04_control/c2_design.md section 16)",
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--set",
        dest="trace_set",
        choices=("r1", "r2"),
        default="r1",
        help="r1: revision R1 cases (default), r2: REANCHOR cases of revision R2",
    )
    if parser.parse_args().trace_set == "r2":
        export_r2()
    else:
        export_r1()


if __name__ == "__main__":
    main()
