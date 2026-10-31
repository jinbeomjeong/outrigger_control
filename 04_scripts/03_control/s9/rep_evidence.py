"""Evidence for the representative Chrono set (spec 432.4): E1 harness-Chrono pair table and E5
per-variable monotonicity of the harness results.

E1 pairs every stored Chrono soil result that has a harness twin. Chrono P3b values are read from
``06_analysis/01_chrono/19_S9/s9_P3b_summary.json`` (rev-60 re-judge); the other Chrono values are
copied from the control verdicts in the spec (section numbers in ``src``). Harness values are read
from the R2DS / x426 result files in ``harness_files`` (the R2DS files = implementation 05708b2
line; re-run this script on the final-controller acceptance files later). The RV2 (432.4.4) and
RV3 (426.9.F.1) runs are same-version pairs: Chrono 05708b2 = the harness version. Their values
are read from each run's ``07_results/S9/<batch>/<case>/result_rejudge_rev60.json`` (``p3b``
block; RV3 C-C1 from the G6 judge ``rev85/rv3c_g6_judge.json``); a missing file drops the pair
and is listed in meta ``missing_chrono_inputs``.

Stroke quantities (CLAUDE.md ``stroke_true = s_motor - F_cyl/k_oil``): the controller reading
is larger than the true rod stroke by the oil / contact compliance F_cyl/k_oil (about 5-6 mm at
68 kN), so the pairs compare like with like:
  max_stroke_reading_mm  controller reading. Chrono = per-leg max of ``meas.stroke`` in the run's
                         ``record/record.npz``; harness = ``max_motor_stroke_mm`` = max(plant.sref)
  max_stroke_true_mm     true rod stroke. Chrono = P3-5 ``s_motor_max_m`` (or the spec value of a
                         curated case); the harness results do not store it (``None``)
Schema 2 (2026-10-31) replaced the mixed ``max_stroke_mm`` / ``d_max_stroke_mm`` (Chrono true vs
harness reading) with these two columns and ``d_max_stroke_reading_mm`` (see meta
``schema_change``).

Schema 3 (2026-10-31, spec 432.4.5) adds:
  final_pairs     the final-controller Chrono runs (FINAL-REP 7 + FINAL6 1 + RV6 X6-rb2 1 +
                  X6-rp2 1 + X6-rp3 1 + FINAL-REP-X 1, ``FINAL_RUNS``) with their
                  final-harness twins (``FINAL_HARNESS_FILES_REL``), summarized apart in
                  ``final_summary``; a run
                  marked ``superseded_by`` is listed but not counted (runs still going are
                  listed in ``FINAL_PENDING_RUNS``)
  P3-2 FLAG       the automatic P3b verdict counts a P3-2 judged ``flag`` (late LOC, spec
                  419.8 / 424.8.1) as pass and lists it in the Chrono ``flags``
  censored_at_guard  per pair: True when either run fired the lift-stroke guard
                  (``WARN_LIFT_STROKE_LIMITED`` / ``FAULT_LIFT_STROKE_LIMIT``; Chrono from the
                  run's ``result.json`` events, harness from the record ``warnings``). The max
                  stroke reading is then bounded by the guard, so its delta is a bound.

E5 groups harness records that differ in one independent variable only and reports the direction
of each metric and whether it is monotone across the levels (verdict rank, READY, min cylinder
force, max stroke reading, ready gap). Since 2026-10-31 E5 reads the final-controller harness
(``E5_HARNESS_FILES_REL``: finB2 p0 / slope+H6 / x426b / H9 and fin_x426 C / D; the same tables
as before, split out of the merged final files by id family, see ``final_e5_tables``); E1 keeps
the R2DS / x426 files above. The verdict rank includes the final ``stroke_limited_stop`` (SGS
safe stop) between ``stroke_limited_pass`` and ``fail``; each study also counts its verdict
changes as worse / better (rank of the last level against the first) and the verdicts per level.

Outputs (``<out dir>``, default ``06_analysis/02_control/s9/rev85``):
  harness_chrono_pairs.json   E1
  harness_monotonicity.json   E5

Usage (python-dev):
  python -I rep_evidence.py [<repo root> [<out dir>]]
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT_REL = "04_scripts/03_control/s9/rep_evidence.py"
DEFAULT_OUT_DIR = ROOT / "06_analysis" / "02_control" / "s9" / "rev85"
PAIRS_FILE_NAME = "harness_chrono_pairs.json"
MONOTONICITY_FILE_NAME = "harness_monotonicity.json"
P3B_SUMMARY_REL = Path("06_analysis") / "01_chrono" / "19_S9" / "s9_P3b_summary.json"
HARNESS_FILES_REL = {  # key: path under 06_analysis/02_control/s9
    "p3b": "rev83/R2DS_p3b.json",
    "slope": "rev83/R2DS_slope_rejudged.json",
    "g6": "rev83/R2DS_g6.json",
    "h6": "rev83/R2DS_h6_rejudge_finloc.json",
    "B_Fs0": "rev85/x426_B_Fs0_rejudged.json",
    "B_Fs8": "rev85/x426_B_Fs8_rejudged.json",
    "B_mid": "rev85/x426_B_mid_rejudged.json",
    "B_m1p1": "rev85/x426_B_m1p1_rejudged.json",
    "C": "rev85/x426_C.json",
    "D": "rev85/x426_D.json",
    "H9": "rev85/h9_roll_fine_cmp.json",
}
UNLOADED_HARNESS_KEYS = ("H9",)  # listed in meta only (no record table)

# E5 inputs: the final-controller harness (spec 429.9-429.11 preset = finB2 / fin_x426).
# key: path under 06_analysis/02_control/s9
E5_HARNESS_FILES_REL = {
    "finB2_p0": "rev85/finB2_p0.json",  # base (p3b flat) and g6 / g6r / ref families
    "finB2_slope": "rev85/finB2_harness_rejudged.json",  # H1..H5 (slope 177) and H6
    "finB2_x426b": "rev85/finB2_x426b_rejudged.json",  # x426 B: |Fs0 / |Fs8 / |m1.1 / middle
    "finB2_h9": "rev85/finB2_h9.json",  # H9 fine roll ratio k
    "fin_x426_C": "rev85/fin_x426_C.json",
    "fin_x426_D": "rev85/fin_x426_D.json",
}
E5_OPTIONAL_FILE_KEYS = ("finB2_x426b", "finB2_h9")  # a missing file gives empty tables
P3B_FAMILIES = ("base",)
G6_FAMILIES = ("g6", "g6r", "ref")
SLOPE_FAMILIES = ("H1", "H2", "H3", "H4", "H5")
H6_FAMILIES = ("H6",)
X426B_SUFFIX_TABLES = {"Fs0": "B_Fs0", "Fs8": "B_Fs8", "m1.1": "B_m1p1"}
X426B_MIDDLE_TABLE = "B_mid"  # rows without a suffix: the auger-middle variant of a slope row
E5_HARNESS_NOTE = ("final controller harness (R8 preset with SGS any_loc + R4c30 + L1gs + DSb75; "
                   "finB2 / fin_x426, spec 429.9-429.11), tables split by id family from "
                   "E5_HARNESS_FILES_REL")

RANK = {"pass": 0, "stroke_limited_pass": 1, "stroke_limited_stop": 2, "fail": 3,
        "stroke_limited_fail": 4}
UNKNOWN_VERDICT_RANK = 3
COMPARED_FIELDS = ("ready_s", "min_force_kN", "max_stroke_reading_mm", "max_stroke_true_mm",
                   "gap_ready_mm", "att_end_absmax_deg")
PAIRS_SCHEMA_VERSION = 3
P3B_PASS_CHECKS = ("P3-1_crawler_zero_after_ready", "P3-2_within", "P3-3_within",
                   "P3-4_within_0p2", "P3-5_within", "P3-6_within", "P3-8_within")
# P3-2 late LOC judged as a FLAG (spec 419.8 / 424.8.1) passes; the reason checks name it
P3_2_WITHIN_CHECK = "P3-2_within"
P3_2_VERDICT_KEY = "P3-2_verdict"
P3_2_FLAG_REASON_CHECKS = ("P3-2_late_loc_revoked", "P3-2_late_loc_reapproach")

# E1 side thresholds (ASSUMPTION, see meta "classification")
OPTIMISTIC_READY_DELAY_S = 5.0
CONSERVATIVE_READY_LEAD_S = -5.0
OPTIMISTIC_MIN_FORCE_RATIO = 1.10
CONSERVATIVE_MIN_FORCE_RATIO = 0.90
OPTIMISTIC_GAP_SHORTFALL_MM = -10.0

# E5: a level-to-level change within the tolerance counts as flat
METRICS = ("rank", "ready_s", "min_force_kN", "max_stroke_reading_mm", "gap_ready_mm")
METRIC_TOLERANCE = {"rank": 0, "ready_s": 0.5, "min_force_kN": 0.2,
                    "max_stroke_reading_mm": 0.5, "gap_ready_mm": 0.5}
NON_MONOTONE_LIST_LIMIT = 40

CURATED = (  # (variable, chrono case, harness id, chrono values, version, src)
    ("A2 nose_down G1 B 3.2 deg", "S9SL_C1_G1_B_top_Fs4_r0_p3p2", "H1|G1|B|top|nose_down",
     {"verdict": "pass", "ready_s": 85.0}, "05708b2-, P-S8-33 before", "spec 400.1-400.5"),
    ("A2 roll J1 A 4.4 deg (R_c 1)", "S9SL_C2_J1_A_top_Fs4_r4p4_p0", "H1|J1|A|top|roll_pos",
     {"verdict": "pass", "note": "P3-7 record row only"}, "P-S8-33 before", "spec 400.2"),
    ("A2 roll J1 B 3.3 deg (k 0.75)", "S9SL_C3_J1_B_top_Fs4_r3p3_p0",
     "H3|J1|B|top|roll_pos@k0.75",
     {"verdict": "stroke_limited_pass", "gap_ready_mm": 21.9}, "P-S8-33 before", "spec 400.4"),
    ("A2 nose_down J1 A 3.2 deg (R_c 1)", "S9SL_C4_J1_A_top_Fs4_r0_p3p2",
     "H1|J1|A|top|nose_down",
     {"verdict": "stroke_limited_fail", "note": "FAULT_LIFT_STROKE_LIMIT"}, "P-S8-33 before",
     "spec 400.3"),
    ("A2 nose_down J1 B 2.8 deg (R_c 0.875, REANCHOR)", "S9SL_X4nd_J1_B_top_Fs4_r0_p2p8",
     "H4|J1|B|top|nose_down_2p8",
     {"verdict": "pass", "ready_s": 97.1, "min_force_kN": 66.6, "max_stroke_true_mm": 645.4,
      "gap_ready_mm": 122.5, "att_end_absmax_deg": 0.0386},
     "3434912 (= 05708b2 commands)", "spec 426.9.G.2"),
    ("A2 edge J1 B (R_c 0.875)", "S9SL_X4ed_J1_B_top_Fs4_r1p925_p1p4",
     "H3|J1|B|top|edge_nd@k0.875",
     {"verdict": "pass", "ready_s": 62.4, "min_force_kN": 63.7, "max_stroke_true_mm": 653.1,
      "gap_ready_mm": 69.2, "att_end_absmax_deg": 0.048}, "3434912", "spec 426.9.G.4"),
    ("A2 roll J1 B 3.85 deg (R_c 0.875)", "S9SL_X4rp_J1_B_top_Fs4_r3p85_p0",
     "H3|J1|B|top|roll_pos@k0.875",
     {"verdict": "stroke_limited_fail", "min_force_kN": 1.2}, "3434912", "spec 426.9.G.3"),
    ("B4 weight x1.1 J2 B", "P3b_J2_B_top_Fs4_m1p1 (RV1 X5)", "H6|J2|B|top|flat|m1.1",
     {"verdict": "fail", "ready_s": 104.1, "min_force_kN": 74.3, "max_stroke_true_mm": 586.9,
      "gap_ready_mm": 41.5, "att_end_absmax_deg": 0.0295, "note": "P3-6 only"}, "3434912",
     "spec 426.9.G.1"),
    ("B4 weight x1.1 J1 B", "P3b_J1_B_top_Fs4_m1p1 (D424R 1)", "H6|J1|B|top|flat|m1.1",
     {"verdict": "fail", "ready_s": 103.3, "min_force_kN": 74.8, "gap_ready_mm": 31.3,
      "att_end_absmax_deg": 0.026, "note": "P3-6 only"}, "3434912 (final - ZIC/R4/SGS)",
     "paper 4.8.2, spec D424R verdict"),
    ("B4 weight x1.2 J1 B", "P3b_J1_B_top_Fs4_m1p2 (D424 2)", "H6|J1|B|top|flat|m1.2",
     {"verdict": "fail", "note": "LOC unconfirmed safe stop (both engines)",
      "max_stroke_true_mm": 528.0, "min_force_kN": 64.3}, "R7 before (LOC 0: equivalent)",
     "paper 4.8.2"),
    ("B1 auger middle J2 B", "P3b_J2_B_middle_Fs4 (D424R 3)", "base|J2|B|middle|Fs4",
     {"verdict": "pass", "ready_s": 79.0, "min_force_kN": 68.41, "gap_ready_mm": 37.12,
      "att_end_absmax_deg": 0.01729}, "3434912", "paper table 17"),
    ("B1 auger bottom J2 B", "P3b_J2_B_bottom_Fs4 (D424R 3)", "base|J2|B|bottom|Fs4",
     {"verdict": "pass", "ready_s": 57.8, "min_force_kN": 68.67, "gap_ready_mm": 38.97,
      "att_end_absmax_deg": 0.01344, "note": "first READY, relevel, last READY 91.2 s"},
     "3434912", "paper table 17"),
    ("B1 auger middle J2 A", "P3b_J2_A_middle_Fs4", "base|J2|A|middle|Fs4",
     {"verdict": "pass", "ready_s": 53.1, "min_force_kN": 66.8}, "p3b_aug (equiv. final-R7)",
     "paper table 17"),
    ("B1 auger bottom J2 A", "P3b_J2_A_bottom_Fs4", "base|J2|A|bottom|Fs4",
     {"verdict": "pass", "ready_s": 53.1, "min_force_kN": 66.7}, "p3b_aug", "paper table 17"),
    ("B1 auger middle S1 B", "P3b_S1_B_middle_Fs4", "base|S1|B|middle|Fs4",
     {"verdict": "pass", "ready_s": 60.0, "min_force_kN": 68.7}, "p3b_aug", "paper table 17"),
    ("B1 auger bottom S1 B", "P3b_S1_B_bottom_Fs4", "base|S1|B|bottom|Fs4",
     {"verdict": "pass", "ready_s": 59.9, "min_force_kN": 68.8}, "p3b_aug", "paper table 17"),
    ("B1 auger middle S1 A", "P3b_S1_A_middle_Fs4", "base|S1|A|middle|Fs4",
     {"verdict": "pass", "ready_s": 56.6, "min_force_kN": 67.3}, "p3b_aug", "paper table 17"),
    ("B1 auger bottom S1 A", "P3b_S1_A_bottom_Fs4", "base|S1|A|bottom|Fs4",
     {"verdict": "pass", "ready_s": 56.5, "min_force_kN": 67.3}, "p3b_aug", "paper table 17"),
    ("A3 soft patch G1@RR (control)", "G6_G1_B_top_Fs4_spG1RR", "ref|G1|top|Fs4",
     {"verdict": "pass", "ready_s": 43.3, "min_force_kN": 62.8, "att_end_absmax_deg": 0.014},
     "0.3 kN", "paper table 15"),
    ("A3 soft patch J1@RR", "G6_G1_B_top_Fs4_spJ1RR", "g6|G1+J1@RR|top|Fs4",
     {"verdict": "pass", "ready_s": 74.5, "min_force_kN": 49.86, "att_end_absmax_deg": 0.015},
     "0.6 kN", "paper table 15"),
    ("A3 soft patch J1@FL", "G6_G1_B_top_Fs4_spJ1FL", "g6|G1+J1@FL|top|Fs4",
     {"verdict": "pass", "ready_s": 66.8, "min_force_kN": 27.8, "att_end_absmax_deg": 0.014},
     "0.6 kN", "paper table 15"),
    ("A3 soft patch J2@RR", "G6_G1_B_top_Fs4_spJ2RR", "g6|G1+J2@RR|top|Fs4",
     {"verdict": "pass", "ready_s": 96.1, "min_force_kN": 40.4, "att_end_absmax_deg": 0.008},
     "0.6 kN", "paper table 15"),
    ("A3 soft patch J2@FL", "G6_G1_B_top_Fs4_spJ2FL", "g6|G1+J2@FL|top|Fs4",
     {"verdict": "pass", "ready_s": 85.6, "min_force_kN": 30.0, "att_end_absmax_deg": 0.015},
     "0.6 kN", "paper table 15"),
    ("A3 soft patch S1@FL", "G6_G1_B_top_Fs4_spS1FL", "g6|G1+S1@FL|top|Fs4",
     {"verdict": "pass", "ready_s": 66.6, "min_force_kN": 17.9, "att_end_absmax_deg": 0.013,
      "note": "G6-7 out-of-scope FLAG"}, "final code (409.1)", "paper table 15"),
)

# Chrono run folders (under 07_results/S9) of the curated cases, keyed by harness id.
# Identity check (the run's judged values equal the spec values of that section):
#   X4-nd / X4-ed / RV1 X5: s_motor max 645.4 / 653.1 / 586.9 mm; x1.2 J1 B: 528.3 mm on RL
#     vs spec 528.0 mm
#   S9SL final code (batch_S9SL_20261029_144406; the 2026-10-28 batches are the old code):
#     C-1 READY 85.0 s, min 31.9 kN, gap 89.2 mm (400.1); C-2 READY 81.1 s, 60.7 kN, gap
#     59.0 mm (400.2); C-3 gap 21.9 mm, FR 677.8 mm (400.4); C-4 min 54.9 kN, no READY (400.3)
#   X4-rp: min after departure 1.16 kN, spec 1.2 kN (426.9.G.3)
CURATED_RECORD_DIRS = {
    "H4|J1|B|top|nose_down_2p8": ("batch_RV1_20261030_111615",
                                  "S9SL_X4nd_J1_B_top_Fs4_r0_p2p8"),
    "H3|J1|B|top|edge_nd@k0.875": ("batch_RV1_20261030_111615",
                                   "S9SL_X4ed_J1_B_top_Fs4_r1p925_p1p4"),
    "H6|J2|B|top|flat|m1.1": ("batch_RV1_20261030_111615", "P3b_J2_B_top_Fs4_m1p1"),
    "H6|J1|B|top|flat|m1.2": ("batch_D424_20261030_014908", "P3b_J1_B_top_Fs4_m1p2"),
    "H1|G1|B|top|nose_down": ("batch_S9SL_20261029_144406", "S9SL_C1_G1_B_top_Fs4_r0_p3p2"),
    "H1|J1|A|top|roll_pos": ("batch_S9SL_20261029_144406", "S9SL_C2_J1_A_top_Fs4_r4p4_p0"),
    "H3|J1|B|top|roll_pos@k0.75": ("batch_S9SL_20261029_144406",
                                   "S9SL_C3_J1_B_top_Fs4_r3p3_p0"),
    "H1|J1|A|top|nose_down": ("batch_S9SL_20261029_144406", "S9SL_C4_J1_A_top_Fs4_r0_p3p2"),
    "H3|J1|B|top|roll_pos@k0.875": ("batch_RV1_20261030_111615",
                                    "S9SL_X4rp_J1_B_top_Fs4_r3p85_p0"),
}

STATIC_RIGID = [  # pairs without per-case values here (paper table 3)
    {"variable": "A4 rigid LEVEL events", "n": 27,
     "metric": "event-leg lift time harness/Chrono 1.02-1.08", "side": "conservative",
     "src": "spec 350.3"},
    {"variable": "TOUCH rule change (rigid)", "metric": "harness predicts larger command change",
     "side": "conservative", "src": "spec 358.7-358.8"},
    {"variable": "A3 non-planar rigid L1-R", "n": 4,
     "metric": "stroke / gap diff <= 0.2 mm (F_s 0)", "side": "representative",
     "src": "decision_log C-S8-76"},
]

# Same-version pairs (Chrono 05708b2 = harness R2DS / x426), spec 432.4.4 and 426.9.F.1.
# Chrono values come from each run folder's ``result_rejudge_rev60.json`` (``p3b`` block).
CHRONO_RESULTS_REL = Path("07_results") / "S9"
REJUDGE_FILE_NAME = "result_rejudge_rev60.json"
RECORD_NPZ_REL = Path("record") / "record.npz"
RUN_RESULT_FILE_NAME = "result.json"  # holds the run's ``events`` list
STROKE_READING_KEY = "meas.stroke"  # controller stroke reading in m, shape (samples, 4 legs)
STROKE_GUARD_EVENT_PREFIXES = ("WARN_LIFT_STROKE_LIMITED", "FAULT_LIFT_STROKE_LIMIT")
SAME_VERSION = "05708b2 (same as harness)"
RV2_RUNS = (  # (batch folder, P3b case)
    ("batch_RV2_20261030_154549", "P3b_J1_B_top_Fs0"),
    ("batch_RV2_20261030_154549", "P3b_J1_B_top_Fs4"),
    ("batch_RV2_20261030_154549", "P3b_J1_B_top_Fs8"),
    ("batch_RV2_20261030_155059", "P3b_J2_B_top_Fs4"),
)
RV3_SLOPE_RUN = {  # B-C1: both runs end in the FAULT_LIFT_STROKE_LIMIT:FR safe stop
    "variable": "A2 roll S1 B 3.3 deg (k 0.75) F_s 0 [RV3 B-C1]",
    "batch": "batch_RV3_20261030_134001", "case": "S9SL_RV3B_S1_B_top_Fs0_r3p3_p0",
    "harness_id": "H3|S1|B|top|roll_pos@k0.75|Fs0",
    "note": "426.9.F.1: pass (b) safe stop FAULT_LIFT_STROKE_LIMIT:FR, no READY; the P3 rows "
            "fail in both engines (same end path)",
    "src_spec": "spec 426.9.F.1"}
RV3_G6_RUN = {  # C-C1: judged by r76_g6_chrono_judge.py (gates), not by the p3b block
    "variable": "A3 soft patch S1@FL pad A [RV3 C-C1]",
    "batch": "batch_RV3_20261030_134021", "case": "G6_G1_A_top_Fs4_spS1FL",
    "harness_id": "g6|G1+S1@FL|top|Fs4|PA",
    "judge_rel": "06_analysis/02_control/s9/rev85/rv3c_g6_judge.json",
    "note": "426.9.F.1: pass with FLAGs (G6-2 late LOC, G6-7 out of scope); gates G6-2 and "
            "G6-7 false, G6-7 fails in the harness too",
    "src_spec": "spec 426.9.F.1"}

# Final-controller pairs (spec 432.4.5 table; Chrono = R8 preset with SGS any_loc + R4c30 +
# L1gs + DSb75 = the final harness finB2 / fin_x426_D). Chrono values come from each run's
# ``result_rejudge_rev60.json`` (``p3b`` block). ``verdict`` (optional) replaces the automatic
# P3b verdict with the control verdict of section ``spec``.
FINAL_VERSION = "final controller (SGS any_loc + R4c30 + L1gs + DSb75), same as final harness"
FINAL_HARNESS_FILES_REL = {  # key: path under 06_analysis/02_control/s9
    "finB2_p0": "rev85/finB2_p0.json",
    "finB2_slope": "rev85/finB2_harness_rejudged.json",
    "finB2_h9": "rev85/finB2_h9.json",
    "fin_x426_D": "rev85/fin_x426_D.json",
}
FINAL_REP_BATCH = "batch_FINAL-REP_20261030_223359"
P3_2_FLAG_NOTE = ("432.5.2: pass with the P3-2 FLAG late_loc_revoked (FLAG rule 419.8 / "
                  "424.10.2); the automatic P3b verdict also counts the P3-2 FLAG as pass "
                  "(chrono flags)")
FINAL_REP_X_BATCH = "batch_FINAL-REP-X_20261031_020716"
FINAL_REP_X_CASE = "P3b_J2_B_top_Fs4_m1p1_t180"
# ``superseded_by``: a later run of the same pair replaces this one; it stays in final_pairs
# (marked) but final_summary counts only the replacing run.
FINAL_RUNS = (
    {"variable": "A1 soil / B3 pad: J1 B top [FINAL-REP B0]", "batch": FINAL_REP_BATCH,
     "case": "P3b_J1_B_top_Fs4", "harness_key": "finB2_p0",
     "harness_id": "base|J1|B|top|Fs4", "spec": "spec 432.5.2"},
    {"variable": "A1 soil / B3 pad: J2 B top [FINAL-REP]", "batch": FINAL_REP_BATCH,
     "case": "P3b_J2_B_top_Fs4", "harness_key": "finB2_p0",
     "harness_id": "base|J2|B|top|Fs4", "spec": "spec 432.5.2", "verdict": "pass",
     "note": P3_2_FLAG_NOTE},
    {"variable": "B1 auger middle J2 B [FINAL-REP]", "batch": FINAL_REP_BATCH,
     "case": "P3b_J2_B_middle_Fs4", "harness_key": "finB2_p0",
     "harness_id": "base|J2|B|middle|Fs4", "spec": "spec 432.5.2", "verdict": "pass",
     "note": P3_2_FLAG_NOTE},
    {"variable": "B4 weight x1.1 J1 B [FINAL-REP]", "batch": FINAL_REP_BATCH,
     "case": "P3b_J1_B_top_Fs4_m1p1", "harness_key": "finB2_slope",
     "harness_id": "H6|J1|B|top|flat|m1.1", "spec": "spec 432.5.1"},
    {"variable": "B4 weight x1.1 J2 B [FINAL-REP]", "batch": FINAL_REP_BATCH,
     "case": "P3b_J2_B_top_Fs4_m1p1", "harness_key": "finB2_slope",
     "harness_id": "H6|J2|B|top|flat|m1.1", "spec": "spec 432.5.1",
     "note": "superseded by FINAL-REP-X (432.5.4) for P3-4",
     "superseded_by": f"{FINAL_REP_X_CASE} @ {FINAL_REP_X_BATCH}"},
    {"variable": "B4 weight x1.1 J2 B 180 s [FINAL-REP-X]", "batch": FINAL_REP_X_BATCH,
     "case": FINAL_REP_X_CASE, "harness_key": "finB2_slope",
     "harness_id": "H6|J2|B|top|flat|m1.1", "spec": "spec 432.5.4", "verdict": "pass",
     "note": "432.5.4: pass with the P3-2 FLAG late_loc_revoked; P3-4 0.032 deg (window "
             "54.7 s); first READY 98.9 s, one relevel, last READY 118.9 s; commands "
             "bit-identical to the 120 s run up to 128 s"},
    {"variable": "A2 roll J1 B 2.86 deg (k 0.65) [X6-rb]", "batch": FINAL_REP_BATCH,
     "case": "S9SL_X6rb_J1_B_top_Fs4_rm2p86_p0", "harness_key": "finB2_h9",
     "harness_id": "H9|J1|B|top|roll_neg@k0.65", "spec": "spec 430.3.2",
     "verdict": "stroke_limited_stop",
     "note": "430.3.2: SGS safe stop FAULT_LIFT_STROKE_LIMIT:soil:FL at the first guard cycle "
             "(out of the boundary); the Chrono reading is cut at the guard"},
    {"variable": "A2 roll J1 B -2.64 deg roll_neg (k 0.6) [X6-rb2]",
     "batch": "batch_RV6_20261031_025137",
     "case": "S9SL_X6rb_J1_B_top_Fs4_rm2p64_p0", "harness_key": "finB2_h9",
     "harness_id": "H9|J1|B|top|roll_neg@k0.6", "spec": "spec 430.3.3", "verdict": "pass",
     "note": "430.3.3: pass, no guard / SGS; reading max FL 679.87 mm (guard margin 2.93 mm), "
             "harness 661.02 (+18.85 uncensored); gap -14.5 mm vs harness"},
    {"variable": "A2 roll J1 B +2.64 deg roll_pos (k 0.6) [X6-rp2]",
     "batch": "batch_RV6_20261031_070613",
     "case": "S9SL_X6rb_J1_B_top_Fs4_r2p64_p0", "harness_key": "finB2_h9",
     "harness_id": "H9|J1|B|top|roll_pos@k0.6", "spec": "spec 430.3.5", "verdict": "fail",
     "note": "430.3.5: fail on P3-5 only (gap 24.84 mm < 25 mm at the READY entry sample, "
             "26.1 mm 5 s later); no guard / SGS, reading max RR 631.01 mm (guard margin "
             "51.79 mm), harness 613.99 (+17.03 uncensored); gap -6.09 mm vs harness (within "
             "slope -15); harness pass -> verdict mismatch, harness optimistic"},
    {"variable": "A2 roll J1 B +2.2 deg roll_pos (k 0.5) [X6-rp3]",
     "batch": "batch_RV6_20261031_091226",
     "case": "S9SL_X6rb_J1_B_top_Fs4_r2p2_p0", "harness_key": "finB2_slope",
     "harness_id": "H3|J1|B|top|roll_pos@k0.5", "spec": "spec 430.3.7", "verdict": "pass",
     "note": "430.3.7: pass, no guard / SGS; gap 32.63 mm (P3-5 margin 7.63 mm), reading max "
             "RR 612.40 mm (guard margin 70.40 mm), harness 595.92 (+16.48 uncensored); gap "
             "-10.48 mm, READY +22.4 s vs harness (within slope -15 / +31); H9 has no k 0.5 "
             "row, twin = H3 row (430.3.6)"},
    {"variable": "A2 roll J1 B 3.85 deg (k 0.875) [X6-rp-sa]", "batch": FINAL_REP_BATCH,
     "case": "S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0", "harness_key": "finB2_slope",
     "harness_id": "H3|J1|B|top|roll_pos@k0.875", "spec": "spec 430.4.1",
     "note": "430.4.1: SGS safe stop accepted (a, b, c); crawler 7.79 kN > 0.01 W at the stop "
             "-> fail + stop_with_crawler_loaded; both runs stop at the guard"},
    {"variable": "A3 dip J2 B RR 150 mm [FINAL6 d150]",
     "batch": "batch_FINAL6_20261031_000833", "case": "P3b_J2_B_top_Fs4_sgRRd150",
     "harness_key": "fin_x426_D", "harness_id": "H8|J2|B|top|flat|RR:d150",
     "spec": "spec 426.9.D.2"},
)
# Final-controller runs still going. Not paired yet: move an entry into FINAL_RUNS (with its
# control verdict) once the run is re-judged. X6-rb2, X6-rp2, X6-rp3 and FINAL-REP-X moved on
# 2026-10-31. An entry may be listed before its run starts: the fields named in
# ``to_fill_after_run`` are placeholders (``None`` or an expected value) until then.
FINAL_PENDING_RUNS: tuple[dict, ...] = ()

H6_MARGIN_NOTE = (
    "H-6 optimistic margin (ASSUMPTION, spec 432.4 / 432.4.5 / 432.4.7, 2026-10-31): flat "
    "READY +17 s, gap -13 mm (RV2 J2 -12.7 mm, 432.4.4); soft slope rows gap -15 mm (X6-rb2 "
    "-14.5 mm, 432.4.7); stroke reading one-sided +23 mm (Chrono "
    "meas.stroke max - harness max(plant.sref); observed X6-rb vs H9 roll_neg@k0.65 >= "
    "+22.7 mm censored at the guard, RV3 C-C1 +21.5 mm uncensored; stroke sensor share "
    "<= 0.4 mm) for soft J1/J2/S1 incl. one-pad patches, not G1 or rigid; slope / x1.1 "
    "READY +31 s")

PAIRS_CLASSIFICATION = (
    "optimistic if harness verdict better, or Chrono READY - harness > 5 s, or harness min F / "
    "Chrono > 1.10, or Chrono gap - harness < -10 mm; conservative = the opposite (READY < -5 s, "
    "ratio < 0.90, verdict worse); mixed = both (ASSUMPTION thresholds)")
PAIRS_VERSION_CAVEAT = (
    "Harness = R2DS (05708b2 line). Chrono = the stored run version (column). Pairs whose "
    "versions differ are trend evidence, not identity; re-run on the final acceptance files. "
    "final_pairs: Chrono final controller = final harness (finB2 / fin_x426_D).")
STROKE_QUANTITY_NOTE = (
    "max_stroke_reading_mm = controller stroke reading (Chrono: max of record meas.stroke per "
    "leg FL, FR, RL, RR; harness: max(plant.sref)); max_stroke_true_mm = true rod stroke "
    "(Chrono: P3-5 s_motor_max_m per leg or the spec value; harness: not stored). The reading "
    "exceeds the true stroke by F_cyl/k_oil (about 5-6 mm at 68 kN). Deltas pair the same "
    "quantity only; a per-leg list counts by its max.")
PAIRS_SCHEMA_CHANGE = (
    "schema 2 (2026-10-31): max_stroke_mm (Chrono true rod stroke vs harness reading, mixed) "
    "split into max_stroke_reading_mm and max_stroke_true_mm; d_max_stroke_mm replaced by "
    "d_max_stroke_reading_mm (d_max_stroke_true_mm when both sides have it); summary adds "
    "d_max_stroke_reading_mm_chrono_minus_harness; meta adds missing_stroke_records. Readers "
    "of d_max_stroke_mm should use d_max_stroke_reading_mm. "
    "schema 3 (2026-10-31, spec 432.4.5): final_pairs / final_summary (final controller "
    "Chrono vs final harness, see final_pairs_note); per pair censored_at_guard, "
    "censored_side and Chrono stroke_guard_events (harness records carry "
    "stroke_guard_events); summaries add the uncensored reading-delta stats and the censored "
    "list; curated S9SL C-1..C-4 and X4-rp now carry the Chrono stroke reading. h6_margin "
    "quotes spec 432.4.5 (stroke +23 mm, reading vs reading) and is not re-derived here. "
    "schema 3 addition (2026-10-31, final 10 runs): the automatic P3b verdict counts a P3-2 "
    "judged flag (late_loc_revoked / late_loc_reapproach, spec 419.8 / 424.8.1) as pass and "
    "lists it in chrono flags (key present only with a FLAG); final pairs may carry "
    "superseded_by (left out of final_summary, listed in final_summary.superseded).")
FINAL_PAIRS_NOTE = (
    "final_pairs = the final-controller Chrono runs (FINAL_RUNS: FINAL-REP 7 + FINAL6 1 + RV6 "
    "X6-rb2 1 + X6-rp2 1 + X6-rp3 1 + FINAL-REP-X 1; the 120 s x1.1 J2 run is superseded by "
    "FINAL-REP-X) with their final-harness twins (final_harness_files), same version on both "
    "sides. They are "
    "summarized apart in final_summary and are NOT counted in summary: summary keeps the 54 "
    "stored-version pairs (several are the same cases at older versions; counting both would "
    "count a case twice). combined_counts adds the two verdict-match counts for reference "
    "only. Chrono verdict = the automatic P3b block (all P3B_PASS_CHECKS) unless the run "
    "carries the control verdict of its spec section (then verdict_auto keeps the automatic "
    "one). Pairs with censored_at_guard true give a bound, not a value: they are left out of "
    "the *_uncensored stroke stats and listed in censored_stroke_reading. Pairs with "
    "superseded_by are replaced by that run: kept in final_pairs, left out of final_summary "
    "counts and listed in final_summary.superseded. Pending runs (final_pending_runs) are not "
    "paired yet.")
CENSORING_NOTE = (
    "censored_at_guard = true when either run fired the lift-stroke guard "
    "(WARN_LIFT_STROKE_LIMITED / FAULT_LIFT_STROKE_LIMIT; Chrono: result.json events, harness: "
    "record warnings); false when both sides are known and none fired; null when a side is "
    "unknown and the other did not fire. The max stroke reading of a guarded run is bounded "
    "by the guard (682.8 mm budget), so d_max_stroke_reading_mm is a bound there: Chrono side "
    "only -> lower bound of Chrono - harness, harness side only -> upper bound, both -> no "
    "information.")
MONOTONICITY_SCHEMA_CHANGE = (
    "2026-10-31: metric max_stroke_mm renamed max_stroke_reading_mm (harness max(plant.sref), "
    "values unchanged). 2026-10-31 (final inputs): E5 reads the final-controller harness "
    "(meta harness_files) instead of R2DS / x426 (05708b2); per study verdict_change_counts "
    "(worse / better / same_ends: rank of the last level vs the first) and verdict_counts "
    "(per level); new study A2 roll ratio k fine (h9); meta unassigned_x426b lists x426b ids "
    "of no variant table (previous output: history/harness_monotonicity_pre_finalE5_20261031"
    ".json)")
MONOTONICITY_TOLERANCE_NOTE = ("flat if |delta| <= 0.5 s / 0.5 mm / 0.2 kN; monotone = "
                               "non-strict with that tolerance")


# ---------------------------------------------------------------------------- inputs
def _load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _script_sha256() -> str:
    # LF line ends: a CRLF checkout gives the same digest
    return hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def harness_files(repo: Path) -> dict[str, Path]:
    """Harness result files of the evidence tables, keyed as in the meta ``harness_files``."""
    s9_dir = repo / "06_analysis" / "02_control" / "s9"
    return {key: s9_dir / rel for key, rel in HARNESS_FILES_REL.items()}


def final_harness_files(repo: Path) -> dict[str, Path]:
    """Final-harness result files of the final pairs, keyed as ``FINAL_RUNS`` harness_key."""
    s9_dir = repo / "06_analysis" / "02_control" / "s9"
    return {key: s9_dir / rel for key, rel in FINAL_HARNESS_FILES_REL.items()}


def stroke_guard_events(event_names: list[str]) -> list[str]:
    """Lift-stroke guard events among ``event_names``, sorted and without repeats."""
    return sorted({name for name in event_names
                   if name.startswith(STROKE_GUARD_EVENT_PREFIXES)})


def normalize_record(record: dict) -> dict:
    """Common fields of one harness record (R2DS records, x426 B/D results, x426 C results)."""
    run = record.get("run") or {}
    verdict = record.get("verdict")
    if verdict is None and "pass" in record:
        verdict = "pass" if record["pass"] else "fail"
    att_end_deg = record.get("att_end_deg") or run.get("att_end_deg")
    min_force_kN = record.get(
        "min_force_kN",
        record.get("min_true_Fcyl_after_off_kN", run.get("min_true_Fcyl_after_off_kN")))
    # the harness result files store max(plant.sref) as "max_stroke_mm" (R2DS) or
    # "max_motor_stroke_mm" (x426): both are the controller reading, not the rod stroke
    max_stroke_reading_mm = record.get(
        "max_stroke_mm", record.get("max_motor_stroke_mm", run.get("max_motor_stroke_mm")))
    warnings = record.get("warnings")
    return {
        "id": record.get("id") or record.get("key"),
        "verdict": verdict,
        "ready_s": record.get("t_ready_s", run.get("t_ready_s")),
        "min_force_kN": min_force_kN,
        "max_stroke_reading_mm": max_stroke_reading_mm,
        "max_stroke_true_mm": None,  # max(plant.x) is not stored by the harness runs
        "gap_ready_mm": record.get("rut_ready_mm", record.get("rut_clear_ready_mm")),
        "att_end_absmax_deg": max(abs(a) for a in att_end_deg) if att_end_deg else None,
        "stroke_guard_events": None if warnings is None else stroke_guard_events(warnings),
    }


def load_records(path: Path) -> dict[str, dict]:
    """Normalized records of one result file by id (records without an id are dropped)."""
    data = _load_json(path)
    rows = data.get("records") or data.get("results") or []
    normalized = (normalize_record(row) for row in rows)
    return {record["id"]: record for record in normalized if record["id"]}


def load_harness(files: dict[str, Path]) -> dict[str, dict[str, dict]]:
    """Records of every harness file that exists; missing files are skipped."""
    return {key: load_records(path) for key, path in files.items()
            if key not in UNLOADED_HARNESS_KEYS and path.exists()}


def e5_harness_files(repo: Path) -> dict[str, Path]:
    """Final-controller harness files of E5, keyed as ``E5_HARNESS_FILES_REL``."""
    s9_dir = repo / "06_analysis" / "02_control" / "s9"
    return {key: s9_dir / rel for key, rel in E5_HARNESS_FILES_REL.items()}


def records_of_families(records: dict[str, dict], families: tuple[str, ...]) -> dict[str, dict]:
    """The records whose id starts with one of ``families`` (the part before the first ``|``)."""
    return {record_id: record for record_id, record in records.items()
            if record_id.split("|", 1)[0] in families}


def split_x426b(records: dict[str, dict]) -> tuple[dict[str, dict[str, dict]], list[str]]:
    """The merged x426 B file split into the variant tables of ``_x426_b_studies``.

    An id ending in ``|Fs0`` / ``|Fs8`` / ``|m1.1`` goes to its suffix table; an id without a
    suffix that names the middle auger level goes to ``B_mid``.

    Returns:
        The tables (all four keys, possibly empty) and the ids that fit none of them.
    """
    tables: dict[str, dict[str, dict]] = {name: {} for name in X426B_SUFFIX_TABLES.values()}
    tables[X426B_MIDDLE_TABLE] = {}
    unassigned: list[str] = []
    for record_id, record in records.items():
        suffix = record_id.rsplit("|", 1)[-1]
        if suffix in X426B_SUFFIX_TABLES:
            tables[X426B_SUFFIX_TABLES[suffix]][record_id] = record
        elif "|middle|" in record_id:
            tables[X426B_MIDDLE_TABLE][record_id] = record
        else:
            unassigned.append(record_id)
    return tables, unassigned


def _load_e5_file(files: dict[str, Path], key: str) -> dict[str, dict]:
    if key in E5_OPTIONAL_FILE_KEYS and not files[key].exists():
        return {}
    return load_records(files[key])


def final_e5_tables(files: dict[str, Path]) -> tuple[dict[str, dict[str, dict]], list[str]]:
    """E5 tables (keys as ``build_studies`` expects) from the final-controller harness files.

    Args:
        files: ``e5_harness_files`` (or the same keys elsewhere).

    Returns:
        The tables and the x426 B ids of no variant table.

    Raises:
        FileNotFoundError: a required file (all but ``E5_OPTIONAL_FILE_KEYS``) is missing.
    """
    p0 = load_records(files["finB2_p0"])
    slope_and_h6 = load_records(files["finB2_slope"])
    x426b_tables, unassigned = split_x426b(_load_e5_file(files, "finB2_x426b"))
    tables = {"p3b": records_of_families(p0, P3B_FAMILIES),
              "g6": records_of_families(p0, G6_FAMILIES),
              "slope": records_of_families(slope_and_h6, SLOPE_FAMILIES),
              "h6": records_of_families(slope_and_h6, H6_FAMILIES),
              "H9": _load_e5_file(files, "finB2_h9"),
              "C": load_records(files["fin_x426_C"]),
              "D": load_records(files["fin_x426_D"]),
              **x426b_tables}
    return tables, unassigned


def merge_by_id(harness: dict[str, dict[str, dict]]) -> dict[str, dict]:
    """One record per id over all files, tagged with its ``source``; the first file wins."""
    merged: dict[str, dict] = {}
    for source, records in harness.items():
        for record_id, record in records.items():
            merged.setdefault(record_id, dict(record, source=source))
    return merged


# ---------------------------------------------------------------------------- E1: pairs
def _scaled(value: float | None, factor: float) -> float | None:
    return None if value is None else value * factor


def read_stroke_reading_max_mm(record_path: Path) -> list[float] | None:
    """Per-leg (FL, FR, RL, RR) maximum of the controller stroke reading of one Chrono run.

    Args:
        record_path: The run's ``record/record.npz``.

    Returns:
        The maxima in mm, or ``None`` when the run has no record file.
    """
    if not record_path.exists():
        return None
    with np.load(record_path, allow_pickle=False) as record:
        reading_m = np.asarray(record[STROKE_READING_KEY])
    return [float(value) * 1e3 for value in reading_m.max(axis=0)]


def read_chrono_guard_events(result_path: Path) -> list[str] | None:
    """Lift-stroke guard events of one Chrono run (``None`` when it has no ``result.json``)."""
    if not result_path.exists():
        return None
    events = _load_json(result_path).get("events") or []
    return stroke_guard_events([str(event.get("name", "")) for event in events])


def stroke_reading_fields(case_dir: Path, repo: Path) -> dict:
    """Chrono stroke-reading columns of the run in ``case_dir``, the record file they use and
    the run's lift-stroke guard events."""
    record_path = case_dir / RECORD_NPZ_REL
    return {"max_stroke_reading_mm": read_stroke_reading_max_mm(record_path),
            "stroke_record": _repo_rel(record_path, repo),
            "stroke_guard_events": read_chrono_guard_events(case_dir / RUN_RESULT_FILE_NAME)}


