# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev18 (R3 Chrono 판정 뒤: Chrono 도구 보완 커밋 R3b, 경로 1 묶음 등급 집계, 경로 2 C-2 보완, C-8a L-5 문구, 결과 본 뒤 개정, 봉인 후보 초안)

- **상태: 봉인 후보 초안(봉인 전).** 봉인 전에는 실행·판정에 쓰지 않는다. 봉인 때 바꿀 머리 줄은 끝 절에 원문으로 적었다.
- 원판~rev16은 고치지 않는다. 이 판은 rev17(sha256 `9400660e2f228c3bdfaf26b1eb36cf08a753e7ebc49fbcdedc4a8ab4e0b92422`, 봉인 2026-11-15 10:51:35 +09:00, 봉인 기준 커밋 S4 `98ea664`, 봉인 파일 커밋 S5 `de195938ce9ae0da90769ac475298f5e74314bf7`, 브랜치 `z4373-s4`) 위에 쌓인다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 앞 판 그대로다. 용어(봉인 기준 커밋, 봉인 파일 커밋)는 rev16 4행과 같다.
- **시점: R3 `576eb87` 도구로 낸 C-1~C-8 두 경로 Chrono 판정 출력(`judge_576eb87/`)을 본 뒤, 메인 checkout은 R3(봉인 SEAL_TIME, 봉인 기준 커밋 SEAL_COMMIT).** 이 판은 결과를 본 뒤의 개정이다. 본 자료는 R18-0에 적었다.
- 작성: control-expert, 2026-11-15. 기준: R2 `b9f5707`(실행), R3 `576eb87`(판정 도구), S4 `98ea664`, S5 `de19593`(rev17).
  - 계기: R3 Chrono 판정에서 경로 1 도구가 C-1·C-2·C-5의 묶음 등급을 내지 않았고, 경로 2는 C-2에서 PS-c E 항목이 없고 S-01·02 안전 종료 분기를 쓰지 않았다. C-8a는 원판 7.4 S-9로 멈췄다.
  - 사용자 결정 60·61(2026-11-15)과 봉인 전 감사(대상 초안 `388b9e8b`, 차단 2·권고 6·확인 필요 2)를 R18-1~R18-7에 반영했다.
- **봉인 준비판이다.** 봉인 전에 답이 필요한 항목은 없다(확인 필요 0). 이 줄은 봉인 때 바뀐다.
- **바꾸지 않는 것**: 숫자 문턱, 등급과 우선순위(원판 8.1), 멈춤 조건의 뜻(원판 8.2), 묶음 범위와 행 목록, 사전 예측, 두 경로 요건, 실행 커밋 R2, 이미 돈 실행의 argv·코드, rev16·rev17의 다른 조항. 이 판이 더하는 것은 판정 도구 보완 커밋 R3b와 그 허용 목록, 경로 1 집계의 정의, 경로 2 보완의 정의, 재판정 순서, C-8a의 L-5 문구다.

## R18-0. 결과 본 뒤 개정의 공개 (본 자료 목록)

- 이 작성자(control-expert, 도메인 검토)가 본 것(읽기 전용, 2026-11-15): `judge_576eb87/chrono_path1/`의 `judge_C*.json`(행별 `grade`·`grade_note`·재계산 항목), `oc5_C-8a.json`·`oc5_C-8b.json`, `run_path1.ps1`; `judge_576eb87/chrono_path2c/p2_C1~C8.json`(묶음·행 상태, C-4·C-8 항목), `chrono_path2/p2h_oc5k_C-8a.json`·`p2h_openloop.json`; C-2 S-01·02 행 `result.json`(`controller_meta.lift_stroke_guard`, `p3b`, `p3b_ext`); 규칙 원판 5.2·7.4, rev6 R6-B8, `d1_selection_rules.md` 6·11절, 명세 427.9.
- 이 작성자가 확인한 사실: 경로 1 R3 도구는 등급을 G6 행(S-03·04)에만 붙이고 그 밖은 "D8 row grade is the bundle judge's"로 비워 둔다. 경로 2는 C-1 통과·C-3 통과·C-5 통과·C-2 판정 불가·C-4 기록 불완전·C-6·C-7 기록 완료·C-8 S-9를 냈다. C-2 S-01·02는 SGS 정지(RL, 52.9 / 52.0 s, `FAULT_STROKE_END` 0, 이탈 뒤 최소 71.2~71.6 kN)다. C-8a·C-4의 RL 값은 R18-5·아래 표다.
- 메인 세션 전달: 사용자 결정 60, 메인 checkout이 R3에 있다는 사실.
- 판정서에는 이 목록을 그대로 싣는다. 이 판의 정의는 위 값을 본 뒤 정했으므로 "결과 본 뒤 정한 정의"로 적는다.

