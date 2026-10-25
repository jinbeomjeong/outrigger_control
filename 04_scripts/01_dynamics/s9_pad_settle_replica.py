"""1-DoF heave replica of the S9 single-pad settle (share + pad mass on SCM, G1 n = 1, Kc = 0); dynamics_model.md 5.34.3.

SCM law as SCMTerrain.cpp:1394-1465; force = A_nodes sigma; explicit loads, symplectic Euler, dt 1e-4.
Start: pad bottom 0.5 mm above the plane at rest, full gravity from t = 0 (smoke protocol) or a Poly345
gravity ramp. Prints final sinkage vs the Bekker static value. SI, z up.
"""

G = 9.80665
Kphi, K, R = 1.5e8, 3.5e8, 1.207e6
N = 72814.17291553626
m = N / G


def run(A, ramp=0.0, t_end=3.0, dt=1e-4, z0=0.0005):
    z, v = z0, 0.0
    sp, sy = 0.0, 0.0
    zmin = 0.0
    for k in range(int(t_end / dt)):
        t = k * dt
        if ramp > 0:
            u = min(t / ramp, 1.0)
            f = 10 * u ** 3 - 15 * u ** 4 + 6 * u ** 5
        else:
            f = 1.0
        s = -z
        sig = K * (s - sp)
        F = 0.0
        if sig > 0:
            if sig > sy:
                sig = Kphi * s
                sy = sig
                sp = s - sig / K
            sig += -v * R
            F = sig * A
        v += dt * (F / m - G * f)
        z += dt * v
        zmin = min(zmin, z)
    return -z, -zmin


for A, lab in ((0.0607, "exact area"), (157 * 0.02 ** 2, "2 cm nodes 157"), (601 * 0.01 ** 2, "1 cm nodes 601")):
    s_st = N / (Kphi * A)
    for ramp in (0.0, 1.0):
        s, smax = run(A, ramp)
        print(f"{lab:16s} ramp {ramp:.1f} s: final sinkage {s*1e3:.3f} mm (max {smax*1e3:.3f}), Bekker static {s_st*1e3:.3f} mm, ratio {s/s_st:.4f}")