def p3_2_flag_names(checks: dict) -> list[str]:
    """FLAG names of a P3-2 check judged ``flag`` (late LOC, spec 419.8 / 424.8.1), else [].

    The reason comes from the ``P3-2_late_loc_*`` booleans; a ``flag`` verdict without one of
    them is kept as the bare ``P3-2_flag``.
    """
    if checks.get(P3_2_VERDICT_KEY) != "flag":
        return []
    reasons = [check for check in P3_2_FLAG_REASON_CHECKS if checks.get(check)]
    return reasons or ["P3-2_flag"]


def _p3b_check_passes(checks: dict, check: str) -> bool:
    """One P3b pass check; P3-2 also passes as a FLAG (FLAG rule 419.8, not a failure)."""
    if check == P3_2_WITHIN_CHECK:
        return bool(checks.get(check)) or checks.get(P3_2_VERDICT_KEY) == "flag"
    return bool(checks.get(check))


def chrono_values_from_p3b_block(row: dict) -> dict:
    """Judged values of one rev-60 P3b block (summary row or ``result_rejudge`` ``p3b``).

    A run without READY has no READY time and no clearance after READY (``None``). The stroke
    of the block is the true rod stroke (per leg); the reading comes from the record file.
    A P3-2 judged ``flag`` counts as pass and its FLAG names are listed in ``flags`` (the key
    is present only when there is a FLAG).
    """
    checks = row["checks"]
    is_pass = all(_p3b_check_passes(checks, check) for check in P3B_PASS_CHECKS)
    clearance = row["P3-5_clearance_stroke"]
    values = {
        "verdict": "pass" if is_pass else "fail",
        "ready_s": row["P3-6_ready"]["t_ready_after_loop_start_s"],
        "min_force_kN": min(row["P3-3_leg_force"]["F_min_after_N"]) / 1e3,
        "max_stroke_true_mm": [value * 1e3 for value in clearance["s_motor_max_m"]],
        "gap_ready_mm": _scaled(clearance["rut_clearance_min_after_first_ready_m"], 1e3),
        "att_end_absmax_deg": row["P3-4_attitude"]["p34_absmax_deg"]}
    flags = p3_2_flag_names(checks)
    if flags:
        values["flags"] = flags
    return values


