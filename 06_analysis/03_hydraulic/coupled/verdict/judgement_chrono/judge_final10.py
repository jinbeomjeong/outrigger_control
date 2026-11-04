"""Final 10-row verdict tables (criteria rev. 6): soil rows from soil_tables.json and s8_stop_detail.json, rigid rows
from chrono_tables.json, Chrono deltas against the clipped harness, clipped harness pair verdict, B_S1 180 s.

Limits come from the criteria and are not tuned to the results. Read only for the run folders. Writes final10.json and
final10_rows.csv next to this file.

Run: conda run -n dynamics-dev python -I judge_final10.py
"""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control")
HERE = ROOT / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono"
VERDICT = HERE.parent
CLIP = VERDICT / "clip"
F_MIN = 9.41458911
F_SPEC = F_MIN + 5.0
F_T3 = F_SPEC * 1.10
GUARD_MM = 682.8
SHA = "1d743eab34d5091757b5e021bc1722f56fbedea9b0bc7ff2b4ca5ea0774fd0de"
P3_ROWS = ("P3-1", "P3-2", "P3-3", "P3-4", "P3-5", "P3-6", "P3-8")
ALIAS = {"S1": "S1", "S6": "S5", "S8": "S8"}
LIM = {"F": 3.0, "stroke": 5.0, "gap": 5.0, "ready": 5.0}
S9 = ROOT / "07_results/S9"
SOIL_DIRS = {
    "S8": (S9 / "batch_COUPLED_eta085_20261104_142213/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0",
           S9 / "batch_FINAL-REP_20261030_223359/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0"),
    "S6": (S9 / "batch_COUPLED_eta085_20261104_142213/P3b_J2_B_top_Fs4_m1p1_t180",
           S9 / "batch_FINAL-REP-X_20261031_020716/P3b_J2_B_top_Fs4_m1p1_t180"),
    "S1": (S9 / "batch_COUPLED_eta085_20261104_142213/P3b_J1_B_top_Fs4",
           S9 / "batch_FINAL-REP_20261030_223359/P3b_J1_B_top_Fs4"),
}


def p3_rows(values: dict) -> dict:
    c = values["checks"]
    return {"P3-1": bool(c["P3-1_recontact_pass"] and c["P3-1_crawler_zero_after_ready"]),
            "P3-1_flags": c.get("P3-1_flags"),
            "P3-2": c["P3-2_verdict"], "P3-2_s": c["P3-2_loc_minus_departure_s"], "P3-2_lim_s": c["P3-2_limit_s"],
            "P3-3": bool(c["P3-3_within"]), "P3-4": bool(c["P3-4_within_0p2"]), "P3-4_deg": c["P3-4_absmax_deg"],
            "P3-5": c["P3-5_within"], "P3-5_mm": None if c["P3-5_rut_clearance_min_after_first_ready_m"] is None else c["P3-5_rut_clearance_min_after_first_ready_m"] * 1e3,
            "P3-6": bool(c["P3-6_within"]), "P3-6_s": values["ready_s"][0] if values["ready_s"] else None,
            "P3-7_record": c["P3-7_within"], "P3-8": bool(c["P3-8_within"])}


