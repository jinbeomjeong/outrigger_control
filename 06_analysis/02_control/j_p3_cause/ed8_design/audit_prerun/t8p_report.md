# 436.9 판 8 T8′ 구현 보고 (실행 전 감사 반영)

## 요약
- **T8′는 `2bf16b31e771d3ef3b427a360fb3312a747af21c`입니다.** 새 브랜치 `ed8-judge2`, 새 worktree `C:\workspace\outrigger_control\.claude\worktrees\ed8-judge2`에 있고 T8 `ecf6c142`의 자식입니다.
  - C8 `56849248`, ed8-impl, ed8-judge(잠금)는 손대지 않았습니다.
  - C8 대비 diff는 `04_scripts`(판정 도구)와 `05_tests`뿐입니다. 03_src와 06_analysis 변경은 0이고, P8-11 시험도 통과했습니다.
- 반영 범위: 감사 B-1·B-2·B-3·M-1·M-2·M-4, R-2·A-4, control-expert 결정문의 A-1·A-3·A-5, F-1.
- 선택 사용 키 파일: `ed8_design\keys_selection_ed8\selection_keys_ed8.json`
  - sha256 `3f3753d92fa150ef83a8af38c7d490d2ba705efc08c513976b63b9b31af19e4a`, 같은 폴더에 SHA256SUMS를 두었습니다.
  - job 23, 단위 18(C-J 11, C-S 1, C-D 0, C-G 6), 단위 아닌 census 줄 1, census 밖 4, r79 건너뜀(P8-14) 13.
  - `PINNED_SHA256["selection_keys"]`에 고정했습니다.
- **전체 단위 시험(T8′):** 2 실패, 8863 통과, 134 건너뜀.
  - 두 실패는 기존 실패입니다(`test_hydraulics_flow_limit_run`, `test_d8x_diag`).
  - T8·C8 junit과 비교하면 상태가 바뀐 시험 0, 새 건너뜀 0입니다. ed8 시험 파일의 skip도 0이고, 선택 키 재생성 시험은 통과했습니다.
- 판정 도구는 실제 판 8 결과에 돌리지 않았습니다(아직 없음). rev26 폴더는 건드리지 않았습니다.

## 1. 반영 내용

| 항목 | 반영 |
|---|---|
| **B-1** (사용자 결정 (가)) | 아래 참조 |
| **B-2** | `heldout_judgement`가 2차 별칭과 셈 전에 `selection["first_aliases"]` 슬롯을 먼저 빼고 `first_aliases_left_out`에 기록합니다. 목록이 없으면 입력 오류(setting_defect)입니다 |
| **B-3** (결정 1.3·1.4) | 아래 참조 |
| **A-5** | 줄 하나의 정체성 함수가 예외(판 7 SettingDefect·NotJudgeable, KeyError·TypeError·ValueError)를 내면 그 줄의 정체성 문제 `identity not computable`로 기록합니다. 도구 오류(종료 3)로 끝나지 않습니다 |
| **A-1** | 아래 참조 |
| **A-3** | census는 결과 줄에만 정체성을 봅니다. 저장 V0와 격자에는 적용하지 않습니다(구조상 그렇게 되어 있고, 따로 시험하지는 않았습니다) |
| **M-2** | `main`이 `jp3_ed7_judge.SettingDefect` → setting_defect, `jp3_ed7_judge.NotJudgeable` → not_judgeable로 바꿉니다 |
| **R-2** (결정 4.2) | run_v5 판 8 줄은 최상위 `ed8_settings`를 `ED8_SETTINGS_EXPECTED`와 비교합니다. 실수는 상대차 1e-12까지 허용하고 bool·int는 타입까지 같아야 합니다. 없거나 다르면 setting_defect입니다 |
| **A-4** | r79 줄은 `hydraulic_options.ed8_settings` 스위치를 줄 또는 T4h meta에서 읽어 설정 값과 비교합니다. `ed8_identity()` 안에서 판 7 `ed7_identity_problems`·`r79_identity_view`를 감싸므로 12a·12b·l1ref에도 적용되고, 끝나면 원래 함수로 돌려놓습니다 |
| **M-1** (결정 3.3) | 아래 참조 |
| **M-4·F-1** (결정 2.3~2.5) | 아래 참조 |
| **M-3** | C8 run steps(`full_suite_ed8.ps1`)는 C8 파일이라 T8′에서 고칠 수 없습니다. "메인 세션 권고" 참조 |

