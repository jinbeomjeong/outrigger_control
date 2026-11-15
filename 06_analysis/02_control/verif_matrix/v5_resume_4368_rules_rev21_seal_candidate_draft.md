# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev21 (R3b 경로 1 재판정 멈춤 뒤: D-29 t_lift를 t_lift,sus로 교체, R19-5 비교 기준, 도구 보완 커밋 R3c, 재판정 범위, 결과 본 뒤 개정, 봉인 후보 초안)

- **상태: 봉인 후보 초안(봉인 전).** 봉인 전에는 실행·판정에 쓰지 않는다. 봉인 때 바꿀 머리 줄은 끝 절에 원문으로 적었다.
- 원판~rev19는 고치지 않는다. 이 판은 rev20(sha256 `615a8fbd82f4ef93f1ca76b3fb4d5c24a2e602e63a997c7c56119fcc73fb5531`, 봉인 2026-11-15 15:54:50 +09:00, 봉인 기준 커밋 S7 `38897f0d8e216d99253adbc18c71ab1ad027c758`, 봉인 파일 커밋 S8 `4d8a95d086ab196b268a9a494098b8458386e1a9`, 브랜치 `z4373-s4`) 위에 쌓인다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 앞 판 그대로다. 용어(봉인 기준 커밋, 봉인 파일 커밋)는 rev16 4행과 같다.
- **시점: R3b `062e051` 경로 1 재판정이 C-1 L2b 6행에서 R19-5로 멈추고 dynamics-expert 진단(`tlift_diag.json`·`tlift_c2c5.json`)을 본 뒤, 경로 2 R3b 판정은 진행 중, 메인 checkout은 R3b(봉인 SEAL_TIME, 봉인 기준 커밋 SEAL_COMMIT).** 이 판은 결과를 본 뒤의 개정이다. 본 자료는 R21-0에 적었다.
- 작성: control-expert, 2026-11-15. 기준: R2 `b9f5707`(실행), R3 `576eb87`, R3b `062e051`(판정 도구, master), S8 `4d8a95d`(rev20).
  - 계기: rev6 D-29의 "첫 ≤ 0 1 ms 표본"이 L2b `pads.npz` `crawler_normal_N`(NSC 스텝 끝 접촉력)에서 LEVEL 첫 표본으로 퇴화했다. 그래서 R19-5가 1 ms 행에서 늘 멈춘다.
  - 사용자 결정 68·69(2026-11-15)를 R21-1~R21-6에 반영했다. 결정 69는 V0 L2b 행의 R15-3 유지(10 Hz t_lift,sus 대응값 기록, 정의 차이 공개)와 새 도구 브랜치 `z4375-p1chrono`·`z4375-p2chrono`(R3b에서)·통합 `z4373-r3c`다.
- **봉인 준비판이다.** 봉인 전에 답이 필요한 항목은 없다(확인 필요 0). 이 줄은 봉인 때 바뀐다.
- **바꾸지 않는 것**: 숫자 문턱(R19-5의 0.1 s + 10⁻⁹ s 포함), 등급과 우선순위(원판 8.1), 멈춤 조건의 뜻(원판 8.2), 묶음 범위와 행 목록, 사전 예측, 두 경로 요건, 실행 커밋 R2, 이미 돈 실행의 argv·코드, 러너 값을 쓰는 R19-5 네 항목, rev16~rev20의 다른 조항.

## R21-0. 결과 본 뒤 개정의 공개 (본 자료 목록)

- 이 작성자(control-expert)가 본 것(읽기 전용, 2026-11-15): 메인 세션이 전한 R3b 경로 1 멈춤 사실(C-1 L2b 6행, 러너 t_lift가 D-29 t_lift보다 0.4~0.5 s 늦음), dynamics-expert 진단 `…\scratchpad\dyn-run\tlift\tlift_diag.json`·`tlift_c2c5.json`(행별 `t_D29`·`t_runner`·`t_lift_sus`·LEVEL 시각·LEVEL 전 1 s의 0 비율·D-29 시각의 크롤러 힘·러너 값 네 항목의 두 창 값), `judge_062e051/chrono_path1/` 파일 목록, v5 기준 rev6 5절(146~159행), rev3 R3-G5, rev6 D-29·D-39, rev15 R15-3, rev19 R19-5.
- 판정서에는 이 목록을 그대로 싣고, 이 판의 정의를 "결과 본 뒤 정한 정의"로 적는다.

