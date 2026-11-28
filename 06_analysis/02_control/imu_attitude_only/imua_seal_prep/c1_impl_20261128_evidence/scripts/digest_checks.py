"""One-screen digest of the evidence checks folder."""
import json
import sys
from pathlib import Path

ev = Path(sys.argv[1])
for n in ("imua_l2b_vb20", "imua_scm_vb", "gd_v0_full"):
    m = json.loads((ev / f"meta_{n}.json").read_text(encoding="utf-8"))
    print(n, {k: m[k] for k in ("controller_tag", "tag_ok", "v5_hydraulics_tag", "expect_name", "expect_ok",
                                "imu_sensor_equal_to_meta", "c2_setup_imu_sensor_equal", "controller_imu_outputs",
                                "record_file", "record_meta_imu_sensor_equal", "inclinometer_on_0p01deg_grid",
                                "inclinometer_per_period", "phases")})
    print("   sensor_imu", m["sensor_imu"], "attitude", m["sensor_attitude"])
    print("   shapes t_s", m["shapes"]["t_s"], "incl", m["shapes"]["inclinometer_t_s"], "nan", sum(m["nan_counts"].values()),
          "err", m["inclinometer_minus_true_deg"], "end true/filt", m["true_attitude_end_deg"], m["filtered_end_deg"])
for n in ("imua_l2b_vb20", "gd_v0_full"):
    c = json.loads((ev / f"replay_control_{n}.json").read_text(encoding="utf-8"))
    print("replay", n, c["with_a_type"], "| off:", c["without_a_type_rebuild"]["settings_equal"],
          len(c["without_a_type_rebuild"]["setting_differences"]), "diffs")
g = json.loads((ev / "gd_summary.json").read_text(encoding="utf-8"))
print("gd", g["ready_t_s"], g["s8_end"], g["worst_roll_error"], g["runner_wall_s"])
print("gd phases", g["phases"])
