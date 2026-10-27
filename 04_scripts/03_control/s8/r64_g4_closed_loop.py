"""Spec rev. 64 323.8 step 2 / P-S8-24 T8: FAULT_REGROUND (G4) on the reduced closed loop.

Harness: the r51_reapp_closed_loop.py plant and loop (imported, not copied): reduced 6-DoF FlexPlant (rigid mast)
+ L1-R rod-side law, Coulomb seal friction, valve lag 0.1 s, IMU 10 ms samples, damping switch, the project C2
(03_src, read only) with c2py_r8d1_closed_loop.preset_config(COMBINED) = with_10hz_d1 (FAULT_REGROUND on, soil
response on, D1'' YAML mass before READY, re-contact watch on) minus CHECK / zero calibration / REANCHOR / target
check; ideal sensors, no rod-side sensor (so cue (b) cannot fire here).

Head-sensor fault: a lasting +150 bar jump on one leg's head reading, armed at event + t_f; the controller takes it at
its first 10 Hz sample at or after the arm time (as cad C-S8-68 run_S8C.py G4H_*).

Cases (6) x event start phase offsets 0 / 25 / 50 / 75 ms = 24 runs; branch from READY + 5 s (deepcopy):
  FS24_FR_Fs0 / _Fs8   flat top, FR floor 24 mm / 0.3 s, FR head fault in the middle of the first RL lift
                       interval of the same run without fault (healthy-sensor target expected)
  FS24_RL_Fs0 / _Fs8   same event, RL head fault at the same time (faulty-sensor target expected)
  quiet_FR_Fs0         flat top, no floor event, FR head fault at event + 0.05 s (no target: G4-7)
  G4_RR_Fs4            flat top, RR 11.5 mm / 2 s, RR head fault at event + 2.05 s (false target recorded)
Each case also runs without fault (lift times) and with the fault but FAULT_REGROUND off (the old FAULT).

Two paths:
  (i)  the project controller in the closed loop (meta fault_reground.run: targets, start / end times, end reason);
  (ii) an independent re-implementation of the 323.2-323.6 (+323.9 (4)) state machine in this file, fed by the
       per-period inputs the controller records (lower load estimates, nominal readings, f_z, strokes, raw tilt,
       plane residual, head forces). The inputs are shared, the decision logic is not. Compared: targets and order,
       per-target start / end time and outcome, FAULT time, end reason.
Truth judgement (1 ms plant record): G4-1 .. G4-8 of spec 323.7 with the 323.9 corrections (true target = airborne
at >= 2 of the 3 controller sample times t_f - 0.2, t_f - 0.1, t_f, airborne = 20 ms mean pad contact <= 0; G4-4 =
min true cylinder force over [FAULT + 1 s, end] >= F_min with >= 3 s of window; G4-5 healthy legs no < F_min stretch
over 0.5 s, faulty leg max <= extension force limit, true head <= 345 bar; G4-6 0.5 s moving-mean attitude change
against the [t_f - 0.5, t_f] mean <= 0.5 deg; G4-7 bit-identical commands with FAULT_REGROUND off when no target).
Also: faulty-target contact detection time against the true force crossing F_min + 5 kN.

Run (dynamics-dev): python -I r64_g4_closed_loop.py <project_root> <out_json> [workers]
Env R64_AFFINITY = hex mask set on the parent before the pool (inherited by the workers). Deterministic.
"""
from __future__ import annotations

import copy
import ctypes
import dataclasses
import json
import math
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

HEAD_JUMP_PA = 150e5
EVENT_DELAY_S = 5.0
RUN_AFTER_EVENT_S = 22.0
OFFSETS = (0.0, 0.025, 0.05, 0.075)
LEGS = ("FL", "FR", "RL", "RR")
HEAD_LIMIT_PA = 345e5
EXT_FORCE_LIMIT_N = np.array([278.7e3, 278.7e3, 199.6e3, 199.6e3])
"""CLAUDE.md / YAML legs.<leg>.cylinder: 210 bar extension force limit, front / rear."""
A_P = np.array([1.3273e-2, 1.3273e-2, 9.503e-3, 9.503e-3])
"""Head areas [m^2] (spec 219.2) for the true head pressure F / A_p."""
FS24 = {"id": "FS24", "leg": 1, "depth": 0.024, "ramp": 0.3}
G4 = {"id": "G4", "leg": 3, "depth": 0.0115, "ramp": 2.0}
CASES = [
    {"id": "FS24_FR_Fs0", "base": "flat_Fs0", "event": FS24, "fault_leg": 1, "fault": "rl_mid"},
    {"id": "FS24_FR_Fs8", "base": "flat_Fs8", "event": FS24, "fault_leg": 1, "fault": "rl_mid"},
    {"id": "FS24_RL_Fs0", "base": "flat_Fs0", "event": FS24, "fault_leg": 2, "fault": "rl_mid"},
    {"id": "FS24_RL_Fs8", "base": "flat_Fs8", "event": FS24, "fault_leg": 2, "fault": "rl_mid"},
    {"id": "quiet_FR_Fs0", "base": "flat_Fs0", "event": None, "fault_leg": 1, "fault": 0.05},
    {"id": "G4_RR_Fs4", "base": "flat_Fs4", "event": G4, "fault_leg": 3, "fault": 2.05},
]
BASES = {"flat_Fs0": 0.0, "flat_Fs4": 4.0, "flat_Fs8": 8.0}
FS24_FALLBACK_FAULT_S = 0.465
"""cad C-S8-68 value (Chrono MLJ RL first lift middle), used only if the harness run shows no RL lift."""
TOL = 1e-6


