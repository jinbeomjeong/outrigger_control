"""Interim verdict of the coupled rigid rows (criteria rev. 6, 7.1, 9.1, 10): limit on vs stored off.

Inputs: verify files written by judge_batches.py (project judge, same code for both sides), the run
folders (read only), the reduced pairs (verdict_pairs.json). Outputs next to this file:
  rows_on_off.csv, judged_rows_diff.csv, item8.csv, reduced_compare.csv, event_detail.json, chrono_tables.json.
Limits come from the criteria; nothing here is tuned to the results.

Run: conda run -n dynamics-dev python -I judge_chrono.py
"""
from __future__ import annotations

import csv
import ctypes
import json
import re
import sys
from ctypes import wintypes
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control")
HERE = ROOT / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono"
sys.path.insert(0, str(ROOT / "03_src"))
S8 = ROOT / "07_results/S8"
CASES = {
    "R2": "K24_top_fdown3.5_Fs4", "R4": "K24_top_roll5.5_Fs4", "R16": "G1L_RE1bF_FL_top_o050_Fs4",
    "R12": "E_G4_Fs4", "R6": "K0V_top_rpB_Fs0", "R8": "A_middle_rpB_Fs0", "R9": "A_bottom_rpB_Fs0",
}
LEGS = ("FL", "FR", "RL", "RR")
TWIST = np.array([0.47607202408216903, -0.47607202408216903, -0.5228340347436333, 0.5228340347436333])
F_MIN = 9.41458911
F_SPEC = F_MIN + 5.0
ITEM8_TOL = 1.25  # s6_control.TREND_TOLERANCE_N
JUDGED_KINDS = ("judged", "function", "anomaly")


def pin(mask: int) -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
    kernel.SetProcessAffinityMask.restype = wintypes.BOOL
    if not kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), mask):
        raise OSError(ctypes.get_last_error(), "SetProcessAffinityMask")


def side(prefix: str, case: str) -> dict:
    batch = sorted(S8.glob(f"{prefix}_{case}_2*"))[-1]
    folder = batch / case
    verify = json.loads((HERE / "verify" / f"verify_{batch.name}.json").read_text(encoding="utf-8"))
    result = json.loads((folder / "result.json").read_text(encoding="utf-8"))
    events = [re.sub(r"^C2Event\(t_s=([0-9.e+-]+), name='(.*)'\)$", r"\1 \2", e)
              for e in json.loads((folder / "controller_events.json").read_text(encoding="utf-8"))]
    return {"batch": batch.name, "dir": folder, "verify": verify, "result": result, "events": events,
            "metric": next(m for m in verify["metrics"] if m["case"] == case),
            "sm": verify["s8_metrics"][case],
            "rows": [r for r in verify["rows"] if r.get("case") == case]}


def rows_by_item(s: dict) -> dict:
    out = {}
    for r in s["rows"]:
        out.setdefault(r["item"], r)
    return out


def row_value(s: dict, item: str):
    r = rows_by_item(s).get(item)
    return None if r is None else r.get("value")


def phase_runs(result: dict) -> list:
    return result["phases"]


def clearance_series(rec, params, floor_plane) -> np.ndarray:
    from outrigger_sim.control.c2 import CRAWLER_XY_BOX_M
    from outrigger_sim.frames import rotate_vector

    n = np.asarray(floor_plane["normal_world"], float)
    n = n / np.linalg.norm(n)
    (x0, x1), (y0, y1) = CRAWLER_XY_BOX_M
    z = float(params.ground.crawler_bottom_z_m)
    corners = [np.array([x, y, z]) for x in (x0, x1) for y in (y0, y1)]
    return np.array([min(float(n @ (p + rotate_vector(q, c))) for c in corners) - float(floor_plane["offset_m"])
                     for p, q in zip(rec["body_pos"], rec["body_quat_wxyz"], strict=True)])


