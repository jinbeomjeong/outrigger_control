"""Read-only check of the V15 re-judgement (dynamics_model.md 5.29.7, rev. 43).

Reads the two batch summaries and per-case judge.json / series.npz (no Chrono, no 03_src import):
  07_results/S8/v15_20261025_132215 (rod_side, 10 cases)
  07_results/S8/v15_20261025_142154 (head_only, 2 cases)
and writes 06_analysis/00_dynamics/s8/s8_v15_rejudge_check.json with
  - per-case check counts, failed rows, the A-1 / A-2 / L-1 values vs the 5.29.7 expectations,
  - the (b) record row residual_head_N FL decomposed into Delta G + Delta(p_r A_ann),
    with the FL rod pressure history (before window, during motion, after return).

Conventions: legs FL FR RL RR, compression +, F = rod axial force, f = seal friction,
G = F - f (two-sensor net reading), head-only reading H = G + p_r A_ann, p_r gauge [Pa].
Run: C:/ProgramData/miniforge3/envs/Chrono-dev/python.exe -I <this file>
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BATCHES = {
    "rod_side": ROOT / "07_results/S8/v15_20261025_132215",
    "head_only": ROOT / "07_results/S8/v15_20261025_142154",
}
OUT = ROOT / "06_analysis/00_dynamics/s8/s8_v15_rejudge_check.json"
LEGS = ("FL", "FR", "RL", "RR")
A_ANN = np.array([0.00376991118, 0.00376991118, 0.00314159265, 0.00314159265])  # YAML legs.*.cylinder
A_P = np.pi / 4 * np.array([0.13, 0.13, 0.11, 0.11]) ** 2


def window_mean(t, y, t0, t1):
    m = (t >= t0) & (t <= t1)
    return y[m].mean(axis=0)


def case_b_rod_pressure(case_dir: Path, jm: dict) -> dict:
    d = np.load(case_dir / "series.npz")
    t = d["t_s"]
    p_r = d["p_r_Pa"]
    G = d["Fp_N"]
    H = d["head_reading_N"]
    u = d["u_m_s"]
    lam = d["lam_m"]
    t0, t1 = jm["t_start_s"], jm["t_end_s"]
    pb = window_mean(t, p_r, t0 - 1.0, t0)
    pa = window_mean(t, p_r, t1 - 1.0, t1)
    Gb, Ga = window_mean(t, G, t0 - 1.0, t0), window_mean(t, G, t1 - 1.0, t1)
    Hb, Ha = window_mean(t, H, t0 - 1.0, t0), window_mean(t, H, t1 - 1.0, t1)
    ident = np.max(np.abs(H - (G + p_r * A_ANN)))
    moving = (t > t0) & (t < t1) & (np.abs(u[:, 0]) > 1e-6)
    # last FL motion sample and the rod pressure right after it
    idx = np.nonzero(np.abs(u[:, 0]) > 1e-6)[0]
    t_last_move = float(t[idx[-1]]) if idx.size else None
    after = t > (t_last_move if t_last_move is not None else t1)
    p_after_first = float(p_r[after][0, 0]) if np.any(after) else None
    ret = (t > t0) & (np.gradient(lam) < 0)
    return {
        "p_r_before_bar_g": (pb / 1e5).tolist(),
        "p_r_after_bar_g": (pa / 1e5).tolist(),
        "FL_p_r_while_moving_bar_g_min_max": [float(p_r[moving, 0].min() / 1e5),
                                              float(p_r[moving, 0].max() / 1e5)]
        if np.any(moving) else None,
        "FL_p_r_during_return_bar_g_mean": float(p_r[ret, 0].mean() / 1e5) if np.any(ret) else None,
        "FL_last_motion_t_s": t_last_move,
        "FL_p_r_first_sample_after_last_motion_bar_g": None if p_after_first is None
        else p_after_first / 1e5,
        "delta_G_N": (Ga - Gb).tolist(),
        "delta_head_N": (Ha - Hb).tolist(),
        "delta_pr_Aann_N": ((pa - pb) * A_ANN).tolist(),
        "head_minus_net_residual_N": ((Ha - Hb) - (Ga - Gb)).tolist(),
        "identity_max_abs_H_minus_G_prA_N": float(ident),
    }


def main() -> None:
    out: dict = {"conventions": __doc__.split("Conventions: ")[1].split("\nRun:")[0]}
    for variant, bdir in BATCHES.items():
        summ = json.loads((bdir / "v15_summary.json").read_text(encoding="utf-8"))
        bout: dict = {"summary_top_keys": [k for k in summ if k != "cases"]}
        for k in summ:
            if k not in ("cases",) and not isinstance(summ[k], (dict, list)):
                bout[k] = summ[k]
        if "summary" in summ:
            bout["summary"] = summ["summary"]
        tot_checks = tot_failed = 0
        cases = {}
        for cname in sorted(p.name for p in bdir.iterdir() if p.is_dir()):
            j = json.loads((bdir / cname / "judge.json").read_text(encoding="utf-8"))
            checks = j.get("checks", [])
            judged = [c for c in checks if c["passed"] is not None]
            failed = [c for c in judged if c["passed"] is False]
            tot_checks += len(judged)
            tot_failed += len(failed)
            rows = []
            for c in checks:
                rows.append([c["row"], c["name"], c["value"], c["reference"], c["passed"],
                             c.get("note", "")])
            cout = {"n_judged": len(judged), "n_failed": len(failed), "n_records": len(checks) - len(judged),
                    "judge_rule": j.get("judge_rule"), "rows": rows}
            led = j.get("ledger", {})
            cout["ledger"] = {k: led.get(k) for k in ("R_mech_end_over_D_f", "creation_rel_smooth",
                                                      "creation_rel_raw", "D_visc_J", "E_ref_J",
                                                      "check_1", "check_4", "judged")}
            if cname.startswith("V15b"):
                cout["rod_pressure"] = case_b_rod_pressure(bdir / cname, j["metrics"])
            cases[cname] = cout
        bout["cases"] = cases
        bout["count_case_level"] = {"judged": tot_checks, "failed": tot_failed}
        # batch-level checks (speed pairs etc.) if present
        for k in ("checks", "batch_checks", "speed_checks"):
            if k in summ:
                bc = summ[k]
                bout[k] = bc
        out[variant] = bout
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")

    # console digest
    for variant in BATCHES:
        b = out[variant]
        print(f"== {variant}: top keys {b['summary_top_keys']}, case-level {b['count_case_level']}")
        if "summary" in b:
            print("   summary:", b["summary"])
        for cname, c in b["cases"].items():
            print(f"-- {cname}: judged {c['n_judged']} failed {c['n_failed']} records {c['n_records']}"
                  f" | ledger R_mech/D_f {c['ledger']['R_mech_end_over_D_f']}")
            for r in c["rows"]:
                v = r[2]
                if isinstance(v, float):
                    v = round(v, 4)
                elif isinstance(v, list):
                    v = [round(x, 3) if isinstance(x, float) else x for x in v]
                elif isinstance(v, dict):
                    v = {k: round(x, 3) if isinstance(x, float) else x for k, x in v.items()}
                print(f"   [{r[4]}] {r[0]} | {r[1]} | {v} | ref {r[3]} | {r[5]}")
            if "rod_pressure" in c:
                rp = c["rod_pressure"]
                print("   p_r before/after [bar g]:", np.round(rp["p_r_before_bar_g"], 2),
                      np.round(rp["p_r_after_bar_g"], 2))
                print("   FL moving p_r min/max:", rp["FL_p_r_while_moving_bar_g_min_max"],
                      " return mean:", rp["FL_p_r_during_return_bar_g_mean"],
                      " first after last motion:", rp["FL_p_r_first_sample_after_last_motion_bar_g"],
                      " t_last", rp["FL_last_motion_t_s"])
                print("   dG:", np.round(rp["delta_G_N"], 1), " dH:", np.round(rp["delta_head_N"], 1),
                      " d(p_r A):", np.round(rp["delta_pr_Aann_N"], 1),
                      " identity:", rp["identity_max_abs_H_minus_G_prA_N"])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
