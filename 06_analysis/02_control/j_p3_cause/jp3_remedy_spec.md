# 436.9 J-P3 보완 설계 명세 — ③ revision 5(미세 명령 잠금 유지)와 플랜트 옵션 P1~P4

작성: control-expert, 2026-11-16. 명세만 쓴다. 저장소 코드(`03_src`, `04_scripts`)는 고치지 않았다. 이 폴더에는 이 문서와 확인 계산 스크립트 `rs01~rs03`(읽기 전용, 결과 JSON 포함)만 더했다. 구현은 python-expert가 한다.

- 규약: 음되먹임, 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1. 작용 명령 $u_k$ = 직전 읽기의 출력이고, 증분 제한 뒤의 값이다. ③ 추적기 소단계는 $\Delta t$ = 1 ms, 하네스 플랜트 내부 스텝은 5×10⁻⁴ s다.
- 단위: 압력 bar(게이지), 힘 kN(실린더 순 힘), 속도 mm/s(+ = 신장), 체적 cm³. 다리 순서는 FL, FR, RL, RR(0~3)이다.
- 근거: `jp3_cause_report.md`(앞 분석), `hydraulics_review.md`(H1~H4, 7절 P1~P4, 8절 $u_{hold}$), 하네스 판정서 `verif_matrix/v5_resume_4368_harness_judgement.md` 9.6·9.9절, ③ 명세 `06_analysis/03_hydraulic/coupled/v5/p3_extend_start_spec.md` 3·4·11·12절, 제어 명세 `s6_control_spec.md` 435절.
- 적용한 사용자 결정: 144(제어기 안 1, $u_{hold}$ 0.21 mm/s = 1 % $v_{max}$, 수축 hold 보조 규칙, P1~P4)와 145(새 옵션·새 태그로 분리, 기존 기본값·해시 보존, 기본 켬은 436.9 판정 뒤, 436.9는 결정 96 자동 범위), 146(첫 판 확인 필요 1~10 모두 권고대로), 147(관문 $e_h$ 9 bar, 수축 need $F_{band}$ 0, $p_r$ 하한 $p_{floor}$, P1 수축 시드는 남기되 예외로 기록, J-P3 판정은 normal 등급 행만).
- 갱신판 근거: hydraulics-expert `hydraulics_remedy_review.md`(P3 식 (a)~(d), P1 출력 끔 목록 검토, R5-4 관문 값 검토, $u_{hold}$ 상한 1.2 %).

### 갱신 이력

| 판 | 날짜 | 바뀐 곳(요지) |
|---|---|---|
| 1 | 2026-11-16 | 첫 판 |
| 3 | 2026-11-16 | 유압 검토 10절(판 2 6.2절 "조건부 맞음") 반영, 결정 148 뜻 그대로. ① 반례 ⑩·6.2절 사실 문단의 닫힌 식 $\varphi p_{bA}-F/A_{ann}$를 경계식 함수로 바꿈(닫힌 식은 전방 $F$ ≤ 3.6 kN, 후방 ≤ 2.2 kN에서만 맞음). ② 경계 = 플랜트가 마지막 스텝에 쓴 목표 `last_target_Pa`(기록 `jp3_p_star_ret_Pa`). ③ 플랜트가 잠긴 `carry_ret`은 갇힌 몫(판정). 5.4절 13~15행 추가(값 변화 없음, 판정 집합만 넓어짐), T-JR-17 추가 |
| 2 | 2026-11-16 | 결정 146·147과 유압 검토 반영. 2.2절 $u_{hold}$ 상한 1.2 %. 2.4절 관문 값($e_h$ 5 → 9 bar, $F_{band}$ 8 kN → 0, $p_r$ $p_T$ → $p_{floor}$)과 R12 관문 140 → 148 ms. 2.5절 수축 감압 예(19 bar/s·1 s → 50.4 bar/s·0.42 s). 2.7절 반례 ⑩(가벼운 다리 수축 채움). 3절 P1 출력 예외(수축 M2 시드 유지)·P2 무릎의 void 적용·P3 식 확정. 5.2절 T-JR-03·08 기준 교체. 5.4절 예측 고정 표(옛 값 → 새 값). 6절 J-P3c를 갇힌 몫(판정)과 채움 몫(기록)으로 나눔, 판정 대상 = normal 등급 이하 행. 9절 확인 필요는 결정 146·147로 닫고 새 항목 2개 |

## 0. 요약

| 항목 | 내용 |
|---|---|
| 제어기 | ③ **revision 5**(`ExtendStartBound(revision=5)`). 태그 기저 `final_C4G2_P3H`, 프리셋 태그 `final_C4G2_P3H_LAS_K1`. rev 4에 다섯 규칙을 더한다: R5-1 $\lvert u\rvert \le u_{hold}$이면 잠금 구간을 닫지 않고 ④ 갱신(결정 144), R5-2 수축 hold 보조 규칙 **(i)**(수축 이동 모델을 잠금 후보로 넣음), R5-3 실제 이동 첫 주기의 $\hat p\leftarrow\max(\hat p, ④)$를 **신장·수축 양쪽**에 적용, R5-4 **선 충전 상계 관문**(CARRY: 플랜트가 아직 잠겨 있을 수 있는 동안 감압을 세지 않고 ④를 끈끈하게 따름), R5-5 $0<\lvert u\rvert\le u_{hold}$에서도 구간을 **연다** |
| $u_{hold}$ | $0.01\,v_{max}$ = **0.20924 mm/s**(결정 144·146). P1(VN, $c_v$ 0.02) 아래 HOLD 전제의 허용 상한은 1.2 % $v_{max}$다(유압 검토 2.2절) |
| 플랜트 | P1 `line_fill_gate`(M1c 선 충전으로 잠긴 다리의 해제만 결정), P2 `lock_anchor_continuous`(모든 잠금 앵커 = 직전 $p_{tr}$, r5 −3 bar 계단 없음, 무릎 식 보정), P3 `rod_flow_cap_all`(M2 법칙 `flow_limited_r6`: 네 분기 유량 상한), P4 `rod_reading_truth`(제어기 로드 판독 = M2 참값). 모두 기본 꺼짐 |
| 하네스 설정 | `VBJ`·`LSJ1`~`LSJ4`(P1~P4 + rev 5, 436.9 판정 대상), `VBJ0`(같은 플랜트, ③ 끔: T8·H-7 짝), `VBH`·`LSH1`~`LSH4`(옛 VB 플랜트 + rev 5: 제어기 단독 효과·T8 진단). 기존 VB·LS1~LS4 정의는 그대로 |
| J-P3 | 모니터가 그 읽기에 실제로 쓴 추정으로 분류한다. J-P3a(신장 이동·CARRY, $\hat p+\delta_m$, 1 Pa), J-P3b(HOLD, ④, 0.6 kN/$A_{ann}$), J-P3c(수축 CARRY의 갇힌 몫: 플랜트가 잠겨 있거나, 이동 중이면 $p_{tr}$이 플랜트가 마지막 스텝에 쓴 수축 목표 $p^*_{last}$ 위, $\max(\hat p+\delta_m, \text{수축 모델})$, 1 Pa)를 판정한다. 수축 CARRY의 채움 몫(이동 중이고 $p_{tr}\le p^*_{last}$)과 LOCK·RET은 기록·FLAG다. 판정 대상 행은 헤드·로드 판독 오차가 normal 등급 이하인 행(이상 센서 행 포함)이고, conservative·old_worst 행은 기록만 한다(결정 147). per-read 추적과 per-lock 기록을 더한다(6절) |
| 재실행 범위 | VB·LS 줄 전부를 VBJ·LSJ로 다시 돌린다. 약 4,600줄 + U-6. R2 기준 8 E코어 벽시계 66,800 s(18.6 h)다. 비용 +25 %(가정)를 얹으면 P·E 전체로 약 7~12 h다(7절). V0 줄은 재사용한다 |
| 결정 144·145 밖의 설계 추가 | R5-3 수축 쪽, R5-4, R5-5. 셋 다 상계의 건전성에 필요하다(2.7절 반례 ⑥~⑧). 결정 146으로 채택 |

## 1. 문제 재정리(설계 입력)

| # | 공백 | 근거 | 보완 |
|---|---|---|---|
| G1 | 모니터는 작용 명령이 정확히 0인 주기만 잠금 구간으로 본다. 부호가 반대인 미세 명령(±2 µm/s) 사이의 플랜트 재잠김과, 실기처럼 계속 잠긴 다리를 보지 못한다 | 원인 보고서 2.4, hydraulics H2 | R5-1, R5-5 |
| G2 | rev 4 시드 $\max(\hat p, ④)$는 "구간 열림 + 신장 명령"일 때만 건다. 수축으로 끝난 잠금은 ④를 잃는다 | 원인 보고서 2.3 | R5-1(미세 수축이 구간을 닫지 않음), R5-3 |
| G3 | P1을 넣으면 잠긴 다리는 선 충전이 끝날 때까지 풀리지 않는다. 추적기는 밸브가 열리면 바로 감압을 센다. 이는 ③ 반례 ②("M1c 유지")이고, 지금 `check_extend_start`가 M1c와 ③을 함께 쓰지 못하게 막는 이유다 | `p3_extend_start_spec.md` 3절 반례 ②, `v5_options.check_extend_start` | R5-4(선 충전 상계 관문) |
| G4 | P1만 넣으면 위반이 해제 뒤 첫 읽기(49.1 s)로 옮겨 간다(간격 약 −14 bar, 추정) | hydraulics 7절 | R5-3 + R5-4 |
| G5 | 미세 수축이 여러 주기 이어지면 로드실이 펌프로 가압될 수 있다. 헤드는 그대로라 ④($M$ 13 bar)를 최대 약 11 bar 넘을 수 있다 | hydraulics 8절 위험 경우 | R5-2(보조 규칙 (i)) |
| G6 | P3로 수축 감압이 유량에 묶이면, 하중으로 오른 잠금 뒤 느린 수축 동안 로드 압력이 수축 바닥값보다 높게 남는다. 그 뒤 신장하면 rev 4의 $\max(\hat p, \text{바닥})$은 상계가 아니다 | P3 식(hydraulics 7절) | R5-3(수축 탈출에도 ④ 시드, 수축 중 감압 없음) |
| G7 | J-P3 상태 분류가 플랜트 상태로만 정해져서, "플랜트는 수축 뒤 잠김, 모니터는 신장 추정"인 읽기(VB 48.8 s, −9.92 bar)가 빠졌다 | 원인 보고서 4절 | 6절 J-P3 정의 |

## 2. 제어기 설계: ③ revision 5

### 2.1 주기 분류(다리 $i$, 읽기 $k$, 작용 명령 $u_k$)

분류는 `TwoPressureMonitor._update_rod_estimates`의 맨 앞에서 한 번 정한다. 추적기 진행과 열주(column) 상계 갱신이 같은 분류를 쓴다.

| 분류 | 조건(rev 5) | 잠금 구간 `_LockStretch` | 추적기 $\hat p$ | 대체 로드 추정 $\hat p_r$ |
|---|---|---|---|---|
| LOCK | $u_k = 0$(rev 4와 같은 정확한 0 판정) | 없으면 연다, 있으면 유지 | rev 4 그대로(꼬리 감압 규칙 v2 (i)) | rev 4: ④·⑤ 중 큰 값 |
| HOLD | $0<\lvert u_k\rvert\le u_{hold}$ | 없으면 연다(R5-5), 있으면 유지(R5-1) | 밸브 추정은 실제 $u_k$로 진행한다. 감압·수축 바닥은 세지 않는다($\hat p$ 그대로). 선 충전 누적 $\hat x\leftarrow0$ | ④·⑤ 중 큰 값. $u_k<0$이면 이 주기에 수축 후보를 더한다(R5-2) |
| CARRY | $\lvert u_k\rvert>u_{hold}$이고, 직전 읽기에서 구간이 열려 있었거나 직전 주기가 CARRY이며, 이 주기 시작에 추적기 선 충전 관문이 닫혀 있음 | 첫 CARRY 주기에 구간을 닫는다(정렬 도구용). 후보·비·출처는 운반 상태 `_CarryState`로 복사해 둔다 | 첫 CARRY 주기 시작: $\hat p\leftarrow\max(\hat p, ④_{k-1})$(R5-3, 양방향). 매 CARRY 주기: $\hat p\leftarrow\max(\hat p, ④^{c}_k)$(끈끈함), $u_k<0$이면 운반 후보에 수축 후보 추가. 신장은 관문이 열린 소단계 다음부터 감압을 센다. 수축은 rev 4 수축 분기 $\max(\hat p,\text{바닥})$를 더 건다 | 신장: $\max(13\ \text{bar}, \hat p+\delta_m)$. 수축: $\max(\text{수축 이동 모델}, \hat p+\delta_m)$ |
| EXT | $u_k>u_{hold}$, CARRY 아님 | 닫힘 | rev 4 신장 분기 | rev 4: $\max(13\ \text{bar}, \hat p+\delta_m)$ |
| RET | $u_k<-u_{hold}$, CARRY 아님 | 닫힘 | rev 4 수축 분기 $\max(\hat p, p_{ret}, \text{수축 이동 모델})$ | rev 4: 수축 이동 모델(전제 ④, 알려진 한계 435.7) |

- ④는 `_locked_upper_bound_Pa`의 모델 상계 $\max_j[M_j+R_{ub}(p_{h,j}-p_h)^+]$이다(⑤ 판독 상계가 합쳐지기 전). ④$^{c}_k$는 운반 후보로 이번 읽기 헤드 $p_{h,k}$에서 계산한 값이다.
- 같은 다리에서 CARRY 중 방향이 바뀌면 $\hat x\leftarrow0$, 방향만 바꾸고 운반 후보와 $\hat p$는 유지한다.
- CARRY 다음에 $\lvert u\rvert\le u_{hold}$가 오면 새 구간을 연다(새 창·새 후보). 운반 상태는 지운다. $\hat p$는 감압을 세지 않았으므로 끈끈한 값이 남는다.
- 관문이 주기 안에서 열리면 그 주기의 분류는 CARRY로 두고, 다음 읽기부터 EXT·RET이다. 신장이면 열린 소단계 다음부터 그 주기 안에서 감압을 센다.
- LOCK·HOLD·CARRY 판정은 진단(D1~D3), 출력 명령, 사건과 무관하다. 바뀌는 것은 ③ 추적기, 열주 상계, 대체 로드 추정과 그 기록뿐이다(2.8절 T8).

