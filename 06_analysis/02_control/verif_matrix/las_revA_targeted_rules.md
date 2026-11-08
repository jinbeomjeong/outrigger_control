# LAS-b 개정 A안 표적·채택 규칙 (P5r = β 4.5 + 끝 완화 램프)

- 작성: control-expert, 2026-11-09
- 상태: **봉인.** sha256과 봉인 시각은 같은 폴더 `las_revA_targeted_rules.sha256`에 있다(LF 줄 끝, BOM 없음으로 계산). 이 파일은 더 고치지 않는다. 바꿀 일이 생기면 덧붙임 판 `las_revA_targeted_rules_rev<n>.md`로 봉인한다(12절).
- 사용자 결정(2026-11-09 새벽)
  - LAS-b 다음 개정은 A안(P5r = β 4.5 + 끝 완화 램프)을 표적한다.
  - 근거는 `las_rev_RG_analysis.md` 3절 후보 A다.
  - 실행은 이 봉인과 별도로 사용자 재승인을 받은 뒤에 한다.
- 이어받는 규칙(원판 구조와 문턱을 재사용한다. 다른 점은 이 파일에 적은 것뿐이다)
  - `las_rev_targeted_rules.md`(sha256 `bb235f27567240b205a544ed7cfd10237827e4627088e0eab1f62b318416ff60`, 이하 "원판")
  - `las_rev_targeted_rules_rev1.md`(sha256 `672bc8f81ba75419e5a201e05a94e2f9aead2de3c205f80c2661e7474cd9fd51`, 이하 "rev1")
  - 원판·rev1의 절 번호를 인용할 때는 "원판 5.2"처럼 적는다. 이 파일과 원판이 다르면 이 파일이 맞다.
- 규약
  - 이산 $T_s$ = 0.1 s, 출력 지연 $d$ = 1(주기 $k$의 명령은 $t_k+0.1$ s에 플랜트에 들어간다)
  - C2 음되먹임 그대로, 상태 되먹임 부호는 바꾸지 않는다
  - 다리 순서 FL, FR, RL, RR(0~3)
  - 힘은 실린더 순 힘이다. 단위는 칸마다 적는다(N 또는 kN). $F_{min}$ = 9,414.589 N
  - $v_{max}$ = 20.924 mm/s, $\gamma$ = 0.16(LAS-b 저속 평균 비)

## 0. 결과를 보기 전의 확정이다

- 이 규칙을 쓸 때 A안 후보로 돌린 실행은 **0줄**이다.
  - 램프 필드는 master(`ca2dc7f`)에도, $n_{min}$이 들어간 worktree 커밋 `19bf586`에도 없다. 저장소 전체 `.py`에 `end_ramp`·`P5r` 문자열이 없다(봉인 직전 검색).
  - 따라서 후보를 돌릴 코드와 도구가 아직 없다.
- 봉인 전에 본 것(모두 공개)
  1. 원판 R-G 결과 90줄(P5·P3·P53): worktree `agent-a2741b9caa5993f5c`의 `06_analysis/03_hydraulic/coupled/v5/las/rev/rev_RG.jsonl`, sha256 `7e8c3b4173f1fc682e665ad173589dbbe335ba914a06d5ef2984c5807bb8cca6`
  2. b0 진단 30줄 `v5/las/diag/diag_Db.jsonl`(sha256 `1436956a…`)과 그 판정서들
  3. 분석서 `las_rev_RG_analysis.md`(pre·post 회귀, 재가속 뒤 골, P53 대 P5 짝)
  4. P5 30줄의 `las` 필드(시작·끝·끝 사유·작동 주기·축척 주기)와 `diag` 블록 구조(`periods[].cmd_mm_s`, `force_window`). 봉인 전 점검 스크립트는 control-expert scratchpad `control_lasrevA\inspect_rg.py`, `inspect_diag.py`다(읽기 전용).
  5. 램프 잔류 들뜸 계산(3.3절): `control_lasrevA\ramp_residual.py`(Python 닫힌 식 + 2차 모드 시간 시뮬레이션)와 Julia 닫힌 식(control-julia 상주 세션). 플랜트 실행은 없다.
- **과적합 공개(사용자 지정 문구를 그대로 둔다)**: R-G 격자는 설계에 **두 번** 쓴 격자다(원판 설계 D-b, 이번 설계 R-G 분석). 그래서 **(가) R-G 통과는 기구 확인일 뿐이다. 일반화 근거는 (나)·(다)다.**
  - 이번에 더한 R-H(3.2절, 반 칸 위상 격자)는 같은 두 키·같은 플랜트에서 위상만 새로 뽑은 표본이다. 위상 기구에 대해서는 표본 밖이지만, 다른 조건(경사·토양·잡음·Chrono)으로의 일반화 근거는 아니다.
  - 잡음 등급 L1~L3, Chrono, 436.8 재개 묶음은 이 표적에 없다(10절 한계).

## 1. 후보 정의

### 1.1 기호

| 기호 | 뜻 | 단위 | 코드(부록 A) |
|---|---|---|---|
| $\beta$ | S7_light 문턱 | $F_{min}$의 배수 | `LiftoffApproachSlowSettings.light_leg_fraction_of_F_min`(기존) |
| $n_{min}$ | `sum` 끝 최소 작동 주기 | 주기 | `min_active_periods`(원판 ③, 이 표적에서는 늘 0) |
| $N_r$ | 끝 완화 램프 주기 수 | 주기 | `end_ramp_periods`(**새 필드**, 기본 0) |
| $k_e$ | LAS-b 끝 주기(`las.end_t_s`) | 주기 | `_end_liftoff_slow` |
| $u_k$ | LAS-b 단계에 들어온 다리 속도 명령(4) | m/s | `_apply_liftoff_approach_slow`의 `leg_speeds` |
| $\bar u_k$ | $u_k$의 네 다리 평균 | m/s | `np.mean(leg_speeds)` |
| $\lambda_0$ | 끝 직전 마지막 작동 주기에 실제로 쓴 축척 | — | 그 주기가 축척됐으면 $\gamma v_{max}/\bar u$, 아니면 1 |
| $m$ | 램프 단계 번호($k_e$에서 1) | — | `ramp_step` |
| $\lambda_m$ | 램프 축척 | — | 1.3절 식 |

