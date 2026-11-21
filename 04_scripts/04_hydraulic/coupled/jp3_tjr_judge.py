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
             M-4 with the line rules of addendum 4a-7 1.2: a declared head-only job (4a-7
             1.1: T4h meta ``head_only_declared``, else the line's, else the harness steady
             path) has no ③ record and ① = ② = 0; an event-path job has its ③ record
             (VBH / VBJ: rev 5 of the 13.6 identity, checked on rev 5 records only) and
             ② > 0 (VBH: ① = 0; VBJ / VBJ0, P4 on: ① = k ②, k of 4a-8 2 = 1 on these
             run_v5 lines); otherwise a setting defect of
             its test. A setting other than 18 declared / 4 event jobs makes its test not
             judgeable. A VB line breaking the same rules adds to the T-JR-10
             "저장값 노후 확인 전" reason (4a-5 2 VB row, prelaunch audit N-4).
             Addendum 4a-5 2: a ``commands_sha256`` that is not a 64-character string
             on either side of a T-JR-10 or T-JR-11 pair makes that test not judgeable (a
             broken record, not a T8 difference).
``t12``      T-JR-12 (13.9, 4a-3 4) of one bundle: ``--bundle VBH`` = VBH against the stored H-6
             (rev 4), ``--bundle VBJ`` = VBJ against VBJ0. Exactly 135 pairs by plain key,
             exactly 1 L2 line. Failure: the L2 line's base grade pass / flag and new grade fail
             (``r79_sensor_judge`` via ``h8_noise_judge_4368.grade_line``; every level's grade
             transitions are a record), a new FAULT name, and the READY table of 4a-3 4.2 (READY
             = ``r79_sensor_judge._ready_time``: base READY and new READY more than 30 s later or
             none = fail; both none and base none / new READY = records). VBJ: J-P3
             (``j_p3_judgement_rev5``, 1 judged row expected; ``judged_key_missing``,
             ``no_judged_runs`` and, judged rows but not 1, ``judged_row_count_mismatch`` are
             not judgeable, 4a-5 3.3, 4a-7 erratum 1 7) and the P4 evidence of the VBJ lines
             (also ① = k ② > 0, erratum 1 9: event-path lines; addendum 4a-8 2: k = 2 on an
             r79 key whose third token is ``g8``, else 1) and of their VBJ0 base lines
             (4a-2 B2, 4a-3 4.4; VBJ and VBJ0 run with
             ``R79_ROD_MODEL=plant_truth``). Records: the R5-7 columns of 5.5 with the
             ``ret_after_gate_s`` resolution (R9). 4a-4 5: VBH needs the fixed H-6 as
             ``--base``; both bundles need ``--base-judge-sha256`` and ``--new-judge-sha256``
             (the ``base-judge`` / ``dg3-judge`` reports; prelaunch audit M-8); without them,
             or with other files, not judgeable. The P4 evidence applies to the 436.9 lines
             only (``v5_setting`` in :data:`JP3_LINE_SETTINGS`; the stored H-6 VB lines predate
             the evidence keys: prelaunch audit B-1). Setting defects (M-3): a new line not of
             the bundle's setting or not rev 5, a VBJ base line not VBJ0, the new file equal to
             the base file. Not judgeable (M-8): a new (VBJ: also base) file whose meta
             ``keys_file`` is not the stored H-6 (135 keys). A new-side
             ``LockWindowMismatchError`` error line is the T-JR-14 (가) failure (exit 1, the
             pairs are not compared; prelaunch audit N-1); other error lines are not judgeable.
             Addendum 4a-8 5: each received judge file must grade every line of its side
             (row count and key set = the lines, unmatched 0, errors 0; a mismatch line is
             left out), else not judgeable.
``dg3-judge``      Prelaunch audit M-8: the judge file of one new-side Dg-3 run (VBH, VBJ,
             VBJ0) with its L1 reference (addendum 4a-8 4: VBH the P-1a extract, its sha the
             fixed ``a591c3a8...``; VBJ / VBJ0 the L1 run of the setting on the
             ``--l1-keys-file``, checked by 4a-8 4.3: 102 lines, no error, L1, plant_truth,
             the setting, candidate current, the key file's (harness, inner) set, meta
             ``keys_file``); the run's meta ``keys_file`` must be the stored H-6, its lines of
             the setting, ``--dg3-sha256`` (when given) its sha. The judge file must grade
             every Dg-3 line (4a-8 5: rows = lines, unmatched 0, errors 0; else not
             judgeable). Reports the judge file's sha256. An existing ``--judge-out`` is
             refused.
``l1-keys``        Addendum 4a-8 4.2: writes the VBJ / VBJ0 L1 key file (one
             ``L1|s0|<harness>|<case_index>|<inner>`` per distinct (harness, inner) of the
             fixed stored H-6, first-appearance order, 102 keys; with ``--l1-extract`` every
             key must be in the fixed L1 extract) and reports its sha256.
``l1-hash-record`` Addendum 4a-8 4.5 (a record): per (harness, inner) of the VBJ and VBJ0 L1
             runs, the counts of the same and of other command hashes.
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
``records``  T-JR-13 .. T-JR-15, all judged (addendum 4a-5 1; user decisions 1 and 4). Any of
             ``--replay``, ``--dg3``, ``--lock-rows`` empty: not judgeable.
             T-JR-13: exactly two ``t4h_replay --extend-start-revision 5`` reports, one of the
             426 h10 T4h runs and one of the 135 H-6 T4h runs; their row ``file`` names must
             be the fixed ``--t4h-sums`` lists (the report records no folder; 4a-5 1 end).
             Failed: an error row. Not judgeable: other report count / run counts, rows !=
             runs, ``extend_start_revision`` missing or not 5, a test-only (``judged:
             False``) or stopped report, other file names, ``--t4h-sums`` not the fixed lists.
             T-JR-14: VBH and VBJ Dg-3 lines, 135 each. Failed: a ``LockWindowMismatchError``
             error line (the fallback log mismatch, 가) or ``lock_window_alignment.
             n_late_fallback`` >= 1 (J11, 나). Not judgeable: other line counts or settings,
             a bundle whose key set is not the 135 stored H-6 keys (``--h6``, 4a-5 erratum 1),
             no ``lock_window_alignment`` or a non-integer ``n_late_fallback`` (a ``reason``
             record), any other error line. Records: ``n_late_by_leg``, ``margin_min_s_by_leg``.
             T-JR-15: VBJ / LSJ1..4 rows (Dg-3 VBJ lines and case E run_v5 rows). Failed: a
             seed row with ``|net_force_seed_step_N|`` > 1 N (4a-2 3.4) or
             ``relock_step_over_1bar_count`` >= 1. Not judgeable: the 3.4 rules, the relock key
             missing, zero seed rows, and a judged set other than the fixed one of 4a-5
             erratum 1 (the Dg-3 VBJ 135 lines of the stored H-6 keys + the five j9_cases
             case E rows, VBJ / LSJ1 .. LSJ4 once each; missing, repeated or other rows). VBH
             (and other) rows are records.

Exit codes and ``status`` (all sub-commands):

======  =================  ===================================================================
exit    status             meaning
======  =================  ===================================================================
0       ``pass``           the bundle passes (``base-judge`` / ``dg3-judge``: written)
1       ``failed``         a failure of 5.5 / 13.9 (T8 hash, pass -> fail, new FAULT, READY,
                           J-P3 H-7, ``records``: a T-JR-13 error row, a T-JR-14 mismatch or
                           late line, a T-JR-15 seed or relock row; ``base-judge-compare``:
                           grades differ, a record); stop (13.5)
