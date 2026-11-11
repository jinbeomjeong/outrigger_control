"""G-S dry run of the LAS-b P5r4 + K1 re-judgement (rules 16.2): list generator and checker.

Rules: ``las_p5r4_k1_rules.md`` 16.2 (sealed, ``las_p5r4k1_judge.RULES_SHA256``). Standard
library only; the stored files are read for keys and job fields (setting, eps), never for
judged values.

``list``  (16.2 (가) / (나)) the harness G-S lines: per bundle x arm x stage one line, a stage
          being (series token of the key: ``d1.key`` group, ``case`` for a verdict case, the
          label kind ``LT`` / ``LH`` / ``LQ`` of a grid line) x setting (VB / V0) x eps
          (``e0`` / ``e+``) present in the bundle; its unit is the first of the stage's units
          that are R-S keys (in sample) when there is one, else the first unit (sorted).
          Z-X is the ref line of the first Z-T key with the DONE record. The Chrono G-S rows
          are the 6 stages x 2 arms of 16.2 (나) with a short ``--duration``; their argv come
          from cad-expert's ``04_scripts/02_chrono/las_p5r4_k1_chrono_rows.py`` (``rows()`` or
          ``ROWS``: dicts with ``p5k_id`` and ``argv``) when that module is there.
          Prints counts, the list sha256 values and the out-of-sample units (keys only).
``check`` (16.2 (가) pass conditions) the G-S lines against the list: line count = list
          count, no ``error`` line, every field the harness judge reads present as a key
          (values may be None), K-3 / K-4 / K-5 true, and the run log's ``errors N`` = 0 when
          ``--log`` is given. Prints only pass / fail per condition and the missing field
          names: never a force, stroke, time, event or hash value.

Usage (python-dev, project root, PowerShell):
  python -I -B 06_analysis/02_control/verif_matrix/scripts/las_p5r4k1_gs.py list
      [--v5-dir <v5>] [--duration-s 10] --out <gs_list.json>
  python -I -B 06_analysis/02_control/verif_matrix/scripts/las_p5r4k1_gs.py check
      --list <gs_list.json> [--gs-dir <v5/las/p5r4k1/gs>] [--log <runner log> ...]
Exit codes: 0 list written / every condition true, 1 a condition false, 2 input error,
3 tool error. The last stdout line is JSON.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import las_p5r4k1_judge as pj  # noqa: E402

CHRONO_ROWS_PATH = pj.ROOT / "04_scripts" / "02_chrono" / "las_p5r4_k1_chrono_rows.py"
GS_BATCH_NAME = "V5-LAS-P5R4-K1-GS"
DEFAULT_DURATION_S = 10.0
DURATION_OPTION = "--duration"
CHRONO_STAGES = (("A-Kc1-VB", "A1", "A2"), ("A-Kc3-VB", "A3", "A4"), ("A-Kc1-V0", "A5", "A6"),
                 ("B", "B1", "B2"), ("C-x1.0", "C1", "C2"), ("C-x1.1", "C3", "C4"))
"""16.2 (나): stage, ref row id, cand row id (rules 4.3 table)."""
GRID_KINDS = ("LT", "LH", "LQ")
VERDICT_SERIES = "case"
ERRORS_PATTERN = re.compile(r"\berrors\s*[:=]?\s*(\d+)\b")
"""= ``tools/verif/log_errors.py`` default pattern."""

COMMON_FIELDS = ("commands_sha256", "final_phase", "event_names", "controller_tag", "job",
                 "las.params", "las.ramp", "las.end_t_s", "las.end_reason",
                 "rev.candidate", "rev.settings", "rev.settings_match", "rev.key",
                 "k1.enabled", "k1.setting", "k1.decisions", "k1.r4_applied",
                 "k1.would_block_any", "k1.loc_calls",
                 "p5k.identity", "p5k.rules", "p5k.is_liftoff_slow_tag", "p5k.override",
                 "p5k.touch_creep_latch_enabled", "p5k.code_blobs", "las_candidate",
                 "las.settings", "rev.identity", "rev.rules_sha256",
                 "effective.flat_soil_margin_order_gate", "effective.touch_creep_latch_enable",
                 "anchor.soil_meta", "anchor.loc_calls", "values.events.t_loc_first_s",
                 "values.events.t_loc_last_s", "values.forces.after_liftoff")
D1_FIELDS = ("d1.verdict", "d1.items", "d1.fail_items", "d1.t_ready_s", "d1.stroke_max_m",
             "d1.F_judged_min_N")
CASE_FIELDS = ("values.times.t_first_ready_s",)
DONE_FIELDS = ("done_trace", "done_clock.loss_s", "done_clock.resets",
               "done_clock.clock_starts_s", "done_clock.t_loc_last_before_done_s")
GRID_FIELDS = ("diag.summary.F_RL_kN", "diag.summary.F_judged_min_kN",
               "diag.summary.gate_consistent", "diag.summary.t_lift_s",
               "diag.touch_budget.level_budget_periods", "diag.periods",
               "diag.force_window.rows")
"""The fields the harness judge reads (5.1, 6.1, 6.2, 6.4), as dotted key paths."""


# =============================================================================== stages
def series_of(unit: str, label: str | None, job: dict) -> str:
    """The series token of a unit: grid label kind, ``case`` or the ``d1.key`` group."""
    for kind in GRID_KINDS:
        if label and f"-{kind}-" in label:
            return kind
    if "case" in job:
        return VERDICT_SERIES
    return unit.split("|")[1]


def stage_of(unit: str, label: str | None, job: dict) -> str:
    eps = float(job.get("eps", 0.0) or 0.0)
    return f"{series_of(unit, label, job)}|{job.get('setting')}|{'e0' if eps == 0 else 'e+'}"


def bundle_units(bundle: str, bases: pj.Bases) -> list[tuple[str, str | None, dict]]:
    """(unit, label, stored job) of every unit of a bundle, from the stored files."""
    lines = bases.lines
    if bundle == "Z-0":
        return [(pj.key_of(line), pj.rev_of(line).get("label"), line["job"])
                for line in lines["R0"]]
    if bundle == "Z-A":
        return [(pj.grid_unit(line), pj.rev_of(line).get("label"), line["job"])
                for line in lines["R0A"] + lines["RQ"]]
    if bundle == "Z-T":
        return [(pj.key_of(line), None, line["job"]) for line in lines["RT"]]
    if bundle == "Z-S":
        return [(pj.stored_key_of(line), None, line["job"]) for line in lines["RS"]]
    if bundle == "Z-C":
        return [(pj.stored_key_of(line), None, line["job"]) for line in lines["SC"]]
    raise ValueError(f"no stored units for {bundle!r}")


def _key_part(unit: str) -> str:
    return unit.split(pj.GRID_UNIT_SEPARATOR, 1)[0]


def harness_rows(bases: pj.Bases) -> list[dict]:
    """16.2 (가): one row per bundle x arm x stage (+ the Z-X row)."""
    in_sample_keys = set(bases.lists["Z-S"])
    rows = []
    for bundle in ("Z-0", "Z-A", "Z-T", "Z-S", "Z-C"):
        stages: dict[str, list[str]] = {}
        for unit, label, job in bundle_units(bundle, bases):
            stages.setdefault(stage_of(unit, label, job), []).append(unit)
        for stage in sorted(stages):
            units = sorted(stages[stage])
            in_sample = [unit for unit in units if _key_part(unit) in in_sample_keys]
            unit = in_sample[0] if in_sample else units[0]
            for arm in pj.BUNDLE_ARMS[bundle]:
                is_out = (bundle == "Z-C" and arm == pj.ARM_CAND
                          and _key_part(unit) not in in_sample_keys)
                rows.append({"bundle": bundle, "arm": arm, "stage": stage, "unit": unit,
                             "in_sample": not is_out})
    first_t = sorted(bases.lists["Z-T"])[0]
    rows.append({"bundle": "Z-X", "arm": pj.ARM_REF, "stage": "Z-X", "unit": first_t,
                 "in_sample": True})
    return rows


def _module_rows(path: Path) -> list[dict] | None:
    """cad-expert's Chrono row module rows (``rows()`` or ``ROWS``), None when absent."""
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("las_p5r4_k1_chrono_rows", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows = module.rows() if callable(getattr(module, "rows", None)) else module.ROWS
    return [dict(row) for row in rows]


def with_duration(argv: list[str], duration_s: float) -> list[str]:
    """``argv`` with ``--duration`` set to ``duration_s`` (16.2 (나): only that changes)."""
    out, i = [], 0
    while i < len(argv):
        token = str(argv[i])
        if token == DURATION_OPTION and i + 1 < len(argv):
            i += 2
            continue
        if token.startswith(f"{DURATION_OPTION}="):
            i += 1
            continue
        out.append(token)
        i += 1
    return [*out, DURATION_OPTION, f"{duration_s:g}"]


def chrono_rows(duration_s: float, rows_path: Path = CHRONO_ROWS_PATH) -> tuple[list[dict], str]:
    """16.2 (나): the 12 G-S rows (argv from the row module when it exists)."""
    module_rows = _module_rows(rows_path)
    by_id = {str(row.get("p5k_id")): row for row in module_rows or []}
    source = "pending: cad-expert module las_p5r4_k1_chrono_rows.py" if module_rows is None \
        else rows_path.as_posix()
    rows = []
    for stage, ref_id, cand_id in CHRONO_STAGES:
        for arm, row_id in ((pj.ARM_REF, ref_id), (pj.ARM_CAND, cand_id)):
            module_row = by_id.get(row_id)
            argv = None if module_row is None else with_duration(
                [str(t) for t in module_row["argv"]], duration_s)
            rows.append({"stage": stage, "p5k_id": row_id, "arm": arm,
                         "case": None if module_row is None else f"GS_{module_row.get('case')}",
                         "duration_s": duration_s, "argv": argv})
    return rows, source


def rows_sha256(rows: list[dict]) -> str:
    """List sha256: one compact sorted-key JSON object per row, LF after each, UTF-8."""
    text = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                   for row in rows)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def list_document(bases: pj.Bases, duration_s: float) -> dict:
    harness = harness_rows(bases)
    chrono, source = chrono_rows(duration_s)
    out_of_sample = sorted(row["unit"] for row in harness if not row["in_sample"])
    return {"rules_sha256": pj.RULES_SHA256, "harness": harness,
            "harness_list_sha256": rows_sha256(harness), "chrono_batch": GS_BATCH_NAME,
            "chrono": chrono, "chrono_list_sha256": rows_sha256(chrono),
            "chrono_argv_source": source, "out_of_sample_units": out_of_sample}


