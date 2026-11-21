# 436.9 J-P3 실행 전 변경분 재감사(verif-protocol-auditor 리포트 원문, 2026-11-21)

메인 세션이 hand-back 원문 전체를 그대로 저장했다.

---

## 감사 요약
- 판정: **차단 0 / 실행 전 수정 0 / 기록 6.** 단계 (1)~(7)은 명령 파일의 단계 의존대로 실행할 수 있다. 각 시작과 재시도는 사용자 승인 뒤에 한다(README 운영 규칙).
- 대상: 변경분 좁은 재감사, 시점 실행 전. 실행 커밋은 worktree `z4369-jp3`의 `fa997f4cb2dba9820118c6d38e469ebb137110e2`(locked, `git status --porcelain` 빈 출력, b51ed6e1 → f83a51e3 → fa997f4c). master는 `23143fb8`.
- 기준 문서(sha 앞 8자리): 지난번 목록에 4a-6 `ae49bf4e`가 더해졌다(추적됨, 첫 커밋 `23143fb8` 16:19). 고정 목록은 `FIXED_INPUTS_fa997f4c.SHA256SUMS` `792f6bbe`.
- 본 결과: 판정 대상 결과를 열지 않았다. `j9_runs/b51ed6e1`·`fa997f4c` 폴더의 파일은 하나도 열지 않았다.

### 볼 것별 결과

| 항목 | 결과 | 근거 |
|---|---|---|
| compare 수정: 짝 만들기와 기준선 규약의 대칭 | **적합** | `jp3_baseline_compare.py` `t4h_path_of`는 `<--new 파일 폴더>/<줄기>_t4h/<t4h_file 이름>`이다. `Baseline.t4h`(`<줄기>_t4h/<이름>`, 기준선 폴더 기준)와 같은 규칙이다. `main`은 `read_new_rows`를 쓰고, `_compare_pair`는 `_new_t4h_path`를 쓴다. 출력 쪽도 맞는다: run_v5는 `<out 줄기>_t4h`(`run_v5.py:716-723`), `jp3_case_replay`는 `<out 줄기>_t4h`(`:60`)에 쓴다. 따라서 step4a의 `j9_cases.jsonl`은 `j9_cases_t4h/`, `cd.jsonl`은 `cd_t4h/`가 된다. 짝 키(`_job_key`)와 4a-1·4a-2의 판정 정의는 바뀌지 않았다 |
| 스캔 제외(4a-6 1·2절) | **적합** | `SCAN_EXCLUDED_FOLDER = "02_control/j_p3_cause/j9_runs/"`이고, 상대 경로(`as_posix`)가 대소문자 그대로 이 접두로 시작하는지 본다. 제외 파일의 키는 키 집합과 seed 최댓값에 들어가지 않는다. 출력에는 `excluded_folder`, `files_excluded`, 파일별 `path`·`sha256`·`r79_keys`·`has_generated_key`가 남고, 제외 밖 스캔 증거도 그대로 남는다. 생성 seed ≠ 25이면 `Stop`(판정 불가)이다. 기본 키 규칙은 바뀌지 않았다 |
| rerun_match(4a-6 4절) | **적합** | `jp3_rerun_match.py`가 읽는 것은 다음뿐이다. p1: 파일 sha 2개와 코드 2개. dry: 다섯 실행의 증거 2키와 `summarize` 코드. fpath: `harness_commands_sha256`(offset별)과 코드. x11: `commands_sha256`, FL 49.0 s 읽기, 코드. 보고에는 항목 이름(`compared`·`differing`)과 상태만 남고 값은 없다. 종료 코드는 0 같음, 1 다름, 2 입력 없음, 3 오류다. 옛 폴더는 `.done`이나 최신 `.stop*`의 `folder` 이름으로 찾아 읽기만 한다 |
| 명령 파일: 대조 위치·종료 처리·b51ed6e1은 읽기만 | **적합** | `Invoke-RerunMatch`(`common.ps1:379-388`)는 step1 `:37`(Write-P1Outputs 뒤), step2 `:39`, step3 `:18`, step4a `:33`(두 판정 뒤)에 있다. `Invoke-Judge` 기본값은 0만 계속이므로 1·2·3이면 멈춘다. `tool:rerun_match_*` = 1이면 `Read-PreviousStops`가 재시도를 거부한다(4a-6 7절). `$PreviousRunsRoot`는 `--old` 인자로만 쓰인다. 출력·코드 파일은 새 시도 폴더에만 쓴다 |
| 블라인드(b51ed6e1에서 결과를 보지 않은 4a A~E·F, 5~7) | **적합** | worktree `04_scripts` 전체와 run_steps에서 `b51ed6e1|j9_runs`를 Grep했다. 나온 것은 rerun_match(4 항목), select 제외 상수, 문서 문자열뿐이다. x11 항목은 `cases_a1`에서 `lsj4_x11.jsonl`과 그 T4h의 49.0 s 한 읽기만 읽는다. `j9_cases.jsonl`과 `cd.jsonl`은 열지 않는다. step4b~7은 b51ed6e1을 참조하지 않는다. 예외 하나는 기록 R-2에 적었다 |
| seal_check `--sums --rev HEAD --check-tracked` | error 0 | 9판 raw 일치. `cited_untracked` 0. warning 2: `seal_missing`(4a-1)과 `seal_name_mismatch`(R-1) |
| FIXED_INPUTS_fa997f4c | **63/63** | 중복 0, CRLF 0. HEAD에 없는 16줄은 resume_k1과 `v5/main.jsonl`(4a-3 5.4)뿐이다. `j9_runs` 줄은 0 |
| placeholder_scan(`<…>`·기본)·ps1_lint | 0 / 0 / 0 | run_steps 9개 |
| junit_skips(fa997f4c) | 지난번과 같은 예외 | full: 7,815건 중 7,681 통과, 2 실패(`test_d8x_diag`, `test_hydraulics_flow_limit_run`), 132 skip. gap: 57 통과, 1 실패(`test_rev7_regression_on_the_stage3_records`). main2: 667 통과, 9 skip. xfail·xpass 0, critical_skipped 0 |
| 다이제스트 | 같음 | 모니터 `552c768a…`, 플랜트 `7404b793…`. `git diff --stat b51ed6e1 fa997f4c`에서 실행 코드는 바뀌지 않았다. 바뀐 것은 compare, dryrun select, rerun_match(새 파일), 시험 4개다 |

