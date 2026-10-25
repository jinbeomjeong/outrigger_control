"""D-S8-7 (dynamics_model.md rev. 41): extract the post-settlement windows of an ML batch.

Read-only on the Chrono records (Chrono-dev python, no Chrono import). For every 'settle' episode:
1 ms pad record (pads.npz) from event - 2 s to event + 8 s, 10 Hz record / r8 series over the same
window, and the per-episode parameters (meta.json run.engine.*) needed by the reduced model.

Writes one compressed npz per episode plus index.json into <out_dir>.
Usage: python -I ds87_extract.py <batch_dir> <out_dir>
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
batch, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
PAD_KEYS = ["t", "F_cyl", "F_pressure", "f_seal", "seal_stuck", "N_raw", "N", "airborne", "s_motor", "s_link",
            "s_piston", "stroke_true", "head_pressure", "rod_pressure", "body_quat_wxyz", "F_seal_limit",
            "F_cyl_mean_interval", "ball_centre_world"]
REC_KEYS = ["t", "body_pos", "body_vel", "body_omega", "F_cyl", "s_ref", "s_motor", "meas.specific_force",
            "meas.angular_rate", "meas.head_pressure", "meas.rod_pressure", "F_crawler", "pad_in_contact"]
index = []
for d in sorted((batch / "episodes").iterdir()):
    if d.name.startswith("_") or not (d / "result.json").exists():
        continue
    case = json.loads((d / "case.json").read_text(encoding="utf-8"))["settings"]
    ep, base = case["episode"], case["base"]
    if ep.get("kind") != "settle":
        continue
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    t_ev = float(res["event_t_s"])
    meta = json.loads((d / "record" / "meta.json").read_text(encoding="utf-8"))
    eng = meta["run"]["engine"]
    act = eng["actuator"]
    pads = np.load(d / "pads.npz", allow_pickle=True)
    rec = np.load(d / "record" / "record.npz", allow_pickle=True)
    r8 = np.load(d / "r8_series.npz", allow_pickle=True)
    w = (pads["t"] >= t_ev - 2.0) & (pads["t"] <= t_ev + 8.0)
    w10 = (rec["t"] >= t_ev - 30.0) & (rec["t"] <= t_ev + 30.0)
    arr = {f"p_{k}": pads[k][w] for k in PAD_KEYS}
    arr.update({f"r_{k.replace('.', '_')}": rec[k][w10] for k in REC_KEYS})
    wr = (r8["t"] >= t_ev - 30.0) & (r8["t"] <= t_ev + 30.0)
    arr.update({"q_t": r8["t"][wr], "q_imu": r8["imu_samples"][wr], "q_phase": r8["phase"][wr],
                "q_issued_u": r8["issued_u"][wr], "q_valve_u": r8["valve_u"][wr]})
    info = dict(run=d.name, leg=ep["leg"], depth_m=float(ep["depth_m"]), ramp_s=float(ep["ramp_s"]), t_ev=t_ev,
                level=base["level"], fs_kN=float(base["fs_kN"]), beta_Pa=float(base["beta_GPa"]) * 1e9,
                L0r_m=float(base["rod_dead_length_m"]), floor_deg=base["floor_deg"],
                seal_limits_N=(act["s8"]["seal_friction"] or {}).get("limits_N", [0.0] * 4),
                k_out_N_m=act["s8"].get("k_out_N_m"),
                head_area_m2=act["head_area_m2"], k_rod_N_m=act["k_rod_N_m"],
                frame_N_m=act["frame_stiffness_N_m"], k_concrete_N_m=act["k_concrete_N_m"],
                head_dead_m=act["dead_length_m"], c_locked=act["damping_locked_N_s_m"],
                c_moving=act["damping_moving_N_s_m"], k_lat=eng["lateral_bushing"]["stiffness_N_m"],
                c_lat=eng["lateral_bushing"]["damping_actual_N_s_m"],
                imu_point=eng["sensor_truth"]["imu_mount_point_body_m"],
                k_op=meta["run"]["params_overrides"].get("actuator.L2b_NSC.axial_stiffness.operating_point_N_m"))
    np.savez_compressed(out / f"{d.name}.npz", **arr, info=json.dumps(info))
    index.append(info)
    print(d.name, ep["leg"], round(ep["depth_m"] * 1e3, 1), ep["ramp_s"], int(w.sum()))
(out / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
print("episodes", len(index))