### 2.2 R5-1·R5-5: 미세 명령 잠금 유지와 열기

- `_update_column_bound`의 닫기 조건 `command_m_s != 0.0`을 rev 5에서는 $\lvert u_k\rvert>u_{hold}$로 바꾼다. 열기 조건도 $\lvert u_k\rvert\le u_{hold}$로 바꾼다.
- 열 때의 창 $W = \tau_v\ln(\max(\lvert u_{last}\rvert,\varepsilon)/\varepsilon)+t_c+T$와 $M_j$ 후보(창 안 표본)는 rev 4 식 그대로다. $u_{last}$는 마지막 $\lvert u\rvert>u_{hold}$ 주기의 명령이다(`_track_moving_leg`는 EXT·RET·CARRY 주기에서만 부른다).
- HOLD 주기는 온라인 비 학습기(`_track_online_ratio`)에 넣지 않는다(학습 전제는 잠김 표본).
- `_remember_command`(CB 방향 판정용)는 실제 명령으로 계속 부른다. CB와 FIXED는 ③을 거부하므로 결과가 같다.
- **HOLD 전제의 성립 범위(유압 검토 2.2절)**: VN 중립의 정상 라인 압력은 1 % $v_{max}$에서 3.6 bar다. 이때 풀릴 수 있는 다리는 $p_r$ < 4.6 bar이고 $p_h$ < 7.6~16.7 bar인 공중·무부하 다리뿐이다. 그런 다리의 압력 변화는 P3에서 $\propto\lvert u\rvert$(약 4 bar/s)라서 ④(≥ 13 bar)가 덮는다. 부하 다리($p_h$ 10~35 bar)가 정상상태에서 풀리기 시작하는 명령은 1.23~1.62 %다. 그래서 **$u_{hold}$ 허용 범위는 0.5~1.2 % $v_{max}$**다(앞 보고서 8절의 0.5~2 %를 좁힘). 이 상한은 P1 회로 값(VN, $c_v$ 0.02, $f_n$ 0.05)에 기대는 가정이다.
- **R5-5가 필요한 이유(결정 146으로 채택)**: P1 플랜트에서는 0을 지나지 않는 미세 부호 반전(+2 → −2 µm/s)에서도 밸브가 $\lvert u_v\rvert\le\varepsilon$를 $t_c$ 동안 지나면 잠긴다. 그 뒤 미세 명령으로는 선 충전이 안 돼 계속 잠긴다. 모니터가 구간을 열지 않으면 G1과 같은 공백이 남는다. 실기에서도 $\lvert u\rvert\le u_{hold}$(겹침 1 % 이하)는 흐르지 않으므로 "잠김"으로 보는 것이 물리와 맞다.

### 2.3 R5-2: 수축 hold 보조 규칙 — (i) 선택

규칙: HOLD·CARRY 주기에서 $u_k<0$이면 그 구간(또는 운반 상태)의 후보 목록에 $\big(M=\texttt{\_lock\_start\_model\_Pa}(i,-1,p_{h,k}),\ p_{h,k}\big)$을 더한다. 출처 표지는 `retract_hold`다. 창 밖이어도 더한다. 이 값은 $\max(\text{수축 이동 모델}(p_{h,k}),\ p_{ret,i})$이다.

| 기준 | (i) $\max(④, \text{수축 이동 모델})$ | (ii) 같은 방향 누적 50 µm에서 hold 끝 |
|---|---|---|
| 덮는 것 | 펌프로 오른 로드 압력 상한(헤드 체크가 열리기 전 B 라인 압력) ≤ 수축 이동 모델이다. 후보로 넣어 두면 그 뒤 하중 감소도 $R_{ub}$로 덮는다 | 가압이 시작되기 전에 hold를 끝낸다 |
| G2·G6 공백 | 생기지 않는다(구간·④를 그대로 들고 간다) | hold를 끝내면 rev 4 수축 분기로 넘어가 ④를 잃는다. 50 µm(0.157 cm³ = 수축 헤드 체크 열림 체적 0.74 cm³의 21 %)에서 다리는 아직 잠겨 있으므로 **원래 J-P3 공백이 다시 생긴다** |
| 매개변수 | 없음(기존 수축 모델 $p_{back}$ 15 bar, $r_p$ 3, $p_{crack}$ 3 bar) | 50 µm가 $V_{line}$·$A_{ann}$ 가정(Q-M9)에 기댄다 |
| 비용 | 미세 수축 뒤 구간이 끝날 때까지 대체 하한이 낮다(전방 $p_h$ 77 bar에서 수축 모델 38.7 bar, 진값 2 bar이면 약 13.8 kN 과보수). 대체 다리에만 걸린다 | 작다 |

- **선택: (i).** (ii)는 hold를 끝내는 순간 rev 4 수축 분기로 돌아가서 이번 J-P3의 기전(잠김 → 미세 수축 → 신장)을 다시 연다. (i)는 상계 논증이 닫혀 있다.
- 수축 이동 모델이 B 라인 열림 압력의 상계인 근거: 수축 헤드 체크 열림 $p_B = p_T + (p_h+p_{cr}-p_T)/\psi$(ψ 3.5, $p_{cr}$ 3 bar, $p_T$ 2 bar) ≤ $p_{back}+(p_h-p_{back})/r_p+p_{crack}$ = $13+p_h/3$ bar. ψ ≥ 2.5이면 $p_h$ ≤ 159 bar에서 성립한다(가정, L-2).
- 비용은 Dg-3(5.5절)에서 과보수 p90과 폐루프 변화로 잰다.

### 2.4 R5-4: 선 충전 상계 관문(CARRY)

목적: P1 플랜트가 잠긴 다리를 해제하는 시각보다 **늦거나 같은 시각**에 추적기가 감압을 세기 시작하게 한다. 관문은 감압을 늦추기만 하므로 상계를 깨지 않는다(늦을수록 $\hat p$가 높다).

**신장(다리 $i$, 소단계 $\Delta t$ 1 ms)**

$$\hat x \leftarrow \max\!\Big(\hat x + \big(\kappa_x\max(\bar u_v,0) - \hat d\big)\Delta t,\ 0\Big),\quad \hat d = \frac{K_n\,g\,\sqrt{\max(\hat p_A-p_T,0)}}{A_h},\quad g=\Big(1-\frac{\lvert\bar u_v\rvert}{c_v v_{max}}\Big)^+$$

$$\hat p_A = p_T + \hat x\,\frac{A_h\beta_{hose}}{V_{line}},\qquad \text{열림: }\ \hat p_A \ge \max\!\Big(p_{h}^{ub}+p_{cr},\ \ p_T+\frac{\hat p+p_{cr}-p_T}{\psi}\Big)$$

- $p_h^{ub} = \max(p_{h,k}, p_{h,k-1}) + e_h$이다. 헤드 판독이 NaN이면 그 주기에는 열지 않는다.
- $e_h$ = **9 bar**(결정 147). 일반식은 $e_h = b_{read}+4.4$ bar다. $b_{read}$ = 행 센서 등급의 헤드 판독 오차 상한(정상: 4 bar 클립 + 3σ 0.6 + 분해능 0.025 = 4.62 bar)이고, 4.4 bar = 주기 안 헤드 혹 3.6 bar(3.4 kN 울림 관찰, **가정**) + 0.8 bar다. 유압 검토 3.2절 격자(81,648건)에서 $e_h$ 5 bar는 624~936건이 플랜트보다 먼저 열렸다(최대 51 ms, 간격 변화 ≥ −0.41 bar, 새 음의 간격 0). 9 bar에서는 0건이다. conservative(약 14 bar 필요)·old_worst(약 21 bar) 등급 행에서는 이 순서가 보증되지 않으므로 그 행의 J-P3는 기록만 한다(6.1절).
- 헤드 체크 조건에서 $\psi p_B$ 항은 뺀다($p_B\ge0$이므로 늦게 열림 = 보수). 로드 압력에는 $\hat p$(상계)를 쓴다(높을수록 늦게 열림).
- 비교 원리: 채움 속도 $\kappa_x\bar u_v\le$ 플랜트 밸브 속도이고 배수 함수가 같으므로 $\hat x(t)\le x_{plant}(t)$다. 문턱은 플랜트 이상이다. 그래서 추적기 관문은 P1 플랜트보다 일찍 열리지 않는다(5절 T-JR-03이 확인).

**수축**: $\hat x$를 $A_{ann}$ 행정 단위로 같은 식(M1c 수축 배수 $K_n g\sqrt{\text{rise}\cdot\text{level}}/A_{ann}$)으로 채운다. 열림은 $\hat x\ge \text{need}^{ub}$이고, need$^{ub}$는 `check_open_delay.retract_dead`를 보수 입력으로 계산한다: $p_h^{ub}$($e_h$ 9 bar 포함), $p_r$ = **$p_{floor}$ = −0.913 bar(g)**, $F_{band}$ = **0**, void 0, $\beta$ 0.69 GPa, $L_{0r}$ 0.10 m, $L_{0h}$ 0.08 m(결정 147).
- 근거(유압 검토 3.3절, 격자 2,268점 × 2다리): need는 $F_{band}$·$p_r$·$s$에 감소, $p_h$에 증가한다. 그래서 가장 큰 need는 $F_{band}$ 0, $p_r$ 최소, $p_h$ 최대에서 나온다. **첫 판의 $F_{band}$ 8 kN은 반대 방향**이었다(need$^{ub}$ < 플랜트 need 6/9건, 최소 비 0.76). 새 값에서는 void > 0인 경우만 남고, 그때 플랜트 로드 압력은 $p_{floor}$라서 어떤 상계도 깨지지 않는다. 시간 계산에서 먼저 열림은 0건이다.
- 대가: 부하 다리의 수축 need가 는다(전방 $p_h$ 77 bar 0.92 → 1.24 mm, 4.71 mm/s에서 CARRY 약 +85 ms; 후방 0.98 → 1.36 mm). 그만큼 J-P3c 판정 창이 길어진다.
- κ_x 0.8의 전제: 추적기 밸브 추정이 플랜트 밸브의 1.25배 이하(같은 τ_v·지연이면 성립).

**관문 매개변수(모두 가정. P1 플랜트 공칭과 같은 값에 보수 쪽 입력만 더함)**

| 기호 | 값 | 출처 |
|---|---|---|
| $V_{line}$, $\beta_{hose}$ | 285 cm³, 0.5 GPa | `CheckValveValues`(Q-M9, H-3) |
| $\psi$, $p_{cr}$, $p_T$ | 3.5, 3 bar, 2 bar | M1c(L-2, H-2) |
| $f_n$(중립 누설 비), $c_v$ | 0.05, 0.02 | M1c VN |
| $K_n$ | $f_n A_h v_{max}/\sqrt{\Delta p_{comp}}$, $\Delta p_{comp}$ 10 bar | 하네스 `params.dp_comp_Pa` |
| $\kappa_x$ | 0.8 | ③ 전달 속도 하한과 같음 |
| $e_h$ | 9 bar(첫 판 5) | 정상 등급 $b_{read}$ 4.62 + 혹 3.6 + 0.8(결정 147, 가정) |
| $F_{band}$(수축 need) | 0(첫 판 8 kN) | need가 $F_{band}$에 감소(결정 147) |
| $p_r$(수축 need) | $p_{floor}$ −0.913 bar(g)(첫 판 $p_T$) | need가 $p_r$에 감소(결정 147) |

**R12 RR 49.0 → 49.1 s 확인 계산**(`rs03_expected_49p1.py`, 결과 `rs03_expected_49p1.json`; 입력 $p_h$ 35.2 bar, 잠긴 $p_r$ 53.9 bar, 앞 주기 명령 0.0749 → 4.71 mm/s는 가정)

| 양 | 경로 A(저장소 함수) | 경로 B(닫힌 식) | 비고 |
|---|---|---|---|
| 플랜트 P1(M1c VN) 헤드 체크 열림 | 70 ms(로드 체크도 70 ms) | – | BL이면 64 ms. 로드 체크가 먼저 열려 $\psi p_B$ 항이 헤드 체크를 바로 연다 |
| $\psi p_B$ 없이 공칭 채움(κ 1) | – | 113 ms(필요 2.06 cm³) | 위 70 ms보다 늦다 = 관문의 보수 쪽 근거 |
| 추적기 관문(κ 0.8, $e_h$ 9 bar) | – | **148 ms**(첫 판 $e_h$ 5 bar: 140 ms) | 49.1 s 읽기는 여전히 CARRY. 갱신 계산은 `rs03_expected_49p1.hand_fill_time`(필요 2.58 cm³, control 재계산 147.95 ms = 유압 검토 148 ms) |
| 추적기 $\bar C_r$ / 플랜트 $C_r$ | 3.583×10⁻¹² / 1.586×10⁻¹² m³/Pa | 3.58×10⁻¹²(원인 보고서) / 1.59×10⁻¹²(hydraulics) | 두 경로 상대차 < 0.1 % |
| $\hat p$(49.1 s), 시작 ④ = 70 bar | 관문 없음 60.5 bar, 관문 ≥ 100 ms 70.0 bar | – | |
| 플랜트 $p_{tr}$(49.1 s), 49.0 s에 53.9 bar | 43.2 bar(70 ms 열림), 42.3 bar(67 ms) | hydraulics 약 45 bar | 간격 ≥ +17 bar(관문 없음), +27 bar(관문) |

