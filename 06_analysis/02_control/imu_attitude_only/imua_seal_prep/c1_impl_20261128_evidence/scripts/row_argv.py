"""Print the full argv tail and start env of named C-5 rows of the 436.8 manifest."""
import json
import sys
from pathlib import Path

doc = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
want = set(sys.argv[2:])
for name, b in doc["batches"].items():
    for r in b["rows"]:
        if r.get("case") in want:
            print(name, r["case"], json.dumps({k: r.get(k) for k in ("argv_tail", "start_env", "planned_pool",
                                                                       "controller", "est_s")}))
