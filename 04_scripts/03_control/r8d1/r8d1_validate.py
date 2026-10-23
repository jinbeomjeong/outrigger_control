import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, time
import numpy as np
import r8d1_lin as R
import c2_linear as cl
tags = ["bottom_pads_b1.6_sup_upper", "middle_pads_b1.6_sup_upper", "top_pads_b1_sup_lower_k0.5-1-1-0.5"]
cat = {c.tag(): c for c in R.rcd.catalogue(full=True)}
ref = json.load(open(r"C:\workspace\outrigger_control\06_analysis\02_control\r8_10hz\r8_lin.json"))
rows = dict((t, r) for t, r in ref["rows"])
t0 = time.perf_counter()
for t in tags:
    lp = cl.build_plant(cat[t])
    cfg = R.Cfg(T=0.1, N=1, d=1, tau_v=0.0, Kp=0.4, Ki=0.02, tau_f=0.5)
    r, _ = R.analyse(lp, cfg)
    print(t, "new", {c: round(r[c]["Ms"], 6) for c in R.CH}, "old", {c: round(v, 6) for c, v in rows[t]["T0.1_prop_d1"]["Ms_by_ch"].items()})
    # eq-model check: N=5 at T=0.02 equals nothing; instead check T=0.02,N=1,d=1 vs T0.02_prop_d1
    cfg2 = R.Cfg(T=0.02, N=1, d=1, Kp=0.4, Ki=0.02, tau_f=0.5)
    r2, _ = R.analyse(lp, cfg2)
    print("   T0.02", {c: round(r2[c]["Ms"], 6) for c in R.CH}, "old", {c: round(v, 6) for c, v in rows[t]["T0.02_prop_d1"]["Ms_by_ch"].items()})
print("wall", time.perf_counter() - t0)
