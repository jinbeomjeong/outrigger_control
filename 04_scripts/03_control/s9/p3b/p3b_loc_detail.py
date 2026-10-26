"""S9 P3b LOC delay and plateau-rise detail for the soil-mode cases (spec rev. 60, 308 / 310).

Cause analysis for P3-2 (LOC delay, J1 B) and P3-7 (plateau margin). For each case:
crawler-normal profile before departure, t_P - departure, tail duration and mean applied
speed, and the minimum S-1 rise over windows whose end has crawler load above
1 kN / 0.01 W / 0.05 W / 0.10 W (reading and truth). The S-1 replay is the one in
``p3b_collect.py`` (imported from this folder), variant lag 0 / shift 0.

Inputs (git-external raw data): ``07_results/S9/batch_P3b_20261026_122444/P3b_*/``
(``result.json``, ``record/record.npz``, ``step_series.npz``).
Output: ``06_analysis/02_control/s9/p3b/p3b_loc_detail.json`` (default).

Usage (dynamics-dev, from the repository root, one command line):
  conda run -n dynamics-dev python -I 04_scripts/03_control/s9/p3b/p3b_loc_detail.py
      [<batch_dir> [<out_json>]]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

# `python -I` does not put the script folder on sys.path; p3b_collect.py lives next to this file.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from p3b_collect import A_ANN, A_P, DEFAULT_BATCH, ROOT, V_MAX, reconstruct_s1  # noqa: E402

DEFAULT_OUT = ROOT / "06_analysis" / "02_control" / "s9" / "p3b" / "p3b_loc_detail.json"


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("batch_dir", nargs="?", type=Path, default=DEFAULT_BATCH)
    parser.add_argument("out_json", nargs="?", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main():
    args = _parse_args()
    batch = args.batch_dir
    out = {}
    for case in sorted(p for p in batch.iterdir() if p.is_dir() and p.name.startswith("P3b_")):
        r = json.loads((case / "result.json").read_text(encoding="utf-8"))
        soil, phases = r["c2_soil"], r["phases"]
        rec = np.load(case / "record" / "record.npz")
        ss = np.load(case / "step_series.npz")
        ts, cr = ss["t_s"], ss["scm_crawler_normal_N"]
        W = soil["W_ref_N"]

        def crawler_at(tq, ts=ts, cr=cr):
            i = int(np.clip(np.searchsorted(ts, tq), 0, len(ts) - 1))
            return float(cr[i])

        t = rec["t"]
        f_read = (rec["meas.head_pressure"] * A_P - rec["meas.rod_pressure"] * A_ANN).sum(axis=1)
        f_true = rec["F_cyl"].sum(axis=1)
        u = rec["u_applied"]
        res = {}
        for name, e, f in (("read", rec["meas.stroke"], f_read), ("true", rec["s_motor"], f_true)):
            tp, tl, wins = reconstruct_s1(t, u, e, f, phases, W, crawler_at, 0.0)
            if name == "true":
                tl_r = soil.get("t_loc_s")
                wins = [w for w in wins if tl_r is None or w[0] <= tl_r + 1e-9]
            buckets = {}
            for lab, thr in (("gt1kN", 1e3), ("gt0p01W", 0.01 * W), ("gt0p05W", 0.05 * W),
                             ("gt0p10W", 0.10 * W)):
                sel = [w for w in wins if crawler_at(w[0]) > thr]
                if sel:
                    wmin = min(sel, key=lambda w: w[1])
                    buckets[lab] = {"n": len(sel), "rise_min_kN": wmin[1] / 1e3,
                                    "t_end_s": wmin[0],
                                    "crawler_at_end_kN": crawler_at(wmin[0]) / 1e3,
                                    "crawler_at_start_kN": crawler_at(wmin[4]) / 1e3}
                else:
                    buckets[lab] = {"n": 0}
            res[name] = {"t_P": tp, "t_loc": tl, "buckets": buckets}
        dep = r["p3b"]["departure"]["t_departure_s"]
        tp, tl = soil.get("t_P_s"), soil.get("t_loc_s")
        m = (t >= tp - 1e-9) & (t <= tl + 1e-9) if tp is not None else np.zeros_like(t, bool)
        # crawler profile: last time above 0.20 .. 0.01 W up to departure + 0.1 s
        prof = {}
        for frac in (0.20, 0.10, 0.05, 0.02, 0.01):
            idx = np.where((ts <= dep + 0.1) & (cr > frac * W))[0]
            prof[f"last_above_{frac}W_s"] = float(ts[idx[-1]]) if len(idx) else None
        out[case.name] = {
            "t_departure_s": dep, "t_P_s": tp, "t_loc_s": tl,
            "tP_minus_dep_s": None if tp is None else tp - dep,
            "tail_s": None if tp is None else tl - tp,
            "tail_mean_u_over_vmax": float(u[m].mean() / V_MAX) if m.any() else None,
            "tail_min_leg_u_over_vmax": float(u[m].min() / V_MAX) if m.any() else None,
            "crawler_at_tP_kN": None if tp is None else crawler_at(tp) / 1e3,
            "crawler_profile": prof,
            "rise": res,
        }
        summary_keys = ("tP_minus_dep_s", "tail_s", "tail_mean_u_over_vmax", "crawler_at_tP_kN")
        read_buckets = {
            k: (round(v["rise_min_kN"], 2), round(v["crawler_at_end_kN"], 1)) if v["n"] else None
            for k, v in res["read"]["buckets"].items()}
        profile_rel = {k: round(v - dep, 2) if v is not None else None for k, v in prof.items()}
        print(case.name, json.dumps({k: out[case.name][k] for k in summary_keys}),
              json.dumps(read_buckets), json.dumps(profile_rel), flush=True)
    args.out_json.write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