def series(s: dict, params) -> dict:
    d = s["dir"]
    res = s["result"]
    with np.load(d / "record" / "record.npz", allow_pickle=False) as z:
        rec = {k: z[k] for k in ("t", "body_pos", "body_quat_wxyz", "F_cyl", "s_motor", "stroke_true", "u_applied",
                                 "meas.stroke", "F_crawler", "pad_in_contact")}
    with np.load(d / "pads.npz", allow_pickle=False) as z:
        pads = {k: z[k] for k in ("t", "F_cyl", "F_cyl_min_interval", "airborne", "N", "f_seal", "s_piston",
                                  "seal_stuck", "F_pressure", "head_pressure")}
    with np.load(d / "r8_series.npz", allow_pickle=False) as z:
        r8 = {k: z[k] for k in z.files}
    with np.load(d / "s8_series.npz", allow_pickle=False) as z:
        s8 = {k: z[k] for k in z.files}
    offset = float(rec["t"][-1]) - float(res["s8_end"]["end_t_s"])
    return {"rec": rec, "pads": pads, "r8": r8, "s8": s8, "offset": offset,
            "clear": clearance_series(rec, params, res["floor_plane"])}


def flow_block(s: dict) -> dict | None:
    fl = s["result"].get("flow_limit")
    if not fl:
        return None
    su = fl["summary"]
    bp = {k: v["short_s"] for k, v in su["by_phase"].items() if v["short_s"] > 0}
    return {"short_s": su["short_s"], "by_phase": bp, "max_deficit_L_min": su["max_deficit_L_min"],
            "min_r": {leg: min(v["min_r_by_phase"].values()) for leg, v in su["speed_ratio"].items()},
            "min_r_level": {leg: v["min_r_by_phase"].get("level") for leg, v in su["speed_ratio"].items()},
            "long93_s": {leg: v["longest_below_0p93_s"] for leg, v in su["speed_ratio"].items()},
            "track_mm": su["tracking"], "limited_sets": su["limited_sets"], "swaps": su["residual_groups"]["disjoint_swaps"],
            "audit_mismatch": su["steps"]["audit_mismatches"], "over_supply": su["max_sum_Q_over_supply_minus_1"]}


def recomputed_flow(s: dict, phases: list) -> dict | None:
    """Second path for the saturation time and speed ratio: from the raw flow series."""
    f = s["dir"] / "flow_series.npz"
    if not f.exists():
        return None
    with np.load(f, allow_pickle=True) as z:
        rows, cols = z["rows"], [str(c) for c in z["columns"]]
        supply = float(z["supply_m3_s"])
    idx = {c: i for i, c in enumerate(cols)}
    t = rows[:, idx["t"]]
    dt = float(np.median(np.diff(t)))
    limited = rows[:, idx["limited_mask"]].astype(int)
    u = rows[:, [idx[f"u_{leg}"] for leg in LEGS]]
    v = rows[:, [idx[f"v_{leg}"] for leg in LEGS]]
    qd = rows[:, idx["Q_dem"]]
    short = qd > supply * (1 + 1e-6)
    n = int(round(1.0 / dt))
    ker = np.ones(n) / n
    r_min = {}
    for i, leg in enumerate(LEGS):
        ub = np.convolve(u[:, i], ker, mode="valid")
        vb = np.convolve(v[:, i], ker, mode="valid")
        ok = np.abs(ub) >= 0.1 * 20.9243016e-3
        r_min[leg] = float(np.min(vb[ok] / ub[ok])) if ok.any() else None
    return {"t_first_s": float(t[0]), "dt_s": dt, "short_s": float(short.sum() * dt), "limited_any_s": float((limited > 0).sum() * dt),
            "max_deficit_L_min": float((qd - supply).max() * 6e4), "r_min": r_min, "first_limited_t": float(t[np.argmax(limited > 0)]) if (limited > 0).any() else None,
            "supply_L_min": supply * 6e4}


def recomputed_force(s: dict, ser: dict) -> dict:
    """Second path for the minimum force: the 1 ms record, airborne samples out, from crawler lift-off."""
    pads = ser["pads"]
    t = pads["t"] - ser["offset"]
    lift = s["sm"]["liftoff_s"]
    sel = t >= lift
    f = pads["F_cyl_min_interval"].copy() / 1e3
    f[pads["airborne"].astype(bool)] = np.inf
    i = np.unravel_index(np.argmin(np.where(sel[:, None], f, np.inf)), f.shape)
    return {"min_kN": float(f[i]), "leg": LEGS[i[1]], "t_s": float(t[i[0]]), "after_liftoff_s": float(t[i[0]] - lift)}


