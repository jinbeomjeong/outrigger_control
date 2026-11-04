"""Hopsan runs of the criteria 8.3 corner points (dp_c, dp_ls); same scenario overrides otherwise.

usage: run_hopsan_sens.py <dp_c bar> <dp_ls bar> <tag> <scenario> [<scenario> ...]
Writes hopsan/<scenario><tag>.csv.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path.home() / ".claude" / "tools" / "hydraulics"))

from hopsan_run import run_hopsan  # noqa: E402

from build_hopsan_spec import log_vars, scenario_overrides  # noqa: E402
from params import LEGS, OUT_DIR, load_params  # noqa: E402
from run_hopsan import DEFAULT_WORK  # noqa: E402
from scenarios import BY_NAME  # noqa: E402


def main() -> None:
    dpc, dpls, tag, names = float(sys.argv[1]) * 1e5, float(sys.argv[2]) * 1e5, sys.argv[3], sys.argv[4:]
    p = load_params().with_(dp_comp=dpc, dp_unl=dpls)
    for name in names:
        sc = BY_NAME[name]
        df, _u, info = run_hopsan(HERE / "coupled_four_leg.hmf", Path(DEFAULT_WORK) / f"{name}{tag}", sim=(0.0, 1e-5, sc.t_end),
                                  params=scenario_overrides(p, sc), num_log_samples=2001, log_only=log_vars(), timeout=500.0)
        shutil.copy2(info["csv"], OUT_DIR / "hopsan" / f"{name}{tag}.csv")
        w = df[df.index >= sc.t_end - sc.window]
        print(name, tag, "r", [round(float(w[f"Mass{leg}#P2#Velocity"].mean()) / (u * p.v_max), 4) if u else None
                               for leg, u in zip(LEGS, sc.u)],
              "pP", round((float(w["Pump#P2#Pressure"].mean()) - 1e5) / 1e5, 2))


if __name__ == "__main__":
    main()