### B-1 (사용자 결정 (가))
- P8-15에서 켬 팔 줄의 `ed8_record`(또는 waiver 수)를 읽지 못한 쌍은 판정 쌍에서 뺍니다.
- 빠진 쌍은 `record_failures: ["(1) 3.8 record key missing: N pairs left out …"]`으로 공개하고, 남은 쌍이 20 이상이어야 합니다.
- 해당 상수는 `UNREAD_PAIRS_LEFT_OUT = {"p815"}`입니다. P8-5·P8-8은 지금처럼 판정 불가로 둡니다.

### B-3 (결정 1.3·1.4)
- 상수는 `V0_CONTROLLER_TAG = "final_C4G2_LAS_K1"`, `V0_ABSENT_KEYS`(9개)입니다.
- `v0_identity_problems`가 확인하는 것: `job.setting`, 태그, `hydraulic_options`·`hydraulics_record` null, `head_only_declared`, 9개 키 없음.
- `identity_defects`는 V0 줄을 이 함수로, 그 밖의 줄은 판 7 정체성으로 봅니다.

### A-1 (5단계 입력 완결성)
- `stage5`는 정확히 세 파일(`ed8_heldout_v0` 678, `aa2` 339, `aa3` 339)을 받습니다. 파일마다 `run_v5.heldout_v0_jobs`와 1:1로 대조합니다.
- 파일 수가 다르거나 빠짐·중복·여분이 있으면 not_judgeable입니다.
- 순서
  1. 정체성 문제가 있으면 setting_defect, 완결성 문제가 있으면 not_judgeable로 두고 바로 반환합니다(정체성이 앞섭니다). 이때는 선택을 계산하지 않고 k도 동결하지 않습니다.
  2. 둘 다 없을 때만 `stage5_selection`을 계산합니다.
- 키 파일 거부(SystemExit)는 setting_defect로 처리합니다.

### M-1 (결정 3.3)
- 생성기 `04_scripts/04_hydraulic/coupled/ed8_selection_keys.py`
  - 입력: 세 raw의 sha와 census 키 sha를 고정합니다. raw에서는 job 키만 읽습니다.
  - 플랜트 대응(VBM→VBN, VBMslow→VBNslow, LSM4→LSN4) 밖이면 거부합니다. r79 줄은 건너뛰고 수를 셉니다.
  - census와는 설정과 plain job으로 대조합니다.
  - 기대 수 `EXPECTED`와 다르면 쓰지 않습니다(종료 2). 출력이나 SUMS가 이미 있으면 거부합니다.
- census 판정 쪽
  - `--selection-keys`는 sha를 고정합니다(없으면 not_judgeable, sha가 다르면 setting_defect).
  - `selection_unit_ids`는 설정까지 맞춰 대조합니다.
  - `selection_units_checked`: 일치 0건이거나 파일 `expected`와 다르면 setting_defect입니다.
  - 보고에 `selection_units`·`selection_non_units`를 넣습니다.

### M-4·F-1 (결정 2.3~2.5)
- `four-case` 키 해석은 `jp3_12b_judge.case_of`로 통일했습니다(접두와 seed를 뗌). 줄은 `load_lines`·`block_keys`로 읽습니다.
- 새 입력 `--selection`, `--selection-sha256`, `--decision`과 그 대조
  - decision `status` = decided.
  - selection과 블록 sha가 decision `ed7_record.inputs_sha256`과 같아야 합니다.
  - `blocks_used` 블록이 모두 주어져야 합니다.
  - 파일은 단계 폴더 안에 있어야 합니다.
- 4사례 조건: 정확히 4개, 틀은 167, 4사례가 모두 틀 안에 있어야 합니다.
- 기록 내용
  - P-pred 입력(`input_statistics`, b4면 `b4_input`)을 all·without_four·four로 나눠 기록합니다.
  - all이 decision `p_pred` 입력과 다르면 setting_defect, `InputStop`도 setting_defect입니다.
  - `k_allow`는 다시 계산하지 않습니다(출력 키 없음).
  - 교착 서명이 None이면 `record_failures` (3)에 넣습니다.

