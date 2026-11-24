"""Check: is the read after each breach read below its bound, and are breach legs distinct per row?"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

rdir, inp = Path(sys.argv[1]), Path(sys.argv[2])
LEGS = ("FL", "FR", "RL", "RR")
for name, sub in (("confirm_b", "confirm_b/confirm_b_t4h"), ("sens", "sens/sens_t4h")):
    rep = json.loads((rdir / f"jp3_p2_{name}.json").read_text(encoding="utf-8"))
    files = {l["line"]: l["t4h"]["file"] for l in rep["lines"] if l.get("t4h")}
    res, legs_distinct = Counter(), Counter()
    for b in rep["breach_rows"]:
        legs_distinct[len({x["leg"] for x in b["reads"]}) == len(b["reads"])] += 1
        with np.load(inp / sub / files[b["line"]], allow_pickle=False) as z:
            ptr, ext = z["jp3_p_tr_Pa"], z["jp3_ext_bound_Pa"]
        for x in b["reads"]:
            i, n = LEGS.index(x["leg"]), x["jp3_read"]
            res[bool(ptr[n + 1, i] <= ext[n + 1, i] + 1.0)] += 1
    print(name, "next read within bound:", res, "breach legs distinct per row:", legs_distinct)
