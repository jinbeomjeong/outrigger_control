# v5 유압 연성 구현 명세 (2026-11-06, 개정 3)

> **2026-11-07 주의**: M2 법칙은 개정 4(`flow_limited_r4`, 뜬 다리 해제 이중 계산 제거, 코드 f8c08cc)로 바뀌었다. 원본은 `06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev5.md` 3절(식·M2-14/14b/14c·실측)이고, 아래 본문의 `flow_limited_r3` 서술은 개정 4 반영 전 문구다(본문 개정 예정).

작성: hydraulics-expert. 구현: python-expert. 기준 코드: master e747d8c(`final_C4G2`). 이 문서는 코드를 고치지 않았고 새 시뮬레이션도 돌리지 않았다. 수치는 저장 결과와 수계산이다. 결정 원문은 `decision_log.md` 4절 줄 286~349.

**개정 1**(사용자 결정): D-1 넣음, D-2 그대로 두고 한계 기록, D-3 하네스 판정 뒤 결정, D-4 양방향, D-5 $\eta_v$ 0.85, D-6 BL + LC 거부. 그래서 오버랩·체크 닫힘(LC, 2.5절)과 제어기 쪽 요구(2.6절)를 더했고 시험·건수·커밋 순서를 다시 계산했다.

**개정 2**(사용자 결정 2026-11-06, `decision_log.md` 4절 v5 구현 줄): M2-6 기준을 **정착값**으로 바꿨다. 옛 기준 4.13~4.25 kN은 정지 1 s 뒤(t = 3.0 s) 순간값이고, 그 시각은 ζ 약 0.01의 로킹 진동(2.95 Hz) 한가운데라 위상에 따라 값이 달라진다. 세 기준 모델을 정지 뒤 30 s까지 다시 돌린 정착값은 Hopsan 2.344, numpy 2.401, 3자유도 법칙 + M2 2.433 kN이고 하네스 2.436 kN(dynamics-expert)과 함께 2.43 ± 0.25 kN 안이다(3.1절 M2-6 아래 표). 같은 개정에서 2.4절에 `shift_head` S7 정확식, $r_s>1$ 마찰 띠 한계, 시험 C-10을 더했다. 개정 2는 hydraulics-expert가 새 기준 실행(scratchpad, 아래)을 돌렸다. 봉인 기준 `v5_criteria.md`는 고치지 않았다(개정 절은 control-expert가 따로 쓴다).

**개정 3**(사용자 결정 2026-11-06, `decision_log.md` 4절 M2 물리 판단·개정 3 구현 줄): M2의 이동 중 로드 압력 변화를 **밸브 유량으로 제한**한다(법칙 이름 `flow_limited_r3`, P-A, B 호스 미포함). 이유: 고정 τ 0.05 s 법칙은 반전마다 유량과 무관하게 로드 압력을 세워 0.33~0.38 mm를 첫 제어 주기에 옮겼고, 미세 명령(1 % $v_{max}$ 아래)에서는 채울 체적이 맞지 않았다(1단계 J8 반복의 원인, control-expert 진단). 2.3절 법칙·식·기호, 2.0절 LC 닫힘 문장, 2.5절 $t_c$ 행, 3.1절 M2-1·M2-2·M2-6 실측과 새 시험 M2-9~13, 5절 한계 4건을 고쳤다. 구현은 master b85f58c·76802c8·a90a303·e4e80f9(python-expert)이고 수치는 그 시험 실측이다. 판정 기준은 봉인 `v5/v5_criteria_rev4.md`이고 이 문서에서 고치지 않는다. M2 끈 실행은 비트 동일이다(B-2 23/23). 법칙 근거 계산은 hydraulics-expert scratchpad `hyd_m2fix/`(`calc.json`, `law.json`, `hopcmp.json`, `m2fix.py`, 보존 보장 없음).

**범위**: 펌프 유량 포화 + 밸브 지연(오버랩·체크 닫힘 포함) + M2(로드 압력 힘). M1c는 기본 끔 옵션. 두 챔버 압력 동역학, D-5 전환, M1c 수정, G4·불감대 제어기 대응, RL 약점 대응은 하지 않는다.

**핵심 회귀 조건**: 플랜트 옵션과 제어기 옵션을 하나도 주지 않은 실행은 `final_C4G2`와 비트 동일하다. 논문 v4 값은 불변이다.

압력은 따로 적지 않으면 **게이지**다. 작동유는 ISO VG 46, 50 °C, $\rho$ 860 kg/m³, $\nu$ 32 mm²/s, $\beta$ 1.0 GPa(**가정**, YAML).

## 1. 현재 구현 목록

| 항목 | 상태 | 근거(파일:줄) |
|---|---|---|
| 유량 분배 식 | **03_src 있음** | `hydraulics/flow_share.py:241` `share_flow`, `:301` `PumpFlowLimiter` |
| 유량 제한 기록·CLI | **03_src 있음** | `hydraulics/flow_limit_run.py:93` `FlowLimitSetting`, `:124` CLI, `:194` `RecordedFlowLimiter` |
| 유량 제한 플랜트 연결 | **03_src 있음** | `actuation.py:185`·`:417`·`:437`, `chrono/actuators.py:369`·`:803`, `chrono/l2b_actuator.py:435` |
| 유량 켬 Chrono 경로 | **스크립트 있음** | `run_S8C.py:1458-1463`(L2b 행만, `:2939`), `run_S9.py:5625-5630`, `s9_batch.py:242-296` `COUPLED_eta085` |
| 유량 하네스 어댑터 | **스크립트 있음** | `04_scripts/04_hydraulic/coupled/harness_flow.py:218`, `verdict_runs.py:57` |
| 밸브 지연(강체 Chrono) | **03_src·스크립트 있음** | `actuation.py:203` `configure_valve`, `run_S8C.py:1122`, τ 0.1 s는 `run_S6C.py:182` |
| 밸브 지연(하네스) | **스크립트 있음(항상 켬)** | `04_scripts/03_control/r8d1/c2py_r8d1_closed_loop.py:69`, `:192` |
| 밸브 지연(토양 Chrono) | **없음** | `run_S9.py`에 `configure_valve` 호출 없음. 명령 램프 경로(`hydraulic_coupling.md` 9절) |
| M2 법칙 | **scratchpad에만** | `scratchpad/hyd_review/m2_check.py:51-55`, 기준값 `pressure_review/m1_m2_reference.json`, `m2_check.json`. 03_src·하네스 없음 |
| M2 기준 회로 스크립트 | **scratchpad에만** | `hyd_review/four_leg.py`, `common.py`, `m2_check.py`, `poc_*.py`, `m1_m2_build.py` (보존 보장 없음, 커밋 1에서 모두 옮긴다. `poc_*.py`, `m1_m2_build.py`는 기록 보존용이고 v5 시험 입력이 아니다) |
| M1c | **스크립트에만** | `04_scripts/03_control/m1_check/m1c_plant.py`, 수축 쪽은 `m1b_plant.py:70` `retract_dead`, `:146` `_void_m`. 03_src 없음. L2b 없음 |
| M1c 단위·폐루프 값 | **저장값(참고)** | `pressure_review/m1c/unit_m1c.json`, `r12.jsonl`, `g4.jsonl`, `main.jsonl`. C4G2 끔 프리셋(1a9b4e6) 값이다 |
| 로드 압력 추적 | **03_src 있음** | `hydraulics/rod_chamber.py:287` 목표, `:518` 1차 지연. `l2b_rod_side.py:431`이 내보냄. 하네스에는 없음(아래 D-2) |
| 인수 판정 틀 | **스크립트 있음** | `m1_check/run_m1.py`(`command_stats`, `event_names`, `state_at_marks`, `_phase_jobs`), `aggregate_m1.py`(`metrics`, `judge_pair`, `effect_table`), 기준 틀 `pressure_review/m1_criteria.md` |
| 체크 닫힘 지연 $t_c$ | **03_src에 기능 있음, 값 0 고정** | `rod_chamber.py:314`·`:466`(시험 `test_rod_chamber.py:426`), `l2b_rod_side.py:138`이 0.0으로 고정. 하네스 없음(`s8_g4_rodside_check.py:111`이 즉시 잠금) |
| 오버랩 꼬리 차단 | **없음** | 제안만 있음(`s8_seal_friction_counterbalance.md` 11.4 2단계) |
| 제어기 잠금 창 | **03_src 있음, 지금 플랜트 규칙** | `two_pressure.py:625`·`:628`, `:2316-2323`. $t_c$ 항은 없음. 쓰는 곳은 대체 다리의 $\hat p_r$(같은 문서 10.4 T8) |
| v5 통합 러너·기준 | **없음** | 이 명세 3절, 기준은 control-expert |

**하네스 환경 주의**: 하네스는 dynamics-dev(numba), L2b는 Chrono-dev, Hopsan 기준은 hydraulics-dev다. 새 03_src 모듈은 numpy만 쓰고 pychrono를 import하지 않는다.

## 2. 항목별 구현

### 2.0 옵션과 적용 순서

새 파일 `hydraulics/v5_options.py`: `HydraulicOptions(flow: FlowLimitSetting | None = None, valve_tau_s: float | None = None, rod_release_force: bool = False, check_delay: CheckDelaySetting | None = None, lock_closure: LockClosureSetting | None = None, lock_window_follows_plant: bool = False)`. **기본값은 모두 끔이다.**

| CLI (`argparse.SUPPRESS`, 없으면 `vars(args)`·meta·결과 불변) | 값 | 비고 |
|---|---|---|
| `--flow-eta-v` 외 기존 5개 | `flow_limit_run.py:124` | 그대로 |
| `--valve-tau-s` (새 옵션, `run_S9`만) | 0.1 | `run_S8C`는 행 정의 값이 이미 있음 |
| `--rod-release-force` (새 옵션) | 플래그 | M2 |
| `--check-delay {VN,BL}` (새 옵션), `--check-delay-volume-scale`, `--check-delay-cv` | 공칭 없음, 1.0, 0.02 | M1c. 앞 옵션 없이 뒤 둘이 오면 `SystemExit` |
| `--lock-overlap-ratio`, `--lock-closing-delay-s` (새 옵션, 함께만) | 공칭 없음(인수 축 0.02, 0.05) | LC 플랜트(2.5절). 밸브 모델 필요 |
| `--lock-window-follows-plant` (새 옵션) | 플래그 | 제어기 창(2.6절). LC 없이 주면 `SystemExit` |

하네스는 `harness_flow.FlowSetting`을 **고치지 않는다.** `run_verdict.definition_digest`가 `asdict(setting)`을 해시하므로(`run_verdict.py:61`) 필드를 더하면 저장 결과가 모두 낡은 것으로 나온다. 별도 인자 `verdict_runs.execute(..., hydraulics=None)`를 두고 digest에는 값이 있을 때만 넣는다(`clip_command` 선례, `:63`).

| 순서 | 하네스(1 ms 조각, 내부 스텝) | L2b(물리 스텝, `hook`) |
|---|---|---|
| 1 | C2 반환 명령(±$v_{max}$ 절단은 C2 안) | 같음 |
| 2 | `_lagged_step` 스텝 평균 속도 | `reference.advance` → `_valve_step` |
| 2a | **LC 꼬리 차단**(`_lagged_step` 안) | **LC 꼬리 차단**(`_valve_step` 바로 뒤) |
| 3 | **M1c** `filter` | **M1c** `filter`(`advance` 안, `flow.limit` 앞) |
| 4 | **유량 제한** `FlowLimitedPlant.step` | **유량 제한** `flow.limit` |
| 5 | 내부 스텝 루프: `_rod_force`(**LC 닫힘 타이머**) → **M2 이동** → 커널(법칙 C, 마찰) | 행정 끝 제동 → 법칙 C → 끝 절단 → $s_{ref}$ 적분 |
| 6 | M1c 지연 이동(`pending_shift`) | 기름 법칙(**LC 닫힘 타이머**, 상태 기계 안) → **M2 이동** → M1c 지연 이동(`shift_reference` + `oil.shift_head`) |

