"""Ramp-release residual factor for crawler lift-off (spec rev 40, item 3).

Residual free-vibration amplitude after a linear ramp of duration t_r applied to an
undamped SDOF, relative to the step response amplitude: |sinc(w t_r / 2)|.
Also estimates the heave travel that releases the last crawler load and the heave
speed needed for a given ramp time. Inputs from dynamics_model.md 5.25 (rev 38).
"""
import json
import numpy as np

f_mode1 = 1.86   # Hz, sway-roll (top auger, lift-off geometry)
f_heave = 7.73   # Hz
k_leg = 2.1e7    # N/m per leg, L1 lumped (assumption from CLAUDE.md)
n_leg = 4
F_pivot = np.array([60e3, 90e3])  # N, residual pivot load released at lift-off (L2b)
v_max = 20.924e-3  # m/s

def factor(f, tr):
    x = 2 * np.pi * f * tr / 2
    return float(abs(np.sinc(x / np.pi)))

trs = [0.05, 0.1, 0.2, 0.3, 0.4, 0.537, 0.6, 0.8, 1.0]
out = {"mode1": {str(t): factor(f_mode1, t) for t in trs},
       "heave": {str(t): factor(f_heave, t) for t in trs}}
dz = F_pivot / (n_leg * k_leg)  # m, heave travel to unload pivot (crawler rigid)
out["release_travel_mm"] = (dz * 1e3).tolist()
t_zero = 1 / f_mode1  # first sinc zero: w t_r / 2 = pi -> t_r = 1/f
out["t_r_first_zero_mode1_s"] = t_zero
out["heave_speed_for_first_zero_mm_s"] = (dz / t_zero * 1e3).tolist()
out["t_r_at_vmax_s"] = (dz / v_max).tolist()
# time cost if the controller must creep over an uncertainty window w at speed v
for w_mm in (2.0, 5.0):
    v = dz.max() / t_zero
    out[f"extra_time_window_{w_mm:.0f}mm_s"] = w_mm * 1e-3 / v - w_mm * 1e-3 / v_max
print(json.dumps(out, indent=1))
