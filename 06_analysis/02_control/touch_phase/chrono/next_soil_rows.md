# K1 토양 Chrono 행 표 (cad-expert 전달용, 시작 전 결정 필요)

**상태:** 토양 하네스는 합격이다. 다만 사전 선정 규칙의 둘째 줄이 충족되지 않고(아래 1), 강체 격자에 K1 통과→실패 1행이 있어(아래 2) 사용자 결정 뒤 시작한다. 이 표는 권장안이다. `criteria.md`는 고치지 않았다.

## 1. 선정

`acceptance/judgement_partial.json`의 `soil.chrono_pick`은 1행만 낸다. 규칙의 둘째 행("첫 행과 다른 토양")에 해당하는 행이 없기 때문이다. J2는 재접근 시작이 모두 1회 이하라 K1이 작동하지 않는다.

K1 작동 후보는 G1 5행이다(재접근 ≥ 2회, 끔과 해시 다름, G1은 사건 전 명령이 끔과 같아 차이는 K1 몫).

| 순위 | 키, 사건 | 인접 최소 켬/끔 (kN) | 사건 다리 부상 합 (s) | 재접근 켬/끔 | 재READY 켬/끔 (s) |
|---|---|---|---|---|---|
| 1 | A\|G1\|FL\|Fs0, RE1bF | 35.16 / 35.16 (RL 54.93 / 40.38) | 1.075 | 4 / 5 | 25.8 / 26.1 |
| 2 | A\|G1\|FL\|Fs8, RE1bF | 38.71 / 38.71 (RL 60.99 / 48.93) | 0.966 | 3 / 4 | 27.7 / 24.2 |
| 3 | A\|G1\|FL\|Fs0, FS24 | 46.03 / 43.00 | 0.361 | 3 / 3 | 27.1 / 23.8 |
| 4 | A\|G1\|FL\|Fs8, FS24 | 52.70 / 50.13 | 0.374 | 2 / 2 | 27.8 / 27.0 |
| 5 | A\|G1\|RR\|Fs0, RE1bF | 71.80 / 71.80 (FR 107.76 / 106.93) | 0.304 | 2 / 2 | 28.2 / 28.1 |

**권장안(규칙의 나머지를 그대로 적용, 둘째 줄만 "다른 토양 없음 → 다음 순위"):** 순위 1, 순위 2, 순위 5(앞 두 행과 다른 사건 다리). 셋째 행은 K1이 시작을 0.1 s 늦추기만 하는 행이라 비용 쪽을 본다.

## 2. 시작 전에 볼 것: 격자 K1 통과→실패

`screen|bottom|2.0|ready|FR`, RE1bF, 오프셋 0.075 s: `U832_pair_union` 1.821 s > 1.8 s(끔 1.489 s), 재접근 켬 FR→FR→FR→RL, 끔 FR→RL. 사건 전 명령이 끔과 같고 보류가 이미 끝난 READY 사건이라 K1 몫이다. 하네스 값이고 Chrono가 아니다.

## 3. 공통

- 코드: `scratchpad\cad_c4g2\wt\`, 커밋 74032be, `c2.py` SHA-256 28482b8d…. 메인 트리 모듈 금지(`r8d1_td.py` 24행 같은 경로 주의).
- 켬: `C2Config().with_10hz_d1(touch_twist_hold=True, reapproach_retrigger_two_samples=True)`. 끔: `C2Config().with_10hz_d1()`. `cad_c4g1\run_s7_c4g1.py`처럼 프리셋 기본값을 바꾸는 방식으로 넣는다.
- 사례 재구성: `run_S9.py`의 `p3b_case("<CID>", "G1", "B", "top", fs)` + `soil_patch={"leg": <leg>, "set": "G1", "grid_m": P3B_PAD_GRID_M["G1"]}`, `p3b_level_argv`. `rv5_cases()`와 같은 형식이다. 지반 평지, 패드 B(`dwg_rear250`), 상단, 압력 normal, IMU ideal, seed는 P3B 상수 그대로, 유량 끔.
- 사건: `--soil-event <leg>:RE1bF:<trigger>`. 사건 시각은 mid(LOC, DONE)이고 기준 실행이 필요하다.
- 기준 실행: 끔 설정, 같은 argv에서 `--soil-event`만 뺀다. 행마다 1건이다(패치 다리·F_s가 다 다르다). 첫 DONE이 지나면 되므로 `duration_s` 60 s로 줄일 수 있다(가정, DONE이 없으면 다시 돌린다).
- 켬·끔 사건 시각은 같게 한다: 끔은 `mid@<기준 사례>`, 켬은 기준에서 읽은 값으로 `t<loop s>`. 켬의 LOC·DONE이 달라지면 그 값을 적는다.

## 4. 행

| # | 사례 이름 | F_s | 패치·사건 | 설정 | 끔 짝 | 저장 기준 |
|---|---|---|---|---|---|---|
| B1 | S9EV_G1_FLFs0_base | 0 | `FL:G1`, 사건 없음 | 끔 | − | 사건 시각 |
| 1a | S9EV_G1_FLFs0_RE1bF_on | 0 | `FL:G1`, `FL:RE1bF:t<B1>` | 켬 | 1b | |
| 1b | S9EV_G1_FLFs0_RE1bF_off | 0 | `FL:G1`, `FL:RE1bF:mid@B1` | 끔 | − | |
| B2 | S9EV_G1_FLFs8_base | 8 | `FL:G1`, 사건 없음 | 끔 | − | 사건 시각 |
| 2a | S9EV_G1_FLFs8_RE1bF_on | 8 | `FL:G1`, `FL:RE1bF:t<B2>` | 켬 | 2b | |
| 2b | S9EV_G1_FLFs8_RE1bF_off | 8 | `FL:G1`, `FL:RE1bF:mid@B2` | 끔 | − | |
| B3 | S9EV_G1_RRFs0_base | 0 | `RR:G1`, 사건 없음 | 끔 | − | 사건 시각 |
| 3a | S9EV_G1_RRFs0_RE1bF_on | 0 | `RR:G1`, `RR:RE1bF:t<B3>` | 켬 | 3b | |
| 3b | S9EV_G1_RRFs0_RE1bF_off | 0 | `RR:G1`, `RR:RE1bF:mid@B3` | 끔 | − | |

`S9EV_*`는 제안 이름이다. 비용: 사건 6건 × 건당 2.6~4.1 h, 기준 3건 × 약 1.3~2 h(60 s로 줄일 때, 추정). 배치표는 compute-scheduler-expert에 받는다.

## 5. 볼 양

`judge_chrono_soil_event`(E-1~E-7)와 다음.
- 재접근 시작 순서, `deferred:*:retrigger`, 사건 다리·인접 다리 최소 힘, F_min 아래 시간, 부상 합, 쌍 합집합(한계 1.8 s), 마지막 접촉(한계 3.0 s), 이탈 뒤 틈, 크롤러 재접촉, 재READY, 이동 압력, 끝 자세, 행정 최대, 가드 작동.
- 켬에 `INFO_TOUCH_TWIST_HOLD`가 있는지, `end_reason`, 사건 전 명령이 끔과 같은지(첫 차이 시각).
- 하네스 대조: 위 표의 값(하네스가 연약 사건에서 낙관 쪽일 수 있음, v4 4.2).
- 판정은 사전 기준을 쓴다: 판정 행 실패 0, 새 FLAG·놓침 0, 대상 행 최소 힘 개선, 다른 다리 F_min 여유 유지, READY 증가 P3-6 안.
