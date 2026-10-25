"""S9 P1 / P2 dynamics judgement support values (dynamics_model.md rev. 50, 5.35).

Independent checks behind the rev. 50 verdicts; reads the cad batch outputs (07_results/S9/...)
and the replica modules, writes one JSON:

  (A) Crawler settle: the Kc/b replica (s9_crawler_replica_kcb.simulate) re-run with the node
      hit height rounded to float32 in world coordinates (Bullet single-precision ray test) and
      with a temporary settle dashpot (test of a procedure change). Shows that the start rise
      and the settled state of n << 1 soils are set by the first-contact penetration s_1
      (sub-micron), because the Chrono SCM plastic correction sets sigma = Bekker(s) even when
      that exceeds the elastic try (SCMTerrain.cpp:1430-1450); for
      s < s_x = (k_eq / K)^(1 / (1 - n)) the virgin branch is stiffer than the elastic branch.
  (B) P1-V16 (J1, J2): 1-DoF heave replica with the same load-step schedule and loaded mass N / g
      (runner single-pad model), Chrono node law, f64 and f32 hit height.
  (C) P1-L5: slope-settle drift split into rigid rotation and track-point slip (window means over
      whole numbers of 1 s windows to cancel the 0.5 - 0.7 Hz rocking).
  (D) G1 middle / bottom auger P2-b comparison values (same-phase replica).

Frame: body x forward, z up; pitch > 0 nose down; z0 = body-origin z change [mm]; gravity
(0, 0, -9.80665) m/s^2; SI unless the key says mm / deg.

Usage (dynamics-dev, activated):
  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/s9_p1p2_judge_rev50.py <out.json>
"""

from __future__ import annotations

import inspect
import json
import math
import sys
import textwrap
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

WT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WT / "04_scripts" / "01_dynamics"))
import run_pad_bekker_p0 as p0  # noqa: E402
import s9_crawler_replica_kcb as kcb  # noqa: E402

S9 = WT / "07_results" / "S9"
P2_BATCH = S9 / "batch_P2_20261026_040423"
V16_BATCH = S9 / "batch_P1_V16_20261026_032113"
L_BATCH = S9 / "batch_P1_L_20261026_034511"
V16_SUMMARY = WT / "06_analysis" / "01_chrono" / "19_S9" / "s9_P1_V16_summary.json"
SETS = json.load(open(WT / "02_params" / "scm_soil_sets.json", encoding="utf-8"))["sets"]


# ---------------------------------------------------------------- (A) crawler settle variants
def _patched_simulate():
    """kcb.simulate with (i) optional float32 world hit height, (ii) optional settle dashpot
    CD [N s/m] on surge / heave and CD * (1.3 m)^2 on pitch, faded linearly to 0 over [T0, T1]."""
    src = textwrap.dedent(inspect.getsource(kcb.simulate))
    old = "        sink = p0.Z_SURF - zw\n"
    new = "        sink = p0.Z_SURF - (zw.astype(np.float32).astype(np.float64) if Q32 else zw)\n"
    oldv = "        vz += dt * (Fz / m - G * gf)\n        om += dt * My / Iyy\n"
    newv = (
        "        cdf = CD * min(1.0, max(0.0, (T1 - t) / (T1 - T0)))\n"
        "        vz += dt * (Fz / m - G * gf - MZ * cdf * vz / m)\n"
        "        om += dt * (My - MT * cdf * 1.69 * om) / Iyy\n"
        "        vx -= dt * MX * cdf * vx / m\n"
    )
    assert src.count(old) == 1 and src.count(oldv) == 1
    src = src.replace(old, new).replace(oldv, newv)
    src = src.replace(
        "def simulate(\n",
        "def simulate_v(\n    Q32,\n    CD,\n    T0,\n    T1,\n    MX,\n    MZ,\n    MT,\n",
        1,
    )
    src = src.replace("simulate.last_anchor_events", "kcb.simulate.last_anchor_events")
    ns = dict(kcb.__dict__)
    ns["kcb"] = kcb
    exec(compile(src, "simulate_v", "exec"), ns)
    return ns["simulate_v"]


