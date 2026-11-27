"""Producer-form read smoke of the T8'' (5955f25b) judge readers on the edition 8 stage 4 lines.

State only (verif_t8pp.md 98-104, 127-130): every reader is run on the real C8 56849248 lines
and the result is reduced to exceptions, setting defects, not-judgeable counts and judgeable
counts. A failed / passed split, a metric value, a layer or a per-line result is never
written: a judged result is bucketed as "judgeable" (pass and fail together).

Run with dynamics-dev ``python.exe -I -B`` from the judge worktree root:
  python -I -B <this file> <judge root> <stage root> <out.json>
"""
from __future__ import annotations

import json
import sys
import traceback
from collections import Counter
from pathlib import Path

JUDGE_ROOT, STAGE_ROOT, OUT = (Path(arg) for arg in sys.argv[1:4])
MAIN = Path(r"C:\workspace\outrigger_control")
COUPLED = JUDGE_ROOT / "04_scripts" / "04_hydraulic" / "coupled"
sys.path.insert(0, str(COUPLED))

import jp3_ed8_gate_judge as gate  # noqa: E402
import jp3_ed8_judge as ed8  # noqa: E402

V0_MAIN = MAIN / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "main.jsonl"
GRID_KEYS = MAIN / "06_analysis" / "02_control" / "j_p3_cause" / "ed6_design" / "keys" / \
    "confirm_b_grid192.json"
CAUSE = MAIN / "06_analysis" / "02_control" / "j_p3_cause"
L1_KEY_FILES = {"L1": CAUSE / "prelaunch_j9" / "ed5_inputs" / "l1_keys_12b.txt",
                "L1a": CAUSE / "prelaunch_j9" / "l1_keys_d3c6c57e.json"}
PINNED_INPUTS = {
    "main_jsonl": (V0_MAIN, gate.MAIN_JSONL_SHA256),
    "p80_reference": (CAUSE / "j9_runs" / "b46bdf8f" / "repro_a2" / "ed7_probe_a2.jsonl",
                      gate.P80_REFERENCE_SHA256),
    "grid_keys": (GRID_KEYS, ed8.PINNED_SHA256["grid_keys"]),
}
STEPS = {"impl_p80": "ed7_probe_a2.jsonl", "impl_p816": "p816.jsonl", "impl_p85": "p85.jsonl",
         "impl_p88": "p88.jsonl", "impl_p815": "p815.jsonl", "impl_t8": "ed8_t8.jsonl",
         "impl_cases": "ed8_cases.jsonl"}
L1_FILES = ("L1_VBN0", "L1_VBN", "L1a_VBN0", "L1a_VBN")

report: dict = {"note": "state only: exceptions, setting_defect, not_judgeable, judgeable "
                        "counts; no pass/fail split, no values"}


def exception_text(exc: BaseException) -> dict:
    frames = traceback.extract_tb(exc.__traceback__)
    where = [f"{Path(frame.filename).name}:{frame.lineno} {frame.name}" for frame in frames[-3:]]
    return {"type": type(exc).__name__, "message": str(exc)[:300], "where": where}


def guarded(name: str, function, *args, **kwargs):
    """Run one reader; an exception is recorded under ``name`` (never re-raised)."""
    try:
        return function(*args, **kwargs), None
    except Exception as exc:  # noqa: BLE001 - every exception is a smoke finding
        report.setdefault("exceptions", []).append({"reader": name, **exception_text(exc)})
        return None, exc


def basis_state(basis: dict) -> dict:
    """Setting defects and not-judgeable counts of a basis; failures are not reported."""
    return {"setting_defects": len(basis.get("setting_defects") or []),
            "not_judgeable": len(basis.get("not_judgeable") or [])}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


# ------------------------------------------------------------------ inputs and step records
def check_inputs() -> None:
    states = {}
    for name, (path, expected) in PINNED_INPUTS.items():
        result, exc = guarded(f"pinned {name}", gate.pinned_input, path, expected, name)
        states[name] = "ok" if result else type(exc).__name__
    report["pinned_inputs"] = states
    steps = {}
    for step, name in {**STEPS, "l1ref": None}.items():
        done = STAGE_ROOT / f"{step}.done"
        outputs = ([STAGE_ROOT / f"{step}_a1" / name] if name else
                   [STAGE_ROOT / "l1ref_a1" / f"{stem}.json" for stem in L1_FILES])
        problems, _ = guarded(f"step {step}", gate.step_output_problems, done, outputs)
        steps[step] = "no problem" if problems == [] else (
            f"{len(problems)} problems" if problems else "exception")
    report["step_records"] = steps


