"""436.9 edition 7 probe share decision (``jp3_remedy_spec_v7.md`` 4 step 2, 526).

Pre-seal design input (public, not a judgement). Spec text, 4 step 2: "몫 판단 규칙: 판 6
4절 2와 같다(동률이면 남김, 발동 0일 때만 뺌)". Edition 6 4 step 2 (``jp3_remedy_spec_v6.md``
335~340, 375): a component X is dropped only when (a) X acted 0 times in the probe, or (b) the
arm without X has fewer failed units against V0 than the full arm; ties keep X. B3 exception:
B3 is dropped only when the arm without B3 fails at least 2 units fewer (activation 0: (a)).

Edition 7 arms (``ed7_probe.ARMS`` at b46bdf8f): full arm ``a2`` = {A_i, A_ib, A_ii, B3};
``a5`` = a2 - B3; ``a6`` = a2 - A(i) (its edition 6 trigger); ``a1`` = {A_i, A_ii, B3}
(= a2 - A_ib by components; spec arm 1 "판 6 봉인"). A_ii has no arm without it.

Failure units: (plant, key) of the main part, against the stored V0 (sha below), computed with
the b46bdf8f condition 3 adoption tool functions (``ed7_condition3_adoption``:
``line_metric``, ``group_judgement``, ``failed_units``) under its ``FIXED_READING`` (J7
``ed7_new``, sensitivity stiffness exception, VBM 5 plants). Record only: the same under the
edition 6 share tool's reading (J7 ``ed6_share``, no exception, all 6 plants).

Activation (record keys of ``lsb_record``, never read as 0 when missing): A_i
``legs.*.a1_raised_periods`` (edition 6 tool key), A_ii ``legs.*.a2_raised_periods``, B3
``legs.*.b3_periods``, A_ib ``blind.legs.*.raised_periods``; also the triggers.

The worktree code is imported read-only from ``--checkout`` (must be b46bdf8f and clean before
and after; ``git status --porcelain --ignored`` is compared). In this process only, the adoption
module's ``EXPECTED_CONDITION`` is extended with a1 (None), a5 and a6 (``with_twist``) so its
``line_problems`` checks the extra arms; for a1 the blind record is expected absent.

======  =================  =======================================================
exit    status             meaning
======  =================  =======================================================
0       ``decided``        outputs written, every check clean
2       ``setting_defect`` outputs written; a line or checkout check failed
2       ``incomplete``     outputs written; a planned job missing or repeated
2       ``not_judgeable``  outputs written; a compared group cannot be compared
2       ``input_error``    no output: input sha differs, or an output exists
3       ``tool_error``     an unexpected failure
======  =================  =======================================================

Usage (dynamics-dev, ``MKL_THREADING_LAYER=TBB``):
  python -I -B share_calc.py --checkout <ed7-impl worktree> --out-dir <this folder>
The stdout's last line is JSON with ``status`` and the output paths.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

EXIT_DECIDED, EXIT_STOP, EXIT_TOOL = 0, 2, 3
EXPECTED_HEAD = "b46bdf8fdbad730eabf9226c5e1cfed0e980b5e9"
PROJECT = Path(r"C:\workspace\outrigger_control")
PROBE_DIR = PROJECT / "06_analysis/02_control/j_p3_cause/j9_runs/6bfb2560/ed7_probe_a1"
ROWS_PATH = PROBE_DIR / "ed7_probe.jsonl"
ROWS_SHA256 = "1107b30962a038ec9ebccdd19543338f7df771261aa208ef458de6b814817ce9"
KEYS_PATH = PROJECT / "06_analysis/02_control/j_p3_cause/ed7_design/tool_6bfb2560/keys/probe_keys_ed7.json"
KEYS_SHA256 = "189dbb1315e2267812a1a14724c1cf405c96b70e2f43735ee22da940b28053da"
V0_PATH = PROJECT / "06_analysis/03_hydraulic/coupled/v5/main.jsonl"
V0_SHA256 = "9ad749907c34c9e9efb77579a8ab6e3b1f86cdc32d36162c0029005ca545b29e"
SPEC_PATH = PROJECT / "06_analysis/02_control/j_p3_cause/jp3_remedy_spec_v7.md"
SPEC_V6_PATH = PROJECT / "06_analysis/02_control/j_p3_cause/jp3_remedy_spec_v6.md"

FULL_ARM = "a2"
SHARE_ARMS = ("a1", "a2", "a5", "a6")
ARM_WITHOUT = {"A_i": "a6", "A_ib": "a1", "A_ii": None, "B3": "a5"}
"""The full arm without the component (``ed7_probe.ARMS``); A_ii has none."""
COMPONENTS = ("A_i", "A_ib", "A_ii", "B3")
B3_DROP_MARGIN = 2
"""Edition 6 4 step 2 B3 exception (stats s30): drop only at 2 or more units fewer."""
DEADBAND_PLANT = "Mc04"
"""Edition 6 tool extra A(i) keep rule plant (``c04``) in edition 7 plant names."""
EXTRA_CONDITION = {"a1": None, "a5": "with_twist", "a6": "with_twist"}
LEG_ACTIVATION_KEYS = {"A_i": ("a1_raised_periods", "a1_triggers"),
                       "A_ii": ("a2_raised_periods", "a2_floors"),
                       "B3": ("b3_periods",)}
BLIND_ACTIVATION_KEYS = ("raised_periods", "triggers")
PRIMARY_KEY = {"A_i": "a1_raised_periods", "A_ii": "a2_raised_periods",
               "B3": "b3_periods", "A_ib": "ib_raised_periods"}
BLIND_MISSING = "lsb_record.blind block missing or incomplete"


class InputError(Exception):
    """No output can be written (exit 2)."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_state(checkout: Path) -> dict:
    """HEAD, porcelain status (with ignored files) of the checkout; a git failure is kept."""
    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(checkout), *args], capture_output=True,
                              text=True, timeout=120, check=False)

    try:
        head = git("rev-parse", "HEAD")
        status = git("status", "--porcelain")
        ignored = git("status", "--porcelain", "--ignored")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"head": None, "is_clean": None, "git_error": str(exc)}
    if head.returncode or status.returncode or ignored.returncode:
        return {"head": None, "is_clean": None,
                "git_error": (head.stderr or status.stderr or ignored.stderr)[:300]}
    return {"head": head.stdout.strip(), "is_clean": not status.stdout.strip(),
            "status_ignored_sha256": hashlib.sha256(ignored.stdout.encode()).hexdigest(),
            "status_ignored_lines": len(ignored.stdout.splitlines())}