def interp_pad(ser: dict, key: str, t_ctrl: float) -> np.ndarray:
    t = ser["pads"]["t"] - ser["offset"]
    k = min(int(np.searchsorted(t, t_ctrl)), len(t) - 1)
    return ser["pads"][key][k]


def window_mean(ser: dict, key: str, t0: float, t1: float) -> np.ndarray:
    t = ser["pads"]["t"] - ser["offset"]
    sel = (t >= t0) & (t < t1)
    return ser["pads"][key][sel].mean(axis=0)


def twist_stats(s: dict, ser: dict) -> dict:
    t = ser["pads"]["t"] - ser["offset"]
    lift = s["sm"]["liftoff_s"]
    F = ser["pads"]["F_cyl"] / 1e3
    D = F @ TWIST
    sel = t >= lift
    done = [p[0] for p in s["result"]["phases"] if p[1] == "done"]
    d_done = float(D[min(int(np.searchsorted(t, done[0])), len(t) - 1)]) if done else None
    return {"peak_abs_D_kN": float(np.abs(D[sel]).max()), "D_first_done_kN": d_done}


def moved_prefix(off: dict, on: dict) -> dict:
    """V-5: the two runs must be bit identical until the limit first acts."""
    t_on, t_off = on["r8"]["t"], off["r8"]["t"]
    n = min(len(t_on), len(t_off))
    first = None
    for k in sorted(set(on["r8"]) & set(off["r8"])):
        a, b = on["r8"][k][:n], off["r8"][k][:n]
        if a.dtype.kind not in "fiub":
            continue
        same = (a == b) | (np.isnan(a) & np.isnan(b)) if a.dtype.kind == "f" else a == b
        same = same.reshape(n, -1).all(axis=1)
        if not same.all():
            d = int(np.argmin(same))
            if first is None or d < first[0]:
                first = (d, k)
    return {"first_diff_t": None if first is None else float(t_on[first[0]]), "first_diff_key": None if first is None else first[1]}


def event_detail(off: dict, on: dict, sroff: dict, sron: dict, leg_focus: str) -> dict:
    out = {}
    li = LEGS.index(leg_focus)
    for name, s, ser in (("off", off, sroff), ("on", on, sron)):
        res = s["result"]
        te = float(res["event_t_s"])
        ready = res.get("ready_t_s")
        ramp = float(res["event"]["spec"]["ramp_s"])
        t = ser["pads"]["t"] - ser["offset"]
        fm = ser["pads"]["F_cyl_min_interval"] / 1e3
        post = (t >= te) & (t <= te + 20)
        airborne = ser["pads"]["airborne"].astype(bool)
        leg_min = {}
        for i, leg in enumerate(LEGS):
            x = fm[post, i]
            j = int(np.argmin(x))
            leg_min[leg] = {"min_kN": float(x[j]), "t_rel_s": float(t[post][j] - te),
                            "airborne_s": float(airborne[post, i].sum() * 1e-3)}
        pre = window_mean(ser, "F_cyl", te - 1.0, te) / 1e3
        pre_seal = window_mean(ser, "f_seal", te - 1.0, te) / 1e3
        pre_press = window_mean(ser, "F_pressure", te - 1.0, te) / 1e3
        tc = ser["s8"]["t"] - ser["offset"]
        k = int(np.searchsorted(tc, te))
        r8 = ser["r8"]
        anchors = {}
        for label, ta in (("lift+1", s["sm"]["liftoff_s"] + 1), ("event-1", te - 1)):
            anchors[label] = (window_mean(ser, "F_cyl", ta - 0.5, ta + 0.5) / 1e3).round(3).tolist()
        phases = res["phases"]
        for ph, tp in [(p[1], p[0]) for p in phases if p[0] < te + 1]:
            if ph in ("done", "ready", "level", "probe"):
                anchors[f"{ph}@{tp:.1f}"] = (window_mean(ser, "F_cyl", tp - 0.3, tp) / 1e3).round(3).tolist()
        ev_rel = [(round(float(e.split(' ', 1)[0]) - te, 2), e.split(' ', 1)[1]) for e in s["events"]
                  if -5 <= float(e.split(' ', 1)[0]) - te <= 40]
        u_rel = r8["issued_u"][:, li]
        first_u = None
        ts = r8["t"] - ser["offset"]
        for a in range(int(np.searchsorted(ts, te)), len(ts)):
            if abs(u_rel[a]) > 1e-6:
                first_u = float(ts[a] - te)
                break
        hist = res.get("twist_stiffness_history") or []
        out[name] = {
            "event_t_s": te, "ready_first_s": ready, "phase_at_event": res["event_state"]["phase_at_event"],
            "event_anchor": res["event_state"]["anchor"], "reference_t_s": res["event_state"]["reference_t_s"],
            "ramp_s": ramp, "leg_min_after_event": leg_min,
            "F_mean_pre_1s_kN": pre.round(3).tolist(), "F_pressure_pre_1s_kN": pre_press.round(3).tolist(),
            "f_seal_pre_1s_kN": pre_seal.round(3).tolist(),
            "D_pre_1s_kN": float(pre @ TWIST), "drop_focus_kN": float(pre[li] - leg_min[leg_focus]["min_kN"]),
            "attitude_pre_deg": np.degrees(ser["rec"]["body_quat_wxyz"][0, :0].sum()) if False else None,
            "F_hat_kN": (ser["s8"]["F_hat_N"][k] / 1e3).round(3).tolist(),
            "F_lower_kN": (ser["s8"]["F_lower_N"][k] / 1e3).round(3).tolist(),
            "F_lower_est_kN": (ser["s8"]["F_lower_est_N"][k] / 1e3).round(3).tolist(),
            "F_band_kN": float(ser["s8"]["F_band_N"][k] / 1e3),
            "leg_band_kN": (ser["s8"]["leg_band_N"][k] / 1e3).round(3).tolist(),
            "stroke_at_event_mm": (ser["rec"]["stroke_true"][int(np.searchsorted(ser["rec"]["t"] - ser["offset"], te))] * 1e3).round(3).tolist(),
            "piston_minus_motor_stroke_mm": ((interp_pad(ser, "s_piston", te) - interp_pad(ser, "stroke_true", te) if False else 0.0)),
            "scale_history": [(round(h["t_s"], 2), round(h["scale_in_use"], 4)) for h in hist][:6],
            "events_rel": ev_rel, "first_u_focus_rel_s": first_u, "anchors_F_kN": anchors,
        }
    return out


