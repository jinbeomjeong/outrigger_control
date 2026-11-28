# 436.9 판 8 5단계 G′ V0 A/A 멈춤 원인 분석(결과 본 뒤의 분석, 기록)

작성: dynamics-expert, 2026-11-28. **이 분석은 5단계 결과를 본 뒤에 했다.** 판정이 아니라 기록이다. 재실행은 하지 않았다. 판정 대상인 저장 출력 세 개와 키 파일만 읽었다. P8-2 경로 2 자료는 열지 않았다.

## 0. 결론 요약

| 질문 | 답 |
|---|---|
| 도구가 센 "E A/A 실패 2"의 정체 | **판정 도구 결함(슬롯 이름 충돌)이다.** E층 `a_phase` 슬롯 2개(줄 10, 28)가 같은 이름을 쓰는 N층 `b_shape` 슬롯(줄 173, 179)의 실패 짝을 빌려 센 값이다. control-expert가 판정서 초안 2절(ba2f09f1)에서 찾은 내용과 같다. 아래 1절에서 따로 재현했다 |
| E층 자기 짝 | 24슬롯 모두 같은 층 짝이 있고(n_AA,E = 24), 실패는 **0**이다(기록) |
| 결함이 없었다면 | 그래도 **멈춤**이다. N층 A/A가 11/310이고 CP95가 0.0581로 0.025를 넘는다(봉인 규칙 코드로 재계산, 기록). 도구 값 10/310도 CP95 0.0541이라, E 점검을 통과했더라도 N에서 멈췄다. 멈춤 사유 문면만 틀렸다 |
| 실제 실패의 기전 | 결정적 하네스에서 **10 Hz 압력 표본 위상**에 따라 결과가 갈린다. (a) 앞다리 RE1bF에서 패드가 10 Hz 표본 직후 0~3 ms 안에 들리면 헤드압 D1 단계 진단이 가짜 FAULT를 낸다(`FAULT_HEAD_PRESSURE` D1_step, 3건). (b) 한 번만 나는 경고 `WARN_D1_IMU_GYRO_MISSING`이 위상에 따라 생기거나 안 생겨 J7 집합이 갈린다(8건) |
| 판 5 선례와 같은 꼴인가 | 아니다. 판 5는 seed(잡음)에 따라 갈린 LEVEL 완료 교착이었다. 이번 것은 seed가 없는 위상 결정적 진단 FAULT와 경고 집합 차이다. "작은 섭동에 이산 결과가 뒤집혀 A/A 바닥이 생긴다"는 점만 같다 |
| 층 E 고유 성질인가 | E층에서는 A/A 실패가 관측되지 않았다(0/24). 실제 실패는 모두 N층에 있고, V0 기준선 자체의 표본 위상 민감도다. 그중 (b)는 판정 정의 문제(J7이 위상에 따라 뒤집히는 진단 경고를 셈)이기도 하다 |

## 1. 도구 결함 재현(기록)

방법은 다음과 같다.
- T8⁗(`ed8-judge4` 7ea78232)의 라이브러리 함수를 읽기 전용으로 import해서 339슬롯을 다시 만들었다(`jp3_ed8_judge.slot_inputs`, `jp3_ed8_rules.aa_pair_of`·`stage5_selection`, `unit_item_verdicts`). CLI는 돌리지 않았고 판정 도구는 아무 파일도 쓰지 않았다.
- **공개**: 지휘 메시지("판정 도구를 돌리지 말고")를 받기 전에 이 라이브러리 호출을 이미 했다. 그래서 C-J 항목 판정은 판정 도구 함수가 계산한 값이다. 손 대조(3절 (3))는 판정 코드 없이 따로 했다.

