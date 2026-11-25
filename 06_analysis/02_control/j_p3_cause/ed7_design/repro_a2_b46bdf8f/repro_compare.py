"""436.9 edition 7 pre-seal reproduction check of probe arm a2 on b46bdf8f (audit M-8).

Compares the a2 lines of the probe 6bfb2560 (``ed7_probe.jsonl``, 114 lines) with the rerun
on b46bdf8f (``j9_runs/b46bdf8f/repro_a2/ed7_probe_a2.jsonl``):

1. line set: the job identities (``ed7_condition3_adoption.job_identity``, runtime fields left
   out) of both files;
2. ``commands_sha256`` of every line pair;
3. the new record keys of b46bdf8f on every rerun line: ``lsb_record.blind.level_done``,
   ``lsb_record.blind.twist_over_limit`` and the T4h array ``lsb_ib_twist_load_N`` (the
   original lines are expected without them; counted as a record);
4. the run identity of the rerun (start and end HEAD b46bdf8f, clean);
5. the 64-row fixed table (``fixed_table_b46bdf8f/fixed_table.py``, its own functions) built
   again from the rerun and compared field by field with ``fixed_table_a2.json``. The D line
   condition of the rerun comes from ``jp3_rev7_condition.build_report`` (b46bdf8f) on the
   rerun; the fixed table read ``condition_ad7a716e.json`` (the same condition file content
   at both commits, ``git diff`` empty). As a control, the same build on the original inputs
   must give ``fixed_table_a2.json`` again (else the method is not trusted: ``not_judgeable``).

``build_table`` repeats ``fixed_table.build`` with the rows, T4h folder, condition report and
run identity as arguments (the fixed table script has them as module constants); the input
sha pins of ``fixed_table.INPUTS`` are checked here except the spec (the spec work copy has
changed since; recorded).

======  ==================  ===================================================
exit    status              meaning
======  ==================  ===================================================
0       ``match``           every comparison equal, every key present
2       ``mismatch``        outputs written; a difference (``differences``)
2       ``not_judgeable``   outputs written; the control build differs
2       ``input_error``     no output: an input sha differs or an output exists
3       ``tool_error``      an unexpected failure
======  ==================  ===================================================

Usage (dynamics-dev ``python.exe -I -B``, ``MKL_THREADING_LAYER=TBB``):
  python -I -B repro_compare.py --out-dir <this folder>
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

EXIT_MATCH, EXIT_STOP, EXIT_TOOL = 0, 2, 3
EXPECTED_HEAD = "b46bdf8fdbad730eabf9226c5e1cfed0e980b5e9"
REPO = Path(r"C:\workspace\outrigger_control")
CAUSE = REPO / "06_analysis/02_control/j_p3_cause"
WORKTREE = REPO / ".claude/worktrees/ed7-impl"
FIXED_DIR = CAUSE / "ed7_design/fixed_table_b46bdf8f"
FIXED_SCRIPT = FIXED_DIR / "fixed_table.py"
FIXED_JSON = FIXED_DIR / "fixed_table_a2.json"
ORIGINAL_DIR = CAUSE / "j9_runs/6bfb2560/ed7_probe_a1"
ORIGINAL_ROWS = ORIGINAL_DIR / "ed7_probe.jsonl"
ORIGINAL_ROWS_SHA256 = "1107b30962a038ec9ebccdd19543338f7df771261aa208ef458de6b814817ce9"
REPRO_DIR = CAUSE / "j9_runs/b46bdf8f/repro_a2"
REPRO_ROWS = REPRO_DIR / "ed7_probe_a2.jsonl"
REPRO_IDENTITY = REPRO_DIR / "ed7_probe_a2.identity.json"
ARM = "a2"
EXPECTED_LINES = 114
NEW_BLIND_KEYS = ("level_done", "twist_over_limit")
NEW_T4H_ARRAY = "lsb_ib_twist_load_N"
UNCOMPARED_TOP_KEYS = ("inputs", "code_identity")
"""Fixed table keys that name the inputs and checkout (differ by construction)."""
ROW_ID_FIELDS = ("scope", "setting", "key")
OUTPUT_NAMES = ("compare_result.json", "condition_repro.json", "fixed_table_repro_a2.json",
                "manifest.json")


class InputError(Exception):
    """No output is written (exit 2)."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalized(value):
    """The value as the fixed table stored it (``json.dumps(default=str)`` round trip)."""
    return json.loads(json.dumps(value, default=str))


