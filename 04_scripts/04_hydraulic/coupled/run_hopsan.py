"""Run the Hopsan four-leg circuit for the scenarios (hopsancli via hopsan_run.py).

usage: run_hopsan.py [--names A B ...] [--ts 1e-5] [--tag dt1e-5] [--work <scratch dir>]
Results (selected variables, ABSOLUTE pressures as written by Hopsan) are copied to
06_analysis/03_hydraulic/coupled/hopsan/<scenario>[_tag].csv.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path.home() / ".claude" / "tools" / "hydraulics"))

from hopsan_run import run_hopsan  # noqa: E402

from build_hopsan_spec import log_vars, scenario_overrides  # noqa: E402
from params import OUT_DIR, load_params  # noqa: E402
from scenarios import BY_NAME, SCENARIOS  # noqa: E402

DEFAULT_WORK = Path(r"C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control"
                    r"\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\hyd_coupling_model\hopsan")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", nargs="*")
    ap.add_argument("--ts", type=float, default=1e-5)
    ap.add_argument("--tag", default="")
    ap.add_argument("--work", default=str(DEFAULT_WORK))
    ap.add_argument("--samples", type=int, default=2001)
    args = ap.parse_args()
    p = load_params()
    names = args.names or [s.name for s in SCENARIOS if s.hopsan]
    out_dir = OUT_DIR / "hopsan"
    out_dir.mkdir(parents=True, exist_ok=True)
    log = {}
    for name in names:
        sc = BY_NAME[name]
        work = Path(args.work) / f"{name}{args.tag}"
        df, _units, info = run_hopsan(
            HERE / "coupled_four_leg.hmf", work, sim=(0.0, args.ts, sc.t_end),
            params=scenario_overrides(p, sc), num_log_samples=args.samples,
            log_only=log_vars(), timeout=500.0)
        dest = out_dir / f"{name}{args.tag}.csv"
        shutil.copy2(info["csv"], dest)
        log[name] = {"wall_s": info["wall_s"], "ts": args.ts, "cmd": " ".join(info["cmd"]), "csv": str(dest)}
        last = df.iloc[-1]
        print(name, info["wall_s"], "s; v[mm/s]",
              [round(float(last[f"Mass{leg}#P2#Velocity"]) * 1e3, 3) for leg in ("FL", "FR", "RL", "RR")],
              "pP[bar g]", round((float(last["Pump#P2#Pressure"]) - 1e5) / 1e5, 2),
              "ph", [round((float(last[f"Spool{leg}#PA#Pressure"]) - 1e5) / 1e5, 2) for leg in ("FL", "FR", "RL", "RR")],
              "Qbyp[L/min]", round(float(last["Unloader#P2#Flow"]) * 6e4, 3))
    path = out_dir / f"run_log{args.tag}.json"
    old = json.loads(path.read_text()) if path.exists() else {}
    old.update(log)
    path.write_text(json.dumps(old, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
