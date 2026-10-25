"""Spec rev. 44: S8 p1 rerun (p1r) acceptance conditions of spec rev. 43 213.6.

Reads two batches (p1 re-judged with the rev. 43 judge, and p1r) and writes one JSON with
  A. F_s 0 regression p1 -> p1r: TOUCH end, D8 min (C1, outside REANCHOR), first READY
  B. F_s 8 (and WIKA / E) TOUCH length vs the same-floor F_s 0 twin (p1r)
  C. free-air touch_seen: path 1 = controller command (raw_u < 0.5 v_max in TOUCH, i.e.
     touch_seen approach 0.25 v_max or a waiting candidate 0) while the pad had no contact in the
     1 ms pad record over the reading period; path 2 = offline replay of the P-S8-6 rule on the
     recorded nominal readings (independent implementation)
  D. G4 8 cases: RR min after the event (1 ms F_cyl_min_interval, own) vs judge rows, re-READY
  E. 1.4 F_min side effect: leg_reapproach_start inside PROBE windows and event-free READY
     windows, D8 min change p1 -> p1r
  F. wall time per case, P / E core placement (case.log), wall per simulated second
Usage: python -I s8p1r_gate.py <p1 dir> <p1r dir> <out json>
Time bases: r8_series / record / pads 't' = record time; phases and metrics times = controller
time = record time - 3 s; controller_events t_s = record time.
"""
import sys, os, re, json
import numpy as np

P1, P1R, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
T0 = 3.0
T = 0.1
VMAX = 20.924e-3
F_MIN = 9414.58911
TOUCH_LEVEL = 1.5 * F_MIN
ROD_W = np.array([1047.2, 1047.2, 718.0, 718.0])
LEGS = ("FL", "FR", "RL", "RR")


def load_verify(base):
    v = json.load(open(os.path.join(base, "verify_S8C.json"), encoding="utf-8"))
    met = {m["case"]: m for m in v["metrics"]}
    rows = {}
    for r in v["rows"]:
        rows.setdefault(r["case"], []).append(r)
    return v, met, rows


def events(base, case):
    ev = json.load(open(os.path.join(base, case, "controller_events.json"), encoding="utf-8"))
    out = []
    for e in ev:
        t = float(re.search(r"t_s=([0-9.eE+-]+)", e).group(1)) - T0
        out.append((t, re.search(r"name='([^']+)'", e).group(1)))
    return out


def phase_intervals(phases, t_end):
    iv = []
    for i, (t, p) in enumerate(phases):
        t1 = phases[i + 1][0] if i + 1 < len(phases) else t_end
        iv.append((p, t, t1))
    return iv


def first_len(phases, name, t_end):
    for p, a, b in phase_intervals(phases, t_end):
        if p == name:
            return b - a, b
    return None, None


def wall_info(base):
    j = json.load(open(os.path.join(base, "batch.json"), encoding="utf-8"))
    out = {}
    for c in j["cases"]:
        log = open(os.path.join(base, c["case_id"], "case.log"), encoding="utf-8", errors="replace").read()
        m = re.search(r"placement \{'mode': '(\w+)'", log)
        out[c["case_id"]] = dict(wall_s=c["wall_s"], placement=m.group(1) if m else None)
    return j["wall_s"], out


v1, m1, rows1 = load_verify(P1)
v2, m2, rows2 = load_verify(P1R)
res = {"inputs": {"p1": P1, "p1r": P1R, "p1_judge": v1["meta"]["judge_revision"],
                  "p1r_judge": v2["meta"]["judge_revision"],
                  "p1r_rows": v2["meta"]["rows"], "p1r_failed": v2["meta"]["failed"]}}


def summary(met, case):
    m = met[case]
    tl, tend = first_len(m["phases"], "touch", m["times_s"]["end"])
    return dict(touch_len=tl, touch_end=tend, ready=m.get("ready_s"), d8=m.get("min_cyl_excl_reanchor_kN"),
                final=m.get("final_phase"), end=m["times_s"]["end"], att=m.get("att_err_last5_maxabs_deg"))


