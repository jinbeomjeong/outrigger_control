# 436.9 J-P3 보완 설계 명세 — ③ revision 5(미세 명령 잠금 유지)와 플랜트 옵션 P1~P4

작성: control-expert, 2026-11-16. 명세만 쓴다. 저장소 코드(`03_src`, `04_scripts`)는 고치지 않았다. 이 폴더에는 이 문서와 확인 계산 스크립트 `rs01~rs03`(읽기 전용, 결과 JSON 포함)만 더했다. 구현은 python-expert가 한다.

- 규약: 음되먹임, 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1. 작용 명령 $u_k$ = 직전 읽기의 출력이고, 증분 제한 뒤의 값이다. ③ 추적기 소단계는 $\Delta t$ = 1 ms, 하네스 플랜트 내부 스텝은 5×10⁻⁴ s다.
- 단위: 압력 bar(게이지), 힘 kN(실린더 순 힘), 속도 mm/s(+ = 신장), 체적 cm³. 다리 순서는 FL, FR, RL, RR(0~3)이다.
- 근거: `jp3_cause_report.md`(앞 분석), `hydraulics_review.md`(H1~H4, 7절 P1~P4, 8절 $u_{hold}$), 하네스 판정서 `verif_matrix/v5_resume_4368_harness_judgement.md` 9.6·9.9절, ③ 명세 `06_analysis/03_hydraulic/coupled/v5/p3_extend_start_spec.md` 3·4·11·12절, 제어 명세 `s6_control_spec.md` 435절.
- 적용한 사용자 결정: 144(제어기 안 1, $u_{hold}$ 0.21 mm/s = 1 % $v_{max}$, 수축 hold 보조 규칙, P1~P4)와 145(새 옵션·새 태그로 분리, 기존 기본값·해시 보존, 기본 켬은 436.9 판정 뒤, 436.9는 결정 96 자동 범위), 146(첫 판 확인 필요 1~10 모두 권고대로), 147(관문 $e_h$ 9 bar, 수축 need $F_{band}$ 0, $p_r$ 하한 $p_{floor}$, P1 수축 시드는 남기되 예외로 기록, J-P3 판정은 normal 등급 행만).
- 갱신판 근거: hydraulics-expert `hydraulics_remedy_review.md`(P3 식 (a)~(d), P1 출력 끔 목록 검토, R5-4 관문 값 검토, $u_{hold}$ 상한 1.2 %).
- 판 4 근거: 구현 `221456d`(worktree `z4369-jp3`)의 사례 재생과 control-expert 검토 `jp3_impl_review.md`. 적용한 사용자 결정은 152다.
  - 불일치는 예측 전제 오류·표기 누락·예시 값으로 공개하고 결정 96 멈춤을 푼다.
  - R5-6 상속을 채택하고, `fresh_stretch`는 시험 전용으로 둔다.
  - ⑪b는 안 A(R5-7)로 처리한다.
  - 시간 노화 규칙은 넣지 않는다. T-JR-12를 먼저 재고, 실패하면 C1~C3을 판 5에 넣는다.
  - 순서는 판 4 → 재구현 → 사례 재생 A~F → T-JR-10~15 → j9_main이다. 관문을 통과하면 자동으로 진행한다.
- 판 4.1 근거: hydraulics-expert `hydraulics_remedy_review.md` 11절(⑪b 크기, 안 A 조건 A1~A5, 시드 운전점, need 출처; 스크립트 `hr11/`). 판 4의 P4-1~P4-6 원문은 고치지 않았다. 바뀐 것은 P4-7 이후로 덧붙였다(5.7절).
- **판 3의 고정 예측(5.3·5.4절) 원문은 고치지 않았다.** 판 4의 사후 정정은 표지 `[판 4 사후 정정 표지]`를 붙인 덧붙임뿐이다. 새 예측은 5.7절에 결과 전에 고정한다.

### 갱신 이력

| 판 | 날짜 | 바뀐 곳(요지) |
|---|---|---|
| 1 | 2026-11-16 | 첫 판 |
| 4a | 2026-11-16(사례 재생 전) | 판 4.1(sha256 `f2f7dfad…`) 위에 덧붙인 판이다. 판 4 실행 전 감사(차단 2 / 수정 10 / 기록 9, `audit-jp3r4\report.md`)와 사용자 결정 153을 반영했다. 13절에 모두 모았다: 기준선 고정 자리(B1), 판정 행 0 = 판정 불가(B2), 반례 갈래 = `fresh_stretch` + `model_only`(M1), P4-3 범위(M2), 자동 진행 범위(M3), 정체성 기록(M4), 시험 상수(M5), T-JR-12 판정 문장(M6), 레코드 skip(M7), 사례 F(M8), 부록 A 정정본(M9), 예측 분류(R1), 옛 기록 재생 거부(R7), 재구현 목록 J4a. 판 4·4.1 본문과 P4-1~P4-9 원문은 고치지 않았다 |
| 4.1 | 2026-11-16 | 유압 검토 11절 반영. 2.10절 R5-7에 덮임 조건 A1~A5를 문장으로 넣음. 적용 범위를 "직전 이동 주기가 수축인 모든 새 구간(LOCK·HOLD에서 열림, 잠금·신장 반전 어디서 시작한 수축이든)"으로 명시함(A5). 판 4의 적용 지점이 이미 이 범위임을 확인함. 2.7절 ⑪b 크기를 P1 플랜트 물리 값으로 보충(전방 최대 +27.4 bar·10.3 kN, $p_{r0}\le$ 60 bar). 2.4절 대가 문장 교체(+0.24 s / +0.27 s). T-JR-04 사례 ⑪b-P1, T-JR-05 (l)(m) 추가. T-JR-12 기록 열 2개 추가. 5.6절 항목 3개 추가. 5.7절 P4-7~P4-9 덧붙임 |
| 4 | 2026-11-16 | 결정 152. 2.1절 CARRY 끝 규칙을 R5-6(관문이 닫힌 운반의 후보 상속, 합집합)으로 바꿈. R5-7(수축 뒤 잠금 시작 후보에 $\hat p+\delta_m$, ⑪b 안 A) 추가. 2.7절 반례 ⑪·⑪b. 2.4절 수축 need 비용 수치 정정(1.24 → 2.32 mm). 4.1절 구현 행과 4.5절 재구현 목록. 5.2절 T-JR-03 기준(149 ms, 허용 0)·T-JR-06 주석(160.16 ms)·T-JR-04 사례 ⑪·⑪b·T-JR-05 (h)~(k)·T-JR-18. 5.3절 C·D 행에 사후 정정 표지(원문 그대로). 5.6절 판 3 예측 사후 대조. 5.7절 새 사전 예측. 6.3절 기록 열(지배 후보 출처·나이, 시드 사건 행). 부록 A 판정서 공개 문장 |
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
| 판 4 추가(결정 152) | **R5-6**: 관문이 한 번도 열리지 않은 운반이 LOCK·HOLD로 끝나면, 새 구간은 창 후보에 운반 후보를 더한 합집합을 쓴다(반례 ⑪). **R5-7**: 수축 뒤(RET·CARRY_ret 뒤) 잠금 시작 후보와 그 주기의 이동 시작값을 $\max(13+p_h/3,\ p_{ret},\ \hat p+\delta_m)$로 한다(반례 ⑪b). 둘 다 상계·기록만 바꾼다(T8 근거 2.8절 그대로) |

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
- CARRY 다음에 $\lvert u\rvert\le u_{hold}$가 오면 새 구간을 연다(새 창·새 후보). 운반 상태는 지운다. $\hat p$는 감압을 세지 않았으므로 끈끈한 값이 남는다. **(판 4: 그 운반에서 관문이 한 번도 열리지 않았으면 R5-6을 적용해 운반 후보를 새 구간에 더한다. 판 3의 "새 후보만"은 반례 ⑪로 깨져 `fresh_stretch` 시험 상수로만 남긴다. 2.9절)**
- (판 4) 수축 뒤 잠금 시작 후보는 R5-7을 따른다(2.10절).
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
  - **(판 4 정정)** 위 0.92·1.24 mm는 플랜트 공칭 입력($\beta$ 1.0 GPa, $L_{0r}=L_{0h}$ 0.05 m, $p_r$ 2 bar, $F_{band}$ 8 / 0 kN, $e_h$ 없음)으로 계산한 값이다(`retract_dead` 재계산 0.920 / 1.235 mm, 검토 `cr08`).
  - 이 절의 보수 입력($\beta$ 0.69, $L_{0r}$ 0.10, $L_{0h}$ 0.08, $p_{floor}$, $F_{band}$ 0, $p_h^{ub}=p_h+e_h$)으로는 전방 $p_h$ 77 bar에서 **2.315 mm**(1.87배), 후방 2.506 mm다.
  - ~~그래서 4.71 mm/s에서 수축 CARRY는 판 1 대비 약 +0.37 s다(밸브 지연 제외 추정).~~ (판 4.1에서 지움. 0.37 s는 need$^{ub}$와 플랜트 공칭 need의 차였고, 판 1 관문과의 차가 아니었다.) 구현은 이 절의 문장(보수 입력)대로이고, 관문을 늦추는 쪽이라 건전성 영향은 없다. 비용은 T-JR-12에서 잰다.
  - 1.24 mm의 출처는 유압 검토 3.4절 비용 칸의 표기 오류였다(유압 검토 11.3절).
- **대가(판 4.1, 위 대가 문장을 대신함; 유압 검토 11.3절)**: 부하 다리의 수축 need$^{ub}$가 는다.
  - 전방($p_h$ 판독 77 bar, $s$ 0.395 m): 판 1 관문 1.43 mm → 2.32 mm. 4.71 mm/s에서 관문 열림이 **+0.24 s** 늦어진다.
  - 후방: 1.49 → 2.51 mm, **+0.27 s**.
  - 같은 점의 플랜트 공칭 need는 0.92 mm($F_{band}$ 8 kN)~1.24 mm($F_{band}$ 0)다. 그래서 4.71 mm/s에서 관문은 플랜트 해제보다 약 0.35~0.46 s 늦게 연다. 그만큼 J-P3c 판정 창이 길어진다.
  - 갇힌 잠금에서는 플랜트 need가 라인 충전분뿐이라 창이 더 길다(4.71 mm/s에서 0.11~0.72 s, 0.5 mm/s에서 최대 약 4.9 s; 유압 검토 11.1절).
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
| (판 4) 관문이 닫힌 운반 뒤 LOCK·HOLD | – | ④∨⑤, 후보 = 창 후보 ∪ 운반 후보(R5-6) |
| (판 4) 수축(RET·CARRY_ret) 뒤 LOCK·HOLD | 창 후보 $\max(13+p_h/3, p_{ret})$ | 창 후보 $\max(13+p_h/3, p_{ret}, \hat p+\delta_m)$(R5-7) |

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
| ⑪(판 4) | 관문이 한 번도 열리지 않은 운반(신장·수축)이 LOCK·HOLD로 끝남. 플랜트는 예전 잠금 그대로일 수 있는데, 판 3 2.1절은 새 구간에 창 후보(이동 뒤 잠금 가정)만 둔다 | (해당 없음) | 판 3 rev 5에서 깨짐: 사례 E LSJ4 FL 49.0 s, ④ 35.3 bar < $p_{tr}$ 46.0 bar, −10.67 bar(구현자 보고) | **R5-6**(2.9절) | T-JR-05 (h)(i), T-JR-04 사례 ⑪, 5.7절 예측 P4-5 |
| ⑪b(판 4) | 관문이 **열린** 수축(RET) 뒤 짧은 시간 안의 LOCK·HOLD. P3 (c)로 갇힌 압력이 남는데(후방 $F$ 14.8 kN, $p_r$ 59.9 bar에서 0.3 mm/s 감압 약 14 bar/s), 창 후보는 수축 모델 $13+p_h/3$뿐이다. HOLD는 J-P3b 판정 대상이고, $F_{lb}$가 $F_{min}$ 쪽으로 낙관이다(참 힘 5 kN 꼴에서 $F_{lb}$ 16.6 kN) | 같은 공백(옛 플랜트는 빠른 감압이라 드묾) | 판 3 rev 5에서 깨질 수 있음: 비교 원리가 허용하는 최악(플랜트가 관문 열림 소단계에 해제) + RET 0.2 s @ 0.3 mm/s + HOLD에서 간격 약 −33 bar(검토 `cr09`). 221456d 사례 재생에서는 노출 0(수축 뒤 hold 최소 간격 +9.7 bar).<br>**(판 4.1, 유압 검토 11.1절)** 위 수치는 플랜트가 관문 열림 소단계에 풀린다고 둔 시험 훅(비교 원리의 최악)의 값이다. P1 플랜트에서는 관문 창(플랜트 해제 → 관문 열림, 0.045~7.8 s) 동안 P3 (c)가 감압한다. 그래서 물리 크기는 **가벼운 다리에서만** 크다: 첫 HOLD 읽기 초과(갇힌 압력 − 수축 모델) 최대 전방 +27.4 bar(10.3 kN)·후방 +22.2 bar(7.0 kN)($p_{r0}\le$ 60 bar). 격자 끝($p_{r0}$ 120 bar)에서는 +53.7 bar(20.2 kN)다. 부하 다리(전방 $F\ge$ 25, 후방 $F\ge$ 15 kN, $p_{r0}\le$ 60 bar)는 0 이하다. $F_{true}<F_{min}$인 480건 가운데 204건에서 수축 모델만으로 $F_{lb}\ge F_{min}$이 된다. VBJ RR 예($F$ 14.8 kN, $p_r$ 59.9 bar)는 관문이 열리기 전에 $p^*$ 12.2 bar까지 내려가 ⑪b 시점의 크기가 0이다. 검토 2.3절의 "11 kN 낙관"은 **RET 시작 때의 크기**다 | **R5-7**(2.10절, 결정 152 안 A, 조건 A1~A5) | T-JR-04 사례 ⑪b·⑪b-P1, T-JR-05 (j)~(m) |

