"""Independent replica of the L1 command law over the V11 schedule (no physics, no saturation).

Command law (written from the formula, not imported): accel limit a = v_max / T_r, discrete braking cap
w = sqrt((a dt/2)^2 + 2 a d) - a dt/2 towards both stroke ends, rate limit a dt, end clip u = (end - s)/dt.
A rigid position motor reads m_rod du/dt of the speed change of the step (+ m_rod g, removed here).
Also scans the end gap to show the bound 1 + r(1 - r)/2 <= 9/8.
"""
import numpy as np

G = 9.80665
V = 0.0209243016          # m/s, run meta max_speed_m_s
TR = 0.1                  # s, actuator.command_ramp_s
A = V / TR
STROKE = 0.70
HALF = 34.5               # s, V11 half period (dynamics_model.md 5.12.12 supplement 7)
M_ROD = {"FL": 106.784, "RL": 73.163}   # kg, YAML moving_part mass (front / rear)


def run(dt, stroke=STROKE, s0=0.0):
    n = int(round(2 * HALF / dt))
    s, u = s0, 0.0
    du_max, i_max = 0.0, -1
    step, half = A * dt, 0.5 * A * dt
    for i in range(n):
        t = i * dt
        cmd = V if t < HALF else -V
        up = np.sqrt(half * half + 2 * A * max(stroke - s, 0.0)) - half
        dn = np.sqrt(half * half + 2 * A * max(s, 0.0)) - half
        tgt = min(max(cmd, -dn), up)
        un = u + np.clip(tgt - u, -step, step)
        sn = s + un * dt
        if sn > stroke or sn < 0.0:
            sn = min(max(sn, 0.0), stroke)
            un = (sn - s) / dt
        if abs(un - u) > du_max:
            du_max, i_max = abs(un - u), i
        s, u = sn, un
    return du_max / step, i_max * dt


for dt in (2e-4, 1e-4, 1e-5):
    r, t = run(dt)
    print(f"dt {dt:g}: max |du| / (a dt) = {r:.6f} at t = {t:.4f} s;", ", ".join(
        f"{k} m a = {m * A:.3f} N, max m du/dt = {m * A * r:.3f} N, 9/8 m a (1 %) = {1.125 * m * A * 1.01:.3f} N"
        for k, m in M_ROD.items()))

# bound scan: fractional last step r in (0, 1) -> 1 + r (1 - r) / 2
dt = 2e-4
worst = 0.0
for stroke in np.linspace(0.69, 0.70, 2001):
    r, _ = run_r = (None, None)
    break
rs = np.linspace(0, 1, 100001)
print("analytic max of 1 + r(1-r)/2:", (1 + rs * (1 - rs) / 2).max())
# numeric scan of the end gap for one extend (s0 chosen to sweep the phase of the last braking step)
vals = []
for s0 in np.linspace(0.0, A * dt * dt, 401):
    n_steps = int(round((0.5 + STROKE / V + 1.0) / dt))
    s, u = s0, 0.0
    step, half = A * dt, 0.5 * A * dt
    dmax = 0.0
    for i in range(n_steps):
        up = np.sqrt(half * half + 2 * A * max(STROKE - s, 0.0)) - half
        tgt = min(V, up)
        un = u + np.clip(tgt - u, -step, step)
        sn = s + un * dt
        if sn > STROKE:
            sn = STROKE
            un = (sn - s) / dt
        dmax = max(dmax, abs(un - u))
        s, u = sn, un
    vals.append(dmax / step)
print(f"end-phase scan dt 2e-4 (401 start offsets): max |du|/(a dt) = {max(vals):.6f}, min = {min(vals):.6f}")
