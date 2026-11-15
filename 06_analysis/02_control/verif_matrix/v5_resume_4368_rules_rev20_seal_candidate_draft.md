# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev20 (rev19 정렬 뒤: R19-7 (1) 모듈 수준 이름, 안전 종료 행의 4.2·6·7.2 판정 키, 사실 오류 공개, 결과 본 뒤 개정, 봉인 후보 초안)

- **상태: 봉인 후보 초안(봉인 전).** 봉인 전에는 실행·판정에 쓰지 않는다. 봉인 때 바꿀 머리 줄은 끝 절에 원문으로 적었다.
- 원판~rev18은 고치지 않는다. 이 판은 rev19(sha256 `7f87b8bb091d23c1bdcd2bf356b732a77bea12c4cfc4853d0ea58f7d239c92b2`, 봉인 2026-11-15 15:25:13 +09:00, 봉인 기준 커밋 S6 `59c933b50d6a32db999c42951d3c168cd552640d`, 봉인 파일 커밋 S7 `38897f0d8e216d99253adbc18c71ab1ad027c758`, 브랜치 `z4373-s4`) 위에 쌓인다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 앞 판 그대로다. 용어(봉인 기준 커밋, 봉인 파일 커밋)는 rev16 4행과 같다.
- **시점: 두 도구 브랜치의 rev19 정렬 구현(경로 1 `1255d6d`, 경로 2 `5dcc8d4`)과 경로 2의 R19-7 대조 결과·질문 T-9를 본 뒤, `z4373-r3b`를 만들기 전, 메인 checkout은 R3(봉인 SEAL_TIME, 봉인 기준 커밋 SEAL_COMMIT).** 이 판은 결과를 본 뒤의 개정이다. 본 자료는 R20-0에 적었다.
- 작성: control-expert, 2026-11-15. 기준: R2 `b9f5707`(실행), R3 `576eb87`(판정 도구), S7 `38897f0`(rev19).
  - 계기: R19-7 조건 (1)을 문장 그대로 대조하면 함수 밖의 모듈 수준 상수 정의 때문에 거짓이 되고, 경로 2가 안전 종료 행의 4.2·6·7.2 판정 키를 물었다.
  - 사용자 결정 66(2026-11-15)을 R20-1~R20-5에 반영했다.
- **봉인 준비판이다.** 봉인 전에 답이 필요한 항목은 없다(확인 필요 0). 이 줄은 봉인 때 바뀐다.
- **바꾸지 않는 것**: 숫자 문턱, 등급과 우선순위(원판 8.1), 멈춤 조건의 뜻(원판 8.2), 묶음 범위와 행 목록, 사전 예측, 두 경로 요건, 실행 커밋 R2, 이미 돈 실행의 argv·코드, rev16~rev19의 다른 조항.

## R20-0. 결과 본 뒤 개정의 공개 (본 자료 목록)

- 이 작성자(control-expert)가 본 것(읽기 전용, 2026-11-15): 메인 세션이 전한 경로 2 `5dcc8d4`의 R19-7 대조 사실((1) 거짓, (2) 참)과 질문 T-9, `git diff f46b5ab b9f5707 -- 04_scripts/03_control/s8/r67_g1_screen.py`, `git show b9f5707:04_scripts/03_control/s8/r67_g1_screen.py`의 `RESUME_K1_KEY` 정의·읽는 줄(616·622·645행)과 함수 머리(608·626·636·652·669행), 원판 4.2·6·7.2·8.2(S-3·S-5·S-6) 머리 문장, S7의 rev19 R19-7 본문.
- 판정서에는 이 목록을 그대로 싣고, 이 판의 정의를 "결과 본 뒤 정한 정의"로 적는다.

## R20-1. R19-7 조건 (1)의 고쳐 씀