def set_affinity_from_env() -> None:
    mask = os.environ.get("R64_AFFINITY")
    if not mask or sys.platform != "win32":
        return
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    k32.SetProcessAffinityMask(k32.GetCurrentProcess(), int(mask, 16))


VARIANT_NAMES = tuple(os.environ.get(
    "R64_VARIANTS", "py,off2,off2+all4,off2+all4+hold,off2+all4+hold+cued,off2+all4+hold+cued+susp").split(","))
"""FAULT_REGROUND candidates by subclass (no 03_src change); a name is '+'-joined tokens:
  py    the implementation as it is (abort 2 = 0.5 s mean of the raw accelerometer tilt against its
        [t_f - 0.5, t_f] mean, 0.5 deg; contact 323.4)
  filt  abort 2 on the levelling attitude estimate (2nd-order low-pass tau 0.8 s x 2) against its value at t_f
  off2  no attitude abort (travel limit, contact, aborts 1 / 3-5 only)
  all4  contact = the target's own 323.4 level AND every other healthy leg's lower load estimate >= F_min AND (a
        faulty leg that is not the target) its Newton estimate >= F_min, 3 samples in a row (a passive touch-down
        of a teetering diagonal, whose partner lifts, does not count)
  hold  the leg stops while the contact condition holds and moves on when it breaks; contact is confirmed after
        HOLD_CONFIRM_SAMPLES samples in a row (1.0 s, longer than one teeter period)
  cued  faulty-leg cue (d): its own lower load estimate < 0 N on the two samples before the fault sample (the
        readings before the jump are valid; no mass bias)
  susp  the D1 step rule is suspended on every leg once FAULT_REGROUND starts (max_step_Pa raised): with one leg
        frozen the step explanation cannot be judged (a teeter moves the frozen leg's load)"""
HOLD_CONFIRM_SAMPLES = 10


def make_controller_class(c2):
    from outrigger_sim.control import fault_reground as fr

    class G4Controller(c2.C2Controller):
        """Project C2 with the candidate tokens of ``abort2`` (instance attribute)."""

        abort2 = "py"

        def _tok(self, name):
            return name in self.abort2.split("+")

        def _mean_reground_tilt_rad(self):
            if self._tok("filt"):
                st = self._state
                return float(st.roll_rad), float(st.pitch_rad)
            return super()._mean_reground_tilt_rad()

        def _has_reground_attitude_moved(self, run):
            if self._tok("off2"):
                return False
            return super()._has_reground_attitude_moved(run)

        def _starts_fault_reground(self, t_s, fault_legs):
            started = super()._starts_fault_reground(t_s, fault_legs)
            if started and self._tok("susp"):
                mon = self._pressures
                mon.refresh_settings(dataclasses.replace(mon.settings, max_step_Pa=1e12))
            return started

        def _faulty_leg_cues(self, window, leg, residuals_m):
            cues, values = super()._faulty_leg_cues(window, leg, residuals_m)
            if self._tok("cued"):
                hist = list(self._state.fault_reground_history)
                before = hist[-3:-1]
                own = [float(q.load_estimate_N[leg]) for q in before]
                values["own_pre_fault_N"] = own
                if len(before) == 2 and all(v < 0.0 for v in own) and "own_pre_fault" not in cues:
                    cues = tuple(cues) + ("own_pre_fault",)
            return cues, values

        def _all4(self, reading, target):
            settings = self.config.fault_reground
            run = self._state.fault_reground
            f_min = self.geometry.F_min_N
            level = f_min + settings.contact_margin_N
            window = self._faulty_contact_window()
            loads = self._load_estimate_N(reading.cylinder_force_lower_N)
            if target.is_faulty:
                at = target.start_other_sum_N - fr.other_legs_mean_sum_N(window, target.leg) >= level
            else:
                at = loads[target.leg] >= level
            ok = all(loads[i] >= f_min for i in range(4) if i != target.leg and i not in run.fault_legs)
            mass = self._pressures.d1_imu_mass_kg()
            for f in run.fault_legs:
                if f != target.leg and mass is not None:
                    newton = fr.newton_leg_load_N(window, f, mass)
                    ok &= newton is None or newton >= f_min
            return bool(at and ok)

        def _has_reground_contact(self, reading, target):
            if not self._tok("all4"):
                return super()._has_reground_contact(reading, target)
            is_at = self._all4(reading, target)
            target.contact_samples_seen = target.contact_samples_seen + 1 if is_at else 0
            need = HOLD_CONFIRM_SAMPLES if self._tok("hold") else self.config.fault_reground.healthy_contact_samples
            return target.contact_samples_seen >= need

        def _drive_reground_target(self, reading, target):
            speeds = super()._drive_reground_target(reading, target)
            if self._tok("hold") and self._state.fault_reground.active_target is target \
                    and target.contact_samples_seen >= 1:
                speeds = self._zero_speeds()  # hold while the contact condition is being confirmed
            return speeds

    return G4Controller


