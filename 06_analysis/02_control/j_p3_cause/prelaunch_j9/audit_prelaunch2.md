# 436.9 J-P3 실행 전 좁은 재감사(verif-protocol-auditor 리포트 원문, 2026-11-21)

메인 세션이 hand-back 원문 전체를 그대로 저장했다. 결정은 맨 끝 절에 덧붙인다.

---

## 감사 요약
- 본 결과: 판정 대상 결과(j9_runs)는 아직 없어서 열지 않았다. 저장 자료는 다음만 봤다.
  - 저장 H-6 `h6_dg3_v4on.json`: `lock_window_alignment`·`n_late_fallback`·`reason`, relock·seed 키가 있는지와 그 개수만 셌다. 값은 보지 않았다.
  - 근거 폴더: `j4a_remedy_325b77a8/e6_identity`의 identity, d84ba7bd의 junit·요약·commit_message, 다이제스트 파일.
- 대상: 좁은 재감사, 시점은 실행 전이다.
  - 지난 감사(`prelaunch_j9/audit_prelaunch.md`)의 B-1·M-1~M-8·R 항목이 해소됐는지 본다.
  - 덧붙임 4a-5와 그 정오 1을 도구와 대조한다.
  - 명령 파일 `prelaunch_j9/run_steps/`(9개)를 본다.
  - 실행 커밋은 worktree `z4369-jp3`의 `d84ba7bdaf00b160396e66d2b5023edc74a8d4f1`이다(locked, `git status --porcelain` 빈 출력).
- 기준 문서(sha 앞 8자):
  - 판 4a `8be9de22`, 4a-1 `4b122dd0`, 4a-2 `2f3e36bd`, 4a-3 `f001383a`, 4a-4 `67380b10`, 4a-4 정오 1 `1ccbe526`
  - **4a-5 `562c4e9f`, 4a-5 정오 1 `a7a0c973`(둘 다 미커밋)**
  - 고정 목록 `FIXED_INPUTS_d84ba7bd.SHA256SUMS` `00736c77`
- 판정: **차단 0 / 실행 전 수정 6 / 기록 13**
  - 지난 차단 B-1은 해소됐다.
  - 4a-5와 명령 파일을 커밋하면(N-6) 실행할 수 있다. N-1~N-5는 그 전에 고치기를 권한다. 고치지 않고 돌리면, 실패가 생겼을 때 그것이 판정 불가나 도구 오류로 표시되어 다시 돌리는 경로로 빠질 수 있다.
  - N-1·N-3·N-4는 코드를 고쳐야 한다. 결정 2에 따라 고치면 새 실행 커밋이 된다. N-2·N-5는 명령 파일만 고치면 되지만, 그 파일들이 고정 목록에 있으므로 목록도 다시 만들어야 한다.

### 단계별 결과

| 단계 | 결과 | 남은 항목 |
|---|---|---|
| (1) P-1 | 통과(B-1 해소) | 공통: N-2, N-3, N-6 |
| (2) 건식 5실행 | 통과(조건부) | N-6. 기록 R-b(r79 VBJ 줄의 relock·seed 키를 미리 확인하라는 권고) |
| (3) F-A 경로 | 통과(조건부) | N-6 |
| (4) 사례 재생·X11·F | 경고 | N-2(step4a가 두 판정 코드를 `max`로 합침), N-3 |
| (5) j9_t8 → T-JR-10/11 | 경고 | N-4(4a-5 2절 VB 행이 구현되지 않음) |
| (6) T-JR-12 | 경고 | N-1, N-2(`max` 합침), N-5 |
| (7) records(T-JR-13~15) | 경고 | N-1(T-JR-14 (가) 판정에 닿을 수 없음) |

### 지난 항목 해소 표

