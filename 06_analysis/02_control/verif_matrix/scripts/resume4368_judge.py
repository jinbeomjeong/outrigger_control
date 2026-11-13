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

Rev3 (``v5_resume_4368_rules_rev3.md``, sealed dad8dfa6, checked raw too):
  grid-v0-sample R3-E1: the 8-job V0 grid sample vs the stored V0 grid (V0 768 needed or not)
  family-f-trigger / family-f  R3-E2: whether family F starts the 64 runs; rev5 5.2 R-1 .. R-4
  ind-las        R3-B5: IND_LAS gate (``INFO_LIFTOFF_SLOW:``) and the IND hash
  reagg-items    TABLE_REAGG rows (R3-A2, R3-G1, R3-E3)
  dg3-hash reads the top-level r79 ``commands_sha256`` only (R3-E4, keys without ``cand=``,
  R3-D1); appendix B files also pass after CRLF -> LF (R3-F4, disclosed); gs also requires the
  command hash and the grid ``extend_bound_check`` (③ settings) and counts
  ``head_only_declared``.

Rev4 (``v5_resume_4368_rules_rev4.md``, sealed 7ea87a30, checked raw too): grid-v0-sample
pairs every run of a sampled result by (event, offset) (R4-B4); gs requires the record-only
fields F-1 .. F-6 of the R4-D table and checks the second table (``extend_bound_check.rule`` =
the ext_moving rule with ``breach_reads``, r79 first DONE: g6 / ref bases ``t_done_s`` = the
first DONE of ``phase_path``, g8 bases (no ``t_done_s``) the first DONE of ``timeline``, no
timeline = S-11, no DONE = None only with a fault ``final_phase`` (else S-11), user decisions
2026-11-13 / rev7 proposal; ``gs --chrono``: PS-c ``soil_event_series.npz`` columns). A T-3K
line with ``t3.las`` and ``t3.gate`` off reads as ``final_C4G2`` without a tag key.

