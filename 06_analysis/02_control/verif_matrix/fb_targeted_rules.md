# FB(명령 유량 예산 + 포화 검출) 표적·채택 규칙 (봉인 원판)

- 작성: control-expert, 2026-11-08. 사용자 결정(11-08 17:2x)
  - FB-1: LAS-b와 묶어 채택을 검토한다.
  - FB-2: 모든 단계에 적용한다.
  - FB-3: $\eta_{v,min}$ 0.85, $\rho$ 0.98(가정)
  - FB-4: 검출은 U + A97
  - FB-5: V0에도 켜고 전환 전 재현기를 둔다.
  - FB-6: 예산 단독 채택은 하지 않는다.
  - FB-7: 이 규칙을 봉인한 뒤 실행한다.
  - F-6(Chrono 열린 루프)을 포함한다.
- 설계 원본: 같은 폴더 `fb_design.md`(control-expert 설계서 사본). 이 규칙과 설계서 4절이 다르면 **이 규칙이 우선**한다.
- 봉인 전에 본 결과: control-expert 진단 32건(scratchpad `ctrl_budget\runs.jsonl`, 설계서 3절)과 저장 T4h 551기록의 오프라인 그림자. 이 규칙의 후보 LF(2절)는 진단 래퍼와 두 가지가 다르다. 첫째, A97을 TOUCH 자유 신장에만 쓴다. 둘째, U의 평가 다리에 하중 변화 관문을 더했다. 따라서 **LF로 돌린 결과는 아직 하나도 없다.**
- 기준 코드: master `0ea8929`. LAS-b는 아직 03_src에 없다(436절 구현 중). 그래서 LAS-b는 `04_scripts/04_hydraulic/coupled/las_targeted.py`의 `b0`(act) 래퍼로 합성한다(3.1절).
- 규약
  - 이산 $T_s$ = 0.1 s, 출력 지연 $d$ = 1, 다리 순서 FL, FR, RL, RR(0~3)
  - 속도 [m/s](+ = 신장), 유량 [L/min], 힘은 실린더 순 힘 [kN]
  - $v_{max}$ = 20.924 mm/s, $F_{min}$ = 9.415 kN
  - 되먹임은 기존 C2 그대로다.

## 1. 규칙 정의(후보 LF가 구현하는 것)

### 1.1 예산 FB-a

- 주기마다, 모든 단계에서 $u\leftarrow u\cdot\min(1,\,Q_b/Q(u))$를 적용한다.
  - $Q(u)=\sum_iA_i(u_i)\lvert u_i\rvert$. 신장이면 헤드 면적, 수축이면 환형 면적(컨트롤러 `geometry.head_area_m2`·`annulus_area_m2`)이다.
- 위치는 `C2Controller._apply_output_ramp`에서 증분 제한(또는 FAULT 정지 0) 계산 뒤다. 축척한 값을 `previous_output_m_s`로 저장한다.
- $Q_{nom}=\rho\,\eta_{v,min}Q_{th}$
  - $Q_{th}$는 YAML `actuator.pump_flow_m3_s`, $\eta_{v,min}$ = 0.85, $\rho$ = 0.98(가정)이다.
  - 따라서 $Q_{nom}$ = 50.1466 L/min이고, 네 다리 $v_{max}$ 수요에 대한 비는 0.876840이다.
- 실행 시작 때 $Q_b=Q_{nom}$이다. 1.2절 검출만 $Q_b$를 내린다.

### 1.2 검출 FB-b

밸브 모형과 추정(주기 $k$의 반환 명령 $a_k$, 행정 판독 $\hat s_k$ = `reading.motor_stroke_m`, $\tau_v$ = 0.1 s):

$$\hat m_k=a_k+(x_k-a_k)\tfrac{\tau_v}{T_s}(1-e^{-T_s/\tau_v}),\quad x_{k+1}=a_k+(x_k-a_k)e^{-T_s/\tau_v},\quad x_0=0$$

$$\hat v_k=(\hat s_{k+1}-\hat s_k)/T_s,\qquad \hat r_{i,k}=\hat v_{i,k}/\hat m_{i,k}$$

