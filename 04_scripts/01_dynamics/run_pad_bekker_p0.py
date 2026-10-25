"""P0: reduced Bekker series model for the pad-area variants on soil (no Chrono).

00_docs/01_dynamics/dynamics_model.md 5.31 (rev. 45), plan 5.30.6 P0, user decisions U-PAD-1..6 (2026-10-25).
Output 06_analysis/00_dynamics/pad_bekker_p0.json (+ pad_bekker_p0_paths.png, pad_bekker_p0_v16.png).
Run: conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_pad_bekker_p0.py   (few minutes, 8 workers)

Model (quasi-static, small angles, rigid body = superstructure level + 4 moving parts)
  q = [uz, phi, theta] about the body-frame origin (up m, rad, rad); vertical displacement of a body point
      at (x, y): uz + y phi - x theta  (pitch > 0 = nose down, roll > 0 = left side up).
  leg i: motor extension e_i (state), series spring k_leg_i(e) = series(k_oil(e) + k_rod_side, k_rod, k_frame)
      (locked-leg stiffness without concrete), pad bottom (rigid leg) z = z_ret_i - e_i + (A q)_i.
  soil element (pad = one element of area A_pad, Bekker width b = 2A/perimeter; crawler = SCM-type node grid
      under the C envelope boxes, 20 mm): SCM normal law of Chrono 10 (SCMTerrain.cpp ComputeInternalForces):
        elastic trial  p_el = K (s - s_p)                (s_p = plastic sinkage)
        if p_el > p_y: p = (k_c / b + k_phi) s^n,  p_y = p,  s_p = s - p / K   (loading / plastic branch)
        else         : p = max(p_el, 0)                                         (elastic un/re-loading)
      damping R is left out (quasi-static); crawler b = 2 A_hull / perimeter_hull of the contact nodes per
      track (Chrono: convex hull of the patch node points, SCMTerrain.cpp ~1366-1374).
  surface: SCM surface at the crawler block-bottom plane (ground.crawler_bottom_z_m + 0.004, 3.11.2).
  levelling law: IDEALISED kinematic law (not C2): 10 Hz, output delay 1 period, heave P on the stroke-based
      clearance estimate (C2 formula, target 50 mm), attitude PI on a 2 x 0.8 s low-passed true attitude,
      twist P on n^T F_cyl (dead band 2 kN), crawler zone (no leg retracts before the lifted latch),
      speed scaling to v_max, increment limit 0.25 v_max per period. No F_min guard / re-approach (the
      minimum F_cyl is recorded instead).
Units SI; gravity (0, 0, -g), g from YAML meta.gravity_m_s2.
"""
from __future__ import annotations

import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402

OUT = ROOT / "06_analysis" / "00_dynamics" / "pad_bekker_p0.json"
FIG_PATH = ROOT / "06_analysis" / "00_dynamics" / "pad_bekker_p0_paths.png"
FIG_V16 = ROOT / "06_analysis" / "00_dynamics" / "pad_bekker_p0_v16.png"
P = dm.load_params()
GEO = dm.geometry_from_params(P)
G = GEO.g
LEGS = dm.LEG_NAMES
L1 = P["contact"]["rigid_floor"]["L1"]
DER = L1["derivation"]
ZF = float(P["ground"]["crawler_bottom_z_m"])
Z_SURF = ZF + 0.004          # SCM surface = crawler block-bottom plane (3.11.2, ASSUMPTION 4 mm pads pressed in)
F_MIN = float(P["control"]["F_min_cylinder_N"])
V_MAX = float(P["actuator"]["max_speed_m_s"])
STROKE = float(P["actuator"]["stroke_m"])
END_MARGIN = 0.6848          # stroke end-margin reference (CLAUDE.md)
SENSOR_END = 0.6948
K_ELASTIC = 2.0e8            # ASSUMPTION: SCM elastic K [Pa/m] (S0 demo level, 3.11.3)
GAMMA = 18e3                 # ASSUMPTION: soil unit weight [N/m^3] for bearing capacity
CLEAR_TARGET = 0.05          # YAML simulation.crawler_clearance_m / C2 heave target
S_REG_CRAWLER = 1e-4         # ASSUMPTION: crawler-node Bekker law replaced by its secant below 0.1 mm (solver regularisation)

# ------------------------------------------------------------------ pad variants (read only)
PV_PATH = ROOT / "02_params" / "pad_variants.json"
FALLBACK = {"330": dict(area=0.1071, perim=1.24970563), "250": dict(area=0.0607, perim=0.929705627)}


def load_pad_variants():
    """Polygons, A, b per variant from 02_params/pad_variants.json; fallback = 5.30.1 constants."""
    out = {}
    src = "fallback 5.30.1 constants"
    if PV_PATH.exists():
        pv = json.loads(PV_PATH.read_text(encoding="utf-8"))
        if not pv.get("failures"):
            src = f"{PV_PATH.relative_to(ROOT)} (generated {pv.get('generated')})"
            for name, v in pv["variants"].items():
                out[v["label"]] = {"name": name, "legs": {
                    leg: {"area": float(d["bottom_area_m2"]), "perim": float(d["perimeter_m"]),
                          "b": float(d["bekker_b_m"]), "B_sq": float(d["equivalent_square_side_m"]),
                          "poly": np.array(d["polygon_xy_m"], float)} for leg, d in v["legs"].items()}}
    if not out:
        for lab, types in (("A", ["330"] * 4), ("B", ["330", "330", "250", "250"])):
            out[lab] = {"name": {"A": "cad330", "B": "dwg_rear250"}[lab], "legs": {}}
            for leg, t in zip(LEGS, types):
                a, pr = FALLBACK[t]["area"], FALLBACK[t]["perim"]
                out[lab]["legs"][leg] = {"area": a, "perim": pr, "b": 2 * a / pr, "B_sq": math.sqrt(a), "poly": None}
    return out, src


PV, PV_SRC = load_pad_variants()

# ------------------------------------------------------------------ soils (literature, ASSUMPTION for the project)
# Wong, Theory of Ground Vehicles (Table 2.3, Bekker values). kc [N/m^(n+1)], kphi [N/m^(n+2)], c [Pa], phi [deg].
# heavy clay 25 % and LETE sand are the sets already used in 3.11.2 / 5.30.4; lean clay 22 % is a new transcription
# (to be checked against the original table).
SOILS = {
    "heavy_clay_25": dict(n=0.13, kc=12.70e3, kphi=1555.95e3, c=68.95e3, phi=34.0, role="J1",
                          src="Wong Table 2.3, heavy clay (WES) 25 % moisture"),
    "lean_clay_22": dict(n=0.20, kc=16.43e3, kphi=1724.69e3, c=68.95e3, phi=20.0, role="J2 (boundary)",
                         src="Wong Table 2.3, lean clay (WES) 22 % moisture (transcription, check)"),
    "LETE_sand": dict(n=0.79, kc=102e3, kphi=5301e3, c=1.3e3, phi=31.1, role="example soft (sensitivity)",
                      src="Wong Table 2.3, LETE sand"),
}
# screening-only sets (bearing check, not run): Wong Table 2.3 values as used in 3.11.2 / 5.30.4
SCREEN = {
    "dry_sand": dict(n=1.1, kc=0.99e3, kphi=1528.43e3, c=1.04e3, phi=28.0),
    "clayey_soil_38": dict(n=0.5, kc=13.19e3, kphi=692.15e3, c=4.14e3, phi=13.0),
    "sandy_loam_Michigan_23": dict(n=0.4, kc=11.42e3, kphi=808.96e3, c=9.65e3, phi=35.0),
    "lean_clay_32": dict(n=0.15, kc=1.52e3, kphi=119.61e3, c=13.79e3, phi=11.0),
    "heavy_clay_40": dict(n=0.11, kc=1.84e3, kphi=103.27e3, c=20.69e3, phi=6.0),
}


