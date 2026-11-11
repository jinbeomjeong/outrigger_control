# LAS-b P5r4 + K1 재판정 규칙 덧붙임 판 rev4 (Chrono 묶음 재실행 절차, 하네스 결과 뒤·Chrono 재실행 결과 전, 봉인)

- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `las_p5r4_k1_rules_rev4.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 초안 `las_p5r4_k1_rules_rev4_draft.md`와 이 머리 두 줄만 다르다.
- 원판 `las_p5r4_k1_rules.md`(`5ee2bac0…`), rev1(`f39846d6…`), rev2(`e0a7d1e5…`), rev3(`31ba01df…`)는 고치지 않는다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 앞 판 그대로다.
- 작성: control-expert(경로 2 작성자), 2026-11-11. 기준 master `7a469f7`(작성 시점 HEAD).
- 계기: Chrono 재실행 전 감사 3 `06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/prelaunch/p5k_prelaunch_audit3.md`(2026-11-11, HEAD `7a469f7`)의 실행 전 수정 1~5, "rev4 최소 문장 초안" 8항, 확인 필요 A~D와 그 끝의 "메인 세션 처리 (감사 3)" 절의 결정.
- **시점: 하네스 결과 뒤, Chrono 재실행 결과 전.** 하네스 묶음 결과는 있다. Chrono 첫 배치 결과는 있으나 아무도 읽지 않았다(RV4-0).
- **바꾸지 않는 것**: 대상 행·키·Chrono 행 목록·argv·풀·스케줄, 판정 기준과 문턱(6.1~6.3, rev3 RV3-1·RV3-6), 비트 예측(4.4), 등급·우선순위(8.1·16.6), 멈춤 조건(8.2), 두 판정 경로 도구와 실행 도구. 이 판은 **Chrono 묶음을 새 배치로 한 번 다시 돌리는 절차**만 정한다.

## RV4-0. 결과 전 근거와 공개

### RV4-0.1 지금 있는 결과와 본 사람 (2026-11-11 23:15 +09:00, control-expert가 main checkout에서 확인)

- **하네스**: Z 묶음 줄 파일(`p5k_Z0`·`ZA`·`ZT`·`ZS`·`ZC`·`ZX.jsonl`)과 판정 출력 `judge_p5k_harness.json`이 있다. 경로 1 판정 도구는 하네스를 잠정 통과로 냈다(메인 세션 전달). 하네스 값은 메인 세션만 알고, 이 판의 작성자는 읽지 않았다.
- **Chrono 첫 배치**: `07_results/S9/batch_V5-LAS-P5R4-K1_20261111_162306/`(12행)이 있다. 그 값(결과 json·명령 npz)은 판정 도구도 사람도 누구도 읽지 않았다. 근거는 다음과 같다.
  - 경로 1 Chrono 판정 출력 `judge_p5k_chrono.json`이 없다.
  - 경로 2 출력 폴더 `verif_matrix/p5k_judge/`에는 `path2_harness.json`만 있다.
  - 첫 postrun 기록 `p5k_chrono_postrun.json`에는 정체성 필드만 있다(감사 3 기록 1).
- **Chrono 재실행 배치**: 아직 없다. `07_results/S9/`에서 이름에 `P5R4`가 든 폴더는 첫 배치와 G-S 배치(`batch_V5-LAS-P5R4-K1-GS_20261111_131719`) 두 개뿐이다.
- 이 판의 작성자는 첫 배치·하네스의 값을 읽지 않았다. 읽은 것은 감사 3 원문, 앞 판들, prelaunch 정체성 기록의 해시 필드(`chrono_rows_main.json`·`manifest.json`의 `rows_list_sha256`), 파일·폴더 이름 목록뿐이다.

### RV4-0.2 공개: 하네스 결과를 본 뒤 Chrono를 다시 돈다

- Chrono 재실행은 하네스 결과가 나온 뒤(하네스 판정 16:22, 감사 3 기록 4) 결정됐다. 원판 8.2 S-6(하네스 `통과` 뒤 Chrono)의 순서는 원래부터 그렇다.
- 재실행의 이유는 첫 배치 postrun의 정체성 `stop`(K-1)이다. 값을 보고 다시 돈 것이 아니다. 원판 8.2 끝 문장이 막는 "값·β·$N_r$·문턱·키·행을 바꿔 다시 돌림"에 해당하지 않는다. 바뀐 것은 HEAD(문서 2줄)뿐이고 행·argv·풀·스케줄은 그대로다.

## RV4-1. 첫 배치의 처리

- `07_results/S9/batch_V5-LAS-P5R4-K1_20261111_162306/`은 postrun K-1 `stop`이다. 실행 중 다른 세션이 추적 문서 2줄을 고쳐 `git status --porcelain --untracked-files=no`가 허용 밖 2줄이 됐다.
- 이 배치는 **판정에 쓰지 않는다.** 두 판정 경로를 이 배치에 돌리지 않는다. 폴더와 첫 prelaunch·postrun 기록(`p5k_chrono_prelaunch.json`, `p5k_chrono_postrun.json`)과 러너 파일(`run_chrono.done`, `run_chrono_status.txt`, `run_chrono_main.log`, `env_main_chrono_before.txt`)은 옮기지도 지우지도 않고 보존한다.
- 첫 배치와 재실행 배치의 명령 npz·결과를 대조하지 않는다. 판정 뒤의 기록용으로도 하지 않는다(사용자 결정 C).
- 판정서에는 첫 배치에서 본 것만 적는다: `progress.log` START/END `rc`, `log_errors.py` 결과, postrun 정체성(stop 사유, 허용 밖 2줄의 파일 이름).

## RV4-2. 재실행

1. 같은 행 목록으로 새 배치 폴더에 **한 번** 돌린다.
   - 행 목록: `prelaunch/chrono_rows_main.json`(파일 sha256 `cca4410bbf43de186f24c1e8e7b551c33838883bce44a180bd230cefb98a0a5d`, 목록 sha256 `rows_list_sha256` `3fdbf80ee426cb9ef4eeab13d5943d08fbef9b89d9a2ef230f13ce45c4f8de3c`)
   - argv·풀·스케줄도 같다(원판 4.3, rev3 RV3-4: 12행 모두 P).
2. `s9_batch --resume`을 쓰지 않는다. 새 배치 폴더(`batch_V5-LAS-P5R4-K1_<새 시각>`)로 처음부터 돈다.
3. 이 재실행은 원판 10.1의 "Chrono 행 실패 재실행"이 아니다. 그래서 새 배치 행에 `rerun_of`를 기록하지 않는다(사용자 결정 B). 5.2의 `rerun_of`는 12행 모두 None이다.
4. 새 배치 안에서 행이 인프라 원인으로 실패하면, 원판 10.1을 새 배치에 그대로 적용한다. 같은 argv·같은 Chrono 실행 HEAD(RV4-3)로 1회만 재실행하고, 그때는 `rerun_of`를 기록한다.

## RV4-3. 실행 HEAD

1. 하네스 실행 HEAD는 `18b1425`다(rev3 RV3-3 1). 하네스 기록과 판정은 그대로 유효하다.
2. **Chrono 실행 HEAD**는 이 판의 봉인 커밋, 또는 그 뒤 Chrono 새 prelaunch 전 마지막 커밋이다. 값은 Chrono 새 prelaunch 기록의 `head`로 읽는다. `7a469f7`로 정하지 않는다(봉인 커밋이 HEAD를 바꾼다).
3. 조건(모두 참이어야 Chrono 새 prelaunch를 시작한다)
   - `git diff --quiet 18b1425 <Chrono 실행 HEAD> -- 03_src 02_params 04_scripts 06_analysis/02_control/verif_matrix/scripts 06_analysis/02_control/verif_matrix/p5k_path2`가 참이다.
   - 5.2 코드 sha, DLL sha(`cec997d7…`), 두 판정 경로 도구 sha가 첫 Chrono prelaunch 기록과 같다.
4. **커밋 금지 구간**: 원판 11.6과 rev3 RV3-3 1의 "prelaunch~postrun"은 **각 묶음의 prelaunch부터 그 묶음의 postrun까지**로 읽는다(사용자 결정 D). Chrono 재실행에서는 Chrono 새 prelaunch부터 새 postrun까지다.
5. 판정서에 다음 두 커밋을 공개한다.
   - `7a469f7`(2026-11-11 22:51:05 +09:00, 첫 Chrono postrun 22:42:20 뒤, 문서 2줄)
   - 이 판의 봉인 커밋
6. 원판 16.2의 "실행 HEAD = prelaunch HEAD"는, 3의 조건이 참이면 `18b1425`에서 한 G-S로 충족된 것으로 본다. G-S는 다시 하지 않는다.

## RV4-4. 기록 이름과 실행 전 감사 파일

1. Chrono 새 prelaunch·postrun 기록은 새 파일에 쓴다.
   - `06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/p5k_chrono_prelaunch_r2.json`
   - `06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/p5k_chrono_postrun_r2.json`
   - 러너 파일은 `run_chrono_r2.*`, env 기록은 `env_main_chrono_r2_before.txt`다.
   - 경로 1 판정 도구의 postrun·judge에는 이 두 경로를 `--prelaunch`·`--postrun`으로 명시해 준다. 기본 이름을 쓰지 않는다.
2. K-0의 "실행 전 감사 리포트 파일"은 Chrono 재실행에서는 `prelaunch/p5k_prelaunch_audit3.md`다.
   - 감사 4를 받으면 그 원문을 같은 파일 끝에 덧붙인다. 그다음 Chrono 새 prelaunch를 실행하고, 그 뒤로 이 파일은 고치지 않는다.
   - 이 파일에는 중괄호 자리표시 토큰을 쓰지 않는다.
   - 하네스 쪽 감사 파일 `p5k_prelaunch_audit.md`는 고치지 않는다.
   - 판정서에는 두 감사 파일의 경로와 sha256을 함께 적는다.

## RV4-5. 자리표시 (원판 16.4, rev3 RV3-3)

1. 새 자리표시를 만들지 않는다(16.4 "위 표에 없는 자리를 만들지 않는다").
2. `RUN_HEAD`는 하네스 실행 HEAD(`18b1425`) 그대로 둔다. Chrono 실행 HEAD는 Chrono 새 prelaunch 기록의 `head`로 읽는다.
3. `BATCH_CHRONO`는 새 배치 폴더 경로로 다시 채운다. 다시 채우기 전에, 그 자리가 든 각 추적 밖 파일의 raw sha256을 처리 기록에 남긴다. 이것이 rev3 RV3-3 4의 **세 번째 시점**이다.
   - 판정서에 세 시점을 적는다: 마지막 추적 커밋 `e9ca269`의 blob / 첫 채움 / 재채움.
   - 첫 채움 값: `commands.md` `2a34ed60…`, `commands_path2.md` `57f04a03…`, `manifest.json` `99702564…`(감사 3, raw).
   - 다시 채울 때는 첫 배치 경로 문자열만 새 배치 경로로 바꾼다.
4. 판정 전 자리표시 점검(16.4, S-10)은 앞 판 그대로다.

## RV4-6. 도구 불변

- 두 판정 경로(경로 1 판정 도구, 경로 2 재집계 스크립트)와 실행 도구(`run_S9`, `s9_batch`, Chrono 행 모듈)는 이 판 때문에 바꾸지 않는다.
- 이 판의 sha는 도구 K-0의 봉인 규칙 상수에 넣지 않는다. 이 판의 봉인 확인(원판 8.2 S-1: `.sha256` 있음, LF sha256 같음)은 실행 전 감사와 판정서가 한다.
- 두 경로가 따로 맞출 해석 문장은 없다. 이 판은 판정 정의를 바꾸지 않는다. 경로 2는 배치 폴더 인자만 새 폴더로 바뀐다(`commands_path2.md`의 `--batch`).

## RV4-7. 실행 중·postrun 수동 확인

1. 실행 중 점검(long-running-task-monitor)마다 다음을 확인한다.
   - 새 `progress.log`에 `log_errors.py`(16.3 Chrono 명령)
   - `git status --porcelain --untracked-files=no`가 0줄
   - `git rev-parse HEAD`가 Chrono 새 prelaunch의 `head`와 같음
   - dirty나 HEAD 변화가 보이면 되돌리지 않는다. 시각과 파일을 기록하고 사용자에게 묻는다.
2. postrun 때 다음을 판정서에 적는다.
   - `git rev-parse HEAD`가 Chrono 새 prelaunch의 `head`와 같다.
   - `git log <Chrono 새 prelaunch head>..HEAD`가 비어 있다.
   - 이 두 확인 가운데 하나라도 거짓이면 판정 도구를 돌리기 전에 사용자에게 묻는다. 이 판은 그 경우의 등급을 정하지 않는다. 이 확인은 원판 11.6 준수를 손으로 보는 기록이며 새 판정 기준이 아니다(도구가 HEAD 같음을 보지 않아서 생긴 공백, 감사 3 실행 전 수정 5).

## 사용자 결정 (2026-11-11 23시경, 감사 3 "메인 세션 처리" 절)

- A: rev4로 간다. detached checkout 대안은 쓰지 않는다.
- B: 새 배치 행에 `rerun_of`를 기록하지 않는다(RV4-2 3).
- C: 첫 배치와 새 배치의 명령 npz 해시를 대조하지 않는다(RV4-1).
- D: 커밋 금지 구간은 각 묶음의 prelaunch~postrun으로 읽고, `7a469f7`과 이 판의 봉인 커밋을 판정서에 공개한다(RV4-3 4·5).
- 사전 승인 범위: 이 판은 기준·문턱을 바꾸지 않고 실행 HEAD와 재실행 절차만 정한다.

## 봉인 때 바꿀 머리 줄 (메인 세션)

봉인할 때 파일 이름을 `las_p5r4_k1_rules_rev4.md`로 바꾸고, **아래 두 줄만** 바꾼다. 이 절을 포함한 나머지 본문은 그대로 둔다.

- 1행(제목) 바꾼 뒤:
  `# LAS-b P5r4 + K1 재판정 규칙 덧붙임 판 rev4 (Chrono 묶음 재실행 절차, 하네스 결과 뒤·Chrono 재실행 결과 전, 봉인)`
- 3행(상태) 바꾼 뒤:
  `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `las_p5r4_k1_rules_rev4.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 초안 `las_p5r4_k1_rules_rev4_draft.md`와 이 머리 두 줄만 다르다.`
