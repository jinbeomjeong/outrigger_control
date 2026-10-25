"""Probe the two E/N gate misses of P-S8-19 (read only): ML low-class probability and
quantile around t_on, against the reading, the seal band and the truth."""
import os
import sys
from pathlib import Path

os.environ.setdefault("MKL_THREADING_LAYER", "TBB")
# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import os as _os
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
# ---
ROOT = REPO
sys.path.insert(0, str(ROOT / "03_src"))

import lightgbm  # noqa: E402
import numpy as np  # noqa: E402
import onnxruntime  # noqa: E402

from outrigger_sim.contact_episode import load_episode  # noqa: E402
from outrigger_sim.ml.dataset import build_examples, tabular_features  # noqa: E402
from outrigger_sim.ml.reading_basis import (  # noqa: E402
    ReadingBasis, pad_record_at_samples, pads_path, with_reading_basis)

RUN = ROOT / r"07_results\S8\ml_main_20261025_090131"
SEEDS = [20261024 + k for k in range(5)]
THR_GRU = dict(zip(SEEDS, [0.09, 0.3, 0.02, 0.31, 0.05]))
THR_LGB = dict(zip(SEEDS, [0.21, 0.17, 0.27, 0.18, 0.22]))
CASES = [("N_G4_Fs8_pressure", 3, 40.4, 40.9), ("N_SS_Fs8_pressure", 3, 50.9, 51.1)]


def softmax(z):
    e = np.exp(z - z.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


sessions = {s: onnxruntime.InferenceSession(str(RUN / f"ml_train_v2/seed_{s}/contact_gru.onnx"),
                                            providers=["CPUExecutionProvider"]) for s in SEEDS}
boosters = {s: lightgbm.Booster(model_file=str(RUN / f"ml_train_v2/seed_{s}/lgbm_classifier.txt"))
            for s in SEEDS}
qboost = {s: lightgbm.Booster(model_file=str(RUN / f"ml_train_v2/seed_{s}/lgbm_quantile.txt"))
          for s in SEEDS}

for run, leg, t_on, t_off in CASES:
    ep = load_episode(RUN / "ml_dataset_en" / f"{run}.npz")
    contact_N, seal_N = pad_record_at_samples(pads_path(ep, ROOT), ep["t_s"])
    ep = with_reading_basis(ep, ReadingBasis.CORRECTED, contact_N, seal_N)
    t = np.asarray(ep["t_s"], float)
    tf = np.asarray(ep["true_force_N"], float)[:, leg]
    tfm = np.asarray(ep["true_force_min_N"], float)[:, leg]
    low = np.asarray(ep["lower_reading_N"], float)[:, leg]
    band = np.asarray(ep["seal_band_N"], float)[:, leg]
    net = np.asarray(ep["net_force_N"], float)[:, leg]
    cmd = np.asarray(ep["command_m_s"], float)[:, leg]
    phase = np.asarray(ep["phase"]).astype(str)
    Fmin = ep.F_min_N
    print(f"\n##### {run} leg {leg} F_min {Fmin:.0f} N  rod_w {ep.rod_weight_N[leg]:.0f} N  "
          f"F_seal_limit RR median {np.nanmedian(seal_N[:, leg]):.0f} N  "
          f"meta keys: {sorted(k for k in ep.meta if 'seal' in k or 'judge' in k or 'mode' in k)}")
    ex = build_examples([ep])
    sel = ex.leg == leg
    rows = ex.row[sel]
    p_gru, q_gru = {}, {}
    for s in SEEDS:
        raw = sessions[s].run(None, {"sequences": ex.sequences[sel], "context": ex.context[sel]})[0]
        pr = softmax(raw[:, :3])
        p_gru[s] = pr[:, 1] + pr[:, 2]
        q_gru[s] = raw[:, 4] if raw.shape[1] > 4 else raw[:, 3]
    feats = tabular_features(ex.subset(sel))
    p_lgb = {s: (lambda P: P[:, 1] + P[:, 2])(boosters[s].predict(feats)) for s in SEEDS}
    q_lgb = {s: qboost[s].predict(feats) for s in SEEDS}
    below = np.flatnonzero(tfm < Fmin)
    if t_on is None:
        # first truth episode below F_min
        if below.size == 0:
            print("  no truth sample below F_min on this leg")
            continue
        t_on = t[below[0]]
        t_off = t[below[below < below[0] + 20][-1]]
    print(f"  truth below F_min rows: {below.size}, min true_force_min {np.nanmin(tfm):.0f} N")
    window = (t >= t_on - 1.5) & (t <= t_off + 1.0)
    print("   t      phase   cmd[mm/s] net[kN] lower[kN] band[kN] lowB[kN] true[kN] tmin[kN] | "
          "GRU p_low per seed | GRU q[kN] med | LGB p_low per seed | LGB q med")
    for i in np.flatnonzero(window):
        k = np.flatnonzero(rows == i)
        if k.size:
            j = k[0]
            pg = " ".join(f"{p_gru[s][j]:.2f}" for s in SEEDS)
            pl = " ".join(f"{p_lgb[s][j]:.2f}" for s in SEEDS)
            qg = np.median([q_gru[s][j] for s in SEEDS])
            ql = np.median([q_lgb[s][j] for s in SEEDS])
        else:
            pg = pl = "-"
            qg = ql = np.nan
        mark = "*" if t_on - 1e-6 <= t[i] <= t_off + 1e-6 else " "
        print(f" {mark}{t[i]:6.1f} {phase[i]:>7} {cmd[i]*1e3:7.2f} {net[i]/1e3:7.2f} {low[i]/1e3:7.2f}"
              f" {band[i]/1e3:6.2f} {(low[i]-band[i])/1e3:7.2f} {tf[i]/1e3:7.2f} {tfm[i]/1e3:7.2f} | {pg} | {qg:6.2f}"
              f" | {pl} | {ql:6.2f}")
    ev = np.array([np.flatnonzero(rows == i)[0] for i in np.flatnonzero(
        (t >= t_on - 1e-6) & (t <= t_off + 1e-6)) if np.any(rows == i)])
    for s in SEEDS:
        print(f"  seed {s}: GRU max p_low in event {p_gru[s][ev].max():.3f} (thr {THR_GRU[s]}), "
              f"min q {q_gru[s][ev].min():.2f} kN; LGB max p {p_lgb[s][ev].max():.3f} "
              f"(thr {THR_LGB[s]}), min q {q_lgb[s][ev].min():.2f} kN; F_min {Fmin/1e3:.3f}")
