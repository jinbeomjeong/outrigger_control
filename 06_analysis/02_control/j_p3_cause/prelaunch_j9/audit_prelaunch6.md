# 실행 전 좁은 재감사 6 (verif-protocol-auditor, 2026-11-21) — 원문 그대로

## 감사 요약
- 판정: **B(차단) 0 / M(중간) 0 / N(참고) 8.** 4a-8 6.2절 VBJ 재판정(`step6v_vbj_rejudge.ps1`)은 사용자 결정대로 **지금 실행할 수 있다.**
- 대상: 좁은 재감사 6, 시점 실행 전. 고친 커밋은 worktree `z4369-jp3` `d3c6c57e27f5b5448ecc33708b955773705ab22e`(locked, `git status --porcelain` 빈 출력, 부모 78fd5d2d). master는 `7c79edcb`.
- 기준 문서(sha 앞 8자리):
  - 4a-8 `fde367f0`, 4a-8 정오 1 `c2d158ab`, 4a-7 정오 3 `50982e30`. 앞 판은 지난 감사와 같다.
  - 고정 목록 `FIXED_INPUTS_d3c6c57e.SHA256SUMS`, L1 키 `l1_keys_d3c6c57e.json` `eea8ed0d`, 명령 `step6v_vbj_rejudge.ps1` `b6bd616b`, 근거 `j4a_remedy_d3c6c57e/SHA256SUMS` `5f70ca03`.
- 본 결과(값 비출력):
  - `j9_runs/78fd5d2d/dg3_a1/dg3_VBJ.json`·`dg3_VBJ0.json`: sha, 줄 수, `level`·key 셋째 토큰(계열)·`v5_setting`의 건수, 오류 줄 수, meta `keys_file.n_keys`, 판정 키 18개의 존재 여부(key_presence).
  - 저장 H-6: (harness, inner, case_index) 키 문자열.
  - path1 L1 추출본: key 문자열.
  - 근거 폴더의 junit과 폐포 보고(상태·건수).
  - 판정 값·등급·READY·J-P3 값과 `dg3_a1/judge/` 파일은 열지 않았다.

## 볼 것별 결과

| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| (1) | 6.1 폐포 ∩ diff = 0 | **적합(독립 확인)** | `git diff --name-only 78fd5d2d d3c6c57e`는 13파일이다. 코드는 6개(`jp3_baseline_compare`·`jp3_case_judge`·`jp3_dryrun_evidence`·`jp3_import_closure`·`jp3_rejudge_inputs`·`jp3_tjr_judge`), 나머지는 시험 7개다. 독립 확인 1: worktree `04_scripts` 전체에서 이 6개 이름을 `import`·`from`·문자열 리터럴로 Grep하면, 판정·대조 도구끼리만 나온다(`jp3_case_judge`·`jp3_dryrun_evidence`·`jp3_rerun_match`·`jp3_tjr_judge`). 독립 확인 2: 동적 로드(`import_module`·`spec_from_file_location`·`runpy`)가 있는 실행 경로 파일 가운데, `las_t3_dg3.py`는 `pre_las_preset_runner.py`를 LAS=off일 때만 부르고(이번 실행은 on), `d8x_record.py`의 `import_module` 목록에는 jp3 이름이 0개다. 도구 보고 `import_closure_78fd5d2d_d3c6c57e.json`: `disjoint`, 폐포 223, 바뀐 파일 13, `meeting` 0. 폐포에는 `j_p3_inputs`·`jp3_fixed_inputs`·`two_pressure.py`·`r79_sensor_judge.py`가 들어 있고 모두 바뀌지 않았다. 새 고정값을 폐포 밖 `jp3_rejudge_inputs.py`에 둔 것은 정오 1 2절과 맞는다 |
| (2) | H8-1 k 규칙 | **적합, 이번 입력 영향 0** | `jp3_baseline_compare.py:315-332` `evidence_multiplier`: `cand=` 접두를 뗀 뒤 `^L\d+\|s\d+\|`이고 셋째 토큰이 `g8`이면 k = 2, 그 밖은 1이다. `rod_evidence_problems`(`:335-360`)와 `judged_line_evidence_problems`(`:285-312`)가 k를 받고, 키가 없으면 결함이다. 입력 검증: VBJ·VBJ0 각 135줄, level은 L2 1 / L3 134, 계열은 g6 80 / g8 40 / ref 15, 정규식에 안 맞는 key 0, 오류 줄 0. L1 키 102개는 모두 `L1\|s0\|…`다. 그래서 L2nocal·L2imuideal 판별 차이(정오 1 5·6절)가 이번 입력 270줄과 L1 204줄에 닿지 않는다 |
| (3) | H8-4 dg3-judge | **적합** | `dg3_input_problems`(`jp3_tjr_judge.py:972-999`): VBH는 L1 sha = P-1a 고정 `a591c3a8`이어야 한다. VBJ·VBJ0는 `l1_run_problems`(`:1013-1050`)로 102줄, 오류 0, level L1, `rod_model` plant_truth, `v5_setting` = 설정, candidate current, (harness, inner) 집합 = 키 파일, meta `keys_file` sha·`n_keys`를 본다. `--dg3-sha256`으로 입력 sha를, `keys_file_problems`로 H-6·135를, 다른 설정 줄 없음을 본다. 판정 파일은 `judge_rows_problems`(`jp3_baseline_compare.py:369-401`)로 runs 수와 키 집합이 입력과 같은지, unmatched 0, errors 0을 본다. `LockWindowMismatchError` 줄은 기대 행과 errors에서 빠지고(정오 1 1절), t12 `_dg3_lines(mismatch_fails=True)`에서 실패(종료 1)로 남는다. 그래서 N-1 실패 경로가 유지된다. L1 실행 검사에는 mismatch 예외가 없다(정오 1 1절 끝과 같다). 이번 두 입력에는 오류 줄이 0이라 예외 경로는 쓰이지 않는다 |
| (4) | H8-5 t12 판정 파일 검사 | **적합** | `t12_judge_row_problems`(`:819-830`): base·new 판정 파일 둘 다에 L1을 뺀 줄로 같은 검사를 하고, mismatch 키는 제외한다. 결과는 `_run`에서 판정 불가로 들어간다. 짝 135·L2 1·키 집합 검사는 그대로다 |
| (5) | step6v | **적합** | 순서: `Initialize-Step`(HEAD = d3c6c57e, 트리 깨끗, 고정 입력 12개, 재시도 거부 가드) → `Assert-RejudgeInputs`(dg3_VBJ0 `c1201b2d`·dg3_VBJ `603e4b81`을 직접 쟀고 일치, `jp3_rejudge_inputs` 상수 대조, 고정 키 파일 sha) → 0. 폐포 확인(`Invoke-Judge`, `meets` 1이면 멈춤) → 1. 키 파일 재생성 sha = 고정값이 아니면 2 → L1 실행 두 개(고정 키 파일, plant_truth, 정체성 래퍼) → `Invoke-IdentityCheck`(d3c6c57e) → 4.5 기록 → dg3-judge VBJ0·VBJ(입력 sha·L1 sha 넘김) → t12 VBJ(두 판정 sha 넘김; ≠ 0이면 `Stop-Step`, 1은 재시도 거부). 출력은 `j9_runs/d3c6c57e/dg3_vbj_a1/`이다. 78fd5d2d `dg3_a1`은 읽기만 하고 `judge/`는 읽지 않는다. 키 파일을 독립으로 다시 만들었다: 102키(g6 63, g8 29, ref 10), 고정 파일과 목록·순서 같음, 102/102가 L1 추출본에 있음, CRLF 0 |
| (6) | 실행 전 도구 | 아래 | |

- `seal_check --sums --rev 7c79edcb --check-tracked`: 15판 raw 일치, error 0, warning 1(`seal_missing` 4a-1).
- `baseline_check sums FIXED_INPUTS_d3c6c57e --base repo-root --rev 7c79edcb`: 90줄, mismatch 0, missing 0, CRLF 0.
  - `cited_untracked` 15는 resume_k1 저장 파일·identity다.
  - `cited_ignored` 2는 `v5/main.jsonl`과 `dg3_VBJ.json`이다. 뒤의 것은 4a-8 7절의 로컬 전용 고정이다.
  - `sums_unlisted` 8은 N-6(지난 감사와 같은 거짓 양성)이다.
