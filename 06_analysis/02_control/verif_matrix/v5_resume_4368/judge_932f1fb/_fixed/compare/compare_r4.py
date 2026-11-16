"""Compare the two 436.8 R4 harness judgement paths with each other and with the baseline sets.

Re-audit ``r4_prerun_reaudit.md`` M-1 (audit A-1). The finished outputs of path 1
(``harness_path1``) and path 2 (``harness_path2``) are compared item by item with the K-10 rule
of R4 block RD-5 (classes, booleans, lists and counts exactly; numbers within
|a - b| <= 1e-9 max(1, |a|, |b|)):

- RD-7 2: the J-P3, J11 and stop S-6 lists of the two paths
- JD-1 / JD-3: the J-P3 and S-6 lists against ``jp_base`` (5) and ``s6_base`` (67)
- JD-2 / JD-7: the G-5 and G-6 lists of the two paths and their 5 / 3 key sets
- JD-8: the RD-8 marker of bundles H-1, H-3, H-4
- supplements 5 / 6: lists (a) and (c) with N_raw / N_F, table (b) with the three-valued
  application condition, records, V0 pair source, the "stop H-10" marker, family F R-1 .. R-4
- RD-11 J_P reading and the H-11 G-3 gate
- RD-8 undecidable counts and marker, RD-9 ③-on counts (with the H-8 dg3 substitution),
  RD-10 J11 counts
- C-9 .. C-11 record items (K-10; the RD-5 / CD-10 excluded keys are not compared)

Not compared: H-12 (path 1 only), bundle grades (path 1 has no bundle-grade summary; its grades
are read from the findings of several judges). RD-13 lists are compared in the K-R table; their
sha256 values are only copied into the report (``rd13_sha256``).

Every difference of column names and value words between the paths is a constant of this module
(``FIELD_SOURCES``, ``COLUMN_MAP``, ``VALUE_WORDS``), fixed before any result exists. Their sha256
is printed by ``--show-map`` and written into every report.

Exit codes: 0 every item equal, 1 a difference, 2 an input error (an expected output file or key
is missing, a list that must not be empty is empty, the baseline sha256 is not the fixed one).

Usage:
    python -I -B compare_r4.py --path1-dir <judge_x/harness_path1> \
        --path2-dir <judge_x/harness_path2> --baseline <r4_baseline_sets.json> --out <report.json>
    python -I -B compare_r4.py --show-map
"""

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BASELINE_SHA256 = "a5627304037729330e1afa5f6a38dbd14fa6aa88210aea3326d5bb9e01b63f29"
"""MD-3 baseline sets, fixed 2026-11-16 11:36:07 +0900 (``r4_baseline_sets.sha256``)."""
RELATIVE_TOLERANCE = 1e-9
"""RD-5 / original 9.2 K-10: numbers agree when |a - b| <= 1e-9 max(1, |a|, |b|)."""

PATH1_FILES = {
    "r4_lists": "r4_lists.json",
    "u3": "u3_judge.json",
    "h11": "h11.json",
    "grid": "grid_h10.json",
    "family_f": "family_f.json",
    "jp": "jp_reuse.json",
    "x16": "x16_records.json",
    "item_list": "item_list.json",
}
"""Path 1 output names (``run_judgement_path1_draft.ps1`` sha256 8e801fa3, README_judges R4)."""
PATH2_FILES = {
    "harness": "harness.json",
    "merge": "p2v5c_merge.json",
    "grid": "p2v5c_grid.json",
    "u3": "u3.json",
    "g3": "g3.json",
    "jp": "jp.json",
    "c16": "c16.json",
    "noise": "p2v5c_noise.json",
    "items": "rd13_items.json",
}
"""Path 2 output names (re-audit M-2, path2/README "실행 예 (R4)", path2_v5c/README)."""

FIELD_SOURCES: dict[str, dict[str, tuple[str, str]]] = {
    "path1": {
        "J-P3": ("r4_lists", "lists.J-P3"),
        "J11": ("r4_lists", "lists.J11"),
        "S-6": ("r4_lists", "lists.S-6"),
        "bundle_markers": ("r4_lists", "bundles.{bundle}.markers"),
        "G-5": ("u3", "R4.G-5_list_RD7"),
        "G-6": ("u3", "R4.G-6_list_RD7"),
        "pair_source": ("grid", "v0_pair_source.source"),
        "sample_jobs": ("grid", "v0_pair_source.sample_jobs"),
        "sample_same": ("grid", "v0_pair_source.sample_jobs_same"),
        "grid_raw": ("grid", "raw_pass_to_fail"),
        "grid_n_raw": ("grid", "N_raw"),
        "grid_excluded": ("grid", "excluded_pass_to_fail"),
        "grid_n_f": ("grid", "N_F"),
        "family_table": ("grid", "family_f_rows"),
        "application": ("grid", "application_condition"),
        "pass_to_pass": ("grid", "record.pass_to_pass"),
        "fail_to_pass": ("grid", "record.fail_to_pass"),
        "fail_to_fail": ("grid", "record.fail_to_fail"),
        "n_fault": ("grid", "record.fault"),
        "fault_rows": ("grid", "record.fault_rows"),
        "undecidable_rows": ("grid", "record.not_judgeable"),
        "h10_marker": ("grid", "h10_marker"),
        "h10_term": ("grid", "h10_grid_selected.count"),
        "h10_value": ("grid", "h10_grid_selected.value"),
        "family_k": ("family_f", "k"),
        "family_R1": ("family_f", "R-1"),
        "family_R2": ("family_f", "R-2"),
        "family_R3": ("family_f", "R-3"),
        "family_R4": ("family_f", "R-4"),
        "family_R3_violations": ("family_f", "R-3_violations"),
        "family_R4_violations": ("family_f", "R-4_violations"),
        "family_result": ("family_f", "result"),
        "jp_rows_count": ("jp", "rows_count"),
        "jp_rows": ("jp", "rows"),
        "jp_stop_markers": ("jp", "stop_markers"),
        "jp_reuse": ("jp", "reuse"),
        "g3": ("h11", "G-3"),
        "g3_false_pairs": ("h11", "false_pairs_RD7"),
        "rd8_record": ("r4_lists", "bundles.{bundle}.RD-8"),
        "rd8_judged": ("r4_lists", "bundles.{bundle}.J-P3_not_judgeable"),
        "rd9": ("r4_lists", "bundles.{bundle}.p3_units_RD9"),
        "dg3_substituted": ("r4_lists", "bundles.H-8.dg3_replaced_excluded"),
        "rd10": ("r4_lists", "bundles.{bundle}.J11_RD10"),
        "c16_rows": ("x16", "rows"),
        "c16_bundles": ("x16", "bundles"),
        "c16_identity_stops": ("x16", "identity_stops"),
        "c9_premise": ("x16", "bundles.C-9.p18_premise.holds"),
        "c9_commands_same": ("x16", "bundles.C-9.controller_commands_same"),
        "rd13_lists": ("item_list", "lists"),
    },
    "path2": {
        "J-P3": ("merge", "RD-7.J-P3"),
        "J11": ("merge", "RD-7.J11"),
        "S-6": ("harness", "stop_S6_list.rows"),
        "bundle_markers": ("harness", "bundles.{bundle}.gates"),
        "G-5": ("u3", "U-3.G-5_list.rows"),
        "G-6": ("u3", "U-3.G-6_list.rows"),
        "pair_source": ("grid", "v0_pair.source"),
        "sample_jobs": ("grid", "v0_pair.sample.jobs"),
        "sample_same": ("grid", "v0_pair.sample.same"),
        "grid_raw": ("grid", "grid.a_pass_to_fail_raw"),
        "grid_n_raw": ("grid", "grid.N_raw"),
        "grid_excluded": ("grid", "grid.c_pass_to_fail_family_F_excluded"),
        "grid_n_f": ("grid", "grid.N_F"),
        "family_table": ("grid", "grid.b_family_F_table"),
        "application": ("grid", "grid.family_F_applicable"),
        "pass_to_pass": ("grid", "grid.grid_records.pass_to_pass"),
        "fail_to_pass": ("grid", "grid.grid_records.fail_to_pass"),
        "fail_to_fail": ("grid", "grid.grid_records.fail_to_fail"),
        "n_fault": ("grid", "grid.grid_records.N_fault"),
        "fault_rows": ("grid", "grid.grid_records.fault_rows"),
        "undecidable_rows": ("grid", "grid.grid_records.undecidable_rows"),
        "h10_marker": ("grid", "grid.supplement6_inputs.h10_marker"),
        "h10_term": ("grid", "grid.h10_grid_term.uses"),
        "h10_value": ("grid", "grid.h10_grid_term.value"),
        "family_k": ("grid", "grid.family_F_rule.k"),
        "family_R1": ("grid", "grid.family_F_rule.R1"),
        "family_R2": ("grid", "grid.family_F_rule.R2.ok"),
        "family_R3": ("grid", "grid.family_F_rule.R3.ok"),
        "family_R4": ("grid", "grid.family_F_rule.R4.ok"),
        "family_R3_violations": ("grid", "grid.family_F_rule.R3.violations"),
        "family_R4_violations": ("grid", "grid.family_F_rule.R4.violations"),
        "family_result": ("grid", "grid.family_F_rule.result"),
        "jp_rows_count": ("jp", "n_rows"),
        "jp_rows": ("jp", "rows"),
        "jp_stop_markers": ("jp", "stop_markers"),
        "jp_reuse": ("jp", "reuse"),
        "g3": ("g3", "G-3"),
        "g3_false_pairs": ("g3", "G-3_false_list.rows"),
        "rd8_record": ("harness", "bundles.{bundle}.r4.rd8"),
        "rd8_judged": ("merge", "RD-8.{bundle}"),
        "rd9": ("harness", "bundles.{bundle}.r4.rd9_p3_on"),
        "rd9_v5c": ("merge", "RD-9.{bundle}.p3_on"),
        "dg3_substituted": ("noise", "R4.H-8_dg3_substituted"),
        "rd10": ("merge", "RD-10.{bundle}"),
        "c16_rows": ("c16", "rows"),
        "c16_bundles": ("c16", "bundles"),
        "c16_stops": ("c16", "stops"),
        "c9_premise": ("c16", "C-9_P-18.premise"),
        "c9_commands_same": ("c16", "C-9_P-18.commands_equal"),
        "rd13_lists": ("items", "list_sha256"),
        "rd13_lists_v5c": ("merge", "RD-13_sha256"),
    },
    "baseline": {
        "jp_base": ("baseline", "jp_base"),
        "s6_base": ("baseline", "s6_base"),
    },
}
"""Where each compared value sits: (output file key, dotted key path inside that file)."""