LC 꼬리 차단은 스풀의 성질이라 밸브 바로 뒤에 둔다. 유량 제한은 차단된 다리의 수요를 0으로 본다. 닫힘 타이머 동안 $u=0$이고 법칙은 이동 상태이므로 M2 이동은 잠길 때까지 이어진다. 단 개정 3에서는 유량으로 채우거나 비우는 쪽(수축 승압, 신장 감압)이 $u=0$이라 멈추고, 목표 쪽으로 저절로 가는 쪽($p_{lag}$ 분기)만 이어진다(2.3절).

M1c를 유량 앞에 두는 이유: 저장 러너의 순서(`m1c_plant.py:416-424`)와 같다. 채움 중 다리의 수요가 빠지지만, 네 다리 동시 $v_{max}$ 명령에서 채움은 약 0.059 s(FL)·0.063 s(RL)에 끝나고 $\tau_v$ 0.1 s로 포화 문턱 0.85 $v_{max}$에 닿는 시각은 0.19 s다(수계산). 이 조합의 폐루프 실행은 아직 없다.

L1(`L1SpeedActuator`)에는 M2·M1c를 넣지 않는다. 옵션을 L1 행에 주면 `SystemExit`로 거부한다(`run_S8C.py:2939` 선례).

### 2.1 펌프 유량 포화

코드는 있다. **식 변경 없음.** 할 일은 옵션 통합과 문구 정리뿐이다.

$$Q_i=K_i\sqrt{y_i},\quad v_i=u_i\sqrt{y_i/\Delta p_c},\quad y_i=\operatorname{smin}_w\!\Big(\Delta p_c,\ \frac{(p_P-p_{L,i})X^2}{X^2+K_i^2}\Big),\quad \sum_i Q_i+Q_{byp}=\eta_vQ_{th}$$

| 기호 | 뜻 | 단위 |
|---|---|---|
| $u_i$, $v_i$ | 요청 속도(밸브 뒤), 전달 속도 | m/s (mm/s) |
| $K_i$ | 스풀 계수 $A_i\lvert u_i\rvert/\sqrt{\Delta p_c}$ | m³/s/√Pa |
| $X$ | 보상기 완전 열림 계수 | m³/s/√Pa |
| $p_P$, $p_{L,i}$ | 갤러리, 부하 압력(게이지) | Pa (bar) |
| $Q_{th}$, $\eta_v$ | 펌프 이론 유량, 체적 효율 | m³/s (L/min), - |

| 입력 | 값 | 표시 |
|---|---|---|
| 펌프 | 30 cc/rev × 2,006.7 rpm = 60.2 L/min | YAML |
| $\eta_v$ | **기본값 없음**(옵션 없으면 제한 끔). 인수 축 0.85, S8만 0.90·0.925 기록 있음 | **ASSUMPTION** |
| $\Delta p_c$ / $\Delta p_{LS}$ / $w$ | 10 / 20 / 1 bar(감도 6·20, 12·30, 0.5·2) | **ASSUMPTION** (Q-M4, Q-M5) |
| 분배 법칙 | 사전 보상 우선(대조 비례) | **ASSUMPTION** |
| $p_T$, 파일럿 | 2 bar, 35 bar | **ASSUMPTION** |

**기본값**: `FlowLimitSetting`은 옵션이 있을 때만 생기고 `FlowShareAssumptions.is_enabled` 기본은 False다. **D-5 전환은 하지 않는다**(S8 F-5, 한계 기록). 지울 낡은 문구: `flow_share.py:3-5`·`:84`, `flow_limit_run.py:6-7`의 "D-5 turns it on after v4", "waits for the v4 paper" → "D-5 not switched, S8 F-5 (decision_log 2026-11-05)". 봉인 기준 문서는 고치지 않는다.

`harness_flow.FlowSetting`의 기본값은 `is_enabled=True`, `eta_v=0.95`다(`harness_flow.py:81`). 프로젝트 기본과 다르니 v5 러너는 항상 명시한다.

### 2.2 밸브 지연

법칙은 있다(`actuation.py:279-290`, $u_a\leftarrow u_r+(u_a-u_r)e^{-\Delta t/\tau_v}$, 다리 속도는 스텝 평균). **할 일은 토양 Chrono에 켜는 옵션뿐이다.**

| 입력 | 값 | 표시 |
|---|---|---|
| $\tau_v$ | 0.1 s, `amp_ramp="none"` | **ASSUMPTION** (U-R8-9 ③ 전) |

- 위치: `run_S9.py`에서 settle 뒤가 아니라 `run_S8C.py:1122`처럼 모델 구성 직후 `model.actuator.configure_valve(tau_s=..., amp_ramp="none")`. 옵션 없으면 호출하지 않는다. `set_flow_limit`보다 먼저 부른다.
- 켜면 명령 램프가 꺼지고(`actuation.py:32`) 저장 토양 행과 짝이 아니다. 토양 짝은 **밸브 켬·유량 끔 기준 행**이 따로 필요하다(D-3).
- 제어기 쪽 $\tau$: `two_pressure.LOCK_WINDOW_VALVE_TAU_S`가 이미 0.1 s다(`two_pressure.py:260`). 제어기 값은 바꾸지 않는다.
- 하네스는 항상 지연이 켜져 있어 지연 자체에는 할 일이 없다.
- 오버랩·체크 닫힘은 별도 옵션이다(2.5절, D-1 결정).

### 2.3 M2 수축 뒤 해제 로드 압력 힘

`pressure_review_report.md` 12.4절의 규칙을 쓴다(4절의 $R_0$ 옆 항 식은 쓰지 않는다). 새 파일 `hydraulics/rod_release.py`.

$$\delta s_{ref,i}^{\,k}=\begin{cases}\dfrac{A_{ann,i}\,(p_{r,i}^{\,k-1}-p_{r,i}^{\,k})}{k_{h,i}} & \text{이동 중}\\[2mm]0 & \text{잠김}\end{cases},\qquad \Delta F\big|_{\text{몸체 고정}}=\frac{k_2}{k_h}A_{ann}\,\Delta p_r$$

$$\dot p_r=\frac{p^*-p_r}{\tau},\qquad p^*=\begin{cases}\max(p_{bB},\,-F/A_{ann}) & \text{신장}\\ \min(p_{thr}(F),\,p_{relief}) & \text{수축}\end{cases}$$

| 기호 | 뜻 | 값·단위 | 표시 |
|---|---|---|---|
| $p_r$ | 로드 압력(게이지) | Pa (bar) | 모델 값, 실측 아님 |
| $k_h$ | $\beta A_h/(L_{0h}+s_{ref})$. 하네스는 `plant.kh`(e_op 고정) | N/m | YAML + **ASSUMPTION** $\beta$, $L_{0h}$ |
| $k_2$ | $k_h$와 $k_{out}$ 직렬 | N/m | |
| $\tau$ | `actuator.rod_side.release_tau_s` | 0.05 s | **ASSUMPTION** |
| $p_{bB}$ | 신장 이동 배압 목표(`rod_chamber.py:195`) | 5 bar | **ASSUMPTION**. 두 챔버 3.1~3.8 bar보다 높다 |
| $p_{r0}$ | 수축 뒤 잠금 압력 | 30.6~34.8 bar | **ASSUMPTION** YAML |

위 $\dot p_r$ 식은 옵션 없는 L2b 추적 압력과 개정 2까지의 M2가 쓰던 1차 지연이다. **개정 3(`flow_limited_r3`, 사용자 결정 2026-11-06)**: M2를 켜면 이동 중인 다리의 로드 압력은 목표 $p^*$로 1차 지연하되, 밸브 유량이 로드실을 채우거나 비우는 속도를 넘지 못한다. 잠긴 다리는 기존 규칙 그대로다.

$$p_{lag}=p^*+\big(p_r^{\,k-1}-p^*\big)e^{-\Delta t/\tau}$$

$$p_r^{\,k}=\begin{cases}\min\!\big(p_{lag},\ p_r^{\,k-1}+Q_{in}\Delta t/C_r\big) & \text{수축이고 } p^*>p_r^{\,k-1}\ \text{(미터인 승압)}\\ \max\!\big(p_{lag},\ p_r^{\,k-1}-Q_{out}\Delta t/C_r\big) & \text{신장이고 } p^*<p_r^{\,k-1}\ \text{(미터아웃 감압)}\\ p_{lag} & \text{그 밖}\end{cases}$$

$$Q_{in}=A_{ann}\lvert u\rvert,\qquad Q_{out}=b_TA_h\lvert u\rvert\sqrt{\frac{\max(p_r^{\,k-1}-p_T,\,0)}{\Delta p_c}},\qquad C_r=A_{ann}^2\Big(\frac{1}{k_r}+\frac{1}{k_h}\Big)$$

| 기호 | 뜻 | 값·단위 | 표시 |
|---|---|---|---|
| $p_{lag}$ | 유량 제한 전 1차 지연 값 | Pa (bar) | |
| $u$ | 이 스텝의 전달 속도(밸브 지연·LC 꼬리 차단·유량 제한 뒤 적분 속도). 하네스: `_rod_force(u)`의 커널 속도로 `_closing_delay_speed`가 $2\varepsilon$로 바꾸기 **전** 값. L2b: `RodChamberLegInput.applied_speed_m_s` | m/s | |
| $Q_{in}$, $Q_{out}$ | 로드실 미터인 유량(수축), 미터아웃 유량(신장, A→T 오리피스) | m³/s | |
| $C_r$ | 로드실 유효 컴플라이언스(로드 기름 + 피스톤 이동으로 헤드 기름) | FL 1.80×10⁻¹², RL 1.59×10⁻¹² m³/Pa(운용점) | **ASSUMPTION**: B 호스 미포함(5절) |
| $k_r$ | 로드 기름 강성. 하네스 `plant.kr`(생성 때 한 번), L2b 그 스텝 `rod_stiffness_N_m` | N/m | YAML + **ASSUMPTION** $\beta$, $L_{0r}$ |
| $A_h$ | 헤드 면적 | 1.3273 / 0.9503 ×10⁻² m²(전방 / 후방) | YAML |
| $b_T$ | 같은 스풀 행정에서 미터아웃(A→T) 대 미터인(P→A) 개도 비 | 1.0 | **ASSUMPTION**(`rod_release.METER_OUT_RATIO`) |
| $\Delta p_c$ | 스풀 개도가 $A_h\lvert u\rvert$를 통과시키는 차압(보상기 차압) | 10 bar | **ASSUMPTION**(`SPOOL_REFERENCE_DROP_PA`, 2.1절과 같은 값) |
| $p_T$ | 리턴 라인 압력(게이지) | 2 bar | **ASSUMPTION**(`TANK_PRESSURE_PA`, 2.1절과 같은 값) |

