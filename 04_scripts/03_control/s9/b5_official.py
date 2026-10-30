"""Official judgement attached to a B5 run (``b5_baseline_compare.py run --official``).

The same judgement path as the R2DS acceptance (``s9_slope_fix_candidates.py``, candidate
``current``):
  slope  ``s9_soil_slope.collect_record`` -> ``judge_case`` (P3 rows with the late-LOC and
         LOC-revoked FLAGs, spec 419.8 / 424.8.1, P3-8 with the spec 377 demotion) ->
         settle check v2 (``s9_settle_rejudge.rejudge_result``, the direct path of a run with
         its settle data)
  g6     ``r72_g6_screen.job`` gates and flags, then the G6-7 FLAG demotion of
         ``r72_judge.py`` (spec 377 ``P3-8_demoted``, U-S9-G6c ``P3-8_preloc_loss``). R2DS
         stored the gates before the demotion; they are kept as ``official_before_p38``.

IND (``control/c8.py`` skeleton) raises none of the C2 events these rows read, so the C2
event rows are ``NA``: P3-2 / G6-2 (LOC), P3-8 / G6-7 (pre-LOC re-approach), SL-3 (LOC
clearance) and RA-* (REANCHOR). ``official_verdict`` judges the remaining rows,
``official_verdict_strict`` counts every NA row as failed.
"""

from __future__ import annotations

import sys

import late_loc_rule
import numpy as np
import s9_settle_rejudge as settle_rejudge
import s9_soil_slope as slope

NA = "NA"
SLOPE_NA_ROWS = ("P3-2", "P3-8", "SL-3")
REANCHOR_ROW_PREFIX = "RA-"
G6_NA_GATES = ("G6-2_loc", "G6-7_preloc")
G6_LOC_FLAGS = (late_loc_rule.G62_FLAG, late_loc_rule.G62_REVOKED_FLAG)
G6_PRELOC_GATE = "G6-7_preloc"
G6_FMIN_GATE = "G6-3_Fmin"
P38_DEMOTED_FLAG = "P3-8_demoted"
P38_PRELOC_LOSS_FLAG = "P3-8_preloc_loss"
P38_UNCHECKED_FLAG = "P3-8_unchecked"
G6_PASS = "pass"
G6_FAIL = "fail"
FAULT_PHASES = ("fault", "fault_reground")


# ---------------------------------------------------------------------------- slope capture
def capture_slope_start(cl, controller) -> None:
    """``s9_soil_slope._make_project_controller`` capture for a controller built elsewhere.

    ``run_case`` builds the controller right after the crawler settle, so the plant state
    here is the settle state the slope judge measures from.
    """
    harness = sys.modules["s9_soil_closed_loop"]
    plant = slope._CAP["plant"]
    slope._CAP["ctrl"] = controller
    slope._CAP["node_d0"] = harness.crawler_node_heights(cl, plant)
    slope._CAP["settle_att_true_deg"] = np.degrees(plant.attitude()).tolist()
    slope._CAP["settle_state"] = slope._settle_state(cl, plant)
    slope._CAP["log"] = {"t_s": [], "phase": [], "fmin_kN": [], "rut_clear_mm": [],
                         "rut_settle_nodes_mm": [], "clear_est_mm": [], "q_floor_deg": [],
                         "sink_mm": [] if plant.soil is not None else None}


# ------------------------------------------------------------------------------ slope judge
def _slope_flags(rows: dict, na_rows: list[str]) -> list[str]:
    """R2DS flags (P3-1, P3-2 as ``s9_slope_fix_candidates._slope_record``) plus the P3-8
    demotion."""
    flags = list(rows["P3-1"].get("flag_names") or [])
    if "P3-2" not in na_rows and rows["P3-2"].get("flag"):
        flags += list(rows["P3-2"].get("flag_names") or [rows["P3-2"]["flag_name"]])
    if "P3-8" not in na_rows and rows["P3-8"].get("flag"):
        flags.append(P38_DEMOTED_FLAG)
    return flags


def _slope_na_rows(rows: dict) -> list[str]:
    return [name for name in rows
            if name in SLOPE_NA_ROWS or name.startswith(REANCHOR_ROW_PREFIX)]


def _slope_verdict(rows: dict, settle: dict, mass_scale: float, failed: set[str]) -> str:
    """``s9_soil_slope`` verdict (``classify`` then the settle check) with the rows in
    ``failed`` forced to fail and the NA rows of ``rows`` left out."""
    na_rows = _slope_na_rows(rows)
    p3 = {}
    for name, row in rows.items():
        is_p3 = name.startswith("P3-") or name == "fault_ready"
        if is_p3 and (name not in na_rows or name in failed):
            p3[name] = {**row, "pass": False} if name in failed else row
    reanchor = {name: {"pass": False} for name in failed if name.startswith(REANCHOR_ROW_PREFIX)}
    stroke = dict(rows["SL-1"])  # classify writes stroke_limited_pass into it
    verdict_rows = slope.classify(p3, stroke, reanchor or None)
    return slope._final_verdict(verdict_rows, settle.get("check"), mass_scale)


def _judged_na_rows(rows: dict, na_rows: list[str]) -> set[str]:
    """NA rows the C2 verdict would judge (a ``pass`` that is not None)."""
    return {name for name in na_rows if rows[name].get("pass") is not None}


