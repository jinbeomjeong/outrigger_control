"""Path-2 recount of the v5 J items on run_v5 harness lines, and of H-5 (U-9 V0) for the 436.8 v5 resume.

Rules: v5 criteria ``v5_criteria.md`` + revisions 1~12b (appendix A of the 436.8 rules), read through the
436.8 rules (tags 4.1, 7.1). H-5: ``u9_targeted_rules_rev1.md`` (644005b7...) with the 436.8 7.1 tag reading
(``final_C4G2`` -> ``final_C4G2_LAS_K1``, ``final_C4G2_P3`` -> ``final_C4G2_P3_LAS_K1``), and the 436.8 rev3
(dad8dfa6...) R3-C1~C8: H0 reference = H-10 main VB line (C1); 436.8 grade = eta 0.85 T1 + H0, eta 0.80 and the
4.1 class are records (C2); J1 pass <-> stroke_limited_stop is a record except S8 (C3); spec-shortfall mark at
F_min + 5 kN (C4); J3 slope by the row's floor angle (C5); J7 names without numeric segments (C6); J11 n_late
None on a fallback line = undecidable (C7); J-P3 inputs by T4h, else configuration, never by inverting the
declaration (C8); rev4 (7ea87a30...) R4-C5: floor angle from ``values.case_floor_deg`` (F-3); rev5 (452a8436...) R5-B3: LS J11 fallback n_late > 0 = L-e.
436.8 rev11 (9bac4524...) R11-2 (``u9``): the T4h of a VB line is looked up only in the runner convention
folders of its ``--vb`` file (``<stem>_t4h/``, ``t4h/``); one ``--t4h-root`` only when no convention folder
exists (else, or two or more, input error S-11, exit 2); the recorded ``t4h_file`` found 0 or 2+ times = S-2.
Author: dynamics-expert (path 2, second author of the 436.8 path 2). Path-1 tools and outputs were not opened
(436.8 9.2); the J-item reading below is built from the rule sentences and the line field names only.

J items (v5 criteria 3, rev2 2.1, rev8 3.2, rev9 3; one line = one row x phase x setting, paired with the
V0 line of the same job without the setting keys):
  J1  pass -> fail: steady rows ``harness_class``; event rows ``event_output.pass``
  J2  min force: steady ``values.forces.after_liftoff.min_kN`` >= F_min; rigid event rows (3.1)
      ``event_output.after_window_force.min_1ms_kN`` >= F_min (soil event rows: trailing 0.5 s mean >= F_min
      and lift-off 0 after the window)
  J3  first READY (7): S1~S5, S7 <= 100 s (judged); rigid R* recorded (FLAG over 90 s flat / 120 s slope)
  J4  ``final_phase`` equals V0 when V0 is ``ready``
  J5  event rows: ``event_output.t_ready_back_s`` present and <= 60 s
  J6  steady ``values.attitude.max_abs_last_5s_deg`` <= 0.2 deg; event ``max|event_output.att_end_deg|`` <= 0.2
  J7  new FAULT / WARN names and new fallback reasons (``INFO_ROD_PRESSURE_FAULT_REASON:<leg>:<D>``) vs V0
  J8  ``command_stats.n_rev`` >= 2 n_off_max and >= n_off_max + 6 (n_off_max = V0 max over the row's phases)
  J9  ``hydraulics_record.m2_clipped_steps_post_lift`` > 0 -> stop (H-9)
  J10 moving pressure: steady ``values.pressure.max_moving_bar`` <= 180; event
      ``event_output.pressure.moving_outside_max_bar`` <= 180
  J11 ``lock_window_alignment.n_late_fallback`` > 0 -> stop (H-7); n_late recorded
  J-P3 (VB / LS, ③ by ``is_extend_start_tag``): rev9 3.2 table on ``hydraulics_record.extend_bound_check``

Exit codes: 0 nothing failed, stopped or undecidable; 1 a fail or an undecidable item; 2 a stop (H-*, S-*)
or a rules sha mismatch; 3 tool error. Last stdout line: JSON summary with ``tool_sha256`` / ``out_sha256``.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import json
import sys
import traceback
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("p2_4368_core", _HERE / "p2_4368.py")
core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)

TOOL_NAME = "p2_v5j.py"
TOOL_VERSION = "1"
_VM = "06_analysis/02_control/verif_matrix/"
U9_RULES = {_VM + "u9_targeted_rules_rev1.md": "644005b706ba46cebba11b975ded474226cc4eab5030ee18e9f91dacd2d14587"}

F_MIN_KN = core.F_MIN_N / 1000.0        # 436.8 2 (YAML 9,414.589 N); v5 criteria table writes 9.415 kN
SPEC_RIGID_KN = (core.F_MIN_N + 5000.0) / 1000.0   # rev3 R3-C4: "14.415 kN" = F_min + 5 kN (record)
ATT_LIMIT_DEG = 0.2                     # J6
MOVING_BAR = 180.0                      # J10
READY_BACK_S = 60.0                     # J5
READY_SOIL_S = 100.0                    # 7 (S1~S5, S7)
READY_FLAT_S, READY_SLOPE_S = 90.0, 120.0   # 7 (rigid R*, FLAG only)
SOIL_READY_CASES = {"S1", "S2", "S3", "S4", "S5", "S7"}
RIGID_EVENT_CASES = {"R12", "R14", "R15", "R16"}   # 3.1 / rev3 R3-C4 rigid events (G4 width grid = R12 twins)
STEADY_CASES = {f"R{i}" for i in range(1, 12)} | {f"S{i}" for i in range(1, 9)}   # rev9 3.1 / rev3 R3-C8
FLOOR_LIST_PATH = "values.case_floor_deg"            # rev4 R4-C5 / F-3: [roll, pitch] deg
FLOOR_ANGLE_PATHS = (("job.d1.roll_deg", "job.d1.pitch_deg"),)   # D-1 lines (R4-C5)
NREV_FACTOR, NREV_ADD = 2, 6            # 4 (assumption in the criteria)
PAIR_DROP = ("setting", "eta_v", "u9_metrics", "mask", "t4h_dir")
PHASE_KEYS = ("eps", "offset_s")
OK_CLASSES = {"pass", "stroke_limited_stop"}

# U-9 (u9 rules rev1 2, 4)
U9_KEYS = {("S2", 0.0), ("S2", 0.001), ("S2", 0.002), ("S2", 0.003), ("S3", 0.0), ("S3", 0.002),
           ("R3", 0.0), ("R3", 0.001), ("R3", 0.002), ("R3", 0.003),
           ("S5", 0.0), ("S5", 0.001), ("S5", 0.002), ("S5", 0.003)}
U9_H0 = {("S2", 0.002), ("S3", 0.0), ("R3", 0.0), ("S5", 0.0)}
ETA_BASE, ETA_LOW = 0.85, 0.80
T3A_DEG, T3B_DEG, T3C_DEG = 0.10, 0.05, 0.10
T4_FLOOR_S, T4_ADD_S = 20.0, 5.0
AB_LONGEST_S = 0.5


# ----------------------------------------------------------------- line helpers
def pair_key(job):
    """Key of the V0 partner: the job without the setting keys (sorted JSON)."""
    j = {k: v for k, v in job.items() if k not in PAIR_DROP}
    return json.dumps(j, sort_keys=True, separators=(",", ":"))


def row_key(job):
    """Row key for the J8 phase maximum: the pair key without the phase keys."""
    j = {k: v for k, v in job.items() if k not in PAIR_DROP + PHASE_KEYS}
    return json.dumps(j, sort_keys=True, separators=(",", ":"))


def is_event(line):
    return line.get("t_event_s") is not None or isinstance(core.dig(line, "event_output.pass", None), bool)


def case_of(line):
    return core.dig(line, "job.case", None)


def tag_of(line):
    v, _ = core.first_path(line, core.TAG_PATHS)
    return None if v is core.MISSING else v


def _is_number(seg):
    try:
        float(seg)
        return True
    except ValueError:
        return False


def floor_slope(line):
    """rev3 R3-C5 / rev4 R4-C5: True if the case floor angle is non-zero, False if both zero, None if not
    recorded (``values.case_floor_deg``, else the D-1 ``job.d1`` angles)."""
    fl = core.dig(line, FLOOR_LIST_PATH, None)
    if isinstance(fl, (list, tuple)) and len(fl) == 2 and all(core.num(x) is not None for x in fl):
        return core.num(fl[0]) != 0.0 or core.num(fl[1]) != 0.0
    for pr, pp in FLOOR_ANGLE_PATHS:
        r, p = core.num(core.dig(line, pr, None)), core.num(core.dig(line, pp, None))
        if r is not None and p is not None:
            return r != 0.0 or p != 0.0
    return None


def names_of(line):
    """(FAULT/WARN name set, fallback reason set, fallback times) from ``events`` [[t, name], ...]
    plus the value lists (steady ``values.events``, event ``event_output``)."""
    names, reasons, fb_times = set(), set(), {}
    raw = []
    for e in line.get("events") or []:
        if isinstance(e, (list, tuple)) and len(e) == 2 and isinstance(e[1], str):
            raw.append((core.num(e[0]), e[1]))
    for p in ("values.events.fault_events", "values.events.warn_events", "event_output.fault_events",
              "event_output.warnings"):
        v = core.dig(line, p, None)
        if isinstance(v, list):
            raw.extend((None, s) for s in v if isinstance(s, str))
    for t, s in raw:
        base = s.partition(":")[0]
        if base.startswith("FAULT_") or base.startswith("WARN_"):
            # rev3 R3-C6: the name = the ':' segments without the numeric ones (leg / reason segments stay)
            s = ":".join(seg for seg in s.split(":") if not _is_number(seg))
            names.add(s)
            if base == "WARN_ROD_PRESSURE_FALLBACK" and t is not None:
                fb_times.setdefault(s, []).append(t)
        elif base == "INFO_ROD_PRESSURE_FAULT_REASON":
            reasons.add(s)
    return names, reasons, fb_times


def j_values(line):
    """The values the J items compare (None = missing)."""
    ev = is_event(line)
    d = {"event": ev, "final_phase": line.get("final_phase"), "n_rev": core.num(core.dig(line, "command_stats.n_rev", None))}
    if ev:
        d["ok1"] = core.dig(line, "event_output.pass", None)
        d["minF"] = core.num(core.dig(line, "event_output.after_window_force.min_1ms_kN", None))
        d["minF_0p5"] = core.num(core.dig(line, "event_output.after_window_force.min_trailing_0p5s_kN", None))
        d["lift_after"] = core.num(core.dig(line, "event_output.after_window_force.lift_ms_after_window", None))
        att = core.dig(line, "event_output.att_end_deg", None)
        d["att"] = (max(abs(core.num(a)) for a in att) if isinstance(att, list) and att
                    and all(core.num(a) is not None for a in att) else None)
        d["press"] = core.num(core.dig(line, "event_output.pressure.moving_outside_max_bar", None))
        d["ready_back"] = core.num(core.dig(line, "event_output.t_ready_back_s", None))
    else:
        d["ok1"] = line.get("harness_class")
        d["minF"] = core.num(core.dig(line, "values.forces.after_liftoff.min_kN", None))
        d["att"] = core.num(core.dig(line, "values.attitude.max_abs_last_5s_deg", None))
        d["press"] = core.num(core.dig(line, "values.pressure.max_moving_bar", None))
    d["t_ready"] = core.num(core.dig(line, "values.times.t_first_ready_s", None))
    return d


def ok_j1(v):
    if v["event"]:
        return v["ok1"] if isinstance(v["ok1"], bool) else None
    return None if v["ok1"] is None else (v["ok1"] in OK_CLASSES)


def ok_j2(v, case):
    if v["event"] and case not in RIGID_EVENT_CASES:
        # soil fast event (3.1): trailing 0.5 s mean >= F_min and no lift after the window
        if v.get("minF_0p5") is None or v.get("lift_after") is None:
            return None
        return core.t_ge(v["minF_0p5"], F_MIN_KN) and v["lift_after"] == 0
    return None if v["minF"] is None else core.t_ge(v["minF"], F_MIN_KN)


def ready_limit(case, line=None):
    """(limit, kind, slope). rev3 R3-C5: rigid R* FLAG limit 120 s if the row's floor angle is non-zero."""
    if case in SOIL_READY_CASES:
        return READY_SOIL_S, "judged", None
    if isinstance(case, str) and case.startswith("R"):
        slope = floor_slope(line) if line is not None else None
        if slope is None:
            return None, "flag_unknown_floor", None
        return (READY_SLOPE_S if slope else READY_FLAT_S), "flag", slope
    return None, None, None