### 1.2 후보 표

| 이름 | $\beta$ | $n_{min}$ | $N_r$ | 쓰는 곳 | 설정(`las` = `C2Config.with_10hz_d1().liftoff_approach_slow`) |
|---|---|---|---|---|---|
| **P0**(b0) | 3.5 | 0 | 0 | R-0, R-P0, R-X | 프리셋 그대로 |
| **P5**(기준, 원판 ⑤) | 4.5 | 0 | 0 | R-0P5, R-H 기준 | `replace(las, light_leg_fraction_of_F_min=4.5)` |
| **P5r4** | 4.5 | 0 | **4** | 판정 후보 | `replace(las, light_leg_fraction_of_F_min=4.5, end_ramp_periods=4)` |
| **P5r6** | 4.5 | 0 | **6** | 판정 후보 | `replace(las, light_leg_fraction_of_F_min=4.5, end_ramp_periods=6)` |

- 나머지 값은 b0 그대로다: $\alpha$ 0.6, $\gamma$ 0.16, $\alpha_{end}$ 0.85, $n_{end}$ 5, $T_{max}$ 1.5 s, $\rho_{on}$ 0.18, `require_soil_response` 참.
- 프리셋 기본값은 바꾸지 않는다. 후보는 실행 도구가 설정을 덮어써서 만든다(원판 7.2와 같음). 채택이 결정된 뒤에만 프리셋 기본값을 바꾼다.
- 분석서 3절의 "$N_r$ = 5(0.5 s)"는 "1/3 → 1을 0.5 s에 걸쳐"라는 뜻이었다. 이 규칙의 정의(1.3절)로는 같은 길이가 $N_r$ = 4(같은 크기 계단 5개, 창 0.5 s)다. 이름이 바뀐 것이지 설계 의도가 바뀐 것은 아니다.

### 1.3 끝 완화 램프 식

LAS-b 끝 사유가 `sum` 또는 `time`이고 $N_r\ge1$, $\lambda_0<1$이면 램프를 시작한다. 그 밖의 끝(`loc`, `phase`, `soil`, `reapproach`, `zone`)은 b0처럼 바로 끝난다(램프 없음). 안전·단계 끝은 막지 않는다는 원판 1.4의 원칙을 그대로 따른다.

$$\lambda_m=\lambda_0+(1-\lambda_0)\,\frac{m}{N_r+1},\qquad m=1,\dots,N_r$$

- $m$ = 1은 끝 주기 $k_e$다. b0에서 끝 주기는 축척 없이 $u$를 그대로 냈다. A안에서는 끝 주기부터 램프가 작용한다. $m$은 그 뒤 LEVEL 주기마다 1씩 오른다(축척이 실제로 걸렸는지와 무관).
- 각 램프 주기의 출력은 다음과 같다.
  $$u^{out}_k=\begin{cases}u_k\,\max\!\left(\lambda_m,\ \dfrac{\gamma v_{max}}{\bar u_k}\right) & \bar u_k>\gamma v_{max}\\[4pt] u_k & \text{그 밖}\end{cases}$$
  - 아래쪽 한계 $\gamma v_{max}/\bar u_k$는 램프가 LAS-b 저속보다 더 느리게 만들지 않게 한다. 두 항 모두 1보다 작으므로 $u^{out}$은 $u$보다 빠르지 않다.
  - 축척은 네 다리에 같은 값이다(LAS-b 본체와 같은 모양). 그래서 비틀림·자세 성분의 비는 바뀌지 않는다.
- $m=N_r+1$이 되는 주기부터 축척 1이다(램프 끝, 사유 `done`). 같은 크기 계단 $N_r+1$개가 $T_s$ 간격으로 들어가므로, 출력이 1/3에서 1로 가는 창은 $(N_r+1)T_s$다(P5r4 0.5 s, P5r6 0.7 s).
- 램프 취소: 램프 주기를 계산하기 전에 아래를 이 순서로 본다. 하나라도 참이면 그 주기부터 축척 1이고 램프는 끝난다(사유 기록).
  1. `loc`: 확정 LOC를 봤다(`has_loc_been_seen`)
  2. `phase`: 이 주기에 LEVEL 단계가 없다(`_finish_liftoff_slow_period` 경로)
  3. `soil`: 토양 모드가 시작됐다
  4. `reapproach`: 재접근 다리가 있다
  5. `zone`: `require_soil_response`가 거짓이고 크롤러 구역을 벗어났다
  - 끝 주기 $k_e$에서는 끝 표가 1~5를 먼저 봤으므로 취소가 일어나지 않는다.
- 놓는 곳: LAS-b 단계(P-S8-30 다음, 차등 침하 가산·행정 가드·증분 제한 앞)다. LAS-b 본체와 같은 곳이다. 뒤 단계(증분 제한 0.25 $v_{max}$/주기, 행정 가드, 차등 침하 가산)는 그대로 작용한다.
- **기본값 = 비트 동일**: $N_r$ = 0이면 램프 상태가 생기지 않고 명령·사건이 b0(β 3.5)·P5(β 4.5)와 비트 같아야 한다(7.1절 R-0·R-0P5).

### 1.4 $N_r$ 선택 근거 (결과 전 결정)