# --- closed loop -------------------------------------------------------------------------------------------------

def with_two_pressures(plant, m, ha):
    """Head and rod readings from the harness net oil force (the r51 loop gives net / A_p as 'head').

    The L1-R rod-side law of the plant (s8_g4_rodside_check.RodSidePlant) adds Gr to the net force; Gr is the rod
    chamber spring: Gr = (p_r0 - p_r) A_ann (Gr = 0 at the lock pressure p_r0, Gr at the knee = (p_r0 - p_floor)
    A_ann). So p_r = p_r0 - Gr / A_ann and p_h = (F_net + p_r A_ann) / A_p (gauge, net = p_h A_p - p_r A_ann).
    ASSUMPTION (harness only): while a leg moves, the rod reading is this decaying release value (no back pressure).
    """
    net = plant.pressure()
    p_r = np.asarray(plant.p_r0, float) - np.asarray(plant.Gr, float) / np.asarray(plant.A_ann, float)
    p_h = (net + p_r * plant.A_ann) / ha
    return dataclasses.replace(m, head_pressure_Pa=p_h, rod_pressure_Pa=p_r)


def snapshot(ctrl, cmd):
    """Per-period inputs of the independent path (recorded by the controller) and its decisions."""
    st = ctrl._state
    rd = st.last_reading
    hist = st.fault_reground_history
    h = hist[-1] if hist else None
    tilt = st.reground_tilt_history[-1] if st.reground_tilt_history else None
    resid = ctrl._support_shadow.leg_residual_changes_m()
    return {
        "t": float(rd.t_s),
        "phase": str(st.phase),
        "cmd": np.asarray(cmd, float).copy(),
        "load_est": None if h is None else np.asarray(h.load_estimate_N, float).copy(),
        "load_nom": None if h is None else np.asarray(h.load_reading_N, float).copy(),
        "fz": None if h is None else h.imu_f_z_m_s2,
        "stroke": np.asarray(rd.motor_stroke_m, float).copy(),
        "tilt": None if tilt is None else tuple(map(float, tilt)),
        "filt": (float(st.roll_rad), float(st.pitch_rad)),
        "resid": None if resid is None else np.asarray(resid, float).copy(),
        "head_force": np.asarray(rd.head_only_force_N, float).copy(),
        "mass": ctrl._pressures.d1_imu_mass_kg(),
        "crawler_lifted": bool(ctrl._is_crawler_lifted_for_d1()),
        "loc": bool(ctrl._is_liftoff_confirmed()),
        "head_fault": list(ctrl._pressures.head_fault_legs),
    }


def simulate(cl, Measurements, plant, ctrl, cmd, valve, ha, ev, off, fault_leg, fault_after_s, run_s):
    """One branch run; returns (1 ms record, per-period log, t_ev, events after the branch)."""
    t_ev = plant.t + off
    n0 = len(ctrl.events)
    rec, log = [], []

    def floor_fn(pl_):
        if ev is None:
            return
        tau = min(1.0, max(0.0, (pl_.t - t_ev) / ev["ramp"]))
        pl_.goff[ev["leg"]] = ev["depth"] * (tau ** 3 * (10 - 15 * tau + 6 * tau ** 2))

    while plant.t < t_ev + run_s - 1e-9:
        m = with_two_pressures(plant, r51.control_period(cl, Measurements, plant, cmd, valve, ha, ctrl.period_s,
                                                         floor_fn, rec), ha)
        if fault_leg is not None and m.t_s >= t_ev + fault_after_s - 1e-9:
            hp = np.array(m.head_pressure_Pa, dtype=float)
            hp[fault_leg] += HEAD_JUMP_PA
            m = dataclasses.replace(m, head_pressure_Pa=hp)
        cmd = np.array(ctrl.update(m).leg_speed_m_s)
        log.append(snapshot(ctrl, cmd))
    events = [(float(e.t_s), e.name) for e in ctrl.events[n0:]]
    return np.array(rec), log, t_ev, events


# --- independent state machine (spec 323.2-323.6, 323.9 (4)) ----------------------------------------------------

