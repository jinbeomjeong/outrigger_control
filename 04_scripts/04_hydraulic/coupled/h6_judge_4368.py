"""436.8 path 1 judge of H-6 (dg3 v4_on, 135 lines), new version (rules rev5 R5-A1, D-19).

H-6 had no grade code before (rev5 R5-A1 table). The grade is rev4 R4-B6 (criteria revision 8
2 #6 and 7.1: "L2 실패 0(키별 꺼짐과 같음), L3 9(기록), J-P3 통과(ext_moving 0), 새 FAULT 0"),
in this order:

  1. stops: J-P3 (rev3 R3-C8 / criteria revision 9 3.2 on the ③ line: ext_moving
     ``breach_reads`` >= 1 = H-7, a defect row = setting defect), J9 (``hydraulics_record.
     m2_clipped_steps_post_lift`` > 0 = H-9, criteria revision 2), fallback-leg ``n_late`` > 0
     (``lock_window_alignment``, H-7);
  2. a FAULT name the L1 line of the same harness, ``case_index`` and ``inner`` (rev4 R4-B3,
     the H-8 VB noise L1 line) does not have (S-6 basis, ``r79.warn_fault``) = ``미달``;
  3. a line grade ``판정 불가`` (missing key, no L1 pair, error line; original rules 9.3) makes the
     bundle ``판정 불가`` (original 8.1: 판정 불가 > 미달 > 통과);
  4. the L3 134 failures (judge gates, re-aggregated by ``h8_noise_judge_4368.grade_line``) are
     recorded; the L2 line goes into the H-8 L2 count (``h8_noise_judge_4368`` replaces it).
A line whose recorded ``two_pressure.extend_start_rule`` is not ``tracked_bound`` is not an H-6
line (rev1 RV1-3: tag ``final_C4G2_P3_LAS_K1``): a finding (S-2). Rev8 R8-2: J-P3 reads ③ from the
line's ``controller_tag`` (a tag that is not ③ = no J-P3 and S-2), and a ③ line without the
recorded ``extend_start_rule`` has J-P3 ``판정 불가``.

Usage (python-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/h6_judge_4368.py --out <report.json>
      --h6 resume_k1/h6_dg3_v4on.json --l1-ref resume_k1/h8_noise_VB.json
      --judge <judge output.json> [--run-judge]
      [--t4h-dir <dir: only without resume_k1/h6_dg3_v4on_t4h/>]
      [--rules-dir <verif_matrix>]
  ``--run-judge`` first writes ``--judge`` with ``r79_sensor_judge.py judge <judge> <h6>
  <L1 lines of --l1-ref> --s4-late-loc``; without it ``--judge`` must exist (the H-8 VB
  ``judge-merged`` output also works: it holds the same rows).
Exit codes: 0 judged without a finding, 1 a finding (stop, 미달, 판정 불가, S-2 / S-15),
2 input error, 3 internal error.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.append(str(_path))

import h8_noise_judge_4368 as h8  # noqa: E402
import judge4368_common as common  # noqa: E402

EXTEND_START_SETTING = "two_pressure.extend_start_rule"
TRACKED_BOUND = "tracked_bound"
EXPECTED_LINES = {"L2": 1, "L3": 134}
"""Original rules 5.1 H-6 / rev1 RV1-3: 135 lines (L3 134 + L2 1)."""
DEFINITION_CHANGES = ("D-19",)
J_P3_NOT_APPLICABLE = "not_applicable"
J_P3_NOT_JUDGEABLE = "not_judgeable"

GRADE_STOP = "멈춤"
GRADE_FAIL = "미달"
GRADE_PASS = "통과"


# ----------------------------------------------------------------------------- line inputs
def bound_check_of(run: dict) -> dict | None:
    """The ③ ext_moving record (the r79 row copy, else the plant record)."""
    if "extend_bound_check" in run:
        return run["extend_bound_check"]
    return (run.get("hydraulics_record") or {}).get("extend_bound_check")


ROD_BASIS_T4H = "T4h rod_pressure_Pa"
ROD_BASIS_CONFIGURATION = "구성 규칙(r79 두 압력 판독)"


def rod_reading(run: dict, t4h_folders: list[Path] | tuple[Path, ...]) -> tuple[bool | None, str]:
    """Rev3 R3-C8 1 with rev12 R12-1: the line's own T4h ``rod_pressure_Pa`` finite somewhere.

    A line without ``t4h_file`` uses the configuration rule (the r79 adapter reads head and rod
    pressure: "있음"). A recorded ``t4h_file`` found 0 or 2+ times in ``t4h_folders`` is S-2:
    ``(None, "S-2: ...")``, never the configuration rule (Q-R12-1 = A). A found file without
    ``rod_pressure_Pa`` keeps the configuration rule (unchanged).
    """
    located = common.locate_t4h(run, t4h_folders)
    if located["status"] == common.T4H_NO_RECORD:
        return True, ROD_BASIS_CONFIGURATION
    if located["status"] == common.T4H_STOP:
        return None, f"S-2: {located['reason']}"
    import numpy as np

    with np.load(located["path"], allow_pickle=False) as data:
        if "rod_pressure_Pa" in data.files:
            return bool(np.isfinite(data["rod_pressure_Pa"]).any()), ROD_BASIS_T4H
    return True, ROD_BASIS_CONFIGURATION


def j_p3(run: dict, t4h_dirs: tuple[Path, ...]) -> dict:
    """Criteria revision 9 3.2 table row of one ③ line.

    Rev8 R8-2: ③ is read from the line's ``controller_tag`` only; a line whose tag is not ③
    has no J-P3 (``not_applicable``, an S-2 finding of the bundle: H-6 lines are ③ lines), and
    a ③ line without the recorded ``extend_start_rule`` is ``판정 불가`` (``missing``).
    """
    from outrigger_sim.control.extend_start_bound import (
        J_P3_JUDGED,
        J_P3_NO_ROD_READING,
        j_p3_run_case,
    )
    from outrigger_sim.hydraulics.v5_options import is_extend_start_tag

    if not is_extend_start_tag(run.get("controller_tag")):
        return {"case": J_P3_NOT_APPLICABLE, "stop": None,
                "reason": f"controller_tag {run.get('controller_tag')!r} is not ③ (rev8 R8-2)"}
    if (run.get("controller_settings") or {}).get(EXTEND_START_SETTING) is None:
        return {"case": J_P3_NOT_JUDGEABLE, "stop": None, "missing": True,
                "reason": f"③ line without {EXTEND_START_SETTING} (rev8 R8-2, original 9.3)"}
    bound = bound_check_of(run)
    has_reading, basis = rod_reading(run, t4h_dirs)
    if has_reading is None:  # rev12 R12-1: the line's T4h cannot be decided
        return {"case": J_P3_NOT_JUDGEABLE, "stop": common.T4H_STOP, "rod_reading_basis": basis}
    declared = run.get("head_only_declared")
    case = j_p3_run_case(bound, has_reading, bool(declared) if declared is not None else False)
    out = {
        "case": case,
        "rod_reading_basis": basis,
        "has_rod_reading_field": run.get("has_rod_reading"),
    }
    if case == J_P3_JUDGED:
        breaches = sum((bound or {}).get("breach_reads") or [])
        out.update(breach_reads=breaches, stop="H-7" if breaches else None)
    elif case == J_P3_NO_ROD_READING:
        out["stop"] = None
    else:
        out["stop"] = "setting_defect"
    return out


def j9(run: dict) -> dict:
    clipped = (run.get("hydraulics_record") or {}).get("m2_clipped_steps_post_lift")
    if clipped is None:
        return {"missing": True}
    total = sum(clipped)
    return {"post_lift_clipped": total, "stop": "H-9" if total else None}


def j11(run: dict) -> dict:
    """Fallback-leg ``n_late`` (rev3 R3-C7: None with fallback legs = 판정 불가)."""
    lwa = run.get("lock_window_alignment")
    legs = sorted((lwa or {}).get("fallback_legs") or {})
    late = None if lwa is None else lwa.get("n_late_fallback")
    if late is None and lwa is not None and legs and lwa.get("n_late_by_leg") is not None:
        late = sum(lwa["n_late_by_leg"].get(leg, 0) for leg in legs)
    if late is None:
        return {"fallback_legs": legs, "missing": bool(legs), "n_late_fallback": None}
    return {"fallback_legs": legs, "n_late_fallback": late, "stop": "H-7" if late else None}


def fault_names(run: dict) -> set[str] | None:
    names = (run.get("r79") or {}).get("warn_fault")
    return None if names is None else {n for n in names if str(n).startswith("FAULT")}


# ------------------------------------------------------------------------------- line grade
def judge_line(run: dict, references: dict, judge_rows: dict, t4h_dirs) -> dict:
    """All H-6 items of one line; ``problems`` make it ``판정 불가``."""
    key = h8.plain_key(run["key"])
    out: dict[str, Any] = {"key": key, "level": run.get("level"), "problems": [], "stops": []}
    if "error" in run:
        out["problems"].append(f"error line: {run['error']}")
        return out
    rule = (run.get("controller_settings") or {}).get(EXTEND_START_SETTING)
    out["extend_start_rule"] = rule
    out["j_p3"], out["j9"], out["j11"] = j_p3(run, t4h_dirs), j9(run), j11(run)
    out["stops"] = [x["stop"] for x in (out["j_p3"], out["j9"], out["j11"]) if x.get("stop")]
    if out["j_p3"].get("missing"):
        out["problems"].append(out["j_p3"]["reason"])
    if out["j9"].get("missing"):
        out["problems"].append("no m2_clipped_steps_post_lift")
    if out["j11"].get("missing"):
        out["problems"].append("n_late None with fallback legs")
    pairs = references.get(h8.pair_key(run)) or []
    mine = fault_names(run)
    if len(pairs) != 1 or mine is None or fault_names(pairs[0]) is None:
        out["problems"].append(f"S-6 basis: {len(pairs)} L1 pair lines, warn_fault {mine}")
    else:
        out["new_fault"] = sorted(mine - fault_names(pairs[0]))
    row = judge_rows.get(key)
    out["line_grade"] = h8.grade_line(row, run)
    if out["line_grade"]["grade"] == h8.GRADE_NOT_JUDGEABLE:
        out["problems"].append(f"line grade: {out['line_grade']['reason']}")
    elif "new_fault" in out:
        judge_new = sorted(n for n in row["rows"]["S-6"].get("new_fault") or [])
        out["judge_s6_same"] = judge_new == out["new_fault"]
    return out


def bundle_grade(lines: list[dict]) -> tuple[str, list[str]]:
    """Rev4 R4-B6 order: stops, then 판정 불가 > 미달 > 통과 (original 8.1)."""
    stops = [f"{line['key']}: {s}" for line in lines for s in line["stops"]]
    undecided = [f"{line['key']}: {line['problems']}" for line in lines if line["problems"]]
    new_fault = [f"{line['key']}: {line['new_fault']}" for line in lines if line.get("new_fault")]
    findings = [f"멈춤 {s}" for s in stops[:20]]
    findings += [f"판정 불가 {u}" for u in undecided[:20]]
    findings += [f"미달 (새 FAULT) {n}" for n in new_fault[:20]]
    if stops:
        return GRADE_STOP, findings
    if undecided:
        return common.NOT_JUDGEABLE, findings
    if new_fault:
        return GRADE_FAIL, findings
    return GRADE_PASS, findings


# ---------------------------------------------------------------------------------------- judge
def judge(args: argparse.Namespace) -> dict:
    h6_file, ref_file = h8.read_run_file(args.h6), h8.read_run_file(args.l1_ref)
    judge_run = None
    if args.run_judge:
        extract = h8.reference_extract(ref_file, Path(args.judge).with_name("h6_L1_reference.json"))
        judge_run = h8.run_r79_judge(Path(args.judge), [args.h6, extract])
    judge_report = h8.read_judge_output(args.judge)
    if judge_report.get("s4_late_loc_rule") is None:
        raise common.InputError(f"{args.judge}: judge output without {h8.LATE_LOC_OPTION}")
    references: dict[tuple, list[dict]] = defaultdict(list)
    for run in ref_file["results"]:
        if run.get("level") == h8.LEVEL_REFERENCE and "error" not in run:
            references[h8.pair_key(run)].append(run)
    rows = {h8.plain_key(r["key"]): r for r in judge_report.get("runs") or []}
    # rev12 R12-1: the H-6 file's own convention folders, one --t4h-dir only without them
    t4h_dirs = tuple(common.t4h_folders(args.h6, h6_file["results"], args.t4h_dir or ()))
    lines = [judge_line(run, references, rows, t4h_dirs) for run in h6_file["results"]]
    status, findings = bundle_grade(lines)
    counts = Counter(line["level"] for line in lines)
    if dict(counts) != EXPECTED_LINES:
        findings.append(f"S-15: H-6 lines {dict(counts)} != {EXPECTED_LINES}")
    not_p3 = [
        line["key"] for line in lines if line.get("extend_start_rule") not in (TRACKED_BOUND, None)
    ]
    if not_p3:
        findings.append(f"S-2: lines without {TRACKED_BOUND}: {not_p3[:5]}")
    not_p3_tag = [
        line["key"] for line in lines if line.get("j_p3", {}).get("case") == J_P3_NOT_APPLICABLE
    ]
    if not_p3_tag:  # rev8 R8-2: ③ by the tag; an H-6 line is a ③ line (rev1 RV1-3)
        findings.append(f"S-2: lines whose controller_tag is not ③: {not_p3_tag[:5]}")
    if judge_run is not None and judge_run["exit_code"] != 0:
        findings.append(f"judge run exit {judge_run['exit_code']}")
    l3 = [line for line in lines if line["level"] == "L3"]
    l2 = [line for line in lines if line["level"] == "L2"]
    return {
        "inputs": {
            "h6": {"path": str(args.h6), "sha256": common.file_sha256(args.h6)},
            "l1_ref": {"path": str(args.l1_ref), "sha256": common.file_sha256(args.l1_ref)},
            "judge": {"path": str(args.judge), "sha256": common.file_sha256(args.judge)},
            "t4h_folders_R12_1": [str(folder) for folder in t4h_dirs],
        },
        "judge_run": judge_run,
        "existing_tool": "없음 (rev5 R5-A1 표: H-6 등급 코드 없음, diff 대상 없음)",
        "status": status,
        "lines": dict(counts),
        "L3_record": {
            "failures": sum(1 for x in l3 if x.get("line_grade", {}).get("grade") == h8.GRADE_FAIL),
            "failed_keys": [
                x["key"] for x in l3 if x.get("line_grade", {}).get("grade") == h8.GRADE_FAIL
            ],
        },
        "L2_to_H8": [{"key": x["key"], "grade": x.get("line_grade", {}).get("grade")} for x in l2],
        "judge_s6_differs": [x["key"] for x in lines if x.get("judge_s6_same") is False],
        "j_p3_cases": dict(Counter(x["j_p3"]["case"] for x in lines if "j_p3" in x)),
        "rod_reading_basis": dict(
            Counter(x["j_p3"].get("rod_reading_basis") for x in lines if "j_p3" in x)
        ),
        "line_details": lines,
        "findings": findings,
    }


def parser() -> argparse.ArgumentParser:
    out = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    common.add_common_arguments(out)
    out.add_argument("--h6", type=Path, required=True, help="resume_k1/h6_dg3_v4on.json")
    out.add_argument("--l1-ref", type=Path, required=True, help="resume_k1/h8_noise_VB.json")
    out.add_argument("--judge", type=Path, required=True, help="r79_sensor_judge output")
    out.add_argument("--run-judge", action="store_true", help="write --judge first")
    out.add_argument("--t4h-dir", type=Path, action="append",
                     help="T4h folder only when the H-6 file has no <stem>_t4h/ or t4h/ "
                     "(at most one; rev12 R12-1)")
    return out


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return common.run_judge(
        judge, args, script=Path(__file__).resolve(), old_tools=(), changes=DEFINITION_CHANGES
    )


if __name__ == "__main__":
    sys.exit(main())
