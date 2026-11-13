# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev12 (최종 Y 후보 `6e2ed8f` 점검 뒤 통일: T4h 찾기의 범위·dirty·`--git-at-start`·열린 루프 `code_state`·행 폴더 시각 창, 결과 전, 봉인 후보 초안)

- **상태: 봉인 후보 초안(봉인 전).** 봉인 전에는 실행·판정에 쓰지 않는다. 봉인 때 바꿀 머리 줄은 끝 절에 원문으로 적었다.
- 원판 `v5_resume_4368_rules.md`(sha256 `9019b405…`), rev1(`d9094fda…`), rev2(`497e4614…`), rev3(`dad8dfa6…`), rev4(`7ea87a30…`), rev5(`452a8436…`), rev6(`809e5639…`), rev7(`e81f7d31…`), rev8(`3ecafaaf…`), rev9(`4cf7843c…`), rev10(`62a0bd8d…`), rev11(`9bac4524…`)은 고치지 않는다. 이 판은 rev11(sha256 `9bac452470faf74f921aa7474b3dabad781dac1ba6c3493aff998e69e430617f`, 봉인 커밋 `4312b8e`) 위에 쌓인다. 전체 sha256은 각 판의 `.sha256`에 있다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 앞 판 그대로다.
- **시점: 436.8 본 실행 결과가 없을 때(봉인 SEAL_TIME, 봉인 커밋 SEAL_COMMIT).** 436.8 본 묶음과 0단계 T-3K는 한 줄·한 행도 돌지 않았다. 있는 것은 G-S 실행뿐이다(R12-0).
- 작성: control-expert, 2026-11-13. 기준 master `4312b8e`(rev11 봉인 커밋). 계기는 두 가지다.
  - 최종 Y 후보 `6e2ed8f` 점검에서 두 경로가 같은 규칙을 다르게 읽는 곳 5건이 나왔다. 사용자 결정 20(2026-11-13): (a) R11-2 적용 범위를 rev12 문장으로 확정한다(권고 "새 rev 없이 일반 규칙으로 읽기"와 다름), (b) dirty는 Chrono 행에서 기록만 하고 경로 2를 고친다(권고와 같음)
  - R11-2를 J-P3 로드 판독(rev3 R3-C8)에 넓히면 "기록된 T4h를 찾지 못함"의 처리가 R3-C8 문장과 부딪혀 새 판단이 필요했다. 사용자 결정 Q-R12-1로 올렸고, 사용자가 A(S-2, 권고와 같음, 2026-11-13)로 정했다
- **봉인 준비판이다.** 사용자 결정이 필요한 새 항목은 없다(R12-9 결정 표). 사용자 결정 20 (a)·(b)와 Q-R12-1 = A(2026-11-13)는 R12-1~R12-6에 반영했다. 이 줄은 봉인 때 바뀐다.
- **바꾸지 않는 것**: 숫자 문턱, 등급과 우선순위, 멈춤 조건의 뜻, 묶음 범위와 행 목록, 사전 예측 값, 두 경로 요건(원판 9.2), rev1~rev11의 정의(R12-1~R12-6이 보충·고쳐 쓰는 문장만 예외). 이 판은 새 숫자를 쓰지 않는다.

## R12-0. 결과 전 근거와 공개

- 2026-11-13 확인: 436.8 본 출력이 없다. 있는 것은 G-S 출력뿐이다(rev11 R11-7).
- 읽은 것: 원판~rev11(특히 원판 6절 커밋 행, 8.2 S-11·S-12, rev3 R3-C8, rev6 R6-C2, rev7 R7-1a·R7-5, rev8 R8-1a, rev11 R11-2·R11-4·R11-7). 메인 세션이 전한 `6e2ed8f` 점검의 두 경로 읽기 차이(각 절의 "지금" 칸). 두 경로의 코드는 열지 않았다.
- 이 작성자는 경로 2 작성자가 아니다(rev2 R2-0).

## R12-1. R11-2(T4h 찾기)의 적용 범위 (사용자 결정 20 (a), Q-R12-1 = A)

- 문장 충돌: R11-2의 제목은 "(rev7 R7-1a·rev8 R8-1a 보충)", 근거는 "T4h 대조(R7-1a)"인데, 정의 1~3은 "한 결과 파일의 T4h는 …"처럼 일반형이다.
- 지금:

