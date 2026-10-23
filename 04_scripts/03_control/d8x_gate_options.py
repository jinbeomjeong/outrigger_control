"""S6 spec revision 2: A1 / A4 gate options against the Chrono stage-2 crawler snapshots (Q12 bushing).

Inputs: 07_results/S6/snapshots_20261021_195044/*/result.json (chrono_end body attitude = (phi_c, theta_c)),
        d8x_boundary_sim.json (reduced-model strokes, for the accepted-floor -> stroke estimate).
Options:
  cur   : verification diamond (5.5, 3.5) on the measured attitude (R3 as implemented),
  sym   : constants only, (5.6, 3.85) on the measured attitude (user's example values),
  map   : floor estimate g_hat = settle-map^-1(phi_c, theta_c) per auger level, diamond (5.5, 3.5) x (1 + eps_u).
Settle map (per level, from the snapshots): theta_c = theta0 + (1 + k_dn) theta_g (theta_g >= 0),
  theta0 + (1 + k_up) theta_g (theta_g < 0); phi_c = (1 + k_phi) phi_g.
Run: conda run -n dynamics-dev python -I d8x_gate_options.py <project_root> <boundary_json> <out_json>
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
SNAP = ROOT / "07_results" / "S6" / "snapshots_20261021_195044"
EPS_U = 0.01   # ASSUMPTION: usage tolerance (CHECK 1 s mean vs 65.5 s snapshot end, Chrono 5 s span 0.017 deg)


def load():
    snaps = {}
    for f in sorted(glob.glob(str(SNAP / "*" / "result.json"))):
        d = json.loads(Path(f).read_text())
        snaps[(d["level"], d["floor"])] = (d["floor_slope_deg"], d["chrono_end"]["body_roll_pitch_deg"])
    return snaps


def fit(snaps):
    maps = {}
    for lvl in ("top", "middle", "bottom"):
        th0 = snaps[(lvl, "flat")][1][1]
        dn = snaps[(lvl, "fdown3.5")][1][1]
        up = snaps[(lvl, "fup3.5")][1][1]
        ph = snaps[(lvl, "roll5.5")][1][0]
        maps[lvl] = dict(theta0_deg=th0, k_dn=(dn - th0) / 3.5 - 1.0, k_up=(th0 - up) / 3.5 - 1.0,
                         k_phi=ph / 5.5 - 1.0)
    return maps


def floor_est(att, m):
    ph, th = att
    d = th - m["theta0_deg"]
    th_g = d / (1.0 + (m["k_dn"] if d >= 0 else m["k_up"]))
    return ph / (1.0 + m["k_phi"]), th_g


def usage(ph, th, a, b):
    return abs(ph) / a + abs(th) / b


def main():
    snaps = load()
    maps = fit(snaps)
    rows = []
    for (lvl, fl), (g, c) in snaps.items():
        m = maps["top" if lvl not in maps else lvl]
        gh = floor_est(c, m)
        gt = floor_est(c, maps["top"])
        rows.append(dict(level=lvl, floor=fl, floor_deg=g, meas_deg=c,
                         u_oper=usage(*c, 4.4, 3.2), u_cur=usage(*c, 5.5, 3.5), u_sym=usage(*c, 5.6, 3.85),
                         g_hat_deg=gh, u_map=usage(*gh, 5.5 * (1 + EPS_U), 3.5 * (1 + EPS_U)),
                         g_hat_topmap_deg=gt, u_topmap=usage(*gt, 5.5 * (1 + EPS_U), 3.5 * (1 + EPS_U))))
    # accepted floor extremes on the pitch / roll axes (top level), measured -> floor through the map
    m = maps["top"]

    def floor_from_meas_pitch(thc):
        return floor_est((0.0, thc), m)[1]

    ext = {
        "sym": {"fdown_floor_deg": floor_from_meas_pitch(3.85), "fup_floor_deg": floor_from_meas_pitch(-3.85),
                "roll_meas_needed_for_roll5.5_deg": snaps[("top", "roll5.5")][1][0]
                / (1 - snaps[("top", "roll5.5")][1][1] / 3.85)},
        "map": {"fdown_floor_deg": 3.5 * (1 + EPS_U), "fup_floor_deg": -3.5 * (1 + EPS_U),
                "roll_floor_deg": 5.5 * (1 + EPS_U)},
    }
    # stroke vs floor from the reduced model (top, H4 rel)
    b = json.loads(Path(sys.argv[2]).read_text())
    smax = {r["id"]: max(r["s_max_seen_mm"]) for r in b["runs"] if "s_max_seen_mm" in r}
    slope_dn = (smax["top|fdown3.6"] - smax["top|fdown3.5"]) / 0.1
    slope_up = (smax["top|fup3.6"] - smax["top|fup3.5"]) / 0.1
    slope_r = (smax["top|roll5.6"] - smax["top|roll5.5"]) / 0.1

    def s_at(axis, x):
        if axis == "dn":
            return smax["top|fdown3.5"] + slope_dn * (x - 3.5)
        if axis == "up":
            return smax["top|fup3.5"] + slope_up * (abs(x) - 3.5)
        return smax["top|roll5.5"] + slope_r * (x - 5.5)

    strokes = {"slopes_mm_per_deg": {"fdown": slope_dn, "fup": slope_up, "roll": slope_r},
               "sym": {"fdown": s_at("dn", ext["sym"]["fdown_floor_deg"]), "fup": s_at("up", ext["sym"]["fup_floor_deg"])},
               "map": {"fdown": s_at("dn", ext["map"]["fdown_floor_deg"]), "fup": s_at("up", ext["map"]["fup_floor_deg"]),
                       "roll": s_at("r", ext["map"]["roll_floor_deg"])},
               "floor_at_670mm": {"fdown": 3.5 + (670 - smax["top|fdown3.5"]) / slope_dn,
                                  "fup": -(3.5 + (670 - smax["top|fup3.5"]) / slope_up),
                                  "roll": 5.5 + (670 - smax["top|roll5.5"]) / slope_r},
               "floor_at_679mm": {"fdown": 3.5 + (679 - smax["top|fdown3.5"]) / slope_dn,
                                  "fup": -(3.5 + (679 - smax["top|fup3.5"]) / slope_up),
                                  "roll": 5.5 + (679 - smax["top|roll5.5"]) / slope_r}}
    out = dict(eps_u=EPS_U, maps=maps, rows=rows, extremes=ext, strokes=strokes)
    Path(sys.argv[3]).write_text(json.dumps(out, indent=1))
    for k, v in maps.items():
        print(k, {a: round(x, 5) for a, x in v.items()})
    for r in rows:
        print(f"{r['level']:6s} {r['floor']:9s} meas=({r['meas_deg'][0]:.4f},{r['meas_deg'][1]:.4f}) "
              f"oper={r['u_oper']:.4f} cur={r['u_cur']:.4f} sym={r['u_sym']:.4f} "
              f"g_hat=({r['g_hat_deg'][0]:.4f},{r['g_hat_deg'][1]:.4f}) map={r['u_map']:.4f} topmap={r['u_topmap']:.4f}")
    print(json.dumps(ext, indent=1))
    print(json.dumps(strokes, indent=1))


if __name__ == "__main__":
    main()
