"""Replay with the project AttitudeEstimator and C2 config (period, window) on recorded samples."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "03_src"))
from outrigger_sim.sensors.attitude import AttitudeEstimator, CascadedLowPass  # noqa: E402
from outrigger_sim.control.c2 import C2Config  # noqa: E402

cfg = C2Config().with_10hz_d1()
print("period", cfg.period_s, "imu", cfg.r8.imu_sample_period_s, "tau", cfg.filters.attitude_time_constant_s,
      "stages", cfg.filters.attitude_stage_count, "check_avg", cfg.target.check_average_s,
      "check_time", cfg.target.check_time_s, "check_max", cfg.target.check_max_s)
batch = Path(sys.argv[1])
for c in sys.argv[2:]:
    r8 = np.load(batch / c / "r8_series.npz")
    res = json.loads((batch / c / "result.json").read_text(encoding="utf-8"))
    est = AttitudeEstimator(CascadedLowPass(cfg.filters.attitude_time_constant_s,
                                            cfg.filters.attitude_stage_count,
                                            cfg.r8.imu_sample_period_s))
    out = []
    for k in range(len(r8["t"])):
        for s in r8["imu_samples"][k]:
            e = est.update(r8["t"][k], s)
        out.append((e.roll_rad, e.pitch_rad))
    out = np.degrees(np.array(out))
    chk = np.where(r8["phase"] == "check")[0]
    print(c, "replay last10", out[chk[-10:]].mean(axis=0), "acc", res["acceptance"]["crawler_attitude_deg"])
    # search a 10-window that matches the acceptance value
    acc = np.array(res["acceptance"]["crawler_attitude_deg"])
    best = min(range(10, len(out)), key=lambda j: np.abs(out[j - 10:j].mean(axis=0) - acc).sum())
    print("   best window end idx", best, "t", r8["t"][best - 1], out[best - 10:best].mean(axis=0))
    print("   controller_meta target", json.dumps(res.get("controller_meta", {}).get("target", {}))[:600])
