"""436.9 edition 5 X-13 (``jp3_remedy_spec_v5.md`` 6.3, 6.6, 8 4.(6)): the T-JR-12b judge.

Sub-commands, run in the order of 8 4.(6) (VBK0 first):

``decide``  VBK0 outputs only (no VBK path argument; no VBK file is opened). On the blocks
            given (b1, b2, then b4 when a decision asked for it): the input fixing of erratum 8
            8-9 (d) (the expected run file sha256 and T4h digest of b1 and b2 are required
            arguments; a missing or differing one is not judgeable and the record then holds
            the status, the reason and the input sha256 only), the key presence gate (6.6, X-2),
            the plan and cell check against the X-11 ``selection.json``, the A/A floor (a record
            since erratum 8 8-1: b1 against b2, all 167 cases; one side without READY, or the
            first READY difference rounded to 1e-6 s above 30 s; written as ``aa_floor``, never a
            stop), the VBK0 classification (6.3.2 order: no trigger, pre-trigger fallback, not
            latched, VBK0 READY not reached, opportunity), the N top-up (6.3.5 with erratum 8
            8-8.1: ``N_opp < 0.9 N`` of b1 + b2 needs b3, and b3 has no allowance, so it is not
            judgeable, also when b3 is given) and the witness top-up (6.3.6: ``k`` = opportunity
            pairs whose VBK0 columns show a witnessed retract carry of the fault leg after the
            latch, ``rod_fault_plan.retract_witnesses`` with the TRw form; ``k < 45`` asks for
            b4, whose opportunity pairs all count; ``k < 45`` after it is not judgeable). A
            ``decided`` record names the blocks (``blocks``, the same set as ``blocks_used``)
            and the allowance ``allow_k`` of erratum 8 8-2 (b1 b2: 7, b1 b2 b4: 9). Writes the
            decision record (inputs with their sha256, counts, decisions, exit code).
``judge``   The decision record (its sha256 given; status ``decided`` with ``blocks_used`` and
            ``allow_k`` of erratum 8 8-2, else exit 2 before any VBK file is opened, also when
            its VBK0 inputs changed), the VBK0 and VBK outputs of the decided blocks. Per pair
            the identity (가) trigger read, (나) pre-trigger command sha256, (다) plan sha256 /
            fault id / leg / anchor / ``delay_reads`` 0 (6.3.4), the pair classification (both
            arms; a VBK-only pre-trigger fallback or missing latch is a setting defect, 6.3.5),
            the rev 6 identity of every VBK line (tag base ``final_C4G2_P3W``,
            ``hydraulics_record.extend_bound_check.rule_revision`` and
            ``run_extend_start_revision`` all 6, 4.6), then 6.3.7 with erratum 8 8-2: (1) a new
            (name, leg) FAULT pair of the T4h ``meta_json`` events on an opportunity or
            VBK0-READY-missing pair (0 count), (2)+(3) ``n23`` = the opportunity pairs whose
            READY was lost or came more than 30 s later (rounded to 1e-6 s) over every used
            block, failed when ``n23 > allow_k`` (the ``ready_rule`` block), (4) J-P3 of those
            VBK lines (``j_p3_judgement_rev5``; 0 judged rows is not judgeable). Records: the
            ``ready_rule`` record keys (``n_vbk0_worse*``, the LEVEL stall signature of erratum 8
            8-3, ``by_cell``, ``by_block``; an exception there leaves that item ``computed``
            False with its reason and never changes the status, erratum 8 8-8.2 W-4),
            ``n_fault_judged`` (the (1) denominator N_1),
            category counts per block and cell, tau_R pairs by the phase of the trigger update
            (LEVEL / PROBE), the coverage keys of 6.3.9 after the latch on the fault leg (sums of
            ``jp3_r58_witness`` / ``jp3_r59_substeps`` / ``jp3_r510_candidates`` of the VBK T4h),
            the new FAULT pairs of the no-trigger and pre-trigger-fallback pairs, the 95 % upper
            bounds of the pass sentence, and the sensor grade transitions (6.3.7, control
            review of 8a3c48c7 W-6): per pair the r79 path 1 grade of the VBK0 and the VBK line
            (``h8_noise_judge_4368.grade_lines`` on the ``grade-judge`` file of each arm, its
            sha256 given), the changed pairs and their keys (``grade_transitions``; a record,
            j9_main judges the grades, 6.5). A grade input defect (a grade-judge file not
            given, missing or of another sha256) is recorded as ``computed`` False with its
            reasons and never changes the status or exit code (erratum 2 audit F-1).
``grade-judge`` ``r79_sensor_judge.py judge --s4-late-loc`` of one arm's block run files and the
            arm's L1 reference run (erratum 2 2-1: VBK0 against the VBJ0 L1 run, VBK against
            the VBJ L1 run, both ``plant_truth``, from the fixed L1 key file; its sha256 and
            the key file's given), into ``--judge-out`` (never overwritten); the record
            (``--out``) names every input and the judge file with their sha256. The judge
            record also publishes ``ungraded_pairs`` and the causes of the ungraded
            opportunity pairs, and the cached ``u_hold`` of the witness count (2-5).
``l1-overlap`` (erratum 2 2-1, a record) the keys the 12b L1 reference and the T-JR-12a L1
            reference of one setting share, with the same / differing command hash counts.
``dry-c``   The c dry check (6.3.10): the VBK0 and VBK lines of the two dry plans (``c92=`` /
            ``c93=`` run files and T4h folders per arm; one plan per dry seed, ``selection.json``
            ``dry.runs``; a run's lines must carry its own plan's sha256 and a plan's keys must
            be its key file's, prelaunch audit B-1 (a)), the 6.3.2 categories and c = the share
            of opportunity pairs whose ``commands_sha256`` changed. ``written`` (exit 0) records
            c; c >= 0.5 stops at step (1) (prelaunch audit W-3, ``step1_p1.ps1``).

Edition 5 erratum 1 (``jp3_remedy_spec_v5_erratum1.md``): 6 a pair counts as "no trigger"
when no fault read was injected in the run, by the injection record itself (``is_armed``,
``applied_periods`` > 0 and ``first_applied_t_s``; the planned read number is not used), and
the (가) trigger read comparison holds for every pair; 7 a FAULT entry of the T4h ``phase``
(a ``fault`` / ``fault_reground`` row whose row before is neither, or the first row) is the
event pair (``PHASE_FAULT``, '–') of 6.3.7 (1).

Inputs: ``--selection`` and ``--selection-sha256`` (the X-11 record), ``--vbk0 b<j>=<run json>``
and ``--vbk0-t4h b<j>=<T4h folder>`` (the r79 runner output and its ``R79_T4H_DIR``; a line's
``t4h_file`` is a name in that folder, never a path of the working folder), for ``decide``
``--expect-vbk0-sha256 b<j>=<sha256>`` and ``--expect-vbk0-t4h-digest b<j>=<digest>`` of b1
and b2 (erratum 8 8-1.3 fixed values; required, 8-9 (d)), and for ``judge``
``--vbk`` / ``--vbk-t4h`` alike plus ``--decision`` / ``--decision-sha256`` and
``--vbk0-grade-judge`` / ``--vbk-grade-judge`` with their sha256 (optional: a missing one is a
grade record defect, F-1). ``--out`` must not exist. The
stdout's last line is JSON with ``status``, the problem counts and the output path.

======  ==================  ===================================================================
exit    status              meaning
======  ==================  ===================================================================
0       ``decided``         decide: the blocks are decided (``blocks``, ``blocks_used``,
                            ``allow_k``)
0       ``needs_b4``        decide: run the b4 VBK0 block, then decide again with it
0       ``pass``            judge: (1) and (4) count 0 and ``n23 <= allow_k``
0       ``written``         grade-judge / dry-c: the record written
1       ``failed``          judge: a 6.3.7 failure ((1) or (4) count 1 or more, or
                            ``n23 > allow_k``; stop, 8 5: re-design) - also with setting
                            defects / not-judgeable reasons found in the same run, which are
                            kept in ``problems`` (erratum 2 2-10)
2       ``setting_defect``  no failure; a not-latched pair, a pair identity / plan / revision
                            mismatch, a VBK-only pre-trigger fallback (outranks not_judgeable)
2       ``not_judgeable``   a missing line, key or array (X-2), another cell table, a decision
                            record of another sha, status, ``blocks_used`` or ``allow_k``
                            (erratum 8 8-8.2), a missing or differing expected VBK0 input
                            (8-9 (d)), b3 needed or given (8-8.1), ``N_opp < 301`` / ``k < 45``
                            after the top-up, 0 judged rows, an existing ``--out``
3       ``error``           a tool error (unreadable file, broken JSON, another shape)
======  ==================  ===================================================================

Erratum 8 (``jp3_remedy_spec_v5_erratum8.md``, sealed cd2de978): the A/A stop of 6.3.8 is
gone (the status ``aa_floor_stop`` is no longer written and a decision record that holds it is
refused by ``judge``); (2) and (3) are one allowance count ``n23`` (8-2); the record keys of
the ``ready_rule`` block are listed in 8-8.2.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import math
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src", ROOT / "04_scripts" / "03_control" / "s8"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

LEGS = ("FL", "FR", "RL", "RR")
NO_LEG = "–"
BLOCKS = ("b1", "b2", "b3", "b4")
CASES_PER_BLOCK = 167
NO_TRIGGER, PRE_FALLBACK, UNLATCHED = "no_trigger", "pre_trigger_fallback", "unlatched"
VBK0_NOT_READY, OPPORTUNITY = "vbk0_ready_unreached", "opportunity"
CATEGORIES = (NO_TRIGGER, PRE_FALLBACK, UNLATCHED, VBK0_NOT_READY, OPPORTUNITY)
"""6.3.2 order: the first that fits."""
JUDGED_CATEGORIES = (OPPORTUNITY, VBK0_NOT_READY)
"""6.3.7 (1) and (4): opportunity pairs and VBK0-READY-missing pairs."""
READY_LIMIT_S = 30.0
READY_ROUND_DIGITS = 6
READY_LOSS, READY_PLUS30, READY_OK = "loss", "plus30", "ok"
"""Erratum 8 8-8.2: the READY outcome of one opportunity pair."""
ALLOW_K_BY_BLOCKS = {("b1", "b2"): 7, ("b1", "b2", "b4"): 9}
"""Erratum 8 8-2: the allowance of ``n23`` by the used blocks (sorted); any other
combination (every one with b3) has no allowance and is not judgeable."""
B3_REASON = "b3 block combination has no allowance (erratum 8 8-2)"
AA_RULE = "erratum 8 8-1: record"
STALL_WINDOW_S = 20.0
STALL_WINDOW_TOLERANCE_S = 1e-6
STALL_SPAN_M = 1e-3
STALL_LAST_PHASES = ("level", "probe")
STALL_SIGNATURE_ARRAYS = ("t_s", "phase", "motor_stroke_m")
"""Erratum 8 8-3: the T4h arrays of the LEVEL stall signature (a record)."""
TRW_CELL = "TRw"
"""Erratum 8 8-6: the cell name of the b4 (TRw) layer in ``by_cell``."""
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_VBK0_BLOCKS = ("b1", "b2")
"""Erratum 8 8-1.3 / 8-9 (d): the VBK0 blocks with fixed values (b4 is recorded only)."""
N_TOPUP_RATIO = 0.9
N_OPP_MIN = 301
K_MIN = 45
UPPER_BOUND_ALPHA = 0.05
SETTING_OF_ARM = {"vbk0": "VBK0", "vbk": "VBK"}
REVISION = 6
REVISION_BASE_TAG = "final_C4G2_P3W"
FAULT_PREFIX = "FAULT"
FAULT_PHASES = ("fault", "fault_reground")
"""``C2Phase.FAULT`` and ``FAULT_REGROUND`` (erratum 1 7: an entry into either is a FAULT)."""
PHASE_FAULT_EVENT = "PHASE_FAULT"
PLAN_FIELDS = ("plan_sha256", "fault_id", "leg", "anchor", "delay_reads")
ROD_FAULT_FIELDS = (*PLAN_FIELDS, "is_armed", "trigger_read", "first_applied_read",
                    "first_applied_t_s", "applied_periods", "latched",
                    "pre_trigger_commands_sha256", "pre_trigger_fallback")
T4H_ARRAYS = ("motor_stroke_m", "command_m_s", "phase", "rod_fault_applied")
T4H_REV6_ARRAYS = ("jp3_t_s", "jp3_r58_witness", "jp3_r59_substeps", "jp3_r510_candidates",
                   "jp3_r59_end_guard_substeps")
"""The rev 6 arrays every VBK T4h must hold (6.6; the four of erratum 1 9.2 (다), audit
warning 4)."""
COVERAGE_KEYS = {"jp3_r58_witness_carries": "jp3_r58_witness",
                 "jp3_r59_substeps": "jp3_r59_substeps",
                 "jp3_r510_candidates": "jp3_r510_candidates"}
TAU_R_ANCHOR = "retract_start_after:LEVEL"
EXIT_OK, EXIT_FAILED, EXIT_NOT_JUDGEABLE, EXIT_ERROR = 0, 1, 2, 3
TIME_TOLERANCE_S = 1e-9


class Stop(Exception):
    """A condition that ends the sub-command with exit 2 (``status`` in :attr:`status`)."""

    def __init__(self, status: str, reason: str) -> None:
        super().__init__(reason)
        self.status = status


@dataclass
class Problems:
    setting_defects: list[str] = field(default_factory=list)
    not_judgeable: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def status(self) -> str:
        """Erratum 2 2-10: a counted failure wins (exit 1, the other reasons stay in the
        lists), then setting_defect, then not_judgeable (exit 2), else pass. A stop before
        any item is judged has no failure, so it keeps exit 2."""
        if self.failures:
            return "failed"
        if self.setting_defects:
            return "setting_defect"
        if self.not_judgeable:
            return "not_judgeable"
        return "pass"

    def counts(self) -> dict[str, int]:
        return {"setting_defects": len(self.setting_defects),
                "not_judgeable": len(self.not_judgeable), "failures": len(self.failures)}


@dataclass
class Line:
    """One result line of one arm with its T4h record (loaded on first use)."""

    key: str
    row: dict
    t4h_path: Path
    _arrays: dict | None = None
    _meta: dict | None = None

    def arrays(self) -> dict:
        if self._arrays is None:
            with np.load(self.t4h_path, allow_pickle=False) as data:
                self._arrays = {name: np.asarray(data[name]) for name in data.files
                                if name != "meta_json"}
                self._meta = json.loads(str(data["meta_json"]))
        return self._arrays

    def meta(self) -> dict:
        self.arrays()
        return self._meta

    @property
    def fault(self) -> dict:
        return self.row["rod_fault"]


# ------------------------------------------------------------------------------- inputs
def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plain_key(key: str) -> str:
    return key.split("#", 1)[1] if "#" in key else key


def case_of(key: str) -> str:
    tokens = plain_key(key).split("|")
    return "|".join([tokens[0], *tokens[2:]])


def ready_time(row: dict) -> float | None:
    """4a-3 4.1 (``r79_sensor_judge._ready_time``): ``base.t_ready_s`` when present, else
    ``base.t_ready``; None = no READY."""
    base = row["base"]
    return base.get("t_ready_s", base.get("t_ready"))


def parse_block_paths(values: list[str] | None, option: str) -> dict[str, Path]:
    """``b<j>=<path>`` arguments by block.

    Raises:
        Stop: A malformed or repeated block (not judgeable).
    """
    paths: dict[str, Path] = {}
    for value in values or []:
        block, separator, path = value.partition("=")
        if not separator or block not in BLOCKS or block in paths:
            raise Stop("not_judgeable", f"{option} {value!r}: one b1..b4=<path> per block")
        paths[block] = Path(path)
    return paths


def load_selection(path: Path, expected_sha256: str) -> dict:
    actual = file_sha256(path)
    if actual != expected_sha256:
        raise Stop("not_judgeable", f"--selection sha256 {actual[:12]} is not the given "
                                    f"{expected_sha256[:12]}")
    return json.loads(path.read_text(encoding="utf-8"))


def block_keys(selection: dict, block: str) -> list[str]:
    """The plain keys of a block (its seed and the 167 cases of the cell table)."""
    seed = selection["blocks"][block]["seed_index"]
    keys = []
    for row in selection["cell_table"]:
        level, rest = row["case"].split("|", 1)
        keys.append(f"{level}|s{seed}|{rest}")
    return keys


def load_lines(result_path: Path, t4h_dir: Path, expected: list[str], arm: str,
               problems: Problems) -> dict[str, Line]:
    """The lines of one block and arm by plain key; every expected key once, no error line,
    the arm's setting (missing / repeated / other lines are not judgeable)."""
    document = json.loads(result_path.read_text(encoding="utf-8"))
    rows = document["results"] if isinstance(document, dict) else document
    lines: dict[str, Line] = {}
    for row in rows:
        key = plain_key(row["key"])
        if key in lines:
            problems.not_judgeable.append(f"{arm} {key}: repeated line")
            continue
        if row.get("error"):
            problems.not_judgeable.append(f"{arm} {key}: error line")
        if row.get("v5_setting") != SETTING_OF_ARM[arm]:
            problems.setting_defects.append(f"{arm} {key}: v5_setting {row.get('v5_setting')!r}")
        t4h_file = row.get("t4h_file")
        lines[key] = Line(key, row, t4h_dir / t4h_file if t4h_file else t4h_dir / "<none>")
    missing = sorted(set(expected) - set(lines))
    other = sorted(set(lines) - set(expected))
    if missing or other:
        problems.not_judgeable.append(f"{arm} {result_path.name}: {len(missing)} keys missing, "
                                      f"{len(other)} other (first {(missing + other)[:2]})")
    return lines


