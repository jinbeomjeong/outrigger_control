"""Sidecar identity table (rev14 R14-6 1): every ``*.identity.json`` under a folder, every start /
end record's head, is_clean and affinity, compared with the expected commit. Read-only.

Usage: python -I -B sidecars.py <folder> <expected head> <out_json>
"""

import json
import sys
from pathlib import Path


def records_of(doc: dict, moment: str) -> list[dict]:
    value = doc.get(moment)
    if isinstance(value, dict):
        return [value]
    return list(value or [])


def main() -> None:
    folder, expected, out_path = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    rows, problems = [], []
    for path in sorted(folder.rglob("*.identity.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        row = {"file": str(path.relative_to(folder))}
        for moment in ("start", "end"):
            records = records_of(doc, moment)
            heads = [(r.get("git") or {}).get("head") for r in records]
            clean = [(r.get("git") or {}).get("is_clean") for r in records]
            masks = sorted({str(r.get("affinity_mask")) for r in records})
            seals = [all((s or {}).get("ok") for s in (r.get("rules_seals") or {}).values())
                     for r in records]
            row[moment] = {"n": len(records), "heads_equal_expected": sum(h == expected for h in heads),
                           "is_clean_true": sum(c is True for c in clean), "affinity": masks,
                           "seals_ok": sum(seals), "times": [r.get("time") for r in records]}
            if not records:
                problems.append(f"{row['file']}: no {moment} record")
            if any(h != expected for h in heads):
                problems.append(f"{row['file']} {moment}: head not {expected[:7]}")
            if any(c is not True for c in clean):
                problems.append(f"{row['file']} {moment}: not clean")
        if row["start"]["n"] != row["end"]["n"]:
            problems.append(f"{row['file']}: start {row['start']['n']} != end {row['end']['n']}")
        rows.append(row)
    report = {"expected_head": expected, "files": len(rows),
              "records_start": sum(r["start"]["n"] for r in rows),
              "records_end": sum(r["end"]["n"] for r in rows), "problems": problems, "rows": rows,
              "exit_code": 1 if problems else 0}
    out_path.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("files", "records_start", "records_end", "exit_code")}
                     | {"problems": len(problems)}))
    sys.exit(report["exit_code"])


if __name__ == "__main__":
    main()
