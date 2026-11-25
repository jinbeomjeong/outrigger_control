"""436.9 edition 7 fixed table before the seal (``jp3_remedy_spec_v7.md`` revision 5, P7-9).

Computes, from the probe 6bfb2560 lines of the sealed-configuration arm ``a2``:

* the 40 probe units of the spec 6.2 sensitivity judgement (the four judged settings VBMslow,
  VBMfast, VBMc005, VBMc04 x the ``probe_seen`` keys of ``sens_keys_ed7.json``): one unit
  verdict against V0 each (pass / fail / missing) with the failed item names;
* the 24 D lines of spec 6.3 (the 12 ``d_grid_keys12.json`` keys x VBM, VBMslow): the ③ rev 7
  condition J-P3a breach, FAULT and the V0 comparison (counted on VBM, a record on VBMslow);
* whether the fixed table alone already fails the spec 6.2 cluster rule or the spec 6.3 rule.

Unit verdict of the 40 (spec 6.2 "probe 본 단위" text, the edition 6 ``sens`` judge form of
``jp3_ed6_judge.judge_sens``): the 436.8 path 1 J1 .. J11 items against the stored V0 line of
the same row and phase (``jp3_j9main_judge._full_items``) with

* J7 replaced by the spec 6.1 comparison ``jp3_ed7_rules.j7_items_ed7`` ((name, leg, reason));
* reading (1) (``jp3_ed6_judge.apply_reading_1``), reading (3) (``jp3_ed6_judge.s8_items``;
  no probe key is an S8 line);
* the sensitivity J7 stiffness exception ``jp3_ed7_rules.is_j7_stiffness_exempt``
  (Q7-C4: ``WARN_PROBE_RETRACT_NOT_OPENED`` is never exempt);
* the R15 worsening of erratum 3 3-1 (``jp3_ed6_judge.sens_r15_worsening``): a worse setting
  fails both of its R15 units (the reading of ``ed6_probe_share`` / the adoption tool);
* a unit fails on a ``fail`` or ``stop`` item; a ``not_judgeable`` item or no V0 line is
  ``missing`` (never read as a pass).

Settings keep their own names (the edition 6 ``sens`` judge form: J11 of a sensitivity setting is
a record). The same units labelled ``VB`` (the adoption tool form, J11 a stop) are computed as a
cross-check; a difference is reported, never chosen silently.

D line V0 comparison (spec 6.3 "판 6 6.3 (나) 꼴"): the V0 pair of the edition 6 grid key file
``confirm_b_grid192.json`` (the key file of the edition 6 record part D), its stored V0 grid run
read with ``jp3_ed6_judge.grid_v0_run`` (command hash checked); an opportunity line (V0 pass)
fails when ``event_output.pass`` is not true or (Q7-C4) ``WARN_PROBE_RETRACT_NOT_OPENED`` is new
against the stored V0 run. Other new WARN names are a record (edition 6 6.3 reading).

Minimum force (spec 7 column, definition open; records only): ``values.forces.after_liftoff
.min_kN`` (all legs) and, as the event-leg-excluded reading, the lowest
``event_output.min_F_after_event_kN`` of the legs other than the event leg
(``event_output.pair[0]``) - an after-event value, see :func:`min_force_values`.

Exit 0 = written; 2 = input error (an input of another sha256, an existing output, a missing
line); 3 = tool error. The stdout's last line is JSON with the status, the counts and the paths.

Usage (dynamics-dev ``python.exe -I -B``; the worktree modules are imported read-only):
  python -I -B fixed_table.py --out-dir <this folder>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import traceback
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

REPO = Path(r"C:\workspace\outrigger_control")
WORKTREE = REPO / ".claude" / "worktrees" / "ed7-impl"
CODE_DIR = WORKTREE / "04_scripts" / "04_hydraulic" / "coupled"
for _path in (CODE_DIR, WORKTREE / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import ed7_condition3_adoption as adoption  # noqa: E402
import jp3_ed6_judge as ed6  # noqa: E402
import jp3_ed7_rules as rules  # noqa: E402
import jp3_j9main_judge as j9judge  # noqa: E402
import judge4368_common as common  # noqa: E402
import judge_stage1_4368 as path1  # noqa: E402

EXIT_WRITTEN, EXIT_INPUT, EXIT_TOOL = 0, 2, 3
EXPECTED_HEAD = "b46bdf8f"
CAUSE = REPO / "06_analysis" / "02_control" / "j_p3_cause"
PROBE_DIR = CAUSE / "j9_runs" / "6bfb2560" / "ed7_probe_a1"
INPUTS = {
    "spec": (CAUSE / "jp3_remedy_spec_v7.md",
             "ebb79469875863e8fae3eb0f7acfbdb99c1abbdb66e2c361452a5d88fbe0a36a"),
    "rows": (PROBE_DIR / "ed7_probe.jsonl",
             "1107b30962a038ec9ebccdd19543338f7df771261aa208ef458de6b814817ce9"),
    "probe_keys": (CAUSE / "ed7_design" / "tool_6bfb2560" / "keys" / "probe_keys_ed7.json",
                   "189dbb1315e2267812a1a14724c1cf405c96b70e2f43735ee22da940b28053da"),
    "v0": (REPO / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "main.jsonl",
           "9ad749907c34c9e9efb77579a8ab6e3b1f86cdc32d36162c0029005ca545b29e"),
    "grid_keys": (CAUSE / "ed6_design" / "keys" / "confirm_b_grid192.json",
                  "4e80e69bd2233b994853ae3f60ed0749f2c39c7dbb6390bc012b016efa5cf85b"),
    "sens_keys": (CAUSE / "ed7_design" / "tool_6bfb2560" / "keys" / "sens_keys_ed7.json", None),
    "condition": (PROBE_DIR / "condition_ad7a716e.json", None),
    "run_identity": (PROBE_DIR / "ed7_probe.identity.json", None),
}
"""Name -> (path, pinned sha256 or None = recorded only)."""
ARM = "a2"
SENS_PLANTS = {"VBMslow": "Mslow", "VBMfast": "Mfast", "VBMc005": "Mc005", "VBMc04": "Mc04"}
D_PLANTS = {"VBM": "M", "VBMslow": "Mslow"}
D_COUNTED_SETTING = "VBM"
EXPECTED_SENS_UNITS = 40
EXPECTED_D_LINES = 24
CROSS_CHECK_LABEL = "VB"
VERDICT_PASS, VERDICT_FAIL, VERDICT_MISSING = "pass", "fail", "missing"
FAILING_KINDS = ("fail", "stop")
R15_ROW = "R15"
R15_ITEM = "R15 worsening (J2, erratum 3 3-1)"
LEGS = ("FL", "FR", "RL", "RR")
OUTPUT_NAMES = ("fixed_table_a2.json", "fixed_table_a2.csv", "manifest.json")


class InputError(Exception):
    """No output is written (exit 2)."""


# ------------------------------------------------------------------------------ inputs
def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_inputs() -> dict[str, dict]:
    """Every input's path and sha256; a pinned sha256 that differs is an input error."""
    found = {}
    for name, (path, pinned) in INPUTS.items():
        if not path.is_file():
            raise InputError(f"input {name} {path} not found")
        digest = file_sha256(path)
        if pinned is not None and digest != pinned:
            raise InputError(f"input {name} {path.name}: sha256 {digest} != pinned {pinned}")
        found[name] = {"path": str(path), "sha256": digest, "pinned": pinned is not None}
    return found


