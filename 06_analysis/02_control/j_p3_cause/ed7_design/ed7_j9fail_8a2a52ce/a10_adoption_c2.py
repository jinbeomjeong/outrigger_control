"""a10: failed keys per (arm, plant) group, incl. the c2 control arm (no D6 witness, no (i-b)
retract position target), from the stored adoption report adoption_b46bdf8f.json (computed
before the seal by the b46bdf8f adoption tool; J7 ed7_new reading; sens plants stiffness
exempt applied here as in FIXED_READING). Read only. Output a10_adoption_arms.json."""
import json
import os

OUT = os.path.dirname(os.path.abspath(__file__))
P = (r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\6bfb2560"
     r"\ed7_probe_a1\adoption_b46bdf8f.json")
EXEMPT = "WARN_PROBE_STIFFNESS_OUT_OF_RANGE"
SENS = {"Mslow", "Mfast", "Mc005", "Mc04"}
VBM5 = {"M", "Mslow", "Mfast", "Mc005", "Mc04"}
d = json.load(open(P, encoding="utf-8"))
groups = d["groups"]
print("group keys", list(groups.keys()))
groups = {k.replace(" main", "").split(" ")[1] + "|" + k.split(" ")[0]: v for k, v in groups.items()}
res = {}
for gname, g in groups.items():
    # group name form "<arm>|<plant>" or nested
    if isinstance(g, dict) and "fail_items" in g:
        arm, plant = (gname.split("|") + [None])[:2]
        items = g["fail_items"]["ed7_new"]
        by = {}
        for it in items:
            by.setdefault(it["key"], []).append(it)
        failed = []
        for key, its in by.items():
            if plant in SENS and all(i["item"] != "J7" or i["detail"] == EXEMPT for i in its):
                its = [i for i in its if i["item"] != "J7"]
            if its:
                failed.append([key, [f'{i["item"]}: {i["detail"]}' for i in its]])
        for key in g.get("r15_failed_keys", []):
            failed.append([key, ["R15 worsening"]])
        res[gname] = failed
    elif isinstance(g, dict):
        for plant, gg in g.items():
            if isinstance(gg, dict) and "fail_items" in gg:
                items = gg["fail_items"]["ed7_new"]
                by = {}
                for it in items:
                    by.setdefault(it["key"], []).append(it)
                failed = []
                for key, its in by.items():
                    if plant in SENS and all(i["item"] != "J7" or i["detail"] == EXEMPT for i in its):
                        its = [i for i in its if i["item"] != "J7"]
                    if its:
                        failed.append([key, [f'{i["item"]}: {i["detail"]}' for i in its]])
                for key in gg.get("r15_failed_keys", []):
                    failed.append([key, ["R15 worsening"]])
                res[f"{gname}|{plant}"] = failed
summary = {}
for name, failed in sorted(res.items()):
    arm = name.split("|")[0]
    plant = name.split("|")[1]
    if plant in VBM5:
        summary.setdefault(arm, []).extend([[plant] + f for f in failed])
for arm, lst in summary.items():
    print(arm, len(lst), json.dumps(lst, ensure_ascii=False)[:900])
json.dump({"by_group": res, "vbm5_failed_units_by_arm": summary},
          open(os.path.join(OUT, "a10_adoption_arms.json"), "w", encoding="utf-8"), indent=1,
          ensure_ascii=False)
