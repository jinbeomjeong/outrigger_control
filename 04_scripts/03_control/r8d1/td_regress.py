import json
old = json.load(open(r"C:\workspace\outrigger_control\06_analysis\02_control\r8_10hz\r8_S_c10_R12A_c10_R12AR.json"))["runs"]
new = json.load(open("td_S_main7.json"))["runs"]
o = {r["id"].replace("|c10_R12AR|", "|X|"): r for r in old if "|c10_R12AR|" in r["id"]}
n = {r["id"].replace("|c10_R12AR_tv0|", "|X|"): r for r in new if "|c10_R12AR_tv0|" in r["id"]}
print(len(o), len(n), len(set(o) & set(n)))
keys = ("min_true_cyl_force_kN", "t_ready_s", "t_touch_s", "ss_true_att_deg_maxabs", "max_pressure_bar", "min_true_cyl_force_substep_kN")
mx = 0; diff = []
for k in sorted(set(o) & set(n)):
    for kk in keys:
        a, b = o[k].get(kk), n[k].get(kk)
        if a != b:
            diff.append((k, kk, a, b))
    if "x" in o[k]:
        if json.dumps(o[k]["x"], sort_keys=True) != json.dumps(n[k]["x"], sort_keys=True):
            diff.append((k, "x", "", ""))
print("differences:", len(diff)); print(diff[:10])