def worktree_identity() -> dict:
    """The imported code checkout: HEAD and cleanliness (a git failure kept apart)."""
    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(WORKTREE), *args], capture_output=True,
                              text=True, timeout=60, check=False)

    head, status = git("rev-parse", "HEAD"), git("status", "--porcelain")
    if head.returncode or status.returncode or not head.stdout.strip():
        raise InputError(f"git failed on the worktree: {(head.stderr or status.stderr)[:300]}")
    identity = {"checkout": str(WORKTREE), "head": head.stdout.strip(),
                "is_clean": not status.stdout.strip()}
    if not identity["head"].startswith(EXPECTED_HEAD) or not identity["is_clean"]:
        raise InputError(f"worktree is not a clean {EXPECTED_HEAD}: {identity}")
    return identity


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------ line selection
@dataclass(frozen=True)
class Wanted:
    """One planned probe line of the fixed table."""

    scope: str
    setting: str
    plant: str
    key: str


def wanted_lines(probe_keys: dict, sens_keys: dict) -> dict[str, Wanted]:
    """Job identity -> the 40 sensitivity units and the 24 D lines (arm a2).

    Raises:
        InputError: A count other than the spec's.
    """
    seen_keys: dict[str, set[str]] = defaultdict(set)
    for line in sens_keys["lines"]:
        setting = line["job"]["setting"]
        if setting in SENS_PLANTS and line["probe_seen"] and line["judged"]:
            seen_keys[setting].add(line["key"])
    plant_to_setting = {plant: setting for setting, plant in SENS_PLANTS.items()}
    d_plant_to_setting = {plant: setting for setting, plant in D_PLANTS.items()}
    wanted = {}
    for line in probe_keys["lines"]:
        _, plant, arm = line["job"]["setting"].split("-")
        if arm != ARM:
            continue
        if line["part"] == "main" and plant in plant_to_setting:
            setting = plant_to_setting[plant]
            if line["key"] in seen_keys[setting]:
                wanted[adoption.job_identity(line["job"])] = Wanted("sens40", setting, plant,
                                                                     line["key"])
        elif line["part"] == "d" and plant in d_plant_to_setting:
            wanted[adoption.job_identity(line["job"])] = Wanted(
                "d24", d_plant_to_setting[plant], plant, line["key"])
    sens = sum(entry.scope == "sens40" for entry in wanted.values())
    d_lines = sum(entry.scope == "d24" for entry in wanted.values())
    if (sens, d_lines) != (EXPECTED_SENS_UNITS, EXPECTED_D_LINES):
        raise InputError(f"planned lines: {sens} sensitivity units / {d_lines} D lines, expected "
                         f"{EXPECTED_SENS_UNITS} / {EXPECTED_D_LINES}")
    return wanted


