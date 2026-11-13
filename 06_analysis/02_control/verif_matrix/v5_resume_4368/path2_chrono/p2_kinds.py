"""Path 2 row kinds: item sets per row type, mapped to the rule rows (d1 rules 11, v5 rev6 / rev12).

Each builder returns (items, judged_keys, notes). `judged_keys` lists the items that enter the
row grade (rules 8.1); the other items are records.
"""
from __future__ import annotations

import p2_core as C
import p2_rules as R


def identity_l2b(row, params, expect_tag=None):
    """rev2 R2-3 + rev1 RV1-10 a: K1 request from argv, effective from controller_meta,
    tag from argv --expect-controller vs result."""
    out = {"clause": "rules 4.2 via rev2 R2-3; tag rev1 RV1-10 a"}
    argv = row.argv
    out["argv_k1_order_gate"] = "--k1-order-gate" in argv
    out["argv_las_off"] = "--las-off" in argv
    cm = row.result.get("controller_meta") or {}
    scm = cm.get("slope_clearance_margin") or {}
    out["order_gate_enabled"] = (scm.get("order_gate") or {}).get("enabled")
    out["flat_soil_margin_order_gate"] = (scm.get("settings") or {}).get("flat_soil_margin_order_gate")
    tag_arg = None
    if "--expect-controller" in argv:
        i = argv.index("--expect-controller")
        tag_arg = argv[i + 1] if i + 1 < len(argv) else None
    out["argv_expect_controller"] = tag_arg
    out["result_controller_tag"] = row.result.get("controller_tag")
    ec = row.result.get("expect_controller") or {}
    out["result_expect_ok"] = ec.get("ok")
    out["las_settings_9_values"] = "not checked by path 2 (preset values not in the rule text)"
    ok = (not out["argv_k1_order_gate"] and out["order_gate_enabled"] is True
          and out["flat_soil_margin_order_gate"] is True and tag_arg is not None
          and tag_arg == out["result_controller_tag"] and out["result_expect_ok"] is True
          and (expect_tag is None or tag_arg == expect_tag))
    if not cm:
        out.update(verdict="indeterminate", reason="controller_meta missing (R2-3, 9.3), review S-3")
    else:
        out["verdict"] = "pass" if ok else "indeterminate"
        if not ok:
            out["reason"] = "4.2 / tag record check failed: S-2 / S-3 review"
    return out


def identity_scm(row, expect_tag=None):
    out = {"clause": "rules 4.2 record check (SCM keys) + 6 identity"}
    res = row.result
    cs = res.get("c2_setup") or {}
    cm = res.get("controller_meta") or {}
    scm = cm.get("slope_clearance_margin") or {}
    # rev7 R7-4: `c2_setup.las_off` may be absent in the on arm (read as False, not a 9.3 missing key)
    # and is required in the off arm. The arm is the argv `--las-off` (rev2 R2-2 "C-4 끔 팔(--las-off)").
    las_off_argv = "--las-off" in row.argv
    las_off_rec = cs.get("las_off") if "las_off" in cs else None
    las_off = bool(las_off_rec) if las_off_rec is not None else False
    las_consistent = (las_off_rec is None and not las_off_argv) or (
        las_off_rec is not None and bool(las_off_rec) == las_off_argv)
    out.update(argv_las_off=las_off_argv, c2_setup_las_off=las_off_rec, las_off_consistent=las_consistent,
               r7_4_las_keys=r7_4_las_presence(res, las_off_argv))
    out.update(k1_order_gate=cs.get("k1_order_gate"), k1_order_gate_effective=cs.get("k1_order_gate_effective"),
               flat_soil_margin_order_gate=(scm.get("settings") or {}).get("flat_soil_margin_order_gate"),
               las_off=las_off, num_threads_chrono=res.get("num_threads_chrono"),
               omp_wait_policy=(res.get("placement") or {}).get("omp_wait_policy"),
               hull_hook_mode=(res.get("hull_hook") or {}).get("mode"),
               hull_hook_fallback=(res.get("hull_hook") or {}).get("fallback_reason"),
               controller_tag=(res.get("v5_hydraulics") or {}).get("controller_tag"),
               expect_ok=(cs.get("expect_controller") or {}).get("ok"))
    want_gate = "on" if las_off else "preset"
    ok = (out["k1_order_gate"] == want_gate and out["k1_order_gate_effective"] is True
          and out["flat_soil_margin_order_gate"] is True and out["num_threads_chrono"] == 4
          and out["omp_wait_policy"] == "PASSIVE" and out["hull_hook_mode"] == "fast"
          and out["hull_hook_fallback"] is None and out["expect_ok"] is True
          and (expect_tag is None or out["controller_tag"] == expect_tag) and las_consistent)
    out["verdict"] = "pass" if ok else "indeterminate"
    if not ok:
        out["reason"] = "4.2 / 6 record check failed: S-2 / S-3 / S-4 review"
        if not las_consistent:
            out["reason"] += ("; argv --las-off vs c2_setup.las_off differ or the off-arm key is absent"
                              " (rev7 R7-4 required in the off arm, 9.3)")
    return out