COLUMN_MAP: dict[str, dict[str, str]] = {
    # Re-audit M-1 table: RD-7 3 row identity columns
    "path1": {"file": "result_file", "location": "location"},
    "path2_harness": {"file": "result_file", "location": "position"},
    "path2_v5c": {"file": "file", "location": "position"},
    "baseline": {"file": "file", "location": "location"},
    # Supplement 5-3 lists: path 2 v5c rows have no position, the row is (file, key, event, phase)
    "path1_grid": {"file": "result_file", "condition": "condition"},
    "path2_grid": {"file": "file", "condition": "applicable"},
    # RD-11 8 J_P row items
    "path1_jp": {
        "events": "events",
        "r4c30": "flat_soil_margin_applied",
        "soil_mode_start": "soil_mode_start",
        "shadow_lines": "shadow_lines",
        "cond1": "condition1_shadow_silent",
        "cond2": "condition2_k1_no_effect",
    },
    "path2_jp": {
        "events": "n_events",
        "r4c30": "n_r4c30",
        "soil_mode_start": "n_soil_mode_start",
        "shadow_lines": "n_shadow_lines",
        "cond1": "cond1",
        "cond2": "cond2",
    },
    # RD-7 1 G-3 false pair columns
    "path1_g3": {
        "field": "compare_field",
        "none_hash": "no_option_hash",
        "compare_hash": "target_hash",
        "none_lines": "no_option_lines",
        "compare_lines": "target_lines",
    },
    "path2_g3": {
        "field": "field",
        "none_hash": "none_hash",
        "compare_hash": "compare_hash",
        "none_lines": "none_lines",
        "compare_lines": "compare_lines",
    },
    # RD-8 counts of H-1 / H-3 / H-4 (recorded-state bundles)
    "path1_rd8_record": {
        "lines_with_breach_reads": "lines_with_breach_reads",
        "wrong_form": "wrong_form",
        "top_level_mismatch": "top_level_mismatch_RD7_3",
        "pass_without_breach_reads": "vb_pass_without_breach_reads",
    },
    "path2_rd8_record": {
        "lines_with_breach_reads": "lines_present",
        "wrong_form": "breach_reads_bad_format",
        "top_level_mismatch": "breach_reads_mismatch",
        "pass_without_breach_reads": "jp3_pass_without_breach_reads",
    },
    # RD-8 format undecidable J-P3 of H-6 / H-8 / H-9 / H-10
    "path1_rd8_judged": {"wrong_form": "RD-8"},
    "path2_rd8_judged": {"wrong_form": "format"},
    # RD-10 counts
    "path1_rd10": {"undecidable": "not_judgeable", "input_missing": "no_input"},
    "path2_rd10": {"undecidable": "undecidable", "input_missing": "input_missing"},
    # RD-9 H-8 dg3 substitution (path 1 counts per file, path 2 in one record)
    "path2_dg3_substituted": {
        "substituted": "p3_on",
        "rd9_without_substituted": "p3_on_judged_in_H-8",
    },
    # C-9 .. C-11 bundle record state
    "path1_c16_bundle": {"state": "state"},
    "path2_c16_bundle": {"state": "status"},
}
"""Canonical column -> source field; a column not listed keeps its name (bundle, leg, k, key)."""

UNDECIDED = "undecidable"
VALUE_WORDS: dict[str, dict[Any, Any]] = {
    "three_valued": {"판정 불가": UNDECIDED, "undecidable": UNDECIDED},
    "family_result": {
        "통과": "pass",
        "실패": "fail",
        "판정 불가": UNDECIDED,
        "pass": "pass",
        "fail": "fail",
        "undecidable": UNDECIDED,
    },
    "pair_source": {
        "저장 V0 격자": "stored",
        "V0 768(h9_grid_v0)": "v0_768",
        "판정 불가": UNDECIDED,
        "stored": "stored",
        "new": "v0_768",
        "undecidable": UNDECIDED,
    },
    "h10_term": {"N_raw": "N_raw", "N_F": "N_F", "none": "none", None: "none"},
    "h10_marker": {"멈춤 H-10": True, None: False, True: True, False: False},
}
"""Path words -> one canonical word (supplement 6-3: 판정 불가 is kept apart from true / false)."""

FAMILY_K_KEY_FORMS = {"path1": "setting|key", "path2": "key|setting"}
"""Key form of the family F ``k`` table of each path (the family keys themselves contain ``|``)."""
PATH1_VIOLATION_FIELDS = {
    "family_R3_violations": ("key", "offset_s", "fault_events", "final_phase"),
    "family_R4_violations": ("key", "offset_s", "gates"),
}
"""Path 1 violation row fields in the order of the path 2 list rows ([key, offset, ...])."""

RD8_MARKER = "J-P3 입력 형식(RD-8)"
RD8_BUNDLES = ("H-1", "H-3", "H-4")
JD2_KEYS = frozenset(
    {
        "H9|J1|B|top|roll_pos@k0.6",
        "g6r|rigid+S1@FL|top|Fs4",
        "g6r|rigid+S1@FR|top|Fs4",
        "slope|edge|top|4.0|RL|raised|20.0|proj",
        "slope|edgeMr|top|4.0|RR|raised|20.0|proj",
    }
)
"""Block JD-2: the R16-15 1 G-5 keys."""
JD7_KEYS = frozenset(
    {
        "slope|edge|top|4.0|FR|raised|20.0|proj",
        "slope|rpB|top|4.0|FR|raised|20.0|proj",
        "slope|edgeMr|top|4.0|FL|raised|20.0|proj",
    }
)
"""Block JD-7: the R16-9 g8 VB G-6 keys."""