# ------------------------------------------------------------------------------ activation
def line_activation(record: dict) -> dict | None:
    """Run totals of the activation keys of one line (None: a key missing)."""
    block = record.get("lsb_record") or {}
    legs = block.get("legs")
    if not isinstance(legs, dict) or len(legs) != 4:
        return None
    totals: dict = {}
    for keys in LEG_ACTIVATION_KEYS.values():
        for key in keys:
            if any(key not in counts for counts in legs.values()):
                return None
            totals[key] = sum(int(counts[key]) for counts in legs.values())
    blind = block.get("blind")
    if blind is None:
        totals.update(ib_raised_periods=None, ib_triggers=None, ib_shots=None)
        return totals
    blind_legs = blind.get("legs") or {}
    if len(blind_legs) != 4 or any(key not in counts for counts in blind_legs.values()
                                   for key in BLIND_ACTIVATION_KEYS):
        return None
    totals["ib_raised_periods"] = sum(int(c["raised_periods"]) for c in blind_legs.values())
    totals["ib_triggers"] = sum(int(c["triggers"]) for c in blind_legs.values())
    totals["ib_shots"] = len(blind.get("shots") or [])
    return totals


# ------------------------------------------------------------------------------ scan
def scan_probe(adoption, share6, planned: dict, keys: dict) -> dict:
    """One streaming pass: line checks, metrics and twist of the share arms, activation and
    stall signature of every line."""
    import numpy as np

    t4h_dir = ROWS_PATH.with_name(f"{ROWS_PATH.stem}_t4h")
    found: Counter = Counter()
    out = {"metrics": {}, "twist": defaultdict(list), "line_problems": {},
           "activation_rows": [], "errors": [], "unplanned": []}
    with ROWS_PATH.open(encoding="utf-8") as handle:
        for text in handle:
            if not text.strip():
                continue
            record = json.loads(text)
            if "error" in record:
                out["errors"].append(record["job"])
                continue
            identity = adoption.job_identity(record["job"])
            entry = planned.get(identity)
            if entry is None:
                out["unplanned"].append(record["job"])
                continue
            found[identity] += 1
            activation = line_activation(record)
            with np.load(t4h_dir / record["t4h_file"], allow_pickle=False) as data:
                stall = share6.is_stall_signature(data)
            out["activation_rows"].append({"plant": entry.plant, "arm": entry.arm,
                                           "part": entry.part, "key": entry.key,
                                           "activation_missing": activation is None,
                                           "stall_signature_ed6": stall,
                                           **(activation or {})})
            if entry.part != adoption.MAIN_PART or entry.arm not in SHARE_ARMS:
                continue
            problems = adoption.line_problems(record, entry, keys, adoption.expected_options)
            if entry.arm == "a1":
                problems = [p for p in problems if p != BLIND_MISSING]
                if (record.get("lsb_record") or {}).get("blind") is not None:
                    problems.append("a1 line has a blind record")
            if problems:
                out["line_problems"][f"{record['job']['setting']} {entry.key}"] = problems
            twist = adoption.twist_record(record)
            if twist is not None:
                out["twist"][(entry.plant, entry.arm)].append(twist)
            metric = adoption.line_metric(record, t4h_dir)
            out["metrics"].setdefault((entry.plant, entry.arm), {})[entry.key] = metric
    out["missing"] = [planned[i].key + " " + i for i in planned if found[i] == 0]
    out["repeated"] = [i for i, count in found.items() if count > 1]
    return out


