"""Per-case overview of the S8 p1 batch: phases, TOUCH duration, slow-approach legs, events."""
import sys, os, json, numpy as np

base = sys.argv[1]
VMAX = 20.924e-3
rows = []
for name in sorted(os.listdir(base)):
    d = os.path.join(base, name)
    if not os.path.isdir(d):
        continue
    res = json.load(open(os.path.join(d, "result.json"), encoding="utf-8"))
    r8 = np.load(os.path.join(d, "r8_series.npz"))
    rec = np.load(os.path.join(d, "record", "record.npz"))
    t = r8["t"]; ph = r8["phase"]; u = r8["issued_u"]
    st = res["settings"]
    tm = np.flatnonzero(ph == "touch")
    slow = []
    t_touch = (t[tm[0]], t[tm[-1]]) if len(tm) else (None, None)
    if len(tm):
        # legs moving below 0.5 v_max for > 50 % of the TOUCH samples while not stopped
        for leg in range(4):
            m = u[tm, leg]
            moving = m > 1e-6
            frac_slow = np.mean((m[moving] < 0.5 * VMAX)) if moving.any() else 0
            if frac_slow > 0.5:
                slow.append(leg)
    events = json.load(open(os.path.join(d, "controller_events.json"), encoding="utf-8"))
    ev_names = [e.split("name='")[1].rstrip("')") for e in events]
    ev_short = [e for e in ev_names if not e.startswith("INFO_PRESSURE_ZERO")]
    rows.append(dict(case=name, dur=st.get("duration_s"), event=(st.get("event") or {}).get("name") if isinstance(st.get("event"), dict) else st.get("event"),
                     t_end=float(t[-1]), touch=t_touch, touch_len=(t_touch[1] - t_touch[0]) if len(tm) else None,
                     slow_legs=slow, last_phase=str(ph[-1]), ready=res.get("ready_t_s"), event_t=res.get("event_t_s"),
                     ev=ev_short[:12], Fs=((res.get("s8_plant_record") or {}).get("seal_friction") or {}).get("F_s_N")))
for r in rows:
    tl = r["touch_len"]
    print(f"{r['case']:26s} dur={r['dur']} end={r['t_end']:.1f} touch={r['touch'][0]}-{r['touch'][1]} len={tl if tl is None else round(tl,1)} "
          f"slow={r['slow_legs']} last={r['last_phase']} ready={r['ready']} ev_t={r['event_t']} Fs={None if r['Fs'] is None else [round(x/1e3,2) for x in r['Fs']]}")
    print("     events:", r["ev"])