평가 판정은 주기 $k+1$의 update 끝(명령 계산 뒤)에 한다. 평가 다리 $E_k$는 아래가 모두 참인 다리다.
1. $\hat m_{i,k}\ge0.3\,v_{max}$
2. $\hat s_{i,k+1}<$ `stroke_soft_max_m` − 0.02 m
3. 모든 다리에서 $\lvert a_{k}-a_{k-1}\rvert\le0.1\,v_{max}$
4. (U에만) $\lvert F_{i,k+1}-F_{i,k}\rvert\le0.02\,k_{oil}(\hat s_{i,k+1})\,\hat m_{i,k}T_s$. $F$ = `reading.cylinder_force_N`, $k_{oil}$ = `geometry.oil_stiffness_N_m`이다.

$\lvert E_k\rvert<2$인 주기에는 두 카운터를 모두 0으로 둔다. 그 밖의 주기:

| 규칙 | 주기 조건 | 단계 조건 | 확정 |
|---|---|---|---|
| U | $\#\{i\in E_k:\hat r_{i,k}<0.93\}\ge3$ | 모든 단계 | 연속 2주기 |
| A97 | $\lvert E_k\rvert=4$이고 $\sum_{E}A_{h,i}\hat v_i/\sum_EA_{h,i}\hat m_i<0.97$ | 주기 $k$와 $k+1$이 모두 TOUCH이고, `touch_seen`이 참인 다리가 없음 | 연속 2주기 |

- 단계 조건이 거짓인 주기에는 그 규칙의 카운터를 0으로 둔다.
- 확정되면 $Q_b\leftarrow\max(0.5Q_{nom},\min(Q_b,0.97\,\hat Q_{del}))$로 내린다. $\hat Q_{del}=\sum_iA_i(\hat v_i)\lvert\hat v_i\rvert$다.
  - 확정한 규칙의 카운터를 0으로 둔다.
  - 사건 `INFO_FLOW_BUDGET_CUT:<U|A97>`를 낸다.
  - 실행 안에서는 $Q_b$를 다시 올리지 않는다.
- 하네스 판독은 이상 판독이므로 창은 한 주기다. 실기 창은 이 규칙의 대상이 아니다(U-R8-9 뒤).

## 2. 후보

| 이름 | 내용 |
|---|---|
| **L** | LAS-b `b0`(`las_targeted.CANDIDATES["b0"]`, `MODE_ACT`). 예산·검출 없음. **비교 기준** |
| **LF** | L + 1.1 + 1.2(값은 1절 그대로) |
| LF-off | LF 래퍼를 설치하되 `enable=False`(F-0 전용) |
| OL-L, OL-LF | L, LF에 열린 루프 상당을 더한 것. 첫 LEVEL 주기부터 8.0 s 동안 `_level_step`의 반환을 네 다리 $v_{max}$로 바꾸고, 그 뒤 정상 폐루프로 돌아간다. 증분 제한·지연·예산은 그대로 적용한다(설계서 3.1절 래퍼와 같음). F-5 전용 |

값 조정 변형은 두지 않는다. LF 하나만 판정한다.

## 3. 표적 묶음과 키

### 3.1 공통

- 실행 단위: `run_v5.run_one(job)`, 프로세스마다 후보 하나(`spawn`, `maxtasksperchild=1`)
- 작업 정의
  - D-1 키: `d1_rows.jobs()`의 `<row key>|<setting>|e<eps>`
  - U-9·verdict 사례: `run_v5` 작업 dict(`case`, `eps`, `setting`, `eta_v`, `u9_metrics=True`)
- 합성: LAS-b 래퍼(`las_targeted.install`)를 먼저 설치하고, 예산·검출 래퍼를 나중에 설치한다. LAS-b 03_src 구현이 이 실행보다 먼저 병합되면, 3.2절 F-0 재현 조건을 그 구현으로 다시 확인한 뒤 래퍼 대신 쓴다. 이 대체는 사후 변경 공개 대상이 아니다. 다만 판정서에 적는다.
- 줄마다 기록: 키, 후보, `commands_sha256`, `final_phase`, `values`, `d1` 블록, 사건 이름. 그리고
  - 플랜트 1 ms 기록에서 단계별 포화 시간: 아무 다리 제한, 3다리 이상 제한
  - `u9_values`(LEVEL $k$별 시간, $k\ge3$ 최장)
  - 예산 meta: 단계별 작용 주기, 최소 축척, $Q_b$ 최종, 확정 사건, $\hat r$ 최소, 합 비 최소
  - LAS-b 블록(`las_targeted.las_block`과 같음)
  - 열린 루프 창 값(F-5)

