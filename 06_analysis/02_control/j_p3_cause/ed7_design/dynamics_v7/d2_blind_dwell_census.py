"""Ed. 7 dynamics review Q7-D1, step 2 (dynamics-expert, 2026-11-24; analysis only, read only).

Census over the ed. 6 records run B (``records_after_stop/B_a1``: j9_main 388 lines VBL / LSL1-4,
sensitivity 184 lines; seen rows, spec v7 O7-1) and C (60 lines) of every LEVEL segment:

  (1) blind dwells that would meet the A(i)-b trigger 1 (locked, one sign, 0 < |u| <= u_hold,
      >= N_blind = 20 periods; trigger 2 "no motion" holds by construction while locked;
      trigger 3 "completion not met" is not in the T4h and is NOT applied - an upper bound on
      the trigger count);
  (2) at the would-be trigger read: true leg forces, twist load D = n . F_true, legs in the band,
      and the forces after a predicted shot of every in-band leg by Delta e = 0.75 mm in its
      command sign (rank-1 law dF = S de, S built from the leg stiffnesses with the shooting
      legs moving and the others locked; a bound on one round of shots);
  (3) ed. 6 A(i) episodes that start late in a LEVEL (all true leg forces >= 40 kN at the start,
      i.e. not the event response): stroke travel from the read before the start to one period
      after the end (the d = 1 tail), and the measured change of D over the same span = the
      empirical shot quantum.

Conventions as d1 (body x fwd, y left; FL, FR, RL, RR; compression +; motor/oil stroke).
Output: CSV + TXT at --out-prefix. stdout ASCII.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405"
           r"\records_after_stop")
DIRS = {"B_j9_main": RUN / "B_a1" / "j9_main_t4h", "B_sens": RUN / "B_a1" / "sens_t4h",
        "C_cf": RUN / "C_a2" / "counterfactual_t4h"}
B3_JSON = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design"
               r"\dynamics_v6\b3_twist_stiffness.json")
LEGS = ("FL", "FR", "RL", "RR")
U_HOLD = 2.09243016e-4
N_BLIND = 20
F_MIN = 9414.58911
SHOT_M = 0.75e-3


def segments(phase):
    out, start = [], 0
    for i in range(1, len(phase) + 1):
        if i == len(phase) or phase[i] != phase[start]:
            out.append((str(phase[start]), start, i - 1))
            start = i
    return out


def runs(flag):
    out, i, n = [], 0, len(flag)
    while i < n:
        if flag[i]:
            j = i
            while j + 1 < n and flag[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-prefix", required=True)
    args = ap.parse_args()
    b3 = json.loads(B3_JSON.read_text(encoding="utf-8"))
    n = np.array(b3["n"])
    k_move = np.array(b3["variants"]["move_harness_R12"]["k_leg_MN_m"]) * 1e6
    k_lock = np.array(b3["variants"]["lock_harness_R12"]["k_leg_MN_m"]) * 1e6

    def S_of(moving):
        k = np.where(moving, k_move, k_lock)
        return np.outer(n, n) / float(np.sum(n**2 / k))

    dwell_rows, ep_rows = [], []
    n_lines = {}
    for tag, folder in DIRS.items():
        files = sorted(folder.glob("*.npz"))
        n_lines[tag] = len(files)
        for path in files:
            with np.load(path, allow_pickle=False) as d:
                t, ph, u = d["t_s"], d["phase"], d["command_m_s"]
                lk, F, s = d["locked"], d["true_force_N"], d["motor_stroke_m"]
                a1 = d["lsb_a1_on"] if "lsb_a1_on" in d.files else None
            band = lk & (np.abs(u) > 1e-12) & (np.abs(u) <= U_HOLD)
            levels = [g for g in segments(ph) if g[0] == "level"]
            for li, (_, i0, i1) in enumerate(levels):
                for leg in range(4):
                    flag = band[:, leg].copy()
                    flag[:i0] = False
                    flag[i1 + 1:] = False
                    sgn = np.sign(u[:, leg])
                    for a, b in runs(flag):
                        cut = [a] + [k for k in range(a + 1, b + 1) if sgn[k] != sgn[k - 1]] + [b + 1]
                        for p, q in zip(cut[:-1], cut[1:]):
                            if q - p < N_BLIND:
                                continue
                            k_t = p + N_BLIND - 1
                            inband = band[k_t].copy()
                            de = np.where(inband, np.sign(u[k_t]) * SHOT_M, 0.0)
                            de_one = np.zeros(4)
                            de_one[leg] = np.sign(u[k_t, leg]) * SHOT_M
                            F_all = F[k_t] + S_of(inband) @ de
                            mv = np.zeros(4, bool)
                            mv[leg] = True
                            F_one = F[k_t] + S_of(mv) @ de_one
                            dwell_rows.append({
                                "set": tag, "line": path.stem, "level_index": li,
                                "n_levels": len(levels), "leg": LEGS[leg],
                                "sign": int(sgn[p]), "t_trigger_s": round(float(t[k_t]), 2),
                                "dwell_s": round((q - p) * 0.1, 1),
                                "legs_in_band": int(inband.sum()),
                                "band_signs": "".join(
                                    ("+" if u[k_t, j] > 0 else "-") if inband[j] else "0"
                                    for j in range(4)),
                                "twist_pattern": bool(inband.all() and (
                                    np.all(np.sign(u[k_t]) == np.sign(n))
                                    or np.all(np.sign(u[k_t]) == -np.sign(n)))),
                                "D_kN": round(float(n @ F[k_t]) / 1e3, 2),
                                "Fmin_kN": round(float(F[k_t].min()) / 1e3, 2),
                                "Fmin_after_one_kN": round(float(F_one.min()) / 1e3, 2),
                                "Fmin_after_all_kN": round(float(F_all.min()) / 1e3, 2),
                                "dD_one_kN": round(float(n @ (F_one - F[k_t])) / 1e3, 2),
                                "dD_all_kN": round(float(n @ (F_all - F[k_t])) / 1e3, 2),
                            })
            if a1 is None:
                continue
            for leg in range(4):
                for a, b in runs(a1[:, leg].astype(bool)):
                    a0 = max(a - 1, 0)
                    if F[a0].min() < 40e3 or str(ph[a]) != "level":
                        continue
                    e = min(b + 1, len(t) - 1)
                    ds = float(s[e, leg] - s[a0, leg])
                    dD = float(n @ (F[e] - F[a0]))
                    ep_rows.append({"set": tag, "line": path.stem, "leg": LEGS[leg],
                                    "t_on_s": round(float(t[a]), 2), "periods_on": b - a + 1,
                                    "sign": int(np.sign(u[a, leg])),
                                    "travel_mm": round(ds * 1e3, 3),
                                    "dD_kN": round(dD / 1e3, 2),
                                    "dD_per_mm_kN": round(dD / 1e3 / (ds * 1e3), 2)
                                    if abs(ds) > 1e-5 else ""})
    pre = str(Path(args.out_prefix))
    for rows, suffix in ((dwell_rows, "_dwells.csv"), (ep_rows, "_late_a1_episodes.csv")):
        if rows:
            with open(pre + suffix, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    L = [f"lines: {n_lines}", f"shot assumed {SHOT_M * 1e3:.2f} mm per in-band leg"]
    for tag in DIRS:
        rs = [r for r in dwell_rows if r["set"] == tag]
        if not rs:
            L.append(f"[{tag}] blind dwells >= {N_BLIND}: 0")
            continue
        fm = np.array([r["Fmin_kN"] for r in rs])
        f1 = np.array([r["Fmin_after_one_kN"] for r in rs])
        fa = np.array([r["Fmin_after_all_kN"] for r in rs])
        D = np.array([r["D_kN"] for r in rs])
        da = np.array([r["dD_all_kN"] for r in rs])
        lines_with = len({r["line"] for r in rs})
        L.append(f"[{tag}] blind dwells >= {N_BLIND}: {len(rs)} in {lines_with} lines; "
                 f"first LEVEL {sum(1 for r in rs if r['level_index'] == 0)}, later "
                 f"{sum(1 for r in rs if r['level_index'] > 0)}")
        L.append(f"   Fmin at trigger kN: min {fm.min():.2f} p05 {np.percentile(fm, 5):.2f} "
                 f"median {np.median(fm):.2f}")
        L.append(f"   Fmin after one-leg shot kN: min {f1.min():.2f}; after all in-band legs: "
                 f"min {fa.min():.2f}; count < F_min+5 kN: one {int((f1 < 14.41).sum())}, "
                 f"all {int((fa < 14.41).sum())}; < F_min: all {int((fa < 9.415).sum())}")
        L.append(f"   D at trigger kN: p05 {np.percentile(D, 5):.2f} median {np.median(D):.2f} "
                 f"p95 {np.percentile(D, 95):.2f}; |D|<3 {int((np.abs(D) < 3).sum())}, "
                 f"3<=|D|<15 {int(((np.abs(D) >= 3) & (np.abs(D) < 15)).sum())}, "
                 f"|D|>=15 {int((np.abs(D) >= 15).sum())}")
        L.append(f"   |dD| one-leg shot kN: median {np.median(np.abs([r['dD_one_kN'] for r in rs])):.2f}; "
                 f"all in-band: median {np.median(np.abs(da)):.2f} max {np.abs(da).max():.2f}")
        L.append("   legs in band: " + str({k: int(sum(1 for r in rs if r["legs_in_band"] == k))
                                            for k in range(1, 5)}))
        cnt = {}
        for r in rs:
            key = f"{r['leg']}{'+' if r['sign'] > 0 else '-'}"
            cnt[key] = cnt.get(key, 0) + 1
        L.append(f"   leg/sign: {cnt}")
        pat = {}
        for r in rs:
            if r["legs_in_band"] >= 3:
                pat[r["band_signs"]] = pat.get(r["band_signs"], 0) + 1
        L.append(f"   >=3 legs in band, sign patterns (FL FR RL RR; n = + - - +): {pat}; "
                 f"twist pattern {sum(1 for r in rs if r['twist_pattern'])}")
        # D_after vs completion window
        Dafter = D + np.array([r["dD_one_kN"] for r in rs])
        L.append(f"   one-leg shot: |D_after| < 3 kN {int((np.abs(Dafter) < 3).sum())}, "
                 f"D crosses to the other side beyond 2 kN {int(((np.sign(Dafter) != np.sign(D)) & (np.abs(Dafter) > 2)).sum())}, "
                 f"|D_after| > |D| {int((np.abs(Dafter) > np.abs(D)).sum())}")
    if ep_rows:
        tr = np.array([abs(r["travel_mm"]) for r in ep_rows])
        dd = np.array([abs(r["dD_kN"]) for r in ep_rows])
        L.append(f"late ed.6 A(i) episodes (all F >= 40 kN at start): {len(ep_rows)}")
        L.append(f"   |travel| mm to end+1: p10 {np.percentile(tr, 10):.3f} median {np.median(tr):.3f} "
                 f"p90 {np.percentile(tr, 90):.3f} max {tr.max():.3f}")
        L.append(f"   |dD| kN: p10 {np.percentile(dd, 10):.2f} median {np.median(dd):.2f} "
                 f"p90 {np.percentile(dd, 90):.2f} max {dd.max():.2f}")
        per = np.array([r["dD_per_mm_kN"] for r in ep_rows if r["dD_per_mm_kN"] != ""], float)
        legs = [r["leg"] for r in ep_rows if r["dD_per_mm_kN"] != ""]
        for lg in LEGS:
            v = np.array([p for p, g in zip(per, legs) if g == lg])
            if v.size:
                L.append(f"   {lg}: dD/travel kN/mm median {np.median(v):.2f} (n={v.size}); "
                         f"rank-1 one-leg {S_of(np.array([g == lg for g in LEGS]))[LEGS.index(lg)].dot(n) / n[LEGS.index(lg)] * n[LEGS.index(lg)] * 1e-3 / 1e3:.2f}")
    Path(pre + "_summary.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
