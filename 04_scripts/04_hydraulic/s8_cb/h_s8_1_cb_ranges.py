"""H-S8-1: counterbalance (CB) rod-side pressure ranges and checks against the S8 Chrono batches.

Basis: ``00_docs/04_control/s6_control_spec.md`` rev. 46, 216.5 / 216.10 (H-S8-1, P-S8-11);
``00_docs/02_hydraulic/s8_seal_friction_counterbalance.md`` 4.3 / 4.4;
``03_src/outrigger_sim/hydraulics/counterbalance.py`` (``cb_rod_pressure_Pa``, read only).

Parts (read only; no Chrono is run):

A. Analytic range tables of the CB-regulated rod pressure while extending (upper bound) and of
   the rod lock pressure ``p_r0`` after an extension / retraction, over the friction level
   (0 / 2 / 4 / 8 kN, rear x 0.8333), front / rear, load state, CB parameter range (4.4) and a
   speed table (flow override of a real valve, stick transient).
B. Check of the CB batch ``07_results/S8/cb_20261025_000840``: moving rod pressure against the
   4.3 target with the 50 ms lag, the lock-instant ``p_r0``, the locked law (G4 maximum).
C. D2 (two_pressure._check_moving) emulation at the 10 Hz controller samples: the residual of
   the rod pressure above three candidate upper bounds, on the CB batch (recorded truth) and on
   the pilot-check batches p1r / rest converted to CB with the 4.3 identity (slope / F_s / auger
   envelope; leg forces do not depend on the lock valve, 216.5 regression <= 0.13 kN except one
   case).
D. Monte Carlo of the normal-grade WIKA errors (mirror of
   ``outrigger_sim/sensors/pressure_error.py`` normal grade, 0.20 bar noise) for the false D2
   fallback probability per leg trace and margin. Seed fixed (20261025).

All pressures GAUGE [Pa] internally, reported in bar g. Units SI.
Usage: python -I h_s8_1_cb_ranges.py <out.json>
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[3]
BAR = 1e5
G = 9.80665
LEGS = ("FL", "FR", "RL", "RR")
CB_BATCH = ROOT / "07_results/S8/cb_20261025_000840"
POC_BATCHES = (ROOT / "07_results/S8/p1r_20261024_222013", ROOT / "07_results/S8/rest_20261024_233615")
# YAML comment (spec 1 table, rod_side_pressure.md 14.7): static cylinder forces [N]
STATIC_F = np.array([118.099e3, 116.106e3, 72.097e3, 70.282e3])
SEED = 20261025
MARGINS_BAR = (0.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0, 25.0)
D2_POC_HIGH = 12.0 * BAR  # two_pressure.TwoPressureSettings.extend_rod_range_Pa[1]
D2_MIN_HEAD = 20.0 * BAR
D2_SPEED_FRACTION = 0.25
D2_SETTLE_S = 1.0
D2_REVERSAL_S = 2.0
D2_HOLD_SAMPLES = 11  # violation held 1.0 s at 10 Hz: samples t_v ... t_v + 1.0 s


# ---------------------------------------------------------------------------------------------
# parameters

def load_params() -> dict:
    y = yaml.safe_load((ROOT / "02_params/rexome33.yaml").read_text(encoding="utf-8"))
    act, legs, cb = y["actuator"], y["legs"], y["actuator"]["counterbalance"]
    return {
        "a_p": np.array([legs[k]["cylinder"]["head_area_m2"] for k in LEGS]),
        "a_r": np.array([legs[k]["cylinder"]["annulus_area_m2"] for k in LEGS]),
        "w_rod": np.array([legs[k]["moving_part"]["mass_kg"] for k in LEGS]) * G,
        "beta": float(act["oil_bulk_modulus_eff_Pa"]),
        "l0h": float(act["oil_dead_length_m"]),
        "l0r": float(act["rod_dead_length_m"]),
        "stroke": float(act["stroke_m"]),
        "v_max": float(act["max_speed_m_s"]),
        "relief": float(act["relief_pressure_moving_Pa"]),
        "floor_g": float(act["rod_side"]["p_floor_Pa"]) - 1e5,
        "rear_scale": float(act["seal_friction"]["rear_scale"]),
        "F_min": float(y["control"]["F_min_cylinder_N"]),
        "p_set": float(cb["p_set_Pa"]),
        "psi": float(cb["pilot_ratio"]),
        "p_back": float(cb["back_pressure_Pa"]),
        "p_T": float(cb["tank_pressure_Pa"]),
        "override": float(cb["override_Pa"]),
        "q_r": float(cb["rated_flow_m3_s"]),
        "tau_v": float(act["rod_side"]["release_tau_s"]),
    }


def p_ext(fp, a_p, a_r, p_set, psi, p_back, floor_g, relief):
    """4.3 extend: max(p_back, (p_set A_p - psi F_p) / (A_p + psi A_ann)), clipped as the code."""
    raw = (p_set * a_p - psi * np.asarray(fp, float)) / (a_p + psi * a_r)
    return np.clip(np.maximum(raw, p_back), floor_g, relief)


def p_ret(fp, a_p, a_r, p_set, psi, floor_g, relief):
    """4.3 retract: (p_set A_p - F_p) / (psi A_p + A_ann), clipped as the code."""
    raw = (p_set * a_p - np.asarray(fp, float)) / (psi * a_p + a_r)
    return np.clip(raw, floor_g, relief)


def nominal(P, i):
    return dict(a_p=P["a_p"][i], a_r=P["a_r"][i], p_set=P["p_set"], psi=P["psi"],
                floor_g=P["floor_g"], relief=P["relief"])


def fs_leg(P, level_N, i):
    return level_N * (P["rear_scale"] if i >= 2 else 1.0)


# ---------------------------------------------------------------------------------------------
# A. analytic tables

def part_a(P) -> dict:
    out = {"extend_upper": [], "lock_p_r0": [], "regulation_end_Fp_N": {}, "speed": [],
           "param_envelope": []}
    p_sets = (300e5, 330e5, 345e5)
    psis = (3.0, 4.0, 8.0)
    for i, side in ((0, "front"), (2, "rear")):
        a_p, a_r = P["a_p"][i], P["a_r"][i]
        for ps in p_sets:
            for psi in psis:
                fp_star = (ps * a_p - P["p_back"] * (a_p + psi * a_r)) / psi
                out["regulation_end_Fp_N"][f"{side}_pset{ps/BAR:.0f}_psi{psi:g}"] = fp_star
        loads = [("air", -P["w_rod"][i]), ("touch", 0.0), ("F_min", P["F_min"]),
                 ("20kN", 20e3), ("40kN", 40e3), ("60kN", 60e3), ("static", STATIC_F[i]),
                 ("100kN", 100e3), ("150kN", 150e3), ("200kN", 200e3)]
        for level in (0.0, 2e3, 4e3, 8e3):
            fs = fs_leg(P, level, i)
            for name, F in loads:
                kw = nominal(P, i)
                slide = float(p_ext(F + fs, a_p, a_r, P["p_set"], P["psi"], P["p_back"],
                                    P["floor_g"], P["relief"]))
                stick = float(p_ext(F - fs, a_p, a_r, P["p_set"], P["psi"], P["p_back"],
                                    P["floor_g"], P["relief"]))
                env = max(float(p_ext(F - fs, a_p, a_r, ps, psi, P["p_back"], P["floor_g"],
                                      P["relief"])) for ps in p_sets for psi in psis)
                ph_slide = (F + fs + slide * a_r) / a_p
                out["extend_upper"].append(dict(side=side, Fs_level_kN=level / 1e3,
                                                Fs_leg_kN=fs / 1e3, load=name, F_kN=F / 1e3,
                                                p_r_slide_bar=slide / BAR,
                                                p_h_slide_bar=ph_slide / BAR,
                                                p_r_stick_worst_bar=stick / BAR,
                                                p_r_envelope_bar=env / BAR))
                r_ext = [float(p_ext(F + s * fs, a_p, a_r, P["p_set"], P["psi"], P["p_back"],
                                     P["floor_g"], P["relief"])) for s in (+1, -1)]
                r_ret = [float(p_ret(F + s * fs, a_p, a_r, P["p_set"], P["psi"], P["floor_g"],
                                     P["relief"])) for s in (-1, +1)]
                env_ext = [float(p_ext(F + s * fs, a_p, a_r, ps, psi, P["p_back"], P["floor_g"],
                                       P["relief"])) for s in (+1, -1) for ps in p_sets
                           for psi in psis]
                env_ret = [float(p_ret(F + s * fs, a_p, a_r, ps, psi, P["floor_g"], P["relief"]))
                           for s in (-1, +1) for ps in p_sets for psi in psis]
                out["lock_p_r0"].append(dict(
                    side=side, Fs_level_kN=level / 1e3, load=name, F_kN=F / 1e3,
                    after_extend_nominal_bar=r_ext[0] / BAR,
                    after_extend_stick_range_bar=[min(r_ext) / BAR, max(r_ext) / BAR],
                    after_extend_envelope_bar=[min(env_ext) / BAR, max(env_ext) / BAR],
                    after_retract_nominal_bar=r_ret[0] / BAR,
                    after_retract_stick_range_bar=[min(r_ret) / BAR, max(r_ret) / BAR],
                    after_retract_envelope_bar=[min(env_ret) / BAR, max(env_ret) / BAR]))
        # speed: a real CB needs Delta p_ov Q / Q_r more opening pressure (not in the 4.3 model);
        # stick transient: the oil column must change by 2 F_s before the piston slides
        s_mid = 0.35
        k_h = P["beta"] * a_p / (P["l0h"] + s_mid)
        for frac in (0.0, 0.25, 0.5, 1.0):
            v = frac * P["v_max"]
            q = a_r * v
            row = dict(side=side, v_frac=frac, v_mm_s=v * 1e3, Q_rod_L_min=q * 6e4)
            for ov in (10e5, 20e5, 40e5):
                d_id = ov * q / P["q_r"]
                row[f"identity_add_bar_ov{ov/BAR:.0f}"] = d_id / BAR
                row[f"Fp_form_add_bar_ov{ov/BAR:.0f}"] = d_id * a_p / (a_p + P["psi"] * a_r) / BAR
            for level in (2e3, 4e3, 8e3):
                fs = fs_leg(P, level, i)
                row[f"stick_s_Fs{level/1e3:g}"] = (2 * fs / (k_h * v)) if v > 0 else math.inf
            out["speed"].append(row)
    return out


# ---------------------------------------------------------------------------------------------
# helpers for the batches

def find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, key)
            if r is not None:
                return r
    return None


def load_case(case: Path):
    pads_p, r8_p = case / "pads.npz", case / "r8_series.npz"
    if not (pads_p.exists() and r8_p.exists()):
        return None
    with np.load(pads_p, allow_pickle=True) as z:
        if "F_pressure" not in z.files:
            return None
        d = {k: z[k] for k in ("t", "F_pressure", "head_pressure", "rod_pressure", "s_motor",
                               "airborne", "F_cyl", "N")}
    with np.load(r8_p, allow_pickle=True) as z:
        d["t10"] = z["t"]
        d["u10"] = z["computed_u"]
    meta = json.loads((case / "case.json").read_text(encoding="utf-8"))
    l0r = find_key(meta, "rod_dead_length_m")
    d["l0r"] = np.array(l0r, float).reshape(-1) if l0r is not None else None
    d["lock_valve"] = find_key(meta, "actuator.lock_valve") or find_key(meta, "lock_valve")
    return d


def moving_masks(d):
    t, s = d["t"], d["s_motor"]
    v = np.zeros_like(s)
    v[1:] = np.diff(s, axis=0) / np.diff(t)[:, None]
    return v > 1e-6, v < -1e-6


# ---------------------------------------------------------------------------------------------
# B. CB batch check

def part_b(P) -> dict:
    out = {}
    for case in sorted(p for p in CB_BATCH.iterdir() if p.is_dir()):
        d = load_case(case)
        if d is None:
            continue
        t = d["t"]
        dt = float(np.median(np.diff(t)))
        ext, ret = moving_masks(d)
        res = {}
        for i, leg in enumerate(LEGS):
            kw = nominal(P, i)
            fp = d["F_pressure"][:, i]
            pr = d["rod_pressure"][:, i]
            ph = d["head_pressure"][:, i]
            tgt_e = p_ext(fp, kw["a_p"], kw["a_r"], P["p_set"], P["psi"], P["p_back"],
                          P["floor_g"], P["relief"])
            tgt_r = p_ret(fp, kw["a_p"], kw["a_r"], P["p_set"], P["psi"], P["floor_g"],
                          P["relief"])
            keep = math.exp(-dt / P["tau_v"])
            pred = np.full_like(pr, np.nan)
            y = math.nan
            for k in range(1, len(t)):
                mv = ext[k, i] or ret[k, i]
                if not mv:
                    y = math.nan
                    continue
                tgt_prev = tgt_e[k - 1] if ext[k, i] else tgt_r[k - 1]
                y = pr[k] if math.isnan(y) else tgt_prev + (y - tgt_prev) * keep
                pred[k] = y
            m_e = ext[:, i] & np.isfinite(pred)
            m_r = ret[:, i] & np.isfinite(pred)
            # identity residual p_r - max(p_back, p_set - psi p_h) while extending (truth)
            ident = pr - np.maximum(P["p_back"], P["p_set"] - P["psi"] * ph)
            # steady extension samples: target changed < 0.1 bar over the last 0.25 s
            n25 = max(int(round(0.25 / dt)), 1)
            tgt_span = np.full_like(pr, np.inf)
            for k in range(n25, len(t)):
                if ext[k - n25:k + 1, i].all():
                    seg = tgt_e[k - n25:k + 1]
                    tgt_span[k] = seg.max() - seg.min()
            steady = ext[:, i] & (tgt_span < 0.1 * BAR)
            grounded = d["N"][:, i] > 100.0
            # lock instants
            moving = ext[:, i] | ret[:, i]
            locks = []
            for k in np.flatnonzero(moving[:-60] & ~moving[1:-59]) + 1:
                if moving[k:k + 50].any():
                    continue
                direction = "ext" if ext[k - 1, i] else "ret"
                exp_ = (tgt_e if direction == "ext" else tgt_r)[k - 1]
                exp_now = (tgt_e if direction == "ext" else tgt_r)[k]
                locks.append(dict(t=float(t[k]), dir=direction, Fp_kN=float(fp[k] / 1e3),
                                  p_r0_rec_bar=float(pr[k + 1] / BAR),
                                  p_r0_formula_bar=float(exp_ / BAR),
                                  p_r0_formula_now_bar=float(exp_now / BAR),
                                  grounded=bool(grounded[k])))
            # locked law of the longest-pressure lock segment
            lk = ~moving
            seg_best = None
            k = 0
            n = len(t)
            while k < n:
                if not lk[k]:
                    k += 1
                    continue
                j = k
                while j < n and lk[j]:
                    j += 1
                if j - k > 20 and k > 0 and grounded[k] and fp[k] > 5e3:
                    mx = float(pr[k:j].max())
                    if seg_best is None or mx > seg_best[2]:
                        seg_best = (k, j, mx)
                k = j
            locked_check = None
            if seg_best is not None:
                k0, k1, mx = seg_best
                s_lock = float(d["s_motor"][k0, i])
                l0r = float(d["l0r"][i]) if d["l0r"] is not None else P["l0r"]
                k_h = P["beta"] * kw["a_p"] / (P["l0h"] + s_lock)
                k_r = P["beta"] * kw["a_r"] / (P["stroke"] - s_lock + l0r)
                share = k_r / (k_h + k_r)
                a0 = k0 + 1
                pred_l = np.maximum(P["floor_g"],
                                    pr[a0] - share * (fp[a0:k1] - fp[a0]) / kw["a_r"])
                kmax = a0 + int(np.argmax(pr[a0:k1]))
                locked_check = dict(t0=float(t[k0]), t1=float(t[k1 - 1]), s_lock_m=s_lock,
                                    share=share, p_r0_bar=float(pr[a0] / BAR),
                                    p_r_max_rec_bar=float(pr[a0:k1].max() / BAR),
                                    t_at_max=float(t[kmax]),
                                    p_r_at_max_pred_bar=float(pred_l[kmax - a0] / BAR),
                                    Fp_lock_kN=float(fp[a0] / 1e3), Fp_at_max_kN=float(fp[kmax] / 1e3),
                                    max_abs_resid_bar=float(np.max(np.abs(pred_l - pr[a0:k1])) / BAR))
            ge = m_e & grounded

            def rng(a):
                return [float(np.min(a) / BAR), float(np.max(a) / BAR)] if a.size else None

            res[leg] = dict(
                ext_grounded_p_r_bar=rng(pr[ge]),
                ext_grounded_Fp_kN=([float(fp[ge].min() / 1e3), float(fp[ge].max() / 1e3)]
                                    if ge.any() else None),
                ext_air_p_r_bar=rng(pr[m_e & ~grounded]),
                lag_model_max_abs_err_ext_bar=(float(np.max(np.abs(pred[m_e] - pr[m_e])) / BAR)
                                               if m_e.any() else None),
                lag_model_max_abs_err_ret_bar=(float(np.max(np.abs(pred[m_r] - pr[m_r])) / BAR)
                                               if m_r.any() else None),
                steady_ext_identity_resid_bar=rng(ident[steady]),
                steady_ext_target_minus_rec_bar=rng((tgt_e - pr)[steady]),
                locks=locks, locked_max=locked_check,
                cb_y_max=None)
        out[case.name] = res
    return out


# ---------------------------------------------------------------------------------------------
# C. D2 emulation and D. Monte Carlo

def d2_eligible(d, P, i):
    """Boolean at the 10 Hz samples + pad indices (two_pressure._check_moving, sign > 0 only)."""
    t10, u10 = d["t10"], d["u10"][:, i]
    idx = np.clip(np.searchsorted(d["t"], t10) - 1, 0, len(d["t"]) - 1)
    thr = D2_SPEED_FRACTION * P["v_max"]
    sign = np.where(np.abs(u10) < thr, 0.0, np.sign(u10))
    elig = np.zeros(len(t10), bool)
    since, last_sign, last_ret = None, 0.0, -math.inf
    for k in range(len(t10)):
        if u10[k] < 0.0:
            last_ret = t10[k]
        if sign[k] != last_sign:
            last_sign = sign[k]
            since = t10[k] if sign[k] else None
        if sign[k] <= 0 or d["N"][idx[k], i] <= 100.0:
            continue
        if t10[k] - since < D2_SETTLE_S - 1e-9 or t10[k] - last_ret < D2_REVERSAL_S - 1e-9:
            continue
        elig[k] = True
    return elig, idx


def held_max(resid, elig, hold=D2_HOLD_SAMPLES):
    """Largest r such that resid > r over `hold` consecutive eligible samples (needed margin)."""
    best = -math.inf
    k, n = 0, len(resid)
    while k < n:
        if not elig[k]:
            k += 1
            continue
        j = k
        while j < n and elig[j]:
            j += 1
        seg = resid[k:j]
        if seg.size >= hold:
            w = np.lib.stride_tricks.sliding_window_view(seg, hold).min(axis=1)
            best = max(best, float(w.max()))
        k = j
    return best


def bounds(P, i, ph, pr, form):
    a_p, a_r = P["a_p"][i], P["a_r"][i]
    if form == "poc12":
        return np.full_like(ph, D2_POC_HIGH)
    if form == "identity":
        return np.maximum(D2_POC_HIGH, P["p_set"] - P["psi"] * ph)
    if form == "Fp_head_only":
        return np.maximum(D2_POC_HIGH, p_ext(ph * a_p, a_p, a_r, P["p_set"], P["psi"],
                                             P["p_back"], P["floor_g"], P["relief"]))
    if form == "Fp_two_sensor":
        return np.maximum(D2_POC_HIGH, p_ext(ph * a_p - pr * a_r, a_p, a_r, P["p_set"],
                                             P["psi"], P["p_back"], P["floor_g"], P["relief"]))
    raise ValueError(form)


FORMS = ("poc12", "identity", "Fp_head_only", "Fp_two_sensor")


def wika_err(rng, n, p):
    """Normal grade static error at pressure p [Pa] for n draws; p shape (m,) -> (n, m)."""
    u = rng.uniform(-1.0, 1.0, (n, 7))
    off = (u[:, 0] * 1.2 + u[:, 1] * 0.4 + u[:, 6] * 0.4) * BAR
    gain = u[:, 3] * 0.005
    nl = u[:, 5] * 2.0 * BAR
    x = p / (400 * BAR)
    par = (x - x**2 - 1.0 / 6.0) / (1.0 / 6.0)
    e = off[:, None] + gain[:, None] * p[None, :] + nl[:, None] * par[None, :]
    return np.clip(e, -4 * BAR, 4 * BAR)


def mc_fallback(rng, P, i, ph, pr, form, margins, n=4000, noise=0.20 * BAR):
    """P(false fallback) of one eligible trace (contiguous segments marked by NaN breaks)."""
    out = {}
    if ph.size == 0:
        return out
    eh = wika_err(rng, n, ph) + rng.normal(0.0, noise, (n, ph.size))
    er = wika_err(rng, n, pr) + rng.normal(0.0, noise, (n, pr.size))
    phm, prm = ph[None, :] + eh, pr[None, :] + er
    a_p, a_r = P["a_p"][i], P["a_r"][i]
    if form == "identity":
        bnd = np.maximum(D2_POC_HIGH, P["p_set"] - P["psi"] * phm)
    else:  # two-sensor F_p form
        raw = (P["p_set"] * a_p - P["psi"] * (phm * a_p - prm * a_r)) / (a_p + P["psi"] * a_r)
        bnd = np.maximum(D2_POC_HIGH, np.clip(np.maximum(raw, P["p_back"]), P["floor_g"],
                                              P["relief"]))
    excess = prm - bnd
    for m in margins:
        viol = excess > m * BAR
        if viol.shape[1] < D2_HOLD_SAMPLES:
            out[m] = 0.0
            continue
        win = np.lib.stride_tricks.sliding_window_view(viol, D2_HOLD_SAMPLES, axis=1).all(axis=2)
        out[m] = float(win.any(axis=1).mean())
    return out


def segments(elig):
    segs, k, n = [], 0, len(elig)
    while k < n:
        if not elig[k]:
            k += 1
            continue
        j = k
        while j < n and elig[j]:
            j += 1
        segs.append((k, j))
        k = j
    return segs


def part_cd(P) -> dict:
    rng = np.random.default_rng(SEED)
    rows = []
    mc = []
    lock_rows = []
    batches = [CB_BATCH, *POC_BATCHES]
    for batch in batches:
        for case in sorted(p for p in batch.iterdir() if p.is_dir()):
            d = load_case(case)
            if d is None:
                continue
            is_cb = (d["lock_valve"] == "counterbalance")
            fs_tok = [tok for tok in case.name.split("_") if tok.startswith("Fs")]
            level = float(fs_tok[0][2:]) if fs_tok else math.nan
            ext, _ = moving_masks(d)
            for i, leg in enumerate(LEGS):
                a_p, a_r = P["a_p"][i], P["a_r"][i]
                elig, idx = d2_eligible(d, P, i)
                fp = d["F_pressure"][idx, i]
                if is_cb:
                    ph, pr = d["head_pressure"][idx, i], d["rod_pressure"][idx, i]
                else:  # CB-equivalent steady values from the same pressure force (4.3)
                    pr = p_ext(fp, a_p, a_r, P["p_set"], P["psi"], P["p_back"], P["floor_g"],
                               P["relief"])
                    ph = (fp + pr * a_r) / a_p
                # lock instants after an extension (CB-equivalent p_r0 at the lock force)
                mov = ext[:, i]
                fpl = d["F_pressure"][:, i]
                for k in np.flatnonzero(mov[:-60] & ~mov[1:-59]) + 1:
                    if mov[k:k + 50].any():
                        continue
                    pr0 = float(p_ext(fpl[k - 1], a_p, a_r, P["p_set"], P["psi"], P["p_back"],
                                      P["floor_g"], P["relief"]))
                    lock_rows.append(dict(batch=batch.name, case=case.name, leg=leg,
                                          side="front" if i < 2 else "rear", Fs_level=level,
                                          t=float(d["t"][k]), Fp_kN=float(fpl[k - 1] / 1e3),
                                          grounded=bool(d["N"][k, i] > 100.0),
                                          p_r0_cb_bar=pr0 / BAR,
                                          p_r_rec_bar=float(d["rod_pressure"][k + 1, i] / BAR)))
                if not elig.any():
                    continue
                row = dict(batch=batch.name, case=case.name, leg=leg,
                           side="front" if i < 2 else "rear", Fs_level=level, cb=is_cb,
                           n_elig=int(elig.sum()),
                           Fp_min_kN=float(fp[elig].min() / 1e3),
                           Fp_max_kN=float(fp[elig].max() / 1e3),
                           p_r_max_bar=float(pr[elig].max() / BAR),
                           p_r_min_bar=float(pr[elig].min() / BAR),
                           p_h_min_bar=float(ph[elig].min() / BAR))
                for form in FORMS:
                    resid = pr - bounds(P, i, ph, pr, form)
                    row[f"held_{form}_bar"] = held_max(resid, elig) / BAR
                    row[f"max_{form}_bar"] = float(resid[elig].max() / BAR)
                rows.append(row)
                # Monte Carlo on the longest eligible segments (concatenated, breaks kept)
                for form in ("identity", "Fp_two_sensor"):
                    probs = []
                    for k0, k1 in segments(elig):
                        if k1 - k0 >= D2_HOLD_SAMPLES:
                            probs.append(mc_fallback(rng, P, i, ph[k0:k1], pr[k0:k1], form,
                                                     MARGINS_BAR, n=2000))
                    if probs:
                        # independent segments share the same static draw in reality; take max
                        # over segments as the lower bound of the run probability
                        agg = {m: max(p[m] for p in probs) for m in MARGINS_BAR}
                        mc.append(dict(case=case.name, leg=leg, side=row["side"],
                                       Fs_level=level, cb=is_cb, form=form, p_fallback=agg))
    return {"d2_rows": rows, "mc": mc, "locks": lock_rows}


def summarize(P, a, b, cd) -> dict:
    s = {}
    rows = cd["d2_rows"]
    for side in ("front", "rear"):
        for lvl in (0.0, 2.0, 4.0, 8.0):
            sel = [r for r in rows if r["side"] == side and r["Fs_level"] == lvl]
            if not sel:
                continue
            key = f"{side}_Fs{lvl:g}"
            s[key] = dict(
                n_traces=len(sel),
                Fp_min_kN=min(r["Fp_min_kN"] for r in sel),
                Fp_max_kN=max(r["Fp_max_kN"] for r in sel),
                p_r_max_bar=max(r["p_r_max_bar"] for r in sel),
                case_of_p_r_max=max(sel, key=lambda r: r["p_r_max_bar"])["case"],
                **{f"held_{f}_max_bar": max(r[f"held_{f}_bar"] for r in sel) for f in FORMS},
                **{f"held_{f}_cases_over_3bar": sum(r[f"held_{f}_bar"] > 3.0 for r in sel)
                   for f in FORMS},
                **{f"held_{f}_cases_over_0": sum(r[f"held_{f}_bar"] > 0.0 for r in sel)
                   for f in FORMS})
            mcs = [m for m in cd["mc"] if m["side"] == side and m["Fs_level"] == lvl]
            for form in ("identity", "Fp_two_sensor"):
                ms = [m["p_fallback"] for m in mcs if m["form"] == form]
                if ms:
                    s[key][f"mc_{form}_max_p"] = {str(m): max(x[m] for x in ms) for m in MARGINS_BAR}
                    s[key][f"mc_{form}_mean_p"] = {str(m): float(np.mean([x[m] for x in ms]))
                                                   for m in MARGINS_BAR}
            lk = [r for r in cd["locks"] if r["side"] == side and r["Fs_level"] == lvl
                  and r["grounded"]]
            if lk:
                s[key]["lock_after_extend_grounded"] = dict(
                    n=len(lk), Fp_kN=[min(r["Fp_kN"] for r in lk), max(r["Fp_kN"] for r in lk)],
                    p_r0_cb_bar=[min(r["p_r0_cb_bar"] for r in lk),
                                 max(r["p_r0_cb_bar"] for r in lk)],
                    case_of_max=max(lk, key=lambda r: r["p_r0_cb_bar"])["case"])
            la = [r for r in cd["locks"] if r["side"] == side and r["Fs_level"] == lvl
                  and not r["grounded"]]
            if la:
                s[key]["lock_after_extend_air"] = dict(
                    n=len(la), p_r0_cb_bar=[min(r["p_r0_cb_bar"] for r in la),
                                            max(r["p_r0_cb_bar"] for r in la)])
    return s


def main() -> None:
    out_path = Path(sys.argv[1])
    P = load_params()
    a = part_a(P)
    b = part_b(P)
    cd = part_cd(P)
    summ = summarize(P, a, b, cd)
    result = {
        "params": {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in P.items()},
        "seed": SEED, "margins_bar": MARGINS_BAR,
        "A": a, "B_cb_batch": b, "C_summary": summ, "C_rows": cd["d2_rows"],
        "D_mc": cd["mc"], "locks": cd["locks"],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=1, default=float), encoding="utf-8")
    print(json.dumps(summ, indent=1, default=float))
    print("== C rows (CB batch, recorded truth)")
    for r in cd["d2_rows"]:
        if r["cb"]:
            print(r["case"], r["leg"], "n", r["n_elig"], "Fp", round(r["Fp_min_kN"], 2),
                  round(r["Fp_max_kN"], 2), "p_r", round(r["p_r_min_bar"], 2),
                  round(r["p_r_max_bar"], 2), "held poc12/id/ho/2s",
                  *(round(r[f"held_{f}_bar"], 2) for f in FORMS))
    print("== B")
    for case, res in b.items():
        for leg, r in res.items():
            print(case, leg, "ext_g p_r", r["ext_grounded_p_r_bar"], "Fp", r["ext_grounded_Fp_kN"],
                  "lagerr", r["lag_model_max_abs_err_ext_bar"], r["lag_model_max_abs_err_ret_bar"],
                  "steady id", r["steady_ext_identity_resid_bar"],
                  "locked", None if r["locked_max"] is None else
                  (round(r["locked_max"]["p_r_max_rec_bar"], 2),
                   round(r["locked_max"]["p_r_at_max_pred_bar"], 2),
                   round(r["locked_max"]["max_abs_resid_bar"], 3)))


if __name__ == "__main__":
    main()
