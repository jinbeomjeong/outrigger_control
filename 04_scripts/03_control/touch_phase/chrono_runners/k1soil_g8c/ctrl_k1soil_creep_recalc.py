"""P3-4 of the stored S9 rows with the sinkage-rate window 0.2 s (present rule) and 1.0 s (proposal). No simulation, no code change.

creep_stop and p34_judgement_window are copied from run_S9.py of the pinned checkout (the module imports pychrono). The 0.2 s pass must reproduce
the stored P3-4 row (reproduction column). Rows come from dyn_k1osc/a06_scan.json; rows without p3b or step_series are listed apart.
Writes k1soil/creep_window_recalc.json and prints changes only.
"""
import json
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control\07_results\S9")
SCAN = Path(r"C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\dyn_k1osc\a06_scan.json")
OUT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\chrono\k1soil\creep_window_recalc.json")
LIMIT = 1.0e-4
ATT = 0.2
MIN_W = 5.0


def sinkage_rate(t, s, w):
    j = np.searchsorted(t, t - w + 1e-9, side="right") - 1
    valid = j >= 0
    j = np.maximum(j, 0)
    rate = np.full_like(s, np.nan)
    rate[valid] = (s[valid] - s[j[valid]]) / (t[valid, None] - t[j[valid], None])
    return rate


def creep(t, s, t_from, w):
    if t_from is None:
        return {"two": None, "signed": None}
    rate = sinkage_rate(t, s, w)
    valid = np.all(np.isfinite(rate), axis=1)
    after = (t >= t_from - 1e-12) & valid

    def final(ok):
        k = np.nonzero(ok)[0]
        if not k.size or not ok[-1]:
            return None
        bad = np.nonzero(after & ~ok)[0]
        return float(t[k[0]]) if not bad.size else float(t[bad[-1] + 1])

    return {"signed": final(after & np.all(rate < LIMIT, axis=1)), "two": final(after & np.all(np.abs(rate) < LIMIT, axis=1))}


def p34(t, rp, cs, phases):
    readies = [tp for k, (tp, ph) in enumerate(phases) if ph == "ready" and (k == 0 or phases[k - 1][1] != "ready")]
    t_ready = readies[-1] if readies else None
    t_creep = cs["two"] if cs["two"] is not None else cs["signed"]
    flags = []
    if t_ready is None:
        flags.append("no_ready")
    if t_creep is None:
        flags.append("no_creep_stop")
    if cs["two"] is None and cs["signed"] is not None:
        flags.append("creep_vibration_suspect")
    if "no_ready" in flags or "no_creep_stop" in flags:
        return {"within": False, "absmax": None, "t0w": None, "len": None, "flags": flags + ["window_short"], "t_creep": t_creep}
    t0w = max(t_ready, t_creep)
    w = t >= t0w - 1e-9
    short = float(t[-1]) - t0w < MIN_W - 1e-9 or not w.any()
    if short:
        flags.append("window_short")
    a = float(np.abs(rp[w]).max()) if w.any() else float("nan")
    return {"within": bool(w.any() and a <= ATT), "absmax": round(a, 5), "t0w": round(t0w, 3), "len": round(float(t[-1]) - t0w, 2), "flags": flags, "t_creep": t_creep}