### 2.8 T8 근거(대체가 없는 실행의 명령 불변)

- rev 5가 바꾸는 상태는 `_LockStretch`·`_CarryState`, 추적기 $\hat p$·$\hat u_v$·$\hat x$, `_LegWatch.rod_estimate_Pa`다. 앞 둘은 대체 다리의 힘 하한(`_fallback_forces`)과 기록(`_count_tension`, `fallback_lock_log`, `extend_start_record`)에만 들어간다.
- D1~D3 진단, 출력, 사건은 이 상태를 읽지 않는다(`two_pressure.py` 2268~2280·2850~2880행 확인). 그래서 대체 다리가 없는 실행의 명령은 rev 4와 비트 동일해야 한다. 바뀌는 것은 meta의 끝 상태값(`fallback_rod_estimate_Pa`)뿐이다(개정 10 조건 A·B·C 선례).
- (판 4) R5-6·R5-7이 바꾸는 것도 `_LockStretch` 후보와 추적기 $\hat p$뿐이다. 그래서 위 논리가 그대로 성립한다. 대체 다리가 없는 실행의 명령 해시는 `221456d`와 같아야 한다(5.7절 P4-1).

### 2.9 R5-6: 관문이 닫힌 운반의 후보 상속(판 4, 결정 152)

**규칙**: 다리 $i$의 운반(CARRY_ext·CARRY_ret가 이어진 주기들)이 LOCK 또는 HOLD 주기로 끝나고, 그 운반에서 추적기 관문이 **한 번도 열리지 않았으면**, 그 주기에 여는 새 구간의 후보 목록은 다음 합집합으로 한다.
- 창 후보(10.4 ②, R5-7 포함)
- 운반 상태의 후보 전부(`_CarryState.candidates`: 운반 시작에 복사한 앞 구간 후보 + 운반 중 R5-2 수축 후보)
- `stroke_window_max_m` = 둘의 최댓값($R_{ub}$ 보수)
- 기록: `inherited_candidates` = 상속한 후보 수(stretch_log), `carry_end_rule` = `inherit_when_gate_shut`(meta)

**근거**
- 비교 원리는 한쪽 함의만 준다: 관문 열림 ⇒ 플랜트 해제. 관문이 닫힌 채면 해제 여부를 모르므로 잠금이 이어졌다고 가정한다. 그때 압력은 예전 후보의 잠김 법칙 $M_j+R_{ub}(p_{h,j}-p_h)^+$를 따른다. 창 후보는 "이동 뒤 창 안의 잠금"만 덮는다.
- P1(VN)에서 $u_{hold}$ 이하 명령으로는 선 충전이 안 된다(2.2절). 그래서 실기에서도 잠금이 이어진다.
- 합집합이므로, 플랜트가 실제로 풀렸다가 창 안에서 다시 잠긴 경우(옛 플랜트)도 창 후보가 덮는다.
- 관문이 열린 운반은 상속하지 않는다. 플랜트가 이미 풀렸고, 신장이면 $\hat p$가, 수축이면 R5-7이 덮는다.

**`fresh_stretch`(판 3 2.1절 문장)**: 반례 ⑪로 비건전하다. 설정·프리셋·CLI에서 고를 수 없게 하고, 시험 전용 모듈 상수(`ALLOW_FRESH_STRETCH_FOR_TEST`, 기본 False, `ALLOW_GATE_WITH_REV4_FOR_TEST` 선례)로만 켠다.

**비용**: 관문이 열리지 않는 긴 운반(높은 헤드의 수축 need$^{ub}$ 2.8~3.1 mm 대 운반 채움 1.6 mm, VBH RR 41.5~42.3 s)이 끈끈한 값을 다음 구간으로 넘긴다. 이는 검토 3.3절의 $M_j$ 사슬의 한 고리다. 크기는 T-JR-12에서 잰다. 실패하면 판 5 완화안 C1(해제 목격)으로 이 고리를 끊는다(9절).

### 2.10 R5-7: 수축 뒤 잠금 시작 후보에 $\hat p+\delta_m$(판 4, 결정 152 안 A)

**규칙**(rev 5, ③ 추적기가 있을 때)
- 수축 방향 잠금 시작 모델을 $M^{ret}(p_h)=\max\big(13+p_h/3\ \text{bar},\ p_{ret,i},\ \hat p_i+\delta_m\big)$로 한다.
- 쓰는 곳은 둘이다.
  1. RET·CARRY_ret 주기의 이동 시작값(`moving_starts`, lookback 최대의 재료)
  2. 마지막 이동 방향이 수축인 구간의 창 후보(`_add_lock_candidate`의 `last_sign < 0`)
- **R5-2 수축 hold 후보(2.3절)와 CARRY_ret의 운반 후보 추가는 판 3 그대로**($\max(13+p_h/3, p_{ret})$)다. 그 후보는 펌프 가압의 상계이고, 구간·운반 자체가 ④와 $\hat p$를 이미 들고 있으므로 $\hat p$를 다시 넣지 않는다(과보수만 늘어남).

**적용 범위(판 4.1, 조건 A5)**: 직전 이동 주기(EXT·RET·CARRY 가운데 마지막 주기, 코드의 `last_sign`)가 수축이면, 그 뒤 여는 **모든** 새 구간에 R5-7 후보를 넣는다.
- 새 구간이 LOCK($u$ = 0)에서 열리든 HOLD($0<\lvert u\rvert\le u_{hold}$, 수축 미세 명령 포함)에서 열리든 넣는다.
- 그 수축이 잠금에서 시작했든(CARRY_ret → RET), 신장 반전(EXT → RET, LC 잠금 없음)에서 시작했든 넣는다. "같은 잠금에서 시작한 운반을 이었을 때"로 좁히지 않는다.
- 후보는 구간을 여는 첫 주기부터 넣는다. 판정 읽기는 밸브 꼬리 때문에 플랜트가 아직 움직이는 첫 HOLD 읽기일 수 있기 때문이다(유압 검토 11.1절).
- 판 4의 적용 지점 1·2가 이미 이 범위다: 창 후보는 `_open_lock_stretch` 직후 첫 `_add_lock_candidate`에서 `stretch.last_sign`으로 고르고, LOCK·HOLD 어느 쪽에서 열어도 같은 경로를 탄다. 판 4.1은 이 범위를 문장과 시험 T-JR-05 (m)로 고정한다.
- 열린 구간 안의 HOLD 주기는 새 구간을 열지 않는다(R5-1). 그러므로 수축 HOLD 자체에는 R5-7 후보를 더하지 않는다. 그 주기의 펌프 가압은 R5-2가 맡고, 갇힌 압력은 구간의 ④가 이미 덮는다(P1에서 HOLD는 잠금을 풀지 않는다, 2.2절).

**덮임 조건 A1~A5(판 4.1, 유압 검토 11.1절)**: 아래가 모두 성립할 때 R5-7이 ⑪b를 덮는다.
- **A1** 플랜트 해제 시점에 $\hat p\ge p_{tr}$이다. 근거는 R5-3 시드 $\max(\hat p, ④)$와 CARRY의 ④$^c$ 끈끈 올림이다. 이 조건은 ④가 J-P3b를 지킨다는 데 기대므로, 독립 보증이 아니다(④가 깨지면 A도 깨진다).
- **A2** RET에서 $\hat p$를 내리지 않는다. `ExtendStartTracker._advance_classified`가 수축 주기에 $\max(\hat p,\ \text{retract floor})$만 한다. 안 B(수축 감압 상계)를 넣으면 이 조건을 다시 증명해야 한다.
- **A3** 해제 뒤 플랜트 $p_{tr}\le\max\big(p_{tr,rel},\ \max_t p^*_{ret}(F(t))\big)$이다. 근거: r6 (c)는 압력을 올리지 않고, (a)는 $\min(p_{lag},\cdot)\le p^*$다. $p^*$가 수축 모델을 넘는 가벼운·공중 다리(반례 ⑩, 최대 +8 bar, $F_{lb}\le$ 1.2 kN)는 기존 공개 한계로 남는다(⑪b와 별개).
- **A4** 후보 $\hat p+\delta_m$의 헤드 짝은 **그 구간(잠금 또는 HOLD 구간) 시작 창의 헤드**다. 다른 잠금 시작 후보와 같은 규칙이다: 창 표본마다 그 표본의 헤드 판독과 짝짓고, ④는 그 최댓값을 쓴다. 따라서 짝의 헤드는 창 헤드의 상한이다. **$\hat p$를 마지막으로 올린 때(RET 중)의 헤드와 짝짓지 않는다.** RET 중 헤드가 창 헤드보다 낮았다면 옛 헤드 짝은 $R_{ub}$ 항을 깎기 때문이다. `moving_starts`의 R5-7 값은 스칼라로 lookback 최대에 들어가고, 짝 헤드는 창 표본의 헤드다(지금 구조 그대로). 주기 안 헤드 극값은 반례 ⑨의 한계로 남는다.
- **A5** 적용 범위는 위 문단이다.
- 수치 확인(유압 검토 11.1절, 1,406건): $\hat p$를 허용 최솟값 $p_{r0}$로 두어도, 모든 HOLD 읽기의 여유 $p_{r0}+\delta_m-p_{tr}$이 +4.30 bar 이상이다.

**근거**
- RET에서 추적기는 $\hat p\leftarrow\max(\hat p,\ \text{바닥})$만 하고 내리지 않는다(rev 4 수축 분기). 수축 탈출 시드(R5-3)로 $\hat p\ge$ ④(잠금 끝)이다.
- P3 (c)는 수축 감압을 유량에 묶을 뿐 압력을 올리지 않는다(분기 (c)는 $\max(p_{lag},\cdot)$이고 고정 $F$에서 단조 감소).
- 그래서 해제 뒤 갇힌 몫은 $\hat p$ 이하다. 채움 몫(목표 이하에서 오름)은 수축 모델과 전제 ④가 맡는다(6.2절 판단 그대로). 따라서 $M^{ret}$는 갇힌 몫과 채움 몫을 모두 덮는다.
- 잠금 순간 이후의 헤드 하강은 ④의 $R_{ub}$ 항이 덮는다.
- $\hat p$가 낮은 수축(신장 감압 뒤의 수축)에서는 $\hat p+\delta_m\le$ 바닥이라 값이 바뀌지 않는다. 그래서 늘어나는 과보수는 R5-3이 높게 시드한 수축에만 걸린다.

**비용**: 긴 수축 뒤 잠금에서도 $\hat p$(잠금 끝 ④)가 남는다. 감압 상계(안 B)를 만들지 않았으므로 시간에 따라 풀리지 않는다. 크기는 T-JR-12에서 잰다. 문제가 되면 안 B(P3 (c) 역식을 $\kappa_x s$, $\bar C_r$, $p_h-b_{read}$, $p_{bA}$ 상한으로 넣은 수축 감압 상계, 결정 146 일부 변경)를 판 5 후보로 한다.
- (판 4.1, 유압 검토 11.1절) 첫 HOLD 읽기의 과보수($p_{r0}+\delta_m-p_{tr}$)는 다리·$F$별 중앙값 7~18 kN, 최대 41 kN이다. VBJ RR 예는 15.1 kN이다($F_{true}$ 14.8 kN에 대해 $F_{lb}\approx$ −0.3 kN).
- 이 과보수의 대부분은 관문 창 안의 감압이다. 그 감압은 해제 증거가 없어 어떤 건전한 추적기도 셀 수 없다. 안 B도 관문 열림 뒤부터만 센다.
- **안 B로 가는 조건**(모두 만족할 때)
  1. T-JR-12가 실패하고, 그 읽기의 지배 후보 출처가 `retract_tracker`다.
  2. 그 RET가 관문 열림 뒤 $t_{dec}$ 이상 이어졌다. $t_{dec}$는 4.71 mm/s에서 0.01~1.1 s, 0.5 mm/s에서 최대 8~10.5 s다.
  3. 사용자가 결정 146 일부 변경을 승인한다.
- 1은 만족하는데 2가 아니면 B로는 줄지 않는다. 그때는 C1(해제 목격) 등을 판 5에서 검토한다. 판단 재료는 T-JR-12 기록 열 2개(5.5절)다.

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
| (판 4) `extend_start_bound.py` | `CARRY_END_RULES`에서 `fresh_stretch`를 뺀다(설정값으로 받지 않음). 시험 전용 `ALLOW_FRESH_STRETCH_FOR_TEST`(기본 False)가 참일 때만 `fresh_stretch`를 받는다. 새 필드 `retract_start_rule: str = "with_tracker"`(R5-7. 시험 전용 상수가 참일 때만 `"model_only"` = 판 3 동작). 두 필드를 rev 5 `to_meta()`에 넣는다 | rev 4 meta 불변 |
| (판 4) `two_pressure.py` | R5-6: 지금 구현(`_carry_to_inherit`, `_update_locked_stretch`의 합집합)을 유지한다. R5-7: 수축용 함수 `_retract_lock_start_model_Pa(leg, head)` = $\max(\texttt{\_lock\_start\_model\_Pa}(leg,-1,head),\ \hat p+\delta_m)$을 만들어 (1) RET·CARRY_ret 주기의 `_track_moving_leg` 시작값, (2) `last_sign < 0`인 `_add_lock_candidate`에 쓴다. R5-2 후보(`_update_locked_stretch` HOLD 분기, `_carry_period_bound_Pa`)는 지금 함수 그대로 둔다. 후보 출처 표지에 `RETRACT_TRACKER`(R5-7 항이 이긴 경우)를 더한다 | rev 4·`model_only` 경로 비트 동일 |
| (판 4) 기록 | per-read: 지배 후보 출처 `jp3_model_bound_source`(int8, 표 `jp3_source_names`), 지배 후보의 나이 `jp3_model_bound_age_s`(읽기 시각 − 후보 시각), 지배 후보의 헤드 `jp3_model_bound_head_Pa`, 상속 여부 `jp3_model_bound_inherited`(bool). 플랜트 시드 사건 행 `p1_retract_seed_log`(6.3절). 운반 기록 `carry_log`(6.3절) | 옵션 꺼짐이면 쓰지 않음 |

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