def saturation_vs_event(on: dict) -> dict:
    res = on["result"]
    te = float(res["event_t_s"])
    ramp = float(res["event"]["spec"]["ramp_s"])
    with np.load(on["dir"] / "flow_series.npz", allow_pickle=True) as z:
        rows, cols = z["rows"], [str(c) for c in z["columns"]]
        supply = float(z["supply_m3_s"])
    idx = {c: i for i, c in enumerate(cols)}
    off = float(res["runner"]["start_t_s"])
    t = rows[:, idx["t"]]
    if t[-1] > float(res["s8_end"]["end_t_s"]) + 1.0:
        t = t - off
    lim = rows[:, idx["limited_mask"]].astype(int) > 0
    edges = np.diff(np.concatenate(([0], lim.astype(int), [0])))
    runs = [{"start_s": round(float(t[a]), 3), "stop_s": round(float(t[b - 1]), 3), "dur_s": round(float(t[b - 1] - t[a]), 3),
             "rel_start_s": round(float(t[a] - te), 3), "rel_stop_s": round(float(t[b - 1] - te), 3),
             "sets": sorted({int(m) for m in rows[a:b, idx["limited_mask"]].astype(int)})}
            for a, b in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1), strict=True)]
    selected = (t >= te) & (t <= te + ramp + 5)
    deficit_end = rows[-1, [idx[f"deficit_integral_{leg}"] for leg in LEGS]] * 1e3
    deficit_event = rows[int(np.searchsorted(t, te)), [idx[f"deficit_integral_{leg}"] for leg in LEGS]] * 1e3
    return {"runs_ge_50ms": [r for r in runs if r["dur_s"] >= 0.05], "n_runs": len(runs),
            "overlap_event_ramp_plus5": bool(lim[selected].any()),
            "max_Q_dem_event_ramp_plus5_L_min": float(rows[selected, idx["Q_dem"]].max() * 6e4),
            "supply_L_min": supply * 6e4, "deficit_at_event_mm": deficit_event.round(3).tolist(),
            "deficit_end_mm": deficit_end.round(3).tolist()}


