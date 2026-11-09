# LAS-b K1 S-Ch 보충 계획 rev1 (덧붙임 판)

- 작성: control-expert, 2026-11-09
- 원판: `las_k1_sch_plan.md` sha256 `b0fe744feca6fd2e2b792a0c000e08c18eb1005f30278d1d0eeaeb2f40d46d9d`(봉인 2026-11-09 19:06:08 +09:00, 커밋 `9df5743`). **원판은 고치지 않는다.** 이 판은 원판에 덧붙인다. 두 판이 다르면 이 판이 우선하고, 이 판이 말하지 않는 것은 원판 그대로다.
- **시점: 결과 전.** S-Ch 결과(result.json)는 0건이다(배치 폴더 `batch_V5-LAS-K1-CHRONO_*` 없음).
- 이 판의 근거는 다음 셋뿐이다. 새로 본 결과 값은 없다.
  - 판정 도구(python-expert, 브랜치 커밋 `8bee8e8`, 병합 전)의 main 건조 prelaunch 결과
  - 도구 코드
  - git 기록
- 이 판이 바꾸는 것: 코드 비교 기준 커밋(R1-1), dirty 허용 목록(R1-2), 판정 도구 정체성(R1-3), 구현 해석 확인과 문구 확정(R1-4), 결측 판정값 처리(R1-5).
- 바꾸지 않는 것: 판정 짝, K1 작동 정의, prefix 규칙, E-6형·C-2형·P3·C-S·C-F 기준과 문턱, 등급, 사전 예측(원판 6.1), 2.1의 봉인 sha256 일곱 개와 DLL sha256.

## R1-0 왜 필요한가 (공개)

- 원판 2.3 (2)와 K-0a는 `git diff --quiet f25b043 HEAD -- 03_src 02_params 04_scripts`가 참이어야 한다고 정했다.
- 원판 봉인 뒤 커밋 `92d22e0`(2026-11-09 19:07:47 +09:00, S1/S2 다시 렌더)이 원판 2.3 (3)의 허용 목록 두 파일을 master에 넣었다.
  - `04_scripts/02_chrono/render_S2_gifs.py`
  - `04_scripts/02_chrono/run_S2a.py`
- 그래서 main 건조 prelaunch가 (2)에서 거짓, 종료 2가 됐다. 나머지 항목은 모두 참이었다(메인 세션 보고): HEAD `92d22e0`, dirty 0, 코드 파일 일곱 개 sha, DLL, 규칙·계획 sha.
- control-expert가 git으로 다시 확인한 사실
  - `git diff --name-only f25b043 92d22e0 -- 03_src 02_params 04_scripts`에 나오는 파일은 위 두 개뿐이다. 그래서 원판 2.1의 봉인 파일 일곱 개는 `92d22e0`에서도 blob이 같다.
  - 봉인 시점 HEAD는 `92d22e0ea5fe527ec87bdbc7ed08fa477329345f`이고, `03_src 02_params 04_scripts`의 `git status --porcelain`은 빈 목록이다.

## R1-1 코드 비교 기준 커밋 (원판 2.2 K-0a, 2.3 (2)를 대체)

- **(a)를 고른다. 기준 커밋을 `92d22e0ea5fe527ec87bdbc7ed08fa477329345f`로 바꾼다.**
  - K-0a: `git diff --quiet 92d22e0 <실행 HEAD> -- 03_src 02_params 04_scripts`가 참이어야 한다.
  - 2.3 (2): prelaunch·postrun에서 `git diff --quiet 92d22e0 HEAD -- 03_src 02_params 04_scripts`가 참이어야 한다.