## 발견 사항

차단 0, 실행 전 수정 0.

### [기록]
- R-1 [S] `jp3_remedy_spec_addendum_4a6.md.sha256`은 저장소 루트 기준 경로(`*06_analysis/02_control/j_p3_cause/…`)를 쓴다. 다른 `.sha256`은 파일 이름만 쓴다(`seal_name_mismatch`). 해시는 같다. 그 폴더에서 `sha256sum -c`를 돌리면 실패하므로, 다음 정리 때 이름 형식을 맞추기를 권한다.
- R-2 [I] 블라인드 경계: step2 `select`는 4a-6 2절대로 제외 폴더(`j9_runs/` 전체, b51ed6e1 `cases_a1`의 A~E 출력 포함)의 json·jsonl 바이트를 읽는다. 거기서 sha256, r79 키 문자열 수, 생성 키 포함 여부만 선정 출력에 남긴다. 판정 값은 꺼내지 않는다. 규칙이 요구한 동작이므로 판정서의 블라인드 문구에 "키 문자열·sha만 읽음"이라고 적는다.
- R-3 [R] step1~3과 4a(x11)에서 판정 도구가 0이 아닌 코드로 끝나면, 대조 전에 멈춘다. 이때 b51ed6e1의 코드(0)와도 다르므로, 4a-6 4절의 "다름" 공개(두 시도 값)도 함께 해야 한다. 결과(멈춤, 재시도 거부)는 4a-6 7절의 "불일치 = 실패"와 같다. 판정서 공개 문구에 두 사유를 함께 적는다.
- R-4 [R] x11 대조는 4a-6 4절 표에 없는 "FL 49.0 s 읽기의 class"도 비교한다. 같은 읽기의 값이고 b51ed6e1에서 이미 본 단계라 블라인드 문제는 없다. 표보다 한 항목 엄격하다.
- R-5 [C][추정] p1 대조는 판정 파일 sha가 같기를 요구한다. `r79_sensor_judge.py judge` 출력(`:817-819`)에는 경로·시각이 없고 L1 추출본도 결정적이다. 그래서 거짓 불일치는 없을 것이다. 다른 항목(증거 정수, 해시)도 결정적이다.
- R-6 [S] 4a-1 `.sha256`은 여전히 없다(고정 목록으로 고정). `ref_check`는 이번에 다시 돌리지 않았다. 4a-6이 새로 가리키는 경로는 `j9_runs/` 폴더와 바뀐 도구 3개이고, 모두 확인했다.