## R21-1. D-29 t_lift의 교체

- **[사실] 퇴화**(dynamics-expert 진단): L2b `pads.npz` `crawler_normal_N`은 표본 스텝 끝의 NSC 접촉력(`GetContactForce`)이라 충격처럼 튄다. 그래서 rev6 D-29("단계 ∉ {idle, check, touch} ∧ ≤ 0인 첫 표본")는 사실상 LEVEL 첫 표본이 된다. 행 집합별 수치는 다음과 같다.
  - C-1 L2b 6행: D-29가 LEVEL 시작과 0~1 ms, 그 시각 크롤러 30~75 kN(20 ms 평균, 30.2~74.6 kN).
  - C-2·C-5 L2b 1 ms 23행: LEVEL 전 1 s 0 비율 55~77 %(`pre_level_1s_zero_frac` 0.551~0.773), D-29 시각 크롤러 30~126 kN(29.9~126.1 kN; 큰 값은 `K0V_top_roll5.5` 126.1, `K0_top_rpBop` 126.06, `G1R_FS24` 118.8, `E_RE1bF_Fs0` 117.2).
  - C-1 6행에는 0 비율 값이 없다. 러너 t_lift(20 ms 평균 크롤러 Fz > 0인 마지막 10 Hz 표본의 다음 표본)는 이륙 완료를 0~0.1 s 안에서 짚는다.
- **[사실] 원 용도**: rev6 D-29가 빌린 v5 기준 rev6 5절 t_lift는 M2 잘림 스텝의 pre/post 분류(H-9)용이었다. 이륙 전 잘림(t ≈ 1.1 s)과 이륙이 20 s 넘게 떨어져 있어 ±0.1 s 오차로 분류가 바뀌지 않는다는 것이 그 근거였다(5절 "근거" 행). D8 창의 시작으로 쓰면 이 여유가 없다.
- **[정의] 새 D-29 t_lift**(C-1·C-2·C-5 L2b 행, 1 ms `crawler_normal_N`이 있는 행): v5 기준 rev6 5절의 t_lift,sus를 쓴다. t_lift,sus = 단계가 `idle`·`check`·`touch`가 아니고, 1 ms `crawler_normal_N` ≤ 0.01 W(W = 376.7 kN, 5절과 같은 문턱)가 기록 끝까지 이어지기 시작한 첫 1 ms 표본의 시각이다. 단계 규칙과 단계 시각 변환은 rev6 D-29 그대로다. `t_lift_basis` = `1ms_sus`로 적는다.
  - 기록 끝까지 ≤ 0.01 W가 유지되지 않으면 그 행의 새 t_lift는 없다. 이때 D8 세 항목과 D-39 C1 행은 `판정 불가`(원판 9.3)이고, 그 묶음은 판정 전에 멈추고 묻는다.
  - 명세 3절(309행) "크롤러 법선력 합이 0이 된 첫 시각"과의 관계: 스텝 끝 접촉력의 0은 법선력 합의 0이 아니므로, 0.01 W와 "끝까지 이어짐"으로 법선력 합이 0이 된 시각을 읽는다. 이것은 rev3 R3-G5의 조작 정의를 바꾸는 읽기이고, 판정서에 그대로 공개한다.
  - D8 세 항목(R19-5: `C1 D8 min true rod force`, `D8 min true cylinder force >= F_min + 5 kN`, `D8 no pad lift-off`)과 D-39 C1 행 재계산은 새 t_lift로 다시 계산한다.
