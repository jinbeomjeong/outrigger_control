"""Path-2 independent recount for the 436.8 v5 resume verification.

Rules: ``v5_resume_4368_rules.md`` (sha256 9019b405...), addenda ``v5_resume_4368_rules_rev1.md``
(sha256 d9094fda...) and ``v5_resume_4368_rules_rev2.md`` (sha256 497e4614...; the later sheet wins).
rev2 R2-1..R2-9 are applied: would_block without due / applied without due = record conflict (line
undecidable, S-5); absent start_s = not started; L2b / L1-R K1 record fields; open-loop r_vu / r_v;
F<F_min window [t_D, t_D + 8 s]; S-9 on either path; grid family by meta.spec + run event; C-2 fixed rows;
CRLF-only appendix-A difference passes and is disclosed. Later sealed addenda rev3..rev7 are checked
with the same raw-sha rule; rev7 (e81f7d31...) R7-4 sets the G-S conditional-absence table of the SCM
level rows (``GS_CONDITIONAL_R74``) and R7-6 the recorded pool mask (identity record only). rev8
(3ecafaaf...): seal check; R8-3 / R8-3a ``step_series.npz`` ``law_locked`` presence and format on SCM level
rows (G-S: S-11; main run: recorded, a C-5 row without it is undecidable); R8-2 ③ request record
(argv ``--extend-start-tracked``, ``v5_hydraulics.hydraulic_options.extend_start_tracked``) and
``controller_meta.two_pressure.settings.extend_start_rule`` against the tag ③ (S-2), J-P3 scope recorded;
R8-1b dotted ``controller_settings`` key read as one key. rev9 (4cf7843c...): seal check; R9-1
``expect_controller.ok`` false or absent on a Chrono controller row = S-2, in G-S also S-11; R9-2 / R9-3
``law_locked`` format on SCM level rows (``step_series.npz``, ``t_s``) and L2b rows (``pads.npz``, ``t``) the
same way: time column, [N, 4], int8, values in {-1, 0, 1}, 1 ms spacing within 1e-6 s, -1 only before the
first arming with the four legs leaving -1 at the same sample (after-arming -1, whole-run -1, per-leg exit
mismatch = format error); R9-4 LS row = manifest ``rows[].v5_setting`` and S9 ``batch.json``
``cases[].v5_setting`` equal and in LS1..LS4 (``--rows-manifest``; name tokens not used), LS row with a
non-③ tag = S-2; R9-5 / R9-6 missing or malformed ``law_locked``: G-S = S-11 (every SCM level / L2b row),
main run C-5 row = J11 not judgeable + stop (both engines), other rows recorded as "input missing".
rev10 (62a0bd8d...): seal check; R10-1a full batch name (`batch.json` `batch` checked against the
folder-name part, no key = folder name; mismatch / undeterminable / not a manifest batch = unknown);
R10-1b unknown name, 0 or several manifest rows or `batch.json` cases for the case = LS not judgeable,
not LS only with one row in each source and no value in both; missing / unreadable manifest = input
error (S-11, exit 2, bundles not judged); R10-2 G-S: name and one row per source, else S-11.
Author: dynamics-expert (path 2, user decision 2026-11-13). Written from the rule sentences, the appendix-A original rules they cite and the input key
facts handed over with the task. The path-1 tools (``resume4368_judge.py``, ``u3_judge_k1.py``,
``resume_k1_record.py``, the judging part of ``resume_k1_steps.py``) and every path-1 output were not
opened (rules 9.2).

Sub-commands (rules section in brackets):

  seal      rules / rev1 / appendix-A sha256 (S-1, A-2)
  harness   harness lines: tag (4.1, S-2), options and records (4.2, S-3, RV1-6 applicable,
            RV1-9), K1 classification (7.2, S-5, S-6), stored-hash check of unchanged lines (7.2),
            line counts (5.1 / RV1-2 / RV1-3 / RV1-12, S-15), missing keys (9.3)
  anchors   P-1 / P-2 bit predictions of H-1 against the RV1-5 anchors (S-7, S-5), appendix B sha
  chrono    Chrono rows: tag (4.1, RV1-10 a), forbidden argv / env (4.2), records (4.2, RV1-10 b),
            identity (6, S-4, S-12), K1 classification (7.2), start condition R_c (2, 7.4),
            departure + F_cyl recount from step_series.npz (9.1 C-8, 7.4), O-C5 stop (S-9, S-10),
            G-S key presence mode (11.2, RV1-10 f)
  oc5k      floor-scale procedure of 5.4 recomputed from probe start-condition keys (RV1-10 d, e)
  jp        J_P reuse reading (7.3) straight from controller_events.json and shadow_jp_b0.jsonl
  openloop  C-6 / C-7 values with the ``analyse`` definition of ``openloop_compare.py`` (9.1)
  compare   K-10 comparison of two finished JSON outputs (9.2)

Exit codes: 0 no stop and nothing failed or undecidable; 1 a fail, an undecidable item or a K-10
difference; 2 a stop condition (S-*) or a rules sha mismatch; 3 tool error. The last stdout line is a
JSON summary with ``out_sha256``. Only the stdlib and numpy are used (numpy only for npz files).
"""
from __future__ import annotations

import argparse
import ast
import datetime as _dt
import hashlib
import json
import math
import re
import sys
import traceback
from pathlib import Path

TOOL_NAME = "p2_4368.py"
TOOL_VERSION = "1"

RULES_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules.md"
RULES_SHA = "9019b405b7a196f28a756e7ca91f443f6241a58bd8e1eee0361483066cb19524"
RULES_SEAL_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules.sha256"
REV1_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev1.md"
REV1_SHA = "d9094fda104e25ac7eb7aea44d7c34d8215a839fc3771aa50b224d43082f02c7"
REV1_SEAL_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev1.sha256"
REV2_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev2.md"
REV2_SHA = "497e4614d6780c3201027b3946e3c21da05e2fefe9a3609436bc35ea664c3199"
REV2_SEAL_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev2.sha256"
REV3_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev3.md"
REV3_SHA = "dad8dfa68da7a988971f4d687706465289ec7dd95d09079c92215c64e5eae557"
REV3_SEAL_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev3.sha256"
REV4_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev4.md"
REV4_SHA = "7ea87a30b08a00263c597d42d3450dc56f68952e8d3205604cb2c5bab5dce14b"
REV4_SEAL_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev4.sha256"
REV5_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev5.md"
REV5_SHA = "452a8436c547e4da8d78205556cbb37633842d42cb98c18849cb883d827b3aca"
REV5_SEAL_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev5.sha256"
REV6_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev6.md"
REV6_SHA = "809e563971ea451aba7c9d0787c660bdcab1c495af39c513c8f158e09b4fe6c9"
REV6_SEAL_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev6.sha256"
REV7_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev7.md"
REV7_SHA = "e81f7d31779b0d69a140c9d90aa4684f3c9299e84aec6af06b13d48d58631502"
REV7_SEAL_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev7.sha256"
REV8_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev8.md"
REV8_SHA = "3ecafaaf33d84bb6f34a8cef5401771832a4999e4930f3644caff56eed640e56"
REV8_SEAL_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev8.sha256"
REV9_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev9.md"
REV9_SHA = "4cf7843ce469df511d7b99c7236f0b245afae9fb4ba5ad903e1c2da823a59a6d"
REV9_SEAL_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev9.sha256"
REV10_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev10.md"
REV10_SHA = "62a0bd8dd6644f78bf37d052e884061d8c14e1cc96e2babc72a6ac0618f12c29"
REV10_SEAL_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev10.sha256"
EXT_RULE_DOTTED = "two_pressure.extend_start_rule"     # rev8 R8-1b: one key of controller_settings
GRID_SPEC_PRESCRIBED = "rev. 67 (G1 / G2 / G7 reduced screen)"   # rev2 R2-7
GRID_EVENTS_PRESCRIBED = {"G4", "RE1bF", "FS24"}

_V5 = "06_analysis/03_hydraulic/coupled/v5/"
_VM = "06_analysis/02_control/verif_matrix/"
APPENDIX_A = {  # rules appendix A (full sha256)
    _V5 + "v5_criteria.md": "06ed0384fb942cfdf9ab481878ffd5f19d5faab4e6163aa986dcdda5156e080e",
    _V5 + "v5_criteria_rev1.md": "cbfac2b2de571500fbf5410dd5456bfa82d4a05cf25f21c76feb25fab1308fab",
    _V5 + "v5_criteria_rev2.md": "e120474b8ebd721e6edc4fec8eef811ce810006b8c489e38cecbb7ae5caeed77",
    _V5 + "v5_criteria_rev3.md": "7084da25c6129681086efc4fbc5afb315d7b4d424cbed123746ec32b4ea61ec2",
    _V5 + "v5_criteria_rev4.md": "642e96f9cfd20a9c2a016ed128a6ce7d584718e5728d6008640f8703a5acbd72",
    _V5 + "v5_criteria_rev5.md": "945f714660cd3ec7e749151bcd81b1f9da35b6001d7fd9c7e2cfeee21fcd320b",
    _V5 + "v5_criteria_rev6.md": "fd5117031ef460cf4c6aa74807b2e73de984b014abb89a952b593499841da39c",
    _V5 + "v5_criteria_rev7.md": "9ccde7a5a4128317ed832dd2f92cd2368280f18cefa6827f1b1731c6d4e9aab3",
    _V5 + "v5_criteria_rev8.md": "c6ec89f71c1d8de4c06000568c2e5978fd7f9fe58a53defea728f2f4886bb25f",
    _V5 + "v5_criteria_rev9.md": "3c50dda50ca6dca60177f26d91d86c009eeb4f9321f5ffd0c98ddc27cf62e981",
    _V5 + "v5_criteria_rev10.md": "bd65db24f68a6d4c3a8346447a0cbfdd89e97cd07f4b295237127c304174e182",
    _V5 + "v5_criteria_rev11.md": "ca6b5c95d8f544ff8ec5db2e1ec193d2b200df74c2e9c7decdb56b61757e2ecb",
    _V5 + "v5_criteria_rev12.md": "e02d63cc1290383ee85d9a1f3a20c6348224b60999cccaf8d587cf610c5f5eb2",
    _V5 + "v5_criteria_rev12a.md": "e171141dce180fbb48493b9b95503ff3577d16f17cc54061ce3ad6e9efd51458",
    _V5 + "v5_criteria_rev12b.md": "0d17f87e9532d558efcab9fa89648e2790ece9c7568a802fbaa4c7631824e75d",
    _VM + "d1_selection_rules.md": "51dea528e57fa0c4378cda110addb73da20339535e16189452af2d06b60736e9",
    _VM + "d1_selection_rules_rev1.md": "eb730bddae35e76bc2569503605dea714b066fa42de7bc7b98efdde3edb3e868",
    _VM + "u3_u6_rerun_rules.md": "8de318825764114ad14afcec362c87c1e01a2ad47195b8491b1c96056e1960b3",
    _VM + "u3_u6_rerun_rules_rev1.md": "2c5e69213b29fc930c478306676efc72b515d67af08634adab3eba2d05f5f15d",
    _VM + "u3_u6_rerun_rules_rev2.md": "be1584a4448d68a30c4fe9ec613d3d7b3cb0b47169c2f5eff72e9a9ca0776880",
    _VM + "u9_targeted_rules_rev1.md": "644005b706ba46cebba11b975ded474226cc4eab5030ee18e9f91dacd2d14587",
    _VM + "las_targeted_rules.md": "00b48fd834d81b9d499015f2d44380623e9fbcb2f1515913a8fd0589503eaf40",
    _VM + "las_targeted_rules_rev1.md": "0d5f59f8e4a09448b93e0cde42adb7d23c2f99f6b365809876efaa6212d27625",
    _VM + "las_targeted_rules_rev2.md": "6be736cb98cea34e4a606606b4009668bbc1470c8a7db23b6a119ef033c97960",
    _VM + "las_targeted_rules_rev3.md": "956f65c74e36eb8fe921dc6399b0d5f2f04099b7852380362351f658c9791cd1",
    _VM + "las_targeted_rules_rev4.md": "05fbde22009c10b74ddf0df071452a99631bb319c2f482df83be59adfad1de6d",
    _VM + "las_targeted_rules_rev4a.md": "3cbbfb5d8afda9075bf9631accf1b8bee4c1ee02edafa34a7869091175a73b15",
    _VM + "las_targeted_rules_rev4b.md": "add921e4978ef16abcc22dfc88dc25e51a770dc98d2d540526f48cf6ea7a6f3f",
    _VM + "las_targeted_rules_rev4c.md": "7e45993f667382f56aeb1b72bb5e7023ecfe3048a3723ac050cefc3b2a721417",
    _VM + "las_targeted_rules_rev5.md": "879d0e4d715b2e9f4e51257863fc259ccfe48105ca019299547d58dca24949b2",
    _VM + "las_k1_rules_adopt2.md": "fb3a5696f24385e81acc9c564500b5e5a0547db45a5335272e7d18400f1e68e8",
    _VM + "las_k1_rules_adopt_rev1.md": "730dbb3d30dffca6d652953c22b62563141beeee6af6f045d6b2cb59f60deb65",
    _VM + "las_p5r4_k1_judgement.md": "5e9fb33b7419d624d8dc305ad93121be090802cc5c85ea29fbc823e019fc9e2f",
    _VM + "v5_resume_4368_plan_draft.md": "141e4958f39b7c7470bb4c66003877f2af0c14c93300a705eb60988e2a04033d",
}
APPENDIX_B = {  # rev1 appendix B (relative to the v5 folder)
    "d1.jsonl": "9039b36a1a9c4ba5ed63528bb7384773018d4c7377dccbf76b18fbcfda86707f",
    "las/las_T1.jsonl": "3dee4f6b88e71654debd68b3ef5c5f1a9b01f1dba8fcd731d1355ec219d9a85b",
    "las/las_T2.jsonl": "2fe6a54aafdc0c3ffbf1991907ee4e1af85761e1bef2e25bef07dd52ab199efb",
    "las/k1/k1_YP.jsonl": "0d985d5624f0fbb0219ca50d1c839b7db639011d6c2ab14fa9d84cfd197fc2c3",
    "soil_defer/s2d_SC.jsonl": "70e91ec1234d56a918af1b4fc053c3175f0f14ab41e2b5f334890f7dc6cb08aa",
    "overlap_t_a.json": "39bc75cb3aa0b6678d75e9ce06aac39f34fcb3debff0fa872bf640ac6d7c77ce",
    "main.jsonl": "9ad749907c34c9e9efb77579a8ab6e3b1f86cdc32d36162c0029005ca545b29e",
    "dg3/dg3_v4_on.json": "5f912ca0d25d6dfe0114e05bf8c7a083fa542ad3de71e76c472e44a1a351167d",
    "dg3/off/dg3_off.json": "95b81f82d800ae3ccf0dd15e205f12ec4b8795a1dcb482e6e30ed41aa0cfd5ce",
    "noise_vb/r79_VB_L1L2L3.json": "d3c9bba1abd3c1fbc700a26527856e14f7754740192c55a404bc203ef8a763b9",
    "noise_v0/r79_V0_L1L2L3.json": "af6a7ae51abe4b9094db9b21cf49f8770861fb0ed91cb269effb6b2cab9b459a",
    "seedext/r79_VB_seedext.json": "6ddca3d5ce5dc6286c319de13d779bbb419df8fbee2bd13577d04b0f4c2d6f57",
    "seedext/r79_V0_seedext.json": "f2c01d65238cac50da57c26ca33541b9506ff50b14aee80d65f31e1378dabaa8",
    "grid_vb/grid_r67_main.json": "8ef4237dc7658559efa04ac07edc1641fe422cbb55e5fee902fbac94eac13ef7",
    "grid_vb/grid_r67_top.json": "498aa41199b2e4ed3467573c061ab2d6a182ffcd10871fe9bc7420989e6e6412",
    "grid_vb/grid_r69_bottom.json": "ee84750be278a2c284bf1fe614155240c0a4c2b564762862276a007afc9609e9",
    "grid_vb/grid_r69_top.json": "c132fd41f13b8033b25804fbc777408a5d1729f31348af34aadd7fd6dfaad325",
}