| 같은 입력 | 경로 1(`h6_judge_4368`·`judge_stage1_4368`의 `rod_reading`, J-P3 로드 판독) | 경로 2(`path2_v5c` stage1) |
|---|---|---|
| 기록된 `t4h_file`을 찾지 못함 | rev3 R3-C8 구성 규칙으로 계속 | S-2 |
| 다른 실행 폴더에 같은 이름 파일 | 지정 폴더를 순서대로 돌아 처음 잡힌 파일을 씀 | 관례 폴더만, 2개 이상이면 S-2 |
| `--t4h-dir` 여러 개 | 허용 | 입력 오류 |

- **규칙 문장에서 바로 나오는 것**:
  - rev3 R3-C8의 로드 판독 입력은 "**그 줄의** T4h 기록"이다. rev7 R7-1a의 대조도 "**같은 실행**"의 T4h meta다. 두 문장 모두 그 실행 자신의 T4h만 입력으로 인정한다. 다른 실행 폴더의 같은 이름 파일은 그 줄의 기록이 아니다(이름이 겹치는 것은 정상이다, rev11 R11-2 근거).
  - 그래서 **찾는 곳**(R11-2 정의 1·2: 러너 관례 폴더 `<결과 파일 stem>_t4h/`·결과 옆 `t4h/`, 관례 폴더가 없을 때만 지정 1개, 그 밖은 입력 오류)과 **같은 이름 파일이 2개 이상 잡히면 그 줄의 기록을 정할 수 없다**는 것은 T4h를 읽는 모든 판정(R7-1a 태그 대조, R3-C8 J-P3 로드 판독, 그 밖 T4h를 입력으로 쓰는 판정)에 같게 적용한다. 이것은 R3-C8·R7-1a의 "그 줄"·"같은 실행"에서 나온다.
- **새 판단이 필요했던 것(Q-R12-1, 사용자 결정 2026-11-13 = A)**: J-P3 로드 판독에서 줄이 `t4h_file`을 기록했는데 관례 폴더에서 그 파일을 찾지 못하거나 2개 이상 잡힐 때의 처리.
  - R3-C8은 "T4h 기록이 없는 줄은 실행 구성으로 정한다"고 했다. 이 문장이 "`t4h_file` 키가 없는 줄"만 뜻하는지, "기록한 파일을 찾지 못한 줄"까지 뜻하는지 정해져 있지 않다.
  - **정의(A, 사용자 결정 2026-11-13, 권고와 같음)**: T4h를 읽는 모든 판정에 R11-2 정의 3을 같게 쓴다.
    1. 줄에 `t4h_file` 키가 없으면 R3-C8대로 실행 구성으로 정한다(J-P3 로드 판독). R7-1a 태그 대조는 rev8 R8-1(재계산)로 한다.
    2. 줄이 `t4h_file`을 기록했는데 찾는 곳에서 그 파일이 0개 또는 2개 이상이면 **S-2**로 그 묶음을 멈춘다. 기록이 가리키는 그 실행의 T4h를 정할 수 없으므로, 구성 규칙으로 대신하지 않는다(rev8 R8-1a "재계산으로 대신하지 않는다"와 같은 이유).
  - 근거: 같은 이름 파일이 섞이는 위험은 태그 대조와 로드 판독에 똑같이 있다. 기록이 있는데 못 찾는 것은 기록 결함이고, "기록 없음"과 다르다. R3-C8의 "T4h 기록이 없는 줄"은 `t4h_file` 키가 없는 줄로 읽는다.
- 결정 필요: **아니오**(사용자 결정 20 (a)와 Q-R12-1 = A, 2026-11-13).

## R12-2. Chrono 행의 dirty (사용자 결정 20 (b))

- 지금: 경로 2는 Chrono 행 `code_at_launch.git.dirty`(또는 `clean` 거짓)를 S-12로 멈출 수 있게 읽는다.
- **정의**: Chrono 행(`run_S9.py`, `run_S8C.py`, `run_S6C.py`, 열린 루프 포함)의 `batch.json` `cases[].code_at_launch.git`의 `clean`·`dirty`·`paths`는 **기록만** 한다. S-12나 다른 멈춤 사유가 아니다. 커밋 정체성은 rev11 R11-4대로 `head`(와 level·L2b·L1-R 행의 `result.json` `code_state.git_at_start`)로만 대조한다.
- 근거:
  - 원판 6절 커밋 행에서 "(+ dirty 여부)"는 **하네스 칸**("줄마다 `git_at_start`(+ dirty 여부)")에만 있다. Chrono 칸("`batch.json` `git_at_start`, result.json 커밋")에는 dirty 조건이 없다.
  - 작업 트리가 깨끗해야 한다는 조건은 하네스 H-0 K-0의 `.identity.json`(rev4 R4-C4, rev6 R6-C2 "깨끗하거나 실행 전 감사가 허용한 파일뿐")에만 있다.
