"""Print a compact table from jp_values.json."""
import json
import sys
from pathlib import Path

d = json.loads(Path(sys.argv[1]).read_text("utf-8"))
lines = []
K3 = "3 F_min (1 ms)"
KM5 = "item 9 M5 closed loop: min true / under F_min [s] / lifted [s]"
KJP = "item 9 J_P M1 missed / M1' late / M3 median / M2 / M4 max (record)"
KJC = "item 9 J_C M1 missed / M1' late / M3 median / M2 / M4 max (record)"
for key, v in d["cases"].items():
    r = v.get("rows") or {}
    g = lambda k: (r.get(k) or {}).get("value")
    pas = lambda k: (r.get(k) or {}).get("passed")
    legs = v.get("legs_after_event") or {}
    lmin = {l: (round(x["min_interval_kN"], 3), round(x["under_F_min_interval_s"], 3), round(x["airborne_s"], 3),
                round(x["min_sample_1ms_kN"], 3)) for l, x in legs.items()}
    rr = {k: x["value"] for k, x in r.items() if "re-READY" in k}
    lines.append(f"## {key}")
    lines.append(f" ready {v.get('ready_t_s')} event {v.get('event_t_s')} phase {v.get('phase_at_event')} end {v.get('s8_end')} wall {v.get('wall_s')}")
    lines.append(f" row3 {g(K3)} pass {pas(K3)} | M5 {g(KM5)} | J_P {g(KJP)} | J_C {g(KJC)}")
    lines.append(f" legs after event (min_int kN, under_F_min s, airborne s, min_1ms) {lmin}")
    lines.append(f" re-READY rows {rr}")
    lines.append(f" warn_fault {v.get('warn_fault')} dip {v.get('touch_dip_held')} reanchor {v.get('reanchor_events')}")
    lines.append(f" events {v.get('events')}")
    lines.append(f" failed {v.get('failed_rows_all')}")
    lines.append(f" first_diff {v.get('first_diff_vs_v4recheck_t_s')} flow {json.dumps(v.get('flow_limit'))[:200]}")
    lines.append(f" tag {v.get('controller_tag')} v5 {json.dumps(v.get('v5_keys'))[:300]}")
lines.append("ITEMS: " + " || ".join(d["all_items_example"]))
Path(sys.argv[2]).write_text("\n".join(lines), "utf-8")
print("ok")
