"""436.9 edition 4a J4a-15 (``jp3_remedy_spec.md`` 5.5 T-JR-10 .. T-JR-15, 13.9; addendum 4a-2
B4, R9, B2, B3; addendum 4a-3 2 .. 4, 5.3): the batch judges of the T8 pairs and of Dg-3, and
the record bundle.

Sub-commands:

``t8``       On the run_v5 batch ``j9_t8`` and the 22 jobs of the revision 8 7.2 rule
             (``run_v5.p3_hash_jobs`` of ``--main-jsonl``, 4a-3 2; exactly 22 pairs each, a pair
             without a result is not judgeable):
             T-JR-10 = VBH against the stored h10 VB line: 4a-3 3.1 A (no
             ``WARN_ROD_PRESSURE_FALLBACK`` on either side), B (``commands_sha256``,
             ``event_names``, ``events`` equal), the ``hydraulics_record`` equality outside the
             3.2 paths (``jp3_t8_rules``), C recorded; every stored line must carry the tag
             ``final_C4G2_P3_LAS_K1`` and its T4h the ③ revision 4 (else not judgeable).
             T-JR-11 = VBJ against VBJ0, ``commands_sha256`` equal. The VB lines are a record
             (4a-3 5.3); a VB line missing, an error VB row or a VB hash other than the stored
             h10 one makes T-JR-10 not judgeable ("저장값 노후 확인 전", 4a-4 4) while T-JR-11
             is still judged (each test reports its own ``status``). 4a-4 5: ``--stored`` and
             ``--main-jsonl`` must be the fixed files (``jp3_fixed_inputs``). Prelaunch audit
             M-4: a VBH / VBJ line that is not a rev 5 row of the 13.6 identity, or a VBH /
             VBJ / VBJ0 line without fitting P4 evidence (4a-2 B2), is a setting defect of its
             test; T-JR-11 hashes must be 64 characters (as T-JR-10).
``t12``      T-JR-12 (13.9, 4a-3 4) of one bundle: ``--bundle VBH`` = VBH against the stored H-6
             (rev 4), ``--bundle VBJ`` = VBJ against VBJ0. Exactly 135 pairs by plain key,
             exactly 1 L2 line. Failure: the L2 line's base grade pass / flag and new grade fail
             (``r79_sensor_judge`` via ``h8_noise_judge_4368.grade_line``; every level's grade
             transitions are a record), a new FAULT name, and the READY table of 4a-3 4.2 (READY
             = ``r79_sensor_judge._ready_time``: base READY and new READY more than 30 s later or
             none = fail; both none and base none / new READY = records). VBJ: J-P3
             (``j_p3_judgement_rev5``, 1 judged row expected) and the P4 evidence of the VBJ
             lines and of their VBJ0 base lines (4a-2 B2, 4a-3 4.4; VBJ and VBJ0 run with
             ``R79_ROD_MODEL=plant_truth``). Records: the R5-7 columns of 5.5 with the
             ``ret_after_gate_s`` resolution (R9). 4a-4 5: VBH needs the fixed H-6 as
             ``--base``; both bundles need ``--base-judge-sha256`` and ``--new-judge-sha256``
             (the ``base-judge`` / ``dg3-judge`` reports; prelaunch audit M-8); without them,
             or with other files, not judgeable. The P4 evidence applies to the 436.9 lines
             only (``v5_setting`` in :data:`JP3_LINE_SETTINGS`; the stored H-6 VB lines predate
             the evidence keys: prelaunch audit B-1). Setting defects (M-3): a new line not of
             the bundle's setting or not rev 5, a VBJ base line not VBJ0, the new file equal to
             the base file. Not judgeable (M-8): a new (VBJ: also base) file whose meta
             ``keys_file`` is not the stored H-6 (135 keys).
``dg3-judge``      Prelaunch audit M-8: the judge file of one new-side Dg-3 run (VBH, VBJ,
             VBJ0) with the P-1a L1 extract (``--l1-reference-sha256`` from the P-1a report;
             the run's meta ``keys_file`` must be the stored H-6, its lines of the setting);
             reports the judge file's sha256. An existing ``--judge-out`` is refused.
``base-judge``     4a-3 4.4: writes the H-6 base judge file (``r79_sensor_judge.py judge`` on
             the stored H-6 with the L1 lines of ``h8_noise_VB.json``, ``--s4-late-loc``) and
             reports its sha256 (both inputs must be the fixed files).
``base-judge-compare``  4a-4 erratum 1 R-2 (a record): the per-key grades (grade, failed
             gates, flags) of the stored H-6 under the new base judge file against the 436.8
             path 1 r79 judge of the same H-6 (``judge_932f1fb/harness_path1/h6_r79_judge.json``,
             sha256 fixed) and, optionally, that folder's ``h6_judge.json`` line grades; also
             whether the two L1 reference extracts are equal. Exit 1 = keys of other grades
             (look for the cause before T-JR-12), 2 = an input missing or of another sha.
``t12-selfcheck``  4a-4 6, before the run: ``t12 --bundle VBH`` of the stored H-6 against
             itself with that judge file on both sides; exit 0 only when the 6 table holds
             (pass, 135 pairs, 1 L2 line, empty failure and improvement lists, 7 pairs without
             READY on both sides, only X -> X grade transitions), else 1.
``records``  T-JR-13 .. T-JR-15 (4a-2 B4; user decision 2026-11-21: the T-JR-15 seed net force
             is judged): Dg-2 replay reports (runs, errors; a record), the
             ``lock_window_alignment`` J11 ``n_late`` of the Dg-3 lines (a record), and
             per-lock records (``relock_step_over_1bar_count``, seed rows) with the seed net
             force of 4a-2 3.4 (``net_force_seed_step_N`` <= 1 N on every row, else failed).
             Not judgeable (prelaunch audit M-6): an empty ``--replay``, ``--dg3`` or
             ``--lock-rows``, a replay report that stopped, is test-only (``judged: False``),
             has error rows or other than one row per run, a run count outside 426 / 135 or
             one of the two missing, and the 3.4 rules.

Exit codes and ``status`` (all sub-commands):

======  =================  ===================================================================
exit    status             meaning
======  =================  ===================================================================
0       ``pass``           the bundle passes (``records``: written, nothing not judgeable)
1       ``failed``         a failure of 5.5 / 13.9 (T8 hash, pass -> fail, new FAULT, READY,
                           J-P3 H-7, ``records``: a T-JR-15 seed row over 1 N)
2       ``not_judgeable``  a pair without a result, another pair or L2 count, a missing key
                           or L2 grade, a stored line of another tag / revision; an existing
                           ``--out``
2       ``setting_defect`` a wrong rev 5 identity or P4 evidence (outranks the others)
3       ``error``          an unexpected input error
======  =================  ===================================================================

The report records the sha256 of every input. The stdout's last line is JSON with ``status``,
the problem counts and the report path only.

Batch commands (dynamics-dev, project root; the main session launches them):
  run_v5.py j9_t8 --out <folder>/j9_t8.jsonl --mask <hex>        (T-JR-10 / 11, 88 rows; the
      22 jobs come from the stored v5/main.jsonl of the main checkout)
  for VBH / VBJ / VBJ0 (T-JR-12, the 135 stored dg3 keys of resume_k1/h6_dg3_v4on.json):
    env R79_V5_SETTING=<setting> R79_T4H_DIR=<folder>/<setting>_t4h LAS_T3_DG3_LAS=on
        LAS_T3_DG3_K1=on LAS_T3_DG3_P3=on [R79_ROD_MODEL=plant_truth for VBJ / VBJ0]
    las_t3_dg3.py <root> run <folder>/dg3_<setting>.json --levels L2,L3
        --keys-file <resume_k1/h6_dg3_v4on.json>          (meta keys_file = the fixed H-6)
  then (M-8) jp3_tjr_judge.py dg3-judge --setting <setting> --dg3 <folder>/dg3_<setting>.json
      --l1-reference <pre>/h6_base_judge_L1_reference.json --l1-reference-sha256
      <l1_reference_sha256 of bj.json> --judge-out <folder>/dg3_<setting>_judge.json
      --out <folder>/dg3_<setting>_judge_report.json
  and t12 --bundle VBH (base H-6, --base-judge-sha256 = P-1a) / --bundle VBJ (base VBJ0,
      --base-judge-sha256 = the VBJ0 dg3-judge report), --new-judge-sha256 = its report
Before T-JR-12 (4a-4 6, the main session; stored data only):
  jp3_tjr_judge.py base-judge --h6 <resume_k1/h6_dg3_v4on.json> --noise
      <resume_k1/h8_noise_VB.json> --judge-out <pre>/h6_base_judge.json --out <pre>/bj.json
  jp3_tjr_judge.py t12-selfcheck --h6 <same H-6> --judge <pre>/h6_base_judge.json
      --judge-sha256 <judge_sha256 of bj.json> --out <pre>/h6_selfcheck.json   (exit 0)
  jp3_tjr_judge.py base-judge-compare --h6 <same H-6> --new-judge <pre>/h6_base_judge.json
      --new-judge-sha256 <judge_sha256> --stored-judge <v4368>/judge_932f1fb/harness_path1/
      h6_r79_judge.json --stored-h6-judge <same folder>/h6_judge.json --new-l1-reference
      <pre>/h6_base_judge_L1_reference.json --stored-l1-reference <same folder>/
      h6_L1_reference.json --out <pre>/h6_judge_compare.json        (record; exit 1 = differ)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import jp3_baseline_compare as compare  # noqa: E402
import jp3_fixed_inputs as fixed  # noqa: E402
import jp3_t8_rules as t8_rules  # noqa: E402
from j_p3_inputs import rod_reading_evidence_problems  # noqa: E402

T8_JOBS = 22
"""4a-3 2: the revision 8 7.2 rule (``run_v5.p3_hash_jobs``) replaces the T-P3-5 20 rows."""
T8_JUDGED_SETTINGS = ("VBH", "VBJ", "VBJ0")
"""``j9_t8`` settings the judgement reads; its VB lines are the 4a-3 5.3 record only."""
T8_TEST_SETTINGS = {"T-JR-10": ("VBH",), "T-JR-11": ("VBJ", "VBJ0")}
"""The ``j9_t8`` settings whose line checks (M-4) belong to each test."""
T8_REVISION_5_SETTINGS = ("VBH", "VBJ")
"""③ rev 5 on (VBJ0 = the same plant with ③ off: no rev 5 identity)."""
STORED_SETTING = "VB"
VB_STALE_REASON = "저장값 노후 확인 전(4a-3 5.3)"
"""4a-4 4: the reason T-JR-10 is not judgeable when the VB record is not 22 equal lines."""
DG3_PAIRS = 135
DG3_L2_LINES = 1
JUDGED_LEVEL = "L2"
"""4a-3 4.3: pass -> fail is judged on the L2 line only (all transitions are recorded)."""
READY_DELAY_LIMIT_S = 30.0
BUNDLE_BASE = {"VBH": "stored H-6 (rev 4)", "VBJ": "VBJ0"}
BUNDLE_BASE_SETTING = {"VBH": "VB", "VBJ": "VBJ0"}
"""Prelaunch audit M-3: the ``v5_setting`` of the base lines (the stored H-6 is a VB run)."""
JP3_LINE_SETTINGS = ("VBH", "VBJ", "VBJ0", "LSH1", "LSH2", "LSH3", "LSH4", "LSJ1", "LSJ2",
                     "LSJ3", "LSJ4")
"""436.9 settings (``run_v5.JP3_SETTINGS``): their lines carry the P4 evidence keys (B-1)."""
REPLAY_RUN_COUNTS = (426, 135)
"""T-JR-13: the Dg-2 replays of the stored h10 T4h (426 npz) and H-6 T4h (135 npz) folders."""
NEW_FAULT_PREFIX = "FAULT"
RET_AFTER_GATE_RESOLUTION = (
    "read grid 0.1 s: ret_after_gate_s = first RET read - T (the read before it), so it differs "
    "from the gate-opening sub-step by up to 0.1 s; a record, not a judged column (4a-2 R9)")
RECORD_COLUMNS = ("retract_tracker_dominated_reads", "retract_tracker_over_tol_reads",
                  "retract_tracker_false_drop_reads")


def _read_json_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _job_identity(job: dict) -> str:
    return json.dumps({k: v for k, v in sorted(job.items()) if k != "setting"}, sort_keys=True)


# --- t8 (T-JR-10 / T-JR-11) -----------------------------------------------------------------

@dataclass(frozen=True)
class T8Inputs:
    """The lines of one ``t8`` judgement (job key = :func:`_job_identity`).

    Attributes:
        rule_jobs: The 22 job keys of the revision 8 7.2 rule (``run_v5.p3_hash_jobs``).
        stored: Stored h10 lines by setting and job key.
        rerun: ``j9_t8`` lines by setting and job key.
        stored_meta: T4h meta of the stored lines (job key -> meta; None = no T4h).
        rerun_meta: T4h meta of the rerun VBH lines.
    """

    rule_jobs: tuple[str, ...]
    stored: dict[str, dict[str, dict]]
    rerun: dict[str, dict[str, dict]]
    stored_meta: dict[str, dict | None]
    rerun_meta: dict[str, dict | None]
    bad_rows: dict[str, int] = field(default_factory=dict)
    """``<stored|rerun>:<setting>`` -> error or repeated rows of that setting."""
    stored_sha_problem: str | None = None
    """4a-4 5: ``--stored`` is not the fixed h10 file (T-JR-10 not judgeable)."""


def judge_t8(inputs: T8Inputs, problems: compare.Problems) -> dict:
    """T-JR-10 / T-JR-11 on the 22 jobs (4a-3 2, 3) and the VB record (4a-3 5.3, 4a-4 4).

    Each test has its own status: a VB record with a missing, error or other-hash line makes
    T-JR-10 not judgeable (4a-4 4) and leaves T-JR-11 judged; the bundle status is the worst."""
    if len(inputs.rule_jobs) != T8_JOBS or len(set(inputs.rule_jobs)) != T8_JOBS:
        problems.not_judgeable.append(f"{len(inputs.rule_jobs)} rule jobs, {T8_JOBS} expected")
        return {}
    tests = {"T-JR-10": compare.Problems(), "T-JR-11": compare.Problems()}
    for name, settings in T8_TEST_SETTINGS.items():
        tests[name].setting_defects += t8_line_defects(inputs, settings)
    vb_record = _vb_rerun_record(inputs)
    report = {"T-JR-11": _t_jr_11(inputs, tests["T-JR-11"]), "VB_rerun_record": vb_record}
    t10 = tests["T-JR-10"]
    t10.not_judgeable += _t_jr_10_preconditions(inputs, vb_record)
    report["T-JR-10"] = {} if t10.not_judgeable else _t_jr_10(inputs, t10)
    for name, found in tests.items():
        report[name]["status"] = found.status()
        problems.setting_defects += [f"{name}: {text}" for text in found.setting_defects]
        problems.not_judgeable += [f"{name}: {text}" for text in found.not_judgeable]
        problems.failures += [f"{name}: {text}" for text in found.failures]
    return report


def t8_line_defects(inputs: T8Inputs, settings: tuple[str, ...]) -> list[str]:
    """Prelaunch audit M-4 (user decision 2026-11-21): on the rule jobs, a VBH / VBJ line is a
    revision 5 row of the sealed identity (13.6) and every VBH / VBJ / VBJ0 line carries the
    P4 evidence (4a-2 B2); otherwise a setting defect."""
    defects = []
    for setting in settings:
        lines = inputs.rerun.get(setting, {})
        for key in inputs.rule_jobs:
            line = lines.get(key)
            if line is None:
                continue  # a missing line is not judgeable (_rows_ok)
            label = f"{setting} {key}"
            revision = _t8_check(line).get("rule_revision")
            if setting in T8_REVISION_5_SETTINGS:
                if revision != 5:
                    defects.append(f"{label}: rule_revision {revision!r}, not 5")
                defects += [f"{label}: {text}" for text in compare.identity_problems(line)]
            defects += [f"{label}: {text}" for text in rod_reading_evidence_problems(
                line.get("hydraulics_record"), line.get("hydraulic_options"))]
    return defects


def _t8_check(line: dict) -> dict:
    return (line.get("hydraulics_record") or {}).get("extend_bound_check") or {}


def _rows_ok(inputs: T8Inputs, label: str, setting: str, lines: dict) -> list[str]:
    """Why the lines of one setting are not exactly the 22 jobs without a bad row."""
    problems = []
    if inputs.bad_rows.get(f"{label}:{setting}"):
        problems.append(f"{label} {setting}: {inputs.bad_rows[f'{label}:{setting}']} error or "
                        "repeated rows")
    missing = [key for key in inputs.rule_jobs if key not in lines]
    if missing:
        problems.append(f"{label} {setting}: {len(missing)} of the 22 jobs missing")
    return problems


def _t_jr_10_preconditions(inputs: T8Inputs, vb_record: dict) -> list[str]:
    problems = [] if inputs.stored_sha_problem is None else [inputs.stored_sha_problem]
    problems += _rows_ok(inputs, "rerun", "VBH", inputs.rerun.get("VBH", {}))
    problems += _rows_ok(inputs, "stored", STORED_SETTING,
                         inputs.stored.get(STORED_SETTING, {}))
    if vb_record["missing"] or vb_record["error_rows"] or vb_record["differing_count"]:
        problems.append(f"{VB_STALE_REASON}: VB lines missing {vb_record['missing']}, error "
                        f"{vb_record['error_rows']}, other hash {vb_record['differing_count']}")
    return problems


def _t_jr_10(inputs: T8Inputs, problems: compare.Problems) -> dict:
    """VBH against the stored VB line: 3.1 A, B, record equality (judged) and C (record)."""
    pairs = []
    for key in inputs.rule_jobs:
        stored = inputs.stored[STORED_SETTING][key]
        new = inputs.rerun["VBH"][key]
        pairs.append(_t_jr_10_pair(key, stored, new, inputs, problems))
    failing = [pair["job"] for pair in pairs if pair["problems"]]
    if failing:
        problems.failures.append(f"{len(failing)}/{T8_JOBS} pairs differ")
    return {"pairs": T8_JOBS, "passing": T8_JOBS - len(failing), "pair_rows": pairs}


def _t_jr_10_pair(key: str, stored: dict, new: dict, inputs: T8Inputs,
                  problems: compare.Problems) -> dict:
    stored_meta, new_meta = inputs.stored_meta.get(key), inputs.rerun_meta.get(key)
    if stored.get("controller_tag") != t8_rules.STORED_TAG:
        problems.not_judgeable.append(f"stored {key}: tag {stored.get('controller_tag')!r}")
    revision = ((stored_meta or {}).get("two_pressure_settings") or {}).get(
        "extend_start_bound") or {}
    if revision.get("revision") != t8_rules.STORED_REVISION:
        problems.not_judgeable.append(f"stored {key}: T4h ③ revision {revision.get('revision')!r}")
    pair_problems = []
    for label, line in (("stored", stored), ("new", new)):
        has_fallback = t8_rules.has_fallback_event(line)
        if has_fallback is None:
            problems.not_judgeable.append(f"{label} {key}: no event_names / events")
        elif has_fallback:
            pair_problems.append(f"A: {label} line has {t8_rules.FALLBACK_EVENT}")
    pair_problems += [f"B: {text}" for text in t8_rules.condition_b_problems(stored, new)]
    paths = t8_rules.record_differences(stored.get("hydraulics_record") or {},
                                        new.get("hydraulics_record") or {})
    pair_problems += [f"record: {path}" for path in paths[:20]]
    return {"job": key, "problems": pair_problems,
            "C_record": t8_rules.fallback_estimate_record(stored_meta, new_meta)}


def _t_jr_11(inputs: T8Inputs, problems: compare.Problems) -> dict:
    """VBJ against VBJ0: ``commands_sha256`` equal on the 22 jobs (4a-3 2)."""
    for setting in ("VBJ", "VBJ0"):
        problems.not_judgeable += _rows_ok(inputs, "rerun", setting,
                                           inputs.rerun.get(setting, {}))
    if problems.not_judgeable:
        return {}
    # prelaunch audit M-4: 64 characters and equal, like T-JR-10 (None == None never passes)
    differing = [key for key in inputs.rule_jobs
                 if not _same_hash(inputs.rerun["VBJ"][key], inputs.rerun["VBJ0"][key])]
    if differing:
        problems.failures.append(f"{len(differing)}/{T8_JOBS} command hashes differ")
    return {"pairs": T8_JOBS, "equal": T8_JOBS - len(differing), "differing": differing[:10]}


def _vb_rerun_record(inputs: T8Inputs) -> dict:
    """4a-3 5.3 record of the current-code VB rerun against the stored h10 hash (equal, other,
    missing, error rows, the other jobs); 4a-4 4 reads it for the T-JR-10 precondition."""
    vb_lines = inputs.rerun.get(STORED_SETTING, {})
    stored_vb = inputs.stored.get(STORED_SETTING, {})
    missing = [key for key in inputs.rule_jobs if key not in vb_lines]
    differing = [key for key in inputs.rule_jobs if key in vb_lines
                 and not _same_hash(vb_lines[key], stored_vb.get(key))]
    return {"lines": T8_JOBS - len(missing),
            "equal": T8_JOBS - len(missing) - len(differing), "differing_count": len(differing),
            "differing": differing[:10], "missing": len(missing),
            "error_rows": inputs.bad_rows.get(f"rerun:{STORED_SETTING}", 0)}


def _same_hash(line: dict, stored: dict | None) -> bool:
    """4a-4 4: the 64-character ``commands_sha256`` of the line equals the stored one."""
    value = line.get("commands_sha256")
    return (stored is not None and isinstance(value, str) and len(value) == t8_rules.HASH_LENGTH
            and value == stored.get("commands_sha256"))


def _by_setting_job(rows: list[dict], label: str,
                    bad_rows: dict[str, int]) -> dict[str, dict[str, dict]]:
    """Lines by setting and job key; error and repeated rows are counted in ``bad_rows``
    (``<label>:<setting>``) and left out."""
    out: dict[str, dict[str, dict]] = {}
    for row in rows:
        name = f"{label}:{row['job']['setting']}"
        setting_lines = out.setdefault(row["job"]["setting"], {})
        key = _job_identity(row["job"])
        if "error" in row or key in setting_lines:
            bad_rows[name] = bad_rows.get(name, 0) + 1
            continue
        setting_lines[key] = row
    return out


def _t4h_meta(folder: Path, line: dict) -> dict | None:
    """The ``meta_json`` of a line's T4h npz (None: no file)."""
    import numpy as np

    name = line.get("t4h_file")
    path = None if name is None else folder / Path(name).name
    if path is None or not path.is_file():
        return None
    with np.load(path, allow_pickle=False) as data:
        return json.loads(str(data["meta_json"]))