- 과보수 비용: 이 사례에서 추적기는 플랜트보다 약 78 ms 늦게 감압을 센다. 일반 신장 시작(잠금 뒤 큰 명령)에서도 0.05~0.2 s 감압이 늦다. $e_h$ 5 → 9 bar 몫은 후방 4.71 mm/s +6.4 ms, 1 mm/s +30 ms, 0.5 mm/s +60 ms, $v_{max}$ +1.4 ms(전방 4.6/21/43/1.0 ms)다. Dg-2·Dg-3(5.5절)에서 과보수 p90 증가로 기록한다.
- 49.1 s의 $\hat p$(70.0 bar)와 간격(+27 bar)은 관문이 100 ms 넘게 닫혀 있는 한 바뀌지 않는다. 148 ms이므로 첫 판 값 그대로다.

### 2.5 R5-3: 탈출 시드(양방향)

- rev 4 `_seed_extension_after_lock`(`commanded > 0`이고 구간 열림)을 rev 5에서는 "직전 읽기에서 구간이 열려 있었고 이번 주기가 CARRY의 첫 주기(또는 관문을 끈 진단에서 EXT·RET의 첫 주기)"로 바꾼다. 방향은 가리지 않는다.
- 값은 직전 읽기의 ④(`stretch.model_bound_Pa`)다. rev 4처럼 `_advance_extend_bound`가 `_update_column_bound`보다 먼저 돌기 때문이다.
- 기록: `lock_seed_raises`(신장, 기존 키), `retract_seed_raises`(수축, 새 키), `carry_raises`(CARRY 끈끈 올림 횟수, 새 키).
- **수축 쪽이 필요한 이유(결정 146으로 채택)**: P1(수축 선 충전 동안 잠김)과 P3(수축 감압 유량 상한)이 있으면 수축 탈출 뒤에도 로드 압력이 잠긴 값 근처에 남는다. 확정된 P3 분기 (c)(3절)로 1 mm/s, $F$ 22 kN, 50 → 30 bar는 **후방 0.42 s(첫 스텝 50.4 bar/s), 전방 0.49 s(44.0 bar/s)**다. 첫 판의 "약 1 s, ≈ 19 bar/s"는 버린 $b_T$=1 꼴 식의 값이었다(유압 검토 1.3절). 수축 중 rev 4 분기는 $\hat p$를 내리지 않으므로, 시드한 ④는 다음 신장까지 남아 상계가 된다. 대가는 긴 수축 뒤 신장 시작의 과보수다(수축 감압 상계는 만들지 않고 RET는 기록만 한다, 결정 146).

### 2.6 대체 로드 추정 요약(rev 4 → rev 5)

| 분류 | rev 4 | rev 5 |
|---|---|---|
| $u=0$ | ④∨⑤ | 같음 |
| $0<u\le u_{hold}$ | 신장 이동 추정 $\max(13, \hat p+\delta_m)$, 구간 닫힘 | ④∨⑤, 구간 유지 |
| $-u_{hold}\le u<0$ | 수축 이동 모델, 구간 닫힘, $\hat p\leftarrow$ 수축 바닥 | ④∨⑤(수축 후보 포함), 구간 유지, $\hat p$ 그대로 |
| CARRY 신장 | (없음) | $\max(13, \hat p+\delta_m)$, $\hat p\ge$ 끈끈한 ④ |
| CARRY 수축 | (없음) | $\max(\text{수축 모델}, \hat p+\delta_m)$ |
| EXT·RET | rev 4 | 같음 |

### 2.7 상계 논증과 반례 조건(③ 명세 3절 표 연장)

- rev 4 논증(단조성: 한 스텝 $G$는 $p$에 증가, $u$에 감소, $C_r$·$p^*$에 증가)은 EXT 주기에 그대로 쓴다. HOLD·LOCK은 ④(잠김 법칙 상계)에, CARRY는 "잠긴 동안 ④ ≥ $p_{tr}$, 풀린 뒤 신장이면 $p_{tr}$은 감압만 함(전제 ①), 수축이면 $p_{tr}\le\max(\text{잠긴 값}, \text{수축 목표})$"에 기댄다.

| # | 반례 조건 | rev 4 | rev 5 처리 | 시험 |
|---|---|---|---|---|
| ①~④ | ③ 명세 3절 그대로 | – | 그대로 | T-P3-3 |
| ⑤ | 미세 반전 + 수축 재잠김 + 잠긴 동안 하중 감소(이번 J-P3) | 깨짐(−26.3 bar) | R5-1·R5-3 | T-JR-04 사례 ⑤ |
| ⑥ | P1 선 충전 동안 잠김 유지(반례 ②의 M1c 경우) | 깨짐(49.1 s, 약 −17 bar, 2.4절 계산) | R5-4 | T-JR-03, T-JR-05 C·D |
| ⑦ | 미세 수축 여러 주기로 로드실 가압 | 깨질 수 있음(최대 약 11 bar) | R5-2 | T-JR-04 사례 ⑦ |
| ⑧ | P3 느린 수축 감압 뒤 신장 | 깨질 수 있음 | R5-3 수축 쪽 | T-JR-04 사례 ⑧ |
| ⑨ | 주기 안 헤드 극값(읽기 사이에 하중이 빠졌다 돌아옴) | 같은 한계 | 남는다. $\delta_m$와 관문 보수로 줄어든다. T-JR-04가 주기 안 하중 무작위 궤적으로 빈도를 기록 | T-JR-04(기록) |
| ⑩ | 가벼운·공중 다리의 수축 채움: 플랜트 수축 목표 $p^*_{ret}(F)=\min\big((\max(p_{bA}, p_{h,thr}(F))A_h-F)/A_{ann},\ p_{relief}\big)$, $p_{h,thr}(F)=\big(F/A_{ann}+p_{cr}+p_{bA}(1-1/\psi)\big)/(\varphi-1/\psi)$(`RodChamberLegParams.moving_target_rod_pressure_Pa(RET, F)`)가 모니터 수축 모델 $13+p_h/3$ bar보다 높다(전방 $F$ < 1.11 kN, 후방 $F$ < 0.14 kN, 공중 전방 $F$ ≈ −1 kN에서 +5.6 bar. 이 범위에서는 헤드가 $p_{bA}$에 클립되어 목표가 $\varphi p_{bA}-F/A_{ann}$와 같다). P3 전부터 있던 전제 ④의 공백이다 | 같은 공백(RET) | 판정에서 뺀다: 수축 CARRY 중 플랜트가 이동 중이고 $p_{tr}\le p^*_{last}$인 읽기는 채움 몫으로 RET와 같은 기록 키에 넣는다(6.2절). $F_{min}$ 보호에는 영향이 없다(6.2절 끝) | T-JR-04 사례 ⑩, T-JR-16 |

### 2.8 T8 근거(대체가 없는 실행의 명령 불변)

- rev 5가 바꾸는 상태는 `_LockStretch`·`_CarryState`, 추적기 $\hat p$·$\hat u_v$·$\hat x$, `_LegWatch.rod_estimate_Pa`다. 앞 둘은 대체 다리의 힘 하한(`_fallback_forces`)과 기록(`_count_tension`, `fallback_lock_log`, `extend_start_record`)에만 들어간다.
- D1~D3 진단, 출력, 사건은 이 상태를 읽지 않는다(`two_pressure.py` 2268~2280·2850~2880행 확인). 그래서 대체 다리가 없는 실행의 명령은 rev 4와 비트 동일해야 한다. 바뀌는 것은 meta의 끝 상태값(`fallback_rod_estimate_Pa`)뿐이다(개정 10 조건 A·B·C 선례).

## 3. 플랜트 옵션 P1~P4(하네스, M2 켬 전제)

| # | 옵션(CLI) | 정의 | 끄는 것·유지하는 것 | 거부 조합 |
|---|---|---|---|---|
| P1 | `line_fill_gate: CheckDelaySetting \| None`(`--line-fill-gate VN`, `--line-fill-gate-volume-scale`, `--line-fill-gate-cv`) | M1c 선 상태 기계(`CheckOpenDelay`의 E1 신장 식, `retract_dead` 수축 need, VN 배수)를 매 1 ms 묶음마다 모든 다리에 돌린다. **플랜트가 잠긴 다리**는 그 방향 체크가 열릴 때까지(신장: 헤드 체크 `is_open`, M1c 정의대로 로드 체크 해제가 먼저; 수축: $x\ge$ need) 커널·법칙 속도 0을 받는다. 열리면 밸브 속도를 그대로 넘긴다. 수축 열림의 M2 시드(`opening_rod_pressure_Pa`)는 예외로 넘긴다(결정 147, 아래 표) | 끔: 크리프 이동, 열림 이동(헤드 배출), 잠금 감쇠기 전환, `RELEASE_SPEED`, 열린 뒤 배수 빼기. 유지(예외): 수축 M2 시드. 풀린 다리(이동 중)는 막지 않는다(방향 반전은 LC 잠금을 거친 경우만 막힘, 단순화) | `check_delay`(M1c 전체)와 함께, BL + LC(D-6), ③ rev 4와 함께(R5-4 없음 = 반례 ⑥) |
| P2 | `lock_anchor_continuous: bool`(`--lock-anchor-continuous`) | 이 스텝에 잠긴 모든 다리(신장·수축): $p_{r0}\leftarrow\max(p_{lag}, p_{floor}) + G_{r,lock}/A_{ann}$. $p_{lag}$ = 마지막 이동 스텝의 M2 지연값이다. 그래서 잠긴 참값 $p_{r0}-G_r/A_{ann}$이 잠금 순간 $p_{lag}$와 같다. 무릎: $\text{knee}=(p_{r0}-G_{r,lock}/A_{ann}-p_{floor})A_{ann}/k_r$(참값 기준으로 $p_{floor}$에서 꺾임). 같은 무릎을 P1의 `_check_delay_inputs` void 계산에도 쓴다. 기존 `_anchor_extension_locks`(r5 B안 −3 bar 계단)는 끈다 | 유지: 해제 쪽(`_start_release`), M2 $\Delta w$ 보정. 기록 `_AnchorRecord`는 같은 열 이름으로 남긴다 | M2 없이, CB와 함께 |
| P3 | `rod_flow_cap_all: bool`(`--rod-flow-cap-all`), M2 법칙 이름 `flow_limited_r6` | `rod_release.flow_limited_rod_pressure_r6`(유압 검토 1.1절 확정): (a) 수축 승압·(b) 신장 감압은 r5와 비트 동일. **(c) 수축 감압** $p^k=\max\big(p_{lag},\ p^{k-1}-A_{ann}s\,[\sqrt{(p_h^{k-1}-p_T)^+/(p_{bA}-p_T)}-1]^+\Delta t/C_r\big)$, $p_h^{k-1}=(F+A_{ann}p^{k-1})/A_h$, $p_{bA}$ 5 bar(다리 params, 등가 $b_{T,ret}$ 1.826). **(d) 신장 승압** $p^k=\min\big(p_{lag},\ \max(p^{k-1}+A_{ann}s\Delta t/C_r,\ p_{lag,F})\big)$, $p_F=-F/A_{ann}$의 인장 몫은 상한에서 뺀다. 가드: $p_{bA}-p_T$ < 0.5 bar이면 `ValueError`. 독립 두 챔버 ODE와 상대차 0.4~1.4 %(하중 10~50 kN). 스냅숏 법칙 표지 6(r5 스냅숏으로 r6 잇기 거부) | r5 함수 `flow_limited_rod_pressure`는 바꾸지 않는다(③ 추적기와 옛 플랜트가 쓴다) | M2 없이 |
| P4 | `rod_reading_truth: bool`(`--rod-reading-truth`) | 제어기에 가는 로드 판독(센서 모형 전 이상값) = `plant_rod_pressure_Pa()`(M2 참값: 이동 중 지연값, 잠김 $p_{r0}-G_r/A_{ann}$). 헤드 = $(F_{net}+p_rA_{ann})/A_h$. 두 경로에 다 건다: `verdict_runs`(지금 `r64.with_two_pressures`)와 r79 계열(`ROD_MODELS`에 `plant_truth` 추가, 지금 기본 `dyn_map`) | 센서 등급 오차 모형은 그 뒤에 그대로 건다 | M2 없이 |

- P1의 M1c 값은 단위 기준 미달 참고값이다(`UNIT_STATUS`). P1을 켠 행의 결과는 "M1c 값 가정 아래"로 쓴다(6.4절 한계 문장).
- P1이 막는 것은 "잠긴 다리의 해제"뿐이다. 그래서 0이 아닌 작은 명령이 풀린 다리에서 흐르는 가정(명세 L-6)은 그대로다. hydraulics P1 (a) 최소안(겹침 차단을 0 아닌 명령에도)은 쓰지 않는다(결정 144: (b) 라인 충전 관문).
- 이 옵션들은 Chrono L2b 플랜트(`l2b_rod_side.py`, 수축 앵커 $p_{ret}$ 같은 구조)에는 넣지 않는다(결정 146: Chrono는 rev 5 제어기만). 나중 이식의 주의 9항목은 유압 검토 4절이다.

**P1 출력 끔 목록과 예외(결정 147, 유압 검토 2.3절)**

| `CheckOpenDelay` 출력 | P1(`CheckOpenGate`) | J-P3 쪽 방향 | 한계 문장 |
|---|---|---|---|
| 신장 로드 체크 해제 뒤 `RELEASE_SPEED`(E2) | 끔. 헤드 체크가 열릴 때까지 잠긴 값을 유지한다 | $p_{tr}$ 과대 → 보수(R12 RR 54 → 36.4 bar 차) | 적는다 |
| **수축 `opening_rod_pressure_Pa`(M2 시드)** | **넘긴다(예외)**. 빼면 플랜트 $p_{tr}$이 물리보다 최대 약 19 bar 낮다(비보수, J-P3c가 덜 엄격) | 시드 유지 = 물리 쪽 | meta `p1_output_exceptions: ["retract_m2_seed"]`로 남기고 한계 문장에 적는다 |
| 수축 `opening_shift_m`(헤드 방출 전방 0.32, 후방 0.45 mm @ 77 bar), `creep_shift_m` | 끔 | 압력 판정 무관, 하중 전이 과도가 작게 나옴 | 적는다 |
| `lock_damping` | 끔(LC 잠김 상태가 정함) | 무관 | – |

