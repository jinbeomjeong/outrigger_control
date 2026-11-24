"""Census of rod-pressure fallbacks (with reason) and end states in the confirmation (가) lines
and in the probe 1bd405c8 lines; read-only, prints a JSON summary."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

CAUSE = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause")
CONFIRM = CAUSE / "j9_runs/79495405/confirm_a1/confirm_a.jsonl"
PROBE = CAUSE / "j9_runs/1bd405c8/ed6_probe_a1/ed6_probe.jsonl"
V0 = CAUSE.parents[1] / "03_hydraulic/coupled/v5/main.jsonl"
J9MAIN5 = CAUSE / "j9_runs/606f8713/j9main_a1/j9_main.jsonl"
REASON = re.compile(r"INFO_ROD_PRESSURE_FAULT_REASON:(\w+):(\w+)")


def row_tag(job):
    twin = job.get("twin") or {}
    phase = (f"{twin.get('level')}-{twin.get('leg')}-Fs{twin.get('fs_kN')}-o{job.get('offset_s')}"
             if twin else f"o{job.get('offset_s')}/e{job.get('eps')}")
    return f"{job.get('case')} {phase}"


def scan(path, label, keep=None):
    out = defaultdict(list)
    counts = Counter()
    for text in path.read_text(encoding="utf-8").splitlines():
        if not text.strip():
            continue
        row = json.loads(text)
        job = row.get("job", {})
        setting = job.get("setting")
        if keep and not keep(setting):
            continue
        counts[setting] += 1
        names = row.get("event_names") or {}
        events = row.get("events") or []
        reasons = [m.groups() for e in events for m in [REASON.search(str(e[1]))] if m]
        if "WARN_ROD_PRESSURE_FALLBACK" in json.dumps(events) or reasons:
            out[setting].append({"row": row_tag(job), "reasons": reasons,
                                 "final": row.get("final_phase"),
                                 "t": [round(e[0], 2) for e in events
                                       if "ROD_PRESSURE" in str(e[1])]})
    return {"label": label, "lines": dict(counts),
            "fallback_lines": {k: v for k, v in out.items()}}


def main():
    result = [scan(CONFIRM, "confirm_a"),
              scan(V0, "V0 main", keep=lambda s: s == "V0"),
              scan(J9MAIN5, "j9_main ed5"),
              scan(PROBE, "probe 1bd405c8")]
    for r in result:
        print(json.dumps({"label": r["label"], "lines": r["lines"],
                          "fallback_counts": {k: len(v) for k, v in r["fallback_lines"].items()}},
                         ensure_ascii=False))
        for setting, items in sorted(r["fallback_lines"].items()):
            for item in items:
                print("   ", setting, json.dumps(item, ensure_ascii=False))


if __name__ == "__main__":
    main()