# rev7 R7-4 table rows that depend on the arm (the two `p3b.P3-3_leg_force` keys are a path 1
# judgement block and are not read by path 2, README).
R7_4_LAS_KEYS = ("start_s", "end_s", "end_reason", "active_periods", "ramp")


def r7_4_las_presence(res: dict, off_arm: bool) -> dict:
    """Record only: presence of the R7-4 arm-dependent keys and the table condition for this arm.
    Key presence is the G-S check of path 1 (`gs-check --manifest`, rules 11.2); judgement keeps
    rules 9.3 and rev2 R2-2 (start_s absent with the block present = LAS-b not started)."""
    cs = res.get("c2_setup") or {}
    las = ((res.get("controller_meta") or {}).get("liftoff_approach_slow"))
    keys = {"c2_setup.las_off": "las_off" in cs}
    for k in R7_4_LAS_KEYS:
        keys[f"controller_meta.liftoff_approach_slow.{k}"] = isinstance(las, dict) and k in las
    ramp = las.get("ramp") if isinstance(las, dict) else None
    keys["controller_meta.liftoff_approach_slow.ramp.periods_applied"] = (
        isinstance(ramp, dict) and "periods_applied" in ramp)
    cond = {"c2_setup.las_off": "required" if off_arm else "absent_allowed"}
    for k in keys:
        if k != "c2_setup.las_off":
            cond[k] = "absent_allowed" if off_arm else "required"
    absent_required = sorted(k for k in keys if not keys[k] and cond[k] == "required")
    return {"clause": "rev7 R7-4 (record; key presence = path 1 G-S check)", "arm": "off" if off_arm else "on",
            "present": keys, "condition": cond, "absent_where_required": absent_required}


def items_d8p(row, params, judged=True, hold=True):
    """d1 rules 11 rows C2-01..08 (judged) and C1-09..12 (record): D8.P."""
    items = {
        "D8_F_after_liftoff": C.d8_force(row, params, rigid_nsc_hold=hold),
        "D8_end_attitude": C.d8_end_attitude(row),
        "D8_READY": C.ready_item(row, R.READY_FLAT_S if row.flat else R.READY_SLOPE_S,
                                 "d1 11 READY flat 90 / slope 120 s (relative to loop start)", judged=True),
        "D8_pressure": C.pressure_item(row, params),
        "D8_FAULT0": _fault_item(row),
        "D8_stroke_guard": dict(C.stroke_guard_class(row), verdict="record",
                                clause="d1 11 행정 가드 분류 (record)"),
        "K1_class": dict(C.k1_classification(row, las_off="--las-off" in row.argv), verdict="record"),
        "identity": identity_l2b(row, params) if row.engine != "scm" else identity_scm(row),
    }
    k1 = items["K1_class"]
    if k1.get("cls") == "indeterminate":
        items["K1_class"]["verdict"] = "indeterminate"
    keys = ["D8_F_after_liftoff", "D8_end_attitude", "D8_READY", "D8_pressure", "D8_FAULT0", "identity", "K1_class"]
    if not judged:
        for k in keys:
            if items[k]["verdict"] in ("pass", "fail", "flag", "hold"):
                items[k]["record_verdict"] = items[k]["verdict"]
    return items, keys, []


def _fault_item(row):
    f = C.fault_present(row)
    return {"clause": "FAULT 0", "verdict": "fail" if f["any"] else "pass", **f}