def presence_problems(line: Line, arm: str) -> list[str]:
    """X-2 / 6.6 key presence of one line (empty = every judged input is there)."""
    row = line.row
    problems = []
    record = row.get("rod_fault")
    if not isinstance(record, dict):
        return ["rod_fault missing"]
    problems += [f"rod_fault.{name} missing" for name in ROD_FAULT_FIELDS if name not in record]
    if not isinstance(record.get("latched"), dict) or "is_same_read_d1" not in record["latched"]:
        problems.append("rod_fault.latched.is_same_read_d1 missing")
    base = row.get("base")
    if not isinstance(base, dict) or not ("t_ready_s" in base or "t_ready" in base):
        problems.append("base.t_ready_s / base.t_ready missing")
    if arm == "vbk":
        check = (row.get("hydraulics_record") or {}).get("extend_bound_check")
        if not isinstance(check, dict):
            problems.append("hydraulics_record.extend_bound_check missing")
        elif "rule_revision" not in check:
            problems.append("hydraulics_record.extend_bound_check.rule_revision missing")
        if "run_extend_start_revision" not in row:
            problems.append("run_extend_start_revision missing")
    if not line.t4h_path.is_file():
        return [*problems, f"T4h {line.t4h_path.name} missing"]
    arrays = line.arrays()
    names = T4H_ARRAYS + (T4H_REV6_ARRAYS if arm == "vbk" else ())
    problems += [f"T4h array {name} missing" for name in names if name not in arrays]
    if not isinstance(line.meta().get("events"), list):
        problems.append("T4h meta_json events missing")
    return problems


def check_presence(lines: dict[str, Line], arm: str, problems: Problems) -> None:
    for key, line in lines.items():
        problems.not_judgeable += [f"{arm} {key}: {text}" for text in presence_problems(line, arm)]


def check_plan(lines: dict[str, Line], selection: dict, block: str, arm: str,
               problems: Problems) -> None:
    """The lines' faults are the block's plan and the fixed cell table (6.3.1, 6.3.4 (다))."""
    plan_name = selection["blocks"][block]["plan"]
    plan_sha = selection["outputs"][plan_name]
    phase_rule = selection["blocks"][block]["phase"]
    anchors = {"tau_C": "phase_exit:CHECK", "tau_R": TAU_R_ANCHOR,
               "TRw": "retract_witness_after:LEVEL"}
    by_case = {row["case"]: row for row in selection["cell_table"]}
    for key, line in lines.items():
        record = line.row.get("rod_fault") or {}
        if record.get("plan_sha256") != plan_sha:
            problems.setting_defects.append(f"{arm} {key}: plan sha256 is not {plan_name}")
        if record.get("delay_reads") != 0:
            problems.setting_defects.append(f"{arm} {key}: delay_reads "
                                            f"{record.get('delay_reads')!r}, 0 needed")
        cell = by_case.get(case_of(key))
        if cell is None:
            continue
        phase = cell["phase"] if phase_rule == "cell" else phase_rule
        if record.get("leg") != cell["leg"] or record.get("anchor") != anchors[phase]:
            problems.not_judgeable.append(f"{arm} {key}: fault {record.get('leg')} "
                                          f"{record.get('anchor')} is not the cell table's")