- 본 실행 전 checkout이 깨끗한지(또는 허용한 파일뿐인지)는 실행 전 감사(원판 A-10, verif-protocol-auditor)가 확인한다. 판정서에는 dirty 기록 행 수와 경로를 적는다.
- 결정 필요: **아니오**(사용자 결정 20 (b), 원판 6절 문장).

## R12-3. `--git-at-start` 인자 (R11-4 보충)

- 지금: 경로 1 judge는 필수(없으면 종료 2). 경로 2 `p2_chrono judge`도 이미 필수다. 선택인 곳은 경로 2 G-S 적재 `gs-load`뿐이다(없으면 그 대조를 판정 불가로 두고 종료 1).
- **정의**: 커밋 정체성을 대조하는 두 경로의 도구는 모두 `--git-at-start <커밋>`을 **필수**로 받는다. 판정 도구뿐 아니라 **G-S 도구**(경로 2 `gs-load`, 경로 1 `gs-check`와 G-S 하위 명령)도 같다. 없으면 입력 오류다(공통 종료 코드 2, 그 묶음 판정·G-S 확인 안 함). 판정서에는 이 값이 항상 있다(원판 13절 1항, rev11 R11-4 2항). G-S에서는 최종 Y 커밋을 준다.
- 근거: R11-4의 비교 기준은 판정서에 적은 `git_at_start`이고, 이 값 없이 대조를 건너뛰면 원판 6절 커밋 확인을 하지 않은 판정이 된다. G-S에서도 R11-4 대조(행 커밋이 최종 Y와 같음)를 하려면 같은 기준값이 필요하다.
- 결정 필요: **아니오**.

## R12-4. 열린 루프 행의 `result.json` `code_state` (R11-4 4항 보충)

- 지금: 경로 2는 열린 루프 행에 `result.json` `code_state`가 있으면 대조하고, 다르면 S-12로 멈춘다.
- **정의**: R11-4 4항(`result.json` `code_state.git_at_start` 대조)은 문장 그대로 level·L2b·L1-R 행에만 적용한다. 열린 루프 행(C-6·C-7)의 커밋 대조는 R11-4 3항의 `code_at_launch.git.head`만이고, 그 행 `result.json`에 `code_state`가 있어도 **기록만** 한다(멈춤 아님). 판정서에 그 값과 `git_at_start`의 같음 여부를 적는다.
- 결정 필요: **아니오**(R11-4 문장).

## R12-5. 행 폴더 시각 창 대체 경로 (rev7 R7-5 보충, 행 로그에 `->` 줄이 없을 때만)

- 지금: 창 끝은 경로 1 `wall_s` 없으면 `est_s`, 경로 2 `wall_s`만. 폴더 맞춤은 경로 1 glob `S8/{tag}_*`·`S6/*_{tag}_*`(와 `S6/*{tag}*`), 경로 2 부분 문자열. 못 찾으면 경로 1 InputError(종료 2), 경로 2 S-11(종료 2).
- **정의**:
  1. **창**: 그 행의 `progress.log` START~END. 없으면 배치 폴더 이름의 시각 ~ 그 시각 + `wall_s`(rev7 R7-5 문장 그대로). `wall_s`도 없으면 창을 정할 수 없다(`est_s`는 실행 전 어림이라 쓰지 않는다). 창의 양 끝에 ±2 s를 둔다(rev7 R7-8).
  2. **후보 폴더**: 그 행 argv의 `--tag` 값 `<tag>`로 좁힌다.
     - `run_S8C.py` 행: `07_results/S8/` 바로 아래에서 이름이 정확히 `<tag>_<YYYYmmdd_HHMMSS>`인 폴더
     - `run_S6C.py` 행: `07_results/S6/` 바로 아래에서 이름이 `_<tag>_L1R_<YYYYmmdd_HHMMSS>`로 끝나는 폴더. `run_S6C.py`는 배치 폴더를 `<기본>_<tag>_L1R_<stamp>`로 만든다(`<기본>` = `bundleC` 또는 `bundleC_<case set>`, `run_S6C.py` 2807~2811행; 예: `07_results/S6/bundleC_d1c1_r4368gs_D1C1_top_flat_crx3_L1R_20261113_082117`, `--tag` = `r4368gs_D1C1_top_flat_crx3`). 확인 실행 꼴 `…_<tag>_check_L1R_<stamp>`는 후보가 아니다
     - 부분 문자열 맞춤과 `S6/*{tag}*` 같은 넓은 맞춤은 쓰지 않는다(다른 tag가 `<tag>`를 품는 경우를 막는다).
     - 폴더 이름의 시각이 창 안에 들고, 그 아래 `<--only 값>/result.json`이 있는 폴더만 후보다.
  3. **판정**: 후보가 정확히 하나면 그 폴더를 쓴다. 창을 정할 수 없거나, 후보가 0개 또는 2개 이상이면 입력 오류(공통 종료 코드 2)이고, 그 묶음은 판정하지 않고 멈춘다(원판 8.2 S-11). rev7 R7-5의 "판정하지 않고 멈춘다"를 이렇게 읽는다.