- P2와 함께 쓸 때 `_check_delay_inputs`의 무릎·void도 `_locked_knee_m(i)`(참값 기준 무릎)를 써야 한다. 아니면 수축 need의 void가 틀린다.
- 스냅숏 접두사는 `p1g_`(M1c `m1c_`와 분리). 잠긴 다리 + `is_open` 참은 정의상 없지만 단언으로 둔다.

## 4. 구현 명세(python-expert)

### 4.1 파일·함수·필드

| 파일 | 바꿀 것 | 기본값·보존 |
|---|---|---|
| `03_src/outrigger_sim/control/extend_start_bound.py` | `EXTEND_HOLD_REVISION = 5`, `SUPPORTED_REVISIONS = (4, 5)`. `ExtendStartBound`에 rev 5 필드: `hold_speed_ratio: float = 0.01`, `retract_hold_rule: str = "retract_model_candidate"`, `exit_seed_rule: str = "both"`, `line_fill_gate: LineFillGateParams \| None = None`(rev 5면 기본 생성). `__post_init__`은 `SUPPORTED_REVISIONS`만 받는다. **`to_meta()`는 revision 4이면 지금 dict와 키·값이 같아야 한다**(rev 5 필드 제외). 새 dataclass `LineFillGateParams`(2.4절 표). 새 클래스 `LineFillGateBound`(다리별 $\hat x$·방향·열림, `reset(leg)`, `advance_substep(leg, mean_valve_m_s, step_s, head_ub_Pa, rod_ub_Pa, stroke_m) -> bool`). `ExtendStartTracker.advance(..., period_class=None, carry_bound_Pa=None)`: `period_class`가 None이면 rev 4 경로를 한 줄도 바꾸지 않고 탄다. 새 메서드 `carry_raise_to(leg, Pa)`, `seed_raise_to(leg, Pa, direction)`. `record()`에 rev 5 키(`retract_seed_raises`, `carry_raises`, `hold_periods`, `carry_periods`, `gate_open_substeps`, `gate_never_opened_carries`) | 클래스 기본 `revision = 4` 그대로 |
| 같은 파일 | `ExtendBoundState`에 rev 5용 분류 `PeriodClass(StrEnum)`: `lock`, `hold`, `carry_ext`, `carry_ret`, `ext`, `ret`. `ExtendBoundCheck`에 6.2절 키와 `add(..., period_classes=None, used_bounds=None)` 인자. None이면 rev 4 기록 그대로. 새 `ExtendBoundTrace`(per-read 배열, 6.3절). `check_extend_start_meta`는 rev 4·5를 받고 revision을 돌려준다 | 기존 키 이름·뜻은 유지(옛 정의 비교용) |
| `03_src/outrigger_sim/control/two_pressure.py` | `_update_rod_estimates`: rev 5면 `_period_classes(commanded)`를 먼저 정한다. `_advance_extend_bound(head, commanded, stroke, classes)`. `_seed_after_lock`(rev 5, 양방향; rev 4는 기존 `_seed_extension_after_lock` 그대로). `_update_column_bound(..., period_class)`: 닫기·열기 조건, HOLD에서 온라인 비 학습 제외, 수축 후보(`LockStartSource.RETRACT_HOLD`). 새 `_CarryState`(후보·비·출처 복사, 방향, 끈끈한 값) 다리별. 대체 추정은 2.6절 표. 새 읽기 전용 `extend_bound_trace_row()`(다리별 분류, $\hat p+\delta_m$, ④ 또는 ④$^c$, 쓴 추정, 관문 열림, hold 사유). `fallback_lock_log` 요약에 `hold_periods`, `retract_hold_candidates`, `close_reason`, `seed_before_Pa`, `seed_after_Pa`(rev 5만). 스냅숏·pickle: 새 상태가 없으면 빈 상태(10.4 ⑧ 선례) | `TwoPressureSettings` 클래스 기본 `extend_start_rule = "constant"` 그대로 |
| `03_src/outrigger_sim/control/c2.py` | `C2Controller.extend_bound_trace_row()` 통과 함수(`locked_model_bound_Pa` 선례). `with_10hz_d1`의 기본 인자는 바꾸지 않는다 | 프리셋 기본 꺼짐 |
| `03_src/outrigger_sim/hydraulics/v5_options.py` | `HydraulicOptions` 새 필드: `extend_start_hold: bool = False`(`extend_start_tracked` 필요), `line_fill_gate: CheckDelaySetting \| None = None`, `lock_anchor_continuous: bool = False`, `rod_flow_cap_all: bool = False`, `rod_reading_truth: bool = False`. `to_dict`는 꺼진 필드를 빼고(지금 digest 보존), `rod_flow_cap_all`이면 `m2_law = "flow_limited_r6"`. `from_dict`·`from_stored`는 법칙 이름과 필드를 맞춰 본다. `validate`·`check_extend_start`에 3절 거부 조합. `apply_controller_options`: `extend_start_hold`이면 `ExtendStartBound(revision=5)`. CLI 인자 5개(모두 `argparse.SUPPRESS`). 태그(4.3절) | 모든 새 필드 꺼짐 |
| `03_src/outrigger_sim/hydraulics/rod_release.py` | `FLOW_LIMITED_R6_LAW = "flow_limited_r6"`, `flow_limited_rod_pressure_r6(previous_Pa, target_Pa, speed_m_s, step_s, lag_s, compliance_m3_Pa, head_area_m2, annulus_area_m2, is_retract, cylinder_force_N, head_back_retract_Pa, *, meter_out_ratio, spool_reference_drop_Pa, tank_pressure_Pa)`(유압 검토 1.5절, 참조 구현 `hr01_p3_flow_law.py`의 `r6()`), `RETRACT_DRAIN_MIN_DROP_PA = 0.5e5`, `STORED_LAWS`에 추가, `RodPressureFlowLaw(law=...)` 선택과 `meta()`에 법칙 이름 | `FLOW_LIMITED_LAW` = r5와 그 함수 그대로 |
| `03_src/outrigger_sim/hydraulics/check_open_delay.py` | `CheckOpenGate(CheckOpenDelay)`: 상태 진행은 부모와 비트 동일, 출력만 3절 P1(잠긴 다리 + 닫힘 = 0, 그 밖 = 입력 속도, 크리프·열림 이동 0, 감쇠 False). 예외로 수축 열림의 `opening_rod_pressure_Pa`는 그대로 넘긴다. `summary()`·`meta()`에 `"mode": "gate_only"`, `"output_exceptions": ["retract_m2_seed"]` | 부모 클래스 그대로 |
| `04_scripts/04_hydraulic/coupled/harness_hydraulics.py` | P1 `_step_with_line_fill_gate`(M1c 입력 순서는 지금 `_step_with_check_delay`와 같이 LC 겹침 차단 뒤·흐름 분배 앞, 1 ms 묶음; 수축 시드는 `_seed_rod_pressure`로), P2 `_anchor_continuous`(P2 켬이면 `_anchor_extension_locks` 건너뜀; `_check_delay_inputs`의 무릎도 `_locked_knee_m`), P3 `_RodPressureLag.relax`가 `force_N`과 `p_head_back_retract_Pa`를 r6에 넘기고 그 스텝 목표를 다리별 `last_target_Pa`로 남김(판 3, J-P3c 경계), P4 판독 함수 `with_plant_truth_pressures(plant, m, ha)`. per-read 추적(`check_extend_bound`가 `extend_bound_trace_row()`와 플랜트 상태를 함께 받음), per-lock 기록 `lock_log`(6.3절). `plant_record`에 새 키 | 옵션 꺼짐이면 새 줄이 돌지 않음 |
| `04_scripts/01_dynamics/s8_g4_rodside_check.py` | 무릎 식을 메서드 `_locked_knee_m(i)`로 뽑는다(기본 = 지금 식, 비트 동일). P2 하위 클래스가 덮어쓴다 | 옛 실행 해시 불변(T-JR-01) |
| `04_scripts/03_control/s8/r64_g4_closed_loop.py`, `r79_sensor_screen.py` | P4 판독 선택점(`with_two_pressures` 호출부 246·542행, `rod_split_function`에 `plant_truth`) | 기본 경로 그대로 |
| `04_scripts/04_hydraulic/coupled/run_v5.py` | `SETTINGS`에 4.2절 설정, `T4H_SETTINGS`에 추가, 436.9 배치 이름(예: `j9_main`, `j9_diag`). 기존 `REQUIRED_SETTINGS`·배치 정의는 그대로 | 기존 배치 해시 불변 |
| `04_scripts/04_hydraulic/coupled/lock_window_alignment.py` | rev 5 meta면 구간 재구성을 `abs(u) <= u_hold` 규칙으로 한다(대체 다리 로그 대조용). J11 판정 기준(0 명령 표본, $n_{late}$)은 그대로 0 명령 기준으로 따로 계산한다 | rev 4 meta는 지금 그대로 |
| `t4h_replay.py`, `chrono_t45_replay.py` | `--extend-start-revision {4,5}`(meta 재구성, P4 행이면 판독 = 참값 재생 확인) | 기본 4 |
| J-P3 판정 도구(두 경로: `j_p3_inputs.py`·`judge_stage1_4368.py` 계열과 경로 2 도구) | 6절 정의의 `j_p3_judgement_rev5(records)`. rev 4 행은 기존 `j_p3_judgement` | – |

### 4.2 하네스 설정(`run_v5.SETTINGS`)

| 이름 | 흐름 제한 | 플랜트 | 제어기 | 쓰임 |
|---|---|---|---|---|
| `VB`, `LS1`~`LS4` | 켬 | 기존(M2 r5 + LC + 창) | ③ rev 4 | 그대로(436.8 결과) |
| `VBH` | 켬 | 기존 VB | ③ rev 5 | 제어기 단독 효과, T8(옛 플랜트), Dg-3 짝. J-P3는 기록 전용(9.9절 플랜트 산물) |
| `LSH1`~`LSH4` | 켬 | 기존 LS1~LS4 | ③ rev 5 | R12 사례 재생 진단만 |
| `VBJ` | 켬 | VB + P1(VN, 1.0, 0.02) + P2 + P3 + P4 | ③ rev 5 | **436.9 판정** |
| `LSJ1`~`LSJ4` | 켬 | `VBJ`에서 LC만 LS1~LS4 값(0.01/0.05, 0.05/0.05, 0.02/0.02, 0.02/0.10) | ③ rev 5 | **436.9 판정** |
| `VBJ0` | 켬 | `VBJ`와 같음 | ③ 끔(`constant`) | T8(새 플랜트), H-7 짝(③ 켬·끔), Dg-3 짝 |

- 설정 표의 `_VB_PLANT_J = {**_VB_PLANT, "line_fill_gate": _vn(1.0), "lock_anchor_continuous": True, "rod_flow_cap_all": True, "rod_reading_truth": True}` 꼴로 둔다.
- 시험 전용 조합 "P1만 + rev 4"(T-JR-05 C)는 설정 표에 넣지 않는다. 시험에서만 `v5_options.ALLOW_GATE_WITH_REV4_FOR_TEST`(모듈 상수, 기본 False)를 바꿔 만든다.

### 4.3 태그

| 상수 | 값 | 규칙 |
|---|---|---|
| `EXTEND_HOLD_CONTROLLER_TAG` | `final_C4G2_P3H` | ③ rev 5 기저. 접미사는 기존 순서 그대로 `_LAS` → `_K1` → `_TCL`: 프리셋 `final_C4G2_P3H_LAS_K1` |
| `EXTEND_HOLD_TAGS` | `("final_C4G2_P3H", "final_C4G2_P3H_LAS", "final_C4G2_P3H_LAS_K1")` | 목록만. 판정은 함수로 |
| `is_extend_start_tag(tag)` | 기저가 `final_C4G2_P3` 또는 `final_C4G2_P3H`이면 참 | ③ 켬 판별(바뀐 뜻: rev 4·5 모두) |
| `extend_start_revision_of_tag(tag)` | `final_C4G2_P3*` → 4, `final_C4G2_P3H*` → 5, 그 밖 None | **설정을 태그에서 다시 만드는 모든 도구는 이 함수를 써야 한다** |
| `controller_tag(options, config)` | `extend_start_hold`이면 P3H 기저 | 플랜트 옵션 P1~P4는 태그가 아니라 설정 이름과 `hydraulic_options`로 판별 |

- 충돌 점검: `_P3H`는 `_LAS`·`_K1`·`_TCL`로 끝나지 않는다. 하네스 키 토큰 `K1`(크롤러 강성)과 겹치지 않는다. 저장소 안에 `P3H`·`VBJ`·`LSJ`·새 필드 이름의 기존 사용은 없다(grep 0건, 2026-11-16).
- **감사 대상(VB 태그를 문자열로 박아 둔 곳, 436.9 러너가 새 태그를 그대로 받는지 확인)**: `04_scripts/04_hydraulic/coupled/resume_k1_steps.py:71-72`, `v5_rerun.py:68`, `las_t3_judge.py:71`, `02_chrono/v5_resume_4368_chrono_rows.py:79·184·718`(③ 판별 → `VB_TAG` 재태그: rev 5 행을 rev 4 태그로 바꾸면 안 됨), `s9_batch.py:428`, `run_S9.py:1532`, `b1_creep_chrono_rows.py:47`, `las_chrono_rows.py:75`, `las_p5r4_k1_chrono_rows.py:60`, `03_control/d8x/d8x_spec.py:164`, `j_p3_inputs.py:34`(`P3_CONTROLLER_TAGS = EXTEND_START_TAGS`). 조용히 재태그하지 말고 모르는 태그는 거부하게 한다.

### 4.4 기존 기본값·해시 보존 점검표

