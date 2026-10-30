"""Spec rev. 67 (coverage gaps G1 / G2 / G7): reduced closed-loop screen of floor events on every leg, after READY
and during LEVEL, and of the pre-grounded start (PS-7a / FL mirror / 7b / 7c).

Harness: the r51_reapp_closed_loop.py plant and loop (imported, not copied): reduced 6-DoF FlexPlant (rigid mast)
+ L1-R rod-side law (armed after the crawler settle), Coulomb seal friction per leg, valve first-order lag 0.1 s
(1 ms chunks), leg damping switch locked / moving, IMU 10 ms samples, head and rod readings from the net oil force
(r64_g4_closed_loop.with_two_pressures). Controller: the project C2 (03_src, read only), plain
``C2Controller`` with c2py_r8d1_closed_loop.preset_config(COMBINED) = ``with_10hz_d1`` (rev. 64-66: FAULT_REGROUND,
soil response, D1'' YAML mass before READY, re-approach re-trigger rule) minus zero calibration / REANCHOR / target
check (CHECK runs with check_time 0: B1' gyro bias + raw-tilt quiet window). Ideal sensors.

Screen (mode "screen"): events = Poly345 floor settlement of one pad applied on every 1 ms chunk
  G4    11.5 mm / 2 s     (5.75 mm/s < v_max: event-less rules, U-S8-43)
  RE1bF 30 mm / 0.05 s    (fast: floor-event rules)
  FS24  24 mm / 0.3 s     (fast: floor-event rules)
x leg FL / FR / RL / RR x auger top / bottom x F_s 0 / 8 kN (rear 0.833 x) x start phase offset 0 / 0.05 s
x timing  ready = READY + 5 s (+ offset);  level = middle of LEVEL after the crawler lift-off confirmation (LOC):
          t_loc + 0.5 (t_done - t_loc) of the same base run (+ offset).
The branch (deepcopy of plant and controller) is taken 0.5 s before the event so that D_0 of the twist-work row
(spec 248.3) has its [-0.5, 0] s window. Each branch runs until the controller has been back in READY for 3 s and
at least 12 s after the event (at most 60 s after the event).

Judgement per run (1 ms plant record; F = true cylinder force, contact = pad contact force, lift = contact <= 0):
  fast events (U-S8-43): event legs = settled leg + its diagonal
    U-S8-32 event-leg row: union lift time of the pair <= 1.8 s, last touch-down <= event + 3.0 s, FAULT 0
    U57 adjacent legs: physical window W = [event, min(pair last touch-down + T_3, event + 5 s)], T_3 = 0.82 s
         (ASSUMPTION for bottom: the top value); lift sum (both adjacent legs) in W <= 0.5 s, max pad gap <= 2 mm,
         lift outside W (to the run end) = 0
    F_min row: min 1 ms F of every leg after W (to the run end) >= F_min (outside the event transient)
  slow event (G4): no lift on any leg, min 1 ms F of every leg after the event >= F_min, FAULT 0
  both: final attitude (true deck attitude, mean of the last 1 s) within +-0.2 deg of the target 0 and READY at the
    end; twist-work recurrence (248.3: P = 1/2 (D - D_0)(n . u_valve), 0.5 s bins from the event to 8 s, judged bins
    start >= 1.5 s, bundle = consecutive bins > +20 J, bundles <= 1)
  records: re-approach starts (time, leg, twist sign), starts after 1.5 s, sign changes, max |attitude change|, time
    back to READY, crawler re-contact in the run, warnings / faults after the event.

PS-7 (mode "ps7", G2): before the controller starts (after the crawler settle, before arm()), one leg is extended
at v_max to g_0 + delta (g_0 = pad gap at zero stroke, harness value) and the plant is held 20 s (Chrono
RRPRE_SETTLE_MIN_S); then t = 0, arm(), controller from CHECK to READY + 5 s.
  PS7a_RR +2 mm, PS7a_FL +2 mm (mirror), PS7b_RR -1.5 mm, PS7c_RR -2.7 mm, ref (no pre-extension)
  x top / bottom x F_s 0 / 8 x controller "proj" (project C2 as it is) / "cap" (candidate P-S8-26, harness subclass:
  TOUCH free-air reference capped at m_rod g + F_s,max, F_s,max = 8 kN front / 6.67 kN rear, ASSUMPTION).
  Zero calibration cannot run in this harness (the preset has no CHECK calibration input: the controller reports
  WARN_PRESSURE_ZERO_SKIPPED:all:no_check), so the calibration path of PS-7 is left to Chrono.
  D8 row (spec 92): min 1 ms F after the crawler lift-off >= F_min + 5 kN, no pad lift after the crawler lift-off,
  final attitude +-0.2 deg, READY; events (WARN_GYRO_BIAS_SKIPPED, WARN_PRESSURE_ZERO_*), phase timeline.

Run (dynamics-dev, MKL_THREADING_LAYER=TBB):
  python -I r67_g1_screen.py <project_root> <out_json> [workers]
Env: R67_MODE = screen | ps7 | all (default all); R67_SLICE = "a:b" (fractions of the sorted job list, for a P / E
split into two processes); R67_AFFINITY = hex mask set on the parent before the pool (inherited by the workers);
R67_OFFSETS = comma list (default 0,0.05); R67_FILTER = substring list of job keys; R67_CANDIDATE = wrapper candidate
(s9_slope_fix_candidates tokens, e.g. P36s+P37t+R4c30+P38z; spec 427.11 / 429.5). Every screen run stores commands_sha256
(prefix + branch commands). Deterministic.
"""
from __future__ import annotations