| 지난 항목 | 상태 | 근거 |
|---|---|---|
| B-1 self-check 설정 결함 | **해소** | `jp3_tjr_judge.py:469-482`(`check_settings=False`), `:510-524`(증거 검사는 `JP3_LINE_SETTINGS` 줄만). `test_jp3_prelaunch_audit.py:65-73`이 실제 H-6과 저장 경로 1 판정 파일로 `expectation_misses == []`와 pass를 assert한다. `test_jp3_addendum_4a3.py:257-260`은 `setting_defects == []`를 assert한다 |
| M-1 정체성 | 해소 | `jp3_run_identity.py`(wrap, 다른 head 거부 `:77-86`, 빈 head 거부 `:80-81`). 명령 파일은 래퍼와 `--out`을 쓰고 판정 전에 `baseline_check identity --mtime`를 돌린다(`common.ps1:271-283`). 도구로 확인: 위조한 빈 head는 `baseline_head_invalid`(종료 1), 실제 기록은 종료 0, sidecar가 0개인 폴더는 종료 2 |
| M-2 명령·환경 | 해소 | `run_steps` 9개. `placeholder_scan --pattern "<[A-Za-z_][^>]*>"` 0, 기본 패턴 0, `ps1_lint` 0. 스레드 5변수(`common.ps1:44-50`), 절대경로 출력 `j9_runs/d84ba7bd/<단계>_a<N>/`(`.gitattributes:154` `-text` 적용) |
| M-3 t12 설정 대조 | 해소 | `:527-542`, `t12_file_defects` `:712-716`, `_run` `:1324` |
| M-4 t8 정체성·B2·64자 | 해소 | `:264-283`, `:342-346`, `:362-368`. 다만 4a-5 2절 VB 행은 빠짐(N-4) |
| M-5 키가 없으면 0 | 해소 | `extend_start_bound.py:1872-1886`, `has_rev5_judged_keys`, `jp3_baseline_compare.py` `retract_tracker_problems`. baseline 쪽 상태 이름은 `not_judgeable`이고, 문구에 `judged_key_missing`을 적는다(종료 2는 같다) |
| M-6 records | 해소 | 빈 입력은 판정 불가(`:968-971`). T-JR-13은 426·135, revision 5, `judged: False` 거부, 오류 행 = 실패. T-JR-14와 T-JR-15는 판정 집합을 고정했다(정오 1, `:1075-1182`). 단 N-1 |
| M-7 실패 처리표 | 해소(문서) | 4a-5 5절. 명령 파일은 새 시도 폴더를 쓰고 덮어쓰기를 거부한다. 단 N-2 |
| M-8 새 쪽 판정 파일 | 해소 | `dg3-judge`(`:810-852`), `--new-judge-sha256` 필수, VBJ도 `--base-judge-sha256` 필수(`:691-709`), keys_file = H-6·135(`:545-552`), step6가 `--keys-file $H6`를 씀. 단 N-5 |
| R-6·R-7·R-8 | 해소 | 고정 목록에 identity sidecar 7개, `reference_extract`가 덮어쓰기를 거부(`h8_noise_judge_4368.py:444-463`), `STORED_H6_JUDGE_SHA256` 대조(`:886-887`) |
| R-3 T4h 경로 기준 | 해소 | `prelaunch_j9/README.md:8-9` |

## 발견 사항 (심각도순)

### [실행 전 수정][R·E] N-1: T-JR-14 (가) "LockWindowMismatchError 줄 = 실패"는 r79 경로에서 닿을 수 없다
- 근거:
  - `lock_window_alignment.py:170-172`가 `LockWindowMismatchError`를 raise한다. 이 함수는 `verdict_runs.lock_window_record`(`:291-300`)를 거쳐 `r79_sensor_screen._v5_record`(`:1108-1109`)에서 불린다. 그런데 `_v5_record`는 `:946`에서 불리고, 이는 실행 try 블록(`:924-935`) **밖**이다. `r79_L3L4_final.run_one`(`:128-151`)에도 잡는 곳이 없다. 그래서 오류 줄이 생기지 않고 pool이 예외로 끝난다. las_t3_dg3는 0이 아닌 코드로 끝나고, step6 `Wait-Runs`가 `Stop-Step 3`을 낸다(`common.ps1:229-238`).
  - 오류 줄이 생기더라도, step6의 t12가 오류 줄을 판정 불가로 처리한다(`jp3_tjr_judge.py:555-565`, 키 집합 불일치 `:483-486`). 그래서 step6가 종료 2로 멈춘다. step7은 `dg3.done`을 요구하므로 돌지 않는다(`step7_records.ps1:9`).
  - 4a-5 1절은 이 경우를 **실패(종료 1)**로 정한다. `jp3_tjr_judge.py:1109-1112`의 실패 분기는 실제로 쓰이지 않는 코드다.