def rod_reading_by_config(line):
    """rev3 R3-C8 1: without a T4h record, the run configuration decides (event path = two pressures)."""
    if is_event(line):
        return True
    if case_of(line) in STEADY_CASES:
        return False
    return None


def head_only_declared(line):
    """rev3 R3-C8 2: the line field, else the rev9 3.1 configuration (steady path cases)."""
    v = line.get("head_only_declared")
    if isinstance(v, bool):
        return v, "field"
    return (case_of(line) in STEADY_CASES and not is_event(line)), "configuration"


def jp3(line, is_p3, rod_reading):
    """rev9 3.2 table with the two inputs of rev3 R3-C8 (rod reading: T4h, else configuration; declaration:
    field, else configuration; the declaration is never inverted into a rod-reading assumption)."""
    tag = tag_of(line)
    if is_p3 is None or not isinstance(tag, str) or not is_p3(tag):
        return "not_applicable_tag", None
    hr = line.get("hydraulics_record") if isinstance(line.get("hydraulics_record"), dict) else None
    ebc = hr.get("extend_bound_check", core.MISSING) if hr is not None else core.MISSING
    declared, _src = head_only_declared(line)
    rod = rod_reading if rod_reading is not None else rod_reading_by_config(line)
    if rod is None:
        return "undecidable", "no T4h record and no configuration basis for the rod reading (R3-C8)"
    if rod:
        if not isinstance(ebc, dict):
            return "setting_defect", "#2 rod reading, extend_bound_check missing / null"
        br = ebc.get("breach_reads")
        if not (isinstance(br, list) and all(isinstance(x, int) for x in br)):
            return "setting_defect", "breach_reads unreadable"
        return ("pass", None) if sum(br) == 0 else ("H-7", f"ext_moving breach_reads {br}")
    if not declared:
        return "setting_defect", "#4 no rod reading without a head-only declaration"
    if isinstance(ebc, dict):
        return "setting_defect", "#5 no rod reading but a record"
    return "no_rod_reading", None


