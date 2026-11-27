## 무결성 검사 요약 (T8⁗, ed8-judge4)
- 대상: 작업 파일 3개 (gate judge M, test_ed8_gate_p80_key 새 파일, test_ed8_jp3_settings M) + 명세·결정·보고·증거 폴더. 범위는 호출자 지정, 6개 항목 전수.
- 판정: ✅ 통과. 커밋을 막을 결함은 없다.
- 축별 발견: A 0 · B 0 · C 0 · D 0 (Critical 0 / High 0 / Medium 0 / Low 2, 아래 권고)

## 차단
없음.

## 권고 (Low)
1. [Low][B] `baseline_check.py sums`는 `cited_untracked` 16건을 error로 낸다. 증거 폴더 `t8pppp_evidence`(SUMS 포함 16개 파일)가 아직 git 미추적이라는 뜻이다. ignore에는 걸리지 않았다(`cited_ignored` 0). 해시 불일치 0, 파일 없음 0, 목록에 없는 파일 0, 항목 15개다. 커밋에 증거 폴더를 포함할지는 호출자가 정한다. 포함하지 않으면 커밋된 문서에서 인용한 증거 sha가 근거 없이 남는다.
2. [Low][A] 새 시험 파일은 LF이고 gate·settings는 CRLF(607/607, 333/333)다. `core.autocrlf=true`이고 `.gitattributes`에 text·eol 지정이 없다(`text: unspecified`). 커밋 때 정규화되므로 문제는 아니다. 보고서가 이미 적은 내용이다.

## 이상 없음 (항목별 근거)
**1. 코드와 명세**
- `p80_job_key`는 `run_v5.job_key(dict(job))`를 그대로 쓴다. 함수 안에서 지연 import를 한다. `run_v5.py:759`의 `RUNTIME_JOB_KEYS = ("mask","t4h_dir")`와 `job_key`(`run_v5.py:771` 부근)가 mask·t4h_dir만 뺀다.
- `hash_table`의 `key=row_identity` 기본값은 유지됐고 지역 변수만 `job_key`로 바뀌었다.
- `judge_p80`은 명세 5절과 일치한다.
  - run과 reference 문제를 분리한다. reference 문제와 키 수 ≠ 114는 `setting_defects`로 간다.
  - 기준에 문제가 있으면 `reference_compared`는 false이고 equal·missing·extra·differing은 None이다.
  - run 문제는 failures이며, 문구 순서는 그대로다.
  - 보고 키 `jobs`, `run_jobs`, `equal`, `missing`, `extra`, `differing`, `run_line_problems`, `reference_line_problems`, `reference_compared`, `key`, `settings_reference`, `settings_run`이 모두 있다.
  - `key` 문자열은 "run_v5.job_key (spec v8 12 P8-0)"다.
  - setting별 개수 함수는 중첩 함수라 최상위 정의가 늘지 않는다.
- `git diff 2263b246` 전문을 읽었다. 바뀐 곳은 모듈 docstring, `p80_job_key`(새로 추가), `hash_table`, `judge_p80`뿐이다. `RUNTIME_JOB_KEYS`, `row_identity`, 팔 짝 관문, `judge_t8`, 상수, CLI 등 "하지 말 것" 목록은 diff에 나타나지 않는다.
- import는 `Callable, Iterable, Mapping`이 이미 있다.
- `byte_check_T8pppp.json`: 금지 파일 8개의 blob이 T8‴와 같다(모두 True). C8 실행 경로 156개 불일치 0. `diff 56849248`은 23개이고 04_scripts·05_tests 밖 0, 실행 경로 안 0이다.

**2. `test_ed8_jp3_settings.py` 변경**
- diff는 `T8PPP_COMMIT` 상수 추가와 비교를 `git diff --name-only T8PP T8PPP`(고정 범위)로 바꾼 것뿐이다. 허용 목록 `T8PPP_CHANGED_PATHS`와 단언문은 그대로다.
- 고정 범위 5955f25b..2263b246의 실제 변경 경로는 `jp3_ed8_judge.py`, `jp3_tjr_judge_ed8.py`, `test_ed8_jp3_settings.py` 세 개다. 허용 목록과 `05_tests/`로 전부 설명되므로 같은 단언이 통과한다.
- 깨끗한 T8‴ checkout(HEAD = 2263b246)에서는 작업 트리 diff와 고정 범위 diff가 같다. 그래서 T8‴에 대한 단언 세기는 같고 허용 목록은 넓어지지 않았다.
- 작업 트리의 미커밋 변경을 잡는 기능은 이 시험에서 빠졌다. 그 몫은 새 시험 `test_changes_since_t8ppp_are_the_gate_and_tests_only`(2263b246 대비 HEAD와 작업 트리, gate와 `05_tests/**`만 허용)가 맡는다.
- 한계: 판 8에서 판정 커밋이 또 생기면 새 T-e가 같은 방식으로 깨진다(보고서 확인 필요 2에 이미 적혀 있다).