### 3.2 묶음

| # | 묶음 | 키 | 후보 | 실행 수 |
|---|---|---|---|---|
| F-0 | 재현·스위치 | `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K1\|VB\|e0`, `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K3\|V0\|e0` | L, LF-off | 4 |
| F-1 | U-9 | `run_v5.u9_targeted_jobs()` 42작업(S2·S3·R3·S5 × 각 ε × V0 / VB η 0.85 / VB η 0.80) + VB η 0.70 4작업(S2·S3·R3·S5, ε 0, `u9_metrics=True`) | L, LF | 92 |
| F-2 | LAS-b T-1·T-2 | `las_targeted.stage_keys("T-1")` 8키 + `stage_keys("T-2")` 184키 | LF(L은 저장 `v5/las/las_T1.jsonl`·`las_T2.jsonl`의 b0 act 줄) | 192 |
| F-3 | 토양 | 아래 16키(모두 ε0) | L, LF | 32 |
| F-4 | 사건·특수 경로 | 아래 14작업(ε0) | L, LF | 28 |
| F-5 | 열린 루프 상당 | `D1\|H-S-0\|J1\|T\|flat\|K1`, `D1\|H-S-0\|J2\|T\|flat\|K1`, `D1\|H-R-0\|rigid\|T\|flat\|K1` × VB·V0, ε0 | OL-L, OL-LF | 12 |
| F-6 | Chrono 열린 루프 | 3.3절 | – | 1(+ 선택 1) |

- **F-3 키**(설정 VB, `J1 flat`만 V0 짝을 더함)
  - `D1|H-S-0|G1|T|flat|K1`
  - `D1|H-S-0|G1|T|diag-rec|K1`
  - `D1|H-S-0|J1|T|flat|K1`
  - `D1|H-S-0|J1|T|diag-rec|K1`
  - `D1|H-S-0|J2|T|flat|K1`
  - `D1|H-S-0|J2|T|diag-rec|K1`
  - `D1|H-S-1|S1|T|flat|K1`
  - `D1|H-S-1|S1|M|flat|K1`
  - `D1|H-S-1|S1|B|flat|K1`
  - `D1|H-S-A|G1+J1@FL|T|flat|K1`
  - `D1|H-S-A|G1+J1@RL|T|flat|K1`
  - `D1|H-S-A|G1+J1@FR|T|diag-psa-soil|K1`
  - `D1|H-S-A-J2|G1+J2@FL|T|flat|K1`
  - `D1|H-R-A-J2|rigid+J2@FL|T|flat|K1`
  - `D1|H-R-A-S1|rigid+S1@FL|T|flat|K1`
  - V0 짝 1키: `D1|H-S-0|J1|T|flat|K1|V0|e0`
  - 합계 15키(VB) + 1키(V0) = 16키
- **F-4 작업**
  - D-1 4키(VB)
    - `D1|H-R-A-stop|rigid+J1@RL|T|fup-op|K1`
    - `D1|H-S-C|J1|T|flat|K1|c-mid@FL`
    - `D1|H-S-C|J1|T|flat|K1|c-mid@RL`
    - `D1|H-S-C-g|J1|T|fdown-rec|K1|c-mid@FL|dsb_gated_off`
  - verdict 사례 5개 × V0·VB(η 기본) = 10작업
    - `R2`(fdown, REANCHOR), `R12`(E_G4), `R14`(E_RE1bF), `R15`(G1L_RE1bF_FL), `R16`(G1L_RE1bF_FL_o050)
    - 모두 `eps` 0. `R12`처럼 `offset_s`가 있는 사례는 `run_v5._phase_jobs(case)`의 첫 작업이다.
  - 사전 접지 시작(PS-7) 하네스 키는 찾지 못해 넣지 않았다(한계, 5절).

### 3.3 F-6 Chrono 열린 루프