- 근거
  1. **닫힌 비교가 된다.** (b)는 f25b043을 두고 두 파일을 빼는 방식이다. 이 방식은 두 파일이 앞으로 또 바뀌어도 잡지 못하는 구멍을 남긴다. (a)는 `92d22e0` 이후 코드 경로의 어떤 변경이든 `stop`으로 잡는다. 두 파일도 다시 감시 대상이 되므로 원판보다 엄격하다.
  2. **판정 대상 코드는 같다.** f25b043 → 92d22e0의 코드 경로 변경은 두 파일뿐이다. 원판 2.1의 일곱 파일(run_S9.py, las_k1_chrono_rows.py, s9_batch.py, c2.py, zero_calibration.py, hull_hook.py, late_loc_rule.py)은 blob이 같다. prelaunch (4)가 이것을 sha로 직접 확인한다. 즉 cad-expert가 f25b043에 구현한 행 정의와 실행 코드는 바뀌지 않는다.
  3. **두 파일은 S-Ch import 경로 밖이다.** `92d22e0`에서 `git grep`(`03_src`, `04_scripts`)으로 import 문을 찾았다.
     - `run_S2a`를 import하는 모듈: `04_scripts/02_chrono/render_S2_gifs.py` 122행(`from run_S2a import dt_case_name`)뿐이다.
     - `render_S2_gifs`를 import하는 모듈: `04_scripts/02_chrono/render_S3_gifs.py` 70~71행뿐이다.
     - `render_S3_gifs`를 import하는 모듈은 없다.
     - S-Ch 경로 모듈이 import하는 프로젝트 스크립트는 `run_S9`, `s9_batch`, `las_chrono_rows`, `las_k1_chrono_rows`, `s9_soil_event_screen`, `run_S6C`, `run_S8C`다. 이 목록에 위 세 모듈(`run_S2a`, `render_S2_gifs`, `render_S3_gifs`)은 없다. 근거는 `run_S9.py` 1425행, `s9_batch.py` 216·300·309·868·927·928·1048·1073·1092·1127·1396·1693·1717·1766행, `las_k1_chrono_rows.py` 63·174행이다.
     - `03_src` 안에는 두 이름을 import하는 곳이 없다.
     - 따라서 두 파일의 변경은 S-Ch 실행 바이트에 들어가지 않는다. 이 근거는 실행 전 감사가 다시 확인한다.
- 원판 2.1 표 머리말 "git blob(LF, `f25b043`)"은 "git blob(LF, `f25b043` = `92d22e0`)"으로 읽는다. 값은 그대로다.

## R1-2 dirty 허용 목록 (원판 2.3 (3)을 대체)

- **허용 목록은 빈 목록이다.** `git status --porcelain=v1 -- 03_src 02_params 04_scripts`가 한 줄이라도 내면 (3)은 거짓이다.
- 이유
  - 두 파일은 이제 커밋됐다. 다시 수정 상태가 되면 기준 커밋(R1-1) 이후 코드가 바뀐 것이므로 허용할 이유가 없다.
  - 빈 목록이 원판보다 엄격하다.
  - 지금 상태(빈 목록)에서 바로 실행할 수 있다.
- 실행 중 작업 트리 고정 규칙(원판 2.3 끝 문단)은 그대로다.

## R1-3 판정 도구 정체성 (원판 2.2에 K-0k를 더함)

- 메인 세션이 알린 도구 sha256 `19b63a35cdade865bd042db39b1b45dfa91274b927ed640f600e627ea6e44843`은 **이 판에 고정하지 않는다.** 이 판에 따라 도구를 고쳐야 하므로(R1-6) 그 값은 실행에 쓰이지 않는다.
- 대신 다음 두 가지로 도구를 묶는다.
  - **K-0k(새 항목)**: 판정 도구 sha256(원시 바이트, `-text`)이 세 곳에서 모두 같아야 한다. 다르면 `stop`이다.
    - `sch_prelaunch.json` `tool.sha256`
    - `sch_postrun.json` `tool.sha256`
    - `judge_SCh.json` `tool.sha256`(판정 실행 시 자기 파일)
  - **실행 전 감사 기록**: verif-protocol-auditor는 실행 전 감사에서 고친 도구의 커밋 해시와 sha256을 적는다. 판정서는 그 값과 K-0k 값이 같음을 적는다. 이 판 봉인 뒤 도구를 바꾸면 실행 전 감사를 다시 한다.
