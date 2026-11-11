"""LAS-b P5r4 + K1 re-judgement, path 1 harness judge (bundles Z-0, Z-A, Z-T, Z-S, Z-C, Z-X).

Rules: the sealed new original ``las_p5r4_k1_rules.md`` (control-expert, LF sha256
:data:`RULES_SHA256`) and the ten rules files of its section 0 table (all sealed, all checked
before anything is judged, S-1). The rules text wins where this code differs; section numbers
in the comments are the rules'. Addenda (``las_p5r4_k1_rules_rev<n>.md``) go into
:data:`RULES_ADDENDA` once they are sealed.

This module reads JSON lines only (standard library, no project module, no other judging tool
imported; rules 0.1 3 / 11.1). The functions marked "copied from" are copies of the sealed
tools, not imports; the source file and its git blob / LF sha256 at copy time are in
:data:`COPIED_FROM` and in every output document. ``las_p5r4k1_targeted.py`` (the run tool)
imports the constants and the line checks of this module.

What it judges
  4.4    bit predictions BT-0, BT-A, BT-T, BT-S, BT-CR, BT-X (a mismatch is ``stop``), and the
         G-S / main-run hash equality of 16.2 (same / different only).
  6.1    Z-A: G-1 / G-1H / G-1Q, G-2' (11.414589 kN), G-3, G-4 (K-A1 .. K-A8 against the stored
         P5 pairs; K-A5 / K-A6 / K-A8 mismatches are ``stop``).
  6.2    Z-T / Z-S / Z-C pairs (cand - ref, full key): C-2 type, P3, C-1 (Z-T), C-F, C-S,
         CK-1 (``R4_LOST``; ``R4_GAINED`` FLAG), A-3 (Z-T), R-1 / R-2 (Z-T, Z-C; Z-S record)
         over the changed-hash population with the C-4 exception (Z-X DONE record, restarts
         after the end ramp).
  3      ``PAIR_DIVERGE`` (cand LAS-b not started and the hashes differ: ``stop``) and the
         ``PAIR_CMD_DIFF`` count.
  9      K-0 .. K-5, K-8, K-9 of the harness lines (a problem is ``stop``).
  6.4    the per-pair record, FLAGs, the in-sample (R-S overlap) / out-of-sample split of Z-C,
         and the rev1 record items (RV1-1 correction path by event name, LOC count, t_L / t_P
         first and last of both arms, raw and applied bias; RV1-2 FLAG ``ANCHOR_SAMPLE_SHIFT``;
         RV1-3 ``anchor_effect_possible`` / ``anchor_effect_unknown``; record only).
  8 / 16.6  status per criterion, bundle and final: ``stop`` > ``undecidable`` (판정 불가,
         ``incomplete`` included) > ``미달`` > ``통과``; lists are never truncated.

The grade is PROVISIONAL: ``k10`` is null until the path 2 recount agrees (10.2).

Usage (python-dev or dynamics-dev, project root, PowerShell):
  python -I -B 06_analysis/02_control/verif_matrix/scripts/las_p5r4k1_judge.py
      [--run-dir <v5/las/p5r4k1>] [--v5-dir <v5>] [--gs-dir <v5/las/p5r4k1/gs>]
      [--expect-judge-sha <sha>] [--out <json>]
Exit codes: 0 provisional 통과, 1 미달 / 판정 불가 / an ask (S-8), 2 stop or an input error
(seals, stored files, lists), 3 tool error. The first stdout line says the grade is
provisional; the last stdout line is JSON.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TOOL_PATH = Path(__file__).resolve()
ROOT = TOOL_PATH.parents[4]
RULES_DIR = ROOT / "06_analysis" / "02_control" / "verif_matrix"
V5_DIR = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5"
RUN_DIR_RELATIVE = Path("las") / "p5r4k1"
GS_DIR_NAME = "gs"
LINE_FILE_PATTERN = "p5k_Z*.jsonl"
GS_FILE_PATTERN = "p5k_GS*.jsonl"
GRID_UNIT_SEPARATOR = "#"

# ------------------------------------------------------------------------------- seals (S-1)
RULES_NAME = "las_p5r4_k1_rules.md"
RULES_SHA256 = "5ee2bac0451f0ca00139a5a2d238c38d13a6b0f430efc5b44fe0e8b929c2f979"
"""``las_p5r4_k1_rules.sha256`` (LF digest, sealed 2026-11-11 09:29:16 +09:00)."""
INHERITED_RULES = {
    "las_rev_targeted_rules.md":
        "bb235f27567240b205a544ed7cfd10237827e4627088e0eab1f62b318416ff60",
    "las_rev_targeted_rules_rev1.md":
        "672bc8f81ba75419e5a201e05a94e2f9aead2de3c205f80c2661e7474cd9fd51",
    "las_revA_targeted_rules.md":
        "b09d004bb2f641db40cdd139a6fb2b1645651e4a3e45a9b16e81a5c938d5778f",
    "las_revA_targeted_rules_rev1.md":
        "c02518021c00b69a9d02ec6bceddbea18b9686ef6de96bafe5e55b716b023960",
    "las_revA_targeted_rules_rev2.md":
        "9f478b7fbc5aa0bd8859716b056bf2d531ac02057dc36d218bada7d7f13e4565",
    "las_revA_targeted_rules_rev3.md":
        "98082a368da626f90ce3b0a41f5c74145b4095c155f14b2b2f63eb319352d709",
    "las_k1_rules.md": "2742c9760ad55a87eccbf73e84025aafe0171a3555e1f54ab19fab24d888e4a0",
    "las_k1_rules_rev1.md": "eeee4ab9661babff50117b8ff579aa41e27a98d083f1fc13f46fb5c733e0b4d3",
    "las_k1_rules_adopt.md": "864836d852b4a783a577f01f738536b7c30c574bf4bebb3b0219e68e59b07ea8",
    "las_k1_rules_adopt2.md": "fb3a5696f24385e81acc9c564500b5e5a0547db45a5335272e7d18400f1e68e8",
}
"""Rules section 0 table: file name -> sealed LF sha256."""
RULES_ADDENDA = {
    "las_p5r4_k1_rules_rev1.md":
        "f39846d6067a7bd409b4ac930d73ebde58a721728ec7d93703ff4627bf21e4b6",
    "las_p5r4_k1_rules_rev2.md":
        "e0a7d1e56b57df5336fc2fd40835624d93585fb224063f6c8068c2b1ba7b10fc",
}
"""Sealed addenda (rev1: sealed 2026-11-11 10:40:10 +09:00, before any result; record items
RV1-1 .. RV1-5, identity RV1-6)."""


def sealed_rules() -> dict[str, str]:
    """Every rules file a line records and S-1 checks: this rules, its addenda, the table."""
    return {RULES_NAME: RULES_SHA256, **RULES_ADDENDA, **INHERITED_RULES}


COPIED_FROM = {
    "04_scripts/04_hydraulic/coupled/las_rev_judge.py": {
        "git_blob": "63955a9ef7e03e667d005d557190d2601a3a0eb7",
        "lf_sha256": "ec1372d39dd41bec1e6aee284438133d04a87b59ac47b5b1249b119ebbd2ec54",
        "functions": ["need", "read_lines", "lf_sha256", "ready_time", "event_name_set",
                      "_item_violations", "items_only", "same_trajectory_drift",
                      "_verdict_violations", "_phase_violations", "_event_violations",
                      "pair_violations", "stroke_increase_m", "exception_record",
                      "ready_population (population part)"]},
    "04_scripts/04_hydraulic/coupled/k1_judge.py": {
        "git_blob": "d6875ec4ff5f6bb68e820e02b91d661ea16fb9bc",
        "lf_sha256": "625ba056e83843bcf9bcd67c5622f2b5f02d5ad778c74f58b9699a53c9e039d0",
        "functions": ["period_of", "key_list_sha256", "event_count", "_verdict_extra",
                      "c2_violations", "p3_comparison", "_decision_problems",
                      "evaluated_loc_periods", "k1_problems (K-8 harness)",
                      "k23_problems (K-8 harness, K1on only)", "identity_value_problems"]},
    "04_scripts/04_hydraulic/coupled/las_revA_judge.py": {
        "git_blob": "2563dc451317a3b57a98096814b65039cbb12b95",
        "lf_sha256": "5b43bfdb72509fc0792c8099c16407bdbb2a8b5bffc59c1a775e4b016bb6831c",
        "functions": ["grid_point_of", "part_of", "ramp_end_s", "lambda0_of",
                      "settings_problems", "_ka1", "_ka2", "_ka4", "_ramp_sequence_problems",
                      "_ka5_ka6", "grid_k_problems", "quarter_k_problems",
                      "exclusion_problems", "force_failures", "g2_prime_failures",
                      "range_cells", "trough_gap_s", "trough_kind"]},
}
"""Rules 11.1: copied functions and the sha of their source file at copy time (HEAD 91d574d)."""

# ------------------------------------------------------------------------------- bundles (4)
BUNDLES = ("Z-0", "Z-A", "Z-T", "Z-S", "Z-C", "Z-X")
ARM_REF, ARM_CAND = "ref", "cand"
BUNDLE_ARMS = {"Z-0": (ARM_REF,), "Z-A": (ARM_CAND,), "Z-T": (ARM_REF, ARM_CAND),
               "Z-S": (ARM_REF, ARM_CAND), "Z-C": (ARM_REF, ARM_CAND), "Z-X": (ARM_REF,)}
PAIR_BUNDLES = ("Z-T", "Z-S", "Z-C")
ARM_CANDIDATE = {ARM_REF: "P0", ARM_CAND: "P5r4"}
"""Rules 2: ref = P0+K1 (preset as it is), cand = P5r4+K1 (one ``replace``)."""
BUNDLE_COUNTS = {"Z-0": 6, "Z-A": 102, "Z-T": 384, "Z-S": 60, "Z-C": 912}
Z_X_MAX_LINES = 10
BUNDLE_FILE = {name: f"p5k_{name.replace('-', '')}.jsonl" for name in BUNDLES}
RESUME_SUFFIX = "_resume"

# Appendix A: stored base files (v5-relative) with raw sha256.
BASE_FILES = {
    "R0": (Path("las/revA2/revA_R0.jsonl"),
           "04cadd3cdd63372518ee8fcf3620bfef43695f08583a99b7458a0c53b7f777f3"),
    "R0A": (Path("las/revA2/revA_R0A.jsonl"),
            "28df99076cc309718e9dcfc270fed5d390a111f5ace8ce77ddbc3a3c8b0f14f8"),
    "RQ": (Path("las/revA2/revA_RQ.jsonl"),
           "93ced32cedb57888c37ea06dfbbe966c12c35d858f5b92a543e816f86cf953ca"),
    "RT": (Path("las/revA2/revA_RT.jsonl"),
           "c72f7e0882c50d86e565366866526ed55073d8bfef5c9f959b82c0e2885afd54"),
    "T1": (Path("las/las_T1.jsonl"),
           "3dee4f6b88e71654debd68b3ef5c5f1a9b01f1dba8fcd731d1355ec219d9a85b"),
    "T2": (Path("las/las_T2.jsonl"),
           "2fe6a54aafdc0c3ffbf1991907ee4e1af85761e1bef2e25bef07dd52ab199efb"),
    "RS": (Path("las/revA2/revA_RS.jsonl"),
           "7c407b6ee07b001f5504186fa013193ba6a2992516021f263b2bb537de43875d"),
    "YS": (Path("las/k1/k1_YS.jsonl"),
           "a31153a64ed9cbdf7410082e8dbda81b79e6d607c0a238d510ac34c0c9333ac6"),
    "SC": (Path("soil_defer/s2d_SC.jsonl"),
           "70e91ec1234d56a918af1b4fc053c3175f0f14ab41e2b5f334890f7dc6cb08aa"),
    "YP": (Path("las/k1/k1_YP.jsonl"),
           "0d985d5624f0fbb0219ca50d1c839b7db639011d6c2ab14fa9d84cfd197fc2c3"),
    "RX": (Path("las/revA2/revA_RX.jsonl"),
           "04f7a4dcf435b66934a811af6cee4cb5fa657f8e897f4a503321dd126f4b0d78"),
}
PAIR_REFERENCE_FILES = {
    "P5_RG": (Path("las/rev/rev_RG.jsonl"),
              "7e8c3b4173f1fc682e665ad173589dbbe335ba914a06d5ef2984c5807bb8cca6"),
    "P5_RH": (Path("las/revA/revA_RH.jsonl"),
              "f934cbd945353fe236e5313ed5b0b147c39a7e30f6b1b02cfc5557739422b0c9"),
}
"""Rules 6.1 G-4: the stored P5 pairs of K-A1 .. K-A4 (A-plan rev2 R2-5; raw sha256 = the
A-plan judge's ``REFERENCE_RG_SHA256`` / ``STORED_REVA_RH_SHA256``)."""
LIST_SHA256 = {
    "Z-0": "4d1591ba30b686bb6484072c1e63df51130791c2d0cee7106d9ae7d1bc4b6c9e",
    "Z-A": "14f89f1f9209114d7e5a2c84f5b45a7d6c650e44ac3de41dd4c93c8733451577",
    "Z-T": "4160bddfff318f8c13b36652c3203e89a02159b5fd5a624499aa6ef0940fe933",
    "Z-T-ref": "4160bddfff318f8c13b36652c3203e89a02159b5fd5a624499aa6ef0940fe933",
    "Z-S": "19c78b49197ac53da5ae50808555c5879aabc90765589ea220830d5588a23950",
    "Z-C": "fe6c9c46f2c799ee440d8a2a5d99d88099c51586297afd01d7201a52d26389d9",
    "Z-C-R4": "dc1e65d49bc0ea34fd04fdb7ba4eeceb7fc576ee15de9658dbe26927598b753b",
    "Z-C-out": "f20bb9e0b1b570660fd15c2a33a2abd66308efce10e1aeb3185cc178956edea7",
    "Z-X-old": "bdad17c7c77abae2eb47c8b366d09d1882fe934fecd112b759040b894f79adfd",
}
"""Appendix A list sha256 (sorted full keys, LF after each, UTF-8)."""
LIST_COUNTS = {"Z-0": 6, "Z-A": 2, "Z-T": 192, "Z-T-ref": 192, "Z-S": 30, "Z-C": 456,
               "Z-C-R4": 165, "Z-C-out": 437, "Z-X-old": 4}
R0A_LABELS, RQ_LABELS = 54, 48
Z_C_IN_SAMPLE = 19
REFERENCE_SOURCES = {"Z-0": ("revA_R0:",), "Z-A": ("revA_R0A/RQ",),
                     "Z-T": ("las_T1/T2", "revA_RT"), "Z-S": ("k1_YS",), "Z-C": ("k1_YP",),
                     "Z-X": ("Z-X:",)}
"""Prefix of a :class:`References` problem text -> the bundle whose bit reference it breaks."""
YP_SUB_BUNDLE = "Y-Pa"
YS_REF_SUB, YS_CAND_SUB = "Y-Sa", "Y-Sb"

# ------------------------------------------------------------------------------- tags (K-3)
TAG_BY_SETTING = {"VB": "final_C4G2_P3_LAS_K1", "V0": "final_C4G2_LAS_K1"}
COMBINATION_TAGS = ("final_C4G2_K1", "final_C4G2_P3_K1")
TOKEN_JOB_KEYS = ("k1", "k1_candidate", "k1_order_gate", "las_off")
"""rev2 RV2-14: ``job`` key names that are a K1 / LAS-off token trace (K-4 stop)."""
OLD_TAG_SUFFIX = "_LAS"
TOUCH_CREEP_SUFFIX = "_TCL"

# ------------------------------------------------------------------------------- LAS-b (K-5)
B0_SETTINGS = {"light_leg_fraction_of_F_min": 3.5, "min_active_periods": 0,
               "end_ramp_periods": 0}
P5R4_OVERRIDE = {"light_leg_fraction_of_F_min": 4.5, "end_ramp_periods": 4}
CANDIDATE_VALUES = {"P0": (3.5, 0, 0), "P5": (4.5, 0, 0), "P5r4": (4.5, 0, 4)}
"""(beta, n_min, N_r) of rules 2 / A-plan 1.2 (P5 only for the stored K-A pairs)."""

# ------------------------------------------------------------------------------- thresholds
F_MIN_N = 9414.589
C_FLOOR_N = F_MIN_N + 1000.0
GRID_FORCE_FLOOR_KN = 10.400
GRID_RANGE_LIMIT_KN = 0.500
G2P_FLOOR_KN = 11.414589
STROKE_LIMIT_M = 0.001
READY_MEDIAN_LIMIT_S = 1.0
READY_MAX_LIMIT_S = 5.0
EXCEPTION_DT_FLOOR_S = 1.0
EXCEPTION_SHARE = 0.8
EXCEPTION_COUNT_LIMIT = 5
EXCEPTION_DT_LIMIT_S = 15.0
C2_STOP_PAIRS = 5
THIN_MARGIN_PERIODS = 12
TOLERANCE = 1e-9
PERIOD_S = 0.1
OUTPUT_DELAY_S = 0.1
LAMBDA0_TOLERANCE = 1e-4
H_R_0_MARK = "|H-R-0|"
H_R_0_COUNT = 48
PASSING_VERDICTS = ("pass", "allowed_stop")
EVENT_PREFIXES = ("FAULT", "WARN")
P3_ITEM_PREFIXES = ("P3-1", "P3-5")
FLAT_SOIL_MARGIN_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN"
SKIP_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED"
GRID_SETTINGS = ("VB", "V0")
GRID_CENTRES = ("1", "0.94", "nom")
GRID_STEPS = (0, 1, 2, 3, 4)
RANGE_STEPS = (0, 1, 2, 3)
HALF_STEPS = (0.5, 1.5, 2.5, 3.5)
QUARTER_STEPS = (0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75)
PART_RG, PART_RH, PART_RQ = "R-G", "R-H", "R-Q"
PART_STEPS = {PART_RG: GRID_STEPS, PART_RH: HALF_STEPS, PART_RQ: QUARTER_STEPS}
RAMP_END_REASONS = ("done", "loc", "phase", "soil", "reapproach", "zone")
QUIET_ENDS = ("sum", "time")
KA1_FIELDS = ("start_t_s", "end_t_s", "end_reason", "active_periods", "scaled_periods",
              "start_leg")
KA_STOP_NAMES = ("K-A5", "K-A6", "K-A8")
CLUSTER_GAP_S = 0.05

# ------------------------------------------------------------------------------- identity
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
THREAD_VARIABLES = ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                    "NUMBA_NUM_THREADS")
THREAD_LAYER = "TBB"
ALLOWED_DIRTY = (
    "04_scripts/04_hydraulic/coupled/test_las_p5r4k1_targeted.py",
    "06_analysis/02_control/verif_matrix/scripts/test_las_p5r4k1_judge.py",
    "06_analysis/02_control/verif_matrix/scripts/test_las_p5r4k1_chrono_judge.py",
)
"""Rules 5.1 / K1 rev1 R1-4: this work's test files only (the code diff must still be empty)."""
BLOB_FILES = ("03_src/outrigger_sim/control/c2.py",
              "03_src/outrigger_sim/hydraulics/v5_options.py")