- 기구(분석서 2.2~2.5): 이륙 뒤 최소 RL 힘은 재가속 계단이 이륙 로킹(주기 약 0.5 s 추정)의 어느 위상에 들어가는가로 깊이가 바뀐다. 계단을 같은 크기 $N_r+1$개로 나누면, 주기 $P$인 가벼운 감쇠 모드에 남는 잔류 진폭은 한 계단 대비 다음 비가 된다.
  $$A(N_r,P)=\left|\frac{\sin\!\big((N_r+1)\,\omega T_s/2\big)}{(N_r+1)\,\sin(\omega T_s/2)}\right|,\qquad \omega=2\pi/P$$

| 기호 | 뜻 | 단위 |
|---|---|---|
| $A$ | 램프 뒤 잔류 진폭 / 한 계단 잔류 진폭 | — |
| $P$ | 이륙 로킹 주기(추정 0.5 s, 창 하나에서 어림) | s |
| $\omega$ | 각진동수 | rad/s |

- 계산(Python 닫힌 식 = Julia 닫힌 식, 표의 자리까지 같음. Python 2차 모드 시뮬레이션($\zeta$ 0.05)은 감쇠 때문에 닫힌 식과 최대 0.07 다르고 경향은 같다)

| $N_r$ | 창 $(N_r+1)T_s$ [s] | $A$($P$ 0.5) | 최악 $P\in[0.4,0.6]$ | 최악 $P\in[0.4,0.8]$ | READY 지연 어림 [s] |
|---|---|---|---|---|---|
| 0 | 0.1 | 1 | 1 | 1 | 0 |
| 2 | 0.3 | 0.539 | 0.667 | 0.805 | 0.07 |
| 3 | 0.4 | 0.250 | 0.433 | 0.653 | 0.10 |
| **4** | 0.5 | **0** | **0.200** | 0.483 | 0.13 |
| 5 | 0.6 | 0.167 | 0.239 | 0.308 | 0.17 |
| **6** | 0.7 | 0.231 | 0.233 | **0.233** | 0.20 |
| 8 | 0.9 | 0.111 | 0.222 | 0.227 | 0.27 |

  - READY 지연 어림은 램프로 잃는 이동을 전속 시간으로 바꾼 값이다: $T_s\sum_{m=1}^{N_r}(1-\lambda_m)=T_s(1-\lambda_0)N_r/2$, $\lambda_0$ = 1/3 가정. 자세 루프가 일부를 메우므로 상한 쪽 어림이다.
- 결정
  - **$N_r$ = 4**: 추정 주기 0.5 s에서 영점이고, $P\in[0.4,0.6]$에서 최악 0.20이 되는 가장 작은 $N_r$다($N_r$ = 3은 0.43). 개입이 가장 작은 유효 후보다.
  - **$N_r$ = 6**: 로킹 주기 추정이 창 하나의 어림이라 길게 틀렸을 경우의 보험이다. $P\in[0.4,0.8]$ 전체에서 최악 0.233으로 고르다. $N_r$ = 4는 $P$ 0.8 s에서 0.48로 나빠진다.
  - 버린 값: $N_r\le3$(0.5 s 근처에서 잔류가 0.25 이상), $N_r$ = 5(4와 6 사이로 정보가 적다), $N_r\ge7$(최악이 6과 같고 지연만 는다).
  - 후보를 둘로 한 이유: 하나($N_r$ 4)만 두면 주기 추정이 틀렸을 때 기구가 맞아도 미달이 난다. 셋 이상은 같은 격자 반복 사용을 늘린다.
- 한계: 이 식은 계단 입력과 단일 모드만 본다. 실제로는 증분 제한(0.25 $v_{max}$/주기)이 b0 계단을 이미 1~2주기로 나누고, 플랜트 명령 램프 0.1 s와 밸브 지연이 더 거른다. 또 최소 힘에는 이륙 자체의 출렁임(램프와 무관)도 들어 있다. 그래서 위 표는 순서를 정하는 근거일 뿐, 힘 예측이 아니다.

## 2. 사전 예측

### 2.1 구현 검증 예측 (어긋나면 구현 결함, 8절 H-3)

같은 격자점의 P5 줄(R-G는 저장 `rev_RG.jsonl` P5 30줄, R-H는 이번 R-H P5 기준 줄)과 짝짓는다.

| # | 예측 | 근거 |
|---|---|---|
| K-A1 | 모든 R-G·R-H 후보 줄에서 `las.start_t_s`, `las.end_t_s`, `las.end_reason`, `las.active_periods`, `las.scaled_periods`, `las.start_leg`가 P5 짝과 같다(실수는 비트 같음) | 끝 주기까지 명령이 P5와 같고, 끝 판정은 그 주기 출력 전에 난다 |
| K-A2 | `diag.periods`에서 $t_s<$ `las.end_t_s`인 모든 주기의 `cmd_mm_s` 4값이 P5 짝과 비트 같다 | 같음 |
| K-A3 | `diag.summary.t_lift_s`가 P5 짝과 같다(R-G 30줄 모두. P5에서 이륙이 늘 재가속 출력 $t_e+0.1$ 전에 났다: post 0.21~0.43 s, 분석서 2.2) | 플랜트는 $t_e+0.1$ s까지 P5와 같은 입력을 받는다 |
| K-A4 | `diag.force_window` 행 가운데 P5 짝 창과 시각이 겹치고 $t<$ `las.end_t_s` + 0.1 s인 행은 16열 모두 비트 같다 | 같음 |
| K-A5 | 끝 사유가 `sum`·`time`이고 $\lambda_0<1$인 줄은 `commands_sha256`이 P5 짝과 **다르다**. 그리고 `las.ramp.start_factor` = $\lambda_0$, `las.ramp.end_reason` ∈ {`done`, `loc`, `phase`, `soil`, `reapproach`, `zone`}, `las.ramp.periods_applied` ≤ $N_r$(`done`이면 = $N_r$) | 램프가 실제로 걸렸는지 확인 |
| K-A6 | 끝 사유가 `loc`·`phase`·`soil`·`reapproach`·`zone`이거나 $\lambda_0$ = 1인 줄은 `las.ramp.periods_applied` = 0 | 1.3절 시작 조건 |
| K-A7 | `las.start_t_s`가 None인 줄(LAS-b 미시작)은 `commands_sha256`이 짝 기준(L 또는 P5)과 같다 | 시작하지 않으면 LAS-b는 명령을 바꾸지 않는다 |
| K-A8 | 줄의 `las.settings`(컨트롤러가 실제로 쓴 설정 asdict)의 $\beta$·$n_{min}$·$N_r$가 1.2절 후보 표와 같다 | 덮어쓰기 누락 검출(원판 K-4) |

