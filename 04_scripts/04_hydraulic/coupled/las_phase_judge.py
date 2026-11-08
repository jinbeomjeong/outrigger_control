"""Judge aid of the LAS-b phase diagnosis D-b (``las_phase_diag_plan.md`` 1.3 and 3).

Reads the D-b lines of ``las_phase_diag.py`` and computes, per key and grid centre c:
  R_c = max_{j<=3} F_RL - min_{j<=3} F_RL,  M_c = mean_{j<=3} F_RL,  P_c = |F_RL(4) - F_RL(0)|
and the plan 3 conditions:
  P1  some key / centre has R_c >= 1.0 kN
  P2  every key / centre has P_c <= max(0.3 kN, 0.25 R_c)
  P3  inside each key / centre at most one exception among the ordered pairs (below)
  P4  per key, max_c M_c - min_c M_c <= max_c R_c
  speed  every R_c < 0.5 kN, both keys M_1.0 > M_0.94 > M_nom (or both the reverse) and
         |M_1.0 - M_nom| >= 1.0 kN on both keys
  mixed  P1, P2, P3, and per key M_c strictly monotone with |M_1.0 - M_nom| >= max_c R_c
Verdict, in this order: anchors failed or a point missing / excluded -> ``undecidable``;
P1 .. P4 -> ``phase``; mixed -> ``mixed``; speed -> ``speed``; else ``undecidable``. Every
condition is reported as well (``phase`` and ``mixed`` can both hold at the equality edge).

P3 reading (this tool's; control-expert recomputes independently): a pair (a, b) of the five
lines (j = 0 .. 4) predicts "a lower" when a has fewer active periods and a start rho not
smaller, or the same or fewer active periods and a larger start rho. A pair whose two signs
disagree (fewer active periods but a smaller rho), or with equal values, or without a start
rho predicts nothing and is counted as ``unordered``. An exception is a predicting pair with
F_RL(a) >= F_RL(b).

Anchors (plan 1.3): A-1 centre 1.0, j 0 = the stored L (b0 act) hash of ``las_T1.jsonl``,
A-2 centre s_nom, j 0 = the stored LF hash of ``fb_F2.jsonl`` (the values below were read from
those files on 2026-11-08).
"""
from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

KEY_VB = "D1|H-R-A|rigid+J1@FR|T|diag-op|K3|VB|e0.002"
KEY_V0 = "D1|H-R-A|rigid+J1@FR|T|diag-op|K3|V0|e0.002"
KEYS = (KEY_VB, KEY_V0)
CENTRES = ("1", "0.94", "nom")
PHASE_STEPS = (0, 1, 2, 3)
PERIODICITY_STEP = 4
ANCHORS = {
    "A-1": {"centre": "1", "j": 0, "source": "las_T1.jsonl b0 act (L)", "hashes": {
        KEY_VB: "eec974b66af2b06063eaf146fc7098eaf968bb017d5567d14fbfe4fa72b5ab15",
        KEY_V0: "52547a6e145e8783e07b310435ef5c2b11fd0012780755cb7b40cb61e8b12507"}},
    "A-2": {"centre": "nom", "j": 0, "source": "fb_F2.jsonl LF", "hashes": {
        KEY_VB: "c72e663e16cf5aec24199f3fe12ff7ed272f18ebde30fc109e710f084947a862",
        KEY_V0: "c190903359aa8dc18316f2cbaf152da914cefc2ca42a150fe25b8d65510dfff0"}},
}
P1_RANGE_KN = 1.0
P2_FLOOR_KN = 0.3
P2_FRACTION = 0.25
P3_MAX_EXCEPTIONS = 1
SPEED_RANGE_KN = 0.5
SPEED_CHANGE_KN = 1.0
VERDICT_PHASE = "phase"
VERDICT_SPEED = "speed"
VERDICT_MIXED = "mixed"
VERDICT_UNDECIDABLE = "undecidable"


def read_lines(path: Path) -> list[dict]:
    """The JSON lines of a D-b file.

    Raises:
        OSError: The file cannot be read.
        ValueError: A line is not JSON.
    """
    return [json.loads(text) for text in path.read_text(encoding="utf-8").splitlines()
            if text.strip()]


def point_of(line: dict) -> dict | None:
    """The values plan 2 records for a D-b line (None for an error or non-grid line)."""
    if "error" in line:
        return None
    diag = line.get("diag") or {}
    budget = diag.get("touch_budget")
    if budget is None:
        return None
    summary = diag.get("summary") or {}
    return {"key": diag["key"], "centre": budget["centre"], "j": budget["j"],
            "s": budget["s"], "hash": line["commands_sha256"],
            "excluded": bool(budget["excluded"]),
            "level_budget_periods": budget["level_budget_periods"],
            "F_RL_kN": summary.get("F_RL_kN"), "active": summary.get("las_active_periods"),
            "rho": summary.get("las_start_rho"), "rho_prev": summary.get("las_start_rho_prev"),
            "start_period": summary.get("las_start_period"),
            "end_reason": summary.get("las_end_reason"),
            "t_touch_end_s": summary.get("t_touch_end_s"), "t_lift_s": summary.get("t_lift_s"),
            "gates_false_before_start": summary.get("gates_false_before_start"),
            "gate_consistent": summary.get("gate_consistent")}


