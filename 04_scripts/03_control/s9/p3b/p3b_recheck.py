"""S9 P3b path-2 recomputation of P3-1 / P3-3 / P3-4 against the runner values (spec rev. 60, 307).

Independent of the runner's judgement code, from ``step_series.npz`` (1 ms):

- P3-4: max |roll|, |pitch| over the runner window. The window start is re-derived from the
  two-sided creep stop (all pad ``sinkage_rate_0p2s_m_s`` < 0.1 mm/s holding to the end)
  and the last READY entry.
- P3-3: min true ``F_cyl_N`` after departure (departure re-derived: crawler normal < 0.01 W
  held for 0.1 s).
- P3-1: max crawler normal over [READY, READY + 10 s] and recontact (>= 0.01 W) after departure.

Prints one line per case and the worst absolute difference to the runner values.

Inputs: ``07_results/S9/batch_P3b_20261026_122444/P3b_*/`` (``step_series.npz``, ``result.json``)
and ``06_analysis/02_control/s9/p3b/p3b_collect.json`` (from ``p3b_collect.py``).
Output: standard output only.

Usage (dynamics-dev, from the repository root, one command line):
  conda run -n dynamics-dev python -I 04_scripts/03_control/s9/p3b/p3b_recheck.py
      [<batch_dir> [<collect_json>]]
"""

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_BATCH = ROOT / "07_results" / "S9" / "batch_P3b_20261026_122444"
DEFAULT_COLLECT = ROOT / "06_analysis" / "02_control" / "s9" / "p3b" / "p3b_collect.json"


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("batch_dir", nargs="?", type=Path, default=DEFAULT_BATCH)
    parser.add_argument("collect_json", nargs="?", type=Path, default=DEFAULT_COLLECT)
    return parser.parse_args()


def main():
    args = _parse_args()
    batch = args.batch_dir
    col = json.loads(args.collect_json.read_text(encoding="utf-8"))
    worst = {"p34": 0.0, "p33": 0.0, "dep": 0.0, "creep": 0.0}
    for k, v in col.items():
        ss = np.load(batch / k / "step_series.npz")
        t = ss["t_s"]
        cr = ss["scm_crawler_normal_N"]
        r = json.loads((batch / k / "result.json").read_text(encoding="utf-8"))
        W = r["p3b"]["weight_N"]
        # departure: first time crawler < 0.01 W held for 0.1 s
        below = cr < 0.01 * W
        dt = t[1] - t[0]
        n = int(round(0.1 / dt))
        run = np.convolve(below.astype(int), np.ones(n, int), "valid")
        i0 = int(np.argmax(run == n))
        t_dep = t[i0]
        # recontact after confirm (> 0.01 W again)
        rec = np.any(cr[i0 + n:] >= 0.01 * W)
        # creep stop two-sided: all |rate| < 0.1 mm/s holding to the end
        rate = np.abs(ss["sinkage_rate_0p2s_m_s"])
        ok = np.all(rate < 1e-4, axis=1) & (t >= t_dep)
        bad = np.where(~ok)[0]
        t_creep = t[bad[-1] + 1] if len(bad) and bad[-1] + 1 < len(t) else t[0]
        t_ready_last = v["P3-4"]["t_ready_last_entry_s"]
        t0 = max(t_creep, t_ready_last)
        m = t >= t0 - 1e-9
        p34 = float(np.max(np.abs(ss["roll_pitch_deg"][m])))
        p33 = float(np.min(ss["F_cyl_N"][t >= t_dep]))
        t_ready = r["p3b"]["P3-1_crawler"]["t_ready_s"]
        p31 = float(np.max(cr[(t >= t_ready) & (t <= t_ready + 10.0)]))
        d34 = abs(p34 - v["P3-4"]["p34_absmax_overall_deg"])
        d33 = abs(p33 - v["P3-3_min_N"])
        ddep = abs(t_dep - v["departure"]["t_departure_s"])
        dcr = abs(t_creep - v["P3-4"]["t_creep_stop_final_two_sided_s"])
        worst = {"p34": max(worst["p34"], d34), "p33": max(worst["p33"], d33),
                 "dep": max(worst["dep"], ddep), "creep": max(worst["creep"], dcr)}
        print(f"{k[4:]}: P3-4 {p34:.5f} (runner {v['P3-4']['p34_absmax_overall_deg']:.5f}) | "
              f"P3-3 {p33/1e3:.2f} kN (runner {v['P3-3_min_N']/1e3:.2f}) | dep {t_dep:.3f} "
              f"(runner {v['departure']['t_departure_s']:.3f}) | creep {t_creep:.3f} "
              f"(runner {v['P3-4']['t_creep_stop_final_two_sided_s']:.3f}) | "
              f"P3-1 max {p31:.1f} N recontact {rec}")
    print("worst abs diff:", worst)


if __name__ == "__main__":
    main()
