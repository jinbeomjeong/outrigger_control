"""Spec rev. 44 (question c): decomposition of the 7c probe load-estimate error, F_s 8 vs F_s 0.

Per probe row (first round, judged legs): estimate E (controller midpoint), truth T0 (mean true
F_cyl over 0.5 s before the first move), true F_cyl at the two hold ends T1, T2 (mean +-0.1 s),
readings R1, R2 (controller nominal reading at the hold-end control instant), seal friction f
(pads f_seal) at the hold ends, rod stroke at the hold ends (record meas.stroke).
  E - T0 = [0.5(R1 + R2) - 0.5(T1 + T2)]     (friction / reading term, ~ -0.5 (f1 + f2))
         + [0.5(T1 + T2) - T0]               (load change over the round trip)
         - 0.5 S_c (s1 - s2)                 (stroke-gap correction, S_c = implied)
S_c is implied from E: S_c = (0.5(R1 + R2) - E) / (0.5 (s1 - s2)).
Also the "true" secant S_true = (T1 - T2) / (s1 - s2) over the return move.
Usage: python -I s8p1r_7c.py <batch dir> <out json> case [case ...]
"""
import sys, os, json
import numpy as np

BASE, OUT, CASES = sys.argv[1], sys.argv[2], sys.argv[3:]
T0 = 3.0
out = {}
for case in CASES:
    d = os.path.join(BASE, case)
    ph = json.load(open(os.path.join(d, "probe_history.json"), encoding="utf-8"))
    pads = np.load(os.path.join(d, "pads.npz"))
    r8 = np.load(os.path.join(d, "r8_series.npz"))
    rec = np.load(os.path.join(d, "record", "record.npz"))
    tp = pads["t"]
    Fc = pads["F_cyl"]
    fs = pads["f_seal"]
    t8 = r8["t"]

    def mean_near(arr, t, leg, w=0.1):
        s = (tp >= t - w) & (tp <= t + w)
        return float(arr[s, leg].mean())

    def mean_before(arr, t, leg, w=0.5):
        s = (tp >= t - w) & (tp < t)
        return float(arr[s, leg].mean())

    def at8(arr, t, leg):
        k = int(np.argmin(np.abs(t8 - t)))
        return float(arr[k, leg])

    rows = []
    for rnd, round_rows in enumerate(ph[:1]):
        for r in round_rows:
            if r.get("is_skipped") or r.get("t_move_start_s") is None:
                continue
            leg = r["leg_index"]
            # probe times are controller-reported record times (same base as pads 't')
            ta, t1, t2 = r["t_move_start_s"], r["t_first_hold_end_s"], r["t_second_hold_end_s"]
            T0v = mean_before(Fc, ta, leg)
            T1, T2 = mean_near(Fc, t1, leg), mean_near(Fc, t2, leg)
            R1, R2 = at8(r8["F_nominal_N"], t1, leg), at8(r8["F_nominal_N"], t2, leg)
            s1, s2 = at8(rec["meas.stroke"], t1, leg), at8(rec["meas.stroke"], t2, leg)
            f0 = mean_before(fs, ta, leg)
            f1, f2 = mean_near(fs, t1, leg), mean_near(fs, t2, leg)
            E = r["load_estimate_N"]
            gap = s1 - s2
            Sc = (0.5 * (R1 + R2) - E) / (0.5 * gap) if abs(gap) > 1e-6 else float("nan")
            St = (T1 - T2) / gap if abs(gap) > 1e-6 else float("nan")
            limit = max(5e3, 0.1 * abs(T0v))
            rows.append(dict(leg=leg, E_kN=E / 1e3, T0_kN=T0v / 1e3, err_kN=(E - T0v) / 1e3,
                             margin_kN=(abs(E - T0v) - limit) / 1e3,
                             term_reading_kN=(0.5 * (R1 + R2) - 0.5 * (T1 + T2)) / 1e3,
                             term_roundtrip_kN=(0.5 * (T1 + T2) - T0v) / 1e3,
                             term_gap_kN=-(0.5 * Sc * gap) / 1e3,
                             f0_kN=f0 / 1e3, f1_kN=f1 / 1e3, f2_kN=f2 / 1e3,
                             gap_mm=gap * 1e3, S_c_MN_m=Sc / 1e6, S_true_MN_m=St / 1e6,
                             Fs_est_kN=r["seal_friction_estimate_N"] / 1e3,
                             S_incr_MN_m=r["incremental_stiffness_N_m"] / 1e6,
                             # E* = 0.5 (T1 + T2) - 0.5 S_true gap = T2 (exact estimator of the
                             # load at the end of the probe): E - T0 = (E - T2) + (T2 - T0)
                             est_vs_end_kN=(E - T2) / 1e3, hyst_kN=(T2 - T0v) / 1e3))
    out[case] = rows
    w = max(rows, key=lambda x: x["margin_kN"])
    print(f"{case:26s} worst {('FL', 'FR', 'RL', 'RR')[w['leg']]} margin {w['margin_kN']:+.2f} err {w['err_kN']:+.2f} = "
          f"est-vs-end {w['est_vs_end_kN']:+.2f} + hysteresis {w['hyst_kN']:+.2f} kN | S_true {w['S_true_MN_m']:.2f} "
          f"S_c {w['S_c_MN_m']:.2f} MN/m | f0 {w['f0_kN']:+.2f} f2 {w['f2_kN']:+.2f} | reading term {w['term_reading_kN']:+.2f}")
    print("    all legs err:", [round(x["err_kN"], 2) for x in rows], "hyst:", [round(x["hyst_kN"], 2) for x in rows],
          "est-end:", [round(x["est_vs_end_kN"], 2) for x in rows], "S_true:", [round(x["S_true_MN_m"], 2) for x in rows])
json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1)
