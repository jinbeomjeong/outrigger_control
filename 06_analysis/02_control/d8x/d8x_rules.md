# D8x 검증 범위 확장 판정 규칙 (원판)

- 작성: control-expert, 2026-11-10. 봉인 정보는 같은 폴더의 `d8x_rules.sha256`에 있다.
- 사용자 결정(2026-11-10, 선택지 2와 계획 승인 Q1~Q9)을 그대로 옮겼다. 이 원판을 봉인한 뒤 바꿀 때는 덧붙임 판(`d8x_rules_rev1.md` …, 각각 `.sha256`)만 쓴다. 원판은 고치지 않는다.
- 규약
  - 기체 좌표: x 전방, y 좌측, z 상방. roll + = 왼쪽이 높음, pitch θ > 0 = 앞내림.
  - 각도는 바닥 경사 [°]. 힘은 실린더 순 힘(참값) [N 또는 kN]. 압력 [bar], 행정 [m].
  - 제어기: 이산, $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1. 다리 순서 FL, FR, RL, RR.
- 기준값
  - $F_{min}$ = 9,414.589 N(YAML `control.F_min_cylinder_N`).
  - **D8 선** $F_{D8}$ = $F_{min}$ + 5,000 N = 14,414.589 N.

## 0. 목적·근거·이미 본 자료

### 0.1 목적

시뮬레이션 검증 범위를 바닥 경사 마름모 5.5° / 3.5°에서 **5.7° / 3.7°**(사분면 4개)로 넓힌다. 이 판정이 그 확장을 받아들일 수 있는지 정한다.

다음은 이 규칙의 범위 밖이다. 이 판정으로 바뀌지 않는다.
- 운용 한계 3.2° / 4.4°(로드 굽힘 근거)
- 운용 시작 조건 $R_c$, 목표 수용 규칙 A
- 연약 지면 $R_c$ 권고

### 0.2 근거

- `dynamics_model.md` 3.9.7.8(브랜치 `worktree-agent-a0fc83e40a37fd5ba`, 커밋 5d12a2c): R8 C2 유연 마스트 재판정 890건이 모두 통과했다. 그래서 D8 안 1(상단 3.3°)의 근거가 사라졌다.
- 사용자 결정(2026-11-10)
  - Q1: 마름모 5.7/3.7
  - Q2: 축소·하네스는 사분면 4개 모두, Chrono는 최악 1점을 더함
  - Q3: Chrono 19행
  - Q4: SCM 없음
  - Q5: 축소·하네스는 E코어에서 지금, Chrono는 K1 재측정 뒤 P코어
  - Q6: 실행 시점의 기본 프리셋 태그 하나로 돌리고, VB·V0 차는 하네스로 본다
  - Q7: 가드·FAULT 미작동을 관문으로 하고, 행정 여유는 기록만
  - Q8: 이 원판을 봉인하고 감사를 세 시점에 받는다
  - Q9: 새 모드 `verification_ext`를 추가한다

### 0.3 봉인 전에 본 자료

아래 자료는 봉인 전에 이미 봤다. **관문 판정에는 쓰지 않는다.** 배경 근거로만 쓴다.

| 자료 | 내용 |
|---|---|
| `06_analysis/00_dynamics/mast_flex_c2_check_r8.json` | 890건(3.9.7.8) |
| `06_analysis/02_control/touch_phase/acceptance/d8/d8_both.json` | D8 576, 옛 경계점 |
| `07_results/S9/batch_FINAL-R-REP_20261030_223425` | FINAL-R-REP 16행 |
| `v5/d1.jsonl` | D-1 옛 경사 |
| `06_analysis/00_dynamics/s6_slope_boundary_check.json` | 옛 경계 상 |

### 0.4 봉인 시점에 보지 않은 것

- G0 결과. dynamics-expert가 따로 진행 중이고, 봉인 시점에는 결과가 없다.
- 새 점의 폐루프 결과. 0건이다.

## 1. 정의

### 1.1 검증 집합

$$\mathcal V_x=\left\{(\varphi_g,\theta_g):\ R_v=\frac{\lvert\varphi_g\rvert}{5.7^\circ}+\frac{\lvert\theta_g\rvert}{3.7^\circ}\le1\right\}$$

| 기호 | 뜻 |
|---|---|
| $\varphi_g,\theta_g$ | 바닥 경사. 바닥면은 $z=-\tan\theta_g\,x+\tan\varphi_g\,y$(`floor_normal` 규약) |
| $R_v$ | 검증 사용률 |
| $\hat\varphi_g,\hat\theta_g$ | 크롤러 위 IMU 자세에서 `CrawlerSettleMap.for_level(level)`로 역산한 바닥 추정. Chrono 시작 검사 A1만 쓴다 |
| $\varepsilon_u$ | A1 사용률 허용 0.01(`VERIFICATION_USAGE_TOLERANCE`, 바꾸지 않음) |

### 1.2 점 목록 (문자 그대로)

모든 점은 오거 세 단계(top, middle, bottom)에 같은 바닥 경사로 쓴다. 표의 $R_v$는 표 값으로 계산했고, 소수 다섯째 자리에서 반올림했다.

**(A) 경계 행렬 점 16개 (R-a)**