GRID_ROW_ID = ("file", "key", "event", "offset_s")
GATE_LIST_COLUMNS = ("vb_false_gates", "v0_false_gates")
FAMILY_TABLE_CELLS = (
    "vb_pass",
    "v0_pass",
    "vb_false_gates",
    "v0_false_gates",
    "vb_pass_without_two",
    "v0_pass_without_two",
)
FAMILY_TABLE_VALUES = FAMILY_TABLE_CELLS + ("condition",)
JP_ROW_ID = ("batch", "case")
JP_ROW_VALUES = (
    "run_id",
    "events_unreadable",
    "events",
    "r4c30",
    "soil_mode_start",
    "shadow_lines",
    "shadow_unreadable",
    "cond1",
    "cond2",
)
G3_ROW_ID = ("script", "key")
G3_ROW_VALUES = ("field", "none_hash", "compare_hash", "none_lines", "compare_lines")

RD8_JUDGED_BUNDLES = ("H-6", "H-8", "H-9", "H-10")
"""RD-7 1 J-P3 list bundles: their RD-8 format undecidable count (path 2 v5c merge)."""
RD9_BUNDLES = ("H-1", "H-3", "H-4", "H-5", "H-6", "H-7", "H-8", "H-9", "H-10")
RD9_V5C_BUNDLES = ("H-6", "H-8", "H-9", "H-10")
"""Path 2 gives RD-9 twice: harness (every bundle) and the v5c merge (its four bundles)."""
RD10_BUNDLES = ("H-6", "H-8", "H-9", "H-10")
C16_BUNDLES = ("C-9", "C-10", "C-11")
C16_IDENTITY_STOPS = ("S-12", "S-4")

C16_ITEMS: tuple[tuple[str, str, str, str, str, str], ...] = (
    # (bundle or "all", item, path 1 key path, path 1 transform, path 2 key path, path 2 transform)
    ("all", "rc", "items.rc", "", "items.rc", ""),
    ("all", "last_sample_s", "items.last_sample_s", "", "items.last_sample_t_s", ""),
    ("all", "first_ready_s", "items.first_ready_s", "", "items.first_ready_s", ""),
    ("C-9", "decisions", "items.decisions", "", "items.decisions", ""),
    ("C-9", "soil_mode_start_s", "items.soil_mode_start_s", "", "items.soil_mode_start_t_s", ""),
    ("C-9", "loc_s", "items.loc_s", "", "items.loc_t_s", ""),
    (
        "C-9",
        "controller_commands_sha256",
        "items.controller_commands_sha256",
        "",
        "items.controller_commands_sha256",
        "",
    ),
    ("C-9", "max_stroke_mm", "items.max_stroke_mm", "", "items.max_stroke_mm", ""),
    ("C-9", "end_rut_gap_mm", "items.end_rut_gap_mm", "", "items.end_rut_gap_mm", ""),
    ("C-9", "P3", "items.P3", "", "items.P3", "p3_by_item"),
    ("C-10", "t_D_s", "items.t_D_s", "", "items.force.t_departure_s", ""),
    (
        "C-10",
        "F_below_F_min_ms",
        "items.F_below_F_min_ms",
        "",
        "items.force.legs",
        "legs_below_F_min_ms",
    ),
    (
        "C-10",
        "F_below_F_min_plus_2kN_ms",
        "items.F_below_F_min_plus_2kN_ms",
        "",
        "items.force.legs",
        "legs_below_F_min_plus_2kN_ms",
    ),
    ("C-10", "F_min_after_N", "items.F_min_after_N", "", "items.force.legs", "legs_F_min_after_N"),
    ("C-10", "t_min_after_s", "items.t_min_after_s", "", "items.force.legs", "legs_t_min_after_s"),
    (
        "C-10",
        "F_min_transient_N",
        "items.F_min_transient_N",
        "",
        "items.force.legs",
        "legs_F_min_transient_N",
    ),
    ("C-10", "G6", "items.G6", "g6_values", "items.G6", "g6_words"),
    ("C-10", "P3-3_within", "items.P3-3_within", "", "items.P3-3", ""),
    ("C-10", "end_phase", "items.end_phase", "", "items.end_phase", ""),
    ("C-10", "max_stroke_mm", "items.max_stroke_mm", "", "items.max_stroke_mm", ""),
    ("C-10", "patch_leg", "items.patch_leg", "", "items.patch_leg", ""),
    (
        "C-10",
        "patch_leg_sinkage_end_mm",
        "items.patch_leg_sinkage_end_mm",
        "",
        "items.patch_leg_sinkage_mm",
        "",
    ),
    ("C-11", "first_loc_s", "items.first_loc_s", "", "items.loc_first_t_s", ""),
    ("C-11", "final_loc_s", "items.final_loc_s", "", "items.loc_final_t_s", ""),
    ("C-11", "loc_cancels", "items.loc_cancels", "", "items.loc_revokes", ""),
    (
        "C-11",
        "loc_period_crawler_max_N",
        "items.loc_period_crawler_max_N",
        "",
        "items.loc_period_crawler_max_N",
        "",
    ),
    (
        "C-11",
        "loc_period_crawler_max_over_W",
        "items.loc_period_crawler_max_over_W",
        "",
        "items.loc_period_crawler_max_over_W",
        "",
    ),
    ("C-11", "loc_period_ge_0p01W", "items.loc_period_ge_0p01W", "", "items.above_0p01W", ""),
    (
        "C-11",
        "final_loc_period",
        "items",
        "final_period_from_flat",
        "items.final_loc_period",
        "final_period_from_dict",
    ),
)
"""R16-11 record items both paths give per row (keys read from x16-records / p2_x16 c16 code).
A missing value is None (a row may legitimately lack it); the row folder itself must be there."""
C16_EXCLUDED_KEYS = (
    "problems",
    "why",
    "note",
    "times_note",
    "G6_rule",
    "G6_source",
    "rc_source",
    "files",
    "files_sha256",
    "folder",
    "identity (detail)",
    "duration_expected_s",
    "window",
    "dt_s",
    "file_sha256",
    "out_root",
    "identity_dir",
)
"""RD-5 / CD-10: free-text reasons, file paths and input sha blocks are not compared."""
P3_CHECK_KEYS = {
    "P3-1": "P3-1_crawler_zero_after_ready",
    "P3-2": "P3-2_within",
    "P3-3": "P3-3_within",
    "P3-4": "P3-4_within_0p2",
    "P3-5": "P3-5_within",
    "P3-6": "P3-6_within",
    "P3-7": "P3-7_within",
    "P3-8": "P3-8_within",
    "P3-9": "P3-9_flags",
}
"""Path 1 names its C-9 P3 values P3-n; path 2 keeps the ``p3b.checks`` key names."""
G6_PATH2_WORDS = {True: "pass", False: "fail", "미달": "fail", None: "not_judgeable"}
"""Path 2 G6 values in the path 1 words (``pass`` / ``fail`` / ``not_judgeable``); a 해당 없음
text stays as written in both paths."""


@dataclass(frozen=True)
class ListSpec:
    """One RD-7 list: its identity and value columns and the path 2 column-name source."""

    name: str
    path2_source: str
    id_columns: tuple[str, ...]
    value_columns: tuple[str, ...]
    must_not_be_empty: bool


RD7_LISTS = (
    ListSpec(
        "J-P3",
        "path2_v5c",
        ("bundle", "file", "location", "leg"),
        ("key", "setting", "breach_reads", "min_gap_bar", "first_breach_t_s"),
        True,
    ),
    ListSpec(
        "J11",
        "path2_v5c",
        ("bundle", "file", "location", "leg"),
        ("key", "setting", "n_late_fallback_by_leg", "marker"),
        False,
    ),
    ListSpec(
        "S-6",
        "path2_harness",
        ("bundle", "file", "location", "k"),
        ("key", "setting", "family", "t_loc_s", "n_P", "n_S", "dP"),
        True,
    ),
)
"""RD-7 3: J-P3 and J11 rows are (bundle, file, location, leg), S-6 rows add k instead of the leg.
JD-1 / JD-3 make the J-P3 (5) and S-6 (67) lists non-empty by definition."""
G_LISTS = (
    ListSpec("G-5", "path2_harness", ("bundle", "file", "location"), ("key",), True),
    ListSpec("G-6", "path2_harness", ("bundle", "file", "location"), ("key",), True),
)


