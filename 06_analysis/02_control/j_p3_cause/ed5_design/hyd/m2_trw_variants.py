"""TRw existence in the saved VBJ0 T4h for two readings of the definition (output command
columns, stroke reading; no judgement values). A carry starts at output read k with
|u_k-1| <= u_hold and u_k < -u_hold and lasts while u < -u_hold (last output read j-1); the reads
whose acting command is that carry are k+1 .. j. Witness: s_ref - s_n >= 1.0 mm, s_ref = s_k-1.
  first: only the first such carry after LEVEL entry (the TR' carry)
  any:   the first carry after LEVEL entry in which a witness occurs"""
import json
from collections import Counter
from pathlib import Path

import numpy as np

import sys

REF_SHIFT = int(sys.argv[1]) if len(sys.argv) > 1 else 0
"""0: s_ref = s_(k-1) (read before the output carry); 1: s_ref = s_k (trigger read)."""
CONTINUING = len(sys.argv) > 2 and sys.argv[2] == "cont"
RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\78fd5d2d\dg3_a1")
U_HOLD, W = 2.0924e-4, 1.0e-3
res = {"first": Counter(), "any": Counter()}
legs = 0
for line in json.loads((RUN / "dg3_VBJ0.json").read_text(encoding="utf-8"))["results"]:
    with np.load(RUN / "VBJ0_t4h" / line["t4h_file"], allow_pickle=False) as z:
        u, s, ph = z["command_m_s"], z["motor_stroke_m"], [str(p).upper() for p in z["phase"]]
    lv = [i for i, p in enumerate(ph) if p == "LEVEL"]
    if not lv:
        continue
    for leg in range(4):
        legs += 1
        k, first = lv[0], True
        while k < len(u):
            if k >= 1 and abs(u[k - 1, leg]) <= U_HOLD and u[k, leg] < -U_HOLD:
                j = k
                while j < len(u) and u[j, leg] < -U_HOLD:
                    j += 1
                last = j if not CONTINUING else j - 1  # CONTINUING: output still retract at n
                reads = np.arange(k + 1, min(last + 1, len(u)))
                ref = s[k - 1 + REF_SHIFT, leg]
                hit = reads[(ref - s[reads, leg]) >= W] if reads.size else reads
                if hit.size:
                    if first:
                        res["first"][ph[k]] += 1
                    res["any"][ph[k]] += 1
                    break
                first = False
                k = j
            k += 1
out = {"legs": legs, **{m: {"total": sum(c.values()), **dict(c)} for m, c in res.items()}}
out["ref_shift"] = REF_SHIFT
out["continuing"] = CONTINUING
Path(__file__).with_name(f"m2_trw_variants_ref{REF_SHIFT}{'_cont' if CONTINUING else ''}.json").write_text(json.dumps(out, indent=1), encoding="utf-8", newline="\n")
print(json.dumps(out, indent=1))
