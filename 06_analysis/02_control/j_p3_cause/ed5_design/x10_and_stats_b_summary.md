# 판 5 VBK 관문: 주입 기능 조사(python-expert)와 통계 재설계(stats-design-expert) 요지 — 2026-11-21

## A. python-expert X-10 조사(읽기 전용)
- **r79 잡음 경로에는 로드 센서 고장 주입이 없다.** 쓸 수 있는 것은 둘이다.
  - `FaultyRodSensor`(STUCK/OFFSET/DROPOUT): `03_src/outrigger_sim/sensors/hydraulic.py:457-492`
  - Chrono 전용 `RodFaultInjection`: `run_S8C.py:1396-1441`. 첫 READY 뒤에만 무장한다.
- 대체 래치 경로(`two_pressure.py`)
  - DROPOUT → `D1_nonfinite`, 즉시 `_fall_back`
  - 범위 밖 값 → `D1_range`
  - STUCK → `D1_stuck`. 10 s가 지나야 하고 잡음 > 0일 때만 걸린다(L1에서는 걸리지 않음)
  - 래치는 초기화에서만 풀린다.
- **최소 구현안**
  - 주입 지점: `r79_sensor_screen.py` `ActiveRun.after_period`(:462-471)의 `adapter.deliver` 뒤 한 곳(G6·ref·G8 공통). 센서 오차 모형 뒤, 제어기 입력 직전이다.
  - 새 모듈 `rod_fault_plan.py`, 환경 변수 `R79_ROD_FAULT_PLAN=<plan.json>`
    - 키마다 고장 하나: leg·kind·value·anchor(`t:` 또는 `phase:`)·delay
  - 설정: `JP3_SETTINGS`에 VBK·VBK0을 추가하고, `common.ps1` `$R79RodModel`에 넣는다.
  - 정체성 가드: 설정과 계획이 짝이 안 맞거나, 계획이 비었거나, 키가 어긋나면 종료 2.
  - 키 문법은 그대로 둔다(안 B). 정체성은 설정 이름 + `plan_sha256` + 행 `rod_fault.fault_id`로 남긴다.
  - 기록: 행 `rod_fault`(armed·first_applied·applied_periods·latched), meta `rod_fault_plan`, T4h 주입 전 rod 판독과 `rod_fault_applied`.
  - 명령 불변: 계획이 없으면 모듈을 import하지 않는다. 시험 (a)~(e)로 확인한다(계획 없음 비트 동일, 끝 뒤 무장, FR dropout 래치, B2 등식, VBK0 계획 없음 거부).
  - 규모: 신규 약 150줄 + r79 약 50 + L3L4 약 20 + run_v5 약 8 + 시험 약 250줄. 반나절~하루.
- **부작용 경고**
  - DROPOUT(NaN): 네 다리 순 힘 합 `_net_sum_N`이 NaN이 되어 헤드 점프 설명 규칙(D1′·D1″)이 모든 다리에서 꺼진다. 그러면 대체 뒤 헤드가 한 주기에 100 bar를 넘게 바뀔 때 `FAULT_HEAD_PRESSURE`가 날 수 있다(코드 읽기).
  - 범위 밖 유한값: 합이 틀려져 설명 규칙이 치우친다.
  - NaN은 T4h, ③ trace, `t4h_replay`에도 들어간다.
  - CHECK 중 주입은 영점 교정 경로를 바꿀 수 있다 → CHECK 기준 무장은 막기를 권고.
- X-10 "주입 끔 = 비트 동일"의 해석: (i) 코드 변경 전후 VBJ·VBJ0 동일, (ii) VBK0(계획 없음) = VBJ0, (iii) rev 6 무주입 = rev 5(T8 문제). 구현은 (i)·(ii)를 보장한다.

## B. stats-design-expert VBK 재설계(오염 후; 근거 `stats_b/`, SHA256SUMS)
- 권고: **L2 167사례 × seed 2(30, 31) = 334짝**, 0 건수. P 4 worker로 약 63분(가정 5.63 s/회).
  - 셀 = 다리 4 × 국면 2(τ_C 운반 전, τ_R 수축 전) = 8. 배정은 rank mod 8이고 두 블록에 같은 셀을 쓴다.
  - 고장 종류는 대체 래치를 거는 것 1개.
  - 국면 트리거를 쓴다. 두 쪽 명령이 주입 전까지 같다는 보장이 없으면 VBK0의 트리거 시각을 VBK에 절대 시각으로 쓴다.
  - "시작부터 주입"은 CHECK 영점 교정 문제로 비권고.
- 바닥 근거: 저장 L2 seed 간 READY 상실 0/3,340(상한 0.09 %). 등급 대리값 pass→fail 3/835(0.36 %).
- **문제: 13.9절 "L2 통과 → 실패 0"을 334짝 전부에 걸면 무해한 rev 6도 약 70 %가 떨어진다**(N=167에서 45 %, 501에서 84 %).
  - 선택지: (a) 등급 전이는 기록, READY·FAULT만 0 건수(권고) / (b) L2 판정 행 1개 지정 / (c) 등급에 따로 k_g / (d) 그대로.
- 검출: N=334, 0 건수에서 짝당 결함률 δ 1 %를 놓칠 확률 2 %, δ 0.5 %에서 약 19 %. MDE80은 0.48 %.
- 무해 기각(바닥 c·f)
  - c 0.3·f 0.1 %이면 9.5 %
  - c 0.5·f 0.35 %이면 44 %
  - ≤1을 허용하면(N=334) 0.5 %, 12 %
  - 비교 표 전문은 `stats_b/vbk_gate_tables.txt`·`rule_compare.json`.
- ĉ ≥ 0.5면 다시 묻는다. 그때 고를 안은 (가) N 334·≤1 또는 (나) N 501·≤1이다.
- 기회 수 N_opp: VBK0가 READY에 닿고 주입 뒤 국면 읽기가 있는 짝 수. N_opp < 0.9N이면 블록 32를 더한다.
- **A/A 바닥 멈춤(권고)**: 새 쪽을 열기 전에 VBK0 seed 30 대 31에서 READY 상실 또는 +30 s가 3건 이상이면 멈추고 다시 묻는다.
- c 건식 확인: seed 90·91, 20사례 × 8셀 = 160짝, 약 30분, ĉ 반폭 ±8 %p.
- 오염: 이번에 열린 문서(유압 검토 4~9절, control 통합)에 판 4a 유래 수치가 있었다. 계산에는 쓰지 않았다.
