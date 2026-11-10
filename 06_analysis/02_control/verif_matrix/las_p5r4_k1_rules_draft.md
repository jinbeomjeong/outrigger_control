# [DRAFT, 봉인 전] LAS-b P5r4 + K1 재판정 규칙 (새 원판 초안)

> **DRAFT, 봉인 전.** 이 파일은 초안이다. 판정에 쓰지 않는다. 이 파일의 sha256은 봉인 값이 아니다.
> - 봉인 때 파일 이름: `06_analysis/02_control/verif_matrix/las_p5r4_k1_rules.md` + `las_p5r4_k1_rules.sha256`(LF, BOM 없음으로 계산).
> - 봉인 때 이 인용 블록과 15절(확인 필요)을 지우고, 15절 답을 본문에 반영한다. 봉인·실행 전 감사·실행 시작은 메인 세션이 사용자 승인을 받아 한다.
> - 봉인 전에 `.gitattributes`에 `06_analysis/02_control/verif_matrix/las_p5r4_k1_rules* -text`와 `06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/*.jsonl -text`를 더한다(지금 `las_k1_rules*` 줄은 이 이름을 덮지 않는다).

- 작성: control-expert, 2026-11-10. 기준 master `b53d890`(K1 전환 병합).
- 판의 성격: **새 원판**이다. A안 규칙(`las_revA_targeted_rules*`)의 rev가 아니다. 이유는 0.1절.
- 사용자 결정
  - 2026-11-09: "LAS-b P5r4는 K1 채택 뒤 P5r4+K1을 다시 판정한다(새 봉인 규칙 + Chrono)."
  - 2026-11-10: 판정 묶음은 **새 `_K1` 태그로 재실행**한다. `pre_k1_preset_runner.py`는 옛 결과 재현에만 쓴다.
- 이어받는 규칙(바꾸지 않는다. 이 판과 다르면 이 판이 맞다)

| 파일 | sha256 | 이어받는 것 |
|---|---|---|
| `las_rev_targeted_rules.md` | `bb235f27567240b205a544ed7cfd10237827e4627088e0eab1f62b318416ff60` | 5.0 None 규칙, 5.2 C-2형·C-1·C-F·C-S·A-3·R-1·R-2·$\mathcal{P}$, 5.3, 6 C-4 예외, 4.2 DONE 기록 |
| `las_rev_targeted_rules_rev1.md` | `672bc8f81ba75419e5a201e05a94e2f9aead2de3c205f80c2661e7474cd9fd51` | 그대로 |
| `las_revA_targeted_rules.md` | `b09d004bb2f641db40cdd139a6fb2b1645651e4a3e45a9b16e81a5c938d5778f` | P5r4 정의(1.2·1.3), K-A1~K-A8, R1-1~R1-4, 6 램프 끝 조건 |
| `las_revA_targeted_rules_rev1.md` | `c02518021c00b69a9d02ec6bceddbea18b9686ef6de96bafe5e55b716b023960` | 그대로 |
| `las_revA_targeted_rules_rev2.md` | `9f478b7fbc5aa0bd8859716b056bf2d531ac02057dc36d218bada7d7f13e4565` | G-2′(11.414589 kN), R-0A·R-Q 정의 |
| `las_revA_targeted_rules_rev3.md` | `98082a368da626f90ce3b0a41f5c74145b4095c155f14b2b2f63eb319352d709` | Q-2 무리 정의(기록용) |
| `las_k1_rules.md` | `2742c9760ad55a87eccbf73e84025aafe0171a3555e1f54ab19fab24d888e4a0` | K1 정의 1.1·1.2, 4.3 C-2형·P3·C-S·C-F |
| `las_k1_rules_rev1.md` | `eeee4ab9661babff50117b8ff579aa41e27a98d083f1fc13f46fb5c733e0b4d3` | R1-1 P3 짝 정의, R1-2 C-2형 = `pair_violations` 정의 |
| `las_k1_rules_adopt.md` | `864836d852b4a783a577f01f738536b7c30c574bf4bebb3b0219e68e59b07ea8` | 9.2 원칙(봉인 판정 도구 상수 불변) |
| `las_k1_rules_adopt2.md` | `fb3a5696f24385e81acc9c564500b5e5a0547db45a5335272e7d18400f1e68e8` | decision 표·$L_1$·`POS`/`NONPOS`/`LATE_STRUCT`/`NO_R4`, K-0~K-10 꼴, 7 결측 |

- 규약
  - 제어: 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1(주기 $k$의 명령은 $t_k+0.1$ s에 플랜트에 들어감), C2 음되먹임. $u$ = 다리 행정 속도 명령 [m/s]. 상태 되먹임 부호는 바꾸지 않는다.
  - 다리 순서 FL, FR, RL, RR(0~3). 힘은 실린더 순 힘 [N](표는 kN). $F_{min}$ = 9,414.589 N. 행정은 모터 행정 [m](표는 mm).
  - 시각 비교는 정수 주기 $n=\mathrm{round}(t/0.1)$(Python 내장)로 한다. Chrono 시각은 8 s 정착을 포함한 절대 시각이다.
  - **이름 주의**: 이 규칙의 "K1"은 R4c30 순서 관문(`slope_clearance_margin.flat_soil_margin_order_gate`)이다. 하네스 키 토큰 `K1`·`K3`(크롤러 강성 ×1·×3)과 다르다. Chrono 크롤러 강성 변형은 이 규칙에서 **Kc1·Kc3**로 적는다.

| 기호 | 뜻 | 단위 |
|---|---|---|
| P0 | LAS-b b0(β 3.5, $n_{min}$ 0, $N_r$ 0) = 채택 프리셋 | — |
| P5r4 | β 4.5, $n_{min}$ 0, $N_r$ 4(A안 1.2·1.3) | — |
| ref / cand | 짝의 기준(P0+K1) / 후보(P5r4+K1) | — |
| $F_{RL}$, $F_{judged,min}$ | 하네스 `diag.summary.F_RL_kN`, `F_judged_min_kN` | kN |
| $F^{C}_{after}$, $F^{C}_{tr}$ | Chrono `p3b.P3-3_leg_force.F_min_after_N`, `F_min_transient_N`(1 ms 참 $F_{cyl}$, 크롤러 이탈 뒤) | N |
| $s_{max}$ | 하네스 `d1.stroke_max_m`, Chrono `p3b.P3-5_clearance_stroke.s_motor_max_m` | m |
| $L_1$, dP | adopt2 기호 그대로(첫 R4 평가 LOC, $n_P-n_S$) | —, 주기 |
| $\lambda_0$ | 램프 시작 축척(A안 1.1) | — |

## 0. 목적과 판의 성격

### 0.1 새 원판으로 하는 이유

1. 짝의 기준이 바뀐다. A안 rev2의 기준 L은 **저장된 b0 줄(K1 꺼짐, 옛 태그)**이었다. 이 규칙의 기준은 **새 프리셋(P0+K1)으로 다시 돈 줄**이다(사용자 결정 11-10). 대상 집합·정체성 검사·도구가 모두 다르다.
2. Chrono 묶음이 새로 들어간다. A안 규칙에는 Chrono가 없었다(A안 10절 한계).
3. 봉인된 판정 도구(`las_rev_judge.py`, `las_revA_judge.py`, `k1_judge.py`, `fb_judge.py`, `u3_judge.py`, `las_k1_rem_judge.py`, `las_k1_sch_judge.py`, `las_k1_adopt_judge.py`)는 옛 태그 상수를 갖는다. adopt 9.2 원칙대로 고치지 않는다. 그래서 **이 규칙은 그 도구들로 판정하지 않고 새 도구 둘(11절)로 판정한다.** 앞으로 다른 규칙이 그 봉인 도구를 `_K1` 태그 결과에 쓰려면 그 규칙의 개정판(새 태그 상수 명시) 또는 새 도구가 필요하다.

### 0.2 질문

**K1 채택 제어기(P0+K1, 태그 `final_C4G2_LAS_K1` / `final_C4G2_P3_LAS_K1`)에서 LAS-b를 P5r4로 바꾸면, 나빠지는 것 없이 이륙 뒤 최소 힘 하한이 지켜지는가.** 하네스(재현 + 표본 밖 S-C)와 Chrono(혼합 지형·연약 지면)로 본다.

- 통과하면 **P5r4 채택 권고**다. 채택(프리셋 β·$N_r$ 변경, 새 태그, 전환 전 재현기, 전환 후 감사)은 사용자가 정하고 별도 전환 규칙으로 한다. 이 규칙은 프리셋을 바꾸지 않는다.