## R18-1. Chrono 도구 보완 커밋 R3b (사용자 결정 60의 2)

- **[정의] 순서**(방법 1: 봉인 먼저)
  1. 이 판을 봉인한다. 봉인 파일 커밋 S6을 S5 `de19593` 위에 만든다(부모 = S5 = 봉인 기준 커밋 SEAL_COMMIT = `de195938ce9ae0da90769ac475298f5e74314bf7`). S6이 바꾸는 것은 이 판의 세 파일과 `.gitattributes`의 `-text` 3줄뿐이다.
  2. 도구 브랜치 둘을 S6에서 가른다: 경로 1 `z4374-p1chrono`(python-expert), 경로 2 `z4374-p2chrono`(원 경로 2 작성자). 각 브랜치는 R18-2·R18-3만 구현하고, Chrono 판정 도구의 봉인 목록에 rev16~rev18을 넣는다(두 경로 같게). 여기서 "Chrono 판정 도구"는 경로 1 `chrono_rows_judge_4368.py`·`chrono_bundle_grade_4368.py`와 경로 2 `path2_chrono/`의 봉인 목록이고, `resume4368_judge.py`는 들어가지 않는다. **R3b에서 `resume4368_judge.py`의 봉인 목록은 고치지 않는다. 봉인 목록 갱신은 R4 하네스 도구 몫(rev13~18)이다.** 하네스 도구(R4)의 봉인 목록에는 rev13~rev18을 넣는다(rev16 R16-13, rev17 R17-3 3을 이어 씀). 목록에 넣지 않는 도구의 rev18 확인은 `tools/verif/seal_check.py`로 한다.
  3. 메인 세션이 S6에서 통합 브랜치 `z4373-r3b`를 만들고 `z4374-p1chrono` → `z4374-p2chrono`를 `--no-ff`로 병합한다. 마지막 병합 커밋이 **R3b**다. 충돌을 손으로 풀었으면 판정 전 감사가 본다.
  4. 메인 checkout을 `git merge --ff-only z4373-r3b`로 R3에서 R3b로 맞춘다. R3..R3b에는 S4·S5·S6과 두 도구 브랜치의 커밋만 있다.
- **[정의] R3b 조건**(모두 참이어야 R3b로 판정한다. 거짓이면 판정하지 않고 멈춘다, 원판 8.2 S-11)
  - `git diff --name-only 576eb87..R3b -- 03_src 02_params`가 비어 있다.
  - `git diff --name-only 576eb87..R3b -- 04_scripts`가 정확히 다음 안이다: `04_scripts/02_chrono/chrono_rows_judge_4368.py`, `04_scripts/02_chrono/chrono_rows_judge_4368_README.md`, 새 파일 `04_scripts/02_chrono/chrono_bundle_grade_4368.py`(경로 1 묶음 등급 집계). 러너·실행 경로(`run_S9.py`·`run_S8C.py`·`run_S6C.py`·`s9_batch.py`, `04_scripts/03_control/`·`04_scripts/01_dynamics/` 전부, `04_scripts/04_hydraulic/` 전부, `v5_resume_4368_chrono_rows.py`)와 manifest(`chrono_rows_manifest.json`, LF blob `f00cd5d8…`)는 diff 0이다.
  - `git diff --name-only 576eb87..R3b`의 모든 파일이 다음 허용 목록 안이다.
    - (가) rev16·rev17·rev18의 규칙 파일 각 세 개와 그 `.gitattributes` `-text` 줄(지운 줄 0)
    - (나) 경로 1: 위 `04_scripts/02_chrono/` 세 파일, `05_tests/unit/test_chrono_rows_judge_4368.py`, 새 파일 `05_tests/unit/test_chrono_bundle_grade_4368.py`, `06_analysis/02_control/verif_matrix/scripts/resume4368_judge.py`(조건: `git diff R3..R3b`의 바뀐 덩어리가 `oc5`·`fmin-time` 하위 명령과 그 전용 함수 안에만 있음을 함수 단위로 보인다. 공용 함수가 바뀌면 그 함수를 부르는 하위 명령을 모두 나열하고, 그 하위 명령들의 R3·R3b 출력이 같은 입력에서 바이트가 같음을 보인다. 판정 전 감사가 이 표를 본다. 그래도 R3·R3b 출력의 바이트가 다르면 R3b 판 `k1-class`·`record-check`를 같은 view로 다시 돌린다. 이때 `rules_seal` 블록을 뺀 분류·문제 목록은 K-10으로 같아야 한다(다르면 S-13)), `05_tests/unit/test_resume4368*.py`
    - (다) 경로 2: `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/` 아래 파일(새 파일 포함), `path2/p2_4368.py`(Chrono 하위 명령 부분)·`path2/test_p2_4368.py`·`path2/README.md`
    - (라) rev8 R8-4의 판정서·감사 기록, `00_docs/decision_log.md`·`00_docs/00_roadmap.md`·`00_docs/handoff/session_handoff.md`
  - R3b blob 표: (나)·(다) 파일의 `git show R3b:<파일>` LF 바이트 sha256 표를 판정서 부록에 싣고, 판정 전 감사가 감사한 브랜치 끝 blob과 대조한다.