- 세 상수는 모듈 상수다(CLI 옵션 아님, `RodPressureFlowLaw` frozen dataclass). $\tau$, $p^*$, 이동량 식 $\delta s_{ref}$, 잘림·스냅숏·잠김 규칙은 바뀌지 않는다. 새 상태 변수와 스냅숏 키는 없다.
- 자르기는 $p_r^{\,k-1}$ 기준 양해법이고 $p_{lag}$를 넘지 않는다. 이산화: 하네스 내부 스텝 `plant.dt`, L2b 1×10⁻⁴ s.
- $u=0$이면 유량으로 채우는 쪽은 압력이 멈춘다(시험 M2-11).
- 유량 제한 때 몸체 고정 이동 속도는 $r\,u$, $r=k_r/(k_h+k_r)$(FL 0.27)다. 반전당 이동 총량($A_{ann}\Delta p_r/k_h$, FL 0.38 mm)은 같고 시간에 퍼진다. FL 수축 반전의 첫 제어 주기(0.1 s) 이동은 개정 2의 0.33 mm 대신 1 % $v_{max}$에서 0.0056 mm, 25 % $v_{max}$에서 0.14 mm이고 $v_{max}$에서는 제한이 걸리지 않는다(0.38 mm, 승압 0.068 s). 1 % $v_{max}$의 승압(5 → 34.8 bar)은 6.8 s, 감압(34.8 → 5 bar)은 1.6 s 걸린다(수계산 `calc.json`, 운용점 행정 0.4011 m).
- L2b는 같은 객체로 `RodChamberLeg` 추적 압력 자체를 자른다(`_relax_tracked_pressure` 지수 단계 뒤, 마찰 경로의 기름 법칙 G도 같음). 그래서 **M2를 켠 L2b는 로드 압력 진값·판독도 개정 3 값이다.** 하네스는 `_RodPressureLag.relax(leg, direction, force_N, speed_m_s)`가 같은 순수 함수 `flow_limited_rod_pressure`를 부른다(복제 금지, 시험 M2-12).
- M1c와 함께: 개방 때 시드 압력이 이미 목표라 유량 제한이 동작하지 않는다.
- 기록: M2를 켠 실행에만 meta `rod_release.law = "flow_limited_r3"`·상수, 정의 digest에 `m2_law: "flow_limited_r3"`. M2 끈 실행에는 키가 없어 `final_C4G2`·황금값과 비트 동일이다. 저장 옵션의 다른 법칙 값은 `from_dict`가 거부한다. 봉인 기준 개정 4는 `m2_law`가 없는 M2 행을 판정에서 뺀다.

옵션 `rod_release_force`. 기본 끔이면 코드 경로가 돌지 않는다.

| 위치 | 구현 |
|---|---|
| **L2b** | `L2bForceActuator.from_params(..., rod_release=None)`. S7 경로는 `hook`의 `spring_force_N`과 `_force` 계산 뒤(`l2b_actuator.py:523-528`), 마찰 경로는 `refresh_readings` 뒤(`:556`). $p_r$은 `self._oil.rod_pressure_Pa`(바닥 분할 **전** 값). `reference.shift_reference(-delta)`로 다음 훅부터 듣게 한다. 잠김 다리·disarm이면 0 |
| **하네스** | 새 파일 `coupled/harness_hydraulics.py`의 플랜트 서브클래스가 `_rod_force`를 덮어쓴다(`m1c_plant.py:393` 형태). 하네스에는 추적 압력이 없으므로 이 클래스가 위 1차 지연을 직접 푼다. 해제 순간 $p_r=p_{r0}-G_r/A_{ann}$에서 시작하고 목표는 `RodChamberLegParams.moving_target_rod_pressure_Pa`로 구한다(법칙 복제 금지). `self.sref += delta` |

공통 규칙:

- 이동 뒤 $s_{ref}$가 $[lo,hi]$를 넘지 않게 자른다. 넘으면 다음 `advance`의 끝 절단이 $u=(s_{new}-s)/\Delta t$로 큰 속도를 만든다(`actuation.py:457-461`). 잘린 스텝 수를 `m2_clipped_steps`로 기록한다.
- `lock_valve="counterbalance"`와 함께 주면 `ValueError`. CB 경로는 시험한 적이 없다.
- 스냅숏 키 `m2_p_prev_Pa`, `m2_shift_total_m`은 옵션이 켜졌을 때만 쓴다(`FLOW_OPEN_KEY` 선례). 없으면 현재 값으로 시작.
- 기록: 다리별 누적 이동량. **행정 판독과 가드에 영향이 있을 수 있다**: 34.8 → 5 bar에서 FL 0.382 mm, RL 0.434 mm이고, 저장 C4G1 S7의 정지 표본 가드 여유가 0.376·0.424 mm(`decision_log.md:317`)로 같은 크기다.

방향은 **신장·수축 둘 다**다(보고서 규칙, D-4 결정). "수축 뒤 해제"라는 이름보다 넓다. 근거: 로드 압력 $p_r$이 있으면 같은 순 힘을 내는 기름 기둥 압축이 $A_{ann}p_r/k_h$만큼 다르므로 $s_{ref}$ 등가량이 양방향으로 움직인다.

### 2.4 M1c 체크 밸브 열림 지연 (기본 끔, 참고 값)

새 파일 `hydraulics/check_open_delay.py`. **`m1c_plant.py`와 `m1b_plant.retract_dead`, `_void_m`의 VN·BL 경로를 식을 바꾸지 않고 옮긴다.** 수정은 제조사 답까지 멈춘다. meta에 `"unit_status": "below_criteria_reference_only"`를 넣고, 집계 표에도 그대로 옮긴다.

**신장(E1)**

$$x'=\lvert u\rvert-\frac{K_n\,g\,\sqrt{p_A-p_T}}{A_h},\quad g=\Big(1-\frac{\lvert u\rvert}{c_vv_{max}}\Big)_+,\quad p_A=p_T+\frac{xA_h\beta_h}{V_{line}}$$

$$\text{로드 체크 개방: }p_T+\psi(p_A-p_{ref})-p_r-p_{cr}>0,\qquad \text{헤드 체크 개방: }p_A+\psi p_B-p_h-p_{cr}>0$$

개방 뒤 $p_B=\min\big(\frac{C_rp_r+C_lp_T}{C_r+C_l},\,p_r\big)$, $C_r=A_{ann}(L_{0r}+s_{max}-s)/\beta$, $C_l=V_{line}/\beta_h$. 헤드가 열리기 전 전달 속도는 0, 로드만 열렸으면 $1.5\times10^{-6}$ m/s(법칙 해제용)다. 열린 뒤 $v=\max(\lvert u\rvert-\text{drain},\,1.5\times10^{-6})$.

**수축**(`retract_dead` 그대로): 채울 행정 $d_s=[V_{line}(p_B-p_T)/\beta_h+V_r(p_{rod}-p_r)/\beta+A_{ann}V_h\Delta p_h/(\beta A_h)]/A_{ann}+\text{void}$. 채움 중 크리프로 $s_{ref}$가 물러나고, 개방 순간 헤드 방출 $V_{line}(p_h+\Delta p_h-p_T)/(\beta_hA_h)$만큼 이동한다.

| 기호 | 뜻 | 값 | 표시 |
|---|---|---|---|
| $x$ | 라인 상태(행정 단위) | m | 상태 |
| $V_{line}$, $\beta_h$ | 라인 체적, 호스 체적탄성계수 | 285 cm³, 0.5 GPa | **ASSUMPTION** (Q-M9) |
| $\psi$, $p_{cr}$ | 파일럿비, 크래킹 | 3.5, 3 bar | **ASSUMPTION** (V-6) |
| $c_v$ | 환기가 닫히는 스풀 개도 | 0.02(감도 0.01·0.05, R12만) | **ASSUMPTION** |
| $K_n$ | 중립 환기 계수. VN = 전개 랜드 × 0.05, BL = 0 | 전개 랜드 $K=A_hv_{max}/\sqrt{\Delta p_c}$ | **ASSUMPTION** |
| 체적 배율 | $V_{line}$, 로드 챔버, 크리프, 헤드 방출에 곱함(공극 제외) | 1, 0.5 | **ASSUMPTION** |
| $p_{ref}$, $\delta$ | VN: $p_T$, $p_{cr}$. BL: 0, 0 | | **ASSUMPTION** |
| 회로 | `VN` 재충전 없는 환기, `BL` A·B 차단 | | 사용자 결정 |

**제외**: `VR`과 그 전용 경로(`_rod_exchange`, `_update_rod_vent`, E3), `E2`(`_rod_force` 덮어쓰기), `E4`(`_e4_step`), `no_delay`, 진단 `rod_early`.

| 위치 | 구현 |
|---|---|
| **공통 입력** | `CheckDelayInputs(t, dt, u, p_h, p_r, locked, void_m, band_N, s_ref)` → `filter`가 전달 속도, 지연 이동량, 잠금 감쇠 마스크를 돌려준다 |
| **하네스** | `harness_hydraulics`가 `plant`에서 입력을 만든다(`p_r = p_r0 - Gr/A_ann`, `p_h = (pressure() + p_r A_ann)/A_h`, `band = Fs - f`). `plant.cn[i] = C_LOCK[i]`, `c_lock` 이동, `pending_shift` 처리는 저장 코드와 같게 |
| **L2b** | `SpeedReference.set_check_delay(obj)`(기본 None)를 두고 `advance`의 `_valve_step` 다음, `flow.limit` 앞에서 부른다. 입력은 `hook`에서 `advance` 전에 넣는다. `p_h=(F_p+p_rA_{ann})/A_p`(바닥 없이, 하네스와 같게), `band=` 마찰 한계 $-f$(S7 경로 0, $r_s>1$ 한계는 아래 표), `void`는 $dc-dc_{knee}$의 양수 부분. 잠금 감쇠 마스크가 켜진 다리는 $c=c_{lock}$(지금은 $\lvert u\rvert\le\varepsilon$로만 고른다, `:526`·`:558`). 지연 이동은 `shift_reference` + `oil.shift_head`. 잠긴 다리의 앵커 이동은 경로마다 다르다(개정 2, 아래 식) |
| **거부** | 밸브 모델이 꺼진 플랜트(명령 램프)에서 켜면 `ValueError`. 램프 경로에는 `_flow_open`이 따로 있어 시험하지 않았다 |
| **스냅숏** | 옵션이 켜졌을 때만 상태 키를 쓴다 |

**`shift_head` 앵커 이동(개정 2)**: 잠긴 법칙은 $F=F_{lock}+k_2\,dc+(k_1-k_2)\min(dc,\,dc_{knee})$, $dc=c-c_{lock}$, $c=s_{ref}-s$다. 헤드 기름만 $\delta$만큼 빠지는 이동($s_{ref}$를 $\delta$ 낮춤)을 이 법칙에 정확히 옮기면 다음과 같다.

$$\text{S7 경로}(k_{out}\ \text{유한}):\quad c_{lock}\leftarrow c_{lock}-\delta\Big(1+\frac{k_h}{k_{out}}\Big),\qquad F_{lock}\leftarrow F_{lock}-k_h\,\delta$$

$$\text{기름 법칙 G}(k_{out}=\infty,\ \text{CB·마찰 경로}):\quad c_{lock}\leftarrow c_{lock}-\delta,\qquad F_{lock}\leftarrow F_{lock}-k_h\,\delta\quad(\text{위 식의 극한, 기존 CB 식과 비트 동일})$$

| 기호 | 뜻 | 단위 |
|---|---|---|
| $\delta$ | 헤드 방출 체적 / $A_h$ (M1c 개방 이동) | m |
| $k_h$, $k_r$, $k_{out}$ | 헤드 기름, 로드 기름, 외부 경로(패드·구조) 강성 | N/m |
| $k_1$, $k_2$ | 무릎 아래(로드 스프링 병렬) / 위 잠김 강성 | N/m |
| $c_{lock}$, $F_{lock}$ | 잠금 순간 앵커 압축, 힘 | m, N |

