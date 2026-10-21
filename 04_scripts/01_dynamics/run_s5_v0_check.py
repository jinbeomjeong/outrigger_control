"""S5 final judgement support (dynamics_model.md 5.9, rev. 22): V0(auger) and the V10 load rule.

Usage (project root, dynamics-dev):
    conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_s5_v0_check.py
Writes 06_analysis/00_dynamics/s5_v0_check.json. Independent of 03_src (YAML text,
auger_levels.json, the S5 verify JSON and s1_pdelta_check.json are read only).

A  V0(auger) in exact rational arithmetic on the printed YAML decimals:
   fixed_part + auger_moving_set_at_cad_pose translated by auger_travel_m along body +z vs
   superstructure.auger_levels.<level> (mass, CoM, inertia about the CoM, body axes, tensor
   notation). Residuals, plan metrics (1e-9: mass rel, CoM abs m, inertia rel to max |I|),
   element-wise relative residuals, and the first-order printed-digit rounding bound
       b_j = h_ref,j + sum_k |d out_j / d in_k| h_k      (h = half a unit in the last printed digit)
   with and without the travel term. Travel consistency: YAML travel == auger_levels.json
   travel_mm * 1e-3 (the exporter composes the level from that same number). Fault injection
   shows which rule catches which error.
B  V10 load rule: Chrono still-window means (verify_S5_L1.json) vs linear reference and vs the
   independent P-delta solution (s1_pdelta_check.json); P-delta share per CoM height h above the
   ball centres; usage of 0.1 % W/4 and its scaling with weight (ASSUMPTION: same k, geometry, CoM).
"""

from __future__ import annotations

import json
from decimal import Decimal
from fractions import Fraction as F
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
YAML_PATH = ROOT / "02_params" / "rexome33.yaml"
AUGER_JSON = ROOT / "01_cad" / "03_auger" / "auger_levels.json"
S5_JSON = ROOT / "06_analysis" / "01_chrono" / "15_S5" / "verify_S5_L1.json"
PDELTA_JSON = ROOT / "06_analysis" / "00_dynamics" / "s1_pdelta_check.json"
OUT = ROOT / "06_analysis" / "00_dynamics" / "s5_v0_check.json"

LEVELS = ("top", "middle", "bottom")
LEGS = ("FL", "FR", "RL", "RR")
NAMES = ("mass", "com_x", "com_y", "com_z", "Ixx", "Iyy", "Izz", "Ixy", "Ixz", "Iyz")


def frac(v) -> F:
    """Exact value of the printed decimal (repr of the float read from the YAML text; the exporter
    writes <= 9 significant digits, so repr reproduces the text)."""
    return F(Decimal(repr(float(v))))


def flat(block) -> list[F]:
    i = block["inertia_kg_m2"]
    return [
        frac(block["mass_kg"]),
        *[frac(c) for c in block["com_m"]],
        frac(i[0][0]),
        frac(i[1][1]),
        frac(i[2][2]),
        frac(i[0][1]),
        frac(i[0][2]),
        frac(i[1][2]),
    ]


def compose(xf, xm, t):
    """Two rigid parts, the second translated by t along +z; inertia about the joint CoM."""
    mf, mm = xf[0], xm[0]
    cf = list(xf[1:4])
    cm = [xm[1], xm[2], xm[3] + t]
    m = mf + mm
    c = [(mf * a + mm * b) / m for a, b in zip(cf, cm, strict=True)]

    def tens(x):
        return [[x[4], x[7], x[8]], [x[7], x[5], x[9]], [x[8], x[9], x[6]]]

    def shift(mass, r):
        rr = sum(v * v for v in r)
        return [[mass * ((rr if i == j else 0) - r[i] * r[j]) for j in range(3)] for i in range(3)]

    tf, tm = tens(xf), tens(xm)
    sf = shift(mf, [a - b for a, b in zip(cf, c, strict=True)])
    sm = shift(mm, [a - b for a, b in zip(cm, c, strict=True)])
    inertia = [[tf[i][j] + tm[i][j] + sf[i][j] + sm[i][j] for j in range(3)] for i in range(3)]
    return [
        m,
        *c,
        inertia[0][0],
        inertia[1][1],
        inertia[2][2],
        inertia[0][1],
        inertia[0][2],
        inertia[1][2],
    ]


def half_unit(v) -> F:
    if v == 0:
        return F(0)
    e = Decimal(repr(float(v))).normalize().as_tuple().exponent
    return F(1, 2) * F(10) ** e


