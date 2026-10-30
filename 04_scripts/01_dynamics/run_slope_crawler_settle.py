"""A1 slope crawler settle table: P0 crawler-on-soil settle extended with the in-plane gravity component (no Chrono).

Purpose: study (1) "soft soil x floor slope" (extra studies 2026-10-28). The reduced S9 harness
(04_scripts/03_control/s9/s9_soil_closed_loop.py, SoilPads.__init__) uses the FLAT P0 settle only
(pad_bekker_p0_soilsets.json 'settle'). This script gives the settle on a tilted floor for a calibration hook.

Model: run_pad_bekker_p0.Model (5.31.2, imported unchanged; soil sets from run_pad_bekker_p0_soilsets._setup),
  solved in FLOOR axes (x_f, y_f in the floor plane, z_f along the floor normal), legs retracted, virgin soil.
  Gravity in floor axes (floor R_f = Ry(theta_f) Rx(phi_f), as the harness Plant q = q_pitch * q_roll):
      g_f = W (sin th_f, -sin ph_f cos th_f, -cos ph_f cos th_f)
  Normal load N = W cos ph_f cos th_f. The in-plane components act at the COG height h above the soil surface
  (Z_SURF of P0) and are carried by crawler shear in the contact plane (no moment arm there), so the moment
  balance about the contact plane gives the effective COG position
      x_eff = x_c + h tan th_f / cos ph_f,   y_eff = y_c - h tan ph_f
  and the generalized load w = N (1, y_eff, -x_eff) (P0 convention q = [uz, phi, theta], point displacement
  uz + y phi - x theta, roll > 0 left up, pitch > 0 nose down).
  ASSUMPTION: crawler shear capacity is enough (utilisation recorded, Janosi-Hanamoto peak c A + N tan(phi_s));
  no shear-induced sinkage (SCM has none); small settle angles (P0 small-angle kinematics in floor axes).
Output 06_analysis/00_dynamics/slope_crawler_settle.json
Run: conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_slope_crawler_settle.py
Regression: flat top rows must reproduce pad_bekker_p0_soilsets.json settle q (same code path).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import run_pad_bekker_p0 as p0  # noqa: E402
import run_pad_bekker_p0_soilsets as p0s  # noqa: E402
import dyn_model as dm  # noqa: E402

OUT = ROOT / "06_analysis" / "00_dynamics" / "slope_crawler_settle.json"
P0_SETS = ROOT / "06_analysis" / "00_dynamics" / "pad_bekker_p0_soilsets.json"
SOILS = ("rigid", "G1", "J1", "J2", "S1")
LEVELS = ("top", "bottom")
# (roll_deg, pitch_deg) of the floor; (0, 3.5) added for the Chrono P1-L5 comparison
SLOPES = ((0.0, 0.0), (0.0, 3.2), (0.0, -3.2), (4.4, 0.0), (-4.4, 0.0), (2.2, 1.6), (2.2, -1.6),
          (2.7355, 1.7592), (0.0, 3.5))
# extra rows for the study (1) k* grid (coordinator 2026-10-28): top level only, per soil; the rigid rows of the
# same slopes are added for the deltas. Appended after the base grid, so the base rows keep their job order.
_K_GRID = ((0.0, 1.6), (0.0, 2.4), (0.0, 2.8), (2.2, 0.0), (3.3, 0.0), (3.85, 0.0), (1.1, 0.8), (1.65, 1.2),
           (1.925, 1.4))
EXTRA = [(s, "top", sl) for s in ("J1", "J2", "S1") for sl in _K_GRID] + [("G1", "top", (0.0, 2.8))]
# auger middle level (coordinator 2026-10-28, S9 reduced runs at three auger levels): base slopes + k grid
EXTRA += [(s, "middle", sl) for s in ("G1", "J1", "J2", "S1") for sl in SLOPES + _K_GRID]
# B5 out-of-sample comparison (control-expert 2026-10-30): J1/J2 top, pad B. s9_soil_slope.SLOPES_DEG x k 0.625 and
# 0.9375 (nose_down, roll_pos, edge_nd), then roll_neg / nose_up / edge_nu x 0.75. Appended last (job order kept).
_B5_OOS = ((0.0, 2.0), (0.0, 3.0), (2.75, 0.0), (4.125, 0.0), (1.375, 1.0), (2.0625, 1.5),
           (-3.3, 0.0), (0.0, -2.4), (1.65, -1.2))
EXTRA += [(s, "top", sl) for s in ("J1", "J2") for sl in _B5_OOS]
# H9 roll boundary refinement (spec 430.2, 2026-10-30): J1/J2 top, roll_pos / roll_neg (+-4.4, 0) x k
# {0.6, 0.65, 0.7, 0.75, 0.8, 0.875}, rounded as s9_soil_slope._scaled_slope; rows already in the grid are skipped
# by all_cases(). Appended last (job order kept).
_H9 = tuple((round(k * r, 4), 0.0) for r in (4.4, -4.4) for k in (0.6, 0.65, 0.7, 0.75, 0.8, 0.875))
EXTRA += [(s, "top", sl) for s in ("J1", "J2") for sl in _H9 if (s, "top", sl) not in EXTRA]
# --merge: existing hook_harness keys recomputed as the bit-identity regression sample
REGRESSION_KEYS = ("G1|top|0|0", "J1|top|0|3.2", "S1|top|2.7355|1.7592", "J2|bottom|4.4|0", "G1|bottom|-4.4|0",
                   "S1|top|0|3.5")
WORKERS = int(os.environ.get("SLOPE_SETTLE_WORKERS", "6"))


def all_cases():
    """(soil, level, slope) of every row: base grid, then the extra soil rows and their rigid rows."""
    base = [(s, lv, sl) for s in SOILS for lv in LEVELS for sl in SLOPES]
    extra_rigid = sorted({("rigid", lv, sl) for _, lv, sl in EXTRA} - set(base), key=lambda c: (c[1], c[2]))
    return base + [c for c in EXTRA if c not in base] + extra_rigid


def key(soil, level, roll, pitch):
    return f"{soil}|{level}|{roll:g}|{pitch:g}"


def rot_floor(roll_deg, pitch_deg):
    ph, th = math.radians(roll_deg), math.radians(pitch_deg)
    Rx = np.array([[1, 0, 0], [0, math.cos(ph), -math.sin(ph)], [0, math.sin(ph), math.cos(ph)]])
    Ry = np.array([[math.cos(th), 0, math.sin(th)], [0, 1, 0], [-math.sin(th), 0, math.cos(th)]])
    return Ry @ Rx


def euler_zyx(R):
    """roll (x), pitch (y, > 0 nose down) of R = Rz Ry Rx."""
    return math.atan2(R[2, 1], R[2, 2]), math.asin(-R[2, 0])


def _job(args):
    soil, level, roll, pitch = args
    cases, _ = p0s.soil_cases()
    if soil != "rigid":
        name = p0s._setup(soil, cases[soil])
    else:
        name = "rigid"
    m = p0.Model(level, "B", name)
    b = p0.body(level)
    com = np.asarray(b.com, float)
    h = float(com[2] - p0.Z_SURF)
    ph, th = math.radians(roll), math.radians(pitch)
    W = m.W
    N = W * math.cos(ph) * math.cos(th)
    x_eff = com[0] + h * math.tan(th) / math.cos(ph)
    y_eff = com[1] - h * math.tan(ph)
    m.w = N * np.array([1.0, y_eff, -x_eff])
    q = m.settle()
    st = m.state(q, np.zeros(4))
    sc, fc, _, con, bc = m.crawler(q)
    nx = m.nx
    tracks = {}
    sh = p0.SOILS.get(name, {}) if name != "rigid" else {}
    for t, lab in ((0, "left"), (1, "right")):
        sl = slice(t * nx, (t + 1) * nx)
        f = fc[sl]; s = sc[sl]; c = f > 0
        Ft = float(f.sum())
        area = float(c.sum()) * p0.H_GRID ** 2
        row = {"F_N": Ft, "F_over_N": Ft / N, "n_contact_nodes": int(c.sum()), "contact_area_m2": area,
               "sink_max_mm": float(s[c].max() * 1e3) if c.any() else 0.0,
               "sink_mean_mm": float((s[c] * f[c]).sum() / Ft * 1e3) if Ft > 0 else 0.0,
               "cop_x_m": float((m.cx[sl][c] * f[c]).sum() / Ft) if Ft > 0 else None,
               "x_contact_m": [float(m.cx[sl][c].min()), float(m.cx[sl][c].max())] if c.any() else None,
               "bekker_b_m": None if bc is None or bc[0] is None else float(bc[0][t])}
        if sh:
            # in-plane load share per track = its normal share (same tan(phi) on both tracks)
            T = math.hypot(W * math.sin(th), W * math.sin(ph) * math.cos(th)) * Ft / N
            cap = sh["c"] * area + Ft * math.tan(math.radians(sh["phi"]))
            row["shear_T_N"] = T
            row["shear_capacity_N"] = cap
            row["shear_utilisation"] = T / cap if cap > 0 else None
        tracks[lab] = row
    Rf = rot_floor(roll, pitch)
    Rs = rot_floor(math.degrees(q[1]), math.degrees(q[2]))
    r_abs, p_abs = euler_zyx(Rf @ Rs)
    return {"soil": soil, "level": level, "floor_roll_deg": roll, "floor_pitch_deg": pitch,
            "W_N": W, "N_N": N, "com_body_m": com.tolist(), "h_cog_above_surface_m": h,
            "cog_eff_xy_m": [x_eff, y_eff],
            "q_floor": q.tolist(), "uz_mm": q[0] * 1e3, "roll_settle_deg": math.degrees(q[1]),
            "pitch_settle_deg": math.degrees(q[2]),
            "roll_abs_deg": math.degrees(r_abs), "pitch_abs_deg": math.degrees(p_abs),
            "resid_rel": m.settle_resid, "F_crawler_N": st["F_crawler"], "crawler_max_sink_mm": st["crawler_max_sink"] * 1e3,
            "tracks": tracks}


# ----------------------------------------------------------------------------------- stage 2: harness hook
AVG_S = 5.0          # mean window after the harness settle (rocking left by the start pose, about 1.3 Hz)
AVG_DT = 0.05


def _harness_settle(h, cl, level, soil, slope_arg, ref_slope):
    """Harness plant (s9_soil_closed_loop.make_plant) settled on the crawler; means over AVG_S of the
    settle q in the axes of the REFERENCE floor ref_slope (the original soil plane; uz = body origin height
    above it, both planes through the world origin) and of the pad penetration without the SoilPads offset h
    (soil_floor formula, along the plant floor normal)."""
    import dyn_model as dmm
    cl.rmf.CONFIG.clear(); cl.rpt.RCFG.clear()
    plant = h.make_plant(cl, level, soil, "B", 0.0, slope=slope_arg)
    plant.step(np.zeros(4), int(round(cl.rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
    zf = float(dmm.load_params()["ground"]["crawler_bottom_z_m"])
    Rref = rot_floor(*ref_slope)
    n_ref = Rref[:, 2]
    qs, pens, wmax = [], [], 0.0
    nstep = int(round(AVG_DT / plant.dt))
    for _ in range(int(round(AVG_S / AVG_DT))):
        plant.step(np.zeros(4), nstep)
        R = cl.rcc._R(plant.q)
        n = plant.nrm
        dphi, dth = euler_zyx(Rref.T @ R)
        O = plant.r - R @ plant.body.com
        qs.append([float(n_ref @ O) + zf, dphi, dth])
        a_n = float(n @ R[:, 2])
        pens.append([(plant.x[i] - float(n @ (plant.r + R @ plant.pad_rel[i])) / a_n) * a_n for i in range(4)])
        wmax = max(wmax, float(np.abs(plant.w).max()))
    return np.mean(qs, axis=0), np.mean(pens, axis=0), np.ptp(np.array(qs)[:, 2]), wmax


def _hjob(args):
    level, slope, soil, d = args
    sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s9"))
    import s9_soil_closed_loop as h
    cl, _, _ = h._imports()
    roll, pitch = slope
    flat_add = 0.0 if soil == "rigid" else math.degrees(h.P0_SETTLE[soil]["q"][2] - h.P0_SETTLE["rigid"]["q"][2])
    arg = (roll + math.degrees(d[0]), pitch + math.degrees(d[1]) - flat_add)
    q, pen, pp, wmax = _harness_settle(h, cl, level, soil, arg, slope)
    return {"level": level, "slope": slope, "soil": soil, "d": list(d), "q_floor": q.tolist(), "pen_noh_m": pen.tolist(),
            "pitch_pp_rad": float(pp), "w_max_rad_s": wmax}


def harness_stage(rows, only=None):
    """Hook for the harness, calibrated on the harness's OWN rigid crawler (layout D):
    floor tilt += d = q_soil(P0) - q_rigid(harness) (iterated once on the soil plant), pad offsets
    h_i = -gap_i(P0 soil) - pen_noh_i (pad bottom to original soil surface equals the P0 soil settle)."""
    cases = [c for c in all_cases() if c[0] != "rigid"] if only is None else list(only)
    combos = []
    for _, lv, sl in cases:
        if (lv, sl) not in combos:
            combos.append((lv, sl))
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        rig = list(ex.map(_hjob, [(lv, s, "rigid", (0.0, 0.0)) for lv, s in combos]))
    rig = {(o["level"], tuple(o["slope"])): o for o in rig}
    out = {}
    jobs = []
    for s, lv, sl in cases:
        tgt = rows[key(s, lv, *sl)]["q_floor"]
        qr = rig[(lv, sl)]["q_floor"]
        jobs.append((lv, sl, s, (tgt[1] - qr[1], tgt[2] - qr[2])))
    # always two passes per row (the first full run never met the 0.002 deg global break, so every row of it
    # has two passes; a fixed count keeps each row independent of which rows are computed together)
    for it in range(2):
        with ProcessPoolExecutor(max_workers=WORKERS) as ex:
            res = list(ex.map(_hjob, jobs))
        nxt = []
        for o in res:
            sl = tuple(o["slope"]); tgt = rows[key(o["soil"], o["level"], *sl)]["q_floor"]
            err = (tgt[1] - o["q_floor"][1], tgt[2] - o["q_floor"][2])
            out[key(o["soil"], o["level"], *sl)] = (o, err, it)
            nxt.append((o["level"], sl, o["soil"], (o["d"][0] + err[0], o["d"][1] + err[1])))
        jobs = nxt
    hook = {}
    for k, (o, err, it) in out.items():
        tgt = rows[k]["q_floor"]
        gap = (p0.GEO.pad_z_retracted + p0.A_PAD @ np.array(tgt)) - p0.Z_SURF
        hpad = -gap - np.array(o["pen_noh_m"])
        hook[k] = {"floor_roll_add_deg": math.degrees(o["d"][0]), "floor_pitch_add_deg": math.degrees(o["d"][1]),
                   "pad_h_m": hpad.tolist(), "target_q_floor": tgt, "harness_q_floor": o["q_floor"],
                   "residual_roll_deg": math.degrees(err[0]), "residual_pitch_deg": math.degrees(err[1]),
                   "harness_settle_pitch_pp_deg": math.degrees(o["pitch_pp_rad"]),
                   "harness_w_max_deg_s": math.degrees(o["w_max_rad_s"]), "iterations": it + 1,
                   "gap_target_mm": (gap * 1e3).tolist()}
    rigid = {f"rigid|{lv}|{s[0]:g}|{s[1]:g}": {"q_floor": o["q_floor"], "pitch_pp_deg": math.degrees(o["pitch_pp_rad"]),
                                              "w_max_deg_s": math.degrees(o["w_max_rad_s"])}
             for (lv, s), o in rig.items()}
    return hook, rigid


def main():
    t0 = time.perf_counter()
    jobs = [(s, lv, r, p) for s, lv, (r, p) in all_cases()]
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        res = list(ex.map(_job, jobs))
    rows = {key(o["soil"], o["level"], o["floor_roll_deg"], o["floor_pitch_deg"]): o for o in res}
    pad_xy = dm.geometry_from_params(dm.load_params()).pad_xy
    hook = {}
    for s, lv, (r, p) in all_cases():
        if s == "rigid":
            continue
        a, rg = rows[key(s, lv, r, p)], rows[key("rigid", lv, r, p)]
        dphi = a["q_floor"][1] - rg["q_floor"][1]
        dth = a["q_floor"][2] - rg["q_floor"][2]
        duz = a["q_floor"][0] - rg["q_floor"][0]
        hpad = (-duz) + pad_xy[:, 0] * math.tan(dth) - pad_xy[:, 1] * math.tan(dphi)
        hook[key(s, lv, r, p)] = {
            "d_uz_m": duz, "d_roll_rad": dphi, "d_pitch_rad": dth,
            "d_roll_deg": math.degrees(dphi), "d_pitch_deg": math.degrees(dth),
            "pad_h_m": hpad.tolist(),
            "sink_track_mm": {"left": a["tracks"]["left"]["sink_max_mm"], "right": a["tracks"]["right"]["sink_max_mm"]},
            "soil_settle_q_floor": a["q_floor"], "rigid_settle_q_floor": rg["q_floor"]}
    # regression: flat top vs pad_bekker_p0_soilsets settle
    old = json.loads(P0_SETS.read_text(encoding="utf-8"))["paths"]
    reg = {}
    for s in SOILS:
        qo = np.array(old[f"{s}|B|closed"]["settle"]["q"])
        reg[s] = float(np.max(np.abs(np.array(rows[key(s, "top", 0, 0)]["q_floor"]) - qo)))
    out = {"meta": {
        "script": "04_scripts/01_dynamics/run_slope_crawler_settle.py",
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "model": "run_pad_bekker_p0.Model (5.31.2) + in-plane gravity moment (effective COG), floor axes",
        "frames": "floor axes = body axes of a body lying flat on the floor; x fwd, y left, z along the floor normal. "
                  "q_floor = [uz m, phi rad, theta rad], point displacement uz + y phi - x theta; roll > 0 left up, "
                  "pitch > 0 nose down. Floor R_f = Ry(pitch) Rx(roll) (harness Plant convention, floor z = "
                  "-tan(pitch) x + tan(roll) y). Absolute attitude = ZYX of R_f R_settle (gravity-referenced, IMU).",
        "gravity": "(0, 0, -g) world, g from YAML meta.gravity_m_s2",
        "pad_variant": "B (pads not in contact in the settle, A and B give the same rows)",
        "assumptions": ["crawler shear in the contact plane carries W sin(alpha), no moment arm (SCM shear has no "
                        "sinkage coupling)", "shear capacity c A + N tan(phi) per track (recorded only)",
                        "small settle angles in floor axes", "rigid = P0 concrete Winkler crawler (same model, for the delta)"],
        "hook_note": "hook[soil|level|roll|pitch]: harness correction soil - rigid in the SAME model (as the flat "
                     "SoilPads: dtheta = soil - rigid, h = (uz_rig - uz_soil) + x tan dtheta). Extension: "
                     "floor roll += d_roll_deg, floor pitch += d_pitch_deg, SoilPads.h = pad_h_m "
                     "(= -d_uz + x tan d_pitch - y tan d_roll), pads FL FR RL RR.",
        "key_format": "'{soil}|{level}|{roll:g}|{pitch:g}' with the floor roll / pitch in deg, e.g. 'J1|top|2.7355|1.7592'",
        "regression_flat_top_vs_p0_soilsets_maxabs_q": reg,
        "runtime_s": round(time.perf_counter() - t0, 1)},
        "soils": list(SOILS), "levels": list(LEVELS), "slopes_deg": [list(s) for s in SLOPES],
        "pad_xy_m": pad_xy.tolist(), "rows": rows, "hook": hook}
    out["extra_rows"] = [key(s, lv, *sl) for s, lv, sl in EXTRA]
    if "--harness" in sys.argv:
        # numba cache compiled in the main process before the spawn pool (harness kernels)
        _hjob((LEVELS[0], SLOPES[0], "rigid", (0.0, 0.0)))
        if "--merge" in sys.argv:
            # keep the existing harness rows; compute the missing ones + a regression sample of existing ones
            prev = json.loads(OUT.read_text(encoding="utf-8"))
            rt = lambda v: json.loads(json.dumps(v, default=float))  # noqa: E731 (JSON round trip)
            reg_rows = {k: rt(rows[k]) == v for k, v in prev["rows"].items()}
            todo = [c for c in all_cases() if c[0] != "rigid" and key(*c[:2], *c[2]) not in prev["hook_harness"]]
            todo += [c for c in all_cases() if key(c[0], c[1], *c[2]) in REGRESSION_KEYS]
            hh, hr = harness_stage(rows, only=todo)
            reg_h = {k: rt(hh[k]) == prev["hook_harness"][k] for k in REGRESSION_KEYS}
            reg_r = {k: rt(v) == prev["harness_rigid"][k] for k, v in hr.items() if k in prev["harness_rigid"]}
            merged = dict(prev["hook_harness"]); merged.update({k: v for k, v in hh.items() if k not in prev["hook_harness"]})
            mr = dict(prev["harness_rigid"]); mr.update({k: v for k, v in hr.items() if k not in prev["harness_rigid"]})
            hh, hr = merged, mr
            out["meta"]["merge_regression"] = {
                "rows_identical": sum(reg_rows.values()), "rows_compared": len(reg_rows),
                "rows_not_identical": [k for k, v in reg_rows.items() if not v],
                "hook_harness_identical": reg_h, "harness_rigid_identical": reg_r,
                "new_hook_harness_keys": len(hh) - len(prev["hook_harness"])}
            print("merge regression", json.dumps(out["meta"]["merge_regression"]), flush=True)
        else:
            hh, hr = harness_stage(rows)
        out["hook_harness"] = hh
        out["harness_rigid"] = hr
        out["meta"]["hook_harness_note"] = (
            "RECOMMENDED hook. Calibrated on the harness's own rigid crawler (layout D), not on the P0 Winkler "
            "rigid: make_plant(..., slope=(roll + floor_roll_add_deg, pitch + floor_pitch_add_deg)) WITHOUT the "
            "flat P0 pitch add of make_plant (floor_pitch_add_deg already contains it), then SoilPads.h = pad_h_m "
            "(goff = -h). Check: harness settle attitude in the original-floor axes = target_q_floor "
            "(residual_*), pad bottom to original soil surface = P0 soil settle gap (gap_target_mm). "
            f"Means over {AVG_S} s after the harness settle (rocking left by the start pose).")
        out["meta"]["runtime_s"] = round(time.perf_counter() - t0, 1)
    OUT.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    OUT.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print("regression", json.dumps(reg))
    for s in SOILS:
        for lv in LEVELS:
            for (r, p) in SLOPES:
                o = rows[key(s, lv, r, p)]
                print(f"{s:5s} {lv:6s} ({r:7.4f},{p:7.4f}) uz {o['uz_mm']:8.3f} mm  dphi {o['roll_settle_deg']:8.4f}  "
                      f"dth {o['pitch_settle_deg']:8.4f}  abs ({o['roll_abs_deg']:7.4f},{o['pitch_abs_deg']:7.4f})  "
                      f"sinkL {o['tracks']['left']['sink_max_mm']:7.3f} sinkR {o['tracks']['right']['sink_max_mm']:7.3f} "
                      f"util {o['tracks']['left'].get('shear_utilisation') or 0:.3f} h {o['h_cog_above_surface_m']:.3f} "
                      f"res {o['resid_rel']:.1e}")
    print("wrote", OUT, "runtime", out["meta"]["runtime_s"])


if __name__ == "__main__":
    main()