- **[정의] rev16 R16-12의 고쳐 씀**
  - 순서 2·3·4: 하네스 도구 브랜치 `z4373-p1harness`·`z4373-p2harness`와 R4 통합 브랜치 `z4373-r4`는 **R3b**에서 가른다(R3b는 S6을 포함한다). 이유: R3b와 R4가 `resume4368_judge.py`·`path2/p2_4368.py`를 함께 고치므로, R3b 위에서 가르지 않으면 병합 충돌이 난다(rev16 봉인 전 감사 차단 1과 같은 이유).
  - 순서 6: 새 실행 뒤 메인을 R3로 맞추는 것과 R3 Chrono 판정은 끝났다. 그다음 R3b로 맞추고 R18-4의 재판정을 R3b 도구로 끝낸 뒤에 R4로 간다.
  - 순서 8: "R4 뒤 Chrono 판정은 하지 않는다"는 그대로다. Chrono 판정 출력은 R18-4의 대체 규칙대로 R3 또는 R3b 출력만 쓴다.
  - R4 조건의 기준점: rev16 R16-12 R4 조건의 "Chrono 판정 도구(`chrono_rows_judge_4368.py`·README·`v5_resume_4368_chrono_rows.py`·manifest·`path2_chrono/` 전부) R3..R4 diff 0"과 허용 목록 판단 전체는 **R3b..R4**로 읽는다. `b9f5707..R4`의 `03_src`·`02_params` 조건은 그대로다. `b9f5707..R4 -- 04_scripts`의 목록에는 R3b 몫(`chrono_rows_judge_4368.py`·그 README·`chrono_bundle_grade_4368.py`)을 넣어 읽는다.
- 결정 필요: **아니오**(사용자 결정 60의 2).

## R18-2. 경로 1 묶음 등급 집계 (사용자 결정 60의 2)

- **[정의] 행 등급**
  - L2b·L1-R 행: 러너 판정기 `verify_S8C`(L2b)·`verify_S6C`(L1-R)의 행 판정(`judged`·`fails`)
  - SCM 행: 그 행 `result.json`의 `p3b` 판정 블록(P3-1~P3-9, `P3-3_within`, 정착·`stroke_limited_stop` 분류)
  - 그 위에 R3 `judge_C*.json`의 재계산 항목(D-26~D-39)을 같은 이름 항목에 덮어쓴다. 덮어쓴 항목과 앞뒤 값을 행마다 남긴다.
  - S-01~04: rev6 R6-B8(D-26)대로 427.9 안전 종료 조건 1~5가 모두 참이면 `allowed_stop`이다. 그때 P3-5·P3-6·FAULT0은 이 조건으로 대신한다. 하나라도 거짓이면 `fail`이다. 다섯 조건은 명세 `s6_control_spec.md` 17691행 원문("정지 사유가 `FAULT_LIFT_STROKE_LIMIT:soil`, `FAULT_STROKE_END` 0, 다리 부상 0, 크롤러 이탈 뒤 실행 끝까지 네 다리 실제 최소 ≥ F_min, 이동 중 압력 ≤ 180 bar(포화 0)")과 같다(분류 문단 17690~17692행).
    - 출처: 180 bar는 명세 320행과 `d1_selection_rules.md` 166행, 다리 부상의 정의는 rev6 R6-B9(Q-14)이다.
  - **행 수 검사**: 집계 도구는 대상 행을 manifest(`chrono_rows_manifest.json`)와 각 배치 `batch.json` `cases[]`에서 열거하고 묶음별 기대 수와 대조한다: C-1 10, C-2 6, C-3 2, C-5 35, C-6·C-7 3, C-8 2. 다르면 S-15다. 행이 0개인 묶음에는 등급을 내지 않는다.
  - **결측**: 행 등급 입력(러너 판정기 출력, `p3b` 블록, 해당 재계산 항목) 가운데 하나라도 없으면 그 행은 `판정 불가`다(원판 9.3). C-2 PS-c 행의 E-1~E-7도 항목이 하나라도 없으면 그 행은 `판정 불가`다.