- `placeholder_scan run_steps --pattern-set both`: 0. `ps1_lint` 10개: 0.
- `gate_scan`(코드 6개): warning 9.
  - `missing_key_default_pass` 2건은 `dg3_input_problems:995-997`과 `l1_run_problems:1025-1038`이다. 뒤의 것은 `results`가 없으면 줄 수 ≠ 102로 판정 불가라 거짓 양성이다. 앞의 것은 N-3.
  - `tag_single_compare` 7건은 고정 설정 이름 비교다.
- `key_presence`(판정 키 18개, 값 비출력):
  - dg3_VBJ 135/135 모두 있음.
  - dg3_VBJ0은 `extend_bound_check`가 null(③ 꺼짐)이라 J-P3 키 5개가 없다. VBJ0은 기준 쪽이라 J-P3를 판정하지 않고, 4a-7 정오 3("VBJ0 이벤트 줄은 record가 없는 것이 정상")과 맞는다.
- `junit_skips`(d3c6c57e):
  - full: 7,935건 중 7,801 통과, 2 실패(`test_d8x_diag`, `test_hydraulics_flow_limit_run`; 기존 예외), 132 skip.
  - gap: 57 통과, 1 실패(`test_rev7_regression_on_the_stage3_records`, 기존 예외).
  - main2: 667 통과, 9 skip. xfail·xpass 0, critical_skipped 0.
  - 지난 M-2(근거 폴더 없음)는 해소됐다.
- `log_errors`: 새 실행 로그가 없어 생략했다.

## 발견 사항

B 0, M 0.

### [N]
- N-1 [I][추정] 배치 `-Workers 12 -VbjMask 0xFFFF -Vbj0Mask 0x0FFF0000`(L1)은 78fd5d2d Dg-3 배치(VBJ `0xFF00` P, VBJ0 `0x0FFF0000` E)와 worker·mask가 다르다. 설정마다 코어 종류(VBJ = P, VBJ0 = E)는 Dg-3와 L1에서 같고, 스레드 5변수는 `Set-RunEnvironment`로 1·TBB 고정이다. 단일 스레드 실행이고 P/E 코어는 ISA가 같다. 그래서 결과 비트에 영향이 없다고 본다. worker 수는 작업 분배만 바꾼다. 4.5 기록(VBJ L1 대 VBJ0 L1 해시)은 코어 종류가 섞인 비교지만 판정이 아니다. 판정서 기록 줄에 배치를 적는다.
- N-2 [I] 재판정은 실행 커밋이 섞인다. Dg-3 입력은 78fd5d2d이고, L1·판정은 d3c6c57e다. 4a-8 6.2·6.3절이 정한 예외이고, 6.1 폐포 조건으로 시뮬레이션 코드 동일이 확인됐다. 판정서 공개 문구(6.4)에 두 커밋을 함께 적는다.
- N-3 [E] `judge_rows_problems`는 입력 줄 0·판정 행 0이면 통과다. `dg3_input_problems`도 `results`가 없는 파일을 통과시킨다. t12의 135짝 검사가 판정 불가로 잡고, 이번 입력은 sha 고정 135줄이라 결론에는 영향이 없다. "판정 행 0 = 판정 불가"를 함수 안에도 두는 것이 정리 후보다(python-expert, 선택).
- N-4 [R] 폐포 진입점은 `las_t3_dg3.py`뿐이다. L1 실행의 부모 프로세스인 정체성 래퍼 `jp3_run_identity.py`와, 등급 판정에 쓰는 `r79_sensor_judge.py`(폐포에 포함됨)는 진입점에 없다. 래퍼는 이번 diff에 없어 영향이 없다. 다음 예외 판단 때는 래퍼도 진입점에 더하기를 권한다.
- N-5 [R] 폐포 도구는 정적 분석이다. 계산된 문자열로 하는 `import_module`은 따라가지 못한다. 실행 경로의 유일한 사례(`d8x_record`)에 jp3 이름이 없음을 Grep으로 확인했다. 이번에는 놓친 것이 없다.
- N-6 [S] `baseline_check sums --base repo-root`의 `sums_unlisted` 8(SUMS 폴더의 다른 파일)은 지난 감사의 N-6과 같다(도구 후보).
- N-7 [R] 정오 1 5·6절의 판별 차이(`L2nocal` 등을 r79 줄로 보지 않음, k = 1)는 다음 전체 실행 전 과제로 남아 있다. 이번 입력에는 영향이 없다(볼 것 (2)).
- N-8 [R] 경로 2 미정 1건(J-P3 입력의 `stretch_mismatch` 오류 줄 처리)은 요청대로 판정 단계 과제로 기록만 한다. 경로 1은 t12에서 실패(종료 1)로 처리하고, T-JR-15 판정 집합에서는 그 줄이 `v5_setting` 없이 남아 판정 불가가 된다(지난 감사 R-2와 같음).

