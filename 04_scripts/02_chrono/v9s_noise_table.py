"""V9 (b) PSOR-noise table: law output F and pad contact force noise per dt x solver setting.

``dynamics_model.md`` 5.22.3 (b). Reads the V9 cases of the S7 baseline batch (PSOR 50, recovery
speed 0.6 m/s) and the ``V9s_*`` cases of a sensitivity batch, writes ``v9s_noise.json`` and
``v9s_noise.csv`` into the sensitivity batch folder. Judgement is dynamics-expert's; this script
only measures. Usage (Chrono-dev python; no pychrono import)::

    python -I -X utf8 v9s_noise_table.py <sensitivity batch dir> [--base <baseline batch dir>]

Noise metrics (series sampled every 1 ms, SI units, per leg FL, FR, RL, RR):

* ``hp20_std``: std of ``y - centred 20-sample mean`` (the judge's 20 ms V9 filter) in the still
  window (last ``STILL_S`` s); step-to-step PSOR noise.
* ``raw_std_last1s``: plain std over the last 1 s (includes any slow motion, < 1 % here).
* V9 numbers as ``judge_S7.py``: final F mean over the last 3 / f1 s, transient extreme RL dF on
  20-sample centred means minus the first-50 ms mean, error ratio (a - b) / (b - c) of the three
  coarse dt.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "07_results" / "S7"
BASE = RESULTS / "run_20261024_033206"
DTS = (1.0e-4, 5.0e-5, 2.5e-5, 1.0e-5)
SETTINGS = {"base_psor50_rec0p6": "V9_FLp1_dt{dt:.1e}",
            "A_psor100_rec0p6": "V9s_psor100_FLp1_dt{dt:.1e}",
            "B_psor50_rec0p05": "V9s_rec005_FLp1_dt{dt:.1e}"}
STILL_S = 5.0
WINDOW = 20
BASELINE_S = 0.05


def centred_mean(y: np.ndarray, window: int) -> np.ndarray:
    c = np.cumsum(np.vstack([np.zeros((1, y.shape[1])), y]), axis=0)
    return (c[window:] - c[:-window]) / window


def hp_std(t: np.ndarray, y: np.ndarray, t_from: float) -> np.ndarray:
    m = centred_mean(y, WINDOW)
    lo = WINDOW // 2
    resid = y[lo: lo + m.shape[0]] - m
    tc = t[lo: lo + m.shape[0]]
    return resid[tc >= t_from].std(axis=0)


def case_numbers(path: Path, tail_s: float) -> dict:
    z = np.load(path / "series.npz")
    t = z["t_s"]
    f = z["cylinder_force_N"]
    n = z["pad_normal_N"]
    t_still = t[-1] - STILL_S
    last1 = t >= t[-1] - 1.0
    last = t >= t[-1] - tail_s
    base = t <= t[0] + BASELINE_S
    f_rl = centred_mean(f[:, 2:3], WINDOW)[:, 0]
    result = json.loads((path / "result.json").read_text(encoding="utf-8"))
    return {
        "F_hp20_std_N": hp_std(t, f, t_still).tolist(),
        "N_hp20_std_N": hp_std(t, n, t_still).tolist(),
        "F_raw_std_last1s_N": f[last1].std(axis=0).tolist(),
        "N_raw_std_last1s_N": n[last1].std(axis=0).tolist(),
        "final_F_N": f[last].mean(axis=0).tolist(),
        "final_roll_pitch_deg": z["roll_pitch_deg"][last].mean(axis=0).tolist(),
        "transient_RL_dF_min_N": float((f_rl - f[base, 2].mean()).min()),
        "wall_s": result["run"]["wall_s"], "steps": result["run"]["steps"],
        "solver_override": result.get("solver_override"),
        "nonfinite": result["series"]["nonfinite_values"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("batch", type=Path)
    ap.add_argument("--base", type=Path, default=BASE)
    args = ap.parse_args(argv)
    batch = args.batch if args.batch.is_absolute() else RESULTS / args.batch
    refs = json.loads((ROOT / "06_analysis" / "00_dynamics" / "reference.json").read_text(
        encoding="utf-8"))
    f1 = refs["L2b_NSC_reference_rev33"]["levels"]["top"]["modes"]["LOCK"][
        "f_damped_Hz (first 6)"][0]
    tail = 3.0 / f1
    out: dict = {"base_batch": str(args.base), "sensitivity_batch": str(batch),
                 "still_window_s": STILL_S, "hp_window_samples": WINDOW, "sample_s": 1e-3,
                 "final_tail_s": tail, "legs": ["FL", "FR", "RL", "RR"], "settings": {}}
    rows = []
    for name, pattern in SETTINGS.items():
        folder = args.base if name.startswith("base") else batch
        per = {}
        for dt in DTS:
            p = folder / pattern.format(dt=dt)
            if not (p / "series.npz").exists():
                continue
            per[f"{dt:g}"] = c = case_numbers(p, tail)
            rows.append({"setting": name, "dt_s": dt,
                         "F_hp20_std_max_N": max(c["F_hp20_std_N"]),
                         "F_hp20_std_FL_N": c["F_hp20_std_N"][0],
                         "F_hp20_std_RL_N": c["F_hp20_std_N"][2],
                         "N_hp20_std_max_N": max(c["N_hp20_std_N"]),
                         "F_raw_std_last1s_max_N": max(c["F_raw_std_last1s_N"]),
                         "N_raw_std_last1s_max_N": max(c["N_raw_std_last1s_N"]),
                         "transient_RL_dF_min_N": c["transient_RL_dF_min_N"],
                         "final_F_FL_N": c["final_F_N"][0], "wall_s": c["wall_s"]})
        v = {float(k): per[k]["transient_RL_dF_min_N"] for k in per}
        coarse = [v[d] for d in DTS[:3] if d in v]
        ratio = ((coarse[0] - coarse[1]) / (coarse[1] - coarse[2])
                 if len(coarse) == 3 and coarse[1] != coarse[2] else math.nan)
        diff_ref = ({f"{d:g}": v[d] - v[1.0e-5] for d in DTS[:3] if d in v}
                    if 1.0e-5 in v else {})
        out["settings"][name] = {"cases": per, "transient_error_ratio": ratio,
                                 "transient_minus_1e-5_N": diff_ref}
    (batch / "v9s_noise.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    with (batch / "v9s_noise.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['setting']:20s} dt {r['dt_s']:.1e}  F hp {r['F_hp20_std_max_N']:8.1f}  "
              f"N hp {r['N_hp20_std_max_N']:9.1f}  F raw {r['F_raw_std_last1s_max_N']:8.1f}  "
              f"N raw {r['N_raw_std_last1s_max_N']:9.1f}  trans {r['transient_RL_dF_min_N']:9.1f}"
              f"  wall {r['wall_s']:6.1f}")
    for name, s in out["settings"].items():
        print(name, "ratio", s["transient_error_ratio"], "minus 1e-5", s["transient_minus_1e-5_N"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
