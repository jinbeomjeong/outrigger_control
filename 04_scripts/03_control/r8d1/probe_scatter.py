"""R8-D1 (C2 preset): probe incremental-stiffness scatter at 10 Hz on the reduced plant and the
effect of the twist / guard gain normalisation settings on the closed loop.

Reuses c2py_r8d1_closed_loop (100 Hz IMU samples, valve lag 0.1 s, ideal sensors, combined judge).
Logs every ProbeSample through a wrapper on ground_contact.evaluate_probe and evaluates several
stiffness estimators offline:
  half   - current (second half of the first move: hold end - mid reading)
  full   - start -> first hold (whole first move)
  rt     - first hold - second hold over the rod-stroke gap (round trip; + 2 F_s / gap bias)
Usage: python -I probe_scatter.py <out.json> [workers]

Spec rev. 31 142 A; result 06_analysis/02_control/r8_10hz/d1/ps_all.json. That run used c2.py
before rev. 31 149 (pre-probe scale 1.0, U63 C1 denominator, mean ratio); a re-run takes the
rev. 31 preset as ``base``.
"""
from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

import numpy as np

PROJ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(PROJ / "03_src"))


def run_case(args):
    level, roll, pitch, beta, fs, variant = args
    import c2py_r8d1_closed_loop as cl
    from outrigger_sim.control import ground_contact as gc
    from outrigger_sim.control.c2 import C2Controller, C2Phase, ContactJudge, TwistGainReference

    log = []
    orig = gc.evaluate_probe

    def wrapped(sample, *a, **k):
        res = orig(sample, *a, **k)
        log.append((sample, res))
        return res

    gc.evaluate_probe = wrapped
    cl.rmf.CONFIG.clear()
    cl.rpt.RCFG.clear()
    plant = cl.rmf.FlexPlant(level, roll, pitch, beta, fs)
    plant.step(np.zeros(4), int(round(cl.rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
    plant.t = 0.0
    cfg = cl.preset_config(ContactJudge.COMBINED, with_imu_samples=True)
    r8 = cfg.r8
    if variant == "pre12":
        r8 = replace(r8, pre_probe_stiffness_scale=1.2)
    elif variant == "knom":
        r8 = replace(r8, twist_gain_reference=TwistGainReference.NOMINAL)
    elif variant == "pre12_cap13":
        r8 = replace(r8, pre_probe_stiffness_scale=1.2)
    cfg = replace(cfg, r8=r8)
    ctl = C2Controller.from_params(cl.PARAMS, cfg)
    head_area = ctl.geometry.head_area_m2
    command = np.zeros(4)
    valve = np.zeros(4)
    t_ready = t_lift = None
    fmin_lift = math.inf
    fmin_level = math.inf
    scales = []
    att = []
    t0 = time.perf_counter()
    while plant.t < 150.0:
        meas, contact, crawler = cl._control_period(plant, command, valve, head_area, ctl.period_s)
        command = np.array(ctl.update(meas).leg_speed_m_s)
        if t_lift is None and crawler == 0.0 and ctl.phase is C2Phase.LEVEL:
            t_lift = plant.t
        if t_lift is not None:
            f = float(plant.true_cyl_force().min())
            fmin_lift = min(fmin_lift, f)
            if t_ready is None:
                fmin_level = min(fmin_level, f)
        if ctl.phase is C2Phase.READY and t_ready is None:
            t_ready = plant.t
        if t_ready is not None:
            att.append(np.degrees(plant.attitude()))
            if plant.t >= t_ready + 5.0:
                break
    probes = []
    for s, r in log:
        if s.is_reversed:
            gap_rod = s.retracted_rod_stroke_m - s.start_rod_stroke_m
            gap_F = s.retracted_force_N - s.start_force_N
        else:
            gap_rod = s.extended_rod_stroke_m - s.start_rod_stroke_m
            gap_F = s.extended_force_N - s.start_force_N
        rt_gap = s.extended_rod_stroke_m - s.retracted_rod_stroke_m
        rt_F = s.extended_force_N - s.retracted_force_N
        probes.append(dict(
            leg=s.leg_index, rev=bool(s.is_reversed),
            half=r.incremental_stiffness_N_m,
            full=gap_F / gap_rod if abs(gap_rod) > 2e-4 else math.nan,
            rt=rt_F / rt_gap if abs(rt_gap) > 2e-4 else math.nan,
            mid_frac=((s.first_move_mid_rod_stroke_m - s.start_rod_stroke_m) / gap_rod)
            if abs(gap_rod) > 2e-4 else math.nan,
            travel_mm=gap_rod * 1e3,
            grounded_stiff=bool(r.is_grounded_by_stiffness),
        ))
    meta = ctl.meta()
    return dict(case=dict(level=level, roll=roll, pitch=pitch, beta=beta, fs=fs, variant=variant),
                t_ready=t_ready, fmin_lift_kN=fmin_lift / 1e3, fmin_level_kN=fmin_level / 1e3,
                att_max=float(np.abs(att).max()) if att else None,
                scale=meta["twist_gain_stiffness"]["measured_scale"], probes=probes,
                phase=str(ctl.phase), wall=time.perf_counter() - t0)


if __name__ == "__main__":
    out = Path(sys.argv[1])
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    jobs = []
    for level in ("top", "middle", "bottom"):
        for roll, pitch in ((0.0, 0.0), (3.0, 0.0), (0.0, -2.5), (0.0, 2.5)):
            for beta in (1.0e9, 1.6e9):
                for fs in (0.0, 5000.0):
                    for variant in ("base", "pre12", "knom"):
                        jobs.append((level, roll, pitch, beta, fs, variant))
    if len(sys.argv) > 3:
        jobs = jobs[: int(sys.argv[3])]
    t0 = time.perf_counter()
    with Pool(workers) as p:
        rows = p.map(run_case, jobs, chunksize=1)
    out.write_text(json.dumps(rows, indent=1, default=float), encoding="utf-8")
    print("cases", len(rows), "wall", round(time.perf_counter() - t0, 1))