def bearing_drained(c, phi_deg, B):
    """Surface square footing, Vesic factors, s_c = 1 + Nq/Nc, s_gamma = 0.6 (same as 5.30.4)."""
    ph = math.radians(phi_deg)
    if ph < 1e-9:
        return 5.14 * 1.2 * c
    Nq = math.exp(math.pi * math.tan(ph)) * math.tan(math.pi / 4 + ph / 2) ** 2
    Nc = (Nq - 1) / math.tan(ph)
    Ng = 2 * (Nq + 1) * math.tan(ph)
    return c * Nc * (1 + Nq / Nc) + 0.5 * GAMMA * B * Ng * 0.6


def bearing_undrained(c):
    """phi_u = 0, c taken as c_u, square surface footing: (pi + 2) 1.2 c."""
    return (math.pi + 2) * 1.2 * c


# ------------------------------------------------------------------ body, legs
LEVELS = ("top", "middle", "bottom")
E_OP = np.array([DER["operating_extension_m"][n] for n in LEGS])
K_OIL_OP = np.array([DER["k_oil_N_m"][n] for n in LEGS])
K_RS = np.array([DER["k_rod_side_N_m"][n] for n in LEGS])
K_ROD = np.array([DER["k_rod_N_m"][n] for n in LEGS])
K_FR = dm.ASSUMPTIONS["frame_bracket_stiffness_N_m"]
DEAD = dm.ASSUMPTIONS["oil_dead_length_m"]
K_SLAB = dm.k_concrete_westergaard()["k_slab_N_m"]
KN_YAML = np.array([L1["kn_per_pad_N_m"][n] for n in LEGS])
KT_YAML = np.array([L1["kt_per_pad_N_m"][n] for n in LEGS])
K_NOM = float(np.mean(KN_YAML))
ROD_W = GEO.rod_mass * G
PAD_XY = GEO.pad_xy
A_PAD = dm.support_matrix(PAD_XY)
N_TW = dm.twist_vector(PAD_XY)
CR_BOX = ((-1.840, 1.844), (-1.366, 1.366))   # C2 CRAWLER_XY_BOX_M (= dyn_model crawler box)
CORNERS = np.array([[CR_BOX[0][0], CR_BOX[1][0]], [CR_BOX[0][0], CR_BOX[1][1]],
                    [CR_BOX[0][1], CR_BOX[1][0]], [CR_BOX[0][1], CR_BOX[1][1]]])
PLANE_FIT = np.linalg.pinv(np.column_stack([np.ones(4), PAD_XY]))   # z = c0 + c1 x + c2 y


def k_oil(e):
    return K_OIL_OP * (DEAD + E_OP) / (DEAD + np.asarray(e, float))


def k_leg(e):
    return dm.series(k_oil(e) + K_RS, K_ROD, K_FR)


def body(level):
    b = dm.body_with_rods(P, GEO, level, np.zeros(4))
    return b


# ------------------------------------------------------------------ crawler C envelope (copy of 3.11.2 geometry)
SHEET = json.load(open(ROOT / "01_cad/06_brep/derived/crawler/crawler_ground_sheet.json", encoding="utf-8"))
SG = SHEET["shoe_geometry"]
BLK_X = float(SG["block_bottom_plane_mm (x, y)"][0]) * 1e-3
BLK_Y0, BLK_Y1 = SHEET["rectangles_body_m"]["left"]["block_bottom_flat"]["y_m"]
DOM = SHEET["scm_active_domain"]["variants"]["full (10 flat + 6 end shoes per track)"]["boxes"]["left"]
END_ST = [float(e["station_x_body_m"]) for e in SHEET["end_shoes_left"]]
END_GAP = [float(e["gap_mm"]) * 1e-3 for e in SHEET["end_shoes_left"]]
_fr = np.polyfit([x for x in END_ST if x > 0], [g for x, g in zip(END_ST, END_GAP) if x > 0], 1)
_re = np.polyfit([-x for x in END_ST if x < 0], [g for x, g in zip(END_ST, END_GAP) if x < 0], 1)
RAMP = {"front": dict(slope=float(_fr[0]), x0=float(-_fr[1] / _fr[0])), "rear": dict(slope=float(_re[0]), x0=float(-_re[1] / _re[0]))}
H_GRID = 0.02


def crawler_nodes(h=H_GRID):
    """C shape (3 boxes per track) bottom height above the block-bottom plane on the left-track node grid."""
    xs = np.arange(DOM["x_m"][0], DOM["x_m"][1], h)
    ys = np.arange(DOM["y_m"][0], DOM["y_m"][1], h)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    hb = np.full(X.shape, np.inf)
    xr0, xf0 = -RAMP["rear"]["x0"], RAMP["front"]["x0"]
    boxes = [(xr0, xf0, 0.0, 0.0, 0.0),
             (xf0, max(END_ST) + BLK_X / 2, 0.0, xf0, RAMP["front"]["slope"]),
             (min(END_ST) - BLK_X / 2, xr0, 0.0, xr0, -RAMP["rear"]["slope"])]
    for (x0, x1, h0, xr, s) in boxes:
        m = (X >= x0) & (X <= x1) & (Y >= BLK_Y0) & (Y <= BLK_Y1)
        hb = np.where(m, np.minimum(hb, h0 + s * (X - xr)), hb)
    return X, Y, hb


class Soil:
    """SCM normal law with plastic memory, vectorised over elements (pads or nodes)."""

    def __init__(self, n, kc, kphi, K, s_reg=0.0):
        self.n, self.kc, self.kphi, self.K, self.s_reg = n, kc, kphi, K, s_reg

    def p(self, s, sp, py, coef):
        el = self.K * (s - sp)
        sc = np.maximum(s, 0.0)
        sr = self.s_reg
        lin = sc < sr                       # ASSUMPTION (crawler nodes): secant line below s_reg (n < 1 regularisation)
        bek = np.where(lin, coef * sr ** self.n * sc / max(sr, 1e-300), coef * sc ** self.n)
        load = el > py
        p = np.where(s <= sp, 0.0, np.where(load, bek, el))
        with np.errstate(divide="ignore", invalid="ignore"):
            dbek = np.where(lin, coef * sr ** (self.n - 1) if sr > 0 else self.K,
                            np.where(sc > 0, self.n * coef * sc ** (self.n - 1), self.K))
        dp = np.where(s <= sp, 0.0, np.where(load, np.minimum(dbek, self.K), self.K))
        return p, dp, load


