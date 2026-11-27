# 436.9 판 8 판정 도구 T8‴ 구현 보고 (D-1·D-1b·D-1c, python-expert, 2026-11-27)

의존성 점검: 모두 있음(python-dev 21개 패키지, depcheck CHECKED 16:51).

## 0. 요약
- **결과**: worktree `C:\workspace\outrigger_control\.claude\worktrees\ed8-judge3`(브랜치 `ed8-judge3`, 기준 5955f25b)에 명세 4절대로 구현했습니다. 커밋은 하지 않았고, 변경은 작업 트리에 그대로 두었습니다.
  - 바꾼 파일 2개: `jp3_ed8_judge.py`, `jp3_tjr_judge_ed8.py`
  - 새 시험 파일 1개: `05_tests/unit/test_ed8_jp3_settings.py`(시험 23개)
- **새 시험**: T8‴에서 23개 모두 통과했습니다.
  - T8″ 코드(5955f25b)에 새 시험만 얹어 돌리면 11개가 실패하고 12개가 통과합니다.
  - T-c는 이름 오류가 아니라 판정 행 수로 실패했습니다: `assert 0 == 10`, `0 == 4`, `0 == 24`. D-1이 재현된 것입니다.
- **P8-4: 깨끗한 통과는 아닙니다.** 건너뜀은 134 → 134로 새 건너뜀이 0입니다. 하지만 시험 1회 비교에서 xdist 배분 순서에 따라 결과가 바뀌는 상태 변화가 나왔습니다(3절).
  - 저장된 T8″ junit과 비교: 새 오류 2건(`test_k2_chrono_runner` 2개, `No module named 'l1r_variant'`)
  - 그 파일만 따로 돌리면 30/30 통과합니다.
  - 같은 5955f25b를 제가 다시 돌린 기준에서는 다른 파일(`test_s8_soil_restore`)이 10건 실패했습니다. 따로 돌리면 34 통과, 1 건너뜀입니다.
  - 판정은 감사·메인 몫으로 넘깁니다(확인 필요 1).
- **실행 경로**: C8 실행 경로 156개 파일, 03_src 트리, "하지 말 것" 13개 파일이 모두 바이트 그대로입니다. 5955f25b 이후 바뀐 추적 파일은 판정 도구 2개뿐입니다.

## 1. 바꾼 파일과 diff 요지 (추적 파일 diff 전문: `t8ppp_evidence\t8ppp_diff_tracked.txt`)

### `04_scripts/04_hydraulic/coupled/jp3_ed8_judge.py` (+47 / −4)
- **상수 2개 추가**. docstring에 규칙 줄(3.6:154-157, 5.1, 5.2, 9:332)을 인용했습니다.
  - `ED8_JP3_JUDGED_SETTINGS = ("VBN", "LSN1", "LSN2", "LSN3", "LSN4", "VBKN", "VBNslow", "VBNfast", "VBNc005", "VBNc04")`
  - `ED8_P3_OFF_SETTINGS = ("VBN0", "VBKN0")`
- **`ed8_jp3_settings()` contextmanager 추가**
  - `j_p3_inputs.REV5_JUDGED_SETTINGS`·`P3_OFF_SETTINGS`를 저장한 뒤 "원래 값 + 판 8 이름(이미 있는 이름은 빼고 뒤에)"으로 바꿉니다.
  - 덧붙이는 일은 private 헬퍼 `_with_names`가 합니다.
  - `finally`에서 원래 **객체**로 되돌립니다.
  - 값을 바꾸는 대입도 `try` 안에 있습니다.
- **`jp3_of`**: `ed7.jp3_of_rows` 호출을 `with ed8_jp3_settings():` 안에서 합니다.
  - 반환 dict에 기록 키 `"J-P3_judged_settings"`를 더했습니다. 상태 계산은 이 키를 읽지 않습니다.
- **모듈 docstring**: T8‴ 단락을 더했습니다.
- import 때는 아무것도 켜지 않습니다. 함수 호출 범위에서만 켭니다.