# ---- A. F_s 0 regression ----------------------------------------------------------------
A = {}
for case in sorted(m2):
    if not case.endswith("Fs0") and "_Fs0_" not in case:
        continue
    if case not in m1:
        continue
    a, b = summary(m1, case), summary(m2, case)
    d = {k: (None if a[k] is None or b[k] is None else b[k] - a[k]) for k in ("touch_end", "d8", "ready")}
    ok = (d["touch_end"] is not None and abs(d["touch_end"]) <= 0.3 + 1e-9
          and (d["d8"] is None or abs(d["d8"]) <= 1.0) and (d["ready"] is None or abs(d["ready"]) <= 1.0))
    A[case] = dict(p1=a, p1r=b, diff=d, passed=bool(ok))
r413 = [r for rr in rows2.values() for r in rr if r["item"].startswith("R41-3")]
res["A_fs0_regression"] = A
res["A_k0v_vs_s7_rows"] = [{k: r.get(k) for k in ("case", "value", "limit", "passed", "note")} for r in r413]

# ---- B. TOUCH length vs F_s 0 twin -------------------------------------------------------
def twin(case):
    if case.startswith("K8_"):
        floor = case.split("_")[2]
        for g in ("K0", "K0V"):
            c = f"{g}_top_{floor}_Fs0"
            if c in m2:
                return c
    if case.startswith("S_"):
        floor = case.split("_")[2]
        return f"K0V_top_{floor}_Fs0"
    if case.startswith("N_D8"):
        return "K0V_top_rpB_Fs0"
    if case.startswith("E_"):
        c = re.sub(r"_Fs[0-9]+", "_Fs0", case)
        if c in m2:
            return c
        return "E_G4_Fs0" if "HOLD" in case else None
    return None


B = {}
for case in sorted(m2):
    if case.endswith("Fs0") or "_Fs0_" in case:
        continue
    tw = twin(case)
    a, b = summary(m2, case), summary(m2, tw) if tw else None
    dl = None if b is None else a["touch_len"] - b["touch_len"]
    B[case] = dict(twin=tw, touch_len=a["touch_len"], twin_touch_len=None if b is None else b["touch_len"],
                   diff=dl, passed=None if dl is None else bool(dl <= 1.0 + 1e-9),
                   ready=a["ready"], twin_ready=None if b is None else b["ready"], final=a["final"])
res["B_touch_len_vs_fs0"] = B

# ---- C. free-air touch_seen ---------------------------------------------------------------
C = {}
for case in sorted(m2):
    d = os.path.join(P1R, case)
    r8 = np.load(os.path.join(d, "r8_series.npz"))
    pads = np.load(os.path.join(d, "pads.npz"))
    ph = r8["phase"]
    kt = np.flatnonzero(ph == "touch")
    if not kt.size:
        C[case] = None
        continue
    t = r8["t"]
    tp = pads["t"]
    Nraw = pads["N_raw"]

    def contact_in_period(k, leg):
        w = (tp > t[k] - T + 1e-9) & (tp <= t[k] + 1e-9)
        return bool((Nraw[w, leg] > 0).any())

    first_contact = []
    for leg in range(4):
        idx = np.flatnonzero((tp >= t[kt[0]]) & (Nraw[:, leg] > 0))
        first_contact.append(None if not idx.size else float(tp[idx[0]] - T0))
    # path 1: controller command
    p1_air, p1_first = [], []
    raw = r8["raw_u"]
    for leg in range(4):
        air = []
        fs = None
        for k in kt:
            slow = 0.0 < raw[k, leg] < 0.5 * VMAX - 1e-9 or raw[k, leg] == 0.0
            if slow:
                if fs is None and raw[k, leg] > 0:
                    fs = float(t[k] - T0)
                if not contact_in_period(k, leg):
                    air.append(round(float(t[k] - T0), 2))
        p1_air.append(air)
        p1_first.append(fs)
    # path 2: offline replay of P-S8-6 (fixed rule) on nominal readings
    Fn = r8["F_nominal_N"]
    rec = np.load(os.path.join(d, "record", "record.npz"))
    s = rec["s_motor"]
    k0 = kt[0]
    p2_first, p2_air = [], []
    for leg in range(4):
        free, consec, fs, air = [], 0, None, False
        t_move = None
        for k in kt:
            moved = s[k, leg] - s[k0, leg] >= 0.5e-3
            if moved and t_move is None:
                t_move = t[k]
            if moved and t[k] - t_move < 5.0 - 1e-9:
                free.append(Fn[k, leg])
            ok = len(free) >= 3
            cond = ok and Fn[k, leg] - np.median(free) - ROD_W[leg] >= TOUCH_LEVEL
            consec = consec + 1 if cond else 0
            if consec >= 2 and fs is None:
                fs = float(t[k] - T0)
                air = not contact_in_period(k, leg)
        p2_first.append(fs)
        p2_air.append(air)
    C[case] = dict(first_contact=first_contact, cmd_slow_first=p1_first, cmd_slow_in_air=p1_air,
                   replay_seen_first=p2_first, replay_seen_in_air=p2_air,
                   air_latch=int(sum(len(a) > 0 for a in p1_air)))