def items_p3(row, params, ready_limit_s, ready_judged, g6=False, allow_stop=True):
    """d1 rules 11 rows S-01/02 (P3, READY 120 s, stroke_limited_stop allowed) and
    S-03/04 (P3 + G6)."""
    notes = []
    t_D = C.t_departure(row)
    locs = C.loc_times(row)
    fault = C.fault_present(row)
    p33 = C.p3_3(row, t_D, params)
    items = {
        "departure": {"clause": "P3-2 t_D / rev2 R2-5", "t_D_s": t_D, "verdict": "record"},
        "P3-1": C.p3_1(row, t_D, locs),
        "P3-2": C.p3_2(row, t_D, locs, p33["verdict"] == "pass", fault["any"], params),
        "P3-3": p33,
        "P3-4": C.p3_4(row),
        "P3-5": C.p3_5(row),
        "P3-6": C.ready_item(row, ready_limit_s, f"P3-6 READY <= {ready_limit_s} s", judged=ready_judged),
        "P3-8": C.p3_8(row, locs, params, fault["any"], demote=g6,
                       p33_pass=None if p33["verdict"] == "indeterminate" else p33["verdict"] == "pass"),
        "P3-9": C.p3_9(row, params),
        "FAULT0": _fault_item(row),
        "leg_lift_after_departure": dict(C.leg_lift(row, t_D) or {}, verdict="record",
                                         clause="pad normal <= 0 after t_D (definition chosen by path 2)"),
        "K1_class": dict(C.k1_classification(row, las_off=bool((row.result.get("c2_setup") or {}).get("las_off"))),
                         verdict="record"),
        "identity": identity_scm(row),
    }
    if items["K1_class"].get("cls") == "indeterminate":
        items["K1_class"]["verdict"] = "indeterminate"
    keys = ["P3-1", "P3-2", "P3-3", "P3-4", "P3-5", "P3-8", "FAULT0", "identity", "K1_class"]
    if ready_judged:
        keys.append("P3-6")
    elif items["P3-6"].get("within") is False:
        items["P3-6"]["flag"] = "P3-6_over_limit (record, rev3 R3-G4)"
    if g6:
        t_R = C.first_phase_time(row, "ready")
        rel = None if t_R is None else t_R - row.loop_start
        items["G6-6"] = {"clause": "G6-6 FAULT 0 + READY reached (G6 Chrono READY <= 120 s, spec 17475)",
                         "t_ready_rel_s": rel, "fault": fault["any"],
                         "verdict": "pass" if (not fault["any"] and rel is not None and R.le(rel, R.G6_READY_S))
                         else "fail"}
        keys.append("G6-6")
    # stroke guard classes (398.1 SL-1, 427.12.5)
    sg = C.stroke_guard_class(row)
    stop = C.stop_classification(row, t_D, params)
    items["stroke_guard"] = dict(sg, verdict="record", stop=stop)
    row_class = None
    if stop is not None:
        row_class = stop["class"]
        if row_class == "stroke_limited_stop" and allow_stop:
            for k in ("P3-4", "P3-5", "P3-6", "FAULT0", "G6-6", "P3-1", "P3-2"):
                if k in items:
                    items[k]["superseded_by"] = "stroke_limited_stop"
            keys = ["P3-3", "P3-8", "identity", "K1_class"]
            items["stroke_guard"]["verdict"] = "pass"
            keys.append("stroke_guard")
        else:
            items["stroke_guard"]["verdict"] = "fail"
            keys.append("stroke_guard")
    elif sg["warn_lift_stroke_limited"] > 0:
        lift = items["leg_lift_after_departure"]
        okc = (not fault["any"] and not lift.get("any", True)
               and items["P3-1"]["verdict"] in ("pass", "flag") and p33["verdict"] == "pass"
               and items["P3-4"]["verdict"] in ("pass", "flag"))
        row_class = "stroke_limited_pass" if okc else "stroke_limited_fail"
        if okc and items["P3-5"]["verdict"] == "fail":
            items["P3-5"]["relaxed_by"] = "stroke_limited_pass (398.1 SL-1)"
            items["P3-5"]["verdict"] = "flag"
    items["row_class"] = {"verdict": "record", "class": row_class}
    if row.notes:
        notes += row.notes
    return items, keys, notes


def bundle_status(rows, expected_count=None, record_bundle=False, extra_stops=None):
    """rules 8.1: 판정 불가 > 미달 > 통과 over judged rows; record bundles 기록 완료 / 불완전.
    Row-count mismatch = S-15."""
    stops = list(extra_stops or [])
    if expected_count is not None and len(rows) != expected_count:
        stops.append(f"S-15: rows {len(rows)} != {expected_count}")
    for r in rows:
        for k, it in r["items"].items():
            if isinstance(it, dict) and it.get("stop"):
                stops.append(f"{r['case']}: {k} {it['stop']}")
    judged = [r["status"] for r in rows if r["status"] in ("통과", "미달", "판정 불가")]
    recs = [r["status"] for r in rows if r["status"] in ("기록 완료", "기록 불완전")]
    if record_bundle:
        status = "기록 불완전" if ("기록 불완전" in recs or stops or not rows) else "기록 완료"
    elif "판정 불가" in judged or stops or not judged:
        status = "판정 불가"
    elif "미달" in judged:
        status = "미달"
    else:
        status = "통과"
    if "기록 불완전" in recs and status in ("통과", "미달"):
        status_note = "record rows incomplete"
    else:
        status_note = None
    n_recalc = sum(1 for r in rows for k in r["judged_keys"]
                   if not str((r["items"].get(k) or {}).get("layer", "")).startswith("re-aggregated"))
    reagg = C.reagg_table(rows)
    return {"status": status, "stops": stops, "rows_judged": len(judged), "rows_record": len(recs),
            "row_status": {r["case"]: r["status"] for r in rows}, "note": status_note,
            "recalculated_judged_items": n_recalc,
            "reaggregated_items": {"names": [e["item"] for e in reagg],
                                   "count": sum(e["rows"] for e in reagg)},
            "TABLE_REAGG": reagg}