def t8_inputs(args: argparse.Namespace, problems: compare.Problems) -> tuple[T8Inputs, list]:
    """The ``t8`` inputs from the command line; also the input files for the sha record.
    ``--main-jsonl`` not the fixed file (4a-4 5) makes the bundle not judgeable (no jobs)."""
    import run_v5

    main_problem = fixed.sha_problem(args.main_jsonl, fixed.MAIN_JSONL_SHA256, "--main-jsonl")
    if main_problem is not None:
        problems.not_judgeable.append(main_problem)
        rule_jobs: tuple[str, ...] = ()
    else:
        rule_jobs = tuple(_job_identity(job) for _, job in run_v5.p3_hash_jobs(args.main_jsonl))
    bad_rows: dict[str, int] = {}
    stored = _by_setting_job(_read_json_lines(args.stored), "stored", bad_rows)
    rerun = _by_setting_job(_read_json_lines(args.rerun), "rerun", bad_rows)
    stored_dir = args.stored_t4h_dir or args.stored.with_name(f"{args.stored.stem}_t4h")
    rerun_dir = args.rerun_t4h_dir or args.rerun.with_name(f"{args.rerun.stem}_t4h")
    stored_vb, rerun_vbh = stored.get(STORED_SETTING, {}), rerun.get("VBH", {})
    stored_meta = {key: _t4h_meta(stored_dir, stored_vb[key])
                   for key in rule_jobs if key in stored_vb}
    rerun_meta = {key: _t4h_meta(rerun_dir, rerun_vbh[key])
                  for key in rule_jobs if key in rerun_vbh}
    files = [args.main_jsonl, args.stored, args.rerun]
    for folder, lines in ((stored_dir, stored_vb), (rerun_dir, rerun_vbh)):
        files += [folder / Path(lines[key]["t4h_file"]).name for key in rule_jobs
                  if key in lines and lines[key].get("t4h_file")]
    stored_problem = fixed.sha_problem(args.stored, fixed.H10_SHA256, "--stored")
    inputs = T8Inputs(rule_jobs, stored, rerun, stored_meta, rerun_meta, bad_rows,
                      stored_problem)
    return inputs, files


