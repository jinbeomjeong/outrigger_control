"""Law C 1-DoF replica (copy of run_s6_check.replica) with FL and RL parameters, dt 2e-4 / 1e-5, lag 0 / 1.

usage: v11b_replica_rl.py [verify_S6_L1_infra.json]   (default: the S6 infra verify JSON)
rev. 30: v_max and the extend / retract force limits are taken per leg from the run metadata
(model.max_speed_m_s, model.force_limits_N) instead of the literals 0.68/30, 218124.7 / 18555.0, so the per-leg
REXOME35 limits are used for new batches.
"""
import ast
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control")
src = (ROOT / "04_scripts/01_dynamics/run_s6_check.py").read_text(encoding="utf-8")
tree = ast.parse(src)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "replica")
ns = {"np": np, "math": math, "G": 9.80665, "RAMP": 0.1, "T_SAT": 2e-3}
exec(compile(ast.Module([fn], []), "replica", "exec"), ns)
VJ = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "06_analysis/01_chrono/16_S6/verify_S6_L1_infra.json"
V = json.loads(VJ.read_text(encoding="utf-8"))
for leg in ("FL", "RL"):
    m = V["v11b"][f"v11b_{leg}_dt2e-4"]["model"]
    k, c, mr = m["spring"]["k_N_m"], m["spring"]["c_N_s_m"], m["rod_mass_kg"]
    f_ext, f_ret = (float(x) for x in m["force_limits_N"])
    ns.update(V_MAX=float(m["max_speed_m_s"]), F_EXT=f_ext, F_RET=f_ret,
              PHASES={"extend": (0.1, 3.0, 1.0, f_ext), "retract": (3.0, 5.5, -1.0, f_ret)})
    for dt in (2e-4, 1e-5):
        for lag in (0, 1):
            r = ns["replica"](dt, "C", k, c, mr, lag)
            ref = c * ns["V_MAX"] / k * 1e6
            e, rt = r["extend"]["creep_from_first_um"], r["retract"]["creep_from_first_um"]
            print(f"{leg} dt {dt:g} lag {lag}: ref {ref:.2f} um, replica {e:.2f} / {rt:.2f} um,"
                  f" replica - v dt {e - ns['V_MAX']*dt*1e6:.2f} / {rt - ns['V_MAX']*dt*1e6:.2f} um")