2       ``not_judgeable``  a pair without a result, another pair or L2 count, a missing key
                           or L2 grade, a stored line of another tag / revision; an existing
                           ``--out`` or another argument error
2       ``setting_defect`` a wrong rev 5 identity or P4 evidence (outranks the others)
3       ``error``          a tool error (``jp3_baseline_compare.TOOL_ERRORS``: a file missing,
                           broken JSON, an input of another shape); not a judgement (4a-5 5.1)
======  =================  ===================================================================

``--help`` of every sub-command prints this table (:data:`EXIT_TABLE`).

The report records the sha256 of every input. The stdout's last line is JSON with ``status``,
the problem counts and the report path only.

Batch commands (dynamics-dev, project root; the main session launches them):
  run_v5.py j9_t8 --out <folder>/j9_t8.jsonl --mask <hex>        (T-JR-10 / 11, 88 rows; the
      22 jobs come from the stored v5/main.jsonl of the main checkout)
  for VBH / VBJ / VBJ0 (T-JR-12, the 135 stored dg3 keys of resume_k1/h6_dg3_v4on.json):
    env R79_V5_SETTING=<setting> R79_T4H_DIR=<folder>/<setting>_t4h LAS_T3_DG3_LAS=on
        LAS_T3_DG3_K1=on LAS_T3_DG3_P3=on [R79_ROD_MODEL=plant_truth for VBJ / VBJ0]
    jp3_run_identity.py wrap <folder>/dg3_<setting>.json -- <python.exe> -I -B
        las_t3_dg3.py <root> run <folder>/dg3_<setting>.json --levels L2,L3
        --keys-file <resume_k1/h6_dg3_v4on.json>          (meta keys_file = the fixed H-6;
        the wrap writes dg3_<setting>.identity.json, 4a-5 4)
  then (M-8) jp3_tjr_judge.py dg3-judge --setting <setting> --dg3 <folder>/dg3_<setting>.json
      --l1-reference <pre>/h6_base_judge_L1_reference.json --l1-reference-sha256
      <l1_reference_sha256 of bj.json> --judge-out <folder>/dg3_<setting>_judge.json
      --out <folder>/dg3_<setting>_judge_report.json
  and t12 --bundle VBH (base H-6, --base-judge-sha256 = P-1a) / --bundle VBJ (base VBJ0,
      --base-judge-sha256 = the VBJ0 dg3-judge report), --new-judge-sha256 = its report
  records (T-JR-13 .. 15): jp3_tjr_judge.py records --replay <h10 replay>.json <H-6
      replay>.json --t4h-sums <prelaunch_j9>/h10_reuse_rerun_t4h.SHA256SUMS
      <prelaunch_j9>/h6_dg3_v4on_t4h.SHA256SUMS --dg3 <folder>/dg3_VBH.json
      <folder>/dg3_VBJ.json --h6 <resume_k1/h6_dg3_v4on.json> --lock-rows
      <folder>/dg3_VBJ.json <cases>/j9_cases.jsonl --out <judge>/records.json
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
import jp3_rejudge_inputs as rejudge  # noqa: E402
import jp3_t8_rules as t8_rules  # noqa: E402
from j_p3_inputs import REV5_JUDGED_SETTINGS  # noqa: E402

T8_JOBS = 22
"""4a-3 2: the revision 8 7.2 rule (``run_v5.p3_hash_jobs``) replaces the T-P3-5 20 rows."""
T8_JUDGED_SETTINGS = ("VBH", "VBJ", "VBJ0")
"""``j9_t8`` settings the judgement reads; its VB lines are the 4a-3 5.3 record only."""
T8_TEST_SETTINGS = {"T-JR-10": ("VBH",), "T-JR-11": ("VBJ", "VBJ0")}
"""The ``j9_t8`` settings whose line checks (M-4) belong to each test."""
T8_REVISION_5_SETTINGS = ("VBH", "VBJ")
"""③ rev 5 on (VBJ0 = the same plant with ③ off: no rev 5 identity)."""
T8_P4_SETTINGS = ("VBJ", "VBJ0")
"""P4 on (``rod_reading_truth``): an event line has ① truth reads = ② monitor rod reads."""
T8_JOB_SPLIT = (18, 4)
"""Addendum 4a-7 1.1: declared head-only (steady) and event-path jobs of the 22 rule jobs."""
EVIDENCE_COUNT_KEYS = ("rod_reading_truth_calls", "two_pressure_reads")
STORED_SETTING = "VB"
VB_STALE_REASON = "저장값 노후 확인 전(4a-3 5.3)"
"""4a-4 4: the reason T-JR-10 is not judgeable when the VB record is not 22 equal lines."""
DG3_PAIRS = 135
DG3_L2_LINES = 1
JUDGED_ROW_COUNT_MISMATCH = "judged_row_count_mismatch"
"""Addendum 4a-7 erratum 1 7: a bundle with judged rows, but not :data:`DG3_L2_LINES` of them
(``extend_start_bound.j_p3_judgement_rev5`` names it ``no_judged_runs``; zero judged rows keep
that name). Not judgeable either way."""
JUDGED_LEVEL = "L2"
"""4a-3 4.3: pass -> fail is judged on the L2 line only (all transitions are recorded)."""
READY_DELAY_LIMIT_S = 30.0
BUNDLE_BASE = {"VBH": "stored H-6 (rev 4)", "VBJ": "VBJ0"}
BUNDLE_BASE_SETTING = {"VBH": "VB", "VBJ": "VBJ0"}
"""Prelaunch audit M-3: the ``v5_setting`` of the base lines (the stored H-6 is a VB run)."""
JP3_LINE_SETTINGS = ("VBH", "VBJ", "VBJ0", "LSH1", "LSH2", "LSH3", "LSH4", "LSJ1", "LSJ2",
                     "LSJ3", "LSJ4", "VBK0")
"""436.9 settings (``run_v5.JP3_SETTINGS``): their lines carry the P4 evidence keys (B-1);
edition 5 VBK0 (the VBJ0 plant, P4 on) too."""
REPLAY_RUN_COUNTS = (426, 135)
"""T-JR-13 (addendum 4a-5 1): the replays of the stored h10 T4h (426 npz) and H-6 T4h (135
npz) folders, one report each."""
REPLAY_REVISION_KEY = "extend_start_revision"
REPLAY_REVISION = 5
"""``t4h_replay --extend-start-revision 5``: the report's ③ revision record (4a-5 1)."""
T4H_SUMS_SHA256 = {"h10_reuse_rerun_t4h.SHA256SUMS": fixed.H10_T4H_SUMS_SHA256,
                   "h6_dg3_v4on_t4h.SHA256SUMS": fixed.H6_T4H_SUMS_SHA256}
