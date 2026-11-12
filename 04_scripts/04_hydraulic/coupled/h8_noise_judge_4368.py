"""436.8 path 1 grade re-aggregation of the H-8 noise bundle, new version (rules rev5 R5-A1).

The gate values of every noise line are the designated judge's (``r79_sensor_judge.py judge …
--s4-late-loc``, v5 criteria 10 / 13.2, rules rev4 R4-A2 table); this tool re-aggregates the
line grades and the bundle numbers with the rev3 R3-E3 / rev4 R4-B3 / rev5 R5-C1 .. C3
definitions (no simulation; the judge itself is unchanged and only run by ``--run-judge``):

  line grade   S-1, S-2, S-3, S-5, S-6 as the judge rows give them. S-4: a failure whose only
               cause is the LOC gate (LOC - departure > 2.9 s, new against L1) on a line whose
               spec 419.8 record (``base.late_loc_reapproach.is_flag``) is a FLAG is the FLAG
               ``S4_late_loc`` (criteria 13.2); a new recontact counts only as the spec 423.1 /
               407.2 ``strict_fail`` class (the judge's ``recontact_new``); an S-4 failure
               explained by none of misfire / miss / strict recontact / LOC gate is a failure
               and listed (rev5 R5-C2). A line with a missing judge row or gate key is
               ``판정 불가``.
  L2 (VB)      S1 front patches and pad A reference lines excluded (``r79_L3L4_final.is_excluded``,
               criteria rev3: n = 835), failures k, one-sided Clopper-Pearson 95 % upper bound by
               ``beta.ppf`` and by the ``binom.cdf`` root; > 3 % = H-10. The 135 dg3 keys are the
               H-6 lines (``--h6`` replaces them, original rules 5.1 H-8 / rev1 RV1-3).
  L1 gate (VB) R4-B3: false LOC (L1 ``r79.crawler_at_loc_over_W`` >= 0.01), unmatched (L2 / L3
               line without the L1 line of the same harness, ``case_index``, ``inner``), errors
               (meta ``n_errors`` + results with ``error``), settings mismatch (``v5_setting`` not
               the bundle setting); any count > 0 = H-10. Each count is set against the judge
               output's own count; a difference is ``판정 불가`` (S-13). The judge output has no
               ``settings_mismatch``: that comparison is "대조 대상 없음" (rev5 R5-C1).
  L3, V0       record (failures, CP upper bounds, VB pass -> fail against the same V0 key).
  seedext      per key and setting k/25, both CP roots, failed gate names, one-sided Fisher exact
               p (VB > V0) and the criteria revision 6 9 wording; the L1 pair is the same-setting
               noise L1 line (rev5 R5-C3); seeds 0 .. 4 command hashes (top-level
               ``commands_sha256``, F-6) equal the noise lines of the same key, else H-15.

Usage (python-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/h8_noise_judge_4368.py --out <report.json>
      --noise-vb resume_k1/h8_noise_VB.json --noise-v0 resume_k1/h8_noise_V0.json
      --h6 resume_k1/h6_dg3_v4on.json
      --seedext-vb resume_k1/h8_seedext_VB.json --seedext-v0 resume_k1/h8_seedext_V0.json
      --judge-dir <folder of the judge outputs> [--run-judge] [--rules-dir <verif_matrix>]
  ``--run-judge`` first writes the judge outputs into ``--judge-dir`` (commands in the report);
  without it the four outputs must already be there (names: :data:`JUDGE_OUTPUT_NAMES`).
Exit codes: 0 judged without a finding, 1 a finding (H-10, H-15, 판정 불가, count mismatch,
"VB 체계적 악화 의심"), 2 input error, 3 internal error.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import judge4368_common as common  # noqa: E402

R79_JUDGE = ROOT / "04_scripts" / "03_control" / "s8" / "r79_sensor_judge.py"
R79_FINAL = ROOT / "04_scripts" / "03_control" / "s8" / "r79_L3L4_final.py"
LATE_LOC_OPTION = "--s4-late-loc"
S4_LATE_LOC_FLAG = "S4_late_loc"
GATES = ("S-1", "S-2", "S-3", "S-4", "S-5", "S-6")
S4_KEYS = ("ok", "fail_misfire_new", "miss", "gate_fail", "recontact_new", "flags")

LEVEL_REFERENCE = "L1"
LEVEL_GRADED = "L2"
LEVEL_RECORD = "L3"
NOT_JUDGED_LEVELS = ("L0", "L1")
S1_FRONT_MARKERS = ("S1@FL", "S1@FR")
PAD_A_INNER = re.compile(r"(G1|J1|J2|S1)\|A\|.*")
"""``r79_L3L4_final.S1_FRONT_MARKERS`` / ``PAD_A_INNER`` (a unit test keeps them equal)."""
EXPECTED_L2_LINES = 835
"""Criteria rev3: L2 lines after the exclusion (allowed failures 16)."""
ACCEPT_UPPER = 0.03
CONFIDENCE = 0.95
FALSE_LOC_FRACTION_OF_W = 0.01
SEEDEXT_SEEDS = 25
HASH_CHECK_SEEDS = range(5)
FISHER_ALPHA = 0.05
WORDING_SUSPECT = "VB 체계적 악화 의심(하네스)"
WORDING_SCATTER = "시드 산포와 구분되지 않음"
CANDIDATE_PREFIX = re.compile(r"^cand=[^#]*#")

GRADE_PASS = "pass"
GRADE_FLAG = "flag"
GRADE_FAIL = "fail"
GRADE_NOT_JUDGEABLE = common.NOT_JUDGEABLE

JUDGE_OUTPUT_NAMES = {
    "VB": "judge_h8_noise_VB.json",
    "V0": "judge_h8_noise_V0.json",
    "seedext_VB": "judge_h8_seedext_VB.json",
    "seedext_V0": "judge_h8_seedext_V0.json",
}
DEFINITION_CHANGES: tuple[str, ...] = ()
"""Rev5 R5-A3 has no D item for H-8: the definitions are R3-E3, R4-B3, R5-C1 .. C3 (below)."""
AGGREGATION_DEFINITIONS = (
    "13.2 S4_late_loc: S-4 LOC gate only + spec 419.8 FLAG record -> FLAG (criteria 13.2)",
    "423.1 / 407.2: a new recontact counts only as strict_fail (judge recontact_new)",
    "R5-C2: an S-4 failure explained by no sub-item is a failure (listed)",
    "S1 front / pad A excluded (r79_L3L4_final.is_excluded), L2 n expected 835",
    "CP one-sided 95 % by beta.ppf and binom.cdf root; L2 > 3 % = H-10",
    "R4-B3 L1 gate four counts against the judge counts (difference = 판정 불가, S-13)",
    "R5-C1: no settings_mismatch in the judge output = 대조 대상 없음",
    "R5-C3: seedext L1 pair = same-setting noise L1 line; seeds 0 .. 4 hash = H-15",
)


# ------------------------------------------------------------------------------------ helpers
def plain_key(key: str) -> str:
    """Rev3 R3-D1: ``cand=current#<key>`` and ``<key>`` are the same key."""
    return CANDIDATE_PREFIX.sub("", str(key))