def t45_items(row, t45):
    """Grades of the path 2 chrono_t45_replay output (rev6 4.2-4.6, rev7 2-3), per row."""
    out = {}
    lay = "tool run by path 2 (rev4 R4-A2 c)"
    if t45 is None:
        for k in ("T4-0", "T4", "T5"):
            out[k] = {"layer": lay, "verdict": "indeterminate",
                      "reason": "no path 2 t45 report (run p2_t45.py, pass --aux t45=...)"}
        return out
    gate = t45.get("tool_gate") or {}
    reg = t45.get("regression") or {}
    rep = t45.get("replay") or {}
    rr = (rep.get("rows") or {}).get(row.folder.name)
    base = {"layer": lay, "tool_gate_ok": gate.get("ok"), "regression_ok": reg.get("ok"),
            "replay_out_sha256": rep.get("out_sha256"), "criteria": rep.get("criteria")}
    if not gate.get("ok") or not reg.get("ok") or rep.get("criteria") != "rev7":
        for k in ("T4-0", "T4", "T5"):
            out[k] = dict(base, verdict="indeterminate", stop="S-11 (rev4 R4-A2 conditions 1-2)")
        return out
    if rr is None:
        for k in ("T4-0", "T4", "T5"):
            out[k] = dict(base, verdict="indeterminate", reason="row not in the path 2 replay")
        return out
    if not rr.get("settings_equal"):
        for k in ("T4-0", "T4", "T5"):
            out[k] = dict(base, verdict="indeterminate", stop="monitor setting rebuild differs (rev6 4.1: no verdict)",
                          setting_differences=rr.get("setting_differences"))
        return out
    t40 = bool(rr.get("t4_0"))
    out["T4-0"] = dict(base, verdict="pass" if t40 else "fail",
                       **({} if t40 else {"stop": "T4-0 fail: tool defect, not judged (rev6 4.2 / 4.6)"}))
    for k in ("T4", "T5"):
        blk = rr.get(k)
        if not t40 or blk is None:
            out[k] = dict(base, verdict="indeterminate", reason="T4-0 failed or block missing")
            continue
        over = int(blk.get("over_0p6kN", 0))
        it = dict(base, over_0p6kN=over, judged_samples=blk.get("judged_samples"),
                  e_excluded=blk.get("e_excluded"), guard_violations=blk.get("guard_violations"),
                  sensor_model=blk.get("sensor_model"), raw_over_0p6kN=blk.get("raw_over_0p6kN"),
                  verdict="pass" if over == 0 else "fail")
        if over > 0:
            it["stop"] = "H-7 (rev6 4.6, rev7 2 #5)"
        out[k] = it
    return out


def jp3_item(row):
    """436.8 rev8 R8-2 (scope) + v5 rev8 3.2 / rev9 3.2 table (Chrono rows always have rod readings,
    rev9 3.2 #4 note).

    Scope: the ③ reading is the row's tag only (rules 4.1 `is_extend_start_tag`, rev3 R3-C8); the
    tag is argv `--expect-controller` with a true expect check (rules 6, rev1 RV1-10 a). Not
    established -> S-2. Request records (argv `--extend-start-tracked`; with a `v5_hydraulics` block
    also `hydraulic_options.extend_start_tracked`, key absent = off; without the block argv only)
    differ from the tag's ③ -> S-2. Tag ③ off -> na (a missing `extend_start_rule` is not counted).
    Tag ③ on: `controller_meta.two_pressure.settings.extend_start_rule` missing -> 판정 불가 (9.3),
    other than `tracked_bound` -> S-2. A tag ③-off row whose running rule is `tracked_bound` is the
    same tag / controller difference and is also S-2 (rules 8.2 S-2; path 2 reading, README 6)."""
    tg = C.row_tag(row)
    argv_on = "--extend-start-tracked" in row.argv
    v5h = row.result.get("v5_hydraulics")
    has_v5h = isinstance(v5h, dict)
    opt_raw = ((v5h.get("hydraulic_options") or {}).get("extend_start_tracked")) if has_v5h else None
    opt_on = (opt_raw is True) if has_v5h else None
    rule = C.extend_start_rule(row)
    out = {"clause": "436.8 rev8 R8-2 / rules 4.1 / v5 rev8 3.2 / rev9 3.2 / rev4 R4-A2 b",
           "tag": tg["tag"], "tag_established": tg["established"], "expect_ok": tg["expect_ok"],
           "expect_name": tg["expect_name"], "argv_extend_start_tracked": argv_on,
           "v5_hydraulics_block": has_v5h, "hydraulic_options_extend_start_tracked": opt_raw,
           "extend_start_rule": rule}
    if not tg["established"]:
        out.update(verdict="indeterminate", stop="S-2 (rev8 R8-2: row tag not established: argv --expect-controller"
                   " / expect check, rules 6, rev1 RV1-10 a)")
        return out
    on = C.is_extend_start_tag(tg["tag"])
    out["extend_start_tag"] = on
    out["request_compared"] = ["argv", "hydraulic_options"] if has_v5h else ["argv"]
    diff = []
    if argv_on != on:
        diff.append("argv --extend-start-tracked")
    if has_v5h and opt_on != on:
        diff.append("v5_hydraulics.hydraulic_options.extend_start_tracked")
    if diff:
        out.update(verdict="indeterminate", request_mismatch=diff,
                   stop="S-2 (rev8 R8-2: ③ request record vs tag: " + ", ".join(diff) + ")")
        return out
    if not on:
        if rule == "tracked_bound":
            out.update(verdict="indeterminate",
                       stop="S-2 (rev8 R8-2 / rules 8.2: tag ③ off but extend_start_rule = tracked_bound)")
            return out
        out.update(verdict="na", reason="tag ③ off (rev8 R8-2: not applicable; extend_start_rule key not required)")
        return out
    if rule is None:
        out.update(verdict="indeterminate", reason="controller_meta.two_pressure.settings.extend_start_rule missing"
                   " on a tag ③ row (rules 9.3)")
        return out
    if rule != "tracked_bound":
        out.update(verdict="indeterminate",
                   stop=f"S-2 (rev8 R8-2: tag ③ on but extend_start_rule = {rule!r})")
        return out
    ebc = (row.result.get("hydraulics_record") or {}).get("extend_bound_check")
    if not ebc:
        out.update(verdict="indeterminate", stop="setting defect (rev9 3.2 #2)")
        return out
    br = ebc.get("breach_reads")
    out.update(rule=ebc.get("rule"), breach_reads=br, margin_used_reads=ebc.get("margin_used_reads"),
               locked_breach_over_tol_reads=ebc.get("locked_breach_over_tol_reads"))
    if br is None:
        out.update(verdict="indeterminate", stop="setting defect (rev9 3.2 #2)")
        return out
    s = int(sum(br))
    out["breach_sum"] = s
    flags = []
    if sum(ebc.get("margin_used_reads") or []) > 0:
        flags.append("J-P3_margin_used")
    if sum(ebc.get("locked_breach_over_tol_reads") or []) > 0:
        flags.append("J-P3_locked_over_tol")
    out["flags"] = flags
    out["verdict"] = "pass" if s == 0 else "fail"
    if s > 0:
        out["stop"] = "H-7 (rev8 3.2)"
    return out