## 확인 필요
없음.

## 위임 필요
없음(R-1은 선택 정리).

## 메인 세션 권고
- 사용자 승인 뒤 step1부터 실행한다. step1이 끝나면 `P1_OUTPUTS_fa997f4c.SHA256SUMS`를 커밋하고 step6 전에 둔다.
- 판정서에는 4a-6 3절 (가)·(나)를 넣는다. (가)의 `f83a51e3`은 7절에 따라 `fa997f4c`로 읽는다. 함께 넣을 것: rerun_match 결과(항목별 같음/다름), R-2·R-3 공개.

## 검사하지 못한 것
- 명령 파일 실행 동작과 rerun_match의 실제 대조: 실행 금지라 정적으로만 확인했다.
- 단위 시험의 내용은 junit 결과로만 확인했다(시험 코드는 읽지 않음).

## 실행한 검증
- python-dev(`-I -B`, TBB):
  - `seal_check`(위와 같음)
  - `placeholder_scan` 2회, `ps1_lint`
  - `junit_skips` 3개
  - 즉석 `fixed_check.py`(63줄, HEAD 추적 여부)
- git 조회: `log`, `status --porcelain`, `worktree list --porcelain`, `diff --stat`/`diff b51ed6e1 fa997f4c`(compare·dryrun)
- 읽은 코드: `jp3_rerun_match.py` 전체, `r79_sensor_judge.py` 출력부, `jp3_case_replay.py` T4h 경로, run_steps `common.ps1:370-402`·step1·step4a
- 최종 판정 직전에 worktree HEAD `fa997f4c`가 깨끗한지 다시 확인했다.
- 만든 뒤 지운 파일: scratchpad `verif-jp3-prelaunch4\`(guard.json, fixed_check.py, seal.md). 폴더째 지웠고 Test-Path는 False다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_addendum_4a1.md 4b122dd0…, jp3_remedy_spec_addendum_4a2.md 2f3e36bd…, jp3_remedy_spec_addendum_4a2.md.sha256 19063b36…, jp3_remedy_spec_addendum_4a3.md f001383a…, jp3_remedy_spec_addendum_4a3.md.sha256 3045bb46…, jp3_remedy_spec_addendum_4a4_erratum1.md 1ccbe526…, jp3_remedy_spec_addendum_4a4_erratum1.md.sha256 27255e69…, jp3_remedy_spec_addendum_4a4.md 67380b10…, jp3_remedy_spec_addendum_4a4.md.sha256 c50c5aac…, jp3_remedy_spec_addendum_4a5_erratum1.md a7a0c973…, jp3_remedy_spec_addendum_4a5_erratum1.md.sha256 5c0be4d7…, jp3_remedy_spec_addendum_4a5.md 562c4e9f…, jp3_remedy_spec_addendum_4a5.md.sha256 b45e407c…, jp3_remedy_spec_addendum_4a6.md ae49bf4e…, jp3_remedy_spec_addendum_4a6.md.sha256 9ca492db…, jp3_remedy_spec.md 8be9de22…, jp3_remedy_spec.md.sha256 174e6fb7…, audit_prelaunch.md e62bc724…, audit_prelaunch2.md 2da391b8…, audit_prelaunch3.md bbe7cf5b…, FIXED_INPUTS_325b77a8.SHA256SUMS 5aeb5f96…, FIXED_INPUTS_b51ed6e1.SHA256SUMS ccebf70d…, FIXED_INPUTS_d84ba7bd.SHA256SUMS 00736c77…, FIXED_INPUTS_fa997f4c.SHA256SUMS 792f6bbe…, FIXED_INPUTS.SHA256SUMS f35fa862…, h10_reuse_rerun_t4h.SHA256SUMS 3d0ed49a…, h6_dg3_v4on_t4h.SHA256SUMS c426f518…, P1_OUTPUTS_b51ed6e1.SHA256SUMS 9f2db2e9…, README.md 612e3587…, common.ps1 79bddea2…, step1_p1.ps1 0dc2394e…, step2_dry.ps1 695aeebe…, step3_fpath.ps1 9c470b89…, step4a_cases.ps1 a6317c9e…, step4b_casef.ps1 8ed958d4…, step5_t8.ps1 21c75381…, step6_dg3.ps1 70b4bf4f…, step7_records.ps1 0a6a9141…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
