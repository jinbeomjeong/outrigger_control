"""Spec rev. 45 item 2: offline replay of the probe midpoint correction on recorded probes.

For every probed leg (all rounds, not skipped, extend first) of a batch, from the controller's
10 Hz readings (r8 ``F_nominal_N``) and rod stroke (record ``meas.stroke_corrected``):

* ``E_rec``   recorded controller estimate (``load_estimate_N``).
* ``E_cur``   reconstruction 0.5 (R1 + R2) - 0.5 S_inc g  (S_inc = recorded incremental stiffness).
* ``E_ret2``  correction by the return-move second-half tangent (R_mid,ret - R2) / (y_mid,ret - y2).
* ``E_avg``   correction by the mean of S_inc and the return second-half tangent.
* ``E_retsec`` correction by the reading return secant (R1 - R2) / g (contains 2 F_s / g).

Truths from the 1 ms pad record: T0 (mean F_cyl 0.5 s before the move), T2 (mean +-0.1 s at the
second hold end); seal friction truth 0.5 |f1 - f2|. Seal estimates 0.5 (R1 - R2 - S g).
Usage: python -I s8_rev45_probe_correction.py <batch dir> <out json>
"""
import json
import os
import sys

import numpy as np

BASE, OUT = sys.argv[1], sys.argv[2]
LEGS = ("FL", "FR", "RL", "RR")
rows = []
for case in sorted(os.listdir(BASE)):
    d = os.path.join(BASE, case)
    ph_path = os.path.join(d, "probe_history.json")
    if not os.path.isfile(ph_path):
        continue
    ph = json.load(open(ph_path, encoding="utf-8"))
    pads = np.load(os.path.join(d, "pads.npz"))
    r8 = np.load(os.path.join(d, "r8_series.npz"))
    rec = np.load(os.path.join(d, "record", "record.npz"))
    tp, Fc, fs = pads["t"], pads["F_cyl"], pads["f_seal"]
    t8, R = r8["t"], r8["F_nominal_N"]
    tr, y, sm = rec["t"], rec["meas.stroke_corrected"], rec["meas.stroke"]

    def k8(t):
        return int(np.argmin(np.abs(t8 - t)))

    def kr(t):
        return int(np.argmin(np.abs(tr - t)))

    def mean_near(a, t, leg, w=0.1):
        s = (tp >= t - w) & (tp <= t + w)
        return float(a[s, leg].mean())

    def mean_before(a, t, leg, w=0.5):
        s = (tp >= t - w) & (tp < t)
        return float(a[s, leg].mean())

    for rnd, round_rows in enumerate(ph):
        for r in round_rows:
            if r.get("is_skipped") or r.get("is_reversed") or r.get("t_move_start_s") is None:
                continue
            leg = r["leg_index"]
            ta, t1, t2 = r["t_move_start_s"], r["t_first_hold_end_s"], r["t_second_hold_end_s"]
            i1, i2 = k8(t1), k8(t2)
            j1, j2 = kr(t1), kr(t2)
            R1, R2 = float(R[i1, leg]), float(R[i2, leg])
            y1, y2 = float(y[j1, leg]), float(y[j2, leg])
            g = y1 - y2
            S_inc = float(r["incremental_stiffness_N_m"])
            # return-move mid sample: motor stroke closest to the midpoint between the hold ends
            m1, m2 = float(sm[j1, leg]), float(sm[j2, leg])
            seg = np.arange(j1, j2 + 1)
            jm = int(seg[np.argmin(np.abs(sm[seg, leg] - 0.5 * (m1 + m2)))])
            im = k8(float(tr[jm]))
            Rm, ym = float(R[im, leg]), float(y[jm, leg])
            S_ret2 = (Rm - R2) / (ym - y2) if abs(ym - y2) > 1e-7 else float("nan")
            S_retsec = (R1 - R2) / g if abs(g) > 1e-7 else float("nan")
            mid = 0.5 * (R1 + R2)
            T0 = mean_before(Fc, ta, leg)
            T1, T2 = mean_near(Fc, t1, leg), mean_near(Fc, t2, leg)
            f1, f2 = mean_near(fs, t1, leg), mean_near(fs, t2, leg)

            def est(S):
                return mid - 0.5 * S * g, 0.5 * (R1 - R2 - S * g)

            E_cur, Fs_cur = est(S_inc)
            E_r2, Fs_r2 = est(S_ret2)
            S_avg = 0.5 * (S_inc + S_ret2)
            E_avg, Fs_avg = est(S_avg)
            E_rs, Fs_rs = est(S_retsec)
            rows.append(dict(
                case=case, round=rnd, leg=LEGS[leg], grounded=bool(r["is_grounded"]),
                gap_mm=g * 1e3, S_inc=S_inc / 1e6, S_ret2=S_ret2 / 1e6, S_retsec=S_retsec / 1e6,
                S_true_ret=(T1 - T2) / g / 1e6 if abs(g) > 1e-7 else float("nan"),
                E_rec_minus_cur=(r["load_estimate_N"] - E_cur) / 1e3,
                T2_minus_T0=(T2 - T0) / 1e3,
                bias_T2=dict(cur=(E_cur - T2) / 1e3, ret2=(E_r2 - T2) / 1e3,
                             avg=(E_avg - T2) / 1e3, retsec=(E_rs - T2) / 1e3),
                Fs_true=0.5 * abs(f1 - f2) / 1e3,
                Fs_est=dict(rec=r["seal_friction_estimate_N"] / 1e3, cur=Fs_cur / 1e3,
                            ret2=Fs_r2 / 1e3, avg=Fs_avg / 1e3, retsec=Fs_rs / 1e3),
                T2_kN=T2 / 1e3))

summary = {}
for key in ("cur", "ret2", "avg", "retsec"):
    b = np.array([x["bias_T2"][key] for x in rows])
    e = np.array([x["Fs_est"][key] - x["Fs_true"] for x in rows])
    ok = np.isfinite(b)
    summary[key] = dict(n=int(ok.sum()), bias_T2_min=float(b[ok].min()), bias_T2_max=float(b[ok].max()),
                        bias_T2_mean=float(b[ok].mean()), bias_T2_absmax=float(np.abs(b[ok]).max()),
                        Fs_err_min=float(e[ok].min()), Fs_err_max=float(e[ok].max()),
                        Fs_err_mean=float(e[ok].mean()))
recon = max(abs(x["E_rec_minus_cur"]) for x in rows)
summary["reconstruction_absmax_kN"] = recon
# by friction group
for grp, pref in (("Fs0", "_Fs0"), ("Fs8", "_Fs8")):
    sel = [x for x in rows if x["case"].endswith(pref) or (pref + "_") in x["case"]]
    if not sel:
        continue
    summary[grp] = {key: dict(
        bias_max=float(np.nanmax([x["bias_T2"][key] for x in sel])),
        bias_min=float(np.nanmin([x["bias_T2"][key] for x in sel])),
        Fs_err_min=float(np.nanmin([x["Fs_est"][key] - x["Fs_true"] for x in sel])),
        Fs_err_max=float(np.nanmax([x["Fs_est"][key] - x["Fs_true"] for x in sel])))
        for key in ("cur", "ret2", "avg")}
    summary[grp]["n"] = len(sel)
json.dump(dict(summary=summary, rows=rows), open(OUT, "w", encoding="utf-8"), indent=1)
print(json.dumps(summary, indent=1))