- 몸체 고정 힘 감소: 무릎 아래 $k_hk_{out}\delta/(k_h+k_r+k_{out})$, 무릎 위 $k_2\delta$. 로드 쪽 기름량(로드 법칙의 기준 압력 $p_{r0}$, 무릎 기준)은 그대로다. 무릎 아래에서는 피스톤 이동 때문에 로드 압력 판독이 $-k_rk_h\delta/((k_h+k_r+k_{out})A_{ann})$ 바뀌고, 무릎 위(바닥)에서는 바뀌지 않는다(control-expert 정정 2026-11-06, 판정을 느슨하게 하지 않음; 개정 1 2.1의 같은 문구도 이 뜻으로 읽는다).
- 옛 구현(a506c29, `l2b_rod_side.py` `shift_head`)은 S7 경로에 $c_{lock}\mathrel{-}=\delta$, $F_{lock}\mathrel{-}=k_2\delta$를 썼다. 이 값은 $(k_h+k_r+k_{out})/(k_h+k_{out})$배, REXOME 강체 바닥에서 1.02~1.16배 과대였다(hydraulics-expert 수치 확인 2026-11-06, `decision_log.md` 4절 v5 구현 줄). 커밋 c8a3e63에서 위 정확식으로 고쳤고 시험 C-10(662ac2c에서 δ 0.1·0.3327 mm, 무릎 위 Δp_r = 0 보강)으로 확인했다.
- 개방 이동에는 `oil.shift_head` 보호 장치(잠기지 않은 다리·disarm이면 앵커를 건드리지 않음)를 둔다.

**M2와 함께 켤 때 이중 계산을 막는다.** 수축 크리프 `creep_ref`$=A_{ann}(p_{rod}-p_r)/k_h$는 M2 이동과 **같은 항**이다(FL 0.3327 mm, BL, $F_{band}$ 0). M1c 수축 개방 때 M2의 직전 압력과 추적 압력을 $p_{rod}$로 시드한다. `retract_dead`의 결과에 `p_rod`를 더하고(값은 안 바뀜), L2b는 `L2bRodSide.seed_release_pressure(i, p)`를 새로 둔다(개방 스텝의 `spring_force_N` 뒤 `_last_p_r[i]`에 쓴다, `:391`이 다음 스텝에 읽음). 신장 쪽은 겹치는 항이 없다.

**알려진 한계**(제조사 답까지 고치지 않는다):

| 한계 | 내용 | 근거 |
|---|---|---|
| 단위 미달 | 경계 구역 동시·분리 오답 3/40(허용 2), 헤드 행정 최대 468 % | `unit_m1c.json`. 이 표는 `VR`로 잰 값이다(`unit_m1c.py:111`). VN·BL 경계값은 없다 |
| 단위 일치 구역 | VN(`vent_ref`) 로드 행정 ≤ 0.55 %, 헤드 ≤ 2.2 %. BL(`block_lowA`) ≤ 0.45 %, ≤ 2.6 % | `unit_m1c.json` `early_unit` |
| 고정 해제 | E2 없음. 켜면 값이 F_min을 넘어가고 복귀 실패가 는다(가장 큰 미결) | `decision_log.md:332` |
| 하네스 $p_r$ 판독 | 수축 잠금 뒤 신장에서 $p_r$이 $p_{r0}$(약 34.8 bar)로 돌아간다. 단위 재현은 2 bar로 떨어진다고 가정했다(`unit_m1c.py:65`). 그래서 수축 뒤 신장의 헤드 개방이 $p_A$ 5.4 bar에서 일어나 지연이 거의 없다($p_B$가 5 bar로 떨어지면 75 bar). 코드로 확인했고, 저장 계열에는 BL FR 31 ms 짧은 구간(34.24 → 34.29 bar)뿐이다 | D-2 결정: 그대로 두고 한계로 기록 |
| 유량·M2·LC 조합 | Hopsan 기준과 폐루프 실행이 없다 | |
| L2b 정지 마찰비 $r_s>1$(개정 2) | 입력 `band = F_s − f`는 미끄럼 한계 기준이다(`l2b_actuator.py:555-557`, 하네스도 같은 식). 붙음 상태의 실제 남은 띠는 $r_sF_s-f$라서 $(r_s-1)F_s$만큼 작게 들어간다. 결과: `retract_dead`의 $p_{open}$·need가 커지고(개방이 늦어지는 쪽), $f>F_s$로 붙어 있으면 band < 0이 되어 `creep_start`가 음수가 된다. YAML 기본 $r_s$ = 1.0(`actuator.seal_friction.static_ratio`)에서는 차이가 없다 | 고치지 않고 한계로 기록. $r_s>1$ 행의 M1c 값은 참고 값. 바꾸려면 붙음 다리에 $r_sF_s-f$를 넘기는 것이 맞지만 단위 기준(`unit_m1c.json`)이 $r_s$ = 1에서만 있다 |

### 2.5 LC: 오버랩 꼬리 차단 + 체크 닫힘 지연 (기본 끔)

근거는 `s8_seal_friction_counterbalance.md` 11.3~11.5절(2·3단계)이다. $\varepsilon$ 1×10⁻⁶ m/s는 수치 문턱이고, 지금 플랜트의 "이동 중" 꼬리 0.86~0.99 s는 지수 밸브와 $\varepsilon$가 만든 것이다.

$$u_i=0\quad\text{if }\ \lvert u_{c,i}\rvert\le\varepsilon\ \text{ and }\ \lvert u_{v,i}\rvert\le u_{ol},\qquad u_{ol}=\delta_{ol}v_{max}$$

$$t_{ol}=t_0+\tau_v\ln\frac{\max(\lvert u_{last}\rvert,u_{ol})}{u_{ol}},\qquad t_{lock}=t_{ol}+t_c$$

| 기호 | 뜻 | 값 | 표시 |
|---|---|---|---|
| $u_c$, $u_v$ | 절단 뒤 명령, 스풀 스텝 평균 속도 | m/s | |
| $\varepsilon$ | 기존 잠금 문턱 | 1×10⁻⁶ m/s | YAML |
| $\delta_{ol}$ | 오버랩 끝 스풀 개도 비 | **2 %**(감도 1, 5 %) = 0.418 mm/s | **ASSUMPTION** 대표값, 밸브 자료 없음 |
| $t_c$ | 유량 차단 뒤 잠김 법칙까지 | **50 ms**(감도 20~100 ms) | **ASSUMPTION** 추정, A·B→T 중립 전제 |
| $t_0$, $u_{last}$ | 명령 0 시각, 그 직전 속도 | s, m/s | |

| 규칙 | 내용 | 표시 |
|---|---|---|
| 차단 조건 | **명령 0 꼬리만** 끊는다. 0이 아닌 작은 명령($\varepsilon<\lvert u_c\rvert<u_{ol}$)은 지금처럼 흐른다 | **ASSUMPTION**: 증폭기 데드밴드 보상. 11.4 근거 |
| 출발 쪽 | 무유량 지연을 넣지 않는다 | **ASSUMPTION**(11.4 2단계 끝). M1c와 별개 |
| $t_c$ 동안 | 유량 0, 이동 상태 법칙 유지, 추적 압력 계속 이완. **M2 켬이면 유량으로 채우는 쪽은 멈춘다**(개정 3: $u=0$이라 수축 승압·신장 감압이 정지하고, $p_{lag}$ 분기만 이완한다. 2.3절) | 11.4 3단계, 2.3절 개정 3 |
| $t_c$ 동안 감쇠 | **이동 감쇠**. LC가 켜지면 감쇠를 $u$가 아니라 법칙의 잠금 상태로 고른다 | **ASSUMPTION**(11절에 없음, 이번에 정함) |
| $t_c$ 안 재명령 | 잠그지 않고 이동으로 돌아간다(기존 H5, 기준점 없음) | `test_rod_chamber.py:426` |
| 잠금 압력 | $p_{r0}$ 규칙 그대로(수축 뒤 `p_r0_after_retract`) | 기존 |
| 넣지 않는 것 | 11.4 4단계(A·B 차단 호스 등가 길이) | D-6, V-6 답 뒤 |

| 위치 | 구현 |
|---|---|
| **설정** | `LockClosureSetting(overlap_ratio, closing_delay_s)` 한 객체. 범위 검사 $0<\delta_{ol}<1$, $t_c\ge0$. 11.7절은 YAML 키를 제안했지만 **YAML에 넣지 않는다**: YAML은 생성물이고 값이 모두 가정이다. "한 키 묶음" 조건은 이 객체 하나로 플랜트와 제어기를 만드는 것으로 지킨다. U-R8-9 ④ 값이 오면 YAML로 옮긴다 |
| **L2b 꼬리** | `SpeedReference.configure_lock_closure(setting)`(기본 None). `advance`의 밸브 분기에서 `_valve_step` 직후에 적용. 밸브 모델이 꺼져 있으면 `ValueError`. 스풀 상태 $u_a$는 계속 감쇠한다 |
| **L2b 타이머** | `L2bRodSide(..., closing_delay_s=0.0)`로 `:138`의 고정 0을 인자로 바꾼다. 상태 기계는 이미 있다(`rod_chamber.py:466`), 스냅숏 키도 있다(`:708`). 마찰 경로의 기름 법칙에도 같은 값 |
| **L2b 감쇠** | `hook`·`_friction_hook`의 $c$ 선택(`:526`, `:558`): LC가 켜지면 `rod_side.locked`로 고른다. 꺼지면 기존 식 그대로 |
| **하네스 꼬리** | `coupled/harness_hydraulics.py`가 `closed_loop._lagged_step`을 바꾼다(`install_command_clip` 선례, `harness_flow.py:253`). 조건은 조각 평균 속도로 판단 |
| **하네스 타이머** | `_rod_force` 덮어쓰기: 대기 중인 다리는 기반 법칙에 $2\varepsilon\cdot$`last_dir`를 넘겨 이동 분기에 두고, 커널에는 $u=0$을 준다. $t_c$가 지나면 0을 넘겨 잠근다. `s8_g4_rodside_check.py`는 고치지 않는다 |
| **하네스 감쇠** | 하네스는 `plant.cn`을 `valve`로 정한다(`s9_soil_closed_loop.py:437`, `r51_reapp_closed_loop.py:339`). LC가 켜지면 플랜트 `step` 맨 앞에서 `plant.locked`로 다시 정한다 |
| **거부** | L1 행, `lock_valve="counterbalance"`는 `ValueError`(CB는 잠금 압력 규칙이 달라 시험한 적 없음) |

**수계산 값**(유량 차단 시각 [s], 잃는 행정, 차단 순간 이동 감쇠 힘 단계):

| $\delta_{ol}$ | $t_{ol}$: 0.25 $v_{max}$ / $v_{max}$ | $\tau_vu_{ol}$ [mm] | $c_{move}u_{ol}$ FL / RL [N] |
|---|---|---|---|
| 1 % | 0.322 / 0.461 | 0.0209 | 21 / 18 |
| **2 %** | **0.253 / 0.391** | **0.0418** | **42 / 36** |
| 5 % | 0.161 / 0.300 | 0.1046 | 105 / 91 |
| 지금($\varepsilon$) | 0.856 / 0.995 | 0.0001 | 0 |

### 2.6 제어기 쪽 요구사항 (플랜트 쪽에서 내는 요구, 값·설계는 control-expert)

11.5절의 조건: **플랜트 잠금 규칙과 제어기 창을 같은 값으로 함께 바꾼다.** 창 식은 다음이 되어야 한다.

$$W=\tau_v\ln\frac{\max(\lvert u_{last}\rvert,u_{ol})}{u_{ol}}+t_c+T$$

