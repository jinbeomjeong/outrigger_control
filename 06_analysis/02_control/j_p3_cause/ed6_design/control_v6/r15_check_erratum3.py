"""R15 J2 values (min over legs of event_output.min_F_after_W_kN): V0 stored vs b1off a1a2b3 lines."""
import json
import statistics
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis")
V0 = ROOT / "03_hydraulic/coupled/v5/main.jsonl"
B1OFF = ROOT / "02_control/j_p3_cause/ed6_design/probe_1bd405c8/b1off_check/ed6_probe_a1a2b3.jsonl"


def j2(row):
    ev = row.get("event_output") or {}
    vals = ev.get("min_F_after_W_kN")
    return None if not vals else min(vals.values())


def main():
    v0 = {}
    for text in V0.read_text(encoding="utf-8").splitlines():
        if not text.strip():
            continue
        row = json.loads(text)
        job = row.get("job", {})
        if job.get("setting") == "V0" and job.get("case") == "R15":
            v0[job.get("offset_s")] = j2(row)
    on = {}
    for text in B1OFF.read_text(encoding="utf-8").splitlines():
        if not text.strip():
            continue
        row = json.loads(text)
        job = row.get("job", {})
        if job.get("case") == "R15":
            on.setdefault(job.get("setting"), {})[job.get("offset_s")] = j2(row)
    print("V0", v0)
    for setting, vals in sorted(on.items()):
        phases = sorted(set(v0) & set(vals))
        off = [v0[p] for p in phases]
        new = [vals[p] for p in phases]
        spread = max(off) - min(off)
        effect = statistics.median(new) - statistics.median(off)
        signs = {(b > a) - (b < a) for a, b in zip(off, new)}
        distinct = abs(effect) > spread and len(signs) == 1 and 0 not in signs
        print(setting, vals, "S", round(spread, 3), "E", round(effect, 3), "distinct", distinct,
              "worse", distinct and effect < 0)


if __name__ == "__main__":
    main()