- 참고: R-G 30점의 P5 값은 모두 끝 사유 `sum`, `scaled_periods` = `active_periods`(7~11)다. 따라서 30줄 모두 램프가 걸려야 한다(K-A5).
- K-A7은 (나)·(다)에도 쓴다. (나)·(다)에서 P5의 시작 여부는 미리 정할 수 없다(원판 2.3과 같은 사정).

### 2.2 기구 예측 (가설, 판정 기준 아님. 어긋나면 "기구 기각"으로 적는다)

짝 차 $\Delta F=F_{RL}^{cand}-F_{RL}^{P5}$ [kN](같은 격자점). $F_{res}$(재가속 시점 힘)는 K-A4로 P5와 같으므로, $\Delta F>0$이면 재가속 골(drop)이 줄었다는 뜻이다.

| # | 예측 | 기각(기구 가설) |
|---|---|---|
| M-1 | 후보마다 R-G + R-H 54짝의 $\Delta F$ 중앙값 > 0 | 중앙값 ≤ 0 |
| M-2 | 후보마다 R-G 6칸의 $\max_c R_c$가 P5의 1.105 kN보다 작다 | ≥ 1.105 kN |
| M-3 | **V0 갈래 A 6줄**(V0 c0.94 j1·j3, V0 c1 j0·j2·j4, V0 nom j3; P5 값 10.771, 10.650, 10.740, 10.764, 10.728, 11.314 kN)에서 $\Delta F>0$인 줄이 ≥ 4/6 | 6줄 모두 $\Delta F<0$ |

- **V0 갈래 A의 G-1 여유(0.25 kN)에 대한 예측: 오른다.**
  - 근거: 갈래 A는 P5(=b0)에서 pre 0.56~0.86 s로 이미 정상 저속에서 이륙했고, 골의 대부분이 재가속 drop 4.5~4.7 kN이다(분석서 2.2 표). 이 drop이 계단 들뜸이라면 램프가 줄인다.
  - 기대 범위(가설): V0 갈래 A 6줄의 $F_{RL}$ 11.0~12.0 kN(drop이 P5 c1 갈래 B 수준 1~2 kN에서 3 kN 사이로). 갈래 B nom 7줄도 같은 범위로 올라 칸 안 범위가 좁아진다.
  - 반대 위험(공개): P3 연장은 재가속 위상만 옮겨 10/12줄이 −0.07 ~ −0.32 kN 내려갔다(분석서 2.4). 램프는 계단 크기를 줄이므로 이와 다르다고 보지만, 이륙 출렁임의 내려가는 위상에서 램프 앞부분이 들어가면 내려갈 수 있다. 그래서 G-1 문턱은 바꾸지 않고 그대로 판정한다.
- READY(참고): 램프가 걸린 줄의 READY는 P5 짝보다 +0.1 ~ +0.3 s 늦을 것이다(1.4절 어림).
- 기구 기각이 나와도 그 자체로 미달은 아니다. 미달은 5절 기준으로만 정한다. 다만 두 후보 모두 M-1 또는 M-3이 기각되면, 램프 길이를 바꾼 후속 후보는 만들지 않고 묻는다(8절 H-11).

## 3. 묶음과 건수·비용

| # | 묶음 | 키·작업 | 후보 | 건수 | CPU 추정 | 벽시계(P 8 + E 12) |
|---|---|---|---|---|---|---|
| R-0 | 비트 시험 b0 | 원판 7.1의 6작업 | P0(새 코드, 기본값) | 6 | 약 8분 | 약 3분 |
| R-0P5 | 비트 시험 P5 | R-G 30점 | P5(새 코드, $N_r$ 0) | 30 | 약 15분 | 약 3분 |
| R-G | (가) 위상 격자 | 원판 3.1과 같은 30점 | P5r4, P5r6 | 60 | 약 31분 | 약 5분 |
| R-H | (가) 반 칸 위상 격자 | 3.2절 24점 | P5(기준), P5r4, P5r6 | 72 | 약 37분 | 약 5분 |
| R-T | (나) T-1·T-2 | 원판 3.2의 192키 | (가) 통과 후보 | ≤ 384 | ≤ 약 450분 | 후보당 약 20분 |
| R-S | (다) 토양·사건 | 원판 3.3의 30작업 | (가) 통과 후보 | ≤ 60 | ≤ 약 104분 | 후보당 약 6분 |
| R-P0 | 기준 재현 | R-T·R-S에서 어느 후보든 해시가 바뀐 키의 합집합 | P0 | ≤ 222(예상 60~100) | ≤ 약 260분 | 약 8~25분 |
| R-X | 예외 근거 | 6절 예외를 주장하는 짝의 L | P0(DONE 기록 켬) | ≤ 10 | ≤ 약 15분 | 약 3분 |

- **예상 건수**: 반드시 168건(R-0 6 + R-0P5 30 + R-G 60 + R-H 72). 두 후보가 (가)를 통과하면 상한 합계 844건(168 + 384 + 60 + 222 + 10), CPU 약 15 시간, 벽시계 약 1.3시간이다. 추정 근거는 원판 3절과 같다(R-G 실측 90줄 약 46 CPU-분).
- 실행 순서: R-0 → R-0P5 → R-G + R-H → (가) 통과 후보만 R-T·R-S → R-P0 → R-X → 판정
  - R-0 또는 R-0P5가 한 줄이라도 어긋나면 그다음을 돌지 않는다(H-2).
  - (가)에서 실패한 후보는 R-T·R-S를 돌지 않는다.
