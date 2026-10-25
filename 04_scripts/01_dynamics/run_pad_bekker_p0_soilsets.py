"""P0 reduced Bekker series model re-run with the S9 soil sets of 02_params/scm_soil_sets.json (no Chrono).

Doc: 00_docs/01_dynamics/dynamics_model.md 5.32 (rev. 46). Model and idealised levelling law: run_pad_bekker_p0.py
(5.31.2), unchanged and imported. Only the auger top level is run (5.31.1: the three levels give identical results in
this vertical quasi-static model).
Output 06_analysis/00_dynamics/pad_bekker_p0_soilsets.json
Run: conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_pad_bekker_p0_soilsets.py [--cache DIR]
Regression: J1 / J2 / S1 nominal sets use the P0 inputs (K 2e8) -> must reproduce pad_bekker_p0.json bit for bit.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import run_pad_bekker_p0 as p0  # noqa: E402

SETS_PATH = ROOT / "02_params" / "scm_soil_sets.json"
OLD = ROOT / "06_analysis" / "00_dynamics" / "pad_bekker_p0.json"
OUT = ROOT / "06_analysis" / "00_dynamics" / "pad_bekker_p0_soilsets.json"
CACHE = None
OLD_NAME = {"J1": "heavy_clay_25", "J2": "lean_clay_22", "S1": "LETE_sand"}


def soil_cases():
    d = json.loads(SETS_PATH.read_text(encoding="utf-8"))
    cases = {}
    for key, s in d["sets"].items():
        c = s["chrono"]
        cases[key] = dict(n=c["n"], kc=c["Kc"], kphi=c["Kphi"], c=c["cohesion"], phi=c["friction"], K=c["elastic_K"])
    g = cases["G1"]
    for kphi, K in d["sets"]["G1"]["sensitivity"]["Kphi_K_pairs_Pa_m"]:
        cases[f"G1_kphi{kphi:.0e}_K{K:.1e}"] = {**g, "kphi": kphi, "K": K}
    for K in d["sets"]["G1"]["sensitivity"]["K_Pa_m"]:
        cases[f"G1_K{K:.1e}"] = {**g, "K": K}
    cases["S1_K6e7"] = {**cases["S1"], "K": 6e7}
    return cases, d


def _setup(key, s):
    name = OLD_NAME.get(key, key)
    p0.SOILS[name] = dict(n=s["n"], kc=s["kc"], kphi=s["kphi"], c=s["c"], phi=s["phi"], role=key, src="scm_soil_sets")
    p0.K_ELASTIC = s["K"]
    return name


def _job(args):
    key, s, variant, mode, e_final = args
    f = None
    if CACHE is not None:
        f = Path(CACHE) / f"{key}_{variant}_{mode}.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
    if key == "rigid":
        name = "rigid"
    else:
        name = _setup(key, s)
    out = p0.run_path("top", variant, name, mode=mode, e_final=None if e_final is None else np.array(e_final))
    out["set"] = key
    if f is not None:
        f.write_text(json.dumps(out, default=float), encoding="utf-8")
    return out


def _init(cache):
    global CACHE
    CACHE = cache


def summary(o, W):
    F = np.array(o["F_contact_final"])
    return {
        "t_done_s": o["t_done"], "t_crawler_off_s": o["t_crawler_off"],
        "clear_est_final_mm": o["clear_est_final"] * 1e3, "clear_true_final_mm": o["clear_orig_final"] * 1e3,
        "clear_overestimate_mm": (o["clear_est_final"] - o["clear_orig_final"]) * 1e3,
        "crawler_share_final": o["F_crawler_final"] / W,
        "sumFcyl_over_Wcyl_final": o["sumFcyl_over_Wcyl_final"],
        "att_max_after_crawler_off_deg": o["att_max_after_crawler_off_deg"] if o["t_crawler_off"] is not None else None,
        "min_Fcyl_minus_Fmin_kN": None if o["min_Fcyl_margin_after_crawler_off"] is None else o["min_Fcyl_margin_after_crawler_off"] / 1e3,
        "max_sink_rate_mm_s": max(o["max_sink_rate_mm_s"]), "e_max_mm": max(o["e_final"]) * 1e3,
        "min_remaining_to_0.6848_mm": min(o["remaining_to_end_margin_m"]) * 1e3,
        "s_pad_final_mm": [x * 1e3 for x in o["s_pad_final"]], "F_contact_final_kN": (F / 1e3).tolist(),
        "pitch_final_deg": o["pitch_final_deg"], "roll_final_deg": o["roll_final_deg"],
        "newton_it_max": o["newton_it_max"], "n_lsq_fallback": o["n_lsq_fallback"],
        "max_resid_fallback_W": o["max_resid_fallback"], "stroke_sensor_end_hit": o["stroke_sensor_end_hit"]}


def main():
    t0 = time.perf_counter()
    cases, sets = soil_cases()
    W = p0.Model("top", "B", "rigid").W
    jobs = [("rigid", None, "B", "closed", None)]
    nominal = ("J1", "J2", "G1", "S1")
    for k in cases:
        for v in ("A", "B"):
            jobs.append((k, cases[k], v, "closed", None))
            jobs.append((k, cases[k], v, "closed_true", None))
    jobs.sort(key=lambda j: 0 if j[0] in ("J1", "J2") else 1)
    with ProcessPoolExecutor(max_workers=14, initializer=_init, initargs=(CACHE,)) as ex:
        out = list(ex.map(_job, jobs))
    res_c = {f"{o['set']}|{o['variant']}|{o['mode']}": o for o in out}
    e_rigid = res_c["rigid|B|closed"]["e_final"]
    jobs2 = [(k, cases[k], v, "open", e_rigid) for k in nominal for v in ("A", "B")]
    with ProcessPoolExecutor(max_workers=8, initializer=_init, initargs=(CACHE,)) as ex:
        out2 = list(ex.map(_job, jobs2))
    for o in out2:
        res_c[f"{o['set']}|{o['variant']}|open"] = o

    # static monotone end states (control independent) for the nominal sets
    mono = {}
    for k in nominal:
        name = _setup(k, cases[k])
        with np.errstate(divide="ignore"):
            mono[k] = {v: p0.final_state_monotone("top", v, name) for v in ("A", "B")}
        if cases[k]["c"] == 0.0:          # undrained check undefined for c = 0 (G1)
            for v in ("A", "B"):
                mono[k][v]["q_ult_undrained_kPa"] = None
                mono[k][v]["p_over_qult_undrained"] = None

    # regression vs pad_bekker_p0.json (same inputs for J1 / J2 / S1)
    old = json.loads(OLD.read_text(encoding="utf-8"))
    reg = {}
    keys = ("e_final", "s_pad_final", "F_contact_final", "pitch_final_deg", "roll_final_deg", "t_done",
            "clear_orig_final", "min_Fcyl_margin_after_crawler_off", "att_max_after_crawler_off_deg")
    for k, nm in OLD_NAME.items():
        for v in ("A", "B"):
            for mode, blk in (("closed", "paths_closed"), ("closed_true", "paths_closed_true_clearance"), ("open", "paths_open")):
                a, b = res_c[f"{k}|{v}|{mode}"], old[blk].get(f"{nm}|{v}|top")
                if b is None:
                    continue
                dmax = 0.0
                for kk in keys:
                    x, y = a[kk], b[kk]
                    if x is None or y is None:
                        dmax = max(dmax, 0.0 if x is y else math.inf)
                        continue
                    dmax = max(dmax, float(np.max(np.abs(np.atleast_1d(np.array(x, float)) - np.atleast_1d(np.array(y, float))))))
                reg[f"{k}|{v}|{mode}"] = dmax
    rigid_old = old["paths_closed"]["rigid|B|top"]["e_final"]
    reg["rigid|B|closed_e_final"] = float(np.max(np.abs(np.array(e_rigid) - np.array(rigid_old))))

    # type comparison (5.31.6 thresholds, load threshold 2 kN per 5.31.6 recommendation also recorded)
    comp = {}
    for k in cases:
        A1, B1 = res_c[f"{k}|A|closed"], res_c[f"{k}|B|closed"]
        A2, B2 = res_c[f"{k}|A|closed_true"], res_c[f"{k}|B|closed_true"]
        row = {"H1": {"A": summary(A1, W), "B": summary(B1, W)}, "H2": {"A": summary(A2, W), "B": summary(B2, W)}}
        if k in nominal:
            oA, oB = res_c[f"{k}|A|open"], res_c[f"{k}|B|open"]
            row["open_pitch_deg"] = {"A": oA["pitch_final_deg"], "B": oB["pitch_final_deg"]}
            row["open_roll_deg"] = {"A": oA["roll_final_deg"], "B": oB["roll_final_deg"]}
            row["open_crawler_share"] = {"A": oA["F_crawler_final"] / W, "B": oB["F_crawler_final"] / W}
        ex = {}
        ex["s_final_RL_H2"] = abs(A2["s_pad_final"][2] - B2["s_pad_final"][2]) > max(0.005, 0.1 * abs(B2["s_pad_final"][2]))
        ex["e_final_RL_H2"] = abs(A2["e_final"][2] - B2["e_final"][2]) > max(0.005, 0.1 * abs(B2["e_final"][2] - p0.E_OP[2]))
        aa, ab = A2["att_max_after_crawler_off_deg"], B2["att_max_after_crawler_off_deg"]
        ex["att_max_H2"] = abs(aa - ab) > 0.05
        if k in nominal:
            ex["open_pitch"] = abs(row["open_pitch_deg"]["A"] - row["open_pitch_deg"]["B"]) > 0.05
        tA, tB = A2["t_done"], B2["t_done"]
        ex["t_done_H2"] = None if (tA is None or tB is None) else abs(tA - tB) > 0.1 * tB
        ex = {kk: (None if vv is None else bool(vv)) for kk, vv in ex.items()}
        row["exceeds"] = ex
        row["type_dependent"] = any(v for v in ex.values() if v)
        comp[k] = row

    res = {"meta": {"script": "04_scripts/01_dynamics/run_pad_bekker_p0_soilsets.py",
                    "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    "model": "run_pad_bekker_p0.py (5.31.2), imported unchanged",
                    "model_sha256": hashlib.sha256((ROOT / "04_scripts/01_dynamics/run_pad_bekker_p0.py").read_bytes()).hexdigest(),
                    "soil_sets": {"path": "02_params/scm_soil_sets.json", "sha256": hashlib.sha256(SETS_PATH.read_bytes()).hexdigest()},
                    "level": "top only (levels identical in this model, 5.31.1)", "weight_N": W,
                    "frames": "body x fwd, y left, z up; pitch > 0 nose down; roll > 0 left up",
                    "damping_R": "not used (quasi-static)", "runtime_s": None},
           "cases": cases, "regression_vs_pad_bekker_p0_maxabs": reg, "final_monotone": mono, "comparison": comp,
           "paths": {k: v for k, v in res_c.items()}}
    res["meta"]["runtime_s"] = time.perf_counter() - t0
    OUT.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("regression", json.dumps(reg), flush=True)
    print("runtime", res["meta"]["runtime_s"], "wrote", OUT, flush=True)


if __name__ == "__main__":
    if "--cache" in sys.argv:
        CACHE = sys.argv[sys.argv.index("--cache") + 1]
        Path(CACHE).mkdir(parents=True, exist_ok=True)
    main()
