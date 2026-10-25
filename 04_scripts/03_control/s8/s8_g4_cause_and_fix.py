"""S8 G4 diagnostics on the rev. 42 reduced harness (s6_control_spec.md rev. 42, 212.3 / 212.4).

A  cause of the combined-judge gap to Chrono L1-R (+0.6..+1.8 kN, dynamics 5.26.6): rod side armed at the event
   branch (dynamics 5.26.6) vs armed before levelling (rev. 42 default, as Chrono L1-R / L2b, where the probe
   already sees it). Prints the probe-measured twist stiffness scale (U-R8-8), F_band and the G4 minima.
B  intervention: rod side from the start, but the controller's twist stiffness scale set to the value of the
   branch-armed run before the G4 branch. If the G4 minima move back, the scale is the cause.
C  U-S8-5 candidate: start level of the P-R8-13 re-approach (LiftedReapproachSettings.load_fraction_of_F_min, set past its (0, 1) check by object.__setattr__,
   a config knob, controller code unchanged) 0.5 (now) / 0.75 / 1.0 / 1.4 / 1.8 of F_min. Whole run with the variant
   (levelling, probe, READY): D8, READY time, re-approach starts in the E0 hold (false starts), G4 4 phases,
   SS 2 phases, RE1bF drop 2 phases. Floors flat and rpB, combined judge, F_s 0 / 4 / 8 kN.
Same harness as s8_fs_precheck.py (3-4-5 sink on 1 ms chunks, L1-R rod side from the start, rear seal x 0.8333).
Deterministic. Run: conda run -n dynamics-dev python -I s8_g4_cause_and_fix.py <project_root> <out_json> [workers]
"""
from __future__ import annotations

import copy
import json
import sys
import time
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402

import s8_fs_precheck as pc  # noqa: E402  (argv[1] = project root)

G4 = (3, 0.0115, 2.0)
SS = (3, 0.0115, 20.0)
DROP = (3, 0.030, 0.05)
PHASES_G4 = (0.0, 0.025, 0.05, 0.075)
FRACTIONS = (0.5, 0.75, 1.0, 1.4, 1.8)