def read_wanted_records(rows_path: Path, wanted: dict[str, Wanted]) -> dict[str, dict]:
    """Stream the probe file once and keep the wanted lines (job identity -> record).

    Raises:
        InputError: A wanted line missing, repeated or an error line.
    """
    records: dict[str, dict] = {}
    with rows_path.open(encoding="utf-8") as handle:
        for text in handle:
            if not text.strip():
                continue
            record = json.loads(text)
            identity = adoption.job_identity(record["job"])
            if identity not in wanted:
                continue
            if "error" in record or identity in records:
                raise InputError(f"wanted line {wanted[identity].key}: error or repeated")
            records[identity] = record
    missing = [wanted[identity].key for identity in wanted if identity not in records]
    if missing:
        raise InputError(f"{len(missing)} wanted lines missing: {missing[:5]}")
    return records


# ------------------------------------------------------------------------------ 6.2 units
def v0_metric_rows(v0_path: Path, v0_sha256: str) -> list[dict]:
    rows = j9judge.stored_v0_rows(v0_path, v0_sha256)
    folders = tuple(common.t4h_folders(v0_path, rows))
    return ed6.metric_rows(rows, folders, {})


def unit_metrics(records: dict[str, dict], wanted: dict[str, Wanted], t4h_dir: Path,
                 label_of) -> dict[str, dict]:
    """Path 1 metrics of the 40 unit lines, settings labelled by ``label_of(entry)``."""
    out = {}
    for identity, entry in wanted.items():
        if entry.scope != "sens40":
            continue
        metric = path1.metrics(records[identity], (t4h_dir,))
        metric["setting"] = label_of(entry)
        metric["soil_stop_crawler"] = records[identity].get("soil_stop_crawler")
        metric["unit_identity"] = identity
        out[identity] = metric
    return out


def replace_j7(table: dict, rows_by: dict) -> None:
    """Spec 6.1: the J7 items of every setting become ``j7_items_ed7`` against the V0 line."""
    base = {(row["row"], row["phase"]): row for row in rows_by.get(j9judge.V0_SETTING, [])}
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows_by.get(j9judge.V0_SETTING, []):
        groups[row["group"]].append(row)
    for setting, part in table.items():
        items = [item for item in part["items"] if item["item"] != "J7"]
        for row in rows_by.get(setting, []):
            reference = base.get((row["row"], row["phase"]))
            if reference is None:
                continue
            items += [{"row": row["row"], "phase": row["phase"], **item}
                      for item in rules.j7_items_ed7(reference, row, groups[row["group"]])]
        part["items"] = items


