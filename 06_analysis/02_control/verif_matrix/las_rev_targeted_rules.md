# LAS-b 개정 표적·채택 규칙 (⑤ S7_light 완화, ③ 최소 작동 주기, ⑤+③)

- 작성: control-expert, 2026-11-08
- 상태: **봉인.** sha256과 봉인 시각은 같은 폴더 `las_rev_targeted_rules.sha256`에 있다(LF 줄 끝으로 계산). 이 파일은 더 고치지 않는다. 바꿀 일이 생기면 덧붙임 판 `las_rev_targeted_rules_rev<n>.md`로 봉인한다(11절).
- 사용자 결정(2026-11-08)
  - LAS-b 개정 3안을 함께 표적한다: ⑤ S7_light 완화, ③ 최소 작동 주기 $n_{min}$ = 8, ⑤+③
  - 재개 검증(명세 436.8)은 개정 결정까지 미룬다.
- 근거: `las_phase_diag_judgement.md`(control-expert 초안), 진단 결과 `06_analysis/03_hydraulic/coupled/v5/las/diag/`(D-a 4줄, D-b 30줄, D-c 2줄)
- 기준 코드: master `15542f3`. LAS-b는 03_src 프리셋 구현(`C2Config.with_10hz_d1().liftoff_approach_slow`, 변형 b0)이다.
- 규약
  - 이산 $T_s$ = 0.1 s, 출력 지연 $d$ = 1
  - 음되먹임 C2 그대로
  - 다리 순서 FL, FR, RL, RR(0~3)
  - 힘은 실린더 순 힘 [N 또는 kN, 칸마다 표시], $F_{min}$ = 9,414.589 N
  - $v_{max}$ = 20.924 mm/s, $W_{ref}$ = `C2Controller._reference_weight_N()`

## 0. 결과를 보기 전의 확정이다

- 이 규칙을 쓸 때 개정 후보(P5·P3·P53)로 돌린 실행은 **0줄**이다. 후보를 돌릴 도구도 아직 없다.
- 봉인 전에 본 것(모두 공개)
  1. D-a·D-b·D-c 결과 36줄과 판정 보조 `diag_Db_judge.md`
  2. D-b 기록의 주기별 관문 값. 이것으로 ⑤의 시작 주기를 미리 계산했다(2절). 스크립트는 control-expert scratchpad `ctrl_lasrev\predict_start.py`이고, 출력은 `predict_start.jsonl`이다. 읽기 전용이다.
  3. 저장 기준 줄의 필드와 LAS-b 작동 집계: `v5/las/las_T1.jsonl`(b0 act 8줄), `las_T2.jsonl`(184줄), `v5/fb/fb_F3.jsonl`·`fb_F4.jsonl`의 L 줄(16 + 14줄). 시작 여부, 작동 주기, 끝 사유, 필드 이름, None 여부, 실행 시간을 봤다.
- 2의 계산은 정확하다. LAS-b는 시작 전에는 명령을 바꾸지 않는다. 그래서 시작 관문만 넓힌 변형은 b0 시작 주기까지 b0와 같은 궤적을 지나간다. 검산으로, $\beta$ = 3.5로 계산한 시작 시각이 저장 b0 시작 시각과 30/30 같았다.
- 과적합 위험: (가) 위상 격자는 이 설계에 쓴 D-b와 같은 격자다. 그래서 (가)는 기구 수정 확인이고, 일반화 근거가 아니다. 표본 밖 근거는 (나)·(다)다. 잡음 등급(L1~L3)과 Chrono는 436.8에서 처음 본다(9절 한계).
- 초안 정정(판정에 영향 없음): `las_phase_diag_judgement.md` 2절의 "갈래 B 13줄"은 **12줄**이다. $F_{RL}$ < $F_{min}$인 줄은 V0 9줄(c 0.94의 j 0·2·4, c 1의 j 1·3, nom의 j 0·1·2·4)과 VB 3줄(nom의 j 0·1·4)이다. 갈래 A는 18줄이다. 판정서를 고칠 때 반영한다.

## 1. 후보 정의

### 1.1 기호

| 기호 | 뜻 | 단위 | 코드 |
|---|---|---|---|
| $\hat L_{i,k}$ | 다리 $i$ 하중 추정 | N | `self._load_estimate_N(reading.cylinder_force_lower_N)` |
| $\beta$ | S7_light 문턱 | $F_{min}$의 배수 | `LiftoffApproachSlowSettings.light_leg_fraction_of_F_min`(**기존 필드**) |
| $n_{min}$ | `sum` 끝을 허용하는 최소 작동 주기 | 주기 | `LiftoffApproachSlowSettings.min_active_periods`(**새 필드**) |
| $a_k$ | 끝 판정 시점의 작동 주기 수(시작 주기부터 이 주기 전까지 작용한 주기 수) | 주기 | `_LiftoffSlowState.active_periods`(`_liftoff_slow_end_reason` 안에서 읽는 값, 그 뒤 +1) |
| $c_k$ | `sum` 카운터 | 주기 | `_LiftoffSlowState.sum_periods` |

### 1.2 후보 표

| 이름 | $\beta$ | $n_{min}$ | 바뀌는 곳 | 설정 |
|---|---|---|---|---|
| **P0**(기준, = b0) | 3.5 | 0 | 없음 | 프리셋 그대로 |
| **P5**(⑤) | **4.5** | 0 | 시작 관문 S7_light | `replace(las, light_leg_fraction_of_F_min=4.5)` |
| **P3**(③) | 3.5 | **8** | 끝 `sum` | `replace(las, min_active_periods=8)` |
| **P53**(⑤+③) | **4.5** | **8** | 둘 다 | `replace(las, light_leg_fraction_of_F_min=4.5, min_active_periods=8)` |