def is_excluded(inner: str) -> bool:
    """S1 front patch or pad type A reference line (criteria rev3, ``r79_L3L4_final``)."""
    return any(m in inner for m in S1_FRONT_MARKERS) or PAD_A_INNER.fullmatch(inner) is not None


def pair_key(run: dict) -> tuple[str, Any, str]:
    """Rev4 R4-B3: the L1 pair has the same harness, ``case_index`` and ``inner``."""
    return (run.get("harness"), run.get("case_index"), run.get("inner"))


def cp_upper_beta(failures: int, runs: int) -> float | None:
    from scipy.stats import beta

    if runs == 0:
        return None
    if failures >= runs:
        return 1.0
    return float(beta.ppf(CONFIDENCE, failures + 1, runs - failures))


def cp_upper_binom(failures: int, runs: int) -> float | None:
    """Second root: the p with P(X <= k | n, p) = 1 - confidence."""
    from scipy.optimize import brentq
    from scipy.stats import binom

    if runs == 0:
        return None
    if failures >= runs:
        return 1.0
    return float(
        brentq(
            lambda p: binom.cdf(failures, runs, p) - (1.0 - CONFIDENCE),
            1e-15,
            1 - 1e-15,
            xtol=1e-15,
            rtol=1e-15,
            maxiter=500,
        )
    )