def j11_item(row, tp, ls=None):
    """rev6 6 + rev2 D-1 + rev5 R5-B1 / R5-B3 + rev6 R6-B7, with rev9 R9-2..R9-5 (C-5 rows).
    Zero-command stretches from the issued command record (r8_series `issued_u`): a stretch opens
    at the first control instant t_s whose issued command is 0 after a non-zero one; its window
    end t_w = t_s + tau_v ln(max(|u_last|, eps) / eps) + t_c + T with the run's
    `two_pressure.settings` (lock_window_valve_tau_s, lock_window_eps_m_s,
    lock_window_closing_delay_s; spec 10.4 2 as written in the monitor docstring). Logged stretches
    are matched to `fallback_lock_log` (t_start_s, window_end_s) to 1e-12 s; a mismatch is S-11.
    Judged / late: rev2 D-1 (t_last, plant lock state at t_w + 1e-6 s from `law_locked`: SCM
    `step_series.npz` on `t_s`, L2b `pads.npz` on `t`, rev8 R8-3a; -1 before the leg's first armed
    sample = locked, rev6 6). Actual fallback legs = log legs U WARN_ROD_PRESSURE_FALLBACK legs
    (R6-B7); n_late > 0 on such a leg = H-7 / L-e (LS rows, R5-B3); other legs recorded.
    `ls` = rev9 R9-4 classification (True / False / None = 판정 불가; with n_late > 0 the row stops
    either way and the stop text says "LS 판별 불가").
    rev9 R9-5 (SCM and L2b alike): `law_locked` absent or failing any R9-2 item (time column, [N, 4],
    int8, {-1, 0, 1}, 1 ms +- 1e-6 s, R9-3 -1 pattern) -> 판정 불가 + stop (G-S: S-11)."""
    import math
    import numpy as np
    log = tp.get("fallback_lock_log")
    st = tp.get("settings") or {}
    out = {"clause": "rev6 6, rev2 D-1, rev5 R5-B1 / B3, rev6 R6-B7, rev8 R8-3 / R8-3a, rev9 R9-2 / R9-3 / R9-4"
                     " / R9-5",
           "law_locked_source": row.law_locked_source, "law_locked_problems": list(row.law_locked_problems),
           "law_locked_codes": C.law_locked_codes(row.law_locked_problems),
           "law_locked_pattern": (row.law_locked_pattern or {}).get("patterns"), "ls": ls}
    # rev9 R9-5 (both engines alike, replaces rev8 R8-3 item 4 and rev3 R3-C7 for law_locked):
    # key absent or any R9-2 item (incl. the R9-3 -1 pattern) failing -> 판정 불가 + stop
    if row.law_locked_problems:
        out.update(verdict="indeterminate", reason="law_locked malformed: " + "; ".join(row.law_locked_problems),
                   stop="R9-5: law_locked malformed (main run: J11 판정 불가, bundle stops and asks; G-S: S-11)")
        return out
    if row.law_locked is None:
        src = "step_series.npz" if row.engine == "scm" else "pads.npz"
        out["law_locked_codes"] = ["key"]
        out.update(verdict="indeterminate", reason=f"{src} law_locked missing (rev9 R9-5)",
                   stop=f"R9-5: {src} law_locked missing (main run: J11 판정 불가, bundle stops and asks;"
                        " G-S: S-11)")
        return out
    if log is None:
        out.update(verdict="indeterminate", reason="fallback_lock_log missing")
        return out
    ev_legs = {C.leg_of(n) for _, n in C.events_named(row, "WARN_ROD_PRESSURE_FALLBACK")} - {None}
    log_legs = {e.get("leg") for e in log if isinstance(e, dict)}
    if log_legs - ev_legs:
        out.update(verdict="indeterminate", stop="S-11 (rev6 R6-B7: log leg without fallback event)",
                   log_legs=sorted(log_legs), event_legs=sorted(ev_legs))
        return out
    actual = sorted(log_legs | ev_legs)
    out["actual_fallback_legs"] = actual
    locked_view, unarmed_after = C.law_lock_view(row.law_locked)
    out["unarmed_after_armed_samples"] = unarmed_after
    try:
        tau = float(st["lock_window_valve_tau_s"])
        eps = float(st["lock_window_eps_m_s"])
        t_c = float(st.get("lock_window_closing_delay_s") or 0.0)
    except (KeyError, TypeError):
        out.update(verdict="indeterminate" if actual else "record", reason="lock window settings missing")
        return out
    T = round(float(np.median(np.diff(row.t10))), 6)
    u = row.issued
    acting = np.vstack([np.zeros((1, 4)), u[:-1]])   # d = 1
    zero_act = np.abs(acting) <= R.CMP_TOL
    stretches = {leg: [] for leg in R.LEGS}
    n_late = [0, 0, 0, 0]
    for li, leg in enumerate(R.LEGS):
        for k in range(1, len(row.t10)):
            if abs(u[k, li]) <= R.CMP_TOL and abs(u[k - 1, li]) > R.CMP_TOL:
                t_s = float(row.t10[k])
                t_w = t_s + tau * math.log(max(abs(u[k - 1, li]), eps) / eps) + t_c + T
                nxt = [j for j in range(k + 1, len(row.t10)) if not zero_act[j, li]]
                closed = bool(nxt)
                t_last = (float(row.t10[nxt[0]]) - T) if closed else row.t_end
                judged = t_w - 1e-9 <= t_last
                j1 = min(int(np.searchsorted(row.tF, t_w + 1e-6)), len(row.tF) - 1)
                state = int(row.law_locked[j1, li])
                late = bool(judged and not locked_view[j1, li])
                n_late[li] += int(late)
                stretches[leg].append({"t_start_s": t_s, "t_window_end_s": t_w, "closed": closed,
                                       "t_last_s": t_last, "judged": judged, "law_locked_after": state,
                                       "late": late})
    matches = []
    for e in log:
        leg = e.get("leg")
        cand = [s for s in stretches.get(leg, []) if abs(s["t_start_s"] - float(e.get("t_start_s", math.nan))) < 0.5 * T]
        if not cand:
            matches.append({"leg": leg, "t_start_s": e.get("t_start_s"), "match": False, "reason": "no stretch"})
            continue
        d = abs(cand[0]["t_window_end_s"] - float(e["window_end_s"]))
        matches.append({"leg": leg, "t_start_s": e.get("t_start_s"), "window_end_s": e["window_end_s"],
                        "recomputed_s": cand[0]["t_window_end_s"], "abs_diff_s": d, "match": d <= 1e-12})
    out.update(n_late=n_late, log_matches=matches,
               stretches={k: v for k, v in stretches.items() if k in actual})
    if any(not m["match"] for m in matches):
        out.update(verdict="indeterminate", stop="S-11 (window end vs fallback_lock_log > 1e-12 s, rev5 R5-B1)")
        return out
    if not actual:
        out.update(verdict="record", status="no actual fallback leg (n_late of all legs recorded)")
        return out
    bad = [leg for leg in actual if n_late[R.LEGS.index(leg)] > 0]
    # rev9 R9-4: LS from the manifest + batch.json v5_setting (ls_classification), never from the name
    if bad:
        if ls is True:
            stop = "L-e (LS row, rev5 R5-B3 / rev9 R9-4)"
        elif ls is False:
            stop = "H-7 (rev6 6)"
        else:
            stop = "H-7 / L-e (LS 판별 불가, rev9 R9-4: stop either way)"
        out.update(verdict="fail", stop=stop, late_fallback_legs=bad)
    else:
        out["verdict"] = "pass"
    return out