def load_arm(selection: dict, results: dict[str, Path], t4h_dirs: dict[str, Path], arm: str,
             problems: Problems) -> dict[str, dict[str, Line]]:
    """Every given block of one arm, checked (presence, plan, cells)."""
    if set(results) != set(t4h_dirs):
        raise Stop("not_judgeable", f"--{arm} and --{arm}-t4h name other blocks")
    blocks = {}
    for block in BLOCKS:
        if block not in results:
            continue
        lines = load_lines(results[block], t4h_dirs[block], block_keys(selection, block), arm,
                           problems)
        check_presence(lines, arm, problems)
        check_plan(lines, selection, block, arm, problems)
        blocks[block] = lines
    return blocks


def input_record(results: dict[str, Path], t4h_dirs: dict[str, Path],
                 blocks: dict[str, dict[str, Line]]) -> dict:
    """sha256 of each run file and a digest of the T4h files its lines name."""
    record = {}
    for block, lines in blocks.items():
        names = sorted(line.t4h_path.name for line in lines.values() if line.t4h_path.is_file())
        digest = hashlib.sha256("".join(
            f"{file_sha256(t4h_dirs[block] / name)}  {name}\n" for name in names).encode())
        record[block] = {"run": str(results[block]), "run_sha256": file_sha256(results[block]),
                         "t4h_dir": str(t4h_dirs[block]), "t4h_files": len(names),
                         "t4h_sha256_digest": digest.hexdigest()}
    return record


# ------------------------------------------------------------------------------- classification
def is_latched(record: dict) -> bool:
    return bool((record.get("latched") or {}).get("is_same_read_d1"))


def is_injected(record: dict) -> bool:
    """The fault reached a read of the run, by the injection record itself (erratum 1 6,
    control review of 8a3c48c7 W-4): armed, ``applied_periods`` > 0 and a first faulty read
    time. A trigger on the run's last update arms with no faulty read after it; such a pair is
    "no trigger", never "not latched" (the planned first read number is not used)."""
    applied = record.get("applied_periods")
    return (bool(record.get("is_armed")) and isinstance(applied, int) and applied > 0
            and record.get("first_applied_t_s") is not None)


def classify_line(line: Line) -> str:
    """6.3.2 order on one arm (the VBK0 count of the decisions, 6.3.5)."""
    record = line.fault
    if not is_injected(record):
        return NO_TRIGGER
    if record.get("pre_trigger_fallback"):
        return PRE_FALLBACK
    if not is_latched(record):
        return UNLATCHED
    if ready_time(line.row) is None:
        return VBK0_NOT_READY
    return OPPORTUNITY


def classify_pair(vbk: Line, vbk0: Line, problems: Problems) -> str:
    """6.3.2 / 6.3.4 on both arms; identity breaks and one-sided outcomes are setting defects."""
    key = vbk0.key
    fault, fault0 = vbk.fault, vbk0.fault
    differing = [name for name in PLAN_FIELDS if fault.get(name) != fault0.get(name)]
    if differing:
        problems.setting_defects.append(f"{key}: plans differ in {differing} (다)")
    if fault.get("trigger_read") != fault0.get("trigger_read"):  # (가), every pair (erratum 1 6)
        problems.setting_defects.append(f"{key}: trigger reads differ (가)")
    injected, injected0 = is_injected(fault), is_injected(fault0)
    if not injected and not injected0:
        return NO_TRIGGER
    if injected != injected0:
        problems.setting_defects.append(f"{key}: injected on one arm only (가)")
        return NO_TRIGGER
    fallback, fallback0 = bool(fault.get("pre_trigger_fallback")), bool(
        fault0.get("pre_trigger_fallback"))
    if fallback or fallback0:
        if fallback and not fallback0:
            problems.setting_defects.append(f"{key}: pre-trigger fallback on VBK only (6.3.5)")
        return PRE_FALLBACK
    if fault.get("pre_trigger_commands_sha256") != fault0.get("pre_trigger_commands_sha256"):
        problems.setting_defects.append(f"{key}: pre-trigger commands differ (나)")
    if not (is_latched(fault) and is_latched(fault0)):
        problems.setting_defects.append(f"{key}: not latched on the first faulty read (6.3.2)")
        return UNLATCHED
    if ready_time(vbk0.row) is None:
        return VBK0_NOT_READY
    return OPPORTUNITY


# ------------------------------------------------------------------------------- decide
def aa_floor(blocks: dict[str, dict[str, Line]], selection: dict) -> dict:
    """6.3.8 count, a record since erratum 8 8-1: b1 against b2 over all 167 cases (missing
    lines are not judgeable); it never stops the decision (``is_stop`` False, no ``stop_at``)."""
    first = {case_of(key): line for key, line in blocks["b1"].items()}
    second = {case_of(key): line for key, line in blocks["b2"].items()}
    cases = [row["case"] for row in selection["cell_table"]]
    missing = [case for case in cases if case not in first or case not in second]
    if missing:
        raise Stop("not_judgeable", f"A/A: {len(missing)} of {len(cases)} pairs incomplete")
    counted = []
    for case in cases:
        ready, ready_other = ready_time(first[case].row), ready_time(second[case].row)
        if (ready is None) != (ready_other is None):
            counted.append(case)
        elif ready is not None and round(abs(ready - ready_other), READY_ROUND_DIGITS) > \
                READY_LIMIT_S:
            counted.append(case)
    return {"pairs": len(cases), "counted_pairs": len(counted), "counted": counted,
            "rule": AA_RULE, "is_stop": False}


def witness_after_latch(line: Line) -> bool:
    """6.3.6 record function on one VBK0 line: a witnessed retract carry of the fault leg with
    its witness read at or after the latch read (TRw form, ``retract_witnesses``)."""
    import rod_fault_plan

    arrays = line.arrays()
    leg = LEGS.index(line.fault["leg"])
    found = rod_fault_plan.retract_witnesses(
        arrays["phase"], arrays["command_m_s"], arrays["motor_stroke_m"], leg,
        _hold_speed_m_s(), from_read=int(line.fault["first_applied_read"]))
    return bool(found)


@functools.cache
def _hold_speed_m_s() -> float:
    """``rod_fault_plan.hold_speed_m_s`` once per process (it reads the parameter YAML)."""
    import rod_fault_plan

    return rod_fault_plan.hold_speed_m_s()


def _hold_speed_record() -> dict:
    """The cached ``u_hold`` of the witness count (erratum 2 2-5: recorded with the judgement;
    the simulation path reads its own)."""
    import rod_fault_plan

    return {"value": _hold_speed_m_s(), "source": rod_fault_plan.HOLD_SPEED_SOURCE,
            "cached_in": "jp3_12b_judge._hold_speed_m_s (once per process)"}


def count_categories(lines: dict[str, Line]) -> dict[str, list[str]]:
    by_category = {category: [] for category in CATEGORIES}
    for key, line in lines.items():
        by_category[classify_line(line)].append(key)
    return by_category


def allowance_of(blocks_used: list[str]) -> int | None:
    """Erratum 8 8-2: ``k_allow`` of the used blocks (None: no allowance, not judgeable)."""
    return ALLOW_K_BY_BLOCKS.get(tuple(sorted(blocks_used)))


def decide(selection: dict, blocks: dict[str, dict[str, Line]]) -> dict:
    """The decisions of 6.3.5, 6.3.6 and the A/A record (erratum 8 8-8.1, module docstring)."""
    if not {"b1", "b2"} <= set(blocks):
        raise Stop("not_judgeable", "decide needs the VBK0 blocks b1 and b2")
    out: dict = {"aa_floor": aa_floor(blocks, selection)}
    categories = {block: count_categories(lines) for block, lines in blocks.items()}
    out["categories"] = {block: {name: len(keys) for name, keys in found.items()}
                         for block, found in categories.items()}
    unlatched = sum(len(found[UNLATCHED]) for found in categories.values())
    if unlatched:
        raise _with_record(Stop("setting_defect", f"{unlatched} VBK0 pairs not latched"), out)
    opportunity_12 = sum(len(categories[block][OPPORTUNITY]) for block in ("b1", "b2"))
    n_12 = CASES_PER_BLOCK * 2
    needs_b3 = opportunity_12 < N_TOPUP_RATIO * n_12
    out["n_topup"] = {"n_opp_b1_b2": opportunity_12, "n_b1_b2": n_12,
                      "threshold": N_TOPUP_RATIO * n_12, "needs_b3": needs_b3}
    if needs_b3 or "b3" in blocks:  # erratum 8 8-8.1: b3 is never run (no allowance)
        raise _with_record(Stop("not_judgeable", B3_REASON), out)
    used = ["b1", "b2"]
    n_opp = sum(len(categories[block][OPPORTUNITY]) for block in used)
    if n_opp < N_OPP_MIN:
        raise _with_record(Stop("not_judgeable", f"N_opp {n_opp} < {N_OPP_MIN}"), out)
    witness_pairs = [key for block in used for key in categories[block][OPPORTUNITY]
                     if witness_after_latch(blocks[block][key])]
    k = len(witness_pairs)
    needs_b4 = k < K_MIN
    out["witness_topup"] = {"k_without_b4": k, "k_min": K_MIN, "needs_b4": needs_b4,
                            "witness_pairs": witness_pairs,
                            "hold_speed_m_s": _hold_speed_record()}  # erratum 2 2-5
    if needs_b4 and "b4" not in blocks:
        out["status"], out["blocks"] = "needs_b4", used
        return out
    if not needs_b4 and "b4" in blocks:
        raise _with_record(Stop("not_judgeable", "b4 given but not asked for (6.3.6)"), out)
    if needs_b4:
        used.append("b4")
        b4_pairs = categories["b4"][OPPORTUNITY]
        k += len(b4_pairs)
        n_opp += len(b4_pairs)
        out["witness_topup"]["b4_opportunity_pairs"] = len(b4_pairs)
        if k < K_MIN:
            raise _with_record(Stop("not_judgeable", f"k {k} < {K_MIN} after b4"), out)
    # erratum 8 8-8.1: blocks (VBK runs, pair loop) and blocks_used (the allowance) agree
    out.update(status="decided", blocks=used, blocks_used=list(used),
               allow_k=allowance_of(used), n=CASES_PER_BLOCK * len(used), n_opp=n_opp, k=k)
    return out