def crawler_job(spec):
    soil, tag, q32, cd, t_end, mask = spec
    sim = _patched_simulate()
    md = kcb.build(soil, 0.04, kcb.CH)
    mx, mz, mt = (1.0 if c in mask else 0.0 for c in "xzt")
    out, _ = sim(q32, cd, 3.0, 5.0, mx, mz, mt, md, t_end=t_end)
    t, th, z, Fz = out[:, 0], out[:, 1], out[:, 3] * 1e3, out[:, 4]
    early = t <= 5.0 + 1e-9
    sel = t > t_end - 1.0 + 1e-9
    return dict(
        soil=soil,
        case=tag,
        float32_hit=q32,
        settle_dashpot_N_s_m=cd,
        dashpot_dofs=mask if cd > 0 else "",
        t_end_s=t_end,
        start_rise_max_mm=float(z[early].max()),
        start_rise_t_s=float(t[early][np.argmax(z[early])]),
        pitch_deg=float(th[sel].mean()),
        z0_mm=float(z[sel].mean()),
        pitch_pp_deg=float(np.ptp(th[sel])),
        Fn_over_W=float(Fz[sel].mean() / (md["mass"] * kcb.G)),
    )


def crawler_specs():
    """(soil, tag, float32 hit, dashpot c [N s/m], t_end [s], damped DOFs x / z / t).
    Dashpot on, faded 3 -> 5 s. "xzt" (surge too) changes the G1 / S1 state (anchor path) and is
    kept only as the rejected variant; "zt" (heave + pitch) is the proposed settle procedure."""
    out = []
    for soil in ("J1", "J2", "G1", "S1"):
        for t_end in (5.0, 20.0):
            out.append((soil, f"f64_t{t_end:g}", False, 0.0, t_end, ""))
            out.append((soil, f"f32_t{t_end:g}", True, 0.0, t_end, ""))
        for mask in ("xzt", "zt", "z"):
            out.append((soil, f"f64_dp2e6_{mask}_t8", False, 2.0e6, 8.0, mask))
            out.append((soil, f"f32_dp2e6_{mask}_t8", True, 2.0e6, 8.0, mask))
    return out


def chrono_crawler(case_dir: Path, t_end: float):
    d = np.load(case_dir / "series.npz")
    t = d["t_s"]
    z = (d["body_pos_m"][:, 2] - d["body_pos_m"][0, 2]) * 1e3
    th = d["roll_pitch_deg"][:, 1]
    sel = t > t_end - 1.0 + 1e-9
    fc = d["scm_crawler_normal_N"]
    return dict(
        case=case_dir.name,
        first_crawler_force_t_s=float(t[np.argmax(fc > 0)]),
        start_rise_max_mm=float(z[t <= 5.0 + 1e-9].max()),
        start_rise_t_s=float(t[np.argmax(z[t <= 5.0 + 1e-9])]),
        up_speed_0p1_0p3_m_s=float(
            (z[np.argmin(abs(t - 0.3))] - z[np.argmin(abs(t - 0.1))]) / 0.2e3
        ),
        pitch_deg=float(th[sel].mean()),
        z0_mm=float(z[sel].mean()),
        pitch_pp_deg=float(np.ptp(th[sel])),
    )


def s_x_mm():
    """Sinkage below which the virgin Bekker pressure exceeds the elastic try K s (n < 1)."""
    out = {}
    for soil in ("J1", "J2", "S1"):
        s = SETS[soil]["chrono"]
        row = {}
        for lab, b in (
            ("pad_rear_b0.1306", 0.130579),
            ("pad_front_b0.1714", 0.171400),
            ("crawler_b0.3771", 0.3771),
        ):
            keq = s["Kc"] / b + s["Kphi"]
            row[lab] = 1e3 * (keq / s["elastic_K"]) ** (1.0 / (1.0 - s["n"]))
        out[soil] = row
    return out