def soil_row(cid: str, r: dict, stop: dict) -> dict:
    on, off = r["on"], r["off"]
    pon, poff = p3_rows(on), p3_rows(off)
    flips = []
    for row in P3_ROWS:
        a, b = pon[row], poff[row]
        good_off = b in (True, "pass", "flag")
        good_on = a in (True, "pass", "flag")
        if good_off and not good_on:
            flips.append(row)
    events_on = set(on["counts"])
    events_off = set(off["counts"])
    new_events = sorted(events_on - events_off)
    gone_events = sorted(events_off - events_on)
    fault_new = sorted(e for e in new_events if e.startswith("FAULT") or e.startswith("WARN_LIFT_STROKE"))
    dF = on["F_min_after_departure_kN"] - off["F_min_after_departure_kN"]
    dF_tw = on["F_min_twist_removed_kN"] - off["F_min_twist_removed_kN"]
    att_on, att_off = pon["P3-4_deg"], poff["P3-4_deg"]
    end_on = float(np.abs(on["end_roll_pitch_deg"]).max())
    end_off = float(np.abs(off["end_roll_pitch_deg"]).max())
    datt = (att_on - att_off) if att_on is not None and att_off is not None else end_on - end_off
    dready = None if not on["ready_s"] or not off["ready_s"] else on["ready_s"][0] - off["ready_s"][0]
    dD = on["D_peak_abs_after_dep_kN"] - off["D_peak_abs_after_dep_kN"]
    dgap = None if pon["P3-5_mm"] is None or poff["P3-5_mm"] is None else pon["P3-5_mm"] - poff["P3-5_mm"]
    dstroke = max(on["stroke_reading_max_mm"]) - max(off["stroke_reading_max_mm"])
    dloc = pon["P3-2_s"] - poff["P3-2_s"]
    dtouch = on["touch_end_s"] - off["touch_end_s"]
    info = ("INFO_LOC_REVOKED", "INFO_DIFF_SINK_HOLD", "INFO_LOC_CLEARANCE_MARGIN", "INFO_TWIST_UNSETTLED", "soil_mode_start")
    new_info = [k for k in info if on["counts"].get(k, 0) and not off["counts"].get(k, 0)]
    flags = {
        "R-1": dF < -max(3.0, 0.10 * off["F_min_after_departure_kN"]),
        "R-2": [x for x, b in (("att>+0.01", datt > 0.01),
                               ("after>1.0 new", on["att_max_after_dep_deg"] > 1.0 and off["att_max_after_dep_deg"] <= 1.0),
                               ("READY>+5", dready is not None and dready > 5.0)) if b],
        "R-3": [x for x, b in (("dD>13", dD > 13.0), ("done>15", on.get("D_at_first_done_kN") is not None and abs(on["D_at_first_done_kN"]) > 15.0),
                               ("new UNSETTLED", on["counts"].get("INFO_TWIST_UNSETTLED", 0) > off["counts"].get("INFO_TWIST_UNSETTLED", 0))) if b],
        "R-4": [x for x, b in (("gap<-5", dgap is not None and dgap < -5.0), ("stroke>+3", dstroke > 3.0)) if b],
        "R-5": new_info + (["dLOC>0.5"] if dloc > 0.5 else []) + (["soil mode change"] if bool(on["counts"].get("soil_mode_start")) != bool(off["counts"].get("soil_mode_start")) else []),
        "R-6": ["TOUCH>2s"] if dtouch > 2.0 else [],
        "R-7": att_on is not None and att_on > 0.062,
    }
    fl, fr = r["flow"], r["flow_recomputed"]
    e_flags = [x for x, b in (("probe/READY exposure", any(k in ("probe", "ready") for k in fl["by_phase"])),
                              ("r<0.93>=7s", max(fl["long93_s"].values()) >= 7.0),
                              ("between>10mm", fl["tracking_mm"]["max_between_legs_mm"] > 10.0),
                              ("swap>1Hz", fl["swaps"]["max_disjoint_swaps_in_1s"] > 1)) if b]
    row = {
        "id": cid, "case": r["case"], "phase": [on["final_phase"], off["final_phase"]],
        "off_rejudge_equals_stored_checks": len(r["off_rejudge_checks_diff"]) <= 1,
        "p3_on": pon, "p3_off": poff, "T1_flips": flips, "T2_new_fault_warn": fault_new,
        "new_events": new_events, "gone_events": gone_events,
        "F_min_kN": [on["F_min_after_departure_kN"], off["F_min_after_departure_kN"]], "F_leg": [on["F_min_leg"], off["F_min_leg"]],
        "F_t_s": [on["F_min_t_s"], off["F_min_t_s"]], "dF_kN": dF,
        "F_twist_removed_kN": [on["F_min_twist_removed_kN"], off["F_min_twist_removed_kN"]], "dF_twist_removed_kN": dF_tw,
        "F_first8_kN": [on["F_min_first8_kN"], off["F_min_first8_kN"]],
        "mean1s_first8_kN": [on["mean1s_min_first8_kN"], off["mean1s_min_first8_kN"]],
        "tau_te_mm": [on["tau_te_mm"], off["tau_te_mm"]], "D_te_kN": [on["D_te_kN"], off["D_te_kN"]], "D_lift_kN": [on["D_lift_kN"], off["D_lift_kN"]],
        "latch_same_pattern": None, "touch_end_s": [on["touch_end_s"], off["touch_end_s"]], "dtouch_s": dtouch,
        "t_departure_s": [on["t_departure_s"], off["t_departure_s"]],
        "ready_s": [on["ready_s"], off["ready_s"]], "dready_first_s": dready, "done_s": [on["done_s"], off["done_s"]],
        "att_deg": [att_on, att_off], "end_abs_deg": [end_on, end_off], "datt_deg": datt,
        "D_peak_kN": [on["D_peak_abs_after_dep_kN"], off["D_peak_abs_after_dep_kN"]], "dD_kN": dD,
        "D_done_kN": [on.get("D_at_first_done_kN"), off.get("D_at_first_done_kN")],
        "gap_mm": [pon["P3-5_mm"], poff["P3-5_mm"]], "dgap_mm": dgap,
        "stroke_read_mm": [max(on["stroke_reading_max_mm"]), max(off["stroke_reading_max_mm"])], "dstroke_mm": dstroke,
        "guard_margin_mm": [on["guard_margin_mm"], off["guard_margin_mm"]],
        "loc_delay_s": [pon["P3-2_s"], poff["P3-2_s"]], "dloc_s": dloc,
        "revokes": [on["checks"]["loc_revokes"], off["checks"]["loc_revokes"]],
        "bar": [on["moving_pressure"]["max_bar"], off["moving_pressure"]["max_bar"]], "saturation": [on["saturation_step_count"], off["saturation_step_count"]],
        "flags_R": flags, "flags_E": e_flags,
        "E1": {"short_s": fl["by_phase"], "deficit_L_min": fl["deficit_by_phase_L_min"]},
        "E1_recomputed_s": fr["short_s"], "E1_summary_s": fl["short_s"],
        "E2": {"min_r": fl["min_r_by_phase"], "long93_s": fl["long93_s"]}, "E2_recomputed": {"r_min": fr["r_min"], "below93_s": fr["below93_s"]},
        "E3": fl["tracking_mm"], "E3_recomputed": {"max_abs_integral_mm": fr["max_abs_integral_mm"], "between": fr["max_between_legs_mm"]},
        "E4": {"swaps": fl["swaps"]["disjoint_swaps"], "max_in_1s": fl["swaps"]["max_disjoint_swaps_in_1s"], "sets_s": fl["limited_sets"]},
        "V2": {"over_supply": fl["over_supply"], "audit_mismatch": fl["steps"]["audit_mismatches"], "demand_met_but_limited": fl["steps"]["demand_met_but_limited"]},
        "V5": r["V5"], "limited_runs_ge_0p5s": fr["runs_ge_0p5s"], "last_limited_s": fr["last_limited_rel_s"],
        "code_state_same_files": all(k[0].startswith((".files_at_start.taken", ".git_at_start", ".slope_clearance")) for k in r["code_state_diff"]),
        "settings_non_meta_diff": {k: v for k, v in r["settings_diff"].items() if k not in ("controller_meta",) and v and k != "args"},
        "args_diff": r["settings_diff"]["args"],
    }
    if cid == "S8":
        row["SA4"] = {side: {"crawler_at_stop_kN": r[f"stop_{side}"]["crawler_at_stop_kN"], "crawler_max_after_kN": r[f"stop_{side}"]["crawler_max_after_stop_kN"],
                             "limit_kN": r[f"stop_{side}"]["crawler_limit_stop_plus_0p01W_kN"], "clause_pass": r[f"stop_{side}"]["crawler_max_after_stop_kN"] <= r[f"stop_{side}"]["crawler_limit_stop_plus_0p01W_kN"],
                             "F_min_after_stop_kN": r[f"stop_{side}"]["F_min_after_stop_all_kN"], "F_min_after_stop_legs_kN": r[f"stop_{side}"]["F_min_after_stop_kN"],
                             "FAULT_STROKE_END": r[f"stop_{side}"]["FAULT_STROKE_END"], "ready": r[f"stop_{side}"]["ready_count"],
                             "pad_min_kN": r[f"stop_{side}"]["pad_normal_min_after_stop_kN"], "crawler_end_kN": r[f"stop_{side}"]["crawler_end_kN"],
                             "t_stop_s": r[f"stop_{side}"]["t_stop_s"], "event": r[f"stop_{side}"]["event"], "end_roll_pitch_deg": r[f"stop_{side}"]["end_roll_pitch_deg"]} for side in ("on", "off")}
        row["SA4"]["detail"] = stop
    return row


