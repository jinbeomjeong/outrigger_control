"""436.8 v5 resume verification, path 1 tools (rules ``v5_resume_4368_rules.md``, sealed 9019b405).

Subcommands (each writes one JSON report with ``--out``; the last stdout line is a JSON summary):

  record-check   4.2 record check of harness outputs (the ``resume_k1`` block of every run record) and of
                 Chrono rows (``batch.json`` argv / start env + ``result.json`` ``c2_setup`` /
                 ``controller_meta``)
  k1-class       7.2 K1 classification per run, the S-5 checks (``applied`` with ``would_block``, the
                 ``_SKIPPED:order`` count), the S-6 uniform-family stop and the hash check of the
                 미작동 runs
                 against anchor files
  jp-reuse       7.3 J_P reuse conditions of the 12 stored Chrono rows (LAS-b shadow + controller events)
  oc5            7.4 O-C5 values of a C-8 row from ``result.json`` (the path 1 inputs of 9.1)
  overlap        11.1 option x stage table of steps files (harness) and Chrono batch rows
  gs             11.2 G-S key presence (prints present / missing only, never values)

Exit codes: 0 no finding, 1 a finding (stop condition, mismatch, missing key), 2 input error, 3
internal error.
The tool reads only; it never runs a simulation. Tag judgements use
``v5_options.is_extend_start_tag`` only.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import traceback
from collections.abc import Iterator
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
for _path in (ROOT / "03_src",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from outrigger_sim.hydraulics.v5_options import is_extend_start_tag  # noqa: E402

RULES_NAME = "v5_resume_4368_rules.md"
RULES_SHA256 = "9019b405b7a196f28a756e7ca91f443f6241a58bd8e1eee0361483066cb19524"
RECORD_KEY = "resume_k1"
"""``04_scripts/04_hydraulic/coupled/resume_k1_record.RECORD_KEY``."""

F_MIN_N = 9414.589
"""Rules 2 / 7.6: YAML ``control.F_min_cylinder_N``."""
OC5_GUARD_N = 2000.0
"""Rules 7.4 / 7.6: F_min + 2000 N."""
COMPARE_EPS = 1e-9
"""Rules 7.6: threshold comparison allowance (in the unit of the value)."""
R_C_LIMIT = 1.0

TAG_V0 = "final_C4G2_LAS_K1"
TAG_P3 = "final_C4G2_P3_LAS_K1"
TAG_ABL = "ABL_LAS_K1"
TAG_C4_OFF_V0 = "final_C4G2_K1"
TAG_C4_OFF_VB = "final_C4G2_P3_K1"
"""Rules 4.1 tags (IND / IND_LAS keep their names)."""

FORBIDDEN_HARNESS_TOKENS = ("K1on", "K1off", "LASoff", "LASon", "TCL", "P5r4")
"""Rules 4.2: candidate tokens / wrappers that re-apply or change ``C2Config.with_10hz_d1()`` defaults."""
FORBIDDEN_ENV = ("OUTRIGGER_LOC_SHADOW",)
FORBIDDEN_SCM_ENV = ("OUTRIGGER_HULL_HOOK", "OUTRIGGER_HULL_HOOK_ALLOW_UNVALIDATED")
FORBIDDEN_CHRONO_OPTIONS = (
    "--k1-order-gate",
    "--las-off",
    "--las-candidate",
    "--k1-forced-block",
    "--k2",
    "--no-controller-check",
)
FORBIDDEN_SCM_OPTIONS = ("--allow-mixed-hull",)
C4_OFF_ALLOWED = {"--las-off": None, "--k1-order-gate": "on"}
"""Rules 4.2: the C-4 off arm allows exactly ``--las-off`` and ``--k1-order-gate on``."""
PRE_PRESET_RUNNER_PATTERN = re.compile(r"pre_\w*_preset_runner\.py")

LAS_PRESET = {
    "enable": True,
    "sum_on_fraction_W": 0.6,
    "light_leg_fraction_of_F_min": 3.5,
    "slow_mean_fraction": 0.16,
    "sum_off_fraction_W": 0.85,
    "off_periods": 5,
    "max_s": 1.5,
    "rho_on": 0.18,
    "require_soil_response": True,
}
"""The 9 LAS-b preset values (run_S9 ``_LAS_EXPECTATIONS``; ``C2Config().with_10hz_d1()``, tested)."""

UNIFORM_D1_GROUPS = ("H-S-0", "H-S-1")
"""Rules 7.2: the uniform soft-soil D-1 families (no patch, no prescribed sink)."""
EVENT_PATTERN = re.compile(r"C2Event\(t_s=([-+0-9.eEinfa]+), name='([^']*)'\)")
"""``repr(C2Event)`` as ``controller_events.json`` stores it (a list of strings)."""
APPLIED_EVENT_PREFIX = "INFO_LOC_FLAT_SOIL_MARGIN:"
SOIL_MODE_START_EVENT = "soil_mode_start"


class InputError(Exception):
    """A missing or unreadable input (exit code 2)."""


# -------------------------------------------------------------------------------------------
# reading
def read_json(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"{path}: {exc}") from exc


def read_records(path: Path) -> list[dict]:
    """The top-level records of a jsonl file (one per line) or of a JSON file (the document)."""
    path = Path(path)
    if path.suffix == ".jsonl":
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise InputError(f"{path}: {exc}") from exc
        return [json.loads(line) for line in lines if line.strip()]
    return [read_json(path)]


def record_block(record: dict) -> Any:
    """The :data:`RECORD_KEY` block of a run record: top level (run_v5 lines, r79 / grid results) or under ``v5``
    (U-3 / U-6 screen records, ``v5_rerun.run_record``); None without one."""
    if RECORD_KEY in record:
        return record[RECORD_KEY]
    v5 = record.get("v5")
    return v5.get(RECORD_KEY) if isinstance(v5, dict) else None


def _is_run_record(node: dict) -> bool:
    v5 = node.get("v5")
    return RECORD_KEY in node or "job" in node or (isinstance(v5, dict) and RECORD_KEY in v5)


def run_records(node: Any, trail: str = "") -> Iterator[tuple[str, dict]]:
    """(location, run record) for every dict that is a run record at any depth (a grid result keeps its branch
    runs under ``results[i].runs[j]``; a screen record keeps the block under ``v5``)."""
    if isinstance(node, dict):
        if _is_run_record(node):
            yield trail, node
        for key, value in node.items():
            if key in (RECORD_KEY, "v5", "job"):
                continue
            yield from run_records(value, f"{trail}.{key}" if trail else key)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from run_records(value, f"{trail}[{index}]")


def record_key(record: dict) -> str:
    """Identity of a run record: ``job`` (sorted JSON, run_v5 ``job_key``), else ``key`` / ``id`` / ``case``."""
    job = record.get("job")
    if isinstance(job, dict):
        return json.dumps(
            {k: job[k] for k in sorted(job) if k not in ("mask", "t4h_dir")}, sort_keys=True
        )
    for name in ("key", "id", "case"):
        if record.get(name) is not None:
            controller = record.get("controller")
            return f"{record[name]}|{controller}" if controller else str(record[name])
    return "<no key>"


def get_path(node: Any, dotted: str) -> tuple[bool, Any]:
    """(present, value) of a dotted key path."""
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return False, None
        node = node[part]
    return True, node


def _token_hits(text: str, tokens: tuple[str, ...]) -> list[str]:
    return [
        token
        for token in tokens
        if re.search(rf"(^|[^A-Za-z0-9]){re.escape(token)}($|[^A-Za-z0-9])", text)
    ]


# -------------------------------------------------------------------------------------- record
# check
def harness_record_problems(record: dict) -> list[str]:
    """Rules 4.2 record check of one harness run (the ``resume_k1`` block, the key tokens)."""
    problems = [
        f"forbidden token {token!r} in the run key"
        for token in _token_hits(record_key(record), FORBIDDEN_HARNESS_TOKENS)
    ]
    block = record_block(record)
    if not isinstance(block, dict):
        return [*problems, f"{RECORD_KEY} block missing"]
    if block.get("applicable") is False:
        return problems
    expected = {"k1_order_gate_request": "preset", "k1_order_gate_effective": True}
    for name, want in expected.items():
        if block.get(name) != want:
            problems.append(f"{name} {block.get(name)!r} != {want!r}")
    _, gate = get_path(block, "slope_clearance_margin.settings.flat_soil_margin_order_gate")
    if gate is not True:
        problems.append(f"flat_soil_margin_order_gate {gate!r} != True")
    _, settings = get_path(block, "liftoff_approach_slow.settings")
    problems += _las_setting_problems(settings, expect_on=True)
    return problems


def _las_setting_problems(settings: Any, *, expect_on: bool) -> list[str]:
    if not isinstance(settings, dict):
        return ["liftoff_approach_slow.settings missing"]
    if not expect_on:
        return (
            []
            if settings.get("enable") is False
            else [f"LAS-b enable {settings.get('enable')!r} != False"]
        )
    problems = []
    for name, want in LAS_PRESET.items():
        got = settings.get(name)
        same = (
            (got is want)
            if isinstance(want, bool)
            else (
                isinstance(got, (int, float))
                and not isinstance(got, bool)
                and math.isclose(got, want, rel_tol=1e-12)
            )
        )
        if not same:
            problems.append(f"liftoff_approach_slow.settings.{name} {got!r} != {want!r}")
    return problems


def argv_option_value(argv: list[str], option: str) -> tuple[bool, str | None]:
    if option not in argv:
        return False, None
    index = argv.index(option)
    value = (
        argv[index + 1] if index + 1 < len(argv) and not argv[index + 1].startswith("--") else None
    )
    return True, value


def chrono_argv_problems(argv: list[str], env: dict, *, is_c4_off: bool, is_scm: bool) -> list[str]:
    """Rules 4.2 forbidden options / env / runners of one Chrono row (``batch.json`` argv + start env)."""
    problems = []
    for option in FORBIDDEN_CHRONO_OPTIONS + (FORBIDDEN_SCM_OPTIONS if is_scm else ()):
        present, value = argv_option_value(argv, option)
        if not present:
            continue
        if is_c4_off and option in C4_OFF_ALLOWED and C4_OFF_ALLOWED[option] in (None, value):
            continue
        problems.append(f"forbidden option {option}" + ("" if value is None else f" {value}"))
    if is_c4_off:
        for option, want in C4_OFF_ALLOWED.items():
            present, value = argv_option_value(argv, option)
            if not present or (want is not None and value != want):
                problems.append(
                    f"C-4 off arm needs {option}" + ("" if want is None else f" {want}")
                )
    if any(PRE_PRESET_RUNNER_PATTERN.search(str(token)) for token in argv):
        problems.append("pre_*_preset_runner.py in the argv")
    for name in FORBIDDEN_ENV + (FORBIDDEN_SCM_ENV if is_scm else ()):
        if name in env:
            problems.append(f"forbidden env {name}={env[name]!r}")
    return problems


def chrono_result_problems(result: dict, *, is_c4_off: bool) -> list[str]:
    """Rules 4.2 record check of one Chrono ``result.json``."""
    problems = []
    want_request = "on" if is_c4_off else "preset"
    checks = {
        "c2_setup.k1_order_gate": want_request,
        "c2_setup.k1_order_gate_effective": True,
        "controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate": True,
    }
    for dotted, want in checks.items():
        present, got = get_path(result, dotted)
        if not present or got != want:
            problems.append(f"{dotted} {got!r} != {want!r}" + ("" if present else " (missing)"))
    present, las_off = get_path(result, "c2_setup.las_off")
    if is_c4_off and las_off is not True:
        problems.append(f"c2_setup.las_off {las_off!r} != True")
    if not is_c4_off and present and las_off:
        problems.append("c2_setup.las_off true outside the C-4 off arm")
    _, settings = get_path(result, "controller_meta.liftoff_approach_slow.settings")
    return problems + _las_setting_problems(settings, expect_on=not is_c4_off)


def _batch_rows(batch_dir: Path) -> dict[str, dict]:
    doc = read_json(batch_dir / "batch.json")
    return {row["case"]: row for row in doc.get("cases", [])}


def _is_scm_row(row: dict) -> bool:
    argv = [str(token) for token in row.get("argv", [])]
    return any(token.endswith("run_S9.py") for token in argv) and "level" in argv


def _is_c4_off(row: dict) -> bool:
    """The C-4 off arm (rules 4.1): the row expects ``final_C4G2_P3_K1`` / ``final_C4G2_K1``."""
    return row.get("controller") in (TAG_C4_OFF_V0, TAG_C4_OFF_VB)


def record_check(args: argparse.Namespace) -> dict:
    harness = []
    for path in args.harness or []:
        for record_doc in read_records(path):
            for where, record in run_records(record_doc):
                problems = harness_record_problems(record)
                harness.append(
                    {
                        "file": str(path),
                        "where": where,
                        "key": record_key(record),
                        "problems": problems,
                    }
                )
    chrono = []
    for batch_dir in args.chrono or []:
        for case, row in _batch_rows(Path(batch_dir)).items():
            env = {**(row.get("start_env") or {}), **(row.get("run_env") or {})}
            is_c4_off, is_scm = _is_c4_off(row), _is_scm_row(row)
            problems = chrono_argv_problems(
                [str(t) for t in row.get("argv", [])], env, is_c4_off=is_c4_off, is_scm=is_scm
            )
            result_path = Path(batch_dir) / case / "result.json"
            if result_path.is_file():
                problems += chrono_result_problems(read_json(result_path), is_c4_off=is_c4_off)
            else:
                problems.append("result.json missing")
            chrono.append(
                {
                    "batch": str(batch_dir),
                    "case": case,
                    "c4_off_arm": is_c4_off,
                    "problems": problems,
                }
            )
    bad = sum(bool(r["problems"]) for r in harness + chrono)
    return {
        "rules": RULES_NAME,
        "section": "4.2",
        "harness_runs": len(harness),
        "chrono_rows": len(chrono),
        "rows_with_problems": bad,
        "stop_S3": bad > 0,
        "harness": [r for r in harness if r["problems"]] if not args.all else harness,
        "chrono": chrono,
        "exit_code": 1 if bad else 0,
    }


# -------------------------------------------------------------------------------------------- 7.2
CLASS_INACTIVE = "미작동"
CLASS_LAS = "LAS-b 작동"
CLASS_K1 = "K1 막힘"
CLASS_K1_UNIFORM = "K1 막힘 — 균일 연약 지면 계열"
CLASS_BOTH = "둘 다"
CLASS_UNDECIDABLE = "판정 불가"
CLASS_NOT_APPLICABLE = "해당 없음(C2 없음)"
CLASS_NO_LAS = "LAS 없음"
"""436.8 user decision Q-6 (2026-11-13): a run with LAS-b off (the C-4 off arm, ``--las-off``) has no
``liftoff_approach_slow.start_s``; it is this class, not 판정 불가. ``k1_state`` keeps its K1 side and
``las_absent_basis`` the keys the class came from (a rule reading the judgement discloses)."""
K1_STATE_INACTIVE = "미작동"
K1_STATE_BLOCKED = "K1 막힘"
K1_STATE_OUTSIDE = "분류 밖"
LAS_ENABLE_PATH = "liftoff_approach_slow.settings.enable"


def las_absence_basis(block: dict, las_off_flag: Any = None) -> dict[str, Any] | None:
    """The keys that show LAS-b off (Q-6): ``args.las_off`` true (Chrono ``result.json``) and / or
    ``liftoff_approach_slow.settings.enable`` false; None when neither holds."""
    basis: dict[str, Any] = {}
    if las_off_flag is True:
        basis["args.las_off"] = True
    present, enable = get_path(block, LAS_ENABLE_PATH)
    if present and enable is False:
        basis[LAS_ENABLE_PATH] = False
    return basis or None


def classification_inputs(block: Any, las_off_flag: Any = None) -> tuple[dict | None, str | None]:
    """(inputs, None) or (None, reason) of the 7.2 keys of a ``resume_k1`` block / Chrono ``controller_meta``;
    ``las_off_flag``: Chrono ``result.json`` ``args.las_off`` (Q-6)."""
    if not isinstance(block, dict):
        return None, f"{RECORD_KEY} block missing"
    las_absent = las_absence_basis(block, las_off_flag)
    present, start_s = get_path(block, "liftoff_approach_slow.start_s")
    if not present and las_absent is None:
        return None, "liftoff_approach_slow.start_s missing"
    present, decisions = get_path(block, "slope_clearance_margin.order_gate.decisions")
    if not present or not isinstance(decisions, list):
        return None, "slope_clearance_margin.order_gate.decisions missing"
    for index, decision in enumerate(decisions):
        missing = [
            k for k in ("would_block", "r4_due_without_gate", "applied") if k not in decision
        ]
        if missing:
            return None, f"decisions[{index}] without {missing}"
    return {"start_s": start_s, "decisions": decisions, "las_absent": las_absent}, None


def _k1_state(decisions: list[dict], blocked: list[dict]) -> str:
    if not any(d["would_block"] for d in decisions):
        return K1_STATE_INACTIVE
    return K1_STATE_BLOCKED if blocked else K1_STATE_OUTSIDE


def classify(inputs: dict) -> tuple[str, dict]:
    """(class, facts) of rules 7.2 from :func:`classification_inputs` (family not yet applied)."""
    decisions = inputs["decisions"]
    is_las_active = inputs["start_s"] is not None
    blocked = [d for d in decisions if d["would_block"] and d["r4_due_without_gate"]]
    facts = {
        "las_start_s": inputs["start_s"],
        "decisions": len(decisions),
        "blocked": len(blocked),
        "applied_and_would_block": sum(bool(d["applied"] and d["would_block"]) for d in decisions),
    }
    if inputs.get("las_absent") is not None:  # Q-6: LAS-b off, its K1 side kept apart
        return CLASS_NO_LAS, {**facts, "las_absent_basis": inputs["las_absent"],
                              "k1_state": _k1_state(decisions, blocked)}
    if not is_las_active and not any(d["would_block"] for d in decisions):
        return CLASS_INACTIVE, facts
    if is_las_active and blocked:
        return CLASS_BOTH, facts
    if is_las_active:
        return CLASS_LAS, facts
    if blocked:
        return CLASS_K1, facts
    return CLASS_UNDECIDABLE, {
        **facts,
        "reason": "would_block without r4_due_without_gate (outside 7.2)",
    }


def harness_family(record: dict) -> str | None:
    """``uniform`` / ``patch_or_sink`` of a D-1 line (``job.d1.group``); None when the record names no family."""
    present, group = get_path(record, "job.d1.group")
    if not present:
        return None
    return "uniform" if group in UNIFORM_D1_GROUPS else "patch_or_sink"


def chrono_family(row: dict) -> str | None:
    """``uniform`` for a run_S9 SCM row without patch / rigid base / soil event; ``rigid`` for L2b / L1-R rows."""
    argv = [str(token) for token in row.get("argv", [])]
    if not _is_scm_row(row):
        return "rigid"
    if any(option in argv for option in ("--soil-patch", "--rigid-base", "--soil-event")):
        return "patch_or_sink"
    return "uniform"


def _anchor_hashes(paths: list[Path]) -> dict[str, str]:
    """Key -> ``commands_sha256`` of the anchor files, the first file that has a key wins."""
    out: dict[str, str] = {}
    for path in paths:
        for doc in read_records(path):
            for _, record in run_records(doc):
                sha = record.get("commands_sha256")
                if sha is not None:
                    out.setdefault(record_key(record), sha)
    return out


def _class_row(
    key: str,
    block: Any,
    family: str | None,
    sha: str | None,
    skipped: int | None,
    anchors: dict[str, str],
    las_off_flag: Any = None,
) -> dict:
    inputs, reason = classification_inputs(block, las_off_flag)
    if inputs is None:
        return {"key": key, "class": CLASS_UNDECIDABLE, "reason": reason, "stops": []}
    klass, facts = classify(inputs)
    stops = []
    if facts["applied_and_would_block"]:
        stops.append("S-5 applied and would_block together")
    if klass == CLASS_NO_LAS and facts["k1_state"] == K1_STATE_OUTSIDE:
        stops.append("would_block without r4_due_without_gate (outside 7.2, 판정 불가)")
    is_blocked = klass in (CLASS_K1, CLASS_BOTH) or (
        klass == CLASS_NO_LAS and facts["k1_state"] == K1_STATE_BLOCKED)
    if is_blocked and skipped is not None and skipped != facts["blocked"]:
        stops.append(f"S-5 _SKIPPED:order events {skipped} != blocked decisions {facts['blocked']}")
    if is_blocked and skipped is None:
        stops.append("_SKIPPED:order event count unreadable (판정 불가)")
    if is_blocked and family == "uniform":
        klass = CLASS_K1_UNIFORM if klass == CLASS_K1 else klass
        stops.append("S-6 K1 block on a uniform soft-soil family")
    elif is_blocked and family is None:
        stops.append("S-6 family unresolved (rules 7.2 names the family, the record does not)")
    hash_check = None
    if klass == CLASS_INACTIVE and key in anchors:
        hash_check = {"anchor": anchors[key], "run": sha, "same": sha == anchors[key]}
        if not hash_check["same"]:
            stops.append("S-5 미작동 run hash differs from its anchor")
    return {
        "key": key,
        "class": klass,
        "family": family,
        **facts,
        "skipped_order_events": skipped,
        "hash_check": hash_check,
        "stops": stops,
    }


def k1_class(args: argparse.Namespace) -> dict:
    anchors = _anchor_hashes([Path(p) for p in args.anchor or []])
    rows = []
    for path in args.harness or []:
        for doc in read_records(path):
            for _, record in run_records(doc):
                block = record_block(record)
                if isinstance(block, dict) and block.get("applicable") is False:
                    rows.append(
                        {"key": record_key(record), "class": CLASS_NOT_APPLICABLE, "stops": []}
                    )
                    continue
                _, skipped = get_path(block, "event_counts.flat_soil_margin_skipped_order")
                sha = (
                    record.get("commands_sha256")
                    or get_path(record, "v5.logged_commands_sha256")[1]
                )
                rows.append(
                    {
                        "file": str(path),
                        **_class_row(
                            record_key(record), block, harness_family(record), sha, skipped, anchors
                        ),
                    }
                )
    for batch_dir in args.chrono or []:
        for case, row in _batch_rows(Path(batch_dir)).items():
            result_path = Path(batch_dir) / case / "result.json"
            if not result_path.is_file():
                rows.append(
                    {
                        "batch": str(batch_dir),
                        "key": case,
                        "class": CLASS_UNDECIDABLE,
                        "reason": "result.json missing",
                        "stops": [],
                    }
                )
                continue
            result = read_json(result_path)
            names = [str(e.get("name")) for e in result.get("events") or [] if isinstance(e, dict)]
            skipped = sum(name == "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order" for name in names)
            rows.append(
                {
                    "batch": str(batch_dir),
                    **_class_row(
                        case,
                        result.get("controller_meta"),
                        chrono_family(row),
                        None,
                        skipped,
                        anchors,
                        las_off_flag=get_path(result, "args.las_off")[1],
                    ),
                }
            )
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["class"]] = counts.get(row["class"], 0) + 1
    stops = [row for row in rows if row["stops"]]
    return {
        "rules": RULES_NAME,
        "section": "7.2",
        "runs": len(rows),
        "counts": counts,
        "undecidable": counts.get(CLASS_UNDECIDABLE, 0),
        "anchors": len(anchors),
        "hash_checked": sum(row.get("hash_check") is not None for row in rows),
        "stops": stops,
        "rows": rows if args.all else [r for r in rows if r["class"] != CLASS_INACTIVE],
        "exit_code": 1 if stops or counts.get(CLASS_UNDECIDABLE) else 0,
    }


# -------------------------------------------------------------------------------------------- 7.3
def parse_controller_events(items: Any) -> tuple[list[tuple[float, str]] | None, list[str]]:
    """``controller_events.json`` (a list of ``repr(C2Event)`` strings, or of ``{t_s, name}`` dicts) as
    (t_s, name) pairs; (None, unreadable items) when any item does not parse."""
    if not isinstance(items, list):
        return None, ["not a list"]
    events, bad = [], []
    for item in items:
        if isinstance(item, dict) and "name" in item:
            events.append((float(item.get("t_s", math.nan)), str(item["name"])))
            continue
        match = EVENT_PATTERN.fullmatch(str(item)) if isinstance(item, str) else None
        if match is None:
            bad.append(str(item)[:120])
            continue
        events.append((float(match.group(1)), match.group(2)))
    return (None, bad) if bad else (events, [])


def jp_row_conditions(events: list[tuple[float, str]]) -> dict:
    """Rules 7.3 condition 2 of one row: R4c30 applied events and soil-mode starts."""
    applied = [name for _, name in events if name.startswith(APPLIED_EVENT_PREFIX)]
    soil = [name for _, name in events if name == SOIL_MODE_START_EVENT]
    return {
        "events": len(events),
        "flat_soil_margin_applied": len(applied),
        "soil_mode_start": len(soil),
        "k1_no_effect": not applied and not soil,
    }


def jp_reuse(args: argparse.Namespace) -> dict:
    shadow = {}
    for record in read_records(Path(args.shadow)):
        for _, line in run_records(record):
            run = get_path(line, "job.chrono_run")[1]
            if run is not None:
                shadow[str(run).replace("\\", "/")] = line
    rows = []
    for folder in args.rows:
        folder = Path(folder)
        run_id = f"{folder.parent.name}/{folder.name}"
        line = shadow.get(run_id)
        silent = (
            line is not None
            and line.get("status") == "silent"
            and line.get("first_fire_t_s") is None
        )
        path = folder / "controller_events.json"
        events, bad = (
            parse_controller_events(read_json(path)) if path.is_file() else (None, ["file missing"])
        )
        condition2 = None if events is None else jp_row_conditions(events)
        rows.append(
            {
                "row": run_id,
                "shadow_status": None if line is None else line.get("status"),
                "condition1_shadow_silent": silent,
                "condition2": condition2,
                "condition3_readable": events is not None,
                "unreadable": bad[:5],
                "reusable": bool(silent and condition2 and condition2["k1_no_effect"]),
            }
        )
    is_reuse = len(rows) == args.expected and all(row["reusable"] for row in rows)
    return {
        "rules": RULES_NAME,
        "section": "7.3",
        "rows": rows,
        "expected_rows": args.expected,
        "reuse": is_reuse,
        "decision": "재사용" if is_reuse else "묶음 JP 재실행",
        "exit_code": 0 if is_reuse else 1,
    }


# -------------------------------------------------------------------------------------------- 7.4
def is_less(value: float, limit: float) -> bool:
    """Rules 7.6: ``v < X`` is true when ``v < X - 1e-9``."""
    return value < limit - COMPARE_EPS


def oc5_class(m_N: float) -> str:
    """Rules 7.4 table: ``stop_S9`` / ``record_with_margin`` / ``record``."""
    if is_less(m_N, F_MIN_N):
        return "stop_S9"
    if is_less(m_N, F_MIN_N + OC5_GUARD_N):
        return "record_with_margin"
    return "record"


def oc5(args: argparse.Namespace) -> dict:
    result = read_json(Path(args.result))
    keys = {
        "F_min_after_N": "p3b.P3-3_leg_force.F_min_after_N",
        "F_min_transient_N": "p3b.P3-3_leg_force.F_min_transient_N",
        "t_min_after_s": "p3b.P3-3_leg_force.t_min_after_s",
        "within": "p3b.P3-3_leg_force.within",
        "R_c_operating": "p3b_ext.start_condition.R_c_operating",
        "crawler_attitude_deg": "p3b_ext.start_condition.crawler_attitude_deg",
        "floor_roll_deg": "args.floor_roll",
        "floor_pitch_deg": "args.floor_pitch",
        "las_start_s": "controller_meta.liftoff_approach_slow.start_s",
        "las_end_s": "controller_meta.liftoff_approach_slow.end_s",
        "las_end_reason": "controller_meta.liftoff_approach_slow.end_reason",
        "k1_decisions": "controller_meta.slope_clearance_margin.order_gate.decisions",
    }
    values, missing = {}, []
    for name, dotted in keys.items():
        present, value = get_path(result, dotted)
        values[name] = value
        if not present:
            missing.append(dotted)
    out = {
        "rules": RULES_NAME,
        "section": "7.4",
        "result": str(args.result),
        "values": values,
        "missing": missing,
        "time_below_note": "F<F_min / F<F_min+2 kN durations are not in result.json "
        "(path 2 recomputes them from the run_S9 series files step_series.npz / r8_series.npz; the "
        "rules text says series.npz, 9.1)",
    }
    r_c, forces = values["R_c_operating"], values["F_min_after_N"]
    if r_c is None or not isinstance(forces, list) or len(forces) != 4:
        return {**out, "status": "판정 불가", "exit_code": 1}
    if r_c > R_C_LIMIT + COMPARE_EPS:
        return {**out, "status": "R_c > 1: O-C5로 읽지 않음 (S-10, 묻는다)", "exit_code": 1}
    m_N = min(float(f) for f in forces)
    klass = oc5_class(m_N)
    return {
        **out,
        "m_N": m_N,
        "min_leg": ["FL", "FR", "RL", "RR"][forces.index(min(forces))],
        "margin_N": m_N - F_MIN_N,
        "class": klass,
        "status": "기록",
        "exit_code": 1 if klass == "stop_S9" else 0,
    }


# ------------------------------------------------------------------------------------------- 11.1
def expected_harness_tag(setting: str | None, controller: str | None = None) -> str | None:
    """Rules 4.1 tag of a harness run by setting / controller name (None: no tag check, e.g. IND)."""
    if controller in ("IND", "IND_LAS"):
        return controller
    if controller == "ABL":
        return TAG_ABL
    if setting is None:
        return None
    return TAG_P3 if setting.startswith(("VB", "LS")) else TAG_V0


def steps_overlap_rows(steps_doc: dict) -> list[dict]:
    """Rules 11.1 rows of a steps file (``resume_k1_steps.py``): bundle, step, env, forbidden hits."""
    rows = []
    for step in steps_doc.get("steps", []):
        cmd = str(step.get("cmd", ""))
        env = step.get("env") or {}
        hits = _token_hits(cmd, FORBIDDEN_HARNESS_TOKENS) + [
            f"env {n}" for n in FORBIDDEN_ENV if n in env
        ]
        hits += ["pre_*_preset_runner.py"] if PRE_PRESET_RUNNER_PATTERN.search(cmd) else []
        hits += ["scratchpad script"] if "scratchpad" in cmd.lower() else []
        meta = step.get("resume_k1") or {}
        rows.append(
            {
                "bundle": meta.get("bundle"),
                "step": step.get("id"),
                "kind": "harness",
                "preset": "C2Config().with_10hz_d1() (no override)",
                "settings": meta.get("settings"),
                "expected_tags": meta.get("expected_tags"),
                "output": meta.get("output"),
                "env": sorted(env),
                "forbidden": hits,
            }
        )
    return rows


def chrono_overlap_rows(batch_doc: dict, batch_name: str) -> list[dict]:
    rows = []
    cases = batch_doc if isinstance(batch_doc, list) else batch_doc.get("cases", [])
    for row in cases:
        argv = [str(t) for t in row.get("argv", [])]
        env = {**(row.get("start_env") or {}), **(row.get("run_env") or {})}
        controller = row.get("controller")
        hits = chrono_argv_problems(argv, env, is_c4_off=_is_c4_off(row), is_scm=_is_scm_row(row))
        expect = argv_option_value(argv, "--expect-controller")[1]
        if expect is not None and expect != controller:
            hits.append(f"--expect-controller {expect} != row controller {controller}")
        rows.append(
            {
                "bundle": row.get("criteria_id") or batch_name,
                "step": row.get("case"),
                "kind": "chrono",
                "preset": "C2Config().with_10hz_d1()",
                "expected_tag": controller,
                "extend_start": None if controller is None else is_extend_start_tag(controller),
                "start_env": env,
                "forbidden": hits,
            }
        )
    return rows


def overlap(args: argparse.Namespace) -> dict:
    rows = []
    for path in args.steps or []:
        rows += steps_overlap_rows(read_json(Path(path)))
    for path in args.batch or []:
        rows += chrono_overlap_rows(read_json(Path(path)), Path(path).parent.name)
    bad = [row for row in rows if row["forbidden"]]
    return {
        "rules": RULES_NAME,
        "section": "11.1",
        "rows": rows,
        "rows_with_findings": len(bad),
        "exit_code": 1 if bad else 0,
    }


# ------------------------------------------------------------------------------------------- 11.2
HARNESS_GS_KEYS = (
    f"{RECORD_KEY}.applicable",
    f"{RECORD_KEY}.k1_order_gate_request",
    f"{RECORD_KEY}.k1_order_gate_effective",
    f"{RECORD_KEY}.slope_clearance_margin.settings.flat_soil_margin_order_gate",
    f"{RECORD_KEY}.liftoff_approach_slow.settings",
    f"{RECORD_KEY}.liftoff_approach_slow.start_s",
    f"{RECORD_KEY}.slope_clearance_margin.order_gate.decisions",
    f"{RECORD_KEY}.event_counts.flat_soil_margin_skipped_order",
    "controller_tag",
)
"""Rules 11.2: the 4.2 / 7.2 key paths a harness run must carry (the tag key is ``controller_tag`` on run_v5
lines, ``v5.controller_tag`` on the screen records: either counts)."""
TAG_KEY_ALTERNATIVES = ("controller_tag", "v5.controller_tag")


def gs_presence(record: dict) -> dict[str, bool]:
    """Key path -> present for one run record. A block of a controller without a C2 configuration
    (``applicable`` False, IND / IND_LAS) needs ``applicable`` only; a grid branch run (no own key)
    inherits the
    tag of its job record, so the tag key is required only on records that name themselves."""
    view = {RECORD_KEY: record_block(record)}
    is_c2 = get_path(view, f"{RECORD_KEY}.applicable")[1] is not False
    names_itself = any(name in record for name in ("job", "key", "id", "case"))
    presence = {}
    for dotted in HARNESS_GS_KEYS:
        if dotted == "controller_tag":
            if names_itself and is_c2:
                presence[dotted] = any(get_path(record, alt)[0] for alt in TAG_KEY_ALTERNATIVES)
        elif is_c2 or dotted == f"{RECORD_KEY}.applicable":
            presence[dotted] = get_path(view, dotted)[0]
    return presence


def gs(args: argparse.Namespace) -> dict:
    files = []
    for path in args.harness:
        runs = [record for doc in read_records(Path(path)) for _, record in run_records(doc)]
        if not runs:
            files.append({"file": str(path), "runs": 0, "missing": ["<no run record>"]})
            continue
        missing = sorted(
            {key for record in runs for key, ok in gs_presence(record).items() if not ok}
        )
        files.append({"file": str(path), "runs": len(runs), "missing": missing})
    bad = [f for f in files if f["missing"]]
    return {
        "rules": RULES_NAME,
        "section": "11.2",
        "files": files,
        "files_with_missing": len(bad),
        "exit_code": 1 if bad else 0,
    }


# --------------------------------------------------------------------------------------------- main
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name, helptext in (("record-check", "4.2"), ("k1-class", "7.2")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--harness", nargs="*", type=Path, help="harness jsonl / json outputs")
        p.add_argument(
            "--chrono", nargs="*", type=Path, help="Chrono batch folders (batch.json + <case>/)"
        )
        p.add_argument("--all", action="store_true", help="list every run, not only the findings")
        p.add_argument("--out", type=Path, required=True)
        if name == "k1-class":
            p.add_argument(
                "--anchor", nargs="*", type=Path, help="hash anchor files (first match wins)"
            )
    p = sub.add_parser("jp-reuse", help="7.3")
    p.add_argument("--shadow", type=Path, required=True, help="v5/las/shadow_jp_b0.jsonl")
    p.add_argument(
        "--rows", nargs="+", type=Path, required=True, help="07_results/S8/v5jp_*/<case> folders"
    )
    p.add_argument("--expected", type=int, default=12)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("oc5", help="7.4 path 1")
    p.add_argument("--result", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("overlap", help="11.1")
    p.add_argument("--steps", nargs="*", type=Path, help="steps files of resume_k1_steps.py")
    p.add_argument(
        "--batch", nargs="*", type=Path, help="Chrono batch.json files (or s9_batch list JSON)"
    )
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("gs", help="11.2 (key presence only)")
    p.add_argument("--harness", nargs="+", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    return parser


COMMANDS = {
    "record-check": record_check,
    "k1-class": k1_class,
    "jp-reuse": jp_reuse,
    "oc5": oc5,
    "overlap": overlap,
    "gs": gs,
}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = COMMANDS[args.command](args)
    except InputError as exc:
        print(json.dumps({"exit_code": 2, "error": str(exc)}, ensure_ascii=True))
        return 2
    except Exception as exc:  # report the failure in the contract form, keep the trace
        print(traceback.format_exc(), file=sys.stderr)
        print(json.dumps({"exit_code": 3, "error": repr(exc)}, ensure_ascii=True))
        return 3
    report["rules_sha256"] = RULES_SHA256
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8"
    )
    summary = {
        k: report[k] for k in report if not isinstance(report[k], (list, dict)) or k == "counts"
    }
    print(json.dumps(summary, ensure_ascii=True, default=str))
    return int(report["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