def j11_record_item(row):
    """rev9 R9-6: J11 outside C-5 = record only (n_late, actual fallback legs); `law_locked` absent or
    malformed is recorded as 'input absent' and counted, never a stop. Same computation as C-5."""
    tp = (row.result.get("controller_meta") or {}).get("two_pressure") or {}
    j = j11_item(row, tp, ls=None)
    out = {k: v for k, v in j.items() if k not in ("verdict", "stop")}
    out["clause"] = "rev9 R9-6 (C-5 outside: J11 record only) / " + j["clause"]
    out["computed_verdict_record"] = j.get("verdict")
    out["c5_stop_would_be_record"] = j.get("stop")
    out["input_absent"] = bool(row.law_locked is None)
    out["verdict"] = "record"
    return out


def expect_item(row):
    """rev9 R9-1: Chrono row (`run_S9.py level`, `run_S8C.py`, `run_S6C.py`) with
    `c2_setup.expect_controller.ok` (SCM) / `expect_controller.ok` (L2b / L1-R) false or absent
    -> the bundle stops with S-2 (G-S: also S-11). Open-loop C-6 / C-7 rows are not called."""
    tg = C.row_tag(row)
    ok = tg["expect_ok"] is True
    src = "c2_setup.expect_controller.ok" if row.engine == "scm" else "expect_controller.ok"
    out = {"clause": "436.8 rev9 R9-1 (rules 6 tag column, 8.2 S-2)", "source": src,
           "expect_ok": tg["expect_ok"], "tag_argv": tg["tag"], "expect_name": tg["expect_name"],
           "verdict": "pass" if ok else "indeterminate"}
    if not ok:
        out["stop"] = (f"S-2 (rev9 R9-1: {src} "
                       + ("absent" if tg["expect_ok"] is None else repr(tg["expect_ok"]))
                       + "; G-S: also S-11)")
    return out


