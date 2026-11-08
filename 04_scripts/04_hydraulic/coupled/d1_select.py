"""D-1 Chrono selection from the harness results (``d1_selection_rules.md``, sealed 2026-11-08).

Implements sections 3 (input fields), 4 (margin m and ranking), 5 (S1 roll sign of C2-03 / C2-07),
6 (S2 soft slope of S-01 / S-02, fup-rec exclusion), 7 (S3 D1-PSC triggers), 8 (crawler x3 2x2
transfer rule, for m and per term), 10 (gates G-1 .. G-5) and 12 (output). The selection does not
change any verdict (section 8 of the rules: D-5).

Input: ``run_v5.py d1`` result lines (``d1.jsonl``); every line's ``d1`` block carries the
section 3 fields (``d1_runs.py``). Output JSON: per cell the chosen Chrono row names, all
candidates with grade, m, the terms and the tie values, the baseline-failure flag, the fup-rec
exclusion, the D1-PSC triggers and rows, the 2x2 table per section 8 cell, the gates and the
SHA-256 of the rules text and of this script (LF-normalised).

Exit code: 0 selection done, 1 a gate (G-1, G-3, G-4) stopped it, 2 input missing (G-2 field
missing, no rules text, no input file).

Usage (python-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/d1_select.py <out_json> <d1.jsonl> [...]
      [--rules 06_analysis/02_control/verif_matrix/d1_selection_rules.md]
      [--revisions 06_analysis/02_control/verif_matrix/d1_selection_rules_rev1.md]
The report records each revision's SHA-256 read from the file and its seal (``rules_revisions``;
rev1 2026-11-08: H-S READY limit = spec 421.1, carried by ``d1_rows`` / ``d1.t_ready_limit_s``).
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

DEFAULT_RULES = ROOT / "06_analysis" / "02_control" / "verif_matrix" / "d1_selection_rules.md"
DEFAULT_REVISIONS = (DEFAULT_RULES.with_name("d1_selection_rules_rev1.md"),)
"""Sealed addenda of the rules (rev1 2026-11-08: H-S READY limit = spec 421.1)."""
REQUIRED_FIELDS = ("key", "verdict", "fail_items", "F_judged_min_N", "F_first_level_min_N",
                   "t_ready_s", "t_ready_limit_s", "att_judged_deg", "stroke_max_m", "imu_R_c",
                   "dsb75_events", "j_p3")
"""Section 3 fields of the ``d1`` block (a run without one of them: exit 2)."""
F_MIN_N = 9415.0
ATTITUDE_LIMIT_DEG = 0.2
STROKE_END_M = 0.6848
TIE_M = 1e-3
TIE_F_N = 1.0
TIE_STROKE_M = 1e-4
CELL_CAP = 2
GRADE_RANK = {"fail": 0, "allowed_stop": 1, "pass": 2}
MISSING_TERM = -1.0
"""Term value of a missing judged quantity (no lift-off, no end attitude): counted as a failure
margin so that such a run ranks first (ASSUMPTION, recorded per run in ``missing_terms``)."""
JUDGED_GROUPS = ("H-R-0", "H-R-A", "H-S-0", "H-S-1", "H-S-A", "H-S-C")
ASSUMED_BOUNDARY_SLOPE = "fup-rec"
EXPECTED_COMBINATIONS = {"H-R": 105, "H-S": 106, "H-S-C-g": 6}
"""Gate G-1 (``d1_selection_rules.md`` 10): combinations per family (H-S without H-S-C-g)."""
J_P3_STOP = ("setting_defect", "H-7")
PSC_F_NEAR_N = 1.1 * F_MIN_N
PSC_ATT_NEAR_DEG = 0.15
PSC_STROKE_NEAR_M = 0.6428
HOLD_EVENT = "INFO_DIFF_SINK_HOLD"
S1_CELLS = (("C2-03", "middle"), ("C2-07", "bottom"))
S2_CELLS = (("S-01", "middle"), ("S-02", "bottom"))
S2_SLOPES = ("diag-rec", "roll-rec", "fup-rec")
PSC_POINTS = (("c-slow", "FL"), ("c-mid", "FL"), ("c-edge", "FL"), ("c-fast", "FL"),
              ("c-mid", "RL"))
CRAWLER_CELLS = (("top", "flat"), ("top", "diag-op"), ("bottom", "flat"),
                 ("bottom", "diag-op"))
TERMS = ("m_F", "m_T", "m_a", "m_s")
LEVEL_LETTER = {"top": "T", "middle": "M", "bottom": "B"}


# ------------------------------------------------------------------------------------ digests
def file_sha256(path: Path) -> str:
    """SHA-256 of a text file with LF line ends (a CRLF checkout gives the same digest)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def sealed_rules_sha256(rules: Path) -> str | None:
    """First token of ``<rules stem>.sha256`` beside the rules text (None without it)."""
    seal = rules.with_suffix(".sha256")
    return seal.read_text(encoding="utf-8").split()[0] if seal.is_file() else None