def setting_of(key: str) -> str:
    """``VB`` / ``V0`` of a G-3 key (Markdown cells cannot hold the key's ``|``)."""
    return "VB" if key == KEY_VB else "V0"


def check_anchors(points: dict[tuple[str, str, int], dict]) -> dict:
    """Plan 1.3: every anchor point's hash against the stored hash (both keys)."""
    out = {}
    for name, anchor in ANCHORS.items():
        for key, expected in anchor["hashes"].items():
            point = points.get((key, anchor["centre"], anchor["j"]))
            got = None if point is None else point["hash"]
            out[f"{name} {setting_of(key)}"] = {"key": key, "source": anchor["source"],
                                                "expected": expected, "got": got,
                                                "pass": got == expected}
    return out


def predicts_lower(a: dict, b: dict) -> bool | None:
    """P3: True = a predicted lower than b, False = b lower than a, None = unordered."""
    if a["rho"] is None or b["rho"] is None or a["active"] is None or b["active"] is None:
        return None
    a_lower = ((a["active"] < b["active"] and a["rho"] >= b["rho"])
               or (a["active"] <= b["active"] and a["rho"] > b["rho"]))
    b_lower = ((b["active"] < a["active"] and b["rho"] >= a["rho"])
               or (b["active"] <= a["active"] and b["rho"] > a["rho"]))
    if a_lower == b_lower:
        return None
    return a_lower


def order_exceptions(line_points: list[dict]) -> dict:
    """P3 counts of one key / centre (all pairs of its lines)."""
    exceptions = unordered = predicting = 0
    for a, b in itertools.combinations(line_points, 2):
        lower = predicts_lower(a, b)
        if lower is None:
            unordered += 1
            continue
        predicting += 1
        low, high = (a, b) if lower else (b, a)
        if low["F_RL_kN"] >= high["F_RL_kN"]:
            exceptions += 1
    return {"exceptions": exceptions, "predicting_pairs": predicting,
            "unordered_pairs": unordered}


def centre_measures(by_step: dict[int, dict]) -> dict:
    """R_c, M_c, P_c and the P3 counts of one key / centre (all five steps present)."""
    phase_values = [by_step[j]["F_RL_kN"] for j in PHASE_STEPS]
    range_kN = max(phase_values) - min(phase_values)
    periodicity_kN = abs(by_step[PERIODICITY_STEP]["F_RL_kN"] - by_step[0]["F_RL_kN"])
    return {"R_c": range_kN, "M_c": sum(phase_values) / len(phase_values),
            "P_c": periodicity_kN,
            "P2_ok": periodicity_kN <= max(P2_FLOOR_KN, P2_FRACTION * range_kN),
            **order_exceptions([by_step[j] for j in sorted(by_step)])}


def _monotone_direction(values: list[float]) -> int:
    """+1 strictly increasing, -1 strictly decreasing, 0 otherwise."""
    pairs = list(itertools.pairwise(values))
    if all(b > a for a, b in pairs):
        return 1
    if all(b < a for a, b in pairs):
        return -1
    return 0


def key_conditions(measures: dict[str, dict]) -> dict:
    """Per key: P4, the M_c direction over the centres (1.0, 0.94, nom) and the change."""
    means = [measures[centre]["M_c"] for centre in CENTRES]
    largest_range = max(measures[centre]["R_c"] for centre in CENTRES)
    change = abs(means[0] - means[-1])
    return {"M_spread": max(means) - min(means), "max_R_c": largest_range,
            "P4_ok": max(means) - min(means) <= largest_range,
            "direction": _monotone_direction(means), "M_change": change}


def _grid_points(lines: list[dict]) -> tuple[dict, list[str]]:
    points = {}
    for line in lines:
        point = point_of(line)
        if point is not None:
            points[(point["key"], point["centre"], point["j"])] = point
    missing = [f"{key} c{centre} j{j}" for key in KEYS for centre in CENTRES
               for j in (*PHASE_STEPS, PERIODICITY_STEP)
               if (key, centre, j) not in points
               or points[(key, centre, j)]["F_RL_kN"] is None]
    return points, missing


def _verdict(flags: dict, anchors_pass: bool, is_complete: bool) -> str:
    if not anchors_pass or not is_complete:
        return VERDICT_UNDECIDABLE
    if flags["P1"] and flags["P2"] and flags["P3"] and flags["P4"]:
        return VERDICT_PHASE
    if flags["mixed"]:
        return VERDICT_MIXED
    if flags["speed"]:
        return VERDICT_SPEED
    return VERDICT_UNDECIDABLE


