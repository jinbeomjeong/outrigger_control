"""M2 candidate in a scratch wrapper around the real law (03_src unchanged): rod pressure change of a moving leg shifts s_ref.

delta s_ref per step = A_ann (p_r(k-1) - p_r(k)) / k_h(s_ref), so F changes by (k2 / k_h) A_ann dp. Also the body-fixed pair that checks
the coefficient, and the TOUCH force difference (gallery plus numerical mid volume). Current REXOME35.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import common  # sets sys.path for the project modules
import build_hopsan_spec as bhs
import four_leg as fl
from common import SCRATCH, dump, pin_two_cores
from params import LEGS, load_params

from outrigger_sim.actuation import SpeedReference
from outrigger_sim.hydraulics.l2b_rod_side import L2bRodSide


def run_law(case, p, grid, cmd, m2: bool, body_fixed: bool = False, tau_release: float = 0.05, dt: float = 1.0e-4):
    f0 = fl.base_loads(case, p)
    law = L2bRodSide(head_area_m2=p.A_h, annulus_area_m2=p.A_r, k_out_N_m=p.k_st, bulk_modulus_Pa=p.beta, head_dead_length_m=p.L0h,
                     rod_dead_length_m=[p.L0r] * 4, stroke_m=p.stroke, p_r0_after_extend_Pa=case.p_r0, p_r0_after_retract_Pa=case.p_r0,
                     p_floor_abs_Pa=1.0e4, release_tau_s=tau_release, lock_eps_m_s=1.0e-6, mechanics="one_sided_parallel", armed=True)
    k2 = np.array([law.k2_N_m(i, float(p.s0[i])) for i in range(4)])
    ref = SpeedReference(p.s0 + f0 / k2, [[0.0, 0.9]] * 4, max_speed_m_s=p.v_max, ramp_s=0.1)
    ref.configure_valve(tau_s=fl.TAU_V)
    q, dq = np.zeros(3), np.zeros(3)
    M = np.array([p.mass, p.I_roll, p.I_pitch])
    force = f0.copy()
    u_act = np.zeros(4)
    rows = []
    p_prev = case.p_r0.copy()
    for k in range(int(round(case.t_end / dt)) + 1):
        t = k * dt
        j = min(int(t / fl.GRID_DT), len(grid) - 1)
        ref.set_command(cmd[j] * p.v_max)
        s_ref_now = ref.s_ref_m
        ref.advance(dt, cylinder_force_N=force, t_s=t)
        u = ref.u_applied_m_s
        w = q[0] + p.yp * q[1] - p.xp * q[2]
        dw = dq[0] + p.yp * dq[1] - p.xp * dq[2]
        s_link = p.s0 + w
        spring = law.spring_force_N(t, dt, u_act, s_ref_now, s_ref_now - s_link, force)
        p_r = law.rod_pressure_Pa
        if m2:
            k_h = p.beta * p.A_h / (p.L0h + s_ref_now)
            moving = ~law.locked
            delta = np.where(moving, p.A_r * (p_prev - p_r) / k_h, 0.0)
            ref.shift_reference(-delta)  # takes effect in the force of the next step
        p_prev = p_r
        c = np.where(np.abs(u) <= 1e-6, fl.C_LOCK, fl.C_MOVE)
        force = spring + c * (u - dw)
        dF = force - f0
        rows.append(np.concatenate([[t], force, u, (force + p_r * p.A_r) / p.A_h, p_r, s_ref_now]))
        if not body_fixed:
            dq = dq + np.array([dF.sum(), (p.yp * dF).sum(), (-p.xp * dF).sum()]) / M * dt
            q = q + dq * dt
        u_act = u
    a = np.array(rows)
    return {"t": a[:, 0], "F": a[:, 1:5], "v": a[:, 5:9], "p_h": a[:, 9:13], "p_r": a[:, 13:17], "pos": a[:, 17:21]}


def load_saved(name: str, tag: str) -> dict:
    a = np.load(SCRATCH / "four" / name / tag)
    return {k: a[k] for k in a.files}


def main() -> None:
    pin_two_cores()
    p = load_params()
    fl.AH[:] = p.A_h
    fl.AR[:] = p.A_r
    by_name = {c.name: c for c in fl.cases(p)}
    out = {"meta": {"dimensions": "current REXOME35, top auger, flat", "pressure": "bar gauge", "law": "real L2bRodSide + SpeedReference, massless rod, 3-DOF body; M2 in this wrapper only",
                    "m2_rule": "moving leg: s_ref += A_ann (p_r_prev - p_r) / k_h(s_ref) every step; k_h = beta A_h / (L0h + s_ref)"}, "closed": {}, "fixed_body": {}, "touch": {}}
    # (a) saved two-chamber results against the law without and with M2
    for name in ("A_stop_all_eta95", "B_twist", "C2_release_ground", "C3_release_ground_r2"):
        case = by_name[name]
        grid, cmd, _u = fl.command_series(case, p)
        hop = load_saved(name, "hop_all.npz")
        num = load_saved(name, "num_all.npz")
        entry = {"hopsan": fl.window_stats(hop, case.t_event, case.t_end), "numpy": fl.window_stats(num, case.t_event, case.t_end)}
        for tag, flag in (("law", False), ("law_m2", True)):
            r = run_law(case, p, grid, cmd, flag)
            entry[tag] = fl.window_stats(r, case.t_event, case.t_end)
            entry[f"{tag}_vs_hopsan"] = fl.compare(r, hop, case.t_event, case.t_end)
            entry[f"{tag}_vs_numpy"] = fl.compare(r, num, case.t_event, case.t_end)
            print(name, tag, "dFmax", np.round(entry[tag]["dF_max_kN"], 2), "dFmin", np.round(entry[tag]["dF_min_kN"], 2), "Fend", np.round(entry[tag]["F_end_kN"], 2),
                  "vsH dF", np.round(entry[f"{tag}_vs_hopsan"]["dF_abs_max_kN"], 2), "Fnet", np.round(entry[f"{tag}_vs_hopsan"]["F_net_10Hz_abs_max_kN"], 2), flush=True)
        print(name, "H dFmax", np.round(entry["hopsan"]["dF_max_kN"], 2), "Fend", np.round(entry["hopsan"]["F_end_kN"], 2), "N", np.round(entry["numpy"]["dF_max_kN"], 2), np.round(entry["numpy"]["F_end_kN"], 2), flush=True)
        out["closed"][name] = entry
    # (b) body fixed: difference of the end force gives the coefficient directly
    r35 = copy.copy(by_name["C2_release_ground"])
    r2 = copy.copy(by_name["C3_release_ground_r2"])
    for c, nm in ((r35, "F_fixed_r35"), (r2, "F_fixed_r2")):
        c.name, c.body_fixed = nm, True
    res = {}
    for c in (r35, r2):
        grid, cmd, u_snap = fl.command_series(c, p)
        hop = fl.run_case_hopsan(c, p, grid, u_snap)
        num = fl.run_case_numpy(c, p, grid, u_snap, with_hose=False)
        res[c.name] = {"hopsan": hop["F"][-200:, 0].mean(), "numpy": num["F"][-200:, 0].mean(),
                       "law": run_law(c, p, grid, cmd, False, True)["F"][-200:, 0].mean(), "law_m2": run_law(c, p, grid, cmd, True, True)["F"][-200:, 0].mean(),
                       "p_r_end_hopsan": hop["p_r"][-200:, 0].mean(), "p_r_end_numpy": num["p_r"][-200:, 0].mean()}
    s_lock = float(p.s0[0])
    k_h = p.beta * p.A_h[0] / (p.L0h + s_lock)
    k2 = 1.0 / (1.0 / k_h + 1.0 / p.k_st[0])
    coef = k2 / k_h
    expected = coef * p.A_r[0] * (34.818e5 - 2.0e5)
    fb = {"k_h_N_m": k_h, "k_out_N_m": p.k_st[0], "k2_N_m": k2, "k2_over_k_h": coef, "A_ann_m2": p.A_r[0], "expected_end_diff_kN": expected / 1e3,
          "F_end_kN": {k: {a: (b / 1e3 if a.startswith(("hopsan", "numpy", "law")) else b / 1e5) for a, b in v.items()} for k, v in res.items()}}
    for tag in ("hopsan", "numpy", "law", "law_m2"):
        fb[f"end_diff_{tag}_kN"] = (res["F_fixed_r35"][tag] - res["F_fixed_r2"][tag]) / 1e3
        fb[f"implied_coefficient_{tag}"] = (res["F_fixed_r35"][tag] - res["F_fixed_r2"][tag]) / (p.A_r[0] * (34.818e5 - 2.0e5))
    out["fixed_body"] = fb
    print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in fb.items() if k != "F_end_kN"}, flush=True)
    print(fb["F_end_kN"], flush=True)
    # (c) TOUCH: is the end force difference the 1 L numerical mid volume?
    base = by_name["E_touch_eta85"]
    for vg in (1.5e-3, 3.0e-3):
        c = copy.copy(base)
        c.name, c.v_gallery = f"E_numpy_Vg{vg * 1e3:g}L", vg
        grid, _cmd, u_snap = fl.command_series(c, p)
        num = fl.run_case_numpy(c, p, grid, u_snap, with_hose=False)
        out["touch"][c.name] = float(num["F"][-1, 0] / 1e3)
        print(c.name, out["touch"][c.name], flush=True)
    c = copy.copy(base)
    c.name = "E_hopsan_Vmid0p1L"
    grid, _cmd, u_snap = fl.command_series(c, p)
    bhs.V_MID, fl.TS = 1.0e-4, 2.0e-6
    (SCRATCH / "four" / c.name).mkdir(parents=True, exist_ok=True)
    hop = fl.run_case_hopsan(c, p, grid, u_snap)
    bhs.V_MID, fl.TS = 1.0e-3, 1.0e-5
    out["touch"][c.name] = float(hop["F"][-1, 0] / 1e3)
    out["touch"]["E_hopsan_Vmid0p1L_v_other_end_mm_s"] = (hop["v"][-30:].mean(axis=0) * 1e3).tolist()
    print(c.name, out["touch"][c.name], out["touch"]["E_hopsan_Vmid0p1L_v_other_end_mm_s"], hop["wall_s"], flush=True)
    dump("m2_check.json", out)


if __name__ == "__main__":
    main()
