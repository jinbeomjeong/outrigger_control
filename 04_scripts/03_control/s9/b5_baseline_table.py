"""B5 table: result JSONs of ``b5_baseline_compare.py`` -> paper table (Markdown + LaTeX rows)
and a summary of the wide set.

Several result files are merged (the wide set comes as ``b5_wide_A.json``, ``b5_wide_B1.json``,
``b5_wide_B2.json``); a (case, controller) pair in a later file replaces the earlier one.
Cell format "C2 / ABL / IND" (controllers in that order, "—" when missing). A failed lite gate
is marked with "*" after the value. The case column shows the display name of
``b5_baseline_compare.CASE_DISPLAY_NAMES`` (F_s as ``$F_s$``), the variable column the symbol
(A1..B3) and the variable name. Usage (an env with numpy, e.g. dynamics-dev or python-dev; the
case table is imported from ``b5_baseline_compare.py``):
  python -I b5_baseline_table.py OUT_PREFIX RESULT.json [RESULT.json ...]
writes OUT_PREFIX.md, OUT_PREFIX_rows.tex, OUT_PREFIX_summary.json.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

# ``python -I`` leaves the script folder off sys.path; the case table lives next to this file
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from b5_baseline_compare import CASES, case_display_name, case_group  # noqa: E402

ORDER = ("C2", "ABL", "IND")
GROUP_LABEL = {"A1": "지반 종류", "A2": "바닥 경사", "A3": "한 패드 연약부", "A4": "지반 사건",
               "B1": "오거 위치", "B2": "실 마찰", "B3": "패드 사양"}
DASH = "—"
WIDE_PREFIXES = ("S|", "G|")
ATT_TOL_DEG = 0.2
RUT_MIN_MM = 25.0
STROKE_GATE_MM = 684.8
CELL_KEYS = ("att", "ready", "fmin", "crawler", "p")


def _fmt(value, digits: int, is_failed: bool = False) -> str:
    if value is None:
        return DASH
    text = f"{value:.{digits}f}"
    return text + ("*" if is_failed else "")


def load_records(paths: list[Path]) -> dict[str, dict[str, dict]]:
    """Merge result files into ``case -> controller -> record`` (later files win)."""
    by_case: dict[str, dict] = defaultdict(dict)
    for path in paths:
        for record in json.loads(Path(path).read_text(encoding="utf-8"))["records"]:
            backfill_gates(record)
            by_case[record["case"]][record["controller"]] = record
    return by_case


def is_wide_case(case_id: str) -> bool:
    return case_id.startswith(WIDE_PREFIXES)


def backfill_gates(record: dict) -> None:
    """Lite gates from the stored fields (records written before the runner had them)."""
    if "lite_gates" in record or "error" in record:
        return
    is_ready = record["t_ready_s"] is not None
    min_off = record["min_Fcyl_after_off_kN"]
    rut = record["rut_all_ready_mm"]
    record["lite_gates"] = {
        "ready_no_fault": is_ready and not record["fault"],
        "crawler": (is_ready and not record["crawler_liftoff_fail"]
                    and not (record["n_crawler_recontact"] or 0)),
        "Fmin": min_off is not None and min_off >= record["F_min_kN"],
        "att": record["att_end_absmax_deg"] <= ATT_TOL_DEG,
        "rut": rut is not None and rut >= RUT_MIN_MM,
        "stroke": record["max_motor_stroke_mm"] <= STROKE_GATE_MM}
    record["lite_pass"] = all(record["lite_gates"].values())


def _fmin_cell(record: dict) -> str:
    gates = record["lite_gates"]
    # after an event the event window decides; else the post lift-off minimum
    fmin = record.get("min_Fcyl_after_event_kN") or record["min_Fcyl_after_off_kN"]
    below_s = record["below_Fmin_after_off_s"] or 0.0
    text = _fmt(fmin, 1, not gates["Fmin"])
    if below_s > 0:
        text += f" ({below_s:.1f} s)"
    return text


def _crawler_cell(record: dict) -> str:
    if record["crawler_liftoff_fail"]:
        return f"실패 {((record['crawler_N_at_ready'] or 0) / 1e3):.1f} kN"
    if record["t_ready_s"] is None:
        return DASH
    text = _fmt(record["rut_all_ready_mm"], 1, not record["lite_gates"]["rut"])
    if record["false_loc"]:
        text += " 거짓LOC"
    return text


def _ready_cell(record: dict) -> str:
    if record["t_ready_s"] is not None:
        return _fmt(record["t_ready_s"], 1)
    return "FAULT" if record["fault"] else "없음"


def cells(records_by_controller: dict) -> dict:
    """Metric cells of one case, each "C2 / ABL / IND"."""
    out = defaultdict(list)
    for name in ORDER:
        record = records_by_controller.get(name)
        if record is None or "error" in record:
            for key in CELL_KEYS:
                out[key].append("err" if record is not None else DASH)
            continue
        out["att"].append(_fmt(record["att_end_absmax_deg"], 3,
                               not record["lite_gates"]["att"]))
        out["ready"].append(_ready_cell(record))
        out["fmin"].append(_fmin_cell(record))
        out["crawler"].append(_crawler_cell(record))
        out["p"].append(_fmt(record["p_max_move_bar"], 1))
    return {key: " / ".join(values) for key, values in out.items()}


def table_rows(by_case: dict) -> tuple[list[str], list[str]]:
    """Markdown lines and LaTeX rows of the table cases (ids not in the wide set)."""
    markdown = ["| 변수 | 사례 | 자세 오차 [°] | READY [s] "
                "| 이탈 뒤 최소 $F_{cyl}$ [kN] (미달 시간) "
                "| READY 때 크롤러 틈 [mm] / 이탈 실패 | 최대 이동 압력 [bar] |",
                "|---|---|---|---|---|---|---|"]
    latex = []
    for case in (c for c in CASES if c in by_case):
        cell = cells(by_case[case])
        group_symbol = case_group(case)
        group = f"{group_symbol} {GROUP_LABEL.get(group_symbol, '')}".rstrip()
        name = case_display_name(case, as_math=True)
        first_record = by_case[case][next(iter(by_case[case]))]
        src = first_record["src"].replace("|", "·")
        markdown.append(f"| {group} | {name} ({src}) | {cell['att']} | {cell['ready']} "
                        f"| {cell['fmin']} | {cell['crawler']} | {cell['p']} |")
        latex.append(f"  {group} & {name} & {cell['att']} & {cell['ready']} & {cell['fmin']} & "
                     f"{cell['crawler']} & {cell['p']} \\\\")
    return markdown, latex


def wide_summary(by_case: dict) -> dict:
    """Per controller: runs, lite passes and failures per gate over the wide set."""
    wide_ids = [c for c in by_case if is_wide_case(c)]
    summary = {}
    for name in ORDER:
        rows = [by_case[c][name] for c in wide_ids
                if name in by_case[c] and "error" not in by_case[c][name]]
        if not rows:
            continue
        failures = defaultdict(int)
        for record in rows:
            for gate, is_ok in record["lite_gates"].items():
                failures[gate] += 0 if is_ok else 1
        summary[name] = {
            "runs": len(rows), "lite_pass": sum(r["lite_pass"] for r in rows),
            "gate_failures": dict(failures),
            "crawler_liftoff_fail": sum(r["crawler_liftoff_fail"] for r in rows),
            "false_loc_runs": sum(bool(r["false_loc"]) for r in rows),
            "fault": sum(r["fault"] for r in rows)}
    return summary


def summary_markdown(summary: dict) -> list[str]:
    lines = ["", "| 제어기 | 실행 | lite 통과 | READY·FAULT | 크롤러 | F_min | 자세 | 틈 | 행정 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name, counts in summary.items():
        failures = counts["gate_failures"]
        lines.append(
            f"| {name} | {counts['runs']} | {counts['lite_pass']} "
            f"| {failures.get('ready_no_fault', 0)} | {failures.get('crawler', 0)} "
            f"| {failures.get('Fmin', 0)} | {failures.get('att', 0)} "
            f"| {failures.get('rut', 0)} | {failures.get('stroke', 0)} |")
    return lines


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    prefix = Path(sys.argv[1])
    by_case = load_records([Path(p) for p in sys.argv[2:]])
    markdown, latex = table_rows(by_case)
    summary = wide_summary(by_case)
    if summary:
        markdown += summary_markdown(summary)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    prefix.with_suffix(".md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    Path(f"{prefix}_rows.tex").write_text("\n".join(latex) + "\n", encoding="utf-8")
    Path(f"{prefix}_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    sys.stdout.buffer.write(("\n".join(markdown) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
