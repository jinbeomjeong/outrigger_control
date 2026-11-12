"""436.8 path 1 judge of the v5 stage 1 J items (H-9 / H-10), new version (rules rev5 R5-A1).

Reads the 436.8 outputs given as arguments (``resume_k1/h9_stage1.jsonl``: main stage-1
settings + pressure_only; ``resume_k1/h10_reuse_rerun.jsonl``: main VB / LS + U-9 VB + item8 +
overlap). Each line's batch is found by its ``run_v5.job_key`` in ``run_v5.batch_jobs``. The
per-line quantities are ``judge_stage1_r5.metrics`` (unchanged); the definitions below replace
the ones of ``judge_stage1_r5.py`` (rev5 R5-A3):

  D-07  J1: fail = V0 in the passing family (``pass``, ``stroke_limited_stop``) and the setting
        outside it; a ``pass`` <-> ``stroke_limited_stop`` move is a record. S8 (criteria 6)
        expects ``stroke_limited_stop``: leaving it is a J1 failure (rev3 R3-C3).
  D-08  J2: F_min 9,414.589 N; the rigid event rows (R12, R14, R15, R16, G4 width grid) use
        E-3 (``min_F_after_W_kN``, window + 1 ms); spec-shortfall mark 14,414.589 N (R3-C4).
  D-09  J7 names: the ':' segments that are numbers are dropped, the others kept;
        ``WARN_ROD_PRESSURE_FALLBACK`` compares reason and controller period (R3-C6).
  D-10  J11: ``n_late`` None on a line with fallback legs = ``판정 불가``; without fallback
        legs ``not_computed`` (R3-C7); fallback-leg ``n_late`` > 0 = stop (VB H-7, LS L-e,
        rev5 R5-B3).
  D-11  J3: S1 .. S5, S7 first READY <= 100 s judged; R1 .. R11 FLAG over 120 s (floor slope)
        / 90 s (flat) from ``values.case_floor_deg`` (F-3), no field = limit "미정" (R4-C5).
  D-12  P-7 violation only when every L1 line has the hash of the same-key V0 line (Q-S4).
  D-13  13.1 order: ``순서 유지`` / ``반대`` (full reverse, ranges apart; VB fails when V0 keeps
        the order) / ``순서 판정 불가`` FLAG (Q-S5).
  D-14  S8 SA-4: the seven items of criteria 6 (Q-S6, F-4 ``values.sa4``); a missing record =
        ``판정 불가``.
  D-15  H-8 FL guard time: first ``WARN_LIFT_STROKE_LIMITED:`` naming FL, integer periods (Q-S7).
  D-16  L-d: phase scatter of ``m1_criteria.md`` 5 (distinct: |E| > S and all pair differences
        of one sign) added to the 1 kN / 1 s record (Q-S9).
  D-17  U-9 VB lines of H-10: counted (S-15) only, graded by H-5 (Q-S10).
J-P3 (rev3 R3-C8): ③ lines only; rod reading = a finite ``rod_pressure_Pa`` in the line's T4h
file, head-only declaration = the line's ``head_only_declared``, else the steady-path rule
(R1 .. R11, S1 .. S8); ``v5_rerun.j_p3_status`` table; ``setting_defect`` / ``H-7`` stop.
Harness grades use ``harness_class`` (Q-S1); S8 J6 is not applicable without READY (Q-S2).

Usage (python-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/judge_stage1_4368.py --out <report.json>
      --h9 <h9_stage1.jsonl> --h10 <h10_reuse_rerun.jsonl> [--t4h-dir <dir> ...]
      [--overlap-ref <h10_overlap_t_a.json>] [--rules-dir <verif_matrix>]
Exit codes: 0 judged, 1 a stop / VB J failure / 판정 불가, 2 input error, 3 internal error.
"""

from __future__ import annotations

import argparse
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STAGE1_SCRIPTS = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "paper_runs" / "scripts"
for _path in (
    HERE,
    STAGE1_SCRIPTS,
    ROOT / "04_scripts" / "03_control" / "m1_check",
    ROOT / "04_scripts" / "03_control" / "s9",
    ROOT / "03_src",
):
    if str(_path) not in sys.path:
        sys.path.append(str(_path))