def oscillation(on_dir: Path, off_dir: Path, runs: list) -> dict:
    """F-6: does the attitude grow inside the limited LEVEL spans, on against off in the same phase-relative windows."""
    out = {}
    for side, d in (("on", on_dir), ("off", off_dir)):
        res = json.loads((d / "result.json").read_text(encoding="utf-8"))
        t0 = float(res["t_loop_start_s"])
        with np.load(d / "step_series.npz", allow_pickle=False) as z:
            t = np.asarray(z["t_s"]) - t0
            rp = np.asarray(z["roll_pitch_deg"])
        with np.load(d / "controller_commands.npz", allow_pickle=False) as z:
            tc = np.asarray(z["t_s"]) - t0
            u = np.asarray(z["issued_u_m_s"])
        phases = [(float(p["t_s"]) - t0, str(p["phase"]).lower()) for p in res["phases"]]
        level_start = next(x for x, n in phases if n == "level")
        sel = t >= level_start
        k = np.ones(1000) / 1000
        detr = np.column_stack([rp[sel, q] - np.convolve(rp[sel, q], k, "same") for q in range(2)])[1000:-1000]
        block = {"detrended_ptp_deg": np.ptp(detr, axis=0).round(4).tolist(), "reversals": []}
        su = np.sign(u[tc >= level_start])
        for q in range(4):
            s = su[:, q]
            s = s[s != 0]
            block["reversals"].append(int((s[1:] != s[:-1]).sum()))
        for lo, hi in runs:
            if lo < level_start:
                continue
            m = (t >= lo) & (t <= hi + 5.0)
            d2 = np.column_stack([rp[m, q] - np.convolve(rp[m, q], k, "same") for q in range(2)])
            block.setdefault("limited_spans", []).append({"span": [lo, hi], "ptp_within_plus5s_deg": np.ptp(d2[500:-500], axis=0).round(4).tolist()})
        out[side] = block
    return out


