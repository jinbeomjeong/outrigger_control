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

Rev1 (``v5_resume_4368_rules_rev1.md``, sealed d9094fda; every subcommand first checks the rev1
file and its ``.sha256`` and stops with S-1 when either is missing or differs):
  keyset         RV1-3: key set (and grid ``runs[]`` / meta) of a new H-6 .. H-9 grid output vs
                 its appendix B source (S-15)
  dg3-hash       RV1-3.2: H-6 vs H-8 VB ``base.commands_sha256`` per key (record)
  anchor-map     RV1-5: P-1 / P-2 anchor lines by ``run_v5.job_key`` (S-7), H-1 hash pairs;
                 its report is the ``k1-class --anchor-map`` input
  import-check   RV1-9: no ``loc_anchor_shadow`` (or a runner that installs it) on the import
                 path of the step runners, no ``OUTRIGGER_LOC_SHADOW`` in a step env
  fmin-time      RV1-7: 7.4 ``F<F_min`` / ``F<F_min+2 kN`` times from ``step_series.npz``
  stroke-exposure RV1-10 j: lines / rows with max stroke >= 678 / 684.8 mm (s_ref and piston)
                 and with ``FAULT_STROKE_END`` (record; a missing coordinate is "기록 없음")
  ``k1-class --family-table`` reads the RV1-6 table of ``resume_k1_family.py`` (a key it does
  not place counts as uniform soft soil: a K1 block there is S-6).

Rev2 (``v5_resume_4368_rules_rev2.md``, sealed 497e4614, also checked raw before every
subcommand): R2-1 a ``would_block`` / ``applied`` decision without ``r4_due_without_gate`` is a
record conflict (line 판정 불가, S-5); R2-2 a LAS-b block without ``start_s`` = not started, no
block = 판정 불가; R2-3 L2b / L1-R results are read from ``controller_meta``; R2-5 ``fmin-time``
finds t_D in ``step_series.npz``; R2-6 ``oc5`` gives the path 1 processing cell; R2-7 grid lines
(``runs[]``) get their family from ``meta.spec`` + ``event``; R2-9 ``appendix-a`` compares the
original appendix A raw, else CRLF -> LF normalised (disclosed).

Exit codes: 0 no finding, 1 a finding (stop condition, mismatch, missing key), 2 input error, 3
internal error.
The tool reads only; it never runs a simulation. Tag judgements use
``v5_options.is_extend_start_tag`` only.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
import sys
import traceback
from collections import Counter
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
RULES_DIR = HERE.parent
RULES_REV1_NAME = "v5_resume_4368_rules_rev1.md"
RULES_REV1_SHA256 = "d9094fda104e25ac7eb7aea44d7c34d8215a839fc3771aa50b224d43082f02c7"
"""Rev1 (sealed 2026-11-13 01:49:34 +09:00): it overrides the original where they differ. Every
subcommand checks the sealed file and its ``.sha256`` first (missing or other value = S-1)."""
RULES_REV2_NAME = "v5_resume_4368_rules_rev2.md"
RULES_REV2_SHA256 = "497e4614d6780c3201027b3946e3c21da05e2fefe9a3609436bc35ea664c3199"
"""Rev2 (sealed 2026-11-13 02:30:11 +09:00): overrides rev1 and the original where they differ."""
SEALED_REVISIONS = ((RULES_REV1_NAME, RULES_REV1_SHA256), (RULES_REV2_NAME, RULES_REV2_SHA256))
"""The revisions every subcommand checks raw (R2-9: sealed rule files are ``-text``, no LF
normalisation)."""
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


def _own_key(node: dict) -> str | None:
    for name in ("key", "id", "case"):
        if node.get(name) is not None:
            return str(node[name])
    return None


def run_records_owned(node: Any, owner: str | None = None, trail: str = ""
                      ) -> Iterator[tuple[str, dict, str | None]]:
    """:func:`run_records` plus the key of the nearest dict above (or at) the record that names
    itself: a grid branch run (``results[i].runs[j]``) has no key of its own and takes its job's."""
    if isinstance(node, dict):
        owner = _own_key(node) or owner
        if _is_run_record(node):
            yield trail, node, owner
        for key, value in node.items():
            if key in (RECORD_KEY, "v5", "job"):
                continue
            yield from run_records_owned(value, owner, f"{trail}.{key}" if trail else key)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from run_records_owned(value, owner, f"{trail}[{index}]")


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


ENGINE_RUNNERS = ("run_S8C.py", "run_S6C.py")
"""L2b and L1-R runners: their results have no ``c2_setup`` (R2-3)."""


def _is_engine_row(row: dict) -> bool:
    return any(str(token).endswith(ENGINE_RUNNERS) for token in row.get("argv", []))


def engine_result_problems(result: dict) -> list[str]:
    """R2-3 record check of an L2b / L1-R ``result.json``: the K1 request is the argv (checked by
    :func:`chrono_argv_problems`: no ``--k1-order-gate`` = preset), the applied gate
    ``controller_meta.slope_clearance_margin.order_gate.enabled``; a missing key is 판정 불가."""
    problems = []
    checks = {
        "controller_meta.slope_clearance_margin.order_gate.enabled": True,
        "controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate": True,
        "expect_controller.ok": True,  # rev1 RV1-10 a: the row runs with --expect-controller
    }
    for dotted, want in checks.items():
        present, got = get_path(result, dotted)
        if not present:
            problems.append(f"{dotted} missing (판정 불가, R2-3: review S-3)")
        elif got != want:
            problems.append(f"{dotted} {got!r} != {want!r}")
    _, settings = get_path(result, "controller_meta.liftoff_approach_slow.settings")
    return problems + _las_setting_problems(settings, expect_on=True)


def chrono_result_problems(result: dict, *, is_c4_off: bool, is_engine: bool = False
                           ) -> list[str]:
    """Rules 4.2 record check of one Chrono ``result.json`` (L2b / L1-R rows: R2-3)."""
    if is_engine:
        return engine_result_problems(result)
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
                problems += chrono_result_problems(read_json(result_path), is_c4_off=is_c4_off,
                                                   is_engine=_is_engine_row(row))
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
    las_block = block.get("liftoff_approach_slow")
    # R2-2: a LAS-b block (with settings) without start_s = LAS-b not started; no block = 판정 불가
    # (the C-4 off arm needs no block, rev1 RV1-10 b)
    if las_absent is None and not (isinstance(las_block, dict) and "settings" in las_block):
        return None, "liftoff_approach_slow block missing (R2-2)"
    start_s = las_block.get("start_s") if isinstance(las_block, dict) else None
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


