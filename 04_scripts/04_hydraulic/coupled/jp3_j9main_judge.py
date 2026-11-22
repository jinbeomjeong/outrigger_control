"""436.9 edition 5 j9_main judge (``jp3_remedy_spec_v5.md`` 6.5, erratum 2 2-7.1): the v5
criteria stage 1 J items of the ``j9_main`` rows and their J-P3 (③ revision 6).

Sub-commands:

``v0-sample-keys`` (2-9.1) the fixed V0 sample key list: the V0 lines of ``main.jsonl``
               grouped by row (the job without ``eps`` / ``offset_s``; the G4 width grid twins
               are one row), the first and the last line of every row (24 rows, at most 48).
``v0-sample``  The V0 sample hash comparison (2-7.1, R3-E1 precedent): every job of the fixed
               V0 sample key file is in the re-run rows once (no error) and in the stored V0
               reference rows once, with the same ``commands_sha256``. Exit 0 same, 1 a
               hash differs (stop; also with other problems, 2-10), 2 not judgeable.
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
                 except R15: worse than V0 and "구분됨" = a J2 failure, weak basis; an R15
                 worsening without pairs or values is not judgeable, H-1); every pair's
                 reference failures are recorded (``baseline_failures``, H-3); S8: the
                 criteria 6 clause alone is ``F-5 기록``, another SA-4 item fails, the clause
                 margin < -6.92 kN / post-stop maximum > 14.21 kN stops; phase-scatter
                 suspects (a VBJ failure with the item failing in another V0 phase of the row)
                 are failures, counted and listed (H-2).
               * J-P3 (2-7.1 3): the rev 6 rows (VBJ, LSJ1 .. LSJ4) through
                 ``j_p3_inputs.j_p3_over_rows`` (the run's ③ revision from its tag, its record
                 ``extend_bound_check``, the rod reading of its T4h, the head-only declaration);
                 the 436.8 per-line J-P3 item is left out here (one J-P3 judgement).
               * H-2: every VBJ / LSJ line is ③ rev 6 (tag base ``final_C4G2_P3W``, the run's
                 revision 6, a ③ record's ``rule_revision`` 6 and ``spec_edition`` fe6f5844).
               Input refusals: the rows are not exactly the ``run_v5`` ``j9_main`` jobs, an error
               line, a row of another setting, a VBJ / LSJ row without a V0 / VB reference.
               Status (erratum 2 2-10, ``status_basis`` keeps every reason): failed > setting
               defect > not judgeable > pass.

======  =================  =================================================================
exit    status             meaning
======  =================  =================================================================
0       ``pass``           no failure, no setting defect, no not-judgeable reason
1       ``failed``         a VBJ J1 .. J11 failure, R15 worsening, S8 SA-4, L-a / L-b / L-c,
                           a stop (J11 H-7 / L-e, criteria 6 F-5), J-P3 H-7 - whatever else
                           was found (the reasons are kept, 2-10)
2       ``setting_defect`` no failure; a rev 6 identity defect (H-2) or a J-P3 setting defect
2       ``not_judgeable``  no failure, no defect; ``no_reference``, a not-judgeable item (R15
                           worsening without pairs / values, L-c without a V0 maximum, an S8
                           stop value None), J-P3 without judged rows, 0 VBJ rows; an input
                           refusal (before any item is judged) or an existing ``--out``
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
    # erratum 2 2-10: a differing hash is a failure whatever the other problems (all kept)
    status = "differs" if differing else ("not_judgeable" if problems else "same")
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
    unjudgeable = [dict(i, setting=s) for table in (j_vs_v0, ls_vs_vb)
                   for s, part in table.items() for i in part["items"]
                   if i["kind"] == "not_judgeable"]
    unjudgeable += s8["not_judgeable"] + l_c["not_judgeable"] + r15_not_judgeable(r15)
    no_reference = {f"{table_name} {s}": part["no_reference"]
                    for table_name, table in (("J_vs_V0", j_vs_v0), ("LS_vs_VB", ls_vs_vb))
                    for s, part in table.items() if part["no_reference"]}
    jp3 = j_p3_over_rows(j_p3_rows(rows, folders), edition5_order=True)  # 2-10.1 5
    report = {"rule": "jp3_remedy_spec_v5.md 6.5, erratum 2 2-7.1 (path 1, 436.8 D-07 .. D-17)",
              "setting_map": SETTING_MAP, "rows": len(rows), "v0_rows": len(v0),
              "inputs": {"rows": {"path": str(rows_path), "sha256": file_sha256(rows_path)},
                         "v0": {"path": str(v0_path), "sha256": v0_sha256}},
              "J_vs_V0": j_vs_v0, "LS_vs_VB": ls_vs_vb,
              "L-d": {s: path1.l_d(rows_by.get(path1.JUDGED_SETTING, []), rows_by.get(s, []))
                      for s in path1.LS_SETTINGS},
              "vb_fail_items": sum(i["kind"] == "fail" for i in vb_items),
              "identity_defects": identity_defects(rows),
              "baseline_failures": baseline_failures(rows_by),
              "phase_scatter_suspects": [i for i in vb_items if i["kind"] == "fail"
                                         and i["base_other_phase_has_it"]],
              "r15_worsening": r15, "S8": s8,
              "L-a": l_a, "L-b": l_b, "L-c": l_c["suspects"], "L-e": l_e, "stops": stops,
              "not_judgeable_items": unjudgeable,
              "no_reference": no_reference, "J-P3": jp3}
    report["phase_scatter_suspect_count"] = len(report["phase_scatter_suspects"])
    report["status_basis"] = status_basis(report)
    report["status"] = _status(report)
    return report


JP3_NOT_JUDGEABLE = ("no_judged_runs", "judged_key_missing", "no_p3_runs")
"""J-P3 statuses with no judged row (2-10: a reason, never a pass)."""
JP3_ROW_DEFECT_COUNTS = ("rule_missing_runs", "test_only_setting_runs", "l1_reference_runs",
                         "revision_key_missing_runs", "revision_key_mismatch_runs")
"""``j_p3_over_rows`` row-level setting defect counts (kept as reasons under an H-7)."""


def status_basis(report: dict) -> dict[str, list[str]]:
    """Erratum 2 2-10: every counted failure, setting defect and not-judgeable reason of one
    judgement, all kept (a failure never hides the reasons, the reasons never hide it).

    Failures: VBJ J1 .. J11, the R15 worsening, the S8 SA-4 items, L-a / L-b / L-c, the stops
    (J11 H-7 / L-e, the criteria 6 F-5 stop values) and J-P3 H-7 (2-10.1 5: overall, of one
    revision, or a judged row with a breach read from the revision judgement).
    Setting defects: the rev 6 identity (H-2) and a J-P3 setting defect (overall, of one
    revision's own judgement, or a row-level count). Not judgeable: ``no_reference``, the
    not-judgeable items, a J-P3 status without judged rows (overall or of a hold revision's
    own judgement; an empty revision 4 side alone is not a reason) and 0 VBJ rows.
    """
    from j_p3_inputs import HOLD_REVISIONS, has_judged_breach

    jp3 = report["J-P3"]
    revision_statuses = set((jp3.get("status_by_revision") or {}).values())
    hold_judgements = [jp3.get(f"rev{revision}") or {} for revision in HOLD_REVISIONS]
    own_statuses = {judgement.get("status") for judgement in hold_judgements}
    is_h7 = (jp3["status"] == "H-7" or "H-7" in revision_statuses
             or any(has_judged_breach(judgement) for judgement in hold_judgements))
    counted = {"VBJ J1 .. J11": report["vb_fail_items"],
               "R15 worsening (J2)": len(report["r15_worsening"]["failures"]),
               "S8 SA-4": len(report["S8"]["failures"]),
               "L-a": len(report["L-a"]), "L-b": len(report["L-b"]), "L-c": len(report["L-c"]),
               "stops (J11 H-7 / L-e, criteria 6 F-5)": len(report["stops"]),
               "J-P3 H-7": int(is_h7)}
    failures = [f"{name}: {count}" for name, count in counted.items() if count]
    defects = []
    if report["identity_defects"]:
        defects.append(f"rev 6 identity (H-2): {len(report['identity_defects'])} lines")
    row_defects = sum(jp3.get(key) or 0 for key in JP3_ROW_DEFECT_COUNTS)
    if (jp3["status"] == "setting_defect" or "setting_defect" in own_statuses | revision_statuses
            or row_defects):
        defects.append("J-P3 setting_defect")
    not_judgeable = []
    if report["no_reference"]:
        not_judgeable.append(f"no_reference: {sum(map(len, report['no_reference'].values()))}")
    if report["not_judgeable_items"]:
        not_judgeable.append(f"not-judgeable items: {len(report['not_judgeable_items'])}")
    unjudged = sorted({status for status in {jp3["status"], *own_statuses}
                       if status in JP3_NOT_JUDGEABLE} - {None})
    for status in unjudged:
        not_judgeable.append(f"J-P3 {status}")
    if not report["J_vs_V0"].get("VB", {}).get("runs"):
        not_judgeable.append("0 judged VBJ rows")
    return {"failures": failures, "setting_defects": defects, "not_judgeable": not_judgeable}


def _status(report: dict) -> str:
    """2-10: failed (exit 1) > setting_defect > not_judgeable (exit 2) > pass."""
    basis = report["status_basis"]
    if basis["failures"]:
        return "failed"
    if basis["setting_defects"]:
        return "setting_defect"
    if basis["not_judgeable"]:
        return "not_judgeable"
    return "pass"


# ------------------------------------------------------------------------------- H-2 identity
WITNESS_REVISION = 6
WITNESS_BASE_TAG = "final_C4G2_P3W"
WITNESS_SPEC_EDITION = "fe6f5844"
"""Erratum 2 2-7.2 (re-audit H-2): the rev 6 identity of every VBJ / LSJ line."""
WITNESS_OPTION_KEYS = ("extend_start_tracked", "extend_start_hold", "extend_start_witness")
"""``hydraulic_options`` flags of a ③ revision 6 run (``v5_options.HydraulicOptions``)."""


def line_identity_problems(row: dict) -> list[str]:
    """H-2 on one line (erratum 2 2-10.1 1 / 3): the tag base is ``final_C4G2_P3W`` and names
    revision 6; the revision mark: ``run_extend_start_revision`` 6 when the line has the key
    (run_v5 lines do not write it), else the three ``hydraulic_options`` flags all true, and a
    key with ``hydraulic_options`` that disagree is a defect too; a ③ record
    (``hydraulics_record.extend_bound_check``) has ``rule_revision`` 6 and ``spec_edition``
    fe6f5844. A line without a record (None) skips the record items only - declared head-only
    or not, its J-P3 is the run-case table's - the tag and the revision mark are checked."""
    from j_p3_inputs import REVISION_KEY

    from outrigger_sim.hydraulics.v5_options import extend_start_revision_of_tag, switch_base_tag

    problems = []
    tag = row.get("controller_tag")
    if not isinstance(tag, str) or switch_base_tag(tag) != WITNESS_BASE_TAG:
        problems.append(f"controller_tag {tag!r}: base is not {WITNESS_BASE_TAG}")
    elif extend_start_revision_of_tag(tag) != WITNESS_REVISION:
        problems.append(f"controller_tag {tag!r} is not revision {WITNESS_REVISION}")
    options = row.get("hydraulic_options")
    undeclared = [key for key in WITNESS_OPTION_KEYS if (options or {}).get(key) is not True]
    if REVISION_KEY in row:
        if row[REVISION_KEY] != WITNESS_REVISION:
            problems.append(f"{REVISION_KEY} {row[REVISION_KEY]!r}")
        elif options is not None and undeclared:  # 2-10.1 1: key and options disagree
            problems.append(f"{REVISION_KEY} 6 but hydraulic_options {undeclared} not true")
    elif undeclared:
        problems.append(f"no {REVISION_KEY} and hydraulic_options {undeclared} not true")
    check = (row.get("hydraulics_record") or {}).get("extend_bound_check")
    if check is not None and not isinstance(check, dict):
        problems.append("extend_bound_check is not an object")
    elif isinstance(check, dict):
        if check.get("rule_revision") != WITNESS_REVISION:
            problems.append(f"extend_bound_check.rule_revision {check.get('rule_revision')!r}")
        if check.get("spec_edition") != WITNESS_SPEC_EDITION:
            problems.append(f"extend_bound_check.spec_edition {check.get('spec_edition')!r}")
    return problems


def identity_defects(rows: list[dict]) -> list[dict]:
    """H-2: the VBJ / LSJ lines whose rev 6 identity fails (a setting defect, 2-10 a reason)."""
    out = []
    for row in rows:
        job = row.get("job") or {}
        if job.get("setting") not in SETTING_MAP:
            continue
        problems = line_identity_problems(row)
        if problems:
            out.append({"job": job, "problems": problems})
    return out


# ------------------------------------------------------------------------------- 2-9.3 / 2-9.4
LIMIT_CYCLE_FACTOR = 2
LIMIT_CYCLE_MARGIN = 6
"""Criteria 4 (2-9.4 L-c): n_rev >= 2 n_rev_off_max and n_rev >= n_rev_off_max + 6."""
F5_STOP_MARGIN_KN = -6.92
F5_STOP_MAX_AFTER_KN = 14.21
"""Criteria 6: clause margin < -6.92 kN or post-stop maximum > 14.21 kN stops."""
R15_ROW = "R15"


def limit_cycle_suspects(rows_by: dict) -> dict:
    """L-c: LS rows whose ``n_rev`` meets the criteria 4 limit-cycle rule against the largest
    V0 ``n_rev`` of the same group (the flow-off maximum); an LS row without that V0 maximum
    (no V0 row of its group, or a V0 / LS ``n_rev`` None) is not judgeable (re-audit warning
    3), never skipped."""
    import judge_stage1_4368 as path1

    off_max: dict[str, int | None] = {}
    for row in rows_by.get(V0_SETTING, []):
        group, n_rev = row["group"], row.get("n_rev")
        if n_rev is None or (group in off_max and off_max[group] is None):
            off_max[group] = None
        else:
            off_max[group] = max(off_max.get(group) or 0, n_rev)
    out: dict[str, list[dict]] = {"suspects": [], "not_judgeable": []}
    for setting in path1.LS_SETTINGS:
        for row in rows_by.get(setting, []):
            where = {"setting": setting, "row": row["row"], "phase": row["phase"]}
            reference = off_max.get(row["group"])
            if reference is None or row.get("n_rev") is None:
                reason = ("no V0 n_rev maximum of the group" if reference is None
                          else "n_rev None")
                out["not_judgeable"].append({**where, "item": "L-c", "kind": "not_judgeable",
                                             "detail": reason})
                continue
            if (row["n_rev"] >= LIMIT_CYCLE_FACTOR * reference
                    and row["n_rev"] >= reference + LIMIT_CYCLE_MARGIN):
                out["suspects"].append({**where, "n_rev": row["n_rev"],
                                        "n_rev_off_max": reference})
    return out


def s8_items(rows_by: dict) -> dict:
    """2-9.3 F-5 on the S8 lines of VB (= VBJ) and LS (= LSJ): the criteria 6 clause alone
    failing is ``F-5 기록`` (flow-on settings, not a failure); another SA-4 item failing is a
    failure; the clause margin < -6.92 kN or the post-stop maximum > 14.21 kN stops; a SA-4
    item without a record and a stop value None are not judgeable."""
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
            if margin is None or after is None:  # re-audit warning 3: never a silent pass
                missing = [name for name, value in (("margin_at_stop_kN", margin),
                                                    ("max_after_stop_kN", after))
                           if value is None]
                out["not_judgeable"].append({**where, "item": "F-5", "kind": "not_judgeable",
                                             "detail": f"criteria 6 stop values None: {missing}"})
            if margin is not None and margin < 0:
                out["f5_records"].append({**where, "margin_at_stop_kN": margin})
            if (margin is not None and margin < F5_STOP_MARGIN_KN) or (
                    after is not None and after > F5_STOP_MAX_AFTER_KN):
                out["stops"].append({**where, "item": "F-5", "kind": "stop",
                                     "detail": "criteria 6 stop value"})
    return out


R15_UNJUDGEABLE_STATES = ("판정 불가", "no R15 pair")
"""Re-audit H-1: R15 worsening states that judge nothing (a reason, never a pass)."""


def r15_worsening(rows_by: dict) -> dict:
    """2-9.3 exception: R15 (criteria 5 "V0 실패, 나빠짐만 판정", the minimum force): VBJ fails
    when its J2 value (E-3 for a rigid event row) is below V0's and the ``m1_criteria`` 5 phase
    test says "구분됨" (2 phases: a weak basis). No pair is ``no R15 pair``; a pair with a J2
    value None (or the phase test without phases) is ``판정 불가`` - both go to the
    not-judgeable items (:func:`r15_not_judgeable`)."""
    import judge_stage1_4368 as path1

    pairs = []
    vb = {r["phase"]: r for r in rows_by.get(path1.JUDGED_SETTING, []) if r["row"] == R15_ROW}
    for row in rows_by.get(V0_SETTING, []):
        if row["row"] == R15_ROW and row["phase"] in vb:
            pairs.append((path1._j2_value_N(row), path1._j2_value_N(vb[row["phase"]])))
    if not pairs:
        return {"pairs": 0, "state": "no R15 pair", "failures": []}
    if any(a is None or b is None for a, b in pairs):
        return {"pairs": len(pairs), "state": "판정 불가",
                "reason": "a J2 value None in an R15 pair", "failures": []}
    scatter = path1.phase_scatter([a for a, _ in pairs], [b for _, b in pairs])
    worse = scatter["state"] == "구분됨" and scatter["E"] < 0
    return {"pairs": len(pairs), "state": scatter["state"], "scatter": scatter,
            "weak_basis": True,
            "failures": [{"row": R15_ROW, "item": "J2", "kind": "fail",
                          "detail": "R15 worsening (구분됨)"}] if worse else []}


def r15_not_judgeable(r15: dict) -> list[dict]:
    """H-1: the R15 worsening as a not-judgeable item when it judged nothing."""
    import judge_stage1_4368 as path1

    if r15["state"] not in R15_UNJUDGEABLE_STATES:
        return []
    detail = f"R15 worsening: {r15['state']}"
    if r15.get("reason"):
        detail += f" ({r15['reason']})"
    return [{"setting": path1.JUDGED_SETTING, "row": R15_ROW, "item": R15_WORSENING_ITEM,
             "kind": "not_judgeable", "detail": detail}]


R15_WORSENING_ITEM = "J2"
"""Erratum 2 final 2-9.3: the one R15 item judged by worsening (not a baseline failure)."""
STATE_FAIL, STATE_FLAG, STATE_RECORD, STATE_UNDETERMINED = (
    "fail", "flag", "record", "undetermined")


def own_item_failures(row: dict) -> list[dict]:
    """The J items a metric row does not pass on its own: the "V0 passes" premise of the 436.8
    path-1 definitions is false for it (D-07 J1, D-08 J2, D-11 J3 of ``judge_stage1_4368``;
    J4 / J5 / J6 / J10 of ``judge_stage1_r5.J_fails``).

    Entries: ``item``, ``state`` (``fail``; ``flag`` / ``record`` for the D-11 rigid record
    rows, whose J3 is a FLAG on the row itself; ``undetermined`` for a value None the
    definition compares without a None case), ``detail``, ``value_missing`` and with it
    ``reason``. Not here: J7 (a name new against V0), J8 (``n_rev`` against the group's V0
    maximum), J9 (the row's own post-lift clips) and J11 (the row's own late fallback reads) -
    ``J_fails`` and D-09 / D-10 compare them without any "V0 passes" premise, so no baseline
    failure exists for them.
    """
    import judge4368_common as common
    import judge_stage1_4368 as path1

    old = path1.old
    out: list[dict] = []

    def add(item: str, detail: str, state: str = STATE_FAIL, missing: str | None = None) -> None:
        entry = {"item": item, "state": state, "detail": detail,
                 "value_missing": missing is not None}
        if missing is not None:
            entry["reason"] = missing
        out.append(entry)

    def over_limit(item: str, key: str, limit: float, none_state: str) -> None:
        value = row.get(key)
        if value is None:
            add(item, f"{key} None", none_state, f"{key} None")
        elif value > limit:
            add(item, f"{key} {value}")

    if row["is_event"]:
        for gate in row.get("gates") or []:
            add("J1", f"gate {gate}")
        over_limit("J5", "t_back", old.RETURN_LIMIT, STATE_FAIL)  # None: no READY back
        over_limit("J6", "att_end", old.ATT_LIMIT, STATE_UNDETERMINED)
        over_limit("J10", "p_move_ev", old.P_MOVE, STATE_UNDETERMINED)
    else:
        _own_steady_items(row, add, over_limit)
    j2 = path1._j2_value_N(row)
    if j2 is None:
        add("J2", "J2 value None", STATE_FAIL, "J2 value None")
    elif not common.is_at_least(j2, common.F_MIN_N):
        add("J2", f"F {j2} N")
    j4_reasons = [f"final {row.get('final')}"] if row.get("final") != "ready" else []
    is_ready_missing = not row["is_event"] and row.get("t_ready") is None
    if is_ready_missing:
        j4_reasons.append("no first READY")
    if j4_reasons:
        add("J4", ", ".join(j4_reasons), STATE_FAIL,
            "t_ready None" if is_ready_missing else None)
    return out


def _own_steady_items(row: dict, add, over_limit) -> None:
    """J1 / J3 / J6 / J10 of a non-event row (:func:`own_item_failures`)."""
    import judge4368_common as common
    import judge_stage1_4368 as path1

    old = path1.old
    if row["row"] != path1.S8_ROW:
        if row.get("class") is None:
            add("J1", "class None", STATE_FAIL, "harness_class None")
        elif row["class"] not in path1.PASSING_CLASSES:
            add("J1", f"class {row['class']}")
    t_ready = row.get("t_ready")
    if row["row"] in path1.SOIL_READY_ROWS:
        if t_ready is None:
            add("J3", "t_ready None", STATE_FAIL, "t_ready None")
        elif common.is_above(t_ready, path1.SOIL_READY_LIMIT_S):
            add("J3", f"t_ready {t_ready}")
    elif row["row"] in path1.RIGID_RECORD_ROWS:  # D-11 rigid record rows: FLAG on the row
        floor = row.get("case_floor")
        if floor is None:
            add("J3", "case_floor_deg missing: FLAG limit 미정", STATE_RECORD,
                "case_floor_deg None")
        else:
            limit = (path1.RIGID_SLOPE_FLAG_S if any(float(a) != 0.0 for a in floor)
                     else path1.RIGID_FLAT_FLAG_S)
            if t_ready is None:
                add("J3", f"t_ready None > {limit} s", STATE_FLAG, "t_ready None")
            elif common.is_above(t_ready, limit):
                add("J3", f"t_ready {t_ready} > {limit} s", STATE_FLAG)
    over_limit("J6", "att_last5", old.ATT_LIMIT, STATE_FAIL)
    over_limit("J10", "p_move", old.P_MOVE, STATE_UNDETERMINED)


BASELINE_TABLES = {"J_vs_V0": "V0", "LS_vs_VB": "VB"}
"""The two judged tables and their reference setting (436.8 labels)."""


def _state_by_item(entries: list[dict]) -> dict[str, str]:
    states: dict[str, str] = {}
    for entry in entries:
        if states.get(entry["item"]) != STATE_FAIL:
            states[entry["item"]] = entry["state"]
    return states


def baseline_failures(rows_by: dict) -> dict:
    """2-9.3 (re-audit H-3): every item the reference row of a (row, phase) pair does not pass
    on its own (:func:`own_item_failures`), with the same item's state on the judged row
    (``pass`` when it has none) - VBJ (= VB) against V0 and LSJ (= LS) against VBJ. A
    record: never counted, never in the status (a J item fails only where the reference
    passes it, D-07 .. D-17 by construction). The R15 J2 of VBJ against V0 is the worsening
    rule's (:func:`r15_worsening`), not listed here."""
    import judge_stage1_4368 as path1

    settings_of = {"J_vs_V0": (path1.JUDGED_SETTING,), "LS_vs_VB": path1.LS_SETTINGS}
    out: dict = {"counted": 0, "rule": "erratum 2 2-9.3: same pair, the reference fails the item "
                 "too -> a baseline failure (recorded only); R15 J2 is the worsening rule's"}
    total = missing = 0
    for table, reference in BASELINE_TABLES.items():
        base = {(r["row"], r["phase"]): r for r in rows_by.get(reference, [])}
        listed = []
        for setting in settings_of[table]:
            for row in rows_by.get(setting, []):
                ref = base.get((row["row"], row["phase"]))
                if ref is None:  # no_reference (a not-judgeable reason of its own)
                    continue
                judged_states = _state_by_item(own_item_failures(row))
                for entry in own_item_failures(ref):
                    if (table == "J_vs_V0" and row["row"] == R15_ROW
                            and entry["item"] == R15_WORSENING_ITEM):
                        continue
                    listed.append({"setting": setting, "reference": reference,
                                   "row": row["row"], "phase": row["phase"],
                                   "item": entry["item"], "reference_state": entry["state"],
                                   "detail": entry["detail"],
                                   "value_missing": entry["value_missing"],
                                   **({"reason": entry["reason"]} if "reason" in entry else {}),
                                   "setting_state": judged_states.get(entry["item"], "pass")})
        out[table] = listed
        total += len(listed)
        missing += sum(entry["value_missing"] for entry in listed)
    out.update(count=total, value_missing_count=missing)
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