| 항목 | 확인 |
|---|---|
| 클래스·프리셋 기본 | `TwoPressureSettings.extend_start_rule = "constant"`, `ExtendStartBound.revision = 4`, `with_10hz_d1` 기본 인자, `HydraulicOptions()` 모든 새 필드 꺼짐 |
| meta·digest | rev 4 `ExtendStartBound.to_meta()` 키 집합 불변, 저장된 모든 설정(`SETTINGS` 15개 + U-9·D-1·u3·u6 설정)의 `HydraulicOptions.to_dict()` digest 불변 |
| 함수 | `flow_limited_rod_pressure`(r5) 출력 격자 해시 불변, `CheckOpenDelay` 상태·출력 불변 |
| 명령 해시 | 기존 VB·LS·V0 배치의 `commands_sha256` 표본 불변(T-JR-01) |

## 5. 단위 시험과 합격 기준

### 5.1 회귀(옵션 꺼짐)

| ID | 내용 | 합격 |
|---|---|---|
| T-JR-01 | 옵션 꺼짐 회귀: B-2, 기존 `two_pressure`·`extend_start_bound`·`v5_options`·`harness_hydraulics` 시험, `test_s8_ml_main.py:229`, B-7, T-P3-1~5, 4.4절 표 | B-2 23/23, 기존 시험 전부 통과, digest·meta·함수 격자 해시 불변. 저장 h10 줄 28·172·245와 같은 사례 재실행 `commands_sha256` 동일 |
| T-JR-02 | 태그·설정: 4.3절 함수 표, 접미사 조합(`_LAS`, `_K1`, `_LAS_K1`, `_TCL`) 전부, `to_dict`/`from_dict` 왕복, 거부 조합 3절 | 표대로. 거부는 `ValueError`/`SystemExit` |

### 5.2 새 규칙 단위 시험

| ID | 내용 | 합격 |
|---|---|---|
| T-JR-03 | 선 충전 관문 상계(속성 시험, 시드 20261116): 무작위 명령열 1,000개(잠금 → 0·미세·큰 명령, 방향 반전, 0.05~5 % $v_{max}$), 헤드 5~200 bar, $p_r$ = 바닥(−0.913)·0·$p_T$·~80 bar, **헤드 판독 오차 ±4.62 bar(정상 등급 상한, 양 부호)**, **주기 안 헤드 혹 0~3.6 bar**($p_r$은 체적 비로 반대), **플랜트 $F_{band}$ 0~16 kN**, **void 0·0.2 mm**, VN·BL. 플랜트 = `CheckOpenGate`(P1 공칭, 1 ms 묶음, 밸브 지연 평균 속도), 추적기 = `LineFillGateBound`($e_h$ 9 bar, need$^{ub}$ $F_{band}$ 0·$p_r$ $p_{floor}$). 수축 need의 $p_h$·$p_r$·$F_{band}$·$s$ 단조성 격자 | 신장·수축 모두 **"관문이 감압·RET 전환을 세는 첫 소단계 ≥ 플랜트 해제 묶음"** 위반 0. void > 0 경우만 따로 센다(기록). 단조성: need가 $F_{band}$·$p_r$·$s$에 감소, $p_h$에 증가(위반이면 격자 최대로 바꾸고 다시 시험). 기준값 재현: R12 RR(VN) 플랜트 70 ms, 관문 **148 ms**(±1 ms) |
| T-JR-04 | T-P3-3 확장(속성 시험, 시드 20261107 + 20261116): 단일 다리 모니터 구동 + 플랜트(옛 r5 플랜트, P1~P3 플랜트 둘 다, 내부 스텝 5×10⁻⁴ s, 잠긴 동안 무작위 하중 궤적). 명시 사례: **⑤**(긴 잠금 39 bar → −2 µm/s 1주기 → +2 µm/s → 잠긴 동안 −70 kN/s 0.3 s → 4.7 mm/s), **⑦**(2 bar 잠금 → −0.2 mm/s 2 s), **⑧**(하중으로 50 bar 잠금 → −1 mm/s 0.5 s → +4.7 mm/s; P3 (c)로 0.42~0.49 s에 30 bar), **⑩**(공중 전방 $F$ −1 kN 신장 잠금 → $v_{max}$ 수축: 채움 몫으로 분류되는지). 매개변수 공칭·감도 끝(β 0.69~1.6 GPa, $L_{0h}$ 0.05~0.08, $L_{0r}$ 0.02~0.10 m, B 호스 +36 %) | rev 5: 모든 읽기에서 J-P3a·c 위반 0, J-P3b 허용 초과 0. rev 4: 사례 ⑤가 위반으로 재현(반례 기록). 반례 ① 사례는 따로 센다. ⑨(주기 안 헤드 극값)는 빈도·최대 크기를 기록(판정 아님) |
| T-JR-05 | HOLD 의미 단위: (a) 0 → +2 µm/s → −2 µm/s → 0에서 구간이 한 번만 열리고 닫히지 않음, ④ 매 주기 갱신. (b) $\lvert u\rvert = u_{hold}$는 HOLD, $u_{hold}(1+10^{-9})$는 CARRY. (c) $u<0$ HOLD에서 후보 `retract_hold` 1개 추가, ④ ≥ 수축 모델. (d) CARRY 첫 주기 시드(신장·수축 각각), 끈끈 올림. (e) HOLD에서 온라인 비 학습기 미호출. (f) rev 4 pickle → rev 5 복원(빈 상태). (g) rev 5 meta 키는 rev 5에서만 | 정의대로 |
| T-JR-06 | P1 플랜트(hydraulics 7절 기준): 잠긴 다리에 ±2 µm/s × 1 s → 해제 0. 4.7 mm/s → 0.1 s 안에 해제. `CheckOpenGate`의 `x`·`is_open`·`rod_released`가 같은 입력의 `CheckOpenDelay`(VN 1.0)와 비트 동일. 크리프·열림 이동·감쇠·시드 출력 0 | 정의대로 |
| T-JR-07 | P2: $G_{r,lock}\ne0$ 재잠김에서 $\lvert\Delta p_{tr}\rvert$ ≤ 0.01 bar, $\lvert\Delta p_h\rvert$ ≤ 0.01 bar, 힘 차 ≤ 1 N. 잠긴 뒤 $\Delta p_r/\Delta p_h$ = −1.2278(±10⁻⁴). 참값 최소 = $p_{floor}$ ± 1 Pa. 신장 잠금 $\lvert p_{r0}-G_{r,lock}/A_{ann}-p_{lag}\rvert$ ≤ 1 Pa(−3 bar 계단 없음) | 정의대로 |
| T-JR-08 | P3 `flow_limited_r6`(유압 검토 1.4절 기준 그대로). ① (a)·(b) 분기는 r5와 격자 해시 비트 동일. ② (c)·(d) 기준값 재현(상대 10⁻⁹, $\Delta t$ 5×10⁻⁴ s, τ 0.05 s): (c) 미세 $p^0$ 80 bar·$F$ = 210 bar·$A_h$ − 80 bar·$A_{ann}$·1 µm/s·200스텝 Δp 전방 −0.015359 / 후방 −0.014512 bar; (d) 미세 2 bar·$F$ 10 kN·1 µm/s·200스텝 +0.0020963 / +0.0019808 bar; (c) 예 50 bar·22 kN·1 mm/s 첫 스텝 44.0 / 50.39 bar/s, 30 bar 도달 0.4935 / 0.4245 s, 1 s에 13.095 / 14.574 bar. ③ 1 µm/s × 0.1 s(수축 감압 $p_h$ ≤ 210 bar, 신장 승압)에서 $\lvert\Delta p\rvert$ < 0.1 bar. ④ (첫 판의 "$v_{max}$에서 r5 ±1 %"를 바꿈) 상한이 묶이지 않는 스텝은 r5와 비트 동일, 1.3절 격자의 0.3 s 시점 차 ≤ 0.3 bar, 일시 최대 차(≤ 12 bar)는 기록만. ⑤ 한 스텝이 $p$에 단조 증가(기울기 ≥ 0). ⑥ 고정점 없음: 수축·$p>p^*$·$s>0$인 모든 격자점에서 $p^k<p^{k-1}$(엄격) | 정의대로 |
| T-JR-09 | P4: 오차 끈 실행에서 매 읽기 로드 판독 = `plant_rod_pressure_Pa()`(이동 중 포함, ≤ 10⁻⁹ Pa), 헤드 판독 식. T4h 재생(`t4h_replay --extend-start-revision 5`)이 ext 판정을 정확히 재현 | 정의대로 |

### 5.3 사례 재생(R12 bottom-FL-Fs4 o0.0, RR; 격자 r69·r67)

예측은 결과 전에 고정한다(판 2 갱신은 5.4절 표). 예측과 다르면 멈추고 원인을 본다(결정 96 멈춤 조건 "허용 범위 밖 변경"에 넣는다).

| 변형 | 설정 | 기대 결과(합격) |
|---|---|---|
| A 재현 | VB, LS1~LS4(rev 4, 옛 플랜트) | 저장 h10 줄과 `commands_sha256`·`extend_bound_check` 동일: VB 2 / −9.806 bar @ 48.9, LS1 0 / +0.486, LS2 3 / −9.643 @ 48.8, LS3 4 / −26.334 @ 48.8, LS4 0 / +0.500. 격자 `grid_r69_bottom` results[12].runs[0] = VB 값과 같음, `grid_r67_top` results[13].runs[3] FR 3 / −0.900 @ 48.7 |
| B 제어기만 | VBH, LSH1~LSH4(옛 플랜트 + rev 5) | **명령 해시 = A**(대체 다리 없음, T8). RR 48.7~49.0 s 읽기 분류 HOLD(작용 −0.00194, +0.00213, +0.0359, +0.0749 mm/s 모두 ≤ $u_{hold}$), 49.1 s CARRY, `seed`/`carry_raises` ≥ 1. J-P3a 위반 0(49.1 s 이후 $\hat p+\delta_m$ ≥ ④ 약 64~78 bar). J-P3b: VB·LS2·LS1·LS4 위반 0. **LS3는 48.8 s에 약 −3 bar(④ ≈ 13 + 1.355 × (77.7 − 47.2) ≈ 54 bar 대 $p_{tr}$ 57.4 bar) 허용 초과 가능**. 이는 앵커 계단 +20.8 bar·헤드 +6.9 bar(hydraulics H3) 플랜트 산물이라 기록 전용이다 |
| C P1만 + rev 4(시험 전용) | VB 플랜트 + P1, P2~P4 끔, rev 4 | RR 43.39 s 잠금 뒤 첫 $\lvert u\rvert>u_{hold}$ 읽기(49.0 → 49.1 s 주기)까지 잠김 상태 변화 0. 해제 49.06~49.08 s. 옛 정의 J-P3 위반이 **49.1 s 읽기로 옮겨 남음**, 간격 −25 ~ −8 bar(추정 −14~−17). 48.7~49.0 s는 ext_locked, `locked_unpaired_reads` ≥ 3. 위반이 없거나 간격이 범위 밖이면 멈춤 |
| D P1만 + rev 5 | VB 플랜트 + P1, rev 5 | 잠김 동작은 C와 같음. J-P3a·b·c 위반 0. 49.1 s CARRY, $\hat p$ ≈ ④(49.0 s) ≈ 70 bar, 간격 ≥ +15 bar(계산 +27). HOLD 읽기 ④ − $p_{tr}$ ≥ +10 bar(hydraulics 물리 기준 +15.4~+16.4). **C의 49.1 s 위반을 D가 덮는 것**이 이 묶음의 핵심 합격이다 |
| E 전체 | VBJ, LSJ1~LSJ4 | 같은 미세 반전 순서가 다시 나오면: RR 잠김 변화 0(43.39 s ~ 첫 $\lvert u\rvert>u_{hold}$), J-P3a·b·c 위반 0, $p_{tr}$(48.8/48.9/49.0 s)가 hydraulics 물리 기준(VB 48.49/52.88/53.92, LS1 46.98/51.06/53.15, LS2 47.98/52.45/53.51, LS3 49.43/53.29/55.00, LS4 46.78/51.86/53.36 bar)과 ±4 bar 안(폐루프 힘 ±2 kN 몫), 다섯 설정의 $p_{tr}$(49.0 s) 범위 ≤ 3 bar. 모든 잠금 $\lvert\Delta p_{tr}\rvert$ ≤ 0.01 bar. 순서가 다르게 나오면 RR 시간선을 기록하고 판정은 J-P3 정의대로(멈춤 아님) |
| F 시나리오 ② | `grid_r67_top` FR 행(offset 0.075, ready, 8.0)을 A·B·E로 | A = 저장값, B·E 위반 0 |

### 5.4 예측 고정 표(갱신판, 결과 보기 전)

이 표는 갱신판에서 결과를 보기 전에 고정한다. 판 1 예측 가운데 결정 147·유압 검토로 바뀐 것과 바뀌지 않은 것을 함께 적는다. 이 판을 쓰는 시점에 436.9 실행·시험 결과는 없다(python-expert 구현 진행 중, control-expert는 출력을 보지 않았다).