def revision_record(path: Path) -> dict:
    """Name, SHA-256 (read from the file), sealed SHA-256 and their match of one addendum."""
    sha = file_sha256(path)
    sealed = sealed_rules_sha256(path)
    return {"rules": path.name, "sha256": sha, "sealed_sha256": sealed,
            "match_seal": sha == sealed}


# -------------------------------------------------------------------------------------- runs
def run_margin(d1: dict) -> dict:
    """Section 4.1: terms and m of one run (PS-c rows without m_T; no READY: m_T left out)."""
    missing = []

    def term(value, limit, *, upper: bool) -> float:
        if value is None:
            return MISSING_TERM
        return (limit - value) / limit if upper else (value - limit) / limit

    f_judged = d1["F_judged_min_N"]
    att = d1["att_judged_deg"]
    if f_judged is None:
        missing.append("m_F")
    if att is None:
        missing.append("m_a")
    terms = {"m_F": term(f_judged, F_MIN_N, upper=False),
             "m_a": term(att, ATTITUDE_LIMIT_DEG, upper=True),
             "m_s": term(d1["stroke_max_m"], STROKE_END_M, upper=True), "m_T": None}
    is_psc = d1.get("path") == "event" or str(d1.get("group", "")).startswith("H-S-C")
    if not is_psc and d1["t_ready_s"] is not None:
        terms["m_T"] = (d1["t_ready_limit_s"] - d1["t_ready_s"]) / d1["t_ready_limit_s"]
    used = [value for value in terms.values() if value is not None]
    return {"m": min(used), "terms": terms, "missing_terms": missing}


def run_entry(line: dict) -> dict:
    """Plain selection record of one result line."""
    d1, job = line["d1"], line["job"]
    row = job["d1"]
    return {"row_key": row["key"], "group": row["group"], "level": row["level"],
            "slope": row["slope_name"], "base": row["base"], "K": row["crawler_k_scale"],
            "sink": row.get("sink"), "tags": row.get("tags") or [], "setting": job["setting"],
            "eps": float(job["eps"]), "grade": d1["verdict"], "fail_items": d1["fail_items"],
            "F_first_level_min_N": d1["F_first_level_min_N"],
            "stroke_max_m": d1["stroke_max_m"], "F_judged_min_N": d1["F_judged_min_N"],
            "att_judged_deg": d1["att_judged_deg"], "dsb75_events": d1["dsb75_events"],
            "j_p3": d1["j_p3"], "guard_active_s": (line.get("values") or {}).get("guard_active_s"),
            **run_margin(d1)}


# -------------------------------------------------------------------------------- candidates
def candidate(name: str, runs: list[dict]) -> dict:
    """Section 4.2: worst grade, smallest m, the tie values of the run with that m."""
    worst = min(runs, key=lambda run: GRADE_RANK[run["grade"]])["grade"]
    tie_run = min(runs, key=lambda run: run["m"])
    return {"name": name, "grade": worst, "m": tie_run["m"],
            "F_first_level_min_N": tie_run["F_first_level_min_N"],
            "stroke_max_m": tie_run["stroke_max_m"], "eps": tie_run["eps"],
            "tie_run": {k: tie_run.get(k) for k in ("row_key", "setting", "eps", "terms")},
            "runs": [{k: run.get(k) for k in ("row_key", "setting", "eps", "grade", "m",
                                               "terms", "missing_terms", "fail_items")}
                     for run in runs]}


