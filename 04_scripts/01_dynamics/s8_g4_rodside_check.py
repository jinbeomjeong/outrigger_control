"""D-S8-3: why the reduced control harness G4 minimum is 5-6 kN below Chrono (dynamics_model.md rev. 39).

Question (s6_control_spec.md rev. 39, 200.2 / 209.3): the S8 pre-check harness (reduced 6-DoF FlexPlant, project C2
R8 preset with_10hz_d1, valve lag 0.1 s, IMU 10 ms) gives G4 (RR sink 11.5 mm / 2 s at READY + 5 s, flat, top)
minimum true cylinder force 4.9-5.5 kN at F_s 0, Chrono bundle C rerun (L1-R) 10.75-12.71 kN. Suspected: no L1-R
rod-side spring in the harness.

Test: the same harness, plant subclass RodSidePlant adds the L1-R rod-side law (dynamics_model.md 5.12 / 5.20.2,
oil-only form) to the harness oil spring, armed when the event branch starts (all legs locked at rest):
  locked:  G = k_h c + Gr,  Gr = Gr_lock + k_r min(c - c_lock, dc_knee),  dc_knee = (p_r0 - p_floor) A_ann / k_r
  moving:  Gr = R0 exp(-(t - t_rel) / tau_v)  (release decay, R0 = Gr at release)
  lock when |u_applied| <= eps (YAML actuator.rod_side.lock_eps_m_s), p_r0 = 2 bar g after an extension, YAML
  p_r0_after_retract after a retraction; k_h = harness k_oil(e_op), k_r = beta A_ann / (stroke - e_op + L0r) (L1-R
  freezes both at e_op, Q-D7).
Implementation: Gr enters the harness kernel as an s_ref shift Gr / k_h for one 5e-4 s step (explicit, like the
harness oil spring); the pressure reading is the net oil force (two sensors, R6-P) = k_h (s_ref - x) + Gr.
The seal friction (harness, parallel to the whole oil force) is unchanged.
Cases: flat, top, F_s {0, 4, 8} kN, judge {pressure, combined}, G4 start phase {0, 0.025, 0.05, 0.075} s,
rod side {off, on}. Metrics as the pre-check: period minimum of the true cylinder force (1 ms chunks), lift time.
Run: conda run -n dynamics-dev python -I 04_scripts/01_dynamics/s8_g4_rodside_check.py [workers]
Writes 06_analysis/00_dynamics/s8_g4_rodside_check.json. Deterministic (no sensor noise).
"""
from __future__ import annotations

import copy
import json
import math
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("NUMBA_NUM_THREADS", "1")

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "06_analysis" / "00_dynamics" / ("s8_g4_rodside_check" + ("_pr0_retract" if os.environ.get("S8_ROD_P0") == "ret" else "") + ".json")
FS_KN = (0.0, 4.0, 8.0)
JUDGES = ("pressure", "combined")
PHASES = (0.0, 0.025, 0.05, 0.075)
SINKS = ("stair_10Hz", "smooth_1ms", "poly345_1ms")   # stair = pre-check harness (offset once per control period); poly345 = Chrono ChFunctionPoly345 (ground_settlement.py)
EVENT = (3, 0.0115, 2.0)          # RR, 11.5 mm, 2 s (G4)
EVENT_DELAY_S = 5.0
EVENT_RUN_S = 20.0
BASE_LIMIT_S = 170.0


def _setup_path():
    for p in (ROOT / "03_src", ROOT / "04_scripts" / "03_control" / "r8d1", ROOT / "04_scripts" / "03_control",
              HERE):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


def _imports():
    _setup_path()
    import c2py_r8d1_closed_loop as cl  # noqa: E402
    from outrigger_sim.control.c2 import C2Controller, C2Phase, ContactJudge
    from outrigger_sim.signals import Measurements
    return cl, C2Controller, C2Phase, ContactJudge, Measurements