# --- t12 (T-JR-12) --------------------------------------------------------------------------

def judge_t12(bundle: str, base: dict, base_judge: dict, new: dict, new_judge: dict,
              *, check_settings: bool = True) -> tuple[dict, compare.Problems]:
    """T-JR-12 of one bundle (module docstring). ``check_settings`` False = the 4a-4 6 self
    check of the stored H-6 against itself (no 436.9 line on either side: the M-3 setting
    checks and the fixed keys file of the new side do not apply)."""
    import h8_noise_judge_4368 as h8

    problems = compare.Problems()
    base_lines = _dg3_lines(base["results"], "base", problems)
    new_lines = _dg3_lines(new["results"], "new", problems)
    if check_settings:
        problems.setting_defects += bundle_setting_problems(bundle, base_lines, new_lines)
        problems.not_judgeable += keys_file_problems("new", new)
        if bundle == "VBJ":
            problems.not_judgeable += keys_file_problems("base", base)
    if len(base_lines) != DG3_PAIRS or set(base_lines) != set(new_lines):
        problems.not_judgeable.append(f"{bundle}: {len(base_lines)} base / {len(new_lines)} new "
                                      f"keys, {DG3_PAIRS} equal keys expected")
        return {"pairs": len(set(base_lines) & set(new_lines))}, problems
    l2_lines = sum(line.get("level") == "L2" for line in new_lines.values())
    if l2_lines != DG3_L2_LINES:
        problems.not_judgeable.append(f"{bundle}: {l2_lines} L2 lines, {DG3_L2_LINES} expected")
    base_grades = h8.grade_lines(list(base_lines.values()), base_judge)
    new_grades = h8.grade_lines(list(new_lines.values()), new_judge)
    ready = _ready_cases(base_lines, new_lines)
    report = {"bundle": bundle, "base": BUNDLE_BASE[bundle], "pairs": DG3_PAIRS,
              "l2_pass_to_fail": _l2_pass_to_fail(base_grades, new_grades, h8, problems),
              "grade_transitions_record": _grade_transitions(base_grades, new_grades),
              "new_fault": _new_faults(base_lines, new_lines, problems),
              "ready_failures": ready["failures"],
              "ready_both_missing_record": ready["both_missing"],
              "ready_improved_record": ready["improved"]}
    for key in ("l2_pass_to_fail", "new_fault", "ready_failures"):
        if report[key]:
            problems.failures.append(f"{bundle}: {len(report[key])} {key} keys")
    _check_lines(bundle, base_lines, new_lines, problems)
    if bundle == "VBJ":
        report["J-P3"] = _dg3_j_p3(list(new_lines.values()), problems)
    report["records"] = _r5_7_records(list(new_lines.values()))
    return report, problems


