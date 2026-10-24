import json
from pathlib import Path

PROJ = Path(__file__).resolve().parents[3]
d = json.loads((PROJ / "06_analysis" / "02_control" / "r8_10hz" / "d1" / "c2_norm.json")
               .read_text(encoding="utf-8"))
for s in (1.0, 1.2, 1.3, 1.5):
    for m in ("rigid", "sup_upper", "sup_lower"):
        sub = [x for x in d if x[1] == s and ("_" + m) in x[0]]
        print(s, m, len(sub), round(max(x[2]["tv0.1_r1.2"]["Ms"] for x in sub), 3),
              round(max(x[2]["tv0.1_r1.2"]["G"] for x in sub), 3),
              round(max(x[2]["tv0.15_r1.2"]["Ms"] for x in sub), 3))
