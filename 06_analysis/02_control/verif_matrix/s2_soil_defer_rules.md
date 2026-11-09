# S-2 토양 모드 시작 유예 개정 규칙 (S2D, 사전 등록·봉인)

- 작성: control-expert, 2026-11-09
- 상태: **봉인.** sha256은 `s2_soil_defer_rules.sha256`(LF, BOM 없음)에 있다. 바꿀 일이 생기면 덧붙임 판 `s2_soil_defer_rules_rev<n>.md`로 봉인한다.
- 사용자 결정(2026-11-09): 다음 방향은 **"토양 모드 시작 유예 개정 (S-2)"**이다. 실행은 이 봉인과 별도로 사용자 승인 뒤에 한다.
- 근거
  - 진단 판정서 `las_revA_diag_judgement.md`(갈래 `boundary_key`, 4절 후보 2)
  - 진단 계획 `las_revA_diag_plan.md`(`da74185b…`)·rev1(`cbca7b4b…`)
  - A안 판정서 `las_revA2_judgement.md`(P5r4 `fail` (다) C-S 1짝)
- 이어받는 규칙
  - A안 쪽: `las_rev_targeted_rules.md`(`bb235f27…`)·rev1(`672bc8f8…`), `las_revA_targeted_rules.md`(`b09d004b…`)·rev1(`c0251802…`)·rev2(`9f478b7f…`)·rev3(`98082a36…`)
  - 여기 적지 않은 판정 정의(C-2형, 5.0 None 규칙, R1-1~R1-4, READY 모집단, C-4 예외)는 그 규칙들 그대로다.
- 규약
  - 이산 $T_s$ = 0.1 s, 출력 지연 $d$ = 1, C2 음되먹임
  - 행정은 평균 모터 행정 [mm], 힘은 실린더 순 힘 [N 또는 kN]
  - $F_{min}$ = 9,414.589 N, $W_{ref}$ = `C2Controller._reference_weight_N()`
  - S-1 창 상승 문턱 $R_0$ = `plateau_rise_max_N` = 2,000 N, 그럴듯함 문턱 0.85 $W_{ref}$
  - 래치 해제 20 mm(`crawler_zone_release_m`)

## 0. 결과를 보기 전의 확정이다 (봉인 전에 본 것)

- S2D 코드와 실행은 **0줄**이다(필드도 없다).
- 봉인 전에 본 것(모두 공개)
  1. diagA 3줄(`v5/las/diagA/diagA.jsonl` `1590e79b…`)의 주기별 S-1/S-2 기록 전부(P0·P5·P5r4). 유예 값을 정한 유일한 주기 기록이다(1.3절).
  2. A안 rev2 결과 요약: revA2 각 묶음의 토양 모드 시작 수(R-0A 0, R-Q 0, R-T 0, R-S 13, R-P0 1)와 R-S 13키 이름·LOC 시각·R4c30 여부. 스크립트 `control_lasrevA\s2_reva2_soil.py`(읽기 전용)
  3. 저장 기준 줄 요약
     - `las_T1`·`las_T2`(b0)는 토양 모드 0줄이다.
     - FB L 30줄은 토양 모드 12줄, R4c30 10줄이고, 키별 LOC 시각·LOC − $t_{off}$(0.1~2.9 s)를 봤다(`s2_census.py`).
  4. `v5/d1.jsonl`(`9039b36a…`, 868줄, 태그 `final_C4G2_P3`·없음 = LAS 전 제어기)의 그룹별 수·토양 모드 수·R4c30 수·`wall_s` 합(`s2_d1_census.py`). 토양 대응 그룹 456줄 가운데 토양 모드 305줄이다.
  5. `c2.py`(master)의 S-1(`_update_liftoff_window`, `_plateau_rise_N`), 래치(`_update_crawler_zone`), S-2(`_hold_crawler_zone_until_liftoff`), R4c30(`_is_flat_soil_margin_due`) 코드
