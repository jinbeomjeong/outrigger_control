"""Export the shared simulation parameters (reference mass case C) to params/rexome33.yaml.

The YAML file is the single source of the vehicle data for the Chrono and the
MuJoCo models: superstructure mass properties for the three auger levels, the
four outrigger legs (attachment, pad, moving part, stroke, speed) and the
ground reference.

Reads only cached data (no STEP parsing):
    cad/parts_classified.csv   part volumes, centroids, unit-density inertia (analyze_parts.py)
    cad/cad_summary.json       leg geometry (analyze_parts.py)
    cad/auger_levels.json      auger travel per level, case C results (analyze_auger_levels.py)
    cad/legs/*_10_1.brep       rod + piston + pad solids in world (CAD) coordinates (inspect_legs.py);
                               also split into pad plate / rod+piston bodies for the SCM model
    analysis/dynamics/reference.json  1st L1 rocking mode (time-step rule) and check values (run_reference.py)

Dynamics keys (docs/dynamics_model.md section 10, rev. 4 incl. the table "개정 4에서 더할 키"): the L1 / L2b-NSC /
L2 stiffness, damping, Chrono input conventions (SMC gn per mass, bushing damping input c/2), hydraulic limits and
time steps are recomputed with the formulas of scripts/dynamics/dyn_model.py and run_reference.py (transcribed,
with line references written as "<file>.py:<first>-<last>"; every such reference is checked against the
current source by check_line_references()), then checked against dyn_model.py itself (full precision),
reference.json and the document.

Writes:
    params/rexome33.yaml       commented YAML, SI units, body frame
    params/rexome33_checks.json  verification results of this export

Mass case C (CLAUDE.md, 2026-10-19, provisional): STEP densities, but the five
AUGER TOOL rows as steel 7.85 g/cm^3.

Frames. CAD root frame: mm, Y up. Body frame (CLAUDE.md): x forward = +Z_cad,
y left = +X_cad, z up = +Y_cad, origin = CAD origin, SI units. Inertia tensors
are about the centre of mass, in body axes, tensor notation (off-diagonal =
-integral(x y dm)).

Every value is recomputed at full precision with the functions of
analyze_auger_levels.py / analyze_parts.py, then checked against an
independent re-implementation and against cad/auger_levels.json. Each check
has a threshold (REL_TOL etc.); if any check fails, the checks JSON is written
with the failures and the YAML is NOT written (exit code 1).

Leg geometry (CLAUDE.md "다리 기하", 2026-10-19): all four legs use the same
extension range 0 ... 0.680 m. In the CAD pose the rear pistons (RL, RR) sit
2 mm below the bore top, so the fully retracted state (extension 0) of a rear
leg is its moving part (rod + piston + pad) raised by +0.002 m (body +z) from
the CAD pose. The front legs are retracted in the CAD pose. All "_retracted"
values in the YAML refer to this retracted state, not to the CAD pose.

Usage:
    python -I scripts/cad/export_params.py
"""

import datetime
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import yaml
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRep import BRep_Builder, BRep_Tool
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Core.BRepTools import BRepTools_WireExplorer, breptools
from OCC.Core.GeomAbs import GeomAbs_Plane
from OCC.Core.gp import gp_Pnt
from OCC.Core.GProp import GProp_GProps
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_REVERSED, TopAbs_SOLID
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import TopoDS_Shape, topods

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_auger_levels import (
    AUGER_JSON,
    DRIVE_TOP,
    LEVEL_NAMES,
    MOVING,
    TOOL_STEEL,
    TOOL_TOP,
    add_tool_steel_case,
    classify,
    shifted,
)
from analyze_mast import GRAVITY_M_S2, leg_loads, tensor_checks
from analyze_parts import (
    CAD_TO_BODY,
    CENTROID_COLUMNS,
    CLASSIFIED_CSV,
    INERTIA_COLUMNS,
    LEG_ORDER,
    STEEL_DENSITY_G_CM3,
    combine_mass_properties,
)
from cad_common import CAD_DIR, PROJECT_ROOT, STEP_PATH, SUMMARY_JSON

PARAMS_DIR = PROJECT_ROOT / "params"
PARAMS_YAML = PARAMS_DIR / "rexome33.yaml"
CHECKS_JSON = PARAMS_DIR / "rexome33_checks.json"
LEG_BREP_DIR = CAD_DIR / "legs"
ROD_PAD_BREP = {  # solid 10 = rod + piston + pad (cad/legs file names from inspect_legs.py)
    "FL": "FRONT_JACK_CYL_1___10_1.brep",
    "FR": "FRONT_JACK_CYL_2___10_1.brep",
    "RL": "REAR_JACK_CYL_1___10_1.brep",
    "RR": "REAR_JACK_CYL_2___10_1.brep",
}

# CLAUDE.md "구동기" (2026-10-19): actuator stroke and speed.
STROKE_M = 0.680
FULL_STROKE_TIME_S = 30.0
MAX_SPEED_M_S = STROKE_M / FULL_STROKE_TIME_S
# CLAUDE.md "오거 위치" (2026-10-19): "기본 실행 단계는 상단이다(무게중심이 가장 높아 제어가 가장 어려운 경우)."
DEFAULT_AUGER_LEVEL = "top"
# Pad plate "두께 20 mm" in docs/cad_review.md 3.1. The BREP shows 20 mm vertical sides plus a 5 mm x 45 deg
# top-edge chamfer (top face 25 mm above the bottom). The exported thickness and side height are measured from
# the leg BREP (pad_bottom_face); the side height must agree with the document within PAD_THICKNESS_TOL_MM.
DOC_PAD_THICKNESS_MM = 20.0
PAD_THICKNESS_TOL_MM = 0.01
SIGNIFICANT_DIGITS = 9
MM = 1e-3

# Acceptance thresholds. A failing check stops the export before params/rexome33.yaml is written.
REL_TOL = 1e-6        # exact recomputations (relative difference)
ABS_COM_TOL_M = 1e-6  # exact recomputations of a position [m]
# cad/auger_levels.json is rounded (mass 0.1 kg, CoM 1e-4 m, leg loads 0.01 kN): allow half a rounding unit.
JSON_MASS_TOL_KG = 0.05
JSON_COM_TOL_M = 5e-5
JSON_INERTIA_REL_TOL = 1e-6  # relative to the largest tensor entry (JSON keeps 7 significant digits)
JSON_LOAD_TOL_KN = 0.005
CAD_SUMMARY_TOL_MM = 0.05    # cad_summary.json lengths are rounded to 0.1 mm

# --------------------------------------------------------------------------
# Dynamics keys (docs/dynamics_model.md section 10, dynamics-expert, 2026-10-19 rev. 4)
# Stages: common = needed from L1 on, L1 = L1 default only, L2b = L2b-NSC (operating plan B re-assessment model:
# large slope, seal friction, SCM), L2 = rigid-guide L2 / SMC L2b (reference only, kept per section 10),
# SCM = soft soil.
# Inputs below are copied from docs/dynamics_model.md / scripts/dynamics/dyn_model.py:43-68 (ASSUMPTIONS);
# every derived value (L1 kn, kt, cn, ct, gn, bushing input, dt, L2b-NSC axial / bushing / dt, L2 damping,
# hydraulic areas and force limits, F_min) is RECOMPUTED here with the same formulas.
# --------------------------------------------------------------------------
DYNAMICS_DOC = "docs/dynamics_model.md"
DYN_MODEL_PY = "scripts/dynamics/dyn_model.py"
RUN_REFERENCE_PY = "scripts/dynamics/run_reference.py"
REFERENCE_JSON = PROJECT_ROOT / "analysis" / "dynamics" / "reference.json"
DYN_MODEL_DIR = PROJECT_ROOT / "scripts" / "dynamics"
ACTUATOR_MODEL_DEFAULT = "L1"               # CLAUDE.md '구동기 모델' (2026-10-19): L1 temporary default
BORE_DIAMETER_M = 0.115                     # CAD, docs/cad_review.md 3.1
ROD_DIAMETER_M = 0.110                      # CAD, docs/cad_review.md 3.1
BARREL_OUTER_DIAMETER_M = 0.160             # CAD, docs/cad_review.md 3.1
OIL_BULK_MODULUS_EFF_PA = 1.0e9             # ASSUMPTION, 사용자 결정 (CLAUDE.md, 2026-10-19)
OIL_BULK_MODULUS_SENSITIVITY_PA = [0.69e9, 1.6e9]  # 사용자 결정 (CLAUDE.md); = dyn_model ASSUMPTIONS oil_bulk_modulus_range_Pa
OIL_DEAD_LENGTH_M = 0.05                    # ASSUMPTION, docs/dynamics_model.md 2.3
FRAME_STIFFNESS_N_M = 1.0e9                 # ASSUMPTION, docs/dynamics_model.md 2.3
STEEL_E_PA = 2.1e11                         # dyn_model.py ASSUMPTIONS steel_E_Pa
ROD_LENGTH_FOR_K_ROD_M = 1.05               # dyn_model.py k_rod() default (piston top z 0.35 to pad bottom z -0.70)
CONCRETE_E_PA = 30e9                        # ASSUMPTION, docs/dynamics_model.md 2.3 / 9
CONCRETE_NU = 0.15                          # ASSUMPTION
SLAB_THICKNESS_M = 0.20                     # ASSUMPTION
SUBGRADE_MODULUS_N_M3 = 80e6                # ASSUMPTION
CRAWLER_CLEARANCE_M = 0.05                  # ASSUMPTION, docs/dynamics_model.md 1.3 (operating point)
BODY_DAMPING_RATIO = 0.05                   # ASSUMPTION, heave zeta (dyn_model.py modal_damping_ratio_body)
ROD_LOCAL_DAMPING_RATIO = 0.3               # ASSUMPTION, total zeta of the L2 rod local mode, run_reference.py:316-319
SWIVEL_CENTER_ABOVE_PAD_BOTTOM_M = 0.06     # ASSUMPTION, docs/dynamics_model.md 2.1 (CAD has no swivel)
SWIVEL_TILT_RANGE_DEG = 10.0                # ASSUMPTION, docs/dynamics_model.md 2.2
PAD_JOINT = "spherical"                     # user decision 2026-10-19 (CLAUDE.md '다리 기하')
F_MIN_FRACTION = 0.10                       # user decision 2026-10-19 (CLAUDE.md 'F_min')
RIGID_FLOOR_FRICTION = 0.5                  # ASSUMPTION, docs/dynamics_model.md 4.2
CRAWLER_KN_TOTAL_N_M = 1.0e8                # ASSUMPTION, docs/dynamics_model.md 4.2
CRAWLER_FRICTION = 0.5                      # ASSUMPTION, docs/dynamics_model.md 4.2
# Time step rules (docs/dynamics_model.md 4.3; run_reference.py:289-294 dt_rec).
DT_LADDER_S = (1e-3, 5e-4, 2e-4, 1e-4, 5e-5, 2e-5, 1e-5)
DT_POINTS_PER_PERIOD = 50
DT_NUMERICAL_DAMPING_SHARE = 0.1  # L1: zeta_num = omega dt / 2 <= 10 % of the 1st rocking zeta
# ---- rev. 4: Chrono 10 input conventions (docs/dynamics_model.md 4.1, docs/chrono_stick_friction_test.md) ----
GROUND_BODY_MASS_KG = 1.0e9                 # implementation convention: fixed floor mass enters m_eff of SMC gn
BUSHING_DAMPING_INPUT_FACTOR = 0.5          # measured (pychrono 10.0.0): ChLoadBodyBodyBushing* damping acts at 2x input
SLIP_DAMPING_REENABLE_SPEED_M_S = 1.0e-3    # ASSUMPTION, stick friction test section 5 setting
L2B_NSC_SOLVER = "PSOR"                     # stick friction test 2.4 (APGD 25x slower, not used)
L2B_NSC_SOLVER_MAX_ITERATIONS = 50
L2B_NSC_FRICTION = 0.5                      # ASSUMPTION, docs/dynamics_model.md 4.2
# ---- rev. 4: hydraulic circuit (docs/hydraulic_circuit.md, CLAUDE.md '유압 회로' / '압력 한계') ----
RELIEF_PRESSURE_MOVING_PA = 2.10e7          # circuit drawing: MCV relief 210 bar (reached only at the stroke ends)
LOCKED_PRESSURE_LIMIT_PA = 3.50e7           # manufacturer: cylinder maximum load test pressure 350 bar (locked)
PUMP_FLOW_L_MIN = 60.2                      # circuit drawing: P6, 60.2 L/min
LOCK_VALVE = "pilot_check"                  # current circuit; option "counterbalance" (manufacturer plan)
RIGID_FLOOR_MODEL = (
    "L1: SMC Hooke, UseMaterialProperties false, normal only (kt = gt = mu = 0) + ground-fixed tangential bushing "
    "with circular Coulomb return mapping; L2b: ChSystemNSC (PSOR) + lateral leg bushing. SMC tangential models "
    "(OneStep/MultiStep) are not used: no stick in Chrono 10")
DAMPING_INPUT_CONVENTION = (
    "SMC Hooke gn, gt are per effective mass: gn = c_n / m_eff, m_eff = m_moving m_ground / (m_moving + m_ground); "
    "ChLoadBodyBodyBushing* damping acts at 2x the input: input = c / 2 (measured, pychrono 10.0.0)")
L1_TANGENTIAL_MODEL = (
    "ChLoadBodyBodyBushingSpherical, body A = leg moving part, body B = fixed floor, applied at the sphere contact "
    "point at first touch; axes = floor tangent plane + normal; normal stiffness and damping 0; after each step "
    "circular Coulomb return mapping with N = pad normal contact force (move B anchor by SetApplicationFrameB); "
    "damping off while sliding; anchor follows when N = 0")
L1_SMC_MATERIAL = "kn = kn_per_pad, gn = gn_per_pad, kt = 0, gt = 0, mu = 0; same values on the pad sphere and the floor shape"
L2B_NSC_AXIAL_STIFFNESS_FORMULA = "series(k_oil(s), k_rod, k_frame, k_concrete)"
CYLINDER_TYPE = ("double-acting; dual pilot-operated check valve mounted on the cylinder (both chambers locked); "
                 "hose outside the locked volume")
ROD_SIDE_CHAMBER_MODEL = "neglected (head side only); one-sided +10 % kv when the leg unloads, sensitivity only"
FLOW_CONTROL = "proportional directional valve, section pressure compensated (LS); load-independent speed"
PRESSURE_SENSOR_LOCATION = ("lock valve block on the cylinder (head chamber); reads the trapped load pressure while "
                            "locked; p = F_cyl / head area")