| 태그 | φ_g [°] | θ_g [°] | $R_v$ |
|---|---|---|---|
| `pitch+` | 0 | 3.7 | 1.00000 |
| `pitch-` | 0 | −3.7 | 1.00000 |
| `roll+` | 5.7 | 0 | 1.00000 |
| `roll-` | −5.7 | 0 | 1.00000 |
| `r+p+0.25` | 1.425 | 2.775 | 1.00000 |
| `r+p+0.5` | 2.85 | 1.85 | 1.00000 |
| `r+p+0.75` | 4.275 | 0.925 | 1.00000 |
| `r+p-0.25` | 1.425 | −2.775 | 1.00000 |
| `r+p-0.5` | 2.85 | −1.85 | 1.00000 |
| `r+p-0.75` | 4.275 | −0.925 | 1.00000 |
| `r-p+0.5` | −2.85 | 1.85 | 1.00000 |
| `r-p-0.5` | −2.85 | −1.85 | 1.00000 |
| `d45++` | 2.2627 | 2.2627 | 1.00851 |
| `d45+-` | 2.2627 | −2.2627 | 1.00851 |
| `d45-+` | −2.2627 | 2.2627 | 1.00851 |
| `d45--` | −2.2627 | −2.2627 | 1.00851 |

- 태그의 s(0.25, 0.5, 0.75)는 roll 몫이다. φ = s·5.7, θ = ±(1 − s)·3.7.
- `d45**`는 사용자 시험 최댓값 "대각 3.2°"다(성분 3.2/√2). $R_v$ 1.00851은 $\varepsilon_u$ 안에 든다.

**(B) rpB 방향 대각점과 거울점 (R-c·Chrono)**

| 이름 | φ_g [°] | θ_g [°] | $R_v$ | 비고 |
|---|---|---|---|---|
| `rpX` | 2.8632 | 1.8413 | 0.99996 | rpB (2.7355, 1.7592) 방향. 소수 넷째 자리에서 내림해 $R_v$ ≤ 1 |
| `rpX+-` | 2.8632 | −1.8413 | 0.99996 | |
| `rpX-+` | −2.8632 | 1.8413 | 0.99996 | |
| `rpX--` | −2.8632 | −1.8413 | 0.99996 | |

**(C) 축 꼭짓점 이름 (R-c·Chrono)**

| 이름 | φ_g | θ_g |
|---|---|---|
| `fdown3.7` | 0 | 3.7 |
| `fup3.7` | 0 | −3.7 |
| `roll5.7` | 5.7 | 0 |
| `rollm5.7` | −5.7 | 0 |

**점 파일**: 9.2의 `d8x_judge.py points`가 위 표를 `06_analysis/02_control/d8x/d8x_points.json`으로 낸다. 실행에 쓰는 각도는 이 파일 값이다. 표 값과 차가 0이 아니면 실행 전 검사 I-3이 실패한다.

### 1.3 검증 모드 `verification_ext`

- `SlopeLimitMode.VERIFICATION_EXT = "verification_ext"`를 새로 둔다.
- `TargetLimits.for_mode`의 값: `relative_roll_span_rad` = radians(5.7), `relative_pitch_span_rad` = radians(3.7), `usage_tolerance` = 0.01. 절대 마름모와 축별 상한은 그대로다.
- 정착 사상을 허용한다. 앞들림 반폭 덮어쓰기(`relative_pitch_span_nose_up_rad`)는 금지한다. 둘 다 기존 VERIFICATION과 같다.
- 기존 `VERIFICATION`(5.5/3.5)은 바꾸지 않는다. 그래서 묶음 C의 `rp05` A1 거부 시험이 그대로 남는다.

## 2. 대상(실행 정체성)

### 2.1 제어기

- 구성: `C2Config.with_10hz_d1()`를 덮어쓰지 않고 그대로 쓴다. 실행 시점의 기본 프리셋이다(Q6).
- 봉인 시점의 태그: V0 `final_C4G2_LAS`, VB `final_C4G2_P3_LAS`. K1(R4c30 순서 관문)은 끔이다.
- Chrono 행이 쓸 태그(`expected_tag`)는 실행 전 기록(I-5)에 적는다. 러너가 보고한 태그가 그 값과 다르면 그 행은 판정 불가다.
- 하네스는 `TargetAcceptance.OFF`로 돈다(기존 `c2py_r8d1_closed_loop.preset_config` 관례). Chrono는 `TargetAcceptance.REJECT`와 `slope_limit_mode = verification_ext`, `CrawlerSettleMap.for_level(level)`을 쓴다.

### 2.2 실행 위치와 파일 정체성

- **E코어 축소·하네스(R-a, R-c, G0 계산)는 구현 브랜치 `d8x-impl`의 HEAD($H_{impl}$)에서 돌릴 수 있다.** 이유: K1 재측정 Chrono가 끝날 때까지 master에 커밋할 수 없다.
- **Chrono(C)는 구현을 병합한 master 커밋($M$)에서만 돈다.**

**실행 경로 파일 목록 $\mathcal F$**(9.2 `manifest`가 만든다)