### `04_scripts/04_hydraulic/coupled/jp3_tjr_judge_ed8.py` (+24 / −4)
- **`_tjr_judged_settings()` contextmanager 추가**
  - `jp3_tjr_judge.REV5_JUDGED_SETTINGS`(import할 때 묶인 이름)를 그 시점의 `j_p3_inputs.REV5_JUDGED_SETTINGS`로 바꿉니다.
  - 원래 바인딩은 `finally`에서 되돌립니다.
- **`edition_8()`**: `with ed8.ed8_identity(), ed8.ed8_jp3_settings(), _tjr_judged_settings():`
  - 순서상 바인딩은 판 8 튜플로 바뀐 뒤에 잡히고, 나올 때는 역순으로 되돌려집니다.
  - 기존 bundle·base·RUN_COMMIT 복원 `finally`는 그대로입니다.
- **모듈 docstring**: D-1c 단락을 더했습니다.

### `05_tests/unit/test_ed8_jp3_settings.py` (새 파일, 시험 23개)
- 저장된 결과 줄은 읽지 않습니다.
- ③ rev 7 기록은 03_src 코드로 만듭니다.
  - `ExtendStartBound(revision=7).identity()`(rule_revision 7, spec_edition 10902ffd)로 시작합니다.
  - 확장 읽기 1회를 `ExtendBoundCheckRev5`에 넣습니다(breach 없음, sensor_grade normal).
  - `.record()`를 꺼낸 뒤 JSON 왕복으로 저장 줄 꼴로 만듭니다.

### 명세 4절 항목별 대응

| 명세 4절 | 대응 |
|---|---|
| 바꿀 파일 1: 상수 2개(docstring 규칙 인용) | 위 상수 2개 |
| `ed8_jp3_settings()`: 저장 → 원래+판 8(중복 없이 뒤에) → `finally`에서 원 객체 | 그대로. 시험 T-b에서 `is`로 확인 |
| `jp3_of`를 `with` 안에서 | 그대로 |
| (선택) `J-P3_judged_settings` 기록 | 넣었습니다(상태 계산 무관) |
| 바꿀 파일 2: `edition_8()`에서 `ed8_jp3_settings` + `tjr7.tjr.REV5_JUDGED_SETTINGS` 바꿈·복원 | 그대로(별도 contextmanager). 되돌림은 모두 `finally` |
| 하지 말 것: `j_p3_inputs.py`·`jp3_tjr_judge.py`·`jp3_ed7_judge.py`·`jp3_j9main_judge.py`·`jp3_ed6_judge.py`·`jp3_12b_judge*.py`·`jp3_ed8_gate_judge.py`·`jp3_ed8_rules.py`·`run_v5.py`·`03_src` | 전부 바이트 그대로(4절) |
| import 때 켜지 않음 | 함수 범위에서만 켬. T-b가 판 8 두 모듈 import 뒤의 튜플이 C8 리터럴과 같은지 확인 |
| 블라인드 출력을 시험 자료로 쓰지 않음, 생산자 job 재실행 없음 | 지켰습니다(6절) |

## 2. 시험 T-a~T-f 결과

T8‴ 작업 트리, Chrono-dev 3.12.15, `-I -B -m pytest -p no:cacheprovider`

