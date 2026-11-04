"""Value extraction for the v4 recheck: same rows from the stored Oct 24 batches and the new batch. Reads only result data.

Usage:
  python -I -B -X utf8 extract.py baseline            -> v4_recheck/expected_before_run.json (written before the run)
  python -I -B -X utf8 extract.py new <batch dir>     -> judge + v4_recheck/recheck_values.json, recheck_rows.csv
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import numpy as np

MAIN = Path(r"C:\workspace\outrigger_control")
HERE = Path(__file__).resolve().parent
S8 = MAIN / "07_results" / "S8"
OUT = MAIN / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono/v4_recheck"
sys.path.insert(0, str(MAIN / "03_src"))
REST, P1R = "rest_20261024_233615", "p1r_20261024_222013"
SOURCE = {"N_G4_Fs0_pressure": REST, "N_G4_Fs4_pressure": REST, "N_G4_Fs8_pressure": REST, "N_SS_Fs0_pressure": REST, "N_SS_Fs4_pressure": REST,
          "N_SS_Fs8_pressure": REST, "K0V_top_fdown3.5_Fs0": P1R, "K24_top_fdown3.5_Fs2": REST, "K8_top_fdown3.5_Fs8": P1R, "E_SS_Fs0": P1R,
          "E_SS_Fs8": P1R, "E_RE1bF_Fs0": P1R, "E_RE1bP_Fs0": P1R, "E_RE1bP_Fs8": P1R}
PAPER = {"N_G4_Fs0_pressure": {"F_min_kN": 12.87}, "N_G4_Fs4_pressure": {"F_min_kN": 9.48}, "N_G4_Fs8_pressure": {"F_min_kN": 6.55, "under_F_min_s": 0.60},
         "N_SS_Fs0_pressure": {"F_min_kN": 15.19}, "N_SS_Fs4_pressure": {"F_min_kN": 12.00}, "N_SS_Fs8_pressure": {"F_min_kN": 8.15, "under_F_min_s": 0.30},
         "K0V_top_fdown3.5_Fs0": {"F_min_kN": 19.29}, "K24_top_fdown3.5_Fs2": {"F_min_kN": 25.44}, "K8_top_fdown3.5_Fs8": {"F_min_kN": 38.47},
         "E_SS_Fs0": {"F_min_kN": 29.33}, "E_SS_Fs8": {"F_min_kN": 21.16},
         "E_RE1bF_Fs0": {"lift_s_range": [1.5, 1.8], "window_bar_range": [183.3, 185.5]}, "E_RE1bP_Fs0": {"lift_s_range": [1.5, 1.8], "window_bar_range": [183.3, 185.5]},
         "E_RE1bP_Fs8": {"lift_s_range": [1.5, 1.8], "window_bar_range": [173.0, 178.5]}}
LEGS = ("FL", "FR", "RL", "RR")
ROW_RE = re.compile(r"^(3 F_min|6 min after settlement|.*re-READY|4 max|item 9 (J_P|J_C|M5)|.*REANCHOR min|G4 item 6|run$|2 attitude|C1 D8|3 lift-off)")
F_MIN_KN = 9.41458911


def verify_rows(doc: dict, cid: str) -> dict:
    return {r["item"]: {"value": r.get("value"), "passed": r.get("passed"), "kind": r.get("kind"), "note": (r.get("note") or "")[:200]}
            for r in doc["rows"] if r.get("case") == cid and ROW_RE.match(r["item"])}


def first_diff(a: Path, b: Path) -> dict:
    """First record time at which the new run differs from the stored run (exact compare)."""
    ra, rb = np.load(a / "record/record.npz", allow_pickle=False), np.load(b / "record/record.npz", allow_pickle=False)
    n = min(len(ra["t"]), len(rb["t"]))
    out = {"rows_new": int(len(ra["t"])), "rows_old": int(len(rb["t"]))}
    for key in ("meas.head_pressure", "F_cyl", "s_motor"):
        if key not in ra.files or key not in rb.files:
            out[key] = "missing"
            continue
        same = (ra[key][:n] == rb[key][:n]).reshape(n, -1).all(axis=1)
        out[key] = None if same.all() else float(ra["t"][int(np.argmin(same))])
    return out


def case_values(d: Path, doc: dict | None, cid: str) -> dict:
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    rec = np.load(d / "record/record.npz", allow_pickle=False)
    pads = np.load(d / "pads.npz", allow_pickle=False)
    end = res["s8_end"]
    offset = float(rec["t"][-1]) - float(end["end_t_s"])
    t = pads["t"] - offset
    fi, fs = pads["F_cyl_min_interval"] / 1e3, pads["F_cyl"] / 1e3
    air = pads["airborne"].astype(bool) if "airborne" in pads.files else np.zeros_like(fi, bool)
    te = res.get("event_t_s")
    dt = np.diff(t, prepend=t[0] - 1e-3)
    legs: dict | None = None
    if te is not None:
        post = t >= float(te)
        legs = {leg: {"min_interval_kN": float(fi[post, i].min()), "t_rel_s": float(t[post][np.argmin(fi[post, i])] - float(te)),
                      "min_sample_1ms_kN": float(fs[post, i].min()),
                      "under_F_min_interval_s": float(dt[post][(fi[post, i] < F_MIN_KN) & ~air[post, i]].sum()),
                      "airborne_s": float(dt[post][air[post, i]].sum())} for i, leg in enumerate(LEGS)}
    # whole run after the crawler is off: the judged row uses its own rule; here plain minima after the first READY only
    ready = res.get("ready_t_s")
    run_mins = None
    if ready is not None:
        m = t >= float(ready)
        run_mins = {leg: {"min_interval_kN": float(fi[m, i].min()), "min_sample_1ms_kN": float(fs[m, i].min())} for i, leg in enumerate(LEGS)}
    events = json.loads((d / "controller_events.json").read_text(encoding="utf-8"))
    names = [re.sub(r"^C2Event\(t_s=([0-9.]+), name='(.*)'\)$", lambda g: f"{float(g[1]):.1f} {g[2]}", str(e)) for e in events]
    settings = res["settings"]
    return {"dir": str(d), "contact": settings.get("contact"), "ready_t_s": ready, "event_t_s": te, "first_probe_t_s": res.get("first_probe_t_s"),
            "phase_at_event": (res.get("event_state") or {}).get("phase_at_event"), "s8_end": {k: end.get(k) for k in ("reason", "end_t_s", "final_phase", "timeout")},
            "wall_s": res["runner"].get("wall_s"), "flow_limit": settings.get("flow_limit"), "legs_after_event": legs, "legs_after_first_ready": run_mins,
            "touch_dip_held": [n for n in names if "INFO_TOUCH_DIP_HELD" in n], "reanchor_events": [n for n in names if "reanchor" in n.lower()],
            "warn_fault": [n for n in names if ("WARN" in n or "FAULT" in n)], "events": names,
            "rows": verify_rows(doc, cid) if doc else None, "failed_rows": [r["item"] for r in (doc or {"rows": []})["rows"] if r.get("case") == cid and r.get("passed") is False]}


def baseline() -> None:
    docs = {b: json.loads((S8 / b / "verify_S8C.json").read_text(encoding="utf-8")) for b in (REST, P1R)}
    old = {cid: case_values(S8 / b / cid, docs[b], cid) for cid, b in SOURCE.items()}
    out = {
        "written_before_run": True, "note": "Stored values and expectations; no acceptance rule here, the main session judges.",
        "paper_values": PAPER,
        "paper_item9_misses": {"J_C": "0/19", "J_P": "2/19 (spec line 8425: both F_s 8 pressure-only closed loop: N_G4_Fs8_pressure, N_SS_Fs8_pressure)"},
        "source_note": "Requested N_* source was p1r; the stored N_* folders are in rest_20261024_233615 (p1r has none of the six). K24_top_fdown3.5_Fs2 also rest.",
        "config_compare": "scratchpad cad_v4recheck/config_diff.json: controller_config of the 14 cases, current code vs stored repr: 0 changed and 0 removed old fields, 155 added "
                          "(soil, loc_revoke, diff_sink, lift_stroke_guard, r8.touch_free_air_cap_excess_N, r8.touch_hold_dip_samples, two_pressure.* and others).",
        "pressure_judge_source": {
            "contact_field": "ContactJudge.PRESSURE, c2.py:490, 'Raw pressure reading only'; set by run_S6C.py:1065 from the case contact; stored and current both 'pressure'",
            "lower_estimate": "c2.py:4770 _load_estimate_N returns the raw force under PRESSURE (no seal band)",
            "probe": "c2.py:5162 no probe under PRESSURE; c2.py:8298 REANCHOR after probe only COMBINED; c2.py:8476 geometry judge only COMBINED",
            "P_S8_26": "c2.py:5054 _touchdown_load_N returns the raw force under PRESSURE, so the free-air reference and its cap (P-S8-26, touch_free_air_cap_excess_N) do not act",
            "P_S8_27": "c2.py:5022 _holds_touch_dip has no contact gate; touch_hold_dip_samples = 2 is in the preset, so the dip hold can act under PRESSURE too (touch_seen latches after 1 sample, c2.py:5049)"},
        "expected": {
            "code_paths": "F_s 0 combined and pressure runs may stay bit-equal up to the first TOUCH dip or other new rule; F_s > 0 runs likely diverge at TOUCH (P-S8-26, P-S8-27).",
            "pressure_only": "Same judge meaning. F_s 8 minima near 6.55 / 8.15 kN below F_min 9.415 kN and J_P M1 = 1 expected if the TOUCH end state stays close; the value moves with the twist at READY, size unknown in advance.",
            "reanchor": "REANCHOR mins near 19.29 / 25.44 / 38.47 kN; F_s 2 and 8 may move with TOUCH change.",
            "ss": "Above F_min, near 29.33 / 21.16 kN.",
            "re1b": "Event-leg lift about 1.3 to 1.8 s (final E_RE1bF_Fs8 was 1.31 s vs 1.6 s stored); window pressure near the stored 173 to 186 bar.",
            "cost_wall_s": "stored walls on a full pool 332 to 626 s; total serial 6510 s, about 27 min on 4 slots plus event spread."},
        "stored_batch_values": old}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "expected_before_run.json").write_text(json.dumps(out, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    for cid, v in old.items():
        r = v["rows"]
        print(cid, "F3", r.get("3 F_min (1 ms)", {}).get("value"), "M5", r.get("item 9 M5 closed loop: min true / under F_min [s] / lifted [s]", {}).get("value"),
              "JP", r.get("item 9 J_P M1 missed / M1' late / M3 median / M2 / M4 max (record)", {}).get("value"), "dip", v["touch_dip_held"], "phase", v["phase_at_event"], "failed", v["failed_rows"])


def new(batch: Path) -> None:
    from outrigger_sim.verify.s8_control import judge_batch

    vfile = OUT / f"verify_{batch.name}.json"
    judge_batch(batch, vfile, root=MAIN, ref_batch=None, lookup_batches=[], deferred_ref=None)
    doc = json.loads(vfile.read_text(encoding="utf-8"))
    rows = {}
    for cid, b in SOURCE.items():
        d = batch / cid
        if not (d / "result.json").exists():
            rows[cid] = {"missing": True}
            continue
        v = case_values(d, doc, cid)
        v["first_diff_vs_stored_t_s"] = first_diff(d, S8 / b / cid)
        rows[cid] = v
    out = {"batch": str(batch), "verify": str(vfile), "meta": {k: doc["meta"].get(k) for k in ("rows", "failed", "hold", "judge_revision")},
           "code_state": json.loads((batch / "code_state.json").read_text(encoding="utf-8")), "cases": rows}
    (OUT / "recheck_values.json").write_text(json.dumps(out, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    with (OUT / "recheck_rows.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case", "row_3_F_min_kN", "under_F_min_s_M5", "lifted_s_M5", "J_C_M1", "J_C_M1p", "J_P_M1", "J_P_M1p", "reready_s", "window_bar", "outside_bar", "first_diff_F_cyl_t_s", "dip_held", "failed_rows"])
        for cid, v in rows.items():
            if v.get("missing"):
                w.writerow([cid, "missing"])
                continue
            r = v["rows"]
            g = lambda k: r.get(k, {}).get("value")
            m5 = g("item 9 M5 closed loop: min true / under F_min [s] / lifted [s]") or [None] * 3
            jc = g("item 9 J_C M1 missed / M1' late / M3 median / M2 / M4 max (record)") or [None] * 5
            jp = g("item 9 J_P M1 missed / M1' late / M3 median / M2 / M4 max (record)") or [None] * 5
            rr = next((x["value"] for k, x in r.items() if "re-READY" in k and "<=" in k), None)
            w.writerow([cid, g("3 F_min (1 ms)"), m5[1], m5[2], jc[0], jc[1], jp[0], jp[1], rr, g("4 max pressure in the event transient"), g("4 max moving pressure outside the event transient"),
                        v["first_diff_vs_stored_t_s"].get("F_cyl"), ";".join(v["touch_dip_held"]), ";".join(v["failed_rows"])])
    print("meta", out["meta"])
    print("written", OUT / "recheck_values.json")


if __name__ == "__main__":
    if sys.argv[1] == "baseline":
        baseline()
    else:
        new(Path(sys.argv[2]))
