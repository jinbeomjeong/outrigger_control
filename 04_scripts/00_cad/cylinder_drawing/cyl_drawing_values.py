"""Drawing-based cylinder values (REXOME35-9206) vs current YAML (CAD REXOME33). SI units."""
import json
import math
import os

RHO = 7850.0  # kg/m^3 ASSUMPTION steel (CAD solids are SS400 7.85)
P_RELIEF = 210e5
P_LOCK = 350e5
BETA = 1.0e9
L_DEAD = 0.05
G = 9.80665
PUMP = 60.2 / 60000.0  # m^3/s

def disc(d):
    return math.pi / 4 * d * d

cases = {
    "yaml_cad": {"D": 0.115, "d": 0.110, "stroke": 0.68},
    "front_dwg": {"D": 0.130, "d": 0.110, "stroke": 0.70},
    "rear_dwg": {"D": 0.110, "d": 0.090, "stroke": 0.70},
}
out = {}
for k, c in cases.items():
    Ap, Ar = disc(c["D"]), disc(c["d"])
    Aa = Ap - Ar
    out[k] = {
        "A_p_m2": Ap, "A_rod_m2": Ar, "A_ann_m2": Aa, "area_ratio_Ap_over_Aann": Ap / Aa,
        "F_ext_210bar_N": P_RELIEF * Ap, "F_ret_210bar_N": P_RELIEF * Aa,
        "F_lock_350bar_N": P_LOCK * Ap,
        "k_oil_s0_N_m": BETA * Ap / L_DEAD, "k_oil_full_N_m": BETA * Ap / (L_DEAD + c["stroke"]),
        "k_rod_ratio_vs_cad": Ar / disc(0.110), "I_rod_ratio_vs_cad": (c["d"] / 0.110) ** 4,
        "Z_rod_ratio_vs_cad": (c["d"] / 0.110) ** 3,
    }
# static loads (top level, YAML superstructure.auger_levels.top.static_leg_loads_N)
loads = {"FL": 118254.6, "FR": 116261.5, "RL": 72700.31, "RR": 70885.44}
press = {}
for leg, F in loads.items():
    Ap_new = out["front_dwg" if leg[0] == "F" else "rear_dwg"]["A_p_m2"]
    press[leg] = {"p_cad_bar": F / out["yaml_cad"]["A_p_m2"] / 1e5, "p_dwg_bar": F / Ap_new / 1e5}
out["static_head_pressure_top"] = press
# pump check: 2 front + 2 rear at v
v_cad = 0.68 / 30.0
v_700 = 0.70 / 30.0
A_sum_new = 2 * out["front_dwg"]["A_p_m2"] + 2 * out["rear_dwg"]["A_p_m2"]
out["pump"] = {
    "flow_4legs_cad_at_v22.67_Lmin": 4 * out["yaml_cad"]["A_p_m2"] * v_cad * 60000,
    "flow_4legs_dwg_at_v22.67_Lmin": A_sum_new * v_cad * 60000,
    "flow_4legs_dwg_at_v23.33_Lmin": A_sum_new * v_700 * 60000,
    "v_max_4legs_at_pump_mm_s": PUMP / A_sum_new * 1000,
    "full_stroke_time_700_at_v_pump_s": 0.70 / (PUMP / A_sum_new),
}
# moving-part mass estimate by substitution on the CAD solid 10 (CAD: 106.784 kg)
cad_total = 106.783666
cad_pad_body = 22.4040315
cad_rod_body = 84.379635
rod_cad = RHO * disc(0.110) * 0.870        # R55 face Y -540.5 ... 329.5 (870 mm)
pist_cad = RHO * disc(0.115) * 0.020
rest_cad = cad_rod_body - rod_cad - pist_cad  # bosses R85 / R40 etc. above the split plane
pad_area_cad = 0.1071
c_rear = 0.030  # ASSUMPTION chamfer leg of the rear pad (front CAD chamfer 30 mm, drawing not dimensioned)
pad_area_rear = 0.250 ** 2 - 2 * c_rear ** 2
est = {}
# front: same rod, piston D130, same pad
f_rod = rod_cad
f_pist = RHO * disc(0.130) * 0.020
est["front"] = {"rod": f_rod, "piston": f_pist, "pad_body": cad_pad_body, "rest": rest_cad}
# rear: rod D90, 20 mm shorter (gland 105 vs 125), piston D110, pad area-scaled, rest scaled by rod area (low) or kept (high)
r_rod = RHO * disc(0.090) * (0.870 - 0.020)
r_pist = RHO * disc(0.110) * 0.020
r_pad = cad_pad_body * pad_area_rear / pad_area_cad
est["rear"] = {"rod": r_rod, "piston": r_pist, "pad_body": r_pad,
               "rest_low": rest_cad * disc(0.090) / disc(0.110), "rest_high": rest_cad}
shorten = {"front": RHO * disc(0.110) * 0.0543, "rear": RHO * disc(0.090) * 0.0543}
for k in est:
    e = est[k]
    base = e["rod"] + e["piston"] + e["pad_body"]
    if k == "front":
        e["total_nominal"] = base + e["rest"]
        e["total_low"] = e["total_nominal"] - shorten[k]
        e["total_high"] = e["total_nominal"]
    else:
        e["total_low"] = base + e["rest_low"] - shorten[k]
        e["total_high"] = base + e["rest_high"]
        e["total_nominal"] = 0.5 * (base + e["rest_low"] + base + e["rest_high"])
    e["shorten_54.3mm_rod_kg"] = shorten[k]
out["moving_mass_estimate_kg"] = est
out["moving_mass_cad_kg"] = {"total": cad_total, "rod_R55_870": rod_cad, "piston": pist_cad,
                            "rest_rod_body": rest_cad, "pad_body": cad_pad_body}
out["pad"] = {"rear_area_m2_c30": pad_area_rear, "rear_area_m2_c25": 0.25 ** 2 - 2 * 0.025 ** 2,
              "front_area_m2_cad": pad_area_cad,
              "rear_bearing_MPa_cad": loads["RL"] / pad_area_cad / 1e6,
              "rear_bearing_MPa_dwg": loads["RL"] / pad_area_rear / 1e6,
              "front_bearing_MPa": loads["FL"] / pad_area_cad / 1e6}
# Moved from the cad scratchpad 2026-10-25: output in the project folder 01_cad/02_legs/drawing_check/.
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "01_cad", "02_legs",
                 "drawing_check", "cyl_drawing_values.json")
json.dump(out, open(p, "w", encoding="utf-8"), indent=1)
print(json.dumps(out, indent=1))
