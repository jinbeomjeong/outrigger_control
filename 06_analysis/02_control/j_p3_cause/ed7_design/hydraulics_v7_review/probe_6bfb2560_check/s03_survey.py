"""Survey of the ed7 probe jsonl: rows per (plant, arm, part), gate mode and record keys present."""
import collections
import json
import sys

PATH = sys.argv[1]
counts = collections.Counter()
modes = collections.defaultdict(collections.Counter)
keys = collections.defaultdict(collections.Counter)
settings = collections.defaultdict(set)
cases = collections.Counter()
with open(PATH, encoding="utf-8") as handle:
    for line in handle:
        row = json.loads(line)
        probe = row.get("ed7_probe") or {}
        plant = probe.get("plant")
        arm = probe.get("arm")
        part = probe.get("part")
        counts[(plant, arm, part)] += 1
        settings[plant].add(row["job"]["setting"])
        hr = row.get("hydraulics_record") or {}
        gate = hr.get("line_fill_gate")
        modes[plant][None if gate is None else gate.get("mode")] += 1
        for key in ("stale_seed_release", "p1_fill_release_log", "lock_log",
                    "p1_retract_seed_log"):
            keys[plant][(key, key in hr)] += 1
        stem = row["t4h_file"][:-4]
        cases[stem[: -len(row["job"]["setting"]) - 1]] += 1
print("rows per (plant, arm, part):")
for item, n in sorted(counts.items(), key=lambda kv: tuple(str(v) for v in kv[0])):
    print("  ", item, n)
print("gate modes per plant:")
for plant, counter in modes.items():
    print("  ", plant, dict(counter))
print("record keys per plant:")
for plant, counter in keys.items():
    print("  ", plant, dict(counter))
print("settings per plant:")
for plant, names in settings.items():
    print("  ", plant, sorted(names))
print("case keys:", len(cases))
for case, n in sorted(cases.items()):
    print("  ", case, n)