import judge4368_common as common  # noqa: E402
import judge_stage1_r5 as old  # noqa: E402

ATT_LIMIT_DEG = 0.2
P_MOVE_LIMIT_BAR = 180.0
SOIL_READY_ROWS = ("S1", "S2", "S3", "S4", "S5", "S7")
SOIL_READY_LIMIT_S = 100.0
RIGID_RECORD_ROWS = tuple(f"R{i}" for i in range(1, 12))
RIGID_SLOPE_FLAG_S = 120.0
RIGID_FLAT_FLAG_S = 90.0
RETURN_LIMIT_S = 60.0
RIGID_EVENT_ROWS = ("R12", "R14", "R15", "R16")
STEADY_PATH_ROWS = (*RIGID_RECORD_ROWS, *(f"S{i}" for i in range(1, 9)))
PASSING_CLASSES = ("pass", "stroke_limited_stop")
SAFE_STOP_CLASS = "stroke_limited_stop"
S8_ROW = "S8"
FALLBACK_EVENT = "WARN_ROD_PRESSURE_FALLBACK"
GUARD_WARNING = "WARN_LIFT_STROKE_LIMITED:"
SOIL_STOP_FAULT = "FAULT_LIFT_STROKE_LIMIT:soil"
STROKE_END_FAULT = "FAULT_STROKE_END"
EVENT_LIST_CAP = 200
"""``run_v5.run_one`` keeps the first 200 WARN / FAULT / INFO_ROD events."""
JUDGED_SETTING = "VB"
RECORD_SETTINGS = (
    "V1",
    "V2",
    "V3",
    "L1",
    "LS1",
    "LS2",
    "LS3",
    "LS4",
    "V4",
    "V5",
    "V6",
    "V7",
    "V8",
    "L2",
)
LS_SETTINGS = ("LS1", "LS2", "LS3", "LS4")
ITEM8_ORDER = ("R6", "R8", "R9")
"""Criteria 13.1: top, middle, bottom auger level."""
U9_VB_LINES = 28
DEFINITION_CHANGES = tuple(f"D-{n:02d}" for n in range(7, 18))


# ------------------------------------------------------------------------------------ batches
def batch_index() -> dict[str, str]:
    """``run_v5.job_key`` -> batch name for the batches of H-9 / H-10."""
    import run_v5

    index = {}
    for name in ("main", "item8", "overlap", "pressure_only", run_v5.U9_BATCH):
        for job in run_v5.batch_jobs(name):
            index.setdefault(run_v5.job_key(job), name)
    return index


def split_batches(lines: list[dict], index: dict[str, str]) -> dict[str, list[dict]]:
    import run_v5

    out: dict[str, list[dict]] = defaultdict(list)
    for line in lines:
        out[index.get(run_v5.job_key(line["job"]), "unknown")].append(line)
    return out


# ------------------------------------------------------------------------------------ metrics
def event_name_436(name: str) -> str:
    """D-09: the event name without its numeric ':' segments."""
    kept = [part for part in name.split(":") if not _is_number(part)]
    return ":".join(kept)


def _is_number(text: str) -> bool:
    try:
        return math.isfinite(float(text))
    except ValueError:
        return False


