"""D2 (Q9) inverse problem, static part: limit downward mast-axis force per event (dynamics_model.md rev. 33, 5.21).

Run (dynamics-dev, activated):
    conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_d2_static_limits.py

Writes 06_analysis/00_dynamics/d2_static_limits.json. Deterministic.

For every auger level x floor (level, operating limits pitch +-3.2 deg, roll +-4.4 deg) x model x lock state the
machine is levelled on the floor (V12 rule: place and settle with the head-only k2, lock with dc = 0), then a
vertical downward force P grows at the D2 point (mast / auger axis). Piecewise-linear statics (rod-side knee) give the
first P at which: head pressure 345 bar (warning, U72), head pressure 350 bar (locked limit), rod-side pressure
350 bar (H-2), cylinder force F_min (control.F_min_cylinder_N), pad lift-off (contact normal 0). Exact for the
model up to the first lift-off (then the topology changes; tip-over is not followed).

Models: "L1-R" = k_h, k_r at e_op for every leg (the Chrono L1-R plant, Q-D7); "L2b" = k_h(e_i), k_r(e_i) at the
levelled extension of each leg. Lock states: after_extend (p_r0 2 bar g, RULE), after_retract (YAML per leg),
head_only (rod side off, = pre-L1-R L1). Seal friction (S8), mast flexibility and dynamics are not in this file.
Frame: body x forward, y left, z up, level body = world axes, gravity -z; pitch + = nose down, roll + = left down
(run_reference.levelled_extension sign); forces N, compression +.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dyn_model as dm  # noqa: E402
import l2b_reference as l2  # noqa: E402

OUT = dm.PROJECT_ROOT / "06_analysis" / "00_dynamics" / "d2_static_limits.json"
FLOORS = {"level": (0.0, 0.0), "pitch +3.2 (nose down)": (0.0, 3.2), "pitch -3.2 (nose up)": (0.0, -3.2),
          "roll +4.4": (4.4, 0.0), "roll -4.4": (-4.4, 0.0)}
# D2 point: auger axis. ASSUMPTION: x, y of the moving set (drive + tool) CoG, 01_cad/03_auger/auger_levels.json
# levels.top.mass.tool_steel.moving_set_cog_body_m [3.2027, 0.0028]; sensitivity = mast section centroid
# (01_cad/04_mast/mast_beam_properties.json mast_axis_reference x 2.51408, y 0)
D2_POINTS = {"auger_axis_x3.203 (base)": (3.2027, 0.0028), "mast_centroid_x2.514 (sensitivity)": (2.51408, 0.0)}
EVENTS = ("p_h_345bar", "p_h_350bar", "p_r_350bar", "F_min", "liftoff")
P_MAX_N = 5.0e6


def main():
    t0 = time.perf_counter()
    p = dm.load_params()
    geo = dm.geometry_from_params(p)
    lp = l2.leg_parameters(p, geo)
    A_ = dm.ASSUMPTIONS
    F_min = float(p["control"]["F_min_cylinder_N"])
    e_op = np.full(4, 0.0) + lp["e_op"]
    res = {"meta": {"script": "04_scripts/01_dynamics/run_d2_static_limits.py",
                    "document": "00_docs/01_dynamics/dynamics_model.md rev. 33, 5.21",
                    "params": "02_params/rexome33.yaml", "frame": "body x fwd, y left, z up; g = -9.80665 z",
                    "pitch_sign": "+ = nose down (floor), roll + = left down", "leg_order": list(dm.LEG_NAMES),
                    "force": "vertical downward P at the D2 point, static, after levelling and locking",
                    "F_min_cylinder_N": F_min, "P_max_searched_N": P_MAX_N,
                    "D2_points_xy_m": D2_POINTS,
                    "limits": {"p_h_345bar": "head pressure p_h = (F + p_r A_ann) / A_p >= 345 bar (warning, U72)",
                               "p_h_350bar": "p_h >= 350 bar (YAML actuator.locked_pressure_limit_Pa)",
                               "p_r_350bar": "rod-side p_r >= 350 bar (H-2, ASSUMPTION manufacturer limit)",
                               "F_min": "cylinder force <= control.F_min_cylinder_N",
                               "liftoff": "pad contact normal = 0 (search stops)"}},
           "cases": {}}
    for lvl in dm.LEVELS:
        b = dm.body_from_params(p, lvl)
        for fname, (ro, pi) in FLOORS.items():
            ext = l2.levelled_extension(geo, ro, pi, A_["crawler_clearance_m"])
            if ext.min() < 0 or ext.max() > geo.stroke:
                raise RuntimeError(f"{fname}: levelled extension outside the stroke {ext}")
            sysm = l2.SlopeSystem(b, geo, ext, lp["kt"], pi, ro)
            for model, s_k in (("L1-R", e_op), ("L2b", ext)):
                k_h, k_r = lp["k_h_f"](s_k), lp["k_r_f"](s_k)
                k2 = dm.series(k_h, lp["k_out"])
                _, F0, N0 = sysm.place_and_settle(k2)
                for lock, (state, p_r0) in {"after_extend": ("LOCK", lp["p_r0_ext"]),
                                            "after_retract": ("LOCK", lp["p_r0_ret"]),
                                            "head_only": ("HEAD", lp["p_r0_ext"])}.items():
                    for pt_name, xy in D2_POINTS.items():
                        if pt_name != next(iter(D2_POINTS)) and not (lock == "after_extend"):
                            continue
                        pw = l2.piecewise_path(sysm, lp, k_h, k_r, [state] * 4, F0, N0,
                                               f_unit=sysm.vertical_force(xy), F_min=F_min, lam_max=P_MAX_N,
                                               p_r0=p_r0)
                        ev = pw["events"]
                        key = f"{lvl} | {fname} | {model} | {lock} | {pt_name}"
                        ent = {"extension_m": l2.r(ext, 5), "F_cyl_start_N": l2.r(F0), "N_start_N": l2.r(N0),
                               "first_event": None, "events_kN": {}}
                        firsts = []
                        for e_name in EVENTS:
                            if e_name in ev:
                                ent["events_kN"][e_name] = {"P_kN": l2.r(ev[e_name]["lam"] * 1e-3, 5),
                                                            "leg": ev[e_name]["leg"],
                                                            "F_cyl_at_event_N": l2.r(ev[e_name]["F_cyl_N"])}
                                firsts.append((ev[e_name]["lam"], e_name))
                            else:
                                ent["events_kN"][e_name] = None
                        if firsts:
                            lam, nm = min(firsts)
                            ent["first_event"] = {"event": nm, "P_kN": l2.r(lam * 1e-3, 5)}
                        ent["knees (leg, P kN)"] = [[k["leg"], l2.r(k["lam"] * 1e-3, 4)] for k in pw["knees"]]
                        ent["p_r_max_before_end_bar"] = l2.r(pw["p_r_max_Pa"] * 1e-5, 4)
                        res["cases"][key] = ent
    # compact table for the document (base point, after_extend)
    tab = {}
    for key, ent in res["cases"].items():
        lvl, fname, model, lock, pt = key.split(" | ")
        if pt != next(iter(D2_POINTS)):
            continue
        tab.setdefault(f"{lvl} | {fname}", {})[f"{model} | {lock}"] = {
            k: (None if v is None else [v["P_kN"], v["leg"]]) for k, v in ent["events_kN"].items()}
    res["table_base_point_kN"] = tab
    res["meta"]["runtime_s"] = round(time.perf_counter() - t0, 2)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    print("written", OUT, "runtime", res["meta"]["runtime_s"], "s")


if __name__ == "__main__":
    main()
