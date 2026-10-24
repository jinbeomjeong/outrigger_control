"""Try the C-5 oscillation definitions (cad assumption vs. proposal) on harness series (10 Hz true
cylinder force, true attitude, guard flag, phase) of matched bundle-C configurations.
Usage: python -I c5_def_test.py <out.json>"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bundle_c_ref as B  # noqa: E402

CAP = {}


def run(cid, seed=12345, l0r_like_stiff=None):
    import c2py_r8d1_closed_loop as cl
    from outrigger_sim.control.c2 import C2Controller
    s = B.CASES[cid]
    cfg = B._config(s)
    if l0r_like_stiff is not None:  # stress: twist / guard gains x 1/scale (pressure contact: no probe)
        from dataclasses import replace
        cfg = replace(cfg, r8=replace(cfg.r8, pre_probe_stiffness_scale=l0r_like_stiff))
    rec = {"guard": [], "phase": [], "t": []}

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

        def update(self, m, t):
            u = super().update(m, t)
            rec["t"].append(t)
            rec["guard"].append(self.controller._state.guard_m_s is not None)
            rec["phase"].append(str(getattr(self.controller.phase, "value", self.controller.phase)))
            return u

    rpt = cl.rpt
    orig = rpt.run_one

    def run_one(case):
        out = orig(case)
        CAP["S"] = {k: np.asarray(v).tolist() for k, v in out["_series"]["S"].items()}
        return out
    rpt.run_one = run_one
    cl.rcr.SensorsS = cl.traces.RecordingSensors
    rpt.C2RA = Adapter
    cl.rcc.CA["settle_scenario"] = dict(cl.rcc.CA["settle_scenario"], start_after_ready_s=5.0)
    case = cl.td2.rsb.mkc(f"T|{cid}|rigid|{seed}|{s['beta']*1e9:g}", s["level"], B.FLOORS[s["floor"]],
                          "rigid", seed=seed, beta=s["beta"] * 1e9)
    case = cl.td2.r8.apply(case, f"C2_tv{s['tau_v']:g}")
    if s["settle"]:
        case["rcfg"]["settle"] = True
    case["rcfg"]["ca_over"] = dict(case["rcfg"]["ca_over"], **cl.HARNESS_LOOP_OFF)
    r = cl.td2.run(case)
    rpt.run_one = orig
    S = CAP["S"]
    if l0r_like_stiff is not None:
        cid = f"{cid}@gain/{l0r_like_stiff:g}"
    return {"cid": cid, "seed": seed, "t": S["t"], "F": S["Ftrue"], "phi": S["phi"], "theta": S["theta"],
            "u": S["u"], "guard": rec["guard"], "phase": rec["phase"], "tc": rec["t"],
            "t_ready": r.get("t_ready_s"), "settle": (r.get("settle_result") or {}).get("t_sink_s")}


if __name__ == "__main__":
    out = []
    for cid in ("C1_G4_pressure", "C1_G4_combined", "C4_tv0.15_G4_pressure", "C1_D8_top_fdown3.5_b1.6",
                "C1_D8_top_roll5.5_b1.6", "C4_tv0.15_D8_top_roll5.5_b1.6", "C9_R5_G4_pressure"):
        out.append(run(cid))
        print(cid, "done", flush=True)
    for sc in (0.4, 0.25, 0.15):
        out.append(run("C1_G4_pressure", l0r_like_stiff=sc))
        print("stress", sc, "done", flush=True)
    Path(sys.argv[1]).write_text(json.dumps(out), encoding="utf-8")
