"""Shapes, NaN counts and meta keys of every A-type record under the smoke folders."""

import json
import sys
from pathlib import Path

import numpy as np

for folder in sorted(Path(sys.argv[1]).glob("smoke_imua*/*_imua")):
    for path in sorted(folder.glob("*.npz")):
        with np.load(path, allow_pickle=False) as data:
            meta = json.loads(str(data["meta_json"]))
            shapes = {k: list(data[k].shape) for k in data.files if k != "meta_json"}
            nan_true = int(np.isnan(data["attitude_true_rad"]).any(axis=1).sum())
            nan_incl = int(np.isnan(data["attitude_true_at_inclinometer_rad"]).any(axis=1).sum())
            nan_force = int(np.isnan(data["true_force_min_N"]).any(axis=1).sum())
            phases = sorted(set(data["phase"].tolist()))
            error_deg = np.degrees(np.nanmax(np.abs(
                data["inclinometer_rad"] - data["attitude_true_at_inclinometer_rad"])))
        print(folder.name, path.name, "t_s", shapes["t_s"], "incl", shapes["inclinometer_rad"],
              "nan_true", nan_true, "nan_incl", nan_incl, "nan_force", nan_force,
              "phases", phases, "events", len(meta["events"]), "tag", meta["controller_tag"],
              "plant_rows", meta["has_plant_rows"], "max|incl-true| deg", round(float(error_deg), 4))
