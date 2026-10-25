"""WIKA A-10 (0-400 bar) error model: net cylinder force error per leg, before / after the
airborne zero calibration. Monte Carlo over sensor parameter draws (seed fixed).

Per sensor: p_meas = p + o + g p + NL(p) + rep, with
  o   offset (zero + temperature zero shift + drift), uniform
  g   span (gain) error, uniform
  NL  BFSL-type shape A * (x - x^2 - 1/6) / (1/6), x = p / 400, amplitude A uniform
  rep non-repeatability per run, uniform +-0.4 bar
Normal grade total is capped at the datasheet +-4 bar (1 % span, excluding temperature).
Airborne zero calibration (legs in air, F = -m_rod g known) removes the combination
o_h A_p - o_r A_ann and the error at the calibration pressures (p_h ~ 1 bar, p_r ~ 5 bar);
it cannot remove span, NL slope, or temperature change after the calibration.
"""

import json
from pathlib import Path

import numpy as np

# --- paths (migrated from the 2026-10-22 session scratchpad ctrl-run on 2026-10-25) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[3]  # 04_scripts/03_control/s6_rev01_28/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s6_rev01_28"  # results of these scripts
OUT_DIR.mkdir(parents=True, exist_ok=True)
_sys.path.append(str(REPO / "04_scripts" / "03_control"))  # siblings migrated earlier
# ---
SPAN = 400.0
LEGS = {"front": dict(Ap=1.3273e-2, Aann=3.7699e-3, mg=1047.0),
        "rear": dict(Ap=9.5033e-3, Aann=3.1416e-3, mg=717.7)}
F_MIN = 9414.55
LOADS = {"static_front": ("front", 118.22e3), "static_rear": ("rear", 71.96e3),
         "guard_front": ("front", F_MIN + 5e3), "guard_rear": ("rear", F_MIN + 5e3),
         "p350_front": ("front", 350e5 * 1.3273e-2), "p350_rear": ("rear", 350e5 * 9.5033e-3)}
P_ROD_LOCK = 2.0  # bar, extend-locked rod side
P_CAL_HEAD, P_CAL_ROD = 1.0, 5.0  # bar, airborne extension
CASES = {
    # name: offset half-range [bar], span [-], NL amplitude [bar], temperature zero [bar],
    #       temperature span [-], cap [bar or None]
    "normal": dict(o=1.2, g=0.005, nl=2.0, tz=0.0, tg=0.0, cap=4.0),
    "conservative": dict(o=1.2, g=0.005, nl=2.0, tz=4.0, tg=0.005, cap=None),
    "old_worst": dict(o=1.2, g=0.005, nl=2.0, tz=10.0, tg=0.01, cap=None),
}
N = 200_000
rng = np.random.default_rng(20261022)


def nl_shape(p):
    x = p / SPAN
    return (x - x**2 - 1.0 / 6.0) / (1.0 / 6.0)


def draw(case, n):
    c = CASES[case]
    u = lambda h: rng.uniform(-h, h, n)  # noqa: E731
    return dict(o=u(c["o"]) + u(c["tz"]) + u(0.4), g=u(c["g"]) + u(c["tg"]), A=u(c["nl"]),
                rep=u(0.4), cap=c["cap"])


def err(s, p):
    e = s["o"] + s["g"] * p + s["A"] * nl_shape(p) + s["rep"]
    if s["cap"] is not None:
        e = np.clip(e, -s["cap"] - 0.4, s["cap"] + 0.4)
    return e


out = {"N": N, "seed": 20261022, "cases": {}}
for case in CASES:
    sh, sr = draw(case, N), draw(case, N)
    res = {}
    for name, (leg, F) in LOADS.items():
        g = LEGS[leg]
        p_h = (F + P_ROD_LOCK * 1e5 * g["Aann"]) / g["Ap"] / 1e5
        dF = err(sh, p_h) * 1e5 * g["Ap"] - err(sr, P_ROD_LOCK) * 1e5 * g["Aann"]
        # airborne zero calibration: subtract the error seen at the calibration point
        dF_cal = dF - (err(sh, P_CAL_HEAD) * 1e5 * g["Ap"] - err(sr, P_CAL_ROD) * 1e5 * g["Aann"])
        # rep is redrawn per run: the calibrated residual keeps one fresh repeatability term
        res[name] = {
            "p_head_bar": p_h,
            "uncal_p95_kN": float(np.percentile(np.abs(dF), 95)) / 1e3,
            "uncal_max_kN": float(np.abs(dF).max()) / 1e3,
            "cal_p95_kN": float(np.percentile(np.abs(dF_cal), 95)) / 1e3,
            "cal_max_kN": float(np.abs(dF_cal).max()) / 1e3,
            "head_bar_p95_uncal": float(np.percentile(np.abs(err(sh, p_h)), 95)),
        }
    out["cases"][case] = res
# deterministic bounds (datasheet linear)
out["linear_bounds_kN"] = {
    leg: {"head_4bar": 4e5 * g["Ap"] / 1e3, "rod_4bar": 4e5 * g["Aann"] / 1e3,
          "head_10bar": 10e5 * g["Ap"] / 1e3, "head_14p4bar": 14.4e5 * g["Ap"] / 1e3,
          "rod_14p4bar": 14.4e5 * g["Aann"] / 1e3, "noise_0p2bar_dual": 0.2e5 * np.hypot(g["Ap"], g["Aann"]) / 1e3}
    for leg, g in LEGS.items()}
(OUT_DIR / _Path(__file__).name).with_suffix(".json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