def _flags(measures: dict, keys: dict) -> dict:
    all_centres = [measures[key][centre] for key in KEYS for centre in CENTRES]
    directions = {keys[key]["direction"] for key in KEYS}
    is_p1 = any(m["R_c"] >= P1_RANGE_KN for m in all_centres)
    is_p2 = all(m["P2_ok"] for m in all_centres)
    is_p3 = all(m["exceptions"] <= P3_MAX_EXCEPTIONS for m in all_centres)
    is_p4 = all(keys[key]["P4_ok"] for key in KEYS)
    is_speed = (all(m["R_c"] < SPEED_RANGE_KN for m in all_centres)
                and len(directions) == 1 and 0 not in directions
                and all(keys[key]["M_change"] >= SPEED_CHANGE_KN for key in KEYS))
    is_mixed = (is_p1 and is_p2 and is_p3
                and all(keys[key]["direction"] != 0
                        and keys[key]["M_change"] >= keys[key]["max_R_c"] for key in KEYS))
    return {"P1": is_p1, "P2": is_p2, "P3": is_p3, "P4": is_p4, "speed": is_speed,
            "mixed": is_mixed}


def judge(lines: list[dict]) -> dict:
    """Anchors, measures, conditions and verdict of a D-b file (module docstring)."""
    points, missing = _grid_points(lines)
    anchors = check_anchors(points)
    anchors_pass = all(entry["pass"] for entry in anchors.values())
    excluded = sorted(f"{p['key']} c{p['centre']} j{p['j']}" for p in points.values()
                      if p["excluded"])
    out = {"anchors": anchors, "anchors_pass": anchors_pass, "missing": missing,
           "excluded": excluded, "points": sorted(points.values(),
                                                  key=lambda p: (p["key"], p["centre"], p["j"])),
           "errors": sum(1 for line in lines if "error" in line)}
    is_complete = not missing and not excluded
    if not is_complete:
        return {**out, "measures": None, "keys": None, "flags": None,
                "verdict": VERDICT_UNDECIDABLE}
    measures = {key: {centre: centre_measures({j: points[(key, centre, j)]
                                               for j in (*PHASE_STEPS, PERIODICITY_STEP)})
                      for centre in CENTRES} for key in KEYS}
    keys = {key: key_conditions(measures[key]) for key in KEYS}
    flags = _flags(measures, keys)
    return {**out, "measures": measures, "keys": keys, "flags": flags,
            "verdict": _verdict(flags, anchors_pass, is_complete)}


def _number(value, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "-"
    return f"{value:.{digits}f}" if isinstance(value, float) else str(value)


def report_markdown(result: dict, source: Path) -> str:
    """A Markdown summary of :func:`judge` (record; control-expert recomputes)."""
    lines = [f"# LAS-b phase diagnosis D-b: judge aid ({source.name})", "",
             f"- verdict: **{result['verdict']}** (anchors pass: {result['anchors_pass']}, "
             f"errors {result['errors']}, missing {len(result['missing'])}, "
             f"excluded {len(result['excluded'])})", "", "## Anchors (plan 1.3)", "",
             "| anchor | source | expected | got | pass |", "|---|---|---|---|---|"]
    for name, entry in result["anchors"].items():
        lines.append(f"| `{name}` | {entry['source']} | {entry['expected'][:12]} | "
                     f"{(entry['got'] or '-')[:12]} | {entry['pass']} |")
    lines += ["", "## Points (plan 2)", "",
              "| key | c | j | s | F_RL kN | TOUCH end s | lift s | start +k | rho | rho_prev "
              "| active | end | false before start | LEVEL budget | gate ok |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in result["points"]:
        setting = setting_of(p["key"])
        lines.append(
            f"| {setting} | {p['centre']} | {p['j']} | {_number(p['s'], 6)} | "
            f"{_number(p['F_RL_kN'])} | {_number(p['t_touch_end_s'], 2)} | "
            f"{_number(p['t_lift_s'], 3)} | {p['start_period']} | {_number(p['rho'], 4)} | "
            f"{_number(p['rho_prev'], 4)} | {p['active']} | {p['end_reason']} | "
            f"{','.join(p['gates_false_before_start'] or []) or '-'} | "
            f"{p['level_budget_periods']} | {p['gate_consistent']} |")
    if result["missing"] or result["excluded"]:
        lines += ["", f"- missing: {result['missing']}", f"- excluded: {result['excluded']}"]
    if result["measures"] is not None:
        lines += ["", "## Measures (plan 3)", "",
                  "| key | c | R_c | M_c | P_c | P2 | P3 exceptions | predicting | unordered |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for key, by_centre in result["measures"].items():
            setting = setting_of(key)
            for centre, m in by_centre.items():
                lines.append(f"| {setting} | {centre} | {_number(m['R_c'])} | "
                             f"{_number(m['M_c'])} | {_number(m['P_c'])} | {m['P2_ok']} | "
                             f"{m['exceptions']} | {m['predicting_pairs']} | "
                             f"{m['unordered_pairs']} |")
        for key, k in result["keys"].items():
            setting = setting_of(key)
            lines.append(f"- {setting}: M spread {_number(k['M_spread'])}, max R_c "
                         f"{_number(k['max_R_c'])}, P4 {k['P4_ok']}, direction "
                         f"{k['direction']}, |M_1.0 - M_nom| {_number(k['M_change'])}")
        lines.append(f"- conditions: {result['flags']}")
    return "\n".join(lines) + "\n"