class InputError(Exception):
    """A missing file or key, or an empty list that must not be empty (exit 2)."""


@dataclass
class ItemResult:
    """The outcome of one compared item: ``equal``, ``differ`` or ``missing`` (input error)."""

    item: str
    status: str
    detail: dict[str, Any] = field(default_factory=dict)


# ----------------------------------------------------------------------------- value helpers
def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def values_equal(first: Any, second: Any) -> bool:
    """RD-5 K-10: exact for booleans, strings and None, tolerant for numbers, element-wise for
    lists and dicts (a bool never equals a number)."""
    if isinstance(first, bool) or isinstance(second, bool):
        return first is second
    if is_number(first) and is_number(second):
        if not (math.isfinite(first) and math.isfinite(second)):
            return first == second
        scale = max(1.0, abs(first), abs(second))
        return abs(first - second) <= RELATIVE_TOLERANCE * scale
    if isinstance(first, list) and isinstance(second, list):
        return len(first) == len(second) and all(map(values_equal, first, second))
    if isinstance(first, dict) and isinstance(second, dict):
        return first.keys() == second.keys() and all(
            values_equal(first[key], second[key]) for key in first
        )
    return first == second


def hashable(value: Any) -> Any:
    """A set-friendly form of an identity value (lists become tuples, numbers floats)."""
    if isinstance(value, list):
        return tuple(hashable(element) for element in value)
    if is_number(value):
        return float(value)
    return value


def dig(document: Any, dotted: str) -> Any:
    """The value at a dotted key path; InputError when a key on the way is missing."""
    node = document
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            raise InputError(f"key {dotted!r} missing (stopped at {part!r})")
        node = node[part]
    return node


def word(kind: str, value: Any) -> Any:
    """The canonical word of a path word (VALUE_WORDS); unknown words stay as they are."""
    words = VALUE_WORDS[kind]
    try:
        return words.get(value, value)
    except TypeError:  # an unhashable value is not a word
        return value


# ---------------------------------------------------------------------------- input reading
class Inputs:
    """The two output folders and the baseline file; each JSON file is read once."""

    def __init__(self, path1_dir: Path, path2_dir: Path, baseline: Path) -> None:
        self.paths = {
            "path1": {name: path1_dir / file_name for name, file_name in PATH1_FILES.items()},
            "path2": {name: path2_dir / file_name for name, file_name in PATH2_FILES.items()},
            "baseline": {"baseline": baseline},
        }
        self._documents: dict[tuple[str, str], Any] = {}

    def sha_records(self) -> list[dict[str, Any]]:
        records = []
        for side, files in self.paths.items():
            for name, path in files.items():
                sha = file_sha256(path) if path.is_file() else None
                records.append({"side": side, "name": name, "path": str(path), "sha256": sha})
        return records

    def document(self, side: str, name: str) -> Any:
        if (side, name) not in self._documents:
            self._documents[(side, name)] = self._read(side, name)
        return self._documents[(side, name)]

    def _read(self, side: str, name: str) -> Any:
        path = self.paths[side][name]
        if not path.is_file():
            raise InputError(f"{side}: expected output file {path.name} missing in {path.parent}")
        if side == "baseline" and file_sha256(path) != BASELINE_SHA256:
            raise InputError(f"baseline sha256 {file_sha256(path)} is not {BASELINE_SHA256}")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise InputError(f"{side}: {path.name} is not UTF-8 JSON ({error})") from error

    def pick(self, side: str, field_name: str, *, bundle: str = "", required: bool = True) -> Any:
        """A value by its FIELD_SOURCES entry; a missing optional key is None."""
        file_name, dotted = FIELD_SOURCES[side][field_name]
        document = self.document(side, file_name)
        try:
            return dig(document, dotted.format(bundle=bundle))
        except InputError:
            if required:
                raise
            return None


# ------------------------------------------------------------------------------ row helpers
def require_list(value: Any, label: str) -> list:
    if not isinstance(value, list):
        raise InputError(f"{label}: not a list")
    return value


def flatten_rows(value: Any, label: str) -> list[dict]:
    """A list of rows, or the rows of a bundle -> rows dict (path 2 merge output)."""
    if isinstance(value, dict):
        per_bundle = [require_list(rows, f"{label} {bundle}") for bundle, rows in value.items()]
        value = [row for rows in per_bundle for row in rows]
    if not all(isinstance(row, dict) for row in require_list(value, label)):
        raise InputError(f"{label}: not a list of row objects")
    return value


def as_float(value: Any) -> Any:
    return float(value) if is_number(value) else value


def canonical_row(
    row: dict, source: str, columns: tuple[str, ...], *, missing_as_none: bool = False
) -> dict[str, Any]:
    """The row under canonical column names (COLUMN_MAP); a missing column is an input error
    unless ``missing_as_none``."""
    names = COLUMN_MAP.get(source, {})
    out = {}
    for column in columns:
        field_name = names.get(column, column)
        if field_name not in row and not missing_as_none:
            raise InputError(f"{source} row without column {field_name!r}")
        out[column] = row.get(field_name)
    return out


def canonical_rows(
    rows: list[dict], source: str, columns: tuple[str, ...], **options: Any
) -> list[dict[str, Any]]:
    return [canonical_row(row, source, columns, **options) for row in rows]


def identity(row: dict[str, Any], id_columns: tuple[str, ...]) -> tuple:
    return tuple(hashable(row[column]) for column in id_columns)


def identity_counter(rows: list[dict], id_columns: tuple[str, ...]) -> Counter:
    return Counter(identity(row, id_columns) for row in rows)


def compare_row_lists(
    rows1: list[dict],
    rows2: list[dict],
    id_columns: tuple[str, ...],
    value_columns: tuple[str, ...],
) -> dict[str, list]:
    """Rows of one path only, duplicated identities and value differences of shared rows."""
    count1, count2 = identity_counter(rows1, id_columns), identity_counter(rows2, id_columns)
    first1 = {identity(row, id_columns): row for row in reversed(rows1)}
    first2 = {identity(row, id_columns): row for row in reversed(rows2)}
    value_differences = []
    for key in sorted(set(first1) & set(first2), key=repr):
        for column in value_columns:
            if not values_equal(first1[key][column], first2[key][column]):
                value_differences.append(
                    {
                        "row": list(key),
                        "column": column,
                        "path1": first1[key][column],
                        "path2": first2[key][column],
                    }
                )
    return {
        "only_path1": [list(key) for key in sorted(set(count1) - set(count2), key=repr)],
        "only_path2": [list(key) for key in sorted(set(count2) - set(count1), key=repr)],
        "duplicates": [
            {"row": list(key), "path1": count1[key], "path2": count2[key]}
            for key in sorted(set(count1) | set(count2), key=repr)
            if count1[key] > 1 or count2[key] > 1
        ],
        "value_differences": value_differences,
    }


def has_difference(comparison: dict[str, list]) -> bool:
    return any(comparison.values())


def require_rows(rows: list, label: str) -> None:
    if not rows:
        raise InputError(f"{label}: empty list (must not be empty, re-audit M-1 3)")


def result(item: str, is_equal: bool, detail: dict[str, Any]) -> ItemResult:
    return ItemResult(item, "equal" if is_equal else "differ", detail)


# --------------------------------------------------------------------- RD-7 and JD items
def rd7_rows(inputs: Inputs, side: str, spec: ListSpec) -> list[dict[str, Any]]:
    source = "path1" if side == "path1" else spec.path2_source
    rows = flatten_rows(inputs.pick(side, spec.name), f"{side} {spec.name}")
    if spec.must_not_be_empty:
        require_rows(rows, f"{side} {spec.name}")
    return canonical_rows(rows, source, spec.id_columns + spec.value_columns)


def item_rd7_list(inputs: Inputs, spec: ListSpec) -> ItemResult:
    """RD-7 2: one list, the same rows and values in both paths."""
    rows1, rows2 = rd7_rows(inputs, "path1", spec), rd7_rows(inputs, "path2", spec)
    comparison = compare_row_lists(rows1, rows2, spec.id_columns, spec.value_columns)
    detail = {"rows_path1": len(rows1), "rows_path2": len(rows2), **comparison}
    return result(f"RD-7 {spec.name} list (RD-7 2)", not has_difference(comparison), detail)


