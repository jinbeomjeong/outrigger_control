"""k06: discrete twist-loop margins against the stiffness ratio r over the clipped scale.

Loop (negative feedback on the twist load D = n^T F, c2.py 3817-3853 ``twist_rates``):
  controller  tau_dot_k = -K_tw * D_f,k / (k_nom * sigma)        (K_tw 0.5 1/s, c2.py 1519-1524)
  filter      D_f = first-order forward-Euler low-pass, T/tau = 0.1/0.2 (c2.py 1527, 4682-4684;
              sensors/attitude.py 43-77: pole 1 - T/tau = 0.5, F(z) = 0.5 z / (z - 0.5))
  output      one period delay d = 1 (R8_D1_SETTINGS output_delay_periods 1, c2.py 1628), ZOH
  plant       valve lag tau_v = 0.1 s (harness HARNESS_VALVE_TAU_S, harness_hydraulics.py 101,
              ASSUMPTION for the machine, U-R8-9) and dD/dt = k_tw,true * tau_dot
  => L(z) = g * K_tw * z^-1 * ZOH{1 / (s (tau_v s + 1))}(z) * F(z),  g = r / sigma,
     r = k_tw,true / k_nom (the probe ratio is its proxy), sigma = clipped scale in [1.0, 1.5].
The dead band (2 kN) and the guard term are left out (linear small-signal loop around |D| > 2 kN).

Writes loop JSONs (ctrl_verify.py margins input, ``tools/control/README.md``) for chosen g and a
table of GM / PM / Ms / delay margin over g; finds the largest g meeting PM >= 45 deg, GM >= 6 dB,
Ms <= 2.0 (ASSUMPTION: the usual classical floors, not a project spec).

Usage: conda run -n dynamics-dev python -I -B k06_twist_margins.py
Output: k06_out.txt, k06_margins.json, loops/loop_g*.json (this folder).
"""
import json
import math
from pathlib import Path

import control as ct
import numpy as np

HERE = Path(__file__).resolve().parent
TS = 0.1
K_TW = 0.5
TAU_V = 0.1
F_POLE = 0.5


def loop(g: float) -> ct.TransferFunction:
    plant = ct.sample_system(ct.tf([1.0], [TAU_V, 1.0, 0.0]), TS, method="zoh")
    delay = ct.tf([1.0], [1.0, 0.0], TS)
    filt = ct.tf([1.0 - F_POLE, 0.0], [1.0, -F_POLE], TS)
    return g * K_TW * delay * plant * filt


W = np.concatenate([np.logspace(-4, math.log10(math.pi / TS) - 1e-9, 200000), [math.pi / TS]])


def metrics(L: ct.TransferFunction) -> dict:
    """Dense-grid margins (unwrapped phase from the integrator end; linear interpolation of the
    crossings), Ms over the grid. The tool ctrl_verify.py margins re-checks chosen loops."""
    resp = L(np.exp(1j * W * TS))
    mag = np.abs(resp)
    ph = np.unwrap(np.angle(resp))
    ms = float(np.max(np.abs(1.0 / (1.0 + resp))))
    gc = np.flatnonzero((mag[:-1] - 1.0) * (mag[1:] - 1.0) <= 0)
    wgc = pm = math.nan
    if len(gc):
        i = int(gc[0])
        a = (1.0 - mag[i]) / (mag[i + 1] - mag[i])
        wgc = float(W[i] + a * (W[i + 1] - W[i]))
        pm = float(math.degrees(ph[i] + a * (ph[i + 1] - ph[i])) + 180.0)
    target = -math.pi
    pc = np.flatnonzero((ph[:-1] - target) * (ph[1:] - target) <= 0)
    wpc = gm = math.inf
    if len(pc):
        i = int(pc[0])
        a = (target - ph[i]) / (ph[i + 1] - ph[i])
        wpc = float(W[i] + a * (W[i + 1] - W[i]))
        gm = float(1.0 / (mag[i] + a * (mag[i + 1] - mag[i])))
    cl = ct.feedback(L, 1)
    poles = cl.poles()
    return {"gm": float(gm), "gm_db": 20 * math.log10(gm) if gm > 0 else None, "pm_deg": float(pm),
            "wpc": float(wpc), "wgc": float(wgc),
            "dm_s": math.radians(pm) / wgc if wgc > 0 else None, "ms": ms,
            "cl_max_abs_pole": float(np.max(np.abs(poles)))}


def main() -> int:
    rows = []
    for g in np.round(np.arange(0.4, 4.01, 0.05), 4):
        rows.append({"g": float(g), **metrics(loop(float(g)))})
    ok = [r for r in rows if r["pm_deg"] >= 45 and r["gm_db"] is not None and r["gm_db"] >= 6 and r["ms"] <= 2.0]
    g_max = max(r["g"] for r in ok) if ok else None
    # bisection of the exact limits of each criterion
    def limit(pred):
        lo, hi = 0.4, 8.0
        if not pred(lo):
            return None
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if pred(mid) else (lo, mid)
        return lo
    lim = {
        "pm45": limit(lambda g: metrics(loop(g))["pm_deg"] >= 45.0),
        "gm6db": limit(lambda g: metrics(loop(g))["gm_db"] >= 6.0),
        "ms2": limit(lambda g: metrics(loop(g))["ms"] <= 2.0),
        "stable": limit(lambda g: metrics(loop(g))["cl_max_abs_pole"] < 1.0),
    }
    ref = {name: {"g": g, **metrics(loop(g))} for name, g in (
        ("nominal_r1_sigma1", 1.0), ("pre_probe_r1_sigma1.2", 1 / 1.2),
        ("r2.3_sigma1.5", 2.3 / 1.5), ("r3.0_sigma1.5", 3.0 / 1.5), ("r3.6_sigma1.5", 3.6 / 1.5),
        ("r0.8_sigma1.0", 0.8))}
    loops = HERE / "loops"
    loops.mkdir(exist_ok=True)
    for name, item in ref.items():
        g = item["g"]
        L = loop(g)
        num = [float(v) for v in np.asarray(L.num[0][0]).ravel()]
        den = [float(v) for v in np.asarray(L.den[0][0]).ravel()]
        (loops / f"loop_{name}.json").write_text(json.dumps(
            {"plant": {"tf": {"num": num, "den": den}}, "dt": TS, "feedback": "negative"}, indent=1),
            encoding="utf-8")
    out = {"model": "L(z) = g K_tw z^-1 ZOH{1/(s(tau_v s+1))} 0.5z/(z-0.5), Ts 0.1 s",
           "K_tw_1_s": K_TW, "tau_v_s": TAU_V, "Ts_s": TS, "filter_pole": F_POLE,
           "g_max_all_criteria_grid": g_max, "limits_g": lim,
           "limits_r_at_sigma_1.5": {k: (None if v is None else 1.5 * v) for k, v in lim.items()},
           "reference": ref, "table": rows}
    (HERE / "k06_margins.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    lines = [out["model"], f"limits g: {lim}", f"limits r (sigma 1.5): {out['limits_r_at_sigma_1.5']}"]
    for name, item in ref.items():
        lines.append(f"{name}: g={item['g']:.4f} GM={item['gm']:.3f} ({item['gm_db']:.2f} dB) @ {item['wpc']:.4f} rad/s, "
                     f"PM={item['pm_deg']:.2f} deg @ {item['wgc']:.4f} rad/s, DM={item['dm_s']:.3f} s, Ms={item['ms']:.3f}, "
                     f"max|z_cl|={item['cl_max_abs_pole']:.4f}")
    (HERE / "k06_out.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
