"""436.9 edition 7 condition 3 adoption (``jp3_remedy_spec_v7.md`` 4 step 2, "조건 3 채택 규칙").

Reads the ``ed7_probe.py`` lines (a design input before the seal, public; not a judgement).
The rule (stats S3, fixed before the seal): arm 3 (condition 3 = first draft) or arm 4
(condition 3 = (나)) replaces arm 2 only when all three hold, else arm 2 stays:

1. ``fewer_failed_units``: fewer failed units against V0 than arm 2 (strictly);
2. ``no_new_failed_units``: no unit that passes in arm 2 fails;
3. ``twist_not_worse``: every twist indicator at most arm 2's - the ratio of A(i)-b shots that
   grew ``|D|``, the four-leg twist triggers, ``n_rev``, the latches.

A unit is one (plant, key) of the main part. Its failure against V0 is the edition 6 probe
share reading (``ed6_probe_share.group_judgement``): a J1 .. J11 ``fail`` item of the
``jp3_j9main_judge._full_items`` table against the stored V0 line of the same row and phase
(an item fails only where V0 passes it), and an R15 worsening fails both R15 keys. A group
with ``no_reference`` or a not-judgeable item makes the comparison not judgeable.

The spec leaves five readings open; the tool does not pick one (spec rule: an unstated
reading goes to 확인 필요). It evaluates the rule under every combination (32) and reports
whether the outcome depends on the reading:

=================  ==========================================================================
reading            values
=================  ==========================================================================
``j7``             ``ed6_share`` (the 436.8 J7 period comparison, as the edition 6 probe share)
                   / ``ed7_new`` (J7 by ``(name, leg, reason)``, ``jp3_ed7_rules.j7_items_ed7``)
``stiffness``      ``none`` (as the edition 6 probe share) / ``sens_exempt`` (the spec 6.2
                   sensitivity J7 stiffness exception on the plants Mslow, Mfast, Mc005, Mc04:
                   a unit whose J7 fail names are exactly ``WARN_PROBE_STIFFNESS_OUT_OF_RANGE``
                   does not fail on them)
``plants``         ``vbm5`` (M, Mslow, Mfast, Mc005, Mc04) / ``all6`` (also the edition 6
                   control plant L)
``ratio``          ``known_shots`` (shots with a ``twist_grew`` value) / ``all_shots``
``n_rev``          ``sum`` (all legs, all lines) / ``line_max`` (the largest per-line sum)
=================  ==========================================================================

Per reading the outcome is ``a2``, ``a3``, ``a4``, ``both_qualify`` (the spec does not say
which one then) or ``not_judgeable``. The ``conclusion`` is an arm only when every reading
gives that same arm.

The report also carries the Q7-C4 facts of every probe line (both parts, every arm): the
``WARN_PROBE_RETRACT_NOT_OPENED`` lines and legs, whether the rounds that raised it were
retract-first (reversed) probe rounds, and how the WARN enters the line's J7 against V0; the
D6 witness round, not-judgeable round and reversed round counts.

======  =====================  ==========================================================
exit    status                 meaning
======  =====================  ==========================================================
0       ``decided``            report written, checks clean, every reading the same arm
2       ``setting_defect``     report written; a compared line's tag, components, condition,
                               options, probe block or blind record, a line's D6 witness
                               record, the run identity (or with ``--require-clean`` this
                               checkout) differs (``checks``)
2       ``incomplete``         report written; a planned job missing, repeated, unplanned or
                               an error line
2       ``not_judgeable``      report written; no reading could be judged
2       ``undecided``          report written; the readings differ, or arms 3 and 4 both
                               qualify
2       ``input_error``        no report: missing input, another sha256, an existing ``--out``
3       ``tool_error``         an unexpected failure
======  =====================  ==========================================================
(status order: setting_defect > incomplete > not_judgeable > undecided > decided)

Usage (dynamics-dev, checkout root):
  python -I -B 04_scripts/04_hydraulic/coupled/ed7_condition3_adoption.py
      --rows <ed7_probe.jsonl> --keys <probe_keys_ed7.json> [--keys-sha256 <sha>]
      --v0 <stored v5/main.jsonl> --v0-sha256 <sha> --out <report.json> [--require-clean]
The T4h records are read from ``<rows stem>_t4h/``, the run identity from
``<rows stem>.identity.json``. The stdout's last line is JSON with ``status``, the counts and
the report path (no indicator value).
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import itertools
import json
import subprocess
import sys
import traceback
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import jp3_ed7_rules as rules  # noqa: E402

EXIT_DECIDED, EXIT_STOP, EXIT_TOOL = 0, 2, 3
BASE_ARM = "a2"
CANDIDATE_ARMS = ("a3", "a4")
COMPARED_ARMS = (BASE_ARM, *CANDIDATE_ARMS)
EXPECTED_TAG = "final_C4G2_P3X_LAS_K1_LSB"
EXPECTED_CONDITION = {"a2": "with_twist", "a3": "level_incomplete",
                      "a4": "attitude_clearance"}
"""``lsb_settings.ib_condition`` of each compared arm (spec 3.1 (다) / first draft / (나))."""
MAIN_PART = "main"
VBM_PLANTS = ("M", "Mslow", "Mfast", "Mc005", "Mc04")
CONTROL_PLANT = "L"
READINGS: dict[str, tuple[str, ...]] = {"j7": ("ed6_share", "ed7_new"),
                                        "stiffness": ("none", "sens_exempt"),
                                        "plants": ("vbm5", "all6"),
                                        "ratio": ("known_shots", "all_shots"),
                                        "n_rev": ("sum", "line_max")}
PLANT_SETS = {"vbm5": VBM_PLANTS, "all6": (*VBM_PLANTS, CONTROL_PLANT)}
STIFFNESS_WARNING = "WARN_PROBE_STIFFNESS_OUT_OF_RANGE"
SENSITIVITY_PLANTS = tuple(name.removeprefix("VB") for name in rules.SENSITIVITY_JUDGED)
"""The probe plants of the four judged sensitivity settings (VBMslow -> Mslow, ...): the
plants of the spec 6.2 J7 stiffness exception reading."""
TWIST_INDICATORS = ("twist_grew_ratio", "four_leg_twist_triggers", "n_rev", "latches")
R15_KEYS = ("R15_o0.0", "R15_o0.05")
V0_SETTING = "V0"
JUDGED_LABEL = "VB"
"""The 436.8 table label a probe group takes (``ed6_probe_share.group_judgement``)."""
RUNTIME_JOB_FIELDS = ("mask", "t4h_dir")
WARN_EVENT = "WARN_PROBE_RETRACT_NOT_OPENED"
"""Spec 3.2: raised after ``probe_d6_settings.not_opened_warn_rounds`` not-judgeable D6
rounds of a leg in a row."""
D6_BLOCK_KEYS = ("rounds", "not_judgeable_rounds", "reversed_rounds")
REVERSED_KINDS = ("not_substituted", "substituted")
WITNESS_COUNT_KEYS = ("rounds", "is_reversed_rounds", "not_judgeable_rounds",
                      "reversed_not_substituted", "reversed_substituted")
LEGS = ("FL", "FR", "RL", "RR")
BLIND_KEYS = ("shots", "legs", "four_leg_twist_triggers")
BLIND_LEG_KEYS = ("n_rev", "latches")
SHOT_KEYS = ("twist_grew",)
"""The ``lsb_record.blind`` keys the twist indicators read (spec 3.1 "기록")."""


class InputError(Exception):
    """No report can be written (exit 2)."""


# ------------------------------------------------------------------------------ inputs
def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def job_identity(job: Mapping) -> str:
    """A job without its runtime fields, as sorted JSON (the probe key file's ``job``)."""
    return json.dumps({k: v for k, v in job.items() if k not in RUNTIME_JOB_FIELDS},
                      sort_keys=True)


@dataclass(frozen=True)
class PlannedLine:
    """One planned probe job of the key file."""

    plant: str
    arm: str
    key: str
    part: str


def read_key_file(path: Path, expected_sha256: str | None) -> tuple[dict, dict[str, PlannedLine]]:
    """The key file and its planned jobs by job identity.

    Raises:
        InputError: Missing file, another sha256, or a line count other than ``expected_lines``.
    """
    if not path.is_file():
        raise InputError(f"--keys {path} not found")
    if expected_sha256 is not None and file_sha256(path) != expected_sha256:
        raise InputError(f"--keys {path.name} is not of the given sha256")
    keys = json.loads(path.read_text(encoding="utf-8"))
    planned = {}
    for line in keys["lines"]:
        _, plant, arm = line["job"]["setting"].split("-")
        planned[job_identity(line["job"])] = PlannedLine(plant, arm, line["key"], line["part"])
    if len(planned) != keys["expected_lines"]:
        raise InputError(f"--keys: {len(planned)} distinct jobs, {keys['expected_lines']} "
                         "expected")
    return keys, planned


def v0_metric_rows(v0_path: Path, v0_sha256: str) -> list[dict]:
    """436.8 path 1 metrics of the stored V0 lines of the ``main`` batch.

    Raises:
        InputError: Another sha256 or no V0 line.
    """
    import jp3_j9main_judge as j9judge
    import judge4368_common as common

    try:
        rows = j9judge.stored_v0_rows(v0_path, v0_sha256)
    except j9judge.NotJudgeable as exc:
        raise InputError(str(exc)) from exc
    folders = tuple(common.t4h_folders(v0_path, rows))
    return j9judge._metric_rows(rows, folders, relabel=False)


def line_metric(record: dict, t4h_dir: Path) -> dict:
    """436.8 path 1 metrics of one probe line, labelled as the judged setting."""
    import judge_stage1_4368 as path1

    metric = path1.metrics(record, (t4h_dir,))
    metric["setting"] = JUDGED_LABEL
    return metric


@functools.cache
def _probe_settings() -> dict:
    import ed7_probe

    return ed7_probe.probe_settings()


def expected_options(setting: str) -> dict:
    """``hydraulic_options`` of a probe setting as ``ed7_probe.py`` defines it."""
    from outrigger_sim.hydraulics.v5_options import HydraulicOptions

    return HydraulicOptions.from_dict(_probe_settings()[setting][1]).to_dict()


# ------------------------------------------------------------------------------ twist
@dataclass(frozen=True)
class TwistRecord:
    """The A(i)-b record counts of one line (``lsb_record.blind``)."""

    shots: int
    shots_known: int
    shots_grew: int
    four_leg_triggers: int
    n_rev: int
    latches: int


def twist_record(record: Mapping) -> TwistRecord | None:
    """The line's twist counts; None when the ``blind`` block or one of the keys it is read
    from is missing (a missing count is never read as 0)."""
    blind = (record.get("lsb_record") or {}).get("blind")
    if not isinstance(blind, Mapping) or any(key not in blind for key in BLIND_KEYS):
        return None
    legs, shots = blind["legs"], blind["shots"]
    if sorted(legs) != sorted(LEGS) or any(key not in legs[leg] for leg in LEGS
                                           for key in BLIND_LEG_KEYS):
        return None
    if any(key not in shot for shot in shots for key in SHOT_KEYS):
        return None
    return TwistRecord(shots=len(shots),
                       shots_known=sum(shot["twist_grew"] is not None for shot in shots),
                       shots_grew=sum(bool(shot["twist_grew"]) for shot in shots),
                       four_leg_triggers=int(blind["four_leg_twist_triggers"]),
                       n_rev=sum(int(legs[leg]["n_rev"]) for leg in LEGS),
                       latches=sum(int(legs[leg]["latches"]) for leg in LEGS))


def twist_indicators(records: Iterable[TwistRecord], ratio: str, n_rev: str) -> dict:
    """The four twist indicators of one arm over its lines (a ratio without a shot is None)."""
    records = list(records)
    shots_grew = sum(r.shots_grew for r in records)
    denominator = sum(r.shots_known if ratio == "known_shots" else r.shots for r in records)
    n_rev_values = [r.n_rev for r in records]
    return {"twist_grew_ratio": shots_grew / denominator if denominator else None,
            "four_leg_twist_triggers": sum(r.four_leg_triggers for r in records),
            "n_rev": sum(n_rev_values) if n_rev == "sum" else max(n_rev_values, default=0),
            "latches": sum(r.latches for r in records),
            "shots": sum(r.shots for r in records), "shots_grew": shots_grew,
            "ratio_denominator": denominator}


def is_not_worse(candidate: float | None, base: float | None) -> bool | None:
    """``candidate <= base``; two missing ratios are equal, one missing is not comparable."""
    if candidate is None and base is None:
        return True
    if candidate is None or base is None:
        return None
    return candidate <= base


# ------------------------------------------------------------------------------ V0 items
def _j7_ed7_items(rows_by: Mapping[str, list[dict]]) -> list[dict]:
    """``jp3_ed7_rules.j7_items_ed7`` of every judged row against its V0 row."""
    base = {(row["row"], row["phase"]): row for row in rows_by.get(V0_SETTING, [])}
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows_by.get(V0_SETTING, []):
        groups[row["group"]].append(row)
    items = []
    for row in rows_by.get(JUDGED_LABEL, []):
        reference = base.get((row["row"], row["phase"]))
        if reference is not None:
            items += [{"row": row["row"], "phase": row["phase"], **item}
                      for item in rules.j7_items_ed7(reference, row, groups[row["group"]])]
    return items


def group_judgement(metrics_by_key: Mapping[str, dict], v0_rows: list[dict]) -> dict:
    """The V0 items of one (plant, arm) group under both J7 readings and its failed keys."""
    import jp3_j9main_judge as j9judge
    import judge_stage1_4368 as path1

    rows_by = path1._by_setting(list(metrics_by_key.values()) + v0_rows)
    part = j9judge._full_items(rows_by, (JUDGED_LABEL,), V0_SETTING)[JUDGED_LABEL]
    key_of = {(metric["row"], metric["phase"]): key for key, metric in metrics_by_key.items()}
    items_by_reading = {"ed6_share": part["items"],
                        "ed7_new": [item for item in part["items"] if item["item"] != "J7"]
                        + _j7_ed7_items(rows_by)}
    r15 = j9judge.r15_worsening(rows_by)
    r15_failed = {key for key in R15_KEYS if key in metrics_by_key} if r15["failures"] else set()
    out = {"lines": len(metrics_by_key), "no_reference": part["no_reference"],
           "keys_without_reference": sorted(key_of[(row, phase)]
                                            for row, phase in part["no_reference"]),
           "r15_worsening": {key: r15[key] for key in ("pairs", "state") if key in r15},
           "r15_failed_keys": sorted(r15_failed),
           "failed_keys": {}, "fail_items": {}, "not_judgeable_items": {}}
    for reading, items in items_by_reading.items():
        fails = [dict(item, key=key_of[(item["row"], item["phase"])])
                 for item in items if item["kind"] == "fail"]
        out["fail_items"][reading] = fails
        out["failed_keys"][reading] = sorted(failed_keys(out, reading, exempt_stiffness=False))
        out["not_judgeable_items"][reading] = (
            [item for item in items if item["kind"] == "not_judgeable"]
            + j9judge.r15_not_judgeable(r15))
    return out


def _first_token(name: str) -> str:
    """The event name of a J7 detail (``jp3_ed6_judge._first_token``)."""
    return name.split(":", 1)[0].split(" at period ", 1)[0]


def failed_keys(group: Mapping, j7: str, exempt_stiffness: bool) -> set[str]:
    """The failed keys of a group under a J7 reading; with ``exempt_stiffness`` a key whose
    J7 fail items name exactly :data:`STIFFNESS_WARNING` (single condition, spec 6.2) does
    not fail on them."""
    items_by_key: dict[str, list[dict]] = defaultdict(list)
    for item in group["fail_items"][j7]:
        items_by_key[item["key"]].append(item)
    failed = set(group["r15_failed_keys"])
    for key, items in items_by_key.items():
        j7_names = {_first_token(item["detail"]) for item in items if item["item"] == "J7"}
        if exempt_stiffness and j7_names == {STIFFNESS_WARNING}:
            items = [item for item in items if item["item"] != "J7"]
        if items:
            failed.add(key)
    return failed


# ------------------------------------------------------------------------------ rule
@dataclass(frozen=True)
class Reading:
    """One combination of the four open readings (module docstring)."""

    j7: str
    stiffness: str
    plants: str
    ratio: str
    n_rev: str

    @property
    def name(self) -> str:
        return " ".join(f"{name}={value}" for name, value in asdict(self).items())


def all_readings() -> list[Reading]:
    return [Reading(*values) for values in itertools.product(*READINGS.values())]


@dataclass
class ArmEvidence:
    """What the rule reads of one arm: its groups by plant and its line twist records."""

    groups: dict[str, dict] = field(default_factory=dict)
    twist: dict[str, list[TwistRecord]] = field(default_factory=dict)


def failed_units(evidence: ArmEvidence, reading: Reading) -> set[tuple]:
    """The failed (plant, key) units of an arm under a reading."""
    units = set()
    for plant in PLANT_SETS[reading.plants]:
        is_exempt = reading.stiffness == "sens_exempt" and plant in SENSITIVITY_PLANTS
        units |= {(plant, key) for key in failed_keys(evidence.groups[plant], reading.j7,
                                                      exempt_stiffness=is_exempt)}
    return units


def judgeability_problems(evidence: Mapping[str, ArmEvidence], reading: Reading) -> list[str]:
    """Why the compared groups of a reading cannot be compared (empty: they can)."""
    problems = []
    for arm in COMPARED_ARMS:
        for plant in PLANT_SETS[reading.plants]:
            group = evidence[arm].groups.get(plant)
            if group is None:
                problems.append(f"{plant} {arm}: no group")
            elif group["no_reference"]:
                problems.append(f"{plant} {arm}: no_reference {group['no_reference']}")
            elif group["not_judgeable_items"][reading.j7]:
                problems.append(f"{plant} {arm}: not-judgeable items")
            elif len(evidence[arm].twist.get(plant, [])) != group["lines"]:
                problems.append(f"{plant} {arm}: a line without its blind record")
    return problems


def arm_indicators(evidence: ArmEvidence, reading: Reading) -> dict:
    plants = PLANT_SETS[reading.plants]
    records = [record for plant in plants for record in evidence.twist[plant]]
    failed = failed_units(evidence, reading)
    return {"failed_units": len(failed), "failed_unit_list": sorted(map(list, failed)),
            **twist_indicators(records, reading.ratio, reading.n_rev)}


def compare_arm(candidate: dict, base: dict, candidate_failed: set, base_failed: set) -> dict:
    """The three criteria of one candidate arm against arm 2 (``True`` = met, None = not
    comparable)."""
    new_failed = sorted(map(list, candidate_failed - base_failed))
    twist = {name: is_not_worse(candidate[name], base[name]) for name in TWIST_INDICATORS}
    twist_met = (None if any(value is None for value in twist.values())
                 else all(twist.values()))
    criteria = {"fewer_failed_units": candidate["failed_units"] < base["failed_units"],
                "no_new_failed_units": not new_failed, "twist_not_worse": twist_met}
    adopted = None if twist_met is None else all(criteria.values())
    return {"criteria": criteria, "twist_by_indicator": twist, "new_failed_units": new_failed,
            "adopted": adopted}


def reading_outcome(evidence: Mapping[str, ArmEvidence], reading: Reading) -> dict:
    """The adoption rule under one reading (module docstring)."""
    problems = judgeability_problems(evidence, reading)
    if problems:
        return {"reading": asdict(reading), "outcome": "not_judgeable", "problems": problems}
    indicators = {arm: arm_indicators(evidence[arm], reading) for arm in COMPARED_ARMS}
    base_failed = failed_units(evidence[BASE_ARM], reading)
    comparisons = {arm: compare_arm(indicators[arm], indicators[BASE_ARM],
                                    failed_units(evidence[arm], reading), base_failed)
                   for arm in CANDIDATE_ARMS}
    adopted = [arm for arm, result in comparisons.items() if result["adopted"]]
    if any(result["adopted"] is None for result in comparisons.values()):
        outcome = "not_judgeable"
    elif len(adopted) > 1:
        outcome = "both_qualify"
    else:
        outcome = adopted[0] if adopted else BASE_ARM
    return {"reading": asdict(reading), "outcome": outcome, "indicators": indicators,
            "comparisons": comparisons}


def adoption(evidence: Mapping[str, ArmEvidence]) -> dict:
    """Every reading and the conclusion (an arm only when all readings give it)."""
    results = [dict(reading_outcome(evidence, reading), name=reading.name)
               for reading in all_readings()]
    outcomes = Counter(result["outcome"] for result in results)
    single = next(iter(outcomes)) if len(outcomes) == 1 else None
    if single in COMPARED_ARMS:
        status, conclusion = "decided", single
    elif set(outcomes) == {"not_judgeable"}:
        status, conclusion = "not_judgeable", None
    else:
        status, conclusion = "undecided", None
    return {"status": status, "conclusion": conclusion, "outcomes": dict(outcomes),
            "readings": results}


# ------------------------------------------------------------------------------ Q7-C4
def warn_legs(record: Mapping) -> list[str]:
    """Legs with ``WARN_PROBE_RETRACT_NOT_OPENED`` in ``event_names`` or ``events``."""
    names = [str(name) for name in record.get("event_names") or {}]
    names += [str(event[1]) for event in record.get("events") or []]
    return sorted({name.split(":")[1] for name in names
                   if name.startswith(f"{WARN_EVENT}:") and len(name.split(":")) > 1})


def warn_streak(rounds: list[Mapping], leg: str, warn_rounds: int) -> list[Mapping] | None:
    """The leg's not-opened rounds that first reached ``warn_rounds`` in a row (None: never)."""
    streak: list[Mapping] = []
    for item in rounds:
        if item.get("leg") != leg:
            continue
        streak = [] if item.get("is_opened") else [*streak, item]
        if len(streak) >= warn_rounds:
            return streak
    return None


def warn_path(streak: list[Mapping] | None) -> str:
    """Whether the rounds that raised the WARN were reversed (retract-first) probe rounds."""
    if streak is None:
        return "streak_not_in_rounds"
    reversed_count = sum(bool(item.get("is_reversed")) for item in streak)
    if reversed_count == len(streak):
        return "reversed_all"
    return "reversed_some" if reversed_count else "not_reversed"


def warn_j7_effect(group: Mapping | None, key: str, leg: str) -> str:
    """How the WARN of ``leg`` enters the J7 of line ``key`` against V0. Both J7 readings treat
    a WARN name the same way (new against V0 = a J7 failure); the edition 6 share items are
    read."""
    if group is None:
        return "not_computed"
    if key in group["keys_without_reference"]:
        return "no_v0_reference"
    items = [item for item in group["fail_items"]["ed6_share"] if item["key"] == key]
    is_warn = [item["item"] == "J7" and item["detail"] == f"{WARN_EVENT}:{leg}"
               for item in items]
    if not any(is_warn):
        return "warn_not_a_j7_fail"
    return "warn_is_the_only_fail_item" if all(is_warn) else "other_fail_items_too"


def witness_counts(block: Mapping | None) -> dict | None:
    """Round counts of a ``probe_d6_record`` (None: no record or a key missing; a missing
    count is not read as 0). A line without the witness (arm ``c2``) or without a probe round
    has no record."""
    if not block or any(key not in block for key in D6_BLOCK_KEYS):
        return None
    reversed_rounds = block["reversed_rounds"]
    if any(kind not in reversed_rounds for kind in REVERSED_KINDS):
        return None
    rounds = block["rounds"]
    return {"rounds": len(rounds),
            "is_reversed_rounds": sum(bool(item.get("is_reversed")) for item in rounds),
            "not_judgeable_rounds": sum(block["not_judgeable_rounds"]),
            "reversed_not_substituted": sum(reversed_rounds["not_substituted"]),
            "reversed_substituted": sum(reversed_rounds["substituted"])}


def d6_facts(record: Mapping, planned: PlannedLine) -> dict:
    """The D6 witness counts and the WARN legs (with the path that raised each) of a line."""
    block = record.get("probe_d6_record")
    counts = witness_counts(block)
    warn_rounds = (record.get("probe_d6_settings") or {}).get("not_opened_warn_rounds")
    rounds = (block or {}).get("rounds") or []
    paths = {}
    for leg in warn_legs(record):
        paths[leg] = ("warn_rounds_setting_missing" if warn_rounds is None
                      else warn_path(warn_streak(rounds, leg, int(warn_rounds))))
    return {"plant": planned.plant, "arm": planned.arm, "part": planned.part,
            "key": planned.key, "has_witness_record": block is not None,
            "witness_record_incomplete": block is not None and counts is None,
            **(counts or dict.fromkeys(WITNESS_COUNT_KEYS, 0)), "warn_legs": paths}


def q7c4_summary(facts: list[dict]) -> dict:
    """Counts of the Q7-C4 facts over every line (``warn_lines`` lists each WARN line)."""
    totals = Counter()
    by_arm: dict[str, Counter] = defaultdict(Counter)
    for fact in facts:
        counts = {"lines": 1, "lines_with_witness_record": fact["has_witness_record"],
                  "lines_witness_record_incomplete": fact["witness_record_incomplete"],
                  "rounds": fact["rounds"], "is_reversed_rounds": fact["is_reversed_rounds"],
                  "not_judgeable_rounds": fact["not_judgeable_rounds"],
                  "reversed_not_substituted": fact["reversed_not_substituted"],
                  "reversed_substituted": fact["reversed_substituted"],
                  "warn_lines": bool(fact["warn_legs"]), "warn_legs": len(fact["warn_legs"])}
        totals.update(counts)
        by_arm[fact["arm"]].update(counts)
    warn_lines = [fact for fact in facts if fact["warn_legs"]]
    paths = Counter(path for fact in warn_lines for path in fact["warn_legs"].values())
    effects = Counter(effect for fact in warn_lines
                      for effect in fact.get("warn_j7_effect", {}).values())
    return {"totals": dict(totals), "by_arm": {arm: dict(c) for arm, c in sorted(by_arm.items())},
            "warn_paths": dict(paths), "warn_j7_effects": dict(effects),
            "warn_lines": warn_lines}


# ------------------------------------------------------------------------------ checks
def line_problems(record: Mapping, planned: PlannedLine, keys: Mapping,
                  options_of: Callable[[str], dict]) -> list[str]:
    """Tag, components, condition 3 variant, options and probe block of a compared line."""
    arm, setting = planned.arm, record["job"]["setting"]
    components = list(keys["arms"][arm])
    block = record.get("ed7_probe") or {}
    found = {"controller_tag": (record.get("controller_tag"), EXPECTED_TAG),
             "lsb_components": (record.get("lsb_components"), components),
             "lsb_record.components": ((record.get("lsb_record") or {}).get("components"),
                                       components),
             "ib_condition": ((record.get("lsb_settings") or {}).get("ib_condition"),
                              EXPECTED_CONDITION[arm]),
             "ed7_probe plant / arm / part": ((block.get("plant"), block.get("arm"),
                                               block.get("part")),
                                              (planned.plant, arm, planned.part)),
             "ed7_probe.lsb_parameters": (block.get("lsb_parameters"),
                                          keys["arm_parameters"].get(arm, {})),
             "hydraulic_options": (record.get("hydraulic_options"), options_of(setting))}
    problems = [f"{name} {value!r} != {expected!r}" for name, (value, expected) in found.items()
                if value != expected]
    if block.get("foreign_modules"):
        problems.append(f"modules from another checkout: {block['foreign_modules'][:3]}")
    if twist_record(record) is None:
        problems.append("lsb_record.blind block missing or incomplete")
    return problems


def run_identity_problems(identity: Mapping | None) -> list[str]:
    """The probe run started and ended on one clean commit."""
    if identity is None:
        return ["no run identity file"]
    entries = [*(identity.get("start") or []), *(identity.get("end") or [])]
    heads = {(entry.get("git") or {}).get("head") for entry in entries}
    problems = []
    if not entries or len(heads) != 1 or None in heads:
        problems.append(f"run identity heads {sorted(map(str, heads))}")
    if any((entry.get("git") or {}).get("is_clean") is not True for entry in entries):
        problems.append("run identity not clean")
    return problems


def code_identity() -> dict:
    """This checkout's HEAD and cleanliness; a git failure is kept apart from a dirty tree."""
    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True,
                              text=True, timeout=60, check=False)

    try:
        head, status = git("rev-parse", "HEAD"), git("status", "--porcelain")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"checkout": str(ROOT), "head": None, "is_clean": None, "git_error": str(exc)}
    if head.returncode or status.returncode or not head.stdout.strip():
        return {"checkout": str(ROOT), "head": None, "is_clean": None,
                "git_error": (head.stderr or status.stderr).strip()[:300]}
    return {"checkout": str(ROOT), "head": head.stdout.strip(),
            "is_clean": not status.stdout.strip()}


