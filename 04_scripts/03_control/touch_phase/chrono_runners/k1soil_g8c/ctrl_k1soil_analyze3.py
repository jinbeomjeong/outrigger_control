"""Third pass: harness rows on/off, C-S8-41 windows against the off run in the same time span, end-of-run creep of the Fs8 on row,
twist tail after the event, and the binary export for the Julia cross-check. Read-only on the batch. Writes analyze3.json and xval/*.bin."""
import json
from pathlib import Path

import numpy as np

BATCH = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_k1soil_G1_20261105")
ACC = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance")
REV85 = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9\rev85")
HERE = Path(__file__).resolve().parent
LEGS = ("FL", "FR", "RL", "RR")
TAGS = ("FLFs0", "FLFs8", "RRFs0")
HKEY = {"FLFs0": "A|G1|FL|Fs0|two", "FLFs8": "A|G1|FL|Fs8|two", "RRFs0": "A|G1|RR|Fs0|two"}
out = {}

# harness
new = {r["key"]: r for r in json.loads((ACC / "soil/soil_A.json").read_text(encoding="utf-8"))["results"]}
old = {r["key"]: r for r in json.loads((REV85 / "finB2_A.json").read_text(encoding="utf-8"))["results"]}
FIELDS = ("timing", "event", "pair_union_s", "pair_last_touch_s", "W_end_s", "adj_min_F_in_W_kN", "min_F_after_W_kN", "t_ready_back_s", "reapproach_starts", "lifts", "pass", "flags", "t_ev_s")
out["harness"] = {}
for tag, key in HKEY.items():
    rec = {}
    for lab, src in (("on", new), ("off", old)):
        runs = [r for r in src[key]["runs"] if r.get("event") == "RE1bF" and r.get("timing") == "level"]
        rec[lab] = [{f: r.get(f) for f in FIELDS} for r in runs]
        rec[lab + "_hold"] = {k: src[key].get("base", {}).get(k) for k in ("t_loc", "t_done", "commands_sha256")}
        print(tag, lab, json.dumps(rec[lab], default=str)[:1100])
    rec["base_hash_same"] = rec["on_hold"]["commands_sha256"] == rec["off_hold"]["commands_sha256"]
    print(tag, "harness base hash same", rec["base_hash_same"])
    out["harness"][tag] = rec

# C-S8-41 windows, off in the same span
out["cs841"] = {}
for tag in TAGS:
    on = json.loads((BATCH / f"S9EV_G1_{tag}_RE1bF_on" / "result.json").read_text(encoding="utf-8"))
    off = json.loads((BATCH / f"S9EV_G1_{tag}_RE1bF_off" / "result.json").read_text(encoding="utf-8"))
    t0 = float(on["t_loop_start_s"])
    tev = float(on["soil_event"]["driver"]["t_ev_s"])
    zon = np.asarray(np.load(BATCH / f"S9EV_G1_{tag}_RE1bF_on" / "soil_event_series.npz")["rows"], float)
    zof = np.asarray(np.load(BATCH / f"S9EV_G1_{tag}_RE1bF_off" / "soil_event_series.npz")["rows"], float)
    w = []
    for win in on["p3b"]["P3-9_deferred"]["windows"]:
        leg = LEGS.index(win["leg"])
        a, b = win["window_s"]
        m_on = (zon[:, 0] >= a + t0 - 1e-9) & (zon[:, 0] <= b + t0 + 1e-9)
        m_of = (zof[:, 0] >= a + t0 - 1e-9) & (zof[:, 0] <= b + t0 + 1e-9)
        rec = {"leg": win["leg"], "deferred_rel_s": [round(x + t0 - tev, 2) for x in win["deferred_s"]], "window_rel_s": [round(a + t0 - tev, 2), round(b + t0 - tev, 2)], "min_on_kN": win["min_kN"], "min_on_check_kN": round(float(zon[m_on, 5 + leg].min()) / 1e3, 3),
               "min_off_same_span_kN": round(float(zof[m_of, 5 + leg].min()) / 1e3, 3), "below_F_min": win["below_F_min"], "flag_row": on["p3b"]["P3-9_deferred"]["flag"]}
        w.append(rec)
    out["cs841"][tag] = {"on": w, "off": off["p3b"]["P3-9_deferred"]["windows"], "flag_on": on["p3b"]["P3-9_deferred"]["flag"], "flag_off": off["p3b"]["P3-9_deferred"]["flag"], "n_flags_on": on["p3b"]["checks"]["P3-9_flags"], "n_flags_off": off["p3b"]["checks"]["P3-9_flags"]}
    print(tag, "C-S8-41", json.dumps(out["cs841"][tag]["on"]))