def read_run_file(path: Path) -> dict:
    data = common.read_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise common.InputError(f"{path}: not an r79 run file (meta, results)")
    return data


def substitute_lines(noise: list[dict], replacements: list[dict]) -> tuple[list[dict], dict]:
    """Original rules 5.1 H-8 / rev1 RV1-3: the dg3 keys are judged by their H-6 lines."""
    by_key = {plain_key(r["key"]): r for r in replacements}
    merged, replaced = [], set()
    for run in noise:
        key = plain_key(run["key"])
        if key in by_key:
            merged.append(by_key[key])
            replaced.add(key)
        else:
            merged.append(run)
    same = differs = incomplete = 0
    for run in noise:
        key = plain_key(run["key"])
        if key not in by_key:
            continue
        mine, theirs = run.get("commands_sha256"), by_key[key].get("commands_sha256")
        if mine is None or theirs is None:  # rev3 R3-E4: 기록 불완전, not a stop
            incomplete += 1
        elif mine == theirs:
            same += 1
        else:
            differs += 1
    return merged, {
        "replaced": len(replaced),
        "replacement_lines": len(by_key),
        "without_noise_line": sorted(set(by_key) - replaced),
        "hash_same_top_level": same,
        "hash_differs_top_level": differs,
        "hash_record_incomplete": incomplete,
    }


# -------------------------------------------------------------------------------- line grades
def s4_causes(s4: dict) -> list[str]:
    causes = []
    if s4["fail_misfire_new"]:
        causes.append("misfire_new")
    if s4["miss"]:
        causes.append("miss")
    if s4["recontact_new"]:
        causes.append("recontact_strict_fail")
    if s4["gate_fail"] and not s4["recontact_new"]:
        causes.append("loc_gate")
    return causes


def has_late_loc_flag_record(run: dict) -> bool:
    """Criteria 13.2: the line's spec 419.8 record (r72 ``late_loc_reapproach``) is a FLAG."""
    record = (run.get("base") or {}).get("late_loc_reapproach") or {}
    return bool(record.get("is_flag"))


def grade_line(row: dict | None, run: dict) -> dict:
    """Path 1 grade of one judged line (module docstring)."""
    if row is None:
        return {"grade": GRADE_NOT_JUDGEABLE, "reason": "no judge row"}
    gates = row.get("rows") or {}
    missing = [name for name in GATES if "ok" not in (gates.get(name) or {})]
    missing += [f"S-4.{k}" for k in S4_KEYS if k not in (gates.get("S-4") or {})]
    if missing:
        return {"grade": GRADE_NOT_JUDGEABLE, "reason": f"judge row without {missing}"}
    failed = [name for name in GATES if name != "S-4" and not gates[name]["ok"]]
    flags = [flag for name in GATES for flag in gates[name].get("flags") or []]
    s4 = gates["S-4"]
    out: dict[str, Any] = {"s4_causes": [], "s4_unexplained": False}
    if not s4["ok"]:
        causes = s4_causes(s4)
        out["s4_causes"] = causes
        if causes == ["loc_gate"] and has_late_loc_flag_record(run):
            flags.append(S4_LATE_LOC_FLAG)
        else:
            failed.append("S-4")
            out["s4_unexplained"] = not causes
    out.update(
        grade=GRADE_FAIL if failed else (GRADE_FLAG if flags else GRADE_PASS),
        failed_gates=failed,
        flags=sorted(set(flags)),
        judge_pass=row.get("pass"),
    )
    return out


def grade_lines(results: list[dict], judge_report: dict) -> dict[str, dict]:
    """Plain key -> grade of every judged-level line (L2, L3, ...) without an error."""
    rows = {plain_key(r["key"]): r for r in judge_report.get("runs") or []}
    grades = {}
    for run in results:
        if run.get("level") in NOT_JUDGED_LEVELS or "error" in run:
            continue
        key = plain_key(run["key"])
        grades[key] = {
            **grade_line(rows.get(key), run),
            "level": run.get("level"),
            "inner": run.get("inner"),
            "seed_index": run.get("seed_index"),
        }
    return grades