## 2. 시험 (합성 입력. 생산자 꼴 반영)
| 시험 파일 | 내용 |
|---|---|
| 새 `test_ed8_t8p.py` | 아래 목록 |
| `test_ed8_gate_judge.py` | B-1 r79 생산자 꼴 줄 4쌍(job = `r79_key`·`setting`, `ed8_record` 없음, T4h는 `r79_<setting>` 하위 폴더): 23쌍 통과 + 기록 실패, 19쌍 판정 불가 |
| `test_ed8_judge.py` | 아래 목록 |

- `test_ed8_t8p.py`가 덮는 것
  - B-2: 합침·비합침 두 경우.
  - B-3: 생산자 꼴 V0 줄, 어긋남마다 문제가 나는지, 생산자 상수 3개(`controller_tag(None, C2Config().with_10hz_d1())`, `options_of("V0")`, `plant_options_record`).
  - A-5, R-2(`ed8_settings_meta`가 VBN config에서 기대값과 같음, 어긋남 5종, 허용 오차·타입), A-4, 원래 함수 복원.
  - M-2, M-1(재생성 바이트 = 고정 sha [핵심 시험, 통과], 고정 sha = 생성 파일, 모르는 플랜트·r79 건너뜀, 덮어쓰기 거부, 설정 대조·기대 수 불일치·0건).
- `test_ed8_judge.py`가 덮는 것
  - `stage5` main을 정체성 스텁 없이 끝까지 실행: 세 출력, CWD를 다른 폴더에 둠.
  - 정체성 결함 → setting_defect이며 A/A 판정을 하지 않음.
  - 빠짐·중복·여분, 두 파일, 정체성과 완결성 동시 결함.
  - 선택 키 설정 대조(VBNfast 제외, VBNslow 포함).
  - `four-case`: 접두 있는 키, 손계산 값, all ≠ decision, 틀 밖, 4사례 아님, b4 있음·없음, 입력 거부.
- **없앤 T8 시험 5개**(동작이 바뀌어 대체됨)
  - `test_arm_pairs_without_the_record_are_not_judgeable_never_zero[p815]`
  - `test_12b_case_of_key_drops_only_the_seed`
  - `test_12b_four_case_record`
  - `test_selection_unit_ids_ignore_the_setting`
  - `test_stage5_main_end_to_end_with_stubbed_readings`
- **생산자 꼴 미시험(남음):** 436.8 `metric_of`와 A/A 항목 판정은 아직 스텁입니다. 결정 1.5가 말한 "T4h 없는 V0 줄이 `metric_of`를 통과하는지"는 확인하지 못했습니다. `t4h_folders_of`는 실제 함수로 통과했습니다. census·heldout·cases 읽기 경로도 같은 상태입니다(감사 M-5).

## 3. 검증
| 검증 | 결과 |
|---|---|
| 집중 시험(ed8·ed7 판정, run_path) | 256 통과 |
| 전체 시험 T8′ | 2 실패(기존), 8863 통과, 134 건너뜀, 1511 s, 끝 시점 HEAD T8′·clean |
| ruff·codespell(바꾼 파일) | 0 |

