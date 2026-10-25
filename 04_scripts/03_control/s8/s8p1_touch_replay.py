"""Offline replay of the C2 TOUCH 'touch_seen' rule on recorded readings (all p1 cases).

current : free-air median over TOUCH samples with (k+1) T < 5 s, from TOUCH entry
          (c2.py _touchdown_load_N), touch_seen latched on one sample >= 1.5 F_min.
fixed   : per leg, free-air samples only after the motor stroke advanced >= 0.5 mm since
          TOUCH entry (friction reversed), touch evaluation only with >= 3 such samples,
          touch_seen on 2 consecutive samples.
Reading = controller nominal reading (F_lower series: equals the nominal without fallback /
allowance). Reports: legs with touch_seen while the pad is in the air (pad_in_contact False
in the 1 ms record at the sample), and the first touch_seen time vs the first contact time.
"""
import sys, os, json, numpy as np

base = sys.argv[1]
T = 0.1
F_MIN = 9414.58911
LEVEL = 1.5 * F_MIN
ROD_W = 1047.2
out = {}
for name in sorted(os.listdir(base)):
    d = os.path.join(base, name)
    if not os.path.isdir(d):
        continue
    r8 = np.load(os.path.join(d, "r8_series.npz"))
    rec = np.load(os.path.join(d, "record", "record.npz"))
    ph = r8["phase"]
    k_t = np.flatnonzero(ph == "touch")
    if not k_t.size:
        continue
    k0 = k_t[0]
    k_end = k_t[-1]
    F = r8["F_lower_N"]
    s = rec["s_motor"]
    contact = rec["pad_in_contact"]
    t = r8["t"]
    res = {}
    for rule in ("current", "fixed"):
        seen_air, first_seen = [], []
        for leg in range(4):
            free = []
            consec = 0
            fs = None
            air_flag = False
            for j, k in enumerate(range(k0, k_end + 1)):
                if rule == "current":
                    if (j + 1) * T < 5.0:
                        free.append(F[k, leg])
                    ok_eval = len(free) > 0
                    cond = ok_eval and F[k, leg] - np.median(free) - ROD_W >= LEVEL
                    hit = cond
                else:
                    moved = s[k, leg] - s[k0, leg] >= 0.5e-3
                    if moved and (j + 1) * T < 5.0 + 0.5 and len(free) < 40:
                        free.append(F[k, leg])
                    ok_eval = len(free) >= 3
                    cond = ok_eval and F[k, leg] - np.median(free) - ROD_W >= LEVEL
                    consec = consec + 1 if cond else 0
                    hit = consec >= 2
                if hit and fs is None:
                    fs = t[k]
                    if not contact[k, leg]:
                        air_flag = True
            seen_air.append(air_flag)
            first_seen.append(None if fs is None else round(float(fs), 2))
        res[rule] = {"seen_in_air": seen_air, "first_seen_t": first_seen}
    k_c = [next((round(float(t[k]), 2) for k in range(k0, len(t)) if contact[k, leg]), None) for leg in range(4)]
    res["first_contact_t"] = k_c
    out[name] = res
    print(f"{name:26s} cur air {np.array(res['current']['seen_in_air']).astype(int)} seen {res['current']['first_seen_t']} | "
          f"fix air {np.array(res['fixed']['seen_in_air']).astype(int)} seen {res['fixed']['first_seen_t']} | contact {k_c}")
json.dump(out, open(sys.argv[2], "w"), indent=1)