# ------------------------------------------------------------------------------ units
def arm_units(adoption, groups: dict, reading) -> tuple[dict, list[str]]:
    """Failed (plant, key) units of every share arm under a reading and the problems."""
    plants = adoption.PLANT_SETS[reading.plants]
    problems, units = [], {}
    for arm in SHARE_ARMS:
        evidence = adoption.ArmEvidence()
        for plant in plants:
            group = groups.get((plant, arm))
            if group is None:
                problems.append(f"{plant} {arm}: no group")
                continue
            if group["no_reference"]:
                problems.append(f"{plant} {arm}: no_reference {group['no_reference']}")
            if group["not_judgeable_items"][reading.j7]:
                problems.append(f"{plant} {arm}: not-judgeable items")
            evidence.groups[plant] = group
        if all(plant in evidence.groups for plant in plants):
            units[arm] = sorted(adoption.failed_units(evidence, reading))
    return units, problems


def unit_diff(units: dict, arm: str) -> dict:
    full, other = set(units[FULL_ARM]), set(units[arm])
    return {"only_in_" + arm: sorted(map(list, other - full)),
            "only_in_" + FULL_ARM: sorted(map(list, full - other))}


# ------------------------------------------------------------------------------ rule
def activation_totals(rows: list[dict], plants: tuple[str, ...]) -> dict:
    """Per component: activation in the full arm (main part, given plants), in every main
    arm that has the component (all plants), and in the D part (arm a2)."""
    import ed7_probe

    def total(selected: list[dict], key: str) -> int | None:
        values = [row.get(key) for row in selected]
        if not selected or any(v is None for v in values):
            return None
        return int(sum(values))

    main = [r for r in rows if r["part"] == "main"]
    out = {}
    for component in COMPONENTS:
        key = PRIMARY_KEY[component]
        full = [r for r in main if r["arm"] == FULL_ARM and r["plant"] in plants]
        having = [r for r in main if component in ed7_probe.ARMS[r["arm"]]]
        d_part = [r for r in rows if r["part"] == "d"]
        trigger_key = {"A_i": "a1_triggers", "A_ii": "a2_floors", "A_ib": "ib_triggers",
                       "B3": None}[component]
        out[component] = {
            "key": key,
            "full_arm_vbm5": total(full, key),
            "full_arm_all6": total([r for r in main if r["arm"] == FULL_ARM], key),
            "arms_with_component_all6": total(having, key),
            "arms_with_component": sorted({r["arm"] for r in having}),
            "d_part_a2": total(d_part, key),
            "full_arm_vbm5_lines_with_activation": sum(bool(r.get(key)) for r in full),
            "full_arm_vbm5_lines": len(full),
        }
        if trigger_key is not None:
            out[component]["full_arm_vbm5_" + trigger_key] = total(full, trigger_key)
    return out


def decide(component: str, counts: dict, activation: int | None, *, b3_activation_rule: bool
           ) -> dict:
    """Edition 6 4 step 2 on one component (``b3_activation_rule``: the spec text applies
    rule (a) to B3; the edition 6 tool did not)."""
    arm = ARM_WITHOUT[component]
    full = counts[FULL_ARM]
    without = None if arm is None else counts[arm]
    result = {"arm_without": arm, "failed_units_without": without,
              "failed_units_full": full, "activation": activation}
    if activation is None:
        return {**result, "decision": "not_judgeable", "rule": "activation record missing"}
    if activation == 0 and (component != "B3" or b3_activation_rule):
        return {**result, "decision": "drop", "rule": "(a) activation 0"}
    if without is None:
        return {**result, "decision": "keep",
                "rule": "(a) activation > 0; (b) not computable (no arm without it)"}
    if component == "B3":
        is_drop = without <= full - B3_DROP_MARGIN
        rule = f"B3 exception: {arm} {without} vs {FULL_ARM} {full}, drop at >= 2 fewer"
    else:
        is_drop = without < full
        rule = f"(b) {arm} {without} vs {FULL_ARM} {full}, drop when fewer (tie keeps)"
    return {**result, "decision": "drop" if is_drop else "keep", "rule": rule}