"""K-2: files whose HEAD blob sha256 every line records and the judge re-reads."""

# ------------------------------------------------------------------------------- statuses
STATUS_STOP, STATUS_UNDECIDABLE = "stop", "undecidable"
STATUS_FAIL, STATUS_PASS = "fail", "pass"
STATUS_INCOMPLETE, STATUS_NOT_RUN = "incomplete", "not_run"
STATUS_RANK = {STATUS_STOP: 0, STATUS_UNDECIDABLE: 1, STATUS_INCOMPLETE: 1, STATUS_FAIL: 2,
               STATUS_PASS: 3}
GRADES = {STATUS_STOP: "stop", STATUS_UNDECIDABLE: "판정 불가", STATUS_INCOMPLETE: "판정 불가",
          STATUS_FAIL: "미달", STATUS_PASS: "통과", STATUS_NOT_RUN: "not_run"}
EXIT_CODES = {STATUS_PASS: 0, STATUS_FAIL: 1, STATUS_UNDECIDABLE: 1, STATUS_INCOMPLETE: 1,
              STATUS_STOP: 2}

# ------------------------------------------------------------------------------- rev1 record
PATH_CORNER_BIAS, PATH_ANCHOR, PATH_BOTH, PATH_NONE = "1", "2", "1+2", "3"
"""rev1 RV1-1 correction paths by event name: (1) ``INFO_CLEARANCE_BIAS``, (2)
``INFO_LOC_CLEARANCE_ANCHOR``, both, neither (no LOC included)."""
ANCHOR_PATHS = (PATH_CORNER_BIAS, PATH_ANCHOR, PATH_BOTH)
BIAS_EVENT = "INFO_CLEARANCE_BIAS"
ANCHOR_EVENT = "INFO_LOC_CLEARANCE_ANCHOR"
LOC_EVENT = "crawler_liftoff_confirmed"
FLAG_ANCHOR_SAMPLE_SHIFT = "ANCHOR_SAMPLE_SHIFT"


class MissingField(KeyError):
    """A field a criterion needs is not in the line (undecidable)."""


class InputError(Exception):
    """Seals, stored files or key lists are not the sealed ones (exit 2, nothing judged)."""


# =============================================================================== small facts
def need(mapping: Any, *path: str) -> Any:
    """``mapping[path[0]][path[1]]...``; a missing key raises :class:`MissingField`.
    Copied from ``las_rev_judge.need``."""
    value = mapping
    for name in path:
        if not isinstance(value, dict) or name not in value:
            raise MissingField(".".join(path))
        value = value[name]
    return value


def read_lines(path: Path) -> list[dict]:
    """JSON lines of a file (blank lines skipped). Copied from ``las_rev_judge.read_lines``.

    Raises:
        ValueError: A line that is not JSON.
    """
    out = []
    for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not text.strip():
            continue
        try:
            out.append(json.loads(text))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number}: {exc}") from exc
    return out


def lf_sha256(path: Path) -> str:
    """sha256 with CRLF read as LF (the seal is an LF digest)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def period_of(t_s: float | None) -> int | None:
    """Rules 0: whole control periods ``round(t / 0.1)`` (Python built-in round)."""
    return None if t_s is None else round(float(t_s) / PERIOD_S)


def key_list_sha256(keys) -> str:
    """Appendix rule: sorted keys, LF after each, UTF-8."""
    return hashlib.sha256("".join(f"{key}\n" for key in sorted(keys)).encode("utf-8")).hexdigest()


def rev_of(line: dict) -> dict:
    return line.get("rev") or {}


def p5k_of(line: dict) -> dict:
    """The ``p5k`` block (error lines carry it too)."""
    return line.get("p5k") or rev_of(line).get("p5k") or {}


def is_error(line: dict) -> bool:
    return "error" in line


def is_verdict_case(line: dict) -> bool:
    return "case" in (line.get("job") or {})


def key_of(line: dict) -> str | None:
    return rev_of(line).get("key")


def grid_unit(line: dict) -> str | None:
    """``<full key>#<label>``: a grid label alone repeats for the VB and V0 keys."""
    key, label = key_of(line), rev_of(line).get("label")
    return None if key is None or label is None else f"{key}{GRID_UNIT_SEPARATOR}{label}"


def unit_of(line: dict) -> str | None:
    """The unit a line stands for: key and grid label in Z-A, the full key elsewhere."""
    if p5k_of(line).get("bundle") == "Z-A":
        return grid_unit(line)
    return key_of(line)


def event_count(line: dict, name: str) -> int:
    """Events whose base name (before ``:``) is exactly ``name`` (never a substring match:
    ``INFO_LOC_FLAT_SOIL_MARGIN`` does not count ``..._SKIPPED``). Copied from ``k1_judge``."""
    total = 0
    for event, count in (line.get("event_names") or {}).items():
        if str(event).split(":", 1)[0] == name:
            total += int(count or 0)
    return total


def stored_key_of(line: dict) -> str:
    """A stored line's full key: ``d1.key``, else ``rev.key`` (verdict cases)."""
    d1 = line.get("d1")
    return d1["key"] if d1 else rev_of(line)["key"]


def worst_status(statuses) -> str:
    """16.6: ``stop`` > ``undecidable`` (``incomplete`` included) > ``fail`` > ``pass``."""
    found = [status for status in statuses if status in STATUS_RANK]
    if not found:
        return STATUS_PASS
    worst = min(found, key=lambda status: STATUS_RANK[status])
    return STATUS_UNDECIDABLE if worst == STATUS_INCOMPLETE else worst


# =============================================================================== seals, bases
def seal_problems(rules_dir: Path = RULES_DIR) -> list[str]:
    """S-1: every rules file and its ``.sha256`` give the sealed LF digest."""
    problems = []
    for name, expected in sealed_rules().items():
        path = rules_dir / name
        sha_path = path.with_suffix(".sha256")
        if not path.is_file() or not sha_path.is_file():
            problems.append(f"missing {path.name} or its .sha256")
            continue
        tokens = sha_path.read_text(encoding="utf-8").split()
        if not tokens or tokens[0].lower() != expected:
            problems.append(f"{sha_path.name} does not hold {expected}")
        digest = lf_sha256(path)
        if digest != expected:
            problems.append(f"{path.name} LF sha256 {digest} != sealed {expected}")
    return problems


@dataclass
class Bases:
    """The stored lines (by name) and the lists recomputed from them (appendix A)."""

    lines: dict[str, list[dict]] = field(default_factory=dict)
    sha256: dict[str, str] = field(default_factory=dict)
    lists: dict[str, list[str]] = field(default_factory=dict)
    labels: dict[str, list[str]] = field(default_factory=dict)
    yp_error_lines: list[dict] = field(default_factory=list)


def _load_files(v5_dir: Path, files: dict, bases: Bases) -> list[str]:
    problems = []
    for name, (relative, expected) in files.items():
        path = v5_dir / relative
        if not path.is_file():
            problems.append(f"missing stored file {path}")
            continue
        bases.sha256[name] = raw_sha256(path)
        if bases.sha256[name] != expected:
            problems.append(f"{path.name} sha256 {bases.sha256[name]} != appendix {expected}")
        bases.lines[name] = read_lines(path)
    return problems


def is_b0_t_line(line: dict) -> bool:
    """A stored ``las_T1`` / ``las_T2`` L line (``las.candidate`` ``b0``)."""
    return (line.get("las") or {}).get("candidate") == "b0"


