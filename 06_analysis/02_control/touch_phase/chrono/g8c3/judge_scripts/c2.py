"""G8C3 batch offline reading, no simulation: stroke coordinates, guard margin, bias reconstruction and its neighbours in t_P, patch contact,
true clearance at t_P, LOC and end, tie between FR and b_RL against the harness line. Writes c2_out.json."""
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
WT = HERE.parent / "cad_c4g2" / "wt"
sys.path.insert(0, str(WT / "03_src"))
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.control import c2  # noqa: E402

B = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_g8c3_20261105")
A3 = Path(r"C:\workspace\outrigger_control\07_results\S6\bundleC_g8c76_p28acc_final_G8C3_top_edge_RL_g230_L1R_20261030_233212\G8C3_top_edge_RL_g230")
RUNS = {"A3off": A3, "E1": B / "G8C3_top_edge_RL_g230_C4G2", "R2L1": B / "G8C3_top_rpB_RL_g230_off", "R3L1": B / "G8C3_top_rpB_RL_g230_C4G2",
        "R2": B / "G8CL2b_top_rpB_RL_g230_Fs4_off", "R3": B / "G8CL2b_top_rpB_RL_g230_Fs4_C4G2"}
geo = c2.C2Geometry.from_params(load_params(level="top"))
LEGS = ["FL", "FR", "RL", "RR"]
CORNERS = geo.crawler_corners_xy_m


def tilt(f):
    """Raw roll, pitch of IMU samples (n, 3): accelerometer tilt; sign checked against the true attitude below."""
    return np.arctan2(f[..., 1], f[..., 2]), np.arctan2(-f[..., 0], np.hypot(f[..., 1], f[..., 2]))


def ev(d):
    out = []
    for e in json.loads((d / "controller_events.json").read_text(encoding="utf-8")):
        m = re.match(r"C2Event\(t_s=([\d.eE+-]+), name='(.*)'\)", e)
        if m:
            out.append((float(m.group(1)), m.group(2)))
    return out