**3. 보고서와 증거**
- 작업 파일 3개의 raw sha256을 재계산했고 보고서 6절과 세 개 모두 일치한다. `ast.parse`도 통과했다.
- `junit_T8pppp_worktree.xml`: tests 9071, failures 3, errors 0, skipped 134다. 보고서의 통과 8934는 9071−3−134와 맞다.
- `junit_T8pppp_changed_files_alone.xml`은 81개, 실패 0이다.
- `junit_compare_T8ppp_formal_vs_T8pppp.txt`: A 9054, B 9071, only_A 0, only_B 17, changed 1(T-e passed → failure)이다. 새 시험 17개는 `new in B` 목록에서 모두 passed다. 이 파일이 새 시험 수 17을 뒷받침한다. 파일 수는 `test_ed8_gate_p80_key.py`의 17 테스트 함수 구성(T-a 2 · T-b 6 · T-c 2 · T-d 2 + main 2 · T-e 2 · T-f 1)과 맞는다.
- 보고서 4절의 "수정 뒤 전체 시험은 다시 돌리지 않았다"는 서술은 증거와 모순이 없다. 134 skip이 그대로이고 새 skip은 0이다. 134개는 T8‴ 정식 junit 134개와 같은 수다. 전체 9071은 settings 시험 수정 전 실행이다. 단독 81개가 수정 뒤 실행이다.
- `byte_check_T8pppp.json`은 위 1항에 적은 내용과 같고, 작업 파일 3개 sha가 보고서와 같다.
- SUMS 대조: `baseline_check.py sums`는 mismatch 0, missing 0, unlisted 0이다.

**4. git 상태**
- `status --porcelain --ignored`는 의도한 3줄뿐이다(`M` gate, `M` settings, `??` 새 시험). ignored·`__pycache__` 항목은 없다.
- `diff --name-only 2263b246`은 gate와 `test_ed8_jp3_settings.py` 두 줄이다. 새 시험은 미추적이라 이 목록에 나오지 않는다.

**5. docstring 인용**
- spec v8 규칙 361행은 P8-0 행으로 "`ed7_probe.py --arms a2 --part all` 114줄 = b46bdf8f 재현 줄별 해시"라고 적혀 있다.
- 345행은 "목록 밖 문제는 입력 결함(`setting_defect`)"이고, 346행은 "계산되지 않은 판정 항목은 판정 불가"다. docstring의 "spec 10:345"는 맞다.
- `ed7_probe.py:228`은 `todo = [job for job in jobs if run_v5.job_key(job) not in done]`이다. `run_v5.py:759`는 `RUNTIME_JOB_KEYS = ("mask", "t4h_dir")`다.

**6. `line_problems` 소비처**
- 제거된 gate의 `line_problems` 키를 읽는 곳은 `ed8_design\control_p80p85\p80_plan_keys.py:38`(`rep["line_problems"]`) 하나뿐이다. 이 파일은 T8‴ worktree를 가리키는 이미 끝난 확인 스크립트다. 출력은 저장돼 있다. 이 스크립트를 ed8-judge4로 바꿔 다시 돌리면 KeyError가 난다. 보고서가 이미 적은 내용이다.
- 04_scripts(`*.{py,ps1}`)에서 나온 나머지 `line_problems`는 d0·ed6·ed7·k1·las 등 다른 모듈의 같은 이름 함수나 키이고 gate 보고와 무관하다. 05_tests에서는 gate 키 소비처가 새 시험의 `run_line_problems`·`reference_line_problems`뿐이다. `test_ed8_gate_judge.py`에는 없다.

## 검사하지 못한 것
- 시험은 돌리지 않았다(지시에 따라). junit 수치는 보고서 증거 파일 재계산에 의존한다. 수정 뒤 전체 시험은 보고서도 다시 돌리지 않았다고 밝혔다. 정식 P8-4는 커밋 뒤에 깨끗한 checkout에서 다시 돌려야 한다.
- 고정 기준 파일과 `e241638d` blob은 열지 않았다. 새 시험 T-d·main 시험이 자기 대조 스모크를 하지만 이 감사에서는 실행하지 않았다.
- 보고서의 ruff·codespell·`diff --check` 0건은 재확인하지 않았다.
- 시작 시점 `source_guard snapshot`은 하지 않았다. 대신 대상 폴더에 쓰기를 하지 않았고, 끝에서 worktree `status --porcelain --ignored`가 3줄뿐임을 확인했다. 이 확인은 파일 내용 불변 증명이 아니라 상태 목록 확인이다.

## 사용자 조치 필요
없음.

## 실행한 검증
- 읽은 것: 명세 `control_p80p85.md` 전체, `impl_report_t8pppp.md` 전체, 새 시험 전체, 두 파일의 `git diff 2263b246` 전문, 규칙 v8 336~365행, `ed7_probe.py` 225~230행, `run_v5.py` 755~772행.
- 도구: python-dev `-I -B`로 sha256·junit XML·`byte_check_T8pppp.json`을 재계산(`ast.parse` 포함), `baseline_check.py sums`, 의존성 점검(STAMP/CHECKED OK).
- git 조회: `status --porcelain --ignored`, `diff --name-only 2263b246`, `diff --name-only 5955f25b 2263b246`, `check-attr`.
- Grep: 단일 경로(ed8-judge4의 `04_scripts`, `05_tests`와 메인 `ed8_design`)에 `glob *.{py,ps1}`를 붙여 `line_problems`를 검색했다.
- 블라인드(`impl_*_a1`, `l1ref_a1`, worktree 사본)와 경로 2 도구는 열지 않았다. 블라인드를 품은 상위 폴더는 검색 범위로 쓰지 않았다. 고정 기준 해시 값은 출력하지 않았다. 증거 폴더에서 연 파일은 `impl_report`, junit 3개, `byte_check` JSON, SUMS뿐이다.
- 사용한 스킬: 없음.
- scratchpad `integrity-t8pppp\`는 지웠다(`Test-Path` False).
- 원본 불변: 확인 못함 — `source_guard` 스냅숏·검증을 돌리지 않았다. 읽기 도구와 조회 명령만 썼고 파일을 수정·생성하지 않았다.
- 이 보고는 `.md` 저장 대상이 아니다.
