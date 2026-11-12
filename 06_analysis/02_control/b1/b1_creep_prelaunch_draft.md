# B1 크리프 근거 `V5-B1-CREEP` — 실행 전 기록(prelaunch) 초안

- 작성: control-expert, 2026-11-11. **초안이다.** 합친 원판 후보 `b1_creep_basis_rules_seal_candidate_draft.md`(같은 폴더) 4.1절 I-1~I-17이 요구하는 항목을 한곳에 모은 틀이다.
- 이 파일은 **추적되는 틀**이고 값을 채우지 않는다. 실제 prelaunch는 실행 직전에 **추적 밖**(배치 폴더 `07_results/S9/batch_V5-B1-CREEP_<stamp>/B1_prelaunch.json`, `.gitignore` 대상)에 채운다. 추적 파일에 값을 채우면 실행 정체성(추적 변경 0)과 자리표시 점검이 충돌한다(P5r4 rev3 RV3-3 교훈).
- 판정이 끝난 뒤 채운 사본을 `06_analysis/02_control/b1/prelaunch/B1_prelaunch.json`으로 커밋한다(`.gitattributes` `b1/** -text`).
- 아래 JSON의 `{이름}`은 채울 자리다. `placeholder_scan.py` 허용 목록은 이 파일에만 적용한다(`--allow` 대상 = 이 파일 이름). 채운 prelaunch에는 `{`로 시작하는 값이 0개여야 한다.

## 1. 채우는 순서와 시각

| 단계 | 기록 | 누가 | 이 단계 전에 끝나야 하는 것 |
|---|---|---|---|
| L-0 | 봉인판 sha, 파라미터 값 | 메인 세션 | 원판 봉인, 전환 후 감사(전환이 있으면) |
| L-1 | 하네스 커밋·출력 sha, 상수 파일 sha | python-expert 실행 → 메인 세션 | 경로 2 sha 고정 |
| L-2 | G-S 건조 실행 기록 | cad-expert·python-expert 실행 → 메인 세션 | L-1 |
| L-3 | 실행 전 감사 원문 경로·sha, 차단 수 0 | verif-protocol-auditor → 메인 세션 | L-2 |
| L-4 | checkout·env·배치표·argv 전개·시작 시각 | 메인 세션(래퍼) | L-3 차단 0 |
| L-5 | 끝난 직후 HEAD·status, rc, 러너 로그 `errors` | 메인 세션(래퍼) | Chrono 6행 끝 |

- 각 단계 시각은 `+09:00` ISO 8601로 적는다. T(시간 순서) 감사는 L-0 < L-1 < L-2 < L-3 < L-4 < 첫 행 시작을 본다.

## 2. JSON 틀

