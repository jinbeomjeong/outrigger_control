"""Twin V0 smoke checks (keys and kinds only; no judged value, no pass / fail bool): the
producer premises of the NB-1 reading on each line, the T8'' V0 identity, the A/A pair verdict
only for two lines of the same (row, group), and the effective shape / SHAPE_SEVERITY kinds.

Usage (Chrono-dev ``python.exe -I -B``): python -I -B check_smoke.py <judge checkout> <runner>
Writes ``smoke_check.json`` beside the lines.
"""
import itertools
import json
import sys
from pathlib import Path

JUDGE = Path(sys.argv[1]).resolve()
for _path in (JUDGE / "04_scripts" / "04_hydraulic" / "coupled", JUDGE / "03_src"):
    sys.path.insert(0, str(_path))

import jp3_ed7_judge as ed7  # noqa: E402
import jp3_ed8_judge as ed8  # noqa: E402


def premises(line: dict) -> dict:
    output = line.get("event_output") or {}
    return {"event": (line["job"].get("twin") or {}).get("event"),
            "has_error": "error" in line,
            "controller_tag_is_v0_tag": line.get("controller_tag") == ed8.V0_CONTROLLER_TAG,
            "v0_absent_keys_present": [name for name in ed8.V0_ABSENT_KEYS
                                       if line.get(name) is not None],
            "hydraulic_options_is_null": line.get("hydraulic_options") is None,
            "hydraulics_record_is_null": line.get("hydraulics_record") is None,
            "lock_window_alignment_absent": "lock_window_alignment" not in line,
            "t4h_file_absent": "t4h_file" not in line,
            "has_reapproach_starts_key": "reapproach_starts" in output,
            "event_list_length": len(line.get("events") or []),
            "event_list_capped": len(line.get("events") or []) >= 200}


def main() -> int:
    folder = Path(sys.argv[2])
    lines = [json.loads(text) for text in
             (folder / "v0_smoke.jsonl").read_text(encoding="utf-8").splitlines() if text.strip()]
    order = {event: i for i, event in enumerate(("RE1bF", "FS24", "G4"))}
    lines.sort(key=lambda line: order.get(line["job"]["twin"]["event"], 9))
    report = {"judge_code": str(JUDGE), "lines": len(lines),
              "premises": [premises(line) for line in lines],
              "v0_identity_problems": [ed8.v0_identity_problems(line) for line in lines]}
    metrics = [ed7.metric_of(line, (), ed8.V0_LABEL) for line in lines]
    keys = [(m["row"], m["group"]) for m in metrics]
    report["row_group_shared"] = len(set(keys)) < len(keys)
    pairs = []
    for (i, a), (j, b) in itertools.combinations(enumerate(keys), 2):
        if a != b:
            continue
        entry = {"base": lines[i]["job"]["twin"]["event"],
                 "candidate": lines[j]["job"]["twin"]["event"]}
        try:
            verdict = ed8.aa_pair_verdict(lines[i], lines[j], ())
            entry.update(raised=None, j11_state=verdict["j11_state"],
                         fail_is_bool=isinstance(verdict["fail"], bool))
        except Exception as exc:  # noqa: BLE001 - the kind is the result
            entry.update(raised=type(exc).__name__, message=str(exc)[:300])
        pairs.append(entry)
    report["aa_pairs"] = pairs or "skipped: no two lines of the same (row, group)"
    shapes = [ed8.effective_shape(line["job"]) for line in lines]
    report["effective_shape_source"] = [
        "twin" if "depth_m" in line["job"]["twin"] else "RE1bF default" for line in lines]
    report["shape_severity_vs_default"] = [ed8.shape_severity(shape, ed8.DEFAULT_RE1BF_SHAPE)
                                           for shape in shapes]
    out = folder / "smoke_check.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "written", "out": str(out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