| 항목 | 값 |
|---|---|
| 키 줄 / 고유 `slot` 이름 | 339 / 291. 겹치는 이름 48개는 모두 (`a_phase`, `b_shape`) 쌍 |
| 원인 줄 | `jp3_ed8_rules.py:464` `pairs = {slot["slot"]: ...}`. 같은 이름이면 정렬상 뒤에 오는 `b_shape` 짝이 남는다. 세기(`_layer_counts` 440행, `aa_summary` 426행)는 슬롯마다 `pairs[slot["slot"]]`을 읽어, 그 짝을 두 슬롯 모두에 쓴다 |
| 도구 이름 그대로 재계산 | stop, "E A/A failures 2 >= 2", E 2/22, N 10/310. `ho_k_selection.json`과 같다(`rerule_unique_names.json` `tool_names`) |
| 고유 이름(`<source>\|<slot>`)으로 재계산 | stop, "N A/A CP95 0.058051 > 0.025", E 0/24(CP95 0.117), N 11/310 |
| 도구 E 실패 2의 출처 | E 줄 10(`a_phase` bottom\|FL\|Fs2\|RE1bF\|level, o 0.0125)은 줄 173 짝을 받았다. E 줄 28(`a_phase` bottom\|FR\|Fs0\|RE1bF\|level, o 0.0625)은 줄 179 짝을 받았다. 두 E 슬롯의 자기 짝은 통과다 |
| 같은 원인의 다른 영향 | E 줄 34·47이 `b_shape`의 `none_in_layer`를 받아 n_AA,E가 22가 됐다. N층에서는 `a_phase` 줄 5·29(기준 실패)와 53·89의 자기 실패가 지워졌고, 줄 190의 실패가 `a_phase` 같은 이름 슬롯에 한 번 더 세어졌다. 그래서 N은 10/310(정확한 값 11/310)이다 |
| `aa_shape_record` | 이름 사전으로 세지만 합계는 같다(harsher 10쌍/실패 1, milder 15/0). 자기 짝으로 세면 same 309/10, harsher 10/1(줄 173), milder 15/0 |

## 2. 도구가 센 두 실패의 실제 짝(N층 `b_shape`)

출처는 `pair_lines.json`이다. 시각은 절대 시각[s], 힘은 실린더 순 힘[kN](압축 +, −0.72·−1.05 kN은 들린 다리의 로드측 장력 바닥), 자세는 기체 좌표계 roll·pitch[°](pitch + = 앞내림)다. 사건 다리 대각은 FL↔RR, FR↔RL이다.

### 2.1 줄 173: bottom, FL, F_s 2 kN, level 시점, RE1bF

| | 기준 V0(o) | 처리 V0(o″), 첫 시도, 같은 N층 |
|---|---|---|
| 오프셋 / 형상 | 0.075 s / 25 mm·0.05 s | 0.0875 s / 30 mm·0.04 s(형상도 바뀜, harsher) |
| t_event / FL 들림 | 24.675 / 24.692(표본 위상 0.092) | 24.687 / **24.700(위상 0.000)** |
| 재접근 시작 | [0.03 FL] → N | [0.01 FL] → N(대각 시작 없음) |
| 사건 | WARN_D1_IMU_GYRO_MISSING(24.8) | 24.8 `FAULT_HEAD_PRESSURE:RL`(사유 D1_step), 25.8 `WARN_FAULT_REGROUND_ABORT:protected_leg_low` |
| 끝 단계 / READY 복귀 | ready / 23.33 s 뒤 | **fault** / 없음 |
| 대각 RR 들림 | 합 0.677 s, 마지막 접촉 1.175 s | **59.8 s**(끝까지 뜸), pair_union 60 s |
| 끝 자세 | (0.0223, −0.0319)° | (−0.4324, 0.2207)° |
| 실패 항목(도구 문면) | – | J1 게이트 Fmin_after_W·U832_last_touch·U832_pair_union·end_att·fault0, J2 F 50620 N → −720 N, J4 ready → fault, J5 t_back 23.33 → None, J6 att_end 0.0319 → 0.4324, J7 FAULT_HEAD_PRESSURE:RL·WARN_FAULT_REGROUND_ABORT |

### 2.2 줄 179: bottom, FR, F_s 0 kN, level 시점, RE1bF 30 mm·0.04 s

