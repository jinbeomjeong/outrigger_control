"""One D-1 harness row on the v5 reduced harness (``d1_rows.py``; batch ``run_v5.py d1``).

Paths (``D1Row.path``), all imported, nothing copied:
  steady  ``s9_soil_slope.run_one``: uniform rigid or soil floor, slope, auger level; a soil
          base takes its settle row ``<soil>|<level>|<roll>|<pitch>`` (hook "harness"; a
          missing row raises KeyError). Head readings only.
  g6      ``r72_g6_screen.job(key, slope=, settle_hook=)``: PS-a, ``<base>+<patch>@<leg>``
          (rigid base: ``MixedRigidPads`` on the tilted floor; soil base: settle row of the
          base). Head readings only.
  event   426.3 mechanism (``s9_soil_event_screen``): PS-c, the base run gives the event time
          (``ready`` = READY + 5 s, ``level`` = mid of LOC and the first DONE), the run is
          repeated to 0.5 s before it and the branch lowers the soil reference surface under the
          leg by d P345((t - t_ev) / T) (``progressive_sink_event``). Head and rod readings.
The flow limit and v5 plant options come from ``verdict_runs.install_plant_options`` (VB / V0),
the crawler factor from ``run_control_comparison.CRAWLER_K_SCALE`` (P-1), both for this worker.

Record ``d1`` of every run (``d1_selection_rules.md`` 3, the field names of that sealed text):
  key, verdict (``pass`` / ``fail`` / ``allowed_stop``), fail_items, F_judged_min_N,
  F_first_level_min_N, t_ready_s, t_ready_limit_s, att_judged_deg, stroke_max_m, imu_R_c,
  dsb75_events, j_p3; ``ready_limit_rule`` (the rev1 READY rule with the SHA-256 of
  ``d1_selection_rules_rev1.md`` read from the file); and the records of the row definition:
  R_c_floor, R_c_settle_true,
  floor_estimate_error_deg (the x1 settle map against the true settle), crawler_k_scale_plant,
  F_first_level_after_liftoff_min_N, has_rod_reading, head_only_declared, expectation (H-R-A-stop).

Judgement per family (D-5: the existing criteria, ``d1_selection_rules.md`` 11):
  H-R  s6 D8 / P: 1 ms true F_cyl after the crawler lift-off >= F_min, end attitude <= 0.2 deg,
       READY <= 90 / 120 s, moving <= 180 bar, every F_cyl / A_p <= 350 bar, FAULT 0;
       H-R-A also the r72 G6 gates; a soil-guard safe stop of a row that allows it is
       ``allowed_stop``.
  H-S  P3 rows of ``s9_soil_slope`` (H-S-0 / H-S-1) or the r72 G6 gates (H-S-A), READY with
       the row's spec 421.1 limit (slope 120 s, flat uniform J1 / J2 / S1 100 s, other flat
       90 s; ``d1_selection_rules_rev1.md`` 1); ``stroke_limited_stop`` allowed.
  PS-c 426.3 E-1 .. E-7 (slow / fast) with the run-maximum stroke <= 684.8 mm.
"""

from __future__ import annotations

