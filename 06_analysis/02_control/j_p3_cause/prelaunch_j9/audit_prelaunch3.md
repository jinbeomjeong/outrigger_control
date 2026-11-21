# 436.9 J-P3 실행 전 N 항목 재감사(verif-protocol-auditor 리포트 원문, 2026-11-21)

메인 세션이 hand-back 원문 전체를 그대로 저장했다.

---

## 감사 요약
- 판정: **차단 0 / 실행 전 수정 0 / 기록 7.** 단계 (1)~(3)은 지금 실행 가능하다. (4)~(7)도 명령 파일의 단계 의존(.done)대로 이어서 실행할 수 있다. 각 단계 시작과 다시 돌리기에는 사용자 승인이 있어야 한다(README 18행).
- 대상: 좁은 재감사, 시점은 실행 전. 지난 감사 `prelaunch_j9/audit_prelaunch2.md`의 N-1~N-6, R-b, R-e를 다시 봤다.
- 실행 커밋: worktree `z4369-jp3`의 `b51ed6e1090cb0a54f2c24799f372fb02c50653c`(부모 d84ba7bd, locked, `git status --porcelain` 빈 출력).
- master 커밋: `b7531f96`(2026-11-21 13:39).
- 기준 문서(sha 앞 8자리): 판 4a `8be9de22`, 4a-1~4a-4와 정오(지난번과 같음), 4a-5 `562c4e9f`, 4a-5 정오 1 `a7a0c973`. 이번에는 모두 추적된다.
- 고정 목록: `FIXED_INPUTS_b51ed6e1.SHA256SUMS` `ccebf70d`.
- 본 결과: 판정 대상 결과는 없다(`j9_runs` 없음). 저장 결과 파일은 이번에 열지 않았다.

### 지난 항목 해소 표

| 항목 | 상태 | 근거 |
|---|---|---|
| N-1 T-JR-14 (가)에 닿을 수 없음 | **해소** | `r79_sensor_screen.py:946-949`, `v5_record_or_mismatch` `:1091-1107`. `LockWindowMismatchError`만 오류 줄로 남기고, 다른 예외는 다시 raise한다. 예외가 없으면 출력은 전과 같다(`out.update(_v5_record(...))`와 같은 경로). t12 `_dg3_lines(mismatch_fails=True)`는 new 쪽 mismatch 줄을 `failures`로 넣고 짝 비교 없이 반환한다(`jp3_tjr_judge.py:490-499`, `:572-590`). 그래서 step6가 종료 1로 멈추고, step7은 `dg3.done`이 없어 자동으로 거부된다(`step7_records.ps1:9`, `common.ps1:221`) |
| N-2 결과를 본 단계의 재실행 장치, `max` 합침, 앞 시도 기록 | **해소** | `Read-PreviousStops`(`common.ps1:189-205`): 앞 `.stop*`의 `tool:*` 코드에 1이 있으면 거부한다. `base_judge_compare` 1은 제외한다. `previous_attempts`는 step_record·.stop·.done에 남는다. `Get-StepCode`(`:207-211`)는 step4a `:31`, step6 `:51`에서 쓴다 |
| N-3 예외가 종료 1로 나옴 | **해소** | `TOOL_ERRORS = (Exception,)`(`jp3_baseline_compare.py:105`). 네 도구 모두 `NotJudgeable`·`Stop`을 먼저 잡고 그 밖은 종료 3으로 낸다 |
| N-4 4a-5 2절 VB 행 | **해소** | `_vb_rerun_record` `evidence_problems`, `_t_jr_10_preconditions`(`jp3_tjr_judge.py:308-316`, `:387-401`) |
| N-5 L1·판정 파일 sha를 고정 목록으로 확인 | **해소** | step1이 `prelaunch_j9/P1_OUTPUTS_b51ed6e1.SHA256SUMS`를 쓴다(`common.ps1:329-346`, 덮어쓰기 거부, LF). step6 `Assert-P1Outputs`(`:348-373`)가 git 추적, HEAD와 같음, 목록 = bj.json = 실제 파일을 확인하고 어기면 종료 2를 낸다 |
| N-6 미커밋 | **해소** | `seal_check --sums --rev HEAD --check-tracked`: 8판 raw 일치, error 0, `cited_untracked` 0. 4a-5·정오·run_steps는 `b7531f96`에서 처음 추가됐다. 코드 b51ed6e1(13:34)이 문서 커밋(13:39)보다 앞서고, 결과는 아직 없다 |
| R-b 건식에서 키가 있는지 기록 | 해소(기록) | `jp3_dryrun_evidence.py:326-338`, `:358`. 판정 조건이 아니다 |
| R-e 변수 지우기 | 해소 | `common.ps1:64-70`, `:161-168`. 목록에 든 변수와 `^(R79_|R72_|R67_|LAS_T3_)` 접두 변수를 모두 지운다 |

