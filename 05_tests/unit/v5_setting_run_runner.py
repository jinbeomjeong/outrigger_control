"""One ``run_v5`` job with its T4h record; writes the command hash and the record keys.

Helper of ``test_v5_setting_records.py``: the harness needs dynamics-dev (numba), the tests run
in Chrono-dev. The job runs through ``run_v5.run_one`` as a batch worker does (T4h record into
the given folder for the VB / LS settings).

Usage:
  python -I -B v5_setting_run_runner.py <job json> <t4h folder> <out.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "03_src"
COUPLED_DIR = PROJECT_ROOT / "04_scripts" / "04_hydraulic" / "coupled"
MAIN_TREE_ROOT = Path(r"C:\workspace\outrigger_control")
"""``r8d1_td.py`` inserts a folder of this tree whichever checkout it runs in."""
T4H_META_KEYS = ("pressure_offset_allowance_N", "pressure_offset_allowance_from_s",
                 "controller_tag", "extend_bound_check", "head_only_declared")


class _ThisCheckoutSysPath(list):
    """``sys.path`` whose ``insert`` maps a main-tree folder onto this checkout (git worktree)."""

    def insert(self, index, folder) -> None:
        path = Path(folder)
        if path.is_relative_to(MAIN_TREE_ROOT) and not path.is_relative_to(PROJECT_ROOT):
            folder = str(PROJECT_ROOT / path.relative_to(MAIN_TREE_ROOT))
        super().insert(index, folder)


sys.path = _ThisCheckoutSysPath(sys.path)
for _path in (COUPLED_DIR, SOURCE_DIR):
    sys.path.insert(0, str(_path))


def _modules_outside_project() -> list[str]:
    """Project modules imported from the main tree in a worktree run (empty in the main tree)."""
    foreign = []
    for module in list(sys.modules.values()):
        file_name = getattr(module, "__file__", None)
        if file_name is None:
            continue
        path = Path(file_name).resolve()
        if path.is_relative_to(MAIN_TREE_ROOT) and not path.is_relative_to(PROJECT_ROOT):
            foreign.append(str(path))
    return foreign


def _t4h_meta(folder: Path, file_name: str | None) -> dict | None:
    if file_name is None:
        return None
    import numpy as np

    with np.load(folder / file_name, allow_pickle=False) as data:
        meta = json.loads(str(data["meta_json"]))
        has_rod_reading = bool(np.isfinite(data["rod_pressure_Pa"]).any())
    return {"extend_start_rule": meta["two_pressure_settings"].get("extend_start_rule"),
            "has_rod_reading": has_rod_reading,
            **{key: meta.get(key) for key in T4H_META_KEYS}}


def main() -> None:
    job, t4h_folder, out_path = json.loads(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    import run_v5

    record = run_v5.run_one({**job, "mask": None, "t4h_dir": str(t4h_folder)})
    if "error" in record:
        raise RuntimeError(f"{job}: {record['error']}\n{record.get('tb')}")
    hydraulics = record.get("hydraulics_record") or {}
    report = {"hash": record["commands_sha256"],
              "controller_tag": record.get("controller_tag"),
              "hydraulic_options": record.get("hydraulic_options"),
              "extend_bound_check": hydraulics.get("extend_bound_check"),
              "head_only_declared": record.get("head_only_declared"),
              "t4h": _t4h_meta(t4h_folder, record.get("t4h_file")),
              "t4h_file": record.get("t4h_file"),
              "u9": record["values"].get("U9"),
              "supply_L_min": record["values"].get("supply_L_min"),
              "foreign_modules": _modules_outside_project()}
    out_path.write_text(json.dumps(report), encoding="utf-8")


if __name__ == "__main__":
    main()