def metrics(record: dict, t4h_dirs: tuple[Path, ...]) -> dict:
    """``judge_stage1_r5.metrics`` plus the 436.8 inputs (raw records, not judged values)."""
    out = old.metrics(record)
    values = record["values"]
    events = [(float(t), str(n)) for t, n in record.get("events") or []]
    event_output = record.get("event_output") or {}
    out.update(
        events_full=events,
        events_capped=len(events) >= EVENT_LIST_CAP,
        bad_436=sorted({event_name_436(n) for _, n in events if n.startswith(("WARN", "FAULT"))}),
        fallback_436=sorted(
            {(n, common.control_period_index(t)) for t, n in events if n.startswith(FALLBACK_EVENT)}
        ),
        case_floor=values.get("case_floor_deg"),
        sa4=values.get("sa4"),
        pressure=values.get("pressure") or {},
        controller_tag=record.get("controller_tag"),
        head_only_declared=record.get("head_only_declared"),
        bound_check=(record.get("hydraulics_record") or {}).get("extend_bound_check"),
        rod_reading=rod_reading(record, t4h_dirs),
        F_after_W_min_kN=(
            min(event_output["min_F_after_W_kN"].values())
            if event_output.get("min_F_after_W_kN")
            else None
        ),
    )
    return out


def rod_reading(record: dict, t4h_dirs: tuple[Path, ...]) -> bool | None:
    """R3-C8 1: a finite ``rod_pressure_Pa`` in the line's T4h file; None = no T4h file found."""
    name = record.get("t4h_file")
    if not name:
        return None
    for folder in (
        *t4h_dirs,
        *((Path(record["job"]["t4h_dir"]),) if record["job"].get("t4h_dir") else ()),
    ):
        path = Path(folder) / name
        if path.is_file():
            import numpy as np

            with np.load(path, allow_pickle=False) as data:
                if "rod_pressure_Pa" not in data.files:
                    return None
                return bool(np.isfinite(data["rod_pressure_Pa"]).any())
    return None


# ------------------------------------------------------------------------------------ J items
def _item(item: str, kind: str, detail: str, scatter: bool = False) -> dict:
    """``kind``: ``fail``, ``stop``, ``not_judgeable``, ``flag`` or ``record``."""
    return {"item": item, "kind": kind, "detail": detail, "base_other_phase_has_it": scatter}


def j1_items(base: dict, on: dict, base_all: list[dict]) -> list[dict]:
    """D-07 (event rows: a gate failing in the setting only, as before)."""
    if on["is_event"]:
        return [
            _item("J1", "fail", f"gate {g}", any(g in b["gates"] for b in base_all))
            for g in on["gates"]
            if g not in base["gates"]
        ]
    if on["row"] == S8_ROW:
        if on["class"] != SAFE_STOP_CLASS:
            return [
                _item(
                    "J1", "fail", f"S8 class {on['class']} (criteria 6 expects {SAFE_STOP_CLASS})"
                )
            ]
        return []
    if base["class"] in PASSING_CLASSES and on["class"] not in PASSING_CLASSES:
        return [
            _item(
                "J1",
                "fail",
                f"class {base['class']} -> {on['class']}",
                any(b["class"] not in PASSING_CLASSES for b in base_all),
            )
        ]
    if base["class"] != on["class"] and {base["class"], on["class"]} <= set(PASSING_CLASSES):
        return [_item("J1", "record", f"safe-stop move {base['class']} -> {on['class']}")]
    return []


def _j2_value_N(row: dict) -> float | None:
    if not row["is_event"]:
        return None if row["F_after"] is None else row["F_after"] * 1e3
    is_rigid_event = row["row"] in RIGID_EVENT_ROWS or row["group"].startswith("G4")
    value = row["F_after_W_min_kN"] if is_rigid_event else row["F_after_event"]
    return None if value is None else value * 1e3


def j2_items(base: dict, on: dict, base_all: list[dict]) -> list[dict]:
    """D-08."""
    before, after = _j2_value_N(base), _j2_value_N(on)
    if common.is_at_least(before, common.F_MIN_N) and not common.is_at_least(after, common.F_MIN_N):
        return [
            _item(
                "J2",
                "fail",
                f"F {before} N -> {after} N",
                any(not common.is_at_least(_j2_value_N(b), common.F_MIN_N) for b in base_all),
            )
        ]
    return []