class Model:
    """Quasi-static machine on soil (pads + crawler)."""

    def __init__(self, level, variant, soil_name, crawler_grid="hull"):
        self.level, self.variant, self.soil_name = level, variant, soil_name
        b = body(level)
        self.W = b.mass * G
        self.cg = b.com[:2]
        self.w = np.array([self.W, self.W * self.cg[1], -self.W * self.cg[0]])
        legs = PV[variant]["legs"]
        self.a_pad = np.array([legs[n]["area"] for n in LEGS])
        self.b_pad = np.array([legs[n]["b"] for n in LEGS])
        if soil_name == "rigid":
            # concrete slab spring under each pad (k_slab, elastic), crawler on a linear Winkler bed with the YAML
            # crawler kn_total spread over the flat C boxes (elastic, no plasticity). Baseline in the same model.
            kfl = float(P["contact"]["crawler"]["kn_total_N_m"]) / (2 * (RAMP["front"]["x0"] + RAMP["rear"]["x0"]) * (BLK_Y1 - BLK_Y0))
            self.pad_soil = Soil(1.0, 0.0, 1.0, 1.0)
            self.pad_coef = K_SLAB / self.a_pad
            self.pad_soil.K = None
            self.pad_K = K_SLAB / self.a_pad
            self.cr_soil = Soil(1.0, 0.0, kfl, kfl)
        else:
            s = SOILS[soil_name]
            self.pad_soil = Soil(s["n"], s["kc"], s["kphi"], K_ELASTIC)
            self.pad_coef = s["kc"] / self.b_pad + s["kphi"]
            self.pad_K = np.full(4, K_ELASTIC)
            self.cr_soil = Soil(s["n"], s["kc"], s["kphi"], K_ELASTIC, s_reg=S_REG_CRAWLER)
        self.crawler_grid = crawler_grid
        X, Y, hb = crawler_nodes()
        self.cX, self.cY, self.chb = X, Y, hb
        ok = np.isfinite(hb)
        self.ix, self.iy = np.nonzero(ok)
        x, y, h = X[ok], Y[ok], hb[ok]
        self.nx = x.size
        self.cx = np.concatenate([x, x])
        self.cy = np.concatenate([y, -y])
        self.chb_flat = np.concatenate([h, h])
        self.A_cr = np.column_stack([np.ones(2 * self.nx), self.cy, -self.cx])
        self.c_sp = np.zeros(2 * self.nx)
        self.c_py = np.zeros(2 * self.nx)
        self.p_sp = np.zeros(4)
        self.p_py = np.zeros(4)
        self.e = np.zeros(4)
        self.q = np.zeros(3)
        self.shape = X.shape

    # -------------------------------------------------- pads
    def pad_p(self, s):
        if self.soil_name == "rigid":
            el = self.pad_K * (s - self.p_sp)
            p = np.where(s <= self.p_sp, 0.0, el)
            dp = np.where(s <= self.p_sp, 0.0, self.pad_K)
            return p, dp, np.zeros(4, bool)
        sl = self.pad_soil
        el = sl.K * (s - self.p_sp)
        sc = np.maximum(s, 0.0)
        bek = self.pad_coef * sc ** sl.n
        load = el > self.p_py
        p = np.where(s <= self.p_sp, 0.0, np.where(load, bek, el))
        with np.errstate(divide="ignore", invalid="ignore"):
            dbek = np.where(sc > 0, sl.n * self.pad_coef * sc ** (sl.n - 1), sl.K)
        dp = np.where(s <= self.p_sp, 0.0, np.where(load, np.minimum(dbek, sl.K), sl.K))
        return p, dp, load

    def pads(self, q, e):
        """Pad sinkage s, contact force F (up), tangent dF/dd and loading flag for the rigid-leg penetration d."""
        kl = k_leg(e)
        d = Z_SURF - (GEO.pad_z_retracted - e + A_PAD @ q)
        lo = self.p_sp.copy()
        hi = np.maximum(d, lo)
        con = d > self.p_sp
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            p, _, _ = self.pad_p(mid)
            f = kl * (d - mid) - self.a_pad * p
            lo = np.where(f > 0, mid, lo)
            hi = np.where(f > 0, hi, mid)
        s = np.where(con, 0.5 * (lo + hi), d)
        p, dp, load = self.pad_p(s)
        F = np.where(con, self.a_pad * p, 0.0)
        ka = self.a_pad * dp
        kt = np.where(con, kl * ka / np.maximum(kl + ka, 1e-30), 0.0)
        return s, F, kt, load & con

    # -------------------------------------------------- crawler
    def patch_b(self, con):
        """Bekker b per track: 2 A / perimeter of the contact nodes (hull = Chrono, manhattan = 3.11.2 model)."""
        bs = []
        for t in range(2):
            m = con[t * self.nx:(t + 1) * self.nx]
            if m.sum() < 3:
                bs.append(np.inf)
                continue
            grid = np.zeros(self.shape, bool)
            grid[self.ix[m], self.iy[m]] = True
            if self.crawler_grid == "manhattan":
                pad = np.pad(grid, 1)
                c = pad[1:-1, 1:-1]
                edges = (c & ~pad[:-2, 1:-1]).sum() + (c & ~pad[2:, 1:-1]).sum() + (c & ~pad[1:-1, :-2]).sum() + (c & ~pad[1:-1, 2:]).sum()
                bs.append(2 * grid.sum() * H_GRID ** 2 / (edges * H_GRID))
                continue
            anyc = grid.any(axis=0)
            cols = np.nonzero(anyc)[0]
            first = grid.argmax(axis=0)[cols]
            last = grid.shape[0] - 1 - grid[::-1].argmax(axis=0)[cols]
            key = (t, first.tobytes(), last.tobytes(), cols.tobytes())
            cache = self.__dict__.setdefault("_bcache", {})
            if key in cache:
                bs.append(cache[key])
                continue
            pts = np.unique(np.vstack([np.column_stack([self.cX[first, cols], self.cY[first, cols]]),
                                       np.column_stack([self.cX[last, cols], self.cY[last, cols]])]), axis=0)
            try:
                hull = ConvexHull(pts)
                area, per = hull.volume, hull.area
            except Exception:  # degenerate (collinear) patch: Chrono sets 1/b = 0 for area < 1e-6
                area, per = 0.0, 1.0
            bval = 2 * area / per if area > 1e-6 else np.inf
            if len(cache) > 20000:
                cache.clear()
            cache[key] = bval
            bs.append(bval)
        return np.array(bs)

    def crawler(self, q):
        s = -(self.A_cr @ q + self.chb_flat)
        con = s > self.c_sp
        if not con.any():
            return s, np.zeros_like(s), np.zeros_like(s), con, None
        sl = self.cr_soil
        if sl.kc != 0.0:
            b = self.b_fix if getattr(self, "b_fix", None) is not None else self.patch_b(con)
            coef = sl.kc / np.repeat(b, self.nx) + sl.kphi
        else:
            b = None
            coef = np.full(s.size, sl.kphi)
        p, dp, load = sl.p(s, self.c_sp, self.c_py, coef)
        a = H_GRID ** 2
        return s, p * a, dp * a, load & con, (b, coef)

    # -------------------------------------------------- equilibrium
    def settle(self, q0=(-0.005, 0.0, 0.0)):
        """Crawler-only settle (legs retracted, virgin soil) with a robust least-squares solve (as 3.11.2):
        n << 1 soils make the virgin node force nearly a step in the sinkage, which defeats plain Newton."""
        from scipy.optimize import least_squares
        e = np.zeros(4)

        def res(q):
            _, Fp, _, _ = self.pads(q, e)
            _, fc, _, _, _ = self.crawler(q)
            return (A_PAD.T @ Fp + self.A_cr.T @ fc - self.w) / self.w[0] * np.array([1, 1 / 3, 1 / 3])

        sol = least_squares(res, np.array(q0, float), x_scale=[0.01, 0.001, 0.001], diff_step=1e-6,
                            xtol=1e-14, ftol=1e-14, gtol=1e-14, max_nfev=2000)
        self.settle_resid = float(np.max(np.abs(sol.fun)))
        return sol.x

    def _resid(self, q, e):
        _, Fp, _, _ = self.pads(q, e)
        _, fc, _, _, _ = self.crawler(q)
        return (A_PAD.T @ Fp + self.A_cr.T @ fc - self.w) / self.w[0] * np.array([1, 1 / 3, 1 / 3])

    def solve(self, e, q0=None, tol=1e-10, maxit=25):
        """Equilibrium for motor extensions e: Newton (analytic tangent), then a least-squares fallback when the
        node-entry / patch-b jumps of the crawler (n << 1 soils) stall it. Accepted residual <= 1e-3 W (recorded)."""
        q = self.q.copy() if q0 is None else np.array(q0, float)
        try:
            q, it = self._newton(e, q, tol, maxit)
            return q, it
        except RuntimeError:
            pass
        from scipy.optimize import least_squares
        sol = least_squares(lambda x: self._resid(x, e), q, x_scale=[0.01, 0.001, 0.001], diff_step=1e-7,
                            xtol=1e-14, ftol=1e-14, gtol=1e-14, max_nfev=500)
        r = float(np.max(np.abs(sol.fun)))
        if r > 1e-3:
            raise RuntimeError(f"equilibrium not converged: {self.level} {self.variant} {self.soil_name} resid {r}")
        self.n_fallback = getattr(self, "n_fallback", 0) + 1
        self.max_resid = max(getattr(self, "max_resid", 0.0), r)
        return sol.x, maxit + int(sol.nfev)

    def _newton(self, e, q, tol, maxit):
        R_norm_prev = None
        for it in range(maxit):
            sp, Fp, ktp, _ = self.pads(q, e)
            sc, fc, ktc, _, _ = self.crawler(q)
            R = A_PAD.T @ Fp + self.A_cr.T @ fc - self.w
            rn = np.max(np.abs(R / self.w[0]) * np.array([1, 1 / 3, 1 / 3]))
            if rn < tol:
                return q, it
            H = A_PAD.T @ (ktp[:, None] * A_PAD) + self.A_cr.T @ (ktc[:, None] * self.A_cr)
            if np.linalg.matrix_rank(H) < 3 or np.linalg.cond(H) > 1e14:
                # no / too few contacts: move the body down (weight not carried) or up
                q = q + np.array([1e-3 if R[0] > 0 else -1e-3, 0.0, 0.0])
                continue
            dq = np.linalg.solve(H, R)
            # backtracking on the residual
            lam = 1.0
            for _ in range(30):
                qn = q + lam * dq
                spn, Fpn, _, _ = self.pads(qn, e)
                _, fcn, _, _, _ = self.crawler(qn)
                Rn = A_PAD.T @ Fpn + self.A_cr.T @ fcn - self.w
                rnn = np.max(np.abs(Rn / self.w[0]) * np.array([1, 1 / 3, 1 / 3]))
                if rnn < rn or lam < 1e-6:
                    break
                lam *= 0.5
            q = qn
            R_norm_prev = rn
        raise RuntimeError(f"equilibrium not converged: {self.level} {self.variant} {self.soil_name} resid {R_norm_prev}")

    def commit(self, q, e):
        """Accept the converged state: update plastic memory of pads and nodes."""
        sp, Fp, _, loadp = self.pads(q, e)
        if self.soil_name != "rigid":
            pp = np.where(self.a_pad > 0, Fp / self.a_pad, 0.0)
            self.p_py = np.where(loadp, pp, self.p_py)
            self.p_sp = np.where(loadp, sp - pp / self.pad_K, self.p_sp)
            sc, fc, _, loadc, _ = self.crawler(q)
            pc = fc / H_GRID ** 2
            self.c_py = np.where(loadc, pc, self.c_py)
            self.c_sp = np.where(loadc, sc - pc / self.cr_soil.K, self.c_sp)
        self.q, self.e = q.copy(), e.copy()
        return sp, Fp

    def state(self, q, e):
        sp, Fp, ktp, loadp = self.pads(q, e)
        sc, fc, _, _, bc = self.crawler(q)
        # crawler block-bottom height above the original surface and above the current (plastic) soil surface
        zrel = self.A_cr @ q + self.chb_flat
        return dict(s_pad=sp, F=Fp, kt_pad=ktp, load_pad=loadp, F_crawler=float(fc.sum()),
                    clear_orig=float(zrel.min()), clear_rut=float((zrel + self.c_sp).min()),
                    crawler_max_sink=float(sc.max()), crawler_b=None if bc is None or bc[0] is None else bc[0].tolist())


