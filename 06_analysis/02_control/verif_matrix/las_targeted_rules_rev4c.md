# LAS-b 표적·채택 규칙 덧붙임 판 4c (H-7′ 필드 확정: J-5·J-6, J-13 grid_vb, J-15)

작성: control-expert, 2026-11-08.

> **상태: 봉인(2026-11-08).** SHA-256과 봉인 시각은 같은 폴더 `las_targeted_rules_rev4c.sha256`에 있다. 이 파일은 더 고치지 않는다.
> - **고치는 판**: 판 4b `las_targeted_rules_rev4b.md`(`add921e4978ef16abcc22dfc88dc25e51a770dc98d2d540526f48cf6ea7a6f3f`)와 그 앞 판 전부. 여기 적지 않은 항목은 그대로다.
> - **결과를 보기 전의 확정이다.** T-3과 재개 검증의 LAS-b 실행 결과는 0줄이다. 본 것은 python-expert의 필드 이름 보고(worktree `agent-a3f0479104b4556fe`, 커밋 `4e5eecd`, 시험 233 통과)뿐이다.
> - 이 판으로 H-7′의 모든 기준선 묶음 형식이 확정된다. 판정 함수의 초안 거부는 이 판의 표대로 바꾼 뒤 풀린다.

## 1. 확정 표

| 묶음 | 판정·실패 항목 | 작동 | FAULT(C3) | G6-2 | P3-2 | READY | 행정 |
|---|---|---|---|---|---|---|---|
| J-5·J-6 (`v5/paper_runs/jp_verify/verify_v5jp_*.json` 12파일과 재실행) | 판정 = 그 사례 `rows[]`가 모두 `passed`이면 pass, 아니면 fail. 실패 항목 = `passed`가 거짓인 `item` | 2절 | 2절의 같은 사건 출처에서 `FAULT` 접두 이름. 기준 줄은 `metrics[i].events`가 전체 목록이 아니므로 3절 | 형식 없음(rev4b) | 형식 없음(rev4b) | `metrics[i].ready_s` | `metrics[i].stroke.max_m` 네 다리 중 최댓값 [m] |
| J-13 grid_vb (`v5/grid_vb/grid_r67_*.json`, `grid_r69_*.json`, `results[i].runs[j]`) | 판정 = `pass`. 실패 항목 = `gates`의 거짓 문(`no_lift`, `Fmin_after_event`, `fault0`, `end_att`, `recurrence`) | 새 실행의 `las_events`(`r67_g1_screen.screen_job`) | `fault_events`와 `warnings`의 `FAULT` 접두 이름 | 형식 없음(rev4b) | 형식 없음(rev4b) | `t_ready_back_s`(사건 기준 상대 시각, 양쪽 같은 정의). 행의 `base.t_ready`는 앞부분 실행 값이라 쓰지 않는다 | 형식 없음(rev4b) |
| J-15 (`07_results/S9/batch_V5-STAGE3_*/<case>/result.json`) | 개정 12 판정기가 쓴 `judged.verdict`·`judged.fail_items`. 줄에 판정기 이름·버전·해시를 남긴다 | `events`. `run_S9.py` 5850·5910행이 `c2.events` 전체를 상한 없이 쓴다. 15개는 그 실행의 실제 사건 수다 | `events`의 `FAULT` 접두 이름 | 형식 없음(rev4b) | `p3b.checks["P3-2_verdict"]`(`fail`만 실패) | `p3b["P3-6_ready"]["t_ready_after_loop_start_s"]` | `p3b["P3-5_clearance_stroke"]["s_motor_max_m"]` 네 다리 중 최댓값 [m] |

## 2. J-5·J-6 작동 판정의 사건 출처

- 저장 jp 기록의 `metrics[i].events`는 2~3개뿐이라 전체 사건 목록이 아니다. 그래서 작동 판정에 쓰지 않는다.
- **확정**: jp 재실행 기록에 기록 전용 `las_events`를 더한다(python-expert). 내용은 rev4b 3절과 같이 `INFO_LIFTOFF_SLOW*` 사건의 시각·이름과 `FAULT*` 사건 이름이다. 명령 불변을 단위 시험으로 보인다.
- 새 줄에 `las_events`가 없으면 판정 불가로 두고 그 묶음을 멈춘다(rev4b 3절과 같음).

## 3. 기준 줄에 전체 사건 목록이 없는 묶음의 C3

- 대상: J-5·J-6. J-7 slope는 rev4b대로 `warnings`를 쓴다.
- 기준 FAULT 집합은 그 기준 기록에서 얻을 수 있는 FAULT 이름의 합집합으로 한다. J-5·J-6에서는 `metrics[i].events`의 `FAULT` 접두 이름과 `rows[]`에서 FAULT를 다루는 항목의 실패 기록이다.
- C3 위반 = 새 줄의 `FAULT` 이름(`las_events`)이 그 합집합에 들지 않는다.
- 기준 쪽에 FAULT 출처가 하나도 없으면(필드 자체가 없으면) C3을 "형식 없음"으로 두지 않는다. 그 줄을 판정 불가로 두고 멈춘다.

## 4. 기록 전용 필드의 비트 불변 확인

- `las_events`(run_record, `screen_job`, jp 재실행)의 명령 불변은 단위 시험만으로 보이지 않는다. 다음으로도 본다.
  - 각 묶음의 미작동 줄 해시가 저장 기준 해시와 같은지(판정서 P-4, 판 3 K-5와 같은 뜻)
  - 묶음마다 미작동 줄이 하나도 없으면 그 사실을 판정서에 적는다
- 미작동인데 해시가 다르면 원판 H-6처럼 구현 결함으로 멈춘다.
