"""H-SH summary: per line the anchor path, c_hat difference bounds and the judged margins.

Reads the ``hsh_run.py`` output (record only; no judgement is changed). For each line
``d = c_hat(current) - c_hat(shadow plan A)`` over every update after each confirmed LOC (mm):

* ``shift_up_mm = max(d_max, 0)``: with plan A the heave loop would lift this much more
  (stroke) -> compared with ``stroke_guard_margin_mm`` (682.8 mm guard - run maximum stroke);
* ``shift_down_mm = max(-d_min, 0)``: with plan A it would stop this much lower (crawler
  clearance) -> compared with ``clearance_margin_mm`` (lowest judged 25 mm crawler clearance
  value - 25 mm).

The 1 : 1 shift is the review's assumption (``loc_anchor_review.md`` 7: the heave loop drives
c_hat to its target). Classes: ``no_loc`` (no confirmed LOC), ``zero`` (path 3 or d = 0 to
1e-9 mm), ``below_margin`` (every non-zero shift below its margin), ``within_margin`` (a
shift reaches its margin, or the margin is not known for a non-zero shift). The second,
stricter column ``strict_class`` compares ``max(|d|)`` with the smaller of both margins.

Usage (python-dev python.exe)::

    python -I -B hsh_summary.py <hsh_shadow.jsonl> --out <hsh_summary.json>

Exit: 0 written (also with within-margin lines), 2 input error. The last stdout line is JSON.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ZERO_MM = 1e-9
EXPECTED_LINES = 456
CLASS_NO_LOC, CLASS_ZERO = "no_loc", "zero"
CLASS_BELOW, CLASS_WITHIN = "below_margin", "within_margin"
EXIT_OK, EXIT_INPUT = 0, 2


def _shift_class(shift_mm: float, margin_mm: float | None) -> str:
    if shift_mm <= ZERO_MM:
        return CLASS_ZERO
    if margin_mm is None or shift_mm >= margin_mm:
        return CLASS_WITHIN
    return CLASS_BELOW


def _combined(classes: list[str]) -> str:
    if CLASS_WITHIN in classes:
        return CLASS_WITHIN
    if CLASS_BELOW in classes:
        return CLASS_BELOW
    return CLASS_ZERO


def line_summary(row: dict) -> dict:
    """The H-SH record of one line (paths, bounds, margins, classes)."""
    record = row.get("loc_shadow") or {}
    locs = record.get("locs") or []
    margins = row.get("margins") or {}
    d1 = row.get("d1") or {}
    out = {
        "key": row["key"], "group": d1.get("group"), "path_kind": d1.get("path"),
        "setting": d1.get("setting"), "verdict": d1.get("verdict"),
        "fail_items": d1.get("fail_items"), "final_phase": row.get("final_phase"),
        "paths": [loc["path"] for loc in locs], "n_loc": len(locs),
        "t_P_s": [loc["t_P_s"] for loc in locs],
        "c_min_tP_mm": [loc["c_min_tP_mm"] for loc in locs],
        "c_hat_tL_current_mm": [loc["c_hat_tL_current_mm"] for loc in locs],
        "c_hat_tL_shadow_mm": [loc["c_hat_tL_shadow_mm"] for loc in locs],
        "att_single_minus_centred_deg": [
            [a - b for a, b in zip(loc["att_single_deg"], loc["att_centred_deg"], strict=True)]
            for loc in locs],
        "window_n": [loc["window_n"] for loc in locs],
        "short_window": any(loc["short_window"] for loc in locs),
        "d_min_mm": record.get("diff_min_mm"), "d_max_mm": record.get("diff_max_mm"),
        "stroke_max_mm": margins.get("stroke_max_mm"),
        "stroke_guard_margin_mm": margins.get("stroke_guard_margin_mm"),
        "clearance_margin_mm": margins.get("clearance_margin_mm"),
        "clearance_values_mm": margins.get("clearance_values_mm"),
    }
    if not locs or out["d_min_mm"] is None:
        out.update(shift_up_mm=None, shift_down_mm=None, cls=CLASS_NO_LOC,
                   strict_class=CLASS_NO_LOC)
        return out
    shift_up = max(out["d_max_mm"], 0.0)
    shift_down = max(-out["d_min_mm"], 0.0)
    up_class = _shift_class(shift_up, out["stroke_guard_margin_mm"])
    down_class = _shift_class(shift_down, out["clearance_margin_mm"])
    margins_mm = (out["stroke_guard_margin_mm"], out["clearance_margin_mm"])
    known = [margin for margin in margins_mm if margin is not None]
    strict = _shift_class(max(shift_up, shift_down), min(known) if known else None)
    out.update(shift_up_mm=shift_up, shift_down_mm=shift_down, up_class=up_class,
               down_class=down_class, cls=_combined([up_class, down_class]), strict_class=strict)
    return out


def _counts(lines: list[dict], name: str) -> dict:
    return dict(collections.Counter(line[name] for line in lines))


def _path_counts(lines: list[dict]) -> dict:
    counter = collections.Counter()
    for line in lines:
        kinds = set(line["paths"]) or {"none"}
        for kind in kinds:
            counter[kind] += 1
    return dict(counter)


def _extremes(lines: list[dict]) -> dict:
    with_d = [line for line in lines if line["d_min_mm"] is not None]
    if not with_d:
        return {}
    low = min(with_d, key=lambda line: line["d_min_mm"])
    high = max(with_d, key=lambda line: line["d_max_mm"])
    return {"d_min_mm": low["d_min_mm"], "d_min_key": low["key"],
            "d_max_mm": high["d_max_mm"], "d_max_key": high["key"],
            "abs_over_1mm": sum(max(abs(line["d_min_mm"]), abs(line["d_max_mm"])) > 1.0
                                for line in with_d),
            "abs_over_5mm": sum(max(abs(line["d_min_mm"]), abs(line["d_max_mm"])) > 5.0
                                for line in with_d)}


def summarise(rows: list[dict]) -> dict:
    lines = [line_summary(row) for row in rows]
    by_group: dict[str, dict] = {}
    for group in sorted({line["group"] for line in lines}):
        members = [line for line in lines if line["group"] == group]
        by_group[group] = {"lines": len(members), "classes": _counts(members, "cls"),
                           "paths": _path_counts(members), **_extremes(members)}
    return {
        "lines": len(lines), "errors": sum(1 for row in rows if row.get("error")),
        "classes": _counts(lines, "cls"), "strict_classes": _counts(lines, "strict_class"),
        "paths": _path_counts(lines), "extremes": _extremes(lines), "by_group": by_group,
        "within_margin_keys": [line["key"] for line in lines if line["cls"] == CLASS_WITHIN],
        "strict_within_keys": [line["key"] for line in lines
                               if line["strict_class"] == CLASS_WITHIN],
        "per_line": lines,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("lines", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        with args.lines.open(encoding="utf-8") as handle:
            rows = [json.loads(text) for text in handle if text.strip()]
    except (OSError, json.JSONDecodeError) as exc:
        print(f"input: {exc!r}", file=sys.stderr)
        return EXIT_INPUT
    summary = summarise(rows)
    args.out.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    short = {name: summary[name] for name in ("lines", "errors", "classes", "strict_classes",
                                              "paths", "extremes")}
    short["complete"] = summary["lines"] == EXPECTED_LINES
    print(json.dumps(short))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