- **[정의]** R19-7 조건 (1)을 다음으로 바꾼다: `git diff f46b5ab <쓴 커밋> -- 04_scripts/03_control/s8/r67_g1_screen.py`의 바뀐 줄(+/−)마다 다음 둘 중 하나가 참이다.
  - (1a) 그 줄이 기록 전용 함수(`v5_job_record`, `v5_branch_record`, `v5_setting_record`, `resume_k1_block`) 안에 있다.
  - (1b) 그 줄이 함수 밖의 모듈 수준 이름(상수와 그 바로 아래 docstring)의 정의이고, 그 이름을 읽는 이 파일의 **모든** 함수가 위 기록 전용 함수 목록 안에 있다. 다른 파일이 **`r67_g1_screen` 모듈의** 그 이름을 읽으면 (1b)는 거짓이다. 읽는 방식은 `from r67_g1_screen import <이름>`이거나, `r67_g1_screen`을 import한 별칭으로 `<별칭>.<이름>`을 쓰는 것이다. 다른 모듈이 같은 이름을 따로 정의한 것과 그 다른 모듈의 이름을 읽는 것은 여기에 해당하지 않는다(예: `r79_sensor_screen.py`·`run_v5.py`가 따로 정의한 `RESUME_K1_KEY`, `test_resume4368.py`가 읽는 `run_v5.RESUME_K1_KEY`). 덩어리 표에는 이 점검에 쓴 grep 명령과 그 결과를 함께 싣는다.
  - 덩어리 표에는 덩어리 머리, 감싸는 함수와 함께 함수 밖 줄마다 "그 줄, 정의하는 이름, 그 이름을 읽는 함수"를 싣는다. 하나라도 어기면 S-11이다. 조건 (2)는 그대로다.
- **[정의]** 덩어리 표는 `git diff -U0 f46b5ab <쓴 커밋> -- 04_scripts/03_control/s8/r67_g1_screen.py`로 만든다. 바뀐 줄 단위로 감싸는 함수 또는 (1b) 이름을 적는다.
- **[사실]** 사례: `RESUME_K1_KEY = "resume_k1"`과 그 docstring 줄(`b9f5707` 622·623행, 첫 덩어리)은 함수 밖에 있다. 이 이름을 읽는 함수는 `v5_job_record`(616행)·`v5_branch_record`(645행)뿐이다.
- 결정 필요: **아니오**(사용자 결정 66의 1).

## R20-2. 안전 종료 행의 4.2·6·7.2 판정 키 (질문 T-9)

- **[정의]** R19-1의 "기록으로 내리는 항목"은 P3·G6·READY·DONE·끝 자세에 기대는 **등급 항목**으로 한정한다. 안전 종료(`allowed_stop`) 행에서도 원판 4.2(금지 옵션·env와 기록 확인), 6(실행 정체성 기록), 7.2(K1 작동 분류)는 판정 키로 남는다. 이 키가 어긋나면 원판 그대로 그 행은 무효이거나(4.2) 멈춘다(8.2 S-3·S-5·S-6, 6절 정체성 위반의 S-2 태그·S-4 SCM 정체성·S-12 커밋).
- 근거: 원판 4.2는 "한 번이라도 있으면 그 행은 무효", 6은 "줄·행마다, 판정 전 확인", 7.2는 "줄·행마다, 관문 켬 실행"이라 적어, 행의 등급 분류보다 앞서고 등급 분류와 무관하게 모든 행에 걸린다. 427.9 "판정 분류"(명세 17690~17692행)와 `s9_soil_slope.py` `classify`는 P3 등급의 분류만 바꾸고 실행의 정체성·옵션·K1 분류는 다루지 않는다.
- 결정 필요: **아니오**(사용자 결정 66의 2).

## R20-3. 사실 오류와 9.2 예외의 공개