def manifest_rows(manifest: dict | None, batch_name: str | None) -> dict | None:
    """`batches.<full batch name>.rows[]` of chrono_rows_manifest.json grouped by case: {case: [rows]}
    (lists keep duplicates, rev10 R10-1b). None if the manifest, the name or the batch is absent."""
    if not manifest or not batch_name:
        return None
    b = (manifest.get("batches") or {}).get(batch_name)
    if not isinstance(b, dict):
        return None
    out = {}
    for r in b.get("rows") or []:
        if isinstance(r, dict):
            out.setdefault(str(r.get("case")), []).append(r)
    return out


def batch_case_counts(batch: dict) -> dict:
    """{case: number of `batch.json` `cases[]` entries with that case} (rev10 R10-1b)."""
    out = {}
    for c in batch.get("cases") or []:
        if isinstance(c, dict):
            out[str(c.get("case"))] = out.get(str(c.get("case")), 0) + 1
    return out


# rev10 R10-1b case labels (G-S counts, R10-2)
LS_INPUT_CASES = ("batch_name_unknown", "manifest_rows_0", "manifest_rows_many", "batch_cases_0",
                  "batch_cases_many", "both_value_absent")


def ls_input_case(case: dict, ctx: dict | None) -> dict:
    """rev10 R10-1a / R10-1b input boundary of the LS reading for one row. `ctx` = {"batch_name": full
    name or None, "batch_name_reason", "mrows": manifest_rows(...), "bcount": batch_case_counts(...)}.
    Returns the counts and the list of boundary labels that make the reading not judgeable
    (`blocking`, empty = both sources have exactly one row)."""
    ctx = ctx or {}
    name = str(case.get("case"))
    bname = ctx.get("batch_name")
    rows = (ctx.get("mrows") or {}).get(name, []) if bname else []
    n_m = len(rows) if bname else None
    n_b = (ctx.get("bcount") or {}).get(name, 0)
    blocking = []
    if not bname:
        blocking.append("batch_name_unknown")
    elif n_m == 0:
        blocking.append("manifest_rows_0")
    elif n_m > 1:
        blocking.append("manifest_rows_many")
    if n_b == 0:
        blocking.append("batch_cases_0")
    elif n_b > 1:
        blocking.append("batch_cases_many")
    return {"batch_name": bname, "batch_name_reason": ctx.get("batch_name_reason"), "manifest_rows": n_m,
            "batch_cases": n_b, "blocking": blocking, "manifest_row": rows[0] if len(rows) == 1 else None}


def ls_classification(case: dict, ctx: dict | None) -> dict:
    """rev9 R9-4 (user decision 13) with the rev10 R10-1 input boundary (user decision 16): LS row =
    v5 setting LS1..LS4 in both the manifest row (`batches.<full batch name>.rows[].v5_setting`) and the
    S9 batch.json case (`cases[].v5_setting`) of the same case. Unknown batch name, 0 or several
    manifest rows, 0 or several batch.json entries -> None (판정 불가). Not LS only when both sources
    have exactly one row and both values are absent / None. Equal -> LS iff in LS1..LS4; one value
    only or different -> None. The case name is not used."""
    name = str(case.get("case"))
    inp = ls_input_case(case, ctx)
    mrow = inp.pop("manifest_row")
    mv = None if mrow is None else mrow.get("v5_setting")
    bv = case.get("v5_setting")
    out = {"clause": "436.8 rev9 R9-4 + rev10 R10-1", "case": name, "manifest_v5_setting": mv,
           "batch_v5_setting": bv, "manifest_row_found": mrow is not None, "input": inp}
    if inp["blocking"]:
        out.update(ls=None, reason="rev10 R10-1b: " + ", ".join(inp["blocking"]) + " (판정 불가)")
    elif mv is None and bv is None:
        out.update(ls=False, reason="both sources one row, value absent / None: not an LS row")
        out["input"]["value_case"] = "both_value_absent"
    elif mv is None or bv is None:
        out.update(ls=None, reason="only one of manifest / batch.json has v5_setting (판정 불가)")
    elif mv != bv:
        out.update(ls=None, reason=f"manifest {mv!r} != batch.json {bv!r} (판정 불가)")
    else:
        out["ls"] = mv in R.LS_SETTINGS
    return out


def ls_item(row, case, ctx):
    """R9-4 / R10-1 record item for C-5 rows; an LS row whose tag is not ③ -> S-2."""
    it = dict(ls_classification(case, ctx), verdict="record")
    if it["ls"] is None:
        it["verdict"] = "indeterminate"
    elif it["ls"]:
        tg = C.row_tag(row)
        on = C.is_extend_start_tag(tg["tag"]) if tg["tag"] else False
        it["tag"] = tg["tag"]
        it["extend_start_tag"] = on
        if not on:
            it.update(verdict="indeterminate", stop="S-2 (rev9 R9-4: LS row with a non-③ tag, rules 4.1)")
    return it


