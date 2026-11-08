"""D-1 Chrono SCM S-03 / S-04: D-1 fields, margins, harness pairs and a preliminary LAS-b shadow.

Inputs (read only): case folders of batch_D1-CHRONO_20261108_131710, the r76 G6 judge output,
v5/d1.jsonl (harness pairs). Output: one JSON with everything the judgement section quotes.

LAS-b shadow (spec 436.2), preliminary control-expert path:
  centre_k = p_h A_h - p_r A_ann - offset (rows after the zero-calibration row), checked against
  completion_series D_raw_N = twist_vector . centre (relative error);
  L_hat = centre - allowance - seal band (band = initial_seal_band_N before the first probe end);
  rho, S7' (sum >= alpha W_ref, min < beta F_min, rho >= rho_on, rho > rho_prev, previous period LEVEL),
  S2 LEVEL, S3 before the first LOC, S4 no soil mode, S6 no re-approach (event count 0), S5 and S8
  reported (S5 taken true, S8 from the issued command mean as a proxy).
Usage: python -I d1s_judge.py <batch dir> <g6_judge.json> <d1.jsonl> <out.json>
"""
import json
import sys
from pathlib import Path

import numpy as np

CASES = {"S-03": "D1S_G1_B_middle_Fs4_spJ1FL", "S-04": "D1S_G1_B_bottom_Fs4_spJ1FL"}
HARNESS_ROW = {"S-03": "D1|H-S-A|G1+J1@FL|M|flat|K1", "S-04": "D1|H-S-A|G1+J1@FL|B|flat|K1"}
F_MIN_SEL_N = 9415.0
F_MIN_JUDGE_N = 9414.58911
S_END_M = 0.6848
ATT_LIMIT_DEG = 0.2
READY_LIMIT_S = 90.0  # spec 421.1 / d1 rules rev1: G1 base PS-a flat
ALPHA, BETA, GAMMA, RHO_ON = 0.6, 3.5, 0.16, 0.18
V_MAX = 0.0209243016
PAIR = (3, 2, 1, 0)


def margins(F, t_ready, t_lim, att, s_max):
    m = {"m_F": (F - F_MIN_SEL_N) / F_MIN_SEL_N,
         "m_a": (ATT_LIMIT_DEG - att) / ATT_LIMIT_DEG,
         "m_s": (S_END_M - s_max) / S_END_M}
    if t_ready is not None:
        m["m_T"] = (t_lim - t_ready) / t_lim
    m["m"] = min(m.values())
    return m


def rho_of(L):
    i = int(np.argmin(L))
    s = float(L.sum())
    return (s - 2.0 * (L[i] + L[PAIR[i]])) / s, i