Rev5 (``v5_resume_4368_rules_rev5.md``, sealed 452a8436, checked raw too): R5-A1 makes the
``04_scripts/04_hydraulic/coupled/*_4368.py`` judges the harness path 1 (this tool keeps its
subcommands; it only adds the rev5 seal check). Rev6 (``v5_resume_4368_rules_rev6.md``, sealed
809e5639, checked raw too): seal check only here (R6-C items are in the ``*_4368.py`` judges).

Rev7 (``v5_resume_4368_rules_rev7.md``, sealed e81f7d31, checked raw too): R7-1a in ``gs`` and
``record-check``: the top-level ``controller_tag`` of every r79 result (H-6 .. H-8) and grid job
record (H-9) against the ``controller_tag`` of the T4h meta of the same run (``t4h_file`` in
``--t4h-dir``, ``<result stem>_t4h/`` or ``t4h/`` next to the result). Different, or a tag on
one side only (a listed T4h file that is not found counts as no meta tag) = S-2.

Rev8 (``v5_resume_4368_rules_rev8.md``, sealed 3ecafaaf, checked raw too): R8-1 replaces the
"not compared" runs of rev7. A run without ``t4h_file`` (grid job records, r79 runs without
``R79_T4H_DIR``) gets its tag recomputed from the recorded switches by the sealed rule
(:func:`recompute_tag`: ``hydraulic_options.extend_start_tracked``, ``resume_k1.applicable``,
LAS-b ``enable``, K1 ``flat_soil_margin_order_gate``; the dg3 ``extend_start_rule`` and every
grid run's switches are cross-checked) and compared with the top-level ``controller_tag``.
Different, one side only or not computable = S-2; ``gs`` also reports a not computable tag as
S-11 (``stop_S11``). Rev8 R8-2 / R8-3 (Chrono J-P3 scope, SCM J11) are in
``04_scripts/02_chrono/chrono_rows_judge_4368.py``.

Rev9 (``v5_resume_4368_rules_rev9.md``, sealed 4cf7843c, checked raw too): R9-7 tag rule (K1
alone = ``final_C4G2_K1``, ③ + K1 = ``final_C4G2_P3_K1``; :func:`recompute_tag` already gives
these); R9-1 in ``record-check``: a Chrono row whose ``expect_controller.ok`` is false or missing
is S-2 (``expect_controller_failed_R9_1``). R9-2 .. R9-6 are in the Chrono judge and gs-check.

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
RULES_REV3_NAME = "v5_resume_4368_rules_rev3.md"
RULES_REV3_SHA256 = "dad8dfa68da7a988971f4d687706465289ec7dd95d09079c92215c64e5eae557"
"""Rev3 (sealed 2026-11-13 03:13:21 +09:00): overrides rev2, rev1 and the original."""
RULES_REV4_NAME = "v5_resume_4368_rules_rev4.md"
RULES_REV4_SHA256 = "7ea87a30b08a00263c597d42d3450dc56f68952e8d3205604cb2c5bab5dce14b"
"""Rev4 (sealed 2026-11-13 03:47:45 +09:00): overrides rev3 .. the original."""
RULES_REV5_NAME = "v5_resume_4368_rules_rev5.md"
RULES_REV5_SHA256 = "452a8436c547e4da8d78205556cbb37633842d42cb98c18849cb883d827b3aca"
"""Rev5 (sealed 2026-11-13 07:32:14 +09:00): overrides rev4 .. the original (R5-A1: the
harness path 1 judges are the ``*_4368.py`` versions)."""
RULES_REV6_NAME = "v5_resume_4368_rules_rev6.md"
RULES_REV6_SHA256 = "809e563971ea451aba7c9d0787c660bdcab1c495af39c513c8f158e09b4fe6c9"
"""Rev6 (sealed 2026-11-13 07:49:42 +09:00): overrides rev5 .. the original (R6-C: F-9, K-0
fields, U-S9-G6c branch)."""
RULES_REV7_NAME = "v5_resume_4368_rules_rev7.md"
RULES_REV7_SHA256 = "e81f7d31779b0d69a140c9d90aa4684f3c9299e84aec6af06b13d48d58631502"
"""Rev7 (sealed 2026-11-13 09:56:53 +09:00): overrides rev6 .. the original (R7-1a: r79 / grid
top-level tag = T4h meta tag, else S-2; R7-7: this seal is checked by the path 1 tools)."""
RULES_REV8_NAME = "v5_resume_4368_rules_rev8.md"
RULES_REV8_SHA256 = "3ecafaaf33d84bb6f34a8cef5401771832a4999e4930f3644caff56eed640e56"
"""Rev8 (sealed 2026-11-13 10:47:09 +09:00): overrides rev7 .. the original (R8-1: runs without
a T4h record recompute the tag from the recorded switches; R8-4: this seal is checked by the
path 1 tools)."""
RULES_REV9_NAME = "v5_resume_4368_rules_rev9.md"
RULES_REV9_SHA256 = "4cf7843ce469df511d7b99c7236f0b245afae9fb4ba5ad903e1c2da823a59a6d"
"""Rev9 (sealed, master e5a2c19): overrides rev8 .. the original (R9-7: K1 alone =
``final_C4G2_K1``, ③ + K1 without LAS-b = ``final_C4G2_P3_K1``; R9-8: this seal is checked)."""
RULES_REV10_NAME = "v5_resume_4368_rules_rev10.md"
RULES_REV10_SHA256 = "62a0bd8dd6644f78bf37d052e884061d8c14e1cc96e2babc72a6ac0618f12c29"
"""Rev10 (sealed, master 8b4ad93): R9-4 LS input boundaries (Chrono tools only); this seal is checked
(R10-3)."""
SEALED_REVISIONS = ((RULES_REV1_NAME, RULES_REV1_SHA256), (RULES_REV2_NAME, RULES_REV2_SHA256),
                    (RULES_REV3_NAME, RULES_REV3_SHA256), (RULES_REV4_NAME, RULES_REV4_SHA256),
                    (RULES_REV5_NAME, RULES_REV5_SHA256), (RULES_REV6_NAME, RULES_REV6_SHA256),
                    (RULES_REV7_NAME, RULES_REV7_SHA256), (RULES_REV8_NAME, RULES_REV8_SHA256),
                    (RULES_REV9_NAME, RULES_REV9_SHA256), (RULES_REV10_NAME, RULES_REV10_SHA256))
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
            expect_ok = None
            if result_path.is_file():
                result = read_json(result_path)
                problems += chrono_result_problems(result, is_c4_off=is_c4_off,
                                                   is_engine=_is_engine_row(row))
                expect_ok = expect_check_ok(result, is_engine=_is_engine_row(row))
            else:
                problems.append("result.json missing")
            chrono.append(
                {
                    "batch": str(batch_dir),
                    "case": case,
                    "c4_off_arm": is_c4_off,
                    "problems": problems,
                    "expect_controller_ok_R9_1": expect_ok,
                }
            )
    bad = sum(bool(r["problems"]) for r in harness + chrono)
    tag_check = r79_tag_check(args.harness or [], getattr(args, "t4h_dir", None) or ())
    # rev9 R9-1: a Chrono row whose expect_controller check is false or missing stops the bundle
    expect_failed = [r["case"] for r in chrono if r["expect_controller_ok_R9_1"] is not True]
    return {
        "expect_controller_failed_R9_1": expect_failed,
        "rules": RULES_NAME,
        "section": "4.2 (+ rev7 R7-1a / rev8 R8-1 tags, rev9 R9-1 expect_controller)",
        "harness_runs": len(harness),
        "chrono_rows": len(chrono),
        "rows_with_problems": bad,
        "stop_S3": bad > 0,
        "harness": [r for r in harness if r["problems"]] if not args.all else harness,
        "chrono": chrono,
        "r79_tag_check": tag_check,
        "stop_S2": tag_check["stop_S2"] or bool(expect_failed),
        "exit_code": 1 if bad or tag_check["stop_S2"] or expect_failed else 0,
    }


def expect_check_ok(result: dict, *, is_engine: bool) -> bool:
    """Rev9 R9-1: the row's controller-tag check (SCM ``c2_setup.expect_controller.ok``, L2b / L1-R
    ``expect_controller.ok``) is true; false or a missing key is S-2."""
    dotted = "expect_controller.ok" if is_engine else "c2_setup.expect_controller.ok"
    return get_path(result, dotted)[1] is True


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
    anchors: dict[str, str] = {}
    anchor_source = "none"
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
T3_SWITCH_OFF = "off"
T3_ALL_OFF_TAG = "final_C4G2"
"""User decision 2026-11-13 (rev7 proposal R7-1 c): a T-3K line with ``t3.las`` = ``off`` and
``t3.gate`` = ``off`` (R-0: LAS-b and the K1 gate off, the pre-LAS preset) carries no
``controller_tag`` by the record rule (key only with ③ or a switch on); it reads as this tag
and is not a missing key."""


def is_t3_all_off_line(record: dict) -> bool:
    """A T-3K line run with LAS-b and the K1 gate off (``t3.las`` and ``t3.gate`` = ``off``)."""
    t3 = record.get("t3")
    return (isinstance(t3, dict) and t3.get("las") == T3_SWITCH_OFF
            and t3.get("gate") == T3_SWITCH_OFF)


def read_controller_tag(record: dict) -> str | None:
    """The run's controller tag: the first tag key present, else ``final_C4G2`` for an all-off
    T-3K line, else None."""
    for dotted in TAG_KEY_ALTERNATIVES:
        present, value = get_path(record, dotted)
        if present:
            return value
    return T3_ALL_OFF_TAG if is_t3_all_off_line(record) else None


SETTLE_V2_SUITES = ("slope", "h6", "x426b", "h9")
"""U-3 fix-candidates suites run through ``s9_soil_slope.run_one`` (they carry ``settle_v2``)."""
SETTLE_V2_KEYS = ("status",)
SETTLE_V2_CHECKED_KEYS = (
    "inputs.pen_inst_mm", "inputs.q_floor_inst_deg", "inputs.q_floor_mean_deg",
    "inputs.d_attitude_deg", "inputs.pad_xy_m", "inputs.gap_target_mm",
    "inputs.gap_target_source", "inputs.table_gap_target_mm", "inputs.residual_deg",
    "inputs.attitude_error_deg",
    "inputs.table_sha256", "result.pen_mean_mm", "result.pen_plus_gap_mm",
    "result.attitude_tol_deg", "result.ok", "result.gate",
)
"""436.8 Q-U1 = A: the settle v2 keys a U-3 run must carry (``checked`` runs: all of them)."""


def settle_v2_prefix(record: dict) -> str | None:
    """Where a run keeps ``settle_v2``: U-3 slope-like records and ``s9_soil_slope`` results at
    the top, D-1 steady lines (U-3 reuse) under ``u3``; None for runs without one."""
    if record.get("suite") in SETTLE_V2_SUITES:
        return "settle_v2"
    if isinstance(record.get("case"), dict) and "settle" in record:
        return "settle_v2"
    if isinstance(record.get("u3"), dict):
        return "u3.settle_v2"
    return None


def settle_v2_presence(record: dict) -> dict[str, bool]:
    prefix = settle_v2_prefix(record)
    if prefix is None:
        return {}
    presence = {f"{prefix}.{key}": get_path(record, f"{prefix}.{key}")[0]
                for key in SETTLE_V2_KEYS}
    if get_path(record, f"{prefix}.status")[1] == "checked":
        presence.update({f"{prefix}.{key}": get_path(record, f"{prefix}.{key}")[0]
                         for key in SETTLE_V2_CHECKED_KEYS})
    return presence


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
                has_tag_key = any(get_path(record, alt)[0] for alt in TAG_KEY_ALTERNATIVES)
                presence[dotted] = has_tag_key or is_t3_all_off_line(record)
        elif is_c2 or dotted == f"{RECORD_KEY}.applicable":
            presence[dotted] = get_path(view, dotted)[0]
    presence.update(settle_v2_presence(record))  # Q-U1 = A
    return presence


COMMAND_HASH_ALTERNATIVES = ("commands_sha256", "hash", "v5.logged_commands_sha256")
"""Rev3 G-S: a harness run's command hash (run_v5 lines, grid runs, screen records). r79
results (rev3 R3-E4) count with the top-level ``commands_sha256`` only."""
HEAD_ONLY_KEYS = ("head_only_declared", "v5.head_only_declared")
"""Rev3 R3-C8 / Q-S3: recorded, not required (a missing field is read by the revision 9 3.1
configuration definition and that fact goes into the judgement)."""
P3_SETTINGS = ("VB", "LS1", "LS2", "LS3", "LS4")


def is_r79_record(record: dict) -> bool:
    return "seed_index" in record and "harness" in record and "inner" in record


def hash_presence(record: dict) -> dict[str, bool]:
    """Rev3 G-S: the command hash of a run that names itself (grid runs do not, see :func:`gs`)."""
    if not any(name in record for name in ("job", "key", "id", "case")):
        return {}
    if isinstance(record.get("runs"), list):  # a grid job record: its runs carry the hashes
        return {}
    if is_r79_record(record):
        return {R79_HASH_KEY: get_path(record, R79_HASH_KEY)[0]}
    return {"command hash": any(get_path(record, k)[0] for k in COMMAND_HASH_ALTERNATIVES)}


def grid_run_presence(document: dict) -> tuple[int, dict[str, bool]]:
    """(runs, key -> all present) of a grid file's ``runs[]``: ``commands_sha256`` and, on a
    ③ setting (``meta.v5_setting`` VB / LS), ``hydraulics_record.extend_bound_check`` (rev3
    Q-G3: J-P3 #1 / #2)."""
    runs = [run for row in document["results"] for run in row["runs"]]
    presence = {"runs[].commands_sha256": all("commands_sha256" in run for run in runs)}
    if (document.get("meta") or {}).get("v5_setting") in P3_SETTINGS:
        presence["runs[].hydraulics_record.extend_bound_check"] = all(
            get_path(run, "hydraulics_record.extend_bound_check")[0] for run in runs)
    return len(runs), presence


SA4_CASES = ("S8",)
"""Rev4 F-4: the v5 S8 family rows (``job.case``) carry ``values.sa4.lift_after_stop_ms``."""
DONE_PHASE = "done"
PHASE_PATH_TIME_TOL_S = 0.005
"""``base.timeline`` keeps the times rounded to 1 ms (``r67_g1_screen.run_base``), the cut
``phase_path`` of older records to 0.01 s: 5 ms accepts both and still parts two 0.1 s
controller periods."""
FIRST_DONE_KEY = "r79 R4-B2 first DONE (base.timeline or base.t_done_s / phase_path)"
"""G-S key of the R4-B2 check (:func:`first_done_check`)."""
FIRST_DONE_OK = "pass"
FIRST_DONE_STOP = "S-11"
FAULT_FINAL_PHASES = ("fault", "fault_reground")
"""``C2Phase.FAULT`` / ``FAULT_REGROUND`` values, the fault ends of a run. Stored r79 bases
(v5 folder and G-S b1ddeae, 2026-11-13) end in ``ready``, ``probe``, ``level`` or ``fault``;
the 4 DONE-less runs among them all end in ``fault``."""


def rev4_presence(record: dict) -> dict[str, bool]:
    """Rev4 R4-D: F-1 .. F-4 on run_v5 lines and the meaning checks of its second table that a
    single record answers (``extend_bound_check.rule`` / ``breach_reads``, r79 first DONE)."""
    out: dict[str, bool] = {}
    job = record.get("job")
    if isinstance(job, dict) and isinstance(record.get("values"), dict):
        out["F-1 values.times.t_check_start_s"] = get_path(
            record, "values.times.t_check_start_s")[0]
        if job.get("d1") is not None:
            out["F-2 d1.demoted_items"] = get_path(record, "d1.demoted_items")[0]
            if get_path(record, "d1.path")[1] == "g6":  # rev5 R5-D4 F-8 (g6 path lines)
                out["F-8 d1.g6_preloc"] = get_path(record, "d1.g6_preloc.preloc_flag_ok")[0]
        else:
            out["F-3 values.case_floor_deg"] = get_path(record, "values.case_floor_deg")[0]
        if job.get("case") in SA4_CASES:
            out["F-4 values.sa4.lift_after_stop_ms"] = get_path(
                record, "values.sa4.lift_after_stop_ms")[0]
            # rev6 R6-D F-9 and the saturation field description (R6-C1 2)
            out["F-9 values.sa4.F_min_after_stop_N"] = get_path(
                record, "values.sa4.F_min_after_stop_N")[0]
            out["values.pressure.saturation_rule = item 4 saturation stop"] = (
                get_path(record, "values.pressure.saturation_rule")[1] == saturation_rule())
    present, bound = get_path(record, "hydraulics_record.extend_bound_check")
    if present and isinstance(bound, dict):
        out["extend_bound_check.rule = ext_moving rule"] = bound.get("rule") == extend_bound_rule()
        out["extend_bound_check.breach_reads"] = "breach_reads" in bound
    if is_r79_record(record) and isinstance(record.get("base"), dict):
        out[FIRST_DONE_KEY] = first_done_check(record["base"])["status"] == FIRST_DONE_OK
    return out


def saturation_rule() -> str | None:
    """``verdict_metrics.SATURATION_RULE`` (rev6 R6-C1 2 field description)."""
    coupled = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
    if str(coupled) not in sys.path:
        sys.path.append(str(coupled))
    try:
        from verdict_metrics import SATURATION_RULE
    except ImportError:
        return None
    return SATURATION_RULE


def extend_bound_rule() -> str | None:
    """``extend_start_bound.EXTEND_BOUND_CHECK_RULE`` (the ext_moving definition of rev4 R4-A2)."""
    try:
        from outrigger_sim.control.extend_start_bound import EXTEND_BOUND_CHECK_RULE
    except ImportError:
        return None
    return EXTEND_BOUND_CHECK_RULE


def timeline_first_done_s(timeline) -> float | None:
    """Time [s] of the first DONE entry of a ``[[t_s, phase], ...]`` phase list (r79
    ``base.timeline`` or ``base.phase_path``); None without one."""
    for entry in timeline or []:
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            continue
        if str(entry[1]).lower().endswith(DONE_PHASE):
            return float(entry[0])
    return None


def _first_done_result(status: str, t_first_done: float | None, source: str,
                       reason: str | None = None) -> dict:
    return {"status": status, "t_first_done_s": t_first_done, "source": source,
            "reason": reason}


def _done_less_result(base: dict, source: str) -> dict:
    """A run whose phase list has no DONE: first DONE = None (rev4 R4-B2 "DONE 없음") when it
    ended in a fault, else S-11 (user decision 2026-11-13)."""
    final_phase = base.get("final_phase")
    if final_phase in FAULT_FINAL_PHASES:
        return _first_done_result(FIRST_DONE_OK, None, source)
    return _first_done_result(FIRST_DONE_STOP, None, source,
                              f"no DONE in {source}, final_phase {final_phase!r} is no fault")


def _first_done_from_timeline(base: dict) -> dict:
    timeline = base.get("timeline")
    if not isinstance(timeline, list) or not timeline:
        return _first_done_result(FIRST_DONE_STOP, None, "base.timeline",
                                  "base.timeline missing or empty")
    t_first_done = timeline_first_done_s(timeline)
    if t_first_done is None:
        return _done_less_result(base, "base.timeline")
    return _first_done_result(FIRST_DONE_OK, t_first_done, "base.timeline")


def _first_done_from_t_done(base: dict) -> dict:
    """g6 / ref shape: ``t_done_s`` (the DONE time the judge reads) against ``phase_path``."""
    t_done = base["t_done_s"]
    path_first_done = timeline_first_done_s(base.get("phase_path"))
    if t_done is None:
        if path_first_done is not None:
            return _first_done_result(FIRST_DONE_STOP, path_first_done, "base.t_done_s",
                                      "base.t_done_s None but base.phase_path has a DONE")
        return _done_less_result(base, "base.t_done_s / base.phase_path")
    if path_first_done is None or abs(path_first_done - float(t_done)) > PHASE_PATH_TIME_TOL_S:
        return _first_done_result(FIRST_DONE_STOP, path_first_done, "base.t_done_s",
                                  f"base.t_done_s {t_done} is not the first DONE of "
                                  f"base.phase_path ({path_first_done})")
    return _first_done_result(FIRST_DONE_OK, float(t_done), "base.t_done_s")


def first_done_check(base: dict) -> dict:
    """Rev4 R4-B2 on the r79 record as written: the first DONE time of the run.

    Two record shapes (stored v5 r79 results, 2026-11-13): g6 / ref runs keep ``t_done_s`` and
    ``phase_path`` (rev4 R4-B2 as written: ``t_done_s`` must be the first DONE of the path);
    g8 runs keep ``timeline`` (each phase change) and no ``t_done_s``, so their first DONE is
    the first DONE entry of ``timeline`` (a missing or empty timeline: S-11, a G-S failure).
    A run without a DONE has first DONE None and passes only when ``final_phase`` is a fault
    (:data:`FAULT_FINAL_PHASES`); otherwise S-11 (user decision 2026-11-13).

    Returns:
        ``status`` (``pass`` or ``S-11``), ``t_first_done_s`` (None: no DONE or missing),
        ``source`` (the field read) and ``reason`` (None on a pass).
    """
    if "t_done_s" in base:
        return _first_done_from_t_done(base)
    return _first_done_from_timeline(base)


SOIL_EVENT_SERIES = "soil_event_series.npz"
SOIL_EVENT_COLUMN_PREFIXES = ("contact_", "Fcyl_", "gap_")


def soil_event_series_presence(case_dir: Path) -> dict[str, bool]:
    """Rev4 R4-D: a PS-c row's ``soil_event_series.npz`` has the pad contact normal, F_cyl and
    gap columns of each leg (spec 426.3 E-1 .. E-6 inputs)."""
    path = case_dir / SOIL_EVENT_SERIES
    if not path.is_file():
        return {}
    import numpy as np

    with np.load(path, allow_pickle=False) as series:
        columns = [str(c) for c in series["columns"]] if "columns" in series.files else []
        has_rows = "rows" in series.files
    wanted = [f"{prefix}{leg}" for prefix in SOIL_EVENT_COLUMN_PREFIXES for leg in LEG_NAMES]
    return {f"{SOIL_EVENT_SERIES} rows + {', '.join(SOIL_EVENT_COLUMN_PREFIXES)}*":
            has_rows and all(name in columns for name in wanted)}


# ------------------------------------------------------------------------- rev7 R7-1a tag check
T4H_FILE_KEY = "t4h_file"
"""r79 result key with the T4h record's file name (``r79_sensor_screen.write_t4h``)."""
T4H_META_KEY = "meta_json"
"""T4h npz entry with the run meta as a JSON string (it holds ``controller_tag``)."""
T4H_DIR_SUFFIX = "_t4h"
"""``<result stem>_t4h/``: the T4h folder of ``resume_k1_steps`` and ``run_v5`` outputs."""
T4H_SIBLING_DIR = "t4h"
"""``t4h/`` next to the result: the T4h folder of ``las_t3`` Dg-3 runs."""
TAG_MATCH = "match"
TAG_STOP = "S-2"
METHOD_T4H = "t4h_meta"
"""Rev7 R7-1a: a run with ``t4h_file`` compares with its T4h meta tag."""
METHOD_RECOMPUTE = "recompute"
"""Rev8 R8-1: a run without ``t4h_file`` compares with the tag recomputed from its switches."""
TAG_CHECK_RULE = ("rev7 R7-1a / rev8 R8-1: r79 (H-6 .. H-8) / grid (H-9) top-level controller_tag "
                  "= T4h meta controller_tag (runs with t4h_file) or the tag recomputed from the "
                  "recorded switches (runs without); different, one side only or not computable = "
                  "S-2 (G-S: not computable also S-11)")

# rev8 R8-1b inputs and R8-1c tag rules (sealed text; the same results as
# ``v5_options.controller_tag``, but written from the rule, not imported)
TAG_BASE_EXTEND_START = "final_C4G2_P3"
TAG_BASE_PLAIN = "final_C4G2"
TAG_SUFFIX_LAS = "_LAS"
TAG_SUFFIX_K1 = "_K1"
HYDRAULIC_OPTIONS_KEY = "hydraulic_options"
EXTEND_START_OPTION_KEY = "extend_start_tracked"
EXTEND_START_SETTING_KEY = "two_pressure.extend_start_rule"
"""One dotted key of ``controller_settings`` (dg3 records only)."""
EXTEND_START_TRACKED_RULE = "tracked_bound"
LAS_ENABLE_PATH = "liftoff_approach_slow.settings.enable"
K1_GATE_PATH = "slope_clearance_margin.settings.flat_soil_margin_order_gate"


class TagNotComputable(Exception):
    """Rev8 R8-1b "재계산 불가": a switch the tag rule needs is not recorded (S-2, G-S S-11)."""


def recompute_tag(is_extend_start: bool, is_las_on: bool, is_k1_on: bool) -> str | None:
    """Rev8 R8-1c as rewritten by rev9 R9-7: ``final_C4G2_P3`` with ③, then ``_LAS``, then
    ``_K1`` at the end (without ③ the base of a suffix is ``final_C4G2``: K1 alone =
    ``final_C4G2_K1``, ③ + K1 without LAS-b = ``final_C4G2_P3_K1``); None (no tag) when ③,
    LAS-b and K1 are all off. No ``_TCL`` (no TCL field is recorded and TCL is forbidden,
    original 4.2)."""
    tag = TAG_BASE_EXTEND_START if is_extend_start else None
    if is_las_on:
        tag = (tag or TAG_BASE_PLAIN) + TAG_SUFFIX_LAS
    if is_k1_on:
        tag = (tag or TAG_BASE_PLAIN) + TAG_SUFFIX_K1
    return tag


def _switch_pair(block: Any, where: str, *, need_applicable: bool) -> tuple[bool, bool]:
    """(LAS-b enable, K1 order gate) of one ``resume_k1`` block (R8-1b)."""
    if not isinstance(block, dict):
        raise TagNotComputable(f"{where}{RECORD_KEY} block missing")
    if need_applicable and block.get("applicable") is not True:
        raise TagNotComputable(f"{where}{RECORD_KEY}.applicable {block.get('applicable')!r}")
    values = []
    for dotted in (LAS_ENABLE_PATH, K1_GATE_PATH):
        present, value = get_path(block, dotted)
        if not present or not isinstance(value, bool):
            raise TagNotComputable(f"{where}{RECORD_KEY}.{dotted} missing or not a bool")
        values.append(value)
    return values[0], values[1]


def _extend_start_switch(record: dict) -> bool:
    """R8-1b ③: ``hydraulic_options.extend_start_tracked`` true = on; the block without the key
    = off (``HydraulicOptions.to_dict`` keeps the key only when on)."""
    options = record.get(HYDRAULIC_OPTIONS_KEY)
    if not isinstance(options, dict):
        raise TagNotComputable(f"{HYDRAULIC_OPTIONS_KEY} block missing")
    return options.get(EXTEND_START_OPTION_KEY) is True


def recorded_switch_problems(record: dict, is_extend_start: bool, switches: tuple[bool, bool]
                             ) -> list[str]:
    """R8-1b cross checks that are S-2 on their own: the dg3 ``extend_start_rule`` against ③
    and every grid run's LAS-b / K1 values against its job record."""
    problems = []
    settings = record.get("controller_settings")
    if isinstance(settings, dict) and EXTEND_START_SETTING_KEY in settings:
        rule = settings[EXTEND_START_SETTING_KEY]
        if (rule == EXTEND_START_TRACKED_RULE) != is_extend_start:
            problems.append(f"controller_settings {EXTEND_START_SETTING_KEY} {rule!r} but "
                            f"{EXTEND_START_OPTION_KEY} {is_extend_start}")
    for index, run in enumerate(record.get("runs") or []):
        where = f"runs[{index}]."
        run_switches = _switch_pair(run.get(RECORD_KEY) if isinstance(run, dict) else None,
                                    where, need_applicable=False)
        if run_switches != switches:
            problems.append(f"{where}{RECORD_KEY} LAS-b / K1 {run_switches} != job {switches}")
    return problems


def _tag_recompute_record(record: dict) -> dict:
    """Rev8 R8-1 for one r79 result or grid job record without ``t4h_file``."""
    top_tag = record.get("controller_tag")
    row: dict[str, Any] = {"key": record_key(record), "method": METHOD_RECOMPUTE,
                           "t4h_file": None, "top_tag": top_tag, "recomputed_tag": None,
                           "not_computable": False}
    try:
        is_extend_start = _extend_start_switch(record)
        switches = _switch_pair(record.get(RECORD_KEY), "", need_applicable=True)
        problems = recorded_switch_problems(record, is_extend_start, switches)
    except TagNotComputable as exc:
        return {**row, "status": TAG_STOP, "not_computable": True,
                "reason": f"tag not computable: {exc}"}
    recomputed = recompute_tag(is_extend_start, *switches)
    row["recomputed_tag"] = recomputed
    if problems:
        return {**row, "status": TAG_STOP, "reason": "; ".join(problems)}
    if top_tag == recomputed:
        return {**row, "status": TAG_MATCH, "reason": None}
    if top_tag is None or recomputed is None:
        side = "recomputed tag" if top_tag is None else "top level"
        return {**row, "status": TAG_STOP, "reason": f"controller_tag on the {side} only"}
    return {**row, "status": TAG_STOP, "reason": "top-level controller_tag differs from the "
                                                 "tag recomputed from the recorded switches"}


def t4h_folders(result_path: Path, extra_dirs: list[Path] | tuple[Path, ...] = ()) -> list[Path]:
    """Folders searched for a run's T4h file, in order: the given ones, then the two runner
    conventions next to the result file."""
    path = Path(result_path)
    return [*(Path(d) for d in extra_dirs), path.with_name(f"{path.stem}{T4H_DIR_SUFFIX}"),
            path.parent / T4H_SIBLING_DIR]


def t4h_meta_tag(path: Path) -> tuple[bool, str | None]:
    """(meta readable, ``controller_tag`` of the meta) of one T4h npz (never loads pickles)."""
    import numpy as np

    try:
        with np.load(path, allow_pickle=False) as data:
            if T4H_META_KEY not in data.files:
                return False, None
            meta = json.loads(str(data[T4H_META_KEY].item()))
    except (OSError, ValueError) as exc:  # json.JSONDecodeError is a ValueError
        print(f"T4h meta of {path} unreadable: {exc}", file=sys.stderr)
        return False, None
    if not isinstance(meta, dict):
        return False, None
    return True, meta.get("controller_tag")


def _tag_compare_record(record: dict, folders: list[Path]) -> dict:
    """R7-1a (with ``t4h_file``) or R8-1 (without) for one r79 result or grid job record:
    status ``match`` / ``S-2``. A listed T4h file that is not found is S-2, never recomputed
    (R8-1a)."""
    name = record.get(T4H_FILE_KEY)
    if not name:
        return _tag_recompute_record(record)
    top_tag = record.get("controller_tag")
    row: dict[str, Any] = {"key": record_key(record), "method": METHOD_T4H, "t4h_file": name,
                           "top_tag": top_tag, "t4h_tag": None, "not_computable": False}
    found = next((folder / str(name) for folder in folders if (folder / str(name)).is_file()),
                 None)
    if found is None:
        return {**row, "status": TAG_STOP,
                "reason": f"{T4H_FILE_KEY} not found in {[str(f) for f in folders]} (no meta tag)"}
    is_readable, t4h_tag = t4h_meta_tag(found)
    row.update(t4h_path=str(found), t4h_tag=t4h_tag)
    if not is_readable:
        return {**row, "status": TAG_STOP, "reason": f"T4h {T4H_META_KEY} missing or unreadable"}
    if top_tag == t4h_tag:
        return {**row, "status": TAG_MATCH, "reason": None}
    if top_tag is None or t4h_tag is None:
        side = "T4h meta" if top_tag is None else "top level"
        return {**row, "status": TAG_STOP, "reason": f"controller_tag on the {side} only"}
    return {**row, "status": TAG_STOP, "reason": "top-level controller_tag differs from T4h meta"}


def tag_check_records(document: Any) -> list[dict]:
    """The R7-1a records of one document: r79 results and the job records of a grid file."""
    results = document.get("results") if isinstance(document, dict) else None
    if not isinstance(results, list):
        return [document] if isinstance(document, dict) and is_r79_record(document) else []
    if is_grid_document(document):
        return [row for row in results if isinstance(row, dict)]
    return [row for row in results if isinstance(row, dict) and is_r79_record(row)]


def r79_tag_check(paths: list[Path], t4h_dirs: list[Path] | tuple[Path, ...] = (),
                  *, with_values: bool = True) -> dict:
    """Rev7 R7-1a and rev8 R8-1 over harness outputs (every run is compared, R8-1d).

    Args:
        paths: Harness output files (r79 / grid ``.json``, ``.jsonl``); other runs are skipped.
        t4h_dirs: Extra T4h folders searched before the runner conventions.
        with_values: Keep the tag values in the rows (``gs`` reports presence only, so False).

    Returns:
        Counts (``compared``, ``by_method``, ``mismatched`` with the not computable ones,
        ``not_computable``), the ``S-2`` rows, ``stop_S2`` (a mismatch anywhere) and
        ``stop_S11_not_computable`` (what G-S also counts as S-11).
    """
    rows = []
    for path in paths:
        folders = t4h_folders(Path(path), t4h_dirs)
        for document in read_records(Path(path)):
            for record in tag_check_records(document):
                rows.append({"file": str(path), **_tag_compare_record(record, folders)})
    mismatched = [r for r in rows if r["status"] == TAG_STOP]
    not_computable = sum(r["not_computable"] for r in rows)
    by_method = Counter(r["method"] for r in rows)
    if not with_values:
        hidden = ("top_tag", "t4h_tag", "recomputed_tag")
        mismatched = [{k: v for k, v in r.items() if k not in hidden} for r in mismatched]
    return {"rule": TAG_CHECK_RULE, "compared": len(rows),
            "by_method": {METHOD_T4H: by_method[METHOD_T4H],
                          METHOD_RECOMPUTE: by_method[METHOD_RECOMPUTE]},
            "mismatched": len(mismatched), "not_computable": not_computable,
            "rows": mismatched, "stop_S2": bool(mismatched),
            "stop_S11_not_computable": bool(not_computable)}


def gs(args: argparse.Namespace) -> dict:
    files = []
    for path in args.harness:
        docs = read_records(Path(path))
        runs = [record for doc in docs for _, record in run_records(doc)]
        if not runs:
            files.append({"file": str(path), "runs": 0, "missing": ["<no run record>"]})
            continue
        presence: dict[str, bool] = {}
        for record in runs:
            found_keys = {**gs_presence(record), **hash_presence(record), **rev4_presence(record)}
            for key, ok in found_keys.items():
                presence[key] = presence.get(key, True) and ok
        grid_runs = 0
        for doc in docs:
            if is_grid_document(doc):
                count, found = grid_run_presence(doc)
                grid_runs += count
                presence.update(found)
        head_only = sum(any(get_path(r, k)[0] for k in HEAD_ONLY_KEYS) for r in runs)
        files.append({"file": str(path), "runs": len(runs), "grid_runs": grid_runs,
                      "missing": sorted(key for key, ok in presence.items() if not ok),
                      "head_only_declared_present": f"{head_only}/{len(runs)}"})
    for batch_dir in getattr(args, "chrono", None) or []:  # rev4: PS-c series columns
        for case in _batch_rows(Path(batch_dir)):
            found = soil_event_series_presence(Path(batch_dir) / case)
            if found:
                files.append({"file": str(Path(batch_dir) / case), "runs": 1,
                              "missing": sorted(k for k, ok in found.items() if not ok)})
    bad = [f for f in files if f["missing"]]
    tag_check = r79_tag_check(args.harness, getattr(args, "t4h_dir", None) or (),
                              with_values=False)
    return {
        "rules": RULES_NAME,
        "section": "11.2 (+ rev3: command hash, extend_bound_check, head_only_declared, "
                   "settle_v2; rev4 R4-D: F-1 .. F-6 and the meaning checks; rev7 R7-1a / rev8 "
                   "R8-1 tags)",
        "files": files,
        "files_with_missing": len(bad),
        "r79_tag_check": tag_check,
        "stop_S2": tag_check["stop_S2"],
        # rev8 R8-1d: a tag that cannot be recomputed is also a G-S key failure (S-11)
        "stop_S11": bool(bad) or tag_check["stop_S11_not_computable"],
        "exit_code": 1 if bad or tag_check["stop_S2"] else 0,
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
    if actual == APPENDIX_B[entry]:
        return entry, []
    try:
        normalised = lf_normalised_sha256(Path(path).read_bytes())
    except OSError as exc:
        raise InputError(f"{path}: {exc}") from exc
    if normalised == APPENDIX_B[entry]:  # rev3 R3-F4: pass, disclosed by crlf_only_files()
        CRLF_ONLY_FILES[entry] = {"raw_sha256": actual, "lf_normalised_sha256": normalised}
        return entry, []
    return entry, [f"{entry} sha256 {actual[:16]} != {APPENDIX_B[entry][:16]} (S-1)"]


CRLF_ONLY_FILES: dict[str, dict] = {}
"""Appendix B files of this process that matched only after CRLF -> LF (rev3 R3-F4); every
report lists them under ``crlf_only`` ("CRLF 변환만 다름")."""


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


R79_HASH_KEY = "commands_sha256"
"""Rev3 R3-E4: the one place an r79 result keeps its command hash (top level)."""
R79_CANDIDATE_PREFIX = "cand=current#"
SEEDEXT_NOISE_SEEDS = range(5)
"""Rev1 RV1-3.2: seedext keys of seeds 0..4 are noise keys too (10 keys per setting)."""


def r79_key(key: Any) -> str:
    """Rev3 R3-D1: ``cand=current#<key>`` and ``<key>`` are the same key."""
    text = str(key)
    return text[len(R79_CANDIDATE_PREFIX):] if text.startswith(R79_CANDIDATE_PREFIX) else text


def _r79_hashes(path: Path) -> dict[str, Any]:
    return {r79_key(row.get("key")): row.get(R79_HASH_KEY)
            for row in read_json(path).get("results") or []}


def hash_pairs(first: dict[str, Any], second: dict[str, Any], keys) -> dict:
    """Per key whether the two top-level hashes are the same (None: one is missing)."""
    rows = []
    for key in keys:
        a, b = first.get(key), second.get(key)
        rows.append({"key": key, "a": a, "b": b,
                     "same": None if a is None or b is None else a == b})
    return {"keys": len(rows), "same": sum(row["same"] is True for row in rows),
            "differ": [row["key"] for row in rows if row["same"] is False],
            "missing": [row["key"] for row in rows if row["same"] is None], "rows": rows}


def _seed_index(key: str) -> int | None:
    parts = key.split("|")
    return int(parts[1][1:]) if len(parts) > 1 and parts[1].startswith("s") else None


def dg3_hash(args: argparse.Namespace) -> dict:
    """RV1-3.2 records with the rev3 R3-E4 hash (top-level ``commands_sha256`` only): H-6 vs
    H-8 VB per dg3 key, and with ``--seedext`` / ``--noise`` the seedext seed 0..4 keys vs the
    noise lines (per setting pair). A missing hash makes the record 기록 불완전, never a stop."""
    h6 = _r79_hashes(Path(args.h6))
    out: dict[str, Any] = {"rules": RULES_REV3_NAME, "section": "RV1-3.2 / R3-E4 (record)",
                           "hash_field": R79_HASH_KEY}
    if args.h8_vb is not None:
        out["h6_vs_h8_vb"] = hash_pairs(h6, _r79_hashes(Path(args.h8_vb)), sorted(h6))
    for seedext, noise in zip(args.seedext or [], args.noise or [], strict=True):
        seed_hashes = _r79_hashes(Path(seedext))
        keys = sorted(key for key in seed_hashes if _seed_index(key) in SEEDEXT_NOISE_SEEDS)
        out.setdefault("seedext_vs_noise", []).append(
            {"seedext": str(seedext), "noise": str(noise),
             **hash_pairs(seed_hashes, _r79_hashes(Path(noise)), keys)})
    blocks = [out.get("h6_vs_h8_vb"), *out.get("seedext_vs_noise", [])]
    is_incomplete = any(block and block["missing"] for block in blocks)
    return {**out, "record_state": "기록 불완전" if is_incomplete else "기록",
            "note": "a difference is recorded and handed to python-expert; it is no stop",
            "exit_code": 0}


# --------------------------------------------------------------- rev3 R3-E1 / R3-E2 grid V0, F
GRID_FILES = ("grid_r67_main", "grid_r67_top", "grid_r69_bottom", "grid_r69_top")
FAMILY_F_KEYS = ("screen|top|0.0|ready|FR", "screen|top|0.0|ready|FL")
FAMILY_F_EVENT = "FS24"
FAMILY_F_GATES = ("Fmin_after_W", "U57_outside")
FAMILY_F_M = 4
FAMILY_F_M_SUM = 6
FAMILY_F_RUNS = 64


def _results_by_key(path: Path) -> dict[str, dict]:
    return {row.get("key"): row for row in read_json(path).get("results") or []}


def _run_hashes(result: dict | None) -> dict[tuple, Any]:
    """(event, offset) -> ``commands_sha256`` of a grid result's runs."""
    return {(run.get("event"), float(run.get("offset_s"))): run.get("commands_sha256")
            for run in (result or {}).get("runs") or []}


def sample_job_runs(stored: dict, sample: dict | None) -> dict:
    """Rev4 R4-B4: one sample job = one stored result; every run is paired by (event, offset)
    and must have the same hash."""
    old, new = _run_hashes(stored), _run_hashes(sample)
    missing = sum(1 for k in old if old[k] is None or new.get(k) is None) + len(set(new) - set(old))
    differ = sum(1 for k in old if old[k] is not None and new.get(k) is not None
                 and old[k] != new[k])
    return {"runs": len(old), "differ": differ, "missing": missing}


def grid_v0_sample(args: argparse.Namespace) -> dict:
    """R3-E1 / R4-B4: the 8-job V0 sample (per stored file the first and the last result; every
    run of the job, paired by (stem, key, event, offset)) against the stored V0 grid by
    ``commands_sha256``; all same -> the stored V0 is the pair, otherwise V0 768 runs
    (``resume_k1/h9_grid_v0/``)."""
    rows, problems = [], []
    for name in GRID_FILES:
        stored_path = Path(args.stored_dir) / f"{name}.json"
        stored = read_json(stored_path).get("results") or []
        sample = _results_by_key(Path(args.sample_dir) / f"{name}.json")
        for row in (stored[0], stored[-1]) if stored else ():
            key = row.get("key")
            compared = sample_job_runs(row, sample.get(key))
            if compared["missing"]:
                problems.append(f"{name} {key}: {compared['missing']} runs without a pair or hash")
            rows.append({"file": name, "key": key, "stored_sha256_file": file_sha256(stored_path),
                         **compared,
                         "same": None if compared["missing"] else compared["differ"] == 0})
    if len(rows) != 2 * len(GRID_FILES):
        problems.append(f"{len(rows)} sample jobs, 8 expected")
    is_all_same = not problems and all(row["same"] for row in rows)
    return {"rules": RULES_REV3_NAME, "section": "R3-E1", "jobs": len(rows),
            "same": sum(row["same"] is True for row in rows), "rows": rows,
            "decision": ("stored V0 is the pair (저장(옛 V0 제어기), 표본 해시 같음)" if is_all_same
                         else "run V0 768: steps_conditional_h9_grid_v0.json"),
            "v0_768_required": not is_all_same, "problems": problems,
            "exit_code": 1 if problems else 0}


def _family_rows(grid_dir: Path) -> dict[tuple[str, float], list[dict]]:
    """(key, offset) -> the FS24 runs of the family F keys in grid_r67_main / grid_r67_top."""
    rows: dict[tuple[str, float], list[dict]] = {}
    for name in ("grid_r67_main", "grid_r67_top"):
        for key, result in _results_by_key(grid_dir / f"{name}.json").items():
            if key not in FAMILY_F_KEYS:
                continue
            for run in result.get("runs") or []:
                if run.get("event") == FAMILY_F_EVENT:
                    rows.setdefault((key, float(run.get("offset_s"))), []).append(run)
    return rows


def _failed_gates(run: dict) -> set[str]:
    return {name for name, ok in (run.get("gates") or {}).items() if ok is False}


def family_f_trigger(args: argparse.Namespace) -> dict:
    """R3-E2: a family F row (12 = 4 phases x 2 keys) with V0 pass and VB fail by
    ``Fmin_after_W`` / ``U57_outside`` only starts the conditional 64 runs."""
    vb, v0 = _family_rows(Path(args.vb_dir)), _family_rows(Path(args.v0_dir))
    rows = []
    for (key, offset), vb_runs in sorted(vb.items()):
        v0_runs = v0.get((key, offset)) or []
        is_v0_pass = bool(v0_runs) and all(run.get("pass") for run in v0_runs)
        only_two = [bool(_failed_gates(run)) and _failed_gates(run) <= set(FAMILY_F_GATES)
                    for run in vb_runs]
        rows.append({"key": key, "offset_s": offset, "vb_runs": len(vb_runs),
                     "v0_pass": is_v0_pass, "vb_fail_by_the_two_gates_only": any(only_two),
                     "trigger": is_v0_pass and any(only_two)})
    is_trigger = any(row["trigger"] for row in rows)
    problems = [] if len(rows) == 8 else [f"{len(rows)} family F (key, phase) rows, 8 expected"]
    return {"rules": RULES_REV3_NAME, "section": "R3-E2", "rows": rows,
            "family_rows_with_duplicates": sum(row["vb_runs"] for row in rows),
            "trigger": is_trigger,
            "decision": "run steps_conditional_h9_family_f.json (64 runs)" if is_trigger
            else "5.2 runs 해당 없음", "problems": problems,
            "exit_code": 1 if problems else 0}


def family_f(args: argparse.Namespace) -> dict:
    """v5 criteria rev5 5.2 R-1 .. R-4 on ``h9_family_F.jsonl`` (64 lines)."""
    lines = read_records(Path(args.lines))
    by = {(line.get("setting"), line.get("key"), float(line.get("offset_s"))): line
          for line in lines}
    problems = [] if len(lines) == FAMILY_F_RUNS == len(by) else [
        f"{len(lines)} lines ({len(by)} distinct), {FAMILY_F_RUNS} expected (S-15)"]

    def fails(line: dict) -> bool:
        return bool(_failed_gates(line) & set(FAMILY_F_GATES))

    k = {(s, key): sum(fails(line) for (s2, key2, _), line in by.items() if (s2, key2) == (s, key))
         for s in ("V0", "VB") for key in FAMILY_F_KEYS}
    r1 = {key: k[("VB", key)] <= k[("V0", key)] + FAMILY_F_M for key in FAMILY_F_KEYS}
    r2 = (sum(k[("VB", key)] for key in FAMILY_F_KEYS)
          <= sum(k[("V0", key)] for key in FAMILY_F_KEYS) + FAMILY_F_M_SUM)
    vb_lines = [line for (s, _, _), line in by.items() if s == "VB"]
    r3_bad = [(line["key"], line["offset_s"]) for line in vb_lines
              if (line.get("gates") or {}).get("fault0") is False
              or line.get("final_phase") != "ready"]
    r4_bad = []
    for (s, key, offset), line in by.items():
        if s != "VB":
            continue
        other = by.get(("V0", key, offset))
        new = _failed_gates(line) - set(FAMILY_F_GATES)
        old = set() if other is None else _failed_gates(other)
        if new - old:
            r4_bad.append({"key": key, "offset_s": offset, "gates": sorted(new - old)})
    is_pass = all(r1.values()) and r2 and not r3_bad and not r4_bad and not problems
    return {"rules": RULES_REV3_NAME, "section": "R3-E2 / rev5 5.2",
            "k": {f"{s}|{key}": n for (s, key), n in k.items()},
            "R-1": r1, "R-2": r2, "R-3_violations": r3_bad, "R-4_violations": r4_bad,
            "m": FAMILY_F_M, "m_sum": FAMILY_F_M_SUM, "pass": is_pass,
            "decision": "the 12 family F rows leave H-10 for the two gates" if is_pass
            else "H-10: stop and ask", "problems": problems,
            "exit_code": 0 if is_pass else 1}


# --------------------------------------------------------------------- rev3 R3-B5 IND_LAS
LAS_START_EVENT = "INFO_LIFTOFF_SLOW:"
LAS_EVENTS_KEY = "liftoff_slow_events"
"""``b5_baseline_compare`` record field (record only): the ``INFO_LIFTOFF_SLOW*`` event names."""


def ind_las(args: argparse.Namespace) -> dict:
    """R3-B5: IND_LAS cases without a LAS-b start event (``INFO_LIFTOFF_SLOW:``; the ``_END:``
    name does not count) must have the IND ``commands_sha256`` of the same case."""
    records = [r for path in args.harness for doc in read_records(Path(path))
               for r in (doc.get("records") or doc.get("results") or [doc])]
    ind = {r.get("case"): r for r in records if r.get("controller") == "IND"}
    rows = []
    for record in (r for r in records if r.get("controller") == "IND_LAS"):
        names = record.get(LAS_EVENTS_KEY)
        if not isinstance(names, list):
            rows.append({"case": record.get("case"), "gate": "판독 불가"})
            continue
        started = any(str(name).startswith(LAS_START_EVENT) for name in names)
        row = {"case": record.get("case"), "gate": "선" if started else "서지 않음"}
        if not started:
            other = ind.get(record.get("case"))
            row["same_hash_as_ind"] = (None if other is None else
                                       record.get("commands_sha256") == other.get(
                                           "commands_sha256"))
        rows.append(row)
    unreadable = sum(row["gate"] == "판독 불가" for row in rows)
    not_started = [row for row in rows if row["gate"] == "서지 않음"]
    differ = [row["case"] for row in not_started if row.get("same_hash_as_ind") is False]
    return {"rules": RULES_REV3_NAME, "section": "R3-B5", "cases": len(rows),
            "gate_started": sum(row["gate"] == "선" for row in rows),
            "gate_not_started": len(not_started),
            "not_started_same_hash": sum(row.get("same_hash_as_ind") is True
                                         for row in not_started),
            "not_started_differ": differ, "gate_unreadable": unreadable,
            "record_state": "기록 불완전" if unreadable else "기록",
            "adapter_defect": bool(differ), "rows": rows,
            "exit_code": 1 if differ else 0}


# ------------------------------------------------------------------- rev3 TABLE_REAGG items
REAGG_ITEMS = {
    "H-1 / H-2 (R3-A2)": ["H-S P3", "H-S G6", "H-S E", "H-R 잠김 350 bar", "H-R G6"],
    "C-5 (R3-G1)": ["T4-0", "T4", "T5", "J11 창", "J-P3", "D2"],
    "PS-c (R3-G1)": ["E-1", "E-2", "E-3", "E-4", "E-6", "E-7"],
    "H-6 / H-8 잡음 (R3-E3)": ["S-1", "S-2", "S-3", "S-4", "S-5", "S-6"],
}
"""Rev3: the items whose two paths are a re-aggregation of the recorded item results (not an
independent recalculation); the judgement's TABLE_REAGG lists them (R3-G1, R3-E3)."""


def reagg_items(args: argparse.Namespace) -> dict:
    """The TABLE_REAGG rows (bundle, items, item count) for the judgement document."""
    rows = [{"bundle": bundle, "items": items, "count": len(items)}
            for bundle, items in REAGG_ITEMS.items()]
    markdown = ["| 묶음 | 재집계 항목 | 수 |", "|---|---|---|"]
    markdown += [f"| {row['bundle']} | {', '.join(row['items'])} | {row['count']} |"
                 for row in rows]
    return {"rules": RULES_REV3_NAME, "section": "R3-G1 / R3-E3 TABLE_REAGG", "rows": rows,
            "markdown": "\n".join(markdown), "exit_code": 0}


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
        # no abbreviations: the removed first-match ``--anchor`` must not mean ``--anchor-map``
        p = sub.add_parser(name, help=helptext, allow_abbrev=False)
        p.add_argument("--harness", nargs="*", type=Path, help="harness jsonl / json outputs")
        p.add_argument(
            "--chrono", nargs="*", type=Path, help="Chrono batch folders (batch.json + <case>/)"
        )
        p.add_argument("--all", action="store_true", help="list every run, not only the findings")
        p.add_argument("--out", type=Path, required=True)
        if name == "record-check":
            p.add_argument("--t4h-dir", type=Path, action="append", default=[],
                           help="T4h folder searched first (repeatable; rev7 R7-1a)")
        if name == "k1-class":
            p.add_argument("--anchor-map", type=Path, default=None,
                           help="anchor-map report (RV1-5 selection, the only anchor input)")
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
    p.add_argument("--harness", nargs="*", type=Path, default=[])
    p.add_argument("--chrono", nargs="*", type=Path, default=[],
                   help="Chrono batch folders: PS-c soil_event_series.npz columns (rev4)")
    p.add_argument("--t4h-dir", type=Path, action="append", default=[],
                   help="T4h folder searched first (repeatable; rev7 R7-1a)")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("keyset",
                       help="rev1 RV1-3: new H-6 .. H-9 grid output vs stored keys (S-15)")
    p.add_argument("--kind", required=True, choices=("r79", "grid"))
    p.add_argument("--new", type=Path, required=True, help="new runner output (.json)")
    p.add_argument("--stored", type=Path, required=True, help="appendix B file under v5/")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("dg3-hash", help="rev1 RV1-3.2: H-6 vs H-8 VB commands_sha256 (record)")
    p.add_argument("--h6", type=Path, required=True)
    p.add_argument("--h8-vb", type=Path, default=None)
    p.add_argument("--seedext", nargs="*", type=Path, help="h8_seedext_{VB,V0}.json")
    p.add_argument("--noise", nargs="*", type=Path, help="h8_noise_{VB,V0}.json, same order")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("grid-v0-sample", help="rev3 R3-E1: V0 grid 8-job sample vs stored V0")
    p.add_argument("--sample-dir", type=Path, required=True, help="resume_k1/h9_grid_v0_sample")
    p.add_argument("--stored-dir", type=Path, required=True,
                   help="06_analysis/02_control/touch_phase/acceptance/c4g2_only/grid")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("family-f-trigger", help="rev3 R3-E2: does family F start the 64 runs")
    p.add_argument("--vb-dir", type=Path, required=True, help="resume_k1/h9_grid")
    p.add_argument("--v0-dir", type=Path, required=True, help="the V0 pair grid folder")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("family-f", help="rev3 R3-E2: rev5 5.2 R-1 .. R-4 on h9_family_F.jsonl")
    p.add_argument("--lines", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("ind-las", help="rev3 R3-B5: IND_LAS gate and the IND hash")
    p.add_argument("--harness", nargs="+", type=Path, required=True,
                   help="U-6 outputs with the IND and IND_LAS records")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("reagg-items", help="rev3: TABLE_REAGG rows")
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
    "grid-v0-sample": grid_v0_sample,
    "family-f-trigger": family_f_trigger,
    "family-f": family_f,
    "ind-las": ind_las,
    "reagg-items": reagg_items,
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
    """Rev1 .. rev10 seals (:data:`SEALED_REVISIONS`); any problem is ``stop_S1``."""
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
        if CRLF_ONLY_FILES:  # rev3 R3-F4 disclosure
            report["appendix_b_crlf_only"] = {
                name: {**values, "note": "CRLF 변환만 다름"}
                for name, values in CRLF_ONLY_FILES.items()}
    report["rules_sha256"] = RULES_SHA256
    report["rules_rev1_sha256"] = RULES_REV1_SHA256
    report["rules_rev2_sha256"] = RULES_REV2_SHA256
    report["rules_rev3_sha256"] = RULES_REV3_SHA256
    report["rules_rev4_sha256"] = RULES_REV4_SHA256
    report["rules_rev7_sha256"] = RULES_REV7_SHA256
    report["rules_rev8_sha256"] = RULES_REV8_SHA256
    report["rules_rev9_sha256"] = RULES_REV9_SHA256
    report["rules_rev10_sha256"] = RULES_REV10_SHA256
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