def _check_lines(bundle: str, base_lines: dict, new_lines: dict,
                 problems: compare.Problems) -> None:
    """Rev 5 identity of the new lines and the P4 evidence of every 436.9 line (B-1 of the
    prelaunch audit: lines whose ``v5_setting`` is a 436.9 setting; the stored H-6 lines, setting
    VB and fixed by sha, predate the evidence keys and are left out; 4a-3 4.4: the VBJ0 base
    lines of the VBJ bundle are 436.9 lines and are checked)."""
    for label, lines in (("new", new_lines), ("base", base_lines)):
        for key, line in lines.items():
            if label == "new":
                problems.setting_defects += [f"{key}: {text}" for text in _dg3_identity(line)]
            if line.get("v5_setting") not in JP3_LINE_SETTINGS:
                continue
            problems.setting_defects += [
                f"{label} {key}: {text}" for text in rod_reading_evidence_problems(
                    line.get("hydraulics_record"), line.get("hydraulic_options"))]


def bundle_setting_problems(bundle: str, base_lines: dict, new_lines: dict) -> list[str]:
    """Prelaunch audit M-3: every new line is of the bundle's setting with a revision 5 record;
    the VBJ bundle's base lines are VBJ0 (setting defects otherwise)."""
    problems = []
    for key, line in new_lines.items():
        record = (line.get("hydraulics_record") or {}).get("extend_bound_check") or {}
        if line.get("v5_setting") != bundle:
            problems.append(f"new {key}: v5_setting {line.get('v5_setting')!r} is not {bundle}")
        if record.get("rule_revision") != 5:
            problems.append(f"new {key}: rule_revision {record.get('rule_revision')!r}, not 5")
    expected_base = BUNDLE_BASE_SETTING[bundle]
    for key, line in base_lines.items():
        if line.get("v5_setting") != expected_base:
            problems.append(f"base {key}: v5_setting {line.get('v5_setting')!r} is not "
                            f"{expected_base}")
    return problems


def keys_file_problems(label: str, document: dict) -> list[str]:
    """Prelaunch audit M-8: a 436.9 Dg-3 run took its keys from the stored H-6 through
    ``--keys-file`` (meta ``keys_file.sha256`` = the fixed H-6, 135 keys)."""
    record = (document.get("meta") or {}).get("keys_file") or {}
    if record.get("sha256") == fixed.H6_SHA256 and record.get("n_keys") == DG3_PAIRS:
        return []
    return [f"{label} file: meta keys_file {record.get('sha256')!r} / {record.get('n_keys')!r} "
            f"is not the stored H-6 ({fixed.H6_SHA256[:12]}, {DG3_PAIRS} keys)"]


def _dg3_lines(results: list[dict], label: str, problems: compare.Problems) -> dict[str, dict]:
    import h8_noise_judge_4368 as h8

    lines = {}
    for run in results:
        key = h8.plain_key(run["key"])
        if "error" in run:
            problems.not_judgeable.append(f"{label} {key}: error line (no result)")
            continue
        lines[key] = run
    return lines


