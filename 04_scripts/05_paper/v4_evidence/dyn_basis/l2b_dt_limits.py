"""Explicit (semi-implicit Euler) stability limits of the L2b local rod modes.

Scheme: v+ = v + h (-k x - c v)/m, x+ = x + h v+  ->  stable iff
omega h < 2 (sqrt(1 + zeta^2) - zeta) and 2 zeta omega h < 2.
Values from 02_params/rexome33.yaml (2026-10-31 read), SI.
"""
import math

import numpy as np

BETA, L0, KF, KC = 1.0e9, 0.05, 1.0e9, 3.23661912e8
LEGS = {
    #       A_p [m2]              k_rod      m (rod+pad)  c_lock    c_move    k_op(YAML)   pad A
    "front": (math.pi / 4 * 0.13**2, 1.90066356e9, 106.783666, 34403.519, 100206.0, 25905744.2, 0.1071),
    "rear": (math.pi / 4 * 0.11**2, 1.27234502e9, 73.1629937, 30348.4527, 86949.0, 19504614.9, 0.0607),
}
SOIL = {"G1": (3.5e8, 1.207e6), "J1": (2.0e8, 9.92e5), "S1": (2.0e8, 7.41e5)}  # K [Pa/m], R [Pa s/m]


def series(*k):
    return 1.0 / sum(1.0 / x for x in k)


def limit(k, m, c):
    w = math.sqrt(k / m)
    z = c / (2 * math.sqrt(k * m))
    h = 2 / w * (math.sqrt(1 + z * z) - z)
    h = min(h, 1 / (z * w)) if z > 0 else h
    return w / (2 * math.pi), z, h


def row(name, k, m, c):
    f, z, h = limit(k, m, c)
    print(f"{name:52s} k={k:9.3e} f={f:7.1f} Hz zeta={z:5.3f} h_lim={h*1e3:6.3f} ms "
          f"margin={h/1e-4:5.1f}x wh@1e-4={2*math.pi*f*1e-4:6.4f} T/50={1/f/50*1e6:6.1f} us")


for leg, (ap, krod, m, cl, cm, kop, apad) in LEGS.items():
    print(f"--- {leg}")
    row("op point (YAML k_op), locked", kop, m, cl)
    row("op point (YAML k_op), moving", kop, m, cm)
    for s in (0.0, 0.7):
        for beta, l0 in ((1.0e9, 0.05), (1.6e9, 0.05), (0.69e9, 0.08)):
            k = series(beta * ap / (l0 + s), krod, KF, KC)
            row(f"air s_ref={s} beta={beta:.2e} L0={l0}, moving", k, m, cm)
            row(f"air s_ref={s} beta={beta:.2e} L0={l0}, locked", k, m, cl)
    kout_c = series(krod, KF, KC)
    kout = series(krod, KF)
    row("air, seal stuck (k_out with concrete), locked", kout_c, m, cl)
    row("air, seal stuck (k_out with concrete), moving", kout_c, m, cm)
    for soil, (K, R) in SOIL.items():
        ks, cs = K * apad, R * apad
        kax = series(BETA * ap / (L0 + 0.0), krod, KF)
        row(f"SCM {soil} slide, s_ref=0 beta 1.0 locked", kax + ks, m, cl + cs)
        row(f"SCM {soil} seal stuck (k_out no concrete), locked", kout + ks, m, cl + cs)
        row(f"SCM {soil} seal stuck (k_out no concrete), moving", kout + ks, m, cm + cs)
        print(f"{'':52s} explicit soil dashpot alone: 2m/c_soil = {2*m/cs*1e3:.2f} ms")

# superstructure heave on explicit leg springs (rod held by NSC contact)
M = 38760.7299
k4 = 2 * 33929017.0 + 2 * 26402111.0
w = math.sqrt(k4 / M)
print(f"heave on LOCK springs f={w/2/math.pi:.2f} Hz, w h@1e-4 = {w*1e-4:.2e}")
kst = 2 * series(1.90066356e9, KF, KC) + 2 * series(1.27234502e9, KF, KC)
w = math.sqrt(kst / M)
print(f"heave all seals stuck f={w/2/math.pi:.2f} Hz, w h@1e-4 = {w*1e-4:.2e}")
# check the scheme by eigenvalues for one case
k, m, c, h = 25905744.2, 106.783666, 100206.0, 1.0e-4
A = np.array([[1 - h * h * k / m, h * (1 - h * c / m)], [-h * k / m, 1 - h * c / m]])
print("spectral radius op moving @1e-4:", max(abs(np.linalg.eigvals(A))))
f, z, hl = limit(k, m, c)
for hh in (hl * 0.999, hl * 1.001):
    A = np.array([[1 - hh * hh * k / m, hh * (1 - hh * c / m)], [-hh * k / m, 1 - hh * c / m]])
    print(f"h={hh*1e3:.4f} ms rho={max(abs(np.linalg.eigvals(A))):.6f}")
# old 71.0 Hz doc values
for z in (0.30, 0.99):
    w = 2 * math.pi * 71.0
    print(f"doc 4.3 71.0 Hz zeta {z}: {2/w*(math.sqrt(1+z*z)-z)*1e3:.2f} ms")
for z in (0.30, 1.0):
    w = 2 * math.pi * 78.0
    print(f"78 Hz zeta {z}: {2/w*(math.sqrt(1+z*z)-z)*1e3:.2f} ms")