# ------------------------------------------------------------------------------ run
@dataclass
class ScanResult:
    """What one pass over the probe lines collects."""

    found: Counter = field(default_factory=Counter)
    error_jobs: list = field(default_factory=list)
    unplanned: list = field(default_factory=list)
    line_problems: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    """``(plant, arm, part) -> {key: metric}`` of the compared and the WARN lines."""
    twist: dict = field(default_factory=lambda: defaultdict(list))
    facts: list = field(default_factory=list)


def is_compared(planned: PlannedLine) -> bool:
    return planned.part == MAIN_PART and planned.arm in COMPARED_ARMS


def scan_lines(rows_path: Path, t4h_dir: Path, planned: Mapping[str, PlannedLine],
               keys: Mapping, options_of: Callable[[str], dict]) -> ScanResult:
    """Stream the probe lines once (the file is large): checks, metrics, twist, D6 facts."""
    scan = ScanResult()
    with rows_path.open(encoding="utf-8") as handle:
        for text in handle:
            if not text.strip():
                continue
            record = json.loads(text)
            identity = job_identity(record["job"])
            entry = planned.get(identity)
            if "error" in record:
                scan.error_jobs.append(record["job"])
                continue
            if entry is None:
                scan.unplanned.append(record["job"])
                continue
            scan.found[identity] += 1
            _collect_line(scan, record, entry, t4h_dir, keys, options_of)
    return scan