| # | 항목 | 판 1 값 | 판 2 값 | 바뀐 이유 |
|---|---|---|---|---|
| 1 | R12 RR 49.0 → 49.1 s 추적기 관문 열림 | 140 ms | **148 ms** | $e_h$ 5 → 9 bar(결정 147). 필요 체적 2.06 → 2.58 cm³ |
| 2 | 49.1 s 분류 / $\hat p$ / 간격 | CARRY / 70.0 bar / +27 bar | **같음** | 관문이 100 ms 넘게 닫힌 채라 값이 같다 |
| 3 | 사례 D 합격(간격 ≥ +15 bar, HOLD ④ − $p_{tr}$ ≥ +10 bar) | – | **같음** | 신장 쪽 값만 바뀌었고 위 2가 같다 |
| 4 | 사례 B·C | – | **같음** | B는 옛 플랜트(시드 예외·P3 무관), C는 rev 4(관문 없음) |
| 5 | 사례 E $p_{tr}$(48.8/48.9/49.0 s) ±4 bar, 범위 ≤ 3 bar | – | **같음** | RR 시간선에 수축 열림이 없어 수축 시드 예외가 걸리지 않는다. P3 (b)는 r5와 같다 |
| 6 | T-JR-03 관문 기준값 | 140 ms | **148 ms** | 1과 같음 |
| 7 | 수축 감압 예(1 mm/s, 22 kN, 50 → 30 bar) | ≈ 19 bar/s, 약 1 s | **후방 50.4 bar/s·0.42 s, 전방 44.0 bar/s·0.49 s** | P3 (c)를 $p_{bA}$에 맞춘 식으로 확정($b_T$=1 꼴 버림) |
| 8 | T-JR-08 $v_{max}$ 기준 | r5 대비 ±1 % | **묶이지 않는 스텝 비트 동일, 0.3 s 시점 차 ≤ 0.3 bar** | 가벼운 다리의 높은 잠금 압력은 $v_{max}$에서도 유량에 묶여 일시 최대 11.8 bar 차가 난다 |
| 9 | 수축 CARRY 길이(전방 $p_h$ 77 bar, 4.71 mm/s) | need 0.92 mm 기준 | **need 1.24 mm, 약 +85 ms** | $F_{band}$ 8 kN → 0, $p_r$ $p_T$ → $p_{floor}$(결정 147) |
| 10 | Dg-3 135키 J-P3 판정 집합 | 135키 | **L2 1키(판정), L3 134키(기록)** | 결정 147(normal 등급 행만) |
| 11 | 공중 전방 다리 수축 노출 | (없음) | `jp3c_fill`·`ret` 기록에 최대 약 +5.6 bar 위반이 나올 수 있다(판정 아님). `jp3c_breach_reads` 0 | 6.2절 판단(갇힌 몫만 판정). 유압 검토 1.6절의 "약 +4 bar"는 첫 읽기 추정, 여기서는 정상 목표 기준 상한 |
| 12 | 수축 시드 계단(P1 예외) | (없음) | 시드 순간 로드 압력 +약 19 bar(부하 다리 $p_h$ 77 bar·$p_r$ 2 bar), 헤드 판독 +5 bar, 순 힘 연속 | 결정 147로 시드 유지 |
| 13 | (판 3) 11의 판정 집합 | 이동 중·잠김 구분 없이 $p_{tr}$ 대 $p^*$ | 플랜트가 잠긴 `carry_ret` 읽기는 판정(갇힌 몫). 공중 전방 사례에서 그 읽기의 $p_{tr}$은 P2 앵커 약 5 bar, 비교값 약 14.7 bar라 **`jp3c_breach_reads` 0 그대로**. 이동 중 읽기는 목표(공중 전방 20.3 bar) 아래에서 오르므로 채움 몫, 기록 위반 최대 **+5.6 bar 그대로** | 유압 검토 10절 #3. 값은 바뀌지 않고 판정 집합만 넓어진다 |
| 14 | (판 3) 경계 값 | 읽기 시각 $F$로 계산한 $p^*_{ret}(F)$ | 플랜트 마지막 스텝 목표 $p^*_{last}$. R12 RR 추적에서 둘의 차 ≤ 0.020 bar, 분기 쪽 뒤집힘 0건이라 **5.3절 사례 예측은 바뀌지 않는다** | 유압 검토 10절 #2 |
| 15 | (판 3) 닫힌 식 범위 | 표기상 모든 $F$ | 전방 $F$ ≤ 3.6 kN, 후방 ≤ 2.2 kN에서만 함수와 같음. 반례 ⑩의 노출 범위(전방 < 1.11, 후방 < 0.14 kN)와 +8.2 / +5.6 / +2.9 bar 값은 이 범위 안이라 **바뀌지 않는다**. 부하 다리 읽기가 판정으로 새지 않는지를 T-JR-17로 확인 | 유압 검토 10절 #1 |

### 5.5 묶음 회귀(436.9 본 실행 전 진단)

| ID | 내용 | 합격 |
|---|---|---|
| T-JR-10 T8(옛 플랜트) | VBH 대 저장 VB: T-P3-5 표본 20행, 개정 8 7.2 해시 22행 | 명령 해시 **20/20**, 22/22. meta 차이는 끝 상태값만(개정 10 조건 A·B·C) |
| T-JR-11 T8(새 플랜트) | VBJ 대 VBJ0, 같은 20행 | 20/20 |
| T-JR-12 Dg-3 | 135키(`dg3_keys.txt`): VBH 대 저장 H-6(rev 4), VBJ 대 VBJ0 | L2 통과 → 실패 0, 새 FAULT 0, 첫 READY +30 s 초과 0, J-P3a·b·c 위반 0(VBJ의 normal 등급 L2 1키만 판정. L3 conservative 134키는 기록만, 결정 147). 기록: 대체 다리 하한 − 진값 > 0.6 kN 수, 과보수 p50/p90/p99 증가, HOLD·CARRY 주기 수, 수축 후보 수, 시드 수 |
| T-JR-13 Dg-2 | 저장 T4h(`h10_reuse_rerun_t4h`, `h6_dg3_v4on_t4h`)를 rev 5로 재생 | 오류 0. 과보수 p90 증가·관문 지연 분포 기록(권고 조건 4 선례: 문턱 없음, 비용 기록) |
| T-JR-14 정렬 | `lock_window_alignment`를 VBH·VBJ Dg-3 135행에 | 대체 다리 로그 대조 불일치 0, J11 $n_{late}$ > 0 행 0 |
| T-JR-15 재잠김 계단 | VBJ 135행 + E 사례의 per-lock 기록 | `relock_step_over_1bar_count` 0(hydraulics 7절 권고 집계), VBH는 기록. 수축 시드(P1 예외)가 만드는 압력 계단(+약 19 bar, 헤드 판독 +5 bar)은 잠금 계단이 아니므로 따로 센다(`p1_retract_seed_count`, `p1_retract_seed_step_max_bar`), 순 힘은 연속(≤ 1 N) |
| T-JR-17 갇힌·채움 경계(판 3) | 단위: ① `last_target_Pa`가 같은 스텝 `flow_limited_rod_pressure_r6`에 넘긴 목표와 비트 동일. ② 경계식 함수 대 닫힌 식: $F$ −20~300 kN 격자에서 전방 $F$ ≤ 3.6 kN·후방 ≤ 2.2 kN에서만 같고 그 밖은 함수가 큼(유압 검토 10절 값 재현: $F$ 5 / 25 / 50 kN 전방 −4.0 / −61.7 / −133.9, 후방 −9.7 / −80.0 / −167.9 bar). ③ 부하 다리($F$ 25 kN) 수축 채움 읽기가 `jp3c_fill_reads`로 감(판정 집합으로 새지 않음). ④ 플랜트가 잠긴 `carry_ret` 읽기는 $p_{tr}$이 $p^*$ 아래여도 `jp3c_reads`. ⑤ $p_{tr}=p^*_{last}$는 채움 | 정의대로 |
| T-JR-16 가벼운 다리 수축 | 단위: 공중 전방 다리($F$ −1 kN, P2 앵커 5 bar, $M$ 13.5 bar) 신장 잠금 → $v_{max}$ 수축(P1~P4 플랜트, rev 5). 묶음: VBJ 전 행의 `jp3c_fill_*`·`ret_*` 집계 | 단위: 수축 CARRY 읽기 가운데 플랜트가 잠긴 읽기(P1 충전 중, $p_{tr}$ ≈ 앵커 5 bar)는 `jp3c_reads`(갇힌 몫, 위반 0), 이동 중이고 $p_{tr}\le p^*_{last}$인 읽기는 `jp3c_fill_reads`로 가고, 그 위반 최대 ≤ 수계산 $p^*_{ret}$ − 수축 모델 = +5.6 bar(+0.5 bar 여유). `jp3c_breach_reads`(갇힌 몫) 0. 그 읽기들의 대체 하한 ≤ 1.2 kN(< $F_{min}$). 묶음: 기록 |

## 6. J-P3 정의 보완안(436.9 규칙 초안 문장)

### 6.1 적용 대상

> "J-P3(436.9)는 ③ revision 5 행(기저 태그 `final_C4G2_P3H`, `extend_start_revision_of_tag` = 5)에 적용한다. 판정 행은 하네스 설정 VBJ·LSJ1~LSJ4이다. rev 4 행(기저 `final_C4G2_P3`)은 개정 8 3.2절·개정 9 3.2절 정의로 계속 판정하며 두 정의를 한 행에 섞지 않는다. VBH·LSH1~LSH4(옛 플랜트 + rev 5)의 J-P3 기록은 9.9절 플랜트 산물을 포함하므로 기록 전용이다. 로드 판독이 없는 헤드 전용 구성의 처리(개정 9 3.2 표)는 그대로다."

> "판정 행은 헤드·로드 압력 판독 오차가 normal 등급 이하인 행이다. 이상 센서 행(하네스 판독 그대로, r79 등급 L0·L1)과 normal 등급 행(L2, L2nocal, L2imuideal)이 여기에 든다. conservative(L3)·old_worst(L4) 등급 행의 J-P3 키는 기록만 하며 묶음 등급에 넣지 않는다(결정 147). 이유는 선 충전 관문 여유 $e_h$ 9 bar가 normal 등급 판독 오차 상한(4.62 bar) + 주기 안 헤드 혹 3.6 bar로 정한 값이라 그 위 등급에서는 '추적기가 플랜트보다 늦게 연다'가 보증되지 않기 때문이다(conservative 약 14 bar, old_worst 약 21 bar 필요). 행의 등급은 결과 줄의 센서 등급 meta로 정하고, 등급 meta가 없는 줄은 이상 센서 경로로 선언된 경우(verdict_runs 하네스 줄)만 이상 센서로 보며, 그 밖은 설정 결함이다."

### 6.2 읽기 분류와 판정 키

> "읽기 $k$, 다리 $i$의 분류는 모니터가 그 읽기에 쓴 추정으로 정한다(2.1절 표 PeriodClass: `lock`, `hold`, `carry_ext`, `carry_ret`, `ext`, `ret`). 플랜트 상태(이동 신장·이동 수축·신장 뒤 잠김·수축 뒤 잠김)는 기록 칸이며 판정 집합을 정하지 않는다. 플랜트 참값 $p_{tr}$은 읽기 시각의 값이다(그 뒤 플랜트는 움직이지 않았다)."

| 키 | 대상 읽기 | 비교 | 허용 | 판정 |
|---|---|---|---|---|
| `jp3a_breach_reads` | `ext` + `carry_ext` | $p_{tr}$ > $\hat p+\delta_m$ | 1 Pa | **판정**: 합 = 0 |
| `jp3b_breach_over_tol_reads` | `hold` | $p_{tr}$ > ④ | 0.6 kN/$A_{ann}$(T4h 허용과 같음; 전방 1.59, 후방 1.91 bar) | **판정**: 합 = 0 |
| `jp3c_breach_reads` | `carry_ret`이고 (플랜트 잠김(`jp3_plant_state` ∈ {locked_ext, locked_ret}) 또는 $p_{tr} > p^*_{last}$)(갇힌 몫) | $p_{tr}$ > $\max(\hat p+\delta_m,\ \text{수축 이동 모델})$ | 1 Pa | **판정**: 합 = 0 |
| `jp3c_fill_reads`, `jp3c_fill_breach_reads`, `jp3c_fill_max_excess_bar` | `carry_ret`이고 플랜트 이동 중이며 $p_{tr}\le p^*_{last}$(채움 몫) | 같음 | 1 Pa | 기록·FLAG(전제 ④, RET와 같은 뜻) |
| `jp3b_breach_reads` | `hold` | $p_{tr}$ > ④ | 1 Pa | FLAG |
| `jp3a_margin_used_reads` | `ext` + `carry_ext` | $p_{tr}$ > $\hat p$ | – | FLAG(개정 8 `margin_used_reads`와 같은 뜻) |
| `lock_ext_breach_over_tol_reads` | `lock`, 플랜트 신장 뒤 잠김 | $p_{tr}$ > ④ + 허용 | 0.6 kN/$A_{ann}$ | 436.8과 같음: FLAG 교차 점검, 판정은 VB T4h 재생 `over_0p6kN == 0`(③ rev 5 설정 재생) |
| `lock_ret_breach_reads` | `lock`, 플랜트 수축 뒤 잠김 | $p_{tr}$ > ④ | 1 Pa | 기록(새 창, 436.8 기준선 없음) |
| `ret_breach_reads`, `ret_max_excess_bar`(그 안의 `ret_trapped_*`·`ret_fill_*`) | `ret` | $p_{tr}$ > 수축 이동 모델 | 1 Pa | 기록·FLAG(전제 ④, 알려진 한계 435.7, 결정 146) |
| 옛 키(`breach_reads`, `locked_*`, `retract_*`) | 개정 8 상태 정의 | 개정 8 | – | 기록(436.8과 비교용) |

> "J-P3(436.9) = `jp3a_breach_reads` + `jp3b_breach_over_tol_reads` + `jp3c_breach_reads`의 판정 행(6.1절: VBJ·LSJ의 normal 등급 이하 행) 합이 0이면 통과, 0보다 크면 대체 경로 `불일치`(H-7)다. FLAG는 묶음 등급을 바꾸지 않고 공개한다."

- 436.8 기준선(`rs02_check_totals.json`, VB·LS 레코드 전부): 엄격 ④ 위반(`locked_breach_reads`) 14건(H-6 2, H-8 VB 12, 최소 간격 −0.89 bar)이 이미 있다. 0.6 kN 허용 초과는 0이다. 그래서 HOLD 판정에 같은 0.6 kN 허용을 쓴다. 엄격 비교를 판정으로 쓰면 ④ 전제의 알려진 여유 부족만으로 실패한다.
- `ret_breach_reads`는 436.8에서도 0이 아니다(h10 3, 계열 𝓕 1, 격자 2). 판정에 넣지 않는다.

**공중·가벼운 다리 수축의 J-P3c 노출 판단(유압 검토 1.6절, 반례 ⑩)**