def _l2_pass_to_fail(base_grades: dict, new_grades: dict, h8,
                     problems: compare.Problems) -> list:
    """4a-3 4.3 / 13.9: L2 lines only; base pass or flag and new fail is a failure. An L2 line
    without a grade is not judgeable (an L3 one is only recorded)."""
    passing = (h8.GRADE_PASS, h8.GRADE_FLAG)
    keys = []
    for key, grade in new_grades.items():
        if grade.get("level") != JUDGED_LEVEL:
            continue
        old = base_grades.get(key)
        if old is None or h8.GRADE_NOT_JUDGEABLE in (grade["grade"], old["grade"]):
            problems.not_judgeable.append(f"{key}: L2 line without a judge grade")
            continue
        if old["grade"] in passing and grade["grade"] == h8.GRADE_FAIL:
            keys.append(key)
    return sorted(keys)


def _grade_transitions(base_grades: dict, new_grades: dict) -> dict[str, dict[str, int]]:
    """4a-3 4.3 record: per level the count of every base -> new grade pair (not judged)."""
    transitions: dict[str, Counter] = {}
    for key, grade in new_grades.items():
        old = base_grades.get(key) or {"grade": "missing"}
        level = str(grade.get("level"))
        transitions.setdefault(level, Counter())[f"{old['grade']}->{grade['grade']}"] += 1
    return {level: dict(counter) for level, counter in sorted(transitions.items())}


def _fault_names(line: dict) -> set[str] | None:
    names = (line.get("r79") or {}).get("warn_fault")
    return None if names is None else {name for name in names
                                       if str(name).startswith(NEW_FAULT_PREFIX)}


def _new_faults(base_lines: dict, new_lines: dict, problems: compare.Problems) -> list:
    keys = []
    for key, line in new_lines.items():
        mine, theirs = _fault_names(line), _fault_names(base_lines[key])
        if mine is None or theirs is None:
            problems.not_judgeable.append(f"{key}: no warn_fault record")
        elif mine - theirs:
            keys.append(key)
    return sorted(keys)


def ready_time_s(line: dict) -> float | None:
    """4a-3 4.1: the line's first READY, ``base.t_ready_s`` if present, else ``base.t_ready``
    (``r79_sensor_judge._ready_time`` itself; None = no READY, also without ``base``)."""
    if not isinstance(line.get("base"), dict):
        return None
    return _r79_judge()._ready_time(line)


def _r79_judge():
    """``04_scripts/03_control/s8/r79_sensor_judge.py`` (imported once, for ``_ready_time``)."""
    s8_dir = ROOT / "04_scripts" / "03_control" / "s8"
    if str(s8_dir) not in sys.path:
        sys.path.insert(0, str(s8_dir))
    import r79_sensor_judge

    return r79_sensor_judge


def _ready_cases(base_lines: dict, new_lines: dict) -> dict[str, list]:
    """4a-3 4.2 table over every pair: base READY and new READY later than base + 30 s, or base
    READY and no new READY, fail; no READY on both sides and base none / new READY are
    records (the first with both ``final_phase`` values)."""
    out: dict[str, list] = {"failures": [], "both_missing": [], "improved": []}
    for key, line in sorted(new_lines.items()):
        base_s, new_s = ready_time_s(base_lines[key]), ready_time_s(line)
        if base_s is not None and (new_s is None or new_s > base_s + READY_DELAY_LIMIT_S):
            out["failures"].append(key)
        elif base_s is None and new_s is None:
            out["both_missing"].append({
                "key": key, "base_final_phase": (base_lines[key].get("base") or {}).get(
                    "final_phase"),
                "new_final_phase": (line.get("base") or {}).get("final_phase")})
        elif base_s is None:
            out["improved"].append(key)
    return out


def _dg3_identity(line: dict) -> list[str]:
    check = (line.get("hydraulics_record") or {}).get("extend_bound_check") or {}
    if check.get("rule_revision") != 5:
        return []
    return [f"{key} {check.get(key)!r}" for key, value in compare.DEFAULT_IDENTITY.items()
            if check.get(key) != value]


def _dg3_j_p3(lines: list[dict], problems: compare.Problems) -> dict:
    """J-P3 of the VBJ bundle: exactly 1 judged (normal grade) row (13.9)."""
    from outrigger_sim.control.extend_start_bound import j_p3_judgement_rev5

    records = [(line.get("hydraulics_record") or {}).get("extend_bound_check") for line in lines]
    rods = [bool(line.get("has_rod_reading", True)) for line in lines]
    judgement = j_p3_judgement_rev5(records, rods, [False] * len(lines),
                                    expected_judged_runs=DG3_L2_LINES)
    status = judgement["status"]
    if status == "H-7":
        problems.failures.append("VBJ: J-P3 H-7")
    elif status == "setting_defect":
        problems.setting_defects.append("VBJ: J-P3 setting defect")
    elif status != "pass":
        problems.not_judgeable.append(f"VBJ: J-P3 {status}")
    return {key: judgement[key] for key in ("status", "runs", "runs_judged", "runs_by_case")}


def _r5_7_records(lines: list[dict]) -> dict:
    """5.5 records of the R5-7 term (sums over the lines) with the R9 resolution note."""
    sums = dict.fromkeys(RECORD_COLUMNS, 0)
    after = []
    for line in lines:
        check = (line.get("hydraulics_record") or {}).get("extend_bound_check") or {}
        for column in RECORD_COLUMNS:
            sums[column] += int(sum(check.get(column) or []))
        after += [row.get("ret_after_gate_s") for row in check.get("retract_tracker_stretch_log")
                  or [] if row.get("ret_after_gate_s") is not None]
    return {**sums, "ret_after_gate_s_values": len(after),
            "ret_after_gate_s_max": max(after) if after else None,
            "ret_after_gate_s_resolution": RET_AFTER_GATE_RESOLUTION}


def t12_input_problems(bundle: str, base: Path, base_judge: Path,
                       base_judge_sha256: str | None) -> list[str]:
    """4a-4 5: VBH's ``--base`` is the fixed H-6; ``--base-judge`` has the sha256 recorded
    before the comparison (``--base-judge-sha256``: P-1a for VBH, the VBJ0 ``dg3-judge`` report
    for VBJ; required for both bundles, prelaunch audit M-8)."""
    problems = []
    if bundle == "VBH":
        problem = fixed.sha_problem(base, fixed.H6_SHA256, "--base (stored H-6)")
        problems += [] if problem is None else [problem]
    problems += judge_sha_problems("--base-judge", base_judge, base_judge_sha256)
    return problems


def judge_sha_problems(label: str, judge: Path, expected: str | None) -> list[str]:
    """The judge file has the sha256 given on the command line (missing = not judgeable)."""
    if expected is None:
        return [f"{label}-sha256 missing (required, prelaunch audit M-8)"]
    problem = fixed.sha_problem(judge, expected.lower(), label)
    return [] if problem is None else [problem]


def t12_file_defects(base: Path, new: Path) -> list[str]:
    """Prelaunch audit M-3: the new file is never the base file itself."""
    if base.is_file() and new.is_file() and fixed.file_sha256(base) == fixed.file_sha256(new):
        return [f"--new {new} has the sha256 of --base {base} (the same run on both sides)"]
    return []


SELFCHECK_EMPTY_LISTS = ("l2_pass_to_fail", "new_fault", "ready_failures",
                         "ready_improved_record")
SELFCHECK_BOTH_MISSING = 7
"""4a-4 6 table: the expectations of the stored H-6 against itself with the real judge."""