def apply_stiffness_exception(table: dict) -> list[dict]:
    """Spec 6.2 single condition (``rules.is_j7_stiffness_exempt``), in place, per unit."""
    exempted = []
    for setting, part in table.items():
        by_unit: dict[tuple, list[dict]] = defaultdict(list)
        for item in part["items"]:
            if item["item"] == "J7" and item["kind"] == "fail":
                by_unit[(item["row"], item["phase"])].append(item)
        for (row, phase), items in by_unit.items():
            if not rules.is_j7_stiffness_exempt([item["detail"] for item in items]):
                continue
            for item in items:
                item["kind"] = "record"
                item["j7_exempt"] = True
            exempted.append({"setting": setting, "row": row, "phase": phase,
                             "names": sorted({item["detail"] for item in items})})
    return exempted


def unit_table(metrics: dict[str, dict], v0_rows: list[dict]) -> dict:
    """The judged items of every unit (module docstring)."""
    rows_by = path1._by_setting(list(metrics.values()) + v0_rows)
    settings = tuple(sorted({metric["setting"] for metric in metrics.values()}))
    table = j9judge._full_items(rows_by, settings, j9judge.V0_SETTING)
    replace_j7(table, rows_by)
    moved = ed6.apply_reading_1(table, rows_by, j9judge.V0_SETTING)
    exempted = apply_stiffness_exception(table)
    s8 = ed6.s8_items(rows_by, settings)
    r15 = ed6.sens_r15_worsening(rows_by, settings)
    return {"table": table, "reading_1_moved": moved, "j7_exempt": exempted, "S8": s8,
            "r15": r15, "rows_by": rows_by}


def unit_verdicts(metrics: dict[str, dict], judged: dict) -> dict[str, dict]:
    """Identity -> verdict, failed items, not-judgeable items and record items of a unit."""
    by_unit: dict[tuple, list[dict]] = defaultdict(list)
    for setting, part in judged["table"].items():
        for item in part["items"]:
            by_unit[(setting, item["row"], str(item["phase"]))].append(item)
    s8_entries = judged["S8"]["failures"] + judged["S8"]["stops"] + judged["S8"]["not_judgeable"]
    for entry in s8_entries:
        by_unit[(entry["setting"], entry["row"], str(entry["phase"]))].append(entry)
    no_reference = {(setting, row, str(phase)) for setting, part in judged["table"].items()
                    for row, phase in part["no_reference"]}
    out = {}
    for identity, metric in metrics.items():
        unit = (metric["setting"], metric["row"], str(metric["phase"]))
        items = by_unit.get(unit, [])
        failed = [_item_text(item) for item in items if item["kind"] in FAILING_KINDS]
        unjudged = [_item_text(item) for item in items if item["kind"] == "not_judgeable"]
        if unit in no_reference:
            unjudged.append("no V0 line of the same row and phase")
        _add_r15(judged["r15"], metric, failed, unjudged)
        records = [_item_text(item) for item in items
                   if item["kind"] not in (*FAILING_KINDS, "not_judgeable")]
        verdict = (VERDICT_FAIL if failed else VERDICT_MISSING if unjudged else VERDICT_PASS)
        out[identity] = {"verdict": verdict, "failed_items": failed,
                         "not_judgeable_items": unjudged, "record_items": records}
    return out


def _item_text(item: dict) -> str:
    detail = item.get("detail")
    if isinstance(detail, list):
        detail = ",".join(map(str, detail))
    text = f"{item['item']} {item['kind']}: {detail}"
    return text + (" (stiffness exempt)" if item.get("j7_exempt") else "")


def _add_r15(r15: dict, metric: dict, failed: list[str], unjudged: list[str]) -> None:
    """Erratum 3 3-1 on a unit of the R15 row (both phases of a worse setting fail)."""
    if metric["row"] != R15_ROW:
        return
    entry = r15.get(metric["setting"]) or {"state": "판정 불가", "worse": False,
                                           "reason": "no R15 worsening entry"}
    if entry["worse"]:
        failed.append(f"{R15_ITEM}: S {entry['S_N']:.1f} N, E {entry['E_N']:.1f} N")
    elif entry["state"] == "판정 불가":
        unjudged.append(f"{R15_ITEM}: {entry.get('reason')}")


# ------------------------------------------------------------------------------ D lines
def grid_pairs(grid_keys: dict) -> dict[str, dict]:
    """Job (without its setting) -> V0 pair of the edition 6 grid key file."""
    return {_job_without_setting(line["job"]): line["v0_pair"] for line in grid_keys["lines"]}


def _job_without_setting(job: dict) -> str:
    return json.dumps({k: v for k, v in job.items()
                       if k not in ("setting", *adoption.RUNTIME_JOB_FIELDS)}, sort_keys=True)


