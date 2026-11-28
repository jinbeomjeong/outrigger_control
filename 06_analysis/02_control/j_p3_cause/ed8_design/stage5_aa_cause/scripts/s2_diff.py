"""Step 2: per duplicate slot name, the two slots (a_phase, b_shape) with their own pair and the
pair the tool's name-keyed dict gave them. Writes dup_name_pairs.csv and prints the E rows and
every failing pair."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
doc = json.loads((OUT / "slots_stage5.json").read_text(encoding="utf-8"))
slots = doc["slots"]
by_name = {}
for rec in slots:
    by_name.setdefault(rec["slot"], []).append(rec)
last = {name: recs[-1]["pair_unique"] for name, recs in by_name.items()}
last_idx = {name: recs[-1]["index"] for name, recs in by_name.items()}

rows = []
for rec in slots:
    own = rec["pair_unique"]
    tool = last[rec["slot"]]
    j = rec["condition_job"]
    t = j.get("twin", {})
    rows.append({
        "index": rec["index"], "source": rec["source"], "slot": rec["slot"],
        "offset_s": j.get("offset_s"), "depth_m": t.get("depth_m"), "ramp_s": t.get("ramp_s"),
        "layer": rec["layer"], "base_pass": rec["base_pass"],
        "own_state": own["state"], "own_tries": own["tries"], "own_aa_fail": own.get("aa_fail"),
        "tool_pair_from_index": last_idx[rec["slot"]], "tool_state": tool["state"],
        "tool_aa_fail": tool.get("aa_fail"),
        "dup_name": len(by_name[rec["slot"]]) > 1,
        "failed_items": " | ".join(rec.get("failed_items", [])),
    })
with open(OUT / "dup_name_pairs.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(r for r in rows if r["dup_name"] or r["own_aa_fail"] or r["tool_aa_fail"])

print("== E-layer slots")
for r in rows:
    if r["layer"] == "E":
        print(r["index"], r["source"], r["slot"], r["offset_s"], r["depth_m"], r["ramp_s"],
              "own", r["own_state"], r["own_aa_fail"], "tool<-", r["tool_pair_from_index"],
              r["tool_state"], r["tool_aa_fail"])
print("== all own failing pairs")
for r in rows:
    if r["own_aa_fail"]:
        print(r["index"], r["source"], r["slot"], r["layer"], r["offset_s"], r["depth_m"],
              r["ramp_s"], r["failed_items"][:400])
