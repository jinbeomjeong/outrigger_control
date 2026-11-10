"""All R16 phases (after analyze_r16.py) and the R12 phase row: distribution and overlap. Read only.

Overlap definition as judgement_chrono/judge_chrono.py saturation_vs_event: flow limit acting in
[event, event + ramp + 5 s]. Outputs tables_r16/round2_results.json.
Usage: python -I analyze_round2.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\agent-ae9039e69988d5282")
MAIN = Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(WT / "03_src"))
OUT = HERE / "tables_r16"
S8 = MAIN / "07_results" / "S8"
LEGS = ("FL", "FR", "RL", "RR")
F_MIN = 9.41458911
ROWS_R12 = ("run", "3 F_min (1 ms)", "3 F_min before the event", "3 F_min in the event transient per leg (report)",
            "3 F_min after the re-READY", "item 9 J_P M1 missed / M1' late / M3 median / M2 / M4 max (record)",
            "item 9 J_C M1 missed / M1' late / M3 median / M2 / M4 max (record)", "4 saturation steps",
            "2 attitude +-0.2 (+mount)", "re-approach starts (report)")


def saturation(case_dir: Path) -> dict:
    res = json.loads((case_dir / "result.json").read_text(encoding="utf-8"))
    te, ramp = float(res["event_t_s"]), float(res["event"]["spec"]["ramp_s"])
    z = np.load(case_dir / "flow_series.npz", allow_pickle=True)
    rows, cols, supply = z["rows"], [str(c) for c in z["columns"]], float(z["supply_m3_s"])
    idx = {c: i for i, c in enumerate(cols)}
    t = rows[:, idx["t"]]
    if t[-1] > float(res["s8_end"]["end_t_s"]) + 1.0:
        t = t - float(res["runner"]["start_t_s"])
    lim = rows[:, idx["limited_mask"]].astype(int) > 0
    edges = np.diff(np.concatenate(([0], lim.astype(int), [0])))
    runs = [{"rel_start_s": round(float(t[a] - te), 3), "rel_stop_s": round(float(t[b - 1] - te), 3),
             "dur_s": round(float(t[b - 1] - t[a]), 3)}
            for a, b in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1), strict=True)]
    sel = (t >= te) & (t <= te + ramp + 5.0)
    qd = rows[:, idx["Q_dem"]]
    return {"event_t_s": te, "ramp_s": ramp, "overlap_event_ramp_plus5": bool(lim[sel].any()),
            "limited_s_in_window": float(lim[sel].sum() * float(np.median(np.diff(t)))),
            "max_Q_dem_window_L_min": float(qd[sel].max() * 6e4), "short_s_in_window": float((qd[sel] > supply * (1 + 1e-6)).sum() * float(np.median(np.diff(t)))),
            "supply_L_min": supply * 6e4, "runs_ge_50ms": [r for r in runs if r["dur_s"] >= 0.05],
            "nearest_run_after_event": next((r for r in runs if r["rel_stop_s"] >= 0.0), None),
            "phases": res["phases"], "ready_s": res.get("ready_t_s"), "end_s": res["s8_end"]["end_t_s"],
            "final_phase": res["s8_end"]["final_phase"], "wall_s": res["runner"]["wall_s"],
            "phase_at_event": res["event_state"]["phase_at_event"], "phase_offset_s": res["event_state"]["phase_offset_s"]}


def event_min(case_dir: Path) -> dict:
    res = json.loads((case_dir / "result.json").read_text(encoding="utf-8"))
    rec = np.load(case_dir / "record" / "record.npz", allow_pickle=False)
    p = np.load(case_dir / "pads.npz", allow_pickle=False)
    off = float(rec["t"][-1]) - float(res["s8_end"]["end_t_s"])
    t, Fm = p["t"] - off, p["F_cyl_min_interval"] / 1e3
    te = float(res["event_t_s"])
    post = (t >= te) & (t <= te + 20.0)
    air = p["airborne"].astype(bool)
    dtp = np.diff(t, prepend=t[0] - 1e-3)
    return {leg: {"min_kN": float(Fm[post, i].min()), "t_rel_s": float(t[post][np.argmin(Fm[post, i])] - te),
                  "airborne_s": float(dtp[post][air[post, i]].sum())} for i, leg in enumerate(LEGS)}


def main() -> None:
    from outrigger_sim.verify.s8_control import judge_batch

    r16 = json.loads((OUT / "r16_results.json").read_text(encoding="utf-8"))
    runs = {k: v for k, v in r16["runs"].items() if k.startswith("r16_")}
    dist = {}
    for leg in ("FL", "FR", "RL", "RR"):
        x = np.array([v["legs"][leg]["min_kN"] for v in runs.values()])
        dist[leg] = {"n": int(x.size), "min": float(x.min()), "median": float(np.median(x)), "max": float(x.max()),
                     "below_F_min": int((x < F_MIN).sum())}
    tau = {k: v["tau_te_mm"] for k, v in runs.items()}
    jc = "item 9 J_C M1 missed / M1' late / M3 median / M2 / M4 max (record)"
    jp = "item 9 J_P M1 missed / M1' late / M3 median / M2 / M4 max (record)"
    table = {k: {"delta_mm": round(1e3 * (v["offsets_m"][0] + 0.002), 3), "tau_te_mm": v["tau_te_mm"], "D_te_kN": v["D_te_kN"], "D_pre_kN": v["D_pre_1s_kN"],
                 "FR": v["legs"]["FR"], "RL": v["legs"]["RL"], "FL": v["legs"]["FL"], "RR": v["legs"]["RR"],
                 "J_C": r16["rows"][jc]["values"].get(k), "J_P": r16["rows"][jp]["values"].get(k),
                 "ready_s": v["ready_first_s"], "wall_s": v["wall_s"], "failed": v["judge_meta"]["failed"],
                 "s_te_mm_rows": None, "t_touch_end_s": v["t_touch_end_s"], "event_t_s": v["event_t_s"],
                 "starts": r16["rows"]["re-approach starts (report)"]["values"].get(k)} for k, v in runs.items()}
    # R12: phase row against the stored on and off rows
    new = next((HERE / "runs_r12").glob("*/E_G4_Fs4_ph0.05"))
    v_new = OUT / "verify_r12_eta085_ph005.json"
    if not v_new.exists():
        judge_batch(new.parent, v_new, root=MAIN, ref_batch=None, lookup_batches=[], deferred_ref=None)
    d_new = json.loads(v_new.read_text(encoding="utf-8"))
    vdir = MAIN / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono/verify"
    on = sorted(S8.glob("coupled_eta085_E_G4_Fs4_*"))[-1]
    off = sorted(S8.glob("final_E_G4_Fs4_2*"))[-1]
    d_on = json.loads((vdir / f"verify_{on.name}.json").read_text(encoding="utf-8"))
    d_off = json.loads((vdir / f"verify_{off.name}.json").read_text(encoding="utf-8"))
    r12: dict = {"new": {"sat": saturation(new), "legs": event_min(new), "meta": {k: d_new["meta"].get(k) for k in ("rows", "failed", "hold")}},
                 "stored_on": {"sat": saturation(on / "E_G4_Fs4"), "legs": event_min(on / "E_G4_Fs4"), "meta": {k: d_on["meta"].get(k) for k in ("rows", "failed", "hold")}},
                 "stored_off": {"legs": event_min(off / "E_G4_Fs4"), "meta": {k: d_off["meta"].get(k) for k in ("rows", "failed", "hold")}}}
    rows = {}
    for label, doc, cid in (("new", d_new, "E_G4_Fs4_ph0.05"), ("stored_on", d_on, "E_G4_Fs4"), ("stored_off", d_off, "E_G4_Fs4")):
        for r in doc["rows"]:
            if r.get("case") == cid:
                rows.setdefault(r["item"], {"kind": r.get("kind"), "limit": r.get("limit"), "values": {}})["values"][label] = r.get("value")
    r12["rows"] = rows
    for label, doc, cid in (("new", d_new, "E_G4_Fs4_ph0.05"), ("stored_on", d_on, "E_G4_Fs4"), ("stored_off", d_off, "E_G4_Fs4")):
        r12[label]["failed_items"] = [r["item"] for r in doc["rows"] if r.get("case") == cid and r.get("passed") is False]
    (OUT / "round2_results.json").write_text(json.dumps({"r16_table": table, "r16_dist": dist, "r12": r12}, indent=1, default=str), encoding="utf-8")
    for k, t in sorted(table.items(), key=lambda x: x[1]["delta_mm"]):
        print(k, "d", t["delta_mm"], "te", round(t["t_touch_end_s"], 1), "ev", round(t["event_t_s"], 2), "tau", round(t["tau_te_mm"], 3), "Dte", round(t["D_te_kN"], 2), "Dpre", round(t["D_pre_kN"], 2),
              "FR", round(t["FR"]["min_kN"], 2), round(t["FR"]["t_rel_s"], 2), "RL", round(t["RL"]["min_kN"], 2), round(t["RL"]["t_rel_s"], 2), "FL", round(t["FL"]["min_kN"], 2), round(t["FL"]["airborne_s"], 3), "RR", round(t["RR"]["min_kN"], 2), round(t["RR"]["airborne_s"], 3),
              "JC", t["J_C"][:2], "JP", t["J_P"][:2], "ready", t["ready_s"], "starts", t["starts"], "wall", round(t["wall_s"]), "failed", t["failed"])
    print("dist", json.dumps(dist))
    for label in ("stored_on", "new"):
        s = r12[label]["sat"]
        print(label, {k: s[k] for k in ("event_t_s", "phase_offset_s", "phase_at_event", "overlap_event_ramp_plus5", "limited_s_in_window", "short_s_in_window", "max_Q_dem_window_L_min", "supply_L_min", "ready_s", "end_s", "final_phase", "wall_s", "nearest_run_after_event")})
        print("   runs>=50ms", s["runs_ge_50ms"][:12])
        print("   phases", s["phases"])
    for label in ("stored_off", "stored_on", "new"):
        print(label, "meta", r12[label]["meta"], "failed", r12[label]["failed_items"], "legs", {k: (round(x["min_kN"], 2), round(x["t_rel_s"], 2), round(x["airborne_s"], 3)) for k, x in r12[label]["legs"].items()})
    for it in ROWS_R12:
        r = rows.get(it)
        if r:
            print(it[:60], "|", str(r["limit"])[:20], "| off", str(r["values"].get("stored_off"))[:90], "| on", str(r["values"].get("stored_on"))[:90], "| new", str(r["values"].get("new"))[:90])
    for it, r in rows.items():
        if r["kind"] in ("judged", "function", "anomaly") and r["values"].get("new") != r["values"].get("stored_on"):
            print("D", it[:70], "|", str(r["limit"])[:24], "| on", str(r["values"].get("stored_on"))[:80], "| new", str(r["values"].get("new"))[:80])


if __name__ == "__main__":
    main()