- **봉인 전에 보지 않은 것**: 위 기록 밖의 주기 기록은 없다. 특히 진짜 연약 지면 키에서 래치 해제 순간의 S-1 창 상승 값은 **기록이 없어 보지 못했다**. 그래서 진짜 토양에서 유예가 걸리는지는 예측만 한다(4.2절). 그 확인이 이 규칙의 핵심 검증(S-C·S-D)이다.

## 1. 개정 정의

### 1.1 기호

| 기호 | 뜻 | 단위 | 코드(부록 A) |
|---|---|---|---|
| $t_{rel}$ | LOC 전 래치 해제가 처음 일어난 주기(원래는 이 주기에 토양 모드 시작) | s | `_hold_crawler_zone_until_liftoff` |
| $R_k$ | 주기 $k$의 S-1 창 꼬리(평균 행정 ≥ 10 mm) 상승 | N | `_plateau_rise_N` 반환값 |
| $\bar L_k$ | 같은 꼬리의 하중 합 평균 | N | `_update_liftoff_window` |
| $N_d$ | 유예 최대 주기 수 | 주기 | `SoilResponseSettings.mode_defer_periods`(새, 기본 0) |
| $\Delta s_d$ | 유예 최대 행정 진행 | m | `mode_defer_stroke_m`(새, 기본 0.0) |
| $k_d$ | 상승 배수 문턱 | — | `mode_defer_rise_factor`(새, 기본 4.0) |

### 1.2 규칙 (S2D)

LOC 전, 래치가 풀리는 주기 $t_{rel}$에 원래 규칙(S-2)은 토양 모드를 시작한다. S2D는 다음 **유예 진입 조건**이 모두 참이면 토양 모드를 시작하지 않고 유예에 들어간다.

1. $N_d\ge1$
2. 이 주기에 S-1 창 꼬리가 있다(평균 행정 ≥ 10 mm를 덮음).
3. $R_k\le k_d\,R_0$(= 8,000 N)
4. $R_k<R_{k-1}$(줄어드는 중). 직전 주기에 꼬리가 없으면 거짓이다.
5. $\bar L_k\ge0.85\,W_{ref}$(하중이 이미 다리로 거의 옮겨 왔음)

유예 중(최대 $N_d$주기, 유예 시작 주기 포함)

- 래치는 잡아 둔다(`in_crawler_zone` 참 유지 → 크롤러 구역 규칙대로 수축 없이 들어 올림). 이것은 토양 모드와 같다.
- 토양 모드는 아니다.
  - 밀어 올림 하한(0.25 $v_{max}$)이 없다.
  - `soil_mode_start_s`가 없다. 그래서 R4c30, L1gs 토양 징후, DSb75 감시, LAS-b의 `soil` 끝은 걸리지 않는다.
- 유예가 이미 시작된 주기들에서 S-1 창은 평소대로 갱신한다. LOC가 확정되면 유예를 끝낸다(사유 `loc`). 토양 모드는 시작하지 않는다.
- 다음 가운데 하나가 먼저 오면 그 주기에 토양 모드를 시작한다(유예 만료).
  - 사유 `periods`: 유예 주기 수 ≥ $N_d$
  - 사유 `stroke`: 평균 행정 진행 ≥ $\Delta s_d$
  - 사유 `rise`: $R_k>k_d R_0$ 또는 $R_k\ge R_{k-1}$
  - 사유 `window`: 꼬리 없음 또는 창 비움
- 만료로 토양 모드를 시작할 때 `soil_mode_start_s`는 만료 주기 시각이다. `soil_mode_start_stroke_m`(S-4 밀어 올림 예산 기준)은 **유예 시작 주기의 평균 행정**이다. 그래서 S-4 예산(150 mm)이 유예로 늘지 않는다.
- 같은 주기 안의 순서는 지금과 같다(S-1 창 갱신 → 래치 갱신). LOC가 확정된 주기에는 `_hold_crawler_zone_until_liftoff`가 바로 반환하므로 유예 처리도 없다.
- 사건
  - 진입 `INFO_SOIL_MODE_DEFER`
  - 끝 `INFO_SOIL_MODE_DEFER_END:<loc|periods|stroke|rise|window>`
  - $N_d$ = 0이면 사건도 상태 변화도 없다.