def rounding_bound(xf, xm, t, xr, include_travel: bool) -> list[float]:
    inputs = list(xf) + list(xm) + [t]
    halves = [half_unit(v) for v in inputs]
    if not include_travel:
        halves[-1] = F(0)
    acc = [half_unit(v) for v in xr]
    for k, h in enumerate(halves):
        if h == 0:
            continue
        up, dn = list(inputs), list(inputs)
        up[k] += h
        dn[k] -= h
        o_up, o_dn = compose(up[:10], up[10:20], up[20]), compose(dn[:10], dn[10:20], dn[20])
        acc = [a + abs(u - d) / 2 for a, u, d in zip(acc, o_up, o_dn, strict=True)]
    return [float(a) for a in acc]


def part_a(params, auger) -> dict:
    s = params["superstructure"]
    xf, xm = flat(s["fixed_part"]), flat(s["auger_moving_set_at_cad_pose"])
    out = {}
    for lv in LEVELS:
        blk = s["auger_levels"][lv]
        t = frac(blk["auger_travel_m"])
        travel_json_m = F(Decimal(repr(float(auger["levels"][lv]["travel_mm"])))) / 1000
        xr = flat(blk)
        xc = compose(xf, xm, t)
        res = [float(a - b) for a, b in zip(xc, xr, strict=True)]
        imax = max(abs(float(v)) for v in xr[4:])
        b_tr = rounding_bound(xf, xm, t, xr, include_travel=True)
        b_no = rounding_bound(xf, xm, t, xr, include_travel=False)
        faults = {}
        cases = {
            "Ixx +0.44 kg m2 (audit example)": ("ref", 4, F(44, 100)),
            "Ixx +0.01 kg m2": ("ref", 4, F(1, 100)),
            "Iyz +1e-3 kg m2": ("ref", 9, F(1, 1000)),
            "com_z +1 um": ("ref", 3, F(1, 10**6)),
            "mass +0.01 kg": ("ref", 0, F(1, 100)),
            "travel +0.01 mm": ("travel", None, F(1, 10**5)),
            "fixed Ixz sign flipped": ("fixed_sign", 8, None),
        }
        for name, (kind, idx, d) in cases.items():
            xr2, xf2, t2 = list(xr), list(xf), t
            if kind == "ref":
                xr2[idx] += d
            elif kind == "travel":
                t2 = t + d
            else:
                xf2[idx] = -xf2[idx]
            r2 = [abs(float(a - b)) for a, b in zip(compose(xf2, xm, t2), xr2, strict=True)]
            faults[name] = {
                "caught_bound_with_travel": bool(any(a > b for a, b in zip(r2, b_tr, strict=True))),
                "caught_bound_no_travel": bool(any(a > b for a, b in zip(r2, b_no, strict=True))),
                "caught_1e-8_plan_metrics": bool(
                    r2[0] > 1e-8 * float(xr[0]) or max(r2[1:4]) > 1e-8 or max(r2[4:]) > 1e-8 * imax
                ),
                "max_residual_over_bound_no_travel": max(
                    a / b for a, b in zip(r2, b_no, strict=True)
                ),
            }
        out[lv] = {
            "travel_m": float(t),
            "travel_equals_auger_json_travel_mm_x_1e-3": t == travel_json_m,
            "residual": dict(zip(NAMES, res, strict=True)),
            "rel_elementwise": dict(
                zip(
                    NAMES,
                    [abs(r) / abs(float(v)) for r, v in zip(res, xr, strict=True)],
                    strict=True,
                )
            ),
            "ref_half_unit_rel": dict(
                zip(NAMES, [float(half_unit(v)) / abs(float(v)) for v in xr], strict=True)
            ),
            "bound_with_travel": dict(zip(NAMES, b_tr, strict=True)),
            "bound_no_travel": dict(zip(NAMES, b_no, strict=True)),
            "residual_over_bound_no_travel": dict(
                zip(NAMES, [abs(r) / b for r, b in zip(res, b_no, strict=True)], strict=True)
            ),
            "max_residual_over_bound_no_travel": max(
                abs(r) / b for r, b in zip(res, b_no, strict=True)
            ),
            "travel_share_of_bound_with_travel": dict(
                zip(NAMES, [1 - n / w for n, w in zip(b_no, b_tr, strict=True)], strict=True)
            ),
            "plan_metrics": {
                "mass_rel": abs(res[0]) / float(xr[0]),
                "com_max_abs_m": max(abs(v) for v in res[1:4]),
                "inertia_rel_to_max": max(abs(v) for v in res[4:]) / imax,
            },
            "plan_metric_bounds_no_travel": {
                "mass_rel": b_no[0] / float(xr[0]),
                "com_max_abs_m": max(b_no[1:4]),
                "inertia_rel_to_max": max(b_no[4:]) / imax,
            },
            "fault_injection": faults,
        }
    return out