import copy
import ctypes
import dataclasses
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
_HERE = ROOT / "04_scripts" / "03_control" / "s8"
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import numpy as np  # noqa: E402

import r51_reapp_closed_loop as r51  # noqa: E402  (sets the harness sys.path)
import r64_g4_closed_loop as r64  # noqa: E402

LEGS = ("FL", "FR", "RL", "RR")
DIAG = {0: 3, 3: 0, 1: 2, 2: 1}
N_TWIST = np.array([0.476, -0.476, -0.523, 0.523])
V_MAX = 0.020924
T3_S = 0.82
"""3-point diagonal rocking period, top (spec 62); used for bottom too (ASSUMPTION)."""
PRE_S = 0.5
MIN_AFTER_S = 12.0
MAX_AFTER_S = 60.0
READY_HOLD_S = 3.0
EVENTS = {
    "G4": {"depth": 0.0115, "ramp": 2.0},
    "RE1bF": {"depth": 0.030, "ramp": 0.05},
    "FS24": {"depth": 0.024, "ramp": 0.3},
}
LEVELS = ("top", "bottom")
FS_KN = (0.0, 8.0)
TIMINGS = ("ready", "level")
PS7 = {"ref": (None, 0.0), "PS7a_RR": (3, 2.0), "PS7a_FL": (0, 2.0), "PS7b_RR": (3, -1.5), "PS7c_RR": (3, -2.7)}
PS7_SETTLE_S = 20.0
F_MIN_N = 9414.6
CANDIDATE_ENV = "R67_CANDIDATE"
"""Spec 427.11 / 429.5: s9_slope_fix_candidates candidate name (unset = the project C2)."""


def set_affinity_from_env() -> None:
    mask = os.environ.get("R67_AFFINITY")
    if not mask or sys.platform != "win32":
        return
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    k32.SetProcessAffinityMask(k32.GetCurrentProcess(), int(mask, 16))


def is_fast(ev: dict) -> bool:
    return ev["depth"] / ev["ramp"] > V_MAX


# --- plant / controller --------------------------------------------------------------------------------------------

TOUCH_CAP_EXCESS_N = np.array([8000.0, 8000.0, 6666.4, 6666.4])
"""Candidate P-S8-26 (harness subclass only, ASSUMPTION): the largest free-air excess over m_rod g a moving airborne
leg can read = the seal friction F_s at the sensitivity upper value 8 kN (rear 0.833 x)."""