def j3_items(base: dict, on: dict) -> list[dict]:
    """D-11."""
    if on["is_event"]:
        return []
    if on["row"] in SOIL_READY_ROWS:
        is_base_within = base["t_ready"] is not None and not common.is_above(
            base["t_ready"], SOIL_READY_LIMIT_S
        )
        if is_base_within and (
            on["t_ready"] is None or common.is_above(on["t_ready"], SOIL_READY_LIMIT_S)
        ):
            return [_item("J3", "fail", f"t_ready {base['t_ready']} -> {on['t_ready']}")]
        return []
    if on["row"] not in RIGID_RECORD_ROWS:
        return []
    floor = on["case_floor"]
    if floor is None:
        return [_item("J3", "record", "case_floor_deg missing: FLAG limit 미정")]
    limit = RIGID_SLOPE_FLAG_S if any(float(a) != 0.0 for a in floor) else RIGID_FLAT_FLAG_S
    if on["t_ready"] is None or common.is_above(on["t_ready"], limit):
        return [_item("J3", "flag", f"t_ready {on['t_ready']} > {limit} s")]
    return []


def j7_items(base: dict, on: dict, base_all: list[dict]) -> list[dict]:
    """D-09."""
    if base["events_capped"] or on["events_capped"]:
        return [_item("J7", "not_judgeable", "event list cut at 200")]
    items = [
        _item("J7", "fail", name, any(name in b["bad_436"] for b in base_all))
        for name in on["bad_436"]
        if name not in base["bad_436"] and not name.startswith(FALLBACK_EVENT)
    ]
    base_fallback = set(base["fallback_436"])
    items += [
        _item("J7", "fail", f"{name} at period {n}")
        for name, n in on["fallback_436"]
        if (name, n) not in base_fallback
    ]
    return items


def j11_items(on: dict) -> list[dict]:
    """D-10 (rev5 R5-B3: the stop is H-7 for VB, L-e for LS)."""
    lwa = on["lwa"]
    has_fallback = bool((lwa or {}).get("fallback_legs"))
    if lwa is None or lwa.get("n_late") is None:
        if has_fallback:
            return [_item("J11", "not_judgeable", "n_late None with fallback legs")]
        return [_item("J11", "record", "not_computed")]
    late = lwa.get("n_late_fallback")
    if late is None and has_fallback:
        late = sum((lwa.get("n_late_by_leg") or {}).get(leg, 0) for leg in lwa["fallback_legs"])
    if late:
        stop = "L-e" if on["setting"] in LS_SETTINGS else "H-7"
        return [_item("J11", "stop", f"fallback-leg n_late {late} ({stop})")]
    return []


def j_p3_item(on: dict) -> list[dict]:
    """R3-C8 (③ lines only)."""
    import v5_rerun

    from outrigger_sim.hydraulics.v5_options import is_extend_start_tag

    if not is_extend_start_tag(on["controller_tag"]):
        return []
    if on["rod_reading"] is None:
        return [
            _item("J-P3", "not_judgeable", "no T4h rod reading record and no configuration rule")
        ]
    declared = on["head_only_declared"]
    if declared is None:
        declared = (not on["is_event"]) and on["row"] in STEADY_PATH_ROWS
    status = v5_rerun.j_p3_status(
        on["controller_tag"], on["bound_check"], on["rod_reading"], bool(declared)
    )
    if status in ("H-7", "setting_defect"):
        return [_item("J-P3", "stop", status)]
    return [_item("J-P3", "record", status)]


def j_items(base: dict, on: dict, base_all: list[dict], n_rev_max: int) -> list[dict]:
    """All J items of ``on`` against ``base`` (same row, same phase)."""
    items = j1_items(base, on, base_all) + j2_items(base, on, base_all) + j3_items(base, on)
    items += [
        _item(f["item"], "fail", f["detail"], f["base_other_phase_has_it"])
        for f in old.J_fails(base, on, base_all, n_rev_max)
        if f["item"] in ("J4", "J5", "J6", "J8", "J9", "J10")
        and not _s8_j6_not_applicable(f, base, on)
    ]
    return items + j7_items(base, on, base_all) + j11_items(on) + j_p3_item(on)