def level_summary(grades: dict[str, dict], level: str) -> dict:
    """Counts and both CP roots of one level, S1 front / pad A lines excluded."""
    lines = {k: g for k, g in grades.items() if g["level"] == level}
    kept = {k: g for k, g in lines.items() if not is_excluded(str(g["inner"]))}
    undecided = sorted(k for k, g in kept.items() if g["grade"] == GRADE_NOT_JUDGEABLE)
    failures = sorted(k for k, g in kept.items() if g["grade"] == GRADE_FAIL)
    n, k = len(kept), len(failures)
    upper_beta, upper_binom = cp_upper_beta(k, n), cp_upper_binom(k, n)
    return {
        "level": level,
        "lines": len(lines),
        "excluded_s1_front_pad_a": len(lines) - n,
        "n": n,
        "failures": k,
        "cp95_upper_beta": upper_beta,
        "cp95_upper_binom_root": upper_binom,
        "cp_roots_abs_diff": (None if upper_beta is None else abs(upper_beta - upper_binom)),
        "is_within_3pct": upper_beta is not None and not common.is_above(upper_beta, ACCEPT_UPPER),
        "not_judgeable": undecided,
        "failed_keys": failures,
        "failed_gate_counts": dict(
            Counter(gate for g in kept.values() for gate in g.get("failed_gates") or [])
        ),
        "flag_counts": dict(Counter(f for g in kept.values() for f in g.get("flags") or [])),
        "s4_unexplained": sorted(k for k, g in kept.items() if g.get("s4_unexplained")),
        "judge_pass_differs": sorted(
            k
            for k, g in kept.items()
            if g["grade"] != GRADE_NOT_JUDGEABLE
            and bool(g.get("judge_pass")) != (g["grade"] != GRADE_FAIL)
        ),
    }


# ------------------------------------------------------------------------------------ L1 gate
def l1_gate(run_files: list[dict], results: list[dict], judge_report: dict, setting: str) -> dict:
    """Rev4 R4-B3 four counts from the run records, set against the judge output (R5-C1)."""
    references = [r for r in results if r.get("level") == LEVEL_REFERENCE and "error" not in r]
    ratios = [(r.get("r79") or {}).get("crawler_at_loc_over_W") for r in references]
    false_loc = sum(
        1 for x in ratios if x is not None and common.is_at_least(x, FALSE_LOC_FRACTION_OF_W)
    )
    pairs = {pair_key(r) for r in references}
    judged = [r for r in results if r.get("level") not in NOT_JUDGED_LEVELS and "error" not in r]
    unmatched = sum(1 for r in judged if pair_key(r) not in pairs)
    error_results = sum(1 for r in results if "error" in r)
    meta_errors = sum(int((f.get("meta") or {}).get("n_errors") or 0) for f in run_files)
    settings_bad = sum(1 for r in results if r.get("v5_setting") != setting)
    direct = {
        "false_loc": false_loc,
        "unmatched": unmatched,
        "errors": meta_errors + error_results,
        "settings_mismatch": settings_bad,
    }
    reference_all = next(
        (e for e in judge_report.get("reference") or [] if e.get("group") == "all"), {}
    )
    judge_side = {
        "false_loc": reference_all.get("false_loc"),
        "unmatched": len(judge_report.get("unmatched") or []),
        # the judge lists the error results of the judged levels only
        "errors": len(judge_report.get("errors") or []),
        "settings_mismatch": (
            len(judge_report["settings_mismatch"]) if "settings_mismatch" in judge_report else None
        ),
    }
    judge_errors_basis = sum(
        1 for r in results if "error" in r and r.get("level") not in NOT_JUDGED_LEVELS
    )
    comparisons = {
        "false_loc": _compare(false_loc, judge_side["false_loc"]),
        "unmatched": _compare(unmatched, judge_side["unmatched"]),
        "errors": _compare(judge_errors_basis, judge_side["errors"]),
        "settings_mismatch": (
            "대조 대상 없음"
            if judge_side["settings_mismatch"] is None
            else _compare(settings_bad, judge_side["settings_mismatch"])
        ),
    }
    return {
        "setting": setting,
        "direct": direct,
        "missing_crawler_ratio_L1": sum(1 for x in ratios if x is None),
        "error_parts": {"meta_n_errors": meta_errors, "error_results": error_results},
        "judge": judge_side,
        "errors_comparison_basis": "judge errors vs error results of L2 / L3 (judge definition)",
        "comparisons": comparisons,
        "is_violated": any(v > 0 for v in direct.values()),
        "is_count_mismatch": any(v == "다름" for v in comparisons.values()),
    }