def _with_record(stop: Stop, record: dict) -> Stop:
    stop.record = record
    return stop


# ------------------------------------------------------------------------------- judge
def fault_pairs(events: list) -> set[tuple[str, str]]:
    """6.3.7 (1): (name, leg) of every event whose first ':' token starts with ``FAULT``; the
    legs are the FL / FR / RL / RR elements of the other tokens split at ',' ({'–'} if none)."""
    pairs = set()
    for event in events:
        name = event[1] if isinstance(event, (list, tuple)) else event
        tokens = str(name).split(":")
        if not tokens[0].startswith(FAULT_PREFIX):
            continue
        legs = {part for token in tokens[1:] for part in token.split(",") if part in LEGS}
        for leg in legs or {NO_LEG}:
            pairs.add((tokens[0], leg))
    return pairs


def phase_fault_pairs(phase) -> set[tuple[str, str]]:
    """Erratum 1 7 (control review of 8a3c48c7 W-5): a T4h ``phase`` row (row k = after update
    k) in :data:`FAULT_PHASES` whose row before is not (or the first row) is an entry; any entry
    gives the event (:data:`PHASE_FAULT_EVENT`, '–'), also when no FAULT-named event came with
    it (the S-4 150 mm stop, the reground limit / abort)."""
    phases = [str(value).lower() for value in phase]
    entered = any(value in FAULT_PHASES and (row == 0 or phases[row - 1] not in FAULT_PHASES)
                  for row, value in enumerate(phases))
    return {(PHASE_FAULT_EVENT, NO_LEG)} if entered else set()


def line_fault_pairs(line: Line) -> set[tuple[str, str]]:
    return fault_pairs(line.meta()["events"]) | phase_fault_pairs(line.arrays()["phase"])


def new_fault_pairs(vbk: Line, vbk0: Line) -> list[tuple[str, str]]:
    return sorted(line_fault_pairs(vbk) - line_fault_pairs(vbk0))


def revision_problems(line: Line) -> list[str]:
    """4.6: the VBK line's tag and both revision keys name revision 6."""
    from outrigger_sim.hydraulics.v5_options import extend_start_revision_of_tag

    row = line.row
    problems = []
    tag = row.get("controller_tag")
    if extend_start_revision_of_tag(tag) != REVISION:
        problems.append(f"controller_tag {tag!r} is not revision {REVISION}")
    check = (row.get("hydraulics_record") or {}).get("extend_bound_check") or {}
    if check.get("rule_revision") != REVISION:
        problems.append(f"extend_bound_check.rule_revision {check.get('rule_revision')!r}")
    if row.get("run_extend_start_revision") != REVISION:
        problems.append(f"run_extend_start_revision {row.get('run_extend_start_revision')!r}")
    return problems


def coverage(line: Line) -> dict[str, int]:
    """6.3.9: the fault leg's per-read rev 6 counts from the latch read on (VBK T4h)."""
    arrays = line.arrays()
    leg = LEGS.index(line.fault["leg"])
    after = np.asarray(arrays["jp3_t_s"], float) >= float(line.fault["first_applied_t_s"]) - \
        TIME_TOLERANCE_S
    return {key: int(np.asarray(arrays[name])[after, leg].astype(np.int64).sum())
            for key, name in COVERAGE_KEYS.items()}


def trigger_phase(line: Line) -> str:
    """The phase after the trigger update (tau_R LEVEL / PROBE record, 6.3.3)."""
    return str(line.arrays()["phase"][int(line.fault["trigger_read"])]).upper()


def upper_bound(count: int) -> float | None:
    return None if count <= 0 else 1.0 - UPPER_BOUND_ALPHA ** (1.0 / count)


def judge_pairs(blocks0: dict, blocks1: dict, decision: dict, problems: Problems) -> dict:
    """Classification, identity, revision and 6.3.7 (1) .. (3) over the decided blocks."""
    from outrigger_sim.control.extend_start_bound import j_p3_judgement_rev5

    pairs, judged_lines, records = [], [], {"new_faults_recorded": []}
    by_block: dict[str, dict[str, int]] = {}
    tau_r_phases: dict[str, int] = {}
    totals = dict.fromkeys(COVERAGE_KEYS, 0)
    for block in decision["blocks"]:
        lines0, lines1 = blocks0[block], blocks1[block]
        by_block[block] = dict.fromkeys(CATEGORIES, 0)
        for key, vbk0 in lines0.items():
            vbk = lines1.get(key)
            if vbk is None:
                continue  # load_lines reported it
            problems.setting_defects += [f"VBK {key}: {text}" for text in revision_problems(vbk)]
            category = classify_pair(vbk, vbk0, problems)
            if category != classify_line(vbk0):
                problems.setting_defects.append(f"{key}: pair category {category} is not the "
                                                f"VBK0 one {classify_line(vbk0)} (6.3.5)")
            by_block[block][category] += 1
            new_faults = new_fault_pairs(vbk, vbk0) if category != UNLATCHED else []
            pair = {"block": block, "key": key, "category": category,
                    "new_faults": [list(item) for item in new_faults]}
            if category in JUDGED_CATEGORIES:
                judged_lines.append(vbk)
                if new_faults:
                    problems.failures.append(f"{key}: new FAULT {new_faults} (1)")
            elif new_faults:
                records["new_faults_recorded"].append(pair)
            if category == VBK0_NOT_READY:  # erratum 8 8-2: the READY of this pair is a record
                pair["ready_s"], pair["ready0_s"] = ready_time(vbk.row), None
            if category == OPPORTUNITY:
                _judge_ready(vbk, vbk0, pair)
                pair["coverage"] = coverage(vbk)
                for name, value in pair["coverage"].items():
                    totals[name] += value
                if vbk0.fault["anchor"] == TAU_R_ANCHOR:
                    phase = trigger_phase(vbk0)
                    tau_r_phases[phase] = tau_r_phases.get(phase, 0) + 1
            pairs.append(pair)
    jp3 = j_p3_judgement_rev5(
        [line.row["hydraulics_record"]["extend_bound_check"] for line in judged_lines],
        [bool(line.row.get("has_rod_reading", True)) for line in judged_lines],
        [bool(line.row.get("head_only_declared", False)) for line in judged_lines],
        expected_judged_runs=len(judged_lines))
    _judge_jp3(jp3, len(judged_lines), problems)
    opportunity = sum(counts[OPPORTUNITY] for counts in by_block.values())
    return {"pairs": pairs, "categories_by_block": by_block, "jp3": jp3,
            "tau_r_trigger_phase": tau_r_phases, "coverage_totals": totals,
            "n_opp": opportunity, "n_fault_judged": len(judged_lines), **records}


def ready_outcome(ready: float | None, ready0: float) -> str:
    """Erratum 8 8-2 on a pair whose VBK0 reached READY: ``loss`` (VBK without READY),
    ``plus30`` (VBK - VBK0 rounded to 1e-6 s with ``round`` above 30 s) or ``ok``."""
    if ready is None:
        return READY_LOSS
    if round(ready - ready0, READY_ROUND_DIGITS) > READY_LIMIT_S:
        return READY_PLUS30
    return READY_OK


def _judge_ready(vbk: Line, vbk0: Line, pair: dict) -> None:
    """Erratum 8 8-8.2: the READY outcome of an opportunity pair (no failure per pair; the
    allowance counts them in :func:`judge_ready_rule`)."""
    ready, ready0 = ready_time(vbk.row), ready_time(vbk0.row)
    pair["ready_s"], pair["ready0_s"] = ready, ready0
    pair["ready_outcome"] = ready_outcome(ready, ready0)


def judge_ready_rule(pairs: list[dict], decision: dict, n_fault_judged: int,
                     problems: Problems) -> dict:
    """Erratum 8 8-2 / 8-8.2: ``n23`` over the opportunity pairs of every used block against
    ``allow_k`` of the (checked) decision record; ``n23 > allow_k`` is one failure. No
    opportunity pair gives the verdict ``not_judgeable`` (never a pass on an empty set; the
    status is not judgeable through :func:`cmd_judge`)."""
    outcomes = [pair["ready_outcome"] for pair in pairs if pair["category"] == OPPORTUNITY]
    n_loss = outcomes.count(READY_LOSS)
    n_plus30 = outcomes.count(READY_PLUS30)
    n_vbk_worse = n_loss + n_plus30
    allow_k = decision["allow_k"]
    if not outcomes:
        verdict = "not_judgeable"
    elif n_vbk_worse > allow_k:
        verdict = "failed"
        problems.failures.append(f"(2)+(3) n23 {n_vbk_worse} > allow {allow_k} (erratum 8 8-2)")
    else:
        verdict = "pass"
    return {"rule": "erratum 8 8-2: n23 = READY lost + READY more than 30 s later over the "
                    "opportunity pairs of every used block; pass if n23 <= allow_k",
            "n_opp": len(outcomes), "n_ready_loss": n_loss, "n_ready_plus30": n_plus30,
            "n_vbk_worse": n_vbk_worse, "allow_k": allow_k,
            "blocks_used": list(decision["blocks_used"]), "verdict": verdict,
            "n_fault_judged": n_fault_judged, "aa_floor": decision.get("aa_floor")}


# ------------------------------------------------------------------- ready_rule records (W-4)
def _cell_names(selection: dict) -> dict[str, str]:
    """Plain case -> cell name ("0" .. "7") of the X-11 cell table."""
    return {row["case"]: str(row["cell"]) for row in selection["cell_table"]}