# --- numbers (rules 7.6, RV1-11) ---
F_MIN_N = 9414.589            # YAML control.F_min_cylinder_N (rules 2 / 7.4)
G_BAND_N = 2000.0             # F_min + 2000 N (7.4)
EPS_THR = 1e-9                # 7.6 threshold tolerance (unit of the value)
K10_REL = 1e-9                # 9.2 K-10 value tolerance
RC_LIMIT = 1.0                # R_c <= 1 (7.4, 5.4-9)
RC_PHI_DEG, RC_THETA_DEG = 4.4, 3.2   # SL-2 (rules 2)
OC5_TARGET, OC5_TOL, OC5_MAX_PROBES = 0.95, 0.02, 3   # 5.4 procedure values (assumption)
OC5_BASE_DEG = (2.3351, 1.5017)        # 5.4-8
OC5_K1 = {"C-8a": 0.9179, "C-8b": 0.8829}  # RV1-10 d
K_DECIMALS = 4                # RV1-10 d
PROBE_DURATION_S = 7.0        # RV1-10 e
SCM_THREADS = 4               # rules 6
DEPARTURE_FRACTION_W = 0.01   # P3a-2 departure rule (crawler normal < 0.01 W for 0.1 s)
DEPARTURE_HOLD_S = 0.1
TRANSIENT_WINDOW_S = 8.0      # P5r4 judgement 8.2 table window (departure + 8 s)

# --- tags (rules 4.1, RV1-3.2) ---
TAG_V0 = "final_C4G2_LAS_K1"
TAG_VB = "final_C4G2_P3_LAS_K1"
TAG_ABL = "ABL_LAS_K1"
TAG_IND = "IND"
TAG_IND_LAS = "IND_LAS"
TAG_C4OFF_V0 = "final_C4G2_K1"
TAG_C4OFF_VB = "final_C4G2_P3_K1"
KIND_TAG = {
    "V0": TAG_V0, "V0v": TAG_V0, "S6SEED": TAG_V0, "V3": TAG_V0, "H7": TAG_V0, "NOP3": TAG_V0,
    "VB": TAG_VB, "LS": TAG_VB, "H6": TAG_VB,
    "ABL": TAG_ABL, "IND": TAG_IND, "IND_LAS": TAG_IND_LAS,
    "C4OFF_V0": TAG_C4OFF_V0, "C4OFF_VB": TAG_C4OFF_VB,
}
KIND_P3 = {"VB": True, "LS": True, "H6": True, "C4OFF_VB": True, "V0": False, "V0v": False,
           "S6SEED": False, "V3": False, "H7": False, "NOP3": False, "C4OFF_V0": False,
           "ABL": None, "IND": None, "IND_LAS": None}
NO_K1_KINDS = {"IND", "IND_LAS"}   # RV1-6 addendum: applicable false is expected only here

# --- LAS-b preset (spec 436 settings table; 9 values; ABL: require_soil_response False) ---
LAS_PRESET = {"enable": True, "sum_on_fraction_W": 0.6, "light_leg_fraction_of_F_min": 3.5,
              "slow_mean_fraction": 0.16, "sum_off_fraction_W": 0.85, "off_periods": 5, "max_s": 1.5,
              "rho_on": 0.18, "require_soil_response": True}
LAS_EXTRA_ZERO = ("min_active_periods", "end_ramp_periods")   # P5r4 extras: must stay 0 under P0

# --- line counts (5.1 + RV1-2 / RV1-3 / RV1-12) ---
HARNESS_COUNTS = {"H-1": 868, "H-3": 2228, "H-4": 968, "H-5": 14, "H-6": 135, "H-7": 135,
                  "H-8": 3106, "H-9": 1676, "H-10": 440}
HARNESS_FILE_COUNTS = {("H-4", "IND_LAS"): 242, ("H-4", "IND"): 242}
C2_FIXED = {"C2-03", "C2-07", "S-01", "S-02"}   # rules 5.2 C-2 fixed rows (rev2 R2-8)
CHRONO_COUNTS = {"C-1": (10, 10), "C-3": (2, 2), "C-4": (4, 4), "C-5": (35, 35), "C-6": (1, 1),
                 "C-7": (2, 2), "C-8a": (1, 1), "C-8b": (1, 1)}

# --- event names (exact, name.split(':', 1)) ---
EV_SKIP_ORDER = "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order"
EV_FLAT = "INFO_LOC_FLAT_SOIL_MARGIN"
EV_SOIL_START = "soil_mode_start"
EV_FAULT_STROKE_END = "FAULT_STROKE_END"

FORBIDDEN_TOKENS = {"K1on", "LASoff", "TCL", "P5r4"}   # 4.2 harness key tokens
CHRONO_FORBIDDEN_ARGV = {"--k1-order-gate", "--las-off", "--las-candidate", "--k1-forced-block",
                         "--k2", "--no-controller-check"}
SCM_FORBIDDEN_ARGV = {"--allow-mixed-hull"}
SCM_FORBIDDEN_ENV = ("OUTRIGGER_HULL_HOOK", "OUTRIGGER_HULL_HOOK_ALLOW_UNVALIDATED")
SHADOW_ENV = "OUTRIGGER_LOC_SHADOW"

SOIL_NAMES = {"G1", "G5", "J1", "J2", "S1", "S2"}
RIGID_GROUPS_H1 = {"H-R-0", "H-R-A", "H-R-A-stop"}     # P-1 rigid 412 (264 + 144 + 4)

PRIORITY = {"stop": 4, "undecidable": 3, "fail": 2, "pass": 1}
MISSING = object()


# ----------------------------------------------------------------- helpers
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dig(d, path, default=MISSING):
    cur = d
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def first_path(d, paths):
    """(value, path) of the first existing path, else (MISSING, None)."""
    for p in paths:
        v = dig(d, p)
        if v is not MISSING:
            return v, p
    return MISSING, None


def num(x):
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, (int, float)) and math.isfinite(float(x)):
        return float(x)
    return None


def fnum(x):
    """Number from a number or an argv string."""
    if isinstance(x, str):
        try:
            x = float(x)
        except ValueError:
            return None
    return num(x)


def t_ge(v, x):
    return v >= x - EPS_THR


def t_lt(v, x):
    return v < x - EPS_THR


def t_gt(v, x):
    return v > x + EPS_THR


def t_absle(v, c, e):
    return abs(v - c) <= e + EPS_THR


def same_value(a, b):
    """K-10 value equality (9.2)."""
    if isinstance(a, bool) or isinstance(b, bool) or a is None or b is None:
        return a is b or a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if not (math.isfinite(a) and math.isfinite(b)):
            return (math.isnan(a) and math.isnan(b)) or a == b
        return abs(a - b) <= K10_REL * max(1.0, abs(a), abs(b))
    return a == b


def combine(statuses):
    best = "pass"
    for s in statuses:
        if PRIORITY.get(s, 3) > PRIORITY[best]:
            best = s
    return best


def job_key(job):
    """run_v5 line key: the job without mask / t4h_dir, sorted JSON (input key fact)."""
    if not isinstance(job, dict):
        return None
    j = {k: v for k, v in job.items() if k not in ("mask", "t4h_dir")}
    return json.dumps(j, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def line_key(rec, controller=None):
    """Line key (input key fact): run_v5 job_key, else key / id / case; '|<controller>' if any."""
    if isinstance(rec.get("job"), dict):
        k = job_key(rec["job"])
    else:
        k = None
        for name in ("key", "id", "case"):
            if isinstance(rec.get(name), str):
                k = rec[name]
                break
    if k is not None:
        c = controller if controller is not None else rec.get("controller")
        if isinstance(c, str) and c:
            k = f"{k}|{c}"
    return k


def tokens(s):
    return [t for t in re.split(r"[|_#=:,+@ /]+", s) if t]


def iter_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_strings(k)
            yield from iter_strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from iter_strings(v)


def forbidden_tokens_in(obj):
    hit = set()
    for s in iter_strings(obj):
        for t in tokens(s):
            if t in FORBIDDEN_TOKENS:
                hit.add(t)
    return sorted(hit)


def event_name_split(name):
    base, _, suffix = name.partition(":")
    return base, suffix


_EV_RE = re.compile(r"^C2Event\(t_s=([^,]+), name=(.+)\)$")


def parse_c2event(s):
    """repr(C2Event) -> (t_s, name); None if the string is not in that form."""
    m = _EV_RE.match(s.strip())
    if not m:
        return None
    try:
        t = float(m.group(1))
        name = ast.literal_eval(m.group(2))
    except (ValueError, SyntaxError):
        return None
    if not isinstance(name, str):
        return None
    return t, name


def resolve_rc(crawler_attitude_deg):
    """SL-2 R_c = |phi_c|/4.4 + |theta_c|/3.2 (rules 2)."""
    if not isinstance(crawler_attitude_deg, (list, tuple)) or len(crawler_attitude_deg) != 2:
        return None
    a, b = num(crawler_attitude_deg[0]), num(crawler_attitude_deg[1])
    if a is None or b is None:
        return None
    return abs(a) / RC_PHI_DEG + abs(b) / RC_THETA_DEG


class Findings:
    """Stops, undecidable items and fails with their place."""

    def __init__(self):
        self.stops = []
        self.undecidable = []
        self.fails = []
        self.records = []

    def stop(self, code, where, why):
        self.stops.append({"code": code, "where": where, "why": why})

    def undec(self, where, why):
        self.undecidable.append({"where": where, "why": why})

    def fail(self, where, why):
        self.fails.append({"where": where, "why": why})

    def note(self, where, what):
        self.records.append({"where": where, "what": what})

    def status(self):
        if self.stops:
            return "stop"
        if self.undecidable:
            return "undecidable"
        if self.fails:
            return "fail"
        return "pass"

    def as_dict(self):
        return {"status": self.status(), "stops": self.stops, "undecidable": self.undecidable,
                "fails": self.fails, "records": self.records,
                "stop_codes": sorted({s["code"] for s in self.stops})}


# ----------------------------------------------------------------- seal (S-1, A-2)
def check_seals(repo, appendix=True):
    """Rules + rev1 sha against the constants and the .sha256 files; appendix A sha."""
    out = {"rules": {}, "appendix_a": {}, "ok": True}
    for rel, want, seal in ((RULES_REL, RULES_SHA, RULES_SEAL_REL), (REV1_REL, REV1_SHA, REV1_SEAL_REL),
                            (REV2_REL, REV2_SHA, REV2_SEAL_REL), (REV3_REL, REV3_SHA, REV3_SEAL_REL),
                            (REV4_REL, REV4_SHA, REV4_SEAL_REL),
                            (REV5_REL, REV5_SHA, REV5_SEAL_REL), (REV6_REL, REV6_SHA, REV6_SEAL_REL),
                            (REV7_REL, REV7_SHA, REV7_SEAL_REL),
                            (REV8_REL, REV8_SHA, REV8_SEAL_REL),
                            (REV9_REL, REV9_SHA, REV9_SEAL_REL),
                            (REV10_REL, REV10_SHA, REV10_SEAL_REL)):   # sealed rules: raw sha only (R2-9, R9-8, R10-3)
        p = repo / rel
        got = sha256_file(p) if p.is_file() else None
        sp = repo / seal
        seal_sha = None
        if sp.is_file():
            first = sp.read_text("utf-8").split()
            seal_sha = first[0].lower() if first else None
        raw = p.read_bytes() if p.is_file() else b""
        ok = got == want and seal_sha == want and not raw.startswith(b"\xef\xbb\xbf") and b"\r\n" not in raw
        out["rules"][rel] = {"sha256": got, "want": want, "seal_file_sha": seal_sha, "ok": ok}
        out["ok"] &= ok
    if appendix:
        for rel, want in APPENDIX_A.items():
            p = repo / rel
            got = sha256_file(p) if p.is_file() else None
            item = {"ok": got == want, "sha256": got}
            if got is not None and got != want:
                # a checkout with core.autocrlf turns LF into CRLF for files without '-text'; the
                # rules list the LF bytes. Accept an EOL-only difference and record it.
                lf = hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                item["sha256_lf"] = lf
                if lf == want:          # rev2 R2-9: CRLF -> LF only; disclose raw and LF sha
                    item["ok"] = True
                    item["eol_only"] = True
                    item["note"] = "CRLF 변환만 다름"
                    out.setdefault("eol_only", []).append(rel)
            out["appendix_a"][rel] = item
            out["ok"] &= item["ok"]
    return out


# ----------------------------------------------------------------- tag ③ judgement (4.1)
def load_is_extend_start(repo):
    """``v5_options.is_extend_start_tag`` (rules 4.1: the only allowed ③ judgement)."""
    src = repo / "03_src"
    mod_path = src / "outrigger_sim" / "hydraulics" / "v5_options.py"
    info = {"path": str(mod_path), "sha256": sha256_file(mod_path) if mod_path.is_file() else None}
    try:
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))
        from outrigger_sim.hydraulics import v5_options  # noqa: PLC0415
        info["loaded"] = True
        return v5_options.is_extend_start_tag, info
    except Exception as exc:  # noqa: BLE001
        info["loaded"] = False
        info["error"] = repr(exc)
        return None, info


# ----------------------------------------------------------------- K1 classification (7.2)
def classify_k1(las, order_gate, skipped_count, family, where, fnd, las_absent_ok=False):
    """Classification of one line / row from its LAS-b and order-gate blocks.

    ``las``: liftoff_approach_slow dict (MISSING if absent); ``order_gate``: slope_clearance_margin
    .order_gate dict; ``skipped_count``: count of INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order (None =
    unreadable); ``las_absent_ok``: C-4 off arm (RV1-10 b 'LAS none')."""
    res = {"class": None, "las_started": None, "blocked": None, "would_block_any": None,
           "would_block_without_r4_due": None, "skipped_order": skipped_count, "family": family}
    if las is MISSING or not isinstance(las, dict):
        if las_absent_ok:
            las_started = False
            res["las"] = "none"
        else:
            fnd.undec(where, "liftoff_approach_slow block missing (9.3)")
            return res
    elif las_absent_ok:
        las_started = False
        res["las"] = "none"
        if las.get("enable") is True or dig(las, "settings.enable") is True:
            fnd.stop("S-3", where, "C-4 off arm with LAS-b enabled")
    else:
        las_started = las.get("start_s") is not None   # key absent = never started (input fact)
    res["las_started"] = las_started
    if not isinstance(order_gate, dict):
        fnd.undec(where, "slope_clearance_margin.order_gate missing (9.3)")
        return res
    if order_gate.get("enabled") is not True:
        fnd.stop("S-3", where, f"order_gate.enabled = {order_gate.get('enabled')!r} (gate-on run expected)")
    decisions = order_gate.get("decisions")
    if not isinstance(decisions, list):
        fnd.undec(where, "order_gate.decisions missing (9.3)")
        return res
    blocked = 0
    wb_any = False
    wb_no_due = 0
    for i, d in enumerate(decisions):
        if not isinstance(d, dict) or "would_block" not in d or "r4_due_without_gate" not in d:
            fnd.undec(where, f"decision {i} lacks would_block / r4_due_without_gate (9.3)")
            return res
        wb = d.get("would_block") is True
        due = d.get("r4_due_without_gate") is True
        if wb:
            wb_any = True
            if due:
                blocked += 1
            else:
                wb_no_due += 1
        if wb and d.get("applied") is True:
            fnd.stop("S-5", where, f"decision {i}: applied and would_block both true")
        if d.get("applied") is True and not due:
            fnd.stop("S-5", where, f"decision {i}: applied without r4_due_without_gate (record conflict, R2-1)")
    res.update(blocked=blocked, would_block_any=wb_any, would_block_without_r4_due=wb_no_due,
               n_decisions=len(decisions))
    if skipped_count is None:
        fnd.undec(where, "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order count unreadable (9.3)")
    elif skipped_count != blocked:
        fnd.stop("S-5", where, f"_SKIPPED:order count {skipped_count} != blocked decisions {blocked}")
    if wb_no_due:
        # rev2 R2-1: record conflict -> the line is undecidable and the bundle stops with S-5
        fnd.undec(where, f"{wb_no_due} decision(s) would_block without r4_due_without_gate (record conflict)")
        fnd.stop("S-5", where, "would_block without r4_due_without_gate (record conflict, R2-1)")
        res["class"] = "record_conflict"
        return res
    prefix = "las_none_" if las_absent_ok else ""
    if blocked == 0 and not las_started:
        res["class"] = prefix + "unchanged"
    elif blocked == 0 and las_started:
        res["class"] = "las"
    elif blocked > 0 and not las_started:
        res["class"] = prefix + "k1_block"
    else:
        res["class"] = "both"
    if blocked > 0 and family in ("uniform", "unresolved"):
        fnd.stop("S-6", where, f"K1 block on a {family} soft-ground line (7.2 / RV1-6)")
    return res