- 행: `s9_batch.v5_openloop_rows()`의 `P3a_J1_B_VB`
  - 저장 argv(`machine --lift-s 28 …`) + `v5_vb_argv()`에 두 인자를 바꾸거나 더한다.
  - `--lift-speed-fraction 0.87684`: 예산 같은 속도 $Q_{nom}/\sum A_hv_{max}$ = 50.1466/57.1902
  - `--lift-s 31.93`: 같은 명령 행정 28 × $v_{max}$ = 585.9 mm
  - 행 이름은 가칭 `P3a_J1_B_VB_FB`다.
- 선택 짝: `P3a_J1_B_V0_FB`(V0, 같은 두 인자). 속도 감소 몫과 포화 제거 몫을 나누는 데 쓴다.
- 비교 상대: 저장 `batch_V5-OPENLOOP-VB_20261108_112044\P3a_J1_B_VB`(현재 VB 열린 루프)와 V0 짝
- 같은 정의(`paper_runs\scripts\openloop_compare.py`)로 값을 낸다.
  - 이륙 전 후방 최소 힘(RL·RR)
  - 이륙 시각
  - 명령 행정 같은 시점(명령 시작 뒤 $t\cdot v$ = 같은 행정)과 명령 끝의 roll·pitch, 다리별 행정
  - 다리 사이 행정 차 최대
  - 힘 피크

## 4. 채택 기준(LF가 모두 만족해야 채택 권고)

비교는 같은 키·같은 설정에서 **LF − L** 짝으로 한다. "새 사건"은 L에 없는 사건 이름(접두사 `FAULT`·`WARN`)이다.

| # | 항목 | 기준 | 대상 |
|---|---|---|---|
| C-1 | η 0.85 포화 제거 | 플랜트 포화 시간(아무 다리 제한, 모든 단계) ≤ 0.01 s/실행 | F-1·F-2·F-3·F-4의 VB(η 0.85) LF 전부 |
| C-2 | 판정 | 아래 셋을 모두 만족 | F-1~F-4 LF 전부 |
| | | (a) D-1 키: L pass → LF fail 0. 실패 항목에 P3-2·G6-2 새 실패 0 | |
| | | (b) verdict·U-9 작업: L의 `final_phase`가 `ready`인데 LF가 `ready`가 아닌 경우 0 | |
| | | (c) 새 FAULT 0, 새 WARN 0 | |
| C-3 | 계열 최소 힘 | G-3 계열 8키(F-2 T-1) LF `F_judged_min` ≥ 10.4 kN | F-2 T-1 |
| C-4 | READY | 두 실행 모두 첫 READY가 있는 짝에서, 사건 이름 집합이 L과 같은 짝은 $\Delta t_{READY}$ ≤ +5.0 s(모두)이고 중앙값 ≤ +2.5 s. 집합이 다른 짝은 READY 판정에서 빼고 목록으로 보고한다(C-2는 적용) | F-1~F-4 |
| C-5 | η 0.80 | LEVEL $k\ge3$ 최장 ≤ 0.01 s(14/14), TOUCH 포화(아무 다리) ≤ 1.0 s/실행 | F-1 VB η 0.80 LF |
| C-6 | η 0.70 | `INFO_FLOW_BUDGET_CUT`가 첫 TOUCH 주기 뒤 1.0 s 안에 있음(4/4), LEVEL $k\ge3$ 최장 ≤ 0.01 s(4/4) | F-1 VB η 0.70 LF |
| C-7 | 스위치 | LF-off 해시 = L 해시(2/2). L 해시 = 저장 b0 해시(VB 키, `las_T1.jsonl`) | F-0 |
| C-8 | 행정 | D-1 짝의 `stroke_max_m` 증가 ≤ 1.0 mm | F-2·F-3·F-4 D-1 |
| C-9 | 거짓 검출 | VB η 0.85와 V0의 LF 실행에서 `INFO_FLOW_BUDGET_CUT` 0건 | F-1~F-4 |
| C-10 | 열린 루프 상당 | OL-LF의 8 s 창 다리 행정 차 ≤ 1.0 mm(VB 3/3). 창 자세 변화의 크기가 같은 키 V0 OL-L 값 + 0.05° 이하(VB 3/3) | F-5 |

