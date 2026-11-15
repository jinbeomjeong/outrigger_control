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
     "7ea87a30b08a00263c597d42d3450dc56f68952e8d3205604cb2c5bab5dce14b", "rules rev4"),
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev5.md",
     "452a8436c547e4da8d78205556cbb37633842d42cb98c18849cb883d827b3aca", "rules rev5"),
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev6.md",
     "809e563971ea451aba7c9d0787c660bdcab1c495af39c513c8f158e09b4fe6c9", "rules rev6"),
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev7.md",
     "e81f7d31779b0d69a140c9d90aa4684f3c9299e84aec6af06b13d48d58631502", "rules rev7"),
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev8.md",
     "3ecafaaf33d84bb6f34a8cef5401771832a4999e4930f3644caff56eed640e56", "rules rev8"),
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev9.md",
     "4cf7843ce469df511d7b99c7236f0b245afae9fb4ba5ad903e1c2da823a59a6d", "rules rev9"),
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev10.md",
     "62a0bd8dd6644f78bf37d052e884061d8c14e1cc96e2babc72a6ac0618f12c29", "rules rev10"),
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev11.md",
     "9bac452470faf74f921aa7474b3dabad781dac1ba6c3493aff998e69e430617f", "rules rev11"),
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev12.md",
     "78f1f99b1bb27473d6e3317c58af195cc3b477829ca1439f390aeeaf32565140", "rules rev12"),
    # rev15 R15-7: the two Chrono judgement tools add rev15 (rev13 / rev14 stay out of the tool lists,
    # R13-7 / R14-7; they are checked by tools/verif/seal_check.py). Sealed 2026-11-15 00:08:30 +09:00,
    # seal commit S3 cc0d9b8. Being in this list also turns on the D-29 L2b 10 Hz reading (R15-3).
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev15.md",
     "0162561c3866412f06ef3be0b3a62434e4a9ba5a37c9003be4df2f373af545ef", "rules rev15"),
    # rev18 R18-1 (다) / order 2: the Chrono judgement tools add rev16..rev18 (both paths the same). Seal sha
    # = first token of each `.sha256` (rev16 sealed 2026-11-15 09:58:22, rev17 10:51:35, rev18 14:28:43 +09:00).
    # The latest sealed revision wins over the earlier ones (rev18 S-01..04 / PS-c completion, R18-2 / R18-3).
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev16.md",
     "b38991943a565a020488d1046dd6e0b5c71276cf925715fa5ba844d8819d0683", "rules rev16"),
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev17.md",
     "9400660e2f228c3bdfaf26b1eb36cf08a753e7ebc49fbcdedc4a8ab4e0b92422", "rules rev17"),
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev18.md",
     "3693a69c3f04eb6c5b26556ec5997d081e38f8f6fa6a581aee66ba512d122a9e", "rules rev18"),
    # rev19 R19-8 order 2: rev16..rev19 in the Chrono tool lists (sealed 2026-11-15, S7 38897f0); rev19 wins.
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev19.md",
     "7f87b8bb091d23c1bdcd2bf356b732a77bea12c4cfc4853d0ea58f7d239c92b2", "rules rev19"),
    # rev20 R20-4 2: rev16..rev20 in the Chrono tool lists (S8 4d8a95d); rev20 wins.
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev20.md",
     "615a8fbd82f4ef93f1ca76b3fb4d5c24a2e602e63a997c7c56119fcc73fb5531", "rules rev20"),
    # rev21 R21-3 2: rev16..rev21 in the Chrono tool lists (S9 da12622); rev21 wins.
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev21.md",
     "ecd709495f203eae1769ae42e67b5ae5bf2fb457146b558c12e46d636ed03f9a", "rules rev21"),
    # rev22 R22-2: rev16..rev22 in the Chrono tool lists (S10 570a9c1); rev22 wins.
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev22.md",
     "a48a81f9a71091aab40f643d48ae65ba559a5c0c629e02ef3145745a095f9328", "rules rev22"),
    # rev23 R23-2: rev16..rev23 in the Chrono tool lists (S11 f40935a); rev23 wins.
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev23.md",
     "fa72e1726f87f686093e36f2f3f489d5b135df6392de6aae7fe91b8739b56f97", "rules rev23"),
    # rev24 R24-3: rev16..rev24 in the Chrono tool lists (S12 b75d874); rev24 wins.
    ("06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev24.md",
     "f475cf77bc610802aa36026394cbe8dbae74745c8889ac203b53a6430e1e1e15", "rules rev24 (wins)"),
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
    # rules 4.1: the ③ reading of a tag is `v5_options.is_extend_start_tag` only (rev8 R8-2)
    "03_src/outrigger_sim/hydraulics/v5_options.py",
]


