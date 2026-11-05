"""Check that pad A and pad B runs of the same case have bit-equal settle blocks (read-only)."""
import json
from pathlib import Path

D = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9\rev80")
for f in ("soil_harness.json", "sensor_harness.json", "beta_harness.json", "base_harness.json"):
    runs = json.loads((D / f).read_text(encoding="utf-8"))["runs"]
    seq = list(runs.values()) if isinstance(runs, dict) else runs
    by = {r["id"]: r for r in seq}
    pairs = same = 0
    for rid, r in by.items():
        if "|A|" not in rid:
            continue
        other = by.get(rid.replace("|A|", "|B|"))
        if other is None:
            continue
        pairs += 1
        a, b = r["settle"], other["settle"]
        if a["att_error_deg"] == b["att_error_deg"] and a["gap_error_mm"] == b["gap_error_mm"]:
            same += 1
    print(f"{f}: A/B pairs {pairs}, settle errors bit-equal {same}")
