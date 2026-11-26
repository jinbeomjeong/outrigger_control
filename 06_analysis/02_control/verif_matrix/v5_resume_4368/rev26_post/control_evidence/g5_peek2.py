"""Reasons recorded for the five G-5 keys in the run-2 outputs (path 2 vb_unique_fail, path 1 grades/classes)."""
import json
from pathlib import Path

F = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368")
KEYS = ["g6r|rigid+S1@FL|top|Fs4", "g6r|rigid+S1@FR|top|Fs4", "slope|edge|top|4.0|RL|raised|20.0|proj",
        "slope|edgeMr|top|4.0|RR|raised|20.0|proj", "H9|J1|B|top|roll_pos@k0.6"]
for run in ("judge_rev26_74c2784", "judge_932f1fb"):
    p2 = json.loads((F / run / "harness_path2" / "u3.json").read_text("utf-8"))
    vu = p2["U-3"]["vb_unique_fail"]
    print(run, "P2 vb_unique_fail type", type(vu).__name__, "len", len(vu))
    print(json.dumps(vu, ensure_ascii=False)[:2500])
    print(run, "P2 sentence_VB", json.dumps(p2["U-3"].get("sentence_VB"), ensure_ascii=False)[:600])
p1 = json.loads((F / "judge_rev26_74c2784" / "harness_path1" / "u3_judge.json").read_text("utf-8"))
for study in ("h9", "g6", "g8"):
    s = p1["u3"][study]
    print(study, "vb_counts", json.dumps(s.get("vb_counts"), ensure_ascii=False))
    g = s.get("grades")
    if isinstance(g, dict):
        for k in KEYS:
            if k in g:
                print("  grades", k, json.dumps(g[k], ensure_ascii=False)[:800])
    c = s.get("classes")
    print("  classes", json.dumps(c, ensure_ascii=False)[:700])
    t = s.get("transition_V0_VB")
    print("  transition", json.dumps(t, ensure_ascii=False)[:400])