- `las` = `C2Config.with_10hz_d1().liftoff_approach_slow`이다. 나머지 값은 b0 그대로다: $\alpha$ 0.6, $\gamma$ 0.16, $\alpha_{end}$ 0.85, $n_{end}$ 5, $T_{max}$ 1.5 s, $\rho_{on}$ 0.18, `require_soil_response` 참.
- 이 표적에서는 프리셋 기본값을 바꾸지 않는다. 후보는 실행 도구가 설정을 덮어써서 만든다(7.2절). 채택이 결정된 뒤에만 프리셋 기본값을 바꾼다.

### 1.3 ⑤ 식 (P5·P53)

$$\text{S7\_light}:\ \min_i\hat L_{i,k}<\beta\,F_{min},\qquad \beta=4.5$$

- 문턱은 4.5 × 9,414.589 = 42,365.65 N이다.
- 식의 형태는 b0와 같다. 숫자만 바꾼다. 따라서 새 코드 경로가 없다.
- S7_light는 시작 관문에서만 쓴다. 그래서 시작 시각이 b0와 같은 실행은 끝까지 명령이 b0와 비트 같다(2절 K-1).

선택 근거와 버린 안(결과 전 결정):

| 안 | 판단 | 근거(D-b 기록, 2절) |
|---|---|---|
| $\beta$ 4.5 고정 | **채택(후보)** | 갈래 B 12줄의 시작 주기가 V0 c 1·0.94에서 +8 → +6으로, V0·VB nom에서 +8 → +7로 당겨진다. 그 주기의 min $\hat L/F_{min}$ 최댓값은 3.982이고, 문턱까지 0.518 $F_{min}$(4.9 kN)이 남는다 |
| $\beta$ 4.0 | 버림 | 격자에서는 4.5와 같은 시작이다. 다만 여유가 0.018 $F_{min}$(0.17 kN)뿐이다. 0.1 kN 수준의 차가 시작을 한 주기 늦출 수 있다. 위상 민감성을 없애려는 목적과 맞지 않는다 |
| $\beta$ 5.0 | 버림 | 격자에서는 4.5와 같은 시작이다. 그런데 넓힐수록 (나)·(다)에서 작동하는 키가 늘어난다. 효과는 같고 개입만 커진다 |
| "가장 가벼운 다리 하중 감소 중"(⑤-dec: $\hat L_{i^*,k}<\hat L_{i^*,k-1}$를 S7_light와 OR) | **버림**(후보로 넣지 않음) | 12줄 모두에서 시작이 $\beta$ 4.5보다 이르지 않았다. V0 c 1·0.94의 5줄은 한 주기 늦고, nom의 7줄은 같다. 또 한 표본 차분이라 실기 압력 잡음에서 문턱 $\delta$가 필요한데, 그 값은 근거가 없다. 새 코드 경로와 새 파라미터가 생긴다. 사용자 결정으로만 다시 넣는다 |
| ④ `sum` 끝 대신 가벼운 다리 하중 회복으로 끝 | 범위 밖 | 사용자 결정(3안만) |

### 1.4 ③ 식 (P3·P53)

- 끝 판정표(`_liftoff_slow_end_reason`)의 순서는 그대로 둔다: `loc` → `phase` → `soil` → `reapproach` → (`zone`) → `sum` → `time`.
- `sum`만 바꾼다.
  $$\texttt{sum}:\quad c_k\ge n_{end}\ \ \textbf{그리고}\ \ a_k\ge n_{min}$$
- 카운터 $c_k$의 갱신은 b0 그대로다. 작동 중인 주기마다 $\sum_i\hat L_{i,k}\ge\alpha_{end}W_{ref}$이면 +1, 아니면 0이다. $a_k<n_{min}$이어서 끝을 미루는 동안에도 카운터는 계속 센다. 그 사이 합이 문턱 아래로 내려가면 카운터는 0으로 돌아간다.
- **$n_{min}$은 `sum` 끝에만 건다.** 안전·단계 끝(`loc`, `phase`, `soil`, `reapproach`, `zone`)과 `time`은 막지 않는다.
  - 그래서 LOC가 오거나 단계가 바뀌면 8주기 전이라도 끝난다.
  - $T_{max}$ 1.5 s는 15주기이므로 $n_{min}$ 8과 겹치지 않는다. `time` 끝의 $a_k$는 늘 15다.
- 뜻: `sum` 끝으로 끝난 실행은 기록 `las.active_periods` ≥ 8이다. 즉 감속이 적어도 8주기(0.8 s) 작용한다. 갈래 A(작동 8~11주기)와 같은 최소 길이다.
- **기본값 = 비트 동일**: $n_{min}$ = 0이다.
  - `sum` 끝이 성립하는 주기에는 $c_k\ge5$이다. 카운터는 작동 주기에만 오르고, 시작 주기에도 오를 수 있다. 그래서 $a_k\ge c_k-1\ge4$다.
  - 따라서 $n_{min}\le4$이면 아무것도 바뀌지 않는다. 기본값 0은 b0와 비트 같다.
- 끝 주기는 b0처럼 작용하지 않는다(명령 유지).

### 1.5 ⑤+③ (P53)

- 1.3과 1.4를 함께 쓴다. 두 규칙이 닿는 곳은 겹치지 않는다(시작 관문 / `sum` 끝).

## 2. 사전 예측 (구현 검증, 판정 기준 아님)

D-b 기록(2절 계산)에서 정해진 예측이다. 하나라도 어긋나면 **구현 결함**으로 멈춘다(8절 H-3). 해시는 `diag_Db.jsonl` 줄의 `commands_sha256` 앞 12자다.

### 2.1 갈래 A 18줄: 세 후보 모두 명령 비트 동일 (K-1)

- 근거: $\beta$를 4.5로 올려도 시작 주기가 b0와 같다. 또 b0의 작동 주기가 이미 ≥ 8이다($a$ = 8, 9, 11).