- 사실: 플랜트 수축 목표는 경계식 함수 $p^*_{ret}(F)=\min\big((\max(p_{bA}, p_{h,thr}(F))A_h-F)/A_{ann},\ p_{relief}\big)$, $p_{h,thr}(F)=\big(F/A_{ann}+p_{cr}+p_{bA}(1-1/\psi)\big)/(\varphi-1/\psi)$(`moving_target_rod_pressure_Pa(RET, F)`, 유압 검토 10절)다. 헤드 문턱이 배압 $p_{bA}$(5 bar) 아래인 가벼운 다리(전방 $F$ ≤ 3.6 kN, 후방 $F$ ≤ 2.2 kN)에서만 헤드가 $p_{bA}$에 클립되어 $\varphi p_{bA}-F/A_{ann}$와 같다. 그보다 무거우면 이 닫힌 식은 참값보다 낮다($F$ 5 / 25 / 50 kN에서 전방 −4.0 / −61.7 / −133.9 bar, 후방 −9.7 / −80.0 / −167.9 bar). 그래서 구현은 닫힌 식이 아니라 함수를 부른다(닫힌 식이면 부하 다리의 채움 읽기가 판정으로 샌다). 모니터 수축 모델은 $13+p_h/3$ bar(클립 범위에서 $p_h=p_{bA}$이므로 14.67 bar)다. 아래 차는 모두 클립 범위 안의 값이다. 차는 전방 $F$ −2 / −1 / 0 kN에서 +8.2 / +5.6 / +2.9 bar, 후방 +6.8 / +3.6 / +0.5 bar다(control 재계산이 유압 검토 표와 같음). 전방 $F$ < 1.11 kN, 후방 $F$ < 0.14 kN이면 모델이 목표 아래다. 이것은 P3 전부터 있던 전제 ④의 공백이다. rev 4에서는 같은 읽기가 RET(FLAG)로 셌다(436.8 `retract_breach_reads` 6건이 이 꼴일 가능성이 있다. 확인은 per-read 기록이 생긴 뒤).
- rev 5에서 이 노출이 J-P3c로 들어오는 경로: 신장 뒤 공중에서 잠긴 다리($M$ 13.5 bar)를 수축하면, 플랜트(P1)는 수축 선 충전 뒤 열리고 시드·M2 (a)로 $p^*_{ret}$(공중 전방 20.3 bar)를 향해 오른다. 추적기 관문은 그보다 늦게 열리므로(엄격 순서) 그 사이 읽기가 `carry_ret`다. 비교값 $\max(\hat p+\delta_m, 14.67)$ ≈ 14.7 bar라서 위반이 난다(정상 목표 기준 최대 +5.6 bar, 첫 읽기는 유압 추정 약 +4 bar).
- **판단: 이 몫은 판정에서 빼고 RET와 같은 전제 ④ 기록으로 넘긴다.** 근거는 셋이다.
  1. CARRY_ret의 목적은 "잠금 동안 하중으로 갇힌 압력"을 수축 시작에서 덮는 것이다(R5-3·R5-4). 채움(목표 이하에서 오르는 중)은 수축 이동 모델이 목표의 상계인지, 즉 전제 ④의 문제다. 그 몫을 J-P3c로 판정하면 rev 5가 고친 공백이 아니라 rev 4부터 있던 RET 공백 때문에 실패한다. 결정 146(RET는 기록만)과도 어긋난다.
  2. 경계는 물리량으로 가른다(판 3, 유압 검토 10절). (가) 플랜트가 잠긴 `carry_ret` 읽기(P1이 해제를 막는 동안, `jp3_plant_state` 잠김)는 $p^*$와 무관하게 **갇힌 몫(판정)**이다. 분기 (a)·(c)는 이동 다리에만 있으므로 잠긴 압력을 $p^*$로 나누면 가벼운 다리에서 갇힌 압력의 ④ 실패가 판정에서 빠질 수 있다. (나) 플랜트가 이동 중이면, **플랜트 법칙이 마지막 내부 스텝에 쓴 목표** $p^*_{last}$(`_RodPressureLag.last_target_Pa`, 기록 `jp3_p_star_ret_Pa`)보다 $p_{tr}$이 높으면 갇힌 몫(판정), 같거나 낮으면 채움 몫(기록)이다. 읽기 시각의 $F$로 다시 계산하지 않는다(R12 RR 추적에서 차 ≤ 0.020 bar였으나 하중 울림이 크면 커질 수 있다). (a)는 $\min(p_{lag},\cdot)\le p^*$, (c)는 $\max(p_{lag},\cdot)\ge p^*$라서 $F$가 고정이면 $p_{tr}$은 $p^*$를 넘지 않는다. 수축 시드(P1 예외)는 잠긴 $p_r<p^*$에서 $p^*$보다 3.3 bar 이상 낮게 시작해 채움 쪽에 머문다. $p_r\ge p^*$이면 시드는 $\max(\cdot, p_r)$라서 갇힌 몫으로 이어진다(유압 검토 10절).
  3. $F_{min}$ 보호에는 영향이 없다: 노출 조건에서 대체 하한은 $p_hA_h-\text{모델}\cdot A_{ann}$ = $p_{bA}A_h-14.67\ \text{bar}\cdot A_{ann}$ = 전방 1.11 kN, 후방 0.14 kN 이하다. $F_{min}$ 9.415 kN보다 한참 낮아 "하한 ≥ $F_{min}$ + 여유"를 잘못 참으로 만들 수 없다. 낙관 크기는 전방 최대 3.1 kN($F$ −2 kN)이다.
- RET와의 연결: `jp3c_fill_*`과 `ret_fill_*`은 같은 뜻(전제 ④, 채움 몫)이고 판정서에는 합으로 적는다. `ret_trapped_*`(RET 중 갇힌 몫, 관문이 열린 뒤 느린 수축 감압)도 기록이다. 이것이 크면 수축 감압 상계(결정 146에서 만들지 않기로 한 것)를 다시 볼 근거가 된다.
- 경로 2 재계산: `ext`·`carry_ext`와 `hold`는 작용 명령과 $u_{hold}$만으로 다시 나눌 수 있다(rev 5에서 $\lvert u\rvert\le u_{hold}$ 읽기는 정의상 구간 안). `carry_ext`와 `ext`는 같은 비교를 쓰므로 관문 상태를 몰라도 J-P3a 집합이 같다. `carry_ret`는 관문 상태가 필요해 기록된 분류를 쓴다(재집계, R3-E3 선례로 공개). 비교값($\hat p+\delta_m$, ④)은 모니터 출력이라 두 경로 모두 기록에 기댄다.

### 6.3 기록 키(per-read·per-lock)

**`hydraulics_record.extend_bound_check`(rev 5 행, JSON 줄)**

| 키 | 뜻 |
|---|---|
| `rule_revision` | 5 |
| `jp3a_reads`, `jp3a_breach_reads`, `jp3a_margin_used_reads`, `jp3a_min_gap_bar`, `jp3a_min_gap_t_s`, `jp3a_first_breach_t_s` | 다리별 |
| `jp3a_by_plant_state` | {`moving_ext`, `moving_ret`, `locked_ext`, `locked_ret`}마다 `reads`·`breach_reads`(VB 48.8 s 꼴 노출을 따로 셈) |
| `jp3b_reads`, `jp3b_breach_reads`, `jp3b_breach_over_tol_reads`, `jp3b_min_gap_bar`, `jp3b_min_gap_t_s` | 다리별 |
| `jp3c_reads`, `jp3c_breach_reads`, `jp3c_min_gap_bar`, `jp3c_min_gap_t_s`, `jp3c_fill_reads`, `jp3c_fill_breach_reads`, `jp3c_fill_max_excess_bar` | 다리별 |
| `sensor_grade`, `jp3_judged_row` | 행 등급(ideal·normal·conservative·old_worst)과 판정 대상 여부(6.1절) |
| `lock_ext_*`(옛 `locked_*`와 같은 정의), `lock_ret_reads`, `lock_ret_breach_reads`, `ret_reads`, `ret_breach_reads`, `ret_max_excess_bar` | 다리별 |
| `class_reads` | 분류별 읽기 수 |
| `trace_excerpt`, `trace_excerpt_columns`, `trace_excerpt_truncated` | 간격 < 2 bar이거나 위반이거나 분류가 바뀐 읽기(앞뒤 2읽기 포함)의 행, 최대 2,000행: `t_s, leg, class, plant_state, u_m_s, used_bound_Pa, ext_bound_Pa, model_bound_Pa, p_tr_Pa, p_star_ret_Pa, head_read_Pa, gap_Pa, gate_open` |

**T4h npz(VBJ·LSJ·VBJ0·VBH·LSH, r79 계열은 `R79_T4H_DIR`)**: 전체 per-read 배열 `jp3_t_s`(n), `jp3_class`(n×4, int8), `jp3_plant_state`(n×4, int8), `jp3_u_m_s`, `jp3_ext_bound_Pa`, `jp3_model_bound_Pa`, `jp3_carry_bound_Pa`, `jp3_used_bound_Pa`, `jp3_p_tr_Pa`, `jp3_p_star_ret_Pa`(플랜트가 마지막 내부 스텝에 쓴 수축 목표 `last_target_Pa`, 읽기 시각 $F$로 다시 계산하지 않음; 이동 다리만 유효, 잠긴 다리는 NaN), `jp3_gate_open`(bool), `jp3_gate_fill_m`(n×4). 이로써 간격을 역산하지 않아도 된다(원인 보고서 4절 요구).

**per-lock `hydraulics_record.lock_log`(플랜트, 모든 잠금)**: 행 `t_lock_s, leg, direction, p_tr_before_Pa, p_r0_Pa, Gr_lock_N, p_tr_after_Pa, dp_tr_step_Pa, dp_h_step_Pa, t_release_s, release_cause(command|gate), gate_wait_s, dF_lock_N, dp_tr_lock_Pa, monitor_class_at_lock, monitor_stretch_open`. 집계 `relock_count`, `relock_step_over_1bar_count`, `max_abs_dp_tr_step_bar`. 행 상한은 `MAX_LOGGED_LOCK_EVENTS`(2,000)와 같다.

**per-stretch `two_pressure.extend_start_record.stretch_log`(모니터, 모든 다리)**: 행 `leg, t_open_s, t_close_s, close_reason(above_hold|run_end), hold_periods, retract_hold_candidates, model_bound_close_Pa, seed_before_Pa, seed_after_Pa, carry_periods, gate_open_t_s`. 상한 2,000행.

### 6.4 R16-15a와 플랜트 산물 한계(규칙 문장 초안)

> "VBJ·LSJ 행의 제어기 로드 판독은 플랜트 M2 참값이다(P4). 그래서 436.8 R16-15a의 판독 한계(잠김 법칙 값 판독, D3 오탐, T4h 재생 불완전)는 이 행에 적용되지 않는다. J-P3의 $p_{tr}$은 P1(선 충전 해제 관문)·P2(잠금 앵커 연속)·P3(네 분기 유량 상한)을 켠 플랜트 값이다. P1은 M1c 선 충전 식과 값(단위 기준 미달 참고값, Q-M9·V-6·L-2·H-3)에 기대므로, J-P3 통과는 'M1c 값 가정 아래 통과'로 적는다. P1은 M1c 출력 가운데 체크 열림 판정과 수축 열림의 M2 시드만 쓴다(시드는 예외로 남김, meta `output_exceptions`). 끈 출력의 방향은 다음과 같다: 신장 로드 체크 먼저 열림의 감압을 무시해 $p_{tr}$이 높게 나온다(보수). 수축 헤드 방출·크리프 이동이 없어 부하 다리 수축 시작의 하중 전이 과도가 작게 나온다(압력 판정과 무관). P1~P4를 끈 행(VB·LS·VBH·LSH)의 J-P3 기록에는 436.8 판정서 9.9절의 플랜트 산물(미세 명령 해제, 재잠김 앵커 계단, 무유량 감압)이 들어 있으므로 판정에 쓰지 않는다. 선 충전 관문 여유 $e_h$ 9 bar는 normal 등급 판독 오차와 주기 안 헤드 혹 3.6 bar(관찰값 가정)에 기대므로, conservative·old_worst 등급 행의 J-P3는 기록만 한다. 주기 안 헤드 극값(반례 ⑨), 수축 이동 중 추정(전제 ④: RET 전체와 수축 CARRY의 채움 몫, 가벼운·공중 다리에서 최대 약 +8 bar, 그때 대체 하한 ≤ 1.2 kN로 $F_{min}$ 판정에는 영향 없음)은 남는 한계로 공개한다."

## 7. 436.9 재실행 범위와 예상 시간

- VB·LS 줄은 모두 다시 돌린다(P1·P2·P3·P4가 모든 VB·LS 명령 해시를 바꾼다). V0 줄은 바뀌는 코드 경로가 없으므로 저장 결과를 쓴다(표본 해시 대조, R3-E1 선례).
- 시간은 436.8 R2 러너 기록(`verif_matrix/v5_resume_4368/run_b9f5707/logs/run_harness.out.log`, identity 파일; 모두 mask `0xFF0000` = E코어 8개, BelowNormal)의 벽시계다. `rs01_scope_census.py`로 줄 수를 셌다.

