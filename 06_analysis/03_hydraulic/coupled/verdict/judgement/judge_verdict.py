"""Judge the 58 coupling pairs against the sealed criteria (hydraulic_coupling_criteria.md, rev. 4).

Reads the run JSON files only. Writes judgement_tables.json and flat CSV tables next to this file.
Limits come from the criteria; nothing here is tuned to the results.
Run: conda run -n dynamics-dev python -I -B judge_verdict.py
"""
from __future__ import annotations

import csv
import json
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = HERE.parent
F_MIN = 9.41458911
F_SPEC = F_MIN + 5.0
F_T3 = F_SPEC * 1.10
ATT_LIM = 0.2 - 0.02
P3_6_LIM = 100.0
GUARD = 682.8
H6 = {"S1": ("flat", 17, 13), "S2": ("flat", 17, 13), "S3": ("flat", 17, 13),
      "S4": ("m1p1", 31, 13), "S5": ("m1p1", 31, 13), "S7": ("slope", 31, 15), "S8": ("slope", 31, 15)}
SOIL = set(H6)
EVENT = {"R12", "R13", "R14", "R15", "R16"}
AUGER_RPB = ("R6", "R8", "R9")
AUGER_FLAT = ("R1", "R10", "R11")


def load(name):
    return json.loads((V / f"{name}.json").read_text(encoding="utf-8"))


def margin_rows(j):
    """Judged values of one run: name -> (value, limit, sense) with sense '>=' or '<='."""
    v = j["values"]
    out = {}
    att = v["attitude"].get("max_abs_last_5s_deg")
    if att is not None:
        out["item2_att"] = (att, ATT_LIM, "<=")
    out["item3_Fmin"] = (v["forces"]["after_liftoff"]["min_kN"], F_MIN, ">=")
    out["item3_Fspec"] = (v["forces"]["after_liftoff"]["min_kN"], F_SPEC, ">=")
    out["S8C1_first8"] = (v["forces"]["first_8s"]["min_kN"], F_SPEC, ">=")
    if v["forces"].get("after_8s"):
        out["S8C1_after8"] = (v["forces"]["after_8s"]["min_kN"], F_SPEC, ">=")
    eo = j.get("event_output")
    bar = eo["pressure"]["moving_outside_max_bar"] if eo else v["pressure"]["max_moving_bar"]
    out["item4_bar"] = (bar, 180.0, "<=")
    out["item4_sat"] = (v["pressure"]["saturation_leg_chunks"], 0, "<=")
    out["item5_rock"] = (v["attitude"]["rocking_amplitude_deg"], 0.06, "<=")
    res = v["attitude"].get("filter_residual_last_5s_deg")
    if res is not None:
        out["item5_resid"] = (res, 0.005, "<=")
    pr = v.get("probe_attitude_change_deg")
    if pr is not None:
        out["item7_probe"] = (pr, 0.1, "<=")
    if eo:
        out["item6_ready_back"] = (eo["t_ready_back_s"], 40.0, "<=")
        out["event_pass"] = (1 if eo["pass"] else 0, 1, ">=")
        for gate, ok in eo["gates"].items():
            out[f"event_gate_{gate}"] = (1 if ok else 0, 1, ">=")
    rows = j.get("rows")
    if rows:
        for key in ("P3-1", "P3-2", "P3-3", "P3-4", "P3-5", "P3-8", "fault_ready", "SL-1"):
            if key in rows and "pass" in rows[key]:
                out[f"{key}_pass"] = (1 if rows[key]["pass"] else 0, 1, ">=")
        t = rows.get("P3-6", {}).get("t_ready_s")
        if t is not None:
            out["P3-6_READY"] = (t, P3_6_LIM, "<=")
    return out


def ok(value, limit, sense):
    return value >= limit if sense == ">=" else value <= limit