## 1. 봉인 전에 본 것 (공개)

### 1.1 이미 본 P5r4 결과 (과적합 공개)

| 자료 | 본 범위 | 이 규칙에서의 지위 |
|---|---|---|
| A안 rev2 판정서 `las_revA2_judgement.md`(R-0A 54, R-Q 48, R-T 192, R-S 30, R-P0 149, R-X 4) | 판정 값 전부 | Z-A·Z-T·Z-S는 **같은 키의 재실행**이다. 기구 확인·재현일 뿐 일반화 근거가 아니다 |
| K1 판정서 `las_k1_judgement.md`(Y-Sb P5r4/K1on 30, Y-T P5r4/K1on 192) | 판정 값 전부(경계 키 Y-Sb − Y-Sa −0.116 mm 등) | 같음 |
| 진단 `las_revA_diag_judgement.md`(경계 키 P0·P5·P5r4 3줄), 분석서 `las_revA_RGH_analysis.md` | 전부 | 같음 |
| K1 전환 G-3 재생(457줄, 새 프리셋에서 Y-Pa·Y-Pb·Y-Sa·Y-Sb·Y-T 해시 같음), 전환 후 감사 `las_k1_switch_post_audit.md` | 건수·해시 일치 | Z-S·Z-T 해시 예측의 근거 |
| Chrono: S-Ch 판정서, REM 판정서 `las_k1_rem_judgement.md`(R1~R8·F1·F2) | 판정 값 전부 | C-C 기준 줄의 비트 예측 근거. **P5r4 Chrono 결과는 없다(0행)** |

- **표본 밖 근거**는 다음뿐이다.
  - 하네스 Z-C의 S-C 456 전체 키 중 R-S와 겹치지 않는 **437키**(P5r4로 돈 적 없음)
  - Chrono 12행 전부(P5r4 Chrono 0행, 혼합 지형 행 0행, G1+J1@FL Chrono 0행)
- S-C P0 값: control-expert가 K1 원판 작성 때(2026-11-09) S-C P0 456줄의 $t_P$·$t_S$·LOC·R4·최대 행정을 봤다(K1 원판 0.2). 이번 초안 작성 중에는 값을 읽지 않았다(1.2).

### 1.2 이 초안을 쓰려고 이번에 읽은 것

