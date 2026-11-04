"""Parameters of the four-leg shared-pump flow-saturation model (hydraulic_coupling.md).

Everything known comes from 02_params/rexome33.yaml (current REXOME35 dimensions).
Every value the YAML does not hold is listed in ASSUMPTIONS with its sensitivity
range. Pressures are GAUGE [Pa] in this module and in the numpy model; only the
Hopsan generator converts to absolute (p_atm = 1e5 Pa).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[3]
YAML_PATH = ROOT / "02_params" / "rexome33.yaml"
OUT_DIR = ROOT / "06_analysis" / "03_hydraulic" / "coupled"
LEGS = ("FL", "FR", "RL", "RR")
P_ATM_HOPSAN = 1.0e5
P_NOM = 7.0e6  # Hopsan pressure-valve nominal pressure drop [Pa], fixed in the hpp

# value, sensitivity range, reason. ASSUMPTION = not in the drawing or the YAML.
ASSUMPTIONS = {
    "dp_comp_Pa": (10e5, [6e5, 10e5, 20e5], "section compensator dp (Q-M5), criteria 8.3"),
    "dp_unload_Pa": (20e5, [12e5, 20e5, 30e5], "inlet compensator standby dp (Q-M4), criteria 8.3"),
    "width_Pa": (1e5, [0.5e5, 1e5, 2e5], "smoothing width of the compensator transition, criteria 8.3 x1/2, x2"),
    "law": ("priority", ["priority", "proportional"], "distribution law, criteria 8.3 (Q-M5 contrast)"),
    "p_tank_Pa": (2e5, [0.0, 2e5, 5e5], "T line back pressure, flow independent, GAUGE (rod_side 14.7)"),
    "rho_kg_m3": (860.0, [850.0, 875.0], "VG46 at 40-50 C, as l2_params.py"),
    "nu_mm2_s": (32.0, [15.0, 100.0], "VG46 at 50 C, as l2_params.py; used only in the hose loss estimate"),
    "Cq": (0.67, [0.6, 0.7], "orifice discharge coefficient; only the product Cq A matters"),
    "V_gallery_m3": (5e-4, [2e-4, 2e-3], "P line 1/2 in x 3 m + MCV gallery"),
    "V_hose_m3": (2.85e-4, [1.4e-4, 5.7e-4], "A or B hose 3/8 in x 4 m (Q-M9); lumped with the chamber while moving"),
    "comp_q_nom_m3_s": (1.667e-3, [0.83e-3, 3.33e-3], "compensator fully open: 100 L/min at 70 bar (Q-M1)"),
    "comp_k_cs": (3.3e-7, [], "Hopsan compensator spring characteristic, droop about 0.05 bar; numpy is ideal; 3x stiffer gives a limit cycle at ts 1e-5 s"),
    "comp_k_cf": (1.9e-7, [], "Hopsan compensator flow-force characteristic"),
    "unl_q_nom_m3_s": (3.0e-3, [], "inlet compensator fully open: 180 L/min at 70 bar"),
    "unl_k_cs": (2.6e-8, [], "inlet compensator spring characteristic, droop about 2 bar at full bypass"),
    "unl_k_cf": (1.9e-8, [], "inlet compensator flow-force characteristic"),
    "spool_bt_ratio": (1.0, [0.5, 1.0, 2.0], "B->T land area / P->A land area (Q-M1)"),
    "p_pilot_Pa": (35e5, [20e5, 50e5], "retract: rod pressure held by the PO check pilot threshold, GAUGE (Q-M2)"),
    "m_body_tilt_neglected": (True, [], "small angles; tilt enters only through the initial static loads"),
}


def _a(name: str) -> float:
    return ASSUMPTIONS[name][0]


@dataclass(frozen=True)
class Params:
    # YAML, array order LEGS
    A_h: np.ndarray
    A_r: np.ndarray
    stroke: float
    s0: np.ndarray
    m_rod: np.ndarray
    xp: np.ndarray  # lever arm from the CoM, body x [m]
    yp: np.ndarray  # lever arm from the CoM, body y [m]
    mass: float
    I_roll: float
    I_pitch: float
    com: np.ndarray
    pad_z: np.ndarray
    k_st: np.ndarray  # series(k_rod, k_frame, k_concrete) [N/m]
    c_g: np.ndarray  # pad dashpot, contact.rigid_floor.L1.cn_per_pad_N_s_m [N s/m]
    beta: float
    L0h: float
    L0r: float
    Q_pump_th: float  # drawing flow 60.2 L/min [m3/s]
    eta_v_nom: float
    v_max: float
    ramp: float
    p_relief: float
    # assumptions
    dp_comp: float = _a("dp_comp_Pa")
    dp_unl: float = _a("dp_unload_Pa")
    width: float = _a("width_Pa")
    law: str = _a("law")
    flow_limit: bool = True
    p_T: float = _a("p_tank_Pa")
    rho: float = _a("rho_kg_m3")
    Cq: float = _a("Cq")
    V_g: float = _a("V_gallery_m3")
    V_hose: float = _a("V_hose_m3")
    comp_q_nom: float = _a("comp_q_nom_m3_s")
    comp_k_cs: float = _a("comp_k_cs")
    comp_k_cf: float = _a("comp_k_cf")
    unl_q_nom: float = _a("unl_q_nom_m3_s")
    unl_k_cs: float = _a("unl_k_cs")
    unl_k_cf: float = _a("unl_k_cf")
    bt_ratio: float = _a("spool_bt_ratio")
    p_pilot: float = _a("p_pilot_Pa")
    extra: dict = field(default_factory=dict)

    # --- derived valve constants ---
    @property
    def X_comp(self) -> float:
        return self.comp_q_nom / math.sqrt(P_NOM)

    @property
    def Cs_comp(self) -> float:
        return math.sqrt(P_NOM) / self.comp_k_cs

    @property
    def Cf_comp(self) -> float:
        return 1.0 / (self.comp_k_cf * math.sqrt(P_NOM))

    @property
    def X_unl(self) -> float:
        return self.unl_q_nom / math.sqrt(P_NOM)

    @property
    def Cs_unl(self) -> float:
        return math.sqrt(P_NOM) / self.unl_k_cs

    @property
    def Cf_unl(self) -> float:
        return 1.0 / (self.unl_k_cf * math.sqrt(P_NOM))

    @property
    def K_spool(self) -> np.ndarray:
        """P->A flow coefficient at full command [m3/s/sqrt(Pa)]: u = 1 gives v_max at dp_comp."""
        return self.A_h * self.v_max / math.sqrt(self.dp_comp)

    @property
    def K_spool_hopsan(self) -> np.ndarray:
        """As K_spool, corrected for the proportional band of the Hopsan compensator valve."""
        q = self.A_h * self.v_max
        b1 = self.Cs_comp + self.Cf_comp * self.dp_unl
        y = self.dp_comp + b1 * np.maximum(self.X_comp - self.K_spool, 0.0)
        return q / np.sqrt(y)

    def Q_pump(self, eta_v: float) -> float:
        """Delivered pump flow; flow limit off = ample supply (the circuit laws stay)."""
        return self.Q_pump_th * (eta_v if self.flow_limit else 2.0)

    def share_config(self):
        from flow_share import FlowShareConfig

        return FlowShareConfig(A_h=self.A_h, A_r=self.A_r, dp_c=self.dp_comp, dp_ls=self.dp_unl, width=self.width,
                               law=self.law, enabled=self.flow_limit, X_comp=self.X_comp, Cs_unl=self.Cs_unl,
                               Cf_unl=self.Cf_unl, X_unl=self.X_unl, p_T=self.p_T, p_relief=self.p_relief)

    def with_(self, **kw) -> "Params":
        return replace(self, **kw)


def series(*k: float) -> float:
    return 1.0 / sum(1.0 / x for x in k)


def load_params(auger: str = "top") -> Params:
    y = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    act, legs = y["actuator"], y["legs"]
    lvl = y["superstructure"]["auger_levels"][auger]
    rf = y["contact"]["rigid_floor"]
    der = rf["L1"]["derivation"]
    com = np.array(lvl["com_m"], float)
    I = np.array(lvl["inertia_kg_m2"], float)
    A_h = np.array([legs[n]["cylinder"]["head_area_m2"] for n in LEGS])
    A_r = np.array([legs[n]["cylinder"]["annulus_area_m2"] for n in LEGS])
    xy = np.array([legs[n]["cylinder_axis_xy_m"] for n in LEGS], float)
    k_st = np.array([
        series(der["k_rod_N_m"][n], act["frame_stiffness_N_m"], rf["concrete"]["k_N_m"]) for n in LEGS
    ])
    return Params(
        A_h=A_h, A_r=A_r, stroke=float(act["stroke_m"]),
        s0=np.array([der["operating_extension_m"][n] for n in LEGS], float),
        m_rod=np.array([legs[n]["moving_part"]["mass_kg"] for n in LEGS], float),
        xp=xy[:, 0] - com[0], yp=xy[:, 1] - com[1],
        mass=float(lvl["mass_kg"]), I_roll=float(I[0, 0]), I_pitch=float(I[1, 1]), com=com,
        pad_z=np.array([legs[n]["pad_bottom_center_retracted_m"][2] for n in LEGS], float),
        k_st=k_st,
        c_g=np.array([rf["L1"]["cn_per_pad_N_s_m"][n] for n in LEGS], float),
        beta=float(act["oil_bulk_modulus_eff_Pa"]), L0h=float(act["oil_dead_length_m"]),
        L0r=float(act["rod_dead_length_m"]), Q_pump_th=float(act["pump_flow_m3_s"]),
        eta_v_nom=float(act["pump_volumetric_efficiency"]), v_max=float(act["max_speed_m_s"]),
        ramp=float(act["command_ramp_s"]), p_relief=float(act["relief_pressure_moving_Pa"]),
    )


def static_loads(p: Params, roll_deg: float = 0.0, pitch_deg: float = 0.0) -> np.ndarray:
    """Cylinder forces [N] of the rigid body on four equal springs (YAML static rule).

    Tilt shifts the effective CoM position over the pads by h tan(angle), with the
    CoM height h above the pad plane at the operating extension. Gravity along the
    leg axis is W cos(alpha). roll > 0: +y side up, CoM moves to -y. pitch > 0:
    nose down, CoM moves to +x. Small-angle rigid plane, no pad friction.
    """
    phi, th = math.radians(roll_deg), math.radians(pitch_deg)
    W = p.mass * 9.80665
    h = float(np.mean(p.com[2] - (p.pad_z - p.s0)))
    x_eff = h * math.tan(th)  # relative to the CoM plan position
    y_eff = -h * math.tan(phi)
    G = np.column_stack([np.ones(4), p.xp, p.yp])
    b = np.array([W * math.cos(phi) * math.cos(th), W * x_eff, W * y_eff])
    # minimum-norm solution of G^T F = b is the equal-spring distribution
    return G @ np.linalg.solve(G.T @ G, b)


def twist_vector(p: Params) -> np.ndarray:
    """Left null vector n of G = [1, yp, -xp]: n.v = twist rate, F = T n is self stress."""
    G = np.column_stack([np.ones(4), p.yp, -p.xp])
    _, _, vt = np.linalg.svd(G.T)
    n = vt[-1]
    return n / n[0]