def record_conflicts(decisions: list[dict]) -> list[str]:
    """R2-1 record conflicts of ``decisions`` (``would_block`` and ``applied`` both require
    ``r4_due_without_gate``; ``applied`` with ``would_block`` cannot hold with the gate on)."""
    conflicts = []
    for index, decision in enumerate(decisions):
        due = decision["r4_due_without_gate"]
        if decision["would_block"] and not due:
            conflicts.append(f"decisions[{index}] would_block without r4_due_without_gate")
        if decision["applied"] and not due:
            conflicts.append(f"decisions[{index}] applied without r4_due_without_gate")
        if decision["applied"] and decision["would_block"]:
            conflicts.append(f"decisions[{index}] applied and would_block together")
    return conflicts


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
        "reason": "would_block without r4_due_without_gate (record conflict, R2-1: S-5)",
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
    conflicts = record_conflicts(inputs["decisions"])
    if conflicts:  # R2-1: the line is 판정 불가, the bundle stops (S-5)
        return {"key": key, "class": CLASS_UNDECIDABLE, "reason": "record conflict (R2-1)",
                "conflicts": conflicts, "family": family,
                "stops": [f"S-5 record conflict (R2-1): {c}" for c in conflicts]}
    klass, facts = classify(inputs)
    stops = []
    is_blocked = klass in (CLASS_K1, CLASS_BOTH) or (
        klass == CLASS_NO_LAS and facts["k1_state"] == K1_STATE_BLOCKED)
    if is_blocked and skipped is not None and skipped != facts["blocked"]:
        stops.append(f"S-5 _SKIPPED:order events {skipped} != blocked decisions {facts['blocked']}")
    if is_blocked and skipped is None:
        stops.append("_SKIPPED:order event count unreadable (판정 불가)")
    if is_blocked and family in ("uniform", None):  # RV1-6: an unplaced key counts as uniform
        klass = CLASS_K1_UNIFORM if klass == CLASS_K1 else klass
        stops.append("S-6 K1 block on a uniform soft-soil family" if family == "uniform" else
                     "S-6 K1 block on a key the family table does not place (RV1-6: uniform)")
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


FAMILY_TABLE_NAMES = {
    "균일 연약": "uniform",
    "패치·처방 침하": "patch_or_sink",
    "강체": "rigid",
    "해당 없음": "not_applicable",
    "미분류": None,
}
"""``resume_k1_family.py`` families -> the names of :func:`_class_row` (미분류 = None = uniform)."""


def read_family_table(path: Path) -> dict[str, str | None]:
    """Key -> family of a ``resume_k1_family.py`` table (RV1-6)."""
    table = read_json(path)
    try:
        return {str(row["key"]): FAMILY_TABLE_NAMES[row["family"]] for row in table["rows"]}
    except KeyError as exc:
        raise InputError(f"{path}: not a family table ({exc})") from exc


def table_family(record: dict, owner: str | None, table: dict[str, str | None]
                 ) -> tuple[str | None, str]:
    """(family, the key it was found under) of a run; (None, "not in table") without a match."""
    candidates = [record_key(record), _own_key(record), owner]
    for key in candidates:
        if key is not None and key in table:
            return table[key], key
    return None, "not in table"


GRID_SPEC = "rev. 67 (G1 / G2 / G7 reduced screen)"
GRID_FLOOR_EVENTS = ("G4", "RE1bF", "FS24")
"""R2-7: a grid run is 패치·처방 침하 when the file's ``meta.spec`` is this and its ``event`` one of
these; otherwise unplaced (= uniform, a K1 block is S-6)."""


def is_grid_document(document: Any) -> bool:
    results = document.get("results") if isinstance(document, dict) else None
    return bool(results) and all(isinstance(row.get("runs"), list) for row in results)


def grid_lines(document: dict) -> Iterator[tuple[dict, str | None, str | None]]:
    """(run, job key, R2-7 family) of every ``results[].runs[]`` entry: the lines of a grid file
    (the job-level record is the prefix run, no line of its own)."""
    is_spec = (document.get("meta") or {}).get("spec") == GRID_SPEC
    for row in document["results"]:
        for run in row["runs"]:
            family = "patch_or_sink" if is_spec and run.get("event") in GRID_FLOOR_EVENTS else None
            yield run, _own_key(row), family


def read_anchor_map(path: Path) -> dict[str, str]:
    """Key -> anchor ``commands_sha256`` of an ``anchor-map`` report (RV1-5)."""
    report = read_json(path)
    if report.get("problems"):
        raise InputError(f"{path}: anchor map with problems {report['problems'][:3]}")
    return dict(report.get("anchors") or {})


GRID_NOT_A_GRID = "<no grid>"


def _k1_class_lines(document: Any) -> Iterator[tuple[dict, str | None, str | None]]:
    """(run record, owner key, grid family or :data:`GRID_NOT_A_GRID`) of one document."""
    if is_grid_document(document):
        yield from grid_lines(document)
        return
    for _, record, owner in run_records_owned(document):
        yield record, owner, GRID_NOT_A_GRID