def main():
    rows, skipped = [], []
    for s in json.loads(SCAN.read_text(encoding="utf-8")):
        d = ROOT / s["batch"] / s["case"]
        if not (d / "step_series.npz").exists():
            d = next((p.parent for p in ROOT.rglob(f"{s['case']}/step_series.npz") if p.parent.parent.name == s["batch"]), d)
        try:
            res = json.loads((d / "result.json").read_text(encoding="utf-8"))
            pb = res["p3b"]
            stored = pb["checks"]
            t_from = pb["creep_stop"]["t_from_s"]
            z = np.load(d / "step_series.npz")
            t = np.asarray(z["t_s"], float)
            sink = np.asarray(z["pad_sinkage_geometric_m"], float)
            rp = np.asarray(z["roll_pitch_deg"], float)
            phases = [(float(p["t_s"]), str(p["phase"])) for p in res["phases"]]
        except Exception as e:  # noqa: BLE001 - listed apart
            skipped.append({"batch": s["batch"], "case": s["case"], "why": repr(e)[:90]})
            continue
        a = p34(t, rp, creep(t, sink, t_from, 0.2), phases)
        b = p34(t, rp, creep(t, sink, t_from, 1.0), phases)
        st_w = stored.get("P3-4_within_0p2")
        st_a = stored.get("P3-4_absmax_deg")
        repro = st_w == a["within"] and (st_a is None and a["absmax"] is None or (st_a is not None and a["absmax"] is not None and abs(st_a - a["absmax"]) < 1e-3))
        rows.append({"batch": s["batch"], "case": s["case"], "soil_event": bool(res.get("soil_event")), "stored_within": st_w, "stored_flags": stored.get("P3-4_flags"), "w02": a, "w10": b, "repro": bool(repro), "final_phase": phases[-1][1] if phases else None, "t_end": float(t[-1])})
    changed = [r for r in rows if r["w02"]["within"] != r["w10"]["within"]]
    p2f = [r for r in changed if r["w02"]["within"]]
    f2p = [r for r in changed if not r["w02"]["within"]]
    flags = [r for r in rows if r["w02"]["flags"] != r["w10"]["flags"] and r not in changed]
    gl = [r["w10"]["absmax"] - r["w02"]["absmax"] for r in rows if r["w02"]["absmax"] is not None and r["w10"]["absmax"] is not None]
    longer = [r["w02"]["t0w"] - r["w10"]["t0w"] for r in rows if r["w02"]["t0w"] is not None and r["w10"]["t0w"] is not None]
    summary = {"rows": len(rows), "skipped": len(skipped), "repro_ok": sum(r["repro"] for r in rows), "pass_0p2": sum(r["w02"]["within"] for r in rows), "pass_1p0": sum(r["w10"]["within"] for r in rows), "pass_to_fail": len(p2f), "fail_to_pass": len(f2p), "flag_change_only": len(flags),
               "absmax_change_deg": [round(min(gl), 5), round(max(gl), 5)] if gl else None, "window_start_earlier_s": [round(min(longer), 2), round(max(longer), 2)] if longer else None, "worst_absmax_1p0": max((r["w10"]["absmax"] for r in rows if r["w10"]["absmax"] is not None), default=None)}
    OUT.write_text(json.dumps({"rule": "P3-4 window from max(two-sided creep stop, last READY entry) to run end, limit 0.2 deg, window < 5 s = window_short; rate limit 0.1 mm/s unchanged, rate window 0.2 s vs 1.0 s", "summary": summary, "rows": rows, "skipped": skipped}, indent=1), encoding="utf-8")
    print(json.dumps(summary))
    print("NOT REPRO", [(r["case"], r["stored_within"], r["w02"]["within"], r["w02"]["absmax"]) for r in rows if not r["repro"]][:30])
    for name, g in (("P2F", p2f), ("F2P", f2p), ("FLAGS", flags)):
        print(name)
        for r in g:
            print(" ", r["batch"][:24], r["case"], r["final_phase"], "| 0.2:", r["w02"]["within"], r["w02"]["absmax"], r["w02"]["t0w"], r["w02"]["len"], r["w02"]["flags"], "| 1.0:", r["w10"]["within"], r["w10"]["absmax"], r["w10"]["t0w"], r["w10"]["len"], r["w10"]["flags"])
    print("FAIL both", [(r["case"], r["w10"]["flags"], r["w10"]["absmax"], r["final_phase"]) for r in rows if not r["w02"]["within"] and not r["w10"]["within"]])
    print("SKIPPED", skipped[:8])


if __name__ == "__main__":
    main()