- **기본값 = 비트 동일**: $N_d$ = 0(기본)이면 유예 경로가 없다. 모든 명령·사건이 지금과 비트 같아야 한다(S-0).

### 1.3 유예 값 (결과 전 결정, 근거)

| 값 | S2D | 근거(diagA 주기 기록, 0절 1) |
|---|---|---|
| $N_d$ | **5주기(0.5 s)** | 래치 해제부터 LOC까지 P0 0주기, P5 2주기(23.8 → 24.0 s), P5r4 3주기(23.8 → 24.1 s). 최댓값 3에 2주기 여유 |
| $\Delta s_d$ | **6 mm** | 같은 구간 행정 진행 P5 3.15 mm(373.475 → 376.621), P5r4 4.40 mm(372.261 → 376.662). 최댓값의 약 1.4배 |
| $k_d$ | **4**(8 kN) | 래치 해제 주기의 $R$ P5 2.25 kN(1.12 $R_0$), P5r4 4.01 kN(2.0 $R_0$). 최댓값의 2배 |
| 감소 조건 | $R_k<R_{k-1}$ | 해제 주기 P5 4.45 → 2.25, P5r4 4.12 → 4.01 kN. 그 뒤 LOC까지 단조 감소(P5 2.25 → 2.03 → 1.45, P5r4 4.01 → 2.39 → 2.36 → 1.81 kN) |
| 하중 조건 | $\bar L\ge0.85\,W_{ref}$ | 해제 주기 $\bar L/W_{ref}$ P5 1.038, P5r4 1.037. S-1 LOC 그럴듯함 문턱과 같은 값 |

- 후보는 **S2D 하나**다.
  - 값을 더 좁히면(예: 3주기·3 mm) 진단 사례 P5r4(3주기·4.4 mm)를 덮지 못한다.
  - 더 넓히면 진짜 토양에서 토양 모드 지연이 커진다.
- 이 값은 경계 키 하나·하네스 하나에서 왔다. 과적합 위험을 공개한다. 일반화 근거는 S-C·S-D(토양 키 전체)와 A-S다.

## 2. 후보와 결합

| 이름 | 설정 | 쓰는 곳 |
|---|---|---|
| **P0** | 현 프리셋(b0 LAS-b, S-2 그대로) | 기준 |
| **S2D** | P0 + `mode_defer_periods`=5, `mode_defer_stroke_m`=0.006, `mode_defer_rise_factor`=4.0 | 토양 키 판정 |
| **P5r4** | A안 rev2 후보(β 4.5, $N_r$ 4) | 저장 결과(revA2) |
| **P5r4S** | P5r4 + S2D 설정 | A안 재판정 |

- 결합 방식: **A안 재판정 = P5r4S를 A안 rev2 기준 그대로(저장 b0 L 대비)로 판정한다.** 통과하면 "P5r4 + S2D"를 함께 채택 권고한다. 각각 따로 채택하지는 않는다.
  - S2D 단독 채택 여부는 S-C·S-D 결과로 따로 묻는다.

## 3. 묶음·건수·비용

