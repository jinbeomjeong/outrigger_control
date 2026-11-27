"""Distribution of len(events) per stored run_v5 line (J7 cap = 200, judge_stage1_4368.py:171).
Counts and quantiles only, split by setting family and event/steady row. Usage: events_len.py <out.json> <jsonl>..."""
import json
import sys
from collections import defaultdict

import numpy as np


def fam(s):
    s = str(s)
    return "V0" if s.startswith("V0") else ("LS*" if s.startswith("LS") else ("VB*" if s.startswith("VB") else s))


def main():
    out_path, files = sys.argv[1], sys.argv[2:]
    rep = {}
    for path in files:
        lens = defaultdict(list)
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                ev_row = bool(rec.get("event_output"))
                key = f"{fam((rec.get('job') or {}).get('setting'))}|{'event' if ev_row else 'steady'}"
                lens[key].append(len(rec.get("events") or []))
        rep[path] = {}
        for key, v in sorted(lens.items()):
            a = np.asarray(v)
            rep[path][key] = {"n": int(a.size), "max": int(a.max()), "p50": float(np.median(a)),
                              "p99": float(np.quantile(a, 0.99)), "ge100": int((a >= 100).sum()),
                              "ge150": int((a >= 150).sum()), "ge200": int((a >= 200).sum())}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1)
    print(json.dumps({"status": "ok"}))


if __name__ == "__main__":
    main()