| 키 | 줄(c, j)과 해시 |
|---|---|
| V0 | c 0.94 j1 `fdef826b7254`, j3 `7a6ef9e2c7f2` · c 1 j0 `52547a6e145e`, j2 `9270a8bb9d20`, j4 `876fed85522c` · nom j3 `acfe58346d29` |
| VB | c 0.94 j0 `2d459242518a`, j1 `38618bda6038`, j2 `108c4357f171`, j3 `2933e25f8ceb`, j4 `b7df1774cd7e` · c 1 j0 `eec974b66af2`, j1 `12b8dc95a4dd`, j2 `e702e1c0f231`, j3 `a40b31bdc696`, j4 `4fa9360b3deb` · nom j2 `e2e750fa446a`, j3 `49f71495509f` |

- 위 18줄의 $F_{RL}$은 10.650~11.594 kN이다. 그래서 (가)의 판정은 사실상 갈래 B 12줄과 $R_c$로 정해진다.

### 2.2 갈래 B 12줄: 시작 시각 (K-2)

- P3의 시작 시각은 b0와 같다. 시작 관문이 그대로이기 때문이다.
- P5와 P53의 시작 시각은 아래 "예측"이다. 같은 칸에 그 주기의 기록 값을 적었다.

| 줄 | TOUCH 끝 [s] | b0 시작 [s](+주기) | P5·P53 예측 시작 [s](+주기) | min $\hat L/F_{min}$ | $\sum\hat L/W$ | $\rho$ |
|---|---|---|---|---|---|---|
| V0 c0.94 j0 | 21.2 | 22.0 (+8) | 21.8 (+6) | 3.963 | 0.712 | 0.1993 |
| V0 c0.94 j2 | 21.2 | 22.0 (+8) | 21.8 (+6) | 3.903 | 0.704 | 0.1979 |
| V0 c0.94 j4 | 21.3 | 22.1 (+8) | 21.9 (+6) | 3.957 | 0.711 | 0.1992 |
| V0 c1 j1 | 20.3 | 21.1 (+8) | 20.9 (+6) | 3.982 | 0.714 | 0.1996 |
| V0 c1 j3 | 20.3 | 21.1 (+8) | 20.9 (+6) | 3.976 | 0.713 | 0.1994 |
| V0 nom j0 | 22.3 | 23.1 (+8) | 23.0 (+7) | 3.847 | 0.764 | 0.2230 |
| V0 nom j1 | 22.3 | 23.1 (+8) | 23.0 (+7) | 3.759 | 0.773 | 0.2315 |
| V0 nom j2 | 22.3 | 23.1 (+8) | 23.0 (+7) | 3.894 | 0.759 | 0.2188 |
| V0 nom j4 | 22.4 | 23.2 (+8) | 23.1 (+7) | 3.848 | 0.764 | 0.2229 |
| VB nom j0 | 22.3 | 23.1 (+8) | 23.0 (+7) | 3.838 | 0.758 | 0.2206 |
| VB nom j1 | 22.3 | 23.1 (+8) | 23.0 (+7) | 3.838 | 0.770 | 0.2262 |
| VB nom j4 | 22.4 | 23.2 (+8) | 23.1 (+7) | 3.837 | 0.758 | 0.2206 |

- 시작 시각의 비교는 $T_s$/2 = 0.05 s 허용으로 한다. 기록 `las.start_t_s`를 쓴다.
- 해석(판정 아님): nom의 7줄은 시작 때 $\sum\hat L$이 이미 0.76~0.77 $W$다. 그래서 P5만으로는 작동 주기가 갈래 A보다 짧을 수 있다. P53을 따로 두는 이유다.

### 2.3 (나)·(다)에서 P3의 비트 동일 집합 (K-3)

P3은 b0가 시작하지 않았거나, `sum` 아닌 사유로 끝났거나, $a\ge8$로 끝난 줄을 바꾸지 않는다. 아래 줄은 `commands_sha256`이 저장 기준 줄과 같아야 한다.

| 묶음 | 저장 b0 작동 집계 | P3 비트 동일이어야 하는 줄 | 바뀔 수 있는 줄 |
|---|---|---|---|
| T-1(8) | 모두 시작, `sum` 끝. $a$ = 9×3, 8×1, 7×3, 6×1 | 4: K3 V0 e0, K3 V0 e0.002, K3 VB e0, K3 VB e0.002 | 4: K1 네 키 |
| T-2(184) | 미시작 130. 시작 54: `sum` 끝 $a$ = 4×23, 5×9, 6×2, 7×5, 8×7, 9×4, 13×2, 14×1, `loc` 끝 $a$ 4×1 | 145(미시작 130 + `sum` $a\ge8$ 14 + `loc` 1) | 39 |
| F-3 L(16) | 시작 3(`sum` $a$ 6·4·5) | 13 | 3 |
| F-4 L(14) | 시작 0 | 14 | 0 |

- P5와 P53은 (나)·(다)에서 저장 주기 기록이 없어 미리 정할 수 없다. 이 둘은 5.2절 A-3과 7.3절 재현으로 확인한다.

### 2.4 구현 일반 검사 (K-4)

- 어느 후보든 `las.end_reason` = `sum`인 줄은 `las.active_periods` ≥ $n_{min}$이어야 한다(P3·P53이면 ≥ 8).
- 줄의 `las.params`(또는 설정 asdict)에 실제 컨트롤러가 쓴 $\beta$·$n_{min}$이 있어야 하고, 후보 표와 같아야 한다. 덮어쓰기가 먹지 않은 줄을 잡는 검사다.

## 3. 묶음과 건수·비용

