"""Write one-key id files (first pad-B key of each stored v4 file) for the smoke runs."""

import json
import sys
from pathlib import Path

WORKTREE = Path(sys.argv[1])
OUT = Path(sys.argv[2])
SOURCES = {
    "D": "06_analysis/02_control/s9/rev85/fin_x426_D.json",
    "C": "06_analysis/02_control/s9/rev85/fin_x426_C.json",
    "slope": "06_analysis/02_control/s9/rev85/finB2_harness.json",
    "b5main": "06_analysis/02_control/s9/rev84/fin_b5_main.json",
}


def entry_key(entry: dict) -> str:
    for name in ("id", "key", "case"):
        if entry.get(name) is not None:
            return str(entry[name])
    raise KeyError(sorted(entry))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for label, relative in SOURCES.items():
        payload = json.loads((WORKTREE / relative).read_text(encoding="utf-8"))
        entries = payload.get("records") or payload.get("results") or []
        if label == "slope":
            entries = [e for e in entries if e.get("suite") in (None, "slope")]
        entries = [e for e in entries if not entry_key(e).endswith("|PA")]
        first = entries[0]
        key = entry_key(first)
        field = "case" if label == "b5main" else "id"
        record = {field: key}
        if "suite" in first:
            record["suite"] = first["suite"]
        (OUT / f"ids_{label}.json").write_text(json.dumps({"records": [record]}), encoding="utf-8")
        print(label, key, first.get("suite"))


if __name__ == "__main__":
    main()