| 묶음 | 파일 |
|---|---|
| 공통 | `03_src/outrigger_sim/**/*.py`, `02_params/rexome33.yaml` |
| R-a | `04_scripts/03_control/touch_phase/acceptance/acc_d8.py`, `acc_common.py`, `04_scripts/03_control/r8d1/c2py_r8d1_closed_loop.py`, `r8d1_td.py`, `r8d1_td2.py`, `04_scripts/03_control/r8d1/` 안의 그 import 대상, `04_scripts/01_dynamics/run_s6_slope_boundary_check.py`, `run_mast_flex_c2_check.py`, `run_pad_tangential_check.py`, `run_control_comparison.py`, `04_scripts/03_control/run_c2_timedomain.py`, `dyn_model.py` |
| R-c | `04_scripts/04_hydraulic/coupled/d1_rows.py`, `d1_runs.py`, `run_v5.py`, 그 import 대상 |
| C | `04_scripts/02_chrono/run_S6C.py`, `run_S8C.py`, `s6_stage2.py`, `s9_batch.py`, `03_src/outrigger_sim/chrono/**` |
| 판정 | `04_scripts/03_control/d8x/*.py` |

- `manifest`는 import를 실제로 따라가서 목록을 닫는다(`sys.modules`의 파일 중 저장소 안에 있는 것).
- 비교는 **git blob id**(`git rev-parse <commit>:<path>`)로 한다. 작업 사본의 바이트는 CRLF 변환 때문에 기준으로 쓰지 않는다.

**규칙**

| # | 규칙 |
|---|---|
| I-1 | 실행 시작과 끝에 `git status --porcelain --untracked-files=no`가 비어 있어야 한다. 기록: HEAD, $\mathcal F$의 blob id, 인터프리터 경로·버전, 스레드 환경 변수(MKL/OMP/NUMBA/OPENBLAS_NUM_THREADS = 1, `MKL_THREADING_LAYER`), affinity 마스크(E코어 `0x0FFF0000`, P코어 묶음은 배치표 값) |
| I-2 | 병합 뒤 $M$에서 `manifest`를 다시 낸다. $\mathcal F_{R\text{-}a}\cup\mathcal F_{R\text{-}c}$의 blob id가 $H_{impl}$과 모두 같으면 R-a·R-c 결과를 $M$의 결과로 승계한다 |
| I-2b | 다르면(예: K1 채택 커밋이 `c2.py`를 바꿈) $M$에서 **재생 검사**를 한다. 대상은 R-a td_main 192건과 R-c 192건이다. 명령 해시(`commands_sha256`)가 모두 같으면 승계한다. 하나라도 다르면 해당 묶음 전체를 $M$에서 다시 돌리고, 판정은 다시 돌린 결과로 한다 |
| I-3 | 점 파일 sha와 값이 1.2 표와 같아야 한다(차 0) |
| I-4 | Chrono 행의 meta: `slope_limit_mode == "verification_ext"`, `floor_true_deg`가 1.2 값과 ≤ 1e-4° 차, 오거 단계·β·F_s가 표 4.4와 같음 |
| I-5 | Chrono 실행 전 기록 `d8x_prelaunch_C.json`: $M$, `expected_tag`, 행 목록(19 = 1차 18 + 2차 1), 시작 상태 목록(cad-expert 선언), 스레드 수, 풀(P) |

## 3. 묶음과 기대 행 수

| ID | 내용 | 기대 수 | 엔진·도구 |
|---|---|---|---|
| G0 | 정적 끝 상태와 정착 사상 역산. 점 (A) 16 + (B) 4 = 20점 × 3단계 | **60** 평가 | dynamics-expert, `run_target_envelope` point 모델(행정 0.70 m, 현 YAML), `run_s6_slope_boundary_check` crawler B 모델 |
| R-a | 경계 행렬. 아래 표 | **1,102** | `acc_d8.py --points`, 프로젝트 `C2Controller`, E코어 |
| R-c | v5 하네스 H-R-X. 아래 표 | **288** | `run_v5.py d1 --group H-R-X`, E코어 |
| C | Chrono 강체 19행(4.4) | **19** (1차 18 + 2차 1) | P코어, $M$ |
| R-b | 없음 | 0 | – |
| SCM | 없음(Q4) | 0 | – |

**R-a 세부.** 변형 정의는 `run_s6_slope_boundary_check.td_cases`와 같다. 점만 1.2 (A)로 바꾼다.

| 부분 | 정의 | 수 |
|---|---|---|
| td_main | 16점 × 3단계 × 마스트 4(rigid, stiff, upper, lower) | 192 |
| td_robust 상단 | 16점 × 마스트 4 × (seed 2 + d0 3 + β 0.69/1.6 2) | 448 |
| td_robust 중·하단 | {pitch+, pitch-, roll+, roll-, r+p+0.5, d45++} × 2단계 × 마스트 4 × (β 2 + d0 1) | 144 |
| td_kt | {pitch+, pitch-, roll+, roll-, r+p+0.5, r+p+0.25, d45++} × 상단(마스트 rigid, stiff; 크롤러 k_t ×{1, 0.3, 3}·KT_REL_CHRONO; kt와 ktd0) 84 + 중·하단(rigid; ×3, kt) 42 | 126 |
| R-a-K1 | td_main 192와 같고 K1만 켬 | 192 |
| 합 | | 1,102 |

**R-c 세부.** 강체, 패드 B, F_s 4 kN(`d1_rows` 관례).