def _compare(direct: int, judge_value: int | None) -> str:
    if judge_value is None:
        return "판정기 값 없음"
    return "같음" if direct == judge_value else "다름"


def pass_to_fail(vb: dict[str, dict], v0: dict[str, dict], level: str) -> dict:
    """Record: VB fail / V0 pass (and the reverse) of the same plain key."""
    to_fail, to_pass = [], []
    for key, grade in vb.items():
        other = v0.get(key)
        if grade["level"] != level or other is None or is_excluded(str(grade["inner"])):
            continue
        if grade["grade"] == GRADE_FAIL and other["grade"] in (GRADE_PASS, GRADE_FLAG):
            to_fail.append(key)
        elif other["grade"] == GRADE_FAIL and grade["grade"] in (GRADE_PASS, GRADE_FLAG):
            to_pass.append(key)
    return {"pass_to_fail": sorted(to_fail), "fail_to_pass": sorted(to_pass)}


# ------------------------------------------------------------------------------------ seedext
def seed_case(key: str) -> str:
    """The seedext case of a plain key ``L2|s<seed>|<harness>|<index>|<inner>``."""
    level, _, rest = plain_key(key).split("|", 2)
    return f"{level}|{rest}"


def seedext_summary(vb: dict[str, dict], v0: dict[str, dict]) -> dict:
    """Criteria revision 6 9: k/25 per key and setting, both CP roots, Fisher p, wording."""
    from scipy.stats import fisher_exact

    cases = sorted({seed_case(k) for k in (*vb, *v0)})
    out = {}
    for case in cases:
        entry: dict[str, Any] = {}
        for name, grades in (("VB", vb), ("V0", v0)):
            lines = {k: g for k, g in grades.items() if seed_case(k) == case}
            failed = [g for g in lines.values() if g["grade"] == GRADE_FAIL]
            n, k = len(lines), len(failed)
            entry[name] = {
                "n": n,
                "failures": k,
                "cp95_upper_beta": cp_upper_beta(k, n),
                "cp95_upper_binom_root": cp_upper_binom(k, n),
                "failed_gate_counts": dict(
                    Counter(gate for g in failed for gate in g.get("failed_gates") or [])
                ),
                "not_judgeable": sum(
                    1 for g in lines.values() if g["grade"] == GRADE_NOT_JUDGEABLE
                ),
            }
        k_vb, k_v0 = entry["VB"]["failures"], entry["V0"]["failures"]
        n_vb, n_v0 = entry["VB"]["n"], entry["V0"]["n"]
        _, p_value = fisher_exact([[k_vb, n_vb - k_vb], [k_v0, n_v0 - k_v0]], alternative="greater")
        is_suspect = p_value < FISHER_ALPHA and k_vb > k_v0
        entry.update(
            fisher_p_one_sided=float(p_value),
            wording=WORDING_SUSPECT if is_suspect else WORDING_SCATTER,
            is_n_expected=(n_vb == SEEDEXT_SEEDS and n_v0 == SEEDEXT_SEEDS),
        )
        out[case] = entry
    return out


def seed_hash_check(seedext: list[dict], noise: list[dict]) -> dict:
    """H-15: seeds 0 .. 4 top-level ``commands_sha256`` (F-6) equal the noise line of the key."""
    noise_hash = {plain_key(r["key"]): r.get("commands_sha256") for r in noise}
    rows, incomplete = [], []
    for run in seedext:
        if run.get("seed_index") not in HASH_CHECK_SEEDS:
            continue
        key = plain_key(run["key"])
        mine, theirs = run.get("commands_sha256"), noise_hash.get(key, "no noise line")
        if mine is None or theirs is None:
            incomplete.append(key)
            continue
        rows.append({"key": key, "same": mine == theirs})
    return {
        "checked": len(rows),
        "different": [r["key"] for r in rows if not r["same"]],
        "record_incomplete": incomplete,
    }