def d_line_values(record: dict, entry: Wanted, pairs: dict[str, dict],
                  condition: dict[tuple, dict]) -> dict:
    """J-P3a, FAULT and the V0 comparison of one D line."""
    pair = pairs.get(_job_without_setting(record["job"]))
    v0 = _d_v0_comparison(record, pair)
    missing_keys = ed6.missing_keys(record, ed6.GRID_REQUIRED_KEYS)
    fault = (None if missing_keys else ed6.fault_reasons(record))
    cond = condition.get((record["job"]["setting"], record["t4h_file"])) or {}
    check = (record.get("hydraulics_record") or {}).get("extend_bound_check") or {}
    return {**v0, "fault_reasons": fault, "fault_missing_keys": missing_keys,
            "condition_state": cond.get("state"),
            "condition_reads": cond.get("condition_reads"),
            "condition_breach_reads": cond.get("condition_breach_reads"),
            "line_jp3a_breach_reads": _leg_sum(check.get("jp3a_breach_reads")),
            "line_jp3b_breach_reads": _leg_sum(check.get("jp3b_breach_reads")),
            "line_jp3c_breach_reads": _leg_sum(check.get("jp3c_breach_reads")),
            "is_counted_for_k": entry.setting == D_COUNTED_SETTING}


def _leg_sum(values) -> int | None:
    """The four-leg sum; None when the list is missing or not four integers (never 0)."""
    if not isinstance(values, list) or len(values) != len(LEGS):
        return None
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        return None
    return sum(values)


def _d_v0_comparison(record: dict, pair: dict | None) -> dict:
    if pair is None:
        return {"v0_verdict": VERDICT_MISSING, "v0_reason": "no V0 pair in the grid key file"}
    try:
        stored = ed6.grid_v0_run(REPO, pair)
    except ed6.NotJudgeable as exc:
        return {"v0_verdict": VERDICT_MISSING, "v0_reason": str(exc), "v0_pair": pair}
    event = record.get("event_output")
    if not isinstance(event, dict) or "pass" not in event:
        return {"v0_verdict": VERDICT_MISSING, "v0_reason": "no event_output.pass",
                "v0_pair": pair}
    is_opportunity = bool(pair["v0_pass"])
    failed_gates = sorted(name for name, ok in (event.get("gates") or {}).items() if ok is False)
    stored_names = {ed6._first_token(str(w)) for w in stored.get("warnings") or []}
    new_warnings = sorted({ed6._first_token(str(w)) for w in event.get("warnings") or []}
                          - stored_names)
    # Q7-C4 (spec 6.1): a retract WARN new against V0 is a J7 failure in the confirmation
    # stage too; the line's event list is read as well as event_output.warnings
    line_names = {ed6._first_token(str(name)) for _, name in record.get("events") or []}
    retract_new = (rules.RETRACT_NOT_OPENED_WARNING in (line_names | set(new_warnings))
                   and rules.RETRACT_NOT_OPENED_WARNING not in stored_names)
    is_failed = is_opportunity and (event["pass"] is not True or retract_new)
    return {"v0_verdict": VERDICT_FAIL if is_failed else VERDICT_PASS,
            "v0_opportunity": is_opportunity, "v0_pass_key_file": pair["v0_pass"],
            "v0_pass_stored": stored.get("pass"), "event_output_pass": event["pass"],
            "failed_gates": failed_gates, "retract_warn_new_q7c4": retract_new,
            "new_warn_names_record": new_warnings, "v0_pair": pair}


# ------------------------------------------------------------------------------ minimum force
def event_leg(record: dict) -> str | None:
    """``event_output.pair[0]`` (the event leg, then its diagonal partner); None for a line
    without an event output."""
    pair = (record.get("event_output") or {}).get("pair")
    if isinstance(pair, list) and pair:
        return str(pair[0])
    return None