"""``--t4h-sums``: the fixed name lists of the two T4h input folders (``prelaunch_j9``)."""
T_JR_14_BUNDLES = ("VBH", "VBJ")
LOCK_WINDOW_MISMATCH_ERROR = "LockWindowMismatchError"
"""``lock_window_alignment.LockWindowMismatchError`` (``stretch_mismatch``): a T-JR-14 (가)
log mismatch; an r79 error line starts with the exception's class name."""
T_JR_15_JUDGED_SETTINGS = ("VBJ", "LSJ1", "LSJ2", "LSJ3", "LSJ4")
"""4a-5 1 T-JR-15: VBJ 135 Dg-3 lines and the case E rows; VBH rows are records."""
T_JR_15_DG3_SETTING = "VBJ"
DG3_SOURCE, RUN_V5_SOURCE = "dg3", "run_v5"
"""``--lock-rows`` row kinds: a Dg-3 line (``key``) or a run_v5 row (``job``)."""
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
    line_meta: dict[str, dict[str, dict | None]] = field(default_factory=dict)
    """Setting -> job key -> T4h meta of the rerun line (4a-7 1.1 ``head_only_declared``)."""


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
        tests[name].not_judgeable += t8_split_problems(inputs, settings)
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
    """The line rules of addendum 4a-7 1.2 (replacing the 4a-5 2 table) on the rule jobs of
    ``settings``: a declared head-only job's line (4a-7 1.1, :func:`is_head_only_line`) has
    no ③ record and both evidence counts 0; an event-path line has a ③ record (VBH / VBJ:
    revision 5 of the 13.6 identity) and rod reads; otherwise a setting defect."""
    defects = []
    for setting in settings:
        lines = inputs.rerun.get(setting, {})
        for key in inputs.rule_jobs:
            line = lines.get(key)
            if line is None:
                continue  # a missing line is not judgeable (_rows_ok)
            meta = inputs.line_meta.get(setting, {}).get(key)
            problems = t8_line_problems(setting, line, is_head_only_line(line, meta))
            defects += [f"{setting} {key}: {text}" for text in problems]
    return defects


def t8_split_problems(inputs: T8Inputs, settings: tuple[str, ...]) -> list[str]:
    """4a-7 1.1: every setting has 18 declared head-only and 4 event-path rule jobs; another
    split makes its test not judgeable."""
    problems = []
    for setting in settings:
        lines = inputs.rerun.get(setting, {})
        declared = sum(is_head_only_line(lines[key], inputs.line_meta.get(setting, {}).get(key))
                       for key in inputs.rule_jobs if key in lines)
        events = sum(key in lines for key in inputs.rule_jobs) - declared
        if (declared, events) != T8_JOB_SPLIT:
            problems.append(f"{setting}: {declared} head-only / {events} event jobs, "
                            f"{T8_JOB_SPLIT[0]} / {T8_JOB_SPLIT[1]} expected (4a-7 1.1)")
    return problems


def is_head_only_line(line: dict, meta: dict | None) -> bool:
    """4a-7 1.1: the T4h meta ``head_only_declared``, else the line's ``head_only_declared``,
    else the harness steady path of the job's case (``jp3_baseline_compare.is_head_only_line``,
    shared with the J-P3 judged-line evidence check of erratum 1 9)."""
    return compare.is_head_only_line(line, meta)


def t8_line_problems(setting: str, line: dict, is_declared: bool) -> list[str]:
    """One line against the 4a-7 1.2 table (``setting``: VBH, VBJ, VBJ0 or VB)."""
    record = line.get("hydraulics_record") or {}
    check = record.get("extend_bound_check")
    counts = {name: record.get(name) for name in EVIDENCE_COUNT_KEYS}
    missing = [name for name, value in counts.items() if not isinstance(value, int)]
    if missing:
        return [f"P4 evidence keys missing: {missing}"]
    truth, reads = counts["rod_reading_truth_calls"], counts["two_pressure_reads"]
    if is_declared:
        problems = ["head-only declared job with an extend_bound_check record"] if check else []
        if truth or reads:
            problems.append(f"head-only declared job with rod reads ({truth} truth, {reads} "
                            "monitor; 0 and 0 needed)")
        return problems
    problems = []
    if setting in T8_REVISION_5_SETTINGS:
        if (check or {}).get("rule_revision") != 5:
            problems.append(f"event job: rule_revision {(check or {}).get('rule_revision')!r}, "
                            "not 5")
        else:  # 13.6 identity only on lines with a revision 5 record (4a-7 1.2)
            problems += compare.identity_problems(line)
    elif setting == STORED_SETTING and not check:
        problems.append("event job without an extend_bound_check record")
    if reads <= 0:
        problems.append("event job without monitor rod reads (② = 0)")
    if setting in T8_P4_SETTINGS:  # the 4a-7 1.2 table: VBJ / VBJ0 ① = k ②, VBH / VB ① = 0
        multiplier = compare.evidence_multiplier(line)  # 4a-8 2 (run_v5 lines: k = 1)
        if truth != multiplier * reads:
            problems.append(f"rod_reading_truth: {truth} truth readings, {reads} monitor rod "
                            f"reads (k = {multiplier}: truth = k x monitor > 0 needed)")
    elif truth != 0:
        problems.append(f"P4 off but {truth} truth readings")
    return problems


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
    if (vb_record["missing"] or vb_record["error_rows"] or vb_record["differing_count"]
            or vb_record["evidence_problems"]):
        problems.append(f"{VB_STALE_REASON}: VB lines missing {vb_record['missing']}, error "
                        f"{vb_record['error_rows']}, other hash {vb_record['differing_count']}, "
                        f"P4 evidence {len(vb_record['evidence_problems'])} (4a-5 2: 1 = 0)")
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
    b_problems = t8_rules.condition_b_problems(stored, new)
    broken = broken_hash_sides({"stored": stored, "new": new})
    if broken:  # addendum 4a-5 2: a broken record, not a T8 difference
        problems.not_judgeable.append(f"{key}: commands_sha256 not 64 characters ({broken})")
        b_problems = [text for text in b_problems if not text.startswith(HASH_FIELD)]
    pair_problems += [f"B: {text}" for text in b_problems]
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
    for key in inputs.rule_jobs:  # addendum 4a-5 2: a hash not of 64 characters
        broken = broken_hash_sides({side: inputs.rerun[side][key] for side in ("VBJ", "VBJ0")})
        if broken:
            problems.not_judgeable.append(f"{key}: commands_sha256 not 64 characters "
                                          f"({broken})")
    if problems.not_judgeable:
        return {}
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
    # addendum 4a-5 2 (prelaunch audit N-4): the VB lines have no P4 reading (1 = 0); 4a-7
    # 1.2: the head-only and event line rules apply to them too
    evidence = []
    for key in inputs.rule_jobs:
        line = vb_lines.get(key)
        if line is not None:
            meta = inputs.line_meta.get(STORED_SETTING, {}).get(key)
            evidence += [f"VB {key}: {text}" for text in t8_line_problems(
                STORED_SETTING, line, is_head_only_line(line, meta))]
    return {"lines": T8_JOBS - len(missing), "evidence_problems": evidence,
            "equal": T8_JOBS - len(missing) - len(differing), "differing_count": len(differing),
            "differing": differing[:10], "missing": len(missing),
            "error_rows": inputs.bad_rows.get(f"rerun:{STORED_SETTING}", 0)}


HASH_FIELD = "commands_sha256"


