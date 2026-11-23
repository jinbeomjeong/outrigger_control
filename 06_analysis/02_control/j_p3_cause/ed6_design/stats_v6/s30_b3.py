"""Ed. 6 B3 (R-5 predicted early twist, spec rev. 1 3.3) - false R-5 rate, exposure of a false
twist, time gain, probe rule risk with the 8th arm (stats-design-expert, 2026-11-23, design only).

R-5 (c2.py 6096-6128, settings 994-1023, preset horizon 4 at 1630): on the lower load estimate
history of the last rate_intervals = 3 periods, fire when drop/period / T_s > 20 kN/s, the latest
period falls, and latest - drop * h < P5 (F_min + relevel margin, 7.0-7.5 kN; h = 4).
Watched only in READY (and PROBE with P-R8-11), c2.py 6070-6076.
Inputs (public / seen rows, O6-5): b3_r5_census.json (R-5 rows), b3_early_window.json
(R-5 -> reapproach 0.3-0.4 s, 3-4 reads, R12 32/32). Load noise sigma_F 0.32 kN/read (s20).
Twist speed: fastest leg 0.25 v_max (c2.py 1256) = 5.231 mm/s; max_travel_m 0.04 (c2.py 1266);
protect_margin_N 5 kN (c2.py 1259). Leg stiffness for the quasi-static twist-load sketch:
LOCK heave 8.88 Hz x 38,400.8 kg -> 1.2e8 N/m total, ~3e7 N/m per leg (ASSUMPTION; frame
torsion compliance unknown -> 1e7 / 2e7 also shown).
Writes s30_b3.json / .txt next to this file. stdout: status only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import beta, binom, norm

HERE = Path(__file__).resolve().parent
SEED = 20261114
F_MIN = 9.415
TS = 0.1
V_TW = 0.25 * 20.924          # mm/s
H = 4


def cp_up(k, n, conf=0.95):
    return float(beta.ppf(conf, k + 1, n - k)) if k < n else 1.0


def noise_r5(rng, n=2_000_000):
    """P(R-5 fires on one read | constant true load L, white noise sigma_F) - MC and bound."""
    out = {}
    for margin in (7.0, 7.5):
        p5 = F_MIN + margin
        for sig in (0.32, 0.6, 1.0, 2.0):
            for load in (p5 + 1.0, p5 + 4.0, p5 + 8.0, 30.0, 42.0):
                y = load + rng.normal(0.0, sig, (n, 4))
                d = (y[:, 0] - y[:, 3]) / 3.0
                fire = (d / TS > 20.0) & (y[:, 2] > y[:, 3]) & (y[:, 3] - d * H < p5)
                need = max(2.0, (load - p5) / H)
                bound = float(norm.sf(need * 3.0 / (sig * np.sqrt(2.0))))
                out[f"m{margin}|sig{sig}|L{load:.1f}"] = {"mc": float(fire.mean()),
                                                         "z_bound": bound}
    return out


def exposure() -> dict:
    """Fastest-leg twist travel and a rigid-deck quasi-static load-transfer sketch."""
    per_cycle = V_TW * TS                     # mm per cycle at full twist speed
    out = {"per_cycle_mm": per_cycle, "true_event_window_mm": [3 * per_cycle, 4 * per_cycle],
           "false_event": {}, "load_sketch": {}}
    for nb in (1, 2, 3, 4, 5):
        cyc = nb + 1 + 1                      # N_B3 releases + detection read + output delay d=1
        out["false_event"][f"N{nb}"] = {"cycles": cyc, "travel_mm": cyc * per_cycle}
    for k in (1e7, 2e7, 3e7):
        dF = k * per_cycle * 1e-3 / 1e3       # kN per cycle per leg, all four legs +-a
        out["load_sketch"][f"k{k:.0e}"] = {
            "dF_per_cycle_kN": dF,
            "protect_level_kN": F_MIN + 5.0,
            "min_after_one_delay_cycle_kN": F_MIN + 5.0 - dF,
            "lift_possible": bool(F_MIN + 5.0 - dF < 0.0)}
    return out


def empirical() -> dict:
    return {
        "false_r5_per_nonevent_row_upper95": {
            "independent_330": cp_up(0, 330), "row_clusters_66": cp_up(0, 66)},
        "false_prediction_among_firings_upper95": {
            "VBJ_R12_32": cp_up(0, 32), "key_clusters_15": cp_up(0, 15)},
        "note": "R14 (2 rows x 5 settings) fired R-5; whether a reapproach followed is not in "
                "the census (not checked)"}


def probe_risk() -> dict:
    """Rule (b) with arm 8 (all - B3): B3 removed if arm 8 has fewer failing keys than arm 6.
    B3 acts only on R-5 keys: R12 o0.0 + 3 G4 keys = 4 keys x 5 plants = 20 units; the other 4
    keys give identical commands (P6-6). Neutral B3, divergence flips p per unit."""
    out = {}
    for n_units, label in ((20, "units_20"), (4, "key_clusters_4")):
        for p in (0.01, 0.02, 0.05, 0.10, 0.20):
            pm = binom.pmf(np.arange(n_units + 1), n_units, p)
            cdf = np.cumsum(pm)
            p_less = float(sum(pm[j] * (cdf[j - 1] if j > 0 else 0.0) for j in range(n_units + 1)))
            out[f"{label}|p{p}"] = {"P_remove_by_chance": p_less}
    # missing B3 harm that only R14 / non-probe events would show
    for pi in (0.05, 0.10, 0.25):
        out[f"harm_keys_unseen|pi{pi}"] = float((1 - pi) ** 4)
    return out


def main() -> int:
    rng = np.random.default_rng(SEED)
    out = {"seed": SEED, "noise_r5": noise_r5(rng), "empirical": empirical(),
           "exposure": exposure(), "probe_rule": probe_risk()}
    chk = {"large_sigma_fires": out["noise_r5"]["m7.0|sig2.0|L17.4"]["mc"] > 0,
           "tiny_sigma_never": out["noise_r5"]["m7.0|sig0.32|L42.0"]["mc"] == 0.0}
    chk["ok"] = all(chk.values())
    out["self_checks"] = chk
    (HERE / "s30_b3.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item()),
                                      encoding="utf-8")
    L = [f"self_checks {chk}", "== noise-only R-5 per read (mc / z bound) =="]
    for k, v in out["noise_r5"].items():
        L.append(f"  {k:<22} {v['mc']:.2e} / {v['z_bound']:.2e}")
    L.append(f"== empirical == {json.dumps(out['empirical'])}")
    L.append(f"== exposure == {json.dumps(out['exposure'])}")
    L.append(f"== probe rule == {json.dumps(out['probe_rule'])}")
    (HERE / "s30_b3.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("ok" if chk["ok"] else "self_check_failed")
    return 0 if chk["ok"] else 3


if __name__ == "__main__":
    sys.exit(main())