def baseline_identities(inputs: Inputs, name: str, id_columns: tuple[str, ...]) -> set[tuple]:
    rows = flatten_rows(inputs.pick("baseline", name), f"baseline {name}")
    require_rows(rows, f"baseline {name}")
    return set(identity_counter(canonical_rows(rows, "baseline", id_columns), id_columns))


def against_baseline(path_ids: set[tuple], base_ids: set[tuple]) -> dict[str, Any]:
    return {
        "equal": path_ids == base_ids,
        "only_path": [list(key) for key in sorted(path_ids - base_ids, key=repr)],
        "only_baseline": [list(key) for key in sorted(base_ids - path_ids, key=repr)],
    }


def item_baseline(
    inputs: Inputs, item: str, spec: ListSpec, base_name: str, id_columns: tuple[str, ...]
) -> ItemResult:
    """JD-1 / JD-3: each path's list, reduced to ``id_columns``, equals the baseline set."""
    base_ids = baseline_identities(inputs, base_name, id_columns)
    detail: dict[str, Any] = {"baseline_rows": len(base_ids)}
    for side in ("path1", "path2"):
        rows = rd7_rows(inputs, side, spec)
        detail[side] = against_baseline(set(identity_counter(rows, id_columns)), base_ids)
    return result(item, detail["path1"]["equal"] and detail["path2"]["equal"], detail)


def item_g_list(
    inputs: Inputs, spec: ListSpec, expected_keys: frozenset[str], item: str
) -> ItemResult:
    """JD-2 / JD-7: the two G lists agree (RD-7 2) and their key set is the block's set."""
    rows1, rows2 = rd7_rows(inputs, "path1", spec), rd7_rows(inputs, "path2", spec)
    comparison = compare_row_lists(rows1, rows2, spec.id_columns, spec.value_columns)
    keys = {
        side: {row["key"] for row in rows} for side, rows in (("path1", rows1), ("path2", rows2))
    }
    key_checks = {
        side: {
            "equal": side_keys == expected_keys,
            "only_path": sorted(map(str, side_keys - expected_keys)),
            "only_block": sorted(expected_keys - side_keys),
        }
        for side, side_keys in keys.items()
    }
    is_equal = not has_difference(comparison) and all(
        check["equal"] for check in key_checks.values()
    )
    return result(item, is_equal, {**comparison, "key_sets": key_checks})


def item_jd8(inputs: Inputs) -> ItemResult:
    """JD-8: the RD-8 marker of H-1 / H-3 / H-4 is present in both paths or in neither."""
    presence = {}
    for bundle in RD8_BUNDLES:
        markers = {
            side: inputs.pick(side, "bundle_markers", bundle=bundle) for side in ("path1", "path2")
        }
        if not all(isinstance(value, list) for value in markers.values()):
            raise InputError(f"{bundle}: marker / gate list is not a list")
        presence[bundle] = {side: RD8_MARKER in value for side, value in markers.items()}
    is_equal = all(value["path1"] == value["path2"] for value in presence.values())
    return result("JD-8 RD-8 marker H-1 / H-3 / H-4", is_equal, {"presence": presence})


# ------------------------------------------------------------------ supplements 5 and 6
def pair_sources(inputs: Inputs) -> dict[str, Any]:
    return {
        side: word("pair_source", inputs.pick(side, "pair_source")) for side in ("path1", "path2")
    }


def lists_not_produced(inputs: Inputs) -> str | None:
    """Why the supplement 5 lists cannot be compared (None when they can)."""
    sources = pair_sources(inputs)
    if sources["path1"] == sources["path2"] == UNDECIDED:
        return "pair source undecidable in both paths: no lists (supplement 6-2)"
    if sources["path1"] != sources["path2"]:
        return "pair sources differ: lists not compared (see the pair source item)"
    return None


def item_pair_source(inputs: Inputs) -> ItemResult:
    """Supplement 6-2: the V0 pair source and the sample job counts."""
    detail = {"pair_source": pair_sources(inputs)}
    for name in ("sample_jobs", "sample_same"):
        detail[name] = {
            side: inputs.pick(side, name, required=False) for side in ("path1", "path2")
        }
    is_equal = all(values_equal(value["path1"], value["path2"]) for value in detail.values())
    return result("S6-2 V0 pair source", is_equal, detail)


def grid_rows(
    inputs: Inputs, side: str, field_name: str, value_columns: tuple[str, ...]
) -> list[dict[str, Any]]:
    source = "path1_grid" if side == "path1" else "path2_grid"
    rows = flatten_rows(inputs.pick(side, field_name), f"{side} {field_name}")
    return canonical_rows(rows, source, GRID_ROW_ID + value_columns)


def skipped_unless_comparable(inputs: Inputs, item: str) -> ItemResult | None:
    reason = lists_not_produced(inputs)
    if reason is None:
        return None
    is_equal = reason.startswith("pair source undecidable in both")
    return result(item, is_equal, {"not_compared": reason})


def item_grid_list(inputs: Inputs, item: str, list_field: str, count_field: str) -> ItemResult:
    """Supplement 5-3 (a) / (c): the pass -> fail list (file, key, event, phase, false gates)
    and its count N_raw / N_F."""
    skipped = skipped_unless_comparable(inputs, item)
    if skipped:
        return skipped
    rows = {
        side: grid_rows(inputs, side, list_field, GATE_LIST_COLUMNS) for side in ("path1", "path2")
    }
    counts = {side: inputs.pick(side, count_field) for side in ("path1", "path2")}
    comparison = compare_row_lists(rows["path1"], rows["path2"], GRID_ROW_ID, GATE_LIST_COLUMNS)
    is_equal = not has_difference(comparison) and values_equal(counts["path1"], counts["path2"])
    return result(item, is_equal, {"counts": counts, **comparison})


def family_table_rows(inputs: Inputs, side: str) -> list[dict[str, Any]]:
    rows = grid_rows(inputs, side, "family_table", FAMILY_TABLE_VALUES)
    for row in rows:
        row["condition"] = word("three_valued", row["condition"])
    return rows


def blank_undecided_cells(rows1: list[dict], rows2: list[dict]) -> None:
    """A row 판정 불가 in both paths is compared by its condition only (the paths write the
    other cells of such a row differently)."""
    index2 = {identity(row, GRID_ROW_ID): row for row in rows2}
    for row1 in rows1:
        row2 = index2.get(identity(row1, GRID_ROW_ID))
        if row2 is None or not row1["condition"] == row2["condition"] == UNDECIDED:
            continue
        for column in FAMILY_TABLE_CELLS:
            row1[column] = row2[column] = None


def item_family_table(inputs: Inputs) -> ItemResult:
    """Supplement 5-3 (b) with 6-3: the 12 family F rows and the three-valued application
    condition."""
    item = "S5-3 (b) family F table and application condition"
    applications = {
        side: word("three_valued", inputs.pick(side, "application")) for side in ("path1", "path2")
    }
    skipped = skipped_unless_comparable(inputs, item)
    if skipped:
        skipped.detail["application"] = applications
        return skipped
    rows1, rows2 = family_table_rows(inputs, "path1"), family_table_rows(inputs, "path2")
    blank_undecided_cells(rows1, rows2)
    comparison = compare_row_lists(rows1, rows2, GRID_ROW_ID, FAMILY_TABLE_VALUES)
    is_equal = not has_difference(comparison) and values_equal(
        applications["path1"], applications["path2"]
    )
    detail = {
        "application": applications,
        "rows_path1": len(rows1),
        "rows_path2": len(rows2),
        **comparison,
    }
    return result(item, is_equal, detail)


def row_identities(inputs: Inputs, side: str, field_name: str) -> list[list]:
    rows = grid_rows(inputs, side, field_name, ())
    return [list(key) for key in sorted(set(identity_counter(rows, GRID_ROW_ID)), key=repr)]