| # | 묶음 | 키·작업 | 후보 | 건수 | CPU 추정 | 벽시계 추정(P 8 + E 12) |
|---|---|---|---|---|---|---|
| R-0 | 비트 시험 | 6.1절 6작업 | P0(새 코드, 기본값) | 6 | 약 8분 | 약 3분 |
| R-G | (가) 위상 격자 | D-b와 같은 30점(3.1절) | P5, P3, P53 | 90 | 약 46분 | 약 6~8분 |
| R-T | (나) T-1·T-2 | 192키(3.2절) | (가)를 통과한 후보 | ≤ 576 | ≤ 약 675분(192키당 170~225분) | 후보당 약 20분 |
| R-S | (다) 토양·사건 | 30작업(3.3절) | (가)를 통과한 후보 | ≤ 90 | ≤ 약 156분(30작업당 약 52분) | 후보당 약 6분 |
| R-P0 | 기준 재현 | R-T·R-S에서 어느 후보든 해시가 바뀐 키의 합집합 | P0 | ≤ 222(예상 60~100) | ≤ 약 260분 | 약 8~25분 |
| R-X | 예외 근거 | 6.3절의 예외를 주장하는 짝의 L | P0(기록 켬) | ≤ 10 | ≤ 약 15분 | 약 3분 |

- 추정 근거: 저장 `wall_s`의 합이다. T-2 b0는 184줄에 222.7분, F-2 LF는 192줄에 169.3분, F-3 L은 16줄에 27.1분, F-4 L은 14줄에 24.9분, D-b는 30줄에 약 15분이다. 동시 실행 배율은 FB 360건이 약 27분 걸린 것(약 10배)으로 잡았다.
- 상한 합계는 약 19 CPU-시간, 벽시계 약 1.5시간이다. 판정서 초안의 "세 후보 약 1시간"은 R-T를 과소 추정한 값이다.
- 실행 순서: R-0 → R-G(세 후보) → (가) 통과 후보만 R-T·R-S → R-P0 → R-X → 판정
  - (가)에서 실패한 후보는 R-T·R-S를 돌지 않는다. 계산을 아끼기 위해서다.
  - 세 후보가 모두 (가)에서 실패하면 멈추고 묻는다(8절 H-6).
- 배치는 compute-scheduler-expert의 배치표를 받는다. G-D 비용 측정(23시까지)과 겹치지 않게 띄운다. 스레드는 1로 고정한다(`fb_targeted.thread_problems`).

### 3.1 R-G (가) 위상 격자

- 키: `D1|H-R-A|rigid+J1@FR|T|diag-op|K3|VB|e0.002`, `D1|H-R-A|rigid+J1@FR|T|diag-op|K3|V0|e0.002`
- 격자: `las_phase_diag_plan.md` 1.2절과 같다. $s_c\in\{1.0,\,0.94,\,0.8768421\}$이고, 중심마다 $j$ = 0..4다.
  $$s_{c,j}=s_c\,T_c/(T_c+j\,\delta),\qquad\delta=0.025\ \mathrm{s}$$
- 예산: **TOUCH 전용**이다(원판 1.1절과 같음). update 끝 단계가 TOUCH인 주기에만 $Q_b=s\,Q(4v_{max})$를 걸고, 그 밖의 단계는 예산 없음, 검출(U·A97)은 끈다.
- 주기 기록은 켠다(D-b와 같은 필드 + 4.2절 DONE 기록).
- 줄 이름: `<후보>-LT-c<중심>-j<j>`. 예: `P53-LT-cnom-j0`

### 3.2 R-T (나) T-1·T-2

- 키: `las_targeted.stage_keys("T-1")` 8키 + `stage_keys("T-2")` 184키. `las_targeted_rules.md` 부록 A·B와 같다.
- 짝 기준(L): 저장 `v5/las/las_T1.jsonl`의 `las.candidate` = `b0` 8줄과 `las_T2.jsonl` 184줄이다. 같은 키로 짝짓는다. 다시 돌리지 않는다.
  - 다만 해시가 바뀐 키는 R-P0로 기준 재현을 확인한다(7.3절).
- 후보 줄은 4.2절 DONE 기록을 켜고 돈다.

### 3.3 R-S (다) 토양·사건 30작업

- 짝 기준(L): 저장 `v5/fb/fb_F3.jsonl`·`fb_F4.jsonl`에서 `fb.candidate` = `L`인 줄이다(커밋 `2ee35c99`, 03_src LAS-b).
- 목록(`fb_targeted_rules.md` 3.2절과 같다. 모두 ε 0)
  - F-3 16키
    - VB 15키
      - `D1|H-S-0|G1|T|flat|K1|VB|e0`
      - `D1|H-S-0|G1|T|diag-rec|K1|VB|e0`
      - `D1|H-S-0|J1|T|flat|K1|VB|e0`
      - `D1|H-S-0|J1|T|diag-rec|K1|VB|e0`
      - `D1|H-S-0|J2|T|flat|K1|VB|e0`
      - `D1|H-S-0|J2|T|diag-rec|K1|VB|e0`
      - `D1|H-S-1|S1|T|flat|K1|VB|e0`
      - `D1|H-S-1|S1|M|flat|K1|VB|e0`
      - `D1|H-S-1|S1|B|flat|K1|VB|e0`
      - `D1|H-S-A|G1+J1@FL|T|flat|K1|VB|e0`
      - `D1|H-S-A|G1+J1@RL|T|flat|K1|VB|e0`
      - `D1|H-S-A|G1+J1@FR|T|diag-psa-soil|K1|VB|e0`
      - `D1|H-S-A-J2|G1+J2@FL|T|flat|K1|VB|e0`
      - `D1|H-R-A-J2|rigid+J2@FL|T|flat|K1|VB|e0`
      - `D1|H-R-A-S1|rigid+S1@FL|T|flat|K1|VB|e0`
    - V0 1키: `D1|H-S-0|J1|T|flat|K1|V0|e0`
  - F-4 14작업
    - D-1 4키(VB)
      - `D1|H-R-A-stop|rigid+J1@RL|T|fup-op|K1|VB|e0`
      - `D1|H-S-C|J1|T|flat|K1|c-mid@FL|VB|e0`
      - `D1|H-S-C|J1|T|flat|K1|c-mid@RL|VB|e0`
      - `D1|H-S-C-g|J1|T|fdown-rec|K1|c-mid@FL|dsb_gated_off|VB|e0`
    - verdict 사례 10작업: `R2`(`decision` reanchor_on), `R12`(`offset_s` 0.0), `R14`(0.0), `R15`(0.05), `R16`(0.05) × VB·V0. 작업 dict는 저장 L 줄의 `job`과 같아야 한다(`u9_metrics` 참).