# ----------------------------------------------------------------- ground family (7.2, RV1-6)
def family_from_tokens(strings):
    """rigid / patch / uniform / unresolved from key and ground strings (path-2 rule, RV1-6:
    independent of the path-1 family table)."""
    toks = []
    for s in strings:
        if isinstance(s, str):
            parts = [p for p in s.split("|") if p]
            toks.extend(parts)
    if any("@" in t for t in toks):
        return "patch"              # patch (soil@leg, rigid+soil@leg) or prescribed sinkage (c-mid@leg)
    if any(t == "rigid" for t in toks):
        return "rigid"
    if any(t in SOIL_NAMES for t in toks):
        return "uniform"
    return "unresolved"


def family_d1(job):
    d1 = job.get("d1") if isinstance(job, dict) else None
    if not isinstance(d1, dict):
        return None
    base, pl, ps, sink = d1.get("base"), d1.get("patch_leg"), d1.get("patch_soil"), d1.get("sink")
    if pl not in (None, "", []) or ps not in (None, "", []) or sink not in (None, "", [], {}):
        return "patch"
    if base == "rigid":
        return "rigid"
    if isinstance(base, str) and base in SOIL_NAMES:
        return "uniform"
    return family_from_tokens([d1.get("key")])


def family_grid(run, file_meta):
    """rev2 R2-7: grid (r67 / r69) runs: meta.spec + run event only, never the key string."""
    spec = file_meta.get("spec") if isinstance(file_meta, dict) else None
    if spec == GRID_SPEC_PRESCRIBED and run.get("event") in GRID_EVENTS_PRESCRIBED:
        return "patch"
    return "unresolved"          # treated as uniform soft (S-6 on a K1 block)


def family_harness(rec, fmt, parent=None, file_meta=None):
    if fmt == "grid_json":
        return family_grid(rec, file_meta or {})
    if fmt == "run_v5_jsonl":
        f = family_d1(rec.get("job"))
        if f is not None:
            return f
        return family_from_tokens([dig(rec, "job.key", None), rec.get("key")])
    strings = []
    for src in (rec, parent or {}):
        for name in ("base", "key", "id", "soil", "soil_model"):
            v = src.get(name)
            if isinstance(v, str):
                strings.append(v)
    return family_from_tokens(strings)


def family_chrono(res, engine):
    if engine in ("L2b", "L1-R"):
        return "rigid"
    args = res.get("args", {}) if isinstance(res.get("args"), dict) else {}
    if args.get("rigid_base") not in (None, "", "none"):
        return "patch"           # mixed: rigid floor + soft patch (C-4, C-8)
    if args.get("soil_patch") not in (None, "", "none") or dig(res, "meta.soil_patch.leg", None) not in (None, ""):
        return "patch"
    if isinstance(args.get("soil"), str) and args.get("soil"):
        return "uniform"
    return "unresolved"


# ----------------------------------------------------------------- record checks (4.2)
def check_las_settings(settings, where, fnd, abl=False):
    if not isinstance(settings, dict):
        fnd.stop("S-3", where, "liftoff_approach_slow.settings missing (4.2 record check)")
        return False
    ok = True
    want = dict(LAS_PRESET)
    if abl:
        want["require_soil_response"] = False
    for k, v in want.items():
        if k not in settings:
            fnd.stop("S-3", where, f"liftoff_approach_slow.settings.{k} missing")
            ok = False
        elif not same_value(settings[k], v) or isinstance(settings[k], bool) != isinstance(v, bool):
            fnd.stop("S-3", where, f"liftoff_approach_slow.settings.{k} = {settings[k]!r} (preset {v!r})")
            ok = False
    for k in LAS_EXTRA_ZERO:
        if k in settings and not same_value(settings[k], 0):
            fnd.stop("S-3", where, f"liftoff_approach_slow.settings.{k} = {settings[k]!r} (P0 preset: 0)")
            ok = False
    extra = sorted(set(settings) - set(want) - set(LAS_EXTRA_ZERO))
    if extra:
        fnd.note(where, f"liftoff_approach_slow.settings extra keys {extra}")
    return ok