def level(floor: str, fs_kN: float, rod: str, fraction: float = 0.5, judge: str = "combined"):
    cl, C2Controller, C2Phase, ContactJudge, Measurements = pc._imports()
    cl.rmf.CONFIG.clear(); cl.rpt.RCFG.clear()
    plant = pc.make_plant(cl, floor, fs_kN)
    plant.step(np.zeros(4), int(round(cl.rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
    plant.t = 0.0
    if rod == "start":
        plant.arm()
    cfg = cl.preset_config(ContactJudge(judge), with_imu_samples=True)
    lr = replace(cfg.r8.lifted_reapproach)
    object.__setattr__(lr, "load_fraction_of_F_min", fraction)  # diagnostic: bypasses the (0, 1) check
    cfg = replace(cfg, r8=replace(cfg.r8, lifted_reapproach=lr))
    ctrl = C2Controller.from_params(cl.PARAMS, cfg)
    ha = ctrl.geometry.head_area_m2
    cmd, valve = np.zeros(4), np.zeros(4)
    t_ready = t_lift = None
    d8 = np.inf
    while plant.t < pc.BASE_LIMIT_S:
        m, fmin, cmin, crawler = pc.period(cl, Measurements, plant, cmd, valve, ha, ctrl.period_s)
        cmd = np.array(ctrl.update(m).leg_speed_m_s)
        if t_lift is None and crawler == 0.0 and ctrl.phase is C2Phase.LEVEL:
            t_lift = plant.t
        if t_lift is not None:
            d8 = min(d8, float(fmin.min()))
        if ctrl.phase is C2Phase.READY and t_ready is None:
            t_ready = plant.t
        if t_ready is not None and plant.t >= t_ready + pc.EVENT_DELAY_S - 1e-9:
            break
    n_reap_lev = sum(1 for e in ctrl.events if e.name.startswith("leg_reapproach_start"))
    return cl, Measurements, plant, ctrl, cmd, valve, ha, t_ready, d8, n_reap_lev


def event(cl, Measurements, plant, ctrl, cmd, valve, ha, ev, off, rod: str, run_s: float = 20.0):
    plant = copy.deepcopy(plant); ctrl = copy.deepcopy(ctrl); cmd = cmd.copy(); valve = valve.copy()
    if rod == "branch":
        plant.arm()
    Fmin = ctrl.geometry.F_min_N
    t_ev = plant.t + off
    n0 = len(ctrl.events)
    mins, below, lift = [], 0, 0

    def floor_fn(pl_):
        leg, depth, ramp = ev
        tau = min(1.0, max(0.0, (pl_.t - t_ev) / ramp))
        pl_.goff[leg] = depth * tau ** 3 * (10 - 15 * tau + 6 * tau ** 2)

    while plant.t < t_ev + run_s:
        m, fmin, cmin, _ = pc.period(cl, Measurements, plant, cmd, valve, ha, ctrl.period_s,
                                     floor_fn if ev is not None else None)
        cmd = np.array(ctrl.update(m).leg_speed_m_s)
        mins.append(fmin.min())
        below += int(fmin.min() < Fmin)
        lift += int(cmin.min() <= 0.0)
    names = [(round(e.t_s - t_ev, 2), e.name) for e in ctrl.events[n0:]]
    return {"offset_s": off, "min_true_kN": float(min(mins) / 1e3), "t_below_Fmin_s": below * 0.1,
            "t_lift_s": lift * 0.1, "n_reapproach_start": sum(1 for _, n in names if n.startswith("leg_reapproach_start")),
            "n_leave_ready_events": sum(1 for _, n in names if n.startswith(("relevel", "leg_reapproach_start"))),
            "events": names[:8], "final_phase": str(ctrl.phase)}


def job(args):
    part, floor, fs, rod, frac = args
    pc.place_worker()
    t0 = time.perf_counter()
    cl, Meas, plant, ctrl, cmd, valve, ha, t_ready, d8, nlev = level(floor, fs, rod, frac)
    st = ctrl._state
    out = {"part": part, "floor": floor, "Fs_kN": fs, "rod": rod, "fraction": frac, "t_ready_s": t_ready,
           "D8_min_kN": d8 / 1e3, "reapproach_starts_levelling": nlev, "F_band_kN": ctrl.seal_band_N / 1e3,
           "twist_stiffness_scale": st.twist_stiffness_scale,
           "twist_stiffness_raw_ratio": st.twist_stiffness_raw_ratio}
    if part == "A":
        out["G4"] = [event(cl, Meas, plant, ctrl, cmd, valve, ha, G4, o, rod) for o in PHASES_G4]
    elif part == "B":
        ctrl_b = level(floor, fs, "branch")[3]
        ctrl._state.twist_stiffness_scale = ctrl_b._state.twist_stiffness_scale
        out["scale_set_to"] = ctrl_b._state.twist_stiffness_scale
        out["G4"] = [event(cl, Meas, plant, ctrl, cmd, valve, ha, G4, o, rod) for o in PHASES_G4]
    else:
        out["G4"] = [event(cl, Meas, plant, ctrl, cmd, valve, ha, G4, o, rod) for o in PHASES_G4]
        out["SS"] = [event(cl, Meas, plant, ctrl, cmd, valve, ha, SS, o, rod, 40.0) for o in (0.0, 0.05)]
        out["DROP"] = [event(cl, Meas, plant, ctrl, cmd, valve, ha, DROP, o, rod) for o in (0.0, 0.05)]
        out["E0"] = [event(cl, Meas, plant, ctrl, cmd, valve, ha, None, 0.0, rod, 40.0)]
    out["wall_s"] = time.perf_counter() - t0
    return out


def main():
    out = Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    jobs = [("A", "flat", fs, rod, 0.5) for fs in (0.0, 4.0, 8.0) for rod in ("branch", "start")]
    jobs += [("B", "flat", fs, "start", 0.5) for fs in (0.0, 4.0, 8.0)]
    jobs += [("C", fl, fs, "start", fr) for fl in ("flat", "rpB") for fs in (0.0, 4.0, 8.0) for fr in FRACTIONS]
    cl = pc._imports()[0]
    pl = pc.make_plant(cl, "flat", 0.0); pl.step(np.zeros(4), 2); pl.arm(); pl.step(np.zeros(4), 2)
    t0 = time.perf_counter()
    with Pool(min(workers, len(jobs))) as pool:
        res = pool.map(job, sorted(jobs, key=lambda j: j[0] != "C"), chunksize=1)
    out.write_text(json.dumps({"meta": {"script": "04_scripts/03_control/s8/s8_g4_cause_and_fix.py",
                                        "doc": __doc__, "wall_s": time.perf_counter() - t0},
                               "runs": res}, indent=1, default=float), encoding="utf-8")
    for r in sorted(res, key=lambda r: (r["part"], r["floor"], r["Fs_kN"], r["rod"], r["fraction"])):
        line = (f"{r['part']} {r['floor']:5s} Fs {r['Fs_kN']:3.0f} rod {r['rod']:6s} f {r['fraction']:.1f} "
                f"band {r['F_band_kN']:5.2f} scale {r['twist_stiffness_scale']:.3f} ready {r['t_ready_s']} "
                f"D8 {r['D8_min_kN']:.1f} reapLev {r['reapproach_starts_levelling']}")
        for k in ("G4", "SS", "DROP", "E0"):
            if k in r:
                line += f" | {k} " + " ".join(f"{e['min_true_kN']:.2f}/{e['t_below_Fmin_s']:.1f}/{e['t_lift_s']:.1f}"
                                              f"/r{e['n_reapproach_start']}" for e in r[k])
        print(line)
    print("wall", round(time.perf_counter() - t0, 1))


if __name__ == "__main__":
    main()
