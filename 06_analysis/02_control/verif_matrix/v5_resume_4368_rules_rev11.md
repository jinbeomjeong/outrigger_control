# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev11 (G-S `ba2da55` 뒤 보충: 4.2 기대값의 줄 종류·T4h 찾기·명령 해시의 뜻·열린 루프 행 정체성·G-S 행 등급·G-S 출력 보관, 결과 전, 봉인)

- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev11.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev11_seal_candidate_draft.md`와 1·3·5·9행만 다르다.
- 원판 `v5_resume_4368_rules.md`(sha256 `9019b405…`), rev1(`d9094fda…`), rev2(`497e4614…`), rev3(`dad8dfa6…`), rev4(`7ea87a30…`), rev5(`452a8436…`), rev6(`809e5639…`), rev7(`e81f7d31…`), rev8(`3ecafaaf…`), rev9(`4cf7843c…`), rev10(`62a0bd8d…`)은 고치지 않는다. 이 판은 rev10(sha256 `62a0bd8dd6644f78bf37d052e884061d8c14e1cc96e2babc72a6ac0618f12c29`, 봉인 커밋 `8b4ad93`) 위에 쌓인다. 전체 sha256은 각 판의 `.sha256`에 있다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 앞 판 그대로다.
- **시점: 436.8 본 실행 결과가 없을 때(봉인 2026-11-13 13:57:36 +09:00, 봉인 커밋 ba2da55).** 436.8 본 묶음과 0단계 T-3K는 한 줄·한 행도 돌지 않았다. 있는 것은 G-S 실행뿐이다(R11-0).
- 작성: control-expert, 2026-11-13. 기준 master `8b4ad93`(rev10 봉인 커밋). 계기는 두 가지다.
  - 최종 Y `ba2da55`(rev10 반영 도구)에서 돈 G-S 두 갈래(하네스 `v5_resume_4368/gs_harness_ba2da55/`, Chrono `07_results/S9/batch_V5-RESUME-K1-GS_20261113_130358`)에서 나온 확인 사항 6건과 순서 갱신. 사용자 결정 17(2026-11-13)은 R11-1을 rev11 규칙으로 정하는 것이다(권고 "도구 결함으로 보고 수정"과 다름)
  - 그 가운데 R11-4(열린 루프 행의 커밋 정체성)는 러너 기록 추가가 필요해 사용자 결정 Q-R11-1로 올렸고, 사용자가 B(러너 기록 추가, 권고와 같음, 2026-11-13)로 정했다
- **봉인본이다.** 사용자 결정이 필요한 새 항목은 없었고, 사용자 결정 17과 Q-R11-1 = B(2026-11-13)는 R11-1~R11-7과 R11-9 결정 표에 반영했다.
- **바꾸지 않는 것**: 숫자 문턱, 등급과 우선순위, 멈춤 조건의 뜻, 묶음 범위와 행 목록, 사전 예측 값, 두 경로 요건(원판 9.2), rev1~rev10의 정의(R11-1~R11-7이 보충·고쳐 쓰는 문장만 예외). 이 판은 새 숫자를 쓰지 않는다.

## R11-0. 결과 전 근거와 공개

- 2026-11-13 확인: 436.8 본 출력이 없다. G-S `ba2da55` 결과(메인 세션 요약): 하네스는 모든 명령 rc 0, gs 판정 결측 0·S-2 0·S-11 0, 태그 대조 4건(T4h 2, R8-1 재계산 2) 일치, R7-2 첫 DONE 4건 pass, identity 11개 모두 `ba2da55`·clean, b1ddeae와 명령 해시 같음. Chrono는 12행 rc 0, `gs-check` errors 0, `law_locked` SCM 9행·L2b 형식 통과(−1 없음), judge stops 0, 봉인 확인 rev10까지 ok, b1ddeae 배치와 공통 npz 키 비트 동일, E 마스크 0x00FF0000·ok 참. `resume4368_judge record-check`는 T-3K R-0 줄에서 S-3을 냈다(R11-1).
- 읽은 것:
  - 규칙: 원판~rev10(특히 원판 4.2·6절·11.2·8.2, rev1 RV1-3.2·RV1-3.3, rev7 R7-1a·R7-1c, rev8 R8-1a, rev10 R10-3), `las_targeted_rules_rev5.md` 2.2(묶음별 LAS-b·관문·기대 태그·프리셋 패치 허용)
  - 코드(읽기만): `04_scripts/04_hydraulic/coupled/las_t3.py`(`R0`·`R0K`·`T3_BUNDLES` 상수, `LAS_ON/OFF`·`GATE_ON/OFF`, `BUNDLE_GATE`, `build_jobs`의 `t3` 필드), `verdict_runs._command_digest`(명령 배열 바이트의 SHA-256), `r79_sensor_screen.py`·`r67_g1_screen.py`의 `commands_sha256` 쓰기
  - 기록(필드 이름과 정체성 값만): `07_results/S9/batch_V5-RESUME-K1-GS_20261113_130358/batch.json` `cases[]`의 `code_at_launch` 유무, 각 행 `result.json`의 `code_state` 유무
  - 두 경로의 코드는 R11-0에 적은 것 밖에는 열지 않았다.
- 이 작성자는 경로 2 작성자가 아니다(rev2 R2-0).

## R11-1. 원판 4.2 기록 확인의 기대값은 줄 종류를 따른다 (사용자 결정 17)

- 지금: 경로 1 `resume4368_judge record-check`는 T-3K R-0 줄(LAS-b 끔·관문 끔·V0, `las_T3_R0.jsonl`)에도 `resume_k1`의 관문·LAS-b 기록이 "켬"이어야 한다고 대조해 S-3을 낸다. `b1ddeae` 출력에 같은 도구를 돌려도 같다.
- **정의**: 원판 4.2의 기록 확인(관문 요청·적용, `flat_soil_margin_order_gate`, `liftoff_approach_slow.settings`)의 기대값은 **그 줄 종류(묶음·설정·팔)의 기대 스위치**다. 원판 4.2 본문의 "프리셋 값"은 그 줄 종류의 기대 스위치가 프리셋일 때의 값이다.

| 줄 종류 | 판별 입력 | LAS-b | K1 관문 | 근거 |
|---|---|---|---|---|
| H-0 R-0 | `t3.bundle` = `R-0`, `t3.las` = `off`, `t3.gate` = `off` | 끔 | 끔 | `las_targeted_rules_rev5.md` 2.2 R-0 행, rev7 R7-1c |
| H-0 R-0K | `t3.bundle` = `R-0K`, `t3.las` = `off`, `t3.gate` = `on` | 끔 | 켬 | 같은 표 R-0K 행 |
| H-0 T-3K | `t3.bundle` ∈ {`T-3a`, `T-3b`, `T-3c`}, `t3.las` = `on`, `t3.gate` = `on` | 켬(b0) | 켬 | 같은 표 T-3K 행 |
| Chrono C-4 끔 팔 | 원판 4.2 그대로(`c2_setup.las_off` = true, `--k1-order-gate on`) | 끔 | 켬 | 원판 4.1·4.2 |
| 그 밖 하네스 줄·Chrono 행 | (위에 들지 않음) | 켬(프리셋) | 켬(프리셋) | 원판 4.2 |

- 대조할 값:
  - LAS-b 켬: `liftoff_approach_slow.settings` 9값이 프리셋 값(원판 4.2 그대로). LAS-b 끔: `settings.enable` = false만 대조한다(원판 4.2 C-4 끔 팔의 "꺼짐"과 같은 뜻).
  - 관문 켬: `k1_order_gate_effective` = true, `slope_clearance_margin.settings.flat_soil_margin_order_gate` = true. 관문 끔: 둘 다 false.
  - 관문 요청(`k1_order_gate_request`, Chrono `c2_setup.k1_order_gate`): 원판 4.2대로 `preset`(C-4 끔 팔은 `on`). 단 R-0·R-0K 줄은 기록만 한다. 이 두 묶음은 요청 인자가 아니라 프리셋 패치(`pre_las_preset_runner`·`las_t3_presets`)로 스위치를 정하기 때문이다(`las_targeted_rules_rev5.md` 2.2 "프리셋 패치 허용" 칸).
- 판별 입력의 일관성: H-0 줄에서 `t3.bundle`과 `t3.las`·`t3.gate`의 짝이 위 표와 다르거나 셋 가운데 하나라도 없으면, 기대값을 정할 수 없는 기록 결함이다. 본 실행은 원판 8.2 S-3, G-S는 S-11이다.
- 기록 사실: `b1ddeae`·`ba2da55` G-S의 R-0 줄은 `t3.las` = `t3.gate` = `"off"`이다(경로 1 작성자 리포트, 메인 세션 전달). `las_t3.py`는 `t3`에 `bundle`·`las`·`gate`를 쓴다(`build_jobs`).
- 이 판의 효과: 위 표대로면 `ba2da55` R-0 줄의 S-3은 규칙상 S-3이 아니다. 판정은 R11-7의 최종 Y G-S로만 한다.
- 결정 필요: **아니오**(사용자 결정 17).

## R11-2. T4h 찾기 (rev7 R7-1a·rev8 R8-1a 보충)

- 지금: 경로 1 gs·record-check에 `--t4h-dir`를 여러 개 주면 같은 이름 T4h npz가 다른 실행 폴더에서 먼저 잡힌다. G-S `ba2da55`에서 H-7 줄이 H-6 폴더의 같은 이름 파일을 집어 S-2 오탐이 났다.
- **정의**:
  1. 한 결과 파일의 T4h는 그 결과 파일의 **러너 관례 폴더**에서만 찾는다. 관례 폴더는 둘이다: `<결과 파일 stem>_t4h/`(run_v5·r79 계열, rev1 RV1-3.3 이름 `h6_dg3_v4on_t4h/` 등), 결과 파일과 같은 폴더의 `t4h/`(`las_t3` 계열).
  2. 관례 폴더가 하나도 없을 때만 다른 폴더를 **1개** 지정할 수 있다. 관례 폴더가 있는데 다른 폴더를 지정하거나, 2개 이상 지정하면 입력 오류다(도구 종료 2, 그 묶음 판정 안 함, 원판 8.2 S-11).
  3. 찾는 곳 전체(관례 폴더 둘, 또는 지정 폴더 1개)에서 기록된 `t4h_file` 이름의 파일이 정확히 하나여야 한다. 둘 이상이면 S-2, 없으면 S-2(rev8 R8-1a)다.
- 근거: T4h 대조(R7-1a)는 "같은 실행"의 T4h meta와의 대조다. 다른 실행 폴더의 같은 이름 파일은 같은 실행의 기록이 아니다. 이름이 겹치는 것은 정상이다(H-6·H-7은 같은 키 목록을 돈다, rev1 RV1-3.2).
- 결정 필요: **아니오**(R7-1a "같은 실행"의 적용).

## R11-3. `commands_sha256`의 뜻과 H-6·H-7 해시가 같은 것

- 기록 사실: G-S `ba2da55`와 `b1ddeae` 모두 H-6(③ 켬)과 H-7(③ 끔) 같은 키 줄의 `commands_sha256`이 같다(`1b1ad1d0…`, 메인 세션 전달).
- **정의**: 하네스 `commands_sha256`은 그 실행이 낸 **명령 배열(주기마다 다리 속도 명령)의 바이트 SHA-256**이다(`verdict_runs._command_digest`, r79·r67 스크린이 같은 함수로 씀). 제어기 설정·스위치는 이 해시에 들어가지 않는다. 그래서 ③이 명령을 바꾸지 않은 실행(③ 상계가 힘 하한에 들어가지 않은 실행)에서는 ③ 켬·끔 해시가 같다. 이것은 결함이 아니고 "③ 미작동"의 기록이다(원판 7.2 미작동의 해시 비교와 같은 뜻).
- ③ 켬·끔의 구분은 해시가 아니라 다음으로 한다:
  - 태그(원판 4.1, rev7 R7-1a, rev8 R8-1: H-6 `final_C4G2_P3_LAS_K1`, H-7 `final_C4G2_LAS_K1`)
  - `hydraulic_options.extend_start_tracked`(rev8 R8-1b: 켬일 때만 키)
  - `controller_settings["two_pressure.extend_start_rule"]`(H-6 `tracked_bound`, H-7 그 밖; rev1 RV1-3.2 "H-7은 `tracked_bound`가 아니어야 한다")
- 판정서에 H-6·H-7 같은 키의 해시 같음 수를 적는다(rev1 RV1-3.2의 H-6↔H-8 같음 기록과 같은 꼴, 멈춤 아님).
- 결정 필요: **아니오**(기록 정의의 확인).

## R11-4. 열린 루프 행(C-6·C-7)의 커밋 정체성 (원판 6절 보충, 사용자 결정 Q-R11-1 = B)

- 기록 사실(G-S `…_130358`): `run_S9.py level` 행과 L2b 행은 `batch.json` `cases[]`에 `code_at_launch`(`files`, `git`)가 있고 `result.json`에 `code_state`(`git_at_start`, `files_at_start`)가 있다. 열린 루프 행 `GS_P3a_G1_B_VB_prop_lift10`(C-6)에는 둘 다 없다. `b1ddeae` G-S도 같다(메인 세션 전달).
- 원판 6절은 커밋 칸을 "Chrono SCM(`run_S9.py level`, **열린 루프**·probe 포함)" 열에 "`batch.json` `git_at_start`, result.json 커밋"으로 정했다. 본 실행 C-6·C-7은 묶음 `C6C7`의 3행뿐이라, 같은 배치 안에서 커밋을 빌려 올 다른 행도 없다.
- 키 이름 사실: S9 `batch.json` 최상위에는 `git_at_start` 키가 없다(`…_130358` 확인). 원판 6절이 적은 "`batch.json` `git_at_start`"는 실제 키와 다르며, 이 불일치는 436.8 원판 봉인 때부터 있었다. 실제 커밋 기록은 행마다 `batch.json` `cases[].code_at_launch.git`(`head`, `clean`, `dirty`, `paths`, `taken_utc`)과 `result.json` `code_state.git_at_start`에 있다.
- **정의(사용자 결정 Q-R11-1 = B, 2026-11-13)**:
  1. 러너(`s9_batch`)가 열린 루프 행에도 level 행과 같은 꼴의 `code_at_launch`(실행 시작 때의 git head·clean·dirty 경로·파일 sha)를 `batch.json` `cases[]`에 기록 전용으로 쓴다. argv·명령 해시는 바뀌지 않아야 하고, 수정 전후 열린 루프 1행의 출력 비트 동일로 보인다. 이 수정은 최종 Y에 넣는다(R11-7, 예정).
  2. 비교 기준은 판정서에 적은 `git_at_start`(최종 Y 커밋 또는 그 위에 판정서·감사 기록만 더한 커밋, R11-7)다. 원판 6절의 "`batch.json` `git_at_start`"는 이 값으로 읽는다.
  3. 열린 루프 행: 그 행 `batch.json` `cases[].code_at_launch.git.head`가 `git_at_start`와 같아야 한다.
  4. level 행과 L2b·L1-R 행: 같은 `code_at_launch.git.head` 대조에 더해, 기존대로 `result.json` `code_state.git_at_start`와도 대조한다(그 기록이 있는 행).
  5. 기록이 없거나 다르면 원판 8.2 S-12로 멈춘다. 원판 S-12의 문장은 "한 묶음 안 커밋이 둘 이상이거나 실행 중 master 커밋·병합"이다. "커밋 기록 없음"을 S-12에 넣는 것은 이 판이 S-12의 범위를 넓히는 것이다(행의 커밋이 `git_at_start`라는 것을 보일 수 없으므로 같은 멈춤으로 다룬다).
- 결정 필요: **아니오**(사용자 결정 Q-R11-1 = B, 2026-11-13).

## R11-5. G-S 행의 등급 (원판 11.2 보충)

- 사실: Chrono judge(`chrono_rows_judge_4368`)가 G-S 행 `GS_D1S_G1_B_middle_Fs4_spJ1FL`에 G6 관문 `fail` 등급을 낸다. 10 s짜리 짧은 실행이라 완료 관문을 채울 수 없기 때문이다.
- **정의**: 원판 11.2 "G-S 결과는 판정하지 않는다"에 따라 G-S 행에서 판정 도구가 낸 등급(`pass`·`fail`·FLAG·`판정 불가`)은 쓰지 않고 멈춤 사유가 아니다. G-S에서 보는 것은 원판 11.2와 앞 판들이 정한 키 있음·형식·정체성·도구 종료 코드(멈춤 수 S-1~S-15 가운데 G-S 확인 항목)뿐이다. 판정서에는 "G-S 행 등급은 판정하지 않음"과 그 등급 수만 적는다.
- 결정 필요: **아니오**(원판 11.2의 적용).

## R11-6. G-S 절차 보충

- `chrono_rows_judge_4368 judge`는 `--out`을 꼭 준다(출력 파일이 판정서 인용 대상이다).
- **G-S 출력 보관**:
  - 하네스 G-S 출력은 `06_analysis/02_control/verif_matrix/v5_resume_4368/gs_harness_<7자리 커밋>/`(기존 `gs_harness_b1ddeae/`·`gs_harness_ba2da55/`와 같은 꼴)에 둔다.
  - Chrono G-S의 도구 출력(`gs-check` 출력, `chrono_rows_judge_4368 judge --out` 파일, `resume4368_judge gs`·`record-check` 출력 등)은 `06_analysis/02_control/verif_matrix/v5_resume_4368/gs_chrono_<7자리 커밋>/`에 둔다. Chrono 배치 폴더 자체는 `07_results/S9/`에 그대로 둔다.
  - 두 폴더는 git 추적 밖에 두고 지우지 않는다. 판정서 13절 10항에 파일마다 sha256과 배치 폴더 이름을 적는다.
- 결정 필요: **아니오**(절차 값).

## R11-7. 수정 순서와 `git_at_start` (rev10 R10-3 고쳐 씀)

- **순서**:
  1. 이 판을 봉인한다.
  2. 최종 Y에 다음을 더한다. rev10 R10-3까지의 Y 구성은 그대로다. 아래 항목은 모두 이 판 봉인 때 **아직 구현되지 않았고, 구현은 최종 Y에서 한다(예정)**.
     - 경로 1: R11-1 기대값(줄 종류), R11-2 T4h 찾기, rev11 봉인 확인.
     - 경로 2: R11-1·R11-2를 읽는 부분이 있으면 같은 문장으로 고치고, rev11 봉인 확인을 넣는다. 경로 2 작성자가 고치며 원판 9.2 독립성 요건은 그대로다.
     - 러너: R11-4 열린 루프 행 `code_at_launch` 기록(사용자 결정 Q-R11-1 = B, cad-expert, 기록 전용).
     - 봉인 확인 목록(`chrono_rows_judge_4368.py` `RULES_SEALS`, `judge4368_common.py`, `resume4368_judge` 봉인 목록, 경로 2 도구의 봉인 목록)에 rev11 파일과 그 봉인 sha를 더한다. 다르거나 없으면 원판 8.2 S-1이다.
     - G-S 출력 폴더 `v5_resume_4368/gs_chrono_<커밋>/`(R11-6)는 아직 없고, 최종 Y G-S에서 처음 만든다.
  3. 최종 Y에서 G-S 전체를 다시 돈다.
- **최종 Y에서 이 판 봉인 뒤 G-S 전체를 다시 돌린 것을 원판 11.2 충족으로 본다.** `git_at_start`는 최종 Y이거나, 그 위에 판정서·감사 기록만 더한 커밋이다(rev8 R8-4의 확인 방법 그대로).
- `ba2da55` G-S는 기록만 한다. R11-1·R11-2 밖 항목의 증거로도 **인용하지 않는다**. 그 G-S는 이 판과 그에 따른 도구 수정 전의 커밋에서 돌았으므로 원판 11.2의 "같은 커밋" 조건을 만족하지 않는다. 판정서의 G-S 근거는 최종 Y G-S 하나다.
- 결정 필요: **아니오**(메인 세션 지시의 순서, `ba2da55` 인용은 권고대로).

## R11-9. 결정 표

| 항목 | 권고·정의 | 결정 필요 |
|---|---|---|
| R11-1 4.2 기대값 | 줄 종류(묶음·설정·팔)의 기대 스위치. H-0은 `t3.bundle`·`t3.las`·`t3.gate`로 판별, R-0 끔·끔, R-0K 끔·켬, T-3K 켬·켬. R-0·R-0K 관문 요청은 기록만. 판별 입력 결함 = S-3(G-S S-11) | 결정됨: 사용자 결정 17(2026-11-13) |
| R11-2 T4h 찾기 | 러너 관례 폴더(`<stem>_t4h/`, `t4h/`)에서만, 관례 폴더 없을 때만 지정 1개, 여러 곳에서 잡히면 S-2, 없으면 S-2 | 아니오 |
| R11-3 명령 해시 | 명령 배열 바이트 SHA-256, 설정 미포함, H-6·H-7 같음 = ③ 미작동 기록, ③ 구분은 태그·`hydraulic_options`·`extend_start_rule` | 아니오 |
| R11-4 열린 루프 정체성 (Q-R11-1) | B: 러너가 열린 루프 행에도 `code_at_launch`를 기록 전용으로 쓰고(최종 Y, 출력 비트 동일 확인) `code_at_launch.git.head`를 판정서의 `git_at_start`와 대조, level·L2b·L1-R 행은 `result.json` `code_state.git_at_start`와도 대조, 없음·다름 = S-12(범위 넓힘). 원판 6절 "`batch.json` `git_at_start`"는 실제 키와 다름 | 결정됨: B(사용자 결정 2026-11-13, 권고와 같음). 고르지 않은 안: A = 원판 A-5·S-12·실행 전 감사와 다른 묶음 행의 `code_at_launch`로 간접 확인, C = 열린 루프 행은 "기록 없음"으로 공개만 |
| R11-5 G-S 행 등급 | 쓰지 않음, 멈춤 아님 | 아니오 |
| R11-6 G-S 절차 | judge `--out` 필수, 출력은 `gs_harness_<커밋>/`·`gs_chrono_<커밋>/`(추적 밖, sha 인용) | 아니오 |
| R11-7 순서 | rev11 봉인 → 최종 Y에 경로 1·2 수정·러너 기록(Q-R11-1 = B)·rev11 봉인 확인 → 최종 Y에서 G-S 전체, `ba2da55` G-S는 기록만이고 인용 안 함 | 아니오 |

### 결과 전 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-13 | 17 | record-check의 원판 4.2 기대값 문제를 rev11 규칙으로 정한다(권고 "도구 결함으로 보고 수정"과 다름) | R11-1, R11-7 |
| 2026-11-13 | Q-R11-1 | B: 러너가 열린 루프 행에도 `code_at_launch`를 기록 전용으로 쓰고 `git_at_start`와 대조한다(권고와 같음) | R11-4, R11-7 |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 파일 이름: `v5_resume_4368_rules_rev11_seal_candidate_draft.md` → `v5_resume_4368_rules_rev11.md`(같은 폴더). 초안 파일은 지우지 않고 그대로 둔다.
2. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev11 (G-S `ba2da55` 뒤 보충: 4.2 기대값의 줄 종류·T4h 찾기·명령 해시의 뜻·열린 루프 행 정체성·G-S 행 등급·G-S 출력 보관, 결과 전, 봉인)`
3. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev11.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev11_seal_candidate_draft.md`와 1·3·5·9행만 다르다.`
4. 5행("시점")에서 `SEAL_TIME`(예: 2026-11-13 10:00:00 +09:00)과 `SEAL_COMMIT`(봉인 파일을 넣는 커밋의 앞 커밋, 7자리)을 값으로 바꾼다. 이 두 이름 말고는 5행을 바꾸지 않는다.
5. 9행("봉인 준비판이다")을 다음으로 바꾼다:
   `- **봉인본이다.** 사용자 결정이 필요한 새 항목은 없었고, 사용자 결정 17과 Q-R11-1 = B(2026-11-13)는 R11-1~R11-7과 R11-9 결정 표에 반영했다.`
6. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules_rev11.sha256`에 `<sha256>  v5_resume_4368_rules_rev11.md  sealed <SEAL_TIME 값> (436.8 rev11: after G-S ba2da55 on top of rev10; 4.2 record check expects the switches of the line kind (H-0 by t3.bundle / t3.las / t3.gate: R-0 off/off, R-0K off/on, T-3K on/on; R-0 / R-0K gate request record only; missing or inconsistent kind inputs = S-3, G-S S-11); T4h looked up only in the runner convention folders (<stem>_t4h/, t4h/), one other folder only without them, several hits or none = S-2; commands_sha256 = hash of the command array bytes, equal H-6 / H-7 hashes = extend-start not acting, split by tag / hydraulic_options / extend_start_rule; open-loop rows record code_at_launch (Q-R11-1 = B, record only) and code_at_launch.git.head is checked against the judgement git_at_start (level / L2b / L1-R rows also against result.json code_state.git_at_start; batch.json has no top-level git_at_start key), missing or different = S-12 (scope widened); G-S row grades not used; judge --out required, G-S outputs in gs_harness_<commit>/ and gs_chrono_<commit>/ untracked with sha in the judgement; order rev11 seal -> path fixes, runner record and rev11 seal check in the final Y -> full G-S at the final Y = 11.2, ba2da55 G-S record only and not cited; user decisions 17 and Q-R11-1 2026-11-13; thresholds and grades unchanged)` 한 줄로 쓴다.
7. `.gitattributes`에 다음을 더한다:
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev11.md -text`
   - `…/v5_resume_4368_rules_rev11.sha256 -text`
   - `…/v5_resume_4368_rules_rev11_seal_candidate_draft.md -text`
8. `tools/verif/seal_check.py`와 `tools/verif/placeholder_scan.py`(봉인본에 `SEAL_TIME`·`SEAL_COMMIT`이 남지 않음)로 확인한 뒤 커밋한다. 봉인 뒤 이 문서를 고치지 않는다. 고칠 것이 생기면 `v5_resume_4368_rules_rev12.md`로 새로 봉인한다.
