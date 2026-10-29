"""Study 3 judgement (control-expert 2026-10-29): J2 / S1 x pad A / B at the auger middle and bottom
levels (``run_S9.py`` ``p3b_aug_cases``) against the P3b top pairs, read only (no Chrono run).

Inputs per case folder: ``result_rejudge_rev60.json`` (``run_S9.py rejudge``: the current P3 rows,
spec 284 with rev. 60, the 377 demotion, U-S9-G6d P3-1 classes and the 419.8 late-LOC FLAG) when it
exists, else ``result.json``; ``record/record.npz`` for the item-4 moving pressure (the paper
definition, ``s8/paper_max_pressure_table.record_moving_peak``: F_cyl / A_p over |u_applied| >
1e-6 m/s). Code state per case: the 420.4 equivalence record of ``s9_batch_summary.py E420`` when
given (``--e420 <json> ...``), else the run start time.

Rows per case: verdict (pass / flag / fail from the P3 checks), P3-1 .. P3-8 values, READY time
(loop relative), end attitude |max| over the P3-4 window, minimum true F_cyl after the crawler
departure (per leg and overall), rut clearance after the first READY, LOC minus departure, max
moving pressure (bar, leg), sinkage, events of interest. Pair deltas = level case minus the top case
of the same soil / pad (``pair_case``).

Usage (project root, any env with numpy + PyYAML):
  python -I 04_scripts/03_control/s9/r82_p3b_aug_judge.py <out_json> <case_dir> [<case_dir> ...]
         [--e420 <json> ...]
Units: s, kN, deg, mm, bar.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s8"))

import paper_max_pressure_table as pmt  # noqa: E402

REJUDGE_FILE = "result_rejudge_rev60.json"
STRICT_ROWS = ("P3-1_recontact_pass", "P3-3_within", "P3-4_within_0p2", "P3-5_within", "P3-6_within",
               "P3-7_within", "P3-8_within")
"""P3 rows that fail a case (P3-2 has its own verdict with the 419.8 FLAG)."""


def _load_case(case_dir: Path) -> tuple[dict, dict, str]:
    result = json.loads((case_dir / "result.json").read_text(encoding="utf-8"))
    rejudge_path = case_dir / REJUDGE_FILE
    if rejudge_path.exists():
        rejudged = json.loads(rejudge_path.read_text(encoding="utf-8"))
        return result, rejudged["p3b"], REJUDGE_FILE
    return result, result["p3b"], "result.json"


def _case_name(case_dir: Path) -> str:
    return case_dir.name


def _soil_pad_level(name: str) -> tuple[str, str, str]:
    parts = name.split("_")  # P3b_<soil>_<pad>_<level>_Fs4
    return parts[1], parts[2], parts[3]


def judge_case(case_dir: Path, e420: dict) -> dict:
    result, p3b, source = _load_case(case_dir)
    checks = p3b["checks"]
    name = _case_name(case_dir)
    soil, pad, level = _soil_pad_level(name)
    failed = [row for row in STRICT_ROWS if checks.get(row) is False]
    p32 = checks.get("P3-2_verdict") or ("pass" if checks.get("P3-2_within") else "fail")
    if p32 == "fail":
        failed.append("P3-2")
    flags = list(checks.get("P3-1_flags") or []) + ([f"P3-2_{p32}"] if p32 == "flag" else [])
    if checks.get("pre_liftoff_flag"):
        flags.append("pre_liftoff")
    verdict = "fail" if failed else ("flag" if flags else "pass")
    leg = p3b["P3-3_leg_force"]
    f_after = [v / 1e3 for v in leg["F_min_after_N"]]
    t0 = float(p3b["t_loop_start_s"])
    ready = p3b["P3-6_ready"].get("t_ready_after_loop_start_s")
    pressure = pmt.record_moving_peak(case_dir)["current"]
    ext = result.get("p3b_ext") or {}
    events = [str(e["name"]) for e in result.get("events") or []]
    interest = ("INFO_LOC_CLEARANCE_MARGIN", "INFO_LOC_WINDOW_RESTART", "INFO_PRESSURE_ZERO_RETURN_TOL",
                "WARN_PRESSURE_ZERO_SKIPPED", "INFO_LIFT_PAUSED", "INFO_TWIST_UNSETTLED", "WARN_", "FAULT_",
                "leg_reapproach_start", "soil_mode_start", "INFO_CLEARANCE_BIAS")
    counts = {key: sum(1 for n in events if n.startswith(key)) for key in interest}
    return {
        "case": name, "soil": soil, "pad": pad, "level": level,
        "pair_case": (result.get("args") or {}).get("pair_case") or f"P3b_{soil}_{pad}_top_Fs4",
        "source": source, "code_state": e420.get(name),
        "verdict": verdict, "failed_rows": failed, "flags": flags,
        "checks": {k: checks.get(k) for k in sorted(checks) if not isinstance(checks.get(k), (dict, list))
                   or k.endswith("flags")},
        "t_ready_rel_s": ready,
        "att_end_absmax_deg": checks.get("P3-4_absmax_deg"),
        "min_F_after_departure_kN": [round(v, 2) for v in f_after],
        "min_F_after_departure_all_kN": round(min(f_after), 2),
        "rut_min_after_ready_mm": None if checks.get("P3-5_rut_clearance_min_after_first_ready_m") is None
        else round(1e3 * checks["P3-5_rut_clearance_min_after_first_ready_m"], 2),
        "loc_minus_departure_s": checks.get("P3-2_loc_minus_departure_s"),
        "max_moving_pressure_bar": None if pressure["max_bar"] is None else round(pressure["max_bar"], 2),
        "max_moving_pressure_leg": pressure.get("leg"),
        "pad_sinkage_end_mm": (ext.get("pad_sinkage") or {}).get("end_mm"),
        "event_counts": counts, "t_loop_start_s": t0,
        "wall_s": result.get("wall_s"),
    }


PAIR_KEYS = ("t_ready_rel_s", "att_end_absmax_deg", "min_F_after_departure_all_kN", "rut_min_after_ready_mm",
             "loc_minus_departure_s", "max_moving_pressure_bar")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out")
    ap.add_argument("cases", nargs="+")
    ap.add_argument("--e420", nargs="*", default=[])
    args = ap.parse_args()
    e420: dict = {}
    for path in args.e420:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        rows_in = data.get("rows") or {}
        for row in (rows_in.values() if isinstance(rows_in, dict) else rows_in):
            name = row.get("case")
            if name:
                state = row.get("code_state")
                e420[name] = {"code_state": state.get("state") if isinstance(state, dict) else state,
                              "equivalent": row.get("equivalent"), "reasons": row.get("reasons")}
    rows = [judge_case(Path(c), e420) for c in args.cases]
    by_name = {r["case"]: r for r in rows}
    pairs = []
    for r in rows:
        if r["level"] == "top" or r["pair_case"] not in by_name:
            continue
        top = by_name[r["pair_case"]]
        pairs.append({"case": r["case"], "pair": top["case"],
                      "delta": {k: None if r[k] is None or top[k] is None else round(r[k] - top[k], 4)
                                for k in PAIR_KEYS}})
    out = {"meta": {"script": "04_scripts/03_control/s9/r82_p3b_aug_judge.py",
                    "spec": "control spec 411 / rev. 80 study 3 (2026-10-29)",
                    "rows_strict": list(STRICT_ROWS) + ["P3-2 (419.8 FLAG)"],
                    "e420": args.e420},
           "cases": rows, "pairs": pairs,
           "summary": {"verdicts": {r["case"]: r["verdict"] for r in rows}}}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    for r in rows:
        print(f"{r['case']:24s} {r['verdict']:5s} fail={r['failed_rows']} flags={r['flags']} "
              f"READY={r['t_ready_rel_s']} att={r['att_end_absmax_deg']} minF={r['min_F_after_departure_all_kN']} "
              f"rut={r['rut_min_after_ready_mm']} locdep={r['loc_minus_departure_s']} "
              f"p={r['max_moving_pressure_bar']}{r['max_moving_pressure_leg']} code={r['code_state']}")
    for p in pairs:
        print("  delta", p["case"], "-", p["pair"], p["delta"])
    print("->", args.out)


if __name__ == "__main__":
    main()