def item_grid_records(inputs: Inputs) -> ItemResult:
    """Supplement 5-3 records: transition counts, FAULT rows, 판정 불가 rows (by row identity)."""
    item = "S5-3 records (fail->pass, fail->fail, FAULT, undecidable rows)"
    skipped = skipped_unless_comparable(inputs, item)
    if skipped:
        return skipped
    detail: dict[str, Any] = {}
    for name in ("pass_to_pass", "fail_to_pass", "fail_to_fail", "n_fault"):
        detail[name] = {side: inputs.pick(side, name) for side in ("path1", "path2")}
    for name in ("fault_rows", "undecidable_rows"):
        detail[name] = {side: row_identities(inputs, side, name) for side in ("path1", "path2")}
    is_equal = all(values_equal(value["path1"], value["path2"]) for value in detail.values())
    return result(item, is_equal, detail)


def item_h10(inputs: Inputs) -> ItemResult:
    """Supplements 5-4 / 6-4: the "stop H-10" marker and the count used as the H-10 grid term."""
    detail = {
        "h10_marker": {
            side: word("h10_marker", inputs.pick(side, "h10_marker")) for side in ("path1", "path2")
        },
        "h10_term": {
            side: word("h10_term", inputs.pick(side, "h10_term")) for side in ("path1", "path2")
        },
        "h10_value": {side: inputs.pick(side, "h10_value") for side in ("path1", "path2")},
    }
    is_equal = all(values_equal(value["path1"], value["path2"]) for value in detail.values())
    return result("S5-4 / S6-4 stop H-10 marker and grid term", is_equal, detail)


# ------------------------------------------------------------------------- family F rules
def family_k(inputs: Inputs, side: str) -> dict[str, Any]:
    """``k`` as ``<key>|<setting>`` -> count for both paths (FAMILY_K_KEY_FORMS)."""
    table = inputs.pick(side, "family_k")
    if not isinstance(table, dict):
        raise InputError(f"{side} family k is not an object")
    out = {}
    for text, count in table.items():
        if FAMILY_K_KEY_FORMS[side] == "setting|key":
            setting, _, key = text.partition("|")
        else:
            key, _, setting = text.rpartition("|")
        out[f"{key}|{setting}"] = count
    return out


def row_values(row: Any, names: tuple[str, ...], label: str) -> list:
    if not isinstance(row, dict) or any(name not in row for name in names):
        raise InputError(f"{label}: row without one of {names}")
    return [row[name] for name in names]


def violation_tuples(inputs: Inputs, side: str, name: str) -> list[list]:
    """R-3 / R-4 violations as [key, offset, ...] lists in the path 2 shape."""
    label = f"{side} {name}"
    rows = require_list(inputs.pick(side, name), label)
    if side == "path2":
        shaped = [list(require_list(row, label)) for row in rows]
    else:
        shaped = [row_values(row, PATH1_VIOLATION_FIELDS[name], label) for row in rows]
    for row in shaped:  # the offset as a float so both paths sort alike
        row[1] = as_float(row[1])
    return sorted(shaped, key=repr)


def family_view(inputs: Inputs, side: str) -> dict[str, Any]:
    view = {"result": word("family_result", inputs.pick(side, "family_result"))}
    if view["result"] == UNDECIDED:
        return view
    view["k"] = family_k(inputs, side)
    for name in ("family_R1", "family_R2", "family_R3", "family_R4"):
        view[name] = inputs.pick(side, name)
    for name in ("family_R3_violations", "family_R4_violations"):
        view[name] = violation_tuples(inputs, side, name)
    return view


def item_family_rules(inputs: Inputs) -> ItemResult:
    """Supplement 4-5: family F R-1 .. R-4 (k, four conditions, violation lists, result). When
    both results are 판정 불가 only the result is compared."""
    views = {side: family_view(inputs, side) for side in ("path1", "path2")}
    differences = {
        name: {"path1": views["path1"].get(name), "path2": views["path2"].get(name)}
        for name in sorted(set(views["path1"]) | set(views["path2"]))
        if not values_equal(views["path1"].get(name), views["path2"].get(name))
    }
    return result(
        "S4-5 family F R-1 .. R-4",
        not differences,
        {
            "result": {side: view["result"] for side, view in views.items()},
            "differences": differences,
        },
    )


# --------------------------------------------------------------------------- RD-11, G-3
def item_jp(inputs: Inputs) -> ItemResult:
    """RD-11 8: the J_P row items, row count, stop markers and the reuse value."""
    rows = {}
    for side in ("path1", "path2"):
        raw = flatten_rows(inputs.pick(side, "jp_rows"), f"{side} jp rows")
        id_rows = canonical_rows(raw, f"{side}_jp", JP_ROW_ID)
        value_rows = canonical_rows(raw, f"{side}_jp", JP_ROW_VALUES, missing_as_none=True)
        rows[side] = [{**ids, **values} for ids, values in zip(id_rows, value_rows, strict=True)]
    comparison = compare_row_lists(rows["path1"], rows["path2"], JP_ROW_ID, JP_ROW_VALUES)
    scalars = {
        "rows_count": {side: inputs.pick(side, "jp_rows_count") for side in ("path1", "path2")},
        "stop_markers": {
            side: sorted(
                require_list(inputs.pick(side, "jp_stop_markers"), f"{side} jp stop markers")
            )
            for side in ("path1", "path2")
        },
        "reuse": {
            side: inputs.pick(side, "jp_reuse", required=False) for side in ("path1", "path2")
        },
    }
    is_equal = not has_difference(comparison) and all(
        values_equal(value["path1"], value["path2"]) for value in scalars.values()
    )
    return result("RD-11 J_P reading", is_equal, {**scalars, **comparison})


def item_g3(inputs: Inputs) -> ItemResult:
    """H-11 (RD-7 1 G-3): the truth value and the false pair list."""
    truth = {side: inputs.pick(side, "g3") for side in ("path1", "path2")}
    rows = {
        side: canonical_rows(
            flatten_rows(inputs.pick(side, "g3_false_pairs"), side),
            f"{side}_g3",
            G3_ROW_ID + G3_ROW_VALUES,
        )
        for side in ("path1", "path2")
    }
    comparison = compare_row_lists(rows["path1"], rows["path2"], G3_ROW_ID, G3_ROW_VALUES)
    is_equal = values_equal(truth["path1"], truth["path2"]) and not has_difference(comparison)
    return result("H-11 G-3 and false pairs", is_equal, {"G-3": truth, **comparison})


# ------------------------------------------------------------------------ RD-8, RD-9, RD-10
def count_record(
    inputs: Inputs, side: str, field_name: str, bundle: str, columns: tuple[str, ...]
) -> dict[str, Any]:
    """One count record under canonical names (COLUMN_MAP entry ``<side>_<field_name>``)."""
    record = inputs.pick(side, field_name, bundle=bundle)
    if not isinstance(record, dict):
        raise InputError(f"{side} {field_name} of {bundle} is not an object")
    return canonical_row(record, f"{side}_{field_name}", columns)


def compare_per_bundle(values: dict[str, dict[str, Any]]) -> tuple[bool, dict[str, Any]]:
    """values[bundle][side] -> (all sides equal in every bundle, detail)."""
    is_equal = True
    for per_side in values.values():
        first, *others = per_side.values()
        is_equal &= all(values_equal(first, other) for other in others)
    return is_equal, values


def item_rd8(inputs: Inputs) -> ItemResult:
    """RD-8: the H-1 / H-3 / H-4 counts with their marker, and the format undecidable J-P3 count
    of the J-P3 list bundles."""
    columns = (
        "lines_with_breach_reads",
        "wrong_form",
        "top_level_mismatch",
        "pass_without_breach_reads",
    )
    values: dict[str, dict[str, Any]] = {}
    for bundle in RD8_BUNDLES:
        values[bundle] = {}
        for side in ("path1", "path2"):
            counts = count_record(inputs, side, "rd8_record", bundle, columns)
            markers = require_list(inputs.pick(side, "bundle_markers", bundle=bundle), bundle)
            values[bundle][side] = {**counts, "marker": RD8_MARKER in markers}
    for bundle in RD8_JUDGED_BUNDLES:
        values[bundle] = {
            side: count_record(inputs, side, "rd8_judged", bundle, ("wrong_form",))
            for side in ("path1", "path2")
        }
    is_equal, detail = compare_per_bundle(values)
    return result("RD-8 undecidable counts and marker", is_equal, detail)


