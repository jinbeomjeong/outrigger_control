"""R51-1 (spec 00_docs/04_control/s6_control_spec.md rev. 51 225 / rev. 52): re-approach re-trigger rule candidates
on the reduced closed loop.

Harness (as s8_fs_precheck.py rev. 42, not copied): reduced 6-DoF FlexPlant (rigid mast) + dynamics rev. 39 L1-R
rod-side law (s8_g4_rodside_check.RodSidePlant, armed after the crawler settle), Coulomb seal friction per leg
(the run's per-leg limits), valve first-order lag 0.1 s (exact chunk mean, 1 ms chunks), IMU 10 ms samples, the
project C2 (03_src, read only) with c2py_r8d1_closed_loop.preset_config(COMBINED) = with_10hz_d1 (10 Hz, d = 1,
increment limit 0.25, R-5, P-R8-13, normalised twist / guard gains) minus CHECK / zero calibration / REANCHOR /
target check; ideal sensors (no noise).
Plant beta: the RodSidePlant is built at the YAML beta (its consistency check) and its oil spring k_h (= k_oil) and
rod-side k_r are then scaled by beta / 1 GPa (both linear in beta). The controller stays at beta 1.0 (U-R8-22).

Re-trigger candidates (subclass R51Controller, no 03_src change; the rule is applied in _start_reapproaches):
  base      project P-R8-13 unchanged
  off       re-approach off (passive reference)
  W<x>      gate: within x s after the end of the last re-approach, a start on a leg whose twist sign differs from the
            last one (the other diagonal) needs the lower load estimate < strong level (0 N) on 2 samples in a row
            (otherwise deferred; the guard path keeps acting); same-diagonal restarts as now
  A<x>      gate for every restart within x s (any diagonal; the literal U-S8-45 candidate)
  S         twist re-approach speed divided by the twist-gain stiffness scale (probe-measured, bounded 1.0..1.5)
  combos    e.g. W0.8S
Events (branch from READY + 5 s by deepcopy; start-phase offsets 0 / 0.025 / 0.05 / 0.075 s): Poly345 floor
settlement of one pad on every 1 ms chunk, depth / ramp of the ML episode or the regression case. Mode "P" (RE1bP):
RR drop 30 mm / 0.05 s 0.1 s after the first PROBE entry (own run, no branch).
Metrics (event + 0 .. 8 s, 1 ms chunks): pad lift (contact <= 0) intervals per leg, event pair (event leg + its
diagonal) union time and last touch-down, adjacent-leg lift time and max pad gap, re-approach starts (time, leg,
twist sign), starts after event + 1.5 s, actuator twist-mode work W = int 1/2 D (n . u_valve) dt per 0.5 s bin
(D = (F_FL + F_RR) - (F_FR + F_RL), true cylinder forces), min true cylinder force (chunk min), max |attitude
change|, time back to READY.
Run (dynamics-dev, numba): python -I r51_reapp_closed_loop.py <project_root> <out_json> [workers]
Env: R51_SET = ml | regress | all (default all); R51_VARIANTS = comma list (default base,off,W0.8,A0.8,S,W0.8S).
Deterministic (no random numbers).
"""
from __future__ import annotations

import copy
import json
import math
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("NUMBA_NUM_THREADS", "1")

import numpy as np  # noqa: E402

