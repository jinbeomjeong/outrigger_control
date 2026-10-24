"""Export controller input/output traces of the reduced-model R8-D1 C2 for the c2.py regression.

Spec: ``00_docs/04_control/s6_control_spec.md`` revision 30, 134 and 139 (design C2, user
decisions 2026-10-24). The cases are run with the time-domain harness of that revision
(``04_scripts/03_control/r8d1/r8d1_td2.py``, configuration ``C2_tv0.1``: 10 Hz, output delay
d = 1 in the harness queue, increment limit 0.25 v_max per period as the harness ramp, valve
lag 0.1 s, R-1 / R-2, A8 attitude gains, twist gain 0.5 on ``n^T P`` low-passed 0.2 s, guard
gain 0.15). The harness scripts are imported read-only; this file only wraps their sensor and
controller classes to record, as ``export_c2_regression_traces.py`` does for revision R1.

Recorded per control step (one row of a structured array, ``ROW_DTYPE``):

* ``case`` - index into the meta ``cases`` list, ``t_s`` - measurement time (s),
* ``specific_force_m_s2`` (3) - period-mean specific force with bias and noise,
* ``cylinder_force_N`` (4) - pressure reading as cylinder force (with noise),
* ``rod_stroke_m`` (4), ``motor_stroke_m`` (4) - stroke readings (with noise),
* ``leg_speed_m_s`` (4) - command returned by the harness controller (before the harness
  queue, ramp and valve lag),
* ``phase_code`` - controller phase after the update, ``guard_steps`` - cumulative steps with
  the F_min guard active.

The meta JSON keeps the harness metrics of every recorded run next to the values of the same
case in the revision-30 result file (``06_analysis/02_control/r8_10hz/d1/td2_*.json``), so the
test can check that the traces are the spec's runs.

Run (project root, needs numba -> dynamics-dev; MKL_THREADING_LAYER=TBB):
  C:\\ProgramData\\miniforge3\\envs\\dynamics-dev\\python.exe -I \
      04_scripts/03_control/export_c2_r8d1_traces.py
Writes 05_tests/data/c2_r8d1_traces.npy and c2_r8d1_traces.json.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE / "r8d1"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "01_dynamics"))
import r8d1_td2 as td2  # noqa: E402  (installs the valve-lag patch and the C2R8F controller)
import run_c2_revision as rcr  # noqa: E402

rcc, rpt, r8 = td2.rcc, td2.rpt, td2.r8

OUT_DIR = PROJECT_ROOT / "05_tests" / "data"
OUT_STEM = "c2_r8d1_traces"
RESULT_DIR = PROJECT_ROOT / "06_analysis" / "02_control" / "r8_10hz" / "d1"
CONFIG_NAME = "C2_tv0.1"

# Representative C2 cases of spec 134: the D8 minimum of the 54-case set (top, roll+ boundary,
# rigid, beta 1.6), a nose-down boundary case with the upper-support mast surrogate, and the
# G4-type settlement (RR sinks 11.5 mm after READY; guard active, beta 1.6).
CASES = (
    {"group": "S", "id": f"T|{CONFIG_NAME}|roll+|rigid|12346|1.6e+09"},
    {"group": "S", "id": f"T|{CONFIG_NAME}|pitch+|upper|12345|1e+09"},
    {"group": "G", "id": f"G|{CONFIG_NAME}|flat|rigid|12345|1.6e+09"},
)
RESULT_FILES = {
    "S": "td2_S_C1_tv0.1_C2_tv0.1.json",
    "G": "td2_G_C1_tv0.1_C2_tv0.1_R12AR_tv1_G_base50_tv1.json",
}
METRIC_KEYS = (
    "t_touch_s",
    "t_crawler_liftoff_s",
    "t_ready_s",
    "min_true_cyl_force_kN",
    "ss_true_att_deg_maxabs",
    "max_pressure_bar",
)

PHASE_CODES = {"TOUCH": 0, "LEVEL": 1, "DONE": 2, "PROBE": 3, "READY": 4, "FAULT": 5}
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
_case_index = 0


class RecordingSensors(rcr.SensorsS):
    """``rcr.SensorsS.read`` (same random draws in the same order) that also returns ``fb``."""

    def read(self, plant, acc, nsub):
        fb = acc[0:3] / nsub + self.bias + self.rng.normal(0, self.sig, 3)
        phi = math.atan2(fb[1], fb[2])
        theta = math.atan2(-fb[0], math.hypot(fb[1], fb[2]))
        P = plant.pressure() + self.rng.normal(0, rcc.CA["pressure_noise_N"], 4)
        x = plant.x + self.rng.normal(0, rcc.CA["stroke_noise_m"], 4)
        s = plant.sref + self.rng_s.normal(0, rcc.CA["stroke_noise_m"], 4)
        return {"phi": phi, "theta": theta, "P": P, "x": x, "s": s, "sat_ext": acc[3:7] > 0,
                "fb": fb.copy()}


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


class RecordingC2R8F(td2.C2R8F):
    """The harness C2 controller that records what it received and returned."""

    def update(self, m, t):
        u = np.array(super().update(m, t), dtype=float)
        _rows.append(
            (
                _case_index,
                t,
                m["fb"],
                np.array(m["P"], dtype=float),
                np.array(m["x"], dtype=float),
                np.array(m["s"], dtype=float),
                u,
                _phase_code(self),
                getattr(self, "guard_steps", 0),
            )
        )
        return u


def _harness_case(spec: dict) -> dict:
    cases = r8.cases_S([CONFIG_NAME]) if spec["group"] == "S" else td2.cases_G([CONFIG_NAME])
    matches = [case for case in cases if case["id"] == spec["id"]]
    if len(matches) != 1:
        raise RuntimeError(f"case {spec['id']!r} not found once in group {spec['group']}")
    return matches[0]


def _published_result(spec: dict) -> dict:
    path = RESULT_DIR / RESULT_FILES[spec["group"]]
    runs = json.loads(path.read_text(encoding="utf-8"))["runs"]
    return next(run for run in runs if run.get("id") == spec["id"])


def _metrics(run: dict) -> dict:
    metrics = {key: run.get(key) for key in METRIC_KEYS}
    settle = run.get("settle_result")
    if settle:
        metrics["min_true_after_sink_kN"] = settle.get("min_true_after_sink_kN")
        metrics["final_true_kN"] = settle.get("final_true_kN")
    return metrics


def main() -> None:
    global _case_index
    rcr.SensorsS = RecordingSensors  # run_one assigns rcc.Sensors = rcr.SensorsS per run
    summaries = []
    for index, spec in enumerate(CASES):
        _case_index = index
        rpt.C2RA = RecordingC2R8F  # run_one builds and identity-checks rpt.C2RA
        case = _harness_case(spec)
        run = td2.run(case)
        if "error" in run:
            raise RuntimeError(f"{spec['id']}: {run['error']}\n{run.get('tb')}")
        published = _published_result(spec)
        summary = {
            "id": spec["id"],
            "group": spec["group"],
            "level": case["level"],
            "mast": case["mast"],
            "seed": case["seed"],
            "beta_Pa": case.get("beta", 1.0e9),
            "rcfg": {key: value for key, value in case["rcfg"].items() if key != "reanchor"},
            "metrics": _metrics(run),
            "published_metrics": _metrics(published),
            "row_count": sum(1 for row in _rows if row[0] == index),
        }
        summaries.append(summary)
        print(spec["id"], summary["metrics"], flush=True)

    rows = np.array(_rows, dtype=ROW_DTYPE)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(OUT_DIR / f"{OUT_STEM}.npy", rows, allow_pickle=False)
    meta = {
        "generator": "04_scripts/03_control/export_c2_r8d1_traces.py",
        "spec": "s6_control_spec.md revision 30, 134 (C2 R8-D1 time responses), 139",
        "harness": "r8d1_td2.py C2R8F on run_c2_r8_10hz_check / run_s6_slope_boundary_check",
        "configuration": CONFIG_NAME,
        "configuration_values": r8.CONFIGS[CONFIG_NAME],
        "gainset": rpt.R1,
        "control_period_s": 0.1,
        "phase_codes": PHASE_CODES,
        "cases": summaries,
        "row_count": int(rows.size),
    }
    meta_path = OUT_DIR / f"{OUT_STEM}.json"
    meta_path.write_text(json.dumps(meta, indent=1, default=float), encoding="utf-8")
    print(f"wrote {rows.size} rows to {OUT_STEM}")


if __name__ == "__main__":
    main()