def selfcheck_problems(report: dict, problems: compare.Problems) -> list[str]:
    """Why a ``t12 --bundle VBH`` report of H-6 against itself is not the 4a-4 6 table."""
    missed = []
    if problems.status() != compare.STATUS_PASS:
        missed.append(f"status {problems.status()} (not / defect / failed "
                      f"{len(problems.not_judgeable)} / {len(problems.setting_defects)} / "
                      f"{len(problems.failures)})")
    if report.get("pairs") != DG3_PAIRS:
        missed.append(f"pairs {report.get('pairs')}")
    missed += [f"{key} not empty" for key in SELFCHECK_EMPTY_LISTS if report.get(key)]
    both_missing = len(report.get("ready_both_missing_record") or [])
    if both_missing != SELFCHECK_BOTH_MISSING:
        missed.append(f"ready_both_missing_record {both_missing}")
    for level, transitions in (report.get("grade_transitions_record") or {}).items():
        other = [name for name in transitions if name.split("->")[0] != name.split("->")[1]]
        if other:
            missed.append(f"{level} transitions other than X->X: {other}")
    return missed


def t12_selfcheck(h6: Path, judge: Path, judge_sha256: str
                  ) -> tuple[dict, compare.Problems, list[Path]]:
    """4a-4 6 (a step before the run, stored data only): ``t12 --bundle VBH`` with the stored
    H-6 as base and new and the real base judge file on both sides; a miss of the 6 table is a
    failure (exit 1), so T-JR-12 does not start."""
    input_problems = t12_input_problems("VBH", h6, judge, judge_sha256)
    outcome = compare.Problems()
    if input_problems:
        outcome.not_judgeable += input_problems
        return {}, outcome, [h6, judge]
    h6_document, judge_document = _read_json(h6), _read_json(judge)
    report, problems = judge_t12("VBH", h6_document, judge_document, h6_document,
                                 judge_document, check_settings=False)
    l2_lines = sum(run.get("level") == "L2" for run in h6_document["results"])
    missed = selfcheck_problems(report, problems)
    if l2_lines != DG3_L2_LINES:
        missed.append(f"L2 lines {l2_lines}")
    outcome.failures += missed
    return {"t12_report": report, "t12_problems": problems.as_dict(), "l2_lines": l2_lines,
            "expectation_misses": missed}, outcome, [h6, judge]


def make_base_judge(h6: Path, noise: Path, judge_out: Path
                    ) -> tuple[dict, compare.Problems, list[Path]]:
    """4a-3 4.4: ``r79_sensor_judge.py judge <judge_out> <H-6> <L1 lines of noise VB>
    --s4-late-loc`` (``h8_noise_judge_4368.run_r79_judge``); the report gives the judge
    file's sha256 for the record before the run and for ``--base-judge-sha256``."""
    import h8_noise_judge_4368 as h8

    problems = compare.Problems()
    for path, expected, label in ((h6, fixed.H6_SHA256, "--h6"),
                                  (noise, fixed.NOISE_VB_SHA256, "--noise")):
        problem = fixed.sha_problem(path, expected, label)
        problems.not_judgeable += [] if problem is None else [problem]
    extract = l1_reference_path(judge_out)
    problems.not_judgeable += [f"{path} exists (never overwritten)"
                               for path in (judge_out, extract) if path.exists()]
    if problems.not_judgeable:
        return {}, problems, [h6, noise]
    h8.reference_extract(h8.read_run_file(noise), extract)
    run = h8.run_r79_judge(judge_out, [h6, extract])
    if run["exit_code"] != 0 or not judge_out.is_file():
        problems.not_judgeable.append(f"r79_sensor_judge exit {run['exit_code']}")
        return {"judge_run": run}, problems, [h6, noise]
    return {"judge_run": run, "judge_file": str(judge_out),
            "judge_sha256": fixed.file_sha256(judge_out),
            "l1_reference_sha256": fixed.file_sha256(extract)}, problems, [h6, noise, extract]


def l1_reference_path(judge_out: Path) -> Path:
    """The L1 extract written next to the ``base-judge`` file (4a-3 4.4)."""
    return judge_out.with_name(f"{judge_out.stem}_L1_reference.json")


@dataclass(frozen=True)
class Dg3JudgeInputs:
    """``dg3-judge`` inputs (prelaunch audit M-8)."""

    setting: str
    dg3: Path
    l1_reference: Path
    l1_reference_sha256: str
    judge_out: Path


def dg3_input_problems(inputs: Dg3JudgeInputs) -> list[str]:
    """Why a new-side Dg-3 file cannot be judged with the P-1a L1 extract: the extract of
    another sha, a run file without the stored H-6 keys file, lines of another setting or an
    existing judge file."""
    problems = []
    problem = fixed.sha_problem(inputs.l1_reference, inputs.l1_reference_sha256.lower(),
                                "--l1-reference (P-1a extract)")
    problems += [] if problem is None else [problem]
    if inputs.judge_out.exists():
        problems.append(f"{inputs.judge_out} exists (never overwritten)")
    if not inputs.dg3.is_file():
        return [*problems, f"--dg3 {inputs.dg3} missing"]
    document = _read_json(inputs.dg3)
    problems += keys_file_problems("--dg3", document)
    other = sorted({str(line.get("v5_setting")) for line in document.get("results") or []
                    if line.get("v5_setting") != inputs.setting})
    if other:
        problems.append(f"--dg3 lines of setting {other}, not {inputs.setting}")
    return problems


def make_dg3_judge(inputs: Dg3JudgeInputs) -> tuple[dict, compare.Problems, list[Path]]:
    """Prelaunch audit M-8 (4a-3 4.4 "the same command"): the r79 judge file of one new-side
    Dg-3 run (VBH, VBJ or VBJ0) with the P-1a L1 extract, ``r79_sensor_judge.py judge
    <judge_out> <dg3> <extract> --s4-late-loc``; the report gives the judge file's sha256 for
    ``t12 --new-judge-sha256`` (and, for VBJ0, ``--base-judge-sha256`` of the VBJ bundle)."""
    import h8_noise_judge_4368 as h8

    problems = compare.Problems()
    files = [inputs.dg3, inputs.l1_reference]
    problems.not_judgeable += dg3_input_problems(inputs)
    if problems.not_judgeable:
        return {"setting": inputs.setting}, problems, files
    run = h8.run_r79_judge(inputs.judge_out, [inputs.dg3, inputs.l1_reference])
    report = {"setting": inputs.setting, "judge_run": run}
    if run["exit_code"] != 0 or not inputs.judge_out.is_file():
        problems.not_judgeable.append(f"r79_sensor_judge exit {run['exit_code']}")
        return report, problems, files
    report.update(judge_file=str(inputs.judge_out),
                  judge_sha256=fixed.file_sha256(inputs.judge_out),
                  dg3_sha256=fixed.file_sha256(inputs.dg3),
                  l1_reference_sha256=fixed.file_sha256(inputs.l1_reference))
    return report, problems, files


@dataclass(frozen=True)
class JudgeCompareInputs:
    """``base-judge-compare`` inputs (all stored files)."""

    h6: Path
    new_judge: Path
    new_judge_sha256: str
    stored_judge: Path
    stored_h6_judge: Path | None = None
    new_l1_reference: Path | None = None
    stored_l1_reference: Path | None = None


GRADE_FIELDS = ("grade", "failed_gates", "flags")
"""The per-key grade fields compared (``h8_noise_judge_4368.grade_line``)."""