- 작업 dict는 `fb_targeted.bundle_base_jobs("F-3")`·`("F-4")`에서 얻는다. 저장 L 줄의 `job`과 하나씩 대조한다. 다르면 멈춘다(8절 H-4).

## 4. 줄마다 기록할 것

### 4.1 정체성

- `git_head`, `git_dirty`, `dirty_files`, `code_diff_sha256`
- sha256: `c2.py`, 실행 도구, 판정 도구, `las_phase_diag.py`, `fb_targeted.py`, `las_targeted.py`
- 이 규칙 파일 sha256, 스레드 변수
- 후보 이름, 컨트롤러가 실제로 쓴 `liftoff_approach_slow` 설정 전체(asdict), `controller_tag`
- 허용 범위
  - 한 후보의 모든 줄은 한 커밋에서 나와야 한다.
  - dirty는 코드가 아닌 파일(`.gitattributes`, `00_docs/decision_log.md`)만 허용한다. 이때 `code_diff_sha256`은 빈 값의 해시여야 한다.
  - 이를 어기면 판정 불가로 멈춘다(8절 H-4).

### 4.2 DONE 하위 조건 기록(기록 전용, 새 필드)

- 범위: 첫 LOC부터 첫 READY + 1 s까지, LEVEL·DONE 주기마다 `done_trace` 한 줄을 남긴다.
- 필드
  - `t_s`, `phase`
  - `loc_ok`: `soil.enable`이 아니거나 LOC 확정
  - `ref_on_target`: `_is_reference_on_target()`
  - `deviation_deg`, `attitude_in_band`: `_completion_deviation_rad()` < `done_attitude_rad`
  - `clearance_done`: `_is_clearance_done`
  - `twist_path`: `relax` 또는 `plain`
  - `twist_ok`: `_is_twist_condition_met`, 또는 $\lvert D\rvert$ < `done_twist_N`
  - `complete_now`
  - `diff_sink_hold`: `_is_diff_sink_holding()`
  - `reapproaching`: 재접근 다리 유무
  - `complete_since_s`: 이 주기 `_level_step` 뒤의 값
- 값은 **원래 호출의 반환값을 가로채서** 얻는다. 같은 함수를 다시 부르지 않는다. `_is_twist_condition_met`처럼 내부 상태를 바꿀 수 있는 함수가 있기 때문이다.
  - `_update_completion`이 앞에서 돌아가 하위 함수를 부르지 않은 주기에는 그 필드를 None으로 둔다(`loc_ok` = 거짓).
- 줄 요약 `done_clock`
  - `t_first_done_s`
  - `t_loc_last_before_done_s`: 첫 DONE 전 마지막 LOC onset
  - `clock_starts_s`: $[t_{loc,last},t_{DONE}]$ 안에서 `complete_since_s`가 None → 값으로 바뀐 시각들 $c_1<\dots<c_m$
  - `resets`: 시계가 값 → None으로 바뀐 주기마다 시각과, 그 주기에 거짓이었던 하위 조건 이름(참이었던 `diff_sink_hold`·`reapproaching` 포함)
  - `loss_s` $\ell=c_m-c_1$(재시작이 없으면 0)
- 비트 불변: 이 기록은 명령을 바꾸지 않아야 한다. 단위 시험과 7.3절 해시 대조(미작동 줄 = 저장 해시)로 함께 보인다.

## 5. 채택 기준

모든 기준은 **같은 키·같은 설정의 짝(후보 − L)**으로 본다. 판정에 쓰는 필드는 아래 표의 실제 기록 키다.

| 쓰는 곳 | 필드 |
|---|---|
| 위상 격자 | `diag.summary.F_RL_kN`, `diag.summary.F_judged_min_kN`, `diag.touch_budget.centre`, `diag.touch_budget.j`, `diag.touch_budget.level_budget_periods`, `diag.summary.gate_consistent`, `las.start_t_s`, `las.active_periods`, `las.end_reason`, `commands_sha256` |
| D-1 짝 | `d1.verdict`(`pass`/`fail`/`allowed_stop`), `d1.fail_items`, `d1.items`(13개: `G6-1_crawler`, `G6-2_loc`, `G6-3_Fmin`, `G6-4_att`, `G6-5_rut_stroke`, `G6-6_fault_ready`, `G6-7_preloc`, `READY`, `D8_F_after_liftoff`, `D8_end_attitude`, `moving_180bar`, `locked_350bar`, `FAULT0`), `d1.F_judged_min_N`, `d1.t_ready_s`, `d1.stroke_max_m`, `final_phase`, `event_names`, `commands_sha256` |
| verdict 사례 짝 | `final_phase`, `event_names`, `values.times.t_first_ready_s`, `commands_sha256` |
| 예외 | `done_clock.loss_s`, `done_clock.resets`, `done_clock.clock_starts_s` |

### 5.0 None·누락 규칙(모든 기준 공통)