def _cell_of(pair: dict, cells: dict[str, str]) -> str:
    """Erratum 8 8-6: the cell of a pair; every b4 pair is the TRw layer."""
    if pair["block"] == "b4":
        return TRW_CELL
    return cells[case_of(pair["key"])]


def _ready_counts(pairs: list[dict]) -> dict[str, int]:
    """``n_opp`` / ``n_vbk_worse`` / ``n_ready_loss`` / ``n_ready_plus30`` of some pairs."""
    outcomes = [pair["ready_outcome"] for pair in pairs if pair["category"] == OPPORTUNITY]
    loss, plus30 = outcomes.count(READY_LOSS), outcomes.count(READY_PLUS30)
    return {"n_opp": len(outcomes), "n_vbk_worse": loss + plus30, "n_ready_loss": loss,
            "n_ready_plus30": plus30}


def by_cell_record(pairs: list[dict], selection: dict, blocks_used: list[str]) -> dict:
    cells = _cell_names(selection)
    names = sorted(set(cells.values()), key=int) + ([TRW_CELL] if "b4" in blocks_used else [])
    grouped: dict[str, list[dict]] = {name: [] for name in names}
    for pair in pairs:
        grouped[_cell_of(pair, cells)].append(pair)
    return {"by_cell": {name: _ready_counts(found) for name, found in grouped.items()}}


def by_block_record(pairs: list[dict], blocks_used: list[str]) -> dict:
    grouped: dict[str, list[dict]] = {block: [] for block in blocks_used}
    for pair in pairs:
        grouped[pair["block"]].append(pair)
    return {"by_block": {block: _ready_counts(found) for block, found in grouped.items()}}


def vbk0_worse_record(pairs: list[dict]) -> dict:
    """Erratum 8 8-6 (W-4): VBK0 without READY and VBK with it (the "VBK0 READY not reached"
    pairs), and VBK0 READY more than 30 s after VBK's on the opportunity pairs where both
    reached READY (rounded to 1e-6 s)."""
    loss = sum(1 for pair in pairs
               if pair["category"] == VBK0_NOT_READY and pair["ready_s"] is not None)
    plus30 = sum(1 for pair in pairs
                 if pair["category"] == OPPORTUNITY and pair["ready_s"] is not None
                 and round(pair["ready0_s"] - pair["ready_s"], READY_ROUND_DIGITS)
                 > READY_LIMIT_S)
    return {"n_vbk0_worse": loss + plus30, "n_vbk0_worse_loss": loss,
            "n_vbk0_worse_plus30": plus30}


def is_stall_signature(line: Line) -> bool:
    """Erratum 8 8-3 (a record): no READY, no fault phase entry (``PHASE_FAULT``), the last T4h
    ``phase`` row ``level`` or ``probe`` (compared in lower case), and every leg's
    ``motor_stroke_m`` span below 1 mm over the reads with ``t_s`` >= last ``t_s`` - 20 s
    - 1e-6 s.

    Raises:
        ValueError: The three arrays do not have one row per read and four legs.
    """
    if ready_time(line.row) is not None:
        return False
    arrays = line.arrays()
    times = np.asarray(arrays["t_s"], float)
    phases = [str(value).lower() for value in arrays["phase"]]
    strokes = np.asarray(arrays["motor_stroke_m"], float)
    if (times.ndim != 1 or len(times) == 0 or len(phases) != len(times)
            or strokes.shape != (len(times), len(LEGS))):
        raise ValueError(f"{line.key}: t_s {times.shape}, phase {len(phases)}, motor_stroke_m "
                         f"{strokes.shape} are not one row per read")
    if phase_fault_pairs(phases) or phases[-1] not in STALL_LAST_PHASES:
        return False
    window = times >= times[-1] - STALL_WINDOW_S - STALL_WINDOW_TOLERANCE_S
    spans = strokes[window].max(axis=0) - strokes[window].min(axis=0)
    return bool((spans < STALL_SPAN_M).all())


def _signature_entry(block: str, line: Line) -> dict:
    return {"block": block, "key": line.key,
            "last_t_s": float(np.asarray(line.arrays()["t_s"], float)[-1])}


def stall_signature_record(pairs: list[dict], blocks0: dict, blocks1: dict,
                           blocks_used: list[str]) -> tuple[dict, list[str]]:
    """Erratum 8 8-3 / 8-6: the READY-lost pairs whose VBK line is a stall signature and the
    VBK0 lines of the used blocks that are; a missing signature array leaves the item not
    computed (its reasons returned, the status unchanged)."""
    lost = [(pair["block"], blocks1[pair["block"]][pair["key"]]) for pair in pairs
            if pair.get("ready_outcome") == READY_LOSS]
    unready0 = [(block, line) for block in blocks_used for line in blocks0[block].values()
                if ready_time(line.row) is None]
    missing = sorted({f"{name} of {line.key}" for _, line in lost + unready0
                      for name in STALL_SIGNATURE_ARRAYS if name not in line.arrays()})
    if missing:
        return {}, [f"T4h array {text} missing" for text in missing[:5]] + (
            [f"(+{len(missing) - 5})"] if len(missing) > 5 else [])
    return {"stall_signature_pairs": [_signature_entry(block, line) for block, line in lost
                                      if is_stall_signature(line)],
            "stall_signature_vbk0_lines": [_signature_entry(block, line)
                                           for block, line in unready0
                                           if is_stall_signature(line)]}, []


RECORD_ITEM_KEYS = {
    "stall_signature": ("stall_signature_pairs", "stall_signature_vbk0_lines"),
    "n_vbk0_worse": ("n_vbk0_worse", "n_vbk0_worse_loss", "n_vbk0_worse_plus30"),
    "by_cell": ("by_cell",),
    "by_block": ("by_block",),
}
"""Erratum 8 8-8.2 (W-4): the ``ready_rule`` record items and their value keys."""


def computed_record(item: str, compute: Callable[[], tuple[dict, list[str]]]) -> dict:
    """One ``ready_rule`` record item with ``<item>_computed`` and ``<item>_reasons``: an
    exception or a returned reason leaves its values None and ``computed`` False. A record
    item never touches ``problems`` (erratum 8 8-8.2 W-4, like the grade transitions)."""
    try:
        values, reasons = compute()
    except Exception as exc:  # noqa: BLE001 (W-4: a record item never ends the judgement)
        values, reasons = {}, [f"exception {type(exc).__name__}: {exc}"]
    if reasons:
        values = dict.fromkeys(RECORD_ITEM_KEYS[item])
    return {**values, f"{item}_computed": not reasons, f"{item}_reasons": reasons}


def ready_rule_records(pairs: list[dict], blocks0: dict, blocks1: dict, selection: dict,
                       blocks_used: list[str]) -> dict:
    """The record keys of the ``ready_rule`` block (erratum 8 8-6, 8-8.2)."""
    return {**computed_record("n_vbk0_worse", lambda: (vbk0_worse_record(pairs), [])),
            **computed_record("stall_signature", lambda: stall_signature_record(
                pairs, blocks0, blocks1, blocks_used)),
            **computed_record("by_cell", lambda: (by_cell_record(pairs, selection,
                                                                 blocks_used), [])),
            **computed_record("by_block", lambda: (by_block_record(pairs, blocks_used), []))}


def _judge_jp3(jp3: dict, judged_rows: int, problems: Problems) -> None:
    """6.3.7 (4): H-7 fails, a defect is a setting defect, 0 rows or missing keys are not
    judgeable (13.2, 4a-5 3.3). Erratum 2 2-10.1 5: the H-7 is read from the rev 6 judged
    rows directly (``j_p3_inputs.has_judged_breach``), never hidden by the combined status;
    a setting defect or a not-judgeable status of the same judgement is kept as a reason."""
    from j_p3_inputs import has_judged_breach

    status = jp3["status"]
    # re-audit warning 2: the judge file says whether the H-7 came from the judged rows
    jp3["h7_from_judged_rows"] = judged_rows > 0 and (status == "H-7" or has_judged_breach(jp3))
    if judged_rows == 0:
        problems.not_judgeable.append("J-P3: 0 judged VBK lines (6.3.7 (4))")
        return
    if jp3["h7_from_judged_rows"]:
        problems.failures.append("J-P3 H-7 on the VBK lines (4)")
    if status == "setting_defect":
        problems.setting_defects.append("J-P3 setting defect on the VBK lines")
    elif status not in ("pass", "H-7"):
        problems.not_judgeable.append(f"J-P3 {status} on the VBK lines")


def decision_block_problems(decision: dict) -> list[str]:
    """Erratum 8 8-8.2 (W-5): why a ``decided`` record cannot give the allowance - ``allow_k``
    or ``blocks_used`` missing, ``blocks_used`` not the set of ``blocks``, ``blocks_used``
    neither {b1, b2} nor {b1, b2, b4}, or ``allow_k`` not the 8-2 value of ``blocks_used``."""
    missing = [name for name in ("allow_k", "blocks_used") if name not in decision]
    if missing:
        return [f"decision record without {name} (erratum 8 8-8.2)" for name in missing]
    blocks_used, blocks, allow_k = decision["blocks_used"], decision.get("blocks"), \
        decision["allow_k"]
    if not isinstance(blocks_used, list) or not isinstance(blocks, list):
        return ["decision record blocks / blocks_used are not lists"]
    problems = []
    if set(blocks_used) != set(blocks):
        problems.append(f"blocks_used {blocks_used} is not the set of blocks {blocks}")
    expected = allowance_of(blocks_used) if len(set(blocks_used)) == len(blocks_used) else None
    if expected is None:
        problems.append(f"blocks_used {blocks_used} is neither [b1, b2] nor [b1, b2, b4] "
                        "(erratum 8 8-2: no allowance)")
    elif type(allow_k) is not int or allow_k != expected:
        problems.append(f"allow_k {allow_k!r} is not {expected} of blocks_used {blocks_used}")
    return problems


