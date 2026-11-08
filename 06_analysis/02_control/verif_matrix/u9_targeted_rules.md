# U-9 표적 하네스 실행 규칙 (실행 전 봉인)

- 작성: control-expert, 2026-11-08. 실행 전에 봉인한다. 봉인 뒤에는 이 파일을 고치지 않고, 바뀌는 것은 개정판으로 낸다.
- 사용자 결정(11-08)
  - U9-1 = (나): 표적 하네스 실행을 추가하고, 단서와 한계 기록을 함께 남긴다.
  - U9-2: 감도로만 기록한다.
  - U9-3: 문장을 수정한다.
- 근거 해석: `u9_saturated_margin.md`. 위치는 세션 scratchpad `ctrl_u9\`이고, 값 출처는 `u9_saturated_margin_values.json`·`recorded.json`이다.
- 규약
  - 되먹임은 음되먹임이다.
  - 제어기는 C2 R8-D1이다. 주기 T = 0.1 s, 출력 지연 d = 1, 밸브 지연 τ_v는 하네스 모델을 따른다.
  - 하네스 청크는 1 ms다.
  - 단위는 SI다. 각도는 deg로 표시한다.

## 1. 목적과 배경

선형 해석(U-9)의 결과는 다음과 같다.

- 앞 다리만 압력 제한되는 포화에서는 여유 기준을 만족한다. 근거가 두 가지다.
  - 기록 운전점(T4_inputs 30점, FL+FR·FL): M_s ≤ 1.4228, 가드 ≤ 1.4256, α ≥ 0.6196, 개루프 안정.
  - 재구성 포락선 403점: M_s ≤ 1.4223.
- 세 다리 이상이 동시에 제한되면 선형 여유가 기준을 넘는다.
  - 세 다리: M_s 1.512~1.519.
  - 네 다리: 개루프 roll·pitch가 발산한다(실근 ≤ +0.12 s⁻¹). M_s 1.44~17.9.
  - 원인은 부하 압력이 유량 분배에 되먹이는 경로(J_F)와 높은 무게중심의 하중 이동이다.
- 1단계 VB 100행에서 세 다리 이상 제한은 1 s 미만의 과도로만 나타났다.
  - 해당 행은 S2·S3 6행이다. 이 행들의 LEVEL 최소 r은 뒤 다리 0.976~0.985다.
  - T4_inputs의 1 s 이상 집합은 LEVEL에서 FL+FR·FL뿐이다.
- 그래서 시간 영역 근거가 없다. 이 실행은 공급을 줄여(η_v 0.80) 그 영역을 일부러 길게 만들고, 발산 징후가 있는지 본다.

사전 예상(정적 법칙 계산, `u9_eta_probe.py`)은 다음과 같다. 기록된 S2·S3 LEVEL 운전점의 u·p_L을 그대로 두고 η_v만 0.80으로 바꾸면, 앞 다리 r은 0.80 → 0.69로 깊어진다. 그래도 제한 집합은 FL+FR 그대로다. 이 때문에 S2·S3만 돌리면 세 다리 이상 영역이 나오지 않을 수 있다(결과 B). 그래서 압력이 맞물리기 쉬운 보조 사례 두 가지를 넣는다.

- R3: 강체, 앞들림 3.5°. 뒤 다리 하중이 커져 앞뒤 부하 압력이 비슷해진다. 선형 격자에서 네 다리 제한이 나온 조건이다.
- S5: J2 운용 중량 ×1.1. 1단계에서 LEVEL 포화가 가장 길었다(3.04 s).

## 2. 대상 키와 설정 (42 실행)

| 군 | 사례(`verdict_cases`) | ε(접근 속도 배율 위상) | 키 수 | 근거 |
|---|---|---|---|---|
| A(기록 계열) | S2(J2 B 상단 F_s 4), S3(J2 B 중단 F_s 4) | S2: 0, 1e-3, 2e-3, 3e-3. S3: 0, 2e-3(`main` 회귀 위상 그대로) | 6 | 1단계에서 LEVEL 네 다리 제한이 나온 6행 |
| B(압력 맞물림 후보) | R3(강체 상단 앞들림 3.5°, F_s 4) | 0, 1e-3, 2e-3, 3e-3 | 4 | 선형 격자에서 네 다리 제한이 나온 조건 |
| C(긴 노출) | S5(J2 B 상단 ×1.1) | 0, 1e-3, 2e-3, 3e-3 | 4 | 1단계 LEVEL 포화 최장 |

- 키마다 설정 3개를 돌린다.
  - `V0`: 유량 제한 꺼짐, `final_C4G2`. J 판정의 짝이다.
  - `VB` η_v 0.85: `final_C4G2_P3`, ③ 켬. 기준선이다.
  - `VB` η_v 0.80: 같은 정의에서 공급만 48.16 L/min으로 줄인다.
- 14키 × 3설정 = 42 실행이다.
- η_v 0.80은 VB 정의(η_v 0.85) 밖이다. 이 결과는 인수 판정이 아니라 논문 3.5.1의 보충 근거로만 쓴다.

## 3. 실행 방법 (코드 확인 결과와 위임 명세)

### 3.1 코드 확인 결과

- `04_scripts/04_hydraulic/coupled/run_v5.py`의 `ETA_V = 0.85`는 모듈 상수다. `options_of(setting)`가 이 값을 쓴다.
- 배치 목록은 `batch_jobs` 안에 고정돼 있고, CLI 인자는 `batch`, `--workers`, `--mask`, `--list`뿐이다. 그래서 **현행 CLI로는 η_v를 바꿀 수 없다.**
- 하네스 쪽 `harness_flow.FlowSetting(eta_v=…)`는 이미 임의의 값을 받는다. 그러므로 바꿀 곳은 `run_v5`뿐이다.
- 현행 기록에는 "동시에 제한된 다리 수별 시간"과 "제한 구간 중 자세 변화"가 없다.
  - `E4.group_time_s`는 잔여 압력 동률 묶음이지 제한 집합이 아니다.
  - `T4_inputs`는 1 s 이상 지속된 구간만 담는다.
  - 그래서 지표를 추가해야 한다.
- 저장된 `main.jsonl`의 VB 줄은 ③ 꺼짐(r5)이라 `run_v5`가 같은 파일에 이어 쓰기를 거부한다. 새 배치는 새 파일 `06_analysis/03_hydraulic/coupled/v5/u9_targeted.jsonl`에 쓴다.

### 3.2 python-expert 위임 명세 (worktree, 병합 전 시험)

| # | 변경 | 시험 |
|---|---|---|
| P-1 | job에 선택 키 `eta_v`(float)를 둔다. `options_of(setting, eta_v=None)`는 유량이 켜진 설정에서 `eta_v`가 있으면 그 값을, 없으면 `ETA_V`를 쓴다. V0처럼 유량이 꺼진 설정에 `eta_v`가 있으면 거부(ValueError)한다 | 키가 없는 모든 기존 배치(`main`, `smoke`, `w2`, `item8`, `overlap`, `pressure_only`, `p3_hash`)의 `batch_jobs` 출력과 `job_key`가 변경 전과 같다. `smoke` 골든 해시도 같다 |
| P-2 | 새 배치 `u9_targeted`를 둔다. 2절의 14키 × [`{"setting":"V0"}`, `{"setting":"VB","eta_v":0.85,"u9_metrics":true}`, `{"setting":"VB","eta_v":0.80,"u9_metrics":true}`] = 42 job이다. V0 job에도 `"u9_metrics": true`를 붙인다. 지표 함수는 유량이 꺼져 있으면 빈 값을 낸다 | `--list`가 `u9_targeted: 42 runs`를 출력한다. 출력 파일은 `u9_targeted.jsonl`이다. T4h는 VB만 `u9_targeted/t4h/`에 쓴다 |
| P-3 | `verdict_metrics`에 `u9_values(rows, phases, period)`를 추가하고, job에 `u9_metrics`가 있을 때만 `values["U9"]`에 넣는다. 다른 배치의 출력 키는 바뀌지 않는다. 내용은 3.3절과 같다 | 합성 청크 행으로 시험한다. ① k별 시간과 최장 구간, ② 구간마다 Δ자세 최대와 시작·끝 필터 오차, ③ 구간이 없으면 빈 목록 |
| P-4 | 결정성 대조: `u9_targeted`의 `VB` η_v 0.85 S2 ε 0 줄의 `commands_sha256`이 `p3_hash.jsonl`의 S2 줄과 같아야 한다(같은 VB 정의, 같은 공급) | 실행 뒤 control-expert가 H0로 확인한다(4절) |
| P-5 | 프리셋·클래스 기본값, `final_C4G2`, VB 정의는 바꾸지 않는다 | 기존 시험 전부 통과 |

### 3.3 지표 `values["U9"]` 정의

| 키 | 정의 | 단위 |
|---|---|---|
| `level_count_s` | LEVEL 단계(`chunk_phases == "level"`)에서 제한 다리 수 k(`limited_mask`의 비트 수, 이동 중인 다리만: \|u\| > 1e-6 m/s)가 1, 2, 3, 4인 청크 시간 | s |
| `post_touch_count_s` | 같은 집계를 TOUCH가 끝난 뒤의 모든 단계에서 한 것 | s |
| `longest_ge3_s`, `longest_eq4_s` | LEVEL에서 k ≥ 3, k = 4인 가장 긴 연속 구간 | s |
| `ge3_runs` | LEVEL k ≥ 3 연속 구간 가운데 0.1 s 이상인 것(최대 50개). 구간마다 다음을 담는다. `t_start_s`, `dur_s`, `set_at_middle`, 참 자세 roll·pitch의 시작값과 구간 안 `max_abs_delta_deg`(\|att(t) − att(t_start)\|의 축별 최대), 10 Hz 필터 자세의 시작·끝 값(`filtered_start_deg`, `filtered_end_deg`, 시작 시각 이전의 가장 가까운 주기와 끝 시각 이후의 가장 가까운 주기), 축별 참 자세 각속도 최대 \|φ̇\|, \|θ̇\| | s, deg, deg/s |
| `level_sat_rate_max_deg_s` | LEVEL에서 k ≥ 1인 청크의 참 자세 각속도 최대(축별) | deg/s |

## 4. 판정 기준 (실행 전 고정)

- 판정은 η_v 0.80 VB 줄마다 한다. 기준선(η_v 0.85 VB)과 V0 짝은 같은 키의 줄이다.
- 문턱 가운데 근거가 명세에 없는 값은 **가정**으로 표시했다.

| # | 항목 | 기준 | 비고 |
|---|---|---|---|
| H0 | 기록 정합(판정 전 확인) | ① η_v 0.85 VB S2 ε 0, S3 ε 0, R3 ε 0, S5 ε 0의 `commands_sha256`이 `p3_hash.jsonl`의 같은 사례 줄과 같다. ② 나머지 ε 키는 `main.jsonl` VB 줄과 비교해 같은지 다른지만 기록한다 | ①이 다르면 판정하지 않고 멈춰 보고한다 |
| T1 | J 항목 | v5 기준 개정 8의 J1~J11과 J-P3을 V0 짝에 대해 적용한다(J3 한계는 `v5_criteria.md` 7절). η_v 0.85 기준선에도 같은 판정을 한다 | 기존 규칙 그대로 |
| T2 | 노출(기록) | `level_count_s`, `longest_ge3_s`, `longest_eq4_s`, E1 LEVEL `short_s`, E2 LEVEL 최소 r, E4 | 기록만 한다 |
| T3a | 발산 징후 없음(구간) | `ge3_runs`의 모든 구간에서 축별 `max_abs_delta_deg` ≤ **0.10°** | 가정: 정확도 ±0.2°의 절반 |
| T3b | 구간 끝 수렴 | 모든 `ge3_runs`에서 축별 \|`filtered_end_deg`\| ≤ \|`filtered_start_deg`\| + **0.05°** | 가정 |
| T3c | 전체 자세 | `attitude.max_abs_after_liftoff_deg`(η_v 0.80) ≤ 같은 키 η_v 0.85 값 + **0.10°** | 가정 |
| T4 | 포화 뒤 복귀 | E5 `back_in_band_after_saturation_s` ≤ max(**20 s**, 같은 키 η_v 0.85 값 + **5 s**). 값이 없으면(띠로 돌아오지 않음) 실패. E5 `max_abs_integral_rad_s`가 한계(0.02)에 닿으면 FLAG로만 기록한다 | 가정. 1단계 S2·S3는 12.7~17.1 s |
| T5 | READY 지연(기록) | η_v 0.80 − η_v 0.85의 `t_first_ready_s` 차 | J3이 판정한다. 차이는 기록만 한다 |

### 4.1 결과 분류와 논문 문구 (사전 고정)

포화 원인 실패는 "V0 통과, VB η_v 0.85 통과, VB η_v 0.80 실패"인 경우를 말한다.

| 분류 | 조건 | 3.5.1 문구(요지) |
|---|---|---|
| **A** | 모든 키에서 T1(포화 원인 실패 0), T3a~c, T4가 통과하고, 어느 한 키에서든 `longest_ge3_s` ≥ 0.5 s | "공급을 η_v 0.80(48.2 L/min)으로 줄여 LEVEL에서 세 다리 이상 동시 제한을 최장 {x} s(네 다리 {y} s)까지 늘려도, 제한 구간의 자세 변화는 최대 {z}°였고 포화 뒤 {w} s 안에 ±0.03° 띠로 돌아왔다. 고정 운전점 선형 여유는 이 영역에서 기준을 넘지만(M_s ≤ 1.52, 네 다리는 개루프 발산 시정수 ≥ 8.2 s), 노출 시간이 그보다 짧아 시간 영역에서는 드러나지 않는다. 선형 여유의 보증 범위는 앞 다리 제한까지다(한계)." |
| **B** | 판정은 A처럼 통과했지만 모든 키에서 `longest_ge3_s` < 0.5 s | "η_v 0.80 표적 조건에서도 세 다리 이상 동시 제한은 최장 {x} s로 짧았다. 앞 다리 제한은 깊어졌다(최소 r {r}). 그래서 시간 영역 확인은 앞 다리 제한 영역에 한정된다. 세 다리 이상 제한에서 선형 여유가 미달하는 것은 검증하지 못한 한계로 남긴다." |
| **C** | 어느 한 키라도 포화 원인 T1 실패, 또는 T3a·T3b·T4 실패 | "η_v 0.80에서 {항목}이 실패했다({키}, {값}). 펌프 체적 효율이 0.85 아래로 떨어지면 포화 중 자세 루프의 강건성을 보장하지 못한다. 이 결과로 η_v ≥ 0.85를 하드웨어 요구로 두거나, LEVEL 들어 올림 명령을 유량 예산(Σ A_i u_i ≤ Q_sup) 안으로 제한해야 한다." → **사용자 결정**(요구 추가 또는 제어기 변경) |
| D | 포화가 원인이 아닌 실패(η_v 0.85 기준선도 실패, 또는 V0도 실패) | 기존 결과와 같은 사유로 따로 기록한다. 분류는 나머지 키로 정한다 |

- T3c만 실패하고 나머지가 모두 통과하면 C로 분류한다. 다만 문구에 "전체 자세 첨두 증가"를 명시한다.
- 공통 문구는 U9-2·U9-3 결정에 따른다. 어느 분류에서든 넣는다.
  - U9-3: "유량 포화는 대각 이득 오차가 아니라 비대각 분배 행렬이므로, 다리 입력 디스크 여유(α 0.69, 이득 0.49~2.05)로는 덮지 못한다. 분배 야코비안을 루프에 넣어 직접 계산했다."
  - U9-2: "+20 ms 출력 지연 감도에서 α는 포화 중 0.546(비포화 0.615)이다."

## 5. 건수·예상 시간·실행 명령 초안 (메인 세션이 compute-scheduler-expert 배치표로 실행)

- 건수: 42 실행. 실행마다 spawn 작업자 1개를 쓴다(`maxtasksperchild=1`).
- 예상 벽시계(1단계 `main.jsonl` 실측 기준): VB는 S2·S3 60~83 s, R3 50~66 s, S5 85~90 s이고 V0는 27~50 s다. 합계 직렬로는 약 2,900 s다. P코어 12 작업자이면 약 5~8분, E코어 섞임 배율 1.7을 넣어도 15분 이하로 예상한다.
- 사전 단계(python-expert 병합 뒤): `--list`로 42건을 확인한다. 시험 P-1~P-5가 통과해야 한다.
- 실행 명령 초안(프로젝트 루트, PowerShell):

```powershell
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B C:\workspace\outrigger_control\04_scripts\04_hydraulic\coupled\run_v5.py u9_targeted --list
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B C:\workspace\outrigger_control\04_scripts\04_hydraulic\coupled\run_v5.py u9_targeted --workers 12 --mask <compute-scheduler 배정 마스크>
```

- 출력은 `06_analysis/03_hydraulic/coupled/v5/u9_targeted.jsonl`과 `06_analysis/03_hydraulic/coupled/v5/u9_targeted/t4h/`(VB만)다.
- 판정: control-expert가 4절 규칙으로 오프라인 판정한다. 판정 스크립트는 scratchpad에 둔다. 입력은 `u9_targeted.jsonl`과 `p3_hash.jsonl`(H0)이다.

## 6. 가정

| 가정 | 값 | 근거 |
|---|---|---|
| 공급 | η_v 0.80 → 48.16 L/min(펌프 60.2 L/min) | 사용자 결정 U9-1 (나) |
| 발산 문턱 | T3a 0.10°, T3b +0.05°, T3c +0.10°, T4 max(20 s, 기준선 + 5 s), A/B 경계 0.5 s | 정확도 ±0.2°와 1단계 S2·S3 복귀 12.7~17.1 s에서 정했다. 명세 값은 아니다 |
| 보조 사례 | R3, S5 | 1절 사전 예상(S2·S3만으로는 세 다리 이상 영역이 생기지 않을 수 있음) |
| 잡음 | 없음(결정적, `run_v5` 그대로) | — |

## 7. 봉인

SHA-256은 `u9_targeted_rules.sha256`에 적는다. 바꿀 때는 `u9_targeted_rules_rev1.md`와 새 해시로 낸다. 결과를 본 뒤 바꾸는 경우에는 그 사실을 적는다.
