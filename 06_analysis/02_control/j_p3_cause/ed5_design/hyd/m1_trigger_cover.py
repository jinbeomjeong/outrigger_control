"""TR' trigger carries in the saved VBJ0 T4h (command, phase, stroke reading columns only; no
judgement values): directed retract stroke of the trigger carry, and the existence of a
stroke-based trigger TRw (first carry after LEVEL entry whose stroke reading fell >= 1.0 mm below
the read before the carry), with the remaining run time after it."""
import json
from collections import Counter
from pathlib import Path

import numpy as np

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\78fd5d2d\dg3_a1")
U_HOLD = 2.0924e-4
WITNESS_M = 1.0e-3

lines = json.loads((RUN / "dg3_VBJ0.json").read_text(encoding="utf-8"))["results"]
phases = Counter()
tr_disp = {"LEVEL": [], "PROBE": [], "other": []}
trw = {"found": 0, "legs": 0, "phase": Counter(), "remaining_s": [], "after_level_s": []}
for line in lines:
    with np.load(RUN / "VBJ0_t4h" / line["t4h_file"], allow_pickle=False) as z:
        t, u, s, ph = z["t_s"], z["command_m_s"], z["motor_stroke_m"], z["phase"]
    names = [str(p).upper() for p in ph]
    phases.update(set(names))
    lv = [i for i, n in enumerate(names) if "LEVEL" in n]
    if not lv:
        continue
    k0 = lv[0]
    for leg in range(4):
        trw["legs"] += 1
        first_tr = None
        found = None
        k = k0 + 1
        while k < len(t):
            if abs(u[k - 1, leg]) <= U_HOLD and u[k, leg] < -U_HOLD:
                ref = s[k - 1, leg]
                j = k
                hit = None
                while j < len(t) and u[j, leg] < -U_HOLD:
                    j += 1
                # the stroke of reads up to one period after the last carry command
                stop = min(j + 1, len(t))
                disp = ref - s[k:stop, leg]
                if first_tr is None:
                    first_tr = (names[k], float(disp.max()))
                idx = np.flatnonzero(disp >= WITNESS_M)
                if idx.size:
                    hit = k + int(idx[0])
                if hit is not None and found is None:
                    found = hit
                    break
                k = j
            k += 1
        if first_tr is not None:
            key = "LEVEL" if "LEVEL" in first_tr[0] else ("PROBE" if "PROBE" in first_tr[0] else "other")
            tr_disp[key].append(first_tr[1] * 1e3)
        if found is not None:
            trw["found"] += 1
            trw["phase"][names[found]] += 1
            trw["remaining_s"].append(float(t[-1] - t[found]))
            trw["after_level_s"].append(float(t[found] - t[k0]))


def pct(v):
    return [round(float(x), 2) for x in np.percentile(v, [10, 50, 90])] if v else None


out = {"phases_seen": sorted(phases),
       "trigger_carry_directed_disp_mm": {k: {"n": len(v), "p10_p50_p90": pct(v),
                                              "ge_1mm": int(sum(x >= 1.0 for x in v))}
                                          for k, v in tr_disp.items()},
       "TRw": {"legs": trw["legs"], "found": trw["found"], "phase": dict(trw["phase"]),
               "remaining_s_p10_p50_p90": pct(trw["remaining_s"]),
               "after_level_s_p10_p50_p90": pct(trw["after_level_s"])}}
Path(__file__).with_suffix(".json").write_text(json.dumps(out, indent=1), encoding="utf-8", newline="\n")
print(json.dumps(out, indent=1))