def git_state(checkout: Path) -> dict:
    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(checkout), *args], capture_output=True,
                              text=True, timeout=120, check=False)

    try:
        head, status = git("rev-parse", "HEAD"), git("status", "--porcelain")
        ignored = git("status", "--porcelain", "--ignored")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"head": None, "is_clean": None, "git_error": str(exc)}
    if head.returncode or status.returncode or ignored.returncode:
        return {"head": None, "is_clean": None,
                "git_error": (head.stderr or status.stderr or ignored.stderr)[:300]}
    return {"head": head.stdout.strip(), "is_clean": not status.stdout.strip(),
            "status_ignored_sha256": hashlib.sha256(ignored.stdout.encode()).hexdigest()}


def load_fixed_table_module():
    """``fixed_table.py`` imported read-only (it puts the worktree code on ``sys.path``)."""
    spec = importlib.util.spec_from_file_location("fixed_table_b46bdf8f", FIXED_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    # dataclasses look the defining module up in sys.modules while the class is built
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ------------------------------------------------------------------------------ lines
def a2_lines(rows_path: Path, adoption) -> dict[str, dict]:
    """Job identity -> the a2 line summary (commands hash, T4h file, new record keys)."""
    out: dict[str, dict] = {}
    repeated = []
    with rows_path.open(encoding="utf-8") as handle:
        for text in handle:
            if not text.strip():
                continue
            record = json.loads(text)
            if record["job"]["setting"].split("-")[-1] != ARM:
                continue
            identity = adoption.job_identity(record["job"])
            if identity in out:
                repeated.append(identity)
            blind = (record.get("lsb_record") or {}).get("blind") or {}
            out[identity] = {"setting": record["job"]["setting"],
                             "has_error": "error" in record,
                             "commands_sha256": record.get("commands_sha256"),
                             "t4h_file": record.get("t4h_file"),
                             **{f"has_{key}": key in blind for key in NEW_BLIND_KEYS}}
    if repeated:
        raise InputError(f"{rows_path.name}: repeated a2 jobs {repeated[:3]}")
    return out


def t4h_has_array(t4h_dir: Path, name: str | None) -> bool | None:
    if name is None or not (t4h_dir / name).is_file():
        return None
    with np.load(t4h_dir / name, allow_pickle=False) as data:
        return NEW_T4H_ARRAY in data.files


def line_comparison(original: dict, repro: dict, repro_t4h: Path) -> dict:
    only_original = sorted(set(original) - set(repro))
    only_repro = sorted(set(repro) - set(original))
    shared = sorted(set(original) & set(repro))
    hash_mismatch = [{"job": job, "setting": original[job]["setting"],
                      "original": original[job]["commands_sha256"],
                      "repro": repro[job]["commands_sha256"]}
                     for job in shared
                     if original[job]["commands_sha256"] != repro[job]["commands_sha256"]
                     or original[job]["commands_sha256"] is None]
    t4h_name_mismatch = [job for job in shared
                         if original[job]["t4h_file"] != repro[job]["t4h_file"]]
    missing_keys = {}
    for job in sorted(repro):
        absent = [key for key in NEW_BLIND_KEYS if not repro[job][f"has_{key}"]]
        if t4h_has_array(repro_t4h, repro[job]["t4h_file"]) is not True:
            absent.append(f"T4h {NEW_T4H_ARRAY}")
        if absent:
            missing_keys[f"{repro[job]['setting']} {job}"] = absent
    return {"original_a2_lines": len(original), "repro_a2_lines": len(repro),
            "only_in_original": only_original, "only_in_repro": only_repro,
            "error_lines_repro": [job for job in repro if repro[job]["has_error"]],
            "commands_sha256_equal": len(shared) - len(hash_mismatch),
            "commands_sha256_compared": len(shared),
            "commands_sha256_mismatch": hash_mismatch,
            "t4h_file_name_mismatch": t4h_name_mismatch,
            "repro_new_keys_missing": missing_keys,
            "original_lines_with_level_done": sum(v["has_level_done"]
                                                  for v in original.values()),
            "original_lines_with_twist_over_limit": sum(v["has_twist_over_limit"]
                                                        for v in original.values())}


# ------------------------------------------------------------------------------ fixed table
def build_table(ft, rows_path: Path, t4h_dir: Path, condition_doc: dict,
                run_identity: dict, inputs: dict) -> dict:
    """``fixed_table.build`` with its file inputs as arguments (same functions, same order)."""
    probe_keys = ft.read_json(ft.INPUTS["probe_keys"][0])
    sens_keys = ft.read_json(ft.INPUTS["sens_keys"][0])
    wanted = ft.wanted_lines(probe_keys, sens_keys)
    records = ft.read_wanted_records(rows_path, wanted)
    v0_rows = ft.v0_metric_rows(ft.INPUTS["v0"][0], ft.INPUTS["v0"][1])

    metrics = ft.unit_metrics(records, wanted, t4h_dir, lambda entry: entry.setting)
    judged = ft.unit_table(metrics, v0_rows)
    verdicts = ft.unit_verdicts(metrics, judged)
    cross = ft.unit_cross_check(records, wanted, t4h_dir, v0_rows, verdicts)

    condition = {(line["setting"], line["t4h_file"]): line for line in condition_doc["lines"]}
    pairs = ft.grid_pairs(ft.read_json(ft.INPUTS["grid_keys"][0]))
    identity_problems = ft.line_identity_problems(records, wanted, probe_keys)

    units, d_rows = [], []
    for identity, entry in sorted(wanted.items(), key=lambda item: (item[1].scope,
                                                                    item[1].setting,
                                                                    item[1].key)):
        record = records[identity]
        common_row = {"scope": entry.scope, "setting": entry.setting, "plant": entry.plant,
                      "key": entry.key, "row": ft.rules.row_key(record["job"]),
                      "phase": ft.phase_of(record["job"]), "t4h_file": record["t4h_file"],
                      "commands_sha256": record.get("commands_sha256"),
                      "final_phase": record.get("final_phase"),
                      **ft.min_force_values(record)}
        if entry.scope == "sens40":
            units.append({**common_row, **verdicts[identity]})
        else:
            d_rows.append({**common_row, **ft.d_line_values(record, entry, pairs, condition)})
    return {"rule": "jp3_remedy_spec_v7.md revision 5 P7-9 (6.2 probe units, 6.3 D lines); "
                    "Q7-C4 decided (WARN_PROBE_RETRACT_NOT_OPENED not exempt)",
            "arm": ft.ARM, "inputs": inputs,
            "checks": {"line_identity_problems": identity_problems,
                       "run_identity_problems": ft.adoption.run_identity_problems(run_identity),
                       "unit_label_cross_check": cross},
            "sens40_units": units, "d24_lines": d_rows,
            "reading_1_moved": judged["reading_1_moved"],
            "j7_stiffness_exempt": judged["j7_exempt"], "r15_worsening": judged["r15"],
            "rule_6_2_fixed_table": ft.cluster_rule_from_fixed(units),
            "rule_6_3_fixed_table": ft.confirmation_rule_from_fixed(d_rows)}


def table_differences(stored: dict, built: dict) -> list[dict]:
    """Field differences between two fixed tables (rows matched by scope, setting, key)."""
    stored, built = normalized(stored), normalized(built)
    differences = []
    for top in sorted(set(stored) | set(built)):
        if top in UNCOMPARED_TOP_KEYS:
            continue
        if top in ("sens40_units", "d24_lines"):
            differences += _row_differences(top, stored.get(top) or [], built.get(top) or [])
        elif stored.get(top) != built.get(top):
            differences.append({"where": top, "stored": stored.get(top),
                                "built": built.get(top)})
    return differences


def _row_differences(section: str, stored_rows: list, built_rows: list) -> list[dict]:
    def by_id(rows):
        return {tuple(row[field] for field in ROW_ID_FIELDS): row for row in rows}

    stored_by, built_by = by_id(stored_rows), by_id(built_rows)
    out = []
    for row_id in sorted(set(stored_by) | set(built_by)):
        left, right = stored_by.get(row_id), built_by.get(row_id)
        if left is None or right is None:
            out.append({"where": f"{section} {' '.join(map(str, row_id))}",
                        "stored": left is not None, "built": right is not None})
            continue
        for field in sorted(set(left) | set(right)):
            if left.get(field) != right.get(field):
                out.append({"where": f"{section} {' '.join(map(str, row_id))}",
                            "field": field, "stored": left.get(field),
                            "built": right.get(field)})
    return out


# ------------------------------------------------------------------------------ run
def checked_inputs(ft) -> dict:
    """Fixed table input pins (spec left out, recorded) plus the original and repro rows."""
    found = {}
    for name, (path, pinned) in ft.INPUTS.items():
        digest = file_sha256(path)
        if name != "spec" and pinned is not None and digest != pinned:
            raise InputError(f"input {name}: sha256 {digest} != pinned {pinned}")
        found[name] = {"path": str(path), "sha256": digest,
                       "pinned": None if name == "spec" else pinned}
    if found["rows"]["sha256"] != ORIGINAL_ROWS_SHA256:
        raise InputError("original rows of another sha256")
    found["fixed_table_a2_json"] = {"path": str(FIXED_JSON), "sha256": file_sha256(FIXED_JSON)}
    found["fixed_table_py"] = {"path": str(FIXED_SCRIPT), "sha256": file_sha256(FIXED_SCRIPT)}
    found["repro_rows"] = {"path": str(REPRO_ROWS), "sha256": file_sha256(REPRO_ROWS)}
    found["repro_identity"] = {"path": str(REPRO_IDENTITY),
                               "sha256": file_sha256(REPRO_IDENTITY)}
    return found


def repro_identity_problems(identity: dict) -> list[str]:
    problems = []
    for side in ("start", "end"):
        entries = identity.get(side) or []
        if not entries:
            problems.append(f"no {side} entry")
        for entry in entries:
            git = entry.get("git") or {}
            if git.get("head") != EXPECTED_HEAD:
                problems.append(f"{side} head {git.get('head')}")
            if git.get("is_clean") is not True:
                problems.append(f"{side} not clean")
    return problems


def run(out_dir: Path) -> tuple[str, dict]:
    outputs = {name: out_dir / name for name in OUTPUT_NAMES}
    if any(path.exists() for path in outputs.values()):
        raise InputError("an output exists (never overwritten)")
    git_before = git_state(WORKTREE)
    if git_before.get("head") != EXPECTED_HEAD or git_before.get("is_clean") is not True:
        raise InputError(f"worktree is not a clean b46bdf8f: {git_before}")
    started = datetime.now(timezone.utc).isoformat()
    ft = load_fixed_table_module()
    import jp3_rev7_condition as condition_tool

    inputs = checked_inputs(ft)
    repro_t4h = REPRO_ROWS.with_name(f"{REPRO_ROWS.stem}_t4h")
    original_t4h = ft.PROBE_DIR / "ed7_probe_t4h"

    lines = line_comparison(a2_lines(ORIGINAL_ROWS, ft.adoption),
                            a2_lines(REPRO_ROWS, ft.adoption), repro_t4h)
    repro_identity = read_json(REPRO_IDENTITY)
    identity = {"problems": repro_identity_problems(repro_identity),
                "run_identity_problems_tool": ft.adoption.run_identity_problems(repro_identity)}

    stored = read_json(FIXED_JSON)
    control = build_table(ft, ORIGINAL_ROWS, original_t4h, read_json(ft.INPUTS["condition"][0]),
                          read_json(ft.INPUTS["run_identity"][0]), stored["inputs"])
    control_differences = table_differences(stored, control)
    condition_repro = condition_tool.build_report(REPRO_ROWS, repro_t4h)
    repro_table = build_table(ft, REPRO_ROWS, repro_t4h, condition_repro, repro_identity,
                              {"repro_rows": inputs["repro_rows"],
                               "condition": "condition_repro.json (b46bdf8f build_report)"})
    repro_differences = table_differences(stored, repro_table)

    if control_differences:
        status = "not_judgeable"
    elif (lines["only_in_original"] or lines["only_in_repro"] or lines["error_lines_repro"]
          or lines["commands_sha256_mismatch"] or lines["repro_new_keys_missing"]
          or identity["problems"] or identity["run_identity_problems_tool"]
          or repro_differences):
        status = "mismatch"
    else:
        status = "match"
    git_after = git_state(WORKTREE)
    result = {"status": status, "lines": lines, "repro_identity": identity,
              "fixed_table": {"rows_compared": len(stored["sens40_units"])
                              + len(stored["d24_lines"]),
                              "control_differences": control_differences,
                              "repro_differences": repro_differences,
                              "repro_rule_6_2": repro_table["rule_6_2_fixed_table"][
                                  "fixed_table_alone"],
                              "repro_rule_6_3": repro_table["rule_6_3_fixed_table"][
                                  "fixed_table_alone"]},
              "condition_repro_summary": condition_repro["summary"],
              "worktree_unchanged": git_after == git_before}
    if git_after != git_before:
        result["status"] = status = "mismatch"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, value in (("compare_result.json", result),
                        ("condition_repro.json", condition_repro),
                        ("fixed_table_repro_a2.json", repro_table)):
        with outputs[name].open("x", encoding="utf-8") as handle:
            json.dump(value, handle, indent=1, default=str, ensure_ascii=False)
    manifest = {"script": {"path": str(Path(__file__).resolve()),
                           "sha256": file_sha256(Path(__file__))},
                "python": sys.executable, "argv": sys.argv, "started_utc": started,
                "ended_utc": datetime.now(timezone.utc).isoformat(),
                "worktree": str(WORKTREE), "git_before": git_before, "git_after": git_after,
                "inputs": inputs, "status": status}
    with outputs["manifest.json"].open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=1, ensure_ascii=False)
    return status, {name: str(path) for name, path in outputs.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        status, paths = run(args.out_dir.resolve())
    except InputError as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}), flush=True)
        return EXIT_STOP
    except Exception:  # every unexpected failure is a tool error (exit 3)
        traceback.print_exc()
        print(json.dumps({"status": "tool_error"}), flush=True)
        return EXIT_TOOL
    print(json.dumps({"status": status, "outputs": paths}), flush=True)
    return EXIT_MATCH if status == "match" else EXIT_STOP


if __name__ == "__main__":
    sys.exit(main())