def share_decisions(units: dict, activation: dict, stall: dict) -> dict:
    counts = {arm: len(value) for arm, value in units.items()}
    spec_text, tool_ed6 = {}, {}
    for component in COMPONENTS:
        value = activation[component]["full_arm_vbm5"]
        spec_text[component] = decide(component, counts, value, b3_activation_rule=True)
        tool_ed6[component] = decide(component, counts, value, b3_activation_rule=False)
    a_i = tool_ed6["A_i"]
    a_i["c04_stall_lines_ed6"] = stall
    if a_i["decision"] == "drop" and stall["a6"] > stall[FULL_ARM]:
        a_i.update(decision="keep", rule=a_i["rule"] + "; kept by the Mc04 stall rule")
    return {"failed_units_by_arm": counts, "spec_text": spec_text,
            "edition6_tool_code": tool_ed6}


# ------------------------------------------------------------------------------ outputs
def write_csv(path: Path, rows: list[dict]) -> None:
    fields: list[str] = []
    for row in rows:
        fields += [name for name in row if name not in fields]
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def unit_rows(adoption, groups: dict, units: dict, reading) -> list[dict]:
    rows = []
    for arm in SHARE_ARMS:
        failed = {tuple(unit) for unit in units.get(arm, [])}
        for plant in adoption.PLANT_SETS[reading.plants]:
            group = groups[(plant, arm)]
            items_by_key = defaultdict(list)
            for item in group["fail_items"][reading.j7]:
                items_by_key[item["key"]].append(f"{item['item']}:{item.get('detail', '')}")
            listed_keys = (set(items_by_key) | set(group.get("r15_failed_keys", []))
                           | {key for unit_plant, key in failed if unit_plant == plant})
            for key in sorted(listed_keys):
                rows.append({"arm": arm, "plant": plant, "key": key,
                             "failed_unit": (plant, key) in failed,
                             "fail_items": " | ".join(items_by_key.get(key, [])),
                             "r15_worsening": key in group.get("r15_failed_keys", [])})
    return rows