- 실패 시나리오: 실제 대체 다리 로그 불일치가 종료 3(도구 오류)이나 종료 2로 나타난다. 4a-5 5.1·5.3에 따르면 이것은 "고쳐서 다시"의 경로이고, 5.4가 금지하는 "실패를 다시 돌려 바꾸기"가 공개 없이 일어날 수 있다. 저장 H-6 135줄에서는 `n_late_fallback`이 모두 정수였고 `reason`은 0이었다(같은 경로, 키 개수 확인). 그래서 발생 가능성은 낮다고 [추정]한다.
- 권장 조치:
  - python-expert: r79 경로에서 `LockWindowMismatchError`를 잡아 그 줄을 오류 줄(`error: "LockWindowMismatchError: …"`)로 남긴다. step6·t12는 그 줄이 있으면 T-JR-14 실패(종료 1)로 보고하거나 step7로 넘긴다.
  - 또는 control-expert: 덧붙임으로 "Dg-3 실행이 이 예외로 끝나면 T-JR-14 실패"를 정하고, 명령 파일이 그 오류를 step6에서 실패로 표시하게 한다.
  - 어느 쪽인지는 "확인 필요 1"이다.

### [실행 전 수정][R] N-2: 결과를 본 단계를 다시 돌리지 못하게 막는 장치가 없다(4a-5 5.4), 그리고 판정 코드를 `max`로 합친다
- 근거:
  - `Initialize-Step`(`common.ps1:178-193`)은 `.done`과 같은 시도 폴더만 거부한다. 판정 코드 1로 끝난 `.stop`이 있어도 `-Attempt 2`는 진행된다.
  - step4a(`:30-31`)와 step6(`:49-50`)는 두 판정 도구 코드를 `[Math]::Max`로 합친다. 1(실패, 결과 봄)과 2·3이 함께 나오면 단계 코드가 2·3이 되어, 다시 돌려도 되는 쪽으로 읽힌다. 개별 코드는 `step_record.codes`에 남는다.
  - 4a-5 5.2 넷째 글머리("새 시도의 실행 기록에 앞 시도 경로와 사유")도 구현되지 않았다.
- 실패 시나리오: step6에서 VBH가 1, VBJ가 2로 끝난다. `.stop`의 exit_code는 2다. 운영자가 a2를 돌려 VBH 실패를 다시 판정한다.
- 권장 조치(메인 세션, 명령 파일):
  - `Initialize-Step`이 `.stop*` 기록의 `codes` 가운데 판정 도구 1(R-2의 1은 제외)이 있으면 거부하게 한다.
  - 합칠 때 1이 하나라도 있으면 단계 코드를 1로 한다.
  - 새 시도 기록에 앞 시도의 `.stop` 경로와 사유를 넣는다.

### [실행 전 수정][E] N-3: `TOOL_ERRORS` 밖의 예외는 Python 종료 1, 곧 "실패"로 읽힌다
- 근거: `jp3_baseline_compare.py`의 `TOOL_ERRORS = (OSError, KeyError, ValueError, TypeError, AttributeError, IndexError)`이다. `jp3_tjr_judge.py:1357`, `jp3_case_judge.py`, `jp3_dryrun_evidence.py`도 같은 튜플만 잡는다. `RuntimeError`(예: `run_v5.p3_hash_jobs`), `ZeroDivisionError`, `StopIteration` 같은 예외는 잡히지 않고 종료 1이 된다. `Invoke-Judge`는 이를 실패로 보고 멈춘다. 4a-5 5.4에 따라 다시 돌릴 수 없다.
- 권장 조치(python-expert): `main`에서 `Exception`을 잡아 종료 3으로 낸다(`KeyboardInterrupt` 제외).

### [실행 전 수정][R] N-4: 4a-5 2절 VB 행(① = 0, 어기면 T-JR-10 판정 불가 사유)이 구현되지 않았다
- 근거: `_vb_rerun_record`(`jp3_tjr_judge.py:376-387`)와 `_t_jr_10_preconditions`(`:302-310`)는 VB 줄의 해시·누락·오류만 본다. `t8_line_defects`(`:264-283`)는 VBH·VBJ·VBJ0만 본다(`T8_TEST_SETTINGS` `:163`).
- 권장 조치(python-expert): VB 줄에 `rod_reading_evidence_problems`를 적용하고, 문제가 있으면 `VB_STALE_REASON` 사유와 함께 T-JR-10 판정 불가로 한다. 단위 시험 1개를 더한다.

