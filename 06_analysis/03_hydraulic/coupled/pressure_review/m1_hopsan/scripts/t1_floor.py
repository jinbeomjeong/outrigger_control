"""Task 1 and 3: retract opening from high head pressure, rod at the floor or refilled, both neutral forms; M1 formula."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from bench import REAR_FS_SCALE, Bench, formula, geometry, load_params, open_metrics, pin, run_many

OUT = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\pressure_review\m1_hopsan")
HERE = Path(__file__).resolve().parent

MODES = {
    "IC_floor": dict(start="ic_floor", pilot_ref_b=True),  # no void: exactly the formula's assumption
    "ramp_floor_ref": dict(start="ramp", pilot_ref_b=True),  # back pressure does not pilot the rod check: floor + void
    "ramp_vent": dict(start="ramp"),  # as the reference table: the rod check is piloted open by the back pressure
    "ramp_vent_stock": dict(start="ramp", stock_check=True),
    "ramp_vent_pT0": dict(start="ramp", p_T=0.0, p_r0=0.0),  # no back pressure: floor + void
    "ramp_lowcrack": dict(start="ramp", pilot_ref_b=True, crack_b=0.5e5),  # referenced pilot, small crack: refill only
    "ramp_block": dict(start="ramp", neutral="block"),
    "ramp_block_db": dict(start="ramp", neutral="block", deadband=True),
}
SPEEDS = {"0.84mm/s": 0.84e-3, "0.05vmax": None, "0.25vmax": None}


def main() -> None:
    pin()
    p = load_params()
    work = HERE / "t1"
    benches = []
    for leg in (1, 2):
        for ph in (115e5, 125e5):
            for fs0 in (0.0, 4e3):
                fs = fs0 * (1.0 if leg < 2 else REAR_FS_SCALE)
                for mode, kw in MODES.items():
                    for tag, sp in SPEEDS.items():
                        v = sp if sp else float(tag.split("v")[0]) * p.v_max
                        dur = min(0.006 / v, 8.0)
                        name = f"{'FLRR'[0:0]}{['FL','FR','RL','RR'][leg]}_{ph / 1e5:g}_{fs0 / 1e3:g}_{mode}_{tag.replace('/', '')}"
                        benches.append((Bench(name, leg, ph, F_s=fs, cmd_t=np.array([0.0, dur]), cmd_u=np.array([-v, 0.0]), **kw), mode, tag, fs0))
    print("runs", len(benches), flush=True)
    results = run_many([b for b, *_ in benches], p, work)
    rows = []
    for (b, mode, tag, fs0), (_, res) in zip(benches, results):
        m = open_metrics(b, res)
        A_h, A_r, s0, _F = geometry(p, b.leg)
        t = res["t"]
        pre_ramp = (t >= b.t_settle - 0.05) & (t < b.t_settle)
        pre_cmd = (t >= res["t_cmd"] - 0.05) & (t < res["t_cmd"])
        creep_ramp = float((res["x"][pre_ramp].mean() - res["x"][pre_cmd].mean()) * 1e3) if b.start == "ramp" else 0.0
        L_r = p.L0r + p.stroke - s0
        if b.neutral == "block":
            soft = L_r / p.beta + 2.85e-4 / 0.5e9 / A_r
        else:
            soft = L_r / p.beta
        void = max(creep_ramp - (b.p_r0 / 1e5 - m["p_r_pre"]) * 1e5 * soft * 1e3, 0.0) if m["p_r_pre"] < -0.5 else 0.0
        f = formula(b, p, m["p_h_pre"], m["p_r_pre"])
        f_harness_floor = formula(b, p, m["p_h_pre"], -0.91)
        row = {"name": b.name, "leg": b.leg, "p_h_target": b.p_h_target / 1e5, "fs0_kN": fs0 / 1e3, "F_s_N": b.F_s, "mode": mode, "cmd": tag,
               "creep_ramp_mm": creep_ramp, "void_mm": void, "formula_mm": f["retract"], "formula_p_open": f["p_open"], "formula_dp_h": f["dp_h"],
               "formula_floor_mm": f_harness_floor["retract"], "formula_plus_void_mm": f["retract"] + void, "wall_s": res["wall_s"], **m}
        row["rel_formula"] = row["stroke_open_mm"] / row["formula_mm"] - 1.0 if row["stroke_open_mm"] == row["stroke_open_mm"] else None
        row["rel_formula_void"] = row["stroke_open_mm"] / row["formula_plus_void_mm"] - 1.0 if row["stroke_open_mm"] == row["stroke_open_mm"] else None
        rows.append(row)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t1_floor.json").write_text(json.dumps(rows, indent=0), encoding="utf-8")
    keys = ("p_h_pre", "p_r_pre", "line_b_pre", "open_b_pre", "void_mm", "t_open_s", "stroke_open_mm", "formula_mm", "formula_plus_void_mm", "p_b_open", "formula_p_open", "p_h_open", "creep_at_open_mm")
    for r in rows:
        if r["cmd"] == "0.05vmax" or r["leg"] == 2 and r["p_h_target"] == 115:
            print(r["name"], {k: (round(r[k], 2) if r.get(k) is not None else None) for k in keys}, flush=True)


if __name__ == "__main__":
    main()