def shadow_run(log, k_f, s, geo, abort2="py"):
    """Re-implementation of FAULT_REGROUND from the per-period inputs; ``k_f`` = fault sample index."""
    period = 0.1
    f_min = geo["F_min"]
    fault_legs = log[k_f]["head_fault"]
    out = {"fault_s": log[k_f]["t"], "targets": [], "end_s": None, "end_reason": None}
    if len(fault_legs) != 1:
        out.update(end_s=log[k_f]["t"], end_reason="two_faults")
        return out
    j = fault_legs[0]
    win = log[max(0, k_f - round(s["target_window_s"] / period) + 1): k_f + 1]
    n_l = s["healthy_lifted_samples"]
    healthy = [i for i in range(4) if i != j]
    lifted = [i for i in healthy if k_f + 1 >= n_l
              and all(log[k]["load_est"][i] < s["healthy_lifted_level_N"] for k in range(k_f - n_l + 1, k_f + 1))]
    lifted.sort(key=lambda i: log[k_f]["load_est"][i])
    resid = log[k_f]["resid"]

    def target(i, faulty, cues):
        gap = float(resid[i]) if resid is not None and resid[i] > s["plane_residual_threshold_m"] else None
        lim = s["max_travel_m"] if gap is None else min(gap + s["travel_gap_margin_m"], s["max_travel_m"])
        return {"leg": i, "faulty": faulty, "cues": cues, "gap_m": gap, "max_travel_m": lim}

    targets = [target(i, False, ["lower_bound"]) for i in lifted]
    cues = []
    newton = None
    mass = log[k_f]["mass"]
    if mass is not None and log[k_f]["crawler_lifted"] and all(r["fz"] is not None for r in win):
        newton = mass * float(np.mean([r["fz"] for r in win])) - float(
            np.mean([np.sum(np.delete(r["load_nom"], j)) for r in win]))
        if newton < f_min:
            cues.append("newton")
    if resid is not None and resid[j] > s["plane_residual_threshold_m"]:
        cues.append("plane")
    if cues:
        targets.append(target(j, True, cues))
    out["newton_N"] = newton
    out["targets"] = targets
    if not targets:
        out.update(end_s=log[k_f]["t"], end_reason="no_target")
        return out
    protected = [i for i in healthy if i not in {t["leg"] for t in targets}]
    n_tilt = round(s["attitude_window_s"] / period)

    def att(k):
        if "filt" in abort2.split("+"):
            return np.array(log[k]["filt"])
        return np.mean([r["tilt"] for r in log[max(0, k - n_tilt + 1): k + 1]], axis=0)

    tilt0 = att(k_f)
    low = {i: 0 for i in protected}
    head_lim = geo["head_force_limit_N"]
    abort_stroke = geo["stroke_soft"] - 0.010 - s["stroke_end_abort_margin_m"]
    active, nxt = None, 0
    t_f = log[k_f]["t"]
    for k in range(k_f + 1, len(log)):
        r = log[k]
        t = r["t"]
        reason = None
        is_low = False
        for i in protected:
            low[i] = low[i] + 1 if r["load_est"][i] < f_min else 0
            is_low |= low[i] >= s["protect_samples"]
        tilt = att(k)
        if is_low:
            reason = "protected_leg_low"
        elif "off2" not in abort2.split("+") and np.max(np.abs(tilt - tilt0)) > s["attitude_abort_rad"]:
            reason = "attitude"
        elif set(r["head_fault"]) - {j}:
            reason = "new_head_fault"
        elif any(r["head_force"][i] > head_lim[i] for i in range(4) if i != j):
            reason = "pressure_warning"
        elif active is not None and r["stroke"][active["leg"]] >= abort_stroke:
            reason = "stroke_end"
        if reason is None and t - t_f >= s["max_total_duration_s"] - TOL:
            reason = "total_time"
        if reason is not None:
            if active is not None:
                active.update(end_s=t, outcome="time" if reason == "total_time" else "aborted",
                              travel_m=float(r["stroke"][active["leg"]] - active["start_stroke"]))
            out.update(end_s=t, end_reason=reason)
            return out
        if active is None:
            if nxt >= len(targets):
                out.update(end_s=t, end_reason="done")
                return out
            active = targets[nxt]
            nxt += 1
            active.update(start_s=t, start_stroke=float(r["stroke"][active["leg"]]), seen=0)
            if active["faulty"]:
                w2 = log[k - round(s["faulty_contact_window_s"] / period) + 1: k + 1]
                active["start_other"] = float(np.mean([np.sum(np.delete(q["load_nom"], j)) for q in w2]))
        i = active["leg"]
        level = f_min + s["contact_margin_N"]
        if active["faulty"]:
            w2 = log[k - round(s["faulty_contact_window_s"] / period) + 1: k + 1]
            now = float(np.mean([np.sum(np.delete(q["load_nom"], j)) for q in w2]))
            at = active["start_other"] - now >= level
            need = s["faulty_contact_samples"]
        else:
            at = r["load_est"][i] >= level
            need = s["healthy_contact_samples"]
        if "all4" in abort2.split("+"):
            need = s["healthy_contact_samples"]
            at &= all(r["load_est"][q] >= f_min for q in range(4) if q != i and q != j)
            if j != i and r["mass"] is not None:
                w2 = log[k - round(s["faulty_contact_window_s"] / period) + 1: k + 1]
                if all(q["fz"] is not None for q in w2):
                    newton_j = r["mass"] * float(np.mean([q["fz"] for q in w2])) - float(
                        np.mean([np.sum(np.delete(q["load_nom"], j)) for q in w2]))
                    at &= newton_j >= f_min
        active["seen"] = active["seen"] + 1 if at else 0
        travel = float(r["stroke"][i] - active["start_stroke"])
        outcome = None
        if active["seen"] >= need:
            outcome = "contact"
        elif travel >= active["max_travel_m"]:
            outcome = "travel"
        elif t - active["start_s"] >= s["max_leg_duration_s"] - TOL:
            outcome = "time"
        if outcome is not None:
            active.update(end_s=t, outcome=outcome, travel_m=travel)
            active = None
    out.update(end_reason="run_end")
    return out