def part_b(params) -> dict:
    s5 = json.loads(S5_JSON.read_text(encoding="utf-8"))
    pdel = json.loads(PDELTA_JSON.read_text(encoding="utf-8"))
    legs = params["legs"]
    l1 = params["contact"]["rigid_floor"]["L1"]
    eop = np.array([l1["derivation"]["operating_extension_m"][k] for k in LEGS])
    z_ball = (
        np.array([legs[k]["pad_bottom_center_retracted_m"][2] for k in LEGS])
        - eop
        + np.array([legs[k]["pad"]["swivel_center_above_pad_bottom_m"] for k in LEGS])
    )
    out = {"z_ball_mean_m": float(z_ball.mean())}
    for lv in LEVELS:
        v1 = s5["V10"][lv]["V1"]
        c = np.array(v1["contact_mean_N"])
        lin_exact = np.array(pdel[lv]["linear_contact_N"])
        nonlin = np.array(pdel[lv]["nonlinear_contact_N"])
        tol = float(v1["tol_N"])
        h = params["superstructure"]["auger_levels"][lv]["com_m"][2] - float(z_ball.mean())
        d_lin_ref = c - np.array(v1["reference_N"])
        out[lv] = {
            "h_m": h,
            "chrono_minus_linear_reference_N": d_lin_ref.tolist(),
            "chrono_minus_linear_exact_N": (c - lin_exact).tolist(),
            "chrono_minus_pdelta_N": (c - nonlin).tolist(),
            "pdelta_minus_linear_exact_N": (nonlin - lin_exact).tolist(),
            "pdelta_share_FL_per_h_N_per_m": float((nonlin - lin_exact)[0] / h),
            "usage_linear_rule": float(np.abs(d_lin_ref).max() / tol),
            "usage_pdelta_rule_0p01pct": float(np.abs(c - nonlin).max() / (0.1 * tol)),
            "weight_factor_where_linear_rule_reaches_1": float(tol / np.abs(d_lin_ref).max()),
            "twist_pattern_check": float(np.dot(c - nonlin, [0.5, -0.5, -0.5, 0.5])),
        }
    return out


def main() -> None:
    params = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    auger = json.loads(AUGER_JSON.read_text(encoding="utf-8"))
    out = {
        "meta": {
            "script": "04_scripts/01_dynamics/run_s5_v0_check.py",
            "doc": "00_docs/01_dynamics/dynamics_model.md 5.9 (rev. 22)",
            "inputs": [
                str(p.relative_to(ROOT)).replace("\\", "/")
                for p in (YAML_PATH, AUGER_JSON, S5_JSON, PDELTA_JSON)
            ],
        },
        "A_v0_auger": part_a(params, auger),
        "B_v10_loads": part_b(params),
    }
    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8", newline="\n")
    for lv, a in out["A_v0_auger"].items():
        print(
            lv,
            "travel exact",
            a["travel_equals_auger_json_travel_mm_x_1e-3"],
            "plan",
            {k: f"{v:.3g}" for k, v in a["plan_metrics"].items()},
            "bounds",
            {k: f"{v:.3g}" for k, v in a["plan_metric_bounds_no_travel"].items()},
            "res/bound max",
            f"{a['max_residual_over_bound_no_travel']:.3f}",
        )
        print(
            "   travel share Ixx",
            f"{a['travel_share_of_bound_with_travel']['Ixx']:.4f}",
            "half-unit rel Iyz",
            f"{a['ref_half_unit_rel']['Iyz']:.2g}",
        )
        print(
            "   faults",
            {
                k: (
                    f["caught_bound_with_travel"],
                    f["caught_bound_no_travel"],
                    f["caught_1e-8_plan_metrics"],
                )
                for k, f in a["fault_injection"].items()
            },
        )
    for lv in LEVELS:
        b = out["B_v10_loads"][lv]
        print(
            lv,
            f"h {b['h_m']:.4f}",
            "C-P",
            [round(x, 3) for x in b["chrono_minus_pdelta_N"]],
            "P-L",
            [round(x, 2) for x in b["pdelta_minus_linear_exact_N"]],
            f"perh {b['pdelta_share_FL_per_h_N_per_m']:.3f}",
            f"use_lin {b['usage_linear_rule']:.3f}",
            f"use_pd {b['usage_pdelta_rule_0p01pct']:.3f}",
            f"Wfac {b['weight_factor_where_linear_rule_reaches_1']:.3f}",
            f"twist {b['twist_pattern_check']:.3f}",
        )
    print("wrote", OUT)


if __name__ == "__main__":
    main()
