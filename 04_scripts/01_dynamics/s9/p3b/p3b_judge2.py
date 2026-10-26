"""S9 P3b dynamics judgement support values, extra checks (dynamics_model.md rev. 53, 5.38).

Per P3b case: crawler full-release time (last crawler normal > 100 N) against LOC (5.38.4),
crawler load after departure, track utilisation restricted to track normal > 5 / 20 / 50 %
of the settle value (5.38.6), loaded pad tilt (pad normal > 1 % of the design load), rut
clearance after departure / last READY, SCM soil parameters, C2 LOC / soil-mode timing
(5.38.5) and the mean leg speed between departure and LOC. Same conventions as
``p3b_judge.py``.

Inputs: ``07_results/S9/batch_P3b_20261026_122444/P3b_*/`` (step_series.npz 1 ms, result.json
with 10 Hz ``s9_rows``) and ``06_analysis/01_chrono/19_S9/s9_P3b_summary.json``.
Output: one intermediate JSON (merged by ``merge_out.py``) plus a printed table.

Usage (dynamics-dev):
  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/s9/p3b/p3b_judge2.py <out_json>
"""

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
B = ROOT / "07_results" / "S9" / "batch_P3b_20261026_122444"
SUMMARY_JSON = ROOT / "06_analysis" / "01_chrono" / "19_S9" / "s9_P3b_summary.json"
DEFAULT_DESIGN_LOADS_N = [119146.3, 117153.2, 72814.2, 70999.3]  # used if result lacks them
SOIL_ORDER = ["G1", "S1", "J2", "J1"]


def _case_extra(name, srow):
    d = np.load(B / name / "step_series.npz")
    r = json.loads((B / name / "result.json").read_text("utf-8"))
    t = d["t_s"]
    cn = d["scm_crawler_normal_N"]
    tn = d["scm_track_normal_raw_N"]
    tu = d["track_utilisation"]
    sm = d["s_motor_m"]
    dep = srow["departure"]["t_departure_s"]
    loc = srow["P3-2_loc"]["t_loc_s"]
    pos = np.where(cn > 100.0)[0]
    t_zero = float(t[pos[-1]]) if pos.size else None  # last time crawler normal > 100 N
    settle_tn = np.array(srow["settle_reference"]["track_normal_N"])
    res = {"t_dep": dep, "t_loc": loc, "t_crawler_last_gt100N": t_zero,
           "loc_minus_zero": None if t_zero is None else loc - t_zero,
           "crawler_N_at_dep_plus": {
               f"+{k}": float(cn[np.searchsorted(t, dep + k)]) for k in (0.5, 1.0, 2.0)}}
    # track utilisation only where the track normal exceeds 5 / 20 / 50 % of the settle value
    for frac in (0.05, 0.2, 0.5):
        m = tn > frac * settle_tn
        u = np.where(m, tu, np.nan)
        j = np.nanargmax(np.nan_to_num(u, nan=-1), axis=0)
        res[f"tu_max_N>{frac}"] = [
            float(np.nanmax(u[:, k])) if np.isfinite(u[:, k]).any() else None for k in (0, 1)]
        res[f"tu_t_N>{frac}"] = [float(t[j[k]]) for k in (0, 1)]
        res[f"tu_Nfrac_at_max_N>{frac}"] = [float(tn[j[k], k] / settle_tn[k]) for k in (0, 1)]
    # 10 Hz rows: loaded pad tilt and rut clearance
    rows = r["s9_rows"]
    tr = np.array([x["t_s"] for x in rows])
    tilt = np.array([x["pad_tilt_deg"] for x in rows], dtype=float)
    pnr = np.array([x["scm_pad_normal_N"] for x in rows], dtype=float)
    rut = np.array([np.nan if x.get("rut_clearance_m") is None else x["rut_clearance_m"]
                    for x in rows], dtype=float)
    design = np.array(r["p3b"].get("design_loads_N", DEFAULT_DESIGN_LOADS_N))
    loaded = pnr > 0.01 * design
    tl = np.where(loaded, tilt, np.nan)
    res["pad_tilt_loaded_max"] = np.nanmax(tl, axis=0).tolist()
    res["pad_tilt_loaded_t"] = [
        float(tr[np.nanargmax(np.nan_to_num(tl[:, k], nan=-1))]) for k in range(4)]
    res["pad_tilt_end"] = tilt[-1].tolist()
    late = tr >= tr[-1] - 10
    res["pad_tilt_last10s_max"] = np.nanmax(tilt[late], axis=0).tolist()
    p35 = r["p3b"]["P3-5_clearance_stroke"]
    res["rut_min_after_dep_mm"] = p35["rut_clearance_min_after_departure_m"] * 1e3
    res["rut_end_mm"] = p35["rut_clearance_end_m"] * 1e3
    rl = srow["P3-4_attitude"]["t_ready_last_entry_s"]
    res["rut_min_after_ready_mm"] = float(np.nanmin(rut[tr >= rl]) * 1e3)
    rut_ok_after_dep = (rut >= 0.025) & (tr >= dep)
    res["t_rut_ge_25mm"] = (
        float(tr[np.argmax(rut_ok_after_dep)]) if np.any(rut_ok_after_dep) else None)
    sc = r["meta"]["scm"]["soil"]["chrono"]
    res["soil_chrono"] = {k: sc[k] for k in sc if not isinstance(sc[k], (dict, list))}
    res["c2_soil"] = {k: r["c2_soil"][k] for k in (
        "loc", "soil_mode", "t_P_s", "t_loc_s", "soil_mode_t_s", "push_m",
        "clearance_at_P_m", "clearance_at_loc_m", "W_ratio")}
    res["soil_mode_used"] = srow["P3-2_loc"]["soil_mode_used"]
    w = (t > dep) & (t <= loc)
    res["leg_speed_dep_loc_mm_s"] = (
        ((sm[w][-1] - sm[w][0]) / (t[w][-1] - t[w][0]) * 1e3).tolist() if w.sum() > 2 else None)
    return res