| 요구 | 내용 |
|---|---|
| R-1 | 지금 식 `two_pressure.py:2316-2323`은 $\varepsilon$ 자리에 $u_{ol}$을 넣을 수 있으나 $t_c$ 항이 없다. 기본 0인 항을 더한다. $x+0.0=x$이므로 끄면 값이 같다. 설정 필드가 meta에 새로 나타나는지는 control-expert가 본다(비트 동일 대상은 명령과 플랜트 값) |
| R-2 | 제어기 설정은 플랜트와 **같은 `LockClosureSetting`에서** 만든다. 따로 입력하지 않는다. $\tau_v$도 플랜트 값(`with_lock_window_tau` 선례, `run_S8C.py:1387`) |
| R-3 | 제어기만 켜는 조합을 러너가 거부한다(아래 표) |
| R-4 | 플랜트 꼬리가 사라지면서 달라지는 다른 규칙을 control-expert가 점검한다(질문 Q-3) |

**조합 허용**(수계산: 제어기 창 − 플랜트 잠금 시각, $\delta_{ol}$ 2 %):

| 조합 | 창 − 잠금 [s] | 허용 | 이유 |
|---|---|---|---|
| 끔·끔 | 지금과 같음(10.5 낙관 0.007 kN) | 기본 | 비트 동일 |
| **플랜트만**(LC 켬, 옛 창) | +0.654($\lvert u_{last}\rvert\ge u_{ol}$, $t_c$ 50 ms). 작은 $u_{last}$ 쪽 +0.119($u_{last}$ 2×10⁻⁶ m/s) | **허용, 단 $t_c\le T$ 검사.** 효과 분리 시험(L1)과 비교용이다. **v5 기준 구성으로 쓰지 않는다.** | 옛 창이 새 잠금을 덮는다(11.5 권고 (1)). $u_{last}\to\varepsilon$에서 여유는 $T-t_c$이므로 $t_c$ 100 ms면 0이고 그 위는 음수다. 창이 길어 과보수는 그대로이고 11.5의 이득(중앙값 0.72 → 0.17 s)이 없다. 수식 판단이고 새 플랜트 기록으로 시험한 것은 아니다 |
| **제어기만**(옛 플랜트, 새 창) | −0.454($\lvert u_{last}\rvert\ge u_{ol}$, 속도와 무관). $u_{last}<u_{ol}$이면 $0.15-\tau_v\ln(u_{last}/\varepsilon)$: 0.16 mm/s에서 −0.358, 0.0045 mm/s 아래에서만 양수 | **금지**(`SystemExit`) | 운용 속도에서 창이 플랜트 잠금보다 먼저 닫힌다. 저장 기록 4,241 구간 중 2,546개가 새 창보다 늦게 잠그고 낙관 29건이 0.6 kN을 넘는다(최대 10.3 kN, 11.5) |
| 둘 다 | $T$ 그대로 남음 | **v5 기준 구성**, 단 Chrono T4·T5 전에는 대체 경로 근거가 없다 | 11.5 조건 |

$\hat p_r$은 대체 다리에만 쓰이므로(10.4 T8) 대체가 없는 행에서는 창을 바꿔도 명령이 같을 것으로 **예상**한다. 확인은 시험 W-2다. 다르면 멈추고 control-expert에 넘긴다.

**control-expert에 넘길 입력**: 2.5절 식·값, 위 표, `s8_seal_friction_counterbalance.md` 11.2~11.5, `h_s8_3_window.json`, `04_scripts/04_hydraulic/s8_cb/h_s8_3_window.py`.

**control-expert 질문**:

| # | 질문 |
|---|---|
| Q-1 | R-1 필드 이름과 $u_{ol}$·$t_c$를 어떻게 넘길 것인가. 하네스 C2 설정에 어느 경로로 넣는가 |
| Q-2 | 새 창의 근거 시험: 10.4 T4·T5와 11.2 시험은 Chrono 기록을 재생한다(p1r 37, CB 6, ML 216). 새 플랜트 기록이 없으면 돌릴 수 없다(11.5 "플랜트가 바뀌면 진값도 바뀐다"). 어떤 행 몇 개면 되는가. D-3 뒤로 미루면 그때까지 새 창의 대체 경로 판정은 비워 두는가 |
| Q-3 | 꼬리가 0.86~0.99 s에서 0.30~0.44 s(잠금 기준)로 줄고 잠금 전 힘 단계가 생긴다. 기록 행의 D1 단계 규칙(`check_draining`, `lock_load_regain`), `locked_start_lookback_s`, R-5 $R_{hi}$, 잠금 전 표본을 쓰는 규칙 중 값을 바꿔야 할 것이 있는가 |
| Q-4 | 잡음·격자 묶음(`acceptance/c4g2_only` 잡음 L1 171·L2 855·L3 501, 격자 768)을 LC + 새 창으로 다시 돌릴 것인가. 대체가 생기는 행은 여기에만 있을 수 있다. 3.3 건수에 넣지 않았다 |
| Q-5 | $R_{ub}$의 `locked_ratio_head_dead_max_m`: 11.4 4단계는 A·B 차단이면 0.12 m로 올리라고 한다. D-6으로 BL + LC는 거부했다. V-6 답이 A·B 차단이면 이 값과 BL을 어떻게 다룰 것인가(H-61-1) |
| Q-6 | v5 기준(`v5_criteria.md`)에서 플랜트만(L1)의 값을 어떻게 읽을 것인가, $t_c$·$\delta_{ol}$ 감도 행의 합격 조건 |

### 2.7 M1c 수정 멈춤과의 관계, 제조사 답 의존

M1c 코드(2.4절)는 **고치지 않는다.** LC가 M1c 입력을 바꾸는 점은 다음과 같다.

| 항목 | 내용 | 처리 |
|---|---|---|
| 입력 $u$ | 꼬리에서 $u_{ol}$에 이르면 0이 된다. M1c 게이트 $g$가 $c_v$ 뒤 선형 대신 차단 순간 1로 뛴다. 라인 배수가 조금 일찍 시작한다 | M1c 식은 그대로. 저장 M1c 재현(C-5)은 **LC 끔에서만** 성립 |
| 재출발 | `plant.locked`인 때만 `rod_released`를 지운다(`m1c_plant.py:233`). $t_c$ 안 재명령은 로드 체크를 다시 채우지 않는다. 물리적으로 맞는 방향이지만 기준이 없다 | 그대로, 조합은 참고 값 |
| $c_v$와 $\delta_{ol}$ | 둘 다 2 %지만 다른 값이다($c_v$는 중립 유로 닫힘, $\delta_{ol}$은 유량 시작). 묶지 않는다 | V-5·V-6 답 뒤 재검토 |
| **BL과 $t_c$** | **물리가 맞지 않는다.** A·B 차단이면 유출 쪽 체크가 라인 압력에 눌려 수 s 이상 열려 있을 수 있다(11.4 3단계). $t_c$ 50 ms는 A·B→T 전제다. 맞추려면 긴 $t_c$와 4단계가 필요하고 값 근거가 없다 | **D-6 결정: 조합 거부.** M1c를 고치는 일은 아니다 |
| VN과 $t_c$ | 중립 A·B→T라 전제가 맞다. 그래도 M1c 라인 배수와 $t_c$는 독립 값이다 | 참고 값 |

**$t_c$·$\delta_{ol}$이 의존하는 제조사 답**(`manufacturer_questions.md`, 대응 `manufacturer_questions_internal.md`):

| 항목 | 주는 것 | 의존 값 |
|---|---|---|
| **V-6**(1차, 가장 먼저) | 중립 A·B 차단 / A·B→T. 차단이면 $t_c$ 전제가 무너진다 | $t_c$ 전제, 4단계 |
| **V-5**(1차) | 불감대(최소 제어 유량), 증폭기 램프 | $\delta_{ol}$, 차단 조건의 데드밴드 보상 가정, $\tau_v$ |
| **L-6**(1차) | 파일럿 감쇠 오리피스, 포핏 특성 | $t_c$ |
| **L-7**(1차) | 파일럿 뒤쪽 연결, 정지 중 압력 | $t_c$(체크 닫힘 조건) |
| **M-2**(1차) | 라인 A·B 압력 1 kHz 측정 | $t_c$·$\delta_{ol}$ 실측 후보. 정지 쪽 판정은 11.6 U-R8-9 ④ 절차가 원본 |
| M-10, C-5(2차, `manufacturer_questions_2nd.md`) | 누설과 잠금 유지. 대응표상 H-61-1 부가 | $t_c$ 값을 직접 주지 않는다. 잠금 뒤 체크가 닫혔는지 간접 확인 |

답이 올 때까지 가정 범위로 쓴다. 값이 오면 설정 객체 값만 바꾼다.

## 3. 시험

### 3.1 단위 시험

위치 `05_tests/unit/test_hydraulics_rod_release.py`(M2-9~11 포함), `test_m2_flow_law_paths.py`(M2-12·13, 개정 3), `test_hydraulics_check_open_delay.py`, `05_tests/chrono/test_l2b_v5_options.py`. 하네스 행은 `returned_clip_hash_runner.py` 형태의 dynamics-dev 하위 실행.

