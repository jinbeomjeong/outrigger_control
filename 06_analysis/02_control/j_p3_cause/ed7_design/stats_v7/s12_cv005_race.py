"""Ed. 7 Q7-S1 addendum (hydraulics h7 H5): at c_v 0.005 the P1 threshold c_v v_max = 0.105 mm/s
is below u_hold, so a locked leg with a band command 0.105 < |u| <= 0.209 mm/s releases after a
line fill of 0.43..2.89 s (hydraulics 5). Race between the A(i)-b trigger and the release.
stats-design-expert, 2026-11-24. Uses simulate() of s10_blind_trigger.py (same folder).
Fill time t_f is set through need = flow * t_f (flow 'full' = u, 'sub' = u - 0.105).
Outputs (argv[1]): s12_cv005_race.json / .txt. stdout: status only.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("s10", HERE / "s10_blind_trigger.py")
s10 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s10)


def main() -> int:
    out_dir = Path(sys.argv[1])
    rng = np.random.default_rng(20261114)
    R = 2000
    res = {}
    for flow in ("full", "sub"):
        for u_b in (0.15, 0.20):
            v = u_b if flow == "full" else u_b - 0.005 * s10.VMAX
            for t_f in (0.43, 1.5, 2.89):
                for n in (20, 25, 30):
                    r = s10.simulate(R, rng, n_blind=n, s_still=0.10, witness="flush", u_pre=0.0,
                                     n_pre=1, u_b=u_b, c_v=0.005, flow=flow, need=v * t_f,
                                     locked0=True, horizon_s=15.0, max_trig=1)
                    kb = r["k_band0"]
                    trig = r["first_trig"] >= 0
                    t_trig = np.where(trig, (r["first_trig"] - kb) * s10.T, np.nan)
                    # release time (fill done) ~ 2 cycles delay + t_f after the band output starts
                    t_rel = 0.2 + t_f
                    res[f"{flow}|u{u_b}|v{v:.3f}|tfill{t_f}|N{n}"] = {
                        "P_trigger_15s": float(trig.mean()),
                        "P_trigger_before_release": float((trig & (t_trig < t_rel)).mean()),
                        "P_trigger_after_release": float((trig & (t_trig >= t_rel)).mean()),
                        "t_trig_q50": float(np.nanmedian(t_trig)) if trig.any() else None}
    (out_dir / "s12_cv005_race.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    L = [f"{k:<36} trig {100*v['P_trigger_15s']:5.1f}% before-release {100*v['P_trigger_before_release']:5.1f}% "
         f"after-release {100*v['P_trigger_after_release']:5.1f}% t50 {v['t_trig_q50']}" for k, v in res.items()]
    (out_dir / "s12_cv005_race.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
