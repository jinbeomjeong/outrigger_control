"""One ``run_v5`` job as a batch worker runs it; writes what the edition 6 tests compare.

Helper of ``test_ed6_harness.py``: the harness needs dynamics-dev (numba; the stored command
hashes are dynamics-dev hashes), the tests run in Chrono-dev. Report keys: the command hash,
the tag, the edition 6 line keys, the T4h array names and ``lsb_read_found`` count, and the
modules imported from another checkout.

Usage:
  python -I -B ed6_check_runner.py <job json> <t4h folder> <out.json> [<extra settings json>]
The optional fourth argument adds test-only settings to ``run_v5`` in this process
(``{"name": [flow on, plant options]}``; P6-6 runs the B3-only arm this way).
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
        found = data["lsb_read_found"] if "lsb_read_found" in data.files else None
        meta = json.loads(str(data["meta_json"]))
        return {"arrays": sorted(data.files), "reads": int(len(data["t_s"])),
                "lsb_read_found": None if found is None else int(found.sum()),
                "meta_controller_tag": meta.get("controller_tag"),
                "meta_lsb_components": meta.get("lsb_components")}


def main() -> None:
    job, t4h_folder, out_path = json.loads(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    import run_v5

    if len(sys.argv) > 4:
        extra = {name: (bool(flow), plant) for name, (flow, plant)
                 in json.loads(sys.argv[4]).items()}
        run_v5.ALL_SETTINGS.update(extra)
        run_v5.T4H_SETTINGS = (*run_v5.T4H_SETTINGS, *extra)

    record = run_v5.run_one({**job, "mask": None, "t4h_dir": str(t4h_folder)})
    if "error" in record:
        raise RuntimeError(f"{job}: {record['error']}\n{record.get('tb')}")
    report = {"hash": record["commands_sha256"], "final_phase": record["final_phase"],
              "controller_tag": record.get("controller_tag"),
              "hydraulic_options": record.get("hydraulic_options"),
              "has_lsb_components": "lsb_components" in record,
              "lsb_components": record.get("lsb_components"),
              "lsb_record": record.get("lsb_record"),
              "event_names": record.get("event_names"), "wall_s": record["wall_s"],
              "t4h": _t4h_summary(t4h_folder, record.get("t4h_file")),
              "foreign_modules": _modules_outside_checkout()}
    out_path.write_text(json.dumps(report, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
