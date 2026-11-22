"""Distinct absolute-path roots in the R4 judge outputs (prefix before a repo top folder); counts only."""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\judge_932f1fb")
TOP = re.compile(r"^(?P<root>[A-Za-z]:[\\/].*?)[\\/](03_src|04_scripts|05_tests|06_analysis|07_results|02_params)"
                 r"[\\/]")
SCR = re.compile(r"^(?P<root>[A-Za-z]:[\\/].*?[\\/]scratchpad)[\\/]", re.I)
cnt = Counter()


def walk(o, f):
    if isinstance(o, dict):
        for v in o.values():
            walk(v, f)
    elif isinstance(o, list):
        for v in o:
            walk(v, f)
    elif isinstance(o, str) and re.match(r"^[A-Za-z]:[\\/]", o):
        m = TOP.match(o) or SCR.match(o)
        cnt[(f.split("/")[0], m.group("root") if m else "<other abs>")] += 1


for d in ("harness_path1", "harness_path1_retry1", "harness_path2"):
    for f in sorted((ROOT / d).glob("*.json")):
        walk(json.load(open(f, encoding="utf-8")), f"{d}/{f.name}")
for (d, r), n in sorted(cnt.items()):
    print(d, r, n)
