"""Ed. 6 A(ii) lock-start fill floor and B event-response thresholds (stats-design-expert,
2026-11-23, design only). Writes s20_aii_b.json and s20_aii_b.txt next to this file.

Part 1 - A(ii) delivered command under the per-cycle increment limit (c2.py:10076-10089,
  |du| <= 0.25 v_max per cycle both ways, v_max 20.924 mm/s, T_s 0.1 s). Two rules:
  "spec": |u| = max(|u_ctrl|, u_fill = v_max) until X >= x_lb, then back to u_ctrl (ramp-down
          also limited) - spec 3.2 wording;
  "deadbeat": the fill command is planned so that X plus the limited ramp-down tail lands on
          x_lb (largest feasible speed each cycle).
Part 2 - kappa_fill guarantee: Monte Carlo over hydraulic parameter priors with a component
  surrogate of the loaded-retract dead stroke calibrated to the hydraulics review
  (ed5_j9fail_606f8713/hydraulics/h1_p1_review_report.md:66-87: components void/rod/line/head
  median 1.21/1.18/0.53/0.19 mm; need ratios psi 3.0/4.2/6.0 -> 1.13/0.87/0.70, beta 0.69/1.6 ->
  1.20/0.84, beta_hose 0.3/1.0 -> 1.11/0.92, V_line x0.5/x2 -> 0.92/1.17, L0r 0.97..1.06).
  Surrogate: need = void + (rod*b + head*b + line*v/h) * g(psi), b = 1/beta_rel,
  v = V_line_rel, h = beta_hose_rel, g = (3.5/psi)^1.253 (fit to the psi row), times a model
  error factor exp(N(0, 0.045)) (record vs recomputed need <= 0.29 mm, review :97).
  x_lb = kappa * [void_part + (rod*b_lo + head*b_lo + line*v_lo/h_lo) * g(psi_lo)] * (p_read factor).
Part 3 - B noise: load estimate noise sigma_F (reduced model 0.3 kN head-force noise,
  sensors/hydraulic.py:53, rod 0.3 bar x A_ann) plus static offset b; B1 end (>= F_min + m for
  N_B samples) and B2 start (< 1.4 F_min for required_samples, c2.py:6230-6250, preset 2).
stdout: status only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import norm

HERE = Path(__file__).resolve().parent
SEED = 20261114
TS = 0.1
VMAX = 20.924
DU = 0.25 * VMAX


def delivered(x_lb: float, rule: str, u_ctrl: float = 0.3) -> dict:
    """Command displacement [mm] delivered from a lock start (u_prev = 0)."""
    u_prev, X, seq = 0.0, 0.0, []
    if rule == "spec":
        while X < x_lb - 1e-12:
            u = min(VMAX, u_prev + DU)
            X += u * TS
            seq.append(u)
            u_prev = u
        fill_cycles = len(seq)
        while u_prev > u_ctrl + 1e-12:          # limited ramp-down to the controller command
            u = max(u_ctrl, u_prev - DU)
            if u <= u_ctrl + 1e-12:
                break
            X += u * TS
            seq.append(u)
            u_prev = u
        return {"x_lb": x_lb, "X_total": X, "fill_cycles": fill_cycles, "cycles": len(seq),
                "excess_over_xlb": X - x_lb}
    # deadbeat: each cycle take the largest u with u <= u_prev + DU such that the remaining
    # amount can still be met including a limited ramp-down to 0
    rem = x_lb
    while rem > 1e-9:
        best = 0.0
        hi = min(VMAX, u_prev + DU)
        for u in np.linspace(hi, 0.0, 2001):
            tail, v = 0.0, u - DU
            while v > 0:
                tail += v * TS
                v -= DU
            if u * TS + tail <= rem + 1e-9:
                best = u
                break
        if best <= 1e-9:
            best = min(hi, rem / TS)
        X += best * TS
        rem -= best * TS
        seq.append(best)
        u_prev = best
        if len(seq) > 50:
            break
    return {"x_lb": x_lb, "X_total": X, "fill_cycles": len(seq), "cycles": len(seq),
            "excess_over_xlb": X - x_lb, "profile_mm_s": [round(s, 3) for s in seq]}


def g_psi(psi):
    return (3.5 / psi) ** 1.253


def need_model(void, rod, head, line, beta_rel, vline_rel, bhose_rel, psi):
    return void + (rod / beta_rel + head / beta_rel + line * vline_rel / bhose_rel) * g_psi(psi)


def kappa_mc(rng, n=200_000) -> dict:
    # per-fill nominal components: scale rod/head/line with p_h (p_open ~ p_h / psi);
    # p_h ~ U(40, 130) bar relative to 121.8 bar; void ~ U(0, 1.5) mm (record 0..~1.5)
    ph = rng.uniform(40.0, 130.0, n)
    sc = (ph + 1.0) / (121.8 + 1.0)
    rod, head, line = 1.18 * sc, 0.19 * sc, 0.53 * sc
    void = rng.uniform(0.0, 1.5, n)

    def logu(lo, hi):
        return np.exp(rng.uniform(np.log(lo), np.log(hi), n))
    beta = logu(0.69, 1.6)          # GPa, nominal 1.0
    vline = logu(0.5, 2.0)
    bhose = logu(0.3, 1.0) / 0.5    # relative to nominal 0.5 GPa
    psi = logu(3.2, 6.0)            # head-side check data psi >= 3.2..4.2 (review :174)
    err = np.exp(rng.normal(0.0, 0.045, n))
    need_true = need_model(void, rod, head, line, beta, vline, bhose, psi) * err
    # pressure read error on p_h (normal grade 0.2 bar noise + residual offset U(-1, 1) bar)
    ph_read = ph + rng.normal(0.0, 0.2, n) + rng.uniform(-1.0, 1.0, n)
    rsc = (ph_read + 1.0) / (ph + 1.0)
    res = {}
    for void_mode in ("exclude", "estimate", "nominal"):
        if void_mode == "exclude":
            vpart = 0.0
        elif void_mode == "estimate":   # void ~ (L0h+s) dp_h / beta, read with beta_lo 1.6
            vpart = void * beta / 1.6 * np.exp(rng.normal(0.0, 0.10, n))
        else:                           # spec example: nominal void counted in x_need
            vpart = 1.21
        for bh_lo in (0.5, 1.0):
            base = vpart + (rod / 1.6 + head / 1.6 + line * 0.5 / (bh_lo / 0.5)) * g_psi(6.0)
            base = base * rsc
            for kappa in (1.0, 0.9, 0.8, 0.7, 0.6):
                x_lb = kappa * base
                over = x_lb - need_true
                res[f"{void_mode}|bhose_lo{bh_lo}|k{kappa}"] = {
                    "p_overfill": float((over > 0).mean()),
                    "overfill_mm_p99": float(np.percentile(np.clip(over, 0, None), 99)),
                    "overfill_mm_max": float(over.max()),
                    "fill_fraction_median": float(np.median(np.minimum(x_lb / need_true, 1.0))),
                    "x_lb_median_mm": float(np.median(x_lb))}
    res["need_true_quantiles_mm"] = [float(q) for q in np.percentile(need_true, [1, 10, 50, 90, 99])]
    return res


def b_noise() -> dict:
    a_h, a_ann = 1.3273e-2, 3.770e-3
    s_f = float(np.hypot(0.300, 0.3e5 * a_ann / 1e3))       # kN, front leg
    out = {"sigma_F_kN": s_f, "B1_false_end": {}, "B2_false_start": {}}
    # B1: P(N_B consecutive reads >= F_min + m | true load = F_min) over a W-sample stay
    for off in (0.0, 0.5, 1.0):
        for m in (0.5, 1.0, 1.5, 2.0, 3.0, 5.0):
            p1 = float(norm.sf((m - off) / s_f))
            for nb in (1, 2, 3):
                pr = p1 ** nb
                for w in (10, 50):
                    out["B1_false_end"][f"off{off}|m{m}|N{nb}|W{w}"] = float(
                        1 - (1 - pr) ** max(w - nb + 1, 1))
    # B2: true load hovering d kN above the start level 1.4 F_min for W samples
    for d in (0.25, 0.5, 1.0, 1.5):
        p1 = float(norm.cdf(-d / s_f))
        for req in (1, 2):
            for w in (5, 20):
                out["B2_false_start"][f"d{d}|req{req}|W{w}"] = float(
                    1 - (1 - p1 ** req) ** max(w - req + 1, 1))
    return out


def main() -> int:
    rng = np.random.default_rng(SEED)
    out = {"seed": SEED, "quantum": {}, "kappa": kappa_mc(rng), "B": b_noise()}
    for x in (0.1, 0.2, 0.4, 0.523, 1.0, 1.7, 2.5, 3.5):
        out["quantum"][str(x)] = {"spec": delivered(x, "spec"), "deadbeat": delivered(x, "deadbeat")}
    chk = {"spec_single_cycle": abs(delivered(0.3, "spec")["X_total"] - DU * TS) < 1e-9,
           "deadbeat_hits": all(abs(out["quantum"][k]["deadbeat"]["X_total"] - float(k)) < 1e-3
                                for k in out["quantum"])}
    chk["ok"] = all(chk.values())
    out["self_checks"] = chk
    (HERE / "s20_aii_b.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item()),
                                         encoding="utf-8")
    L = [f"self_checks {chk}", "== A(ii) delivered command X_total [mm] (spec / deadbeat) =="]
    for k, v in out["quantum"].items():
        L.append(f"x_lb {k:>5}: spec {v['spec']['X_total']:.3f} (fill {v['spec']['fill_cycles']} "
                 f"cyc, total {v['spec']['cycles']}) | deadbeat {v['deadbeat']['X_total']:.3f} "
                 f"({v['deadbeat']['cycles']} cyc) {v['deadbeat'].get('profile_mm_s')}")
    L.append("== kappa: p_overfill / overfill p99 mm / max / fill fraction median / x_lb median ==")
    for k, v in out["kappa"].items():
        if isinstance(v, dict):
            L.append(f"{k:<28} {100*v['p_overfill']:6.2f}% {v['overfill_mm_p99']:.3f} "
                     f"{v['overfill_mm_max']:.3f} {v['fill_fraction_median']:.2f} "
                     f"{v['x_lb_median_mm']:.2f}")
    L.append(f"need_true q01/10/50/90/99 {out['kappa']['need_true_quantiles_mm']}")
    L.append(f"== B: sigma_F {out['B']['sigma_F_kN']:.3f} kN ==")
    for k, v in out["B"]["B1_false_end"].items():
        if "W50" in k:
            L.append(f"B1 {k:<22} {100*v:8.4f}%")
    for k, v in out["B"]["B2_false_start"].items():
        L.append(f"B2 {k:<22} {100*v:8.4f}%")
    (HERE / "s20_aii_b.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("ok" if chk["ok"] else "self_check_failed")
    return 0 if chk["ok"] else 3


if __name__ == "__main__":
    sys.exit(main())
