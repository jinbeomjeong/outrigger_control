"""One ``run_v5`` job as a batch worker runs it; writes what the edition 7 tests compare.

Helper of ``test_ed7_harness.py`` (the harness needs dynamics-dev; the tests run in Chrono-dev).
Report keys: the command hash, the tag, the line keys of editions 6 and 7, the hydraulics record
keys, the T4h array names and meta keys, and the modules imported from another checkout.

Usage:
  python -I -B ed7_check_runner.py <job json> <t4h folder> <out.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = PROJECT_ROOT / "04_scripts" / "04_hydraulic" / "coupled"
MAIN_CHECKOUT = Path(r"C:\workspace\outrigger_control")
for _path in (COUPLED_DIR, PROJECT_ROOT / "03_src"):
    sys.path.insert(0, str(_path))


def _modules_outside_checkout() -> list[str]:
    foreign = []
    for module in list(sys.modules.values()):
        file_name = getattr(module, "__file__", None)
        if file_name is None:
            continue
        path = Path(file_name).resolve()
        if path.is_relative_to(MAIN_CHECKOUT) and not path.is_relative_to(PROJECT_ROOT):
            foreign.append(str(path))
    return foreign


def _t4h_summary(folder: Path, file_name: str | None) -> dict:
    if file_name is None:
        return {"arrays": None}
    import numpy as np

    with np.load(folder / file_name, allow_pickle=False) as data:
        meta = json.loads(str(data["meta_json"]))
        return {"arrays": sorted(data.files), "reads": int(len(data["t_s"])),
                "meta_keys": sorted(meta)}


def main() -> None:
    job, t4h_folder, out_path = json.loads(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    import run_v5

    record = run_v5.run_one({**job, "mask": None, "t4h_dir": str(t4h_folder)})
    if "error" in record:
        raise RuntimeError(f"{job}: {record['error']}\n{record.get('tb')}")
    hydraulics_record = record.get("hydraulics_record") or {}
    report = {"hash": record["commands_sha256"], "final_phase": record["final_phase"],
              "controller_tag": record.get("controller_tag"),
              "hydraulic_options": record.get("hydraulic_options"),
              "line_keys": sorted(record),
              "lsb_components": record.get("lsb_components"),
              "lsb_record": record.get("lsb_record"),
              "probe_d6_settings": record.get("probe_d6_settings"),
              "probe_d6_record": record.get("probe_d6_record"),
              "hydraulics_record_keys": sorted(hydraulics_record),
              "stale_seed_release": hydraulics_record.get("stale_seed_release"),
              "event_names": record.get("event_names"), "wall_s": record["wall_s"],
              "t4h": _t4h_summary(t4h_folder, record.get("t4h_file")),
              "foreign_modules": _modules_outside_checkout()}
    out_path.write_text(json.dumps(report, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
