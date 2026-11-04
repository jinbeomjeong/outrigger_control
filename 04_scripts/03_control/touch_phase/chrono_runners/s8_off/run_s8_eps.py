"""S8 soil row, flow limit off, approach speed x (1 - eps) until the first pad contact. Main-tree code, no source edit.

The stored flow-off run's arguments are rebuilt from its result.json and checked against the parser, only --out-root and
(for the short comparison) --duration may differ. No flow option is passed, so ``set_flow_limit`` is not called; the
script checks that the speed reference holds no flow limit when the first command arrives.

Wrapper: ``S9Engine.apply_command`` is replaced at run time. Each command before the first contact with
t_s >= gate has its leg speeds multiplied by (1 - eps). First contact = any leg with truth F_contact_n_N > CONTACT_N at a
control instant (read before the command is applied); after it the commands pass unchanged and truth is not read.
The controller, the sensors and the plant are not changed; record ``u_cmd`` keeps the controller's command, ``u_applied``
the scaled one.

Usage: python -I -X utf8 -u run_s8_eps.py --eps <e> --gate-s <t> --out-root <dir> [--duration <s>]
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import sys
from pathlib import Path

MAIN = Path(r"C:\workspace\outrigger_control")
STORED = MAIN / "07_results/S9/batch_FINAL-REP_20261030_223359/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0"
HASHED = ("04_scripts/02_chrono/run_S9.py", "03_src/outrigger_sim/chrono/scm_engine.py", "03_src/outrigger_sim/chrono/scm_model.py",
          "03_src/outrigger_sim/chrono/l2b_engine.py", "03_src/outrigger_sim/chrono/l2b_actuator.py", "03_src/outrigger_sim/actuation.py",
          "03_src/outrigger_sim/runner.py", "03_src/outrigger_sim/control/c2.py", "02_params/rexome33.yaml", "02_params/scm_soil_sets.json")
CONTACT_N = 3000.0
"""Same contact level as dynamics-expert sweep.py (oil force 3 kN there, SCM pad normal force here)."""


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
    ap.add_argument("--gate-s", type=float, required=True, help="absolute time from which commands are scaled [s]")
    ap.add_argument("--out-root", required=True)
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

    if not Path(scm_engine.__file__).resolve().is_relative_to(MAIN / "03_src"):
        raise SystemExit(f"wrong outrigger_sim: {scm_engine.__file__}")
    stored = json.loads((STORED / "result.json").read_text(encoding="utf-8"))
    argv = rebuild_argv(run_S9, stored["args"], me.out_root, me.duration)
    case = stored["args"]["case"]
    state = {"first_contact_t_s": None, "first_contact_F_N": None, "scaled_commands": 0, "commands": 0, "flow_limit_checked": False,
             "flow_limit_is_none": None}
    original = scm_engine.S9Engine.apply_command
    factor = 1.0 - me.eps

    def apply_command(self, command):
        state["commands"] += 1
        if not state["flow_limit_checked"]:
            state["flow_limit_checked"] = True
            state["flow_limit_is_none"] = self.model.actuator.reference.flow_limit is None
            if not state["flow_limit_is_none"]:
                raise RuntimeError("flow limit is on: this wrapper is for the flow-off row")
        if state["first_contact_t_s"] is None:
            fn = self.truth().F_contact_n_N
            if float(max(fn)) > CONTACT_N:
                state["first_contact_t_s"] = float(command.t_s)
                state["first_contact_F_N"] = [float(v) for v in fn]
            elif float(command.t_s) >= me.gate_s:
                state["scaled_commands"] += 1
                command = dataclasses.replace(command, leg_speed_m_s=command.leg_speed_m_s * factor)
        original(self, command)

    scm_engine.S9Engine.apply_command = apply_command
    run_S9.main(argv)
    code = {f: hashlib.sha256((MAIN / f).read_bytes()).hexdigest() for f in HASHED}
    side = {"eps": me.eps, "gate_s": me.gate_s, "contact_N": CONTACT_N, "state": state, "argv": argv, "code_sha256": code,
            "wrapper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "env": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OUTRIGGER_PLACEMENT")}}
    d = Path(me.out_root) / case
    d.mkdir(parents=True, exist_ok=True)
    (d / "eps_wrapper.json").write_text(json.dumps(side, indent=1), encoding="utf-8")
    print("eps_wrapper", json.dumps({k: side[k] for k in ("eps", "gate_s", "state", "env")}), flush=True)


if __name__ == "__main__":
    main()
