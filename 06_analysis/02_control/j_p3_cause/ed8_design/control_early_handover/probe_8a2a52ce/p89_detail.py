"""P8-9 detail of the condition (3) failures (record, not part of the rule): event output fields
of A vs the candidate on the failing keys. Output p89_detail_out.txt.

Usage: conda run -n dynamics-dev python -I -B p89_detail.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
recs = [json.loads(x) for x in (HERE / "raw" / "runs.jsonl").read_text("utf-8").splitlines()]
CASES = [("R12", 0.075, "FR", 4.0, ("A", "H3")), ("R15", 0.05, None, None, ("A", "H3")),
         ("R15", 0.0, None, None, ("A", "H1"))]
FIELDS = ("run_after_s", "final_phase", "t_ready_back_s", "att_end_deg", "max_att_change_deg",
          "gates", "margins", "n_late_starts", "sign_changes", "warnings", "lifts",
          "min_F_after_W_kN", "min_F_after_event_kN", "after_window_force")
out = []
for case, off, leg, fs, arms in CASES:
    for r in recs:
        j = r["job"]
        arm = j["setting"].split("-")[1]
        if j["case"] != case or j.get("offset_s") != off or arm not in arms:
            continue
        tw = j.get("twin") or {}
        if leg is not None and (tw.get("leg") != leg or tw.get("fs_kN") != fs
                                or tw.get("level") != "bottom"):
            continue
        eo = r.get("event_output") or {}
        out.append(f"== {case} o{off} {tw} {arm} t_event {r.get('t_event_s')} "
                   f"final {r.get('final_phase')}")
        out.append(f"   times {r['values'].get('times')}")
        out.append(f"   attitude {r['values'].get('attitude')}")
        for f in FIELDS:
            out.append(f"   {f}: {json.dumps(eo.get(f), default=str)[:900]}")
        out.append(f"   event_names {r.get('event_names')}")
        tail = [e for e in r.get("events") or []][-12:]
        out.append(f"   last WARN/FAULT events {tail}")
text = "\n".join(out)
(HERE / "p89_detail_out.txt").write_text(text, "utf-8")
print(text.encode("ascii", "replace").decode())