def make_plant_class(cl):
    import dyn_model as dm
    import l2b_reference as l2b
    base = cl.rmf.FlexPlant

    class RodSidePlant(base):
        """FlexPlant + L1-R rod-side law (module docstring); armed by arm()."""

        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            p = dm.load_params(); geo = dm.geometry_from_params(p)
            lp = l2b.leg_parameters(p, geo)
            e_op = np.zeros(4) + np.asarray(lp["e_op"], float)
            self.kh = np.asarray(self.ko, float).copy()
            kh_ref = lp["k_h_f"](e_op)
            if np.abs(self.kh / kh_ref - 1).max() > 1e-6:
                raise RuntimeError("harness k_oil(e_op) differs from l2b k_h(e_op)")
            self.kr = lp["k_r_f"](e_op)
            self.A_ann = np.asarray(lp["A_ann"], float)
            self.p_ext = np.asarray(lp["p_r0_ext"], float)
            self.p_ret = np.asarray(lp["p_r0_ret"], float)
            self.p_floor = float(lp["p_floor_g"])
            rs = p["actuator"]["rod_side"]
            self.eps = float(rs["lock_eps_m_s"]); self.tau = float(rs["release_tau_s"])
            self.armed = False
            self.Gr = np.zeros(4)
            self.n_lock_events = 0; self.n_release_events = 0
            self.Gr_min = np.zeros(4); self.Gr_max = np.zeros(4)

        def arm(self):
            self.armed = True
            self.locked = np.ones(4, bool)
            c = self.sref - self.x
            self.c_lock = c.copy(); self.Gr_lock = np.zeros(4)
            self.p_r0 = (self.p_ret.copy() if os.environ.get("S8_ROD_P0") == "ret"
                         else self.p_ext.copy())   # READY: legs locked after an extension (sensitivity: retract)
            self.r0 = np.zeros(4); self.t_rel = np.full(4, -1e9)
            self.last_dir = np.ones(4)

        def _rod_force(self, u):
            c = self.sref - self.x
            Gr = np.zeros(4)
            for i in range(4):
                still = abs(u[i]) <= self.eps
                if abs(u[i]) > self.eps:
                    self.last_dir[i] = 1.0 if u[i] > 0 else -1.0
                if self.locked[i] and still:
                    knee = (self.p_r0[i] - self.p_floor) * self.A_ann[i] / self.kr[i]
                    Gr[i] = self.Gr_lock[i] + self.kr[i] * min(c[i] - self.c_lock[i], knee)
                elif self.locked[i] and not still:            # release
                    knee = (self.p_r0[i] - self.p_floor) * self.A_ann[i] / self.kr[i]
                    self.r0[i] = self.Gr_lock[i] + self.kr[i] * min(c[i] - self.c_lock[i], knee)
                    self.t_rel[i] = self.t; self.locked[i] = False; self.n_release_events += 1
                    Gr[i] = self.r0[i]
                elif (not self.locked[i]) and still:        # lock: anchor = current moving value
                    Gr[i] = self.r0[i] * math.exp(-max(self.t - self.t_rel[i], 0.0) / self.tau)
                    self.locked[i] = True; self.c_lock[i] = c[i]; self.Gr_lock[i] = Gr[i]
                    self.p_r0[i] = self.p_ext[i] if self.last_dir[i] > 0 else self.p_ret[i]
                    self.n_lock_events += 1
                else:
                    Gr[i] = self.r0[i] * math.exp(-max(self.t - self.t_rel[i], 0.0) / self.tau)
            self.Gr = Gr
            self.Gr_min = np.minimum(self.Gr_min, Gr); self.Gr_max = np.maximum(self.Gr_max, Gr)
            return Gr

        def step(self, u, nsteps):
            if not self.armed:
                return super().step(u, nsteps)
            u = np.asarray(u, float)
            agg = None
            for _ in range(nsteps):
                Gr = self._rod_force(u)
                shift = Gr / self.kh
                self.sref += shift
                a = super().step(u, 1)
                self.sref -= shift
                if agg is None:
                    agg = a.copy()
                else:
                    agg[0:11] += a[0:11]
                    agg[11:16] = a[11:16]
                    agg[16:20] = np.maximum(agg[16:20], a[16:20])
                    agg[20:24] = np.minimum(agg[20:24], a[20:24])
            self.hist_t = []; self.hist = []
            self.acc[:24] = agg
            return self.acc[:24]

        def pressure(self):
            return self.ko * (self.sref - self.x) + (self.Gr if self.armed else 0.0)

    return RodSidePlant