# ------------------------------------------------------------------ helpers
def clearance_estimate(rod_stroke):
    pad_z = GEO.pad_z_retracted - rod_stroke
    plane = PLANE_FIT @ pad_z
    corner_z = plane[0] + CORNERS @ plane[1:]
    return float(np.min(ZF - corner_z))


def bekker_inverse(F, area, coef, n):
    return (F / (area * coef)) ** (1.0 / n)


def twist_free_loads(level):
    """Contact forces with n^T F_cyl = 0 (C2 twist target) and A^T F_contact = w."""
    b = body(level)
    W = b.mass * G
    w = np.array([W, W * b.com[1], -W * b.com[0]])
    w_cyl = w - A_PAD.T @ ROD_W
    F_cyl = A_PAD @ np.linalg.solve(A_PAD.T @ A_PAD, w_cyl)
    return F_cyl + ROD_W, F_cyl


# ------------------------------------------------------------------ path simulation (idealised levelling law)
KZ, KP, KI, KTW = 0.5, 0.2, 0.01, 0.5
TAU_F = 0.8
DT_P, DT_C = 0.01, 0.1
DB_ATT, DB_HEAVE, DB_TW, DONE_TW = math.radians(0.03), 0.0015, 2000.0, 3000.0
T_MAX = 400.0


