"""v5 stage 1 judgement values (criteria v5_criteria.md + rev1..rev6), read-only; M2 law r5 (copy of judge_stage1_r4.py, output name only).

Reads the run lines of main / item8 / overlap / pressure_only and the *_values.json tables and
writes one JSON with the per-gate counts and the failing / flagged rows.
"""
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

V5 = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5")
OUT = Path(__file__).with_name("stage1_values_r5.json")
F_MIN = 9.415
SPEC_RIGID = 14.415
ATT_LIMIT = 0.2
P_MOVE = 180.0
SOIL_READY = ("S1", "S2", "S3", "S4", "S5", "S7")
SOIL_LIMIT = 100.0
RETURN_LIMIT = 60.0
FLOW_ON = {"V2", "V3", "VB", "V4", "V5", "V6", "V7", "V8", "LS1", "LS2", "LS3", "LS4"}


def load(batch):
    return [json.loads(line) for line in (V5 / f"{batch}.jsonl").read_text(encoding="utf-8").splitlines()]


def row_name(job):
    return "R2ra" if job.get("decision") == "reanchor_on" else job["case"]


def phase(job):
    if job.get("twin"):
        t = job["twin"]
        return f"{t['level']}|{t['leg']}|{t['fs_kN']:g}|{job.get('offset_s')}"
    if job.get("offset_s") is not None:
        return f"offset {job['offset_s']}"
    return f"eps {job.get('eps', 0.0)}"


def group(job):
    """Same row for the phase scatter: the G4 width grid groups by its twin (level, leg, F_s)."""
    if job.get("twin"):
        t = job["twin"]
        return f"G4|{t['level']}|{t['leg']}|{t['fs_kN']:g}"
    return row_name(job)


def metrics(rec):
    v = rec["values"]
    ev = rec.get("event_output") or {}
    hyd = rec.get("hydraulics_record") or {}
    out = {"row": row_name(rec["job"]), "phase": phase(rec["job"]), "group": group(rec["job"]),
           "setting": rec["job"]["setting"], "final": rec["final_phase"],
           "t_ready": v["times"]["t_first_ready_s"], "t_lift": v["forces"].get("t_lift_s"),
           "F_after": (v["forces"].get("after_liftoff") or {}).get("min_kN"),
           "att_last5": v["attitude"]["max_abs_last_5s_deg"],
           "p_move": v["pressure"]["max_moving_bar"], "guard_s": v["guard_active_s"],
           "n_rev": rec["command_stats"]["n_rev"], "class": rec.get("harness_class"),
           "bad": sorted(k for k in rec["event_names"] if k.startswith(("WARN", "FAULT"))),
           "fallback_events": sorted({(round(t, 3), n) for t, n in rec["events"] if "ROD" in n}),
           "post_clip": hyd.get("m2_clipped_steps_post_lift"),
           "pre_clip": hyd.get("m2_clipped_steps_pre_lift"),
           "m2_total_mm": hyd.get("m2_shift_total_mm"),
           "lock_changes": len(hyd.get("lock_events") or []),
           "sha": rec["commands_sha256"], "lwa": rec.get("lock_window_alignment"),
           "is_event": bool(ev), "t_event": rec.get("t_event_s")}
    if ev:
        out.update(pass_=ev["pass"], gates=sorted(k for k, g in ev["gates"].items() if not g),
                   F_after_W=min(ev["min_F_after_W_kN"].values()),
                   F_after_event=min(ev["min_F_after_event_kN"].values()),
                   t_back=ev.get("t_ready_back_s"),
                   att_end=max(abs(a) for a in ev["att_end_deg"]),
                   p_move_ev=ev["pressure"]["moving_outside_max_bar"],
                   sat_out_ms=ev["pressure"]["saturation_outside_ms"],
                   awf=ev.get("after_window_force"), miss=ev.get("lower_bound_miss"),
                   ref10=ev.get("ref_10hz_episodes"), final_ev=ev.get("final_phase"))
    if rec.get("soil_stop_crawler"):
        out["s8"] = rec["soil_stop_crawler"]
        out["events_list"] = rec["events"]
    if rec.get("overlap_found"):
        out["overlap_found"] = rec["overlap_found"]
    return out