| | 기준 V0(o) | 처리 V0(o″) |
|---|---|---|
| 오프셋 | 0.025 s | 첫 후보 0.0125는 E라 엇갈림. 둘째 **0.0875 s**(형상 같음) |
| 재접근 | [0.07 FR, 0.97 RL] → N | [0.01 FR] → N |
| FR 들림 | 24.725 + 0.013(위상 0.038) | **24.800(위상 0.000)** |
| 사건 | GYRO_MISSING | `FAULT_HEAD_PRESSURE:FL`·`:RR`(둘 다 D1_step) |
| 끝 단계 | ready, 21.98 s 뒤 복귀 | **fault**. 대각 RL 끝까지 뜸, pair_union 60 s, n_rev 22 → 2 |
| 실패 항목 | – | J1 위 다섯 게이트, J2 32460 N → −720 N, J4 ready → fault, J5 21.98 → None, J6 0.0308 → 0.5171, J7 FAULT_HEAD_PRESSURE:FL·RR |

### 2.3 기전

**사실**(1356줄 전수, `stage5_line_census.csv`·`front_re1bf_lift_phase.csv`·`fault_line_slots.csv`)
- 5단계 1356줄에서 `final_phase = fault`는 **8줄**이다. 8줄 모두 다음 조건을 함께 만족한다.
  - 앞다리 RE1bF, 오프셋 0.0875 s
  - 사건 다리 들림이 10 Hz 표본 시각 뒤 **0.000~0.003 s**
  - 사유 `INFO_HEAD_PRESSURE_FAULT_REASON:<인접 다리>:D1_step`
- 다른 오프셋(0, 0.0125, …, 0.075)과 뒷다리 사건, FS24·G4에서는 FAULT가 0이다.
- 앞다리 RE1bF o 0.0875의 FAULT 비율은 형상·시점에 따라 갈린다.
  - 30 mm·0.04 s: 4/5(들림 위상 0.000~0.001)
  - 기본 30 mm·0.05 s, ready 시점: 4/13. 모두 F_s ≤ 2 kN(0·0·1·2 kN)이다.
  - 기본 형상, level 시점: 0/11
  - 25 mm·0.05 s: 0/4(들림 위상 0.004)
- 5단계 기준 실패 3슬롯(줄 5, 29, 181)도 모두 이 FAULT다(o 0.0875 기준 줄).
- 저장 V0 본 위상 {0, 0.025, 0.05, 0.075}에서는 들림 위상이 0.012~0.092 s라, 이 창(0~3 ms)이 표본에 들어간 적이 없다.
- 판정 규칙(C8 `two_pressure.py` 2034~2096행)
  - 10 Hz 한 주기 헤드압 변화 |Δp_h| > `max_step_Pa`(클래스 기본 100 bar. 프리셋 값은 확인하지 않음)이면 단계 후보가 된다.
  - 크롤러가 뜬 뒤에는 D1''가 적용된다. IMU 잔차 r = ΣF − M_eff f_z의 주기 변화가 0.5·|Δp_h|A_p 이상이면 "설명 안 됨"으로 FAULT다.
  - 이 줄들은 모두 `WARN_D1_IMU_GYRO_MISSING`이다. 곧 지레 보정 (α×r)_z 없이 f_z를 그대로 썼다.

