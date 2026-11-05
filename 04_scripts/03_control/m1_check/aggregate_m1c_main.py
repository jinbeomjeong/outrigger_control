"""Reference tables of the M1c rows outside R12 and G4 (not a verdict; criteria items of m1_criteria.md sec. 3, 4, 5).

Usage (dynamics-dev): python -I aggregate_m1c_main.py
OFF comes from m1/main.jsonl after a hash check on the rows re-run with the M1c off path. M1 pairs: VN_c2_v1-V1, VN_c2_v05-V05,
BL_v1-B1, BL_v05-B05. Output: m1c/main_reference.json.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from aggregate_m1 import effect_table, judge_pair, metrics, phase_id, row_id  # noqa: E402
from aggregate_m1c import LEGS, OUT, PR, load, zone_of  # noqa: E402

PAIR = {"VN_c2_v1": "V1", "VN_c2_v05": "V05", "BL_v1": "B1", "BL_v05": "B05"}
KEYS = ("t_ready", "F_after", "F_after_W", "n_rev", "reapp", "guard_s", "t_loc_first", "D_done", "att_last5", "pair_union", "t_back")


def merged_starts(rec):
    """Extend starts, repeated log entries of a leg within 0.5 s merged, whole run."""
    last = {}
    out = []
    for s in (rec.get("m1") or {}).get("ext_starts", []):
        if s[1] not in last or s[0] - last[s[1]] > 0.5:
            out.append((s[0], LEGS[s[1]], s[2], s[3], zone_of(s[3], s[2])))
        last[s[1]] = s[0]
    return out


def returned(rec) -> bool:
    event = rec.get("event_output")
    if event:
        return event["final_phase"] == "ready" and event["t_ready_back_s"] is not None
    return rec["final_phase"] == "ready" and rec["values"]["times"]["t_first_ready_s"] is not None


def main() -> None:
    off_rows = load(PR / "m1" / "main.jsonl")
    m1_rows = {}
    base = defaultdict(dict)
    for r in off_rows:
        if "error" in r:
            continue
        if r["job"]["variant"] == "OFF":
            base[row_id(r["job"])][phase_id(r["job"])] = r
        else:
            m1_rows[(row_id(r["job"]), r["job"]["variant"], phase_id(r["job"]))] = r
    # hash: the rows re-run on the M1c off path against the stored runs
    stored_hash = {r["job"]["case"]: r["commands_sha256"] for r in load(PR / "m1" / "hash.jsonl") if r["job"]["variant"] == "OFF"}
    checks = [(r["job"]["case"], r["commands_sha256"][:8], stored_hash[r["job"]["case"]][:8]) for r in load(OUT / "hash2.jsonl")]
    same_main = [(c, base[c][0.0]["commands_sha256"][:8] == stored_hash[c][:8]) for c in ("R4", "R9", "S1") if 0.0 in base[c]]
    print("hash2", checks, "stored main eps 0 same as stored hash", same_main)
    rows = load(OUT / "main.jsonl")
    errors = [r["job"] for r in rows if "error" in r]
    print("runs", len(rows), "errors", errors)
    per = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        if "error" not in r:
            per[row_id(r["job"])][r["job"]["variant"]][phase_id(r["job"])] = r
    fails, ret, big, effects = [], [], [], {}
    zone_tot = defaultdict(lambda: [0, 0, 0, 0])
    no_event = []
    for row, variants in sorted(per.items()):
        off = {p: metrics(r) for p, r in base[row].items()}
        off_max = max(v["n_rev"] for v in off.values())
        off_list = list(off.values())
        off_ret = {p: returned(r) for p, r in base[row].items()}
        effects[row] = {}
        for variant, recs in variants.items():
            on = {}
            for p, r in recs.items():
                if r.get("event_output") == {}:  # event never reached: the base run had no READY
                    r["event_output"] = None
                if base[row][p].get("event_output") and not r["event_output"]:
                    no_event.append((row, variant, p, r["final_phase"], r["values"]["times"]))
                    continue
                on[p] = metrics(r)
                for f in judge_pair(off[p], on[p], off_max, off_list):
                    fails.append({"row": row, "variant": variant, "phase": p, **f})
                if on[p]["n_rev"] > off_max:
                    pass
                if off_ret[p] and not returned(r):
                    ret.append({"row": row, "variant": variant, "phase": p, "final": r["final_phase"], "D_end": (r.get("state_at", {}).get("end") or {}).get("D")})
                st = merged_starts(r)
                z = zone_tot[(row, variant)]
                z[0] += len(st)
                z[1] += sum(s[4] is not None for s in st)
                z[2] += 1
                z[3] += any(s[4] for s in st)
            effects[row][variant] = {k: v for k, v in effect_table(off, on).items()}
            m1_value = []
            for p, v in on.items():
                other = m1_rows.get((row, PAIR[variant], p))
                if other is None:
                    continue
                o = metrics(other)
                for key in ("F_after", "F_after_W", "t_ready"):
                    a, b = v.get(key), o.get(key)
                    if a is not None and b is not None:
                        m1_value.append((key, round(a - b, 2), p))
            if m1_value:
                worst = {k: max((abs(x[1]), x[1], x[2]) for x in m1_value if x[0] == k) for k in {x[0] for x in m1_value}}
                big.append((row, variant, {k: w[1] for k, w in worst.items()}))
    print("fails", len(fails), Counter((f["item"], f["variant"]) for f in fails))
    for f in fails:
        print(" ", f)
    print("no event", no_event)
    print("return failures", len(ret), Counter((r["row"], r["variant"]) for r in ret))
    for r in ret[:60]:
        print(" ", r)
    print("zone (starts, in zone, runs, runs with zone)")
    for k, v in sorted(zone_tot.items()):
        print(" ", k, v)
    tot = defaultdict(lambda: [0, 0, 0, 0])
    for k, v in zone_tot.items():
        for i in range(4):
            tot[k[1]][i] += v[i]
    print("zone totals", dict(tot))
    for row, by in effects.items():
        for variant, table in by.items():
            line = [f"{k} {table[k]['effect']:+.2f}/{table[k]['scatter']:.2f}{'*' if table[k]['separated'] else ''}" for k in KEYS if k in table]
            print(f"{row:6s} {variant:10s} " + " ".join(line))
    print("vs M1 (largest difference per key)")
    for item in big:
        print(" ", item)
    # plain value table per row
    table = {}
    for row, variants in sorted(per.items()):
        for variant in ("OFF", *PAIR):
            recs = base[row] if variant == "OFF" else variants.get(variant, {})
            vals = [metrics(r) for r in recs.values() if variant == "OFF" or r.get("event_output") is not None or not base[row][next(iter(base[row]))].get("event_output")]
            if not vals:
                continue
            table[f"{row}|{variant}"] = {"F_after": sorted(v.get("F_after") for v in vals if v.get("F_after") is not None), "F_after_W": sorted(v["F_after_W"] for v in vals if "F_after_W" in v), "t_ready": [v["t_ready"] for v in vals], "pass": [v["pass_"] for v in vals if "pass_" in v], "class": sorted({str(v["class"]) for v in vals}), "failed": sorted({x for v in vals for x in v["failed"]}), "bad": sorted({x for v in vals for x in v["bad_events"]}), "rev": [v["n_rev"] for v in vals], "att": [v["att_last5"] for v in vals], "gates": sorted({g for v in vals for g in v.get("gates", [])})}
    print("values")
    for k, v in table.items():
        print(k, json.dumps(v))
    (OUT / "main_reference.json").write_text(json.dumps({"fails": fails, "return_failures": ret, "no_event": no_event, "effects": effects, "values": table, "zones": {f"{k[0]}|{k[1]}": v for k, v in zone_tot.items()}, "vs_m1": big}, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