def items_c5(row, params, t45=None, case=None, ctx=None):
    """v5 rev12 2.2 judged items for C-5 (rev4 R4-A2): recomputed t_lift / H-9, J-P3, J11 window
    (actual fallback legs), D2 records; T4-0 / T4 / T5 from the path 2 run of chrono_t45_replay
    (`t45` = the p2_t45.py document), graded here. `case` = the batch.json case and `ctx` = the
    batch context of `ls_input_case` (rev9 R9-4 / rev10 R10-1 LS reading; without `case` it is None)."""
    items = {}
    tl, basis = C.t_lift(row)
    items["t_lift"] = {"clause": "rev6 5", "t_lift_s": tl, "basis": basis,
                       "t_lift_sus_s": C.t_lift_sus(row) if row.weight_N is not None else None,
                       "recontacts_after_t_lift": C.recontacts(row, tl) if row.weight_N is not None else None,
                       "verdict": "record"}
    hr = row.result.get("hydraulics_record") or {}
    opts = (row.result.get("v5_hydraulics") or {}).get("hydraulic_options") or {}
    m2_on = bool(opts.get("m2_law"))
    clips = hr.get("m2_clip_times_s")
    complete = hr.get("m2_clip_times_complete")
    h9 = {"clause": "rev6 5 H-9: M2-on row, clips after t_lift > 0 = stop", "m2_on": m2_on,
          "clip_times_complete": complete}
    if not m2_on:
        h9["verdict"] = "na"
    elif clips is None or complete is not True or tl is None:
        h9["verdict"] = "indeterminate"
        h9["reason"] = "clip times missing / incomplete or no t_lift"
    else:
        post = [sum(1 for t in leg if t > tl + R.CMP_TOL) for leg in clips]
        pre = [sum(1 for t in leg if t <= tl + R.CMP_TOL) for leg in clips]
        h9.update(post_lift=post, pre_lift=pre, verdict="fail" if sum(post) > 0 else "pass")
        if sum(post) > 0:
            h9["stop"] = "H-9"
    items["H-9"] = h9
    if row.law_locked is not None:
        lockb, after = C.law_lock_view(row.law_locked)   # rev6 6: -1 before first arming = locked
        d = __import__("numpy").diff(lockb.astype(int), axis=0)
        items["J11_lock_transitions"] = {"clause": "rev6 6 / rev8 R8-3 / rev9 R9-3 (record: plant lock events)",
                                         "source": row.law_locked_source,
                                         "lock_on": (d == 1).sum(axis=0).tolist(),
                                         "lock_off": (d == -1).sum(axis=0).tolist(),
                                         "unarmed_after_armed_samples": after, "verdict": "record"}
    keys = ["H-9", "K1_class"]
    tp = (row.result.get("controller_meta") or {}).get("two_pressure") or {}
    # --- T4-0 / T4 / T5: rev4 R4-A2 option c (path 2 ran chrono_t45_replay, p2_t45.py)
    if row.engine == "l2b":
        for k, it in t45_items(row, t45).items():
            items[k] = it
            keys.append(k)
    else:
        for k in ("T4-0", "T4", "T5"):
            items[k] = {"verdict": "na", "reason": "T4 / T5 are defined on L2b records (rev6 4.1 pads.npz)"}
    # --- J-P3: rev4 R4-A2 option b, rev8 3.2 + rev9 3.2 table (Chrono rows read both pressures)
    items["J-P3"] = jp3_item(row)
    keys.append("J-P3")
    # --- J11 window: rev6 6 + rev2 D-1, actual fallback legs from fallback_lock_log (rev3 R3-C7)
    ls = None
    if case is not None:
        items["LS_class"] = ls_item(row, case, ctx)
        ls = items["LS_class"]["ls"]
    items["J11_window"] = j11_item(row, tp, ls=ls)
    keys.append("J11_window")
    # --- D2: rev5 R5-B2 (reason = third part of INFO_ROD_PRESSURE_FAULT_REASON:<leg>:<reason>)
    reasons = {}
    for _, n in C.events_named(row, "INFO_ROD_PRESSURE_FAULT_REASON"):
        parts = n.split(":", 2)
        if len(parts) == 3:
            reasons.setdefault(parts[1], parts[2])
    fb_legs = sorted({C.leg_of(n) for _, n in C.events_named(row, "WARN_ROD_PRESSURE_FALLBACK")} - {None})
    d2_legs = sorted(l for l, r in reasons.items() if r.startswith("D2"))
    items["D2"] = {"clause": "rev5 R5-B2 / rev6 389-390 (record)", "verdict": "record",
                   "d2_fallback_legs": d2_legs, "d2_fallback_count": len(d2_legs),
                   "fallback_legs": fb_legs, "reasons": reasons,
                   "reason_unreadable_legs": [l for l in fb_legs if l not in reasons],
                   "d2_violation_start_ratio": (tp.get("review_record") or {}).get("d2_violation_start_ratio"),
                   "expected_zero": len(d2_legs) == 0}
    items["K1_class"] = dict(C.k1_classification(row, las_off=False), verdict="record")
    if items["K1_class"].get("cls") == "indeterminate":
        items["K1_class"]["verdict"] = "indeterminate"
    return items, keys, list(row.notes)
