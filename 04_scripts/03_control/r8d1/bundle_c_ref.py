"""Bundle-C consistency reference (spec rev. 31, 146): the revision-30 harness (r8d1_td2, KPlant,
pad tangential bushings, harness sensor noise, valve lag) with the CURRENT project c2.py
(rev. 31 149 P-R8 applied) for every run_S6C.py case that the reduced plant can represent.

Variants per case (3 noise seeds 12345-12347, rigid mast):
  matched  controller settings of the Chrono case (contact judge, H4 on, combined verdict, tau_v,
           increment, twist reference, fast relevel; G4 settlement at READY + 5 s like s6_stage2)
  h142     the 142 C harness configuration (pressure contact, no REANCHOR, settlement READY + 2 s)
           for the D8 / G4 cases only (comparison with v_all.json "base").
Departures common to both (harness lacks the parts): no CHECK / zero calibration (start at TOUCH),
target check off, IMU per-period mean (no 10 ms samples), head pressure only (no L1-R rod side),
min force = 10 Hz-sampled true cylinder force after the crawler lift-off.

Usage: python -I bundle_c_ref.py <out_raw.json> [workers]
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

PROJ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJ / "03_src"))
sys.path.insert(0, str(PROJ / "04_scripts" / "03_control" / "r8d1"))
sys.path.insert(0, str(PROJ / "04_scripts" / "03_control"))

SEEDS = (12345, 12346, 12347)
FLOORS = {"flat": (0.0, 0.0), "roll3": (3.0, 0.0), "roll5.5": (5.5, 0.0), "fdown3.5": (0.0, 3.5),
          "fup3.5": (0.0, -3.5), "rp05": (2.7699, 1.7813), "fdown3.2": (0.0, 3.2),
          "roll4.4": (4.4, 0.0)}


def d(level, floor, beta=1.0, contact="combined", h4=True, combined_verdict=None, settle=False,
      tau_v=0.1, increment="sym0.25", twist="measured_Sii", fast=False, h142=False):
    return dict(level=level, floor=floor, beta=beta, contact=contact, h4=h4,
                combined_verdict=combined_verdict, settle=settle, tau_v=tau_v,
                increment=increment, twist=twist, fast=fast, h142=h142)


NULL = {
    "C1_RE1b_top_flat_settleRR30": "floor event settle_RR_30 (30 mm RR settlement) is not in the harness",
    "C1_RE1bF_top_flat_dropRR30": "floor event drop_RR_30 (sudden 30 mm drop, 1e-5 s window) is not in the harness",
    "C1_RE1bP_top_flat_dropRR30_probe": "floor event drop_RR_30_probe is not in the harness",
    "C1_PS7_flat_FLp10_cal": "WIKA pressure error model + CHECK zero calibration path is Chrono/SensorSuite only",
    "C1_PS7_flat_FLm10_cal": "WIKA pressure error model + CHECK zero calibration path is Chrono/SensorSuite only",
    "C1_G5_top_flat_change_p3": "target change event and target acceptance are not in the harness (target check off)",
    "C4b_D8_top_roll5.5_b1.6": "amplifier per_step ramp (R-3) is not in the harness (only a full-scale rate limit)",
    "C4b_D8_bottom_rp05_b1.6": "amplifier per_step ramp (R-3) is not in the harness (only a full-scale rate limit)",
    "C4b_G4_pressure": "amplifier per_step ramp (R-3) is not in the harness (only a full-scale rate limit)",
    "C5_L0r0.02_top_fdown3.2": "L1-R rod-side parallel spring (L_0r) is not in the reduced plant; Chrono only",
    "C5_L0r0.02_top_roll4.4": "L1-R rod-side parallel spring (L_0r) is not in the reduced plant; Chrono only",
    "C5_L0r0.02_G4_pressure": "L1-R rod-side parallel spring (L_0r) is not in the reduced plant; Chrono only",
    "C5_L0r0.1_top_fdown3.2": "L1-R rod-side parallel spring (L_0r) is not in the reduced plant; Chrono only",
    "C5_L0r0.1_top_roll4.4": "L1-R rod-side parallel spring (L_0r) is not in the reduced plant; Chrono only",
    "C5_L0r0.1_G4_pressure": "L1-R rod-side parallel spring (L_0r) is not in the reduced plant; Chrono only",
    "C6_G4_pressure": "sub-period output offset (+20 ms, R-5) is not in the harness (commands at period boundaries)",
    "C6_D8_top_roll5.5_b1.6": "sub-period output offset (+20 ms, R-5) is not in the harness (commands at period boundaries)",
    "C7_asym_RE1bF_top_flat_dropRR30": "floor event drop_RR_30 is not in the harness",
    "C10_knom_RE1bP_top_flat_dropRR30_probe": "floor event drop_RR_30_probe is not in the harness",
}

CASES = {}
for fl in ("roll5.5", "fdown3.5", "fup3.5", "rp05"):
    for b, tag in ((0.69, "b0.69"), (1.6, "b1.6")):
        CASES[f"C1_D8_top_{fl}_{tag}"] = d("top", fl, b)
for lv in ("middle", "bottom"):
    CASES[f"C1_D8_{lv}_rp05_b1.6"] = d(lv, "rp05", 1.6)
CASES["C1_H4V_top_fdown3.5"] = d("top", "fdown3.5")
CASES["C1_H4P_top_fdown3.2"] = d("top", "fdown3.2")
for fl in ("flat", "roll3"):
    CASES[f"C1_G1_top_{fl}"] = d("top", fl, contact="pressure", combined_verdict=False)
CASES["C1_G3_top_flat_normal_zeroed"] = d("top", "flat")
CASES["C1_G3_top_fdown3.5_normal_zeroed"] = d("top", "fdown3.5")
for c in ("pressure", "combined"):
    CASES[f"C1_G4_{c}"] = d("top", "flat", contact=c, settle=True)
for tau in (0.05, 0.15):
    CASES[f"C4_tv{tau:g}_D8_top_roll5.5_b1.6"] = d("top", "roll5.5", 1.6, tau_v=tau)
    CASES[f"C4_tv{tau:g}_D8_top_fup3.5_b1.6"] = d("top", "fup3.5", 1.6, tau_v=tau)
    CASES[f"C4_tv{tau:g}_G4_pressure"] = d("top", "flat", contact="pressure", settle=True, tau_v=tau)
CASES["C7_sym0.1_D8_top_rp05_b1.6"] = d("top", "rp05", 1.6, increment="sym0.1")
CASES["C7_sym0.1_D8_top_roll5.5_b1.6"] = d("top", "roll5.5", 1.6, increment="sym0.1")
CASES["C7_asym_G4_pressure"] = d("top", "flat", contact="pressure", settle=True, increment="asym")
for c in ("pressure", "combined"):
    CASES[f"C9_R5_G4_{c}"] = d("top", "flat", contact=c, settle=True, fast=True)
CASES["C10_knom_G4_combined"] = d("top", "flat", contact="combined", settle=True, twist="k_nom")

H142_CASES = [k for k in CASES if k.startswith("C1_D8_") or k in ("C1_G4_pressure",)]

SETTINGS = {}


def _key(s):
    return json.dumps(s, sort_keys=True)


def _config(s):
    from outrigger_sim.control.c2 import (C2Config, ContactJudge, FastRelevelSettings,
                                          IncrementLimit, TwistGainReference)
    from outrigger_sim.control.target import TargetAcceptance
    from outrigger_sim.control.zero_calibration import ZeroCalibrationMode
    import c2py_r8d1_closed_loop as cl
    if s["h142"]:
        return cl.preset_config(ContactJudge.PRESSURE, with_imu_samples=False)
    base = C2Config().with_10hz_d1()
    r8 = replace(base.r8, imu_sample_period_s=None)
    if s["increment"] == "sym0.1":
        r8 = replace(r8, increment_limit=IncrementLimit(0.1, 0.1))
    elif s["increment"] == "asym":
        r8 = replace(r8, increment_limit=IncrementLimit(fraction_per_period=0.1,
                                                        guard_fraction_per_period=0.25))
    if s["twist"] == "k_nom":
        r8 = replace(r8, twist_gain_reference=TwistGainReference.NOMINAL)
    if s["fast"]:
        r8 = replace(r8, fast_relevel=FastRelevelSettings())
    probe = base.probe if s["combined_verdict"] is None else replace(
        base.probe, use_combined_verdict=s["combined_verdict"])
    return replace(
        base,
        output_ramp_time_s=None,
        zero_calibration=replace(base.zero_calibration, mode=ZeroCalibrationMode.OFF),
        contact=ContactJudge(s["contact"]),
        reanchor=replace(base.reanchor, enable=s["h4"]),
        probe=probe,
        target=replace(base.target, check_time_s=0.0, acceptance=TargetAcceptance.OFF),
        r8=r8,
    )


def job(args):
    cid, s, seed = args
    import c2py_r8d1_closed_loop as cl
    from outrigger_sim.control.c2 import C2Controller
    traces, td2, rsb, r8m, rcc = cl.traces, cl.td2, cl.td2.rsb, cl.td2.r8, cl.rcc
    cfg = _config(s)

    class Adapter(cl.HarnessAdapter):
        def __init__(self, ctx, contact="pressure"):
            self.c = ctx
            cl.rmf.LAST["ctrl"] = self
            self.controller = C2Controller.from_params(cl.PARAMS, cfg)
            self.controller.reset()
            self.t_touch = self.t_done = self.t_ready_first = None
            self.fault = False
            self.probe_time = 0.0
            self.probe_rounds = 0
            self.events = []
            self.probe_log = []
            self.phi_f = self.th_f = None
            self.guard_steps = 0

    cl.rcr.SensorsS = traces.RecordingSensors
    cl.rpt.C2RA = Adapter
    rcc.CA["settle_scenario"] = dict(rcc.CA["settle_scenario"],
                                     start_after_ready_s=2.0 if s["h142"] else 5.0)
    ang = FLOORS[s["floor"]]
    beta = s["beta"] * 1e9
    case = rsb.mkc(f"T|{cid}|rigid|{seed}|{beta:g}", s["level"], ang, "rigid", seed=seed, beta=beta)
    case = r8m.apply(case, f"C2_tv{s['tau_v']:g}")
    if s["settle"]:
        case["rcfg"]["settle"] = True
    case["rcfg"]["ca_over"] = dict(case["rcfg"]["ca_over"], **cl.HARNESS_LOOP_OFF)
    t0 = time.perf_counter()
    try:
        run = td2.run(case)
    except Exception as e:  # noqa: BLE001
        return dict(case=cid, seed=seed, h142=s["h142"], error=repr(e))
    if "error" in run:
        return dict(case=cid, seed=seed, h142=s["h142"], error=str(run["error"])[:400])
    ad = cl.rmf.LAST["ctrl"]
    meta = ad.controller.meta()
    m = traces._metrics(run)
    return dict(case=cid, seed=seed, h142=s["h142"], metrics=m, fails=run.get("fails"),
                t_done_s=run.get("t_done_s"), events=run.get("events"),
                fault=ad.fault, phase=str(ad.controller.phase),
                revision=meta.get("revision"), twist_gain_stiffness=meta.get("twist_gain_stiffness"),
                wall=time.perf_counter() - t0)


if __name__ == "__main__":
    out = Path(sys.argv[1])
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    only = sys.argv[3].split(",") if len(sys.argv) > 3 else None
    import psutil
    psutil.Process().cpu_affinity(list(range(16, psutil.cpu_count())))  # E-cores
    jobs = []
    for cid, s in CASES.items():
        if only and cid not in only:
            continue
        for seed in SEEDS:
            jobs.append((cid, s, seed))
    for cid in H142_CASES:
        if only and cid not in only:
            continue
        for seed in SEEDS:
            jobs.append((cid, dict(CASES[cid], h142=True), seed))
    print("jobs", len(jobs), flush=True)
    t0 = time.perf_counter()
    with Pool(workers) as p:
        rows = p.map(job, jobs, chunksize=1)
    out.write_text(json.dumps({"null": NULL, "cases": CASES, "rows": rows}, indent=1, default=str),
                   encoding="utf-8")
    print("wall", round(time.perf_counter() - t0, 1), "errors",
          [(r["case"], r["error"][:200]) for r in rows if "error" in r][:6])