def chrono_p3b_values(summary: dict, repo: Path) -> dict[str, dict]:
    """Chrono P3b values per case from ``s9_P3b_summary.json`` (rev-60 re-judge).

    The stroke reading of each case is read from its run folder under the summary's
    ``source_batch``.
    """
    batch_dir = repo / summary["source_batch"]
    return {name: dict(chrono_values_from_p3b_block(row),
                       **stroke_reading_fields(batch_dir / name, repo),
                       version="P3b 10-26 (batch_P3b_20261026_122444), rev-60 re-judge",
                       src="06_analysis/01_chrono/19_S9/s9_P3b_summary.json")
            for name, row in summary["rows"].items()}


def curated_stroke_readings(repo: Path) -> dict[str, dict]:
    """Stroke-reading columns of the curated cases in ``CURATED_RECORD_DIRS`` by harness id."""
    return {harness_id: stroke_reading_fields(repo / CHRONO_RESULTS_REL / batch / case, repo)
            for harness_id, (batch, case) in CURATED_RECORD_DIRS.items()}


def chrono_values_from_g6_judge(case_row: dict) -> dict:
    """Judged values of one ``r76_g6_chrono_judge.py`` case (verdict = all gates pass)."""
    return {
        "verdict": "pass" if case_row["pass"] else "fail",
        "ready_s": case_row["t_ready_rel_s"],
        "min_force_kN": min(case_row["F_min_after_departure_kN"]),
        "max_stroke_true_mm": list(case_row["s_motor_max_mm"]),
        "gap_ready_mm": case_row["rut_min_after_ready_mm"],
        "att_end_absmax_deg": case_row["attitude_p34_absmax_deg"]}