| 부분 | 정의 | 수 |
|---|---|---|
| 행 | 경사 8(`fdown3.7`, `fup3.7`, `roll5.7`, `rollm5.7`, `rpX`, `rpX+-`, `rpX-+`, `rpX--`) × 3단계 × 크롤러 ×1/×3 | 48 |
| 실행 | 48 × VB/V0 × ε {0, 2e-3} | 192 |
| R-c-K1 | 48 × VB/V0 × ε 0, K1 켬 | 96 |
| 합 | | 288 |

## 4. 판정 항목과 문턱

### 4.1 행 판정 항목

각 행은 항목이 모두 참이면 `pass`다.

| # | 항목 | 문턱 | 출처 | 적용 |
|---|---|---|---|---|
| J1 | 크롤러 이탈(LOC 또는 첫 크롤러 하중 0) 뒤 최소 참 실린더 힘(1 ms 또는 부분 스텝 최소) | ≥ $F_{D8}$ | `dynamics_model.md` 3.9.7.7, 인수 `criteria.md` D8 | R-a, R-c, C |
| J2 | H4(REANCHOR) 진행 중 최소 참 실린더 힘 | ≥ $F_{D8}$ | 3.9.7.8 `reanchor_on` | H4가 돈 행 |
| J3 | 패드 부상(접지 뒤 참 법선력 ≤ 0) | 0회 | 3.9.7.7 | 전부 |
| J4 | READY 뒤 끝까지 참 데크 자세 최대 \|오차\| | ≤ 0.2° | CLAUDE.md 정확도 | 전부 |
| J5 | 첫 READY 시각(실행 시작 기준) | ≤ 120 s | `d1_rows.READY_LIMITS_S` 경사 | 전부 |
| J6 | 이동 중 최대 압력 / 잠김 최대 | ≤ 210 / ≤ 350 bar | CLAUDE.md 압력 판정. Chrono는 명세 412 `max_pressure_by_variable` | 이동: 전부. 잠김: C(필드가 있을 때) |
| J7 | 행정 사건 `FAULT_STROKE_END`, `WARN_LIFT_STROKE_LIMITED`, `FAULT_LIFT_STROKE_LIMIT*` | 0 | Q7 | 전부 |
| J8 | 그 밖의 `FAULT_*` 사건 | 0 | – | 전부 |
| J9 | `WARN_*` 사건(허용 목록 밖) | 0. 허용 목록: `WARN_PROBE_STIFFNESS_OUT_OF_RANGE`(β 감도에서 예상, 3.9.7.8) | – | 전부 |
| J10 | LOC 뒤 크롤러 재접촉(엔진 접촉 플래그) | 0 | – | C |
| J11 | 드라이버 실패 목록(`fails`, 하네스 자체 판정) | 빈 목록 | 인수 `criteria.md` | R-a, R-c |

### 4.2 기록 전용

판정에 쓰지 않는다. 판정서에 표로 남긴다.
- 판독 최대 행정과 가드 682.8 mm까지의 여유 [mm]
- 로드 SF 판정 쌍(dynamics-expert)
- 패드 μN 이용률
- 마스트 상대 회전
- `INFO_LIFTOFF_SLOW`, `INFO_LIFT_PAUSED` 등 INFO 사건 수
- VB − V0 최소 힘 차
- Chrono − 하네스 차(E1 형식, 같은 점·단계)
- 정착 사상 역산 오차
- 레벨링 시간

### 4.3 G0 판정 기준 (dynamics-expert, 원판이 먼저 정함)

20점 × 3단계 각각에 대해 준정적 레벨링 끝 상태를 계산한다. 조건: 크롤러 틈 50 mm, 수평 목표, 현 YAML, 행정 0.70 m.

| # | 항목 | 문턱 |
|---|---|---|
| G0-1 | 최대 모터 행정 $s_{max}$ + 동작 여유 | < 0.6828 m. 동작 여유는 탐침 2 mm, 앞내림 점(θ_g > 0)이면 H4 2.9 mm를 더함 |
| G0-2 | 최소 실린더 힘(정적) | ≥ $F_{D8}$ |
| G0-3 | 스위블 각 | ≤ 10° |
| G0-4 | Chrono 대상 점(4.4의 바닥, 상단, 그리고 중·하단 `rpX`)의 정착 사상 역산 | 독립 크롤러 준정적 모델이 낸 크롤러 위 자세를 `CrawlerSettleMap.for_level`로 역산했을 때 $\hat R_v$ ≤ 1.005, 각 성분 역산 오차 ≤ 0.037°. W 후보 점(5.1)도 상단에서 같은 기준 |

기록: 20 mm 틈 결과, 로드 SF 쌍, μN 이용률, $s_{max}$ 여유 [mm].

### 4.4 Chrono 19행

- 행 이름 규칙: `D8X_<기존 계열>_<단계>_<바닥>_<설정>`
- 엔진: L2b = `run_S8C.py`(L2b-NSC, 강체 크롤러), L1-R = `run_S6C.py`(묶음 C)
- β의 단위는 GPa. L2b의 β 1.0은 YAML 값이다.

