"""V5-OPENLOOP-R judgement metrics (J1 SCM damping_R sensitivity, open-loop V0), prereg R-1..R-6.

Definitions follow paper_runs/scripts/prop_dip_timebase.py (R-1..R-4c) and openloop_compare.py analyse (R-6),
plus prereg section 4: R-1 definition (2) = per-leg min of F_cyl from rear contact (swivel event of RL)
to crawler lift-off (first 0.1 s run of crawler normal < 1 % W). All forces kN (cylinder force, extend +),
lengths mm, times s (absolute t; lift start 8 s). Crawler front point: body x = +1.30 m, small angle,
pitch > 0 nose down.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\paper_runs\scripts")

R = Path(r"C:\workspace\outrigger_control\07_results\S9")
B = R / "batch_V5-OPENLOOP-R_20261108_231840"
U = 0.020924
RUNS = {
    "V0_R992k": (R / "batch_V5-OPENLOOP-V0_20261108_123517/P3a_J1_B_V0", U, 1.0),
    "R888k": (B / "P3a_J1_B_V0_R888k", U, 887600 / 992000),
    "R600k": (B / "P3a_J1_B_V0_R600k", U, 600000 / 992000),
    "R300k": (B / "P3a_J1_B_V0_R300k", U, 300000 / 992000),
    "VB_prop": (R / "batch_V5-OPENLOOP-VB-PROP_20261108_164953/P3a_J1_B_VB_prop", U * 0.894736837447082, 1.0),
}
XF = 1.30
F_MIN = 9414.58911
T_LIFT = 8.0


def first_run(t, mask, hold):
    n = len(t)
    k = 0
    while k < n:
        if mask[k]:
            j = k
            while j < n and mask[j]:
                j += 1
            if t[j - 1] - t[k] >= hold - 1e-9:
                return k
            k = j
        else:
            k += 1
    return None


def runs_of(t, mask):
    """List of (t_start, t_end, n_samples) for contiguous true runs."""
    out = []
    idx = np.nonzero(mask)[0]
    if not idx.size:
        return out
    br = np.nonzero(np.diff(idx) > 1)[0]
    starts = np.r_[idx[0], idx[br + 1]]
    ends = np.r_[idx[br], idx[-1]]
    for a, b in zip(starts, ends):
        out.append([float(t[a]), float(t[b]), int(b - a + 1)])
    return out


def analyse(p, u, lam):
    res = json.loads((p / "result.json").read_text("utf-8"))
    z = np.load(p / "series.npz")
    t = z["t_s"]
    zb = z["body_pos_m"][:, 2]
    rp = z["roll_pitch_deg"]
    th = np.radians(rp[:, 1])
    fc = z["F_cyl_N"]
    cr = z["scm_crawler_normal_N"]
    pn = z["scm_pad_normal_N"]
    sm = z["s_motor_m"]
    sink = z["pad_sinkage_geometric_m"]
    W = res["p3a"]["weight_N"]
    ev = res["swivel"]["events"]
    first_ev = {i: min((e[0] for e in ev if e[1] == i), default=None) for i in range(4)}
    tc = first_ev[2]
    tf = first_ev[0]
    kc = int(np.searchsorted(t, tc))
    kf = int(np.searchsorted(t, tf))
    lift = t > T_LIFT + 1e-9
    k = first_run(t[lift], cr[lift] < 0.01 * W, 0.1)
    klo = int(np.nonzero(lift)[0][k])
    tlo = float(t[klo])
    # R-1 definition (2): per-leg min, rear contact .. lift-off
    seg = fc[kc:klo + 1, 2:]
    j = np.argmin(seg, axis=0)
    r1 = {"F_kN": (seg[j, [0, 1]] / 1e3).tolist(), "t_s": [float(t[kc + jj]) for jj in j],
          "t_rel_front_contact_s": [float(t[kc + jj] - tf) for jj in j]}
    # R-1 definition (1): stored rule (from first > 1.4 F_min to lift-off), per leg
    r1s = {"F_kN": [], "t_s": [], "t_first_above_s": []}
    for i in (2, 3):
        idx = np.nonzero(lift & (fc[:, i] > 1.4 * F_MIN))[0]
        if not idx.size or idx[0] >= klo:
            r1s["F_kN"].append(None); r1s["t_s"].append(None); r1s["t_first_above_s"].append(None)
            continue
        s = fc[idx[0]:klo + 1, i]
        jj = int(np.argmin(s))
        r1s["F_kN"].append(float(s[jj] / 1e3)); r1s["t_s"].append(float(t[idx[0] + jj]))
        r1s["t_first_above_s"].append(float(t[idx[0]]))
    stored = res["p3a"]["P3a-9_min_cylinder_force"].get("before_liftoff")
    # prop_dip_timebase legacy: RL argmin (stored-rule window, first-sample lift-off), both legs at that index
    a = np.nonzero((t > tc) & (fc[:, 2] > 1.4 * F_MIN))[0]
    lo1 = np.nonzero((t > 8) & (cr < 0.01 * W))[0][0]
    legacy = None
    if a.size and a[0] < lo1:
        km = a[0] + int(np.argmin(fc[a[0]:lo1 + 1, 2]))
        legacy = {"F_kN": (fc[km, 2:] / 1e3).tolist(), "t_rel_front_contact_s": float(t[km] - tf)}
    # R-2, R-3, R-4c
    r2 = (fc[kf, 2:] / 1e3).tolist()
    r3 = (np.array(r1["F_kN"]) - np.array(r2)).tolist()
    r4c = (fc[kc:kf, 2:].max(axis=0) / 1e3).tolist()
    # R-4 crawler front sinkage by time since rear contact
    zf = (zb - XF * th) - (zb[kc] - XF * th[kc])
    by_time = {}
    for dt in (0.04, 0.08, 0.10, 0.12, 0.14):
        kk = int(np.searchsorted(t, tc + dt))
        by_time[f"{dt:.2f}"] = float(zf[kk] * 1e3)
    m = (t > tc + 0.06) & (t < tc + 0.14)
    rate = float(np.polyfit(t[m], zf[m], 1)[0] * 1e3)
    # state at rear contact (settle-state difference)
    at_c = {"z_body_mm": float(zb[kc] * 1e3), "pitch_deg": float(np.degrees(th[kc])), "crawler_kN": float(cr[kc] / 1e3),
            "crawler_over_W": float(cr[kc] / W)}
    # R-5(b): rear SCM pad normal <= 0 after rear contact (to lift-off, and to end)
    r5b = {}
    for name, i in (("RL", 2), ("RR", 3)):
        kci = int(np.searchsorted(t, first_ev[i]))
        mk = np.zeros_like(t, dtype=bool)
        mk[kci:] = pn[kci:, i] <= 0.0
        rr = runs_of(t, mk)
        r5b[name] = {"t_contact_s": first_ev[i], "n_runs": len(rr), "runs": rr[:10],
                     "n_samples_to_liftoff": int(mk[:klo + 1].sum()), "n_samples_total": int(mk.sum()),
                     "pad_N_min_contact_to_liftoff_kN": float(pn[kci:klo + 1, i].min() / 1e3)}
    # R-6
    i0 = int(np.argmax(lift)) - 1
    dt_s = float(np.median(np.diff(t)))
    w = int(round(1.0 / dt_s))
    rt = np.full_like(sink, np.nan)
    rt[w:] = (sink[w:] - sink[:-w]) / 1.0
    ok = np.all(rt < 1e-4, axis=1) & (t >= tlo)
    kk = np.nonzero(ok)[0]
    creep_first = float(t[kk[0]] - tlo) if kk.size else None
    peaks = fc[lift].max(axis=0)
    lim = np.array(res["p3a"]["limits"]["F_extend_limit_N"])
    eq = res["p3a"].get("equilibrium_rel_error")
    st = res.get("settle_last_1s", {})
    out = {
        "lambda": lam, "u_m_s": u,
        "t_contact_s": first_ev, "t_rear_contact_s": tc, "t_front_contact_s": tf,
        "R1_def2": r1, "R1_def1_stored_rule_recomputed": r1s, "R1_stored_p3a9": stored, "R1_legacy_prop_dip": legacy,
        "R1_linear_pred_kN": 11.70 - 23.4 * (1 - lam),
        "R2_kN": r2, "R3_kN": r3, "R4c_kN": r4c,
        "R4c_ratio_to_V0": None,
        "R4_dz_front_mm": by_time, "R4_rate_mm_s": rate,
        "R4b_gap_s": tf - tc, "R4b_gap_sref_mm": (tf - tc) * u * 1e3,
        "R5a_flag": [v < F_MIN / 1e3 for v in r1["F_kN"]], "R5a_margin_kN": [v - F_MIN / 1e3 for v in r1["F_kN"]],
        "R5b": r5b,
        "state_at_rear_contact": at_c,
        "settle_last_1s": {"pitch_mean_deg": st.get("pitch_mean_deg"), "z_origin_mean_mm": st.get("z_origin_mean_mm"),
                           "roll_mean_deg": st.get("roll_mean_deg"), "normal_over_weight": st.get("normal_over_weight")},
        "R6": {"t_liftoff_s": tlo, "t_liftoff_after_start_s": tlo - T_LIFT,
               "stored_liftoff_s": res["p3a"]["P3a-2_liftoff"]["t_liftoff_s"],
               "sink_end_mm": (sink[-1] * 1e3).tolist(), "sink_at_liftoff_mm": (sink[klo] * 1e3).tolist(),
               "creep_after_liftoff_mm": ((sink[-1] - sink[klo]) * 1e3).tolist(),
               "creep_stop_first_s": creep_first,
               "d_roll_pitch_end_deg": (rp[-1] - rp[i0]).tolist(),
               "F_peak_kN": (peaks / 1e3).tolist(), "F_peak_ratio_max": float((peaks / lim).max()),
               "s_motor_max_mm": float(sm.max() * 1e3),
               "p3a_checks": res["p3a"]["checks"], "equilibrium_rel_error": eq,
               "stored_creep_stop": res["p3a"].get("creep_stop")},
        "soil_damping_R_recorded": res["meta"]["scm"]["soil"]["chrono"]["damping_R"] if "scm" in res["meta"] else None,
        "wall_s": res.get("wall_s"), "us_per_step": res.get("us_per_step"), "threads": res["args"].get("threads"),
        "placement": res.get("placement", {}).get("mode"),
        "params_sha256": res["meta"].get("params_sha256"), "scm_run_sha256": res["meta"].get("scm_run_sha256"),
    }
    return out


out = {}
for name, (p, u, lam) in RUNS.items():
    out[name] = analyse(p, u, lam)
v0 = np.array(out["V0_R992k"]["R4c_kN"])
for name in out:
    out[name]["R4c_ratio_to_V0"] = (np.array(out[name]["R4c_kN"]) / v0).tolist()
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, default=float), "utf-8")
for name, o in out.items():
    print("==", name, "lam %.4f" % o["lambda"])
    print("  R1 def2", [round(v, 3) for v in o["R1_def2"]["F_kN"]], [round(v, 4) for v in o["R1_def2"]["t_rel_front_contact_s"]])
    print("  R1 def1", o["R1_def1_stored_rule_recomputed"], "stored", o["R1_stored_p3a9"])
    print("  legacy", o["R1_legacy_prop_dip"], "lin", round(o["R1_linear_pred_kN"], 2))
    print("  R2", [round(v, 3) for v in o["R2_kN"]], "R3", [round(v, 3) for v in o["R3_kN"]],
          "R4c", [round(v, 3) for v in o["R4c_kN"]], "ratio", [round(v, 4) for v in o["R4c_ratio_to_V0"]])
    print("  R4", {k: round(v, 3) for k, v in o["R4_dz_front_mm"].items()}, "rate", round(o["R4_rate_mm_s"], 3))
    print("  R4b", round(o["R4b_gap_s"], 4), round(o["R4b_gap_sref_mm"], 3), "contacts", o["t_contact_s"])
    print("  R5a", o["R5a_flag"], [round(v, 3) for v in o["R5a_margin_kN"]])
    print("  R5b", {k: (v["n_runs"], v["n_samples_to_liftoff"], v["n_samples_total"], round(v["pad_N_min_contact_to_liftoff_kN"], 3), v["runs"][:3]) for k, v in o["R5b"].items()})
    print("  at contact", o["state_at_rear_contact"], "settle", o["settle_last_1s"])
    r6 = o["R6"]
    print("  R6 lo", round(r6["t_liftoff_after_start_s"], 4), "stored", r6["stored_liftoff_s"],
          "sink_end", [round(v, 2) for v in r6["sink_end_mm"]], "creep", [round(v, 2) for v in r6["creep_after_liftoff_mm"]],
          "cstop", r6["creep_stop_first_s"], "stored_cs", r6["stored_creep_stop"])
    print("  R6 att", [round(v, 4) for v in r6["d_roll_pitch_end_deg"]], "pkratio", round(r6["F_peak_ratio_max"], 4),
          "smax", round(r6["s_motor_max_mm"], 2), "checks", r6["p3a_checks"], "eq", r6["equilibrium_rel_error"])
    print("  R", o["soil_damping_R_recorded"], "thr", o["threads"], o["placement"], "wall", o["wall_s"])