def _verdict_rank(verdict: str | None) -> int:
    return RANK.get(verdict, UNKNOWN_VERDICT_RANK)


def _pair_deltas(harness: dict, chrono: dict) -> dict:
    """Verdict match, Chrono - harness differences and the harness / Chrono min force ratio."""
    deltas: dict = {"verdict_same": harness["verdict"] == chrono["verdict"]}
    for field in COMPARED_FIELDS:
        if harness.get(field) is not None and chrono.get(field) is not None:
            deltas[f"d_{field}"] = round(chrono[field] - harness[field], 3)
    if harness.get("min_force_kN") and chrono.get("min_force_kN"):
        deltas["minF_ratio_h_over_c"] = round(
            harness["min_force_kN"] / chrono["min_force_kN"], 3)
    return deltas


def _largest_magnitude(value):
    """A non-empty per-leg number list counts by its largest magnitude; others pass through."""
    is_number_list = (isinstance(value, list) and value
                      and all(isinstance(item, (int, float)) for item in value))
    return max(abs(item) for item in value) if is_number_list else value


def stroke_censoring(harness: dict | None, chrono: dict) -> dict:
    """Whether the stroke-reading delta of a pair is cut by the lift-stroke guard.

    Returns:
        ``censored_at_guard`` (True / False / None, see ``CENSORING_NOTE``) and
        ``censored_side`` (``"chrono"``, ``"harness"``, ``"both"`` or None).
    """
    chrono_events = chrono.get("stroke_guard_events")
    harness_events = (harness or {}).get("stroke_guard_events")
    guarded_sides = [side for side, events in (("chrono", chrono_events),
                                                ("harness", harness_events)) if events]
    if len(guarded_sides) == 2:
        return {"censored_at_guard": True, "censored_side": "both"}
    if guarded_sides:
        return {"censored_at_guard": True, "censored_side": guarded_sides[0]}
    both_known = chrono_events is not None and harness_events is not None
    return {"censored_at_guard": False if both_known else None, "censored_side": None}