def compare_base_judges(inputs: JudgeCompareInputs
                        ) -> tuple[dict, compare.Problems, list[Path]]:
    """4a-4 erratum 1 (R-2, a record, not a judgement condition): the per-key grades of the
    stored H-6 under the new ``base-judge`` file against the 436.8 path 1 r79 judge of the same
    H-6 (``STORED_H6_R79_JUDGE_SHA256``); with ``stored_h6_judge`` also against that
    ``h6_judge_4368`` report's ``line_details`` grades. A difference is a failure here (exit 1:
    find its cause before T-JR-12); a missing or other input is not judgeable (exit 2)."""
    import h8_noise_judge_4368 as h8

    problems = compare.Problems()
    checks = [(inputs.h6, fixed.H6_SHA256, "--h6"),
              (inputs.new_judge, inputs.new_judge_sha256.lower(), "--new-judge"),
              (inputs.stored_judge, fixed.STORED_H6_R79_JUDGE_SHA256, "--stored-judge")]
    if inputs.stored_h6_judge is not None:  # prelaunch audit R-8: fixed like the others
        checks.append((inputs.stored_h6_judge, fixed.STORED_H6_JUDGE_SHA256,
                       "--stored-h6-judge"))
    problems.not_judgeable += [problem for path, expected, label in checks
                               if (problem := fixed.sha_problem(path, expected, label))]
    files = [path for path, _, _ in checks]
    if problems.not_judgeable:
        return {}, problems, files
    results = _read_json(inputs.h6)["results"]
    new_grades = h8.grade_lines(results, _read_json(inputs.new_judge))
    stored_grades = h8.grade_lines(results, _read_json(inputs.stored_judge))
    report = {"record_only": "4a-4 erratum 1 R-2: not a judgement condition",
              "stored_judge": _grade_differences(new_grades, stored_grades, problems,
                                                 "stored r79 judge")}
    if inputs.stored_h6_judge is not None:
        report["stored_h6_judge"] = _line_grade_differences(
            new_grades, _read_json(inputs.stored_h6_judge), problems)
    report["l1_reference"] = _l1_reference_record(inputs)
    return report, problems, files


def _grade_differences(new: dict, stored: dict, problems: compare.Problems,
                       label: str) -> dict:
    if set(new) != set(stored) or len(new) != DG3_PAIRS:
        problems.not_judgeable.append(f"{label}: {len(new)} / {len(stored)} graded keys, "
                                      f"{DG3_PAIRS} equal keys expected")
        return {"keys": len(new)}
    rows = [{"key": key, **{f"new_{name}": new[key].get(name) for name in GRADE_FIELDS},
             **{f"stored_{name}": stored[key].get(name) for name in GRADE_FIELDS}}
            for key in sorted(new)
            if any(new[key].get(name) != stored[key].get(name) for name in GRADE_FIELDS)]
    if rows:
        problems.failures.append(f"{label}: {len(rows)} keys of other grades (record)")
    return {"keys": len(new), "differing": len(rows), "rows": rows,
            "grade_counts_new": dict(Counter(grade["grade"] for grade in new.values()))}


def _line_grade_differences(new: dict, h6_judge: dict, problems: compare.Problems) -> dict:
    """Against ``h6_judge.json`` ``line_details[].line_grade``."""
    import h8_noise_judge_4368 as h8

    stored = {h8.plain_key(line["key"]): line.get("line_grade") or {}
              for line in h6_judge.get("line_details") or []}
    return _grade_differences(new, stored, problems, "stored h6_judge line grades")


def _l1_reference_record(inputs: JudgeCompareInputs) -> dict:
    """Whether the new L1 extract is the stored one byte for byte (a record)."""
    if inputs.new_l1_reference is None or inputs.stored_l1_reference is None:
        return {"record": "not given"}
    new_sha = fixed.file_sha256(inputs.new_l1_reference)
    stored_sha = fixed.file_sha256(inputs.stored_l1_reference)
    return {"new_sha256": new_sha, "stored_sha256": stored_sha, "equal": new_sha == stored_sha,
            "stored_is_fixed": stored_sha == fixed.STORED_H6_L1_REFERENCE_SHA256}


# --- records (T-JR-13 .. 15) ----------------------------------------------------------------

def judge_records(replays: list[dict], dg3_files: list[dict], lock_rows: list[dict]
                  ) -> tuple[dict, compare.Problems]:
    """T-JR-13 .. 15 (module docstring): T-JR-13 and T-JR-14 are records, T-JR-15's seed net
    force is judged (4a-2 3.4, user decision 2026-11-21); an empty input of any of the three,
    a replay report that is not a judged rev 5 Dg-2 replay of 426 or 135 runs, or the 3.4
    not-judgeable rules make the bundle not judgeable (prelaunch audit M-6)."""
    problems = compare.Problems()
    for name, given in (("T-JR-13 --replay", replays), ("T-JR-14 --dg3", dg3_files),
                        ("T-JR-15 --lock-rows", lock_rows)):
        if not given:
            problems.not_judgeable.append(f"{name}: no input (an empty bundle is never a pass)")
    problems.not_judgeable += replay_report_problems(replays)
    alignment_rows = [_alignment_record(line) for document in dg3_files
                      for line in document.get("results") or []]
    if dg3_files and not alignment_rows:
        problems.not_judgeable.append("T-JR-14: zero Dg-3 lines over the --dg3 files")
    seed_rows = [_lock_record(row) for row in lock_rows]
    for row in seed_rows:
        if row["seed"]["not_judgeable"] is not None:
            problems.not_judgeable.append(f"T-JR-15 {row['setting']}: "
                                          f"{row['seed']['not_judgeable']}")
    if lock_rows and not sum(row["seed"]["rows"] for row in seed_rows):
        problems.not_judgeable.append("T-JR-15: zero seed rows over the rows (4a-2 3.4)")
    over_1n_rows = sum(row["seed"]["over_1N_rows"] for row in seed_rows)
    if over_1n_rows:
        problems.failures.append(f"T-JR-15: {over_1n_rows} seed rows over 1 N (4a-2 3.4)")
    report = {"T-JR-13": [{"runs": replay.get("runs"), "runs_over": replay.get("runs_over"),
                           "J-P3": (replay.get("J-P3") or {}).get("status")}
                          for replay in replays],
              "T-JR-14": alignment_rows,
              "T-JR-15": seed_rows,
              "T-JR-15_seed_rows_over_1N": over_1n_rows}
    return report, problems


def replay_report_problems(replays: list[dict]) -> list[str]:
    """T-JR-13 "오류 0" (prelaunch audit M-6): every report is a ``t4h_replay`` output of
    :data:`REPLAY_RUN_COUNTS` runs, not a test-only one (``judged: False``) or a stop, with one
    row per run and no row error; each expected run count appears."""
    problems = []
    for index, replay in enumerate(replays):
        label = f"T-JR-13 replay {index}"
        rows = replay.get("rows")
        if "stop" in replay or replay.get("judged") is False:
            problems.append(f"{label}: a stop or test-only report (judged False)")
        elif not isinstance(rows, list) or replay.get("runs") != len(rows):
            problems.append(f"{label}: runs {replay.get('runs')!r} without one row per run")
        elif any("error" in row for row in rows):
            problems.append(f"{label}: {sum('error' in row for row in rows)} error rows")
        elif replay.get("runs") not in REPLAY_RUN_COUNTS:
            problems.append(f"{label}: {replay.get('runs')} runs, not one of "
                            f"{REPLAY_RUN_COUNTS}")
    counts = {replay.get("runs") for replay in replays}
    missing = [count for count in REPLAY_RUN_COUNTS if count not in counts]
    if replays and missing:
        problems.append(f"T-JR-13: no replay report of {missing} runs")
    return problems


def _alignment_record(line: dict) -> dict:
    alignment = line.get("lock_window_alignment") or {}
    late = alignment.get("n_late_fallback_by_leg") or {}
    return {"key": line.get("key"), "n_late_fallback_by_leg": late,
            "n_late_over_0": any((value or 0) > 0 for value in late.values())}