def judge_pair(line, v0, v0_nrev_max, is_p3, rod_reading=None):
    """J1~J11 + J-P3 of one setting line against its V0 partner. Returns (items, fnd)."""
    fnd = core.Findings()
    where = core.job_key(line.get("job"))
    case = case_of(line)
    a, b = j_values(v0), j_values(line)
    it = {}

    def rel(name, ok0, ok1, record=None):
        if ok0 is None or ok1 is None:
            it[name] = {"result": "undecidable", "v0": ok0, "set": ok1, **(record or {})}
            fnd.undec(where, f"{name}: value missing (9.3)")
        elif ok0 and not ok1:
            it[name] = {"result": "fail", "v0": ok0, "set": ok1, **(record or {})}
            fnd.fail(where, f"{name}: V0 ok, setting not")
        else:
            it[name] = {"result": "pass" if ok1 else "baseline_fail", "v0": ok0, "set": ok1, **(record or {})}

    rel("J1", ok_j1(a), ok_j1(b), {"class_v0": a["ok1"], "class_set": b["ok1"]})
    if not b["event"] and a["ok1"] in OK_CLASSES and b["ok1"] in OK_CLASSES and a["ok1"] != b["ok1"]:
        # rev3 R3-C3: pass <-> stroke_limited_stop is a record, except the S8 row whose expected class is
        # stroke_limited_stop (v5 criteria 6: leaving that class is a J1 fail)
        if case == "S8" and a["ok1"] == "stroke_limited_stop":
            it["J1"]["result"] = "fail"
            fnd.fail(where, f"J1: S8 class {a['ok1']} -> {b['ok1']}")
        else:
            it["J1"]["safe_stop_move"] = f"{a['ok1']} -> {b['ok1']}"
    rel("J2", ok_j2(a, case), ok_j2(b, case), {"minF_v0_kN": a["minF"], "minF_set_kN": b["minF"]})
    if not b["event"] and isinstance(case, str) and case.startswith("R") and b["minF"] is not None \
            and core.t_lt(b["minF"], SPEC_RIGID_KN):
        it["J2"]["spec_shortfall"] = True        # "사양 미달" record
    lim, kind, slope = ready_limit(case, line)
    if b["event"]:
        it["J3"] = {"result": "record", "t_ready_v0": a["t_ready"], "t_ready_set": b["t_ready"]}
    elif case == "S8":
        it["J3"] = {"result": "pass" if b["t_ready"] is None else "fail", "rule": "S8 READY 0"}
        if b["t_ready"] is not None:
            fnd.fail(where, "J3: S8 reached READY")
    elif kind == "flag_unknown_floor":
        it["J3"] = {"result": "record", "t_ready_set": b["t_ready"],
                    "slope": "판정 불가", "flag_limit": "미정",
                    "why": "rigid row without values.case_floor_deg: FLAG limit (90 / 120 s) not set (R4-C5)"}
    elif lim is None:
        it["J3"] = {"result": "record", "t_ready_set": b["t_ready"], "why": "no READY limit for this case"}
    elif kind == "judged":
        ok0 = a["t_ready"] is not None and not core.t_gt(a["t_ready"], lim)
        ok1 = b["t_ready"] is not None and not core.t_gt(b["t_ready"], lim)
        rel("J3", ok0, ok1, {"limit_s": lim, "t_ready_v0": a["t_ready"], "t_ready_set": b["t_ready"]})
    else:
        flag = b["t_ready"] is not None and core.t_gt(b["t_ready"], lim)
        it["J3"] = {"result": "flag" if flag else "record", "limit_s": lim, "floor_slope": slope,
                    "t_ready_set": b["t_ready"]}
    fp0, fp1 = a["final_phase"], b["final_phase"]
    if fp0 is None or fp1 is None:
        it["J4"] = {"result": "undecidable"}
        fnd.undec(where, "J4: final_phase missing")
    elif fp0 == "ready" and fp1 != "ready":
        it["J4"] = {"result": "fail", "v0": fp0, "set": fp1}
        fnd.fail(where, f"J4: V0 ready, setting {fp1}")
    else:
        it["J4"] = {"result": "pass", "v0": fp0, "set": fp1, "same": fp0 == fp1}
    if b["event"]:
        ok0 = a.get("ready_back") is not None and not core.t_gt(a["ready_back"], READY_BACK_S)
        ok1 = b.get("ready_back") is not None and not core.t_gt(b["ready_back"], READY_BACK_S)
        rel("J5", ok0, ok1, {"v0_s": a.get("ready_back"), "set_s": b.get("ready_back")})
    else:
        it["J5"] = {"result": "not_applicable"}
    ok = (lambda x: None if x is None else not core.t_gt(x, ATT_LIMIT_DEG))
    rel("J6", ok(a["att"]), ok(b["att"]), {"v0_deg": a["att"], "set_deg": b["att"]})
    n0, r0, t0 = names_of(v0)
    n1, r1, t1 = names_of(line)
    new_n, new_r = sorted(n1 - n0), sorted(r1 - r0)
    fb_time_diff = sorted(k for k in set(t0) | set(t1) if sorted(t0.get(k, [])) != sorted(t1.get(k, [])))
    it["J7"] = {"result": "fail" if (new_n or new_r) else "pass", "new_names": new_n, "new_reasons": new_r,
                "fallback_time_differs": fb_time_diff}
    if new_n or new_r:
        fnd.fail(where, f"J7: new {new_n + new_r}")
    if b["n_rev"] is None or v0_nrev_max is None:
        it["J8"] = {"result": "undecidable"}
        fnd.undec(where, "J8: n_rev missing")
    else:
        lc = b["n_rev"] >= NREV_FACTOR * v0_nrev_max and b["n_rev"] >= v0_nrev_max + NREV_ADD
        it["J8"] = {"result": "fail" if lc else "pass", "n_rev": b["n_rev"], "n_off_max": v0_nrev_max,
                    "increase": b["n_rev"] > v0_nrev_max}
        if lc:
            fnd.fail(where, "J8: limit cycle suspected (H-4)")
    hr = line.get("hydraulics_record") if isinstance(line.get("hydraulics_record"), dict) else {}
    m2_on = isinstance(core.dig(line, "hydraulic_options.m2_law", None), str)
    post = hr.get("m2_clipped_steps_post_lift")
    if not m2_on:
        it["J9"] = {"result": "not_applicable", "why": "M2 off"}
    elif not (isinstance(post, list) and all(isinstance(x, int) for x in post)):
        it["J9"] = {"result": "undecidable"}
        fnd.undec(where, "J9: m2_clipped_steps_post_lift missing")
    else:
        it["J9"] = {"result": "stop" if sum(post) else "pass", "post_lift": post,
                    "pre_lift": hr.get("m2_clipped_steps_pre_lift")}
        if sum(post):
            fnd.stop("H-9", where, f"m2_clipped_steps_post_lift {post}")
    okp = (lambda x: None if x is None else not core.t_gt(x, MOVING_BAR))
    rel("J10", okp(a["press"]), okp(b["press"]), {"v0_bar": a["press"], "set_bar": b["press"]})
    lwa = line.get("lock_window_alignment")
    has_fb = any(n.startswith("WARN_ROD_PRESSURE_FALLBACK") for n in n1)
    if isinstance(lwa, dict) and lwa.get("n_late_fallback") is None and lwa.get("n_late") is None and has_fb:
        # rev3 R3-C7: a fallback leg with n_late None -> the J11 stop condition cannot be checked
        it["J11"] = {"result": "undecidable", "why": "fallback leg present, n_late None"}
        fnd.undec(where, "J11: fallback leg present but n_late missing (R3-C7)")
    elif not isinstance(lwa, dict):
        lc_on = isinstance(core.dig(line, "hydraulic_options.lock_closure", None), dict)
        it["J11"] = {"result": "undecidable" if lc_on else "not_applicable"}
        if lc_on:
            fnd.undec(where, "J11: lock_window_alignment missing")
    else:
        nlf = lwa.get("n_late_fallback")
        if "n_late_fallback" not in lwa and lwa.get("n_late") is None and isinstance(lwa.get("reason"), str):
            # the line records why no window was aligned (steady path: "no rod reading" = no fallback leg)
            it["J11"] = {"result": "not_computed", "reason": lwa["reason"]}
        elif not isinstance(nlf, int):
            it["J11"] = {"result": "undecidable"}
            fnd.undec(where, "J11: n_late_fallback missing")
        else:
            it["J11"] = {"result": "stop" if nlf else "pass", "n_late_fallback": nlf,
                         "n_late_by_leg": lwa.get("n_late_by_leg")}
            if nlf:   # rev5 R5-B3: on LS rows the same violation is L-e (v5 criteria 8), on VB rows H-7
                code = "L-e" if str(core.dig(line, "job.setting", "")).startswith("LS") else "H-7"
                fnd.stop(code, where, f"n_late_fallback {nlf}")
    res, why = jp3(line, is_p3, rod_reading)
    it["J-P3"] = {"result": res, "why": why, "rod_reading_source": "t4h" if rod_reading is not None else "configuration",
                  "declaration_source": head_only_declared(line)[1]}
    if res == "undecidable":
        fnd.undec(where, f"J-P3: {why}")
    elif res == "H-7":
        fnd.stop("H-7", where, f"J-P3 {why}")
    elif res == "setting_defect":
        fnd.stop("J-P3-defect", where, why)
    return it, fnd