def _compare(a: dict, b: dict) -> int:
    """Section 4.3 order (negative = ``a`` first)."""
    if GRADE_RANK[a["grade"]] != GRADE_RANK[b["grade"]]:
        return GRADE_RANK[a["grade"]] - GRADE_RANK[b["grade"]]
    if abs(a["m"] - b["m"]) >= TIE_M:
        return -1 if a["m"] < b["m"] else 1
    fa, fb = a["F_first_level_min_N"], b["F_first_level_min_N"]
    if fa is not None and fb is not None and abs(fa - fb) >= TIE_F_N:
        return -1 if fa < fb else 1
    sa, sb = a["stroke_max_m"], b["stroke_max_m"]
    if sa is not None and sb is not None and abs(sa - sb) >= TIE_STROKE_M:
        return -1 if sa > sb else 1
    if (a["eps"] == 0.0) != (b["eps"] == 0.0):
        return -1 if a["eps"] == 0.0 else 1
    return -1 if a["name"] < b["name"] else (1 if a["name"] > b["name"] else 0)


def rank(candidates: list[dict]) -> list[dict]:
    return sorted(candidates, key=functools.cmp_to_key(_compare))


def is_baseline_failure(chosen: dict, v0_grade_of) -> bool:
    """Section 4.3: the chosen candidate fails and a failing run's V0 twin fails too."""
    if chosen["grade"] != "fail":
        return False
    return any(run["grade"] == "fail" and v0_grade_of(run["row_key"], run["eps"]) == "fail"
               for run in chosen["runs"])


def select_cell(candidates: list[dict], v0_grade_of) -> dict:
    """One row, or two on a baseline failure (cap :data:`CELL_CAP`)."""
    ranked = rank(candidates)
    chosen = ranked[:1]
    baseline = bool(ranked) and is_baseline_failure(ranked[0], v0_grade_of)
    if baseline and len(ranked) > 1:
        chosen = ranked[:CELL_CAP]
    return {"selected": [c["name"] for c in chosen], "baseline_failure": baseline,
            "ranking": [c["name"] for c in ranked], "candidates": ranked}


def select_soft_slope(candidates: list[dict], v0_grade_of) -> dict:
    """Section 6: fup-rec competes unless its grade is ``fail`` (then excluded, a question)."""
    fup = [c for c in candidates if c["slope"] == ASSUMED_BOUNDARY_SLOPE]
    excluded = [c["name"] for c in fup if c["grade"] == "fail"]
    kept = [c for c in candidates if c["name"] not in excluded]
    out = select_cell(kept, v0_grade_of)
    out["candidates"] = rank(candidates)
    out["fup_rec_excluded"] = bool(excluded)
    if excluded:
        out["fup_rec_note"] = ("가정 경계 미성립 (U3): 앞들림 경계 재결정을 사용자 질문으로 "
                               "올린다 (제어기 결함으로 읽지 않는다)")
    return out


def psc_triggers(profile: str, runs: list[dict]) -> dict:
    """Section 7 T1 .. T3 of one profile (its VB runs, both phases)."""
    holds = [sum(1 for e in run["dsb75_events"] if e.get("name") == HOLD_EVENT) for run in runs]
    t2 = (profile == "c-slow" and any(h >= 1 for h in holds)) or (
        profile in ("c-mid", "c-fast") and bool(runs) and all(h == 0 for h in holds))
    f_values = [run["F_judged_min_N"] for run in runs]
    t3 = (any(f is None or f < PSC_F_NEAR_N for f in f_values)
          or any(run["att_judged_deg"] is None or run["att_judged_deg"] > PSC_ATT_NEAR_DEG
                 for run in runs)
          or any(run["stroke_max_m"] > PSC_STROKE_NEAR_M for run in runs))
    return {"T1_fail": any(run["grade"] == "fail" for run in runs), "T2_dsb75_role": bool(t2),
            "T3_near_limit": bool(t3), "holds_by_eps": dict(zip(
                [run["eps"] for run in runs], holds, strict=True)),
            "F_judged_min_N": min((f for f in f_values if f is not None), default=None),
            "att_max_deg": max((r["att_judged_deg"] for r in runs
                                if r["att_judged_deg"] is not None), default=None),
            "stroke_max_m": max((run["stroke_max_m"] for run in runs), default=None)}