ROOT = Path(sys.argv[1]).resolve()
for _p in (ROOT / "03_src", ROOT / "04_scripts" / "03_control" / "r8d1", ROOT / "04_scripts" / "03_control",
           ROOT / "04_scripts" / "01_dynamics"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

YAML_BETA = 1.0e9
EVENT_DELAY_S = 5.0
WINDOW_S = 8.0
RUN_AFTER_S = float(os.environ.get("R51_RUN_S", "12.0"))
BASE_LIMIT_S = 170.0
OFFSETS = (0.0, 0.025, 0.05, 0.075)
N_TWIST = np.array([0.476, -0.476, -0.523, 0.523])
LEGS = ("FL", "FR", "RL", "RR")
DIAG = {0: 3, 3: 0, 1: 2, 2: 1}

SCOPE = json.loads((ROOT / "06_analysis" / "02_control" / "s8" / "s8_rev52_cs836_scope.json").read_text(encoding="utf-8"))


def _ml_base(base_id: str, episodes: list[str]) -> dict:
    c = SCOPE["cases"][episodes[0]]
    return {"id": base_id, "level": c["level"], "floor": tuple(c["floor_deg"]), "beta": c["beta_GPa"] * 1e9,
            "seal_N": list(c["seal_N"]),
            "events": [{"id": e, "leg": LEGS.index(SCOPE["cases"][e]["leg"]),
                        "depth": SCOPE["cases"][e]["depth_mm"] / 1e3, "ramp": SCOPE["cases"][e]["ramp_s"]}
                       for e in episodes]}


def _reg_base(base_id, level, floor, fs_kN, events, beta=1.0e9, p_mode=False):
    rear = 0.8333
    return {"id": base_id, "level": level, "floor": floor, "beta": beta,
            "seal_N": [fs_kN * 1e3, fs_kN * 1e3, rear * fs_kN * 1e3, rear * fs_kN * 1e3], "events": events,
            "p_mode": p_mode}


REG_EVENTS = [
    {"id": "G4", "leg": 3, "depth": 0.0115, "ramp": 2.0},
    {"id": "SS", "leg": 3, "depth": 0.0115, "ramp": 20.0},
    {"id": "RE1bF", "leg": 3, "depth": 0.030, "ramp": 0.05},
    {"id": "FLdrop", "leg": 0, "depth": 0.030, "ramp": 0.05},
]
BASES_ML = [
    _ml_base("ML78", ["ML78_ep0", "ML78_ep1", "ML78_ep3"]),
    _ml_base("ML00", ["ML00_ep5"]),
    _ml_base("ML21", ["ML21_ep1"]),
    _ml_base("ML90", ["ML90_ep1"]),
    _ml_base("ML24", ["ML24_ep7"]),
]
def _scope_bases() -> list[dict]:
    """All C-S8-36 fast front settlements of the scope file, grouped by ML base (R51_SET=scope)."""
    groups: dict[str, list[str]] = {}
    for case in SCOPE["scope"]:
        groups.setdefault(case.split("_")[0], []).append(case)
    return [_ml_base(b, eps) for b, eps in groups.items()]


BASES_REG = [
    _reg_base("flat_Fs0", "top", (0.0, 0.0), 0.0, REG_EVENTS, p_mode=True),
    _reg_base("flat_Fs4", "top", (0.0, 0.0), 4.0, REG_EVENTS),
    _reg_base("flat_Fs8", "top", (0.0, 0.0), 8.0, REG_EVENTS[:3]),
    _reg_base("flat_Fs2_b1.6", "top", (0.0, 0.0), 2.0, REG_EVENTS, beta=1.6e9),
    _reg_base("rpB_Fs2", "top", (2.7355, 1.7592), 2.0, REG_EVENTS[:3]),
    _reg_base("mid_flat_Fs0", "middle", (0.0, 0.0), 0.0, REG_EVENTS[2:]),
]

VARIANTS = {
    "project": {"project": True},
    "base": {},
    "off": {"enable": False},
    "W0.8": {"window_s": 0.8, "opposite_only": True},
    "W1.5": {"window_s": 1.5, "opposite_only": True},
    "A0.8": {"window_s": 0.8, "opposite_only": False},
    "S": {"speed_norm": True},
    "W0.8S": {"window_s": 0.8, "opposite_only": True, "speed_norm": True},
    "W1.5S": {"window_s": 1.5, "opposite_only": True, "speed_norm": True},
    "A0.8S": {"window_s": 0.8, "opposite_only": False, "speed_norm": True},
    "W0.8S3": {"window_s": 0.8, "opposite_only": True, "speed_norm": True, "strong_samples": 3},
    "H": {"hold_on_contact": True},
    "T": {"taper": True},
    "W0.8Sr0.8": {"window_s": 0.8, "opposite_only": True, "retrigger_s": 0.8},
    "W0.8Sr2": {"window_s": 0.8, "opposite_only": True, "retrigger_s": 2.0},
    "W0.8F0.6r2": {"window_s": 0.8, "opposite_only": True, "retrigger_s": 2.0, "retrigger_factor": 0.6},
    "Sr2": {"retrigger_s": 2.0},
    "F0.6r2": {"retrigger_s": 2.0, "retrigger_factor": 0.6},
    "W0.8F0.5r2": {"window_s": 0.8, "opposite_only": True, "retrigger_s": 2.0, "retrigger_factor": 0.5},
    "W0.8F0.7r2": {"window_s": 0.8, "opposite_only": True, "retrigger_s": 2.0, "retrigger_factor": 0.7},
    "W0.8F0.6r1.5": {"window_s": 0.8, "opposite_only": True, "retrigger_s": 1.5, "retrigger_factor": 0.6},
    "W0.8F0.6r3": {"window_s": 0.8, "opposite_only": True, "retrigger_s": 3.0, "retrigger_factor": 0.6},
    "W0.5F0.6r2": {"window_s": 0.5, "opposite_only": True, "retrigger_s": 2.0, "retrigger_factor": 0.6},
    "W1.2F0.6r2": {"window_s": 1.2, "opposite_only": True, "retrigger_s": 2.0, "retrigger_factor": 0.6},
    "W0.8F0.6r2s1": {"window_s": 0.8, "opposite_only": True, "retrigger_s": 2.0, "retrigger_factor": 0.6,
                     "strong_samples": 1},
    "W0.8F0.6r2s3": {"window_s": 0.8, "opposite_only": True, "retrigger_s": 2.0, "retrigger_factor": 0.6,
                     "strong_samples": 3},
    "A0.8F0.6r2": {"window_s": 0.8, "opposite_only": False, "retrigger_s": 2.0, "retrigger_factor": 0.6},
    "W0.8T": {"window_s": 0.8, "opposite_only": True, "taper": True},
    "A0.8T": {"window_s": 0.8, "opposite_only": False, "taper": True},
    "W0.8TS": {"window_s": 0.8, "opposite_only": True, "taper": True, "speed_norm": True},
    "W0.8H": {"window_s": 0.8, "opposite_only": True, "hold_on_contact": True},
    "A0.8H": {"window_s": 0.8, "opposite_only": False, "hold_on_contact": True},
    "W0.8M": {"window_s": 0.8, "opposite_only": True, "slow_mean": True},
    "W0.8HM": {"window_s": 0.8, "opposite_only": True, "hold_on_contact": True, "slow_mean": True},
    "A0.8HM": {"window_s": 0.8, "opposite_only": False, "hold_on_contact": True, "slow_mean": True},
    "W0.8G": {"window_s": 0.8, "opposite_only": True, "gyro_gate": True},
    "W0.8SG": {"window_s": 0.8, "opposite_only": True, "speed_norm": True, "gyro_gate": True},
}


def place_worker() -> None:
    """EcoQoS off for this worker (no cost measurement here)."""
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = wintypes.HANDLE

    class PTS(ctypes.Structure):
        _fields_ = [("Version", wintypes.ULONG), ("ControlMask", wintypes.ULONG), ("StateMask", wintypes.ULONG)]

    st = PTS(1, 1, 0)
    k32.SetProcessInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    k32.SetProcessInformation(k32.GetCurrentProcess(), 4, ctypes.byref(st), ctypes.sizeof(st))


def _imports():
    import c2py_r8d1_closed_loop as cl  # noqa: E402  (patches the harness modules)
    from outrigger_sim.control import c2
    from outrigger_sim.signals import Measurements
    return cl, c2, Measurements


def make_controller_class(c2):
    class R51Controller(c2.C2Controller):
        """P-R8-13 with an R51-1 re-trigger rule (module docstring); rule dict ``r51`` set per instance."""

        r51: dict = {}

        def reset(self, *a, **kw):
            out = super().reset(*a, **kw)
            self._r51_last_end_s = None
            self._r51_last_sign = 0.0
            self._r51_strong = np.zeros(4, dtype=int)
            self._r51_deferred = []
            return out

        def _end_reapproach(self, leg, reading, outcome):
            super()._end_reapproach(leg, reading, outcome)
            self._r51_last_end_s = float(reading.t_s)
            self._r51_last_sign = float(np.sign(self.geometry.twist_vector[leg]))

        def _gated(self, leg: int, t_s: float) -> bool:
            w = self.r51.get("window_s")
            if w is None or self._r51_last_end_s is None:
                return False
            if t_s - self._r51_last_end_s >= w - 1e-9:
                return False
            if self.r51.get("opposite_only", True):
                return float(np.sign(self.geometry.twist_vector[leg])) != self._r51_last_sign
            return True

        def _start_reapproaches(self, reading, loads_N, settings):
            if not self.r51.get("window_s") and not self.r51.get("retrigger_s"):
                return super()._start_reapproaches(reading, loads_N, settings)
            st = self._state
            lift_off = settings.load_fraction_of_F_min * self.geometry.F_min_N
            required = settings.samples or self.config.r8.confirmation.relevel_samples
            strong_level = self.r51.get("strong_level_N", 0.0)
            strong_samples = self.r51.get("strong_samples", 2)
            probed = self._probed_leg()
            hist = getattr(self, "_r51_hist", [])
            hist.append(np.asarray(loads_N, float).copy())
            self._r51_hist = hist[-self.r51.get("mean_samples", 8):]
            slow = np.mean(self._r51_hist, axis=0)
            for leg in range(c2.LEG_COUNT):
                another = settings.single_leg and bool(st.active_reapproaches)
                watched = (st.touched[leg] and st.is_reapproach_armed[leg] and leg not in st.active_reapproaches
                           and leg != probed and not another)
                if not watched or loads_N[leg] >= lift_off:
                    st.reapproach_low_counts[leg] = 0
                    self._r51_strong[leg] = 0
                    continue
                st.reapproach_low_counts[leg] += 1
                self._r51_strong[leg] = self._r51_strong[leg] + 1 if loads_N[leg] < strong_level else 0
                if st.reapproach_low_counts[leg] < required:
                    continue
                is_static = self.r51.get("slow_mean") and slow[leg] < lift_off
                if (self._gated(leg, float(reading.t_s)) and self._r51_strong[leg] < strong_samples
                        and not is_static):
                    self._r51_deferred.append((float(reading.t_s), leg))
                    continue
                if self.r51.get("gyro_gate"):
                    # corner rise rate from the gyro sample (body small angle): v = w_x y - w_y x [m/s]
                    wx, wy = st.gyro_rate_rad_s
                    px, py = self.geometry.pad_xy_m[leg]
                    if wx * py - wy * px < -self.r51.get("gyro_gate_m_s", 0.005):
                        self._r51_deferred.append((float(reading.t_s), leg))
                        continue
                st.reapproach_low_counts[leg] = 0
                self._r51_strong[leg] = 0
                run = c2._Reapproach(leg, reading.t_s, float(reading.motor_stroke_m[leg]), settings.mode)
                rt = self.r51.get("retrigger_s")
                run.r51_retrigger = bool(rt and self._r51_last_end_s is not None
                                         and float(reading.t_s) - self._r51_last_end_s < rt - 1e-9)
                st.active_reapproaches[leg] = run
                st.reapproach_history.append(run)
                self._add_event(reading.t_s, f"leg_reapproach_start:{c2.LEG_ORDER[leg]}", is_warning=True)

        def _reapproach_twist_rate(self, reading):
            if self.r51.get("hold_on_contact"):
                st = self._state
                run = st.active_reapproaches[min(st.active_reapproaches)]
                if run.exit_samples_seen >= 1:
                    # no push while the exit level is being confirmed
                    self._r51_hold_periods = getattr(self, "_r51_hold_periods", 0) + 1
                    return 0.0
            rate = super()._reapproach_twist_rate(reading)
            if self.r51.get("taper"):
                st = self._state
                run = st.active_reapproaches[min(st.active_reapproaches)]
                n_exit = self.config.r8.lifted_reapproach.exit_samples
                rate = rate * max(0.0, 1.0 - run.exit_samples_seen / n_exit)
            if self.r51.get("speed_norm"):
                scale = self._twist_gain_scale()
                if scale:
                    rate = rate / scale
            if self.r51.get("retrigger_s"):
                st = self._state
                run = st.active_reapproaches[min(st.active_reapproaches)]
                if getattr(run, "r51_retrigger", False):
                    f = self.r51.get("retrigger_factor")
                    if f is not None:
                        rate = rate * f
                    else:
                        scale = self._twist_gain_scale()
                        rate = rate / scale if scale else rate
            return rate

    return R51Controller


def make_plant(cl, base):
    import s8_g4_rodside_check as rsc
    Plant = rsc.make_plant_class(cl)
    plant = Plant(base["level"], base["floor"][0], base["floor"][1], Fs=0.0)
    k = base["beta"] / YAML_BETA
    plant.ko = np.asarray(plant.ko, float) * k
    plant.kh = plant.ko.copy()
    plant.kr = np.asarray(plant.kr, float) * k
    plant.Fs = np.asarray(base["seal_N"], float)
    return plant


def pad_gaps(cl, plant) -> np.ndarray:
    R = cl.rcc._R(plant.q)
    ez = R[:, 2]
    a_n = float(plant.nrm @ ez)
    out = np.zeros(4)
    for i in range(4):
        p0 = plant.r + R @ plant.pad_rel[i]
        out[i] = (plant.nrm @ p0 + plant.goff[i]) / a_n - plant.x[i]
    return out


C_LOCK = np.array([34403.519, 34403.519, 30348.4527, 30348.4527])
C_MOVE = np.array([100206.065477022, 100206.065477022, 86949.0144383396, 86949.0144383396])
"""Leg damping [N s/m] of the L2b Chrono runs (record meta ``run.engine.actuator.damping_locked / moving``, same in
every ML base): locked zeta 0.03 / moving zeta 0.10 (dynamics 5.20.3). As the 5.28 replica, the moving value
applies while the valve output |u| > lock_eps (1e-6 m/s), switched per 1 ms chunk. R51_DAMP=lock keeps the harness
L1 value (locked) always.
An empty R51_DAMP counts as unset (switch): a runner that restores an unset variable as ""
must not turn the damping switch off (spec 429.11.1)."""
DAMP_SWITCH = (os.environ.get("R51_DAMP") or "switch") == "switch"


def control_period(cl, Measurements, plant, cmd, valve, ha, period_s, floor_fn=None, rec=None):
    lag_steps = round(cl.LAG_CHUNK_S / plant.dt)
    cps = round(cl.IMU_SAMPLE_S / cl.LAG_CHUNK_S)
    nsp = round(period_s / cl.IMU_SAMPLE_S)
    imu = []
    for _ in range(nsp):
        fsum = np.zeros(3)
        for _ in range(cps):
            if floor_fn is not None:
                floor_fn(plant)
            if DAMP_SWITCH:
                plant.cn = np.where(np.abs(valve) > 1e-6, C_MOVE, C_LOCK)
            acc = cl._lagged_step(plant, cmd, valve, lag_steps)
            fsum += acc[0:3]
            if rec is not None:
                c = np.asarray(acc[11:15], float)
                rec.append(np.r_[plant.t, c, c - plant.Wr, valve, pad_gaps(cl, plant), np.degrees(plant.attitude())])
        imu.append(fsum / (lag_steps * cps))
    return Measurements(
        t_s=plant.t, specific_force_m_s2=np.mean(imu, axis=0), angular_rate_rad_s=np.asarray(plant.w, float),
        head_pressure_Pa=plant.pressure() / ha, stroke_m=np.asarray(plant.sref, float),
        stroke_corrected_m=np.asarray(plant.x, float), imu_specific_force_samples_m_s2=np.array(imu))


def _intervals(mask, t):
    idx = np.flatnonzero(mask)
    if not idx.size:
        return []
    br = np.flatnonzero(np.diff(idx) > 1)
    st = np.r_[idx[0], idx[br + 1]]
    en = np.r_[idx[br], idx[-1]]
    return [(float(t[a]), float(t[b]) + 1e-3) for a, b in zip(st, en)]


def metrics(rec, t_ev, ctrl, n_ev0, ev_leg, att0, t_ready_after):
    r = np.array(rec)
    t = r[:, 0] - t_ev
    w = (t >= 0) & (t <= WINDOW_S)
    contact, F, valve, gap, att = r[:, 1:5], r[:, 5:9], r[:, 9:13], r[:, 13:17], r[:, 17:19]
    lifted = contact <= 0.0
    out = {"lifts": {}}
    for i, leg in enumerate(LEGS):
        iv = _intervals(w & lifted[:, i], t)
        if iv:
            out["lifts"][leg] = {"sum_s": round(sum(b - a for a, b in iv), 3), "last_touch_s": round(iv[-1][1], 3),
                                 "n": len(iv), "max_gap_mm": round(float(gap[w & lifted[:, i], i].max() * 1e3), 2),
                                 "intervals": [(round(a, 3), round(b, 3)) for a, b in iv[:12]]}
    pair = [ev_leg, DIAG[ev_leg]]
    adj = [i for i in range(4) if i not in pair]
    up = _intervals(w & lifted[:, pair].any(axis=1), t)
    out["pair_union_s"] = round(sum(b - a for a, b in up), 3)
    out["pair_last_touch_s"] = round(up[-1][1], 3) if up else 0.0
    aw = w & lifted[:, adj].any(axis=1)
    out["adj_sum_s"] = round(float((w[:, None] & lifted[:, adj]).sum() * 1e-3), 3)
    out["adj_max_gap_mm"] = round(float(max((gap[w & lifted[:, i], i].max() if (w & lifted[:, i]).any() else 0.0)
                                            for i in adj) * 1e3), 2)
    out["adj_last_touch_s"] = round(_intervals(aw, t)[-1][1], 3) if aw.any() else 0.0
    starts = [(round(e.t_s - t_ev, 2), e.name.split(":")[1]) for e in ctrl.events[n_ev0:]
              if e.name.startswith("leg_reapproach_start")]
    out["starts"] = starts
    out["n_starts"] = len(starts)
    out["n_late_starts"] = sum(1 for s, _ in starts if s > 1.5)
    signs = [int(np.sign(N_TWIST[LEGS.index(leg)])) for _, leg in starts]
    out["sign_changes"] = int(sum(1 for a, b in zip(signs, signs[1:]) if a != b))
    out["deferred"] = [(round(ts - t_ev, 2), LEGS[leg]) for ts, leg in getattr(ctrl, "_r51_deferred", []) if ts >= t_ev][:30]
    D = (F[:, 0] + F[:, 3]) - (F[:, 1] + F[:, 2])
    p = 0.5 * D * (valve @ N_TWIST) * 1e-3
    bins = []
    for lo in np.arange(0.0, WINDOW_S, 0.5):
        m = (t >= lo) & (t < lo + 0.5)
        bins.append(round(float(p[m].sum()), 1))
    out["W_bins_J"] = bins
    out["W_after1.5_pos_J"] = round(float(sum(b for b in bins[3:] if b > 0)), 1)
    out["W_after1.5_max_bin_J"] = max(bins[3:]) if len(bins) > 3 else 0.0
    out["min_true_kN"] = round(float(F[w].min() / 1e3), 2)
    out["min_true_after1.5_grounded_kN"] = None
    out["max_att_change_deg"] = round(float(np.abs(att[w] - att0).max()), 4)
    out["t_back_ready_s"] = None if t_ready_after is None else round(t_ready_after - t_ev, 2)
    out["final_phase"] = str(ctrl.phase)
    # passive decay check of the diagonal load difference after 1.5 s (peaks of |D| in 0.5 s bins)
    pk = []
    for lo in np.arange(1.5, WINDOW_S, 0.5):
        m = (t >= lo) & (t < lo + 0.5)
        pk.append(round(float(np.ptp(D[m]) / 1e3), 1))
    out["D_ptp_kN_bins_from1.5"] = pk
    out["gate_U832"] = {"pair_union_le_1.8": out["pair_union_s"] <= 1.8,
                        "pair_last_touch_le_3.0": out["pair_last_touch_s"] <= 3.0,
                        "adj_gap_le_2mm": out["adj_max_gap_mm"] <= 2.0}
    return out


def run_event(cl, Measurements, C2Phase, plant, ctrl, cmd, valve, ha, ev, off):
    t_ev = plant.t + off
    n0 = len(ctrl.events)
    rec = []
    leg, depth, ramp = ev["leg"], ev["depth"], ev["ramp"]

    def floor_fn(pl_):
        tau = min(1.0, max(0.0, (pl_.t - t_ev) / ramp))
        pl_.goff[leg] = depth * (tau ** 3 * (10 - 15 * tau + 6 * tau ** 2))

    att0 = np.degrees(plant.attitude())
    t_ready_after = None
    was_ready = True
    while plant.t < t_ev + RUN_AFTER_S:
        m = control_period(cl, Measurements, plant, cmd, valve, ha, ctrl.period_s, floor_fn, rec)
        cmd = np.array(ctrl.update(m).leg_speed_m_s)
        is_ready = ctrl.phase is C2Phase.READY
        if not is_ready:
            was_ready = False
        if is_ready and not was_ready and t_ready_after is None and plant.t > t_ev + 0.5:
            t_ready_after = plant.t
    out = metrics(rec, t_ev, ctrl, n0, leg, att0, t_ready_after)
    out.update({"event": ev["id"], "offset_s": off})
    return out


def level_to_ready(cl, Measurements, C2Phase, plant, ctrl, stop_fn):
    ha = ctrl.geometry.head_area_m2
    cmd, valve = np.zeros(4), np.zeros(4)
    t_ready = t_lift = None
    min_lev = math.inf
    while plant.t < BASE_LIMIT_S:
        rec = [] if t_lift is not None else None
        m = control_period(cl, Measurements, plant, cmd, valve, ha, ctrl.period_s, None, rec)
        cmd = np.array(ctrl.update(m).leg_speed_m_s)
        if t_lift is None and plant.acc[15] == 0.0 and ctrl.phase is C2Phase.LEVEL:
            t_lift = plant.t
        if rec:
            min_lev = min(min_lev, float(np.array(rec)[:, 5:9].min()))
        if ctrl.phase is C2Phase.READY and t_ready is None:
            t_ready = plant.t
        if stop_fn(plant, ctrl, t_ready):
            break
    return cmd, valve, t_ready, t_lift, min_lev


def run_job(args):
    base, vname = args
    place_worker()
    cl, c2, Measurements = _imports()
    C2Phase = c2.C2Phase
    t0 = time.perf_counter()
    cl.rmf.CONFIG.clear()
    cl.rpt.RCFG.clear()
    Cls = make_controller_class(c2)
    plant = make_plant(cl, base)
    plant.step(np.zeros(4), int(round(cl.rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
    plant.t = 0.0
    plant.arm()
    cfg = cl.preset_config(c2.ContactJudge.COMBINED, with_imu_samples=True,
                           with_reapproach=VARIANTS[vname].get("enable", True))
    if VARIANTS[vname].get("project"):
        # P-S8-16 acceptance: the plain project controller (its preset must carry the rule); compare with W0.8F0.6r2
        ctrl = c2.C2Controller.from_params(cl.PARAMS, cfg)
    else:
        ctrl = Cls.from_params(cl.PARAMS, cfg)
        ctrl.r51 = dict(VARIANTS[vname])
    ctrl.reset()
    ha = ctrl.geometry.head_area_m2
    p_plant, p_ctrl = (copy.deepcopy(plant), copy.deepcopy(ctrl)) if base.get("p_mode") else (None, None)
    cmd, valve, t_ready, t_lift, min_lev = level_to_ready(
        cl, Measurements, C2Phase, plant, ctrl,
        lambda pl, ct, tr: tr is not None and pl.t >= tr + EVENT_DELAY_S - 1e-9)
    res = {"base": base["id"], "variant": vname, "t_ready_s": t_ready, "t_crawler_liftoff_s": t_lift,
           "D8_min_true_after_liftoff_kN": round(min_lev / 1e3, 2),
           "pre_event_reapproach": [f"{e.t_s:.1f} {e.name}" for e in ctrl.events if "reapproach" in e.name],
           "twist_scale": ctrl._twist_gain_scale(), "events": [],
           "lifted_reapproach_settings": repr(ctrl.config.r8.lifted_reapproach)}
    if t_ready is None:
        res["error"] = "no READY"
        return res
    for ev in base["events"]:
        for off in OFFSETS:
            res["events"].append(run_event(cl, Measurements, C2Phase, copy.deepcopy(plant), copy.deepcopy(ctrl),
                                           cmd.copy(), valve.copy(), ha, ev, off))
    if base.get("p_mode"):
        res["events"].append(run_probe_drop(cl, Measurements, C2Phase, p_plant, p_ctrl))
    res["wall_s"] = round(time.perf_counter() - t0, 1)
    return res


def run_probe_drop(cl, Measurements, C2Phase, plant, ctrl):
    """RE1bP: RR drop 30 mm / 0.05 s at 0.1 s after the first PROBE entry (v34_drop mode P)."""
    ha = ctrl.geometry.head_area_m2
    cmd, valve = np.zeros(4), np.zeros(4)
    t_probe = None
    while plant.t < BASE_LIMIT_S:
        m = control_period(cl, Measurements, plant, cmd, valve, ha, ctrl.period_s)
        cmd = np.array(ctrl.update(m).leg_speed_m_s)
        if ctrl.phase is C2Phase.PROBE and t_probe is None:
            t_probe = plant.t
        if t_probe is not None and plant.t >= t_probe + 0.1 - 1e-9:
            break
    if t_probe is None:
        return {"event": "RE1bP", "error": "no PROBE"}
    return run_event(cl, Measurements, C2Phase, plant, ctrl, cmd, valve, ha,
                     {"id": "RE1bP", "leg": 3, "depth": 0.030, "ramp": 0.05}, 0.0)


def main():
    out = Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    which = os.environ.get("R51_SET", "all")
    names = os.environ.get("R51_VARIANTS", "base,off,W0.8,A0.8,S,W0.8S").split(",")
    bases = (BASES_ML if which in ("ml", "all") else []) + (BASES_REG if which in ("regress", "all") else [])
    if which == "scope":
        bases = _scope_bases()
    only = os.environ.get("R51_BASES")
    if only:
        bases = [b for b in bases if b["id"] in only.split(",")]
    jobs = [(b, v) for b in bases for v in names]
    cl = _imports()[0]
    pl = make_plant(cl, BASES_ML[0])
    pl.step(np.zeros(4), 2); pl.arm(); pl.step(np.zeros(4), 2)
    t0 = time.perf_counter()
    with Pool(min(workers, len(jobs))) as pool:
        res = pool.map(run_job, jobs, chunksize=1)
    out.write_text(json.dumps({"meta": {"script": "04_scripts/03_control/s8/r51_reapp_closed_loop.py",
                                        "spec": "rev. 52 (R51-1)", "wall_s": round(time.perf_counter() - t0, 1),
                                        "workers": workers, "variants": {n: VARIANTS[n] for n in names},
                                        "offsets_s": OFFSETS, "window_s": WINDOW_S},
                               "runs": res}, indent=1, default=float), encoding="utf-8")
    print("done", round(time.perf_counter() - t0, 1), "s ->", out)


if __name__ == "__main__":
    main()