### [실행 전 수정][R] N-5: 4a-5 3.4의 "L1 참조 sha를 고정 목록 값으로 assert"가 명령 파일에 없다
- 근거: step6는 `--l1-reference-sha256`과 `--base-judge-sha256`을 P-1의 도구 보고 `p1_a1/judge/bj.json`에서 읽는다(`step6_dg3.ps1:14-16`). README `:14`는 "P-1 출력은 만든 뒤 이 목록에 더한다"고 적었지만, 그 목록을 대조하는 단계가 없다.
- 권장 조치(메인 세션): step1이 끝난 뒤 P-1 고정 목록(판정 파일·L1 참조 sha)을 만들어 커밋한다. step6는 그 목록 값과 `bj.json` 값이 같은지 확인한 뒤 진행한다.

### [실행 전 수정][T·S] N-6: 4a-5·정오와 실행 자료가 아직 커밋되지 않았다
- 근거: `seal_check --sums --rev HEAD --check-tracked`에서 `cited_untracked` 4건(error)이 나왔다. 대상은 4a-5와 `.sha256`, 정오 1과 `.sha256`이다. 8판 모두 raw 해시가 봉인과 같다.
- 미추적(git status): `jp3_impl_rereview_4a5.md`, `run_steps/` 9개, `FIXED_INPUTS_325b77a8`·`_d84ba7bd`, `README.md`, `audit_prelaunch.md`, 근거 폴더 `j4a_remedy_9618e00e`·`_325b77a8`·`_d84ba7bd`.
- 시각: 4a-5 mtime 10:12, 정오 10:50. 코드 커밋은 9618e00e 09:39, 325b77a8 10:45, d84ba7bd 11:13이다. 지금 "결과 전"의 근거는 mtime뿐이다.
- 권장 조치(메인 세션): integrity-checker 확인 뒤 step1 전에 커밋한다. 커밋 뒤 `FIXED_INPUTS_d84ba7bd` 55줄을 다시 대조한다(`-text`이므로 sha가 유지돼야 한다).

### [기록]
- R-a [S] 고정 목록 `FIXED_INPUTS_d84ba7bd` 55/55가 같다. 중복 0, CRLF 0. 저장 T4h 폴더를 SUMS와 다시 대조했다: h10 426/426, H-6 135/135, 다름·추가 0.
- R-b [E] 단계 (2) 건식 `summarize`는 증거 2키만 본다. r79 VBJ 줄에 `relock_step_over_1bar_count`·`p1_retract_seed_log_columns`·`lock_window_alignment.n_late_fallback`이 있는지는 단계 (7)에서야 드러난다. 저장 H-6(rev 4 VB)에는 relock·seed 키가 0/135다. 권고: 건식 요약에 이 키들이 있는지(값 없이) 더한다.
- R-c [I] 인터프리터: dynamics-dev `python.exe -I -B`를 직접 부른다. 기준선·저장 h10·H-6 identity의 python과 같고, 스레드 5변수(TBB 포함)를 명시한다. 일치한다.
- R-d [I][추정] mask·workers가 기준선(E `0xfff0000`)·h10·H-6(`0xff0000`)과 다르다. 이번에는 P `0xFFFF`이고, step6는 VBH `0x00FF`, VBJ `0xFF00`, VBJ0 E `0x0FFF0000`이다. 단일 스레드이고 P/E 코어의 ISA가 같아(i7-14700) 수치 영향은 없다고 본다.
  - 영향이 있더라도 P4-1·T-JR-10의 VB 기록(4a-4 4)이 멈춤(거짓 통과가 아닌 쪽)으로 드러낸다.
  - T-JR-12의 VBJ(P)와 VBJ0(E)는 해시가 아니라 등급·READY 비교라 판정에 영향이 없다고 본다. 같은 코어 종류에 두는 편이 깔끔하다.