- **[사실]** rev19 봉인 전 control-expert 보고(초안 `20c68016` 보고)의 "[확인한 사실] `f46b5ab..59c933b`에서 `r67_g1_screen.py`의 바뀐 줄은 모두 기록 전용 함수 안에 있다"는 함수 밖 상수 `RESUME_K1_KEY`와 그 docstring을 놓친 사실 오류다. rev19 본문 R19-7에는 이 문장이 [정의] 조건 (1)으로만 들어갔고, 그 조건은 문장 그대로는 거짓이 된다. 판정서 한계 절에 그대로 적는다: "rev19 R19-7 조건 (1)은 모듈 수준 상수 정의를 빠뜨려 문장 그대로 대조하면 거짓이었다. rev20 R20-1이 그 이름을 읽는 함수가 모두 기록 전용임을 조건으로 고쳤다. 이 개정은 경로 2의 대조 결과를 본 뒤 했다."
- **[사실]** 9.2: 이 판의 정의는 경로 2의 대조 결과와 질문을 본 뒤 정했다. 두 경로는 같은 정의 문장만 받는다. 정의할 곳의 선택은 두 경로에서 독립이 아니다.

## R20-4. 순서·허용 목록·봉인 목록 (rev19 R19-8의 고쳐 씀)

- **[정의]**
  1. 이 판을 봉인한다. 봉인 파일 커밋 S8을 S7 `38897f0` 위에 만든다(부모 = S7 = 봉인 기준 커밋 SEAL_COMMIT = `38897f0d8e216d99253adbc18c71ab1ad027c758`, 브랜치 `z4373-s4`). S8이 바꾸는 것은 이 판의 세 파일과 `.gitattributes`의 `-text` 3줄뿐이다.
  2. 두 도구 브랜치 `z4374-p1chrono`·`z4374-p2chrono`가 각각 S8을 병합한 뒤 R20-1·R20-2를 맞춘다. Chrono 판정 도구의 봉인 목록은 rev16~rev20(두 경로 같게), 하네스 도구(R4)의 봉인 목록은 rev13~rev20이다. `resume4368_judge.py`의 봉인 목록은 R3b에서 고치지 않는다.
  3. `z4373-r3b`는 S8에서 만든다. 나머지 순서(`--no-ff` 병합 순서, 메인 ff-only)는 R19-8 그대로이고 R19-8의 S7은 S8로 읽는다. R3..R3b에는 S4~S8과 두 도구 브랜치의 커밋만 있다.
  - 허용 목록 (가): rev16~rev20의 규칙 파일 각 세 개와 그 `-text` 줄(지운 줄 0). rev20 몫은 `v5_resume_4368_rules_rev20.md`, `v5_resume_4368_rules_rev20.sha256`, `v5_resume_4368_rules_rev20_seal_candidate_draft.md`와 그 `-text` 3줄이다.
- 결정 필요: **아니오**(사용자 결정 66의 4).

## R20-5. 두 경로에 넘기는 문장

- **[정의]** 두 경로 작성자에게 같은 문장을 넘긴다: R20-1·R20-2·R20-4의 [정의] 글머리와 인용한 원 절(원판 4.2·6·7.2·8.2, 명세 427.9 "판정 분류", rev19 R19-1·R19-7). R20-0·R20-3과 다른 경로의 코드·출력은 넘기지 않는다. 지시문에 "이 판의 다른 절은 열지 않는다"를 넣는다.
- 결정 필요: **아니오**(사용자 결정 66의 5).

### 결정 표

| 항목 | 정의 | 결정 필요 |
|---|---|---|
| R20-1 R19-7 (1) | 기록 전용 함수 안이거나, 기록 전용 함수만 읽는 모듈 수준 이름의 정의; 함수 밖 줄·이름·읽는 함수 표; 어기면 S-11 | 결정됨: 사용자 결정 66의 1 |
| R20-2 T-9 | 안전 종료 행에서도 4.2·6·7.2는 판정 키, 기록으로 내리는 것은 P3·G6·READY 의존 등급 항목만 | 결정됨: 사용자 결정 66의 2 |
| R20-3 공개 | R19-7 사실 오류, 9.2 예외 | 결정됨: 사용자 결정 66의 3 |
| R20-4 순서·목록 | S8(부모 S7) → 두 도구 브랜치가 S8 병합 뒤 맞춤 → `z4373-r3b`(S8에서), 허용 (가) rev16~rev20, 봉인 목록 Chrono rev16~20·하네스 rev13~20 | 결정됨: 사용자 결정 66의 4 |
| R20-5 넘길 문장 | 두 경로 같은 [정의] 글머리 | 결정됨: 사용자 결정 66의 5 |

