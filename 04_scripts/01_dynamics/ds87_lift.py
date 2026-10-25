"""D-S8-7 (dynamics_model.md rev. 41): event-leg lift time after a settlement - quasi-static gap + actuator-rate
prediction vs the ML pilot rerun (L2b-NSC Chrono, 86 settle episodes).

Prediction (independent of Chrono except the pre-event state of the run):
* statics: rigid body on 4 vertical springs at the pad centres (dyn_model.static_loads, legs removed when F < 0), weight at the
  centre of the pre-event cylinder forces (CoP), prestrain delta0 = F0 / k so the pre-event loads are exact.
  Leg stiffness: series(k_h(s), k_out) for legs that gain load, series(k_h + k_r, k_out) for the two legs that
  lose load (settled leg and its diagonal: locked legs below the anchor, rod side active) - variant 'mix';
  variant 'h': series(k_h, k_out) for all. Settled leg ground lowered by d.
  d_c = smallest d at which a leg force reaches 0 (bisection); g_s(d) = separation of the lifted leg at depth d
  (negative compression, m); rho = d g_s / d d beyond d_c.
* kinematics: ground d(t) = depth Poly345((t - t_ev) / ramp); lift starts at t_a with d(t_a) = d_c;
  gap g(t) = rho (d(t) - d_c) - v_c max(0, t - t_a - T_d); lift ends at the first g <= 0 after the ground has
  moved past d_c. T_d = 0.25 s (10 Hz sample + d = 1 + valve lag, ASSUMPTION from rev. 48 0.20 .. 0.27 s),
  v_c = 20.9 mm/s (4 legs x 0.25 v_max in the twist mode, rev. 48 sum |u| 17 .. 21 mm/s).
* control's formula (rev. 48): 0.25 s + gap_chrono / 20.9 mm/s, gap_chrono = max pad gap of the lifted leg.
Chrono (pads.npz 1 ms, 'airborne' = 20 ms mean N <= 0): for the settled leg and its diagonal, the longest
continuous lift in [t_ev, t_ev + 6 s], the cumulative lift, the last touch-down, and the max gap of the settled
leg (ball centre z change minus the ground drop).
Variant 'trig': closure starts T_d after the lifting leg load reaches 1.4 F_min (statics), instead of after t_a.
Writes 06_analysis/00_dynamics/ds87_lift.json (+ .png).
Usage: python -I ds87_lift.py <extract_dir>
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402

P = dm.load_params()
GEO = dm.geometry_from_params(P)
LEGS = list(dm.LEG_NAMES)
DIAG = {0: 3, 3: 0, 1: 2, 2: 1}
A_ANN = np.array([dm.annulus_area(i) for i in range(4)])
STROKE = 0.70
T_D = 0.25
V_C = 4 * 0.25 * 0.0209243016
F_TRIG = 1.4 * 9414.59  # re-approach threshold 1.4 F_min (YAML control.F_min_cylinder_N)
OUT = ROOT / "06_analysis" / "00_dynamics" / "ds87_lift.json"


def poly345(x):
    x = np.clip(x, 0.0, 1.0)
    return 10 * x**3 - 15 * x**4 + 6 * x**5


def statics(k, F0, W, cop, leg, d):
    """Rigid body on 4 unilateral vertical springs; active set removes the most negative leg one at a time
    (dyn_model.static_loads removes all negative legs at once, which can leave 2 legs)."""
    delta = F0 / k
    delta = delta.copy()
    delta[leg] -= d
    A = dm.support_matrix(GEO.pad_xy)
    w = np.array([W, W * cop[1], -W * cop[0]])
    active = np.ones(4, bool)
    for _ in range(4):
        Ka = np.diag(k * active)
        q = np.linalg.solve(A.T @ Ka @ A, A.T @ Ka @ delta - w)
        c = delta - A @ q
        F = k * c * active
        if (F[active] >= -1e-9).all():
            # inactive legs must not penetrate
            if (c[~active] <= 1e-12).all():
                return F, c
        j = int(np.argmin(np.where(active, F, np.inf)))
        active[j] = False
    raise RuntimeError("statics did not converge")


def predict(info, z, variant):
    tp = z["p_t"]
    t_ev = info["t_ev"]
    pre = (tp > t_ev - 0.6) & (tp < t_ev - 0.1)
    F0 = np.median(z["p_F_cyl"][pre], axis=0)
    s = np.median(z["p_s_link"][pre], axis=0)
    W = float(F0.sum())
    cop = (F0[:, None] * GEO.pad_xy).sum(0) / W
    kh = info["beta_Pa"] * np.array(info["head_area_m2"]) / (info["head_dead_m"] + s)
    kr = info["beta_Pa"] * A_ANN / (info["L0r_m"] + STROKE - s)
    kout = 1 / (1 / np.array(info["k_rod_N_m"]) + 1 / info["frame_N_m"] + 1 / info["k_concrete_N_m"])
    leg = LEGS.index(info["leg"])
    k = 1 / (1 / kh + 1 / kout)
    if variant == "mix":
        kb = 1 / (1 / (kh + kr) + 1 / kout)
        k = k.copy()
        k[leg] = kb[leg]
        k[DIAG[leg]] = kb[DIAG[leg]]
    lo, hi = 0.0, 0.06
    F, _ = statics(k, F0, W, cop, leg, hi)
    if F.min() > 0:
        return None
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        F, _ = statics(k, F0, W, cop, leg, mid)
        if F.min() > 1e-6:
            lo = mid
        else:
            hi = mid
    d_c = hi
    F, _ = statics(k, F0, W, cop, leg, d_c + 1e-4)
    lifted = int(np.argmin(F))
    depth = info["depth_m"]
    _, c1 = statics(k, F0, W, cop, leg, d_c + 0.01)
    rho = -c1[lifted] / 0.01
    g_s = max(0.0, rho * (depth - d_c))
    # kinematic lift time
    t = np.arange(0, 8, 1e-3)
    dg = depth * poly345(t / info["ramp_s"])
    if depth <= d_c:
        return dict(d_c_mm=round(d_c * 1e3, 2), lifted=LEGS[lifted], rho=round(rho, 3), g_s_mm=0.0, T_lift_s=0.0)
    ia = int(np.argmax(dg > d_c))
    t_a = t[ia]
    g = rho * (dg - d_c) - V_C * np.maximum(0, t - t_a - T_D)
    after = np.flatnonzero((t > t_a) & (g <= 0))
    t_b = t[after[0]] if len(after) else np.nan
    # variant 'trig': closure starts T_D after the lifting leg's load reaches the re-approach threshold
    # 1.4 F_min (control: reapproach / R-5 fire on the first sample below it, rev. 48 218.5 (1)(2))
    lo2, hi2 = 0.0, d_c
    for _ in range(60):
        mid = 0.5 * (lo2 + hi2)
        F, _ = statics(k, F0, W, cop, leg, mid)
        if F[lifted] > F_TRIG:
            lo2 = mid
        else:
            hi2 = mid
    d_r = hi2
    t_r = t[int(np.argmax(dg >= d_r))]
    g2 = rho * (dg - d_c) - V_C * np.maximum(0, t - t_r - T_D)
    after2 = np.flatnonzero((t > t_a) & (g2 <= 0))
    t_b2 = t[after2[0]] if len(after2) else np.nan
    return dict(d_c_mm=round(d_c * 1e3, 2), lifted=LEGS[lifted], rho=round(rho, 3), g_s_mm=round(g_s * 1e3, 2),
                t_a_s=round(t_a, 3), T_lift_s=round(float(t_b - t_a), 3), g_max_mm=round(float(g.max() * 1e3), 2),
                d_r_mm=round(d_r * 1e3, 2), t_r_s=round(float(t_r), 3), T_lift_trig_s=round(float(t_b2 - t_a), 3),
                t_end_s=round(float(t_b), 3), k_tw=round(float(1 / np.sum(1 / k)), -3))


def chrono(info, z):
    tp = z["p_t"] - info["t_ev"]
    leg = LEGS.index(info["leg"])
    out = {}
    w = (tp >= 0) & (tp <= 6.0)
    for L in (leg, DIAG[leg]):
        a = z["p_airborne"][w, L]
        tt = tp[w]
        if not a.any():
            out[LEGS[L]] = dict(longest_s=0.0, cum_s=0.0, last_touch_s=None, first_lift_s=None)
            continue
        e = np.diff(np.concatenate([[0], a.astype(int), [0]]))
        st, en = np.flatnonzero(e == 1), np.flatnonzero(e == -1) - 1
        dur = tt[en] - tt[st]
        out[LEGS[L]] = dict(longest_s=round(float(dur.max()), 3), cum_s=round(float(a.sum() * 1e-3), 3),
                            last_touch_s=round(float(tt[en[-1]]), 3) if en[-1] < len(tt) - 1 else None,
                            first_lift_s=round(float(tt[st[0]]), 3), n_lifts=int(len(st)))
    # union of the event pair (settled leg or diagonal airborne): span first lift .. last touch, union time
    u = (z["p_airborne"][w, leg] | z["p_airborne"][w, DIAG[leg]])
    if u.any():
        iu = np.flatnonzero(u)
        out["pair_span_s"] = round(float(tp[w][iu[-1]] - tp[w][iu[0]]), 3)
        out["pair_union_s"] = round(float(u.sum() * 1e-3), 3)
        out["pair_last_touch_s"] = round(float(tp[w][iu[-1]]), 3)
    else:
        out["pair_span_s"] = out["pair_union_s"] = 0.0
        out["pair_last_touch_s"] = None
    # gap of the settled leg
    zb = z["p_ball_centre_world"][:, leg, 2]
    zg = -info["depth_m"] * poly345(tp / info["ramp_s"])
    i0 = np.searchsorted(tp, 0.0)
    gap = (zb - zb[i0]) - (zg - zg[i0])
    out["gap_settled_max_mm"] = round(float(gap[w].max() * 1e3), 2)
    # sum |u| issued (10 Hz) over the 1.5 s after the event
    qt = z["q_t"] - info["t_ev"]
    ww = (qt > 0.2) & (qt <= 1.5)
    out["sum_abs_u_mm_s"] = round(float(np.abs(z["q_issued_u"][ww]).sum(1).mean() * 1e3), 2) if ww.any() else None
    return out


src = Path(sys.argv[1])
index = json.loads((src / "index.json").read_text(encoding="utf-8"))
ctrl = {r["run"]: r for r in json.loads((ROOT / "06_analysis/02_control/s8/s8_ml_rev48_lift.json").read_text(encoding="utf-8"))}
rows = []
for info in index:
    z = np.load(src / f"{info['run']}.npz", allow_pickle=True)
    c = chrono(info, z)
    pm = predict(info, z, "mix")
    ph = predict(info, z, "h")
    cr = ctrl.get(info["run"], {})
    leg = info["leg"]
    dleg = LEGS[DIAG[LEGS.index(leg)]]
    longest = max(c[leg]["longest_s"], c[dleg]["longest_s"])
    lifted_c = leg if c[leg]["longest_s"] >= c[dleg]["longest_s"] else dleg
    ctrl_pred = 0.25 + cr["gap_max_mm"] / (V_C * 1e3) if cr.get("gap_max_mm") is not None and cr.get("lift_s", 0) > 0 else None
    row = dict(run=info["run"], leg=leg, depth_mm=round(info["depth_m"] * 1e3, 1), ramp_s=info["ramp_s"],
               v_mm_s=round(info["depth_m"] / info["ramp_s"] * 1e3, 1), fs_kN=info["fs_kN"], level=info["level"],
               chrono=c, chrono_longest_s=longest, chrono_lifted=lifted_c if longest > 0 else None,
               pred_mix=pm, pred_h=ph, ctrl_formula_s=round(ctrl_pred, 3) if ctrl_pred is not None else None,
               ctrl_gap_mm=cr.get("gap_max_mm"), ctrl_lift_s=cr.get("lift_s"), ctrl_lift_leg=cr.get("lift_leg"))
    rows.append(row)
    print(f"{info['run']:9s} {leg} {row['depth_mm']:5.1f} mm {row['v_mm_s']:6.1f} mm/s | chrono {lifted_c if longest else '-':2s}"
          f" longest {longest:.3f} cum {c[leg]['cum_s']:.2f}/{c[dleg]['cum_s']:.2f} gapS {c['gap_settled_max_mm']:5.1f}"
          f" sum|u| {c['sum_abs_u_mm_s']} | pred mix d_c {pm['d_c_mm'] if pm else '-'} {pm['lifted'] if pm else ''}"
          f" g_s {pm['g_s_mm'] if pm else '-'} T {pm['T_lift_s'] if pm else '-'} | h d_c {ph['d_c_mm'] if ph else '-'} T {ph['T_lift_s'] if ph else '-'}"
          f" | ctrl formula {row['ctrl_formula_s']}")

# category statistics
def cat(r):
    if r["v_mm_s"] < 50:
        return "slow(<50mm/s)"
    return ("rear" if r["leg"] in ("RL", "RR") else "front") + "_fast"


summary = {}
for cname in ("rear_fast", "front_fast", "slow(<50mm/s)"):
    sel = [r for r in rows if cat(r) == cname]
    lifted = [r for r in sel if r["chrono_longest_s"] > 0.05]
    pos_pred = [r for r in sel if r["pred_mix"] and (r["pred_mix"].get("T_lift_trig_s") or 0) > 0.05]
    fp = [r["run"] for r in pos_pred if r["chrono_longest_s"] <= 0.05]
    fn = [r["run"] for r in lifted if not (r["pred_mix"] and (r["pred_mix"].get("T_lift_trig_s") or 0) > 0.05)]
    both = [r for r in lifted if r["pred_mix"] and (r["pred_mix"].get("T_lift_trig_s") or 0) > 0.05]
    e = {}
    for key, pick in (("mix_vs_longest", lambda r: r["pred_mix"]["T_lift_s"] - r["chrono_longest_s"]),
                      ("trig_vs_longest", lambda r: r["pred_mix"]["T_lift_trig_s"] - r["chrono_longest_s"]),
                      ("h_trig_vs_longest", lambda r: (r["pred_h"]["T_lift_trig_s"] if r["pred_h"] and "T_lift_trig_s" in r["pred_h"] else 0.0) - r["chrono_longest_s"]),
                      ("trig_vs_pair_span", lambda r: r["pred_mix"]["T_lift_trig_s"] - r["chrono"]["pair_span_s"]),
                      ("ctrl_formula_vs_longest", lambda r: (r["ctrl_formula_s"] - r["ctrl_lift_s"]) if r["ctrl_formula_s"] is not None else np.nan)):
        v = np.array([pick(r) for r in both], float)
        v = v[np.isfinite(v)]
        if len(v):
            e[key] = dict(n=int(len(v)), mean=round(float(v.mean()), 3), min=round(float(v.min()), 3),
                          max=round(float(v.max()), 3))
    summary[cname] = dict(n=len(sel), chrono_lift=len(lifted), predicted_lift=len(pos_pred), false_pos=fp,
                          false_neg=fn, errors_s=e,
                          chrono_longest_max_s=round(max([r["chrono_longest_s"] for r in sel] + [0.0]), 3))
    print(cname, json.dumps(summary[cname]))
OUT.write_text(json.dumps(dict(summary=summary, rows=rows), indent=1, default=float), encoding="utf-8")

# summary
fig, ax = plt.subplots(1, 2, figsize=(13, 5))
xs, ys, cs = [], [], []
for r in rows:
    pm = r["pred_mix"]
    if pm is None:
        continue
    xs.append(pm["T_lift_s"]); ys.append(r["chrono_longest_s"]); cs.append(r["v_mm_s"])
xs, ys, cs = map(np.array, (xs, ys, cs))
sc = ax[0].scatter(xs, ys, c=np.log10(cs), cmap="viridis")
ax[0].plot([0, 2], [0, 2], "k--", lw=0.8)
ax[0].set_xlabel("predicted lift [s] (quasi-static gap 'mix' + T_d 0.25 s + v_c 20.9 mm/s)")
ax[0].set_ylabel("Chrono longest lift, settled leg or diagonal [s]")
plt.colorbar(sc, ax=ax[0], label="log10 settle speed [mm/s]")
x2 = np.array([r["ctrl_formula_s"] for r in rows if r["ctrl_formula_s"] is not None])
y2 = np.array([r["ctrl_lift_s"] for r in rows if r["ctrl_formula_s"] is not None])
ax[1].scatter(x2, y2)
ax[1].plot([0, 2], [0, 2], "k--", lw=0.8)
ax[1].set_xlabel("control formula 0.25 s + gap_chrono / 20.9 mm/s [s]")
ax[1].set_ylabel("Chrono longest lift (rev. 48 table) [s]")
for a in ax:
    a.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(OUT.with_suffix(".png"), dpi=90)
print("wrote", OUT)