### 4.5 판 4 재구현 목록(python-expert, `221456d` 위에)

> 판 4a: 이 목록과 감사 수정을 합친 최신 목록은 13.12절(J4a-1~)이다. 두 목록이 다르면 13.12절을 따른다.

| # | 항목 | 확인 |
|---|---|---|
| J4-1 | R5-6을 판 4 규칙으로 고정한다: `inherit_when_gate_shut`만 설정값으로 받고, `fresh_stretch`는 `ALLOW_FRESH_STRETCH_FOR_TEST`로만 받는다. meta `carry_end_rule` | T-JR-05 (h)(i), T-JR-02(거부 조합에 `fresh_stretch` 추가) |
| J4-2 | R5-7 `_retract_lock_start_model_Pa`(2.10절). 적용 두 곳, 비적용 두 곳(R5-2 hold 후보, CARRY_ret 운반 후보). 시험 전용 `model_only` | T-JR-05 (j)(k), T-JR-04 사례 ⑪b |
| J4-3 | 후보 출처 `RETRACT_TRACKER` 추가. 출처 표는 기존 순서를 유지하고 끝에 붙인다 | T-JR-18 |
| J4-4 | per-read 기록 4열(`jp3_model_bound_source`·`_age_s`·`_head_Pa`·`_inherited`)과 `trace_excerpt` 열 추가 | T-JR-18 |
| J4-5 | 플랜트 시드 사건 행 `p1_retract_seed_log`, 운반 기록 `carry_log` | T-JR-15(시드 순 힘 연속 ≤ 1 N 결과 보고), T-JR-18 |
| J4-6 | T-JR-03 기준값을 149 ms(허용 0)로, 연속 ODE 구간 검사를 추가한다(5.2절) | T-JR-03 |
| J4-7 | T-JR-06 경로 B 주석·식을 "$\psi p_B$ 도움 없음 + VN 배수 포함"(87 bar 160.16 ms)으로, 하한을 M1c 로드 체크 해제 시각으로 바꾼다. 35.2 bar(R12 RR 70 ms) 사례를 함께 둔다 | T-JR-06 |
| J4-8 | T-JR-04 사례 ⑪·⑪b, T-JR-05 (h)~(k), T-JR-18 추가 | 5.2절 |
| J4-9 | 사례 재생 A~F를 5.7절 예측으로 판정하는 비교 스크립트: `221456d` 출력(scratchpad `jp3\cases2`·`cases3`)과 명령 해시·읽기별 사용 상계를 대조한다 | 5.7절 |
| J4-11(판 4.1) | T-JR-04 사례 ⑪b-P1(유압 검토 11.1절 모형: P1 플랜트 + r6, 관문이 RET 안에서 열리는 최소 $N$ 탐색, 판독 −4.62 bar) | P4-7 |
| J4-12(판 4.1) | T-JR-05 (l)(m). A4는 지금 구조(창 표본 헤드 짝)를 시험으로 고정하고, A5는 네 경로 ①~④에서 첫 주기 후보를 확인한다. 실패하면 J4-2 적용 지점 2를 고친다 | P4-8 |
| J4-13(판 4.1) | T-JR-12 기록: `retract_tracker_dominated_reads`(다리별, 과보수 > 0.6 kN·거짓 저하 수 포함), `retract_tracker_stretch_log`, T4h `jp3_ret_after_gate_s` | P4-9, 6.3절 |
| J4-10 | 시험 묶음의 기존 실패 2건 처리: `test_d8x_diag::test_rerun_gives_the_stored_command_hash`는 master `3992e5e`에서도 같은 해시 `c0b626b9…`로 실패한다(검토에서 확인, 무관). `test_chrono_t45_replay::test_rev7_regression_on_the_stage3_records`(55 ≠ 23)는 master에서 확인한 뒤 T-JR-01 예외로 기록한다 | T-JR-01 |

## 5. 단위 시험과 합격 기준

### 5.1 회귀(옵션 꺼짐)

| ID | 내용 | 합격 |
|---|---|---|
| T-JR-01 | 옵션 꺼짐 회귀: B-2, 기존 `two_pressure`·`extend_start_bound`·`v5_options`·`harness_hydraulics` 시험, `test_s8_ml_main.py:229`, B-7, T-P3-1~5, 4.4절 표 | B-2 23/23, 기존 시험 전부 통과, digest·meta·함수 격자 해시 불변. 저장 h10 줄 28·172·245와 같은 사례 재실행 `commands_sha256` 동일 |
| T-JR-02 | 태그·설정: 4.3절 함수 표, 접미사 조합(`_LAS`, `_K1`, `_LAS_K1`, `_TCL`) 전부, `to_dict`/`from_dict` 왕복, 거부 조합 3절 | 표대로. 거부는 `ValueError`/`SystemExit` |

### 5.2 새 규칙 단위 시험

| ID | 내용 | 합격 |
|---|---|---|
| T-JR-03 | 선 충전 관문 상계(속성 시험, 시드 20261116): 무작위 명령열 1,000개(잠금 → 0·미세·큰 명령, 방향 반전, 0.05~5 % $v_{max}$), 헤드 5~200 bar, $p_r$ = 바닥(−0.913)·0·$p_T$·~80 bar, **헤드 판독 오차 ±4.62 bar(정상 등급 상한, 양 부호)**, **주기 안 헤드 혹 0~3.6 bar**($p_r$은 체적 비로 반대), **플랜트 $F_{band}$ 0~16 kN**, **void 0·0.2 mm**, VN·BL. 플랜트 = `CheckOpenGate`(P1 공칭, 1 ms 묶음, 밸브 지연 평균 속도), 추적기 = `LineFillGateBound`($e_h$ 9 bar, need$^{ub}$ $F_{band}$ 0·$p_r$ $p_{floor}$). 수축 need의 $p_h$·$p_r$·$F_{band}$·$s$ 단조성 격자 | 신장·수축 모두 **"관문이 감압·RET 전환을 세는 첫 소단계 ≥ 플랜트 해제 묶음"** 위반 0. void > 0 경우만 따로 센다(기록). 단조성: need가 $F_{band}$·$p_r$·$s$에 감소, $p_h$에 증가(위반이면 격자 최대로 바꾸고 다시 시험). 기준값 재현: R12 RR(VN) 플랜트 70 ms, 관문 **148 ms**(±1 ms). **(판 4로 바꿈)** 관문 = **149 ms(1 ms 소단계, 허용 0)**이고, 연속 ODE 시각 $t_{B1}$ = 148.013 ms에 대해 $t_{B1}\le t_{gate}\le t_{B1}+1$ ms. 근거: 배수 없는 닫힌 식 147.948 ms, VN 배수 포함 연속 ODE 148.013 ms, 배수 포함 1 ms 소단계 149 ms(검토 `cr04`, 저장소 코드 import 없음). 149 ms는 연속 시각이 148 ms 소단계 경계를 0.013 ms 넘어 다음 소단계 끝에서 판정한 값이다. 플랜트 70 ms(±1 ms)는 그대로 |
| T-JR-04 | T-P3-3 확장(속성 시험, 시드 20261107 + 20261116): 단일 다리 모니터 구동 + 플랜트(옛 r5 플랜트, P1~P3 플랜트 둘 다, 내부 스텝 5×10⁻⁴ s, 잠긴 동안 무작위 하중 궤적). 명시 사례: **⑤**(긴 잠금 39 bar → −2 µm/s 1주기 → +2 µm/s → 잠긴 동안 −70 kN/s 0.3 s → 4.7 mm/s), **⑦**(2 bar 잠금 → −0.2 mm/s 2 s), **⑧**(하중으로 50 bar 잠금 → −1 mm/s 0.5 s → +4.7 mm/s; P3 (c)로 0.42~0.49 s에 30 bar), **⑩**(공중 전방 $F$ −1 kN 신장 잠금 → $v_{max}$ 수축: 채움 몫으로 분류되는지). 매개변수 공칭·감도 끝(β 0.69~1.6 GPa, $L_{0h}$ 0.05~0.08, $L_{0r}$ 0.02~0.10 m, B 호스 +36 %) | rev 5: 모든 읽기에서 J-P3a·c 위반 0, J-P3b 허용 초과 0. rev 4: 사례 ⑤가 위반으로 재현(반례 기록). 반례 ① 사례는 따로 센다. ⑨(주기 안 헤드 극값)는 빈도·최대 크기를 기록(판정 아님) |
| T-JR-05 | HOLD 의미 단위: (a) 0 → +2 µm/s → −2 µm/s → 0에서 구간이 한 번만 열리고 닫히지 않음, ④ 매 주기 갱신. (b) $\lvert u\rvert = u_{hold}$는 HOLD, $u_{hold}(1+10^{-9})$는 CARRY. (c) $u<0$ HOLD에서 후보 `retract_hold` 1개 추가, ④ ≥ 수축 모델. (d) CARRY 첫 주기 시드(신장·수축 각각), 끈끈 올림. (e) HOLD에서 온라인 비 학습기 미호출. (f) rev 4 pickle → rev 5 복원(빈 상태). (g) rev 5 meta 키는 rev 5에서만 | 정의대로 |
| T-JR-06 | P1 플랜트(hydraulics 7절 기준): 잠긴 다리에 ±2 µm/s × 1 s → 해제 0. 4.7 mm/s → 0.1 s 안에 해제. `CheckOpenGate`의 `x`·`is_open`·`rod_released`가 같은 입력의 `CheckOpenDelay`(VN 1.0)와 비트 동일. 크리프·열림 이동·감쇠·시드 출력 0. **(판 4로 바꿈)** "0.1 s 안"은 헤드 35 bar(R12 RR, $\psi$ 도움으로 70 ms)에 묶인 문장이었다. 해제 시각 기준을 헤드에 따른 구간으로 바꾼다: M1c 로드 체크 해제 시각 ≤ 해제 ≤ $t_B$ + 5 ms. $t_B$ = "$\psi p_B$ 도움 없음 + VN 배수 포함" 채움 시각이다(밸브 정지 → 4.71 mm/s, τ 0.1 s, 전방 $p_h$ 87 bar **160.16 ms**, 배수 없으면 160.08 ms, 35.2 bar 94.02 ms; 검토 `cr04`). 구현 실측 152 ms(87 bar)는 로드 체크가 먼저 풀려 약 8 ms 이르다. R12 RR 35.2 bar 사례(70 ms)를 함께 둔다 | 정의대로 |
| T-JR-07 | P2: $G_{r,lock}\ne0$ 재잠김에서 $\lvert\Delta p_{tr}\rvert$ ≤ 0.01 bar, $\lvert\Delta p_h\rvert$ ≤ 0.01 bar, 힘 차 ≤ 1 N. 잠긴 뒤 $\Delta p_r/\Delta p_h$ = −1.2278(±10⁻⁴). 참값 최소 = $p_{floor}$ ± 1 Pa. 신장 잠금 $\lvert p_{r0}-G_{r,lock}/A_{ann}-p_{lag}\rvert$ ≤ 1 Pa(−3 bar 계단 없음) | 정의대로 |
| T-JR-08 | P3 `flow_limited_r6`(유압 검토 1.4절 기준 그대로). ① (a)·(b) 분기는 r5와 격자 해시 비트 동일. ② (c)·(d) 기준값 재현(상대 10⁻⁹, $\Delta t$ 5×10⁻⁴ s, τ 0.05 s): (c) 미세 $p^0$ 80 bar·$F$ = 210 bar·$A_h$ − 80 bar·$A_{ann}$·1 µm/s·200스텝 Δp 전방 −0.015359 / 후방 −0.014512 bar; (d) 미세 2 bar·$F$ 10 kN·1 µm/s·200스텝 +0.0020963 / +0.0019808 bar; (c) 예 50 bar·22 kN·1 mm/s 첫 스텝 44.0 / 50.39 bar/s, 30 bar 도달 0.4935 / 0.4245 s, 1 s에 13.095 / 14.574 bar. ③ 1 µm/s × 0.1 s(수축 감압 $p_h$ ≤ 210 bar, 신장 승압)에서 $\lvert\Delta p\rvert$ < 0.1 bar. ④ (첫 판의 "$v_{max}$에서 r5 ±1 %"를 바꿈) 상한이 묶이지 않는 스텝은 r5와 비트 동일, 1.3절 격자의 0.3 s 시점 차 ≤ 0.3 bar, 일시 최대 차(≤ 12 bar)는 기록만. ⑤ 한 스텝이 $p$에 단조 증가(기울기 ≥ 0). ⑥ 고정점 없음: 수축·$p>p^*$·$s>0$인 모든 격자점에서 $p^k<p^{k-1}$(엄격) | 정의대로 |
| T-JR-09 | P4: 오차 끈 실행에서 매 읽기 로드 판독 = `plant_rod_pressure_Pa()`(이동 중 포함, ≤ 10⁻⁹ Pa), 헤드 판독 식. T4h 재생(`t4h_replay --extend-start-revision 5`)이 ext 판정을 정확히 재현 | 정의대로 |
| T-JR-04 사례 ⑪(판 4) | 단일 다리 모니터 + P1~P4 플랜트. 신장 잠금(헤드 73 bar, $p_{tr}$ 31 bar) → 잠긴 채 하중 감소(헤드 −30 bar/s) → $-1.4u_{hold}$ 2주기(관문 need 미달) → $-0.99u_{hold}$ HOLD 3주기 | R5-6: HOLD 읽기 ④ ≥ $p_{tr}$(J-P3b 위반 0), `inherited_candidates` ≥ 1. `fresh_stretch`(시험 상수): HOLD 첫 읽기 ④ = 수축 모델이고 $p_{tr}$ − ④ > 0.6 kN/$A_{ann}$(반례 재현, 기록) |
| T-JR-04 사례 ⑪b(판 4) | 단일 다리, 후방, 로드 판독 대체 상태(⑤ 없음, $p_{ret}$ 바닥 ≤ 수축 모델), $F$ 14.8 kN 고정, 잠긴 $p_{tr}$ 59.9 bar(헤드 35.4 bar). 비교 원리가 허용하는 최악 = 플랜트가 **관문 열림 소단계에 해제**(시험용 플랜트 훅). 그 뒤 RET 0.3 mm/s × 0.2 s → HOLD(0 명령) 1 s. P3 (c) 감압, $C_r$ 1.586×10⁻¹² m³/Pa. 변형: RET 0.1·0.5 s, 1 mm/s × 0.1·0.2 s, $F$ 5 kN | 기대값은 5.7절 P4-6 표. R5-7: 모든 HOLD 읽기 ④ ≥ $p_{tr}$(위반 0). `model_only`(시험 상수): 위반이 재현되고 간격 ≤ −20 bar |
| T-JR-04 사례 ⑪b-P1(판 4.1) | 유압 검토 11.1절 모형을 그대로 쓴다: 단일 다리, **전방, $F$ 2 kN 고정, 잠긴 $p_{r0}$ 60 bar**. P1 플랜트(M1c 수축 선 충전 κ 1, VN 배수, need = 플랜트 입력 `retract_dead`, 해제 시드 $\max(p_{rod}, p_{r0})$)와 P3(`flow_limited_rod_pressure_r6`, 5×10⁻⁴ s). 작용 명령 **−0.5 mm/s**를 관문이 RET 안에서 열리는 가장 작은 주기 수 $N$만큼 준 뒤 0(HOLD). **헤드 판독 = 참값 − 4.62 bar**. 대체 다리(⑤ 없음). 밸브 τ_v 0.1 s, 1 ms 묶음 평균. 띠 0·4 kN 두 변형 | `model_only`(시험 상수): 첫 HOLD 읽기 초과 $p_{tr}-④$ = **+27.4 bar**(± 0.5 bar, 두 띠 가운데 큰 값. 유압 검토 표의 $p_{r0}\le$ 60 bar 전방 $F$ 2 kN 최대). R5-7: 모든 HOLD 읽기 위반 0, 여유 ≥ +4.30 bar. 기대값이 ±0.5 bar 넘게 다르면 모형 입력(띠, $N$, 판독 오차 적용 위치)을 유압 검토 `hr11/q1_trapped_after_ret.py`와 대조한다 |
| T-JR-05 (l)(m)(판 4.1) | (l) A4: RET 중 헤드가 낮다가 구간 시작 창에서 헤드가 오른 경우, R5-7 후보의 짝 헤드 = 창 표본 헤드(최댓값)이고, RET 중 $\hat p$를 올린 때의 헤드가 아니다. 그 뒤 헤드가 내려가면 ④ = $\hat p+\delta_m+R_{ub}(p_{h,창}-p_h)$. (m) A5: ① CARRY_ret → RET → LOCK, ② CARRY_ret → RET → 수축 HOLD($u=-0.5u_{hold}$)로 열린 구간, ③ EXT → RET(반전, 잠금 없음) → HOLD, ④ 관문이 닫힌 CARRY_ret → HOLD(R5-6과 함께) 네 경우 모두 구간 첫 주기부터 출처 `retract_tracker` 후보가 있다(①~③은 $\hat p+\delta_m$ > 바닥일 때). 열린 구간 안의 수축 HOLD 주기에는 R5-7 후보가 더해지지 않는다(R5-2 후보만) | 정의대로 |
| T-JR-05 (h)~(k)(판 4) | (h) 관문이 닫힌 CARRY_ret → HOLD: 새 구간 후보 = 창 후보 + 운반 후보(개수·값 일치), `stroke_window_max_m` = 최댓값. (i) 관문이 닫힌 CARRY_ext → LOCK도 같음. 관문이 열린 운반 → LOCK은 상속 0. (j) RET 뒤 LOCK 창 후보 = $\max(13+p_h/3, p_{ret}, \hat p+\delta_m)$, 출처 `retract_tracker`(R5-7 항이 이겼을 때). (k) R5-2 hold 후보와 CARRY_ret 운반 후보에는 $\hat p$ 항이 없음. 신장 감압 뒤 수축($\hat p+\delta_m\le$ 바닥)에서는 R5-7이 값을 바꾸지 않음(비트 동일) | 정의대로 |
| T-JR-18(판 4) | 기록: per-read `jp3_model_bound_source`·`_age_s`·`_head_Pa`·`_inherited`가 ④를 만든 후보와 일치(재계산 ≤ 1 Pa). `p1_retract_seed_log` 행 수 = `p1_retract_seed_count`, 행마다 순 힘 연속 ≤ 1 N. `carry_log`의 `gate_opened`가 거짓인 행 수 = `gate_never_opened_carries` | 정의대로 |

