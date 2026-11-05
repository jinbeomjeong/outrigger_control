"""M1 start delay against m1_m2_reference.json: one leg, constant load, valve lag, friction band as in the kernel.

Usage (dynamics-dev): python -I unit_delay.py <out.json>
Retract: time the check opens. Extend: time the piston moved 0.2 mm. The leg: oil spring k_oil on a fixed load with a
Coulomb band +-F_s starting at zero friction load (fresh stick), piston = reference minus the part the band holds.
Tolerances from the reference file: retract +-5 % against Hopsan, extend +-10 % (F_s 0), +-15 % (with friction).
The extend v_max column is left out as in the report (ringing of the earlier retract).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("MKL_THREADING_LAYER", "TBB")
os.environ.setdefault("MKL_NUM_THREADS", "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REFERENCE = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "pressure_review" / "m1_m2_reference.json"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "04_scripts" / "04_hydraulic" / "coupled"))
sys.path.insert(0, str(ROOT / "03_src"))

from m1_plant import M1Config, dead_strokes_m  # noqa: E402
from params import load_params  # noqa: E402

TAU_V = 0.1
V_MAX_KEYS = ("0.05", "0.1", "0.25", "1")


def simulate(cfg, common, F_s, command, dt=2e-5, move=0.2e-3):
    """(time the check opens, time the piston moved ``move``) for a command fraction step [s]; friction at zero load."""
    values = dead_strokes_m(cfg, F_s=F_s, **common)
    k_oil = common["beta"] * common["A_h"] / (common["L0h"] + common["s"])
    is_retract = command < 0.0
    need = float(values["retract"] if is_retract else values["extend"])
    speed = abs(command)
    filled = reference = valve = t = 0.0
    t_open = None
    start = float(values["creep_start"])
    creep = float(values["creep_ref"])
    band = F_s / k_oil
    t_move = None
    while t < 30.0:
        valve += (speed - valve) * dt / TAU_V
        t += dt
        if t_open is None:
            filled += valve * dt
            if is_retract and start < 1.0:
                reference = creep * max(filled / need - start, 0.0) / (1.0 - start)
            if filled >= need:
                t_open = t
                if is_retract:
                    reference = creep + float(values["discharge"])
        else:
            reference += valve * dt
        if t_move is None and reference - band >= move:
            t_move = t
        if t_move is not None and t_open is not None:
            return t_open, t_move
    return t_open, float("nan")


def main() -> None:
    params = load_params()
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    inputs = reference["M1"]
    table = inputs["table"]
    legs = {"FL": 0, "RL": 2}
    s0 = reference["inputs"]["s0_m"]
    rows = []
    cfg = M1Config()
    for leg, index in legs.items():
        for tag, entry in table[leg].items():
            F_s = float(entry["F_s_N"])
            common = dict(p_h=entry["hand_inputs"]["p_h0_bar_g"] * 1e5, p_r=2e5, s=s0[leg],
                          A_h=float(params.A_h[index]), A_ann=float(params.A_r[index]), s_max=params.stroke,
                          L0r=params.L0r, L0h=params.L0h, beta=params.beta, p_T=params.p_T)
            values = dead_strokes_m(cfg, F_s=F_s, **common)
            for key in V_MAX_KEYS:
                data = entry["by_command"][key]
                v = float(key) * params.v_max
                open_s, _ = simulate(cfg, common, F_s, -v)
                _, ext_s = simulate(cfg, common, F_s, v)
                hop_open = data["retract_check_open_s"]["hopsan"]
                hop_ext = data["extend_piston_0p2mm_s"]["hopsan"]
                rows.append({"leg": leg, "F_s_kN": F_s / 1e3, "command": float(key), "m1_retract_open_s": round(open_s, 4),
                             "hopsan_retract_open_s": round(hop_open, 4), "retract_rel": round(open_s / hop_open - 1.0, 4),
                             "m1_extend_0p2_s": round(ext_s, 4), "hopsan_extend_0p2_s": round(hop_ext, 4),
                             "extend_rel": round(ext_s / hop_ext - 1.0, 4), "extend_in_table": key != "1",
                             "dead_retract_mm": round(float(values["retract"]) * 1e3, 4),
                             "ref_retract_mm": round(entry["hand_inputs"]["retract_open_stroke_mm"], 4),
                             "dead_extend_mm": round(float(values["extend"]) * 1e3, 4),
                             "ref_extend_mm": round(entry["hand_inputs"]["extend_dead_stroke_mm"], 4),
                             "discharge_mm": round(float(values["discharge"]) * 1e3, 4),
                             "ref_discharge_mm": round(entry["hand_inputs"]["head_dump_stroke_mm"], 4)})
    retract_worst = max(abs(r["retract_rel"]) for r in rows)
    ext_f0 = max(abs(r["extend_rel"]) for r in rows if r["extend_in_table"] and r["F_s_kN"] == 0.0)
    ext_fs = max(abs(r["extend_rel"]) for r in rows if r["extend_in_table"] and r["F_s_kN"] > 0.0)
    out = {"tolerance": {"retract_open": 0.05, "extend_Fs0": 0.10, "extend_with_friction": 0.15},
           "worst": {"retract_open": retract_worst, "extend_Fs0": ext_f0, "extend_with_friction": ext_fs},
           "pass": bool(retract_worst <= 0.05 and ext_f0 <= 0.10 and ext_fs <= 0.15), "rows": rows}
    Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("worst", "pass")}, indent=1))
    for r in rows:
        if r["leg"] == "FL":
            print(r["F_s_kN"], r["command"], "ret", r["m1_retract_open_s"], r["hopsan_retract_open_s"], r["retract_rel"],
                  "ext", r["m1_extend_0p2_s"], r["hopsan_extend_0p2_s"], r["extend_rel"], "dead", r["dead_retract_mm"],
                  r["ref_retract_mm"], r["dead_extend_mm"], r["ref_extend_mm"], r["discharge_mm"], r["ref_discharge_mm"])


if __name__ == "__main__":
    main()