# ------------------------------------------------------------------ census readers
def identity_state(rows: list[dict], label: str) -> None:
    found, _ = guarded(f"identity_defects {label}", ed8.identity_defects, rows)
    if found is None:
        return
    by_setting = Counter(str((entry["job"] or {}).get("setting")) for entry in found)
    report.setdefault("identity_defects", {})[label] = {
        "lines": len(rows), "lines_with_problems": len(found),
        "by_setting": dict(by_setting)}


def metrics_of(rows: list[dict], folders, label_of, name: str) -> list[dict]:
    import jp3_ed7_judge as ed7

    metrics, errors = [], 0
    for row in rows:
        metric, exc = guarded(f"metric_of {name}", ed7.metric_of, dict(row), folders,
                              label_of(row))
        if exc is None:
            metrics.append(metric)
        else:
            errors += 1
    report.setdefault("metric_of", {})[name] = {"lines": len(rows), "computed": len(metrics),
                                                "exceptions": errors}
    return metrics


def unit_state(verdicts: dict) -> dict:
    no_reference = {(str(r), str(p)) for r, p in verdicts["no_reference"]}
    counts = Counter()
    for key, unit in verdicts["units"].items():
        if unit["not_judgeable_items"] or (str(key[0]), str(key[1])) in no_reference:
            counts["not_judgeable_units"] += 1
        else:
            counts["judgeable_units"] += 1
    counts["no_reference"] = len(no_reference)
    return dict(counts)