- 판정서에 행마다 폴더를 찾은 방법(`case_log`, `case_log_relocated`, `time_window`)을 적는다(rev7 R7-5).
- 결정 필요: **아니오**(rev7 R7-5·R7-8 문장).

## R12-6. 수정 순서와 `git_at_start` (rev11 R11-7 고쳐 씀)

- **순서**:
  1. 이 판을 봉인한다.
  2. 최종 Y에 두 경로의 수정을 더한다. rev11 R11-7까지의 Y 구성은 그대로다. 아래는 이 판 봉인 때 아직 구현되지 않았고, 구현은 최종 Y에서 한다(예정).
     - 경로 1: R12-1(T4h를 읽는 모든 판정의 찾는 곳, Q-R12-1 결과), R12-3, R12-5.
     - 경로 2: R12-1, R12-2(dirty 기록만), R12-3, R12-4, R12-5. 경로 2 작성자가 고치며 원판 9.2 독립성 요건은 그대로다.
     - 봉인 확인 목록(`chrono_rows_judge_4368.py` `RULES_SEALS`, `judge4368_common.py`, `resume4368_judge` 봉인 목록, 경로 2 도구의 봉인 목록)에 rev12 파일과 그 봉인 sha를 더한다. 다르거나 없으면 원판 8.2 S-1이다.
  3. 최종 Y에서 G-S 전체를 다시 돈다.
- **최종 Y에서 이 판 봉인 뒤 G-S 전체를 다시 돌린 것을 원판 11.2 충족으로 본다.** `git_at_start`는 최종 Y이거나, 그 위에 판정서·감사 기록만 더한 커밋이다. `6e2ed8f`를 포함해 최종 Y보다 앞선 커밋의 G-S는 기록만 하고 인용하지 않는다(rev11 R11-7과 같은 이유).
- 결정 필요: **아니오**(메인 세션 지시의 순서).

## R12-9. 결정 표

| 항목 | 권고·정의 | 결정 필요 |
|---|---|---|
| R12-1 T4h 찾기 범위 | 찾는 곳(관례 폴더, 지정 1개)과 "같은 이름 2개 이상 = 그 줄의 기록 아님"은 T4h를 읽는 모든 판정에(R3-C8 "그 줄의", R7-1a "같은 실행"). `t4h_file` 없음 = R3-C8 구성 규칙 / R8-1 재계산 | 결정됨: 사용자 결정 20 (a) |
| R12-1 Q-R12-1 | A: 기록한 `t4h_file`이 0개·2개 이상 잡히면 J-P3 로드 판독에서도 S-2(구성 규칙으로 대신하지 않음), R3-C8 "T4h 기록이 없는 줄" = `t4h_file` 키 없는 줄 | 결정됨: A(사용자 결정 2026-11-13, 권고와 같음). 고르지 않은 안: B = J-P3 로드 판독은 구성 규칙으로 계속하고 수만 기록, C = J-P3 로드 판독만 그 줄 `판정 불가` |
| R12-2 dirty | Chrono 행 `clean`·`dirty`·`paths`는 기록만, 멈춤 아님. 원판 6절 dirty는 하네스 칸에만, clean 요구는 H-0 K-0에만. checkout 깨끗함은 실행 전 감사 | 결정됨: 사용자 결정 20 (b) |
| R12-3 `--git-at-start` | 두 경로의 판정 도구와 G-S 도구(`gs-load`, `gs-check` 등) 모두 필수, 없으면 입력 오류(종료 2) | 아니오 |
| R12-4 열린 루프 `code_state` | 기록만, 대조는 `code_at_launch.git.head`만 | 아니오 |
| R12-5 시각 창 대체 | 창 = START~END, 없으면 폴더 시각 + `wall_s`(`est_s` 안 씀) ±2 s. 후보 = `S8/<tag>_<stamp>`, `S6/…_<tag>_L1R_<stamp>`(정확 맞춤, `_check_L1R_` 제외) + `<--only>/result.json`. 0개·2개 이상·창 불가 = 입력 오류(종료 2, S-11) | 아니오 |
| R12-6 순서 | rev12 봉인 → 최종 Y에 두 경로 수정·rev12 봉인 확인 → 최종 Y에서 G-S 전체 | 아니오 |

