"""Rev. 51: of the rod falls > 100 bar (s8main_rod_steps.py output), how many happened while the
plant valve was still locked (|u_applied| <= 1e-6 m/s over the whole past period, 1 ms truth via
s_motor change < 1 um) and with the leg airborne: the lift-off collapse signature.

Usage: python -I s8main_rod_steps_lock.py <rod_steps_json>
"""
import json
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
f = json.load(open(sys.argv[1], encoding="utf-8"))["falls"]
locked = [x for x in f if x["u_applied_start"] <= 1e-6 and x["s_motor_ptp_m"] < 1e-6]
print(f"falls {len(f)}; plant locked over the period {len(locked)}")
print("  locked by reason:", dict(Counter(x["reason"] for x in locked)))
la = [x for x in locked if x["air_frac"] > 0.5 and x["dph_bar"] < 0]
print(f"  locked + airborne + head falling (lift-off collapse): {len(la)}; reasons {dict(Counter(x['reason'] for x in la))}")
for x in la[:40]:
    print(f"    {x['case']} {x['t_s']:.2f} {x['leg']}: dpr {x['dpr_bar']:+.1f} dph {x['dph_bar']:+.1f} new {x['new_rod_bar']:.1f} cmd now {x['cmd_now']:+.2e} before {x['cmd_before']:+.2e} air {x['air_frac']:.2f} {x['reason']}")