def _collect_line(scan: ScanResult, record: dict, entry: PlannedLine, t4h_dir: Path,
                  keys: Mapping, options_of: Callable[[str], dict]) -> None:
    fact = d6_facts(record, entry)
    scan.facts.append(fact)
    if is_compared(entry):
        problems = line_problems(record, entry, keys, options_of)
        if problems:
            scan.line_problems[f"{record['job']['setting']} {entry.key}"] = problems
        twist = twist_record(record)
        if twist is not None:
            scan.twist[(entry.plant, entry.arm)].append(twist)
    if is_compared(entry) or fact["warn_legs"]:
        metric = line_metric(record, t4h_dir)
        scan.metrics.setdefault((entry.plant, entry.arm, entry.part), {})[entry.key] = metric


def build_evidence(scan: ScanResult, v0_rows: list[dict]) -> tuple[dict, dict]:
    """Arm evidence of the compared arms and every group judgement by ``plant arm part``."""
    groups = {key: group_judgement(metrics, v0_rows) for key, metrics in scan.metrics.items()}
    evidence = {arm: ArmEvidence() for arm in COMPARED_ARMS}
    for (plant, arm, part), group in groups.items():
        if part == MAIN_PART and arm in COMPARED_ARMS:
            evidence[arm].groups[plant] = group
            evidence[arm].twist[plant] = scan.twist.get((plant, arm), [])
    return evidence, groups