### 5.3 사례 재생(R12 bottom-FL-Fs4 o0.0, RR; 격자 r69·r67)

예측은 결과 전에 고정한다(판 2 갱신은 5.4절 표). 예측과 다르면 멈추고 원인을 본다(결정 96 멈춤 조건 "허용 범위 밖 변경"에 넣는다).

| 변형 | 설정 | 기대 결과(합격) |
|---|---|---|
| A 재현 | VB, LS1~LS4(rev 4, 옛 플랜트) | 저장 h10 줄과 `commands_sha256`·`extend_bound_check` 동일: VB 2 / −9.806 bar @ 48.9, LS1 0 / +0.486, LS2 3 / −9.643 @ 48.8, LS3 4 / −26.334 @ 48.8, LS4 0 / +0.500. 격자 `grid_r69_bottom` results[12].runs[0] = VB 값과 같음, `grid_r67_top` results[13].runs[3] FR 3 / −0.900 @ 48.7 |
| B 제어기만 | VBH, LSH1~LSH4(옛 플랜트 + rev 5) | **명령 해시 = A**(대체 다리 없음, T8). RR 48.7~49.0 s 읽기 분류 HOLD(작용 −0.00194, +0.00213, +0.0359, +0.0749 mm/s 모두 ≤ $u_{hold}$), 49.1 s CARRY, `seed`/`carry_raises` ≥ 1. J-P3a 위반 0(49.1 s 이후 $\hat p+\delta_m$ ≥ ④ 약 64~78 bar). J-P3b: VB·LS2·LS1·LS4 위반 0. **LS3는 48.8 s에 약 −3 bar(④ ≈ 13 + 1.355 × (77.7 − 47.2) ≈ 54 bar 대 $p_{tr}$ 57.4 bar) 허용 초과 가능**. 이는 앵커 계단 +20.8 bar·헤드 +6.9 bar(hydraulics H3) 플랜트 산물이라 기록 전용이다 |
| C P1만 + rev 4(시험 전용) | VB 플랜트 + P1, P2~P4 끔, rev 4 | RR 43.39 s 잠금 뒤 첫 $\lvert u\rvert>u_{hold}$ 읽기(49.0 → 49.1 s 주기)까지 잠김 상태 변화 0. 해제 49.06~49.08 s. 옛 정의 J-P3 위반이 **49.1 s 읽기로 옮겨 남음**, 간격 −25 ~ −8 bar(추정 −14~−17). 48.7~49.0 s는 ext_locked, `locked_unpaired_reads` ≥ 3. 위반이 없거나 간격이 범위 밖이면 멈춤<br>**[판 4 사후 정정 표지 — 위 원문은 판 3 고정 예측 그대로]** 이 행의 수치는 436.8 명령 순서(RR 48.7~49.0 s 미세 반전, 49.0 → 49.1 s 4.71 mm/s 신장)가 다시 나온다는 전제의 값이다. E 행과 같은 단서가 빠졌다(표기 누락): "순서가 다르게 나오면 RR 시간선을 기록하고, 결함 기전(관문 없는 rev 4가 P1 지연 해제 뒤 갇힌 압력을 놓침)의 재현 여부로 판정한다." `221456d` 실측: 순서가 달라짐(48.7~49.0 s 수축 −0.35~−0.59 mm/s), 해제 49.093 s, 위반 49.2 s RR −4.19·FL −3.56 bar(기전 재현). 5.6절 |
| D P1만 + rev 5 | VB 플랜트 + P1, rev 5 | 잠김 동작은 C와 같음. J-P3a·b·c 위반 0. 49.1 s CARRY, $\hat p$ ≈ ④(49.0 s) ≈ 70 bar, 간격 ≥ +15 bar(계산 +27). HOLD 읽기 ④ − $p_{tr}$ ≥ +10 bar(hydraulics 물리 기준 +15.4~+16.4). **C의 49.1 s 위반을 D가 덮는 것**이 이 묶음의 핵심 합격이다<br>**[판 4 사후 정정 표지 — 위 원문은 판 3 고정 예측 그대로]** 분류·$\hat p$·HOLD 간격 수치는 C 행과 같은 명령 순서 전제의 값이다. 순서가 다르면 RR 시간선을 기록하고, 핵심 합격("C의 위반 읽기를 D가 덮음", J-P3a·b·c 위반 0)만 판정한다. ④ ≈ 70 bar는 원인 보고서 가정 $M_j$ = 13 bar에서 나온 값으로, 구현의 잠금 시작 모델($\max(13,\hat p+\delta_m)$, lookback 최대)과 다르다. `221456d` 실측: 위반 0, C의 위반 읽기 49.2 s RR 간격 +161.2 bar, 49.1 s `carry_ret` +111.1 bar, 48.7~49.0 s HOLD 읽기 없음. 5.6절 |
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
| T-JR-12 Dg-3 | 135키(`dg3_keys.txt`): VBH 대 저장 H-6(rev 4), VBJ 대 VBJ0 | L2 통과 → 실패 0, 새 FAULT 0, 첫 READY +30 s 초과 0, J-P3a·b·c 위반 0(VBJ의 normal 등급 L2 1키만 판정. L3 conservative 134키는 기록만, 결정 147). 기록: 대체 다리 하한 − 진값 > 0.6 kN 수, 과보수 p50/p90/p99 증가, HOLD·CARRY 주기 수, 수축 후보 수, 시드 수. **(판 4.1 추가, 안 B 판단용)** ① `retract_tracker_dominated_reads`: 대체 다리의 LOCK·HOLD 읽기 가운데 ④의 지배 후보 출처가 `retract_tracker`(R5-7)인 읽기 수(다리별). 그 가운데 과보수 > 0.6 kN, 거짓 저하($F_{true}\ge F_{min}$, $F_{lb}<F_{min}$)인 수도 함께 센다. ② `retract_tracker_ret_after_gate_s`: 그런 구간마다, 직전 RET가 **관문 열림 뒤** 이어진 길이 [s](관문 열림 시각 → RET 마지막 주기 끝). 분포(p50/p90/최대)와 행 목록(상한 2,000행: `leg, t_open_s, ret_after_gate_s, ret_mean_speed_m_s, dominated_reads, max_over_kN`). 안 B로 갈지는 2.10절 비용 문단의 조건으로 판단한다 |
| T-JR-13 Dg-2 | 저장 T4h(`h10_reuse_rerun_t4h`, `h6_dg3_v4on_t4h`)를 rev 5로 재생 | 오류 0. 과보수 p90 증가·관문 지연 분포 기록(권고 조건 4 선례: 문턱 없음, 비용 기록) |
| T-JR-14 정렬 | `lock_window_alignment`를 VBH·VBJ Dg-3 135행에 | 대체 다리 로그 대조 불일치 0, J11 $n_{late}$ > 0 행 0 |
| T-JR-15 재잠김 계단 | VBJ 135행 + E 사례의 per-lock 기록 | `relock_step_over_1bar_count` 0(hydraulics 7절 권고 집계), VBH는 기록. 수축 시드(P1 예외)가 만드는 압력 계단(+약 19 bar, 헤드 판독 +5 bar)은 잠금 계단이 아니므로 따로 센다(`p1_retract_seed_count`, `p1_retract_seed_step_max_bar`), 순 힘은 연속(≤ 1 N) |
| T-JR-17 갇힌·채움 경계(판 3) | 단위: ① `last_target_Pa`가 같은 스텝 `flow_limited_rod_pressure_r6`에 넘긴 목표와 비트 동일. ② 경계식 함수 대 닫힌 식: $F$ −20~300 kN 격자에서 전방 $F$ ≤ 3.6 kN·후방 ≤ 2.2 kN에서만 같고 그 밖은 함수가 큼(유압 검토 10절 값 재현: $F$ 5 / 25 / 50 kN 전방 −4.0 / −61.7 / −133.9, 후방 −9.7 / −80.0 / −167.9 bar). ③ 부하 다리($F$ 25 kN) 수축 채움 읽기가 `jp3c_fill_reads`로 감(판정 집합으로 새지 않음). ④ 플랜트가 잠긴 `carry_ret` 읽기는 $p_{tr}$이 $p^*$ 아래여도 `jp3c_reads`. ⑤ $p_{tr}=p^*_{last}$는 채움 | 정의대로 |
| T-JR-16 가벼운 다리 수축 | 단위: 공중 전방 다리($F$ −1 kN, P2 앵커 5 bar, $M$ 13.5 bar) 신장 잠금 → $v_{max}$ 수축(P1~P4 플랜트, rev 5). 묶음: VBJ 전 행의 `jp3c_fill_*`·`ret_*` 집계 | 단위: 수축 CARRY 읽기 가운데 플랜트가 잠긴 읽기(P1 충전 중, $p_{tr}$ ≈ 앵커 5 bar)는 `jp3c_reads`(갇힌 몫, 위반 0), 이동 중이고 $p_{tr}\le p^*_{last}$인 읽기는 `jp3c_fill_reads`로 가고, 그 위반 최대 ≤ 수계산 $p^*_{ret}$ − 수축 모델 = +5.6 bar(+0.5 bar 여유). `jp3c_breach_reads`(갇힌 몫) 0. 그 읽기들의 대체 하한 ≤ 1.2 kN(< $F_{min}$). 묶음: 기록 |

