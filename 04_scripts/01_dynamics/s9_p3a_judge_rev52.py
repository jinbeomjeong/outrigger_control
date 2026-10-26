"""S9 P3a (open-loop lift on SCM) dynamics judgement support values (dynamics_model.md rev. 52, 5.37).

Reads the cad P3a batch (07_results/S9/batch_P3a_20261026_092653, 1 ms rows) and writes one JSON
plus one PNG:

  (A) Gap and lift-off decomposition: geometric pad-bottom gap to the SCM plane at t = 0 and at
      the lift start (8 s); touch times; extension at lift-off; pad sinkage at lift-off against
      the continuous Bekker static value at the lift-off load, with and without the SCM rate
      term R * sink rate (SCMTerrain.cpp:1462-1465: sigma += -Vn R, not clamped by the yield).
  (B) Post-lift-off creep: pad sink rates, roll / pitch at +0.5 / 1 / 2 / 4 s, time when all
      sink rates stay < 0.1 mm/s; minimum cylinder force between first loading (> 1.4 F_min)
      and lift-off (staggered-touch dip).
  (C) End-state roll stiffness on the virgin branch (tangent n N / s per pad) against W h.
  (D) Independent replica after lift-off: rigid superstructure, 3 DoF about the pad-bottom level
      (heave, roll > 0 left up, pitch > 0 nose down), four single-node Chrono-law SCM pads
      (elastic try K (s - s_p), Bekker replacement k_eq s^n with yield memory, + R sink rate),
      rigid legs extending at v_max from the Chrono lift-off state, P-Delta with the COM height
      h(t) above the pad bottoms, pads anchored laterally, small angles. Variants: actual pad
      layout (RR 75 mm further outboard than RL), symmetric rear layout with COM y = 0 (+-1e-6 rad
      seed), h x 0.5, R = 0. Semi-implicit Euler, dt 2e-5 s.

Frame: body x forward, y left, z up; roll > 0 left side up, pitch > 0 nose down; gravity
(0, 0, -9.80665) m/s^2; SI unless the key says mm / kN / deg. Sinkage + = pad bottom below the
SCM plane (plane = crawler bottom + 4 mm, scm_model.BLOCK_BOTTOM_ABOVE_CRAWLER_BOTTOM_M).

Usage (dynamics-dev, activated):
  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/s9_p3a_judge_rev52.py <out.json> <out.png>
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

WT = Path(__file__).resolve().parents[2]
BATCH = WT / "07_results" / "S9" / "batch_P3a_20261026_092653"
CASES = ("P3a_J1_B", "P3a_J1_A", "P3a_G1_B", "P3a_G1_A")
LEGS = ("FL", "FR", "RL", "RR")
G = 9.80665
# YAML 02_params/rexome33.yaml (params_sha256 d06a97dd... in the run meta)
M = 38400.8366  # superstructure.auger_levels.top.mass_kg
COM_B = np.array([0.460190503, -0.00136232581, 2.18347069])  # top auger, body axes
IXX_C, IYY_C = 533505.361, 688692.429  # about the COM
PAD_XY = {"actual": np.array([[2.2938, 1.3238], [2.2938, -1.3238], [-2.556, 1.1679], [-2.556, -1.2429]]),
          "symmetric": np.array([[2.2938, 1.3238], [2.2938, -1.3238], [-2.556, 1.2054], [-2.556, -1.2054]])}
PAD_BOTTOM_Z_B = np.array([-0.6998, -0.6998, -0.71, -0.71])  # legs.*.pad_bottom_center_retracted_m z
CRAWLER_BOTTOM_Z = -1.0509
SCM_PLANE_OFFSET = 0.004
MOVING_MASS = np.array([106.783666, 106.783666, 73.1629937, 73.1629937])  # legs.*.moving mass (rod + pad)
V_LEG = 0.020924  # actuator.max_speed_m_s
F_MIN = 9414.58911  # control.F_min_cylinder_N


def load(case):
    d = np.load(BATCH / case / "series.npz")
    r = json.loads((BATCH / case / "result.json").read_text("utf-8"))
    return {k: d[k] for k in d.files}, r


def soil(r):
    sc = r["meta"]["scm"]["soil"]["chrono"]
    pv = r["meta"]["pad_variant"]
    area = np.array([pv["pad_bottom_area_m2"][k] for k in LEGS])
    b = np.array([pv["pad_bekker_b_m"][k] for k in LEGS])
    return dict(n=sc["n"], K=sc["elastic_K"], R=sc["damping_R"], keq=sc["Kc"] / b + sc["Kphi"], A=area)


def bekker_s(N, so, sig_rate=0.0):
    p = N / so["A"] - sig_rate
    return (np.maximum(p, 0.0) / so["keq"]) ** (1.0 / so["n"])


def part_a_b_c(case):
    d, r = load(case)
    so = soil(r)
    t = d["t_s"]
    sk, pn, F, s_m, rp = (d["pad_sinkage_geometric_m"], d["scm_pad_normal_N"], d["F_cyl_N"], d["s_motor_m"],
                          d["roll_pitch_deg"])
    i8 = int(np.searchsorted(t, 8.0 - 1e-9))
    lo = r["p3a"]["P3a-2_liftoff"]["t_liftoff_s"]
    ilo = int(np.searchsorted(t, lo - 1e-9))
    gap_yaml = PAD_BOTTOM_Z_B - CRAWLER_BOTTOM_Z
    touch = [float(t[np.nonzero((t > 8.0) & (pn[:, i] > 0))[0][0]]) for i in range(4)]
    j0, j1 = int(np.searchsorted(t, lo - 0.3)), int(np.searchsorted(t, lo - 0.1))
    rate = (sk[j1] - sk[j0]) / (t[j1] - t[j0])
    out = {"soil": {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in so.items()},
           "A_gap": {"gap_yaml_rigid_floor_mm": (gap_yaml * 1e3).round(2).tolist(),
                     "gap_yaml_minus_scm_plane_offset_mm": ((gap_yaml - SCM_PLANE_OFFSET) * 1e3).round(2).tolist(),
                     "gap_t0_mm": (-sk[0] * 1e3).round(3).tolist(), "gap_lift_start_mm": (-sk[i8] * 1e3).round(3).tolist(),
                     "settle_end_roll_pitch_deg": rp[i8].tolist(), "settle_end_z0_mm": float(d["body_pos_m"][i8, 2] * 1e3),
                     "t_touch_s": touch, "s_motor_at_touch_mm": [float(s_m[np.searchsorted(t, touch[i]), i] * 1e3)
                                                                for i in range(4)]},
           "A_liftoff": {"t_liftoff_s": lo, "s_motor_mm": (s_m[ilo] * 1e3).round(2).tolist(),
                         "pad_normal_kN": (pn[ilo] / 1e3).round(3).tolist(),
                         "design_load_kN": (np.array(r["meta"]["scm"]["soil"]["design_loads_N"]) / 1e3).round(3).tolist(),
                         "sinkage_mm": (sk[ilo] * 1e3).round(3).tolist(),
                         "sink_rate_0p3_0p1s_before_mm_s": (rate * 1e3).round(3).tolist(),
                         "bekker_static_at_load_mm": (bekker_s(pn[ilo], so) * 1e3).round(3).tolist(),
                         "bekker_static_at_design_load_mm": (bekker_s(np.array(r["meta"]["scm"]["soil"]["design_loads_N"]), so)
                                                             * 1e3).round(3).tolist(),
                         "bekker_with_rate_term_mm": (bekker_s(pn[ilo], so, so["R"] * rate) * 1e3).round(3).tolist(),
                         "rate_term_over_pressure": (so["R"] * rate / (pn[ilo] / so["A"])).round(5).tolist()}}
    post = {}
    for dtw in (0.5, 1.0, 2.0, 4.0):
        k = int(np.searchsorted(t, lo + dtw))
        k0 = int(np.searchsorted(t, lo + dtw - 0.2))
        post[f"+{dtw:g}s"] = {"sink_rate_mm_s": ((sk[k] - sk[k0]) / (t[k] - t[k0]) * 1e3).round(3).tolist(),
                              "d_roll_deg": float(rp[k, 0] - rp[ilo, 0]), "d_pitch_deg": float(rp[k, 1] - rp[ilo, 1]),
                              "sinkage_mm": (sk[k] * 1e3).round(2).tolist()}
    # settle time of the creep: all 0.2 s sink rates < 0.1 mm/s from then on
    kk = np.arange(ilo + 200, len(t))
    rates = np.abs(sk[kk] - sk[kk - 200]) / 0.2
    bad = np.nonzero(np.any(rates >= 1e-4, axis=1))[0]
    t_quiet = float(t[kk[bad[-1]]] - lo) if bad.size else 0.0
    dip = []
    for i in range(4):
        k0 = int(np.nonzero((t > 8) & (F[:, i] > 1.4 * F_MIN))[0][0])
        m = (np.arange(len(t)) >= k0) & (t <= lo)
        k = int(np.argmin(np.where(m, F[:, i], np.inf)))
        dip.append({"t_first_above_1p4Fmin_s": float(t[k0]), "F_cyl_min_until_liftoff_kN": float(F[k, i] / 1e3),
                    "t_min_s": float(t[k]), "below_F_min": bool(F[k, i] < F_MIN)})
    out["B_post_liftoff"] = {"windows": post, "t_creep_quiet_after_liftoff_s": t_quiet,
                             "rule": "all four 0.2 s sink rates < 0.1 mm/s from then to the end",
                             "end_roll_pitch_deg": rp[-1].tolist(),
                             "d_roll_pitch_end_vs_liftoff_deg": (rp[-1] - rp[ilo]).tolist(),
                             "end_sinkage_mm": (sk[-1] * 1e3).round(3).tolist(),
                             "end_pad_normal_kN": (pn[-1] / 1e3).round(3).tolist(),
                             "end_bekker_static_at_end_load_mm": (bekker_s(pn[-1], so) * 1e3).round(3).tolist(),
                             "max_past_load_from_end_sinkage_kN": (so["A"] * so["keq"] * np.maximum(sk[-1], 0) ** so["n"]
                                                                   / 1e3).round(3).tolist(),
                             "staggered_touch_dip": dip}
    # (C) roll stiffness on the virgin branch at the end state vs W h
    y = PAD_XY["actual"][:, 1]
    kt = so["n"] * pn[-1] / np.maximum(sk[-1], 1e-6)
    h = COM_B[2] + float(d["body_pos_m"][-1, 2]) - (CRAWLER_BOTTOM_Z + SCM_PLANE_OFFSET) + float(np.mean(sk[-1]))
    w = (M + MOVING_MASS.sum()) * G
    out["C_roll_stiffness"] = {"k_tangent_virgin_N_m": kt.round(0).tolist(), "K_roll_tangent_N_m_rad": float((kt * y ** 2).sum()),
                               "h_com_above_pad_bottom_m": h, "W_h_N_m_rad": w * h,
                               "ratio_Wh_over_K": w * h / float((kt * y ** 2).sum()),
                               "k_elastic_unloading_N_m": (so["K"] * so["A"]).round(0).tolist(),
                               "note": "all-plastic tangent; a pad that unloads switches to K A (stiff)"}
    out["_lift_state"] = {"ilo": ilo, "lo": lo, "sink": sk[ilo].tolist(), "s_motor": s_m[ilo].tolist(),
                          "t_run": float(t[-1] - t[ilo])}
    out["_chrono_hist"] = {"t": (t[ilo::100] - lo).tolist(), "roll": (rp[ilo::100, 0] - rp[ilo, 0]).tolist(),
                           "sink_mm": (sk[ilo::100] * 1e3).tolist()}
    return case, out


def replica(args):
    st, so, kw = args
    layout = kw.get("layout", "actual")
    yc = kw.get("yc")
    h_scale, R_scale, phi0 = kw.get("h_scale", 1.0), kw.get("R_scale", 1.0), kw.get("phi0", 0.0)
    t_run, dt = st["t_run"], 2e-5
    xy = PAD_XY[layout]
    x, y = xy[:, 0], xy[:, 1]
    xc, ycb = COM_B[0], (COM_B[1] if yc is None else yc)
    n, K, R, keq, A = so["n"], so["K"], so["R"] * R_scale, np.asarray(so["keq"]), np.asarray(so["A"])
    s0 = np.asarray(st["sink"])
    s = s0.copy()
    sy = keq * np.maximum(s, 0) ** n
    sp = s - sy / K
    s_leg0 = float(np.mean(st["s_motor"]))
    hz0 = COM_B[2] - float(np.mean(PAD_BOTTOM_Z_B))
    z = th = vz = wphi = wth = 0.0
    phi = phi0
    sdot = np.full(4, V_LEG)
    t, k = 0.0, 0
    hist = []
    while t < t_run - 1e-12:
        h = (hz0 + s_leg0 + V_LEG * t) * h_scale
        ix, iy = IXX_C + M * h ** 2, IYY_C + M * h ** 2
        s_new = s0 + V_LEG * t - z - y * (phi - phi0) + x * th
        if k:
            sdot = (s_new - s) / dt
        s = s_new
        sig = np.maximum(K * (s - sp), 0.0)
        bek = keq * np.maximum(s, 0) ** n
        yld = sig > sy
        sig = np.where(yld, bek, sig)
        sy = np.where(yld, bek, sy)
        sp = np.where(yld, s - bek / K, sp)
        sig_tot = sig + np.where(K * (s - sp) > 0, R * sdot, 0.0)
        N = A * sig_tot - MOVING_MASS * G
        vz += (N.sum() - M * G) / M * dt
        wphi += ((N * y).sum() - M * G * (ycb - h * phi)) / ix * dt
        wth += (-(N * x).sum() + M * G * (xc + h * th)) / iy * dt
        z += vz * dt
        phi += wphi * dt
        th += wth * dt
        if k % 5000 == 0:
            hist.append([t, float(np.degrees(phi - phi0)), *(s * 1e3).tolist()])
        t += dt
        k += 1
    hist = np.array(hist)
    return {"variant": kw, "end_d_roll_deg": float(np.degrees(phi - phi0)), "end_d_pitch_deg": float(np.degrees(th)),
            "end_sinkage_mm": (s * 1e3).round(3).tolist(), "end_pad_normal_kN": (A * sig_tot / 1e3).round(3).tolist(),
            "max_past_load_kN": (A * sy / 1e3).round(3).tolist(),
            "d_roll_at_1_2_4_s_deg": [float(np.interp(q, hist[:, 0], hist[:, 1])) for q in (1, 2, 4)],
            "_hist": hist.tolist()}


VARIANTS = {"actual": {}, "symmetric_yc0_+1e-6": {"layout": "symmetric", "yc": 0.0, "phi0": 1e-6},
            "symmetric_yc0_-1e-6": {"layout": "symmetric", "yc": 0.0, "phi0": -1e-6},
            "actual_h_x0.5": {"h_scale": 0.5}, "actual_R0": {"R_scale": 0.0}}


def main():
    out_json, out_png = Path(sys.argv[1]), Path(sys.argv[2])
    res = {"doc": __doc__.strip().splitlines()[0], "batch": str(BATCH.relative_to(WT)).replace("\\", "/"),
           "frames": "body x fwd, y left, z up; roll > 0 left up; pitch > 0 nose down; sinkage + below SCM plane",
           "cases": {}}
    with ProcessPoolExecutor(4) as ex:
        for case, o in ex.map(part_a_b_c, CASES):
            res["cases"][case] = o
        jobs, keys = [], []
        for case in ("P3a_J1_B", "P3a_J1_A", "P3a_G1_B"):
            _, r = load(case)
            so = {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in soil(r).items()}
            for name, kw in VARIANTS.items():
                jobs.append((res["cases"][case]["_lift_state"], so, kw))
                keys.append((case, name))
        for (case, name), rr in zip(keys, ex.map(replica, jobs)):
            res["cases"][case].setdefault("D_replica", {})[name] = rr
    # figure (J1_B)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    c = res["cases"]["P3a_J1_B"]
    ch = c["_chrono_hist"]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].plot(ch["t"], ch["roll"], "k-", label="Chrono")
    for name, sty in (("actual", "C0--"), ("symmetric_yc0_+1e-6", "C1:"), ("actual_R0", "C2-.")):
        hh = np.array(c["D_replica"][name]["_hist"])
        ax[0].plot(hh[:, 0], hh[:, 1], sty, label=f"replica {name}")
    ax[0].set_xlabel("time after lift-off [s]")
    ax[0].set_ylabel("roll change [deg] (> 0 left up)")
    ax[0].legend(fontsize=8)
    ax[0].set_title("J1 B roll after crawler lift-off")
    sk = np.array(ch["sink_mm"])
    hh = np.array(c["D_replica"]["actual"]["_hist"])
    for i, leg in enumerate(LEGS):
        ax[1].plot(ch["t"], sk[:, i], f"C{i}-", label=f"{leg} Chrono")
        ax[1].plot(hh[:, 0], hh[:, 2 + i], f"C{i}--", label=f"{leg} replica")
    ax[1].set_xlabel("time after lift-off [s]")
    ax[1].set_ylabel("pad sinkage [mm]")
    ax[1].legend(fontsize=7, ncol=2)
    ax[1].set_title("J1 B pad sinkage")
    fig.tight_layout()
    fig.savefig(out_png, dpi=120)
    for case in res["cases"].values():
        case.pop("_lift_state", None)
        case.pop("_chrono_hist", None)
        for rr in case.get("D_replica", {}).values():
            rr.pop("_hist", None)
    out_json.write_text(json.dumps(res, indent=1), "utf-8")
    for case, o in res["cases"].items():
        print(case, json.dumps({k: o[k] for k in ("A_liftoff", "C_roll_stiffness")}))
        print("  post", json.dumps(o["B_post_liftoff"]["d_roll_pitch_end_vs_liftoff_deg"]),
              o["B_post_liftoff"]["t_creep_quiet_after_liftoff_s"],
              json.dumps([dd["F_cyl_min_until_liftoff_kN"] for dd in o["B_post_liftoff"]["staggered_touch_dip"]]))
        for name, rr in o.get("D_replica", {}).items():
            print("  rep", name, round(rr["end_d_roll_deg"], 4), round(rr["end_d_pitch_deg"], 4), rr["end_sinkage_mm"])


if __name__ == "__main__":
    main()