def flips(on, off):
    """Rows passing with the limit off and failing with it on."""
    a, b = margin_rows(on), margin_rows(off)
    res = []
    for k, (val, lim, sense) in a.items():
        if k in b and ok(b[k][0], lim, sense) and not ok(val, lim, sense):
            res.append({"row": k, "on": val, "off": b[k][0], "limit": lim, "sense": sense})
    missing = sorted(set(b) - set(a))
    return res, missing


def event_names(j, prefix):
    return sorted({e[1].split(":")[0] for e in j["events"] if e[1].startswith(prefix)})


def h6_class(j, case):
    """H-6 'margin pass' from the harness values: None for a safe stop run."""
    if j.get("harness_class") != "pass":
        return {"class": str(j.get("harness_class")), "reasons": []}
    kind, dready, dclear = H6[case]
    reasons = []
    t = j["rows"]["P3-6"]["t_ready_s"]
    if t + dready > P3_6_LIM:
        reasons.append(f"READY {t:.1f}+{dready}={t + dready:.1f}>100")
    rut = j["rut_ready_mm"]
    if rut - dclear < 25.0:
        reasons.append(f"clear {rut:.1f}-{dclear}={rut - dclear:.1f}<25")
    gm = GUARD - j["max_motor_stroke_reading_mm"]
    if gm < 23.0:
        reasons.append(f"guard margin {gm:.1f}<23")
    return {"class": "boundary" if reasons else "margin_pass", "reasons": reasons}


