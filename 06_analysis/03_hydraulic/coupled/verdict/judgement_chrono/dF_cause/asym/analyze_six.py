"""Six final-controller flow-off G4 rows (F_s 0, 4, 8 x event phase 0, 0.05) against the rev. 44 gate. Read only for stored data.

Usage: python -I -B -X utf8 analyze_six.py
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
VDIR = MAIN / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono/verify"
LEGS = ("FL", "FR", "RL", "RR")
N = np.array([0.47607202408216903, -0.47607202408216903, -0.5228340347436333, 0.5228340347436333])
JC = "item 9 J_C M1 missed / M1' late / M3 median / M2 / M4 max (record)"
JP = "item 9 J_P M1 missed / M1' late / M3 median / M2 / M4 max (record)"
F_MIN = 9.41458911


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
    pre = (t >= te - 1.0) & (t < te)
    return {"case": cid, "dir": str(d), "event_t_s": te, "phase_at_event": res["event_state"]["phase_at_event"], "ready_s": res.get("ready_t_s"), "legs": legs,
            "D_pre_kN": float(p["F_cyl"][pre].mean(axis=0) @ N / 1e3), "J_C": rows[JC]["value"], "J_P": rows[JP]["value"],
            "reready_s": rows["6 re-READY <= 40 s"]["value"], "F_min_row": rows["3 F_min (1 ms)"]["value"],
            "item6_min": rows["G4 item 6 (1) min after settlement >= F_min"]["value"], "final_phase": res["s8_end"]["final_phase"], "end_s": res["s8_end"]["end_t_s"],
            "wall_s": res["runner"]["wall_s"], "pid": json.loads((d / "case.json").read_text(encoding="utf-8"))["runner"]["pid"],
            "soil_stop_in_config": "soil_stop=True" in str(res["settings"].get("controller_config", "")),
            "failed": doc["meta"]["failed"], "hold": doc["meta"]["hold"], "failed_items": [r["item"] for r in rows.values() if r.get("passed") is False]}


def main() -> None:
    from outrigger_sim.verify.s8_control import judge_batch

    ph0 = sorted(HERE.glob("final_E_G4_Fs0Fs8_ph0_off_*"))[-1]
    v_ph0 = HERE / f"verify_{ph0.name}.json"
    if not v_ph0.exists():
        judge_batch(ph0, v_ph0, root=MAIN, ref_batch=None, lookup_batches=[], deferred_ref=None)
    d_ph0 = json.loads(v_ph0.read_text(encoding="utf-8"))
    ph5 = sorted(HERE.glob("final_E_G4_Fs0Fs8_ph0.05_off_*"))[-1]
    d_ph5 = json.loads((HERE / f"verify_{ph5.name}.json").read_text(encoding="utf-8"))
    f4_5 = sorted(HERE.glob("final_E_G4_Fs4_ph0.05_off_*"))[-1]
    d_f45 = json.loads((HERE / f"verify_{f4_5.name}.json").read_text(encoding="utf-8"))
    f4_0 = S8 / "final_E_G4_Fs4_20261030_233941"
    d_f40 = json.loads((VDIR / f"verify_{f4_0.name}.json").read_text(encoding="utf-8"))
    gate = json.loads((MAIN / "06_analysis/02_control/s8/s8_p1r_rev44_gate.json").read_text(encoding="utf-8"))["D_g4"]
    cells = {"E_G4_Fs0": side(ph0 / "E_G4_Fs0", d_ph0, "E_G4_Fs0"), "E_G4_Fs0_ph0.05": side(ph5 / "E_G4_Fs0_ph0.05", d_ph5, "E_G4_Fs0_ph0.05"),
             "E_G4_Fs4": side(f4_0 / "E_G4_Fs4", d_f40, "E_G4_Fs4"), "E_G4_Fs4_ph0.05": side(f4_5 / "E_G4_Fs4_ph0.05", d_f45, "E_G4_Fs4_ph0.05"),
             "E_G4_Fs8": side(ph0 / "E_G4_Fs8", d_ph0, "E_G4_Fs8"), "E_G4_Fs8_ph0.05": side(ph5 / "E_G4_Fs8_ph0.05", d_ph5, "E_G4_Fs8_ph0.05")}
    for cid, c in cells.items():
        g = gate[cid]
        c["gate_rr_kN"] = g["rr_min_own_kN"]
        c["gate_reready_s"] = g["judge_rerdy"]
        c["rr_minus_gate_kN"] = c["legs"]["RR"]["min_kN"] - g["rr_min_own_kN"]
        c["rr_equal_gate"] = c["legs"]["RR"]["min_kN"] == g["rr_min_own_kN"]
        c["other_legs_min_kN"] = min(c["legs"][q]["min_kN"] for q in ("FL", "FR", "RL"))
    per_fs = {}
    for fs in ("Fs0", "Fs4", "Fs8"):
        pair = {k: cells[k]["legs"]["RR"]["min_kN"] for k in (f"E_G4_{fs}", f"E_G4_{fs}_ph0.05")}
        pair_gate = {k: cells[k]["gate_rr_kN"] for k in pair}
        per_fs[fs] = {"min_kN": min(pair.values()), "at": min(pair, key=pair.get), "margin_to_F_min_kN": min(pair.values()) - F_MIN,
                      "gate_min_kN": min(pair_gate.values()), "gate_at": min(pair_gate, key=pair_gate.get)}
    overall = min(per_fs.items(), key=lambda kv: kv[1]["min_kN"])
    out = {"cells": cells, "tested_phase_min_per_fs": per_fs, "overall": overall, "F_min_kN": F_MIN,
           "code_state_ph0": json.loads((ph0 / "code_state.json").read_text(encoding="utf-8")), "meta_ph0": {k: d_ph0["meta"].get(k) for k in ("rows", "failed", "hold")}}
    (HERE / "six_cells_results.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    for k, c in cells.items():
        print(k, {q: (round(c[q], 4) if isinstance(c[q], float) else c[q]) for q in ("event_t_s", "phase_at_event", "ready_s", "D_pre_kN", "J_C", "J_P", "reready_s", "gate_reready_s", "F_min_row", "item6_min", "failed", "hold", "failed_items", "gate_rr_kN", "rr_minus_gate_kN", "rr_equal_gate", "soil_stop_in_config", "final_phase", "wall_s", "pid")})
        print("   legs", {g: (round(x["min_kN"], 3), round(x["t_rel_s"], 2), round(x["airborne_s"], 3)) for g, x in c["legs"].items()})
    print("per_fs", json.dumps(per_fs))
    print("overall", overall)
    print("meta ph0", out["meta_ph0"], "head", out["code_state_ph0"]["main_head"])
    # first plant divergence of the new phase-0 rows from p1r
    for cid in ("E_G4_Fs0", "E_G4_Fs8"):
        a, b = np.load(ph0 / cid / "record/record.npz", allow_pickle=False), np.load(S8 / "p1r_20261024_222013" / cid / "record/record.npz", allow_pickle=False)
        n = min(len(a["t"]), len(b["t"]))
        for key in ("meas.head_pressure", "F_cyl", "s_motor"):
            same = (a[key][:n] == b[key][:n]).reshape(n, -1).all(axis=1)
            print(cid, key, "first diff t", None if same.all() else float(a["t"][int(np.argmin(same))]), "rows", len(a["t"]), len(b["t"]))


if __name__ == "__main__":
    main()