# --- truth judgement ---------------------------------------------------------------------------------------------

def judge(rec, log, events, t_ev, fault_leg, fault_arm_s, meta_run, geo, s, cmds_off=None):
    t = rec[:, 0]
    contact, F, att = rec[:, 1:5], rec[:, 5:9], rec[:, 17:19]
    ts = np.array([r["t"] for r in log])
    phases = [r["phase"] for r in log]
    k_f = next((k for k, r in enumerate(log) if r["phase"] in ("fault_reground", "fault")), None)
    out = {"fault_arm_s": round(fault_arm_s, 4)}
    if k_f is None:
        out["error"] = "no fault entry"
        return out, None
    t_f = ts[k_f]
    k_fault = next(k for k in range(k_f, len(log)) if phases[k] == "fault")
    t_fault = ts[k_fault]
    out["t_f_rel_s"] = round(t_f - t_ev, 3)
    out["entry_phase"] = phases[k_f]
    out["t_fault_rel_s"] = round(t_fault - t_ev, 3)
    # G4-1
    ev_names = [n for tt, n in events if abs(tt - t_f) < TOL]
    out["G4_1"] = bool(abs(t_f - (t_ev + fault_arm_s)) < 0.1 + TOL and t_f >= t_ev + fault_arm_s - TOL
                       and any(n.startswith("FAULT_HEAD") for n in ev_names))
    out["G4_1_events"] = [n for n in ev_names if not n.startswith("INFO_")][:8]
    # G4-2 true targets
    airborne = {}
    for i in range(4):
        hits = 0
        for dt in (-0.2, -0.1, 0.0):
            m = (t > t_f + dt - 0.020 - 1e-9) & (t <= t_f + dt + 1e-9)
            hits += bool(contact[m, i].mean() <= 0.0)
        airborne[LEGS[i]] = hits
    true_targets = [l for l, h in airborne.items() if h >= 2]
    tg = [] if meta_run is None else [x["leg"] for x in meta_run["targets"]]
    out["airborne_hits"] = airborne
    out["true_targets"] = true_targets
    out["targets"] = tg
    out["G4_2_miss"] = [l for l in true_targets if l not in tg]
    out["G4_2_false"] = [l for l in tg if l not in true_targets]
    out["G4_2"] = not out["G4_2_miss"]
    wf = (t >= t_f - 0.2) & (t <= t_f + 0.2)
    out["airborne_ms_in_window"] = {LEGS[i]: int((contact[wf, i] <= 0).sum()) for i in range(4)}
    late = (t > t_f) & (t <= t_f + 0.5)
    out["late_airborne"] = [LEGS[i] for i in range(4)
                            if (contact[late, i] <= 0).sum() > 20 and LEGS[i] not in true_targets]
    # G4-3
    after = [k for k in range(k_fault + 1, len(log))]
    out["G4_3"] = bool(t_fault - t_f <= 15.0 + TOL and all(np.all(np.abs(log[k]["cmd"]) <= 1e-12) for k in after))
    # G4-4
    w4 = t >= t_fault + 1.0
    span = float(t[-1] - (t_fault + 1.0))
    mins = F[w4].min(axis=0)
    out["G4_4_window_s"] = round(span, 2)
    out["G4_4_min_kN"] = {LEGS[i]: round(float(mins[i]) / 1e3, 2) for i in range(4)}
    k1 = np.searchsorted(t, t_fault + 1.0)
    out["F_at_fault_plus1_kN"] = {LEGS[i]: round(float(F[min(k1, len(t) - 1), i]) / 1e3, 2) for i in range(4)}
    out["G4_4"] = None if span < 3.0 else bool(mins.min() >= geo["F_min"])
    # record (not the 323.9 (2) judgement): 0.5 s moving-mean minimum, the static load under a lasting teeter
    nm = 500
    csF = np.cumsum(np.vstack([np.zeros((1, 4)), F]), axis=0)
    movF = (csF[nm:] - csF[:-nm]) / nm
    tmF = t[nm - 1:]
    wm = tmF >= t_fault + 1.0
    mm = movF[wm].min(axis=0)
    out["G4_4_mean05_min_kN"] = {LEGS[i]: round(float(mm[i]) / 1e3, 2) for i in range(4)}
    out["G4_4_mean05"] = None if span < 3.0 else bool(mm.min() >= geo["F_min"])
    tail = t >= t[-1] - 2.0
    out["last2s_mean_kN"] = {LEGS[i]: round(float(F[tail, i].mean()) / 1e3, 2) for i in range(4)}
    out["last2s_ptp_kN"] = {LEGS[i]: round(float(np.ptp(F[tail, i])) / 1e3, 2) for i in range(4)}
    # G4-5
    w5 = (t >= t_f) & (t < t_fault + 1.0)
    healthy = [i for i in range(4) if i != fault_leg and LEGS[i] not in tg]
    longest = {}
    for i in healthy:
        low = w5 & (F[:, i] < geo["F_min"])
        iv = r51._intervals(low, t)
        longest[LEGS[i]] = round(max((b - a for a, b in iv), default=0.0), 3)
    out["G4_5_healthy_longest_low_s"] = longest
    head_true = F / A_P
    out["G4_5_max_head_bar"] = round(float(head_true[w5].max()) / 1e5, 1)
    fmax = float(F[w5, fault_leg].max())
    out["G4_5_faulty_max_kN"] = round(fmax / 1e3, 1)
    kf_ms = np.searchsorted(t, t_f)
    out["G4_5_faulty_rise_from_entry_kN"] = round((fmax - float(F[kf_ms, fault_leg])) / 1e3, 1)
    out["G4_5"] = bool(all(v <= 0.5 for v in longest.values()) and head_true[w5].max() <= HEAD_LIMIT_PA
                       and fmax <= EXT_FORCE_LIMIT_N[fault_leg])
    # G4-6
    ref = att[(t >= t_f - 0.5) & (t <= t_f)].mean(axis=0)
    n = 500
    cs = np.cumsum(np.vstack([np.zeros((1, 2)), att]), axis=0)
    mov = (cs[n:] - cs[:-n]) / n
    tm = t[n - 1:]
    w6 = (tm >= t_f) & (tm <= t_fault + 1.0)
    d6 = float(np.abs(mov[w6] - ref).max()) if w6.any() else 0.0
    out["G4_6_mean_change_deg"] = round(d6, 4)
    out["G4_6_inst_change_deg"] = round(float(np.abs(att[(t >= t_f) & (t <= t_fault + 1.0)] - att[kf_ms]).max()), 4)
    out["G4_6"] = bool(d6 <= 0.5)
    # G4-7
    if cmds_off is not None and not tg:
        cmds_on = np.array([r["cmd"] for r in log])
        out["G4_7_bit_identical"] = bool(cmds_on.shape == cmds_off.shape and np.array_equal(cmds_on, cmds_off))
    # G4-8 + truth contact time of each target
    if meta_run is not None:
        g8 = []
        for x in meta_run["targets"]:
            i = LEGS.index(x["leg"])
            row = {"leg": x["leg"], "outcome": x["outcome"], "travel_mm": None if x["travel_m"] is None
                   else round(x["travel_m"] * 1e3, 2), "limit_mm": round(x["max_travel_m"] * 1e3, 2),
                   "duration_s": None if x["duration_s"] is None else round(x["duration_s"], 2)}
            if x["start_s"] is not None:
                m = (t >= x["start_s"]) & (F[:, i] >= geo["F_min"] + 5e3) & (contact[:, i] > 0)
                tc = float(t[m][0]) if m.any() else None
                row["true_contact_rel_start_s"] = None if tc is None else round(tc - x["start_s"], 3)
                row["detect_rel_start_s"] = None if x["end_s"] is None else round(x["end_s"] - x["start_s"], 3)
            g8.append(row)
        out["G4_8"] = g8
    out["final_min_kN_all"] = round(float(mins.min()) / 1e3, 2)
    return out, k_f


