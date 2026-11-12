"""Path 2 (independent) Chrono judgement for 436.8 C-1..C-5: rule constants and seal checks.

Every constant cites the sentence it was taken from. Nothing here was taken from a
path 1 tool (resume4368_judge.py, u3_judge_k1.py, resume_k1_*.py, run_S9 / run_S8C /
run_S6C judgement functions). See README.md for the read list.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

REPO_MARKER = "02_params/rexome33.yaml"

# --- sealed documents (rules 9019b405 1.2 / Appendix A, rev1 header) -----------------
# (relative path, expected sha256 of the LF file, role)
SEALED = [
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules.md",
     "9019b405b7a196f28a756e7ca91f443f6241a58bd8e1eee0361483066cb19524", "rules (original)"),
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev1.md",
     "d9094fda104e25ac7eb7aea44d7c34d8215a839fc3771aa50b224d43082f02c7", "rules rev1"),
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev2.md",
     "497e4614d6780c3201027b3946e3c21da05e2fefe9a3609436bc35ea664c3199", "rules rev2"),
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev3.md",
     "dad8dfa68da7a988971f4d687706465289ec7dd95d09079c92215c64e5eae557", "rules rev3"),
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev4.md",
     "7ea87a30b08a00263c597d42d3450dc56f68952e8d3205604cb2c5bab5dce14b", "rules rev4 (wins)"),
    ("06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev7.md",
     "9ccde7a5a4128317ed832dd2f92cd2368280f18cefa6827f1b1731c6d4e9aab3", "Appendix A: v5 rev7 (T4 / T5 E, B1, tool regression)"),
    ("06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev8.md",
     "c6ec89f71c1d8de4c06000568c2e5978fd7f9fe58a53defea728f2f4886bb25f", "Appendix A: v5 rev8 (J-P3 3.2)"),
    ("06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev9.md",
     "3c50dda50ca6dca60177f26d91d86c009eeb4f9321f5ffd0c98ddc27cf62e981", "Appendix A: v5 rev9 (J-P3 table)"),
    ("06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev2.md",
     "e120474b8ebd721e6edc4fec8eef811ce810006b8c489e38cecbb7ae5caeed77", "Appendix A: v5 rev2 (J11 D-1)"),
    ("06_analysis/02_control/verif_matrix/d1_selection_rules.md",
     "51dea528e57fa0c4378cda110addb73da20339535e16189452af2d06b60736e9", "Appendix A: D-1 rules 11"),
    ("06_analysis/02_control/verif_matrix/d1_selection_rules_rev1.md",
     "eb730bddae35e76bc2569503605dea714b066fa42de7bc7b98efdde3edb3e868", "Appendix A: D-1 rules rev1"),
    ("06_analysis/02_control/verif_matrix/las_p5r4_k1_judgement.md",
     "5e9fb33b7419d624d8dc305ad93121be090802cc5c85ea29fbc823e019fc9e2f", "Appendix A: P5r4 judgement (R2-5 source, not opened)"),
    ("06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev6.md",
     "fd5117031ef460cf4c6aa74807b2e73de984b014abb89a952b593499841da39c", "Appendix A: v5 rev6 (t_lift, J11)"),
    ("06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev12.md",
     "e02d63cc1290383ee85d9a1f3a20c6348224b60999cccaf8d587cf610c5f5eb2", "Appendix A: v5 rev12 (C-5 rows)"),
    ("06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev12a.md",
     "e171141dce180fbb48493b9b95503ff3577d16f17cc54061ce3ad6e9efd51458", "Appendix A: v5 rev12a"),
    ("06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev12b.md",
     "0d17f87e9532d558efcab9fa89648e2790ece9c7568a802fbaa4c7631824e75d", "Appendix A: v5 rev12b"),
]
# Read but not sealed (living documents): sha recorded in the output only.
RECORDED = [
    "00_docs/04_control/s6_control_spec.md",
    "02_params/rexome33.yaml",
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


RAW_ONLY = {  # rev2 R2-9 last-but-one bullet: sealed rule files are compared raw only
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev1.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev2.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev3.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev4.md",
}


def seal_check(repo: Path) -> dict:
    """Seal check (rules 8.2 S-1, rev2 R2-9). Raw sha must match; for Appendix A files,
    if only CRLF differs and the LF-normalised sha matches, pass and disclose
    ("CRLF 변환만 다름"). The three 436.8 rule files are compared raw only."""
    rows = []
    ok = True
    for rel, want, role in SEALED:
        p = repo / rel
        if not p.exists():
            rows.append({"file": rel, "role": role, "status": "missing"})
            ok = False
            continue
        raw = p.read_bytes()
        got = sha256_bytes(raw)
        if got == want:
            rows.append({"file": rel, "role": role, "status": "match", "sha256": got})
            continue
        lf = raw.replace(b"\r\n", b"\n")
        got_lf = sha256_bytes(lf)
        if got_lf == want and rel not in RAW_ONLY:
            rows.append({"file": rel, "role": role, "status": "match_after_lf_normalisation",
                         "note": "CRLF 변환만 다름", "sha256_raw": got, "sha256_lf": got_lf})
            continue
        rows.append({"file": rel, "role": role, "status": "mismatch", "sha256_raw": got,
                     "sha256_lf": got_lf, "expected": want})
        ok = False
    rec = []
    for rel in RECORDED:
        p = repo / rel
        rec.append({"file": rel, "sha256": sha256_bytes(p.read_bytes()) if p.exists() else None})
    return {"ok": ok, "sealed": rows, "recorded": rec}


# --- numbers (rules 7.6 + the original rule sentences) ----------------------------------
LEGS = ("FL", "FR", "RL", "RR")
CMP_TOL = 1e-9  # rules 7.6 last bullet: threshold comparison tolerance (in the quantity's unit)


def ge(v, x):  # "v >= X" true when v >= X - 1e-9
    return v >= x - CMP_TOL


def lt(v, x):  # "v < X" true when v < X - 1e-9
    return v < x - CMP_TOL


def gt(v, x):  # "v > X" true when v > X + 1e-9
    return v > x + CMP_TOL


def le(v, x):  # "v <= X" : read as not (v > X)
    return not gt(v, x)


# spec 3 (S6 items) / d1 11 H-R-0 "D8.P"
D8_LAST_WINDOW_S = 5.0          # spec 3: "마지막 5 s = 첫 READY 뒤 정지 구간의 끝 5 s"
D8_MOUNT_DEG = 0.02             # spec 3 item 2: "+ 장착 몫 0.02° <= 0.2°"
ATT_LIMIT_DEG = 0.2             # spec 3 item 2, spec 284 P3-4
MOVING_BAR = 180.0              # d1 11 "이동 <= 180 bar" (spec 3 item 4)
LOCKED_BAR = 350.0              # d1 11 "잠김 <= 350 bar"
READY_FLAT_S = 90.0             # d1 11 H-R "READY 평지 90 / 경사 120 s"
READY_SLOPE_S = 120.0
MOVING_U_EPS = CMP_TOL          # rev3 R3-G10 Q-13: moving = applied command != 0 (7.6 tolerance 1e-9 m/s)
# spec 210.2 R40-2 (rigid NSC crawler hold)
HOLD_WINDOW_S = 8.0             # "그 최소가 이륙 뒤 8 s 안"
HOLD_SLOW_MEAN_S = 1.0          # R40-1 "느린 성분(1 s 중심 평균)"
HOLD_SLOW_MARGIN_N = 5000.0     # rev3 R3-G6: threshold = F_min + 5 kN (= 14,414.589 N)

# spec 284 P3 / 284.1 / 423.3 / 419.8 / 424.8.1 / 433.6
W_FRACTION = 0.01               # P3-2 "< 0.01 W", recontact ">= 0.01 W" (393)
DEPART_HOLD_S = 0.1             # P3-2 "t_D = ... < 0.01 W가 0.1 s 이어진 구간의 시작"
P32_SLACK_S = 1.0               # P3-2 "10 mm/(0.25 v_max) + 1.0 s = 2.9 s"
P32_WINDOW_M = 0.010
P32_SPEED_FRACTION = 0.25
P32_RULE_VALUE_S = 2.9          # the rounded value written in the rule (recorded next to the formula)
READY_WINDOW_S = 10.0           # P3-1 "READY ~ READY + 10 s"
TRANSIENT_MAX_S = 0.5           # U-S9-G6d (가): "지속 <= 0.5 s, LOC 전에 끝남, 최대 <= 0.15 W"
TRANSIENT_MAX_W = 0.15
CHATTER_AFTER_LOC_S = 1.0       # 423.3 Q-G
CHATTER_MAX_S = 0.1
CHATTER_MAX_OVER = 1.2
CREEP_RATE_WINDOW_S = 1.0       # 433.6 (v5): "침하율 창 0.2 s -> 1.0 s"
CREEP_STOP_M_S = 1e-4           # 284.1: "|0.2 s 후향 침하 속도| < 0.1 mm/s"
P34_WINDOW_MIN_S = 5.0          # 284.1: "길이 >= 5 s"
CLEARANCE_MIN_M = 0.025         # P3-5 ">= 25 mm"
STROKE_END_M = 0.6848           # P3-5 "모터 행정 <= 0.6848 m"; d1 1 s_end
G6_READY_S = 120.0              # spec 17475 "G6 Chrono 판정기(G6-1~G6-7, READY <= 120 s)"
# rev3 R3-G8: 377 demotion threshold = F_min (17279 "14.4 kN" not used)
LOC_CYCLE_S = 0.1               # 419.8.1 "(t_LOC - 0.1 s, t_LOC]"

# rev2 R2-5 / 7.4 (record windows)
FMIN_REC_WINDOW_S = 8.0         # R2-5 "기록 창 = [t_D, t_D + 8 s]"
FMIN_PLUS_N = 2000.0            # 7.4 / R2-5 "F < F_min + 2000 N"
# rules 2 / 5.4 (R_c)
RC_PHI_DEG = 4.4                # R_c = |phi_c|/4.4 + |theta_c|/3.2
RC_THETA_DEG = 3.2

# rev6 5 / 6 (C-5)
TLIFT_SKIP_PHASES = ("idle", "check", "touch")

EVENT_LOC = "crawler_liftoff_confirmed"
EVENT_LOC_REVOKED = "INFO_LOC_REVOKED"
EVENT_REAPPROACH_START = "leg_reapproach_start"
EVENT_REAPPROACH_CONTACT = "leg_reapproach_contact"
EVENT_REAPPROACH_NO_CONTACT = "WARN_LEG_REAPPROACH_NO_CONTACT"
EVENT_LOC_WINDOW_RESTART = "INFO_LOC_WINDOW_RESTART"
EVENT_P38 = ("leg_reapproach_start", "relevel_predicted", "probe_aborted_low_load")
EVENT_DEFERRED = "leg_reapproach_deferred"
EVENT_STROKE_LIMITED = "WARN_LIFT_STROKE_LIMITED"
EVENT_STROKE_STOP = "FAULT_LIFT_STROKE_LIMIT"
FAULT_PHASES = ("fault", "fault_reground")