def crawler_rule(means: dict[tuple[str, int], float], sigma: float) -> dict:
    """Section 8: Delta_V0, Delta_VB, I and the rule number (1 transfer, 2 no effect, 3 open).

    ``means`` keys: (``V0`` | ``VB``, 1 | 3) -> phase mean of the term."""
    delta_v0 = means[("V0", 3)] - means[("V0", 1)]
    delta_vb = means[("VB", 3)] - means[("VB", 1)]
    interaction = delta_vb - delta_v0
    same_sign = delta_vb != 0.0 and delta_v0 != 0.0 and (delta_vb > 0) == (delta_v0 > 0)
    if same_sign and abs(interaction) <= 0.5 * max(abs(delta_vb), abs(delta_v0)):
        rule = 1
    elif abs(delta_vb) < sigma and abs(delta_v0) < sigma:
        rule = 2
    else:
        rule = 3
    out = {"delta_V0": delta_v0, "delta_VB": delta_vb, "I": interaction, "sigma": sigma,
           "rule": rule, "text": {1: "옮겨 읽음", 2: "크롤러 강성 영향 없음",
                                  3: "VB 크롤러 감도 미확정"}[rule]}
    if rule == 1:
        out["transfer_correction"] = means[("VB", 3)] - means[("V0", 3)]
        out["transfer_rule"] = "m_C(VB,3) ~ m_C(V0,3) + transfer_correction (record, not a verdict)"
    return out


# ----------------------------------------------------------------------------------- tables
def _tag(value: float) -> str:
    return f"{value:g}".replace("-", "m").replace(".", "p")


def _by_key(entries: list[dict]) -> dict:
    return {(e["row_key"], e["setting"], e["eps"]): e for e in entries}


def _v0_lookup(index: dict):
    def v0_grade_of(row_key: str, eps: float) -> str | None:
        twin = index.get((row_key, "V0", eps))
        return None if twin is None else twin["grade"]
    return v0_grade_of


def s1_selection(entries: list[dict], index: dict) -> dict:
    out = {}
    for cell, level in S1_CELLS:
        candidates = []
        for slope, chrono in (("roll+op", "roll4.4"), ("roll-op", "rollm4.4")):
            runs = [e for e in entries if e["group"] == "H-R-0" and e["level"] == level
                    and e["slope"] == slope and e["setting"] == "VB"]
            if runs:
                candidates.append({**candidate(f"D1C2_{level}_{chrono}_Fs4", runs),
                                   "slope": slope})
        out[cell] = select_cell(candidates, _v0_lookup(index))
    return out


def s2_selection(entries: list[dict], index: dict, slope_deg) -> dict:
    out = {}
    for cell, level in S2_CELLS:
        candidates = []
        for slope in S2_SLOPES:
            runs = [e for e in entries if e["group"] == "H-S-0" and e["base"] == "J1"
                    and e["level"] == level and e["slope"] == slope and e["setting"] == "VB"]
            if runs:
                roll, pitch = slope_deg(slope)
                name = f"D1S_J1_B_{level}_Fs4_r{_tag(roll)}_p{_tag(pitch)}"
                candidates.append({**candidate(name, runs), "slope": slope})
        out[cell] = select_soft_slope(candidates, _v0_lookup(index))
    return out


