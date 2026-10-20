"""Independent reference responses for the L2 hydraulic leg model (spec 6) and the cross check
Python spec implementation <-> Hopsan 2.24.4 (+ analytic values from linearize.py).

Stages (python -I run_l2_reference.py <cache_dir> [stage ...]; default all):
  py     Python spec implementation, flipped topology, Hopsan force convention, dt 1e-5 s, all scenarios
  hop    Hopsan, ts 1e-5 s and 5e-6 s (convergence), all scenarios
  conv   Python dt 5e-6 s for S1, S3, S4, S2b (convergence)
  spec1  Python only: physical topology (gauge force, Chrono intent), all scenarios
  spec2  merged L2b-NSC form, hook lag study (dt 1e-4 / 5e-5, lag 0 / 1 / 1+predictor)
  spec3  seal friction sweep F_s 0 / 2 / 5 / 12 kN (S1, S5)
  spec4  beta and air sensitivity, damping sensitivity of the D2 peak
  spec5  seal friction inside the discrete law (merged / physical, hook lag), counterbalance capacity
  report metrics, comparison verdicts, JSON 06_analysis/03_hydraulic/l2_reference_responses.json and figures
Each run is cached as <cache_dir>/<key>.npz so stages can be repeated cheaply.
Run on the E-cores (logical 16-27) with below-normal priority; hopsancli inherits the affinity.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import l2_params as lp  # noqa: E402
import scenarios as sc  # noqa: E402
import single_leg as sl  # noqa: E402

OUT_JSON = lp.OUT_DIR / "l2_reference_responses.json"
FIG_DIR = lp.OUT_DIR
STEP_SCEN = ("S1", "S1f", "S3", "S4", "S4p")
KEYS = ("t", "s", "v", "p_A_g", "p_B_g", "F_g", "F_sensor", "xM", "q_relief", "q_cb", "q_rod", "F_fric", "z")


# ---------------------------------------------------------------------------------------------
# runners with cache
# ---------------------------------------------------------------------------------------------


def _save(cache: Path, key: str, rec: dict, meta: dict) -> None:
    arrs = {k: np.asarray(v) for k, v in rec.items() if isinstance(v, np.ndarray)}
    np.savez_compressed(cache / f"{key}.npz", **arrs)
    (cache / f"{key}.json").write_text(json.dumps(meta, default=str), encoding="utf-8")


def load(cache: Path, key: str) -> tuple[dict, dict] | None:
    f = cache / f"{key}.npz"
    if not f.exists():
        return None
    d = dict(np.load(f))
    meta = json.loads((cache / f"{key}.json").read_text(encoding="utf-8"))
    return d, meta


def py_run(cache: Path, name: str, key: str, topology: str = "flipped", dt: float = 1e-5, lag: int = 0,
           predict: bool = False, hopsan_conv: bool = True, beta: float = 1.0e9, F_s: float | None = None,
           air: float = 0.0, c_scale: float = 1.0, force: bool = False, **prm_kw) -> tuple[dict, dict]:
    hit = None if force else load(cache, key)
    if hit:
        return hit
    _, c0 = lp.build()
    sch, t_end, o = sc.make(name, c0)
    Fs = o["F_s"] if F_s is None else F_s
    kser = math.inf
    if topology == "merged":
        kser = c0["k_g"]
    prm, c = lp.build(beta=beta, F_s=Fs, air=air, with_relief=o["with_relief"], with_cb=o["with_cb"],
                      hopsan_force_convention=hopsan_conv, k_series=kser, c_scale=c_scale, **prm_kw)
    b = sl.Bench(prm, c, topology=topology, M=o["M"], F_preload=o["F_preload"])
    t0 = time.perf_counter()
    rec = sl.run(b, sch, t_end, dt, lag=lag, predict=predict, out_dt=max(1e-4, dt))
    wall = time.perf_counter() - t0
    meta = {"tool": "python", "scenario": name, "topology": topology, "dt": dt, "lag": lag, "predict": predict,
            "hopsan_force_convention": hopsan_conv, "beta": beta, "F_s": Fs, "air": air, "c_scale": c_scale,
            "prm_kw": prm_kw, "wall_s": round(wall, 2), "diverged_at_s": rec.get("diverged_at_s"),
            "c_h_locked": prm.c_h_locked_N_s_m, "c_h_moving": prm.c_h_moving_N_s_m}
    rec = {k: v for k, v in rec.items() if isinstance(v, np.ndarray)}
    _save(cache, key, rec, meta)
    print(f"  py {key}: {wall:.1f} s", flush=True)
    return rec, meta


def hop_run(cache: Path, name: str, key: str, ts: float = 1e-5, F_s: float | None = None,
            force: bool = False) -> tuple[dict, dict]:
    hit = None if force else load(cache, key)
    if hit:
        return hit
    import hopsan_single_leg as hs

    r = hs.run_model(name, cache / "hopsan_work", ts=ts, F_s=F_s, tag=f"_{ts:g}")
    info = r.pop("info")
    rec = {k: v for k, v in r.items()}
    rec["xM"] = rec.pop("xM_raw")
    rec["vM"] = rec.pop("vM_raw")
    _, c = lp.build()
    rec["F_sensor"] = rec["p_A_g"] * c["A_A"]
    meta = {"tool": "hopsan", "scenario": name, **info}
    _save(cache, key, rec, meta)
    print(f"  hop {key}: {info['wall_s']} s", flush=True)
    return rec, meta


# ---------------------------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------------------------


def _mean(t, y, a, b):
    m = (t >= a) & (t <= b)
    return float(np.mean(y[m]))


def metrics(name: str, r: dict, c: dict) -> dict:
    t = r["t"]
    pA = r["p_A_g"] / 1e5
    s = r["s"]
    out: dict = {}
    if name in STEP_SCEN:
        out.update({f"pA_{k}": v for k, v in sl.step_metrics(t, pA, 0.1).items()})
        out["ds_final_mm"] = (_mean(t, s, t[-1] - 0.2, t[-1]) - s[0]) * 1e3
        out["pA_rise_bar"] = out["pA_peak"] - out["pA_initial"]
        out["pB_min_bar_g"] = float(np.min(r["p_B_g"])) / 1e5
        if "q_cb" in r and np.any(r["q_cb"]):
            dt = np.diff(t)
            out["cb_relieved_L"] = float(np.sum(0.5 * (r["q_cb"][1:] + r["q_cb"][:-1]) * dt)) * 1e3
    elif name in ("S2", "S2r"):
        out["v_hold_mm_s"] = _mean(t, r["v"], 1.2, 2.5) * 1e3
        out["pA_hold_bar"] = _mean(t, pA, 1.2, 2.5)
        out["pB_hold_bar"] = _mean(t, r["p_B_g"] / 1e5, 1.2, 2.5)
        w = (t >= 2.6) & (t <= 3.9)
        out["pA_after_stop_max_bar"] = float(np.max(pA[w]))
        out["pA_after_stop_min_bar"] = float(np.min(pA[w]))
        out["pA_final_bar"] = _mean(t, pA, t[-1] - 0.1, t[-1])
        out["ds_total_mm"] = (s[-1] - s[0]) * 1e3
        out["ds_after_ramp_end_mm"] = (s[-1] - float(np.interp(2.7, t, s))) * 1e3
        out["pA_initial_bar"] = float(pA[0])
    elif name == "S2b":
        out["pA_max_bar"] = float(np.max(pA))
        idx = np.where(pA >= 200.0)[0]
        out["t_reach_200bar_s"] = float(t[idx[0]]) if idx.size else float("nan")
        out["pA_final_bar"] = _mean(t, pA, t[-1] - 0.2, t[-1])
        out["ds_total_mm"] = (s[-1] - s[0]) * 1e3
        out["F_sat_kN"] = out["pA_final_bar"] * 1e5 * c["A_A"] / 1e3
    elif name == "S5":
        dF_true = r["F_g"] - r["F_g"][0]
        dF_sens = r["F_sensor"] - r["F_sensor"][0]
        err = dF_true - dF_sens
        out["max_abs_reading_error_kN"] = float(np.max(np.abs(err))) / 1e3
        out["residual_reading_error_end_kN"] = float(np.mean(err[t > t[-1] - 0.3])) / 1e3
        out["ds_end_mm"] = (s[-1] - s[0]) * 1e3
    return out


TRANSIENT = ("peak", "rise", "overshoot", "f_damped", "zeta", "settle", "after_stop", "t_reach", "t_peak",
             "max_abs", "min", "relieved")


def compare(a: dict, b: dict) -> dict:
    """a = candidate (Python), b = reference (Hopsan). Relative differences and the class of each metric."""
    rows = {}
    for k, vb in b.items():
        va = a.get(k)
        if va is None or not isinstance(vb, float) or not math.isfinite(vb) or not math.isfinite(va):
            continue
        cls = "transient" if any(x in k for x in TRANSIENT) else "steady"
        denom = abs(vb) if abs(vb) > 1e-9 else 1.0
        rel = abs(va - vb) / denom
        if k in ("pA_initial", "pA_peak", "pA_final", "pA_hold_bar", "pA_final_bar", "pA_after_stop_max_bar",
                 "pA_after_stop_min_bar", "pA_max_bar", "pA_initial_bar"):
            # pressures relative to their own level are lenient: also give the change-based value
            pass
        if k in ("pA_settle_2pct_s", "pA_n_peaks", "pB_min_bar_g", "pB_hold_bar", "ds_after_ramp_end_mm",
                 "pA_t_peak"):
            cls = "info"
        if k in ("pA_zeta_logdec",):
            cls = "transient"
        lim = (0.01, 0.05) if cls == "steady" else (0.05, 0.10)
        verdict = "info" if cls == "info" else ("match" if rel <= lim[0] else ("allowed" if rel <= lim[1] else "fail"))
        rows[k] = {"python": va, "hopsan": vb, "rel_diff": rel, "class": cls, "verdict": verdict}
    return rows


def overall(rows: dict) -> str:
    v = [r["verdict"] for r in rows.values() if r["verdict"] != "info"]
    if any(x == "fail" for x in v):
        return "불일치"
    if all(x == "match" for x in v):
        return "일치"
    return "허용 일치"


# ---------------------------------------------------------------------------------------------
# stages
# ---------------------------------------------------------------------------------------------


def stage_py(cache: Path) -> None:
    for nm in sc.ALL:
        py_run(cache, nm, f"py_{nm}")


def stage_hop(cache: Path) -> None:
    for nm in sc.ALL:
        hop_run(cache, nm, f"hop_{nm}", ts=1e-5)
        hop_run(cache, nm, f"hop_{nm}_ts5e-6", ts=5e-6)


def stage_conv(cache: Path) -> None:
    for nm in ("S1", "S3", "S4", "S2b"):
        py_run(cache, nm, f"py_{nm}_dt5e-6", dt=5e-6)


LAG_CASES = [(1e-4, 0, False), (1e-4, 1, False), (1e-4, 1, True), (5e-5, 0, False), (5e-5, 1, False),
             (5e-5, 1, True)]


def stage_spec1(cache: Path) -> None:
    for nm in ("S1", "S2", "S2r", "S2b", "S3", "S4", "S4p", "S5"):
        py_run(cache, nm, f"phys_{nm}", topology="physical", hopsan_conv=False)


def stage_spec2(cache: Path) -> None:
    for nm in ("S1", "S3"):
        py_run(cache, nm, f"merged_{nm}", topology="merged", hopsan_conv=False)
    for nm in ("S1", "S3"):
        for dt, lag, pred in LAG_CASES:
            py_run(cache, nm, f"lag_{nm}_dt{dt:g}_lag{lag}{'p' if pred else ''}", topology="physical",
                   hopsan_conv=False, dt=dt, lag=lag, predict=pred)
        for dt, lag, pred in LAG_CASES[:3]:
            py_run(cache, nm, f"lagm_{nm}_dt{dt:g}_lag{lag}{'p' if pred else ''}", topology="merged",
                   hopsan_conv=False, dt=dt, lag=lag, predict=pred)


def stage_spec3(cache: Path) -> None:
    for Fs in (0.0, 2.0e3, 5.0e3, 12.0e3):
        py_run(cache, "S5", f"fric_S5_Fs{int(Fs)}", topology="physical", hopsan_conv=False, F_s=Fs)
        py_run(cache, "S1", f"fric_S1_Fs{int(Fs)}", topology="physical", hopsan_conv=False, F_s=Fs)


FRIC_CASES = [  # (key, topology, dt, lag, predict, F_s, sigma0, sigma1)
    ("frm_Fs5k_ref", "merged", 1e-5, 0, False, 5e3, None, 0.0),
    ("frm_Fs5k_dt1e-4_lag0", "merged", 1e-4, 0, False, 5e3, None, 0.0),
    ("frm_Fs5k_dt1e-4_lag1", "merged", 1e-4, 1, False, 5e3, None, 0.0),
    ("frm_Fs5k_dt1e-4_lag1p", "merged", 1e-4, 1, True, 5e3, None, 0.0),
    ("frm_Fs12k_ref", "merged", 1e-5, 0, False, 12e3, None, 0.0),
    ("frm_Fs12k_dt1e-4_lag1", "merged", 1e-4, 1, False, 12e3, None, 0.0),
    ("frm_Fs12k_dt1e-4_lag1p", "merged", 1e-4, 1, True, 12e3, None, 0.0),
    ("frp_Fs5k_s1e10_dt1e-4_lag1", "physical", 1e-4, 1, False, 5e3, None, 0.0),
    ("frp_Fs5k_s1e10_dt5e-5_lag1p", "physical", 5e-5, 1, True, 5e3, None, 0.0),
    ("frp_Fs5k_s2e8_ref", "physical", 1e-5, 0, False, 5e3, 2e8, 1.3e5),
    ("frp_Fs5k_s2e8_dt1e-4_lag1", "physical", 1e-4, 1, False, 5e3, 2e8, 1.3e5),
    ("frp_Fs5k_s2e8_dt1e-4_lag1p", "physical", 1e-4, 1, True, 5e3, 2e8, 1.3e5),
    ("frp_Fs5k_s2e8_dt5e-5_lag1p", "physical", 5e-5, 1, True, 5e3, 2e8, 1.3e5),
]
CB_CASES = [  # (key, q at 20 bar override [m^3/s], q_nom [m^3/s], tau [s])
    ("cb_base", None, 1.0e-3, None),
    ("cb_large", 120.0e-3 / 60.0, 4.0e-3, 0.005),
    ("cb_ideal", 600.0e-3 / 60.0, 2.0e-2, 0.001),
]


def stage_spec5(cache: Path) -> None:
    for key, topo, dt, lag, pred, Fs, s0, s1 in FRIC_CASES:
        py_run(cache, "S1", key, topology=topo, hopsan_conv=False, dt=dt, lag=lag, predict=pred, F_s=Fs,
               sigma0=s0, sigma1=s1)
    for key, qo, qn, tau in CB_CASES:
        py_run(cache, "S4", key, topology="physical", hopsan_conv=False, cb_q_override=qo, cb_q_nom=qn, cb_tau=tau)


def stage_spec4(cache: Path) -> None:
    for beta in (0.69e9, 1.6e9):
        py_run(cache, "S1", f"beta_S1_{beta:g}", topology="physical", hopsan_conv=False, beta=beta)
        py_run(cache, "S3", f"beta_S3_{beta:g}", topology="physical", hopsan_conv=False, beta=beta)
    for air in (0.005, 0.02):
        py_run(cache, "S1", f"air_S1_{air:g}", topology="physical", hopsan_conv=False, air=air)
        py_run(cache, "S3", f"air_S3_{air:g}", topology="physical", hopsan_conv=False, air=air)
    for zs in (0.01 / 0.03, 0.10 / 0.03):
        py_run(cache, "S3", f"zeta_S3_{zs:.3f}", topology="physical", hopsan_conv=False, c_scale=zs)
        py_run(cache, "S4", f"zeta_S4_{zs:.3f}", topology="physical", hopsan_conv=False, c_scale=zs)


# ---------------------------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------------------------


def _clean(x):
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (np.floating, float)):
        x = float(x)
        return None if not math.isfinite(x) else float(f"{x:.6g}")
    if isinstance(x, np.integer):
        return int(x)
    return x


def stage_report(cache: Path) -> dict:
    _, c = lp.build()
    res: dict = {"meta": {
        "script": "04_scripts/04_hydraulic/run_l2_reference.py", "date": "2026-10-20",
        "env": "conda hydraulics-dev (Python 3.13), Hopsan 2.24.4 hopsancli; E-cores 16-27, below normal",
        "pressure": "bar gauge (p_atm = 1e5 Pa); Hopsan absolute converted",
        "cross_check_convention": "flipped topology + Hopsan force convention F = A1 p1_abs - A2 p2_abs "
                                  "(physical gauge force differs by A_rod p_atm = 0.95 kN)",
        "criteria": {"steady": "match <= 1 %, allowed <= 5 %", "transient": "match <= 5 %, allowed <= 10 %"},
        "cache_dir": str(cache)}}
    cross = {}
    for nm in sc.ALL:
        p = load(cache, f"py_{nm}")
        h = load(cache, f"hop_{nm}")
        h2 = load(cache, f"hop_{nm}_ts5e-6")
        if not (p and h):
            continue
        mp, mh = metrics(nm, p[0], c), metrics(nm, h[0], c)
        entry = {"python": mp, "hopsan": mh, "compare": compare(mp, mh)}
        entry["verdict"] = overall(entry["compare"])
        if h2:
            mh2 = metrics(nm, h2[0], c)
            entry["hopsan_ts5e-6"] = mh2
            entry["hopsan_step_convergence"] = compare(mh2, mh)
        p2 = load(cache, f"py_{nm}_dt5e-6")
        if p2:
            mp2 = metrics(nm, p2[0], c)
            entry["python_dt5e-6"] = mp2
            entry["python_step_convergence"] = compare(mp2, mp)
        entry["wall_s"] = {"python": p[1].get("wall_s"), "hopsan": h[1].get("wall_s")}
        cross[nm] = entry
    res["cross_check"] = cross

    # analytic vs simulation (hydraulic natural frequency, static rise)
    lin = json.loads((lp.OUT_DIR / "l2_linear_plant.json").read_text(encoding="utf-8"))
    info = lin["B_single_leg"]["FL_top_locked"]["info"]
    an = {"f_h_analytic_Hz": info["f_h_analytic_Hz"], "zeta_analytic": info["zeta_analytic"],
          "f_d_analytic_Hz": info["f_h_analytic_Hz"] * math.sqrt(1 - info["zeta_analytic"] ** 2),
          "dpA_static_S1_bar": 20.0e3 / c["A_A"] / 1e5, "dpA_static_S3_bar": 125.0e3 / c["A_A"] / 1e5}
    for nm in ("S1", "S3"):
        for tool in ("py", "hop", "phys"):
            r = load(cache, f"{tool}_{nm}")
            if not r:
                continue
            m = metrics(nm, r[0], c)
            an[f"{tool}_{nm}_f_d_Hz"] = m.get("pA_f_damped_Hz")
            an[f"{tool}_{nm}_zeta"] = m.get("pA_zeta_logdec")
            an[f"{tool}_{nm}_dpA_final_bar"] = m["pA_final"] - m["pA_initial"]
    res["analytic_vs_sim"] = an

    # spec-mode results (physical topology, gauge force)
    spec = {}
    for nm in ("S1", "S2", "S2r", "S2b", "S3", "S4", "S4p", "S5"):
        r = load(cache, f"phys_{nm}")
        if r:
            spec[nm] = metrics(nm, r[0], c)
    for nm in ("S1", "S3"):
        r = load(cache, f"merged_{nm}")
        if r:
            spec[f"{nm}_merged_L2bNSC_form"] = metrics(nm, r[0], c)
    res["spec_mode_physical"] = spec

    lag = {}
    for nm in ("S1", "S3"):
        ref = load(cache, f"phys_{nm}")
        mref = metrics(nm, ref[0], c) if ref else {}
        rows = {}
        for topo in ("lag", "lagm"):
            for dt, lg, pred in (LAG_CASES if topo == "lag" else LAG_CASES[:3]):
                key = f"{topo}_{nm}_dt{dt:g}_lag{lg}{'p' if pred else ''}"
                r = load(cache, key)
                if not r:
                    continue
                m = metrics(nm, r[0], c) if not r[1].get("diverged_at_s") else {}
                row = {"diverged_at_s": r[1].get("diverged_at_s"), "wall_s": r[1].get("wall_s")}
                for k in ("pA_peak", "pA_final", "pA_f_damped_Hz", "pA_zeta_logdec"):
                    if k in m:
                        row[k] = m[k]
                        if k in mref and topo == "lag":
                            row[f"{k}_rel_to_dt1e-5"] = (m[k] - mref[k]) / mref[k]
                if topo == "lagm":
                    mm = load(cache, f"merged_{nm}")
                    if mm and m:
                        mr2 = metrics(nm, mm[0], c)
                        for k in ("pA_peak", "pA_f_damped_Hz", "pA_zeta_logdec"):
                            if k in m and k in mr2:
                                row[f"{k}_rel_to_merged_dt1e-5"] = (m[k] - mr2[k]) / mr2[k]
                rows[key] = row
        lag[nm] = {"reference_dt1e-5_lag0": mref, "cases": rows}
    res["hook_lag_study"] = lag

    sens = {}
    for key_prefix, nm in (("fric_S5_Fs", "S5"), ("fric_S1_Fs", "S1")):
        for Fs in (0, 2000, 5000, 12000):
            r = load(cache, f"{key_prefix}{Fs}")
            if r:
                sens[f"{nm}_Fs{Fs}"] = metrics(nm, r[0], c)
    for beta in (0.69e9, 1.6e9):
        for nm in ("S1", "S3"):
            r = load(cache, f"beta_{nm}_{beta:g}")
            if r:
                sens[f"{nm}_beta{beta / 1e9:.2f}"] = metrics(nm, r[0], c)
    for air in (0.005, 0.02):
        for nm in ("S1", "S3"):
            r = load(cache, f"air_{nm}_{air:g}")
            if r:
                sens[f"{nm}_air{air:g}"] = metrics(nm, r[0], c)
    for zs in (0.01 / 0.03, 0.10 / 0.03):
        for nm in ("S3", "S4"):
            r = load(cache, f"zeta_{nm}_{zs:.3f}")
            if r:
                sens[f"{nm}_zeta{0.03 * zs:.2f}"] = metrics(nm, r[0], c)
    res["sensitivity_physical"] = sens

    fr = {}
    for key, topo, dt, lag, pred, Fs, s0, s1 in FRIC_CASES:
        r = load(cache, key)
        if not r:
            continue
        row = {"topology": topo, "dt": dt, "lag": lag, "predict": pred, "F_s": Fs,
               "sigma0": s0 or lp.ASSUMPTIONS["seal_friction_sigma0_N_m"][0], "sigma1": s1,
               "diverged_at_s": r[1].get("diverged_at_s"), "wall_s": r[1].get("wall_s")}
        if not r[1].get("diverged_at_s"):
            m = metrics("S1", r[0], c)
            row.update({k: m.get(k) for k in ("pA_peak", "pA_final", "pA_rise_bar", "ds_final_mm")})
            row["pA_hf_rms_bar"] = float(np.std(np.diff(r[0]["p_A_g"] / 1e5)))
        fr[key] = row
    res["friction_discrete_study"] = fr
    cbr = {}
    for key, qo, qn, tau in CB_CASES:
        r = load(cache, key)
        if r:
            m = metrics("S4", r[0], c)
            cbr[key] = {"q_at_20bar_override_L_min": (qo or 20e-3 / 60) * 6e4, "q_nom_L_min_at_70bar": qn * 6e4,
                        "tau_s": tau or lp.ASSUMPTIONS["cb_tau_s"][0],
                        **{k: m.get(k) for k in ("pA_peak", "pA_final", "ds_final_mm", "cb_relieved_L")}}
    res["counterbalance_capacity_study"] = cbr
    res = _clean(res)
    OUT_JSON.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT_JSON}")
    figures(cache, c)
    return res


def figures(cache: Path, c: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    col_py, col_hop = "#1f5fa8", "#d1495b"
    fig, axes = plt.subplots(3, 3, figsize=(14, 10.5), constrained_layout=True)
    panels = [("S1", "p_A_g", 1e-5, "p_A [bar g]"), ("S1f", "p_A_g", 1e-5, "p_A [bar g]"),
              ("S2", "s", 1e3, "s [mm]"), ("S2r", "p_A_g", 1e-5, "p_A [bar g]"),
              ("S2b", "p_A_g", 1e-5, "p_A [bar g]"), ("S3", "p_A_g", 1e-5, "p_A [bar g]"),
              ("S4", "p_A_g", 1e-5, "p_A [bar g]"), ("S4p", "p_A_g", 1e-5, "p_A [bar g]"),
              ("S5", "F_sensor", 1e-3, "F_sensor = p_A A_A [kN]")]
    for ax, (nm, key, sc_, lab) in zip(axes.ravel(), panels, strict=True):
        p = load(cache, f"py_{nm}")
        h = load(cache, f"hop_{nm}")
        if h:
            ax.plot(h[0]["t"], h[0][key] * sc_, color=col_hop, lw=2.2, alpha=0.7, label="Hopsan 2.24.4 (ts 1e-5)")
        if p:
            ax.plot(p[0]["t"], p[0][key] * sc_, color=col_py, lw=1.0, label="Python spec (dt 1e-5)")
        if nm == "S5" and p:
            ax.plot(p[0]["t"], (p[0]["F_g"] - p[0]["F_g"][0] + p[0]["F_sensor"][0]) * sc_, color="#555555",
                    lw=0.8, ls="--", label="true leg load (Python)")
        if key == "p_A_g" and nm in ("S3", "S4", "S4p"):
            ax.axhline(350.0, color="#555555", lw=0.8, ls=":")
        if nm == "S2b":
            ax.axhline(210.0, color="#555555", lw=0.8, ls=":")
        ax.set_title(nm)
        ax.set_xlabel("t [s]")
        ax.set_ylabel(lab)
        ax.grid(alpha=0.3)
    axes[0, 0].legend(fontsize=8, frameon=False)
    axes[2, 2].legend(fontsize=7, frameon=False)
    fig.suptitle("L2 single leg (FL, top): Python spec implementation vs Hopsan "
                 "(flipped bench, Hopsan force convention)")
    fig.savefig(FIG_DIR / "l2_reference_responses.png", dpi=130)
    plt.close(fig)

    # hook-lag study
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), constrained_layout=True)
    for ax, nm in zip(axes, ("S1", "S3"), strict=True):
        ref = load(cache, f"phys_{nm}")
        if ref:
            ax.plot(ref[0]["t"], ref[0]["p_A_g"] / 1e5, color="#222222", lw=2.0, label="dt 1e-5, lag 0 (reference)")
        styles = {(1e-4, 0, False): ("#1f5fa8", "-"), (1e-4, 1, False): ("#d1495b", "-"),
                  (1e-4, 1, True): ("#2a9d8f", "--")}
        for (dt, lg, pred), (colr, ls) in styles.items():
            r = load(cache, f"lag_{nm}_dt{dt:g}_lag{lg}{'p' if pred else ''}")
            if r:
                ax.plot(r[0]["t"], r[0]["p_A_g"] / 1e5, color=colr, ls=ls, lw=1.0,
                        label=f"dt {dt:g}, lag {lg}{' + predictor' if pred else ''}")
        ax.set_xlim(0.05, 1.5)
        ax.set_title(f"{nm}: physical topology, hook lag")
        ax.set_xlabel("t [s]")
        ax.set_ylabel("p_A [bar g]")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, frameon=False)
    fig.savefig(FIG_DIR / "l2_hook_lag_study.png", dpi=130)
    plt.close(fig)

    # friction: pressure reading vs true load
    fig, ax = plt.subplots(figsize=(7, 5), constrained_layout=True)
    for Fs, colr in ((0, "#222222"), (2000, "#1f5fa8"), (5000, "#2a9d8f"), (12000, "#d1495b")):
        r = load(cache, f"fric_S5_Fs{Fs}")
        if r:
            d = r[0]
            ax.plot((d["F_g"] - d["F_g"][0]) / 1e3, (d["F_sensor"] - d["F_sensor"][0]) / 1e3, color=colr, lw=1.2,
                    label=f"F_s = {Fs / 1e3:g} kN")
    ax.set_xlabel("true leg load change [kN]")
    ax.set_ylabel("pressure reading change p_A A_A [kN]")
    ax.set_title("S5 locked leg, slow load cycle (physical topology)")
    ax.grid(alpha=0.3)
    ax.legend(frameon=False)
    fig.savefig(FIG_DIR / "l2_friction_reading.png", dpi=130)
    plt.close(fig)


def main() -> None:
    cache = Path(sys.argv[1])
    cache.mkdir(parents=True, exist_ok=True)
    stages = sys.argv[2:] or ["py", "hop", "conv", "spec1", "spec2", "spec3", "spec4", "spec5", "report"]
    table = {"py": stage_py, "hop": stage_hop, "conv": stage_conv, "spec1": stage_spec1, "spec2": stage_spec2,
             "spec3": stage_spec3, "spec4": stage_spec4, "spec5": stage_spec5, "report": stage_report}
    for st in stages:
        t0 = time.perf_counter()
        print(f"stage {st}", flush=True)
        table[st](cache)
        print(f"stage {st} done in {time.perf_counter() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    main()
