"""Judge the acceptance bundles against acceptance/criteria.md and write acceptance/judgement.json.

Usage: python -I -B acc_judge.py [--acc <acceptance folder>] [--self-test]
--self-test reads the stored final-controller files as if they were the new runs (every pair must be identical).
A bundle whose files are missing is reported as ``missing``; nothing is decided for it.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from scipy.optimize import brentq
from scipy.stats import beta, binom

MAIN = Path(r"C:\workspace\outrigger_control")
ACC = MAIN / "06_analysis/02_control/touch_phase/acceptance"
REV85 = MAIN / "06_analysis/02_control/s9/rev85"
REV79 = MAIN / "06_analysis/02_control/s8/rev79"
WT = Path(__file__).resolve().parent.parent / "cad_c4g2" / "wt"
GUARD_KN = 14.41
ACCEPT = 0.03
S1_FRONT = ("S1@FL", "S1@FR")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def stored_runs(path: Path) -> list[dict]:
    return (load(path) or {}).get("runs", [])


def cp_upper(k: int, n: int) -> tuple[float, float]:
    if k >= n:
        return 1.0, 1.0
    return float(beta.ppf(0.95, k + 1, n - k)), float(brentq(lambda p: binom.cdf(k, n, p) - 0.05, 1e-15, 1 - 1e-15, xtol=1e-15))


def event_runs(doc) -> dict:
    """{(key, timing, event, offset): run} of an r67 / study A file."""
    out = {}
    for res in doc["results"]:
        if "error" in res:
            out[(res["key"], "error")] = res
            continue
        for index, run in enumerate(res["runs"]):
            out[(res["key"], res.get("timing", run.get("timing")), run.get("event"), run.get("offset_s"), index)] = run
    return out


def compare_event(new, base, name: str, keep=lambda key: True) -> dict:
    a, b = event_runs(new), event_runs(base)
    keys = [k for k in a if keep(k)]
    errors = [k[0] for k in keys if len(k) == 2]
    p2f, f2p, unmatched, same_hash, failed = [], [], [], 0, []
    for k in keys:
        if len(k) == 2:
            continue
        run = a[k]
        if not run.get("pass"):
            failed.append(str(k[:4]))
        old = b.get(k)
        if old is None:
            unmatched.append(str(k[:4]))
            continue
        same_hash += run.get("commands_sha256") == old.get("commands_sha256") and run.get("commands_sha256") is not None
        if old.get("pass") and not run.get("pass"):
            p2f.append(str(k[:4]))
        elif run.get("pass") and not old.get("pass"):
            f2p.append(str(k[:4]))
    faults = sum(bool(a[k].get("fault_periods")) for k in keys if len(k) != 2)
    return {"name": name, "n": len(keys), "failed": len(failed), "failed_rows": failed[:60], "pass_to_fail": p2f, "fail_to_pass": f2p, "unmatched": unmatched,
            "errors": errors, "fault_runs": faults, "same_hash": int(same_hash)}


def flat_verdicts(doc) -> dict:
    """{id: verdict-like} of the wrapper, H8 and x426 formats."""
    out = {}
    for rec in doc.get("records", []) or doc.get("cases", []):
        out[rec.get("id", rec.get("case_id"))] = rec.get("verdict", rec.get("pass"))
    for res in doc.get("results", []):
        key = res.get("key", res.get("id", res.get("case_id")))
        if isinstance(res.get("base"), dict) and "pass" in res["base"]:
            out[key] = res["base"]["pass"]
        elif "verdict" in res:
            out[key] = res["verdict"]
        elif "pass" in res:
            out[key] = res["pass"]
    return out


def is_good(value) -> bool:
    return value in (True, "pass", "stroke_limited_pass")


def compare_flat(new, base, name: str) -> dict:
    a, b = flat_verdicts(new), flat_verdicts(base)
    p2f, unmatched = [], []
    for key, value in a.items():
        if key not in b:
            unmatched.append(key)
        elif is_good(b[key]) and not is_good(value):
            p2f.append(key)
    return {"name": name, "n": len(a), "pass_to_fail": p2f, "unmatched": unmatched}


def r79_judge(run_files: list[Path], out: Path) -> dict | None:
    if not all(p.exists() for p in run_files):
        return None
    script = WT / "04_scripts/03_control/s8/r79_sensor_judge.py"
    done = subprocess.run([sys.executable, "-I", "-B", str(script), "judge", str(out), *map(str, run_files)], capture_output=True, text=True, timeout=1800)
    if done.returncode:
        return {"error": done.stderr[-800:]}
    return load(out)


def noise_verdict(report: dict, stored: dict, level: str = "L2") -> dict:
    rows = [r for r in report["runs"] if r["level"] == level and not any(m in r["inner"] for m in S1_FRONT)]
    k, n = sum(not r["pass"] for r in rows), len(rows)
    u1, u2 = cp_upper(k, n) if n else (None, None)
    old = {r["key"]: r for r in stored["runs"]} if stored else {}
    p2f = [r["key"] for r in rows if r["key"] in old and old[r["key"]]["pass"] and not r["pass"]]
    f2p = [r["key"] for r in rows if r["key"] in old and not old[r["key"]]["pass"] and r["pass"]]
    return {"level": level, "failures": k, "runs": n, "rate": k / n if n else None, "cp95_upper_beta": u1, "cp95_upper_binom_root": u2, "accept": bool(n and u1 <= ACCEPT),
            "unmatched": len(report["unmatched"]), "errors": len(report["errors"]), "pass_to_fail": p2f, "fail_to_pass": f2p}


def judge_d8(doc, off) -> dict:
    runs = doc["runs"]
    bad = {"error": [r["id"] for r in runs if "error" in r]}
    ok = [r for r in runs if "error" not in r]
    bad["fails"] = [r["id"] for r in ok if r.get("fails")]
    bad["fault"] = [r["id"] for r in ok if r.get("fault")]
    bad["below_guard"] = [r["id"] for r in ok if r["min_true_cyl_force_kN"] < GUARD_KN]
    bad["attitude"] = [r["id"] for r in ok if r["ss_true_att_deg_maxabs"] > 0.2]
    bad["ready"] = [r["id"] for r in ok if not r.get("t_ready_s") or r["t_ready_s"] > 100.0]
    out = {"n": len(runs), "min_true_kN": min(r["min_true_cyl_force_kN"] for r in ok), "ready_max_s": max((r["t_ready_s"] or 1e9) for r in ok),
           "att_max_deg": max(r["ss_true_att_deg_maxabs"] for r in ok), "pmax_bar": max(r["max_pressure_bar"] for r in ok),
           "hold_runs": sum(bool(r["hold_events"]) for r in ok), "retrigger_runs": sum(r["retrigger_deferred"] > 0 for r in ok),
           "bad": {k: v[:40] for k, v in bad.items()}, "bad_counts": {k: len(v) for k, v in bad.items()}, "accept": not any(bad.values()) and len(runs) == 576}
    if off:
        base = {r["id"]: r for r in off["runs"] if "error" not in r}
        pairs = [(r, base[r["id"]]) for r in ok if r["id"] in base]
        if pairs:
            out["vs_off_main"] = {"n": len(pairs), "ready_mean_delta_s": sum((a["t_ready_s"] or 0) - (b["t_ready_s"] or 0) for a, b in pairs) / len(pairs),
                                  "min_true_delta_kN_worst": min(a["min_true_cyl_force_kN"] - b["min_true_cyl_force_kN"] for a, b in pairs),
                                  "min_true_off_kN": min(b["min_true_cyl_force_kN"] for _, b in pairs)}
    return out


def judge_crawler(doc) -> dict:
    rows = []
    for r in doc["runs"]:
        if "error" in r:
            rows.append({"id": r["id"], "ok": False, "why": "error"})
            continue
        forces = r["values"]["forces"]["after_liftoff"]["min_kN"]
        ready = r["values"]["times"].get("t_first_ready_s")
        fault = str(r["final_phase"]).lower().endswith("fault") or any(e[1].startswith("FAULT") for e in r["events"])
        rows.append({"id": r["id"], "ok": bool(ready) and not fault and forces >= GUARD_KN, "F_min_kN": forces, "ready_s": ready, "fault": fault, "harness_class": r["harness_class"], "failed_rows": r["failed_rows"]})
    return {"n": len(rows), "failed": [x for x in rows if not x["ok"]], "F_min_kN": min((x["F_min_kN"] for x in rows if "F_min_kN" in x), default=None), "accept": len(rows) == 72 and all(x["ok"] for x in rows), "rows": rows}


def soil_pick(new, base) -> list[dict]:
    a, b = event_runs(new), event_runs(base)
    candidates = []
    for k, run in a.items():
        if len(k) == 2 or not k[0].endswith("|two") or k[0].split("|")[1] not in ("G1", "J2"):
            continue
        if run.get("event") not in ("RE1bF", "FS24") or run.get("timing", "level") != "level":
            continue
        starts = run.get("reapproach_starts")
        count = starts if isinstance(starts, int) else len(starts or [])
        old = b.get(k) or {}
        if count < 2 or run.get("commands_sha256") == old.get("commands_sha256"):
            continue
        adj = run.get("adj_min_F_in_W_kN") or {}
        lifts = run.get("lifts") or {}
        parts = k[0].split("|")
        candidates.append({"key": k[0], "event": run["event"], "soil": parts[1], "leg": parts[2], "fs": parts[3], "adj_min_kN": min(adj.values()) if adj else None,
                           "lift_sum_s": sum(v.get("sum_s", 0) for v in lifts.values()), "starts": count})
    candidates.sort(key=lambda c: (c["adj_min_kN"] if c["adj_min_kN"] is not None else 1e9, -c["lift_sum_s"], c["key"], c["event"]))
    picks = candidates[:1]
    if picks:
        other = [c for c in candidates if c["soil"] != picks[0]["soil"]]
        picks += other[:1]
    if len(picks) == 2:
        third = [c for c in candidates if c not in picks and (c["fs"] not in {p["fs"] for p in picks} or c["leg"] not in {p["leg"] for p in picks})]
        picks += third[:1]
    return picks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--acc", type=Path, default=ACC)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    acc = args.acc
    self_test = args.self_test
    out: dict = {"criteria": "acceptance/criteria.md", "self_test": self_test}
    # grid
    grid = []
    mapping = [("grid_r67_main", REV85 / "finB2_r67_main.json"), ("grid_r67_top", REV85 / "finB2_r67_top.json"),
               ("grid_r69_top", acc / "grid/grid_r69_top_off.json"), ("grid_r69_bottom", acc / "grid/grid_r69_bottom_off.json")]
    for name, base_path in mapping:
        new_path = base_path if self_test else acc / "grid" / f"{name}.json"
        new, base = load(new_path), load(base_path)
        grid.append(compare_event(new, base, name) if new and base else {"name": name, "missing": True})
    out["grid"] = {"parts": grid, "n": sum(g.get("n", 0) for g in grid), "accept": all(not g.get("missing") and not g["pass_to_fail"] and not g["errors"] and not g["fault_runs"] and not g["unmatched"] for g in grid)}
    # soil
    base_a = load(REV85 / "finB2_A.json")
    soil_new = base_a if self_test else load(acc / "soil/soil_A.json")
    if soil_new:
        two = compare_event(soil_new, base_a, "soil_two", keep=lambda k: k[0].endswith("|two"))
        soft = [r for r in two["failed_rows"] if "|G1|" in r or "|J2|" in r]
        out["soil"] = {**two, "soft_failed": soft, "accept": two["n"] == 60 and not soft and not two["pass_to_fail"] and not two["errors"] and not two["fault_runs"],
                       "chrono_pick": soil_pick(soil_new, base_a)}
    else:
        out["soil"] = {"missing": True}
    # regression
    reg = []
    for name, stored in (("clip_harness", "finB2_harness.json"), ("clip_p0", "finB2_p0.json"), ("clip_x426_C", "fin_x426_C.json"), ("clip_x426_D", "fin_x426_D.json")):
        base = load(REV85 / stored)
        new = base if self_test else None
        if not self_test:
            matches = sorted((acc / "regression").glob(f"{name}*.json")) if (acc / "regression").exists() else []
            new = load(matches[0]) if matches else None
        reg.append(compare_flat(new, base, name) if new and base else {"name": name, "missing": True})
    out["regression_flat"] = reg
    if not self_test:
        clip_a = load(acc / "regression/clip_A.json")
        out["regression_A"] = compare_event(clip_a, base_a, "clip_A") if clip_a else {"missing": True}
        clip_r79 = acc / "regression/clip_r79_L1L2.json"
        report = r79_judge([clip_r79], acc / "regression/clip_r79_L1L2_judgement.json") if clip_r79.exists() else None
        if report and "error" not in report:
            old = {r["key"]: r for r in stored_runs(REV79 / "fin_r79_merged_judgement.json")}
            out["regression_r79_L1L2"] = {"n": len(report["runs"]), "unmatched": report["unmatched"], "errors": report["errors"],
                                          "pass_to_fail": [r["key"] for r in report["runs"] if r["key"] in old and old[r["key"]]["pass"] and not r["pass"]]}
        else:
            out["regression_r79_L1L2"] = report or {"missing": True}
        out["regression_r79_L3L4"] = "record only: those keys are also in the noise L3 and L4 steps"
    # D8, crawler
    d8 = load(acc / "d8/d8_both.json")
    out["d8"] = judge_d8(d8, load(acc / "d8/d8_main_off.json")) if d8 else {"missing": True}
    crawler = load(acc / "crawler/crawler_both.json")
    out["crawler"] = judge_crawler(crawler) if crawler else {"missing": True}
    # noise
    stored_l2 = load(REV79 / "fin_r79_merged_judgement.json")
    if self_test:
        out["noise_L2"] = noise_verdict(stored_l2, stored_l2)
    else:
        report = r79_judge([acc / "noise/r79_L1L2.json"], acc / "noise/r79_L1L2_judgement.json")
        out["noise_L2"] = noise_verdict(report, stored_l2) if report and "error" not in report else (report or {"missing": True})
        if (acc / "noise/r79_L1L2.json").exists():
            for level in ("L3", "L4"):
                run = acc / "noise" / f"r79_{level}.json"
                if run.exists():
                    judge_out = acc / "noise" / f"r79_{level}_judgement.json"
                    script = WT / "04_scripts/03_control/s8/r79_L3L4_final.py"
                    done = subprocess.run([sys.executable, "-I", "-B", str(script), str(WT), "judge", str(judge_out), str(run), "--reference", str(acc / "noise/r79_L1L2.json"),
                                           "--previous", str(REV79 / "fin_r79_L3L4_final_judgement.json")], capture_output=True, text=True, timeout=1800)
                    judged = load(judge_out) if done.returncode == 0 else None
                    out[f"noise_{level}_record"] = (judged or {}).get("levels", {"error": done.stderr[-500:]})
    path = acc / ("judgement_self_test.json" if self_test else "judgement.json")
    path.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    for key, value in out.items():
        print(key, json.dumps(value, default=float)[:700])
    print("->", path)


if __name__ == "__main__":
    main()
