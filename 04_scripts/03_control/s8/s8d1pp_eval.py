"""Rev. 49 (D1'' details R41-1..3): compare M_eff calibrations and the gyro lever-arm correction on the
D1'' head-step rule, from the per-run series written by s8d1pp_extract.py.

Variants of the residual r_k = sum F_read(t_k) - M (f_z(t_k) - lever_k):
  M:     'ready'  = median sum/f_z of the current READY stay (>= 3 samples, last 600), causal, as implemented
         'true'   = YAML upper-body mass 38,400.8 kg (reference, not available to the controller)
         'mid'    = 'ready' - sum(F_s,i) / (2 g) with the run's true seal limits (idealised mid-band correction)
  lever: 'none', 'gyro' (truth alpha + gyro noise of the normal grade, s8d1pp_extract), 'exact' (truth alpha)
Also the per-run slope estimate d(sum)/d(f_z) on lifted, moving, quiet periods (no head step > 100 bar).

Outputs (stdout + JSON):
  * slope / READY / mid mass errors per batch (percent of 38,400.8 kg)
  * transient periods (lifted, max |dp_h| > 30 bar, both periods lifted, no FAULT phase): |d r| p50/p99/max
    per variant, per batch and per F_s class (run mean seal limit 0 / <= 2.5 / <= 5 / > 5 kN)
  * real head steps > 100 bar: max |d r| / (|dp_h| A_p) per variant, count >= 0.5
  * injected persistent head jump J (+-100, +-150 bar) on every lifted period (episodes: after the event):
    detection rate (|d r + J A_p| >= 0.5 |dp + J| A_p) per variant, quiet / transient
Usage: python -I s8d1pp_eval.py <series_dir> <out_json>
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
src, out_json = Path(sys.argv[1]), Path(sys.argv[2])
A_P = np.array([1.3273229e-2, 1.3273229e-2, 9.50331778e-3, 9.50331778e-3])
G = 9.80665
M_TRUE = 38400.8
LIFTED = {"level", "done", "reanchor", "probe", "ready"}
JUMPS = (100.0, -100.0, 150.0, -150.0)
VARIANTS = [(m, lv) for m in ("ready", "true", "mid") for lv in ("none", "gyro", "exact")] + [("zero", "none")]
# ('zero', 'none') = M 0: the D1' four-leg sum rule on the same periods (reference)
THRESHOLDS = (0.4, 0.5, 0.6)


def ready_mass(phase, ratio):
    """Causal M_eff of the implementation: median of the current READY stay from 3 samples on."""
    m = np.full(phase.size, np.nan)
    cur, stay = np.nan, []
    for k in range(phase.size):
        if phase[k] == "ready":
            if k == 0 or phase[k - 1] != "ready":
                stay = []
            if np.isfinite(ratio[k]) and ratio[k] > 0:
                stay.append(ratio[k])
                stay = stay[-600:]
            if len(stay) >= 3:
                cur = float(np.median(stay))
        m[k] = cur
    return m


def fs_class(fs_kN):
    return "Fs0" if fs_kN < 0.05 else ("Fs<=2.5" if fs_kN <= 2.5 else ("Fs<=5" if fs_kN <= 5.0 else "Fs>5"))


dr = defaultdict(list)          # (variant, batch, class) -> |d r| on transient periods [kN]
steps = defaultdict(list)       # variant -> ratios of real steps
step_rows = []
inj = defaultdict(lambda: [0, 0])  # (variant, J, quiet/transient) -> [n, detected]
mass_err = defaultdict(list)
bias_contrib = []
for f in sorted(src.glob("*.npz")):
    batch, run = f.stem.split("__", 1)
    z = np.load(f)
    t, s, fz = z["t"], z["sum_N"], z["f_z"]
    head = z["head_Pa"] / 1e5
    phase = z["phase"].astype(str)
    lim = z["seal_limits_N"]
    t_ev = float(z["t_ev"])
    fsk = float(lim.mean() / 1e3)
    cls = fs_class(fsk)
    lifted = np.isin(phase, list(LIFTED))
    with np.errstate(divide="ignore", invalid="ignore"):
        m_ready = ready_mass(phase, s / fz)
    masses = {"ready": m_ready, "true": np.full(t.size, M_TRUE), "mid": m_ready - lim.sum() / (2 * G),
              "zero": np.where(np.isfinite(m_ready), 0.0, np.nan)}
    levers = {"none": np.zeros(t.size), "gyro": z["lever_noisy"], "exact": z["lever_true"]}
    # mass errors (last READY value before the event or at the end)
    k_ref = np.flatnonzero(np.isfinite(m_ready) & ((t < t_ev) if np.isfinite(t_ev) else True))
    if k_ref.size:
        mass_err[(batch, "ready")].append(m_ready[k_ref[-1]] / M_TRUE - 1)
        mass_err[(batch, "mid")].append(masses["mid"][k_ref[-1]] / M_TRUE - 1)
    dh = np.diff(head, axis=0)
    dsum = np.diff(s)
    dfz = np.diff(fz)
    quiet100 = np.abs(dh).max(axis=1) < 100.0
    moving = np.any(z["commanded"][1:] != 0.0, axis=1)
    sel = lifted[1:] & lifted[:-1] & moving & quiet100 & (phase[1:] != "fault")
    if sel.sum() >= 5 and np.sum(dfz[sel] ** 2) > 0:
        slope = float(np.sum(dsum[sel] * dfz[sel]) / np.sum(dfz[sel] ** 2))
        mass_err[(batch, "slope")].append(slope / M_TRUE - 1)
        mass_err[(batch, "slope_rms_dfz")].append(float(np.sqrt(np.mean(dfz[sel] ** 2))))
    both = lifted[1:] & lifted[:-1] & (phase[1:] != "fault") & (phase[:-1] != "fault")
    post = both & ((t[1:] >= t_ev) if np.isfinite(t_ev) else True)
    trans = np.abs(dh).max(axis=1) > 30.0
    has_lever = np.isfinite(z["lever_true"][1:]) & np.isfinite(z["lever_true"][:-1])
    dmass = (m_ready - M_TRUE)[1:]
    ok_b = both & np.isfinite(dmass)
    if ok_b.any():
        bias_contrib.append(float(np.nanmax(np.abs(dmass[ok_b] * dfz[ok_b])) / 1e3))
    for (mk, lk) in VARIANTS:
        if lk != "none" and not has_lever.any():
            continue
        r = s - masses[mk] * (fz - levers[lk])
        d = np.diff(r)
        valid = both & np.isfinite(d) & (has_lever if lk != "none" else True)
        v = valid & trans
        key = f"{mk}/{lk}"
        dr[(key, batch, cls)] += list(np.abs(d[v]) / 1e3)
        for k, leg in zip(*np.nonzero((np.abs(dh) > 100.0) & valid[:, None])):
            J = abs(dh[k, leg]) * 1e5 * A_P[leg]
            ratio = abs(d[k]) / J
            steps[key].append(ratio)
            if key in ("ready/none", "ready/gyro", "true/exact"):
                step_rows.append(dict(variant=key, batch=batch, run=run, leg=int(leg), t=round(float(t[k + 1]), 2),
                                      dp=round(float(dh[k, leg]), 1), ratio=round(float(ratio), 3), fs_kN=round(fsk, 2)))
        vinj = valid & post
        for J in JUMPS:
            for L in range(4):
                jf = J * 1e5 * A_P[L]
                dp = dh[:, L] + J
                cand = vinj & (np.abs(dp) > 100.0)
                for th in THRESHOLDS:
                    if th != 0.5 and key not in ("ready/gyro", "zero/none"):
                        continue
                    det = np.abs(d + jf) >= th * np.abs(dp) * 1e5 * A_P[L]
                    tag = key if th == 0.5 else f"{key}@{th}"
                    for qk, qs in (("quiet", cand & ~trans), ("transient", cand & trans)):
                        acc = inj[(tag, J, qk)]
                        acc[0] += int(qs.sum())
                        acc[1] += int((qs & det).sum())

res = {"mass_error": {}, "dr_transient_kN": {}, "real_steps": {}, "injection": {}, "step_rows": step_rows,
       "ready_bias_contribution_max_kN": max(bias_contrib) if bias_contrib else None}
print("== mass error vs 38,400.8 kg (fraction)")
for (b, kind), v in sorted(mass_err.items()):
    v = np.array(v)
    res["mass_error"][f"{b}/{kind}"] = dict(n=int(v.size), min=float(v.min()), median=float(np.median(v)),
                                            max=float(v.max()))
    print(f"  {b:28s} {kind:14s} n {v.size:3d} min {v.min():+.4f} med {np.median(v):+.4f} max {v.max():+.4f}")
print("  READY-mass bias contribution max |(M_ready - M) d f_z| [kN]:", res["ready_bias_contribution_max_kN"])
print("== transient |d r| [kN] (all batches pooled per F_s class)")
pooled = defaultdict(list)
for (key, b, cls), v in dr.items():
    pooled[(key, cls)] += v
    pooled[(key, "all")] += v
for (key, cls), v in sorted(pooled.items()):
    v = np.array(v)
    if not v.size:
        continue
    row = dict(n=int(v.size), p50=float(np.percentile(v, 50)), p99=float(np.percentile(v, 99)), max=float(v.max()),
               over_47_5=int((v >= 47.5).sum()))
    res["dr_transient_kN"][f"{key}/{cls}"] = row
    print(f"  {key:12s} {cls:8s} n {row['n']:5d} p50 {row['p50']:5.1f} p99 {row['p99']:5.1f} max {row['max']:5.1f}"
          f" >=47.5: {row['over_47_5']}")
print("== real head steps > 100 bar: |d r| / J")
for key, v in sorted(steps.items()):
    v = np.array(v)
    res["real_steps"][key] = dict(n=int(v.size), max=float(v.max()), p90=float(np.percentile(v, 90)),
                                  over_0_5=int((v >= 0.5).sum()))
    print(f"  {key:12s} n {v.size:3d} max {v.max():.3f} p90 {np.percentile(v, 90):.3f} >=0.5: {(v >= 0.5).sum()}")
print("== injected persistent jump detection")
for (key, J, qk), (n, dcount) in sorted(inj.items()):
    if n:
        res["injection"][f"{key}/{J:+.0f}/{qk}"] = dict(n=n, rate=dcount / n)
        if qk == "transient" or dcount < n:
            print(f"  {key:12s} J {J:+5.0f} {qk:9s} n {n:6d} detected {dcount / n:7.2%}")
out_json.parent.mkdir(parents=True, exist_ok=True)
out_json.write_text(json.dumps(res, indent=1), encoding="utf-8")
