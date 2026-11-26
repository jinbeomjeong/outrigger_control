"""eps (approach-speed scale before the first touch) alias check on the stored edition 7 lines.

For every (src, setting, case, offset/twin) group with several eps, compare the eps pairs on
  * commands_sha256 (bit alias),
  * the 10 Hz phase times (values.times: t_check_start, t_touch_end, t_first_done, t_first_ready),
  * the discrete event counts (event_names) and command_stats (reversal / start counts).
"Discrete alias" = all phase times equal and event counts and command_stats equal.

Usage: python -I -B u05_eps_alias.py <out_folder> <label>=<jsonl> ...
"""
import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 300)
out = Path(sys.argv[1])
groups = defaultdict(list)
for arg in sys.argv[2:]:
    label, path = arg.split("=", 1)
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            if "error" in r:
                continue
            job = r["job"]
            if job.get("twin") or job.get("offset_s") is not None:
                continue  # event rows: no eps axis
            times = (r.get("values") or {}).get("times") or {}
            key = (label, job["setting"], job["case"], job.get("decision"), job.get("eta_v"))
            groups[key].append({
                "eps": float(job.get("eps", 0.0)), "sha": r.get("commands_sha256"),
                "times": tuple(round(float(times[k]), 3) if times.get(k) is not None else None
                               for k in ("t_check_start_s", "t_touch_end_s", "t_first_done_s",
                                         "t_first_ready_s")),
                "events": json.dumps(r.get("event_names"), sort_keys=True),
                "cstats": json.dumps(r.get("command_stats"), sort_keys=True),
                "final": r.get("final_phase")})
rows = []
for key, lst in groups.items():
    for a, b in combinations(sorted(lst, key=lambda x: x["eps"]), 2):
        if a["eps"] == b["eps"]:
            continue
        same_times = a["times"] == b["times"]
        rows.append({"src": key[0], "setting": key[1], "case": key[2], "decision": key[3],
                     "eps_a": a["eps"], "eps_b": b["eps"], "same_sha": a["sha"] == b["sha"],
                     "same_times": same_times, "same_events": a["events"] == b["events"],
                     "same_cstats": a["cstats"] == b["cstats"],
                     "discrete_alias": same_times and a["events"] == b["events"]
                     and a["cstats"] == b["cstats"],
                     "t_touch_end_a": a["times"][1], "t_touch_end_b": b["times"][1],
                     "t_ready_a": a["times"][3], "t_ready_b": b["times"][3]})
df = pd.DataFrame(rows)
df.to_csv(out / "u05_eps_pairs.csv", index=False)
summ = df.groupby(["src", "eps_a", "eps_b"])[["same_sha", "same_times", "same_events",
                                               "same_cstats", "discrete_alias"]].mean().round(3)
summ["n"] = df.groupby(["src", "eps_a", "eps_b"]).size()
print(summ.to_string())
summ.to_csv(out / "u05_eps_summary.csv")
s7 = df[df["case"] == "S7"]
print("\n== S7 ==")
print(s7[["src", "setting", "eps_a", "eps_b", "same_sha", "same_times", "discrete_alias",
          "t_touch_end_a", "t_touch_end_b", "t_ready_a", "t_ready_b"]].to_string())
ctrl = df.assign(newc=df["setting"].str.startswith(("VBM", "LSM")))
print("\n== discrete alias by controller family (VBM/LSM vs other) and eps pair ==")
print(ctrl.groupby(["newc", "eps_a", "eps_b"])["discrete_alias"].agg(["mean", "size"]).round(3).to_string())
print("\n== same t_touch_end (first-touch phase end) by eps pair ==")
df["same_touch"] = df["t_touch_end_a"] == df["t_touch_end_b"]
print(df.groupby(["eps_a", "eps_b"])["same_touch"].agg(["mean", "size"]).round(3).to_string())