# ---------------------------------------------------------------- (B) V16 1-DoF replica
def v16_replica(case: str, q32: bool):
    r = json.loads((V16_BATCH / case / "result.json").read_text("utf-8"))
    summ = json.loads(V16_SUMMARY.read_text("utf-8"))
    row0 = next(x for x in summ["rows"] if x["case"] == case)
    sc = r["load_steps"]["schedule"]
    soil = r["meta"]["scm"]["soil"]["chrono"]
    n_h, b = row0["levels"][-1]["n_contact"], row0["levels"][-1]["b_hull_m"]
    h = r["args"]["grid"]
    A = n_h * h * h
    leg = r["args"].get("leg", "RL")
    n_full = r["meta"]["scm"]["soil"]["design_loads_N"][["FL", "FR", "RL", "RR"].index(leg)]
    G = 9.80665
    m = n_full / G
    K, Kphi, Kc, n, R = soil["elastic_K"], soil["Kphi"], soil["Kc"], soil["n"], soil["damping_R"]
    coef = Kc / b + Kphi
    z0w = -1.0469

    def poly(u):
        u = min(max(u, 0.0), 1.0)
        return 10 * u**3 - 15 * u**4 + 6 * u**5

    def factor(t):
        for row in sc:
            if t < row["t_hold_start_s"]:
                u = poly((t - row["t_ramp_start_s"]) / row["ramp_s"])
                return row["from_factor"] + (row["factor"] - row["from_factor"]) * u
            if t < row["t_hold_end_s"]:
                return row["factor"]
        return sc[-1]["factor"]

    dt = 1e-4
    z = v = sp = sy = 0.0
    marks = {round(row["t_hold_end_s"] / dt): row for row in sc}
    levels = []
    for k in range(int(round(sc[-1]["t_hold_end_s"] / dt))):
        t = k * dt
        zw = z0w + z
        if q32:
            zw = float(np.float32(zw))
        s = z0w - zw
        sig = K * (s - sp)
        F = 0.0
        if sig > 0:
            if sig > sy:
                sig = coef * max(s, 0.0) ** n
                sy = sig
                sp = s - sig / K
            sig += -v * R
            F = sig * A
        v += dt * (F / m - G * factor(t))
        z += dt * v
        if (k + 1) in marks:
            row = marks[k + 1]
            ch = row0["levels"][row["level"]]["node_sinkage_mm"]
            levels.append(
                dict(
                    level=row["level"],
                    factor=row["factor"],
                    unloading=row["unloading"],
                    replica_sinkage_mm=-z * 1e3,
                    chrono_node_sinkage_mm=ch,
                    chrono_minus_replica_mm=ch + z * 1e3,
                    rel=(ch / (-z * 1e3) - 1.0) if abs(z) > 1e-6 else None,
                )
            )
    return dict(case=case, float32_hit=q32, mass_kg=m, A_m2=A, b_m=b, levels=levels)


