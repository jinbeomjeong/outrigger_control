"""d08 (D-3): the post-event LEVEL tail, twist drift path.

Per 10 Hz period in the post-event LEVEL segment (the first LEVEL after the event time):
  * command u (T4h ``command_m_s``), its twist component ``nu^T u`` and support part;
  * executed oil-volume rate ``v_s = d s_ref / dt`` and piston rate ``v_x = dx / dt`` (plant);
    their twist components ``nu^T v``;
  * per leg: plant ``locked``, seal stick, the P1 fill ``line_fill_gate.x``;
  * twist load ``D = nu^T F`` (T4h ``lsb_ib_twist_load_N``) and its rate; the controller roll,
    pitch, integrals, completion flags, A_ib flag.
Window summaries (10 s windows): mean dD/dt, mean nu^T v_x, the ratio (effective twist
stiffness), the share of periods with a locked leg holding a nonzero command, the commanded
vs executed twist rate of that leg, and the attitude error.

``nu`` = controller ``C2Geometry.twist_vector`` (unit, A^T nu = 0, FL FR RL RR).

Usage: conda run -n dynamics-dev python -I -B d08_d3_tail_twist.py <d00 scratch dir>
Output: d08_d3_tail_twist_trace.csv, d08_d3_tail_twist_windows.csv, d08_d3_tail_twist.json.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent
WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed7-impl")
LEGS = ("FL", "FR", "RL", "RR")
U_HOLD = 0.01 * 0.020924
RUNS = ("R12_top-FR-Fs0-o0.05_D8-LSM4-a2", "R12_top-FR-Fs0-o0.05_D8-LSM4-A",
        "R12_top-FL-Fs0-o0.0_D8-Mslow-a2", "R12_top-FL-Fs0-o0.0_D8-Mslow-A")


def geometry():
    sys.path.insert(0, str(WT / "03_src"))
    from outrigger_sim.control.c2 import C2Geometry
    from outrigger_sim.params import load_params

    g = C2Geometry.from_params(load_params())
    return np.asarray(g.support_matrix, float), np.asarray(g.twist_vector, float)


def longest(path: Path, tkey: str) -> dict:
    z = np.load(path, allow_pickle=False)
    objs = sorted({k.split("|")[0] for k in z.files})
    best = max(objs, key=lambda o: len(z[f"{o}|{tkey}"]) if f"{o}|{tkey}" in z.files else 0)
    return {k.split("|", 1)[1]: z[k] for k in z.files if k.startswith(best + "|")}


def main() -> int:
    scratch = Path(sys.argv[1])
    A, nu = geometry()
    P = A @ np.linalg.pinv(A)
    rp = json.loads((OUT / "d01_repro_check.json").read_text(encoding="utf-8"))
    tev = {r["d8"]["stem"]: r["rerun"]["t_event_s"] for r in rp if r.get("d8")}
    trace, wins, summ = [], [], {}
    for run in RUNS:
        z = dict(np.load(scratch / "t4h" / f"{run}.npz", allow_pickle=False))
        plant = longest(scratch / "logs" / f"{run}_plant.npz", "t")
        ctrl = longest(scratch / "logs" / f"{run}_ctrl.npz", "m.t_s")
        t = z["t_s"]
        ph = np.char.lower(z["phase"].astype(str))
        te = tev[run]
        idx = np.flatnonzero((ph == "level") & (t > te))
        if not len(idx):
            continue
        i0 = idx[0]
        i1 = i0
        while i1 + 1 < len(t) and ph[i1 + 1] == "level":
            i1 += 1
        ips = np.array([int(np.argmin(np.abs(plant["t"] - t[k]))) for k in range(i0 - 1, i1 + 1)])
        ics = np.array([int(np.argmin(np.abs(ctrl["m.t_s"] - t[k]))) for k in range(i0, i1 + 1)])
        sref = plant["sref"][ips]
        x = plant["x"][ips]
        vs = np.diff(sref, axis=0) / 0.1
        vx = np.diff(x, axis=0) / 0.1
        u = z["command_m_s"][i0:i1 + 1]
        D = z["lsb_ib_twist_load_N"][i0 - 1:i1 + 1]
        dD = np.diff(D) / 0.1
        locked = plant["locked"][ips[1:]] > 0.5
        f = plant["f"][ips[1:]]
        Fs = plant["Fs"][ips[1:]]
        stuck = np.abs(f) < Fs - 1.0
        for n, k in enumerate(range(i0, i1 + 1)):
            ic = ics[n]
            row = {"run": run, "t_s": round(float(t[k]), 2), "t_after_event_s": round(float(t[k] - te), 2),
                   "D_kN": round(float(D[n + 1]) / 1e3, 3), "dD_kN_s": round(float(dD[n]) / 1e3, 3),
                   "nu_u_mm_s": round(float(nu @ u[n]) * 1e3, 4),
                   "nu_vs_mm_s": round(float(nu @ vs[n]) * 1e3, 4),
                   "nu_vx_mm_s": round(float(nu @ vx[n]) * 1e3, 4),
                   "supp_u_norm_mm_s": round(float(np.linalg.norm(P @ u[n])) * 1e3, 4),
                   "roll_mrad": round(float(ctrl["s.roll_rad"][ic]) * 1e3, 4),
                   "pitch_mrad": round(float(ctrl["s.pitch_rad"][ic]) * 1e3, 4),
                   "roll_int": round(float(ctrl["s.roll_integral"][ic]), 6),
                   "pitch_int": round(float(ctrl["s.pitch_integral"][ic]), 6),
                   "on_target": int(ctrl["s.completion_flags.is_on_target"][ic] > 0.5),
                   "complete": int(ctrl["s.completion_flags.is_complete"][ic] > 0.5)}
            for j, leg in enumerate(LEGS):
                row.update({f"{leg}_u_mm_s": round(float(u[n, j]) * 1e3, 4),
                            f"{leg}_vs_mm_s": round(float(vs[n, j]) * 1e3, 4),
                            f"{leg}_vx_mm_s": round(float(vx[n, j]) * 1e3, 4),
                            f"{leg}_locked": int(locked[n, j]), f"{leg}_stuck": int(stuck[n, j]),
                            f"{leg}_ib": int(z["lsb_ib_on"][k, j])})
            trace.append(row)
        # windows of 10 s
        tt = t[i0:i1 + 1]
        for w0 in np.arange(tt[0], tt[-1], 10.0):
            m = (tt >= w0) & (tt < w0 + 10.0)
            if m.sum() < 20:
                continue
            nvx = np.array([nu @ v for v in vx[m]])
            nvs = np.array([nu @ v for v in vs[m]])
            nuu = np.array([nu @ v for v in u[m]])
            held = locked[m] & (np.abs(u[m]) > 1e-9)
            sub = (np.abs(u[m]) > 1e-9) & (np.abs(u[m]) <= U_HOLD + 1e-12)
            missing = np.where(held, u[m], 0.0)  # commanded but not executed (locked)
            wins.append({
                "run": run, "w0_after_event_s": round(float(w0 - te), 1), "periods": int(m.sum()),
                "dD_kN_per_10s": round(float(D[1:][m][-1] - D[:-1][m][0]) / 1e3, 3),
                "mean_nu_vx_mm_s": round(float(nvx.mean()) * 1e3, 5),
                "mean_nu_vs_mm_s": round(float(nvs.mean()) * 1e3, 5),
                "mean_nu_u_mm_s": round(float(nuu.mean()) * 1e3, 5),
                "mean_nu_missing_mm_s": round(float(np.mean(missing @ nu)) * 1e3, 5),
                "k_tw_eff_MN_m": round(float(np.mean(dD[m]) / (nvx.mean())) / 1e6, 3)
                if abs(nvx.mean()) > 1e-9 else None,
                "held_leg_periods": {LEGS[j]: int(held[:, j].sum()) for j in range(4)},
                "subhold_leg_periods": {LEGS[j]: int(sub[:, j].sum()) for j in range(4)},
                "mean_u_mm_s": {LEGS[j]: round(float(u[m][:, j].mean()) * 1e3, 4) for j in range(4)},
                "mean_vx_mm_s": {LEGS[j]: round(float(vx[m][:, j].mean()) * 1e3, 4) for j in range(4)},
                "roll_mrad_range": [round(float(np.min([r for r in [ctrl['s.roll_rad'][c] for c in ics[m]]])) * 1e3, 4),
                                    round(float(np.max([ctrl['s.roll_rad'][c] for c in ics[m]])) * 1e3, 4)],
                "pitch_mrad_range": [round(float(np.min([ctrl['s.pitch_rad'][c] for c in ics[m]])) * 1e3, 4),
                                     round(float(np.max([ctrl['s.pitch_rad'][c] for c in ics[m]])) * 1e3, 4)],
                "on_target_frac": round(float(np.mean([ctrl['s.completion_flags.is_on_target'][c] > 0.5
                                                       for c in ics[m]])), 2),
                "ib_on_periods": int(z["lsb_ib_on"][i0:i1 + 1][m].sum())})
        summ[run] = {"t_event_s": te, "level_t0_s": round(float(t[i0]), 2),
                     "level_t1_s": round(float(t[i1]), 2), "level_len_s": round(float(t[i1] - t[i0] + 0.1), 2)}
    for name, rows in (("trace", trace), ("windows", wins)):
        fields = []
        for r in rows:
            for k in r:
                if k not in fields:
                    fields.append(k)
        with (OUT / f"d08_d3_tail_twist_{name}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in rows:
                w.writerow({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in r.items()})
    (OUT / "d08_d3_tail_twist.json").write_text(json.dumps({"nu": nu.tolist(), "segments": summ,
                                                            "windows": wins}, indent=1), encoding="utf-8")
    print("nu", np.round(nu, 4).tolist())
    for k, v in summ.items():
        print(k, v)
    for w in wins:
        print(json.dumps(w))
    return 0


if __name__ == "__main__":
    sys.exit(main())
