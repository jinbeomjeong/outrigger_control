"""S9 P2-b comparison values: crawler settle replica with the Bekker K_c/b term (J1, J2, S1, G1).

dynamics_model.md 5.34.13 supplement (P2-4, rev. 49). Extends s9_crawler_rocking_replica.py
(planar surge x, heave z, pitch theta; SCM normal law per node, explicit loads, symplectic Euler)
with the Chrono 10 SCM cohesive term:

  sigma_plastic = (K_c * oob + K_phi) * s^n,   oob = perimeter / (2 area) of the convex hull of the
  patch node points (SCMTerrain.cpp:1366-1374; area < 1e-6 -> oob = 0).

A patch is the 4-connected set of ray-HIT nodes (SCMTerrain.cpp:1316-1362), not only the nodes in
contact: a ray hits when the target lies between level + 0.1 - 0.5 m and level + 0.1 m
(m_test_offset_up = 0.1, m_test_offset_down = 0.5 defaults, SCMTerrain.cpp:392; the S9 runner does
not call SetTestHeight). So in Chrono each track patch is the whole C-envelope footprint inside the
active domain (ramp bottoms are far below 0.1 m), and oob is constant. The replica uses that value
("hit" mode, default). "contact" mode (hull of the nodes with sigma > 0, the P0 choice) and "none"
(K_c = 0) are sensitivity cases only.

Node phase: Chrono, nodes at (i h, j h) in the SCM plane frame (SCMTerrain.cpp:1178), plane origin
(0, 0) (5.34.11). Track anchors: per-soil k, c from the runner formula
(scm_model.track_tangential_values: k = series(6 k_t,roller, 0.8 K A_c / 2),
c = c_G1 sqrt(k / k_G1)), k_rollers back-computed from the G1 run meta value.
Load: gravity (0, 0, -9.80665) m/s^2 times Poly345 3 s, then hold (t_end 5 s or 20 s), judged
on the mean of the last 1 s. Frame: body x forward, z up, pitch > 0 nose down; SI.

Usage (dynamics-dev, activated):
  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/s9_crawler_replica_kcb.py <out.json>
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull

WT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WT / "04_scripts" / "01_dynamics"))
import run_pad_bekker_p0 as p0  # noqa: E402
import s9_crawler_rocking_replica as rr  # noqa: E402

G = rr.G
SETS = json.load(open(WT / "02_params" / "scm_soil_sets.json", encoding="utf-8"))["sets"]
KAPPA = 0.8  # scm_model.KAPPA_HORIZONTAL
TEST_UP, TEST_DOWN = 0.1, 0.5  # SCMLoader defaults (not changed by the S9 runner)
_KS_G1 = KAPPA * SETS["G1"]["chrono"]["elastic_K"] * SETS["G1"]["crawler_settle_P0"]["A_c_m2"] / 2
K_ROLLERS = 1.0 / (1.0 / rr.K_TRACK - 1.0 / _KS_G1)


def track_values(soil):
    ks = KAPPA * SETS[soil]["chrono"]["elastic_K"] * SETS[soil]["crawler_settle_P0"]["A_c_m2"] / 2
    k = 1.0 / (1.0 / K_ROLLERS + 1.0 / ks)
    return k, rr.C_TRACK * math.sqrt(k / rr.K_TRACK)


def nodes(h, phase):
    """(X, Y, hb) of the left-track node grid. phase None = replica/P0 corner grid, else (ox, oy)
    offset of the Chrono lattice i*h (+ox) inside the active domain (copy of the grid-phase
    script)."""
    if phase is None:
        return p0.crawler_nodes(h)
    ox, oy = phase
    x0, x1 = p0.DOM["x_m"]
    y0, y1 = p0.DOM["y_m"]
    xs = (np.ceil((x0 - ox) / h) + np.arange(0, int((x1 - x0) / h) + 2)) * h + ox
    xs = xs[(xs >= x0) & (xs < x1)]
    ys = (np.ceil((y0 - oy) / h) + np.arange(0, int((y1 - y0) / h) + 2)) * h + oy
    ys = ys[(ys >= y0) & (ys < y1)]
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    hb = np.full(X.shape, np.inf)
    xr0, xf0 = -p0.RAMP["rear"]["x0"], p0.RAMP["front"]["x0"]
    boxes = [
        (xr0, xf0, 0.0, 0.0, 0.0),
        (xf0, max(p0.END_ST) + p0.BLK_X / 2, 0.0, xf0, p0.RAMP["front"]["slope"]),
        (min(p0.END_ST) - p0.BLK_X / 2, xr0, 0.0, xr0, -p0.RAMP["rear"]["slope"]),
    ]
    for a, b, h0, xr, s in boxes:
        m = (X >= a) & (X <= b) & (Y >= p0.BLK_Y0) & (Y <= p0.BLK_Y1)
        hb = np.where(m, np.minimum(hb, h0 + s * (X - xr)), hb)
    return X, Y, hb


def build(soil, h, phase):
    X, Y, hb = nodes(h, phase)
    ok = np.isfinite(hb)
    hit = ok & (hb <= TEST_UP) & (hb >= TEST_UP - TEST_DOWN)
    b = p0.body("top")
    xs = X[:, 0]
    ny = ok.sum(axis=1)
    hcol = np.array([hb[i][ok[i]].min() if ok[i].any() else np.inf for i in range(len(xs))])
    m = ny > 0
    # Chrono patch of one track = hit nodes; hull of the node points
    pts = np.column_stack([X[hit], Y[hit]])
    hull = ConvexHull(pts)
    area, per = float(hull.volume), float(hull.area)
    ys_hit = np.unique(Y[hit])
    nyu = np.unique(ny[m])
    return dict(
        soil=soil,
        h=h,
        phase=phase,
        s=SETS[soil]["chrono"],
        mass=b.mass,
        com=b.com,
        Iyy=b.inertia[1, 1],
        x=xs[m],
        zb=p0.Z_SURF + hcol[m],
        w=ny[m] * 2.0 * h * h,
        ny=ny[m],
        Ly=float(ys_hit.max() - ys_hit.min()),
        hull=dict(
            area_m2=area,
            perimeter_m=per,
            oob_1_m=per / (2 * area),
            b_m=2 * area / per,
            n_hit_nodes=int(hit.sum()),
            n_nodes=int(ok.sum()),
            ny_per_column=nyu.tolist(),
            hb_max_m=float(hb[ok].max()),
            x_span_m=[float(X[hit].min()), float(X[hit].max())],
            y_span_m=[float(ys_hit.min()), float(ys_hit.max())],
        ),
    )


def simulate(
    md,
    t_end=5.0,
    dt=1e-4,
    ramp=3.0,
    bmode="hit",
    ramp_lead=0.0,
    k_scale=1.0,
    track=None,
    rec_every=10,
    anchor="coulomb_lag",
    pdelta=True,
):
    """Same integrator as rr.simulate; coef = K_c oob + K_phi (bmode), track anchors per soil.

    anchor "fixed" = rr.simulate (spring to the t = 0 point, always on).
    anchor "coulomb" = the S9 runner's GroundBushingCoulomb on the tracks (ground_bushing.py,
    scm_model.py TrackNormals): no bushing at t = 0; created at the current track point when the
    track normal N = F_z / 2 (planar: no roll) exceeds 100 N; return mapping k |d| <= tan(phi) N
    (anchor moved, damping off while sliding, back on below 1 mm/s); removed after N <= 0 for
    1 ms; the anchor move / damping switch acts immediately.
    anchor "coulomb_lag" (default, the runner): as "coulomb", but the anchor move and damping
    switch of the hook after step k act from step k + 2 (ground_bushing.py one-step lag);
    create / remove act from step k + 1."""
    mu = math.tan(math.radians(SETS[md["soil"]]["chrono"]["friction"]))
    s = md["s"]
    K, Kphi, Kc, n, R = s["elastic_K"], s["Kphi"], s["Kc"], s["n"], s["damping_R"]
    kt, ct = track if track is not None else track_values(md["soil"])
    kt *= k_scale
    ct *= math.sqrt(k_scale)
    m, Iyy, com = md["mass"], md["Iyy"], md["com"]
    dxb = md["x"] - com[0]
    dzb = md["zb"] - com[2]
    tdx, tdz = rr.X_TRACK - com[0], rr.Z_TRACK - com[2]
    w = md["w"]
    Ly = md["Ly"]
    if bmode == "hit":
        coef_c = Kc * md["hull"]["oob_1_m"] + Kphi
    elif bmode == "none":
        coef_c = Kphi
    else:
        coef_c = None
    xg, zg, th = com[0], com[2], 0.0
    vx = vz = om = 0.0
    sp = np.zeros_like(w)
    sy = np.zeros_like(w)
    x_tr0 = rr.X_TRACK
    exists = anchor == "fixed"
    sliding = False
    x_use, sl_use = x_tr0, False  # values the force sees (one-step hook lag, "coulomb_lag")
    x_prev, sl_prev = x_tr0, False
    zero_t = 0.0
    n_create = n_remove = n_slide = 0
    nsteps = int(round(t_end / dt))
    out = []
    oob_rec = []
    for k in range(nsteps):
        t = k * dt
        c, sn = math.cos(th), math.sin(th)
        # moment arm of the node forces about the COG; pdelta=False drops the horizontal shift
        # dzb sin(theta) (= the small-angle P0 kinematics, no geometric stiffness -W h)
        ox = c * dxb + sn * dzb if pdelta else dxb
        oz = -sn * dxb + c * dzb
        zw = zg + oz
        vzn = vz + om * (-c * dxb - sn * dzb)
        sink = p0.Z_SURF - zw
        sig = K * (sink - sp)
        con = sig > 0
        if coef_c is None:
            if con.any():
                xc = md["x"][con]
                Lx = float(xc.max() - xc.min())
                A = Lx * Ly
                oob = (2 * (Lx + Ly)) / (2 * A) if A >= 1e-6 else 0.0
            else:
                oob = 0.0
            coef = Kc * oob + Kphi
            if (k + 1) % rec_every == 0:
                oob_rec.append(oob)
        else:
            coef = coef_c
        load = con & (sig > sy)
        bek = coef * np.maximum(sink, 0.0) ** n
        sig = np.where(load, bek, sig)
        sy = np.where(load, bek, sy)
        sp = np.where(load, sink - bek / K, sp)
        sig = np.where(con, sig - vzn * R, 0.0)
        fz = sig * w
        Fz = fz.sum()
        My = -(ox * fz).sum()
        ptx = xg + c * tdx + sn * tdz
        pvx = vx + om * (-sn * tdx + c * tdz)
        if exists:
            Fx = -2 * kt * (ptx - x_use) - (0.0 if sl_use else 2 * ct * pvx)
        else:
            Fx = 0.0
        My += (-sn * tdx + c * tdz) * Fx
        gf = rr.ramp_factor(t + ramp_lead, ramp, "poly345")
        vx += dt * Fx / m
        vz += dt * (Fz / m - G * gf)
        om += dt * My / Iyy
        xg += dt * vx
        zg += dt * vz
        th += dt * om
        if anchor in ("coulomb", "coulomb_lag"):
            c3, s3 = math.cos(th), math.sin(th)
            ptx = xg + c3 * tdx + s3 * tdz
            pvx = vx + om * (-s3 * tdx + c3 * tdz)
            N = max(0.5 * Fz, 0.0)
            event = False
            if not exists:
                if N > 100.0:
                    exists, sliding, zero_t, x_tr0 = True, False, 0.0, ptx
                    n_create += 1
                    event = True
            else:
                d = ptx - x_tr0
                lim = mu * N
                if kt * abs(d) > lim:
                    x_tr0 += d * (1.0 - lim / (kt * abs(d)))
                    sliding = True
                    n_slide += 1
                elif sliding and abs(pvx) < 1e-3:
                    sliding = False
                if Fz <= 0.0:
                    zero_t += dt
                    if zero_t >= 1e-3 * (1 - 1e-9):
                        exists = False
                        n_remove += 1
                        event = True
                else:
                    zero_t = 0.0
            if anchor == "coulomb" or event:
                # immediate (no lag), or a structural change (Chrono runs a full Update next step)
                x_use, sl_use = x_tr0, sliding
                x_prev, sl_prev = x_tr0, sliding
            else:
                # anchor move / damping switch of this hook acts from the step after next
                x_use, sl_use = x_prev, sl_prev
                x_prev, sl_prev = x_tr0, sliding
        if (k + 1) % rec_every == 0:
            c2, s2 = math.cos(th), math.sin(th)
            ox0 = xg + c2 * (-com[0]) + s2 * (-com[2])
            oz0 = zg - s2 * (-com[0]) + c2 * (-com[2])
            out.append((t + dt, math.degrees(th), ox0, oz0, Fz, con.sum()))
    out = np.array(out)
    simulate.last_anchor_events = dict(create=n_create, remove=n_remove, slide_steps=n_slide)
    return out, (np.array(oob_rec) if oob_rec else None)


def summarise(md, out, oob_rec, ramp=3.0):
    t, th, zo, Fz = out[:, 0], out[:, 1], out[:, 3], out[:, 4]
    sel = t >= t[-1] - 1.0 + 1e-9
    W = md["mass"] * G
    early = t <= ramp + 2.0 + 1e-9
    i_up = int(np.argmax(zo[early]))
    win = []
    for te in np.arange(ramp + 2.0, t[-1] + 1e-9, 1.0):
        s = (t > te - 1.0 + 1e-9) & (t <= te + 1e-9)
        win.append(
            [float(te), float(th[s].mean()), float(np.ptp(th[s])), float(zo[s].mean() * 1e3)]
        )
    r = dict(
        pitch_deg=float(th[sel].mean()),
        pitch_pp_deg=float(np.ptp(th[sel])),
        z0_mm=float(zo[sel].mean() * 1e3),
        Fn_over_W=float(Fz[sel].mean() / W),
        start_rise_max_mm=float(zo[early][i_up] * 1e3),
        start_rise_t_s=float(t[early][i_up]),
        windows_end_mean_pp_z0=win,
        n_contact_cols_end=int(out[-1, 5]),
        n_cols=int(len(md["x"])),
    )
    if oob_rec is not None:
        r["oob_contact_end_1_m"] = float(oob_rec[-1])
    return r


def job(spec):
    soil, h, phase, kw, tag = spec
    t0 = time.perf_counter()
    md = build(soil, h, phase)
    out, oob = simulate(md, **kw)
    r = summarise(md, out, oob, ramp=kw.get("ramp", 3.0))
    r["anchor_events"] = dict(simulate.last_anchor_events)
    r.update(
        soil=soil,
        h=h,
        phase=phase,
        case=tag,
        opts={k: v for k, v in kw.items()},
        hull=md["hull"],
        wall_s=time.perf_counter() - t0,
    )
    return r


CH = (0.0, 0.0)


def specs():
    out = []
    for soil in ("J1", "J2", "S1", "G1"):
        out.append((soil, 0.04, CH, {}, "base_4cm"))
        out.append((soil, 0.02, CH, {}, "grid_2cm"))
        out.append((soil, 0.01, CH, {}, "grid_1cm"))
        out.append((soil, 0.005, CH, {}, "grid_0p5cm"))
        out.append((soil, 0.04, CH, {"bmode": "contact"}, "b_contact_4cm"))
        out.append((soil, 0.04, CH, {"bmode": "none"}, "b_none_4cm"))
        out.append((soil, 0.04, CH, {"anchor": "fixed"}, "anchor_fixed_4cm"))
        out.append((soil, 0.04, CH, {"anchor": "coulomb"}, "mf_anchor_nolag_4cm"))
        # P2-f decomposition: P0 grid + contact b, slow ramp 30 s, no anchors, +/- P-delta
        slow = {"ramp": 30.0, "t_end": 33.0, "bmode": "contact", "k_scale": 0.0}
        out.append((soil, 0.02, None, dict(slow), "dec_P0grid_slow_noanchor"))
        out.append(
            (soil, 0.02, None, dict(slow, pdelta=False), "dec_P0grid_slow_noanchor_nopdelta")
        )
        out.append((soil, 0.02, CH, {"bmode": "contact"}, "b_contact_2cm"))
        out.append((soil, 0.04, CH, {"dt": 5e-5, "rec_every": 20}, "unc_dt_half"))
        out.append((soil, 0.04, CH, {"ramp_lead": 1e-4}, "unc_ramp_lead_1step"))
        out.append((soil, 0.04, CH, {"k_scale": 2.0}, "unc_track_k_x2"))
        out.append((soil, 0.04, CH, {"k_scale": 0.5}, "unc_track_k_x0p5"))
        out.append((soil, 0.04, CH, {"t_end": 6.0}, "unc_hold_3s"))
        for ox in (0.01, 0.02, 0.03):
            out.append((soil, 0.04, (ox, 0.0), {}, f"phase_x{int(ox * 100)}cm_4cm"))
        out.append((soil, 0.02, None, {"bmode": "contact"}, "P0grid_2cm_b_contact"))
        # long hold (t_end 20 s = ramp 3 + hold 17 s): n << 1 soils' residual rocking decays slowly
        out.append((soil, 0.04, CH, {"t_end": 20.0}, "long20_base_4cm"))
        out.append((soil, 0.04, CH, {"t_end": 20.0, "anchor": "fixed"}, "long20_anchor_fixed_4cm"))
        out.append(
            (soil, 0.04, CH, {"t_end": 20.0, "anchor": "coulomb"}, "long20_mf_anchor_nolag_4cm")
        )
        out.append((soil, 0.04, CH, {"t_end": 20.0, "bmode": "contact"}, "long20_b_contact_4cm"))
        out.append((soil, 0.02, CH, {"t_end": 20.0}, "long20_grid_2cm"))
        out.append((soil, 0.01, CH, {"t_end": 20.0}, "long20_grid_1cm"))
        out.append(
            (soil, 0.04, CH, {"t_end": 20.0, "dt": 5e-5, "rec_every": 20}, "long20_unc_dt_half")
        )
        out.append((soil, 0.04, CH, {"t_end": 20.0, "k_scale": 2.0}, "long20_unc_track_k_x2"))
        out.append((soil, 0.04, CH, {"t_end": 20.0, "k_scale": 0.5}, "long20_unc_track_k_x0p5"))
        for ox in (0.01, 0.02, 0.03):
            out.append(
                (soil, 0.04, (ox, 0.0), {"t_end": 20.0}, f"long20_phase_x{int(ox * 100)}cm_4cm")
            )
    return out


def selfcheck():
    """Kc = 0 (G1) + G1 track values: identical to rr.simulate on the same Chrono-phase nodes."""
    md = build("G1", 0.04, CH)
    mine, _ = simulate(md, t_end=1.0, track=(rr.K_TRACK, rr.C_TRACK), anchor="fixed")
    md2 = dict(
        s=md["s"], mass=md["mass"], com=md["com"], Iyy=md["Iyy"], x=md["x"], zb=md["zb"], w=md["w"]
    )
    ref, _ = rr.simulate(md2, 1.0, ramp=3.0, shape="poly345")
    d = float(np.max(np.abs(mine[:, :5] - ref[:, :5])))
    kt, ct = track_values("G1")
    return dict(
        max_abs_diff_vs_rr=d,
        track_G1_rel=[kt / rr.K_TRACK - 1, ct / rr.C_TRACK - 1],
        hull_vs_rect=_hull_rect_check(md),
    )


def _hull_rect_check(md):
    Lx = float(md["hull"]["x_span_m"][1] - md["hull"]["x_span_m"][0])
    Ly = md["Ly"]
    return dict(
        rect_area=Lx * Ly,
        rect_perimeter=2 * (Lx + Ly),
        hull_area=md["hull"]["area_m2"],
        hull_perimeter=md["hull"]["perimeter_m"],
    )


def main():
    out_path = Path(sys.argv[1])
    t0 = time.perf_counter()
    sc = selfcheck()
    print("selfcheck", json.dumps(sc))
    sp = specs()
    with ProcessPoolExecutor(max_workers=min(len(sp), max(1, (os.cpu_count() or 4) - 2))) as ex:
        res = list(ex.map(job, sp))
    P0 = {
        k: dict(
            pitch_deg=SETS[k]["crawler_settle_P0"]["pitch_deg"],
            z0_mm=SETS[k]["crawler_settle_P0"]["z0_mm"],
        )
        for k in ("J1", "J2", "S1", "G1")
    }
    by = {(r["soil"], r["case"]): r for r in res}
    summary = {}
    for soil in ("J1", "J2", "S1", "G1"):
        k, c = track_values(soil)
        summary[soil] = dict(track_anchor=dict(k_N_m=k, c_N_s_m=c))
        for label, pre in (("t5s", ""), ("t20s", "long20_")):
            b = by[(soil, pre + "base_4cm")]
            rel = {}
            for (s2, case), r in by.items():
                if s2 != soil or case == pre + "base_4cm":
                    continue
                if (pre and not case.startswith(pre)) or (not pre and case.startswith("long20_")):
                    continue
                rel[case[len(pre) :]] = dict(
                    pitch_rel=r["pitch_deg"] / b["pitch_deg"] - 1,
                    z0_rel=r["z0_mm"] / b["z0_mm"] - 1,
                    pitch_abs_deg=r["pitch_deg"] - b["pitch_deg"],
                    z0_abs_mm=r["z0_mm"] - b["z0_mm"],
                )
            num = [rel[cc] for cc in rel if cc in ("unc_dt_half", "unc_ramp_lead_1step")]
            mf = [
                rel[cc]
                for cc in rel
                if cc
                in (
                    "mf_anchor_nolag_4cm",
                    "b_contact_4cm",
                    "unc_track_k_x2",
                    "unc_track_k_x0p5",
                    "unc_dt_half",
                )
            ]
            summary[soil].setdefault("model_form_spread", {})[label] = dict(
                cases=[
                    "mf_anchor_nolag_4cm",
                    "b_contact_4cm",
                    "unc_track_k_x2",
                    "unc_track_k_x0p5",
                    "unc_dt_half",
                ],
                pitch_rel_max=max(abs(u["pitch_rel"]) for u in mf),
                z0_rel_max=max(abs(u["z0_rel"]) for u in mf),
                pitch_abs_max_deg=max(abs(u["pitch_abs_deg"]) for u in mf),
                z0_abs_max_mm=max(abs(u["z0_abs_mm"]) for u in mf),
            )
            g2 = by[(soil, pre + "grid_2cm")]
            summary[soil][label] = dict(
                window_s=[b["opts"].get("t_end", 5.0) - 1.0, b["opts"].get("t_end", 5.0)],
                P2b_compare_4cm=dict(
                    pitch_deg=b["pitch_deg"],
                    z0_mm=b["z0_mm"],
                    pitch_pp_deg=b["pitch_pp_deg"],
                    Fn_over_W=b["Fn_over_W"],
                    start_rise_max_mm=b["start_rise_max_mm"],
                    start_rise_t_s=b["start_rise_t_s"],
                ),
                P2e_replica_2cm=dict(
                    pitch_deg=g2["pitch_deg"],
                    z0_mm=g2["z0_mm"],
                    pitch_rel=rel["grid_2cm"]["pitch_rel"],
                    z0_rel=rel["grid_2cm"]["z0_rel"],
                ),
                P2f_vs_P0=dict(
                    pitch_rel=b["pitch_deg"] / P0[soil]["pitch_deg"] - 1,
                    z0_rel=b["z0_mm"] / P0[soil]["z0_mm"] - 1,
                ),
                numerical_uncertainty_max=dict(
                    pitch_rel=max(abs(u["pitch_rel"]) for u in num),
                    z0_rel=max(abs(u["z0_rel"]) for u in num),
                )
                if num
                else None,
                rel_to_base=rel,
            )
        tr = by[(soil, "base_4cm")]
        summary[soil]["Kc_oob_over_Kphi"] = (
            SETS[soil]["chrono"]["Kc"] * tr["hull"]["oob_1_m"] / SETS[soil]["chrono"]["Kphi"]
        )
        summary[soil]["hull_4cm"] = tr["hull"]
        print(
            soil,
            json.dumps(
                {
                    lab: {k2: v for k2, v in summary[soil][lab].items() if k2 != "rel_to_base"}
                    for lab in ("t5s", "t20s")
                }
            ),
        )
    doc = dict(
        meta=dict(
            script="04_scripts/01_dynamics/s9_crawler_replica_kcb.py",
            doc="dynamics_model.md 5.34.13 supplement (rev. 49)",
            frame="body x forward, z up; pitch > 0 nose down; z0 = body-origin z change [mm]",
            gravity_m_s2=[0, 0, -G],
            load="Poly345 3 s + hold 2 s, judged on mean of last 1 s",
            dt_s=1e-4,
            phase="Chrono lattice (i h, j h), plane origin (0, 0)",
            b_rule="oob = perimeter / (2 area) of the hull of the ray-hit nodes of one track "
            "(SCMTerrain.cpp:1316-1374; test up 0.1 m, down 0.5 m defaults, :392)",
            mass_kg=float(p0.body("top").mass),
            auger="top",
            k_rollers_N_m=K_ROLLERS,
            wall_s=time.perf_counter() - t0,
        ),
        selfcheck=sc,
        P0=P0,
        summary=summary,
        runs=res,
    )
    out_path.write_text(json.dumps(doc, indent=1), "utf-8")
    print("wrote", out_path, "wall", time.perf_counter() - t0)


if __name__ == "__main__":
    main()