**[추정] 기전**
- 앞 패드 지지 상실 뒤 몸체가 대각축(사건 다리-대각 다리 선의 직교 방향)으로 흔들리며 하중이 인접 두 다리로 빠르게 옮겨간다.
- 들림이 표본 시각 바로 뒤(0~3 ms)이면, 앞 표본은 사건 전 정적 하중이고 다음 표본(+0.1 s)은 전이 한가운데라 인접 다리 한 주기 Δp_h가 가장 커진다.
- 같은 순간 회전 가속이 크다. 그런데 지레 보정이 없는 f_z(10 ms 부분 평균)는 질량중심 수직 가속과 다르다. 그래서 r이 0.5·|Δp_h|A_p 넘게 변해(뒤 ø110이면 약 48 kN 이상, 앞 ø130이면 약 66 kN 이상) 하중 재분배가 아니라 센서 도약으로 판정된다.
- 다른 위상에서는 전이가 두 주기에 나뉘어 한 주기 변화가 작거나, 표본이 전이 앞뒤를 덜 가른다.
- 더 빠른 램프(0.04 s)는 들림을 3~4 ms 앞당겨 같은 표본에서 들림을 잡게 하고(재접근 시작 0.11 → 0.01) 동적 하중도 키운다.
- ready 시점(잠긴 다리 ζ 0.03, 이동 중 0.10보다 작음)과 작은 F_s(실 마찰 소산 작음)는 흔들림 진폭을 키우는 쪽이다.
- FAULT 뒤에는 재접지가 `protected_leg_low`로 중단되고, 대각 다리가 끝까지 뜬 채 끝난다.

**아닌 것**
- RE1bF 조기 인계(E층 기전)가 아니다. FAULT는 사건 뒤 첫 표본(+0.1 s)에서 나고, 대각 재접근은 시작조차 하지 않는다.
- LEVEL 교착도 아니다.

## 3. 나머지 실패와 손 대조

### (2) 자기 짝이 남은 N층 실패(도구 출력 기준: 고유 이름 6, `b_shape` 3)

| 줄 | 원천 | 사건·시점 | o → o″ | 실패 항목 | 꼴 |
|---|---|---|---|---|---|
| 112 | a_phase | top FR Fs2 FS24 ready | 0.0125 → 0.0625 | J7 WARN_D1_IMU_GYRO_MISSING | (b) |
| 120 | a_phase | top FR Fs8 FS24 ready | 0.0125 → 0.0375 | J7 GYRO_MISSING | (b) |
| 228 | c_fs | bottom level FR FS24 Fs1 | 0.0 → 0.0625 | J7 GYRO_MISSING | (b) |
| 252 | c_fs | bottom level RR RE1bF Fs1 | 0.0125 → 0.0 | J7 GYRO_MISSING | (b) |
| 270 | c_fs | bottom ready FR RE1bF Fs1 | 0.05 → **0.0875** | J1·J2(35.65 kN → −0.72)·J4·J5·J6(0.0296 → 0.5267)·J7 FAULT_HEAD_PRESSURE:RR | (a) |
| 280 | c_fs | bottom ready RL RE1bF Fs3 | 0.0125 → 0.0 | J7 GYRO_MISSING | (b) |
| 173, 179 | b_shape | 2절 | | | (a) |
| 190 | b_shape | bottom RL Fs2 RE1bF ready, 30 mm·0.04 s | 0.025 → 0.0875 | J7 GYRO_MISSING | (b) |
| 53, 89 | a_phase | bottom RL Fs0 / RR Fs4 RE1bF ready | → 0.0875 | J7 GYRO_MISSING | (b), 도구에서 지워짐 |

(b) 기전(사실 + [추정])
- `WARN_D1_IMU_GYRO_MISSING`은 D1''가 단계 후보를 처음 평가할 때 한 번만 나는 경고다(`two_pressure.py` 2112~2113).
- 뒷다리 RE1bF에서는 이 경고가 표본 경계 근처 위상(0.0, 0.0125, 0.0875)에서만 생긴다.
  - level: 0.0에서 3/19, 0.0875에서 6/26, 그 밖 0
  - ready: 0.0에서 2/12, 0.0125에서 4/28, 0.0875에서 12/34
- 한 주기 Δp_h가 100 bar를 넘는지가 위상에 따라 갈린다는 뜻이다[추정]. 단계가 설명돼 FAULT는 아니다. 물리 응답은 같고 진단 경고 유무만 달라 J7 집합 차이가 실패로 세어진다.

### (3) `a_phase` E층 슬롯의 자기 짝: 저장 jsonl로 다시 셀 수 있는가

