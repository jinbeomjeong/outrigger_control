"""Compare L1 vs L2b around the crawler lift-off of one S7 control ③ pair (read-only).

Spec ``s6_control_spec.md`` rev. 37 193.1 (control-expert re-analysis, moved from the session
scratchpad 2026-10-24). Reads ``record/record.npz`` (10 Hz), ``pads.npz`` (1 ms) and
``r8_series.npz`` of ``L1_<pair>`` / ``L2b_<pair>`` in a ``run_S7C.py`` batch and the case times
from its ``verify_S7C.json``. Prints the 10 Hz table around TOUCH end and lift-off (crawler
normal force, cylinder forces, twist ``n^T F``, motor strokes, guard, issued speeds), the 1 ms
minimum after lift-off and per-window minima. Times relative to each engine's controller start.

Run (project root; dynamics-dev or Chrono-dev)::

    python -I 04_scripts/03_control/s7c/pair_rpB.py [pair] [--batch 07_results/S7/<batch>]
"""
import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BATCH = "07_results/S7/ctrl3_20261024_154939"
N_TW = np.array([0.476, -0.476, -0.523, 0.523])
FMIN = 9414.58911

ap = argparse.ArgumentParser()
ap.add_argument("pair", nargs="?", default="D8_top_rpB_b1.0")
ap.add_argument("--batch", default=DEFAULT_BATCH, help="batch dir (relative to the project root)")
args = ap.parse_args()
B = Path(args.batch) if Path(args.batch).is_absolute() else ROOT / args.batch
pair = args.pair

vj = json.loads((B / "verify_S7C.json").read_text(encoding="utf-8"))
met = {m["case"]: m for m in vj["metrics"]}

for eng in ("L1", "L2b"):
    case = f"{eng}_{pair}"
    m = met[case]
    t0 = m["times_s"]["t0"]
    lv = m["times_s"]["touch"]  # end of TOUCH (relative)
    lo = m["times_s"]["liftoff"]
    r = np.load(B / case / "record" / "record.npz")
    p = np.load(B / case / "pads.npz")
    s = np.load(B / case / "r8_series.npz")
    t = r["t"] - t0
    tp = p["t"] - t0
    F = p["F_cyl_min_interval"] if "F_cyl_min_interval" in p.files else p["F_cyl"]
    print(f"== {case}: TOUCH end {lv:.2f}, crawler lift-off {lo:.3f} s (rel. t0)")
    # crawler force and leg loads on 10 Hz record
    Fc = r["F_crawler"]
    sel = (t >= lv - 3.0) & (t <= lo + 4.0)
    print("  t_rel  Fcrawl_z[kN]  Fcyl FL FR RL RR [kN]  twist nTF [kN]  s_motor RL,RR [mm]  "
          "guard  u_issued RL,RR [mm/s]")
    ts = s["t"] - t0
    for k in np.where(sel)[0][::3]:
        j = np.argmin(np.abs(ts - t[k]))
        print(f"  {t[k]:6.2f} {Fc[k, 2] / 1e3:9.1f}  "
              + " ".join(f"{x / 1e3:7.1f}" for x in r["F_cyl"][k])
              + f"  {N_TW @ r['F_cyl'][k] / 1e3:7.2f}  {r['s_motor'][k, 2] * 1e3:7.2f} "
              f"{r['s_motor'][k, 3] * 1e3:7.2f}"
              + f"  {int(s['guard_active'][j])}  {s['issued_u'][j, 2] * 1e3:6.2f} "
              f"{s['issued_u'][j, 3] * 1e3:6.2f}")
    # 1 ms minima after lift-off
    a = tp >= lo
    k = np.argmin(F[a].min(axis=1))
    kk = np.where(a)[0][k]
    print(f"  min after lift-off {F[kk].min() / 1e3:.2f} kN leg "
          f"{['FL', 'FR', 'RL', 'RR'][int(np.argmin(F[kk]))]} at {tp[kk]:.3f} s "
          f"(lift-off + {tp[kk] - lo:.3f} s)")
    # min in windows
    for w0, w1 in ((lo, lo + 1.0), (lo + 1.0, lo + 5.0), (lo + 5.0, m["times_s"]["ready"])):
        b = (tp >= w0) & (tp < w1)
        if b.any():
            mn = F[b].min(axis=0)
            print(f"  window [{w0 - lo:+.1f},{w1 - lo:+.1f}] s after lift-off: min per leg "
                  + " ".join(f"{x / 1e3:.2f}" for x in mn))
    # twist at lift-off and stroke at TOUCH end
    kl = np.argmin(np.abs(t - lo))
    kt = np.argmin(np.abs(t - lv))
    print("  at TOUCH end: s_motor [mm] " + " ".join(f"{x * 1e3:.2f}" for x in r["s_motor"][kt])
          + "; Fcyl [kN] " + " ".join(f"{x / 1e3:.1f}" for x in r["F_cyl"][kt])
          + f"; crawler z {Fc[kt, 2] / 1e3:.1f} kN")
    print("  at lift-off:  s_motor [mm] " + " ".join(f"{x * 1e3:.2f}" for x in r["s_motor"][kl])
          + "; Fcyl [kN] " + " ".join(f"{x / 1e3:.1f}" for x in r["F_cyl"][kl])
          + f"; twist {N_TW @ r['F_cyl'][kl] / 1e3:.2f} kN")
    print(f"  guard periods total {int(s['guard_active'].sum())}")
