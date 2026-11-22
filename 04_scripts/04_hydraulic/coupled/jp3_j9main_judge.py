"""436.9 edition 5 j9_main judge (``jp3_remedy_spec_v5.md`` 6.5, erratum 2 2-7.1): the v5
criteria stage 1 J items of the ``j9_main`` rows and their J-P3 (③ revision 6).

Sub-commands:

``v0-sample-keys`` (2-9.1) the fixed V0 sample key list: the V0 lines of ``main.jsonl``
               grouped by row (the job without ``eps`` / ``offset_s``; the G4 width grid twins
               are one row), the first and the last line of every row (24 rows, at most 48).
``v0-sample``  The V0 sample hash comparison (2-7.1, R3-E1 precedent): every job of the fixed
               V0 sample key file is in the re-run rows once (no error) and in the stored V0
               reference rows once, with the same ``commands_sha256``. Exit 0 same, 1 a
               hash differs (stop), 2 not judgeable.
``judge``      The v5 criteria 12 stage 1 judgement on path 1 (436.8 ``judge_stage1_4368``
               definitions D-07 .. D-17 and metrics, reused): the settings map VBJ -> VB and
               LSJ1 .. LSJ4 -> LS1 .. LS4 before the 436.8 tables run, so its stop settings,
               J11 (D-10, RD-10) and the LS table apply as they are.
               * ``J_vs_V0``: VB (= VBJ) against the stored V0 rows of the ``main`` batch (same
                 row, same phase); every J1 .. J11 ``fail`` counts (the 436.8 H-2 count).
               * ``LS_vs_VB``: LS (= LSJ) against VB; L-a = the J1 / J2 / J4 / J6 / J7 fails
                 of LS on the rows VB passes, L-b = the J3 / J5 fails; J11 stops (L-e / H-7).
               * L-c (2-9.4): LS limit-cycle suspicion (criteria 4 against the V0 n_rev
                 maximum of the group); L-e: LS J11 stops. L-a / L-b / L-c stop (H-6).
               * L-d: record (D-16).
               * 2-9.3: baseline failures are not counted (a J item fails only where V0 passes;
                 except R15: worse than V0 and "구분됨" = a J2 failure, weak basis); S8: the
                 criteria 6 clause alone is ``F-5 기록``, another SA-4 item fails, the clause
                 margin < -6.92 kN / post-stop maximum > 14.21 kN stops; phase-scatter
                 suspects (a VBJ failure with the item failing in another V0 phase of the row)
                 are failures, counted and listed (H-2).
               * J-P3 (2-7.1 3): the rev 6 rows (VBJ, LSJ1 .. LSJ4) through
                 ``j_p3_inputs.j_p3_over_rows`` (the run's ③ revision from its tag, its record
                 ``extend_bound_check``, the rod reading of its T4h, the head-only declaration);
                 the 436.8 per-line J-P3 item is left out here (one J-P3 judgement).
               Input refusals: the rows are not exactly the ``run_v5`` ``j9_main`` jobs, an error
               line, a row of another setting, a VBJ / LSJ row without a V0 / VB reference.

======  =================  =================================================================
exit    status             meaning
======  =================  =================================================================
0       ``pass``           VB J1 .. J11 failures 0, L-a / L-b 0, no J11 stop, J-P3 pass
1       ``failed``         a J failure, an L-a / L-b violation, a J11 stop, J-P3 H-7
2       ``setting_defect`` J-P3 setting defect / rev 5 rows; ``not_judgeable`` (inputs, 0
                           judged J-P3 rows, a not-judgeable J item), an existing ``--out``
3       ``error``          a tool error
======  =================  =================================================================

Usage (dynamics-dev or python-dev with the harness packages; project root):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_j9main_judge.py judge --rows <j9_main.jsonl>
      --v0 <stored V0 rows> --v0-sha256 <sha> --out <report.json>
  python -I -B ... v0-sample --sample-keys <keys.json> --sample <rerun.jsonl>
      --v0 <stored V0 rows> --v0-sha256 <sha> --out <report.json>
The stdout's last line is JSON with ``status``, the counts and the report path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

EXIT_PASS, EXIT_FAILED, EXIT_STOP, EXIT_ERROR = 0, 1, 2, 3
SETTING_MAP = {"VBJ": "VB", "LSJ1": "LS1", "LSJ2": "LS2", "LSJ3": "LS3", "LSJ4": "LS4"}
"""Erratum 2 2-7.1 2: the 436.8 settings the j9_main settings take."""
V0_SETTING = "V0"
L_A_ITEMS = ("J1", "J2", "J4", "J6", "J7")
L_B_ITEMS = ("J3", "J5")
J_P3_ITEM = "J-P3"
EXIT_OF_STATUS = {"pass": EXIT_PASS, "same": EXIT_PASS, "written": EXIT_PASS,
                  "failed": EXIT_FAILED,
                  "differs": EXIT_FAILED, "setting_defect": EXIT_STOP,
                  "not_judgeable": EXIT_STOP}


class NotJudgeable(Exception):
    """An input defect (exit 2)."""


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]


def stored_v0_rows(path: Path, expected_sha256: str) -> list[dict]:
    """The V0 lines of the ``main`` batch of the stored file (its sha256 given).

    Raises:
        NotJudgeable: Another sha256, or no V0 line.
    """
    import run_v5

    if file_sha256(path) != expected_sha256:
        raise NotJudgeable(f"--v0 {path} is not of the given sha256")
    main_keys = {run_v5.job_key(job) for job in run_v5.batch_jobs("main")}
    rows = [row for row in read_rows(path)
            if (row.get("job") or {}).get("setting") == V0_SETTING and "error" not in row
            and run_v5.job_key(row["job"]) in main_keys]
    if not rows:
        raise NotJudgeable(f"--v0 {path} has no V0 line of the main batch")
    return rows


# ------------------------------------------------------------------------------- V0 sample
PHASE_FIELDS = ("eps", "offset_s")
"""Erratum 2 2-9.1: the phase fields a row (job identity) leaves out."""
RUNTIME_JOB_FIELDS = ("mask", "t4h_dir")
V0_SAMPLE_ROWS = 24
"""2-9.1: required 13 + regression 11 rows."""


def _row_identity(job: dict) -> str:
    """The row of a job: without its phase fields; the G4 width grid's ``twin`` (14 twins x 2
    offsets, criteria 5 "G4 폭 격자", one row) counts as a phase too, only its presence is
    kept (with it the 100 V0 lines are the 24 rows of 2-9.1)."""
    identity = {k: v for k, v in job.items() if k not in (*PHASE_FIELDS, *RUNTIME_JOB_FIELDS)}
    if "twin" in identity:
        identity["twin"] = "G4 width grid"
    return json.dumps(identity, sort_keys=True)


def v0_sample_keys(v0_path: Path, v0_sha256: str) -> dict:
    """2-9.1: the V0 lines of ``main.jsonl`` grouped by row (the job without its phase fields),
    file order inside a row; the first and the last line of every row (one line: that one).

    Raises:
        NotJudgeable: Another sha256, or not 24 rows / more than 48 jobs.
    """
    rows: dict[str, list[dict]] = {}
    for line in stored_v0_rows(v0_path, v0_sha256):
        job = {k: v for k, v in line["job"].items() if k not in RUNTIME_JOB_FIELDS}
        rows.setdefault(_row_identity(job), []).append(job)
    jobs = []
    for group in rows.values():
        jobs += [group[0]] if len(group) == 1 else [group[0], group[-1]]
    if len(rows) != V0_SAMPLE_ROWS or len(jobs) > 2 * V0_SAMPLE_ROWS:
        raise NotJudgeable(f"{len(rows)} V0 rows ({V0_SAMPLE_ROWS} expected), {len(jobs)} jobs")
    return {"rule": "jp3_remedy_spec_v5_erratum2.md 2-9.1 (R3-E1 precedent: first and last line "
                    "of every row)",
            "source": {"path": str(v0_path), "sha256": v0_sha256},
            "rows": len(rows), "jobs": jobs}


def v0_sample(keys_path: Path, sample_path: Path, v0_path: Path, v0_sha256: str) -> dict:
    """``v0-sample`` (module docstring)."""
    import run_v5

    keys = json.loads(Path(keys_path).read_text(encoding="utf-8"))
    jobs = keys["jobs"] if isinstance(keys, dict) else keys
    wanted = [run_v5.job_key(job) for job in jobs]
    if not wanted or any((job.get("setting") != V0_SETTING) for job in jobs):
        raise NotJudgeable("the sample key file names no job or a job not of V0")
    stored = {run_v5.job_key(row["job"]): row for row in stored_v0_rows(v0_path, v0_sha256)}
    rerun: dict[str, list[dict]] = {}
    for row in read_rows(sample_path):
        rerun.setdefault(run_v5.job_key(row["job"]), []).append(row)
    problems, differing = [], []
    for key in wanted:
        if key not in stored:
            problems.append(f"{key}: no stored V0 line")
            continue
        found = rerun.get(key) or []
        if len(found) != 1 or "error" in found[0]:
            problems.append(f"{key}: {len(found)} re-run lines (one without an error expected)")
            continue
        if found[0].get("commands_sha256") != stored[key].get("commands_sha256"):
            differing.append(key)
    extra = sorted(set(rerun) - set(wanted))
    problems += [f"{key}: re-run line outside the sample" for key in extra]
    status = "not_judgeable" if problems else ("differs" if differing else "same")
    return {"rule": "erratum 2 2-7.1 V0 sample hash (R3-E1 precedent)", "status": status,
            "sample_jobs": len(wanted), "differing": differing, "problems": problems,
            "inputs": {"sample_keys": {"path": str(keys_path),
                                       "sha256": file_sha256(keys_path)},
                       "sample": {"path": str(sample_path), "sha256": file_sha256(sample_path)},
                       "v0": {"path": str(v0_path), "sha256": v0_sha256}}}


# ------------------------------------------------------------------------------- judge
def check_rows(rows: list[dict]) -> None:
    """The rows are exactly the ``j9_main`` jobs, each once, without an error line.

    Raises:
        NotJudgeable: Module docstring input refusals.
    """
    import run_v5

    expected = Counter(run_v5.job_key(job) for job in run_v5.j9_main_jobs())
    found = Counter(run_v5.job_key(row["job"]) for row in rows)
    problems = []
    if found != expected:
        missing, extra = expected - found, found - expected
        problems.append(f"rows are not the j9_main jobs ({sum(missing.values())} missing, "
                        f"{sum(extra.values())} extra or repeated)")
    errors = sum("error" in row for row in rows)
    if errors:
        problems.append(f"{errors} error lines")
    other = sorted({str(row["job"].get("setting")) for row in rows
                    if row["job"].get("setting") not in SETTING_MAP})
    if other:
        problems.append(f"rows of settings {other}")
    if problems:
        raise NotJudgeable("; ".join(problems))


def _metric_rows(rows: list[dict], folders: tuple[Path, ...], *, relabel: bool) -> list[dict]:
    import judge_stage1_4368 as path1

    out = []
    for row in rows:
        metric = path1.metrics(row, folders)
        if relabel:
            metric["setting"] = SETTING_MAP[metric["setting"]]
        out.append(metric)
    return out


def _without_line_j_p3(table: dict) -> dict:
    """The 436.8 table without its per-line J-P3 items (one J-P3 judgement, 2-7.1 3)."""
    out = {}
    for setting, part in table.items():
        items = [item for item in part["items"] if item["item"] != J_P3_ITEM]
        out[setting] = {**part, "items": items,
                        "by_kind": dict(Counter(item["kind"] for item in items)),
                        "by_item": dict(Counter(f"{item['item']}:{item['kind']}"
                                                for item in items))}
    return out


def _full_items(rows_by: dict, settings: tuple[str, ...], reference: str) -> dict:
    """``judge_stage1_4368.j_table`` without its 300-item cut (every item judged here)."""
    import judge_stage1_4368 as path1

    base = {(r["row"], r["phase"]): r for r in rows_by.get(reference, [])}
    groups: dict[str, list[dict]] = {}
    for row in rows_by.get(reference, []):
        groups.setdefault(row["group"], []).append(row)
    n_rev_max = {g: max(r["n_rev"] for r in rs) for g, rs in groups.items()}
    out = {}
    for setting in settings:
        items, missing = [], []
        for row in rows_by.get(setting, []):
            ref = base.get((row["row"], row["phase"]))
            if ref is None:
                missing.append([row["row"], row["phase"]])
                continue
            items += [{"row": row["row"], "phase": row["phase"], **item}
                      for item in path1.j_items(ref, row, groups[row["group"]],
                                                n_rev_max[row["group"]])]
        out[setting] = {"runs": len(rows_by.get(setting, [])), "no_reference": missing,
                        "items": items}
    return _without_line_j_p3(out)


def j_p3_rows(rows: list[dict], folders: tuple[Path, ...]) -> list[dict]:
    """The ``j_p3_inputs.j_p3_over_rows`` rows of the j9_main lines (2-7.1 3)."""
    import judge_stage1_4368 as path1
    from j_p3_inputs import P3_RULE, REVISION_KEY, RULE_KEY, is_p3_expected

    from outrigger_sim.hydraulics.v5_options import extend_start_revision_of_tag

    out = []
    for row in rows:
        tag = row.get("controller_tag")
        revision = extend_start_revision_of_tag(tag)
        hydraulics = row.get("hydraulics_record") or {}
        reading = path1.rod_reading(row, folders)
        declared = row.get("head_only_declared")
        if declared is None:
            declared = (not row.get("event_output")) and (
                path1.old.row_name(row["job"]) in path1.STEADY_PATH_ROWS)
        entry = {"setting": row["job"]["setting"], "p3_expected": is_p3_expected(
                     tag, row["job"]["setting"]),
                 "extend_bound_check": hydraulics.get("extend_bound_check"),
                 "has_rod_reading": bool(reading), "head_only_declared": bool(declared)}
        if revision is not None:
            entry.update({RULE_KEY: P3_RULE, REVISION_KEY: revision})
        out.append(entry)
    return out


def judge(rows_path: Path, v0_path: Path, v0_sha256: str) -> dict:
    """``judge`` (module docstring)."""
    import judge4368_common as common
    import judge_stage1_4368 as path1
    from j_p3_inputs import j_p3_over_rows

    rows = read_rows(rows_path)
    check_rows(rows)
    v0 = stored_v0_rows(v0_path, v0_sha256)
    folders = tuple(common.t4h_folders(rows_path, rows))
    v0_folders = tuple(common.t4h_folders(v0_path, v0))
    metrics = _metric_rows(rows, folders, relabel=True) + _metric_rows(v0, v0_folders,
                                                                        relabel=False)
    rows_by = path1._by_setting(metrics)
    j_vs_v0 = _full_items(rows_by, (path1.JUDGED_SETTING,), V0_SETTING)
    ls_vs_vb = _full_items(rows_by, path1.LS_SETTINGS, path1.JUDGED_SETTING)
    vb_items = j_vs_v0[path1.JUDGED_SETTING]["items"]
    vb_failed_rows = {(i["row"], i["phase"]) for i in vb_items if i["kind"] == "fail"}
    l_a = [dict(i, setting=s) for s, part in ls_vs_vb.items() for i in part["items"]
           if i["kind"] == "fail" and i["item"] in L_A_ITEMS
           and (i["row"], i["phase"]) not in vb_failed_rows]
    l_b = [dict(i, setting=s) for s, part in ls_vs_vb.items() for i in part["items"]
           if i["kind"] == "fail" and i["item"] in L_B_ITEMS]
    l_c = limit_cycle_suspects(rows_by)
    stops = [dict(i, setting=s) for table in (j_vs_v0, ls_vs_vb) for s, part in table.items()
             for i in part["items"] if i["kind"] == "stop"]
    l_e = [item for item in stops if item["setting"] in path1.LS_SETTINGS
           and item["item"] == "J11"]
    s8 = s8_items(rows_by)
    stops += s8["stops"]
    r15 = r15_worsening(rows_by)
    r15_baseline = r15_baseline_failures(rows_by)
    unjudgeable = [dict(i, setting=s) for table in (j_vs_v0, ls_vs_vb)
                   for s, part in table.items() for i in part["items"]
                   if i["kind"] == "not_judgeable"]
    no_reference = {f"{table_name} {s}": part["no_reference"]
                    for table_name, table in (("J_vs_V0", j_vs_v0), ("LS_vs_VB", ls_vs_vb))
                    for s, part in table.items() if part["no_reference"]}
    jp3 = j_p3_over_rows(j_p3_rows(rows, folders))
    report = {"rule": "jp3_remedy_spec_v5.md 6.5, erratum 2 2-7.1 (path 1, 436.8 D-07 .. D-17)",
              "setting_map": SETTING_MAP, "rows": len(rows), "v0_rows": len(v0),
              "inputs": {"rows": {"path": str(rows_path), "sha256": file_sha256(rows_path)},
                         "v0": {"path": str(v0_path), "sha256": v0_sha256}},
              "J_vs_V0": j_vs_v0, "LS_vs_VB": ls_vs_vb,
              "L-d": {s: path1.l_d(rows_by.get(path1.JUDGED_SETTING, []), rows_by.get(s, []))
                      for s in path1.LS_SETTINGS},
              "vb_fail_items": sum(i["kind"] == "fail" for i in vb_items),
              "baseline_failures": {
                  "counted": 0, "rule": "2-9.3: a J item fails only where the paired V0 passes "
                  "it (D-07 .. D-17 by construction); a V0 failure is never a VBJ failure, "
                  "except the R15 worsening rule on J2 (r15_worsening); V0's other R15 "
                  "failures are listed here (recorded only)",
                  "R15": r15_baseline, "R15_count": len(r15_baseline)},
              "phase_scatter_suspects": [i for i in vb_items if i["kind"] == "fail"
                                         and i["base_other_phase_has_it"]],
              "r15_worsening": r15, "S8": s8,
              "L-a": l_a, "L-b": l_b, "L-c": l_c, "L-e": l_e, "stops": stops,
              "not_judgeable_items": unjudgeable + s8["not_judgeable"],
              "no_reference": no_reference, "J-P3": jp3}
    report["phase_scatter_suspect_count"] = len(report["phase_scatter_suspects"])
    report["status"] = _status(report)
    return report


def _status(report: dict) -> str:
    jp3_status = report["J-P3"]["status"]
    if report["no_reference"] or report["not_judgeable_items"] or jp3_status in (
            "no_judged_runs", "judged_key_missing", "no_p3_runs"):
        return "not_judgeable"
    if jp3_status == "setting_defect":
        return "setting_defect"
    if (report["vb_fail_items"] or report.get("r15_worsening", {}).get("failures")
            or report.get("S8", {}).get("failures") or report["L-a"] or report["L-b"]
            or report.get("L-c") or report["stops"] or jp3_status == "H-7"):
        return "failed"
    return "pass"


# ------------------------------------------------------------------------------- 2-9.3 / 2-9.4
LIMIT_CYCLE_FACTOR = 2
LIMIT_CYCLE_MARGIN = 6
"""Criteria 4 (2-9.4 L-c): n_rev >= 2 n_rev_off_max and n_rev >= n_rev_off_max + 6."""
F5_STOP_MARGIN_KN = -6.92
F5_STOP_MAX_AFTER_KN = 14.21
"""Criteria 6: clause margin < -6.92 kN or post-stop maximum > 14.21 kN stops."""
R15_ROW = "R15"


def limit_cycle_suspects(rows_by: dict) -> list[dict]:
    """L-c: LS rows whose ``n_rev`` meets the criteria 4 limit-cycle rule against the largest
    V0 ``n_rev`` of the same group (the flow-off maximum)."""
    import judge_stage1_4368 as path1

    off_max: dict[str, int] = {}
    for row in rows_by.get(V0_SETTING, []):
        off_max[row["group"]] = max(off_max.get(row["group"], 0), row["n_rev"])
    suspects = []
    for setting in path1.LS_SETTINGS:
        for row in rows_by.get(setting, []):
            reference = off_max.get(row["group"])
            if reference is None:
                continue
            if (row["n_rev"] >= LIMIT_CYCLE_FACTOR * reference
                    and row["n_rev"] >= reference + LIMIT_CYCLE_MARGIN):
                suspects.append({"setting": setting, "row": row["row"], "phase": row["phase"],
                                 "n_rev": row["n_rev"], "n_rev_off_max": reference})
    return suspects


def s8_items(rows_by: dict) -> dict:
    """2-9.3 F-5 on the S8 lines of VB (= VBJ) and LS (= LSJ): the criteria 6 clause alone
    failing is ``F-5 기록`` (flow-on settings, not a failure); another SA-4 item failing is a
    failure; the clause margin < -6.92 kN or the post-stop maximum > 14.21 kN stops; a SA-4
    item without a record is not judgeable."""
    import judge_stage1_4368 as path1

    out = {"f5_records": [], "failures": [], "stops": [], "not_judgeable": []}
    for setting in (path1.JUDGED_SETTING, *path1.LS_SETTINGS):
        for row in rows_by.get(setting, []):
            if row["row"] != path1.S8_ROW:
                continue
            sa4 = path1.sa4_items(row)
            where = {"setting": setting, "row": row["row"], "phase": row["phase"]}
            if sa4["state"] == "fail":
                out["failures"].append({**where, "item": "SA-4", "kind": "fail",
                                        "detail": [k for k, v in sa4["items"].items() if not v]})
            elif sa4["state"] != "pass":
                out["not_judgeable"].append({**where, "item": "SA-4", "kind": "not_judgeable",
                                             "detail": "a SA-4 item without a record"})
            crawler = row.get("s8") or {}
            margin, after = crawler.get("margin_at_stop_kN"), crawler.get("max_after_stop_kN")
            if margin is not None and margin < 0:
                out["f5_records"].append({**where, "margin_at_stop_kN": margin})
            if (margin is not None and margin < F5_STOP_MARGIN_KN) or (
                    after is not None and after > F5_STOP_MAX_AFTER_KN):
                out["stops"].append({**where, "item": "F-5", "kind": "stop",
                                     "detail": "criteria 6 stop value"})
    return out


def r15_worsening(rows_by: dict) -> dict:
    """2-9.3 exception: R15 (criteria 5 "V0 실패, 나빠짐만 판정", the minimum force): VBJ fails
    when its J2 value (E-3 for a rigid event row) is below V0's and the ``m1_criteria`` 5 phase
    test says "구분됨" (2 phases: a weak basis)."""
    import judge_stage1_4368 as path1

    pairs = []
    vb = {r["phase"]: r for r in rows_by.get(path1.JUDGED_SETTING, []) if r["row"] == R15_ROW}
    for row in rows_by.get(V0_SETTING, []):
        if row["row"] == R15_ROW and row["phase"] in vb:
            pairs.append((path1._j2_value_N(row), path1._j2_value_N(vb[row["phase"]])))
    usable = [(a, b) for a, b in pairs if a is not None and b is not None]
    if not usable:
        return {"pairs": len(pairs), "state": "판정 불가" if pairs else "no R15 pair",
                "failures": []}
    scatter = path1.phase_scatter([a for a, _ in usable], [b for _, b in usable])
    worse = scatter["state"] == "구분됨" and scatter["E"] < 0
    return {"pairs": len(pairs), "scatter": scatter, "weak_basis": True,
            "failures": [{"row": R15_ROW, "item": "J2", "kind": "fail",
                          "detail": "R15 worsening (구분됨)"}] if worse else []}


R15_WORSENING_ITEM = "J2"
"""Erratum 2 final 2-9.3: the one R15 item judged by worsening; V0's other R15 failures are
baseline failures (recorded only)."""


def own_item_failures(row: dict) -> list[dict]:
    """The J items a metric row fails on its own: the "V0 passes" premise of the 436.8 path-1
    definitions (D-07 .. D-17; J1 / J2 / J3 of ``judge_stage1_4368``, J4 / J5 / J6 / J10 of
    ``judge_stage1_r5.J_fails``) is false for it. J7 / J8 / J9 / J11 have no such premise."""
    import judge4368_common as common
    import judge_stage1_4368 as path1

    old = path1.old
    out = []

    def add(item: str, detail: str) -> None:
        out.append({"item": item, "detail": detail})

    if row["is_event"]:
        for gate in row["gates"]:
            add("J1", f"gate {gate}")
        if row["t_back"] is None or row["t_back"] > old.RETURN_LIMIT:
            add("J5", f"t_back {row['t_back']}")
        if row["att_end"] is not None and row["att_end"] > old.ATT_LIMIT:
            add("J6", f"att_end {row['att_end']}")
        if row["p_move_ev"] is not None and row["p_move_ev"] > old.P_MOVE:
            add("J10", f"p_move_out {row['p_move_ev']}")
    else:
        if row["row"] != path1.S8_ROW and row["class"] not in path1.PASSING_CLASSES:
            add("J1", f"class {row['class']}")
        if row["row"] in path1.SOIL_READY_ROWS and (
                row["t_ready"] is None
                or common.is_above(row["t_ready"], path1.SOIL_READY_LIMIT_S)):
            add("J3", f"t_ready {row['t_ready']}")
        if row["att_last5"] is None or row["att_last5"] > old.ATT_LIMIT:
            add("J6", f"att_last5 {row['att_last5']}")
        if row["p_move"] is not None and row["p_move"] > old.P_MOVE:
            add("J10", f"p_move {row['p_move']}")
    if not common.is_at_least(path1._j2_value_N(row), common.F_MIN_N):
        add("J2", f"F {path1._j2_value_N(row)} N")
    j4_reasons = [f"final {row['final']}"] if row["final"] != "ready" else []
    if not row["is_event"] and row["t_ready"] is None:
        j4_reasons.append("no first READY")
    if j4_reasons:
        add("J4", ", ".join(j4_reasons))
    return out


def r15_baseline_failures(rows_by: dict) -> list[dict]:
    """2-9.3: V0's R15 failures other than J2, per (phase, item) of every V0 / VBJ R15 pair - a
    baseline failure (recorded, never counted); ``vbj_also_fails`` is the VBJ row's own state."""
    import judge_stage1_4368 as path1

    vb = {r["phase"]: r for r in rows_by.get(path1.JUDGED_SETTING, []) if r["row"] == R15_ROW}
    out = []
    for row in rows_by.get(V0_SETTING, []):
        if row["row"] != R15_ROW or row["phase"] not in vb:
            continue
        vbj_items = {failure["item"] for failure in own_item_failures(vb[row["phase"]])}
        for failure in own_item_failures(row):
            if failure["item"] == R15_WORSENING_ITEM:
                continue
            out.append({"row": R15_ROW, "phase": row["phase"], **failure,
                        "kind": "baseline_failure",
                        "vbj_also_fails": failure["item"] in vbj_items})
    return out


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    judged = sub.add_parser("judge")
    judged.add_argument("--rows", type=Path, required=True)
    sample = sub.add_parser("v0-sample")
    sample.add_argument("--sample-keys", type=Path, required=True)
    sample.add_argument("--sample", type=Path, required=True)
    keys = sub.add_parser("v0-sample-keys", help="write the fixed V0 sample key list (2-9.1)")
    for command in (judged, sample, keys):
        command.add_argument("--v0", type=Path, required=True)
        command.add_argument("--v0-sha256", required=True)
        command.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.out.exists():
        print(json.dumps({"status": "not_judgeable", "reason": "--out exists"}))
        return EXIT_STOP
    try:
        if args.command == "judge":
            report = judge(args.rows, args.v0, args.v0_sha256)
        elif args.command == "v0-sample-keys":
            report = {"status": "written", **v0_sample_keys(args.v0, args.v0_sha256)}
        else:
            report = v0_sample(args.sample_keys, args.sample, args.v0, args.v0_sha256)
    except NotJudgeable as exc:
        report = {"status": "not_judgeable", "reason": str(exc)}
    except Exception as exc:  # noqa: BLE001 (every other failure is a tool error)
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(json.dumps({"status": "error"}))
        return EXIT_ERROR
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, default=str)
    print(json.dumps({"status": report["status"], "out": str(args.out)}))
    return EXIT_OF_STATUS[report["status"]]


if __name__ == "__main__":
    sys.exit(main())
