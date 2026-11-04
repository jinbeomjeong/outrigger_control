"""Compare re-run verdict results against the stored ones, field by field and array by array."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

STORED = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\verdict")
COUPLED = Path(r"C:\workspace\outrigger_control\04_scripts\04_hydraulic\coupled")
IGNORED_KEYS = {"wall_s"}


def _differences(new: dict, old: dict) -> list[str]:
    keys = (set(new) | set(old)) - IGNORED_KEYS
    return sorted(key for key in keys if new.get(key) != old.get(key))


def _npz_is_same(new_path: Path, old_path: Path) -> bool:
    with np.load(new_path) as new, np.load(old_path) as old:
        if set(new.files) != set(old.files):
            return False
        return all(new[key].tobytes() == old[key].tobytes() for key in new.files)


def compare_folder(folder: Path) -> dict:
    table = {}
    for path in sorted(folder.glob("*.json")):
        new = json.loads(path.read_text(encoding="utf-8"))
        old = json.loads((STORED / path.name).read_text(encoding="utf-8"))
        table[path.stem] = {
            "harness_sha_same": new.get("harness_commands_sha256")
            == old.get("harness_commands_sha256"),
            "commands_sha_same": new["commands_sha256"] == old["commands_sha256"],
            "commands_sha": new["commands_sha256"][:16],
            "differing_json_keys": _differences(new, old),
            "npz_bits_same": _npz_is_same(path.with_suffix(".npz"),
                                          STORED / f"{path.stem}.npz"),
        }
    return table


def main() -> None:
    sys.path.insert(0, str(COUPLED))
    import aggregate_verdict

    out_path, *folders = sys.argv[1:]
    report = {Path(folder).name: compare_folder(Path(folder)) for folder in folders}
    off_runs = aggregate_verdict._load_runs(Path(folders[-1]))
    report["off_identity_vs_rev85"] = aggregate_verdict.off_identity(off_runs)
    Path(out_path).write_text(json.dumps(report, indent=1), encoding="utf-8")
    for name, table in report.items():
        if name == "off_identity_vs_rev85":
            continue
        for run_id, row in table.items():
            print(run_id, row["commands_sha"], row["harness_sha_same"], row["commands_sha_same"],
                  row["npz_bits_same"], row["differing_json_keys"])
    print("rev85:", [(r["case_id"], r["is_same"]) for r in report["off_identity_vs_rev85"]])


if __name__ == "__main__":
    main()