| 묶음 | 436.9 설정 | 줄(VB·LS 쪽) | R2 벽시계(8 E) [s] | 비고 |
|---|---|---|---|---|
| H-1 D-1 | VBJ | 434 | 약 5,800 | `h1_d1` 8,182 s는 VB+V0. VB 몫 0.71(H-8 VB/V0 비)로 나눔(추정) |
| H-3 U-3 | VBJ | 1,114(slope 110, h6 26, h9 24, g6 116, g8 516, p3b 171, x426b 84, C 34, D 33) | 10,779 | 두 경로 도구 보완(재판정-1)과 함께 |
| H-4 U-6 | VBJ(C2·ABL·IND) + IND_LAS | `u6_*` 4파일 | 12,994 | ABL·IND는 ③이 없어 플랜트만 바뀜 |
| H-6 dg3 | VBJ | 135 | 2,063 | Dg-3 짝(T-JR-12)과 같은 행. J-P3 판정은 L2 1키, L3 134키는 기록(결정 147) |
| H-7 dg3 끔 | VBJ0 | 135 | 1,913 | |
| H-8 잡음 | VBJ | 1,503 + seedext 50 | 20,899 + 726 | J-P3 판정은 normal 이하 등급 행만, L3(conservative) 행은 기록(결정 147) |
| H-9 계열 𝓕 | VBJ | 32 | 1,357 | |
| H-9 격자 | VBJ | 768 run(4파일) | 3,190 | |
| H-10 | VBJ, LSJ1~4 | 426(VB 138 + LS 288; V0 10·V3 4는 재사용) | 6,779(main 6,036 + u9_vb 399 + item8 111 + overlap 233) | U-9 VB 28줄 포함 |
| H-12 | VBJ | 3 | 약 300(추정) | u3 g8 G-6 3키 T4h |
| **합** | | **약 4,600줄 + U-6** | **약 66,800 s(18.6 h)** | 148 E코어·h |
| 본 실행 전 진단 | VBH, VBJ0, A~F 사례, T8 20×2 | 약 135 + 40 + 31 | 약 3,000 | T-JR-10~15 |

- 비용 가정: P1 선 상태 기계(1 ms 묶음 × 4다리, `retract_dead` 포함), rev 5 관문 소단계, per-read 추적 기록이 더해진다. **+25 %(가정, 실측 없음)** → 약 185 E코어·h ≈ 109 P코어·h(E/P 1.7).
- 벽시계 추정: P 8 + E 12를 모두 쓰면(E 환산 약 25.6) 약 **7 h**, Chrono C-8a가 P코어를 나눠 쓰면 **9~12 h**, E 8코어만이면 약 **23 h**다. 배치표·실행 명령은 compute-scheduler-expert, 30분이 넘으므로 감시(long-running-task-monitor)와 예약이 필요하다.
- 비용을 먼저 재는 방법: T-JR-12의 VBJ 135행을 먼저 돌려 행당 시간을 H-6(2,063 s/135행 @ 8 E)과 비교하고, 위 +25 %를 바꾼다.
- Chrono VB 행은 이 표에 없다. 결정 146대로 rev 5 제어기만 켜고 L2b 플랜트는 그대로 둔다(T4 재생 포함, 행 범위는 Chrono 판정서 11절 목록과 함께 정한다).

**436.9 진행 순서(결정 96 자동 범위)**: 구현(python-expert) → T-JR-01~09 → 사례 재생 A~F(예측 고정 뒤) → T-JR-10~15 → 436.9 규칙 봉인(이 6절 초안 + 하네스 판정서 10절 재판정-1·2 등. J-P3는 0 건수 판정이라 새 통계 문턱이 없다. 다른 rev26 항목에 비율 문턱이 생기면 stats-design-expert 검토) → verif-protocol-auditor 실행 전 감사 → integrity → 병합 → 배치표 → 본 실행 → 두 경로 판정 → K-R. 멈춤 조건은 결정 96 그대로이고, 5.3·5.4절 예측 불일치를 "허용 범위 밖 변경"으로 더한다. VBH 진단 묶음은 본 실행 전에 돌린다(결정 146).

## 8. 가정

| 가정 | 값 | 쓰임·근거 |
|---|---|---|
| $u_{hold}$ | $0.01\,v_{max}$ = 0.20924 mm/s | 결정 144·146, 허용 0.5~1.2 % $v_{max}$(유압 검토 2.2절, P1 VN 값에 기댐) |
| 수축 후보 | $\max(\text{수축 이동 모델}, p_{ret})$, ψ ≥ 2.5 | 2.3절 |
| 관문 값 | 2.4절 표(P1 공칭 + $\kappa_x$ 0.8, $e_h$ 9 bar, 수축 need $F_{band}$ 0·$p_r$ $p_{floor}$, ψ$p_B$ 항 제외) | 결정 147, 유압 검토 3절 |
| P1 회로 | VN, volume_scale 1.0, $c_v$ 0.02 | LC와 함께 쓸 수 있는 회로(D-6) |
| P3 계수 | (c) A→T를 $p_{bA}$ 5 bar에 맞춤($b_{T,ret}$ 1.826), (d) 쓸기 유량 상한. $b_T$ 1, $\Delta p_c$ 10 bar, $p_T$ 2 bar | 유압 검토 1절(고정 하중·질량 없는 피스톤 유도, Q-M1·V-1 대기) |
| 주기 안 헤드 혹 | 3.6 bar | $e_h$ 9 bar의 근거(관찰값, 증명된 상계 아님) |
| 사례 예측 | 2.4절·5.3절 값(입력 $p_h$ 35.2 bar, 잠긴 $p_r$ 53.9 bar, ④ 70 bar) | `rs03_expected_49p1.json`, hydraulics 4절 |
| 재실행 비용 | +25 %, E/P 1.7 | 7절 |
| J-P3b 허용 | 0.6 kN/$A_{ann}$ | T4h 허용(개정 8 9절)과 같음, 436.8 기준선 |
| 시드 | 속성 시험 20261107(기존), 20261116(새) | 5.2절 |

## 9. 확인 필요

**판 1의 1~10은 결정 146·147로 닫았다.**

| # | 항목 | 결정 |
|---|---|---|
| 1 | R5-3 수축 쪽 시드 | 넣음(146) |
| 2 | R5-4 선 충전 관문 | 넣음(146). 값은 $e_h$ 9 bar, 수축 need $F_{band}$ 0·$p_r$ $p_{floor}$(147) |
| 3 | R5-5 미세 명령에서 구간 열기 | 넣음(146) |
| 4 | 보조 규칙 | (i)(146) |
| 5 | P4 판정 정의 | 켬(146) |
| 6 | J-P3b 허용 | 0.6 kN/$A_{ann}$(146) |
| 7 | $u_{hold}$ | 0.01 $v_{max}$(146), 허용 상한 1.2 %(유압 검토) |
| 8 | Chrono VB 행 | rev 5 제어기만(146) |
| 9 | RET | 기록만(146) |
| 10 | VBH | 본 실행 전에 돌림(146) |
| – | P1 수축 시드 | 남기고 예외로 기록(147) |
| – | J-P3 판정 등급 | normal 등급 행만, conservative·old_worst는 기록(147) |

**새 확인 필요(이번 갱신에서 생김)**

11. **"normal 등급 행만"의 범위**: 이상 센서 행(H-1·H-9·H-10처럼 하네스 판독 그대로, r79 L0·L1)도 판정에 넣는다고 읽었다. 이상 센서는 오차가 0이라 $e_h$ 9 bar의 전제를 더 잘 만족한다. 이상 센서 행을 빼면 이번 J-P3 사례(H-9 격자·H-10)가 판정 밖으로 나간다. **권고: 이상 + normal을 판정**(6.1절 문장). 다르게 읽어야 하면 6.1절만 고친다.
12. **J-P3c를 갇힌 몫(판정)과 채움 몫(기록)으로 나누기**(6.2절 판단): 가벼운·공중 다리 수축의 노출(최대 약 +5.6~8 bar)은 rev 4부터 있던 전제 ④(수축 모델 < 수축 목표)의 공백이고, 그때 대체 하한은 ≤ 1.2 kN이라 $F_{min}$ 판정에 닿지 않는다. 판정 집합을 플랜트 잠김 여부와 $p_{tr}$ 대 $p^*_{last}$로 가르면 결정 146(RET 기록만)과 맞는다. **권고: 나눈다.** 나누지 않으면 J-P3c가 RET 공백 때문에 H-7로 갈 수 있다.

## 10. 핸드오프

| 대상 | 일 |
|---|---|
| python-expert | 4절 구현, 5절 시험 T-JR-01~16과 사례 재생 A~F. 갱신판 차이: 관문 상수($e_h$ 9 bar, need $F_{band}$ 0·$p_r$ $p_{floor}$), `CheckOpenGate` 수축 시드 예외와 meta, P2 무릎의 `_check_delay_inputs` 적용, P3 `flow_limited_r6` 식과 T-JR-08 기준값(유압 검토 1.4·1.5·5절, 참조 구현 `hr01_p3_flow_law.py`), J-P3c 갇힌·채움 분리와 `p_star_ret_Pa` 기록 열, 행 등급 키 `sensor_grade`·`jp3_judged_row`. 4.3절 태그 감사 목록 |
| hydraulics-expert | 닫힘: 6.2절 경계는 `hydraulics_remedy_review.md` 10절(조건부 맞음 → 판 3에서 세 곳 정정)로 확인됨 |
| verif-protocol-auditor | 436.9 봉인 전·실행 전 감사: 태그 접미사 조합(`_P3H` + `_LAS`·`_K1`), 래퍼·프리셋 이중 적용, 5.3·5.4절 예측의 결과 전 고정(판 2 sha), $e_h$·$F_{band}$·$p_r$ 하한이 규칙 문장과 코드 상수로 같은지, P1 출력 예외 meta, 행 등급 판별(등급 meta 없는 줄 처리), V0 재사용 표본 해시 |
| compute-scheduler-expert | 7절 표로 배치표(VBJ 135행 비용 측정 먼저, VBH 진단 먼저) |
| stats-design-expert | J-P3는 0 건수라 필요 없음. rev26의 다른 항목에 비율 문턱이 생기면 그때 |
## 11. 수행한 작업

| 스크립트(이 폴더) | 환경 | 내용 | 출력 |
|---|---|---|---|
| `rs01_scope_census.py` | dynamics-dev(`conda run -n dynamics-dev python -I -B`) | `resume_k1` identity의 벽시계·mask, 결과 줄의 설정·태그 수 | 콘솔(7절 표) |
| `rs02_check_totals.py` | 같음 | 436.8 VB·LS 레코드의 `extend_bound_check` 키 합(격자 run 단위 포함) | `rs02_check_totals.json` |
| `rs03_expected_49p1.py` | 같음 | 49.0 → 49.1 s의 플랜트 P1 열림(M1c), 추적기 관문, $\hat p$·$p_{tr}$ 감압. 저장소 함수(경로 A)와 닫힌 식(경로 B) | `rs03_expected_49p1.json` |

- 읽은 코드(읽기만): `extend_start_bound.py` 전체, `two_pressure.py` 2268~2650·2785~2880행, `harness_hydraulics.py` 전체, `s8_g4_rodside_check.py` 73~155행, `check_open_delay.py` 전체, `rod_release.py` 81~141행, `v5_options.py` 전체, `run_v5.py` 72~264행, `lock_window_alignment.py` 머리, `r79_sensor_screen.py` 135~272행, `r64_g4_closed_loop.py` 192~201행.
- 판 2: `hydraulics_remedy_review.md`(hydraulics-expert, `hr01~hr06`)를 읽었다. 관문 148 ms와 가벼운 다리 $p^*_{ret}$ − 모델 값은 `rs03_expected_49p1.hand_fill_time`을 import한 `-c` 한 줄로 다시 계산해 유압 검토 값과 맞췄다(147.95 ms; 전방 +8.24 / +5.59 / +2.94 bar). 436.9 실행·시험 출력은 보지 않았다.
- Julia 교차 검증은 하지 않았다. 이 작업은 설계 명세이고, 수치는 사례 예측용 보조 계산이다. 2.4절 표의 두 경로(저장소 함수와 닫힌 식)로 $C_r$ 값만 대조했다(상대차 < 0.1 %).

## 12. 기호

| 기호 | 뜻 | 단위 |
|---|---|---|
| $u_k$, $u_{hold}$ | 작용 명령, hold 문턱($0.01v_{max}$) | mm/s |
| $\hat p$, $\delta_m$ | ③ 추적기 로드 압력 상계, 여유 0.5 bar | bar |
| ④, ④$^c$ | 모니터 잠김 모델 상계 $\max_j[M_j+R_{ub}(p_{h,j}-p_h)^+]$, 운반 후보로 계산한 값 | bar |
| ⑤ | 판독 상계 | bar |
| $M_j$, $p_{h,j}$, $R_{ub}$ | 잠금 시작 후보, 그때 헤드, 상계 비 | bar, bar, – |
| $p_{tr}$ | 플랜트 로드 압력 참값(이동: M2 지연값, 잠김: $p_{r0}-G_r/A_{ann}$) | bar |
| $p_{r0}$, $G_r$, $G_{r,lock}$, $p_{lag}$, $p_{floor}$ | 잠금 앵커, 로드 스프링 힘, 잠금 순간 값, M2 지연값, 바닥(0.1 bar abs) | bar, N, N, bar, bar |
| $\hat x$, $\hat p_A$, $\hat d$ | 추적기 선 충전 상태(행정 단위), 선 압력, 중립 배수 속도 | m, bar, m/s |
| $V_{line}$, $\beta_{hose}$, $\psi$, $p_{cr}$, $p_T$ | 라인 체적, 호스 체적탄성, 파일럿 비, 크래킹, 탱크 | cm³, GPa, –, bar, bar |
| $K_n$, $g$, $f_n$, $c_v$, $\Delta p_{comp}$ | 중립 누설 계수, 스풀 게이트, 누설 비, 벤트 닫힘 비, 보상기 차압 | m³/(s·Pa^0.5), –, –, –, bar |
| $\kappa_x$, $e_h$, $F_{band}$ | 속도 하한 비 0.8, 헤드 판독 여유, 마찰 띠 | –, bar, kN |
| $A_h$, $A_{ann}$ | 헤드 면적, 로드측 고리 면적(전방 1.327×10⁻²·3.770×10⁻³, 후방 9.503×10⁻³·3.142×10⁻³) | m² |
| $C_r$, $\bar C_r$ | 플랜트·추적기 로드측 컴플라이언스 | m³/Pa |
| $t_c$, $u_{ol}$ | LC 닫힘 지연, 겹침 끝 속도 | s, mm/s |