def census_readers(t8_rows, case_rows) -> None:
    import ed8_key_lists as keys
    import jp3_ed6_judge as ed6
    import jp3_ed7_judge as ed7

    t8_path = STAGE_ROOT / "impl_t8_a1" / STEPS["impl_t8"]
    cases_path = STAGE_ROOT / "impl_cases_a1" / STEPS["impl_cases"]
    folders = tuple(ed7.t4h_folders_of(t8_path, t8_rows)) + tuple(
        ed7.t4h_folders_of(cases_path, case_rows))
    rows = t8_rows + case_rows
    identity_state(t8_rows, "impl_t8")
    identity_state(case_rows, "impl_cases")

    v0_by_job, _ = guarded("v0_rows_by_job", ed8.v0_rows_by_job, V0_MAIN)
    v0_by_job = v0_by_job or {}
    v0_lines = [v0_by_job.get(keys.plain_job_key(row["job"])) for row in rows]
    report["v0_pairs"] = {"lines": len(rows), "with_v0_main_line": sum(
        line is not None for line in v0_lines)}
    v0_unique = {keys.plain_job_key(line["job"]): line for line in v0_lines if line is not None}

    # C-J (i) as census: VBN as VB, LSN as LS<n>, V0 metrics with the census row folders
    cj_rows = [row for row in rows if row["job"]["setting"] in ed8.CJ_LABEL]
    cj_metrics = metrics_of(cj_rows, folders, lambda row: ed8.CJ_LABEL[row["job"]["setting"]],
                            "C-J lines (VBN as VB, LSN as LS)")
    v0_metrics = metrics_of(list(v0_unique.values()), folders, lambda row: ed8.V0_LABEL,
                            "V0 main lines of the same jobs")
    vb = [metric for metric in cj_metrics if metric["setting"] == ed8.TREATMENT_LABEL]
    verdicts, _ = guarded("unit_item_verdicts C-J", ed8.unit_item_verdicts, vb, v0_metrics)
    if verdicts is not None:
        report["unit_item_verdicts C-J"] = unit_state(verdicts)
    base_counts = Counter()
    for metric in v0_metrics:
        base, exc = guarded("is_base_pass", ed8.is_base_pass, metric)
        base_counts["computed" if exc is None and isinstance(base, bool) else "not computed"] += 1
    report["is_base_pass"] = dict(base_counts)

    # layers of the C-J units (6.3) from the V0 pair starts: computable or a setting defect
    layer_counts = Counter()
    for row, v0_line in zip(rows, v0_lines, strict=True):
        if row["job"]["setting"] != "VBN":
            continue
        starts = None if v0_line is None else keys.main_line_starts(v0_line)
        _, exc = guarded("layer_of", ed8.layer_of, row["job"], starts)
        layer_counts["computed" if exc is None else type(exc).__name__] += 1
    report["layer_of (VBN, V0 main starts)"] = dict(layer_counts)

    # the edition 7 C-J item path the census takes (LS against VB, groups)
    def cj_groups():
        import jp3_j9main_judge as base_judge
        import judge_stage1_4368 as path1

        rows_by = path1._by_setting(cj_metrics + v0_metrics)
        j_vs_v0 = base_judge._full_items(rows_by, (ed8.TREATMENT_LABEL,), ed8.V0_LABEL)
        ls_vs_vb = base_judge._full_items(rows_by, path1.LS_SETTINGS, ed8.TREATMENT_LABEL)
        ed7.replace_j7(ls_vs_vb, rows_by, ed8.TREATMENT_LABEL)
        ed6.apply_reading_1(ls_vs_vb, rows_by, ed8.TREATMENT_LABEL)
        ed7.replace_j7(j_vs_v0, rows_by, ed8.V0_LABEL)
        ed6.apply_reading_1(j_vs_v0, rows_by, ed8.V0_LABEL)
        groups = ed7._j9main_items(j_vs_v0, ls_vs_vb, rows_by)
        return {"ls_not_judgeable_items": sum(
            item.get("setting") in path1.LS_SETTINGS for item in groups["not_judgeable_items"]),
            "group_keys": sorted(groups)}

    groups, _ = guarded("C-J (ii) groups", cj_groups)
    if groups is not None:
        report["C-J (ii) groups"] = groups

    # J-P3 and the ③ rev 7 condition (bucketed)
    for name, part in (("impl_t8", t8_rows), ("impl_cases", case_rows)):
        jp3, _ = guarded(f"jp3_of {name}", ed8.jp3_of, part, folders)
        if jp3 is not None:
            report.setdefault("jp3_of", {})[name] = {
                **basis_state(jp3["basis"]),
                "judged_rows_equal_case_rows": (jp3["J-P3_judged_rows"] == ed8.CASE_ROWS
                                                if name == "impl_cases" else None)}

    # stats Q-2 line counts (records): forms only, no witness sums
    for name, part in (("impl_t8 VBN", [r for r in t8_rows if r["job"]["setting"] == "VBN"]),
                       ("impl_cases VBN", [r for r in case_rows
                                           if r["job"]["setting"] == "VBN"])):
        counts, _ = guarded(f"jx_line_counts {name}", ed8.jx_line_counts, part)
        if counts is not None:
            witness = counts["probe_d6_witness"]
            report.setdefault("jx_line_counts", {})[name] = {
                "lines": len(part), "j11_opportunity_lines": counts["j11_opportunity_lines"],
                "j11_opportunity_by_reason": counts["j11_opportunity_by_reason"],
                "j11_not_judgeable_lines": counts["j11_not_judgeable_lines"],
                "witness_lines_with_record": witness["lines_with_record"],
                "witness_lines_without_record": witness["lines_without_record"],
                "witness_lines_other_form": witness["lines_other_form"]}

    # C-S: the edition 7 unit table with the lines' own setting labels
    def cs_table():
        import run_v5

        own = [ed7.metric_of(dict(row), folders, row["job"]["setting"]) for row in rows]
        settings = (*run_v5.ED8_SENSITIVITY_SETTINGS, *run_v5.ED8_SENSITIVITY_RECORD_SETTINGS)
        judged = ed7.unit_table(own, v0_metrics, settings)
        verdicts = ed7.unit_verdicts(own, judged)
        states = Counter("not_judgeable" if v["verdict"] == ed7.VERDICT_MISSING else "judgeable"
                         for v in verdicts.values())
        return {"units": len(verdicts), **dict(states),
                "settings_with_no_reference": sum(bool(part["no_reference"])
                                                  for part in judged["table"].values())}

    cs, _ = guarded("C-S unit_table / unit_verdicts", cs_table)
    if cs is not None:
        report["C-S unit_table"] = cs

    # C-D: the fixed table's D line values (condition, J-P3a reads, FAULT, V0 comparison)
    grid_keys = json.loads(GRID_KEYS.read_text(encoding="utf-8"))
    d_values, _ = guarded("d_lines_of", ed7.d_lines_of, rows, folders, grid_keys, MAIN)
    if d_values is not None:
        counts = Counter()
        for value in d_values.values():
            counts["lines"] += 1
            counts["v0_comparison_missing"] += value["v0_verdict"] == ed7.VERDICT_MISSING
            counts["condition_breach_reads_none"] += value["condition_breach_reads"] is None
            counts["line_jp3a_breach_reads_none"] += value["line_jp3a_breach_reads"] is None
            counts["fault_keys_missing"] += bool(value["fault_missing_keys"])
        report["d_lines_of"] = dict(counts)
    report["d_lines_of_distinct_t4h_keys"] = None if d_values is None else len(d_values)

    # C-G: grid_line_values with the grid192 pair of the same job when there is one
    pairs = ed7.grid_pairs(grid_keys)
    g_counts = Counter()
    for row in rows:
        line = {"job": row["job"], "v0_pair": pairs.get(ed7.job_without_setting(row["job"]))}
        value, exc = guarded("grid_line_values", ed8.grid_line_values, line, row, MAIN)
        if exc is not None:
            g_counts["exception"] += 1
            continue
        g_counts["lines"] += 1
        g_counts["with_grid_pair"] += line["v0_pair"] is not None
        g_counts["v0_comparison_missing"] += value["v0_verdict"] == ed7.VERDICT_MISSING
        g_counts["fault_not_readable"] += value["fault_reasons"] is None
    report["grid_line_values"] = dict(g_counts)

    # records the census writes beside the counts
    records, _ = guarded("line_records", ed7.line_records, rows, folders)
    if records is not None:
        totals = records["totals"]
        report["line_records"] = {"lines": totals.get("lines"),
                                  "stall_not_readable": totals.get("stall_not_readable", 0),
                                  "twist_record_missing": totals.get("twist_record_missing", 0)}
    waivers, _ = guarded("waiver_lines", ed8.waiver_lines, rows)
    report["waiver_lines_ran"] = waivers is not None