### 5.6 판 3 예측 사후 대조(판 4, 구현 `221456d`, 결정 152)

판 3 5.3·5.4절 원문은 그대로 둔다. 아래는 결과를 본 뒤 쓴 대조이고 예측이 아니다. 근거는 `jp3_impl_review.md` 3절이다(scratchpad `jp3\cases2`·`cases3`, 검토 스크립트 `cr01`·`cr02`·`cr05`·`cr08`).

| 판 3 항목 | 예측 | 실측 | 원인 | 분류 |
|---|---|---|---|---|
| 5.3 C | 위반 49.1 s, 간격 −25~−8 bar, 해제 49.06~49.08 s | 위반 49.2 s, RR −4.19 / FL −3.56 bar, 해제 49.093 s(수축 쪽 선 충전 완료) | P1이 미세 명령 해제를 없애 폐루프가 앞서 갈라졌다(48.4 s 헤드 57.5 대 62.7 bar). 48.7~49.0 s 명령이 수축 −0.35~−0.59 mm/s가 됐다. 첫 신장 읽기는 49.2 s | **예측 전제 오류 + 표기 누락**(C·D 행에 순서 단서 없음). 결함 기전은 재현됐다 |
| 5.3 D | 49.1 s CARRY 신장, $\hat p$ ≈ 70 bar, 간격 ≥ +15, HOLD 간격 ≥ +10 bar | 위반 0. 49.1 s `carry_ret` +111.1 bar, 49.2 s +161.2 bar. 48.7~49.0 s HOLD 없음. 전 구간 jp3b 최소 +7.09 bar(다른 시각, 가벼운 다리 13 대 5 bar) | 위와 같음 | **예측 전제 오류**. 핵심 합격은 충족 |
| 5.3 E | $p_{tr}$ ±4 bar, 다섯 설정 범위 ≤ 3 bar | VBJ 48.48 / 54.51 / 59.92 bar(49.0 s +6.0), 49.0 s 범위 5.75 bar | 순서가 달라짐(48.7~49.1 s `carry_ret`) | **E 행 단서대로 기록**(멈춤 대상 아님). 판정 키 0 |
| 5.4 #12 | 수축 시드 계단 +약 19 bar($p_h$ 77·$p_r$ 2 bar) | 최대 +33.87~33.99 bar(E 다섯 설정, 7~11건) | 시드 ∝ 대략 $p_h/\psi'$. $p_h$ 약 110~125 bar로 추정(기록 없음) | **예시 값**(상계 아님). 판 4에서 시드 사건 행을 기록한다(T-JR-18) |
| 5.3 B, 2.4절 ④ | ④ 약 64~78 bar(49.1 s), LS3 48.8 s 약 −3 bar 허용 초과 가능 | VBH 49.1 s 185.95 bar, LSH3 jp3b 허용 초과 0(최소 +7.27 bar) | 가정 $M_j$ = 13 bar가 틀렸다. 실제 $M_j$는 $\max(13,\hat p+\delta_m)$와 lookback 최대라서 VBH RR 43.2 s에 87.67 bar(참값 5.0 bar)였다 | **예측 전제 오류**(보수 쪽, 합격 영향 없음) |
| 2.4절·5.4 #9 수축 need | 전방 $p_h$ 77 bar 1.24 mm, CARRY +85 ms | 구현 need$^{ub}$ 2.315 mm($p_h$ 77 + $e_h$ 9) | 명세 값은 플랜트 공칭 입력이다. 보수 입력으로는 1.87배다(2.4절 판 4 정정) | **명세 비용 수치 오류**(구현은 명세 문장대로, 보수 쪽) |
| 2.1절 CARRY 끝 | (규칙) 새 구간·새 후보만 | E LSJ4 FL 49.0 s −10.67 bar(`fresh_stretch`, 구현자 보고) | 반례 ⑪ | **명세 규칙 결함** → R5-6 |
| 5.4 #1·#6 관문 148 ms | 148 ms | 149 ms | 1 ms 소단계 판정(연속 148.013 ms) | **기준 표기 정밀도**. T-JR-03을 149 ms(허용 0)로 바꿈 |
| (판 4.1) 2.4절·5.4 #9 수축 need 출처 | 위 행은 "명세 비용 수치 오류"로 적었다 | 1.24 mm는 유압 검토 3.4절 비용 칸이 `hr02_gate_check.json`의 플랜트 공칭 점(`ret_static.<leg>:point_loaded`)을 옮긴 **표기 오류**였다(유압 검토 11.3절). 판 1 관문 대비 실제 증가는 전방 +0.89 mm·+0.24 s, 후방 +1.01 mm·+0.27 s다. 판 4의 "+0.37 s"는 need$^{ub}$와 플랜트 공칭 need의 차였다 | 표기 오류는 유압 검토 쪽에 있었다. 명세는 그 값을 확인하지 않고 옮겼다 | **출처 표기 오류**. 2.4절 대가 문장을 판 4.1로 바꿈. 3.3절 건전성 표(보수 입력)는 그대로 맞다 |
| (판 4.1) 5.4 #12 시드 운전점 | +19 bar($p_h$ 77·$p_r$ 2 bar) | 최대 사건은 RL 49.6~49.7 s, $p_h$ **120.5~120.9 bar**, 잠긴 $p_r$ = 바닥 −0.91 bar(g), 띠 7.0 kN이다(재구성 33.69~33.83 bar 대 기록 33.87~33.99 bar, 차 ≤ 0.17 bar). 둘째는 FR $p_h$ 115.6 bar(32.4 bar)다. $p_h$ 77·$p_r$ 2·띠 0의 값은 18.8 bar로 판 3 예와 같다 | 바닥 $p_r$(로드실 공극)이 계단을 +0.9 bar 더 키운다. 시드 32.8 bar는 수축 모델 53.2 bar보다 낮아 2.3절 논증이 성립한다 | **예시 값**(확인됨, 유압 검토 11.2절). 순 힘 연속은 시드 사건 행(T-JR-18)으로 닫는다 |
| (판 4.1) 2.7절 ⑪b 크기, 검토 2.3절 | ⑪b 예: VBJ RR($F$ 14.8 kN, $p_r$ 59.9 bar)에서 $F_{lb}$ 11 kN 낙관 | P1 플랜트에서는 관문 창 동안 감압되어, 이 예의 ⑪b 시점 크기는 0이다($p_{tr}$ 12.2 bar = $p^*$). 11 kN은 RET 시작 때의 크기다. 물리 최대는 가벼운 다리의 전방 +27.4 bar(10.3 kN)·후방 +22.2 bar(7.0 kN)다($p_{r0}\le$ 60 bar) | 검토는 관문 창 안의 감압을 빼고 셌다(시험 훅 최악) | **예시 운전점 오류**(⑪b가 실재한다는 판정과 안 A 필요성은 유지: 480건 가운데 204건 거짓 참). P4-6(훅)은 그대로 두고 P4-7(P1 물리 사례)을 더함 |

### 5.7 판 4 사전 예측(결과 전 고정, 판 4 재구현의 사례 재생·단위 시험)

판 4를 쓰는 시점에 판 4 구현·시험 결과는 없다. 아래 예측은 이 판의 sha로 고정한다. 명령 순서에 기대지 않는 성질만 예측한다.

| # | 예측 | 근거 | 어기면 |
|---|---|---|---|
| P4-1 | 사례 재생 A~E의 `commands_sha256`(앞 12자)가 `221456d`와 같다. VB·VBH `295d0e7c9310`, LS1·LSH1 `bd50065cc09d`, LS2·LSH2 `875ad53bccc3`, LS3·LSH3 `53ae7c735918`, LS4·LSH4 `651a51ce7e3e`, VBJ `b3b4fb65002a`, LSJ1 `15afaa17ebcf`, LSJ2 `75c37ff55c01`, LSJ3 `983ad2785c86`, LSJ4 `3672c7222519`, C·D `e3869a3be2f8`. F의 A·B는 저장값과 같다 | 2.8절(T8). 사례 행에는 대체 다리가 없고, R5-6·R5-7은 상계·기록만 바꾼다 | T8 결함으로 멈춘다 |
| P4-2 | 같은 읽기·같은 다리에서 사용 상계(판 4) ≥ 사용 상계(`221456d`)다. 다른 읽기는 지배 후보 출처가 `retract_tracker`인 구간, 또는 그 구간에서 시드·운반으로 이어진 읽기뿐이다. 분류는 같거나, 관문이 늦어져 EXT·RET가 CARRY로 바뀌는 방향뿐이다 | R5-7은 최댓값 항만 더한다. 추적기 한 스텝과 관문 문턱은 $\hat p$에 단조다(높을수록 늦게 열림) | 멈추고 원인을 본다(결정 96) |
| P4-3 | J-P3a·b·c 판정 키가 VBJ·LSJ1~4에서 모두 0이다. VBH·LSH의 jp3b 허용 초과 0(기록), 재잠김 1 bar 초과 0 | P4-2와 `221456d`의 0 | 멈춘다 |
| P4-4 | 플랜트 기록은 `221456d`와 같다: `p1_retract_seed_count` VBJ 7, LSJ1 11, LSJ2 8, LSJ3 11, LSJ4 11, 최대 시드 계단 33.87~33.99 bar. 새 `p1_retract_seed_log`의 행마다 순 힘 연속 ≤ 1 N | 플랜트 코드 불변 | 멈춘다 |
| P4-5 | 시험 상수 `fresh_stretch`로 E LSJ4를 돌리면 명령 해시는 `3672c7222519` 그대로이고, FL 49.0 s HOLD 읽기에서 J-P3b 허용 초과 1건이 재현된다($p_{tr}$ − ④ = +10.67 bar ± 0.05 bar, 구현자 보고값) | R5-6이 없을 때의 반례 ⑪ | 멈추고 원인을 본다 |
| P4-6 | T-JR-04 사례 ⑪b(아래 표). R5-7: 모든 HOLD 읽기 간격 ≥ 0. `model_only`: 간격 ≤ −20 bar | 검토 `cr09`(P3 (c) 단독 적분, $\Delta t$ 5×10⁻⁴ s, 목표 지연 $p_{lag}$는 아래에 있다고 가정) | HOLD 시작 $p_{tr}$과 `model_only` 간격이 표에서 ±2 bar 넘게 다르거나, R5-7 간격이 표의 하한 간격보다 작으면 멈추고 원인을 본다(플랜트 훅·$C_r$ 차이 확인) |

**P4-6 기대값**(후방, $p_{r0}$ 59.9 bar, 플랜트가 관문 열림 소단계에 해제, RET 뒤 HOLD 첫 읽기)

| $F$ [kN] | RET 속도 × 시간 | HOLD 시작 $p_{tr}$ [bar] | 판 3 ④(= $13+p_h/3$) 간격 [bar] | 판 4 하한 간격($p_{r0}+\delta_m-p_{tr}$) [bar] | 판 3 $F_{lb}$ [kN] |
|---|---|---|---|---|---|
| 14.8 | 0.3 mm/s × 0.1 s | 58.52 | −33.88 | +1.88 | 25.44 |
| 14.8 | 0.3 mm/s × 0.2 s | 57.15 | −32.66 | +3.25 | 25.06 |
| 14.8 | 0.3 mm/s × 0.5 s | 53.13 | −29.08 | +7.27 | 23.94 |
| 14.8 | 1.0 mm/s × 0.1 s | 55.35 | −31.06 | +5.05 | 24.56 |
| 14.8 | 1.0 mm/s × 0.2 s | 50.95 | −27.14 | +9.45 | 23.33 |
| 5.0($p_{r0}$ 60.0) | 0.3 mm/s × 0.2 s | 57.92 | −36.78 | +2.58 | 16.56(참 5.0 kN < $F_{min}$) |

- "판 4 하한 간격"은 R5-7 항 $\hat p+\delta_m$에서 $\hat p$ = $p_{r0}$(시드 = ④ ≥ 잠긴 참값의 하한)로 놓은 값이다. 실제 ④·$\hat p$는 더 크므로 실측 간격은 이 값 이상이다.

**판 4.1 덧붙임(P4-1~P4-6 원문은 그대로, 결과 전 고정)**