| 시험 | 내용 | T8‴ | T8″ 코드 + 새 시험 |
|---|---|---|---|
| T-a `test_a_judged_names_are_the_rule_and_run_v5_sets` | 판정 10 = run_v5 판정 5 ∪ {VBKN} ∪ 감도 4이고 규칙 리터럴과도 같음. 판정·기록 6·③끔 2가 서로 겹치지 않음. 셋의 합집합 = `ED8_SETTINGS` 18개. 판정·기록은 `extend_start_rev7 is True`, ③ 끔은 그 키 없음 | 통과 | 실패(상수 없음) |
| T-b 5개 | 문맥 안 is_p3_expected: (off 태그, VBN0/VBKN0) 거짓, (ED8_TAG, 판정 10) 참. 문맥 밖 두 튜플이 C8 리터럴과 같고 `is` 원 객체. `jp3_tjr_judge.REV5_JUDGED_SETTINGS is j_p3_inputs...`. 예외 뒤 복원. 중첩해도 이름이 한 번만 더해짐. `j_p3_inputs.py` 작업 파일 blob = C8 blob. `edition_8()` 안 tjr 바인딩에 VBN 있음·VBN0 없음, 나오면 복원(예외 포함) | 5 통과 | blob 시험만 통과, 나머지 4 실패 |
| T-c `test_c_producer_lines_are_edition_8_lines` | 생산자 꼴 줄 10개(`run_v5.ed8_batch_jobs(ED8_CASES_BATCH)`, 각 설정의 identity 필드, ED8_TAG, top-level `ed8_settings`, rev 7 기록, `head_only_declared` False, `event_output` 비어 있지 않음)가 `ed8.identity_defects` 0 | 통과 | 통과 |
| T-c `test_c_cases_lines_are_ten_judged_rows` | `jp3_of(lines, ())["J-P3_judged_rows"] == 10`, basis 세 목록이 비어 있음("J-P3 0 judged rows"·"J-P3 no_judged_runs" 없음), rev7 pass. **회귀 감시**: 문맥 밖 `ed7.jp3_judged_rows(ed7.jp3_of_rows(lines, ())) == 0` | 통과 | **실패 `assert 0 == 10`** |
| T-c 매개변수 2개 | C-S 판정 4설정 각 1줄 → 4, C-D VBN 12 + VBNslow 12 → 24, basis 비어 있음 | 통과 | **실패 `0 == 4`, `0 == 24`** |
| T-c `test_c_record_settings_are_never_judged` | 기록 6설정 → 판정 0, `rev7_unjudged_setting_runs` 6, setting_defect·failures 없음, not_judgeable에 "J-P3 0 judged rows" | 통과 | 통과(예상대로: T8″에서도 판정 밖) |
| T-c `test_c_p3_off_line_is_no_expected_row` | cases 10줄 + VBN0 줄 1개(③-off 태그, ③ 기록 없음) → 판정 10, `runs_expected` 10, `rule_missing_runs` 0, basis 비어 있음 | 통과 | **실패 `0 == 10`** |
| T-d `test_d_check_lines_reads_the_vbn_judged_line_evidence` | `edition_8()` + `edition_7()` 안에서 VBN 있음·VBN0 없음. 판정 줄 증거가 모자란 VBN new 줄(L2, rod read 0) → `_check_lines`가 "J-P3 judged event line" 문구를 정확히 1건 더함(`_dg3_identity` 문구는 따로 둠) | 통과 | 실패 |
| T-d `test_d_without_the_edition_8_names_the_check_is_skipped` | 판 8 이름 없이(bundle만 VBN으로) 같은 호출을 하면 그 문구가 없음 = T8″의 조용한 누락 재현 | 통과 | 통과 |
| T-e `test_e_changes_since_t8pp_...` | `git diff --name-only 5955f25b`(작업 트리 포함)가 판정 도구 2개 ∪ `05_tests/` 안 | 통과 | 통과 |
| T-e `test_e_override_is_used_by_the_edition_8_judges_only` | 04_scripts·03_src의 *.py 중 `ed8_jp3_settings`를 쓰는 파일 = {jp3_ed8_judge.py, jp3_tjr_judge_ed8.py} | 통과 | 실패 |
| T-e 매개변수 7개 | 판 6·7 진입 모듈 5개 + `jp3_tjr_judge.py`·`j_p3_inputs.py`가 판 8 두 모듈을 import하지 않음(AST) | 7 통과 | 7 통과 |
| T-e 기존 `test_ed8_run_path.py` 4개 | C8 바이트·폐포·목록·diff | 통과(전체 시험과 대상 실행 모두) | — |
| T-f | 절대 경로, `-p no:cacheprovider`로 cwd = ed8-judge3 루트 23 통과, cwd = 저장소 밖 임시 폴더 23 통과. 끝난 뒤 `git status --porcelain --ignored`는 의도한 3줄뿐(M 2, ?? 1), 임시 cwd 폴더도 빈 채 | 통과 | — |