- 문서: 위 표의 규칙·판정서 전부, 명세 436절(436.7·436.8), 전환 후 감사 원문(main checkout 미추적 파일 `las_k1_switch_post_audit.md`), `session_handoff.md`, decision_log 640~703행.
- 코드(읽기만): `run_S9.py` 1505~1575행(`CONTROLLER_EXPECTATIONS`, `_LAS_EXPECTATIONS`의 β 3.5 고정), `c2.py` `_liftoff_approach_slow_meta`(7948~7975), `LiftoffApproachSlowSettings` 필드(2121~2143), `las_chrono_rows.py`·`las_k1_chrono_rows.py`·`las_k1_rem_chrono_rows.py` 머리말·상수, `s9_batch.py` 369~378행.
- 저장 결과(값을 읽지 않은 스크립트, control-expert scratchpad `p5r4k1\`, `conda run -n dynamics-dev python -I -B`)
  - `scan_keys.py`: 하네스 jsonl 10개의 파일 sha256, 줄 수, `d1.key` 계열 건수, `las.candidate`/`controller_tag` 건수, `wall_s` 합·최대, 최상위 필드 이름.
  - `key_lists.py`: `rev.key` 목록과 목록 sha256(부록 A), S-C ∩ R-S = 19키.
  - `chrono_fields.py`: REM R1 `result.json`의 필드 이름만(`controller_meta.liftoff_approach_slow` 키, `p3b` 하위 키, `c2_setup` 키).
  - PowerShell `Get-FileHash`: REM R1·R4·R7·R8 `controller_commands.npz` sha256(4.4 BT-C 기준값).
- 판정 값(힘·행정·READY·사건)은 이번에 저장 파일에서 새로 읽지 않았다. 판정서에 이미 적힌 값만 인용했다.

## 2. 후보와 기준 정의

| 이름 | 설정 | 하네스 구현 | Chrono 구현 |
|---|---|---|---|
| **ref = P0+K1** | `C2Config().with_10hz_d1()` 그대로(LAS-b b0, 관문 켬) | 프리셋 그대로, K1 토큰 없음 | `--las-candidate P0`(덮어쓰기 없음) |
| **cand = P5r4+K1** | 위 + `replace(las, light_leg_fraction_of_F_min=4.5, end_ramp_periods=4)` | `dataclasses.replace` 한 번 | `--las-candidate P5r4`(11.2) |

- 태그: 두 팔 모두 프리셋 태그다. V0 `final_C4G2_LAS_K1`, VB `final_C4G2_P3_LAS_K1`. 후보 구분은 태그가 아니라 `las_candidate` 필드로 한다(A안 관례와 같음).
- **두 번 적용 금지**
  - K1: 프리셋만 쓴다. 하네스 토큰 `K1on`, Chrono `--k1-order-gate`를 **주지 않는다**. 실효 값은 실행된 제어기의 `controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate`와 `order_gate.enabled`로 확인한다(따로 만든 제어기 값으로 확인하지 않는다, 전환 후 감사 R-5).
  - LAS-b: 덮어쓰기는 한 번이다. 덮어쓰기 전 프리셋이 b0인지(β 3.5, $n_{min}$ 0, $N_r$ 0)와 관문 True를 먼저 확인한다. P0 팔은 덮어쓰지 않는다.
  - `--las-off`, `--k1-forced-block first`, `pre_*_preset_runner.py`는 이 규칙의 행에 쓰지 않는다. 섞이면 K 위반(stop).
- 프리셋 기본값은 바꾸지 않는다.

## 3. PAIR_DIVERGE 정의 (이 판에서 확정)

- adopt2는 3.4(조건부: "$L_1$ dP > 0이면 … 다르면 FLAG")와 6절(무조건: "짝 명령 sha가 다름")이 달랐다. REM에서는 두 정의 모두 0이라 결과에 닿지 않았다(REM 판정서 11절).
- **이 규칙의 정의(조건부)**: `PAIR_DIVERGE` = 결과 전에 정한 **짝 동일 전제**가 기록 특징으로 참인 짝에서 명령 해시가 다른 것.
  - 이 규칙의 짝 동일 전제: **cand의 LAS-b가 시작하지 않았다**(`las.start_t_s` None, Chrono는 `controller_meta.liftoff_approach_slow.start_s` None).
    - 근거: β가 커지면 S7_light 조건(min L < β $F_{min}$)이 참인 주기 집합은 커지기만 한다. LAS-b가 시작하기 전에는 두 팔의 입력열이 같다. 그래서 β 4.5에서 한 번도 시작하지 않았으면 β 3.5에서도 시작하지 않는다. 램프는 LAS-b 끝 뒤에만 작용한다.
  - 명령 해시: 하네스 `commands_sha256`. Chrono는 `controller_commands.npz`의 `t_s`·`issued_u_m_s` 배열 내용 해시(파일 sha는 기록).
  - **처리: stop(구현 결함 후보)**. A안 K-A7과 같은 사건이다. FLAG가 아니다.
- 전제가 거짓인 짝(cand LAS-b 시작)의 명령 차이는 **설계상 생긴다**. 이것은 `PAIR_CMD_DIFF` 건수로 **기록만** 한다.
- 조건부로 정한 이유
  1. 무조건 정의는 차이가 의도인 짝(이 규칙에서는 LAS-b가 작동한 모든 짝)에서 구조적으로 켜진다. 정보가 없고, 진짜 표류(전제가 참인데 다름)를 묻는다.
  2. adopt2 3.4의 문맥과 REM 경로 2의 계수가 조건부였다.
  3. 전제는 결과 전에 쓸 수 있고, 갈라지기 전 기록(LAS-b 시작 여부)으로 판단할 수 있다.
- adopt2와 REM 판정은 바꾸지 않는다(두 정의 모두 0).

## 4. 묶음

### 4.1 공통

- 하네스 출력은 새 폴더 `06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/`(main checkout, 로컬 전용, git exclude), 줄 파일 `p5k_<묶음>.jsonl`. 앞 폴더(`revA2/`, `k1/`)에 쓰지 않는다.
- Chrono 배치 이름 `V5-LAS-P5R4-K1`(`s9_batch` 등록), 결과 `07_results/S9/batch_V5-LAS-P5R4-K1_<시각>/`.
- 짝은 **전체 키**(`rev.key` = `d1.key|setting|e<eps>`, 격자 행은 줄 이름)로 맺는다.
- 키 목록은 저장 기준 파일에서 다시 계산하고 부록 A 목록 sha256과 대조한다. 다르면 실행하지 않는다. `--keys`·`--limit`은 본 실행에 쓰지 않는다.

### 4.2 하네스 묶음

| # | 묶음 | 키 | 팔 | 줄 | 기대(비트 예측, 4.4) |
|---|---|---|---|---|---|
| Z-0 | 비트 시험 b0 | A안 원판 7.1의 6작업(`revA_R0.jsonl` 키) | ref | 6 | `revA_R0.jsonl` 해시 6/6 |
| Z-A | (가)′ 재현 | R-0A 54(R-G 30 + R-H 24) + R-Q 48 | cand | 102 | `revA_R0A.jsonl`·`revA_RQ.jsonl` 해시 102/102 |
| Z-T | (나) | R-T 192키 | ref, cand | 384 | ref = 저장 L(`las_T1`·`las_T2` b0 줄) 192/192, cand = `revA_RT.jsonl` 192/192 |
| Z-S | (다) | R-S 30작업 | ref, cand | 60 | ref = `k1_YS.jsonl` P0 30/30, cand = `k1_YS.jsonl` P5r4 30/30 |
| Z-C | (라) **표본 밖** | S-C 456 전체 키(`s2d_SC.jsonl`) | ref, cand | 912 | ref = 저장(R4 평가 165키는 `k1_YP.jsonl` K1on 줄, 나머지 291키는 `s2d_SC.jsonl`) 456/456. cand는 예측 없음 |
| Z-X | C-4 예외 근거 | 예외를 주장하는 짝의 ref(DONE 기록 켬) | ref | ≤ 10 | ref 해시 = Z-T/Z-S ref 해시 |

- Z-A에는 ref 팔이 없다. (가)′는 A안 rev2처럼 cand 절대 하한(G-2′)만 본다. 짝 기준(K-A1~K-A4)은 R-0A의 저장 P5 짝이다(A안 rev2 R2-5).
- Z-C의 키는 S-C의 모든 계열(H-S-0 216, H-S-C 120, H-S-A 72, H-S-C-g 24, H-S-1 12, H-R-A-S1 4, H-R-A-J2 4, H-S-A-J2 4)과 VB·V0 × ε 0·0.002다. R-T와 겹치는 키는 0, R-S와 겹치는 키는 19다(1.1).
- 실행 순서: Z-0 → Z-A → Z-T·Z-S·Z-C → (필요하면) Z-X → 하네스 판정. Z-0 또는 Z-A에 비트 불일치가 한 줄이라도 있으면 다음 묶음을 돌지 않는다(8절 S-2).
- 스레드 1 고정(`fb_targeted.thread_problems`). 줄마다 작업자 마스크를 기록한다.

### 4.3 Chrono 묶음 (`V5-LAS-P5R4-K1`, 12행)

공통: 패드 B(`dwg_rear250`), F_s 4 kN, 오거 상단, 압력 normal, IMU ideal, seed 20261026, `--threads` = `run_S9.SCM_THREADS_FIXED`(4), start_env `OMP_WAIT_POLICY=PASSIVE`·`OUTRIGGER_HULL_HOOK=fast`, DLL sha `cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15`, 계획 풀 P(짝은 같은 풀 종류). `--expect-controller`는 VB `final_C4G2_P3_LAS_K1`, V0 `final_C4G2_LAS_K1`. 짝의 argv 차이는 `--las-candidate` 값 하나(+ `case`)다.

| # | id | 지형·조건 | 플랜트 | 폐루프 | 팔 | 짝 | 보는 것 |
|---|---|---|---|---|---|---|---|
| 1 | A1 | 혼합 지형 강체 + J1@FR(`las_chrono_rows` 꼴), 바닥 (2.3351, 1.5017)°, `record_only`, Kc1 | VB | 160 s | ref | A2 | 이륙 뒤 최소 힘(G-2′C) |
| 2 | A2 | 같음 | VB | 160 s | cand | A1 | |
| 3 | A3 | 같음, Kc3(`--crawler-kn-scale 3`) | VB | 160 s | ref | A4 | |
| 4 | A4 | 같음 | VB | 160 s | cand | A3 | |
| 5 | A5 | 같음, Kc1 | V0 | 160 s | ref | A6 | V0 위상 갈래(하네스 V0 칸이 낮았음) |
| 6 | A6 | 같음 | V0 | 160 s | cand | A5 | |
| 7 | B1 | G6 꼴 G1 바닥 + J1 패치@FL(`las_k1_chrono_rows` 꼴, 패치 세트만 J1), 평지 | VB | 200 s | ref | B2 | 경계 키 `D1\|H-S-A\|G1+J1@FL\|T\|flat\|K1\|VB\|e0`의 Chrono 대응(C-S, K1 막힘) |
| 8 | B2 | 같음 | VB | 200 s | cand | B1 | |
| 9 | C1 | P3b 균일 J2 평지(`las_k1_rem_chrono_rows` 꼴), ×1.0 | VB | 120 s | ref | C2 | K1이 R4c30을 계속 켜는가(R4_LOST, F2 한계 경로) |
| 10 | C2 | 같음 | VB | 120 s | cand | C1 | |
| 11 | C3 | 같음, ×1.1(`--mass-scale 1.1`) | VB | **180 s** | ref | C4 | |
| 12 | C4 | 같음 | VB | **180 s** | cand | C3 | |

- C3·C4를 180 s로 늘리는 이유: REM R8(같은 조건 ref)의 첫 READY가 117.6 s로 120 s 끝에 붙어 있다. cand가 조금만 늦어도 "READY 없음"(C-2형 (b))이 루프 길이 때문에 난다. 그래서 C3도 180 s로 돌리고, 비트 예측(4.4 BT-C)은 앞 120 s 구간으로 본다.
- 실행 순서: 하네스 판정 `통과` 뒤에만 시작한다(8절 S-6). 배치표는 compute-scheduler-expert(12절).

### 4.4 비트 예측 (판정 기준. 어긋나면 stop)

| # | 예측 | 근거 |
|---|---|---|
| BT-0 | Z-0 6/6 = `revA_R0.jsonl` | b0 경로, K1은 R4 평가 LOC에서만 작동하고 이 6작업은 토양 모드가 없다(Y-T 192/192와 같은 계열) |
| BT-A | Z-A 102/102 = `revA_R0A.jsonl`·`revA_RQ.jsonl`의 같은 줄 | 같은 계열(강체 + J1@FR), Y-T에서 K1on 192/192 같음 |
| BT-T | Z-T ref 192/192 = 저장 L, cand 192/192 = `revA_RT.jsonl`(= `k1_YT.jsonl`) | Y-T, R-P0 149/149, G-5b |
| BT-S | Z-S ref 30/30 = `k1_YS.jsonl` P0, cand 30/30 = `k1_YS.jsonl` P5r4 | G-3(새 프리셋에서 Y-Sa·Y-Sb 해시 같음) |
| BT-CR | Z-C ref 456/456 = 저장(165 `k1_YP.jsonl` K1on, 291 `s2d_SC.jsonl`) | Y-Pa·Y-Pb, G-3. R4 평가가 없는 줄에서 관문은 명령을 바꾸지 않는다 |
| BT-C | Chrono C1의 명령 배열(`t_s`·`issued_u_m_s` 내용 해시) = REM R7(파일 sha `ebf86d1d40af464e2e4e23d4ea79ad56721829e65d70cb4efb1d2cc072e4b559`의 내용). C3의 앞 120 s(t ≤ 128 s) 구간 = REM R8(`97aace614a534a6aa95f67857947dcd541f9ecca1e9974eb5105fc017bf7c8aa`의 내용) | REM R7·R8은 관문 켬 + LAS-b b0 + 같은 조건이다. 전환은 태그·기본값만 바꿨다. 같은 스레드 수·풀 |
| BT-X | Z-X ref 해시 = 같은 키 Z-T/Z-S ref 해시 | A안 원판 6절 |

- A1~A6, B1·B2, cand 행에는 비트 예측이 없다(새 조건).
- BT-C가 어긋나면 Chrono 판정을 멈추고 묻는다. 결과(짝 판정)는 정보용으로 적는다(전환이 설명되지 않는 변화를 냈다는 뜻이기 때문이다).

## 5. 줄·행마다 기록할 것 (실행 정체성)

### 5.1 하네스 줄

- `git_head`, `git_dirty`, `dirty_files`, `code_diff_sha256`(A안 원판 4.1. dirty는 시험 파일만, K1 rev1 R1-4)
- sha256: `c2.py`, `v5_options.py`, 실행 도구, 판정 도구, `las_revA_targeted.py`·`fb_targeted.py`·`las_targeted.py`·`k1_targeted.py`(import하면), 이 규칙 + 0절 표의 모든 규칙
- `controller_tag`: VB `final_C4G2_P3_LAS_K1`, V0 `final_C4G2_LAS_K1`(정확 일치. `v5_options.is_liftoff_slow_tag` 참도 함께 기록)
- `las_candidate`(`P0`/`P5r4`), `las.settings`(실행된 제어기의 asdict), `las.ramp`, `las.start_t_s`·`end_t_s`·`end_reason`
- `k1`: `enabled`(실행된 제어기 meta), `decisions`(adopt2 키 전부), `would_block_any`, `r4_applied`
- `rev.attempt`(1/2), `rev.resumed`, 작업자 마스크, 스레드 변수(`OMP_NUM_THREADS` 등 1)
- `done_trace`·`done_clock`(원판의 원판 4.2, cand와 Z-X ref)

### 5.2 Chrono 행 (result.json·batch.json)

- `code_state.git_at_start.head`, dirty 목록, 코드 sha(작업 트리 CRLF, HEAD blob LF): `run_S9.py`, `s9_batch.py`, `las_p5r4_k1_chrono_rows.py`, `c2.py`, `zero_calibration.py`, `hull_hook.py`, `late_loc_rule.py`, `v5_options.py`, `rigid_base.py`
- `c2_setup.las_candidate`(`requested`, 적용 뒤 `settings` asdict), `c2_setup.k1_order_gate`(= `preset`), `k1_order_gate_effective` 참, `c2_setup.k1_forced_block` `off`, 제어기 클래스 `C2Controller`
- `controller_meta.liftoff_approach_slow`(`settings`, `start_s`, `end_s`, `end_reason`, `active_periods`, `ramp`), `controller_meta.slope_clearance_margin`(`settings`, `order_gate.enabled`, `order_gate.decisions`), `controller_meta.loc_revoke`, `controller_meta.soil.mode_starts`
- `expect_controller.ok`, `args.threads` = `num_threads_chrono` = 4, batch `omp_wait_policy` PASSIVE, `hull_hook.mode` = `requested` = `fast`, `fallback_reason` None, batch `hull_hook_effective`·`mixed_hull_mode` 거짓, `placement`(풀, `affinity_ok`, `power_throttling_off_ok`)
- `rc`, `restored_from` None, `rerun_of`(재실행 행만)

## 6. 판정 기준

### 6.1 하네스 (가)′ — Z-A (cand 102줄)

| # | 기준 | 정의 |
|---|---|---|
| G-1 / G-1H / G-1Q | 하한 | `F_RL_kN`·`F_judged_min_kN` ≥ 10.400 kN(30 / 24 / 48줄) |
| G-2′ | 하한 여유 | 102줄 모두 `F_RL_kN`·`F_judged_min_kN` ≥ **11.414589** kN(A안 rev2 R2-1) |
| G-3 | 제외 검사 | A안 원판 G-3(묶음마다 모든 줄, 오류 0, LEVEL 예산 0, `gate_consistent` 참) |
| G-4 | 구현 예측 | K-A5·K-A6·K-A8, K-A1~K-A4(저장 P5 짝, A안 rev2 R2-5) |

- BT-A가 참이면 값은 A안 rev2 판정과 같다. 그래서 (가)′는 **재현 확인**이다(1.1).
- 기록: 원 G-2·G-2H, Q-1~Q-5(rev3 RQ3-1 분류), M-1~M-3.

### 6.2 하네스 (나) Z-T, (다) Z-S, (라) Z-C — 짝(cand − ref)

| # | 기준 | Z-T | Z-S | Z-C | 정의 |
|---|---|---|---|---|---|
| C-2형 | 나빠짐 0 | ○ | ○ | ○ | K1 rev1 R1-2(= `pair_violations` 정의: verdict None, `d1.items` 합집합, READY → None, 새 FAULT·WARN·`fail_items`). verdict 사례는 (b)·(c)만 |
| P3 | 끝 크롤러 | ○ | ○ | ○ | K1 rev1 R1-1(기준 참 → 후보 거짓/없음 = 위반, 기준 거짓은 `P3_baseline_false`로 적음) |
| C-1 | 계열 하중 | ○ | — | — | T-1 8키 cand `d1.F_judged_min_N` ≥ 10,414.589 N |
| C-F | 여유선 | ○ | ○ | ○ | ref ≥ 10,414.589 N인 짝에서 cand ≥ 10,414.589 N |
| C-S | 행정 | ○ | ○ | ○ | 모든 D-1 짝에서 $s_{max}$ 증가 ≤ 0.001 m |
| CK-1 | R4c30 유지 | ○ | ○ | ○ | ref의 $L_1$이 `applied` 참이면 cand에도 `applied` 참인 R4 평가 decision이 있다. 없으면 위반 `R4_LOST` |
| A-3 | 강체 균일 | ○ | — | — | H-R-0 48키 cand 해시 = ref 해시 |
| R-1 / R-2 | READY | ○ | 기록 | ○ | 해시가 바뀐 짝 모집단 $\mathcal{P}$(원판의 원판 5.2, C-4 예외 6절 + A안 6 램프 끝 조건)의 $\Delta t$ 중앙 ≤ +1.0 s, 최대 ≤ +5.0 s |

- CK-1은 이 규칙에서 새로 넣었다. K1의 알려진 한계(REM F2: 첫 R4 LOC가 막히면 R4c30이 끝까지 없음)가 P5r4의 LOC·토양 모드 순서 변화로 판정 행에서 생기는지를 직접 본다. 반대(cand에만 적용, `R4_GAINED`)는 FLAG로 적고 C-S가 판정한다.
- $\mathcal{P}$ 빈 집합: 해시가 바뀐 짝이 0이면 "해시 동일로 성립"이고 건수를 적는다. 바뀐 짝이 있는데 $\mathcal{P}$가 비면 `undecidable`(원판의 원판 5.2).
- 구현 예측 K-A7(전제 참 → 해시 같음)은 3절 `PAIR_DIVERGE`로 처리한다(stop). K-A8은 모든 cand 줄 `las.settings`가 P5r4, 모든 ref 줄이 b0임을 본다.
- Z-C는 판정 짝 456개다. 짝 단위로 센다.

### 6.3 Chrono — 짝(cand − ref)

| # | 기준 | 대상 | 정의 |
|---|---|---|---|
| CC-2 | 나빠짐 0 | 6짝 | (a) 판정 항목 집합 $I$의 각 항목: ref 참 → cand 거짓(또는 없음) = 위반. (b) ref 끝 단계 `ready` → cand 비ready = 위반, ref 첫 READY 있음 → cand 없음 = 위반. (c) cand `FAULT*`·`WARN*` 사건 이름 ⊆ ref 이름 |
| CC-F | 여유선 | 6짝 | ref $F^{C}_{after}$ ≥ 10,414.589 N이면 cand ≥ 10,414.589 N |
| G-2′C | 하한 여유 | A2·A4·A6 | cand $F^{C}_{after}$ ≥ 11,414.589 N **그리고** $F^{C}_{tr}$ ≥ 11,414.589 N |
| CC-S | 행정 | 6짝 | $s_{max}$ 증가 ≤ 0.001 m |
| CK-1C | R4c30 유지 | B·C 짝 | ref $L_1$ `applied` 참 → cand에 `applied` 참 R4 평가 decision 있음. 없으면 `R4_LOST` 위반 |
| CC-R | READY | 해시가 바뀐 짝 | $\Delta t$ = cand − ref `P3-6_ready.t_ready_after_loop_start_s`. 최대 ≤ +5.0 s, 중앙 ≤ +1.0 s(둘 다 값이 있는 짝). 바뀐 짝이 있는데 모집단이 비면 `undecidable` |

- 판정 항목 집합 $I$ = `p3b.checks`의 `P3-1_recontact_pass`, `P3-1_crawler_zero_after_ready`, `P3-2_within`, `P3-3_within`, `P3-4_within_0p2`, `P3-5_within`, `P3-6_within`, `P3-7_within`, `P3-8_within`.
  - 예외(명세 419.8): `P3-2_within` 참 → 거짓이어도 cand `P3-2_late_loc_reapproach` 또는 `P3-2_late_loc_revoked`가 참이면 위반이 아니라 FLAG `LATE_LOC_P32`다.
  - `P3-4_window_short`는 FLAG(명세 433.6)이고 $I$에 넣지 않는다.
  - $I$의 키가 한 행이라도 없으면 그 짝은 `undecidable`(구현자가 키 이름을 실행 전에 확인한다, 11절).
- **관측 요건(빈 집합 통과 금지)**: A 짝 3개 가운데 cand LAS-b가 시작하고 램프가 작용한(`ramp.periods_applied` ≥ 1) 짝이 **1개 이상** 있어야 한다. 없으면 Chrono `undecidable`(사유 `NO_P5R4_OBSERVATION`). B·C 짝에서 cand LAS-b가 시작하지 않으면 그 짝은 판정은 하되(동일 → 위반 없음) 판정서에 "P5r4 미작동, P5r4 근거 아님"을 적는다.
- `R4_GAINED`(cand에만 R4c30 적용)는 FLAG이고 CC-S가 판정한다.
- C3·C4의 READY·사건·항목은 180 s 전체로 본다.

### 6.4 기록 (판정 아님)

- 짝마다: LAS-b 시작·끝·끝 사유·작동 주기·$\lambda_0$·램프 끝 사유, LOC 시각, 토양 모드 시작, $L_1$ 튜플, `PAIR_CMD_DIFF`, READY $\Delta t$, 최소 힘 다리·시각, 끝 크롤러 틈, 최대 행정.
- FLAG: `R4_GAINED`, `LATE_LOC_P32`, `THIN_MARGIN`(cand $L_1$ dP ≤ 12), 10.400~10.4146 kN 사이 줄, Z-C의 R-S 겹침 19키 결과(표본 안)와 437키 결과(표본 밖)를 나눈 표.
- Chrono A 짝: ref 대비 cand 최소 힘 차, 하네스 같은 계열 값(`las_chrono_rows` 머리말 b0 11.377 kN)과의 차.

## 7. 사전 예측 (판정 기준 아님. 4.4 비트 예측만 판정 기준)

| # | 항목 | 예측 | 확신 |
|---|---|---|---|
| P-1 | Z-A·Z-T·Z-S 판정 | A안 rev2·K1 Y-S와 같은 값으로 모두 통과 | 높음(BT가 참이면 자명) |
| P-2 | Z-C cand LAS-b 시작 줄 | 456 가운데 40~140줄(9~31 %). 근거: R-S 30작업 중 P5r4 시작 5줄 | 중간 |
| P-3 | Z-C `PAIR_CMD_DIFF` | P-2의 시작 줄과 같은 수(시작 → 명령 다름) | 중간 |
| P-4 | Z-C C-S | 위반 0. 위반이 난다면 기구는 `R4_GAINED`(cand만 토양 모드 + dP > 0) | 중간(60 %) |
| P-5 | Z-C CK-1 | `R4_LOST` 0(균일 연약 지면 dP가 크다: S-C 진짜 연약 지면 dP ≥ +31주기) | 중간~높음 |
| P-6 | Z-C C-2형·P3·C-F | 위반 0 | 중간 |
| P-7 | Z-C R-1 / R-2 | 중앙 ≤ +0.5 s, 최대 ≤ +3 s | 중간 |
| P-8 | Chrono A2·A4·A6 | cand LAS-b 시작·램프 작용. $F^{C}_{after}$ 12.0~15.0 kN(G-2′C 통과). A6(V0)이 셋 중 가장 낮다 | 중간(하네스↔Chrono 이륙 과도 일치는 확인된 적 없음) |
| P-9 | Chrono A ref | $F^{C}_{after}$ 10.5~12.0 kN(하네스 b0 11.377 kN 근처) | 낮음~중간 |
| P-10 | Chrono B 짝 | ref·cand 모두 R4c30 없음(토양 모드 없음 또는 K1 막힘), $\lvert\Delta s_{max}\rvert$ ≤ 1 mm, C-S 통과 | 중간(60 %) |
| P-11 | Chrono C 짝 | ref·cand 모두 `POS`·$L_1$ 적용(REM dP +99·+198 대비 LAS-b 지연 ≤ 10주기), CK-1C 통과 | 높음 |
| P-12 | Chrono C 짝 C-S | $\lvert\Delta s_{max}\rvert$ ≤ 1 mm. 연약 지면 소성 침하가 들어 올림 속도에 따라 몇 mm 달라질 수 있어 **확신 낮음(50 %)** | 낮음 |
| P-13 | BT-C | C1 = R7, C3 앞 120 s = R8 | 높음 |
| P-14 | 전체 등급 | 하네스 `통과`, Chrono `통과`(가장 가능성 큰 미달 사유: P-12 C-S, 그다음 P-10) | 중간 |

## 8. 등급·순서·멈춤

### 8.1 묶음별 상태 (앞의 것이 이긴다)

| 순서 | 상태 | 조건 |
|---|---|---|
| 1 | `stop` | 비트 예측(4.4) 불일치, 구현 예측(K-A5·K-A6·K-A8) 불일치, `PAIR_DIVERGE`, 정체성 K 위반(9절), 두 번 적용 흔적(2절) |
| 2 | `undecidable` | 판정 필드 누락(원판의 원판 5.0, A안 R1-3), $\mathcal{P}$ 빈 집합인데 바뀐 짝 있음, Chrono 관측 요건 미달, 결측(10절) |
| 3 | `미달` | 6.1~6.3 기준 하나라도 위반. **나오는 즉시 확정**(K1 원판 SK-5). 판정을 되돌리거나 기준을 고치지 않는다 |
| 4 | `통과` | 모든 기준 참 |
| — | `incomplete` / `not_run` | 묶음 줄 없음 / 앞 단계 미통과로 안 돔 |

- 최종: 하네스(Z 전체)와 Chrono가 모두 `통과`면 **P5r4 채택 권고**. 하나라도 `미달`이면 P5r4 `미달`(P0 유지 권고, 채택 여부는 사용자). `stop`·`undecidable`은 묻는다.

### 8.2 멈춤

| # | 조건 | 처리 |
|---|---|---|
| S-1 | 이 규칙·0절 표 규칙의 `.sha256`이 없거나 LF sha256이 다름 | 실행하지 않는다 |
| S-2 | Z-0·Z-A 비트 불일치 | 다음 묶음을 돌지 않는다. python-expert가 원인을 찾은 뒤 Z-0부터 다시(새 판 필요 여부는 감사가 정함) |
| S-3 | Z-T·Z-S·Z-C 비트 불일치(ref 또는 BT 대상 cand) | 진행 중 묶음은 끝까지 돌리고(정보용) `stop`, 묻는다 |
| S-4 | 기준 위반 | 즉시 `미달` 확정. 진행 중 묶음은 끝까지 돌리고 나머지 줄은 정보용으로 적는다. 다음 묶음(Chrono 포함)은 `not_run` |
| S-5 | 한 묶음에서 C-2형 위반 짝 누적 ≥ 5 | 그 묶음 남은 실행을 멈춘다(A안 H-8) |
| S-6 | 하네스 판정이 `통과`가 아님 | Chrono를 시작하지 않는다(사용자 결정이 있으면 예외, 판정서에 시각과 함께 적음) |
| S-7 | BT-C 불일치 | Chrono 판정 멈춤, 짝 결과는 정보용, 묻는다 |
| S-8 | C-4 예외 과다(한 묶음 > 5 또는 $\Delta t$ > +15 s) | 자동 권고하지 않고 묻는다 |

- 미달이어도 값을 바꿔 다시 돌리지 않는다. β, $N_r$, 문턱, 키, 행을 결과를 본 뒤 바꾸려면 새 판(결과 본 뒤 판으로 공개)을 봉인한다.

## 9. 정체성·일관성 검사 (하나라도 거짓이면 stop)

| # | 검사 |
|---|---|
| K-0 | 이 규칙 sha256 = `.sha256` 기록. 두 판정 도구 sha256 = 실행 전 감사 기록 = prelaunch = postrun = judge. 실행 전 감사 리포트 파일(원문 그대로 저장) sha256 = prelaunch 기록 |
| K-1 | 하네스: 한 묶음·한 팔의 모든 줄이 한 `git_head`, dirty 허용 밖 0, `code_diff_sha256` 빈 해시. Chrono: 12행 `git_at_start.head` = prelaunch HEAD, `git diff --quiet <prelaunch> <postrun> -- 03_src 02_params 04_scripts` 참, `git status --porcelain --untracked-files=no` 허용 목록 밖 0줄 |
| K-2 | 코드 sha(5.1·5.2 목록) = 기록. `c2.py`·`v5_options.py` blob이 prelaunch HEAD blob과 같다 |
| K-3 | 태그: 모든 줄·행 `controller_tag`(Chrono `expect_controller`) = 설정별 새 태그 정확 일치. 옛 태그(`_LAS`로 끝나는 것 포함) 0 |
| K-4 | 관문: 모든 줄·행 실행된 제어기의 `flat_soil_margin_order_gate` 참, `order_gate.enabled` 참, `decisions` 키 있음. 하네스 줄에 K1 토큰 흔적 없음, Chrono `c2_setup.k1_order_gate` = `preset` |
| K-5 | LAS-b 설정: ref 줄·행 `settings`가 b0(β 3.5, $n_{min}$ 0, $N_r$ 0, 나머지 436.3 값), cand 줄·행이 P5r4(β 4.5, $N_r$ 4, 나머지 b0). `las_candidate` 필드와 맞음(K-A8) |
| K-6 | Chrono 실행 조건: threads 4 = `num_threads_chrono`, PASSIVE, hull `fast`·DLL sha·`fallback_reason` None·`mixed_hull_mode` 거짓, 풀 = 계획, 짝 같은 풀 종류, `affinity_ok`·`power_throttling_off_ok` 참 |
| K-7 | Chrono 인자: 짝 argv 차이 = `--las-candidate` 값 하나(+ `case`). 고정값(seed, grade, F_s, pad, soil, level, mass_scale, duration, rigid-base, crawler-kn-scale, v5 인자) 일치. `--k1-order-gate`·`--k1-forced-block`·`--las-off` 없음 |
| K-8 | decision 기록 일관성: adopt2 K-8 (a)~(e)를 모든 행·줄에 적용 |
| K-9 | 목록: 묶음 키 목록 sha256 = 부록 A, 중복 줄 0, 목록 밖 줄 0, 짝 없는 키 0 |
| K-10 | 두 경로 재집계 완전 일치(10.2). 판정서가 도구 밖에서 확정한다 |

## 10. 결측·두 경로

### 10.1 결측·오류

| 경우 | 처리 |
|---|---|
| 하네스 오류 줄 | 같은 정체성으로 그 키만 1회 재실행(`rev.attempt` 2, 공개). 남으면 `incomplete` |
| Chrono 행 실패(rc ≠ 0, result.json 없음 등, 인프라 원인) | 같은 argv·같은 HEAD로 **1회만** 재실행(사용자에게 알린 뒤, `rerun_of`). 두 번째도 실패하면 그 짝 `undecidable` |
| Chrono 제어 FAULT·안전 정지로 끝남 | 결측이 아니다. CC-2로 판정한다 |
| 결측 행을 하네스·옛 Chrono 행으로 메움 | 금지 |

### 10.2 두 경로 재집계

- 경로 1: python-expert 판정 도구 두 개(11절). 잠정 등급, `k10: null`.
- 경로 2: control-expert 독립 재집계 스크립트(하네스 `p5k_recount.py`, Chrono `p5k_chrono_recount.py`, scratchpad). 판정 도구·프로젝트 모듈을 열지도 import하지도 않는다. jsonl·result.json·batch.json·이 규칙만 읽는다.
  - **결과 전 고정**: 구현이 끝난 뒤, 도구 단위 시험의 합성 줄(fixture)로만 맞춰 보고 sha256을 메인 세션에 넘긴다. 이 sha는 prelaunch에 기록한다. **판정 줄을 한 줄이라도 만든 뒤에는 고치지 않는다.** 첫 불일치 뒤 맞춘 항목은 독립이 아님을 공개한다.
  - 출처를 경로 1과 다르게 둔다: LOC는 decision 먼저·사건 대조, $t_S$는 `mode_starts` → 사건, 사건 이름은 `split(":",1)[0]` 정확 일치, READY는 `values.times.t_first_ready_s`(하네스)·`P3-6_ready`(Chrono).
- K-10 비교 대상: 비트 예측 결과, 짝별 위반 목록·`items_only_*`, 기준별 참·거짓·개수·중앙·최대·최소, `PAIR_DIVERGE`·`PAIR_CMD_DIFF`, CK-1 분류, FLAG 건수, 등급. 수치 허용 1e-9(kN·s·m). 등급·목록은 완전 일치.

## 11. 구현 목록 (위임)

### 11.1 전환 후 감사 W-3 태그 소비자 — 이 규칙에서의 처리

| 소비자 | 이 규칙에서 쓰나 | 처리 |
|---|---|---|
| `s9_batch.V5_P3_LAS_K1_CONTROLLER`·`V5_LAS_K1_CONTROLLER`(정의만 있음) | 쓴다 | 새 행 모듈이 이 상수를 기대값으로 쓴다(연결) |
| `las_chrono_rows.py:75,144`(옛 `_LAS` 태그) | 지형 도우미만(`base_case`, `level_argv`) | 파일을 고치지 않는다. 새 모듈이 도우미를 import하고 태그는 직접 정한다. 옛 `V5-LAS-CHRONO` 4행은 436.8 재개 때 처리 |
| `las_k1_chrono_rows.py:50` | 지형 도우미만(G6 꼴, 패치 세트 인자) | 고치지 않는다(S-Ch 재현 정의 유지). 패치 세트를 인자로 받는 도우미가 없으면 새 모듈에 같은 꼴로 쓴다 |
| `las_k1_rem_chrono_rows.py:43` | 지형 도우미만(`base_case`, `level_argv`) | 고치지 않는다(REM 재현 정의 유지) |
| `d1_chrono_rows.py:101,160,164`, `v5_stage3_las_rows.py:108` | 쓰지 않는다 | 이 규칙 밖(436.8·D-1 Chrono 재개 규칙에서 "새 태그 재실행"으로 정함) |
| `u3_judge.py:70,72`, `u3_reuse.py:122,235` | 쓰지 않는다 | 이 규칙 밖(U-3·U-6는 436.8). 쓰려면 그 규칙 개정판 |
| `fb_judge.py`, `las_rev_judge.py`, `las_revA_judge.py`, `k1_judge.py`, `las_k1_*_judge.py`, `p3_hash_check.py`, `p3_chrono_check.py` | **판정에 쓰지 않는다** | 봉인·옛 결과 전용, 고치지 않는다. 필요한 함수(`pair_violations`, 정체성 검사)는 **복사**하고 원본 파일 sha를 새 도구 docstring·출력에 적는다 |
| `v5_options.EXTEND_START_TAGS`·`j_p3_inputs.is_p3_expected` | 하네스 d1 항목 계산이 쓴다 | 바꾸지 않는다. 실행 전 시험: VB 새 태그 줄에서 `p3_expected` 참 |
| W-1(LAS 끔 + 관문 켬 조합 태그) | 조합을 쓰지 않는다 | 이 규칙의 전제는 아니다. run_S9는 `--las-off`와 `--las-candidate`를 함께 주면 종료 2 |
| `las_targeted._turn_preset_las_off`(무결성 Medium) | 쓰지 않는다 | — |

### 11.2 cad-expert (Chrono)

1. `run_S9.py level --las-candidate {P0,P5r4}`
   - 없으면 기존 동작 그대로(P0와 비트 같음). `P0`은 덮어쓰지 않고 기록만 한다.
   - 순서: 프리셋 → (기존 단계) → `--expect-controller` 점검(프리셋이 새 태그 기대값인지, `_LAS_EXPECTATIONS` β 3.5 포함) → 후보 적용(`replace(..., light_leg_fraction_of_F_min=4.5, end_ramp_periods=4)`) → **후보 기대값 점검**(만든 제어기의 `liftoff_approach_slow` 전체가 2절 표와 같은지; 다르면 종료 2).
     - 이유: `_LAS_EXPECTATIONS`는 β 3.5를 고정하므로 후보 적용 뒤에 같은 점검을 하면 항상 거부된다. 프리셋 점검과 후보 점검을 나눈다.
   - `c2_setup.las_candidate`(`requested`, `settings`)를 기록한다. 태그는 바꾸지 않는다.
   - `--las-off`와 함께 주면 종료 2. `--k1-forced-block first`와 함께 주면 종료 2.
2. `04_scripts/02_chrono/las_p5r4_k1_chrono_rows.py` + `s9_batch` 등록(`V5-LAS-P5R4-K1`): 4.3절 12행, 행 키 `case`, `p5k_id`, `las_candidate`, `pair_case`, `v5_setting`, `role` `judge`, `start_env`, `planned_pool`, `est_pool_s`. `argv_check`(짝 argv 차이 하나, 고정값 표, 새 태그 기대 통과, 후보 점검 통과, `--k1-order-gate` 없음).
3. 단위 시험 `05_tests/unit/test_las_p5r4_k1_chrono_rows.py`(시뮬레이션 없음): 12행, 짝 차이, 태그, C3·C4 180 s, `--las-candidate P0`와 무인자의 config 비트 동일.

### 11.3 python-expert (하네스·판정 도구)

1. `04_scripts/04_hydraulic/coupled/las_p5r4k1_targeted.py`: 묶음 Z-0·Z-A·Z-T·Z-S·Z-C·Z-X, 팔 ref/cand(2절), 프리셋 점검(b0 + 관문 참 + $N_r$ 0, `fb_targeted.check_preset_las`에 관문 점검을 더한 새 함수), K1 토큰 없음, 5.1 기록, 목록 sha 대조(부록 A), 앞 묶음 정체성 검사(같은 폴더 안), `rev.attempt`·`resumed`, 출력 폴더 `v5/las/p5r4k1/`. 봉인 도구(`las_revA_targeted.py` 등)는 고치지 않는다.
2. `06_analysis/02_control/verif_matrix/scripts/las_p5r4k1_judge.py`(하네스, 표준 라이브러리만): 4.4 비트 예측, 6.1·6.2, 3절, 8절 상태, 기록 6.4, 전체 자리 출력, 잠정 등급·`k10: null`, 종료 0 통과·1 미달/undecidable·2 stop·3 도구 오류.
3. `06_analysis/02_control/verif_matrix/scripts/las_p5r4k1_chrono_judge.py`: `prelaunch`·`postrun`·`judge`(REM 도구 꼴, 정체성 코드는 복사), BT-C(npz 배열 내용 해시, C3는 t ≤ 128 s 구간), 6.3, 9절 K-0~K-9.
4. 단위 시험: 상태 순서, `PAIR_DIVERGE`(전제 참·해시 다름 → stop, 전제 거짓·해시 다름 → 기록만), CK-1(`R4_LOST`·`R4_GAINED`), $I$ 키 누락 → undecidable, `LATE_LOC_P32` 예외, 관측 요건, $\mathcal{P}$ 빈 집합 두 경우, 사건 이름 정확 일치(`_SKIPPED` 함정), 하네스 팔의 관문 실효 값을 실행 제어기 meta에서 읽음.
5. 전환 후 감사 R-5 권고(`pre_*` 러너 관문 False subprocess 시험)는 이 규칙의 전제는 아니지만, 같은 작업 브랜치에서 하면 sha 기록에 들어간다.

### 11.4 control-expert

- 경로 2 두 스크립트를 합성 줄로 맞춘 뒤 sha를 넘긴다(10.2).
- 봉인 전: 15절 답 반영, 부록 A 목록 sha 재계산 확인.

### 11.5 메인 세션

- `.gitattributes` 두 줄(머리 인용 블록), 봉인(`.sha256`), 실행 전 감사(verif-protocol-auditor `[시점] 실행 전`, 리포트 원문 저장 → K-0), compute-scheduler-expert 배치표·예약, long-running-task-monitor 점검, prelaunch~postrun 동안 main checkout 커밋·병합 금지.

## 12. 비용과 순서

### 12.1 하네스 (가정: 저장 `wall_s` 평균을 단가로 씀)

| 묶음 | 줄 | 단가 [s/줄] | CPU [s] |
|---|---|---|---|
| Z-0 | 6 | 110(R-0 단가 가정) | 660 |
| Z-A | 102 | 86(R-0A 4,654/54, R-Q 4,087/48) | 8,700 |
| Z-T | 384 | 92(R-T 17,695/192) | 35,300 |
| Z-S | 60 | 108(R-S 3,249/30) | 6,500 |
| Z-C | 912 | 124(S-C 56,759/456) | 113,500 |
| Z-X | ≤ 10 | 110 | ≤ 1,100 |
| 합 | ≤ 1,474 | — | 약 165,800(약 46 CPU-h) |

- 벽시계: 기계 전체(P 8 + E 12, 단일 스레드 작업) 동시 배율을 앞 묶음 실측처럼 약 11배로 보면 **약 4.2 h**, E만 쓰면 약 6~7 h(가정). Z-C가 68 %다.
- 줄이는 안(15절 Q-1): Z-C를 ε 0만(456줄) → 합 약 109,000 s(약 30 CPU-h, 기계 전체 약 2.8 h).

### 12.2 Chrono (가정)

| 행 | 단가 근거 | 행당 [s] |
|---|---|---|
| A1~A6(혼합 지형 160 s) | `las_chrono_rows.MIXED_US_PER_STEP` P 2,800 µs/step × 168 s / 1e-4 × VB 1.2 = 5,600(**미측정 가정**, 혼합 지형 폐루프 실측 없음) | 5,600 |
| B1·B2(G6 J1@FL 200 s) | S-Ch(G6 J2@FL 200 s, P 2행 동시) 5,628~5,658 s × 4행 동시 1.2 | 6,800 |
| C1·C2(J2 ×1.0 120 s) | REM R1·R7 6,230~6,560 s(P 4행 동시) | 6,500 |
| C3·C4(J2 ×1.1 180 s) | REM R4·R8 6,083~6,668 s × 180/120 | 9,700 |

- 12행 직렬 합 약 79,600 s(22 h). **P만 4행씩**: 3묶음(가장 긴 C3·C4·B를 먼저) 약 6 h. **P 4 + E 3**(E 약 1.5배, 짝은 같은 풀 종류): 약 4.5 h. 최소 8행안(15절 Q-2, A3~A6 뺌): P만 약 4.5 h.
- 15분 넘게 걸리므로 compute-scheduler-expert 배치표·`reserve.py` 예약, long-running-task-monitor 점검이 필요하다.

### 12.3 D8x와의 순서 (제안)

D8x는 E코어 하네스 R-a·R-c(약 3 h) → 관문 G1 → Chrono 19행(P, 약 1.5~2 h)이 이미 사용자 결정으로 정해져 있다. P코어를 다투는 것은 두 Chrono 묶음이다.

1. 지금(계산 없음): 이 규칙 봉인, 구현(11절), 경로 2 고정, 실행 전 감사. D8x는 그대로 진행.
2. D8x E 하네스(약 3 h) 동안: P에서 이 규칙의 Z-0·Z-A(108줄, 약 15분)를 먼저 돌려 비트 시험을 끝낸다. 이어서 Z-T·Z-S(444줄)를 P에서.
3. D8x Chrono 19행이 P를 쓰는 동안(약 2 h): Z-C를 E에서(D8x E 하네스가 끝난 뒤).
4. D8x Chrono가 끝나고 하네스 판정이 `통과`면: 이 규칙의 Chrono 12행을 P(+E)에서 약 4.5~6 h.
5. 모든 것이 이어지면 시작부터 약 10~12 h(가정). 정확한 묶음·마스크는 compute-scheduler-expert가 정한다.

## 13. 판정서와 공개 체크리스트

- 판정서: `06_analysis/02_control/verif_matrix/las_p5r4_k1_judgement.md`.
- 적을 것: K1 원판 8절 체크리스트 1~11 전부, 이 규칙 1절 공개 원문, 비트 예측 결과(4.4), 묶음별 상태, 짝별 위반, $\mathcal{P}$ 크기·예외 짝, `PAIR_DIVERGE`·`PAIR_CMD_DIFF`, CK-1 분류, Z-C 표본 안(19키)/밖(437키) 분리 표, Chrono 관측 요건, 사전 예측 대조(7절), 실행 전 감사 원문 경로·sha, 두 경로 sha와 K-10 대조, REM F2 알려진 한계가 판정 행에서 나타났는지(`R4_LOST` 0이면 "관측 안 됨"을 그대로 적음).

## 14. 한계

- 하네스 Z-A·Z-T·Z-S는 이미 본 키의 재실행이다. 하네스 표본 밖 근거는 Z-C 437키뿐이다.
- Chrono는 결정론 1위상 표본이다. 하네스에서 이륙 첫 골이 위상에 따라 두 무리로 갈렸다(A안 rev2 R2-0). Chrono 3짝이 그 분포를 덮지 않는다.
- 잡음 등급 L1~L3, U-3·U-6, 경사 연약 지면, 오거 중·하단 ×1.1, 운용 중량 +20 %, S1 패치, t180은 보지 않는다(436.8 재개에서 본다).
- 혼합 지형 Chrono 비용은 미측정 가정이다.
- K1의 알려진 한계(REM F2)는 판정 행 C1~C4에서 `R4_LOST`가 0이면 여전히 판정 행에서 관측되지 않은 경로로 남는다.

## 15. 확인 필요 (봉인 전에 사용자 결정, 봉인 때 지움)

| # | 질문 | 선택지 | 추천 |
|---|---|---|---|
| Q-1 | 하네스 표본 밖 묶음 Z-C(S-C 456 전체 키 × 두 팔)를 넣는가 | (A) 912줄 전부 / (B) ε 0만 456줄 / (C) 넣지 않음(하네스는 재현만) | **A**. ε 0.002는 TOUCH 위상을 옮기고 K1은 같은 주기 순서에 민감해 표본 가치가 크다. C이면 하네스 표본 밖 근거가 0이다 |
| Q-2 | Chrono 행 범위 | (A) 12행 / (B) 8행(A3~A6 뺌: Kc3·V0 혼합 지형 없음) | **A**. 하네스에서 V0 칸 최소가 가장 낮았다(V0 1 칸 $M_c$ 13.41 kN). B는 P만 약 4.5 h로 1.5 h 줄어든다 |
| Q-3 | Chrono C-S 문턱 | (A) 1 mm(LAS-b 원판 C5·K1 결정 3 그대로) / (B) B 짝만 1 mm, A·C 짝은 기록 + 끝 크롤러 틈 P3-5·행정 가드(642.8 mm) 판정 | **A**(이전 사용자 결정과 일관). 다만 P-12 확신이 낮아 C 짝에서 수 mm 차로 미달할 수 있음을 미리 알린다 |
| Q-4 | Chrono 하한 G-2′C | (A) 절대 11.414589 kN(A안 rev2 R2-1 그대로) / (B) 상대: cand ≥ ref − 0.3 kN | **A**. B는 ref가 낮으면 같이 낮아도 통과한다 |
| Q-5 | Chrono 시작 조건 | (A) 하네스 `통과` 뒤 / (B) 하네스와 병행(하네스 미달이면 Chrono는 정보용) | **A**. Chrono 4.5~6 h를 아낀다 |
| Q-6 | D8x와의 순서 | (A) 12.3 제안(D8x Chrono 먼저) / (B) 이 규칙 Chrono 먼저 | **A**. D8x는 이미 자동 시작 결정이 있다 |
| Q-7 | C3·C4 폐루프 | (A) 180 s(BT-C는 앞 120 s) / (B) 120 s(REM과 완전히 같음) | **A**. REM R8 READY 117.6 s라 B는 루프 끝 때문에 거짓 미달이 날 수 있다 |
| Q-8 | PAIR_DIVERGE 정의 | (A) 조건부(3절, stop) / (B) 무조건(명령이 다르면 FLAG) | **A** |

## 부록 A. 키 목록과 기준 파일 (봉인 때 다시 계산해 대조)

- 목록 sha256 규약: K1 원판 부록 규약과 같다(전체 키 `rev.key`를 파이썬 기본 문자열 정렬, 각 줄 끝 LF, UTF-8 바이트의 sha256).
- 아래 값은 초안 작성 때 control-expert scratchpad `p5r4k1\key_lists.py`로 계산했다(main checkout 저장 파일, 2026-11-10).

| 묶음 | 기준 파일(main checkout `06_analysis/03_hydraulic/coupled/v5/`) | 파일 sha256 | 키 | 목록 sha256 |
|---|---|---|---|---|
| Z-0 | `las/revA2/revA_R0.jsonl`(6줄) | `04cadd3cdd63372518ee8fcf3620bfef43695f08583a99b7458a0c53b7f777f3` | 6 | `4d1591ba30b686bb6484072c1e63df51130791c2d0cee7106d9ae7d1bc4b6c9e` |
| Z-A(R-0A) | `las/revA2/revA_R0A.jsonl`(54줄) | `28df99076cc309718e9dcfc270fed5d390a111f5ace8ce77ddbc3a3c8b0f14f8` | 2키 × 격자 54점 | 키 `14f89f1f9209114d7e5a2c84f5b45a7d6c650e44ac3de41dd4c93c8733451577`. 격자 점은 줄 이름(`P5r4-LT-…`, `P5r4-LH-…`)으로 짝짓고 도구가 이름 목록 sha를 기록한다 |
| Z-A(R-Q) | `las/revA2/revA_RQ.jsonl`(48줄) | `93ced32cedb57888c37ea06dfbbe966c12c35d858f5b92a543e816f86cf953ca` | 2키 × 격자 48점 | 위와 같음(`P5r4-LQ-…`) |
| Z-T | `las/revA2/revA_RT.jsonl`(192줄, cand 비트 기준) | `c72f7e0882c50d86e565366866526ed55073d8bfef5c9f959b82c0e2885afd54` | 192 | `4160bddfff318f8c13b36652c3203e89a02159b5fd5a624499aa6ef0940fe933` |
| Z-T ref | `las/las_T1.jsonl`(b0 8줄)·`las/las_T2.jsonl`(184줄) | 봉인 때 기록 | 192 | Z-T와 같아야 한다 |
| Z-S | `las/revA2/revA_RS.jsonl`(30줄, 키 목록) | `7c407b6ee07b001f5504186fa013193ba6a2992516021f263b2bb537de43875d` | 30 | `19c78b49197ac53da5ae50808555c5879aabc90765589ea220830d5588a23950` |
| Z-S 비트 기준 | `las/k1/k1_YS.jsonl`(60줄 = P0 30 + P5r4 30) | `a31153a64ed9cbdf7410082e8dbda81b79e6d607c0a238d510ac34c0c9333ac6` | 30 × 2 | Z-S와 같아야 한다 |
| Z-C | `soil_defer/s2d_SC.jsonl`(456줄) | `70e91ec1234d56a918af1b4fc053c3175f0f14ab41e2b5f334890f7dc6cb08aa` | 456 | `fe6c9c46f2c799ee440d8a2a5d99d88099c51586297afd01d7201a52d26389d9` |
| Z-C 중 R4 평가 165키(ref 비트 기준) | `las/k1/k1_YP.jsonl`(206줄) | `0d985d5624f0fbb0219ca50d1c839b7db639011d6c2ab14fa9d84cfd197fc2c3` | 165 | `dc1e65d49bc0ea34fd04fdb7ba4eeceb7fc576ee15de9658dbe26927598b753b`(K1 원판 부록 A) |
| Z-C 중 R-S와 겹치지 않는 키(표본 밖) | — | — | 437 | `f20bb9e0b1b570660fd15c2a33a2abd66308efce10e1aeb3185cc178956edea7` |
| Z-X 참고(옛 R-X) | `las/revA2/revA_RX.jsonl`(4줄) | `04f7a4dcf435b66934a811af6cee4cb5fa657f8e897f4a503321dd126f4b0d78` | 4 | `bdad17c7c77abae2eb47c8b366d09d1882fe934fecd112b759040b894f79adfd` |

- `k1_YP.jsonl`은 206줄이다(Y-Pa 165 + Y-Pb 40 + 후보 필드가 빈 1줄). 도구는 K1on·`las_candidate` P0 줄만 비트 기준으로 쓰고, 나머지 줄 수와 이름을 출력한다. 빈 1줄의 정체는 봉인 전에 확인한다(초안 작성 때 내용은 보지 않았다).
- Chrono BT-C 기준: main checkout `07_results/S9/batch_V5-LAS-K1-REM_20261109_235554/`의 `REM_J2_B_top_Fs4_VB_gateon/controller_commands.npz`(`ebf86d1d…b559`), `REM_J2_B_top_Fs4_m1p1_VB_gateon/controller_commands.npz`(`97aace61…c8aa`). gateoff R1·R4 파일 sha도 각각 같다.
