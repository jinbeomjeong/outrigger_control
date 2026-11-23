"""Ed. 6 recheck of A(i) / A(ii) with the hydraulics-v6 values adopted by the user (2026-11-23)
(stats-design-expert, review of ed6_design/hydraulics_v6/h6_review_report.md, design only).

Adopted values (h6 report 1-5, user decision 2026-11-23):
  A(i): u_cap 1.05 mm/s, du_step 0.2 mm/s per cycle, start max(|u|, u_hold), N_cap 40;
        above-threshold flow: net charge u when |u| >= r_th (h6 5: drain gate 0), else 0.
        The leg moves only after the remaining fill x_f is charged (A(i) alone on a loaded retract:
        x_f up to 3.1 mm, h6 5 table; after A(ii) robust floor ~0.9 mm: ~2.2 mm).
  A(ii): robust lower bound, kappa 1.0, void by the two-chamber reconstruction (h6 1, beta 1.6 on
        the head term); retract witness = rod pressure rise >= max(3 bar, 0.5 (p_open,lb - p_r0))
        on one read, or ds >= 1.0 mm; extension A(ii) dropped from the probe.
Kept from the first design (s10): trigger E3, N_trig 10, D_trig 0.5 mm, eta 0.25; witness E3
s_w,A 0.4 mm (also 0.5 and E1 shown). Noise: stroke 0.1 mm/read; pressure 0.20 bar/read
(normal grade, h6 3), static offsets cancel in same-sensor differences.
Parts: A episode table, B trigger confirmation (+ overtravel of a false trigger on a moving leg),
C A(ii) surrogate overfill check of the robust set (+ friction sensitivity), D witness noise.
Writes s21_recheck_h6.json / .txt next to this file. stdout: status only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import norm

HERE = Path(__file__).resolve().parent
SEED = 20261114
TS, SIG, U_HOLD = 0.1, 0.1, 0.209243
U_CAP, DU, N_CAP = 1.05, 0.2, 40


def ds_obs(r, est):
    if est == "E1":
        return r - r[:, :1]
    c = np.full_like(r, np.nan)
    c[:, 2:] = (r[:, :-2] + r[:, 1:-1] + r[:, 2:]) / 3.0
    return c - r[:, :3].mean(1, keepdims=True)


def episode(rng, reps, u_ctrl, r_th, x_f, s_w, est, f_move=None, k_max=60):
    """A(i) episode from the trigger cycle. f_move: if set, the leg is already moving at
    f_move * u_eff (false-trigger case, r_th/x_f ignored)."""
    k = np.arange(k_max + 3)
    start = max(u_ctrl, U_HOLD)
    uk = np.minimum(start + DU * k, U_CAP)
    ueff = np.maximum(u_ctrl, uk)
    if f_move is not None:
        v = f_move * ueff
    else:
        charge = np.where(ueff >= r_th, ueff, 0.0) * TS
        cum = np.cumsum(charge)
        moved = np.clip(cum - x_f, 0.0, None)
        v = np.diff(np.concatenate([[0.0], moved])) / TS
    s_true = np.concatenate([[0.0], np.cumsum(v * TS)])[: k.size]
    r = s_true[None, :] + rng.normal(0.0, SIG, (reps, k.size))
    ds = np.nan_to_num(ds_obs(r, est), nan=-1e9)
    k_cap = int(np.argmax(uk >= U_CAP - 1e-12))
    k_end = min(k_cap + N_CAP, k_max)
    wit = ds >= s_w
    wit[:, k_end + 1:] = False
    has = wit.any(1)
    kw = np.where(has, wit.argmax(1), k_end)
    pulse = s_true[kw]
    pulse_d = s_true[np.minimum(kw + 2, k.size - 1)]      # + current cycle + output delay d = 1
    intended = f_move * u_ctrl * TS * (kw + 2) if f_move is not None else 0.0
    out = {"p_witness": float(has.mean()), "end_s_median": float(np.median(kw) * TS),
           "end_s_p95": float(np.percentile(kw, 95) * TS),
           "pulse_p95_mm": float(np.percentile(pulse, 95)),
           "overtravel_d1_p95_mm": float(np.percentile(pulse_d - intended, 95)),
           "p_false_end": float((has & (pulse < 0.5 * s_w)).mean())}
    return out


def part_a(rng, reps=5000):
    rows = []
    for est in ("E3", "E1"):
        for s_w in (0.4, 0.5):
            row = {"est": est, "s_w": s_w, "by_case": {}}
            for x_f in (0.0, 0.33, 2.2, 3.1):
                for r_th in (0.10, 0.39, 0.62, 0.81, 1.2):
                    row["by_case"][f"xf{x_f}|r{r_th}"] = episode(rng, reps, 0.3, r_th, x_f, s_w,
                                                                 est)
            for f in (1.0, 0.85, 0.7):
                row["by_case"][f"moving_f{f}"] = episode(rng, reps, 0.3, 0.0, 0.0, s_w, est,
                                                         f_move=f)
            rows.append(row)
    return rows


def part_b(rng, reps=20000, L=100):
    """Trigger E3 N10 D0.5 eta0.25 (unchanged by the ramp values): moving FT and stall delay."""
    def first(s_true, u):
        r = s_true[None, :] + rng.normal(0.0, SIG, (reps, s_true.size))
        ds = ds_obs(r, "E3")
        k = np.arange(s_true.size)
        d = k * u * TS
        trig = ((k >= 10) & (d >= 0.5 - 1e-12))[None, :] & (ds < 0.25 * d[None, :])
        return np.where(trig.any(1), trig.argmax(1), -1)
    out = {"moving": {}, "stall": {}}
    for u in (0.25, 0.3, 0.4, 0.6):
        for f in (1.0, 0.85, 0.7):
            fr = first(f * u * TS * np.arange(L + 1), u)
            out["moving"][f"u{u}_f{f}"] = float((fr >= 0).mean())
    for u in (0.22, 0.4, 0.75):
        fr = first(np.zeros(L + 1), u)
        ok = fr >= 0
        out["stall"][f"u{u}"] = {"p_detect": float(ok.mean()),
                                 "median_s": float(np.median(fr[ok]) * TS),
                                 "p95_s": float(np.percentile(fr[ok], 95) * TS)}
    return out


def g_psi(psi):
    return (3.5 / psi) ** 1.253          # fit to h1 psi row (s20)


def part_c(rng, n=400_000):
    """Robust lower bound vs surrogate truth (components as s20; h6 1 robust set: psi 6, beta 1.6,
    V_line x0.5, beta_hose 1.0, L0r 0.02, p_cr 1 bar, read margin 4 bar, band 2 F_s,max - the band
    term is NOT modelled in x_lb (conservative for this check), friction in the truth is a
    need-reduction fraction phi)."""
    ph = rng.uniform(40.0, 130.0, n)
    sc = (ph + 1.0) / 122.8
    rod, head, line = 1.18 * sc, 0.19 * sc, 0.53 * sc
    void = rng.uniform(0.0, 1.5, n)

    def logu(lo, hi):
        return np.exp(rng.uniform(np.log(lo), np.log(hi), n))
    beta, vline = logu(0.69, 1.6), logu(0.5, 2.0)
    bhose, psi = logu(0.3, 1.0) / 0.5, logu(3.2, 6.0)
    l0r_fac = rng.uniform(0.97, 1.06, n)                       # h1 L0r row on the total
    err = np.exp(rng.normal(0.0, 0.045, n))
    need0 = (void + (rod * l0r_fac / beta + head / beta + line * vline / bhose) * g_psi(psi)) * err
    # x_lb robust: void reconstruction (beta 1.6 on head term; under-estimate, h6 1: -1.17..-0.05)
    void_est = np.clip(void * beta / 1.6 + rng.normal(0.0, 0.01, n), 0.0, None)
    # p_open driver p_h + p_cr - p_T: truth (p_h + 1) with p_cr 3; bound (p_h_read - 4 + 1 - 2)
    ph_read = ph + rng.normal(0.0, 0.2, n) + rng.uniform(-2.0, 2.0, n)   # offset within +-2 bar
    sc_lb = np.clip((ph_read - 4.0 - 1.0) / 122.8, 0.0, None)
    rod_lb = 1.18 * (1.0 - 0.03 * 3.11 / 1.18)                 # L0r 0.02 -> total x0.97
    x_lb = void_est + (rod_lb / 1.6 + 0.19 / 1.6 + 0.53 * 0.5 / 2.0) * g_psi(6.0) * sc_lb
    res = {"x_lb_over_need_quantiles": [float(q) for q in np.percentile(x_lb / need0,
                                                                        [50, 90, 99, 99.9, 100])],
           "by_phi": {}}
    for phi in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5):
        need = need0 * (1.0 - phi)
        over = x_lb - need
        res["by_phi"][str(phi)] = {"p_overfill": float((over > 0).mean()),
                                   "overfill_p999_mm": float(np.percentile(np.clip(over, 0, None),
                                                                           99.9)),
                                   "overfill_max_mm": float(over.max())}
    # phi at which overfill first appears = 1 - max(x_lb/need0)
    res["phi_break"] = float(1.0 - (x_lb / need0).max())
    res["fill_fraction_median"] = float(np.median(np.minimum(x_lb / need0, 1.0)))
    return res


def part_d(rng, reps=200_000):
    """Witness noise: rod rise w_r = p_r(k) - min p_r over [k_s, k] >= 3 bar with no true rise,
    looks over 50 reads; ds >= 1.0 mm (E1) over 40 looks with no motion; harness detection margin."""
    p = rng.normal(0.0, 0.2, (reps // 10, 51))
    w = p - np.minimum.accumulate(p, axis=1)
    out = {"rod_false_50reads": float((w[:, 1:] >= 3.0).any(1).mean()),
           "rod_w_max_p999_bar": float(np.percentile(w.max(1), 99.9)),
           "ds1mm_false_40looks_bound": float(40 * norm.sf(1.0 / (SIG * np.sqrt(2)))),
           "rod_threshold_example_bar": float(max(3.0, 0.5 * ((120 - 4 + 1 - 2) / 6 + 0.913)))}
    return out


def main() -> int:
    rng = np.random.default_rng(SEED)
    chk = {}
    e = episode(rng, 2000, 0.3, 5.0, 0.0, 0.4, "E3")
    chk["never_open_pulse0"] = e["pulse_p95_mm"] == 0.0
    e = episode(rng, 2000, 0.3, 0.0, 0.0, 0.4, "E3", f_move=1.0)
    chk["moving_witness1"] = e["p_witness"] == 1.0
    chk["ok"] = all(chk.values())
    out = {"seed": SEED, "values": {"u_cap": U_CAP, "du_step": DU, "N_cap": N_CAP},
           "self_checks": chk, "A_episode": part_a(rng), "B_trigger": part_b(rng),
           "C_aii_robust": part_c(rng), "D_witness_noise": part_d(rng)}
    (HERE / "s21_recheck_h6.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item()),
                                              encoding="utf-8")
    L = [f"values {out['values']} self_checks {chk}",
         "== A(i) episode (u_ctrl 0.3): p_witness / end p95 s / pulse p95 / overtravel(d=1) p95 / "
         "p_false_end =="]
    for row in out["A_episode"]:
        L.append(f"-- {row['est']} s_w {row['s_w']}")
        for c, x in row["by_case"].items():
            L.append(f"  {c:<14} {x['p_witness']:.3f} / {x['end_s_p95']:.1f} / "
                     f"{x['pulse_p95_mm']:.2f} / {x['overtravel_d1_p95_mm']:.2f} / "
                     f"{x['p_false_end']:.4f}")
    L.append(f"== trigger E3 N10 D0.5 eta0.25 == {json.dumps(out['B_trigger'])}")
    L.append(f"== A(ii) robust kappa 1 == {json.dumps(out['C_aii_robust'])}")
    L.append(f"== witness noise == {json.dumps(out['D_witness_noise'])}")
    (HERE / "s21_recheck_h6.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("ok" if chk["ok"] else "self_check_failed")
    return 0 if chk["ok"] else 3


if __name__ == "__main__":
    sys.exit(main())