# Source line references "<file>.py:<first>[-<last>]" used in this script's comments: each range must contain the
# listed text in the current source (check_line_references). Update both when scripts/dynamics changes.
LINE_REFS = {
    ("dyn_model.py", 43, 68): ["ASSUMPTIONS = {", '"F_min_basis"'],
    ("dyn_model.py", 170, 171): ["def piston_area"],
    ("dyn_model.py", 174, 178): ["def k_oil", "dead + np.asarray(ext"],
    ("dyn_model.py", 181, 184): ["def k_rod", "/ rod_length"],
    ("dyn_model.py", 187, 200): ["def k_concrete_westergaard", "k_slab = 8 * ks * l**2"],
    ("dyn_model.py", 203, 233): ["def k_leg_lateral(", "return 1.0 / a11"],
    ("dyn_model.py", 203, 240): ["def k_leg_lateral(", "def k_leg_lateral_legs"],
    ("dyn_model.py", 236, 240): ["def k_leg_lateral_legs"],
    ("dyn_model.py", 243, 244): ["def series"],
    ("run_reference.py", 75, 76): ["touch = geo.touch_extension", 'e_op = touch + A_["crawler_clearance_m"]'],
    ("run_reference.py", 84, 92): ["kc_nom = wc", "ko_eff = dm.series(ko, kr, kf)", "kh_free = dm.k_leg_lateral_legs"],
    ("run_reference.py", 289, 294): ["def dt_rec", "if dt <= T / ppc"],
    ("run_reference.py", 289, 297): ["def dt_rec", "f_rod_local = math.sqrt((ko_eff.mean() + kc_nom)"],
    ("run_reference.py", 297, 297): ["f_rod_local = math.sqrt((ko_eff.mean() + kc_nom)"],
    ("run_reference.py", 311, 336): ["zt = A_", "L1_rigid_motor_lumped_contact", "L2b_NSC_force_motor_axial_spring"],
    ("run_reference.py", 313, 326): ["k_L1 = kv_H", "kt_L1 = dm.series(kh_free, kc_nom)", "c_tan=2 * zt"],
    ("run_reference.py", 315, 315): ["c_o = 2 * zt * np.sqrt(ko_eff * W_tot / g / 4)"],
    ("run_reference.py", 316, 319): ["zeta_rod = 0.3", "c_c = 2 * zeta_rod"],
    ("run_reference.py", 334, 335): ["L2b_NSC_force_motor_axial_spring_lateral_bushing", "kh=kt_L1", "ko=kv_H"],
    ("run_reference.py", 370, 370): ["ch=2 * zt * np.sqrt(cfg[\"kh\"] * W_tot / g / 4)"],
    ("run_reference.py", 395, 395): ["\"c_tangential_N_s_m\": r(2 * zt * np.sqrt(cfg[\"kh\"] * W_tot / g / 4))"],
    ("run_reference.py", 400, 402): ["L1_numerical_damping_bound_s", "0.2 * z1 / (2 * math.pi * f1)"],
    ("run_reference.py", 404, 405): ["L2b_NSC_rod_on_axial_spring_Hz", "L2b_NSC_dt_s", "kv_H.mean() / m_rod"],
    ("run_reference.py", 411, 426): ["A_head = dm.piston_area()", "A_ann = math.pi / 4", "p_max = 210e5",
                                     "max_rod_side_force_N", "pump_flow_L_min"],
}
# Pad plate split (SCM bodies): the pad plate is the part of the rod+pad solid below this height above the pad
# bottom face (task definition 2026-10-19: "바닥에서 25 mm 두께 판 부분" = pad.thickness_m measured from the BREP).
PAD_SPLIT_HEIGHT_MM = 25.0
# docs/dynamics_model.md section 10 values as printed (check only; tolerance = half a unit of the last digit).
DOC10_EXPECTED = {
    "L1.kn_per_pad_N_m": ([2.081e7, 2.081e7, 2.125e7, 2.125e7], 0.0005e7),
    "L1.kt_per_pad_N_m": ([8.510e6, 8.510e6, 8.404e6, 8.404e6], 0.0005e6),
    "L1.cn_per_pad_N_s_m": ([4.504e4, 4.504e4, 4.551e4, 4.551e4], 0.0005e4),
    "L1.ct_per_pad_N_s_m": ([2.880e4, 2.880e4, 2.862e4, 2.862e4], 0.0005e4),
    "L1.dt_s": ([2.0e-4], 0.05e-4),
    "L2.kn_per_pad_N_m": ([3.24e8] * 4, 0.005e8),
    "L2.kt_per_pad_N_m": ([3.24e8] * 4, 0.005e8),
    "L2.cn_per_pad_N_s_m": ([6.875e4, 6.875e4, 6.832e4, 6.832e4], 0.0005e4),
    "L2.ct_per_pad_N_s_m": ([1.776e5] * 4, 0.0005e5),
    "L2.oil_damping_N_s_m": ([4.656e4, 4.656e4, 4.708e4, 4.708e4], 0.0005e4),
    "L2.lateral_bushing_N_m": ([8.740e6, 8.740e6, 8.628e6, 8.628e6], 0.0005e6),
    "L2.lateral_bushing_damping_N_s_m": ([2.880e4, 2.880e4, 2.862e4, 2.862e4], 0.0005e4),
    "L2.dt_s": ([5.0e-5], 0.05e-5),
    "concrete.k_N_m": ([3.24e8], 0.005e8),
    # rev. 4 prints 9452.55 (the double rounding 9452.5475 -> 9452.55 -> 9452.6 of rev. 3 is resolved)
    "F_min_cylinder_N": ([9452.55], 0.005),
    # ---- rev. 4 table "개정 4에서 더할 키" ----
    "ground_body_mass_kg": ([1.0e9], 0.05e9),
    "L1.gn_per_pad_1_s": ([421.77, 421.77, 426.15, 426.15], 0.005),
    "L1.bushing_stiffness_per_pad_N_m": ([8.510e6, 8.510e6, 8.404e6, 8.404e6], 0.0005e6),
    "L1.bushing_damping_input_per_pad_N_s_m": ([1.43997e4, 1.43997e4, 1.43090e4, 1.43090e4], 0.000005e4),
    "L1.slip_damping_reenable_speed_m_s": ([1.0e-3], 0.05e-3),
    "L2b_NSC.solver_max_iterations": ([50], 0.5),
    "L2b_NSC.friction": ([0.5], 0.05),
    "L2b_NSC.axial_stiffness_operating_point_N_m": ([2.081e7, 2.081e7, 2.125e7, 2.125e7], 0.0005e7),
    "L2b_NSC.oil_damping_N_s_m": ([4.656e4, 4.656e4, 4.708e4, 4.708e4], 0.0005e4),
    "L2b_NSC.lateral_bushing_N_m": ([8.510e6, 8.510e6, 8.404e6, 8.404e6], 0.0005e6),
    "L2b_NSC.lateral_bushing_damping_input_N_s_m": ([1.43997e4, 1.43997e4, 1.43090e4, 1.43090e4], 0.000005e4),
    "L2b_NSC.dt_s": ([2.0e-4], 0.05e-4),
    "annulus_area_m2": ([8.83573e-4], 0.000005e-4),
    "relief_pressure_moving_Pa": ([2.10e7], 0.005e7),
    "max_force_extend_N": ([2.18125e5], 0.000005e5),
    "max_force_retract_N": ([1.8555e4], 0.00005e4),
    "locked_pressure_limit_Pa": ([3.50e7], 0.005e7),
    "locked_force_limit_N (printed 3.635e5)": ([3.635e5], 0.0005e5),
    "pump_flow_m3_s": ([1.00333e-3], 0.000005e-3),
}


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def sig(value: float, digits: int = SIGNIFICANT_DIGITS) -> float:
    """Round to significant digits (keeps tiny off-diagonal terms meaningful)."""
    value = float(value)
    if value == 0.0 or not np.isfinite(value):
        return 0.0 if value == 0.0 else value
    return float(f"{value:.{digits}g}")


def vec(values, digits: int = SIGNIFICANT_DIGITS) -> list:
    return [sig(v, digits) for v in np.asarray(values, dtype=float).ravel()]


def mat(values) -> list:
    """3x3 matrix; round-off noise below 1e-12 of the largest entry is written as 0."""
    values = np.asarray(values, dtype=float)
    values = np.where(np.abs(values) < 1e-12 * np.max(np.abs(values)), 0.0, values)
    return [vec(row) for row in values]


def body_from_cad_mm(point_mm) -> np.ndarray:
    return CAD_TO_BODY @ (np.asarray(point_mm, dtype=float) * MM)


def mass_properties_si(properties) -> dict:
    """MassProperties (CAD, kg, mm, kg*mm^2) -> body frame SI, full precision."""
    inertia = CAD_TO_BODY @ (properties.inertia_kg_mm2 * 1e-6) @ CAD_TO_BODY.T
    return {
        "mass_kg": float(properties.mass_kg),
        "com_m": CAD_TO_BODY @ (properties.cog_mm * MM),
        "inertia_kg_m2": 0.5 * (inertia + inertia.T),
    }


# --------------------------------------------------------------------------
# Independent case C re-implementation (check only)
# --------------------------------------------------------------------------
def independent_case_c(parts: pd.DataFrame, travel_mm: float, rows: pd.Series) -> dict:
    """Case C superstructure without the analysis helpers: own density rule and own sums."""
    used = parts[rows & (parts["volume_used_mm3"] > 0)]
    is_tool = (used["top_assembly"] == TOOL_TOP).to_numpy()
    is_moving = used["top_assembly"].isin([DRIVE_TOP, TOOL_TOP]).to_numpy()
    rho = np.where(is_tool, STEEL_DENSITY_G_CM3, used["density_step_g_cm3"].to_numpy()) * 1e-6  # kg/mm^3
    mass = used["volume_used_mm3"].to_numpy() * rho
    centroid = used[CENTROID_COLUMNS].to_numpy().copy()
    centroid[is_moving, 1] += travel_mm
    total = mass.sum()
    com = mass @ centroid / total
    inertia = np.zeros((3, 3))
    for (i, j), column in INERTIA_COLUMNS.items():
        value = float((used[column].to_numpy() * rho).sum())
        inertia[i, j] = inertia[j, i] = value
    d = centroid - com
    inertia += (mass * (d * d).sum(axis=1)).sum() * np.eye(3) - np.einsum("k,ki,kj->ij", mass, d, d)
    body_inertia = CAD_TO_BODY @ (inertia * 1e-6) @ CAD_TO_BODY.T
    return {"mass_kg": total, "com_m": CAD_TO_BODY @ (com * MM), "inertia_kg_m2": body_inertia}


def relative_difference(a, b) -> float:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    scale = max(np.max(np.abs(b)), 1e-12)
    return float(np.max(np.abs(a - b)) / scale)


def check_line_references() -> dict:
    """Source line references of this script vs the current scripts/dynamics sources.

    (a) every LINE_REFS range must contain its listed text (catches renumbering after a dynamics revision);
    (b) every "<dyn_model|run_reference>.py:<first>[-<last>]" written in this file must be a LINE_REFS range.
    """
    lines = {name: (DYN_MODEL_DIR / name).read_text(encoding="utf-8").splitlines()
             for name in ("dyn_model.py", "run_reference.py")}
    missing = []
    for (name, first, last), needles in LINE_REFS.items():
        block = "\n".join(lines[name][first - 1:last])
        missing += [f"{name}:{first}-{last} lacks {needle!r}" for needle in needles if needle not in block]
    own = Path(__file__).read_text(encoding="utf-8")
    used = {(m[1] + ".py", int(m[2]), int(m[3] or m[2]))
            for m in re.finditer(r"\b(dyn_model|run_reference)\.py:(\d+)(?:-(\d+))?", own)}
    unlisted = sorted(f"{n}:{a}-{b}" for n, a, b in used - set(LINE_REFS))
    # stale "lines N" style references (the format used before rev. 4) must not remain
    old_style = re.findall(r"(?:dyn_model|run_reference)\.py[^\n]{0,60}?\blines? \d+", own)
    return {"ranges_checked": len(LINE_REFS), "references_in_source": len(used), "missing_text": missing,
            "unlisted_references": unlisted, "old_style_references": old_style}


# --------------------------------------------------------------------------
# Pad bottom face from the cached BREP
# --------------------------------------------------------------------------
def pad_bottom_face(brep_file: str) -> dict:
    """Lowest planar face with normal -Y_cad of the rod+pad solid: polygon, area, centroid.

    Also measures the pad plate profile:
      thickness   = bottom face to the lowest planar face with normal +Y_cad above it
                    (the pad top face around the rod boss);
      side height = height of the vertical planar side faces that start at the bottom face
                    (the rest of the thickness is the top-edge chamfer).
    """
    shape = TopoDS_Shape()
    if not breptools.Read(shape, str(LEG_BREP_DIR / brep_file), BRep_Builder()):
        raise SystemExit(f"cannot read {brep_file}")
    best = None
    up_faces = []  # (y, area) of planar faces facing +Y_cad
    side_faces = []  # (y_min, y_max) of vertical planar faces
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = topods.Face(explorer.Current())
        explorer.Next()
        surface = BRepAdaptor_Surface(face, True)
        if surface.GetType() != GeomAbs_Plane:
            continue
        normal = surface.Plane().Axis().Direction()
        n = np.array([normal.X(), normal.Y(), normal.Z()])
        if face.Orientation() == TopAbs_REVERSED:
            n = -n
        y = surface.Plane().Location().Y()
        if abs(n[1]) < 1e-3:
            box = Bnd_Box()
            brepbndlib.AddOptimal(face, box, False, False)  # exact, without the face tolerance
            _, y_low, _, _, y_high, _ = box.Get()
            side_faces.append((y_low, y_high))
            continue
        if n[1] > 0.999:
            up_properties = GProp_GProps()
            brepgprop.SurfaceProperties(face, up_properties)
            up_faces.append((y, up_properties.Mass()))
            continue
        if n[1] > -0.999:
            continue
        if best is None or y < best[1]:
            best = (face, y)
    face, y = best
    above = [f for f in up_faces if f[0] > y]
    top_y, top_area = min(above) if above else (np.nan, np.nan)
    sides = [high - y for low, high in side_faces if abs(low - y) < 1e-3]
    side_height = max(sides) if sides else np.nan
    properties = GProp_GProps()
    brepgprop.SurfaceProperties(face, properties)
    centre = properties.CentreOfMass()
    wire = breptools.OuterWire(face)
    points = []
    wire_explorer = BRepTools_WireExplorer(wire)
    while wire_explorer.More():
        p = BRep_Tool.Pnt(wire_explorer.CurrentVertex())
        points.append([p.X(), p.Y(), p.Z()])
        wire_explorer.Next()
    points = np.array(points)
    return {
        "y_cad_mm": float(y),
        "area_mm2": float(properties.Mass()),
        "centroid_cad_mm": np.array([centre.X(), centre.Y(), centre.Z()]),
        "vertices_cad_mm": points,
        "thickness_mm": float(top_y - y),
        "side_height_mm": float(side_height),
        "side_face_count": len(sides),
        "top_face_area_mm2": float(top_area),
    }