def period(cl, Measurements, plant, command, valve, head_area, period_s, floor_fn=None):
    lag_steps = round(cl.LAG_CHUNK_S / plant.dt)
    cps = round(cl.IMU_SAMPLE_S / cl.LAG_CHUNK_S)
    nsp = round(period_s / cl.IMU_SAMPLE_S)
    imu, fmin, cmin = [], np.full(4, np.inf), np.full(4, np.inf)
    for _ in range(nsp):
        fsum = np.zeros(3)
        for _ in range(cps):
            if floor_fn is not None:
                floor_fn(plant)
            acc = cl._lagged_step(plant, command, valve, lag_steps)
            fsum += acc[0:3]
            c = np.asarray(acc[11:15], float)
            cmin = np.minimum(cmin, c)
            fmin = np.minimum(fmin, c - plant.Wr)
        imu.append(fsum / (lag_steps * cps))
    m = Measurements(
        t_s=plant.t, specific_force_m_s2=np.mean(imu, axis=0),
        angular_rate_rad_s=np.asarray(plant.w, float),
        head_pressure_Pa=plant.pressure() / head_area,
        stroke_m=np.asarray(plant.sref, float), stroke_corrected_m=np.asarray(plant.x, float),
        imu_specific_force_samples_m_s2=np.array(imu))
    return m, fmin, cmin