# ------------------------------------------------------------------------------- judge running
def reference_extract(noise: dict, path: Path) -> Path:
    """The L1 lines of a noise file as a run file (rev5 R5-C3: the seedext L1 pair)."""
    lines = [r for r in noise["results"] if r.get("level") == LEVEL_REFERENCE]
    meta = {**(noise.get("meta") or {}), "extract": "L1 lines only (436.8 rev5 R5-C3)"}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"meta": meta, "results": lines}, default=float), encoding="utf-8")
    return path


def run_r79_judge(out: Path, run_files: list[Path], rerun: Path | None = None) -> dict:
    """``r79_sensor_judge.py judge[-merged] … --s4-late-loc`` with this interpreter."""
    if rerun is None:
        arguments = ["judge", str(out), *map(str, run_files)]
    else:
        arguments = ["judge-merged", str(out), str(rerun), *map(str, run_files)]
    command = [sys.executable, "-I", "-B", str(R79_JUDGE), *arguments, LATE_LOC_OPTION]
    completed = subprocess.run(  # noqa: S603 (this interpreter, fixed script)
        command, capture_output=True, text=True, encoding="utf-8", check=False
    )
    return {
        "command": command[1:],
        "exit_code": completed.returncode,
        "last_line": (completed.stdout.strip().splitlines() or [""])[-1],
        "stderr_tail": completed.stderr.strip().splitlines()[-3:],
    }


def read_judge_output(path: Path) -> dict:
    report = common.read_json(path)
    if "runs" not in report:
        raise common.InputError(f"{path}: not an r79_sensor_judge judge output")
    return report


# ---------------------------------------------------------------------------------------- judge
def judge(args: argparse.Namespace) -> dict:
    files = {
        name: read_run_file(getattr(args, name))
        for name in ("noise_vb", "noise_v0", "h6", "seedext_vb", "seedext_v0")
    }
    judge_dir = Path(args.judge_dir)
    paths = {name: judge_dir / file for name, file in JUDGE_OUTPUT_NAMES.items()}
    runs: dict[str, Any] = {}
    if args.run_judge:
        runs["VB"] = run_r79_judge(paths["VB"], [args.noise_vb], rerun=args.h6)
        runs["V0"] = run_r79_judge(paths["V0"], [args.noise_v0])
        for setting in ("VB", "V0"):
            noise = files[f"noise_{setting.lower()}"]
            extract = reference_extract(noise, judge_dir / f"h8_noise_{setting}_L1.json")
            runs[f"seedext_{setting}"] = run_r79_judge(
                paths[f"seedext_{setting}"], [getattr(args, f"seedext_{setting.lower()}"), extract]
            )
    reports = {name: read_judge_output(path) for name, path in paths.items()}
    if reports["VB"].get("s4_late_loc_rule") is None:
        raise common.InputError(f"{paths['VB']}: judge output without {LATE_LOC_OPTION}")

    vb_results, substitution = substitute_lines(
        files["noise_vb"]["results"], files["h6"]["results"]
    )
    v0_results = files["noise_v0"]["results"]
    grades_vb = grade_lines(vb_results, reports["VB"])
    grades_v0 = grade_lines(v0_results, reports["V0"])
    seed_vb = grade_lines(files["seedext_vb"]["results"], reports["seedext_VB"])
    seed_v0 = grade_lines(files["seedext_v0"]["results"], reports["seedext_V0"])

    report: dict[str, Any] = {
        "inputs": {
            name: {
                "path": str(getattr(args, name)),
                "sha256": common.file_sha256(getattr(args, name)),
            }
            for name in files
        },
        "judge_outputs": {
            name: {"path": str(p), "sha256": common.file_sha256(p)} for name, p in paths.items()
        },
        "judge_runs": runs,
        "aggregation_definitions": list(AGGREGATION_DEFINITIONS),
        "dg3_substitution": substitution,
        "VB": {
            "L2": level_summary(grades_vb, LEVEL_GRADED),
            "L3": level_summary(grades_vb, LEVEL_RECORD),
            "L1_gate": l1_gate([files["noise_vb"], files["h6"]], vb_results, reports["VB"], "VB"),
            "vs_V0_L2": pass_to_fail(grades_vb, grades_v0, LEVEL_GRADED),
            "vs_V0_L3": pass_to_fail(grades_vb, grades_v0, LEVEL_RECORD),
        },
        "V0_record": {
            "L2": level_summary(grades_v0, LEVEL_GRADED),
            "L3": level_summary(grades_v0, LEVEL_RECORD),
            "L1_gate": l1_gate([files["noise_v0"]], v0_results, reports["V0"], "V0"),
        },
        "seedext": seedext_summary(seed_vb, seed_v0),
        "seed_hash_H15": {
            "VB": seed_hash_check(files["seedext_vb"]["results"], files["noise_vb"]["results"]),
            "V0": seed_hash_check(files["seedext_v0"]["results"], files["noise_v0"]["results"]),
        },
    }
    report["status"], report["findings"] = bundle_status(report)
    return report


