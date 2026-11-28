"""Check an A-type Chrono case folder: tag, imu_sensor meta, sensor setup and the attitude record.

Usage: python check_imua.py <worktree> <case dir> <expected tag> [--out report.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree")
    ap.add_argument("case")
    ap.add_argument("tag")
    ap.add_argument("--out")
    a = ap.parse_args()
    wt = Path(a.worktree)
    sys.path.insert(0, str(wt / "04_scripts" / "04_hydraulic" / "coupled"))
    sys.path.insert(0, str(wt / "03_src"))
    sys.path.insert(0, str(wt / "04_scripts" / "02_chrono"))
    import imu_a_harness
    import imua_chrono

    d = Path(a.case)
    r = json.loads((d / "result.json").read_text(encoding="utf-8"))
    want = imua_chrono.imu_sensor_block(imu_a_harness.ImuSetting("inclinometer", "v5_A"))
    cm = r["controller_meta"]
    tag = r.get("controller_tag") or (r.get("v5_hydraulics") or {}).get("controller_tag")
    c2s = r.get("c2_setup") or {}
    def find_setup(x):
        if isinstance(x, dict):
            if "attitude_sensor" in x and "imu" in x and "legs" in x:
                return {"config": x}
            for v in x.values():
                got = find_setup(v)
                if got:
                    return got
        return None

    sens = find_setup(json.loads((d / "record" / "meta.json").read_text(encoding="utf-8"))) or {}
    out = {"case": str(d), "controller_tag": tag, "tag_ok": tag == a.tag,
           "v5_hydraulics_tag": (r.get("v5_hydraulics") or {}).get("controller_tag"),
           "expect_name": (c2s.get("expect_controller") or {}).get("name"),
           "expect_ok": (c2s.get("expect_controller") or {}).get("ok"),
           "imu_sensor_equal_to_meta": cm.get("imu_sensor") == want,
           "c2_setup_imu_sensor_equal": c2s.get("imu_sensor") == want if "imu_sensor" in c2s else None,
           "controller_imu_outputs": cm.get("imu_outputs"),
           "record_file": r.get("imua_record_file")}
    out["sensor_setup_keys"] = sorted((sens.get("config") or {}).keys())
    out["sensor_attitude"] = (sens.get("config") or {}).get("attitude_sensor")
    out["sensor_imu"] = {k: v for k, v in ((sens.get("config") or {}).get("imu") or {}).items()
                         if k in ("accel_noise_density_m_s2_rtHz", "gyro_noise_density_rad_s_rtHz", "accel_bias_m_s2",
                                  "gyro_bias_rad_s", "grade", "sample_period_s")}
    with np.load(d / r["imua_record_file"], allow_pickle=False) as z:
        meta = json.loads(str(z["meta_json"]))
        arr = {k: z[k] for k in z.files if k != "meta_json"}
    out["record_meta"] = {k: meta[k] for k in ("form", "controller_tag", "F_min_N", "truth_rows")}
    out["record_meta_imu_sensor_equal"] = meta["imu_sensor"] == want
    out["record_events"] = len(meta["events"])
    out["shapes"] = {k: list(v.shape) for k, v in arr.items()}
    out["nan_counts"] = {k: int(np.isnan(v).sum()) for k, v in arr.items() if v.dtype.kind == "f"}
    err = arr["inclinometer_rad"] - arr["attitude_true_at_inclinometer_rad"]
    out["inclinometer_minus_true_deg"] = {
        "max_abs_roll": float(np.nanmax(np.abs(np.degrees(err[:, 0])))),
        "max_abs_pitch": float(np.nanmax(np.abs(np.degrees(err[:, 1])))),
        "rms_roll": float(np.sqrt(np.nanmean(np.degrees(err[:, 0]) ** 2))),
        "rms_pitch": float(np.sqrt(np.nanmean(np.degrees(err[:, 1]) ** 2)))}
    q = math.radians(0.01)
    steps = arr["inclinometer_rad"] / q
    out["inclinometer_on_0p01deg_grid"] = bool(np.allclose(steps, np.round(steps), atol=1e-6))
    out["inclinometer_per_period"] = float(arr["inclinometer_t_s"].size / max(arr["t_s"].size, 1))
    out["phases"] = sorted(set(arr["phase"].tolist()))
    out["true_attitude_end_deg"] = np.degrees(arr["attitude_true_rad"][-1]).tolist()
    out["filtered_end_deg"] = arr["attitude_filtered_deg"][-1].tolist()
    out["true_force_min_kN_min"] = float(np.nanmin(arr["true_force_min_N"]) / 1e3)
    txt = json.dumps(out, indent=1, default=str)
    if a.out:
        Path(a.out).write_text(txt, encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
