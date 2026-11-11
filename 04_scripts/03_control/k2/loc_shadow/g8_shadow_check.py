"""E5a check: the G8 shadow rows against the stored B-6 rows and the review's plan A values.

Per arm (``off``, ``tcl``) and key:
  * command hash ``sha`` of the shadow row = the stored B-6 row (the shadow left the commands);
  * the controller's single-period c_hat(t_L) of the shadow record = the stored trace ``ce`` at
    ``t_loc`` (both are the current estimate);
  * the shadow c_hat(t_L) (plan A) against ``loc_anchor_review.md`` 3.1 "centred 1 s" (rounded
    to 0.01 mm there; criterion 0.1 mm, review 5.2 E5a);
  * the shadow ring buffer against the trace ``att`` of the same periods (deg).

Usage (python-dev python.exe)::

    python -I -B g8_shadow_check.py <stored b6 dir> <e5a dir> --out <json>

Exit: 0 every check holds, 1 a check fails, 2 input error. The last stdout line is JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ARMS = ("off", "tcl")
ROW_FILE_STORED = "g8_b6.jsonl"
ROW_FILE_SHADOW = "g8_shadow.jsonl"
REVIEW_CENTRED_MM = {
    ("off", "s8"): 2.25, ("off", "s6"): 3.50, ("off", "s10"): 5.56, ("off", "s16"): 4.02,
    ("tcl", "s16"): 5.50, ("tcl", "s6"): 5.22, ("tcl", "s8"): 5.38, ("tcl", "s10"): 5.35,
}
"""``loc_anchor_review.md`` 3.1 / scratchpad ``g8.txt`` "centred_1s" c_hat(t_L), mm."""
CENTRED_TOLERANCE_MM = 0.1
REVIEW_ROUNDING_MM = 0.005
CE_TOLERANCE_MM = 0.0015
"""The trace stores ``ce`` rounded to 0.001 mm."""
TIME_TOLERANCE_S = 1e-6
EXIT_OK, EXIT_FAIL, EXIT_INPUT = 0, 1, 2


def _rows(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8") as handle:
        rows = [json.loads(text) for text in handle if text.strip()]
    return {row["key"]: row for row in rows}


def _seed(key: str) -> str:
    return key.split("|")[1]


def _trace_value(trace: list[dict], t_s: float, name: str):
    for point in trace:
        if abs(point["t"] - t_s) < 1e-3:
            return point[name]
    return None


def _buffer_vs_trace_deg(buffer: list[list[float]], trace: list[dict]) -> float | None:
    worst = None
    for t_s, roll_deg, pitch_deg in buffer:
        att = _trace_value(trace, t_s, "att")
        if att is None:
            continue
        gap = max(abs(att[0] - roll_deg), abs(att[1] - pitch_deg))
        worst = gap if worst is None else max(worst, gap)
    return worst


def check_row(arm: str, stored: dict, new: dict) -> dict:
    record = new.get("loc_shadow") or {}
    locs = record.get("locs") or []
    loc = locs[-1] if locs else None
    result = {"arm": arm, "key": new["key"], "seed": _seed(new["key"]),
              "error": new.get("error"), "sha_same": new.get("sha") == stored.get("sha"),
              "n_loc": len(locs), "path": None if loc is None else loc["path"]}
    if loc is None:
        result["ok"] = False
        return result
    ce_stored = _trace_value(stored.get("trace") or [], loc["t_L_s"], "ce")
    review = REVIEW_CENTRED_MM.get((arm, result["seed"]))
    shadow_tL = loc["c_hat_tL_shadow_mm"]
    centred_gap = None if review is None else abs(shadow_tL - review)
    result.update({
        "t_P_s": loc["t_P_s"], "t_L_s": loc["t_L_s"], "window_n": loc["window_n"],
        "window_half_s": loc["window_half_s"],
        "c_hat_tL_current_mm": loc["c_hat_tL_current_mm"], "ce_stored_mm": ce_stored,
        "c_hat_tL_shadow_mm": shadow_tL, "review_centred_mm": review,
        "centred_gap_mm": centred_gap, "diff_tL_mm": loc["diff_tL_mm"],
        "diff_min_mm": loc["diff_min_mm"], "diff_max_mm": loc["diff_max_mm"],
        "buffer_vs_trace_deg": _buffer_vs_trace_deg(loc["raw_tilt_buffer"], new.get("trace") or []),
        "smax_stored": stored.get("smax"), "smax_new": new.get("smax"),
    })
    is_ce_ok = (ce_stored is not None
                and abs(loc["c_hat_tL_current_mm"] - ce_stored) <= CE_TOLERANCE_MM)
    is_centred_ok = (centred_gap is not None
                     and centred_gap <= CENTRED_TOLERANCE_MM + REVIEW_ROUNDING_MM)
    is_ok = bool(result["sha_same"] and not result["error"] and is_ce_ok and is_centred_ok)
    result.update(ce_ok=is_ce_ok, centred_ok=is_centred_ok, ok=is_ok)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("stored_dir", type=Path)
    parser.add_argument("e5a_dir", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    results = []
    try:
        for arm in ARMS:
            stored = _rows(args.stored_dir / arm / ROW_FILE_STORED)
            new = _rows(args.e5a_dir / arm / ROW_FILE_SHADOW)
            if set(stored) != set(new):
                print(f"{arm}: keys differ", file=sys.stderr)
                return EXIT_INPUT
            results += [check_row(arm, stored[key], new[key]) for key in sorted(new)]
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        print(f"input: {exc!r}", file=sys.stderr)
        return EXIT_INPUT
    summary = {"rows": len(results), "sha_same": sum(r["sha_same"] for r in results),
               "ce_ok": sum(bool(r.get("ce_ok")) for r in results),
               "centred_ok": sum(bool(r.get("centred_ok")) for r in results),
               "all_ok": all(r["ok"] for r in results)}
    args.out.write_text(json.dumps({"summary": summary, "rows": results}, indent=1),
                        encoding="utf-8")
    for r in results:
        print(f"{r['arm']} {r['seed']} sha {'same' if r['sha_same'] else 'DIFF'} "
              f"cur {r.get('c_hat_tL_current_mm'):.3f} ce {r.get('ce_stored_mm')} "
              f"shadow {r.get('c_hat_tL_shadow_mm'):.3f} review {r.get('review_centred_mm')} "
              f"d_tL {r.get('diff_tL_mm'):.2f} d [{r.get('diff_min_mm'):.2f}, "
              f"{r.get('diff_max_mm'):.2f}] buf-trace {r.get('buffer_vs_trace_deg')}")
    print(json.dumps(summary))
    return EXIT_OK if summary["all_ok"] else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