def run_path(level, variant, soil, mode="closed", e_final=None, record=False):
    m = Model(level, variant, soil)
    # settle on the crawler, legs retracted
    q = m.settle()
    m.commit(q, np.zeros(4))
    st0 = m.state(q, np.zeros(4))
    settle = dict(q=q.tolist(), pitch_deg=math.degrees(q[2]), roll_deg=math.degrees(q[1]), uz_mm=q[0] * 1e3,
                  resid_rel=m.settle_resid,
                  crawler_max_sink_mm=st0["crawler_max_sink"] * 1e3, crawler_b=st0["crawler_b"])
    e = np.zeros(4)
    u_cmd = np.zeros(4)
    u_queue = [np.zeros(4)]
    filt1 = np.array([q[1], q[2]])
    filt2 = filt1.copy()
    integ = np.zeros(2)
    lifted = False
    t = 0.0
    nstep_c = int(round(DT_C / DT_P))
    k = 0
    hist = []
    t_touch = [None] * 4
    t_lift = t_crawler_off = t_done = None
    done_since = None
    s_prev = np.zeros(4)
    F_prev = np.zeros(4)
    max_rate = np.zeros(4)
    F_peak = np.zeros(4)
    min_margin = np.inf
    min_margin_t = None
    att_max_after = 0.0
    stroke_hit = False
    sink_after_lift = None
    e_at_lift = None
    s_at_lift = None
    newton_it = []
    while t < T_MAX:
        # controller update at the start of each period (sample = state at t)
        if k % nstep_c == 0:
            st = m.state(m.q, e)
            F = st["F"]
            F_cyl = F - ROD_W
            rod = e - F_cyl.clip(0) / k_oil(e)
            c_est = clearance_estimate(rod)
            if mode == "closed_true":
                # heave on the TRUE crawler clearance (block plane above the original surface) - what the C2 stroke
                # estimate would have to deliver on soil; not measurable by the strokes alone
                c_est = st["clear_orig"]
            if not lifted and c_est > 0.01:
                lifted = True
                t_lift = t
                e_at_lift, s_at_lift = e.copy(), st["s_pad"].copy()
            att = filt2
            heave_err = CLEAR_TARGET - c_est
            if mode in ("closed", "closed_true"):
                hr = KZ * heave_err
                err = -att
                if lifted:
                    integ += err * DT_C
                    integ = np.clip(integ, -0.002 / KI, 0.002 / KI)
                rates = KP * err + (KI * integ if lifted else 0.0)
                tw = 0.0
                ntf = float(N_TW @ F_cyl)
                if lifted and abs(ntf) > DB_TW:
                    tw = -KTW * ntf / K_NOM
                u = A_PAD @ np.array([hr, rates[0], rates[1]]) + N_TW * tw
                if not lifted and u.min() < 0:
                    u = u - u.min()
                mx = np.max(np.abs(u))
                if mx > V_MAX:
                    u *= V_MAX / mx
                du = np.clip(u - u_cmd, -0.25 * V_MAX, 0.25 * V_MAX)
                u_new = u_cmd + du
                ok = (lifted and np.all(np.abs(att) <= DB_ATT) and abs(heave_err) <= DB_HEAVE and abs(ntf) <= DONE_TW)
                if ok:
                    done_since = t if done_since is None else done_since
                    if t - done_since >= 1.0 and t_done is None:
                        t_done = done_since
                else:
                    done_since = None
                if t_done is not None:
                    u_new = np.zeros(4)
            else:  # open loop: all legs together, proportional to e_final, stop at e_final
                frac = e_final / np.max(e_final)
                rem = e_final - e
                u_new = np.where(rem > 1e-9, V_MAX * frac, 0.0)
                if np.all(rem <= 1e-9):
                    t_done = t_done if t_done is not None else t
            u_queue.append(u_new)
            u_cmd = u_new
            if record:
                hist.append([t, *e, *st["s_pad"], *F_cyl, math.degrees(m.q[1]), math.degrees(m.q[2]),
                             math.degrees(att[0]), math.degrees(att[1]), c_est, st["F_crawler"], st["clear_rut"]])
            if t_done is not None and t >= t_done + 1.0:
                break
        u_apply = u_queue[-2] if len(u_queue) >= 2 else np.zeros(4)   # output delay d = 1 period
        e_new = e + u_apply * DT_P
        if mode == "open":
            e_new = np.minimum(e_new, e_final)
        if np.any(e_new > SENSOR_END):
            stroke_hit = True
            e_new = np.minimum(e_new, SENSOR_END)
        e = np.maximum(e_new, 0.0)
        q, it = m.solve(e, q0=m.q)
        newton_it.append(it)
        s_pad, F = m.commit(q, e)
        t += DT_P
        k += 1
        # first-order stages of the attitude filter (100 Hz)
        al = DT_P / (TAU_F + DT_P)
        meas = np.array([q[1], q[2]])
        filt1 += al * (meas - filt1)
        filt2 += al * (filt1 - filt2)
        for i in range(4):
            if t_touch[i] is None and F[i] > 0:
                t_touch[i] = t
        stc = None
        if t_crawler_off is None and np.all(F > 0):
            stc = m.state(q, e)
            if stc["F_crawler"] <= 0:
                t_crawler_off = t
        rate = (s_pad - s_prev) / DT_P
        max_rate = np.maximum(max_rate, np.where((F > 0) & (F_prev > 0), rate, 0.0))
        s_prev = s_pad.copy()
        F_prev = F.copy()
        F_peak = np.maximum(F_peak, F)
        if t_crawler_off is not None:
            mg = float(np.min(F - ROD_W - F_MIN))
            if mg < min_margin:
                min_margin, min_margin_t = mg, t
            att_max_after = max(att_max_after, math.degrees(max(abs(q[1]), abs(q[2]))))
    st = m.state(m.q, e)
    F = st["F"]
    out = dict(level=level, variant=variant, soil=soil, mode=mode, settle=settle,
               t_touch=t_touch, t_lift_latch=t_lift, t_crawler_off=t_crawler_off, t_done=t_done,
               e_final=e.tolist(), s_pad_final=st["s_pad"].tolist(), s_plastic_final=m.p_sp.tolist(),
               F_contact_final=F.tolist(), F_cyl_final=(F - ROD_W).tolist(), F_peak=F_peak.tolist(),
               nT_Fcyl_final=float(N_TW @ (F - ROD_W)),
               roll_final_deg=math.degrees(m.q[1]), pitch_final_deg=math.degrees(m.q[2]), uz_final_mm=m.q[0] * 1e3,
               clear_est_final=clearance_estimate(e - (F - ROD_W).clip(0) / k_oil(e)),
               clear_orig_final=st["clear_orig"], clear_rut_final=st["clear_rut"], F_crawler_final=st["F_crawler"],
               min_Fcyl_margin_after_crawler_off=min_margin if np.isfinite(min_margin) else None,
               min_margin_t=min_margin_t, att_max_after_crawler_off_deg=att_max_after,
               max_sink_rate_mm_s=(max_rate * 1e3).tolist(), stroke_sensor_end_hit=stroke_hit,
               remaining_to_end_margin_m=(END_MARGIN - e).tolist(),
               e_at_lift=None if e_at_lift is None else e_at_lift.tolist(),
               s_at_lift=None if s_at_lift is None else s_at_lift.tolist(),
               newton_it_max=int(max(newton_it)) if newton_it else 0,
               n_lsq_fallback=getattr(m, "n_fallback", 0), max_resid_fallback=getattr(m, "max_resid", 0.0),
               sumFcyl_over_Wcyl_final=float(np.sum(F - ROD_W) / (m.W - ROD_W.sum())),
               kt_pad_final=st["kt_pad"].tolist(), loading_branch_final=st["load_pad"].tolist())
    if record:
        out["hist"] = np.array(hist).tolist()
    return out


# ------------------------------------------------------------------ static / monotone analyses
def final_state_monotone(level, variant, soil):
    """Control-independent level end state: twist-free loads, monotone Bekker sinkage, strokes for two heave rules."""
    F, F_cyl = twist_free_loads(level)
    legs = PV[variant]["legs"]
    a = np.array([legs[n]["area"] for n in LEGS])
    b = np.array([legs[n]["b"] for n in LEGS])
    B = np.array([legs[n]["B_sq"] for n in LEGS])
    s_ = SOILS[soil]
    coef = s_["kc"] / b + s_["kphi"]
    z = bekker_inverse(F, a, coef, s_["n"])
    p = F / a
    kl_guess = k_leg(E_OP + z)
    c = F / kl_guess
    # (H2) true clearance: crawler block-bottom plane 50 mm above the original soil surface (level body: = uz)
    #   actual pad bottom = Z_SURF - z = z_ret - e + uz + c  =>  e = z_ret - (Z_SURF - z) + uz + c
    uz_H2 = CLEAR_TARGET
    e_H2 = GEO.pad_z_retracted - (Z_SURF - z) + uz_H2 + c
    # (H1) C2 heave rule: stroke-based estimate = 50 mm; rod stroke = e - F_cyl / k_oil
    def est_minus_target(uz):
        e = GEO.pad_z_retracted - (Z_SURF - z) + uz + c
        return clearance_estimate(e - F_cyl / k_oil(e)) - CLEAR_TARGET
    lo, hi = -0.5, 0.5
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if est_minus_target(mid) > 0:
            hi = mid
        else:
            lo = mid
    uz_H1 = 0.5 * (lo + hi)
    e_H1 = GEO.pad_z_retracted - (Z_SURF - z) + uz_H1 + c
    qult_d = np.array([bearing_drained(s_["c"], s_["phi"], Bi) for Bi in B])
    qult_u = bearing_undrained(s_["c"])
    k_bek = s_["n"] * F / z
    return dict(F_contact=F.tolist(), F_cyl=F_cyl.tolist(), p_kPa=(p / 1e3).tolist(), z_mm=(z * 1e3).tolist(),
                k_bekker_tangent=k_bek.tolist(), k_elastic_KA=(K_ELASTIC * a).tolist(),
                q_ult_drained_kPa=(qult_d / 1e3).tolist(), p_over_qult_drained=(p / qult_d).tolist(),
                q_ult_undrained_kPa=qult_u / 1e3, p_over_qult_undrained=(p / qult_u).tolist(),
                uz_H1_mm=uz_H1 * 1e3, true_clear_orig_H1_mm=(uz_H1 - 0.0) * 1e3,
                e_H1=e_H1.tolist(), e_H2=e_H2.tolist(), remaining_H1=(END_MARGIN - e_H1).tolist(),
                remaining_H2=(END_MARGIN - e_H2).tolist())