### 결과 전 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-13 | 20 (a) | R11-2 적용 범위를 rev12 문장으로 확정한다(권고 "새 rev 없이 일반 규칙으로 읽기"와 다름) | R12-1 |
| 2026-11-13 | 20 (b) | dirty는 Chrono 행에서 기록만 하고 경로 2를 고친다(권고와 같음) | R12-2, R12-6 |
| 2026-11-13 | Q-R12-1 | A: 기록한 `t4h_file`이 0개·2개 이상 잡히면 J-P3 로드 판독에서도 S-2(권고와 같음) | R12-1 |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 파일 이름: `v5_resume_4368_rules_rev12_seal_candidate_draft.md` → `v5_resume_4368_rules_rev12.md`(같은 폴더). 초안 파일은 지우지 않고 그대로 둔다.
2. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev12 (최종 Y 후보 `6e2ed8f` 점검 뒤 통일: T4h 찾기의 범위·dirty·`--git-at-start`·열린 루프 `code_state`·행 폴더 시각 창, 결과 전, 봉인)`
3. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev12.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev12_seal_candidate_draft.md`와 1·3·5·9행만 다르다.`
4. 5행("시점")에서 `SEAL_TIME`(예: 2026-11-13 10:00:00 +09:00)과 `SEAL_COMMIT`(봉인 파일을 넣는 커밋의 앞 커밋, 7자리)을 값으로 바꾼다. 이 두 이름 말고는 5행을 바꾸지 않는다.
5. 9행("봉인 준비판이다")을 다음으로 바꾼다:
   `- **봉인본이다.** 사용자 결정이 필요한 새 항목은 없었고, 사용자 결정 20 (a)·(b)와 Q-R12-1 = A(2026-11-13)는 R12-1~R12-6과 R12-9 결정 표에 반영했다.`
6. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules_rev12.sha256`에 `<sha256>  v5_resume_4368_rules_rev12.md  sealed <SEAL_TIME 값> (436.8 rev12: after the final Y candidate 6e2ed8f check on top of rev11; R11-2 lookup places and the several-hits rule apply to every judgement that reads a T4h (R3-C8 "that line", R7-1a "same run"), no t4h_file = R3-C8 configuration rule / R8-1 recompute, a recorded t4h_file found 0 or 2+ times = S-2 also for the J-P3 rod reading (Q-R12-1 = A); Chrono code_at_launch clean / dirty record only (dirty is in the harness column of the original 6 only), checkout cleanliness by the pre-run audit; --git-at-start required on both paths for judge and G-S tools, missing = input error; open-loop result.json code_state record only; R7-5 time-window fallback: START..END else folder stamp + wall_s (no est_s) +- 2 s, exact folder names S8/<tag>_<stamp> and S6/..._<tag>_L1R_<stamp> (no _check_L1R_) with <--only>/result.json, none / several / no window = input error (S-11); order rev12 seal -> both path fixes and rev12 seal check in the final Y -> full G-S at the final Y = 11.2; user decisions 20 (a), 20 (b) and Q-R12-1 2026-11-13; thresholds and grades unchanged)` 한 줄로 쓴다.
7. `.gitattributes`에 다음을 더한다:
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev12.md -text`
   - `…/v5_resume_4368_rules_rev12.sha256 -text`
   - `…/v5_resume_4368_rules_rev12_seal_candidate_draft.md -text`
8. `tools/verif/seal_check.py`와 `tools/verif/placeholder_scan.py`(봉인본에 `SEAL_TIME`·`SEAL_COMMIT`이 남지 않음)로 확인한 뒤 커밋한다. 봉인 뒤 이 문서를 고치지 않는다. 고칠 것이 생기면 `v5_resume_4368_rules_rev13.md`로 새로 봉인한다.