def record_rows(on, off, case):
    va, vb = on["values"], off["values"]
    f_on, f_off = va["forces"]["after_liftoff"]["min_kN"], vb["forces"]["after_liftoff"]["min_kN"]
    rec = {"dF_kN": f_on - f_off, "F_on": f_on, "F_off": f_off,
           "F_leg_on": va["forces"]["after_liftoff"]["leg"], "F_t_on": va["forces"]["after_liftoff"]["t_s"],
           "R1_flag": (f_on - f_off) < -max(3.0, 0.10 * f_off)}
    a_on, a_off = va["attitude"].get("max_abs_last_5s_deg"), vb["attitude"].get("max_abs_last_5s_deg")
    rec.update(att_on=a_on, att_off=a_off, datt=None if a_on is None or a_off is None else a_on - a_off)
    rec["att_after_on"] = va["attitude"]["max_abs_after_liftoff_deg"]
    rec["att_after_off"] = vb["attitude"]["max_abs_after_liftoff_deg"]
    t_on, t_off = va["times"].get("t_first_ready_s"), vb["times"].get("t_first_ready_s")
    rec.update(ready_on=t_on, ready_off=t_off, dready=None if t_on is None or t_off is None else t_on - t_off)
    rec["R2_flag"] = [x for x, b in (("att>0.01", rec["datt"] is not None and rec["datt"] > 0.01),
                                     ("after>1.0", rec["att_after_on"] > 1.0 and rec["att_after_off"] <= 1.0),
                                     ("READY>5", rec["dready"] is not None and rec["dready"] > 5.0)) if b]
    d_on, d_off = va["twist"]["peak_abs_after_liftoff_kN"], vb["twist"]["peak_abs_after_liftoff_kN"]
    done_on = va["twist"].get("abs_at_first_done_kN")
    rec.update(D_on=d_on, D_off=d_off, dD=d_on - d_off, D_done_on=done_on,
               D_done_off=vb["twist"].get("abs_at_first_done_kN"))
    tw_on, tw_off = event_names(on, "INFO_TWIST_UNSETTLED"), event_names(off, "INFO_TWIST_UNSETTLED")
    rec["R3_flag"] = [x for x, b in (("dD>13", rec["dD"] > 13.0),
                                     ("done>15", done_on is not None and done_on > 15.0),
                                     ("new_unsettled", bool(tw_on) and not tw_off)) if b]
    rut_on, rut_off = on.get("rut_ready_mm"), off.get("rut_ready_mm")
    st_on, st_off = on["max_motor_stroke_reading_mm"], off["max_motor_stroke_reading_mm"]
    rec.update(rut_on=rut_on, rut_off=rut_off, drut=None if rut_on is None or rut_off is None else rut_on - rut_off,
               stroke_on=st_on, stroke_off=st_off, dstroke=st_on - st_off, guard_margin_on=GUARD - st_on)
    rec["R4_flag"] = [x for x, b in (("clear<-5", rec["drut"] is not None and rec["drut"] < -5.0),
                                     ("stroke>+3", rec["dstroke"] > 3.0)) if b]
    # R-5 rule events
    info = ("INFO_LOC_REVOKED", "INFO_DIFF_SINK_HOLD", "INFO_LOC_CLEARANCE_MARGIN", "soil_mode_start")
    new = []
    counts = {}
    for name in info:
        c_on = sum(1 for e in on["events"] if e[1].startswith(name))
        c_off = sum(1 for e in off["events"] if e[1].startswith(name))
        counts[name] = (c_on, c_off)
        if c_on and not c_off:
            new.append(name)
    rec["rule_counts"] = counts
    rows_on, rows_off = on.get("rows", {}), off.get("rows", {})
    dl_on = rows_on.get("P3-2", {}).get("loc_delay_s")
    dl_off = rows_off.get("P3-2", {}).get("loc_delay_s")
    rec.update(loc_delay_on=dl_on, loc_delay_off=dl_off,
               dloc=None if dl_on is None or dl_off is None else dl_on - dl_off)
    rec["R5_flag"] = new + (["loc_delay>0.5"] if rec["dloc"] is not None and rec["dloc"] > 0.5 else [])
    ea, eb = va["events"], vb["events"]
    dg = va["guard_active_s"] - vb["guard_active_s"]
    dtt = va["times"]["t_touch_end_s"] - vb["times"]["t_touch_end_s"]
    rec.update(reapp_on=ea["reapproach_starts_after_liftoff"], reapp_off=eb["reapproach_starts_after_liftoff"],
               p5_on=ea["p5_relevels_after_liftoff"], p5_off=eb["p5_relevels_after_liftoff"],
               dguard_s=dg, dtouch_s=dtt)
    rec["R6_flag"] = [x for x, b in (("reapproach+", rec["reapp_on"] > rec["reapp_off"]),
                                     ("P5+", rec["p5_on"] > rec["p5_off"]),
                                     ("guard>1s", dg > 1.0), ("TOUCH>2s", dtt > 2.0)) if b]
    rec["R7_flag"] = a_on is not None and a_on > 0.062
    rec["probe_rounds"] = (on.get("probe_rounds", {}).get("n_probe_rounds"), off.get("probe_rounds", {}).get("n_probe_rounds"))
    rec["final_phase"] = (on["final_phase"], off["final_phase"])
    # E rows
    e1 = {k: (round(x["short_s"], 3), round(x["max_deficit_L_min"], 3)) for k, x in va["E1"].items() if x["short_s"] > 0}
    rmin = min(min(x["min_r_by_phase"].values()) for x in va["E2"].values() if x["min_r_by_phase"])
    rmin_level = [x["min_r_by_phase"].get("level") for x in va["E2"].values()]
    long93 = max(x["longest_below_0p93_s"] for x in va["E2"].values())
    rec.update(E1=e1, E2_min_r=rmin, E2_min_r_level=min(r for r in rmin_level if r is not None),
               E2_long93_s=long93, E3_integral_mm=max(va["E3"]["max_abs_integral_mm"].values()),
               E3_between_mm=va["E3"]["max_between_legs_mm"], E4_swaps=va["E4"]["disjoint_swaps"],
               E4_max_in_1s=va["E4"]["max_disjoint_swaps_in_1s"], E4_groups=va["E4"]["group_time_s"],
               E4_gallery=va["E4"]["gallery_bar_while_saturated"],
               E5_I_end=va["E5"]["abs_integral_at_saturation_end_rad_s"], E5_I_max=va["E5"]["max_abs_integral_rad_s"],
               E5_back_s=va["E5"]["back_in_band_after_saturation_s"], E5_at_limit=va["E5"]["max_abs_integral_rad_s"] >= va["E5"]["integral_limit_rad_s"] * (1 - 1e-9))
    rec["E_flags"] = [x for x, b in (("probe/READY exposure", any(k in ("probe", "ready") for k in e1)),
                                     ("r<0.93>=7s", long93 >= 7.0), ("between>10mm", rec["E3_between_mm"] > 10.0),
                                     ("swap>1Hz", rec["E4_max_in_1s"] > 1), ("I at limit", rec["E5_at_limit"])) if b]
    return rec