def rod_reading_from_t4h(line, t4h_root):
    """rev9 3.1: a T4h record with any finite ``rod_pressure_Pa`` = rod reading. None if no file."""
    if t4h_root is None or not isinstance(line.get("t4h_file"), str):
        return None
    p = Path(t4h_root) / line["t4h_file"]
    if not p.is_file():
        return None
    import numpy as np   # noqa: PLC0415 (numpy only for npz)
    with np.load(p, allow_pickle=False) as z:
        if "rod_pressure_Pa" not in z.files:
            return None
        a = np.asarray(z["rod_pressure_Pa"], dtype=float)
        return bool(np.isfinite(a).any())


def _rod_reading_file(p):
    import numpy as np   # noqa: PLC0415 (numpy only for npz)
    with np.load(p, allow_pickle=False) as z:
        if "rod_pressure_Pa" not in z.files:
            return None
        a = np.asarray(z["rod_pressure_Pa"], dtype=float)
        return bool(np.isfinite(a).any())


def t4h_convention_dirs(result_file):
    """436.8 rev11 R11-2 1: the runner convention folders of one result file: ``<stem>_t4h/`` and ``t4h/``
    next to it (only those that exist)."""
    p = Path(result_file)
    return [d for d in (p.with_name(p.stem + "_t4h"), p.parent / "t4h") if d.is_dir()]