def min_force_values(record: dict) -> dict:
    """The two minimum force readings of the spec 7 column (records, module docstring).

    The after-liftoff value is one number over all legs (no per-leg after-liftoff minimum is
    recorded, and the T4h ``true_force_*`` arrays are the limiter oil force, not the true
    force), so the event-leg-excluded value is read after the event:
    ``event_output.min_F_after_event_kN`` over the legs other than the event leg.
    """
    forces = (record.get("values") or {}).get("forces") or {}
    after = forces.get("after_liftoff") or {}
    leg = event_leg(record)
    twin_leg = (record["job"].get("twin") or {}).get("leg")
    out = {"min_force_all_legs_kN": after.get("min_kN"), "min_force_leg": after.get("leg"),
           "event_leg": leg, "event_leg_matches_twin": None if twin_leg is None or leg is None
           else leg == twin_leg,
           "min_force_after_event_excl_event_leg_kN": None,
           "min_force_after_event_excl_event_leg_leg": None}
    per_leg = (record.get("event_output") or {}).get("min_F_after_event_kN")
    if leg is None or not isinstance(per_leg, dict) or sorted(per_leg) != sorted(LEGS):
        out["min_force_note"] = "no event leg or no per-leg after-event minimum: not applicable"
        return out
    others = {name: value for name, value in per_leg.items() if name != leg}
    if any(value is None for value in others.values()):
        out["min_force_note"] = "a per-leg after-event minimum is None"
        return out
    lowest = min(others, key=others.get)
    out["min_force_after_event_excl_event_leg_kN"] = others[lowest]
    out["min_force_after_event_excl_event_leg_leg"] = lowest
    return out


# ------------------------------------------------------------------------------ rule checks
def cluster_rule_from_fixed(units: list[dict]) -> dict:
    """Spec 6.2 cluster rule on the fixed table alone, with the missing units read both ways."""
    def evaluate(treat_missing_as_fail: bool) -> dict:
        failed_phases: dict[tuple, list[str]] = defaultdict(list)
        for unit in units:
            is_failed = unit["verdict"] == VERDICT_FAIL or (
                treat_missing_as_fail and unit["verdict"] == VERDICT_MISSING)
            if is_failed:
                failed_phases[(unit["setting"], unit["row"])].append(unit["phase"])
        multi = sorted(f"{s} {r}: {p}" for (s, r), p in failed_phases.items() if len(p) >= 2)
        single = sorted(f"{s} {r}: {p[0]}" for (s, r), p in failed_phases.items()
                        if len(p) == 1)
        return {"multi_phase_clusters": multi, "single_phase_clusters": single,
                "single_count_4_settings": len(single), "k": rules.SENSITIVITY_CLUSTER_K,
                "is_failed": bool(multi) or len(single) > rules.SENSITIVITY_CLUSTER_K}

    as_pass, as_fail = evaluate(False), evaluate(True)
    missing = [f"{u['setting']} {u['key']}" for u in units if u["verdict"] == VERDICT_MISSING]
    if as_pass["is_failed"]:
        determined = "fail"
    elif not missing:
        determined = "not_failed"
    else:
        determined = "undetermined (missing units)" if as_fail["is_failed"] else "not_failed"
    return {"rule": "spec 6.2: a (setting, row) with >= 2 failed phases, or more than k = 4 "
                    "single-phase (setting, row) over the four judged settings",
            "missing_units": missing, "missing_as_pass": as_pass, "missing_as_fail": as_fail,
            "fixed_table_alone": determined}


def confirmation_rule_from_fixed(d_rows: list[dict]) -> dict:
    """Spec 6.3: D VBM opportunity failures alone over k = 3, or a J-P3a breach / FAULT on the
    24 lines; a missing value is listed and keeps the result undetermined unless it fails."""
    counted = [row for row in d_rows if row["is_counted_for_k"]]
    fails = [row["key"] for row in counted if row["v0_verdict"] == VERDICT_FAIL]
    v0_missing = [row["key"] for row in counted if row["v0_verdict"] == VERDICT_MISSING]
    breach = [f"{row['setting']} {row['key']}" for row in d_rows
              if (row["condition_breach_reads"] or 0) > 0]
    breach_missing = [f"{row['setting']} {row['key']}" for row in d_rows
                      if row["condition_breach_reads"] is None]
    faults = [f"{row['setting']} {row['key']}" for row in d_rows if row["fault_reasons"]]
    fault_missing = [f"{row['setting']} {row['key']}" for row in d_rows
                     if row["fault_reasons"] is None]
    is_failed = len(fails) > rules.CONFIRMATION_K or bool(breach) or bool(faults)
    has_missing = bool(v0_missing or breach_missing or fault_missing)
    can_still_fail = len(fails) + len(v0_missing) > rules.CONFIRMATION_K
    if is_failed:
        determined = "fail"
    elif has_missing and (can_still_fail or breach_missing or fault_missing):
        determined = "undetermined (missing values)"
    else:
        determined = "not_failed"
    return {"rule": "spec 6.3: D VBM opportunity failures alone > k = 3, or J-P3a breach (③ rev 7 "
                    "condition reads) > 0, or FAULT > 0 on the 24 lines",
            "vbm_opportunities": sum(bool(row.get("v0_opportunity")) for row in counted),
            "vbm_opportunity_failures": fails, "d_fixed_failures_d": len(fails),
            "vbm_v0_missing": v0_missing, "k": rules.CONFIRMATION_K,
            "condition_breach_lines": breach, "condition_breach_missing": breach_missing,
            "fault_lines": faults, "fault_missing": fault_missing,
            "line_jp3a_breach_lines": [f"{r['setting']} {r['key']}" for r in d_rows
                                       if (r["line_jp3a_breach_reads"] or 0) > 0],
            "fixed_table_alone": determined}


