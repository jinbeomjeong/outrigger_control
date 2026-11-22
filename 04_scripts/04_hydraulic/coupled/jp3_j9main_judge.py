"""436.9 edition 5 j9_main judge (``jp3_remedy_spec_v5.md`` 6.5, erratum 2 2-7.1): the v5
criteria stage 1 J items of the ``j9_main`` rows and their J-P3 (③ revision 6).

Sub-commands:

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
               * L-d: record (D-16).
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
EXIT_OF_STATUS = {"pass": EXIT_PASS, "same": EXIT_PASS, "failed": EXIT_FAILED,
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
    stops = [dict(i, setting=s) for table in (j_vs_v0, ls_vs_vb) for s, part in table.items()
             for i in part["items"] if i["kind"] == "stop"]
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
              "vb_fail_items_base_other_phase": sum(
                  i["kind"] == "fail" and i["base_other_phase_has_it"] for i in vb_items),
              "L-a": l_a, "L-b": l_b, "stops": stops, "not_judgeable_items": unjudgeable,
              "no_reference": no_reference, "J-P3": jp3}
    report["status"] = _status(report)
    return report


def _status(report: dict) -> str:
    jp3_status = report["J-P3"]["status"]
    if report["no_reference"] or report["not_judgeable_items"] or jp3_status in (
            "no_judged_runs", "judged_key_missing", "no_p3_runs"):
        return "not_judgeable"
    if jp3_status == "setting_defect":
        return "setting_defect"
    if (report["vb_fail_items"] or report["L-a"] or report["L-b"] or report["stops"]
            or jp3_status == "H-7"):
        return "failed"
    return "pass"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    judged = sub.add_parser("judge")
    judged.add_argument("--rows", type=Path, required=True)
    sample = sub.add_parser("v0-sample")
    sample.add_argument("--sample-keys", type=Path, required=True)
    sample.add_argument("--sample", type=Path, required=True)
    for command in (judged, sample):
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