def _s8_j6_not_applicable(failure: dict, base: dict, on: dict) -> bool:
    """Q-S2: S8 with no READY on both sides has no J6."""
    return (
        failure["item"] == "J6"
        and on["row"] == S8_ROW
        and base["t_ready"] is None
        and on["t_ready"] is None
    )


# ----------------------------------------------------------------------- criteria 6, 11, 13
def sa4_items(row: dict) -> dict:
    """D-14: the seven SA-4 items of one S8 line (None = no record = 판정 불가)."""
    events = row["events_full"]
    warn = [t for t, n in events if n.startswith(GUARD_WARNING)]
    fault = [t for t, n in events if n.startswith(SOIL_STOP_FAULT)]
    sa4 = row["sa4"] or {}
    lifted = sa4.get("lift_after_stop_ms")
    after_lift = row["F_after"]
    items = {
        "same_cycle_warn_fault": bool(warn and fault)
        and common.control_period_index(warn[0]) == common.control_period_index(fault[0]),
        "no_stroke_end": not any(n.startswith(STROKE_END_FAULT) for _, n in events),
        "no_ready": row["t_ready"] is None,
        "F_after_stop_ge_Fmin": f_after_stop_item(sa4, after_lift),
        "no_lift_after_stop": None if lifted is None else all(v == 0 for v in lifted),
        "moving_le_180bar": None
        if row["p_move"] is None
        else not common.is_above(row["p_move"], P_MOVE_LIMIT_BAR),
        "no_saturation": None
        if row["pressure"].get("saturation_leg_chunks") is None
        else row["pressure"]["saturation_leg_chunks"] == 0,
    }
    if row["events_capped"]:
        items["same_cycle_warn_fault"] = items["no_stroke_end"] = None
    state = (
        "판정 불가"
        if any(v is None for v in items.values())
        else ("pass" if all(items.values()) else "fail")
    )
    return {
        "phase": row["phase"],
        "setting": row["setting"],
        "items": items,
        "state": state,
        "pad_force_definition": sa4.get("rule"),
        "F_after_stop_basis": (
            "F-9 F_min_after_stop_N"
            if sa4.get("F_min_after_stop_N") is not None
            else "이륙 뒤 최소(충분조건, F-9 없음)"
        ),
    }


def f_after_stop_item(sa4: dict, after_lift_kN: float | None) -> bool | None:
    """Rev6 R6-C1 1: the F-9 per-leg minimum from the stop to the run end >= F_min on all four
    legs; without F-9 the after-liftoff minimum is a sufficient condition (>= F_min: true,
    else ``판정 불가`` = None)."""
    per_leg = sa4.get("F_min_after_stop_N")
    if per_leg is not None:
        return all(common.is_at_least(v, common.F_MIN_N) for v in per_leg)
    after_lift_N = None if after_lift_kN is None else after_lift_kN * 1e3
    return True if common.is_at_least(after_lift_N, common.F_MIN_N) else None


def fl_guard_period(row: dict) -> int | None | str:
    """Q-S7: integer period of the first guard warning naming FL (``판정 불가`` if cut)."""
    for t, name in row["events_full"]:
        if name.startswith(GUARD_WARNING) and "FL" in name[len(GUARD_WARNING) :].split(","):
            return common.control_period_index(t)
    return common.NOT_JUDGEABLE if row["events_capped"] else None


def h8_s7(rows_by_setting: dict[str, list[dict]]) -> dict:
    """Criteria 11 H-8: VB S7 class or FL guard period differs from V0."""
    v0 = {r["phase"]: r for r in rows_by_setting.get("V0", []) if r["row"] == "S7"}
    out = []
    for row in rows_by_setting.get(JUDGED_SETTING, []):
        if row["row"] != "S7" or row["phase"] not in v0:
            continue
        base = v0[row["phase"]]
        periods = (fl_guard_period(base), fl_guard_period(row))
        undecided = common.NOT_JUDGEABLE in periods
        out.append(
            {
                "phase": row["phase"],
                "class": [base["class"], row["class"]],
                "fl_guard_period": list(periods),
                "state": "판정 불가"
                if undecided
                else (
                    "H-8" if periods[0] != periods[1] or base["class"] != row["class"] else "same"
                ),
            }
        )
    return {
        "rows": out,
        "stop": any(r["state"] == "H-8" for r in out),
        "not_judgeable": any(r["state"] == "판정 불가" for r in out),
    }