# ------------------------------------------------------------------------------ assembly
def phase_of(job: dict) -> str:
    """The phase inside a row (spec 6.2): the offset of an event job, else the eps."""
    if "offset_s" in job:
        return f"o{float(job['offset_s']):g}"
    return f"e{float(job.get('eps', 0.0)):g}"


def build(inputs: dict) -> dict:
    probe_keys = read_json(INPUTS["probe_keys"][0])
    sens_keys = read_json(INPUTS["sens_keys"][0])
    wanted = wanted_lines(probe_keys, sens_keys)
    records = read_wanted_records(INPUTS["rows"][0], wanted)
    t4h_dir = PROBE_DIR / "ed7_probe_t4h"
    v0_rows = v0_metric_rows(INPUTS["v0"][0], INPUTS["v0"][1])

    metrics = unit_metrics(records, wanted, t4h_dir, lambda entry: entry.setting)
    judged = unit_table(metrics, v0_rows)
    verdicts = unit_verdicts(metrics, judged)
    cross = unit_cross_check(records, wanted, t4h_dir, v0_rows, verdicts)

    condition_doc = read_json(INPUTS["condition"][0])
    condition = {(line["setting"], line["t4h_file"]): line for line in condition_doc["lines"]}
    pairs = grid_pairs(read_json(INPUTS["grid_keys"][0]))
    identity_problems = line_identity_problems(records, wanted, probe_keys)

    units, d_rows = [], []
    for identity, entry in sorted(wanted.items(), key=lambda item: (item[1].scope,
                                                                    item[1].setting,
                                                                    item[1].key)):
        record = records[identity]
        common_row = {"scope": entry.scope, "setting": entry.setting, "plant": entry.plant,
                      "key": entry.key, "row": rules.row_key(record["job"]),
                      "phase": phase_of(record["job"]), "t4h_file": record["t4h_file"],
                      "commands_sha256": record.get("commands_sha256"),
                      "final_phase": record.get("final_phase"),
                      **min_force_values(record)}
        if entry.scope == "sens40":
            units.append({**common_row, **verdicts[identity]})
        else:
            d_rows.append({**common_row, **d_line_values(record, entry, pairs, condition)})
    return {"rule": "jp3_remedy_spec_v7.md revision 5 P7-9 (6.2 probe units, 6.3 D lines); "
                    "Q7-C4 decided (WARN_PROBE_RETRACT_NOT_OPENED not exempt)",
            "arm": ARM, "inputs": inputs,
            "checks": {"line_identity_problems": identity_problems,
                       "run_identity_problems": adoption.run_identity_problems(
                           read_json(INPUTS["run_identity"][0])),
                       "unit_label_cross_check": cross},
            "sens40_units": units, "d24_lines": d_rows,
            "reading_1_moved": judged["reading_1_moved"],
            "j7_stiffness_exempt": judged["j7_exempt"], "r15_worsening": judged["r15"],
            "rule_6_2_fixed_table": cluster_rule_from_fixed(units),
            "rule_6_3_fixed_table": confirmation_rule_from_fixed(d_rows)}