- 배치는 compute-scheduler-expert 배치표를 받는다. 스레드는 1로 고정한다(`fb_targeted.thread_problems`).
- 출력 폴더는 **새 폴더** `06_analysis/03_hydraulic/coupled/v5/las/revA/`다. 줄 파일 `revA_R<묶음>[_<후보>].jsonl`. 원판 폴더 `v5/las/rev/`에는 쓰지 않는다(원판 도구의 묶음 정체성 검사와 섞이지 않게).

### 3.1 R-G (가) 위상 격자

- 원판 3.1과 같다: 두 키(`D1|H-R-A|rigid+J1@FR|T|diag-op|K3|VB|e0.002`, `…|V0|e0.002`), $s_c\in\{1.0,0.94,0.8768421\}$, $j$ = 0..4, $\delta$ = 0.025 s, TOUCH 전용 예산, 검출(U·A97) 끔, 주기 기록 켬.
- 줄 이름 `<후보>-LT-c<중심>-j<j>`.
- 짝 기준은 저장 `rev_RG.jsonl`(sha256 `7e8c3b41…`, 0절)의 P5 30줄이다. 이 파일을 실행 트리로 복사해 쓸 때도 sha256을 대조한다(H-10).

### 3.2 R-H (가) 반 칸 위상 격자 (표본 밖 위상)

- 같은 두 키, 같은 세 중심, 같은 예산 규칙이다. $j\in\{0.5,\,1.5,\,2.5,\,3.5\}$만 다르다.
  $$s_{c,j}=s_c\,\frac{T_c}{T_c+j\,\delta},\qquad T_c=T_1/s_c,\ \delta=0.025\ \mathrm{s}$$
  - TOUCH 끝을 12.5, 37.5, 62.5, 87.5 ms 늦춘다. R-G 점 사이의 위상이다. b0 V0 c 1에서 본 실효 위상 주기 약 50 ms(진단 판정서 1절)의 반 칸이므로, R-G가 뽑지 않은 위상을 뽑는다.
- 2 키 × 3 중심 × 4점 = 24점. 후보 셋(P5, P5r4, P5r6) = 72줄.
- 줄 이름 `<후보>-LH-c<중심>-j<j>`(소수점은 `p`, 예: `P5r4-LH-cnom-j1p5`). 기록 `diag.touch_budget.j`는 실수로 남긴다.
- P5 24줄은 판정 대상이 아니다. K-A1~K-A4와 M-1의 짝 기준이고, P5 자체의 표본 밖 값으로 함께 적는다.

### 3.3 R-T, R-S, R-P0, R-X

- 키, 작업 dict, 짝 기준(L = 저장 b0, `las_T1.jsonl`·`las_T2.jsonl`·`fb_F3.jsonl`·`fb_F4.jsonl`의 L 줄), DONE 기록, 재현·예외 방법은 원판 3.2·3.3·6·7.3과 같다.
- 원판 K-1·K-2(갈래 A 비트 동일, 시작 시각 표)와 K-3(P3 비트 동일 집합)은 **이 표적에서 쓰지 않는다.** A안은 끝 뒤 명령을 바꾸므로 갈래 A도 바뀐다. 대신 2.1절 K-A1~K-A8을 쓴다.

## 4. 줄마다 기록할 것

- 원판 4.1(정체성)·4.2(DONE 기록) 그대로다. 다음을 더하거나 바꾼다.
  - 이 규칙 파일 sha256(`rules_revA_sha256`). 원판·rev1 sha256도 함께 적는다.
  - `controller_tag` ∈ {`final_C4G2_LAS`, `final_C4G2_P3_LAS`}
  - `las.settings`에 `end_ramp_periods`, `las.params.n_r`
  - `las.ramp`: `n_r`, `start_factor`($\lambda_0$, 램프 없으면 None), `periods_applied`, `scaled_periods`, `end_t_s`, `end_reason`
  - `diag.periods[].las`(작동·램프 주기): `ramp_m`, `ramp_factor`($\lambda_m$), `ramp_scaled`(축척이 실제로 걸렸는지)
- 한 후보의 모든 줄은 한 커밋에서 나와야 한다. dirty 허용은 원판 4.1과 같다.

## 5. 채택 기준

모든 기준은 같은 키·같은 설정의 짝으로 본다. 판정 필드는 원판 5절 표 + 4절의 새 필드다.

### 5.0 None·누락·`d1.items` 규칙

- 원판 5.0을 그대로 쓴다.
- rev1 R1-1~R1-4를 처음부터 포함한다.
  - R1-1: `d1.items` 비교 범위는 L과 후보의 키 합집합 $U$다. 원판 13개 이름은 예시다.
  - R1-2: 한쪽에만 있는 키는 다른 쪽을 None으로 보고 5.0 항목 규칙을 쓴다(L에만 있고 L 참 → 위반, 후보에만 있고 후보 거짓 → 위반, 그 밖은 위반 아님). 짝마다 `items_only_L`, `items_only_cand`를 적는다.
  - R1-3: 판정 불가는 `d1`·`d1.items`가 없을 때와, `commands_sha256`이 L과 같은데 `d1.items`가 다를 때(판정기 표류)뿐이다.
  - R1-4: 두 판정 경로 모두 R1-1~R1-3으로 계산하고 짝별 위반 목록·`items_only_*`가 같아야 한다.

### 5.1 (가) R-G + R-H (후보마다)