def broken_hash_sides(lines: dict[str, dict]) -> list[str]:
    """The sides whose ``commands_sha256`` is not a 64-character string (addendum 4a-5 2)."""
    return [side for side, line in lines.items()
            if not (isinstance(line.get(HASH_FIELD), str)
                    and len(line[HASH_FIELD]) == t8_rules.HASH_LENGTH)]


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
    line_meta = {setting: {key: _t4h_meta(rerun_dir, rerun[setting][key])
                           for key in rule_jobs if key in rerun.get(setting, {})}
                 for setting in (*T8_JUDGED_SETTINGS, STORED_SETTING)}
    inputs = T8Inputs(rule_jobs, stored, rerun, stored_meta, rerun_meta, bad_rows,
                      stored_problem, line_meta)
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
    new_lines = _dg3_lines(new["results"], "new", problems, mismatch_fails=True)
    if check_settings:
        problems.setting_defects += bundle_setting_problems(bundle, base_lines, new_lines)
        problems.not_judgeable += keys_file_problems("new", new)
        if bundle == "VBJ":
            problems.not_judgeable += keys_file_problems("base", base)
    mismatches = sorted(h8.plain_key(run["key"]) for run in new["results"]
                        if is_lock_window_mismatch(run))
    if mismatches:  # prelaunch audit N-1: a failure as it is, the pairs are not compared
        return {"bundle": bundle, "lock_window_mismatch_keys": mismatches}, problems
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
            problems.setting_defects += [  # 4a-8 2: k = 2 on the r79 G8 lines
                f"{label} {key}: {text}" for text in compare.line_evidence_problems(line)]
            if line.get("v5_setting") in REV5_JUDGED_SETTINGS:  # erratum 1 9: J-P3 lines
                problems.setting_defects += [
                    f"{label} {key}: {text}" for text in compare.judged_line_evidence_problems(
                        line.get("hydraulics_record"), is_head_only_line(line, None),
                        compare.evidence_multiplier(line))]


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


def _dg3_lines(results: list[dict], label: str, problems: compare.Problems, *,
               mismatch_fails: bool = False) -> dict[str, dict]:
    """The result lines by plain key. An error line is not judgeable, except a
    ``LockWindowMismatchError`` line of the new side (``mismatch_fails``): the T-JR-14 (가)
    failure of 4a-5 1, reported here as a failure so that step 6 does not stop as not
    judgeable (prelaunch audit N-1)."""
    import h8_noise_judge_4368 as h8

    lines = {}
    for run in results:
        key = h8.plain_key(run["key"])
        if mismatch_fails and is_lock_window_mismatch(run):
            problems.failures.append(f"{label} {key}: T-JR-14 failure "
                                     f"({LOCK_WINDOW_MISMATCH_ERROR})")
            continue
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
    if status == "no_judged_runs" and judgement["runs_judged"]:
        # erratum 1 7: judged rows, but not the fixed number (both not judgeable)
        status = judgement["status"] = JUDGED_ROW_COUNT_MISMATCH
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


def t12_judge_row_problems(documents: dict[str, dict]) -> list[str]:
    """Addendum 4a-8 5 (second item): each received r79 judge file grades every line of its
    Dg-3 side (``compare.judge_rows_problems``: row count and key set = the lines, unmatched
    0, errors 0); a miss is not judgeable (13.2: zero judged rows is never a pass)."""
    problems = []
    for side in ("base", "new"):
        lines = [line for line in documents[side].get("results") or []
                 if line.get("level") != L1_LEVEL]
        problems += compare.judge_rows_problems(f"--{side}-judge", lines,
                                                documents[f"{side}_judge"],
                                                mismatch_keys(lines))
    return problems


def mismatch_keys(lines: list[dict]) -> frozenset[str]:
    """Plain keys of the ``LockWindowMismatchError`` lines: a T-JR-14 failure as it is
    (prelaunch audit N-1), not an ungraded line of 4a-8 5."""
    import h8_noise_judge_4368 as h8

    return frozenset(h8.plain_key(line["key"]) for line in lines
                     if is_lock_window_mismatch(line))


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
    """``dg3-judge`` inputs (prelaunch audit M-8; addendum 4a-8 4, 5)."""

    setting: str
    dg3: Path
    l1_reference: Path
    l1_reference_sha256: str
    judge_out: Path
    l1_keys_file: Path | None = None
    """4a-8 4.2 key file of the VBJ / VBJ0 L1 run (required there, unused for VBH)."""
    dg3_sha256: str | None = None
    """4a-8 6.2 3: the fixed sha256 of a stored Dg-3 file (None: not asserted)."""


PLANT_TRUTH_SETTINGS = ("VBJ", "VBJ0")
"""4a-8 4.1: their L1 reference is a new L1 run of the same setting (``plant_truth``)."""
L1_ROD_MODEL = "plant_truth"
L1_LEVEL = "L1"
L1_CANDIDATE = "current"


def dg3_input_problems(inputs: Dg3JudgeInputs) -> list[str]:
    """Why a new-side Dg-3 file cannot be judged: an L1 reference of another sha than given
    (VBH: also than the fixed P-1a extract, 4a-8 4.1; VBJ / VBJ0: not the 4.3 L1 run of the
    setting), a Dg-3 file of another sha than ``dg3_sha256``, a run file without the stored
    H-6 keys file, lines of another setting or an existing judge file."""
    problems = []
    problem = fixed.sha_problem(inputs.l1_reference, inputs.l1_reference_sha256.lower(),
                                "--l1-reference")
    problems += [] if problem is None else [problem]
    if inputs.setting in PLANT_TRUTH_SETTINGS:
        problems += l1_run_problems(inputs.setting, inputs.l1_reference, inputs.l1_keys_file)
    elif inputs.l1_reference_sha256.lower() != fixed.STORED_H6_L1_REFERENCE_SHA256:
        problems.append(f"--l1-reference-sha256 is not the P-1a extract "
                        f"{fixed.STORED_H6_L1_REFERENCE_SHA256[:12]} (4a-8 4.1: VBH keeps it)")
    if inputs.judge_out.exists():
        problems.append(f"{inputs.judge_out} exists (never overwritten)")
    if not inputs.dg3.is_file():
        return [*problems, f"--dg3 {inputs.dg3} missing"]
    if inputs.dg3_sha256 is not None:
        problem = fixed.sha_problem(inputs.dg3, inputs.dg3_sha256.lower(), "--dg3")
        problems += [] if problem is None else [problem]
    document = _read_json(inputs.dg3)
    problems += keys_file_problems("--dg3", document)
    other = sorted({str(line.get("v5_setting")) for line in document.get("results") or []
                    if line.get("v5_setting") != inputs.setting})
    if other:
        problems.append(f"--dg3 lines of setting {other}, not {inputs.setting}")
    return problems


def l1_key_pairs(keys: list[str]) -> list[tuple[str, str]]:
    """(harness, inner) of ``L1|s0|<harness>|<case_index>|<inner>`` keys (4a-8 4.2)."""
    import h8_noise_judge_4368 as h8

    pairs = []
    for key in keys:
        tokens = h8.plain_key(key).split("|", 4)
        pairs.append((tokens[2], tokens[4]) if len(tokens) == 5 else ("", key))
    return pairs


def l1_run_problems(setting: str, l1_run: Path, keys_file: Path | None) -> list[str]:
    """Addendum 4a-8 4.3: the VBJ / VBJ0 L1 reference is the L1 run of ``setting`` on the 4.2
    key file - :data:`L1_KEY_COUNT` lines without an error line, each ``level`` L1,
    ``rod_model`` plant_truth, ``v5_setting`` = the setting, ``candidate`` current; its
    (harness, inner) set is the key file's; meta ``keys_file`` names the key file (sha256,
    ``n_keys``). Any miss makes the bundle not judgeable."""
    if keys_file is None or not keys_file.is_file():
        return [f"{setting}: --l1-keys-file missing (4a-8 4.3)"]
    if not l1_run.is_file():
        return [f"{setting}: --l1-reference {l1_run} missing"]
    keys = [str(row["key"]) for row in _read_json(keys_file).get("results") or []]
    document = _read_json(l1_run)
    lines = document.get("results") or []
    problems = []
    if len(keys) != rejudge.L1_KEY_COUNT:
        problems.append(f"{setting}: key file of {len(keys)} keys, {rejudge.L1_KEY_COUNT} "
                        "expected (4a-8 4.2)")
    errors = sum("error" in line for line in lines)
    if len(lines) != rejudge.L1_KEY_COUNT or errors:
        problems.append(f"{setting}: L1 run of {len(lines)} lines, {errors} error lines; "
                        f"{rejudge.L1_KEY_COUNT} and 0 expected (4a-8 4.3)")
    expected_fields = {"level": L1_LEVEL, "rod_model": L1_ROD_MODEL, "v5_setting": setting,
                       "candidate": L1_CANDIDATE}
    for field_name, value in expected_fields.items():
        other = sum(line.get(field_name) != value for line in lines)
        if other:
            problems.append(f"{setting}: {other} L1 lines with {field_name} other than "
                            f"{value!r} (4a-8 4.3)")
    found = {(str(line.get("harness")), str(line.get("inner"))) for line in lines}
    if found != set(l1_key_pairs(keys)):
        problems.append(f"{setting}: L1 (harness, inner) set differs from the key file's "
                        "(4a-8 4.3)")
    record = (document.get("meta") or {}).get("keys_file") or {}
    if record.get("sha256") != fixed.file_sha256(keys_file) or record.get("n_keys") != len(keys):
        problems.append(f"{setting}: L1 meta keys_file is not the key file (sha256 / n_keys, "
                        "4a-8 4.3)")
    return problems


