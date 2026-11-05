"""Values of the G8C3 batch after the run: the C-S8-76 judge (g8_metrics, g8_rows, same gates on both engines), anchor, hold, guard, re-approach counts, comparison with A3 and the harness expectation.

Writes touch_phase/chrono/g8c3/g8c3_values.json and prints a table. No simulation; checkout code on the path.
Usage: python -I -B -X utf8 extract_g8c.py [batch folder] (default the batch; a scratch folder for the start check)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
WT = HERE.parent / "cad_c4g2" / "wt"
MAIN = Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(WT / "03_src"))
BATCH = MAIN / "07_results/S9/batch_g8c3_20261105"
OUT = MAIN / "06_analysis/02_control/touch_phase/chrono/g8c3"
A3 = MAIN / "07_results/S6/bundleC_g8c76_p28acc_final_G8C3_top_edge_RL_g230_L1R_20261030_233212/G8C3_top_edge_RL_g230"
EXCLUDED_SETTING_KEYS = ("case_id", "notes", "group", "items", "bundle_c", "controller_config", "start_t_s")


def first_difference(a: Path, b: Path, t0_a: float, t0_b: float) -> dict:
    """First sample where s_motor differs (records on the same grid after the run start)."""
    x, y = np.load(a / "record/record.npz"), np.load(b / "record/record.npz")
    n = min(len(x["t"]), len(y["t"]))
    sx, sy = x["s_motor"][:n], y["s_motor"][:n]
    bad = ~np.equal(sx, sy).all(axis=1)
    grid = float(np.max(np.abs((x["t"][:n] - t0_a) - (y["t"][:n] - t0_b))))
    return {"samples": int(n), "time_grid_max_diff_s": grid, "bits_equal": not bool(bad.any()), "first_diff_t_s": None if not bad.any() else float(x["t"][int(np.argmax(bad))] - t0_a),
            "max_abs_diff_mm_before_first": 0.0 if not bad.any() else float(np.max(np.abs(sx[: int(np.argmax(bad))] - sy[: int(np.argmax(bad))]), initial=0.0)) * 1e3, "max_abs_diff_mm_all": float(np.max(np.abs(sx - sy))) * 1e3}


def settings_diff(a: dict, b: dict) -> dict:
    keys = (set(a) | set(b)) - set(EXCLUDED_SETTING_KEYS)
    return {k: [a.get(k), b.get(k)] for k in sorted(keys) if a.get(k) != b.get(k) and not isinstance(a.get(k), dict)}


def pair_view(x: dict, m: dict | None) -> dict:
    m = m or {}
    mc = m.get("min_cyl_after_liftoff") or {}
    fault = m.get("fault") or {}
    return {"row": x.get("row"), "FR_max_mm": x["stroke_max_mm"][1], "b_RL_mm": x["b_RL_mm"], "min_force_kN": mc.get("min_kN"), "min_force_leg": mc.get("leg"), "stopped": bool(fault.get("state_detected")), "stop_events": x["guard"][:2], "final_phase": m.get("final_phase"),
            "t_ready_s": (m.get("times_s") or {}).get("ready"), "settle_roll_pitch_deg": x["settle_roll_pitch_deg"], "true_clearance_end_mm": (m.get("crawler_clearance_end_mm") or {}).get("true_min"), "fs_kN_plant": x.get("fs_kN_plant")}


def engine_pairs(extra: dict, mets: dict) -> dict:
    """R2 vs R2L1 and R3 vs R3L1: FR maximum, b_RL, minimum force, stop, settled attitude (first record sample)."""
    by_row = {x.get("row"): (cid, x) for cid, x in extra.items()}
    out = {}
    for name, a, b in (("off R2-R2L1", "R2", "R2L1"), ("C4G2 R3-R3L1", "R3", "R3L1")):
        missing = [r for r in (a, b) if r not in by_row]
        if missing:
            out[name] = {"missing": missing}
            continue
        va, vb = (pair_view(by_row[r][1], mets.get(by_row[r][0])) for r in (a, b))
        diff = {k: None if va[k] is None or vb[k] is None else va[k] - vb[k] for k in ("FR_max_mm", "b_RL_mm", "min_force_kN", "true_clearance_end_mm")}
        diff["settle_roll_pitch_deg"] = (np.asarray(va["settle_roll_pitch_deg"]) - np.asarray(vb["settle_roll_pitch_deg"])).tolist()
        diff["same_stop_outcome"] = va["stopped"] == vb["stopped"]
        out[name] = {"L2b": va, "L1R": vb, "L2b_minus_L1R": diff}
    return out


def main() -> None:
    from outrigger_sim.params import load_params
    from outrigger_sim.verify import s6_control as sc

    batch = Path(sys.argv[1]) if len(sys.argv) > 1 else BATCH
    params = load_params(level="top")
    mets, extra = {}, {}
    for d in sorted(p for p in batch.iterdir() if (p / "result.json").exists() and not p.name.startswith("_")):
        case = sc.load_case(d)
        res = case["result"]
        cid = res["case"]
        try:
            mets[cid] = sc.g8_metrics(case, params)
        except Exception as exc:  # a start-check run has no lift-off
            mets[cid] = None
            extra.setdefault(cid, {})["metrics_error"] = repr(exc)
        names = [nm for _t, nm in sc._events(case)]
        t0 = float(res["settings"]["start_t_s"])
        side = json.loads((d / "g8c_job_side.json").read_text(encoding="utf-8")) if (d / "g8c_job_side.json").exists() else {}
        anchor = next((n for n in names if n.startswith("INFO_LOC_CLEARANCE_ANCHOR")), None)
        tm = [(float(t) - t0, nm) for t, nm in sc._events(case)]
        x = extra.setdefault(cid, {})
        x.update(row=side.get("row"), engine=side.get("engine"), fs_kN_plant=side.get("fs_kN_plant"), config=side.get("config"), wall_s=res["runner"]["wall_s"], us_per_step=res["runner"]["us_per_step"], placement=res["runner"].get("placement"), floor=res["settings"].get("floor"),
                 grade=res["settings"].get("grade"), seed=res.get("seed"), phases_last=res["phases"][-3:], stroke_max_mm=[v * 1e3 for v in res["stroke"]["max_m"]], anchor=anchor, b_RL_mm=None if anchor is None else float(anchor.split(":")[1].split(",")[2]),
                 settle_roll_pitch_deg=np.degrees(sc.roll_pitch_from_quat(case["rec"]["body_quat_wxyz"][0])).tolist(), hold=[e for e in tm if "TWIST_HOLD" in e[1]], loc=[e for e in tm if e[1] == "crawler_liftoff_confirmed"], guard=[e for e in tm if "STROKE_LIMIT" in e[1] or "FAULT" in e[1]], pauses=[e for e in tm if "LIFT_PAUSED" in e[1]],
                 reapproach=[e for e in tm if "reapproach" in e[1] or "retrigger" in e[1]], block=side.get("block"), g8_block_keys={k: (res.get("g8") or {}).get(k) for k in ("h_m", "g_start_measured_m", "fs_kN_plant")}, flow_limit=(res["settings"].get("s8") or {}).get("flow_limit"),
                 k1_verdict="K1 cannot act: no re-approach start in this run, a both-on run is the same command" if not [e for e in names if e.startswith("leg_reapproach")] else "re-approach present: K1 may act, a both-on row is needed to know")
        if d.name.startswith("G8C3_top_edge_RL_g230") and A3.exists():
            a3res = json.loads((A3 / "result.json").read_text(encoding="utf-8"))
            x["vs_A3"] = {"first_difference": first_difference(d, A3, t0, float(a3res["settings"]["start_t_s"])), "settings_diff": settings_diff(res["settings"], a3res["settings"]), "A3_stroke_max_mm": [v * 1e3 for v in a3res["stroke"]["max_m"]]}
    good = {k: v for k, v in mets.items() if v}
    rows = sc.g8_rows(good) if good else []
    pairs = engine_pairs(extra, mets)
    doc = {"batch": str(batch), "rule": sc.G8_RULE, "failed_rows": [[r["case"], r["item"], r["value"]] for r in rows if r.get("passed") is False], "flags": sorted(r["case"] for r in rows if r.get("flag")), "engine_pairs": pairs, "extra": extra, "metrics": mets, "rows": rows}
    target = (OUT if batch == BATCH else batch)
    target.mkdir(parents=True, exist_ok=True)
    (target / "g8c3_values.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=sc._json_default_ps7), encoding="utf-8")
    for cid, x in extra.items():
        m = mets.get(cid) or {}
        mc = m.get("min_cyl_after_liftoff") or {}
        cc = m.get("crawler_clearance_end_mm") or {}
        print(cid, x.get("engine"), "Fs", x.get("fs_kN_plant"), "final", m.get("final_phase"), "ready", (m.get("times_s") or {}).get("ready"), "stroke_max", np.round(x["stroke_max_mm"], 2).tolist(), "b_RL", x["b_RL_mm"], "minF", mc.get("min_kN"), mc.get("leg"), "clear", cc.get("true_min"),
              "fault", (m.get("fault") or {}).get("state_detected"), "hold", x["hold"][:1], "guard", x["guard"][:2], "reappr", len(x["reapproach"]), "wall", round(x["wall_s"], 1), "us", round(x["us_per_step"], 1), x.get("metrics_error", ""))
        print("  ", x["k1_verdict"], "block", x.get("block"))
        if "vs_A3" in x:
            print("   vs A3", json.dumps(x["vs_A3"], default=str)[:900])
    print("engine pairs (L2b F_s 4 vs L1-R F_s 0; engine, F_s and crawler model change together)")
    for name, p in pairs.items():
        if p.get("missing"):
            print(" ", name, "missing rows", p["missing"])
            continue
        for leg in ("L2b", "L1R", "L2b_minus_L1R"):
            print(" ", name, leg, json.dumps(p[leg], default=str))
    print("failed rows", doc["failed_rows"])
    print("written", target / "g8c3_values.json")


if __name__ == "__main__":
    main()