- **[정의] V0 L2b 행**(1 ms `crawler_normal_N`이 없는 행): rev15 R15-3의 10 Hz 구간 대체를 그대로 쓴다(t_b = 크롤러 법선 ≤ 0인 첫 10 Hz 표본, 원본 `record.npz` `F_crawler`·`floor_plane.normal_world`).
  - **[사실] 같은 뜻인지**: R15-3의 t_b는 t_lift,sus와 정의가 같지 않다(문턱 0, 첫 표본, "끝까지 이어짐" 조건 없음). 진단에서 V0 `bracket_10Hz` 행의 차는 모두 0이었다. 그래서 정의는 바꾸지 않는다. 대신 경로마다 10 Hz t_lift,sus 대응값(그 10 Hz 표본부터 기록 끝까지 법선 ≤ 0.01 W인 첫 표본)을 기록으로 함께 낸다. t_b와 다르면 판정서에 적는다(등급은 R15-3 값으로 낸다). 대응값이 없으면 "기록 결측"으로 적는다.
- **[사실] D-29·R15-3을 쓰는 다른 곳**
  - rev6 D-39(C-1 C1 행): 새 t_lift를 따른다(위 [정의]).
  - rev19 R19-5(D8 세 항목, t_lift 차 비교): 새 t_lift를 따른다(R21-2).
  - rev15 R15-3(V0 L2b 행의 D8 t_lift, 예: C-5 `_V0` 행): 바뀌지 않는다.
  - rev6 D-30(SCM `scm_crawler_normal_N`, L1-R R6-B1)과 rev2 R2-5·R6-B4 t_D(P3 계열): 바뀌지 않는다. SCM 법선은 연속 진값이라 퇴화가 보고되지 않았다(5절 "근거" 행 `probe_vb` 41.401 s 첫 ≤ 0, 41.406 s부터 0, 재접촉 0).
  - v5 기준 rev6 5절의 M2 pre/post 분류(H-9·H-18·H-19)는 436.8 판정이 아니며 바꾸지 않는다.
- 결정 필요: **아니오**(사용자 결정 68의 1).

## R21-2. R19-5 비교 기준

- **[정의]** R19-5의 "맞춘 D-29 t_lift"는 R21-1의 새 t_lift(1 ms 행은 t_lift,sus를 그 시각 이상인 첫 10 Hz 제어 주기 표본으로 올린 값, V0 L2b 행은 R15-3 t_b 그대로)다. 차 = |러너 t_lift − 맞춘 D-29 t_lift|, 문턱 0.1 s + 10⁻⁹ s와 멈춤, 차를 계산할 수 없을 때의 멈춤, 러너 값을 쓰는 네 항목은 R19-5 그대로다.
- **[정의] 올림 경계 규칙**: 1 ms 행의 올림 값 = 같은 행 `record.npz` `t`(제어 주기 시각 배열)에서 t ≥ t_lift,sus − 10⁻⁹ s인 첫 표본의 시각이다. 정수 연산이나 `ceil`로 계산하지 않고 이 배열에서 고른다. 차와 문턱의 비교는 원판 7.6 허용(문턱 + 10⁻⁹ s)으로 한다.
- **[정의] 시간 원점**: 세 시각(`pads.npz` `t`, `record.npz` `t`, 러너 `liftoff_s` + `settings.start_t_s`)과 단계 시각(`phases` + `settings.start_t_s`, rev6 R6-1)은 모두 엔진 절대 시각으로 맞춘 뒤 비교한다. [사실] 원 자료 한 행(`07_results/S8/v5s3_VB_D1C2_middle_rollm4.4_Fs4_20261115_004908/D1C2_middle_rollm4.4_Fs4`)에서 `pads.npz` `t`(1 ms, 3.001~71.500 s)와 `record.npz` `t`(10 Hz, 3.1~71.5 s)는 이미 엔진 절대 시각이고(끝 값이 같음), `phases`는 상대 시각(첫 `check` 0.1 s), `settings.start_t_s` = 3.0 s였다.
- **[사실]** 진단의 10 Hz 올림 t_lift,sus는 29행 모두 러너와 차가 0 또는 +0.1 s였다. 러너 값을 쓰는 네 항목은 두 창 모두에서 판정이 같았고, C-2·C-5 L2b 23행에서 수치가 바뀌는 것은 F3 계열 3건(46.27·50.46·50.46 kN, 모두 문턱보다 크게 남음)과 `5a rocking amplitude` 9행의 미세 변화(C-2 2행, C-5 7행, 최대 Δ ≈ 0.0017°, 판정 같음)였다. 29행 가운데 12행은 차가 +0.1 s로 문턱에 붙는다. 마지막 1 ms 접촉 기준은 짧은 재접촉 때문에 맞지 않았다(`K0V_top_roll5.5`에서 −0.4 s). 그래서 그 기준은 쓰지 않는다.
- 결정 필요: **아니오**(사용자 결정 68의 2).

