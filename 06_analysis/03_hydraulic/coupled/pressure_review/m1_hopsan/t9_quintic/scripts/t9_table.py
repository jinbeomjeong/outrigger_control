"""Tables of the quintic replay against the harness 1 ms series."""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

BASE = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\pressure_review")
OUT = BASE / "m1_hopsan" / "t9_quintic"
rows = json.loads((OUT / "replay.json").read_text(encoding="utf-8"))
SCR = Path(__file__).resolve().parent / "t9"
agg = defaultdict(list)
for r in rows:
    h = np.load(BASE / "m1b" / "series_r12" / f"R12_{r['commands']}_{r['offset']}.npz")
    th, Fh = h["t"], h["F"] / 1e3
    k = th > 0
    agg[(r["circuit"], r["commands"])].append({"off": r["offset"], "RR": r["F_min_kN"]["RR"], "t": r["F_min_t_s"]["RR"], "hRR": float(Fh[k, 3].min()), "ht": float(th[k][np.argmin(Fh[k, 3])]),
                                               "FL": r["F_min_kN"]["FL"], "FR": r["F_min_kN"]["FR"], "RL": r["F_min_kN"]["RL"]})
summary = {}
print("circuit cmds | Hopsan RR min per phase | t_min | harness same commands | harness t | FL FR RL min")
for key, v in agg.items():
    print(key, [round(x["RR"], 2) for x in v], [round(x["t"], 2) for x in v], "| h", [round(x["hRR"], 2) for x in v], [round(x["ht"], 2) for x in v], "| FL", round(min(x["FL"] for x in v), 1), "FR", round(min(x["FR"] for x in v), 1), "RL", round(min(x["RL"] for x in v), 1))
    summary[str(key)] = v
base = {(r["circuit"], r["commands"], r["offset"]): r for r in rows}
print("\nvs nocheck same commands: delta RR min")
for c in ("vent", "vent_ref", "block"):
    for cmd in ("OFF", "V1", "B1"):
        d = [base[(c, cmd, o)]["F_min_kN"]["RR"] - base[("nocheck", cmd, o)]["F_min_kN"]["RR"] for o in (0.0, 0.025, 0.05, 0.075)]
        print(c, cmd, np.round(d, 2).tolist())
print("\nmarks, offset 0.025")
for c, cmd in (("nocheck", "OFF"), ("vent", "OFF"), ("vent", "V1"), ("vent_ref", "V1"), ("block", "B1")):
    r = base[(c, cmd, 0.025)]
    print(c, cmd)
    for key in ("+1", "+1.2", "+1.4", "+1.6", "+1.8", "+2", "+2.5"):
        m = r["marks"][key]
        print("  ", key, "F", m["F"], "ph", m["p_h"], "pr", m["p_r"], "la", m["line_a"], "lb", m["line_b"])
    if "checks" in r:
        for leg, x in r["checks"].items():
            print("   ", leg, {k: (round(y, 3) if y is not None else None) for k, y in x.items()})
print("\nharness at marks, offset 0.025")
for tag in ("OFF", "V1", "B1", "VR_c2_v1", "VN_c2_v1", "BL_v1"):
    h = np.load(BASE / "m1b" / "series_r12" / f"R12_{tag}_0.025.npz")
    print(tag, {f"+{v:g}": (h["F"][int(np.searchsorted(h["t"], v))] / 1e3).round(1).tolist() for v in (1.0, 1.2, 1.4, 1.6, 1.8, 2.0)})
print("\nRR rod state vent: time series, offset 0.025")
for c, cmd in (("vent", "V1"), ("vent", "OFF"), ("vent_ref", "V1")):
    d = np.load(SCR / f"{c}_{cmd}_0.025.npz")
    t = d["t"]
    print(c, cmd)
    for v in (0.2, 0.4, 0.6, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6):
        j = int(np.argmin(np.abs(t - v)))
        print("  ", v, "F", round(d["F"][j, 3] / 1e3, 1), "pr", round(d["pr"][j, 3] / 1e5, 1), "lb", round(d["lb"][j, 3] / 1e5, 1), "ph", round(d["ph"][j, 3] / 1e5, 1), "la", round(d["la"][j, 3] / 1e5, 1), "rod", int(d["ob"][j, 3] > 0.5), "head", int(d["oa"][j, 3] > 0.5), "u", round(float(np.interp(v, d["grid"], d["u"][:, 3])) * 1e3, 2))
    w = (t > 0) & (t < 2.0)
    print("   head check open fraction, 0..2 s", round(float((d["oa"][w, 3] > 0.5).mean()), 3), "rod", round(float((d["ob"][w, 3] > 0.5).mean()), 3), "p_r max", round(float(d["pr"][w, 3].max()) / 1e5, 1))
(OUT / "replay_table.json").write_text(json.dumps(summary, indent=0), encoding="utf-8")