| # | 행 이름 | 엔진 | β | F_s [kN] | 단계 | 바닥 | 차수 |
|---|---|---|---|---|---|---|---|
| 1 | `D8X_K24_top_fdown3.7_Fs4` | L2b | 1.0 | 4 | top | fdown3.7 | 1 |
| 2 | `D8X_K24_top_fup3.7_Fs4` | L2b | 1.0 | 4 | top | fup3.7 | 1 |
| 3 | `D8X_K24_top_roll5.7_Fs4` | L2b | 1.0 | 4 | top | roll5.7 | 1 |
| 4 | `D8X_K24_top_rollm5.7_Fs4` | L2b | 1.0 | 4 | top | rollm5.7 | 1 |
| 5 | `D8X_K24_top_rpX_Fs4` | L2b | 1.0 | 4 | top | rpX | 1 |
| 6 | `D8X_K24_top_<W>_Fs4` | L2b | 1.0 | 4 | top | W(5.1) | 1 |
| 7 | `D8X_C1_D8_top_fdown3.7_b1.6` | L1-R | 1.6 | –(L1-R는 실 마찰 없음) | top | fdown3.7 | 1 |
| 8 | `D8X_C1_D8_top_fup3.7_b1.6` | L1-R | 1.6 | – | top | fup3.7 | 1 |
| 9 | `D8X_C1_D8_top_roll5.7_b1.6` | L1-R | 1.6 | – | top | roll5.7 | 1 |
| 10 | `D8X_C1_D8_top_rpX_b1.6` | L1-R | 1.6 | – | top | rpX | 1 |
| 11 | `D8X_C1_H4V_top_fdown3.7` | L1-R | 1.0 | – | top | fdown3.7 | 1 |
| 12 | `D8X_A_middle_rpX_Fs0` | L2b | 1.0 | 0 | middle | rpX | 1 |
| 13 | `D8X_A_bottom_rpX_Fs0` | L2b | 1.0 | 0 | bottom | rpX | 1 |
| 14 | `D8X_K0V_top_fdown3.7_Fs0` | L2b | 1.0 | 0 | top | fdown3.7 | 1 |
| 15 | `D8X_K0V_top_fup3.7_Fs0` | L2b | 1.0 | 0 | top | fup3.7 | 1 |
| 16 | `D8X_K0V_top_roll5.7_Fs0` | L2b | 1.0 | 0 | top | roll5.7 | 1 |
| 17 | `D8X_K0V_top_rollm5.7_Fs0` | L2b | 1.0 | 0 | top | rollm5.7 | 1 |
| 18 | `D8X_K0V_top_rpX_Fs0` | L2b | 1.0 | 0 | top | rpX | 1 |
| 19 | `D8X_K8_top_<V>_Fs8` | L2b | 1.0 | 8 | top | V(5.2) | 2 |

- 시나리오 길이·H4·탐침·센서는 기존 계열(`K24_*`, `C1_D8_*`, `C1_H4V_*`, `A_*`, `K0V_*`, `K8_*`)의 정의를 그대로 쓴다. 바닥과 검증 모드만 다르다.
- 시작 상태(크롤러 정착)는 cad-expert가 행마다 선언하고 I-5에 적는다. 필요한 (단계, 바닥)은 top × {fdown3.7, fup3.7, roll5.7, rollm5.7, rpX, W}, middle × rpX, bottom × rpX, 모두 8쌍이다. 엔진별로 필요한 것을 선언한다.

## 5. 관문과 선정 규칙

### 5.0 관문 순서

| 관문 | 조건 | 통과하면 | 실패하면 |
|---|---|---|---|
| G-S | 이 원판 봉인, 실행 전 감사(verif-protocol-auditor `[시점] 실행 전`) 차단 0, 구현 시험 통과(9.3), 점 파일 I-3 | G0와 R-a·R-c 실행 | 실행하지 않음 |
| G0 | 4.3의 60평가가 모두 통과 | R-a·R-c 결과를 판정한다(실행은 G-S 뒤 병행 가능. **판정·선정은 G0 통과 뒤**) | 분기 B-G0 |
| G1 | R-a 1,102와 R-c 288이 모두 들어옴(빈 집합 방지 6절). 판정 대상(K1 짝 제외 R-a 910, R-c 192)이 모두 `pass`. K1 짝 행도 J1~J11은 판정함 | 5.1로 W 선정, 7절 불변 판정, Chrono 1차 실행 | 분기 B-G1 |
| G2a | Chrono 1차 18행이 모두 `pass` | 5.2로 V 선정, 2차 1행 실행 | 분기 B-C |
| G2b | 2차 1행 `pass` | G3 | 분기 B-C |
| G3 | 두 경로 재집계 일치(8절), 판정 후 감사 차단 0, I-2(또는 I-2b) 승계 확인 | 판정 등급(10절)과 문서 반영 | 판정 불가 |

미달·판정 불가가 나오면 **원인 분석까지만 하고 사용자에게 묻는다**(사용자 결정 Q5). 다음 관문으로 자동으로 넘어가지 않는다.

### 5.1 최악 점 W 선정 (Chrono 6행)