def make_dg3_judge(inputs: Dg3JudgeInputs) -> tuple[dict, compare.Problems, list[Path]]:
    """Prelaunch audit M-8 (4a-3 4.4 "the same command"): the r79 judge file of one new-side
    Dg-3 run (VBH, VBJ or VBJ0) with its L1 reference (VBH: the P-1a extract; VBJ / VBJ0: the
    4a-8 4.3 L1 run of the setting), ``r79_sensor_judge.py judge <judge_out> <dg3> <L1>
    --s4-late-loc``. The judge file must grade every Dg-3 line (4a-8 5:
    ``compare.judge_rows_problems``), else not judgeable. The report gives the judge file's
    sha256 for ``t12 --new-judge-sha256`` (and, for VBJ0, ``--base-judge-sha256`` of the VBJ
    bundle)."""
    import h8_noise_judge_4368 as h8

    problems = compare.Problems()
    files = [inputs.dg3, inputs.l1_reference,
             *([] if inputs.l1_keys_file is None else [inputs.l1_keys_file])]
    problems.not_judgeable += dg3_input_problems(inputs)
    if problems.not_judgeable:
        return {"setting": inputs.setting}, problems, files
    run = h8.run_r79_judge(inputs.judge_out, [inputs.dg3, inputs.l1_reference])
    report = {"setting": inputs.setting, "judge_run": run}
    if run["exit_code"] != 0 or not inputs.judge_out.is_file():
        problems.not_judgeable.append(f"r79_sensor_judge exit {run['exit_code']}")
        return report, problems, files
    lines = [line for line in _read_json(inputs.dg3).get("results") or []
             if line.get("level") != L1_LEVEL]
    judge = _read_json(inputs.judge_out)
    problems.not_judgeable += compare.judge_rows_problems("--judge-out", lines, judge,
                                                          mismatch_keys(lines))
    report.update(judge_file=str(inputs.judge_out),
                  judge_sha256=fixed.file_sha256(inputs.judge_out),
                  dg3_sha256=fixed.file_sha256(inputs.dg3),
                  l1_reference_sha256=fixed.file_sha256(inputs.l1_reference),
                  judge_rows={"runs": len(judge.get("runs") or []),
                              "unmatched": len(judge.get("unmatched") or []),
                              "errors": len(judge.get("errors") or []), "lines": len(lines)})
    return report, problems, files


def l1_hash_record(vbj_l1: Path, vbj0_l1: Path) -> tuple[dict, compare.Problems, list[Path]]:
    """Addendum 4a-8 4.5 (a record, not a judgement): per (harness, inner) whether the VBJ L1
    and the VBJ0 L1 lines have the same command hash (``base.commands_sha256``, else
    ``base.cmd_sha256``); counts only. Not judgeable: a file missing or a pair on one side
    only."""
    problems = compare.Problems()
    by_pair = {}
    for label, path in (("VBJ", vbj_l1), ("VBJ0", vbj0_l1)):
        if not path.is_file():
            problems.not_judgeable.append(f"{label} L1 run {path} missing")
            return {}, problems, [vbj_l1, vbj0_l1]
        by_pair[label] = {(str(line.get("harness")), str(line.get("inner"))): line
                          for line in _read_json(path).get("results") or []}
    pairs = set(by_pair["VBJ"]) | set(by_pair["VBJ0"])
    one_side = pairs ^ (set(by_pair["VBJ"]) & set(by_pair["VBJ0"]))
    if one_side:
        problems.not_judgeable.append(f"{len(one_side)} (harness, inner) pairs on one side only")

    def command_hash(line: dict) -> str | None:
        base = line.get("base") or {}
        return base.get("commands_sha256") or base.get("cmd_sha256")

    shared = sorted(pairs - one_side)
    hashes = [(command_hash(by_pair["VBJ"][pair]), command_hash(by_pair["VBJ0"][pair]))
              for pair in shared]
    report = {"pairs": len(shared),
              "same_command_hash": sum(mine is not None and mine == theirs
                                       for mine, theirs in hashes),
              "other_command_hash": sum(mine != theirs for mine, theirs in hashes),
              "hash_missing": sum(mine is None or theirs is None for mine, theirs in hashes),
              "record_only": "4a-8 4.5: not a judgement"}
    return report, problems, [vbj_l1, vbj0_l1]


# --- l1-keys (addendum 4a-8 4.2) ------------------------------------------------------------

def l1_keys_of(h6: dict) -> list[str]:
    """One key ``L1|s0|<harness>|<case_index>|<inner>`` per distinct (harness, inner) of the
    stored H-6 lines, in the order they first appear (4a-8 4.2)."""
    seen: set[tuple[str, str]] = set()
    keys = []
    for line in h6.get("results") or []:
        pair = (str(line["harness"]), str(line["inner"]))
        if pair in seen:
            continue
        seen.add(pair)
        keys.append(f"{L1_LEVEL}|s0|{pair[0]}|{line['case_index']}|{pair[1]}")
    return keys


def make_l1_keys(h6_path: Path, keys_out: Path,
                 l1_extract: Path | None) -> tuple[dict, compare.Problems, list[Path]]:
    """Addendum 4a-8 4.2: the L1 key file of the VBJ / VBJ0 L1 runs from the fixed stored H-6
    (``{"results": [{"key": ...}]}``, LF bytes). Not judgeable: another H-6 sha, a key count
    other than :data:`jp3_rejudge_inputs.L1_KEY_COUNT`, an existing key file, or (with
    ``l1_extract``, the P-1a / stored L1 extract of the fixed sha) a key not in the extract."""
    import h8_noise_judge_4368 as h8

    problems = compare.Problems()
    files = [h6_path, *([] if l1_extract is None else [l1_extract])]
    problem = fixed.sha_problem(h6_path, fixed.H6_SHA256, "--h6 (stored H-6)")
    if problem is not None:
        problems.not_judgeable.append(problem)
        return {}, problems, files
    if keys_out.exists():
        problems.not_judgeable.append(f"{keys_out} exists (never overwritten)")
        return {}, problems, files
    keys = l1_keys_of(_read_json(h6_path))
    report = {"keys": len(keys), "by_harness": dict(Counter(key.split("|")[2] for key in keys))}
    if len(keys) != rejudge.L1_KEY_COUNT:
        problems.not_judgeable.append(f"{len(keys)} L1 keys, {rejudge.L1_KEY_COUNT} expected "
                                      "(4a-8 4.2)")
    if l1_extract is not None:
        problem = fixed.sha_problem(l1_extract, fixed.STORED_H6_L1_REFERENCE_SHA256,
                                    "--l1-extract")
        if problem is not None:
            problems.not_judgeable.append(problem)
        else:
            extract = _read_json(l1_extract)
            plain = {h8.plain_key(line["key"]) for line in extract.get("results") or []}
            missing = [key for key in keys if key not in plain]
            report["keys_not_in_extract"] = len(missing)
            if missing:
                problems.not_judgeable.append(f"{len(missing)} keys not in the L1 extract")
    if problems.not_judgeable:
        return report, problems, files
    keys_out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps({"results": [{"key": key} for key in keys]}, indent=1) + "\n"
    keys_out.write_bytes(text.encode("utf-8"))
    report.update(keys_file=str(keys_out), keys_file_sha256=fixed.file_sha256(keys_out))
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