## 발견 사항

차단 0, 실행 전 수정 0.

### [기록]
- R-1 [E] **메인 운영 규칙(README 19~20행)에 대한 답: 충분하다. 다만 한 줄을 자동화하기를 권한다.**
  - "단계 6 T-JR-14 실패면 단계 7 안 함"은 명령 파일이 이미 강제한다. step7은 `dg3.done`을 요구하고, step6가 종료 1이면 .done이 생기지 않는다.
  - "failures가 있으면 종료 2여도 재시도 안 함"은 4a-5 5.4보다 엄격하다. 5.4는 종료 2를 "결과를 본 것"으로 치지 않는다. 그런데 `Problems.status()`가 판정 불가를 실패보다 앞에 두므로, 실패와 판정 불가가 섞이면 종료 2가 된다. 그래서 이 규칙이 필요하다.
  - 지금은 "메인이 보고를 확인해 막는다"로 되어 있다. 보고 파일의 `failures`를 여는 것은 5.4의 "판정 값을 연 때"에 가깝다. 대신 도구 표준 출력 마지막 줄(로그 `logs/<label>.log`)의 `failures_count`를 쓰면 5.4에서 결과를 본 것으로 치지 않는다. `Read-PreviousStops`가 이 값까지 보게 하면 자동으로 막을 수 있다(메인 세션 명령 파일, 선택).
  - 이 엄격한 규칙은 결과 전에 정한 운영 규칙이므로, 판정서에도 적기를 권한다.
- R-2 [E] r79 mismatch 줄에는 `v5_setting`·`hydraulics_record`가 없다(`_v5_record`가 raise해서 기록되지 않음). 그래서 step7의 T-JR-14·T-JR-15에서는 설정별로 묶는 단계에서 빠진다. 그 결과 실패가 아니라 판정 불가로 나오고, `judge_t_jr_15`의 새 mismatch 실패 분기는 Dg-3 줄에서 실행되지 않는다. 다만 mismatch는 step6에서 종료 1로 잡히고 step7은 돌지 않으므로 판정에는 영향이 없다. VBJ0(기준 쪽) mismatch는 판정 불가(2)다. 4a-5의 T-JR-14 대상이 VBH·VBJ뿐이므로 정의와 맞는다.
- R-3 [S] `FIXED_INPUTS_b51ed6e1` 57/57이 일치한다(중복 0, CRLF 0). master HEAD에 없는 16줄은 `v5/main.jsonl`과 resume_k1 저장 파일·identity sidecar다(4a-3 5.4가 허용하는 git 밖 고정).
- R-4 [S] 4a-1에는 아직 `.sha256`이 없다(`seal_missing` warning 1). 해시는 고정 목록으로 고정돼 있다.
- R-5 [R] `ref_check --rev HEAD`(4a-5·정오)는 missing 9다. 코드 파일 4개(`jp3_tjr_judge.py` 등)는 master에 병합되지 않은 worktree 브랜치에만 있다. 지난번 `--rev d84ba7bd`에서는 찾아졌다. 나머지 5건은 지난번과 같다(P-1 출력 전, 필드 이름, 저장소 밖 도구, git 밖 H-6).
- R-6 [E] junit(b51ed6e1):
  - full: 7,788건 중 7,654 통과, 2 실패, 132 skip, xfail·xpass 0.
  - main2: 667 통과, 9 skip.
  - gap: 57 통과, 1 실패.
  - 실패 3건은 지난번과 같은 예외다(`test_d8x_diag`, `test_hydraulics_flow_limit_run`(worktree 데이터), `test_rev7_regression_on_the_stage3_records`). critical_skipped 0.
  - 판정서에 "전부 통과"라고 쓰지 않는다.
- R-7 [I] 다이제스트는 모니터 `552c768a…`, 플랜트 `7404b793…`로 전과 같다. 그 밖에 확인한 것:
  - `git diff --stat d84ba7bd b51ed6e1`로 보면 `03_src`, `harness_hydraulics.py`, `run_v5.py`, `verdict_runs.py`는 바뀌지 않았다. 실행 코드 중 바뀐 것은 `r79_sensor_screen.py`의 예외 감싸기뿐이다.
  - `ClearedVariables`에는 접두 패턴으로 지운 변수만 남는다. 목록에 있던 이름은 기록되지 않는다(사소함).