def quasi_static_validity(level, kt_pad):
    """Lowest modes (6-DoF, vertical = final tangent leg-soil stiffness, lateral = YAML kt) of the levelled state."""
    b = dm.body_with_rods(P, GEO, level, E_OP)
    F, _ = twist_free_loads(level)
    pts = np.column_stack([PAD_XY, GEO.pad_z_retracted - E_OP + 0.06])
    K = dm.stiffness_6dof(b, pts, np.asarray(kt_pad), KT_YAML, F)
    M = dm.mass_6dof(b)
    w2, f, Phi, cls, orth = dm.modal(M, K, dm.DOF6)
    return dict(f_Hz=[float(x) for x in f], mode_class=cls)


# ------------------------------------------------------------------ V16 single-pad reference (grid dependence)
def inside_convex(poly, pts):
    """Points strictly inside a CCW convex polygon."""
    ok = np.ones(len(pts), bool)
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        cr = (b[0] - a[0]) * (pts[:, 1] - a[1]) - (b[1] - a[1]) * (pts[:, 0] - a[0])
        ok &= cr > 0
    return ok


def v16_reference(poly, area, b, soil, F_list, grids=(0.02, 0.01, 0.005), nph=5):
    s = SOILS[soil]
    coef = s["kc"] / b + s["kphi"]
    out = {"exact": {"area": area, "b": b, "z_mm": [bekker_inverse(F, area, coef, s["n"]) * 1e3 for F in F_list],
                     "KA_N_m": K_ELASTIC * area}}
    r = np.max(np.linalg.norm(poly, axis=1)) + 0.05
    for h in grids:
        rel = []
        rel_area = []
        rel_b = []
        for i in range(nph):
            for j in range(nph):
                ox, oy = (i / nph) * h, (j / nph) * h
                xs = np.arange(-r + ox, r, h)
                X, Y = np.meshgrid(xs, np.arange(-r + oy, r, h), indexing="ij")
                pts = np.column_stack([X.ravel(), Y.ravel()])
                ins = pts[inside_convex(poly, pts)]
                A_force = len(ins) * h * h
                hull = ConvexHull(ins)
                b_h = 2 * hull.volume / hull.area
                coef_h = s["kc"] / b_h + s["kphi"]
                rel.append(bekker_inverse(1.0, A_force, coef_h, s["n"]) / bekker_inverse(1.0, area, coef, s["n"]) - 1)
                rel_area.append(A_force / area - 1)
                rel_b.append(b_h / b - 1)
        out[f"h_{h * 1e3:.0f}mm"] = {"z_rel_min": float(min(rel)), "z_rel_max": float(max(rel)),
                                     "z_rel_mean": float(np.mean(rel)),
                                     "area_force_rel": [float(min(rel_area)), float(max(rel_area))],
                                     "b_hull_rel": [float(min(rel_b)), float(max(rel_b))],
                                     "p_equiv_rel_max": float(max(abs(min(rel)), abs(max(rel))) * s["n"])}
    return out


# ------------------------------------------------------------------ validation
def validate():
    val = {}
    # (a) linear springs only (pads on k_slab, crawler off): equilibrium vs dyn_model.static_loads
    m = Model("top", "B", "rigid")
    m.chb_flat = m.chb_flat + 10.0      # crawler far away
    e = E_OP + 0.02
    q, _ = m.solve(e, q0=np.array([0.0, 0.0, 0.0]))
    s, F, _, _ = m.pads(q, e)
    kser = dm.series(k_leg(e), K_SLAB)
    pen0 = Z_SURF - (GEO.pad_z_retracted - e)       # penetration at q = 0
    F_ref, q_ref, _ = dm.static_loads(kser, PAD_XY, m.W, m.cg, delta=pen0)
    val["linear_vs_static_loads"] = {"F_rel_max": float(np.max(np.abs(F / F_ref - 1))),
                                     "q_abs_max": float(np.max(np.abs(q - q_ref)))}
    # (b) crawler settle on soil, manhattan b (= 3.11.2 model) vs crawler_contact_check.json (C, 20 mm)
    refall = json.load(open(ROOT / "06_analysis/00_dynamics/crawler_contact_check.json", encoding="utf-8"))["partB_scm_shape"]
    ref = refall["results"]["C"]
    W_ref, cg_ref = float(refall["meta"]["weight_N"]), np.array(refall["meta"]["com_xy_m"], float)
    keymap = {"LETE_sand": "LETE_sand", "heavy_clay_25": "heavy_clay_25pct (S0 benchmark soil)"}
    for soil, rk in keymap.items():
        mm = Model("top", "B", soil, crawler_grid="manhattan")
        val.setdefault("crawler_ref_inputs", {"W_ref_N": W_ref, "cg_ref": cg_ref.tolist(), "W_now_N": mm.W, "cg_now": mm.cg.tolist()})
        mm.w = np.array([W_ref, W_ref * cg_ref[1], -W_ref * cg_ref[0]])   # same inputs as the 2026-10-21 reference
        mr = Model("top", "B", soil, crawler_grid="manhattan")
        mr.w = mm.w.copy()
        q_reg = mr.settle()                       # with the 0.1 mm crawler regularisation
        mm.cr_soil.s_reg = 0.0                    # exact Bekker for the reproduction check
        qq = mm.settle()
        val[f"crawler_settle_{soil}_regularisation_effect"] = {"z0_mm": (q_reg[0] - qq[0]) * 1e3,
                                                               "pitch_deg": math.degrees(q_reg[2] - qq[2])}
        r20 = ref[rk]["h_20mm"]
        mh = Model("top", "B", soil, crawler_grid="hull")
        qh = mh.settle()
        val[f"crawler_settle_{soil}"] = {"z0_mm_this": qq[0] * 1e3, "z0_mm_ref": r20["z0_mm"],
                                         "pitch_deg_this": math.degrees(qq[2]), "pitch_deg_ref": r20["pitch_deg"],
                                         "z0_rel": qq[0] * 1e3 / r20["z0_mm"] - 1 if abs(r20["z0_mm"]) > 1e-6 else None,
                                         "pitch_rel": math.degrees(qq[2]) / r20["pitch_deg"] - 1,
                                         "hull_b_z0_mm": qh[0] * 1e3, "hull_b_pitch_deg": math.degrees(qh[2]),
                                         "resid_this": mm.settle_resid, "resid_hull": mh.settle_resid}
    # (c) single pad monotone loading on soil: bisection solution vs closed-form Bekker inverse
    mp = Model("top", "B", "LETE_sand")
    z_cf = bekker_inverse(70e3, mp.a_pad[2], mp.pad_coef[2], SOILS["LETE_sand"]["n"])
    sl = mp.pad_soil
    p = sl.kphi  # dummy
    pz, _, _ = mp.pad_p(np.array([z_cf] * 4))
    val["pad_law_closed_form_rel"] = float(abs(pz[2] * mp.a_pad[2] / 70e3 - 1))
    return val


