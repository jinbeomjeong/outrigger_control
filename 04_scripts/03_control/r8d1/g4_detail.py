import json
d = json.load(open("td2_G_G2.json"))
for r in d["runs"]:
    sr = r.get("settle_result", {})
    print(r["id"][:44], r.get("contact"), "min_after", sr.get("min_true_after_sink_kN"), "t", sr.get("t_min_after_sink_s"),
          "below", sr.get("t_below_Fmin_true_after_sink_s"), "guard", r.get("guard_active_s"), "fails", r.get("fails"))