- **[정의] 묶음 규칙**: C-1·C-2는 `d1_selection_rules.md` 11절(+ rev1), C-3는 같은 절(G6 행), C-5는 v5 기준 개정 12·12a·12b(T4·T5·J11·J-P3·D2와 P3 항목). 묶음 등급은 원판 8.1 순서(`판정 불가` > `미달` > `통과`)다.
- **[정의] 기록 묶음의 값**: C-6·C-7은 `result.json` `p3a`(P3a-1~5와 명세 11047 FLAG)를 읽는다. C-8은 `resume4368_judge.py fmin-time`으로 F<F_min·F<F_min+2 kN 시간을 `step_series.npz` 1 ms에서 낸다(rev1 RV1-7).
- **[정의] 도구 위치와 판(版)**
  - 집계는 새 파일 `chrono_bundle_grade_4368.py`(R3b)가 한다.
  - 러너 판정기 `verify_S8C`·`verify_S6C`의 행 판정, `p3a` 읽기, 입력 view(R18-2a)는 R3와 R3b에서 blob이 같은 도구다. 이 도구들은 R3에서 돌려도 되고, 판정서에 R3·R3b blob이 같음을 보인다(rev15 R15-2 꼴).
  - `fmin-time`은 R3b에서 고칠 수 있으므로 **R3b 판의 출력만** 쓴다. R3 판 `fmin-time` 출력은 쓰지 않는다.
  - 경로 1 `chrono_rows_judge_4368.py judge`(C-1~C-8)는 R3b 한 판으로 다시 돌리고, R3 출력과 K-10 꼴(등급·참거짓·목록·개수·분류 완전 일치, 수치 상대 1e-9)로 같은지 기록한다. 다른 곳은 판정서에 표로 싣고 python-expert에 원인 확인을 넘긴다. 판정에는 R3b 출력을 쓴다.
  - 출력은 `judge_576eb87/chrono_path1/`에 새 이름으로 두고, 기존 R3 출력은 지우지 않는다.