def k1_class(args: argparse.Namespace) -> dict:
    anchors = _anchor_hashes([Path(p) for p in args.anchor or []])
    anchor_source = "first match of --anchor files" if anchors else "none"
    if args.anchor_map is not None:  # RV1-5: the selected anchors, one per key
        anchors = read_anchor_map(Path(args.anchor_map))
        anchor_source = f"anchor-map {args.anchor_map}"
    table = None if args.family_table is None else read_family_table(Path(args.family_table))
    rows = []
    for path in args.harness or []:
        for doc in read_records(path):
            for record, owner, grid_family in _k1_class_lines(doc):
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
                if grid_family is not GRID_NOT_A_GRID:
                    family, family_source = grid_family, "R2-7 (meta.spec + event)"
                elif table is None:
                    family, family_source = harness_family(record), "record (job.d1.group)"
                else:
                    family, family_source = table_family(record, owner, table)
                rows.append(
                    {
                        "file": str(path),
                        "owner": owner,
                        "family_source": family_source,
                        **_class_row(
                            record_key(record), block, family, sha, skipped, anchors
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
        "anchor_source": anchor_source,
        "family_table": None if args.family_table is None else {
            "path": str(args.family_table), "sha256": file_sha256(Path(args.family_table))},
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


OC5_PROCESSING = {"stop_S9": "멈춤", "record_with_margin": "여유 기록", "record": "기록"}
"""R2-6: the 7.4 processing cell of a path; the two paths' cells are compared outside this tool
(different cells = 판정 불가, stop and ask)."""


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
        "time_below_note": "F<F_min / F<F_min+2 kN durations are not in result.json: path 1 "
        "computes them with the fmin-time subcommand from step_series.npz (rev1 RV1-7)",
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
        "path": "경로 1 (result.json p3b.P3-3_leg_force.F_min_after_N, R2-6)",
        "processing": OC5_PROCESSING[klass],
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


DG3_P3_ENV = "LAS_T3_DG3_P3"
DG3_LAS_ENV = "LAS_T3_DG3_LAS"
DG3_P3_OFF_BUNDLE = "H-7"
"""RV1-3.2: ``LAS_T3_DG3_P3=off`` (VB without ③) only in H-7; ``LAS_T3_DG3_LAS=off`` nowhere."""


def dg3_switch_problems(env: dict, bundle: str | None) -> list[str]:
    """RV1-3.2 use of the ``las_t3_dg3.py`` switches in one step's env."""
    problems = []
    if env.get(DG3_P3_ENV) == "off" and bundle != DG3_P3_OFF_BUNDLE:
        problems.append(f"env {DG3_P3_ENV}=off outside {DG3_P3_OFF_BUNDLE}")
    if env.get(DG3_LAS_ENV) == "off":
        problems.append(f"env {DG3_LAS_ENV}=off")
    return problems


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
        hits += dg3_switch_problems(env, meta.get("bundle"))
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
                "dg3_switches": {name: env[name] for name in sorted(env)
                                 if name.startswith("LAS_T3_DG3_")},
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
    f"{RECORD_KEY}.liftoff_approach_slow.settings",  # R2-2: no start_s key = not started
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


# ------------------------------------------------------------------------------ rev1 RV1-3 keyset
APPENDIX_B = {
    "dg3/dg3_v4_on.json": "5f912ca0d25d6dfe0114e05bf8c7a083fa542ad3de71e76c472e44a1a351167d",
    "dg3/off/dg3_off.json": "95b81f82d800ae3ccf0dd15e205f12ec4b8795a1dcb482e6e30ed41aa0cfd5ce",
    "noise_vb/r79_VB_L1L2L3.json":
        "d3c9bba1abd3c1fbc700a26527856e14f7754740192c55a404bc203ef8a763b9",
    "noise_v0/r79_V0_L1L2L3.json":
        "af6a7ae51abe4b9094db9b21cf49f8770861fb0ed91cb269effb6b2cab9b459a",
    "seedext/r79_VB_seedext.json":
        "6ddca3d5ce5dc6286c319de13d779bbb419df8fbee2bd13577d04b0f4c2d6f57",
    "seedext/r79_V0_seedext.json":
        "f2c01d65238cac50da57c26ca33541b9506ff50b14aee80d65f31e1378dabaa8",
    "grid_vb/grid_r67_main.json":
        "8ef4237dc7658559efa04ac07edc1641fe422cbb55e5fee902fbac94eac13ef7",
    "grid_vb/grid_r67_top.json": "498aa41199b2e4ed3467573c061ab2d6a182ffcd10871fe9bc7420989e6e6412",
    "grid_vb/grid_r69_bottom.json":
        "ee84750be278a2c284bf1fe614155240c0a4c2b564762862276a007afc9609e9",
    "grid_vb/grid_r69_top.json": "c132fd41f13b8033b25804fbc777408a5d1729f31348af34aadd7fd6dfaad325",
    "d1.jsonl": "9039b36a1a9c4ba5ed63528bb7384773018d4c7377dccbf76b18fbcfda86707f",
    "las/las_T1.jsonl": "3dee4f6b88e71654debd68b3ef5c5f1a9b01f1dba8fcd731d1355ec219d9a85b",
    "las/las_T2.jsonl": "2fe6a54aafdc0c3ffbf1991907ee4e1af85761e1bef2e25bef07dd52ab199efb",
    "las/k1/k1_YP.jsonl": "0d985d5624f0fbb0219ca50d1c839b7db639011d6c2ab14fa9d84cfd197fc2c3",
    "soil_defer/s2d_SC.jsonl": "70e91ec1234d56a918af1b4fc053c3175f0f14ab41e2b5f334890f7dc6cb08aa",
}
"""Rev1 appendix B (files under ``06_analysis/03_hydraulic/coupled/v5/``): a file whose sha256 is
not this value does not start its bundle (S-1 handling)."""
GRID_META_FIELDS = ("offsets_s", "n_jobs", "candidate", "v5_setting")
GRID_EVENT_KEYS = ("event", "offset_s")


def file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError as exc:
        raise InputError(f"{path}: {exc}") from exc


def appendix_b_problems(path: Path) -> tuple[str | None, list[str]]:
    """(appendix B entry, problems) of a stored file: it must be one of :data:`APPENDIX_B` and
    have that sha256."""
    text = str(path).replace("\\", "/")
    entry = next((name for name in APPENDIX_B if text.endswith("/v5/" + name)), None)
    if entry is None:
        return None, [f"{path} is no appendix B file"]
    actual = file_sha256(path)
    if actual != APPENDIX_B[entry]:
        return entry, [f"{entry} sha256 {actual[:16]} != {APPENDIX_B[entry][:16]} (S-1)"]
    return entry, []


def r79_result_keys(document: dict) -> list[str]:
    return [str(row.get("key")) for row in document.get("results") or []]


def grid_branch_ids(document: dict) -> set[tuple]:
    """(job key, event, offset) of every ``runs[]`` entry of a grid file."""
    return {(row.get("key"), *(run.get(name) for name in GRID_EVENT_KEYS))
            for row in document.get("results") or [] for run in row.get("runs") or []}


def set_difference_report(new: list, stored: list) -> dict:
    new_set, stored_set = set(new), set(stored)
    return {"new": len(new), "new_distinct": len(new_set), "stored": len(stored),
            "missing_in_new": sorted(map(str, stored_set - new_set))[:20],
            "extra_in_new": sorted(map(str, new_set - stored_set))[:20],
            "same": new_set == stored_set and len(new) == len(new_set)}


def keyset(args: argparse.Namespace) -> dict:
    """RV1-3.1 / RV1-3.2: key set of a new H-6 .. H-9 grid output against its stored source
    (S-15 when it differs); grid files also compare ``runs[]`` and the meta of RV1-3.2."""
    entry, problems = appendix_b_problems(Path(args.stored))
    stored, new = read_json(Path(args.stored)), read_json(Path(args.new))
    out: dict[str, Any] = {"rules": RULES_REV1_NAME, "section": "RV1-3 (S-15)",
                           "kind": args.kind, "stored": str(args.stored), "appendix_b": entry,
                           "new": str(args.new)}
    keys = set_difference_report(r79_result_keys(new), r79_result_keys(stored))
    out["keys"] = keys
    if not keys["same"]:
        problems.append("job key set differs (S-15)")
    if args.kind == "grid":
        branches = set_difference_report(sorted(grid_branch_ids(new)),
                                         sorted(grid_branch_ids(stored)))
        runs = sum(len(row.get("runs") or []) for row in new.get("results") or [])
        out["runs"] = {"new": runs, **{k: branches[k] for k in ("stored", "missing_in_new",
                                                                  "extra_in_new", "same")}}
        if not branches["same"] or runs != branches["stored"]:
            problems.append("runs[] (key, event, offset) set differs (S-15)")
        meta_new, meta_stored = new.get("meta") or {}, stored.get("meta") or {}
        out["meta"] = {f: {"new": meta_new.get(f), "stored": meta_stored.get(f)}
                       for f in GRID_META_FIELDS}
        problems += [f"meta {f} differs" for f in GRID_META_FIELDS
                     if meta_new.get(f) != meta_stored.get(f)]
    errors = [row.get("key") for row in new.get("results") or [] if "error" in row]
    out["error_rows"] = errors[:20]
    out["n_error_rows"] = len(errors)
    return {**out, "problems": problems, "exit_code": 1 if problems else 0}


def dg3_hash(args: argparse.Namespace) -> dict:
    """RV1-3.2 H-8 dg3 replacement: per H-6 key, whether the H-8 VB line of the same key has the
    same ``base.commands_sha256`` (record; predicted same, never a stop)."""
    h6 = {row.get("key"): row for row in read_json(Path(args.h6)).get("results") or []}
    h8 = {row.get("key"): row for row in read_json(Path(args.h8_vb)).get("results") or []}
    rows = []
    for key, line in h6.items():
        other = h8.get(key)
        sha6 = get_path(line, "base.commands_sha256")[1]
        sha8 = None if other is None else get_path(other, "base.commands_sha256")[1]
        rows.append({"key": key, "h6": sha6, "h8_vb": sha8,
                     "same": None if sha6 is None or sha8 is None else sha6 == sha8})
    differing = [row["key"] for row in rows if row["same"] is False]
    return {"rules": RULES_REV1_NAME, "section": "RV1-3.2 (record)", "keys": len(rows),
            "same": sum(row["same"] is True for row in rows), "differ": len(differing),
            "unreadable": sum(row["same"] is None for row in rows),
            "differing_keys": differing, "rows": rows,
            "note": "a difference is recorded and handed to python-expert; it is no stop",
            "exit_code": 0}


# --------------------------------------------------------------- rev2 R2-9 appendix A (S-1)
APPENDIX_A_HEADING = "## 부록 A."
APPENDIX_A_ROW = re.compile(r"^\| `([^`]+)`[^|]*\| `([0-9a-f]{64})` \|")


def appendix_a_entries(rules_text: str) -> list[tuple[str, str]]:
    """(repository path, sha256) of the original rules' appendix A table; ``…/name`` rows take the
    folder of the row above."""
    lines = rules_text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith(APPENDIX_A_HEADING)), None)
    if start is None:
        raise InputError(f"{RULES_NAME}: no appendix A")
    entries, folder = [], ""
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        match = APPENDIX_A_ROW.match(line)
        if match is None:
            continue
        path, sha256 = match.groups()
        if path.startswith("…/"):
            path = f"{folder}/{path[2:]}"
        folder = path.rsplit("/", 1)[0]
        entries.append((path, sha256))
    return entries


def lf_normalised_sha256(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def appendix_a(args: argparse.Namespace) -> dict:
    """R2-9: appendix A files by raw sha256, else by the sha256 of the bytes with every CRLF made
    LF (pass, disclosed as "CRLF 변환만 다름"); a file that differs also then is S-1."""
    root = Path(args.root)
    rules_text = (RULES_DIR / RULES_NAME).read_text(encoding="utf-8")
    rows, problems = [], []
    for relative, sha256 in appendix_a_entries(rules_text):
        path = root / relative
        if not path.is_file():
            rows.append({"file": relative, "status": "missing"})
            problems.append(f"S-1 {relative} missing")
            continue
        data = path.read_bytes()
        raw = hashlib.sha256(data).hexdigest()
        row = {"file": relative, "raw_sha256": raw, "expected": sha256}
        if raw == sha256:
            row["status"] = "raw same"
        elif lf_normalised_sha256(data) == sha256:
            row.update(status="CRLF 변환만 다름", lf_normalised_sha256=sha256)
        else:
            row.update(status="differs", lf_normalised_sha256=lf_normalised_sha256(data))
            problems.append(f"S-1 {relative} differs (also after CRLF -> LF)")
        rows.append(row)
    return {"rules": RULES_REV2_NAME, "section": "R2-9 (8.2 S-1)", "files": len(rows),
            "crlf_only": [row["file"] for row in rows if row["status"] == "CRLF 변환만 다름"],
            "rows": rows, "problems": problems, "stop_S1": bool(problems),
            "exit_code": 1 if problems else 0}


# ------------------------------------------------------------------------- rev1 RV1-5 anchors
ANCHOR_SELECTIONS = (
    ("P-1 T-1", "las/las_T1.jsonl", 8),
    ("P-1 T-2", "las/las_T2.jsonl", 184),
    ("P-1 rest", "d1.jsonl", 216),
    ("P-2 Y-Pa", "las/k1/k1_YP.jsonl", 165),
    ("P-2 rest", "soil_defer/s2d_SC.jsonl", 291),
)
"""RV1-5 table: (prediction, anchor file under v5/, key count)."""
UNPREDICTED_GROUP = "H-R-A-stop"
"""RV1-5: the H-R-A-stop lines get no prediction."""


def job_key_of(line: dict) -> str | None:
    """``run_v5.job_key(line["job"])``: the ``job`` dict without ``mask`` / ``t4h_dir``."""
    job = line.get("job")
    if not isinstance(job, dict):
        return None
    return json.dumps({k: job[k] for k in sorted(job) if k not in ("mask", "t4h_dir")},
                      sort_keys=True)


def _anchor_lines(path: Path, name: str, taken: set[str]) -> list[dict]:
    """The lines of one anchor file that RV1-5 picks (each without ``error``)."""
    lines = [line for line in read_records(path) if "error" not in line]
    if name in ("P-1 T-1", "P-1 T-2"):
        return [line for line in lines if get_path(line, "las.candidate")[1] == "b0"]
    if name == "P-2 Y-Pa":
        return [line for line in lines if get_path(line, "k1.sub_bundle")[1] == "Y-Pa"
                and get_path(line, "las.candidate")[1] == "P0"]
    if name == "P-1 rest":
        return [line for line in lines if get_path(line, "job.d1.group")[1] == "H-R-0"
                and job_key_of(line) not in taken]
    return [line for line in lines if job_key_of(line) not in taken]  # P-2 rest


def anchor_selection(files: dict[str, Path]) -> dict:
    """RV1-5 anchors: key -> (prediction, ``commands_sha256``), with the S-7 checks."""
    anchors: dict[str, dict] = {}
    problems, counts = [], {}
    taken_p1: set[str] = set()
    taken_p2: set[str] = set()
    for name, entry, expected in ANCHOR_SELECTIONS:
        path = files[entry]
        _, sha_problems = appendix_b_problems(path)
        problems += sha_problems
        taken = taken_p1 if name.startswith("P-1") else taken_p2
        picked = _anchor_lines(path, name, taken)
        per_key = Counter(job_key_of(line) for line in picked)
        repeated = [key for key, n in per_key.items() if n != 1]
        if repeated:
            problems.append(f"S-7 {name}: {len(repeated)} keys with more than one line")
        if None in per_key:
            problems.append(f"S-7 {name}: a picked line without job")
        counts[name] = {"keys": len(per_key), "expected": expected}
        if len(per_key) != expected:
            problems.append(f"S-7 {name}: {len(per_key)} keys, RV1-5 table {expected}")
        for line in picked:
            key = job_key_of(line)
            if key in anchors:
                problems.append(f"S-7 key in two selections ({anchors[key]['prediction']}, {name})")
            anchors[key] = {"prediction": name, "commands_sha256": line.get("commands_sha256")}
        if name.startswith("P-1") and name != "P-1 rest":
            taken_p1.update(per_key)
        if name == "P-2 Y-Pa":
            taken_p2.update(per_key)
    return {"anchors": anchors, "counts": counts, "problems": problems}


def anchor_map(args: argparse.Namespace) -> dict:
    """RV1-5: pick the anchors, pair them with the H-1 lines by ``job_key`` (exactly one anchor
    per predicted H-1 key, else S-7) and compare ``commands_sha256`` (record of P-1 / P-2)."""
    files = {entry: Path(args.v5_dir) / entry for _, entry, _ in ANCHOR_SELECTIONS}
    selection = anchor_selection(files)
    anchors, problems = selection["anchors"], list(selection["problems"])
    out: dict[str, Any] = {"rules": RULES_REV1_NAME, "section": "RV1-5",
                           "counts": selection["counts"], "anchor_keys": len(anchors)}
    if args.h1 is not None:
        pairs, unpaired = [], []
        for line in read_records(Path(args.h1)):
            key = job_key_of(line)
            if get_path(line, "job.d1.group")[1] == UNPREDICTED_GROUP:
                continue
            anchor = anchors.get(key)
            if anchor is None:
                unpaired.append(key)
                continue
            sha = line.get("commands_sha256")
            pairs.append({"key": key, "prediction": anchor["prediction"],
                          "anchor": anchor["commands_sha256"], "run": sha,
                          "same": sha is not None and sha == anchor["commands_sha256"]})
        if unpaired:
            problems.append(f"S-7 {len(unpaired)} predicted H-1 keys without an anchor")
        out["h1"] = {"paired": len(pairs), "unpaired": unpaired[:20],
                     "same": sum(p["same"] for p in pairs),
                     "differ": sum(not p["same"] for p in pairs),
                     "pairs": pairs if args.all else [p for p in pairs if not p["same"]]}
    out["anchors"] = {key: value["commands_sha256"] for key, value in anchors.items()}
    return {**out, "problems": problems, "stop_S7": any("S-7" in p for p in problems),
            "exit_code": 1 if problems else 0}


# ------------------------------------------------------------------------ rev1 RV1-9 imports
LOC_SHADOW_MODULE = "loc_anchor_shadow"
LOC_SHADOW_INSTALLERS = ("hsh_run", "g8_shadow", "b1_harness")
"""RV1-9: the runners that call ``loc_anchor_shadow.install()``."""
SCRIPT_PATTERN = re.compile(r"[\w./\\:-]+\.py\b")
SOURCE_DIRS = ("03_src", "04_scripts", "05_tests/unit")


def module_index(root: Path) -> dict[str, list[Path]]:
    """Module name -> files under :data:`SOURCE_DIRS`: plain script names (``r67_g1_screen``)
    and dotted package names under ``03_src`` (``outrigger_sim.control.c2``)."""
    index: dict[str, list[Path]] = {}
    for folder in SOURCE_DIRS:
        for path in (root / folder).rglob("*.py"):
            index.setdefault(path.stem, []).append(path)
            if folder == "03_src":
                parts = path.relative_to(root / folder).with_suffix("").parts
                dotted = ".".join(parts[:-1] if parts[-1] == "__init__" else parts)
                index.setdefault(dotted, []).append(path)
    return index


def imported_names(path: Path) -> set[str]:
    """Every module name a file imports anywhere (also inside functions) and the name string of
    ``importlib.import_module("...")`` / ``spec_from_file_location("...", path)``; dotted names
    also give their prefixes."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:
        raise InputError(f"{path}: {exc}") from exc
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif (isinstance(node, ast.Call)
              and getattr(node.func, "attr", None) in ("import_module", "spec_from_file_location")
              and node.args and isinstance(node.args[0], ast.Constant)):
            names.add(str(node.args[0].value))
    prefixes = {".".join(name.split(".")[:i]) for name in names
                for i in range(1, name.count(".") + 1)}
    return names | prefixes


def import_closure(start: list[Path], index: dict[str, list[Path]]) -> dict[Path, set[str]]:
    """File -> imported names for the files reachable from ``start`` (an over-approximation: a
    plain name maps to every file of that name)."""
    seen: dict[Path, set[str]] = {}
    todo = list(start)
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        seen[path] = imported_names(path)
        for name in seen[path]:
            todo += [found for found in index.get(name, []) if found not in seen]
    return seen


def step_scripts(steps_doc: dict, root: Path) -> list[Path]:
    """Repository ``.py`` files named in the step commands (the interpreter excluded)."""
    scripts = []
    for step in steps_doc.get("steps", []):
        for token in SCRIPT_PATTERN.findall(str(step.get("cmd", ""))):
            path = Path(token) if Path(token).is_absolute() else root / token
            if path.is_file() and path not in scripts:
                scripts.append(path)
    return scripts


def import_check(args: argparse.Namespace) -> dict:
    """RV1-9: no 436.8 harness runner reaches ``loc_anchor_shadow`` (import) or a runner that
    installs it, and no step env names ``OUTRIGGER_LOC_SHADOW``."""
    root = Path(args.root)
    index = module_index(root)
    steps_doc = {"steps": [step for path in args.steps for step in read_json(Path(path))["steps"]]}
    scripts = step_scripts(steps_doc, root)
    closure = import_closure(scripts, index)
    hits = sorted(str(path.relative_to(root)) for path in closure
                  if path.stem == LOC_SHADOW_MODULE or path.stem in LOC_SHADOW_INSTALLERS)
    env_hits = [step.get("id") for step in steps_doc["steps"]
                if any(name in (step.get("env") or {}) for name in FORBIDDEN_ENV)]
    problems = [f"{hit} is reachable from a 436.8 runner" for hit in hits]
    problems += [f"step {step} env names {FORBIDDEN_ENV}" for step in env_hits]
    return {"rules": RULES_REV1_NAME, "section": "RV1-9",
            "runners": sorted(str(path.relative_to(root)) for path in scripts),
            "closure_files": len(closure),
            "closure": sorted(str(path.relative_to(root)) for path in closure),
            "loc_shadow_hits": hits, "env_hits": env_hits, "problems": problems,
            "method": "AST imports (module level and in functions, import_module / "
                      "spec_from_file_location name strings), plain names matched to every file "
                      "of that name",
            "exit_code": 1 if problems else 0}


# ------------------------------------------------------------------- rev1 RV1-7 F<F_min times
FMIN_WINDOW_S = 8.0
"""P5r4 judgement 8.2 table: departure .. departure + 8 s, 1 ms true F_cyl."""
SERIES_FILE = "step_series.npz"
LEG_NAMES = ("FL", "FR", "RL", "RR")


def below_durations(t_s, force_N, t_start_s: float, limit_N: float,
                    window_s: float = FMIN_WINDOW_S) -> dict:
    """Per leg the time (and sample count) with ``F < limit`` (7.6: ``v < X - 1e-9``) in the
    window ``t_start .. t_start + window_s``; the sample step is the median of ``diff(t)``."""
    import numpy as np

    t = np.asarray(t_s, dtype=float)
    force = np.asarray(force_N, dtype=float)
    window = (t >= t_start_s - COMPARE_EPS) & (t <= t_start_s + window_s + COMPARE_EPS)
    step_s = float(np.median(np.diff(t))) if t.size > 1 else math.nan
    below = window[:, None] & (force < limit_N - COMPARE_EPS)
    counts = below.sum(axis=0)
    return {"samples": [int(n) for n in counts], "ms": [round(float(n) * step_s * 1e3, 3)
                                                        for n in counts],
            "window_samples": int(window.sum()), "step_s": step_s}


DEPARTURE_FRACTION_W = 0.01
DEPARTURE_HOLD_S = 0.1
CRAWLER_NORMAL_KEY = "scm_crawler_normal_N"
"""R2-5: t_D = first sample of the first stretch with the 1 ms crawler true normal < 0.01 W for
>= 0.1 s (W = ``p3b.weight_N``). ``step_series.npz`` ``scm_crawler_normal_N`` is the crawler
support force along the plane normal (``run_S9`` ``sup_force_N @ normal``), taken as the sum of
all crawler contact normals also on mixed terrain."""


def departure_time(t_s, crawler_N, weight_N: float) -> float | None:
    """R2-5 t_D (None when no stretch qualifies)."""
    import numpy as np

    t = np.asarray(t_s, dtype=float)
    below = np.asarray(crawler_N, dtype=float) < DEPARTURE_FRACTION_W * weight_N
    start = None
    for index, is_below in enumerate(below):
        if not is_below:
            start = None
            continue
        start = index if start is None else start
        if t[index] - t[start] >= DEPARTURE_HOLD_S - COMPARE_EPS:
            return float(t[start])
    return None


def fmin_time(args: argparse.Namespace) -> dict:
    """RV1-7 / R2-5: the 7.4 record values ``F<F_min`` and ``F<F_min+2 kN`` time of one C-8 row
    in [t_D, t_D + 8 s] (and, record only, t_D .. run end)."""
    import numpy as np

    case = Path(args.case)
    result = read_json(case / "result.json")
    out: dict[str, Any] = {"rules": RULES_REV2_NAME, "section": "RV1-7 / R2-5 (7.4 record)",
                           "case": str(case), "window_s": FMIN_WINDOW_S,
                           "definition": "1 ms true F_cyl (step_series.npz F_cyl_N) in [t_D, t_D + "
                                         "8 s]; t_D = crawler normal < 0.01 W for 0.1 s (R2-5)",
                           "series_sha256": file_sha256(case / SERIES_FILE)}
    present, weight_N = get_path(result, "p3b.weight_N")
    if not present or not isinstance(weight_N, (int, float)):
        return {**out, "status": "판정 불가 (p3b.weight_N missing)", "exit_code": 1}
    try:
        with np.load(case / SERIES_FILE, allow_pickle=False) as series:
            t_s = np.asarray(series["t_s"], dtype=float)
            force_N = np.asarray(series["F_cyl_N"], dtype=float)
            crawler_N = np.asarray(series[CRAWLER_NORMAL_KEY], dtype=float)
    except (OSError, KeyError, ValueError) as exc:
        raise InputError(f"{case / SERIES_FILE}: {exc}") from exc
    t_dep = departure_time(t_s, crawler_N, float(weight_N))
    out["t_D_s"] = t_dep
    out["p3b_departure_t_s"] = get_path(result, "p3b.departure.t_departure_s")[1]  # record only
    if t_dep is None:
        return {**out, "status": "판정 불가 (t_D not defined, R2-5)", "exit_code": 1}
    run_end_s = float(t_s[-1])
    out["window_complete"] = run_end_s >= t_dep + FMIN_WINDOW_S - COMPARE_EPS
    out["run_end_s"] = run_end_s
    results = {}
    for name, limit in (("F_below_F_min", F_MIN_N), ("F_below_F_min_plus_2kN",
                                                      F_MIN_N + OC5_GUARD_N)):
        window = below_durations(t_s, force_N, t_dep, limit)
        whole = below_durations(t_s, force_N, t_dep, limit, window_s=run_end_s - t_dep)
        results[name] = {**window, "max_ms": max(window["ms"]),
                         "to_run_end_record_only": {"ms": whole["ms"], "max_ms": max(whole["ms"])}}
    return {**out, "legs": list(LEG_NAMES), **results, "status": "기록", "exit_code": 0}


# ------------------------------------------------------------- rev1 RV1-10 j stroke exposure
STROKE_LIMITS_MM = (678.0, 684.8)
"""RV1-10 j record limits (``end_stop_cushion_model_review.md``): cushion reading 678 mm, gate
684.8 mm. Comparison with the 7.6 allowance 1e-9 m."""
STROKE_EPS_MM = COMPARE_EPS * 1e3
S_REF_PATHS = (
    ("d1.stroke_max_m", 1e3),
    ("base.max_motor_stroke_mm", 1.0),
    ("max_motor_stroke_mm", 1.0),
    ("max_stroke_mm", 1.0),
    ("p3b.P3-5_clearance_stroke.s_motor_max_m", 1e3),
)
"""(key path, factor to mm) of a run's maximum ``s_ref`` / ``stroke_m`` (oil-volume coordinate,
harness ``max(plant.sref)``, Chrono L1 motor position); the first path present counts."""
PISTON_PATHS = (("r79.max_true_stroke_mm", 1.0),)
"""(key path, factor to mm) of a run's maximum piston stroke (``stroke_corrected_m``)."""
EVENT_PATHS = ("events", "event_names", "warnings", "fault_events", "base.warnings",
               "base.events_head", "r79.warn_fault")
STROKE_END_COUNT_PATHS = ("r79.n_stroke_end_fault",)
STROKE_END_EVENT = "FAULT_STROKE_END"


def path_maximum_mm(record: dict, paths: tuple) -> tuple[float | None, str | None]:
    """(maximum in mm, path) of the first present path with a numeric value or list."""
    for dotted, factor in paths:
        present, value = get_path(record, dotted)
        if not present or value is None:
            continue
        values = value if isinstance(value, list) else [value]
        numbers = [float(v) for v in values if isinstance(v, (int, float))
                   and not isinstance(v, bool) and math.isfinite(v)]
        if numbers:
            return max(numbers) * factor, dotted
    return None, None


def _event_names(value: Any) -> Iterator[str]:
    for item in value if isinstance(value, list) else []:
        if isinstance(item, str):
            yield item
        elif isinstance(item, dict) and "name" in item:
            yield str(item["name"])
        elif isinstance(item, (list, tuple)):
            yield from (str(part) for part in item if isinstance(part, str))


def stroke_end_fault(record: dict) -> bool | None:
    """True / False from the record's event lists or counters; None without any of them."""
    found_source = False
    for dotted in STROKE_END_COUNT_PATHS:
        present, value = get_path(record, dotted)
        if present and isinstance(value, int):
            found_source = True
            if value > 0:
                return True
    for dotted in EVENT_PATHS:
        present, value = get_path(record, dotted)
        if not present or not isinstance(value, list):
            continue
        found_source = True
        if any(name.startswith(STROKE_END_EVENT) for name in _event_names(value)):
            return True
    return False if found_source else None


def unit_records(document: Any) -> list[dict]:
    """The lines / rows a bundle counts: grid ``results[].runs[]``, r79 / screen ``results[]`` or
    ``records[]``, jsonl lines, or one ``result.json``."""
    if isinstance(document, dict):
        results = document.get("results") or document.get("records")
        if isinstance(results, list):
            if results and all(isinstance(row.get("runs"), list) for row in results):
                return [run for row in results for run in row["runs"]]
            return results
        return [document]
    return list(document)


def exposure_counts(records: list[dict]) -> dict:
    out: dict[str, Any] = {"lines": len(records)}
    for coordinate, paths in (("s_ref", S_REF_PATHS), ("piston", PISTON_PATHS)):
        values = [path_maximum_mm(record, paths) for record in records]
        recorded = [value for value, _ in values if value is not None]
        cell: dict[str, Any] = {"recorded": len(recorded),
                                "no_record": len(records) - len(recorded),
                                "paths": sorted({path for _, path in values if path})}
        for limit in STROKE_LIMITS_MM:
            cell[f"ge_{limit:g}_mm"] = sum(value >= limit - STROKE_EPS_MM for value in recorded)
        if not recorded:
            cell["note"] = "기록 없음"
        out[coordinate] = cell
    faults = [stroke_end_fault(record) for record in records]
    out[STROKE_END_EVENT] = {"lines": sum(fault is True for fault in faults),
                             "no_event_record": sum(fault is None for fault in faults)}
    return out


def stroke_exposure(args: argparse.Namespace) -> dict:
    """RV1-10 j: per bundle the lines / rows with max stroke >= 678 mm and >= 684.8 mm (``s_ref``
    and piston apart) and with ``FAULT_STROKE_END``; record only (no grade, no stop)."""
    records = [record for path in args.harness or [] for doc in read_records(Path(path))
               for record in unit_records(doc)]
    for batch_dir in args.chrono or []:
        for case in _batch_rows(Path(batch_dir)):
            result_path = Path(batch_dir) / case / "result.json"
            records.append(read_json(result_path) if result_path.is_file() else {})
    return {"rules": RULES_REV1_NAME, "section": "RV1-10 j (record)", "bundle": args.bundle,
            "limits_mm": list(STROKE_LIMITS_MM), **exposure_counts(records),
            "s_ref_paths": [p for p, _ in S_REF_PATHS],
            "piston_paths": [p for p, _ in PISTON_PATHS],
            "exit_code": 0}


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
            p.add_argument("--anchor-map", type=Path, default=None,
                           help="anchor-map report (RV1-5 selection; replaces --anchor)")
            p.add_argument("--family-table", type=Path, default=None,
                           help="resume_k1_family.py table (RV1-6; a key not in it = uniform)")
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
    p = sub.add_parser("keyset",
                       help="rev1 RV1-3: new H-6 .. H-9 grid output vs stored keys (S-15)")
    p.add_argument("--kind", required=True, choices=("r79", "grid"))
    p.add_argument("--new", type=Path, required=True, help="new runner output (.json)")
    p.add_argument("--stored", type=Path, required=True, help="appendix B file under v5/")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("dg3-hash", help="rev1 RV1-3.2: H-6 vs H-8 VB commands_sha256 (record)")
    p.add_argument("--h6", type=Path, required=True)
    p.add_argument("--h8-vb", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("anchor-map", help="rev1 RV1-5: P-1 / P-2 anchors by job_key (S-7)")
    p.add_argument("--v5-dir", type=Path, required=True,
                   help="06_analysis/03_hydraulic/coupled/v5 of the checkout with the anchors")
    p.add_argument("--h1", type=Path, default=None, help="resume_k1/h1_d1.jsonl (after H-1)")
    p.add_argument("--all", action="store_true", help="list every pair, not only differences")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("import-check", help="rev1 RV1-9: no loc_anchor_shadow on the runner path")
    p.add_argument("--steps", nargs="+", type=Path, required=True)
    p.add_argument("--root", type=Path, default=ROOT, help="checkout (git_at_start)")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("fmin-time", help="rev1 RV1-7: 7.4 F<F_min times of a C-8 row (record)")
    p.add_argument("--case", type=Path, required=True,
                   help="case folder (result.json, step_series.npz)")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("appendix-a", help="rev2 R2-9: original appendix A sha256 (S-1)")
    p.add_argument("--root", type=Path, default=ROOT, help="checkout (git_at_start)")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("stroke-exposure", help="rev1 RV1-10 j: stroke exposure counts (record)")
    p.add_argument("--bundle", required=True)
    p.add_argument("--harness", nargs="*", type=Path)
    p.add_argument("--chrono", nargs="*", type=Path)
    p.add_argument("--out", type=Path, required=True)
    return parser


COMMANDS = {
    "record-check": record_check,
    "k1-class": k1_class,
    "jp-reuse": jp_reuse,
    "oc5": oc5,
    "overlap": overlap,
    "gs": gs,
    "keyset": keyset,
    "dg3-hash": dg3_hash,
    "anchor-map": anchor_map,
    "import-check": import_check,
    "fmin-time": fmin_time,
    "appendix-a": appendix_a,
    "stroke-exposure": stroke_exposure,
}


def revision_seal_problems(folder: Path, name: str, sha256: str) -> tuple[dict, list[str]]:
    """One sealed revision: the file's raw sha256 and the first field of its ``.sha256`` must both
    be ``sha256`` (rules 8.2 S-1; R2-9: sealed rule files are compared raw)."""
    rules_path = folder / name
    seal_path = rules_path.with_suffix(".sha256")
    out: dict[str, Any] = {"expected_sha256": sha256}
    problems = []
    if seal_path.is_file():
        fields = seal_path.read_text(encoding="utf-8").split()
        out["seal_file_sha256"] = fields[0] if fields else None
        if out["seal_file_sha256"] != sha256:
            problems.append(
                f"{seal_path.name} value {out['seal_file_sha256']!r} is not the sealed one")
    else:
        problems.append(f"{seal_path.name} missing")
    if rules_path.is_file():
        out["rules_file_sha256"] = hashlib.sha256(rules_path.read_bytes()).hexdigest()
        if out["rules_file_sha256"] != sha256:
            problems.append(
                f"{rules_path.name} sha256 {out['rules_file_sha256'][:16]} is not the sealed one")
    else:
        problems.append(f"{rules_path.name} missing")
    return out, problems


def sealed_rules_check(rules_dir: Path | None = None) -> dict:
    """Rev1 and rev2 seals (:data:`SEALED_REVISIONS`); any problem is ``stop_S1``."""
    folder = RULES_DIR if rules_dir is None else Path(rules_dir)
    revisions, problems = {}, []
    for name, sha256 in SEALED_REVISIONS:
        revisions[name], found = revision_seal_problems(folder, name, sha256)
        problems += found
    return {"revisions": revisions, "problems": problems, "stop_S1": bool(problems)}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    seal = sealed_rules_check()
    if seal["stop_S1"]:  # no judgement under an unsealed or changed revision
        report = {"rules": RULES_NAME, "section": "8.2 S-1 (rev1 / rev2 seal)",
                  "rules_seal": seal, "exit_code": 1}
    else:
        try:
            report = COMMANDS[args.command](args)
        except InputError as exc:
            print(json.dumps({"exit_code": 2, "error": str(exc)}, ensure_ascii=True))
            return 2
        except Exception as exc:  # report the failure in the contract form, keep the trace
            print(traceback.format_exc(), file=sys.stderr)
            print(json.dumps({"exit_code": 3, "error": repr(exc)}, ensure_ascii=True))
            return 3
        report["rules_seal"] = seal
    report["rules_sha256"] = RULES_SHA256
    report["rules_rev1_sha256"] = RULES_REV1_SHA256
    report["rules_rev2_sha256"] = RULES_REV2_SHA256
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