def dg3_substitution(inputs: Inputs, side: str) -> dict[str, Any]:
    """H-8 ③ lines judged as H-6 lines (supplement 2-1 / 3-1) and the RD-9 count without them."""
    if side == "path2":
        columns = ("substituted", "rd9_without_substituted")
        return count_record(inputs, "path2", "dg3_substituted", "H-8", columns)
    per_file = inputs.pick("path1", "dg3_substituted")
    if not isinstance(per_file, dict):
        raise InputError("path1 bundles.H-8.dg3_replaced_excluded is not an object")
    rd9 = inputs.pick("path1", "rd9", bundle="H-8")
    if not all(is_number(value) for value in [rd9, *per_file.values()]):
        raise InputError("path1 H-8 RD-9 / dg3 counts are not numbers")
    substituted = sum(per_file.values())
    return {"substituted": substituted, "rd9_without_substituted": rd9 - substituted}


def item_rd9(inputs: Inputs) -> ItemResult:
    """RD-9: ③-on line / run counts per bundle (path 2 twice: harness and v5c merge) and the
    H-8 dg3 substitution."""
    values: dict[str, dict[str, Any]] = {}
    for bundle in RD9_BUNDLES:
        values[bundle] = {
            side: inputs.pick(side, "rd9", bundle=bundle) for side in ("path1", "path2")
        }
        if bundle in RD9_V5C_BUNDLES:
            values[bundle]["path2_v5c"] = inputs.pick("path2", "rd9_v5c", bundle=bundle)
    values["H-8 dg3 substitution"] = {
        side: dg3_substitution(inputs, side) for side in ("path1", "path2")
    }
    is_equal, detail = compare_per_bundle(values)
    return result("RD-9 ③-on counts and H-8 dg3 substitution", is_equal, detail)


def item_rd10(inputs: Inputs) -> ItemResult:
    """RD-10: J11 undecidable and input-missing counts of the J11 bundles."""
    values = {
        bundle: {
            side: count_record(inputs, side, "rd10", bundle, ("undecidable", "input_missing"))
            for side in ("path1", "path2")
        }
        for bundle in RD10_BUNDLES
    }
    is_equal, detail = compare_per_bundle(values)
    return result("RD-10 J11 undecidable / input missing", is_equal, detail)


# --------------------------------------------------------------------------- C-9 .. C-11
def dig_or_none(document: Any, dotted: str) -> Any:
    try:
        return dig(document, dotted)
    except InputError:
        return None


def legs_field(name: str, scale: float = 1.0) -> Callable[[Any], Any]:
    """Path 2 per-leg dicts (``force.legs``) -> the per-leg list of one field, scaled."""

    def transform(legs: Any) -> Any:
        if not isinstance(legs, list):
            return None
        values = [leg.get(name) if isinstance(leg, dict) else None for leg in legs]
        return [value * scale if is_number(value) else value for value in values]

    return transform


def p3_by_item(checks: Any) -> Any:
    if not isinstance(checks, dict):
        return checks
    return {item: checks.get(key) for item, key in P3_CHECK_KEYS.items()}


def g6_values(gates: Any) -> Any:
    """Path 1 G6 entries {"P3", "value"} -> value."""
    if not isinstance(gates, dict):
        return gates
    return {
        gate: entry.get("value") if isinstance(entry, dict) else entry
        for gate, entry in gates.items()
    }


def g6_words(gates: Any) -> Any:
    if not isinstance(gates, dict):
        return gates
    return {
        gate: G6_PATH2_WORDS.get(value, value) if not isinstance(value, (dict, list)) else value
        for gate, value in gates.items()
    }


def final_period_from_flat(items: Any) -> Any:
    """Path 1 keeps the final-LOC values flat; None when the final LOC is the first LOC."""
    if not isinstance(items, dict) or not items.get("final_loc_differs"):
        return None
    return {
        "crawler_max_N": items.get("final_loc_period_crawler_max_N"),
        "crawler_max_over_W": items.get("final_loc_period_crawler_max_over_W"),
        "above_0p01W": items.get("final_loc_period_ge_0p01W"),
    }


def final_period_from_dict(period: Any) -> Any:
    if not isinstance(period, dict):
        return None
    return {
        name: period.get(name) for name in ("crawler_max_N", "crawler_max_over_W", "above_0p01W")
    }


C16_TRANSFORMS: dict[str, Callable[[Any], Any]] = {
    "": lambda value: value,
    "p3_by_item": p3_by_item,
    "g6_values": g6_values,
    "g6_words": g6_words,
    "legs_below_F_min_ms": legs_field("t_below_F_min_s", 1000.0),
    "legs_below_F_min_plus_2kN_ms": legs_field("t_below_F_min_plus_2kN_s", 1000.0),
    "legs_F_min_after_N": legs_field("F_min_after_N"),
    "legs_t_min_after_s": legs_field("t_min_after_s"),
    "legs_F_min_transient_N": legs_field("F_min_transient_N"),
    "final_period_from_flat": final_period_from_flat,
    "final_period_from_dict": final_period_from_dict,
}


def c16_rows(inputs: Inputs, side: str) -> dict[str, dict]:
    rows = inputs.pick(side, "c16_rows")
    if not isinstance(rows, dict) or not rows:
        raise InputError(f"{side} C-9 .. C-11 rows missing or empty")
    if not all(isinstance(row, dict) and "bundle" in row for row in rows.values()):
        raise InputError(f"{side} C-9 .. C-11 row without bundle")
    return rows


def c16_row_items(row: dict, side: str) -> dict[str, Any]:
    """The canonical record items of one row (C16_ITEMS, transforms applied)."""
    values = {}
    for scope, item, path1_key, path1_transform, path2_key, path2_transform in C16_ITEMS:
        if scope not in ("all", row["bundle"]):
            continue
        key, transform = (
            (path1_key, path1_transform) if side == "path1" else (path2_key, path2_transform)
        )
        values[item] = C16_TRANSFORMS[transform](dig_or_none(row, key))
    return values


def c16_identity_stops(inputs: Inputs, side: str) -> list[list[str]]:
    """(row, S-12 / S-4) pairs of the R16-11b identity stops."""
    if side == "path1":
        stops = inputs.pick("path1", "c16_identity_stops")
        pairs = {
            (case, code)
            for case, codes in (stops or {}).items()
            for code in C16_IDENTITY_STOPS
            if (codes or {}).get(code)
        }
    else:
        stops = require_list(inputs.pick("path2", "c16_stops", required=False) or [], "c16 stops")
        pairs = {
            (str(stop.get("where", "")).partition(":")[2], stop.get("code"))
            for stop in stops
            if isinstance(stop, dict) and stop.get("code") in C16_IDENTITY_STOPS
        }
    return sorted([list(pair) for pair in pairs])


def c16_bundle_view(inputs: Inputs, side: str) -> dict[str, Any]:
    bundles = inputs.pick(side, "c16_bundles")
    view = {}
    for bundle in C16_BUNDLES:
        record = bundles.get(bundle) if isinstance(bundles, dict) else None
        if not isinstance(record, dict):
            raise InputError(f"{side} C-9 .. C-11 bundle {bundle} missing")
        view[bundle] = canonical_row(record, f"{side}_c16_bundle", ("state",))["state"]
    view["C-9 P-18 premise"] = inputs.pick(side, "c9_premise", required=False)
    view["C-9 commands same"] = inputs.pick(side, "c9_commands_same", required=False)
    return view


def item_c16(inputs: Inputs) -> ItemResult:
    """R16-11 / RD-5: C-9 .. C-11 record items per row, bundle states, the C-9 P-18 premise and
    the identity stops (CD-10 excluded keys not compared)."""
    rows = {side: c16_rows(inputs, side) for side in ("path1", "path2")}
    differences = []
    for case in sorted(set(rows["path1"]) | set(rows["path2"])):
        if case not in rows["path1"] or case not in rows["path2"]:
            differences.append(
                {"row": case, "only_in": "path1" if case in rows["path1"] else "path2"}
            )
            continue
        items = {side: c16_row_items(rows[side][case], side) for side in ("path1", "path2")}
        differences += [
            {"row": case, "item": name, "path1": value, "path2": items["path2"][name]}
            for name, value in items["path1"].items()
            if not values_equal(value, items["path2"][name])
        ]
    scalars = {
        "bundles": {side: c16_bundle_view(inputs, side) for side in ("path1", "path2")},
        "identity_stops": {side: c16_identity_stops(inputs, side) for side in ("path1", "path2")},
    }
    is_equal = not differences and all(
        values_equal(value["path1"], value["path2"]) for value in scalars.values()
    )
    return result(
        "C-9 .. C-11 records (K-10, CD-10 keys excluded)",
        is_equal,
        {**scalars, "rows": len(rows["path1"]), "item_differences": differences},
    )


