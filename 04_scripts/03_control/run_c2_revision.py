"""C2 revision R1 (00_docs/04_control/c2_design.md section 16): three logic fixes after the flexible-mast re-judgement
(dynamics_model.md 3.9.7.5) and their time-domain re-verification.

Fixes (all options of the controller class C2R below; defaults reproduce run_c2_timedomain.C2D bit for bit):
  (B) crawler-zone rule ("no retraction while the crawler may still bear load"): the original rule compares the raw
      stroke-based clearance estimate with 20 mm every step. That estimate is computed from the rod position
      x = s - P / k_oil, so it carries the 3 Hz rocking through the oil compression P / k_oil; with the estimate
      hovering near 20 mm the rule becomes a relay (rear leg speed 0 <-> -10 mm/s every rocking period) that pumps
      the pitch-surge mode. Options:
        rule_src   "raw_x"  (original) | "lpf_x" (1st-order low-pass of the raw estimate, tau rule_tau_s)
                   | "s_lpfP" (estimate from the motor stroke minus the low-passed oil compression:
                     x_slow = s - LPF_tau(P) / k_oil,nom(s); only the compression term is filtered)
        rule_rearm_m None (memoryless threshold at rule_release_m, original) | value (latch with hysteresis:
                     zone on at LEVEL entry, off when the estimate >= rule_release_m, on again when < rule_rearm_m)
  (A) touchdown / crawler lift-off:
        touch_hold_s       a leg counts as touched only after its load stays >= P_touch for this long
                           (stopped while it waits; if the load drops it extends again)
        touch_approach_frac  extension speed (fraction of v_max) once a leg has seen the touch load once
        zone_speed_frac    while the crawler zone is on (B latch), the leg-speed vector is scaled to <= this
                           fraction of v_max (slow crawler unloading = slow tangential load transfer)
  (S) stroke-end logic: stroke_src "x" (rod position, original; never reaches s_max - 1 mm under load because of
      the 3 mm oil compression) | "s" (motor position = the coordinate the stroke limit acts on, as c2.py).

Plant: run_mast_flex_c2_check.FlexPlant (imported read-only; flex 0 = the original reduced kernel bit for bit,
dynamics_model.md 3.9.7.2), so rigid L1 and the 1-mode equivalent flexible mast (stiff / upper / lower support) use
the same code path. Controller loop, delay, ramp and metrics: run_c2_timedomain.run_case (imported read-only).
The motor stroke s is read with its own noise stream (seed + 1000) so that the other sensor draws stay identical.

Run (project root, dynamics-dev activated):
  conda run -n dynamics-dev python -I 04_scripts/03_control/run_c2_revision.py --stage screen   [--workers 12]
  conda run -n dynamics-dev python -I 04_scripts/03_control/run_c2_revision.py --stage verify   [--workers 12]
  conda run -n dynamics-dev python -I 04_scripts/03_control/run_c2_revision.py --stage regress
Writes 06_analysis/02_control/c2_revision_{screen,verify,regress}.json and c2_revision_*.png.
E-cores 16-27, below-normal priority (run_c2_timedomain.set_affinity). Seeds 12345.. (run_control_comparison).
Conventions: body x fwd, y left, z up; pitch > 0 nose down; legs FL, FR, RL, RR; SI units; T = 20 ms.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "01_dynamics"))
sys.path.insert(0, str(HERE))
import run_mast_flex_c2_check as rmf  # noqa: E402  (patches rcc.Plant = FlexPlant in this process)
import run_control_comparison as rcc  # noqa: E402
import run_c2_timedomain as c2t  # noqa: E402
import dyn_model as dm  # noqa: E402
import run_mast_bending_check as mbc  # noqa: E402

OUT_DIR = dm.PROJECT_ROOT / "06_analysis" / "02_control"
DEG = math.pi / 180

# ------------------------------------------------------------------------------------------------ options

R_DEFAULTS = {"rule_src": "raw_x", "rule_tau_s": 0.2, "rule_release_m": 0.02, "rule_rearm_m": None,
              "touch_hold_s": 0.0, "touch_approach_frac": 1.0, "zone_speed_frac": 1.0, "stroke_src": "x"}

B_FIX = {"rule_src": "s_lpfP", "rule_tau_s": 0.2, "rule_rearm_m": 0.01}
P3 = dict(c2t.GAINSETS[c2t.PROPOSAL])
VARIANTS = {
    "it3": {},                                                         # proposal as decided (reference)
    "B_lpfx": {"rule_src": "lpf_x"},                                   # dynamics diagnostic 'filtered'
    "B_lpfx_latch": {"rule_src": "lpf_x", "rule_rearm_m": 0.01},
    "B_slow_latch": dict(B_FIX),
    "BS": dict(B_FIX, stroke_src="s"),
    "BS_hold": dict(B_FIX, stroke_src="s", touch_hold_s=0.5, touch_approach_frac=0.25),
    "BS_zone": dict(B_FIX, stroke_src="s", zone_speed_frac=0.3),
    "BS_hold_zone": dict(B_FIX, stroke_src="s", touch_hold_s=0.5, touch_approach_frac=0.25, zone_speed_frac=0.3),
    # attribution / sensitivity of the touch confirmation (stage 'attrib')
    "BS_holdonly": dict(B_FIX, stroke_src="s", touch_hold_s=0.5),
    "BS_apponly": dict(B_FIX, stroke_src="s", touch_approach_frac=0.25),
    "BS_hold0.25": dict(B_FIX, stroke_src="s", touch_hold_s=0.25, touch_approach_frac=0.25),
    "BS_hold1.0": dict(B_FIX, stroke_src="s", touch_hold_s=1.0, touch_approach_frac=0.25),
    "BS_hold_app0.5": dict(B_FIX, stroke_src="s", touch_hold_s=0.5, touch_approach_frac=0.5),
    "BS_hold_rearm5": dict(B_FIX, stroke_src="s", touch_hold_s=0.5, touch_approach_frac=0.25, rule_rearm_m=0.005),
    "BS_hold_tau0.5": dict(B_FIX, stroke_src="s", touch_hold_s=0.5, touch_approach_frac=0.25, rule_tau_s=0.5),
}
SCREEN_VARIANTS = ("it3", "B_lpfx", "B_lpfx_latch", "B_slow_latch", "BS", "BS_hold", "BS_zone", "BS_hold_zone")
ATTRIB_VARIANTS = ("BS_hold", "BS_holdonly", "BS_apponly", "BS_hold0.25", "BS_hold1.0", "BS_hold_app0.5",
                   "BS_hold_rearm5", "BS_hold_tau0.5")
for _v, _o in VARIANTS.items():
    c2t.GAINSETS["R:" + _v] = dict(P3, **_o)
    c2t.GAINSETS["R:" + _v + "_d0"] = dict(P3, delay_steps=0, **_o)
c2t.OPTION_DEFAULTS.update(R_DEFAULTS)   # every run resets the options first (c2t._run / _run below)


# ------------------------------------------------------------------------------------------------ sensors


class SensorsS(rcc.Sensors):
    """rcc.Sensors + motor stroke s (plant.sref) with its own noise stream (other draws unchanged)."""

    def __init__(self, imu, rng, g):
        super().__init__(imu, rng, g)
        seed = int(rng.bit_generator.seed_seq.entropy) if hasattr(rng.bit_generator, "seed_seq") else 0
        self.rng_s = np.random.default_rng(seed + 1000)

    def read(self, plant, acc, nsub):
        m = super().read(plant, acc, nsub)
        m["s"] = plant.sref + self.rng_s.normal(0, rcc.CA["stroke_noise_m"], 4)
        return m


rcc.Sensors = SensorsS


# ------------------------------------------------------------------------------------------------ controller


class C2R(c2t.C2D):
    """C2D with the revision options (module docstring). Same phases / attributes as rcc.Controller."""
    name = "C2R"

    def __init__(self, ctx, contact="pressure"):
        super().__init__(ctx, contact=contact)
        self.zone = True               # crawler zone (no retraction) for the latched rule
        self.rule_c = None             # rule clearance estimate [m]
        self.Pf = None                 # low-passed pressure for s_lpfP [N]
        self.cand_t = [None] * 4       # touch candidate start times
        self.seen = np.zeros(4, bool)  # touch load seen once (approach speed)
        self.zone_steps = 0; self.zone_toggles = 0; self._zone_prev = True

    # --- (B) rule estimate, updated every period (also in TOUCH: warm filters) ---
    def _rule_estimate(self, m, raw):
        CA = rcc.CA
        src = CA["rule_src"]
        a = rcc.T_CTRL / CA["rule_tau_s"]
        if src == "raw_x":
            self.rule_c = raw
        elif src == "lpf_x":
            self.rule_c = raw if self.rule_c is None else self.rule_c + a * (raw - self.rule_c)
        elif src == "s_lpfP":
            P = m["P"]
            self.Pf = P.copy() if self.Pf is None else self.Pf + a * (P - self.Pf)
            ko = np.asarray(dm.k_oil(m["s"], beta=1.0e9), float)   # controller nominal beta (c2.py oil_stiffness)
            self.rule_c = self.c.clearance_est(m["s"] - self.Pf / ko)
        else:
            raise ValueError(src)
        return self.rule_c

    def _zone_update(self, rc):
        CA = rcc.CA
        rel = CA["rule_release_m"]; rearm = CA["rule_rearm_m"]
        if rearm is None:
            self.zone = rc < rel
        elif self.zone and rc >= rel:
            self.zone = False; self.ev("crawler_zone_off")
        elif (not self.zone) and rc < rearm:
            self.zone = True; self.ev("crawler_zone_rearm")
        if self.zone != self._zone_prev:
            self.zone_toggles += 1
        self._zone_prev = self.zone
        self.zone_steps += int(self.zone)

    # --- (A) touch ---
    def _touch(self, m, t):
        CA = rcc.CA
        c = self.c
        if self.contact == "pressure":
            load = m["P"]
        else:
            if t < 5.0:
                self.air.append(m["P"].copy())
                self.P_air = np.median(np.array(self.air), axis=0)
            load = m["P"] - self.P_air - CA["rod_weight_N"]
        cond = load >= CA["P_touch_N"]
        hold = CA["touch_hold_s"]
        if hold <= 0.0:
            self.touched |= cond
            cand = np.zeros(4, bool)
        else:
            cand = np.zeros(4, bool)
            for i in range(4):
                if self.touched[i]:
                    continue
                if cond[i]:
                    if self.cand_t[i] is None:
                        self.cand_t[i] = t
                    if t - self.cand_t[i] >= hold - 1e-9:
                        self.touched[i] = True
                    else:
                        cand[i] = True
                else:
                    self.cand_t[i] = None
        self.seen |= cond
        v_free = np.where(self.seen, CA["touch_approach_frac"] * c.vmax, c.vmax)
        u = np.where(self.touched | cand, 0.0, v_free)
        if self.touched.all():
            self.phase = "level"; self.t_touch = t
            self.on_touch(m)
        return u

    def update(self, m, t):
        CA = rcc.CA
        self.t = t
        self.filt(m)
        c = self.c
        raw = c.clearance_est(m["x"])
        rc = self._rule_estimate(m, raw) if "s" in m or CA["rule_src"] != "s_lpfP" else raw
        if self.phase == "touch":
            return self._touch(m, t)
        if self.done:
            low = self.lifted and self.ready and float(self.load_est(m).min()) < c.F_min + 3e3
            if max(abs(self.phi_s), abs(self.th_s)) > CA["relevel_att_deg"] * DEG or low:
                self.done = False; self.ready = False; self.ok_since = None; self.probe = None
                self.ev("relevel" + ("_lowload" if low else ""))
                self.on_relevel()
            else:
                if self.contact == "combined" and not self.ready:
                    return self.probe_step(m)
                if not self.ready:
                    self.ready = True; self.t_ready = t
                    if self.t_ready_first is None:
                        self.t_ready_first = t
                return np.zeros(4)
        if not self.lifted and raw > 0.01:
            self.lifted = True
        u = self.level(m)
        self._zone_update(rc)
        if self.zone:     # crawler may still bear load: no retraction (add pure heave), optional slow unloading
            u = rcc._sat_scale(u + max(0.0, -float(u.min())), c.vmax)
            fr = CA["zone_speed_frac"]
            if fr < 1.0:
                u = rcc._sat_scale(u, fr * c.vmax)
        pos = m["s"] if CA["stroke_src"] == "s" else m["x"]
        at_end = (pos >= c.smax - 1e-3) & (u > 1e-5)
        self.end_cnt = getattr(self, "end_cnt", 0) + 1 if at_end.any() else 0
        if self.end_cnt * rcc.T_CTRL > 2.0:
            if not getattr(self, "fault", False):
                self.ev("stroke_end_fault")
            self.fault = True
        if getattr(self, "fault", False):
            return np.zeros(4)
        return rcc._stroke_clip(u, pos, c.smax)


# ------------------------------------------------------------------------------------------------ runs

CONFIG = rmf.CONFIG
LAST = rmf.LAST


def _run(kw):
    """One case: FlexPlant (rigid or equivalent mast) + C2R; options = c2t.OPTION_DEFAULTS + gain set."""
    kw = dict(kw)
    cfg = kw.pop("cfg", {})
    CONFIG.clear(); CONFIG.update(cfg)
    rcc.Plant = rmf.FlexPlant
    rcc.Sensors = SensorsS
    c2t.C2D = C2R if not cfg.get("orig_ctrl") else rmf.C2D_ORIG
    tag = kw.pop("tag"); grp = kw.pop("group"); gs = kw.pop("gainset"); mast = kw.pop("mast", "rigid")
    rcc.CA.update(c2t.OPTION_DEFAULTS); rcc.CA.update(c2t.GAINSETS[gs])
    t0 = time.perf_counter()
    try:
        r = c2t.run_case(keep_series=True, **kw)
        pl = LAST["plant"]
        if pl.flex != (0 if cfg.get("mast_eq") is None else 1):
            raise RuntimeError("plant flex flag does not match the case configuration")
        S = r.pop("_series")
        r.update(rmf.extra_metrics(S, r, pl))
        tl = r.get("t_crawler_liftoff_s")
        if tl is not None:
            post = S["t"] >= tl + 1.0
            if r.get("t_ready_s") is not None:
                post &= S["t"] <= r["t_ready_s"]
            if post.any():   # true crawler clearance during levelling (1 s after lift-off .. ready)
                r["min_true_clearance_levelling_mm"] = round(float(S["clr"][post].min()) * 1e3, 2)
                r["crawler_recontact"] = bool((S["crawler_N"][post] > 0).any())
        if cfg.get("keep_series"):
            r["_series"] = {k: np.asarray(v) for k, v in S.items()}
    except Exception as e:  # noqa: BLE001
        import traceback
        r = {"error": repr(e), "tb": traceback.format_exc()[-800:]}
    r.update({"slope": tag, "group": grp, "gainset": gs, "mast": mast, "seed": kw.get("seed"),
              "beta_GPa": kw.get("beta", 1.0e9) / 1e9, "variant": cfg.get("variant", ""),
              "wall_s": round(time.perf_counter() - t0, 1)})
    return r


# patch C2R to expose itself for diagnostics (zone toggles) through LAST
_orig_init = C2R.__init__


def _init_record(self, ctx, contact="pressure"):
    _orig_init(self, ctx, contact)
    LAST["ctrl"] = self


C2R.__init__ = _init_record

KEEP = ("gainset", "group", "mast", "variant", "seed", "slope", "level", "beta_GPa", "Fs_kN", "contact", "imu",
        "soft_FL", "settle", "damping_scale", "t_touch_s", "t_crawler_liftoff_s", "t_ready_s", "t_level_after_touch_s",
        "ss_true_att_deg_maxabs", "min_true_cyl_force_kN", "min_true_leg", "min_true_cyl_force_substep_kN",
        "min_true_leg_substep", "t_min_after_liftoff_s", "min_true_during_levelling_kN", "min_pressure_reading_kN",
        "t_below_Fmin_true_s", "max_pressure_bar", "levelled_loads_true_kN", "final_clearance_mm", "rocking_peak_deg",
        "overshoot_true_deg", "guard_active_s", "probe_rounds", "zone_toggles", "zone_time_s",
        "min_true_clearance_levelling_mm", "crawler_recontact", "fails", "events",
        "error", "tb", "wall_s")


def compact(r):
    if r.get("t_ready_s") is not None and r.get("t_touch_s") is not None:
        r["t_level_after_touch_s"] = round(r["t_ready_s"] - r["t_touch_s"], 2)
    out = {k: r[k] for k in KEEP if k in r and r[k] is not None}
    if "events" in out:
        out["events"] = out["events"][:8]
    return out


def _run_c(kw):
    r = _run(kw)
    c = LAST.get("ctrl")
    if c is not None and isinstance(c, C2R) and "error" not in r:
        r["zone_toggles"] = int(c.zone_toggles)
        r["zone_time_s"] = round(c.zone_steps * rcc.T_CTRL, 2)
    r.pop("_series", None)
    return compact(r)


# ------------------------------------------------------------------------------------------------ case lists

SL = rmf.SLOPE_ANG


def _eqs():
    mast = mbc.load_mast(); boom = rmf.load_boom()
    return {(lv, sup): rmf.public(rmf.equivalent_mast(lv, sup, boom, mast)) for lv in dm.LEVELS for sup in rmf.SUPPORTS}


def _mcfg(eqs, lv, mast, **extra):
    d = {"mast_eq": None if mast == "rigid" else eqs[(lv, mast)]}
    d.update(extra)
    return d


SCREEN_SLOPES = ("flat", "pitch+3.3", "pitch+3.5", "pitch+3.7", "pitch-3.5", "pitch-3.7", "roll+5.7", "diag3",
                 "diag3.2")


ATTRIB_SLOPES = ("pitch+3.3", "pitch+3.5", "pitch+3.7", "roll+5.7", "diag3.2")


def screen_cases(eqs, variants=SCREEN_VARIANTS, slopes=SCREEN_SLOPES):
    cases = []
    for v in variants:
        for mast in ("rigid", "stiff"):
            for tag in slopes:
                ro, pi = SL[tag]
                for d0 in ("", "_d0"):
                    for s in range(3):
                        cases.append(dict(gainset=f"R:{v}{d0}", level="top", roll=ro, pitch=pi, tag=tag,
                                          group="screen", mast=mast, seed=12345 + s, cfg=_mcfg(eqs, "top", mast)))
                cases.append(dict(gainset=f"R:{v}", level="top", roll=ro, pitch=pi, beta=1.6e9, tag=tag,
                                  group="screen_beta1.6", mast=mast, cfg=_mcfg(eqs, "top", mast)))
    return cases


def verify_cases(eqs, final):
    """Final design `final` (variant key): base matrix + sensitivities of c2_design 8 (rigid), flexible-mast matrix
    and robustness grid of dynamics_model.md 3.9.7 (seeds x delay x beta), extra crawler tangential sensitivity."""
    g1 = f"R:{final}"; g0 = f"R:{final}_d0"
    cases = []
    # (1) base matrix of c2_design 8.1 (rigid, 3 levels x 11 slopes, seed 12345)
    for lv in dm.LEVELS:
        for tag, ro, pi in c2t.SLOPES:
            for gs in (g1, g0):
                cases.append(dict(gainset=gs, level=lv, roll=ro, pitch=pi, tag=tag, group="base", mast="rigid", cfg={}))
    # (2) c2_design 8.2 sensitivity groups (rigid, top)
    for tag, ro, pi in [("diag3", 2.1213, 2.1213), ("roll+3", 3, 0)]:
        for b in (0.69e9, 1.6e9):
            cases.append(dict(gainset=g1, level="top", roll=ro, pitch=pi, beta=b, tag=tag, group="beta", cfg={}))
    for tag, ro, pi in [("flat", 0, 0), ("roll+3", 3, 0), ("pitch+3.3", 0, 3.3)]:
        for fs in (0.0, 2e3, 5e3, 12e3):
            for ctc in ("pressure", "combined"):
                if fs == 0.0 and ctc == "pressure":
                    continue
                cases.append(dict(gainset=g1, level="top", roll=ro, pitch=pi, Fs=fs, contact=ctc, tag=tag,
                                  group="seal", cfg={}))
    for fs in (0.0, 12e3):
        for ctc in ("pressure", "combined"):
            cases.append(dict(gainset=g1, level="top", Fs=fs, contact=ctc, settle=True, tag="flat", group="settle",
                              cfg={}))
    for tag, ro, pi in [("flat", 0, 0), ("diag3", 2.1213, 2.1213)]:
        cases.append(dict(gainset=g1, level="top", roll=ro, pitch=pi, soft_FL=True, tag=tag, group="soft_FL", cfg={}))
        cases.append(dict(gainset=g1, level="top", roll=ro, pitch=pi, imu="worst", tag=tag, group="imu_worst", cfg={}))
    for tag, ro, pi in [("flat", 0, 0), ("roll+3", 3, 0), ("diag3", 2.1213, 2.1213), ("pitch+3.3", 0, 3.3),
                        ("pitch+3.5", 0, 3.5)]:
        cases.append(dict(gainset=g1, level="top", roll=ro, pitch=pi, damping_scale=1 / 3, tag=tag, group="damp_low",
                          cfg={}))
    # (3) flexible-mast matrix (3.9.7.3): 3 levels x 3 supports x 23 slopes, seed 12345, delay 1
    for lv in dm.LEVELS:
        for mast in rmf.FLEX:
            for tag, ro, pi in rmf.SLOPES:
                cases.append(dict(gainset=g1, level=lv, roll=ro, pitch=pi, tag=tag, group="flex_matrix", mast=mast,
                                  cfg=_mcfg(eqs, lv, mast)))
    # (4) robustness grid (3.9.7.4): rigid + 3 supports, seeds 3 x delay 1/0, beta 0.69/1.6 (delay 1)
    for lv, tags in (("top", rmf.ROBUST_TOP), ("middle", rmf.ROBUST_LOW), ("bottom", rmf.ROBUST_LOW)):
        for mast in ("rigid",) + rmf.FLEX:
            for tag in tags:
                ro, pi = SL[tag]
                for gs in (g1, g0):
                    for s in range(3):
                        cases.append(dict(gainset=gs, level=lv, roll=ro, pitch=pi, tag=tag, group="robust_seed",
                                          mast=mast, seed=12345 + s, cfg=_mcfg(eqs, lv, mast)))
                if lv == "top":
                    for b in (0.69e9, 1.6e9):
                        cases.append(dict(gainset=g1, level=lv, roll=ro, pitch=pi, beta=b, tag=tag,
                                          group="robust_beta", mast=mast, cfg=_mcfg(eqs, lv, mast)))
    # (5) sensitivities at the D8 edge (top): crawler tangential stiffness x0.5 / x2, mast zeta 0.012/0.023,
    #     leg damping 1/3 with stiff mast, seal friction 12 kN combined with stiff mast
    edge = ("pitch+3.3", "pitch+3.5", "diag2.8", "diag3", "roll+5.5")
    for tag in edge:
        ro, pi = SL.get(tag, (5.5, 0.0)) if tag != "roll+5.5" else (5.5, 0.0)
        for mast in ("rigid", "stiff"):
            for ks in (0.5, 2.0):
                cases.append(dict(gainset=g1, level="top", roll=ro, pitch=pi, tag=tag, group=f"crawler_kt_x{ks:g}",
                                  mast=mast, cfg=_mcfg(eqs, "top", mast, ktcr_scale=ks)))
            for ds in (1 / 3,):
                cases.append(dict(gainset=g1, level="top", roll=ro, pitch=pi, damping_scale=ds, tag=tag,
                                  group="damp_low_mast", mast=mast, cfg=_mcfg(eqs, "top", mast)))
            cases.append(dict(gainset=g1, level="top", roll=ro, pitch=pi, Fs=12e3, contact="combined", tag=tag,
                              group="seal12_combined", mast=mast, cfg=_mcfg(eqs, "top", mast)))
        for mast in ("upper", "lower"):
            for z in (0.012, 0.023):
                e = dict(eqs[("top", mast)])
                sc = z / float(e["zeta"][0])
                e["c_rot_N_m_s_rad"] = (np.array(e["c_rot_N_m_s_rad"]) * sc).tolist(); e["zeta"] = [z, z]
                cases.append(dict(gainset=g1, level="top", roll=ro, pitch=pi, tag=tag, group=f"zeta{z}", mast=mast,
                                  cfg={"mast_eq": e}))
    return cases


# ------------------------------------------------------------------------------------------------ summaries


def env_table(runs, groups, key_fn):
    out = {}
    for r in runs:
        if r.get("group") not in groups:
            continue
        k = key_fn(r)
        e = out.setdefault(k, {"n": 0, "fails": 0, "min_kN": None, "min_sub_kN": None, "fail_kinds": [],
                               "t_level_max_s": 0.0, "ss_max_deg": 0.0, "max_bar": 0.0, "zone_toggles_max": 0,
                               "min_clr_mm": None, "recontact": 0})
        e["n"] += 1
        v = r.get("min_true_cyl_force_kN"); vs = r.get("min_true_cyl_force_substep_kN")
        if v is not None:
            e["min_kN"] = v if e["min_kN"] is None else min(e["min_kN"], v)
        if vs is not None:
            e["min_sub_kN"] = vs if e["min_sub_kN"] is None else min(e["min_sub_kN"], vs)
        if r.get("fails") or "error" in r:
            e["fails"] += 1
            e["fail_kinds"] = sorted(set(e["fail_kinds"]) | set(r.get("fails", [])) | ({"error"} if "error" in r else set()))
        e["t_level_max_s"] = max(e["t_level_max_s"], r.get("t_level_after_touch_s", 0.0) or 0.0)
        e["ss_max_deg"] = max(e["ss_max_deg"], r.get("ss_true_att_deg_maxabs", 0.0) or 0.0)
        e["max_bar"] = max(e["max_bar"], r.get("max_pressure_bar", 0.0) or 0.0)
        e["zone_toggles_max"] = max(e["zone_toggles_max"], r.get("zone_toggles", 0) or 0)
        c_ = r.get("min_true_clearance_levelling_mm")
        if c_ is not None:
            e["min_clr_mm"] = c_ if e["min_clr_mm"] is None else min(e["min_clr_mm"], c_)
        e["recontact"] += int(bool(r.get("crawler_recontact")))
    return out


def d8_pass(e, need=9.45255 + 5.0):
    return e["fails"] == 0 and e["min_kN"] is not None and e["min_kN"] >= need


# ------------------------------------------------------------------------------------------------ regression


def regress():
    """C2R with default options must reproduce C2D (run_c2_timedomain) bit for bit; FlexPlant flex 0 = rcc.Plant."""
    out = {}
    for tag in ("diag3", "pitch+3.7"):
        ro, pi = SL[tag]
        res = {}
        for name, orig in (("C2D", True), ("C2R_default", False)):
            r = _run(dict(gainset=c2t.PROPOSAL, level="top", roll=ro, pitch=pi, tag=tag, group="regress",
                          cfg={"orig_ctrl": orig, "keep_series": True}))
            res[name] = r
        a, b = res["C2D"]["_series"], res["C2R_default"]["_series"]
        d = max(float(np.max(np.abs(np.asarray(a[k]) - np.asarray(b[k])))) for k in ("u", "Ftrue", "P", "x", "phi"))
        out[tag] = {"max_abs_series_diff": d, "min_kN": [res["C2D"].get("min_true_cyl_force_kN"),
                                                         res["C2R_default"].get("min_true_cyl_force_kN")],
                    "stored_c2_design_it3": {"diag3": 22.75, "pitch+3.7": 24.39}[tag]}
    return out


# ------------------------------------------------------------------------------------------------ figure


def figure(eqs, final, stem):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(4, 1, figsize=(10, 10), sharex=True)
    cols = {"it3": "#9e9e9e", final: "#d62728"}
    for v in ("it3", final):
        r = _run(dict(gainset=f"R:{v}_d0", level="top", roll=0, pitch=3.5, tag="pitch+3.5", group="fig",
                      mast="rigid", cfg={"keep_series": True}))
        S = r["_series"]; t = S["t"]
        lab = f"{v} (delay 0): min {r.get('min_true_cyl_force_kN')} kN"
        ax[0].plot(t, S["Ftrue"][:, 3] / 1e3, color=cols[v], lw=0.8, label=lab + " RR")
        ax[0].plot(t, S["Ftrue"][:, 2] / 1e3, color=cols[v], lw=0.8, ls=":")
        ax[1].plot(t, S["u"][:, 3] * 1e3, color=cols[v], lw=0.7)
        ax[2].plot(t, (S["clr"]) * 1e3, color=cols[v], lw=0.8)
        ax[3].plot(t, np.degrees(S["theta"]), color=cols[v], lw=0.8)
    ax[0].axhline(9.4526, color="k", ls="--", lw=0.8); ax[0].axhline(14.4526, color="k", ls=":", lw=0.8)
    ax[0].set_ylabel("true cyl. force [kN]\nRR solid, RL dotted"); ax[0].legend(fontsize=8); ax[0].set_ylim(0, 160)
    ax[1].set_ylabel("applied RR speed [mm/s]")
    ax[2].set_ylabel("true crawler clearance [mm]"); ax[2].axhline(20, color="k", ls=":", lw=0.8)
    ax[3].set_ylabel("true pitch [deg]"); ax[3].set_xlabel("time from leg start [s]")
    for a in ax:
        a.grid(alpha=0.3)
    ax[0].set_title("C2 revision: top auger, ground pitch +3.5 deg (nose down), rigid mast, no extra delay; "
                    "grey = it3, red = revised", fontsize=9)
    ax[3].set_xlim(10, 50)
    fig.tight_layout()
    p = OUT_DIR / f"{stem}_pitch3.5.png"
    fig.savefig(p, dpi=90); plt.close(fig)
    return p


# ------------------------------------------------------------------------------------------------ main


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("screen", "attrib", "verify", "regress"), required=True)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--final", default="BS_hold_zone")
    args = ap.parse_args()
    cores = c2t.set_affinity()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    if args.stage == "regress":
        res = {"regress": regress(), "frozen_kernel": rmf.verify_frozen_identity()}
        p = OUT_DIR / "c2_revision_regress.json"
        p.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
        print(json.dumps(res, indent=1, default=float))
        return
    eqs = _eqs()
    if args.stage == "screen":
        cases = screen_cases(eqs)
    elif args.stage == "attrib":
        cases = screen_cases(eqs, ATTRIB_VARIANTS, ATTRIB_SLOPES)
    else:
        cases = verify_cases(eqs, args.final)
    _run_c(dict(cases[0]))
    from multiprocessing import Pool
    with Pool(args.workers) as pool:
        runs = pool.map(_run_c, cases, chunksize=1)
    meta = {"script": "04_scripts/03_control/run_c2_revision.py", "argv": sys.argv[1:], "affinity": cores,
            "dt_s": rcc.DT, "T_ctrl_s": rcc.T_CTRL, "variants": VARIANTS, "R_defaults": R_DEFAULTS,
            "base_gainset": P3, "n_runs": len(runs),
            "criterion_D8": "min true cylinder force (20 ms samples, after crawler lift-off) >= F_min + 5 kN = 14.45 kN, "
                            "no pad lift-off, ss <= 0.2 deg, ready within 150 s"}
    if args.stage in ("screen", "attrib"):
        tab = env_table(runs, ("screen", "screen_beta1.6"),
                        lambda r: f"{r['gainset'].replace('_d0', '')}|{r['mast']}|{r['slope']}|"
                                  f"{'d0' if r['gainset'].endswith('_d0') else ('b1.6' if r['group'] != 'screen' else 'd1')}")
        res = {"meta": meta, "table": tab, "runs": runs}
    else:
        res = {"meta": dict(meta, final=args.final, final_options=VARIANTS[args.final])}
        res["base"] = env_table(runs, ("base",), lambda r: f"{'d0' if r['gainset'].endswith('_d0') else 'd1'}|"
                                                            f"{r['level']}|{r['slope']}")
        res["sens"] = env_table(runs, ("beta", "seal", "settle", "soft_FL", "imu_worst", "damp_low"),
                                lambda r: f"{r['group']}|{r['slope']}|{r.get('contact', '')}|Fs{r.get('Fs_kN', 0)}"
                                          f"|b{r.get('beta_GPa')}")
        res["flex_matrix"] = env_table(runs, ("flex_matrix",), lambda r: f"{r['level']}|{r['mast']}|{r['slope']}")
        res["robust"] = env_table(runs, ("robust_seed", "robust_beta"),
                                  lambda r: f"{r['level']}|{r['mast']}|{r['slope']}|"
                                            f"{'d0' if r['gainset'].endswith('_d0') else 'd1'}")
        res["edge_sens"] = env_table(runs, tuple(g for g in {r.get('group') for r in runs}
                                                 if g and (g.startswith("crawler_kt") or g.startswith("zeta")
                                                           or g in ("damp_low_mast", "seal12_combined"))),
                                     lambda r: f"{r['group']}|{r['mast']}|{r['slope']}")
        res["runs"] = runs
        try:
            res["meta"]["figure"] = str(figure(eqs, args.final, "c2_revision").relative_to(dm.PROJECT_ROOT))
        except Exception as e:  # noqa: BLE001
            res["meta"]["figure_error"] = repr(e)
    res["meta"]["wall_s"] = round(time.perf_counter() - t0, 1)
    p = OUT_DIR / f"c2_revision_{args.stage}.json"
    p.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("wrote", p, res["meta"]["wall_s"], "s", len(runs), "runs")


if __name__ == "__main__":
    main()
