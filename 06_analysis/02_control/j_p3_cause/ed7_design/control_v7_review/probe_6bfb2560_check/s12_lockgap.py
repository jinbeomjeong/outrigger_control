"""D part: ④ (model bound) - truth on the locked reads of the condition legs inside the first PROBE
window after the event, before the locked_ext -> moving_ext transition; carry reads split by the
plant state at the read."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
           r"\6bfb2560\ed7_probe_a1")
OUT = Path(sys.argv[1])
LEGS = ["FL", "FR", "RL", "RR"]
rows = []
with (RUN / "ed7_probe.jsonl").open(encoding="utf-8") as fh:
    for text in fh:
        rec = json.loads(text)
        if rec["ed7_probe"]["part"] != "d":
            continue
        name, te = rec["t4h_file"], float(rec["t_event_s"])
        ebc = rec["hydraulics_record"]["extend_bound_check"]
        with np.load(RUN / "ed7_probe_t4h" / name) as d:
            cls = [str(s) for s in d["jp3_class_names"]]
            pst = [str(s) for s in d["jp3_plant_state_names"]]
            ph = np.array([str(p).lower() for p in d["phase"]])
            t = d["t_s"]
            idx = np.flatnonzero((ph == "probe") & (t >= te))
            a = b = int(idx[0])
            while b + 1 < len(ph) and ph[b + 1] == "probe":
                b += 1
            jt = d["jp3_t_s"]
            ins = np.flatnonzero((jt >= t[a] - 1e-9) & (jt <= t[b] + 1e-9))
            st, cl = d["jp3_plant_state"][ins], d["jp3_class"][ins]
            model, used, ptr = (d["jp3_model_bound_Pa"][ins], d["jp3_used_bound_Pa"][ins],
                                d["jp3_p_tr_Pa"][ins])
            for leg in range(4):
                tr = [k for k in range(1, len(ins)) if st[k - 1, leg] == pst.index("locked_ext")
                      and st[k, leg] == pst.index("moving_ext")]
                if not tr:
                    continue
                kt = tr[0]
                # locked stretch before the transition (contiguous locked_ext reads)
                k0 = kt - 1
                while k0 - 1 >= 0 and st[k0 - 1, leg] == pst.index("locked_ext"):
                    k0 -= 1
                lock_sel = [k for k in range(k0, kt) if cl[k, leg] == cls.index("lock")
                            and np.isfinite(model[k, leg])]
                carry = [k for k in range(len(ins)) if cl[k, leg] == cls.index("carry_ext")]
                c_locked = [k for k in carry if st[k, leg] == pst.index("locked_ext") or k == kt]
                c_moving = [k for k in carry if k not in c_locked]
                rows.append({
                    "key": name.split("_P7-")[0], "plant": rec["ed7_probe"]["plant"], "leg": LEGS[leg],
                    "lock_reads": len(lock_sel),
                    "lock_min_model_minus_truth_bar": (min((model[k, leg] - ptr[k, leg]) / 1e5 for k in lock_sel)
                                                      if lock_sel else np.nan),
                    "carry_at_release_min_gap_bar": min((used[k, leg] - ptr[k, leg]) / 1e5 for k in c_locked),
                    "carry_moving_min_gap_bar": (min((used[k, leg] - ptr[k, leg]) / 1e5 for k in c_moving)
                                                 if c_moving else np.nan),
                    "carry_moving_used_bar": (min(used[k, leg] / 1e5 for k in c_moving) if c_moving else np.nan),
                    "carry_moving_truth_bar": (max(ptr[k, leg] / 1e5 for k in c_moving) if c_moving else np.nan),
                    "ebc_locked_min_gap_bar_line": min(ebc["locked_min_gap_bar"]),
                    "ebc_jp3a_min_gap_bar_line": (min(ebc["jp3a_min_gap_bar"]) if isinstance(ebc.get("jp3a_min_gap_bar"), list)
                                                  else ebc.get("jp3a_min_gap_bar"))})
df = pd.DataFrame(rows)
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 200)
print(df.groupby("plant")[["lock_min_model_minus_truth_bar", "carry_at_release_min_gap_bar",
                           "carry_moving_min_gap_bar", "ebc_locked_min_gap_bar_line",
                           "ebc_jp3a_min_gap_bar_line"]].agg(["min", "median"]).T.to_string())
print(df.sort_values("lock_min_model_minus_truth_bar").head(8).to_string(index=False))
print("legs:", len(df))
df.to_csv(OUT / "d_lock_gaps.csv", index=False)