res_all = {}
for name, d in RUNS.items():
    rec = np.load(d / "record" / "record.npz")
    pads = np.load(d / "pads.npz")
    gap = np.load(d / "crawler_gap.npz")
    r8 = np.load(d / "r8_series.npz")
    result = json.loads((d / "result.json").read_text(encoding="utf-8"))
    t0 = float(result["settings"]["start_t_s"])
    events = ev(d)
    t_loc = next(t for t, n in events if n == "crawler_liftoff_confirmed")
    anchor = next(n for t, n in events if n.startswith("INFO_LOC_CLEARANCE_ANCHOR"))
    anchor = np.array([float(v) for v in anchor.split(":")[1].split(",")])
    t = rec["t"]
    meas_s = rec["meas.stroke"]
    corr = rec["meas.stroke_corrected"]
    phases = [(float(a) + t0, str(b)) for a, b in result["phases"]]
    print(name, "t range rec", t[0], t[-1], "r8", r8["t"][0], r8["t"][-1], "t0", t0, "phases", result["phases"][:4], "loc", t_loc)
    t_done = next((a for a, b in phases if b == "done"), None)
    t_level = next((a for a, b in phases if b == "level"), None)
    # stroke coordinates at the FR leg
    coords = {k: float(np.max(v[:, 1]) * 1e3) for k, v in (("meas_stroke_guard", meas_s), ("record_s_motor", rec["s_motor"]), ("record_s_ref", rec["s_ref"]), ("record_stroke_true", rec["stroke_true"]),
                                                           ("meas_corrected", corr), ("pads_s_motor", pads["s_motor"]), ("pads_stroke_true", pads["stroke_true"]), ("pads_s_piston", pads["s_piston"]) if "s_piston" in pads.files else ("pads_s_motor2", pads["s_motor"]))}
    # controller time grid of r8 and record
    tr = r8["t"]
    imu = r8["imu_samples"]
    roll, pitch = tilt(imu)
    raw = np.column_stack([roll.mean(axis=1), pitch.mean(axis=1)])
    mean_stroke = meas_s.mean(axis=1)
    i_loc = int(np.argmin(np.abs(t - t_loc)))
    j_loc = int(np.argmin(np.abs(tr - t_loc)))
    span = 0.010
    i_p = i_loc
    while i_p > 0 and mean_stroke[i_loc] - mean_stroke[i_p] < span:
        i_p -= 1
    t_P = float(t[i_p])
    j_p = int(np.argmin(np.abs(tr - t_P)))
    # settle attitude: search the CHECK window, the last 2 s before TOUCH phase start, mean raw tilt
    t_check_end = next((a for a, b in phases if b == "touch"), None)
    win = (tr > t_check_end - 2.0 - 1e-9) & (tr <= t_check_end + 1e-9)
    settle = raw[win].mean(axis=0)

    def bias_at(k):
        jj = int(np.argmin(np.abs(tr - t[k])))
        cc = geo.clearance_corners_m(corr[k])
        dphi, dth = raw[jj] - settle
        rise = CORNERS[:, 1] * dphi - CORNERS[:, 0] * dth
        return cc - (rise - rise.min()) + 0.005, cc

    b_tp, c_tp = bias_at(i_p)
    # order: corners RR, RL, FR, FL -> leg order FL, FR, RL, RR
    leg_order = [3, 2, 1, 0]
    b_legs = b_tp[leg_order] * 1e3
    neigh = {}
    for off in range(-3, 4):
        k = i_p + off
        b, _ = bias_at(k)
        jj = int(np.argmin(np.abs(tr - t[k])))
        neigh[off] = dict(t=round(float(t[k] - t0), 1), b_RL=round(float(b[leg_order][2] * 1e3), 1), att_deg=np.degrees(raw[jj]).round(3).tolist())
    tg = gap["t"]
    ming = gap["min_gap_m"]
    gap_at = lambda x: float(ming[int(np.argmin(np.abs(tg - x)))] * 1e3)  # noqa: E731
    i_end_level = int(np.flatnonzero(t <= (t_done if t_done else t[-1]))[-1])
    ce_end = (geo.clearance_corners_m(corr[i_end_level]) - anchor[leg_order] * 1e-3)
    # first crawler departure, first load-free time
    fc = np.asarray(rec["F_crawler"], float)
    fcn = np.linalg.norm(fc, axis=1)
    i_off = int(np.flatnonzero(fcn > 0)[-1]) if (fcn > 0).any() else None
    # patch: RL pad contact time and force onset
    n_rl = rec["F_contact_n"][:, 2]
    i_c = next((i for i in range(len(t)) if abs(n_rl[i]) > 0 and (t[i] > t0)), None)
    s_rl_contact = float(meas_s[i_c, 2] * 1e3) if i_c is not None else None
    out = dict(run=name, t0=t0, t_touch=None if t_check_end is None else t_check_end - t0, t_level=None if t_level is None else t_level - t0, t_done=None if t_done is None else t_done - t0,
               t_loc=t_loc - t0, t_P=t_P - t0, n_tail=i_loc - i_p + 1, coords_FR_max_mm={k: round(v, 2) for k, v in coords.items()},
               FR_guard_at_done=round(float(meas_s[i_end_level, 1] * 1e3), 2), u_at_done=round(float(rec["u_applied"][i_end_level, 1] * 1e3), 3), pred_at_done=round(float(meas_s[i_end_level, 1] + rec["u_applied"][i_end_level, 1] * 0.2) * 1e3, 2),
               guard_margin_mm=round(682.8 - float(meas_s[i_end_level, 1] + rec["u_applied"][i_end_level, 1] * 0.2) * 1e3, 2),
               anchor_FL_FR_RL_RR=anchor.tolist(), b_reconstructed=b_legs.round(1).tolist(), recon_err_mm=round(float(np.max(np.abs(b_legs - anchor))), 2), settle_deg=np.degrees(settle).round(3).tolist(), c_tP_FL_FR_RL_RR=(c_tp[leg_order] * 1e3).round(1).tolist(),
               cc_tP=gap_at(t_P), cc_loc=gap_at(t_loc), cc_done=gap_at(t_done) if t_done else None, cc_end=float(ming[-1] * 1e3), ce_at_done=round(float(ce_end.min() * 1e3), 2), t_crawler_load_last=None if i_off is None else float(t[i_off] - t0),
               neighbours=neigh, t_RL_contact=None if i_c is None else float(t[i_c] - t0), s_RL_contact_mm=s_rl_contact,
               legs_end_guard_mm=(meas_s[i_end_level] * 1e3).round(2).tolist(), F_end_kN=(rec["F_cyl"][-1] / 1e3).round(1).tolist(), min_gap_after=float(ming[(tg >= t_loc)].min() * 1e3))
    side = json.loads((d / "g8c_job_side.json").read_text(encoding="utf-8")) if (d / "g8c_job_side.json").exists() else {}
    if name in ("R2", "R3"):
        g8 = result.get("g8", {})
        out["patch"] = {k: g8.get(k) for k in ("g0_m", "h_m", "g_start_measured_m", "gaps_above_base_floor_m", "box_top_floor_frame_m", "floor_z_m", "crawler_gap_end_m")}
        out["patch"]["crawler_gap_end_m"] = (g8.get("crawler_gap_end_m") or {}).get("min")
    res_all[name] = out
    print(name, json.dumps({k: v for k, v in out.items() if k not in ("neighbours", "patch")}, default=str))
    print("   neigh", json.dumps(neigh))
    if "patch" in out:
        print("   patch", json.dumps(out["patch"], default=str))
(HERE / "c2_out.json").write_text(json.dumps(res_all, indent=1, default=str), encoding="utf-8")