def compare(meta_run, sh):
    """Two-path comparison of targets, times and end reason."""
    if meta_run is None:
        return {"same": sh["end_reason"] in ("no_target", "two_faults"), "note": "no meta run"}
    rows = []
    same = [x["leg"] for x in meta_run["targets"]] == [LEGS[x["leg"]] for x in sh["targets"]]
    for a, b in zip(meta_run["targets"], sh["targets"]):
        r = {"leg": a["leg"], "py": [a["start_s"], a["end_s"], a["outcome"]],
             "shadow": [b.get("start_s"), b.get("end_s"), b.get("outcome")]}
        ok = (a["outcome"] == b.get("outcome")
              and all((x is None and y is None) or (x is not None and y is not None and abs(x - y) < TOL)
                      for x, y in ((a["start_s"], b.get("start_s")), (a["end_s"], b.get("end_s")))))
        r["same"] = ok
        same &= ok
        rows.append(r)
    end_same = (meta_run["end_reason"] == sh["end_reason"] and meta_run["end_s"] is not None
                and sh["end_s"] is not None and abs(meta_run["end_s"] - sh["end_s"]) < TOL)
    return {"same": bool(same and end_same), "targets": rows,
            "end": {"py": [meta_run["end_s"], meta_run["end_reason"]], "shadow": [sh["end_s"], sh["end_reason"]]}}