def attach_warn_effects(facts: list[dict], groups: Mapping[tuple, dict]) -> None:
    """The J7 effect of every WARN leg, read from the group judgement of its line."""
    for fact in facts:
        if not fact["warn_legs"]:
            continue
        group = groups.get((fact["plant"], fact["arm"], fact["part"]))
        fact["warn_j7_effect"] = {leg: warn_j7_effect(group, fact["key"], leg)
                                  for leg in fact["warn_legs"]}


def checks_of(scan: ScanResult, planned: Mapping[str, PlannedLine],
              run_identity: Mapping | None) -> dict:
    missing = [planned[identity].key + " " + identity for identity in planned
               if scan.found[identity] == 0]
    repeated = [identity for identity, count in scan.found.items() if count > 1]
    incomplete_witness = [f"{fact['plant']} {fact['arm']} {fact['key']}" for fact in scan.facts
                          if fact["witness_record_incomplete"]]
    return {"missing_jobs": missing, "repeated_jobs": repeated,
            "unplanned_jobs": scan.unplanned, "error_lines": scan.error_jobs,
            "line_problems": scan.line_problems,
            "witness_record_incomplete": incomplete_witness,
            "run_identity_problems": run_identity_problems(run_identity)}


DEFECT_CHECKS = ("line_problems", "witness_record_incomplete", "run_identity_problems",
                 "code_problems")