# =============================================================================== check
def has_path(line: dict, dotted: str) -> bool:
    value: Any = line
    for name in dotted.split("."):
        if not isinstance(value, dict) or name not in value:
            return False
        value = value[name]
    return True


def required_fields(line: dict, row: dict) -> tuple[str, ...]:
    fields = list(COMMON_FIELDS)
    fields += CASE_FIELDS if pj.is_verdict_case(line) else D1_FIELDS
    if row["arm"] == pj.ARM_CAND or row["bundle"] == "Z-X":
        fields += DONE_FIELDS
    if row["bundle"] == "Z-A" or (pj.rev_of(line).get("grid_point") is not None):
        fields += GRID_FIELDS
    return tuple(fields)


def check_row(line: dict | None, row: dict) -> dict:
    """Pass conditions of one G-S line (field names only, no values)."""
    if line is None:
        return {"present": False, "ok": False}
    if pj.is_error(line):
        return {"present": True, "error_line": True, "ok": False}
    missing = [name for name in required_fields(line, row) if not has_path(line, name)]
    if not has_path(line, "las.start_t_s") and (line.get("las") or {}).get(
            "wrapper_reached") is not False:
        missing.append("las.start_t_s")
    k3 = not pj.tag_problems(line)
    k4 = not pj.gate_problems(line)
    k5 = not pj.las_problems(line)
    return {"present": True, "error_line": False, "missing_fields": missing,
            "K-3": k3, "K-4": k4, "K-5": k5, "gs_flag": pj.p5k_of(line).get("gs") is True,
            "ok": not missing and k3 and k4 and k5 and pj.p5k_of(line).get("gs") is True}