# ------------------------------------------------------------------ main
CACHE = None   # optional per-case cache dir (--cache DIR), lets a long batch resume after a shell timeout


def _job(args):
    level, variant, soil, mode, e_final, record = args
    if CACHE is not None:
        f = Path(CACHE) / f"{soil}_{variant}_{level}_{mode}.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
    out = run_path(*args)
    if CACHE is not None:
        f.write_text(json.dumps(out, default=float), encoding="utf-8")
    return out


def _init_worker(cache):
    global CACHE
    CACHE = cache


def main():
    t0 = time.perf_counter()
    res = {"meta": {"script": "04_scripts/01_dynamics/run_pad_bekker_p0.py", "doc": "dynamics_model.md 5.31 (rev. 45)",
                    "pad_variants_source": PV_SRC, "gravity_m_s2": G, "Z_surface_m": Z_SURF,
                    "frames": "body x fwd, y left, z up; pitch > 0 nose down; roll > 0 left up; q about body origin",
                    "assumptions": {"K_elastic_Pa_m": K_ELASTIC, "gamma_N_m3": GAMMA, "soil_damping_R": "omitted (quasi-static)",
                                    "levelling_law": "idealised (not C2): KZ 0.5, KP 0.2, KI 0.01, KTW 0.5 on n^T F_cyl / k_nom, "
                                                     "filter 2 x 0.8 s, 10 Hz, delay 1, dead bands 0.03 deg / 1.5 mm / 2 kN",
                                    "crawler": "C envelope, 20 mm grid, hull b (Chrono)", "pad": "one flat element, swivel keeps it level",
                                    "k_leg": "series(k_oil(e) + k_rod_side, k_rod, k_frame), dead length 0.05 m",
                                    "type_A_rear_mass": "same as B (U-PAD-3)"}}}
    res["validation"] = validate()
    print("validation", json.dumps(res["validation"], default=float), flush=True)

    # soil screening (bearing)
    scr = {}
    Fmono, _ = twist_free_loads("top")
    for name, s in {**SOILS, **SCREEN}.items():
        row = {}
        for v in ("A", "B"):
            legs = PV[v]["legs"]
            pr = [Fmono[i] / legs[n]["area"] for i, n in enumerate(LEGS)]
            qd = [bearing_drained(s["c"], s["phi"], legs[n]["B_sq"]) for n in LEGS]
            row[v] = {"p_max_kPa": max(pr) / 1e3, "p_over_qult_drained_max": max(p / q for p, q in zip(pr, qd)),
                      "p_over_qult_undrained_max": max(pr) / bearing_undrained(s["c"])}
        scr[name] = row
    res["soil_screening"] = scr

    # monotone final states
    res["final_monotone"] = {s: {v: {lv: final_state_monotone(lv, v, s) for lv in LEVELS} for v in ("A", "B")} for s in SOILS}

    # path runs
    jobs = [(lv, v, s, "closed", None, (lv == "top")) for s in SOILS for v in ("A", "B") for lv in LEVELS]
    jobs += [(lv, "B", "rigid", "closed", None, (lv == "top")) for lv in LEVELS]
    jobs += [("top", v, s, "closed_true", None, True) for s in SOILS for v in ("A", "B")]
    jobs.sort(key=lambda j: 0 if j[2] == "heavy_clay_25" else 1)        # slowest first
    with ProcessPoolExecutor(max_workers=12, initializer=_init_worker, initargs=(CACHE,)) as ex:
        out = list(ex.map(_job, jobs))
    paths = {f"{o['soil']}|{o['variant']}|{o['level']}": o for o in out if o["mode"] == "closed"}
    paths_true = {f"{o['soil']}|{o['variant']}|{o['level']}": o for o in out if o["mode"] == "closed_true"}
    # open loop: legs driven to the rigid-floor final extensions of the same level
    jobs2 = [(lv, v, s, "open", np.array(paths[f"rigid|B|{lv}"]["e_final"]), False) for s in SOILS for v in ("A", "B") for lv in LEVELS]
    with ProcessPoolExecutor(max_workers=12, initializer=_init_worker, initargs=(CACHE,)) as ex:
        out2 = list(ex.map(_job, jobs2))
    open_ = {f"{o['soil']}|{o['variant']}|{o['level']}": o for o in out2}
    res["paths_closed"] = {k: {kk: vv for kk, vv in o.items() if kk != "hist"} for k, o in paths.items()}
    res["paths_closed_true_clearance"] = {k: {kk: vv for kk, vv in o.items() if kk != "hist"} for k, o in paths_true.items()}
    res["paths_open"] = open_

    # quasi-static validity at the end state (tangent loading branch and elastic branch)
    qsv = {}
    for s in SOILS:
        for v in ("A", "B"):
            o = paths[f"{s}|{v}|top"]
            kl = k_leg(np.array(o["e_final"]))
            fm = res["final_monotone"][s][v]["top"]
            kload = dm.series(kl, np.array(fm["k_bekker_tangent"]))
            kel = dm.series(kl, np.array(fm["k_elastic_KA"]))
            qsv[f"{s}|{v}"] = {"loading": quasi_static_validity("top", kload), "elastic": quasi_static_validity("top", kel)}
    res["quasi_static_validity_top"] = qsv

    # type comparison
    def tol_load(b):
        return max(1000.0, 0.01 * abs(b))

    def tol_sink(b):
        return max(0.005, 0.10 * abs(b))

    comp = {}
    for s in SOILS:
        for lv in LEVELS:
            A_, B_ = paths[f"{s}|A|{lv}"], paths[f"{s}|B|{lv}"]
            oA, oB = open_[f"{s}|A|{lv}"], open_[f"{s}|B|{lv}"]
            rows = {}
            rows["open_loop_pitch_deg"] = (oA["pitch_final_deg"], oB["pitch_final_deg"], 0.05)
            rows["open_loop_roll_deg"] = (oA["roll_final_deg"], oB["roll_final_deg"], 0.05)
            rows["att_max_after_crawler_off_deg"] = (A_["att_max_after_crawler_off_deg"], B_["att_max_after_crawler_off_deg"], 0.05)
            for i, n in enumerate(LEGS):
                rows[f"F_final_{n}"] = (A_["F_contact_final"][i], B_["F_contact_final"][i], tol_load(B_["F_contact_final"][i]))
                rows[f"F_peak_{n}"] = (A_["F_peak"][i], B_["F_peak"][i], tol_load(B_["F_peak"][i]))
                rows[f"s_final_{n}"] = (A_["s_pad_final"][i], B_["s_pad_final"][i], tol_sink(B_["s_pad_final"][i]))
                rows[f"e_final_{n}"] = (A_["e_final"][i], B_["e_final"][i], tol_sink(B_["e_final"][i] - E_OP[i]))
            rows["min_Fcyl_margin"] = (A_["min_Fcyl_margin_after_crawler_off"], B_["min_Fcyl_margin_after_crawler_off"],
                                       tol_load(F_MIN))
            tA, tB = A_["t_done"], B_["t_done"]
            rows["t_done_s"] = (tA, tB, 0.10 * tB if tB else None)
            rows["clear_true_final_m"] = (A_["clear_orig_final"], B_["clear_orig_final"], 0.005)
            rows["F_crawler_final_N"] = (A_["F_crawler_final"], B_["F_crawler_final"], 1000.0)
            if lv == "top":
                At, Bt = paths_true[f"{s}|A|top"], paths_true[f"{s}|B|top"]
                rows["TRUE_t_done_s"] = (At["t_done"], Bt["t_done"], 0.10 * Bt["t_done"] if Bt["t_done"] else None)
                rows["TRUE_att_max_after_crawler_off_deg"] = (At["att_max_after_crawler_off_deg"], Bt["att_max_after_crawler_off_deg"], 0.05)
                rows["TRUE_min_Fcyl_margin"] = (At["min_Fcyl_margin_after_crawler_off"], Bt["min_Fcyl_margin_after_crawler_off"], tol_load(F_MIN))
                for i, n in enumerate(LEGS):
                    rows[f"TRUE_e_final_{n}"] = (At["e_final"][i], Bt["e_final"][i], tol_sink(Bt["e_final"][i] - E_OP[i]))
                    rows[f"TRUE_s_final_{n}"] = (At["s_pad_final"][i], Bt["s_pad_final"][i], tol_sink(Bt["s_pad_final"][i]))
            verdict = {}
            for key, (a, b, tl) in rows.items():
                if a is None or b is None or tl is None:
                    verdict[key] = {"A": a, "B": b, "tol": tl, "diff": None, "exceeds": None}
                    continue
                d = a - b
                verdict[key] = {"A": a, "B": b, "diff": d, "tol": tl, "exceeds": bool(abs(d) > tl)}
            comp[f"{s}|{lv}"] = {"rows": verdict, "type_dependent": any(r["exceeds"] for r in verdict.values() if r["exceeds"] is not None)}
    res["type_comparison"] = comp

    # V16 single-pad reference draft
    v16 = {}
    Fb, _ = twist_free_loads("top")
    for lab, leg_i in (("330", 0), ("250", 2)):
        legd = PV["B"]["legs"][LEGS[leg_i]]
        poly = legd["poly"]
        if poly is None:
            continue
        Fd = float(Fb[leg_i])
        F_list = [f * Fd for f in (0.25, 0.5, 0.75, 1.0, 1.25)]
        v16[lab] = {"leg_for_design_load": LEGS[leg_i], "F_design_N": Fd, "F_list_N": F_list,
                    "soils": {s: v16_reference(poly, legd["area"], legd["b"], s, F_list) for s in SOILS}}
    # type A rear (330 at the rear orientation) for completeness
    legA = PV["A"]["legs"]["RL"]
    if legA["poly"] is not None:
        Fd = float(Fb[2])
        F_list = [f * Fd for f in (0.25, 0.5, 0.75, 1.0, 1.25)]
        v16["330_rear"] = {"leg_for_design_load": "RL", "F_design_N": Fd, "F_list_N": F_list,
                           "soils": {s: v16_reference(legA["poly"], legA["area"], legA["b"], s, F_list) for s in SOILS}}
    res["v16_draft"] = v16
    res["meta"]["runtime_s"] = time.perf_counter() - t0
    OUT.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")

    # ------------------------------------------------ figures
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(4, 3, figsize=(15, 13), sharex="col")
    cols = {"A": "tab:orange", "B": "tab:blue", "rigid": "0.4"}
    for j, s in enumerate(SOILS):
        for v in ("A", "B"):
            h = np.array(paths[f"{s}|{v}|top"]["hist"])
            if h.size == 0:
                continue
            t = h[:, 0]
            axs[0, j].plot(t, h[:, 14], color=cols[v], label=f"{v} pitch")
            axs[0, j].plot(t, h[:, 13], color=cols[v], ls=":", label=f"{v} roll")
            for i, ls in zip(range(4), ("-", "--", "-.", ":")):
                axs[1, j].plot(t, h[:, 5 + i] * 1e3, color=cols[v], ls=ls, label=f"{v} {LEGS[i]}")
                axs[2, j].plot(t, h[:, 9 + i] / 1e3, color=cols[v], ls=ls)
                axs[3, j].plot(t, h[:, 1 + i] * 1e3, color=cols[v], ls=ls)
        hr = np.array(paths[f"rigid|B|top"]["hist"])
        axs[0, j].plot(hr[:, 0], hr[:, 14], color=cols["rigid"], lw=0.8, label="rigid B pitch")
        for i, ls in zip(range(4), ("-", "--", "-.", ":")):
            axs[3, j].plot(hr[:, 0], hr[:, 1 + i] * 1e3, color=cols["rigid"], ls=ls, lw=0.8)
        axs[2, j].axhline(F_MIN / 1e3, color="k", lw=0.6)
        axs[0, j].set_title(f"{s} ({SOILS[s]['role']}), auger top")
        axs[0, j].set_ylabel("true attitude [deg]")
        axs[1, j].set_ylabel("pad sinkage [mm]")
        axs[2, j].set_ylabel("F_cyl [kN] (line = F_min)")
        axs[3, j].set_ylabel("motor extension [mm]")
        axs[3, j].set_xlabel("time [s]")
        axs[0, j].legend(fontsize=7)
        axs[1, j].legend(fontsize=6, ncol=2)
        for a in axs[:, j]:
            a.grid(alpha=0.3)
    fig.suptitle("P0 reduced Bekker series model, idealised levelling law (not C2); A = cad330, B = dwg_rear250")
    fig.tight_layout()
    fig.savefig(FIG_PATH, dpi=110)
    plt.close(fig)

    fig, axs = plt.subplots(1, 3, figsize=(15, 4.5))
    for j, s in enumerate(SOILS):
        for lab, col in (("330", "tab:orange"), ("250", "tab:blue"), ("330_rear", "tab:green")):
            if lab not in v16:
                continue
            d = v16[lab]
            z = np.array(d["soils"][s]["exact"]["z_mm"])
            F = np.array(d["F_list_N"]) / 1e3
            axs[j].plot(z, F, "o-", color=col, label=f"{lab} exact")
            r = d["soils"][s]["h_10mm"]
            axs[j].fill_betweenx(F, z * (1 + r["z_rel_min"]), z * (1 + r["z_rel_max"]), color=col, alpha=0.2,
                                 label=f"{lab} 10 mm grid phases")
        axs[j].set_xlabel("sinkage z [mm]")
        axs[j].set_ylabel("pad load F [kN]")
        axs[j].set_title(s)
        axs[j].grid(alpha=0.3)
        axs[j].legend(fontsize=7)
    fig.suptitle("V16 draft: single pad Bekker load-sinkage (loading branch) and 10 mm grid-phase band (Chrono hull b, node-count area)")
    fig.tight_layout()
    fig.savefig(FIG_V16, dpi=110)
    plt.close(fig)
    print("runtime", res["meta"]["runtime_s"], flush=True)


if __name__ == "__main__":
    if "--cache" in sys.argv:
        CACHE = sys.argv[sys.argv.index("--cache") + 1]
        Path(CACHE).mkdir(parents=True, exist_ok=True)
    main()