def clip_compare(row: dict, summary: dict) -> dict:
    s = summary[f"CL_{ALIAS[row['id']]}_eta0.85"]
    f = lambda k: None if s[k] in ("", None) else float(s[k])
    chrono = {"F": row["dF_kN"], "stroke": row["dstroke_mm"], "gap": row["dgap_mm"], "ready": row["dready_first_s"]}
    clip = {"F": f("min_true_force_after_off_kN_delta"), "stroke": f("max_motor_stroke_mm_delta"), "gap": f("rut_ready_mm_delta"), "ready": f("t_ready_s_delta")}
    out = {"reduced_case": ALIAS[row["id"]], "class": [s["class_on"], s["class_off"]], "items": {},
           "probe_rounds_reduced": [f("probe_rounds_on"), f("probe_rounds_off")]}
    for k, lim in LIM.items():
        a, b = chrono[k], clip[k]
        diff = None if a is None or b is None else a - b
        out["items"][k] = {"chrono_delta": a, "clip_delta": b, "diff": diff, "limit": lim, "within": None if diff is None else abs(diff) <= lim}
    return out


def clip_verdict() -> dict:
    spec = importlib.util.spec_from_file_location("judge_verdict", VERDICT / "judgement/judge_verdict.py")
    jv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(jv)
    jv.V = CLIP
    out = {}
    for cid in ("S1", "S2", "S3", "S4", "S5", "S7", "S8"):
        off = jv.load(f"CL_OFF_{cid}")
        for eta in ("0.85", "0.90"):
            run = f"CL_{cid}_eta{eta}"
            on = jv.load(run)
            fl, missing = jv.flips(on, off)
            fl = [x for x in fl if not x["row"].startswith(("item", "S8C1"))]
            fnew = sorted(set(on["values"]["events"]["fault_events"]) - set(off["values"]["events"]["fault_events"]))
            wnew = sorted(set(on["values"]["events"]["warn_events"]) - set(off["values"]["events"]["warn_events"]))
            fa = on["values"]["forces"]["after_liftoff"]["min_kN"]
            fb = off["values"]["forces"]["after_liftoff"]["min_kN"]
            h_on, h_off = jv.h6_class(on, cid), jv.h6_class(off, cid)
            rec = jv.record_rows(on, off, cid)
            out[run] = {"T1_flips": fl, "missing": missing, "class": [on.get("harness_class"), off.get("harness_class")],
                        "final_phase": [on["final_phase"], off["final_phase"]], "new_fault": fnew, "new_warn": wnew,
                        "T3a": fa < jv.F_T3 and fb >= jv.F_T3, "T3b_on": h_on, "T3b_off": h_off,
                        "T3b_change": h_off["class"] == "margin_pass" and h_on["class"] != "margin_pass",
                        "F": [fa, fb], "ready": [rec["ready_on"], rec["ready_off"]], "rut": [rec["rut_on"], rec["rut_off"]],
                        "stroke": [rec["stroke_on"], rec["stroke_off"]], "R": {k: rec[k] for k in ("R1_flag", "R2_flag", "R3_flag", "R4_flag", "R5_flag", "R6_flag", "R7_flag")},
                        "E_flags": rec["E_flags"], "E5_I_end": rec["E5_I_end"], "E5_I_max": rec["E5_I_max"], "E5_back_s": rec["E5_back_s"], "E5_at_limit": rec["E5_at_limit"]}
    return out


