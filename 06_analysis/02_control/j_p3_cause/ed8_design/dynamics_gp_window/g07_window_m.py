"""G' window shift, part 7: per-cluster window model -> P(E | condition, phase) on the 8 G' phases and the
window-shift factor m for the stats size model (f3_sizes / s8r_sizes: E prob x m).

1. Edge fit on the 21 stored reruns (V0, VBM, U8-A; bottom front RE1bF ready, 30 mm / 0.05 s):
   controller-effective edges t_r*, t_h* (g00.window_features with the g03 offsets) =
   intercept(arm, leg) + a * F_s + beta * (start - 0.1), start = first 10 Hz sample after the event pad
   lifted (t_lift 0.015 s): phi 0 -> 0.1, phi > 0.015 -> 0.1 - phi, phi 0.0875 -> 0.1125.
2. Cluster windows for V0 (families = timing {ready, level} x leg {FL, FR}; clusters F_s {0, 2, 4, 8}):
   ready = V0 fit; level = ready + delta_L (per cluster, N(0, SIG_L)); per-cluster residual N(0, SIG_R).
   SIG_L, SIG_R are chosen so the model reproduces the stored V0 grid E flags (g01, 4 old phases).
3. Exit rule (dynamics_u832_o00 4.2, stats 6.3): first sample s1 = min{0.1 k - phi >= t_r*};
   E <=> s1 + 0.2 <= t_h* and round(s1 + 0.2, 3) <= 0.450.
4. Conditions: base; depth shapes shift both edges by the reduced-model differences (g06 ensemble,
   drawn uniformly from the per-run ensemble values); F_s in {1, 3, 6} kN via the fitted F_s slopes
   (interpolation inside the stored 0..8 kN range).
   m(condition) = mean P(E) over the 8 phases and the E-candidate clusters / same for base (stats slot weights:
   depth slots keep the cluster F_s; F_s slots replace it).
   Sensitivity "25L<x>": 25/0.05 with the rising edge from the data argument (g05) and the window lengthened by
   x ms instead of the reduced-model value (x = 0: pure translation of the window).
Monte Carlo over the cluster draws and the slope / shift uncertainty (seed 20261126, own seed, not a G' seed).
Usage: python -I -B g07_window_m.py <rerun_dir> <out_folder>
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g00_rock_model as rm  # noqa: E402

rerun, out = Path(sys.argv[1]), Path(sys.argv[2])
PH_OLD = [0.0, 0.025, 0.05, 0.075]
PH_NEW = [0.0125, 0.0375, 0.0625, 0.0875]
PH_ALL = sorted(PH_OLD + PH_NEW)
FS_BASE = [0.0, 2.0, 4.0, 8.0]
FS_NEW = [1.0, 3.0, 6.0]
T_LIFT = 0.015
rng = np.random.default_rng(20261126)


def start_of(phi):
    """First 10 Hz sample after the event pad lifted (event start = sample when phi = 0)."""
    k = 0
    while True:
        s = round(0.1 * k - phi, 6)
        if s > T_LIFT:
            return s
        k += 1


def is_E(tr, th, phi):
    k = 0
    while True:
        s = round(0.1 * k - phi, 6)
        if s >= tr - 1e-9:
            break
        k += 1
    ex = s + 0.2
    return (ex <= th + 1e-9) and (round(ex, 3) <= 0.450)


# ---- 1. edge fit ----------------------------------------------------------------------------------------
recs = []
for p in sorted((rerun / "logs").glob("R12_bottom-F*-RE1bF-ready_*_rows.npz")):
    stem = p.name[:-len("_rows.npz")]
    arm = stem.split("_")[-1]
    parts = stem.split("_")[1].split("-")
    leg_name, fs, off = parts[1], float(parts[2][2:]), float(parts[3][1:])
    leg = 0 if leg_name == "FL" else 1
    _, t, rows = rm.load_valve(rerun, stem)
    w = (t >= -0.01) & (t <= 1.0)
    f = rm.window_features(t[w], rows[w, 1:5], rows[w, 13:17], leg, fs)
    phi = round(off % 0.1, 4)
    recs.append({"stem": stem, "arm": arm, "leg": leg_name, "fs": fs, "phi": phi, "start": start_of(phi),
                 "t_r": f["t_r_star"], "t_h": f["t_h_star"], "t_c": f["t_contact"], "t_rl": f["t_relift"]})
groups = sorted({(r["arm"], r["leg"]) for r in recs})


def fit(key):
    A, b = [], []
    for r in recs:
        row = [1.0 if (r["arm"], r["leg"]) == g else 0.0 for g in groups] + [r["fs"], r["start"] - 0.1]
        A.append(row)
        b.append(r[key])
    A, b = np.array(A), np.array(b)
    x, *_ = np.linalg.lstsq(A, b, rcond=None)
    res = b - A @ x
    dof = len(b) - len(x)
    s2 = float(res @ res / dof)
    cov = s2 * np.linalg.inv(A.T @ A)
    return {"coef": dict(zip([f"{a}|{lg}" for a, lg in groups] + ["a_Fs", "beta"], x.tolist())),
            "se": dict(zip([f"{a}|{lg}" for a, lg in groups] + ["a_Fs", "beta"], np.sqrt(np.diag(cov)).tolist())),
            "resid_sd": float(np.sqrt(s2)), "max_abs_resid": float(np.abs(res).max())}


FIT = {"t_r": fit("t_r"), "t_h": fit("t_h")}

# ---- 2/3. cluster windows, calibration of SIG_L / SIG_R against the stored grid E flags ---------------------
gridE = {}
for r in csv.DictReader((out / "g01_grid_E_rows.csv").open(encoding="utf-8")):
    if r["dup"] == "True" or r["level"] != "bottom" or r["event"] != "RE1bF":
        continue
    gridE[(r["timing"], r["leg"], float(r["fs_kN"]), float(r["phi_s"]))] = r["E"] == "True"


def edges(timing, leg, fs, phi, dL, dR, shift_r=0.0, shift_h=0.0, slope=None):
    a_r = FIT["t_r"]["coef"]["a_Fs"] if slope is None else slope[0]
    a_h = FIT["t_h"]["coef"]["a_Fs"] if slope is None else slope[1]
    st = start_of(phi) - 0.1
    tr = FIT["t_r"]["coef"][f"V0|{leg}"] + a_r * fs + FIT["t_r"]["coef"]["beta"] * st + shift_r
    th = FIT["t_h"]["coef"][f"V0|{leg}"] + a_h * fs + FIT["t_h"]["coef"]["beta"] * st + shift_h
    if timing == "level":
        tr += dL[0]
        th += dL[1]
    return tr + dR[0], th + dR[1]


CLUSTERS = [(tm, lg, fs) for tm in ("ready", "level") for lg in ("FL", "FR") for fs in FS_BASE]


def agreement(sig_l, sig_r, n=400):
    """Expected fraction of stored grid flags reproduced (MC over the per-cluster deltas)."""
    hits = 0.0
    tot = 0
    for (tm, lg, fs) in CLUSTERS:
        for _ in range(n):
            dL = rng.normal(0, sig_l, 2) if sig_l > 0 else np.zeros(2)
            dR = rng.normal(0, sig_r, 2) if sig_r > 0 else np.zeros(2)
            for phi in PH_OLD:
                key = (tm, lg, fs, phi)
                if key not in gridE:
                    continue
                tr, th = edges(tm, lg, fs, phi, dL, dR)
                hits += (is_E(tr, th, phi) == gridE[key]) / n
        tot += sum(1 for phi in PH_OLD if (tm, lg, fs, phi) in gridE)
    return hits / tot


cal = []
for sl in (0.0, 0.001, 0.002, 0.003, 0.004):
    for sr in (0.0, 0.001, 0.002):
        cal.append({"sig_L": sl, "sig_R": sr, "agreement": round(agreement(sl, sr, 200), 4)})
cal.sort(key=lambda r: -r["agreement"])
SIG_L, SIG_R = cal[0]["sig_L"], cal[0]["sig_R"]
det = []
for (tm, lg, fs) in CLUSTERS:
    for phi in PH_OLD:
        if (tm, lg, fs, phi) in gridE:
            tr, th = edges(tm, lg, fs, phi, np.zeros(2), np.zeros(2))
            det.append({"cluster": f"{tm}-{lg}-Fs{fs:g}", "phi": phi, "stored_E": gridE[(tm, lg, fs, phi)],
                        "model_tr": round(float(tr), 4), "model_th": round(float(th), 4),
                        "model_E_nominal": bool(is_E(tr, th, phi))})

# ---- 4. conditions -----------------------------------------------------------------------------------------
g06 = list(csv.DictReader((out / "g06_variants.csv").open(encoding="utf-8")))
SH = {}
for sh in ("25/0.05", "30/0.04"):
    v = [(float(r["d_t_r_star"]), float(r["d_t_h_star"])) for r in g06 if r["shape"] == sh and r["case"].startswith("ens")]
    vo = [(float(r["d_t_r_star"]), float(r["d_t_h_star"])) for r in g06 if r["shape"] == sh and r["case"] == "valve_off"]
    SH[sh] = np.array(v + vo)          # valve-off pairs added as the upper bound of the controller-history term
N_MC = 4000
se_r = FIT["t_r"]["se"]["a_Fs"]
se_h = FIT["t_h"]["se"]["a_Fs"]


def mc(condition):
    """Return P(E) per phase (8) for the base clusters (depth: per cluster F_s) or the F_s families."""
    pe = np.zeros(len(PH_ALL))
    cnt = 0
    for _ in range(N_MC):
        slope = (FIT["t_r"]["coef"]["a_Fs"] + rng.normal(0, se_r), FIT["t_h"]["coef"]["a_Fs"] + rng.normal(0, se_h))
        if condition in SH:
            dr, dh = SH[condition][rng.integers(len(SH[condition]))]
        elif condition.startswith("25L"):
            # sensitivity: rising edge from the data argument (g05, V0 -38.5..-45.2 ms), window lengthened by L ms
            dr = rng.uniform(-0.0452, -0.0385)
            dh = dr + float(condition[3:]) / 1e3
        else:
            dr, dh = 0.0, 0.0
        fam = (("ready", "FL"), ("ready", "FR"), ("level", "FL"), ("level", "FR"))[rng.integers(4)]
        if condition.startswith("Fs"):
            fs = float(condition[2:])
        else:
            fs = FS_BASE[rng.integers(4)]
        dL = rng.normal(0, SIG_L, 2) if SIG_L > 0 else np.zeros(2)
        dR = rng.normal(0, SIG_R, 2) if SIG_R > 0 else np.zeros(2)
        for j, phi in enumerate(PH_ALL):
            tr, th = edges(fam[0], fam[1], fs, phi, dL, dR, dr, dh, slope)
            pe[j] += is_E(tr, th, phi)
        cnt += 1
    return pe / cnt


conds = ["base", "25/0.05", "30/0.04", "Fs1", "Fs3", "Fs6", "Fs0", "Fs2", "Fs4", "Fs8",
         "25L-10", "25L0", "25L10", "25L20", "25L30"]
P = {c: mc(c) for c in conds}
STATS_P = np.array([15 / 16, 0.5, 0.0, 0.0, 4 / 16, 1.0, 1.0, 1.0])   # stats P_RE on PH_ALL order
base_mean = P["base"].mean()
summary = {c: {"P_by_phase": dict(zip([str(p) for p in PH_ALL], np.round(P[c], 3).tolist())),
               "mean": round(float(P[c].mean()), 4), "m_vs_model_base": round(float(P[c].mean() / base_mean), 3)}
           for c in conds}
summary["stats_P_RE"] = {"P_by_phase": dict(zip([str(p) for p in PH_ALL], STATS_P.round(3).tolist())),
                         "mean": round(float(STATS_P.mean()), 4)}
res = {"fit": FIT, "sig_calibration": cal, "SIG_L": SIG_L, "SIG_R": SIG_R, "nominal_vs_grid": det,
       "shape_shift_pairs_ms": {k: (1e3 * v).round(1).tolist() for k, v in SH.items()}, "conditions": summary,
       "records": recs, "seed": 20261126, "N_MC": N_MC}
(out / "g07_window_m.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
lines = [f"edge fit t_r*: {json.dumps({k: round(v, 5) for k, v in FIT['t_r']['coef'].items()})} se a_Fs {se_r:.5f} "
         f"resid sd {FIT['t_r']['resid_sd']:.4f} max {FIT['t_r']['max_abs_resid']:.4f}",
         f"edge fit t_h*: {json.dumps({k: round(v, 5) for k, v in FIT['t_h']['coef'].items()})} se a_Fs {se_h:.5f} "
         f"resid sd {FIT['t_h']['resid_sd']:.4f} max {FIT['t_h']['max_abs_resid']:.4f}",
         f"SIG_L {SIG_L} SIG_R {SIG_R}; calibration top: {cal[:3]}",
         "nominal model vs stored grid (old phases):"]
lines += [f"  {d['cluster']:16s} phi {d['phi']:<6} stored {'E' if d['stored_E'] else 'N'} model "
          f"{'E' if d['model_E_nominal'] else 'N'} (t_r* {d['model_tr']}, t_h* {d['model_th']})" for d in det]
lines.append("")
lines.append("P(E) by phase " + " ".join(f"{p:>7}" for p in PH_ALL) + "   mean   m(model)")
for c in conds:
    lines.append(f"{c:12s}  " + " ".join(f"{v:7.3f}" for v in P[c]) + f"  {P[c].mean():.3f}  {P[c].mean() / base_mean:.3f}")
lines.append(f"{'stats P_RE':12s}  " + " ".join(f"{v:7.3f}" for v in STATS_P) + f"  {STATS_P.mean():.3f}")
(out / "g07_window_m.txt").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
print(json.dumps({"status": "ok"}))