def run(args: argparse.Namespace) -> tuple[str, dict]:
    out_dir = args.out_dir.resolve()
    outputs = {name: out_dir / name for name in
               ("share_result.json", "share_units.csv", "share_activation.csv",
                "manifest.json")}
    existing = [str(path) for path in outputs.values() if path.exists()]
    if existing:
        raise InputError(f"outputs exist (never overwritten): {existing}")
    checkout = args.checkout.resolve()
    git_before = git_state(checkout)
    started = datetime.now(timezone.utc).isoformat()
    shas = {"rows": file_sha256(ROWS_PATH), "keys": file_sha256(KEYS_PATH),
            "v0": file_sha256(V0_PATH)}
    expected = {"rows": ROWS_SHA256, "keys": KEYS_SHA256, "v0": V0_SHA256}
    if shas != expected:
        raise InputError(f"input sha256 differ: {shas} != {expected}")

    coupled = checkout / "04_scripts/04_hydraulic/coupled"
    sys.path.insert(0, str(coupled))
    import ed6_probe_share as share6
    import ed7_condition3_adoption as adoption

    adoption.EXPECTED_CONDITION = {**adoption.EXPECTED_CONDITION, **EXTRA_CONDITION}
    keys, planned = adoption.read_key_file(KEYS_PATH, KEYS_SHA256)
    v0_rows = adoption.v0_metric_rows(V0_PATH, V0_SHA256)
    scan = scan_probe(adoption, share6, planned, keys)
    groups = {key: adoption.group_judgement(metrics, v0_rows)
              for key, metrics in scan["metrics"].items()}

    fixed = adoption.FIXED_READING
    ed6_like = adoption.Reading(j7="ed6_share", stiffness="none", plants="all6",
                                ratio="known_shots", n_rev="sum")
    units, problems = arm_units(adoption, groups, fixed)
    units_ed6, problems_ed6 = arm_units(adoption, groups, ed6_like)
    activation = activation_totals(scan["activation_rows"], adoption.VBM_PLANTS)
    stall = {arm: sum(r["stall_signature_ed6"] for r in scan["activation_rows"]
                      if r["part"] == "main" and r["arm"] == arm
                      and r["plant"] == DEADBAND_PLANT) for arm in (FULL_ARM, "a6")}
    decisions = share_decisions(units, activation, stall) if not problems else None
    decisions_ed6 = (share_decisions(units_ed6, activation, stall)
                     if not problems_ed6 else None)
    checks = {"line_problems": scan["line_problems"], "missing_jobs": scan["missing"],
              "repeated_jobs": scan["repeated"], "error_lines": scan["errors"],
              "unplanned_jobs": scan["unplanned"],
              "activation_missing": [f"{r['plant']} {r['arm']} {r['part']} {r['key']}"
                                     for r in scan["activation_rows"]
                                     if r["activation_missing"]],
              "comparison_problems": problems}
    git_after = git_state(checkout)
    code_problems = []
    if git_before.get("head") != EXPECTED_HEAD or git_before.get("is_clean") is not True:
        code_problems.append(f"checkout before: {git_before}")
    if git_after != git_before:
        code_problems.append(f"checkout changed during the run: {git_after}")
    checks["code_problems"] = code_problems

    if checks["line_problems"] or checks["activation_missing"] or code_problems:
        status = "setting_defect"
    elif scan["missing"] or scan["repeated"] or scan["errors"] or scan["unplanned"]:
        status = "incomplete"
    elif problems:
        status = "not_judgeable"
    else:
        status = "decided"

    result = {
        "status": status,
        "rule_text": {"spec_v7_526": "몫 판단 규칙: 판 6 4절 2와 같다(동률이면 남김, 발동 0일 "
                                     "때만 뺌). 실제로 쓸 도구의 규칙을 문면과 대조해 공개한다.",
                      "spec_v6_4_2": "(a) 발동 수 0, (b) X를 뺀 팔이 전부 켠 팔보다 V0 대비 "
                                     "실패 키가 적음; 동률이면 남김; B3는 2키 이상 적을 때만"
                                     "(발동 0이면 (a))"},
        "arms": {"full": FULL_ARM, "without": ARM_WITHOUT},
        "reading_fixed": fixed.name,
        "failed_units": {arm: [list(u) for u in value] for arm, value in units.items()},
        "unit_differences_vs_full": {arm: unit_diff(units, arm) for arm in units
                                     if arm != FULL_ARM},
        "activation": activation,
        "decisions": decisions,
        "record_only_edition6_tool_reading": {
            "reading": ed6_like.name, "problems": problems_ed6,
            "failed_units": {arm: [list(u) for u in value] for arm, value in units_ed6.items()},
            "unit_differences_vs_full": {arm: unit_diff(units_ed6, arm) for arm in units_ed6
                                         if arm != FULL_ARM},
            "decisions": decisions_ed6},
        "checks": checks,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    with outputs["share_result.json"].open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=1, ensure_ascii=False, default=str)
    write_csv(outputs["share_units.csv"], unit_rows(adoption, groups, units, fixed))
    write_csv(outputs["share_activation.csv"], scan["activation_rows"])
    manifest = {
        "tool": str(Path(__file__).resolve()), "tool_sha256": file_sha256(Path(__file__)),
        "started_utc": started, "ended_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.executable, "argv": sys.argv,
        "checkout": str(checkout), "git_before": git_before, "git_after": git_after,
        "inputs": {"rows": {"path": str(ROWS_PATH), "sha256": shas["rows"]},
                   "keys": {"path": str(KEYS_PATH), "sha256": shas["keys"]},
                   "v0": {"path": str(V0_PATH), "sha256": shas["v0"]},
                   "spec_v7": {"path": str(SPEC_PATH), "sha256": file_sha256(SPEC_PATH)},
                   "spec_v6": {"path": str(SPEC_V6_PATH), "sha256": file_sha256(SPEC_V6_PATH)},
                   "imported_modules": {
                       name: {"path": str(Path(module.__file__)),
                              "sha256": file_sha256(Path(module.__file__))}
                       for name, module in (("ed7_condition3_adoption", adoption),
                                            ("ed6_probe_share", share6))}},
        "status": status,
    }
    with outputs["manifest.json"].open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=1, ensure_ascii=False)
    return status, {name: str(path) for name, path in outputs.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        status, paths = run(args)
    except InputError as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}), flush=True)
        return EXIT_STOP
    except Exception:  # every unexpected failure is a tool error (exit 3)
        traceback.print_exc()
        print(json.dumps({"status": "tool_error"}), flush=True)
        return EXIT_TOOL
    print(json.dumps({"status": status, "outputs": paths}), flush=True)
    return EXIT_DECIDED if status == "decided" else EXIT_STOP


if __name__ == "__main__":
    sys.exit(main())