def add_stroke_censoring(pairs: list[dict]) -> None:
    """Set ``censored_at_guard`` / ``censored_side`` on every pair (in place)."""
    for pair in pairs:
        pair.update(stroke_censoring(pair["harness"], pair["chrono"]))


def _side_name(is_optimistic: bool, is_conservative: bool) -> str:
    if is_optimistic and is_conservative:
        return "mixed"
    if is_optimistic:
        return "optimistic"
    if is_conservative:
        return "conservative"
    return "representative"


def classify_pair(harness: dict | None, chrono: dict) -> tuple[str | None, dict]:
    """Side of the harness against Chrono (harness better = optimistic) and the deltas.

    Returns ``(None, {})`` when there is no harness twin or either verdict is missing. List
    values on the Chrono side (per leg) count by their largest magnitude.
    """
    if harness is None or chrono.get("verdict") is None or harness.get("verdict") is None:
        return None, {}
    chrono = {key: _largest_magnitude(value) for key, value in chrono.items()}
    deltas = _pair_deltas(harness, chrono)
    harness_rank = _verdict_rank(harness["verdict"])
    chrono_rank = _verdict_rank(chrono["verdict"])
    ready_delay_s = deltas.get("d_ready_s", 0)
    force_ratio = deltas.get("minF_ratio_h_over_c", 1)
    is_optimistic = (harness_rank < chrono_rank or ready_delay_s > OPTIMISTIC_READY_DELAY_S
                     or force_ratio > OPTIMISTIC_MIN_FORCE_RATIO
                     or deltas.get("d_gap_ready_mm", 0) < OPTIMISTIC_GAP_SHORTFALL_MM)
    is_conservative = (harness_rank > chrono_rank or ready_delay_s < CONSERVATIVE_READY_LEAD_S
                       or force_ratio < CONSERVATIVE_MIN_FORCE_RATIO)
    return _side_name(is_optimistic, is_conservative), deltas