## R21-3. 도구 보완 커밋 R3c의 순서와 조건

- **[정의] 순서**
  1. 이 판을 봉인한다. 봉인 파일 커밋 S9를 S8 `4d8a95d` 위에 만든다(부모 = S8 = 봉인 기준 커밋 SEAL_COMMIT = `4d8a95d086ab196b268a9a494098b8458386e1a9`, 브랜치 `z4373-s4`). S9가 바꾸는 것은 이 판의 세 파일과 `.gitattributes`의 `-text` 3줄뿐이다.
  2. 도구 브랜치 둘을 R3b `062e051`에서 새로 가른다: 경로 1 `z4375-p1chrono`(python-expert), 경로 2 `z4375-p2chrono`(원 경로 2 작성자). 각 브랜치는 먼저 S9를 병합하고, R21-1·R21-2만 구현한다. Chrono 판정 도구의 봉인 목록은 rev16~rev21이다(두 경로 같게).
  3. 메인 세션이 R3b에서 통합 브랜치 `z4373-r3c`를 만들고 `z4375-p1chrono` → `z4375-p2chrono`를 `--no-ff`로 병합한다. 마지막 병합 커밋이 **R3c**다.
  4. 메인 checkout을 `git merge --ff-only z4373-r3c`로 R3b에서 R3c로 맞추고 master에 푸시한다. R3b..R3c에는 S9와 두 도구 브랜치의 커밋만 있다.
  - rev16 R16-12·rev18 R18-1의 R4 고쳐 씀은 R3c로 읽는다: 하네스 도구 브랜치 `z4373-p1harness`·`z4373-p2harness`와 R4 통합 브랜치 `z4373-r4`는 **R3c**에서 가른다. R4 조건의 Chrono 판정 도구·허용 목록 기준점은 **R3c..R4**다. 하네스 도구(R4)의 봉인 목록은 rev13~rev21이다.
- **[정의] R3c 조건**(모두 참이어야 R3c로 판정한다. 거짓이면 판정하지 않고 멈춘다, 원판 8.2 S-11)
  - `git diff --name-only 062e051..R3c -- 03_src 02_params`가 비어 있다.
  - `git diff --name-only 062e051..R3c -- 04_scripts`가 `04_scripts/02_chrono/chrono_rows_judge_4368.py`, `chrono_rows_judge_4368_README.md`, `chrono_bundle_grade_4368.py` 안이다. 러너·실행 경로와 manifest는 diff 0이다(rev18 R18-1의 목록 그대로).
  - `06_analysis/02_control/verif_matrix/scripts/resume4368_judge.py`는 diff 0이다(D-29를 쓰지 않는다).
  - `git diff --name-only 062e051..R3c`의 모든 파일이 허용 목록 안이다.
    - (가) rev21 규칙 파일 세 개(`v5_resume_4368_rules_rev21.md`, `.sha256`, `_seal_candidate_draft.md`)와 그 `.gitattributes` `-text` 3줄(지운 줄 0)
    - (나) 경로 1: 위 `04_scripts/02_chrono/` 세 파일, `05_tests/unit/test_chrono_rows_judge_4368.py`, `05_tests/unit/test_chrono_bundle_grade_4368.py`
    - (다) 경로 2: `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/` 아래 파일, `path2/p2_4368.py`(Chrono 하위 명령 부분)·`path2/test_p2_4368.py`·`path2/README.md`
    - (라) rev8 R8-4의 판정서·감사 기록, `00_docs/decision_log.md`·`00_docs/00_roadmap.md`·`00_docs/handoff/session_handoff.md`
  - R3c blob 표: (나)·(다) 파일의 `git show R3c:<파일>` LF 바이트 sha256 표를 판정서 부록에 싣는다.