def log_error_counts(paths: list[Path]) -> dict[str, int | None]:
    """The last ``errors N`` of each runner log (None: no such line, not zero)."""
    out = {}
    for path in paths:
        counts = [int(m.group(1)) for m in ERRORS_PATTERN.finditer(
            path.read_text(encoding="utf-8", errors="replace"))]
        out[path.as_posix()] = counts[-1] if counts else None
    return out


def check_document(document: dict, gs_lines: list[dict], logs: dict[str, int | None]) -> dict:
    rows = document["harness"]
    by_unit = {}
    extra = 0
    for line in gs_lines:
        block = pj.p5k_of(line)
        key = (block.get("bundle"), block.get("arm"), pj.unit_of(line))
        if key in by_unit and not pj.is_error(by_unit[key]):
            extra += 1
            continue
        by_unit[key] = line
    results = []
    for row in rows:
        result = check_row(by_unit.get((row["bundle"], row["arm"], row["unit"])), row)
        results.append({"bundle": row["bundle"], "arm": row["arm"], "stage": row["stage"],
                        "unit": row["unit"], **result})
    wanted = {(row["bundle"], row["arm"], row["unit"]) for row in rows}
    outside = sum(1 for key in by_unit if key not in wanted)
    error_lines = sum(1 for line in gs_lines if pj.is_error(line))
    conditions = {
        "line_count_equals_list": len(gs_lines) == len(rows) and not extra and not outside,
        "no_error_lines": error_lines == 0,
        "fields_present": all(not r.get("missing_fields") and r["present"] for r in results),
        "K-3_K-4_K-5": all(r.get("K-3") and r.get("K-4") and r.get("K-5") for r in results),
        "log_errors_0": bool(logs) and all(count == 0 for count in logs.values()),
    }
    return {"rows": len(rows), "lines": len(gs_lines), "error_lines": error_lines,
            "duplicates": extra, "outside_list": outside, "logs": logs,
            "conditions": conditions, "ok": all(conditions.values()), "per_row": results}