# end of run creep and twist
out["creep"] = {}
for tag in TAGS:
    for s in ("RE1bF_off", "RE1bF_on"):
        d = BATCH / f"S9EV_G1_{tag}_{s}"
        z = np.load(d / "step_series.npz")
        t = np.asarray(z["t_s"], float)
        rate = np.asarray(z["sinkage_rate_0p2s_m_s"], float)
        over = np.nanmax(rate, axis=1) >= 1e-4
        last = float(t[np.flatnonzero(over)[-1]]) if over.any() else None
        tail = t >= t[-1] - 10
        rp = np.asarray(z["roll_pitch_deg"], float)
        F = np.asarray(z["F_cyl_N"], float)
        D = (F[:, 0] + F[:, 3]) - (F[:, 1] + F[:, 2])
        res_cmd = np.load(d / "controller_commands.npz")
        tc, uc = res_cmd["t_s"], res_cmd["issued_u_m_s"]
        nz = np.flatnonzero(np.any(np.abs(uc) > 1e-12, axis=1))
        over_idx = np.flatnonzero(over)
        spans = []
        if over_idx.size:
            splits = np.split(over_idx, np.flatnonzero(np.diff(over_idx) > 1) + 1)
            spans = [[round(float(t[g[0]]), 3), round(float(t[g[-1]]), 3), round(float(np.nanmax(rate[g])) * 1e3, 4)] for g in splits[-6:]]
        rec = {"t_end_s": float(t[-1]), "last_rate_over_0p1mm_s_t_s": last, "rate_at_end_mm_s": (rate[-1] * 1e3).round(5).tolist(), "last_spans_t0_t1_maxrate_mm_s": spans, "last_nonzero_command_s": float(tc[nz[-1]]) if nz.size else None,
               "attitude_tail_range_deg": (rp[tail].max(axis=0) - rp[tail].min(axis=0)).round(5).tolist(), "D_tail_mean_kN": round(float(D[tail].mean()) / 1e3, 3), "D_tail_range_kN": round(float(D[tail].max() - D[tail].min()) / 1e3, 3)}
        out["creep"].setdefault(tag, {})[s] = rec
        print(tag, s, "creep", json.dumps(rec))

# binary export, same rows as the judge: t, contact x4, Fcyl x4 at the judge cut
xd = HERE / "xval"
xd.mkdir(exist_ok=True)
index = {}
for tag in TAGS:
    for s in ("RE1bF_off", "RE1bF_on"):
        d = BATCH / f"S9EV_G1_{tag}_{s}"
        res = json.loads((d / "result.json").read_text(encoding="utf-8"))
        r = np.asarray(np.load(d / "soil_event_series.npz")["rows"], dtype=np.float64)
        j = res["soil_event"]["judgement"]
        tev = float(res["soil_event"]["driver"]["t_ev_s"])
        r = r[r[:, 0] - tev <= float(j["stop_rel_s"]) + 1e-9][:, [0, 1, 2, 3, 4, 5, 6, 7, 8]]
        p = xd / f"{tag}_{s}.bin"
        r.astype("<f8").tofile(p)
        index[f"{tag}_{s}"] = {"path": str(p), "rows": int(r.shape[0]), "cols": 9, "t_ev": tev, "leg": tag[:2]}
(xd / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
(HERE / "analyze3.json").write_text(json.dumps(out, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
print("exported", {k: v["rows"] for k, v in index.items()})