# ------------------------------------------------------------------ held-out reading
def heldout_readers(t8_rows) -> None:
    import ed8_key_lists as keys
    import jp3_ed6_judge as ed6
    import jp3_ed7_judge as ed7
    import judge4368_common as common

    t8_path = STAGE_ROOT / "impl_t8_a1" / STEPS["impl_t8"]
    v0_by_job = ed8.v0_rows_by_job(V0_MAIN)
    v0_rows = list(v0_by_job.values())
    folders = tuple(ed7.t4h_folders_of(t8_path, t8_rows))
    folders += tuple(common.t4h_folders(V0_MAIN, v0_rows))
    counts = Counter()
    for row in t8_rows:
        if row["job"]["setting"] != "VBN":
            continue
        condition = v0_by_job.get(keys.plain_job_key(row["job"]))
        if condition is None:
            counts["no_condition_line"] += 1
            continue

        def one(row=row, condition=condition):
            reference = ed7.metric_of(dict(condition), folders, ed8.V0_LABEL)
            treatment = ed7.metric_of(dict(row), folders, ed8.TREATMENT_LABEL)
            treatment["row"], treatment["phase"] = reference["row"], reference["phase"]
            verdicts = ed8.unit_item_verdicts([treatment], [reference])
            unit = verdicts["units"][(reference["row"], str(reference["phase"]))]
            base = ed8.is_base_pass(reference)
            missing = ed6.missing_keys(dict(row), ed6.GRID_REQUIRED_KEYS)
            reasons = None if missing else ed6.fault_reasons(dict(row))
            return bool(unit["not_judgeable_items"]), isinstance(base, bool), reasons is None

        result, exc = guarded("heldout per-line reading", one)
        if exc is not None:
            counts["exception"] += 1
            continue
        unjudged, base_ok, fault_unread = result
        counts["lines"] += 1
        counts["not_judgeable_items"] += unjudged
        counts["base_pass_computed"] += base_ok
        counts["fault_not_readable (no grid keys)"] += fault_unread
    report["heldout per-line reading (VBN t8 vs V0 main)"] = dict(counts)
    jx, _ = guarded("heldout jx_line_counts", ed8.jx_line_counts,
                    [row for row in t8_rows if row["job"]["setting"] == "VBN"])
    report["heldout jx_line_counts ran"] = jx is not None


