"""V-5 (3') judgement of C-S8-67 (spec rev. 62 317.1, U-S8-67 (b)): RR rod fault + G4 on RR.

Two independent paths:

* controller path: the run's own ``controller_events.json`` (R-5 ``relevel_predicted``,
  ``INFO_R5_FALLBACK_SLOPE``, warnings, FAULT) and the official S8 judge
  (``outrigger_sim.verify.s8_control.judge_batch``) for the companion judged rows (READY, FAULT 0,
  1 ms true force >= F_min, end attitude);
* replay path: ``outrigger_sim.control.r5_fallback_replay.replay_case`` without any workaround
  (python D-1..D-4 fixed), same-run gate, optimism of the RR fallback rows and the in-run
  healthy-sensor counterfactual (first row where the true-force prediction would fire).

Pass criteria (317.1): 1. RR ``relevel_predicted`` <= the pair's healthy-sensor time (relative to
t_G4 when READY differs) and no false RR R-5 between the fault and t_G4 (true force >= 3 P5);
2. ``INFO_R5_FALLBACK_SLOPE:RR`` >= 1; 3. same-run gate passed, RR ``judged_falling`` optimism
<= 1.2 kN (L2b), no missed trigger on 302.2 rows (level-row misses are a FLAG); 4. record: other
legs' minimum 1 ms true force after the fault vs F_min + 5 kN and the pair's FL / FR / RL.

Times are controller times (pads / record / r8 ``t``); ``result.json`` ``phases`` and
``ready_t_s`` are run-relative (offset = ``rod_fault.t_start_s - rod_fault_t_s``).

Usage (dynamics-dev):
    python -I 04_scripts/03_control/s8/v5_c67_judge.py --batch 07_results/S8/v5_c67_<stamp>
        --pair Fs0=07_results/S8/v4_c29_Fs0_<stamp>/MLJ_K0V_fdown3.5_G4RF_Fs0
        --pair Fs8=07_results/S8/v4_c29_Fs8_<stamp>/MLJ_K0V_fdown3.5_G4RF_Fs8
        --out 06_analysis/02_control/s9/v5
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "03_src"))

from outrigger_sim.contact_episode import read_controller_events  # noqa: E402
from outrigger_sim.control.c2 import C2Config, C2Geometry  # noqa: E402
from outrigger_sim.control.r5_fallback_replay import replay_case  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.verify import s8_control  # noqa: E402

LEGS = ("FL", "FR", "RL", "RR")
EVENT_LEG = "RR"
G4_AFTER_READY_S = 5.0  # run_S8C.py G4 "at": "ready+5"
ALLOWANCE_L2B_N = 1200.0  # 303 V-2, L2b
F_MARGIN_N = 5000.0  # 317.1 criterion 4 (record)
P5_MARGIN_N = 7500.0  # 316 P5 = F_min + 7.5 kN
R5_HORIZON_S = 0.4  # R-5 prediction horizon: 4 periods x 0.1 s (R8 C2)
GUARD_CAP_M_S = 2.5e-3
BAR = 1e5


def _jsonable(x: Any) -> Any:
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return _jsonable(x.tolist())
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


def controller_path(case: Path) -> dict[str, Any]:
    """Events and run timing from the controller record."""
    r = json.loads((case / "result.json").read_text(encoding="utf-8"))
    fault = r.get("rod_fault") or {}
    offset = float(fault["t_start_s"]) - float(r["rod_fault_t_s"])
    phases = [(round(float(t) + offset, 3), p) for t, p in r["phases"]]
    readies = [t for t, p in phases if p == "ready"]
    t_g4 = round(float(r["ready_t_s"]) + offset + G4_AFTER_READY_S, 3)
    events = read_controller_events(case / "controller_events.json")

    def named(prefix: str) -> list[tuple[float, str]]:
        return [(round(t, 3), n) for t, n in events if n.startswith(prefix)]

    relevel = [(t, n.split(":", 1)[1]) for t, n in named("relevel_predicted")]
    info = named("INFO_R5_FALLBACK_SLOPE")
    return {
        "case": str(case),
        "time_offset_s(ctrl-run)": offset,
        "fault": {"leg": fault.get("leg"), "kind": fault.get("fault"),
                  "t_ctrl_s": round(float(fault["t_start_s"]), 3),
                  "applied_periods": fault.get("applied_periods"),
                  "periods_without_rod_reading": fault.get("periods_without_rod_reading")},
        "t_G4_ctrl_s": t_g4,
        "phases_ctrl_s": phases,
        "ready_ctrl_s": readies,
        "relevel_predicted": relevel,
        "relevel_predicted_rel_G4_s": [(round(t - t_g4, 3), leg) for t, leg in relevel],
        "probe_aborted_low_load": named("probe_aborted_low_load"),
        "info_r5_fallback_slope": info,
        "info_r5_fallback_slope_count_by_leg": {
            leg: sum(1 for _, n in info if n.split(":")[1] == leg) for leg in LEGS},
        "warn_rod_pressure_fallback": named("WARN_ROD_PRESSURE_FALLBACK"),
        "info_rod_fault_reason": named("INFO_ROD_PRESSURE_FAULT_REASON"),
        "fault_events": [(round(t, 3), n) for t, n in events if "FAULT" in n.upper()
                         and not n.startswith(("INFO_ROD_PRESSURE_FAULT_REASON",))],
        "warn_events": named("WARN_"),
        "reapproach": named("leg_reapproach"),
        "all_event_count": len(events),
        "s8_end": r.get("s8_end"),
        "_result": r,
    }


def force_rows(case: Path, cp: dict[str, Any], params) -> dict[str, Any]:
    """1 ms true-force minima (``F_pressure_min_interval``), fault-leg lock windows, guard."""
    r = cp["_result"]
    f_min = float(params.control.F_min_cylinder_N)
    p5 = f_min + P5_MARGIN_N
    with np.load(case / "pads.npz", allow_pickle=False) as p:
        t = np.asarray(p["t"], dtype=float)
        fpm = np.asarray(p["F_pressure_min_interval"], dtype=float)
        fp = np.asarray(p["F_pressure"], dtype=float)
        head = np.asarray(p["head_pressure"], dtype=float)
    with np.load(case / "r8_series.npz", allow_pickle=False) as s:
        tr = np.asarray(s["t"], dtype=float)
        cmp_guard = np.asarray(s["cmp_guard_u"], dtype=float)
        issued = np.asarray(s["issued_u"], dtype=float)
    t_f = cp["fault"]["t_ctrl_s"]
    t_g4 = cp["t_G4_ctrl_s"]
    after = t >= t_f - 1e-9

    def minimum(mask: np.ndarray, legs: list[int], arr: np.ndarray = fpm) -> dict[str, Any]:
        sub = arr[mask][:, legs]
        k = np.unravel_index(np.argmin(sub), sub.shape)
        return {"min_kN": round(float(sub[k]) / 1e3, 3), "leg": LEGS[legs[k[1]]],
                "t_ctrl_s": round(float(t[mask][k[0]]), 3)}

    per_leg_after = {LEGS[j]: minimum(after, [j]) for j in range(4)}
    fault_to_g4 = (t >= t_f - 1e-9) & (t < t_g4)
    per_leg_f2g4 = {LEGS[j]: minimum(fault_to_g4, [j]) for j in range(4)}
    first_ready = cp["ready_ctrl_s"][0]
    lifted = t >= first_ready - 1e-9
    per_leg_from_ready = {LEGS[j]: minimum(lifted, [j]) for j in range(4)}

    leg = LEGS.index(cp["fault"]["leg"])
    others = [j for j in range(4) if j != leg]
    # false R-5 on the fault leg between fault and t_G4: R-5 times with true force >= 3 P5
    false_r5 = []
    for tr5, lg in cp["relevel_predicted"]:
        if lg == LEGS[leg] and t_f - 1e-9 <= tr5 < t_g4:
            i = int(np.argmin(np.abs(t - tr5)))
            false_r5.append({"t_ctrl_s": tr5, "true_force_kN": round(float(fp[i, leg]) / 1e3, 3),
                             "is_false(>=3P5)": bool(fp[i, leg] >= 3 * p5)})
    true_at_relevel = []
    for tr5, lg in cp["relevel_predicted"]:
        i = int(np.argmin(np.abs(t - tr5)))
        j = LEGS.index(lg)
        # R-5 predicts the level HORIZON periods ahead (4 x 0.1 s): truth there, and the
        # minimum of the fall that follows (2 s window)
        i_h = int(np.argmin(np.abs(t - (tr5 + R5_HORIZON_S))))
        win = (t >= tr5 - 1e-9) & (t <= tr5 + 2.0)
        k = int(np.argmin(fpm[win, j]))
        true_at_relevel.append({
            "t_ctrl_s": tr5, "leg": lg,
            "F_pressure_kN": round(float(fp[i, j]) / 1e3, 3),
            "F_pressure_min_interval_kN": round(float(fpm[i, j]) / 1e3, 3),
            "F_pressure_at_t_plus_horizon_kN": round(float(fp[i_h, j]) / 1e3, 3),
            "min_next_2s_kN": round(float(fpm[win, j][k]) / 1e3, 3),
            "min_next_2s_t_ctrl_s": round(float(t[win][k]), 3),
            "class_at_fire": ("false(>=3P5)" if fp[i, j] >= 3 * p5 else
                              "true_low(<P5+5kN)" if fp[i, j] < p5 + F_MARGIN_N else "between"),
        })

    # fault-leg lock windows (218.10 formula, as 316.3)
    tp = r["controller_meta"]["two_pressure"]
    st = tp["settings"]
    a_p = np.atleast_1d(np.asarray(tp["head_area_m2"], dtype=float))
    a_ann = np.atleast_1d(np.asarray(tp["annulus_area_m2"], dtype=float))
    a_p = float(a_p[leg] if a_p.size == 4 else a_p[0])
    a_ann = float(a_ann[leg] if a_ann.size == 4 else a_ann[0])
    b_fb = float(st["fallback_min_band_N"])
    locks = [e for e in (tp.get("fallback_lock_log") or []) + (tp.get("fallback_lock_current") or [])
             if e["leg"] == LEGS[leg] and e["t_start_s"] >= t_f - 1e-9]
    lock_rows = []
    for e in locks:
        r_ub, h_a, m = float(e["ratio_bound"]), float(e["anchor_head_Pa"]), float(e["start_Pa"])
        h_star = (f_min + F_MARGIN_N + b_fb + m * a_ann + r_ub * h_a * a_ann) / (a_p + r_ub * a_ann)
        i = int(np.argmin(np.abs(t - e["t_start_s"])))
        lock_rows.append({"t_start_s": round(e["t_start_s"], 3), "R_ub": round(r_ub, 3),
                          "M_bar": round(m / BAR, 2), "h_a_bar": round(h_a / BAR, 2),
                          "h_star_bar": round(h_star / BAR, 2),
                          "head_true_at_lock_bar": round(float(head[i, leg]) / BAR, 2)})
    r8_after = tr >= t_f - 1e-9
    guard_sat = (np.abs(cmp_guard[r8_after]) >= 0.95 * GUARD_CAP_M_S).sum(axis=0) * 0.1
    issued_sat = float((np.abs(issued[r8_after, leg]) >= 0.95 * GUARD_CAP_M_S).sum()) * 0.1
    return {
        "F_min_N": f_min, "P5_N": p5, "F_min_plus_5kN_N": f_min + F_MARGIN_N,
        "F_pressure_min_interval_after_fault": per_leg_after,
        "others_min_after_fault": minimum(after, others),
        "fault_leg_min_after_fault": per_leg_after[LEGS[leg]],
        "F_pressure_min_interval_fault_to_G4": per_leg_f2g4,
        "F_pressure_min_interval_from_first_ready": per_leg_from_ready,
        "all_legs_min_from_first_ready": minimum(lifted, [0, 1, 2, 3]),
        "fault_leg_false_r5_fault_to_G4": false_r5,
        "true_force_at_relevel": true_at_relevel,
        "fault_leg_head_true_max_after_fault_bar": round(float(head[after, leg].max()) / BAR, 2),
        "fault_leg_lock_windows": lock_rows,
        "guard_saturation_s_per_leg(cmp_guard_u)": dict(zip(LEGS, guard_sat.round(2).tolist())),
        "judge_guard_cap_s(issued_u fault leg)": round(issued_sat, 2),
    }


def replay_path(case: Path, geometry: C2Geometry) -> dict[str, Any]:
    """Unmodified ``replay_case`` (run's controller setting: R8-D1 preset, column_nominal)."""
    config = C2Config().with_10hz_d1()
    rep = replay_case(case, geometry, config, sources=("plant_meta", "column_nominal"))
    out = {k: rep[k] for k in ("engine", "replayable", "reasons", "notes",
                               "probed_leg_source_counts", "command_history_match", "gate",
                               "level_gate", "same_run_gate", "true_force_source")}
    out["variants"] = {}
    for src, v in rep["variants"].items():
        rows = v.get("optimism_rows") or []
        leg_rows = [rw for rw in rows if rw["leg"] == EVENT_LEG]
        judged = [rw for rw in leg_rows if rw.get("row_class") == "judged_falling"]
        fb_fire = [rw["t_s"] for rw in leg_rows if rw["fallback_fires"] and rw["is_watched"]]
        hl_fire = [rw["t_s"] for rw in leg_rows if rw["healthy_fires"] and rw["is_watched"]]
        out["variants"][src] = {
            "r5_events": v["r5_events"],
            "fallback_slope_events": v["fallback_slope_events"],
            "row_classes": v.get("row_classes"),
            "allowance_N": v.get("allowance_N"),
            "judged_falling_within_allowance": v.get("judged_falling_within_allowance"),
            "slope_rows_missed_triggers": v.get("slope_rows_missed_triggers"),
            "judgement_passed": v.get("judgement_passed"),
            "level_missed_triggers": v.get("level_missed_triggers"),
            "level_missed_trigger_flag": v.get("level_missed_trigger_flag"),
            "worst_judged_falling_row": max(judged, key=lambda rw: rw["difference_N"],
                                            default=None),
            "missed_rows": [rw for rw in leg_rows if rw["is_missed"]],
            "first_fallback_fire_watched_s": min(fb_fire, default=None),
            "first_healthy_fire_watched_s": min(hl_fire, default=None),
            "watched_fire_rows": [(round(rw["t_s"], 3), rw["phase"], rw["row_class"],
                                   rw["fallback_fires"], rw["healthy_fires"],
                                   round(rw["L_hat_fb_N"] / 1e3, 3),
                                   round(rw["L_hat_true_N"] / 1e3, 3))
                                  for rw in leg_rows if rw["is_watched"]
                                  and (rw["fallback_fires"] or rw["healthy_fires"])],
        }
    return out


def judge_rows(batch: Path, out_path: Path, case_ids: list[str]) -> dict[str, Any]:
    """Official S8 judge on a batch; rows of the given cases (all, failed, companion rows)."""
    path = s8_control.judge_batch(batch, out_path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    res = {"file": str(path), "batch_failed": doc["meta"]["failed"],
           "batch_rows": doc["meta"]["rows"], "summary": doc["meta"].get("summary")}
    for cid in case_ids:
        rows = [rw for rw in doc["rows"] if rw.get("case") in (cid, "*")]
        res[cid] = {
            "rows": len(rows),
            "failed": [{k: rw.get(k) for k in ("item", "value", "limit", "note")}
                       for rw in rows if rw.get("passed") is False],
            "judged_rows": [{k: rw.get(k) for k in ("item", "value", "limit", "passed", "kind")}
                            for rw in rows if rw.get("kind", "judged") == "judged"],
        }
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True)
    ap.add_argument("--pair", action="append", default=[], help="Fs0=<case dir>")
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip-judge", action="store_true")
    args = ap.parse_args()
    batch = (ROOT / args.batch) if not Path(args.batch).is_absolute() else Path(args.batch)
    out_dir = (ROOT / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    params = load_params()
    geometry = C2Geometry.from_params(params)
    pairs = {}
    for spec in args.pair:
        tag, _, p = spec.partition("=")
        pairs[tag] = (ROOT / p) if not Path(p).is_absolute() else Path(p)

    doc: dict[str, Any] = {"spec": "s6_control_spec rev. 63 (317.1 criteria, U-S8-67 (b))",
                           "batch": str(batch), "cases": {}, "pairs": {}}
    case_dirs = sorted(d for d in batch.iterdir() if (d / "result.json").exists())
    for d in case_dirs:
        tag = d.name.rsplit("_", 1)[1]  # Fs0 / Fs8
        cp = controller_path(d)
        fr = force_rows(d, cp, params)
        print(f"== {d.name}: replay ...", flush=True)
        rp = replay_path(d, geometry)
        cp.pop("_result")
        doc["cases"][tag] = {"case_id": d.name, "controller": cp, "forces": fr, "replay": rp}
        if tag in pairs:
            pc = controller_path(pairs[tag])
            pf = force_rows(pairs[tag], pc, params)
            pc.pop("_result")
            doc["pairs"][tag] = {"case_id": pairs[tag].name, "controller": pc, "forces": pf}

    if not args.skip_judge:
        doc["judge"] = {"c67": judge_rows(batch, out_dir / "verify_S8C_c67.json",
                                          [d.name for d in case_dirs])}

    # --- verdict -------------------------------------------------------------------------
    verdict = {}
    for tag, c in doc["cases"].items():
        cp, fr, rp = c["controller"], c["forces"], c["replay"]
        pair = doc["pairs"].get(tag)
        rr = [t for t, lg in cp["relevel_predicted"] if lg == EVENT_LEG and t >= cp["t_G4_ctrl_s"]]
        pair_rr = [t for t, lg in pair["controller"]["relevel_predicted"]
                   if lg == EVENT_LEG] if pair else []
        t_rr = min(rr, default=None)
        t_pair = min(pair_rr, default=None)
        rel = None if t_rr is None else round(t_rr - cp["t_G4_ctrl_s"], 3)
        rel_pair = None if t_pair is None else round(t_pair - pair["controller"]["t_G4_ctrl_s"], 3)
        same_ready = pair is not None and abs(cp["ready_ctrl_s"][0]
                                              - pair["controller"]["ready_ctrl_s"][0]) < 1e-6
        n_false = sum(1 for e in fr["fault_leg_false_r5_fault_to_G4"] if e["is_false(>=3P5)"])
        n_r5_f2g4 = len(fr["fault_leg_false_r5_fault_to_G4"])
        c1 = (t_rr is not None and t_pair is not None
              and (t_rr <= t_pair + 1e-6 if same_ready else rel <= rel_pair + 1e-6)
              and n_r5_f2g4 == 0)
        n_info = cp["info_r5_fallback_slope_count_by_leg"][EVENT_LEG]
        c2 = n_info >= 1
        own = (rp["same_run_gate"] or {}).get("source", "column_nominal")
        var = rp["variants"][own]
        worst = var["worst_judged_falling_row"]
        worst_N = None if worst is None else worst["difference_N"]
        c3 = bool(rp["gate"]["passed"] and rp["same_run_gate"] and rp["same_run_gate"]["passed"]
                  and worst_N is not None and worst_N <= ALLOWANCE_L2B_N
                  and var["slope_rows_missed_triggers"] == 0)
        others = fr["others_min_after_fault"]
        pair_others = None
        if pair:
            pf = pair["forces"]["F_pressure_min_interval_after_fault"]
            k = min(("FL", "FR", "RL"), key=lambda lg: pf[lg]["min_kN"])
            pair_others = {"leg": k, **pf[k]}
        verdict[tag] = {
            "1_rr_relevel_ctrl_s": t_rr, "1_rr_relevel_rel_G4_s": rel,
            "1_pair_healthy_ctrl_s": t_pair, "1_pair_rel_G4_s": rel_pair,
            "1_same_ready": same_ready, "1_rr_r5_fault_to_G4": n_r5_f2g4,
            "1_false_r5(>=3P5)": n_false, "1_passed": c1,
            "2_info_rr_count": n_info, "2_passed": c2,
            "3_gate": rp["gate"], "3_same_run_gate_passed": (rp["same_run_gate"] or {}).get("passed"),
            "3_worst_judged_falling_kN": None if worst_N is None else round(worst_N / 1e3, 3),
            "3_judged_falling_rows": (var["row_classes"] or {}).get("judged_falling", {}).get("rows"),
            "3_slope_missed": var["slope_rows_missed_triggers"],
            "3_level_missed_flag": var["level_missed_trigger_flag"],
            "3_judgement_passed_tool": var["judgement_passed"], "3_passed": c3,
            "4_others_min_after_fault": others, "4_pair_others_min_after_fault": pair_others,
            "4_limit_kN(record)": round((fr["F_min_plus_5kN_N"]) / 1e3, 3),
            "4_meets_record_limit": others["min_kN"] * 1e3 >= fr["F_min_plus_5kN_N"],
            "two_path_r5_equal": rp["same_run_gate"]["r5_equal"] if rp["same_run_gate"] else None,
            "two_path_info_equal": (rp["same_run_gate"] or {}).get("fallback_slope_equal"),
            "replay_first_fallback_fire_s": var["first_fallback_fire_watched_s"],
            "replay_first_healthy_fire_s": var["first_healthy_fire_watched_s"],
        }
        print(f"== {tag}: {json.dumps(_jsonable(verdict[tag]))}")
    doc["verdict"] = verdict
    out = out_dir / "v5_c67_judgement.json"
    out.write_text(json.dumps(_jsonable(doc), indent=1, default=str, ensure_ascii=False),
                   encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