def recompute_lists(bases: Bases) -> None:
    """Appendix A lists from the stored files (recomputed, never typed in)."""
    lines = bases.lines
    bases.lists["Z-0"] = [key_of(line) for line in lines["R0"]]
    grid = lines["R0A"] + lines["RQ"]
    bases.lists["Z-A"] = sorted({key_of(line) for line in lines["R0A"]})
    bases.labels["R-0A"] = [grid_unit(line) for line in lines["R0A"]]
    bases.labels["R-Q"] = [grid_unit(line) for line in lines["RQ"]]
    bases.labels["Z-A"] = [grid_unit(line) for line in grid]
    bases.lists["Z-T"] = [key_of(line) for line in lines["RT"]]
    bases.lists["Z-T-ref"] = [line["las"]["key"] for line in lines["T1"] + lines["T2"]
                              if is_b0_t_line(line)]
    bases.lists["Z-S"] = [stored_key_of(line) for line in lines["RS"]]
    sc_keys = [stored_key_of(line) for line in lines["SC"]]
    bases.lists["Z-C"] = sc_keys
    bases.lists["Z-C-R4"] = [stored_key_of(line) for line in lines["SC"]
                             if event_count(line, FLAT_SOIL_MARGIN_EVENT) > 0]
    rs = set(bases.lists["Z-S"])
    bases.lists["Z-C-out"] = [key for key in sc_keys if key not in rs]
    bases.lists["Z-X-old"] = [key_of(line) for line in lines["RX"]]


def list_problems(bases: Bases) -> list[str]:
    """Rules 4.1 / K-9: each recomputed list is its appendix list (count, unique, sha256)."""
    problems = []
    for name, expected in LIST_SHA256.items():
        keys = bases.lists.get(name, [])
        digest = key_list_sha256(keys)
        if len(keys) != LIST_COUNTS[name] or len(set(keys)) != len(keys) or digest != expected:
            problems.append(f"list {name}: {len(keys)} keys, sha256 {digest} != {expected}")
    in_sample = set(bases.lists.get("Z-C", [])) & set(bases.lists.get("Z-S", []))
    if len(in_sample) != Z_C_IN_SAMPLE:
        problems.append(f"Z-C in-sample keys {len(in_sample)} != {Z_C_IN_SAMPLE}")
    for name, count in (("R-0A", R0A_LABELS), ("R-Q", RQ_LABELS)):
        labels = bases.labels.get(name, [])
        if len(labels) != count or len(set(labels)) != count:
            problems.append(f"labels {name}: {len(labels)} ({len(set(labels))} unique) != {count}")
    return problems


def load_bases(v5_dir: Path = V5_DIR) -> Bases:
    """The stored files (raw sha256 checked) and the recomputed lists.

    Raises:
        InputError: A file is missing or not the appendix one, or a list differs.
    """
    bases = Bases()
    problems = _load_files(v5_dir, {**BASE_FILES, **PAIR_REFERENCE_FILES}, bases)
    if problems:
        raise InputError(problems)
    recompute_lists(bases)
    problems = list_problems(bases)
    if problems:
        raise InputError(problems)
    return bases


def label_list_sha256(bases: Bases) -> dict[str, str]:
    """Appendix A: the tool records the grid label list sha256 (R-0A, R-Q)."""
    return {name: key_list_sha256(bases.labels.get(name, [])) for name in ("R-0A", "R-Q")}


# =============================================================================== references
@dataclass
class References:
    """Expected hashes of the bit predictions (4.4) and the stored K-A pairs."""

    hashes: dict[tuple[str, str], dict[str, str]] = field(default_factory=dict)
    """(bundle, arm) -> unit -> expected ``commands_sha256``."""
    problems: list[str] = field(default_factory=list)
    """Reference problems (a duplicate or missing stored line): S-3 ``stop``."""
    p5_pairs: dict[str, dict[tuple, dict]] = field(default_factory=dict)
    """``R-G`` / ``R-H`` -> grid point -> stored P5 line (K-A1 .. K-A4)."""
    yp_error_keys: list[str] = field(default_factory=list)