- 스텁은 T4h 읽기 둘뿐입니다(고정물 `t4h_reads`, 주석에 사유).
  - `judge_stage1_4368.rod_reading` → 참
  - `jp3_ed7_judge.condition_judgement` → pass 요약
  - `jp3_of`·`jp3_of_rows`·`j_p3_rows`·`j_p3_over_rows`·`j_p3_judgement_rev5`는 스텁하지 않았습니다.
- 대상 회귀 실행: `test_ed8*.py` 전부(run_path 포함) + `test_ed7_judge.py` + `test_jp3_rev6.py`에서 459 통과.
- ruff(프로젝트 pyproject 설정, `--no-cache`)·codespell·`git diff --check`: 바꾼 3개 파일 모두 0건.
- T8″ 코드에서 새 시험을 돌린 뒤에는 그 확인 시험 파일을 따로 지우지 않고, 바로 판정 도구 2개 수정을 얹었습니다. 같은 파일이 T8‴의 새 시험입니다.

## 3. P8-4 수치

조건: Chrono-dev `-I -B -m pytest 05_tests/unit -n 12 --dist loadfile -p no:cacheprovider`, `OUTRIGGER_RECORDS_ROOT=C:\workspace\outrigger_control`, NUMBA·hypothesis 저장 위치는 scratchpad, `PYTHONDONTWRITEBYTECODE=1`. t8pp_report.md 3절의 T8″ 조건과 같습니다. 시작 전 `status.py`로 본 유효 예약은 0이었고, affinity는 고정하지 않았습니다.

| 실행 | 시험 수 | 통과 | 실패 | 오류 | 건너뜀 | 시간 |
|---|---|---|---|---|---|---|
| 저장된 T8″ junit(`t8pp_evidence\junit_T8pp_5955f25b.xml`) | 9031 | 8895 | 2 | 0 | 134 | 1498 s |
| 기준 재실행 5955f25b(깨끗한 ed8-judge3, 제가 실행) | 9031 | 8885 | 12 | 0 | 134 | 1509 s |
| **T8‴ 작업 트리** | 9054 (= 9031 + 새 23) | 8916 | 2 | 2 | 134 | 1576 s |

- **기존 실패 2개(세 실행 공통)**: `test_hydraulics_flow_limit_run::test_coupled_batch_rows_and_resume`, `test_d8x_diag::test_rerun_gives_the_stored_command_hash`
- **새 시험 23개**: 모두 통과(미통과 0)
- **새 건너뜀**: 0(134 → 134, 상태 변화 목록에 skipped 없음)
- **저장된 T8″와 대비한 T8‴ 상태 변화 2건**: `test_k2_chrono_runner::test_hook_sets_cn_only_from_the_valve`, `::test_dhat_recorder_reads_only`가 passed에서 error로 바뀌었습니다.
  - 원인 메시지: `ModuleNotFoundError: No module named 'l1r_variant'`
  - t8pp_report.md:107-110이 중간 커밋 c877b8cd에서 이미 기록한 증상과 같습니다(xdist 배분 순서에 따른 sys.path 의존).
  - T8‴에서 그 파일만 따로 돌리면 30/30 통과합니다(`T8ppp_k2_chrono_runner_alone.txt`).
- **기준 재실행과 대비**: 위 2건에 더해 `test_s8_soil_restore` 10건이 failure에서 passed로 바뀌었습니다.
  - 기준 재실행에서 이 10건은 `No module named 's9_merge'`로 실패했고, 저장된 T8″에서는 통과했습니다.
  - 같은 커밋 5955f25b에서 그 파일만 따로 돌리면 34 통과, 1 건너뜀입니다.