@dataclass(frozen=True)
class RecordsInputs:
    """``records`` inputs (addendum 4a-5 1).

    Attributes:
        replays: ``t4h_replay`` reports (T-JR-13).
        dg3_files: Dg-3 run files of VBH and VBJ (T-JR-14).
        lock_rows: run_v5 rows and Dg-3 lines with a ``hydraulics_record`` (T-JR-15).
        t4h_names: Run count -> the T4h file names of its fixed input folder (from the fixed
            ``*_t4h.SHA256SUMS``); the report's row ``file`` names must be these (1, end).
        h6_keys: The 135 plain keys of the stored H-6 (``--h6``): the T-JR-14 line set of
            each bundle and the Dg-3 VBJ part of the T-JR-15 set (4a-5 erratum 1).
    """

    replays: list[dict]
    dg3_files: list[dict]
    lock_rows: list[dict]
    t4h_names: dict[int, set[str]] = field(default_factory=dict)
    h6_keys: frozenset[str] = frozenset()


def judge_records(inputs: RecordsInputs) -> tuple[dict, compare.Problems]:
    """T-JR-13 .. 15 (addendum 4a-5 1 table and erratum 1, user decisions 1 and 4: all three
    judged)."""
    problems = compare.Problems()
    for name, given in (("T-JR-13 --replay", inputs.replays), ("T-JR-14 --dg3", inputs.dg3_files),
                        ("T-JR-15 --lock-rows", inputs.lock_rows)):
        if not given:
            problems.not_judgeable.append(f"{name}: no input (an empty bundle is never a pass)")
    if len(inputs.h6_keys) != DG3_PAIRS:
        problems.not_judgeable.append(f"--h6: {len(inputs.h6_keys)} stored H-6 keys, "
                                      f"{DG3_PAIRS} expected (4a-5 erratum 1)")
    report = {"T-JR-13": judge_t_jr_13(inputs.replays, inputs.t4h_names, problems),
              "T-JR-14": judge_t_jr_14(inputs.dg3_files, inputs.h6_keys, problems),
              "T-JR-15": judge_t_jr_15(inputs.lock_rows, inputs.h6_keys, problems)}
    return report, problems


def h6_keys_of(path: Path | None) -> tuple[frozenset[str], list[str]]:
    """The plain keys of the stored H-6 (its sha asserted; 4a-5 erratum 1)."""
    import h8_noise_judge_4368 as h8

    if path is None:
        return frozenset(), ["--h6 missing (the stored H-6: T-JR-14 / 15 key sets)"]
    problem = fixed.sha_problem(path, fixed.H6_SHA256, "--h6 (stored H-6)")
    if problem is not None:
        return frozenset(), [problem]
    return frozenset(h8.plain_key(run["key"]) for run in _read_json(path)["results"]), []


def key_set_problems(label: str, keys: list[str], expected: frozenset[str]) -> list[str]:
    """Why ``keys`` are not exactly ``expected`` once each (missing, repeated, other keys)."""
    counts = Counter(keys)
    repeated = sorted(key for key, count in counts.items() if count > 1)
    missing, other = sorted(expected - set(counts)), sorted(set(counts) - expected)
    if not (repeated or missing or other):
        return []
    return [f"{label}: key set is not the stored H-6 {len(expected)} keys ({len(missing)} "
            f"missing, {len(repeated)} repeated, {len(other)} other; first "
            f"{(missing + repeated + other)[:2]})"]


# T-JR-13 ---------------------------------------------------------------------------------------

def judge_t_jr_13(replays: list[dict], t4h_names: dict[int, set[str]],
                  problems: compare.Problems) -> list[dict]:
    """Exactly two judged rev 5 replay reports, 426 runs of the h10 T4h folder and 135 of the
    H-6 one, one row per run; an error row fails (4a-5 1)."""
    if replays and Counter(replay.get("runs") for replay in replays) != Counter(
            REPLAY_RUN_COUNTS):
        problems.not_judgeable.append(
            f"T-JR-13: {len(replays)} reports of {[r.get('runs') for r in replays]} runs, "
            f"exactly one each of {REPLAY_RUN_COUNTS} expected")
    records = []
    for index, replay in enumerate(replays):
        label = f"T-JR-13 replay {index}"
        problems.not_judgeable += [f"{label}: {text}"
                                   for text in replay_report_problems(replay, t4h_names)]
        rows = replay.get("rows") if isinstance(replay.get("rows"), list) else []
        error_rows = sum("error" in row for row in rows)
        if error_rows:
            problems.failures.append(f"{label}: {error_rows} replay error rows")
        records.append({"runs": replay.get("runs"), "runs_over": replay.get("runs_over"),
                        "error_rows": error_rows,
                        "extend_start_revision": replay.get(REPLAY_REVISION_KEY),
                        "J-P3": (replay.get("J-P3") or {}).get("status")})
    return records


def replay_report_problems(replay: dict, t4h_names: dict[int, set[str]]) -> list[str]:
    """Why one report is not a judged ``t4h_replay --extend-start-revision 5`` output of its
    fixed input folder (not judgeable)."""
    rows = replay.get("rows")
    if "stop" in replay or replay.get("judged") is False:
        return ["a stop or test-only report (judged False)"]
    if not isinstance(rows, list) or replay.get("runs") != len(rows):
        return [f"runs {replay.get('runs')!r} without one row per run"]
    problems = []
    if replay.get(REPLAY_REVISION_KEY) != REPLAY_REVISION:
        problems.append(f"{REPLAY_REVISION_KEY} {replay.get(REPLAY_REVISION_KEY)!r}, not "
                        f"{REPLAY_REVISION}")
    expected = t4h_names.get(replay.get("runs"))
    names = {str(row.get("file")) for row in rows}
    if expected is None:
        problems.append(f"no fixed T4h folder of {replay.get('runs')} runs (--t4h-sums)")
    elif names != expected:
        problems.append(f"row files are not the fixed T4h folder of {replay.get('runs')} runs "
                        f"({len(names - expected)} other, {len(expected - names)} missing)")
    return problems


def t4h_names_of(sums_files: list[Path]) -> tuple[dict[int, set[str]], list[str]]:
    """Run count -> T4h names of each fixed ``*_t4h.SHA256SUMS`` (its sha asserted)."""
    names, problems = {}, []
    for path in sums_files:
        expected = T4H_SUMS_SHA256.get(path.name)
        problem = (f"--t4h-sums {path.name}: not a fixed T4h list" if expected is None
                   else fixed.sha_problem(path, expected, "--t4h-sums"))
        if problem is not None:
            problems.append(problem)
            continue
        listed = {line.split(maxsplit=1)[1].lstrip("*")
                  for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}
        names[len(listed)] = listed
    missing = [count for count in REPLAY_RUN_COUNTS if count not in names]
    if missing:
        problems.append(f"--t4h-sums: no fixed T4h list of {missing} files")
    return names, problems


