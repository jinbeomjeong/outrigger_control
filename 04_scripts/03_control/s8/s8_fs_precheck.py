"""S8 pre-check on the reduced plant: seal friction F_s 0/2/4/8 kN, pressure-only vs combined judge.

Spec context: 00_docs/04_control/s6_control_spec.md rev. 39 (S8 plan, 200), rev. 42 (this harness fix, 212).
Engine-free closed loop of the project C2 with the R8-D1 preset (10 Hz, d = 1, valve lag 0.1 s, IMU 10 ms
samples) on the reduced 6-DoF plant (FlexPlant rigid mast, seal friction = Coulomb parallel to the oil spring,
return mapping). Departures as c2py_r8d1_closed_loop.preset_config: no CHECK / zero calibration, target check off,
REANCHOR off; ideal sensors (no noise).

Rev. 42 harness (dynamics_model.md rev. 39, 5.26.6, D-S8-3):
  * floor events are applied on every 1 ms chunk with the Chrono shape z = -depth Poly345((t - t_ev) / ramp)
    (ground_settlement.py / l2b_ground_patch.py); rev. 39 put a linear offset once per control period
    (10 Hz stair, the main cause of the 5-6 kN low G4 minima);
  * the L1-R rod-side law (s8_g4_rodside_check.RodSidePlant) is armed after the crawler settle, before levelling
    (default, as Chrono L1-R / L2b: the probe already sees it); the reading is the net oil force (two sensors,
    R6-P). Arming only at the event branch (dynamics 5.26.6) leaves the probe-measured twist stiffness scale
    (U-R8-8) at 1.17 instead of 1.46 and puts the combined G4 minima 1.3-1.7 kN above Chrono (212.3);
  * seal friction per leg: front F_s, rear rear_scale x F_s (YAML seal_friction.rear_scale 0.8333, U-S8-H2,
    as the Chrono S8 law); rev. 39 used the same F_s on all four legs.
Variant knobs (environment): S8_SINK = poly345_1ms (default) / stair_10Hz (rev. 39); S8_ROD = start (default) /
branch (armed at the event branch, dynamics 5.26.6) / off; S8_REAR = rear scale (default YAML 0.8333; 1.0 =
rev. 39 and dynamics 5.26.6); S8_SET = main (3 floors) / flat. stair_10Hz + off + 1.0 reproduces the rev. 39
JSON bit for bit; branch + 1.0 reproduces dynamics s8_g4_rodside_check.json (3-4-5 + rod side) bit for bit.

Per base (floor, F_s, judge): level to READY + 5 s, then branch (deepcopy) into the event scenarios
  E0 hold 40 s, E1 RR sink 11.5 mm / 2 s (G4), E2 RR sink 11.5 mm / 20 s (SS), E3 RR drop 30 mm / 0.05 s
  (RE1bF), E4 RR sink 9 mm / 20 s (SS9); fast events at start phases 0 / 0.025 / 0.05 / 0.075 s, slow ones 0 / 0.05.
Truth: true cylinder force (pad contact - rod weight), minimum over the 1 ms chunks of each control period;
lift = pad contact 0. Episodes (203.1, simplified): per leg, consecutive periods with truth < F_min (U or L).
Offline judges on the recorded readings (independent of the control action):
  JP_m : P < F_min + m ;  JC_m : P - F_band < F_min + m   (m = 0 judge level, 7.5 kN = P5 action level)
  sampling_only (211.2): JC_m0 never flags the episode but JC_m7.5 flags it by t_on + 0.3 s.
Probe diagnostics (F_band, rev. 42 212.5): the plant state at both probe end readings (truth, friction state f,
rod stroke) so that the seal estimate splits into the own-leg friction part -(f_e - f_r)/2 and the residual
((F_e - F_r) - S dx)/2 (load hysteresis of the other legs + stiffness correction error).
Units SI inside; report kN / s. Deterministic (no random numbers).
Run: conda run -n dynamics-dev python -I s8_fs_precheck.py <project_root> <out_json> [workers]
"""
from __future__ import annotations

import copy
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("NUMBA_NUM_THREADS", "1")

import numpy as np