# ----------------------------------------------------------------- harness
def harness_records(path, fmt):
    """Yield (rec, parent, index_label) of one harness output file."""
    p = Path(path)
    if fmt == "run_v5_jsonl":
        with open(p, encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if line:
                    yield json.loads(line), None, f"line{i + 1}"
        return
    data = json.loads(p.read_text("utf-8"))
    if fmt == "u3_json":
        for i, r in enumerate(data.get("records", [])):
            yield r, data, f"records[{i}]"
    elif fmt == "r79_json":
        for i, r in enumerate(data.get("results", [])):
            yield r, data, f"results[{i}]"
    elif fmt == "grid_json":
        for i, r in enumerate(data.get("results", [])):
            for j, run in enumerate(r.get("runs", [])):
                yield run, r, f"results[{i}].runs[{j}]"
    else:
        raise ValueError(f"unknown format {fmt}")


RESUME_PATHS = {"run_v5_jsonl": ("resume_k1",), "u3_json": ("v5.resume_k1", "resume_k1"),
                "r79_json": ("resume_k1",), "grid_json": ("resume_k1",)}
TAG_PATHS = ("controller_tag", "v5.controller_tag", "v5_hydraulics.controller_tag", "resume_k1.controller_tag")
HASH_PATHS = ("commands_sha256", "v5.commands_sha256", "r79.commands_sha256")


def harness_key(rec, parent, fmt, label):
    if fmt == "grid_json":
        pk = parent.get("key") if isinstance(parent, dict) else None
        k = rec.get("key") or rec.get("id") or rec.get("case")
        if not k:
            k = f"{pk}|{label.split('.')[-1]}" if pk else None
        return k
    return line_key(rec)


def skipped_count_harness(rec, rk):
    """Count of INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order: raw event list first, then the line's
    event-name counts, then the resume_k1 event_counts (source recorded)."""
    evs = rec.get("events")
    if isinstance(evs, list) and evs:
        n = 0
        ok = True
        for e in evs:
            name = e if isinstance(e, str) else (e.get("name") if isinstance(e, dict) else None)
            if name is None:
                ok = False
                break
            if name == EV_SKIP_ORDER:
                n += 1
        if ok:
            return n, "events"
    names = rec.get("event_names")
    if isinstance(names, dict):
        v = names.get(EV_SKIP_ORDER)
        if v is None:
            v = names.get(EV_SKIP_ORDER.split(":")[0])
        return int(v or 0), "event_names"
    v = dig(rk, "event_counts.flat_soil_margin_skipped_order", None) if isinstance(rk, dict) else None
    if isinstance(v, int):
        return v, "resume_k1.event_counts"
    return None, None


def cmd_harness(args, repo):
    manifest = json.loads(Path(args.manifest).read_text("utf-8"))
    is_p3, mod_info = load_is_extend_start(repo)
    fnd_all = {}
    files_out = []
    bundles = {}
    for entry in manifest["files"]:
        bundle, kind, fmt = entry["bundle"], entry["kind"], entry["format"]
        path = Path(entry["path"])
        if not path.is_absolute():
            path = repo / path
        fnd = fnd_all.setdefault(bundle, Findings())
        b = bundles.setdefault(bundle, {"lines": 0, "classes": {}, "families": {}, "tags": {},
                                         "errors": 0, "missing": 0, "files": []})
        want_tag = KIND_TAG.get(kind)
        if want_tag is None:
            raise ValueError(f"unknown kind {kind}")
        stored = {}
        if entry.get("stored"):
            sp = Path(entry["stored"])
            if not sp.is_absolute():
                sp = repo / sp
            for rec, par, lab in harness_records(sp, entry.get("stored_format", fmt)):
                if "error" in rec:
                    continue
                k = harness_key(rec, par, entry.get("stored_format", fmt), lab)
                h, _ = first_path(rec, HASH_PATHS)
                stored.setdefault(k, []).append(h)
        file_meta = json.loads(path.read_text("utf-8")).get("meta", {}) if fmt == "grid_json" else None
        n_file = 0
        classes = {}
        hash_cmp = {"compared": 0, "equal": 0, "differ": [], "no_anchor": 0}
        keys_seen = set()
        for rec, parent, label in harness_records(path, fmt):
            n_file += 1
            key = harness_key(rec, parent, fmt, label)
            where = f"{bundle}:{path.name}:{label}:{key}"
            if key in keys_seen:
                fnd.stop("S-15", where, "duplicate line key")
            keys_seen.add(key)
            if "error" in rec:
                b["errors"] += 1
                fnd.undec(where, f"line has error: {str(rec.get('error'))[:200]}")
                continue
            # forbidden key tokens / wrappers (4.2)
            hit = forbidden_tokens_in([rec.get("job"), rec.get("key"), rec.get("id")])
            if hit:
                fnd.stop("S-3", where, f"forbidden key tokens {hit}")
            k0 = rec.get("key")
            if isinstance(k0, str) and k0.startswith("cand=") and not k0.startswith("cand=current#"):
                fnd.stop("S-3", where, f"candidate token other than 'current' in key {k0.split('|')[0]}")
            # tag (4.1)
            tag, tag_path = first_path(rec, TAG_PATHS)
            b["tags"][str(tag if tag is not MISSING else None)] = b["tags"].get(
                str(tag if tag is not MISSING else None), 0) + 1
            if tag is MISSING or tag is None:
                fnd.stop("S-11", where, "controller_tag missing (RV1-3.2: stop and ask)")
            elif tag != want_tag:
                fnd.stop("S-2", where, f"tag {tag!r} != expected {want_tag!r} ({kind})")
            elif is_p3 is not None and KIND_P3.get(kind) is not None and is_p3(tag) != KIND_P3[kind]:
                fnd.stop("S-2", where, f"is_extend_start_tag({tag}) = {is_p3(tag)} for kind {kind}")
            if kind in ("H6", "H7"):
                # rev8 R8-1b: the record key is one dotted key, controller_settings["two_pressure.extend_start_rule"]
                cs = rec.get("controller_settings")
                if isinstance(cs, dict) and EXT_RULE_DOTTED in cs:
                    rule = cs[EXT_RULE_DOTTED]
                else:
                    rule, rp = first_path(rec, ("controller_settings.two_pressure.extend_start_rule",
                                                "resume_k1.two_pressure.extend_start_rule"))
                if rule is MISSING:
                    fnd.note(where, "two_pressure.extend_start_rule not in line (RV1-3.2 check not possible)")
                elif (kind == "H6") != (rule == "tracked_bound"):
                    fnd.stop("S-2", where, f"extend_start_rule {rule!r} for {kind}")
            # resume_k1 block
            rk, rk_path = first_path(rec, RESUME_PATHS[fmt])
            if rk is MISSING or not isinstance(rk, dict):
                b["missing"] += 1
                fnd.undec(where, "resume_k1 block missing (9.3)")
                continue
            if rk.get("applicable") is False:
                if kind in NO_K1_KINDS:
                    classes["n/a"] = classes.get("n/a", 0) + 1
                    continue
                fnd.stop("S-3", where, f"resume_k1.applicable false on a {kind} line (gate expected)")
                continue
            if kind in NO_K1_KINDS:
                fnd.note(where, f"resume_k1.applicable {rk.get('applicable')!r} on {kind}")
            # 4.2 record check
            if rk.get("k1_order_gate_request") != "preset":
                fnd.stop("S-3", where, f"k1_order_gate_request = {rk.get('k1_order_gate_request')!r}")
            if rk.get("k1_order_gate_effective") is not True:
                fnd.stop("S-3", where, f"k1_order_gate_effective = {rk.get('k1_order_gate_effective')!r}")
            scm = rk.get("slope_clearance_margin") if isinstance(rk.get("slope_clearance_margin"), dict) else {}
            if dig(scm, "settings.flat_soil_margin_order_gate", None) is not True:
                fnd.stop("S-3", where, "slope_clearance_margin.settings.flat_soil_margin_order_gate not true")
            fsm = num(dig(scm, "settings.flat_soil_margin_m", None))
            las = rk.get("liftoff_approach_slow", MISSING)
            check_las_settings(las.get("settings") if isinstance(las, dict) else None, where, fnd,
                               abl=(kind == "ABL"))
            fam = family_harness(rec, fmt, parent, file_meta)
            b["families"][fam] = b["families"].get(fam, 0) + 1
            sk, sk_src = skipped_count_harness(rec, rk)
            ec = dig(rk, "event_counts.flat_soil_margin_skipped_order", None)
            if sk_src != "resume_k1.event_counts" and isinstance(ec, int) and sk is not None and ec != sk:
                fnd.note(where, f"skipped:order {sk} ({sk_src}) vs resume_k1.event_counts {ec}")
            c = classify_k1(las, scm.get("order_gate", MISSING), sk, fam, where, fnd)
            cl = c.get("class") or "undecidable"
            classes[cl] = classes.get(cl, 0) + 1
            if fsm is not None and not same_value(fsm, 0.03):
                fnd.note(where, f"flat_soil_margin_m = {fsm}")
            # unchanged lines: stored hash (7.2)
            if cl == "unchanged" and stored:
                h, _ = first_path(rec, HASH_PATHS)
                anchors = stored.get(key)
                if not anchors:
                    hash_cmp["no_anchor"] += 1
                elif len(anchors) != 1:
                    fnd.stop("S-5", where, f"{len(anchors)} stored lines for the key")
                else:
                    hash_cmp["compared"] += 1
                    if h is MISSING or h is None:
                        fnd.undec(where, "commands_sha256 missing for the stored-hash check")
                    elif h == anchors[0]:
                        hash_cmp["equal"] += 1
                    else:
                        hash_cmp["differ"].append(key)
                        fnd.stop("S-5", where, "unchanged line: commands_sha256 differs from the stored line")
        want_n = HARNESS_FILE_COUNTS.get((bundle, kind))
        if want_n is not None and n_file != want_n:
            fnd.stop("S-15", f"{bundle}:{path.name}", f"{n_file} lines, rules say {want_n} for {kind}")
        if entry.get("expect_lines") is not None and n_file != int(entry["expect_lines"]):
            fnd.stop("S-15", f"{bundle}:{path.name}", f"{n_file} lines, manifest expects {entry['expect_lines']}")
        b["lines"] += n_file
        for k, v in classes.items():
            b["classes"][k] = b["classes"].get(k, 0) + v
        b["files"].append({"path": str(path), "sha256": sha256_file(path), "kind": kind, "format": fmt,
                           "lines": n_file, "classes": classes, "stored_hash": hash_cmp if stored else None,
                           "stored": entry.get("stored")})
        files_out.append(str(path))
    for bundle, b in bundles.items():
        want = HARNESS_COUNTS.get(bundle)
        if want is not None and b["lines"] != want:
            fnd_all[bundle].stop("S-15", bundle, f"{b['lines']} lines, rules (rev1) say {want}")
        b.update(fnd_all[bundle].as_dict())
        b["grade_scope"] = "436.8 layer only (4.1 / 4.2 / 7.2 / 9.3 / S-15); original-rule grades not recounted"
    codes = sorted({c for b in bundles.values() for c in b["stop_codes"]})
    return ({"bundles": bundles, "v5_options": mod_info, "stop_codes": codes},
            combine(b["status"] for b in bundles.values()))


# ----------------------------------------------------------------- anchors (P-1 / P-2, RV1-5)
def read_jsonl(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def cmd_anchors(args, repo):
    fnd = Findings()
    v5 = Path(args.v5_root) if args.v5_root else repo / _V5
    shas = {}
    for rel in ("d1.jsonl", "las/las_T1.jsonl", "las/las_T2.jsonl", "las/k1/k1_YP.jsonl", "soil_defer/s2d_SC.jsonl"):
        p = v5 / rel
        got = sha256_file(p) if p.is_file() else None
        shas[rel] = got
        if got != APPENDIX_B[rel]:
            # rev3 R3-F4: CRLF -> LF normalisation also for the appendix-B data files (disclosed)
            lf = hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest() if p.is_file() else None
            if lf == APPENDIX_B[rel]:
                fnd.note(rel, {"raw_sha256": got, "lf_sha256": lf, "note": "CRLF 변환만 다름"})
            else:
                fnd.stop("S-1", rel, f"appendix B sha {got} != {APPENDIX_B[rel]}")
    if fnd.stops:
        return {"appendix_b": shas, **fnd.as_dict()}, "stop"

    def ok_lines(rel):
        return [r for r in read_jsonl(v5 / rel) if "error" not in r]

    def index(lines, where):
        idx = {}
        for r in lines:
            idx.setdefault(job_key(r.get("job")), []).append(r)
        return idx

    t1 = [r for r in ok_lines("las/las_T1.jsonl") if dig(r, "las.candidate", None) == "b0"]
    t2 = [r for r in ok_lines("las/las_T2.jsonl") if dig(r, "las.candidate", None) == "b0"]
    yp = [r for r in ok_lines("las/k1/k1_YP.jsonl")
          if dig(r, "k1.sub_bundle", None) == "Y-Pa" and dig(r, "las.candidate", None) == "P0"]
    i_t1, i_t2, i_yp = index(t1, "T1"), index(t2, "T2"), index(yp, "YP")
    keys_192 = set(i_t1) | set(i_t2)
    if set(i_t1) & set(i_t2):
        fnd.stop("S-7", "anchors", f"T-1 / T-2 key overlap {len(set(i_t1) & set(i_t2))}")
    d1 = [r for r in ok_lines("d1.jsonl") if job_key(r.get("job")) not in keys_192
          and dig(r, "job.d1.group", None) == "H-R-0"]
    i_d1 = index(d1, "d1")
    sc = [r for r in ok_lines("soil_defer/s2d_SC.jsonl") if job_key(r.get("job")) not in set(i_yp)]
    i_sc = index(sc, "SC")
    counts = {"T1": len(i_t1), "T2": len(i_t2), "d1_rest": len(i_d1), "YP": len(i_yp), "SC_rest": len(i_sc)}
    dup = {n: sum(1 for v in i.values() if len(v) != 1) for n, i in
           (("T1", i_t1), ("T2", i_t2), ("d1_rest", i_d1), ("YP", i_yp), ("SC_rest", i_sc))}
    want_counts = {"T1": 8, "T2": 184, "d1_rest": 216, "YP": 165, "SC_rest": 291}
    for n, w in want_counts.items():
        if counts[n] != w or dup[n]:
            fnd.stop("S-7", f"anchor {n}", f"{counts[n]} keys ({dup[n]} not unique), RV1-5 says {w}")
    if args.h1 is None:
        return {"appendix_b": shas, "anchor_counts": counts, "anchor_duplicates": dup, **fnd.as_dict()}, fnd.status()
    h1 = [r for r in read_jsonl(Path(args.h1))]
    res = {"P-1": {"predicted": 0, "equal": 0, "differ": [], "no_anchor": [], "blocked_rigid": []},
           "P-2": {"predicted": 0, "equal": 0, "differ": [], "no_anchor": []},
           "unpredicted_stop_lines": 0}
    for r in h1:
        if "error" in r:
            fnd.undec(job_key(r.get("job")), "H-1 line has error")
            continue
        k = job_key(r.get("job"))
        group = dig(r, "job.d1.group", None)
        if group is None:
            fnd.undec(k, "job.d1.group missing")
            continue
        if group == "H-R-A-stop":
            res["unpredicted_stop_lines"] += 1
            continue
        if group in RIGID_GROUPS_H1:
            pred, sources = "P-1", (i_t1, i_t2, i_d1)
            dec = dig(r, "resume_k1.slope_clearance_margin.order_gate.decisions", None)
            if isinstance(dec, list) and any(isinstance(d, dict) and d.get("would_block") is True
                                             and d.get("r4_due_without_gate") is True for d in dec):
                res["P-1"]["blocked_rigid"].append(k)
                fnd.stop("S-7", k, "P-1: K1 decisions blocked on a rigid H-1 line")
        else:
            pred, sources = "P-2", (i_yp, i_sc)
        hits = [x for s in sources for x in s.get(k, [])]
        res[pred]["predicted"] += 1
        if len(hits) != 1:
            res[pred]["no_anchor"].append(k)
            fnd.stop("S-7", k, f"{pred}: {len(hits)} anchor lines for the key (exactly 1 required)")
            continue
        if r.get("commands_sha256") == hits[0].get("commands_sha256") and r.get("commands_sha256"):
            res[pred]["equal"] += 1
        else:
            res[pred]["differ"].append(k)
            fnd.stop("S-7", k, f"{pred}: commands_sha256 differs from the anchor")
    want = {"P-1": 408, "P-2": 456}
    for p, n in want.items():
        if res[p]["predicted"] != n:
            fnd.stop("S-7", p, f"{res[p]['predicted']} predicted lines, rules say {n}")
    if res["unpredicted_stop_lines"] != 4:
        fnd.note("H-R-A-stop", f"{res['unpredicted_stop_lines']} lines (rules: 4, not predicted)")
    return {"appendix_b": shas, "anchor_counts": counts, "h1": str(args.h1),
            "h1_sha256": sha256_file(args.h1), **res, **fnd.as_dict()}, fnd.status()


# ----------------------------------------------------------------- Chrono rows
def batch_rows(batch_dir):
    b = json.loads((Path(batch_dir) / "batch.json").read_text("utf-8"))
    return b, b.get("cases", [])


def engine_of(argv):
    s = " ".join(argv or [])
    if "run_S9.py" in s:
        return "SCM"
    if "run_S8C.py" in s:
        return "L2b"
    if "run_S6C.py" in s:
        return "L1-R"
    return "unknown"


def argv_value(argv, opt):
    if opt in argv:
        i = argv.index(opt)
        return argv[i + 1] if i + 1 < len(argv) else None
    for a in argv:
        if a.startswith(opt + "="):
            return a.split("=", 1)[1]
    return None


def argv_has(argv, opt):
    return any(a == opt or a.startswith(opt + "=") for a in argv)


def resolve_result(batch_dir, row, repo):
    for p in (dig(row, "s8c_check.result_json", None), dig(row, "s6c_check.result_json", None),
              row.get("result_json")):
        if isinstance(p, str) and p:
            q = Path(p)
            if q.is_file():
                return q
            s = p.replace("\\", "/")
            if "07_results/" in s:
                q = repo / ("07_results/" + s.split("07_results/", 1)[1])
                if q.is_file():
                    return q
    q = Path(batch_dir) / row["case"] / "result.json"
    if q.is_file():
        return q
    # L1-R (run_S6C.py) / L2b without s8c_check: 07_results/S6|S8/*<--tag>*<batch stamp>/<--only>/result.json
    argv = [str(a) for a in row.get("argv", [])]
    tag, only = argv_value(argv, "--tag"), argv_value(argv, "--only")
    parts = Path(batch_dir).name.split("_")
    stamp = "_".join(parts[-2:]) if len(parts) >= 2 else ""
    if tag and only:
        for sub in ("S6", "S8"):
            base = repo / "07_results" / sub
            if base.is_dir():
                for d in sorted(base.glob(f"*{tag}*{stamp}")):
                    q = d / only / "result.json"
                    if q.is_file():
                        return q
    return None


def departure_index(t, crawler_n, weight_n):
    """First sample of the first run with crawler normal < 0.01 W lasting >= 0.1 s (P3a-2)."""
    import numpy as np  # noqa: PLC0415
    mask = crawler_n < DEPARTURE_FRACTION_W * weight_n
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return None
    starts = idx[np.r_[True, np.diff(idx) > 1]]     # first sample of each run of True
    ends = idx[np.r_[np.diff(idx) > 1, True]]       # last sample of each run
    for s, e in zip(starts, ends):
        if t[e] - t[s] >= DEPARTURE_HOLD_S - 1e-9:
            return int(s)
    return None


def series_force_recount(step_path, weight_n):
    """Departure and per-leg 1 ms F_cyl recount (rules 9.1 C-8, 7.4; P5r4 judgement 8.2 table)."""
    import numpy as np  # noqa: PLC0415
    z = np.load(step_path, allow_pickle=False)
    t = np.asarray(z["t_s"], float)
    F = np.asarray(z["F_cyl_N"], float)
    cr = np.asarray(z["scm_crawler_normal_N"], float)
    i0 = departure_index(t, cr, weight_n)
    out = {"file_sha256": sha256_file(step_path), "rows": int(t.size)}
    if i0 is None:
        out["t_departure_s"] = None
        return out
    td = float(t[i0])
    dt = float(np.median(np.diff(t)))
    after = t >= td - 1e-12
    trans = after & (t <= td + TRANSIENT_WINDOW_S + 1e-9)
    late = t > td + TRANSIENT_WINDOW_S + 1e-9
    legs = []
    for i in range(4):
        fa = F[after, i]
        ta = t[after]
        j = int(np.argmin(fa))
        ft = F[trans, i]
        tt = t[trans]
        jt = int(np.argmin(ft))
        below = int(np.count_nonzero(ft < F_MIN_N - EPS_THR))
        below2 = int(np.count_nonzero(ft < F_MIN_N + G_BAND_N - EPS_THR))
        below_all = int(np.count_nonzero(fa < F_MIN_N - EPS_THR))
        legs.append({"F_min_after_N": float(fa[j]), "t_min_after_s": float(ta[j]),
                     "F_min_transient_N": float(ft[jt]), "t_min_transient_s": float(tt[jt]),
                     "F_min_late_N": float(F[late, i].min()) if np.any(late) else None,
                     "t_below_F_min_s": below * dt, "t_below_F_min_plus_2kN_s": below2 * dt,
                     "t_below_F_min_after_all_s": below_all * dt})
    truncated = bool(t[-1] < td + TRANSIENT_WINDOW_S - 1e-9)    # rev2 R2-5: run ends before the window end
    out.update(t_departure_s=td, dt_s=dt, window="[t_D, t_D + 8 s] for times (R2-5); t >= t_D for F_min_after (R2-6)",
               window_truncated_at_run_end=truncated, legs=legs,
               max_t_below_F_min_s=max(lg["t_below_F_min_s"] for lg in legs),
               max_t_below_F_min_plus_2kN_s=max(lg["t_below_F_min_plus_2kN_s"] for lg in legs))
    return out


def expected_chrono_tag(row, res, argv):
    cid = row.get("criteria_id") or dig(row, "r4368.criteria_id", None)
    arm = dig(row, "r4368.arm", None)
    setting = row.get("v5_setting")
    if setting is None and isinstance(res, dict):
        setting = "VB" if dig(res, "args.extend_start_tracked", False) else "V0"
    off = arm == "off" or argv_has(argv, "--las-off")
    if cid in ("C-6", "C-7"):
        return None, "openloop", off
    # rev9 R9-4: LS = v5 setting LS1..LS4 exactly (original 4.1 "VB / LS1~LS4 (③ on)"); an LS row needs a ③ tag
    ext = setting == "VB" or setting in LS_SETTINGS
    if off:
        return (TAG_C4OFF_VB if ext else TAG_C4OFF_V0), "C4OFF_" + ("VB" if ext else "V0"), True
    if ext:
        return TAG_VB, "VB", False
    return TAG_V0, "V0", False


LS_SETTINGS = ("LS1", "LS2", "LS3", "LS4")     # rev9 R9-4 (original 4.1 table, v5 criteria LS1~LS4)
_BATCH_DIR_RE = re.compile(r"^batch_(.+)_\d{8}_\d{6}$")


def bundle_of(batch_dir):
    """Folder-name part of ``batch_<full batch name>_<YYYYmmdd_HHMMSS>`` (rev10 R10-1a), else None."""
    m = _BATCH_DIR_RE.match(Path(batch_dir).name)
    return m.group(1) if m else None


ROWS_MANIFEST_REL = "06_analysis/02_control/verif_matrix/v5_resume_4368/chrono_rows_manifest.json"
# rev10 R10-1b / R10-2: per-row source cases of the LS reading (G-S counts these)
R10_SOURCE_FAIL = ("batch_name_unknown", "manifest_rows_0", "manifest_rows_many", "batch_cases_0",
                   "batch_cases_many")


def load_rows_manifest(path):
    """rev10 R10-1b: the manifest is a judging input. Missing, not JSON, or without ``batches`` -> (None,
    reason): input error (exit 2), the Chrono bundle is not judged (S-11)."""
    p = Path(path)
    if not p.is_file():
        return None, f"rows manifest absent: {p}"
    try:
        m = json.loads(p.read_text("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        return None, f"rows manifest not readable as JSON: {exc!r}"[:300]
    if not isinstance(m, dict) or not isinstance(m.get("batches"), dict):
        return None, "rows manifest has no 'batches' object"
    return m, None


def full_batch_name(batch, batch_dir, manifest):
    """rev10 R10-1a: the full batch name (``V5-RESUME-K1-`` prefix included) = ``batch.json`` top-level
    ``batch`` checked against the folder-name part; no key = folder-name part; a mismatch, nothing to
    determine it with, or a name that is not a manifest ``batches`` key = unknown. Returns (name, why)."""
    folder = bundle_of(batch_dir)
    key = batch.get("batch", MISSING) if isinstance(batch, dict) else MISSING
    if key is not MISSING:
        if not isinstance(key, str) or key != folder:
            return None, f"batch.json batch {key!r} != folder-name part {folder!r}"
        name = key
    elif folder is None:
        return None, "no batch key and the folder name is not batch_<name>_<YYYYmmdd_HHMMSS>"
    else:
        name = folder
    if name not in manifest.get("batches", {}):
        return None, f"{name!r} is not a manifest batch"
    return name, None


def r94_ls_row(manifest, batch_dir, batch, row):
    """rev9 R9-4 with rev10 R10-1: LS reading of one Chrono row from manifest
    ``batches.<full batch name>.rows[].v5_setting`` and ``batch.json`` ``cases[].v5_setting`` of the same
    ``case``. Both sources need exactly one row for the case (else ``undecidable``: batch name unknown,
    manifest rows 0 / several, batch.json cases 0 / several). With one row each: equal and in LS1..LS4 =
    ``ls``; equal and another value, or the value absent / None in both rows = ``not_ls``; one value only
    or different = ``undecidable``. The row name is not read. ``source_case`` holds the R10-1b case."""
    case = row.get("case")
    out = {"manifest_v5_setting": None, "batch_v5_setting": None, "source_ok": False}
    name, why = full_batch_name(batch, batch_dir, manifest)
    out["batch_name"] = name
    if name is None:
        out.update({"class": "undecidable", "source_case": "batch_name_unknown", "why": why})
        return out
    m_rows = manifest["batches"][name].get("rows") if isinstance(manifest["batches"][name], dict) else None
    m_hits = [r for r in m_rows if isinstance(r, dict) and r.get("case") == case] if isinstance(m_rows, list) else []
    b_cases = batch.get("cases") if isinstance(batch, dict) else None
    b_hits = [r for r in b_cases if isinstance(r, dict) and r.get("case") == case] if isinstance(b_cases, list) else []
    out.update(manifest_rows=len(m_hits), batch_cases=len(b_hits))
    for n, label in ((len(m_hits), "manifest_rows"), (len(b_hits), "batch_cases")):
        if n != 1:
            sc = f"{label}_{'0' if n == 0 else 'many'}"
            out.update({"class": "undecidable", "source_case": sc, "why": f"{n} {label.replace('_', ' ')} for the case"})
            return out
    out["source_ok"] = True
    m_val, b_val = m_hits[0].get("v5_setting"), b_hits[0].get("v5_setting")
    out.update(manifest_v5_setting=m_val, batch_v5_setting=b_val)
    if m_val is None and b_val is None:
        out.update({"class": "not_ls", "source_case": "both_values_absent"})
    elif m_val is None or b_val is None:
        out.update({"class": "undecidable", "source_case": "one_value_only", "why": "one value only"})
    elif m_val != b_val:
        out.update({"class": "undecidable", "source_case": "values_differ", "why": "the two values differ"})
    else:
        out.update({"class": "ls" if m_val in LS_SETTINGS else "not_ls", "source_case": "values_equal"})
    return out


GS_KEYS_SCM = ("c2_setup.k1_order_gate", "c2_setup.k1_order_gate_effective",
               "controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate",
               "controller_meta.slope_clearance_margin.order_gate.enabled",
               "controller_meta.slope_clearance_margin.order_gate.decisions",
               "p3b_ext.start_condition.crawler_attitude_deg", "p3b_ext.start_condition.R_c_operating",
               "args.floor_roll", "args.floor_pitch", "num_threads_chrono", "placement.omp_wait_policy",
               "hull_hook.requested", "hull_hook.mode", "hull_hook.fallback_reason", "events",
               "v5_hydraulics.controller_tag", "c2_setup.expect_controller.ok", "p3b.weight_N",
               "p3b.P3-3_leg_force.F_min_after_N", "p3b.P3-3_leg_force.F_min_transient_N")
# rev7 R7-4: t_min_after_s left the path-2 list (not in the R7-4 table, never read by path 2; keeping it as
# "always present" would stop rows that did not depart, keeping it conditional would invent a condition).
GS_KEYS_LAS_ON = ("controller_meta.liftoff_approach_slow.settings",)   # path-2 key, not in the R7-4 table
LAS_R74 = ("controller_meta.liftoff_approach_slow.start_s", "controller_meta.liftoff_approach_slow.end_s",
           "controller_meta.liftoff_approach_slow.end_reason", "controller_meta.liftoff_approach_slow.active_periods",
           "controller_meta.liftoff_approach_slow.ramp", "controller_meta.liftoff_approach_slow.ramp.periods_applied")
# rev7 R7-4 table (9 keys): key -> absent allowed when (row, res) holds; required otherwise.
GS_CONDITIONAL_R74 = {
    "p3b.P3-3_leg_force.F_min_after_N": ("p3b.departure.departed is False",
                                         lambda row, res: dig(res, "p3b.departure.departed", MISSING) is False),
    "p3b.P3-3_leg_force.F_min_transient_N": ("p3b.departure.departed is False",
                                             lambda row, res: dig(res, "p3b.departure.departed", MISSING) is False),
    "c2_setup.las_off": ("on arm (r4368.arm != 'off')", lambda row, res: dig(row, "r4368.arm", None) != "off"),
    **{k: ("off arm (r4368.arm == 'off')", lambda row, res: dig(row, "r4368.arm", None) == "off") for k in LAS_R74},
}
GS_CONDITIONAL = set(GS_CONDITIONAL_R74)   # kept name: the keys whose absence can be allowed
NONE_IS_VALUE = ("hull_hook.fallback_reason",) + tuple(GS_CONDITIONAL_R74)


# rev8 R8-3a name table (SCM level rows): <row>/step_series.npz law_locked, [N, 4] int8, legs FL FR RL RR,
# time axis = t_s of the same file (1 ms, same rows as the other keys), values 1 locked / 0 moving / -1 unarmed
LAW_LOCKED_KEY = "law_locked"
LAW_LOCKED_VALUES = (-1, 0, 1)
LAW_LOCKED_DT_S = 1e-3
LAW_LOCKED_DT_TOL_S = 1e-6     # path-2 tolerance on the 1 ms spacing (float sums of the Chrono step)


# rev9 R9-2: the same check on both R8-3a keys (engine -> file, time column of the same file)
LAW_LOCKED_FILES = {"SCM": ("step_series.npz", "t_s"), "L2b": ("pads.npz", "t")}
LEGS = ("FL", "FR", "RL", "RR")


def minus1_pattern(a):
    """rev9 R9-3 on a [N, 4] array with values in {-1, 0, 1}. Returns (patterns, problems, first_armed):
    ``none`` (no -1), ``pre_arming`` (-1 from the start, all four legs leave -1 at the same sample, no -1
    afterwards: locked, revision 6 section 6), else format errors ``whole_run`` (every sample and leg -1),
    ``after_arming`` (a -1 after a 0 or 1 on that leg), ``leg_mismatch`` (legs leave -1 at different
    samples, a leg never leaving included)."""
    import numpy as np  # noqa: PLC0415
    neg = a == -1
    if not neg.any():
        return ["none"], [], 0
    if neg.all():
        return ["whole_run"], ["R9-3: -1 over the whole run (no arming: no plant lock event for J11)"], None
    first = []
    for i in range(a.shape[1]):
        idx = np.flatnonzero(~neg[:, i])
        first.append(int(idx[0]) if idx.size else None)
    pats, prob = [], []
    after = [LEGS[i] for i in range(a.shape[1]) if first[i] is not None and neg[first[i]:, i].any()]
    if after:
        pats.append("after_arming")
        prob.append(f"R9-3: -1 after the first arming on {after}")
    if len(set(first)) > 1:
        pats.append("leg_mismatch")
        prob.append(f"R9-3: legs leave -1 at different samples {dict(zip(LEGS, first, strict=True))}")
    if not pats:
        pats.append("pre_arming")
        return pats, prob, first[0]
    return pats, prob, None


def law_locked_format(path, time_key="t_s"):
    """rev8 R8-3 / R8-3a with rev9 R9-2 / R9-3: presence and format of ``law_locked`` in ``path``
    (SCM ``step_series.npz`` with ``t_s``, L2b ``pads.npz`` with ``t``). Returns a dict with ``present``
    (key in the file), ``ok``, ``problems`` and ``failed_items`` (R9-2 items 1..6 that are not met; empty when
    the format is right) and ``minus1_patterns`` (R9-3). Values are not judged here (J11 is graded by the
    C-5 path 2); per-leg 0->1 / 1->0 counts are recorded (-1 before the first arming counts as locked)."""
    import numpy as np  # noqa: PLC0415
    p = Path(path)
    out = {"file": p.name, "time_key": time_key, "present": False, "ok": False, "problems": [],
           "failed_items": []}
    if not p.is_file():
        out["problems"].append(f"{p.name} absent")
        return out
    z = np.load(p, allow_pickle=False)
    if LAW_LOCKED_KEY not in z.files:
        out["problems"].append("law_locked key absent")
        return out
    out["present"] = True
    a = z[LAW_LOCKED_KEY]
    prob, items = out["problems"], out["failed_items"]

    def bad(item, why):
        prob.append(why)
        if item not in items:
            items.append(item)

    t = None
    if time_key not in z.files:                                     # R9-2 item 1
        bad("1_time_column", f"{time_key} absent (time axis of law_locked)")
    else:
        t = np.asarray(z[time_key], float)
        if t.ndim != 1:
            bad("1_time_column", f"{time_key} shape {tuple(t.shape)} (1-D time column required)")
            t = None
    out["shape"] = list(a.shape)
    if a.ndim != 2 or a.shape[1] != 4:                              # R9-2 item 2
        bad("2_shape", f"shape {tuple(a.shape)} ([N, 4] required)")
    elif t is not None and t.size != a.shape[0]:
        bad("2_shape", f"{time_key} rows {t.size} != law_locked rows {a.shape[0]}")
    if a.dtype != np.int8:                                          # R9-2 item 3
        bad("3_dtype", f"dtype {a.dtype} (int8 required)")
    values_ok = not (a.size and not np.isin(a, LAW_LOCKED_VALUES).all())
    if not values_ok:                                               # R9-2 item 4
        bad("4_values", f"values {sorted(set(np.unique(a).tolist()) - set(LAW_LOCKED_VALUES))} outside {{-1, 0, 1}}")
    if t is not None and t.size > 1:                                # R9-2 item 5
        dt = np.diff(t)
        off = np.abs(dt - LAW_LOCKED_DT_S) > LAW_LOCKED_DT_TOL_S
        out["max_abs_dt_error_s"] = float(np.max(np.abs(dt - LAW_LOCKED_DT_S)))
        if off.any():
            bad("5_spacing", f"{time_key} spacing not 1 ms at {int(off.sum())} steps (first {float(dt[off][0])!r} s)")
    if a.ndim == 2 and a.shape[1] == 4 and a.shape[0] > 0 and values_ok:   # R9-2 item 6 / R9-3
        pats, mprob, first = minus1_pattern(a)
        out["minus1_patterns"] = pats
        if "pre_arming" in pats:
            out["pre_arming_samples"] = first
        for why in mprob:
            bad("6_minus1", why)
    if not prob and a.shape[0] > 1:
        lk = a != 0             # revision 6 section 6: -1 (before the first arming) counts as locked
        out["transitions_per_leg"] = {leg: {"to_locked": int(np.count_nonzero(~lk[:-1, i] & lk[1:, i])),
                                            "to_unlocked": int(np.count_nonzero(lk[:-1, i] & ~lk[1:, i]))}
                                      for i, leg in enumerate(LEGS)}
    out["ok"] = not prob
    return out


def law_locked_target(argv, engine, kind):
    """(file name, time key) of the R8-3a law_locked record of a row, None when the row has none (L1-R,
    open loop, SCM rows other than ``run_S9.py level``)."""
    if kind == "openloop":
        return None
    if engine == "SCM" and "level" in argv:
        return LAW_LOCKED_FILES["SCM"]
    if engine == "L2b":
        return LAW_LOCKED_FILES["L2b"]
    return None


def r82_extend_start(res, argv, tag, is_p3, where, fnd):
    """rev8 R8-2 on a Chrono controller row. ③ is judged by the row tag only (4.1, rev3 R3-C8); the two
    request records must agree with it (argv ``--extend-start-tracked``; ``v5_hydraulics.hydraulic_options
    .extend_start_tracked``, key absent = off, only when the ``v5_hydraulics`` block exists), else S-2. On a ③
    row ``controller_meta.two_pressure.settings.extend_start_rule`` must be ``tracked_bound`` (other value =
    S-2; absent = J-P3 not judgeable, recorded: J-P3 is graded by the C-5 path 2). Non-③ rows: J-P3 not
    applicable, the key is not counted as missing."""
    if is_p3 is None or not isinstance(tag, str):
        return {"status": "tag_unreadable"}       # the tag check above already stopped (S-2)
    p3 = bool(is_p3(tag))
    rec = {"tag_extend_start": p3, "argv_extend_start_tracked": argv_has(argv, "--extend-start-tracked")}
    if rec["argv_extend_start_tracked"] != p3:
        fnd.stop("S-2", where, f"R8-2: argv --extend-start-tracked {rec['argv_extend_start_tracked']} vs tag ③ {p3}")
    v5h = res.get("v5_hydraulics")
    if isinstance(v5h, dict):
        ho = v5h.get("hydraulic_options")
        rec["v5_hydraulic_options_block"] = isinstance(ho, dict)
        rec["v5_extend_start_tracked"] = bool(ho.get("extend_start_tracked", False)) if isinstance(ho, dict) else False
        if rec["v5_extend_start_tracked"] != p3:
            fnd.stop("S-2", where, f"R8-2: v5_hydraulics.hydraulic_options.extend_start_tracked "
                                   f"{rec['v5_extend_start_tracked']} vs tag ③ {p3}")
    else:
        rec["v5_hydraulics_block"] = False     # argv only (R8-2)
    rule = dig(res, "controller_meta.two_pressure.settings.extend_start_rule", MISSING)
    rec["extend_start_rule"] = None if rule is MISSING else rule
    if not p3:
        rec["status"] = "not_applicable"
    elif rule is MISSING:
        rec["status"] = "applicable_rule_missing"
        fnd.note(where, "R8-2: ③ row without controller_meta.two_pressure.settings.extend_start_rule -> "
                        "J-P3 not judgeable (9.3; graded by the C-5 path 2)")
    elif rule != "tracked_bound":
        rec["status"] = "applicable_rule_wrong"
        fnd.stop("S-2", where, f"R8-2: extend_start_rule {rule!r} on a ③ row (tracked_bound required)")
    else:
        rec["status"] = "applicable"
    return rec


def gs_presence(row, res, keys):
    """11.2 key presence with rev7 R7-4: a table key is ``conditional_absent`` only when its absence
    condition holds, else ``result_missing`` (S-11); a key outside the table is ``present`` or ``absent``
    (S-11). A value None counts as present for the keys in NONE_IS_VALUE: R7-4 speaks of the key (an
    existing key with null, e.g. a LAS-b start_s of a row where LAS-b did not start, rev2 R2-2, is
    present); None fallback = no fallback. Other keys keep the earlier path-2 reading (None = absent)."""
    pres, bad = {}, []
    for k in keys:
        v = dig(res, k)
        here = v is not MISSING and (v is not None or k in NONE_IS_VALUE)
        if here:
            pres[k] = "present"
        elif k in GS_CONDITIONAL_R74:
            pres[k] = "conditional_absent" if GS_CONDITIONAL_R74[k][1](row, res) else "result_missing"
        else:
            pres[k] = "absent"
        if pres[k] in ("absent", "result_missing"):
            bad.append(k)
    return pres, bad


def chrono_row(batch_dir, batch, row, repo, is_p3, gs_mode, fnd, commits, manifest=None):
    case = row.get("case")
    argv = [str(a) for a in row.get("argv", [])]
    engine = engine_of(argv)
    cid = row.get("criteria_id") or dig(row, "r4368.criteria_id", None)
    where = f"{Path(batch_dir).name}:{case}"
    out = {"case": case, "criteria_id": cid, "engine": engine, "rc": row.get("rc"), "pool": row.get("pool"),
           "planned_pool": row.get("planned_pool"), "role": dig(row, "r4368.role", None),
           "d1_id": row.get("d1_id") or dig(row, "r4368.d1_id", None)}
    # rev9 R9-4 / rev10 R10-1: LS reading from the manifest row and the batch.json case (used for J11 on
    # C-5 rows only; J11 is graded by the C-5 path 2, here it is recorded and an LS row must carry a ③ tag)
    out["r94_ls"] = r94_ls_row(manifest, batch_dir, batch, row)
    if gs_mode and not out["r94_ls"]["source_ok"]:
        # rev10 R10-2: G-S checks the full batch name and exactly one case row in each source
        fnd.stop("S-11", where, f"G-S R10-2: {out['r94_ls']['source_case']} ({out['r94_ls'].get('why')})")
    head = dig(row, "code_at_launch.git.head", None)
    commits.setdefault(head, []).append(case)
    if dig(row, "code_at_launch.git.dirty", []) not in ([], None):
        fnd.stop("S-12", where, "dirty tree at launch")
    if row.get("rc") not in (0, None):
        fnd.undec(where, f"rc = {row.get('rc')} (run error, P-15)")
    rpath = resolve_result(batch_dir, row, repo)
    out["result_json"] = str(rpath) if rpath else None
    if rpath is None:
        fnd.undec(where, "result.json not found")
        return out
    res = json.loads(rpath.read_text("utf-8"))
    out["result_sha256"] = sha256_file(rpath)
    want_tag, kind, off = expected_chrono_tag(row, res, argv)
    out["kind"] = kind
    if kind == "openloop":
        out["r94_ls"]["class"] = "not_applicable"      # no controller: no LS reading (sources still checked)
    if cid == "C-5" and out["r94_ls"]["class"] == "undecidable":
        fnd.note(where, f"R9-4 / R10-1b: LS reading not judgeable ({out['r94_ls']['source_case']}: "
                        f"{out['r94_ls'].get('why')}): an actual fallback leg n_late > 0 on this row stops "
                        "(H-7 / L-e); the judgement document writes 'LS 판별 불가' and the case")
    # ---- G-S key presence (11.2, RV1-10 f): presence only, no values
    if gs_mode:
        keys = GS_KEYS_SCM + (() if off else GS_KEYS_LAS_ON) + tuple(k for k in GS_CONDITIONAL_R74
                                                                     if k not in GS_KEYS_SCM) \
            if engine == "SCM" else (
            "controller_tag", "expect_controller.ok", "expect_controller.controller_tag",
            "controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate",
            "controller_meta.slope_clearance_margin.order_gate.enabled",
            "controller_meta.slope_clearance_margin.order_gate.decisions",
            "controller_meta.liftoff_approach_slow.settings")
        if engine in ("L2b", "L1-R"):
            evp = Path(rpath).parent / "controller_events.json"
            out["gs_controller_events_json"] = "present" if evp.is_file() else "absent"
            if not evp.is_file():
                fnd.stop("S-11", where, "G-S: controller_events.json absent")
        if kind == "openloop":
            keys = ("v5_hydraulics.controller_options.applied", "p3a.checks", "num_threads_chrono",
                    "hull_hook.mode")
        elif engine == "SCM" and not isinstance(res.get("v5_hydraulics"), dict):
            # rev8 R8-2: SCM rows without a v5_hydraulics block (V0, S6SEED) are normal; their tag is the
            # --expect-controller value with c2_setup.expect_controller.ok
            keys = tuple(k for k in keys if k != "v5_hydraulics.controller_tag")
            out["gs_v5_hydraulics_block"] = False
        keys = tuple(dict.fromkeys(keys))
        pres, bad = gs_presence(row, res, keys)
        for k in bad:
            fnd.stop("S-11", where, f"G-S key {pres[k]}: {k}" + (
                f" (R7-4: absence allowed only when {GS_CONDITIONAL_R74[k][0]})" if k in GS_CONDITIONAL_R74 else ""))
        arm = dig(row, "r4368.arm", None)
        if engine == "SCM" and (arm == "off") != bool(off):
            fnd.note(where, f"r4368.arm {arm!r} vs path-2 off arm {off} (R7-4 uses r4368.arm)")
        out["gs_keys"] = pres
        out["gs_conditional_absent"] = sorted(k for k, v in pres.items() if v == "conditional_absent")
        if kind != "openloop":
            # rev9 R9-1: expect_controller.ok false or absent = S-2, and in G-S also S-11 (11.2 failure)
            ok_flag, ok_path = first_path(res, ("expect_controller.ok", "c2_setup.expect_controller.ok"))
            out["r91_expect_controller_ok"] = None if ok_flag is MISSING else ok_flag
            if ok_flag is not True:
                why = f"R9-1: expect_controller.ok = {'absent' if ok_flag is MISSING else repr(ok_flag)}"
                fnd.stop("S-2", where, why)
                fnd.stop("S-11", where, why + " (G-S failure, 11.2)")
        tgt = law_locked_target(argv, engine, kind)
        if tgt is not None:
            # rev8 R8-3 / rev9 R9-2, R9-5, R9-6: the 1 ms law_locked record is a G-S key (11.2) of every
            # SCM level and L2b row, whatever the row kind; absent or malformed = S-11
            ll = law_locked_format(Path(rpath).parent / tgt[0], tgt[1])
            ll["engine"] = engine
            out["gs_law_locked"] = ll
            if not ll["ok"]:
                fnd.stop("S-11", where, f"G-S law_locked (R9-2 / R9-5, {engine} {tgt[0]}): {'; '.join(ll['problems'])}")
        return out
    # ---- tag (4.1, RV1-10 a)
    if kind == "openloop":
        if dig(res, "v5_hydraulics.controller_options.applied", None) is not False:
            fnd.stop("S-2", where, "open-loop row: controller_options.applied is not false")
    else:
        exp_arg = argv_value(argv, "--expect-controller")
        if exp_arg != want_tag:
            fnd.stop("S-2", where, f"--expect-controller {exp_arg!r} != {want_tag!r}")
        rec_tag, tag_path = first_path(res, ("controller_tag", "v5_hydraulics.controller_tag"))
        ok_flag, _ = first_path(res, ("expect_controller.ok", "c2_setup.expect_controller.ok"))
        name, _ = first_path(res, ("expect_controller.name", "c2_setup.expect_controller.name",
                                   "expect_controller.controller_tag"))
        # rev8 R8-2 (original 6, RV1-10 a): the tag of a Chrono row is its --expect-controller value with
        # a true expect_controller check. A recorded tag must agree; SCM rows without a v5_hydraulics
        # block (V0, S6SEED) carry none, which is not a stop.
        tag = exp_arg if isinstance(exp_arg, str) else MISSING
        out["tag"] = None if tag is MISSING else tag
        out["tag_recorded"] = None if rec_tag is MISSING else rec_tag
        out["tag_source"] = "argv --expect-controller"
        if rec_tag is MISSING:
            if engine == "SCM" and not isinstance(res.get("v5_hydraulics"), dict):
                fnd.note(where, "no recorded controller_tag (no v5_hydraulics block): tag = --expect-controller (R8-2)")
            else:
                fnd.stop("S-2", where, f"recorded tag missing (expected {want_tag!r})")
        elif rec_tag != want_tag:
            fnd.stop("S-2", where, f"recorded tag {rec_tag!r} != {want_tag!r}")
        out["r91_expect_controller_ok"] = None if ok_flag is MISSING else ok_flag
        if ok_flag is not True:
            # rev9 R9-1: the bundle stops (S-2); J-P3 alone is not set to not judgeable
            fnd.stop("S-2", where, f"R9-1: expect_controller.ok = {'absent' if ok_flag is MISSING else repr(ok_flag)}")
        if name != want_tag:
            fnd.stop("S-2", where, f"expect_controller ok={ok_flag!r} name={name!r}")
        if is_p3 is not None and tag is not MISSING and isinstance(tag, str):
            p3_want = kind in ("VB", "C4OFF_VB")
            if is_p3(tag) != p3_want:
                fnd.stop("S-2", where, f"is_extend_start_tag({tag}) = {is_p3(tag)}")
            if out["r94_ls"]["class"] == "ls" and not is_p3(tag):
                fnd.stop("S-2", where, f"R9-4: LS row (v5_setting {out['r94_ls']['batch_v5_setting']}) with a non-③ tag {tag!r}")
        out["jp3_scope"] = r82_extend_start(res, argv, tag, is_p3, where, fnd)
    # ---- forbidden argv / env (4.2)
    for opt in CHRONO_FORBIDDEN_ARGV:
        if argv_has(argv, opt):
            allowed = off and kind != "openloop" and ((opt == "--las-off") or
                                                      (opt == "--k1-order-gate" and argv_value(argv, opt) == "on"))
            if not allowed:
                fnd.stop("S-3", where, f"forbidden argv {opt}")
    if off and not (argv_has(argv, "--las-off") and argv_value(argv, "--k1-order-gate") == "on"):
        fnd.stop("S-3", where, "C-4 off arm without '--las-off --k1-order-gate on'")
    if any("pre_" in Path(a).name and a.endswith("_preset_runner.py") for a in argv):
        fnd.stop("S-3", where, "pre_*_preset_runner.py in argv")
    start_env = row.get("start_env") if isinstance(row.get("start_env"), dict) else {}
    if SHADOW_ENV in start_env:
        fnd.stop("S-3", where, f"{SHADOW_ENV} in start_env")
    if engine == "SCM":
        for opt in SCM_FORBIDDEN_ARGV:
            if argv_has(argv, opt):
                fnd.stop("S-3", where, f"forbidden argv {opt}")
        for e in SCM_FORBIDDEN_ENV:
            if e in start_env:
                fnd.stop("S-3", where, f"{e} in start_env")
        if row.get("hull_hook_env") not in (None, {}, ""):
            fnd.stop("S-3", where, f"hull_hook_env = {row.get('hull_hook_env')!r}")
        henv = dig(res, "hull_hook.env", {})
        if isinstance(henv, dict):
            for e in SCM_FORBIDDEN_ENV:
                if henv.get(e) not in (None, ""):
                    fnd.stop("S-3", where, f"result hull_hook.env.{e} = {henv.get(e)!r}")
    # ---- record checks (4.2, RV1-10 b)
    if kind != "openloop":
        gate = dig(res, "c2_setup.k1_order_gate", None)
        eff = dig(res, "c2_setup.k1_order_gate_effective", None)
        if engine in ("L2b", "L1-R") and gate is None and eff is None:
            # L2b / L1-R results carry no c2_setup block: same meaning = no --k1-order-gate in argv
            # (request 'preset') and the order gate recorded on (effective)
            gate = "on" if argv_value(argv, "--k1-order-gate") == "on" else (
                "preset" if not argv_has(argv, "--k1-order-gate") else argv_value(argv, "--k1-order-gate"))
            eff = dig(res, "controller_meta.slope_clearance_margin.order_gate.enabled", None)
            fnd.note(where, "k1_order_gate request read from argv, effective from order_gate.enabled (L2b / L1-R, R2-3)")
            if not isinstance(res.get("controller_meta"), dict) or eff is None:
                fnd.undec(where, "controller_meta / order_gate.enabled missing (R2-3, 9.3)")
        if gate != ("on" if off else "preset"):
            fnd.stop("S-3", where, f"k1_order_gate request = {gate!r}")
        if eff is not True:
            fnd.stop("S-3", where, f"k1_order_gate_effective = {eff!r}")
        if dig(res, "controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate", None) is not True:
            fnd.stop("S-3", where, "flat_soil_margin_order_gate not true")
        las = dig(res, "controller_meta.liftoff_approach_slow")
        las_off_rec = dig(res, "c2_setup.las_off", None)
        if off:
            if las_off_rec is not True:
                fnd.stop("S-3", where, f"C-4 off arm: c2_setup.las_off = {las_off_rec!r}")
            if isinstance(las, dict) and dig(las, "settings.enable", False) is True:
                fnd.stop("S-3", where, "C-4 off arm: liftoff_approach_slow enabled")
        else:
            if las_off_rec not in (None, False):
                fnd.stop("S-3", where, f"c2_setup.las_off = {las_off_rec!r} on an on-arm row")
            check_las_settings(las.get("settings") if isinstance(las, dict) else None, where, fnd)
        # ---- K1 classification (7.2)
        events = res.get("events") if isinstance(res.get("events"), list) else None
        sk = None
        if events is not None:
            sk = sum(1 for e in events if isinstance(e, dict) and e.get("name") == EV_SKIP_ORDER)
        else:
            ev_path = Path(rpath).parent / "controller_events.json"
            if ev_path.is_file():
                parsed = [parse_c2event(s) for s in json.loads(ev_path.read_text("utf-8"))]
                if all(p is not None for p in parsed):
                    sk = sum(1 for p in parsed if p[1] == EV_SKIP_ORDER)
        fam = family_chrono(res, engine)
        out["family"] = fam
        out["k1"] = classify_k1(las if las is not None else MISSING,
                                dig(res, "controller_meta.slope_clearance_margin.order_gate"),
                                sk, fam, where, fnd, las_absent_ok=off)
        lasd = las if isinstance(las, dict) else {}
        out["las"] = {"start_s": lasd.get("start_s"), "end_s": lasd.get("end_s"),
                      "end_reason": lasd.get("end_reason")}
        if events is not None:
            out["fault_stroke_end"] = sum(1 for e in events if isinstance(e, dict)
                                          and event_name_split(str(e.get("name")))[0] == EV_FAULT_STROKE_END)
    # ---- identity (6, S-4)
    if engine == "SCM":
        ident = {"num_threads_chrono": res.get("num_threads_chrono"),
                 "start_env_OMP": start_env.get("OMP_WAIT_POLICY"),
                 "result_omp": dig(res, "placement.omp_wait_policy", None),
                 "hull_requested_row": row.get("hull_hook_requested"),
                 "hull_effective_row": dig(row, "hull_hook_effective.mode", None),
                 "hull_fallback_row": dig(row, "hull_hook_effective.fallback_reason", None),
                 "hull_mode_result": dig(res, "hull_hook.mode", None),
                 "hull_requested_result": dig(res, "hull_hook.requested", None),
                 "hull_fallback_result": dig(res, "hull_hook.fallback_reason", None),
                 "power_throttling_off_ok": dig(res, "placement.power_throttling_off_ok", None),
                 "affinity_logical_processors": dig(res, "placement.affinity_logical_processors", None),
                 # rev7 R7-6: the applied pool mask is recorded; a false affinity_mask_ok is written in the
                 # judgement document (6 "affinity change"), it is not a stop
                 "affinity_mask_process": dig(res, "placement.affinity_mask_process", None),
                 "affinity_mask_ok": dig(res, "placement.affinity_mask_ok", None),
                 "placement_applied_row": row.get("placement_applied")}
        out["identity"] = ident
        if ident["affinity_mask_ok"] is False:
            fnd.note(where, f"placement.affinity_mask_ok false (mask {ident['affinity_mask_process']!r}, R7-6: "
                            "write in the judgement document)")
        if ident["num_threads_chrono"] != SCM_THREADS or argv_value(argv, "--threads") != str(SCM_THREADS):
            fnd.stop("S-4", where, f"threads {ident['num_threads_chrono']!r} / argv {argv_value(argv, '--threads')!r}")
        if ident["start_env_OMP"] != "PASSIVE" or ident["result_omp"] != "PASSIVE":
            fnd.stop("S-4", where, f"OMP_WAIT_POLICY start_env {ident['start_env_OMP']!r} result {ident['result_omp']!r}")
        if not (ident["hull_requested_row"] == "fast" and ident["hull_effective_row"] == "fast"
                and ident["hull_mode_result"] == "fast" and ident["hull_fallback_row"] is None
                and ident["hull_fallback_result"] is None):
            fnd.stop("S-4", where, "hull hook not fast or fallback_reason present")
    pool_ok = row.get("pool") == row.get("planned_pool") == "pcore"
    out["hash_compare_allowed"] = bool(pool_ok)
    if not pool_ok:
        fnd.note(where, f"pool {row.get('pool')!r} planned {row.get('planned_pool')!r}: no hash comparison (6)")
    # ---- start condition (2, 7.4)
    sc = dig(res, "p3b_ext.start_condition", None)
    if isinstance(sc, dict):
        rc = resolve_rc(sc.get("crawler_attitude_deg"))
        out["R_c_path2"] = rc
        out["R_c_recorded"] = sc.get("R_c_operating")
        out["crawler_attitude_deg"] = sc.get("crawler_attitude_deg")
        out["floor_deg"] = [dig(res, "args.floor_roll", None), dig(res, "args.floor_pitch", None)]
        if rc is not None and num(sc.get("R_c_operating")) is not None and not same_value(rc, sc["R_c_operating"]):
            fnd.note(where, f"R_c path2 {rc} vs recorded {sc['R_c_operating']} (K-10 tolerance exceeded)")
        out["outside_start_condition"] = None if rc is None else bool(t_gt(rc, RC_LIMIT))
        if out["outside_start_condition"]:
            out["P3-3_within"] = first_path(res, ("p3b.checks.P3-3_within", "p3b.P3-3_leg_force.within"))[0]
            if out["P3-3_within"] is MISSING:
                out["P3-3_within"] = None
    # ---- 1 ms recount (9.1 C-8; done for every SCM level row that has the series)
    step = Path(rpath).parent / "step_series.npz"
    if engine == "SCM" and kind != "openloop" and step.is_file():
        w = num(dig(res, "p3b.weight_N", None))
        if w is None:
            fnd.undec(where, "p3b.weight_N missing: departure not recomputed")
        else:
            rec = series_force_recount(step, w)
            out["series"] = rec
            if rec.get("t_departure_s") is None:
                fnd.note(where, "t_D undefined: F<F_min times are missing (R2-5)")
                if cid in ("C-8a", "C-8b"):
                    fnd.undec(where, "t_D undefined (R2-5)")
            stored_td = num(dig(res, "p3b.departure.t_departure_s", None))
            if rec.get("t_departure_s") is not None and stored_td is not None and not same_value(rec["t_departure_s"], stored_td):
                fnd.note(where, f"departure path2 {rec['t_departure_s']} vs recorded {stored_td}")
            fa_rec = dig(res, "p3b.P3-3_leg_force.F_min_after_N", None)
            if rec.get("legs") and isinstance(fa_rec, list) and len(fa_rec) == 4:
                diffs = [i for i in range(4) if not same_value(rec["legs"][i]["F_min_after_N"], fa_rec[i])]
                if diffs:
                    fnd.note(where, f"F_min_after path2 vs recorded differ on legs {diffs}")
    # ---- rev8 R8-3 / rev9 R9-2, R9-5, R9-6: law_locked record of the SCM level and L2b rows (J11 input;
    # J11 itself is the C-5 path 2's). C-5 rows of both engines: not judgeable + stop and ask; other rows:
    # "input missing", recorded and counted (no stop).
    tgt = law_locked_target(argv, engine, kind)
    if tgt is not None:
        ll = law_locked_format(Path(rpath).parent / tgt[0], tgt[1])
        ll["engine"] = engine
        out["law_locked"] = ll
        if not ll["ok"]:
            if cid == "C-5":
                ll["handling"] = "c5_not_judgeable_stop"
                fnd.undec(where, f"R9-5: law_locked ({engine} {tgt[0]}) {'; '.join(ll['problems'])} -> J11 not "
                                 "judgeable (9.3); the fallback-leg n_late > 0 stop (H-7 / L-e) cannot be "
                                 "checked: stop the bundle and ask")
            else:
                ll["handling"] = "input_missing_recorded"
                fnd.note(where, f"R9-6: law_locked ({engine} {tgt[0]}) {'; '.join(ll['problems'])} (row outside "
                                "C-5: J11 input missing, recorded)")
    # ---- O-C5 (7.4, S-9, S-10)
    if cid in ("C-8a", "C-8b"):
        oc = {"k_from_argv": None}
        fr, fp = fnum(argv_value(argv, "--floor-roll")), fnum(argv_value(argv, "--floor-pitch"))
        if fr is not None and fp is not None:
            k = round(fr / OC5_BASE_DEG[0], K_DECIMALS)
            oc["k_from_argv"] = k
            oc["floor_consistent_with_k"] = (round(k * OC5_BASE_DEG[0], 4) == fr and round(k * OC5_BASE_DEG[1], 4) == fp)
            if not oc["floor_consistent_with_k"]:
                fnd.note(where, "floor arguments not of the form round(k * base, 4) for one k (5.4-8)")
        rc = out.get("R_c_path2")
        if rc is None:
            fnd.undec(where, "O-C5: R_c not computable")
        elif t_gt(rc, RC_LIMIT):
            fnd.stop("S-10", where, f"O-C5 main row R_c = {rc:.6f} > 1 (5.4-9)")
        else:
            legs = (out.get("series") or {}).get("legs")
            if not legs:
                fnd.undec(where, "O-C5: no 1 ms recount (no departure or no step_series.npz)")
            else:
                m = min(lg["F_min_after_N"] for lg in legs)
                leg_i = min(range(4), key=lambda i: legs[i]["F_min_after_N"])
                oc.update(m_path2_N=m, m_leg=("FL", "FR", "RL", "RR")[leg_i], margin_N=m - F_MIN_N)
                fa_rec = dig(res, "p3b.P3-3_leg_force.F_min_after_N", None)
                if isinstance(fa_rec, list) and all(num(x) is not None for x in fa_rec):
                    oc["m_result_json_N"] = min(fa_rec)
                if t_lt(m, F_MIN_N):
                    oc["tier"] = "stop"
                    fnd.stop("S-9", where, f"O-C5: m = {m:.3f} N < F_min (path-2 1 ms recount)")
                elif t_lt(m, F_MIN_N + G_BAND_N):
                    oc["tier"] = "record_with_margin"
                else:
                    oc["tier"] = "record"
                if "m_result_json_N" in oc:
                    tier_rj = ("stop" if t_lt(oc["m_result_json_N"], F_MIN_N) else
                               "record_with_margin" if t_lt(oc["m_result_json_N"], F_MIN_N + G_BAND_N) else "record")
                    oc["tier_result_json"] = tier_rj
                    # rev2 R2-6: either path below F_min -> S-9 until decided; the two-path comparison of
                    # tiers (R2-6 2..4) is done in the judgement document, not here
                    if tier_rj == "stop" and oc["tier"] != "stop":
                        fnd.stop("S-9", where, "O-C5: result.json m < F_min (R2-6 5)")
                    if tier_rj != oc["tier"]:
                        fnd.note(where, f"O-C5 tier path2 {oc['tier']} vs result.json m {tier_rj}")
        out["oc5"] = oc
    return out


def cmd_chrono(args, repo):
    is_p3, mod_info = load_is_extend_start(repo)
    fnd = Findings()
    rows = []
    commits = {}
    per_cid = {}
    mpath = Path(args.rows_manifest) if getattr(args, "rows_manifest", None) else repo / ROWS_MANIFEST_REL
    manifest, merr = load_rows_manifest(mpath)
    if manifest is None:
        # rev10 R10-1b: input error, the Chrono bundles are not judged (S-11, exit 2)
        fnd.stop("S-11", "rows manifest", f"R10-1b input error: {merr}")
        return {"rows": [], "rows_manifest": str(mpath), "rows_manifest_error": merr,
                "batches_not_judged": [str(b) for b in args.batch], **fnd.as_dict()}, fnd.status()
    for bd in args.batch:
        batch, cases = batch_rows(bd)
        gs_mode = args.gs or "-GS_" in Path(bd).name
        if batch.get("mixed_hull_mode") is True or "MIXED_HULL_MODE" in json.dumps(batch.get("warnings", "")):
            fnd.stop("S-4", Path(bd).name, "MIXED_HULL_MODE")
        for row in cases:
            r = chrono_row(bd, batch, row, repo, is_p3, gs_mode, fnd, commits, manifest)
            rows.append(r)
            if not gs_mode and dig(row, "r4368.role", None) not in ("probe",):
                per_cid[r["criteria_id"]] = per_cid.get(r["criteria_id"], 0) + 1
    real_heads = [h for h in commits if h is not None]
    if len(real_heads) > 1 and not args.gs:
        fnd.stop("S-12", "batches", f"{len(real_heads)} launch commits: {sorted(real_heads)}")
    if args.check_counts:
        for cid, (lo, hi) in CHRONO_COUNTS.items():
            n = per_cid.get(cid, 0)
            if not lo <= n <= hi:
                fnd.stop("S-15", cid, f"{n} rows, rules say {lo}..{hi}")
        if args.c2_expected is not None and per_cid.get("C-2", 0) != args.c2_expected:
            fnd.stop("S-15", "C-2", f"{per_cid.get('C-2', 0)} rows, H-2 output says {args.c2_expected}")
        if args.c2_psc is not None and args.c2_psc > 2:
            fnd.stop("S-15", "C-2", f"PS-c rows {args.c2_psc} > 2 (RV1-10 g)")
        # rev2 R2-8: the four fixed C-2 rows exactly once each, + RV1-10 g ranges
        c2 = [r for r in rows if r.get("criteria_id") == "C-2"]
        fixed = [r for r in c2 if r.get("d1_id") in C2_FIXED]
        psc = [r for r in c2 if r not in fixed and ("PSC" in str(r.get("d1_id")) or "D1PSC" in str(r.get("case")))]
        extra = [r for r in c2 if r not in fixed and r not in psc]
        ids = sorted(str(r.get("d1_id")) for r in fixed)
        if ids != sorted(C2_FIXED):
            fnd.stop("S-15", "C-2", f"fixed rows {ids}, rules say {sorted(C2_FIXED)} once each (R2-8)")
        if not (0 <= len(extra) <= 4 and len(psc) <= 2 and 4 <= len(c2) <= 10):
            fnd.stop("S-15", "C-2", f"baseline extra {len(extra)} (0..4), PS-c {len(psc)} (0..2), total {len(c2)} (4..10)")
    out_rows = [{k: v for k, v in r.items()} for r in rows]
    outside = [r["case"] for r in rows if r.get("outside_start_condition")]
    k1_table = {}
    for r in rows:
        cl = (r.get("k1") or {}).get("class")
        if cl:
            k1_table.setdefault(r.get("criteria_id"), {}).setdefault(cl, 0)
            k1_table[r.get("criteria_id")][cl] += 1
    ll_rows = [r.get("gs_law_locked") or r.get("law_locked") for r in rows]
    ll_rows = [x for x in ll_rows if isinstance(x, dict)]
    law_locked_check = {"rows": len(ll_rows),
                        "missing": sum(1 for x in ll_rows if not x["present"]),
                        "problems": sum(1 for x in ll_rows if x["present"] and not x["ok"])}
    # rev9 R9-8 G-S record items: R9-2 per item, R9-3 per -1 pattern, per engine; R9-6 outside-C-5 inputs
    r9_ll = {"rows": len(ll_rows), "by_engine": {}, "missing": 0, "failed_items": {}, "minus1_patterns": {},
             "c5_not_judgeable": 0, "outside_c5_input_missing": 0,
             "max_abs_dt_error_s": max((x["max_abs_dt_error_s"] for x in ll_rows if "max_abs_dt_error_s" in x),
                                       default=None)}
    for x in ll_rows:
        e = r9_ll["by_engine"].setdefault(x.get("engine", "?"), {"rows": 0, "ok": 0, "missing": 0, "malformed": 0})
        e["rows"] += 1
        e["ok" if x["ok"] else ("missing" if not x["present"] else "malformed")] += 1
        r9_ll["missing"] += int(not x["present"])
        for it in x.get("failed_items", []):
            r9_ll["failed_items"][it] = r9_ll["failed_items"].get(it, 0) + 1
        for pt in x.get("minus1_patterns", []):
            r9_ll["minus1_patterns"][pt] = r9_ll["minus1_patterns"].get(pt, 0) + 1
        r9_ll["c5_not_judgeable"] += int(x.get("handling") == "c5_not_judgeable_stop")
        r9_ll["outside_c5_input_missing"] += int(x.get("handling") == "input_missing_recorded")
    r91 = {"rows_checked": sum(1 for r in rows if "r91_expect_controller_ok" in r),
           "s2": sum(1 for r in rows if "r91_expect_controller_ok" in r and r["r91_expect_controller_ok"] is not True)}
    r94 = {"rows_manifest": str(mpath), "rows_manifest_sha256": sha256_file(mpath), "classes": {},
           "ls_rows": [], "undecidable_rows": [], "c5_undecidable_rows": [],
           # rev10 R10-2: per-row source cases and the batch-name / one-row-per-source check
           "source_cases": {}, "source_check": {"rows": 0, "ok": 0, "failed": 0}, "batch_names": {}}
    for r in rows:
        rl = r.get("r94_ls") or {}
        if "source_case" in rl:
            r94["source_cases"][rl["source_case"]] = r94["source_cases"].get(rl["source_case"], 0) + 1
            r94["source_check"]["rows"] += 1
            r94["source_check"]["ok" if rl.get("source_ok") else "failed"] += 1
            bn = str(rl.get("batch_name"))
            r94["batch_names"][bn] = r94["batch_names"].get(bn, 0) + 1
        cl = rl.get("class")
        if cl:
            r94["classes"][cl] = r94["classes"].get(cl, 0) + 1
            if cl == "ls":
                r94["ls_rows"].append(r["case"])
            elif cl == "undecidable":
                r94["undecidable_rows"].append(r["case"])
                if r.get("criteria_id") == "C-5":
                    r94["c5_undecidable_rows"].append(r["case"])
    jp3 = {}
    for r in rows:
        st = (r.get("jp3_scope") or {}).get("status")
        if st:
            jp3[st] = jp3.get(st, 0) + 1
    return {"rows": out_rows, "rows_per_criteria_id": per_cid, "launch_commits": {str(k): v for k, v in commits.items()},
            "R8-3_law_locked_check": law_locked_check, "R8-2_jp3_scope": jp3,
            "R9-2_law_locked_check": r9_ll, "R9-1_expect_controller": r91, "R9-4_ls_rows": r94,
            "outside_start_condition_rows": outside, "k1_table": k1_table, "v5_options": mod_info,
            "grade_scope": "436.8 layer (4.1 / 4.2 / 6 / 7.2 / 7.4 / O-C5); original Chrono judgement blocks "
                           "(D-1 rules 11, rev12 2.2) not recounted", **fnd.as_dict()}, fnd.status()


# ----------------------------------------------------------------- O-C5 floor-scale procedure (5.4)
def cmd_oc5k(args, repo):
    """5.4 steps 3..8 with RV1-10 d (k rounded to 4 decimals at once) and e (PROBE_DURATION 7 s).

    ``--probe`` lists the counted probes in run order; a probe without R_c at 7 s may be followed by
    its doubled (14 s) rerun, which is not counted (5.4-3)."""
    fnd = Findings()
    row = args.row
    k = OC5_K1[row]
    ks, rcs, steps = [], [], []
    chosen = None
    pending_double = False
    next_k = k
    for ppath in args.probe:
        res = json.loads(Path(ppath).read_text("utf-8"))
        att = dig(res, "p3b_ext.start_condition.crawler_attitude_deg", None)
        fr, fp = num(dig(res, "args.floor_roll", None)), num(dig(res, "args.floor_pitch", None))
        dur = num(dig(res, "args.duration", None))
        want = [round(k * OC5_BASE_DEG[0], 4), round(k * OC5_BASE_DEG[1], 4)]
        rc = resolve_rc(att)
        st = {"probe_file": str(ppath), "k": k, "floor_args": [fr, fp], "floor_want": want, "duration_s": dur,
              "R_c_recorded": dig(res, "p3b_ext.start_condition.R_c_operating", None), "R_c_path2": rc,
              "doubled_rerun": pending_double}
        steps.append(st)
        n = len(ks) + 1
        if not (same_value(fr, want[0]) and same_value(fp, want[1])):
            fnd.stop("S-10", f"probe{n}", f"floor args {fr},{fp} != round(k*base, 4) {want}")
            break
        want_dur = 2 * PROBE_DURATION_S if pending_double else PROBE_DURATION_S
        if dur is None or not same_value(dur, want_dur):
            fnd.note(f"probe{n}", f"duration {dur} (expected {want_dur} s, RV1-10 e)")
        if rc is None:
            if pending_double:
                fnd.stop("S-10", f"probe{n}", "R_c missing after the doubled rerun (5.4-3)")
                break
            pending_double = True
            continue
        pending_double = False
        ks.append(k)
        rcs.append(rc)
        if t_absle(rc, OC5_TARGET, OC5_TOL):
            chosen = k
            break
        if len(ks) >= OC5_MAX_PROBES:
            fnd.stop("S-10", f"probe{n}", "third probe still outside 0.95 +- 0.02 (5.4-7)")
            break
        if len(ks) == 1:
            next_k = round(ks[0] * OC5_TARGET / rcs[0], K_DECIMALS)
        else:
            if rcs[1] == rcs[0]:
                fnd.stop("S-10", f"probe{n}", "R_c(k2) = R_c(k1): secant undefined (5.4-7)")
                break
            next_k = round(ks[0] + (OC5_TARGET - rcs[0]) * (ks[1] - ks[0]) / (rcs[1] - rcs[0]), K_DECIMALS)
        if not (0.0 < next_k <= 1.0):
            fnd.stop("S-10", f"probe{n}", f"next k {next_k} not in (0, 1] (5.4-7)")
            break
        k = next_k
    if chosen is None and not fnd.stops:
        fnd.undec("procedure", f"not finished after {len(ks)} counted probe(s); next k = {k}"
                  + (" (doubled rerun pending)" if pending_double else ""))
    out = {"row": row, "k1": OC5_K1[row], "steps": steps, "k": chosen,
           "floor_deg": None if chosen is None else [round(chosen * OC5_BASE_DEG[0], 4), round(chosen * OC5_BASE_DEG[1], 4)],
           "n_probes_counted": len(ks), "n_probe_files": len(steps), **fnd.as_dict()}
    return out, fnd.status()


# ----------------------------------------------------------------- J_P reuse (7.3)
def cmd_jp(args, repo):
    fnd = Findings()
    shadow = read_jsonl(args.shadow)
    sh = {}
    for s in shadow:
        run = dig(s, "job.chrono_run", None)
        if run:
            sh.setdefault(run.replace("\\", "/"), []).append(s)
    runs = []
    for bd in args.batch:
        batch, cases = batch_rows(bd)
        for row in cases:
            rpath = resolve_result(bd, row, repo)
            where = f"{Path(bd).name}:{row.get('case')}"
            item = {"case": row.get("case"), "batch": Path(bd).name}
            if rpath is None:
                item["readable"] = False
                fnd.note(where, "result.json not found")
                runs.append(item)
                continue
            run_id = f"{rpath.parent.parent.name}/{rpath.parent.name}"
            ev_path = rpath.parent / "controller_events.json"
            item["chrono_run"] = run_id
            if not ev_path.is_file():
                item["readable"] = False
                runs.append(item)
                continue
            raw = json.loads(ev_path.read_text("utf-8"))
            parsed = [parse_c2event(s) if isinstance(s, str) else None for s in raw]
            item["events_sha256"] = sha256_file(ev_path)
            item["n_events"] = len(raw)
            if any(p is None for p in parsed):
                item["readable"] = False
                item["unparsed"] = sum(p is None for p in parsed)
                runs.append(item)
                continue
            item["readable"] = True
            names = [event_name_split(p[1])[0] for p in parsed]
            item["n_flat_soil_margin"] = sum(1 for nm in names if nm == EV_FLAT)
            item["n_soil_mode_start"] = sum(1 for nm in names if nm == EV_SOIL_START)
            s = sh.get(run_id, [])
            item["shadow_entries"] = len(s)
            item["shadow_silent"] = (len(s) == 1 and s[0].get("status") == "silent" and s[0].get("first_fire_t_s") is None)
            item["cond1"] = item["shadow_silent"]
            item["cond2"] = item["n_flat_soil_margin"] == 0 and item["n_soil_mode_start"] == 0
            runs.append(item)
    n = len(runs)
    reuse = (n == 12 and all(r.get("readable") and r.get("cond1") and r.get("cond2") for r in runs))
    if n != 12:
        fnd.note("jp", f"{n} J_P runs read (rules: 12)")
    out = {"runs": runs, "n_runs": n, "reuse": reuse, "shadow_sha256": sha256_file(args.shadow),
           "decision": "reuse stored judgement" if reuse else "rerun J_P 12 rows in bundle JP (5.2)", **fnd.as_dict()}
    return out, "pass" if not fnd.stops else "stop"


# ----------------------------------------------------------------- open loop (C-6 / C-7)
def load_analyse(script):
    """The ``analyse`` definition of openloop_compare.py without running its module-level code."""
    src = Path(script).read_text("utf-8")
    tree = ast.parse(src)
    keep = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef)):
            if isinstance(node, ast.FunctionDef) and node.name not in ("first_run", "plane_fit", "analyse"):
                continue
            keep.append(node)
        elif isinstance(node, ast.Assign) and all(isinstance(t, ast.Name) and t.id in ("F_MIN", "T_LIFT", "PAD_XY")
                                                    for t in node.targets):
            keep.append(node)
    mod = ast.Module(body=keep, type_ignores=[])
    ns = {}
    exec(compile(mod, str(script), "exec"), ns)  # noqa: S102 - repository script cited by the rules
    return ns["analyse"], hashlib.sha256(src.encode("utf-8")).hexdigest()


def yaml_vmax(repo):
    """YAML actuator.max_speed_m_s (rev2 R2-4)."""
    text = (repo / "02_params" / "rexome33.yaml").read_text("utf-8")
    try:
        import yaml  # noqa: PLC0415
        return float(yaml.safe_load(text)["actuator"]["max_speed_m_s"])
    except Exception:  # noqa: BLE001 - fall back to the plain text block
        m = re.search(r"(?ms)^actuator:\s*\n(.*?)(?=^\S)", text + "\nEND:\n")
        v = re.search(r"^\s+max_speed_m_s:\s*([0-9.eE+-]+)", m.group(1), re.M) if m else None
        return float(v.group(1)) if v else None


def speed_ratio_vu(run_dir, vmax, t0=8.5):
    """r_vu (R2-4): per leg median v/u of the flow_series 1 ms rows with t0 < t <= end and u >= 0.1 v_max."""
    import numpy as np  # noqa: PLC0415
    p = Path(run_dir) / "flow_series.npz"
    if not p.is_file() or vmax is None:
        return None
    z = np.load(p, allow_pickle=False)
    cols = [str(c) for c in z["columns"]]
    rows = z["rows"]
    t = rows[:, cols.index("t")]
    out = {}
    for leg in ("FL", "FR", "RL", "RR"):
        u, v = rows[:, cols.index(f"u_{leg}")], rows[:, cols.index(f"v_{leg}")]
        m = (t > t0 + EPS_THR) & (u >= 0.1 * vmax - EPS_THR)
        out[leg] = float(np.median(v[m] / u[m])) if np.any(m) else None
    return {"per_leg": out, "window_s": [t0, float(t[-1])], "v_max_m_s": vmax, "rows_file": "flow_series.npz"}


def speed_ratio_v(run_dir, vmax, t0=10.0, t1=20.0):
    """r_v (R2-4): per leg (s_motor(last) - s_motor(first)) / (t_last - t_first) / v_max over t0 <= t <= t1."""
    import numpy as np  # noqa: PLC0415
    z = np.load(Path(run_dir) / "series.npz", allow_pickle=False)
    t, sm = z["t_s"], z["s_motor_m"]
    m = (t >= t0 - EPS_THR) & (t <= t1 + EPS_THR)
    if vmax is None or np.count_nonzero(m) < 2:
        return None
    idx = np.flatnonzero(m)
    v = (sm[idx[-1]] - sm[idx[0]]) / (t[idx[-1]] - t[idx[0]]) / vmax
    return {"per_leg": dict(zip(("FL", "FR", "RL", "RR"), map(float, v))), "window_s": [float(t[idx[0]]), float(t[idx[-1]])],
            "v_max_m_s": vmax}


def cmd_openloop(args, repo):
    fnd = Findings()
    script = Path(args.script) if args.script else repo / _V5 / "paper_runs/scripts/openloop_compare.py"
    analyse, ssha = load_analyse(script)
    vmax = yaml_vmax(repo)
    runs = {}
    for spec in args.run:
        label, d = spec.split("=", 1)
        d = Path(d)
        try:
            o, _ = analyse(d)
        except Exception as exc:  # noqa: BLE001
            fnd.undec(label, f"analyse failed: {exc!r}")
            continue
        o["r_vu"] = speed_ratio_vu(d, vmax)      # P-10 compares this (R2-4); None for V0 (no flow record)
        o["r_v"] = speed_ratio_v(d, vmax)        # P-11 / P-11b compare this (R2-4)
        pre = [x for x in o.get("pre_liftoff_min_F_kN", []) if x is not None]
        o["spec_11047_flag"] = bool(pre) and any(t_lt(x * 1e3, F_MIN_N) for x in pre)
        p3a = o.get("stored_p3a_checks") or {}
        if isinstance(p3a, dict):
            bad = [k for k, v in p3a.items() if k.startswith("P3a-1") and v is False]
            if bad:
                fnd.note(label, f"P3a-1 failure {bad} (7.5: write separately)")
        if "flow" in o:
            ls = o["flow"].get("limited_s")
            o["flow_limited_rows_zero"] = (isinstance(ls, dict) and all((num(v) or 0) == 0 for v in ls.values()))
        runs[label] = o
    return {"script": str(script), "script_sha256": ssha, "runs": runs, **fnd.as_dict()}, fnd.status()


# ----------------------------------------------------------------- K-10 compare (9.2)
def flatten(obj, prefix="", out=None):
    if out is None:
        out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            flatten(v, f"{prefix}.{k}" if prefix else str(k), out)
    elif isinstance(obj, list) and obj and all(isinstance(x, (dict, list)) for x in obj):
        for i, v in enumerate(obj):
            flatten(v, f"{prefix}[{i}]", out)
    else:
        out[prefix] = obj
    return out


def cmd_compare(args, repo):
    a = flatten(json.loads(Path(args.a).read_text("utf-8")))
    b = flatten(json.loads(Path(args.b).read_text("utf-8")))
    if args.map:
        mp = json.loads(Path(args.map).read_text("utf-8"))
        pairs = [(x, y) for x, y in mp.items()]
    else:
        pairs = [(k, k) for k in sorted(set(a) & set(b))]
    diffs = []
    for ka, kb in pairs:
        va, vb = a.get(ka, MISSING), b.get(kb, MISSING)
        if va is MISSING or vb is MISSING:
            diffs.append({"a": ka, "b": kb, "why": "missing", "va": None if va is MISSING else va,
                          "vb": None if vb is MISSING else vb})
            continue
        if isinstance(va, list) and isinstance(vb, list):
            eq = len(va) == len(vb) and all(same_value(x, y) for x, y in zip(va, vb))
        else:
            eq = same_value(va, vb)
        if not eq:
            diffs.append({"a": ka, "b": kb, "va": va, "vb": vb})
    out = {"a": str(args.a), "b": str(args.b), "a_sha256": sha256_file(args.a), "b_sha256": sha256_file(args.b),
           "n_pairs": len(pairs), "n_diff": len(diffs), "diffs": diffs[:500],
           "only_a": sorted(set(a) - set(b))[:200] if not args.map else [],
           "only_b": sorted(set(b) - set(a))[:200] if not args.map else []}
    return out, "pass" if not diffs else "fail"


# ----------------------------------------------------------------- main
EXIT = {"pass": 0, "fail": 1, "undecidable": 1, "stop": 2}


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=None, help="repository root (default: 5 levels above this file)")
    ap.add_argument("--out", default=None, help="output JSON path")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seal")
    h = sub.add_parser("harness")
    h.add_argument("--manifest", required=True)
    a = sub.add_parser("anchors")
    a.add_argument("--h1", default=None, help="h1_d1.jsonl (omit: anchor selection counts only)")
    a.add_argument("--v5-root", default=None)
    c = sub.add_parser("chrono")
    c.add_argument("--batch", action="append", required=True)
    c.add_argument("--gs", action="store_true", help="G-S key presence only")
    c.add_argument("--check-counts", action="store_true")
    c.add_argument("--c2-expected", type=int, default=None)
    c.add_argument("--c2-psc", type=int, default=None)
    c.add_argument("--rows-manifest", default=None,
                   help="chrono_rows_manifest.json for the rev9 R9-4 / rev10 R10-1 LS reading (default: "
                        "<repo>/" + ROWS_MANIFEST_REL + "; missing or unreadable = input error, S-11)")
    o = sub.add_parser("oc5k")
    o.add_argument("--row", choices=sorted(OC5_K1), required=True)
    o.add_argument("--probe", action="append", required=True, help="probe result.json, in run order")
    j = sub.add_parser("jp")
    j.add_argument("--shadow", required=True)
    j.add_argument("--batch", action="append", required=True)
    ol = sub.add_parser("openloop")
    ol.add_argument("--run", action="append", required=True, help="label=run_dir")
    ol.add_argument("--script", default=None)
    cm = sub.add_parser("compare")
    cm.add_argument("--a", required=True)
    cm.add_argument("--b", required=True)
    cm.add_argument("--map", default=None)
    return ap


CMDS = {"harness": cmd_harness, "anchors": cmd_anchors, "chrono": cmd_chrono, "oc5k": cmd_oc5k,
        "jp": cmd_jp, "openloop": cmd_openloop, "compare": cmd_compare}


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    repo = Path(args.repo) if args.repo else Path(__file__).resolve().parents[5]
    tool_sha = sha256_file(Path(__file__))
    summary = {"tool": TOOL_NAME, "version": TOOL_VERSION, "tool_sha256": tool_sha, "cmd": args.cmd}
    try:
        seals = check_seals(repo)
        if not seals["ok"]:
            report = {"seals": seals, "status": "stop", "stop_codes": ["S-1"]}
            status = "stop"
        elif args.cmd == "seal":
            report, status = {"seals": seals}, "pass"
        else:
            body, status = CMDS[args.cmd](args, repo)
            report = {"seals": {"ok": True, "rules_sha256": RULES_SHA, "rev1_sha256": REV1_SHA, "rev2_sha256": REV2_SHA, "rev3_sha256": REV3_SHA, "rev4_sha256": REV4_SHA, "rev5_sha256": REV5_SHA, "rev6_sha256": REV6_SHA, "rev7_sha256": REV7_SHA, "rev8_sha256": REV8_SHA, "rev9_sha256": REV9_SHA, "rev10_sha256": REV10_SHA,
                                "eol_only": seals.get("eol_only", []),
                                "eol_only_detail": {k: v for k, v in seals["appendix_a"].items() if v.get("eol_only")}},
                      **body}
        report.update(tool=TOOL_NAME, version=TOOL_VERSION, tool_sha256=tool_sha, cmd=args.cmd,
                      argv=sys.argv[1:] if argv is None else list(argv),
                      created=_dt.datetime.now().astimezone().isoformat(timespec="seconds"), status=status)
        text = json.dumps(report, indent=1, ensure_ascii=False, default=str)
        out_sha = None
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(text + "\n", encoding="utf-8", newline="\n")
            out_sha = sha256_file(args.out)
        code = EXIT[status]
        summary.update(status=status, exit=code, out=args.out, out_sha256=out_sha,
                       stop_codes=report.get("stop_codes", []))
        if "decision" in report:
            summary["decision"] = report["decision"]
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        code = 3
        summary.update(status="tool_error", exit=3, error=repr(exc)[:300], out_sha256=None)
    print(json.dumps(summary, ensure_ascii=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