def judge_slope(case: dict, out: dict, harness, cl, settle_table: dict, *,
                is_industry: bool) -> dict:
    """Official fields of a slope-harness run.

    Args:
        case: Slope case payload (``SlopeCase.to_dict()``, the one ``slope._CAP["case"]`` holds).
        out: ``run_case`` output.
        harness: The patched ``s9_soil_closed_loop`` module.
        cl: Its first ``_imports()`` module.
        settle_table: Dynamics settle table (``hook_harness``, ``pad_xy_m``).
        is_industry: IND run: the C2 event rows are NA.

    Returns:
        ``official_*`` fields of the b5 record.
    """
    record = slope.collect_record(case, out, harness, cl)
    result = slope._compact(record, slope.judge_case(record))
    result = settle_rejudge.rejudge_result(result, settle_table["hook_harness"],
                                           settle_table["pad_xy_m"])
    rows = result["rows"]
    check = (result.get("settle") or {}).get("check")
    fields = {"official_settle_check_ok": None if check is None else bool(check["ok"]),
              "official_settle_table_status": case.get("settle_table_status")}
    if not is_industry:
        return {**fields, "official_verdict": result["verdict"],
                "official_verdict_strict": result["verdict"],
                "official_failed_rows": list(result["failed_rows"]),
                "official_flags": _slope_flags(rows, []), "official_na_rows": []}
    return {**fields, **industry_slope_fields(rows, result.get("settle") or {},
                                              case.get("mass_scale", 1.0))}


def industry_slope_fields(rows: dict, settle: dict, mass_scale: float = 1.0) -> dict:
    """Official fields of an IND slope run from its judged rows: the C2 event rows NA.

    Args:
        rows: ``judge_case`` rows (P3-*, fault_ready, SL-*, RA-*).
        settle: Settle record with the settle check v2 under ``check`` (None: no table row).
        mass_scale: Plant mass factor of the case (spec 422: the settle check is a record).
    """
    na_rows = _slope_na_rows(rows)
    return {"official_verdict": _slope_verdict(rows, settle, mass_scale, set()),
            "official_verdict_strict": _slope_verdict(rows, settle, mass_scale,
                                                      _judged_na_rows(rows, na_rows)),
            "official_failed_rows": sorted(name for name, row in rows.items()
                                           if row.get("pass") is False and name not in na_rows),
            "official_flags": _slope_flags(rows, na_rows), "official_na_rows": na_rows}


# --------------------------------------------------------------------------------- g6 judge
def demote_preloc_gate(rec: dict) -> tuple[dict, list[str]]:
    """r72 gates with the G6-7 FLAG demotion of ``r72_judge.py`` and the demotion FLAGs.

    G6-7 passes as ``P3-8_demoted`` when every pre-LOC started leg kept its true minimum
    >= F_min (spec 377), or as ``P3-8_preloc_loss`` when it did not but G6-3 holds and the run
    has no FAULT (U-S9-G6c); a record without the pre-LOC check stays failed
    (``P3-8_unchecked``).
    """
    gates = dict(rec["gates"])
    if gates.get(G6_PRELOC_GATE, True):
        return gates, []
    flag_ok = rec.get("preloc_flag_ok")
    has_fault = rec.get("final_phase") in FAULT_PHASES
    if flag_ok is True:
        gates[G6_PRELOC_GATE] = True
        return gates, [P38_DEMOTED_FLAG]
    if flag_ok is False and gates.get(G6_FMIN_GATE) and not has_fault:
        gates[G6_PRELOC_GATE] = True
        return gates, [P38_PRELOC_LOSS_FLAG]
    if flag_ok is None:
        return gates, [P38_UNCHECKED_FLAG]
    return gates, []


def _g6_verdict(gates: dict) -> str:
    return G6_PASS if all(gates.values()) else G6_FAIL


def _failed_gates(gates: dict) -> list[str]:
    return [name for name, is_pass in gates.items() if not is_pass]


def judge_g6(rec: dict, *, is_industry: bool) -> dict:
    """Official fields of a g6-harness run from its ``r72_g6_screen.job`` record.

    Raises:
        RuntimeError: The r72 job reported an error.
    """
    if "error" in rec:
        raise RuntimeError(f"r72 job failed: {rec['error']}\n{rec.get('tb', '')}")
    raw_gates = rec["gates"]
    before_p38 = {"verdict": _g6_verdict(raw_gates), "failed_rows": _failed_gates(raw_gates)}
    flags = list(rec.get("flags") or [])
    if not is_industry:
        gates, p38_flags = demote_preloc_gate(rec)
        return {"official_verdict": _g6_verdict(gates), "official_verdict_strict":
                _g6_verdict(gates), "official_failed_rows": _failed_gates(gates),
                "official_flags": flags + p38_flags, "official_na_rows": [],
                "official_before_p38": before_p38}
    judged = {name: is_pass for name, is_pass in raw_gates.items() if name not in G6_NA_GATES}
    na_gates = [name for name in raw_gates if name in G6_NA_GATES]
    strict = {**judged, **dict.fromkeys(na_gates, False)}
    return {"official_verdict": _g6_verdict(judged), "official_verdict_strict": _g6_verdict(strict),
            "official_failed_rows": _failed_gates(judged),
            "official_flags": [flag for flag in flags if flag not in G6_LOC_FLAGS],
            "official_na_rows": na_gates, "official_before_p38": before_p38}