| ID | 내용 | 기대값 | 근거 |
|---|---|---|---|
| F-1 | 기존 `test_hydraulics_flow_share`, `test_hydraulics_flow_limit_run`, `test_flow_limit_actuators`, `coupled/test_harness_flow`, `test_flow_share` 전부 통과 | 변화 없음 | 기존 |
| F-2 | 네 다리 $v_{max}$ 수요·공급 | 57.189 L/min. 공급 57.19 / 54.18 / 51.17 L/min. 비례 법칙 $r$ 0.8947($\eta_v$ 0.85) | 수계산. $\eta_v$ 0.95 비 1.000014 |
| F-3 | 옵션 없음 = 끔 | `flow_limit is None`, `FlowShareAssumptions.is_enabled` False | D-5 미전환 |
| V-1 | 밸브 켬 계단 응답 $\tau_v$ 0.1 s | $t$ = 0.1 s에 $u/v_{max}$ 0.632, $s_{ref}$ 0.770 mm | 수계산 |
| V-2 | `run_S9` 옵션 없음 | `valve_model_on` False, `command_ramp_active` True, args 키 없음 | 저장 meta |
| M2-1 | 실제 `L2bRodSide` + `SpeedReference`, 몸체 고정, FL 신장 0.25 $v_{max}$ 0.5 s, 로드 34.818 대 2 bar 끝 힘 차 | **10.89 ± 0.3 kN**, 옵션 없음 0.0 | 수계산 10.893, numpy 10.879, 래퍼 10.700. Hopsan 8.46은 제외(보고서 12.4). **개정 3 실측 10.702 kN**(통과) |
| M2-2 | 자유 몸체 C2 − C3 끝 힘 FL(t = 3.0 s, 저장 실행 길이 그대로) | **4.13~4.25 ± 0.5 kN** | Hopsan 4.13, numpy 4.20, 래퍼 4.25. **주석(개정 2)**: 정지 1 s 뒤 순간값이라 로킹 진동(2.95 Hz, ζ 약 0.01, 진폭 약 1.9 kN) 위상에 따라 달라진다. 정착값은 **2.43 kN**(M2-6). 이 시험은 래퍼 재현용으로 그대로 둔다. **주석(개정 3)**: 실측 순간 **4.316 kN**, 200스텝 평균 **4.224 kN**(둘 다 허용 안). 순간값 차(+0.09 kN)는 유량 제한으로 감압 시각이 바뀌어 로킹 위상이 달라진 몫으로 본다(정착값 차는 3자유도 법칙에서 +0.02 kN). 판정은 정착값(M2-6)으로 한다 |
| M2-3 | 네 다리 정지 A 켬·끔 차 | ≤ 0.05 kN | 래퍼 ≤ 0.01 kN |
| M2-4 | 마찰 경로 $F_s$ 4 kN, M2-1 짝 차 | 10.89 ± 0.3 kN | **수계산만**(미끄러지면 $f$ 같은 한계). Hopsan 기준 없음 |
| M2-5 | 이동 합: $s_{ref}$ 고정, 34.818 → 5 bar | FL 0.3820 mm(1×10⁻⁹ m 안) | 수계산 |
| M2-6 | 하네스 플랜트 C2 − C3, FL 힘 **정착값**(개정 2). 측정: 정지(t = 2.0 s) 뒤 **30 s 이상** 실행, 정지 뒤 **10~30 s 평균**(t 12~32 s) 또는 정지 뒤 1 s부터의 **상수 + 감쇠 정현파 맞춤의 상수항** | **2.43 ± 0.25 kN** | 아래 표. 허용 ±0.25 kN의 근거: 하네스 횡 패드 스프링 효과 약 6 %, 모델 간 이동량 차 약 2 %, 맞춤 오차. 벗어나면 멈추고 dynamics-expert. ~~4.13~4.25 ± 1 kN~~(개정 1, 순간값 기준이라 폐기). **개정 3 하네스 실측 2.4746 kN**(통과, 봉인 기준 개정 4의 2.475 kN) |
| M2-7 | 스냅숏 복원 뒤 연속 실행과 비트 동일 | | |
| M2-8 | 신장 뒤 수축 시작 | **기대값 없음.** Hopsan 대조가 없다(보고서 12.4 미시험). 부호와 M2-5 합만 시험 | hydraulics-expert가 기준 1건 추가 가능 |
| M2-9 | (개정 3) FL 몸체 고정, 1 % $v_{max}$ 수축, 로드 5 bar 시작 | 승압 기울기 $A_{ann}u/C_r$ = **4.39 bar/s**, 이동 속도 $r\,u$ = **0.0562 mm/s**, $r=k_r/(k_h+k_r)$, 상대 1 % 안 | 수계산. **실측 4.3864 bar/s, 0.05620 mm/s** |
| M2-10 | (개정 3) FL 1 % $v_{max}$ 신장, 로드 34.818 → 10 bar 감압 시간 | $t=2C_r\sqrt{\Delta p_c}\,(\sqrt{p_0-p_T}-\sqrt{p_1-p_T})/(b_TA_hu)$ = **1.188 s**, 상대 1 % 안 | 수계산(오리피스 배수 폐형식). **실측 1.1877 s** |
| M2-11 | (개정 3) $u=0$, 수축 승압·신장 감압 두 경우 | 유량으로 채우는 쪽 압력 불변 | 법칙 정의. **실측 불변**(통과) |
| M2-12 | (개정 3) 하네스 `_RodPressureLag`와 L2b 상태 기계에 같은 입력열, 네 다리 | 로드 압력 상대 1×10⁻¹² 안 | 같은 순수 함수. **실측 비트 동일** |
| M2-13 | (개정 3) 저장 Hopsan C2(34.818 bar 잠김, FL 0.25 $v_{max}$ 신장)의 밸브 입력으로 법칙을 돌려 감압 곡선 대조 | 20 bar 도달 시각 차 ≤ **5 ms** | 데이터 `05_tests/data/m2_13_hopsan_c2_release*`. **실측 1.8 ms**(개정 2의 τ 법칙은 35 ms 빠름) |
| C-1 | 이식본이 저장 표를 재현: `unit_m1c.json`의 `vent_ref`, `block_lowA` 60행 | 행정 차 ≤ 1×10⁻⁴ mm | 저장 값 |
| C-2 | 수축 쪽 이식이 `m1b/unit_m1b.json`과 같음 | 값 동일 | `m1_criteria.md` M1c 절 |
| C-3 | 신장 수계산, $p_h$ 89.5(FL)·76(RL), $p_r$ 2 bar | 헤드 개방 $p_A$ 85.5 / 72.0 bar, $x$ **0.3586 / 0.4199 mm**. VN 로드 개방 $p_A$ 2.857 bar, $x$ 0.00368 mm(FL). BL 로드는 즉시 | 수계산, BL($K_n$ 0)로 드레인 없이 |
| C-4 | 수축 수계산, FL, $p_h$ 89.5, $p_r$ 2, $s$ 0.4011 m | 아래 표 | `retract_dead` 값. BL $F_{band}$ 0의 $p_{open}$은 Hopsan 28.0 bar와 맞는다 |
| C-5 | 하네스 폐루프 비트 재현: `pre_c4g2_preset_runner.py`로 R12 `VN_c2_v1`·`BL_v1`·`VN_c2_v05`·`BL_v05` 각 4위상, G4 2행, S7·R15 각 1위상 | `commands_sha256` = `m1c/r12.jsonl`, `g4.jsonl`, `main.jsonl` | 먼저 OFF가 `m1c/hash.jsonl`과 같은지 본다. 안 같으면 멈추고 보고 |
| C-6 | 같은 입력 열을 하네스·L2b 어댑터에 넣음(마찰 부호 포함) | `need`, 전달 속도 일치 | 커널 $f$와 L2b $f$의 부호가 같은지 이 시험이 확인한다(코드로 확정 못 함) |
| C-7 | 스텝 수렴 1 ms 대 1×10⁻⁴ s | 헤드 개방 행정 차 ≤ 1 % | 새 기준 |
| C-8 | M2 + M1c 수축: 크리프 + M2 합 | $A_{ann}(p_{rod}-p_r)/k_h$ = 0.3327 mm(FL, BL), **2배가 아님** | 수계산 |
| C-9 | meta에 `unit_status`, VR·E2·E4 값을 주면 `ValueError` | | 사용자 결정 |
| C-10 | `shift_head` 앵커 이동(개정 2): 잠긴 다리, 몸체 고정, $\delta$ 0.1 mm, 무릎 아래·위 각 1건, S7 경로와 기름 법칙 G | 힘 감소 무릎 아래 $k_hk_{out}\delta/(k_h+k_r+k_{out})$, 위 $k_2\delta$(상대 1×10⁻⁹ 안). 로드 쪽 불변. 기름 법칙 G는 기존 CB 식과 비트 동일 | 2.4절 정확식 |
| L-1 | 꼬리 차단 시각, $\delta_{ol}$ 1·2·5 %, 0.25·1.0 $v_{max}$에서 명령 0 | 2.5절 표 값, 1 스텝(하네스 1 조각) 안 | 수계산 |
| L-2 | 차단으로 잃는 행정(명령 0 뒤 $\int u\,dt$가 이상값보다 작은 양) | 0.0209 / 0.0418 / 0.1046 mm, 상대 1 % 안 | 수계산, 11.3의 0.04 mm와 맞음 |
| L-3 | 차단 순간 힘 단계(이동 감쇠) | FL 42 N, RL 36 N($\delta_{ol}$ 2 %), 상대 5 % 안 | 수계산. 스프링 변화가 없는 몸체 고정 조건 |
| L-4 | 잠금 시각 $t_{ol}+t_c$, $t_c$ 20·50·100 ms | 1 스텝 안, 잠금 때 $F$ 불연속 없음 | 수계산, `rod_chamber` 규칙 |
| L-5 | $t_c$ 안 재명령 | 잠기지 않음, 기준점 없음 | `test_rod_chamber.py:426` 규칙 |
| L-6 | 0이 아닌 작은 명령 0.16 mm/s($u_{ol}$ 아래) | 끊기지 않음 | 11.4 2단계 |
| L-7 | 스냅숏 복원 뒤 비트 동일, 하네스 `deepcopy` 분기 | | |
| L-8 | 옵션 없음: `L2bRodSide` `poc_close_delay_s` 0.0, 감쇠 식 기존 | 비트 동일 | B-2, B-4 |
| L-9 | 네 다리 정지 힘 대조 | **기대값 없음.** 저장 네 다리 Hopsan 회로에는 체크가 없고, $t_c$·오버랩 기준이 없다. 값만 기록 | 근거 없음. 저장 `poc_*.json`을 기준으로 쓸 수 있는지는 확인하지 못함 |
| L-10 | BL + LC 조합 거부 | `ValueError` | D-6 결정 |
| W-1 | 창 값: $\delta_{ol}$ / $t_c$가 1 % / 50, 2 % / 50, 5 % / 50, 2 % / 100 ms일 때 0.25 $v_{max}$·$v_{max}$의 $W$ | 0.472·0.611, 0.403·0.541, 0.311·0.450, 0.453·0.591 s | 수계산, 11.5 표와 맞음 |
| W-2 | LC 켬에서 새 창 켬·끔 명령 해시, 대체 없는 8행 | **같을 것으로 예상**(10.4 T8 근거). 다르면 멈춘다 | 코드 읽기 |
| W-3 | 제어기만 켬 | `SystemExit` | 11.5 |
| W-4 | 플랜트만, $t_c>T$ | `ValueError` | 2.6절 표 |
| W-5 | 새 창 끔: 기존 `two_pressure` 시험과 `test_s8_ml_main.py:229` | 비트 동일 | |
| W-6 | T4·T5(새 플랜트 기록 재생) | 통과 기준 하한 ≤ 진값 + 0.6 kN. **새 플랜트 Chrono 기록이 있어야 한다**(Q-2) | 10.4 |

M2-6 기준값(개정 2, FL 힘 C2 − C3 [kN], C2 로드 34.818 bar g / C3 2 bar g 해제, FL 0.25 $v_{max}$ 0.5 s 신장, 3자유도 몸체):

| 모델 | t = 3.0 s 순간값 | 정지 뒤 3~10 s 평균 | **정지 뒤 10~30 s 평균** | 맞춤 상수항(3~32 s, 2모드) | 로킹 모드 f / ζ |
|---|---|---|---|---|---|
| Hopsan 두 챔버(Δt 1×10⁻⁵ s) | 4.10 | 2.340 | **2.344** | 2.342 | 2.953 Hz / 0.0080 |
| numpy 두 챔버(RK4 5×10⁻⁵ s) | 4.18 | 2.398 | **2.401** | 2.400 | 2.952 Hz / 0.0080 |
| 3자유도 법칙 + M2(`m2_check.run_law`) | 4.23 | 2.431 | **2.433** | 2.433 | 2.947 Hz / 0.0108 |
| 하네스(dynamics-expert, 6자유도) | | | 2.436 | | |
| 3자유도 법칙 + M2 **개정 3**(hydraulics-expert `hyd_m2fix/law.json`) | 4.316 | 2.461 | **2.456** | 2.456 | 2.947 Hz / 0.0108 |
| 하네스 **개정 3**(python-expert 시험 M2-6) | | | **2.4746** | | |

- 2모드 맞춤의 둘째 모드는 4.86 Hz(ζ 0.014~0.018)다. 맞춤 RMS 잔차 ≤ 0.004 kN.
- Hopsan 스텝 절반(5×10⁻⁶ s, 12 s 실행): 정지 뒤 3~10 s 평균 2.3375 대 2.340 kN(0.1 %).
- Hopsan·numpy는 법칙 모델(3자유도·하네스)보다 1~4 % 낮다(Hopsan ↔ numpy 2.4 %, numpy ↔ 3자유도 1.3 %, Hopsan ↔ 3자유도 3.7 %)(두 챔버 잠김 강성·끝 로드 압력 차로 추정, 원인 분리 안 함). 정지 뒤 10~20 s 창 ptp가 약 1 kN이므로 10 s보다 짧은 창 평균은 쓰지 않는다.
- 실행: scratchpad `m2_6_hyd\run_long.py`, `settle.py`, 결과 `settle.json`, `settle.png`(보존 보장 없음). 모델 스크립트는 워크트리 a506c29의 `04_scripts/04_hydraulic/pressure_review/{four_leg,m2_check}.py`를 읽기만 했다.