def unit_cross_check(records: dict, wanted: dict, t4h_dir: Path, v0_rows: list[dict],
                     verdicts: dict) -> dict:
    """The 40 units labelled ``VB`` (adoption tool form): verdicts that differ."""
    metrics = unit_metrics(records, wanted, t4h_dir, lambda entry: CROSS_CHECK_LABEL)
    by_setting: dict[str, dict] = defaultdict(dict)
    for identity, metric in metrics.items():
        by_setting[wanted[identity].setting][identity] = metric
    differences = []
    for setting_metrics in by_setting.values():
        other = unit_verdicts(setting_metrics, unit_table(setting_metrics, v0_rows))
        for identity, verdict in other.items():
            if verdict["verdict"] != verdicts[identity]["verdict"]:
                entry = wanted[identity]
                differences.append({"setting": entry.setting, "key": entry.key,
                                    "own_label": verdicts[identity]["verdict"],
                                    "vb_label": verdict["verdict"],
                                    "vb_label_items": verdict["failed_items"]})
    return {"label": CROSS_CHECK_LABEL, "units": len(metrics), "differences": differences}


def line_identity_problems(records: dict, wanted: dict, probe_keys: dict) -> dict:
    """``ed7_condition3_adoption.line_problems`` (tag, components, condition, options, blind
    record) of every fixed-table line."""
    problems = {}
    for identity, entry in wanted.items():
        record = records[identity]
        part = "main" if entry.scope == "sens40" else "d"
        planned = adoption.PlannedLine(entry.plant, ARM, entry.key, part)
        found = adoption.line_problems(record, planned, probe_keys, adoption.expected_options)
        if found:
            problems[f"{entry.setting} {entry.key}"] = found
    return problems


# ------------------------------------------------------------------------------ output
CSV_COLUMNS = ("scope", "setting", "plant", "key", "row", "phase", "verdict", "failed_items",
               "not_judgeable_items", "record_items", "v0_verdict", "v0_opportunity",
               "event_output_pass", "failed_gates", "is_counted_for_k", "fault_reasons",
               "condition_state", "condition_reads", "condition_breach_reads",
               "line_jp3a_breach_reads", "retract_warn_new_q7c4", "new_warn_names_record",
               "min_force_all_legs_kN", "min_force_leg", "event_leg",
               "min_force_after_event_excl_event_leg_kN",
               "min_force_after_event_excl_event_leg_leg", "final_phase", "commands_sha256",
               "t4h_file")


def csv_text(table: dict) -> str:
    lines = [",".join(CSV_COLUMNS)]
    for row in table["sens40_units"] + table["d24_lines"]:
        lines.append(",".join(_csv_cell(row.get(column)) for column in CSV_COLUMNS))
    return "\n".join(lines) + "\n"


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = " | ".join(map(str, value))
    text = str(value)
    if any(char in text for char in ',"\n'):
        text = '"' + text.replace('"', '""') + '"'
    return text


def write_new(path: Path, text: str) -> str:
    data = text.encode("utf-8")
    with path.open("xb") as handle:
        handle.write(data)
    return hashlib.sha256(data).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if any((args.out_dir / name).exists() for name in OUTPUT_NAMES):
            raise InputError("an output exists (never overwritten)")
        code = worktree_identity()
        inputs = checked_inputs()
        table = build(inputs)
        table["code_identity"] = code
    except InputError as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}))
        return EXIT_INPUT
    except Exception:  # every unexpected failure is a tool error (exit 3), never a result
        traceback.print_exc()
        print(json.dumps({"status": "tool_error"}))
        return EXIT_TOOL
    shas = {"fixed_table_a2.json": write_new(args.out_dir / "fixed_table_a2.json",
                                             json.dumps(table, indent=1, default=str) + "\n"),
            "fixed_table_a2.csv": write_new(args.out_dir / "fixed_table_a2.csv",
                                            csv_text(table))}
    manifest = {"script": {"path": str(Path(__file__).resolve()),
                           "sha256": file_sha256(Path(__file__).resolve())},
                "command": (r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B "
                            f"{Path(__file__).resolve()} --out-dir {args.out_dir}"),
                "python": sys.version, "code_identity": table["code_identity"],
                "inputs": table["inputs"], "outputs": shas}
    write_new(args.out_dir / "manifest.json", json.dumps(manifest, indent=1) + "\n")
    print(json.dumps({"status": "written", "units": len(table["sens40_units"]),
                      "d_lines": len(table["d24_lines"]),
                      "rule_6_2": table["rule_6_2_fixed_table"]["fixed_table_alone"],
                      "rule_6_3": table["rule_6_3_fixed_table"]["fixed_table_alone"],
                      "out": str(args.out_dir)}))
    return EXIT_WRITTEN


if __name__ == "__main__":
    sys.exit(main())