# T-JR-14 ---------------------------------------------------------------------------------------

def judge_t_jr_14(dg3_files: list[dict], h6_keys: frozenset[str],
                  problems: compare.Problems) -> dict:
    """VBH and VBJ, 135 lines each with the stored H-6 key set (4a-5 erratum 1): no
    ``LockWindowMismatchError`` line and ``lock_window_alignment.n_late_fallback`` = 0 on every
    line (4a-5 1)."""
    import h8_noise_judge_4368 as h8

    lines_by_setting: dict[str, list[dict]] = {}
    for document in dg3_files:
        for line in document.get("results") or []:
            lines_by_setting.setdefault(str(line.get("v5_setting")), []).append(line)
    if dg3_files:
        counts = {setting: len(lines) for setting, lines in sorted(lines_by_setting.items())}
        if counts != dict.fromkeys(T_JR_14_BUNDLES, DG3_PAIRS):
            problems.not_judgeable.append(f"T-JR-14: lines by setting {counts}, "
                                          f"{DG3_PAIRS} of each of {T_JR_14_BUNDLES} expected")
        for setting in T_JR_14_BUNDLES:
            keys = [h8.plain_key(str(line.get("key")))
                    for line in lines_by_setting.get(setting, [])]
            problems.not_judgeable += key_set_problems(f"T-JR-14 {setting}", keys, h6_keys)
    report = {}
    for setting in T_JR_14_BUNDLES:
        rows = [_alignment_check(line, problems) for line in lines_by_setting.get(setting, [])]
        report[setting] = {"lines": len(rows),
                           "mismatch_error_lines": sum(row["kind"] == "mismatch" for row in rows),
                           "late_lines": sum(row["kind"] == "late" for row in rows),
                           "rows": rows}
    return report


def is_lock_window_mismatch(line: dict) -> bool:
    """An r79 error line of a ``LockWindowMismatchError`` (``r79_sensor_screen.
    v5_record_or_mismatch``: the T-JR-14 (가) failure of 4a-5 1)."""
    return ("error" in line
            and str(line["error"]).split(":", 1)[0].strip() == LOCK_WINDOW_MISMATCH_ERROR)


def _alignment_check(line: dict, problems: compare.Problems) -> dict:
    """One Dg-3 line of T-JR-14 (its kind: ok, late, mismatch, not_judgeable)."""
    label = f"T-JR-14 {line.get('v5_setting')} {line.get('key')}"
    record = {"key": line.get("key"), "kind": "ok"}
    if "error" in line:
        if is_lock_window_mismatch(line):
            problems.failures.append(f"{label}: {LOCK_WINDOW_MISMATCH_ERROR} (log mismatch)")
            return {**record, "kind": "mismatch"}
        problems.not_judgeable.append(f"{label}: error line {str(line['error'])[:80]}")
        return {**record, "kind": "not_judgeable"}
    alignment = line.get("lock_window_alignment")
    late = alignment.get("n_late_fallback") if isinstance(alignment, dict) else None
    if not isinstance(late, int) or isinstance(late, bool):
        reason = alignment.get("reason") if isinstance(alignment, dict) else "no record"
        problems.not_judgeable.append(f"{label}: n_late_fallback {late!r} ({reason})")
        return {**record, "kind": "not_judgeable", "reason": reason}
    record.update(n_late_fallback=late,
                  n_late_by_leg=alignment.get("n_late_by_leg"),
                  margin_min_s_by_leg=alignment.get("margin_min_s_by_leg"))
    if late >= 1:
        problems.failures.append(f"{label}: n_late_fallback {late} (J11)")
        record["kind"] = "late"
    return record


# T-JR-15 ---------------------------------------------------------------------------------------

def judge_t_jr_15(lock_rows: list[dict], h6_keys: frozenset[str],
                  problems: compare.Problems) -> dict:
    """VBJ / LSJ rows: every seed row |net force| <= 1 N (4a-2 3.4) and
    ``relock_step_over_1bar_count`` = 0; VBH (and any other setting) rows are records. The
    judged set is fixed (4a-5 erratum 1): the Dg-3 VBJ 135 lines of the stored H-6 keys and
    the five j9_cases case E rows (VBJ, LSJ1 .. LSJ4 once each)."""
    rows = [_lock_record(row) for row in lock_rows]
    judged = [row for row in rows if row["setting"] in T_JR_15_JUDGED_SETTINGS]
    if lock_rows:
        problems.not_judgeable += judged_set_problems(judged, h6_keys)
    for row in judged:
        label = f"T-JR-15 {row['setting']} {row['key']}"
        if row["lock_window_mismatch"]:  # N-1: no record on the line; a T-JR-14 failure
            problems.failures.append(f"{label}: {LOCK_WINDOW_MISMATCH_ERROR} line "
                                     "(T-JR-14 failure, no T-JR-15 record)")
            continue
        if row["seed"]["not_judgeable"] is not None:
            problems.not_judgeable.append(f"{label}: {row['seed']['not_judgeable']}")
        elif row["seed"]["over_1N_rows"]:
            problems.failures.append(f"{label}: {row['seed']['over_1N_rows']} seed rows over "
                                     "1 N (4a-2 3.4)")
        relocks = row[compare.RELOCK_KEY]
        if not isinstance(relocks, int) or isinstance(relocks, bool):
            problems.not_judgeable.append(f"{label}: {compare.RELOCK_KEY} {relocks!r}")
        elif relocks >= 1:
            problems.failures.append(f"{label}: {compare.RELOCK_KEY} {relocks}")
    if judged and not sum(row["seed"]["rows"] for row in judged):
        problems.not_judgeable.append("T-JR-15: zero seed rows over the judged rows (4a-2 3.4)")
    return {"rows": rows, "judged_rows": len(judged),
            "seed_rows_over_1N": sum(row["seed"]["over_1N_rows"] for row in judged),
            "relock_rows_over_0": sum(isinstance(row[compare.RELOCK_KEY], int)
                                      and row[compare.RELOCK_KEY] >= 1 for row in judged)}


def judged_set_problems(judged: list[dict], h6_keys: frozenset[str]) -> list[str]:
    """Why the judged T-JR-15 rows are not the fixed set of 4a-5 erratum 1 (not judgeable)."""
    dg3 = [row for row in judged if row["source"] == DG3_SOURCE]
    case_rows = [row for row in judged if row["source"] == RUN_V5_SOURCE]
    problems = []
    other_dg3 = sorted({row["setting"] for row in dg3} - {T_JR_15_DG3_SETTING})
    if other_dg3:
        problems.append(f"T-JR-15: Dg-3 lines of {other_dg3} (only {T_JR_15_DG3_SETTING})")
    problems += key_set_problems(f"T-JR-15 Dg-3 {T_JR_15_DG3_SETTING}",
                                 [row["key"] for row in dg3
                                  if row["setting"] == T_JR_15_DG3_SETTING], h6_keys)
    expected_case = case_e_identity()
    other_case = [row["key"] for row in case_rows if row["key"] != expected_case]
    if other_case:
        problems.append(f"T-JR-15: {len(other_case)} VBJ / LSJ run_v5 rows that are not the "
                        f"j9_cases case E job (first {other_case[0]})")
    settings = Counter(row["setting"] for row in case_rows if row["key"] == expected_case)
    if settings != Counter(T_JR_15_JUDGED_SETTINGS):
        problems.append(f"T-JR-15: case E rows by setting {dict(sorted(settings.items()))}, "
                        f"one each of {T_JR_15_JUDGED_SETTINGS} expected")
    return problems


