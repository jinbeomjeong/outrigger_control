"""Ed. 7 dynamics review Q7-D1, step 1 (dynamics-expert, 2026-11-24; analysis only, read only).

Reads the counterfactual C T4h of the ed. 6 records run (``records_after_stop/C_a2``, 60 lines,
already seen and disclosed as O7-2 in spec v7) and answers, per post-event LEVEL:

  (a) blind dwells: stretches of >= 20 periods in which a leg is locked and its command stays
      0 < |u| <= u_hold with one sign (the A(i)-b trigger of spec v7 3.1 without condition 3).
      For each: which leg, sign, how many legs dwell together, the twist load D = n . F_true,
      the smallest true leg force, and the command split into the rigid part (heave, roll and
      pitch rates: span{1, x, y}) and the twist part (n tau_dot).
  (b) ed. 6 A(i) episodes (lsb_a1_on): stroke travel of the raised leg from the episode start
      to 3 periods after its end, the measured change of D and of every leg force over the same
      span, and the rank-1 prediction dF = S de with S = k_tw n n^T (k_tw for "leg i moving,
      others locked", harness strokes).

Conventions: body axes x fwd, y left; legs FL, FR, RL, RR; force compression +; stroke = motor
(oil) coordinate ``motor_stroke_m``; command m/s extension +. Pad x, y from 02_params via the
ed. 6 dynamics json (pad_xy_m printed as (y, x)). Units SI, printed mm, kN, s.
Output: CSV + TXT next to --out-prefix. stdout ASCII.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

T4H = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405"
           r"\records_after_stop\C_a2\counterfactual_t4h")
B3_JSON = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design"
               r"\dynamics_v6\b3_twist_stiffness.json")
LEGS = ("FL", "FR", "RL", "RR")
U_HOLD = 2.09243016e-4
N_BLIND = 20
F_MIN = 9414.58911


def segments(phase):
    out, start = [], 0
    for i in range(1, len(phase) + 1):
        if i == len(phase) or phase[i] != phase[start]:
            out.append((str(phase[start]), start, i - 1))
            start = i
    return out


def runs(flag):
    """(start, end) inclusive index pairs of True runs."""
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
    yx = np.array(b3["pad_xy_m"])
    x, y = yx[:, 1], yx[:, 0]
    basis = np.column_stack([np.ones(4), x, y, n])        # heave, d/dx slope, d/dy slope, twist
    k_move = np.array(b3["variants"]["move_harness_R12"]["k_leg_MN_m"]) * 1e6
    k_lock = np.array(b3["variants"]["lock_harness_R12"]["k_leg_MN_m"]) * 1e6
    k_tw_one = {}
    for i in range(4):
        k = k_lock.copy()
        k[i] = k_move[i]
        k_tw_one[i] = 1.0 / float(np.sum(n**2 / k))

    dwell_rows, ep_rows = [], []
    for path in sorted(T4H.glob("*.npz")):
        with np.load(path, allow_pickle=False) as d:
            t, ph, u = d["t_s"], d["phase"], d["command_m_s"]
            lk, F, s = d["locked"], d["true_force_N"], d["motor_stroke_m"]
            a1 = d["lsb_a1_on"] if "lsb_a1_on" in d.files else np.zeros_like(lk)
        levels = [g for g in segments(ph) if g[0] == "level"]
        if len(levels) < 2:
            continue
        _, i0, i1 = levels[-1]
        name = path.stem
        band = lk & (np.abs(u) > 1e-12) & (np.abs(u) <= U_HOLD)
        # (a) blind dwells of one sign, >= N_BLIND periods, inside the post-event LEVEL
        for leg in range(4):
            sgn = np.sign(u[:, leg])
            flag = band[:, leg].copy()
            flag[:i0] = False
            flag[i1 + 1:] = False
            for a, b in runs(flag):
                # split on sign changes
                cut = [a] + [k for k in range(a + 1, b + 1) if sgn[k] != sgn[k - 1]] + [b + 1]
                for p, q in zip(cut[:-1], cut[1:]):
                    if q - p < N_BLIND:
                        continue
                    k_trig = p + N_BLIND - 1
                    coef = np.linalg.solve(basis, u[k_trig])
                    rigid = basis[:, :3] @ coef[:3]
                    twist = basis[:, 3] * coef[3]
                    together = int(sum(band[k_trig, j] for j in range(4)))
                    D = float(n @ F[k_trig])
                    dwell_rows.append({
                        "line": name, "leg": LEGS[leg], "sign": int(sgn[p]),
                        "t_start_s": round(float(t[p]), 2), "dwell_s": round((q - p) * 0.1, 1),
                        "t_trigger_s": round(float(t[k_trig]), 2),
                        "legs_in_band_at_trigger": together,
                        "u_leg_mm_s": round(float(u[k_trig, leg]) * 1e3, 4),
                        "u_rigid_leg_mm_s": round(float(rigid[leg]) * 1e3, 4),
                        "u_twist_leg_mm_s": round(float(twist[leg]) * 1e3, 4),
                        "D_kN": round(D / 1e3, 2),
                        "Fmin_true_kN": round(float(F[k_trig].min()) / 1e3, 2),
                        "Fmin_leg": LEGS[int(np.argmin(F[k_trig]))],
                        "F_leg_kN": round(float(F[k_trig, leg]) / 1e3, 2),
                        "pred_dD_per_0p6mm_kN": round(k_tw_one[leg] * n[leg] * 0.6e-3
                                                      * np.sign(u[k_trig, leg]) / 1e3, 2),
                        "pred_dF_min_leg_per_0p6mm_kN": round(
                            k_tw_one[leg] * n[int(np.argmin(F[k_trig]))] * n[leg] * 0.6e-3
                            * np.sign(u[k_trig, leg]) / 1e3, 2),
                    })
        # (b) ed. 6 A(i) episodes
        for leg in range(4):
            flag = a1[:, leg].astype(bool)
            for a, b in runs(flag):
                e = min(b + 3, len(t) - 1)
                a0 = max(a - 1, 0)
                ds = float(s[e, leg] - s[a0, leg])
                dF = F[e] - F[a0]
                pred = k_tw_one[leg] * n * n[leg] * ds
                ep_rows.append({
                    "line": name, "leg": LEGS[leg], "t_on_s": round(float(t[a]), 2),
                    "periods_on": b - a + 1, "phase_at_on": str(ph[a]),
                    "sign": int(np.sign(u[a, leg])),
                    "stroke_travel_mm": round(ds * 1e3, 3),
                    "dD_meas_kN": round(float(n @ dF) / 1e3, 2),
                    "dD_pred_kN": round(float(n @ pred) / 1e3, 2),
                    "dF_meas_kN": "|".join(f"{v / 1e3:.2f}" for v in dF),
                    "dF_pred_kN": "|".join(f"{v / 1e3:.2f}" for v in pred),
                    "Fmin_before_kN": round(float(F[a0].min()) / 1e3, 2),
                    "Fmin_after_kN": round(float(F[a0:e + 1].min()) / 1e3, 2),
                })
    pre = Path(args.out_prefix)
    for rows, suffix in ((dwell_rows, "_dwells.csv"), (ep_rows, "_a1_episodes.csv")):
        if rows:
            with open(str(pre) + suffix, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    # summary
    lines = []
    lines.append(f"k_tw (leg i moving, others locked) MN/m: "
                 + ", ".join(f"{LEGS[i]} {k_tw_one[i] / 1e6:.2f}" for i in range(4)))
    lines.append(f"blind dwells >= {N_BLIND} periods (post-event LEVEL): {len(dwell_rows)}")
    if dwell_rows:
        tw = np.array([abs(r["u_twist_leg_mm_s"]) for r in dwell_rows])
        rg = np.array([abs(r["u_rigid_leg_mm_s"]) for r in dwell_rows])
        lines.append(f"  |twist part| / (|twist|+|rigid|) median {np.median(tw / (tw + rg)):.2f}, "
                     f"min {np.min(tw / (tw + rg)):.2f}, max {np.max(tw / (tw + rg)):.2f}")
        lines.append("  legs in band at the trigger read: " + str(
            {k: int(sum(1 for r in dwell_rows if r['legs_in_band_at_trigger'] == k))
             for k in range(1, 5)}))
        Ds = np.array([r["D_kN"] for r in dwell_rows])
        lines.append(f"  D at trigger kN: min {Ds.min():.2f} median {np.median(Ds):.2f} "
                     f"max {Ds.max():.2f}; |D| < 3 kN: {int((np.abs(Ds) < 3).sum())}")
        fm = np.array([r["Fmin_true_kN"] for r in dwell_rows])
        lines.append(f"  smallest true leg force at trigger kN: min {fm.min():.2f} "
                     f"median {np.median(fm):.2f}")
        lines.append("  leg/sign counts: " + str(
            {f"{r['leg']}{'+' if r['sign'] > 0 else '-'}": 0 for r in dwell_rows}))
        cnt = {}
        for r in dwell_rows:
            k = f"{r['leg']}{'+' if r['sign'] > 0 else '-'}"
            cnt[k] = cnt.get(k, 0) + 1
        lines[-1] = "  leg/sign counts: " + str(cnt)
    lines.append(f"ed.6 A(i) episodes: {len(ep_rows)}")
    if ep_rows:
        tr = np.array([abs(r["stroke_travel_mm"]) for r in ep_rows])
        dm = np.array([r["dD_meas_kN"] for r in ep_rows])
        dp = np.array([r["dD_pred_kN"] for r in ep_rows])
        lines.append(f"  |travel| mm (start-1 .. end+3): min {tr.min():.3f} median "
                     f"{np.median(tr):.3f} max {tr.max():.3f}")
        ok = np.abs(dp) > 0.5
        if ok.any():
            lines.append(f"  dD meas/pred (|pred| > 0.5 kN, n={int(ok.sum())}): median "
                         f"{np.median(dm[ok] / dp[ok]):.2f}, p10 {np.percentile(dm[ok] / dp[ok], 10):.2f}"
                         f", p90 {np.percentile(dm[ok] / dp[ok], 90):.2f}")
        lines.append("  phase at on: " + str({p: sum(1 for r in ep_rows if r['phase_at_on'] == p)
                                               for p in sorted({r['phase_at_on'] for r in ep_rows})}))
    Path(str(pre) + "_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
