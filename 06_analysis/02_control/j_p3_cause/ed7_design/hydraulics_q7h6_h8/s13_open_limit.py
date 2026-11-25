"""Q7-H8: h7 4.1 "head pressure open limit" table with and without the overlap tail.

Open limit = p_h at which need(p_h, s) equals the oil the line gets. need = retract_dead
(check_open_delay, VN, P1 split volumes, b0 / k_ext 0, F_band 0, void 0), p_r 5 bar (h7 H3 state).
Oil: h7 used the command 2.098 mm; the harness line gets command - u_ol tau_v (0.0418 mm,
overlap cut, spec 2.5) - the low-speed drain (0.0019 mm, P7-7 rebuild s11).

Usage: python -I -B s13_open_limit.py
"""
P_T, DELTA, PSI, P_CR = 2e5, 3e5, 3.5, 3e5
V_LINE, BETA_HOSE, L0, S_MAX = 285e-6, 0.5e9, 0.05, 0.70
LEGS = {"front": (0.013273229, 0.00376991118), "rear": (0.00950331778, 0.00314159265)}
CORNERS = {"nominal": (1.0e9, 1.0, 1.0), "slow": (0.69e9, 1.5, 1.5)}
U_OL_TAU = 0.02 * 0.0209243016 * 0.1      # 0.0418 mm
LOW_SPEED_DRAIN = 0.0019e-3
P_R = 5e5


def need_m(p_h, s, a_h, a_ann, beta, s_l, s_d, p_r=P_R, band=0.0):
    drive = p_h + P_CR - P_T
    p_free = max(drive / PSI, 0.0)
    if a_ann * (p_free - DELTA - p_r) > band:
        p_b = (drive - (a_ann * (DELTA + p_r) + band) / a_h) / (PSI - a_ann / a_h)
    else:
        p_b = p_free
    p_rod = max(p_b - DELTA, p_r)
    dp_h = max(a_ann * (p_rod - p_r) - band, 0.0) / a_h
    v_head = a_h * (L0 * s_d + s)
    v_rod = a_ann * (L0 * s_d + S_MAX - s)
    vol = (V_LINE * s_l * max(p_b - P_T, 0.0) / BETA_HOSE + v_rod * (p_rod - p_r) / beta
           + a_ann * v_head * dp_h / (beta * a_h))
    return vol / a_ann


def open_limit_bar(oil_m, s, a_h, a_ann, corner):
    lo, hi = 1e5, 400e5
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if need_m(mid, s, a_h, a_ann, *corner) <= oil_m:
            lo = mid
        else:
            hi = mid
    return lo / 1e5


oils = {"h7 (2.098)": 2.098e-3, "corrected (2.098 - tail - drain)": 2.098e-3 - U_OL_TAU - LOW_SPEED_DRAIN}
print(f"tail u_ol*tau_v = {U_OL_TAU * 1e3:.4f} mm, effective oil {oils['corrected (2.098 - tail - drain)'] * 1e3:.4f} mm")
for leg, (a_h, a_ann) in LEGS.items():
    for cname, corner in CORNERS.items():
        row = []
        for s in (0.25, 0.40, 0.55):
            old = open_limit_bar(oils["h7 (2.098)"], s, a_h, a_ann, corner)
            new = open_limit_bar(oils["corrected (2.098 - tail - drain)"], s, a_h, a_ann, corner)
            row.append(f"s {s * 1e3:.0f}: {old:6.1f} -> {new:6.1f} ({new - old:+.1f})")
        print(f"{leg:5s} {cname:7s} " + " | ".join(row))
