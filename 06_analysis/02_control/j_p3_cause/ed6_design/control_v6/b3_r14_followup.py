"""R14 rows (j9_main 606f8713 VBJ and LSJ): does a re-approach follow the R-5 prediction? (read only)

Prints, per R14 row, the R-5 relevel_predicted events, the re-approach start/contact events and
the minimum leg force after the event (E-3 and the 10 Hz T4h minimum of the predicted leg).
Output: b3_r14_followup.json (this folder). control-expert 2026-11-23.
"""
import json
from pathlib import Path

import numpy as np

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\606f8713\j9main_a1")
OUT = Path(__file__).resolve().parent
LEGS = ("FL", "FR", "RL", "RR")
res = []
with open(RUN / "j9_main.jsonl", encoding="utf-8") as f:
    for line in f:
        d = json.loads(line)
        if d["job"]["case"] != "R14":
            continue
        z = np.load(RUN / "j9_main_t4h" / d["t4h_file"], allow_pickle=False)
        ev = json.loads(str(z["meta_json"]))["events"]
        t_ev = d["t_event_s"]
        r5 = [(round(e[0], 2), e[1]) for e in ev if e[1].startswith("relevel_predicted")]
        ra = [(round(e[0], 2), e[1]) for e in ev if e[1].startswith(("leg_reapproach", "WARN_LEG_REAPPROACH"))]
        leg = LEGS.index(r5[0][1].split(":")[1]) if r5 else None
        fmin = None
        if leg is not None:
            t = z["t_s"]
            m = t >= t_ev - 1e-9
            fmin = round(float(np.min(z["true_force_min_N"][m, leg])) / 1e3, 2)
        mfw = d["event_output"]["min_F_after_W_kN"]
        res.append({"setting": d["job"]["setting"], "key": d["t4h_file"].rsplit("_", 1)[0],
                    "t_event_s": t_ev, "relevel_predicted": r5, "reapproach_events": ra,
                    "r5_leg_min_force_10hz_kN": fmin, "E3_min_kN": min(mfw.values()),
                    "event_pass": d["event_output"]["pass"]})
(OUT / "b3_r14_followup.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
for r in res:
    print(r)