## 확인 필요
없음.

## 위임 필요
선택 사항: python-expert에 N-3 정리와 N-4 폐포 진입점 추가.

## 메인 세션 권고
- step6v를 실행한다(사용자 결정, 차단 0).
- 끝나면 판정 후 감사를 받는다. 볼 것: `dg3_vbj_a1/judge/` 보고의 inputs sha와 고정 목록 대조, 정체성 확인 보고, 판정서 공개 문구(6.4, N-1·N-2).

## 검사하지 못한 것
- 시험 코드 내용(H8-1~H8-5 단위 시험)은 junit 결과로만 확인했다.
- 명령 파일 실행 동작은 정적으로만 읽었다.
- 폐포 도구 자체 실행은 하지 않았다. 도구 보고를 읽고, 위 Grep 두 가지로 독립 확인했다.

## 실행한 검증
- python-dev(`-I -B`, TBB):
  - `seal_check`, `baseline_check sums --base repo-root`
  - `placeholder_scan --pattern-set both`, `ps1_lint`, `gate_scan`(6개)
  - `key_presence`(dg3_VBJ·VBJ0 키 18개, VBJ0 결측 5키 확인)
  - `junit_skips`(근거 3개)
  - 즉석 스크립트 `l1_keys_check.py`(키 재구성·추출본 포함 여부·입력 토큰 건수)
  - `Get-FileHash`(Dg-3 입력 2개)
- git 조회: `log`, `status --porcelain`, `worktree list`, `diff --stat`/`--name-only`/`diff 78fd5d2d d3c6c57e`(판정 도구·rejudge 상수)
- Grep: 바뀐 모듈 이름의 import·문자열, 동적 로드 사용처, `d8x_record`의 jp3 이름
- 최종 판정 직전에 worktree HEAD `d3c6c57e`가 깨끗한지 다시 확인했다.
- 만든 뒤 지운 파일: scratchpad `verif-prelaunch6\`(guard.json, l1_keys_check.py, seal.md). 폴더째 지웠고 Test-Path는 False다.
- 원본 불변: 확인 — `source_guard verify --strict-additions` 결과 pass True, folder_status unchanged, 입력 65개(명세·덧붙임·정오·`.sha256`, prelaunch_j9 전체, 멈춤 보고, 근거 SUMS, dg3_VBJ0.json). `report_line` 원문은 출력에서 필드만 골라 읽어 남기지 못했다. 원문이 필요하면 다음 감사에서 다시 낸다.
- 사용한 스킬: 없음

---

## 메인 결정(2026-11-21)

- 차단 0·중간 0 → 사용자 사전 승인대로 step6v를 20:23:45에 시작(`-Attempt 1 -Workers 12 -VbjMask 0xFFFF -Vbj0Mask 0x0FFF0000`, 예약 `r-20261121202345-a62ad6`). N-3·N-4는 선택 정리 후보, N-1·N-2는 판정서 공개 문구에 넣는다.