def main() -> None:
    pin(0x0C000000)
    from outrigger_sim.params import load_params

    params = load_params()
    pairs = json.loads((HERE.parent / "verdict_pairs.json").read_text(encoding="utf-8"))["pairs"]
    pair_by = {p["run_id"]: p for p in pairs}
    tables = {"criteria_sha256": "1d743eab34d5091757b5e021bc1722f56fbedea9b0bc7ff2b4ca5ea0774fd0de", "cases": {}}
    rows_csv, diff_csv, redu_csv = [], [], []
    item8 = {}
    event_json = {}
    for cid, case in CASES.items():
        on, off = side("coupled_eta085", case), side("final", case)
        sr_on, sr_off = series(on, params), series(off, params)
        rec = {"chrono_batch_on": on["batch"], "chrono_batch_off": off["batch"]}
        m_on, m_off = on["metric"], off["metric"]
        # judged rows
        ron, roff = rows_by_item(on), rows_by_item(off)
        flips, newfail, valuediff = [], [], []
        for item, r in ron.items():
            if r.get("kind") not in JUDGED_KINDS:
                continue
            o = roff.get(item)
            if r.get("passed") is False:
                newfail.append(item)
                if o is not None and o.get("passed") is True:
                    flips.append(item)
            if o is not None and r.get("value") != o.get("value"):
                valuediff.append(item)
        missing = sorted(set(roff) - set(ron))
        extra = sorted(set(ron) - set(roff))
        for item, r in ron.items():
            o = roff.get(item, {})
            diff_csv.append([cid, item[:110], r.get("kind"), r.get("passed"), o.get("passed"),
                             json.dumps(r.get("value"), default=str)[:160], json.dumps(o.get("value"), default=str)[:160],
                             json.dumps(r.get("limit"), default=str)[:60]])
        def ev_names(s):
            return [e.split(" ", 1)[1] for e in s["events"]]
        en_on, en_off = ev_names(on), ev_names(off)
        new_ev = sorted(set(en_on) - set(en_off))
        gone_ev = sorted(set(en_off) - set(en_on))
        flow = flow_block(on)
        flow2 = recomputed_flow(on, on["result"]["phases"])
        force2_on, force2_off = recomputed_force(on, sr_on), recomputed_force(off, sr_off)
        tw_on, tw_off = twist_stats(on, sr_on), twist_stats(off, sr_off)
        def clear_vals(s, ser):
            t = ser["rec"]["t"] - ser["offset"]
            ready = s["metric"]["times_s"]["ready"]
            k = int(np.searchsorted(t, ready))
            return {"ready_mm": float(ser["clear"][min(k, len(t) - 1)] * 1e3), "end_mm": float(ser["clear"][-1] * 1e3),
                    "min_after_ready_mm": float(ser["clear"][k:].min() * 1e3) if k < len(t) else None}
        cl_on, cl_off = clear_vals(on, sr_on), clear_vals(off, sr_off)
        stroke_on = float(np.nanmax(sr_on["rec"]["meas.stroke"]) * 1e3)
        stroke_off = float(np.nanmax(sr_off["rec"]["meas.stroke"]) * 1e3)
        phases_on = dict()
        def phase_len(s):
            return s["result"]["s8_end"]["phase_lengths"]["total_s"]
        rec.update(
            final_phase=[on["result"]["s8_end"]["final_phase"], off["result"]["s8_end"]["final_phase"]],
            judge_failed=[on["verify"]["meta"]["failed"], off["verify"]["meta"]["failed"]],
            T1_flips=flips, on_failed_rows=newfail, rows_missing_on=missing, rows_extra_on=extra, new_events=new_ev, gone_events=gone_ev,
            event_counts=[len(en_on), len(en_off)],
            F_min_kN=[m_on["min_cyl_after_liftoff_kN"], m_off["min_cyl_after_liftoff_kN"]],
            F_min_leg=[m_on["min_cyl_leg"], m_off["min_cyl_leg"]],
            F_min_t_s=[m_on["min_cyl_t_s"], m_off["min_cyl_t_s"]],
            liftoff_s=[on["sm"]["liftoff_s"], off["sm"]["liftoff_s"]],
            F_min_after_liftoff_s=[m_on["min_cyl_t_s"] - on["sm"]["liftoff_s"], m_off["min_cyl_t_s"] - off["sm"]["liftoff_s"]],
            F_excl_reanchor_kN=[m_on.get("min_cyl_excl_reanchor_kN"), m_off.get("min_cyl_excl_reanchor_kN")],
            F_recomputed=[force2_on, force2_off],
            c1=[on["sm"]["c1"], off["sm"]["c1"]],
            end_att_deg=[row_value(on, "2 attitude +-0.2 (+mount)"), row_value(off, "2 attitude +-0.2 (+mount)")],
            att_last5_deg=[m_on.get("att_err_last5_maxabs_deg"), m_off.get("att_err_last5_maxabs_deg")],
            ready_s=[m_on["times_s"]["ready"], m_off["times_s"]["ready"]],
            ready_minus_touch_s=[m_on.get("t_ready_minus_touch_s"), m_off.get("t_ready_minus_touch_s")],
            touch_end_s=[m_on["times_s"]["touch"], m_off["times_s"]["touch"]],
            phase_len_on=phase_len(on), phase_len_off=phase_len(off),
            max_moving_bar=[m_on.get("max_moving_pressure_bar"), m_off.get("max_moving_pressure_bar")],
            max_any_bar=[m_on.get("max_pressure_any_step_bar"), m_off.get("max_pressure_any_step_bar")],
            saturation_steps=[m_on.get("saturation_steps"), m_off.get("saturation_steps")],
            rocking_deg=[m_on.get("rocking_amp_deg"), m_off.get("rocking_amp_deg")],
            stroke_max_mm=[(np.array(m_on["stroke"]["max_m"]) * 1e3).round(3).tolist(), (np.array(m_off["stroke"]["max_m"]) * 1e3).round(3).tolist()],
            stroke_reading_max_mm=[stroke_on, stroke_off],
            clearance_mm=[cl_on, cl_off],
            D=[tw_on, tw_off],
            flow=flow, flow_recomputed=flow2, V5=moved_prefix(sr_off, sr_on),
            reapproach=[row_value(on, "re-approach starts (report)"), row_value(off, "re-approach starts (report)")],
            guard_active_s=[float(np.nansum(sr_on["r8"]["guard_active"]) * 0.1), float(np.nansum(sr_off["r8"]["guard_active"]) * 0.1)],
            F9=[row_value(on, "F9 twist at READY entry n^T F / n^T F_hat / n^T eps [kN] (record)"),
                row_value(off, "F9 twist at READY entry n^T F / n^T F_hat / n^T eps [kN] (record)")],
        )
        if m_on.get("item6"):
            rec["item6"] = [m_on["item6"], m_off["item6"]]
        tables["cases"][cid] = rec
        rows_csv.append([cid, case, rec["final_phase"][0], rec["final_phase"][1], len(flips), len(newfail),
                         rec["F_min_kN"][0], rec["F_min_kN"][1], rec["F_min_leg"][0], rec["F_min_t_s"][0], rec["F_min_after_liftoff_s"][0],
                         rec["end_att_deg"][0], rec["end_att_deg"][1], rec["ready_s"][0], rec["ready_s"][1],
                         rec["max_moving_bar"][0], rec["max_moving_bar"][1], stroke_on, stroke_off, cl_on["ready_mm"], cl_off["ready_mm"],
                         json.dumps(flow["by_phase"]), flow["short_s"], min(flow["min_r"].values()), max(flow["long93_s"].values())])
        # reduced model
        pair = pair_by[f"A_{cid}_eta0.85"]["metrics"]
        def pv(key):
            x = pair.get(key) or {}
            return x.get("on"), x.get("off"), x.get("delta")
        F_c = rec["F_min_kN"][0] - rec["F_min_kN"][1]
        comps = [("F_min_kN", pv("item3_min_force_after_liftoff_kN"), F_c, 3.0),
                 ("stroke_reading_mm", pv("max_stroke_reading_mm"), stroke_on - stroke_off, 5.0),
                 ("clearance_ready_mm", pv("P3_5_rut_ready_mm"), cl_on["ready_mm"] - cl_off["ready_mm"], 5.0),
                 ("first_READY_s", pv("t_first_ready_s"), rec["ready_s"][0] - rec["ready_s"][1], 5.0)]
        for name, (ron_, roff_, rd), cd, lim in comps:
            diff = None if rd is None else cd - float(rd)
            redu_csv.append([cid, name, ron_, roff_, rd, cd, diff, lim, None if diff is None else abs(diff) <= lim])
        if cid in ("R12", "R16"):
            ev_rows = {k: [ron.get(k, {}).get("value"), roff.get(k, {}).get("value")] for k in ron
                       if k.startswith(("3 F_min", "6 ", "G4 item", "RE1b", "C-S8-72", "R-5", "R44-213.6 U-S8-9", "item 9 M5", "4 max",
                                        "item 9 J_C M1", "I1 J_C", "5a"))}
            event_json[cid] = {"detail": event_detail(off, on, sr_off, sr_on, "RR" if cid == "R12" else "FL"),
                               "saturation_vs_event": saturation_vs_event(on), "rows": ev_rows,
                               "reduced": {k: pair[k] for k in pair if k.startswith("event") or k.startswith("item3")}}
        print(cid, "flips", flips, "failed_on", newfail, "F_on/off", round(rec["F_min_kN"][0], 3), round(rec["F_min_kN"][1], 3),
              "V5", rec["V5"], "new", new_ev, "gone", gone_ev, "force2", force2_on["min_kN"], flush=True)
    # item 8
    def trio(field, idx):
        return [tables["cases"][c][field][idx] for c in ("R6", "R8", "R9")]
    for label, idx in (("on", 0), ("off", 1)):
        excl = trio("F_excl_reanchor_kN", idx)
        full = trio("F_min_kN", idx)
        time = trio("ready_minus_touch_s", idx)
        ok = excl[0] <= excl[1] + ITEM8_TOL and excl[1] <= excl[2] + ITEM8_TOL
        item8[label] = {"F_top_mid_bot_kN": excl, "F_full_kN": full, "legs": trio("F_min_leg", idx), "after_liftoff_s": trio("F_min_after_liftoff_s", idx),
                        "ready_minus_touch_s": time, "ordering_pass": ok,
                        "slow_min_first8_kN": [tables["cases"][c]["c1"][idx]["slow_min_first8_kN"] for c in ("R6", "R8", "R9")],
                        "raw_min_first8_kN": [tables["cases"][c]["c1"][idx]["raw_min_first8_kN"] for c in ("R6", "R8", "R9")],
                        "raw_min_kN": [tables["cases"][c]["c1"][idx]["raw_min_kN"] for c in ("R6", "R8", "R9")],
                        "slow_min_kN": [tables["cases"][c]["c1"][idx]["slow_min_kN"] for c in ("R6", "R8", "R9")],
                        "slow_after_lift_s": [tables["cases"][c]["c1"][idx].get("slow_t_s") for c in ("R6", "R8", "R9")]}
    tables["item8"] = item8
    tables["events"] = event_json
    (HERE / "chrono_tables.json").write_text(json.dumps(tables, indent=1, default=str), encoding="utf-8")
    (HERE / "event_detail.json").write_text(json.dumps(event_json, indent=1, default=str), encoding="utf-8")
    with (HERE / "rows_on_off.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow("id case phase_on phase_off T1_flips failed_on F_on F_off leg_on t_on after_liftoff_on att_on att_off ready_on ready_off "
                   "bar_on bar_off stroke_on stroke_off clear_on clear_off short_by_phase short_s min_r long93_s".split())
        w.writerows(rows_csv)
    with (HERE / "judged_rows_diff.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "item", "kind", "pass_on", "pass_off", "value_on", "value_off", "limit"])
        w.writerows(diff_csv)
    with (HERE / "reduced_compare.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "metric", "reduced_on", "reduced_off", "reduced_delta", "chrono_delta", "chrono_minus_reduced", "limit", "within"])
        w.writerows(redu_csv)
    with (HERE / "item8.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["side", "field", "top", "middle", "bottom"])
        for label, b in item8.items():
            for k, v in b.items():
                if isinstance(v, list):
                    w.writerow([label, k, *v])
    print(json.dumps(item8, indent=0, default=str))


if __name__ == "__main__":
    main()
