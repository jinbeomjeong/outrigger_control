"""Print the soil-rule meta (bias per corner, settle attitude, LOC log) of an s9 result file."""
import json
import sys

d = json.loads(open(sys.argv[1], encoding="utf-8").read())
flt = sys.argv[2] if len(sys.argv) > 2 else ""
for r in d["runs"]:
    if flt in r["id"] and "soil_rule_meta" in r:
        m = r["soil_rule_meta"]
        print(r["id"], "raw", m.get("bias_corner_raw_mm"), "used", m.get("bias_corner_mm"), "settle",
              m.get("settle_att_deg"), "c@P", round(m["clear_est_at_P_mm"] or 0, 1), "tP", m.get("t_P_s"),
              "off", r["t_crawler_off_first_s"], "c_rut", round(r["clear_true_ready_mm"] or 0, 1))
