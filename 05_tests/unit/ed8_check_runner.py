"""One ``run_v5`` job as a batch worker runs it; writes the line and the T4h names it made.

Helper of ``test_ed8_impl_harness.py`` (the harness needs dynamics-dev; the tests run in
Chrono-dev). The report: the whole line (JSON form), the T4h array names and meta keys, and the
modules imported from another checkout.

Usage:
  python -I -B ed8_check_runner.py <job json> <t4h folder> <out.json>
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
        shapes = {name: list(data[name].shape) for name in data.files if name != "meta_json"}
        return {"arrays": sorted(data.files), "shapes": shapes, "reads": int(len(data["t_s"])),
                "meta_keys": sorted(meta), "controller_tag": meta.get("controller_tag")}


def main() -> None:
    job, t4h_folder, out_path = json.loads(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    import run_v5

    record = run_v5.run_one({**job, "mask": None, "t4h_dir": str(t4h_folder)})
    if "error" in record:
        raise RuntimeError(f"{job}: {record['error']}\n{record.get('tb')}")
    report = {"line": record, "t4h": _t4h_summary(t4h_folder, record.get("t4h_file")),
              "foreign_modules": _modules_outside_checkout()}
    out_path.write_text(json.dumps(report, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