# ---------------------------------------------------------------- (C) L5 split
def l5_split(case: str, slope_deg=3.5):
    d = np.load(L_BATCH / case / "series.npz")
    a = math.radians(slope_deg)
    t = d["t_s"]
    pos = d["body_pos_m"]
    th = np.radians(d["roll_pitch_deg"][:, 1])
    xtr, ztr = kcb.rr.X_TRACK, kcb.rr.Z_TRACK
    px = pos[:, 0] + xtr * np.cos(th) + ztr * np.sin(th)
    pz = pos[:, 2] - xtr * np.sin(th) + ztr * np.cos(th)
    tin = px * math.cos(a) - pz * math.sin(a)
    oin = pos[:, 0] * math.cos(a) - pos[:, 2] * math.sin(a)

    def wm(x, t0, t1):
        s = (t > t0 + 1e-9) & (t <= t1 + 1e-9)
        return float(x[s].mean())

    i0, i1 = int(np.argmin(abs(t - 5.0))), int(np.argmin(abs(t - 15.0)))
    sel = t > 5.0
    x = np.degrees(th[sel]) - np.degrees(th[sel]).mean()
    f = np.fft.rfftfreq(len(x), float(np.median(np.diff(t))))
    X = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    pp2 = [float(np.ptp(np.degrees(th[(t > s0) & (t <= s0 + 2)]))) for s0 in np.arange(5, 14.99, 2)]
    fpk = float(f[1:][np.argmax(X[1:])])
    zeta = (
        math.log(pp2[0] / pp2[-1]) / (2 * math.pi * fpk * 2 * (len(pp2) - 1)) if fpk > 0 else None
    )
    return dict(
        case=case,
        origin_in_plane_endpoints_mm=float(oin[i1] - oin[i0]) * 1e3,
        track_point_in_plane_endpoints_mm=float(tin[i1] - tin[i0]) * 1e3,
        pitch_change_endpoints_deg=float(np.degrees(th[i1] - th[i0])),
        track_point_in_plane_4s_means_mm=(wm(tin, 11, 15) - wm(tin, 5, 9)) * 1e3,
        pitch_change_4s_means_deg=float(np.degrees(wm(th, 11, 15) - wm(th, 5, 9))),
        rocking_peak_Hz=fpk,
        pitch_pp_per_2s_deg=pp2,
        rocking_zeta_from_pp_decay=zeta,
    )


# ---------------------------------------------------------------- (D) G1 levels
def g1_levels():
    res = {}
    for lev in ("top", "middle", "bottom"):
        md = kcb.build("G1", 0.04, kcb.CH)
        b = p0.body(lev)
        md.update(mass=b.mass, com=b.com, Iyy=b.inertia[1, 1])
        out, oob = kcb.simulate(md, t_end=5.0)
        r = kcb.summarise(md, out, oob)
        res[lev] = dict(pitch_deg=r["pitch_deg"], z0_mm=r["z0_mm"], pitch_pp_deg=r["pitch_pp_deg"])
    return res


def main():
    out_path = Path(sys.argv[1])
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=14) as ex:
        crawler = list(ex.map(crawler_job, crawler_specs()))
        v16 = list(
            ex.map(
                v16_replica,
                ["V16_J1_B_RL_1cm", "V16_J1_B_FL_1cm", "V16bp_J2_B_RL_1cm"] * 2,
                [False] * 3 + [True] * 3,
            )
        )
    chrono = {
        "J1_5s": chrono_crawler(P2_BATCH / "P2-1_J1_top_M14s", 5.0),
        "J2_5s": chrono_crawler(P2_BATCH / "P2-1_J2_top_M14s", 5.0),
    }
    b2 = S9 / "batch_P2B2_20s_20261026"
    for soil in ("J1", "J2"):
        c = b2 / f"P2B2_{soil}_top_M14s_20s"
        if (c / "series.npz").exists():
            chrono[f"{soil}_20s"] = chrono_crawler(c, 20.0)
    doc = dict(
        meta=dict(
            script="04_scripts/01_dynamics/s9_p1p2_judge_rev50.py",
            doc="dynamics_model.md rev. 50, 5.35",
            frame="body x forward, z up; pitch > 0 nose down; z0 = body-origin z change [mm]",
            gravity_m_s2=[0, 0, -9.80665],
            dt_s=1e-4,
            wall_s=None,
        ),
        s_x_mm=s_x_mm(),
        crawler_replica_variants=crawler,
        crawler_chrono=chrono,
        v16_replica=v16,
        l5=[l5_split("L5_G1_M14s_pitch3.5"), l5_split("L5_J1_M14s_pitch3.5")],
        g1_levels_replica=g1_levels(),
    )
    doc["meta"]["wall_s"] = time.perf_counter() - t0
    out_path.write_text(json.dumps(doc, indent=1), "utf-8")
    print("wrote", out_path, "wall", doc["meta"]["wall_s"])


if __name__ == "__main__":
    main()