ROOT = Path(sys.argv[1]).resolve()
for _p in (ROOT / "03_src", ROOT / "04_scripts" / "03_control" / "r8d1", ROOT / "04_scripts" / "03_control",
           ROOT / "04_scripts" / "01_dynamics"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

SINK = os.environ.get("S8_SINK", "poly345_1ms")
ROD = os.environ.get("S8_ROD", "start")
REAR = os.environ.get("S8_REAR")            # None -> YAML rear_scale
SET = os.environ.get("S8_SET", "main")

FLOORS = {"flat": (0.0, 0.0), "roll4.4": (4.4, 0.0), "rpB": (2.7355, 1.7592)}
FS_KN = (0.0, 2.0, 4.0, 8.0)
JUDGES = ("pressure", "combined")
EVENTS = {
    "E0_hold": None,
    "E1_sink11.5_2s": (3, 0.0115, 2.0),
    "E2_sink11.5_20s": (3, 0.0115, 20.0),
    "E3_drop30_0.05s": (3, 0.030, 0.05),
    "E4_sink9_20s": (3, 0.009, 20.0),
}
OFFSETS_FAST = (0.0, 0.025, 0.05, 0.075)
OFFSETS_SLOW = (0.0, 0.05)
EVENT_DELAY_S = 5.0
EVENT_RUN_S = 40.0
BASE_LIMIT_S = 170.0
TAU_D_S = 0.3                 # 203.3 M1' (ASSUMPTION): detection 1 period + d + tau_v


def place_worker() -> None:
    """EcoQoS off for this worker (all-core affinity; not a cost measurement)."""
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = wintypes.HANDLE

    class PTS(ctypes.Structure):
        _fields_ = [("Version", wintypes.ULONG), ("ControlMask", wintypes.ULONG),
                    ("StateMask", wintypes.ULONG)]

    st = PTS(1, 1, 0)
    k32.SetProcessInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    k32.SetProcessInformation(k32.GetCurrentProcess(), 4, ctypes.byref(st), ctypes.sizeof(st))


def _imports():
    import c2py_r8d1_closed_loop as cl  # noqa: E402  (patches the harness modules)
    from outrigger_sim.control.c2 import C2Controller, C2Phase, ContactJudge
    from outrigger_sim.signals import Measurements
    return cl, C2Controller, C2Phase, ContactJudge, Measurements


def rear_scale() -> float:
    if REAR is not None:
        return float(REAR)
    from outrigger_sim.params import load_params
    p = load_params()
    return float(p.raw["actuator"]["seal_friction"]["rear_scale"])


def make_plant(cl, floor: str, fs_kN: float):
    import s8_g4_rodside_check as rsc   # dynamics rev. 39 RodSidePlant (same law, not copied)
    Plant = rsc.make_plant_class(cl)
    roll, pitch = FLOORS[floor]
    plant = Plant("top", roll, pitch, Fs=fs_kN * 1e3)
    plant.Fs = np.array([1.0, 1.0, rear_scale(), rear_scale()]) * fs_kN * 1e3
    return plant


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
    return m, fmin, cmin, float(acc[15])


# --- probe diagnostics -------------------------------------------------------------------------------------

PROBE_LOG: list[dict] = []


def _patch_probe(plant_ref: dict) -> None:
    from outrigger_sim.control import ground_contact as gc
    if getattr(gc.ProbeRound, "_s8_patched", False):
        return
    orig = gc.ProbeRound._end_stage

    def _end_stage(self, record, reading):
        pl = plant_ref.get("plant")
        if pl is not None:
            PROBE_LOG.append({"leg": int(self.leg), "stage": self._stage.name, "t": float(reading.t_s),
                              "reading_N": float(reading.cylinder_force_N[self.leg]),
                              "rod_m": float(reading.rod_stroke_m[self.leg]),
                              "true_N": pl.true_cyl_force().copy().tolist(),
                              "f_N": np.asarray(pl.f, float).copy().tolist(),
                              "Fs_N": np.asarray(pl.Fs, float).tolist()})
        return orig(self, record, reading)

    gc.ProbeRound._end_stage = _end_stage
    gc.ProbeRound._s8_patched = True


def probe_breakdown(ctrl) -> list[dict]:
    """Seal estimate split per probed leg of the first round (rev. 42 212.5)."""
    if not ctrl.probe_history:
        return []
    out = []
    first = ctrl.probe_history[0]
    for res in first:
        leg = res.leg_index
        ends = [e for e in PROBE_LOG if e["leg"] == leg]
        if len(ends) < 2 or getattr(res, "is_skipped", False):
            continue
        a, b = ends[0], ends[1]            # FIRST_MOVE end, SECOND_MOVE end
        rev = getattr(res, "is_reversed", False)
        e_, r_ = (b, a) if rev else (a, b)  # extended, retracted
        dP = e_["reading_N"] - r_["reading_N"]
        dF = e_["true_N"][leg] - r_["true_N"][leg]
        df = e_["f_N"][leg] - r_["f_N"][leg]
        dx = e_["rod_m"] - r_["rod_m"]
        est = res.seal_friction_estimate_N
        S_used = (dP - 2 * est) / dx if abs(dx) > 1e-9 else float("nan")
        S_true = dF / dx if abs(dx) > 1e-9 else float("nan")
        others = [i for i in range(4) if i != leg]
        out.append({
            "leg": leg, "reversed": bool(rev), "Fs_leg_kN": e_["Fs_N"][leg] / 1e3,
            "seal_estimate_kN": est / 1e3,
            "own_friction_part_kN": -0.5 * df / 1e3,
            "residual_kN": 0.5 * (dF - S_used * dx) / 1e3,
            "travel_mm": dx * 1e3, "S_used_MN_m": S_used / 1e6, "S_true_secant_MN_m": S_true / 1e6,
            "stiffness_error_part_kN": 0.5 * (S_true - S_used) * dx / 1e3,
            "f_ext_kN": e_["f_N"][leg] / 1e3, "f_ret_kN": r_["f_N"][leg] / 1e3,
            "others_f_change_kN": [(e_["f_N"][i] - r_["f_N"][i]) / 1e3 for i in others],
            "check_identity_kN": (est - (-0.5 * df + 0.5 * (dF - S_used * dx))) / 1e3,
        })
    return out


# --- runs --------------------------------------------------------------------------------------------------


def run_base(args):
    floor, fs_kN, judge = args
    place_worker()
    cl, C2Controller, C2Phase, ContactJudge, Measurements = _imports()
    t0 = time.perf_counter()
    cl.rmf.CONFIG.clear()
    cl.rpt.RCFG.clear()
    plant = make_plant(cl, floor, fs_kN)
    plant.step(np.zeros(4), int(round(cl.rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
    plant.t = 0.0
    if ROD == "start":
        plant.arm()
    ref = {"plant": plant}
    PROBE_LOG.clear()
    _patch_probe(ref)
    cfg = cl.preset_config(ContactJudge(judge), with_imu_samples=True)
    ctrl = C2Controller.from_params(cl.PARAMS, cfg)
    ha = ctrl.geometry.head_area_m2
    Fmin = ctrl.geometry.F_min_N
    cmd, valve = np.zeros(4), np.zeros(4)
    t_lift = t_ready = None
    min_true_lev, min_contact_lev = np.inf, np.inf
    err_lev = []
    while plant.t < BASE_LIMIT_S:
        m, fmin, cmin, crawler = period(cl, Measurements, plant, cmd, valve, ha, ctrl.period_s)
        cmd = np.array(ctrl.update(m).leg_speed_m_s)
        if t_lift is None and crawler == 0.0 and ctrl.phase is C2Phase.LEVEL:
            t_lift = plant.t
        if t_lift is not None:
            min_true_lev = min(min_true_lev, float(fmin.min()))
            min_contact_lev = min(min_contact_lev, float(cmin.min()))
            err_lev.append((plant.pressure() - plant.true_cyl_force()).tolist())
        if ctrl.phase is C2Phase.READY and t_ready is None:
            t_ready = plant.t
        if t_ready is not None and plant.t >= t_ready + EVENT_DELAY_S - 1e-9:
            break
    ref["plant"] = None
    err_lev = np.array(err_lev) if err_lev else np.zeros((1, 4))
    F = plant.true_cyl_force()
    n = np.array([0.476, -0.476, -0.523, 0.523])
    base = {"floor": floor, "Fs_kN": fs_kN, "Fs_leg_kN": (plant.Fs / 1e3).tolist(), "judge": judge,
            "t_ready_s": t_ready, "t_crawler_liftoff_s": t_lift, "phase": str(ctrl.phase),
            "D8_min_true_after_liftoff_kN": min_true_lev / 1e3,
            "D8_margin_vs_Fmin+5_kN": (min_true_lev - Fmin - 5e3) / 1e3,
            "min_contact_after_liftoff_kN": min_contact_lev / 1e3,
            "F_band_kN": ctrl.seal_band_N / 1e3,
            "true_at_ready+5_kN": (F / 1e3).tolist(),
            "twist_true_nTF_kN": float(n @ F / 1e3),
            "reading_minus_true_at_ready_kN": ((plant.pressure() - F) / 1e3).tolist(),
            "reading_minus_true_level_maxmin_kN": [float(err_lev.max() / 1e3), float(err_lev.min() / 1e3)],
            "probe_rounds": len(ctrl.probe_history),
            "probe_breakdown_round1": probe_breakdown(ctrl)}
    events = []
    if t_ready is not None:
        for ename, ev in EVENTS.items():
            offs = (0.0,) if ev is None else (OFFSETS_FAST if ev[2] < 5.0 else OFFSETS_SLOW)
            for off in offs:
                pl = copy.deepcopy(plant)
                if ROD == "branch":
                    pl.arm()
                events.append(run_event(cl, C2Phase, Measurements, pl, copy.deepcopy(ctrl), cmd.copy(),
                                        valve.copy(), ha, Fmin, ename, ev, off))
    base["events"] = events
    base["wall_s"] = time.perf_counter() - t0
    return base


def _episodes(mask: np.ndarray) -> list[tuple[int, int]]:
    """Index ranges [a, b] of consecutive True samples."""
    out, a = [], None
    for k, v in enumerate(mask):
        if v and a is None:
            a = k
        if not v and a is not None:
            out.append((a, k - 1)); a = None
    if a is not None:
        out.append((a, len(mask) - 1))
    return out


def run_event(cl, C2Phase, Measurements, plant, ctrl, cmd, valve, ha, Fmin, ename, ev, off):
    t_ev = plant.t + off
    n0 = len(ctrl.events)
    rows = []

    def floor_fn(pl_):
        leg, depth, ramp = ev
        tau = min(1.0, max(0.0, (pl_.t - t_ev) / ramp))
        pl_.goff[leg] = depth * (tau ** 3 * (10 - 15 * tau + 6 * tau ** 2) if SINK == "poly345_1ms" else tau)

    while plant.t < t_ev + EVENT_RUN_S:
        if ev is not None and SINK == "stair_10Hz":
            floor_fn(plant)
        m, fmin, cmin, _ = period(cl, Measurements, plant, cmd, valve, ha, ctrl.period_s,
                                  floor_fn if (ev is not None and SINK != "stair_10Hz") else None)
        P = plant.pressure().copy()
        band = float(ctrl.seal_band_N)
        cmd = np.array(ctrl.update(m).leg_speed_m_s)
        rows.append((plant.t, P, fmin, cmin, band, str(ctrl.phase), plant.true_cyl_force().copy(), cmd.copy(),
                     np.asarray(plant.Gr, float).copy() if getattr(plant, "armed", False) else np.zeros(4)))
    t = np.array([r[0] for r in rows]) - t_ev
    P = np.array([r[1] for r in rows])
    Ft = np.array([r[2] for r in rows])          # period min of the true cylinder force (1 ms chunks)
    C = np.array([r[3] for r in rows])
    band = np.array([r[4] for r in rows])
    phase = [r[5] for r in rows]
    Fe = np.array([r[6] for r in rows])          # true force at the sample instant
    U = np.array([r[7] for r in rows])
    Gr = np.array([r[8] for r in rows])
    ev_names = [(round(e.t_s - t_ev, 2), e.name) for e in ctrl.events[n0:]]
    out = {"event": ename, "offset_s": off,
           "min_true_kN": float(Ft.min() / 1e3), "min_true_leg": int(np.unravel_index(Ft.argmin(), Ft.shape)[1]),
           "t_min_s": float(t[np.unravel_index(Ft.argmin(), Ft.shape)[0]]),
           "t_below_Fmin_s": float((Ft.min(axis=1) < Fmin).sum() * 0.1),
           "t_lift_s": float((C.min(axis=1) <= 0.0).sum() * 0.1),
           "final_min_true_kN": float(Fe[-1].min() / 1e3), "final_phase": phase[-1],
           "reapproach": any(n.startswith("leg_reapproach_start") for _, n in ev_names),
           "rod_side_range_kN": [float(Gr.min() / 1e3), float(Gr.max() / 1e3)]}
    left = [i for i, p in enumerate(phase) if p != "ready"]
    out["t_first_leave_ready_s"] = float(t[left[0]]) if left else None
    out["n_leave_ready"] = int(sum(1 for i in range(1, len(phase)) if phase[i - 1] == "ready" and phase[i] != "ready"))
    out["controller_events"] = ev_names[:20]
    # F10: retract commands on a low-load leg (combined lower bound < F_min + 7.5 kN), periods
    low = (P - band[:, None]) < Fmin + 7.5e3
    out["F10_retract_on_low_load_periods"] = int((low & (U < -1e-6)).sum())
    out["RR_cmd_first_2s_mm_s"] = (U[:20, 3] * 1e3).round(3).tolist()
    # offline judges (same records, readings only) vs truth episodes (period min of the true force)
    truth_under = Ft < Fmin
    for m_kN in (0.0, 7.5):
        level = Fmin + m_kN * 1e3
        for jn, est in (("JP", P), ("JC", P - band[:, None])):
            flag = est < level
            key = f"{jn}_m{m_kN:g}"
            eps = []
            for leg in range(4):
                for a, b in _episodes(truth_under[:, leg]):
                    fl = np.flatnonzero(flag[a:b + 1, leg])
                    eps.append({"leg": leg, "t_on_s": float(t[a]), "t_off_s": float(t[b]),
                                "min_true_kN": float(Ft[a:b + 1, leg].min() / 1e3),
                                "lift": bool((C[a:b + 1, leg] <= 0.0).any()),
                                "t_flag_s": float(t[a + fl[0]]) if fl.size else None,
                                "missed": bool(fl.size == 0)})
            fa = flag & (Fe >= level + 2e3)
            near = (Fe >= Fmin - 5e3) & (Fe <= Fmin + 10e3)
            err = (est - Fe)[near]
            out[key] = {"episodes": eps, "false_alarm_samples": int(fa.sum()),
                        "first_flag_s": [float(t[np.flatnonzero(flag[:, leg])[0]]) if flag[:, leg].any() else None
                                         for leg in range(4)],
                        "max_est_minus_true_near_Fmin_kN": float(err.max() / 1e3) if err.size else None}
    # sampling_only (211.2): judge level misses, action level flags by t_on + tau_d
    so = []
    for e0 in out["JC_m0"]["episodes"]:
        if not e0["missed"]:
            continue
        leg = e0["leg"]
        flags = np.flatnonzero(((P - band[:, None])[:, leg]) < Fmin + 7.5e3)
        ok = any(t[k] <= e0["t_on_s"] + TAU_D_S + 1e-9 for k in flags)
        so.append({"leg": leg, "t_on_s": e0["t_on_s"], "min_true_kN": e0["min_true_kN"], "sampling_only": bool(ok)})
    out["JC_m0_missed_episodes"] = so
    return out


def main():
    out = Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    floors = FLOORS if SET == "main" else {"flat": FLOORS["flat"]}
    jobs = [(f, fs, j) for f in floors for fs in FS_KN for j in JUDGES]
    if os.environ.get("S8_SMOKE"):
        jobs = [("flat", 4.0, "combined")]
    # load / compile the numba kernels once in the parent before the spawn pool (numba cache)
    cl = _imports()[0]
    pl = make_plant(cl, "flat", 0.0)
    pl.step(np.zeros(4), 2); pl.arm(); pl.step(np.zeros(4), 2)
    t0 = time.perf_counter()
    with Pool(min(workers, len(jobs))) as pool:
        res = pool.map(run_base, sorted(jobs, key=lambda j: -j[1]), chunksize=1)
    res.sort(key=lambda r: (list(FLOORS).index(r["floor"]), r["Fs_kN"], r["judge"]))
    out.write_text(json.dumps({"meta": {"script": "04_scripts/03_control/s8/s8_fs_precheck.py", "spec": "rev. 42",
                                        "wall_s": time.perf_counter() - t0, "workers": workers,
                                        "sink": SINK, "rod_side": ROD, "rear_scale": rear_scale(), "set": SET,
                                        "floors": floors, "Fs_kN_front": FS_KN, "events": EVENTS,
                                        "offsets_fast": OFFSETS_FAST, "offsets_slow": OFFSETS_SLOW},
                               "runs": res}, indent=1, default=float), encoding="utf-8")
    print("done", round(time.perf_counter() - t0, 1), "s ->", out)


if __name__ == "__main__":
    main()