- 후보 집합 $\mathcal C$: R-a 점 가운데 `pitch+`, `pitch-`, `roll+`, `roll-`, `r+p+0.5`(rpX와 같은 위치로 봄)를 뺀 11점. 즉 `r+p+0.25`, `r+p+0.75`, `r+p-0.25`, `r+p-0.5`, `r+p-0.75`, `r-p+0.5`, `r-p-0.5`, `d45++`, `d45+-`, `d45-+`, `d45--`.
- 지표: $m(p)$ = 상단·마스트 `rigid`인 R-a 행(td_main, td_robust, td_kt. K1 짝 제외) 가운데 점 $p$인 행들의 J1 값의 최솟값.
- 거울 대각 세 점은 R-c 상단 행(VB·V0·ε 모두. K1 짝 제외)의 J1 최솟값도 함께 넣어 작은 쪽을 쓴다. 짝은 `r+p-0.5` ↔ `rpX+-`, `r-p+0.5` ↔ `rpX-+`, `r-p-0.5` ↔ `rpX--`다.
- 선정: W = argmin $m(p)$. 같은 값이면 위 목록 순서가 앞인 점을 고른다.
- W의 바닥 각도는 R-a 점 좌표다. 거울 대각이 뽑혀도 R-a 좌표를 쓴다.
- Chrono 바닥 이름:

| R-a 점 | 바닥 이름 |
|---|---|
| `r+p+0.25` | `dxpp025` |
| `r+p+0.75` | `dxpp075` |
| `r+p-0.25` | `dxpm025` |
| `r+p-0.5` | `dxpm050` |
| `r+p-0.75` | `dxpm075` |
| `r-p+0.5` | `dxmp050` |
| `r-p-0.5` | `dxmm050` |
| `d45++` | `d45pp` |
| `d45+-` | `d45pm` |
| `d45-+` | `d45mp` |
| `d45--` | `d45mm` |

- W가 G0-4를 통과하지 못했으면 다음 순위 점을 쓰고 그 사실을 판정서에 적는다.
- 선정 결과는 `d8x_judge.py select-w`가 `d8x_selection.json`으로 내고, Chrono 1차 실행 전 기록(I-5)에 넣는다.

### 5.2 F_s 8 행 V 선정 (Chrono 19행)