def t180_verdict() -> dict:
    s = json.loads((VERDICT / "followup/t180_summary.json").read_text(encoding="utf-8"))
    on, off = s["B_S1_eta0.90_t180s"], s["OFF_S1_t180s"]
    ready_on = [x[1] for x in on["phase_segments"] if x[0] == "ready"]
    ready_off = [x[1] for x in off["phase_segments"] if x[0] == "ready"]
    rut, stroke = on["rut_ready_mm"], on["max_stroke_mm"]
    return {"class": [on["harness_class"], off["harness_class"]], "final_phase": [on["final_phase"], off["final_phase"]],
            "failed_rows": [on["failed_rows"], off["failed_rows"]], "command_prefix_equal_stored": [on["command_prefix_equal_stored"], off["command_prefix_equal_stored"]],
            "first_ready_s": [ready_on[0], ready_off[0]], "ready_segments": [ready_on, ready_off],
            "last_command_s": [on["last_nonzero_command_t_s"], off["last_nonzero_command_t_s"]],
            "end_att_deg": [on["attitude"]["max_abs_last_5s_deg"], off["attitude"]["max_abs_last_5s_deg"]],
            "F_min_kN": [on["forces"]["after_liftoff"]["min_kN"], off["forces"]["after_liftoff"]["min_kN"]],
            "rut_ready_mm": [rut, off["rut_ready_mm"]], "stroke_mm": [stroke, off["max_stroke_mm"]],
            "T3a": on["forces"]["after_liftoff"]["min_kN"] < F_T3,
            "T3b_first_ready": {"ready_plus_17": ready_on[0] + 17, "gap_minus_13": rut - 13, "guard_margin": GUARD_MM - stroke},
            "T3b_last_ready": {"ready_plus_17": ready_on[-1] + 17},
            "new_events": on["events_after_first_ready"], "E5": on["E5"],
            "stored_120s_final_phase": "probe (harness run limit before the second READY)"}