def s3_selection(entries: list[dict]) -> dict:
    profiles, rows = {}, []
    for name, leg in PSC_POINTS:
        runs = [e for e in entries if e["group"] == "H-S-C" and e["base"] == "J1"
                and e["level"] == "top" and e["setting"] == "VB" and e["sink"]
                and e["sink"]["name"] == name and e["sink"]["leg"] == leg]
        triggers = psc_triggers(name, runs)
        is_in = triggers["T1_fail"] or triggers["T2_dsb75_role"] or triggers["T3_near_limit"]
        profiles[f"{name}@{leg}"] = {**triggers, "included": is_in, "runs": len(runs)}
        if is_in:
            rows += [f"D1PSC_J1_B_top_Fs4_{leg}_{name.replace('-', '')}",
                     f"D1PSC_J1_B_top_Fs4_sp{leg}J1_base"]
    rows = list(dict.fromkeys(rows))
    return {"profiles": profiles, "rows": rows,
            "decision": "include" if rows else "하네스 근거로 생략"}


def _quantity(index: dict, row_key: str | None, setting: str, eps: float,
              quantity: str) -> float | None:
    """m or one term of the run (row, setting, eps); None without that run."""
    entry = index.get((row_key, setting, eps))
    if entry is None:
        return None
    return entry["m"] if quantity == "m" else entry["terms"][quantity]


def crawler_table(entries: list[dict], index: dict) -> dict:
    """Section 8 per cell: m and each term."""
    out = {}
    for level, slope in CRAWLER_CELLS:
        row_keys = {k: next((e["row_key"] for e in entries if e["group"] == "H-R-0"
                             and e["level"] == level and e["slope"] == slope and e["K"] == k),
                            None) for k in (1, 3)}
        cell = {}
        for quantity in ("m", *TERMS):
            pairs = {(s, k): (_quantity(index, row_keys[k], s, 0.0, quantity),
                              _quantity(index, row_keys[k], s, 2e-3, quantity))
                     for s in ("V0", "VB") for k in (1, 3)}
            if any(v is None for pair in pairs.values() for v in pair):
                cell[quantity] = {"rule": None, "note": "term missing in a run"}
                continue
            means = {key: 0.5 * (a + b) for key, (a, b) in pairs.items()}
            sigma = max(abs(a - b) for a, b in pairs.values())
            cell[quantity] = {**crawler_rule(means, sigma),
                              "means": {f"{s},{k}": v for (s, k), v in means.items()}}
        rules_by_term = {q: cell[q].get("rule") for q in TERMS}
        cell["terms_differ_from_m"] = any(r != cell["m"].get("rule") for r in
                                          rules_by_term.values())
        out[f"{LEVEL_LETTER[level]}|{slope}"] = cell
    return out


# ------------------------------------------------------------------------------------- gates
def gate_g1(lines: list[dict], expected_keys: set[str]) -> dict:
    errors = [line["job"] for line in lines if "error" in line]
    seen = {_job_identity(line["job"]) for line in lines if "error" not in line}
    missing = sorted(expected_keys - seen)
    combos: dict[str, set] = {}
    for line in lines:
        row = line["job"]["d1"]
        family = "H-S-C-g" if row["group"] == "H-S-C-g" else row["group"][:3]
        combos.setdefault(family, set()).add(row["key"])
    counts = {family: len(keys) for family, keys in combos.items()}
    return {"pass": not errors and not missing and counts == EXPECTED_COMBINATIONS,
            "run_errors": len(errors), "missing_runs": len(missing),
            "combinations": counts, "expected": EXPECTED_COMBINATIONS}


def _job_identity(job: dict) -> str:
    return json.dumps({"row": job["d1"]["key"], "setting": job["setting"],
                       "eps": float(job["eps"])}, sort_keys=True)


def gate_g3(entries: list[dict], index: dict) -> dict:
    """VB fail with a passing V0 twin in a judged row (fup-rec exempt, section 6)."""
    hits = []
    for e in entries:
        if (e["setting"] != "VB" or e["grade"] != "fail" or e["group"] not in JUDGED_GROUPS
                or e["slope"] == ASSUMED_BOUNDARY_SLOPE):
            continue
        twin = index.get((e["row_key"], "V0", e["eps"]))
        if twin is not None and twin["grade"] == "pass":
            hits.append({"row_key": e["row_key"], "eps": e["eps"], "fail_items": e["fail_items"]})
    return {"pass": not hits, "vb_only_failures": hits}


