"""E1 harness-Chrono pair statistics split by pad (read-only).

Pad of a pair: 'A' if the Chrono case name has '_A_' or the harness id has '|A|' (one-pad soft runs on pad A
would carry 'PA'); everything else is pad B (the S9 default).  Same statistics as the file summary:
verdict_same count, d_ready_s (C - H), d_gap_ready_mm, d_max_stroke_reading_mm (all and uncensored),
by variable x side.  Also lists the A2 slope pairs (Table 3).
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

p = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9\rev85\harness_chrono_pairs.json")
doc = json.loads(p.read_text(encoding="utf-8"))
pairs = doc["pairs"]


def pad_of(r):
    c, h = r["chrono_case"], r["harness_id"] or ""
    if "_A_" in c or "|A|" in h or "|PA" in h:
        return "A"
    return "B"


def rng(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "n 0"
    return f"n {len(vals)}, {min(vals):+.3f} ~ {max(vals):+.3f}, mean {sum(vals)/len(vals):+.3f}"


for sel_name, sel in (("all", pairs), ("pad B", [r for r in pairs if pad_of(r) == "B"]),
                      ("pad A", [r for r in pairs if pad_of(r) == "A"])):
    d = [r["delta"] for r in sel]
    print(f"== {sel_name}: pairs {len(sel)}, verdict_same {sum(1 for x in d if x.get('verdict_same'))}")
    print("   d_ready_s     ", rng([x.get("d_ready_s") for x in d]))
    print("   d_gap_ready_mm", rng([x.get("d_gap_ready_mm") for x in d]))
    print("   d_stroke all  ", rng([x.get("d_max_stroke_reading_mm") for x in d]))
    print("   d_stroke uncens", rng([x.get("d_max_stroke_reading_mm") for r, x in zip(sel, d) if not r.get("censored_at_guard")]))
    print("   minF ratio h/c", rng([x.get("minF_ratio_h_over_c") for x in d]))
    by = defaultdict(Counter)
    for r in sel:
        by[r["variable"]][r["side"]] += 1
    print("   by variable x side:", {k: dict(v) for k, v in sorted(by.items())})
    if sel_name == "pad B":
        by_v = defaultdict(list)
        for r in sel:
            by_v[r["variable"]].append(r)
        for v, rs in sorted(by_v.items()):
            dd = [r["delta"] for r in rs]
            print(f"   [{v}] pairs {len(rs)} same {sum(1 for x in dd if x.get('verdict_same'))}; READY {rng([x.get('d_ready_s') for x in dd])}; gap {rng([x.get('d_gap_ready_mm') for x in dd])}")
print("== A2 pairs (Table 3 slope)")
for r in pairs:
    if r["variable"].startswith("A2"):
        x = r["delta"]
        print(f"   {pad_of(r)} {r['variable']:<12} {r['chrono_case']:<55} {r['harness_id']:<40} side {r['side']:<15} "
              f"same {x.get('verdict_same')} dR {x.get('d_ready_s')} dgap {x.get('d_gap_ready_mm')} dS {x.get('d_max_stroke_reading_mm')} "
              f"C {r['chrono'].get('verdict')} H {r['harness'].get('verdict')}")
print("== pad A pair list")
for r in pairs:
    if pad_of(r) == "A":
        print("  ", r["variable"], r["chrono_case"], r["harness_id"])