def J_fails(base, on, base_all, n_rev_max):
    """Criteria 3 / 4 failures of ``on`` against ``base`` (same row, same phase)."""
    fails = []

    def add(item, detail, scatter):
        fails.append({"item": item, "detail": detail, "base_other_phase_has_it": bool(scatter)})

    if on["is_event"]:
        for g in on["gates"]:
            if g not in base["gates"]:
                add("J1", f"gate {g}", any(g in b["gates"] for b in base_all))
        if base["F_after_event"] >= F_MIN > on["F_after_event"]:
            add("J2", f"F_after_event {base['F_after_event']} -> {on['F_after_event']}",
                any(b["F_after_event"] < F_MIN for b in base_all))
        if base["t_back"] is not None and base["t_back"] <= RETURN_LIMIT and (
                on["t_back"] is None or on["t_back"] > RETURN_LIMIT):
            add("J5", f"t_back {base['t_back']} -> {on['t_back']}",
                any(b["t_back"] is None or b["t_back"] > RETURN_LIMIT for b in base_all))
        if base["att_end"] <= ATT_LIMIT < on["att_end"]:
            add("J6", f"att_end {base['att_end']} -> {on['att_end']}",
                any(b["att_end"] > ATT_LIMIT for b in base_all))
        if base["p_move_ev"] <= P_MOVE < on["p_move_ev"]:
            add("J10", f"p_move_out {base['p_move_ev']} -> {on['p_move_ev']}", False)
    else:
        if base["class"] in ("pass", "stroke_limited_stop") and on["class"] != base["class"]:
            add("J1", f"class {base['class']} -> {on['class']}",
                any(b["class"] != base["class"] for b in base_all))
        if base["F_after"] is not None and base["F_after"] >= F_MIN and (
                on["F_after"] is None or on["F_after"] < F_MIN):
            add("J2", f"F_after {base['F_after']} -> {on['F_after']}",
                any((b["F_after"] or 0) < F_MIN for b in base_all))
        if on["row"] in SOIL_READY and base["t_ready"] is not None and base["t_ready"] <= SOIL_LIMIT \
                and (on["t_ready"] is None or on["t_ready"] > SOIL_LIMIT):
            add("J3", f"t_ready {base['t_ready']} -> {on['t_ready']}",
                any(b["t_ready"] is None or b["t_ready"] > SOIL_LIMIT for b in base_all))
        if base["att_last5"] is not None and base["att_last5"] <= ATT_LIMIT and (
                on["att_last5"] is None or on["att_last5"] > ATT_LIMIT):
            add("J6", f"att_last5 {base['att_last5']} -> {on['att_last5']}",
                any((b["att_last5"] or 99) > ATT_LIMIT for b in base_all))
        if base["p_move"] <= P_MOVE < on["p_move"]:
            add("J10", f"p_move {base['p_move']} -> {on['p_move']}", False)
    if base["final"] == "ready" and on["final"] != "ready":
        add("J4", f"final {base['final']} -> {on['final']}",
            any(b["final"] != "ready" for b in base_all))
    if base["t_ready"] is not None and on["t_ready"] is None and not on["is_event"]:
        add("J4", "first READY reached by V0, not by the setting", False)
    for name in on["bad"]:
        if name not in base["bad"]:
            add("J7", name, any(name in b["bad"] for b in base_all))
    if on["n_rev"] >= 2 * n_rev_max and on["n_rev"] >= n_rev_max + 6:
        add("J8", f"n_rev {on['n_rev']} vs base max {n_rev_max}", False)
    if on["post_clip"] is not None and any(n > 0 for n in on["post_clip"]):
        add("J9", f"post-lift clips {on['post_clip']}", False)
    lwa = on["lwa"]
    if lwa and lwa.get("n_late") is not None and lwa.get("n_late_fallback", 0) > 0:
        add("J11", f"n_late_fallback {lwa['n_late_fallback']}", False)
    return fails


def by_key(rows):
    return {(r["row"], r["phase"]): r for r in rows}