import contextlib
import copy
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
S9_DIR = ROOT / "04_scripts" / "03_control" / "s9"
S8_DIR = ROOT / "04_scripts" / "03_control" / "s8"
for _path in (HERE, S9_DIR, ROOT / "04_scripts" / "01_dynamics", ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import verdict_runs as vr  # noqa: E402
from d1_rows import (  # noqa: E402
    D8X_GROUP,
    FS_KN,
    PAD,
    RIGID,
    ROLE_RECORD,
    TAG_STROKE_STOP_ALLOWED,
    TAG_STROKE_STOP_EXPECTED,
    D1Row,
    ready_rule_record,
)
from harness_flow import COLUMN, TRUE_FORCE  # noqa: E402
from verdict_metrics import chunk_phases  # noqa: E402

ATTITUDE_LIMIT_DEG = 0.2
MOVING_LIMIT_BAR = 180.0
LOCKED_LIMIT_BAR = 350.0
RELIEF_BAR = 210.0
PA_PER_BAR = 1e5
START_ROLL_SPAN_DEG = 4.4
START_PITCH_SPAN_DEG = 3.2
VERDICT_PASS = "pass"
VERDICT_FAIL = "fail"
VERDICT_ALLOWED_STOP = "allowed_stop"
SOIL_STOP_VERDICT = "stroke_limited_stop"
FAULT_PHASES = ("fault", "fault_reground")
DSB75_PREFIXES = ("INFO_DIFF_SINK_HOLD", "INFO_DIFF_SINK_RELEASE")
STROKE_GUARD_EVENTS = ("FAULT_LIFT_STROKE_LIMIT", "WARN_LIFT_STROKE_LIMITED", "FAULT_STROKE_END")
J_P3_NOT_APPLICABLE = "not_applicable"
"""J-P3 of a V0 run (the ③ bound is a VB / LS option, criteria revision 8 3.1)."""
P3_SETTINGS = ("VB",)


# ------------------------------------------------------------------------------------ modules
@contextlib.contextmanager
def _argv_as_root():
    """``r72_g6_screen`` reads the project root from ``sys.argv[1]`` at import."""
    saved = sys.argv
    sys.argv = [saved[0] if saved else "", str(ROOT)]
    try:
        yield
    finally:
        sys.argv = saved


def _r72_module():
    if str(S8_DIR) not in sys.path:
        sys.path.insert(0, str(S8_DIR))
    with _argv_as_root():
        import r72_g6_screen
    return r72_g6_screen


def _settle_block() -> dict:
    import s9_soil_closed_loop as sl

    path = Path(os.environ.get(sl.SETTLE_TABLE_ENV) or sl.DEFAULT_SETTLE_TABLE)
    return json.loads(path.read_text(encoding="utf-8"))[sl.SETTLE_TABLE_BLOCK]


# -------------------------------------------------------------------------------------- paths
def _run_steady(row: D1Row, mass_scale: float = 1.0) -> tuple[dict, dict, object, object, dict]:
    import s9_soil_slope as slope

    case = slope.SlopeCase("D1", row.base, PAD, row.level, row.slope_name, row.roll_deg,
                           row.pitch_deg, mass_scale=float(mass_scale))
    case = slope.attach_settle_table([case], _settle_block())[0]
    if case.settle_table_status == "no_table_row":
        raise KeyError(f"settle table has no hook_harness row {case.harness_settle_key!r}")
    result = slope.run_one(case.to_dict())
    if "error" in result:
        raise RuntimeError(f"{row.key}: {result['error']}\n{result.get('tb')}")
    plant, ctrl = slope._CAP["plant"], slope._CAP["ctrl"]
    extra = {"harness_class": result["verdict"], "failed_rows": result["failed_rows"],
             "run": result["run"], "warnings": result["warnings"]}
    finished, series = vr._finish(plant, ctrl, extra)
    finished["harness_commands_sha256"] = result["run"]["commands_sha256"]
    return finished, series, plant, ctrl, result


def _run_g6(row: D1Row) -> tuple[dict, dict, object, object, dict]:
    r72 = _r72_module()
    key = f"d1|{row.soil}|{row.level}|Fs{FS_KN:g}"
    settle_hook = None if row.base == RIGID else "harness"
    record = r72.job(key, slope=(row.roll_deg, row.pitch_deg), settle_hook=settle_hook)
    if "error" in record:
        raise RuntimeError(f"{row.key}: {record['error']}\n{record.get('tb')}")
    plant, ctrl = r72._CAP["plant"], r72._CAP["ctrl"]
    extra = {"harness_class": record.get("verdict", "pass" if record["pass"] else "fail"),
             "g6_gates": record["gates"], "flags": record["flags"],
             "warnings": record["warnings"]}
    finished, series = vr._finish(plant, ctrl, extra)
    finished["harness_commands_sha256"] = record["commands_sha256"]
    return finished, series, plant, ctrl, record


def event_time_s(timeline: dict, timing: str) -> float | None:
    """PS-c event time of a base run: ``ready`` = READY + 5 s, ``level`` = mid LOC / first DONE."""
    import s9_soil_event_screen as study_a

    if timing == "ready":
        return None if timeline["t_ready"] is None else timeline["t_ready"] + study_a.READY_DELAY_S
    if timeline["t_loc"] is None or timeline["t_done"] is None:
        return None
    return timeline["t_loc"] + 0.5 * (timeline["t_done"] - timeline["t_loc"])


def _run_event(row: D1Row) -> tuple[dict, dict, object, object, dict]:
    import s9_soil_closed_loop as sl
    import s9_soil_event_screen as study_a
    from verdict_metrics import after_window_force_values

    cl, c2, meas = sl._imports()
    plant, ctrl, _ = study_a.make_event_base(cl, c2, row.base, row.level, PAD, FS_KN,
                                             slope=(row.roll_deg, row.pitch_deg))
    timeline = study_a.run_base_soil(cl, meas, copy.deepcopy(plant), copy.deepcopy(ctrl),
                                     hold_after_ready_s=study_a.READY_DELAY_S - study_a.PRE_S)
    target = event_time_s(timeline, row.sink.timing)
    timeline_record = {key: timeline[key] for key in ("t_lift", "t_loc", "t_done", "t_ready")}
    if target is None:  # report what the base did (verdict_runs._run_event rule)
        study_a.run_base_soil(cl, meas, plant, ctrl)
        extra = {"harness_class": None, "timeline": timeline_record,
                 "event_skipped": "base run without the READY / LOC / DONE of the event time"}
        finished, series = vr._finish(plant, ctrl, extra)
        return finished, series, plant, ctrl, {"event_skipped": True}
    prefix = study_a.run_base_soil(cl, meas, plant, ctrl, stop_t=target - study_a.PRE_S)
    t_ev = plant.t + study_a.PRE_S
    spec = study_a.progressive_sink_event(row.sink.depth_mm, row.sink.ramp_s)
    branch = study_a.branch_soil(cl, meas, plant, ctrl, prefix["cmd"].copy(),
                                 prefix["valve"].copy(), row.sink.name,
                                 sl.LEGS.index(row.sink.leg), t_ev, event_spec=spec)
    judged = study_a.judge_soil_event(branch, FS_KN, ctrl.geometry.head_area_m2,
                                      prefix["stroke_max_mm"])
    rows = branch.rows
    judged["after_window_force"] = after_window_force_values(
        rows[:, 0] - t_ev, rows[:, 5:9], rows[:, 1:5], judged["event_window_end_s"],
        float(ctrl.geometry.F_min_N))
    extra = {"harness_class": "pass" if judged["pass"] else "fail", "timeline": timeline_record,
             "event": row.sink.name, "leg": row.sink.leg, "timing": row.sink.timing,
             "t_event_s": round(t_ev, 3), "event_output": judged}
    finished, series = vr._finish(plant, ctrl, extra)
    return finished, series, plant, ctrl, judged


PATH_RUNNERS = {"steady": _run_steady, "g6": _run_g6, "event": _run_event}


# ------------------------------------------------------------------------------------- record
def first_level_minimum_N(rows: np.ndarray, period: dict,
                          after_index: int | None = None) -> float | None:
    """Smallest 1 ms true F_cyl of the four legs from the first LEVEL chunk to the first DONE
    chunk (the run end without one); ``after_index`` keeps only chunks from that index on."""
    phases = chunk_phases(rows, period["t"], period["phase"])
    levels = np.flatnonzero(phases == "level")
    if not levels.size:
        return None
    start = int(levels[0])
    dones = np.flatnonzero(phases[start:] == "done")
    end = start + int(dones[0]) + 1 if dones.size else len(rows)
    if after_index is not None:
        start = max(start, after_index)
    if start >= end:
        return None
    return float(rows[start:end, TRUE_FORCE].min())


def _lift_index(rows: np.ndarray, t_lift_s: float | None) -> int | None:
    if t_lift_s is None:
        return None
    return int(np.searchsorted(rows[:, COLUMN["t"]], t_lift_s - 1e-9))


def start_ratio(roll_deg: float, pitch_deg: float) -> float:
    """R_c = |phi| / 4.4 deg + |theta| / 3.2 deg."""
    return abs(roll_deg) / START_ROLL_SPAN_DEG + abs(pitch_deg) / START_PITCH_SPAN_DEG


def settle_map_records(row: D1Row, settle_attitude_rad: tuple[float, float]) -> dict:
    """IMU R_c of the floor by the x1 settle map (P-6), R_c of the true settle attitude and the
    controller's floor estimate error (the map applied to the true settle, minus the floor)."""
    from outrigger_sim.control.target import CrawlerSettleMap

    settle_map = CrawlerSettleMap.for_level(row.level)
    floor_rad = (math.radians(row.roll_deg), math.radians(row.pitch_deg))
    imu_deg = [math.degrees(v) for v in settle_map.crawler_from_floor(floor_rad)]
    estimate_deg = [math.degrees(v) for v in settle_map.floor_from_crawler(settle_attitude_rad)]
    settle_deg = [math.degrees(v) for v in settle_attitude_rad]
    return {"imu_R_c": start_ratio(*imu_deg), "imu_attitude_deg": imu_deg,
            "R_c_floor": start_ratio(row.roll_deg, row.pitch_deg),
            "R_c_settle_true": start_ratio(*settle_deg), "settle_attitude_true_deg": settle_deg,
            "floor_estimate_error_deg": [estimate_deg[0] - row.roll_deg,
                                         estimate_deg[1] - row.pitch_deg]}


def dsb75_events(controller) -> list[dict]:
    """``INFO_DIFF_SINK_HOLD:<legs>:<|r| mm/s>`` and ``INFO_DIFF_SINK_RELEASE:<reason>``."""
    out = []
    for event in controller.events:
        if not event.name.startswith(DSB75_PREFIXES):
            continue
        parts = event.name.split(":")
        entry = {"t_s": round(float(event.t_s), 3), "name": parts[0]}
        if parts[0] == DSB75_PREFIXES[0]:
            entry.update(axis=parts[1] if len(parts) > 1 else None,
                         r_mm_s=float(parts[2]) if len(parts) > 2 else None)
        else:
            entry["reason"] = parts[1] if len(parts) > 1 else None
        out.append(entry)
    return out


def j_p3_status(setting_name: str, record: dict | None, has_rod_reading: bool,
                head_only_declared: bool) -> str:
    """Per-run J-P3 (criteria revision 8 / 9): ``pass``, ``H-7``, ``no_rod_reading`` or
    ``setting_defect`` for a VB run, :data:`J_P3_NOT_APPLICABLE` for V0."""
    from outrigger_sim.control.extend_start_bound import (
        J_P3_JUDGED,
        J_P3_NO_ROD_READING,
        j_p3_run_case,
    )

    if setting_name not in P3_SETTINGS:
        return J_P3_NOT_APPLICABLE
    case = j_p3_run_case(record, has_rod_reading, head_only_declared)
    if case == J_P3_JUDGED:
        return "H-7" if sum(record.get("breach_reads") or []) else "pass"
    return "no_rod_reading" if case == J_P3_NO_ROD_READING else "setting_defect"


def _fault_events(controller) -> list[str]:
    return [e.name for e in controller.events if e.name.startswith("FAULT")]


def _d8_items(values: dict, rows: np.ndarray, head_area_m2, t_ready_s, limit_s, att_deg,
              controller) -> dict:
    """s6 D8 / P rows of a rigid run (True = pass)."""
    after = (values.get("forces") or {}).get("after_liftoff")
    moving = (values.get("pressure") or {}).get("max_moving_bar")
    peak_bar = float((rows[:, TRUE_FORCE] / np.asarray(head_area_m2, float)).max() / PA_PER_BAR)
    f_min = float(controller.geometry.F_min_N)
    return {"D8_F_after_liftoff": after is not None and after["min_kN"] * 1e3 >= f_min,
            "D8_end_attitude": att_deg is not None and att_deg <= ATTITUDE_LIMIT_DEG,
            "READY": t_ready_s is not None and t_ready_s <= limit_s,
            "moving_180bar": moving is None or moving <= MOVING_LIMIT_BAR,
            "locked_350bar": peak_bar <= LOCKED_LIMIT_BAR,
            "FAULT0": not _fault_events(controller)
            and str(controller.phase) not in FAULT_PHASES}


def _max_abs(values) -> float | None:
    if values is None:
        return None
    finite = [abs(float(v)) for v in values if v is not None and math.isfinite(float(v))]
    return max(finite) if finite else None


def judgement(row: D1Row, harness: dict, values: dict, rows: np.ndarray, controller,
              t_ready_s: float | None) -> dict:
    """verdict, fail_items, F_judged_min_N, att_judged_deg of one run (module docstring)."""
    limit = row.ready_limit_s
    is_ready_ok = t_ready_s is not None and t_ready_s <= limit
    allows_stop = TAG_STROKE_STOP_ALLOWED in row.tags
    is_soil_stop = harness.get("verdict") == SOIL_STOP_VERDICT
    if row.path == "event":
        items = {name: bool(ok) for name, ok in (harness.get("gates") or {}).items()}
        f_values = (harness.get("min_F_after_event_kN") if not harness.get("fast")
                    else harness.get("min_F_after_W_kN")) or {}
        f_judged = min(f_values.values()) * 1e3 if f_values else None
        att = _max_abs(harness.get("att_end_deg"))
        if harness.get("event_skipped"):
            items = {"event_time_reached": False}
    elif row.path == "g6":
        items = {name: bool(ok) for name, ok in harness["gates"].items()}
        items["READY"] = is_ready_ok
        f_judged = (None if harness.get("min_true_Fcyl_after_off_kN") is None
                    else harness["min_true_Fcyl_after_off_kN"] * 1e3)
        att = _max_abs(harness.get("att_end_deg"))
    else:
        failed = set(harness.get("failed_rows") or [])
        items = {name: name not in failed for name in sorted(harness.get("rows") or {})
                 if (harness["rows"][name] or {}).get("pass") is not None}
        items["READY"] = is_ready_ok
        harness_class = harness.get("verdict")
        if harness_class in ("error", "settle_check_fail", "stroke_limited_fail"):
            items[f"harness_{harness_class}"] = False
        min_off = (harness.get("run") or {}).get("min_true_Fcyl_after_off_kN")
        f_judged = None if min_off is None else min_off * 1e3
        att = _max_abs(((harness.get("rows") or {}).get("P3-4") or {}).get("att_end_deg"))
    if row.group.startswith("H-R"):
        d8 = _d8_items(values, rows, controller.geometry.head_area_m2, t_ready_s, limit, att,
                       controller)
        items = {**items, **d8} if row.path == "g6" else d8
        after = (values.get("forces") or {}).get("after_liftoff")
        f_judged = None if after is None else after["min_kN"] * 1e3
    fail_items = sorted(name for name, ok in items.items() if not ok)
    if is_soil_stop and allows_stop:
        verdict = VERDICT_ALLOWED_STOP
    elif fail_items:
        verdict = VERDICT_FAIL
    else:
        verdict = VERDICT_PASS
    return {"verdict": verdict, "fail_items": fail_items, "F_judged_min_N": f_judged,
            "att_judged_deg": att, "items": items}


def stop_expectation(row: D1Row, values: dict, rows: np.ndarray, controller) -> dict | None:
    """H-R-A-stop (record): stroke-guard family end, moving <= 210 bar, every F_cyl / A_p <=
    350 bar and no F_min breach after the lift-off; ``met`` False = "기대 불일치"."""
    if TAG_STROKE_STOP_EXPECTED not in row.tags:
        return None
    names = [e.name for e in controller.events]
    guard = sorted({n.split(":")[0] for n in names if n.startswith(STROKE_GUARD_EVENTS)})
    moving = (values.get("pressure") or {}).get("max_moving_bar")
    peak_bar = float((rows[:, TRUE_FORCE] / np.asarray(controller.geometry.head_area_m2,
                                                       float)).max() / PA_PER_BAR)
    after = (values.get("forces") or {}).get("after_liftoff")
    conditions = {"stroke_guard_end": bool(guard),
                  "moving_210bar": moving is None or moving <= RELIEF_BAR,
                  "locked_350bar": peak_bar <= LOCKED_LIMIT_BAR,
                  "F_min_after_liftoff": (after is None or after["min_kN"] * 1e3
                                          >= float(controller.geometry.F_min_N))}
    return {"met": all(conditions.values()), "conditions": conditions, "guard_events": guard}


def u3_record(harness: dict) -> dict:
    """The slope-suite record fields of a steady run (``s9_slope_fix_candidates
    .slope_record_fields``): what the U-3 judge reads when a U-3 key reuses this run
    (``u3_u6_rerun_rules.md`` 6 Q-5). Record only, after the run."""
    import s9_slope_fix_candidates as fix

    return fix.slope_record_fields(harness)


def d1_record(row: D1Row, setting_name: str, eps: float, result: dict, plant, controller,
              harness: dict) -> dict:
    """The ``d1`` block of a run (module docstring)."""
    rows = plant.flow_limiter.rows()
    period = vr.period_arrays(controller)
    values = result["values"]
    t_ready_s = (values.get("times") or {}).get("t_first_ready_s")
    t_lift_s = (values.get("forces") or {}).get("t_lift_s")
    first_level = first_level_minimum_N(rows, period)
    after_lift = first_level_minimum_N(rows, period, _lift_index(rows, t_lift_s))
    settle_rad = (float(rows[0, COLUMN["roll"]]), float(rows[0, COLUMN["pitch"]]))
    has_rod = bool(np.isfinite(period["rod_pressure_Pa"]).any())
    head_only = row.path != "event"
    bound_check = (result.get("hydraulics_record") or {}).get("extend_bound_check")
    judged = judgement(row, harness, values, rows, controller, t_ready_s)
    record = {
        "key": f"{row.key}|{setting_name}|e{eps:g}", "row_key": row.key, "group": row.group,
        "role": row.role, "path": row.path, "setting": setting_name, "eps": eps,
        **{k: v for k, v in judged.items() if k != "items"}, "items": judged["items"],
        "F_first_level_min_N": first_level, "F_first_level_after_liftoff_min_N": after_lift,
        "t_ready_s": t_ready_s, "t_ready_limit_s": row.ready_limit_s,
        "ready_limit_rule": ready_rule_record(),
        "stroke_max_m": float(plant.flow_limiter.max_stroke_reading_m),
        **settle_map_records(row, settle_rad),
        "crawler_k_scale_plant": float(getattr(plant, "crawler_k_scale", 1.0)),
        "dsb75_events": dsb75_events(controller),
        "has_rod_reading": has_rod, "head_only_declared": head_only,
        "j_p3": j_p3_status(setting_name, bound_check, has_rod, head_only),
        "harness_class": result.get("harness_class")}
    if row.path == "steady" and "rows" in harness:
        record["u3"] = u3_record(harness)
    expectation = stop_expectation(row, values, rows, controller)
    if expectation is not None:
        record["expectation"] = expectation
    if row.role == ROLE_RECORD:
        record["record_only"] = True
    if row.group == D8X_GROUP:
        record["d8x"] = d8x_block(row, values, plant, controller, rows)
    return record


def d8x_block(row: D1Row, values: dict, plant, controller, rows: np.ndarray) -> dict:
    """D8x R-c record of an H-R-X run (``d8x_record.run_metrics`` on the 1 ms chunks, the
    effective K1 gate, the angles and the repository files this worker imported)."""
    record = _d8x_record_module()
    times = values.get("times") or {}
    rod_weight = getattr(plant, "Wr", None)
    if rod_weight is None:
        raise RuntimeError(f"{row.key}: the plant has no rod weight Wr (D8x J3)")
    metrics = record.run_metrics(
        t_s=rows[:, COLUMN["t"]], cyl_force_N=rows[:, TRUE_FORCE], rod_weight_N=rod_weight,
        t_att_s=rows[:, COLUMN["t"]],
        att_deg=np.degrees(rows[:, [COLUMN["roll"], COLUMN["pitch"]]]),
        t_touch_s=times.get("t_touch_end_s"),
        t_crawler_off_s=(values.get("forces") or {}).get("t_lift_s"),
        t_ready_s=times.get("t_first_ready_s"), events=record.controller_events(controller),
        max_moving_bar=(values.get("pressure") or {}).get("max_moving_bar"),
        stroke_max_m=float(plant.flow_limiter.max_stroke_reading_m))
    files = record.repo_module_files(ROOT)
    return {"k1_order_gate": record.effective_k1(controller),
            "liftoff_slow_enabled": record.liftoff_slow_enabled(controller),
            "angles_deg": [row.roll_deg, row.pitch_deg], "level": row.level,
            "floor": row.slope_name, "crawler_k_scale": row.crawler_k_scale,
            "module_files": files, "module_files_sha256": record.files_digest(files),
            **metrics}


def _d8x_record_module():
    d8x_dir = ROOT / "04_scripts" / "03_control" / "d8x"
    if str(d8x_dir) not in sys.path:
        sys.path.insert(0, str(d8x_dir))
    import d8x_record

    return d8x_record


# ---------------------------------------------------------------------------------- public API
def execute(entry: dict, setting, hydraulics, *, setting_name: str,
            eps: float, k1: str | None = None, mass_scale: float = 1.0) -> tuple[dict, dict]:
    """Run one D-1 row in this worker (patches stay for the rest of the process).

    Args:
        entry: ``D1Row.to_job()`` of the row.
        setting: ``FlowSetting`` of the plant setting.
        hydraulics: ``HydraulicOptions`` or None (V0).
        setting_name: ``VB`` / ``V0`` (record and J-P3).
        eps: Phase offset of the run (the caller installs it; record only here).
        k1: D8x H-R-X jobs only: ``on`` / ``off`` sets the R4c30 order gate explicitly in
            this worker (the preset has it on since the K1 switch, so ``off`` is installed too);
            None (every other row) keeps the preset as it is.
        mass_scale: Plant superstructure mass / inertia factor of a steady row (spec 422.2,
            ``s9_soil_closed_loop.scale_plant_mass``; the controller keeps the YAML mass).
            1.0 (every d1 job) leaves the run bit for bit; B1 H-W runs 1.1 (B1 rules R-4).

    Returns:
        The result dict (``verdict_runs._finish`` keys, the plant options record,
        ``head_only_declared`` and ``d1``) and the 10 Hz series.

    Raises:
        ValueError: A D8x row without ``k1``, or ``mass_scale`` other than 1 on a row whose
            path is not ``steady``.
    """
    import run_control_comparison as rcc

    row = D1Row.from_job(entry)
    if row.group == D8X_GROUP and k1 is None:  # D8x rev3 2: no silent preset fallback
        raise ValueError(f"{row.key}: a D8x H-R-X row needs k1 off|on")
    if float(mass_scale) != 1.0 and row.path != "steady":
        raise ValueError(f"{row.key}: mass_scale {mass_scale} needs a steady row, not {row.path}")
    vr.install_plant_options(setting, hydraulics)
    c2 = vr.install_logged_controller()
    if k1 is not None:
        record = _d8x_record_module()
        record.install_k1_order_gate(record.k1_arm_is_on(k1), c2.C2Controller)
    rcc.CRAWLER_K_SCALE = float(row.crawler_k_scale)
    path_options = {"mass_scale": float(mass_scale)} if row.path == "steady" else {}
    result, series, plant, controller, harness = PATH_RUNNERS[row.path](row, **path_options)
    t_lift_s = ((result.get("values") or {}).get("forces") or {}).get("t_lift_s")
    result.update(vr.plant_options_record(hydraulics, t_lift_s))
    result[vr.HEAD_ONLY_DECLARED_KEY] = row.path != "event"
    result["d1"] = d1_record(row, setting_name, eps, result, plant, controller, harness)
    if k1 is not None:  # 436.8 record block: a D8x job requested the gate itself
        import resume_k1_record

        result[resume_k1_record.RECORD_KEY] = resume_k1_record.controller_record(controller,
                                                                                 request=k1)
    return result, series