def shadow(case, res):
    cm = res["controller_meta"]
    tp = cm["two_pressure"]
    A_h = np.asarray(tp["head_area_m2"], float)
    A_a = np.asarray(tp["annulus_area_m2"], float)
    off = np.asarray(tp["zero_offsets_N"], float)
    allow = np.asarray(tp["offset_allowance_N"], float)
    tv = np.asarray(cm["geometry"]["twist_vector"], float)
    band0 = float(cm["initial_seal_band_N"])
    W_ref = float(res["c2_soil"]["W_ref_N"])
    t_loc = res["c2_soil"]["t_loc_s"]
    soil_t = res["c2_soil"]["soil_mode_t_s"]
    with np.load(case / "record" / "record.npz") as z:
        t = z["t"].copy(); ph_ = z["meas.head_pressure"].copy(); pr = z["meas.rod_pressure"].copy()
        Ftrue = z["F_cyl"].copy()
    with np.load(case / "r8_series.npz") as z:
        assert np.allclose(z["t"], t, atol=1e-9)
        phase = z["phase"].astype(str); u = z["issued_u"].copy()
    with np.load(case / "completion_series.npz") as z:
        assert np.allclose(z["t_s"], t, atol=1e-9)
        Draw = z["D_raw_N"].copy()
    cal_t = min(e["t_s"] for e in res["events"] if e["name"].startswith("INFO_PRESSURE_ZERO_CALIBRATED"))
    k_cal = int(np.searchsorted(t, cal_t - 1e-9))  # row of the event
    net = ph_ * A_h - pr * A_a
    centre = net.copy()
    centre[k_cal + 1:] -= off
    D_rec = centre @ tv
    ok = np.isfinite(Draw)
    rel = np.abs(D_rec[ok] - Draw[ok]) / np.maximum(np.abs(Draw[ok]), 1.0)
    # judged window: LEVEL after update, before the first LOC
    rows = []
    rho_prev = None
    prev_level = False
    reapproach_none = res["p3b_ext"]["event_counts"].get("leg_reapproach_start", 0) == 0
    for k in range(t.size):
        lvl = phase[k] == "level"
        if not lvl:
            rho_prev, prev_level = None, False
            continue
        before_loc = t_loc is None or t[k] < t_loc - 1e-9
        L = centre[k] - allow - band0
        rho, i = rho_of(L)
        S = float(L.sum())
        ubar = float(u[k].mean())
        s7 = (prev_level and rho_prev is not None and S >= ALPHA * W_ref and L.min() < BETA * F_MIN_JUDGE_N
              and rho >= RHO_ON and rho > rho_prev)
        rho_true, _ = rho_of(Ftrue[k])
        if before_loc or (t_loc is not None and t[k] < t_loc + 1.0):
            rows.append({"t_s": round(float(t[k]), 3), "before_loc": bool(before_loc),
                         "L_hat_kN": [round(x / 1e3, 3) for x in L], "sum_over_W": round(S / W_ref, 4),
                         "min_over_Fmin": round(float(L.min()) / F_MIN_JUDGE_N, 3), "rho": round(rho, 4),
                         "rho_true_Fcyl": round(rho_true, 4), "light_leg": int(i),
                         "ubar_over_vmax_issued": round(ubar / V_MAX, 3), "S7p": bool(s7),
                         "fires_if_S5_S8_true": bool(s7 and before_loc and soil_t is None and reapproach_none)})
        rho_prev, prev_level = rho, True
    pre = [r for r in rows if r["before_loc"]]
    return {"D_raw_check": {"rows": int(ok.sum()), "max_rel": float(rel.max()), "max_abs_N": float(np.abs(D_rec[ok] - Draw[ok]).max())},
            "zero_cal_row_t_s": float(t[k_cal]), "band_N": band0, "W_ref_N": W_ref, "t_loc_s": t_loc,
            "soil_mode_t_s": soil_t, "reapproach_none": reapproach_none,
            "pre_loc_level_periods": len(pre),
            "rho_max_pre_loc": max((r["rho"] for r in pre), default=None),
            "rho_true_max_pre_loc": max((r["rho_true_Fcyl"] for r in pre), default=None),
            "fires": any(r["fires_if_S5_S8_true"] for r in pre),
            "S7p_any_pre_loc": any(r["S7p"] for r in pre), "rows": rows}


