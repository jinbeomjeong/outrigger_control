"""Project c2.py (with_10hz_d1) in the revision-30 harness (r8d1_td2, C2_tv0.1: valve lag 0.1 s, noise, KPlant)
for the D8 boundary S cases and the G4-type settlement, with R8 setting variants:
  base   symmetric 0.25 increment, measured S_ii normalisation, pre-probe 1.0, lower bound 1.0 (as implemented)
  pre12  pre-probe scale 1.2
  inc01  symmetric 0.1
  asym   0.1, guard direction 0.25
  hramp  base, but the harness continuous ramp 0.4 s (= 0.25 v_max / period inside the period) instead of steps
Usage: python -I c2py_variants.py <out.json> <variants,comma> [workers] [group S|G|SG]

Spec rev. 31 142 C; results 06_analysis/02_control/r8_10hz/d1/v_all.json and v_pre.json. Those
runs used c2.py before rev. 31 149 (``base`` = pre-probe 1.0 as described above); a re-run takes
the rev. 31 preset (pre-probe 1.2, head-only denominator, median) as ``base``.
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

PROJ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(PROJ / "03_src"))
sys.path.insert(0, str(PROJ / "04_scripts" / "03_control"))

VARIANT = {"name": "base"}


def _config(cl, contact, with_imu):
    from outrigger_sim.control.c2 import IncrementLimit
    cfg = cl.preset_config(contact, with_imu)
    v = VARIANT["name"]
    r8 = cfg.r8
    if v == "pre12":
        r8 = replace(r8, pre_probe_stiffness_scale=1.2)
    elif v.startswith("pre") and v[3:].replace(".", "").isdigit() and "." in v:
        r8 = replace(r8, pre_probe_stiffness_scale=float(v[3:]))
    elif v == "inc01":
        r8 = replace(r8, increment_limit=IncrementLimit(0.1, 0.1))
    elif v == "asym":
        r8 = replace(r8, increment_limit=IncrementLimit(0.1, 0.25))
    return replace(cfg, r8=r8)


def job(args):
    spec, variant = args
    VARIANT["name"] = variant
    import c2py_r8d1_closed_loop as cl
    if not hasattr(cl, "preset_config_orig"):
        cl.preset_config_orig = cl.preset_config
    orig = cl.preset_config_orig

    class _Shim:
        preset_config = staticmethod(orig)

    cl.preset_config = lambda contact, with_imu_samples: _config(_Shim, contact, with_imu_samples)
    if variant == "hramp":
        cl.HARNESS_LOOP_OFF = {"ramp_s": 0.4, "delay_steps": 0}
        # controller increment limit effectively off (harness ramp does it)
        from outrigger_sim.control.c2 import IncrementLimit

        def cfg_h(contact, with_imu_samples, _o=orig):
            c = _o(contact, with_imu_samples)
            return replace(c, r8=replace(c.r8, increment_limit=IncrementLimit(2.0, 2.0)))
        cl.preset_config = cfg_h
    else:
        cl.HARNESS_LOOP_OFF = {"ramp_s": 1e-9, "delay_steps": 0}
    t0 = time.perf_counter()
    try:
        r = cl.run_harness_case(spec)
    except Exception as e:  # noqa: BLE001
        return dict(id=spec["id"], variant=variant, error=repr(e))
    r["variant"] = variant
    r["wall"] = time.perf_counter() - t0
    return r


if __name__ == "__main__":
    out = Path(sys.argv[1])
    variants = sys.argv[2].split(",")
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    group = sys.argv[4] if len(sys.argv) > 4 else "SG"
    import export_c2_r8d1_traces as traces
    specs = []
    if "S" in group:
        specs += [{"group": "S", "id": c["id"]} for c in traces.r8.cases_S([traces.CONFIG_NAME])
                  if c["id"].startswith("T|")]
    if "G" in group:
        specs += [{"group": "G", "id": c["id"]} for c in traces.td2.cases_G([traces.CONFIG_NAME])]
    jobs = [(s, v) for v in variants for s in specs]
    print("jobs", len(jobs), flush=True)
    t0 = time.perf_counter()
    with Pool(workers) as p:
        rows = p.map(job, jobs, chunksize=1)
    out.write_text(json.dumps(rows, indent=1, default=float), encoding="utf-8")
    print("wall", round(time.perf_counter() - t0, 1), "errors", sum("error" in r for r in rows))
