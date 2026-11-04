"""R16 mirror2 delta 0.175 mm, C4G2 + K1: one row, same job as run_c4g2.py (commit 74032be, flow limit off).

Usage: python -I -B -X utf8 -u run_d0175.py expected | run | values <stamp>
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import metrics_c4g2 as mc  # noqa: E402
import run_c4g2 as rc  # noqa: E402
from run_c4g2 import job  # noqa: E402

ROW = "R16_mirror2_d0175_C4G2K1"
CASE = rc.R16
OFFSETS = [-1.825e-3, 2.175e-3, -1.825e-3, 2.175e-3]
OFF_BATCH = mc.ASYM / "runs_r16/r16_mirror2_d0175"
OFF = OFF_BATCH / CASE
OUT = mc.OUT


def expected() -> None:
    m = mc.metrics(OFF)
    m.pop("events_rel")
    target = max(-3.0, min(3.0, -m["D_te_kN"] / (6.679788447853166 / 0.2941966802395609)))
    doc = {"written_before_run": True, "note": "Off values and expectations; control-expert judges.", "code": {"commit": rc.COMMIT, "c2_sha256": rc.C2_SHA}, "offsets_mm": [v * 1e3 for v in OFFSETS], "off_dir": str(OFF),
           "expected": {"target_mm_from_off_D_te": target, "hold": "starts, end_reason time unless a re-approach falls inside the 1.5 s hold", "D_te": "equal to off (TOUCH unchanged)", "D_lift": "toward 0 from the off value",
                        "RL": "above the off 17.08 kN; the d000 and d070 rows reached 27.53 and 27.19 kN", "FL_RR": "lift near -11.3 and -1.4 kN as the other R16 rows (event driven)", "cost": "about 730 to 830 s"},
           "off_values": m}
    (OUT / "expected_c4g2_d0175_before_run.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print({q: m[q] for q in ("t_te_s", "tau_te_mm", "D_te_kN", "t_lift_s", "D_lift_kN", "ready_t_s")}, {g: round(v["min_interval_kN"], 2) for g, v in m["after_event"].items()}, "target", target)


def run() -> None:
    from outrigger_sim.batch import Case, run_cases

    head = subprocess.run(["git", "-c", "core.longpaths=true", "-C", str(rc.WT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL).stdout.strip()
    if head != rc.COMMIT:
        raise SystemExit(f"worktree at {head}, want {rc.COMMIT}")
    stamp = time.strftime("%Y%m%d_%H%M%S")
    d = rc.MAIN / "07_results/S8" / f"c4g2_{ROW}_{stamp}"
    d.mkdir(parents=False, exist_ok=False)
    (d / "code_state.json").write_text(json.dumps({"commit": head, "worktree": str(rc.WT), "c2_sha256": rc.C2_SHA, "row": ROW, "case": CASE, "pad_gap_offsets_m": OFFSETS, "preset_flags": rc.K1}, indent=1), encoding="utf-8")
    print("stamp", stamp, flush=True)
    case = Case(CASE, {"duration_s": None, "row": ROW, "pad_gap_offsets_m": OFFSETS, "preset_flags": rc.K1})
    report = run_cases([case], job, d, max_workers=1, placement="pcore", timeout_s=rc.TIMEOUT_S)
    print([(o.case_id, o.status, round(o.wall_s, 1), (o.error or "")[-2000:]) for o in report.outcomes], flush=True)


def values(stamp: str) -> None:
    from outrigger_sim.verify.s8_control import judge_batch

    b = rc.MAIN / "07_results/S8" / f"c4g2_{ROW}_{stamp}"
    vf = OUT / f"verify_{b.name}.json"
    judge_batch(b, vf, root=rc.MAIN, ref_batch=None, lookup_batches=[], deferred_ref=None)
    voff = HERE / "verify_off_r16_d0175.json"
    judge_batch(OFF_BATCH, voff, root=rc.MAIN, ref_batch=None, lookup_batches=[], deferred_ref=None)
    keep = ("item 9 J_P", "item 9 J_C", "item 9 M5", "4 max", "3 F_min", "RE1b re-READY", "2 attitude", "run")

    def rows(path: Path) -> tuple[dict, dict]:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return {r["item"]: r.get("value") for r in doc["rows"] if r.get("case") == CASE and r["item"].startswith(keep) and "sensitiv" not in r["item"] and "raw reading" not in r["item"]}, doc["meta"]

    r_on, m_on = rows(vf)
    r_off, m_off = rows(voff)
    sampling = [r.get("sampling_only_count") for r in json.loads(vf.read_text(encoding="utf-8"))["rows"] if "sampling_only_count" in r]
    d = b / CASE
    on, off = mc.metrics(d), mc.metrics(OFF)
    doc = {"on": on, "off": off, "rows_on": r_on, "rows_off": r_off, "failed": [m_on.get("failed"), m_off.get("failed")], "hold": [m_on.get("hold"), m_off.get("hold")], "first_diff_vs_off": mc.first_diff(d, OFF), "sampling_only_count": sampling,
           "side": json.loads((d / "c4g2_job_side.json").read_text(encoding="utf-8"))}
    (OUT / "c4g2_d0175_values.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    drop = ("events_rel", "phases", "dir", "touch_last3")
    for name, m in (("ON", on), ("OFF", off)):
        print(name, json.dumps({k: v for k, v in m.items() if k not in drop}, default=lambda x: str(x))[:2400])
    print("last3", on["touch_last3"])
    print("rows on", json.dumps(r_on, ensure_ascii=False)[:1400])
    print("rows off", json.dumps(r_off, ensure_ascii=False)[:1400])
    print(doc["failed"], doc["hold"], doc["first_diff_vs_off"], sampling)
    s = doc["side"]
    print({k: s[k] for k in ("c2_sha256", "models_built_offsets", "main_tree_modules_at_end", "config_retrigger_samples", "config_clip", "fs_kN", "flow_limit", "outrigger_sim")})


if __name__ == "__main__":
    if sys.argv[1] == "expected":
        expected()
    elif sys.argv[1] == "run":
        run()
    else:
        values(sys.argv[2])
