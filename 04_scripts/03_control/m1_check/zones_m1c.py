"""Extend starts of the M1c runs against the zones the boundary unit missed, repeated log entries merged (read only).

Usage (dynamics-dev): python -I zones_m1c.py
A start = the first entry of a leg with no other entry in the 0.5 s before it. Window: event - 0.2 s to + 3 s (the sink response).
Zone rule as in aggregate_m1c. Output: m1c/zones.json.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from aggregate_m1c import LEGS, OUT, load, zone_of  # noqa: E402


def starts(rec):
    m1 = rec.get("m1")
    if not m1 or rec.get("t_event_s") is None:
        return []
    ev = rec["t_event_s"]
    last = {}
    out = []
    for s in m1["ext_starts"]:
        t, leg = s[0], s[1]
        if leg not in last or t - last[leg] > 0.5:
            if ev - 0.2 <= t <= ev + 3.0:
                out.append((round(t - ev, 2), LEGS[leg], s[2], s[3], zone_of(s[3], s[2])))
        last[leg] = t
    return out


def main() -> None:
    report = {}
    for batch in ("r12", "g4"):
        per = defaultdict(lambda: {"starts": 0, "zone": 0, "rows": 0, "rows_zone": 0, "rows_list": [], "by_leg": defaultdict(lambda: [0, 0]), "sink_leg_first": [0, 0]})
        for rec in load(OUT / f"{batch}.jsonl"):
            if "error" in rec or not rec.get("event_output"):
                continue
            b = per[rec["job"]["variant"]]
            st = starts(rec)
            b["rows"] += 1
            b["starts"] += len(st)
            z = [s for s in st if s[4]]
            b["zone"] += len(z)
            twin = rec["job"].get("twin") or {"leg": "RR", "level": "top", "fs_kN": 4.0}
            for s in st:
                b["by_leg"][s[1]][0] += 1
                b["by_leg"][s[1]][1] += s[4] is not None
            first = [s for s in st if s[1] == twin["leg"]][:1]
            if first:
                b["sink_leg_first"][0] += 1
                b["sink_leg_first"][1] += first[0][4] is not None
            if z:
                b["rows_zone"] += 1
                fev = rec["event_output"]["min_F_after_event_kN"]
                b["rows_list"].append({"twin": [twin["level"], twin["leg"], twin["fs_kN"]], "offset": rec["job"]["offset_s"], "zone_starts": z, "F_min": round(min(fev.values()), 2), "pass": rec["event_output"]["pass"]})
        for name, b in per.items():
            b["by_leg"] = {k: v for k, v in b["by_leg"].items()}
            print(batch, name, "rows", b["rows"], "rows with a zone start", b["rows_zone"], "starts", b["starts"], "in zone", b["zone"], "by leg (n, zone)", b["by_leg"], "sink leg first start (n, zone)", b["sink_leg_first"])
            if batch == "r12":
                print("    ", [(r["offset"], r["zone_starts"], r["F_min"]) for r in b["rows_list"]][:4])
        report[batch] = {k: dict(v) for k, v in per.items()}
    for rec in load(OUT / "r12.jsonl"):
        if rec["job"]["variant"] in ("VN_c2_v1_E4", "VR_c2_v1_E4") and rec["job"]["offset_s"] == 0.0:
            print(rec["job"]["variant"], "final", rec["final_phase"], "times", rec["values"]["times"], "names", rec["event_names"], "e4 mm", rec["m1"]["e4_mm"], "end", rec["state_at"].get("end"))
    (OUT / "zones.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
