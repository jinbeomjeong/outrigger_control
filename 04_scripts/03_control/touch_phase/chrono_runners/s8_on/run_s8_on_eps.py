"""S8 soil row, flow limit on (eta_v 0.85): delivered speed after the limit x (1 - eps) until the first pad contact.

Main-tree code, no source edit. The arguments of the stored flow-on run are rebuilt from its result.json and checked against the
parser; only --out-root and (for short checks) --duration may differ.

Wrapper, two run-time replacements:
* ``S9Engine.apply_command`` only reads: first contact = any leg with truth F_contact_n_N > CONTACT_N at a control instant (same
  definition as the flow-off run_s8_eps.py). The command is passed unchanged.
* ``RecordedFlowLimiter.limit``: for t_s >= gate and before the first contact, the speeds it returns are multiplied by (1 - eps).

Difference from the flow-off variant (run_s8_eps.py): there the controller command is scaled; here the speed after the limit is,
because a scaled command hardly changes the delivered speed while the limit acts. flow_series.npz is written inside the limiter,
so its v_* and Q_sum are the values BEFORE the scaling, and the deficit integral does not hold the eps part. The speed that acted is
record u_applied and the slope of step_series s_motor_m. Scaling only lowers |speed|, so the flow drawn cannot exceed the supply; the
wrapper also records the largest scaled demand / supply.

Usage: python -I -B -X utf8 -u run_s8_on_eps.py --eps <e> --gate-s <t> --out-root <dir> --step-id <id> [--duration <s>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

MAIN = Path(r"C:\workspace\outrigger_control")
STORED = MAIN / "07_results/S9/batch_COUPLED_eta085_20261104_142213/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0"
HASHED = ("04_scripts/02_chrono/run_S9.py", "03_src/outrigger_sim/chrono/scm_engine.py", "03_src/outrigger_sim/chrono/scm_model.py",
          "03_src/outrigger_sim/chrono/l2b_engine.py", "03_src/outrigger_sim/chrono/l2b_actuator.py", "03_src/outrigger_sim/actuation.py",
          "03_src/outrigger_sim/runner.py", "03_src/outrigger_sim/control/c2.py", "03_src/outrigger_sim/hydraulics/flow_limit_run.py",
          "03_src/outrigger_sim/hydraulics/flow_share.py", "02_params/rexome33.yaml", "02_params/scm_soil_sets.json")
CONTACT_N = 3000.0
PERTURBATION = ("delivered leg speed after RecordedFlowLimiter.limit x (1 - eps) until the first contact; the flow-off variant "
                "run_s8_eps.py scales the controller command instead; flow_series v_* and Q_sum are before this scaling")


def level_parser(run_s9):
    ap = run_s9.build_parser()
    sub = next(a for a in ap._actions if isinstance(a, argparse._SubParsersAction))
    return ap, sub.choices["level"]


def rebuild_argv(run_s9, stored_args: dict, out_root: str, duration: float | None) -> list[str]:
    """CLI arguments that parse back to the stored args (checked), with the new out root and duration."""
    want = dict(stored_args, out_root=out_root)
    if duration is not None:
        want["duration"] = float(duration)
    ap, lp = level_parser(run_s9)
    argv = ["level"]
    for action in lp._actions:
        if action.dest in ("help", "action") or action.dest not in want or not action.option_strings:
            continue
        value = want[action.dest]
        if value is None or value is False:
            continue
        flag = action.option_strings[0]
        if value is True:
            argv.append(flag)
        elif isinstance(value, (list, tuple)):
            argv += [flag, *(repr(float(v)) if isinstance(v, float) else str(v) for v in value)]
        else:
            argv += [flag, repr(float(value)) if isinstance(value, float) else str(value)]
    parsed = vars(ap.parse_args(argv))
    parsed = {k: (list(v) if isinstance(v, tuple) else v) for k, v in parsed.items()}
    if parsed != want:
        diff = {k: (parsed.get(k), want.get(k)) for k in set(parsed) | set(want) if parsed.get(k) != want.get(k)}
        raise SystemExit(f"rebuilt arguments differ from the stored run: {diff}")
    return argv


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eps", type=float, required=True)
    ap.add_argument("--gate-s", type=float, required=True, help="absolute time from which speeds are scaled [s]")
    ap.add_argument("--out-root", required=True)
    ap.add_argument("--step-id", required=True, help="label only, keeps the id on the command line for the sampler")
    ap.add_argument("--duration", type=float, default=None)
    me = ap.parse_args()
    if not 0.0 <= me.eps < 0.01:
        raise SystemExit(f"--eps out of range: {me.eps}")
    sys.path.insert(0, str(MAIN / "04_scripts" / "02_chrono"))
    os.chdir(MAIN)
    import run_S9

    if Path(run_S9.__file__).resolve() != (MAIN / "04_scripts/02_chrono/run_S9.py").resolve():
        raise SystemExit(f"wrong run_S9: {run_S9.__file__}")
    from outrigger_sim.chrono import scm_engine
    from outrigger_sim.hydraulics import flow_limit_run

    if not Path(flow_limit_run.__file__).resolve().is_relative_to(MAIN / "03_src"):
        raise SystemExit(f"wrong outrigger_sim: {flow_limit_run.__file__}")
    stored = json.loads((STORED / "result.json").read_text(encoding="utf-8"))
    argv = rebuild_argv(run_S9, stored["args"], me.out_root, me.duration)
    case = stored["args"]["case"]
    state = {"first_contact_t_s": None, "first_contact_F_N": None, "commands": 0, "limit_steps": 0, "scaled_steps": 0,
             "scaled_steps_limited": 0, "first_scaled_t_s": None, "last_scaled_t_s": None, "max_scaled_demand_over_supply": None}
    original_apply = scm_engine.S9Engine.apply_command
    original_limit = flow_limit_run.RecordedFlowLimiter.limit
    factor = 1.0 - me.eps

    def apply_command(self, command):
        state["commands"] += 1
        if state["first_contact_t_s"] is None:
            fn = self.truth().F_contact_n_N
            if float(max(fn)) > CONTACT_N:
                state["first_contact_t_s"] = float(command.t_s)
                state["first_contact_F_N"] = [float(v) for v in fn]
        original_apply(self, command)

    def limit(self, t_s, dt_s, request_m_s, force_N):
        delivered = original_limit(self, t_s, dt_s, request_m_s, force_N)
        state["limit_steps"] += 1
        if state["first_contact_t_s"] is not None or t_s < me.gate_s:
            return delivered
        scaled = delivered * factor
        state["scaled_steps"] += 1
        if state["first_scaled_t_s"] is None:
            state["first_scaled_t_s"] = float(t_s)
        state["last_scaled_t_s"] = float(t_s)
        if np.any(delivered != np.asarray(request_m_s, dtype=float)):
            state["scaled_steps_limited"] += 1
        ratio = float(self.pump.demand_m3_s(scaled)) / self.supply_m3_s
        if state["max_scaled_demand_over_supply"] is None or ratio > state["max_scaled_demand_over_supply"]:
            state["max_scaled_demand_over_supply"] = ratio
        return scaled

    scm_engine.S9Engine.apply_command = apply_command
    flow_limit_run.RecordedFlowLimiter.limit = limit
    run_S9.main(argv)
    code = {f: hashlib.sha256((MAIN / f).read_bytes()).hexdigest() for f in HASHED}
    side = {"step_id": me.step_id, "eps": me.eps, "gate_s": me.gate_s, "contact_N": CONTACT_N, "perturbation": PERTURBATION, "state": state, "argv": argv,
            "main_head": (MAIN / ".git/refs/heads/master").read_text(encoding="utf-8").strip(), "code_sha256": code,
            "wrapper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "env": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OUTRIGGER_PLACEMENT")}}
    d = Path(me.out_root) / case
    d.mkdir(parents=True, exist_ok=True)
    (d / "eps_wrapper.json").write_text(json.dumps(side, indent=1), encoding="utf-8")
    print("eps_wrapper", json.dumps({k: side[k] for k in ("step_id", "eps", "gate_s", "state", "env")}), flush=True)


if __name__ == "__main__":
    main()
