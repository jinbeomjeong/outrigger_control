"""Independent check of the V14 RL+ stroke-end stop question (dynamics_model.md 5.20.8).

Independent of l2b_reference.SlopeSystem / piecewise_path: incremental stepping (dlam = 1e-3 mm) with
dyn_model.static_slope_10dof as the linear solver, own rod-side state tracking, own piston-position bookkeeping.
Piston position s_p = ext + F_oil / k_out (outer compression rod + frame + concrete in series).
Optional mechanical stop s_p <= s_max: the leg at the stop carries further changes through k_out only (oil frozen).
SI units, body frame x fwd y left z up, compression +, legs FL FR RL RR.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dyn_model as dm  # noqa: E402
import l1r_reference as l1r  # noqa: E402
import l2b_reference as l2  # noqa: E402  (only levelled_extension / max_slope geometry)
import numpy as np  # noqa: E402

p = dm.load_params()
geo = dm.geometry_from_params(p)
lp = l1r.leg_parameters(p, geo)
body = dm.body_from_params(p, "top")
F_MIN = float(p["control"]["F_min_cylinder_N"])
SMAX = geo.stroke
SMEAS = float(p["sensors"]["stroke"]["measurable_max_m"])
CLR = dm.ASSUMPTIONS["crawler_clearance_m"]
KC = 1e13
beta, A_p, A_ann, L0h, k_out = lp["beta"], lp["A_p"], lp["A_ann"], lp["L0h"], lp["k_out"]
p_r0, p_fl = lp["p_r0_ext"], lp["p_floor_g"]
IT = 2  # RL


def run(pitch, roll, L0r, stop, dlam=1e-6, lam_max=20e-3, col="sref"):
    ext = l2.levelled_extension(geo, roll, pitch, CLR)
    kh0 = beta * A_p / (L0h + ext); s_col = ext
    if col != "sref":
        F_s = dm.static_slope_10dof(body, geo, ext, dm.series(kh0, k_out), KC, lp["kt"], pitch, roll)["F_cyl"]
        s_col = ext - F_s / (dm.series(kh0, k_out) if col == "rod" else kh0)
    kh = beta * A_p / (L0h + s_col)
    kr = beta * A_ann / (SMAX - s_col + L0r)
    k2 = dm.series(kh0, k_out)
    s0 = dm.static_slope_10dof(body, geo, ext, k2, KC, lp["kt"], pitch, roll)
    F, N = s0["F_cyl"].copy(), s0["N"].copy()
    sp0 = ext + F / k_out
    st = ["LOCK", "LOCK", "MOVE", "LOCK"]
    dF_lock = np.zeros(4)
    x = np.zeros(4)  # piston travel toward extension (stop side) since locking [m]
    at_stop = [False] * 4
    ev = {}
    lam = 0.0
    xmax = np.zeros(4)
    while lam < lam_max:
        ko = np.empty(4)
        for i in range(4):
            if st[i] == "MOVE":
                ko[i] = k2[i]
            elif at_stop[i]:
                ko[i] = k_out[i]
            elif st[i] == "LOCK":
                ko[i] = dm.series(kh[i] + kr[i], k_out[i])
            else:  # KNEE
                ko[i] = k2[i]
        d = np.zeros(4); d[IT] = dlam
        a = dm.static_slope_10dof(body, geo, ext, ko, KC, lp["kt"], pitch, roll, delta=d)
        b = dm.static_slope_10dof(body, geo, ext, ko, KC, lp["kt"], pitch, roll)
        dF, dN = a["F_cyl"] - b["F_cyl"], a["N"] - b["N"]
        F += dF; N += dN; lam += dlam
        for i in range(4):
            if st[i] == "MOVE" or at_stop[i]:
                continue
            k_oil = kh[i] + kr[i] if st[i] == "LOCK" else kh[i]
            x[i] += -dF[i] / k_oil
            dF_lock[i] += dF[i]
            if st[i] == "LOCK":
                pr = p_r0[i] - kr[i] / (kh[i] + kr[i]) * dF_lock[i] / A_ann[i]
                if pr <= p_fl:
                    st[i] = "KNEE"
            if stop and sp0[i] + x[i] >= SMAX:
                at_stop[i] = True
                ev.setdefault(f"stop_{dm.LEG_NAMES[i]}_mm", lam * 1e3)
        xmax = np.maximum(xmax, x)
        for i in range(4):
            if F[i] <= F_MIN and "F_min" not in ev:
                ev["F_min"] = (lam * 1e3, dm.LEG_NAMES[i], x.copy())
            if N[i] <= 0 and "lift" not in ev:
                ev["lift"] = (lam * 1e3, dm.LEG_NAMES[i], x.copy())
        if "lift" in ev:
            break
    room_geo = (SMAX - ext) * 1e3
    room_true = (SMAX - sp0) * 1e3
    room_model = (SMAX - (ext - s0["F_cyl"] / kh0)) * 1e3
    kL = dm.series(kh + kr, k_out)
    M, K, C, labels, _ = dm.model_10dof(body, geo, ext, ko=kL, kc=np.full(4, KC), kh=lp["kt"], co=lp["cn"], cc=np.zeros(4), ch=lp["ct"])
    f6 = dm.modal(M, K, labels)[1][:6]
    return dict(ext=ext, F0=s0["F_cyl"], room_geo_mm=room_geo, room_piston_mm=room_true, room_model_piston_mm=room_model, f6=np.asarray(f6), s_col=s_col,
                Fmin_mm=ev["F_min"][0], Fmin_leg=ev["F_min"][1], lift_mm=ev["lift"][0], lift_leg=ev["lift"][1],
                x_at_Fmin_mm=ev["F_min"][2] * 1e3, x_at_lift_mm=ev["lift"][2] * 1e3,
                stop_events={k: v for k, v in ev.items() if k.startswith("stop")})


out = {}
cases = {}
for name, dirn in (("pitch+", 0), ("roll+", 90), ("diag45", 45)):
    s70 = l2.max_slope(geo, dirn, CLR) * 0.999
    s69 = l2.max_slope(geo, dirn, CLR, SMEAS) * 0.999
    cases[name] = (dirn, s70, s69)
out["slopes_deg"] = {k: {"stroke_0.70_x0.999": v[1], "sensor_0.6948_x0.999": v[2]} for k, v in cases.items()}

def fmt(res):
    return {k: (np.round(v, 4).tolist() if isinstance(v, np.ndarray) else (round(v, 4) if isinstance(v, float) else v))
            for k, v in res.items()}

for name, (dirn, s70, s69) in cases.items():
    for tag, s in (("0.70", s70), ("0.6948", s69)):
        ro, pi = s * math.sin(math.radians(dirn)), s * math.cos(math.radians(dirn))
        for col in ("sref", "rod", "piston"):
            key = f"{name} {tag} ({s:.4f} deg) col={col}"
            out[key] = fmt(run(pi, ro, 0.05, False, col=col))
            o = out[key]
            print(key, "Fmin", o["Fmin_mm"], o["Fmin_leg"], "lift", o["lift_mm"], "f6", o["f6"],
                  "room_model", o["room_model_piston_mm"], "x_lift", o["x_at_lift_mm"], "F0", o["F0"], flush=True)

with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)
