"""Episode-window 1 ms values of J_C misses, event leg, band origin, later behaviour of the leg, run outcome."""
import json
import os
from collections import Counter
from pathlib import Path

import numpy as np

S = r"C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\ctrl_v4den"
ROOT = r"C:\workspace\outrigger_control"
ML = Path(ROOT) / r"07_results\S8\ml_main_20261025_090131"
LEGS = ("FL", "FR", "RL", "RR")
FMIN = 9.41458911
h = json.load(open(S + r"\ml_jc_head.json", encoding="utf-8"))
done = False
all_out = []
for name in ("test", "OOD-1", "OOD-2", "MLJ", "validation", "train"):
    rows_all = {}
    for it in h[name]:
        for r in it["rows"]:
            rows_all.setdefault(r["run"], []).append((it["meta"], r))
    for run, items in sorted(rows_all.items()):
        for m, r in items:
            if r["scope"] != "scored" or r["JC_first_decision_s"] is not None:
                continue
            p = str(m["source"])
            folder = p if os.path.isabs(p) else os.path.join(ROOT, p)
            res = json.load(open(os.path.join(folder, "result.json"), encoding="utf-8"))
            if not done:
                print("episode field", json.dumps(res.get("episode"), default=str)[:700])
                print("settings keys", list(res["settings"].keys())[:40])
                done = True
            ep = res.get("episode") or {}
            pads = np.load(os.path.join(folder, "pads.npz"), allow_pickle=False)
            t = pads["t"]
            i = LEGS.index(r["leg"])
            lo, hi = r["t_on_s"] - 0.1, r["t_on_s"] + (r["samples"] - 1) * 0.1
            w = (t > lo) & (t <= hi + 1e-9)
            dt = np.median(np.diff(t))
            fw = pads["F_cyl"][w, i] / 1e3
            under = float((fw < FMIN).sum() * dt)
            air = float(pads["airborne"][w, i].astype(bool).sum() * dt)
            lift_cond = float((fw + float(np.asarray(json.loads(str(pads["meta_json"])).get("rod_weight_N", [0, 0, 0, 0]))[i] if False else 0) <= 0.5).sum() * dt)
            n = pads["N"][w, i]
            # Later behaviour: same leg, 1 s and whole rest of the run after the episode.
            after = t > hi
            fa = pads["F_cyl"][after, i] / 1e3
            # Other episodes of this leg in the run caught by J_C within 3 s.
            near = [x for _, x in items if x["scope"] == "scored" and x is not r and x["leg"] == r["leg"] and abs(x["t_on_s"] - r["t_on_s"]) < 3.0]
            caught_near = sum(x["JC_first_decision_s"] is not None for x in near)
            others = [x for _, x in items if x["scope"] == "scored" and x is not r]
            ep_npz = np.load(ML / ("ml_dataset" if name != "MLJ" else "ml_dataset_mlj") / f"{run}.npz", allow_pickle=False)
            ep_t = ep_npz["t_s"]
            ep_phase = ep_npz["phase"]
            base = str(m["base_id"])
            bp = ML / "ml_dataset" / f"{base}.npz"
            first_round = None
            if bp.exists():
                b = np.load(bp, allow_pickle=False)
                re_ = np.flatnonzero(b["probe_round_end"])
                first_round = float(b["t_s"][re_[0]]) if re_.size else None
            all_out.append({
                "set": name, "run": run, "leg": r["leg"], "ev_leg": ep.get("leg"), "ev": {k: ep.get(k) for k in ("kind", "leg", "depth_m", "drop_m", "duration_s", "rate") if k in ep},
                "level": m["level"], "Fs_kN": None if not m["seal_friction_N"] else round(m["seal_friction_N"][0] / 1e3, 2), "roll": m["floor_roll_deg"], "pitch": m["floor_pitch_deg"], "grade": m["sensor_grade"], "zc": m["zero_calibration"],
                "t_on": round(r["t_on_s"], 1), "dt_ev": None if r["t_since_event_s"] is None else round(r["t_since_event_s"], 1), "samples": r["samples"], "lift_flag": r["is_lift"],
                "min_window_kN": round(float(fw.min()), 2), "under_ms": round(under * 1e3), "air_ms": round(air * 1e3), "N_le0_ms": round(float((n <= 0).sum() * dt) * 1e3),
                "true_at_sample_kN": round(r["true_at_samples_min_kN"], 2), "est_kN": round(r["est_min_kN"], 2), "est_minus_Fmin": round(r["est_minus_Fmin_min_kN"], 2), "band": round(r["band_on_kN"], 2),
                "phase": r["phase_on"], "base_first_probe_end": first_round, "t_ep_start": round(float(ep_t[0]), 1), "end_phase": str(ep_phase[-1]), "ep_end_t": round(float(ep_t[-1]), 1), "first_ready": None if not (ep_phase == "ready").any() else round(float(ep_t[np.argmax(ep_phase == "ready")]), 1),
                "same_leg_min_after": round(float(fa.min()), 2) if fa.size else None, "near_same_leg": len(near), "near_caught": caught_near, "other_eps": len(others), "other_caught": sum(x["JC_first_decision_s"] is not None for x in others),
                "JC_action": r["JC_action_delay_s"], "JP_miss": r["JP_first_decision_s"] is None})
for o in all_out:
    if o["set"] in ("test", "OOD-1", "OOD-2", "MLJ"):
        print(o)
for o in all_out:
    if o["set"] == "train" and o["samples"] > 1:
        print("TRAIN >=2", o)
print("n", len(all_out), "air_ms>0", sum(o["air_ms"] > 0 for o in all_out), "air_ms max", max(o["air_ms"] for o in all_out), "under_ms max", max(o["under_ms"] for o in all_out))
print("under_ms pct", np.percentile([o["under_ms"] for o in all_out], [50, 90, 100]))
print("end phases", Counter(o["end_phase"] for o in all_out), "first_ready none", sum(o["first_ready"] is None for o in all_out))
print("event leg same", sum(o["ev_leg"] == o["leg"] for o in all_out), "of", len(all_out), Counter(str(o["ev_leg"]) for o in all_out))
print("bands 13.0:", sum(abs(o["band"] - 13.0) < 0.01 for o in all_out), "first probe known", sum(o["base_first_probe_end"] is not None for o in all_out), "t_on after first probe", sum(o["base_first_probe_end"] is not None and o["t_on"] > o["base_first_probe_end"] for o in all_out))
print("grade", Counter((o["set"], o["grade"], o["zc"]) for o in all_out))
json.dump(all_out, open(S + r"\ml_jc_missed_detail.json", "w", encoding="utf-8"), indent=0, default=str)