- 결정 필요: **아니오**(사용자 결정 68의 4).

## R21-4. 재판정 범위와 R3b 출력의 처리

- **[정의] 경로 1**
  - 다시 돈다: `chrono_rows_judge_4368.py judge` C-1~C-8 전부와 `chrono_bundle_grade_4368.py`를 R3c 한 판으로 다시 돌린다(`--git-at-start` R2). 출력은 `judge_062e051/` 옆 새 폴더(R3c 커밋 이름)에 두고 R3b 출력은 지우지 않는다.
  - R3b 출력과의 대조: D-29 t_lift와 그에 기대는 값(D8 세 항목, D-39 C1 행, R19-5 차, 그 행·묶음 등급) 밖의 항목은 R3b `judge_C*.json`과 K-10 꼴로 같아야 한다. 다르면 판정서에 표로 싣고 그 묶음은 판정 전에 멈추고 묻는다.
  - 다시 쓰는 것(재실행 없음): 러너 판정 출력(`runner_judge/`, `03_src`·러너 diff 0), rev18 R18-2a 입력 view와 `k1-class`·`record-check` 출력, `fmin-time`·`oc5` 출력(`resume4368_judge.py` diff 0). 판정서에 R3b·R3c blob이 같음을 보인다.
- **[정의] 경로 2**: 진행 중인 R3b 판정은 끝까지 돌리든 멈추든 등급에 쓰지 않고 기록으로 둔다. 경로 2는 R3c 도구로 C-1~C-8을 다시 판정하고, D-29 밖 항목을 R3b 출력(있으면)과 K-10으로 대조한다. 다르면 경로 1과 같이 멈추고 묻는다.
- **[정의] 대체**: 판정에는 R3c 출력을 쓴다. R3·R3b 출력은 기록이다. 두 경로 등급이 갈리면 원판 S-13 그대로 멈추고 묻는다.
- 결정 필요: **아니오**(사용자 결정 68의 5).

## R21-5. 두 경로에 넘기는 문장

- **[정의]** 두 경로 작성자에게 같은 문장을 넘긴다: R21-1·R21-2·R21-3·R21-4의 [정의] 글머리, 그리고 인용한 원 절(v5 기준 rev6 5절, 명세 3절 309행, rev3 R3-G5, rev6 D-29·D-30·D-39, rev15 R15-3, rev19 R19-5). R21-0, [사실] 글머리, 진단 파일, 다른 경로의 코드·출력은 넘기지 않는다. 지시문에 "이 판의 다른 절은 열지 않는다"를 넣는다.
- 결정 필요: **아니오**(사용자 결정 68의 6).

## R21-6. 공개

- **[사실]** 판정서 한계 절에 그대로 적는다: "rev21은 R3b 경로 1 재판정이 C-1 L2b 6행에서 R19-5로 멈추고, dynamics-expert가 원인을 rev6 D-29 정의의 퇴화(L2b 스텝 끝 NSC 접촉력에서 첫 ≤ 0 표본이 LEVEL 첫 표본; C-1 L2b 6행: D-29가 LEVEL 시작과 0~1 ms, 그 시각 크롤러 30~75 kN; C-2·C-5 L2b 1 ms 23행: LEVEL 전 1 s 0 비율 55~77 %, D-29 시각 크롤러 30~126 kN)로 진단한 뒤 정했다. rev6 D-29가 빌린 정의는 원래 M2 잘림 스텝의 pre/post 분류용이었다. rev3 R3-G5의 조작 정의(명세 309행 '법선력 합이 0이 된 첫 시각' → 5절 첫 ≤ 0)를 같은 기준 문서(v5 기준 rev6 5절) 안의 t_lift,sus로 바꿨다. 새 정의 t_lift,sus는 결과를 본 뒤 정했고, 명세 3절의 '0'을 0.01 W와 '끝까지 이어짐'으로 읽는다."
- **[사실]** 9.2: 이 판의 정의는 경로 1 출력과 그 진단을 본 뒤 정했다. 두 경로는 같은 정의 문장만 받는다. 정의할 곳의 선택은 두 경로에서 독립이 아니다. 경로 2는 이 변경의 계기(경로 1 멈춤)를 정의 문장 밖으로는 받지 않는다.