| # | 묶음 | 내용 | 건수 | CPU 어림 |
|---|---|---|---|---|
| S-0 | 비트 시험 | 새 코드, $N_d$ = 0을 명시. A안 원판 R-0 6작업(저장 해시) + diagA 3줄(P0·P5·P5r4 저장 해시) | 9 | 약 0.2 h |
| S-C | 토양 키 기준·경합 조사 | P0(현 프리셋, **S2D 그림자 기록 켬**: 유예 진입 조건을 기록만 하고 행동하지 않음)로 v5 D-1 토양 대응 그룹 456작업(H-S-0 216, H-S-1 12, H-S-A 72, H-S-A-J2 4, H-S-C 120, H-S-C-g 24, H-R-A-J2 4, H-R-A-S1 4; 작업 dict는 `d1.jsonl` `job`과 같아야 함) | 456 | 약 28 h(`d1.jsonl` 같은 그룹 `wall_s` 합 99,547 s) |
| S-D | S2D 토양 판정 | S2D로, S-C에서 토양 모드가 시작된 모든 키 + 토양 모드 없는 키 가운데 시드 고정 무작위 40키(`numpy.random.default_rng(20261109)`, 키 이름 정렬 뒤 추출) | 예상 약 345(305 + 40) | 약 21 h |
| A-S | A안 재판정 | P5r4S로 A안 rev2 묶음 그대로: R-0A 격자 54 + R-Q 48 + R-T 192 + R-S 30 | 324 | 약 8.2 h(revA2 같은 묶음 `wall_s` 합) |
| S-Ch | Chrono SCM 재확인 | 하네스 묶음 통과 뒤. 토양 모드가 시작되는 SCM 행 2~4행(행 정의는 cad-expert, 실행 전 덧붙임 판으로 확정), P0와 S2D 짝 | 4~8 | 행당 약 8,800 s |

- 하네스 합계 약 1,134건, 약 57 CPU-시간이다. 벽시계는 P 8 + E 12에서 약 3~4시간이다(배치는 compute-scheduler-expert).
- Chrono는 별도로 행당 약 2.4시간이다. SCM 실행 규칙(스레드 고정, P 우선, `OMP_WAIT_POLICY=PASSIVE`)을 따른다.
- 순서: S-0 → S-C → S-D → S 판정 → (통과 시) A-S → A 판정 → (통과 시, 사용자 승인) S-Ch
- 출력: main checkout `v5/soil_defer/` 아래 `s2d_<묶음>.jsonl`(로컬 전용, git exclude, `-text`)
- 원 S9 P3b 토양 스윕 묶음(`06_analysis/02_control/s9/` 계열)은 이 규칙의 판정 범위에 넣지 않는다. 필요하면 덧붙임 판으로 행 수를 확정한 뒤 넣는다(4.4절 한계).

## 4. 사전 예측

### 4.1 구현 확인 (어긋나면 구현 결함, 멈춤 SH-3)

| # | 예측 |
|---|---|
| K-S0 | S-0 9줄 해시가 저장값과 같다 |
| **K-S1** | P0(또는 P5r4) 기준 줄에 토양 모드 시작이 **없으면** 같은 키의 S2D(또는 P5r4S) 줄은 해시가 같다. 유예는 기준 실행이 토양 모드를 시작했을 주기에서만 들어갈 수 있기 때문이다. 대상: S-D의 무작위 40키, A-S의 R-0A·R-Q·R-T 294줄 전부와 R-S에서 revA2 P5r4가 토양 모드 없던 17줄 |
| K-S2 | S-C 그림자 기록이 "유예 진입 안 함"이고 토양 모드가 시작된 키는, S2D 줄이 기준과 해시가 같다 |
| K-S3 | 그림자 기록이 "유예 진입"인 키만 해시가 바뀔 수 있다. 바뀐 키의 첫 명령 차이는 그 진입 주기 이후다 |
| K-S4 | 유예 중 모든 주기에서 래치가 잡혀 있고(`in_crawler_zone` 참), 적용 출력에 수축 다리가 없다 |
| K-S5 | 만료 줄의 `soil_mode_start_stroke_m`은 유예 시작 주기의 평균 행정과 같다 |

### 4.2 결과 예측 (가설. 어긋나면 SH-6으로 묻는다)

