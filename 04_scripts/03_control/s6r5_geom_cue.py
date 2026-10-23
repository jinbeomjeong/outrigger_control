"""S6 spec revision 5: geometric contact cues from the stroke sensors (G1' / G2 / G3), reduced 6-DoF plant.

Re-uses 05_tests/unit/test_c2_closed_loop.py helpers (levelled C2 R4 loop, reduced plant) by import, read-only.
Scenarios after a levelled READY, controller frozen (u = 0 unless noted), per auger level:
  sink  : RR floor sinks 30 mm over 5 s (floor subsides under a loaded pad -> RR lifts off), 25 s observed
  lift  : RR retracts 25 mm at 0.25 v_max (the leg pulls its own pad off a rigid floor), 25 s observed
  twist : all legs keep contact, twist move +-4 mm on the n mode (control: no lift), 20 s observed
Cues (sensor values only: rod stroke = stroke_corrected + N(0, 0.1 mm), head-pressure force, IMU attitude):
  G1' : reference at the scenario start: floor normal n0 (world, from the 4-pad plane and the IMU attitude).
        Each period the pad points p_i (body (x_i, y_i, z_p,i - e_i) rotated by the IMU attitude), raised by the
        predicted penetration F_i / k_s along n0; leave-one-out height d_i = n0.p_i - median_{j != i} n0.p_j
        (no absolute heave is measured, so the offset comes from the other three pads), mm, + = above the floor.
  G2  : four-pad plane fit residual in body axes (no IMU), compression-corrected, mm, signed for leg i.
  G3  : attitude from the strokes (plane of the 4 pads, body axes) change since the reference minus the IMU change.
Truth: pad contact force > 0. IMU: the reduced-model nominal sensor (0.5 mg zero error, 100 ug/rtHz).
Run: conda run -n dynamics-dev python -I s6r5_geom_cue.py <project_root> <out_json>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(sys.argv[1])
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(ROOT / "05_tests" / "unit"))
import test_c2_closed_loop as T  # noqa: E402

rcc = T.reduced_model
LEVEL = {"name": "top", "Fs": 0.0}


def settled_plant_level(roll_deg=0.0, pitch_deg=0.0):
    plant = rcc.Plant(LEVEL["name"], roll_deg, pitch_deg, Fs=LEVEL["Fs"])
    plant.step(np.zeros(4), int(round(rcc.SETTLE_ON_CRAWLER_S / rcc.DT)))
    plant.t = 0.0
    return plant


T.settled_plant = settled_plant_level
RNG = np.random.default_rng(20261021)
NOISE_M = 1e-4
N_TW = np.array([0.476, -0.476, -0.523, 0.523])


def R_of(phi, th):
    cp, sp, ct, st = math.cos(phi), math.sin(phi), math.cos(th), math.sin(th)
    return np.array([[ct, 0, st], [0, 1, 0], [-st, 0, ct]]) @ np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])


def imu_att(acc_f):
    fx, fy, fz = acc_f
    return math.atan2(fy, fz), math.atan2(-fx, math.hypot(fy, fz))


def run(level, scen, Fs=0.0):
    LEVEL["name"] = level; LEVEL["Fs"] = Fs
    loop = T.levelled(T.c2_loop())
    pl = loop.plant
    ctx_xy = rcc.dm.geometry_from_params(rcc.dm.load_params()).pad_xy
    zp = rcc.dm.geometry_from_params(rcc.dm.load_params()).pad_z_retracted
    ks = pl.ks.copy()
    M = np.column_stack([np.ones(4), ctx_xy])
    f_phi = f_th = None
    a = rcc.T_CTRL / 0.5
    st = {"f1": None, "f2": None}

    def filt(att):
        if st["f1"] is None:
            st["f1"] = np.array(att); st["f2"] = np.array(att)
        st["f1"] = st["f1"] + a * (np.array(att) - st["f1"]); st["f2"] = st["f2"] + a * (st["f1"] - st["f2"])
        return st["f2"]

    def sense():
        m = loop.last
        e = np.asarray(m.stroke_corrected_m) + RNG.normal(0, NOISE_M, 4)
        F = np.asarray(m.head_pressure_Pa) * loop.controller.geometry.head_area_m2
        att = filt(imu_att(np.asarray(m.specific_force_m_s2) + np.array([0.5e-3 * 9.81, 0.5e-3 * 9.81, 0.0])))
        return e, F, att

    def pads_body(e, F):
        pen = np.maximum(F, 0.0) / ks                    # predicted penetration (k_s nominal = plant value)
        return np.column_stack([ctx_xy, zp - e - pen])  # floor-surface point under each pad, body axes

    # warm the filter for 2 s at the reference state
    for _ in range(100):
        loop.advance(np.zeros(4)); sense()
    e0, F0, att0 = sense()
    P0 = pads_body(e0, F0)
    n_b0 = np.linalg.lstsq(M, P0[:, 2], rcond=None)[0]
    n0 = R_of(*att0) @ np.array([-n_b0[1], -n_b0[2], 1.0]); n0 /= np.linalg.norm(n0)
    t0 = pl.t
    rows = []
    vmax = loop.controller.geometry.max_speed_m_s
    T_end = 25.0 if scen != "twist" else 20.0
    while pl.t - t0 < T_end:
        u = np.zeros(4)
        tt = pl.t - t0
        if scen == "sink":
            pl.goff[T.RR] = T.LIFTING_SINK_M * min(1.0, tt / T.SINK_RAMP_S)
        elif scen == "lift":
            if tt < 0.025 / (0.25 * vmax):
                u[T.RR] = -0.25 * vmax
        elif scen == "twist":
            ph = tt % 8.0
            if ph < 0.7:
                u = 0.25 * vmax * N_TW
            elif 4.0 <= ph < 4.7:
                u = -0.25 * vmax * N_TW
        loop.advance(u)
        e, F, att = sense()
        P = pads_body(e, F)
        W = (R_of(*att) @ P.T).T
        h = W @ n0
        d1 = np.array([h[i] - np.median(np.delete(h, i)) for i in range(4)]) * 1e3   # median of the other three
        coef = np.linalg.lstsq(M, P[:, 2], rcond=None)[0]
        res = (P[:, 2] - M @ coef) * 1e3                 # body z residual (+ = floor point higher -> pad above)
        nb = np.array([-coef[1], -coef[2], 1.0])
        kin = np.array([math.asin(-(R_of(0, 0) @ nb / np.linalg.norm(nb))[1]),
                        math.atan2(nb[0], nb[2])])
        kin0 = np.array([math.asin(n_b0[2] / math.sqrt(1 + n_b0[1] ** 2 + n_b0[2] ** 2)),
                         math.atan2(-n_b0[1], 1.0)])
        g3 = np.degrees((kin - kin0) + (np.array(att) - np.array(att0)))
        rows.append(dict(t=round(tt, 2), contact=(loop.record.pad_contact_force_N[-1] > 0).tolist(),
                         F_kN=(F / 1e3).round(2).tolist(), d1_mm=d1.round(2).tolist(), res_mm=res.round(3).tolist(),
                         g3_deg=g3.round(4).tolist()))
    return rows


def summarise(rows):
    C = np.array([r["contact"] for r in rows]); D = np.array([r["d1_mm"] for r in rows])
    Rz = np.array([r["res_mm"] for r in rows]); G3 = np.array([r["g3_deg"] for r in rows])
    F = np.array([r["F_kN"] for r in rows])
    out = {}
    for k, lab in enumerate(("FL", "FR", "RL", "RR")):
        g = C[:, k]; l = ~g
        out[lab] = {"lifted_frac": round(float(l.mean()), 3),
                    "d1_grounded_range_mm": [round(float(D[g, k].min()), 2), round(float(D[g, k].max()), 2)] if g.any() else None,
                    "d1_lifted_range_mm": [round(float(D[l, k].min()), 2), round(float(D[l, k].max()), 2)] if l.any() else None,
                    "res_grounded_absmax_mm": round(float(np.abs(Rz[g, k]).max()), 3) if g.any() else None,
                    "res_lifted_range_mm": [round(float(Rz[l, k].min()), 3), round(float(Rz[l, k].max()), 3)] if l.any() else None,
                    "F_lifted_max_kN": round(float(F[l, k].max()), 2) if l.any() else None}
    out["g3_absmax_deg"] = round(float(np.abs(G3).max()), 4)
    out["d1_end_mm"] = D[-1].round(2).tolist()
    return out


def main():
    res = {}
    jobs = [(l, s, 0.0) for l in ("top", "middle", "bottom") for s in ("sink", "lift", "twist")]
    jobs += [("top", s, fs) for s in ("sink", "lift", "twist") for fs in (5e3, 12e3)]
    for lvl, scen, Fs in jobs:
            rows = run(lvl, scen, Fs)
            s = summarise(rows)
            res[f"{lvl}|{scen}|Fs{Fs/1e3:g}"] = {"summary": s, "rows_every_0.5s": rows[::25]}
            print(f"{lvl:6s} {scen:5s} Fs{Fs/1e3:g} RR lifted {s['RR']['lifted_frac']} d1 RR grounded {s['RR']['d1_grounded_range_mm']} "
                  f"lifted {s['RR']['d1_lifted_range_mm']} | res RR lifted {s['RR']['res_lifted_range_mm']} "
                  f"| others grounded d1 {[s[k]['d1_grounded_range_mm'] for k in ('FL','FR','RL')]} "
                  f"res {[s[k]['res_grounded_absmax_mm'] for k in ('FL','FR','RL','RR')]} g3 {s['g3_absmax_deg']} end {s['d1_end_mm']}",
                  flush=True)
    Path(sys.argv[2]).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