- 두 파일 모두 바뀐 모듈(`jp3_ed8_judge`·`jp3_tjr_judge_ed8`·`j_p3_inputs`·`jp3_tjr_judge`)을 import하지 않습니다(Grep 0건).
- 새 시험 파일이 하나 늘면서 loadfile 배분이 바뀐 것으로 추정합니다(추정, 확인 안 함).
- **판단**: 규칙 문구 "새 실패 0"은 이 한 번의 비교만으로는 깨끗하게 충족되지 않습니다. 이 2건을 순서 의존 기존 성질로 볼지는 감사·메인이 정할 일입니다(확인 필요 1).
- 대조 파일
  - `junit_compare_T8pp_stored_vs_T8ppp.txt`
  - `junit_compare_base_rerun_vs_T8ppp.txt`
  - `junit_compare_T8pp_stored_vs_base_rerun.txt`(같은 커밋 두 실행 사이 10건 차이)

## 4. 실행 경로 바이트 불변
`byte_check_T8ppp.json`(Python subprocess로 git blob 대조)
- C8 실행 경로 목록 156개 파일: 작업 파일 blob 불일치 0
- 03_src 트리 HEAD = C8 = 목록 `ed797e8e…`, 작업 트리 03_src diff 없음
- "하지 말 것" 13개 파일의 작업 파일 blob = 5955f25b blob(모두 true)
  - `j_p3_inputs.py`, `jp3_tjr_judge.py`, `jp3_ed7_judge.py`, `jp3_j9main_judge.py`, `jp3_ed6_judge.py`, `jp3_12b_judge.py`, `jp3_12b_judge_ed7.py`, `jp3_12b_judge_ed8.py`, `jp3_ed8_gate_judge.py`, `jp3_ed8_rules.py`, `run_v5.py`, `jp3_tjr_judge_ed7.py`, `jp3_baseline_compare.py`
- `git diff --name-only 5955f25b` = 판정 도구 2개뿐
- `test_ed8_run_path.py` 4개 통과

## 5. 커밋할 파일과 제안 커밋 메시지
작업 파일 raw sha256. 판정 도구 2개는 autocrlf로 CRLF이고, 새 시험 파일은 LF입니다. blob은 셋 다 LF입니다.

| 파일 | 상태 | sha256(작업 파일) |
|---|---|---|
| `04_scripts/04_hydraulic/coupled/jp3_ed8_judge.py` | M | `c01004b1619af40cf90ed8ecf901bc04fc455fa5d5123b20c48e50b8804819b3` |
| `04_scripts/04_hydraulic/coupled/jp3_tjr_judge_ed8.py` | M | `14c10cafd5794eb4101ab17ffc8565ef806d4b7a540038fafca8d10085b43a0d` |
| `05_tests/unit/test_ed8_jp3_settings.py` | ?? (새 파일) | `bfd37f3fd7d2918f4f3cec4b288753b35122b108c5d113fc51e5a7195f614a7c` |

제안 커밋 메시지:
```
436.9 ed8 judge commit T8''': J-P3 settings of edition 8 (D-1, D-1b, D-1c)

- jp3_ed8_judge: ED8_JP3_JUDGED_SETTINGS (10, spec v8 3.6/5.1/5.2/9) and
  ED8_P3_OFF_SETTINGS (VBN0, VBKN0); ed8_jp3_settings() adds them to the
  j_p3_inputs tuples around each jp3_of J-P3 read and restores the C8 objects
  (j_p3_inputs.py stays the C8 run path bytes, P8-11)
- jp3_tjr_judge_ed8.edition_8(): the same names plus the jp3_tjr_judge
  REV5_JUDGED_SETTINGS binding, so t12 --bundle VBN checks the J-P3
  judged-line P4 evidence (_check_lines)
- test_ed8_jp3_settings: T-a .. T-e of control_d1_settings.md 4 (producer-form
  lines, real J-P3 path; T-c fails on T8'' 5955f25b)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01S2ErLKQQpuRHeBUsoPmLoF
```