```json
{
  "schema": "b1-creep-prelaunch/1",
  "batch_name": "V5-B1-CREEP",
  "batch_dir": "{BATCH_DIR}",
  "rules": {
    "sealed_file": "06_analysis/02_control/b1/{RULES_FILE}",
    "sealed_sha256": "{RULES_SHA256}",
    "sha256_file": "06_analysis/02_control/b1/{RULES_SHA_FILE}",
    "sealed_at": "{RULES_SEALED_AT}",
    "gridconv_plan_sha256": "0e909bf1186a4cc90e40353d25244ee4a76a04cdabe48235e7051f9a111e9b24",
    "gridconv_plan_rev1_sha256": "3f354eb7c122584c7e65e66bb2eeaf33e27cfa9b445521a9802bdf8962d1da9e",
    "gridconv_judgement_sha256": "a483ac48582c3171654d3e9e6f213bb11c3436b64d3396bea75da50e8a89e56b",
    "gridconv_verdict": "PASS"
  },
  "parameters": {
    "P5R4_OUTCOME": "{P5R4_OUTCOME}",
    "CTRL_TAG_VB": "{CTRL_TAG_VB}",
    "CTRL_TAG_V0": "{CTRL_TAG_V0}",
    "CTRL_PRESET_NOTE": "{CTRL_PRESET_NOTE}",
    "HEAD_M": "{HEAD_M_FULL}",
    "P7_REF": "{P7_REF}",
    "HULL_DLL_SHA": "{HULL_DLL_SHA}",
    "START_LIMIT": "{START_LIMIT}",
    "POOL_ROWS": {"C1": "{POOL_C1}", "C2": "{POOL_C2}", "C3": "{POOL_C3}",
                  "C4": "{POOL_C4}", "C5": "{POOL_C5}", "C6": "{POOL_C6}"}
  },
  "checkout": {
    "path": "{CHECKOUT_PATH}",
    "kind": "{CHECKOUT_KIND}",
    "head_before": "{HEAD_BEFORE}",
    "status_tracked_before": "{STATUS_BEFORE}",
    "head_after": "{HEAD_AFTER}",
    "status_tracked_after": "{STATUS_AFTER}",
    "dll_src_sha256": "{DLL_SRC_SHA}",
    "dll_copy_sha256": "{DLL_COPY_SHA}",
    "params_yaml_sha256": "{YAML_SHA}",
    "c2_py_sha256": "{C2_SHA}",
    "run_S9_py_sha256": "{RUN_S9_SHA}",
    "s9_batch_py_sha256": "{S9_BATCH_SHA}"
  },
  "environment": {
    "interpreter": "C:\\ProgramData\\miniforge3\\envs\\Chrono-dev\\python.exe",
    "interp_flags": "{INTERP_FLAGS}",
    "env_removed": ["OUTRIGGER_HULL_HOOK", "OUTRIGGER_HULL_HOOK_ALLOW_UNVALIDATED",
                    "OUTRIGGER_HULL_HOOK_DLL", "OUTRIGGER_LOC_SHADOW"],
    "env_set": {"OMP_WAIT_POLICY": "PASSIVE"},
    "env_extra": "{ENV_EXTRA}",
    "threads_chrono": 4
  },
  "placement": {
    "table_path": "{PLACEMENT_TABLE}",
    "table_sha256": "{PLACEMENT_SHA}",
    "reservation_id": "{RESERVATION_ID}",
    "masks": {"C1": "{MASK_C1}", "C2": "{MASK_C2}", "C3": "{MASK_C3}",
              "C4": "{MASK_C4}", "C5": "{MASK_C5}", "C6": "{MASK_C6}"},
    "waves": "{WAVES}"
  },
  "rows": [
    {"id": "C1", "case": "B1_J2_B_bottom_Fs4_VB_fdown", "argv": "{ARGV_C1}", "argv_sha256": "{ARGV_SHA_C1}", "budget_leg": "FL", "duration_s": 160},
    {"id": "C2", "case": "B1_J2_B_middle_Fs4_VB_fdown", "argv": "{ARGV_C2}", "argv_sha256": "{ARGV_SHA_C2}", "budget_leg": "FL", "duration_s": 160},
    {"id": "C3", "case": "B1_J2_B_top_Fs4_VB_fdown", "argv": "{ARGV_C3}", "argv_sha256": "{ARGV_SHA_C3}", "budget_leg": "FL", "duration_s": 160},
    {"id": "C4", "case": "B1_J2_B_bottom_Fs4_VB_diag", "argv": "{ARGV_C4}", "argv_sha256": "{ARGV_SHA_C4}", "budget_leg": "FR", "duration_s": 160},
    {"id": "C5", "case": "B1_J2_B_top_Fs4_VB_fup", "argv": "{ARGV_C5}", "argv_sha256": "{ARGV_SHA_C5}", "budget_leg": "RL", "duration_s": 160},
    {"id": "C6", "case": "B1_J2_B_bottom_Fs4_m1p1_VB_fdown", "argv": "{ARGV_C6}", "argv_sha256": "{ARGV_SHA_C6}", "budget_leg": "FL", "duration_s": 180}
  ],
  "argv_checks": {
    "built_with": "v5_vb_argv() + explicit --expect-controller (not v5_vb_rows)",
    "expect_controller_value_equals_CTRL_TAG_VB": "{ARGV_EXPECT_OK}",
    "grid_args": "--grid 0.01 --crawler-grid 0.04",
    "start_limit_arg": "{ARGV_START_LIMIT}"
  },
  "overlap_table": {
    "rules_section": "seal candidate 2.4",
    "checked_by": "{OVERLAP_CHECKED_BY}",
    "checked_at": "{OVERLAP_CHECKED_AT}",
    "h_m0_margin_form": "enable kept, margin_m = 0",
    "c6_controller_mass_nominal": "{C6_CTRL_MASS_NOMINAL}",
    "preset_dump_diff_vs_e67dae8": "{PRESET_DUMP_DIFF}",
    "preset_dump_tool_sha256": "{PRESET_DUMP_TOOL_SHA}"
  },
  "grid_record": {
    "fields_file": "{GRID_RECORD_FILE}",
    "interval": "{GRID_RECORD_INTERVAL}",
    "cost_ratio_on_off": "{GRID_RECORD_COST}",
    "bit_identity_on_off_step_series": "{GRID_RECORD_BIT_SAME}",
    "pad_xy_yaw_field": "{M4H_FIELD}"
  },
  "loc_anchor_record": {
    "chrono_imu_raw_tilt_field": "{M12_CHRONO_FIELD}",
    "harness_shadow": "{HARNESS_SHADOW_ON}",
    "harness_shadow_hash_pairs": "{SHADOW_HASH_PAIRS}"
  },
  "harness": {
    "commit": "{HARNESS_COMMIT}",
    "output_jsonl": "06_analysis/03_hydraulic/coupled/v5/b1/b1_H.jsonl",
    "output_sha256": "{HARNESS_OUT_SHA}",
    "runs": 32,
    "tags_seen": "{HARNESS_TAGS}",
    "errors_total": "{HARNESS_ERRORS}",
    "errors_left": "{HARNESS_ERRORS_LEFT}"
  },
  "constants": {
    "file": "06_analysis/02_control/b1/b1_harness_constants.json",
    "sha256": "{CONST_SHA}",
    "tool_sha256": "{CONST_TOOL_SHA}"
  },
  "path_tools": {
    "path1_tool": "{PATH1_TOOL}",
    "path1_sha256": "{PATH1_SHA}",
    "path2_script": "{PATH2_SCRIPT}",
    "path2_sha256": "{PATH2_SHA}",
    "path2_fixed_at": "{PATH2_FIXED_AT}"
  },
  "dry_run": {
    "dir": "{DRY_DIR}",
    "started": "{DRY_START}",
    "rows": "{DRY_ROWS}",
    "outputs_shown": "rc, expect_controller.ok, tag string, hull_hook, num_threads_chrono, field key names, runner errors only",
    "result": "{DRY_RESULT}"
  },
  "audit": {
    "prerun_audit_path": "{AUDIT_PATH}",
    "prerun_audit_sha256": "{AUDIT_SHA}",
    "blocking": "{AUDIT_BLOCKING}"
  },
  "launched": "{LAUNCHED_AT}",
  "ended": "{ENDED_AT}",
  "batch_json_cases_argv_rc": "{BATCH_JSON_OK}",
  "runner_log_errors": "{RUNNER_ERRORS}",
  "runner_log_errors_left": "{RUNNER_ERRORS_LEFT}"
}
```