def gate_g4(entries: list[dict]) -> dict:
    hits = [{"row_key": e["row_key"], "eps": e["eps"], "j_p3": e["j_p3"]} for e in entries
            if e["setting"] == "VB" and e["j_p3"] in J_P3_STOP]
    counts: dict[str, int] = {}
    for e in entries:
        if e["setting"] == "VB":
            counts[e["j_p3"]] = counts.get(e["j_p3"], 0) + 1
    return {"pass": not hits, "stops": hits, "vb_j_p3_counts": counts}


def missing_fields(lines: list[dict]) -> list[dict]:
    """Gate G-2: runs whose ``d1`` block lacks a section 3 field."""
    out = []
    for line in lines:
        if "error" in line:
            continue
        d1 = line.get("d1") or {}
        lacking = [name for name in REQUIRED_FIELDS if name not in d1]
        if lacking:
            out.append({"job": line.get("job"), "missing": lacking})
    return out


# -------------------------------------------------------------------------------------- main
def select(lines: list[dict], expected_keys: set[str], slope_deg) -> tuple[dict, int]:
    """The section 12 report and the exit code (gates G-1 .. G-4 first)."""
    lacking = missing_fields(lines)
    if lacking:
        return {"gates": {"G-2": {"pass": False, "runs": lacking[:50],
                                  "count": len(lacking)}}}, 2
    entries = [run_entry(line) for line in lines if "error" not in line]
    index = _by_key(entries)
    gates = {"G-1": gate_g1(lines, expected_keys), "G-2": {"pass": True},
             "G-3": gate_g3(entries, index), "G-4": gate_g4(entries)}
    report = {"gates": gates, "runs": len(entries)}
    if not all(gates[g]["pass"] for g in ("G-1", "G-3", "G-4")):
        return report, 1
    report.update(S1=s1_selection(entries, index), S2=s2_selection(entries, index, slope_deg),
                  S3=s3_selection(entries), crawler_x3=crawler_table(entries, index))
    return report, 0


def _read_lines(paths: list[Path]) -> list[dict]:
    lines = []
    for path in paths:
        lines += [json.loads(text) for text in path.read_text(encoding="utf-8").splitlines()
                  if text.strip()]
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out_json")
    parser.add_argument("results", nargs="+", help="run_v5 d1 result files (jsonl)")
    parser.add_argument("--rules", default=str(DEFAULT_RULES))
    parser.add_argument("--revisions", nargs="*", default=[str(p) for p in DEFAULT_REVISIONS],
                        help="sealed addenda of the rules (default: rev1)")
    args = parser.parse_args()
    rules, inputs = Path(args.rules), [Path(p) for p in args.results]
    revisions = [Path(p) for p in args.revisions]
    if not all(p.is_file() for p in (rules, *revisions, *inputs)):
        print(json.dumps({"error": "rules text, a rules revision or an input missing"}))
        return 2
    import d1_rows

    expected = {_job_identity(job) for job in d1_rows.jobs()}
    report, code = select(_read_lines(inputs), expected, d1_rows.slope_deg)
    rules_sha = file_sha256(rules)
    report = {"rules": str(rules), "rules_sha256": rules_sha,
              "rules_sealed_sha256": sealed_rules_sha256(rules),
              "rules_match_seal": rules_sha == sealed_rules_sha256(rules),
              "rules_revisions": [revision_record(p) for p in revisions],
              "script_sha256": file_sha256(Path(__file__)),
              "inputs": [str(p) for p in inputs], "exit_code": code, **report}
    Path(args.out_json).write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    summary = {k: report.get(k) for k in ("exit_code", "rules_sha256", "script_sha256")}
    summary["rules_revisions_sha256"] = [r["sha256"] for r in report["rules_revisions"]]
    summary["gates"] = {name: gate["pass"] for name, gate in report["gates"].items()}
    print(json.dumps(summary))
    return code


if __name__ == "__main__":
    sys.exit(main())