def order_131(item8_rows: list[dict], main_rows: list[dict]) -> dict:
    """D-13 / Q-S5 on the after-liftoff minimum force of the four phases."""
    values: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in [*item8_rows, *main_rows]:
        if (
            row["row"] in ITEM8_ORDER
            and row["setting"] in ("V0", JUDGED_SETTING)
            and row["F_after"] is not None
        ):
            values[(row["setting"], row["row"])].append(row["F_after"])
    out = {}
    for setting in ("V0", JUDGED_SETTING):
        stats = [values.get((setting, name)) or [] for name in ITEM8_ORDER]
        if not all(stats):
            out[setting] = {"state": "순서 판정 불가", "reason": "missing phases"}
            continue
        medians = [statistics.median(v) for v in stats]
        ranges = [(min(v), max(v)) for v in stats]
        keeps = (
            medians[0] < medians[1] < medians[2]
            and ranges[0][1] < ranges[1][0]
            and ranges[1][1] < ranges[2][0]
        )
        reverse = (
            medians[0] > medians[1] > medians[2]
            and ranges[0][0] > ranges[1][1]
            and ranges[1][0] > ranges[2][1]
        )
        out[setting] = {
            "medians_kN": medians,
            "ranges_kN": ranges,
            "phases": [len(v) for v in stats],
            "state": "순서 유지" if keeps else ("반대" if reverse else "순서 판정 불가"),
        }
    vb, v0 = out[JUDGED_SETTING]["state"], out["V0"]["state"]
    return {**out, "fail": vb == "반대" and v0 == "순서 유지", "flag": vb == "순서 판정 불가"}


def phase_scatter(off: list[float], on: list[float]) -> dict:
    """``m1_criteria.md`` 5: S = range of the off phases, E = median(on) - median(off)."""
    if not off or not on or len(off) != len(on):
        return {"state": "판정 불가", "phases": [len(off), len(on)]}
    spread = max(off) - min(off)
    effect = statistics.median(on) - statistics.median(off)
    signs = {math.copysign(1.0, b - a) for a, b in zip(off, on, strict=True) if b != a}
    distinct = (
        abs(effect) > spread
        and len(signs) == 1
        and all(b != a for a, b in zip(off, on, strict=True))
    )
    return {
        "S": spread,
        "E": effect,
        "state": "구분됨" if distinct else "위상 산포 안",
        "weak": len(off) == 2,
    }


def l_d(vb_rows: list[dict], ls_rows: list[dict]) -> list[dict]:
    """D-16: per row group the 1 kN / 1 s record and the phase-scatter class (Q-S9)."""

    def force(r):
        return r["F_after_event"] if r["is_event"] else r["F_after"]

    def time(r):
        return r["t_back"] if r["is_event"] else r["t_ready"]

    vb_by = {(r["group"], r["phase"]): r for r in vb_rows}
    groups: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
    for row in ls_rows:
        if (row["group"], row["phase"]) in vb_by:
            groups[row["group"]].append((vb_by[(row["group"], row["phase"])], row))
    out = []
    for name, pairs in sorted(groups.items()):
        entry = {"group": name, "phases": len(pairs)}
        for label, get in (("F_kN", force), ("T_s", time)):
            usable = [
                (get(a), get(b)) for a, b in pairs if get(a) is not None and get(b) is not None
            ]
            entry[label] = phase_scatter([a for a, _ in usable], [b for _, b in usable])
            entry[label]["max_abs_change"] = max((abs(b - a) for a, b in usable), default=None)
        entry["sensitive_record"] = any(
            (entry[k].get("max_abs_change") or 0.0) >= 1.0 or entry[k]["state"] == "위상 산포 안"
            for k in ("F_kN", "T_s")
        )
        out.append(entry)
    return out