- R-e [I] `Set-RunEnvironment`가 지우는 목록(`common.ps1:64-65,156`)에 `R79_CANDIDATE`(`r79_sensor_screen.py:742`)와 `R79_TRACE`가 없다. 셸에 남아 있으면 실행 조건이 바뀔 수 있다. 목록에 더하기를 권한다.
- R-f [I] `baseline_check identity`는 "출력마다 sidecar 하나"를 검사하지 않는다(폴더에 sidecar가 0개면 종료 2). 지금 명령 파일은 모든 실행을 래핑하거나 `--out`으로 돌리므로 구성상 충족한다.
- R-g [I] `--mtime`이 기본 `--fail-on warning`이라 엄격하다. 경고로 생기는 종료 2는 결과를 보기 전이므로 다시 돌릴 수 있다(5.4). python-expert 확인 필요 항목 그대로 둔다.
- R-h [C] 단계 (2) select 스캔에 단계 (1) 출력(H-6 판정 파일·L1 참조)이 들어가 파일 수가 늘어난다. s25 키가 새로 생길 경로는 없다. 생성 키가 다르면 `place_keys_file`이 멈춘다(`jp3_dryrun_evidence.py:398-419`). 판정과 무관하다.
- R-i [E] junit(d84ba7bd):
  - full: 7,774건 중 7,640 통과, 2 실패, 132 skip, xfail 0. 실패는 `test_d8x_diag`(J4a-17 예외)와 `test_hydraulics_flow_limit_run`(worktree 데이터, gap에서는 통과)이다.
  - main2: 667 통과, 9 skip.
  - gap: 57 통과, 1 실패. `test_rev7_regression_on_the_stage3_records`(J4a-17 예외)다.
  - critical_skipped 0, xpass 0. 지난번과 같은 예외 구성이다.
- R-j [S] 다이제스트: 모니터 `552c768a…`, 플랜트 `7404b793…`가 99e9132b와 d84ba7bd에서 같다. `git diff --stat 99e9132b d84ba7bd`에서 `two_pressure.py`·`harness_hydraulics.py`·`run_v5.py`는 바뀌지 않았다. `extend_start_bound.py`는 판정 함수만 바뀌었다(`:1798-1913`).
- R-k [R] `ref_check --rev d84ba7bd`(4a-5·정오): missing 5건, untracked 4건이다. 모두 설명된다(P-1 출력은 아직 없음, 필드 이름, 저장소 밖 도구, git 밖 H-6, 미커밋 문서).
- R-l [S] 4a-1의 `.sha256`은 여전히 없다. 고정 목록 3행으로 고정돼 있다.
- R-m [T] 판정 대상 출력이 없다(`j9_runs` 없음). 4a-5 1~5절은 결과 전 정의이고, 6절은 정오(영향 없음)다.

## 규칙↔도구 대조표(4a-5·정오 1)

| 규칙 | 도구·명령 | 판단 |
|---|---|---|
| 1 T-JR-13: 보고 둘(426·135), run당 한 행, 오류 행 = 실패, revision 5, `judged: False`·멈춤 = 판정 불가, 입력 대응 | `jp3_tjr_judge.py:1007-1070`, step7 | 일치(대응은 고정 SUMS 이름 대조) |
| 1 T-JR-14: 135줄 × VBH·VBJ, mismatch = 실패, `n_late_fallback` ≥ 1 = 실패, 키 없음·reason = 판정 불가 | `:1075-1127` | 표 칸은 일치. **(가)는 실행 경로상 닿을 수 없음(N-1)** |
| 1 T-JR-15 / 정오 1: VBJ 135 + 사례 E 5, 시드 ≤ 1 N, relock = 0 | `:1132-1208`, step7 `--lock-rows` | 일치 |
| 1 빈 입력 = 판정 불가 | `:968-974` | 일치 |
| 2 t8 정체성·B2·64자 = 판정 불가 | `:264-283, 342-346, 362-368` | 일치. **VB 행 누락(N-4)** |
| 3.1 설정 대조·base sha ≠ new sha·B2 범위 | `:510-542, 712-716` | 일치 |
| 3.2 자기 대조 | `:745-764`, 시험 `test_jp3_prelaunch_audit.py:65-73` | 일치 |
| 3.3 `judged_key_missing` 우선순위 | `extend_start_bound.py:1880-1893`, `j_p3_inputs.py:188-196` | 일치 |
| 3.4 dg3-judge, L1 sha, 두 sha 필수, keys_file = H-6·135 | `:545-552, 691-709, 810-852`, step6 | 도구는 일치. **"고정 목록 값" 대조는 명령 파일에 없음(N-5)** |
| 4 판정 전 정체성(40자 head, clean, git 실패 표지) | `common.ps1:271-283`, `jp3_run_identity.py`, verif `baseline_check` | 일치(도구로 확인) |
| 5.1 종료 0/1/2/3, 단계 의존 | `EXIT_TABLE`, `Initialize-Step` Requires(step4a dry, 4b dry·fpath, 5 dry, 6 p1·dry, 7 dry·cases·dg3) | 의존은 일치. 예상 밖 예외가 종료 1(N-3) |
| 5.2 폴더, judge/, 덮어쓰기 금지, 앞 시도 기록 | `common.ps1:102-105, 178-193`, 도구 `--out` 거부 | 앞 시도 기록 누락(N-2) |
| 5.3 이어 돌리기 조건 | 명령 파일은 이어 돌리기 없이 새 폴더만 씀. wrap은 다른 head 거부 | 일치(더 엄격) |
| 5.4 결과 본 단계는 다시 돌리지 않음 | 장치 없음 | **N-2** |