def main():
    d = json.loads((V / "verdict_pairs.json").read_text(encoding="utf-8"))
    pairs = d["pairs"]
    out = {"criteria_sha256": "d48f4b74342aa027caced7498124ed384e349d0cc06f20d505fed07d9acac44e", "runs": {}}
    offs = {}
    for r in pairs:
        on = load(r["run_id"])
        off = offs.setdefault(r["off_run"], load(r["off_run"]))
        case = r["case_id"]
        fl, missing = flips(on, off)
        # criteria sec. 4: items 2-8 and S8 C1 judge the rigid cases, the P3 rows judge the soil cases.
        soil_outside = [x for x in fl if case in SOIL and x["row"].startswith(("item", "S8C1"))]
        fl = [x for x in fl if x not in soil_outside]
        faults_new = sorted(set(on["values"]["events"]["fault_events"]) - set(off["values"]["events"]["fault_events"]))
        warn_new = sorted(set(on["values"]["events"]["warn_events"]) - set(off["values"]["events"]["warn_events"]))
        cls = (on.get("harness_class"), off.get("harness_class"))
        t3a = (on["values"]["forces"]["after_liftoff"]["min_kN"] < F_T3 and off["values"]["forces"]["after_liftoff"]["min_kN"] >= F_T3)
        t3b = None
        if case in SOIL:
            ca, cb = h6_class(on, case), h6_class(off, case)
            t3b = {"on": ca, "off": cb, "change": cb["class"] == "margin_pass" and ca["class"] != "margin_pass"}
        rec = record_rows(on, off, case)
        flags_new = sorted(k for k, v in on.get("rows", {}).items() if isinstance(v, dict) and v.get("flag") and not off["rows"][k].get("flag"))
        out["runs"][r["run_id"]] = {
            "bundle": r["bundle"], "case": case, "name": r["chrono_name"], "setting": r["setting"],
            "T1_flips": fl, "soil_item_rows_record_only": soil_outside, "missing_rows_on": missing,
            "T2": {"class": cls, "class_change": cls[0] != cls[1], "new_faults": faults_new, "new_warn": warn_new,
                   "final_phase": (on["final_phase"], off["final_phase"])},
            "T3a": t3a, "T3b": t3b, "new_row_flags": flags_new, "record": rec,
            "V2a": on["values"]["V2_a"],
            "def_same": on["definition_sha256"] == off["definition_sha256"],
            "seed": (on.get("seed"), off.get("seed")),
        }
    # item 8 trend: order of the min force over the auger levels on one slope
    trend = {}
    for tag, trio in (("rpB", AUGER_RPB), ("flat", AUGER_FLAT)):
        for b, eta in (("A", "0.85"), ("B", "0.90")):
            ids = [f"{b}_{c}_eta{eta}" for c in trio]
            on = [out["runs"][i]["record"]["F_on"] for i in ids]
            off = [out["runs"][i]["record"]["F_off"] for i in ids]
            ron = [out["runs"][i]["record"]["ready_on"] for i in ids]
            roff = [out["runs"][i]["record"]["ready_off"] for i in ids]
            order = lambda x: "<".join(n for _, n in sorted(zip(x, ("top", "mid", "bot"))))
            trend[f"{tag}_eta{eta}"] = {"F_on": on, "F_off": off, "order_on": order(on), "order_off": order(off),
                                        "ready_on": ron, "ready_off": roff,
                                        "legs_times": [(out["runs"][i]["record"]["F_leg_on"], out["runs"][i]["record"]["F_t_on"]) for i in ids]}
    out["item8_trend"] = trend
    # V-1, V-4
    c = {}
    for run in ("C_R1_eta0.95", "C_S1_eta0.95"):
        j = load(run)
        off = load(f"OFF_{j['case_id']}")
        c[run] = {"same_commands": j["commands_sha256"] == off["commands_sha256"], "V2a": j["values"]["V2_a"],
                  "max_abs_delta": max(abs(float(x["delta"])) for x in next(p for p in pairs if p["run_id"] == run)["metrics"].values()
                                       if isinstance(x.get("delta"), (int, float)))}
    out["V1"] = c
    v4 = {}
    for case, runs in (("R4", ("E_R4_eta0.85_widthdouble", "E_R4_eta0.85_widthhalf")), ("S1", ("E_S1_eta0.85_widthdouble", "E_S1_eta0.85_widthhalf"))):
        base = load(f"A_{case}_eta0.85")
        rows_base = margin_rows(base)
        for run in runs:
            j = load(run)
            rows = margin_rows(j)
            worst = None
            table = {}
            for k, (val, lim, sense) in rows_base.items():
                if k not in rows or sense is None or k.endswith("_pass") or k.startswith("event"):
                    continue
                margin = abs(val - lim)
                change = abs(rows[k][0] - val)
                frac = change / margin if margin > 0 else (0.0 if change == 0 else float("inf"))
                table[k] = {"base": val, "run": rows[k][0], "limit": lim, "change": change, "frac_of_margin": frac}
                if worst is None or frac > worst[1]:
                    worst = (k, frac)
            verd = (j.get("harness_class"), j.get("failed_rows"), base.get("harness_class"), base.get("failed_rows"))
            v4[run] = {"worst": worst, "rows": table, "verdict": verd, "same_verdict": verd[0] == verd[2] and verd[1] == verd[3],
                       "same_commands": j["commands_sha256"] == base["commands_sha256"]}
    out["V4"] = v4
    # contribution summary
    summ = {}
    for b, eta in (("A", 0.85), ("B", 0.90)):
        runs = [v for v in out["runs"].values() if v["bundle"] == b]
        dF = [v["record"]["dF_kN"] for v in runs]
        dr = [v["record"]["dready"] for v in runs if v["record"]["dready"] is not None]
        summ[str(eta)] = {
            "n": len(runs), "T1_flips": sum(len(v["T1_flips"]) for v in runs),
            "T2_class_change": sum(v["T2"]["class_change"] for v in runs),
            "T2_new_fault_warn": sum(bool(v["T2"]["new_faults"] or v["T2"]["new_warn"]) for v in runs),
            "T3a": sum(bool(v["T3a"]) for v in runs),
            "T3b": sum(bool(v["T3b"] and v["T3b"]["change"]) for v in runs),
            "new_row_flags": {v["case"]: v["new_row_flags"] for v in runs if v["new_row_flags"]},
            "dF_kN": {"min": min(dF), "median": st.median(dF), "max": max(dF)},
            "dREADY_s": {"min": min(dr), "median": st.median(dr), "max": max(dr)},
            "R1": [v["case"] for v in runs if v["record"]["R1_flag"]],
            "R2": {v["case"]: v["record"]["R2_flag"] for v in runs if v["record"]["R2_flag"]},
            "R3": {v["case"]: v["record"]["R3_flag"] for v in runs if v["record"]["R3_flag"]},
            "R4": {v["case"]: v["record"]["R4_flag"] for v in runs if v["record"]["R4_flag"]},
            "R5": {v["case"]: v["record"]["R5_flag"] for v in runs if v["record"]["R5_flag"]},
            "R6": {v["case"]: v["record"]["R6_flag"] for v in runs if v["record"]["R6_flag"]},
            "R7": [v["case"] for v in runs if v["record"]["R7_flag"]],
            "E_flags": {v["case"]: v["record"]["E_flags"] for v in runs if v["record"]["E_flags"]},
        }
    out["summary"] = summ
    (HERE / "judgement_tables.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    fields = ["run", "bundle", "case", "name", "T1_flips", "class_on", "class_off", "new_faults", "new_warn", "T3a", "T3b",
              "new_flags", "final_on", "final_off", "F_on", "F_off", "dF", "R1", "att_on", "att_off", "datt", "ready_on", "ready_off",
              "dready", "R2", "D_on", "D_off", "dD", "D_done_on", "R3", "rut_on", "rut_off", "drut", "stroke_on", "stroke_off", "dstroke",
              "R4", "loc_on", "loc_off", "R5", "R6", "R7", "rounds_on", "rounds_off", "E_touch_short_s", "E_level_short_s",
              "min_r", "min_r_level", "long93", "E3_int", "E3_between", "E4_swaps", "E5_I_end", "E5_back_s", "E_flags"]
    with open(HERE / "judgement_table.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for run, v in out["runs"].items():
            x = v["record"]
            w.writerow([run, v["bundle"], v["case"], v["name"], len(v["T1_flips"]), v["T2"]["class"][0], v["T2"]["class"][1],
                        ";".join(v["T2"]["new_faults"]), ";".join(v["T2"]["new_warn"]), v["T3a"], bool(v["T3b"] and v["T3b"]["change"]),
                        ";".join(v["new_row_flags"]), x["final_phase"][0], x["final_phase"][1], x["F_on"], x["F_off"], x["dF_kN"], x["R1_flag"],
                        x["att_on"], x["att_off"], x["datt"], x["ready_on"], x["ready_off"], x["dready"], ";".join(x["R2_flag"]),
                        x["D_on"], x["D_off"], x["dD"], x["D_done_on"], ";".join(x["R3_flag"]), x["rut_on"], x["rut_off"], x["drut"],
                        x["stroke_on"], x["stroke_off"], x["dstroke"], ";".join(x["R4_flag"]), x["loc_delay_on"], x["loc_delay_off"],
                        ";".join(x["R5_flag"]), ";".join(x["R6_flag"]), x["R7_flag"], x["probe_rounds"][0], x["probe_rounds"][1],
                        x["E1"].get("touch", (0, 0))[0], x["E1"].get("level", (0, 0))[0], x["E2_min_r"], x["E2_min_r_level"], x["E2_long93_s"],
                        x["E3_integral_mm"], x["E3_between_mm"], x["E4_swaps"], x["E5_I_end"], x["E5_back_s"], ";".join(x["E_flags"])])
    print(json.dumps({"summary": summ, "item8": trend, "V1": c,
                      "V4": {k: {kk: vv for kk, vv in v.items() if kk != "rows"} for k, v in v4.items()},
                      "flips": {k: v["T1_flips"] for k, v in out["runs"].items() if v["T1_flips"]},
                      "new_warn": {k: (v["T2"]["new_faults"], v["T2"]["new_warn"]) for k, v in out["runs"].items() if v["T2"]["new_faults"] or v["T2"]["new_warn"]},
                      "class_change": {k: v["T2"]["class"] for k, v in out["runs"].items() if v["T2"]["class_change"]},
                      "t3a": [k for k, v in out["runs"].items() if v["T3a"]],
                      "t3b": {k: v["T3b"] for k, v in out["runs"].items() if v["T3b"]},
                      "def_diff": [k for k, v in out["runs"].items() if not v["def_same"]],
                      "V2a_worst": max(v["V2a"]["max_sum_Q_over_supply_minus_1"] for v in out["runs"].values()),
                      "V2a_vu_worst": max(v["V2a"]["max_abs_v_minus_u_on_demand_met_m_s"] for v in out["runs"].values()),
                      "audit_mism": sum(v["V2a"]["audit_mismatches"] for v in out["runs"].values()),
                      "missing": {k: v["missing_rows_on"] for k, v in out["runs"].items() if v["missing_rows_on"]}}, indent=0, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
