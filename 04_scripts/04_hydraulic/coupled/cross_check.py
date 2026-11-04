"""Three-way comparison per scenario with xcheck.py compare, and the criteria V-2 / V-3 checks.

Sources: hand (hand/<name>.json, GAUGE), numpy (numpy/<name>.csv, GAUGE, xcheck kind om),
hopsan (hopsan/<name>.csv, ABSOLUTE, p_atm 1e5). Steady value = mean over the last
scenario.window seconds. Writes xcheck/<name>.{json,md}, cross_check_summary.json, v3_table.csv.

--v2b re-runs the dynamic model.py for all scenarios with output at every step and writes
v2b_summary.json and v2b_table.csv (criteria 6 V-2 (b), rev. 3).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

from params import LEGS, OUT_DIR, load_params  # noqa: E402
from scenarios import BY_NAME, SCENARIOS, Scenario  # noqa: E402

XCHECK = Path.home() / ".claude" / "tools" / "hydraulics" / "xcheck.py"
Q_FLOOR = 1e-6  # m3/s (0.06 L/min), floor of relative flow differences at zero flow
V_FLOOR = 1e-3  # m/s, floor for locked legs (ringing around zero)
P_FLOOR = 1e5  # Pa
TIE_R = 0.002  # r difference treated as a tie for the first slowed leg (criteria 6 V-3)
V3_DR_LIMIT = 0.02  # criteria 6 V-3, ASSUMPTION of the criteria
GRID_ETAS = (0.90, 0.85)  # criteria 6 V-3 load grid
T_SKIP = 0.02  # s, start of the gallery balance (criteria 6 V-2 b)
V2B_BALANCE_CM3 = 0.01  # criteria 6 V-2 b, ASSUMPTION of the criteria
V2B_EXCESS = 1e-4  # criteria 6 V-2 b, mean sum Q_i / Q_sup - 1 over the steady window
V2B_SPEED = 0.002  # criteria 6 V-2 b, fraction of v_max
V2B_DT = 5e-5  # s, the integration step of run_numpy.py
V2B_DT_FINE = 1e-5  # s, step of the short run that resolves the first 20 ms


def mapping(sc: Scenario) -> dict:
    win = [sc.t_end - sc.window, sc.t_end]
    q = []
    for leg in LEGS:
        for name, hand, npy, hop, unit, floor, scale in (
            (f"v_{leg}", f"v_{leg}", f"v_{leg}", f"Mass{leg}#P2#Velocity", "m/s", V_FLOOR, 1.0),
            (f"Q_{leg}", f"Q_in_{leg}", f"Q_in_{leg}", f"Spool{leg}#PA#Flow", "m^3/s", Q_FLOOR, 1.0),
            (f"p_h_{leg}", f"p_h_{leg}", f"p_h_{leg}", f"Spool{leg}#PA#Pressure", "Pa", P_FLOOR, 1.0),
            (f"p_r_{leg}", f"p_r_{leg}", f"p_r_{leg}", f"Spool{leg}#PB#Pressure", "Pa", P_FLOOR, 1.0),
        ):
            vars_ = {"hand": hand, "numpy": {"var": npy, "unit": unit}}
            if sc.hopsan:
                vars_["hopsan"] = {"var": hop, "unit": unit, "scale": scale}
            q.append({"name": name, "metric": "mean", "window": win, "floor": floor, "unit": unit, "vars": vars_,
                      "kind": "pressure" if unit == "Pa" else "flow"})
    for name, npy, hop, unit, floor in (("p_P", "p_P", "Pump#P2#Pressure", "Pa", P_FLOOR),
                                        ("Q_byp", "Q_byp", "Unloader#P2#Flow", "m^3/s", Q_FLOOR)):
        vars_ = {"hand": name, "numpy": {"var": npy, "unit": unit}}
        if sc.hopsan:
            vars_["hopsan"] = {"var": hop, "unit": unit}
        q.append({"name": name, "metric": "mean", "window": win, "floor": floor, "unit": unit, "vars": vars_,
                  "kind": "pressure" if unit == "Pa" else "flow"})
    return {"quantities": q}


def run_xcheck(sc: Scenario, out_dir: Path) -> dict:
    map_path = out_dir / f"{sc.name}_map.json"
    map_path.write_text(json.dumps(mapping(sc), indent=0), encoding="utf-8")
    cmd = [sys.executable, "-I", str(XCHECK), "compare", "--map", str(map_path),
           "--source", f"hand={OUT_DIR / 'hand' / (sc.name + '.json')}",
           "--source", f"numpy={OUT_DIR / 'numpy' / (sc.name + '.csv')}",
           "--kind", "hand=hand", "--kind", "numpy=om", "--pressure-ref", "numpy=gauge",
           "--out", str(out_dir / f"{sc.name}.json"), "--warnings-ok"]
    if sc.hopsan:
        cmd += ["--source", f"hopsan={OUT_DIR / 'hopsan' / (sc.name + '.csv')}", "--kind", "hopsan=hopsan"]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, encoding="utf-8", errors="replace", env=env)
    lines = proc.stdout.strip().splitlines()
    if not lines:
        raise RuntimeError(f"{sc.name}: xcheck no output: {proc.stderr[-800:]}")
    tail = json.loads(lines[-1])
    tail["exit"] = proc.returncode
    return tail


def read_hopsan(path: Path) -> tuple[np.ndarray, dict]:
    cols = {}
    with open(path, newline="") as fh:
        for row in csv.reader(fh):
            if row:
                cols[row[0]] = np.array([float(x) for x in row[3:]])
    return cols.pop("Time"), cols


def read_numpy(path: Path) -> tuple[np.ndarray, dict]:
    with open(path, newline="") as fh:
        rows = list(csv.reader(fh))
    a = np.array([[float(x) for x in r] for r in rows[1:]])
    names = rows[0]
    return a[:, 0], {n: a[:, j] for j, n in enumerate(names) if j > 0}


def moving_ratio(t: np.ndarray, v: np.ndarray, u: np.ndarray, v_max: float) -> np.ndarray:
    """r = 1 s moving mean of v / 1 s moving mean of u, NaN where mean u < 0.1 v_max (criteria sec. 1)."""
    dt = float(np.median(np.diff(t)))
    n = max(1, int(round(1.0 / dt)))
    ker = np.ones(n) / n
    vm, um = np.convolve(v, ker, "valid"), np.convolve(u, ker, "valid")
    with np.errstate(invalid="ignore", divide="ignore"):
        r = np.where(np.abs(um) >= 0.1 * v_max, vm / um, np.nan)
    return np.concatenate([np.full(n - 1, np.nan), r])


def v3_row(sc: Scenario, p) -> dict:
    """Steady r_i of numpy and Hopsan with the same command, first slowed leg, |dr|."""
    tn, n = read_numpy(OUT_DIR / "numpy" / f"{sc.name}.csv")
    th, h = read_hopsan(OUT_DIR / "hopsan" / f"{sc.name}.csv")
    u = np.array(sc.u) * p.v_max
    t0 = sc.t_end - sc.window
    rn, rh = [], []
    for i, leg in enumerate(LEGS):
        if u[i] == 0:
            rn.append(np.nan)
            rh.append(np.nan)
            continue
        rn.append(float(np.mean(n[f"v_{leg}"][tn >= t0]) / u[i]))
        rh.append(float(np.mean(h[f"Mass{leg}#P2#Velocity"][th >= t0]) / u[i]))
    rn_a, rh_a = np.array(rn), np.array(rh)

    def slowest(r: np.ndarray) -> list[str]:
        """Legs within 0.002 of the lowest r: FL and FR tie once the twist has settled."""
        return [leg for i, leg in enumerate(LEGS) if np.isfinite(r[i]) and r[i] <= np.nanmin(r) + TIE_R]

    def tie_margin(r: np.ndarray) -> float:
        """Distance of the leg nearest the tie limit; a small value means the set is close to changing."""
        return float(np.nanmin(np.abs(r - (np.nanmin(r) + TIE_R))))

    a, b = slowest(rn_a), slowest(rh_a)
    max_dr = float(np.nanmax(np.abs(rn_a - rh_a)))
    same = set(a) == set(b)
    return {"r_numpy": rn, "r_hopsan": rh, "max_abs_dr": max_dr,
            "first_slow_numpy": "+".join(a), "first_slow_hopsan": "+".join(b),
            "first_slow_same": same,  # criteria rev. 3: the two sets must be equal
            "first_slow_overlap_rule": bool(set(a) & set(b)),  # rule before rev. 3, comparison only
            "tie_margin_numpy": tie_margin(rn_a), "tie_margin_hopsan": tie_margin(rh_a),
            "on_grid": sc.eta_v in GRID_ETAS, "pass": bool(same and max_dr <= V3_DR_LIMIT)}


def v2_row(sc: Scenario, p) -> dict:
    """Original-criteria numbers of the numpy CSV (1 ms output): excess over the supply, speed error."""
    t, n = read_numpy(OUT_DIR / "numpy" / f"{sc.name}.csv")
    Q_sum = sum(n[f"Q_in_{leg}"] for leg in LEGS)
    Q_p = n["Q_pump"]
    area = np.where(np.array(sc.u) < 0, p.A_r, p.A_h)
    u = np.vstack([n[f"u_{leg}"] for leg in LEGS]).T * p.v_max
    dem = (np.abs(u) * area).sum(axis=1)
    settle = t >= sc.t_end - sc.window
    met = dem <= Q_p * (1 + 1e-6)
    v = np.vstack([n[f"v_{leg}"] for leg in LEGS]).T
    dev = np.abs(v.mean(axis=0, where=settle[:, None]) - u[-1])
    return {"max_excess_rel_steady": float((Q_sum[settle] / Q_p[settle] - 1).max()),
            "max_excess_rel_all": float((Q_sum / Q_p - 1).max()),
            "demand_met": bool(met[settle].all()),
            "max_speed_error_when_met_mm_s": float(dev.max() * 1e3) if met[settle].all() else None}


def balance_error_m3(t: np.ndarray, net_flow: np.ndarray, p_P: np.ndarray, p, t0: float = 0.0) -> np.ndarray:
    """Gallery balance from t0: trapezoid of (Q_sup - sum Q_i - Q_byp) minus (V_g / beta) dp_P [m3]."""
    m = t >= t0 - 1e-12
    integral = np.concatenate([[0.0], np.cumsum(0.5 * (net_flow[m][1:] + net_flow[m][:-1]) * np.diff(t[m]))])
    return integral - p.V_g / p.beta * (p_P[m] - p_P[m][0])


def v2b_case(name: str) -> dict:
    """Criteria 6 V-2 (b) of one scenario from a re-run of the current model.py, output at every step."""
    from dataclasses import replace

    from model import simulate

    p = load_params()
    sc = BY_NAME[name]
    res = simulate(p, sc, dt=V2B_DT, log_dt=V2B_DT)
    idx = {n: j for j, n in enumerate(res["names"])}
    t, a = res["time"], res["data"]

    def col(q: str) -> np.ndarray:
        return a[:, idx[q]]

    Q = np.column_stack([col(f"Q_in_{leg}") for leg in LEGS])
    Q_sum, Q_byp, Q_sup, p_P = Q.sum(axis=1), col("Q_byp"), col("Q_pump"), col("p_P")
    net = Q_sup - Q_sum - Q_byp
    u = np.column_stack([col(f"u_{leg}") for leg in LEGS]) * p.v_max
    v = np.column_stack([col(f"v_{leg}") for leg in LEGS])
    sign = np.array(sc.u)
    area = np.where(sign < 0, p.A_r, p.A_h)
    dem = (np.abs(u) * area).sum(axis=1)
    settle = t >= sc.t_end - sc.window
    active_area = float(area[sign != 0].sum())

    # (b1) balance after the first 20 ms, at the step output and at the 1 ms output
    every = int(round(1e-3 / V2B_DT))
    err = balance_error_m3(t, net, p_P, p, t0=T_SKIP)
    err_1ms = balance_error_m3(t[::every], net[::every], p_P[::every], p, t0=T_SKIP)
    # (b2) steady mean, (b3) speed error when the demand is met
    excess_mean = float((Q_sum[settle] / Q_sup[settle] - 1.0).mean())
    met = bool((dem[settle] <= Q_sup[settle] * (1 + 1e-6)).all())
    speed_err = float(np.abs(v[settle].mean(axis=0) - u[settle].mean(axis=0)).max() / p.v_max) if met else None
    # excess volume, record only: stored oil released by the gallery and the chambers
    over = np.maximum(Q_sum - Q_sup, 0.0)
    dt = np.diff(t)
    v_over_all = float((0.5 * (over[1:] + over[:-1]) * dt).sum())
    late = t[:-1] >= T_SKIP
    v_over_late = float((0.5 * (over[1:] + over[:-1]) * dt)[late].sum())

    # first 20 ms: the balance by output interval, and with a five times smaller integration step
    k20 = int(np.searchsorted(t, T_SKIP - 1e-12))
    first = {}
    for label, step in (("1ms", every), ("0.2ms", every // 5), ("0.05ms", 1)):
        first[label] = float(balance_error_m3(t[:k20 + 1:step], net[:k20 + 1:step], p_P[:k20 + 1:step], p)[-1] * 1e6)
    fine = simulate(p, replace(sc, t_end=2 * T_SKIP), dt=V2B_DT_FINE, log_dt=V2B_DT_FINE)
    ix = {n: j for j, n in enumerate(fine["names"])}
    f = fine["data"]
    net_f = f[:, ix["Q_pump"]] - f[:, [ix[f"Q_in_{leg}"] for leg in LEGS]].sum(axis=1) - f[:, ix["Q_byp"]]
    k_f = int(np.searchsorted(fine["time"], T_SKIP - 1e-12))
    first["0.01ms_dt1e-5"] = float(balance_error_m3(fine["time"][:k_f + 1], net_f[:k_f + 1], f[:k_f + 1, ix["p_P"]], p)[-1] * 1e6)

    # does the stored CSV (older than model.py and params.py) hold the same numbers?
    t_csv, n_csv = read_numpy(OUT_DIR / "numpy" / f"{name}.csv")
    stored_diff = {}
    for q in ("Q_byp", "p_P", *[f"v_{leg}" for leg in LEGS], *[f"Q_in_{leg}" for leg in LEGS]):
        ref = n_csv[q]
        new = np.interp(t_csv, t, col(q))
        stored_diff[q] = float(np.abs(new - ref).max() / max(np.abs(ref).max(), 1e-12))

    return {"name": name, "eta_v": sc.eta_v, "dt_s": V2B_DT, "wall_s": round(res["wall_s"], 1), "finite": bool(np.isfinite(a).all()),
            "balance_after_20ms_cm3": float(np.abs(err).max() * 1e6), "balance_after_20ms_1ms_output_cm3": float(np.abs(err_1ms).max() * 1e6),
            "excess_mean_steady": excess_mean, "demand_met": met, "speed_error_rel_vmax": speed_err,
            "excess_inst_max_rel_all": float((Q_sum / Q_sup - 1).max()), "excess_inst_max_rel_after_20ms": float((Q_sum / Q_sup - 1)[t >= T_SKIP].max()),
            "excess_inst_max_rel_steady": float((Q_sum[settle] / Q_sup[settle] - 1).max()),
            "excess_volume_all_cm3": v_over_all * 1e6, "excess_volume_after_20ms_cm3": v_over_late * 1e6,
            "excess_stroke_all_mm": v_over_all / active_area * 1e3, "excess_stroke_after_20ms_mm": v_over_late / active_area * 1e3,
            "Q_byp_t0_L_min": float(Q_byp[0] * 6e4), "Q_byp_t_dt_L_min": float(Q_byp[1] * 6e4),
            "first_20ms_balance_cm3": first, "stored_csv_max_rel_diff": max(stored_diff.values()),
            "pass": {"balance": bool(np.abs(err).max() * 1e6 <= V2B_BALANCE_CM3), "excess": excess_mean <= V2B_EXCESS,
                     "speed": speed_err is None or speed_err <= V2B_SPEED}}


def run_v2b(jobs: int) -> None:
    """Writes v2b_summary.json and v2b_table.csv, about 45 worker-minutes in total."""
    names = [sc.name for sc in SCENARIOS]
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        rows = list(ex.map(v2b_case, names))
    meta = {"model_py_sha256": sha256((HERE / "model.py").read_bytes()).hexdigest(),
            "params_py_sha256": sha256((HERE / "params.py").read_bytes()).hexdigest(),
            "limits": {"balance_cm3": V2B_BALANCE_CM3, "excess_mean": V2B_EXCESS, "speed_rel_vmax": V2B_SPEED, "t_skip_s": T_SKIP}}
    (OUT_DIR / "v2b_summary.json").write_text(json.dumps({"meta": meta, "rows": rows}, indent=1), encoding="utf-8")
    fields = ["name", "eta_v", "balance_after_20ms_cm3", "balance_after_20ms_1ms_output_cm3", "excess_mean_steady", "demand_met",
              "speed_error_rel_vmax", "excess_inst_max_rel_all", "excess_inst_max_rel_steady", "excess_volume_all_cm3",
              "excess_stroke_all_mm", "excess_volume_after_20ms_cm3", "excess_stroke_after_20ms_mm", "stored_csv_max_rel_diff"]
    with open(OUT_DIR / "v2b_table.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([*fields, "first20ms_1ms_cm3", "first20ms_0.2ms_cm3", "first20ms_0.05ms_cm3", "first20ms_0.01ms_cm3", "pass_balance", "pass_excess", "pass_speed"])
        for r in rows:
            w.writerow([r[k] for k in fields] + list(r["first_20ms_balance_cm3"].values()) + list(r["pass"].values()))
            print(r["name"], f"bal {r['balance_after_20ms_cm3']:.2e} (1ms {r['balance_after_20ms_1ms_output_cm3']:.2e}) cm3,",
                  f"mean {r['excess_mean_steady']:+.2e}, speed {r['speed_error_rel_vmax']}, stored {r['stored_csv_max_rel_diff']:.1e},",
                  f"Vex {r['excess_volume_all_cm3']:.3f} cm3 / {r['excess_stroke_all_mm']:.4f} mm,", r["first_20ms_balance_cm3"], r["pass"])


def write_v3_table(summary: dict) -> None:
    with open(OUT_DIR / "v3_table.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "on_grid", "first_slow_numpy", "first_slow_hopsan", "same_before_rev3_overlap", "same_rev3_equal_sets",
                    "max_abs_dr", "tie_margin_numpy", "tie_margin_hopsan", "pass", "r_numpy", "r_hopsan"])
        for name, row in summary.items():
            v3 = row.get("v3")
            if v3:
                w.writerow([name, v3["on_grid"], v3["first_slow_numpy"], v3["first_slow_hopsan"], v3["first_slow_overlap_rule"], v3["first_slow_same"],
                            v3["max_abs_dr"], v3["tie_margin_numpy"], v3["tie_margin_hopsan"], v3["pass"], v3["r_numpy"], v3["r_hopsan"]])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v2b", action="store_true", help="re-run model.py for the 32 scenarios and write the V-2 (b) table only")
    ap.add_argument("--jobs", type=int, default=6)
    args = ap.parse_args()
    if args.v2b:
        run_v2b(args.jobs)
        return
    p = load_params()
    out_dir = OUT_DIR / "xcheck"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    for sc in SCENARIOS:
        tail = run_xcheck(sc, out_dir)
        row = {"verdict": tail.get("verdict"), "exit": tail["exit"], "xcheck": str(out_dir / f"{sc.name}.json")}
        rep = json.loads((out_dir / f"{sc.name}.json").read_text(encoding="utf-8"))
        worst = sorted(rep["rows"], key=lambda r: r["rel"] / max(r["tol_allowed"], 1e-12), reverse=True)[:3]
        row["worst"] = [{k: r[k] for k in ("quantity", "ref", "other", "value_ref", "value_other", "unit", "rel", "verdict")}
                        for r in worst]
        row["warnings"] = rep.get("warnings", [])
        row["v2"] = v2_row(sc, p)
        if sc.hopsan:
            row["v3"] = v3_row(sc, p)
        summary[sc.name] = row
        v3 = row.get("v3", {})
        print(f"{sc.name:6s} {row['verdict']:10s} worst {worst[0]['quantity']:8s} {worst[0]['ref']}-{worst[0]['other']} {worst[0]['rel']*100:6.2f} % "
              f"| dr {v3.get('max_abs_dr', float('nan')):.4f} first {v3.get('first_slow_numpy')}/{v3.get('first_slow_hopsan')} "
              f"| V2 {row['v2']['max_excess_rel_steady']:+.2e} err {row['v2']['max_speed_error_when_met_mm_s']}")
    (OUT_DIR / "cross_check_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    write_v3_table(summary)


if __name__ == "__main__":
    main()
