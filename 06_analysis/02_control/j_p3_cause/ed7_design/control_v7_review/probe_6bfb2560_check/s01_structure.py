"""Print the key structure of the first lines of the ed7 probe jsonl (no values of long arrays)."""
import json
import sys

PATH = (r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
        r"\6bfb2560\ed7_probe_a1\ed7_probe.jsonl")


def shape(obj, depth=0, maxdepth=4, prefix=""):
    pad = "  " * depth
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)) and depth < maxdepth:
                n = len(v)
                print(f"{pad}{k}: {type(v).__name__}[{n}]")
                if isinstance(v, list):
                    if v and isinstance(v[0], (dict, list)):
                        shape(v[0], depth + 1, maxdepth)
                    else:
                        print(f"{pad}  sample={str(v[:4])[:120]}")
                else:
                    shape(v, depth + 1, maxdepth)
            else:
                s = json.dumps(v)
                print(f"{pad}{k}: {s[:120]}")
    elif isinstance(obj, list):
        if obj:
            shape(obj[0], depth + 1, maxdepth)


which = int(sys.argv[1]) if len(sys.argv) > 1 else 0
maxdepth = int(sys.argv[2]) if len(sys.argv) > 2 else 3
with open(PATH, encoding="utf-8") as fh:
    for i, line in enumerate(fh):
        if i == which:
            rec = json.loads(line)
            print("bytes", len(line))
            shape(rec, 0, maxdepth)
            break
