"""C9 mast bending check: flexible upright mast vs the rigid superstructure (L1) model.

00_docs/01_dynamics/dynamics_model.md revision 10 (section 3.9). Inputs (read only):
  01_cad/04_mast/mast_beam_properties.csv / .json (cad-expert extraction, 00_docs/00_cad/cad_mast_beam.md)
  02_params/rexome33.yaml (through dyn_model), 06_analysis/00_dynamics/reference.json (L1 stiffness / damping)

Model (all linear, small motion about the levelled static state, body level = world axes):
  * Mast = 3D Euler-Bernoulli frame along body z at the axis x 2.51408, y 0 (mast_axis_reference). Node DoF
    [ux, uy, uz, rx, ry, rz]; fore-aft bending (ux, ry) uses EIy_eff, lateral (uy, -rx) EIx_eff, torsion GJ_eff,
    axial EA_eff (slice effective = harmonic mean, merged to h-long elements in series). Mast slices are lumped
    masses at their own CoM, rigidly offset from the nearest node.
  * Attachments as rigid masses on the nearest node: top sheave, winch, lower guide, backstay equivalent mass at its
    upper pivot (180.9 kg). Auger drive + tool = rigid body (6 DoF) on the mast through stiff shoe springs (x at both
    rails, y at the centre, per shoe row) and a vertical pinion spring ('rows'), or rigidly at the shoe-span centre
    node ('centre', the CAD reference estimate).
  * Supports: hinge pin H1 (2.033, 0, 1.371) - translations and rx, rz rigid to the boom, ry free;
    boom = rigid point mass 1,275.9 kg turning about the boom roll pin (axis x through (y 0.47, z 0.569)) against the
    boom-cylinder roll spring k_roll = k_cyl * (1.0 m)^2; backstay = axial spring k_bs between the boom lower pivot
    and the mast upper pivot (plus the T/L string term).
  * Coupled model: floating frame. Body 6 DoF about the composite CoM (superstructure incl. mast + 4 rods at e_op),
    mast DoF relative to the body frame. Rigid-limit identity: the body block of M and K equals the L1 6-DoF model
    exactly (checked). Gravity: second-order terms of every preload (beam P-delta, offset points, backstay string,
    boom pendulum, body-mast cross term m g (rx_b w_y - ry_b w_x)); pads as in dyn_model.stiffness_6dof.
  * Damping: L1 pad dashpots (reference.json) + mast stiffness-proportional beta K (zeta 0.015 at the mast-only f1).

Conventions: body frame x forward, y left, z up (SI); gravity -9.80665 z_hat m/s^2; roll about +x, pitch about +y
(pitch > 0 nose down); leg order FL, FR, RL, RR. Frequencies in Hz (rad/s in the JSON where noted).

Run (dynamics-dev activated; about 1 min):
  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_mast_bending_check.py [--no-plots]
Writes 06_analysis/00_dynamics/mast_bending_check.json, mast_bending_check_frequencies.png and
mast_bending_check_transients.png. Deterministic (no random numbers).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import eigh
from scipy.optimize import brentq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dyn_model as dm  # noqa: E402

ROOT = dm.PROJECT_ROOT
MAST_CSV = ROOT / "01_cad" / "04_mast" / "mast_beam_properties.csv"
MAST_JSON = ROOT / "01_cad" / "04_mast" / "mast_beam_properties.json"
PARTS_CSV = ROOT / "01_cad" / "01_parts" / "parts_classified.csv"
REF_JSON = ROOT / "06_analysis" / "00_dynamics" / "reference.json"
OUT_DIR = ROOT / "06_analysis" / "00_dynamics"
OUT_JSON = OUT_DIR / "mast_bending_check.json"

IMU_C1 = np.array([0.31, 0.88, 0.040])   # IMU point C1 (CLAUDE.md, user decision 2026-10-20)
TAU_FILTER = 0.5                         # s, each of the two first-order stages (CLAUDE.md)
F_CROSSOVER_HZ = 0.064                   # levelling loop crossover (imu_cabin_and_accuracy_review.md 2.3)
ZETA_MAST = 0.015                        # ASSUMPTION (CLAUDE.md damping decision): structure / mast modes
K_PEN = 1.0e12                           # N/m, penalty for rigid joints (hinge pin, shoes, clamps)
K_PEN_ROT = 1.0e13                       # N m/rad
RAIL_X, RAIL_Y, PINION_X = 2.613, 0.32, 2.706  # corner-rail centre x, |y|; rack pitch line x (cad_mast_beam.md 3, 6.3)

# boom (BOOM:1 in parts_classified.csv; CAD mm -> body m: x = Z_cad, y = X_cad, z = Y_cad). Point mass (own inertia
# neglected, ASSUMPTION): its roll inertia about the pin is ~600 kg m^2 vs ~5e5 for the mast set.
BOOM_PART = "REXOME33_Assy_r3(미니어쳐) / BOOM:1"

# support stiffness sweeps (ASSUMPTIONS; Q-B1, Q-B3). k_bs: backstay axial; k_cyl: boom cylinder (lever 1.0 m)
K_BS_SWEEP = [1.0e7, 3.0e7, 1.0e8, 2.882e8, 4.177e8, 6.683e8, 1.0e12]
K_CYL_SWEEP = [1.0e7, 3.0e7, 1.0e8, 3.0e8, 1.0e9, 1.0e12]
K_BS_NOM = 4.177e8    # oil only, both chambers locked, beta 1.0 GPa (JSON supports.backstay) = UPPER bound
K_BS_LOW = 1.0e8      # ASSUMPTION: hoses / valve block / steel in series (Q-B1 open) - lower nominal
K_CYL_NOM = 2.1e8     # ASSUMPTION: bore ~D200 (face R100), locked column ~0.15 m, beta 1.0 GPa -> 1e9*0.0314/0.15
K_CYL_LOW = 3.0e7     # ASSUMPTION: unlocked / long hoses (Q-B3 open)
LEVELS = dm.LEVELS
DEG = 180.0 / math.pi


def r(x, n=6):
    if isinstance(x, (list, tuple)):
        return [r(v, n) for v in x]
    if isinstance(x, np.ndarray):
        return r(x.tolist(), n)
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        x = float(x)
        if x == 0.0 or not math.isfinite(x):
            return x
        return float(f"{x:.{n}g}")
    if isinstance(x, dict):
        return {k: r(v, n) for k, v in x.items()}
    return x


def skew(v):
    return np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0.0]])


def a_off(rv):
    """6x6: motion [u; rot] of a point at offset rv from a reference with motion [u_ref; rot]."""
    A = np.eye(6)
    A[:3, 3:] = -skew(rv)
    return A


def hess_offset(f, rv):
    """Hessian w.r.t. the rotation vector of -f . (1/2 rot x (rot x rv)): constant force f at offset rv.

    Equals -F0 * dyn_model._hz(d) for f = (0, 0, F0) (checked in main)."""
    f = np.asarray(f, float); rv = np.asarray(rv, float)
    return -(0.5 * (np.outer(f, rv) + np.outer(rv, f)) - float(f @ rv) * np.eye(3))


def beam_matrices(L, EA, EIx_lat, EIy_fa, GJ, N=0.0):
    """12x12 elastic and geometric stiffness of a frame element along +z (node DoF ux uy uz rx ry rz).

    Fore-aft plane: v = ux, slope = +ry (EIy_fa). Lateral plane: v = uy, slope = -rx (EIx_lat).
    N = axial force (tension +) for the geometric matrix."""
    Ke = np.zeros((12, 12)); Kg = np.zeros((12, 12))
    kb = np.array([[12, 6 * L, -12, 6 * L], [6 * L, 4 * L * L, -6 * L, 2 * L * L],
                   [-12, -6 * L, 12, -6 * L], [6 * L, 2 * L * L, -6 * L, 4 * L * L]]) / L ** 3
    kgm = np.array([[6 / 5, L / 10, -6 / 5, L / 10], [L / 10, 2 * L * L / 15, -L / 10, -L * L / 30],
                    [-6 / 5, -L / 10, 6 / 5, -L / 10], [L / 10, -L * L / 30, -L / 10, 2 * L * L / 15]]) / L
    for (iv1, is1, iv2, is2, sgn, EI) in ((0, 4, 6, 10, 1.0, EIy_fa), (1, 3, 7, 9, -1.0, EIx_lat)):
        T = np.zeros((4, 12)); T[0, iv1] = 1; T[1, is1] = sgn; T[2, iv2] = 1; T[3, is2] = sgn
        Ke += EI * T.T @ kb @ T
        Kg += N * T.T @ kgm @ T
    for (i, j, k) in ((2, 8, EA / L), (5, 11, GJ / L)):
        Ke[np.ix_([i, j], [i, j])] += k * np.array([[1, -1], [-1, 1.0]])
    return Ke, Kg


# ---------------------------------------------------------------------------------------------------- input data
def load_mast():
    with open(MAST_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with open(MAST_JSON, encoding="utf-8") as f:
        js = json.load(f)

    def col(name):
        return np.array([float(rw[name]) if rw[name] not in ("", None) else np.nan for rw in rows])

    d = {k: col(k) for k in ("z_lo_m", "z_hi_m", "z_center_m", "A_m2", "Iy_m4", "Ix_m4", "EA_eff_N", "EIy_eff_N_m2",
                             "EIx_eff_N_m2", "GJ_eff_N_m2", "slice_mass_kg", "slice_com_x_m", "slice_com_y_m")}
    d["json"] = js
    return d


# --------------------------------------------------------------------------------------------- mast system model
class MastSystem:
    """Mast + attachments + auger + boom, DoF relative to the body frame. Body fixed = mast-only analysis."""

    def __init__(self, mast, level, h=0.10, k_bs=K_BS_NOM, k_cyl=K_CYL_NOM, shoe="rows", clamp_z=None,
                 E_scale=1.0, k_shoe=K_PEN, boom=None, geometric=True):
        js = mast["json"]
        self.level, self.h, self.k_bs, self.k_cyl, self.shoe, self.clamp_z = level, h, k_bs, k_cyl, shoe, clamp_z
        self.g = 9.80665
        self.x_ax = float(js["mast_axis_reference"]["x_m"])
        sup = js["supports"]
        self.r_hinge = np.array(sup["hinge_pin"]["point_body_m"], float)
        bs = sup["backstay"]
        self.r_bs_lo = np.array(bs["lower_pivot_body_m"], float)
        self.r_bs_up = np.array(bs["upper_pivot_body_m"], float)
        self.n_bs = (self.r_bs_up - self.r_bs_lo) / np.linalg.norm(self.r_bs_up - self.r_bs_lo)
        self.L_bs = float(np.linalg.norm(self.r_bs_up - self.r_bs_lo))
        self.r_pin = np.array(sup["boom_lateral"]["boom_roll_pin"]["point_body_m"], float)
        self.lever_cyl = float(sup["boom_lateral"]["boom_cylinder"]["lever_arm_about_roll_pin_m"])
        # ---- nodes: slices with stiffness, merged into h-long elements (flexibilities in series)
        ok = mast["EIy_eff_N_m2"] > 0
        zlo, zhi = mast["z_lo_m"][ok], mast["z_hi_m"][ok]
        z0, z1 = float(zlo.min()), float(zhi.max())
        nel = int(round((z1 - z0) / h))
        zn = z0 + h * np.arange(nel + 1)
        if clamp_z is not None:
            jc = int(np.argmin(np.abs(zn - clamp_z)))
            zn = zn[jc:]
        self.zn = zn
        self.nn = len(zn)
        self.elems = []
        for e in range(self.nn - 1):
            za, zb = zn[e], zn[e + 1]
            sel = ok & (mast["z_lo_m"] >= za - 1e-9) & (mast["z_hi_m"] <= zb + 1e-9)
            dz = mast["z_hi_m"][sel] - mast["z_lo_m"][sel]
            Lh = dz.sum()
            props = [Lh / np.sum(dz / mast[k][sel]) for k in ("EA_eff_N", "EIx_eff_N_m2", "EIy_eff_N_m2", "GJ_eff_N_m2")]
            props = [p * E_scale for p in props]
            self.elems.append((e, Lh, *props))
        # DoF layout: nodes (6 each), auger (6), boom roll (1)
        self.i_aug = 6 * self.nn
        self.i_boom = 6 * self.nn + 6
        self.n = 6 * self.nn + 7
        # ---- mass elements: (name, m, c, I3x3 about c, attachment)
        self.masses = []
        dz_s = mast["z_hi_m"] - mast["z_lo_m"]
        for s in range(len(mast["slice_mass_kg"])):
            m = mast["slice_mass_kg"][s]
            if m <= 0:
                continue
            zc = mast["z_center_m"][s]
            if clamp_z is not None and zc < zn[0]:
                continue
            cx = mast["slice_com_x_m"][s] if np.isfinite(mast["slice_com_x_m"][s]) else self.x_ax
            cy = mast["slice_com_y_m"][s] if np.isfinite(mast["slice_com_y_m"][s]) else 0.0
            A = mast["A_m2"][s]
            if A > 0:
                rx2, ry2 = mast["Ix_m4"][s] / A, mast["Iy_m4"][s] / A   # (int y^2 dA)/A, (int x^2 dA)/A
            else:
                rx2 = ry2 = 0.0
            I3 = m * np.diag([rx2 + dz_s[s] ** 2 / 12, ry2 + dz_s[s] ** 2 / 12, rx2 + ry2])
            c = np.array([cx, cy, zc])
            e = int(np.searchsorted(zn, zc) - 1)
            if 0 <= e < self.nn - 1:   # half to each end node of the element holding the slice (rigid offsets)
                self.masses.append(("slice", 0.5 * m, c, 0.5 * I3, ("node", e)))
                self.masses.append(("slice", 0.5 * m, c, 0.5 * I3, ("node", e + 1)))
            else:
                self.masses.append(("slice", m, c, I3, ("node", self.near(zc))))
        att = js["attachments_lumped"]
        for key in ("topsheave", "winch", "lower_guide"):
            a = att[key]
            c = np.array(a["com_m"], float)
            if clamp_z is not None and c[2] < zn[0]:
                continue
            self.masses.append((key, float(a["mass_kg"]), c, np.array(a["inertia_about_com_body_kg_m2"], float),
                                ("node", self.near(c[2]))))
        self.m_bs_eq = float(js["supports"]["backstay"]["equivalent_mass_at_upper_pivot_kg"])
        if clamp_z is None:
            self.masses.append(("backstay_eq", self.m_bs_eq, self.r_bs_up.copy(), np.zeros((3, 3)),
                                ("node", self.near(self.r_bs_up[2]))))
        ag = js["auger_drive_tool_levels"][level]
        self.aug = ag
        self.c_aug = np.array(ag["com_m"], float)
        self.has_aug = not (clamp_z is not None and ag["shoe_span_centre_z_m"] < zn[0])
        if self.has_aug:
            self.masses.append(("auger", float(ag["mass_kg"]), self.c_aug.copy(), np.array(ag["inertia_kg_m2"], float),
                                ("auger",)))
        self.boom = boom
        if boom is not None and clamp_z is None:
            self.masses.append(("boom", boom[0], np.array(boom[1], float), np.zeros((3, 3)), ("boom",)))
        # ---- springs (translational along n or rotational about n), endpoints (attachment, point)
        self.springs = []   # dict(kind, a, ra, b, rb, n, k, tag)
        self.fixed = []
        if clamp_z is not None:
            self.fixed += list(range(0, 6))
        else:
            jh = self.near(self.r_hinge[2])
            for ax in np.eye(3):
                self.add("t", ("node", jh), self.r_hinge, ("boom",), self.r_hinge, ax, K_PEN, "hinge")
            self.add("r", ("node", jh), None, ("boom",), None, np.array([1.0, 0, 0]), K_PEN_ROT, "hinge_rx")
            self.add("r", ("node", jh), None, ("ground",), None, np.array([0, 0, 1.0]), K_PEN_ROT, "hinge_rz")
            self.add("r", ("boom",), None, ("ground",), None, np.array([1.0, 0, 0]), k_cyl * self.lever_cyl ** 2, "boom_roll")
            if k_bs is not None:
                self.add("t", ("node", self.near(self.r_bs_up[2])), self.r_bs_up, ("boom",), self.r_bs_lo, self.n_bs,
                         k_bs, "backstay")
        if not self.has_aug:
            self.fixed += list(range(self.i_aug, self.i_aug + 6))
        elif shoe == "rows":
            for zr in ag["shoe_rows_z_m"]:
                zc = 0.5 * (zr[0] + zr[1]); j = self.near(zc)
                for sy in (RAIL_Y, -RAIL_Y):
                    p_ = np.array([RAIL_X, sy, zc])
                    self.add("t", ("auger",), p_, ("node", j), p_, np.array([1.0, 0, 0]), k_shoe, "shoe_x")
                self.add("t", ("auger",), np.array([RAIL_X, 0, zc]), ("node", j), np.array([RAIL_X, 0, zc]),
                         np.array([0, 1.0, 0]), k_shoe, "shoe_y")
            zp = 0.5 * (ag["pinion_z_m"][0] + ag["pinion_z_m"][1]); j = self.near(zp)
            p_ = np.array([PINION_X, 0, zp])
            self.add("t", ("auger",), p_, ("node", j), p_, np.array([0, 0, 1.0]), k_shoe, "pinion_z")
        else:   # 'centre': rigid at the shoe-span centre node (CAD reference estimate)
            j = self.near(ag["shoe_span_centre_z_m"])
            p_ = np.array([self.x_ax, 0, self.zn[j]])
            for ax in np.eye(3):
                self.add("t", ("auger",), p_, ("node", j), p_, ax, K_PEN, "aug_rigid")
                self.add("r", ("auger",), None, ("node", j), None, ax, K_PEN_ROT, "aug_rigid_r")
        if clamp_z is not None or boom is None:
            self.fixed.append(self.i_boom)
        self.free = np.setdiff1d(np.arange(self.n), np.array(self.fixed, int))
        self.geometric = geometric
        self._assemble()

    def near(self, z):
        return int(np.argmin(np.abs(self.zn - z)))

    def add(self, kind, a, ra, b, rb, n, k, tag):
        self.springs.append(dict(kind=kind, a=a, ra=ra, b=b, rb=rb, n=np.asarray(n, float), k=float(k), tag=tag))

    def ref_point(self, att):
        if att[0] == "node":
            return np.array([self.x_ax, 0.0, self.zn[att[1]]])
        if att[0] == "auger":
            return self.c_aug
        if att[0] == "boom":
            return self.r_pin
        return None

    def pmap(self, att, pt):
        """6 x n map: [translation; rotation] of the point pt rigidly attached to att."""
        T = np.zeros((6, self.n))
        if att[0] == "node":
            i = 6 * att[1]
            T[:, i:i + 6] = a_off(pt - self.ref_point(att))
        elif att[0] == "auger":
            T[:, self.i_aug:self.i_aug + 6] = a_off(pt - self.c_aug)
        elif att[0] == "boom":
            ex = np.array([1.0, 0, 0])
            T[:3, self.i_boom] = np.cross(ex, pt - self.r_pin)
            T[3:, self.i_boom] = ex
        return T

    def rot_index(self, att):
        if att[0] == "node":
            return list(range(6 * att[1] + 3, 6 * att[1] + 6))
        if att[0] == "auger":
            return list(range(self.i_aug + 3, self.i_aug + 6))
        return None

    def _assemble(self):
        n = self.n
        K = np.zeros((n, n)); M = np.zeros((n, n))
        for (e, L, EA, EIx, EIy, GJ) in self.elems:
            Ke, _ = beam_matrices(L, EA, EIx, EIy, GJ)
            idx = list(range(6 * e, 6 * e + 12))
            K[np.ix_(idx, idx)] += Ke
        self.K_beam = K.copy()
        for s in self.springs:
            G = self.sgrad(s)
            K += s["k"] * np.outer(G, G)
        self.B = {}
        for (name, m, c, I3, att) in self.masses:
            B = self.pmap(att, c)
            Me = np.zeros((6, 6)); Me[:3, :3] = m * np.eye(3); Me[3:, 3:] = I3
            M += B.T @ Me @ B
        self.K_el, self.M = K, M
        # gravity load and static solution (body fixed, level)
        f = np.zeros(n)
        for (name, m, c, I3, att) in self.masses:
            f += self.pmap(att, c)[2] * (-m * self.g)
        self.f_g = f
        fr = self.free
        u = np.zeros(n)
        u[fr] = np.linalg.solve(K[np.ix_(fr, fr)], f[fr])
        self.u_static = u
        self.K_geo = self._geometric(u) if self.geometric else np.zeros((n, n))

    def sgrad(self, s):
        Ta = self.pmap(s["a"], s["ra"] if s["ra"] is not None else self.ref_point(s["a"]) if s["a"][0] != "ground" else np.zeros(3))
        Tb = self.pmap(s["b"], s["rb"] if s["rb"] is not None else (self.ref_point(s["b"]) if s["b"][0] != "ground" else np.zeros(3)))
        rows = slice(0, 3) if s["kind"] == "t" else slice(3, 6)
        return s["n"] @ (Ta[rows] - Tb[rows])

    def _geometric(self, u):
        n = self.n
        Kg = np.zeros((n, n))
        self.N_elem = []
        for (e, L, EA, EIx, EIy, GJ) in self.elems:
            N = EA / L * (u[6 * e + 8] - u[6 * e + 2])
            self.N_elem.append(N)
            _, Kge = beam_matrices(L, EA, EIx, EIy, GJ, N)
            idx = list(range(6 * e, 6 * e + 12))
            Kg[np.ix_(idx, idx)] += Kge
        self.N_elem = np.array(self.N_elem)
        ex = np.array([1.0, 0, 0])

        def add_offset(att, pt, fvec):
            if att[0] in ("node", "auger"):
                ri = self.rot_index(att)
                Kg[np.ix_(ri, ri)] += hess_offset(fvec, pt - self.ref_point(att))
            elif att[0] == "boom":
                Kg[self.i_boom, self.i_boom] += ex @ hess_offset(fvec, pt - self.r_pin) @ ex

        self.spring_forces = {}
        for s in self.springs:
            if s["kind"] != "t":
                continue
            G = self.sgrad(s)
            sval = s["k"] * float(G @ u)   # elongation force (tension +): force on a = -sval n, on b = +sval n
            self.spring_forces.setdefault(s["tag"], []).append(sval)
            add_offset(s["a"], s["ra"], -sval * s["n"])
            add_offset(s["b"], s["rb"], sval * s["n"])
            if s["tag"] == "backstay":
                Ta = self.pmap(s["a"], s["ra"])[:3]; Tb = self.pmap(s["b"], s["rb"])[:3]
                D = Ta - Tb
                P = np.eye(3) - np.outer(s["n"], s["n"])
                Kg += (sval / self.L_bs) * D.T @ P @ D
        for (name, m, c, I3, att) in self.masses:
            add_offset(att, c, np.array([0, 0, -m * self.g]))
        return Kg

    def KM(self, geometric=True):
        K = self.K_el + (self.K_geo if geometric else 0.0)
        fr = self.free
        return K[np.ix_(fr, fr)], self.M[np.ix_(fr, fr)]

    def modes(self, geometric=True, nmodes=12):
        K, M = self.KM(geometric)
        w2, Phi = eigh(K, M, subset_by_index=[0, min(nmodes, K.shape[0]) - 1])
        f = np.sqrt(np.clip(w2, 0, None)) / (2 * np.pi)
        return f, Phi, K, M

    def classify(self, Phi, M):
        """Kinetic-energy share per family: fore-aft (ux, ry), lateral (uy, rx), torsion (rz), axial (uz), boom."""
        fr = self.free
        fam = np.empty(self.n, dtype=object)
        for j in range(self.nn):
            for k, nm in enumerate(("FA", "LAT", "AX", "LAT", "FA", "TOR")):
                fam[6 * j + k] = nm
        for k, nm in enumerate(("FA", "LAT", "AX", "LAT", "FA", "TOR")):
            fam[self.i_aug + k] = nm
        fam[self.i_boom] = "LAT"
        fam = fam[fr]
        out = []
        for j in range(Phi.shape[1]):
            v = Phi[:, j]
            e = np.abs(v * (M @ v)); e /= e.sum()
            out.append({nm: float(e[fam == nm].sum()) for nm in ("FA", "LAT", "TOR", "AX")})
        return out


def mast_only_table(mast, level, boom, **kw):
    ms = MastSystem(mast, level, boom=boom, **kw)
    f, Phi, K, M = ms.modes(nmodes=12)
    cls = ms.classify(Phi, M)
    fam = {}
    for fj, c in zip(f, cls):
        dom = max(c, key=c.get)
        if c[dom] < 0.5:
            dom = "MIX"
        fam.setdefault(dom, []).append(float(fj))
    return ms, f, cls, fam


# --------------------------------------------------------------------------------------- body (L1) and coupling
def l1_setup(p, geo, ref, level, lifted=True):
    """L1 6-DoF body about the composite CoM: M6, K6 (pads incl. preload term), C6, AZ, k, c, F0."""
    g = geo.g
    xy = geo.pad_xy
    e_op = geo.touch_extension + dm.ASSUMPTIONS["crawler_clearance_m"]
    L1 = ref["chrono_test_references"]["L1_rigid_motor_lumped_contact"]
    kv = np.array(L1["k_vertical_N_m"]); kt = np.array(L1["k_horizontal_N_m"])
    cn = np.array(L1["c_pad_N_s_m"]); ct = np.array(L1["c_tan_N_s_m"])
    if lifted:
        bw = dm.body_with_rods(p, geo, level, e_op)
        pad_pts = np.column_stack([xy, geo.pad_z_retracted - e_op])
        F0, _, _ = dm.static_loads(kv, xy, bw.mass * g, bw.com[:2])
        K6 = dm.stiffness_6dof(bw, pad_pts, kv, kt, F0)
        C6 = np.zeros((6, 6)); AZ = []
        K6el = np.zeros((6, 6))
        for i in range(4):
            ax, ay, az = dm.a_vec(pad_pts[i] - bw.com)
            C6 += cn[i] * np.outer(az, az) + ct[i] * (np.outer(ax, ax) + np.outer(ay, ay))
            K6el += kv[i] * np.outer(az, az) + kt[i] * (np.outer(ax, ax) + np.outer(ay, ay))
            AZ.append(az)
        return dict(body=bw, M6=dm.mass_6dof(bw), K6=K6, K6el=K6el, C6=C6, AZ=np.array(AZ), kv=kv, cn=cn, F0=F0,
                    e_op=e_op, pad_pts=pad_pts)
    # crawler on the floor, legs retracted (layout D, rollers + gapped end shoes, tangential 0 as in reference.json)
    bw = dm.body_with_rods(p, geo, level, np.zeros(4))
    xy_c, k_c, _ = dm.crawler_points(p); gap = dm.crawler_gaps(p)
    W = bw.mass * g
    F, q, act = dm.static_unilateral(xy_c, k_c, -gap, W, bw.com[:2])
    pts3 = np.column_stack([xy_c[act], np.full(int(act.sum()), geo.crawler_bottom_z)])
    K6 = np.zeros((6, 6)); K6el = np.zeros((6, 6)); C6 = np.zeros((6, 6))
    c_tot = dm.crawler_damping_total(float(p["contact"]["crawler"]["kn_total_N_m"]),
                                     dm.body_with_rods(p, geo, "top", e_op).mass)
    c_each = c_tot / int((gap <= 0).sum())
    for j, kk, F0j in zip(range(len(pts3)), k_c[act], F[act]):
        d = pts3[j] - bw.com
        _, _, az = dm.a_vec(d)
        K6 += kk * np.outer(az, az); K6el += kk * np.outer(az, az)
        K6[3:, 3:] -= F0j * dm._hz(d)
        C6 += c_each * np.outer(az, az)
    return dict(body=bw, M6=dm.mass_6dof(bw), K6=K6, K6el=K6el, C6=C6, n_active=int(act.sum()),
                crawler_pts=pts3, crawler_F=F[act])


def rest_body(bw, ms):
    """Superstructure+rods minus every mast-side mass (mass, CoM, inertia about CoM)."""
    I_o = bw.inertia + bw.mass * (bw.com @ bw.com * np.eye(3) - np.outer(bw.com, bw.com))
    m_r = bw.mass; s_r = bw.mass * bw.com
    for (name, m, c, I3, att) in ms.masses:
        I_o = I_o - (I3 + m * (c @ c * np.eye(3) - np.outer(c, c)))
        m_r -= m; s_r = s_r - m * c
    c_r = s_r / m_r
    I_r = I_o - m_r * (c_r @ c_r * np.eye(3) - np.outer(c_r, c_r))
    return m_r, c_r, I_r


def coupled(ms, l1):
    """Floating-frame coupled matrices over [body 6 | mast free DoF]."""
    bw = l1["body"]; ref = bw.com; g = ms.g
    fr = ms.free; nf = len(fr)
    n = 6 + nf
    M = np.zeros((n, n)); K = np.zeros((n, n))
    m_r, c_r, I_r = rest_body(bw, ms)
    Ab = a_off(c_r - ref)
    Me = np.zeros((6, 6)); Me[:3, :3] = m_r * np.eye(3); Me[3:, 3:] = I_r
    M[:6, :6] += Ab.T @ Me @ Ab
    for (name, m, c, I3, att) in ms.masses:
        B = np.zeros((6, n))
        B[:, :6] = a_off(c - ref)
        B[:, 6:] = ms.pmap(att, c)[:, fr]
        Me = np.zeros((6, 6)); Me[:3, :3] = m * np.eye(3); Me[3:, 3:] = I3
        M += B.T @ Me @ B
        # gravity cross term m g (rx_b w_y - ry_b w_x), w = translation of the mass point (relative)
        Bt = ms.pmap(att, c)[:3, fr]
        K[3, 6:] += m * g * Bt[1]; K[6:, 3] += m * g * Bt[1]
        K[4, 6:] += -m * g * Bt[0]; K[6:, 4] += -m * g * Bt[0]
    K[:6, :6] += l1["K6"]
    Krel, _ = ms.KM(True)
    K[6:, 6:] += Krel
    return M, K, dict(m_rest=m_r, c_rest=c_r, I_rest=I_r)


def damping_coupled(ms, l1, beta):
    fr = ms.free
    n = 6 + len(fr)
    C = np.zeros((n, n))
    C[:6, :6] = l1["C6"]
    C[6:, 6:] = beta * ms.K_el[np.ix_(fr, fr)]
    return C


def strain_share(ms, l1, phi):
    """Elastic strain-energy share of the mast system (beam + supports) in a coupled mode."""
    fr = ms.free
    qb, u = phi[:6], phi[6:]
    Em = float(u @ ms.K_el[np.ix_(fr, fr)] @ u)
    Ep = float(qb @ l1["K6el"] @ qb)
    return Em / (Em + Ep) if Em + Ep > 0 else 0.0


def coupled_modes(ms, l1, nmodes=14):
    M, K, info = coupled(ms, l1)
    w2, Phi = eigh(K, M, subset_by_index=[0, nmodes - 1])
    f = np.sqrt(np.clip(w2, 0, None)) / (2 * np.pi)
    share = [strain_share(ms, l1, Phi[:, j]) for j in range(nmodes)]
    return f, Phi, share, M, K, info


def mac_track(l1, Phi, M):
    """For each rigid 6-DoF mode, the coupled mode with the largest body-coordinate MAC (mass weighted)."""
    w2r, Phir = eigh(l1["K6"], l1["M6"])
    Mb = l1["M6"]
    out = []
    for i in range(6):
        a = Phir[:, i]
        best, jb = -1, -1
        for j in range(Phi.shape[1]):
            b = Phi[:6, j]
            mac = (a @ Mb @ b) ** 2 / ((a @ Mb @ a) * (b @ Mb @ b) + 1e-300)
            if mac > best:
                best, jb = mac, j
        out.append((i, float(np.sqrt(w2r[i]) / (2 * np.pi)), jb, float(best)))
    return out


# ------------------------------------------------------------------------------------------- time responses
def lp2_filter(t, x):
    """Two first-order stages tau 0.5 s (exact for piecewise-linear input on the grid)."""
    from scipy.signal import lsim
    num, den = [1.0], np.polymul([TAU_FILTER, 1.0], [TAU_FILTER, 1.0])
    y0 = x[0]
    _, y, _ = lsim((num, den), x - y0, t - t[0])
    return y + y0


def simulate_linear(sysm, l1, geo, s_fun, qext_fun, kinks, t_a, t_b, init, dt_out=2e-3):
    """Linear response of the lifted L1 model (rigid 6-DoF or coupled) to pad base motion and an external body load.

    sysm = (M, K, C) with the 6 body DoF first. s_fun(t) -> (s (4), sdot (4)): pad base input of the rigid motors
    (s = e - e_op); qext_fun(t) -> generalised external load on the body DoF (6). Both piecewise linear with kinks at
    `kinks`. init 'ramp' (exact steady state of a ramp before the first kink) or 'static' (constant load before).
    Pad force F = F0 + kv (s - AZ q) + cn (sdot - AZ qdot); quasi-static F_qs from K q = Q_spring(t).
    IMU C1 apparent tilt: phi + a_y/g, theta - a_x/g (run_imu_accuracy_review); filter 2 x first order tau 0.5 s."""
    M, K, C = sysm
    kv, cn, AZ, F0 = l1["kv"], l1["cn"], l1["AZ"], l1["F0"]
    n = M.shape[0]
    Pb = np.zeros((n, 4)); Pb[:6, :] = AZ.T
    w2, Phi = eigh(K, M)
    keep = np.sqrt(np.clip(w2, 0, None)) / (2 * np.pi) < 300.0
    w2, Phi = w2[keep], Phi[:, keep]
    Cr = Phi.T @ C @ Phi
    nm = len(w2)

    def Q(t):
        s, sd = s_fun(t)
        out = Pb @ (kv * s + cn * sd)
        out[:6] += qext_fun(t)
        return out

    def Qk(t):   # spring part only (quasi-static reference)
        s, _ = s_fun(t)
        out = Pb @ (kv * s)
        out[:6] += qext_fun(t)
        return out

    def rhs(t, y):
        eta, deta = y[:nm], y[nm:]
        return np.concatenate([deta, Phi.T @ Q(t) - Cr @ deta - w2 * eta])

    if init == "ramp":
        h = 1e-3
        Q1 = (Q(t_a + h) - Q(t_a)) / h
        eta0 = (Phi.T @ Q(t_a)) / w2 - (Cr @ ((Phi.T @ Q1) / w2)) / w2
        deta0 = (Phi.T @ Q1) / w2
    else:
        eta0 = (Phi.T @ Q(t_a)) / w2
        deta0 = np.zeros(nm)
    y = np.concatenate([eta0, deta0])
    seg = [t_a] + sorted(set(float(x) for x in kinks if t_a < x < t_b)) + [t_b]
    T, Y = [], []
    for a, b in zip(seg[:-1], seg[1:]):
        te = np.arange(a, b, dt_out)
        sol = solve_ivp(rhs, (a, b), y, method="DOP853", rtol=1e-9, atol=1e-12, t_eval=np.append(te, b), max_step=5e-3)
        T.append(sol.t[:-1]); Y.append(sol.y[:, :-1]); y = sol.y[:, -1]
    T = np.concatenate(T); Y = np.concatenate(Y, axis=1)
    eta, deta = Y[:nm], Y[nm:]
    q = Phi @ eta; qd = Phi @ deta
    QQ = np.array([Q(t) for t in T]).T
    qdd = Phi @ (Phi.T @ QQ - Cr @ deta - w2[:, None] * eta)
    q_qs = np.linalg.solve(K, np.array([Qk(t) for t in T]).T)
    S = np.array([s_fun(t)[0] for t in T]).T
    Sd = np.array([s_fun(t)[1] for t in T]).T
    F = F0[:, None] + kv[:, None] * (S - AZ @ q[:6]) + cn[:, None] * (Sd - AZ @ qd[:6])
    F_qs = F0[:, None] + kv[:, None] * (S - AZ @ q_qs[:6])
    rho = IMU_C1 - l1["body"].com
    acc = qdd[:3] + np.cross(qdd[3:6].T, rho).T
    g = geo.g
    app = np.vstack([q[3] + acc[1] / g, q[4] - acc[0] / g])
    app_qs = q_qs[3:5]
    filt = np.vstack([lp2_filter(T, app[0]), lp2_filter(T, app[1])])
    return dict(T=T, t_last=float(max(kinks)), dF=F - F_qs, F=F, app=app, app_qs=app_qs, filt=filt,
                true=q[3:5], n_modes=nm)


def simulate_stop(sysm, l1, geo, t0_pre=3.0, t_after=15.0):
    """Legs extending at v_max stop at their own e_op (V4 schedule, rear first, t = 0 at motor start)."""
    v, e_op = geo.v_max, l1["e_op"]
    t_stop = e_op / v

    def s_fun(t):
        return np.minimum(v * t, e_op) - e_op, np.where(v * t < e_op, v, 0.0)

    return simulate_linear(sysm, l1, geo, s_fun, lambda t: np.zeros(6), list(t_stop),
                           float(t_stop.min()) - t0_pre, float(t_stop.max()) + t_after, "ramp")


def simulate_release(sysm, l1, l1c, geo, T_ramp, t_after=15.0):
    """Proxy of the V4 crawler hand-over: the crawler floor load (static layout-D distribution at legs 0, total = W)
    acts upward on the lifted body and falls linearly to 0 over T_ramp (kinks at 0 and T_ramp); legs locked."""
    pts, Fcr = l1c["crawler_pts"], l1c["crawler_F"]
    ref = l1["body"].com
    Qc = np.zeros(6)
    for pt, Fj in zip(pts, Fcr):
        _, _, az = dm.a_vec(pt - ref)
        Qc += az * Fj

    def qext(t):
        return Qc * float(np.clip(1.0 - t / T_ramp, 0.0, 1.0))

    return simulate_linear(sysm, l1, geo, lambda t: (np.zeros(4), np.zeros(4)), qext, [0.0, T_ramp],
                           -1.0, T_ramp + t_after, "static")


def stop_metrics(res):
    T, tl = res["T"], res["t_last"]
    out = {"max_abs_pad_force_dev_from_quasi_static_N": float(np.abs(res["dF"]).max()),
           "max_pad_force_N": float(res["F"].max())}
    for tw in (0.0, 2.0, 5.0, 10.0):
        m = T >= tl + tw
        out[f"filtered_IMU_tilt_dev_max_deg_after_last_stop+{tw:g}s (roll, pitch)"] = (
            np.degrees(np.abs(res["filt"][:, m] - res["app_qs"][:, m]).max(axis=1)).tolist())
    m = T >= tl
    out["raw_IMU_apparent_tilt_dev_max_deg_after_last_stop (roll, pitch)"] = np.degrees(
        np.abs(res["app"][:, m] - res["app_qs"][:, m]).max(axis=1)).tolist()
    out["true_body_tilt_dev_max_deg_after_last_stop (roll, pitch)"] = np.degrees(
        np.abs(res["true"][:, m] - res["app_qs"][:, m]).max(axis=1)).tolist()
    return out


# --------------------------------------------------------------------------------------------- verification
def verify_uniform_cantilever():
    """Uniform cantilever with a tip mass (no rotary inertia): FE (this element, lumped mass) vs the exact root of
    1 + cos l cosh l + mu l (cos l sinh l - sin l cosh l) = 0, mu = m_tip / (rho A L)."""
    EI, rhoA, L, mt = 1.82e8, 290.0, 7.7, 6257.0
    mu = mt / (rhoA * L)

    def fchar(lam):
        return 1 + math.cos(lam) * math.cosh(lam) + mu * lam * (math.cos(lam) * math.sinh(lam) - math.sin(lam) * math.cosh(lam))

    lam1 = brentq(fchar, 0.1, 1.875)
    f_exact = lam1 ** 2 / (2 * math.pi) * math.sqrt(EI / (rhoA * L ** 4))
    res = []
    for ne in (50, 100, 200, 400):
        h = L / ne
        n = 6 * (ne + 1)
        K = np.zeros((n, n))
        for e in range(ne):
            Ke, _ = beam_matrices(h, 1e10, EI, EI, 1e8)
            idx = list(range(6 * e, 6 * e + 12)); K[np.ix_(idx, idx)] += Ke
        mdiag = np.zeros(n)
        for j in range(ne + 1):
            mj = rhoA * h * (0.5 if j in (0, ne) else 1.0) + (mt if j == ne else 0.0)
            mdiag[6 * j:6 * j + 3] = mj
        fr = np.arange(6, n)
        tr = fr[mdiag[fr] > 0]; ro = fr[mdiag[fr] == 0]   # massless rotations: exact static condensation
        Kc = K[np.ix_(tr, tr)] - K[np.ix_(tr, ro)] @ np.linalg.solve(K[np.ix_(ro, ro)], K[np.ix_(ro, tr)])
        w2 = eigh(Kc, np.diag(mdiag[tr]), subset_by_index=[0, 3], eigvals_only=True)
        f = np.sqrt(w2) / (2 * math.pi)
        res.append((ne, float(f[0]), float(f[1]), float(f[0] / f_exact - 1)))
    errs = [abs(x[3]) for x in res]
    order = [math.log2(errs[i] / errs[i + 1]) for i in range(len(errs) - 1)]
    return {"f_exact_Hz": f_exact, "lambda1": lam1, "mu_tip_over_beam_mass": mu,
            "fe (n_elem, f_fore_aft, f_lateral, rel_err)": res,
            "convergence_order_log2_err_ratio": order,
            "fore_aft_equals_lateral_max_rel": max(abs(x[1] / x[2] - 1) for x in res)}


def verify_rigid_rotation(ms):
    """Rayleigh energy of the assembled K (elastic + geometric) for an exact rigid rotation of the mast set vs an
    independent exact-geometry finite-difference potential (gravity + preloaded backstay/roll springs)."""
    g = ms.g
    out = {}
    ex, ey = np.array([1.0, 0, 0]), np.array([0, 1.0, 0])
    # (a) roll of the whole set (mast + boom + auger) about the boom roll pin axis
    u = np.zeros(ms.n)
    for j in range(ms.nn):
        pt = np.array([ms.x_ax, 0, ms.zn[j]])
        u[6 * j:6 * j + 3] = np.cross(ex, pt - ms.r_pin); u[6 * j + 3:6 * j + 6] = ex
    u[ms.i_aug:ms.i_aug + 3] = np.cross(ex, ms.c_aug - ms.r_pin); u[ms.i_aug + 3:ms.i_aug + 6] = ex
    u[ms.i_boom] = 1.0
    K = ms.K_el + ms.K_geo
    E_fe = float(u @ K @ u)
    # independent: V(a) = sum m g z(a) + 1/2 k_roll a^2 (backstay ends both on the rotating set -> constant length)
    k_roll = ms.k_cyl * ms.lever_cyl ** 2

    def Rx(a):
        c, s = math.cos(a), math.sin(a)
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])

    def V(a):
        v = 0.5 * k_roll * a * a
        for (name, m, c, I3, att) in ms.masses:
            v += m * g * (Rx(a) @ (c - ms.r_pin))[2]
        return v
    da = 1e-4
    E_ex = (V(da) - 2 * V(0) + V(-da)) / da ** 2
    out["roll_about_boom_pin"] = {"uKu_N_m_per_rad2": E_fe, "exact_fd_N_m_per_rad2": E_ex,
                                  "rel_diff": abs(E_fe / E_ex - 1)}
    # (b) pitch of the mast set (no boom) about the hinge pin axis y; backstay lower end fixed on the boom
    u = np.zeros(ms.n)
    for j in range(ms.nn):
        pt = np.array([ms.x_ax, 0, ms.zn[j]])
        u[6 * j:6 * j + 3] = np.cross(ey, pt - ms.r_hinge); u[6 * j + 3:6 * j + 6] = ey
    u[ms.i_aug:ms.i_aug + 3] = np.cross(ey, ms.c_aug - ms.r_hinge); u[ms.i_aug + 3:ms.i_aug + 6] = ey
    E_fe = float(u @ K @ u)
    T0 = ms.spring_forces["backstay"][0]
    k = ms.k_bs
    L0 = ms.L_bs - T0 / k   # free length giving the static tension

    def Ry(a):
        c, s = math.cos(a), math.sin(a)
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])

    def Vp(a):
        v = 0.0
        for (name, m, c, I3, att) in ms.masses:
            if name == "boom":
                continue
            v += m * g * (Ry(a) @ (c - ms.r_hinge))[2]
        Lb = np.linalg.norm(ms.r_hinge + Ry(a) @ (ms.r_bs_up - ms.r_hinge) - ms.r_bs_lo)
        return v + 0.5 * k * (Lb - L0) ** 2
    E_ex = (Vp(da) - 2 * Vp(0) + Vp(-da)) / da ** 2
    # static moment balance check (first derivative of the exact potential ~ 0 at a = 0)
    dV = (Vp(da) - Vp(-da)) / (2 * da)
    out["pitch_about_hinge"] = {"uKu_N_m_per_rad2": E_fe, "exact_fd_N_m_per_rad2": E_ex,
                                "rel_diff": abs(E_fe / E_ex - 1), "exact_dV_da_at_0_N_m": dV,
                                "backstay_tension_N": T0}
    return out


# ------------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-plots", action="store_true")
    args = ap.parse_args()
    t_start = time.perf_counter()
    p = dm.load_params(); geo = dm.geometry_from_params(p)
    with open(REF_JSON, encoding="utf-8") as f:
        ref = json.load(f)
    mast = load_mast()
    js = mast["json"]
    # boom point mass from the parts table (columns located by header)
    with open(PARTS_CSV, encoding="utf-8-sig") as f:
        rec = next(rw for rw in csv.DictReader(f) if rw["instance_path"] == BOOM_PART)
    # CAD (X, Y, Z) mm -> body (y, z, x) m
    boom = (float(rec["mass_step_kg"]), np.array([float(rec["centroid_z_mm"]), float(rec["centroid_x_mm"]),
                                                  float(rec["centroid_y_mm"])]) / 1e3)
    res = {"meta": {
        "script": "04_scripts/01_dynamics/run_mast_bending_check.py",
        "doc": "00_docs/01_dynamics/dynamics_model.md section 3.9 (revision 10)",
        "inputs": ["01_cad/04_mast/mast_beam_properties.csv", "01_cad/04_mast/mast_beam_properties.json",
                   "02_params/rexome33.yaml", "06_analysis/00_dynamics/reference.json",
                   "01_cad/01_parts/parts_classified.csv (BOOM:1 mass and CoM)"],
        "frame": "body: x forward, y left, z up; origin = CAD origin; SI; level body = world axes",
        "gravity_m_s2": [0, 0, -geo.g],
        "angles": "roll about +x, pitch about +y (pitch > 0 nose down)",
        "assumptions": {
            "E_G_steel": "E 210 GPa, G 80.8 GPa (cad extraction), section stiffness = slice effective values in series",
            "mast_axis": "beam nodes on x 2.51408, y 0; centroid shift at hinge / lugs (to 2.20 m) ignored",
            "element_length_m": 0.10,
            "hinge": "pin rigid (penalty 1e12 N/m, 1e13 N m/rad): ux uy uz rx rz tied to the boom, ry free",
            "boom": f"rigid point mass {boom[0]:.1f} kg at {np.round(boom[1], 4).tolist()} m, own inertia neglected, turns about the roll pin only",
            "boom_cylinder_k_cyl_N_m": {"nominal": K_CYL_NOM, "low": K_CYL_LOW, "sweep": K_CYL_SWEEP,
                                        "basis": "ASSUMPTION: bore ~D200 (face radius 100 mm), locked oil ~0.15 m, beta 1 GPa; Q-B3 open"},
            "backstay_k_bs_N_m": {"upper (oil only, beta 1.0)": K_BS_NOM, "low nominal": K_BS_LOW, "sweep": K_BS_SWEEP,
                                  "basis": "JSON supports.backstay (oil only = upper bound); hoses / valve unknown (Q-B1)"},
            "auger_coupling": "rigid auger body; shoe rows x (both rails) + y springs and one vertical pinion spring, 1e12 N/m",
            "attachments": "top sheave, winch, lower guide rigid on the nearest node; backstay eq. mass 180.9 kg at the upper pivot",
            "mast_damping": f"stiffness-proportional, zeta {ZETA_MAST} at the mast-only first bending mode (CLAUDE.md structure 0.015)",
            "L1": "reference.json L1_rigid_motor_lumped_contact (k, c), beta 1.0 GPa; crawler-on: layout D, tangential 0",
            "flange_joints": "rigid (bolted), as in the extraction",
        },
    }}

    # ---------------------------------------------------------------- verification
    ver = {}
    ver["hess_offset_vs_dyn_model_hz"] = float(np.abs(hess_offset([0, 0, 2.5e4], [0.3, -1.2, 0.7])
                                                     + 2.5e4 * dm._hz(np.array([0.3, -1.2, 0.7]))).max())
    ver["uniform_cantilever_tip_mass"] = verify_uniform_cantilever()
    ms_top = MastSystem(mast, "top", boom=boom)
    ver["rigid_rotation_geometric_terms_top"] = verify_rigid_rotation(ms_top)
    m_mast = sum(m for (nm, m, c, I3, a) in ms_top.masses if nm == "slice")
    sl = [(m, c, I3) for (nm, m, c, I3, a) in ms_top.masses if nm == "slice"]
    cm = sum(m * c for m, c, _ in sl) / m_mast
    Izz = sum(I3[2, 2] + m * ((c[0] - cm[0]) ** 2 + (c[1] - cm[1]) ** 2) for m, c, I3 in sl)
    Ixx = sum(I3[0, 0] + m * ((c[1] - cm[1]) ** 2 + (c[2] - cm[2]) ** 2) for m, c, I3 in sl)
    ma = js["attachments_lumped"]["mast_assy_total"]
    ver["mast_mass_vs_json"] = {"slices_kg": m_mast, "json_kg": ma["mass_kg"], "rel": m_mast / ma["mass_kg"] - 1,
                                "com_m": cm.tolist(), "json_com_m": ma["com_m"],
                                "Ixx_Izz_kg_m2": [Ixx, Izz], "json_Ixx_Izz": [ma["inertia_about_com_body_kg_m2"][0][0],
                                                                                ma["inertia_about_com_body_kg_m2"][2][2]]}
    # rigid-limit identity of the coupled model (body block = L1 6-DoF)
    rid = {}
    for lv in LEVELS:
        l1 = l1_setup(p, geo, ref, lv)
        ms = MastSystem(mast, lv, boom=boom)
        M, K, info = coupled(ms, l1)
        mr = info["m_rest"]; Ir = info["I_rest"]
        rid[lv] = {"max_rel_M_body_block_vs_L1": float(np.abs(M[:6, :6] - l1["M6"]).max() / np.abs(l1["M6"]).max()),
                   "max_rel_K_body_block_vs_L1": float(np.abs(K[:6, :6] - l1["K6"]).max() / np.abs(l1["K6"]).max()),
                   "rest_body_mass_kg": mr, "rest_body_inertia_min_eig_kg_m2": float(np.linalg.eigvalsh(Ir).min()),
                   "coupled_K_symmetry": float(np.abs(K - K.T).max() / np.abs(K).max()),
                   "coupled_M_min_eig": float(np.linalg.eigvalsh(M).min())}
        if lv == "top":
            fr6 = np.sqrt(eigh(l1["K6"], l1["M6"], eigvals_only=True)) / (2 * np.pi)
            stiff = {}
            for sc in (1.0, 10.0, 100.0):
                ms_s = MastSystem(mast, lv, boom=boom, E_scale=sc, k_bs=1e12 if sc > 1 else K_BS_NOM,
                                  k_cyl=1e12 if sc > 1 else K_CYL_NOM)
                f_s = coupled_modes(ms_s, l1, nmodes=8)[0]
                stiff[f"E x{sc:g}, supports {'rigid' if sc > 1 else 'nominal'}"] = f_s[:6].tolist()
            rid[lv]["L1_rigid_f_Hz"] = np.sort(fr6).tolist()
            rid[lv]["stiffening_trend_lowest6_Hz"] = stiff
    ver["rigid_limit_identity"] = rid
    # mesh convergence (top, nominal): h 0.10 vs 0.05 m
    conv = {}
    for h in (0.20, 0.10, 0.05):
        _, f, cls, fam = mast_only_table(mast, "top", boom, h=h)
        conv[f"h={h:g}"] = f[:6].tolist()
    ver["mesh_convergence_top_mast_only_lowest6_Hz"] = conv
    res["verification"] = ver

    # ---------------------------------------------------------------- 1. mast-only frequencies (body fixed)
    mo = {}
    # (a) CAD-mimic cantilever (clamped at the hinge height, auger at the shoe-span centre, backstay ignored)
    cad_ref = js["frequency_estimate_reference"]["results_hz"]
    for lv in LEVELS:
        ent = {}
        for geo_on in (False, True):
            ms = MastSystem(mast, lv, boom=None, clamp_z=float(ms_top.r_hinge[2]), shoe="centre", geometric=geo_on)
            f, Phi, K, M = ms.modes(geometric=geo_on, nmodes=10)
            cls = ms.classify(Phi, M)
            fa = [float(x) for x, c in zip(f, cls) if c["FA"] > 0.5]
            la = [float(x) for x, c in zip(f, cls) if c["LAT"] > 0.5]
            to = [float(x) for x, c in zip(f, cls) if c["TOR"] > 0.5]
            ent["with_P_delta" if geo_on else "no_P_delta"] = {"fore_aft_Hz": fa[:2], "lateral_Hz": la[:2],
                                                              "torsion_Hz": to[:1], "auger_included": ms.has_aug}
        ent["cad_reference_fe_Hz (fore-aft f1, f2; lateral f1, f2)"] = [
            cad_ref[lv]["cantilever_fore_aft"]["f1_fe_hz"], cad_ref[lv]["cantilever_fore_aft"]["f2_fe_hz"],
            cad_ref[lv]["cantilever_lateral"]["f1_fe_hz"], cad_ref[lv]["cantilever_lateral"]["f2_fe_hz"]]
        mo.setdefault("cantilever_at_hinge_cad_mimic", {})[lv] = ent
    # (b) supported mast (pin + backstay + boom roll), sweeps
    sweep = {}
    for lv in LEVELS:
        rows = []
        for kbs in K_BS_SWEEP:
            for kcy in K_CYL_SWEEP:
                ms = MastSystem(mast, lv, boom=boom, k_bs=kbs, k_cyl=kcy)
                f, Phi, K, M = ms.modes(nmodes=10)
                cls = ms.classify(Phi, M)
                fa = [float(x) for x, c in zip(f, cls) if c["FA"] > 0.5]
                la = [float(x) for x, c in zip(f, cls) if c["LAT"] > 0.5]
                to = [float(x) for x, c in zip(f, cls) if c["TOR"] > 0.5]
                rows.append({"k_bs_N_m": kbs, "k_cyl_N_m": kcy, "fore_aft_Hz": fa[:2], "lateral_Hz": la[:2],
                             "torsion_Hz": to[:1],
                             "backstay_tension_kN": ms.spring_forces["backstay"][0] / 1e3})
        sweep[lv] = rows
    mo["supported_sweep"] = sweep
    # convenience table: FA f1 vs k_bs (k_cyl nominal), LAT f1 vs k_cyl (k_bs nominal)
    tab = {}
    for lv in LEVELS:
        fa_row = {f"{kbs:.3g}": next(x for x in sweep[lv] if x["k_bs_N_m"] == kbs and x["k_cyl_N_m"] == K_CYL_SWEEP[-2])["fore_aft_Hz"]
                  for kbs in K_BS_SWEEP}
        la_row = {f"{kcy:.3g}": next(x for x in sweep[lv] if x["k_cyl_N_m"] == kcy and x["k_bs_N_m"] == K_BS_NOM)["lateral_Hz"]
                  for kcy in K_CYL_SWEEP}
        tab[lv] = {"fore_aft_f1_f2_vs_k_bs (k_cyl 1e9)": fa_row, "lateral_f1_f2_vs_k_cyl (k_bs 4.177e8)": la_row}
    mo["summary_table"] = tab
    # nominal cases with the static state
    nomc = {}
    cases = {"upper (k_bs 4.177e8, k_cyl 2.1e8)": (K_BS_NOM, K_CYL_NOM),
             "low (k_bs 1e8, k_cyl 3e7)": (K_BS_LOW, K_CYL_LOW),
             "rigid supports": (1e12, 1e12)}
    for lv in LEVELS:
        for cname, (kbs, kcy) in cases.items():
            ms = MastSystem(mast, lv, boom=boom, k_bs=kbs, k_cyl=kcy)
            f, Phi, K, M = ms.modes(nmodes=10)
            cls = ms.classify(Phi, M)
            u = ms.u_static
            jt = ms.nn - 1
            nomc.setdefault(lv, {})[cname] = {
                "f_Hz": f[:8].tolist(), "families": [max(c, key=c.get) for c in cls[:8]],
                "static_top_node_ux_uy_mm": (u[6 * jt:6 * jt + 2] * 1e3).tolist(),
                "static_top_node_ry_rx_deg": [u[6 * jt + 4] * DEG, u[6 * jt + 3] * DEG],
                "static_auger_com_dx_dy_dz_mm": (u[ms.i_aug:ms.i_aug + 3] * 1e3).tolist(),
                "backstay_tension_kN": ms.spring_forces["backstay"][0] / 1e3,
                "boom_roll_static_deg": u[ms.i_boom] * DEG,
                "max_compression_kN": float(-ms.N_elem.min()) / 1e3,
                "P_delta_effect_on_f1_pct": 100 * (f[0] / ms.modes(geometric=False, nmodes=1)[0][0] - 1),
            }
    mo["nominal_cases"] = nomc
    res["mast_only"] = mo

    # ---------------------------------------------------------------- 2. coupled with the L1 body
    cp = {}
    l1_band = {}
    for lv in LEVELS:
        L1f = ref["chrono_test_references"]["L1_rigid_motor_lumped_contact"]["levels"][lv]["f_undamped_Hz"]
        l1_band[lv] = L1f
    beta_band = ref.get("L1_beta_sensitivity_top")
    coupled_out = {}
    for lv in LEVELS:
        l1 = l1_setup(p, geo, ref, lv)
        ent = {}
        for cname, (kbs, kcy) in list(cases.items()) + [("upper bs, low cyl", (K_BS_NOM, K_CYL_LOW)),
                                                         ("low bs, nominal cyl", (K_BS_LOW, K_CYL_NOM))]:
            ms = MastSystem(mast, lv, boom=boom, k_bs=kbs, k_cyl=kcy)
            f, Phi, share, M, K, _ = coupled_modes(ms, l1, nmodes=14)
            tr = mac_track(l1, Phi, M)
            fm = ms.modes(nmodes=4)[0]
            beta = 2 * ZETA_MAST / (2 * np.pi * fm[0])
            C = damping_coupled(ms, l1, beta)
            fd, zd = dm.complex_modes(M, K, C)
            ent[cname] = {
                "mast_only_f_Hz": fm[:4].tolist(),
                "coupled_f_Hz": f.tolist(),
                "mast_strain_energy_share": share,
                "coupled_damped_f_Hz": fd[:14].tolist(), "coupled_zeta": zd[:14].tolist(),
                "rigid_mode_tracking (rigid i, f_rigid, coupled j, MAC)": tr,
                "rocking_shift_pct (1st, 2nd)": [100 * (f[tr[0][2]] / tr[0][1] - 1), 100 * (f[tr[1][2]] / tr[1][1] - 1)],
                "beta_mast_s": beta,
            }
        coupled_out[lv] = ent
    cp["lifted_L1"] = coupled_out
    cp["L1_rigid_f_Hz"] = l1_band
    cp["L1_beta_sensitivity_top"] = beta_band
    # sweep of the coupled 1st/2nd rocking against k_bs / k_cyl (top) for the overlap picture
    sw = []
    l1 = l1_setup(p, geo, ref, "top")
    for kbs in K_BS_SWEEP:
        for kcy in K_CYL_SWEEP:
            ms = MastSystem(mast, "top", boom=boom, k_bs=kbs, k_cyl=kcy)
            f, Phi, share, M, K, _ = coupled_modes(ms, l1, nmodes=10)
            tr = mac_track(l1, Phi, M)
            sw.append({"k_bs": kbs, "k_cyl": kcy, "f_coupled_Hz": f[:8].tolist(), "mast_share": share[:8],
                       "rock1_f_Hz": float(f[tr[0][2]]), "rock2_f_Hz": float(f[tr[1][2]]),
                       "rock1_mac": tr[0][3], "rock2_mac": tr[1][3]})
    cp["top_sweep"] = sw
    # crawler on the floor (legs retracted, layout D), top
    cr = {}
    for lv in ("top",):
        l1c = l1_setup(p, geo, ref, lv, lifted=False)
        for cname, (kbs, kcy) in cases.items():
            ms = MastSystem(mast, lv, boom=boom, k_bs=kbs, k_cyl=kcy)
            M, K, _ = coupled(ms, l1c)
            w2, Phi = eigh(K, M, subset_by_index=[0, 13])
            f = np.sqrt(np.clip(w2, 0, None)) / (2 * np.pi)
            share = [strain_share(ms, l1c, Phi[:, j]) for j in range(14)]
            frig = np.sqrt(np.clip(eigh(l1c["K6"], l1c["M6"], eigvals_only=True), 0, None)) / (2 * np.pi)
            cr[cname] = {"coupled_f_Hz": f.tolist(), "mast_share": share, "rigid_f_Hz": np.sort(frig).tolist(),
                         "active_crawler_spheres": l1c["n_active"]}
    cp["crawler_on_floor_top"] = cr
    res["coupled"] = cp

    # ---------------------------------------------------------------- 3. static effects (coupled statics)
    st = {}
    for lv in LEVELS:
        l1 = l1_setup(p, geo, ref, lv)
        for cname, (kbs, kcy) in cases.items():
            ms = MastSystem(mast, lv, boom=boom, k_bs=kbs, k_cyl=kcy)
            M, K, _ = coupled(ms, l1)
            rhs = np.zeros(K.shape[0]); rhs[6:] = ms.f_g[ms.free]
            q = np.linalg.solve(K, rhs)
            dF = -l1["kv"] * (l1["AZ"] @ q[:6])
            u = np.zeros(ms.n); u[ms.free] = q[6:]
            mtot = l1["body"].mass
            dx = sum(m * (ms.pmap(a, c)[:3] @ u) for (nm, m, c, I3, a) in ms.masses) / mtot
            jt = ms.nn - 1
            st.setdefault(lv, {})[cname] = {
                "body_roll_pitch_change_deg": (q[3:5] * DEG).tolist(),
                "pad_force_change_N (FL, FR, RL, RR)": dF.tolist(),
                "composite_com_shift_mm": (dx * 1e3).tolist(),
                "mast_top_lean_rel_body_deg (pitch-like ry, roll-like rx)": [u[6 * jt + 4] * DEG, u[6 * jt + 3] * DEG],
                "mast_top_deflection_rel_body_mm (x, y)": (u[6 * jt:6 * jt + 2] * 1e3).tolist(),
            }
    res["static_effects"] = st

    # ---------------------------------------------------------------- 4. dynamic transients (top, lifted, linear)
    dyn = {"leg_stop": {}, "crawler_release_proxy": {}}
    l1 = l1_setup(p, geo, ref, "top")
    l1c = l1_setup(p, geo, ref, "top", lifted=False)
    T_rel = 15.584 - 15.050   # s: first pad touch -> crawler fully off (dynamics_model.md 3.7, layout D, dynamic)
    sims = {}
    rig = (l1["M6"], l1["K6"], l1["C6"])
    for key, fun in (("leg_stop", lambda s_: simulate_stop(s_, l1, geo)),
                     ("crawler_release_proxy", lambda s_: simulate_release(s_, l1, l1c, geo, T_rel))):
        rs = fun(rig)
        dyn[key]["rigid_L1"] = stop_metrics(rs); dyn[key]["rigid_L1"]["n_modes"] = rs["n_modes"]
        sims[(key, "rigid L1")] = rs
    worst = min(sw, key=lambda x: min(x["rock1_f_Hz"] / l1_band["top"][0], x["rock2_f_Hz"] / l1_band["top"][1]))
    dyn_cases = dict(cases)
    dyn_cases["tuned (mast-only FA f1 ~ rocking 2, LAT f1 ~ rocking 1: k_bs 6e8, k_cyl 1e8)"] = (6.0e8, 1.0e8)
    dyn_cases[f"extreme sweep point (k_bs {worst['k_bs']:.3g}, k_cyl {worst['k_cyl']:.3g})"] = (worst["k_bs"], worst["k_cyl"])
    for cname, (kbs, kcy) in dyn_cases.items():
        ms = MastSystem(mast, "top", boom=boom, k_bs=kbs, k_cyl=kcy)
        M, K, _ = coupled(ms, l1)
        fm = ms.modes(nmodes=2)[0]
        C = damping_coupled(ms, l1, 2 * ZETA_MAST / (2 * np.pi * fm[0]))
        for key, fun in (("leg_stop", lambda s_: simulate_stop(s_, l1, geo)),
                         ("crawler_release_proxy", lambda s_: simulate_release(s_, l1, l1c, geo, T_rel))):
            rs = fun((M, K, C))
            mt = stop_metrics(rs); mt["n_modes"] = rs["n_modes"]; mt["mast_only_f_Hz"] = fm.tolist()
            r0 = dyn[key]["rigid_L1"]
            mt["ratio_pad_force_dev_vs_rigid"] = (mt["max_abs_pad_force_dev_from_quasi_static_N"]
                                                  / r0["max_abs_pad_force_dev_from_quasi_static_N"])
            dyn[key][cname] = mt
            sims[(key, cname)] = rs
    dyn["model"] = ("linear L1 (lifted, top) with/without the flexible mast, modal (< 300 Hz), DOP853 rtol 1e-9 "
                    "piecewise between kinks. leg_stop: legs extend at v_max and stop at e_op (rear 17.245 s, front "
                    "17.696 s from motor start), exact steady ramp state 3 s before the first stop (rigid case "
                    "reproduces reference.json residual pitch 0.01847 deg). crawler_release_proxy: layout-D crawler "
                    "floor load (static at legs 0, total = W) applied upward to the lifted body and ramped to 0 over "
                    f"{T_rel:.3f} s (first touch -> crawler off), legs locked; a proxy of the V4 hand-over kinks, not "
                    "the V4 model. IMU C1 accelerometer tilt phi + a_y/g, theta - a_x/g; filter 2 x first order tau 0.5 s")
    dyn["V4_reference_dynamic_deviation_kN"] = 23.2
    dyn["V4_reference_peak_pad_force_kN"] = 141.0
    res["dynamic_top"] = dyn

    # ---------------------------------------------------------------- 5. control-band relations
    cb = {}
    for fz in (1.5, 2.0, 2.4, 2.74, 3.0, 3.58, 3.85, 5.0):
        wt = 2 * np.pi * fz * TAU_FILTER
        Hf = 1.0 / (1.0 + wt ** 2)
        cb[f"{fz:g} Hz"] = {"filter_gain": Hf, "loop_gain_est (fc/f x filter)": F_CROSSOVER_HZ / fz * Hf,
                            "samples_per_period_at_20ms": 1.0 / (fz * 0.02)}
    cb["note"] = ("loop gain estimate = crossover 0.064 Hz / f (integrating plant) x filter gain; multiply by the "
                  "resonant IMU participation 1/(2 zeta) x (IMU tilt share) for a mode. 20 ms loop: Nyquist 25 Hz")
    res["control_band"] = cb
    res["meta"]["runtime_s"] = time.perf_counter() - t_start

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(r(res), f, indent=1, ensure_ascii=False)
    print(f"wrote {OUT_JSON} ({res['meta']['runtime_s']:.1f} s)")
    if not args.no_plots:
        plots(res, sims)


def plots(res, sims):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(1, 3, figsize=(15, 4.6))
    tab = res["mast_only"]["summary_table"]
    band = res["coupled"]["L1_rigid_f_Hz"]
    cols = {"top": "#d1495b", "middle": "#00798c", "bottom": "#edae49"}
    for lv in LEVELS:
        fa = tab[lv]["fore_aft_f1_f2_vs_k_bs (k_cyl 1e9)"]
        ks = [float(k) for k in fa]; f1 = [v[0] for v in fa.values()]
        axs[0].semilogx(ks, f1, "o-", color=cols[lv], label=f"{lv}: mast-only FA f1")
        la = tab[lv]["lateral_f1_f2_vs_k_cyl (k_bs 4.177e8)"]
        ks = [float(k) for k in la]; f1 = [v[0] for v in la.values()]
        axs[1].semilogx(ks, f1, "s-", color=cols[lv], label=f"{lv}: mast-only LAT f1")
    for ax in axs[:2]:
        for lv in LEVELS:
            ax.axhline(band[lv][0], color=cols[lv], ls=":", lw=1)
            ax.axhline(band[lv][1], color=cols[lv], ls="--", lw=1)
        ax.axhspan(1.53, 3.94, color="0.85", zorder=0, label="L1 rocking band (beta 0.69-1.6 GPa, 3 levels)")
        ax.set_ylabel("frequency [Hz]"); ax.grid(True, which="both", alpha=0.3); ax.legend(fontsize=7)
    axs[0].set_xlabel("backstay axial stiffness k_bs [N/m] (k_cyl 1e9)")
    axs[1].set_xlabel("boom cylinder stiffness k_cyl [N/m], lever 1 m (k_bs 4.18e8)")
    axs[0].set_title("Fore-aft mast f1 (body fixed); dotted/dashed = L1 rocking 1/2")
    axs[1].set_title("Lateral mast f1 (body fixed)")
    sw = res["coupled"]["top_sweep"]
    kb = sorted(set(x["k_bs"] for x in sw))
    for kc, mk in ((1e7, "v"), (2.1e8 if False else 1e8, "o"), (1e12, "^")):
        r1 = [next(x for x in sw if x["k_bs"] == k and x["k_cyl"] == kc)["rock1_f_Hz"] for k in kb]
        r2 = [next(x for x in sw if x["k_bs"] == k and x["k_cyl"] == kc)["rock2_f_Hz"] for k in kb]
        axs[2].semilogx(kb, r1, mk + "-", color="#30638e", label=f"rocking 1 (k_cyl {kc:.0e})")
        axs[2].semilogx(kb, r2, mk + "--", color="#d1495b", label=f"rocking 2 (k_cyl {kc:.0e})")
    axs[2].axhline(band["top"][0], color="#30638e", lw=0.8, ls=":")
    axs[2].axhline(band["top"][1], color="#d1495b", lw=0.8, ls=":")
    axs[2].set_xlabel("k_bs [N/m]"); axs[2].set_ylabel("coupled frequency [Hz]")
    axs[2].set_title("Top: coupled rocking modes (dotted = rigid L1)"); axs[2].grid(True, which="both", alpha=0.3)
    axs[2].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "mast_bending_check_frequencies.png", dpi=130)
    plt.close(fig)

    fig, axs = plt.subplots(3, 2, figsize=(14, 9), sharex="col")
    names = ["rigid L1", "upper (k_bs 4.177e8, k_cyl 2.1e8)", "low (k_bs 1e8, k_cyl 3e7)",
             "tuned (mast-only FA f1 ~ rocking 2, LAT f1 ~ rocking 1: k_bs 6e8, k_cyl 1e8)"]
    colors = ["#222222", "#d1495b", "#00798c", "#edae49"]
    for c_, key in enumerate(("leg_stop", "crawler_release_proxy")):
        for nm, col in zip(names, colors):
            rs = sims[(key, nm)]
            t = rs["T"] - rs["t_last"]
            lw = 1.8 if nm == "rigid L1" else 1.0
            lab = nm.split(" (")[0] if nm != "rigid L1" else nm
            j = int(np.argmax(np.abs(rs["dF"]).max(axis=1)))
            axs[0, c_].plot(t, rs["dF"][j] / 1e3, color=col, lw=lw, label=f"{lab} ({['FL', 'FR', 'RL', 'RR'][j]})")
            axs[1, c_].plot(t, np.degrees(rs["true"][1] - rs["app_qs"][1]), color=col, lw=lw, label=lab)
            axs[2, c_].plot(t, np.degrees(rs["filt"][1] - rs["app_qs"][1]), color=col, lw=lw, label=lab)
        axs[0, c_].set_ylabel("pad force - quasi-static [kN]")
        axs[1, c_].set_ylabel("true body pitch dev [deg]")
        axs[2, c_].set_ylabel("IMU C1 pitch, filtered (2 x tau 0.5 s) [deg]")
        axs[2, c_].set_xlabel("time from the last kink [s]" if key != "leg_stop" else "time from the last leg stop [s]")
        axs[2, c_].set_ylim(-0.03, 0.03)
        for ax in axs[:, c_]:
            ax.grid(True, alpha=0.3)
        axs[0, c_].legend(fontsize=7)
    axs[0, 0].set_title("Top, legs stop at e_op (V4 schedule)")
    axs[0, 1].set_title("Top, crawler hand-over proxy (load ramp 0.534 s)")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "mast_bending_check_transients.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    main()