## 확인 필요
없음.

## 위임 필요
없음. 선택: R-1의 `failures_count` 자동 거부(메인 세션 명령 파일).

## 메인 세션 권고
- 사용자 승인 뒤 step1 → step2 → step3 순서로 실행한다.
- step1이 끝나면 `P1_OUTPUTS_b51ed6e1.SHA256SUMS`를 커밋한다. step6가 이를 요구한다.
- 각 단계가 끝난 뒤 판정 후 감사에서 확인할 것:
  - 보고의 `inputs` sha와 고정 목록·T4h SUMS 대조
  - 정체성 확인 보고(`_identity_checks/`)

## 검사하지 못한 것
- `t4h_replay`가 H-6 T4h를 받는지, r79 VBJ 줄에 relock·seed 키가 있는지: 실행이 금지돼 확인하지 못했다(지난번과 같다). 단계 (2)의 R-b 기록과 단계 (7)에서 드러난다.
- 명령 파일 동작은 정적으로만 읽었다.

## 실행한 검증
- python-dev(`-I -B`, TBB):
  - `seal_check --repo … "jp3_remedy_spec*.md" --sums baseline SUMS --rev HEAD --check-tracked --code <worktree coupled>`: error 0, warning 1, info 18.
  - `placeholder_scan run_steps\*.ps1`: `<…>` 패턴 0, 기본 패턴 0.
  - `ps1_lint` 9개: 0.
  - `junit_skips` 3개(R-6).
  - `ref_check --rev HEAD`(R-5).
  - 즉석 스크립트 `fixed_check.py`(57줄, HEAD 추적 여부).
- git 조회: `log`, `status --porcelain`, `worktree list --porcelain`, `diff --stat`/`diff d84ba7bd b51ed6e1`(코드 4개).
- 최종 판정 직전에 worktree HEAD `b51ed6e1`이 깨끗한지 다시 확인했다.
- 만든 뒤 지운 파일: scratchpad `verif-jp3-prelaunch3\`(guard.json, fixed_check.py, seal.md). 폴더째 지웠고 Test-Path는 False다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_addendum_4a1.md 4b122dd0…, jp3_remedy_spec_addendum_4a2.md 2f3e36bd…, jp3_remedy_spec_addendum_4a2.md.sha256 19063b36…, jp3_remedy_spec_addendum_4a3.md f001383a…, jp3_remedy_spec_addendum_4a3.md.sha256 3045bb46…, jp3_remedy_spec_addendum_4a4_erratum1.md 1ccbe526…, jp3_remedy_spec_addendum_4a4_erratum1.md.sha256 27255e69…, jp3_remedy_spec_addendum_4a4.md 67380b10…, jp3_remedy_spec_addendum_4a4.md.sha256 c50c5aac…, jp3_remedy_spec_addendum_4a5_erratum1.md a7a0c973…, jp3_remedy_spec_addendum_4a5_erratum1.md.sha256 5c0be4d7…, jp3_remedy_spec_addendum_4a5.md 562c4e9f…, jp3_remedy_spec_addendum_4a5.md.sha256 b45e407c…, jp3_remedy_spec.md 8be9de22…, jp3_remedy_spec.md.sha256 174e6fb7…, audit_prelaunch.md e62bc724…, audit_prelaunch2.md 2da391b8…, FIXED_INPUTS_325b77a8.SHA256SUMS 5aeb5f96…, FIXED_INPUTS_b51ed6e1.SHA256SUMS ccebf70d…, FIXED_INPUTS_d84ba7bd.SHA256SUMS 00736c77…, FIXED_INPUTS.SHA256SUMS f35fa862…, h10_reuse_rerun_t4h.SHA256SUMS 3d0ed49a…, h6_dg3_v4on_t4h.SHA256SUMS c426f518…, README.md 75f40ece…, common.ps1 fd0dc74d…, step1_p1.ps1 e9ca543e…, step2_dry.ps1 5c4c1cd6…, step3_fpath.ps1 89ccf465…, step4a_cases.ps1 2027657b…, step4b_casef.ps1 8ed958d4…, step5_t8.ps1 21c75381…, step6_dg3.ps1 70b4bf4f…, step7_records.ps1 0a6a9141…, SHA256SUMS 51a3d9cc…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
