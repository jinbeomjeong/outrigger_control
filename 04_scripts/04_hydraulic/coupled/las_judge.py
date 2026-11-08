"""Judge of the LAS-b targeted runs (sealed ``las_targeted_rules.md`` 3 and 5).

Criteria per variant against the stored ``v5/d1.jsonl`` line of the same key (rules 3.1):
  C1  T-1: all 8 keys ``d1.verdict`` pass and ``F_judged_min_N`` >= F_min + 1,000 N
  C2  no baseline pass -> fail, no baseline allowed_stop -> fail; a baseline fail keeps its
      ``fail_items`` (the new set is a subset of the stored one)
  C3  no ``FAULT*`` event name (``event_names``) that the baseline line does not have
  C4  item ``G6-2_loc`` pass where the baseline passes it; T-1 also tabulates the judge's
      LOC - t_off (``las.loc_minus_t_off_s``)
  C5  keys where the rule started (``las.start_t_s``): ``t_ready_s`` + <= 5.0 s and
      ``stroke_max_m`` + <= 0.001 m (a READY the baseline has and the run lost fails)
  C6  T-2: the H-R-0 keys keep the baseline ``commands_sha256`` (rule silent there)
Ranking (rules 3.2): T-1 candidates = LAS-b variants with C1 .. C5; first the largest worst-key
``F_judged_min_N`` (variants within 500 N of it are tied), inside the tie the smaller largest
LOC - t_off, then the smaller largest READY increase, then closeness to b0
(b0 > b-T20 > b-T10 > b-a7 > b-a5). The runner-up for T-2' is the next variant of that order
(tie members first, then the others by worst-key F).
Stops (rules 5): H-1 T-0 hash differs, H-2 error lines (retry the key once), H-3 no T-1
candidate (LAS-a C1 / C4 / C5 reported with it), H-4 the variant fails T-2 (or C6).

Usage (python-dev or dynamics-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/las_judge.py T-0|T-1|T-2 <jsonl>
      [--baseline <d1.jsonl>] [--t1 <las_T1.jsonl>] [--candidate NAME] [--out <md>]
The last stdout line is JSON. Exit codes: 0 judged without a stop, 1 a stop (H-1 .. H-4),
2 input error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASELINE_PATH = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "d1.jsonl"

F_MIN_N = 9414.589
"""Rules header: F_min [N] (cylinder net force)."""
C1_MARGIN_N = 1000.0
TIE_WINDOW_N = 500.0
READY_INCREASE_LIMIT_S = 5.0
STROKE_INCREASE_LIMIT_M = 0.001
G62_ITEM = "G6-2_loc"
RIGID_GROUP = "H-R-0"
LASB_VARIANTS = ("b0", "b-a5", "b-a7", "b-T10", "b-T20")
CLOSENESS_TO_B0 = ("b0", "b-T20", "b-T10", "b-a7", "b-a5")
LASA = "LASa"
CURRENT = "current"
T1_KEY_COUNT = 8
T0_KEY_COUNT = 2


# ------------------------------------------------------------------------------- input
def read_lines(path: Path) -> list[dict]:
    return [json.loads(text) for text in path.read_text(encoding="utf-8").splitlines() if text]


def load_baseline(path: Path) -> dict[str, dict]:
    out = {}
    for record in read_lines(path):
        if "d1" in record:
            out[record["d1"]["key"]] = record
    return out


def line_key(record: dict) -> str:
    las = record.get("las") or {}
    if las.get("key"):
        return las["key"]
    job = record["job"]
    return f"{job['d1']['key']}|{job['setting']}|e{float(job['eps']):g}"


def by_candidate(lines: list[dict]) -> dict[str, dict[str, dict]]:
    """candidate -> key -> line (the last error-free line wins; errors kept apart)."""
    out: dict[str, dict[str, dict]] = {}
    for record in lines:
        if "error" in record:
            continue
        name = (record.get("las") or {}).get("candidate", "?")
        out.setdefault(name, {})[line_key(record)] = record
    return out


def error_keys(lines: list[dict]) -> list[str]:
    """H-2: keys with an error line and no later good line of the same candidate."""
    good = {(line_key(r), (r.get("las") or {}).get("candidate")) for r in lines
            if "error" not in r}
    failed = []
    for record in lines:
        if "error" not in record:
            continue
        pair = (line_key(record), (record.get("las") or {}).get("candidate"))
        if pair not in good:
            failed.append(f"{pair[1]} {pair[0]}")
    return sorted(set(failed))


# ------------------------------------------------------------------------------- criteria
def _fault_names(record: dict) -> set[str]:
    return {name for name in (record.get("event_names") or {}) if name.startswith("FAULT")}


def c2_problem(new: dict, base: dict) -> str | None:
    verdict, stored = new["d1"]["verdict"], base["d1"]["verdict"]
    if stored in ("pass", "allowed_stop") and verdict == "fail":
        return f"{stored} -> fail {new['d1']['fail_items']}"
    if stored == "fail":
        extra = set(new["d1"]["fail_items"]) - set(base["d1"]["fail_items"])
        if extra:
            return f"new fail items {sorted(extra)}"
    return None


def c3_problem(new: dict, base: dict) -> str | None:
    extra = _fault_names(new) - _fault_names(base)
    return f"new FAULT {sorted(extra)}" if extra else None


def c4_problem(new: dict, base: dict) -> str | None:
    if base["d1"]["items"].get(G62_ITEM) is not True:
        return None
    if new["d1"]["items"].get(G62_ITEM) is True:
        return None
    return f"{G62_ITEM} pass -> {new['d1']['items'].get(G62_ITEM)}"


def increase(new_value, base_value) -> float | None:
    if new_value is None or base_value is None:
        return None
    return float(new_value) - float(base_value)


def c5_problem(new: dict, base: dict) -> str | None:
    if (new.get("las") or {}).get("start_t_s") is None:
        return None
    ready_new, ready_base = new["d1"]["t_ready_s"], base["d1"]["t_ready_s"]
    if ready_new is None and ready_base is not None:
        return "READY lost"
    ready_up = increase(ready_new, ready_base)
    stroke_up = increase(new["d1"]["stroke_max_m"], base["d1"]["stroke_max_m"])
    problems = []
    if ready_up is not None and ready_up > READY_INCREASE_LIMIT_S:
        problems.append(f"READY +{ready_up:.2f} s")
    if stroke_up is not None and stroke_up > STROKE_INCREASE_LIMIT_M:
        problems.append(f"stroke +{stroke_up * 1e3:.2f} mm")
    return "; ".join(problems) or None


def c6_problem(new: dict, base: dict) -> str | None:
    if new["d1"].get("group") != RIGID_GROUP:
        return None
    if new["commands_sha256"] == base["commands_sha256"]:
        return None
    return f"hash {new['commands_sha256'][:12]} != {base['commands_sha256'][:12]}"


KEYWISE = {"C2": c2_problem, "C3": c3_problem, "C4": c4_problem, "C5": c5_problem}


def c1_problems(lines: dict[str, dict]) -> dict[str, str]:
    out = {}
    for key, record in lines.items():
        d1 = record["d1"]
        f_value = d1["F_judged_min_N"]
        if d1["verdict"] != "pass" or f_value is None or f_value < F_MIN_N + C1_MARGIN_N:
            out[key] = f"{d1['verdict']} F {f_value}"
    return out


def keywise_problems(lines: dict[str, dict], baseline: dict[str, dict],
                     names: tuple[str, ...]) -> dict[str, dict[str, str]]:
    """criterion -> key -> problem, for the criteria ``names`` (C2 .. C6)."""
    out: dict[str, dict[str, str]] = {name: {} for name in names}
    checks = {**KEYWISE, "C6": c6_problem}
    for key, record in lines.items():
        base = baseline[key]
        for name in names:
            problem = checks[name](record, base)
            if problem is not None:
                out[name][key] = problem
    return out


def key_table(lines: dict[str, dict], baseline: dict[str, dict]) -> list[dict]:
    """Per key: verdict, F, LOC - t_off, READY / stroke increase, start and end of the rule."""
    rows = []
    for key in sorted(lines):
        record, base = lines[key], baseline[key]
        las = record.get("las") or {}
        rows.append({"key": key, "verdict": record["d1"]["verdict"],
                     "verdict_base": base["d1"]["verdict"],
                     "F_N": record["d1"]["F_judged_min_N"],
                     "F_base_N": base["d1"]["F_judged_min_N"],
                     "loc_minus_t_off_s": las.get("loc_minus_t_off_s"),
                     "ready_up_s": increase(record["d1"]["t_ready_s"], base["d1"]["t_ready_s"]),
                     "stroke_up_m": increase(record["d1"]["stroke_max_m"],
                                             base["d1"]["stroke_max_m"]),
                     "start_t_s": las.get("start_t_s"), "end_reason": las.get("end_reason"),
                     "hash_equal": record["commands_sha256"] == base["commands_sha256"]})
    return rows


def _max_or_none(values) -> float | None:
    finite = [float(v) for v in values if v is not None]
    return max(finite) if finite else None


def variant_summary(lines: dict[str, dict], baseline: dict[str, dict]) -> dict:
    """C1 .. C5 of one T-1 variant and the ranking numbers."""
    table = key_table(lines, baseline)
    problems = {"C1": c1_problems(lines),
                **keywise_problems(lines, baseline, ("C2", "C3", "C4", "C5"))}
    f_values = [row["F_N"] for row in table]
    return {"keys": len(lines), "criteria": {name: not found for name, found in problems.items()},
            "problems": problems,
            "worst_F_N": None if None in f_values or not f_values else min(f_values),
            "max_loc_minus_t_off_s": _max_or_none(row["loc_minus_t_off_s"] for row in table),
            "max_ready_up_s": _max_or_none(row["ready_up_s"] for row in table),
            "table": table}


# ------------------------------------------------------------------------------- ranking
def _tie_order(name: str, summary: dict) -> tuple:
    loc = summary["max_loc_minus_t_off_s"]
    ready = summary["max_ready_up_s"]
    return (float("inf") if loc is None else loc, float("inf") if ready is None else ready,
            CLOSENESS_TO_B0.index(name))


def rank_variants(summaries: dict[str, dict]) -> list[str]:
    """Rules 3.2 order of the variants that meet C1 .. C5 (first = selected)."""
    passing = {name: s for name, s in summaries.items()
               if name in LASB_VARIANTS and s["keys"] == T1_KEY_COUNT
               and all(s["criteria"].values())}
    if not passing:
        return []
    best_F = max(s["worst_F_N"] for s in passing.values())
    tied = [name for name, s in passing.items() if best_F - s["worst_F_N"] <= TIE_WINDOW_N]
    others = [name for name in passing if name not in tied]
    tied.sort(key=lambda name: _tie_order(name, passing[name]))
    others.sort(key=lambda name: (-passing[name]["worst_F_N"],
                                  *_tie_order(name, passing[name])))
    return tied + others


# ------------------------------------------------------------------------------- stages
def judge_t0(lines: list[dict], baseline: dict[str, dict]) -> dict:
    current = by_candidate(lines).get(CURRENT, {})
    rows = [{"key": key, "hash": record["commands_sha256"][:12],
             "hash_base": baseline[key]["commands_sha256"][:12],
             "equal": record["commands_sha256"] == baseline[key]["commands_sha256"]}
            for key, record in sorted(current.items())]
    is_ok = len(rows) == T0_KEY_COUNT and all(row["equal"] for row in rows)
    return {"stage": "T-0", "rows": rows, "stop": None if is_ok else "H-1",
            "reason": "T-0 hashes equal the baseline" if is_ok
            else f"H-1: {sum(not r['equal'] for r in rows)} of {len(rows)} hashes differ "
                 f"(2 expected)"}


def judge_t1(lines: list[dict], baseline: dict[str, dict]) -> dict:
    groups = by_candidate(lines)
    summaries = {name: variant_summary(group, baseline) for name, group in groups.items()
                 if name != CURRENT}
    ranking = rank_variants(summaries)
    out = {"stage": "T-1", "summaries": summaries, "ranking": ranking,
           "selected": ranking[0] if ranking else None,
           "runner_up": ranking[1] if len(ranking) > 1 else None}
    incomplete = [name for name in LASB_VARIANTS
                  if summaries.get(name, {}).get("keys") != T1_KEY_COUNT]
    if not ranking:
        lasa = summaries.get(LASA)
        out["stop"] = "H-3"
        out["reason"] = "H-3: no LAS-b variant meets C1 .. C5" + (
            f" (not all {T1_KEY_COUNT} keys run: {incomplete})" if incomplete else "")
        out["lasa"] = None if lasa is None else {
            name: lasa["criteria"].get(name) for name in ("C1", "C4", "C5")}
    else:
        out["stop"] = None
        out["reason"] = f"selected {ranking[0]} (rules 3.2)"
    if incomplete:
        out["incomplete_variants"] = incomplete
    return out


def judge_t2(lines: list[dict], baseline: dict[str, dict], t1_lines: list[dict] | None,
             candidate: str | None) -> dict:
    """C2 .. C6 of one variant on T-2 (and on its T-1 lines when given)."""
    groups = by_candidate(lines)
    name = candidate or (next(iter(groups)) if len(groups) == 1 else None)
    if name is None or name not in groups:
        raise ValueError(f"T-2 lines hold {sorted(groups)}; name one with --candidate")
    t2 = groups[name]
    problems = keywise_problems(t2, baseline, ("C2", "C3", "C4", "C5", "C6"))
    t1_problems = {}
    ranking = []
    if t1_lines is not None:
        t1 = by_candidate(t1_lines).get(name, {})
        t1_problems = keywise_problems(t1, baseline, ("C2", "C3", "C4", "C5"))
        t1_judgement = judge_t1(t1_lines, baseline)
        ranking = t1_judgement["ranking"]
    merged = {crit: {**problems.get(crit, {}), **t1_problems.get(crit, {})}
              for crit in ("C2", "C3", "C4", "C5", "C6")}
    failed = {crit: found for crit, found in merged.items() if found}
    rigid = [key for key, record in t2.items() if record["d1"].get("group") == RIGID_GROUP]
    started = sorted(key for key, record in t2.items()
                     if (record.get("las") or {}).get("start_t_s") is not None)
    is_adopted = not failed and len(t2) == 184
    out = {"stage": "T-2", "candidate": name, "keys": len(t2), "rigid_keys": len(rigid),
           "started_keys": started, "criteria": {crit: not merged[crit] for crit in merged},
           "failed_keys": failed, "adopted": name if is_adopted else None}
    if is_adopted:
        out.update(stop=None, reason=f"adopted {name}: C2 .. C6 met on T-2"
                   + (" and T-1" if t1_lines is not None else ""))
        return out
    only_non_c6 = bool(failed) and "C6" not in failed
    index = ranking.index(name) if name in ranking else -1
    runner_up = ranking[index + 1] if 0 <= index < len(ranking) - 1 else None
    out.update(stop="H-4", t2_prime_allowed=only_non_c6, runner_up=runner_up if only_non_c6
               else None,
               reason=("H-4: " + ", ".join(f"{crit} {len(keys)} keys"
                                          for crit, keys in failed.items())
                       if failed else f"H-4: {len(t2)} of 184 keys"))
    return out


# ------------------------------------------------------------------------------- report
def _fmt(value, scale: float = 1.0, digits: int = 3) -> str:
    return "-" if value is None else f"{value * scale:.{digits}f}"


def _cell(text: str) -> str:
    """A key inside a Markdown table cell (the key's ``|`` escaped, as in the sealed text)."""
    return text.replace("|", "\\|")


def report_lines(result: dict) -> list[str]:
    lines = [f"# LAS judge {result['stage']}", ""]
    if result["stage"] == "T-1":
        for name, summary in result["summaries"].items():
            marks = " ".join(f"{c}={'ok' if ok else 'NG'}" for c, ok in summary["criteria"].items())
            lines.append(f"## {name}: worst F {_fmt(summary['worst_F_N'], 1e-3)} kN, "
                         f"max LOC-t_off {_fmt(summary['max_loc_minus_t_off_s'], 1, 2)} s, "
                         f"max READY+ {_fmt(summary['max_ready_up_s'], 1, 2)} s; {marks}")
            lines.append("| key | verdict (base) | F kN (base) | LOC-t_off s | READY+ s | "
                         "stroke+ mm | start s | end |")
            lines.append("|---|---|---|---|---|---|---|---|")
            for row in summary["table"]:
                lines.append(
                    f"| `{_cell(row['key'])}` | {row['verdict']} ({row['verdict_base']}) | "
                    f"{_fmt(row['F_N'], 1e-3)} ({_fmt(row['F_base_N'], 1e-3)}) | "
                    f"{_fmt(row['loc_minus_t_off_s'], 1, 2)} | {_fmt(row['ready_up_s'], 1, 2)} | "
                    f"{_fmt(row['stroke_up_m'], 1e3, 2)} | {_fmt(row['start_t_s'], 1, 1)} | "
                    f"{row['end_reason'] or '-'} |")
            for crit, found in summary["problems"].items():
                for key, problem in found.items():
                    lines.append(f"- {crit} `{key}`: {problem}")
            lines.append("")
        lines.append(f"ranking: {result['ranking']}")
    elif result["stage"] == "T-2":
        lines.append(f"candidate {result['candidate']}: {result['keys']} keys, rule started on "
                     f"{len(result['started_keys'])}")
        for crit, found in result["failed_keys"].items():
            for key, problem in found.items():
                lines.append(f"- {crit} `{key}`: {problem}")
    else:
        for row in result["rows"]:
            lines.append(f"- `{row['key']}` {row['hash']} vs {row['hash_base']}: "
                         f"{'equal' if row['equal'] else 'DIFFERENT'}")
    if result.get("errors"):
        lines.append(f"H-2 error lines (retry once): {result['errors']}")
    lines.append(f"result: {result['reason']}")
    return lines


def final_json(result: dict) -> dict:
    keep = ("stage", "selected", "runner_up", "ranking", "candidate", "adopted", "stop",
            "reason", "errors", "t2_prime_allowed", "lasa", "incomplete_variants")
    out = {key: result[key] for key in keep if key in result}
    if "criteria" in result:
        out["criteria"] = result["criteria"]
    if result["stage"] == "T-1":
        out["criteria"] = {name: s["criteria"] for name, s in result["summaries"].items()}
    return out


def judge(stage: str, path: Path, baseline_path: Path, t1_path: Path | None,
          candidate: str | None) -> dict:
    lines = read_lines(path)
    baseline = load_baseline(baseline_path)
    unknown = sorted({line_key(r) for r in lines if "error" not in r} - set(baseline))
    if unknown:
        raise ValueError(f"keys without a baseline line: {unknown[:3]}")
    if stage == "T-0":
        result = judge_t0(lines, baseline)
    elif stage == "T-1":
        result = judge_t1(lines, baseline)
    else:
        result = judge_t2(lines, baseline, None if t1_path is None else read_lines(t1_path),
                          candidate)
    errors = error_keys(lines)
    result["errors"] = errors
    if errors and result.get("stop") is None:
        result["stop"] = "H-2"
        result["reason"] = f"H-2: {len(errors)} error lines (retry once); " + result["reason"]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("stage", choices=("T-0", "T-1", "T-2"))
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--baseline", type=Path, default=BASELINE_PATH)
    parser.add_argument("--t1", type=Path, default=None, help="T-1 lines (T-2: C2 .. C5 too)")
    parser.add_argument("--candidate", default=None)
    parser.add_argument("--out", type=Path, default=None, help="Markdown report")
    args = parser.parse_args(argv)
    try:
        result = judge(args.stage, args.jsonl, args.baseline, args.t1, args.candidate)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"stage": args.stage, "error": repr(exc)}))
        return 2
    text = "\n".join(report_lines(result))
    if args.out is not None:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    print(json.dumps(final_json(result), default=str))
    return 1 if result.get("stop") else 0


if __name__ == "__main__":
    sys.exit(main())