def _unique(name: str, pairs: list[tuple[str, str]], problems: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for unit, sha in pairs:
        if unit in out:
            problems.append(f"{name}: {unit} twice in the stored file")
        out[unit] = sha
    return out


def _p5_points(lines: list[dict]) -> dict[tuple, dict]:
    out = {}
    for line in lines:
        if rev_of(line).get("candidate") == "P5" and not is_error(line):
            out[grid_point_of(line)] = line
    return out


def build_references(bases: Bases) -> References:
    """4.4 expected hashes per (bundle, arm, unit) from the stored files."""
    refs = References()
    lines = bases.lines
    problems = refs.problems
    refs.hashes[("Z-0", ARM_REF)] = _unique(
        "revA_R0", [(key_of(line), line["commands_sha256"]) for line in lines["R0"]], problems)
    refs.hashes[("Z-A", ARM_CAND)] = _unique(
        "revA_R0A/RQ", [(grid_unit(line), line["commands_sha256"])
                        for line in lines["R0A"] + lines["RQ"]], problems)
    refs.hashes[("Z-T", ARM_REF)] = _unique(
        "las_T1/T2", [(line["las"]["key"], line["commands_sha256"])
                      for line in lines["T1"] + lines["T2"] if is_b0_t_line(line)], problems)
    refs.hashes[("Z-T", ARM_CAND)] = _unique(
        "revA_RT", [(key_of(line), line["commands_sha256"]) for line in lines["RT"]], problems)
    for arm, sub in ((ARM_REF, YS_REF_SUB), (ARM_CAND, YS_CAND_SUB)):
        selected = [line for line in lines["YS"] if not is_error(line)
                    and (line.get("k1") or {}).get("sub_bundle") == sub]
        refs.hashes[("Z-S", arm)] = _unique(f"k1_YS {sub}", [
            (key_of(line), line["commands_sha256"]) for line in selected], problems)
    refs.hashes[("Z-C", ARM_REF)] = _zc_reference(bases, refs)
    refs.p5_pairs = {PART_RG: _p5_points(lines["P5_RG"]), PART_RH: _p5_points(lines["P5_RH"])}
    return refs


def _zc_reference(bases: Bases, refs: References) -> dict[str, str]:
    """BT-CR: R4-evaluated 165 keys from ``k1_YP`` (Y-Pa, K1on, P0, no ``error``; exactly one
    such line per key), the other 291 from ``s2d_SC``."""
    r4 = set(bases.lists["Z-C-R4"])
    yp: dict[str, list[str]] = {}
    for line in bases.lines["YP"]:
        if is_error(line):
            refs.yp_error_keys.append(str(key_of(line)))
            continue
        block = line.get("k1") or {}
        if (block.get("sub_bundle") == YP_SUB_BUNDLE and block.get("k1_candidate") == "K1on"
                and block.get("las_candidate") == "P0"):
            yp.setdefault(key_of(line), []).append(line["commands_sha256"])
    out = {}
    for line in bases.lines["SC"]:
        key = stored_key_of(line)
        if key in r4:
            found = yp.get(key, [])
            if len(found) != 1:
                refs.problems.append(f"k1_YP: {len(found)} usable Y-Pa lines for {key}")
                continue
            out[key] = found[0]
        else:
            out[key] = line["commands_sha256"]
    return out


# =============================================================================== run lines
@dataclass
class ArmLines:
    """Lines of one bundle arm keyed by their unit (full key; Z-A grid label)."""

    finished: dict[str, dict] = field(default_factory=dict)
    error_units: dict[str, int] = field(default_factory=dict)
    duplicates: list[str] = field(default_factory=list)
    reruns: list[str] = field(default_factory=list)
    error_lines: int = 0


def read_run_lines(run_dir: Path) -> list[dict]:
    """Every ``p5k_Z*.jsonl`` line of the run folder (resume files included, G-S not)."""
    lines = []
    for path in sorted(run_dir.glob(LINE_FILE_PATTERN)):
        lines += read_lines(path)
    return lines


def split_lines(lines: list[dict]) -> tuple[dict[tuple[str, str], ArmLines], list[str]]:
    """(bundle, arm) -> lines, and the lines that belong to no bundle arm (K-9)."""
    parts = {(bundle, arm): ArmLines() for bundle in BUNDLES for arm in BUNDLE_ARMS[bundle]}
    foreign = []
    for line in lines:
        block = p5k_of(line)
        part = parts.get((block.get("bundle"), block.get("arm")))
        unit = unit_of(line)
        if part is None or unit is None:
            foreign.append(f"{block.get('bundle')} {block.get('arm')} {unit}")
            continue
        attempt = block.get("attempt") or rev_of(line).get("attempt") or 1
        if attempt >= 2 or block.get("resumed"):
            part.reruns.append(unit)
        if is_error(line):
            part.error_lines += 1
            part.error_units[unit] = part.error_units.get(unit, 0) + 1
            continue
        if unit in part.finished:
            part.duplicates.append(unit)
        part.finished[unit] = line
    return parts, foreign


def expected_units(bundle: str, arm: str, bases: Bases, claim_keys: list[str]) -> list[str]:
    if bundle == "Z-A":
        return list(bases.labels["Z-A"])
    if bundle == "Z-X":
        return list(claim_keys)
    return list(bases.lists[bundle])


# =============================================================================== C-2 type (6.2)
def ready_time(line: dict) -> float | None:
    """READY time: ``d1.t_ready_s`` (D-1), ``values.times.t_first_ready_s`` (verdict cases).
    Copied from ``las_rev_judge.ready_time``."""
    if is_verdict_case(line):
        return need(line, "values", "times", "t_first_ready_s")
    return need(line, "d1", "t_ready_s")


def event_name_set(line: dict) -> set[str]:
    """``FAULT*`` / ``WARN*`` base names of ``event_names``. Copied from ``las_rev_judge``."""
    names = need(line, "event_names")
    out = set()
    for name in names:
        base = str(name).split(":", 1)[0]
        if base.startswith(EVENT_PREFIXES):
            out.add(base)
    return out


def _item_violations(cand_items: dict, ref_items: dict) -> list[str]:
    """Key union: ref true and cand not true; ref None and cand false. Copied."""
    out = []
    for name in sorted(set(cand_items) | set(ref_items)):
        ref_value, value = ref_items.get(name), cand_items.get(name)
        if (ref_value is True and value is not True) or (ref_value is None and value is False):
            out.append(f"item {name} {ref_value} -> {value}")
    return out


def items_only(cand: dict, ref: dict) -> dict[str, list[str]]:
    cand_keys = set(need(cand, "d1", "items"))
    ref_keys = set(need(ref, "d1", "items"))
    return {"items_only_ref": sorted(ref_keys - cand_keys),
            "items_only_cand": sorted(cand_keys - ref_keys)}


def same_trajectory_drift(cand: dict, ref: dict) -> None:
    """Equal commands hash but other ``d1.items`` is judge drift (copied, rev1 R1-3).

    Raises:
        MissingField: Same hash, different items (undecidable).
    """
    cand_items, ref_items = need(cand, "d1", "items"), need(ref, "d1", "items")
    if cand["commands_sha256"] == ref["commands_sha256"] and cand_items != ref_items:
        raise MissingField("d1.items differ with an equal commands hash (rev1 R1-3)")


def _verdict_violations(cand: dict, ref: dict) -> list[str]:
    cand_d1, ref_d1 = need(cand, "d1"), need(ref, "d1")
    verdict, ref_verdict = need(cand_d1, "verdict"), need(ref_d1, "verdict")
    out = []
    if verdict is None:
        out.append("verdict None")
    elif ref_verdict in PASSING_VERDICTS and verdict == "fail":
        out.append(f"verdict {ref_verdict} -> fail")
    extra = set(need(cand_d1, "fail_items") or ()) - set(need(ref_d1, "fail_items") or ())
    if extra:
        out.append(f"new fail items {sorted(extra)}")
    same_trajectory_drift(cand, ref)
    return out + _item_violations(need(cand_d1, "items"), need(ref_d1, "items"))


def _phase_violations(cand: dict, ref: dict) -> list[str]:
    out = []
    if need(ref, "final_phase") == "ready" and need(cand, "final_phase") != "ready":
        out.append(f"final_phase ready -> {cand['final_phase']}")
    if ready_time(ref) is not None and ready_time(cand) is None:
        out.append("READY time -> None")
    return out


def _event_violations(cand: dict, ref: dict) -> list[str]:
    extra = event_name_set(cand) - event_name_set(ref)
    return [f"new events {sorted(extra)}"] if extra else []


def pair_violations(cand: dict, ref: dict) -> list[str]:
    """C-2 type (a) .. (c); verdict cases only (b) and (c). Copied from ``las_rev_judge``.

    Raises:
        MissingField: A criteria field missing in either line (undecidable).
    """
    out = [] if is_verdict_case(ref) else _verdict_violations(cand, ref)
    return out + _phase_violations(cand, ref) + _event_violations(cand, ref)


def _verdict_extra(cand: dict, ref: dict) -> list[str]:
    """K1 wording of (a): a verdict leaving ``pass`` / ``allowed_stop`` (copied, k1_judge)."""
    if is_verdict_case(ref):
        return []
    ref_verdict = need(ref, "d1", "verdict")
    verdict = need(cand, "d1", "verdict")
    if ref_verdict in PASSING_VERDICTS and verdict not in PASSING_VERDICTS:
        return [f"verdict {ref_verdict} -> {verdict}"]
    return []


def c2_violations(cand: dict, ref: dict) -> list[str]:
    """C-2 type of K1 rev1 R1-2 (``pair_violations`` + the K1 (a) verdict wording; copied)."""
    found = pair_violations(cand, ref)
    for text in _verdict_extra(cand, ref):
        if text not in found:
            found.append(text)
    return found


def p3_comparison(cand: dict, ref: dict) -> dict:
    """K1 rev1 R1-1 P3 of one pair over the ``P3-1*`` / ``P3-5*`` item union (copied).

    Raises:
        MissingField: ``d1.items`` missing on a D-1 line.
    """
    if is_verdict_case(cand) or is_verdict_case(ref):
        return {"violations": [], "baseline_false": [], "not_applicable": True}
    cand_items = need(cand, "d1", "items")
    ref_items = need(ref, "d1", "items")
    names = sorted(name for name in set(cand_items) | set(ref_items)
                   if name.startswith(P3_ITEM_PREFIXES))
    violations, baseline_false = [], []
    for name in names:
        ref_value, value = ref_items.get(name), cand_items.get(name)
        if ref_value is False:
            baseline_false.append(name)
        elif (ref_value is True and value is not True) or (ref_value is None and value is False):
            violations.append(f"{name} {ref_value} -> {value}")
    return {"violations": violations, "baseline_false": baseline_false,
            "not_applicable": not names}


def stroke_increase_m(cand: dict, ref: dict) -> float | None:
    """C-S: ``d1.stroke_max_m`` increase (None when either value is None). Copied."""
    value, ref_value = need(cand, "d1", "stroke_max_m"), need(ref, "d1", "stroke_max_m")
    if value is None or ref_value is None:
        return None
    return float(value) - float(ref_value)


# =============================================================================== K1 decisions
def k1_block(line: dict) -> dict:
    return line.get("k1") or {}


def decisions_of(line: dict) -> list[dict]:
    """``k1.decisions`` (the run controller's ``order_gate.decisions``).

    Raises:
        MissingField: No decisions recorded.
    """
    decisions = need(line, "k1", "decisions")
    if not isinstance(decisions, list):
        raise MissingField("k1.decisions is not a list")
    return decisions


def l1_of(decisions: list[dict]) -> dict | None:
    """adopt2 $L_1$: the first R4-evaluated decision (``r4_due_without_gate`` true)."""
    return next((d for d in decisions if d.get("r4_due_without_gate") is True), None)


def has_applied_r4(decisions: list[dict]) -> bool:
    return any(d.get("r4_due_without_gate") is True and d.get("applied") is True
               for d in decisions)


def ck1_record(cand: dict, ref: dict) -> dict:
    """CK-1: ref $L_1$ applied -> cand has an applied R4 decision (else ``R4_LOST``);
    ``R4_GAINED`` (FLAG) when only cand applies R4.

    Raises:
        MissingField: ``k1.decisions`` missing on either line.
    """
    ref_decisions, cand_decisions = decisions_of(ref), decisions_of(cand)
    ref_l1, cand_l1 = l1_of(ref_decisions), l1_of(cand_decisions)
    is_ref_applied = ref_l1 is not None and ref_l1.get("applied") is True
    is_lost = is_ref_applied and not has_applied_r4(cand_decisions)
    is_gained = not has_applied_r4(ref_decisions) and has_applied_r4(cand_decisions)
    return {"R4_LOST": is_lost, "R4_GAINED": is_gained,
            "ref_L1": l1_tuple(ref_l1), "cand_L1": l1_tuple(cand_l1),
            "thin_margin": cand_l1 is not None and cand_l1.get("dP") is not None
            and cand_l1["dP"] <= THIN_MARGIN_PERIODS}


def l1_tuple(decision: dict | None) -> dict | None:
    if decision is None:
        return None
    return {name: decision.get(name) for name in
            ("t_loc_s", "t_P_s", "t_S_s", "n_P", "n_S", "dP", "would_block", "applied")}


def _decision_problems(key: str, decision: dict) -> list[str]:
    """A decision holds t_P and t_S and its period numbers agree (copied, k1_judge)."""
    t_P_s, t_S_s = decision.get("t_P_s"), decision.get("t_S_s")
    if t_P_s is None or t_S_s is None:
        return [f"K-8 {key}: decision at {decision.get('t_loc_s')} without t_P / t_S"]
    n_P, n_S = period_of(t_P_s), period_of(t_S_s)
    if (decision.get("n_P"), decision.get("n_S"), decision.get("dP")) != (n_P, n_S, n_P - n_S):
        return [f"K-8 {key}: n_P / n_S / dP {decision.get('n_P')} / {decision.get('n_S')} / "
                f"{decision.get('dP')} != {n_P} / {n_S} / {n_P - n_S}"]
    expected_block = bool(decision.get("r4_due_without_gate")) and n_P <= n_S
    if bool(decision.get("would_block")) != expected_block:
        return [f"K-8 {key}: would_block {decision.get('would_block')} != {expected_block}"]
    return []


def evaluated_loc_periods(block: dict) -> list[int]:
    """LOCs at which R4 was evaluated (harness witness of ``_apply_slope_clearance_margin``:
    not the slope margin, R4 on, a soil mode). Copied from ``k1_judge``."""
    return [period_of(call["t_s"]) for call in block.get("loc_calls") or ()
            if not call["slope_margin_fired"] and call["r4_on"] and call["t_S_s"] is not None]


def k8_problems(line: dict) -> list[str]:
    """K-8 on a harness line (adopt2 K-8 (a) .. (e) as ``k1_judge`` K-1 / K-3 check them on the
    harness: decision periods = witness periods, decisions complete, applied = due and not
    blocked, one margin event per applied decision, one skip event per blocked one)."""
    block, key = k1_block(line), key_of(line)
    for name in ("enabled", "decisions", "r4_applied", "would_block_any", "loc_calls"):
        if name not in block:
            return [f"K-8 {key}: k1.{name} missing"]
    decisions = block["decisions"]
    problems = []
    witness = evaluated_loc_periods(block)
    if [period_of(d.get("t_loc_s")) for d in decisions] != witness:
        problems.append(f"K-8 {key}: decisions at {[d.get('t_loc_s') for d in decisions]}, "
                        f"evaluated LOC periods {witness}")
    for decision in decisions:
        problems += _decision_problems(key, decision)
        expected = bool(decision.get("r4_due_without_gate")) and not bool(
            decision.get("would_block"))
        if bool(decision.get("applied")) != expected:
            problems.append(f"K-8 {key}: applied {decision.get('applied')} at "
                            f"{decision.get('t_loc_s')}, expected {expected}")
    applied = sum(1 for d in decisions if d.get("applied"))
    if applied != event_count(line, FLAT_SOIL_MARGIN_EVENT):
        problems.append(f"K-8 {key}: {applied} applied decisions, "
                        f"{event_count(line, FLAT_SOIL_MARGIN_EVENT)} margin events")
    blocked = sum(1 for d in decisions if d.get("r4_due_without_gate") and d.get("would_block"))
    if event_count(line, SKIP_EVENT) != blocked:
        problems.append(f"K-8 {key}: {event_count(line, SKIP_EVENT)} skip events, "
                        f"{blocked} blocked decisions")
    if block["r4_applied"] is not (applied > 0):
        problems.append(f"K-8 {key}: r4_applied {block['r4_applied']}, {applied} applied")
    if block["would_block_any"] is not any(d.get("would_block") for d in decisions):
        problems.append(f"K-8 {key}: would_block_any {block['would_block_any']}")
    return problems


# =============================================================================== K-A (Z-A, 6.1)
def grid_point_of(line: dict) -> tuple | None:
    """(setting, centre, j) of a grid line, ``j`` keeps its type. Copied."""
    point = rev_of(line).get("grid_point")
    if point is None:
        return None
    return need(line, "job", "setting"), str(point[0]), point[1]


def part_of(line: dict) -> str | None:
    """Z-A part from the label kind (``LT`` R-G, ``LH`` R-H, ``LQ`` R-Q)."""
    label = str(rev_of(line).get("label") or "")
    for kind, part in (("-LT-", PART_RG), ("-LH-", PART_RH), ("-LQ-", PART_RQ)):
        if kind in label:
            return part
    return None


def settings_problems(line: dict) -> list[str]:
    """K-A8 / K-5: the controller's own settings are the arm candidate's (copied, revA)."""
    rev = rev_of(line)
    candidate = need(rev, "candidate")
    if candidate not in CANDIDATE_VALUES:
        return [f"K-A8 candidate {candidate!r} unknown"]
    beta, n_min, n_r = CANDIDATE_VALUES[candidate]
    problems = []
    if need(rev, "settings_match") is not True:
        problems.append("K-A8 controller settings differ from the candidate's (other fields)")
    settings = need(rev, "settings")
    actual = (settings.get("light_leg_fraction_of_F_min"), settings.get("min_active_periods"),
              settings.get("end_ramp_periods"))
    if actual != (beta, n_min, n_r):
        problems.append(f"K-A8 settings beta/n_min/N_r {actual} != {(beta, n_min, n_r)}")
    params = need(line, "las", "params")
    from_params = (params.get("beta"), params.get("n_min"), params.get("n_r"))
    if from_params != (beta, n_min, n_r):
        problems.append(f"K-A8 las.params beta/n_min/n_r {from_params}")
    return problems


def ramp_end_s(line: dict) -> float | None:
    """rev2 RV2-11: the end the restarts must follow is ``las.ramp.end_t_s``, else (None or
    absent) ``las.end_t_s``."""
    las = line.get("las") or {}
    ramp = las.get("ramp") or {}
    if ramp.get("end_t_s") is not None:
        return ramp["end_t_s"]
    return las.get("end_t_s")


def _acted_periods(line: dict) -> list[dict]:
    out = []
    for period in need(line, "diag", "periods"):
        las = period.get("las")
        if las and las.get("active_after"):
            out.append(las)
    return out


def lambda0_of(line: dict) -> tuple[bool, float | None]:
    """(lambda_0 < 1, mean(out) / mean(in)) of the last acted period. Copied.

    Raises:
        MissingField: No acted period is recorded.
    """
    acted = _acted_periods(line)
    if not acted:
        raise MissingField("diag.periods[].las of the last acted period")
    last = acted[-1]
    if not last.get("is_scaled"):
        return False, 1.0
    inputs, outputs = last["input_mm_s"], last["output_mm_s"]
    return True, (sum(outputs) / len(outputs)) / (sum(inputs) / len(inputs))


def _ka1(cand: dict, pair: dict) -> list[str]:
    las, pair_las = need(cand, "las"), need(pair, "las")
    return [f"K-A1 las.{name} {las.get(name)!r} != P5 {pair_las.get(name)!r}"
            for name in KA1_FIELDS if las.get(name) != pair_las.get(name)]


def _commands_before(line: dict, t_end_s: float) -> list[tuple]:
    return [(period["t_s"], period["cmd_mm_s"]) for period in need(line, "diag", "periods")
            if period["t_s"] < t_end_s - TOLERANCE]


def _ka2(cand: dict, pair: dict, t_end_s: float) -> list[str]:
    if _commands_before(cand, t_end_s) != _commands_before(pair, t_end_s):
        return [f"K-A2 period commands before t_e {t_end_s} differ from P5"]
    return []


def _ka4(cand: dict, pair: dict, t_end_s: float) -> list[str]:
    rows = need(cand, "diag", "force_window", "rows")
    pair_rows = need(pair, "diag", "force_window", "rows")
    if not rows or not pair_rows:
        return []
    t_from = max(rows[0][0], pair_rows[0][0])
    t_to = min(rows[-1][0], pair_rows[-1][0], t_end_s + OUTPUT_DELAY_S - TOLERANCE)

    def inside(table):
        return [row for row in table if t_from - TOLERANCE <= row[0] < t_to]

    if inside(rows) != inside(pair_rows):
        return [f"K-A4 force_window rows in [{t_from}, {t_to}) differ from P5"]
    return []


def _ramp_sequence_problems(line: dict, ramp: dict, applied: int) -> list[str]:
    ramp_periods = [period["las"] for period in need(line, "diag", "periods")
                    if (period.get("las") or {}).get("ramp_m") is not None]
    steps = [las["ramp_m"] for las in ramp_periods]
    problems = []
    if steps != list(range(1, applied + 1)):
        problems.append(f"K-A5 ramp steps {steps} != 1..{applied}")
    scaled = sum(1 for las in ramp_periods if las.get("ramp_scaled"))
    if scaled != ramp.get("scaled_periods"):
        problems.append(f"K-A5 {scaled} ramp_scaled periods != las.ramp.scaled_periods "
                        f"{ramp.get('scaled_periods')}")
    return problems


def _ka5_ka6(cand: dict, pair: dict | None, n_r: int) -> list[str]:
    """K-A5 / K-A6 (and the K-A8 ``ramp.n_r``). Copied from ``las_revA_judge``."""
    las = need(cand, "las")
    ramp = need(cand, "las", "ramp")
    problems = []
    if ramp.get("n_r") != n_r:
        problems.append(f"K-A8 las.ramp.n_r {ramp.get('n_r')} != {n_r}")
    applied = need(ramp, "periods_applied")
    if las.get("end_reason") not in QUIET_ENDS:
        if applied != 0:
            problems.append(f"K-A6 end {las.get('end_reason')} with {applied} ramp periods")
        return problems
    is_scaled, lambda0 = lambda0_of(cand if pair is None else pair)
    if not is_scaled:
        if applied != 0:
            problems.append(f"K-A6 lambda_0 = 1 with {applied} ramp periods")
        return problems
    if pair is None:
        if not need(ramp, "scaled_periods"):
            problems.append("K-A5 the ramp never scaled a command (no P5 pair to compare)")
    elif cand["commands_sha256"] == pair["commands_sha256"]:
        problems.append("K-A5 commands hash equals P5 although the ramp acts")
    start = need(ramp, "start_factor")
    if start is None or abs(start - lambda0) > LAMBDA0_TOLERANCE:
        problems.append(f"K-A5 start_factor {start!r} != lambda_0 {lambda0!r}")
    if need(ramp, "end_reason") not in RAMP_END_REASONS:
        problems.append(f"K-A5 ramp end_reason {ramp.get('end_reason')!r}")
    limit_ok = applied == n_r if ramp.get("end_reason") == "done" else applied <= n_r
    if not limit_ok:
        problems.append(f"K-A5 {applied} ramp periods with end {ramp.get('end_reason')}")
    return problems + _ramp_sequence_problems(cand, ramp, applied)


def _n_r_of(line: dict) -> int:
    return CANDIDATE_VALUES.get(need(line, "rev", "candidate"), (None, None, -1))[2]


def grid_k_problems(cand: dict, pair: dict, part: str) -> list[str]:
    """K-A1 .. K-A8 of one R-0A-part line against its stored P5 pair (copied).

    Raises:
        MissingField: A field the checks read is missing.
    """
    problems = settings_problems(cand)
    las = need(cand, "las")
    if las.get("start_t_s") is None:
        if cand["commands_sha256"] != pair["commands_sha256"]:
            problems.append("K-A7 not started but the commands hash differs from P5")
        return problems
    problems += _ka1(cand, pair)
    t_end_s = las.get("end_t_s")
    if t_end_s is not None:
        problems += _ka2(cand, pair, t_end_s) + _ka4(cand, pair, t_end_s)
    lift = need(cand, "diag", "summary", "t_lift_s")
    pair_lift = need(pair, "diag", "summary", "t_lift_s")
    if part == PART_RG and lift != pair_lift:
        problems.append(f"K-A3 t_lift_s {lift} != P5 {pair_lift}")
    return problems + _ka5_ka6(cand, pair, _n_r_of(cand))


def quarter_k_problems(line: dict) -> list[str]:
    """K-A5, K-A6, K-A8 of one R-Q-part line (no P5 pair). Copied.

    Raises:
        MissingField: A field the checks read is missing.
    """
    problems = settings_problems(line)
    if need(line, "las").get("start_t_s") is None:
        applied = need(line, "las", "ramp", "periods_applied")
        if applied != 0:
            problems.append(f"K-A6 not started with {applied} ramp periods")
        return problems
    return problems + _ka5_ka6(line, None, _n_r_of(line))


def is_ka_stop(problem: str) -> bool:
    return any(name in problem for name in KA_STOP_NAMES)


def expected_points(steps) -> set[tuple]:
    return {(s, c, j) for s in GRID_SETTINGS for c in GRID_CENTRES for j in steps}


def exclusion_problems(part: str, lines: dict[tuple, dict], errors: int) -> list[str]:
    """G-3: every point there, no error, level budget 0, gates consistent (copied)."""
    expected = expected_points(PART_STEPS[part])
    problems = []
    if errors or set(lines) != expected:
        problems.append(f"{part}: lines {len(lines)}/{len(expected)}, errors {errors}, missing "
                        f"{sorted(expected - set(lines), key=str)}, extra "
                        f"{sorted(set(lines) - expected, key=str)}")
    for point, line in lines.items():
        try:
            budget = need(line, "diag", "touch_budget", "level_budget_periods")
            consistent = need(line, "diag", "summary", "gate_consistent")
        except MissingField as exc:
            problems.append(f"{part} {point}: missing {exc}")
            continue
        if budget != 0 or consistent is not True:
            problems.append(f"{part} {point}: level_budget_periods {budget}, "
                            f"gate_consistent {consistent}")
    return problems


def _forces(line: dict) -> tuple:
    summary = (line.get("diag") or {}).get("summary") or {}
    return summary.get("F_RL_kN"), summary.get("F_judged_min_kN")


def force_failures(part: str, lines: dict[tuple, dict], floor_kN: float
                   ) -> tuple[list[dict], list[str]]:
    """(lines below ``floor_kN``, values between 10.400 and 10.4146 kN). Copied."""
    failures, between = [], []
    for point in sorted(lines, key=str):
        f_rl, f_judged = _forces(lines[point])
        if f_rl is None or f_judged is None or min(f_rl, f_judged) < floor_kN:
            failures.append({"part": part, "point": list(point), "F_RL_kN": f_rl,
                             "F_judged_min_kN": f_judged})
        for value in (f_rl, f_judged):
            if value is not None and GRID_FORCE_FLOOR_KN <= value < C_FLOOR_N / 1e3:
                between.append(f"{part} {point}: {value!r} kN")
    return failures, between


def range_cells(by_point: dict[tuple, dict], steps) -> list[dict]:
    """Record: R_c = max - min of F_RL over ``steps`` per (setting, centre) (copied)."""
    cells = []
    for setting in GRID_SETTINGS:
        for centre in GRID_CENTRES:
            values = [_forces(by_point[(setting, centre, j)])[0]
                      if (setting, centre, j) in by_point else None for j in steps]
            if any(value is None for value in values):
                cells.append({"setting": setting, "centre": centre, "R_c": None})
                continue
            cells.append({"setting": setting, "centre": centre,
                          "R_c": max(values) - min(values),
                          "ok_original_0p5": max(values) - min(values)
                          <= GRID_RANGE_LIMIT_KN + TOLERANCE})
    return cells


def trough_kind(line: dict) -> str | None:
    """A-plan rev2 B.1: gap <= 0.05 s = lift-off first trough, else after re-acceleration."""
    t_min = ((line.get("diag") or {}).get("summary") or {}).get("t_RL_min_s")
    t_end = (line.get("las") or {}).get("end_t_s")
    if t_min is None or t_end is None:
        return None
    gap = t_min - (t_end + OUTPUT_DELAY_S)
    return "liftoff_first" if gap <= CLUSTER_GAP_S else "after_reacceleration"


# =============================================================================== identity (9)
def tag_problems(line: dict) -> list[str]:
    """K-3: the setting's new tag exactly; no old ``_LAS``, combination or ``_TCL`` tag."""
    setting = (line.get("job") or {}).get("setting")
    tag = line.get("controller_tag")
    expected = TAG_BY_SETTING.get(setting)
    problems = []
    if tag != expected:
        problems.append(f"K-3 controller_tag {tag!r} != {expected!r} ({setting})")
    if isinstance(tag, str) and (tag.endswith(OLD_TAG_SUFFIX) or tag in COMBINATION_TAGS
                                 or tag.endswith(TOUCH_CREEP_SUFFIX)):
        problems.append(f"K-3 tag {tag!r} is old / combination / _TCL")
    if p5k_of(line).get("is_liftoff_slow_tag") is not True:
        problems.append("K-3 v5_options.is_liftoff_slow_tag not true")
    return problems


def gate_problems(line: dict) -> list[str]:
    """K-4: the run controller has the gate on (setting and meta), decisions recorded, no K1
    token, touch creep latch off."""
    block, p5k = k1_block(line), p5k_of(line)
    problems = []
    if block.get("setting") is not True or block.get("enabled") is not True:
        problems.append(f"K-4 gate setting {block.get('setting')!r} enabled "
                        f"{block.get('enabled')!r}")
    if "decisions" not in block:
        problems.append("K-4 k1.decisions missing")
    if p5k.get("k1_token") is not None or "K1on" in str(rev_of(line).get("label")):
        problems.append("K-4 a K1 token is on the line")
    if p5k.get("touch_creep_latch_enabled") is not False:
        problems.append(f"K-4 touch_creep_latch enable {p5k.get('touch_creep_latch_enabled')!r}")
    effective = line.get("effective") or {}
    if (effective.get("flat_soil_margin_order_gate") is not True
            or effective.get("touch_creep_latch_enable") is not False):
        problems.append(f"K-4 effective gate / touch creep {effective!r}")
    job_keys = sorted(key for key in line.get("job") or {} if key in TOKEN_JOB_KEYS)
    if job_keys:
        problems.append(f"K-4 job keys {job_keys} (rev2 RV2-14 token trace)")
    return problems


def las_problems(line: dict) -> list[str]:
    """K-5 / K-A8: the arm's settings (ref b0, cand P5r4) and the ``las_candidate`` field."""
    p5k = p5k_of(line)
    arm = p5k.get("arm")
    want = ARM_CANDIDATE.get(arm)
    problems = []
    names = {"p5k.las_candidate": p5k.get("las_candidate"), "las_candidate":
             line.get("las_candidate"), "rev.candidate": rev_of(line).get("candidate")}
    if "candidate" in (line.get("las") or {}):
        names["las.candidate"] = line["las"]["candidate"]
    wrong = {name: value for name, value in names.items() if value != want}
    if wrong:
        problems.append(f"K-5 {wrong} != {want!r} ({arm})")
    try:
        problems += settings_problems(line)
    except MissingField as exc:
        problems.append(f"K-5 missing {exc}")
    override = p5k.get("override") or {}
    expected_applications = 0 if arm == ARM_REF else None
    if expected_applications == 0 and override.get("applications"):
        problems.append(f"K-5 ref arm overridden {override.get('applications')} times")
    if arm == ARM_CAND and not override.get("applications"):
        problems.append("K-5 cand arm without an override")
    return problems


def identity_value_problems(line: dict) -> list[str]:
    """K-0 / K-1 per line: empty code diff, allowed dirty files only, threads 1, the sealed
    rules digests (adapted copy of ``k1_judge.identity_value_problems``)."""
    p5k = p5k_of(line)
    identity = p5k.get("identity") or {}
    problems = []
    if identity.get("code_diff_sha256") != EMPTY_SHA256:
        problems.append("K-1 code_diff_sha256 not empty")
    dirty = [name for name in identity.get("dirty_files") or () if name not in ALLOWED_DIRTY]
    if dirty:
        problems.append(f"K-1 dirty {dirty}")
    threads = identity.get("threads") or {}
    wrong = [name for name in THREAD_VARIABLES if threads.get(name) != "1"]
    if wrong or threads.get("MKL_THREADING_LAYER") != THREAD_LAYER:
        problems.append(f"K-1 threads {threads}")
    if p5k.get("rules") != sealed_rules():
        problems.append("K-0 rules sha256 are not the sealed set")
    return problems


def line_problems(line: dict) -> list[str]:
    """Every per-line stop check (K-0 .. K-5, K-8) of one finished line."""
    return (identity_value_problems(line) + tag_problems(line) + gate_problems(line)
            + las_problems(line) + k8_problems(line))


def identity_signature(line: dict) -> tuple:
    identity = p5k_of(line).get("identity") or {}
    return (identity.get("git_head"), identity.get("code_diff_sha256"),
            json.dumps(identity.get("sha256"), sort_keys=True),
            json.dumps(p5k_of(line).get("code_blobs"), sort_keys=True))


def git_blob_sha256(root: Path, head: str, path: str) -> str | None:
    """sha256 of ``git show <head>:<path>`` (read-only query; None when it fails)."""
    try:
        done = subprocess.run(["git", "-C", str(root), "show", f"{head}:{path}"],  # noqa: S603,S607
                              capture_output=True, timeout=60, check=False,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    return hashlib.sha256(done.stdout).hexdigest() if done.returncode == 0 else None


# =============================================================================== bundle judging
@dataclass
class Context:
    """Everything the judging reads (built by :func:`load_context`; unit tests build it)."""

    bases: Bases
    refs: References
    parts: dict[tuple[str, str], ArmLines]
    foreign: list[str]
    gs_lines: list[dict] = field(default_factory=list)
    blob_lookup: Any = None
    """``(head, path) -> sha256 | None`` (git); None skips the K-2 blob re-read."""


def criterion(ok: bool | None, items=None, **extra) -> dict:
    """One criterion: ``ok`` True / False / None (undecidable)."""
    status = STATUS_UNDECIDABLE if ok is None else (STATUS_PASS if ok else STATUS_FAIL)
    return {"ok": ok, "status": status, "items": list(items or []), "count": len(items or []),
            **extra}


def arm_completeness(bundle: str, arm: str, ctx: Context, claim_keys: list[str]) -> dict:
    part = ctx.parts[(bundle, arm)]
    wanted = expected_units(bundle, arm, ctx.bases, claim_keys)
    wanted_set = set(wanted)
    missing = [unit for unit in wanted if unit not in part.finished]
    errors_left = [unit for unit in missing if unit in part.error_units]
    return {"expected": len(wanted), "finished": len(part.finished),
            "error_lines": part.error_lines, "errors_total": part.error_lines,
            "errors_left": errors_left,
            "missing": [unit for unit in missing if unit not in part.error_units],
            "duplicates": list(part.duplicates),
            "out_of_list": sorted(unit for unit in part.finished if unit not in wanted_set),
            "reruns": sorted(set(part.reruns))}


def bit_predictions(bundle: str, ctx: Context) -> dict:
    """4.4 per arm: equal / different / missing against the expected hashes (no values)."""
    out = {}
    for arm in BUNDLE_ARMS[bundle]:
        expected = ctx.refs.hashes.get((bundle, arm))
        if bundle == "Z-X":
            expected = z_x_expected(ctx)
        if expected is None:
            out[arm] = {"predicted": False}
            continue
        part = ctx.parts[(bundle, arm)]
        different = sorted(unit for unit, line in part.finished.items()
                           if unit in expected and not _hash_matches(line, expected[unit]))
        equal = sum(1 for unit, line in part.finished.items()
                    if unit in expected and _hash_matches(line, expected[unit]))
        out[arm] = {"predicted": True, "expected": len(expected), "equal": equal,
                    "different": different, "ok": not different}
    return out


def _hash_matches(line: dict, expected) -> bool:
    """One expected hash, or (BT-X) the ref hashes of every bundle the key belongs to."""
    if isinstance(expected, (list, tuple)):
        return all(line["commands_sha256"] == sha for sha in expected)
    return line["commands_sha256"] == expected


def z_x_expected(ctx: Context) -> dict[str, list[str]]:
    """BT-X (rev2 RV2-6): a Z-X ref hash = the new ref hash of every bundle (Z-T / Z-S /
    Z-C) the key belongs to; a key of Z-S and Z-C must equal both."""
    out: dict[str, list[str]] = {}
    for bundle in PAIR_BUNDLES:
        for key, line in ctx.parts[(bundle, ARM_REF)].finished.items():
            out.setdefault(key, []).append(line["commands_sha256"])
    return out


def bundle_identity(bundle: str, ctx: Context) -> dict:
    """K-1 / K-2 over a bundle arm (one git_head and tool / blob sha) and the per-line checks."""
    problems: dict[str, list[str]] = {}
    signatures = {}
    for arm in BUNDLE_ARMS[bundle]:
        part = ctx.parts[(bundle, arm)]
        arm_signatures = {identity_signature(line) for line in part.finished.values()}
        signatures[arm] = len(arm_signatures)
        if len(arm_signatures) > 1:
            problems.setdefault("_bundle", []).append(
                f"K-1 / K-2 {arm}: {len(arm_signatures)} run identities")
        for unit, line in part.finished.items():
            found = line_problems(line) + blob_problems(line, ctx)
            if found:
                problems[f"{arm} {unit}"] = found
    return {"ok": not problems, "problems": problems, "identities_per_arm": signatures}


def blob_problems(line: dict, ctx: Context) -> list[str]:
    """K-2: the recorded HEAD blob sha256 of ``c2.py`` / ``v5_options.py`` = ``git show``."""
    if ctx.blob_lookup is None:
        return []
    head = (p5k_of(line).get("identity") or {}).get("git_head")
    recorded = p5k_of(line).get("code_blobs") or {}
    out = []
    for path in BLOB_FILES:
        now = ctx.blob_lookup(head, path)
        if now is None or recorded.get(path) != now:
            out.append(f"K-2 {path} blob {recorded.get(path)!r} != git show {head}: {now!r}")
    return out


def judge_z0(ctx: Context) -> dict:
    """Z-0: BT-0 only (6 lines)."""
    lines = ctx.parts[("Z-0", ARM_REF)].finished
    return {"bits": bit_predictions("Z-0", ctx),
            "records": {"anchor": {unit: anchor_arm(line) for unit, line in sorted(lines.items())}}}


def judge_za(ctx: Context) -> dict:
    """6.1 on the 102 cand lines: G-1 / G-1H / G-1Q, G-2', G-3, G-4 (K-A) and records."""
    part = ctx.parts[("Z-A", ARM_CAND)]
    by_part: dict[str, dict[tuple, dict]] = {PART_RG: {}, PART_RH: {}, PART_RQ: {}}
    undecidable, k_found = [], []
    for unit, line in sorted(part.finished.items()):
        name = part_of(line)
        if name is None:
            undecidable.append(f"{unit}: no part")
            continue
        try:
            point = grid_point_of(line)
        except MissingField as exc:
            undecidable.append(f"{unit}: missing {exc}")
            continue
        by_part[name][point] = line
        try:
            if name == PART_RQ:
                k_found += [f"{unit}: {text}" for text in quarter_k_problems(line)]
            else:
                pair = ctx.refs.p5_pairs.get(name, {}).get(point)
                if pair is None:
                    undecidable.append(f"{unit}: no stored P5 pair")
                    continue
                k_found += [f"{unit}: {text}" for text in grid_k_problems(line, pair, name)]
        except MissingField as exc:
            undecidable.append(f"{unit}: missing {exc}")
    errors_by_part = {name: 0 for name in by_part}
    for unit in part.error_units:
        name = part_of({"rev": {"label": unit}})
        if name in errors_by_part:
            errors_by_part[name] += 1
    g3 = []
    for name, lines in by_part.items():
        g3 += exclusion_problems(name, lines, errors_by_part[name])
    g1, between = force_failures(PART_RG, by_part[PART_RG], GRID_FORCE_FLOOR_KN)
    g1h, between_h = force_failures(PART_RH, by_part[PART_RH], GRID_FORCE_FLOOR_KN)
    g1q, between_q = force_failures(PART_RQ, by_part[PART_RQ], GRID_FORCE_FLOOR_KN)
    g2p = []
    for name, lines in by_part.items():
        g2p += force_failures(name, lines, G2P_FLOOR_KN)[0]
    ka_stop = [text for text in k_found if is_ka_stop(text)]
    criteria = {"G-1": criterion(not g1, g1), "G-1H": criterion(not g1h, g1h),
                "G-1Q": criterion(not g1q, g1q), "G-2'": criterion(not g2p, g2p),
                "G-3": criterion(None if g3 else True, g3),
                "G-4": criterion(not k_found if not undecidable else None,
                                 k_found + undecidable)}
    rows = [{"label": unit, "part": part_of(line), "F_RL_kN": _forces(line)[0],
             "F_judged_min_kN": _forces(line)[1], "trough": trough_kind(line),
             "las_start_t_s": (line.get("las") or {}).get("start_t_s"),
             "las_end_reason": (line.get("las") or {}).get("end_reason"),
             "ramp": (line.get("las") or {}).get("ramp")}
            for unit, line in sorted(part.finished.items())]
    return {"bits": bit_predictions("Z-A", ctx), "criteria": criteria,
            "ka_stop": ka_stop, "k_problems": k_found, "undecidable": undecidable,
            "between_thresholds": between + between_h + between_q,
            "records": {"G-2_cells": range_cells(by_part[PART_RG], RANGE_STEPS),
                        "rows": rows,
                        "anchor": {unit: anchor_arm(line)
                                   for unit, line in sorted(part.finished.items())},
                        "Q_M_records": "not recomputed: BT-A true reproduces the A-plan rev2 "
                                       "Q-1 .. Q-5 / M-1 .. M-3 values (rules 6.1)"}}


# --------------------------------------------------------------------------- pair bundles
def exception_record(cand: dict, ref: dict, rx_line: dict | None) -> dict:
    """C-4 exception of one pair with a READY delay above +1.0 s (copied from
    ``las_rev_judge.exception_record``; restarts after the end ramp, A-plan 6)."""
    delta_s = ready_time(cand) - ready_time(ref)
    out = {"dt_s": delta_s, "is_exception": False}
    clock = cand.get("done_clock")
    if rx_line is None or "done_clock" not in rx_line or clock is None:
        return {**out, "reason": "no done_clock on both sides (Z-X line missing)"}
    if rx_line["commands_sha256"] != ref["commands_sha256"]:
        return {**out, "reason": "BT-X Z-X hash differs from the ref", "h5": True}
    loss_s, ref_loss_s = clock.get("loss_s"), rx_line["done_clock"].get("loss_s")
    out.update(loss_cand_s=loss_s, loss_ref_s=ref_loss_s, resets=clock.get("resets"),
               t_las_end_s=ramp_end_s(cand),
               t_loc_last_s=clock.get("t_loc_last_before_done_s"))
    if loss_s is None or ref_loss_s is None:
        return {**out, "reason": "loss_s None"}
    excess_s = loss_s - ref_loss_s
    out["E_over_dt"] = excess_s / delta_s if delta_s else None
    if excess_s < EXCEPTION_SHARE * delta_s - TOLERANCE:
        return {**out, "reason": "E < 0.8 dt"}
    t_end_s = out["t_las_end_s"]
    if t_end_s is None:
        return {**out, "reason": "no LAS-b / ramp end time (rev2 RV2-11)"}
    starts = clock.get("clock_starts_s") or []
    # rev2 RV2-11: restarts inside l are c_1 <= t <= c_m; "after" is a larger whole period.
    counted = [reset for reset in clock.get("resets") or []
               if starts and starts[0] <= reset["t_s"] <= starts[-1]]
    end_period = period_of(t_end_s)
    if any(period_of(reset["t_s"]) <= end_period for reset in counted):
        return {**out, "reason": "a restart not after the LAS-b / ramp end period"}
    return {**out, "is_exception": True, "reason": "gate timing branch"}


def anchor_path_of(bias_events: int, anchor_events: int) -> str:
    """rev1 RV1-1: (1) ``INFO_CLEARANCE_BIAS``, (2) ``INFO_LOC_CLEARANCE_ANCHOR``, both
    ``1+2``, neither (3)."""
    if bias_events and anchor_events:
        return PATH_BOTH
    if bias_events:
        return PATH_CORNER_BIAS
    if anchor_events:
        return PATH_ANCHOR
    return PATH_NONE


def _source(line: dict, *path: str) -> tuple[Any, str | None]:
    """(value, missing field name): None and the dotted name when the field is absent."""
    try:
        return need(line, *path), None
    except MissingField:
        return None, ".".join(path)


def anchor_arm(line: dict) -> dict:
    """rev1 RV1-1 record of one arm (harness sources, ``anchor`` block first)."""
    missing = []
    names = line.get("event_names")
    if not isinstance(names, dict):
        missing.append("event_names")
    path = anchor_path_of(event_count(line, BIAS_EVENT), event_count(line, ANCHOR_EVENT))
    locs = event_count(line, LOC_EVENT)
    values = {}
    for name, source in (("t_L_first_s", ("values", "events", "t_loc_first_s")),
                         ("t_L_last_s", ("values", "events", "t_loc_last_s")),
                         ("t_P_last_s", ("anchor", "soil_meta", "t_P_s")),
                         ("raw_bias_m", ("anchor", "soil_meta", "bias_corner_raw_m")),
                         ("applied_bias_m", ("anchor", "soil_meta", "bias_corner_m")),
                         ("loc_anchor_bias_mm", ("anchor", "soil_meta", "loc_anchor_bias_mm")),
                         ("loc_anchor_applied", ("anchor", "soil_meta", "loc_anchor_applied"))):
        values[name], absent = _source(line, *source)
        if absent:
            missing.append(absent)
    values["t_P_first_s"], first_source = first_t_p(line, locs, values["t_P_last_s"])
    if first_source is None and locs:
        missing.append("t_P first (anchor.loc_calls / k1.loc_calls)")
    applied = values["applied_bias_m"] or []
    agree = None
    if values["loc_anchor_applied"] is not None:
        is_anchor_path = path in (PATH_ANCHOR, PATH_BOTH)
        agree = (is_anchor_path == (values["loc_anchor_applied"] is True)) and (
            path == PATH_NONE or any(v != 0.0 for v in applied))
    first_call = (line.get("anchor") or {}).get("loc_calls") or []
    return {"anchor_path": path, "loc_count": locs, **values,
            "n_L_first": period_of(values["t_L_first_s"]),
            "n_L_last": period_of(values["t_L_last_s"]),
            "n_P_first": period_of(values["t_P_first_s"]),
            "n_P_last": period_of(values["t_P_last_s"]), "t_P_first_source": first_source,
            "first_loc_bias": first_call[0] if first_call else None,
            "anchor_meta_agree": agree, "ANCHOR_RECORD_MISSING": missing}


def first_t_p(line: dict, locs: int, t_p_last: float | None) -> tuple[float | None, str | None]:
    """rev1 t_P first: ``anchor.loc_calls[0]``, else ``k1.loc_calls[0]``, else t_P last when
    there is exactly one LOC."""
    for source in (("anchor", "loc_calls"), ("k1", "loc_calls")):
        calls, _ = _source(line, *source)
        if calls:
            return calls[0].get("t_P_s"), ".".join(source)
    if locs == 1 and t_p_last is not None:
        return t_p_last, "t_P last (one LOC)"
    return None, None


def anchor_record(cand: dict, ref: dict) -> dict:
    """rev1 RV1-1 / RV1-2 of one pair: both arms and the FLAG ``ANCHOR_SAMPLE_SHIFT`` (True,
    False, or None when no slot can be compared)."""
    arms = {ARM_REF: anchor_arm(ref), ARM_CAND: anchor_arm(cand)}
    uses_anchor = any(arm["anchor_path"] in ANCHOR_PATHS for arm in arms.values())
    deltas = {}
    for slot in ("n_P_first", "n_P_last", "n_L_first", "n_L_last"):
        ref_value, cand_value = arms[ARM_REF][slot], arms[ARM_CAND][slot]
        deltas[slot] = None if ref_value is None or cand_value is None else cand_value - ref_value
    compared = [deltas[slot] for slot in ("n_P_first", "n_P_last") if deltas[slot] is not None]
    if not uses_anchor:
        flag = False
    elif not compared:
        flag = None
    else:
        flag = any(delta != 0 for delta in compared)
    missing = sorted({name for arm in arms.values() for name in arm["ANCHOR_RECORD_MISSING"]})
    return {"ref": arms[ARM_REF], "cand": arms[ARM_CAND], "delta": deltas,
            FLAG_ANCHOR_SAMPLE_SHIFT: flag, "ANCHOR_RECORD_MISSING": missing}


def las_start_s(line: dict) -> float | None:
    """``las.start_t_s``; a run whose LAS-b wrapper was never reached has no start (None).

    Raises:
        MissingField: Neither the start nor ``wrapper_reached`` false is recorded.
    """
    las = need(line, "las")
    if "start_t_s" in las:
        return las["start_t_s"]
    if las.get("wrapper_reached") is False:
        return None
    raise MissingField("las.start_t_s")


RANGE_IN, RANGE_OUT_REF_NONE, RANGE_OUT = "in", "ref_none", "out"
"""rev2 RV2-2 scope of a C-F / C-S pair: judged, outside because the ref value is None, or
outside the C-F scope (ref below the margin line)."""


def cf_state(f_ref: float | None, f_cand: float | None) -> tuple[str, bool]:
    """rev2 RV2-2 1: (scope, violation) of C-F."""
    if f_ref is None:
        return RANGE_OUT_REF_NONE, False
    if f_ref < C_FLOOR_N:
        return RANGE_OUT, False
    return RANGE_IN, f_cand is None or f_cand < C_FLOOR_N


def cs_state(s_ref: float | None, s_cand: float | None) -> tuple[str, bool]:
    """rev2 RV2-2 2: (scope, violation) of C-S (ref None: outside, both None included;
    cand None with a ref value: violation)."""
    if s_ref is None:
        return RANGE_OUT_REF_NONE, False
    if s_cand is None:
        return RANGE_IN, True
    return RANGE_IN, float(s_cand) - float(s_ref) > STROKE_LIMIT_M + TOLERANCE


def _decide(record: dict, name: str, evaluate):
    """rev2 RV2-4: a missing field makes only the criterion ``name`` undecidable."""
    try:
        return evaluate()
    except MissingField as exc:
        record["undecided"][name] = str(exc)
        return None


def _p3_of(cand: dict, ref: dict) -> dict:
    if not is_verdict_case(ref):
        same_trajectory_drift(cand, ref)
    return p3_comparison(cand, ref)


def pair_record(key: str, cand: dict, ref: dict, rx_line: dict | None) -> dict:
    """Every 6.2 quantity of one pair (cand - ref); a missing field is recorded in
    ``undecided`` under the criterion that reads it (rev2 RV2-4)."""
    is_case = is_verdict_case(ref)
    is_changed = cand["commands_sha256"] != ref["commands_sha256"]
    record = {"key": key, "changed": is_changed, "is_case": is_case, "undecided": {}}
    start_t_s = _decide(record, "PAIR_DIVERGE", lambda: las_start_s(cand))
    is_premise_known = "PAIR_DIVERGE" not in record["undecided"]
    record.update(c2=_decide(record, "C-2", lambda: c2_violations(cand, ref)),
                  cand_las_started=start_t_s is not None,
                  PAIR_DIVERGE=is_premise_known and start_t_s is None and is_changed,
                  PAIR_CMD_DIFF=is_premise_known and start_t_s is not None and is_changed)
    p3 = _decide(record, "P3", lambda: _p3_of(cand, ref)) or {}
    record.update(P3=p3.get("violations"), P3_baseline_false=p3.get("baseline_false", []),
                  CK1=_decide(record, "CK-1", lambda: ck1_record(cand, ref)),
                  anchor=anchor_record(cand, ref))
    record["ready_cand_s"] = _decide(record, "R", lambda: ready_time(cand))
    record["ready_ref_s"] = _decide(record, "R", lambda: ready_time(ref))
    if not is_case:
        _d1_fields(record, cand, ref)
    both = record["ready_cand_s"] is not None and record["ready_ref_s"] is not None
    record["dt_s"] = record["ready_cand_s"] - record["ready_ref_s"] if both else None
    if is_changed and both and record["dt_s"] > EXCEPTION_DT_FLOOR_S:
        record["exception"] = exception_record(cand, ref, rx_line)
    record["record"] = pair_note(cand, ref)
    return record


def _d1_fields(record: dict, cand: dict, ref: dict) -> None:
    """C-F / C-S values of a D-1 pair with their rev2 RV2-2 scope."""
    forces = _decide(record, "C-F", lambda: (need(ref, "d1", "F_judged_min_N"),
                                             need(cand, "d1", "F_judged_min_N")))
    strokes = _decide(record, "C-S", lambda: (need(ref, "d1", "stroke_max_m"),
                                              need(cand, "d1", "stroke_max_m")))
    f_ref, f_cand = forces or (None, None)
    s_ref, s_cand = strokes or (None, None)
    record.update(F_ref_N=f_ref, F_cand_N=f_cand, stroke_ref_m=s_ref, stroke_cand_m=s_cand,
                  stroke_increase_m=None if s_ref is None or s_cand is None
                  else float(s_cand) - float(s_ref))
    record["C-F_scope"], record["C-F_violation"] = cf_state(f_ref, f_cand) if forces \
        else (None, False)
    record["C-S_scope"], record["C-S_violation"] = cs_state(s_ref, s_cand) if strokes \
        else (None, False)
    try:
        record.update(items_only(cand, ref))
    except MissingField:
        pass


def pair_note(cand: dict, ref: dict) -> dict:
    """6.4 record of one pair (record only)."""
    def las_of(line):
        las = line.get("las") or {}
        ramp = las.get("ramp") or {}
        return {"start_t_s": las.get("start_t_s"), "end_t_s": las.get("end_t_s"),
                "end_reason": las.get("end_reason"), "active_periods": las.get("active_periods"),
                "lambda0": ramp.get("start_factor"), "ramp_end_reason": ramp.get("end_reason"),
                "ramp_periods": ramp.get("periods_applied")}

    def d1_of(line):
        d1 = line.get("d1") or {}
        return {"F_judged_min_N": d1.get("F_judged_min_N"),
                "F_first_level_after_liftoff_min_N": d1.get("F_first_level_after_liftoff_min_N"),
                "stroke_max_m": d1.get("stroke_max_m"),
                "t_first_loc_s": (line.get("done_clock") or {}).get("t_first_loc_s")}

    return {"cand_las": las_of(cand), "ref_las": las_of(ref), "cand_d1": d1_of(cand),
            "ref_d1": d1_of(ref)}


def ready_population(pairs: dict[str, dict]) -> dict:
    """R-1 / R-2 over the changed pairs without the C-4 exceptions, with the empty-set rule
    (copied from ``las_rev_judge.ready_population``)."""
    changed = [key for key, pair in pairs.items() if pair["changed"]]
    exceptions, population, h5 = [], {}, []
    open_keys = sorted(key for key, pair in pairs.items() if "R" in pair.get("undecided", {}))
    for key in changed:
        pair = pairs[key]
        if pair["dt_s"] is None:
            continue
        record = pair.get("exception")
        if record is not None and record.get("h5"):
            h5.append(key)
        if record is not None and record["is_exception"]:
            exceptions.append(key)
            continue
        population[key] = pair["dt_s"]
    out = {"changed": len(changed), "population": len(population), "exceptions": exceptions,
           "BT-X_mismatch": h5, "median_s": None, "max_s": None, "undecided_pairs": open_keys}
    if open_keys:
        values = list(population.values())
        return {**out, "R-1": None, "R-2": None, "basis": "READY field missing (rev2 RV2-4)",
                "median_s": statistics.median(values) if values else None,
                "max_s": max(values) if values else None}
    if not changed:
        return {**out, "R-1": True, "R-2": True, "basis": f"{len(pairs)}/{len(pairs)} hash equal"}
    if not population:
        return {**out, "R-1": None, "R-2": None, "basis": "changed pairs but empty population"}
    values = list(population.values())
    out.update(median_s=statistics.median(values), max_s=max(values))
    out["R-1"] = out["median_s"] <= READY_MEDIAN_LIMIT_S + TOLERANCE
    out["R-2"] = out["max_s"] <= READY_MAX_LIMIT_S + TOLERANCE
    out["basis"] = "population"
    return out


def judged_pairs(bundle: str, ctx: Context) -> tuple[dict[str, dict], list[str], list[str]]:
    """(pair records, undecidable texts, unpaired keys) of a pair bundle."""
    ref_part, cand_part = ctx.parts[(bundle, ARM_REF)], ctx.parts[(bundle, ARM_CAND)]
    rx = ctx.parts[("Z-X", ARM_REF)].finished
    pairs, undecidable = {}, []
    keys = sorted(set(ref_part.finished) & set(cand_part.finished))
    unpaired = sorted(set(ref_part.finished) ^ set(cand_part.finished))
    for key in keys:
        try:
            pairs[key] = pair_record(key, cand_part.finished[key], ref_part.finished[key],
                                     rx.get(key))
        except MissingField as exc:  # a field no single criterion owns (``commands_sha256``)
            undecidable.append(f"{key}: missing {exc}")
    for key, pair in pairs.items():
        undecidable += [f"{key} {name}: missing {field_name}"
                        for name, field_name in sorted(pair["undecided"].items())]
    return pairs, undecidable, unpaired


def _open_keys(pairs: dict[str, dict], name: str) -> list[str]:
    return sorted(k for k, p in pairs.items() if name in p["undecided"])


def _pair_criteria(bundle: str, pairs: dict[str, dict], whole_pair_open: bool,
                   bases: Bases) -> dict:
    """6.2 criteria; a pair whose field a criterion reads is missing makes that criterion
    undecidable (rev2 RV2-4, 16.6 layer 1) while the violations are still listed.

    Args:
        whole_pair_open: A pair could not be built at all (every criterion undecidable).
    """

    def make(items, name, **extra):
        open_keys = _open_keys(pairs, name)
        is_open = whole_pair_open or bool(open_keys)
        return criterion(None if is_open else not items, items, undecidable_pairs=open_keys,
                         **extra)

    c2 = [f"{k}: {p['c2']}" for k, p in pairs.items() if p["c2"]]
    p3 = [f"{k}: {p['P3']}" for k, p in pairs.items() if p["P3"]]
    d1 = {k: p for k, p in pairs.items() if not p["is_case"]}
    cf = [f"{k}: ref {p['F_ref_N']} -> {p['F_cand_N']}" for k, p in d1.items()
          if p["C-F_violation"]]
    cs = [f"{k}: {p['stroke_ref_m']} -> {p['stroke_cand_m']}" for k, p in d1.items()
          if p["C-S_violation"]]
    ck1 = [f"{k}: R4_LOST" for k, p in pairs.items() if p["CK1"] and p["CK1"]["R4_LOST"]]

    def ref_none(name):
        return sorted(k for k, p in d1.items() if p[f"{name}_scope"] == RANGE_OUT_REF_NONE)

    out = {"C-2": make(c2, "C-2"), "P3": make(p3, "P3"),
           "C-F": make(cf, "C-F", ref_none=ref_none("C-F")),
           "C-S": make(cs, "C-S", ref_none=ref_none("C-S")), "CK-1": make(ck1, "CK-1"),
           "PAIR_DIVERGE_premise": make([], "PAIR_DIVERGE")}
    if bundle == "Z-T":
        t1 = set(bases.lists["Z-T-ref"]) & {line["las"]["key"] for line in bases.lines["T1"]
                                            if is_b0_t_line(line)}
        c1 = [f"{k}: {p['F_cand_N']}" for k, p in d1.items() if k in t1
              and "C-F" not in p["undecided"]
              and (p["F_cand_N"] is None or p["F_cand_N"] < C_FLOOR_N)]
        out["C-1"] = make(c1, "C-F")
        h_r_0 = [key for key in bases.lists["Z-T"] if H_R_0_MARK in key]
        a3 = [key for key in h_r_0 if key in pairs and pairs[key]["changed"]]
        a3_open = (whole_pair_open or len(h_r_0) != H_R_0_COUNT
                   or any(k not in pairs for k in h_r_0))
        out["A-3"] = criterion(None if a3_open else not a3, a3, h_r_0_keys=len(h_r_0))
    return out


def judge_pair_bundle(bundle: str, ctx: Context) -> dict:
    """6.2 of Z-T / Z-S / Z-C with ``PAIR_DIVERGE`` (stop) and the records."""
    pairs, undecidable, unpaired = judged_pairs(bundle, ctx)
    whole_pair_open = len(undecidable) > sum(len(p["undecided"]) for p in pairs.values())
    criteria = _pair_criteria(bundle, pairs, whole_pair_open, ctx.bases)
    ready = ready_population(pairs)
    if bundle in ("Z-T", "Z-C"):
        ok = None if (whole_pair_open or ready["R-1"] is None) else ready["R-1"]
        criteria["R-1"] = criterion(ok, [] if ok in (True, None) else [ready["median_s"]])
        ok = None if (whole_pair_open or ready["R-2"] is None) else ready["R-2"]
        criteria["R-2"] = criterion(ok, [] if ok in (True, None) else [ready["max_s"]])
    diverge = sorted(k for k, p in pairs.items() if p["PAIR_DIVERGE"])
    cmd_diff = sorted(k for k, p in pairs.items() if p["PAIR_CMD_DIFF"])
    c2_pairs = [k for k, p in pairs.items() if p["c2"]]
    exceptions = ready["exceptions"]
    s8_ask = len(exceptions) > EXCEPTION_COUNT_LIMIT or any(
        pairs[k]["dt_s"] > EXCEPTION_DT_LIMIT_S for k in exceptions)
    out = {"bits": bit_predictions(bundle, ctx), "criteria": criteria, "ready": ready,
           "pairs_decided": len(pairs), "undecidable_pairs": undecidable,
           "unpaired": unpaired, "PAIR_DIVERGE": diverge, "PAIR_CMD_DIFF": len(cmd_diff),
           "PAIR_CMD_DIFF_keys": cmd_diff, "c2_pairs": len(c2_pairs),
           "S-5_c2_stop": len(c2_pairs) >= C2_STOP_PAIRS, "S-8_ask": s8_ask,
           "flags": pair_flags(pairs), **anchor_effect(pairs), "pairs": pairs}
    if bundle == "Z-C":
        out["sample_split"] = sample_split(pairs, ctx.bases)
    return out


def is_cs_violation(pair: dict) -> bool:
    return not pair["is_case"] and bool(pair.get("C-S_violation"))


def anchor_effect(pairs: dict[str, dict]) -> dict:
    """rev1 RV1-3: C-S / P3 violation pairs with ``ANCHOR_SAMPLE_SHIFT`` (``앵커 표본 효과
    가능``) and with the FLAG None (``앵커 기록 없음``); the verdict stays as it is."""
    violating = {k: p for k, p in pairs.items() if is_cs_violation(p) or p["P3"]}
    return {"anchor_effect_possible": sorted(
                k for k, p in violating.items() if p["anchor"][FLAG_ANCHOR_SAMPLE_SHIFT] is True),
            "anchor_effect_unknown": sorted(
                k for k, p in violating.items() if p["anchor"][FLAG_ANCHOR_SAMPLE_SHIFT] is None)}


def pair_flags(pairs: dict[str, dict]) -> dict:
    """6.4 FLAG lists (record only)."""
    between = [f"{k}: {p.get('F_cand_N')}" for k, p in pairs.items()
               if p.get("F_cand_N") is not None
               and GRID_FORCE_FLOOR_KN * 1e3 <= p["F_cand_N"] < C_FLOOR_N]
    return {"R4_GAINED": sorted(k for k, p in pairs.items() if (p["CK1"] or {}).get("R4_GAINED")),
            "THIN_MARGIN": sorted(k for k, p in pairs.items()
                                  if (p["CK1"] or {}).get("thin_margin")),
            FLAG_ANCHOR_SAMPLE_SHIFT: sorted(k for k, p in pairs.items()
                                             if p["anchor"][FLAG_ANCHOR_SAMPLE_SHIFT] is True),
            "ANCHOR_SAMPLE_SHIFT_none": sorted(k for k, p in pairs.items()
                                               if p["anchor"][FLAG_ANCHOR_SAMPLE_SHIFT] is None),
            "ANCHOR_RECORD_MISSING": sorted(k for k, p in pairs.items()
                                            if p["anchor"]["ANCHOR_RECORD_MISSING"]),
            "between_10p400_10p4146_kN": between,
            "P3_baseline_false": sorted(k for k, p in pairs.items() if p["P3_baseline_false"])}


def sample_split(pairs: dict[str, dict], bases: Bases) -> dict:
    """6.4: Z-C results in-sample (the 19 R-S keys) and out-of-sample (437 keys)."""
    in_sample = set(bases.lists["Z-C"]) & set(bases.lists["Z-S"])

    def summary(keys):
        selected = {k: pairs[k] for k in keys if k in pairs}
        return {"pairs": len(selected),
                "changed": sum(1 for p in selected.values() if p["changed"]),
                "c2_pairs": sorted(k for k, p in selected.items() if p["c2"]),
                "cs_over": sorted(k for k, p in selected.items() if is_cs_violation(p)),
                "R4_LOST": sorted(k for k, p in selected.items()
                                  if (p["CK1"] or {}).get("R4_LOST")),
                "las_started": sum(1 for p in selected.values() if p["cand_las_started"])}

    return {"in_sample": summary(sorted(in_sample)),
            "out_of_sample": summary(sorted(set(bases.lists["Z-C"]) - in_sample))}


def claim_keys(ctx: Context) -> list[str]:
    """Z-X keys: changed pairs of Z-T / Z-S / Z-C with a READY delay above +1.0 s."""
    out = set()
    for bundle in PAIR_BUNDLES:
        ref_part, cand_part = ctx.parts[(bundle, ARM_REF)], ctx.parts[(bundle, ARM_CAND)]
        for key, cand in cand_part.finished.items():
            ref = ref_part.finished.get(key)
            if ref is None or cand["commands_sha256"] == ref["commands_sha256"]:
                continue
            try:
                cand_s, ref_s = ready_time(cand), ready_time(ref)
            except MissingField:
                continue
            if cand_s is not None and ref_s is not None and cand_s - ref_s > EXCEPTION_DT_FLOOR_S:
                out.add(key)
    return sorted(out)


def gs_equality(ctx: Context) -> dict:
    """16.2: a G-S line and the main-run line of the same bundle, arm and unit have the same
    ``commands_sha256`` (reported as same / different only)."""
    different, same = [], 0
    for line in ctx.gs_lines:
        if is_error(line):
            continue
        block = p5k_of(line)
        part = ctx.parts.get((block.get("bundle"), block.get("arm")))
        main = None if part is None else part.finished.get(unit_of(line))
        if main is None:
            continue
        if main["commands_sha256"] == line["commands_sha256"]:
            same += 1
        else:
            different.append(f"{block.get('bundle')} {block.get('arm')} {unit_of(line)}")
    return {"gs_lines": len(ctx.gs_lines), "compared": same + len(different), "same": same,
            "different": different, "ok": not different}


# =============================================================================== status (8, 16.6)
def bundle_status(bundle: str, result: dict, completeness: dict, identity: dict,
                  ref_problems: list[str]) -> tuple[str, list[str]]:
    """8.1 order with 16.6: stop > undecidable > fail > pass; (status, reasons)."""
    reasons = []
    has_lines = any(c["finished"] or c["error_lines"] for c in completeness.values())
    if bundle == "Z-X" and not any(c["expected"] for c in completeness.values()):
        return STATUS_PASS, ["no C-4 exception claim: Z-X not needed"]
    if not has_lines:
        return STATUS_INCOMPLETE, ["no lines"]
    bits = result.get("bits") or {}
    for arm, bit in bits.items():
        if bit.get("predicted") and bit.get("different"):
            reasons.append(f"stop: bit prediction {arm} {len(bit['different'])} different")
    if not identity["ok"]:
        reasons.append(f"stop: identity / K problems {len(identity['problems'])}")
    if result.get("ka_stop"):
        reasons.append(f"stop: K-A5 / K-A6 / K-A8 {len(result['ka_stop'])}")
    if result.get("PAIR_DIVERGE"):
        reasons.append(f"stop: PAIR_DIVERGE {len(result['PAIR_DIVERGE'])}")
    if ref_problems:
        reasons.append(f"stop: stored reference problems {len(ref_problems)} (S-3)")
    for arm, comp in completeness.items():
        if comp["duplicates"] or comp["out_of_list"]:
            reasons.append(f"stop: K-9 {arm} duplicates {len(comp['duplicates'])} out of list "
                           f"{len(comp['out_of_list'])}")
    if any(text.startswith("stop") for text in reasons):
        return STATUS_STOP, reasons
    for arm, comp in completeness.items():
        if comp["missing"] or comp["errors_left"]:
            reasons.append(f"incomplete: {arm} missing {len(comp['missing'])}, errors left "
                           f"{len(comp['errors_left'])}")
    if result.get("unpaired"):
        reasons.append(f"incomplete: unpaired {len(result['unpaired'])}")
    criteria = result.get("criteria") or {}
    statuses = [c["status"] for c in criteria.values()]
    if any(text.startswith("incomplete") for text in reasons):
        statuses.append(STATUS_UNDECIDABLE)
    status = worst_status(statuses)
    reasons += [f"{name}: {c['status']}" for name, c in criteria.items()
                if c["status"] != STATUS_PASS]
    return status, reasons


def final_status(bundles: dict[str, dict]) -> str:
    """16.6 layer 3: worst over the bundles; a ``not_run`` bundle behind a ``fail`` does not
    make the final undecidable."""
    statuses = []
    has_fail = False
    for name in BUNDLES:
        status = bundles[name]["status"]
        if status == STATUS_FAIL:
            has_fail = True
        if status == STATUS_INCOMPLETE and has_fail:
            continue
        statuses.append(status)
    return worst_status(statuses)


# =============================================================================== driver
def load_context(run_dir: Path, v5_dir: Path, gs_dir: Path | None, root: Path = ROOT
                 ) -> Context:
    """Read the stored files, the references and the run lines.

    Raises:
        InputError: Seals, stored files or lists are not the sealed ones.
    """
    bases = load_bases(v5_dir)
    refs = build_references(bases)
    parts, foreign = split_lines(read_run_lines(run_dir) if run_dir.is_dir() else [])
    gs_lines = []
    if gs_dir is not None and gs_dir.is_dir():
        for path in sorted(gs_dir.glob(GS_FILE_PATTERN)):
            gs_lines += read_lines(path)
    return Context(bases, refs, parts, foreign, gs_lines,
                   lambda head, path: git_blob_sha256(root, head, path) if head else None)


def judge(ctx: Context) -> dict:
    """Every bundle, the cross checks and the provisional grade."""
    claims = claim_keys(ctx)
    results = {"Z-0": judge_z0(ctx), "Z-A": judge_za(ctx)}
    for bundle in PAIR_BUNDLES:
        results[bundle] = judge_pair_bundle(bundle, ctx)
    results["Z-X"] = {"bits": bit_predictions("Z-X", ctx), "claim_keys": claims,
                      "over_limit": len(claims) > Z_X_MAX_LINES}
    bundles = {}
    for bundle in BUNDLES:
        completeness = {arm: arm_completeness(bundle, arm, ctx, claims)
                        for arm in BUNDLE_ARMS[bundle]}
        identity = bundle_identity(bundle, ctx)
        ref_problems = [text for text in ctx.refs.problems
                        if text.startswith(REFERENCE_SOURCES[bundle])]
        status, reasons = bundle_status(bundle, results[bundle], completeness, identity,
                                        ref_problems)
        bundles[bundle] = {"status": status, "grade": GRADES[status], "reasons": reasons,
                           "completeness": completeness, "identity": identity,
                           **results[bundle]}
    _apply_order(bundles)
    final = final_status(bundles)
    if ctx.foreign:
        final = STATUS_STOP
    gs = gs_equality(ctx)
    if not gs["ok"]:
        final = STATUS_STOP
    asks = [f"{name} S-8" for name in PAIR_BUNDLES if bundles[name].get("S-8_ask")]
    if results["Z-X"]["over_limit"]:
        asks.append(f"Z-X {len(claims)} claim keys > {Z_X_MAX_LINES}")
    return {"provisional": True, "k10": None, "final_status": final,
            "final_grade": GRADES[final], "asks": asks, "foreign_lines": ctx.foreign,
            "reference_problems": ctx.refs.problems, "yp_error_keys": ctx.refs.yp_error_keys,
            "gs_equality": gs, "label_list_sha256": label_list_sha256(ctx.bases),
            "bundles": bundles}


def _apply_order(bundles: dict[str, dict]) -> None:
    """8.1 S-2 / S-4: after a Z-0 / Z-A stop or any fail, later bundles without lines are
    ``not_run`` (record), never a reason for the final grade."""
    blocked = False
    for name in BUNDLES:
        bundle = bundles[name]
        if blocked and bundle["status"] == STATUS_INCOMPLETE and not any(
                c["finished"] for c in bundle["completeness"].values()):
            bundle["status"], bundle["grade"] = STATUS_NOT_RUN, GRADES[STATUS_NOT_RUN]
        if bundle["status"] in (STATUS_FAIL, STATUS_STOP):
            blocked = True


def tool_record() -> dict:
    return {"path": TOOL_PATH.as_posix(), "sha256": raw_sha256(TOOL_PATH),
            "lf_sha256": lf_sha256(TOOL_PATH), "copied_from": COPIED_FROM}


def error_line_counts(doc: dict) -> dict[str, dict[str, int]]:
    """16.3 / rev2 RV2-8 per bundle: ``errors_total`` (every error line, first attempts
    included) and ``errors_left`` ((arm, key) with error lines and no finished line)."""
    return {name: {"errors_total": sum(c["errors_total"]
                                       for c in bundle["completeness"].values()),
                   "errors_left": sum(len(c["errors_left"])
                                      for c in bundle["completeness"].values())}
            for name, bundle in (doc.get("bundles") or {}).items()}


def summary_of(doc: dict) -> dict:
    return {"tool": "las_p5r4k1_judge", "provisional": True, "k10": None,
            "final_status": doc.get("final_status"), "final_grade": doc.get("final_grade"),
            "asks": len(doc.get("asks") or []), "errors": error_line_counts(doc),
            "bundles": {name: b["status"] for name, b in (doc.get("bundles") or {}).items()},
            "out": doc.get("out")}


def _parse_args(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--v5-dir", type=Path, default=V5_DIR,
                        help="v5 folder with the stored files (the main checkout's)")
    parser.add_argument("--run-dir", type=Path, default=None,
                        help="folder of the p5k_Z*.jsonl lines (default <v5>/las/p5r4k1)")
    parser.add_argument("--gs-dir", type=Path, default=None,
                        help="G-S folder (16.2 hash equality; default <run-dir>/gs if present)")
    parser.add_argument("--expect-judge-sha", default=None,
                        help="this tool's sha256 recorded by the pre-run audit (K-0)")
    parser.add_argument("--out", type=Path, default=None, help="judgement JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    print("PROVISIONAL grade (k10 null until the path 2 recount agrees, rules 10.2)")
    try:
        problems = seal_problems()
        if problems:
            raise InputError(problems)
        tool = tool_record()
        if args.expect_judge_sha and args.expect_judge_sha not in (tool["sha256"],
                                                                   tool["lf_sha256"]):
            raise InputError([f"K-0 judge sha256 {tool['sha256']} != {args.expect_judge_sha}"])
        run_dir = args.run_dir or args.v5_dir / RUN_DIR_RELATIVE
        gs_dir = args.gs_dir or run_dir / GS_DIR_NAME
        ctx = load_context(run_dir, args.v5_dir, gs_dir)
    except InputError as exc:
        print(f"input error: {exc}")
        print(json.dumps({"tool": "las_p5r4k1_judge", "final_status": STATUS_STOP,
                          "input_error": str(exc)}, ensure_ascii=False))
        return 2
    except (OSError, ValueError) as exc:
        print(f"tool error: {exc!r}")
        print(json.dumps({"tool": "las_p5r4k1_judge", "tool_error": repr(exc)}))
        return 3
    doc = judge(ctx)
    doc["tool"] = tool
    doc["rules"] = sealed_rules()
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1, default=str),
                            encoding="utf-8")
        doc["out"] = str(args.out)
    for name, bundle in doc["bundles"].items():
        print(f"{name}: {bundle['status']} ({len(bundle['reasons'])} reasons)")
    code = EXIT_CODES.get(doc["final_status"], 1)
    if code == 0 and doc["asks"]:
        code = 1
    print(json.dumps(summary_of(doc), ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
