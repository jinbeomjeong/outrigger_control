"""Judge aid of the LAS-b phase diagnosis D-b (``las_phase_diag_plan.md`` 1.3 / 3 as read by
``las_phase_diag_plan_rev1.md``; rev1 wins where they differ).

Per key and grid centre c (``cell``):
  R_c = max_{j<=3} F_RL - min_{j<=3} F_RL,  M_c = mean_{j<=3} F_RL,  P_c = |F_RL(4) - F_RL(0)|
Conditions:
  P1  some cell has R_c >= 1.0 kN
  P2  every cell has P_c <= max(0.3 kN, 0.25 R_c)
  P3  (rev1 1) evaluated only in the cells with R_c >= 1.0 kN, over the 10 pairs of j = 0 .. 4.
      a is predicted lower than b when active_a <= active_b and rho_a >= rho_b with one of the
      two strict (dominance); crossed or equal pairs predict nothing. A line without a LAS
      start (rho or active None) takes part in no pair. A contradiction is a predicting pair
      whose predicted-lower line has an F_RL more than 0.2 kN above the other's.
      Per evaluated cell: not-started lines <= 1 and predicting pairs >= 6 (else P3 is
      ``undetermined``) and contradictions <= 1 (else ``fail``). P3 ``pass`` needs at least
      one evaluated cell, all of them passing; no evaluated cell = ``not_evaluated``.
  P4  (rev1 2) per key, max_c M_c - min_c M_c <= max_c R_c
  mixed  (rev1 2) P1, P2, P3 pass and per key M_c strictly monotone over (1.0, 0.94, nom) with
         |M_1.0 - M_nom| > max_c R_c (strict)
  speed  (rev1 3) per key: every R_c < 0.5 kN, M_c strictly monotone, |M_1.0 - M_nom| >= 1.0
         kN; and both keys change in the same direction
Verdict order (rev1 5): exclusion checks (rev1 4: an error line, fewer than 30 grid lines,
``gate_consistent`` False, LEVEL budget periods != 0, an anchor mismatch) -> ``undecidable_tool``;
P3 undetermined -> ``undecidable``; phase (P1 .. P4); mixed (when phase and mixed both hold,
mixed); speed; else ``undecidable``.

Anchors (plan 1.3): A-1 centre 1.0, j 0 = the stored L (b0 act) hash of ``las_T1.jsonl``,
A-2 centre s_nom, j 0 = the stored LF hash of ``fb_F2.jsonl`` (values read from those files on
2026-11-08).
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
ALL_STEPS = (*PHASE_STEPS, PERIODICITY_STEP)
GRID_LINES = len(KEYS) * len(CENTRES) * len(ALL_STEPS)
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
P3_MAX_NOT_STARTED = 1
P3_MIN_PREDICTING_PAIRS = 6
P3_MAX_CONTRADICTIONS = 1
P3_CONTRADICTION_MARGIN_KN = 0.2
SPEED_RANGE_KN = 0.5
SPEED_CHANGE_KN = 1.0
P3_PASS = "pass"
P3_FAIL = "fail"
P3_UNDETERMINED = "undetermined"
P3_NOT_EVALUATED = "not_evaluated"
VERDICT_PHASE = "phase"
VERDICT_SPEED = "speed"
VERDICT_MIXED = "mixed"
VERDICT_UNDECIDABLE = "undecidable"
VERDICT_UNDECIDABLE_TOOL = "undecidable_tool"


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


# ------------------------------------------------------------------------------- exclusion
def exclusion_problems(lines: list[dict], points: dict, anchors: dict) -> list[str]:
    """Rev1 4: any of these makes the whole judgement ``undecidable_tool``."""
    problems = [f"error line: {(line.get('diag') or {}).get('key')} "
                f"{(line.get('diag') or {}).get('candidate')}"
                for line in lines if "error" in line]
    missing = [f"{setting_of(key)} c{centre} j{j}" for key in KEYS for centre in CENTRES
               for j in ALL_STEPS if (key, centre, j) not in points
               or points[(key, centre, j)]["F_RL_kN"] is None]
    if missing:
        problems.append(f"{GRID_LINES - len(missing)} of {GRID_LINES} grid lines: "
                        f"missing {missing}")
    for (key, centre, j), point in sorted(points.items()):
        label = f"{setting_of(key)} c{centre} j{j}"
        if point["gate_consistent"] is False:
            problems.append(f"{label}: gate_consistent False")
        if point["level_budget_periods"]:
            problems.append(f"{label}: LEVEL budget periods {point['level_budget_periods']}")
    problems += [f"anchor {name} mismatch" for name, entry in anchors.items()
                 if not entry["pass"]]
    return problems


# ------------------------------------------------------------------------------- P3
def has_las_start(point: dict) -> bool:
    return point["rho"] is not None and point["active"] is not None


def predicts_lower(a: dict, b: dict) -> bool:
    """Rev1 1 dominance: active_a <= active_b and rho_a >= rho_b, one of them strict."""
    is_weakly_dominant = a["active"] <= b["active"] and a["rho"] >= b["rho"]
    is_strict = a["active"] < b["active"] or a["rho"] > b["rho"]
    return is_weakly_dominant and is_strict


def p3_cell(line_points: list[dict]) -> dict:
    """Rev1 1 counts of one cell (the lines of j = 0 .. 4) and its P3 status."""
    started = [point for point in line_points if has_las_start(point)]
    not_started = len(line_points) - len(started)
    predicting = contradictions = 0
    for a, b in itertools.combinations(started, 2):
        if predicts_lower(a, b):
            low, high = a, b
        elif predicts_lower(b, a):
            low, high = b, a
        else:
            continue
        predicting += 1
        if low["F_RL_kN"] > high["F_RL_kN"] + P3_CONTRADICTION_MARGIN_KN:
            contradictions += 1
    if not_started > P3_MAX_NOT_STARTED or predicting < P3_MIN_PREDICTING_PAIRS:
        status = P3_UNDETERMINED
    elif contradictions > P3_MAX_CONTRADICTIONS:
        status = P3_FAIL
    else:
        status = P3_PASS
    return {"not_started": not_started, "predicting_pairs": predicting,
            "contradictions": contradictions, "status": status}


def p3_overall(measures: dict) -> str:
    """P3 over the evaluated cells (R_c >= 1.0 kN): undetermined > fail > pass."""
    statuses = [cell["p3"]["status"] for by_centre in measures.values()
                for cell in by_centre.values() if cell["p3_evaluated"]]
    if not statuses:
        return P3_NOT_EVALUATED
    if P3_UNDETERMINED in statuses:
        return P3_UNDETERMINED
    return P3_FAIL if P3_FAIL in statuses else P3_PASS


# ------------------------------------------------------------------------------- measures
def centre_measures(by_step: dict[int, dict]) -> dict:
    """R_c, M_c, P_c, P2 and the rev1 P3 counts of one cell (all five steps present)."""
    phase_values = [by_step[j]["F_RL_kN"] for j in PHASE_STEPS]
    range_kN = max(phase_values) - min(phase_values)
    periodicity_kN = abs(by_step[PERIODICITY_STEP]["F_RL_kN"] - by_step[0]["F_RL_kN"])
    return {"R_c": range_kN, "M_c": sum(phase_values) / len(phase_values),
            "P_c": periodicity_kN,
            "P2_ok": periodicity_kN <= max(P2_FLOOR_KN, P2_FRACTION * range_kN),
            "p3_evaluated": range_kN >= P1_RANGE_KN,
            "p3": p3_cell([by_step[j] for j in ALL_STEPS])}


def _monotone_direction(values: list[float]) -> int:
    """+1 strictly increasing, -1 strictly decreasing, 0 otherwise."""
    pairs = list(itertools.pairwise(values))
    if all(b > a for a, b in pairs):
        return 1
    if all(b < a for a, b in pairs):
        return -1
    return 0


def key_conditions(measures: dict[str, dict]) -> dict:
    """Per key: P4, the M_c direction over (1.0, 0.94, nom), the change and the speed part."""
    means = [measures[centre]["M_c"] for centre in CENTRES]
    ranges = [measures[centre]["R_c"] for centre in CENTRES]
    largest_range = max(ranges)
    spread = max(means) - min(means)
    direction = _monotone_direction(means)
    change = abs(means[0] - means[-1])
    return {"M_spread": spread, "max_R_c": largest_range, "P4_ok": spread <= largest_range,
            "direction": direction, "M_change": change,
            "mixed_ok": direction != 0 and change > largest_range,
            "speed_ok": all(value < SPEED_RANGE_KN for value in ranges) and direction != 0
            and change >= SPEED_CHANGE_KN}


def conditions(measures: dict, keys: dict) -> dict:
    """P1 .. P4, mixed and speed of a complete grid (module docstring)."""
    cells = [measures[key][centre] for key in KEYS for centre in CENTRES]
    p3 = p3_overall(measures)
    is_p123 = (any(cell["R_c"] >= P1_RANGE_KN for cell in cells)
               and all(cell["P2_ok"] for cell in cells) and p3 == P3_PASS)
    directions = {keys[key]["direction"] for key in KEYS}
    return {"P1": any(cell["R_c"] >= P1_RANGE_KN for cell in cells),
            "P2": all(cell["P2_ok"] for cell in cells), "P3": p3,
            "P4": all(keys[key]["P4_ok"] for key in KEYS),
            "phase": is_p123 and all(keys[key]["P4_ok"] for key in KEYS),
            "mixed": is_p123 and all(keys[key]["mixed_ok"] for key in KEYS),
            "speed": all(keys[key]["speed_ok"] for key in KEYS) and len(directions) == 1}


def verdict_of(flags: dict) -> str:
    """Rev1 5 order after the exclusion checks."""
    if flags["P3"] == P3_UNDETERMINED:
        return VERDICT_UNDECIDABLE
    if flags["mixed"]:  # rev1 2: mixed when phase and mixed both hold
        return VERDICT_MIXED
    if flags["phase"]:
        return VERDICT_PHASE
    if flags["speed"]:
        return VERDICT_SPEED
    return VERDICT_UNDECIDABLE


def _grid_points(lines: list[dict]) -> dict:
    points = {}
    for line in lines:
        point = point_of(line)
        if point is not None:
            points[(point["key"], point["centre"], point["j"])] = point
    return points


def judge(lines: list[dict]) -> dict:
    """Exclusion checks, anchors, measures, conditions and verdict of a D-b file."""
    points = _grid_points(lines)
    anchors = check_anchors(points)
    problems = exclusion_problems(lines, points, anchors)
    out = {"anchors": anchors, "anchors_pass": all(entry["pass"] for entry in anchors.values()),
           "exclusion_problems": problems,
           "points": sorted(points.values(), key=lambda p: (p["key"], p["centre"], p["j"])),
           "errors": sum(1 for line in lines if "error" in line)}
    if problems:
        return {**out, "measures": None, "keys": None, "flags": None,
                "verdict": VERDICT_UNDECIDABLE_TOOL}
    measures = {key: {centre: centre_measures({j: points[(key, centre, j)] for j in ALL_STEPS})
                      for centre in CENTRES} for key in KEYS}
    keys = {key: key_conditions(measures[key]) for key in KEYS}
    flags = conditions(measures, keys)
    return {**out, "measures": measures, "keys": keys, "flags": flags,
            "verdict": verdict_of(flags)}


# ------------------------------------------------------------------------------- report
def _number(value, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "-"
    return f"{value:.{digits}f}" if isinstance(value, float) else str(value)


def _point_rows(points: list[dict]) -> list[str]:
    rows = ["| key | c | j | s | F_RL kN | TOUCH end s | lift s | start +k | rho | rho_prev "
            "| active | end | false before start | LEVEL budget | gate ok |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in points:
        rows.append(
            f"| {setting_of(p['key'])} | {p['centre']} | {p['j']} | {_number(p['s'], 6)} | "
            f"{_number(p['F_RL_kN'])} | {_number(p['t_touch_end_s'], 2)} | "
            f"{_number(p['t_lift_s'], 3)} | {p['start_period']} | {_number(p['rho'], 4)} | "
            f"{_number(p['rho_prev'], 4)} | {p['active']} | {p['end_reason']} | "
            f"{','.join(p['gates_false_before_start'] or []) or '-'} | "
            f"{p['level_budget_periods']} | {p['gate_consistent']} |")
    return rows


def _measure_rows(result: dict) -> list[str]:
    rows = ["| key | c | R_c | M_c | P_c | P2 | P3 evaluated | not started | predicting pairs "
            "| contradictions | P3 cell |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for key, by_centre in result["measures"].items():
        for centre, m in by_centre.items():
            p3 = m["p3"]
            rows.append(f"| {setting_of(key)} | {centre} | {_number(m['R_c'])} | "
                        f"{_number(m['M_c'])} | {_number(m['P_c'])} | {m['P2_ok']} | "
                        f"{m['p3_evaluated']} | {p3['not_started']} | "
                        f"{p3['predicting_pairs']} | {p3['contradictions']} | {p3['status']} |")
    for key, k in result["keys"].items():
        rows.append(f"- {setting_of(key)}: M spread {_number(k['M_spread'])}, max R_c "
                    f"{_number(k['max_R_c'])}, P4 {k['P4_ok']}, direction {k['direction']}, "
                    f"|M_1.0 - M_nom| {_number(k['M_change'])}, mixed part {k['mixed_ok']}, "
                    f"speed part {k['speed_ok']}")
    rows.append(f"- conditions: {result['flags']}")
    return rows


def report_markdown(result: dict, source: Path) -> str:
    """A Markdown summary of :func:`judge` (record; control-expert recomputes)."""
    lines = [f"# LAS-b phase diagnosis D-b: judge aid ({source.name})", "",
             f"- verdict: **{result['verdict']}** (anchors pass: {result['anchors_pass']}, "
             f"errors {result['errors']}, exclusion problems "
             f"{len(result['exclusion_problems'])})", "", "## Anchors (plan 1.3)", "",
             "| anchor | source | expected | got | pass |", "|---|---|---|---|---|"]
    for name, entry in result["anchors"].items():
        lines.append(f"| `{name}` | {entry['source']} | {entry['expected'][:12]} | "
                     f"{(entry['got'] or '-')[:12]} | {entry['pass']} |")
    if result["exclusion_problems"]:
        lines += ["", "## Exclusion checks (rev1 4)", ""]
        lines += [f"- {problem}" for problem in result["exclusion_problems"]]
    lines += ["", "## Points (plan 2)", "", *_point_rows(result["points"])]
    if result["measures"] is not None:
        lines += ["", "## Measures (plan 3, rev1 1 .. 3)", "", *_measure_rows(result)]
    return "\n".join(lines) + "\n"