# --- jobs --------------------------------------------------------------------------------------------------------

def prepare_base(cl, c2, Measurements, fs_kN):
    base = r51._reg_base("b", "top", (0.0, 0.0), fs_kN, [])
    plant = r51.make_plant(cl, base)
    plant.step(np.zeros(4), int(round(cl.rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
    plant.t = 0.0
    plant.arm()
    cfg = cl.preset_config(c2.ContactJudge.COMBINED, with_imu_samples=True, with_reapproach=True)
    ctrl = make_controller_class(c2).from_params(cl.PARAMS, cfg)
    ctrl.reset()
    ha = ctrl.geometry.head_area_m2
    cmd, valve = np.zeros(4), np.zeros(4)
    t_ready = t_lift = None
    while plant.t < r51.BASE_LIMIT_S:
        m = with_two_pressures(plant, r51.control_period(cl, Measurements, plant, cmd, valve, ha, ctrl.period_s),
                               ha)
        cmd = np.array(ctrl.update(m).leg_speed_m_s)
        if t_lift is None and plant.acc[15] == 0.0 and ctrl.phase is c2.C2Phase.LEVEL:
            t_lift = plant.t
        if ctrl.phase is c2.C2Phase.READY and t_ready is None:
            t_ready = plant.t
        if t_ready is not None and plant.t >= t_ready + EVENT_DELAY_S - 1e-9:
            break
    return plant, ctrl, cmd, valve, t_ready, t_lift


def run_job(args):
    case, off = args
    r51.place_worker()
    cl, c2, Measurements = r51._imports()
    cl.rmf.CONFIG.clear()
    cl.rpt.RCFG.clear()
    t0 = time.perf_counter()
    plant, ctrl, cmd, valve, t_ready, t_lift = prepare_base(cl, c2, Measurements, BASES[case["base"]])
    ha = ctrl.geometry.head_area_m2
    s = ctrl.config.fault_reground.to_meta()
    g = ctrl.geometry
    geo = {"F_min": g.F_min_N, "stroke_soft": g.stroke_soft_max_m,
           "head_force_limit_N": (g.locked_force_limit_N
                                  - ctrl.config.thresholds.locked_pressure_warning_margin_Pa * g.head_area_m2)}
    res = {"case": case["id"], "offset_s": off, "t_ready_s": t_ready, "t_crawler_liftoff_s": t_lift,
           "loc_at_branch": bool(ctrl._is_liftoff_confirmed()), "settings": s,
           "mass_at_branch_kg": ctrl._pressures.d1_imu_mass_kg(),
           "pre_branch_warnings": sorted({e.name for e in ctrl.events if e.name.startswith(("WARN", "FAULT"))})}
    if t_ready is None or str(ctrl.phase) != "ready":
        res["error"] = f"no READY at the branch (phase {ctrl.phase})"
        return res
    ev = case["event"]
    fault_after = case["fault"]
    if fault_after == "rl_mid":
        rec0, _, t_ev0, _ = simulate(cl, Measurements, copy.deepcopy(plant), copy.deepcopy(ctrl), cmd.copy(),
                                     valve.copy(), ha, ev, off, None, 0.0, 3.0)
        tt = rec0[:, 0] - t_ev0
        iv = [(a, b) for a, b in r51._intervals((rec0[:, 3] <= 0.0) & (tt >= 0.0), tt)]
        res["rl_lift_intervals_nofault"] = [(round(a, 3), round(b, 3)) for a, b in iv[:6]]
        fault_after = 0.5 * (iv[0][0] + iv[0][1]) if iv else FS24_FALLBACK_FAULT_S
    res["fault_after_event_s"] = round(fault_after, 4)
    # FAULT_REGROUND off (the old FAULT)
    ctrl_off = copy.deepcopy(ctrl)
    ctrl_off.config = dataclasses.replace(
        ctrl.config, fault_reground=dataclasses.replace(ctrl.config.fault_reground, enable=False))
    rec_off, log_off, _, _ = simulate(cl, Measurements, copy.deepcopy(plant), ctrl_off, cmd.copy(), valve.copy(),
                                      ha, ev, off, case["fault_leg"], fault_after, RUN_AFTER_EVENT_S)
    cmds_off = np.array([r["cmd"] for r in log_off])
    j_off, _ = judge(rec_off, log_off, [], plant.t + off, case["fault_leg"], fault_after, None, geo, s)
    res["off"] = {k: j_off.get(k) for k in ("t_f_rel_s", "t_fault_rel_s", "G4_4", "G4_4_min_kN", "true_targets",
                                            "final_min_kN_all", "G4_6_mean_change_deg", "G4_4_mean05",
                                            "G4_4_mean05_min_kN", "last2s_mean_kN", "last2s_ptp_kN")}
    res["variants"] = {}
    for vname in VARIANT_NAMES:
        ctrl_on = copy.deepcopy(ctrl)
        ctrl_on.abort2 = vname
        rec, log, t_ev, events = simulate(cl, Measurements, copy.deepcopy(plant), ctrl_on, cmd.copy(),
                                          valve.copy(), ha, ev, off, case["fault_leg"], fault_after,
                                          RUN_AFTER_EVENT_S)
        meta_run = ctrl_on.meta()["fault_reground"]["run"]
        j_on, k_f = judge(rec, log, events, t_ev, case["fault_leg"], fault_after, meta_run, geo, s, cmds_off)
        v = {"meta_run": meta_run, "judge": j_on,
             "events": [(round(tt - t_ev, 3), n) for tt, n in events
                        if not n.startswith(("INFO_PRESSURE", "shadow_"))][:60]}
        if k_f is not None:
            if not {"hold", "cued", "susp"} & set(vname.split("+")):
                sh = shadow_run(log, k_f, s, geo, vname)
                v["shadow"] = {k: x for k, x in sh.items() if k != "targets"}
                v["shadow"]["targets"] = [{k: y for k, y in x.items() if k != "seen"} for x in sh["targets"]]
                v["two_path"] = compare(meta_run, sh)
            r = log[k_f]
            t_fault = j_on.get("t_fault_rel_s")
            hi = t_ev + (t_fault if t_fault is not None else 0.0) + 2.0
            v["series"] = [[round(q["t"] - t_ev, 2), q["phase"][:6],
                            None if q["tilt"] is None else [round(math.degrees(a), 3) for a in q["tilt"]],
                            [round(math.degrees(a), 3) for a in q["filt"]],
                            None if q["load_est"] is None else (q["load_est"] / 1e3).round(1).tolist(),
                            (q["cmd"] * 1e3).round(2).tolist(), (q["stroke"] * 1e3).round(2).tolist(),
                            [round(float(np.interp(q["t"], rec[:, 0], rec[:, 17 + a])), 3) for a in (0, 1)],
                            [round(float(np.interp(q["t"], rec[:, 0], rec[:, 5 + a])) / 1e3, 1) for a in range(4)],
                            None if q["load_nom"] is None else round(float(q["load_nom"].sum()) / 1e3, 1),
                            None if q["fz"] is None else round(q["fz"], 3)]
                           for q in log if t_ev - 1.0 <= q["t"] <= hi + 6.0]
            v["inputs_at_fault"] = {
                "load_est_kN": (r["load_est"] / 1e3).round(2).tolist(),
                "resid_mm": None if r["resid"] is None else (r["resid"] * 1e3).round(3).tolist(),
                "mass_kg": r["mass"], "crawler_lifted": r["crawler_lifted"], "loc": r["loc"]}
        res["variants"][vname] = v
    res["wall_s"] = round(time.perf_counter() - t0, 1)
    return res


def main():
    set_affinity_from_env()
    out = Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    only = os.environ.get("R64_CASES")
    cases = [c for c in CASES if not only or c["id"] in only.split(",")]
    offs = OFFSETS if not os.environ.get("R64_OFFSETS") else tuple(
        float(x) for x in os.environ["R64_OFFSETS"].split(","))
    jobs = [(c, o) for c in cases for o in offs]
    t0 = time.perf_counter()
    with Pool(min(workers, len(jobs))) as pool:
        res = pool.map(run_job, jobs, chunksize=1)
    summary = []
    for r in res:
        if "error" in r:
            summary.append({"case": r["case"], "off": r["offset_s"], "error": r["error"]})
            continue
        for vname, v in r["variants"].items():
            j = v["judge"]
            summary.append({
                "case": r["case"], "off": r["offset_s"], "var": vname, "t_f": j.get("t_f_rel_s"),
                "fault": j.get("t_fault_rel_s"), "targets": j.get("targets"), "true": j.get("true_targets"),
                "end": None if v.get("meta_run") is None else v["meta_run"]["end_reason"],
                "G4": {k: j.get(k) for k in ("G4_1", "G4_2", "G4_3", "G4_4", "G4_4_mean05", "G4_5", "G4_6",
                                             "G4_7_bit_identical")},
                "min_kN": j.get("final_min_kN_all"), "off_G4_4": r["off"].get("G4_4"),
                "off_min_kN": r["off"].get("final_min_kN_all"), "two_path_same": v.get("two_path", {}).get("same")})
    out.write_text(json.dumps({"meta": {"script": "04_scripts/03_control/s8/r64_g4_closed_loop.py",
                                        "spec": "rev. 64 323.8 step 2 (P-S8-24 T8)",
                                        "wall_s": round(time.perf_counter() - t0, 1), "workers": workers,
                                        "offsets_s": offs, "run_after_event_s": RUN_AFTER_EVENT_S,
                                        "head_jump_Pa": HEAD_JUMP_PA},
                               "summary": summary, "runs": res}, indent=1, default=float), encoding="utf-8")
    print("done", round(time.perf_counter() - t0, 1), "s ->", out)


if __name__ == "__main__":
    main()