- 이유: 도구는 자기 sha를 담을 수 없다. 이 판에 숫자를 고정하면 R1-6 수정 뒤 판정이 반드시 `stop`이 된다. 세 기록의 일치와 감사 기록이면 "실행 전에 감사한 도구로 판정했다"를 보일 수 있다.
- K-0j(규칙·계획 sha)에 이 판 `las_k1_sch_plan_rev1.md`를 더한다. 원판 계획 sha `b0fe744f…`도 계속 확인한다.

## R1-4 구현 해석 확인 (도구 `8bee8e8`을 control-expert가 읽고 확인)

- 메인 세션이 말한 "구현자 해석 9가지"의 원문 목록은 받지 못했다. 그래서 control-expert가 도구 코드를 읽고, 원판 문구가 정하지 않은 해석 9개를 직접 골라 확인한다.
- 구현자 목록에 아래에 없는 항목이 있으면 그 항목은 이 판에서 확인되지 않은 것이다. 실행 전 감사에서 다시 묻는다.

| # | 도구의 해석 | 판정 | 계획 문구 |
|---|---|---|---|
| I-1 | prelaunch (4)는 작업 트리 원시 sha(CRLF 열)와 HEAD의 blob sha(LF 열)가 **둘 다** 맞아야 참이다 | 확인 | 원판 2.3 (4)에 "HEAD blob = 2.1 LF 열"을 더한다 |
| I-2 | **prelaunch는 행 argv 차이를 보지 않고, judge의 K-0g에서만 본다** | 확인(문구 확정) | 아래 R1-4.1 |
| I-3 | K-0a(HEAD)와 K-0b(dirty)는 result.json `git_at_start`를 쓸 수 없으면 batch.json `code_at_launch.git`의 값으로 대체한다. 둘 다 없으면 거짓이다 | 확인 | 원판 K-0a 대체 규칙을 K-0b에도 적용한다 |
| I-4 | K-0g argv: 두 argv의 길이가 같고, 다른 위치는 `--k1-order-gate`·`--case` 바로 뒤 값뿐이다. 관문 값은 실제로 `off` → `on`이어야 한다. result.json `args`의 다른 키 집합은 정확히 {`k1_order_gate`, `case`}다 | 확인 | 원판 K-0g 그대로 |
| I-5 | K-0d: prelaunch `all_ok`, postrun `all_ok`가 모두 참이고, 항목 (1)~(5)의 값이 서로 같다. (6) 규칙 sha는 각 기록의 `all_ok` 안에서 본다 | 확인 | 그대로. 도구 sha는 K-0k로 따로 본다(R1-3) |
| I-6 | K1 미작동이면 stop 사유는 K-0, K-S1, K-S2, K-4형에서만 나온다. E-6형·짝 비교는 계산해 기록만 하고 `미달`을 내지 않는다. stop이 있으면 `k1_inactive`보다 `stop`이 우선이다. `order_gate.decisions`가 없거나 None이면 `incomplete`, 빈 목록이면 미작동 판단으로 간다 | 확인 | 원판 3.2·4.4 그대로 |
| I-7 | E-6b 판정값 `grid_end_m`이 없거나 유한하지 않으면 E-6b **실패**로 센다 | **바꾼다** | R1-5 |
| I-8 | **E-6b가 0 < `grid_end_m` < 25 mm이면서 E-6a가 거짓**이면: FLAG를 달지 않고 결과를 `below_25mm_with_crawler_load`로 기록한다. E-6b 실패로는 세지 않는다. 실패는 E-6a 한 번으로 센다 | 확인(문구 확정) | 아래 R1-4.2 |
| I-9 | C-S에서 `s_motor_max_m`가 없으면 거짓(실패)으로 센다. C-F에서 기준 `F_min_after_N`이 없으면 해당 없음(통과)으로 센다. C-2형·P3의 None 처리는 rev1(K1 규칙) R1-1·R1-2 그대로다 | C-2형·P3는 확인. **C-S·C-F 결측은 바꾼다** | R1-5 |