def load_decision(path: Path, expected_sha256: str, vbk0_inputs: dict) -> dict:
    """The decision record (its sha256, status ``decided``, the same VBK0 inputs, the blocks
    and allowance of erratum 8 8-8.2).

    Raises:
        Stop: Another sha, another status, changed VBK0 inputs or a block / allowance problem
            (not judgeable).
    """
    if not path.is_file():
        raise Stop("not_judgeable", f"--decision {path} missing")
    actual = file_sha256(path)
    if actual != expected_sha256:
        raise Stop("not_judgeable", f"--decision sha256 {actual[:12]} is not the given "
                                    f"{expected_sha256[:12]}")
    decision = json.loads(path.read_text(encoding="utf-8"))
    if decision.get("status") != "decided":
        raise Stop("not_judgeable", f"decision status {decision.get('status')!r}, not decided")
    if decision.get("inputs", {}).get("vbk0") != vbk0_inputs:
        raise Stop("not_judgeable", "the VBK0 inputs are not the decision's")
    block_problems = decision_block_problems(decision)
    if block_problems:
        raise Stop("not_judgeable", "; ".join(block_problems))
    return decision


# ------------------------------------------------------------------------------- grades (W-6)
def _grade_module():
    """``h8_noise_judge_4368`` (the r79 path 1 grades, as T-JR-12 reads them)."""
    import h8_noise_judge_4368

    return h8_noise_judge_4368


def grade_transitions(blocks0: dict, blocks1: dict, decision: dict,
                      judges: dict[str, tuple[Path | None, str | None]],
                      categories: dict[tuple[str, str], str] | None = None,
                      exits: dict[str, int | None] | None = None) -> dict:
    """6.3.7 / 6.3.9 record (control review of 8a3c48c7 W-6): per pair the VBK0 grade and the
    VBK grade of its line (``h8_noise_judge_4368.grade_lines`` on the r79 judge file of each arm,
    the ``grade-judge`` output); the pairs whose grade changed, with their keys; a line without a
    judge row is counted (``ungraded``). A grade input defect (no file, another sha256, not a
    judge output: :func:`grade_input_problems`) gives ``computed`` False with the reasons and
    leaves the 12b status alone (erratum 2 audit F-1: the transitions are a record)."""
    h8 = _grade_module()
    categories = categories or {}
    reports, inputs = {}, {}
    # erratum 2 audit F-1: a grade input defect is a record only ("not computed" with its
    # reason); it never reaches ``problems`` (the 12b status and exit code stay the judgement's)
    input_problems = grade_input_problems(judges, exits)
    if input_problems:
        return {"computed": False, "reason": "grade input defect (a record, 6.3.7)",
                "input_problems": input_problems}
    for arm, (path, _) in judges.items():
        reports[arm] = json.loads(path.read_text(encoding="utf-8"))
        inputs[arm] = {"path": str(path), "sha256": file_sha256(path)}
    changed, ungraded, by_transition = [], [], {}
    for block in decision["blocks"]:
        grades0 = h8.grade_lines([line.row for line in blocks0[block].values()], reports["vbk0"])
        grades1 = h8.grade_lines([line.row for line in blocks1[block].values()], reports["vbk"])
        for key in blocks0[block]:
            grade0, grade1 = grades0.get(key) or {}, grades1.get(key) or {}
            before, after = grade0.get("grade"), grade1.get("grade")
            if h8.GRADE_NOT_JUDGEABLE in (before, after) or None in (before, after):
                ungraded.append({"block": block, "key": key,
                                 "category": categories.get((block, key)),
                                 "vbk0_reason": _ungraded_reason(grade0),
                                 "vbk_reason": _ungraded_reason(grade1)})
            if before != after:
                name = f"{before}->{after}"
                by_transition[name] = by_transition.get(name, 0) + 1
                changed.append({"block": block, "key": key, "vbk0": before, "vbk": after})
    ungraded_opportunity = [item for item in ungraded if item["category"] == OPPORTUNITY]
    # erratum 2 2-1: the ungraded count is public; the causes of opportunity pairs among them too
    return {"computed": True, "inputs": inputs, "changed_pairs": len(changed),
            "by_transition": by_transition, "changed": changed,
            "ungraded_pairs": len(ungraded), "ungraded_opportunity_pairs":
                len(ungraded_opportunity), "ungraded_opportunity": ungraded_opportunity,
            "ungraded_other": [item for item in ungraded if item["category"] != OPPORTUNITY],
            "rule": "a record (6.3.7): j9_main judges the grades (6.5)"}