- V = 1차 L2b F_s 4 행 6개(#1~#6) 가운데 J1이 가장 작은 행의 바닥이다. 같은 값이면 표 순서로 정한다.
- `d8x_judge.py select-v`가 1차 판정 뒤 낸다.

## 6. 빈 집합 방지

| # | 규칙 |
|---|---|
| E-1 | 묶음별 실제 수 = 3절 기대 수(G0 60, R-a 1,102, R-c 288, C 19). 다르면 판정 불가. 판정 도구는 묶음별 기대·실제·통과·실패·불가 수를 출력한다 |
| E-2 | 행마다 TOUCH(첫 접지), 크롤러 이탈, 첫 READY 시각이 모두 있다. 하나라도 없으면 그 행은 `fail`이다. 결측을 통과로 세지 않는다 |
| E-3 | `REJ_*` 코드(특히 `REJ_SLOPE_D8`, `REJ_TARGET_*`)가 0이다. 하나라도 있으면 `fail`. Chrono는 `target_checks` 또는 사건 목록에서, 하네스는 사건 목록에서 센다 |
| E-4 | Chrono `slope_limit_mode == "verification_ext"`, `floor_true_deg`가 1.2와 같음(I-4). 아니면 판정 불가 |
| E-5 | 하네스 행의 각도가 점 파일과 같음(≤ 1e-9°). 오거 단계·마스트·변형 키가 3절 정의 집합 안. 집합 밖 키나 중복 키가 있으면 판정 불가 |
| E-6 | 태그: Chrono 행의 태그 = I-5 `expected_tag`. 하네스 행의 태그·K1 플래그 = 실행 전 기록 값. 태그 필터로 행을 고를 때는 필터 전후 수를 출력하고, 필터 뒤 수 = 기대 수인지 확인한다(`_LAS` 접미사 포함) |
| E-7 | 수치 필드가 NaN·None이면 그 항목은 `fail`. 실행 간 비교는 `equal_nan=True`로 한다 |
| E-8 | J1의 "이탈 뒤" 구간이 1 s보다 짧으면(실행이 이탈 직후 끝남) 판정 불가 |

## 7. 불변·승계 규칙

| # | 대상 | 규칙 |
|---|---|---|
| V-1 | K1 | R-a-K1 192건과 R-a td_main 192건, R-c-K1 96건과 R-c 대응 96건(VB·V0, ε 0)의 `commands_sha256`를 짝마다 비교한다. 모두 같으면 `K1_INVARIANT`. 이 경우 K1 끔 태그로 돈 Chrono 행은 K1 채택 태그의 결과로 승계한다. 조건: 그 Chrono 행에 토양 모드 시작과 `INFO_LOC_FLAT_SOIL_MARGIN`, `INFO_LOC_CLEARANCE_MARGIN`, `INFO_LOC_REVOKED` 사건이 0이어야 한다 |
| V-1b | K1 | 다른 짝이 있으면 그 점·단계를 `K1_DEPENDENT`로 표시한다. K1이 채택되면 그 점의 Chrono 행을 채택 태그로 다시 돌린다. K1이 Chrono 시작 전에 채택되면 Chrono는 채택 태그로 바로 돌고, V-1은 기록이 된다 |
| V-2 | LAS-b | R-a·R-c 판정 대상 행의 `INFO_LIFTOFF_SLOW` 수를 점·단계별로 센다. 0인 점은 `LAS_INACTIVE`. LAS-b 시작 관문·파라미터가 바뀌면(P5r4 등) R-a td_main 192와 R-c 192를 바뀐 제어기로 다시 돌린다. 명령 해시가 모두 같으면 승계한다 |
| V-2b | LAS-b | 작동한 점은 `LAS_DEPENDENT`. 그 점을 쓰는 Chrono 행은 LAS-b가 바뀐 뒤 다시 돌린다. 판정 등급은 조건부(10절) |
| V-3 | ③(VB/V0) | R-c VB와 V0의 J1 차를 점·단계·크롤러·ε별로 기록한다. 판정 대상 행이 모두 `pass`이면 추가 Chrono는 없다(Q6) |
| V-4 | 전환 | 판정 기간에 기본 프리셋·태그가 바뀌면(K1 채택 등) verif-protocol-auditor `[시점] 전환 후` 감사를 받고 I-2b를 적용한다 |

## 8. 두 경로 재집계

- **경로 1**: `04_scripts/03_control/d8x/d8x_judge.py`(python-expert 구현, 9.2).
- **경로 2**: control-expert의 독립 재집계 스크립트 `d8x_recount.py`.
  - 원 결과 파일(jsonl·verify json·`r8_series.npz`)을 직접 읽는다. 경로 1의 출력은 읽지 않는다.
  - 결과가 나오기 전에 작성하고 sha를 판정서에 적어 고정한다.
- **일치 기준**
  - 묶음별 수(E-1), 행별 `pass`/`fail`/불가, 관문 결과, W·V 선정, V-1·V-2 분류가 모두 같아야 한다.
  - 같은 원 데이터에서 낸 수치는 상대차 ≤ 1e-9(0이면 절대차 ≤ 1e-9)여야 한다.
- 하나라도 다르면 G3는 판정 불가다. 원인을 고친 뒤 두 경로를 다시 돌린다.

## 9. 구현 명세 (봉인 대상. 구현은 이 절을 따른다)

### 9.1 브랜치

- 구현 브랜치는 `d8x-impl`이다(이 원판 커밋에서 가지를 뻗거나 병합해 원판을 포함한다).
- 병합은 K1 재측정 Chrono가 끝난 뒤 메인 세션이 한다.
- 구현 담당 에이전트는 정의·메모리를 고치지 않는다.

### 9.2 python-expert

1. `03_src/outrigger_sim/control/target.py`
   - `SlopeLimitMode.VERIFICATION_EXT`와 `TargetLimits.for_mode`(1.3)를 추가한다.
   - `TargetSettings.__post_init__`에서 정착 사상 허용과 앞들림 덮어쓰기 금지를 VERIFICATION과 같게 한다.
   - 시험 세 가지:
     - rpX (2.8632, 1.8413)은 `ACCEPTED`
     - rpX × 1.0126은 `REJ_SLOPE_D8`
     - 기존 VERIFICATION의 `rp05`는 그대로 거부(회귀)
   - 기존 모드의 행·해시는 바뀌지 않아야 한다(기존 시험 전부 통과).
2. `04_scripts/04_hydraulic/coupled/d1_rows.py`
   - 그룹 `H-R-X`(3절 R-c 48행)를 추가한다. 경사는 `_scaled_slope`가 아니라 **1.2 (B)·(C)의 명시 각도**로 준다.
   - `run_v5.py d1 --group H-R-X [--k1 on|off] --out 06_analysis/02_control/d8x/rc/hrx_<k1>.jsonl`을 만든다.
   - 줄마다 `commands_sha256`, 사건 이름 목록, 태그, K1 플래그, 각도를 넣는다.
3. `04_scripts/03_control/touch_phase/acceptance/acc_d8.py`
   - `--points <d8x_points.json>` 인자를 추가한다.
   - `--stages main,robust,kt`를 추가한다. td_kt는 `ktcr_rel_kn` 변형이고 정의는 3절이다.
   - `--k1 on|off`를 추가한다.
   - 출력에 `commands_sha256`, 사건 이름 목록, 태그, 각도, 변형 키를 넣는다.
   - 출력 경로는 `06_analysis/02_control/d8x/ra/ra_<k1>.json`이다.
   - 기존 인자 없이 실행하면 옛 결과와 같아야 한다(회귀).
4. `04_scripts/03_control/d8x/d8x_judge.py`
   - 하위 명령: `points`, `manifest`, `prelaunch --bundle {ra,rc,C}`, `judge-ra`, `judge-rc`, `judge-chrono`, `invariance`, `select-w`, `select-v`, `report`
   - 공통 CLI 계약: 종료 코드 0 통과 / 1 실패 / 2 판정 불가·입력 오류 / 3 내부 오류. `--out`, `--format json|md`, 마지막 줄 JSON.
   - 필드 대응표(4.1 항목 ↔ 원 결과 키)를 출력에 넣는다. 키가 없으면 종료 2.
   - Chrono 판정은 `run_S8C.py judge`, `run_S6C.py judge`가 낸 verify json과 `r8_series.npz`를 읽는다.

### 9.3 cad-expert

- `run_S6C.py`, `run_S8C.py`, `s6_stage2.FLOORS`에 1.2 (B)·(C)의 바닥을 추가한다. W 후보 11개 바닥(5.1 이름표)도 미리 정의한다.
- 4.4의 행을 묶음 `--set d8x_w1`(18행. #6은 W 자리)과 `--set d8x_w2`(#19)로 정의한다.
- 행은 `verification_ext`를 쓰고, meta에 `slope_limit_mode`, `floor_true_deg`, 태그를 기록한다.
- 시작 상태(크롤러 정착 스냅숏) 생성 작업과 필요한 (단계, 바닥, 엔진) 목록을 선언한다(4.4 끝).
- 스냅숏 생성은 Chrono 묶음 전에 P코어에서 한다. 비용은 배치표에 넣는다.
- 기존 행의 정의·meta 해시는 바뀌지 않아야 한다(옛 `OPTIONAL_META` 관례).

### 9.4 dynamics-expert

- G0(4.3)를 계산하고 판정한다. 출력은 `06_analysis/00_dynamics/d8x_g0.json`이다.
- 점은 `d8x_points.json`을 읽는다.

### 9.5 control-expert

- 경로 2 `d8x_recount.py`를 쓰고(결과 전에 sha 고정), 판정서 `d8x_judgement.md`를 쓴다.

## 10. 판정 등급

| 등급 | 조건 |
|---|---|
| **통과** | G-S~G3 모두 통과. `K1_DEPENDENT`·`LAS_DEPENDENT` 0. FLAG 0 |
| **조건부 통과** | 관문은 모두 통과했지만 FLAG가 있음. FLAG: (i) J1 또는 J2가 $F_{D8}$ + 2 kN보다 작은 행, (ii) 판독 행정 여유 < 5 mm, (iii) `LAS_DEPENDENT` 또는 `K1_DEPENDENT` 점, (iv) G0-4 역산 오차 > 0.02°. FLAG마다 위치와 값을 적는다 |
| **미달** | 판정 대상 행 하나라도 `fail`, 또는 G0 실패 |
| **판정 불가** | 빈 집합 방지·정체성(I-*)·두 경로 일치 가운데 하나라도 실패 |

**통과 또는 조건부 통과일 때 반영할 문서**(메인 세션이 위임하고, 반영 뒤 integrity-checker가 감사)
- CLAUDE.md 기준값 "레벨링 시작 조건" 칸
- `decision_log.md` 10절 한 줄
- `dynamics_model.md` 3.9.7.7(결정 기록 덧붙임), 0절 D8 행, 3.12.5·3.12.6 단서, 3.13, G0 결과 절
- `s6_control_spec.md` 2.3 단서와 새 절(D8x 판정)
- `00_roadmap.md` 1·4·5·6절
- 논문 v5 서술(paper-writing-expert)

운용 한계 3.2° / 4.4°는 어느 등급에서도 바꾸지 않는다.

## 11. 실패 분기 (미리 정함. 모두 "분석까지, 사용자에게 질문")

| ID | 경우 | 분석 내용과 제안 범위 |
|---|---|---|
| B-G0 | G0-1~3 실패(가장 걸리기 쉬운 곳은 앞내림 3.7°) | 실패 축·단계·여유를 낸다. 제안: 그 축을 G0 통과 최대값(0.1° 간격)으로 줄임. 앞내림·앞들림이 비대칭이 되면 `verification_ext`에 방향별 반축이 필요하다(python-expert). 이 원판의 덧붙임 판으로 처리한다 |
| B-G0-4 | 정착 사상 역산 실패 | 정착 사상 재적합(명세 13.3 K6) 제안. Chrono는 멈춘다 |
| B-G1 | R-a·R-c 행 실패 | 실패 행의 점·단계·마스트·변형과 기전. 제안: (a) 그 사분면·점을 줄여 다각형으로, (b) 단계별 반축, (c) 제어기 수정. (c)는 별도 설계·봉인이다. Chrono는 멈춘다 |
| B-C | Chrono 행 실패(하네스는 통과) | 모델 간 차 분석(dynamics-expert·cad-expert, E1). 그 방향은 5.5/3.5에 둔다 |
| B-ID | 정체성·빈 집합·두 경로 불일치 | 원인을 고친 뒤 해당 묶음을 다시 돌리거나 다시 집계한다. 결과값은 보지 않고 절차 결함만 고친다 |
| B-V | `K1_DEPENDENT`·`LAS_DEPENDENT` | V-1b·V-2b대로 다시 돌릴 대상과 시점을 낸다 |

## 12. 가정

- 정착 사상 계수(`target.py` `_SETTLE_MAP_COEFFICIENTS`, 2026-10-21 스냅숏 맞춤)는 3.7/5.7에 외삽한다. G0-4로 확인한다.
- 밸브 지연 $\tau_v$ 0.1 s, 질량 경우 C, 크롤러 D안·L1 강성 1×10⁸ N/m, L2b 강체 NSC 크롤러는 현 YAML·기존 계열 그대로다(**가정**).
- G0의 크롤러 틈 50 mm와 동작 여유(탐침 2 mm, H4 2.9 mm)는 `dynamics_model.md` 3.12·3.13의 가정 값이다.
- J5 READY 120 s는 강체 경사 행의 기존 한계다. 레벨링 시간의 사양 값이 아니라 판정 한계다.
- 행당 비용(계획서 4절)은 판정과 무관하다.