def rigid_rows(t: dict) -> dict:
    out = {}
    for cid, c in t["cases"].items():
        fo, ff = c["F_min_kN"]
        ro, rf = c["ready_s"]
        ao, af = c["att_last5_deg"]
        do, df = c["D"][0]["peak_abs_D_kN"], c["D"][1]["peak_abs_D_kN"]
        go, gf = c["clearance_mm"][0]["ready_mm"], c["clearance_mm"][1]["ready_mm"]
        so, sf = c["stroke_reading_max_mm"]
        to, tf = c["touch_end_s"]
        flow = c["flow"]
        ra = c.get("reapproach") or [None, None]
        out[cid] = {
            "case": CASE_NAMES[cid], "phase": c["final_phase"], "T1_flips": c["T1_flips"], "failed_on": c["on_failed_rows"], "judge_failed": c["judge_failed"],
            "new_events": c["new_events"], "gone_events": c["gone_events"], "F_min_kN": [fo, ff], "dF_kN": fo - ff, "leg": c["F_min_leg"],
            "F_after_liftoff_s": c["F_min_after_liftoff_s"], "ready_s": [ro, rf], "dready_s": ro - rf, "att_last5_deg": [ao, af], "datt_deg": ao - af,
            "end_att_mount_deg": c["end_att_deg"], "bar": c["max_moving_bar"], "saturation": c["saturation_steps"], "rocking_deg": c["rocking_deg"],
            "D_peak_kN": [do, df], "dD_kN": do - df, "D_done_kN": [c["D"][0]["D_first_done_kN"], c["D"][1]["D_first_done_kN"]],
            "gap_mm": [go, gf], "dgap_mm": go - gf, "stroke_mm": [so, sf], "dstroke_mm": so - sf, "dtouch_s": to - tf,
            "guard_active_s": c["guard_active_s"], "reapproach": ra, "V5": c["V5"],
            "flags_R": {"R-1": (fo - ff) < -max(3.0, 0.10 * ff), "R-2": [x for x, b in (("att>+0.01", ao - af > 0.01), ("READY>+5", ro - rf > 5.0)) if b],
                        "R-3": [x for x, b in (("dD>13", do - df > 13.0), ("done>15", abs(c["D"][0]["D_first_done_kN"] or 0) > 15.0)) if b],
                        "R-4": [x for x, b in (("gap<-5", go - gf < -5.0), ("stroke>+3", so - sf > 3.0)) if b],
                        "R-6": [x for x, b in (("TOUCH>2s", to - tf > 2.0), ("guard>1s", c["guard_active_s"][0] - c["guard_active_s"][1] > 1.0)) if b],
                        "R-7": ao > 0.062},
            "flags_E": [x for x, b in (("probe/READY exposure", any(k in ("probe", "ready") for k in flow["by_phase"])), ("r<0.93>=7s", max(flow["long93_s"].values()) >= 7.0),
                                       ("between>10mm", flow["track_mm"]["max_between_legs_mm"] > 10.0)) if b],
            "E1_s": flow["by_phase"], "E_min_r": min(flow["min_r"].values()), "E_long93_s": max(flow["long93_s"].values()), "E3_between_mm": flow["track_mm"]["max_between_legs_mm"],
            "E3_max_mm": max(flow["track_mm"]["max_abs_integral_mm"].values()), "sets_s": flow["limited_sets"], "E4_swaps": flow["swaps"],
        }
    return out


CASE_NAMES = {"R2": "K24_top_fdown3.5_Fs4", "R4": "K24_top_roll5.5_Fs4", "R16": "G1L_RE1bF_FL_top_o050_Fs4", "R12": "E_G4_Fs4",
              "R6": "K0V_top_rpB_Fs0", "R8": "A_middle_rpB_Fs0", "R9": "A_bottom_rpB_Fs0"}


