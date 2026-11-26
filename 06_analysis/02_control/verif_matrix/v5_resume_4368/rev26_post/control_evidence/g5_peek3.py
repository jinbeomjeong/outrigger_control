"""Find the recorded VB / V0 fail reasons of the five G-5 keys in run-2 path 1 u3_judge.json (search all nodes)."""
import json
from pathlib import Path

F = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368")
p1 = json.loads((F / "judge_rev26_74c2784" / "harness_path1" / "u3_judge.json").read_text("utf-8"))
KEYS = {"g6": ["g6r|rigid+S1@FL|top|Fs4", "g6r|rigid+S1@FR|top|Fs4"],
        "g8": ["slope|edge|top|4.0|RL|raised|20.0|proj", "slope|edgeMr|top|4.0|RR|raised|20.0|proj"],
        "h9": ["H9|J1|B|top|roll_pos@k0.6"]}
for study, keys in KEYS.items():
    s = p1["u3"][study]
    g = s["grades"]
    print(study, "grades type", type(g).__name__, "keys", list(g)[:6] if isinstance(g, dict) else len(g))
    for k in keys:
        hits = []

        def walk(o, path):
            if isinstance(o, dict):
                for kk, vv in o.items():
                    if kk == k:
                        hits.append((path + [kk], vv))
                    walk(vv, path + [kk])
            elif isinstance(o, list):
                for i, vv in enumerate(o):
                    if isinstance(vv, dict) and vv.get("key") == k:
                        hits.append((path + [f"[{i}]"], vv))
                    walk(vv, path + [f"[{i}]"])
        walk(s, [])
        for p, v in hits:
            print("  ", k, "/".join(p), json.dumps(v, ensure_ascii=False)[:900])
