"""Read run metas of the stored acceptance bundles."""
import json
from pathlib import Path

MAIN = Path(r"C:\workspace\outrigger_control")
for rel in ("06_analysis/02_control/s9/rev85/finB2_r67_main.json", "06_analysis/02_control/s9/rev85/finB2_r67_top.json", "06_analysis/02_control/s9/rev85/finB2_A.json",
            "06_analysis/02_control/s8/rev79/fin_r79_merged.json", "06_analysis/02_control/s8/rev79/fin_r79_L3L4_final.json",
            "06_analysis/02_control/s8/rev79/fin_r79_merged_judgement.json", "06_analysis/02_control/s8/rev79/fin_r79_L3L4_final_judgement.json"):
    p = MAIN / rel
    d = json.loads(p.read_text(encoding="utf-8"))
    print("==", rel, list(d.keys())[:10])
    m = d.get("meta") or {}
    print("  meta", json.dumps({k: m[k] for k in m if k not in ("row_columns", "controller_settings", "settings")}, ensure_ascii=False)[:800])
    if "results" in d:
        r = d["results"]
        print("  n results", len(r), "keys", list(r[0].keys())[:20] if isinstance(r, list) else None)
        if isinstance(r, list):
            print("  sample key", r[0].get("key"), "n runs", len(r[0].get("runs", [])), "total", sum(len(x.get("runs", [])) for x in r))
            print("  sum wall", round(sum(x.get("wall_s", 0) for x in r), 0))
            if r[0].get("runs"):
                print("  run keys", list(r[0]["runs"][0].keys())[:30])
for p in sorted((MAIN / "06_analysis/02_control/s8").rglob("r69_g5*")):
    print(p.relative_to(MAIN), p.stat().st_size)
d = json.loads((MAIN / "06_analysis/02_control/s8/rev79/fin_r79_merged_judgement.json").read_text(encoding="utf-8"))
print(json.dumps({k: (v if not isinstance(v, (list, dict)) else str(type(v)) + str(len(v))) for k, v in d.items()})[:600])
for k, v in d.items():
    if isinstance(v, dict):
        print(k, list(v.keys())[:30])