def main(batch, judge_json, d1_jsonl, out):
    batch = Path(batch)
    judge = {c["case"]: c for c in json.loads(Path(judge_json).read_text(encoding="utf-8"))["cases"]}
    harness = {}
    for line in Path(d1_jsonl).read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        d = r.get("d1") or {}
        if d.get("row_key") in HARNESS_ROW.values():
            m = margins(d["F_judged_min_N"], d["t_ready_s"], d["t_ready_limit_s"], d["att_judged_deg"], d["stroke_max_m"])
            harness[d["key"]] = {"verdict": d["verdict"], "fail_items": d["fail_items"],
                                 "F_judged_kN": round(d["F_judged_min_N"] / 1e3, 3),
                                 "F_first_level_kN": round(d["F_first_level_min_N"] / 1e3, 3),
                                 "t_ready_s": d["t_ready_s"], "att_deg": round(d["att_judged_deg"], 4),
                                 "stroke_max_mm": round(d["stroke_max_m"] * 1e3, 2),
                                 "j_p3": d["j_p3"], "dsb75": len(d["dsb75_events"]),
                                 **{k: round(v, 4) for k, v in m.items()}}
    outd = {"cases": {}, "harness": harness}
    for rid, name in CASES.items():
        case = batch / name
        res = json.loads((case / "result.json").read_text(encoding="utf-8"))
        j = judge[name]
        with np.load(case / "step_series.npz") as z:
            ts = z["t_s"].copy(); F = z["F_cyl_N"].copy(); s = z["s_motor_m"].copy()
        t0 = res["t_loop_start_s"]
        ph = res["phases"]
        t_level = next(p["t_s"] for p in ph if p["phase"] == "level")
        t_done = next((p["t_s"] for p in ph if p["phase"] == "done"), None)
        sel = (ts >= t_level - 1e-9) & (ts <= (t_done if t_done is not None else ts[-1]) + 1e-9)
        F_first_level = float(F[sel].min())
        F_judged = float(min(j["F_min_after_departure_kN"])) * 1e3
        p3b = res["p3b"]
        F_judged_exact = p3b["P3-3_leg_force"]
        t_ready = j["t_ready_rel_s"]
        att = float(res["p3b"]["checks"]["P3-4_absmax_deg"])
        s_max = float(s.max())
        m = margins(F_judged, t_ready, READY_LIMIT_S, att, s_max)
        ebc = res["hydraulics_record"]["extend_bound_check"]
        names = [e["name"] for e in res["events"]]
        outd["cases"][rid] = {
            "case": name, "verdict": "pass" if j["pass"] else "fail", "gates": j["gates"], "flags": j["flags"],
            "p3_checks": {k: v for k, v in p3b["checks"].items() if k.endswith(("_within", "_verdict"))},
            "F_judged_kN_per_leg": j["F_min_after_departure_kN"], "P3-3_block": F_judged_exact,
            "F_first_level_min_kN": round(F_first_level / 1e3, 3),
            "t_ready_rel_s": round(t_ready, 2), "t_ready_limit_s": READY_LIMIT_S,
            "loc_minus_departure_s": j["loc_minus_departure_s"], "loc_limit_s": j["loc_limit_s"],
            "att_p34_absmax_deg": round(att, 4), "end_mean_roll_pitch_deg": j["end_mean_roll_pitch_deg"],
            "rut_min_after_ready_mm": j["rut_min_after_ready_mm"], "stroke_max_mm": round(s_max * 1e3, 2),
            "P3-6": j["P3-6"], "P3-7": j["P3-7"],
            "margins": {k: round(v, 4) for k, v in m.items()},
            "phases_rel_s": j["phases_rel_s"], "events": names,
            "faults": [n for n in names if n.startswith("FAULT")], "warns": [n for n in names if n.startswith("WARN")],
            "dsb75": res["controller_meta"]["diff_sink"],
            "j_p3": {"breach_reads_sum": int(sum(ebc["breach_reads"])), "margin_used_sum": int(sum(ebc["margin_used_reads"])),
                     "locked_breach_over_tol_sum": int(sum(ebc["locked_breach_over_tol_reads"])),
                     "min_gap_bar": min(ebc["min_gap_bar"]), "has_rod_sensor": res["controller_meta"]["two_pressure"]["has_rod_sensor"]},
            "m2": {"shift_mm": res["hydraulics_record"]["m2_shift_total_mm"], "clipped": res["hydraulics_record"]["m2_clipped_steps"],
                   "clip_times_s": res["hydraulics_record"]["m2_clip_times_s"]},
            "controller_tag": res["v5_hydraulics"]["controller_tag"], "git_head": res["code_state"]["git_at_start"]["head"],
            "pressure_max_moving": res.get("monitor", {}).get("cylinder_force_max_N"),
            "las_shadow": shadow(case, res)}
    Path(out).write_text(json.dumps(outd, indent=1), encoding="utf-8")
    for rid, c in outd["cases"].items():
        sh = c["las_shadow"]
        print(rid, c["verdict"], c["margins"], "F1L", c["F_first_level_min_kN"], "READY", c["t_ready_rel_s"],
              "stroke", c["stroke_max_mm"], "JP3", c["j_p3"])
        print("   shadow D_raw", sh["D_raw_check"], "periods", sh["pre_loc_level_periods"], "rho_max", sh["rho_max_pre_loc"],
              "rho_true_max", sh["rho_true_max_pre_loc"], "S7p", sh["S7p_any_pre_loc"], "fires", sh["fires"])
    for k, v in sorted(harness.items()):
        print(k, v["verdict"], "F", v["F_judged_kN"], "m", v["m"], "READY", v["t_ready_s"], "att", v["att_deg"])


if __name__ == "__main__":
    main(*sys.argv[1:5])