## 6. 공개 항목 (읽은 파일·검색 범위)
- **Read(메인 checkout)**
  - `ed8_design\control_d1_settings\control_d1_settings.md`(전체), `d1_settings.json`, `d1_decision_draft.txt`
  - `ed8_design\t8pp_evidence\`: `suite_T8pp_5955f25b.log` 앞 40줄·끝 25줄, `junit_compare_C8_vs_T8pp.txt`, `SHA256SUMS`, `junit_T8pp_5955f25b.xml` 첫 testsuite 줄. junit 전체는 대조 스크립트로 파싱했습니다.
  - `ed8_design\audit_prerun\t8pp_report.md` 85~124행(+ 단일 파일 Grep)
  - `ed8_design\p84_suite_41e107e9_56849248\run_p84.ps1`
- **Read(ed8-impl worktree)**: `06_analysis\02_control\j_p3_cause\prelaunch_j9\run_steps_ed8\full_suite_ed8.ps1`(경로를 직접 지정)
- **Read(ed8-judge3)**
  - `jp3_ed8_judge.py` 1~300·1275~1334
  - `jp3_tjr_judge_ed8.py`·`jp3_tjr_judge_ed7.py` 전체
  - `jp3_tjr_judge.py` 185~269·630~704·836~885
  - `j_p3_inputs.py` 1~291
  - `jp3_ed7_judge.py` 295~359·380~539
  - `jp3_j9main_judge.py` 265~334
  - `run_v5.py` 270~509
  - `jp3_baseline_compare.py` 995~1084
  - `03_src\outrigger_sim\control\extend_start_bound.py` 376~535·551~578·1658~2337
  - `test_ed8_judge.py` 1~120·660~749
  - `test_ed7_judge.py` 700~869
  - `test_jp3_rev6.py` 625~694
  - `test_ed8_run_path.py` 전체
- **Grep(경로는 모두 하위 폴더나 단일 파일)**
  - ed8-judge3 `04_scripts`(glob `*.py`)·`03_src`(glob `*.py`)·`04_scripts\04_hydraulic\coupled`(glob `*.py`, `jp3_ed{7,8}*.py`, `jp3_{tjr_judge,baseline_compare}.py`)
  - `05_tests`(glob `*.py`)·`05_tests\unit`(glob `test_{k2_chrono_runner,s8_soil_restore}.py`)
  - 단일 파일: `jp3_ed8_judge.py`, `jp3_ed7_judge.py`, `extend_start_bound.py`, `run_v5.py`, `jp3_baseline_compare.py`, `test_ed8_judge.py`, `test_ed7_judge.py`, `test_jp3_rev6.py`, `test_s8_soil_restore.py`, `pyproject.toml`, scratchpad의 draft `jp3_ed8_judge.py`
- **Glob**
  - 메인 checkout `...\ed8_design\t8pp_evidence\`(`*`), `...\ed8_design\p84_suite_41e107e9_56849248\`(`*`), `...\ed8_design\`(`*t8p*`)
  - `C:\Users\jinbeom\.claude\runners`(`**/*t8pp*`, `outrigger-ed8*/**/*.ps1`)
  - ed8-judge3 `04_scripts`(`**/s9_merge*`)
- **시험 코드의 스캔 범위**: T-e 시험은 worktree의 `04_scripts`와 `03_src` 아래 *.py만 rglob로 읽습니다(블라인드 없음).
- **훅에 막힌 시도**: 없습니다. 블라인드를 품은 상위 폴더(`j9_runs`, `56849248`, `j_p3_cause`, `06_analysis`, 저장소 루트, worktree 루트)를 Grep·Glob 범위로 쓰지 않았습니다.
- **블라인드**
  - `j9_runs\56849248\impl_*_a1\`, `l1ref_a1\`와 worktree 사본은 Read·Grep·Glob·목록 어디에도 쓰지 않았습니다.
  - `stage4_prejudge\`는 열지 않았습니다(보고서 md도 열지 않음).
  - 4단계 출력은 시험 자료로 쓰지 않았습니다. 생산자 job을 다시 돌리지 않았고, 판정 도구로 관문을 판정하지 않았습니다.
  - 전체 시험은 T8″와 같은 조건(`OUTRIGGER_RECORDS_ROOT`=메인 checkout)이었습니다. 시험이 읽는 저장 기록의 값은 제가 열지 않았습니다.
- **기타**
  - ed8-judge2·ed8-impl·ed8-judge는 쓰지 않았습니다. ed8-impl은 실행 스크립트 1개만 Read했습니다.
  - 정션·링크는 만들지 않았습니다.
- **정리**
  - 전체 시험 두 번이 각각 `__pycache__` 13개를 남겼습니다. `PYTHONDONTWRITEBYTECODE`와 `-B`를 줘도 생겼으니, 하위 프로세스를 띄우는 시험에서 나온 것으로 봅니다(추정).
  - git status가 보여 준 그 13개 경로만 지정해서 지웠습니다. 최종 `git -C ed8-judge3 status --porcelain --ignored`는 의도한 3줄뿐입니다.
  - T-f의 단독 실행 두 번은 캐시를 남기지 않았습니다.
  - scratchpad `python-t8ppp\`는 지웠습니다.
- **실행 방식**: Python·pytest는 PowerShell로 실행했습니다. Bash는 git 조회 2회에만 썼고, heredoc과 파이프는 쓰지 않았습니다. 종료한 프로세스는 없습니다.

### 증거 폴더 `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\t8ppp_evidence\` (새로 만듦, SUMS는 쓰지 않음)

| 파일 | sha256 |
|---|---|
| `junit_base_5955f25b_rerun.xml` / `suite_base_5955f25b_rerun.txt` | `5349442f…` / `27f70098…` |
| `junit_base_5955f25b_soil_restore_alone.xml` / `base_5955f25b_soil_restore_alone.txt` | `26ac9429…` / `a74d1da7…` |
| `junit_newtests_on_T8pp_5955f25b.xml` / `newtests_on_T8pp_5955f25b.txt` (T-c가 T8″에서 실패) | `78d7d6bc…` / `2d2baca1…` |
| `junit_T8ppp_worktree.xml` / `suite_T8ppp_worktree.txt` | `fde17ef2…` / `93f779e1…` |
| `junit_T8ppp_k2_chrono_runner_alone.xml` / `T8ppp_k2_chrono_runner_alone.txt` | `f9d91157…` / `f4ae4621…` |
| `junit_Tf_cwd_worktree.xml` / `Tf_cwd_worktree.txt` | `b87a5af9…` / `9acc3c45…` |
| `junit_Tf_cwd_outside.xml` / `Tf_cwd_outside.txt` | `60e9fd63…` / `222f5816…` |
| `ed8_and_related_files_T8ppp.txt` (459 통과) | `ef04e06e…` |
| `junit_compare_T8pp_stored_vs_T8ppp.txt` | `8c931ec3…` |
| `junit_compare_base_rerun_vs_T8ppp.txt` | `11c8efda…` |
| `junit_compare_T8pp_stored_vs_base_rerun.txt` | `1b630da1…` |
| `byte_check_T8ppp.json` | `da78c1f2…` |
| `t8ppp_diff_tracked.txt` | `feaab923…` |

- 로그와 대조 txt 안에는 scratchpad 경로 문자열이 들어 있습니다(지금은 지워진 경로).
- 폴더 SHA256SUMS는 메인이 이 보고서를 저장한 뒤 `baseline_check.py write-sums`로 써 주십시오.

## 사용자 조치 필요

| 대상 | 내용 | 명령 | 대체 경로 |
|---|---|---|---|
| Suspended git.exe | 제가 띄운 PowerShell 반복문(blob 대조)의 `git -C ed8-judge3 rev-parse 5955f25b:…/jp3_ed8_rules.py`가 Suspended로 멈췄습니다. 래퍼 PID 89112, 자식 PID 58136 / TID 99952, 시작 2026-11-27 18:00:57. dry-run 결과 `ready`. 그 PowerShell 작업(백그라운드 ID bffj4qzda)이 아직 이 git을 기다립니다 | `& "C:\ProgramData\miniforge3\envs\python-dev\python.exe" -I -B "C:\Users\jinbeom\.claude\tools\monitor\resume_thread.py" --pid 58136 --tid 99952 --started "2026-11-27 18:00:57" --apply` | 대조는 Python subprocess 스크립트로 다시 해서 끝냈습니다(4절). 읽기 전용 rev-parse라 재개해도 부작용은 없습니다 |

## 확인 필요
1. **P8-4를 한 번의 비교로 판정할 수 있는지**
   - 바뀐 모듈을 import하지 않는 시험 파일들이 xdist loadfile 배분에 따라 실패·통과를 오갑니다(`test_k2_chrono_runner` 2개, `test_s8_soil_restore` 10개).
   - 저장된 T8″ 대비 새 오류 2건, 같은 커밋 두 실행 사이 차이 10건입니다.
   - 두 가지 길이 있습니다.
     - (가) 그 파일 단독 통과(30/30, 34+1s)를 근거로 순서 의존 기존 성질로 봅니다(t8pp_report:107-110 선례).
     - (나) 정식 P8-4를 러너(`full_suite_ed8.ps1`꼴, 자동 재실행 없음)로 T8‴ 커밋에서 다시 돌려 판정합니다.
   - 저는 판정하지 않았습니다.
2. **T-e `test_e_changes_since_t8pp_...`는 T8‴ 전용입니다.** 명세대로 "5955f25b 이후 변경 ⊂ {판정 도구 2개, 05_tests}"를 단언합니다. T8‴ 위에 다른 04_scripts 파일을 바꾸는 커밋이 생기면 이 시험이 실패합니다. 기존 `test_t8_diff_against_c8…`와 같은 성격입니다.
3. **`jp3_of` 출력의 새 기록 키**: `J-P3_judged_settings`가 cases 보고서 최상위와 census·heldout 단계의 `J-P3` dict에 함께 나옵니다. 상태 계산은 읽지 않습니다. 넣지 않기를 원하면 1줄만 빼면 됩니다.
4. **T-c ③ 기록의 출처**
   - 명세가 허용한 두 방법 가운데 "03_src ③ rev 7 코드가 만든 기록"을 골랐습니다.
   - 실제 모니터 실행이 아니라 `ExtendStartBound(revision=7).identity()` + `ExtendBoundCheckRev5` 읽기 1회의 `record()`입니다.
   - 판 7 VBM 저장 줄은 쓰지 않았습니다. 저장 자료에 기대지 않으니 worktree에서도 건너뛰지 않습니다.

## 메인 세션 권고
- 커밋 전에 integrity-checker를 돌려 주십시오. 커밋 뒤에는 T8‴ 해시를 고정하고 `ed8-judge3`를 `git worktree lock`해 주십시오.
- 정식 P8-4가 필요하면(확인 필요 1의 (나)) 커밋 뒤 깨끗한 T8‴ checkout에서 기존 러너를 돌려 주십시오. Chrono-dev `-n 12`로 약 26분 걸립니다. 출력은 `~/.claude/runners/outrigger-ed8/…`의 새 폴더에 두십시오.

## 위임 필요
- **verif-protocol-auditor**: T8‴ 재감사(control_d1_settings.md 7절 목록)
  - 판 8 이름이 빠진 이름 튜플 전수 검색
  - 덮어쓰기가 판 8 문맥에서만 켜지는지
  - P8-11 실행 경로 바이트
  - 블라인드 권한이 있는 쪽에서 cases 판정 행 수(10)만 보는 값 없는 스모크
  - 경로 2 도구의 판정 집합 확인. 저는 경로 2 도구를 열지 않았습니다.

## 기타
- 커버리지: 측정하지 않았습니다(요청 없음).
- 사용한 스킬: 없음
- 메모리 반영안: `tool_xdist_order_flakes_suite_compare.md`를 새로 썼고 MEMORY.md 색인에 1줄을 더했습니다. 내용은 같은 커밋에서도 loadfile 배분에 따라 sys.path 의존 실패가 옮겨 다니니, 저장 기준·새 기준 둘과 대조하고 바뀐 파일을 단독으로 다시 돌리라는 것입니다. PowerShell git 반복문 대신 Python subprocess를 쓰라는 내용도 넣었습니다.
