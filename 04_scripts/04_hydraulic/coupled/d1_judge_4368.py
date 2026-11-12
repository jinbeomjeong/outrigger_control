"""436.8 path 1 judge of D-1 (H-1 / H-2), new version (rules rev5 R5-A1, R5-D1).

Reads the H-1 output (``resume_k1/h1_d1.jsonl``) and re-grades every line's ``d1`` block with
the 436.8 definitions; the item values stay the recorded ``d1.items`` (rev3 R3-A2 layer 2).
Then it writes the re-graded lines and, with ``--select-out``, runs ``d1_select.py`` on them
(rev3 R3-A2 layer 3; the selection code is unchanged). Changes against ``d1_runs.judgement`` /
``d1_select.py`` (rev5 R5-A3):

  D-23  every G-3-exempt line (``ASSUMED_BOUNDARY`` tag = H-S-0 ``fup-rec``, VB and V0, every
        eps and auger level) whose VB is ``fail`` while the same-key V0 passes gets the record
        "가정 경계 미성립" and the user question on the lift-off boundary (rev3 R3-A1).
  D-24  spec 377: a g6-path line with ``G6-7_preloc`` false and ``d1.g6_preloc.preloc_flag_ok``
        true has that item demoted to the FLAG ``P3-8_demoted`` (out of ``fail_items``, into
        ``demoted_items`` with rule 377). Rev6 R6-C3 (U-S9-G6c): ``preloc_flag_ok`` false with
        ``G6-3_Fmin`` true and no FAULT (``final_phase``) is the FLAG ``P3-8_preloc_loss`` (rule
        ``U-S9-G6c``, also in ``demoted_items``). A g6 line with ``G6-7_preloc`` false and no
        ``preloc_flag_ok`` is ``판정 불가`` (``P3-8_unchecked`` is not used). Other demotions
        already inside the harness values are not repeated.
  D-25  READY origin (rev4 R4-C1): ``values.times.t_check_start_s`` <= 0.1 s (+1e-9) when the
        F-1 field exists, else the harness definition (closed loop from t = 0, "정의에 의함");
        ``d1.t_ready_s`` must equal ``values.times.t_first_ready_s`` within 1e-9, else
        ``판정 불가``.
The recorded ``d1.verdict`` is compared with the re-graded one (a difference is listed, it is
explained by D-24 or else a finding).

Usage (python-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/d1_judge_4368.py --out <report.json>
      --h1 <h1_d1.jsonl> --regraded <regraded.jsonl> [--select-out <d1_select report.json>]
      [--rules-dir <verif_matrix>]
Exit codes: 0 judged, 1 a finding (판정 불가 line, unexplained verdict change, selection gate),
2 input error, 3 internal error.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import judge4368_common as common  # noqa: E402

VERDICT_PASS = "pass"
VERDICT_FAIL = "fail"
VERDICT_ALLOWED_STOP = "allowed_stop"
"""``d1_runs.VERDICT_*``."""
TAG_ASSUMED_BOUNDARY = "ASSUMED_BOUNDARY"
"""``d1_rows.TAG_ASSUMED_BOUNDARY`` (H-S-0 ``fup-rec`` rows)."""
PRELOC_ITEM = "G6-7_preloc"
DEMOTION_FLAG = "P3-8_demoted"
DEMOTION_RULE = "377"
PRELOC_LOSS_FLAG = "P3-8_preloc_loss"
PRELOC_LOSS_RULE = "U-S9-G6c"
G6_3_ITEM = "G6-3_Fmin"
FAULT_PHASES = ("fault", "fault_reground")
"""``r72_judge`` no-FAULT test: the final phase is not a FAULT phase."""
READY_ORIGIN_LIMIT_S = 0.1
DEFINITION_CHANGES = ("D-23", "D-24", "D-25")


def regrade(line: dict) -> dict:
    """Re-graded ``d1`` fields of one line: verdict, fail_items, demoted_items, problems."""
    d1 = line["d1"]
    items = dict(d1.get("items") or {})
    false_items = sorted(name for name, ok in items.items() if not ok)
    demoted, problems = [], []
    if d1.get("path") == "g6" and items.get(PRELOC_ITEM) is False:
        demotion, problem = preloc_demotion(line, items)
        if demotion is not None:
            demoted.append(demotion)
        if problem is not None:
            problems.append(problem)
    fail_items = [name for name in false_items if name not in {d["item"] for d in demoted}]
    if d1.get("verdict") == VERDICT_ALLOWED_STOP:
        verdict = VERDICT_ALLOWED_STOP  # d1_runs: soil stop on a row that allows it
    else:
        verdict = VERDICT_FAIL if fail_items else VERDICT_PASS
    problems += ready_origin_problems(line)
    return {
        "verdict": verdict,
        "fail_items": fail_items,
        "demoted_items": demoted,
        "flags": [d["flag"] for d in demoted],
        "problems": problems,
    }


def preloc_demotion(line: dict, items: dict) -> tuple[dict | None, str | None]:
    """The G6-7 branches of ``r72_judge`` (rev5 R5-D1, rev6 R6-C3) for a false ``G6-7_preloc``.

    Returns (demoted item or None, ``판정 불가`` reason or None): ``preloc_flag_ok`` true =
    spec 377 ``P3-8_demoted``; false with G6-3 true and no FAULT (``final_phase``) = U-S9-G6c
    ``P3-8_preloc_loss``; false otherwise = a failure; missing = ``판정 불가`` (the old
    ``P3-8_unchecked`` tag is not used).
    """
    flag_ok = (line["d1"].get("g6_preloc") or {}).get("preloc_flag_ok")
    if flag_ok is None:
        return None, "G6-7_preloc false without d1.g6_preloc.preloc_flag_ok (F-8)"
    if flag_ok is True:
        return {"item": PRELOC_ITEM, "rule": DEMOTION_RULE, "flag": DEMOTION_FLAG}, None
    g6_3, final_phase = items.get(G6_3_ITEM), line.get("final_phase")
    if g6_3 is None or final_phase is None:
        return None, f"U-S9-G6c inputs missing ({G6_3_ITEM} {g6_3}, final_phase {final_phase})"
    if g6_3 and final_phase not in FAULT_PHASES:
        return {"item": PRELOC_ITEM, "rule": PRELOC_LOSS_RULE, "flag": PRELOC_LOSS_FLAG}, None
    return None, None


def ready_origin_problems(line: dict) -> list[str]:
    """D-25."""
    times = (line.get("values") or {}).get("times") or {}
    problems = []
    check_start = times.get("t_check_start_s")
    if check_start is not None and common.is_above(check_start, READY_ORIGIN_LIMIT_S):
        problems.append(f"t_check_start_s {check_start} > 0.1 s")
    t_first, t_d1 = times.get("t_first_ready_s"), line["d1"].get("t_ready_s")
    if (t_first is None) != (t_d1 is None) or (
        t_first is not None and abs(float(t_first) - float(t_d1)) > common.COMPARE_EPS
    ):
        problems.append(f"d1.t_ready_s {t_d1} != values.times.t_first_ready_s {t_first}")
    return problems


def origin_basis(line: dict) -> str:
    has_field = ((line.get("values") or {}).get("times") or {}).get("t_check_start_s") is not None
    return "F-1 t_check_start_s" if has_field else "정의에 의함 (하네스 폐루프 t = 0)"


def assumed_boundary_records(lines: list[dict], grades: dict[str, dict]) -> list[dict]:
    """D-23: VB fail / same-key V0 pass on every ASSUMED_BOUNDARY line."""
    by_key = {}
    for line in lines:
        d1 = line["d1"]
        by_key[(d1["row_key"], d1["eps"], d1["setting"])] = d1["key"]
    out = []
    for line in lines:
        d1 = line["d1"]
        tags = ((line.get("job") or {}).get("d1") or {}).get("tags") or []
        if TAG_ASSUMED_BOUNDARY not in tags or d1["setting"] != "VB":
            continue
        v0_key = by_key.get((d1["row_key"], d1["eps"], "V0"))
        vb_verdict = grades[d1["key"]]["verdict"]
        v0_verdict = None if v0_key is None else grades[v0_key]["verdict"]
        if vb_verdict == VERDICT_FAIL and v0_verdict in (VERDICT_PASS, VERDICT_ALLOWED_STOP):
            out.append(
                {
                    "key": d1["key"],
                    "v0": v0_verdict,
                    "record": "가정 경계 미성립",
                    "question": "앞들림 경계 재결정 (사용자 질문, rev3 R3-A1)",
                }
            )
    return out


def write_regraded(lines: list[dict], grades: dict[str, dict], path: Path) -> None:
    with Path(path).open("w", encoding="utf-8", newline="\n") as handle:
        for line in lines:
            if "d1" not in line:
                continue
            grade = grades[line["d1"]["key"]]
            d1 = {
                **line["d1"],
                "verdict": grade["verdict"],
                "fail_items": grade["fail_items"],
                "demoted_items": grade["demoted_items"],
                "verdict_recorded": line["d1"].get("verdict"),
            }
            handle.write(json.dumps({**line, "d1": d1}, ensure_ascii=False) + "\n")


def run_select(regraded: Path, out: Path) -> dict:
    completed = subprocess.run(  # noqa: S603 (this interpreter, fixed script)
        [sys.executable, "-I", "-B", str(HERE / "d1_select.py"), str(out), str(regraded)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return {
        "exit_code": completed.returncode,
        "last_line": (completed.stdout.strip().splitlines() or [""])[-1],
        "out": str(out),
    }


def judge(args: argparse.Namespace) -> dict:
    lines = common.read_jsonl(args.h1)
    errors = [line.get("job") for line in lines if "error" in line]
    good = [line for line in lines if "error" not in line and "d1" in line]
    grades = {line["d1"]["key"]: regrade(line) for line in good}
    changed = []
    for line in good:
        grade = grades[line["d1"]["key"]]
        if grade["verdict"] != line["d1"].get("verdict"):
            changed.append(
                {
                    "key": line["d1"]["key"],
                    "recorded": line["d1"].get("verdict"),
                    "regraded": grade["verdict"],
                    "explained_by": "D-24" if grade["demoted_items"] else None,
                }
            )
    undecided = {k: g["problems"] for k, g in grades.items() if g["problems"]}
    write_regraded(good, grades, args.regraded)
    report: dict[str, Any] = {
        "inputs": {"h1": str(args.h1)},
        "lines": len(lines),
        "errors": len(errors),
        "regraded": str(args.regraded),
        "demoted": {k: g["demoted_items"] for k, g in grades.items() if g["demoted_items"]},
        "verdict_changes": changed,
        "not_judgeable": undecided,
        "ready_origin_basis": dict(Counter(origin_basis(line) for line in good)),
        "assumed_boundary": assumed_boundary_records(good, grades),
        "note": "436.8부터 새 판이 377을 적용 (rev5 R5-D1)",
    }
    if args.select_out is not None:
        report["d1_select"] = run_select(args.regraded, args.select_out)
    findings = [f"{len(errors)} error lines"] if errors else []
    findings += [f"판정 불가 {key}: {problems}" for key, problems in list(undecided.items())[:20]]
    findings += [
        f"unexplained verdict change {c['key']}" for c in changed if c["explained_by"] is None
    ]
    if report["assumed_boundary"]:
        findings.append(f"가정 경계 미성립 {len(report['assumed_boundary'])} lines: ask the user")
    if report.get("d1_select", {}).get("exit_code") not in (None, 0):
        findings.append(f"d1_select exit {report['d1_select']['exit_code']}")
    report["findings"] = findings
    return report


def parser() -> argparse.ArgumentParser:
    out = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    common.add_common_arguments(out)
    out.add_argument("--h1", type=Path, required=True, help="resume_k1/h1_d1.jsonl")
    out.add_argument("--regraded", type=Path, required=True, help="re-graded lines (output)")
    out.add_argument("--select-out", type=Path, default=None, help="d1_select report (output)")
    return out


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return common.run_judge(
        judge,
        args,
        script=Path(__file__).resolve(),
        old_tools=(HERE / "d1_runs.py", HERE / "d1_select.py"),
        changes=DEFINITION_CHANGES,
    )


if __name__ == "__main__":
    sys.exit(main())