# D-29 (rev6 table: L2b D8 t_lift from the 1 ms pads.npz crawler_normal_N). rev15 R15-3 (user decision
# 2026-11-14): L2b rows without the 1 ms record (V0 rows) take the rev6 R6-B1 10 Hz bracket. The reading is
# on only while rev15 is in SEALED (added after its seal, R15-7); the seal check then requires the file.
D29_RULE_FILE = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev15.md"


def d29_l2b_bracket_enabled() -> bool:
    return any(rel == D29_RULE_FILE for rel, _, _ in SEALED)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


RAW_ONLY = {  # rev2 R2-9 last-but-one bullet: sealed rule files are compared raw only
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev1.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev2.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev3.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev4.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev5.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev6.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev7.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev8.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev9.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev10.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev11.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev12.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev15.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev16.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev17.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev18.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev19.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev20.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev21.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev22.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev23.md",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev24.md",
}


def sidecar_sha(p: Path):
    """First token of the sibling `.sha256` record (rev7 R7-7: seal sha and `.sha256` record both)."""
    sc = p.with_suffix(".sha256")
    if not sc.exists():
        return None
    tok = sc.read_text(encoding="utf-8", errors="replace").split()
    return tok[0].lower() if tok else None


def seal_check(repo: Path) -> dict:
    """Seal check (rules 8.2 S-1, rev2 R2-9, rev7 R7-7, rev8 R8-4, rev9 R9-8, rev10 R10-3, rev11 R11-7, rev12 R12-6, rev15 R15-7,
    rev18 R18-1, rev19 R19-8, rev20 R20-4, rev21 R21-3, rev22 R22-2, rev23 R23-2, rev24 R24-3). Raw sha must match; for
    Appendix A files, if only CRLF differs and the LF-normalised sha matches, pass and disclose
    ("CRLF 변환만 다름"). The 436.8 rule files (original, rev1..rev12, rev15..rev24) are compared raw only, and
    their code seal sha must also equal the first token of the sibling `.sha256` record (R7-7, R8-4,
    R9-8)."""
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
        if rel in RAW_ONLY:
            rec = sidecar_sha(p)
            if rec is None:
                rows.append({"file": rel, "role": role, "status": "sidecar_missing", "sha256": got,
                             "expected": want})
                ok = False
                continue
            if rec != want:
                rows.append({"file": rel, "role": role, "status": "sidecar_mismatch", "sha256": got,
                             "expected": want, "sidecar_sha256": rec})
                ok = False
                continue
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
W_TLIFT_SUS_N = 376700.0       # rev21 R21-1 "W = 376.7 kN, 5절과 같은 문턱" (v5 rev6 5 t_lift,sus: 0.01 W)
# rev8 R8-3a name table (J11 plant lock state): SCM `step_series.npz` `law_locked` on `t_s`,
# L2b `pads.npz` `law_locked` on `t`; [N, 4] int8, legs FL FR RL RR, 1 ms, values 1 / 0 / -1.
LAW_LOCK_FILES = {"scm": ("step_series.npz", "t_s"), "l2b": ("pads.npz", "t")}
LAW_LOCK_VALUES = (-1, 0, 1)    # R8-3a: 1 locked, 0 moving, -1 unarmed (rev6 6: before first arming = locked)
LAW_LOCK_DT_S = 1e-3            # R8-3a "1 ms"
LAW_LOCK_DT_TOL_S = 1e-6        # rev9 R9-2 item 5: |dt - 1 ms| <= 1e-6 s (procedure value, not a judgement threshold)
# rev9 R9-2 format check items (problem codes): 1 time column, 2 shape [N, 4] with N = time rows,
# 3 int8, 4 values in {-1, 0, 1}, 5 1 ms spacing, 6 -1 pattern (R9-3). "key" = law_locked absent.
LAW_LOCK_ITEMS = ("key", "R9-2.1", "R9-2.2", "R9-2.3", "R9-2.4", "R9-2.5", "R9-2.6")
# rev9 R9-3 -1 patterns: none / before_first_arming (allowed, = locked) / after_arming / whole_run /
# per_leg_mismatch (the last three = format error, R9-5)
LAW_LOCK_PATTERNS = ("none", "before_first_arming", "after_arming", "whole_run", "per_leg_mismatch")