C-4 기대값(FL, 단위 mm, 압력 bar):

| 회로 | $F_{band}$ [kN] | need | $p_{open}$ | creep | discharge |
|---|---|---|---|---|---|
| BL ($\delta$ 0) | 0 | 1.6311 | 27.96 | 0.3327 | 0.4074 |
| BL | 4 | 1.4363 | 27.03 | 0.3207 | 0.3933 |
| VN ($\delta$ 3) | 0 | 1.4714 | 27.70 | 0.2908 | 0.4034 |
| VN | 4 | 1.2766 | 26.76 | 0.2788 | 0.3894 |

### 3.2 기본 끔 비트 동일

| ID | 시험 | 기준값 | 비용(근거) |
|---|---|---|---|
| B-1 | **코드 변경 전에** e747d8c에서 황금값 생성: `run_verdict.py --bundles OFF --decide R13=ss_fs4 --decide S6=alias_s5 --out 06_analysis/03_hydraulic/coupled/v5/golden_off` | 새 저장값. `verdict/OFF_*`는 옛 제어기라 쓰지 않는다 | 저장 OFF 22행 합 약 590 코어·s (`verdict/OFF_*.json`, 제어기 다름) |
| B-2 | 구현 뒤 같은 명령 → 모든 행 `commands_sha256` 일치 | B-1 | 같음 |
| B-3 | `definition_digest`가 옵션 없을 때 변하지 않음 | 저장 파일 대조 | 즉시 |
| B-4 | 강체 Chrono 1행 `hash_G1L_Fs0` 재실행 | `command_hash` f624ed94…, `record`·`pads`·`r8_series`·`s8_series` 전 배열(`final_c4g2_values.json` `hash_check`) | G1L 저장 1,022 s |
| B-5 | 토양 Chrono 짧은 행, 옵션 없음 | `batch_FINAL-C4G2_20261105/P3b_J1_B_top_Fs4`와 앞부분 `step_series.npz` `equal_nan` | 짧은 행 시간은 **측정 없음** |
| B-6 | `s9_batch.py check-sources FINAL-REP`, `--expect-controller final_C4G2` | 통과 | 즉시 |
| B-7 | `05_tests/unit` 전체, `05_tests/chrono/test_l2b_actuator.py`(L1 비트 대조 포함), `test_actuator_valve`, `test_l2b_s8`, `test_l2b_closed_loop` | 통과 | |
| B-8 | `git diff 09_paper`, `02_params/rexome33.yaml` 변화 없음 | | 즉시 |

B-2·B-4·B-5는 LC·제어기 창 코드를 넣은 뒤에도 그대로 다시 본다(커밋 표). 플랜트 옵션과 제어기 옵션이 모두 꺼진 경우만 비트 동일 대상이다. 플랜트만 켠 조합은 비트 동일 대상이 아니다.

### 3.3 인수 실행

**새 러너** `coupled/run_v5.py <batch> [--workers N] [--mask HEX]`: `m1_check/run_m1c.py` 형태(jsonl 이어쓰기, spawn 풀, `maxtasksperchild=1`, 결정론). 출력 `06_analysis/03_hydraulic/coupled/v5/<batch>.jsonl`. `--list`로 건수를 먼저 보여 준다. **집계** `coupled/aggregate_v5.py`는 값만 내고 판정 문구는 쓰지 않는다. **판정**은 control-expert가 실행 전에 쓴 `v5_criteria.md`로 한다(기준 틀 `m1_criteria.md` 1~7절). 강체 행의 READY는 기록이고 연약 행은 100 s 한계다.

| 필수 행 | 위상 | 건수 | 비고 |
|---|---|---|---|
| R12 | 사건 오프셋 0, 0.025, 0.05, 0.075 | 4 | |
| G4 폭 격자 | 상단 4다리 × $F_s$ 0·4·8 + 하단 FL·RR $F_s$ 4, 오프셋 0·0.05 | 28 | `run_m1c.py:70-74` |
| R14 / R15 / R16 | 오프셋 2 / 2 / 4 | 8 | `run_m1.py:56` |
| S1, S4, S5, S7, S8 | $\varepsilon$ 0, 1, 2, 3×10⁻³ | 20 | |
| R2, R2ra(`reanchor_on`) | 같음 | 8 | |
| R7 | 같음 | 4 | M1 격자는 2위상이었다. 필수 행이라 4로 올렸다 |
| **필수 합** | | **72** | |
| 회귀: R1, R5, R6, R8, R9, R10, R11, S3 2위상, R3, R4, S2 4위상 | | **28** | R13·S6는 결정 행이라 뺀다(M1 격자와 같음) |

**설정**(D-5 전환 아님, 실행마다 명시):

| 표시 | 내용 | 필수 72 | 회귀 28 | 뜻 |
|---|---|---|---|---|
| V0 | 전부 끔 | ○ | ○ | 짝 기준, 해시 = 황금값 |
| V1 | M2 | ○ | | M2 단독 효과 |
| V2 | 유량 $\eta_v$ 0.85 | ○ | | 저장 유량 결과와 연결 |
| V3 | 유량 0.85 + M2 | ○ | | LC 없는 구성, 저장 값과 연결 |
| L1 | LC(2 %, 50 ms), 플랜트만 | ○ | | LC 단독 효과 |
| L2 | LC + 새 창 | 8행 | | W-2 해시만: R12, R14, R16, S1, S7, R2, R7, S8 위상 0 |
| **VB** | **유량 0.85 + M2 + LC + 새 창** | ○ | ○ | **v5 기준 구성** |
| V4 | V3 + M1c VN ×1 | ○ | ○ | 참고, LC 끔 |
| V5 | V3 + M1c BL ×1 | ○ | ○ | 참고, LC 끔 |
| V6 | V3 + M1c VN ×0.5 | ○ | | 참고, LC 끔 |
| V7 | V3 + M1c BL ×0.5 | ○ | | 참고, LC 끔 |
| V8 | VB + M1c VN ×1 | ○ | | 참고, 기준 없는 조합 |
| LS1~LS4 | VB에서 $\delta_{ol}$ / $t_c$ = 1 % / 50, 5 % / 50, 2 % / 20, 2 % / 100 ms | ○ | | 감도 |

BL은 LC 끔에서만 돌린다(D-6 결정, BL + LC 거부).

합 **1,200건**(개정 전 688). 잡음·격자 묶음은 넣지 않았다(Q-4). 행마다 낼 값: 첫 READY, 끝 상태(`final_phase`), 복귀 시각(`t_ready_back_s`), 부호 전환 수 $n_{rev}$, 최소 힘(이륙 뒤·사건 창 뒤), FAULT·WARN 이름, 가드 시간, 다리별 M2 누적 이동, M1c 채움 수·시간, LC 잠금 횟수와 $t_c$ 안 재명령 수.

**실행량**(하네스, 저장 실측 근거. 합계는 추정):

| 근거 | 값 |
|---|---|
| 유량 끔 행(`m1c/main.jsonl` 중앙값, E 코어) | R12 62, G4 53, R14 52, R15 59, R16 45, S1 52, S4 55, S5 62, S7 45, R2 43, R7 36, S8 29 s |
| 유량 켬 행(`verdict/A_*`, 11-04) | R12 40, R14 45, R15 45, R16 43, R2 93, R7 88, S1 121, S4 117, S5 122, S7 109, S8 80 s |
| 설정별 추정 | V0 약 4,700, V1·L1 약 3,600, L2 약 360, V2·V3·V6·V7·V8·LS1~LS4 약 4,900, VB·V4·V5 약 7,900 코어·s |
| **합계 추정** | **약 80,000 코어·s(약 22 코어·h)**. 20 워커면 약 67 분 |

**모르는 것**: 이 합계는 LC·M2 비용을 뺀 값이다. LC와 M2의 스텝 비용, 유량 켬에 M1c를 더한 행의 시간은 측정이 없다(유량 켬 값을 그대로 썼다). LC로 이동 구간이 줄어 유량 해석 조각이 달라지는 효과도 모른다. 배치표는 compute-scheduler-expert가 낸다. Q-4의 잡음·격자 재실행 시간은 **확인하지 못했다.**

**Chrono 실행량**(저장 실측, 옵션 없는 값): 필수 강체 6행 합 **5,558 s**(`batch_FINAL-R-C4G2_20261105/progress.log`: E_G4 856, E_RE1bF_Fs8 1,277, G1L_Fs0 1,022, G1L_o050 1,051, K24_fdown 751, K8 601), 필수 토양 5행 합 **51,084 s = 14.2 h**(`result.json`: S1 8,289, S4 9,506, S5 9,560, S7 11,552, S8 12,177). 유량 켬 행당 약 +180 s(`s9_batch.py:265`, 추정). 밸브 켠 토양과 L2b의 M2·M1c·LC 비용은 **측정 없음**. 러너는 `s9_batch.py` `coupled_rows`(`:277`)를 본뜬 새 묶음, 판정은 `verdict/judgement_chrono/judge_chrono.py`·`judge_soil.py`와 `chrono/final_c4g2/` 표 형식. **행 수와 시점은 하네스 판정 뒤 결정한다(D-3 결정).** 그때 함께 정할 것: 토양 밸브 켬 기준 행, W-6 T4·T5에 필요한 기록(Q-2).

## 4. python-expert 작업 순서 (커밋 단위)

커밋마다 integrity-checker를 거치는 일은 메인 세션이 챙긴다.

| # | 커밋 | 내용 | 끝 조건 |
|---|---|---|---|
| 1 | 황금값과 기준 스크립트 | 코드 변경 없이 B-1 실행. `hyd_review/{common,four_leg,m2_check,m1_m2_build}.py`, `hyd_review/poc_*.py`를 `04_scripts/04_hydraulic/pressure_review/`로 복사(경로만 고침). `poc_*.py`, `m1_m2_build.py`는 기록 보존용이라 재실행하지 않는다 | 황금값 저장, `m2_check` 저장값 재현 |
| 2 | 옵션 틀 | `v5_options.py`, CLI 정의, 낡은 D-5 문구 수정, F-3 | B-3, B-7 |
| 3 | M2 법칙 + L2b | `rod_release.py`, `L2bForceActuator` 연결, 스냅숏 | M2-1~5, 7, 8. B-7 |
| 4 | M2 하네스 | `harness_hydraulics.py`, `verdict_runs.execute` 인자 | M2-6, B-2 |
| 5 | LC 플랜트 + L2b | `LockClosureSetting`, `SpeedReference.configure_lock_closure`, `L2bRodSide(closing_delay_s)`, 감쇠 선택 | L-1~8, B-7 |
| 6 | LC 하네스 | `_lagged_step` 교체, `_rod_force` 타이머, `cn` 재설정 | L-1, L-4, L-5, L-7 하네스판, B-2 |
| 7 | **제어기 창**(control-expert Q-1 답 뒤) | R-1~R-3. 조합 거부. 새 창 끔이 기본 | W-1, W-3, W-4, W-5, B-2 |
| 8 | M1c 모듈 | `check_open_delay.py` 이식, VR·E2·E4 삭제 | C-1~4, C-9 |
| 9 | M1c 하네스 | 어댑터. M2 시드 포함, D-6 거부 | C-5, C-8, L-10, B-2 |
| 10 | M1c L2b | `set_check_delay`, 감쇠 마스크, `seed_release_pressure`, 스냅숏. 개정 2: `shift_head` S7 정확식 | C-6, C-7, C-10, B-7 |
| 11 | 토양 밸브 옵션과 Chrono 인자 | `run_S9 --valve-tau-s`, `run_S8C`·`run_S9`에 M2·M1c·LC·창 인자, `s9_batch` 행 정의(실행 안 함) | V-1, V-2, B-6 |
| 12 | 러너·집계 | `run_v5.py`, `aggregate_v5.py`. `--list` 1,200건 확인, 행 1개 짧은 연기 시험 | V0 R12 해시 = 황금값, W-2 |
| 13 | 회귀 묶음 | B-4, B-5 실행(메인 세션이 띄움). `hydraulic_coupling.md` 머리에 이 명세 링크 | 일치. 다르면 멈추고 보고 |