# ------------------------------------------------------------------ 12b on the l1ref lines
def twelve_b_readers() -> None:
    import hashlib

    import jp3_12b_judge as judge
    import jp3_12b_judge_ed7 as judge7
    import jp3_12b_judge_ed8 as judge8

    out = {}
    for stem in L1_FILES:
        path = STAGE_ROOT / "l1ref_a1" / f"{stem}.json"
        t4h_dir = path.with_name(f"{stem}_t4h")
        setting = "VBN0" if stem.endswith("VBN0") else "VBN"
        arm = "vbk0" if setting == "VBN0" else "vbk"
        entry: dict = {}
        with judge8.edition_8(), judge7.edition_7():
            # load_lines form: the L1 setting as the arm's setting for this smoke only
            saved = dict(judge.SETTING_OF_ARM)
            judge.SETTING_OF_ARM[arm] = setting
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
                expected = [judge.plain_key(row["key"]) for row in document["results"]]
                problems = judge.Problems()
                lines, exc = guarded(f"load_lines {stem}", judge.load_lines, path, t4h_dir,
                                     expected, arm, problems)
            finally:
                judge.SETTING_OF_ARM.clear()
                judge.SETTING_OF_ARM.update(saved)
            if lines is not None:
                meta_ok = 0
                for line in lines.values():
                    meta, exc = guarded(f"Line.meta {stem}", line.meta)
                    meta_ok += exc is None and isinstance(meta, dict)
                cases, _ = guarded(f"case_of {stem}",
                                   lambda: {judge.case_of(key) for key in lines})
                entry["load_lines"] = {
                    "lines": len(lines), "setting_defects": len(problems.setting_defects),
                    "not_judgeable": len(problems.not_judgeable),
                    "t4h_files_found": sum(line.t4h_path.is_file() for line in lines.values()),
                    "meta_loaded": meta_ok,
                    "distinct_cases": None if cases is None else len(cases)}
            # identity: the 12b line identity (A-4 switch read from the line or the T4h meta)
            problem_lines, exceptions = 0, 0
            for line in (lines or {}).values():
                found, exc = guarded(f"line_identity_problems {stem}",
                                     judge7.line_identity_problems, line, setting)
                exceptions += exc is not None
                problem_lines += bool(found)
            entry["line_identity_problems"] = {"lines_with_problems": problem_lines,
                                               "exceptions": exceptions}
            switch_problems = 0
            for line in (lines or {}).values():
                meta = line.meta() if line.t4h_path.is_file() else None
                view = __import__("jp3_ed7_judge").r79_identity_view(line.row, meta)
                found = ed8.ed8_settings_problems(view, __import__("jp3_ed7_judge")
                                                  .setting_identity(setting),
                                                  whole_options=False)
                switch_problems += bool(found)
            entry["A-4 ed8_settings switch problems (lines)"] = switch_problems
            # grade-judge reference check with the real key file sha256
            prefix = "L1a" if stem.startswith("L1a") else "L1"
            key_sha = hashlib.sha256(L1_KEY_FILES[prefix].read_bytes()).hexdigest()
            found, _ = guarded(f"l1_reference_problems {stem}", judge.l1_reference_problems,
                               path, arm, key_sha)
            entry["l1_reference_problems"] = None if found is None else len(found)
        out[stem] = entry
    report["12b readers on l1ref"] = out


def main() -> int:
    check_inputs()
    t8_rows = read_jsonl(STAGE_ROOT / "impl_t8_a1" / STEPS["impl_t8"])
    case_rows = read_jsonl(STAGE_ROOT / "impl_cases_a1" / STEPS["impl_cases"])
    guarded("census readers", census_readers, t8_rows, case_rows)
    guarded("heldout readers", heldout_readers, t8_rows)
    guarded("12b readers", twelve_b_readers)
    modules = {name: getattr(module, "__file__", None) for name, module in sys.modules.items()
               if name.split(".")[0] in {"jp3_ed8_judge", "jp3_ed8_gate_judge", "jp3_ed7_judge",
                                         "jp3_ed6_judge", "run_v5", "verdict_runs",
                                         "judge_stage1_4368", "judge4368_common",
                                         "jp3_12b_judge", "jp3_12b_judge_ed7",
                                         "jp3_12b_judge_ed8", "jp3_j9main_judge",
                                         "ed8_key_lists", "outrigger_sim"}}
    report["module_files_outside_judge_root"] = sorted(
        name for name, file in modules.items()
        if file and not str(Path(file).resolve()).lower().startswith(
            str(JUDGE_ROOT.resolve()).lower()))
    report["modules_checked"] = len(modules)
    report["exception_count"] = len(report.get("exceptions", []))
    OUT.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"status": "written", "exceptions": report["exception_count"],
                      "out": str(OUT)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