INCOMPLETE_CHECKS = ("missing_jobs", "repeated_jobs", "unplanned_jobs", "error_lines")


def status_of(checks: Mapping, decision: Mapping) -> str:
    """Module docstring order: setting_defect > incomplete > the decision's status."""
    if any(checks.get(name) for name in DEFECT_CHECKS):
        return "setting_defect"
    if any(checks[name] for name in INCOMPLETE_CHECKS):
        return "incomplete"
    return decision["status"]


def build_report(args: argparse.Namespace) -> dict:
    rows_path = args.rows.resolve()
    t4h_dir = rows_path.with_name(f"{rows_path.stem}_t4h")
    identity_path = rows_path.with_name(f"{rows_path.stem}.identity.json")
    if not rows_path.is_file() or not t4h_dir.is_dir():
        raise InputError(f"--rows {rows_path} or its T4h folder {t4h_dir.name} not found")
    keys, planned = read_key_file(args.keys.resolve(), args.keys_sha256)
    v0_rows = v0_metric_rows(args.v0, args.v0_sha256)
    run_identity = (json.loads(identity_path.read_text(encoding="utf-8"))
                    if identity_path.is_file() else None)
    scan = scan_lines(rows_path, t4h_dir, planned, keys, expected_options)
    evidence, groups = build_evidence(scan, v0_rows)
    attach_warn_effects(scan.facts, groups)
    checks = checks_of(scan, planned, run_identity)
    code = code_identity()
    if args.require_clean and code.get("is_clean") is not True:
        checks["code_problems"] = [f"checkout not clean or git failed: {code}"]
    decision = adoption(evidence)
    return {"status": status_of(checks, decision),
            "rule": "jp3_remedy_spec_v7.md 4 step 2 조건 3 채택 규칙 (revision 4)",
            "inputs": _inputs(rows_path, args, keys, run_identity), "code_identity": code,
            "checks": checks, "decision": decision,
            "groups": {f"{plant} {arm} {part}": group
                       for (plant, arm, part), group in groups.items()},
            "q7c4": q7c4_summary(scan.facts)}