| # | 예측 | 근거 |
|---|---|---|
| Q-S1 | 경계 키 `D1\|H-S-A\|G1+J1@FL\|T\|flat\|K1\|VB\|e0`: P5r4S는 유예 3주기 뒤 LOC(24.1 s), 토양 모드·R4c30 없음, 최대 행정 ≤ 저장 L 0.438764 + 0.001 m. 그래서 A안 C-S를 통과한다 | diagA P5r4 기록(해제 주기 $R$ 4.01 kN 감소 중, $\bar L/W$ 1.037) |
| Q-S2 | S-C에서 유예 진입 조건이 참인 토양 모드 키는 그 그룹 토양 모드 키의 **20 % 이하**다 | 진짜 연약 지면에서는 래치 해제 때 크롤러가 아직 하중을 받아 $\bar L<0.85 W$이거나 $R$이 크다고 본다. **기록으로 확인하지 못한 가정이다**(0절) |
| Q-S3 | 유예에 들어간 키 가운데 만료(`periods`·`stroke`·`rise`·`window`)된 키의 토양 모드 시작 지연은 모두 ≤ 0.5 s다 | 규칙상 상한 |
| Q-S4 | A-S의 R-S 13키(revA2 P5r4 토양 모드) 가운데 해시가 바뀌는 키는 경계 키를 포함해 **4키 이하**다 | 진짜 연약 지면 키(J1·J2·S1 평지, C 계열)는 LOC − $t_{off}$ 0.8~2.9 s로 래치 해제와 LOC 사이가 멀다고 본다 |

## 5. 판정 기준

### 5.1 S 판정 (S2D 대 P0, S-D 짝)

모든 기준은 같은 키 짝(S2D − P0)으로 본다. 정의는 A안 원판 5.0·5.2와 rev1 R1-1~R1-4 그대로다.

| # | 기준 |
|---|---|
| SC-2 | C-2형 위반 0: verdict, `fail_items`, `d1.items`(G6 토양 항목 포함), 단계, FAULT·WARN 새 이름 |
| SC-F | P0 `F_judged_min_N` ≥ 10,414.589 N이면 S2D도 그 이상 |
| SC-S | `d1.stroke_max_m` 증가 ≤ 0.001 m |
| SC-R | 해시가 바뀐 짝의 READY $\Delta t$ 중앙 ≤ +1.0 s, 최대 ≤ +5.0 s. 빈 집합 처리는 A안 원판 5.2와 같다 |
| **SC-T (비회귀: 진짜 토양에서 늦게 켜짐)** | 만료 짝마다 다음을 모두 만족한다. 그리고 유예가 `loc`로 끝나 토양 모드를 피한 짝은 수·키를 기록하고 SC-2를 그대로 적용한다 |
| | (a) 토양 모드 시작 지연 $t_S^{S2D}-t_S^{P0}$ ≤ 0.5 s + $10^{-9}$ |
| | (b) K-S4(유예 중 수축 없음·래치 유지) |
| | (c) G6-1(크롤러)·G6-3($F_{min}$)·G6-7(LOC 전) 항목 새 실패 0 |
| | (d) 유예 구간과 그 뒤 1 s의 최소 다리 하중이 P0 같은 구간 최소보다 1 kN 넘게 낮지 않다 |
| K | K-S1~K-S5 위반 0 |

### 5.2 A 판정 (P5r4S, A안 rev2 기준 그대로)

- (가)′: G-1, G-1H, G-1Q, G-2′(≥ 11.414589 kN), G-3, G-4
- (나): R-T 7기준(C-2형, C-1, C-F, C-S, A-3, R-1, R-2)
- (다): R-S C-2형, C-S
- 짝 기준은 저장 b0 L(A안과 같음)이다. R-P0는 이미 149/149 재현됐으므로 다시 돌지 않는다. 다만 A-S에서 새로 해시가 바뀐 키가 그 149 밖이면 그 키만 P0로 재현한다.
- K-S1(A-S 대상 311줄)이 위반 0이어야 한다.

### 5.3 S-Ch (Chrono SCM)