def _lock_record(row: dict) -> dict:
    """T-JR-15 per row: relock counts and the 3.4 seed force check of its seed rows."""
    record = row.get("hydraulics_record") or {}
    return {"setting": (row.get("job") or {}).get("setting") or row.get("key"),
            "relock_step_over_1bar_count": record.get("relock_step_over_1bar_count"),
            "p1_retract_seed_count": record.get("p1_retract_seed_count"),
            "p1_retract_seed_step_max_bar": record.get("p1_retract_seed_step_max_bar"),
            "seed": compare.seed_force_check(record)}


# --- command line ---------------------------------------------------------------------------

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    t8 = commands.add_parser("t8")
    t8.add_argument("--out", type=Path, required=True)
    t8.add_argument("--stored", type=Path, required=True,
                    help="stored VB lines of the current controller (resume_k1/h10_reuse_rerun)")
    t8.add_argument("--stored-t4h-dir", type=Path, default=None,
                    help="default <stored stem>_t4h next to --stored")
    t8.add_argument("--rerun", type=Path, required=True, help="run_v5 j9_t8 output")
    t8.add_argument("--rerun-t4h-dir", type=Path, default=None)
    t8.add_argument("--main-jsonl", type=Path, required=True,
                    help="stored v5/main.jsonl: the 22 jobs of the revision 8 7.2 rule")
    t12 = commands.add_parser("t12")
    t12.add_argument("--out", type=Path, required=True)
    t12.add_argument("--bundle", choices=sorted(BUNDLE_BASE), required=True)
    for name in ("base", "base-judge", "new", "new-judge"):
        t12.add_argument(f"--{name}", type=Path, required=True)
    t12.add_argument("--base-judge-sha256", default=None,
                     help="the sha256 of --base-judge (VBH: P-1a, VBJ: the VBJ0 dg3-judge "
                          "report; required, without it not judgeable)")
    t12.add_argument("--new-judge-sha256", default=None,
                     help="the sha256 of --new-judge (its dg3-judge report; required)")
    dg3_judge = commands.add_parser(
        "dg3-judge", help="M-8: the judge file of a new-side Dg-3 run with the P-1a L1 extract")
    dg3_judge.add_argument("--out", type=Path, required=True)
    dg3_judge.add_argument("--setting", choices=T8_JUDGED_SETTINGS, required=True)
    dg3_judge.add_argument("--dg3", type=Path, required=True,
                           help="las_t3_dg3 output of the setting (--keys-file = stored H-6)")
    dg3_judge.add_argument("--l1-reference", type=Path, required=True,
                           help="P-1a h6_base_judge_L1_reference.json")
    dg3_judge.add_argument("--l1-reference-sha256", required=True,
                           help="l1_reference_sha256 of the P-1a base-judge report")
    dg3_judge.add_argument("--judge-out", type=Path, required=True)
    base_judge = commands.add_parser("base-judge",
                                     help="4a-3 4.4: the H-6 base judge file (r79_sensor_judge)")
    base_judge.add_argument("--out", type=Path, required=True)
    base_judge.add_argument("--h6", type=Path, required=True)
    base_judge.add_argument("--noise", type=Path, required=True,
                            help="resume_k1/h8_noise_VB.json (its L1 lines are the reference)")
    base_judge.add_argument("--judge-out", type=Path, required=True)
    judges = commands.add_parser(
        "base-judge-compare",
        help="4a-4 erratum 1 R-2: new H-6 judge grades against the 436.8 path 1 judge (record)")
    judges.add_argument("--out", type=Path, required=True)
    judges.add_argument("--h6", type=Path, required=True)
    judges.add_argument("--new-judge", type=Path, required=True)
    judges.add_argument("--new-judge-sha256", required=True)
    judges.add_argument("--stored-judge", type=Path, required=True,
                        help="verif_matrix/v5_resume_4368/judge_932f1fb/harness_path1/"
                             "h6_r79_judge.json")
    judges.add_argument("--stored-h6-judge", type=Path, default=None,
                        help="the same folder's h6_judge.json (line grades, optional)")
    judges.add_argument("--new-l1-reference", type=Path, default=None)
    judges.add_argument("--stored-l1-reference", type=Path, default=None)
    selfcheck = commands.add_parser("t12-selfcheck",
                                    help="4a-4 6: stored H-6 against itself with the real judge")
    selfcheck.add_argument("--out", type=Path, required=True)
    selfcheck.add_argument("--h6", type=Path, required=True)
    selfcheck.add_argument("--judge", type=Path, required=True)
    selfcheck.add_argument("--judge-sha256", required=True)
    records = commands.add_parser("records")
    records.add_argument("--out", type=Path, required=True)
    records.add_argument("--replay", type=Path, nargs="*", default=[])
    records.add_argument("--dg3", type=Path, nargs="*", default=[])
    records.add_argument("--lock-rows", type=Path, nargs="*", default=[],
                         help="run_v5 jsonl files (VBJ 135 rows, case E)")
    return parser


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(args: argparse.Namespace) -> tuple[dict, compare.Problems, list[Path]]:
    if args.command == "t8":
        problems = compare.Problems()
        inputs, files = t8_inputs(args, problems)
        return judge_t8(inputs, problems), problems, files
    if args.command == "t12":
        input_problems = [*t12_input_problems(args.bundle, args.base, args.base_judge,
                                              args.base_judge_sha256),
                          *judge_sha_problems("--new-judge", args.new_judge,
                                              args.new_judge_sha256)]
        report, problems = judge_t12(args.bundle, _read_json(args.base),
                                     _read_json(args.base_judge), _read_json(args.new),
                                     _read_json(args.new_judge))
        problems.not_judgeable[:0] = input_problems
        problems.setting_defects[:0] = t12_file_defects(args.base, args.new)
        return report, problems, [args.base, args.base_judge, args.new, args.new_judge]
    if args.command == "dg3-judge":
        return make_dg3_judge(Dg3JudgeInputs(args.setting, args.dg3, args.l1_reference,
                                             args.l1_reference_sha256, args.judge_out))
    if args.command == "base-judge":
        return make_base_judge(args.h6, args.noise, args.judge_out)
    if args.command == "t12-selfcheck":
        return t12_selfcheck(args.h6, args.judge, args.judge_sha256)
    if args.command == "base-judge-compare":
        return compare_base_judges(JudgeCompareInputs(
            args.h6, args.new_judge, args.new_judge_sha256, args.stored_judge,
            args.stored_h6_judge, args.new_l1_reference, args.stored_l1_reference))
    lock_rows = [row for path in args.lock_rows for row in _read_json_lines(path)]
    report, problems = judge_records([_read_json(path) for path in args.replay],
                                     [_read_json(path) for path in args.dg3], lock_rows)
    return report, problems, [*args.replay, *args.dg3, *args.lock_rows]


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error(f"{args.out} exists (a new report never overwrites one)")
    inputs: list[Path] = []
    try:
        report, problems, inputs = _run(args)
        report.update(problems.as_dict())
        status = problems.status()
    except (OSError, KeyError, ValueError) as exc:
        report, status = {"error": f"{type(exc).__name__}: {exc}"}, compare.STATUS_ERROR
    report.update(status=status, command=args.command,
                  inputs=[{"path": str(path), "sha256": compare.file_sha256(path)}
                          for path in inputs if path.is_file()])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1, default=float), encoding="utf-8")
    print(json.dumps({"status": status, "out": str(args.out),
                      **{f"{kind}_count": len(report.get(kind) or [])
                         for kind in ("setting_defects", "not_judgeable", "failures")}}))
    return compare.STATUS_EXIT[status]


if __name__ == "__main__":
    sys.exit(main())