def polygon_area(xy: np.ndarray) -> float:
    x, y = xy[:, 0], xy[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


# --------------------------------------------------------------------------
# SCM bodies: split the rod+piston+pad solid into pad plate and rod+piston
# --------------------------------------------------------------------------
def _solid_count(shape) -> int:
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    count = 0
    while explorer.More():
        count += 1
        explorer.Next()
    return count


def _volume_properties(shape) -> dict:
    """Unit-density volume properties in the CAD frame: volume mm^3, centroid mm, inertia mm^5 about the centroid."""
    properties = GProp_GProps()
    brepgprop.VolumeProperties(shape, properties)
    centre = properties.CentreOfMass()
    matrix = properties.MatrixOfInertia()  # about the centroid, tensor form (same as extract_parts.py)
    box = Bnd_Box()
    brepbndlib.AddOptimal(shape, box, False, False)
    return {
        "volume_mm3": float(properties.Mass()),
        "centroid_mm": np.array([centre.X(), centre.Y(), centre.Z()]),
        "inertia_mm5": np.array([[matrix.Value(r, c) for c in (1, 2, 3)] for r in (1, 2, 3)]),
        "bbox_mm": np.array(box.Get()).reshape(2, 3),
        "solids": _solid_count(shape),
        "valid": bool(BRepCheck_Analyzer(shape).IsValid()),
    }


def split_rod_pad(brep_file: str, pad_bottom_y_mm: float, split_height_mm: float) -> dict:
    """Split the leg moving-part solid by the plane Y_cad = pad bottom + split_height_mm.

    pad   = solid below the plane (the octagonal plate incl. its top-edge chamfer),
    rod   = solid above the plane: rod + piston + boss (largest piece) and the 4 gussets on the pad top face
            (separate solids once the plate is removed; the caller moves them to the pad body, doc 2.6).
    Implemented as a boolean common / cut with a box (half space below the plane).
    Returns unit-density volume properties (CAD frame, mm) of whole, pad and rod.
    """
    shape = TopoDS_Shape()
    if not breptools.Read(shape, str(LEG_BREP_DIR / brep_file), BRep_Builder()):
        raise SystemExit(f"cannot read {brep_file}")
    whole = _volume_properties(shape)
    (x0, y0, z0), (x1, y1, z1) = whole["bbox_mm"]
    margin = 10.0
    lower = BRepPrimAPI_MakeBox(gp_Pnt(x0 - margin, y0 - margin, z0 - margin),
                                gp_Pnt(x1 + margin, pad_bottom_y_mm + split_height_mm, z1 + margin)).Shape()
    pad = _volume_properties(BRepAlgoAPI_Common(shape, lower).Shape())
    rod_shape = BRepAlgoAPI_Cut(shape, lower).Shape()
    rod = _volume_properties(rod_shape)
    # Volumes of the rod-side solids (largest = rod/boss, the others = gussets) for the report.
    pieces = []
    explorer = TopExp_Explorer(rod_shape, TopAbs_SOLID)
    while explorer.More():
        pieces.append(_volume_properties(explorer.Current()))
        explorer.Next()
    pieces.sort(key=lambda p: -p["volume_mm3"])
    return {"whole": whole, "pad": pad, "rod": rod, "rod_pieces": pieces}


def unit_to_mass_properties_si(props: dict, density_kg_mm3: float, offset_m: np.ndarray) -> dict:
    """Unit-density CAD properties -> mass kg, CoM (body frame, m, + offset) and inertia about CoM (body axes)."""
    inertia = CAD_TO_BODY @ (props["inertia_mm5"] * density_kg_mm3 * 1e-6) @ CAD_TO_BODY.T
    return {
        "mass_kg": props["volume_mm3"] * density_kg_mm3,
        "com_m": CAD_TO_BODY @ (props["centroid_mm"] * MM) + offset_m,
        "inertia_kg_m2": 0.5 * (inertia + inertia.T),
    }


def _inside_cad_bbox(com_body_m: np.ndarray, bbox_mm: np.ndarray) -> bool:
    """Body-frame CoM (CAD pose) inside a CAD-frame bounding box (mm)."""
    point_mm = CAD_TO_BODY.T @ np.asarray(com_body_m, float) / MM
    return bool(np.all(point_mm >= bbox_mm[0] - 1e-6) and np.all(point_mm <= bbox_mm[1] + 1e-6))


def combine_two(a: dict, b: dict) -> dict:
    """Parallel-axis combination of two rigid bodies (mass, com, inertia about own com, same axes)."""
    mass = a["mass_kg"] + b["mass_kg"]
    com = (a["mass_kg"] * a["com_m"] + b["mass_kg"] * b["com_m"]) / mass
    inertia = np.zeros((3, 3))
    for part in (a, b):
        d = part["com_m"] - com
        inertia += part["inertia_kg_m2"] + part["mass_kg"] * (d @ d * np.eye(3) - np.outer(d, d))
    return {"mass_kg": mass, "com_m": com, "inertia_kg_m2": inertia}


# --------------------------------------------------------------------------
# Dynamics: L1 / L2 stiffness, damping and time step (transcribed from scripts/dynamics)
# --------------------------------------------------------------------------
def series(*ks):
    """dyn_model.py:243-244 series(): springs in series."""
    return 1.0 / sum(1.0 / np.asarray(k, float) for k in ks)


def piston_area() -> float:
    """dyn_model.py:170-171 piston_area() (head side, full bore area)."""
    return np.pi / 4 * BORE_DIAMETER_M ** 2


def k_oil(ext):
    """dyn_model.py:174-178 k_oil(): locked oil column beta A / (L0 + e)."""
    return OIL_BULK_MODULUS_EFF_PA * piston_area() / (OIL_DEAD_LENGTH_M + np.asarray(ext, float))


def k_rod() -> float:
    """dyn_model.py:181-184 k_rod(): E A / L, L = 1.05 m."""
    return STEEL_E_PA * np.pi / 4 * ROD_DIAMETER_M ** 2 / ROD_LENGTH_FOR_K_ROD_M


def k_concrete_slab() -> float:
    """dyn_model.py:187-200 k_concrete_westergaard(): k = 8 k_s l^2, l = (D / k_s)^(1/4)."""
    d = CONCRETE_E_PA * SLAB_THICKNESS_M ** 3 / (12 * (1 - CONCRETE_NU ** 2))
    radius = (d / SUBGRADE_MODULUS_N_M3) ** 0.25
    return 8 * SUBGRADE_MODULUS_N_M3 * radius ** 2


def k_leg_lateral_swivel(ext: float, attach_z: float, barrel_bottom_z: float, pad_bottom_retracted_z: float) -> float:
    """dyn_model.py:203-233 k_leg_lateral(ext, guided_tip=False, ...) via dyn_model.py:236-240 k_leg_lateral_legs().

    Fixed-free 2-segment Euler-Bernoulli beam with the leg's own geometry (YAML values): barrel D160/D115 from
    attachment_point_m z to barrel_z_range_m[0], rod D110 from there to the load point = swivel centre
    (pad bottom - ext + swivel_center_above_pad_bottom_m; the ball transmits no moment).
    """
    e_mod = STEEL_E_PA
    ei1 = e_mod * np.pi / 64 * (BARREL_OUTER_DIAMETER_M ** 4 - BORE_DIAMETER_M ** 4)
    ei2 = e_mod * np.pi / 64 * ROD_DIAMETER_M ** 4
    tip_z = pad_bottom_retracted_z - ext + SWIVEL_CENTER_ABOVE_PAD_BOTTOM_M
    length1 = attach_z - barrel_bottom_z
    length2 = barrel_bottom_z - tip_z
    length = length1 + length2
    s = np.linspace(0.0, length, 20001)
    ei = np.where(s < length1, ei1, ei2)
    return 1.0 / np.trapezoid((length - s) ** 2 / ei, s)


def dt_ladder(dt_max: float) -> float:
    """run_reference.py:289-294 dt_rec(): largest ladder value <= dt_max."""
    for dt in DT_LADDER_S:
        if dt <= dt_max:
            return dt
    return DT_LADDER_S[-1]


def dynamics_derivation(pad_z: np.ndarray, attach_z: np.ndarray, barrel_bottom_z: np.ndarray,
                        crawler_bottom_z: float, rod_mass: np.ndarray,
                        superstructure_mass_top: float, l1_first_mode: tuple[float, float]) -> dict:
    """All derived dynamics values, per leg in LEG_ORDER (inputs = values as written to the YAML).

    Sources: run_reference.py:75-76 (operating point), run_reference.py:84-92 (stiffness),
    run_reference.py:311-336 (L1 / L2 / L2b / L2b-NSC configurations), run_reference.py:370 and
    run_reference.py:395 (tangential / bushing damping), run_reference.py:297 (rod local mode),
    run_reference.py:400-402 (L1 time step rule), run_reference.py:404-405 (L2b-NSC time step),
    run_reference.py:411-426 (hydraulic circuit), docs/dynamics_model.md 4.1 (Chrono input conventions).
    rod_mass is legs.<leg>.moving_part.mass_kg (the SMC contact pair is moving part + floor, doc 4.1).
    """
    e_op = (pad_z - crawler_bottom_z) + CRAWLER_CLEARANCE_M           # touch extension + clearance
    kc = k_concrete_slab()
    ko = k_oil(e_op)
    kr = k_rod()
    ko_eff = series(ko, kr, FRAME_STIFFNESS_N_M)                      # oil + rod + frame (axial)
    kh_free = np.array([k_leg_lateral_swivel(e_op[i], attach_z[i], barrel_bottom_z[i], pad_z[i]) for i in range(4)])
    m_tot = superstructure_mass_top + rod_mass.sum()                  # body_with_rods(top).mass = W_tot / g
    kn_l1 = series(ko_eff, kc)
    kt_l1 = series(kh_free, kc)
    zeta = BODY_DAMPING_RATIO
    cn_l1 = 2 * zeta * np.sqrt(kn_l1 * m_tot / 4)
    ct_l1 = 2 * zeta * np.sqrt(kt_l1 * m_tot / 4)
    c_oil = 2 * zeta * np.sqrt(ko_eff * m_tot / 4)
    # L2 contact dashpot: total zeta 0.30 on the rod local mode, minus the oil dashpot acting in parallel
    c_contact_l2 = 2 * ROD_LOCAL_DAMPING_RATIO * np.sqrt((ko_eff + kc) * rod_mass.mean()) - c_oil
    ct_l2 = 2 * zeta * np.sqrt(np.full(4, kc) * m_tot / 4)            # L2 tangential, kt = concrete
    c_bushing_l2b = 2 * zeta * np.sqrt(series(kh_free, kc) * m_tot / 4)  # L2b lateral (kh = series(bushing, kc))
    # L1 dt: numerical damping of EULER_IMPLICIT_LINEARIZED zeta_num ~ omega dt / 2 <= 10 % of the 1st rocking zeta
    f1, zeta1 = l1_first_mode
    dt_l1_max = 2 * DT_NUMERICAL_DAMPING_SHARE * zeta1 / (2 * np.pi * f1)
    # L2 dt: >= 50 steps per period of the rod local mode (rod between oil spring and concrete contact)
    f_rod_local = np.sqrt((ko_eff.mean() + kc) / rod_mass.mean()) / (2 * np.pi)
    dt_l2_max = 1.0 / f_rod_local / DT_POINTS_PER_PERIOD
    # ---- rev. 4 (docs/dynamics_model.md 4.1 / 4.4 / 10) ----
    # SMC Hooke gn per effective mass of the contact pair (moving part + fixed floor); doc 10 defines
    # gn = cn / m_moving (the 1e9 kg floor changes m_eff by ~1e-7 relative; the exact m_eff is in the checks).
    gn_l1 = cn_l1 / rod_mass
    m_eff = rod_mass * GROUND_BODY_MASS_KG / (rod_mass + GROUND_BODY_MASS_KG)
    bushing_input_l1 = BUSHING_DAMPING_INPUT_FACTOR * ct_l1     # Chrono input = actual c_t / 2
    # L2b-NSC: axial force law = series(oil, rod, frame, concrete) (operating point) = L1 kn; bushing = L1 kt
    k_axial_l2b = series(ko_eff, kc)
    bushing_l2b = kt_l1
    bushing_damping_l2b = 2 * zeta * np.sqrt(bushing_l2b * m_tot / 4)   # run_reference.py:395 with kh = kt_L1
    bushing_input_l2b = BUSHING_DAMPING_INPUT_FACTOR * bushing_damping_l2b
    # L2b-NSC dt: the rod is held by the rigid contact; if it separates it rides on the axial spring alone
    f_rod_axial = np.sqrt(k_axial_l2b.mean() / rod_mass.mean()) / (2 * np.pi)
    dt_l2b_max = 1.0 / f_rod_axial / DT_POINTS_PER_PERIOD
    # hydraulic circuit: head / annulus areas, force limits at 210 bar (moving) and 350 bar (locked)
    head_area = piston_area()
    annulus_area = np.pi / 4 * (BORE_DIAMETER_M ** 2 - ROD_DIAMETER_M ** 2)
    pump_flow_m3_s = PUMP_FLOW_L_MIN / 60000.0
    return {
        "pad_z": pad_z, "attach_z": attach_z, "barrel_bottom_z": barrel_bottom_z,
        "e_op": e_op, "kc": kc, "ko": ko, "kr": kr, "ko_eff": ko_eff, "kh_free": kh_free, "m_tot": m_tot,
        "kn_l1": kn_l1, "kt_l1": kt_l1, "cn_l1": cn_l1, "ct_l1": ct_l1, "c_oil": c_oil, "c_contact_l2": c_contact_l2,
        "ct_l2": ct_l2, "c_bushing_l2b": c_bushing_l2b,
        "f1_l1": f1, "zeta1_l1": zeta1, "dt_l1_max": dt_l1_max, "dt_l1": dt_ladder(dt_l1_max),
        "f_rod_local": f_rod_local, "dt_l2_max": dt_l2_max, "dt_l2": dt_ladder(dt_l2_max),
        "rod_mass": rod_mass, "gn_l1": gn_l1, "m_eff": m_eff, "gn_l1_exact_m_eff": cn_l1 / m_eff, "bushing_input_l1": bushing_input_l1,
        "k_axial_l2b": k_axial_l2b, "bushing_l2b": bushing_l2b, "bushing_damping_l2b": bushing_damping_l2b,
        "bushing_input_l2b": bushing_input_l2b,
        "f_rod_axial_l2b": f_rod_axial, "dt_l2b_max": dt_l2b_max, "dt_l2b": dt_ladder(dt_l2b_max),
        "head_area": head_area, "annulus_area": annulus_area,
        "max_force_extend": RELIEF_PRESSURE_MOVING_PA * head_area,
        "max_force_retract": RELIEF_PRESSURE_MOVING_PA * annulus_area,
        "locked_force_limit": LOCKED_PRESSURE_LIMIT_PA * head_area,
        "pump_flow_m3_s": pump_flow_m3_s, "flow_4_legs_at_vmax_m3_s": 4 * MAX_SPEED_M_S * head_area,
    }


def dynamics_checks(derived: dict, reference: dict, dt_values: dict, f_min: float) -> dict:
    """Generated values vs (a) dyn_model.py at full precision, (b) reference.json (6 significant digits),
    (c) docs/dynamics_model.md section 10 as printed."""
    out = {}
    # (a) full precision: import the dynamics module itself (pure functions, no YAML read)
    try:
        sys.path.insert(0, str(DYN_MODEL_DIR))
        sys.dont_write_bytecode = True  # do not write __pycache__ into scripts/dynamics (read-only for this script)
        import dyn_model as dm  # noqa: PLC0415
        a = dm.ASSUMPTIONS
        same_inputs = {
            "oil_bulk_modulus_eff_Pa": a["oil_bulk_modulus_eff_Pa"] == OIL_BULK_MODULUS_EFF_PA,
            "oil_dead_length_m": a["oil_dead_length_m"] == OIL_DEAD_LENGTH_M,
            "frame_bracket_stiffness_N_m": a["frame_bracket_stiffness_N_m"] == FRAME_STIFFNESS_N_M,
            "bore_rod_barrel_diameters": (a["bore_diameter_m"], a["rod_diameter_m"], a["barrel_outer_diameter_m"])
            == (BORE_DIAMETER_M, ROD_DIAMETER_M, BARREL_OUTER_DIAMETER_M),
            "steel_E_Pa": a["steel_E_Pa"] == STEEL_E_PA,
            "concrete": (a["concrete_E_Pa"], a["concrete_nu"], a["slab_thickness_m"], a["subgrade_modulus_N_m3"])
            == (CONCRETE_E_PA, CONCRETE_NU, SLAB_THICKNESS_M, SUBGRADE_MODULUS_N_M3),
            "crawler_clearance_m": a["crawler_clearance_m"] == CRAWLER_CLEARANCE_M,
            "modal_damping_ratio_body": a["modal_damping_ratio_body"] == BODY_DAMPING_RATIO,
            "swivel_ball_height_above_pad_bottom_m": a["swivel_ball_height_above_pad_bottom_m"]
            == SWIVEL_CENTER_ABOVE_PAD_BOTTOM_M,
            "swivel_tilt_range_deg": a["swivel_tilt_range_deg"] == SWIVEL_TILT_RANGE_DEG,
            "F_min_fraction_of_mean_leg_load": a["F_min_fraction_of_mean_leg_load"] == F_MIN_FRACTION,
        }
        e_op, m_tot = derived["e_op"], derived["m_tot"]
        kc = dm.k_concrete_westergaard()["k_slab_N_m"]
        ko_eff = dm.series(dm.k_oil(e_op), dm.k_rod(), a["frame_bracket_stiffness_N_m"])
        leg_geometry = SimpleNamespace(attach_z=derived["attach_z"], barrel_bottom_z=derived["barrel_bottom_z"],
                                       pad_z_retracted=derived["pad_z"])
        kh = dm.k_leg_lateral_legs(leg_geometry, e_op, False)
        kn, kt = dm.series(ko_eff, kc), dm.series(kh, kc)
        z = a["modal_damping_ratio_body"]
        cn_dm, ct_dm = 2 * z * np.sqrt(kn * m_tot / 4), 2 * z * np.sqrt(kt * m_tot / 4)
        head_dm = dm.piston_area()
        annulus_dm = np.pi / 4 * (a["bore_diameter_m"] ** 2 - a["rod_diameter_m"] ** 2)  # run_reference.py:411-426
        full = {
            "kc": kc, "ko_eff": ko_eff, "kh_free": kh, "kn_l1": kn, "kt_l1": kt,
            "cn_l1": cn_dm, "ct_l1": ct_dm,
            "c_oil": 2 * z * np.sqrt(ko_eff * m_tot / 4),
            "ct_l2": 2 * z * np.sqrt(np.full(4, kc) * m_tot / 4),
            "c_bushing_l2b": 2 * z * np.sqrt(kt * m_tot / 4),
            # rev. 4
            "gn_l1": cn_dm / derived["rod_mass"],
            "bushing_input_l1": ct_dm / 2,
            "k_axial_l2b": kn,
            "bushing_l2b": kt,
            "bushing_input_l2b": 2 * z * np.sqrt(kt * m_tot / 4) / 2,
            "f_rod_axial_l2b": np.sqrt(kn.mean() / derived["rod_mass"].mean()) / (2 * np.pi),
            "head_area": head_dm, "annulus_area": annulus_dm,
            "max_force_extend": 210e5 * head_dm, "max_force_retract": 210e5 * annulus_dm,
            "locked_force_limit": 350e5 * head_dm,
        }
        same_inputs["oil_bulk_modulus_range_Pa"] = list(a["oil_bulk_modulus_range_Pa"]) == OIL_BULK_MODULUS_SENSITIVITY_PA
        out["dyn_model_import"] = "ok"
        out["dyn_model_same_inputs"] = same_inputs
        out["dyn_model_full_precision_rel"] = {k: relative_difference(derived[k], v) for k, v in full.items()}
    except Exception as error:  # noqa: BLE001 - reported as a failing check
        out["dyn_model_import"] = f"failed: {error!r}"
    # (b) reference.json (run_reference.py rounds to 6 significant digits): compare after the same rounding
    tests = reference["chrono_test_references"]
    l1, l2 = tests["L1_rigid_motor_lumped_contact"], tests["L2_force_motor_oil_spring"]
    l2b = tests["L2b_force_motor_oil_spring_lateral_bushing"]
    nsc = tests["L2b_NSC_force_motor_axial_spring_lateral_bushing"]
    hyd = reference["hydraulic_circuit"]
    ts = reference["time_step"]
    stiff = reference["stiffness"]

    def r6(x):
        return [sig(v, 6) for v in np.atleast_1d(x)]

    pairs = {
        "levelled_extension_m": (r6(derived["e_op"]), reference["operating_point"]["levelled_extension_m"]),
        "k_slab_N_m": (r6(derived["kc"]), [stiff["concrete_westergaard"]["k_slab_N_m"]]),
        "k_axial_leg_N_m": (r6(derived["ko_eff"]), stiff["k_axial_leg_N_m (oil+rod+frame)"]),
        "k_lateral_leg_swivel_pad_N_m": (r6(derived["kh_free"]), stiff["k_lateral_leg_swivel_pad_N_m"]),
        "L1.kn": (r6(derived["kn_l1"]), l1["k_vertical_N_m"]),
        "L1.kt": (r6(derived["kt_l1"]), l1["k_horizontal_N_m"]),
        "L1.cn": (r6(derived["cn_l1"]), l1["c_pad_N_s_m"]),
        "L1.ct": (r6(derived["ct_l1"]), l1["c_tan_N_s_m"]),
        "L2.c_oil": (r6(derived["c_oil"]), l2["c_oil_N_s_m"]),
        "L2.c_contact": (r6(derived["c_contact_l2"]), l2["c_contact_N_s_m"]),
        "L2.c_tangential": (r6(derived["ct_l2"]), l2["c_tangential_N_s_m"]),
        "L2b.c_contact": (r6(derived["c_contact_l2"]), l2b["c_contact_N_s_m"]),
        "L2b.c_tangential (bushing damping)": (r6(derived["c_bushing_l2b"]), l2b["c_tangential_N_s_m"]),
        "L2b.k_horizontal": (r6(series(derived["kh_free"], derived["kc"])), l2b["k_horizontal_N_m"]),
        "F_min_cylinder_N": (r6(f_min), [l1["levels"]["top"]["F_min_cylinder_N"]]),
        "L2.dt_s": ([derived["dt_l2"]], [ts["H_dt_s"]]),
        # rev. 4
        "L1.dt_max_s (numerical damping bound, 4 digits)": ([sig(derived["dt_l1_max"], 4)],
                                                          [ts["L1_numerical_damping_bound_s (omega1 dt/2 <= 0.1 zeta1, top)"]]),
        "L1.gn = c_pad / moving mass": (r6(derived["gn_l1"]),
                                        r6(np.array(l1["c_pad_N_s_m"]) / derived["rod_mass"])),
        "L1.bushing_input = c_tan / 2": (r6(derived["bushing_input_l1"]), r6(np.array(l1["c_tan_N_s_m"]) / 2)),
        "L2b_NSC.k_axial (k_vertical)": (r6(derived["k_axial_l2b"]), nsc["k_vertical_N_m"]),
        "L2b_NSC.lateral_bushing (k_horizontal)": (r6(derived["bushing_l2b"]), nsc["k_horizontal_N_m"]),
        "L2b_NSC.c_oil": (r6(derived["c_oil"]), nsc["c_oil_N_s_m"]),
        "L2b_NSC.bushing_damping_actual (c_tangential)": (r6(derived["bushing_damping_l2b"]), nsc["c_tangential_N_s_m"]),
        "L2b_NSC.rod_on_axial_spring_Hz (4 digits)": ([sig(derived["f_rod_axial_l2b"], 4)],
                                                      [ts["L2b_NSC_rod_on_axial_spring_Hz (contact open)"]]),
        "L2b_NSC.dt_s": ([derived["dt_l2b"]], [ts["L2b_NSC_dt_s"]]),
        "hydraulic.annulus_area_m2": (r6(derived["annulus_area"]), [hyd["annulus_area_m2"]]),
        "hydraulic.head_area_m2": (r6(derived["head_area"]), [hyd["head_area_m2"]]),
        "hydraulic.relief_pressure_Pa": ([RELIEF_PRESSURE_MOVING_PA], [hyd["max_pressure_Pa"]]),
        "hydraulic.max_force_extend_N": (r6(derived["max_force_extend"]), [hyd["max_head_force_N"]]),
        "hydraulic.max_force_retract_N": (r6(derived["max_force_retract"]), [hyd["max_rod_side_force_N"]]),
        "hydraulic.pump_flow_L_min": ([derived["pump_flow_m3_s"] * 60000.0], [hyd["pump_flow_L_min"]]),
        "hydraulic.flow_4_legs_at_vmax_L_min (4 digits)": ([sig(derived["flow_4_legs_at_vmax_m3_s"] * 60000.0, 4)],
                                                           [hyd["flow_4_legs_at_vmax_L_min"]]),
    }
    out["reference_json_rel"] = {k: relative_difference(g, ref) for k, (g, ref) in pairs.items()}
    # rev. 4 consistency: exact m_eff (floor 1e9 kg) vs the m_moving definition of gn; pump covers 4 legs at v_max
    out["gn_m_moving_vs_exact_m_eff_rel"] = relative_difference(derived["gn_l1"], derived["gn_l1_exact_m_eff"])
    out["pump_flow_covers_4_legs_at_vmax"] = bool(derived["pump_flow_m3_s"] >= derived["flow_4_legs_at_vmax_m3_s"])
    out["line_references"] = check_line_references()
    # (c) document section 10 as printed
    generated = {
        "L1.kn_per_pad_N_m": derived["kn_l1"], "L1.kt_per_pad_N_m": derived["kt_l1"],
        "L1.cn_per_pad_N_s_m": derived["cn_l1"], "L1.ct_per_pad_N_s_m": derived["ct_l1"],
        "L1.dt_s": [dt_values["L1"]], "L2.kn_per_pad_N_m": [derived["kc"]] * 4,
        "L2.kt_per_pad_N_m": [derived["kc"]] * 4, "L2.cn_per_pad_N_s_m": derived["c_contact_l2"],
        "L2.ct_per_pad_N_s_m": derived["ct_l2"], "L2.lateral_bushing_damping_N_s_m": derived["c_bushing_l2b"],
        "L2.oil_damping_N_s_m": derived["c_oil"], "L2.lateral_bushing_N_m": derived["kh_free"],
        "L2.dt_s": [dt_values["L2"]], "concrete.k_N_m": [derived["kc"]], "F_min_cylinder_N": [f_min],
        # rev. 4
        "ground_body_mass_kg": [GROUND_BODY_MASS_KG],
        "L1.gn_per_pad_1_s": derived["gn_l1"],
        "L1.bushing_stiffness_per_pad_N_m": derived["kt_l1"],
        "L1.bushing_damping_input_per_pad_N_s_m": derived["bushing_input_l1"],
        "L1.slip_damping_reenable_speed_m_s": [SLIP_DAMPING_REENABLE_SPEED_M_S],
        "L2b_NSC.solver_max_iterations": [L2B_NSC_SOLVER_MAX_ITERATIONS],
        "L2b_NSC.friction": [L2B_NSC_FRICTION],
        "L2b_NSC.axial_stiffness_operating_point_N_m": derived["k_axial_l2b"],
        "L2b_NSC.oil_damping_N_s_m": derived["c_oil"],
        "L2b_NSC.lateral_bushing_N_m": derived["bushing_l2b"],
        "L2b_NSC.lateral_bushing_damping_input_N_s_m": derived["bushing_input_l2b"],
        "L2b_NSC.dt_s": [dt_values["L2b_NSC"]],
        "annulus_area_m2": [derived["annulus_area"]],
        "relief_pressure_moving_Pa": [RELIEF_PRESSURE_MOVING_PA],
        "max_force_extend_N": [derived["max_force_extend"]],
        "max_force_retract_N": [derived["max_force_retract"]],
        "locked_pressure_limit_Pa": [LOCKED_PRESSURE_LIMIT_PA],
        "locked_force_limit_N (printed 3.635e5)": [derived["locked_force_limit"]],
        "pump_flow_m3_s": [derived["pump_flow_m3_s"]],
    }
    doc = {}
    for key, (expected, tol) in DOC10_EXPECTED.items():
        diff = float(np.max(np.abs(np.asarray(generated[key], float) - np.asarray(expected, float))))
        doc[key] = {"max_abs_diff": diff, "half_unit_tol": tol,
                    "max_rel_diff": diff / float(np.max(np.abs(expected)))}
    out["doc10_printed"] = doc
    return out


# --------------------------------------------------------------------------
# Commented YAML emitter
# --------------------------------------------------------------------------
def _scalar(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        text = repr(float(value))
        if "e" in text and "." not in text:  # PyYAML (YAML 1.1) reads "5e-05" as a string; write "5.0e-05"
            mantissa, exponent = text.split("e")
            text = f"{mantissa}.0e{exponent}"
        return text
    text = str(value)
    return json.dumps(text, ensure_ascii=False)  # JSON strings are valid YAML double-quoted scalars


def _is_flow_list(value) -> bool:
    return isinstance(value, list) and all(not isinstance(v, (dict, list)) for v in value)


def _flow(value) -> str:
    if _is_flow_list(value):
        return "[" + ", ".join(_scalar(v) for v in value) + "]"
    return "[" + ", ".join(_flow(v) for v in value) + "]"


def emit(data: dict, comments: dict, indent: int = 0, path: str = "") -> list[str]:
    """YAML block mapping; comments[path] goes after scalars / before blocks. Paths use '.'."""
    lines = []
    pad = "  " * indent
    for key, value in data.items():
        key_path = f"{path}.{key}" if path else str(key)
        comment = comments.get(key_path)
        if isinstance(value, dict):
            if comment:
                lines.append(f"{pad}# {comment}")
            lines.append(f"{pad}{key}:")
            lines.extend(emit(value, comments, indent + 1, key_path))
            continue
        if isinstance(value, list) and value and all(isinstance(v, list) for v in value) and len(value) > 1 \
                and all(_is_flow_list(v) for v in value) and len(value) <= 8:
            if comment:
                lines.append(f"{pad}# {comment}")
            lines.append(f"{pad}{key}:")
            for row in value:
                lines.append(f"{pad}  - {_flow(row)}")
            continue
        text = _flow(value) if isinstance(value, list) else _scalar(value)
        line = f"{pad}{key}: {text}"
        if comment:
            line += f"  # {comment}"
        lines.append(line)
    return lines


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> None:
    parts_raw = pd.read_csv(CLASSIFIED_CSV, encoding="utf-8-sig")
    summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
    auger = json.loads(AUGER_JSON.read_text(encoding="utf-8"))
    table = add_tool_steel_case(classify(parts_raw))
    if TOOL_STEEL not in auger["levels"]["top"]["mass"]:
        raise SystemExit("cad/auger_levels.json has no case C; run analyze_auger_levels.py first")

    checks = {"levels": {}, "legs": {}, "totals": {}}
    comments = {}

    # ---------------- superstructure per auger level ----------------
    is_superstructure = table["group"] != "leg_rod_pad"
    levels = {}
    for name in LEVEL_NAMES:
        travel_mm = float(auger["levels"][name]["travel_mm"])
        posed = shifted(table, travel_mm)
        props = mass_properties_si(combine_mass_properties(posed[is_superstructure], TOOL_STEEL))
        pads_xy = np.array([summary["legs"][leg]["pad_center_body_m"][:2] for leg in LEG_ORDER])
        loads = leg_loads(pads_xy, props["mass_kg"], props["com_m"][:2])
        inertia = props["inertia_kg_m2"]
        levels[name] = {
            "auger_travel_m": sig(travel_mm * MM),
            "mass_kg": sig(props["mass_kg"]),
            "com_m": vec(props["com_m"]),
            "inertia_kg_m2": mat(inertia),
            "principal_moments_kg_m2": vec(np.linalg.eigvalsh(inertia)),
            "static_leg_loads_N": {leg: sig(v, 7) for leg, v in zip(LEG_ORDER, loads)},
        }
        # Checks: independent re-implementation, auger_levels.json, tensor validity, load equilibrium.
        independent = independent_case_c(parts_raw, travel_mm, parts_raw["group"] != "leg_rod_pad")
        reference = auger["levels"][name]["mass"][TOOL_STEEL]
        written = levels[name]
        checks["levels"][name] = {
            "independent_mass_rel": relative_difference(written["mass_kg"], independent["mass_kg"]),
            "independent_com_max_abs_m": float(np.max(np.abs(np.array(written["com_m"]) - independent["com_m"]))),
            "independent_inertia_rel_to_max": relative_difference(written["inertia_kg_m2"],
                                                                  independent["inertia_kg_m2"]),
            "auger_json_mass_abs_kg": abs(written["mass_kg"] - reference["mass_kg"]),
            "auger_json_com_max_abs_m": float(np.max(np.abs(np.array(written["com_m"])
                                                            - np.array(reference["cog_body_m"])))),
            "auger_json_inertia_max_abs_kg_m2": float(np.max(np.abs(np.array(written["inertia_kg_m2"])
                                                                    - np.array(reference["inertia_about_cog_body_kg_m2"])))),
            "auger_json_inertia_rel_to_max": relative_difference(written["inertia_kg_m2"],
                                                                 reference["inertia_about_cog_body_kg_m2"]),
            "auger_json_leg_loads_max_abs_kN": max(abs(written["static_leg_loads_N"][leg] / 1000
                                                       - reference["leg_loads_kN"][leg]) for leg in LEG_ORDER),
            "tensor": tensor_checks({"inertia_about_cog_body_kg_m2": written["inertia_kg_m2"]}),
            "leg_load_sum_rel_to_weight": abs(sum(written["static_leg_loads_N"].values())
                                              - written["mass_kg"] * GRAVITY_M_S2) / (written["mass_kg"] * GRAVITY_M_S2),
        }

    # Auger moving set (drive + tool) at the CAD pose, for models that move it as a separate body.
    moving_rows = table["motion"].isin(MOVING)
    moving = mass_properties_si(combine_mass_properties(table[moving_rows], TOOL_STEEL))
    fixed = mass_properties_si(combine_mass_properties(table[is_superstructure & ~moving_rows], TOOL_STEEL))

    # ---------------- legs ----------------
    legs = {}
    leg_masses = []
    for leg in LEG_ORDER:
        geometry = summary["legs"][leg]
        axis_x_cad, axis_z_cad = geometry["axis_cad_mm"]["X"], geometry["axis_cad_mm"]["Z"]
        axis_xy = body_from_cad_mm([axis_x_cad, 0.0, axis_z_cad])[:2]
        bracket = geometry["bracket_bolt_holes_y_cad_mm"]
        rows = table[(table["group"] == "leg_rod_pad") & (table["leg"] == leg)]
        if len(rows) != 1:
            raise SystemExit(f"{leg}: expected one rod+pad row, got {len(rows)}")
        rod = mass_properties_si(combine_mass_properties(rows, TOOL_STEEL))
        leg_masses.append(rod["mass_kg"])
        face = pad_bottom_face(ROD_PAD_BREP[leg])
        # CLAUDE.md "다리 기하": retracted state = moving part raised until the piston reaches the bore top,
        # so that every leg extends 0 ... STROKE_M. Offset (CAD pose -> retracted) along body +z, in mm.
        retract_offset_mm = STROKE_M / MM - geometry["remaining_extension_mm"]
        piston_gap_mm = geometry["bore_y_cad_mm"][1] - geometry["piston_y_cad_mm"][1]  # bore top - piston top
        offset_m = np.array([0.0, 0.0, retract_offset_mm * MM])
        pad_bottom_cad = body_from_cad_mm([axis_x_cad, geometry["pad_bottom_y_cad_mm"], axis_z_cad])
        pad_bottom = pad_bottom_cad + offset_m
        rod_com_retracted = rod["com_m"] + offset_m
        vertices_body = (CAD_TO_BODY @ (face["vertices_cad_mm"] * MM).T).T
        polygon = vertices_body[:, :2] - pad_bottom_cad[:2]
        if polygon_area(polygon) < 0:
            polygon = polygon[::-1]  # counter-clockwise seen from +z
        face_centroid_body = body_from_cad_mm(face["centroid_cad_mm"])
        # SCM bodies (docs/dynamics_model.md 2.1 / 10): pad plate and rod+piston from the same BREP solid.
        density_kg_mm3 = float(rows[f"density_{TOOL_STEEL}_g_cm3"].iloc[0]) * 1e-6
        split = split_rod_pad(ROD_PAD_BREP[leg], face["y_cad_mm"], PAD_SPLIT_HEIGHT_MM)
        # docs/dynamics_model.md 2.6 (rev. 3): the 4 gussets on the pad top face belong to the pad body; the rod
        # body is the largest solid above the plane (rod + piston + boss, incl. the rod between 25 and 60 mm).
        plate_body = unit_to_mass_properties_si(split["pad"], density_kg_mm3, offset_m)
        gussets = split["rod_pieces"][1:]
        pad_body = plate_body
        for gusset in gussets:
            pad_body = combine_two(pad_body, unit_to_mass_properties_si(gusset, density_kg_mm3, offset_m))
        rod_body = unit_to_mass_properties_si(split["rod_pieces"][0], density_kg_mm3, offset_m)
        whole_body = unit_to_mass_properties_si(split["whole"], density_kg_mm3, offset_m)
        pad_rod = combine_two(pad_body, rod_body)
        gusset_volume_mm3 = sum(p["volume_mm3"] for p in gussets)
        legs[leg] = {
            "cad_instance": geometry["jack_instance"],
            "cylinder_axis_xy_m": vec(axis_xy),
            "axis_direction": [0.0, 0.0, 1.0],
            "attachment_point_m": vec([*axis_xy, np.mean(bracket) * MM]),
            "bracket_bolt_hole_z_range_m": vec(np.array(bracket) * MM),
            "barrel_z_range_m": vec(np.array(geometry["barrel_y_cad_mm"]) * MM),
            "bore_z_range_m": vec(np.array(geometry["bore_y_cad_mm"]) * MM),
            "retracted_offset_from_cad_m": sig(retract_offset_mm * MM),
            "extension_range_m": [0.0, STROKE_M],
            "pad_bottom_center_retracted_m": vec(pad_bottom),
            "pad": {
                "shape": "octagon",
                "thickness_m": sig(face["thickness_mm"] * MM),
                "side_height_m": sig(face["side_height_mm"] * MM),
                "bottom_area_m2": sig(face["area_mm2"] * 1e-6),
                "polygon_xy_m": [vec(p) for p in polygon],
                "joint": PAD_JOINT,
                "swivel_center_above_pad_bottom_m": SWIVEL_CENTER_ABOVE_PAD_BOTTOM_M,
                "swivel_tilt_range_deg": SWIVEL_TILT_RANGE_DEG,
            },
            "moving_part": {
                "mass_kg": sig(rod["mass_kg"]),
                "com_retracted_m": vec(rod_com_retracted),
                "com_above_pad_bottom_m": sig(rod_com_retracted[2] - pad_bottom[2]),
                "inertia_kg_m2": mat(rod["inertia_kg_m2"]),
            },
            "pad_body": {
                "split_plane_above_pad_bottom_m": sig(PAD_SPLIT_HEIGHT_MM * MM),
                "mass_kg": sig(pad_body["mass_kg"]),
                "com_m": vec(pad_body["com_m"]),
                "com_above_pad_bottom_m": sig(pad_body["com_m"][2] - pad_bottom[2]),
                "inertia_kg_m2": mat(pad_body["inertia_kg_m2"]),
            },
            "rod_body": {
                "mass_kg": sig(rod_body["mass_kg"]),
                "com_m": vec(rod_body["com_m"]),
                "com_above_pad_bottom_m": sig(rod_body["com_m"][2] - pad_bottom[2]),
                "inertia_kg_m2": mat(rod_body["inertia_kg_m2"]),
            },
        }
        bbox_low = body_from_cad_mm(rows[["bbox_min_x_mm", "bbox_min_y_mm", "bbox_min_z_mm"]].to_numpy()[0])
        bbox_high = body_from_cad_mm(rows[["bbox_max_x_mm", "bbox_max_y_mm", "bbox_max_z_mm"]].to_numpy()[0])
        checks["legs"][leg] = {
            "tensor": tensor_checks({"inertia_about_cog_body_kg_m2": legs[leg]["moving_part"]["inertia_kg_m2"]}),
            "com_inside_part_bbox": bool(np.all(rod["com_m"] >= bbox_low - 1e-9) and np.all(rod["com_m"] <= bbox_high + 1e-9)),
            "pad_vertex_count": int(len(polygon)),
            "pad_face_y_vs_summary_mm": face["y_cad_mm"] - geometry["pad_bottom_y_cad_mm"],
            "pad_face_centroid_minus_axis_xy_mm": vec((face_centroid_body[:2] - pad_bottom_cad[:2]) / MM, 6),
            "retract_offset_mm": float(retract_offset_mm),
            "retract_offset_minus_piston_gap_mm": float(retract_offset_mm - piston_gap_mm),
            "com_above_pad_bottom_cad_minus_retracted_m": float((rod["com_m"][2] - pad_bottom_cad[2])
                                                                - (rod_com_retracted[2] - pad_bottom[2])),
            "pad_thickness_brep_mm": face["thickness_mm"],
            "pad_side_height_brep_mm": face["side_height_mm"],
            "pad_side_face_count": face["side_face_count"],
            "pad_side_height_brep_minus_doc_mm": face["side_height_mm"] - DOC_PAD_THICKNESS_MM,
            "pad_top_face_area_m2": face["top_face_area_mm2"] * 1e-6,
            "pad_area_brep_vs_polygon_rel": abs(face["area_mm2"] * 1e-6 - polygon_area(polygon))
            / (face["area_mm2"] * 1e-6),
            "rod_mass_vs_csv_rel": float(abs(rod["mass_kg"] - rows["mass_step_kg"].iloc[0]) / rod["mass_kg"]),
            "split": {
                "split_plane_minus_pad_thickness_mm": PAD_SPLIT_HEIGHT_MM - face["thickness_mm"],
                "whole_valid": split["whole"]["valid"], "pad_valid": split["pad"]["valid"],
                "rod_valid": split["rod"]["valid"],
                "whole_solids": split["whole"]["solids"], "pad_solids": split["pad"]["solids"],
                "rod_solids": split["rod"]["solids"],
                "rod_piece_volumes_mm3": [p["volume_mm3"] for p in split["rod_pieces"]],
                "gusset_count": len(gussets),
                "gusset_mass_kg_in_pad_body": gusset_volume_mm3 * density_kg_mm3,
                "plate_mass_kg": plate_body["mass_kg"],
                "gussets_touch_split_plane": bool(all(
                    abs(g["bbox_mm"][0][1] - (face["y_cad_mm"] + PAD_SPLIT_HEIGHT_MM)) < 1e-3 for g in gussets)),
                "rod_piece_starts_at_split_plane": bool(
                    abs(split["rod_pieces"][0]["bbox_mm"][0][1] - (face["y_cad_mm"] + PAD_SPLIT_HEIGHT_MM)) < 1e-3),
                "volume_pad_plus_rod_minus_whole_rel": abs(split["pad"]["volume_mm3"] + split["rod"]["volume_mm3"]
                                                           - split["whole"]["volume_mm3"]) / split["whole"]["volume_mm3"],
                "brep_whole_vs_moving_part_mass_rel": abs(whole_body["mass_kg"] - rod["mass_kg"]) / rod["mass_kg"],
                # pad + rod (parallel-axis theorem) vs the existing moving part (parts_classified.csv)
                "sum_mass_rel": abs(pad_rod["mass_kg"] - rod["mass_kg"]) / rod["mass_kg"],
                "sum_com_max_abs_m": float(np.max(np.abs(pad_rod["com_m"] - rod_com_retracted))),
                "sum_inertia_rel_to_max": relative_difference(pad_rod["inertia_kg_m2"], rod["inertia_kg_m2"]),
                # the same with the values as written to the YAML (9 significant digits)
                "written_sum_mass_rel": 0.0,
                "written_sum_com_max_abs_m": 0.0,
                "written_sum_inertia_rel_to_max": 0.0,
                "pad_tensor": tensor_checks({"inertia_about_cog_body_kg_m2": legs[leg]["pad_body"]["inertia_kg_m2"]}),
                "rod_tensor": tensor_checks({"inertia_about_cog_body_kg_m2": legs[leg]["rod_body"]["inertia_kg_m2"]}),
                "pad_com_inside_bbox": _inside_cad_bbox(pad_body["com_m"] - offset_m, split["pad"]["bbox_mm"]),
                "rod_com_inside_bbox": _inside_cad_bbox(rod_body["com_m"] - offset_m, split["rod_pieces"][0]["bbox_mm"]),
                "pad_com_below_split_plane": bool(pad_body["com_m"][2] - pad_bottom[2] < PAD_SPLIT_HEIGHT_MM * MM),
                "rod_com_above_split_plane": bool(rod_body["com_m"][2] - pad_bottom[2] > PAD_SPLIT_HEIGHT_MM * MM),
            },
        }
        written = combine_two(*({"mass_kg": legs[leg][b]["mass_kg"], "com_m": np.array(legs[leg][b]["com_m"]),
                                 "inertia_kg_m2": np.array(legs[leg][b]["inertia_kg_m2"])} for b in ("pad_body", "rod_body")))
        moving_written = legs[leg]["moving_part"]
        split_check = checks["legs"][leg]["split"]
        split_check["written_sum_mass_rel"] = abs(written["mass_kg"] - moving_written["mass_kg"]) / moving_written["mass_kg"]
        split_check["written_sum_com_max_abs_m"] = float(np.max(np.abs(written["com_m"]
                                                                       - np.array(moving_written["com_retracted_m"]))))
        split_check["written_sum_inertia_rel_to_max"] = relative_difference(written["inertia_kg_m2"],
                                                                            moving_written["inertia_kg_m2"])
        comments[f"legs.{leg}.pad.bottom_area_m2"] = (
            f"BREP cad/legs/{ROD_PAD_BREP[leg]} lowest -Y_cad plane; docs/cad_review.md gives 0.1071")

    # ---------------- totals ----------------
    total = mass_properties_si(combine_mass_properties(table, TOOL_STEEL))
    super_cad_pose = mass_properties_si(combine_mass_properties(table[is_superstructure], TOOL_STEEL))
    total_a = summary["mass_properties"]["step"]["total_assembly"]["mass_kg"]
    tool_delta = float(table.loc[table["motion"] == "moving_tool", "mass_tool_steel_kg"].sum()
                       - table.loc[table["motion"] == "moving_tool", "mass_step_kg"].sum())
    checks["totals"] = {
        "superstructure_plus_4_rods_minus_total_rel": abs(super_cad_pose["mass_kg"] + sum(leg_masses)
                                                         - total["mass_kg"]) / total["mass_kg"],
        "moving_plus_fixed_minus_superstructure_rel": abs(moving["mass_kg"] + fixed["mass_kg"]
                                                         - super_cad_pose["mass_kg"]) / super_cad_pose["mass_kg"],
        "total_case_c_kg": total["mass_kg"],
        "total_case_a_kg_cad_summary": total_a,
        "tool_steel_minus_step_kg": tool_delta,
        "total_c_minus_a_minus_tool_delta_kg": total["mass_kg"] - total_a - tool_delta,
        "level_masses_equal": len({levels[n]["mass_kg"] for n in LEVEL_NAMES}) == 1,
    }

    # ---------------- dynamics (docs/dynamics_model.md section 10) ----------------
    reference = json.loads(REFERENCE_JSON.read_text(encoding="utf-8"))
    l1_top = reference["chrono_test_references"]["L1_rigid_motor_lumped_contact"]["levels"]["top"]
    l1_first_mode = (float(l1_top["f_damped_Hz"][0]), float(l1_top["zeta"][0]))  # 1st rocking mode, L1, top
    crawler_bottom_z = sig(summary["geometric_low_part_check"]["ground_y_cad_mm"] * MM)
    derived = dynamics_derivation(
        pad_z=np.array([legs[leg]["pad_bottom_center_retracted_m"][2] for leg in LEG_ORDER]),
        attach_z=np.array([legs[leg]["attachment_point_m"][2] for leg in LEG_ORDER]),
        barrel_bottom_z=np.array([legs[leg]["barrel_z_range_m"][0] for leg in LEG_ORDER]),
        crawler_bottom_z=crawler_bottom_z,
        rod_mass=np.array([legs[leg]["moving_part"]["mass_kg"] for leg in LEG_ORDER]),
        superstructure_mass_top=levels["top"]["mass_kg"],
        l1_first_mode=l1_first_mode,
    )
    f_min_cylinder = F_MIN_FRACTION * levels["top"]["mass_kg"] * GRAVITY_M_S2 / 4

    def per_leg(values, digits=SIGNIFICANT_DIGITS):
        return {leg: sig(v, digits) for leg, v in zip(LEG_ORDER, np.broadcast_to(values, (4,)))}

    checks["dynamics"] = dynamics_checks(derived, reference, {"L1": derived["dt_l1"], "L2": derived["dt_l2"],
                                                              "L2b_NSC": derived["dt_l2b"]}, f_min_cylinder)
    checks["dynamics"]["reference_json_assumptions_beta_Pa"] = reference["meta"]["assumptions"]["oil_bulk_modulus_eff_Pa"]
    checks["dynamics"]["l1_dt_rule"] = {"f1_Hz": derived["f1_l1"], "zeta1": derived["zeta1_l1"],
                                        "dt_max_s": derived["dt_l1_max"], "dt_s": derived["dt_l1"]}
    checks["dynamics"]["l2_dt_rule"] = {"f_rod_local_Hz": derived["f_rod_local"], "dt_max_s": derived["dt_l2_max"],
                                        "dt_s": derived["dt_l2"]}
    checks["dynamics"]["l2b_nsc_dt_rule"] = {"f_rod_on_axial_spring_Hz": derived["f_rod_axial_l2b"],
                                             "dt_max_s": derived["dt_l2b_max"], "dt_s": derived["dt_l2b"]}

    # ---------------- document ----------------
    pad_lowest_z = min(legs[leg]["pad_bottom_center_retracted_m"][2] for leg in LEG_ORDER)
    data = {
        "meta": {
            "name": "REXOME33 outrigger levelling - shared simulation parameters",
            "generator": "scripts/cad/export_params.py",
            "generated": datetime.date.today().isoformat(),
            "sources": {
                "step": STEP_PATH.name,
                "parts": "cad/parts_classified.csv",
                "summary": "cad/cad_summary.json",
                "auger_levels": "cad/auger_levels.json",
                "leg_brep": "cad/legs/*_10_1.brep",
                "checks": "params/rexome33_checks.json",
                "dynamics": DYNAMICS_DOC,
                "dynamics_formulas": f"{DYN_MODEL_PY}, {RUN_REFERENCE_PY}",
                "dynamics_reference": "analysis/dynamics/reference.json",
            },
            "dynamics_stages": {
                "common": ("needed from L1 on: legs.*.pad.{joint, swivel_center_above_pad_bottom_m, "
                           "swivel_tilt_range_deg}, actuator.{model_default, bore/rod/barrel diameters, oil_*, "
                           "frame_stiffness_N_m, cylinder_type, annulus_area_m2, rod_side_chamber_model, "
                           "relief_pressure_moving_Pa, max_force_extend_N, max_force_retract_N, "
                           "locked_pressure_limit_Pa, lock_valve, pump_flow_m3_s, flow_control}, control.*, "
                           "sensors.*, contact.rigid_floor.{model, geometry, friction, ground_body_mass_kg, "
                           "damping_input_convention, concrete}, contact.crawler.*, simulation.crawler_clearance_m"),
                "L1": "L1 default (controller development): contact.rigid_floor.L1.*, simulation.L1.*",
                "L2b": ("L2b-NSC, operating plan B re-assessment (large slope, seal friction, SCM): "
                        "contact.rigid_floor.L2b_NSC.*, actuator.L2b_NSC.*, simulation.L2b_NSC.*"),
                "L2": ("when switching to L2 after the hydraulic spec is known (rigid-guide L2 and SMC-L2b keys, kept "
                       "per docs/dynamics_model.md 10; operating plan B uses L2b instead): contact.rigid_floor.L2.*, "
                       "actuator.L2.*, simulation.L2.*"),
                "SCM": "soft soil (separate pad body): legs.*.pad_body.*, legs.*.rod_body.*",
            },
            "mass_basis": {
                "case": "C",
                "status": "provisional",
                "description": "STEP densities; the 5 AUGER TOOL rows as steel 7.85 g/cm^3 (CLAUDE.md 2026-10-19)",
            },
            "frame": {
                "axes": "x forward (mast / FRONT JACK CYL side), y left, z up; right-handed",
                "origin": "CAD origin (body origin undecided)",
                "units": "SI (m, kg, s, rad, N)",
                "cad_length_unit": "mm",
                "cad_axes": {"x": "+Z_cad", "y": "+X_cad", "z": "+Y_cad"},
                "rotation_body_from_cad": CAD_TO_BODY.tolist(),
            },
            "inertia_convention": "about the centre of mass, body axes, tensor form (off-diagonal = -integral(x*y dm))",
            "gravity_m_s2": GRAVITY_M_S2,
            "leg_order": list(LEG_ORDER),
        },
        "ground": {
            "crawler_bottom_z_m": sig(summary["geometric_low_part_check"]["ground_y_cad_mm"] * MM),
            "lowest_pad_bottom_z_m": pad_lowest_z,
        },
        "superstructure": {
            "definition": "whole assembly incl. crawler and leg barrels, minus the 4 leg moving parts (rod+piston+pad)",
            "default_auger_level": DEFAULT_AUGER_LEVEL,
            "auger_level_order": list(LEVEL_NAMES),
            "auger_levels": levels,
            "auger_moving_set_at_cad_pose": {
                "description": "DRIVE AUGER ASSY + AUGER TOOL (378 rows) at travel 0; translates along +z",
                "mass_kg": sig(moving["mass_kg"]),
                "com_m": vec(moving["com_m"]),
                "inertia_kg_m2": mat(moving["inertia_kg_m2"]),
                "travel_range_m": vec([auger["range"]["lower_travel_mm"] * MM, auger["range"]["upper_travel_mm"] * MM]),
            },
            "fixed_part": {
                "description": "superstructure minus the auger moving set",
                "mass_kg": sig(fixed["mass_kg"]),
                "com_m": vec(fixed["com_m"]),
                "inertia_kg_m2": mat(fixed["inertia_kg_m2"]),
            },
        },
        "actuator": {
            "type": "hydraulic cylinder approximated by ChLinkMotorLinear (simplified)",
            "stroke_m": STROKE_M,
            "full_stroke_time_s": FULL_STROKE_TIME_S,
            "max_speed_m_s": sig(MAX_SPEED_M_S),
            "extension_direction": [0.0, 0.0, -1.0],
            "model_default": ACTUATOR_MODEL_DEFAULT,
            "bore_diameter_m": BORE_DIAMETER_M,
            "rod_diameter_m": ROD_DIAMETER_M,
            "barrel_outer_diameter_m": BARREL_OUTER_DIAMETER_M,
            "oil_bulk_modulus_eff_Pa": OIL_BULK_MODULUS_EFF_PA,
            "oil_bulk_modulus_sensitivity_range_Pa": list(OIL_BULK_MODULUS_SENSITIVITY_PA),
            "oil_dead_length_m": OIL_DEAD_LENGTH_M,
            "frame_stiffness_N_m": FRAME_STIFFNESS_N_M,
            "cylinder_type": CYLINDER_TYPE,
            "annulus_area_m2": sig(derived["annulus_area"]),
            "rod_side_chamber_model": ROD_SIDE_CHAMBER_MODEL,
            "relief_pressure_moving_Pa": RELIEF_PRESSURE_MOVING_PA,
            "max_force_extend_N": sig(derived["max_force_extend"]),
            "max_force_retract_N": sig(derived["max_force_retract"]),
            "locked_pressure_limit_Pa": LOCKED_PRESSURE_LIMIT_PA,
            "lock_valve": LOCK_VALVE,
            "pump_flow_m3_s": sig(derived["pump_flow_m3_s"]),
            "flow_control": FLOW_CONTROL,
            "L2b_NSC": {
                "axial_stiffness": {
                    "formula": L2B_NSC_AXIAL_STIFFNESS_FORMULA,
                    "operating_point_N_m": per_leg(derived["k_axial_l2b"]),
                },
                "oil_damping_N_s_m": per_leg(derived["c_oil"]),
                "lateral_bushing_N_m": per_leg(derived["bushing_l2b"]),
                "lateral_bushing_damping_input_N_s_m": per_leg(derived["bushing_input_l2b"]),
            },
            "L2": {
                "oil_damping_N_s_m": per_leg(derived["c_oil"]),
                "lateral_bushing_N_m": per_leg(derived["kh_free"]),
                "lateral_bushing_damping_N_s_m": per_leg(derived["c_bushing_l2b"]),
            },
        },
        "legs": legs,
        "contact": {
            "rigid_floor": {
                "model": RIGID_FLOOR_MODEL,
                "geometry": ("1 sphere per pad, radius = swivel_center_above_pad_bottom_m, centred at the swivel "
                             "centre, on the rod body"),
                "friction": RIGID_FLOOR_FRICTION,
                "ground_body_mass_kg": GROUND_BODY_MASS_KG,
                "damping_input_convention": DAMPING_INPUT_CONVENTION,
                "concrete": {
                    "k_N_m": sig(derived["kc"]),
                    "E_Pa": CONCRETE_E_PA,
                    "nu": CONCRETE_NU,
                    "slab_thickness_m": SLAB_THICKNESS_M,
                    "subgrade_modulus_N_m3": SUBGRADE_MODULUS_N_M3,
                },
                "L1": {
                    "kn_per_pad_N_m": per_leg(derived["kn_l1"]),
                    "kt_per_pad_N_m": per_leg(derived["kt_l1"]),
                    "cn_per_pad_N_s_m": per_leg(derived["cn_l1"]),
                    "ct_per_pad_N_s_m": per_leg(derived["ct_l1"]),
                    "gn_per_pad_1_s": per_leg(derived["gn_l1"]),
                    "smc_material": L1_SMC_MATERIAL,
                    "tangential_model": L1_TANGENTIAL_MODEL,
                    "bushing_stiffness_per_pad_N_m": per_leg(derived["kt_l1"]),
                    "bushing_damping_input_per_pad_N_s_m": per_leg(derived["bushing_input_l1"]),
                    "slip_damping_reenable_speed_m_s": SLIP_DAMPING_REENABLE_SPEED_M_S,
                    "derivation": {
                        "operating_extension_m": per_leg(derived["e_op"]),
                        "k_oil_N_m": per_leg(derived["ko"]),
                        "k_rod_N_m": sig(derived["kr"]),
                        "k_axial_leg_N_m": per_leg(derived["ko_eff"]),
                        "k_lateral_leg_swivel_N_m": per_leg(derived["kh_free"]),
                        "steel_E_Pa": STEEL_E_PA,
                        "rod_length_for_k_rod_m": ROD_LENGTH_FOR_K_ROD_M,
                        "damping_ratio": BODY_DAMPING_RATIO,
                        "damping_mass_kg": sig(derived["m_tot"]),
                    },
                },
                "L2b_NSC": {
                    "solver": L2B_NSC_SOLVER,
                    "solver_max_iterations": L2B_NSC_SOLVER_MAX_ITERATIONS,
                    "friction": L2B_NSC_FRICTION,
                },
                "L2": {
                    "kn_per_pad_N_m": per_leg(derived["kc"]),
                    "kt_per_pad_N_m": per_leg(derived["kc"]),
                    "cn_per_pad_N_s_m": per_leg(derived["c_contact_l2"]),
                    "ct_per_pad_N_s_m": per_leg(derived["ct_l2"]),
                },
            },
            "crawler": {
                "kn_total_N_m": CRAWLER_KN_TOTAL_N_M,
                "friction": CRAWLER_FRICTION,
            },
        },
        "control": {
            "F_min_fraction_of_mean_leg_load": F_MIN_FRACTION,
            "F_min_cylinder_N": sig(f_min_cylinder),
            "F_min_basis": ("cylinder force (pressure x bore area) = superstructure weight share; "
                            "pad contact force = cylinder force + rod weight"),
        },
        "sensors": {
            "cylinder_pressure": {
                "location": PRESSURE_SENSOR_LOCATION,
            },
        },
        "simulation": {
            "crawler_clearance_m": CRAWLER_CLEARANCE_M,
            "L1": {"dt_s": derived["dt_l1"]},
            "L2b_NSC": {"dt_s": derived["dt_l2b"]},
            "L2": {"dt_s": derived["dt_l2"]},
        },
    }

    comments.update({
        "meta.mass_basis": "CLAUDE.md '기준 질량' (case C); replace when the operating weight is known",
        "meta.frame": "CLAUDE.md '좌표계와 명명'",
        "meta.gravity_m_s2": "standard gravity used for the static leg loads; set it explicitly in every engine",
        "ground.crawler_bottom_z_m": "cad_summary.json geometric_low_part_check.ground_y_cad_mm (crawler bottom, CAD pose)",
        "ground.lowest_pad_bottom_z_m": "min of legs.*.pad_bottom_center_retracted_m z (all legs fully retracted)",
        "superstructure.definition": "docs/cad_review.md 3.2",
        "superstructure.default_auger_level": ("CLAUDE.md '오거 위치' (2026-10-19): default run level is top "
                                               "(highest CoM, hardest case); controller checks use all three levels"),
        "superstructure.auger_levels": ("auger_levels.json levels.<name>.mass.tool_steel, recomputed at full precision "
                                        "(combine_mass_properties, case tool_steel)"),
        "superstructure.auger_moving_set_at_cad_pose": "auger_parts.csv motion moving_drive + moving_tool, case C",
        "superstructure.auger_moving_set_at_cad_pose.travel_range_m": "auger_levels.json range lower/upper_travel_mm",
        "superstructure.fixed_part": "check: fixed_part + moving set at a travel = auger_levels entry",
        "actuator": "CLAUDE.md '구동기' (680 mm, 0 -> full stroke in 30 s)",
        "actuator.stroke_m": "CLAUDE.md; CAD estimate bore 700 - piston 20 (cad_summary.json legs.*.stroke_estimate_mm)",
        "actuator.max_speed_m_s": "stroke_m / full_stroke_time_s",
        "actuator.extension_direction": "body frame: extending pushes the pad down (-z)",
        # ---- dynamics keys, docs/dynamics_model.md section 10 ----
        "meta.dynamics_stages": ("docs/dynamics_model.md 10 (rev. 4): stage in which each dynamics key is needed "
                                 "(common / L1 / L2b / L2 / SCM); operating plan B (CLAUDE.md): L1 for the "
                                 "controller, L2b = L2b-NSC for re-assessment"),
        "actuator.model_default": "[common] user decision 2026-10-19 (CLAUDE.md '구동기 모델'): L1 temporary default",
        "actuator.bore_diameter_m": "[common] CAD, docs/cad_review.md 3.1",
        "actuator.rod_diameter_m": "[common] CAD, docs/cad_review.md 3.1",
        "actuator.barrel_outer_diameter_m": "[common] CAD, docs/cad_review.md 3.1",
        "actuator.oil_bulk_modulus_eff_Pa": ("[common, L2b, L2] ASSUMPTION: 사용자 결정 (CLAUDE.md, 2026-10-19); "
                                             "drives the L1 stiffness and the L2b k_oil(s)"),
        "actuator.oil_bulk_modulus_sensitivity_range_Pa": ("[common] ASSUMPTION: 사용자 결정 (CLAUDE.md), "
                                                           "docs/dynamics_model.md 2.4; = dyn_model.py ASSUMPTIONS "
                                                           "oil_bulk_modulus_range_Pa (checked)"),
        "actuator.oil_dead_length_m": ("[common, L2b, L2] ASSUMPTION: port/pipe volume as column length, "
                                       "docs/dynamics_model.md 2.3 (lock valve on the cylinder supports a small value)"),
        "actuator.frame_stiffness_N_m": "[common, L2b, L2] ASSUMPTION: bracket / outrigger box, docs/dynamics_model.md 2.3",
        # ---- rev. 4: hydraulic circuit (docs/hydraulic_circuit.md, docs/dynamics_model.md 2.3 / 4.4) ----
        "actuator.cylinder_type": "[common] circuit drawing, docs/hydraulic_circuit.md",
        "actuator.annulus_area_m2": ("[common] derived from CAD bore / rod: pi/4 (bore^2 - rod^2); "
                                     "head area = pi/4 bore^2 = 0.0103869 m^2 (run_reference.py:411-426)"),
        "actuator.rod_side_chamber_model": "[common] ASSUMPTION: docs/dynamics_model.md 2.3 (sensitivity only)",
        "actuator.relief_pressure_moving_Pa": ("[common] circuit drawing: MCV relief 210 bar, reached only at the stroke "
                                               "ends (CLAUDE.md '압력 한계')"),
        "actuator.max_force_extend_N": ("[common] derived: relief_pressure_moving_Pa x head area; force saturation while "
                                        "moving (extend), docs/dynamics_model.md 4.4 / V11b"),
        "actuator.max_force_retract_N": ("[common] derived: relief_pressure_moving_Pa x annulus_area_m2; force saturation "
                                         "while moving (retract pull)"),
        "actuator.locked_pressure_limit_Pa": ("[common] manufacturer: cylinder maximum load test pressure 350 bar (locked, "
                                              "judgement metric V17); force = 350 bar x head area = "
                                              f"{derived['locked_force_limit']:.0f} N"),
        "actuator.lock_valve": ("[common] manufacturer: current dual pilot-operated check; option \"counterbalance\" "
                                "(relieves like a 350 bar relief, L2b model in docs/dynamics_model.md 4.4)"),
        "actuator.pump_flow_m3_s": ("[common] circuit drawing: 60.2 L/min; 4 legs at max_speed_m_s need 56.5 L/min "
                                    "(checked)"),
        "actuator.flow_control": ("[common] ASSUMPTION (확인 필요): circuit drawing read as proportional + section pressure "
                                  "compensation; basis of the L1 speed-limited motor"),
        "actuator.L2b_NSC": ("[L2b] ChLinkMotorLinearForce F = k_ax(s)(s_ref - s) + c_oil(ds_ref - ds), "
                             "s_ref <- clip(s_ref + sat(u) dt, 0, stroke), docs/dynamics_model.md 2.3 / 4.4; on SCM drop "
                             "k_concrete from k_ax (series(k_oil(s), k_rod, k_frame)); lateral bushing with the drive "
                             "guide freed in x, y"),
        "actuator.L2b_NSC.axial_stiffness": ("ASSUMPTION (derived): k_oil(s) = oil_bulk_modulus_eff_Pa pi/4 bore^2 / "
                                             "(oil_dead_length_m + s); operating point = contact.rigid_floor.L1.kn_per_pad_N_m "
                                             "(run_reference.py:334-335)"),
        "actuator.L2b_NSC.oil_damping_N_s_m": "ASSUMPTION (derived): = actuator.L2.oil_damping_N_s_m (heave zeta 0.05)",
        "actuator.L2b_NSC.lateral_bushing_N_m": ("ASSUMPTION (derived): = contact.rigid_floor.L1.kt_per_pad_N_m "
                                                 "(swivel leg bending in series with the concrete tangential k)"),
        "actuator.L2b_NSC.lateral_bushing_damping_input_N_s_m": (
            "ASSUMPTION (derived): Chrono input = actual / 2 (contact.rigid_floor.damping_input_convention); actual = "
            "2 zeta sqrt(k_bushing m/4), zeta 0.05 (run_reference.py:395)"),
        "actuator.L2": ("[L2] ChLinkMotorLinearForce F = k_oil(s)(s_ref - s) + c_oil(ds_ref - ds), "
                        "docs/dynamics_model.md 4.4; k_oil(s) = oil_bulk_modulus_eff_Pa * pi/4 bore^2 / (oil_dead_length_m + s)"),
        "actuator.L2.oil_damping_N_s_m": ("ASSUMPTION (derived): 2 zeta sqrt(k_axial_leg m/4), zeta 0.05, "
                                          "run_reference.py:315"),
        "actuator.L2.lateral_bushing_N_m": ("ASSUMPTION (derived): SMC-L2b option (bushing without the concrete), swivel "
                                            "leg fixed-free beam, per-leg geometry, load at the swivel centre = "
                                            "contact.rigid_floor.L1.derivation.k_lateral_leg_swivel_N_m, "
                                            "dyn_model.py:203-240; L2b-NSC uses actuator.L2b_NSC.lateral_bushing_N_m"),
        "actuator.L2.lateral_bushing_damping_N_s_m": ("ASSUMPTION (derived): SMC-L2b lateral zeta 0.05, ACTUAL value (Chrono "
                                                      "input = half): 2 zeta sqrt(series(bushing, concrete k) m/4), "
                                                      "run_reference.py:370 and run_reference.py:395"),
        "contact": "docs/dynamics_model.md 4.1 / 4.2 (all contact parameters are assumptions)",
        "contact.rigid_floor.model": ("[common] recommendation, docs/dynamics_model.md 4.1 (rev. 4), "
                                      "docs/chrono_stick_friction_test.md"),
        "contact.rigid_floor.geometry": "[common] recommendation, docs/dynamics_model.md 2.1 / 4.2",
        "contact.rigid_floor.friction": ("[common] ASSUMPTION: steel-concrete 0.4 ... 0.6, docs/dynamics_model.md 4.2; "
                                         "L1: mu of the Python Coulomb return mapping (SMC material mu = 0)"),
        "contact.rigid_floor.ground_body_mass_kg": ("[common] implementation convention (not physical): fixed floor body "
                                                    "mass with SetFixed(True); ChBody default 1 kg kills the SMC damping "
                                                    "(docs/dynamics_model.md 4.1, stick friction test 2.2)"),
        "contact.rigid_floor.damping_input_convention": "[common] measured convention, stick friction test 2.2 / 2.3",
        "contact.rigid_floor.concrete": ("[common, L2b, L2] ASSUMPTION: slab on grade, Westergaard k = 8 k_s l^2, "
                                         "l = (D/k_s)^(1/4), D = E h^3 / (12 (1 - nu^2)); dyn_model.py:187-200"),
        "contact.rigid_floor.L1": ("[L1] ASSUMPTION (derived at the operating extension, beta_eff 1.0 GPa): "
                                   "kn = series(k_oil, k_rod, k_frame, k_concrete), kt = series(k_lateral_leg_swivel, "
                                   "k_concrete), c = 2 zeta sqrt(k m/4) (actual values); run_reference.py:313-326, "
                                   "dyn_model.py series/k_oil/k_rod/k_leg_lateral_legs (per-leg geometry, load at the "
                                   "swivel centre); kt / ct act through the ground-fixed bushing, not the SMC material; "
                                   "rerun when an assumption changes"),
        "contact.rigid_floor.L1.gn_per_pad_1_s": ("ASSUMPTION (derived): SMC Hooke gn = cn_per_pad_N_s_m / "
                                                  "legs.<leg>.moving_part.mass_kg (contact pair = moving part + 1e9 kg "
                                                  "floor, m_eff relative difference ~1e-7, checked)"),
        "contact.rigid_floor.L1.smc_material": "recommendation, docs/dynamics_model.md 4.1",
        "contact.rigid_floor.L1.tangential_model": ("recommendation, docs/dynamics_model.md 4.1 (built-in "
                                                    "ChLoadBodyBodyBushingPlastic is not used)"),
        "contact.rigid_floor.L1.bushing_stiffness_per_pad_N_m": "ASSUMPTION (derived): = kt_per_pad_N_m",
        "contact.rigid_floor.L1.bushing_damping_input_per_pad_N_s_m": ("ASSUMPTION (derived): Chrono input = "
                                                                       "ct_per_pad_N_s_m / 2 (bushing damping acts at 2x)"),
        "contact.rigid_floor.L1.slip_damping_reenable_speed_m_s": ("ASSUMPTION: bushing damping is switched back on below "
                                                                   "this slip speed (stick friction test section 5)"),
        "contact.rigid_floor.L1.derivation": ("intermediate values; operating extension = pad bottom - "
                                              "ground.crawler_bottom_z_m + simulation.crawler_clearance_m "
                                              "(run_reference.py:75-76); damping_mass_kg = superstructure top + 4 moving parts"),
        "contact.rigid_floor.L2b_NSC": ("[L2b] ChSystemNSC rigid contact (stick exact), docs/dynamics_model.md 4.1 / 4.2; "
                                        "solver: GetSolver().AsIterative().SetMaxIterations(solver_max_iterations); "
                                        "friction ASSUMPTION; no contact compliance or damping (in actuator.L2b_NSC)"),
        "contact.rigid_floor.L2": ("[L2] ASSUMPTION: kn = kt = concrete k; cn = 2 * 0.30 * sqrt((k_axial_leg + k_concrete) "
                                   "m_rod_mean) - actuator.L2.oil_damping (total rod local mode zeta 0.30, "
                                   "run_reference.py:316-319); ct = 2 * 0.05 * sqrt(k_concrete m/4), not used in L2b "
                                   "(bushing damping instead)"),
        "contact.crawler": "[common] ASSUMPTION: crawler-floor contact before lift-off, docs/dynamics_model.md 4.2",
        "control": "[common] CLAUDE.md 'F_min' (user decision 2026-10-19), docs/dynamics_model.md 3.2 / 6",
        "control.F_min_fraction_of_mean_leg_load": "user decision 2026-10-19",
        "control.F_min_cylinder_N": ("derived: fraction * superstructure mass * g / 4 (cylinder force basis; "
                                     "pad contact force basis adds the rod weight, about 10.50 kN)"),
        "simulation.crawler_clearance_m": "[common] ASSUMPTION: crawler lifted 50 mm in the levelled state, docs/dynamics_model.md 1.3",
        "simulation.L1": ("[L1] ASSUMPTION (rule, confirm by V9): dt = largest of 1e-3, 5e-4, 2e-4, ... with "
                          "omega1 dt / 2 <= 0.1 zeta1 (1st rocking mode, L1, top, analysis/dynamics/reference.json), "
                          "docs/dynamics_model.md 4.3"),
        "simulation.L2b_NSC": ("[L2b] ASSUMPTION (rule, confirm by V9): dt <= T / 50 of the rod on the axial spring alone "
                               "(contact open) sqrt(mean k_ax / m_rod) / 2 pi, run_reference.py:404-405; PSOR 50 at "
                               "2e-4 s held a 2 deg slope (stick friction test), docs/dynamics_model.md 4.3"),
        "simulation.L2": ("[L2] ASSUMPTION (rule): dt <= T / 50 of the rod local mode sqrt((k_axial_leg + k_concrete) "
                          "/ m_rod) / 2 pi, run_reference.py:289-297, docs/dynamics_model.md 4.3"),
        "sensors": "[common] CLAUDE.md '센서' / '압력 센서' (2026-10-19), docs/hydraulic_circuit.md",
        "sensors.cylinder_pressure.location": "manufacturer description; head-side reading, rod-side pressure 0 assumed",
        "legs": ("cad_summary.json legs.<leg> (axis_cad_mm, pad_bottom_y_cad_mm, bracket_bolt_holes_y_cad_mm, ...); "
                 "CLAUDE.md '다리 기하': every leg extends 0 ... 0.680 m from the retracted state, "
                 "retracted = CAD pose + retracted_offset_from_cad_m along +z"),
    })
    for name in LEVEL_NAMES:
        comments[f"superstructure.auger_levels.{name}.auger_travel_m"] = (
            f"auger_levels.json levels.{name}.travel_mm (drive + tool along +z from the CAD pose)")
        comments[f"superstructure.auger_levels.{name}.static_leg_loads_N"] = (
            "derived, ASSUMPTION: rigid body on 4 equal vertical springs, rigid level floor, pads at "
            "pad_bottom_center_retracted_m")
        comments[f"superstructure.auger_levels.{name}.inertia_kg_m2"] = "about com_m, body axes"
    for leg in LEG_ORDER:
        comments[f"legs.{leg}.cylinder_axis_xy_m"] = f"cad_summary.json legs.{leg}.axis_cad_mm (X, Z) -> (y, x)"
        comments[f"legs.{leg}.attachment_point_m"] = ("on the axis at the middle of the bracket bolt-hole range "
                                                      "(convention; the barrel is rigid with the superstructure)")
        comments[f"legs.{leg}.bracket_bolt_hole_z_range_m"] = f"cad_summary.json legs.{leg}.bracket_bolt_holes_y_cad_mm"
        comments[f"legs.{leg}.barrel_z_range_m"] = f"cad_summary.json legs.{leg}.barrel_y_cad_mm"
        comments[f"legs.{leg}.bore_z_range_m"] = f"cad_summary.json legs.{leg}.bore_y_cad_mm"
        comments[f"legs.{leg}.retracted_offset_from_cad_m"] = (
            f"CLAUDE.md '다리 기하': stroke_m - cad_summary.json legs.{leg}.remaining_extension_mm "
            "(= bore top - piston top); the CAD pose is extension = this value")
        comments[f"legs.{leg}.extension_range_m"] = "CLAUDE.md '다리 기하' / '구동기': 0 = fully retracted"
        comments[f"legs.{leg}.pad_bottom_center_retracted_m"] = (
            f"cad_summary.json legs.{leg}.pad_center_body_m (bottom face) + retracted_offset_from_cad_m in z")
        comments[f"legs.{leg}.pad.polygon_xy_m"] = ("outer wire vertices of the pad bottom face relative to "
                                                    "pad_bottom_center_retracted_m (x, y), counter-clockwise from +z; "
                                                    "CAD shape and orientation (CLAUDE.md '다리 기하')")
        comments[f"legs.{leg}.pad.thickness_m"] = (f"BREP cad/legs/{ROD_PAD_BREP[leg]}: bottom face to the pad top "
                                                   "face (+Y_cad plane), incl. the 45 deg top-edge chamfer")
        comments[f"legs.{leg}.pad.side_height_m"] = ("BREP: height of the 8 vertical side faces; "
                                                     "docs/cad_review.md 3.1 '두께 20 mm' is this value")
        comments[f"legs.{leg}.moving_part"] = (f"rod + piston + pad (solid 10, SS400 7.85), parts_classified.csv "
                                               f"group leg_rod_pad leg {leg}; retracted state (CAD + offset in z)")
        comments[f"legs.{leg}.moving_part.inertia_kg_m2"] = "about com_retracted_m, body axes"
        comments[f"legs.{leg}.pad.joint"] = "[common] user decision 2026-10-19 (CLAUDE.md '다리 기하'): swivel pad"
        comments[f"legs.{leg}.pad.swivel_center_above_pad_bottom_m"] = (
            "[common] ASSUMPTION: ball centre height (CAD has no swivel), docs/dynamics_model.md 2.1")
        comments[f"legs.{leg}.pad.swivel_tilt_range_deg"] = "[common] ASSUMPTION: free tilt about the ball, docs/dynamics_model.md 2.2"
        comments[f"legs.{leg}.pad_body"] = (
            f"[SCM] pad plate (part of BREP cad/legs/{ROD_PAD_BREP[leg]} below pad bottom + split_plane_above_pad_bottom_m) "
            "+ the 4 gussets on its top face (docs/dynamics_model.md 2.6); boolean split, SS400 7.85; retracted state; "
            "com_m / inertia about com_m in body axes")
        comments[f"legs.{leg}.rod_body"] = (
            "[SCM] rod + piston + boss = largest solid above the split plane (incl. the rod 25 ... 60 mm above the pad bottom); "
            "pad_body + rod_body = moving_part (parallel-axis check in rexome33_checks.json); retracted state; "
            "the swivel centre (pad bottom + swivel_center_above_pad_bottom_m) is an ASSUMPTION")

    header = [
        "# REXOME33 shared simulation parameters (Chrono and MuJoCo read this file).",
        "# GENERATED by scripts/cad/export_params.py - do not edit by hand; rerun the script.",
        "# Mass basis: case C (provisional). Frame: x forward, y left, z up, origin = CAD origin, SI units.",
        "# Values are CAD-model values; assumptions are marked ASSUMPTION in the comments.",
        "",
    ]
    text = "\n".join(header + emit(data, comments)) + "\n"

    # Round trip (in memory, before writing): the YAML text must load back to exactly the same data.
    loaded = yaml.safe_load(text)
    checks["yaml_round_trip_equal"] = loaded == json.loads(json.dumps(data))
    for name in LEVEL_NAMES:  # moving set shifted + fixed part == level
        travel = levels[name]["auger_travel_m"]
        m_total = moving["mass_kg"] + fixed["mass_kg"]
        com = (moving["mass_kg"] * (moving["com_m"] + [0, 0, travel]) + fixed["mass_kg"] * fixed["com_m"]) / m_total
        checks["levels"][name]["two_body_com_max_abs_m"] = float(np.max(np.abs(com - levels[name]["com_m"])))

    failures = evaluate_checks(checks)
    checks["thresholds"] = {
        "REL_TOL": REL_TOL, "ABS_COM_TOL_M": ABS_COM_TOL_M, "JSON_MASS_TOL_KG": JSON_MASS_TOL_KG,
        "JSON_COM_TOL_M": JSON_COM_TOL_M, "JSON_INERTIA_REL_TOL": JSON_INERTIA_REL_TOL,
        "JSON_LOAD_TOL_KN": JSON_LOAD_TOL_KN, "CAD_SUMMARY_TOL_MM": CAD_SUMMARY_TOL_MM,
        "PAD_THICKNESS_TOL_MM": PAD_THICKNESS_TOL_MM,
        "DOC10_PRINTED": "half a unit of the last printed digit (docs/dynamics_model.md 10)",
        "REFERENCE_JSON": "REL_TOL after rounding the generated value to 6 significant digits (run_reference.py r())",
    }
    checks["failures"] = failures
    checks["passed"] = not failures
    PARAMS_DIR.mkdir(exist_ok=True)
    with CHECKS_JSON.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(checks, ensure_ascii=False, indent=1, default=float) + "\n")
    print(json.dumps(checks, ensure_ascii=False, indent=1, default=float))
    if failures:
        print(f"FAILED {len(failures)} check(s); {PARAMS_YAML} was NOT written", file=sys.stderr)
        sys.exit(1)
    with PARAMS_YAML.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print(f"wrote {PARAMS_YAML}")


def evaluate_checks(checks: dict) -> list[str]:
    """Apply the acceptance thresholds; returns a list of failure messages (empty = all passed)."""
    failures = []

    def require(condition, label, value):
        if not bool(condition):
            failures.append(f"{label} = {value}")

    def require_tensor(prefix, tensor):
        for key, ok in tensor.items():
            require(ok, f"{prefix}.tensor.{key}", ok)

    for name, c in checks["levels"].items():
        p = f"levels.{name}"
        require(c["independent_mass_rel"] <= REL_TOL, f"{p}.independent_mass_rel", c["independent_mass_rel"])
        require(c["independent_com_max_abs_m"] <= ABS_COM_TOL_M, f"{p}.independent_com_max_abs_m",
                c["independent_com_max_abs_m"])
        require(c["independent_inertia_rel_to_max"] <= REL_TOL, f"{p}.independent_inertia_rel_to_max",
                c["independent_inertia_rel_to_max"])
        require(c["auger_json_mass_abs_kg"] <= JSON_MASS_TOL_KG, f"{p}.auger_json_mass_abs_kg",
                c["auger_json_mass_abs_kg"])
        require(c["auger_json_com_max_abs_m"] <= JSON_COM_TOL_M, f"{p}.auger_json_com_max_abs_m",
                c["auger_json_com_max_abs_m"])
        require(c["auger_json_inertia_rel_to_max"] <= JSON_INERTIA_REL_TOL, f"{p}.auger_json_inertia_rel_to_max",
                c["auger_json_inertia_rel_to_max"])
        require(c["auger_json_leg_loads_max_abs_kN"] <= JSON_LOAD_TOL_KN, f"{p}.auger_json_leg_loads_max_abs_kN",
                c["auger_json_leg_loads_max_abs_kN"])
        require(c["leg_load_sum_rel_to_weight"] <= REL_TOL, f"{p}.leg_load_sum_rel_to_weight",
                c["leg_load_sum_rel_to_weight"])
        require(c["two_body_com_max_abs_m"] <= ABS_COM_TOL_M, f"{p}.two_body_com_max_abs_m",
                c["two_body_com_max_abs_m"])
        require_tensor(p, c["tensor"])
    for leg, c in checks["legs"].items():
        p = f"legs.{leg}"
        require_tensor(p, c["tensor"])
        require(c["com_inside_part_bbox"], f"{p}.com_inside_part_bbox", c["com_inside_part_bbox"])
        require(c["pad_vertex_count"] == 8, f"{p}.pad_vertex_count", c["pad_vertex_count"])
        require(abs(c["pad_face_y_vs_summary_mm"]) <= CAD_SUMMARY_TOL_MM, f"{p}.pad_face_y_vs_summary_mm",
                c["pad_face_y_vs_summary_mm"])
        require(max(abs(v) for v in c["pad_face_centroid_minus_axis_xy_mm"]) <= CAD_SUMMARY_TOL_MM,
                f"{p}.pad_face_centroid_minus_axis_xy_mm", c["pad_face_centroid_minus_axis_xy_mm"])
        require(c["pad_area_brep_vs_polygon_rel"] <= REL_TOL, f"{p}.pad_area_brep_vs_polygon_rel",
                c["pad_area_brep_vs_polygon_rel"])
        require(c["rod_mass_vs_csv_rel"] <= REL_TOL, f"{p}.rod_mass_vs_csv_rel", c["rod_mass_vs_csv_rel"])
        require(0.0 <= c["retract_offset_mm"] <= 10.0, f"{p}.retract_offset_mm (expected 0 ... 10 mm)",
                c["retract_offset_mm"])
        require(abs(c["retract_offset_minus_piston_gap_mm"]) <= CAD_SUMMARY_TOL_MM,
                f"{p}.retract_offset_minus_piston_gap_mm", c["retract_offset_minus_piston_gap_mm"])
        require(abs(c["com_above_pad_bottom_cad_minus_retracted_m"]) <= ABS_COM_TOL_M,
                f"{p}.com_above_pad_bottom_cad_minus_retracted_m", c["com_above_pad_bottom_cad_minus_retracted_m"])
        require(c["pad_side_face_count"] == 8, f"{p}.pad_side_face_count", c["pad_side_face_count"])
        require(abs(c["pad_side_height_brep_minus_doc_mm"]) <= PAD_THICKNESS_TOL_MM,
                f"{p}.pad_side_height_brep_minus_doc_mm", c["pad_side_height_brep_minus_doc_mm"])
        require(c["pad_thickness_brep_mm"] >= c["pad_side_height_brep_mm"], f"{p}.pad_thickness_brep_mm",
                c["pad_thickness_brep_mm"])
        s = c["split"]
        q = f"{p}.split"
        require(abs(s["split_plane_minus_pad_thickness_mm"]) <= PAD_THICKNESS_TOL_MM,
                f"{q}.split_plane_minus_pad_thickness_mm", s["split_plane_minus_pad_thickness_mm"])
        for key in ("whole_valid", "pad_valid", "rod_valid", "pad_com_inside_bbox", "rod_com_inside_bbox",
                    "pad_com_below_split_plane", "rod_com_above_split_plane"):
            require(s[key], f"{q}.{key}", s[key])
        require(s["gusset_count"] == 4, f"{q}.gusset_count", s["gusset_count"])
        require(s["gussets_touch_split_plane"], f"{q}.gussets_touch_split_plane", s["gussets_touch_split_plane"])
        require(s["rod_piece_starts_at_split_plane"], f"{q}.rod_piece_starts_at_split_plane",
                s["rod_piece_starts_at_split_plane"])
        require(s["whole_solids"] == 1 and s["pad_solids"] == 1, f"{q}.whole/pad_solids",
                (s["whole_solids"], s["pad_solids"]))
        for key in ("volume_pad_plus_rod_minus_whole_rel", "brep_whole_vs_moving_part_mass_rel", "sum_mass_rel",
                    "sum_inertia_rel_to_max", "written_sum_mass_rel", "written_sum_inertia_rel_to_max"):
            require(s[key] <= REL_TOL, f"{q}.{key}", s[key])
        for key in ("sum_com_max_abs_m", "written_sum_com_max_abs_m"):
            require(s[key] <= ABS_COM_TOL_M, f"{q}.{key}", s[key])
        require_tensor(f"{q}.pad", s["pad_tensor"])
        require_tensor(f"{q}.rod", s["rod_tensor"])
    d = checks["dynamics"]
    require(d["dyn_model_import"] == "ok", "dynamics.dyn_model_import", d["dyn_model_import"])
    for key, ok in d.get("dyn_model_same_inputs", {}).items():
        require(ok, f"dynamics.dyn_model_same_inputs.{key}", ok)
    for key, value in d.get("dyn_model_full_precision_rel", {}).items():
        require(value <= REL_TOL, f"dynamics.dyn_model_full_precision_rel.{key}", value)
    for key, value in d["reference_json_rel"].items():
        require(value <= REL_TOL, f"dynamics.reference_json_rel.{key}", value)
    for key, value in d["doc10_printed"].items():
        require(value["max_abs_diff"] <= value["half_unit_tol"], f"dynamics.doc10_printed.{key}", value)
    require(d["gn_m_moving_vs_exact_m_eff_rel"] <= REL_TOL, "dynamics.gn_m_moving_vs_exact_m_eff_rel",
            d["gn_m_moving_vs_exact_m_eff_rel"])
    require(d["pump_flow_covers_4_legs_at_vmax"], "dynamics.pump_flow_covers_4_legs_at_vmax",
            d["pump_flow_covers_4_legs_at_vmax"])
    refs = d["line_references"]
    for key in ("missing_text", "unlisted_references", "old_style_references"):
        require(not refs[key], f"dynamics.line_references.{key}", refs[key])
    require(refs["references_in_source"] > 0, "dynamics.line_references.references_in_source",
            refs["references_in_source"])
    require(d["reference_json_assumptions_beta_Pa"] == OIL_BULK_MODULUS_EFF_PA,
            "dynamics.reference_json_assumptions_beta_Pa", d["reference_json_assumptions_beta_Pa"])
    t = checks["totals"]
    require(t["superstructure_plus_4_rods_minus_total_rel"] <= REL_TOL, "totals.superstructure_plus_4_rods_minus_total_rel",
            t["superstructure_plus_4_rods_minus_total_rel"])
    require(t["moving_plus_fixed_minus_superstructure_rel"] <= REL_TOL,
            "totals.moving_plus_fixed_minus_superstructure_rel", t["moving_plus_fixed_minus_superstructure_rel"])
    require(abs(t["total_c_minus_a_minus_tool_delta_kg"]) <= JSON_MASS_TOL_KG,
            "totals.total_c_minus_a_minus_tool_delta_kg", t["total_c_minus_a_minus_tool_delta_kg"])
    require(t["level_masses_equal"], "totals.level_masses_equal", t["level_masses_equal"])
    require(checks["yaml_round_trip_equal"], "yaml_round_trip_equal", checks["yaml_round_trip_equal"])
    return failures


if __name__ == "__main__":
    main()