def t4h_places(result_files, given):
    """rev11 R11-2 1 / 2: search folders per result file. Another folder only when no result file has a
    convention folder, and at most one. Returns ({file: [dirs]}, None) or (None, input-error reason)."""
    given = list(given or [])
    if len(given) > 1:
        return None, f"{len(given)} T4h folders given (R11-2 2: at most one)"
    places = {str(f): t4h_convention_dirs(f) for f in result_files}
    if given and any(places.values()):
        return None, "a T4h folder given while a runner convention folder exists (R11-2 2)"
    if given:
        places = {k: [Path(given[0])] for k in places}
    return places, None


def rod_reading_lookup(line, dirs):
    """rev11 R11-2 3: the recorded ``t4h_file`` must be found exactly once in ``dirs``.
    (reading, status, hits): status ``no_t4h_file`` (line without the field: configuration, R3-C8),
    ``ok``, ``not_found`` / ``several`` (S-2)."""
    name = line.get("t4h_file")
    if not isinstance(name, str):
        return None, "no_t4h_file", []
    hits = [d / name for d in dict.fromkeys(dirs) if (d / name).is_file()]
    if len(hits) != 1:
        return None, ("not_found" if not hits else "several"), [str(h) for h in hits]
    return _rod_reading_file(hits[0]), "ok", [str(hits[0])]


def nrev_max_by_row(v0_lines):
    out = {}
    for ln in v0_lines:
        n = core.num(core.dig(ln, "command_stats.n_rev", None))
        if n is None:
            continue
        rk = row_key(ln["job"])
        out[rk] = max(out.get(rk, n), n)
    return out