## 3. 항목별 출처와 확인 (규칙 대응)

| 키 | 규칙 | 확인 방법 |
|---|---|---|
| `rules.*` | 원판 후보 10.1 S, 1.1 | `seal_check.py`, `.sha256` 내용 = 파일 sha |
| `parameters.*` | 원판 후보 1.1 | 봉인판 1.1 값과 문자열 완전 일치. `CTRL_TAG_*`는 `controller_meta`·하네스 meta와 완전 일치(1.4) |
| `checkout.*` | I-1, I-8, I-10 | 시작 직전·끝난 직후 `git rev-parse HEAD`, `git status --porcelain --untracked-files=no` |
| `environment.*` | I-4, I-5, I-7, I-14 | 실행 셸에서 `env_removed`를 지운 뒤 띄움, `-I` 포함 |
| `placement.*` | I-6 | compute-scheduler-expert 배치표 경로·sha, `reserve.py` id |
| `rows[].argv` | I-2, I-15 | 래퍼가 실제 argv 목록을 잡아 `batch.json cases[].argv`와 같은지 비교 |
| `argv_checks.*` | I-3, 2.2 | `--expect-controller` 값 = `CTRL_TAG_VB`, `v5_vb_rows` 미사용 |
| `overlap_table.*` | 원판 후보 2.4, I-17 | 겹침 표 칸마다 코드 줄로 확인한 사람·시각 |
| `grid_record.*` | 원판 후보 6, T-10 | 기록 켬/끔 짧은 짝 `step_series.npz` 비트 동일, 비용 비 ≤ 1.05 |
| `loc_anchor_record.*` | 원판 후보 7.5 | Chrono 필드 키 이름, 하네스 그림자 끔 짝 4개 명령 해시 같음 |
| `harness.*`, `constants.*` | 원판 후보 7.3, I-9, E-1 | 하네스 32줄 태그·errors, 상수 파일 sha가 prelaunch보다 먼저 |
| `path_tools.*` | 원판 후보 9절, T 순서 | 경로 2 sha 고정 시각 < 첫 Chrono 행 시작 |
| `dry_run.*` | 원판 후보 2.3, I-16 | 판정 값 출력 없음, 시각 < `launched` |
| `audit.*` | 원판 후보 10.1 | 차단 0 |
| `runner_log_errors*` | I-12 | `log_errors.py <러너 로그 폴더>` 종료 0 |

## 4. 남은 것

- 배치 폴더 안에서 채운 prelaunch의 sha를 판정서 첫머리에 적는다.
- 실행 중 이 checkout에 병합·checkout을 하지 않는다(전용 worktree면 그 worktree 기준).
- 행 하나가 V-1 실패로 `--resume`되면 `rerun_of`와 옮긴 `attempt1/` 경로를 postrun에 적는다(원판 후보 4.3).