## 확인 필요
1. N-1: T-JR-14 (가)를 어떻게 처리할지 정해야 한다.
   - 안 ① 코드: r79 경로가 예외를 오류 줄로 남기고, step6·t12가 그 줄을 실패로 넘긴다.
   - 안 ② 덧붙임: "Dg-3 실행이 `LockWindowMismatchError`로 끝나면 T-JR-14 실패"를 정하고, 명령 파일이 그렇게 표시한다.
   - 결정 4(T-JR-14 판정)의 범위 안에서 어느 쪽인지 사용자나 control-expert가 정한다.
2. N-1·N-3·N-4를 고치면 코드 커밋이 바뀐다. 결정 2를 그대로 적용해 새 커밋에서 일곱 단계를 모두 돌릴지 정해야 한다(권장). 판정 도구 수정만으로 실행 커밋을 다시 잡는 것이 맞는지도 함께 정한다.

## 위임 필요
- python-expert:
  - N-1 ①: `r79_sensor_screen.py:946`의 `_v5_record` 예외 처리. 오류 줄의 이름은 `LockWindowMismatchError:`로 시작하게 한다.
  - N-3: 판정 도구 4개의 `main`이 `Exception`을 잡아 종료 3으로 낸다.
  - N-4: VB 줄의 B2 증거 검사와 단위 시험.
  - R-b: 건식 요약에 r79 VBJ 줄의 relock·seed·n_late 키가 있는지 기록한다(선택).
- control-expert: N-1 ②를 택하면 덧붙임 문안.
- 메인 세션: N-2·N-5·R-e 명령 파일 수정, 고정 목록 갱신, N-6 커밋(integrity-checker 먼저).

## 메인 세션 권고
- 수정 → 커밋 → worktree lock 갱신 → 이 감사의 N 항목만 재감사한다(명령 파일과 도구 차이).
- 그다음 step1부터 사용자 승인 뒤 실행한다.
- step1이 끝난 뒤 P-1 고정 목록을 커밋하고(N-5) step6 전에 대조한다.

## 검사하지 못한 것
- `t4h_replay`가 저장 H-6 T4h(r79 기록)를 `--extend-start tracked_bound --extend-start-revision 5`로 받아들이는지, 보고 행의 `file` 이름이 SUMS 이름과 같은 꼴인지: 실행 금지라 확인하지 못했다. 단계 (7)에서 판정 불가(종료 2)로 드러나는 안전한 쪽이다.
- r79 경로의 rev 5 VBJ 줄에 seed·relock 키가 실제로 기록되는지: 실행 없이는 확인하지 못했다(R-b).
- 명령 파일을 실제로 실행하는 동작(Start-Process 인자 이어 붙이기, sampler, `record.py`): 정적으로만 읽었다. `ps1_lint`은 0이었다.
- `handoff_leak`: 경로 2 넘김 문서가 없다. `log_errors`: 러너 로그가 없다.

## 실행한 검증
- python-dev(`python.exe -I -B`, `MKL_THREADING_LAYER=TBB`):
  - `seal_check --repo … "j_p3_cause/jp3_remedy_spec*.md" --sums baseline SUMS --rev HEAD --check-tracked --code <worktree coupled>`: 8판, `cited_untracked` 4(error), `seal_missing` 1, `cited_ignored_tracked` 18(info).
  - `ref_check --rev d84ba7bd`(4a-5·정오): missing 5, untracked 4(R-k).
  - `placeholder_scan run_steps\*.ps1`: 기본 패턴 0, `<…>` 패턴 0.
  - `ps1_lint`(9개, ast): 0.
  - `junit_skips`(d84ba7bd의 full·main2·gap, critical `test_jp3|j_p3|v5_setting_records|addendum_4a|prelaunch_audit`): R-i.
  - `baseline_check identity`: `325b77a8/e6_identity/forged` 종료 1(`baseline_head_invalid`), `/run` 종료 0. scratchpad 빈 폴더 시험은 종료 2.
  - 즉석 스크립트: `fixed_check.py`(55줄), `t4h_check.py`(426/135), `lwa_keys.py`(H-6 키가 있는지만).
