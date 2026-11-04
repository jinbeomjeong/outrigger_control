"""R12 event table of the new flow-off phase run against the stored rows, judge_batch, r8_series prefix. Read only for others.

Usage: python -I -B -X utf8 analyze_r12_off.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

MAIN = Path(r"C:\workspace\outrigger_control")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(MAIN / "03_src"))
S8 = MAIN / "07_results/S8"
VDIR = MAIN / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono/verify"
SC = Path(__file__).resolve().parents[1]
LEGS = ("FL", "FR", "RL", "RR")
JC = "item 9 J_C M1 missed / M1' late / M3 median / M2 / M4 max (record)"
JP = "item 9 J_P M1 missed / M1' late / M3 median / M2 / M4 max (record)"


def side(d: Path, doc: dict, cid: str) -> dict:
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    rec = np.load(d / "record" / "record.npz", allow_pickle=False)
    p = np.load(d / "pads.npz", allow_pickle=False)
    r8 = np.load(d / "r8_series.npz", allow_pickle=False)
    off = float(rec["t"][-1]) - float(res["s8_end"]["end_t_s"])
    t, Fm = p["t"] - off, p["F_cyl_min_interval"] / 1e3
    te = float(res["event_t_s"])
    post = (t >= te) & (t <= te + 20.0)
    air = p["airborne"].astype(bool)
    dtp = np.diff(t, prepend=t[0] - 1e-3)
    legs = {leg: {"min_kN": float(Fm[post, i].min()), "t_rel_s": float(t[post][np.argmin(Fm[post, i])] - te),
                  "airborne_s": float(dtp[post][air[post, i]].sum())} for i, leg in enumerate(LEGS)}
    rows = {r["item"]: r for r in doc["rows"] if r.get("case") == cid}
    events = json.loads((d / "controller_events.json").read_text(encoding="utf-8"))
    ev = []
    for e in events:
        m = re.match(r"C2Event\(t_s=([0-9.e+-]+), name='(.*)'\)", e)
        ev.append((float(m.group(1)) - off, m.group(2)))
    starts = [(round(a - te, 3), n) for a, n in ev if n.startswith("leg_reapproach") and a >= te]
    rt = r8["t"] - off
    cu = r8["cmp_reapproach_u"]
    k_rows = np.flatnonzero((rt >= te - 1e-9) & (np.abs(cu).max(axis=1) > 0.0))
    first = None
    if k_rows.size:
        k = int(k_rows[0])
        leg = int(np.argmax(np.abs(cu[k])))
        first = {"t_abs_s": float(rt[k]), "t_rel_event_s": float(rt[k] - te), "leg": LEGS[leg], "u_mm_s": float(cu[k, leg] * 1e3),
                 "F_lower_prev_kN": [float(v) for v in r8["F_lower_N"][k - 1] / 1e3], "F_lower_at_kN": [float(v) for v in r8["F_lower_N"][k] / 1e3],
                 "F_lower_est_prev_kN": [float(v) for v in r8["F_lower_est_N"][k - 1] / 1e3], "F_hat_prev_kN": [float(v) for v in r8["F_hat_N"][k - 1] / 1e3],
                 "t_prev_rel_event_s": float(rt[k - 1] - te)}
    pre = (t >= te - 1.0) & (t < te)
    return {"event_t_s": te, "phase_at_event": res["event_state"]["phase_at_event"], "phase_offset_s": res["event_state"]["phase_offset_s"],
            "legs": legs, "J_C": rows[JC]["value"], "J_P": rows[JP]["value"], "reready_s": rows["6 re-READY <= 40 s"]["value"],
            "failed": doc["meta"]["failed"], "hold": doc["meta"]["hold"], "judged_rows": doc["meta"]["rows"],
            "F_min_row": rows["3 F_min (1 ms)"]["value"], "D_pre_kN": float(p["F_cyl"][pre].mean(axis=0) @ np.array([0.47607202408216903, -0.47607202408216903, -0.5228340347436333, 0.5228340347436333]) / 1e3),
            "first_reapproach": first, "reapproach_events": starts, "ready_s": res.get("ready_t_s"), "end_s": res["s8_end"]["end_t_s"],
            "final_phase": res["s8_end"]["final_phase"], "wall_s": res["runner"]["wall_s"], "failed_items": [r["item"] for r in rows.values() if r.get("passed") is False]}


def prefix(a_dir: Path, b_dir: Path, event_abs: float) -> dict:
    a, b = np.load(a_dir / "r8_series.npz", allow_pickle=False), np.load(b_dir / "r8_series.npz", allow_pickle=False)
    n = min(len(a["t"]), len(b["t"]))
    first, keys = None, 0
    per_key = {}
    for key in a.files:
        if key not in b.files or a[key].ndim == 0:
            continue
        x, y = a[key][:n], b[key][:n]
        same = ((x == y) | (np.isnan(x) & np.isnan(y))) if x.dtype.kind == "f" else (x == y)
        same = same.reshape(n, -1).all(axis=1)
        keys += 1
        if not same.all():
            i = int(np.argmin(same))
            per_key[key] = float(a["t"][i])
            if first is None or i < first[0]:
                first = (i, key)
    return {"keys": keys, "rows_compared": n, "first_diff_key": None if first is None else first[1],
            "first_diff_t_abs": None if first is None else float(a["t"][first[0]]), "event_t_abs": event_abs,
            "rows_equal_before_event": None if first is None else first[0],
            "prev_sample_t_abs": None if first is None or first[0] == 0 else float(a["t"][first[0] - 1]),
            "first_diff_per_key": dict(sorted(per_key.items(), key=lambda kv: kv[1])[:10])}


def main() -> None:
    from outrigger_sim.verify.s8_control import judge_batch

    batch = sorted(HERE.glob("final_E_G4_Fs4_ph0.05_off_*"))[-1]
    v_new = HERE / f"verify_{batch.name}.json"
    if not v_new.exists():
        judge_batch(batch, v_new, root=MAIN, ref_batch=None, lookup_batches=[], deferred_ref=None)
    d_new = json.loads(v_new.read_text(encoding="utf-8"))
    off0 = S8 / "final_E_G4_Fs4_20261030_233941"
    on0 = sorted(S8.glob("coupled_eta085_E_G4_Fs4_*"))[-1]
    onph = SC / "cad_asym" / "runs_r12" / "r12_eta085_ph005"
    d_off = json.loads((VDIR / f"verify_{off0.name}.json").read_text(encoding="utf-8"))
    d_on = json.loads((VDIR / f"verify_{on0.name}.json").read_text(encoding="utf-8"))
    d_onph = json.loads((SC / "cad_asym" / "tables_r16" / "verify_r12_eta085_ph005.json").read_text(encoding="utf-8"))
    table = {"off_ph0": side(off0 / "E_G4_Fs4", d_off, "E_G4_Fs4"), "off_ph005": side(batch / "E_G4_Fs4_ph0.05", d_new, "E_G4_Fs4_ph0.05"),
             "on_ph0": side(on0 / "E_G4_Fs4", d_on, "E_G4_Fs4"), "on_ph005": side(onph / "E_G4_Fs4_ph0.05", d_onph, "E_G4_Fs4_ph0.05")}
    pre = prefix(batch / "E_G4_Fs4_ph0.05", off0 / "E_G4_Fs4", table["off_ph005"]["event_t_s"] + 3.0)
    rows_diff = {}
    a = {r["item"]: r for r in d_new["rows"] if r.get("case") == "E_G4_Fs4_ph0.05"}
    b = {r["item"]: r for r in d_off["rows"] if r.get("case") == "E_G4_Fs4"}
    for it in a:
        if a[it].get("kind") in ("judged", "function", "anomaly") and a[it].get("value") != (b.get(it) or {}).get("value"):
            rows_diff[it] = {"limit": a[it].get("limit"), "off_ph0": (b.get(it) or {}).get("value"), "off_ph005": a[it].get("value")}
    out = {"batch": str(batch), "table": table, "prefix_vs_off_ph0": pre, "judged_rows_changed": rows_diff}
    (HERE / "r12_off_results.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    for k, v in table.items():
        print(k, {q: (round(v[q], 3) if isinstance(v[q], float) else v[q]) for q in ("event_t_s", "phase_at_event", "D_pre_kN", "J_C", "J_P", "reready_s", "failed", "hold", "F_min_row", "ready_s", "end_s", "final_phase", "wall_s", "failed_items")})
        print("   legs", {g: (round(x["min_kN"], 2), round(x["t_rel_s"], 2), round(x["airborne_s"], 3)) for g, x in v["legs"].items()})
        print("   first", v["first_reapproach"])
        print("   events", v["reapproach_events"])
    print("prefix", json.dumps(pre))
    for it, r in rows_diff.items():
        print("D", it[:75], "|", str(r["limit"])[:22], "|", str(r["off_ph0"])[:70], "|", str(r["off_ph005"])[:70])
    print((batch / "code_state.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