- 행 정의 덧붙임 판에서 확정한다.
- 판정은 SC-2·SC-S·SC-T와 같은 정의를 Chrono 결과 필드에 맞춰 쓴다.

### 5.4 종합

- S 판정과 A 판정이 모두 통과하면 **"P5r4 + S2D" 채택 권고**다. 그 뒤 S-Ch(사용자 승인) 결과를 붙인다.
- S 판정만 통과하면 S2D 단독 채택을 묻는다.
- A만 통과하는 경우는 정의상 없다(A는 S2D를 포함).
- 채택은 사용자가 정한다.

## 6. 멈춤 조건

| # | 조건 | 처리 |
|---|---|---|
| SH-1 | 이 파일·`.sha256`이 없거나 LF sha256이 다르다 | 실행하지 않는다 |
| SH-2 | S-0 불일치 | 모든 묶음을 멈춘다. python-expert가 고친 뒤 S-0부터 다시 한다 |
| SH-3 | K-S1~K-S5 위반 | 그 묶음을 멈춘다. 구현 결함 후보 |
| SH-4 | 정체성(한 커밋, 빈 diff, dirty 문서만), 작업 dict 불일치, 판정 필드 누락 | 판정 불가 |
| SH-5 | 실행 오류 | 한 번 다시 돈다. 다시 오류면 멈춘다 |
| SH-6 | Q-S1~Q-S4 어긋남 | 그 단계 판정은 끝까지 내되, 다음 단계(A-S, S-Ch) 전에 멈추고 묻는다 |
| SH-7 | SC-T 위반 1건 이상 | **S 판정 미달.** A-S로 가지 않고 묻는다. 유예 값을 바꿔 다시 돌리지 않는다 |
| SH-8 | SC-2·SC-F·SC-S·SC-R 위반 누적 5짝 이상 | S-D의 남은 실행을 멈춘다 |

- 미달이어도 $N_d$, $\Delta s_d$, $k_d$를 결과에 맞춰 바꾸지 않는다. 바꾸려면 사용자 결정과 덧붙임 판이 필요하다.

## 7. 판정서와 두 경로

- 판정서: `06_analysis/02_control/verif_matrix/s2_soil_defer_judgement.md`
- 두 경로: 판정 도구(python-expert) + control-expert 재집계(jsonl만 읽음). 기준별 참·거짓, 개수, 수치(1e-9)가 같아야 확정이다.
- 판정서에 적을 것
  - 이 규칙과 이어받은 규칙의 sha256, 0절 공개
  - S-0, K-S1~K-S5, Q-S1~Q-S4
  - S-C 경합 조사: 래치 해제와 LOC가 같은 주기·1~$N_d$주기 안인 키 수(그룹별), 그림자 유예 진입 수
  - SC·A 기준별 표, 만료·회피 짝 목록, 한계

## 8. 한계 (봉인 시점)

- 유예 값은 하네스 경계 키 하나(diagA)에서 정했다.
- 진짜 연약 지면에서 래치 해제 순간의 창 상태는 봉인 전에 기록이 없다(Q-S2는 가정).
- S-C의 기준 P0는 현 프리셋이고, `d1.jsonl`(LAS 전 제어기)와 다르다. 그래서 S-C의 토양 모드 수는 305와 다를 수 있다(S-D 건수도 그만큼 바뀜).
- 잡음 등급 L1~L3, 경사 연약 키(H-S-1 외), Chrono 폐루프는 S-Ch 2~4행 외에 보지 않는다.
- 같은 주기 경합의 근본(LOC 확정 → 래치 처리 순서)은 바꾸지 않는다. S2D는 경합 뒤 짧은 구간만 다룬다.

## 부록 A. python-expert 구현 명세

### A.1 `c2.py`

- `SoilResponseSettings`에 필드 3개를 더한다(모두 클래스 기본값, 옛 피클은 기본값으로 읽음).
  - `mode_defer_periods: int = 0`: ≥ 0 정수, 아니면 `ValueError`
  - `mode_defer_stroke_m: float = 0.0`: ≥ 0
  - `mode_defer_rise_factor: float = 4.0`: > 0