- git 조회: `log`, `status --porcelain`, `worktree list --porcelain`, `diff --stat 99e9132b d84ba7bd`, `diff`(판정 도구·판정 함수·두 replay 파일).
- 최종 판정 직전에 worktree HEAD `d84ba7bd`가 깨끗한지 다시 확인했고, 입력 35개가 바뀌지 않았음도 확인했다(아래).
- 만든 뒤 지운 파일: scratchpad `verif-jp3-prelaunch2\`(guard.json, fixed_check.py, t4h_check.py, lwa_keys.py, seal.md, empty_id\out.jsonl). 폴더째 지웠고 Test-Path는 False다.
- 메모리: `audit_pitfalls.md`에 한 항목을 더했다(정의된 실패에 닿을 수 없는 경로, `max` 코드 합침, `.done`만 보는 시도 가드). `MEMORY.md` 색인도 갱신했다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_addendum_4a1.md 4b122dd0…, jp3_remedy_spec_addendum_4a2.md 2f3e36bd…, jp3_remedy_spec_addendum_4a2.md.sha256 19063b36…, jp3_remedy_spec_addendum_4a3.md f001383a…, jp3_remedy_spec_addendum_4a3.md.sha256 3045bb46…, jp3_remedy_spec_addendum_4a4_erratum1.md 1ccbe526…, jp3_remedy_spec_addendum_4a4_erratum1.md.sha256 27255e69…, jp3_remedy_spec_addendum_4a4.md 67380b10…, jp3_remedy_spec_addendum_4a4.md.sha256 c50c5aac…, jp3_remedy_spec_addendum_4a5_erratum1.md a7a0c973…, jp3_remedy_spec_addendum_4a5_erratum1.md.sha256 5c0be4d7…, jp3_remedy_spec_addendum_4a5.md 562c4e9f…, jp3_remedy_spec_addendum_4a5.md.sha256 b45e407c…, jp3_remedy_spec.md 8be9de22…, jp3_remedy_spec.md.sha256 174e6fb7…, audit_prelaunch.md e62bc724…, FIXED_INPUTS_325b77a8.SHA256SUMS 5aeb5f96…, FIXED_INPUTS_d84ba7bd.SHA256SUMS 00736c77…, FIXED_INPUTS.SHA256SUMS f35fa862…, h10_reuse_rerun_t4h.SHA256SUMS 3d0ed49a…, h6_dg3_v4on_t4h.SHA256SUMS c426f518…, README.md be4c9b28…, common.ps1 0400ef6e…, step1_p1.ps1 9a2d381b…, step2_dry.ps1 5c4c1cd6…, step3_fpath.ps1 89ccf465…, step4a_cases.ps1 af34c287…, step4b_casef.ps1 8ed958d4…, step5_t8.ps1 21c75381…, step6_dg3.ps1 6823136b…, step7_records.ps1 0a6a9141…, jp3_impl_rereview_4a5.md 537cc6fb…, SHA256SUMS 5a07ed62…, SHA256SUMS cdd849f1…, SHA256SUMS 7528d3e7…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음

---

## 메인 세션 덧붙임: 사용자 결정(2026-11-21)

- 확인 필요 1(N-1): **안 ① 코드**. r79 경로가 `LockWindowMismatchError`를 그 줄의 오류 줄(`error: "LockWindowMismatchError: …"`)로 남기고, 판정 도구가 그 줄을 T-JR-14 실패(종료 1)로 보고한다. 실패가 다시 돌리기 경로로 빠지지 않게 한다.
- 확인 필요 2: 결정 2를 그대로 적용한다. N-1·N-3·N-4를 고친 **새 커밋 하나로 7단계 전부**를 돌린다. 명령 파일(N-2·N-5·R-e)과 고정 목록도 그 커밋에 맞춰 다시 만들고, N 항목만 재감사한다.