| # | 기준 | 정의 |
|---|---|---|
| G-1 | 하중(R-G) | 30줄 모두 `F_RL_kN` ≥ 10.400이고 `F_judged_min_kN` ≥ 10.400 |
| G-2 | 위상 범위(R-G) | 6칸 모두 $R_c=\max_{j\le3}F_{RL}-\min_{j\le3}F_{RL}$ ≤ 0.500 kN. 칸마다 $j$ = 0..3의 4줄이 있어야 한다 |
| G-1H | 하중(R-H) | 24줄 모두 `F_RL_kN` ≥ 10.400이고 `F_judged_min_kN` ≥ 10.400 |
| G-2H | 위상 범위(R-G ∪ R-H) | 6칸 모두 $R^{\cup}_c=\max-\min$ over $j\in\{0,0.5,1,1.5,2,2.5,3,3.5\}$ ≤ 0.500 kN. 칸마다 8줄이 있어야 한다 |
| G-3 | 제외 검사 | 원판 G-3을 R-G 30줄·R-H 24줄 각각에 쓴다(모든 줄 존재, 오류 0, `level_budget_periods` = 0, `gate_consistent` 참) |
| G-4 | 구현 예측 | 2.1절 K-A1~K-A6·K-A8 |

- 참고 기록(판정 아님): 줄마다 시작·끝 주기, 작동 주기, 끝 사유, 이륙 시각, $\lambda_0$, 램프 끝 사유, $F_{res}$, drop, 최소 다리 이름, 최소 시각과 $t_e+0.1$의 차. 칸마다 $M_c$, $P_c$, P5 대비 $\Delta F$. 2.2절 M-1~M-3 결과.
- 문턱은 원판과 같다. 10.400 kN(사용자 지정)과 10.4146 kN(원판 C1 $F_{min}$ + 1 kN) 사이의 줄은 따로 적는다. $R_c$는 갈래 B가 A보다 높아져도 커진다. 그래도 미달로 센다(원판 5.1).

### 5.2 (나) R-T, 5.3 (다) R-S

- 원판 5.2·5.3을 그대로 쓴다: C-2형(a)~(c), C-1 유지, C-F, C-S, A-3(H-R-0 48키 해시 = L), R-1(READY 중앙 ≤ +1.0 s), R-2(최대 ≤ +5.0 s), $\mathcal{P}$ 빈 집합 처리, (다) verdict 사례 10짝.
- A-3 공개: β 4.5에서 H-R-0 키의 LAS-b 시작 여부는 미리 모른다. 시작하면 A-3이 실패할 수 있다. 원판과 같은 사용자 결정(A-3 유지)을 따른다.
- K-A7은 (나)·(다) 모든 줄에 쓴다(구현 예측, 어긋나면 H-3).

### 5.4 판정 분류와 순서 (원판 판정 뒤 감사에서 정한 분류, 처음부터 넣음)

후보마다 다음 순서로 하나의 상태를 정한다. 앞의 것이 이긴다.

| 순서 | 상태 | 조건 |
|---|---|---|
| 1 | `stop` | 구현 예측 어긋남(G-4, (나)·(다)의 K-A7·K-A8). 구현 결함 후보다. 어긋나서 돌지 못한 줄이 있어도 기준 미달로 세지 않는다 |
| 2 | `undecidable` | 정체성 위반(4절, 원판 4.1), 제외 검사 G-3 실패, 판정 필드 누락(5.0), 작업 dict 불일치, $\mathcal{P}$ 빈 집합인데 해시가 바뀐 짝이 있음 |
| 3 | `fail` | G-1, G-2, G-1H, G-2H, (나)·(다) 기준 가운데 하나라도 미달 |
| 4 | `pass` | 모든 기준 통과 → 채택 권고(원판 6절 예외 한도 H-9는 그대로) |
| — | `incomplete` | 그 묶음의 줄이 하나도 없음(빈 후보) 또는 (가) 통과 뒤 (나)·(다)를 아직 돌지 않음 |

- **빈 후보**(어느 묶음의 줄이 0줄)는 통과도 미달도 아니다. `incomplete`로 적고 H-6 개수에 넣지 않는다.
- H-6은 G-1·G-2·G-1H·G-2H 미달로 `fail`인 후보만 센다. `stop`·`undecidable`·`incomplete`는 세지 않는다.
- 판정 도구의 종료 코드: `stop`·`undecidable`이 있거나 멈춤 조건이 걸리면 1, 아니면 0(원판 도구와 같은 뜻).

## 6. C-4 예외 (관문 시점 분기)

- 원판 6절을 그대로 쓴다. 추가 조건: 후보 줄의 $\ell$에 든 재시작(`resets`)이 모두 LAS-b 끝 **그리고 램프 끝**(`las.ramp.end_t_s`, 램프가 없으면 `las.end_t_s`) 뒤에 있어야 한다.

## 7. 비트 시험·재현

### 7.1 R-0 (b0)

- 원판 7.1의 6작업을 새 코드(필드 `end_ramp_periods` 기본 0, `min_active_periods` 기본 0, 프리셋 그대로)로 돌린다. `commands_sha256` 64자가 원판 7.1 표의 저장값과 같아야 한다.

### 7.2 R-0P5 ($N_r$ = 0이면 P5와 비트 동일)

- 새 코드에서 $\beta$ 4.5, $N_r$ = 0(필드를 명시적으로 0으로 줌)으로 R-G 30점을 돌린다.
- 30줄 모두 `commands_sha256` 64자가 저장 `rev_RG.jsonl`의 같은 격자점 P5 줄과 같아야 한다. `diag.summary.F_RL_kN`도 비트 같아야 한다.
- 이 시험이 통과해야 R-G 후보 줄을 저장 P5 줄과 짝지을 수 있다.

### 7.3 단위 시험 (python-expert, 부록 A)

