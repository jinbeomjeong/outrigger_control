"""List D8-type beta != 1.0 cases across bundle C batches with min true cylinder force."""
import argparse
import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ROOT = REPO_ROOT / "07_results" / "S6"
DEFAULT_BATCHES = [
    "bundleC_L1R_20261024_100736",
    "bundleC_rerun32_L1R_20261024_114455",
    "bundleC_rerun33_L1R_20261024_125604",
    "bundleC_rerun34_L1R_20261024_141040",
]

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--batches", nargs="+", default=DEFAULT_BATCHES, help="batch folders under 07_results/S6"
)
BATCHES = parser.parse_args().batches
F_GATE = 14.41458911
table = {}
for b in BATCHES:
    p = os.path.join(ROOT, b, "verify_S6C.json")
    if not os.path.exists(p):
        continue
    d = json.load(open(p, encoding="utf-8"))
    for m in d["metrics"]:
        bc = m.get("bundle_c") or {}
        beta = bc.get("beta_GPa")
        table.setdefault(m["case"], {})[b[8:20]] = (
            beta, bc.get("config"), m.get("group"), m.get("min_cyl_after_liftoff_kN"),
            m.get("min_cyl_excl_reanchor_kN"), m.get("min_cyl_t_s"), (m.get("times_s") or {}).get("liftoff"),
            m.get("min_cyl_leg"), bc.get("increment"), bc.get("amp_ramp"), bc.get("tau_v_s"),
            bc.get("command_offset_s"), bc.get("L0r_m"))
for case, rows in sorted(table.items()):
    betas = {r[0] for r in rows.values()}
    if betas <= {1.0, None}:
        continue
    for b, r in rows.items():
        beta, cfg, grp, mn, mnx, tmin, tlo, leg, inc, amp, tau, off, l0r = r
        dt = (tmin - tlo) if (tmin is not None and tlo is not None) else None
        mn_s = f"{mn:7.2f}" if mn is not None else "   None"
        dt_s = f"{dt:6.2f}" if dt is not None else "  None"
        print(f"{case:42s} {b:14s} beta={beta} cfg={cfg} grp={grp} min={mn_s} leg={leg} t-liftoff={dt_s}"
              f" inc={inc} amp={amp} tau={tau} off={off} L0r={l0r}")