# ----------------------------------------------------------------- H-5 (U-9)
def u9_key(job):
    return (job.get("case"), round(float(job.get("eps", 0.0)), 6))


def recount_u9(v0_lines, vb_lines, h0_ref_lines, is_p3, stored_main=None, stored_p3=None, t4h_root=None,
               t4h_lookup=None):
    """``t4h_lookup(line)`` -> (reading, status, hits) is the rev11 R11-2 search (main); without it the
    single ``t4h_root`` folder of the earlier sheets is read (kept for library callers)."""
    fnd = core.Findings()
    t4h_log = {"ok": 0, "no_t4h_file": 0, "not_found": 0, "several": 0}

    def rod(ln, where):
        if t4h_lookup is None:
            return rod_reading_from_t4h(ln, t4h_root)
        val, st, hits = t4h_lookup(ln)
        t4h_log[st] += 1
        if st in ("not_found", "several"):
            fnd.stop("S-2", where, f"R11-2: T4h {ln.get('t4h_file')!r} {st} in the convention / given folder(s) {hits}")
        return val
    v0 = {}
    for ln in v0_lines:
        k = u9_key(ln["job"])
        if k in v0:
            fnd.stop("S-15", f"V0 {k}", "duplicate key")
        v0[k] = ln
        if ln["job"].get("setting") != "V0":
            fnd.stop("S-2", f"V0 {k}", f"setting {ln['job'].get('setting')!r} in the V0 file")
        if tag_of(ln) != core.TAG_V0:
            fnd.stop("S-2", f"V0 {k}", f"tag {tag_of(ln)!r} != {core.TAG_V0!r} (7.1 tag reading)")
    vb = {ETA_BASE: {}, ETA_LOW: {}}
    for ln in vb_lines:
        e = core.num(ln["job"].get("eta_v"))
        k = u9_key(ln["job"])
        eta = ETA_BASE if e is not None and abs(e - ETA_BASE) < 1e-9 else (ETA_LOW if e is not None and abs(e - ETA_LOW) < 1e-9 else None)
        if eta is None:
            fnd.stop("S-15", f"VB {k}", f"eta_v {e!r} not in (0.85, 0.80)")
            continue
        if k in vb[eta]:
            fnd.stop("S-15", f"VB {k} eta {eta}", "duplicate key")
        vb[eta][k] = ln
        if tag_of(ln) != core.TAG_VB:
            fnd.stop("S-2", f"VB {k} eta {eta}", f"tag {tag_of(ln)!r} != {core.TAG_VB!r}")
    for name, d in (("V0", v0), ("VB0.85", vb[ETA_BASE]), ("VB0.80", vb[ETA_LOW])):
        if set(d) != U9_KEYS:
            fnd.stop("S-15", name, f"{len(d)} keys; missing {sorted(U9_KEYS - set(d))}, extra {sorted(set(d) - U9_KEYS)}")
    # H0 (4: before judging). (1) hash = reference line of the same (case, eps); (2) others vs main VB (record)
    h0 = {"checked": [], "record_main": [], "record_stored_p3": []}
    ref = {}
    for ln in h0_ref_lines or []:
        j = ln.get("job") or {}
        if j.get("setting") == "VB" and "eta_v" not in j and not j.get("u9_metrics"):
            ref.setdefault(u9_key(j), []).append(ln)
    for k in sorted(U9_KEYS):
        ln = vb[ETA_BASE].get(k)
        if ln is None:
            continue
        if k in U9_H0:
            cands = ref.get(k, [])
            if not cands:
                h0["checked"].append({"key": list(k), "result": "no_reference"})
                fnd.stop("U9-H0", str(k), "no reference VB line for H0 (1)")
                continue
            same = cands[0].get("commands_sha256") == ln.get("commands_sha256")
            h0["checked"].append({"key": list(k), "result": "same" if same else "different",
                                  "ref_job": cands[0].get("job")})
            if not same:
                fnd.stop("U9-H0", str(k), "commands_sha256 differs from the reference VB line (H0 (1))")
        for src, store, tag in ((stored_main, h0["record_main"], "main"), (stored_p3, h0["record_stored_p3"], "p3_hash")):
            if not src:
                continue
            hit = [x for x in src if (x.get("job") or {}).get("setting") == "VB" and u9_key(x["job"]) == k]
            if hit:
                store.append({"key": list(k), "same": hit[0].get("commands_sha256") == ln.get("commands_sha256")})
    nmax = nrev_max_by_row(list(v0.values()))
    keys = []
    cls_flags = {"cause_fail": [], "baseline_or_v0_fail": [], "T3a": [], "T3b": [], "T3c": [], "T4": [],
                 "T4_flag_integral": []}
    longest_ge3 = []
    rec080 = {"stops": [], "undecidable": []}
    for k in sorted(U9_KEYS):
        l0, lb, ll = v0.get(k), vb[ETA_BASE].get(k), vb[ETA_LOW].get(k)
        if l0 is None or lb is None or ll is None:
            continue
        where = f"{k[0]}|eps {k[1]}"
        rmax = nmax.get(row_key(l0["job"]))
        rb = rod(lb, f"VB0.85 {where}")
        rl = rod(ll, f"VB0.80 {where}")
        jb, fb = judge_pair(lb, l0, rmax, is_p3, rb)
        jl, fl = judge_pair(ll, l0, rmax, is_p3, rl)
        # rev3 R3-C2: the 436.8 grade = eta 0.85 VB vs V0 T1 (+ H0); eta 0.80 T1 / T3 / T4 / class = records
        fnd.stops.extend(fb.stops)
        fnd.undecidable.extend(fb.undecidable)
        for s in fb.fails:
            fnd.fail(s["where"], f"T1 eta 0.85: {s['why']}")
        rec080["stops"].extend(fl.stops)
        rec080["undecidable"].extend(fl.undecidable)
        t1b = "undecidable" if fb.undecidable else ("fail" if (fb.fails or fb.stops) else "pass")
        t1l = "undecidable" if fl.undecidable else ("fail" if (fl.fails or fl.stops) else "pass")
        v0_ok = ok_j1(j_values(l0))
        cause = t1l == "fail" and t1b == "pass" and v0_ok is True
        if cause:
            cls_flags["cause_fail"].append(where)
        if t1b == "fail" or v0_ok is False:
            cls_flags["baseline_or_v0_fail"].append(where)
        u9 = core.dig(ll, "values.U9", None)
        u9 = u9 if isinstance(u9, dict) else {}
        runs = u9.get("ge3_runs")
        t3a = t3b = None
        if isinstance(runs, list):
            t3a, t3b = True, True
            for r in runs:
                for ax in ("roll", "pitch"):
                    d = core.num(core.dig(r, f"max_abs_delta_deg.{ax}", None))
                    fs = core.num(core.dig(r, f"filtered_start_deg.{ax}", None))
                    fe = core.num(core.dig(r, f"filtered_end_deg.{ax}", None))
                    if d is None or fs is None or fe is None:
                        t3a = t3b = None
                        break
                    t3a = t3a and not core.t_gt(d, T3A_DEG)
                    t3b = t3b and not core.t_gt(abs(fe), abs(fs) + T3B_DEG)
                if t3a is None:
                    break
        al = core.num(core.dig(ll, "values.attitude.max_abs_after_liftoff_deg", None))
        ab = core.num(core.dig(lb, "values.attitude.max_abs_after_liftoff_deg", None))
        t3c = None if al is None or ab is None else not core.t_gt(al, ab + T3C_DEG)
        e5l = core.dig(ll, "values.E5", None)
        e5l = e5l if isinstance(e5l, dict) else {}
        bl = core.num(e5l.get("back_in_band_after_saturation_s"))
        bb = core.num(core.dig(lb, "values.E5.back_in_band_after_saturation_s", None))
        if "back_in_band_after_saturation_s" not in e5l:
            t4 = None
        elif bl is None:
            t4 = False                         # "값이 없으면(띠로 돌아오지 않음) 실패"
        else:
            lim = max(T4_FLOOR_S, (bb + T4_ADD_S) if bb is not None else T4_FLOOR_S)
            t4 = not core.t_gt(bl, lim)
        integ, ilim = core.num(e5l.get("max_abs_integral_rad_s")), core.num(e5l.get("integral_limit_rad_s"))
        t4_flag = integ is not None and ilim is not None and core.t_ge(integ, ilim)
        for nm, val in (("T3a", t3a), ("T3b", t3b), ("T3c", t3c), ("T4", t4)):
            if val is None:
                rec080["undecidable"].append({"where": where, "why": f"{nm}: value missing (9.3)"})
            elif val is False:
                cls_flags[nm].append(where)
        if t4_flag:
            cls_flags["T4_flag_integral"].append(where)
        lg = core.num(u9.get("longest_ge3_s"))
        longest_ge3.append(lg)
        tr_l = core.num(core.dig(ll, "values.times.t_first_ready_s", None))
        tr_b = core.num(core.dig(lb, "values.times.t_first_ready_s", None))
        keys.append({
            "key": list(k), "T1_VB0p85": t1b, "T1_VB0p80": t1l, "V0_J1_ok": v0_ok, "cause_fail": cause,
            "J_VB0p85": jb, "J_VB0p80": jl, "T3a": t3a, "T3b": t3b, "T3c": t3c, "T4": t4,
            "T4_FLAG_integral_limit": t4_flag,
            "T2": {"level_count_s": u9.get("level_count_s"), "longest_ge3_s": u9.get("longest_ge3_s"),
                   "longest_eq4_s": u9.get("longest_eq4_s"),
                   "E1_level_short_s": core.dig(ll, "values.E1.level.short_s", None),
                   "E2_level_min_r": {leg: core.dig(ll, f"values.E2.{leg}.min_r_by_phase.level", None)
                                      for leg in ("FL", "FR", "RL", "RR")},
                   "E4": core.dig(ll, "values.E4", None)},
            "T5_ready_diff_s": None if tr_l is None or tr_b is None else tr_l - tr_b,
            "attitude_after_liftoff_deg": {"eta0p80": al, "eta0p85": ab},
            "E5_back_in_band_s": {"eta0p80": bl, "eta0p85": bb},
        })
    # 4.1 classification
    any_ge = [x for x in longest_ge3 if x is not None]
    if rec080["undecidable"] or len(keys) != len(U9_KEYS):
        cls = "undecidable"
    elif cls_flags["cause_fail"] or cls_flags["T3a"] or cls_flags["T3b"] or cls_flags["T4"]:
        cls = "C"
    elif cls_flags["T3c"]:
        cls = "C (T3c only: 전체 자세 첨두 증가)"
    elif any(core.t_ge(x, AB_LONGEST_S) for x in any_ge):
        cls = "A"
    else:
        cls = "B"
    ask = cls.startswith("C")
    if ask:   # 4.1 "-> 사용자 결정": ask before writing the v5 summary sentence; the bundle grade stays
        fnd.note("U-9", f"class {cls}: ask the user before the v5 summary sentence (R3-C2)")
    status = fnd.status()
    body = {"H0": h0, "keys": keys, "classification": cls, "classification_is_record": True,
            "ask_user_before_v5_sentence": ask, "eta0p80_record_findings": rec080, "class_flags": cls_flags,
            "D_keys_recorded_separately": cls_flags["baseline_or_v0_fail"],
            "longest_ge3_s_max": max(any_ge) if any_ge else None,
            "status_4368": {"pass": "통과", "fail": "미달", "undecidable": "판정 불가", "stop": "멈춤"}[status],
            "counts": {"V0": len(v0), "VB0p85": len(vb[ETA_BASE]), "VB0p80": len(vb[ETA_LOW])},
            "R11-2_t4h_lookup": t4h_log if t4h_lookup is not None else "single --t4h-root (library call)"}
    return body, fnd