res["C_touch_seen_air"] = C

# ---- D. G4 ---------------------------------------------------------------------------------
D = {}
for case in sorted(m2):
    if not case.startswith("E_G4"):
        continue
    d = os.path.join(P1R, case)
    rj = json.load(open(os.path.join(d, "result.json"), encoding="utf-8"))
    t_ev = rj["event_t_s"]
    pads = np.load(os.path.join(d, "pads.npz"))
    tp = pads["t"] - T0
    w = (tp >= t_ev) & (tp <= t_ev + 10.0)
    fmin = pads["F_cyl_min_interval"][w, 3]
    k = int(np.argmin(fmin))
    ev = events(P1R, case)
    after = [(round(tt - t_ev, 2), n) for tt, n in ev if tt >= t_ev - 1e-6 and not n.startswith("INFO")]
    rows = {r["item"]: r for r in rows2[case]}
    D[case] = dict(event_t=t_ev, rr_min_own_kN=float(fmin[k] / 1e3), at_ev_plus_s=float(tp[w][k] - t_ev),
                   judge_item6_1=rows.get("G4 item 6 (1) min after settlement >= F_min", {}).get("value"),
                   judge_6min=rows.get("6 min after settlement", {}).get("value"),
                   judge_rerdy=rows.get("6 re-READY <= 40 s", {}).get("value"),
                   p1_rr_min=None, events_after=after[:10])
    if case in m1:
        rows_p1 = {r["item"]: r for r in rows1[case]}
        D[case]["p1_rr_min"] = rows_p1.get("6 min after settlement", {}).get("value")
res["D_g4"] = D

# ---- E. 1.4 side effect --------------------------------------------------------------------
E = {}
for case in sorted(m2):
    m = m2[case]
    ev = events(P1R, case)
    iv = phase_intervals(m["phases"], m["times_s"]["end"])
    t_event = json.load(open(os.path.join(P1R, case, "result.json"), encoding="utf-8")).get("event_t_s")
    starts = [tt for tt, n in ev if n.startswith("leg_reapproach_start")]
    in_probe, in_ready_free = [], []
    for tt in starts:
        for p, a, b in iv:
            if a - 1e-9 <= tt < b - 1e-9:
                if p == "probe":
                    in_probe.append(round(tt, 2))
                if p == "ready" and (t_event is None or tt < t_event - 1e-9):
                    in_ready_free.append(round(tt, 2))
    d8a = m1[case].get("min_cyl_excl_reanchor_kN") if case in m1 else None
    d8b = m.get("min_cyl_excl_reanchor_kN")
    E[case] = dict(starts=[round(x, 2) for x in starts], in_probe=in_probe, in_event_free_ready=in_ready_free,
                   event_t=t_event, d8_p1=d8a, d8_p1r=d8b, d8_diff=None if d8a is None or d8b is None else d8b - d8a)
res["E_reapproach"] = E
res["E_F7_rows"] = [{k: r.get(k) for k in ("case", "value", "limit", "passed")}
                    for rr in rows2.values() for r in rr if r["item"].startswith("F7")]