셀 수 있다. 키 파일 `aa_order`의 job과 jsonl 줄 `job`(mask·t4h_dir 뺀 사전)을 맞추면 짝이 1:1로 찾아진다.
- 판정 코드 없이 손 대조 스크립트로 셌다(`scripts/s10_hand.py`, `aphase_E_hand_check.csv`).
  - 층은 6.3 문면대로 정했다: 대각 시작 0 ≤ t, round(t, 3) ≤ 0.450.
  - 비교한 것은 이산 필드뿐이다: 끝 단계, fault_events, 사건 게이트 전부, 경고 집합.
- 결과(기록, 판정으로 쓰지 않음): `a_phase` E층 슬롯 9개(줄 4, 10, 11, 16, 17, 22, 28, 34, 47)는 모두 같은 층 짝이 있고, 이산 필드 차이는 **0건**이다.
- 한계: 연속 항목(J2 최소 힘, J5 복귀 시간, J6 끝 자세, J8 n_rev) 문턱은 손으로 보지 않았다.
  - 앞의 라이브러리 계산(판정 도구 함수)으로는 9개 모두 통과였다.
  - 복귀 시간 차는 최대 0.97 s(줄 47: 22.24 → 23.21 s)다.

## 4. 원인 분류

1. **구현 결함(판정 도구)**: 슬롯 식별자가 고유하지 않다. 명세 7.2는 원천 표지와 슬롯 키를 함께 정렬 키로 쓰지만, 도구는 `slot`만을 식별자로 쓴다. 멈춤 사유 "E A/A failures 2"는 이 결함의 산물이다.
2. **V0 기준선 위상 민감도(N층)**: 결정적 하네스의 10 Hz 표본 위상에 따른 가짜 D1 FAULT(3)와 경고 플립(8). E층 고유 성질로는 관측되지 않았다.
3. **판정 정의**
   - (가) J7이 위상에 따라 뒤집히는 1회성 진단 경고를 실패로 센다.
   - (나) A/A 층 짝짓기가 후보 V0(o″) 자신의 결과(대각 재접근 시작)로 층을 정한다. 그래서 FAULT 줄은 구조상 항상 N이 된다. E층 A/A는 이 실패형을 볼 수 없게 검열된다. 이번 실행에서 실제로 검열된 FAULT 후보는 0건이다(줄 174의 FAULT 후보는 결정된 시도 뒤라 무시됨).
   - (다) `b_shape` A/A 짝은 위상과 함께 형상도 바꾼다(줄 173 harsher). 순수 A/A가 아니다.

## 5. 판 9 설계에 주는 함의(선택지만, 결정은 사용자 몫)

| 주제 | 선택지 |
|---|---|
| 슬롯 식별 | A. 슬롯 ID = (원천, 슬롯 키, 줄 번호)로 바꾸고, 이름 고유성 단언 시험을 넣는다. B. 키 파일 `slot`에 원천 접두를 넣는다. 두 경우 모두 8단계 경로도 같이 고친다(5절 끝) |
| D1 가짜 FAULT | A. 플랜트·진단은 그대로 두고 0.0875 창을 "기준 실패"로 기록만 한다(현행). B. 지레 보정 입력(자이로 부분 평균)을 하네스에서 공급하는지 확인한 뒤 D1''를 다시 판단한다(제어·유압 검토). C. 새 위상 O′에서 표본 경계 3 ms 안 들림이 생기는 오프셋을 따로 층으로 둔다 |
| J7 경고 플립 | A. A/A·C-J J7에서 `WARN_D1_IMU_GYRO_MISSING` 같은 1회성 진단 경고를 기록 항목으로 내린다. B. 그대로 세고 N 문턱(CP95 0.025)을 바닥에 맞게 다시 정한다(stats) |
| 층 E 정의 | A. 6.3 유지(이번 E A/A 0/24). B. A/A 짝짓기 층을 후보 결과가 아니라 처리 전 공변량(기준 V0(o)의 층)으로 고정해 FAULT 후보를 E에서 빼지 않는다 |
| A/A 문턱 | N 11/310이면 CP95 0.058이다. 현행 0.025를 지키려면 x_AA ≲ 3이 필요하다. 위 J7·D1 처리 없이는 다시 멈출 공산이 크다[추정] |
| 원천 선택 | A. `b_shape` A/A 후보를 같은 형상으로 한정한다. B. 새 위상 O′을 표본 경계(0.0875 = 경계 −12.5 ms)에서 떼어 둔다. C. 현행 유지 + 위상·형상 기록 |

