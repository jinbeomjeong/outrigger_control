"""Step 3: find fallback / rod-sensor state keys in the five breach records.

Prints every key path containing 'fallback', 'rod_state', 'sensor' or 'substitut' with a short
value, for h10 lines 28 / 172 / 245 and the two grid runs. Read-only.
"""
import json
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control")
RK1 = ROOT / r"06_analysis\03_hydraulic\coupled\v5\resume_k1"
WORDS = ("fallback", "rod_state", "sensor", "substitut", "lower_reading", "rod_fault")


def walk(d, path=""):
    if isinstance(d, dict):
        for k, v in d.items():
            p = f"{path}.{k}" if path else k
            if any(w in k.lower() for w in WORDS):
                s = json.dumps(v)
                print("  ", p, "=", s[:300])
            walk(v, p)
    elif isinstance(d, list):
        for i, v in enumerate(d[:50]):
            walk(v, f"{path}[{i}]")


def main():
    lines = (RK1 / "h10_reuse_rerun.jsonl").read_text(encoding="utf-8").splitlines()
    for ln in (28, 172, 245):
        print("line", ln)
        walk(json.loads(lines[ln - 1]))
    for fn, ri, rj in (("grid_r67_top.json", 13, 3), ("grid_r69_bottom.json", 12, 0)):
        d = json.loads((RK1 / "h9_grid" / fn).read_text(encoding="utf-8"))
        print(fn, ri, rj)
        walk(d["results"][ri]["runs"][rj])
        print("  event:", json.dumps(d["results"][ri]["runs"][rj].get("event"))[:600])


if __name__ == "__main__":
    main()