def main() -> None:
    soil = json.loads((HERE / "soil_tables.json").read_text(encoding="utf-8"))
    stop = json.loads((HERE / "s8_stop_detail.json").read_text(encoding="utf-8"))
    tables = json.loads((HERE / "chrono_tables.json").read_text(encoding="utf-8"))
    with (CLIP / "clip_summary.csv").open(encoding="utf-8") as f:
        clip_rows = {r["run_id"]: r for r in csv.DictReader(f)}
    out = {"criteria_sha256": SHA, "soil": {}, "rigid": rigid_rows(tables), "item8": tables["item8"]}
    for cid, r in soil["rows"].items():
        row = soil_row(cid, r, stop)
        row["clip_compare"] = clip_compare(row, clip_rows)
        row["oscillation"] = oscillation(SOIL_DIRS[cid][0], SOIL_DIRS[cid][1], r["flow_recomputed"]["runs_ge_0p5s"])
        out["soil"][cid] = row
    out["clip_verdict"] = clip_verdict()
    out["t180"] = t180_verdict()
    with (HERE / "reduced_compare.csv").open(encoding="utf-8") as f:
        out["rigid_reduced_compare"] = list(csv.DictReader(f))
    ev = tables.get("events") or {}
    out["rigid_event_overlap"] = {k: {x: v["saturation_vs_event"].get(x) for x in ("overlap_event_ramp_plus5", "max_Q_dem_event_ramp_plus5_L_min", "supply_L_min")} for k, v in ev.items()}
    (HERE / "final10.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    with (HERE / "final10_rows.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow("id case phase_on phase_off T1_flips F_on F_off dF ready_on ready_off dready att_on att_off gap_on gap_off stroke_on stroke_off bar_on bar_off".split())
        for cid, x in out["soil"].items():
            w.writerow([cid, x["case"], *x["phase"], ";".join(x["T1_flips"]), *x["F_min_kN"], x["dF_kN"], x["ready_s"][0][0] if x["ready_s"][0] else "", x["ready_s"][1][0] if x["ready_s"][1] else "",
                        x["dready_first_s"], *x["att_deg"], *x["gap_mm"], *x["stroke_read_mm"], *x["bar"]])
        for cid, x in out["rigid"].items():
            w.writerow([cid, x["case"], *x["phase"], ";".join(x["T1_flips"]), *x["F_min_kN"], x["dF_kN"], *x["ready_s"], x["dready_s"], *x["att_last5_deg"], *x["gap_mm"], *x["stroke_mm"], *x["bar"]])
    short = {k: v for k, v in out.items() if k not in ("rigid_reduced_compare",)}
    for cid, x in short["soil"].items():
        x = dict(x)
        for k in ("p3_on", "p3_off", "E2", "E2_recomputed", "V5", "args_diff", "SA4", "settings_non_meta_diff"):
            pass
    print(json.dumps({"soil": {c: {k: x[k] for k in ("T1_flips", "T2_new_fault_warn", "new_events", "gone_events", "flags_R", "flags_E", "clip_compare", "oscillation", "E1", "E1_recomputed_s", "E1_summary_s", "off_rejudge_equals_stored_checks", "code_state_same_files", "settings_non_meta_diff", "V2", "dF_kN", "dF_twist_removed_kN", "tau_te_mm", "D_te_kN", "D_lift_kN", "dtouch_s")} for c, x in out["soil"].items()},
                      "rigid": {c: {k: x[k] for k in ("T1_flips", "failed_on", "dF_kN", "dready_s", "datt_deg", "dD_kN", "dgap_mm", "dstroke_mm", "dtouch_s", "flags_R", "flags_E", "new_events", "gone_events", "rocking_deg", "guard_active_s", "reapproach")} for c, x in out["rigid"].items()},
                      "clip_verdict": {k: {x: v[x] for x in ("T1_flips", "class", "final_phase", "new_fault", "new_warn", "T3a", "T3b_change", "T3b_on", "ready", "R", "E_flags", "E5_I_max", "E5_I_end", "E5_back_s", "E5_at_limit")} for k, v in out["clip_verdict"].items()},
                      "t180": out["t180"], "overlap": out["rigid_event_overlap"]}, indent=0, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()