### 결정 표

| 항목 | 정의 | 결정 필요 |
|---|---|---|
| R21-1 D-29 교체 | 1 ms 행 = t_lift,sus(≤ 0.01 W 끝까지, 단계 조건 그대로, `1ms_sus`), D8 세 항목·D-39 재계산, V0 L2b = R15-3 그대로(10 Hz sus 대응값 기록), D-30·t_D·M2 분류 불변 | 결정됨: 사용자 결정 68의 1, 69(V0 L2b R15-3 유지) |
| R21-2 R19-5 기준 | 맞춘 값 = 새 t_lift의 10 Hz 올림(V0는 t_b), 문턱·네 항목 그대로 | 결정됨: 사용자 결정 68의 2 |
| R21-3 R3c | S9(부모 S8, `z4373-s4`) → `z4375-p1chrono`·`z4375-p2chrono`(R3b에서, S9 병합 뒤 구현) → `z4373-r3c`(R3b에서, `--no-ff`) → 메인 ff-only·푸시; 03_src·02_params·러너·manifest·`resume4368_judge.py` diff 0, 허용 (가)~(라); R4 브랜치는 R3c에서, R4 기준점 R3c..R4; 봉인 목록 Chrono rev16~21·하네스 rev13~21 | 결정됨: 사용자 결정 68의 4, 69(브랜치) |
| R21-4 재판정 | 경로 1 judge·bundle 전부 R3c 재실행 + D-29 밖 K-10 대조, 러너·view·fmin-time·oc5 출력 재사용, 경로 2 R3b 출력은 기록, R3c 출력으로 판정 | 결정됨: 사용자 결정 68의 5 |
| R21-5 넘길 문장 | R21-1~R21-4 [정의] 글머리 + 인용 원 절 | 결정됨: 사용자 결정 68의 6 |
| R21-6 공개 | 결과 본 뒤 개정, 퇴화 수치, 원 용도, 9.2 | 결정됨: 사용자 결정 68의 3 |

