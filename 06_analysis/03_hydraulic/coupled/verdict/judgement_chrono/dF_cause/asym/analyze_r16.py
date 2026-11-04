"""R16 gap runs: project judge (worktree code, verify files in ./tables_r16) and event values. Read only for the
runs and for the stored batch. Definitions of the event block as judgement_chrono/judge_chrono.py event_detail.

Usage: python -I analyze_r16.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\agent-ae9039e69988d5282")
MAIN = Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(WT / "03_src"))
OUT = HERE / "tables_r16"
CASE = "G1L_RE1bF_FL_top_o050_Fs4"
STORED = MAIN / "07_results/S8/final_G1L_RE1bF_FL_top_o050_Fs4_20261031_004637"
STORED_VERIFY = MAIN / ("06_analysis/03_hydraulic/coupled/verdict/judgement_chrono/verify/"
                        "verify_final_G1L_RE1bF_FL_top_o050_Fs4_20261031_004637.json")
LEGS = ("FL", "FR", "RL", "RR")
TWIST = np.array([0.47607202408216903, -0.47607202408216903, -0.5228340347436333, 0.5228340347436333])
JUDGED = ("judged", "function", "anomaly")


def judge(batch: Path, name: str) -> dict:
    from outrigger_sim.verify.s8_control import judge_batch

    out = OUT / f"verify_{name}.json"
    if not out.exists():
        judge_batch(batch, out, root=MAIN, ref_batch=None, lookup_batches=[], deferred_ref=None)
    return json.loads(out.read_text(encoding="utf-8"))


def event_values(d: Path) -> dict:
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    rec = np.load(d / "record" / "record.npz", allow_pickle=False)
    p = np.load(d / "pads.npz", allow_pickle=False)
    s8 = np.load(d / "r8_series.npz", allow_pickle=False)
    off = float(rec["t"][-1]) - float(res["s8_end"]["end_t_s"])
    t, F, Fm = p["t"] - off, p["F_cyl"] / 1e3, p["F_cyl_min_interval"] / 1e3
    air = p["airborne"].astype(bool)
    te = float(res["event_t_s"])
    post = (t >= te) & (t <= te + 20)
    dtp = np.diff(t, prepend=t[0] - 1e-3)
    legs = {}
    for i, leg in enumerate(LEGS):
        x = Fm[post, i]
        j = int(np.argmin(x))
        legs[leg] = {"min_kN": float(x[j]), "t_rel_s": float(t[post][j] - te), "airborne_s": float(dtp[post][air[post, i]].sum())}
    pre = (t >= te - 1.0) & (t < te)
    F_pre = F[pre].mean(axis=0)
    pt = s8["t"] - off
    t_touch = float(pt[np.flatnonzero(~np.isin(s8["phase"], ("idle", "check", "touch")))[0]])
    k = int(np.searchsorted(t, t_touch))
    s = p["s_motor"] * 1e3
    # first pad contact per leg (N_raw > 0) and body attitude in the world frame around it
    raw = p["N_raw"]
    first = [int(np.argmax(raw[:, i] > 0.0)) for i in range(4)]
    w, x, y, z = p["body_quat_wxyz"].T
    pitch = np.degrees(np.arcsin(2.0 * (w * y - z * x)))
    roll = np.degrees(np.arctan2(2.0 * (w * x + y * z), 1.0 - 2.0 * (x * x + y * y)))
    k0 = min(first)
    k_ref = (t >= t[k0] - 1.0) & (t < t[k0] - 0.5)  # machine still on the crawler, no pad load
    pitch0, roll0 = float(pitch[k_ref].mean()), float(roll[k_ref].mean())
    sm = np.convolve(F.sum(axis=1), np.ones(20) / 20, "same")
    crf = np.linalg.norm(rec["F_crawler"], axis=1) / 1e3
    crt = rec["t"] - off
    W = float(np.median(F[(t > t_touch - 8) & (t < t_touch - 6)].sum(axis=1)) + np.median(crf[(crt > t_touch - 8) & (crt < t_touch - 6)]))
    t_lift = float(t[np.flatnonzero((t > t_touch) & (W - sm < 3.0))[0]])
    k_lift = int(np.searchsorted(t, t_lift))
    contact = {
        "rule": "first N_raw > 0 per leg; pitch, roll = world angles from body_quat_wxyz (same formula as dF_cause/decompose.py), "
                "rise = minus the mean over [first contact - 1 s, first contact - 0.5 s]",
        "t_first_s": [float(t[q]) for q in first],
        "t_first_rel_touch_end_s": [float(t[q] - t_touch) for q in first],
        "s_motor_mm": [float(s[first[i], i]) for i in range(4)],
        "s_link_mm": [float(p["s_link"][first[i], i] * 1e3) for i in range(4)],
        "pitch_ref_deg": pitch0, "roll_ref_deg": roll0,
        "pitch_rise_at_first_deg": [float(pitch[q] - pitch0) for q in first],
        "roll_rise_at_first_deg": [float(roll[q] - roll0) for q in first],
        "pitch_rise_at_touch_end_deg": float(pitch[k] - pitch0),
        "pitch_rise_max_before_lift_deg": float((pitch[k0:k_lift] - pitch0).max()),
        "pitch_rise_min_before_lift_deg": float((pitch[k0:k_lift] - pitch0).min()),
        "pitch_rise_at_lift_deg": float(pitch[k_lift] - pitch0),
        "t_lift_s": t_lift,
    }
    events = json.loads((d / "controller_events.json").read_text(encoding="utf-8"))
    names = [e.split("name='")[1].rstrip("')") for e in events]
    keep = [(round(float(e.split("t_s=")[1].split(",")[0]) - off - te, 2), n) for e, n in zip(events, names, strict=True)
            if not n.startswith(("INFO_PRESSURE_ZERO", "INFO_D1"))]
    return {
        "contact": contact,
        "event_t_s": te, "phase_at_event": res["event_state"]["phase_at_event"], "t_touch_end_s": t_touch,
        "tau_te_mm": float(TWIST @ s[k]), "D_te_kN": float(F[k - 200:k].mean(axis=0) @ TWIST),
        "D_pre_1s_kN": float(F_pre @ TWIST), "F_pre_1s_kN": F_pre.tolist(), "legs": legs,
        "ready_first_s": res.get("ready_t_s"), "final_phase": res["s8_end"]["final_phase"], "end_s": res["s8_end"]["end_t_s"],
        "timeout": res["s8_end"]["timeout"], "events_rel": keep, "wall_s": res["runner"]["wall_s"],
        "us_per_step": res["runner"]["us_per_step"], "n_steps": res["runner"]["n_steps"],
        "offsets_m": (json.loads((d / "case.json").read_text(encoding="utf-8")).get("run_meta") or {}).get("engine", {}).get("pad_gap_offsets_m"),
    }


def main() -> None:
    OUT.mkdir(exist_ok=True)
    report: dict = {"runs": {}, "rows": {}}
    stored_doc = judge(STORED, "stored_worktree_code")
    ref = json.loads(STORED_VERIFY.read_text(encoding="utf-8"))
    a = {r["item"]: r.get("value") for r in stored_doc["rows"] if r.get("case") == CASE}
    b = {r["item"]: r.get("value") for r in ref["rows"] if r.get("case") == CASE}
    report["judge_stored_vs_saved_verify"] = {"rows": len(a), "rows_saved": len(b), "different": [k for k in set(a) | set(b) if a.get(k) != b.get(k)]}
    docs = {"stored_off": (STORED / CASE, stored_doc)}
    for rid in sorted(p.name for p in (HERE / "runs_r16").iterdir() if (p / CASE / "result.json").exists()):
        docs[rid] = (HERE / "runs_r16" / rid / CASE, judge(HERE / "runs_r16" / rid, rid))
    items: list[str] = []
    for name, (d, doc) in docs.items():
        report["runs"][name] = event_values(d)
        report["runs"][name]["judge_meta"] = {k: doc["meta"].get(k) for k in ("rows", "failed", "hold")}
        report["runs"][name]["row_failed_items"] = [r["item"] for r in doc["rows"] if r.get("case") == CASE and r.get("passed") is False]
        for r in doc["rows"]:
            if r.get("case") == CASE:
                report["rows"].setdefault(r["item"], {"kind": r.get("kind"), "limit": r.get("limit"), "values": {}})["values"][name] = r.get("value")
                if r["item"] not in items:
                    items.append(r["item"])
    (OUT / "r16_results.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    names = list(docs)
    with (OUT / "r16_rows.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["item", "kind", "limit", *names])
        for it in items:
            r = report["rows"][it]
            w.writerow([it, r["kind"], json.dumps(r["limit"], default=str), *[json.dumps(r["values"].get(n), default=str) for n in names]])
    print(json.dumps(report["judge_stored_vs_saved_verify"]))
    for n, v in report["runs"].items():
        print(n, {k: (round(v[k], 3) if isinstance(v[k], float) else v[k]) for k in ("event_t_s", "phase_at_event", "t_touch_end_s", "tau_te_mm", "D_te_kN", "D_pre_1s_kN", "ready_first_s", "final_phase", "end_s", "timeout", "wall_s", "offsets_m", "judge_meta", "row_failed_items")})
        print("   F_pre", np.round(v["F_pre_1s_kN"], 1), {k: (round(x["min_kN"], 2), round(x["t_rel_s"], 2), round(x["airborne_s"], 3)) for k, x in v["legs"].items()})
        print("   contact", {k: (np.round(c, 4).tolist() if not isinstance(c, str) else None) for k, c in v["contact"].items() if k != "rule"})
        print("   ev", v["events_rel"])
    for it in items:
        r = report["rows"][it]
        if r["kind"] in JUDGED or any(s in it for s in ("window end", "1 ms instantaneous", "item 9 J_", "re-approach", "record: re-approach", "M5", "transient")):
            print(repr(it)[:70], r["kind"], "lim", str(r["limit"])[:32])
            for n in names:
                print("     ", n[-8:], str(r["values"].get(n))[:210])


if __name__ == "__main__":
    main()