# ----------------------------------------------------------------- CLI
def read_lines(paths):
    out = []
    for p in paths or []:
        out.extend(core.read_jsonl(p))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=None)
    ap.add_argument("--out", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("u9", help="H-5 U-9 recount (u9 rules rev1 + 436.8 7.1)")
    u.add_argument("--v0", required=True, help="resume_k1/h5_u9_v0.jsonl (14 V0 lines)")
    u.add_argument("--vb", action="append", required=True,
                   help="file(s) with the U-9 VB lines (eta_v 0.85 / 0.80, u9_metrics); h10_reuse_rerun.jsonl")
    u.add_argument("--h0-ref", action="append", default=None,
                   help="file(s) with the reference VB lines of H0 (1) (default: the --vb files)")
    u.add_argument("--stored-main", default=None, help="stored v5/main.jsonl (H0 (2) record)")
    u.add_argument("--stored-p3", default=None, help="stored v5/p3_hash.jsonl (record)")
    u.add_argument("--t4h-root", action="append", default=None,
                   help="T4h folder of the VB lines (rev9 3.1 rod reading). 436.8 rev11 R11-2: the runner "
                        "convention folders <vb stem>_t4h/ and t4h/ next to each --vb file are used; another "
                        "folder only when none exists, at most one (else input error, S-11, exit 2)")
    args = ap.parse_args(argv)
    repo = Path(args.repo) if args.repo else _HERE.parents[4]
    tool_sha = core.sha256_file(Path(__file__))
    summary = {"tool": TOOL_NAME, "version": TOOL_VERSION, "tool_sha256": tool_sha,
               "core_sha256": core.sha256_file(_HERE / "p2_4368.py")}
    try:
        seals = core.check_seals(repo)
        rs = {rel: core.sha256_file(repo / rel) if (repo / rel).is_file() else None for rel in U9_RULES}
        if not seals["ok"] or any(rs[r] != w for r, w in U9_RULES.items()):
            report, code = {"seals": seals, "u9_rules": rs, "stop_codes": ["S-1"]}, 2
        else:
            is_p3, mod = core.load_is_extend_start(repo)
            report = {"u9_rules": rs, "v5_options": mod, "seals_eol_only": seals.get("eol_only", [])}
            places, perr = t4h_places(args.vb, args.t4h_root)
            report["R11-2_t4h_places"] = ({k: [str(d) for d in v] for k, v in places.items()} if places
                                          else {"input_error": perr})
            if places is None:
                # rev11 R11-2 2: input error, the bundle is not judged (S-11, exit 2)
                report["stop_codes"] = ["S-11"]
                report["H-5"] = {"status_4368": "멈춤", "not_judged": True, "why": perr}
                code = 2
            else:
                v0 = read_lines([args.v0])
                src = {}
                vbl = []
                for p in args.vb:
                    for x in core.read_jsonl(p):
                        if (x.get("job") or {}).get("setting") == "VB" and (x.get("job") or {}).get("u9_metrics"):
                            src[id(x)] = str(p)
                            vbl.append(x)
                ref = read_lines(args.h0_ref or args.vb)
                sm = read_lines([args.stored_main]) if args.stored_main else None
                sp = read_lines([args.stored_p3]) if args.stored_p3 else None
                body, f = recount_u9(v0, vbl, ref, is_p3, sm, sp,
                                     t4h_lookup=lambda ln: rod_reading_lookup(ln, places[src[id(ln)]]))
                report["H-5"] = {**body, **f.as_dict(),
                                 "inputs": {"v0": [args.v0, core.sha256_file(args.v0)],
                                            "vb": [[p, core.sha256_file(p)] for p in args.vb]}}
                report["stop_codes"] = f.as_dict()["stop_codes"]
                code = {"stop": 2, "undecidable": 1, "fail": 1, "pass": 0}[f.status()]
        report.update(tool=TOOL_NAME, version=TOOL_VERSION, tool_sha256=tool_sha,
                      created=_dt.datetime.now().astimezone().isoformat(timespec="seconds"))
        text = json.dumps(report, indent=1, ensure_ascii=False, default=str)
        out_sha = None
        if args.out:
            Path(args.out).write_text(text + "\n", encoding="utf-8", newline="\n")
            out_sha = core.sha256_file(args.out)
        summary.update(exit=code, out=args.out, out_sha256=out_sha, stop_codes=report.get("stop_codes", []))
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        code = 3
        summary.update(exit=3, error=repr(exc)[:300], out_sha256=None)
    print(json.dumps(summary, ensure_ascii=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