def _join(v, n=2):
    return "/".join("nan" if x is None else f"{x:.{n}f}" for x in v)


def _print_table(out, summ):
    for k in sorted(out, key=lambda k: (SOIL_ORDER.index(summ[k]["soil"]), k)):
        x = out[k]
        t_zero = x["t_crawler_last_gt100N"]
        loc_zero = x["loc_minus_zero"]
        speed = x["leg_speed_dep_loc_mm_s"]
        print(k[4:], "zero", None if t_zero is None else round(t_zero, 2),
              "loc-zero", None if loc_zero is None else round(loc_zero, 2),
              "Ncr", {kk: round(v) for kk, v in x["crawler_N_at_dep_plus"].items()},
              "soilmode", x["soil_mode_used"], "v", None if speed is None else _join(speed, 1))
        print("   tu05", _join(x["tu_max_N>0.05"], 3),
              "Nfrac", _join(x["tu_Nfrac_at_max_N>0.05"], 3),
              "t", _join(x["tu_t_N>0.05"], 1),
              "| tu20", _join(x["tu_max_N>0.2"], 3), "| tu50", _join(x["tu_max_N>0.5"], 3))
        print("   tilt loaded", _join(x["pad_tilt_loaded_max"], 3),
              "t", _join(x["pad_tilt_loaded_t"], 1), "end", _join(x["pad_tilt_end"], 3),
              "| rut min dep", f"{x['rut_min_after_dep_mm']:.1f}",
              "after ready", f"{x['rut_min_after_ready_mm']:.1f}",
              "end", f"{x['rut_end_mm']:.1f}", "t>=25", x["t_rut_ge_25mm"])
    for s in SOIL_ORDER:
        k = next(k for k in out if summ[k]["soil"] == s)
        print(s, out[k]["soil_chrono"])


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out_json", type=Path)
    return parser.parse_args()


def main():
    args = _parse_args()
    summ = json.loads(SUMMARY_JSON.read_text("utf-8"))["rows"]
    out = {name: _case_extra(name, srow) for name, srow in summ.items()}
    args.out_json.write_text(json.dumps(out, indent=1, default=float), "utf-8")
    _print_table(out, summ)


if __name__ == "__main__":
    main()