# =============================================================================== CLI
def _parse_args(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list", help="write the G-S list (harness lines, Chrono rows)")
    listing.add_argument("--v5-dir", type=Path, default=pj.V5_DIR)
    listing.add_argument("--duration-s", type=float, default=DEFAULT_DURATION_S)
    listing.add_argument("--out", type=Path, required=True)
    checking = sub.add_parser("check", help="check the harness G-S lines (no values)")
    checking.add_argument("--list", type=Path, required=True)
    checking.add_argument("--gs-dir", type=Path, default=None,
                          help="default <v5>/las/p5r4k1/gs")
    checking.add_argument("--v5-dir", type=Path, default=pj.V5_DIR)
    checking.add_argument("--log", type=Path, nargs="*", default=[],
                          help="runner logs whose last 'errors N' must be 0")
    checking.add_argument("--out", type=Path, default=None)
    return parser.parse_args(argv)


def _write(path: Path | None, document: dict) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=1), encoding="utf-8")


def run_list(args) -> int:
    document = list_document(pj.load_bases(args.v5_dir), args.duration_s)
    _write(args.out, document)
    print(f"harness G-S lines {len(document['harness'])} sha256 "
          f"{document['harness_list_sha256']}")
    print(f"chrono G-S rows {len(document['chrono'])} sha256 {document['chrono_list_sha256']} "
          f"(argv: {document['chrono_argv_source']})")
    print(f"out-of-sample units {len(document['out_of_sample_units'])}")
    print(json.dumps({"tool": "las_p5r4k1_gs", "command": "list",
                      "harness": len(document["harness"]),
                      "harness_list_sha256": document["harness_list_sha256"],
                      "chrono": len(document["chrono"]),
                      "chrono_list_sha256": document["chrono_list_sha256"],
                      "out": str(args.out)}))
    return 0


def run_check(args) -> int:
    document = json.loads(args.list.read_text(encoding="utf-8"))
    gs_dir = args.gs_dir or args.v5_dir / pj.RUN_DIR_RELATIVE / pj.GS_DIR_NAME
    gs_lines = []
    for path in sorted(gs_dir.glob(pj.GS_FILE_PATTERN)):
        gs_lines += pj.read_lines(path)
    result = check_document(document, gs_lines, log_error_counts(list(args.log)))
    result["list_sha256_recomputed"] = rows_sha256(document["harness"])
    result["list_sha256_matches"] = (result["list_sha256_recomputed"]
                                     == document.get("harness_list_sha256"))
    result["ok"] = result["ok"] and result["list_sha256_matches"]
    _write(args.out, result)
    for name, value in result["conditions"].items():
        print(f"{name}: {'pass' if value else 'FAIL'}")
    print(json.dumps({"tool": "las_p5r4k1_gs", "command": "check", "ok": result["ok"],
                      "conditions": result["conditions"], "out": str(args.out)}))
    return 0 if result["ok"] else 1


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if pj.seal_problems():
            raise pj.InputError(pj.seal_problems())
        return run_list(args) if args.command == "list" else run_check(args)
    except (pj.InputError, KeyError, ValueError) as exc:
        print(f"input error: {exc!r}")
        print(json.dumps({"tool": "las_p5r4k1_gs", "input_error": str(exc)}))
        return 2
    except OSError as exc:
        print(f"tool error: {exc!r}")
        print(json.dumps({"tool": "las_p5r4k1_gs", "tool_error": repr(exc)}))
        return 3


if __name__ == "__main__":
    sys.exit(main())