def rd13_record(inputs: Inputs) -> dict[str, Any]:
    """RD-13 list sha256 values of both paths, copied for the K-R table (not compared)."""
    record: dict[str, Any] = {}
    for side, name in (
        ("path1", "rd13_lists"),
        ("path2", "rd13_lists"),
        ("path2_v5c", "rd13_lists_v5c"),
    ):
        try:
            value = inputs.pick("path2" if side == "path2_v5c" else side, name, required=False)
        except InputError as error:
            value = {"not_read": str(error)}
        if side == "path1" and isinstance(value, dict):
            value = {
                bundle: entry.get("sha256") if isinstance(entry, dict) else entry
                for bundle, entry in value.items()
            }
        record[side] = value
    return record


# ------------------------------------------------------------------------------ run them
def item_runners() -> list[tuple[str, Callable[[Inputs], ItemResult]]]:
    """Every compared item in report order (name used when the item has an input error)."""
    jp3, j11, s6 = RD7_LISTS
    g5, g6 = G_LISTS
    return [
        ("RD-7 J-P3 list (RD-7 2)", lambda i: item_rd7_list(i, jp3)),
        ("RD-7 J11 list (RD-7 2)", lambda i: item_rd7_list(i, j11)),
        ("RD-7 S-6 list (RD-7 2)", lambda i: item_rd7_list(i, s6)),
        (
            "JD-1 J-P3 = jp_base",
            lambda i: item_baseline(
                i, "JD-1 J-P3 = jp_base", jp3, "jp_base", ("bundle", "file", "location", "leg")
            ),
        ),
        (
            "JD-3 S-6 = s6_base",
            lambda i: item_baseline(
                i, "JD-3 S-6 = s6_base", s6, "s6_base", ("bundle", "file", "location")
            ),
        ),
        ("JD-2 G-5 (5 keys)", lambda i: item_g_list(i, g5, JD2_KEYS, "JD-2 G-5 (5 keys)")),
        ("JD-7 G-6 (3 keys)", lambda i: item_g_list(i, g6, JD7_KEYS, "JD-7 G-6 (3 keys)")),
        ("JD-8 RD-8 marker H-1 / H-3 / H-4", item_jd8),
        ("S6-2 V0 pair source", item_pair_source),
        (
            "S5-3 (a) raw pass->fail, N_raw",
            lambda i: item_grid_list(i, "S5-3 (a) raw pass->fail, N_raw", "grid_raw", "grid_n_raw"),
        ),
        (
            "S5-3 (c) family F excluded pass->fail, N_F",
            lambda i: item_grid_list(
                i, "S5-3 (c) family F excluded pass->fail, N_F", "grid_excluded", "grid_n_f"
            ),
        ),
        ("S5-3 (b) family F table and application condition", item_family_table),
        ("S5-3 records (fail->pass, fail->fail, FAULT, undecidable rows)", item_grid_records),
        ("S5-4 / S6-4 stop H-10 marker and grid term", item_h10),
        ("S4-5 family F R-1 .. R-4", item_family_rules),
        ("RD-11 J_P reading", item_jp),
        ("H-11 G-3 and false pairs", item_g3),
        ("RD-8 undecidable counts and marker", item_rd8),
        ("RD-9 ③-on counts and H-8 dg3 substitution", item_rd9),
        ("RD-10 J11 undecidable / input missing", item_rd10),
        ("C-9 .. C-11 records (K-10, CD-10 keys excluded)", item_c16),
    ]


def run_items(inputs: Inputs) -> list[ItemResult]:
    results = []
    for name, runner in item_runners():
        try:
            results.append(runner(inputs))
        except InputError as error:
            results.append(ItemResult(name, "missing", {"input_error": str(error)}))
    return results


def exit_code(results: list[ItemResult]) -> int:
    statuses = {item.status for item in results}
    if "missing" in statuses:
        return 2
    return 1 if "differ" in statuses else 0


def column_map_record() -> dict[str, Any]:
    """The fixed name tables (files, value places, columns, words) and their sha256."""
    tables = {
        "path1_files": PATH1_FILES,
        "path2_files": PATH2_FILES,
        "field_sources": FIELD_SOURCES,
        "column_map": COLUMN_MAP,
        "value_words": {
            kind: {str(key): value for key, value in words.items()}
            for kind, words in VALUE_WORDS.items()
        },
        "family_k_key_forms": FAMILY_K_KEY_FORMS,
        "path1_violation_fields": PATH1_VIOLATION_FIELDS,
        "c16_items": C16_ITEMS,
        "c16_excluded_keys": C16_EXCLUDED_KEYS,
        "p3_check_keys": P3_CHECK_KEYS,
        "g6_path2_words": {str(key): value for key, value in G6_PATH2_WORDS.items()},
        "count_bundles": {
            "rd8": RD8_BUNDLES,
            "rd8_judged": RD8_JUDGED_BUNDLES,
            "rd9": RD9_BUNDLES,
            "rd9_v5c": RD9_V5C_BUNDLES,
            "rd10": RD10_BUNDLES,
        },
    }
    return {"tables": tables, "sha256": canonical_sha256(tables)}


def build_report(inputs: Inputs, results: list[ItemResult]) -> dict[str, Any]:
    statuses = Counter(item.status for item in results)
    return {
        "tool": Path(__file__).name,
        "tool_sha256": file_sha256(Path(__file__)),
        "column_map_sha256": column_map_record()["sha256"],
        "baseline_sha256_fixed": BASELINE_SHA256,
        "rule": "re-audit M-1; R4 block RD-5 K-10, RD-7..RD-11, JD-1..JD-8, supplements 4-6",
        "inputs": inputs.sha_records(),
        "rd13_sha256": rd13_record(inputs),
        "items": [
            {"item": item.item, "status": item.status, "detail": item.detail} for item in results
        ],
        "counts": {status: statuses.get(status, 0) for status in ("equal", "differ", "missing")},
        "exit_code": exit_code(results),
    }


def write_report(report: dict[str, Any], out: Path) -> str:
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, ensure_ascii=False, indent=1, default=str) + "\n"
    out.write_text(text, encoding="utf-8", newline="\n")
    return file_sha256(out)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--path1-dir", type=Path, help="judge_<M4>/harness_path1")
    parser.add_argument("--path2-dir", type=Path, help="judge_<M4>/harness_path2")
    parser.add_argument("--baseline", type=Path, help="r4_baseline_sets.json (sha256 a5627304...)")
    parser.add_argument("--out", type=Path, help="report JSON")
    parser.add_argument(
        "--show-map",
        action="store_true",
        help="print the fixed name tables and their sha256, compare nothing",
    )
    args = parser.parse_args(argv)
    if not args.show_map and None in (args.path1_dir, args.path2_dir, args.baseline, args.out):
        parser.error("--path1-dir, --path2-dir, --baseline and --out are required")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.show_map:
        record = column_map_record()
        print(json.dumps(record["tables"], ensure_ascii=False, indent=1, sort_keys=True))
        print(
            json.dumps(
                {"tool_sha256": file_sha256(Path(__file__)), "column_map_sha256": record["sha256"]},
                ensure_ascii=True,
            )
        )
        return 0
    inputs = Inputs(args.path1_dir, args.path2_dir, args.baseline)
    report = build_report(inputs, run_items(inputs))
    out_sha256 = write_report(report, args.out)
    print(
        json.dumps(
            {
                "exit_code": report["exit_code"],
                **report["counts"],
                "tool_sha256": report["tool_sha256"],
                "column_map_sha256": report["column_map_sha256"],
                "out": str(args.out),
                "out_sha256": out_sha256,
            },
            ensure_ascii=True,
        )
    )
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
