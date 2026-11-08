# LAS-b 표적·채택 규칙 덧붙임 판 4b (정정: dg3 v4_on 옵션 표현, J-3′ 사건 출처, J-7 slope 작동 기록, H-7′ 형식 없음 추가)

작성: control-expert, 2026-11-08.

> **상태: 봉인(2026-11-08).** SHA-256과 봉인 시각은 같은 폴더 `las_targeted_rules_rev4b.sha256`에 있다. 이 파일은 더 고치지 않는다.
> - **고치는 판**: 판 4a `las_targeted_rules_rev4a.md`(`3cbbfb5d8afda9075bf9631accf1b8bee4c1ee02edafa34a7869091175a73b15`)와 그 앞 판 전부(원판, 판 1~4, 판 3 키 목록). 여기 적지 않은 항목은 그대로다.
> - **결과를 보기 전의 정정이다.**
>   - T-3과 재개 검증의 LAS-b 실행 결과는 0줄이다.
>   - 본 것은 다음뿐이다.
>     - python-expert의 rev4a 반영 보고(worktree `agent-a3f0479104b4556fe`, 커밋 `5a080bb`): 시험 180 통과, 키 목록과 d1.jsonl 불일치 0, 저장 dg3 4기록 옵션 = HEAD VB에서 ③를 뺀 것 4/4
>     - 확인 질문 3건과 필드 이름 표
>     - 코드 `v5_options.py` 136~156·355~364·387~397행
>   - 문턱, 대상 수(T-3 315건), 멈춤 처리의 뜻은 바꾸지 않는다.

## 1. dg3 v4_on 옵션 표현 (rev4a 4절 #2)

- 저장 v4_on 기록은 ③(재신장 시작 경계)를 프리셋 패치로 켰다. 그래서 `hydraulic_options`에 ③ 키가 없다. 저장 meta의 `preset_settings["two_pressure.extend_start_rule"]` = `tracked_bound`다.
- HEAD의 `VB`는 같은 것을 옵션 `extend_start_tracked: True`로 켠다.
  - 코드에서 이 옵션이 하는 일은 셋뿐이다. 제어기 설정 `two_pressure.extend_start_rule`을 `tracked_bound`로 두기(`v5_options.py` 361~364행), 태그 `_P3`(393행), 생성 때 검사(142~143행)다.
  - 플랜트에는 영향이 없다.
  - 따라서 두 표현은 같은 제어기를 가리킨다.
- **확정**: rev4a 4절 #2의 옵션 대조에서는 아래 한 가지 차이만 허용한다. 그 밖의 차이는 모두 H-T3-3이다.

| 폴더 | 허용 차이(새 줄 옵션 − 저장 옵션) | 같은 조건 |
|---|---|---|
| v4_on | `{"extend_start_tracked": True}` 하나 | 새 줄 제어기 설정의 `two_pressure.extend_start_rule` = 저장 `preset_settings`의 값 `tracked_bound`(K-3) |
| off | 없음 | `extend_start_rule` = `constant`(K-3) |

- 이 차이 허용은 대조 규칙의 정정이다. 명령이 같은지는 여전히 해시로 판정한다(판 3 K-4·K-5).

## 2. J-3′ 사건 출처 (rev4a 5절 J-3′)

- S9 케이스 폴더에는 `controller_events.json`이 없다. 사건 출처를 **`result.json`의 `events`(시각·이름, 잘림 표시 없음)**로 정정한다.
- 이것을 `d1s_judge.py` 152행이 이름 목록으로 바꿔 `cases.<id>.events`에 쓴다. 이 값을 쓰는 것을 **승인한다.** 조건은 다음과 같다.
  1. 바꿀 때 이름을 거르지 않는다(INFO 사건 포함).
  2. 판정 시작 때 기준 줄과 새 줄 모두 `len(cases.<id>.events)` = `len(result.json["events"])`인지 대조한다. 다르면 그 줄을 판정 불가로 두고 멈춘다.
- 행정 필드 `stroke_max_mm`이 기준(저장 S-03·S-04 `d1s_judge.json`)과 새 기록 양쪽에 있으면 **J-3′ 형식은 확정**이다. 없으면 C5′-S를 형식 없음으로 두지 않고 control-expert에게 돌려보낸다.

## 3. J-7 U-3 slope V0 110의 작동 기록

- 지금 새 기록(`v5_rerun.run_record`)에는 LAS-b 작동을 판정할 사건 목록이 없다. 그러면 H-7′ 대상을 정할 수 없다.
- **확정**: `v5_rerun`에 기록 전용 필드를 더한다(python-expert).
  - 이름: `las_events`. 내용은 `INFO_LIFTOFF_SLOW*` 사건의 시각·이름과 `FAULT*` 사건 이름이다.
  - 명령은 바뀌지 않아야 한다. 단위 시험으로 필드가 있는 실행과 없는 실행의 `hash`가 같음을 보인다.
- 이 필드가 생기면 J-7 slope 형식은 확정이다. 작동은 `las_events`로 판정하고, 기준 FAULT는 지금 초안대로 `warnings`의 `FAULT` 접두 이름에서 읽는다.
- 새 줄에 `las_events`가 없으면 그 줄은 판정 불가로 두고 그 묶음을 멈춘다. "미작동"으로 치지 않는다.

## 4. H-7′ 형식 없음 추가와 남은 초안 (rev4a 5절 J-5·J-6, grid_vb, J-15)

rev4a 5절의 "형식 없음은 이 표에 적힌 것만"에 아래를 더한다. 결과를 보기 전에 기록 형식을 보고 정한 것이다.

| 묶음 | 형식 없음(확정) | 지정한 필드 | 상태 |
|---|---|---|---|
| J-5·J-6 (verify_v5jp 행, 강체 L2b) | C4′(G6-2), P3-2 | 판정·실패 항목은 행 항목 이름 목록, FAULT·작동은 그 행의 사건 목록, READY·행정은 python-expert가 실제 필드 이름을 표로 낸다 | 초안. READY·행정·사건의 필드 이름을 받으면 확정한다 |
| J-13 grid_vb | C4′, P3-2, C5′-S(행정) | FAULT = `fault_events`와 `warnings`의 `FAULT` 접두 이름. 판정·READY·작동 사건의 필드 이름은 python-expert가 낸다. **작동 판정용 사건이 없으면 J-7처럼 기록 전용 `las_events`를 더한다** | 초안 |
| J-15 (3단계 Chrono, p3b) | C4′(G6-2, P3 행에는 없음) | P3-2 = `p3b.checks`의 P3-2(실패만 실패), READY = `P3-6_ready`의 READY 시각 값, 행정 = `P3-5`의 `s_motor_max`, 사건 = `events` | 초안. 조건: "events 15"가 고정 15개로 잘린 목록이면 작동 판정에 쓰지 않는다. 전체 사건 목록(S9 `result.json` `events`)을 쓰고 2절과 같이 개수를 대조한다 |

- 초안 묶음은 확정 전까지 판정 함수가 거부한다(지금 구현 그대로).
- 확정은 control-expert가 필드 이름 표를 받아서 한다. 이 판의 "형식 없음"을 넘는 새 형식 없음이 필요하면 덧붙임 판으로 봉인한다.
