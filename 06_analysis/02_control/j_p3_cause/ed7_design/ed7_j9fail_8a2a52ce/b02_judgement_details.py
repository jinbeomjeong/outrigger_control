"""b02: detail fields for the edition 7 judgement draft (t8 tags, l1ref identity sources,
rev7 condition summaries, main_checks result lines, P5-1 record status). Read only."""
import json
import os
import re

R = r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\8a2a52ce"
J = R + r"\judge_60ebb4a4"
t8 = json.load(open(J + r"\t8_a1\t8.json", encoding="utf-8"))
print("t8 tags", json.dumps(t8["controller_tags"]), "expected", json.dumps(t8["expected_tags"]))
l1 = json.load(open(J + r"\l1ref_a1\l1ref.json", encoding="utf-8"))
for stem, v in l1["runs"].items():
    s = {k: (v[k] if not isinstance(v[k], (dict, list)) else (list(v[k].keys())[:12] if isinstance(v[k], dict) else len(v[k]))) for k in v}
    print("l1ref", stem, json.dumps(s, ensure_ascii=False)[:600])
    src = v.get("identity_sources") or {}
    print("   identity_sources fields", {f: {o: (x.get("count") if isinstance(x, dict) else x) for o, x in (d or {}).items()} if isinstance(d, dict) else d for f, d in list(src.items())[:8]})
for name in ("cases_a1\\cases.json", "confirm_a1\\confirm.json", "j9main_a1\\j9main.json", "sens_a1\\sens.json"):
    d = json.load(open(os.path.join(J, name), encoding="utf-8"))
    print("rev7", name, json.dumps(d["rev7_condition"]["summary"]))
    rec = d.get("records", {}).get("totals")
    print("   records", json.dumps(rec))
    if "J-P3_record_settings" in d:
        print("   record settings rev7_record_only runs_with_breach",
              d["J-P3_record_settings"]["rev7_record_only"]["runs_with_breach"],
              "runs_judged", d["J-P3_record_settings"]["rev7_record_only"]["runs_judged"])
mc = os.path.join(R, "main_checks")
for f in sorted(os.listdir(mc)):
    if f.endswith(".md"):
        txt = open(os.path.join(mc, f), encoding="utf-8", errors="replace").read()
        m = re.findall(r"(status[^\n]{0,80}|exit[^\n]{0,60}|불일치[^\n]{0,40}|mismatch[^\n]{0,40})", txt)
        print("mc", f, m[:3])
p51 = r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\p51_record_8a2a52ce\compare\p51_record_compare.json"
d = json.load(open(p51, encoding="utf-8"))
print("p51", {k: d[k] for k in d if not isinstance(d[k], (list, dict))})
for f in ("probe.pause", "confirm.pause", "sens.pause"):
    print(f, open(os.path.join(mc, "chain_log", f), encoding="utf-8").read()[:350])