- 기준에 쓰는 필드가 줄에 없으면 그 짝은 **판정 불가**다. 그 묶음을 멈춘다(8절 H-4). 통과로 세지 않는다.
- 값이 None이면 다음과 같이 처리한다.
  - `d1.items[k]`: 짝 L의 값이 참인데 후보가 참이 아니면(거짓 또는 None) 위반이다. L이 None이고 후보가 거짓이어도 위반이다.
  - `d1.verdict`: D-1 짝에서 후보가 None이면 위반이다. verdict 사례(작업에 `case`가 있음)는 `d1`이 없는 것이 정상이고, `final_phase`로 본다.
  - READY 시각
    - L은 있고 후보가 None이면 위반이다(5.2 C-2형 (b)).
    - 둘 다 None이면 READY 계산에서 빼고 목록으로 적는다. L의 `final_phase`가 `fault`인 작업만 해당한다.
    - L이 None이고 후보가 값을 가지면 개선으로 적는다(판정 영향 없음).
  - 위상 격자의 `F_RL_kN`·`F_judged_min_kN`이 None이면 그 줄은 미달이다.
- 사건 이름 집합은 `event_names`(실행 전체 이름별 횟수 dict)의 키를 쓴다. 이름은 `:` 앞 부분이고, 접두사 `FAULT`·`WARN`인 것만 본다.

### 5.1 (가) R-G 위상 격자 (후보마다)

| # | 기준 | 정의 |
|---|---|---|
| G-1 | 하중 | 30줄 모두 `F_RL_kN` ≥ 10.400이고 `F_judged_min_kN` ≥ 10.400 |
| G-2 | 위상 범위 | 키 2 × 중심 3의 6칸 모두 $R_c=\max_{j\le3}F_{RL}-\min_{j\le3}F_{RL}$ ≤ 0.500 kN. 칸마다 $j$ = 0..3의 4줄이 있어야 한다. 없으면 판정 불가다 |
| G-3 | 제외 검사 | D-b와 같다. 30줄이 모두 있고, 오류 줄 0, `level_budget_periods` = 0, `gate_consistent` 참. 하나라도 어기면 **판정 불가(도구)**로 멈춘다. 일부 줄만 다시 돌지 않는다 |
| G-4 | 사전 예측 | 2.1·2.2·2.4절(K-1·K-2·K-4). 어긋나면 구현 결함으로 멈춘다(8절 H-3) |

- 참고 기록(판정 아님): 줄마다 시작 주기, 작동 주기, 끝 사유, 이륙 시각, 최소 다리 이름. 칸마다 $M_c$와 $P_c$.
- 문턱의 뜻
  - 10.400 kN은 사용자 지정값이다. 원판 C1의 $F_{min}$ + 1,000 N = 10,414.589 N과 14.6 N 차이다. 두 값 사이에 든 줄이 있으면 판정서에 따로 적는다.
  - $R_c$는 갈래 B가 갈래 A보다 **높아져도** 커진다. 그래도 위상 의존이 남은 것이므로 미달로 센다.

### 5.2 (나) R-T T-1·T-2 (후보마다, 192짝)

| # | 기준 | 정의 |
|---|---|---|
| C-2형 | 나빠짐 0 | 짝마다 아래 (a)~(c)에 위반이 없다. 위반은 짝 단위로 센다(`fb_targeted_rules_rev3` R3-2) |
| | (a) 판정 | L `pass` → 후보 `fail` 0, L `allowed_stop` → 후보 `fail` 0. 후보 `fail_items` ⊆ L `fail_items`. `d1.items` 새 실패 0(5.0절. `G6-2_loc` 포함) |
| | (b) 단계 | L `final_phase` = `ready`인데 후보가 `ready`가 아닌 경우 0. L READY 시각이 있는데 후보가 None인 경우 0 |
| | (c) 사건 | 후보의 `FAULT*`·`WARN*` 이름 ⊆ L의 이름 |
| C-1 유지 | 계열 하중 | T-1 8키 모두 후보 `d1.F_judged_min_N` ≥ 10,414.589 N(LAS-b 원판 C1) |
| C-F | 여유선 | L `d1.F_judged_min_N` ≥ 10,414.589 N인 모든 D-1 짝에서 후보도 ≥ 10,414.589 N |
| C-S | 행정 | 모든 D-1 짝에서 `d1.stroke_max_m` 증가 ≤ 0.001 m(LAS-b 원판 C5) |
| A-3 | 강체 균일 | T-2의 H-R-0 48키(L은 48키 모두 미시작)에서 후보 `commands_sha256` = L 해시. 사용자 결정(2026-11-08, A-3 유지) |
| R-1 | READY 중앙 | 모집단 $\mathcal{P}$의 $\Delta t=t^{cand}_{READY}-t^{L}_{READY}$ 중앙값 ≤ +1.0 s |
| R-2 | READY 최대 | 같은 모집단에서 $\max\Delta t$ ≤ +5.0 s |

READY 모집단 $\mathcal{P}$(빈 집합 처리 포함):

- $\mathcal{P}$ = 해시가 바뀐 짝(후보 `commands_sha256` ≠ L) 가운데 두 READY 시각(`d1.t_ready_s`)이 모두 있고, 6절 예외로 빠지지 않은 짝이다.
  - 해시가 같은 짝은 $\Delta t$ = 0이 자명하다. 그래서 모집단에 넣지 않는다. 넣으면 중앙값이 0으로 희석된다.
- $\mathcal{P}$가 비면 처리가 갈린다.
  - 해시가 바뀐 짝이 0이고 192짝 모두 해시가 같으면, R-1·R-2는 **해시 동일로 성립**한다. 판정서에 "192/192 해시 동일"을 적는다.
  - 해시가 바뀐 짝이 있는데 $\mathcal{P}$가 비면(모두 예외이거나 READY가 없음), R-1·R-2는 **판정 불가**로 멈추고 묻는다. 빈 집합에서 통과로 세지 않는다.