- 판정: C-1~C-10을 모두 만족하면 **채택 권고**다. 하나라도 어기면 **미달**이고, 미달 항목·키·값을 보고한다.
- 미달이어도 값을 바꿔 다시 돌리지 않는다. 대안(예: $\rho$, A97 문턱, 단계 범위)은 사용자 결정으로만 고른다.
- **F-6은 채택 기준이 아니다.** 결과는 논문 2.8의 기록이다. 기대는 "후방 골이 $F_{min}$ 위로 오르고 행정 차가 1 mm 아래"다. 기대와 다르면 기록하고 사용자에게 보고한다.
- 선형 여유는 실행 기준이 아니다. 작용 운전점은 U-9 비례 분배 행(M_s 1.3505, α 0.7471, Python↔Julia 확인)을 인용한다. 검출로 $s$ < 0.8947이 된 실행이 있으면 그 최소 $s$를 보고한다. 새 여유 계산이 필요한지는 control-expert가 판단한다.

## 5. 알려진 한계(봉인 시점)

- 하네스 행정 판독은 이상 판독이다. 실기 잡음·피스톤 위치 좌표는 시험하지 않는다(U의 하중 변화 관문만 넣음).
- PS-7(사전 접지 시작) 하네스 키가 없다. 잡음 등급(L1~L3)·U-3·U-6·Chrono 폐루프는 표적에 없다. 이들은 FB-1에 따라 LAS-b 전체 재실행(436.8)에서 처음 본다.
- 하네스는 Chrono 열린 루프의 후방 골을 재현하지 않는다(설계서 3.1절). 그래서 C-10은 행정 차·자세만 본다.
- 분배 법칙은 하네스 VB의 priority뿐이다.

## 6. 멈춤 조건

| # | 조건 | 처리 |
|---|---|---|
| H-1 | 이 파일 또는 `fb_design.md`가 없거나, 이 파일 sha256이 `fb_targeted_rules.sha256`과 다름 | 실행하지 않는다 |
| H-2 | F-0 C-7 불일치 | 모든 묶음을 멈추고 래퍼를 점검한다 |
| H-3 | 실행 오류 줄 | 그 작업을 한 번 다시 돈다. 다시 오류면 그 묶음을 멈추고 보고한다 |
| H-4 | 묶음 진행 중 C-2 위반이 누적 5건 이상 | 그 묶음을 멈추고 보고한다(남은 계산 절약). 이미 끝난 줄은 판정에 쓴다 |
| H-5 | F-6에서 `--abort-on-limit` 중단 또는 행정 끝 FAULT | 기록하고 보고한다(F-6은 채택 기준이 아님) |

- 순서: F-0 → (통과 시) F-1~F-5 병행 → F-6. F-6은 cad-expert 명세 확인 뒤 메인 세션이 띄운다. F-1~F-5와 동시에 돌려도 된다.

## 7. 결과를 본 뒤 바꾼 것의 공개

- 이 원판은 고치지 않는다. F-0~F-6 결과를 하나라도 본 뒤 키·후보·값·기준·판정 정의를 바꾸면 새 덧붙임 판 `fb_targeted_rules_rev<n>.md`와 `.sha256`으로 봉인한다. 덧붙임 판에는 다음을 적는다.
  1. 바꾼 항목, 원판의 값, 새 값
  2. 바꾸기 전에 본 결과(묶음·줄 수)
  3. "결과를 본 뒤의 변경"이라는 표시
- 판정서는 원판 기준과 덧붙임 판 기준의 결과를 둘 다 적는다. 채택 결정은 사용자가 한다.
- 판정 도구·래퍼의 구현 결함 수정(규칙 문구와 다르게 구현된 것을 문구대로 고치는 것)은 변경이 아니다. 다만 판정서에 고친 내용과 다시 돌린 줄을 적는다.

## 8. 판정 산출물

- 출력은 새 이름으로 쓴다. 저장 기준선은 덮어쓰지 않는다.
  - 실행 줄: `06_analysis/03_hydraulic/coupled/v5/fb/fb_F<n>.jsonl`(가칭)
  - 판정서: `06_analysis/02_control/verif_matrix/fb_judgement.md`
- 판정은 두 경로로 한다: python-expert 판정 도구, control-expert의 jsonl 재집계. 두 결과가 같아야 확정이다.