### R1-4.1 argv 확인의 위치 (I-2 확정)

- **prelaunch는 행 argv를 보지 않는다. argv 차이의 판정은 judge의 K-0g에서만 한다.**
- 이유
  - prelaunch 도구는 run_S9를 import하지 않는다(원판 5). 그래서 행 argv를 만들 수 없다.
  - 실제 실행된 argv의 기록은 batch.json `argv`와 result.json `args`다. 실행 전 예정값보다 실행 기록이 판정 근거로 더 강하다.
- 대신 실행 전 운영 절차로 행 생성 점검을 한 번 한다(판정 항목 아님, 판정서에 기록).
  - 명령: cad-expert가 정한 `las_k1_chrono_rows.py --out <scratchpad 파일>`(Chrono-dev)
  - 조건: 종료 0, `ok` 참, 두 행 `status` `ok`
  - 이 점검이 실패하면 배치를 띄우지 않는다.

### R1-4.2 E-6b 0~25 mm이면서 E-6a 거짓 (I-8 확정)

- 원판 4.2 E-6b 행의 FLAG 조건은 "0 < 값 < 0.025 m이고 E-6a 참"이다. E-6a가 거짓이면 그 조건이 성립하지 않는다.
- 이 경우는 다음처럼 처리한다.
  - E-6b 결과는 **`below_25mm_with_crawler_load`**로 기록한다.
  - FLAG `E-6_post_event_clearance`는 달지 않는다.
  - **E-6b 실패로 세지 않는다.** 이미 E-6a 실패(끝 크롤러 하중 > 0)로 등급이 정해지므로, 같은 물리 사실을 두 번 세지 않는다.
- E-6형 등급(원판 4.2)은 E-6a에서 정한다.
  - gateon만 E-6a가 거짓이면 `미달`이다.
  - 양쪽 모두 E-6a가 거짓이면 `stop`이다.
- `grid_end_m` ≤ 0 m이면 E-6a와 관계없이 E-6b 실패다(원판 그대로).

## R1-5 결측 판정값 처리 (원판 6 SC-2·8 교훈 3을 판정값에 적용)

- 판정값이 없다는 것은 기록이 빠졌다는 뜻이다. 이것을 물리 실패(`미달`)나 통과로 세지 않고 **`incomplete`**로 처리한다(원판 4.4, 종료 3).
- 대상(어느 한 행이라도 해당하면)
  - E-6b: `p3b_ext.crawler_gap.grid_end_m`이 없거나 None이거나 유한하지 않다
  - E-6a: `step_series.npz` 끝 1.0 s 창이 비었다(표본 0)
  - C-S: `p3b.P3-5_clearance_stroke.s_motor_max_m`이 없거나 빈 목록이다
  - C-F: `p3b.P3-3_leg_force.F_min_after_N`이 없거나 빈 목록이다(기준 행 결측도 해당 없음이 아니라 `incomplete`다. 빈 집합 통과 방지)
- 원판 SC-2(1회 재실행)를 그대로 적용한다. 재실행 뒤에도 남으면 `incomplete`다.
- 값이 있고 기준이 문턱 아래인 경우(C-F 기준 < 10,414.589 N)는 원판대로 해당 없음이다.

## R1-6 판정 도구 수정 명세 (python-expert, 브랜치 `8bee8e8` 위에서)