def _p3b_pair(name: str, chrono: dict, all_records: dict[str, dict]) -> dict:
    _, soil, pad, level, friction = name.split("_")
    harness_id = f"base|{soil}|{pad}|{level}|{friction}"
    harness = all_records.get(harness_id)
    side, deltas = classify_pair(harness, chrono)
    if friction != "Fs4":
        variable = "B2 F_s"
    elif level != "top":
        variable = "B1 auger"
    else:
        variable = "A1 soil / B3 pad"
    if soil == "G1":
        version_note = "equivalent to final (no final feature acts)"
    else:
        version_note = "not equivalent (R4 / ZIC / DSb act under the final controller)"
    return {"variable": variable, "chrono_case": name, "harness_id": harness_id,
            "chrono": chrono, "harness": harness, "side": side, "delta": deltas,
            "chrono_version_note": version_note}


def build_pairs(chrono_p3b: dict[str, dict], all_records: dict[str, dict],
                curated: tuple[tuple, ...] = CURATED,
                curated_readings: dict[str, dict] | None = None) -> list[dict]:
    """E1 pairs: the Chrono P3b cases (sorted by name), then the curated spec / paper cases.

    ``curated_readings`` (harness id -> stroke-reading columns, see
    ``curated_stroke_readings``) adds the Chrono stroke reading to those curated cases.
    """
    readings = curated_readings or {}
    pairs = [_p3b_pair(name, chrono, all_records) for name, chrono in sorted(chrono_p3b.items())]
    for variable, case, harness_id, values, version, src in curated:
        chrono = dict(values, **readings.get(harness_id, {}), version=version, src=src)
        harness = all_records.get(harness_id)
        side, deltas = classify_pair(harness, chrono)
        pairs.append({"variable": variable, "chrono_case": case, "harness_id": harness_id,
                      "chrono": chrono, "harness": harness, "side": side, "delta": deltas})
    return pairs


def _repo_rel(path: Path, repo: Path) -> str:
    return path.relative_to(repo).as_posix()


def _rejudge_path(repo: Path, batch: str, case: str) -> Path:
    return repo / CHRONO_RESULTS_REL / batch / case / REJUDGE_FILE_NAME


def _rv2_pair(path: Path, batch: str, case: str, repo: Path,
              all_records: dict[str, dict]) -> dict:
    chrono = dict(chrono_values_from_p3b_block(_load_json(path)["p3b"]),
                  **stroke_reading_fields(path.parent, repo),
                  version=SAME_VERSION, src=_repo_rel(path, repo))
    pair = _p3b_pair(case, chrono, all_records)
    # the 10-26 P3b pair has the same case name: the batch folder tells them apart
    pair["chrono_case"] = f"{case} @ {batch}"
    pair["chrono_version_note"] = "same version as the harness (RV2, spec 432.4.4)"
    return pair


def _rv3_pair(run: dict, chrono: dict, src: str, all_records: dict[str, dict]) -> dict:
    chrono = dict(chrono, note=run["note"], version=SAME_VERSION, src=src,
                  spec=run["src_spec"])
    harness = all_records.get(run["harness_id"])
    side, deltas = classify_pair(harness, chrono)
    return {"variable": run["variable"], "chrono_case": f"{run['case']} @ {run['batch']}",
            "harness_id": run["harness_id"], "chrono": chrono, "harness": harness,
            "side": side, "delta": deltas,
            "chrono_version_note": "same version as the harness (RV3, spec 426.9.F.1)"}


def _find_g6_case(judge_path: Path, case: str) -> dict | None:
    for case_row in _load_json(judge_path)["cases"]:
        if case_row["case"] == case:
            return case_row
    return None


def build_same_version_pairs(repo: Path,
                             all_records: dict[str, dict]) -> tuple[list[dict], list[str]]:
    """RV2 and RV3 pairs (Chrono 05708b2 = harness version) and the missing Chrono inputs.

    A missing result file (or a G6 judge file without the case) drops that pair; its path is
    returned so the output can list it.
    """
    pairs: list[dict] = []
    missing: list[str] = []
    for batch, case in RV2_RUNS:
        path = _rejudge_path(repo, batch, case)
        if path.exists():
            pairs.append(_rv2_pair(path, batch, case, repo, all_records))
        else:
            missing.append(_repo_rel(path, repo))
    slope_path = _rejudge_path(repo, RV3_SLOPE_RUN["batch"], RV3_SLOPE_RUN["case"])
    if slope_path.exists():
        chrono = dict(chrono_values_from_p3b_block(_load_json(slope_path)["p3b"]),
                      **stroke_reading_fields(slope_path.parent, repo))
        pairs.append(_rv3_pair(RV3_SLOPE_RUN, chrono, _repo_rel(slope_path, repo),
                               all_records))
    else:
        missing.append(_repo_rel(slope_path, repo))
    judge_path = repo / RV3_G6_RUN["judge_rel"]
    case_row = _find_g6_case(judge_path, RV3_G6_RUN["case"]) if judge_path.exists() else None
    if case_row is not None:
        g6_dir = repo / CHRONO_RESULTS_REL / RV3_G6_RUN["batch"] / RV3_G6_RUN["case"]
        chrono = dict(chrono_values_from_g6_judge(case_row),
                      **stroke_reading_fields(g6_dir, repo))
        pairs.append(_rv3_pair(RV3_G6_RUN, chrono, RV3_G6_RUN["judge_rel"], all_records))
    else:
        missing.append(f"{RV3_G6_RUN['judge_rel']} (case {RV3_G6_RUN['case']})")
    return pairs, missing


def _final_chrono_values(path: Path, run: dict, repo: Path) -> dict:
    """Judged Chrono values of one final run; a spec verdict replaces the automatic one."""
    chrono = chrono_values_from_p3b_block(_load_json(path)["p3b"])
    chrono.update(stroke_reading_fields(path.parent, repo))
    if "verdict" in run:
        chrono["verdict_auto"] = chrono["verdict"]
        chrono["verdict"] = run["verdict"]
    if "note" in run:
        chrono["note"] = run["note"]
    chrono.update(version=FINAL_VERSION, src=_repo_rel(path, repo), spec=run["spec"])
    return chrono


def _final_pair(run: dict, chrono: dict, final_harness: dict[str, dict[str, dict]]) -> dict:
    harness = final_harness.get(run["harness_key"], {}).get(run["harness_id"])
    if harness is not None:
        harness = dict(harness, source=run["harness_key"])
    side, deltas = classify_pair(harness, chrono)
    pair = {"variable": run["variable"], "chrono_case": f"{run['case']} @ {run['batch']}",
            "harness_id": run["harness_id"], "chrono": chrono, "harness": harness,
            "side": side, "delta": deltas,
            "chrono_version_note": "same version as the harness (final controller, spec "
                                   "432.4.5)"}
    if "superseded_by" in run:
        pair["superseded_by"] = run["superseded_by"]
    return pair


def build_final_pairs(repo: Path, final_harness: dict[str, dict[str, dict]],
                      runs: tuple[dict, ...] = FINAL_RUNS) -> tuple[list[dict], list[str]]:
    """Final-controller pairs (``FINAL_RUNS``) and the missing Chrono / harness inputs.

    A missing ``result_rejudge_rev60.json`` drops the pair; a missing harness twin keeps the
    pair without a side. Both are returned as ``missing`` entries.
    """
    pairs: list[dict] = []
    missing: list[str] = []
    for run in runs:
        path = _rejudge_path(repo, run["batch"], run["case"])
        if not path.exists():
            missing.append(_repo_rel(path, repo))
            continue
        pair = _final_pair(run, _final_chrono_values(path, run, repo), final_harness)
        if pair["harness"] is None:
            missing.append(f"harness {run['harness_key']}: {run['harness_id']}")
        pairs.append(pair)
    return pairs, missing


def _delta_stats(pairs: list[dict], delta_key: str) -> dict:
    """n / min / max / mean of one delta over the pairs that have it (empty when none do)."""
    deltas = [pair["delta"][delta_key] for pair in pairs if delta_key in pair["delta"]]
    if not deltas:
        return {}
    return {"n": len(deltas), "min": min(deltas), "max": max(deltas),
            "mean": round(sum(deltas) / len(deltas), 2)}


def summarize_pairs(pairs: list[dict]) -> dict:
    """Pair counts, side counts per variable (first two words), READY and stroke differences."""
    side_count: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for pair in pairs:
        words = pair["variable"].split(" ")
        side_count[f"{words[0]} {words[1]}"][pair["side"] or "no_twin"] += 1
    uncensored = [pair for pair in pairs if pair.get("censored_at_guard") is not True]
    return {"n_pairs": len(pairs),
            "n_with_harness": sum(pair["harness"] is not None for pair in pairs),
            "verdict_same": sum(bool(pair["delta"].get("verdict_same")) for pair in pairs),
            "by_variable_side": {key: dict(value) for key, value in side_count.items()},
            "d_ready_s_chrono_minus_harness": _delta_stats(pairs, "d_ready_s"),
            "d_max_stroke_reading_mm_chrono_minus_harness": _delta_stats(
                pairs, "d_max_stroke_reading_mm"),
            "d_max_stroke_reading_mm_uncensored": _delta_stats(
                uncensored, "d_max_stroke_reading_mm"),
            "censored_stroke_reading": censored_stroke_readings(pairs)}


def censored_stroke_readings(pairs: list[dict]) -> list[dict]:
    """Pairs whose reading delta is cut by the guard: case, guarded side and the delta."""
    return [{"chrono_case": pair["chrono_case"], "censored_side": pair.get("censored_side"),
             "d_max_stroke_reading_mm": pair["delta"].get("d_max_stroke_reading_mm")}
            for pair in pairs if pair.get("censored_at_guard") is True]