| # | 예측 | 덧붙인 이유 | 어기면 |
|---|---|---|---|
| P4-7 | T-JR-04 사례 ⑪b-P1(전방, $F$ 2 kN, $p_{r0}$ 60 bar, $U$ 0.5 mm/s, 헤드 판독 −4.62 bar, 관문 열림 직후 HOLD): `model_only`면 첫 HOLD 초과 +27.4 bar(± 0.5 bar), R5-7이면 위반 0이고 여유 ≥ +4.30 bar | P4-6은 "플랜트가 관문 열림 소단계에 해제"인 시험 훅(비교 원리의 최악)이다. P1 플랜트의 물리 크기는 유압 검토 11.1절이 따로 쟀으므로, 그 사례를 P4-6과 별개의 예측으로 더한다. P4-6은 바꾸지 않는다 | 멈추고, 모형 입력을 `hr11/q1_trapped_after_ret.py`와 대조한다 |
| P4-8 | T-JR-05 (l)(m): A4(짝 헤드 = 구간 시작 창 헤드)와 A5(직전 이동 주기가 수축이면 LOCK·HOLD 어디서 연 새 구간이든 첫 주기부터 R5-7 후보, 같은 잠금으로 좁히지 않음)가 판 4 적용 지점 1·2로 이미 성립한다. **그래서 판 4.1의 범위 명시가 P4-1·P4-2의 값을 바꾸지 않는다** | 판 4 2.10절 문장이 A5 범위를 명시하지 않았다. 범위를 넓힌 것이 아니라 명시한 것이므로, 기존 예측과 같은 값이 나와야 한다 | (m)이 실패하면 구현이 판 4 지점 2를 좁게 구현한 것이다. 고친 뒤 P4-1·P4-2를 다시 판정한다 |
| P4-9 | T-JR-12 새 기록 열은 사례 재생 A~F(대체 다리 없음)에서 `retract_tracker_dominated_reads` = 0, `retract_tracker_stretch_log` 빈 목록이다. per-read `jp3_model_bound_source`는 모든 다리에 있다. `retract_tracker` 출처 읽기의 사용 상계는 P4-2를 따른다 | 열의 정의가 대체 다리 한정이라는 것을 결과 전에 고정한다(빈 집계를 통과로 읽지 않게 하기 위함) | 정의 결함으로 멈춘다 |

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

**(판 4) 진단 기록(판정 아님)**
- T4h per-read
  - `jp3_model_bound_source`(n×4, int8, 표 `jp3_source_names`): ④를 만든 후보의 출처(`pilot_model`, `extend_bound`, `previous_moving`, `retract_hold`, `retract_tracker` 등)
  - `jp3_model_bound_age_s`(n×4): 읽기 시각 − 그 후보를 넣은 시각. 상속 후보는 원래 넣은 시각
  - `jp3_model_bound_head_Pa`(n×4): 그 후보의 $p_{h,j}$
  - `jp3_model_bound_inherited`(n×4, bool): R5-6 상속 후보인지
  - LOCK·HOLD 밖의 읽기는 NaN·−1·False다. `trace_excerpt` 열에 `model_source, model_age_s`를 더한다.
- 플랜트 `hydraulics_record.p1_retract_seed_log`(P1 수축 M2 시드 사건, 상한 2,000행): `t_s, leg, p_h_Pa, p_r_locked_Pa, seed_Pa, step_Pa, dp_h_read_Pa, net_force_step_N`.
- 모니터 `extend_start_record.carry_log`(운반마다, 상한 2,000행): `leg, t_start_s, t_end_s, direction, periods, sum_abs_u_T_m, gate_opened, gate_open_t_s, need_ub_m_at_end, end_class(lock|hold|ext|ret|run_end), inherited_to_stretch`. 집계 `gate_never_opened_carries`는 그대로다.
- (판 4.1) `extend_bound_check`의 다리별 집계 `retract_tracker_dominated_reads`, 구간 기록 `retract_tracker_stretch_log`(행 `leg, t_open_s, ret_after_gate_s, ret_mean_speed_m_s, dominated_reads, max_over_kN`, 상한 2,000행). T4h에는 per-read `jp3_ret_after_gate_s`(n×4; R5-7 후보가 지배한 읽기에서만 값이 있고, 그 밖은 NaN)를 둔다. `max_over_kN`은 하네스가 참 힘을 알 때만 채운다(제어기는 참 힘을 읽지 않는다).

### 6.4 R16-15a와 플랜트 산물 한계(규칙 문장 초안)

> "VBJ·LSJ 행의 제어기 로드 판독은 플랜트 M2 참값이다(P4). 그래서 436.8 R16-15a의 판독 한계(잠김 법칙 값 판독, D3 오탐, T4h 재생 불완전)는 이 행에 적용되지 않는다. J-P3의 $p_{tr}$은 P1(선 충전 해제 관문)·P2(잠금 앵커 연속)·P3(네 분기 유량 상한)을 켠 플랜트 값이다. P1은 M1c 선 충전 식과 값(단위 기준 미달 참고값, Q-M9·V-6·L-2·H-3)에 기대므로, J-P3 통과는 'M1c 값 가정 아래 통과'로 적는다. P1은 M1c 출력 가운데 체크 열림 판정과 수축 열림의 M2 시드만 쓴다(시드는 예외로 남김, meta `output_exceptions`). 끈 출력의 방향은 다음과 같다: 신장 로드 체크 먼저 열림의 감압을 무시해 $p_{tr}$이 높게 나온다(보수). 수축 헤드 방출·크리프 이동이 없어 부하 다리 수축 시작의 하중 전이 과도가 작게 나온다(압력 판정과 무관). P1~P4를 끈 행(VB·LS·VBH·LSH)의 J-P3 기록에는 436.8 판정서 9.9절의 플랜트 산물(미세 명령 해제, 재잠김 앵커 계단, 무유량 감압)이 들어 있으므로 판정에 쓰지 않는다. 선 충전 관문 여유 $e_h$ 9 bar는 normal 등급 판독 오차와 주기 안 헤드 혹 3.6 bar(관찰값 가정)에 기대므로, conservative·old_worst 등급 행의 J-P3는 기록만 한다. 주기 안 헤드 극값(반례 ⑨), 수축 이동 중 추정(전제 ④: RET 전체와 수축 CARRY의 채움 몫, 가벼운·공중 다리에서 최대 약 +8 bar, 그때 대체 하한 ≤ 1.2 kN로 $F_{min}$ 판정에는 영향 없음)은 남는 한계로 공개한다."

> (판 4 추가) "관문이 열리지 않은 운반 뒤의 잠금은 운반 후보를 상속하고(R5-6), 수축 뒤 잠금 시작 후보에는 추적기 상계 $\hat p+\delta_m$를 넣는다(R5-7). 수축 감압 상계는 만들지 않았으므로(결정 146), 긴 수축 뒤 잠금과 관문이 늦게 열리는 긴 운반 뒤의 대체 하한은 보수적이다. 그 비용은 T-JR-12(Dg-3)로 쟀다. 시간이 지나면 후보를 버리는 규칙은 넣지 않았다. P1 플랜트에서는 미세 명령으로 잠금이 풀리지 않아, 오래된 후보가 실제 잠금 시작이기 때문이다(결정 152)."

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

**(판 4, 결정 152) 진행 순서**: 판 4 → 재구현(4.5절 J4-1~10) → T-JR-01~09·16~18 → 사례 재생 A~F(5.7절 예측) → T-JR-10~15. 여기서 **T-JR-12(Dg-3)가 비용 관문**이다. 실패하면 판 5(C1~C3, 필요하면 안 B)로 간다 → j9_main(H-10 본 부분) → 봉인 이하 위 순서. 관문을 통과하면 자동으로 진행한다. 완화안을 넣어도 대체 다리가 없는 행의 명령은 바뀌지 않는다. 그러나 J-P3 per-read 기록이 바뀌므로 j9_main은 T-JR-12 뒤에 돌린다.

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
| (판 4) ⑪b 기대값 | P3 (c) 단독 적분, $F$ 고정, $C_r$ 1.586×10⁻¹² m³/Pa(플랜트 공칭), $p_{bA}$ 5 bar, 목표 지연 $p_{lag}$는 감압 경로 아래, 플랜트가 관문 열림 소단계에 해제(비교 원리가 허용하는 최악) | 5.7절 P4-6, 검토 `cr09` |
| (판 4) 시드 계단 운전점 | +33.9 bar ↔ $p_h$ 약 110~125 bar($p_{rod}\propto p_h/\psi'$, $\psi'$ ≈ 3.2) | 5.6절, 유압 확인은 메인이 따로 넘김 |

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

**판 4 결정(152, 모두 검토 권고대로)**

| # | 항목 | 결정 |
|---|---|---|
| 13 | 결정 96 멈춤(5.3·5.4절 불일치) | 예측 전제 오류·표기 누락·예시 값으로 공개(부록 A)하고 멈춤을 푼다 |
| 14 | R5-6 상속 | 채택. `fresh_stretch`는 시험 전용 |
| 15 | 반례 ⑪b | 안 A(R5-7). 안 B(수축 감압 상계)는 T-JR-12에서 비용 문제가 생길 때의 판 5 후보 |
| 16 | 노화 규칙 | 넣지 않는다 |
| 17 | 비용 완화 C1~C3 | T-JR-12를 먼저 잰다. 실패하면 판 5에 넣는다. C1 = 운반 중 `stroke_m`(기름 부피 좌표) 변화로 해제를 목격(하네스·L1 좌표 한정), C2 = 관문이 열린 운반 뒤 lookback 최대에서 관문 전 끈끈한 값 제외, C3 = R5-2 후보를 공급 체적으로 제한(검토 4.3절) |
| 18 | 순서 | 판 4 → 재구현 → 사례 재생 A~F(5.7절) → T-JR-10~15 → j9_main. 관문을 통과하면 자동으로 진행한다 |

**새 확인 필요(판 2 갱신에서 생김, 결정 148로 닫힘)**

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
| (판 4) python-expert | 4.5절 J4-1~10, 5.2절 새 시험, 5.7절 예측 판정 |
| (판 4) hydraulics-expert | 메인이 따로 넘긴다: ⑪b 크기(갇힌 압력 지속 시간 격자)와 안 B 가능성, 시드 +33.9 bar 운전점, 2.4절 need 1.24 mm가 공칭 입력 값인지 |
| (판 4) verif-protocol-auditor | 판 4 sha로 5.7절 예측이 결과 전에 고정됐는지, 판 3 고정 예측 원문이 바뀌지 않았는지(표지 덧붙임만), `fresh_stretch`·`model_only`가 설정에서 고를 수 없는지, 부록 A 문장 |

## 11. 수행한 작업

| 스크립트(이 폴더) | 환경 | 내용 | 출력 |
|---|---|---|---|
| `rs01_scope_census.py` | dynamics-dev(`conda run -n dynamics-dev python -I -B`) | `resume_k1` identity의 벽시계·mask, 결과 줄의 설정·태그 수 | 콘솔(7절 표) |
| `rs02_check_totals.py` | 같음 | 436.8 VB·LS 레코드의 `extend_bound_check` 키 합(격자 run 단위 포함) | `rs02_check_totals.json` |
| `rs03_expected_49p1.py` | 같음 | 49.0 → 49.1 s의 플랜트 P1 열림(M1c), 추적기 관문, $\hat p$·$p_{tr}$ 감압. 저장소 함수(경로 A)와 닫힌 식(경로 B) | `rs03_expected_49p1.json` |