- 판정서에는 해시가 바뀐 짝 수, $\mathcal{P}$ 크기, 예외 짝 목록, 중앙·최대를 적는다.

### 5.3 (다) R-S 토양·사건 (후보마다, 30짝)

| # | 기준 | 정의 |
|---|---|---|
| C-2형 | 나빠짐 0 | 5.2절 (a)~(c)와 같다. verdict 사례 10짝은 (b)·(c)만 본다(`final_phase`, READY 시각은 `values.times.t_first_ready_s`) |
| C-S | 행정 | D-1 20짝에서 `d1.stroke_max_m` 증가 ≤ 0.001 m |

- READY 변화는 기록만 한다. 판정에 쓰지 않는다. 짝마다 $\Delta t$와 예외 여부를 적는다.
- 사용자 지정 기준은 "새 FAULT·WARN 0"((c))이다. (a)·(b)·C-S는 이 규칙이 더한 것이다. 원래 LAS-b·FB 채택 기준의 나빠짐 0을 그대로 이은 것이다.

### 5.4 판정

- 후보 하나가 G-1~G-4, (나)의 모든 기준, (다)의 모든 기준을 만족하면 **채택 권고**다.
- 하나라도 어기면 **미달**이다. 기준·키·값을 적는다.
- 채택은 사용자가 결정한다. 채택 뒤 구현(프리셋 기본값)·명세 개정·그림자 판정·436.8 재개의 범위는 그때 정한다.

## 6. C-4 예외: 관문 시점 분기 (사전 등록)

- 대상: 5.2절 R-1·R-2의 해시가 바뀐 짝 가운데 $\Delta t$ > +1.0 s인 짝
- 정의: 아래가 모두 참이면 그 짝은 **관문 시점 분기**다. R-1·R-2 모집단에서 빼고 따로 보고한다.
  1. 후보 줄과 L 줄 모두에 `done_clock`이 있다. L은 R-X 재실행 줄이고, 그 `commands_sha256`은 저장 L 해시와 같아야 한다.
  2. $E=\ell^{cand}-\ell^{L}\ge0.8\,\Delta t$. $\ell$은 4.2절 `loss_s`다. 80 %는 D-c 분류와 같은 문턱이다.
  3. 후보 줄의 $\ell$에 든 재시작(`resets`)이 모두 LAS-b가 끝난 뒤(`las.end_t_s` 이후)에 있다.
- 근거가 없으면 예외도 없다(보수 쪽).
  - 1이 없으면(R-X를 돌지 않았거나 해시가 다름) 그 짝은 예외가 아니다. R-1·R-2 모집단에 그대로 남는다.
  - R-X 재실행 해시가 저장 L과 다르면, 기준 재현 실패로 멈춘다(8절 H-5).
- 보고: 짝마다 다음을 적는다.
  - $\Delta t$, $\ell^{cand}$, $\ell^{L}$, $E/\Delta t$
  - 재시작 시각과 거짓이 된 하위 조건 이름
  - LAS-b 시작·끝, LOC 시각
- 한도: 한 후보의 예외 짝이 5개를 넘거나, 예외 짝 하나라도 $\Delta t$ > +15 s면, 그 후보는 자동으로 채택 권고가 되지 않는다. 다른 기준을 모두 통과했어도 "예외 과다"로 묻는다.
- (다)의 READY 기록에도 같은 정의로 예외 여부를 적는다(판정 아님).

## 7. 비트 시험·재현

### 7.1 R-0 비트 시험 (후보 실행 전)

- 새 필드 `min_active_periods`(기본 0)를 넣은 코드로, 프리셋을 덮어쓰지 않은 P0를 돌린다. 아래 6작업의 `commands_sha256`이 저장값과 같아야 한다.

| 작업 | 저장 출처 | 기대 해시(앞 12자) |
|---|---|---|
| `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K1\|VB\|e0` | `las_T1.jsonl` b0 | `aff9b0f10ac5` |
| `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K3\|V0\|e0` | `las_T1.jsonl` b0 | `fc2ca22f2850` |
| D-b A-1 VB(`…K3\|VB\|e0.002`, LT c1 j0) | `diag_Db.jsonl` | `eec974b66af2` |
| D-b A-1 V0(`…K3\|V0\|e0.002`, LT c1 j0) | `diag_Db.jsonl` | `52547a6e145e` |
| `D1\|H-S-A\|G1+J1@FR\|T\|diag-psa-soil\|K1\|VB\|e0`(b0 작동) | `fb_F3.jsonl` L | 저장 줄 전체 해시 |
| `R12` VB(`offset_s` 0.0) | `fb_F4.jsonl` L | 저장 줄 전체 해시 |

- 해시는 64자 전체로 대조한다. 표의 앞 12자는 확인용이다.
- 단위 시험(python-expert)
  - $n_{min}\in\{0,1,2,3,4\}$에서 작동 시나리오 명령이 비트 같다.
  - $n_{min}$ = 8에서 `sum` 끝 $a\ge8$이다. 안전 끝(`loc`·`phase`·`soil`·`reapproach`)은 $a$ < 8에서도 그대로 난다.
  - `min_active_periods` 음수는 `ValueError`다.
  - 옛 피클(필드 없음)을 읽으면 0이다.

### 7.2 후보 설정의 적용

- 도구는 프리셋 LAS-b가 b0인지 먼저 확인한다(`fb_targeted.check_preset_las`).
- 그 뒤 컨트롤러를 만들 때 `dataclasses.replace`로 1.2절 값만 덮어쓴다.
- 줄에는 컨트롤러가 실제로 쓴 설정을 다시 읽어 기록한다(K-4).
- `las_targeted.install`(옛 b0 래퍼)은 설치하지 않는다.

### 7.3 R-P0 기준 재현 (구현 동등성 공백 메우기)