def make_controller_class(c2):
    class CapController(c2.C2Controller):
        """Project C2; ``touch_cap`` True caps the TOUCH free-air reference at m_rod g + F_s,max (candidate)."""

        touch_cap = False

        def _touchdown_load_from_moving_samples_N(self, reading):
            load = super()._touchdown_load_from_moving_samples_N(reading)
            if not self.touch_cap:
                return load
            st = self._state
            rod_weight = self._touch_rod_weight_N()
            free_air = np.asarray(st.free_air_force_N, float)
            cap = rod_weight + TOUCH_CAP_EXCESS_N
            out = np.array(load, float)
            for leg in range(4):
                if np.isfinite(free_air[leg]) and free_air[leg] > cap[leg]:
                    out[leg] = float(reading.cylinder_force_N[leg]) - cap[leg] - rod_weight[leg]
                    self.cap_used = getattr(self, "cap_used", set()) | {leg}
            return out

    return CapController


def make_base(cl, c2, level, fs_kN, zero_cal=False, pre=None, touch_cap=False):
    """Plant settled on the crawler (+ optional pre-extension of one leg), armed, and a fresh controller."""
    base = r51._reg_base("b", level, (0.0, 0.0), fs_kN, [])
    plant = r51.make_plant(cl, base)
    plant.step(np.zeros(4), int(round(cl.rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
    gaps0 = r51.pad_gaps(cl, plant)
    info = {"g0_mm": (gaps0 * 1e3).round(3).tolist()}
    if pre is not None and pre[0] is not None:
        leg, delta_mm = pre
        target = float(gaps0[leg]) + delta_mm * 1e-3
        u = np.zeros(4)
        u[leg] = V_MAX
        n = 0
        while float(plant.sref[leg]) < target - 1e-12 and n < 100000:
            plant.step(u, 1)
            n += 1
        plant.sref[leg] = target
        plant.step(np.zeros(4), int(round(PS7_SETTLE_S / plant.dt)))
        info.update(pre_leg=LEGS[leg], pre_delta_mm=delta_mm, pre_target_mm=round(target * 1e3, 3),
                    pre_contact_N=round(float(np.asarray(plant.acc[11:15])[leg]), 1),
                    pre_gap_mm=(r51.pad_gaps(cl, plant) * 1e3).round(3).tolist())
    plant.t = 0.0
    plant.arm()
    cfg = cl.preset_config(c2.ContactJudge.COMBINED, with_imu_samples=True, with_reapproach=True)
    if zero_cal:
        from outrigger_sim.control.zero_calibration import ZeroCalibrationMode
        cfg = dataclasses.replace(cfg, zero_calibration=dataclasses.replace(
            cfg.zero_calibration, mode=ZeroCalibrationMode.AIRBORNE_ROUNDTRIP))
    if touch_cap:
        ctrl = make_controller_class(c2).from_params(cl.PARAMS, cfg)
        ctrl.touch_cap = True
    else:
        ctrl = c2.C2Controller.from_params(cl.PARAMS, cfg)
    ctrl.reset()
    return plant, ctrl, info


def step_period(cl, Meas, plant, ctrl, cmd, valve, ha, floor_fn=None, rec=None):
    m = r64.with_two_pressures(plant, r51.control_period(cl, Meas, plant, cmd, valve, ha, ctrl.period_s,
                                                         floor_fn, rec), ha)
    return np.array(ctrl.update(m).leg_speed_m_s)


def run_base(cl, c2, Meas, plant, ctrl, stop_t=None, rec=None, crawler=None, log=None, hasher=None):
    """Run from the start; returns the timeline and the state at ``stop_t`` (or READY + 5 s).

    ``hasher`` (hashlib object, optional): updated with every command (spec 427.11 hash record)."""
    ha = ctrl.geometry.head_area_m2
    cmd, valve = np.zeros(4), np.zeros(4)
    tl, last = [], None
    t_lift = t_loc = t_ready = None

    def hook(pl_):
        if crawler is not None:
            crawler.append(float(pl_.acc[15]))

    while plant.t < r51.BASE_LIMIT_S:
        if stop_t is not None and plant.t >= stop_t - 1e-9:
            break
        cmd = step_period(cl, Meas, plant, ctrl, cmd, valve, ha, hook if crawler is not None else None, rec)
        if hasher is not None:
            hasher.update(cmd.tobytes())
        ph = str(ctrl.phase)
        if log is not None:
            log.append((float(plant.t), ph, np.asarray(plant.sref, float).copy(), cmd.copy(),
                        np.degrees(plant.attitude()), float(plant.acc[15]), np.asarray(plant.acc[11:15], float).copy(),
                        np.array(ctrl._state.touched, bool)))
        if ph != last:
            tl.append((round(plant.t, 3), ph))
            last = ph
        if t_lift is None and plant.acc[15] == 0.0 and ph == "level":
            t_lift = plant.t
        if t_loc is None and ctrl._is_liftoff_confirmed():
            t_loc = plant.t
        if ph == "ready" and t_ready is None:
            t_ready = plant.t
        if stop_t is None and t_ready is not None and plant.t >= t_ready + 5.0 - 1e-9:
            break
    t_done = next((t for t, p in tl if p == "done"), None)
    return {"timeline": tl, "t_lift": t_lift, "t_loc": t_loc, "t_done": t_done, "t_ready": t_ready,
            "cmd": cmd, "valve": valve}


# --- branch --------------------------------------------------------------------------------------------------------

def branch(cl, Meas, plant, ctrl, cmd, valve, ev, leg, t_ev, hasher=None):
    """One event branch; ``hasher`` (optional) is updated with every command."""
    ha = ctrl.geometry.head_area_m2
    rec, phases, crawler = [], [], []
    n0 = len(ctrl.events)

    def floor_fn(pl_):
        crawler.append(float(pl_.acc[15]))
        if ev is None:
            return
        tau = min(1.0, max(0.0, (pl_.t - t_ev) / ev["ramp"]))
        pl_.goff[leg] = ev["depth"] * (tau ** 3 * (10 - 15 * tau + 6 * tau ** 2))

    t_ready_back = None
    ready_since = None
    left_ready = False
    while plant.t < t_ev + MAX_AFTER_S - 1e-9:
        cmd = step_period(cl, Meas, plant, ctrl, cmd, valve, ha, floor_fn, rec)
        if hasher is not None:
            hasher.update(cmd.tobytes())
        ph = str(ctrl.phase)
        phases.append((round(plant.t - t_ev, 3), ph))
        if plant.t > t_ev:
            if ph != "ready":
                left_ready = True
                ready_since = None
            elif ready_since is None:
                ready_since = plant.t
                if t_ready_back is None and left_ready:
                    t_ready_back = plant.t
        if (plant.t >= t_ev + MIN_AFTER_S - 1e-9 and ready_since is not None
                and plant.t - ready_since >= READY_HOLD_S - 1e-9):
            break
    events = [(round(e.t_s - t_ev, 3), e.name) for e in ctrl.events[n0:]]
    return np.array(rec), phases, events, np.array(crawler), t_ready_back, ctrl


def _intervals(mask, t):
    return r51._intervals(mask, t)


def twist_work(t, F, valve, t0=0.0):
    D = (F[:, 0] + F[:, 3]) - (F[:, 1] + F[:, 2])
    m0 = (t >= t0 - 0.5) & (t < t0)
    D0 = float(np.median(D[m0])) if m0.any() else float(D[0])
    P = 0.5 * (D - D0) * (valve @ N_TWIST)
    bins = []
    for lo in np.arange(0.0, 8.0, 0.5):
        m = (t >= lo) & (t < lo + 0.5)
        bins.append(round(float(P[m].sum() * 1e-3), 1))
    judged = bins[3:]
    bundles, cur = [], None
    for k, w in enumerate(judged):
        if w > 20.0:
            if cur is None:
                cur = [1.5 + 0.5 * k, 0.0]
            cur[1] += w
        elif cur is not None:
            bundles.append(cur)
            cur = None
    if cur is not None:
        bundles.append(cur)
    return {"bins_J": bins, "bundles": [(b[0], round(b[1], 1)) for b in bundles], "n_bundles": len(bundles),
            "max_judged_bin_J": max(judged) if judged else 0.0, "D0_kN": round(D0 / 1e3, 2)}


def judge_event(rec, phases, events, crawler, t_ev, t_ready_back, ev, leg, ctrl, att0):
    t = rec[:, 0] - t_ev
    contact, F, valve, gap, att = rec[:, 1:5], rec[:, 5:9], rec[:, 9:13], rec[:, 13:17], rec[:, 17:19]
    lifted = contact <= 0.0
    after = t >= 0.0
    out = {"run_after_s": round(float(t[-1]), 2)}
    lifts = {}
    for i in range(4):
        iv = _intervals(after & lifted[:, i], t)
        if iv:
            lifts[LEGS[i]] = {"sum_s": round(sum(b - a for a, b in iv), 3), "n": len(iv),
                              "first_s": round(iv[0][0], 3), "last_touch_s": round(iv[-1][1], 3),
                              "max_gap_mm": round(float(gap[after & lifted[:, i], i].max() * 1e3), 2)}
    out["lifts"] = lifts
    pair = [leg, DIAG[leg]]
    adj = [i for i in range(4) if i not in pair]
    up = _intervals(after & lifted[:, pair].any(axis=1), t)
    pu = round(sum(b - a for a, b in up), 3)
    plast = round(up[-1][1], 3) if up else 0.0
    w_end = min(plast + T3_S, 5.0) if up else min(T3_S, 5.0)
    inW = after & (t <= w_end)
    adj_sum = float((inW[:, None] & lifted[:, adj]).sum() * 1e-3)
    adj_gap = max((float(gap[inW & lifted[:, i], i].max()) if (inW & lifted[:, i]).any() else 0.0) for i in adj)
    adj_out = float(((t > w_end)[:, None] & lifted[:, adj]).sum() * 1e-3)
    post = t > w_end
    fmin_post = F[post].min(axis=0) if post.any() else np.full(4, np.nan)
    fmin_after = F[after].min(axis=0)
    fmin_adj_W = F[inW][:, adj].min(axis=0) if inW.any() else np.full(2, np.nan)
    phs = [p for _, p in phases]
    n_fault = sum(1 for p in phs if p in ("fault", "fault_reground"))
    fault_events = [n for _, n in events if n.startswith("FAULT")]
    tail = t >= t[-1] - 1.0
    att_end = att[tail].mean(axis=0)
    out.update({
        "pair": [LEGS[i] for i in pair], "pair_union_s": pu, "pair_last_touch_s": plast, "W_end_s": round(w_end, 3),
        "adj_lift_sum_W_s": round(adj_sum, 3), "adj_max_gap_W_mm": round(adj_gap * 1e3, 3),
        "adj_lift_outside_W_s": round(adj_out, 3),
        "adj_min_F_in_W_kN": {LEGS[i]: round(float(v) / 1e3, 2) for i, v in zip(adj, fmin_adj_W)},
        "min_F_after_W_kN": {LEGS[i]: round(float(fmin_post[i]) / 1e3, 2) for i in range(4)},
        "min_F_after_event_kN": {LEGS[i]: round(float(fmin_after[i]) / 1e3, 2) for i in range(4)},
        "fault_periods": n_fault, "fault_events": fault_events,
        "final_phase": phs[-1] if phs else None, "t_ready_back_s": None if t_ready_back is None
        else round(t_ready_back - t_ev, 2),
        "att_end_deg": [round(float(a), 4) for a in att_end],
        "max_att_change_deg": round(float(np.abs(att[after] - att0).max()), 4),
        "crawler_contact_after_event_ms": int(np.sum(np.asarray(crawler)[-len(t):][after] > 0.0))
        if len(crawler) >= len(t) else None,
    })
    starts = [(round(tt, 2), n.split(":")[1]) for tt, n in events if n.startswith("leg_reapproach_start")]
    signs = [int(np.sign(N_TWIST[LEGS.index(lg)])) for _, lg in starts]
    out["reapproach_starts"] = starts
    out["n_late_starts"] = sum(1 for s, _ in starts if s > 1.5)
    out["sign_changes"] = int(sum(1 for a, b in zip(signs, signs[1:]) if a != b))
    out["twist"] = twist_work(t, F, valve)
    out["warnings"] = sorted({n for _, n in events if n.startswith(("WARN", "FAULT", "INFO_ROD_PRESSURE_FAULT", "INFO_HEAD_PRESSURE_FAULT"))})
    # verdicts
    end_ok = bool(out["final_phase"] == "ready" and np.all(np.abs(att_end) <= 0.2))
    rec_ok = out["twist"]["n_bundles"] <= 1
    if is_fast(ev):
        g = {"U832_pair_union": pu <= 1.8, "U832_last_touch": plast <= 3.0, "fault0": n_fault == 0,
             "U57_sum": adj_sum <= 0.5, "U57_gap": adj_gap <= 2e-3, "U57_outside": adj_out == 0.0,
             "Fmin_after_W": bool(np.nanmin(fmin_post) >= F_MIN_N), "end_att": end_ok, "recurrence": rec_ok}
    else:
        g = {"no_lift": not lifts, "Fmin_after_event": bool(fmin_after.min() >= F_MIN_N), "fault0": n_fault == 0,
             "end_att": end_ok, "recurrence": rec_ok}
    out["gates"] = g
    out["pass"] = bool(all(g.values()))
    out["margins"] = {"pair_union_to_1.8_s": round(1.8 - pu, 3), "last_touch_to_3.0_s": round(3.0 - plast, 3),
                      "adj_sum_to_0.5_s": round(0.5 - adj_sum, 3),
                      "Fmin_after_W_minus_Fmin_kN": round((float(np.nanmin(fmin_post)) - F_MIN_N) / 1e3, 2),
                      "Fmin_after_event_minus_Fmin_kN": round((float(fmin_after.min()) - F_MIN_N) / 1e3, 2)}
    return out


# --- jobs ----------------------------------------------------------------------------------------------------------

def screen_job(key):
    _, level, fs, timing, leg_name = key.split("|")
    fs = float(fs)
    leg = LEGS.index(leg_name)
    r51.place_worker()
    cl, c2, Meas = r51._imports()
    cl.rmf.CONFIG.clear()
    cl.rpt.RCFG.clear()
    t0 = time.perf_counter()
    plant, ctrl, info = make_base(cl, c2, level, fs)
    tl = run_base(cl, c2, Meas, copy.deepcopy(plant), copy.deepcopy(ctrl))
    res = {"key": key, "level": level, "fs_kN": fs, "timing": timing, "leg": leg_name, "base": {
        k: tl[k] for k in ("timeline", "t_lift", "t_loc", "t_done", "t_ready")}, "runs": []}
    if tl["t_ready"] is None or tl["t_loc"] is None or tl["t_done"] is None:
        res["error"] = "base without LOC / DONE / READY"
        return res
    t_target = (tl["t_ready"] + 5.0) if timing == "ready" else tl["t_loc"] + 0.5 * (tl["t_done"] - tl["t_loc"])
    prefix_hasher = hashlib.sha256()
    st = run_base(cl, c2, Meas, plant, ctrl, stop_t=t_target - PRE_S, hasher=prefix_hasher)
    res["prefix_commands_sha256"] = prefix_hasher.hexdigest()
    t_b = plant.t
    res["branch_t_s"] = round(t_b, 3)
    res["branch_phase"] = str(ctrl.phase)
    offs = tuple(float(x) for x in os.environ.get("R67_OFFSETS", "0,0.05").split(","))
    for ev_id, ev in EVENTS.items():
        for off in offs:
            pl, ct = copy.deepcopy(plant), copy.deepcopy(ctrl)
            t_ev = t_b + PRE_S + off
            att0 = np.degrees(pl.attitude())
            run_hasher = prefix_hasher.copy()  # prefix + branch commands
            rec, phases, events, crawler, t_rb, ct = branch(cl, Meas, pl, ct, st["cmd"].copy(), st["valve"].copy(),
                                                            ev, leg, t_ev, hasher=run_hasher)
            ph_at_ev = next((p for tt, p in phases if tt >= 0.0), None)
            j = judge_event(rec, phases, events, crawler, t_ev, t_rb, ev, leg, ct, att0)
            j.update({"event": ev_id, "offset_s": off, "phase_at_event": ph_at_ev, "t_ev_s": round(t_ev, 3),
                      "fast": is_fast(ev), "commands_sha256": run_hasher.hexdigest()})
            candidate_record = _candidate_record(ct)
            if candidate_record is not None:  # spec 427.11: only with R67_CANDIDATE
                j["candidate_record"] = candidate_record
            res["runs"].append(j)
    res["wall_s"] = round(time.perf_counter() - t0, 1)
    return res


def ps7_job(key):
    _, case, level, fs, var = key.split("|")
    fs = float(fs)
    r51.place_worker()
    cl, c2, Meas = r51._imports()
    cl.rmf.CONFIG.clear()
    cl.rpt.RCFG.clear()
    t0 = time.perf_counter()
    plant, ctrl, info = make_base(cl, c2, level, fs, zero_cal=(var == "cal"), pre=PS7[case],
                                  touch_cap=(var == "cap"))
    rec, crawler, log = [], [], []
    tl = run_base(cl, c2, Meas, plant, ctrl, rec=rec, crawler=crawler, log=log)
    rec = np.array(rec)
    t = rec[:, 0]
    contact, F, att = rec[:, 1:5], rec[:, 5:9], rec[:, 17:19]
    res = {"key": key, "case": case, "level": level, "fs_kN": fs, "variant": var, "info": info,
           "timeline": tl["timeline"], "t_lift": tl["t_lift"], "t_loc": tl["t_loc"], "t_ready": tl["t_ready"]}
    import hashlib
    res["cmd_sha256"] = hashlib.sha256(np.array([q[3] for q in log]).tobytes()).hexdigest()[:16]
    res["cap_used_legs"] = sorted(LEGS[i] for i in getattr(ctrl, "cap_used", set()))
    # TOUCH record: duration, latch time per leg, stroke at the end, max |attitude|, crawler load, max leg contact
    tt = np.array([q[0] for q in log])
    is_touch = np.array([q[1] == "touch" for q in log])
    if is_touch.any():
        k_end = int(np.flatnonzero(is_touch)[-1])
        latched = np.array([q[7] for q in log])
        lat_t = {LEGS[i]: (round(float(tt[np.flatnonzero(latched[:, i])[0]]), 2) if latched[:, i].any() else None)
                 for i in range(4)}
        atts = np.array([q[4] for q in log])[is_touch]
        res["touch"] = {
            "start_s": round(float(tt[is_touch][0]), 2), "end_s": round(float(tt[k_end]), 2),
            "duration_s": round(float(tt[k_end] - tt[is_touch][0]), 2), "latch_s": lat_t,
            "stroke_at_end_mm": (log[k_end][2] * 1e3).round(1).tolist(),
            "stroke_at_start_mm": (log[int(np.flatnonzero(is_touch)[0])][2] * 1e3).round(1).tolist(),
            "max_abs_att_deg": np.abs(atts).max(axis=0).round(3).tolist(),
            "att_at_end_deg": np.round(log[k_end][4], 3).tolist(),
            "min_crawler_kN": round(min(q[5] for q, m in zip(log, is_touch) if m) / 1e3, 1),
            "max_contact_kN": (np.array([q[6] for q, m in zip(log, is_touch) if m]).max(axis=0) / 1e3).round(1).tolist()}
    if tl["t_lift"] is not None:
        w = t >= tl["t_lift"]
        mins = F[w].min(axis=0)
        lifts = {LEGS[i]: round(float((w & (contact[:, i] <= 0)).sum() * 1e-3), 3) for i in range(4)}
        att_end = att[t >= t[-1] - 1.0].mean(axis=0)
        res.update({"min_F_after_liftoff_kN": {LEGS[i]: round(float(mins[i]) / 1e3, 2) for i in range(4)},
                    "lift_after_liftoff_s": lifts, "att_end_deg": [round(float(a), 4) for a in att_end]})
        g = {"Fmin_plus5": bool(mins.min() >= F_MIN_N + 5e3), "no_lift": all(v == 0 for v in lifts.values()),
             "end_att": bool(np.all(np.abs(att_end) <= 0.2)), "ready": tl["t_ready"] is not None}
        res["gates"] = g
        res["pass"] = bool(all(g.values()))
    # start of the run: per-leg contact force and true force at t = 0.1 s and at TOUCH end
    k1 = int(np.searchsorted(t, 0.1))
    res["contact_at_0.1s_kN"] = {LEGS[i]: round(float(contact[k1, i]) / 1e3, 2) for i in range(4)}
    res["events"] = [(round(e.t_s, 2), e.name) for e in ctrl.events if not e.name.startswith(("INFO_PRESSURE", "shadow"))][:80]
    meta = ctrl.meta()
    zc = meta.get("zero_calibration") if isinstance(meta, dict) else None
    res["zero_calibration_meta"] = json.loads(json.dumps(zc, default=str)) if zc is not None else None
    res["stroke_end_mm"] = (np.asarray(plant.sref) * 1e3).round(2).tolist()
    res["wall_s"] = round(time.perf_counter() - t0, 1)
    return res


def _candidate_name():
    name = os.environ.get(CANDIDATE_ENV, "")
    return None if name in ("", "current") else name


def _candidate_record(ctrl):
    if _candidate_name() is None:
        return None
    import s9_slope_fix_candidates as fx
    return fx.screen_candidate_record(ctrl)


def _install_candidate():
    """Spec 427.11 / 429.5: the ``R67_CANDIDATE`` wrapper candidate in place of the project C2 (every
    controller is built through ``c2.C2Controller``); returns the restore function. Unset / "current": nothing."""
    name = _candidate_name()
    if name is None:
        return lambda: None
    s9_dir = ROOT / "04_scripts" / "03_control" / "s9"
    if str(s9_dir) not in sys.path:
        sys.path.insert(0, str(s9_dir))
    import s9_slope_fix_candidates as fx
    return fx.install_screen_candidate(name)


def run_job(key):
    try:
        restore = _install_candidate()
        try:
            out = screen_job(key) if key.startswith("screen|") else ps7_job(key)
        finally:
            restore()
        out["candidate"] = _candidate_name() or "current"
        return out
    except Exception as exc:  # keep the batch going; the error is reported
        import traceback
        return {"key": key, "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()[-2000:]}


def all_jobs(mode):
    jobs = []
    if mode in ("screen", "all"):
        jobs += [f"screen|{lv}|{fs}|{tm}|{lg}" for lv in LEVELS for fs in FS_KN for tm in TIMINGS for lg in LEGS]
    if mode in ("ps7", "all"):
        jobs += [f"ps7|{c}|{lv}|{fs}|{cal}" for c in PS7 for lv in LEVELS for fs in FS_KN for cal in ("proj", "cap")]
    return jobs


def main():
    set_affinity_from_env()
    out = Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    jobs = all_jobs(os.environ.get("R67_MODE", "all"))
    filt = os.environ.get("R67_FILTER")
    if filt:
        jobs = [j for j in jobs if any(f in j for f in filt.split(","))]
    # long jobs first (LEVEL screens run longest), then slice
    jobs.sort(key=lambda k: (0 if "|level|" in k else 1 if k.startswith("screen") else 2, k))
    sl = os.environ.get("R67_SLICE")
    if sl:
        a, b = (float(x) for x in sl.split(":"))
        n = len(jobs)
        idx = [k for k in range(n) if a <= (k + 0.5) / n < b]
        jobs = [jobs[k] for k in idx]
    t0 = time.perf_counter()
    with Pool(max(1, min(workers, len(jobs)))) as pool:
        res = pool.map(run_job, jobs, chunksize=1)
    out.write_text(json.dumps({"meta": {"script": "04_scripts/03_control/s8/r67_g1_screen.py",
                                        "spec": "rev. 67 (G1 / G2 / G7 reduced screen)",
                                        "wall_s": round(time.perf_counter() - t0, 1), "workers": workers,
                                        "affinity": os.environ.get("R67_AFFINITY"), "slice": sl,
                                        "offsets_s": os.environ.get("R67_OFFSETS", "0,0.05"), "n_jobs": len(jobs),
                                        "candidate": _candidate_name() or "current"},
                               "results": res}, indent=1, default=float), encoding="utf-8")
    print("done", round(time.perf_counter() - t0, 1), "s ->", out)


if __name__ == "__main__":
    main()
