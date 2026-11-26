"""Print the H-3 G-5 rows of the rev26 run-2 outputs (path 1 u3_judge.json, path 2 u3.json) and where the five
keys appear in path 1 u3_judge.json (paths and small leaf values only)."""
import json
import sys
from pathlib import Path

F = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368")
RUN = F / sys.argv[1]
p1 = json.loads((RUN / "harness_path1" / "u3_judge.json").read_text("utf-8"))
p2 = json.loads((RUN / "harness_path2" / "u3.json").read_text("utf-8"))
print("P1 top keys:", list(p1)[:40])
print("P1 R4 keys:", list(p1.get("R4", {})))
g5 = p1["R4"]["G-5_list_RD7"]
print("P1 G-5_list_RD7:", json.dumps(g5, ensure_ascii=False)[:3000])
print("P1 G-6_list_RD7:", json.dumps(p1["R4"].get("G-6_list_RD7"), ensure_ascii=False)[:1500])
u3 = p1.get("u3", {})
for s, v in u3.items():
    print("P1 study", s, "status", v.get("status"), "keys", list(v)[:30])
    print("   phrase", json.dumps(v.get("phrase"), ensure_ascii=False)[:400])
    print("   gates", json.dumps(v.get("gates"), ensure_ascii=False)[:600])
print("P2 U-3 keys:", list(p2.get("U-3", {})))
print("P2 U-3 status", p2["U-3"].get("status"), "stop_codes", p2["U-3"].get("stop_codes"))
print("P2 G-5_list:", json.dumps(p2["U-3"].get("G-5_list"), ensure_ascii=False)[:3000])
