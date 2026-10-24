"""Split the post lift-off minimum into a slow mean and an oscillation, L1 vs L2b (read-only).

Spec ``s6_control_spec.md`` rev. 37 193.2 (control-expert re-analysis, moved from the session
scratchpad 2026-10-24). 1 ms ``pads.npz`` ``F_cyl_min_interval`` from lift-off - 2 s to + 8 s;
slow = 1 s centred mean (1001 samples, ``np.convolve`` "same"); half-amplitude = (max - min) / 2
of force - slow in [0, 3] s and [3, 6] s after lift-off. The judged version of the slow
component is ``outrigger_sim.verify.s7_control.slow_force_metrics`` (C-R18). Also prints the
crawler release time (10 Hz crawler z force, 50 % of its value 1 s before lift-off) and the body
angular-rate RMS over the 2 s before lift-off.

Run (project root; dynamics-dev or Chrono-dev)::

    python -I 04_scripts/03_control/s7c/osc_rpB.py [--batch 07_results/S7/<batch>] [pairs ...]
"""
import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BATCH = "07_results/S7/ctrl3_20261024_154939"
DEFAULT_PAIRS = ("D8_top_rpB_b1.0", "smoke_top_flat", "H4V_top_fdown3.5")
LEGS = ["FL", "FR", "RL", "RR"]

ap = argparse.ArgumentParser()
ap.add_argument("pairs", nargs="*", default=list(DEFAULT_PAIRS))
ap.add_argument("--batch", default=DEFAULT_BATCH, help="batch dir (relative to the project root)")
args = ap.parse_args()
B = Path(args.batch) if Path(args.batch).is_absolute() else ROOT / args.batch

vj = json.loads((B / "verify_S7C.json").read_text(encoding="utf-8"))
met = {m["case"]: m for m in vj["metrics"]}

for pair in args.pairs:
    for eng in ("L1", "L2b"):
        case = f"{eng}_{pair}"
        m = met[case]
        t0, lo = m["times_s"]["t0"], m["times_s"]["liftoff"]
        p = np.load(B / case / "pads.npz")
        r = np.load(B / case / "record" / "record.npz")
        tp = p["t"] - t0
        F = p["F_cyl_min_interval"]
        win = 1001  # 1.0 s centred mean at 1 ms
        ker = np.ones(win) / win
        sel = (tp >= lo - 2.0) & (tp <= lo + 8.0)
        idx = np.where(sel)[0]
        out = []
        for leg in range(4):
            x = F[idx, leg]
            mean = np.convolve(x, ker, mode="same")
            osc = x - mean
            core = (tp[idx] >= lo) & (tp[idx] <= lo + 3.0)
            core2 = (tp[idx] >= lo + 3.0) & (tp[idx] <= lo + 6.0)
            out.append((LEGS[leg], x[core].min() / 1e3, mean[core].min() / 1e3,
                        (osc[core].max() - osc[core].min()) / 2e3,
                        (osc[core2].max() - osc[core2].min()) / 2e3))
        # crawler release: crawler z force from its value 1 s before lift-off to 50 % (10 Hz)
        tr = r["t"] - t0
        Fc = r["F_crawler"][:, 2]
        k1 = np.argmin(np.abs(tr - (lo - 1.0)))
        ref = Fc[k1]
        a = np.where((tr > lo - 3) & (tr <= lo) & (Fc <= 0.5 * ref))[0]
        t50 = tr[a[0]] if len(a) else np.nan
        # body angular rate rms in 2 s before lift-off (crawler segment)
        b = (tr > lo - 2.0) & (tr <= lo)
        w = r["body_omega"][b]
        print(f"{case:34s} crawler z 1 s before {ref / 1e3:6.1f} kN, 50 % at lift-off - "
              f"{lo - t50:.2f} s; |omega| rms pre-lift-off "
              f"{np.sqrt((w ** 2).sum(1).mean()) * 1e3:.3f} mrad/s")
        for leg, mn, mmean, amp1, amp2 in out:
            print(f"   {leg}: min {mn:7.2f} kN, min 1 s mean {mmean:7.2f} kN, osc half-amp "
                  f"[0,3] s {amp1:5.2f} kN, [3,6] s {amp2:5.2f} kN")