- **[정의] R18-2a. 경로 1 7.2·4.2의 L2b·L1-R 행 입력 view**(사용자 결정 59·61의 방식, 결과 본 뒤 정한 입력 배열과 읽기)
  - R3 도구 `resume4368_judge.py k1-class`·`record-check`는 그대로 둔다.
  - 원 `batch.json`과 러너 폴더(`07_results/S8/…`)의 `result.json`을 `<batch>/<case>/` 꼴로 복사한 view를 만든다. 위치는 `judge_576eb87\chrono_path1\chrono_view\`, 만드는 도구는 `make_view.py`(파일 sha256 `adb01782…`, git 추적 밖, 판정서 커밋 때 함께 고정)다.
  - 대응표는 `view_map.json`(sha256 `1b2c500f…`)이다. 41개 항목, 36행 `case_log`, 복사 전후 sha256이 모두 같다.
  - [사실] 41개 항목의 내역: `batch.json` 3개와 `result.json` 38개(L2b 32 + L1-R 4 + SCM 2)다. 행 counts 밖의 3개는 열린 루프 행이 아니라 `batch.json`이다.
  - 대응표가 경로 2 행 폴더(`p2_C*.json` `rows[].folder_method`·`folder`)와 맞지 않는 행은 S-11이다.
  - 결과는 `k1_classification_7_2_view.json`(sha256 `3d174e10…`), `record_check_chrono_view.json`(sha256 `058993f3…`)이다. S-5·S-6은 0이고, 도구가 낸 문제는 열린 루프 3행뿐이다.
  - 열린 루프 C-6·C-7 3행은 7.2·4.2에서 "해당 없음(원판 5.3)"으로 읽는다. 확인 근거는 `controller_options.applied` = false(C-7b는 블록이 없다, rev15 R15-4 1)다. 도구가 낸 3행 문제는 기록으로만 둔다.
  - R3b에서: `k1-class`·`record-check`가 지나는 코드는 R18-1 (나)의 조건으로 R3와 같아야 하므로 다시 돌리지 않는다. 그 조건의 바이트 동일 확인에 이 둘을 넣는다. view는 `make_view.py` 파일 sha256과 입력 파일 sha256이 같으면 그대로 쓴다. `k1_classification_7_2_view.json`·`record_check_chrono_view.json`에는 `rules_seal` 블록이 있어 봉인 목록이 바뀌면 바이트가 달라진다. 그래서 R3b에서는 `resume4368_judge.py`의 봉인 목록을 고치지 않고(R18-1 2), 바이트가 달라지면 R18-1 (나)의 재실행·K-10 규칙을 따른다. 다르면 같은 방식으로 다시 만들고 대응표를 새로 낸다.
  - 판정서 공개 문구: "결과 본 뒤 정한 입력 배열과 읽기".
- 결정 필요: **아니오**.

## R18-3. 경로 2 보완 (사용자 결정 60의 2)

- **[정의] 보완 항목**
  1. C-2 PS-c 2행의 E-1~E-7: E-1~E-6은 실행 기록에서 원 정의대로 재계산하고(rev4 R4-A2 안 b), E-7은 원 규칙이 지정한 기존 판정 도구를 경로 2가 직접 실행해 그 항목 결과를 재집계한다(rev4 R4-A2 안 c, 한계 공개 문장 그대로).
  2. S-01~04의 427.9 안전 종료 분기: R18-2 "S-01~04" 글머리의 조건 1~5를 따로 계산해 `allowed_stop` / `fail`을 낸다(rev6 R6-B8, D-26).
- **[정의] 작성자와 넘길 문장**: 원 경로 2 작성자가 고친다. 경로 1의 코드·출력은 주지 않는다. 넘기는 문장은 다음뿐이다: 이 판 R18-1의 R3b 조건 (다)와 순서, R18-2의 "S-01~04" 글머리, R18-3의 이 두 [정의] 글머리, R18-4, rev4 R4-A2(안 b·안 c와 한계 공개 문장), rev6 R6-B8, `d1_selection_rules.md` 11절의 S-01·02 행, 명세 427.9의 "판정 분류" 문단. 경로 2 지시문에는 "이 판의 다른 절은 열지 않는다"를 넣고, 경로 2 판정서의 읽은 것 목록으로 확인한다.
- **[사실] 9.2 예외 공개**: 원판 9.2는 "상대 출력을 본 뒤에는 어느 경로도 고치지 않는다"이다. 이번 보완은 두 경로 출력과 도메인 검토(경로 2의 E 항목 미구현, S-01·02 안전 종료 분기 누락, 경로 1의 등급 미집계)를 본 뒤 정했다. 판정서 한계 절에 그대로 적는다: "R3b 두 경로 보완 항목은 메인 세션과 도메인 검토가 R3 두 경로 출력을 본 뒤 정했다. 보완의 구현과 재판정 값은 경로마다 따로 만들었다. 보완 항목의 선택은 두 경로 출력에서 독립이 아니다." 경로 2 작성자에게 넘기는 보완 항목 목록으로 결함 사실이 전달되는 것은 이 공개로 충분하다(사용자 결정 61, rev16 R16-10 3 선례).
- 결정 필요: **아니오**(사용자 결정 60의 2).

## R18-4. 재판정 범위와 출력의 대체

- **[정의] 범위**
  - 경로 1: C-1·C-2·C-3·C-5의 묶음 등급 집계(R18-2), C-6·C-7 `p3a` 기록, C-8 `fmin-time`.
  - 경로 2: C-2 전부. `path2_chrono/`의 공용 파일이 바뀌면 C-1·C-3~C-8도 R3b 도구로 다시 돌리고, R3 출력과 등급·목록·수치가 같은지(원판 9.2 K-10) 본다. 다르면 기록하고 그 묶음은 판정 전에 멈추고 묻는다.
  - 모든 판정 도구의 `--git-at-start`는 R2다.
- **[정의] 대체**: R3b 출력이 있는 묶음·항목은 R3b 출력을 쓴다. R3 출력은 기록으로 둔다(S-13 경과처럼 판정서에 싣되 등급의 근거로 쓰지 않는다). R3b 재판정에서 두 경로 등급이 갈리면 원판 S-13 그대로 멈추고 묻는다.
- **[정의] C-2 S-01·02의 남은 두 값**: 다리 부상 0과 이동 중 압력 ≤ 180 bar는 두 경로가 값으로 내고, 판정서에 행마다 적는다.
- 결정 필요: **아니오**.

## R18-5. C-8a S-9의 처리와 L-5 문구 (사용자 결정 60의 1)

- **[정의]** C-8a(O-C5 VB, Kc3) S-9는 (A)로 처리한다: L-5 알려진 한계로 공개하고, 원인 진단은 436.9로 넘긴다. C-8은 기록 묶음이라 등급은 바뀌지 않는다(원판 7.4·8.1).
- **[정의] L-5 문구**(판정서에 그대로): "운용 시작 조건 안(R_c 0.952, 바닥 2.1434°·1.3784°)의 혼합 지형(강체 + J1@FR, VB, 크롤러 강성 ×3)에서, 크롤러 이탈 직후 35.286 s에 RL 실제 실린더 힘이 최소 5,869.6 N(F_min 9,414.6 N 대비 −3,545 N)까지 내려갔다. F<F_min 시간은 0.158 s, F<F_min + 2 kN 시간은 0.212 s다. 다리는 접지를 유지했다. 사전 예측 P-13(RL 최소가 P5r4 A3의 8.64 kN보다 높다)은 빗나갔다. 바닥을 줄였는데 최소가 낮아진 비단조라 시점 민감성이 의심된다. 같은 지형의 C-4 4행(R_c > 1)도 RL 이탈 직후 하강(4.20~10.81 kN)을 보였다. 원인 진단(1 ms 다리별 하중, LAS-b 끝 시각과의 관계, 크롤러 강성 의존)은 436.9에서 한다. 짝 C-8b(V0, 크롤러 강성 ×1)의 RL 최소는 11,951.2 N(F_min + 2.54 kN)이다."
- **[정의] 시간 값의 확정**: 문구의 F<F_min 0.158 s와 F<F_min + 2 kN 0.212 s는 경로 2 값이다. 경로 1 `fmin-time`(R3b 판, R18-2)과 K-10으로 대조한 뒤 확정한다. 값이 다르면 원판 9.2대로 기록하고, 문구에는 대조한 값을 적거나(수치만 허용 밖이면) 멈추고 묻는다(분류가 다르면).
- **[참고] 근거 출력과 키**
  - m·다리·시각: 경로 1 `judge_576eb87\chrono_path1\oc5_C-8a.json` `values.F_min_after_N`(RL = 5,869.61684783503 N)·`values.t_min_after_s`, `m_N`·`min_leg`·`margin_N`; 경로 2 `chrono_path2c\p2_C8.json` `rows[case = OC5_mixed_rigid_J1FR_Kc3_VB_top].items.m_7_4.per_leg.min_N`
  - 시간: 경로 2 같은 행 `items.Fmin_time_full.t_below_Fmin_s`·`t_below_Fmin_plus2k_s`(RL 0.158 / 0.212 s)
  - "접지 유지": 위 `F_min_after_N`의 네 다리 값이 모두 양수(최소 RL 5,869.6 N)이고, 같은 행 `result.json` `p3b`의 부상·재접촉 기록이 0이다(판정서에서 키와 함께 다시 적는다).
  - C-4 범위 4.20~10.81 kN: 경로 2 `p2_C4.json` `rows[].items.P3-3.min_N`(RL), 경로 1은 각 행 `result.json` `p3b.P3-3_leg_force.F_min_after_N`(RL)
  - R_c 0.952: 두 경로 `R_c_operating`·`items.R_c.R_c`(0.9523695802182304)
- 결정 필요: **아니오**(사용자 결정 60의 1).

## R18-6. C-4 기록 (참고)

- **[참고]** C-4 4행(R_c 1.076 / 1.035, 운용 시작 조건 밖)의 RL 최소: Kc1 lason 10.81, Kc1 lasoff 7.65, Kc3 lason 8.64, Kc3 lasoff 4.20 kN. 원판 7.4대로 L-5 알려진 한계이고 등급 밖이다. 사전 예측 P-9(켬 팔 10.81 / 8.64 kN, 켬 ≥ 끔)와 맞다. P3-5 판정 불가(READY 뒤 rut 표본 없음)는 기록 불완전 사유로 적는다.

## R18-7. 결정 표

| 항목 | 정의·권고 | 결정 필요 |
|---|---|---|
| R18-0 사후 개정 공개 | 본 자료 목록, 결과 본 뒤 정한 정의 | 아니오 |
| R18-1 R3b | S6(부모 S5) → `z4374-p1chrono`·`z4374-p2chrono`(S6에서) → `z4373-r3b`(`--no-ff`) → 메인 ff-only; `03_src`·`02_params`·러너·manifest diff 0, 허용 목록 (가)~(라), `resume4368_judge.py` 함수 단위 diff·바이트 동일; 하네스 도구 브랜치와 `z4373-r4`는 R3b에서; R4 조건의 Chrono 도구·허용 목록 기준점은 R3b..R4; 봉인 목록 Chrono rev16~18, 하네스 rev13~18 | 결정됨: 사용자 결정 60의 2 |
| R18-2 경로 1 집계 | 러너 판정기·`p3b` 행 등급 + 재계산 항목 덮어씀, S-01~04 D-26(명세 17691행 원문), 행 수 검사(S-15)·결측(판정 불가), 묶음 규칙, C-6·C-7 `p3a`, C-8 `fmin-time`(R3b 판만), `judge` C-1~C-8 R3b 재실행·R3 대조, 그대로 쓰는 도구는 blob 같음 공개 | 아니오(감사 권고 반영) |
| R18-2a 입력 view | L2b·L1-R 36행 7.2·4.2 view(`make_view.py` `adb01782…`, `view_map.json` `1b2c500f…`), 경로 2 폴더와 어긋나면 S-11, 열린 루프 3행 해당 없음, R3b에서는 blob·입력 같으면 재사용 | 결정됨: 사용자 결정 59·61 |
| R18-3 경로 2 보완 | C-2 PS-c E-1~E-7(R4-A2 안 b·c), S-01~04 안전 종료 분기, 원 작성자·넘길 문장 목록, 9.2 예외 공개(결함 사실 전달은 공개로 충분) | 결정됨: 사용자 결정 60의 2, 61 |
| R18-4 재판정·대체 | 범위, R3b 출력 우선·R3 출력 기록, 갈리면 S-13, S-01·02 남은 두 값 | 아니오 |
| R18-5 C-8a | (A) L-5 공개 + 436.9 진단, 문구 확정 | 결정됨: 사용자 결정 60의 1 |
| 머리·봉인 절 | S5 = `de195938ce9ae0da90769ac475298f5e74314bf7`(`z4373-s4`, 부모 S4 `98ea664`) = SEAL_COMMIT, rev17 봉인 sha256 `9400660e…92422`(2026-11-15 10:51:35 +09:00)를 4행에 적음. 하네스 도구 브랜치를 R3b에서 가르는 것은 메인 세션 동의(충돌 회피, rev16 감사 차단 1과 같은 이유) | 아니오(메인 세션 확인) |

### 결과 본 뒤 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-15 | 61 | 사용자 결정 61(2026-11-15, rev18 봉인 전 감사의 확인 필요 2건): ① 경로 2에 넘기는 보완 항목 목록으로 결함 사실이 전달되는 것은 공개로 충분하다(rev16 R16-10 3 선례), R18-3 공개 문장 그대로. ② 경로 1 7.2·4.2의 L2b·L1-R 행은 입력 view 방식(사용자 결정 59) | R18-2a, R18-3 |
| 2026-11-15 | 60 | 사용자 결정 60(2026-11-15): ① C-8a S-9는 (A) L-5 알려진 한계로 공개, 원인 진단은 436.9, 등급 불변. ② C-2는 rev18 + R3b 도구 보완으로, R4 병합 전에 Chrono 판정 도구를 보완하고 C-2(필요하면 다른 묶음)를 다시 판정 | R18-1~R18-5 |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 봉인 전 확인 필요는 없다(S5 해시·rev17 봉인 sha는 4행과 R18-7 표에 적었다).
2. 파일 이름: `v5_resume_4368_rules_rev18_seal_candidate_draft.md`를 같은 폴더에 `v5_resume_4368_rules_rev18.md`로 복사한다. 초안 파일은 지우지 않는다.
3. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev18 (R3 Chrono 판정 뒤: Chrono 도구 보완 커밋 R3b, 경로 1 묶음 등급 집계, 경로 2 C-2 보완, C-8a L-5 문구, 결과 본 뒤 개정, 봉인)`
4. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev18.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev18_seal_candidate_draft.md`와 1·3·5·9행만 다르다.`
5. 5행("시점")에서 `SEAL_TIME`과 `SEAL_COMMIT`(S5 `de19593`)을 값으로 바꾼다. 이 두 이름 말고는 5행을 바꾸지 않는다.
6. 9행("봉인 준비판이다")을 다음으로 바꾼다:
   `- **봉인본이다.** 봉인 전 확인 필요는 없었고(S5 해시·rev17 봉인 sha는 4행, 하네스 도구 브랜치는 R3b에서), 사용자 결정 60·61(2026-11-15)과 봉인 전 감사(대상 초안 `388b9e8b`)의 차단·권고는 R18-1~R18-7에 반영했다.`
7. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules_rev18.sha256`에 `<sha256>  v5_resume_4368_rules_rev18.md  sealed <SEAL_TIME 값> (436.8 rev18: after the R3 576eb87 Chrono judgement on top of rev17; thresholds, grades and stop meanings unchanged, seen-data list disclosed; seal commit S6 on S5 de19593; Chrono tool fix commit R3b = z4373-r3b (--no-ff merges of z4374-p1chrono and z4374-p2chrono cut from S6), main fast-forwarded R3 -> R3b, 03_src / 02_params / runners / manifest diff 0, 04_scripts only chrono_rows_judge_4368.py, its README and the new chrono_bundle_grade_4368.py, resume4368_judge.py oc5 / fmin-time only, path2_chrono and the path2 p2_4368.py Chrono part, R3b blob table; harness tool branches and z4373-r4 cut from R3b (rewrites rev16 R16-12 2-4, 6, 8); path 1 bundle grades = runner verify_S8C / verify_S6C and p3b row grades with the R3 recomputed items, S-01..04 D-26 safe stop, d1_selection_rules 11 and criteria revision 12 / 12a / 12b, C-6 / C-7 p3a, C-8 fmin-time, R3 tools used where they suffice; path 2 by its original author: C-2 PS-c E-1..E-7 (R4-A2 b / c) and the S-01..04 427.9 safe-stop branch, sentence list given, 9.2 exception disclosed; R3b outputs replace R3 outputs for the re-judged items, split grades stop as S-13; C-2 S-01 / S-02 leg lift and moving pressure values in the judgement; C-8a S-9 handled as L-5 with the fixed sentence (RL 5,869.6 N at 35.286 s, F<F_min 0.158 s, F<F_min+2 kN 0.212 s, R_c 0.952, P-13 missed), cause to 436.9 (user decision 60); R4 conditions on the Chrono tools and the allow list read as R3b..R4; path 1 7.2 / 4.2 of the 36 L2b / L1-R rows by the input view (make_view.py adb01782, view_map.json 1b2c500f, S-11 on a folder mismatch with path 2, open-loop rows not applicable, user decisions 59 / 61); row count check (S-15), missing inputs = not judgeable; fmin-time from the R3b version only; path 1 judge C-1..C-8 re-run at R3b and compared with R3; resume4368_judge.py diff by function with byte identity of the other subcommands; seal lists Chrono rev16..18, harness rev13..18; 427.9 conditions quoted from spec line 17691)` 한 줄로 쓴다.
8. `.gitattributes`에 다음 3줄을 더한다(**`git add`보다 먼저**, 지우는 줄 없음):
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev18.md -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev18.sha256 -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev18_seal_candidate_draft.md -text`
9. 확인: `tools/verif/seal_check.py`와 `tools/verif/placeholder_scan.py`를 돌리고, 봉인본 5행에 `SEAL_TIME`·`SEAL_COMMIT`이 남지 않았는지 Grep으로 따로 본다.
10. `git add`(세 파일과 `.gitattributes`)와 봉인 파일 커밋 S6을 S5 위에 만든다. 메인 checkout의 HEAD는 바꾸지 않는다(R3 그대로, R18-1 순서 4에서 R3b로 맞춘다). 봉인 뒤 이 문서를 고치지 않는다.