def run_base(args):
    fs_kN, judge = args
    cl, C2Controller, C2Phase, ContactJudge, Measurements = _imports()
    cl.rmf.CONFIG.clear(); cl.rpt.RCFG.clear()
    Plant = make_plant_class(cl)
    t0 = time.perf_counter()
    plant = Plant("top", 0.0, 0.0, Fs=fs_kN * 1e3)
    plant.step(np.zeros(4), int(round(cl.rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
    plant.t = 0.0
    cfg = cl.preset_config(ContactJudge(judge), with_imu_samples=True)
    ctrl = C2Controller.from_params(cl.PARAMS, cfg)
    ha = ctrl.geometry.head_area_m2
    Fmin = ctrl.geometry.F_min_N
    cmd, valve = np.zeros(4), np.zeros(4)
    t_ready = None
    while plant.t < BASE_LIMIT_S:
        m, _, _ = period(cl, Measurements, plant, cmd, valve, ha, ctrl.period_s)
        cmd = np.array(ctrl.update(m).leg_speed_m_s)
        if ctrl.phase is C2Phase.READY and t_ready is None:
            t_ready = plant.t
        if t_ready is not None and plant.t >= t_ready + EVENT_DELAY_S - 1e-9:
            break
    out = {"Fs_kN": fs_kN, "judge": judge, "t_ready_s": t_ready, "F_band_kN": ctrl.seal_band_N / 1e3,
           "valve_at_branch_m_s": valve.tolist(), "cmd_at_branch_m_s": cmd.tolist(),
           "true_at_branch_kN": (plant.true_cyl_force() / 1e3).tolist(), "events": []}
    if t_ready is None:
        return out
    for sink in SINKS:
        for rod in (False, True):
            for ph in PHASES:
                pl = copy.deepcopy(plant); ct = copy.deepcopy(ctrl)
                if rod:
                    pl.arm()
                out["events"].append(run_event(cl, C2Phase, Measurements, pl, ct, cmd.copy(), valve.copy(), ha,
                                               Fmin, ph, rod, sink))
    out["wall_s"] = time.perf_counter() - t0
    return out


def run_event(cl, C2Phase, Measurements, plant, ctrl, cmd, valve, ha, Fmin, off, rod, sink):
    t_ev = plant.t + off
    leg, depth, ramp = EVENT
    n0 = len(ctrl.events)
    rows = []
    while plant.t < t_ev + EVENT_RUN_S:
        def floor_fn(pl_):
            tau_ = min(1.0, max(0.0, (pl_.t - t_ev) / ramp))
            pl_.goff[leg] = depth * (tau_ ** 3 * (10 - 15 * tau_ + 6 * tau_ ** 2) if sink == "poly345_1ms" else tau_)
        if sink == "stair_10Hz":
            floor_fn(plant)
        m, fmin, cmin = period(cl, Measurements, plant, cmd, valve, ha, ctrl.period_s,
                               None if sink == "stair_10Hz" else floor_fn)
        P = plant.pressure().copy()
        cmd = np.array(ctrl.update(m).leg_speed_m_s)
        rows.append((plant.t, P, fmin, cmin, str(ctrl.phase), plant.true_cyl_force().copy(),
                     (plant.Gr.copy() if rod else np.zeros(4))))
    t = np.array([r[0] for r in rows]) - t_ev
    P = np.array([r[1] for r in rows]); Ft = np.array([r[2] for r in rows]); C = np.array([r[3] for r in rows])
    Gr = np.array([r[6] for r in rows])
    k = int(np.argmin(Ft[:, leg]))
    ev = [(round(e.t_s - t_ev, 2), e.name) for e in ctrl.events[n0:]][:12]
    first_level = next((x[0] for x in ev if "relevel" in x[1] or "leave" in x[1]), None)
    return {"rod_side": rod, "sink": sink, "phase_s": off,
            "min_true_kN": float(Ft.min() / 1e3), "min_true_leg": int(np.unravel_index(Ft.argmin(), Ft.shape)[1]),
            "t_min_s": float(t[k]), "t_below_Fmin_s": float((Ft.min(axis=1) < Fmin).sum() * 0.1),
            "t_lift_s": float((C.min(axis=1) <= 0.0).sum() * 0.1),
            "RR_true_at_samples_kN (first 2.5 s)": (Ft[: 26, leg] / 1e3).round(2).tolist(),
            "RR_reading_kN (first 2.5 s)": (P[: 26, leg] / 1e3).round(2).tolist(),
            "RR_rod_side_force_kN (first 2.5 s)": (Gr[: 26, leg] / 1e3).round(2).tolist(),
            "controller_events": ev, "first_relevel_s": first_level,
            "rod_lock_events": getattr(plant, "n_lock_events", 0),
            "rod_release_events": getattr(plant, "n_release_events", 0),
            "Gr_range_kN": ([(plant.Gr_min / 1e3).round(2).tolist(), (plant.Gr_max / 1e3).round(2).tolist()]
                            if rod else None)}


def main():
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    t0 = time.perf_counter()
    jobs = [(fs, j) for fs in FS_KN for j in JUDGES]
    if os.environ.get("S8_SMOKE"):
        jobs = [(0.0, "combined")]
    # compile / load the numba kernels in the main process before the spawn pool (numba cache lesson)
    cl = _imports()[0]
    Plant = make_plant_class(cl)
    pl = Plant("top", 0.0, 0.0, Fs=0.0)
    pl.step(np.zeros(4), 2)
    pl.arm(); pl.step(np.zeros(4), 2)
    with Pool(workers) as pool:
        res = pool.map(run_base, jobs, chunksize=1)
    summary = []
    for b in res:
        for e in b["events"]:
            summary.append([b["Fs_kN"], b["judge"], e["sink"], e["rod_side"], e["phase_s"], round(e["min_true_kN"], 2),
                            round(e["t_lift_s"], 2), e["first_relevel_s"]])
    OUT.write_text(json.dumps({"meta": {"script": "04_scripts/01_dynamics/s8_g4_rodside_check.py",
                                        "doc": __doc__.split("\n\n")[1], "wall_s": time.perf_counter() - t0,
                                        "workers": workers, "event": EVENT, "phases": PHASES,
                                        "summary_cols": ["Fs_kN", "judge", "sink", "rod_side", "phase_s", "min_true_kN",
                                                         "t_lift_s", "first_relevel_s"]},
                               "summary": summary, "runs": res}, indent=1, default=float), encoding="utf-8")
    print("wrote", OUT, f"{time.perf_counter() - t0:.1f} s")


if __name__ == "__main__":
    main()