- 전체 시험 조건: ed8-judge2에서 Chrono-dev `-n 12 --dist loadfile`, `OUTRIGGER_RECORDS_ROOT=main`, `NUMBA_CACHE_DIR`은 scratchpad였습니다. 시작 전 `reserve.py list`로 확인한 유효 예약은 0이었습니다.
- 증거: 새 폴더 `ed8_design\t8p_evidence\`(SUMS `912eb29c…`)
  - `junit_T8p_2bf16b31.xml`, `suite_T8p_2bf16b31.log`, `junit_diff_T8_vs_T8p.txt`, `junit_diff_C8_vs_T8p.txt`(상태 변화 0)
  - 러너가 처음에 `audit_prerun\t8p_tests\`에 junit을 썼습니다. sha로 인용되는 감사 폴더를 피하려고 `t8p_evidence`로 옮겼고, 남은 빈 폴더는 지웠습니다.
- 정리: ed8-judge2의 `__pycache__` 13개와 `.hypothesis`를 지웠습니다(status --ignored 비어 있음). scratchpad `python-ed8-t8p`도 지웠습니다.

## 감사 M-5 키 존재 점검 목록 (추가 안)
`key_presence.py`로 값 출력 없이 존재만 봅니다.

| 대상 | 키 |
|---|---|
| run_v5 판 8 줄(`impl_t8`·`impl_cases`, census·G′ VBN) | 감사 원안의 키 + **`ed8_settings`, `ed8_settings.probe_k1_scale_settings.scale_mid_min_piston_travel_m`, `ed8_settings.r8.stiffness_warning_range`, `ed8_settings.r8.lifted_reapproach.short_run_s`, `ed8_settings.r8.lifted_reapproach.short_run_exit_samples`, `ed8_settings.twist_completion_relax.locked_drift_waiver`·`waiver_max_rise_N`·`waiver_margin_N`** |
| 5단계 V0 줄(`ho_v0`·`ho_aa2`·`ho_aa3`) | 있어야 함: **`controller_tag`**, `commands_sha256`, `event_output.reapproach_starts`(사건 줄) |
| 5단계 V0 줄 | 없어야 함(**`V0_ABSENT_KEYS`**): `lsb_components`, `lsb_settings`, `lsb_record`, `probe_d6_settings`, `probe_d6_record`, `probe_stiffness_record`, `ib_block_record`, `ed8_settings`, `ed8_record` |
| 5단계 V0 줄 | null이어야 함: `hydraulic_options`, `hydraulics_record` |
| r79 줄(12a·12b·l1ref) | T4h meta의 `hydraulic_options.ed8_settings` |

## 확인 필요
1. **P8-15 "읽지 못한 쌍"의 범위.** `ed8_record`가 없는 쌍(r79 4키)만이 아니라 waiver 수가 정수가 아닌 쌍도 같은 규칙(빼고 기록 실패 (1))으로 처리했습니다. 둘 다 0으로 읽지 않는다는 원칙은 같습니다.
2. **5단계 오류 줄의 처리.** 오류 줄은 정체성을 적용하지 않고, 그 슬롯을 지금처럼 not_judgeable로 둡니다(`slot_inputs`, 결정 1.3과 같음).

## 메인 세션 권고
- **M-3 기준선(P8-4).** C8 run steps는 바꿀 수 없으므로 아래처럼 돌려 주십시오.
  1. 41e107e9 detached checkout을 만듭니다. 예: `git -C C:\workspace\outrigger_control worktree add --detach .claude\worktrees\ed8-base41 41e107e9`
  2. 띄우는 PowerShell에서 먼저 `$env:NUMBA_CACHE_DIR='C:\Users\jinbeom\.claude\runners\outrigger-ed8\numba_cache\suite_base'`를 설정하고 `full_suite_ed8.ps1 -Side base -Worktree <ed8-base41> -ExpectCommit 41e107e98a5b0e45c3197dbfee46e8dd033eba35 -OutDir <runner 폴더>`를 돌립니다. 하위 프로세스가 환경 변수를 물려받는지는 확인하지 않았으니, 끝난 뒤 worktree에 `.nbi`·`.nbc`가 없는지 봐 주십시오.
  3. `-Side run`도 run worktree가 아닌 C8 별도 checkout에서 같은 방법으로 돌립니다. 각 약 25~30분 걸립니다.
- 선택 키 폴더 `keys_selection_ed8\`와 `t8p_evidence\`를 6단계 census 전에 커밋해 주십시오.
- T8′ 재감사(verif-protocol-auditor) 뒤 `ed8-judge2`를 잠가 주십시오.

## 공개 (실제 행위)
- 블라인드 경로는 열지 않았습니다.
- Grep·Read는 모두 하위 경로나 단일 파일로 지정했습니다. 대상: `ed8-judge2\04_scripts\04_hydraulic\coupled`, `05_tests\unit`, `03_src\outrigger_sim\control\c2.py`, 감사·결정문 두 파일, 명세 머리말 30~41행, `impl_report_ed8\stats_t8_check.md`.
- P8 raw는 생성기가 job 키만 읽었고, 판정 값은 출력하지 않았습니다.
- **Bash 파이프 1회:** worktree 생성 명령 끝에 `| tail -n 1`을 붙였습니다(규칙 위반, 출력 한 줄만 봄). 그 밖의 Bash는 쓰지 않았습니다.
- 프로세스는 종료하지 않았습니다.

사용한 스킬: 없음