- $N_r$ = 0에서 LAS-b 작동 시나리오 명령이 비트 같다(β 3.5·4.5 모두).
- $N_r$ = 4에서 끝 주기부터 축척 열이 $\lambda_0+(1-\lambda_0)m/5$, $m$ = 1..4, 그다음 1이다(손 계산과 1e-15 안).
- 아래쪽 한계: $\bar u$가 작아 $\gamma v_{max}/\bar u>\lambda_m$이면 출력 평균이 $\gamma v_{max}$다. $\bar u\le\gamma v_{max}$면 $u$ 그대로다.
- 취소: 램프 중 LOC·LEVEL 아님·토양 모드·재접근·구역 이탈에서 그 주기부터 축척 1이고 사유가 기록된다.
- 끝 사유 `loc`·`phase`·`soil`·`reapproach`·`zone`에서는 램프가 생기지 않는다.
- `end_ramp_periods` 음수·정수 아님은 `ValueError`다. 옛 피클(필드 없음)을 읽으면 0이다.
- $N_r$ = 0이면 새 사건이 생기지 않는다.

### 7.4 R-P0, R-X

- 원판 7.3·6절과 같다.

## 8. 멈춤 조건

| # | 조건 | 처리 |
|---|---|---|
| H-1 | 이 파일·`.sha256`이 없거나 LF 기준 sha256이 다르다. 원판·rev1도 같다 | 실행하지 않는다 |
| H-2 | R-0(6) 또는 R-0P5(30) 한 줄이라도 불일치 | 모든 묶음을 멈춘다. python-expert가 고친 뒤 R-0부터 다시 한다 |
| H-3 | 구현 예측 K-A1~K-A8 불일치 | 그 후보의 모든 묶음을 멈춘다(상태 `stop`) |
| H-4 | 정체성 위반, 판정 필드 누락, 작업 dict 불일치 | 그 묶음을 멈추고 `undecidable`로 보고한다 |
| H-5 | R-P0 또는 R-X 재실행 해시 ≠ 저장 L 해시 | 모든 판정을 멈추고 기준 재현 실패로 보고한다 |
| H-6 | 두 후보 모두 (가) `fail`(G-1·G-2·G-1H·G-2H) | 멈추고 묻는다. (가) 결과 전부와 M-1~M-3을 붙인다 |
| H-7 | 실행 오류 줄 | 원판 H-7과 같다. R-G·R-H는 G-3대로 그 묶음 전체를 다시 돈다 |
| H-8 | 한 후보의 R-T 또는 R-S에서 C-2형 위반 짝 누적 5 이상 | 그 후보의 남은 실행을 멈춘다 |
| H-9 | 예외 과다(원판 6절 한도) | 자동 권고하지 않고 묻는다 |
| H-10 | 짝 기준 `rev_RG.jsonl`이 없거나 sha256이 `7e8c3b41…8cca6`이 아니다 | R-0P5·R-G를 돌지 않는다 |
| H-11 | 두 후보 모두 M-1 또는 M-3 기각 | 판정은 5절대로 끝까지 내되, 램프 길이를 바꾼 후속 후보를 만들지 않고 묻는다 |

- 미달이어도 값을 바꿔 다시 돌리지 않는다. 다른 $N_r$, 다른 $\beta$, 후보 B(이륙 정착 끝)·C(이륙 전 저속 보장)는 사용자 결정으로만 고른다.

## 9. 순위 규칙 (둘 다 채택 권고일 때)

1. (가) R-G + R-H 54줄의 $\min$ `F_judged_min_kN`이 큰 후보. 차가 0.3 kN 안이면 동률이다.
2. (나)+(다) 222짝에서 해시가 바뀐 짝이 적은 후보
3. (나) R-1 중앙값이 작은 후보
4. P5r4 > P5r6(개입이 작은 쪽)

- 판정서에는 통과한 모든 후보와 P5(R-H 기준)의 값을 표로 낸다.

## 10. 판정 두 경로·산출물·한계

- 판정서: `06_analysis/02_control/verif_matrix/las_revA_judgement.md`
- 판정 경로
  1. python-expert 판정 도구(원판 `las_rev_judge.py`를 이 규칙으로 확장하거나 `las_revA_judge.py`)
  2. control-expert 재집계 스크립트(판정 도구를 import하지 않고 jsonl만 읽음)
- 두 경로가 기준별 참·거짓, 개수, 중앙·최대·최소값, 실패 키, 짝별 위반 목록에서 같아야 확정이다. 수치는 1e-9 kN·s 안이어야 한다. 판정 도구는 $R_c$·$M_c$·$P_c$·$\Delta F$를 전체 자리로 출력한다(원판 판정에서 3자리 출력이라 직접 대조를 못 했다).
- 판정서에 적을 것: 이 규칙·원판·rev1 sha256, 0절 공개, R-0·R-0P5 결과, K-A1~K-A8, M-1~M-3, 기준별 표, 상태 분류(5.4), 예외 짝, R-P0 재현 수, 순위, 한계.
- 알려진 한계(봉인 시점)
  - 로킹 주기 0.5 s는 창 하나의 어림이다. $N_r$ 선택은 그 가정에 기댄다(1.4절).
  - 하네스 이상 판독, 잡음 등급 L1~L3, U-3·U-6, Chrono 폐루프, 다른 경사의 이륙 위상은 이 표적에 없다. 436.8 재개에서 처음 본다.
  - (가)는 같은 두 키의 위상 표본뿐이다(0절).
  - PS-7 사전 접지 시작 하네스 키는 없다(원판과 같음).

## 11. 실행 전 요건

- 이 봉인은 실행 승인이 아니다. 실행은 사용자 재승인 뒤에만 한다.
- 실행 전 감사: verif-protocol-auditor `[시점] 실행 전`(규칙 봉인, 도구↔규칙, 정체성, 빈 집합).
- 구현은 부록 A 명세로 python-expert가 한다. 구현 뒤 R-0·R-0P5부터 돈다.

