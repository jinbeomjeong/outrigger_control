# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev15 (R2 본 실행 뒤 판정 중: 판정 도구 커밋 R3 ≠ 실행 커밋 R2, D-29 V0 L2b t_lift, manifest 재생성, LS 판별 범위, PS-c G-S 정체성, 결측 두 건, 결과 본 뒤 개정, 봉인)

- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev15.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev15_seal_candidate_draft.md`와 1·3·5·9행만 다르다.
- 원판 `v5_resume_4368_rules.md`(sha256 `9019b405…`), rev1(`d9094fda…`), rev2(`497e4614…`), rev3(`dad8dfa6…`), rev4(`7ea87a30…`), rev5(`452a8436…`), rev6(`809e5639…`), rev7(`e81f7d31…`), rev8(`3ecafaaf…`), rev9(`4cf7843c…`), rev10(`62a0bd8d…`), rev11(`9bac4524…`), rev12(`78f1f99b…`), rev13(`383bffc1…`), rev14(`baedeab4…`)는 고치지 않는다. 이 판은 rev14(sha256 `baedeab499133214804167dede4c4674f9edba4e67bd711dd6418a561f60ac3f`, 봉인 커밋 `e1a2f66`) 위에 쌓인다. 전체 sha256은 각 판의 `.sha256`에 있다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 앞 판 그대로다.
- **시점: R2 `b9f5707` 본 실행 중·판정 중, 결과 일부를 본 뒤(봉인 2026-11-15 00:08:30 +09:00, 봉인 커밋 b9f5707, 판정 입력 manifest `chrono_rows_manifest.json` LF blob sha256 `f00cd5d85d45739384c19db455e6d659472d068a3cca91ab0a1242db7f42d40e`, 이미 행이 있던 묶음은 불변, OC5 묶음의 `n`·`rows`·`list_sha256`·`est_sum_s`는 새 O-C5 본 행의 결과로 바뀜).** 이 판은 결과를 본 뒤의 개정이다. 본 자료는 R15-0에 모두 적었다.
- 작성: control-expert, 2026-11-14. 기준 R2 = `b9f5707`(rev14 R14-3). 계기: Chrono 판정 중 판정 도구 결함 셋과 규칙 공백 셋이 나왔다.
  - 판정 도구 결함(결정 19, 도구만 수정): 경로 1 `z4372-p1judge`(첫 커밋 `e998fd5`), 경로 2 `z4372-p2chrono`(`5a84e94`), 경로 2 `z4372-p2t45`(첫 커밋 `e0238de`). 세 브랜치 모두 R2에서 갈라졌다.
  - 규칙 공백: D-29의 V0 L2b t_lift, C-7b `v5_hydraulics` 부재, C-4 끔 팔 `liftoff_approach_slow` 결측. 그 밖에 판정 입력 manifest에 O-C5 본 행이 없었다.
- **봉인본이다.** 사용자 결정이 필요한 새 항목은 없었고, 사용자 결정(2026-11-14) (a)~(h)는 R15-1~R15-8과 R15-9 결정 표에 반영했다.
- **바꾸지 않는 것**: 숫자 문턱, 등급과 우선순위, 멈춤 조건의 뜻, 묶음 범위와 행 목록, 사전 예측 값, P-1·P-2 앵커, 두 경로 요건(원판 9.2), 모든 묶음의 실행 커밋 `git_at_start` = R2(rev14 R14-3). 이 판은 새 숫자를 쓰지 않고, 이미 돈 실행의 argv·코드를 바꾸지 않는다.

## R15-0. 결과 본 뒤 개정의 공개 (본 자료 목록)

- 이 판은 R2 본 실행 결과 일부가 나온 뒤에 쓴다. 문턱·등급·멈춤 조건의 뜻은 바꾸지 않는다. 바꾸는 것은 판정 도구와 판정 입력, 그리고 원 규칙이 정하지 않은 세 곳의 읽기(R15-3·R15-4)뿐이다.
- **이 판을 쓰기 전에 사람·도구가 본 것**(메인 세션 전달, 2026-11-14):
  1. 실행 상태: 하네스 73단계 모두 exit 0(23:31). Chrono C-1·C-3·C-4·C-5(3폴더)·C-6/7·OC5PROBE·OC5 본 행 rc 0. C-2 4행(22:26~)과 PS-c 2행(23:01~)은 진행 중이다.
  2. PS-c G-S 1행의 확인 결과: `gs_psc_check` ok, R4-D 열과 사건 키 있음, 1 ms 55,301행(R15-6).
  3. H-2 C-2 선정: 두 경로가 같은 6행을 골랐다(사용자 결정 (h)).
  4. Chrono 판정 중 판정자가 본 것:
     - V0 L2b 행에 1 ms `crawler_normal_N`이 없고, 경로 1 `e998fd5`가 그 행의 10 Hz 구간 값을 `reference_not_used`로 남겼다(판정자는 그 값을 보았다).
     - C-7b 행에 `v5_hydraulics` 블록이 없다.
     - C-4 끔 팔에 `controller_meta.liftoff_approach_slow`가 없다.
     - 경로 1이 V0 L2b 행을 L1-R로 읽었다.
     - 경로 2가 C-7a·b를 열린 루프로 읽지 않았고, probe에 O-C5 본 행 블록을 적용했다.
     - `p2_t45` 회귀 행 폴더를 정확히 고정하지 않았다.
  5. 판정 등급·멈춤 여부·P-1·P-2 대조 결과는 이 판을 쓰는 데 쓰지 않았다. 이 작성자는 결과 파일과 판정 출력의 내용을 열지 않았다. 도구 커밋은 이름·줄 수·커밋 메시지와 `v5_resume_4368_chrono_rows.py` diff만 보았다.
- 사후 개정이므로 판정서에는 이 목록을 그대로 싣는다. D-29 V0 L2b(R15-3)처럼 값을 본 뒤 정한 읽기는 그 사실을 판정 결과 옆에 적는다.
- 이 작성자는 경로 2 작성자가 아니다(rev2 R2-0).

## R15-1. 판정 도구 커밋 R3와 실행 커밋 R2 (사용자 결정 (d)·(e))

- **정의**:
  1. 실행 커밋은 모든 묶음에서 R2 `b9f5707` 그대로다(rev14 R14-3). 판정 도구는 R3에서 돌린다. R2 ≠ R3을 허용한다(사용자 결정 (d)).
  2. 판정 도구의 `--git-at-start`에는 R2를 준다(rev12 R12-3). R11-4 커밋 정체성, K-0, 사이드카 head 대조는 모두 R2와 대조한다. 판정서에는 실행 커밋 R2와 판정 도구 커밋 R3을 따로 적는다.
  3. **R3 병합 시점**(사용자 결정 (e)): 하네스가 끝나고(23:31, 끝남), C-2·PS-c·OC5 러너의 `.done`이 모두 써진 뒤다. 그 전에는 메인 checkout에서 커밋·병합하지 않는다(원판 A-5 둘째 문장, S-12). 봉인 커밋과 도구 수정은 전용 worktree의 브랜치에서 만든다(A-5의 worktree 예외).
     - 이 문장은 rev14 R14-4 순서 6("R2 뒤에는 모든 묶음이 끝날 때까지 커밋·병합하지 않는다")을 고쳐 쓴다. R2 뒤의 커밋은 R15-2의 R3 조건을 지키는 R3(와 그 안의 브랜치 커밋)만 허용하고, R3 뒤 판정이 끝날 때까지는 판정서·감사 기록만 더한다.
  4. 원판 11.2: 실행 코드가 R2와 같으므로(R15-2 조건) R2의 G-S가 그대로 11.2 충족이다(rev14 R14-4). R3에서 실행 G-S를 다시 돌지 않는다. 다만 R3 판정 도구의 G-S 읽기(경로 1 `gs-check`, 경로 2 `gs-load`)는 R2의 G-S 출력에 다시 적용한다. 그 결과를 기록하고, R2 때와 달라진 항목은 판정서에 공개한다.
  5. **C-5 경로 2 재판정**(사용자 결정 43): R3 병합 뒤 C-5 경로 2를 R3의 경로 2 도구로 다시 판정한다. R3 이전 도구로 낸 C-5 경로 2 출력은 기록으로만 두고 대조(원판 9.2)에 쓰지 않는다.
- 결정 필요: **아니오**(사용자 결정 (d)·(e)·43).

## R15-2. R3의 모양과 허용 목록 (방법 1: 봉인 먼저)

- **순서**(rev15 봉인 sha를 도구에 미리 넣는다):
  1. manifest 생성기 수정과 manifest 재생성은 끝났다(R15-5): 브랜치 `z4372-manifest` 커밋 `57828fc`(부모 R2). 그 manifest의 LF blob sha256 `f00cd5d85d45739384c19db455e6d659472d068a3cca91ab0a1242db7f42d40e`를 5행에 적었다.
  2. 이 판을 봉인한다. 봉인 커밋 S3는 전용 worktree 브랜치에서 R2 위에 만든다(부모 = R2 `b9f5707`). S3이 바꾸는 것은 (가) 세 파일과 (나) `.gitattributes` 3줄뿐이다.
  3. R15-3의 D-29 읽기는 봉인 전에 두 브랜치에 들어갔다: 경로 1 `z4372-p1judge` 끝 `531729f`(구현 커밋 포함, 출력 키 `l2b_bracket_rows_R15_3`), 경로 2 `z4372-p2t45` 끝 `4d03747`(`floor_plane.normal_world` 사영). 봉인 뒤 두 Chrono 도구에 R15-7의 봉인 목록(rev15 sha)을 넣는 커밋을 각 브랜치(`z4372-p1judge`, `z4372-p2t45`) 위에 하나씩 더한다. 경로 2는 경로 2 작성자가 고치고 원판 9.2 독립성 요건은 그대로다.
  4. R15-1 3의 시점에 메인 checkout에서 다음을 이 차례로 `--no-ff` 병합한다: S3 브랜치 → `z4372-p1judge` → `z4372-p2chrono`(`5a84e94`) → `z4372-p2t45` → `z4372-manifest`(`57828fc`). `z4372-p1judge`와 `z4372-p2t45`의 병합 대상은 순서 3의 봉인 목록 커밋이 올라간 브랜치 끝이다(그 바로 아래가 각각 `531729f`, `4d03747`). 마지막 병합 커밋이 R3이다. 병합에서 충돌을 손으로 풀면 그 결과를 판정 전 감사가 본다. R3 뒤 판정이 끝날 때까지 실행 코드를 바꾸는 커밋은 없다.
     - 위 다섯 브랜치(끝 커밋은 순서 3 뒤 기준)의 커밋과 병합 커밋 말고는 R2..R3에 들어가지 않는다. 그 밖의 커밋이 들어가면 R3 조건이 거짓이다.
  5. R3에서 manifest를 다시 생성하고 R3에 든 manifest와 바이트가 같은지 확인한다(사용자 결정 (f)).
- **R3 조건**(모두 참이어야 판정한다):
  - `git diff --name-only b9f5707..R3 -- 03_src 02_params`의 출력이 비어 있다.
  - `git diff --name-only b9f5707..R3 -- 04_scripts`의 출력이 정확히 다음 셋 안이다: `04_scripts/02_chrono/chrono_rows_judge_4368.py`, `04_scripts/02_chrono/chrono_rows_judge_4368_README.md`, `04_scripts/02_chrono/v5_resume_4368_chrono_rows.py`. 러너 경로(`run_S9.py`, `run_S8C.py`, `run_S6C.py`, `s9_batch.py`, `04_scripts/04_hydraulic`, `04_scripts/03_control`, `04_scripts/01_dynamics`)는 diff 0이다.
  - `git diff --name-only b9f5707..R3`의 모든 파일이 허용 목록 안이다.
    - (가) `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev15.md`, `v5_resume_4368_rules_rev15.sha256`, `v5_resume_4368_rules_rev15_seal_candidate_draft.md`
    - (나) `.gitattributes`에 (가) 세 파일의 `-text` 줄 3개를 더한 것만(지운 줄 0개). manifest에는 `-text` 줄을 더하지 않는다: 이미 추적되는 파일에 속성을 바꾸면 작업 복사본 바이트가 바뀌고(CRLF → LF), rev7 R7-4가 적은 작업본 sha256 기준과 어긋난다. manifest는 LF blob sha256으로만 대조한다(R15-5).
    - (다) 경로 1: `04_scripts/02_chrono/chrono_rows_judge_4368.py`, `chrono_rows_judge_4368_README.md`, `05_tests/unit/test_chrono_rows_judge_4368.py`
    - (라) 생성기·manifest: `04_scripts/02_chrono/v5_resume_4368_chrono_rows.py`, `05_tests/unit/test_v5_resume_4368_chrono_rows.py`, `05_tests/unit/test_v5_resume_4368_manifest_oc5.py`(새 파일), `06_analysis/02_control/verif_matrix/v5_resume_4368/chrono_rows_manifest.json`(LF blob sha256 = 5행 값)
    - (마) 경로 2: `06_analysis/02_control/verif_matrix/v5_resume_4368/path2/` 아래 `README.md`·`p2_4368.py`·`test_p2_4368.py`, `path2_v5c/` 아래 `README.md`·`p2v5c_common.py`, `path2_chrono/` 아래 `README.md`·`p2_core.py`·`p2_kinds.py`·`p2_rules.py`·`p2_t45.py`·`test_p2_synthetic.py`
    - (바) rev8 R8-4의 판정서·감사 기록, `00_docs/decision_log.md`·`00_docs/00_roadmap.md`·`00_docs/handoff/session_handoff.md`
  - 생성기 조건: R3의 `v5_resume_4368_chrono_rows.py`가 내는 행 정의(argv·`case`·`criteria_id`)가 R2와 같다. 확인 방법은 세 가지다.
    - **R2 manifest에 이미 행이 있던 묶음**: 행 항목과 묶음별 `list_sha256`이 R2의 manifest 값과 같다.
    - 이미 돈 행의 argv가 각 `batch.json` `cases[].argv`와 같다.
    - rev7 R7-4의 `gs_conditional_table` `table_sha256` `eef5129f…`도 그대로다.
    - 달라지는 것은 다음뿐이어야 하고, 모두 새로 들어간 O-C5 본 행의 결과다: OC5 묶음(`V5-RESUME-K1-OC5`)의 `n`(0 → 2)·`rows`·`list_sha256`(`e3b0c442…` → `539fb9e9…`)·`est_sum_s`, 그리고 `gs_conditional_absent.scope.V5-RESUME-K1-OC5.level_rows`의 확장.
  - 하나라도 거짓이면 판정하지 않고 멈춘다(원판 8.2 S-11).
- **blob sha의 기록**: (다)·(마)와 생성기 코드의 최종 내용은 이 판 봉인 뒤에 정해진다(순서 3). 그래서 manifest 말고는 blob sha256을 이 판에 적지 않는다.
  - R3를 만든 뒤 `git show R3:<파일>`의 LF 바이트 sha256 표(이하 R3 blob 표)를 판정서 부록에 싣는다.
  - 판정 전 감사(verif-protocol-auditor)가 R3 blob 표를 감사한 브랜치 끝 커밋의 blob과 대조한다.
  - 판정 뒤 R3 blob과 다른 도구로 낸 출력은 쓰지 않는다.
- 결정 필요: **아니오**(사용자 결정 (d)·(e)·(f), 방법 1).

## R15-3. D-29 V0 L2b 행의 t_lift (사용자 결정 (c), 결과 본 뒤)

- 사실: rev6 D-29는 C-1·C-2·C-5 L2b 행의 D8 t_lift를 1 ms `pads.npz` `crawler_normal_N`으로 정했다. V0 L2b 행의 `pads.npz`에는 그 배열이 없다(`law_locked`는 있다). rev6 R6-B1의 10 Hz 구간 대체는 L1-R 행에만 정해져 있었다. 그래서 V0 L2b 행의 t_lift는 규칙 공백이었다.
- **정의**: 1 ms `crawler_normal_N`이 없는 L2b 행(V0 L2b)의 D8 t_lift는 rev6 R6-B1의 10 Hz 구간 대체로 정한다. R6-B1은 v5 기준 개정 6 5절 "1 ms 크롤러 기록이 없는 실행"의 문장이다.
  - t_lift = 단계가 `idle`·`check`·`touch`가 아니고 크롤러 법선 ≤ 0인 **첫** 10 Hz 표본 시각 t_b다. t_a(법선 > 0인 마지막 10 Hz 표본)도 기록한다. `t_lift_basis` = `bracket_10Hz`.
  - **원본**(두 경로 같음, L1-R의 R6-B1이 쓰는 원본과 이름·꼴이 같다):
    - 크롤러 힘: 행 폴더 `record/record.npz`의 키 `F_crawler`, `[N, 3]` 세계 좌표 벡터 [N]. 출처는 `TruthState.F_crawler_N`(`03_src/outrigger_sim/signals.py` 348행)이다.
    - 시간축: 같은 파일의 `t`(0.1 s 간격) [s].
    - 법선: `result.json` `floor_plane.normal_world`를 단위 벡터로 정규화한 n. 크롤러 법선 = `F_crawler` · n [N].
    - 단계 시각: `result.json` `phases`의 시각에 `settings.start_t_s`를 더해 `t`와 같은 시각 기준으로 맞춘다.
  - 이 원본 가운데 하나라도 없거나 꼴이 다르면(`F_crawler`가 `[N, 3]`이 아님, `t`와 길이가 다름, 법선이 0 벡터) 그 행의 D8 t_lift는 `판정 불가`다(원판 9.3). 판정서에는 행마다 쓴 파일·키를 적는다.
  - 1 ms `crawler_normal_N`이 있는 L2b 행은 rev6 D-29 그대로다.
- 경로 1 `e998fd5`의 처리(`rule_gap`, 구간 값 `reference_not_used`, 출력 키 `rule_gaps_D29`)는 이 정의로 바꿨다(`z4372-p1judge` `531729f`, 출력 키 `l2b_bracket_rows_R15_3`). 경로 2 `e0238de`의 "D-29 rev15 대기" 관문도 이 정의로 열었다(`z4372-p2t45` `4d03747`). 두 구현이 위 원본을 그대로 쓰는지는 판정 전 감사가 본다.
- **공개**: 이 읽기는 판정자가 V0 L2b 행의 구간 값을 본 뒤에 정했다(R15-0 4). 판정서에는 그 행들의 t_lift와 `t_lift_basis`, 그리고 "결과 본 뒤 정한 읽기"를 함께 적는다. 1 ms 기록이 있는 행과 섞어 하나의 값 범위로 요약하지 않는다.
- 결정 필요: **아니오**(사용자 결정 (c)).

## R15-4. 결측 두 건의 공개 규칙 (사용자 결정 (a)·(b))

1. **C-7b `v5_hydraulics` 부재 = 정상**: C-7b(`P3a_G1_B_V0_FB`)는 V0 열린 루프다. 원판 5.3 C-7b 열은 "V0라 유량 항목 해당 없음"이라고 적는다. 그래서 `v5_hydraulics` 블록과 유량 항목(`args.flow_law`, `v5_hydraulics.controller_options`, `flow_limit.summary`, `flow_series.npz`)이 없는 것은 결측(원판 9.3)이 아니라 해당 없음이다. 두 경로 모두 그 행에서 유량 항목을 "해당 없음"으로 적는다. VB 열린 루프 행(C-6, C-7a)에는 이 항목들이 필수 그대로다.
2. **C-4 끔 팔 `liftoff_approach_slow` 결측 = 허용 결측**: C-4 끔 팔(`--las-off`, `r4368.arm` = `"off"`)에서 `controller_meta.liftoff_approach_slow`의 블록 전체나 하위 키가 없는 것은 rev7 R7-4의 허용 결측(끔 팔은 `liftoff_approach_slow.*` 결측 허용)이고, rev1 RV1-10 b("끔 팔은 블록이 없거나 `enable` 거짓")와 같다. 7.2 분류는 RV1-10 b대로 "LAS 없음"이다. 판정서에는 허용 결측으로 기록한다. 켬 팔에서 같은 키가 없으면 rev7 R7-4대로 `result_missing`이다.
- 결정 필요: **아니오**(사용자 결정 (a)·(b)).

## R15-5. 판정 입력 manifest 재생성 (사용자 결정 (f))

- manifest `06_analysis/02_control/verif_matrix/v5_resume_4368/chrono_rows_manifest.json`은 판정 입력이다(rev7 R7-4, rev10 R10-1). R2 판에는 OC5 본 행이 없었다. cad-expert가 생성기(`v5_resume_4368_chrono_rows.py`)를 고쳐, 실행한 O-C5 probe를 그대로 두고 O-C5 본 행을 함께 담아 다시 만들었다: 브랜치 `z4372-manifest` 커밋 `57828fc`(부모 R2), 시험 `05_tests/unit/test_v5_resume_4368_manifest_oc5.py`.
- 조건:
  - R2 manifest에 이미 행이 있던 묶음의 행 항목과 묶음별 `list_sha256`은 바뀌지 않는다. OC5 묶음은 R2에 행이 없었으므로(0행) 이 불변 조건의 대상이 아니다. 그 `n`·`rows`·`list_sha256`(`e3b0c442…` → `539fb9e9…`)·`est_sum_s`는 새 O-C5 본 행 2행의 결과로 바뀐다.
  - `gs_conditional_absent` 표의 `table_sha256` `eef5129f43114877a005950ddd30eca8216d4d08a3196a2d1e82e5dc3363c9aa`도 바뀌지 않는다.
  - 새 항목의 argv는 실제로 돈 probe·O-C5 본 행의 `batch.json` `cases[].argv`와 같다.
  - 불변 확인 결과(메인 세션 전달, cad-expert): 기존 행·`list_sha256`·`table_sha256` `eef5129f…`·`s9_batch` 배치 정의 72개가 그대로다. 바뀐 것은 새 O-C5 본 행의 결과인 OC5 묶음의 `n`(0 → 2)·`rows`·`list_sha256`(`e3b0c442…` → `539fb9e9…`)·`est_sum_s`와 `gs_conditional_absent.scope.V5-RESUME-K1-OC5.level_rows`의 확장뿐이다. 새 행 argv는 실제 `batch.json`과 같다. `e998fd5`와 병합해도 충돌이 없고 manifest sha도 같다. 판정 전 감사가 같은 확인을 R3에서 다시 한다.
- 판정에 쓰는 manifest는 R3에 든 파일이다. 그 LF blob sha256(`git show R3:<경로>`)은 `f00cd5d85d45739384c19db455e6d659472d068a3cca91ab0a1242db7f42d40e`(5행)이고, R3에서 다시 생성한 결과의 LF 바이트가 같아야 한다. 이 파일에는 `.gitattributes` 속성이 없고 `core.autocrlf=true`라 작업 복사본은 CRLF다. 그래서 대조는 blob 기준으로 하고, 작업 복사본 sha256은 판정서에 참고로만 적는다.
- 결정 필요: **아니오**(사용자 결정 (f)).

## R15-6. PS-c G-S를 배치 밖에서 돈 것 (공개)

- rev5 R5-B4 순서 2(PS-c 행 전에 G-S 1행)를 `run_S9.py` 직접 실행으로 했다. 출력은 `06_analysis/02_control/verif_matrix/v5_resume_4368/gs_psc_b9f5707/`이고, `--duration`은 130 s다.
- 배치 러너(`s9_batch`)를 거치지 않았으므로 `batch.json`과 `cases[].code_at_launch`가 없다. 그래서 이 G-S 행의 실행 정체성은 둘로 대신한다: 실행 직전에 쓴 `gs_identity_start.json`과 `result.json` `code_state`(`git_at_start`, `files_at_start`). 둘의 커밋은 R2여야 한다.
- 대체가 허용되는 범위:
  - 이 대체는 이 G-S 1행에만 허용한다. G-S는 판정하지 않으므로(원판 11.2) R11-4의 "기록 없음 = S-12"는 본 행에만 적용한다.
  - PS-c 본 행 2행은 배치 러너로 돌고 있다. 그 행들은 R11-4 그대로 `code_at_launch.git.head`와 `code_state.git_at_start`를 R2와 대조한다.
- 확인 결과(`gs_psc_check` ok, R4-D 열·사건 키 있음, 1 ms 55,301행)와 두 정체성 파일의 sha256을 판정서에 적는다.
- 결정 필요: **아니오**.

## R15-7. 봉인 확인 목록

- 이 절은 rev14 R14-7 첫 문장("도구의 봉인 확인 목록(경로 1·경로 2 모두)은 rev12까지 그대로 둔다")을 두 Chrono 판정 도구에 한해 고쳐 쓴다.
- R15-3의 정의를 구현하는 두 Chrono 판정 도구는 봉인 확인 목록에 rev15 파일과 그 봉인 sha를 넣는다. 경로 1은 `chrono_rows_judge_4368.py` `RULES_SEALS`, 경로 2는 `path2_chrono`의 봉인 목록(`p2_t45`가 읽는 것)이다. 이것이 방법 1(봉인 먼저)의 이유다. 두 경로를 같게 한다. 다르거나 없으면 원판 8.2 S-1이다.
- 하네스 판정 도구와 그 밖의 도구 목록은 rev12까지 그대로 둔다(rev13 R13-7, rev14 R14-7). rev13·rev14와, 목록에 없는 도구에 대한 rev15 확인은 `tools/verif/seal_check.py`로 한다. 시점은 판정 전 감사와 판정서 커밋 전이다.
- 결정 필요: **아니오**(방법 1의 결과, 두 경로 대칭).

## R15-8. LS 판별의 적용 범위 (사용자 결정 (g))

- rev10 R10-1(전체 묶음 이름·manifest 행 수·manifest 파일에 따른 `판정 불가`·입력 오류)은 LS 판별을 하는 **C-5 행에만** 적용한다. rev9 R9-4 "LS 판별은 J11을 판정하는 C-5 행에서만 쓴다"와 같은 범위다.
- C-5 밖의 Chrono 행(C-1~C-4, C-6~C-8, probe, JP)에서는 LS 판별을 하지 않는다. manifest에 행이 없거나 묶음 이름을 정할 수 없어도 그것만으로 `판정 불가`나 입력 오류가 되지 않는다. 그 행의 다른 판정 항목에서 manifest를 쓰는 곳(rev7 R7-4 키 결측 표)은 원래 규칙 그대로다.
- 결정 필요: **아니오**(사용자 결정 (g)).

## R15-9. 결정 표

| 항목 | 권고·정의 | 결정 필요 |
|---|---|---|
| R15-0 사후 개정 공개 | 본 자료 목록을 판정서에 싣는다. 문턱·등급·멈춤의 뜻은 그대로 | 아니오 |
| R15-1 R3 ≠ R2 | 실행 R2, 판정 도구 R3, `--git-at-start` R2. R3 병합은 하네스 끝 ∧ C-2·PS-c `.done` 뒤. R2 G-S가 11.2 충족, R3 도구의 G-S 읽기는 다시 적용해 기록 | 결정됨: 사용자 결정 2026-11-14 (d)·(e) |
| R15-2 R3 모양 | 방법 1: 생성기 수정·manifest sha·D-29 구현(`531729f`·`4d03747`) → rev15 봉인(S3, 부모 R2) → 두 Chrono 도구에 rev15 봉인 목록 커밋 → S3 → p1judge → p2chrono → p2t45 → manifest `--no-ff` 병합 = R3. R14-4 순서 6을 고쳐 씀. C-5 경로 2는 R3 도구로 재판정(결정 43). `03_src`·`02_params`·러너 diff 0, 허용 목록 (가)~(바), blob 표는 판정서 부록과 감사 | 결정됨: 사용자 결정 2026-11-14 (d)·(e)·(f), 방법 1 |
| R15-3 D-29 V0 L2b | 1 ms `crawler_normal_N` 없는 L2b 행은 R6-B1 10 Hz 구간 대체(t_b, `bracket_10Hz`), 결과 본 뒤 정한 읽기로 공개 | 결정됨: 사용자 결정 2026-11-14 (c) |
| R15-4 결측 두 건 | C-7b `v5_hydraulics` 부재 = 해당 없음(원판 5.3). C-4 끔 팔 `liftoff_approach_slow` 결측 = R7-4 허용 결측 | 결정됨: 사용자 결정 2026-11-14 (a)·(b) |
| R15-5 manifest | `57828fc`: O-C5 probe 유지 + O-C5 본 행 2행 추가로 재생성, `-text` 줄 없이 blob 대조, 기존 행·`list_sha256`·`table_sha256` 불변, LF blob sha = 5행 값, R3에서 재생성 같음 | 결정됨: 사용자 결정 2026-11-14 (f) |
| R15-6 PS-c G-S | 배치 밖 직접 실행, 정체성은 `gs_identity_start.json` + `code_state`(R2), 이 1행에만 | 아니오 |
| R15-7 봉인 목록 | 두 Chrono 판정 도구에 rev15를 넣음(대칭), 그 밖은 rev12까지 + `seal_check.py` | 아니오 |
| R15-8 LS 범위 | R10-1은 C-5 행에만 | 결정됨: 사용자 결정 2026-11-14 (g) |

### 결과 본 뒤 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-14 | (a) | 사용자 결정 2026-11-14: C-7b `v5_hydraulics` 부재 = 정상(V0 해당 없음) | R15-4 1 |
| 2026-11-14 | (b) | 사용자 결정 2026-11-14: C-4 끔 팔 `liftoff_approach_slow` 결측 = R7-4 허용 결측으로 기록 | R15-4 2 |
| 2026-11-14 | (c) | 사용자 결정 2026-11-14: D-29 V0 L2b t_lift = R6-B1 10 Hz 구간 대체(결과 본 뒤 개정, 공개) | R15-3 |
| 2026-11-14 | (d) | 사용자 결정 2026-11-14: 판정 도구 커밋 R3 ≠ 실행 커밋 R2 허용 | R15-1, R15-2 |
| 2026-11-14 | (e) | 사용자 결정 2026-11-14: R3 병합 = 하네스 끝 ∧ C-2·PS-c 러너 `.done` 뒤 | R15-1 3 |
| 2026-11-14 | (f) | 사용자 결정 2026-11-14: manifest는 판정 입력, probe·본 행 포함 재생성, sha를 rev15에, 생성기 수정(cad-expert), R3에서 재생성 | R15-2, R15-5 |
| 2026-11-14 | (g) | 사용자 결정 2026-11-14: R10-1 LS 판별은 C-5 행에만 | R15-8 |
| 2026-11-14 | (h) | 사용자 결정 2026-11-14: H-2 C-2 선정은 두 경로가 같은 6행 | R15-0 3 |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 파일 이름: `v5_resume_4368_rules_rev15_seal_candidate_draft.md` → `v5_resume_4368_rules_rev15.md`(같은 폴더). 초안 파일은 지우지 않고 그대로 둔다.
2. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev15 (R2 본 실행 뒤 판정 중: 판정 도구 커밋 R3 ≠ 실행 커밋 R2, D-29 V0 L2b t_lift, manifest 재생성, LS 판별 범위, PS-c G-S 정체성, 결측 두 건, 결과 본 뒤 개정, 봉인)`
3. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev15.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev15_seal_candidate_draft.md`와 1·3·5·9행만 다르다.`
4. 5행("시점")에서 `SEAL_TIME`(예: 2026-11-14 10:00:00 +09:00)과 `SEAL_COMMIT`(봉인 파일을 넣는 커밋 S3의 부모 = R2 `b9f5707`, R15-2 순서 2)을 값으로 바꾼다. 이 두 이름 말고는 5행을 바꾸지 않는다(manifest sha는 이미 값이다).
5. 9행("봉인 준비판이다")을 다음으로 바꾼다:
   `- **봉인본이다.** 사용자 결정이 필요한 새 항목은 없었고, 사용자 결정(2026-11-14) (a)~(h)는 R15-1~R15-8과 R15-9 결정 표에 반영했다.`
6. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules_rev15.sha256`에 `<sha256>  v5_resume_4368_rules_rev15.md  sealed <SEAL_TIME 값> (436.8 rev15: after part of the R2 b9f5707 results, on top of rev14; thresholds, grades and stop meanings unchanged, seen-data list disclosed; run commit stays R2 for every bundle, judgement tools at R3 with --git-at-start R2, R3 merged after the harness end and the C-2 / PS-c / OC5 runner .done (rewrites rev14 R14-4 step 6), C-5 path 2 re-judged with the R3 tools (user decision 43); R3 = --no-ff merges in this order of seal commit S3 (parent R2), z4372-p1judge (tip above 531729f with the rev15 seal list commit; D-29 key l2b_bracket_rows_R15_3), z4372-p2chrono 5a84e94, z4372-p2t45 (tip above 4d03747 with the rev15 seal list commit), z4372-manifest 57828fc, 03_src / 02_params / runner paths diff 0, 04_scripts only chrono_rows_judge_4368.py / its README / v5_resume_4368_chrono_rows.py with unchanged row definitions, R3 blob table in the judgement appendix checked by the pre-judgement audit; R2 G-S stays 11.2, R3 G-S readers re-applied as record; D-29 L2b rows without 1 ms crawler_normal_N (V0 L2b) use the R6-B1 10 Hz bracket t_b (bracket_10Hz) on record/record.npz F_crawler [N,3] world (TruthState.F_crawler_N), t 0.1 s, normal = normalised result.json floor_plane.normal_world, phases + settings.start_t_s, decided after seeing values and disclosed; C-7b v5_hydraulics and flow items not applicable (original 5.3); C-4 off-arm liftoff_approach_slow absence allowed (R7-4, RV1-10 b); manifest regenerated with the probe and O-C5 main rows (57828fc; bundles that already had rows, their list_sha256, table_sha256 eef5129f and 72 s9_batch definitions unchanged; the OC5 bundle n 0 -> 2, rows, list_sha256 e3b0c442 -> 539fb9e9 and est_sum_s follow from the new main rows), LF blob sha f00cd5d8 in line 5 compared by blob (no -text attribute, core.autocrlf), equal on regeneration at R3; PS-c G-S run outside the batch, identity by gs_identity_start.json and result.json code_state for that row only; rev15 in the seal lists of both Chrono judges (method 1, seal first; rewrites the first sentence of rev14 R14-7 for those two tools only), other lists stay at rev12 plus seal_check.py; R10-1 LS reading on C-5 rows only; user decisions 2026-11-14 (a)..(h))` 한 줄로 쓴다.
7. `.gitattributes`에 다음 3줄을 더한다(지우는 줄 없음, R15-2 (나)):
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev15.md -text`
   - `…/v5_resume_4368_rules_rev15.sha256 -text`
   - `…/v5_resume_4368_rules_rev15_seal_candidate_draft.md -text`
8. `tools/verif/seal_check.py`와 `tools/verif/placeholder_scan.py`로 확인한다. 봉인본 5행의 자리 값(`SEAL_TIME`·`SEAL_COMMIT`)이 값으로 바뀌었는지 본다. 이 절의 안내 문구에는 이 이름들이 남는다(rev12~rev14와 같은 선례). 그 뒤 전용 worktree 브랜치에서 봉인 커밋 S3을 만든다(부모 `b9f5707`, R15-2 순서 2). 봉인 뒤 이 문서를 고치지 않는다. 고칠 것이 생기면 `v5_resume_4368_rules_rev16.md`로 새로 봉인한다.