| # | 위치 | 수정 |
|---|---|---|
| T-1 | `BASE_COMMIT` | `"f25b043"` → `"92d22e0ea5fe527ec87bdbc7ed08fa477329345f"`(전체 해시). 문서 문자열·주석의 f25b043 표기도 바꾼다(2.1 LF 값은 그대로) |
| T-2 | `ALLOWED_DIRTY` | 빈 `frozenset()` |
| T-3 | `SEALED_RULES` | `"las_k1_sch_plan_rev1.md": "<이 판 sha256>"`을 더한다(원판 계획 `b0fe744f…`는 유지). `PLAN_SHA256` 하나만 기록하던 출력 필드(`plan_sha256`)는 두 계획 sha를 모두 내도록 바꾼다 |
| T-4 | K-0k 추가 | `identity_checks`에 K-0k를 더한다: prelaunch `tool.sha256` = postrun `tool.sha256` = 실행 중 도구 sha256. 기록이 없거나 다르면 거짓(→ `stop`) |
| T-5 | E-6b 결측 | `e6b_end_gap`의 `no_value`는 실패가 아니라 `incomplete` 사유로 올린다(R1-5) |
| T-6 | E-6a 빈 창 | `window.any()`가 거짓이면 `incomplete` 사유로 올린다 |
| T-7 | C-S 결측 | `stroke_comparison`의 `s_motor_max_m missing`은 `incomplete` 사유로 올린다 |
| T-8 | C-F 결측 | `force_comparison`에서 어느 행이든 `F_min_after_N`이 없으면 `incomplete`로 처리한다. 값이 있고 기준 < 문턱일 때만 해당 없음이다 |
| T-9 | 상태 우선순위 | 결측 때문에 `incomplete`가 되면 그 묶음의 최종 `status`는 `incomplete`(종료 3)다. 다만 같은 판정에서 K-0·K-S·C-P `stop` 사유가 있으면 둘 다 공개하고 `stop`을 우선한다. 판정값이 없으면 `미달`을 낼 수 없으므로 `미달` > `stop` 규칙은 적용할 곳이 없다 |
| T-10 | 시험 | `test_las_k1_sch_judge.py`에 다음 경우를 더한다: T-1·T-2(92d22e0 기준·빈 허용 목록), T-4 불일치 → stop, T-5~T-8 각 결측 → incomplete, I-8(0~25 mm이면서 E-6a 거짓 → E-6b 실패 아님·FLAG 없음) |

- 수정한 도구는 실행 전 감사 전에 커밋한다. 감사가 커밋 해시와 sha256을 적는다(R1-3).
- 도구 경로는 `06_analysis/02_control/verif_matrix/scripts/`다. R1-1의 코드 diff 범위(`03_src 02_params 04_scripts`) 밖이므로, 도구 커밋은 K-0a를 깨지 않는다.

## R1-7 봉인 전에 본 것 (원판 7절에 더함)

- 원판 봉인 뒤 이 판 봉인 전에 본 것
  - 메인 세션 메시지: 건조 prelaunch의 항목별 참·거짓, 도구 sha256
  - 판정 도구 `8bee8e8:06_analysis/02_control/verif_matrix/scripts/las_k1_sch_judge.py` 전문(머리, 상수, prelaunch·K-0·K-S·명령·E-6·짝 비교·상태 함수)
  - `git log`, `git diff --name-only f25b043 92d22e0`, `git grep` import 조사(R1-1)
  - 커밋 `92d22e0` 메시지
- S-Ch 결과는 보지 않았다(0건).

## R1-8 판정서 공개 항목 (원판 8절에 더함)

1. 이 판의 sha256, 봉인 시각, 봉인 커밋 시각
2. R1-1 기준 커밋 변경의 이유와 import 근거. 실행 전 감사의 재확인 결과
3. K-0k 세 sha와 감사 기록 sha의 일치
4. 행 생성 점검(R1-4.1)의 명령·종료 코드·출력 경로
5. R1-4 표 I-1~I-9와 구현자 원문 목록 대조(감사에서 받은 경우)
6. R1-5 `incomplete` 사유 건수(0이어도 적는다)