- 이유: (나)의 짝 기준 L은 03_src에 LAS-b가 들어가기 전의 래퍼 시기 줄이다. 그동안 해시로 직접 같음을 보인 것은 30키뿐이었다(`fb_targeted_rules_rev2` R2-1 ③).
- 방법: R-T·R-S에서 **어느 후보든** 해시가 바뀐 키의 합집합을 P0(새 코드, 기본값)로 다시 돈다. 그 해시가 저장 L 해시와 같아야 한다. 다르면 8절 H-5로 멈춘다.
- 해시가 바뀌지 않은 키는 후보 줄 자체가 저장 해시와 같으므로 재현이 이미 보인 셈이다.
- 판정서에 "192 + 30짝 가운데 해시 동일 n, R-P0 재현 m"을 적는다.

## 8. 멈춤 조건

| # | 조건 | 처리 |
|---|---|---|
| H-1 | 이 파일이나 `.sha256`이 없거나, LF 기준 sha256이 다르다 | 실행하지 않는다 |
| H-2 | R-0 비트 시험 불일치(6작업 중 하나라도) | 모든 묶음을 멈춘다. 구현 결함이므로 python-expert가 고친 뒤 R-0부터 다시 한다 |
| H-3 | 사전 예측 K-1~K-4 불일치 | 그 후보의 모든 묶음을 멈춘다. 구현 결함 후보로 보고한다 |
| H-4 | 정체성 위반(4.1절), 판정 필드 누락(5.0절), 작업 dict 불일치(3.3절) | 그 묶음을 멈추고 판정 불가로 보고한다 |
| H-5 | R-P0 또는 R-X 재실행 해시 ≠ 저장 L 해시 | 모든 판정을 멈추고 기준 재현 실패로 보고한다. 기준 L을 바꾸지 않는다 |
| H-6 | 세 후보 모두 (가) 미달 | 멈추고 묻는다. (가) 결과 전부(줄별 시작·작동·끝·$F_{RL}$)를 붙인다 |
| H-7 | 실행 오류 줄 | 그 작업을 한 번 다시 돈다. 다시 오류면 그 묶음을 멈추고 보고한다. R-G는 G-3대로 30줄을 다시 돈다 |
| H-8 | 한 후보의 R-T 또는 R-S에서 C-2형 위반 짝이 누적 5 이상 | 그 후보의 남은 실행을 멈춘다(계산 절약). 끝난 줄은 판정에 쓴다 |
| H-9 | 예외 과다(6절 한도) | 그 후보는 자동 권고가 되지 않는다. 묻는다 |

- 미달이어도 값을 바꿔 다시 돌리지 않는다. 다른 $\beta$, 다른 $n_{min}$, ⑤-dec, ④는 사용자 결정으로만 고른다.

## 9. 순위 규칙 (둘 이상이 채택 권고일 때)

1. (가) 30줄의 $\min$ `F_judged_min_kN`이 가장 큰 후보를 1순위로 둔다. 차가 0.3 kN 안이면 동률로 본다.
2. 동률이면 (나)+(다) 222짝에서 해시가 바뀐 짝이 적은 후보를 고른다. 개입이 작은 쪽이다.
3. 그래도 동률이면 (나) R-1 중앙값이 작은 후보를 고른다.
4. 그래도 동률이면 P5 > P3 > P53 순서로 고른다.
   - P5는 기존 필드의 값만 바꾼다.
   - P3은 새 필드 하나를 쓴다.
   - P53은 둘 다다.

- 판정서에는 1순위만이 아니라 통과한 모든 후보의 기준값을 표로 낸다.
- 알려진 한계(봉인 시점)
  - 하네스 이상 판독, 잡음 등급 L1~L3, U-3·U-6, Chrono 폐루프는 이 표적에 없다. 436.8 재개에서 처음 본다.
  - (가)는 설계에 쓴 격자와 같다(0절).
  - PS-7 사전 접지 시작 하네스 키는 없다(FB와 같은 한계).

## 10. 판정 두 경로와 산출물

- 실행 줄: `06_analysis/03_hydraulic/coupled/v5/las/rev/rev_R<묶음>.jsonl`(새 폴더). 저장 기준선은 덮어쓰지 않는다.
- 판정서: `06_analysis/02_control/verif_matrix/las_rev_judgement.md`
- 판정 경로
  1. python-expert 판정 도구 `las_rev_judge.py`
  2. control-expert 재집계 스크립트(판정 도구를 import하지 않고 jsonl만 읽음)
- 두 경로의 결과가 같아야 확정이다. 기준마다 참·거짓, 개수, 중앙·최대·최소값이 같아야 하고, 수치는 1e-9 kN·s 안이어야 한다. 다르면 원인을 적고 판정을 확정하지 않는다.
- 판정서에 적을 것
  - 이 규칙의 sha256
  - 0절 공개 내용
  - R-0 결과
  - K-1~K-4 결과
  - 기준별 결과 표
  - 예외 짝
  - R-P0 재현 수
  - 순위
  - 한계

## 11. 결과를 본 뒤 바꾼 것의 공개

- 이 판은 고치지 않는다. 후보 결과를 한 줄이라도 본 뒤 키·후보·값·기준·판정 정의를 바꾸면, 덧붙임 판 `las_rev_targeted_rules_rev<n>.md`와 `.sha256`으로 봉인한다. 덧붙임 판에는 다음을 적는다.
  1. 바꾼 항목, 이 판의 값, 새 값
  2. 바꾸기 전에 본 결과(묶음·줄 수)
  3. "결과를 본 뒤의 변경"이라는 표시
- 판정서는 이 판의 기준과 덧붙임 판의 기준으로 낸 결과를 둘 다 적는다.
- 도구가 이 문구와 다르게 구현된 것을 문구대로 고치는 것은 변경이 아니다. 다만 고친 내용과 다시 돈 줄을 판정서에 적는다.