def bundle_status(report: dict) -> tuple[str, list[str]]:
    """Original rules 8.1 order with the H-10 / H-15 stops first."""
    findings, stops = [], []
    l2, gate = report["VB"]["L2"], report["VB"]["L1_gate"]
    if not l2["is_within_3pct"]:
        stops.append(
            f"H-10: L2 CP upper {l2['cp95_upper_beta']} > 3 % ({l2['failures']}/{l2['n']})"
        )
    if gate["is_violated"]:
        stops.append(f"H-10: L1 gate {gate['direct']}")
    for setting, check in report["seed_hash_H15"].items():
        if check["different"]:
            stops.append(f"H-15: seedext {setting} seed 0..4 hash differs {check['different'][:5]}")
    undecided = list(l2["not_judgeable"])
    if gate["is_count_mismatch"]:
        undecided.append(f"S-13 L1 gate counts differ from the judge: {gate['comparisons']}")
    if l2["n"] != EXPECTED_L2_LINES:
        findings.append(f"S-15: L2 n {l2['n']} != {EXPECTED_L2_LINES}")
    orphans = report["dg3_substitution"]["without_noise_line"]
    if orphans:
        findings.append(f"S-15: H-6 keys without a noise line {orphans[:5]}")
    for case, entry in report["seedext"].items():
        if entry["wording"] == WORDING_SUSPECT:
            findings.append(f"사용자 확인: seedext {case} {WORDING_SUSPECT}")
        if not entry["is_n_expected"]:
            findings.append(f"S-15: seedext {case} n VB {entry['VB']['n']} / V0 {entry['V0']['n']}")
    for name, run in report["judge_runs"].items():
        if run["exit_code"] != 0:
            findings.append(f"judge run {name} exit {run['exit_code']}")
    findings = stops + [f"판정 불가: {u}" for u in undecided[:20]] + findings
    if stops:
        return "멈춤", findings
    if undecided:
        return GRADE_NOT_JUDGEABLE, findings
    return "통과", findings


def parser() -> argparse.ArgumentParser:
    out = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    common.add_common_arguments(out)
    out.add_argument("--noise-vb", type=Path, required=True, help="resume_k1/h8_noise_VB.json")
    out.add_argument("--noise-v0", type=Path, required=True, help="resume_k1/h8_noise_V0.json")
    out.add_argument("--h6", type=Path, required=True, help="resume_k1/h6_dg3_v4on.json")
    out.add_argument("--seedext-vb", type=Path, required=True, help="resume_k1/h8_seedext_VB.json")
    out.add_argument("--seedext-v0", type=Path, required=True, help="resume_k1/h8_seedext_V0.json")
    out.add_argument("--judge-dir", type=Path, required=True, help="folder of the judge outputs")
    out.add_argument(
        "--run-judge", action="store_true", help="run r79_sensor_judge into --judge-dir first"
    )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return common.run_judge(
        judge,
        args,
        script=Path(__file__).resolve(),
        old_tools=(R79_FINAL, R79_JUDGE),
        changes=DEFINITION_CHANGES,
    )


if __name__ == "__main__":
    sys.exit(main())
