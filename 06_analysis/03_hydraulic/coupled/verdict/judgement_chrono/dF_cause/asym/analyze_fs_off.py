"""F_s 0 and 8 flow-off phase rows against the rev. 44 gate and the stored p1r rows. Read only for the stored data.

Usage: python -I -B -X utf8 analyze_fs_off.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

MAIN = Path(r"C:\workspace\outrigger_control")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(MAIN / "03_src"))
S8 = MAIN / "07_results/S8"
P1R = S8 / "p1r_20261024_222013"
LEGS = ("FL", "FR", "RL", "RR")
N = np.array([0.47607202408216903, -0.47607202408216903, -0.5228340347436333, 0.5228340347436333])
JC = "item 9 J_C M1 missed / M1' late / M3 median / M2 / M4 max (record)"
JP = "item 9 J_P M1 missed / M1' late / M3 median / M2 / M4 max (record)"


def side(d: Path, doc: dict, cid: str) -> dict:
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    rec = np.load(d / "record" / "record.npz", allow_pickle=False)
    p = np.load(d / "pads.npz", allow_pickle=False)
    off = float(rec["t"][-1]) - float(res["s8_end"]["end_t_s"])
    t, Fm = p["t"] - off, p["F_cyl_min_interval"] / 1e3
    te = float(res["event_t_s"])
    post = (t >= te) & (t <= te + 20.0)
    air = p["airborne"].astype(bool)
    dtp = np.diff(t, prepend=t[0] - 1e-3)
    legs = {leg: {"min_kN": float(Fm[post, i].min()), "t_rel_s": float(t[post][np.argmin(Fm[post, i])] - te),
                  "airborne_s": float(dtp[post][air[post, i]].sum())} for i, leg in enumerate(LEGS)}
    rows = {r["item"]: r for r in doc["rows"] if r.get("case") == cid}
    get = lambda k: (rows.get(k) or {}).get("value")  # noqa: E731
    pre = (t >= te - 1.0) & (t < te)
    return {"event_t_s": te, "phase_at_event": res["event_state"]["phase_at_event"] if res.get("event_state") else None, "legs": legs,
            "D_pre_kN": float(p["F_cyl"][pre].mean(axis=0) @ N / 1e3), "J_C": get(JC), "J_P": get(JP), "reready_s": get("6 re-READY <= 40 s"),
            "F_min_row": get("3 F_min (1 ms)"), "ready_s": res.get("ready_t_s"), "end_s": res["s8_end"]["end_t_s"], "final_phase": res["s8_end"]["final_phase"],
            "wall_s": res["runner"]["wall_s"], "pid": json.loads((d / "case.json").read_text(encoding="utf-8"))["runner"]["pid"],
            "soil_stop_in_config": "soil_stop=True" in str(res["settings"].get("controller_config", "")),
            "failed_items": [r["item"] for r in rows.values() if r.get("passed") is False], "rows": rows}


def compare(a_dir: Path, b_dir: Path) -> dict:
    out = {}
    for rel, tk in (("r8_series.npz", "t"), ("record/record.npz", "t")):
        a, b = np.load(a_dir / rel, allow_pickle=False), np.load(b_dir / rel, allow_pickle=False)
        n = min(len(a[tk]), len(b[tk]))
        first, count, missing = None, 0, [k for k in a.files if k not in b.files]
        for key in a.files:
            if key not in b.files or a[key].ndim == 0 or len(a[key]) != len(a[tk]) or len(b[key]) != len(b[tk]) or a[key].dtype.kind not in "fiubU":
                continue
            x, y = a[key][:n], b[key][:n]
            same = ((x == y) | (np.isnan(x) & np.isnan(y))) if x.dtype.kind == "f" else (x == y)
            same = same.reshape(n, -1).all(axis=1)
            count += 1
            if not same.all():
                i = int(np.argmin(same))
                if first is None or i < first[0]:
                    first = (i, key, float(a[tk][i]))
        out[rel] = {"arrays": count, "rows_a": len(a[tk]), "rows_b": len(b[tk]), "first_diff": first, "keys_only_new": missing}
    return out


def main() -> None:
    from outrigger_sim.verify.s8_control import judge_batch

    batch = sorted(HERE.glob("final_E_G4_Fs0Fs8_ph0.05_off_*"))[-1]
    v_new = HERE / f"verify_{batch.name}.json"
    if not v_new.exists():
        judge_batch(batch, v_new, root=MAIN, ref_batch=None, lookup_batches=[], deferred_ref=None)
    d_new = json.loads(v_new.read_text(encoding="utf-8"))
    d_p1r = json.loads((P1R / "verify_S8C.json").read_text(encoding="utf-8"))
    gate = json.loads((MAIN / "06_analysis/02_control/s8/s8_p1r_rev44_gate.json").read_text(encoding="utf-8"))["D_g4"]
    table = {}
    for cid in ("E_G4_Fs0_ph0.05", "E_G4_Fs8_ph0.05"):
        table[f"new {cid}"] = side(batch / cid, d_new, cid)
    for cid in ("E_G4_Fs0", "E_G4_Fs0_ph0.05", "E_G4_Fs8", "E_G4_Fs8_ph0.05"):
        table[f"p1r {cid}"] = side(P1R / cid, d_p1r, cid)
    report = {"batch": str(batch), "meta_new": {k: d_new["meta"].get(k) for k in ("rows", "failed", "hold")},
              "meta_p1r": {k: d_p1r["meta"].get(k) for k in ("rows", "failed", "hold")}, "table": {}, "gate_vs_new": {}, "bits_vs_p1r": {}, "rows_changed": {}}
    for k, v in table.items():
        report["table"][k] = {q: v[q] for q in v if q != "rows"}
        print(k, {q: (round(v[q], 3) if isinstance(v[q], float) else v[q]) for q in ("event_t_s", "phase_at_event", "D_pre_kN", "J_C", "J_P", "reready_s", "F_min_row", "ready_s", "end_s", "final_phase", "wall_s", "pid", "soil_stop_in_config", "failed_items")})
        print("   legs", {g: (round(x["min_kN"], 2), round(x["t_rel_s"], 2), round(x["airborne_s"], 3)) for g, x in v["legs"].items()})
    print("meta new", report["meta_new"], "meta p1r", report["meta_p1r"])
    for cid in ("E_G4_Fs0_ph0.05", "E_G4_Fs8_ph0.05"):
        g = gate[cid]
        new = table[f"new {cid}"]
        cmp = {"gate_rr_min_own_kN": g["rr_min_own_kN"], "new_rr_kN": new["legs"]["RR"]["min_kN"], "new_F_min_row": new["F_min_row"],
               "exact_equal": g["rr_min_own_kN"] == new["legs"]["RR"]["min_kN"], "diff_kN": new["legs"]["RR"]["min_kN"] - g["rr_min_own_kN"],
               "gate_judge_item6_1": g["judge_item6_1"], "gate_reready_s": g["judge_rerdy"], "new_reready_s": new["reready_s"],
               "gate_event_t": g["event_t"], "new_event_t": new["event_t_s"]}
        report["gate_vs_new"][cid] = cmp
        print("gate", cid, cmp)
        bits = compare(batch / cid, P1R / cid)
        report["bits_vs_p1r"][cid] = bits
        print("bits", cid, bits)
        a, b = table[f"new {cid}"]["rows"], table[f"p1r {cid}"]["rows"]
        ch = {it: {"limit": a[it].get("limit"), "new": a[it].get("value"), "p1r": (b.get(it) or {}).get("value")}
              for it in a if a[it].get("kind") in ("judged", "function", "anomaly") and a[it].get("value") != (b.get(it) or {}).get("value")}
        report["rows_changed"][cid] = ch
        for it, r in ch.items():
            print("  D", it[:70], "|", str(r["limit"])[:20], "| new", str(r["new"])[:60], "| p1r", str(r["p1r"])[:60])
    (HERE / "fs_off_results.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    print((batch / "code_state.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