- `mode_defer_shadow: bool = False`(기록 전용): 참이면 유예 진입 조건과 가상 끝 사유를 기록만 하고 행동하지 않는다. 명령이 비트 같아야 한다.
- `_update_liftoff_window`가 계산한 꼬리 유무·$R_k$·$\bar L_k$를 상태에 남긴다(`last_tail_ok`, `last_rise_N`, `prev_rise_N`, `last_tail_mean_load_N`). 다시 계산하지 않는다. 기록 전용이라 명령에 영향이 없다.
- `_hold_crawler_zone_until_liftoff`
  - 래치 해제 분기(`not state.in_crawler_zone` 그리고 토양 모드 아님)에서 1.2절 진입 조건이 참이고 $N_d\ge1$이면 유예에 들어간다.
    - `state.in_crawler_zone = True`로 래치를 잡는다.
    - `soil.defer_start_s`, `soil.defer_start_stroke_m`, `soil.defer_periods`를 둔다.
    - 사건 `INFO_SOIL_MODE_DEFER`를 낸다.
  - 유예 중 주기: 1.2절 만료 조건을 본다.
    - 만료면 토양 모드를 시작한다(`soil_mode_start_s` = 현재, `soil_mode_start_stroke_m` = `defer_start_stroke_m`, 사건 `soil_mode_start`와 `INFO_SOIL_MODE_DEFER_END:<사유>`).
    - 아니면 래치를 계속 잡고 `defer_periods`를 1 올린다.
  - LOC 확정으로 함수가 일찍 반환하는 주기에 유예 중이었다면 `INFO_SOIL_MODE_DEFER_END:loc`를 기록하고 유예를 끝낸다.
- `_has_soil_mode_started`, `_is_in_soil_mode`는 유예를 토양 모드로 보지 않는다(바꾸지 않음).
- 메타 `soil`에 `defer`: 설정, `start_s`, `end_s`, `end_reason`, `periods`, `start_stroke_m`, 그림자 기록(진입 여부·시각·$R$·$\bar L$)을 더한다.

### A.2 도구

- 새 도구 `04_scripts/04_hydraulic/coupled/s2_defer_targeted.py`(또는 `las_revA_targeted.py` 확장)
  - 묶음 S-0, S-C, S-D, A-S
  - 후보 P0, S2D, P5r4S. 설정은 `dataclasses.replace`로만 만든다.
  - 작업 dict는 S-C에서 `d1.jsonl` `job`과, A-S에서 A안 도구의 작업과 같아야 한다.
  - diag 주기 기록은 S-0의 diagA 키와 Q-S1 경계 키에서 켠다(diagA와 같은 `soil` 필드 + `defer` 필드).
- 판정 도구 `s2_defer_judge.py`
  - 5절 기준, K-S1~K-S5, Q-S1~Q-S4, S-C 경합 조사 출력
  - 상태 순서 `stop` > `undecidable` > `fail` > `pass`, 빈 묶음 `incomplete`
- 정체성 기록: 이 규칙 sha256(`rules_s2d_sha256`), A안 규칙 6개 sha256, `git_head`, dirty, 코드 diff, 도구·`c2.py` sha256, 스레드, `controller_tag`
- 단위 시험
  - $N_d$ = 0에서 토양 시나리오 명령이 비트 같다. 그림자 켬/끔도 비트 같다.
  - 진입 조건 각각(꼬리 없음, $R$ 큼, $R$ 증가, $\bar L$ 작음)에서 유예가 없다.
  - 만료 사유 4가지와 `loc` 끝
  - 만료 시 `soil_mode_start_stroke_m` = 유예 시작 행정(S-4 예산 불변)
  - 유예 중 래치 유지·수축 없음
  - 음수·정수 아님 → `ValueError`
- 실행 전 감사: verif-protocol-auditor `[시점] 실행 전`