# ------------------------------------------------------------------------------------ judging
def _by_setting(rows: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        out[row["setting"]].append(row)
    return out


def j_table(rows_by: dict[str, list[dict]], settings: tuple[str, ...], reference: str) -> dict:
    """J items of every listed setting against ``reference`` (same row, same phase)."""
    base = {(r["row"], r["phase"]): r for r in rows_by.get(reference, [])}
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows_by.get(reference, []):
        groups[row["group"]].append(row)
    n_rev_max = {g: max(r["n_rev"] for r in rs) for g, rs in groups.items()}
    out = {}
    for setting in settings:
        items, missing = [], []
        for row in rows_by.get(setting, []):
            ref = base.get((row["row"], row["phase"]))
            if ref is None:
                missing.append([row["row"], row["phase"]])
                continue
            items += [
                {"row": row["row"], "phase": row["phase"], **i}
                for i in j_items(ref, row, groups[row["group"]], n_rev_max[row["group"]])
            ]
        out[setting] = {
            "runs": len(rows_by.get(setting, [])),
            "no_reference": missing,
            "by_kind": dict(Counter(i["kind"] for i in items)),
            "by_item": dict(Counter(f"{i['item']}:{i['kind']}" for i in items)),
            "items": items[:300],
        }
    return out


def p7(rows_by: dict[str, list[dict]]) -> dict:
    """D-12 / Q-S4."""
    v0 = {(r["row"], r["phase"]): r["sha"] for r in rows_by.get("V0", [])}
    l1 = rows_by.get("L1", [])
    same = [[r["row"], r["phase"]] for r in l1 if v0.get((r["row"], r["phase"])) == r["sha"]]
    return {
        "L1_lines": len(l1),
        "same_hash_as_V0": len(same),
        "keys": same[:60],
        "violation": bool(l1) and len(same) == len(l1),
    }


def judge(args: argparse.Namespace) -> dict:
    index = batch_index()
    t4h_dirs = tuple(Path(p) for p in args.t4h_dir or [])
    lines = {"H-9": common.read_jsonl(args.h9), "H-10": common.read_jsonl(args.h10)}
    errors = {name: [r["job"] for r in rs if "error" in r] for name, rs in lines.items()}
    batches = {
        name: split_batches([r for r in rs if "error" not in r], index)
        for name, rs in lines.items()
    }
    main_rows = [metrics(r, t4h_dirs) for name in lines for r in batches[name].get("main", [])]
    rows_by = _by_setting(main_rows)
    report: dict[str, Any] = {
        "inputs": {
            "h9": str(args.h9),
            "h10": str(args.h10),
            "t4h_dirs": [str(p) for p in t4h_dirs],
        },
        "S-15_counts": {
            name: {
                batch: dict(Counter(r["job"]["setting"] for r in rs))
                for batch, rs in batches[name].items()
            }
            for name in lines
        },
        "errors": {name: len(e) for name, e in errors.items()},
        "P-7": p7(rows_by),
        "J_vs_V0": j_table(rows_by, (JUDGED_SETTING, *RECORD_SETTINGS), "V0"),
        "LS_vs_VB": j_table(rows_by, LS_SETTINGS, JUDGED_SETTING),
        "L-d": {s: l_d(rows_by.get(JUDGED_SETTING, []), rows_by.get(s, [])) for s in LS_SETTINGS},
        "H-8_S7": h8_s7(rows_by),
        "S8_SA4": {
            s: [sa4_items(r) for r in rs if r["row"] == S8_ROW]
            for s, rs in sorted(rows_by.items())
            if any(r["row"] == S8_ROW for r in rs)
        },
        "spec_short_14414p589N": {
            s: [
                {"row": r["row"], "phase": r["phase"], "F_after_kN": r["F_after"]}
                for r in rows_by.get(s, [])
                if not r["is_event"]
                and r["row"].startswith("R")
                and r["F_after"] is not None
                and not common.is_at_least(r["F_after"] * 1e3, common.F_MIN_PLUS_5KN_N)
            ]
            for s in ("V0", JUDGED_SETTING)
        },
    }
    item8 = [metrics(r, t4h_dirs) for r in batches["H-10"].get("item8", [])]
    item8_by = _by_setting(item8)
    report["item8_J"] = j_table(item8_by, (JUDGED_SETTING,), "V0")  # Q-S8
    report["13.1"] = order_131(item8, main_rows)
    overlap = [metrics(r, t4h_dirs) for r in batches["H-10"].get("overlap", [])]
    overlap_by = _by_setting(overlap)
    report["overlap_J"] = j_table(overlap_by, tuple(s for s in overlap_by if s != "V0"), "V0")
    report["overlap_reference"] = (
        None if args.overlap_ref is None else common.read_json(args.overlap_ref)
    )
    u9 = batches["H-10"].get(index_u9_name(), [])
    report["U-9_VB_lines"] = {
        "lines": len(u9),
        "expected": U9_VB_LINES,
        "S-15": len(u9) == U9_VB_LINES,
        "note": "등급은 H-5 (Q-S10)",
    }
    report["pressure_only_finals"] = dict(
        Counter(
            f"{r['job']['setting']}|{r['final_phase']}"
            for r in batches["H-9"].get("pressure_only", [])
        )
    )
    report["unknown_lines"] = {name: len(batches[name].get("unknown", [])) for name in lines}
    report["findings"] = findings_of(report)
    return report


def index_u9_name() -> str:
    import run_v5

    return run_v5.U9_BATCH


def findings_of(report: dict) -> list[str]:
    findings = [f"{name}: {n} error lines" for name, n in report["errors"].items() if n]
    findings += [
        f"{name}: {n} lines of no known batch" for name, n in report["unknown_lines"].items() if n
    ]
    if report["P-7"]["violation"]:
        findings.append("P-7: every L1 line has the V0 hash (H-1)")
    for table in ("J_vs_V0", "LS_vs_VB", "item8_J", "overlap_J"):
        for setting, part in report[table].items():
            kinds = part["by_kind"]
            if kinds.get("stop"):
                findings.append(f"{table} {setting}: {kinds['stop']} stop items")
            if kinds.get("not_judgeable"):
                findings.append(f"{table} {setting}: {kinds['not_judgeable']} 판정 불가 items")
            if setting == JUDGED_SETTING and kinds.get("fail"):
                findings.append(f"{table} VB: {kinds['fail']} J failures (H-2)")
            if part["no_reference"]:
                findings.append(f"{table} {setting}: {len(part['no_reference'])} lines without V0")
    if report["H-8_S7"]["stop"] or report["H-8_S7"]["not_judgeable"]:
        findings.append("H-8: S7 class / FL guard period differs or 판정 불가")
    for setting, rows in report["S8_SA4"].items():
        bad = [r for r in rows if r["state"] != "pass"]
        if bad:
            findings.append(f"S8 SA-4 {setting}: {len(bad)} lines fail or 판정 불가")
    if report["13.1"]["fail"]:
        findings.append("13.1: VB order reversed (H-11)")
    if not report["U-9_VB_lines"]["S-15"]:
        findings.append("S-15: U-9 VB line count")
    return findings


def parser() -> argparse.ArgumentParser:
    out = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    common.add_common_arguments(out)
    out.add_argument("--h9", type=Path, required=True, help="resume_k1/h9_stage1.jsonl")
    out.add_argument("--h10", type=Path, required=True, help="resume_k1/h10_reuse_rerun.jsonl")
    out.add_argument("--t4h-dir", action="append", help="folder of the T4h files (repeatable)")
    out.add_argument("--overlap-ref", type=Path, default=None, help="h10_overlap_t_a.json (record)")
    return out


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return common.run_judge(
        judge,
        args,
        script=Path(__file__).resolve(),
        old_tools=(STAGE1_SCRIPTS / "judge_stage1_r5.py",),
        changes=DEFINITION_CHANGES,
    )


if __name__ == "__main__":
    sys.exit(main())