def missing_stroke_records(pairs: list[dict]) -> list[str]:
    """Record files named by a pair whose Chrono stroke reading could not be read."""
    return [pair["chrono"]["stroke_record"] for pair in pairs
            if "stroke_record" in pair["chrono"]
            and pair["chrono"].get("max_stroke_reading_mm") is None]


def summarize_final_pairs(final_pairs: list[dict]) -> dict:
    """``summarize_pairs`` over the final pairs that are not superseded by a later run.

    A superseded pair is the same harness twin judged on an earlier run; counting it as well
    would count the pair twice. It is listed in ``superseded`` instead.
    """
    counted = [pair for pair in final_pairs if "superseded_by" not in pair]
    summary = summarize_pairs(counted)
    summary["superseded"] = [
        {"chrono_case": pair["chrono_case"], "superseded_by": pair["superseded_by"]}
        for pair in final_pairs if "superseded_by" in pair]
    return summary


def _combined_counts(summary: dict, final_summary: dict) -> dict:
    return {key: summary[key] + final_summary[key]
            for key in ("n_pairs", "n_with_harness", "verdict_same")}


def build_pairs_payload(pairs: list[dict], files: dict[str, Path], repo: Path,
                        missing_chrono: list[str], final_pairs: list[dict] | None = None,
                        missing_final: list[str] | None = None) -> dict:
    """E1 output (``harness_chrono_pairs.json``); sets the censoring fields of all pairs."""
    final_pairs = final_pairs or []
    add_stroke_censoring(pairs)
    add_stroke_censoring(final_pairs)
    meta = {"spec": "432.4 E1 (control 2026-10-30; final pairs 432.4.5, 2026-10-31)",
            "script": SCRIPT_REL,
            "script_sha256": _script_sha256(), "schema_version": PAIRS_SCHEMA_VERSION,
            "schema_change": PAIRS_SCHEMA_CHANGE, "stroke_quantities": STROKE_QUANTITY_NOTE,
            "censoring": CENSORING_NOTE,
            "harness_files": {key: str(path.relative_to(repo)) for key, path in files.items()},
            "final_harness_files": {key: str(path.relative_to(repo))
                                    for key, path in final_harness_files(repo).items()},
            "classification": PAIRS_CLASSIFICATION, "version_caveat": PAIRS_VERSION_CAVEAT,
            "final_pairs_note": FINAL_PAIRS_NOTE, "final_pending_runs": list(FINAL_PENDING_RUNS),
            "h6_margin": H6_MARGIN_NOTE, "missing_chrono_inputs": missing_chrono,
            "missing_final_inputs": missing_final or [],
            "missing_stroke_records": missing_stroke_records(pairs + final_pairs)}
    summary = summarize_pairs(pairs)
    final_summary = summarize_final_pairs(final_pairs)
    return {"meta": meta, "summary": summary, "pairs": pairs,
            "final_summary": final_summary, "final_pairs": final_pairs,
            "combined_counts": _combined_counts(summary, final_summary),
            "static_pairs": STATIC_RIGID}


# ---------------------------------------------------------------------------- E5: monotonicity
def _metric_value(record: dict, metric: str):
    if metric == "rank":
        return _verdict_rank(record["verdict"])
    return record.get(metric)


def _direction(delta: float, tolerance: float) -> str:
    if delta > tolerance:
        return "up"
    if delta < -tolerance:
        return "down"
    return "flat"


def _is_monotone(sequence: list, tolerance: float) -> bool:
    """Non-strict monotone: every step is within ``tolerance`` of one direction."""
    steps = [after - before for before, after in zip(sequence, sequence[1:], strict=False)]
    return all(step >= -tolerance for step in steps) or all(step <= tolerance for step in steps)


def monotonicity_study(name: str, groups: dict[str, dict], levels: list[str]) -> dict:
    """Per metric the direction from ``levels[0]`` to ``levels[-1]`` and the monotone count.

    Args:
        name: Study label (independent variable and data set).
        groups: ``{group key: {level: record}}``; groups missing a level are skipped, and a
            metric is skipped for a group when any level lacks it.
        levels: Levels of the independent variable in order.
    """
    result = {"variable": name, "levels": levels, "n_groups": 0, "metrics": {},
              "verdict_changes": [], "verdict_change_counts": {}, "verdict_counts": {},
              "non_monotone": []}
    stats = {m: {"up": 0, "down": 0, "flat": 0, "monotone": 0, "n": 0} for m in METRICS}
    verdict_counts: dict[str, dict[str, int]] = {level: defaultdict(int) for level in levels}
    for group, by_level in sorted(groups.items()):
        if not all(level in by_level for level in levels):
            continue
        result["n_groups"] += 1
        verdicts = [by_level[level]["verdict"] for level in levels]
        for level, verdict in zip(levels, verdicts, strict=True):
            verdict_counts[level][str(verdict)] += 1
        if len(set(verdicts)) > 1:
            result["verdict_changes"].append({"group": group, "verdicts": verdicts})
        for metric in METRICS:
            sequence = [_metric_value(by_level[level], metric) for level in levels]
            if any(value is None for value in sequence):
                continue
            tolerance = METRIC_TOLERANCE[metric]
            metric_stats = stats[metric]
            metric_stats["n"] += 1
            metric_stats[_direction(sequence[-1] - sequence[0], tolerance)] += 1
            is_monotone = _is_monotone(sequence, tolerance)
            metric_stats["monotone"] += is_monotone
            if not is_monotone:
                result["non_monotone"].append(
                    {"group": group, "metric": metric, "seq": [round(v, 2) for v in sequence]})
    result["metrics"] = stats
    result["verdict_change_counts"] = count_verdict_change_directions(result["verdict_changes"])
    result["verdict_counts"] = {level: dict(counts) for level, counts in verdict_counts.items()}
    return result


def count_verdict_change_directions(verdict_changes: list[dict]) -> dict[str, int]:
    """Verdict changes counted by the rank of the last level against the first.

    ``worse`` = higher rank at the last level, ``better`` = lower, ``same_ends`` = the ends
    agree (the verdict changed in between only).
    """
    counts = {"worse": 0, "better": 0, "same_ends": 0}
    for change in verdict_changes:
        first_rank = _verdict_rank(change["verdicts"][0])
        last_rank = _verdict_rank(change["verdicts"][-1])
        if last_rank > first_rank:
            counts["worse"] += 1
        elif last_rank < first_rank:
            counts["better"] += 1
        else:
            counts["same_ends"] += 1
    return counts


def group_p3b_by_part(p3b: dict[str, dict], part_index: int) -> dict[str, dict]:
    """Group the flat P3b rows ``base|soil|pad|level|Fs`` by all parts except one.

    The excluded part (index into the ``|`` split, 1..4) becomes the level key.
    """
    groups: dict[str, dict] = defaultdict(dict)
    for record_id, record in p3b.items():
        parts = record_id.split("|")
        if len(parts) != 5 or parts[0] != "base":
            continue
        key = "|".join(part for i, part in enumerate(parts) if i not in (0, part_index))
        groups[key][parts[part_index]] = record
    return groups


def _p3b_studies(p3b: dict[str, dict]) -> list[dict]:
    return [
        monotonicity_study("B2 F_s (p3b flat)", group_p3b_by_part(p3b, 4),
                           ["Fs0", "Fs4", "Fs8"]),
        monotonicity_study("B1 auger (p3b flat)", group_p3b_by_part(p3b, 3),
                           ["top", "middle", "bottom"]),
        monotonicity_study("B3 pad A -> B (p3b flat)", group_p3b_by_part(p3b, 2), ["A", "B"]),
        monotonicity_study("A1 soil G1 -> J1 -> J2 -> S1 (p3b flat)",
                           group_p3b_by_part(p3b, 1), ["G1", "J1", "J2", "S1"]),
    ]


def group_slope_by_ratio(slope: dict[str, dict]) -> dict[str, dict]:
    """A2 slope ratio k per (soil, pad, level, direction).

    Levels: ``k0`` = the H1 flat row, ``k<k>`` = the H3 ``<direction>@k<k>`` rows,
    ``k1.0`` = the H1 direction row.
    """
    flat = {}
    for record_id, record in slope.items():
        parts = record_id.split("|")
        if parts[4] == "flat":
            flat[(parts[1], parts[2], parts[3])] = record
    groups: dict[tuple, dict] = defaultdict(dict)
    for record_id, record in slope.items():
        parts = record_id.split("|")
        family, soil, pad, level, direction = parts[0], parts[1], parts[2], parts[3], parts[4]
        if family == "H3" and "@k" in direction:
            base_direction, ratio = direction.split("@k")
            groups[(soil, pad, level, base_direction)][f"k{ratio}"] = record
        elif family == "H1" and direction != "flat":
            groups[(soil, pad, level, direction)]["k1.0"] = record
    for (soil, pad, level, _direction_name), by_level in groups.items():
        if (soil, pad, level) in flat:
            by_level["k0"] = flat[(soil, pad, level)]
    return {"|".join(key): value for key, value in groups.items()}


def group_h9_by_ratio(h9: dict[str, dict]) -> tuple[dict[str, dict], list[str]]:
    """H9 rows ``H9|soil|pad|level|<direction>@k<k>`` per (soil, pad, level, direction).

    Returns:
        The groups (level ``k<k>``) and the levels of all groups in ascending k.
    """
    groups: dict[str, dict] = defaultdict(dict)
    ratio_texts: set[str] = set()
    for record_id, record in h9.items():
        _, soil, pad, level, direction = record_id.split("|")
        base_direction, ratio_text = direction.split("@k")
        groups["|".join((soil, pad, level, base_direction))][f"k{ratio_text}"] = record
        ratio_texts.add(ratio_text)
    levels = [f"k{text}" for text in sorted(ratio_texts, key=float)]
    return dict(groups), levels


def group_slope_by_pad(slope: dict[str, dict]) -> dict[str, dict]:
    """Slope rows keyed by (family, soil, level, direction) with the pad as level."""
    groups: dict[tuple, dict] = defaultdict(dict)
    for record_id, record in slope.items():
        parts = record_id.split("|")
        groups[(parts[0], parts[1], parts[3], parts[4])][parts[2]] = record
    return {"|".join(key): value for key, value in groups.items()}


def _slope_studies(slope: dict[str, dict]) -> list[dict]:
    by_ratio = group_slope_by_ratio(slope)
    return [
        monotonicity_study("A2 slope ratio k (slope 177)", by_ratio,
                           ["k0", "k0.5", "k0.75", "k0.875", "k1.0"]),
        monotonicity_study("A2 slope ratio k (no k0.875 rows)", by_ratio,
                           ["k0", "k0.5", "k0.75", "k1.0"]),
        monotonicity_study("B3 pad A -> B (slope 177)", group_slope_by_pad(slope), ["A", "B"]),
    ]