## 12. 결과를 본 뒤 바꾼 것의 공개

- 원판 11절과 같다. A안 후보 결과를 한 줄이라도 본 뒤 키·후보·값·기준·판정 정의를 바꾸면 덧붙임 판 `las_revA_targeted_rules_rev<n>.md`와 `.sha256`으로 봉인하고, 바꾼 항목·이 판의 값·새 값, 바꾸기 전에 본 결과, "결과를 본 뒤의 변경" 표시를 적는다.
- 도구를 이 문구대로 고치는 것은 변경이 아니다. 고친 내용과 다시 돈 줄은 판정서에 적는다.

## 부록 A. python-expert 구현 명세

### A.1 기준 코드

- $n_{min}$ 필드(`min_active_periods`)와 원판 도구(`las_rev_targeted.py`, `las_rev_judge.py`)는 worktree 브랜치 `worktree-agent-a2741b9caa5993f5c`(커밋 `3c129ea` → `19bf586`)에만 있고 master(`ca2dc7f`)에 없다. 먼저 그 변경을 master 기준 작업 브랜치에 가져온다(병합 여부는 메인 세션 결정). A안 필드는 그 위에 더한다.

### A.2 `03_src/outrigger_sim/control/c2.py`

- `LiftoffApproachSlowSettings`에 필드 하나를 더한다.
  ```python
  end_ramp_periods: int = 0
  """``N_r`` (las_revA_targeted_rules.md 1.3): after a ``sum`` / ``time`` end, scale the
  command by lambda_m = lambda_0 + (1 - lambda_0) m / (N_r + 1), m = 1..N_r (m = 1 at the
  end period), floored at the slow mean; 0 keeps the b0 / P5 commands bit for bit;
  configs unpickled from older code read 0."""
  ```
  - `__post_init__`: `int`(bool 제외)이고 ≥ 0이 아니면 `ValueError`.
- `_LiftoffSlowState`에 더한다: `last_scale_factor: float = 1.0`(마지막 작동 주기에 쓴 축척), `ramp_step: int = 0`(0 = 램프 없음), `ramp_start_factor: float | None = None`, `ramp_periods_applied: int = 0`, `ramp_scaled_periods: int = 0`, `ramp_end_s: float | None = None`, `ramp_end_reason: str | None = None`.
- `_scaled_to_liftoff_slow_mean`: 작동 주기마다 `last_scale_factor`를 그 주기 축척(축척 안 했으면 1.0)으로 둔다. 반환값은 바꾸지 않는다.
- `_apply_liftoff_approach_slow`
  - 끝 주기: 끝 사유가 `SUM`·`TIME`이고 $N_r\ge1$이고 `last_scale_factor` < 1이면 `ramp_step = 1`, `ramp_start_factor = last_scale_factor`로 램프를 시작하고 이 주기에 1.3절 식을 적용한다. 그 밖이면 지금처럼 `leg_speeds`를 그대로 돌려준다.
  - 작동이 아닌 LEVEL 주기에서 `ramp_step` ≥ 1이면: 1.3절 취소 1·3·4·5를 그 순서로 보고, 참이면 램프를 끝내고(사유) 그대로 돌려준다. 아니면 식을 적용한다.
  - 적용 뒤 `ramp_periods_applied += 1`, 축척이 실제로 걸렸으면 `ramp_scaled_periods += 1`, `ramp_step += 1`. `ramp_step > N_r`이면 램프 끝(`done`, `ramp_end_s` = 이 주기 시각).
- `_finish_liftoff_slow_period`: LEVEL 단계가 없는 주기에 램프 중이면 사유 `phase`로 끝낸다(LAS-b 본체 처리 뒤).
- 사건: $N_r\ge1$이고 램프가 시작된 실행에서만 램프 끝에 `INFO_LIFTOFF_SLOW_RAMP_END:<reason>` 하나. $N_r$ = 0이면 사건·상태 변화가 없어야 한다.
- 메타 `_liftoff_approach_slow_meta`: `ramp` dict(`n_r`, `start_factor`, `periods_applied`, `scaled_periods`, `end_t_s`, `end_reason`).
- `OutputLimit.LIFTOFF_SLOW` 표시는 램프 주기에도 지금 방식(`_note_output_limit`)대로 남는다.

### A.3 표적·판정 도구

- 후보 P0, P5, P5r4, P5r6(1.2절). 설정은 `dataclasses.replace`로만 덮어쓴다. `las_targeted.install`은 설치하지 않는다. 프리셋 LAS-b가 b0인지 먼저 확인한다(`fb_targeted.check_preset_las`).
- 묶음 R-0, R-0P5, R-G, R-H, R-T, R-S, R-P0, R-X. 출력 폴더 `v5/las/revA/`. R-T 이후 묶음은 같은 폴더의 앞 묶음 줄이 모두 현재 커밋·도구 sha256에서 나왔을 때만 돈다(원판 도구 `earlier_identity_problems`와 같은 검사).
- R-H 격자: `touch_budget.j` 실수, 줄 이름 `-j0p5` 꼴.
- 기록: 4절 필드, `rules_revA_sha256`(+ 원판·rev1), `controller_tag` 검사.
- 판정: 5절(R1-1~R1-4 포함), 상태 순서 `stop` > `undecidable` > `fail` > `pass`, 빈 후보 `incomplete`, H-6은 (가) `fail`만 센다. K-A1~K-A8 검사, M-1~M-3과 $\Delta F$·$R_c$·$R^{\cup}_c$를 전체 자리로 출력한다.
- R-0P5 짝 기준 `rev_RG.jsonl`은 경로를 인자로 받고 sha256을 대조한다(H-10).
- 단위 시험은 7.3절. 판정 도구 시험은 손으로 만든 줄로 상태 순서·빈 후보·H-6 개수·K-A 위반을 덮는다.