# ---- F. wall time -------------------------------------------------------------------------
Fw = {}
for tag, base, met in (("p1", P1, m1), ("p1r", P1R, m2)):
    tot, info = wall_info(base)
    for c, x in info.items():
        sim = met[c]["times_s"]["end"] + T0 if c in met else None
        x["sim_s"] = sim
        x["wall_per_sim"] = None if sim is None else x["wall_s"] / sim
    Fw[tag] = dict(batch_wall_s=tot, cases=info)
pairs = []
for c in Fw["p1r"]["cases"]:
    if c in Fw["p1"]["cases"]:
        a, b = Fw["p1"]["cases"][c], Fw["p1r"]["cases"][c]
        if a["placement"] != b["placement"] and a["wall_per_sim"] and b["wall_per_sim"]:
            e, p = (a, b) if a["placement"] == "ecore" else (b, a)
            pairs.append(dict(case=c, e_rate=e["wall_per_sim"], p_rate=p["wall_per_sim"],
                              ratio=e["wall_per_sim"] / p["wall_per_sim"]))
rates = {}
for tag in ("p1", "p1r"):
    for pl in ("pcore", "ecore"):
        v = [x["wall_per_sim"] for x in Fw[tag]["cases"].values() if x["placement"] == pl and x["wall_per_sim"]]
        rates[f"{tag}_{pl}"] = dict(n=len(v), median=float(np.median(v)) if v else None,
                                    min=float(np.min(v)) if v else None, max=float(np.max(v)) if v else None)
Fw["swap_pairs"] = pairs
Fw["rates"] = rates
res["F_wall"] = Fw

json.dump(res, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=float)

# ---- print ---------------------------------------------------------------------------------
print("A. F_s 0 regression (p1r - p1): touch_end / D8 / READY")
for c, x in A.items():
    d = x["diff"]
    print(f"  {c:26s} {d['touch_end']:+.2f} s  {d['d8'] if d['d8'] is None else round(d['d8'], 3)} kN  "
          f"{d['ready'] if d['ready'] is None else round(d['ready'], 2)} s  final {x['p1r']['final']} pass {x['passed']}")
for r in res["A_k0v_vs_s7_rows"]:
    print("  R41-3", r)
print("B. TOUCH length vs twin")
for c, x in B.items():
    print(f"  {c:26s} {x['touch_len']:.2f} vs {x['twin']} {x['twin_touch_len']} diff {x['diff']} pass {x['passed']} "
          f"ready {x['ready']} final {x['final']}")
print("C. free-air touch_seen")
for c, x in C.items():
    if x is None:
        print(f"  {c:26s} no TOUCH")
        continue
    print(f"  {c:26s} air {x['air_latch']} cmd_first {[None if v is None else round(v, 2) for v in x['cmd_slow_first']]} "
          f"replay {[None if v is None else round(v, 2) for v in x['replay_seen_first']]} replay_air {x['replay_seen_in_air']} "
          f"contact {[None if v is None else round(v, 3) for v in x['first_contact']]}")
print("D. G4")
for c, x in D.items():
    print(f"  {c:18s} own {x['rr_min_own_kN']:.2f} kN @ev+{x['at_ev_plus_s']:.2f} | judge 6min {x['judge_6min']} item6(1) {x['judge_item6_1']} "
          f"reREADY {x['judge_rerdy']} | p1 {x['p1_rr_min']}")
    print("      ", x["events_after"])
print("E. re-approach")
for c, x in E.items():
    if x["starts"] or (x["d8_diff"] is not None and abs(x["d8_diff"]) > 0.0):
        print(f"  {c:26s} starts {x['starts']} probe {x['in_probe']} readyfree {x['in_event_free_ready']} ev {x['event_t']} "
              f"d8 {x['d8_p1']} -> {x['d8_p1r']} ({x['d8_diff']})")
for r in res["E_F7_rows"]:
    print("  F7", r)
print("F. wall")
print("  batch", Fw["p1"]["batch_wall_s"], Fw["p1r"]["batch_wall_s"])
print("  rates", json.dumps(rates, indent=None))
for p in pairs:
    print("  swap", p)