def pair_with_slope(variant: dict[str, dict], suffix: str, slope: dict[str, dict],
                    level_names: list[str]) -> dict[str, dict]:
    """x426 B: id = slope id + ``|<suffix>``; pair each with its slope Fs4 / top record.

    Middle-auger ids (and the ``mid`` set) also try the slope id with ``|top|``.
    """
    groups = {}
    for record_id, record in variant.items():
        candidates = []
        if record_id.endswith("|" + suffix):
            candidates.append(record_id.rsplit("|", 1)[0])
        if suffix == "mid" or "middle" in record_id:
            candidates.append(record_id.replace("|middle|", "|top|"))
        for base_id in candidates:
            if base_id and base_id in slope:
                groups[base_id] = {level_names[0]: slope[base_id], level_names[1]: record}
                break
    return groups


def _x426_b_studies(harness: dict[str, dict], slope: dict[str, dict]) -> list[dict]:
    specs = [  # (harness key, id suffix, study name, levels)
        ("B_Fs0", "Fs0", "B2 F_s 4 -> 0 on slope (x426 B2)", ["Fs4", "Fs0"]),
        ("B_Fs8", "Fs8", "B2 F_s 4 -> 8 on slope (x426 B3)", ["Fs4", "Fs8"]),
        ("B_mid", "mid", "B1 auger top -> middle on slope (x426 B4)", ["top", "middle"]),
        ("B_m1p1", "m1.1", "B4 weight 1.0 -> 1.1 on slope (x426 B1)", ["m1.0", "m1.1"]),
    ]
    studies = []
    for key, suffix, name, levels in specs:
        groups = pair_with_slope(harness.get(key, {}), suffix, slope, levels)
        studies.append(monotonicity_study(name, groups, levels))
    return studies


def group_h6_by_weight(h6: dict[str, dict]) -> dict[str, dict]:
    """H6 flat rows by case; the ``m<scale>`` suffix is the level (no suffix = ``m1.0``)."""
    groups: dict[str, dict] = defaultdict(dict)
    for record_id, record in h6.items():
        parts = record_id.split("|")
        if parts[-1].startswith("m"):
            groups["|".join(parts[1:-1])][parts[-1]] = record
        else:
            groups["|".join(parts[1:])]["m1.0"] = record
    return groups


def group_start_gap(d_results: dict[str, dict]) -> dict[str, dict]:
    """x426 D per (soil, leg, sign) over the start gap; level ``0`` = the no-gap reference.

    Ids with a sixth part ``<leg>:<g|d><mm>`` are gap runs; the first five parts are the
    reference id. Bump groups (``g``) list g110 / g55 / g20, dip groups list d60 / d150; a
    level absent from the data is stored as ``None``.
    """
    groups: dict[tuple, dict] = defaultdict(dict)
    for record_id, record in d_results.items():
        parts = record_id.split("|")
        if len(parts) != 6:
            continue
        leg, gap = parts[5].split(":")
        key = (parts[1], leg, gap[0])
        groups[key][gap] = record
        groups[key]["0"] = d_results.get("|".join(parts[:5]))
    by_key = {}
    for key, by_level in groups.items():
        present = {level: record for level, record in by_level.items() if record is not None}
        if key[2] == "g":
            wanted = ("0", "g110", "g55", "g20")
        else:
            wanted = ("0", "d60", "d150")
        by_key["|".join(key)] = {level: present.get(level) for level in wanted}
    return by_key


def group_soft_patch_pad(c_results: dict[str, dict], g6: dict[str, dict]) -> dict[str, dict]:
    """x426 C pad-A runs (``<g6 key>|PA``) paired with the R2DS g6 pad-B run."""
    groups = {}
    for record_id, record in c_results.items():
        if record_id.endswith("|PA"):
            base_id = record_id[:-3]
            if base_id in g6:
                groups[base_id] = {"B": g6[base_id], "A": record}
    return groups


def _non_planar_studies(harness: dict[str, dict]) -> list[dict]:
    gap_groups = group_start_gap(harness["D"])
    bump = {key: value for key, value in gap_groups.items() if "g20" in value}
    dip = {key: value for key, value in gap_groups.items() if "d150" in value}
    return [
        monotonicity_study("A3 bump (start gap 110 -> 20 mm, x426 D)", bump,
                           ["0", "g110", "g55", "g20"]),
        monotonicity_study("A3 dip (60 -> 150 mm, x426 D)", dip, ["0", "d60", "d150"]),
        monotonicity_study("B3 pad B -> A on soft patch (x426 C vs g6)",
                           group_soft_patch_pad(harness["C"], harness["g6"]), ["B", "A"]),
    ]


def build_studies(harness: dict[str, dict[str, dict]]) -> list[dict]:
    """All E5 studies in output order.

    Raises:
        KeyError: A required harness table (p3b, slope, h6, D, C, g6) was not loaded. The
            x426 B tables are optional (their studies then have no groups); the H9 study is
            added only when an ``H9`` table has rows.
    """
    slope = harness["slope"]
    studies = _p3b_studies(harness["p3b"])
    studies += _slope_studies(slope)
    if harness.get("H9"):
        h9_groups, h9_levels = group_h9_by_ratio(harness["H9"])
        studies.append(monotonicity_study("A2 roll ratio k fine (h9)", h9_groups, h9_levels))
    studies += _x426_b_studies(harness, slope)
    studies.append(monotonicity_study("B4 weight m1.0 -> m1.1 -> m1.2 (h6 flat)",
                                      group_h6_by_weight(harness["h6"]),
                                      ["m1.0", "m1.1", "m1.2"]))
    studies += _non_planar_studies(harness)
    for study in studies:
        study["non_monotone"] = study["non_monotone"][:NON_MONOTONE_LIST_LIMIT]
    return studies


def build_monotonicity_payload(studies: list[dict], files: dict[str, Path] | None = None,
                               repo: Path | None = None,
                               unassigned_x426b: list[str] | None = None) -> dict:
    """E5 output (``harness_monotonicity.json``).

    Args:
        studies: ``build_studies`` output.
        files: E5 harness files (``e5_harness_files``), listed relative to ``repo``.
        repo: Repository root of ``files``.
        unassigned_x426b: x426 B ids of no variant table (``final_e5_tables``).
    """
    harness_files_rel = {}
    if files is not None and repo is not None:
        harness_files_rel = {key: _repo_rel(path, repo) for key, path in files.items()}
    meta = {"spec": "432.4 E5 (control 2026-10-30; final inputs 2026-10-31)",
            "script": SCRIPT_REL, "script_sha256": _script_sha256(),
            "schema_change": MONOTONICITY_SCHEMA_CHANGE, "rank": RANK,
            "tolerance": MONOTONICITY_TOLERANCE_NOTE, "harness": E5_HARNESS_NOTE,
            "harness_files": harness_files_rel,
            "unassigned_x426b": list(unassigned_x426b or [])}
    return {"meta": meta, "studies": studies}


# ---------------------------------------------------------------------------- entry point
def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


def _print_digest(pairs_payload: dict, studies: list[dict]) -> None:
    """Console digest (ASCII)."""
    summary = pairs_payload["summary"]
    print("E1 pairs", summary["n_pairs"], "with harness", summary["n_with_harness"],
          "verdict same", summary["verdict_same"], "dREADY",
          summary["d_ready_s_chrono_minus_harness"])
    final_summary = pairs_payload["final_summary"]
    print("E1 final pairs", final_summary["n_pairs"], "verdict same",
          final_summary["verdict_same"], "dREADING",
          final_summary["d_max_stroke_reading_mm_chrono_minus_harness"])
    for pair in pairs_payload["pairs"] + pairs_payload["final_pairs"]:
        harness = pair["harness"] or {}
        print(f"  {pair['variable'][:34]:34s} {pair['chrono_case'][:34]:34s} "
              f"side={pair['side']} C={pair['chrono'].get('verdict')}"
              f" H={harness.get('verdict')} cens={pair['censored_at_guard']}"
              f" d={json.dumps(pair['delta'])[:150]}")
    for study in studies:
        metric_text = " ".join(
            f"{name}:u{s['up']}/d{s['down']}/f{s['flat']}/mono{s['monotone']}of{s['n']}"
            for name, s in study["metrics"].items())
        change_counts = study["verdict_change_counts"]
        print(f"E5 {study['variable'][:48]:48s} groups={study['n_groups']:3d} "
              f"vchg={len(study['verdict_changes']):2d} (worse {change_counts['worse']} "
              f"better {change_counts['better']}) " + metric_text)


def main(argv: list[str]) -> None:
    repo = Path(argv[1]) if len(argv) > 1 else ROOT
    out_dir = Path(argv[2]) if len(argv) > 2 else DEFAULT_OUT_DIR
    files = harness_files(repo)
    harness = load_harness(files)
    chrono_p3b = chrono_p3b_values(_load_json(repo / P3B_SUMMARY_REL), repo)
    all_records = merge_by_id(harness)
    pairs = build_pairs(chrono_p3b, all_records,
                        curated_readings=curated_stroke_readings(repo))
    same_version_pairs, missing_chrono = build_same_version_pairs(repo, all_records)
    pairs += same_version_pairs
    for path in missing_chrono:
        print("missing Chrono input (pair skipped):", path)
    final_harness = load_harness(final_harness_files(repo))
    final_pairs, missing_final = build_final_pairs(repo, final_harness)
    for path in missing_final:
        print("missing final input:", path)
    pairs_payload = build_pairs_payload(pairs, files, repo, missing_chrono,
                                        final_pairs, missing_final)
    for path in pairs_payload["meta"]["missing_stroke_records"]:
        print("missing Chrono stroke record (no reading comparison):", path)
    out_dir.mkdir(parents=True, exist_ok=True)
    # E1 is written before E5 is built, as in the scratchpad original
    _write_json(out_dir / PAIRS_FILE_NAME, pairs_payload)
    e5_files = e5_harness_files(repo)
    e5_tables, unassigned_x426b = final_e5_tables(e5_files)
    studies = build_studies(e5_tables)
    _write_json(out_dir / MONOTONICITY_FILE_NAME,
                build_monotonicity_payload(studies, e5_files, repo, unassigned_x426b))
    _print_digest(pairs_payload, studies)


if __name__ == "__main__":
    main(sys.argv)