# rev9 R9-4: LS row = v5 setting LS1..LS4 in both the manifest row and the S9 batch.json case
LS_SETTINGS = ("LS1", "LS2", "LS3", "LS4")
MANIFEST_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368/chrono_rows_manifest.json"

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

# spec 427.9 "판정 분류" (17690-17692), rev6 R6-B8 / D-26, rev18 R18-2 (S-01..04 safe stop).
# The recorded stop event is `FAULT_LIFT_STROKE_LIMIT:<reason>:<leg>` (raw events of the C-2 rows); condition 1
# reads the reason token. Saturation ("포화 0") = an extending control row (applied u > 0) with F_cyl / A_p >= the
# 210 bar relief (harness form, `s9_soil_event_screen` docstring E-4; CLAUDE.md "이동 중 최대 210 bar(릴리프)").
SAFE_STOP_REASON = "soil"
EVENT_STROKE_END = "FAULT_STROKE_END"
SATURATION_BAR = 210.0
SAFE_STOP_CLASSES = ("allowed_stop", "fail", "indeterminate")

# spec 426.3 study A rows E-1..E-7 (PS-c rows of C-2, rev4 R4-A2 option b / c). Branch structure of 426.3
# (event - 0.5 s; >= 12 s after the event and READY held 3 s; at most 60 s; slow pressure window to the ramp
# end + 3 s, so the branch runs >= ramp + 3 s).
E_SLOW_EVENTS = ("G4", "SS")          # 426.3 E-1 "느린 사건(G4·SS)"
E_FAST_EVENTS = ("FS24", "RE1bF")     # 426.3 timing level / E-1 "빠른 사건"
E_PRE_S = 0.5                         # 426.3 "사건 0.5 s 전 deepcopy"
E_MIN_AFTER_S = 12.0                  # "사건 뒤 >= 12 s"
E_READY_HOLD_S = 3.0                  # "READY 3 s 유지까지"
E_MAX_AFTER_S = 60.0                  # "최대 60 s"
E_SLOW_TAIL_S = 3.0                   # E-4 "느린 사건은 사건 시작 ~ 램프 끝 + 3 s"
E1_LIFT_SUM_S = 1.8                   # E-1 "다리별 누적 부상 최대 <= 1.8 s"
E1_LAST_TOUCH_S = 3.0                 # E-1 "마지막 재접지 <= 사건 + 3.0 s"
E2_T3_S = 0.82                        # E-2 "T_3 0.82 s (가정)"
E2_W_CAP_S = 5.0                      # E-2 "W = [0, min(쌍 마지막 재접지 + T_3, 5 s)]"
E2_SUM_S = 0.5                        # E-2 "W 안 부상 합 <= 0.5 s"
E2_GAP_M = 0.002                      # E-2 "틈 <= 2 mm"
E2_LOWF_FS_N = 2000.0                 # E-2 "U-S8-75 저마찰 예외(F_s < 2 kN 전방"
E2_LOWF_SUM_S = 0.1                   # "합 <= 0.1 s"
E2_LOWF_GAP_M = 0.0005                # "틈 <= 0.5 mm) 는 FLAG"
E4_WINDOW_BAR = 350.0                 # E-4 "창 안 다리별 F_cyl/A_p <= 350 bar"
E4_MOVING_BAR = 180.0                 # E-4 "창 밖 이동 표본 ... <= 180 bar"
E4_MOVING_EPS_M_S = 1e-6              # E-4 "(|u| > 10^-6 m/s)"
E5_END_MEAN_S = 1.0                   # E-5 "끝 1 s 평균 참 데크 |roll|·|pitch| <= 0.2°"
E5_STROKE_M = 0.6848                  # E-5 "실행 중 최대 행정 <= 684.8 mm"
E6_CLEAR_M = 0.025                    # E-6 "전 절점 틈 >= 25 mm"
E7_MAX_BUNDLES = 1                    # E-7 "비틀림 일 +20 J 초과 묶음 <= 1" (248.3)
E_DIAG = {"FL": "RR", "RR": "FL", "FR": "RL", "RL": "FR"}   # E-1 "침하 다리 + 대각"
E_ROW_COLUMNS = ("t", "contact_FL", "contact_FR", "contact_RL", "contact_RR", "Fcyl_FL", "Fcyl_FR",
                 "Fcyl_RL", "Fcyl_RR", "valve_FL", "valve_FR", "valve_RL", "valve_RR", "gap_FL",
                 "gap_FR", "gap_RL", "gap_RR", "roll_deg", "pitch_deg", "crawler_N")
"""`soil_event_series.npz` `columns` (raw record of the C-2 PS-c event row; R4-A2 "패드 접촉 법선, F_cyl, 틈")."""