### 결과 본 뒤 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-15 | 69 | 사용자 결정 69(2026-11-15, rev21 초안 보고의 판단 1·2): ① V0 L2b 행은 R15-3을 그대로 쓰고 10 Hz t_lift,sus 대응값을 기록하며 정의 차이를 공개한다. ② 새 도구 브랜치 `z4375-p1chrono`·`z4375-p2chrono`를 R3b에서 가르고 `z4373-r3c`로 통합한다 | R21-1, R21-3 |
| 2026-11-15 | 68 | 사용자 결정 68(2026-11-15): D-29 t_lift를 v5 기준 rev6 5절 t_lift,sus로 바꾸고 R19-5를 그 값으로 비교하는 rev21을 S8 위 S9로 봉인한 뒤, R3b 위에서 도구를 보완(R3c)하고 다시 판정한다 | R21-1~R21-6 |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 봉인 전 확인 필요는 없다(S8 해시·rev20 봉인 sha는 4행에 적었다).
2. 파일 이름: `v5_resume_4368_rules_rev21_seal_candidate_draft.md`를 같은 폴더에 `v5_resume_4368_rules_rev21.md`로 복사한다. 초안 파일은 지우지 않는다.
3. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev21 (R3b 경로 1 재판정 멈춤 뒤: D-29 t_lift를 t_lift,sus로 교체, R19-5 비교 기준, 도구 보완 커밋 R3c, 재판정 범위, 결과 본 뒤 개정, 봉인)`
4. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev21.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev21_seal_candidate_draft.md`와 1·3·5·9행만 다르다.`
5. 5행("시점")에서 `SEAL_TIME`과 `SEAL_COMMIT`(S8 `4d8a95d`)을 값으로 바꾼다. 이 두 이름 말고는 5행을 바꾸지 않는다.
6. 9행("봉인 준비판이다")을 다음으로 바꾼다:
   `- **봉인본이다.** 봉인 전 확인 필요는 없었고(S8 해시·rev20 봉인 sha는 4행), 사용자 결정 68·69(2026-11-15)와 봉인 전 감사(대상 초안 `d63a33fc`)의 차단·권고는 R21-1~R21-6에 반영했다(결정 69 = V0 L2b R15-3 유지·10 Hz t_lift,sus 대응값 기록·정의 차이 공개, 새 도구 브랜치 `z4375-p1chrono`·`z4375-p2chrono`와 통합 `z4373-r3c`).`
7. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules_rev21.sha256`에 `<sha256>  v5_resume_4368_rules_rev21.md  sealed <SEAL_TIME 값> (436.8 rev21: after the R3b 062e051 path 1 re-judgement stopped on R19-5 in the six C-1 L2b rows and the dynamics-expert diagnosis on top of rev20; thresholds, grades and stop meanings unchanged, seen-data list disclosed; seal commit S9 on S8 4d8a95d; D-29 t_lift on 1 ms L2b rows replaced by the criteria rev6 section 5 t_lift,sus (crawler_normal_N <= 0.01 W held to the record end, phase rule unchanged, basis 1ms_sus) because the first <= 0 step-end NSC sample degenerates to the first LEVEL sample (C-1 L2b 6 rows: D-29 within 0-1 ms of the LEVEL start, crawler 30-75 kN; C-2 / C-5 L2b 1 ms 23 rows: 55-77 % zeros in the last second before LEVEL, crawler 30-126 kN at D-29); no t_lift,sus = D8 items and D-39 not judgeable and stop-and-ask; 10 Hz rounding by the record.npz t array (first t >= t_lift,sus - 1e-9), comparison with the 7.6 tolerance; D8 three items and D-39 recomputed; V0 L2b keeps R15-3 with the 10 Hz sustained counterpart recorded and the definition difference disclosed (user decision 69); D-30, t_D and the M2 pre / post split unchanged; R19-5 compares the runner t_lift with the new t_lift rounded up to the 10 Hz grid, threshold and the four runner items unchanged; tool fix commit R3c = z4373-r3c (--no-ff merges of z4375-p1chrono and z4375-p2chrono cut from R3b 062e051 after merging S9, user decision 69), main fast-forwarded R3b -> R3c and pushed, 03_src / 02_params / runners / manifest / resume4368_judge.py diff 0, allow list (a)-(d); harness tool branches and z4373-r4 cut from R3c, R4 conditions read as R3c..R4; seal lists Chrono rev16..21 / harness rev13..21; path 1 judge and bundle grade re-run at R3c with K-10 against R3b outside the D-29 items, runner / view / fmin-time / oc5 outputs reused, path 2 R3b outputs recorded only; same definition sentences to both paths; user decisions 68 / 69; 9.2 exception disclosed)` 한 줄로 쓴다.
8. `.gitattributes`에 다음 3줄을 더한다(**`git add`보다 먼저**, 지우는 줄 없음):
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev21.md -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev21.sha256 -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev21_seal_candidate_draft.md -text`
9. 확인: `tools/verif/seal_check.py`와 `tools/verif/placeholder_scan.py`를 돌리고, 봉인본 5행에 `SEAL_TIME`·`SEAL_COMMIT`이 남지 않았는지 Grep으로 따로 본다.
10. `git add`(세 파일과 `.gitattributes`)와 봉인 파일 커밋 S9를 S8 위에 만든다(브랜치 `z4373-s4`). 메인 checkout의 HEAD는 바꾸지 않는다(R3b 그대로, R21-3 순서 4에서 R3c로 맞춘다). 봉인 뒤 이 문서를 고치지 않는다.