- 읽은 코드(읽기만): `extend_start_bound.py` 전체, `two_pressure.py` 2268~2650·2785~2880행, `harness_hydraulics.py` 전체, `s8_g4_rodside_check.py` 73~155행, `check_open_delay.py` 전체, `rod_release.py` 81~141행, `v5_options.py` 전체, `run_v5.py` 72~264행, `lock_window_alignment.py` 머리, `r79_sensor_screen.py` 135~272행, `r64_g4_closed_loop.py` 192~201행.
- 판 2: `hydraulics_remedy_review.md`(hydraulics-expert, `hr01~hr06`)를 읽었다. 관문 148 ms와 가벼운 다리 $p^*_{ret}$ − 모델 값은 `rs03_expected_49p1.hand_fill_time`을 import한 `-c` 한 줄로 다시 계산해 유압 검토 값과 맞췄다(147.95 ms; 전방 +8.24 / +5.59 / +2.94 bar). 436.9 실행·시험 출력은 보지 않았다.
- 판 4: 구현 `221456d` 출력(scratchpad `jp3\`)을 읽고 검토 `jp3_impl_review.md`를 썼다. 검토 스크립트 `cr01~cr09`는 scratchpad `ctrl-review\`에 있다. `cr04`(관문 기준 시각, 저장소 import 없음), `cr08`(need 재현, `retract_dead` import), `cr09`(⑪b 기대값, 저장소 import 없음)가 이 판의 수치 근거다.
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
| $M^{ret}$ | (판 4) 수축 뒤 잠금 시작 후보 $\max(13+p_h/3, p_{ret}, \hat p+\delta_m)$(R5-7) | bar |
| $F_{lb}$ | 대체 하한 $p_hA_h-\hat p_{used}A_{ann}$ | kN |
| $t_{B1}$ | 관문 열림 연속 ODE 시각(T-JR-03) | ms |

## 13. 판 4a 덧붙임(2026-11-16, 사례 재생 전; 기준 판 4.1 sha256 `f2f7dfadabe8588589b52318b751b1cdb71e2eeab132519e408e35703a24ec96`)

판 4 실행 전 감사(`audit-jp3r4\report.md`)와 사용자 결정 153을 반영한다. 이 절은 앞 절의 고정 문장(판 3 5.3·5.4절, 판 4 5.7절 P4-1~P4-6, 판 4.1 P4-7~P4-9)을 고치지 않는다. 앞 절과 이 절이 다르면 **이 절이 우선**하고, 차이를 판정서에 적는다.

### 13.1 기준선 고정(B1, 결정 153)

- 5.7절과 J4-9의 비교 기준 "`221456d` 출력"은 앞으로 **깨끗한 `221456d` 체크아웃으로 다시 만든 기준선**을 뜻한다. scratchpad `jp3\cases2`·`cases3`는 커밋 전 작업 트리 출력이라 기준선이 아니다(identity: git.head `abbda97`, `is_clean` false; 그 뒤 수정 파일 5개).
- 기준선: 폴더 `06_analysis\02_control\j_p3_cause\baseline_221456d\`, 목록 파일 `baseline_221456d\SHA256SUMS`.
  - **목록 파일 sha256 = `197ac14e96822130ba4eee98486be6ba9646c207ed1a27936c275077b3a60361`**
  - 이 값을 채운 판이 봉인 대상이다. 채우기 전에는 5.7절 P4-1·P4-2·P4-4·P4-5와 13.3절 예측을 판정하지 않는다.
- 기준선은 다음을 포함해야 한다. 각 결과 파일의 identity는 `git.head` `221456d`, `is_clean` true여야 한다.
  - `run_v5 j9_cases` 15행
  - `jp3_case_replay.py`의 C·D
  - 13.8절 사례 F 행 — **메인 정오(2026-11-16)**: 221456d에는 F 실행 경로가 없어 이번 기준선에 없다. 13.8절 F-E 대체 문장(기준선에 없으면 기록)을 적용한다.
  - 반례 갈래 행(13.3절, 시험 상수 실행이라 별도 하위 폴더와 설정 이름) — **메인 정오(2026-11-16)**: 이번 기준선에는 `fresh_stretch`만 켠 `lsj4_fresh_stretch` 행(래퍼 실행, −10.674 bar)이 있다. 221456d에는 R5-7이 없어 판 3 동작과 같다. `fresh_stretch`+`model_only` 갈래는 재구현 뒤 13.3절 P4-5a로 판정한다. 검토 근거 스크립트·요약(`cr*`, `cases*_summary.txt`, `cd3_summary.txt`, `suite_summary.txt`)은 `review_evidence/`에 보존했다.
- P4-1의 해시 목록(앞 12자)은 커밋 전 트리 값이다. 비교는 **기준선의 값**과 한다. 목록과 기준선이 다르면 기준선이 우선이고, 차이를 판정서에 "커밋 전 트리 대 221456d 차이"로 기록한다(멈춤 아님). 기준선끼리 비교해서 다르면 P4-1대로 멈춘다.
- 비교 스크립트(J4a-9)는 다음을 assert한다. 하나라도 어기면 판정 불가로 멈춘다.
  - 기준선 `SHA256SUMS`의 sha와 파일별 해시
  - 짝 행의 `jp3_t_s` 길이와 값이 같음
  - 판정 행 수 > 0
  - 클래스별 읽기 수 > 0(LOCK·HOLD·CARRY_ext·CARRY_ret·EXT)

### 13.2 판정 행 0 = 판정 불가(B2, 결정 153)

> "J-P3(436.9) 판정에서 판정 행(6.1절: VBJ·LSJ의 normal 등급 이하 행)이 0개이면, 판정 키의 합과 무관하게 **판정 불가**(`no_judged_runs`)로 보고하고 멈춘다. 결함 행이 있으면 결함이 우선한다. T-JR-12처럼 판정 행 수가 정해진 묶음에서는 그 수와 다르면 판정 불가다."

- 구현: `j_p3_judgement_rev5`의 상태에 `no_judged_runs`를 더한다(지금은 `runs_judged == 0`이어도 `pass`, `extend_start_bound.py` 1605~1625행). 판정 도구 두 경로 모두에 넣는다.

### 13.3 반례 갈래(M1, R4, 결정 153)

- R5-7은 **조건 없이** 적용한다(A5, 2.10절). 그래서 `fresh_stretch`만 켜면 R5-7 후보($\hat p+\delta_m$, LSJ4 FL 48.8~48.9 s의 $\hat p$ ≥ 132 bar)가 49.0 s HOLD ④를 덮는다. 따라서 반례 ⑪은 재현되지 않는다. P4-5와 T-JR-04 사례 ⑪의 "`fresh_stretch`" 갈래는 이 점을 빠뜨렸다.
- **판 4a의 반례 갈래 정의**: `fresh_stretch`와 `model_only`를 **함께** 켠다. 이것이 판 3 rev 5 동작(= `221456d` 동작)이다. P4-5 원문은 그대로 두고 아래 P4-5a로 대신 판정한다.
  - **P4-5a**: 반례 갈래(두 시험 상수, 설정 이름 `LSJ4_X11`, 별도 하위 폴더)로 E LSJ4를 돌린다. 기대: 명령 해시는 기준선 LSJ4와 같고, FL 49.0 s HOLD 읽기에서 J-P3b 허용 초과 1건이 나온다. $p_{tr}$ − ④는 기준선에 같은 갈래 행이 있으면 그 값 ± 0.05 bar, 없으면 +10.674 bar ± 0.05 bar(커밋 전 트리 `cases_summary.txt` 100행의 값)다. 어기면 멈추고 원인을 본다.
  - T-JR-04 사례 ⑪의 `fresh_stretch` 갈래도 두 상수를 함께 켠다. 기대 "HOLD 첫 읽기 ④ = 수축 모델이고 초과 > 0.6 kN/$A_{ann}$"는 그대로다.
  - `fresh_stretch`만 켠 갈래는 기록용으로만 돌린다. 기대는 "재현 안 됨(J-P3b 위반 0)"이고, 판정은 하지 않는다.

### 13.4 P4-3 범위(M2)

- **P4-3a**(P4-3을 대신함): "J-P3a·b·c 판정 키는 VBJ·LSJ1~4에서 모두 0이다. **재잠김 1 bar 초과 0은 VBJ·LSJ1~4에만 적용한다.** VBH·LSH의 jp3b 허용 초과와 재잠김 계단은 기록이다."
- 이유: 옛 플랜트(P2 없음)의 VBH·LSH1~4는 기준선(커밋 전 트리)에서도 재잠김 1 bar 초과가 36·35·36·35·34건이다. 이것은 r5 앵커 계단(9.9절 플랜트 산물)이고 판정 대상이 아니다.

### 13.5 자동 진행 범위(M3, 결정 152·153)

> "판 4a 봉인 → 재구현 → 단위 시험 → 사례 재생 A~F → T-JR-10~15 → j9_main까지는 각 관문을 통과하면 자동으로 진행한다. **436.9 규칙 봉인과 436.9 본 실행 전에는 사용자에게 다시 확인한다.** 관문 하나라도 실패하거나 판정 불가(13.2절)이면 멈추고 보고한다."

### 13.6 정체성 기록(M4)

- jsonl `hydraulics_record.extend_bound_check`(rev 5 행)에 다음을 복사한다. 지금은 T4h npz `meta_json`에만 있다.
  - `spec_edition`: 봉인된 판 4a의 sha256 앞 8자. 코드 상수 `JP3_SPEC_EDITION`이고, 메인이 봉인 뒤 값을 넘긴다.
  - `carry_end_rule`
  - `retract_start_rule`
- 판정 도구와 J4a-9 비교 스크립트가 기본값이 아닌 행(`fresh_stretch` 또는 `model_only`)을 판정 집합에 받으면 `setting_defect`로 거부한다. 시험 상수 실행은 별도 설정 이름(`*_X11`)과 별도 하위 폴더로만 만든다.
- `spec_edition`이 봉인 값과 다른 rev 5 행도 `setting_defect`다(옛 판 코드의 출력이 섞이는 것을 막는다).

### 13.7 시험 상수와 검사(M5)

| 상수(`extend_start_bound.py`, 모듈 수준, 기본 False) | 허용하는 값 | 검사 |
|---|---|---|
| `ALLOW_FRESH_STRETCH_FOR_TEST` | `carry_end_rule = "fresh_stretch"` | `ExtendStartBound.__post_init__`: 상수가 거짓인데 이 값이면 `ValueError` |
| `ALLOW_MODEL_ONLY_RETRACT_START_FOR_TEST` | `retract_start_rule = "model_only"` | 같음 |

- pickle 복원은 `__post_init__`을 거치지 않는다. 그래서 같은 검사를 `ExtendStartBound.check_allowed()`로 빼고, 다음 두 곳에서도 부른다.
  - `TwoPressureMonitor` 생성
  - `ensure_hold_state` 등 rev 5 상태를 다시 여는 곳
- `HydraulicOptions`·CLI·프리셋에는 두 값을 고를 경로를 두지 않는다.
- T-JR-02에 다음을 더한다.
  - 두 값을 상수 없이 만들면 `ValueError`
  - 상수를 켠 뒤 만든 pickle을 상수를 끈 프로세스에서 복원하면 `ValueError`
  - `to_dict`/`from_dict` 왕복에서 두 값을 받지 않음

### 13.8 사례 F(M8, 결정 153)

- 작업 추가: `grid_r67_top` FR 행(offset 0.075, ready, 8.0)을 VB·LS1~4(A), VBH·LSH1~4(B), VBJ·LSJ1~4(E)로 돌리는 배치 `j9_case_f`(J4a-14).
- **결과 전 고정 예측**
  - **F-A**: 저장값과 같다(5.3절 F 행; `grid_r67_top` results[13].runs[3] FR 3 / −0.900 bar @ 48.7 s).
  - **F-B**: 명령 해시가 F-A와 같다(T8). VBH J-P3a 위반 0. LSH 행은 기록이다.
  - **F-E**: VBJ·LSJ1~4의 J-P3a·b·c 판정 키가 0이고, 재잠김 1 bar 초과가 0이다.
    - F-E 명령 해시는 판정하지 않는다. 기준선에 F-E 행이 있으면, 판 4a 재구현 출력과 해시가 같아야 하고(P4-1과 같은 T8 논리) 읽기별 사용 상계가 기준선 이상이어야 한다(P4-2와 같음). 기준선에 없으면 해시와 상계를 기록만 한다.
- 어기면 멈춘다(F-A·F-B는 회귀 결함, F-E는 J-P3 실패 또는 T8 결함).

### 13.9 T-JR-12 판정 문장(M6, 결정 153)

> "T-JR-12(Dg-3, 135키): 짝은 VBH 대 저장 H-6(rev 4)와 VBJ 대 VBJ0 두 묶음이고, 각 묶음의 짝 수가 정확히 135이며, J-P3 판정 행(normal 등급 L2)이 정확히 1이어야 한다(아니면 판정 불가로 멈춤). 실패 판정: L2 통과 → 실패 0, 새 FAULT 0, 첫 READY +30 s 초과 0. **READY에 닿지 못한 행(시간 초과·FAULT·중단 포함)은 '+30 s 초과'로 세어 실패로 본다.** 짝 행 하나라도 결과가 없으면 판정 불가다. 5.5절의 기록 열(판 4.1의 `retract_tracker_*` 포함)은 판정과 별도로 낸다."

- 배치와 판정 도구가 아직 없다(`run_v5.py`에는 `j9_main`·`j9_cases`뿐이고, `h6_judge_4368.py`는 rev 5를 NOT_JUDGEABLE로 둔다). J4a-15로 만든다.

### 13.10 레코드 회귀의 skip(M7)

- T-JR-01 "기존 시험 전부 통과"에서 다음 skip 3건은 **통과가 아니라 미실행**이다.
  - `test_v5_setting_records::test_p3_hash_batch_is_the_22_cases_of_revision_8`
  - `::test_rebuilt_allowance_replays_the_dg3_lower_readings`
  - `::test_p3_records_replay_with_their_own_setting`
- 주 체크아웃의 저장 레코드를 가리키게 해서(환경 변수 또는 경로 인자) 실행한다. 실행하지 못하면 T-JR-01 보고에 "skip 3 = 미실행"으로 적는다. 이 경우 T-JR-01은 관문을 통과하지 못한 것으로 보고 멈춘다.

### 13.11 기록 사항(R1, R7)

- **R1 예측 분류**: 판정서에서 **"적중"은 P4-2와 P4-6에만** 쓴다. 둘은 결과에서 독립인 사전 예측이다(단조성, `cr09` 독립 적분). 그 밖의 항목(P4-1·P4-3a·P4-4·P4-5a·P4-7~P4-9, F-A·F-B·F-E)은 "**회귀 대조 일치**"로 쓴다.
- **R7 옛 rev 5 기록의 재생**: `t4h_replay.py`·`chrono_t45_replay.py`는 meta에서 설정을 다시 만든다. `221456d` 시대 rev 5 기록에는 `retract_start_rule`이 없으므로, 판 4a 코드에서는 기본값 `with_tracker`로 재구성된다. 그 결과 저장 meta와 달라 **재생이 거부된다.** 이것은 의도한 동작이다. 옛 기록을 새 규칙으로 조용히 다시 해석하지 않기 위해서다.
  - 옛 기록은 기준선 비교(저장 출력끼리)에만 쓴다.
  - 옛 기록을 굳이 재생해야 하면, 시험 상수를 켠 명시 옵션(`--retract-start-rule model_only`, 별도 출력 폴더)으로만 한다. 그 결과는 판정에 쓰지 않는다.
- **R6**: `j_p3_inputs.py` 55행의 `startswith(("VB", "LS"))`는 `VBG4`·`VBG5`·`*_X11`도 ③ 행으로 잡는다. 13.6절의 `setting_defect` 검사로 막고, 시험 설정 이름은 판정 도구의 설정 목록에서 뺀다.
- **R9**: `_lock_start_model_Pa` 자체를 고치면 R5-2 후보에도 $\hat p$가 들어간다(이중 적용). 그래서 R5-7은 별도 함수로만 둔다. T-JR-05 (k)가 이를 확인한다.
- **M10**: 판 4a를 기준선 sha로 채운 뒤, integrity 점검을 거쳐 `.sha256`과 함께 커밋한다. 그 다음에 재구현 출력을 만든다. 순서는 메인이 맡는다.

### 13.12 재구현 목록 J4a(python-expert; 4.5절 J4-1~13을 대신함)

| # | 항목 | 근거 | 확인 |
|---|---|---|---|
| J4a-1 | R5-6 고정. `fresh_stretch`는 `ALLOW_FRESH_STRETCH_FOR_TEST`로만 받는다. meta에 `carry_end_rule` | J4-1, 13.7 | T-JR-02, T-JR-05 (h)(i) |
| J4a-2 | R5-7 별도 함수 `_retract_lock_start_model_Pa`. 적용 두 곳(RET·CARRY_ret 이동 시작값, `last_sign < 0` 창 후보), 조건 없음(A5), 비적용 두 곳(R5-2 HOLD 후보, CARRY_ret 운반 후보). `retract_start_rule`은 `with_tracker`이고, `model_only`는 `ALLOW_MODEL_ONLY_RETRACT_START_FOR_TEST`로만 받는다 | J4-2, 2.10, 13.7 | T-JR-05 (j)~(m), T-JR-04 ⑪b·⑪b-P1 |
| J4a-3 | 시험 상수 검사: `__post_init__`과 `check_allowed()`(모니터 생성·복원 경로), CLI·옵션 경로 없음 | M5, 13.7 | T-JR-02(거부·pickle·왕복) |
| J4a-4 | 후보 출처 `RETRACT_TRACKER`를 기존 표 끝에 더한다 | J4-3 | T-JR-18 |
| J4a-5 | per-read 4열(`jp3_model_bound_source`·`_age_s`·`_head_Pa`·`_inherited`)과 `trace_excerpt` 열 | J4-4 | T-JR-18 |
| J4a-6 | `p1_retract_seed_log`, `carry_log`. T-JR-15 시드 순 힘 연속 결과 보고 | J4-5 | T-JR-15, T-JR-18 |
| J4a-7 | T-JR-12 기록 `retract_tracker_dominated_reads`, `retract_tracker_stretch_log`, T4h `jp3_ret_after_gate_s` | J4-13 | P4-9 |
| J4a-8 | 정체성 복사: `extend_bound_check`에 `spec_edition`(상수 `JP3_SPEC_EDITION`), `carry_end_rule`, `retract_start_rule`. 판정 도구 두 경로와 J4a-9가 기본값이 아니거나 `spec_edition`이 다른 행을 `setting_defect`로 거부 | M4, 13.6 | T-JR-02, 판정 도구 시험 |
| J4a-9 | 기준선 비교 스크립트: `SHA256SUMS` sha·파일 해시 확인, 명령 해시(P4-1), 읽기별 사용 상계 ≥ 기준선(P4-2), `jp3_t_s` 길이·값 같음, 판정 행 수 > 0, 클래스별 읽기 수 > 0 assert | J4-9, B1, 13.1 | 5.7절, 13.3·13.8 |
| J4a-10 | `j_p3_judgement_rev5`에 `no_judged_runs`(판정 행 0 = 판정 불가), 두 경로 | B2, 13.2 | 판정 도구 시험(빈 선택 → `no_judged_runs`) |
| J4a-11 | T-JR-03 149 ms(허용 0)와 연속 ODE 구간. T-JR-06 경로 B 160.16 ms(VN 배수 포함), 하한은 로드 체크 해제 시각, 35.2 bar 사례 함께 | J4-6·7 | T-JR-03·06 |
| J4a-12 | T-JR-04 사례 ⑪(반례 갈래 = 두 상수 함께)·⑪b(훅)·⑪b-P1(유압 `hr11` 모형), T-JR-05 (h)~(m), T-JR-18 | J4-8·11·12, 13.3 | P4-5a·P4-6·P4-7·P4-8 |
| J4a-13 | 반례 갈래 실행: 설정 이름 `*_X11`(두 상수), 별도 하위 폴더, 판정 도구 설정 목록에서 제외 | M1, M4, 13.3 | P4-5a |
| J4a-14 | 사례 F 배치 `j9_case_f`(A·B·E 15행), 기준선에도 같은 행 | M8, 13.8 | F-A·F-B·F-E |
| J4a-15 | T-JR-10~15 배치·판정 도구: T8 짝(VBH 20/20·22/22, VBJ 대 VBJ0 20/20), T-JR-12(VBH 대 H-6, VBJ 대 VBJ0, 짝 135 assert, 판정 행 1 assert, READY 미도달 = 실패, 결과 없는 짝 = 판정 불가), T-JR-13~15 | M6, 13.9 | 13.9 문장 |
| J4a-16 | T-JR-01 레코드 회귀 skip 3건을 주 체크아웃 레코드로 실행. 못 하면 "미실행"으로 보고하고 멈춘다 | M7, 13.10 | T-JR-01 |
| J4a-17 | 기존 실패 2건: `test_d8x_diag`(master에서도 같은 해시, 무관), `test_chrono_t45_replay`(master 확인 뒤 예외로 기록) | J4-10 | T-JR-01 |
| J4a-18 | `t4h_replay`·`chrono_t45_replay`: 옛 rev 5 meta(`retract_start_rule` 없음)는 거부. 명시 옵션 `--retract-start-rule model_only`(시험 상수, 별도 폴더)일 때만 재생 | R7, 13.11 | 재생 도구 시험 |

## 부록 A. 436.9 판정서 초안 자리의 공개 문장(결정 152)

> **판 4a(M9, 결정 153)**: 판정서에는 아래 A.1(판 4 원문)이 아니라 **A.2 정정본**을 쓴다. A.1은 기록으로 남긴다.

### A.2 정정본(판 4a, 판정서에 둘 문장)

> "436.9 사례 재생에서 판 3 5.3절의 사전 고정 예측 가운데 C(P1만 + rev 4)·D(P1만 + rev 5)의 수치 예측과 E의 $p_{tr}$ 대역, 5.4절 12행(수축 시드 계단)이 실측과 달랐고, 결정 96 멈춤 조건에 따라 멈췄다. 이 재생은 커밋 `221456d` 전의 작업 트리(git.head `abbda97`, 커밋되지 않은 변경 있음)에서 돌린 것이다. 예측은 판 3(sha `dfb289ad…`) 그대로 두며 고치지 않는다. 수치 예측이 어긋난 원인은 예측 전제다: C·D·E의 수치 예측은 436.8의 미세 반전 명령 순서(RR 48.7~49.0 s 작용 명령 −0.0019~+0.0749 mm/s, 49.0 → 49.1 s 4.71 mm/s 신장)가 P1을 켠 플랜트에서도 다시 나온다고 가정했으나, P1이 미세 명령 해제를 없애 폐루프가 그보다 앞서(48.4 s 헤드 57.5 대 62.7 bar) 갈라졌고, 48.7~49.0 s 명령은 $u_{hold}$를 넘는 수축(−0.26~−0.59 mm/s)이 되었다. 판 3 5.3절 C·D 행에는 이 조건을 적지 않았다(E 행에만 있음). 이는 명세 작성자의 표기 누락이다. C는 관문 없는 rev 4가 P1의 지연 해제 뒤 갇힌 압력을 놓치는 기전을 재현했고(해제 49.093 s 뒤 첫 신장 읽기 49.2 s, RR −4.19 bar·FL −3.56 bar), D는 같은 플랜트에서 위반 0이며 그 읽기의 간격은 +161 bar다. 수축 시드 계단 예측 +19 bar는 $p_h$ 77 bar 운전점의 예시 값이었고, 실측 최대 +33.9 bar는 RL $p_h$ 120.5~120.9 bar·잠긴 $p_r$ 바닥에서의 시드다. 다만 같은 재생은 **판 3 2.1절 규칙의 결함**을 드러냈다. 관문이 열리지 않은 운반이 잠금·hold로 끝날 때 새 구간이 운반 후보를 버리는 것이다(반례 ⑪). **판 3 규칙대로라면 LSJ4 FL 49.0 s에 J-P3b 허용 초과 1건($p_{tr}$ − ④ = +10.674 bar)이 나와 J-P3 불일치(H-7)가 된다.** E 다섯 설정의 판정 키 0은 구현자가 이 결함을 막으려 넣은 상속 규칙 아래의 값이다(판 4에서 R5-6으로 채택). 따라서 C·D·E 수치 예측의 불일치 자체는 설계 결함 때문이 아니지만, 판 3 규칙에는 결함이 하나 있었고 판 4에서 고쳤다. 또한 결과를 본 뒤 시험 기준 두 개를 바꿨다: T-JR-03 관문 시각(148 ± 1 ms → 149 ms 허용 0; 판 3 기준으로도 통과)과 T-JR-06 해제 시각('0.1 s 안' → 헤드에 따른 닫힌 식 구간; 판 3 기준이면 헤드 87 bar 사례의 152 ms는 불합격). 판 4a의 사례 재생은 깨끗한 `221456d`로 다시 만든 기준선(목록 sha `197ac14e96822130ba4eee98486be6ba9646c207ed1a27936c275077b3a60361`)에 대해 결과 전에 고정한 예측(명령 해시 같음, 읽기별 상계가 기준선 이상, J-P3 판정 키 0)으로 다시 판정한다."

- 함께 적을 사실(각주)
  - ④ 예측 64~78 bar는 가정 $M_j$ = 13 bar의 값이었다(실측 VBH 49.1 s 185.95 bar, 보수 쪽).
  - 2.4절 need 1.24 mm는 유압 검토 3.4절 비용 칸이 플랜트 공칭 입력 값을 옮긴 표기 오류였다(보수 입력으로 2.315 mm).
  - 반례 ⑪b(관문이 열린 짧은 수축 뒤 hold)는 판 4 R5-7로 막았다(유압 검토 11.1절: 가벼운 다리 최대 전방 +27.4 bar).
  - 판정서에서 "적중"은 P4-2·P4-6에만 쓴다(13.11절).

### A.1 판 4 원문(기록, 판정서에 쓰지 않음 — 아래 판 4 본문 그대로)

아래 문장은 `jp3_impl_review.md` 3.4절의 문장을 그대로 옮긴 것이다. 436.9 하네스 판정서 초안의 "사례 재생 예측 불일치" 자리에 둔다.

> "436.9 사례 재생(구현 `221456d`)에서 판 3 5.3절의 사전 고정 예측 가운데 C(P1만 + rev 4)·D(P1만 + rev 5)의 수치 예측과 E의 $p_{tr}$ 대역, 5.4절 12행(수축 시드 계단)이 실측과 달랐고, 결정 96 멈춤 조건에 따라 멈췄다. 예측은 판 3(sha `dfb289ad…`) 그대로 두며 고치지 않는다. 원인은 예측 전제다: C·D·E의 수치 예측은 436.8의 미세 반전 명령 순서(RR 48.7~49.0 s 작용 명령 −0.0019~+0.0749 mm/s, 49.0 → 49.1 s 4.71 mm/s 신장)가 P1을 켠 플랜트에서도 다시 나온다고 가정했으나, P1이 미세 명령 해제를 없애 폐루프가 그보다 앞서(48.4 s 헤드 57.5 대 62.7 bar) 갈라졌고, 48.7~49.0 s 명령은 $u_{hold}$를 넘는 수축(−0.26~−0.59 mm/s)이 되었다. 판 3 5.3절 C·D 행에는 이 조건을 적지 않았다(E 행에만 있음). 이는 명세 작성자의 표기 누락이다. 설계 결함의 증거는 없다: C는 관문 없는 rev 4가 P1의 지연 해제 뒤 갇힌 압력을 놓치는 기전을 재현했고(해제 49.093 s 뒤 첫 신장 읽기 49.2 s, RR −4.19 bar·FL −3.56 bar), D는 같은 플랜트에서 위반 0이며 그 읽기의 간격은 +161 bar다. E는 다섯 설정 모두 J-P3a·b·c 판정 키 0, 재잠김 1 bar 초과 0이다. 수축 시드 계단 예측 +19 bar는 $p_h$ 77 bar 운전점의 예시 값이었고, 실측 최대 +33.9 bar는 더 높은 헤드(약 110~125 bar, 추정)의 시드로 설명된다. 같은 재생에서 판 3이 정하지 않은 규칙 공백 하나(관문이 열리지 않은 운반이 잠금·hold로 끝날 때 운반 후보 소실, 반례 ⑪)가 드러났다. 이를 판 4 규칙 R5-6으로 고쳤고, 판 4의 사례 재생은 새로 고정한 예측(명령 해시가 `221456d`와 같고, 읽기별 상계가 `221456d` 이상)으로 다시 판정한다."

- 함께 적을 사실(판정서 본문 또는 각주): ④ 예측(64~78 bar)은 가정 $M_j$ = 13 bar의 값이었다(실측 VBH 49.1 s 185.95 bar, 보수 쪽). 2.4절 수축 need 1.24 mm는 플랜트 공칭 입력의 값이었다(보수 입력으로 2.315 mm, 1.87배, 보수 쪽). 둘 다 합격 판정에 영향이 없다(5.6절).
- (판 4.1) 위 문장의 "약 110~125 bar, 추정"은 유압 검토 11.2절에서 확인됐다: 최대 사건은 RL $p_h$ 120.5~120.9 bar, 잠긴 $p_r$ 바닥이다. 문장은 결정 152대로 그대로 두고, 판정서에는 이 확인을 각주로 붙인다. need 1.24 mm의 출처는 유압 검토 3.4절 비용 칸의 표기 오류였다(11.3절).