def main():
    recs = load("main")
    rows = [metrics(r) for r in recs]
    S = defaultdict(list)
    for r in rows:
        S[r["setting"]].append(r)
    base = by_key(S["V0"])
    base_groups = defaultdict(list)
    for r in S["V0"]:
        base_groups[r["group"]].append(r)
    nrev_max = {g: max(r["n_rev"] for r in rs) for g, rs in base_groups.items()}
    out = {}

    # P-5 / P-7 / P-4 (hydraulic option per setting)
    out["counts"] = {s: len(v) for s, v in sorted(S.items())}
    opt = defaultdict(set)
    for r in recs:
        opt[r["job"]["setting"]].add(json.dumps(r["hydraulic_options"], sort_keys=True))
    out["options_per_setting"] = {s: sorted(v) for s, v in sorted(opt.items())}
    l1 = by_key(S["L1"])
    out["P7_L1_hash_equal_V0"] = [k for k, r in l1.items() if r["sha"] == base[k]["sha"]]
    out["P7_L1_lock_changes_min"] = min(r["lock_changes"] for r in S["L1"])

    # V0 baseline failures (criteria: base failures are recorded, not counted)
    v0_fail = []
    for r in S["V0"]:
        bad = []
        if r["is_event"] and not r["pass_"]:
            bad.append(f"event fail gates={r['gates']}")
        if not r["is_event"] and r["class"] not in ("pass", "stroke_limited_stop"):
            bad.append(f"class {r['class']}")
        if r["final"] != "ready":
            bad.append(f"final {r['final']}")
        if bad:
            v0_fail.append({"row": r["row"], "phase": r["phase"], "bad": bad})
    out["V0_baseline_failures"] = v0_fail

    # J1..J11 per setting against V0 (VB judged; others recorded)
    out["J_vs_V0"] = {}
    for s in ("VB", "V1", "V2", "V3", "L1", "LS1", "LS2", "LS3", "LS4", "V4", "V5", "V6", "V7", "V8", "L2"):
        fails = []
        for r in S[s]:
            b = base[(r["row"], r["phase"])]
            for f in J_fails(b, r, base_groups[r["group"]], nrev_max[r["group"]]):
                fails.append({"row": r["row"], "phase": r["phase"], **f})
        out["J_vs_V0"][s] = {"runs": len(S[s]), "n_fail": len(fails),
                             "by_item": dict(Counter(f["item"] for f in fails)),
                             "fails": fails[:200]}

    # LS against VB (L-a .. L-d)
    vb = by_key(S["VB"])
    vb_groups = defaultdict(list)
    for r in S["VB"]:
        vb_groups[r["group"]].append(r)
    vb_nrev = {g: max(r["n_rev"] for r in rs) for g, rs in vb_groups.items()}
    out["LS_vs_VB"] = {}
    for s in ("LS1", "LS2", "LS3", "LS4"):
        fails, big = [], []
        for r in S[s]:
            b = vb[(r["row"], r["phase"])]
            for f in J_fails(b, r, vb_groups[r["group"]], vb_nrev[r["group"]]):
                fails.append({"row": r["row"], "phase": r["phase"], **f})
            fb = b["F_after_event"] if b["is_event"] else b["F_after"]
            fl = r["F_after_event"] if r["is_event"] else r["F_after"]
            tb = b["t_back"] if b["is_event"] else b["t_ready"]
            tl = r["t_back"] if r["is_event"] else r["t_ready"]
            dF = None if fb is None or fl is None else fl - fb
            dT = None if tb is None or tl is None else tl - tb
            if (dF is not None and abs(dF) >= 1.0) or (dT is not None and abs(dT) >= 1.0):
                big.append({"row": r["row"], "phase": r["phase"], "dF_kN": dF, "dT_s": dT})
        # L-b limits for LS itself
        lim = []
        for r in S[s]:
            if r["is_event"]:
                if r["t_back"] is None or r["t_back"] > RETURN_LIMIT:
                    lim.append((r["row"], r["phase"], "t_back", r["t_back"]))
            elif r["row"] in SOIL_READY and (r["t_ready"] is None or r["t_ready"] > SOIL_LIMIT):
                lim.append((r["row"], r["phase"], "t_ready", r["t_ready"]))
        out["LS_vs_VB"][s] = {"n_fail": len(fails), "by_item": dict(Counter(f["item"] for f in fails)),
                              "fails": fails[:100], "Lb_limit_violations": lim,
                              "Ld_big_changes_n": len(big), "Ld_big_changes": big[:60]}

    # VB / L1 table, E_LC and interaction (criteria 8)
    v3 = by_key(S["V3"])

    def ok(r, b):
        return not J_fails(b, r, base_groups[r["group"]], nrev_max[r["group"]])

    tab = Counter()
    eff = defaultdict(list)
    for k, r in l1.items():
        b = base[k]
        tab[(("VB pass" if ok(vb[k], b) else "VB fail"), ("L1 pass" if ok(r, b) else "L1 fail"))] += 1
        for name, get in (("F_min_kN", lambda x: x["F_after_event"] if x["is_event"] else x["F_after"]),
                          ("t_ready_s", lambda x: x["t_ready"]),
                          ("t_back_s", lambda x: x.get("t_back")), ("n_rev", lambda x: x["n_rev"])):
            vals = [get(x) for x in (r, b, vb[k], v3[k])]
            if any(v is None for v in vals):
                continue
            e_lc = vals[0] - vals[1]
            inter = (vals[2] - vals[3]) - e_lc
            eff[name].append((e_lc, inter))
    out["VB_L1_table"] = {f"{a} / {c}": n for (a, c), n in tab.items()}
    out["E_LC_interaction"] = {
        name: {"n": len(v), "E_LC_median": statistics.median(e for e, _ in v),
               "E_LC_range": [min(e for e, _ in v), max(e for e, _ in v)],
               "inter_median": statistics.median(i for _, i in v),
               "inter_range": [min(i for _, i in v), max(i for _, i in v)]}
        for name, v in eff.items()}

    # n_rev increase record (VB)
    out["VB_nrev_increase"] = [
        {"row": r["row"], "phase": r["phase"], "n_rev": r["n_rev"], "base_max": nrev_max[r["group"]]}
        for r in S["VB"] if r["n_rev"] > nrev_max[r["group"]]]

    # J2 spec shortfall 14.415 kN (event-less rigid rows) and soil, VB and V0
    out["spec_short_14p415"] = {
        s: [{"row": r["row"], "phase": r["phase"], "F_after": r["F_after"]} for r in S[s]
            if not r["is_event"] and r["row"].startswith("R") and r["F_after"] is not None
            and r["F_after"] < SPEC_RIGID] for s in ("V0", "VB")}

    # VB value ranges per row (report table)
    summ = {}
    for s in ("V0", "VB"):
        g = defaultdict(list)
        for r in S[s]:
            g[r["group"]].append(r)
        summ[s] = {}
        for name, rs in sorted(g.items()):
            F = [r["F_after_event"] if r["is_event"] else r["F_after"] for r in rs]
            F = [x for x in F if x is not None]
            summ[s][name] = {
                "n": len(rs), "final": dict(Counter(r["final"] for r in rs)),
                "class_or_pass": dict(Counter(str(r["pass_"]) if r["is_event"] else str(r["class"]) for r in rs)),
                "t_ready": [min((r["t_ready"] for r in rs if r["t_ready"] is not None), default=None),
                            max((r["t_ready"] for r in rs if r["t_ready"] is not None), default=None)],
                "t_ready_none": sum(r["t_ready"] is None for r in rs),
                "t_back": [min((r["t_back"] for r in rs if r.get("t_back") is not None), default=None),
                           max((r["t_back"] for r in rs if r.get("t_back") is not None), default=None)],
                "F_min": [min(F, default=None), max(F, default=None)],
                "n_rev": [min(r["n_rev"] for r in rs), max(r["n_rev"] for r in rs)],
                "att": max((r["att_end"] if r["is_event"] else (r["att_last5"] or 0)) for r in rs),
                "p_move": max((r["p_move_ev"] if r["is_event"] else r["p_move"]) for r in rs),
                "bad": sorted({b for r in rs for b in r["bad"]}),
                "guard_s": [min(r["guard_s"] for r in rs), max(r["guard_s"] for r in rs)]}
    out["summary"] = summ

    # H-3 R12 / G4 V0 pass count vs VB
    def passes(s, pred):
        return sum(1 for r in S[s] if pred(r) and r["is_event"] and r["pass_"])
    out["H3"] = {s: {"R12": passes(s, lambda r: r["group"] == "R12"),
                     "G4": passes(s, lambda r: r["group"].startswith("G4"))} for s in ("V0", "VB")}

    # H-8 S7 class and guard
    out["H8_S7"] = {s: [{"phase": r["phase"], "class": r["class"], "guard_s": r["guard_s"],
                         "final": r["final"], "bad": r["bad"]} for r in S[s] if r["row"] == "S7"]
                    for s in ("V0", "VB")}

    # S8 criteria 6
    s8 = {}
    for s in sorted(S):
        lst = []
        for r in S[s]:
            if r["row"] != "S8":
                continue
            ev = r.get("events_list") or []
            warn_t = [t for t, n in ev if n.startswith("WARN_LIFT_STROKE_LIMITED")]
            fault_t = [t for t, n in ev if n.startswith("FAULT_LIFT_STROKE_LIMIT:soil")]
            lst.append({"phase": r["phase"], "class": r["class"], "t_ready": r["t_ready"],
                        "same_cycle": bool(warn_t and fault_t and abs(warn_t[0] - fault_t[0]) < 1e-6),
                        "stroke_end": any("STROKE_END" in n for _, n in ev),
                        "F_after": r["F_after"], "p_move": r["p_move"], **(r.get("s8") or {})})
        if lst:
            s8[s] = lst
    out["S8"] = s8

    # J11 per gate setting: fallback legs and reasons of runs without stretches
    j11 = {}
    for s in ("VB", "LS1", "LS2", "LS3", "LS4", "L1"):
        reasons = Counter()
        fb_runs = 0
        late_all = 0
        for rec in recs:
            if rec["job"]["setting"] != s:
                continue
            lwa = rec.get("lock_window_alignment")
            if lwa is None:
                reasons["no lock_window_alignment key"] += 1
            elif lwa.get("n_late") is None and "reason" in lwa:
                reasons[lwa["reason"]] += 1
            else:
                fb_runs += bool(lwa.get("fallback_legs"))
                late_all += sum(lwa["n_late_by_leg"].values())
        j11[s] = {"skipped": dict(reasons), "runs_with_fallback_legs": fb_runs,
                  "late_all_legs": late_all}
    out["J11"] = j11
    # which rows lack the alignment (VB)
    out["J11_VB_skipped_rows"] = sorted({(row_name(r["job"]), phase(r["job"])) for r in recs
                                         if r["job"]["setting"] == "VB"
                                         and (r.get("lock_window_alignment") or {}).get("n_late", 0) is None})[:40]

    # event force (criteria 3.1 values, VB)
    out["VB_event_force"] = [
        {"row": r["row"], "phase": r["phase"], "min_1ms": r["awf"]["min_1ms_kN"],
         "min_0p5s": r["awf"]["min_trailing_0p5s_kN"], "lift_ms": r["awf"]["lift_ms_after_window"],
         "FLAG_E3_1ms": r["awf"]["FLAG_E3_1ms"], "F_after_W": r["F_after_W"]}
        for r in S["VB"] if r["is_event"] and r.get("awf")]

    # ---------- item8 ----------
    it = [metrics(r) for r in load("item8")]
    out["item8_rows"] = [{"row": r["row"], "phase": r["phase"], "setting": r["setting"],
                          "final": r["final"], "F_after": r["F_after"], "bad": r["bad"],
                          "post_clip": r["post_clip"], "class": r["class"]} for r in it]
    reg = [r for r in rows if r["row"] in ("R6", "R8", "R9") and r["setting"] in ("V0", "VB")]
    allr = it + reg
    by = defaultdict(list)
    for r in allr:
        by[(r["setting"], r["row"])].append((r["phase"], r["F_after"]))
    out["item8_values"] = {f"{s}|{row}": sorted(v) for (s, row), v in sorted(by.items())}
    # J for item8 VB rows vs V0 of same phase
    itb = {(r["row"], r["phase"]): r for r in it if r["setting"] == "V0"}
    out["item8_J"] = []
    for r in it:
        if r["setting"] == "VB":
            b = itb[(r["row"], r["phase"])]
            out["item8_J"] += J_fails(b, r, [b], b["n_rev"])

    # ---------- overlap ----------
    ov = [metrics(r) for r in load("overlap")]
    ovb = {(r["phase"]): r for r in ov if r["setting"] == "V0"}
    out["overlap"] = []
    for r in ov:
        b = ovb[r["phase"]]
        f = J_fails(b, r, [b], b["n_rev"]) if r["setting"] != "V0" else []
        of = r.get("overlap_found") or {}
        out["overlap"].append({
            "setting": r["setting"], "phase": r["phase"], "t_event": r["t_event"],
            "final": r["final"], "pass": r.get("pass_"), "gates": r.get("gates"),
            "F_after_event": r.get("F_after_event"), "F_after_W": r.get("F_after_W"),
            "t_back": r.get("t_back"), "n_rev": r["n_rev"],
            "awf_min_1ms": (r.get("awf") or {}).get("min_1ms_kN"),
            "overlap_found": of, "J_fails": f, "sha": r["sha"][:12]})
    # golden check context: main R12 V0 offset 0 event time vs overlap
    out["overlap_golden_context"] = {
        "main_R12_V0_o0_t_event": base[("R12", "offset 0.0")]["t_event"],
        "main_R12_V0_o0_sha": base[("R12", "offset 0.0")]["sha"][:12],
        "overlap_V0_o0_t_event": ovb["offset 0.0"]["t_event"],
        "overlap_V0_o0_sha": ovb["offset 0.0"]["sha"][:12],
        "golden_sha": json.loads((V5 / "golden_off" / "OFF_R12.json").read_text(encoding="utf-8"))["commands_sha256"][:12],
        "overlap_t_a": json.loads((V5 / "overlap_t_a.json").read_text(encoding="utf-8"))}

    # ---------- pressure_only ----------
    po = json.loads((V5 / "pressure_only_values.json").read_text(encoding="utf-8"))["pressure_only"]
    agg = defaultdict(lambda: Counter())
    mins = defaultdict(list)
    for e in po:
        for j in ("pressure", "combined"):
            v = e.get(j)
            if v is None:
                agg[(e["setting"], j)]["missing"] += 1
                continue
            agg[(e["setting"], j)]["runs"] += 1
            agg[(e["setting"], j)]["miss_intervals"] += v["miss_intervals"] or 0
            agg[(e["setting"], j)]["runs_with_miss"] += bool(v["miss_intervals"])
            agg[(e["setting"], j)]["below_ms_sum"] += v["below_f_min_ms_sum"] or 0
            agg[(e["setting"], j)]["runs_below"] += bool(v["below_f_min_ms_sum"])
            agg[(e["setting"], j)]["ref10_missed"] += (v["ref_10hz_episodes"] or {}).get("missed") or 0
            agg[(e["setting"], j)]["ref10_episodes"] += (v["ref_10hz_episodes"] or {}).get("episodes") or 0
            mins[(e["setting"], j)].append(v["min_1ms_kN"])
    out["pressure_only"] = {f"{s}|{j}": {**dict(c), "min_1ms_range": [min(mins[(s, j)]), max(mins[(s, j)])]}
                            for (s, j), c in sorted(agg.items())}
    out["pressure_only_unit_status"] = sorted({e["unit_status"] for e in po})
    pr = [metrics(r) for r in load("pressure_only")]
    out["pressure_only_finals"] = dict(Counter(f"{r['setting']}|{r['final']}|pass={r.get('pass_')}"
                                               for r in pr))

    # ---------- T4h ----------
    t4 = {}
    for b in ("main", "item8", "overlap"):
        rep = json.loads((V5 / b / "t4h" / "t4h_replay.json").read_text(encoding="utf-8"))
        rows_ = rep["rows"]
        t4[b] = {"runs": len(rows_), "not_pass": sum(not r["provisional_pass"] for r in rows_),
                 "over_0p6kN": sum(r["over_0p6kN"] for r in rows_),
                 "max_excess_N": max(r["max_excess_N"] for r in rows_ if r["max_excess_N"] is not None),
                 "tail_samples": sum(sum(r["unlocked_tail_samples_by_leg"].values()) for r in rows_),
                 "tail_over": sum(sum(r["unlocked_tail_over_0p6kN_by_leg"].values()) for r in rows_),
                 "tail_runs_over": sum(sum(r["unlocked_tail_over_0p6kN_by_leg"].values()) > 0 for r in rows_),
                 "tail_max_N": max(r["unlocked_tail_max_excess_N"] for r in rows_
                                   if r["unlocked_tail_max_excess_N"] is not None),
                 "settings": dict(Counter(r["file"].rsplit("_", 1)[1].split(".")[0] for r in rows_)),
                 "keys": sorted(k for k in rep if k != "rows")}
        t4[b]["meta"] = {k: rep[k] for k in rep if k != "rows"}
    out["t4h"] = t4

    OUT.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("written", OUT)


if __name__ == "__main__":
    main()

