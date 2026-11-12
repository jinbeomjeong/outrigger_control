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
    las_off = bool(cs.get("las_off"))
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
          and (expect_tag is None or out["controller_tag"] == expect_tag))
    out["verdict"] = "pass" if ok else "indeterminate"
    if not ok:
        out["reason"] = "4.2 / 6 record check failed: S-2 / S-3 / S-4 review"
    return out


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
        "P3-8": C.p3_8(row, locs, params, fault["any"], demote=g6),
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
    return {"status": status, "stops": stops, "rows_judged": len(judged), "rows_record": len(recs),
            "row_status": {r["case"]: r["status"] for r in rows}, "note": status_note}


def items_c5(row, params):
    """v5 rev12 2.2 judged items for C-5. Path 2 recomputes the series-only parts (rev6 5
    t_lift / H-9, rev6 6 lock transitions as a record); T4 / T5 / J-P3 / D2 / lock-window items
    need a re-implementation of the controller's two-pressure monitor and are not built."""
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
        ll = row.law_locked.astype(int)
        lockv = (ll != 0).astype(int)   # rev6 6: -1 (before arming) is read as locked
        d = __import__("numpy").diff(lockv, axis=0)
        items["J11_lock_transitions"] = {"clause": "rev6 6 (record: plant lock events)",
                                         "lock_on": (d == 1).sum(axis=0).tolist(),
                                         "lock_off": (d == -1).sum(axis=0).tolist(), "verdict": "record"}
    for k in ("T4-0", "T4", "T5", "J11_window", "J-P3", "D2_lock_window"):
        items[k] = {"clause": "v5 rev6 4 / 6, rev8 J-P3, rev12 2.2", "verdict": "indeterminate",
                    "reason": "not implemented in path 2 (needs an independent two-pressure monitor replay)"}
    items["K1_class"] = dict(C.k1_classification(row, las_off=False), verdict="record")
    if items["K1_class"].get("cls") == "indeterminate":
        items["K1_class"]["verdict"] = "indeterminate"
    keys = ["H-9", "T4-0", "T4", "T5", "J11_window", "J-P3", "D2_lock_window", "K1_class"]
    return items, keys, list(row.notes)
