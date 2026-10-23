"""S6 spec revision 2, part 2: floor-slope estimation (A) crawler model vs (B) touch strokes + IMU.

Part A (analytic, engine independent): outrigger_sim.scenarios.crawler_slope.crawler_slope_pose (the Chrono
stage-2 start, matches the Chrono end within 0.005 deg) for crawler kn x {1/3, 1, 3} (CLAUDE.md sensitivity x3),
levels top / middle / bottom, floors flat, +-3.5, roll 5.5, diag 3, +-3.2, roll 4.4. Error of the nominal map
(fitted at kn x 1, as section 13 of the spec) when the true crawler is kn x 3 or x 1/3.
Part B (reduced 6-DoF closed loop, s6_target_sim.run_tgt by import): at the TOUCH end (all four pads confirmed, the
crawler still carries the load) fit the pad plane in body axes from the leg strokes and combine it with the
attitude to get the absolute floor slope. Stroke sources: 'x' = rod stroke + 0.1 mm noise (= stroke_true /
stroke_corrected), 's' = motor stroke + 0.1 mm noise (no oil correction), 's-P/ko' = motor stroke - pressure/k_oil.
Attitude sources: the controller's 2nd-order filtered IMU (nominal IMU of the reduced model, zero error 0.5 mg) and
the plant truth (separates the IMU part). Also the A5 stroke predictor evaluated at the TOUCH end against the
final levelled stroke, and the pad-plane twist residual.
Conventions: roll > 0 left up, pitch > 0 nose down, floor plane z = -tan(theta_g) x + tan(phi_g) y, body ZYX (yaw 0).
Run: conda run -n dynamics-dev python -I d8x_floor_est.py <project_root> <out_json> [workers]
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control"))
sys.path.insert(0, str(ROOT / "03_src"))
import s6_target_sim as sts  # noqa: E402

DEG = math.pi / 180.0
C_STAR = 0.05


def floor_from_normal(n):
    n = np.asarray(n, float) / np.linalg.norm(n)
    return math.degrees(math.asin(-n[1])), math.degrees(math.atan2(n[0], n[2]))


def body_R(phi, th):
    cp, sp, ct, st = math.cos(phi), math.sin(phi), math.cos(th), math.sin(th)
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    Ry = np.array([[ct, 0, st], [0, 1, 0], [-st, 0, ct]])
    return Ry @ Rx


def plane_est(ctx, ext, phi, th):
    """Pad plane (body) from extensions -> absolute floor (roll, pitch) deg, twist residual mm, coef."""
    z = ctx.zp - ext
    coef, *_ = np.linalg.lstsq(ctx.M, z, rcond=None)
    res = z - ctx.M @ coef
    n_body = np.array([-coef[1], -coef[2], 1.0])
    return floor_from_normal(body_R(phi, th) @ n_body), float(np.max(np.abs(res)) * 1e3), coef


class C2RTf(sts.C2RT):
    """Adds per-period pad-plane relative tilt through the same 2nd-order filter as the attitude (lag cancels)."""

    def update(self, m, t):
        z = self.c.zp - np.asarray(m["x"])
        coef, *_ = np.linalg.lstsq(self.c.M, z, rcond=None)
        rel = np.radians(floor_from_normal([-coef[1], -coef[2], 1.0]))   # floor attitude in body axes
        a = sts.rcc.T_CTRL / sts.rcc.CA["imu_lpf_tau_s"]
        if getattr(self, "rel1", None) is None:
            self.rel1 = rel.copy(); self.relf = rel.copy()
        else:
            self.rel1 += a * (rel - self.rel1); self.relf += a * (self.rel1 - self.relf)
        return super().update(m, t)

    def on_touch(self, m):
        super().on_touch(m)
        import run_mast_flex_c2_check as rmf
        pl = rmf.LAST["plant"]
        c = self.c
        ph_t, th_t = pl.attitude()
        rec = {"t_s": round(float(self.t), 3), "imu_filt_deg": [math.degrees(self.phi_f), math.degrees(self.th_f)],
               "true_att_deg": [math.degrees(ph_t), math.degrees(th_t)],
               "true_floor_deg": list(floor_from_normal(pl.nrm)), "P_kN": (np.asarray(m["P"]) / 1e3).round(2).tolist()}
        srcs = {"x": np.asarray(m["x"]), "s": np.asarray(m["s"]),
                "s-P/ko": np.asarray(m["s"]) - np.asarray(m["P"]) / pl.ko}
        for nm, ext in srcs.items():
            for an, (ph, th) in (("imu", (self.phi_f, self.th_f)), ("true", (ph_t, th_t))):
                g, twist, _ = plane_est(c, ext, ph, th)
                rec[f"floor[{nm},{an}]"] = list(g)
            rec[f"twist_mm[{nm}]"] = twist
        n_rel = body_R(*self.relf) @ np.array([0.0, 0.0, 1.0])
        rec["floor[xfilt,imu]"] = list(floor_from_normal(body_R(self.phi_f, self.th_f) @ n_rel))
        # A5 predictor at TOUCH end (target 0), spec 2.3, motor stroke
        s = np.asarray(m["s"])
        z = c.zp - np.asarray(m["x"])
        coef, *_ = np.linalg.lstsq(c.M, z, rcond=None)
        ck = c.zcb - (coef[0] + c.corners @ coef[1:])
        dphi, dth = -self.phi_f, -self.th_f
        dz = C_STAR - np.min(ck + c.corners[:, 1] * dphi - c.corners[:, 0] * dth)
        rec["a5_pred_mm"] = ((s + dz + c.xy[:, 1] * dphi - c.xy[:, 0] * dth) * 1e3).round(2).tolist()
        self.touch_rec = rec


sts.C2RT = C2RTf
_RUN = sts.run_tgt


def run(case):
    import run_mast_flex_c2_check as rmf
    bias = [0.0, 0.0] if case.get("imu_zero_bias") else [0.5, -0.5]   # reset every case (pool workers are reused)
    sts.rcc.CA["imu_nominal"] = {"bias_mg": bias, "noise_ug_rtHz": 100.0}
    out = _RUN(case)
    ctrl = rmf.LAST.get("ctrl")
    out["touch_rec"] = getattr(ctrl, "touch_rec", None)
    return out


def part_a():
    from outrigger_sim.params import load_params
    from outrigger_sim.scenarios.crawler_slope import crawler_slope_pose
    floors = {"flat": (0, 0), "fdown3.5": (0, 3.5), "fup3.5": (0, -3.5), "roll5.5": (5.5, 0),
              "diag3": (3 / math.sqrt(2), 3 / math.sqrt(2)), "fdown3.2": (0, 3.2), "fup3.2": (0, -3.2),
              "roll4.4": (4.4, 0)}
    base = load_params()
    kn0 = float(base.get("contact.crawler.kn_per_sphere_N_m"))
    out = []
    for lvl in ("top", "middle", "bottom"):
        for sc in (1 / 3, 1.0, 3.0):
            p = load_params(level=lvl, overrides={"contact.crawler.kn_per_sphere_N_m": kn0 * sc})
            for nm, (r, q) in floors.items():
                pose = crawler_slope_pose(p, r, q)
                out.append(dict(level=lvl, kn_scale=sc, floor=nm, floor_deg=[r, q],
                                body_deg=[pose.body_roll_deg, pose.body_pitch_deg],
                                delta_deg=[pose.body_roll_deg - r, pose.body_pitch_deg - q]))
    return out


def cases():
    C = []
    for lvl in ("top", "bottom"):
        for nm, fl in (("flat", (0.0, 0.0)), ("fdown3.5", (0.0, 3.5)), ("fup3.5", (0.0, -3.5)),
                       ("roll5.5", (5.5, 0.0)), ("diag3", (3 / math.sqrt(2), 3 / math.sqrt(2))),
                       ("roll-4.4", (-4.4, 0.0))):
            for zb in (False, True):
                C.append(dict(id=f"{lvl}|{nm}" + ("|bias0" if zb else ""), group="d8x_B", floor_deg=fl,
                              level=lvl, imu_zero_bias=zb,
                              tgt={"target_deg": (0.0, 0.0), "ra_mode": "rel"}, t_hold=10.0))
    return C


def main():
    out_json = Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    t0 = time.time()
    A = part_a()
    print(f"part A {len(A)} poses {time.time() - t0:.1f} s", flush=True)
    import run_c2_timedomain as c2t
    c2t.set_affinity()
    C = cases()
    import multiprocessing as mp
    res = []
    with mp.get_context("spawn").Pool(min(workers, len(C))) as pool:
        for r in pool.imap_unordered(run, C):
            res.append(r)
            print(f"{time.time() - t0:7.1f} s  {r['id']}  {r.get('error', '')}", flush=True)
    order = {c["id"]: i for i, c in enumerate(C)}
    res.sort(key=lambda r: order[r["id"]])
    keep = ("id", "floor_deg", "level", "t_touch_s", "t_crawler_liftoff_s", "t_ready_s", "s_max_seen_mm", "s_final_mm",
            "min_true_cyl_force_kN", "touch_rec", "error")
    out_json.write_text(json.dumps({"partA": A, "partB": [{k: r.get(k) for k in keep} for r in res],
                                    "runtime_s": time.time() - t0}, indent=1, default=float))
    print("written", out_json)


if __name__ == "__main__":
    main()