## 가정
- 10 Hz 표본 시각은 0.1 s의 정수배라고 보았다(저장 사건 시각 24.8·44.8 등에서 확인).
- 들림 시각은 `t_event_s` + `lifts[사건 다리].first_s`다(저장값 반올림 1 ms).
- `max_step_Pa`는 클래스 기본 100 bar로 썼다. R8 프리셋 값은 확인하지 않았다.

## 메인 세션 권고(진단 실행, 띄우지 않음)
2.3의 [추정]을 확정하려면 시계열이 필요하다. 다음 4개 job을 D1 내부 기록과 함께 다시 돌린다.
- 기록할 것: 10 Hz 헤드·로드압 표본, ΣF, f_z, r 변화, 문턱 0.5·|Δp_h|A_p, 자이로 부분 평균 유무.
- 대상 job
  1. 줄 179 후보(bottom FR Fs0 level 30 mm·0.04 s o 0.0875, FAULT)
  2. 같은 형상 o 0.075(통과)
  3. 줄 173 짝 기준(25 mm·0.05 s o 0.0875, 통과)
  4. 줄 270 후보(bottom ready FR Fs1 o 0.0875, FAULT)
- 예상 시간: job당 약 15~60 s(저장 wall_s 기준), 전체 수 분.
- 실행 명령: run_v5에 단일 job과 trace를 주는 방법은 구현 담당(python-expert)이 정해야 한다. T4h는 V0 설정에 쓰이지 않는다.
- 출력: `ed8_design/stage5_aa_cause/diag/` 권장.

## 위임 필요
- python-expert(T8 판정 도구)
  - `jp3_ed8_rules.stage5_selection`·`_layer_counts`·`aa_summary`, `jp3_ed8_judge.aa_shape_record`가 `slot` 이름을 식별자로 쓰는 문제를 고친다.
  - **8단계 경로도 같은 결함이 있다** [확인 필요]: `jp3_ed8_rules._unit_layer`(587행)가 `slot_layers`를 이름으로 찾고, `first_aliases`도 이름 목록이다. `heldout_judgement`는 `"row": unit["slot"]`으로 병합한다(557~559행). 그래서 `a_phase`·`b_shape` 같은 이름 단위가 다른 슬롯의 층을 받거나 한 병합 단위로 묶일 수 있다.
- verif-protocol-auditor: 5단계 판정서에 "멈춤은 유지, 사유 문면 정정(N CP95)"을 어떻게 적을지, 그리고 이 분석이 결과 뒤 분석이라는 공개 문면을 감사한다.

## 근거 파일(`C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\stage5_aa_cause\`)
- `slots_stage5.json`/`.csv`: 339슬롯 자기 짝
- `dup_name_pairs.csv`: 이름 충돌 대응
- `rerule_unique_names.json`: 도구 이름 재현, 고유 이름 재계산
- `pair_lines.json`: 실패 짝 줄 요약
- `stage5_line_census.csv`, `fault_by_offset.csv`, `front_re1bf_lift_phase.csv`, `fault_line_slots.csv`
- `shape_record_unique.json`, `aphase_E_hand_check.csv`
- `provenance.json`: 입력 sha·열 정의
- `scripts\s1~s10.py`
- 실행: dynamics-dev `python.exe -I -B <script> <이 폴더>`(s1만 `conda run -n dynamics-dev`). 판정 도구는 import만 했고 worktree에는 쓰지 않았다. scratchpad 하위 폴더는 지웠다.

사용한 스킬: 없음
