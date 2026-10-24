"""V14 L2b-NSC: size of the geometric (P-delta) effect on the RL+ small-signal stiffness (record).

dynamics_model.md rev. 35, 5.22.3 (V14 systematic difference, user item 4, 2026-10-24). Chrono S7
V14 shows the RL+ secant -1.8 to -1.9 % and the thresholds +1.4 to +2.9 % against the linear
reference (L2b_NSC_reference_rev33 / V14, no P-delta), the same sign in all four slope cases and
on the level floor. Hypothesis: P-delta.

Model (Chrono S7 topology, finite rotations): superstructure body 6 DoF (CoM translation, rotation
vector, exp map) + rod ball translation (x, y, z) per leg. Axial spring along the body z axis
between the attachment point and the rod ball; lateral springs kt along body x / y between the
barrel point at the ball centre and the rod; NSC contact = isotropic stick penalty KC at the sphere
contact point B + R (-hb n) (rod rotation = body rotation). Procedure as the reference (V12 rule):
place with zero spring force at the case extension, settle with the head-only k2(e) on every leg,
then arm the rod side on the locked legs (FL, FR, RR): axial law F_settle + k1 (comp - comp_settle),
k1 = series(k_h + k_r, k_out) (as l2b_reference piecewise_path LOCK); RL (moving) keeps k2. Small-signal RL+ stiffness dF_RL / d delta (central difference
+-10 um of the RL natural length) at gravity x 1 (P-delta in) and gravity x 1e-6 (linear limit,
same topology). The rod-side knee (p_floor) is not modelled: small-signal only.

Units SI; body frame x forward, y left, z up; floor z = sx x + sy y (sx = -tan pitch, sy = tan roll,
as run_reference). Output 06_analysis/00_dynamics/v14_pdelta_check.json.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import jax
import jax.numpy as jnp
import numpy as np

jax.config.update("jax_enable_x64", True)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402
import l2b_reference as l2b  # noqa: E402

KC = 1.0e11          # N/m stick penalty (>= 1e3 x the axial / lateral springs; rigid-limit check below)
DELTA = 1.0e-5       # m, central difference of the RL natural length
G_LINEAR = 1.0e-6    # gravity scale of the linear limit
CASES = ("level", "max pitch+", "max roll+", "max diag 45")
RL = 2

p = dm.load_params()
geo = dm.geometry_from_params(p)
lp = l2b.leg_parameters(p, geo)
body = dm.body_from_params(p, "top")
hb = dm.ASSUMPTIONS["swivel_ball_height_above_pad_bottom_m"]
ref = json.loads((ROOT / "06_analysis" / "00_dynamics" / "reference.json").read_text(
    encoding="utf-8"))["L2b_NSC_reference_rev33"]["V14"]["cases"]


def skew(v):
    return jnp.array([[0.0, -v[2], v[1]], [v[2], 0.0, -v[0]], [-v[1], v[0], 0.0]])


def rot(r):
    return jax.scipy.linalg.expm(skew(r))


def build(ext, roll_deg, pitch_deg, kc=KC):
    ext = np.asarray(ext, float)
    sx, sy = -math.tan(math.radians(pitch_deg)), math.tan(math.radians(roll_deg))
    nrm = np.array([-sx, -sy, 1.0])
    nrm /= np.linalg.norm(nrm)
    d_att = np.array([[*geo.pad_xy[i], geo.attach_z[i]] for i in range(4)]) - body.com
    d_ball = np.array([[*geo.pad_xy[i], geo.pad_z_retracted[i] - ext[i] + hb]
                       for i in range(4)]) - body.com
    b0 = body.com + d_ball                       # rod ball centres at placement (world)
    v0 = -hb * nrm                               # contact offset from the ball
    c0 = b0 + v0                                 # stick anchors
    L0 = d_att[:, 2] - d_ball[:, 2]              # zero-force axial length
    k2 = lp["k2_f"](ext)
    kr = lp["k_r_f"](ext)
    k1 = dm.series(lp["k_h_f"](ext) + kr, lp["k_out"])   # locked: rod side inside the series with k_out
    kt = np.broadcast_to(np.asarray(lp["kt"], float), (4,))
    g, m, mr = geo.g, body.mass, geo.rod_mass

    def parts(q):
        u, rv, w = q[:3], q[3:6], q[6:].reshape(4, 3)
        R = rot(rv)
        c = body.com + u
        A = c + d_att @ R.T
        P = c + d_ball @ R.T
        B = b0 + w
        ez, ex, ey = R[:, 2], R[:, 0], R[:, 1]
        L = (A - B) @ ez
        lat_x, lat_y = (P - B) @ ex, (P - B) @ ey
        C = B + v0 @ R.T
        return u, c, B, L, lat_x, lat_y, C

    def energy(q, gscale, dnat, armed, comp_settle):
        u, c, B, L, lx, ly, C = parts(q)
        comp = L0 + dnat - L                     # axial compression (+ = load)
        f_s = k2 * comp_settle                   # settled axial force (head only)
        e = jnp.sum((1 - armed) * 0.5 * k2 * comp ** 2
                    + armed * (f_s * comp + 0.5 * k1 * (comp - comp_settle) ** 2))
        e += 0.5 * jnp.sum(kt * (lx ** 2 + ly ** 2))
        e += 0.5 * kc * jnp.sum((C - c0) ** 2)
        e += gscale * g * (m * c[2] + jnp.sum(mr * B[:, 2]))
        return e

    grad = jax.jit(jax.grad(energy))
    hess = jax.jit(jax.hessian(energy))

    def axial_comp(q, dnat):
        return np.asarray(L0 + dnat - parts(q)[3])

    def solve(q, *args, tol=1e-9, it=40):
        for _ in range(it):
            gr = np.asarray(grad(q, *args))
            dq = np.linalg.solve(np.asarray(hess(q, *args)), -gr)
            q = q + dq
            if np.abs(dq).max() < tol * 1e-3:
                break
        res = float(np.abs(np.asarray(grad(q, *args))).max())
        return q, res

    return dict(solve=solve, axial_comp=axial_comp, k2=k2, k1=k1)


def small_signal(model, gscale):
    z = jnp.zeros(18)
    zero4 = jnp.zeros(4)
    armed = jnp.array([1.0, 1.0, 0.0, 1.0])
    q_s, res0 = model["solve"](z, gscale, zero4, jnp.zeros(4), zero4)
    comp_s = model["axial_comp"](q_s, np.zeros(4))
    out, res = {}, [res0]
    for sgn in (+1, -1):
        dnat = np.zeros(4)
        dnat[RL] = sgn * DELTA
        q, r_ = model["solve"](q_s, gscale, jnp.asarray(dnat), armed, jnp.asarray(comp_s))
        comp = model["axial_comp"](q, dnat)
        k_leg = np.where(np.array([1, 1, 0, 1]) > 0,
                         model["k2"] * comp_s + model["k1"] * (comp - comp_s), model["k2"] * comp)
        out[sgn] = k_leg
        res.append(r_)
    dF = (out[1] - out[-1]) / (2 * DELTA) * 1e-3          # N per mm
    F0 = model["k2"] * comp_s
    return dF, F0, max(res)


def main():
    result = {"method": " ".join(__doc__.split("\n\n")[1].split()), "KC_N_m": KC,
              "delta_m": DELTA, "gravity_scale_linear": G_LINEAR, "cases": {}}
    for name in CASES:
        rc = ref[name]
        ro, pi = rc["ground_roll_pitch_deg"]
        model = build(rc["extension_m"], ro, pi)
        dF1, F0, r1 = small_signal(model, 1.0)
        dFl, _, r2 = small_signal(model, G_LINEAR)
        ref_ss = rc["RL+"]["L1R_after_extend"]["dF_cyl_per_mm_small_signal_N"]
        stiff = build(rc["extension_m"], ro, pi, kc=KC * 10)
        dF1s, _, _ = small_signal(stiff, 1.0)
        result["cases"][name] = {
            "ground_roll_pitch_deg": [ro, pi],
            "settled_cylinder_force_N": np.round(F0, 1).tolist(),
            "dF_per_mm_small_signal_N (P-delta in)": np.round(dF1, 2).tolist(),
            "dF_per_mm_small_signal_N (linear limit)": np.round(dFl, 2).tolist(),
            "reference_dF_per_mm_small_signal_N (rev33, linear)": ref_ss,
            "linear_limit_vs_reference_RL_rel": round(float(dFl[RL] / ref_ss[RL] - 1), 5),
            "P_delta_effect_RL_rel (P-delta / linear - 1)": round(float(dF1[RL] / dFl[RL] - 1), 5),
            "P_delta_effect_RL_rel at KC x 10": round(float(dF1s[RL] / dFl[RL] - 1), 5),
            "max_gradient_residual (N or N m)": max(r1, r2),
        }
        print(name, result["cases"][name]["P_delta_effect_RL_rel (P-delta / linear - 1)"],
              result["cases"][name]["linear_limit_vs_reference_RL_rel"])
    out = ROOT / "06_analysis" / "00_dynamics" / "v14_pdelta_check.json"
    out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print("out:", out)


if __name__ == "__main__":
    main()