def case_e_identity() -> str:
    """The job key (:func:`_job_identity`) of the j9_cases rows (case E = its VBJ / LSJ rows)."""
    import run_v5

    keys = {_job_identity(job) for job in run_v5.j9_case_jobs()}
    if len(keys) != 1:
        raise ValueError(f"run_v5.j9_case_jobs has {len(keys)} job keys, 1 expected")
    return keys.pop()


def _lock_record(row: dict) -> dict:
    """T-JR-15 per row (run_v5 row or Dg-3 line): relock count and the 3.4 seed check."""
    import h8_noise_judge_4368 as h8

    record = row.get("hydraulics_record") or {}
    job = row.get("job")
    is_run_v5 = isinstance(job, dict)
    return {"source": RUN_V5_SOURCE if is_run_v5 else DG3_SOURCE,
            "lock_window_mismatch": is_lock_window_mismatch(row),
            "setting": job.get("setting") if is_run_v5 else row.get("v5_setting"),
            "key": _job_identity(job) if is_run_v5 else h8.plain_key(str(row.get("key"))),
            compare.RELOCK_KEY: record.get(compare.RELOCK_KEY),
            "p1_retract_seed_count": record.get("p1_retract_seed_count"),
            "p1_retract_seed_step_max_bar": record.get("p1_retract_seed_step_max_bar"),
            "seed": compare.seed_force_check(record)}


def read_lock_rows(path: Path) -> list[dict]:
    """``--lock-rows``: a run_v5 jsonl, or a Dg-3 run json (its ``results`` lines)."""
    if path.suffix == ".json":
        return list(_read_json(path).get("results") or [])
    return _read_json_lines(path)


# --- command line ---------------------------------------------------------------------------

_RAW_HELP = argparse.RawDescriptionHelpFormatter
EXIT_TABLE = compare.EXIT_TABLE


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], epilog=EXIT_TABLE,
                                     formatter_class=_RAW_HELP)
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
                           help="VBH: P-1a h6_base_judge_L1_reference.json; VBJ / VBJ0: the "
                                "L1 run of the setting (addendum 4a-8 4.3)")
    dg3_judge.add_argument("--l1-reference-sha256", required=True,
                           help="VBH: l1_reference_sha256 of the P-1a base-judge report (= the "
                                "fixed extract); VBJ / VBJ0: the L1 run's recorded sha256")
    dg3_judge.add_argument("--l1-keys-file", type=Path, default=None,
                           help="VBJ / VBJ0: the 4a-8 4.2 key file of the L1 run (required)")
    dg3_judge.add_argument("--dg3-sha256", default=None,
                           help="the fixed sha256 of --dg3 (4a-8 6.2 3: stored Dg-3 files)")
    dg3_judge.add_argument("--judge-out", type=Path, required=True)
    l1_keys = commands.add_parser("l1-keys", help="4a-8 4.2: the VBJ / VBJ0 L1 key file")
    l1_keys.add_argument("--out", type=Path, required=True)
    l1_keys.add_argument("--h6", type=Path, required=True, help="the fixed stored H-6")
    l1_keys.add_argument("--keys-out", type=Path, required=True)
    l1_keys.add_argument("--l1-extract", type=Path, default=None,
                         help="the fixed L1 extract (a591c3a8...): every key must be in it")
    l1_hashes = commands.add_parser("l1-hash-record",
                                    help="4a-8 4.5: VBJ / VBJ0 L1 command hash counts (record)")
    l1_hashes.add_argument("--out", type=Path, required=True)
    l1_hashes.add_argument("--vbj-l1", type=Path, required=True)
    l1_hashes.add_argument("--vbj0-l1", type=Path, required=True)
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
    records = commands.add_parser("records", help="T-JR-13 .. 15 (addendum 4a-5 1, judged)",
                                  epilog=EXIT_TABLE, formatter_class=_RAW_HELP)
    records.add_argument("--out", type=Path, required=True)
    records.add_argument("--replay", type=Path, nargs="*", default=[],
                         help="the two t4h_replay --extend-start-revision 5 reports")
    records.add_argument("--t4h-sums", type=Path, nargs="*", default=[],
                         help="prelaunch_j9/h10_reuse_rerun_t4h.SHA256SUMS and "
                              "h6_dg3_v4on_t4h.SHA256SUMS (fixed; the reports' input folders)")
    records.add_argument("--dg3", type=Path, nargs="*", default=[],
                         help="Dg-3 run files of VBH and VBJ (T-JR-14)")
    records.add_argument("--h6", type=Path, default=None,
                         help="resume_k1/h6_dg3_v4on.json (fixed): the 135 keys of the T-JR-14 "
                              "bundles and the T-JR-15 Dg-3 VBJ lines (4a-5 erratum 1)")
    records.add_argument("--lock-rows", type=Path, nargs="*", default=[],
                         help="run_v5 jsonl (case E) and Dg-3 json (VBJ 135 lines) files")
    for sub in (t8, t12, dg3_judge, l1_keys, l1_hashes, base_judge, judges, selfcheck):
        sub.epilog, sub.formatter_class = EXIT_TABLE, _RAW_HELP
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
        documents = {name: _read_json(path) for name, path in (
            ("base", args.base), ("base_judge", args.base_judge), ("new", args.new),
            ("new_judge", args.new_judge))}
        report, problems = judge_t12(args.bundle, documents["base"], documents["base_judge"],
                                     documents["new"], documents["new_judge"])
        problems.not_judgeable[:0] = [*input_problems, *t12_judge_row_problems(documents)]
        problems.setting_defects[:0] = t12_file_defects(args.base, args.new)
        return report, problems, [args.base, args.base_judge, args.new, args.new_judge]
    if args.command == "dg3-judge":
        return make_dg3_judge(Dg3JudgeInputs(args.setting, args.dg3, args.l1_reference,
                                             args.l1_reference_sha256, args.judge_out,
                                             args.l1_keys_file, args.dg3_sha256))
    if args.command == "l1-keys":
        return make_l1_keys(args.h6, args.keys_out, args.l1_extract)
    if args.command == "l1-hash-record":
        return l1_hash_record(args.vbj_l1, args.vbj0_l1)
    if args.command == "base-judge":
        return make_base_judge(args.h6, args.noise, args.judge_out)
    if args.command == "t12-selfcheck":
        return t12_selfcheck(args.h6, args.judge, args.judge_sha256)
    if args.command == "base-judge-compare":
        return compare_base_judges(JudgeCompareInputs(
            args.h6, args.new_judge, args.new_judge_sha256, args.stored_judge,
            args.stored_h6_judge, args.new_l1_reference, args.stored_l1_reference))
    t4h_names, sums_problems = t4h_names_of(args.t4h_sums)
    h6_keys, h6_problems = h6_keys_of(args.h6)
    report, problems = judge_records(RecordsInputs(
        [_read_json(path) for path in args.replay], [_read_json(path) for path in args.dg3],
        [row for path in args.lock_rows for row in read_lock_rows(path)], t4h_names, h6_keys))
    problems.not_judgeable[:0] = [*sums_problems, *h6_problems]
    return report, problems, [*args.replay, *args.dg3, *args.lock_rows, *args.t4h_sums,
                              *([] if args.h6 is None else [args.h6])]


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
    except compare.TOOL_ERRORS as exc:
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
