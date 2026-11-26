"""a03: which fixed-table (P7-9) units / D lines carried the stiffness WARN, and how they
were judged (sens exemption vs D V0 comparison). Read only."""
import json

P = (r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design"
     r"\fixed_table_b46bdf8f\fixed_table_a2.json")
d = json.load(open(P, encoding="utf-8"))
for part in ("sens40_units", "d24_lines"):
    items = d[part]
    if isinstance(items, dict):
        items = list(items.values())
    print("==", part, len(items))
    for u in items:
        txt = json.dumps(u, ensure_ascii=False)
        keep = {k: u[k] for k in u if k in ("id", "setting", "row", "phase", "key", "t4h_file",
                                             "verdict", "failed_items", "record_items",
                                             "v0_verdict", "v0_relative", "plant")}
        flag = "STIFF" if "STIFFNESS" in txt else ""
        print(flag, json.dumps(keep, ensure_ascii=False)[:400])
print("== exempt", json.dumps(d["j7_stiffness_exempt"], ensure_ascii=False)[:2000])
print("== d24 keys", list((d["d24_lines"][0] if isinstance(d["d24_lines"], list)
                            else list(d["d24_lines"].values())[0]).keys()))