def _inputs(rows_path: Path, args: argparse.Namespace, keys: Mapping,
            run_identity: Mapping | None) -> dict:
    heads = sorted({str((entry.get("git") or {}).get("head"))
                    for entry in (run_identity or {}).get("start") or []})
    return {"rows": {"path": str(rows_path), "sha256": file_sha256(rows_path)},
            "keys": {"path": str(args.keys), "sha256": file_sha256(args.keys),
                     "lines": keys["expected_lines"]},
            "v0": {"path": str(args.v0), "sha256": args.v0_sha256},
            "run_heads": heads}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rows", type=Path, required=True, help="ed7_probe.py output")
    parser.add_argument("--keys", type=Path, required=True, help="probe_keys_ed7.json")
    parser.add_argument("--keys-sha256", default=None)
    parser.add_argument("--v0", type=Path, required=True, help="stored v5 main.jsonl")
    parser.add_argument("--v0-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True, help="report json (new file)")
    parser.add_argument("--require-clean", action="store_true",
                        help="this checkout must be a clean commit (setting_defect else)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.out.exists():
            raise InputError(f"--out {args.out} exists (a report is never overwritten)")
        report = build_report(args)
    except InputError as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}), flush=True)
        return EXIT_STOP
    except Exception:  # every unexpected failure is a tool error (exit 3), never a result
        traceback.print_exc()
        print(json.dumps({"status": "tool_error"}), flush=True)
        return EXIT_TOOL
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, default=str)
    decision, q7c4 = report["decision"], report["q7c4"]["totals"]
    print(json.dumps({"status": report["status"], "readings": len(decision["readings"]),
                      "outcome_kinds": len(decision["outcomes"]),
                      "line_problems": len(report["checks"]["line_problems"]),
                      "missing_jobs": len(report["checks"]["missing_jobs"]),
                      "probe_lines": q7c4.get("lines", 0), "out": str(args.out)}), flush=True)
    return EXIT_DECIDED if report["status"] == "decided" else EXIT_STOP


if __name__ == "__main__":
    sys.exit(main())