그 뒤: control-expert가 기준 초안 작성 → 사용자가 미룬 판정 항목 8개 결정 → `v5_criteria.md` 봉인 → 메인 세션이 1,200건 실행 → control-expert 판정 → Chrono 범위 결정(D-3).

**막히는 곳**: control-expert 답(Q-1)이 직접 필요한 것은 커밋 7뿐이다. 커밋 1~6, 8~11은 답 없이 진행한다(커밋 11의 `--lock-window-follows-plant` 연결만 커밋 7 뒤). 커밋 12·13은 답이 필요 없지만 **커밋 7 뒤에야 끝난다**: 끝 조건 W-2는 새 창이 있어야 하고, B-2·B-4·B-5는 제어기 창 코드까지 넣은 뒤 확인해야 한다. BL + LC 거부(L-10)는 D-6 결정대로 커밋 9에 넣는다.

## 5. 미정·모르는 것

**결정된 것**(사용자, 개정 1):

| ID | 내용 | 결정 |
|---|---|---|
| D-1 | 오버랩·체크 닫힘 $t_c$ | **넣음**(2.5, 2.6절) |
| D-2 | M1c 입력 $p_r$ | 그대로 두고 한계 기록 |
| D-3 | Chrono 행과 시점, 토양 밸브 켬 기준 행 | 하네스 판정 뒤 결정 |
| D-4 | M2 방향 | 양방향 |
| D-5 | v5 기준 구성 $\eta_v$ | 0.85 |
| D-6 | BL(A·B 차단)과 $t_c$ 50 ms는 물리가 맞지 않는다(2.7절) | **BL은 LC 끔에서만 돌리고 조합은 거부**(사용자 결정 2026-11-06). V-6 답 뒤 다시 본다 |
| - | "v5로" 미룬 판정 항목 8개 | control-expert 기준 초안을 본 뒤 사용자가 정함 |

**모르는 것**:

- $\delta_{ol}$, $t_c$ 실제 값(V-5, V-6, L-6, L-7, U-R8-9 ④). 가정 범위로 쓴다. LC의 Hopsan 기준은 없다.
- 새 플랜트에서 11.5의 이득(창 중앙값 0.72 → 0.17 s)이 실제 과보수를 얼마나 줄이는지. 11.5도 정량할 수 없다고 적었다.
- $u_{ol}$ 아래의 0이 아닌 작은 명령: 11.4는 흐른다고 가정한다. 같은 문서 12절은 실기에서 체크가 열리지 않는 해제 4건을 적었다(0.13~3.6 % $v_{max}$). 이 차이는 모델에 없다.
- $t_c$ 동안 이동 감쇠를 쓰는 가정의 영향.

- 실기 값 전부: 중립 형식(V-6), $V_{line}$, $\psi$, $p_{cr}$, 체크 포핏 특성, $\Delta p_c$, $\Delta p_{LS}$, $\tau_v$. 답이 없으므로 **ASSUMPTION** 범위로 쓴다.
- S8 F-5 원인: 유량과 정지 위상을 분리하지 못했다(`decision_log.md:333`). V2~V7의 S8 실패는 새 실패로 세지 않고 이 한계로 기록할지 기준에 적는다.
- 커널 마찰 상태 $f$와 L2b $f$의 부호가 같은지(C-6으로 확인).
- M2 + 마찰 경로, M2 + M1c, M1c + 유량, 신장 뒤 수축의 M2: Hopsan 기준 없음.
- M2의 $p_{bB}$ 5 bar가 C3·비틀림을 약간 나쁘게 한다(최대 +0.5 kN, 원인 미시험).
- 저속 수축 리밋 사이클(7.8~8.7 Hz)은 넣지 않는다. 실제 여부 미상, M-시험 뒤.
- **M2 개정 3의 알려진 한계**(사용자 결정 2026-11-06: 기록만, 제조사 답 V-5·V-6·L-6·L-7 뒤 재검토. 대칭 오버랩 P-B는 채택하지 않음):
  - **반전 lost motion**: 독립 두 챔버 + 파일럿 체크 모델(scratchpad `hyd_m2fix/`)에서 수축 반전 때 명령보다 늦는 lost motion이 FL 1.04 mm(범위 0.94~1.04 mm, B 호스 포함 FL 1.49 mm)로 나온다. 개정 2·3 법칙 모두 이것을 넣지 않는다. 반전 직후 실제 거동은 "앞서는 킥"보다 이 늦음이 지배적일 수 있다.
  - **신장→수축 overrun**: 같은 모델에서 $\psi\,p_T$(3.5 × 2 = 7 bar)가 크래킹 3 bar보다 크면 체크가 차압 거의 0으로 열린 채 남고, 신장에서 수축으로 바꿀 때 A→T 노치로 부하압이 배수되어 다리가 더 내려간다. 크기는 정량하지 않았다. 중립 형식(V-6)과 파일럿 연결(L-7)에 달렸다.
  - **최소 제어 유량**: 개정 3에서 미세 명령의 로드 압력 변화는 느리다(FL 승압 5 → 34.8 bar: 1 % $v_{max}$ 6.8 s, 0.1 % $v_{max}$ 68 s; 감압: 1.6 s, 16 s). 실기 스풀 불감대(V-5)에서는 0.1 % $v_{max}$급 명령이 아예 흐르지 않을 수 있다. 제어기 완료(DONE·READY)가 이런 명령에 의존하면 실기에서 끝나지 않을 위험이 있다(모델은 작은 명령도 흐른다고 둔다, 2.5절 L-6과 같은 가정).
  - **B 호스 컴플라이언스**: $C_r$에 로크 블록 밖 B 호스를 넣지 않았다(**ASSUMPTION**). 체크가 열린 이동 중에는 호스 기름도 압축되므로 넣으면 $C_r$이 +32~36 % 커진다(FL 1.80 → 2.37×10⁻¹² m³/Pa, $V_{line}$ 285 cm³, $\beta_h$ 0.5 GPa 가정). 승압·감압 시간이 같은 비율로 길어지고(1 % $v_{max}$ 수축 6.8 → 9.0 s), M2-1은 10.702 → 10.703 kN, 3자유도 정착값은 2.456 → 2.458 kN이다. 감도로만 본다.

**⑥ 압력만 판정 비교: 하네스와 Chrono 설정 차이**(2026-11-06): 하네스 ⑥ 압력만 판정(`c2py_r8d1_closed_loop.preset_config(ContactJudge.PRESSURE, with_imu_samples=True, with_reapproach=True)`)과 Chrono `N_G4_*_pressure`는 접지 판정 코드가 같다(`ContactJudge.PRESSURE`, `C2Controller._load_estimate_N`이 `forces.lower`를 그대로 씀). 설정은 `reanchor.enable`, `target.acceptance`, `target.check_time_s`, `target.slope_limit_mode`, `zero_calibration.mode` 다섯 가지가 다르고, 같은 차이가 결합 판정 짝(하네스 COMBINED 대 Chrono `E_G4_Fs4`)에도 있다. 그래서 하네스 안의 짝 비교(압력만 대 결합, 같은 행·위상·설정)는 이 차이의 영향을 받지 않고, 하네스 값을 Chrono N_G4 값과 직접 맞댈 때만 걸린다. 사용자 결정(2026-11-06): 그대로 구현한다. 판정 근거는 봉인 기준 13.4(1 ms 진값·하한, 창 뒤 놓침 구간 수)이고, Chrono식 10 Hz 지표(명세 `s6_control_spec.md` 203.1~203.3, 키 `event_output.ref_10hz_episodes`)는 참고값이며 판정에 쓰지 않는다. 다섯 설정의 양쪽 값은 손으로 적지 않고 하네스 meta `controller.config.to_meta()`와 Chrono 저장 `controller_meta`에서 읽어 1단계 판정 보고서 ⑥ 표에 붙인다.

**n_late(J11) 정의**(control-expert 2026-11-06): 다리별 명령 0 구간(시작 = 작용 명령이 0.0인 첫 10 Hz 표본, 창 끝 = `_LockStretch.window_end_s`, 닫힘 = 명령이 다시 0이 아닌 첫 표본 또는 실행 끝) 중 작용 명령 0인 열린 표본 가운데 $t_k \ge t_w - 10^{-9}$ s인 것이 있는 구간만 판정하고($t_w - 10^{-9} \le t_{last}$, $t_{last}$ = 닫힌 구간 $t_c - T$, 열린 구간 $t_{end}$; 그 밖은 `unjudged`, 다음 명령이 창 끝 전에 들어온 경우 포함 — 11-06 정정), 창 끝 + 10⁻⁶ s의 플랜트 잠금 상태(`plant.lock_events`)가 풀림이면 늦음으로 센다. 단위는 구간(건), 실행당 다리마다. 관문은 대체 다리의 `n_late_fallback` > 0(VB → H-7, LS → L-e)이고 나머지는 기록이다. 창 끝은 명령 기록에서 다시 계산해 제어기 값과 ≤ 10⁻¹² s로 맞춘다. 결과 키 `lock_window_alignment`, T4h 저장은 VB·LS1~4 행 10 Hz만(세부 키는 구현 커밋 docstring).

**T4h 판정 표본**(사용자 결정 2026-11-06, 봉인 9절 문구는 그대로): 작용 명령(직전 주기 출력)이 0이고 그 다리 플랜트가 표본 시각 $t_k$에 잠긴(`lock_events` 기준) 표본만 판정한다. 대체를 강제한 하한 − `true_force_N` > 0.6 kN인 수가 0이면 잠정 통과다. 명령 0이지만 아직 잠기지 않은 표본(밸브 꼬리 + $t_c$)은 하네스 로드 판독이 기반 법칙의 이동 값(배압 없음, `r64_g4_closed_loop.with_two_pressures`의 ASSUMPTION)이라 진값이 아니므로 판정하지 않고 `unlocked_tail_samples_by_leg`·`unlocked_tail_max_excess_N`으로 기록만 하며, 이 구간은 Chrono T4·T5(기준 13.5)에 맡긴다. 근거: R12 VB 초과 16표본(최대 8.22 kN = (34.82 − 13.0) bar × $A_{ann}$)이 모두 READY 꼬리 신장 뒤 잠기기 전 표본이고, 잠긴 표본에서 하한 − 진값은 −8.3~−10.9 kN(보수 쪽).

**이 명세 밖, 기준 쪽에 적어 둔 v5 항목**(control-expert 기준 작성 때 본다): 항목 8 위상 무관 지표(`decision_log.md:297`), S-4 늦은 LOC FLAG(`:293`), 사건·포화 겹침 합성 사례(`:296`), R12 유량 켬 10.92 kN(`:305`), S6 끔 시드 변경 검토(`:307`), 압력만 판정 비교(`:328`), 토양 빠른 사건 1 ms·0.5 s 통일(`:346`), P3-4 집계 `P3-4_verdict`(명세 433.6). 넣을지는 기준 초안을 본 뒤 사용자가 정한다.
