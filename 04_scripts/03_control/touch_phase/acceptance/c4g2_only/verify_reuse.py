"""Check the reuse rule of the C4G2-only bundle after a noise step: every rerun inactive sample row must equal the C4G2 + K1 row, and no row may carry a retrigger deferral or a retrigger_samples other than 1.
Compares r79, events, sensors, zero_calibration, base without wall_s. Exit 1 on any mismatch (the runner stops; criteria_c4g2_only.md says what then). Usage: python -I -B verify_reuse.py r79_L1L2|r79_L3"""
import json
import sys
from pathlib import Path

ACC = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance")
OUT = ACC / "c4g2_only"
name = sys.argv[1]


def partial(path):
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        rows[rec["key"]] = rec
    return rows


def nm(e):
    return str(e.get("name")) if isinstance(e, dict) else str(e[-1]) if isinstance(e, (list, tuple)) else str(e)


def strip(base):
    return {k: v for k, v in base.items() if k != "wall_s"}


manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))["files"][name]
both = partial(ACC / f"noise/{name}.json.partial.jsonl")
new = partial(OUT / f"noise/{name}.json.partial.jsonl")
final = json.loads((OUT / f"noise/{name}.json").read_text(encoding="utf-8"))
bad = []
sample = manifest["sample_near"] + manifest["sample_random"]
for k in sample:
    a, b = new.get(k), both[k]
    if a is None or "reuse" in a:
        bad.append((k, "not rerun"))
        continue
    diff = [f for f in ("r79", "events", "sensors", "zero_calibration") if a.get(f) != b.get(f)]
    if strip(a["base"]) != strip(b["base"]):
        diff.append("base")
    if diff:
        bad.append((k, diff))
ret = [k for k, r in new.items() if any(nm(e).endswith(":retrigger") for e in r.get("events", []))]
errors = [k for k, r in new.items() if "error" in r]
out = {"file": name, "rows": len(new), "expected_rows": manifest["rows"], "sample": len(sample), "sample_mismatch": bad, "retrigger_rows": ret, "errors": errors, "final_n": final["meta"]["n_jobs"], "seeded": sum("reuse" in r for r in new.values())}
(OUT / f"verify_{name}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out))
sys.exit(1 if bad or ret or errors or len(new) != manifest["rows"] else 0)