def grade_input_problems(judges: dict[str, tuple[Path | None, str | None]],
                         exits: dict[str, int | None] | None = None) -> list[str]:
    """Why the grade transitions cannot be computed: a grade-judge file not given (its
    ``grade-judge`` stopped: ``exits`` names its exit code, e.g. 2 on an L1 reference defect or
    3 on a tool error, erratum 2 2-1), missing, of another sha256 or not an r79 judge output
    (``runs``). A record (erratum 2 audit F-1)."""
    exits = exits or {}
    problems = []
    for arm, (path, expected) in judges.items():
        if path is None or expected is None:
            code = exits.get(arm)
            problems.append(f"{arm}: grade-judge 종료 {code} (grade-judge exit {code}: no file)"
                            if code is not None else
                            f"{arm}: no grade-judge file given (its grade-judge did not write one)")
            continue
        if not Path(path).is_file():
            problems.append(f"{arm}: grade-judge file {path} missing")
            continue
        actual = file_sha256(path)
        if actual != expected:
            problems.append(f"{arm}: grade-judge sha256 {actual[:12]} is not the given "
                            f"{expected[:12]}")
            continue
        try:
            document = json.loads(Path(path).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            problems.append(f"{arm}: grade-judge file is no JSON")
            continue
        if not isinstance(document, dict) or not isinstance(document.get("runs"), list):
            problems.append(f"{arm}: grade-judge file is no r79 judge output (runs)")
    return problems


def _ungraded_reason(grade: dict) -> str | None:
    """Why a line has no grade (None: it has one): no judge row (no L1 pair), a judge row
    without its gates, or no line (an error line is not graded)."""
    if not grade:
        return "no graded line (an error line or another level)"
    if grade.get("grade") == _grade_module().GRADE_NOT_JUDGEABLE:
        return str(grade.get("reason"))
    return None


L1_SETTING_OF_ARM = {"vbk0": "VBJ0", "vbk": "VBJ"}
"""Erratum 2 2-1: each arm grades against the L1 run of its own plant (VBK0: VBJ0, VBK: VBJ
with the VBK options and no fault plan), both ``R79_ROD_MODEL=plant_truth``."""
L1_ROD_MODEL = "plant_truth"


def l1_reference_problems(path: Path, arm: str, keys_sha256: str) -> list[str]:
    """Why ``path`` is not the arm's L1 reference run (erratum 2 2-1): the run took the fixed
    L1 key file (meta ``keys_file.sha256``); every line an L1 line of
    :data:`L1_SETTING_OF_ARM` with :data:`L1_ROD_MODEL`, without an error, at least one."""
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = document["results"] if isinstance(document, dict) else document
    if not rows:
        return ["--l1-reference has no line"]
    expected = L1_SETTING_OF_ARM[arm]
    problems = []
    keys_file = ((document.get("meta") if isinstance(document, dict) else None)
                 or {}).get("keys_file") or {}
    if keys_file.get("sha256") != keys_sha256:
        problems.append(f"--l1-reference meta keys_file.sha256 "
                        f"{str(keys_file.get('sha256'))[:12]} is not the L1 key file's")
    if keys_file.get("n_keys") != len(rows):
        problems.append(f"--l1-reference has {len(rows)} lines, its key file "
                        f"{keys_file.get('n_keys')!r} keys")
    for row in rows:
        key = str(row.get("key"))
        if row.get("level") != h8_reference_level():
            problems.append(f"{key}: level {row.get('level')!r}, not L1")
        if row.get("v5_setting") != expected:
            problems.append(f"{key}: setting {row.get('v5_setting')!r}, not {expected}")
        if row.get("rod_model") != L1_ROD_MODEL:
            problems.append(f"{key}: rod_model {row.get('rod_model')!r}, not {L1_ROD_MODEL}")
        if row.get("error"):
            problems.append(f"{key}: an error line")
    return problems


def h8_reference_level() -> str:
    return _grade_module().LEVEL_REFERENCE


def cmd_grade_judge(args) -> tuple[str, dict]:
    """``r79_sensor_judge.py judge`` of one arm's run files and the L1 reference (the r79 path 1
    grades the ``judge`` sub-command reads; ``h8_noise_judge_4368.run_r79_judge``)."""
    h8 = _grade_module()
    if file_sha256(args.l1_reference) != args.l1_reference_sha256:
        raise Stop("not_judgeable", "--l1-reference is not of the given sha256")
    l1_problems = l1_reference_problems(args.l1_reference, args.arm, args.l1_keys_sha256)
    if l1_problems:
        raise Stop("not_judgeable", "; ".join(l1_problems[:3]))
    runs = parse_block_paths(args.runs, "--runs")
    if not runs:
        raise Stop("not_judgeable", "no --runs")
    if args.judge_out.exists():
        raise Stop("not_judgeable", f"--judge-out {args.judge_out} exists (never overwritten)")
    files = [runs[block] for block in BLOCKS if block in runs]
    run = h8.run_r79_judge(args.judge_out, [*files, args.l1_reference])
    record = {"rule": "X-13 grade-judge (control review of 8a3c48c7 W-6)", "arm": args.arm,
              "inputs": {**{block: {"path": str(path), "sha256": file_sha256(path)}
                            for block, path in runs.items()},
                         "l1_reference": {"path": str(args.l1_reference),
                                          "sha256": args.l1_reference_sha256,
                                          "setting": L1_SETTING_OF_ARM[args.arm],
                                          "rod_model": L1_ROD_MODEL},
                         "l1_keys": {"sha256": args.l1_keys_sha256}},
              "judge_run": run}
    if run["exit_code"] != 0 or not args.judge_out.is_file():
        record.update(status="not_judgeable", reason=f"r79_sensor_judge exit {run['exit_code']}")
        return "not_judgeable", record
    record.update(status="written", judge_file=str(args.judge_out),
                  judge_sha256=file_sha256(args.judge_out))
    return "written", record


# ------------------------------------------------------------------------------- L1 overlap
def _command_hash(line: dict) -> str | None:
    """The line's command hash (top level, else ``base.commands_sha256`` / ``cmd_sha256``)."""
    base = line.get("base") or {}
    return line.get("commands_sha256") or base.get("commands_sha256") or base.get("cmd_sha256")


def l1_overlap(pairs: dict[str, tuple[Path, Path]]) -> dict:
    """Erratum 2 2-1 (audit warning 5, a record): per setting the keys the 12b L1 reference and
    the T-JR-12a L1 reference share, and how many of them have the same command hash (the same
    commit and a deterministic run: all should; a differing key is published)."""
    out = {}
    for setting, (l1_12b, l1_12a) in pairs.items():
        lines = []
        for path in (l1_12b, l1_12a):
            document = json.loads(Path(path).read_text(encoding="utf-8"))
            rows = document["results"] if isinstance(document, dict) else document
            lines.append({plain_key(row["key"]): row for row in rows})
        common = sorted(set(lines[0]) & set(lines[1]))
        differing = [key for key in common
                     if _command_hash(lines[0][key]) != _command_hash(lines[1][key])
                     or _command_hash(lines[0][key]) is None]
        out[setting] = {"inputs": {"12b": {"path": str(l1_12b), "sha256": file_sha256(l1_12b)},
                                   "12a": {"path": str(l1_12a), "sha256": file_sha256(l1_12a)}},
                        "common_keys": len(common), "same_hash": len(common) - len(differing),
                        "differing_hash": len(differing), "differing_keys": differing,
                        "only_12b": len(set(lines[0]) - set(lines[1])),
                        "only_12a": len(set(lines[1]) - set(lines[0]))}
    return out


def cmd_l1_overlap(args) -> tuple[str, dict]:
    pairs = {}
    for value in args.pair:
        setting, separator, files = value.partition("=")
        first, comma, second = files.partition(",")
        if not separator or not comma or setting not in L1_SETTING_OF_ARM.values():
            raise Stop("not_judgeable", f"--pair {value!r}: <VBJ|VBJ0>=<12b L1>,<12a L1>")
        pairs[setting] = (Path(first), Path(second))
    missing = [str(path) for pair in pairs.values() for path in pair if not path.is_file()]
    if missing:
        raise Stop("not_judgeable", f"L1 file missing: {missing[0]}")
    return "written", {"rule": "erratum 2 2-1 (a record, not a judgement)",
                       "status": "written", "by_setting": l1_overlap(pairs)}


# ------------------------------------------------------------------------------- dry c (6.3.10)
DRY_RUNS = ("c92", "c93")
"""The dry runs of one arm, one per dry seed, each with its own plan and key file
(``c92_plan.json`` / ``c92_keys.txt``, ``c93_...``; prelaunch audit B-1 (a)); the seeds are
``jp3_12b_plan.DRY_SEEDS`` (edition 5 erratum 6 6-3: 92 / 93)."""


def dry_run_keys(selection: dict, plans_dir: Path, problems: Problems) -> dict[str, list[str]]:
    """Per dry run the plain keys of its plan (``selection.json`` ``dry.runs``); a plan whose
    keys are not exactly its key file's is a setting defect (the runner's X-10 guard).

    Raises:
        Stop: The selection names other dry runs (not judgeable).
    """
    runs = (selection.get("dry") or {}).get("runs") or {}
    if set(runs) != set(DRY_RUNS):
        raise Stop("not_judgeable", f"selection dry runs {sorted(runs)}, {list(DRY_RUNS)} "
                                    "expected (one plan per dry seed)")
    out = {}
    for run in DRY_RUNS:
        plan = json.loads((plans_dir / runs[run]["plan"]).read_text(encoding="utf-8"))
        keys = [plain_key(key) for key in plan["faults"]]
        listed = (plans_dir / runs[run]["keys"]).read_text(encoding="utf-8").splitlines()
        if keys != listed:
            problems.setting_defects.append(f"{run}: plan keys are not its key file's")
        out[run] = keys
    return out


def dry_plan_sha256(selection: dict, run: str) -> str:
    """The sha256 the selection recorded for the plan of one dry run."""
    return selection["outputs"][selection["dry"]["runs"][run]["plan"]]


def parse_dry_paths(values: list[str] | None, option: str) -> dict[str, Path]:
    """``c92=<path>`` / ``c93=<path>`` arguments, both required.

    Raises:
        Stop: A malformed, repeated or missing run (not judgeable).
    """
    paths: dict[str, Path] = {}
    for value in values or []:
        run, separator, path = value.partition("=")
        if not separator or run not in DRY_RUNS or run in paths:
            raise Stop("not_judgeable", f"{option} {value!r}: one {'/'.join(DRY_RUNS)}=<path> "
                                        "per run")
        paths[run] = Path(path)
    if set(paths) != set(DRY_RUNS):
        raise Stop("not_judgeable", f"{option} needs {list(DRY_RUNS)}, got {sorted(paths)}")
    return paths


def load_dry_arm(expected: dict[str, list[str]], results: list[str], t4h: list[str], arm: str,
                 problems: Problems) -> dict[str, dict[str, Line]]:
    """The dry lines of one arm per dry run: the keys of that run's plan."""
    result_paths = parse_dry_paths(results, f"--{arm}")
    t4h_paths = parse_dry_paths(t4h, f"--{arm}-t4h")
    return {run: load_lines(result_paths[run], t4h_paths[run], expected[run], arm, problems)
            for run in DRY_RUNS}


def cmd_dry_c(args) -> tuple[str, dict]:
    """6.3.10: c = the share of the opportunity pairs whose commands changed (VBK against VBK0,
    ``commands_sha256``), and the trigger existence of the dry pairs (record). The decision of
    the next step (c >= 0.5 stops and asks) is the main session's."""
    selection = load_selection(args.selection, args.selection_sha256)
    problems = Problems()
    expected_by_run = dry_run_keys(selection, args.selection.parent, problems)
    expected = [key for run in DRY_RUNS for key in expected_by_run[run]]
    by_run = {arm: load_dry_arm(expected_by_run, getattr(args, arm), getattr(args, f"{arm}_t4h"),
                                arm, problems)
              for arm in SETTING_OF_ARM}
    lines = {arm: {key: line for run in DRY_RUNS for key, line in runs[run].items()}
             for arm, runs in by_run.items()}
    for arm, runs in by_run.items():
        check_presence(lines[arm], arm, problems)
        for run, run_lines in runs.items():  # B-1 (a): each run against its own plan
            plan_sha = dry_plan_sha256(selection, run)
            problems.setting_defects += [
                f"{arm} {key}: plan sha256 is not the {run} dry plan"
                for key, line in run_lines.items()
                if (line.row.get("rod_fault") or {}).get("plan_sha256") != plan_sha]
    report = {"rule": "jp3_remedy_spec_v5.md 6.3.10 (X-13 dry-c)", "pairs": len(expected),
              "inputs": {arm: {run: {"path": str(path), "sha256": file_sha256(path)}
                               for run, path in parse_dry_paths(getattr(args, arm),
                                                                f"--{arm}").items()}
                         for arm in SETTING_OF_ARM}}
    if problems.not_judgeable or problems.setting_defects:
        report.update(status=problems.status(), problems=problems.__dict__)
        return report["status"], report
    categories = dict.fromkeys(CATEGORIES, 0)
    changed = 0
    for key in expected:
        vbk0, vbk = lines["vbk0"][key], lines["vbk"][key]
        category = classify_pair(vbk, vbk0, problems)
        categories[category] += 1
        if category == OPPORTUNITY:
            changed += vbk.row.get("commands_sha256") != vbk0.row.get("commands_sha256")
    opportunity = categories[OPPORTUNITY]
    report.update(categories=categories, changed_opportunity_pairs=changed,
                  c=None if opportunity == 0 else changed / opportunity,
                  trigger_share=1.0 - categories[NO_TRIGGER] / len(expected),
                  problems=problems.__dict__)
    if opportunity == 0:
        problems.not_judgeable.append("no opportunity pair (X-5)")
    status = "written" if not (problems.not_judgeable or problems.setting_defects) else (
        problems.status())
    report["status"] = status
    return status, report


# ------------------------------------------------------------------------------- commands
def _write_new(path: Path, document: dict) -> str:
    data = (json.dumps(document, indent=1, ensure_ascii=False, default=_plain) + "\n").encode()
    with path.open("xb") as handle:
        handle.write(data)
    return hashlib.sha256(data).hexdigest()


def _plain(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    raise TypeError(f"not JSON: {type(value).__name__}")


def _parse_expected(values: list[str] | None, option: str,
                    problems: list[str]) -> dict[str, str]:
    """``b<j>=<sha256>`` expectations by block; a malformed or repeated one is a problem."""
    expected: dict[str, str] = {}
    for value in values or []:
        block, separator, sha = value.partition("=")
        if not separator or block not in BLOCKS or block in expected or not SHA256_HEX.match(sha):
            problems.append(f"{option} {value!r}: one b<j>=<64 hex sha256> per block")
            continue
        expected[block] = sha
    return expected


def expected_input_problems(args, vbk0_inputs: dict) -> tuple[dict, list[str]]:
    """Erratum 8 8-9 (d): the run file sha256 and T4h digest of b1 and b2 against the given
    expectations (8-1.3 fixed values; both required for both blocks; no other block has a
    fixed value). Returns the expectations and why they do not hold (empty: they hold)."""
    problems: list[str] = []
    runs = _parse_expected(args.expect_vbk0_sha256, "--expect-vbk0-sha256", problems)
    digests = _parse_expected(args.expect_vbk0_t4h_digest, "--expect-vbk0-t4h-digest",
                              problems)
    for name, given in (("--expect-vbk0-sha256", runs),
                        ("--expect-vbk0-t4h-digest", digests)):
        missing = [block for block in EXPECTED_VBK0_BLOCKS if block not in given]
        other = sorted(set(given) - set(EXPECTED_VBK0_BLOCKS))
        if missing:
            problems.append(f"{name} missing for {missing} (required, erratum 8 8-9 (d))")
        if other:
            problems.append(f"{name} for {other}: no fixed value (erratum 8 8-8.1, recorded "
                            "only)")
    for block in EXPECTED_VBK0_BLOCKS:
        actual = vbk0_inputs.get(block)
        if actual is None:
            problems.append(f"VBK0 {block} not given")
            continue
        for key, given in (("run_sha256", runs), ("t4h_sha256_digest", digests)):
            if block in given and actual[key] != given[block]:  # full values: any digit counts
                problems.append(f"VBK0 {block} {key} {actual[key]} is not the expected "
                                f"{given[block]}")
    expected = {block: {"run_sha256": runs.get(block), "t4h_sha256_digest": digests.get(block)}
                for block in EXPECTED_VBK0_BLOCKS}
    return expected, problems


def cmd_decide(args) -> tuple[str, dict]:
    selection = load_selection(args.selection, args.selection_sha256)
    results = parse_block_paths(args.vbk0, "--vbk0")
    t4h_dirs = parse_block_paths(args.vbk0_t4h, "--vbk0-t4h")
    problems = Problems()
    blocks = load_arm(selection, results, t4h_dirs, "vbk0", problems)
    record = {"rule": "jp3_remedy_spec_v5.md 6.3.5 / 6.3.6 with erratum 8 8-8.1 (X-13 decide)",
              "inputs": {"selection_sha256": args.selection_sha256,
                         "vbk0": input_record(results, t4h_dirs, blocks)}}
    expected, expected_problems = expected_input_problems(args, record["inputs"]["vbk0"])
    if expected_problems:  # 8-9 (d): status, reason and input sha256 only, no decision keys
        record.update(status="not_judgeable",
                      reason="erratum 8 8-9 (d): " + "; ".join(expected_problems))
        return record["status"], record
    record["inputs"]["vbk0_expected"] = {**expected, "matched": True}
    status = problems.status()
    if status != "pass":
        record.update(status=status, problems=problems.__dict__)
        return status, record
    try:
        record.update(decide(selection, blocks))
    except Stop as stop:
        record.update(getattr(stop, "record", {}), status=stop.status, reason=str(stop))
    return record["status"], record


def cmd_judge(args) -> tuple[str, dict]:
    selection = load_selection(args.selection, args.selection_sha256)
    results0 = parse_block_paths(args.vbk0, "--vbk0")
    t4h0 = parse_block_paths(args.vbk0_t4h, "--vbk0-t4h")
    problems = Problems()
    blocks0 = load_arm(selection, results0, t4h0, "vbk0", problems)
    # the decision first: a missing, changed or stopped one ends here, no VBK file opened
    decision = load_decision(args.decision, args.decision_sha256,
                             input_record(results0, t4h0, blocks0))
    if set(blocks0) != set(decision["blocks"]):
        raise Stop("not_judgeable", f"VBK0 blocks {sorted(blocks0)} are not the decided "
                                    f"{decision['blocks']}")
    results1 = parse_block_paths(args.vbk, "--vbk")
    t4h1 = parse_block_paths(args.vbk_t4h, "--vbk-t4h")
    if set(results1) != set(decision["blocks"]):
        raise Stop("not_judgeable", f"VBK blocks {sorted(results1)} are not the decided "
                                    f"{decision['blocks']}")
    blocks1 = load_arm(selection, results1, t4h1, "vbk", problems)
    report = {"rule": "jp3_remedy_spec_v5.md 6.3.7 with erratum 8 8-2 (X-13 judge)",
              "inputs": {"selection_sha256": args.selection_sha256,
                         "decision_sha256": args.decision_sha256,
                         "vbk0": input_record(results0, t4h0, blocks0),
                         "vbk": input_record(results1, t4h1, blocks1)},
              "decision": {name: decision.get(name) for name in
                           ("blocks", "blocks_used", "allow_k", "n", "n_opp", "k", "aa_floor",
                            "n_topup", "witness_topup")}}
    if problems.not_judgeable or problems.setting_defects:
        report.update(status=problems.status(), problems=problems.__dict__)
        return report["status"], report
    found = judge_pairs(blocks0, blocks1, decision, problems)
    if found["n_opp"] == 0:  # X-5: no judged row is never a pass
        problems.not_judgeable.append("no opportunity pair")
    report.update(found)
    report["ready_rule"] = {
        **judge_ready_rule(found["pairs"], decision, found["n_fault_judged"], problems),
        **ready_rule_records(found["pairs"], blocks0, blocks1, selection,
                             decision["blocks_used"])}
    try:
        report["grade_transitions"] = grade_transitions(
            blocks0, blocks1, decision,
            {"vbk0": (args.vbk0_grade_judge, args.vbk0_grade_judge_sha256),
             "vbk": (args.vbk_grade_judge, args.vbk_grade_judge_sha256)},
            {(pair["block"], pair["key"]): pair["category"] for pair in found["pairs"]},
            {"vbk0": args.vbk0_grade_judge_exit, "vbk": args.vbk_grade_judge_exit})
    except Exception as exc:  # noqa: BLE001 (erratum 2 2-1: a record; the judgement stands)
        report["grade_transitions"] = {"computed": False,
                                       "reason": f"exception {type(exc).__name__}: {exc}"}
    report["hold_speed_m_s"] = _hold_speed_record()  # erratum 2 2-5
    # erratum 8 8-10: the (1) denominator is N_1 = opportunity + VBK0-READY-missing pairs
    n_fault_judged = found["n_fault_judged"]
    report["pass_sentence"] = {"blocks_used": decision["blocks_used"],
                               "n_opp": decision.get("n_opp"),
                               "n_fault_judged": n_fault_judged,
                               "upper_bound_n_fault_judged": upper_bound(n_fault_judged),
                               "n_vbk_worse": report["ready_rule"]["n_vbk_worse"],
                               "allow_k": decision["allow_k"],
                               "k": decision.get("k"),
                               "upper_bound_k": upper_bound(decision.get("k") or 0)}
    report.update(status=problems.status(), problems=problems.__dict__,
                  problem_counts=problems.counts())
    return report["status"], report


EXIT_OF_STATUS = {"decided": EXIT_OK, "needs_b4": EXIT_OK, "pass": EXIT_OK,
                  "written": EXIT_OK, "failed": EXIT_FAILED,
                  "setting_defect": EXIT_NOT_JUDGEABLE, "not_judgeable": EXIT_NOT_JUDGEABLE}
"""Erratum 8 8-8.1: ``aa_floor_stop`` and ``needs_b3`` are no longer written."""
COMMANDS = {"decide": cmd_decide, "judge": cmd_judge, "grade-judge": cmd_grade_judge,
            "dry-c": cmd_dry_c, "l1-overlap": cmd_l1_overlap}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("decide", "judge"):
        command = sub.add_parser(name)
        command.add_argument("--selection", type=Path, required=True)
        command.add_argument("--selection-sha256", required=True)
        command.add_argument("--vbk0", action="append", required=True)
        command.add_argument("--vbk0-t4h", action="append", required=True)
        command.add_argument("--out", type=Path, required=True)
        if name == "decide":  # erratum 8 8-9 (d): required, checked by the tool (exit 2)
            command.add_argument("--expect-vbk0-sha256", action="append", default=None,
                                 help="b1|b2=<run file sha256> (erratum 8 8-1.3)")
            command.add_argument("--expect-vbk0-t4h-digest", action="append", default=None,
                                 help="b1|b2=<T4h digest of input_record> (erratum 8 8-1.3)")
        if name == "judge":
            command.add_argument("--decision", type=Path, required=True)
            command.add_argument("--decision-sha256", required=True)
            command.add_argument("--vbk", action="append", required=True)
            command.add_argument("--vbk-t4h", action="append", required=True)
            for arm in ("vbk0", "vbk"):  # W-6: the grade-judge files of both arms
                # optional (erratum 2 audit F-1): a missing one is a record, never a stop
                command.add_argument(f"--{arm}-grade-judge", type=Path, default=None)
                command.add_argument(f"--{arm}-grade-judge-sha256", default=None)
                command.add_argument(f"--{arm}-grade-judge-exit", type=int, default=None,
                                     help="the arm's grade-judge exit code when it wrote no "
                                          "file (2 or 3; a record, erratum 2 2-1)")
    grades = sub.add_parser("grade-judge")
    grades.add_argument("--arm", choices=sorted(SETTING_OF_ARM), required=True)
    grades.add_argument("--runs", action="append", required=True, help="b<j>=<run json>")
    grades.add_argument("--l1-reference", type=Path, required=True)
    grades.add_argument("--l1-reference-sha256", required=True,
                        help="the L1 run file's sha256 of FIXED_INPUTS (erratum 2 2-1)")
    grades.add_argument("--l1-keys-sha256", required=True,
                        help="the L1 key file's sha256 of FIXED_INPUTS (the run's meta must "
                             "name it)")
    grades.add_argument("--judge-out", type=Path, required=True)
    grades.add_argument("--out", type=Path, required=True)
    overlap = sub.add_parser("l1-overlap")
    overlap.add_argument("--pair", action="append", required=True,
                         help="VBJ|VBJ0=<12b L1 run>,<T-JR-12a L1 run>")
    overlap.add_argument("--out", type=Path, required=True)
    dry = sub.add_parser("dry-c")
    dry.add_argument("--selection", type=Path, required=True)
    dry.add_argument("--selection-sha256", required=True)
    for arm in ("vbk0", "vbk"):
        dry.add_argument(f"--{arm}", action="append", required=True,
                         help=f"{'|'.join(DRY_RUNS)}=<run json>")
        dry.add_argument(f"--{arm}-t4h", action="append", required=True,
                         help=f"{'|'.join(DRY_RUNS)}=<T4h folder>")
    dry.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.out.exists():
        print(json.dumps({"status": "not_judgeable", "reason": "--out exists",
                          "out": str(args.out)}))
        return EXIT_NOT_JUDGEABLE
    try:
        status, document = COMMANDS[args.command](args)
    except Stop as stop:
        status, document = stop.status, {"status": stop.status, "reason": str(stop)}
    except Exception as exc:  # (마): any unexpected exception is a tool error, never a verdict
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(json.dumps({"status": "error", "out": str(args.out)}))
        return EXIT_ERROR
    exit_code = EXIT_OF_STATUS[status]
    document["exit"] = exit_code
    sha = _write_new(args.out, document)
    counts = document.get("problem_counts") or {
        name: len(values) for name, values in (document.get("problems") or {}).items()}
    print(json.dumps({"status": status, "out": str(args.out), "out_sha256": sha, **counts}))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
