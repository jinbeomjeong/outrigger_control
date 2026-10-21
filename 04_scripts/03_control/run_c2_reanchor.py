"""C2 pad re-anchoring action (REANCHOR) inside the C2 state machine: design screen and robustness verification.

Hand-off from dynamics-expert (00_docs/01_dynamics/dynamics_model.md rev. 18, section 3.10.7,
06_analysis/00_dynamics/pad_tangential_check.json, class run_pad_tangential_check.C2RA): after levelling, unload the
light rear pads one at a time along the twist mode n so that each slips under mu N and re-anchors; this releases the
internal fore-aft pad tangential force (rod lateral load) on fore-aft slopes.

What this script adds (control design, c2_design.md section 17):
  * REANCHOR as a C2 phase: DONE (first time) -> REANCHOR (wait, move / hold / return / hold2 per step, abort-return)
    -> LEVEL (trim: twist loop rebalances n^T P) -> DONE -> [PROBE if combined judge] -> READY.
    Applied once per lifting cycle when |theta_ground| >= 2.5 deg, lifted, crawler zone off, strokes away from the ends.
    While active: attitude PI, heave, twist loop, F_min guard and the low-load relevel trigger are suspended (the
    sequence owns the command); attitude monitor (> 0.07 deg), other-leg load during the move (load_est < F_min + 5 kN),
    any-leg load during the hold (load_est < F_min) and stroke cap (8 mm) abort the sequence (return the commanded
    strokes to zero, then trim).
  * Stop threshold on the pressure reading (final option set 'H4'): P_stop,k = max(stair_k, 20 kN, F_min + F_band + 10 kN),
    stair 45 / 30 / 20 / 20 kN, margin 10 kN = 5 kN D8 criterion + 4.3 kN max hold-phase drop (0.1 v_max, beta 1.6 GPa)
    + pressure noise; F_band is the C2 state (D5: 13 kN, raised only by the combined-judge probe that follows
    REANCHOR) -> stops 45 / 32.45 / 32.45 / 32.45 kN now. 'F4' (45/45/30.45/30.45, margin 8 kN) and 'G4b' (no F_band
    floor, reaches 20 kN) are the bracketing variants.
  * Rejected: friction-direction-aware floor ('G*' screen variants, see the RA_AWARE comment).
  * 'dyn' option set = the dynamics proposal reproduced inside the state machine (no floor, stair 45/45/30/30/20/20,
    no trim, no aborts) for the regression check against run_pad_tangential_check.C2RA.

Models (import only, nothing modified): plant run_pad_tangential_check.TPlant (= run_mast_flex_c2_check.FlexPlant +
pad tangential bookkeeping: ground-fixed bushing k_t with circular Coulomb cap mu N, YAML k_t or secant k_t(e)),
controller base run_c2_revision.C2R with gain set 'R:BS_hold' (C2 revision R1), loop / delay / ramp / metrics
run_c2_timedomain.run_case. Reduced 6-DoF, crawler layout D, IMU C1, dt 5e-4 s, T = 20 ms, case C mass.

Conventions: body x fwd, y left, z up; roll > 0 left side up, pitch > 0 nose down (floor slope = attitude on the
crawler); legs FL, FR, RL, RR; leg speed > 0 = extension; negative feedback in every C2 channel; SI units inside
(kN / mm / deg only in the outputs). Cylinder force = pressure reading x bore area (head side).

Run (project root, dynamics-dev activated; E-cores 16-27, below-normal priority, BLAS 1 thread):
  conda run -n dynamics-dev python -I 04_scripts/03_control/run_c2_reanchor.py --stage repro    (~1 min)
  conda run -n dynamics-dev python -I 04_scripts/03_control/run_c2_reanchor.py --stage screen   (~1 min, 52 runs)
  conda run -n dynamics-dev python -I 04_scripts/03_control/run_c2_reanchor.py --stage screen2  (~1 min, 51 runs)
  conda run -n dynamics-dev python -I 04_scripts/03_control/run_c2_reanchor.py --stage verify [--variant H4|G4b|F4]
                                                                                   (~4 min each, 202 runs, 12 workers)
  conda run -n dynamics-dev python -I 04_scripts/03_control/run_c2_reanchor.py --stage report   (tables + figures)
Writes 06_analysis/02_control/c2_reanchor.json (one key per stage) and c2_reanchor_{timeseries,summary}.png.
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "01_dynamics"))
sys.path.insert(0, str(HERE))
import run_pad_tangential_check as ptc  # noqa: E402  (imports rmf / rcc / c2t / rcr; patches rcc.Plant in-process)
import run_mast_flex_c2_check as rmf  # noqa: E402
import run_control_comparison as rcc  # noqa: E402
import run_c2_timedomain as c2t  # noqa: E402
import run_c2_revision as rcr  # noqa: E402
import dyn_model as dm  # noqa: E402

OUT_DIR = dm.PROJECT_ROOT / "06_analysis" / "02_control"
OUT_JSON = OUT_DIR / "c2_reanchor.json"
LEGS = dm.LEG_NAMES
DEG = math.pi / 180
F_MIN = 9452.55
F_BAND_D5 = 13e3                 # c2_design.md 10.2 (D5): seal-friction design band at the start
NEED = F_MIN + 5e3               # D8 / R1 criterion on the true cylinder force [N]
R1 = "R:BS_hold"
MASTS = ("rigid", "stiff", "upper", "lower")
RA: dict = {}                    # per-run re-anchoring options (set in run_one, read by C2RN)

# ------------------------------------------------------------------------------------------------ options

RA_OFF = {"enable": False}
RA_FINAL = {                      # common base of the F*/G*/H* option sets (final = H4, c2_design.md 17.2)
    "enable": True, "theta_min_deg": 2.5, "wait_s": 2.0, "speed_frac": 0.1,
    "stair_N": [45e3, 45e3, 30e3, 30e3], "floor_abs_N": 20e3, "floor_margin_N": 8e3,
    "targets": ["RR", "RL"], "hold_s": 1.0, "hold2_s": 1.0,
    "other_margin_N": 5e3, "max_step_stroke_m": 8e-3, "att_abort_deg": 0.07, "stroke_end_margin_m": 0.01,
    "other_low": "abort", "trim": True,
}
RA_DYN = {                        # dynamics proposal as run in pad_tangential_check (reanchor3 'stair')
    "enable": True, "theta_min_deg": 0.0, "wait_s": 2.0, "speed_frac": 0.1,
    "stair_N": [45e3, 45e3, 30e3, 30e3, 20e3, 20e3], "floor_abs_N": 0.0, "floor_margin_N": -1e9,
    "targets": ["RR", "RL"], "hold_s": 1.0, "hold2_s": 1.0,
    "other_margin_N": 5e3, "max_step_stroke_m": 0.02, "att_abort_deg": None, "stroke_end_margin_m": 0.0,
    "other_low": "stop_step", "other_use_reading": True, "trim": False,
}
VARIANTS = {
    "off": RA_OFF,
    "dyn": RA_DYN,
    "dyn_trim": dict(RA_DYN, trim=True),
    "F4": RA_FINAL,                                                    # 45/45/30/30 with the floor (30.45 kN)
    "F6": dict(RA_FINAL, stair_N=[45e3, 45e3, 30e3, 30e3, 30e3, 30e3]),
    "F2": dict(RA_FINAL, stair_N=[30e3, 30e3]),
    "F4v05": dict(RA_FINAL, speed_frac=0.05),
    "F4_floor20": dict(RA_FINAL, floor_margin_N=-1e9, stair_N=[45e3, 45e3, 30e3, 30e3, 20e3, 20e3]),  # after F_band validated small
    "F4_force": dict(RA_FINAL, theta_min_deg=0.0),                    # applied regardless of slope (negative test)
}
# H4 = final proposal: stair 45 / 30 / 20 / 20 kN, every step floored at max(20 kN, F_min + F_band + 10 kN)
# (10 kN = 5 kN D8 criterion + 4.3 kN max hold-phase drop + 3 sigma pressure noise; with the D5 start value F_band 13 kN
# the effective stops are 45 / 32.45 / 32.45 / 32.45 kN; once the probe has
# validated a small band, F_band <= 0.55 kN, they become 45 / 30 / 20 / 20 kN = G4b), hold guard (any leg < F_min).
VARIANTS["H4"] = dict(RA_FINAL, stair_N=[45e3, 30e3, 20e3, 20e3], hold_guard=True, floor_margin_N=10e3)
VARIANTS["H4_force"] = dict(VARIANTS["H4"], theta_min_deg=0.0)
# REJECTED (c2_design.md 17.3): friction-direction-aware floor. Assumed the target only retracts, so once its reading has dropped by
# >= 2 F_band during the move the seal friction is fully developed in the retract direction and the true force is
# >= reading; the floor is then F_min + 5 kN + D_m (D_m 5 kN hold-phase drop allowance) -> 20 kN. Until then the
# conservative D5 floor F_min + F_band + 8 kN applies.
# Wrong in the twist mode: the other three legs also move and change the target load while its rod sticks, so the
# reading drop is shared between the oil and the pad springs (F_s 12 kN, nose-down 3.5: reading 82.8 -> 43.2 kN,
# true 71.1 -> 38.7 kN, friction offset still -4.6 kN = true < reading). Kept only as the 'G*' screen variants.
RA_AWARE = dict(RA_FINAL, stair_N=[45e3, 45e3, 30e3, 30e3, 20e3, 20e3], floor_mode="aware", aware_margin_N=10e3,
                floor_abs_N=20e3)
VARIANTS.update({
    "G6": RA_AWARE,
    "G4": dict(RA_AWARE, stair_N=[30e3, 30e3, 20e3, 20e3]),
    "G4b": dict(RA_AWARE, stair_N=[45e3, 30e3, 20e3, 20e3]),
    "G6_force": dict(RA_AWARE, theta_min_deg=0.0),
    "G4b_force": dict(RA_AWARE, stair_N=[45e3, 30e3, 20e3, 20e3], theta_min_deg=0.0),
})
FINAL = "H4"
ALT = "G4b"                      # same stair without the F_band floor = H4 after the band is validated <= 2.55 kN

SLOPES = {"flat": (0.0, 0.0), "pitch+2.0": (0.0, 2.0), "pitch-2.0": (0.0, -2.0),
          "pitch+2.5": (0.0, 2.5), "pitch-2.5": (0.0, -2.5), "pitch+3.0": (0.0, 3.0), "pitch-3.0": (0.0, -3.0),
          "pitch+3.2": (0.0, 3.2), "pitch-3.2": (0.0, -3.2), "pitch+3.5": (0.0, 3.5), "pitch-3.5": (0.0, -3.5),
          "pitch+3.7": (0.0, 3.7), "roll+5.5": (5.5, 0.0), "roll-5.5": (-5.5, 0.0),
          "r+1.1p+2.8": (1.1, 2.8), "r-1.1p-2.8": (-1.1, -2.8), "r+2.75p+1.75": (2.75, 1.75)}


# ------------------------------------------------------------------------------------------------ controller


class C2RN(rcr.C2R):
    """C2 revision R1 + REANCHOR phase (module docstring). ra_log uses the event format of
    run_pad_tangential_check.C2RA so that ptc.reanchor_metrics can be reused."""
    name = "C2RN"

    def __init__(self, ctx, contact="pressure"):
        super().__init__(ctx, contact=contact)
        self.ra = None                    # None = not decided yet; dict = active / finished
        self.ra_log = []                  # C2RA-compatible step events (first entry = 'start')
        self.ra_events = []               # decision / wait / abort events
        self.att_ground = None

    def on_touch(self, m):
        self.att_ground = (float(self.phi_f), float(self.th_f))      # on the crawler: filtered attitude = floor slope
        super().on_touch(m)

    def _log(self, t, what, **kw):
        self.ra_log.append(dict(t=round(float(t), 4), what=what, **kw))

    def _ev(self, t, what, **kw):
        self.ra_events.append(dict(t=round(float(t), 4), what=what, **kw))

    def _prelude(self, m, t):
        self.t = t
        self.filt(m)
        raw = self.c.clearance_est(m["x"])
        if "s" in m or rcc.CA["rule_src"] != "s_lpfP":
            self._rule_estimate(m, raw)        # keep the crawler-rule pressure low-pass warm

    def _eligible(self, m):
        sp = RA
        if not sp.get("enable"):
            return "disabled"
        if self.att_ground is None or abs(self.att_ground[1]) < sp["theta_min_deg"] * DEG - 1e-12:
            return "theta_below_min"
        if not self.lifted:
            return "not_lifted"
        if self.zone:
            return "crawler_zone"
        if getattr(self, "fault", False):
            return "fault"
        mg = sp["stroke_end_margin_m"]
        s = m["s"] if "s" in m else m["x"]
        if mg > 0 and ((s < mg).any() or (s > self.c.smax - mg).any()):
            return "stroke_margin"
        return None

    def p_stop(self, k):
        sp = RA
        st = sp["stair_N"][min(k, len(sp["stair_N"]) - 1)]
        if sp.get("floor_mode") == "aware":
            return max(st, sp["floor_abs_N"], self.c.F_min + sp["aware_margin_N"])
        return max(st, sp["floor_abs_N"], self.c.F_min + self.fs_band + sp["floor_margin_N"])

    def p_stop_conservative(self):
        return self.c.F_min + self.fs_band + RA_FINAL["floor_margin_N"]

    def update(self, m, t):
        if self.ra is not None and self.ra["st"] != "finished":
            self._prelude(m, t)
            return self._ra_step(m, t)
        if self.ra is None and self.done and not self.ready and self.phase == "level":
            why = self._eligible(m)
            if why is None:
                self._prelude(m, t)
                self.ra = {"st": "wait", "t0": t, "k": 0, "cum": np.zeros(4), "outcome": None,
                           "P_stop_N": [self.p_stop(k) for k in range(len(RA["stair_N"]))]}
                self._ev(t, "wait", theta_ground_deg=round(self.att_ground[1] / DEG, 3),
                         P_stop_kN=[round(v / 1e3, 2) for v in self.ra["P_stop_N"]], F_band_kN=self.fs_band / 1e3)
                return self._ra_step(m, t)
            self.ra = {"st": "finished", "outcome": "skipped:" + why}
            self._ev(t, "skip", reason=why)
        return super().update(m, t)

    def _finish(self, t, outcome):
        ra = self.ra
        ra["st"] = "finished"; ra["outcome"] = outcome
        self._log(t, "end")
        self._ev(t, "finish", outcome=outcome)
        if RA.get("trim", True):        # back to LEVEL: twist loop rebalances n^T P, attitude PI trims
            self.done = False; self.ready = False; self.ok_since = None; self.probe = None
        return np.zeros(4)

    def _return_cmd(self, ra, v):
        mx = float(np.max(np.abs(ra["cum"])))
        if mx < 1e-10:
            return None
        lam = min(1.0, mx / (v * rcc.T_CTRL))
        u = -ra["cum"] / mx * v * lam
        ra["cum"] = ra["cum"] + u * rcc.T_CTRL
        return u

    def _ra_step(self, m, t):
        ra = self.ra; c = self.c; sp = RA
        v = sp["speed_frac"] * c.vmax
        st = ra["st"]
        if st == "wait":
            if self._att_bad():
                return self._finish(t, "aborted:attitude_wait")
            # C2RA compatibility: the wait ends on the first period with t >= t0 + wait (same period starts 'move')
            if t < ra["t0"] + sp["wait_s"]:
                return np.zeros(4)
            ra["st"] = "move"; ra["t_step"] = t
            self._log(t, "start", k=0)
            st = "move"
        if st == "abort_return":
            u = self._return_cmd(ra, v)
            if u is None:
                return self._finish(t, ra["abort_reason"])
            return u
        steps = [sp["targets"][k % len(sp["targets"])] for k in range(len(sp["stair_N"]))]
        if ra["k"] >= len(steps):
            return self._finish(t, "completed")
        tgt = LEGS.index(steps[ra["k"]])
        n = np.asarray(c.n, float)
        dirv = -math.copysign(1.0, n[tgt]) * n / np.max(np.abs(n))
        P = m["P"]
        P_stop = ra["P_stop_N"][ra["k"]]
        if st == "move":
            if ra.get("P_start_k") != ra["k"]:
                ra["P_start_k"] = ra["k"]; ra["P_start"] = float(P[tgt])
            if sp.get("floor_mode") == "aware" and ra["P_start"] - P[tgt] < 2.0 * self.fs_band:
                P_stop = max(P_stop, self.p_stop_conservative())   # friction may not be in the retract direction yet
        # supervisory aborts (not in the 'dyn' reproduction)
        if sp.get("att_abort_deg") is not None and self._att_bad():
            return self._abort(t, "aborted:attitude")
        if st == "move":
            others = [j for j in range(4) if j != tgt]
            Lo = P if sp.get("other_use_reading") else self.load_est(m)
            low = min(Lo[j] for j in others) < c.F_min + sp["other_margin_N"]
            cap = np.max(np.abs(ra["cum"])) >= sp["max_step_stroke_m"]
            if low and sp["other_low"] == "abort":
                return self._abort(t, "aborted:other_low")
            if cap and sp["other_low"] == "abort":
                return self._abort(t, "aborted:stroke_cap")
            if P[tgt] <= P_stop or cap or low:
                ra["st"] = "hold"; ra["t0"] = t
                self._log(t, "hold", k=ra["k"], leg=LEGS[tgt], P_kN=round(float(P[tgt]) / 1e3, 2),
                          reason="P_stop" if P[tgt] <= P_stop else ("cap" if cap else "guard"),
                          cum_mm=(ra["cum"] * 1e3).round(3).tolist())
                return np.zeros(4)
            u = dirv * v
            ra["cum"] = ra["cum"] + u * rcc.T_CTRL
            return u
        if st == "hold":
            if sp.get("hold_guard") and float(self.load_est(m).min()) < c.F_min + sp.get("hold_guard_margin_N", 0.0):
                return self._abort(t, "aborted:hold_low")     # any leg (target included) below F_min (hard)
            if t - ra["t0"] >= sp["hold_s"] - 1e-9:
                ra["st"] = "return"; self._log(t, "return", k=ra["k"])
            return np.zeros(4)
        if st == "return":
            u = self._return_cmd(ra, v)
            if u is None:
                ra["st"] = "hold2"; ra["t0"] = t; self._log(t, "hold2", k=ra["k"])
                return np.zeros(4)
            return u
        if st == "hold2":
            if t - ra["t0"] >= sp["hold2_s"] - 1e-9:
                ra["k"] += 1; ra["st"] = "move"; ra["cum"] = np.zeros(4); ra["t0"] = t
                self._log(t, "next", k=ra["k"])
            return np.zeros(4)
        raise RuntimeError(st)

    def _att_bad(self):
        lim = RA.get("att_abort_deg")
        return lim is not None and max(abs(self.phi_s), abs(self.th_s)) > lim * DEG

    def _abort(self, t, reason):
        ra = self.ra
        ra["st"] = "abort_return"; ra["abort_reason"] = reason
        self._ev(t, "abort", reason=reason, k=ra["k"], cum_mm=(ra["cum"] * 1e3).round(3).tolist())
        u = self._return_cmd(ra, RA["speed_frac"] * self.c.vmax)
        if u is None:
            return self._finish(t, reason)
        return u


# ------------------------------------------------------------------------------------------------ one run


def _hist(pl):
    return np.array(pl.hist_t), np.array(pl.hist)


def ra_metrics(S, r, pl, ctrl):
    """Re-anchoring metrics from the 1 ms plant record (hist = acc[11:45]: Fl 0:4, Fmin 13:17, Ft_x 17:21,
    Ft_y 21:25) and the 20 ms series (true attitude)."""
    t, H = _hist(pl)
    Fl = H[:, 0:4]; fmin = H[:, 13:17]; Fm = np.hypot(H[:, 17:21], H[:, 21:25])
    Wr = pl.Wr
    ts = np.asarray(S["t"]); att = np.degrees(np.column_stack([S["phi"], S["theta"]]))
    out = {"outcome": None if ctrl.ra is None else ctrl.ra.get("outcome"), "events": ctrl.ra_events[:8],
           "theta_ground_deg": None if ctrl.att_ground is None else round(ctrl.att_ground[1] / DEG, 3)}
    tl = r.get("t_crawler_liftoff_s")
    post = t >= (tl if tl is not None else 0.0)
    out["min_true_cyl_post_liftoff_substep_kN"] = round(float((fmin[post] - Wr).min()) / 1e3, 2)
    out["Ft_final_kN"] = (Fm[-1] / 1e3).round(2).tolist()
    out["Fcyl_final_kN"] = ((Fl[-1] - Wr) / 1e3).round(2).tolist()
    tdone = r.get("t_done_s")
    if tdone is not None:
        j = int(np.clip(np.searchsorted(t, tdone - 1e-9), 0, len(t) - 1))
        out["Ft_at_done_kN"] = (Fm[j] / 1e3).round(2).tolist()
    if ctrl.ra_log:
        t0 = ctrl.ra_log[0]["t"]
        tend = [e["t"] for e in ctrl.ra_log if e["what"] == "end"]
        tend = tend[0] if tend else ts[-1]
        w = (t >= t0) & (t <= tend); ws = (ts >= t0) & (ts <= tend)
        pre = (ts >= t0 - 0.5) & (ts <= t0)
        att0 = att[pre].mean(axis=0)
        j0 = int(np.clip(np.searchsorted(t, t0 - 1e-9), 0, len(t) - 1))
        out["t_start_s"] = t0; out["t_end_s"] = tend; out["duration_s"] = round(tend - t0, 2)
        out["Ft0_kN"] = (Fm[j0] / 1e3).round(2).tolist()
        out["Fcyl0_kN"] = ((Fl[j0] - Wr) / 1e3).round(2).tolist()
        out["Ft_max_during_kN"] = (Fm[w].max(axis=0) / 1e3).round(2).tolist()
        out["min_true_cyl_during_kN"] = round(float((fmin[w] - Wr).min()) / 1e3, 2)
        out["min_true_leg_during"] = LEGS[int(np.argmin((fmin[w] - Wr).min(axis=0)))]
        out["max_true_cyl_during_kN"] = round(float((Fl[w] - Wr).max()) / 1e3, 2)
        out["max_att_dev_deg"] = (np.abs(att[ws] - att0).max(axis=0)).round(4).tolist()
        out["max_abs_att_during_deg"] = round(float(np.abs(att[ws]).max()), 4)
        f0 = float(Fm[j0].max()); f1 = float(Fm[-1].max())
        out["Ft_maxleg_start_kN"] = round(f0 / 1e3, 2); out["Ft_maxleg_final_kN"] = round(f1 / 1e3, 2)
        out["Ft_maxleg_reduction"] = round(1.0 - f1 / f0, 4) if f0 > 0 else None
        try:
            det = ptc.reanchor_metrics(S, r, pl, ctrl)
            out["steps"] = [{k: s[k] for k in ("k", "leg", "reason", "P_stop_reading_kN", "stroke_mm", "duration_s",
                                               "Ft_after_kN", "min_true_cyl_kN", "min_true_cyl_per_leg_kN",
                                               "min_cyl_by_phase", "max_att_dev_deg")} for s in det["steps"]]
        except Exception as e:  # noqa: BLE001
            out["steps_error"] = repr(e)
    return out


def run_one(case):
    """case: dict(id, group, level, slope, mast, gainset, seed, beta, Fs, contact, variant, kt_mode, ctrl)."""
    case = dict(case)
    cfg = {"record": True}
    mast = case.get("mast", "rigid")
    if mast != "rigid":
        cfg["mast_eq"] = ptc.eqs()[(case["level"], mast)]
    rmf.CONFIG.clear(); rmf.CONFIG.update(cfg)
    ptc.RCFG.clear(); ptc.RCFG["case_id"] = case["id"]
    roll, pitch = SLOPES[case["slope"]]
    if case.get("kt_mode", "yaml") == "ext":
        ext = ptc.kin_internal(case["level"], roll, pitch, "ext")["levelled_ext_m"]
        ptc.RCFG["kt_per_pad"] = ptc.kt_of_ext(ext).tolist()
    if "mu" in case:
        cfg["mu_pad"] = float(case["mu"])
        rmf.CONFIG["mu_pad"] = cfg["mu_pad"]
    var = case.get("variant", "off")
    RA.clear(); RA.update(VARIANTS[var]); RA.update(case.get("ra_over", {}))
    use_c2ra = case.get("ctrl") == "C2RA"
    if use_c2ra:                       # the dynamics implementation itself (regression anchor)
        ptc.RCFG["reanchor"] = {"wait_s": 2.0, "speed_frac": RA_DYN["speed_frac"], "P_stop_N": list(RA_DYN["stair_N"]),
                                "hold_s": 1.0, "hold2_s": 1.0, "max_stroke_m": 0.02,
                                "steps": ["RR", "RL", "RR", "RL", "RR", "RL"], "mode": "twist"}
    rcc.Plant = ptc.TPlant; rcc.Sensors = rcr.SensorsS
    c2t.C2D = ptc.C2RA if use_c2ra else C2RN
    rcc.CA.update(c2t.OPTION_DEFAULTS); rcc.CA.update(c2t.GAINSETS[case.get("gainset", R1)])
    rcc.CA["Fs_band_N"] = float(case.get("F_band", F_BAND_D5))
    rcc.T_HOLD = float(case.get("t_hold", 10.0 if not use_c2ra else 2.0 + 6 * (2 * 0.004 / (0.1 * 0.022667) + 2.0) + 15.0))
    t0 = time.perf_counter()
    try:
        r = c2t.run_case(level=case["level"], roll=roll, pitch=pitch, beta=case.get("beta", 1.0e9),
                         Fs=case.get("Fs", 0.0), contact=case.get("contact", "pressure"), seed=case.get("seed", 12345),
                         keep_series=True)
        pl = rmf.LAST["plant"]; ctrl = rmf.LAST["ctrl"]
        if not isinstance(pl, ptc.TPlant) or pl.case_id != case["id"]:
            raise RuntimeError("plant identity check failed")
        if type(ctrl) is not (ptc.C2RA if use_c2ra else C2RN):
            raise RuntimeError("controller identity check failed")
        if pl.flex != (0 if mast == "rigid" else 1):
            raise RuntimeError("mast flag mismatch")
        if "mu" in case and abs(pl.mu_pad - float(case["mu"])) > 1e-12:
            raise RuntimeError("mu_pad not applied")
        S = r.pop("_series")
        out = {k: r.get(k) for k in ("t_touch_s", "t_crawler_liftoff_s", "t_done_s", "t_ready_s", "min_true_cyl_force_kN",
                                     "min_true_leg", "ss_true_att_deg_maxabs", "max_pressure_bar", "fails", "events",
                                     "levelled_loads_true_kN", "levelled_twist_load_kN", "probe_rounds", "probe_time_s",
                                     "probe_last", "guard_active_s")}
        out.update(rmf.extra_metrics(S, r, pl))
        if r.get("t_ready_s") is not None and r.get("t_touch_s") is not None:
            out["t_level_after_touch_s"] = round(r["t_ready_s"] - r["t_touch_s"], 2)
        if use_c2ra:
            det = ptc.reanchor_metrics(S, r, pl, ctrl)
            out["ra"] = {"steps": [{k: s[k] for k in ("k", "leg", "reason", "P_stop_reading_kN", "stroke_mm",
                                                      "Ft_after_kN", "min_true_cyl_kN")} for s in det["steps"]],
                         "log": ctrl.ra_log}
        else:
            out["ra"] = ra_metrics(S, r, pl, ctrl)
            out["ra"]["log"] = ctrl.ra_log
            out["fs_band_end_kN"] = ctrl.fs_band / 1e3
        if case.get("keep_series"):
            t, H = _hist(pl)
            out["_series"] = {"t": t, "H": H, "S": S}
    except Exception as e:  # noqa: BLE001
        import traceback
        out = {"error": repr(e), "tb": traceback.format_exc()[-1500:]}
    finally:
        rcc.T_HOLD = 10.0
    out.update({k: case.get(k) for k in ("id", "group", "level", "slope", "mast", "gainset", "seed", "variant",
                                          "contact", "kt_mode")})
    out["beta_GPa"] = case.get("beta", 1.0e9) / 1e9; out["Fs_kN"] = case.get("Fs", 0.0) / 1e3
    out["mu_pad"] = case.get("mu", 0.5); out["ra_over"] = case.get("ra_over")
    out["wall_s"] = round(time.perf_counter() - t0, 1)
    return out


def judge(r):
    """Pass / fail of one run (c2_design.md 17.4): attitude deviation during REANCHOR <= 0.1 deg, steady-state
    attitude <= 0.2 deg, true cylinder force after lift-off >= F_min + 5 kN (substep), READY, no R1 fail flag."""
    if "error" in r:
        return ["error"]
    f = list(r.get("fails") or [])
    ra = r.get("ra", {})
    if r.get("t_ready_s") is None:
        f.append("not_ready")
    ms = r.get("min_true_cyl_force_substep_kN")
    if ms is not None and ms * 1e3 < NEED:
        f.append("min_force<Fmin+5")
    dev = ra.get("max_att_dev_deg")
    if dev is not None and max(dev) > 0.1:
        f.append("att_dev>0.1")
    ss = r.get("ss_true_att_deg_maxabs")
    if ss is not None and ss > 0.2:
        f.append("ss>0.2")
    return sorted(set(f))


# ------------------------------------------------------------------------------------------------ case lists


def mk(cid, group, level, slope, variant, mast="rigid", **kw):
    c = {"id": cid, "group": group, "level": level, "slope": slope, "mast": mast, "variant": variant,
         "gainset": R1, "seed": 12345}
    c.update(kw)
    return c


def cases_for(stage, variant=None):
    variant = variant or FINAL
    C = []
    if stage == "repro":
        C.append(mk("repro|C2RA", "repro", "top", "pitch+3.5", "dyn", ctrl="C2RA"))
        C.append(mk("repro|C2RN_dyn", "repro", "top", "pitch+3.5", "dyn"))
        C.append(mk("repro|C2RA|pitch-3.5", "repro", "top", "pitch-3.5", "dyn", ctrl="C2RA"))
        C.append(mk("repro|C2RN_dyn|pitch-3.5", "repro", "top", "pitch-3.5", "dyn"))
        C.append(mk("repro|C2RN_off", "repro", "top", "pitch+3.5", "off"))
        return C
    if stage == "screen":
        for sl in ("pitch+3.5", "pitch-3.5", "pitch+3.2", "roll+5.5"):
            for var in ("off", "dyn_trim", "F4", "F6", "F2", "F4v05", "F4_floor20"):
                v = "F4_force" if (sl == "roll+5.5" and var == "F4") else var
                for Fs in (0.0, 12e3):
                    if var == "F4_floor20" and Fs > 0:
                        continue
                    C.append(mk(f"scr|{sl}|{v}|Fs{Fs / 1e3:g}", "screen", "top", sl, v, Fs=Fs))
        return C
    if stage == "screen2":           # friction-aware floor variants, mu and slope-angle sensitivity
        for sl in ("pitch+3.5", "pitch-3.5", "pitch+3.2", "pitch+2.5", "pitch-2.5"):
            for var in ("G6", "G4", "G4b"):
                for Fs in (0.0, 12e3):
                    C.append(mk(f"scr2|{sl}|{var}|Fs{Fs / 1e3:g}", "screen2", "top", sl, var, Fs=Fs))
        for sl in ("pitch+2.5", "pitch-2.5", "pitch+2.0"):
            for var in ("off", "F4_force"):
                C.append(mk(f"scr2|{sl}|{var}|Fs0", "screen2", "top", sl, var))
        C.append(mk("scr2|pitch+2.0|G6_force|Fs0", "screen2", "top", "pitch+2.0", "G6_force"))
        for mu in (0.3, 0.7):
            for var in ("off", "G6", "F4"):
                for sl in ("pitch+3.5", "pitch-3.5"):
                    C.append(mk(f"scr2|{sl}|{var}|mu{mu}", "screen2_mu", "top", sl, var, mu=mu))
        for var in ("G6", "F4"):     # 0.25 v_max sanity (dynamics: abrupt slip release)
            C.append(mk(f"scr2|pitch+3.5|{var}|v0.25", "screen2_speed", "top", "pitch+3.5", var, ra_over={"speed_frac": 0.25}))
        return C
    if stage == "verify":
        V = variant
        # (1) base matrix: 3 levels x slopes, rigid, d1, seed 12345 -- with and without REANCHOR
        sl1 = ("flat", "pitch+2.0", "pitch-2.0", "pitch+2.5", "pitch-2.5", "pitch+3.0", "pitch-3.0", "pitch+3.2",
               "pitch-3.2", "pitch+3.5", "pitch-3.5", "pitch+3.7", "roll+5.5", "r+1.1p+2.8", "r-1.1p-2.8")
        for lv in dm.LEVELS:
            for sl in sl1:
                for var in ("off", V):
                    C.append(mk(f"base|{lv}|{sl}|{var}", "base", lv, sl, var))
        fa = ("pitch+3.5", "pitch-3.5", "pitch+3.2", "pitch-3.2", "pitch+3.7", "r+1.1p+2.8")
        # (2) flexible masts (equivalent 1-mode), top, d1
        for mast in MASTS[1:]:
            for sl in fa:
                C.append(mk(f"mast|{mast}|{sl}", "mast", "top", sl, V, mast))
        # (3) delay 0, all masts
        for mast in MASTS:
            for sl in ("pitch+3.5", "pitch-3.5", "pitch+3.2", "pitch+3.7"):
                C.append(mk(f"d0|{mast}|{sl}", "delay0", "top", sl, V, mast, gainset=R1 + "_d0"))
        # (4) beta 0.69 / 1.6 GPa
        for b in (0.69e9, 1.6e9):
            for mast in ("rigid", "stiff"):
                for sl in ("pitch+3.5", "pitch-3.5", "pitch+3.2", "pitch+2.5"):
                    C.append(mk(f"beta|{b / 1e9:g}|{mast}|{sl}", "beta", "top", sl, V, mast, beta=b))
        # (5) seal friction 0/2/5/12 kN x judge (pressure / combined)
        for Fs in (0.0, 2e3, 5e3, 12e3):
            for ct in ("pressure", "combined"):
                for sl in ("pitch+3.5", "pitch-3.5", "pitch+3.2"):
                    C.append(mk(f"Fs|{Fs / 1e3:g}|{ct}|{sl}", "friction", "top", sl, V, Fs=Fs, contact=ct))
                if Fs == 12e3:
                    C.append(mk(f"Fs|{Fs / 1e3:g}|{ct}|pitch+3.5|stiff", "friction", "top", "pitch+3.5", V, "stiff",
                                Fs=Fs, contact=ct))
        # (6) seeds, all masts
        for s in (1, 2):
            for mast in MASTS:
                for sl in ("pitch+3.5", "pitch-3.5"):
                    C.append(mk(f"seed|{s}|{mast}|{sl}", "seed", "top", sl, V, mast, seed=12345 + s))
        # (7) secant k_t(e) (lower rod lateral stiffness, best estimate) and middle / bottom with masts
        for mast in ("rigid", "stiff"):
            for sl in ("pitch+3.5", "pitch-3.5", "pitch+3.2"):
                C.append(mk(f"ktext|{mast}|{sl}", "ktext", "top", sl, V, mast, kt_mode="ext"))
        for lv in ("middle", "bottom"):
            for mast in ("stiff", "lower"):
                for sl in ("pitch+3.5", "pitch-3.5"):
                    C.append(mk(f"lvmast|{lv}|{mast}|{sl}", "level_mast", lv, sl, V, mast))
        # (8) negative test: forced on roll-dominated slopes (not applied by the rule)
        for sl in ("roll+5.5", "roll-5.5", "r+2.75p+1.75"):
            for Fs in (0.0, 12e3):
                C.append(mk(f"force|{sl}|Fs{Fs / 1e3:g}", "forced", "top", sl, V + "_force", Fs=Fs))
        return C
    raise ValueError(stage)


# ------------------------------------------------------------------------------------------------ io / pool


def load_out():
    if OUT_JSON.exists():
        return json.loads(OUT_JSON.read_text(encoding="utf-8"))
    return {}


def save_out(d):
    OUT_JSON.write_text(json.dumps(d, indent=1, default=float), encoding="utf-8")


def run_pool(cases, workers):
    r0 = run_one(dict(cases[0]))          # numba compile in the main process first
    if len(cases) == 1:
        return [r0]
    from multiprocessing import Pool
    with Pool(workers) as pool:
        rest = pool.map(run_one, cases[1:], chunksize=1)
    return [r0] + rest


# ------------------------------------------------------------------------------------------------ report


def repro_check(d):
    """C2RN 'dyn' option set vs run_pad_tangential_check.C2RA (same plant, same seed): per-step results must be
    identical; C2RA in this process vs the stored dynamics result (reanchor3 'stair')."""
    runs = {r["id"]: r for r in d["repro"]["runs"]}
    out = {}
    for a, b in (("repro|C2RA", "repro|C2RN_dyn"), ("repro|C2RA|pitch-3.5", "repro|C2RN_dyn|pitch-3.5")):
        sa = runs[a]["ra"]["steps"]; sb = runs[b]["ra"]["steps"]
        diffs = []
        for x, y in zip(sa, sb, strict=False):
            for k in ("P_stop_reading_kN", "Ft_after_kN", "min_true_cyl_kN", "stroke_mm"):
                xa = np.asarray(x[k] if x[k] is not None else np.nan, float)
                ya = np.asarray(y[k] if y[k] is not None else np.nan, float)
                if xa.shape == ya.shape and xa.size:
                    diffs.append(float(np.nanmax(np.abs(xa - ya))))
        la = [(e["t"], e["what"]) for e in runs[a]["ra"]["log"]]
        lb = [(e["t"], e["what"]) for e in runs[b]["ra"]["log"]]
        out[b] = {"n_steps": [len(sa), len(sb)], "max_abs_diff_step_metrics": max(diffs) if diffs else None,
                  "log_identical": la == lb}
    try:
        dy = json.loads((dm.PROJECT_ROOT / "06_analysis" / "00_dynamics" / "pad_tangential_check.json").read_text(encoding="utf-8"))
        ref = [r for r in dy["reanchor3"]["runs"] if r["id"] == "ra3|twist|V:pitch+3.5|rigid|yaml|v0.1|stair"][0]
        rs = ref["reanchor"]["steps"]; ms = runs["repro|C2RA"]["ra"]["steps"]
        dd = [float(np.max(np.abs(np.asarray(x["Ft_after_kN"]) - np.asarray(y["Ft_after_kN"])))) for x, y in zip(rs, ms, strict=False)]
        dm_ = [abs(x["min_true_cyl_kN"] - y["min_true_cyl_kN"]) for x, y in zip(rs, ms, strict=False) if x["min_true_cyl_kN"] is not None]
        out["C2RA_here_vs_stored_dynamics"] = {"max_abs_diff_Ft_after_kN": max(dd), "max_abs_diff_min_cyl_kN": max(dm_)}
    except Exception as e:  # noqa: BLE001
        out["C2RA_here_vs_stored_dynamics"] = {"error": repr(e)}
    return out


def cap_bound(d, mu=0.5):
    """Independent quasi-static bound: after a target pad was held at true normal force N it can carry at most
    mu N tangentially; with the friction sign of a retracting rod, N <= P_stop + F_s + W_rod (reading-based stop).
    Rear-pad final tangential force must not exceed mu (P_stop_last + F_s + W_rod) + elastic reload share."""
    out = []
    for st in [k for k in d if k.startswith(("screen", "verify"))]:
        for r in d.get(st, {}).get("runs", []):
            ra = r.get("ra", {})
            if not ra.get("steps") or "error" in r or ra.get("outcome") != "completed":
                continue
            last = {}
            for s in ra["steps"]:
                if s["leg"] is not None:
                    last[s["leg"]] = s["P_stop_reading_kN"]
            Wr = 1.0472
            for leg in ("RL", "RR"):
                if leg in last:
                    bound = float(r.get("mu_pad", mu)) * (last[leg] + r["Fs_kN"] + Wr)
                    out.append({"id": r["id"], "leg": leg, "Ft_final_kN": ra["Ft_final_kN"][LEGS.index(leg)],
                                "bound_kN": round(bound, 2)})
    if not out:
        return {}
    ratio = [o["Ft_final_kN"] / o["bound_kN"] for o in out]
    worst = out[int(np.argmax(ratio))]
    return {"n": len(out), "max_ratio_final_over_bound": round(float(max(ratio)), 3),
            "median_ratio": round(float(np.median(ratio)), 3), "worst": worst}


def summarize(runs):
    rows = []
    for r in runs:
        ra = r.get("ra", {})
        rows.append({"id": r["id"], "fails": judge(r), "outcome": ra.get("outcome"),
                     "min_substep_kN": r.get("min_true_cyl_force_substep_kN"),
                     "min_during_kN": ra.get("min_true_cyl_during_kN"), "leg_during": ra.get("min_true_leg_during"),
                     "Ft0_max_kN": ra.get("Ft_maxleg_start_kN"), "Ft_final_max_kN": ra.get("Ft_maxleg_final_kN"),
                     "Ft_final_max_noRA_kN": None if ra.get("Ft_final_kN") is None else round(max(ra["Ft_final_kN"]), 2),
                     "reduction": ra.get("Ft_maxleg_reduction"), "Ft_max_during_kN": ra.get("Ft_max_during_kN"),
                     "att_dev_deg": None if ra.get("max_att_dev_deg") is None else max(ra["max_att_dev_deg"]),
                     "ss_deg": r.get("ss_true_att_deg_maxabs"), "t_level_s": r.get("t_level_after_touch_s"),
                     "ra_s": ra.get("duration_s"), "max_bar": r.get("max_pressure_bar"),
                     "loads_end_kN": r.get("levelled_loads_true_kN"), "twist_end_kN": r.get("levelled_twist_load_kN")})
    return rows


def stage_report(d):
    rep = {}
    if "repro" in d:
        rep["repro"] = repro_check(d)
    for st in ("screen", "screen2"):
        if st in d:
            rep[st] = summarize(d[st]["runs"])
    for vk in [k for k in d if k.startswith("verify")]:
        rep[vk] = verify_report(d[vk]["runs"], d[vk].get("variant", FINAL))
    rep["cap_bound"] = cap_bound(d)
    return rep


def verify_report(runs, VAR):
    rep = {"rows": summarize(runs)}
    if True:
        byid = {r["id"]: r for r in runs}
        # base pairs: with / without REANCHOR
        pairs = []
        for lv in dm.LEVELS:
            for sl in SLOPES:
                a = byid.get(f"base|{lv}|{sl}|off"); b = byid.get(f"base|{lv}|{sl}|{VAR}")
                if a is None or b is None or "error" in a or "error" in b:
                    continue
                pairs.append({"level": lv, "slope": sl, "applied": b["ra"].get("outcome"),
                              "Ft_final_off_kN": a["ra"]["Ft_final_kN"], "Ft_final_ra_kN": b["ra"]["Ft_final_kN"],
                              "Ft_max_off_kN": round(max(a["ra"]["Ft_final_kN"]), 2),
                              "Ft_max_ra_kN": round(max(b["ra"]["Ft_final_kN"]), 2),
                              "min_off_kN": a.get("min_true_cyl_force_substep_kN"),
                              "min_ra_kN": b.get("min_true_cyl_force_substep_kN"),
                              "t_level_off_s": a.get("t_level_after_touch_s"), "t_level_ra_s": b.get("t_level_after_touch_s"),
                              "fails_off": judge(a), "fails_ra": judge(b)})
        rep["base_pairs"] = pairs
        groups = {}
        for r in runs:
            if r.get("variant") == "off":
                continue
            g = r["group"]
            ra = r.get("ra", {})
            e = groups.setdefault(g, {"n": 0, "n_fail": 0, "fails": [], "applied": 0, "min_substep_kN": None,
                                      "min_during_kN": None, "att_dev_max_deg": 0.0, "ss_max_deg": 0.0,
                                      "reduction_min": None, "reduction_max": None, "Ft_final_max_kN": None,
                                      "ra_s_max": 0.0, "max_bar": 0.0, "outcomes": {}})
            e["n"] += 1
            f = judge(r)
            if f:
                e["n_fail"] += 1; e["fails"].append((r["id"], f))
            oc = ra.get("outcome"); e["outcomes"][str(oc)] = e["outcomes"].get(str(oc), 0) + 1
            if oc == "completed":
                e["applied"] += 1
            ms = r.get("min_true_cyl_force_substep_kN")
            if ms is not None:
                e["min_substep_kN"] = ms if e["min_substep_kN"] is None else min(e["min_substep_kN"], ms)
            md = ra.get("min_true_cyl_during_kN")
            if md is not None:
                e["min_during_kN"] = md if e["min_during_kN"] is None else min(e["min_during_kN"], md)
            if ra.get("max_att_dev_deg"):
                e["att_dev_max_deg"] = max(e["att_dev_max_deg"], max(ra["max_att_dev_deg"]))
            if r.get("ss_true_att_deg_maxabs") is not None:
                e["ss_max_deg"] = max(e["ss_max_deg"], r["ss_true_att_deg_maxabs"])
            rd = ra.get("Ft_maxleg_reduction")
            if rd is not None and oc == "completed":
                e["reduction_min"] = rd if e["reduction_min"] is None else min(e["reduction_min"], rd)
                e["reduction_max"] = rd if e["reduction_max"] is None else max(e["reduction_max"], rd)
                ff = ra["Ft_maxleg_final_kN"]
                e["Ft_final_max_kN"] = ff if e["Ft_final_max_kN"] is None else max(e["Ft_final_max_kN"], ff)
            if ra.get("duration_s"):
                e["ra_s_max"] = max(e["ra_s_max"], ra["duration_s"])
            if r.get("max_pressure_bar"):
                e["max_bar"] = max(e["max_bar"], r["max_pressure_bar"])
        rep["groups"] = groups
        rep["n"] = len(runs); rep["n_errors"] = sum("error" in r for r in runs)
    return rep


def figures(d):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    paths = []
    # (1) time series: top, pitch +3.5 (nose down), rigid, F4, Fs 0 and 12 kN
    cases = [mk("fig|Fs0", "fig", "top", "pitch+3.5", FINAL, keep_series=True),
             mk("fig|Fs12", "fig", "top", "pitch+3.5", FINAL, Fs=12e3, keep_series=True)]
    res = [run_one(c) for c in cases]
    cols = {"FL": "#1f77b4", "FR": "#ff7f0e", "RL": "#2ca02c", "RR": "#d62728"}
    fig, ax = plt.subplots(4, 2, figsize=(13, 11), sharex="col")
    for jc, (r, ttl) in enumerate(zip(res, ("F_s 0 kN", "F_s 12 kN"), strict=True)):
        if "error" in r:
            continue
        s = r["_series"]; t = s["t"]; H = s["H"]; S = s["S"]
        t0 = r["ra"].get("t_start_s", t[0]); t1 = r.get("t_ready_s") or t[-1]
        win = (t >= t0 - 4) & (t <= t1 + 2)
        tsw = (S["t"] >= t0 - 4) & (S["t"] <= t1 + 2)
        Fm = np.hypot(H[:, 17:21], H[:, 21:25]) / 1e3
        Fc = (H[:, 0:4] - 1047.2) / 1e3
        for i, leg in enumerate(LEGS):
            ax[0, jc].plot(t[win], Fm[win, i], color=cols[leg], lw=1, label=leg)
            ax[1, jc].plot(t[win], Fc[win, i], color=cols[leg], lw=1, label=leg)
            ax[1, jc].plot(S["t"][tsw], np.asarray(S["P"])[tsw, i] / 1e3, color=cols[leg], lw=0.6, ls="--")
            ax[3, jc].plot(S["t"][tsw], np.asarray(S["u"])[tsw, i] * 1e3, color=cols[leg], lw=1, label=leg)
        ax[1, jc].axhline(NEED / 1e3, color="k", lw=0.8, ls=":", label="F_min + 5 kN")
        att = np.degrees(np.column_stack([S["phi"], S["theta"]]))
        ax[2, jc].plot(S["t"][tsw], att[tsw, 0], lw=1, label="roll (true)")
        ax[2, jc].plot(S["t"][tsw], att[tsw, 1], lw=1, label="pitch (true)")
        for a in ax[:, jc]:
            a.axvline(t0, color="0.5", lw=0.6); a.axvline(r["ra"].get("t_end_s", t0), color="0.5", lw=0.6)
            a.grid(alpha=0.3)
        ax[0, jc].set_title(f"top, nose-down 3.5 deg, rigid mast, {ttl}\nREANCHOR {FINAL} (grey lines: start / end), "
                            "then trim -> READY", fontsize=9)
        ax[0, jc].set_ylabel("pad tangential |F_t| [kN]")
        ax[1, jc].set_ylabel("cylinder force [kN]\n(solid true, dashed reading)")
        ax[2, jc].set_ylabel("attitude [deg]")
        ax[3, jc].set_ylabel("leg speed applied [mm/s]")
        ax[3, jc].set_xlabel("time [s]")
        ax[0, jc].legend(ncol=4, fontsize=8); ax[1, jc].legend(ncol=5, fontsize=7); ax[2, jc].legend(fontsize=8)
    fig.tight_layout()
    p = OUT_DIR / "c2_reanchor_timeseries.png"
    fig.savefig(p, dpi=110); plt.close(fig); paths.append(str(p.relative_to(dm.PROJECT_ROOT)))
    # (2) summary: base pairs, max-leg tangential force without / with REANCHOR, and min force
    rep = d.get("report", {})
    pairs = rep.get("verify", {}).get("base_pairs", [])
    if pairs:
        fig, ax = plt.subplots(2, 1, figsize=(13, 8))
        lab = [f"{p['level'][0].upper()} {p['slope']}" for p in pairs]
        x = np.arange(len(pairs))
        ax[0].bar(x - 0.2, [p["Ft_max_off_kN"] for p in pairs], 0.4, label="R1 (no REANCHOR)", color="#9e9e9e")
        ax[0].bar(x + 0.2, [p["Ft_max_ra_kN"] for p in pairs], 0.4, label=f"R1 + REANCHOR ({FINAL})", color="#1f77b4")
        ax[0].axhline(26, color="k", ls=":", lw=0.8, label="rod C45 allowable at e 654 mm (26 kN, cad check, assumption)")
        ax[0].set_ylabel("max-leg pad tangential force\nat run end [kN]")
        ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3, axis="y")
        ax[1].bar(x - 0.2, [p["min_off_kN"] for p in pairs], 0.4, color="#9e9e9e", label="R1")
        ax[1].bar(x + 0.2, [p["min_ra_kN"] for p in pairs], 0.4, color="#1f77b4", label="R1 + REANCHOR")
        ax[1].axhline(NEED / 1e3, color="r", ls=":", lw=0.8, label="F_min + 5 kN = 14.45 kN")
        ax[1].set_ylabel("min true cylinder force\nafter crawler lift-off [kN]")
        for a in ax:
            a.set_xticks(x); a.set_xticklabels(lab, rotation=70, fontsize=7)
        ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3, axis="y")
        fig.tight_layout()
        p = OUT_DIR / "c2_reanchor_summary.png"
        fig.savefig(p, dpi=110); plt.close(fig); paths.append(str(p.relative_to(dm.PROJECT_ROOT)))
    return paths


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=("repro", "screen", "screen2", "verify", "report"))
    ap.add_argument("--variant", default=FINAL, help="REANCHOR option set for --stage verify")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()
    cores = c2t.set_affinity()
    t0 = time.perf_counter()
    d = load_out()
    d.setdefault("meta", {}).update({
        "script": "04_scripts/03_control/run_c2_reanchor.py", "doc": "00_docs/04_control/c2_design.md 17",
        "frame": "body x fwd, y left, z up; roll > 0 left up, pitch > 0 nose down; leg speed > 0 extension",
        "controller": f"C2RN = run_c2_revision.C2R (gain set {R1}) + REANCHOR phase; variants {list(VARIANTS)}",
        "final_variant": FINAL, "final_options": RA_FINAL,
        "plant": "run_pad_tangential_check.TPlant (FlexPlant + pad tangential bushing, mu 0.5), dt 5e-4 s, T 20 ms",
        "F_min_N": F_MIN, "criterion_N": NEED, "F_band_N": F_BAND_D5, "affinity": cores, "slopes_deg": SLOPES})
    if args.stage == "report":
        d["report"] = stage_report(d)
        save_out(d)
        d["meta"]["figures"] = figures(d)
    else:
        cases = cases_for(args.stage, args.variant)
        runs = run_pool(cases, args.workers)
        for r in runs:
            r.pop("_series", None)
        key = args.stage if (args.stage != "verify" or args.variant == FINAL) else f"verify_{args.variant}"
        d[key] = {"n": len(runs), "wall_s": round(time.perf_counter() - t0, 1), "runs": runs, "variant": args.variant}
        ne = sum("error" in r for r in runs)
        print(f"stage {args.stage}: {len(runs)} runs, {ne} errors")
        for r in runs:
            if "error" in r:
                print(r["id"], r["error"], r["tb"][-600:])
    d["meta"].setdefault("stage_wall_s", {})[args.stage] = round(time.perf_counter() - t0, 1)
    save_out(d)
    print("wrote", OUT_JSON, round(time.perf_counter() - t0, 1), "s")


if __name__ == "__main__":
    main()