### 결과 본 뒤 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-15 | 66 | 사용자 결정 66(2026-11-15): R19-7 (1)을 모듈 수준 이름까지 고쳐 쓰고, 안전 종료 행의 4.2·6·7.2 판정 키를 정하고, R19-7 사실 오류를 공개하는 rev20을 S7 위 S8로 봉인한 뒤 두 도구 브랜치가 S8을 병합해 맞춘다 | R20-1~R20-5 |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 봉인 전 확인 필요는 없다(S7 해시·rev19 봉인 sha는 4행에 적었다).
2. 파일 이름: `v5_resume_4368_rules_rev20_seal_candidate_draft.md`를 같은 폴더에 `v5_resume_4368_rules_rev20.md`로 복사한다. 초안 파일은 지우지 않는다.
3. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev20 (rev19 정렬 뒤: R19-7 (1) 모듈 수준 이름, 안전 종료 행의 4.2·6·7.2 판정 키, 사실 오류 공개, 결과 본 뒤 개정, 봉인)`
4. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev20.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev20_seal_candidate_draft.md`와 1·3·5·9행만 다르다.`
5. 5행("시점")에서 `SEAL_TIME`과 `SEAL_COMMIT`(S7 `38897f0`)을 값으로 바꾼다. 이 두 이름 말고는 5행을 바꾸지 않는다.
6. 9행("봉인 준비판이다")을 다음으로 바꾼다:
   `- **봉인본이다.** 봉인 전 확인 필요는 없었고(S7 해시·rev19 봉인 sha는 4행), 사용자 결정 66(2026-11-15)은 R20-1~R20-5에 반영했다.`
7. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules_rev20.sha256`에 `<sha256>  v5_resume_4368_rules_rev20.md  sealed <SEAL_TIME 값> (436.8 rev20: after the rev19 tool alignment (path 1 1255d6d, path 2 5dcc8d4) on top of rev19; thresholds, grades and stop meanings unchanged, seen-data list disclosed; seal commit S8 on S7 38897f0; R19-7 condition (1) also allows module-level names (constant and its docstring) read only by the record-only functions, with a table of out-of-function lines, defined names and reading functions, else S-11 (RESUME_K1_KEY read by v5_job_record / v5_branch_record); safe-stop rows keep the rules 4.2 / 6 / 7.2 keys, only P3 / G6 / READY-dependent grade items are recorded; the rev19 R19-7 factual error disclosed; tool branches merge S8 then align, z4373-r3b from S8, allow list (a) rev16..rev20, seal lists Chrono rev16..20 / harness rev13..20; same definition sentences to both paths; user decision 66; 9.2 exception disclosed)` 한 줄로 쓴다.
8. `.gitattributes`에 다음 3줄을 더한다(**`git add`보다 먼저**, 지우는 줄 없음):
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev20.md -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev20.sha256 -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev20_seal_candidate_draft.md -text`
9. 확인: `tools/verif/seal_check.py`와 `tools/verif/placeholder_scan.py`를 돌리고, 봉인본 5행에 `SEAL_TIME`·`SEAL_COMMIT`이 남지 않았는지 Grep으로 따로 본다.
10. `git add`(세 파일과 `.gitattributes`)와 봉인 파일 커밋 S8을 S7 위에 만든다(브랜치 `z4373-s4`). 메인 checkout의 HEAD는 바꾸지 않는다. 봉인 뒤 이 문서를 고치지 않는다.
