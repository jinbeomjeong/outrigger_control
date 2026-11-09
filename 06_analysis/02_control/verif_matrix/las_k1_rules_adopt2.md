# K1 조건부 채택 재측정 판정 기준 — Chrono SCM 관문 꺼짐/켬 직접 측정 (봉인 원판)

- 작성: control-expert, 2026-11-09
- 상태: **새 원판. 이 규칙의 대상 행(2.2절)을 실행하기 전에 봉인한다.** 바꾸려면 새 판(rev1 …)을 만들고, 그 판이 결과를 보기 전인지 본 뒤인지를 첫머리에 적는다.
- 판의 성격: `las_k1_rules_adopt.md`(`864836d8…7ea8`)의 rev가 아니라 **새 원판**이다(사용자 결정 D-5, 이유 0.1절).
- 파일: `06_analysis/02_control/verif_matrix/las_k1_rules_adopt2.md` + `.sha256`. `.gitattributes`의 `06_analysis/02_control/verif_matrix/las_k1_rules* -text`가 두 파일을 덮는다.
- 봉인 때 master HEAD: `490c2db`(추적 파일 수정 없음).
- 사용자 결정
  - 2026-11-09 23시경(adopt 판정서 14.5 D-1 (가) = 선택지 A)
    1. Chrono로 다시 잰다. 프리셋은 LAS-b 켬(채택 대상), `--k1-order-gate off`로 decisions를 기록한다.
    2. 대상: J2 상단·중단·하단, J2 ×1.1, J1 ×1.1(+ 아래 D-1).
    3. gateon 짝(J2 상단, J2 ×1.1)으로 "막힘 → 취소 → 재평가" 경로를 본다.
    4. 하네스 사전 점검을 먼저 한다(1.3절).
    5. "취소 뒤 재평가 LOC" 처리를 이 규칙에 미리 정한다(3.3절).
  - 2026-11-09 초안 검토 뒤(D-1~D-5)
    - D-1: 초안의 R5(J2 ×1.1 t180)는 빼고 **J2 상단 ×1.1 V0**(태그 `final_C4G2_LAS`)로 바꾼다.
    - D-2: gateon 짝 2행(R7, R8)을 둔다.
    - D-3: **막힘 강제 진단 변형**(F1·F2)을 더한다. 정보용이고 등급에 넣지 않는다. 변형은 연구용 하위 클래스로 두고 `c2.py`는 바꾸지 않는다(2.3절).
    - D-4: 폐루프 120 s를 유지한다.
    - D-5: 새 원판 `las_k1_rules_adopt2.md`.
- 이어받는 규칙: K1 원판 `las_k1_rules.md`(`2742c976…e4a0`, K1 정의 1.1 그대로), rev1(`eeee4ab9…b4d3`), S-Ch 계획(`b0fe744f…6d9d`)·rev1(`d8f957cb…9295`), adopt(`864836d8…7ea8`, 9절 전환 절차를 그대로 쓴다).
- 규약
  - 제어: 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1, C2 음되먹임($u$ = 다리 행정 속도 명령 [m/s]).
  - 시각은 Chrono 절대 시각 [s](8 s 정착 포함)이다. 비교는 정수 주기 $n$ = `round(t / 0.1)`(Python 내장, 짝수 반올림, `c2.py` `_flat_soil_order_periods`와 같은 식)로만 한다. 부동소수 시각끼리 직접 비교하지 않는다(짝 일치 K-7은 같은 float인지를 본다).
  - 이름: 이 규칙의 K1 = LAS-b K1(R4c30 순서 관문, `SlopeClearanceMarginSettings.flat_soil_margin_order_gate`). touch-phase K1(2026-11-05 탈락)과도, 하네스 키 토큰 `K1`(크롤러 강성 ×1)과도 다르다.

| 기호 | 정의 | 단위 |
|---|---|---|
| LOC | 크롤러 이탈 확정(사건 `crawler_liftoff_confirmed`) | — |
| decision $D_i$ | `controller_meta.slope_clearance_margin.order_gate.decisions[i]`(시간순). 키 `t_loc_s, t_P_s, t_S_s, n_P, n_S, dP, r4_due_without_gate, would_block, applied` | — |
| R4 평가 LOC | `r4_due_without_gate` 참인 decision의 LOC | — |
| $L_1$ | 행의 **첫** R4 평가 LOC(1차 R4 LOC) | — |
| 취소 $r_j$ | `controller_meta.loc_revoke.t_revoke_s[j]`, 주기 $n_{r,j}$ | s, 주기 |
| 토양 모드 시작 | `controller_meta.soil.mode_starts[*]`(`t_s`, `source`) | s |
| 취소 뒤 LOC | $n_{loc}$보다 작은 취소 주기 $n_{r,j}$가 1건 이상 있는 decision | — |
| dP | $n_P - n_S$. K1은 dP ≤ 0이거나 $t_P$·$t_S$가 없으면 R4c30을 막는다 | 주기 |

## 0. 목적과 판의 성격

### 0.1 새 원판으로 하는 이유

1. adopt는 **저장 결과 그림자 판정**이고, 대상 집합 A(74행)를 부록 sha로 고정했다(adopt 2.6). 이 규칙은 **새 Chrono 실행**의 결과를 판정한다. 대상 집합, 정체성 검사(실행 정체성), 판정 도구가 모두 다르다. rev1로 adopt를 고치면 adopt의 봉인된 대상과 K 검사를 결과 뒤에 바꾸는 꼴이 된다.
2. adopt의 판정 `판정 불가`는 그대로 남는다(기록). 이 규칙은 adopt 6.2 "판정 불가 → 선택지 A"의 후속 실험이다.
3. 이어받는 것: K1 정의(원판 1.1), adopt 9절 전환 절차, adopt 7절 FLAG 문턱 `THIN_MARGIN` 12. 바꾸지 않는다.

### 0.2 판정 대상

- 질문: **채택 대상 제어기(LAS-b 켬)에 K1을 켜면, R4c30을 켜야 할 균일 연약 지면 행에서 R4c30이 켜지는가.**
- 측정
  - 관문 꺼짐 6행의 $L_1$ dP(decisions에 직접 기록되어 복원 불가가 없다).
  - 관문 켬 짝 2행의 실제 경로(적용 / 막힘 / 취소 / 재평가).
  - (정보용) 막힘 강제 변형 2행의 취소 → 재평가 경로.

## 1. 봉인 전에 본 데이터 (공개)

- **이 절의 데이터는 채택 근거로 쓰지 않는다.** 대상 키 선정, 재평가 LOC 정의, 사전 예측(8절)의 근거로만 썼다. 등급(4.2절)은 2.2절 R1~R8의 새 실행 결과로만 정한다.

### 1.1 adopt 판정과 판정 뒤 분석 (전부 봄)

- adopt 판정서(2026-11-09 22:3x) 3절 전체를 봤다.
  - MUST `OK` 13건(dP +49~+209).
  - `UNRECOVERABLE` 18건의 $n_R$·$n_S$·취소 주기·다음 LOC 주기.
  - PATCH 2건(−20).
  - `B_SOFT_NONPOS` 3행(dP 0).
  - 13절 사건 순서(21/21행): LOC → R4 → 취소(3~15주기 뒤) → 토양 모드 재시작(취소 다음 주기) → 재LOC. 재LOC `t_P_s`는 재시작 `soil_mode_t_s`와 같은 float다.
- 이 규칙의 대상 조건의 옛 제어기 값(adopt 3.2)
  - J2 상단·중단·하단 ×1.0: $n_R$ 451, $n_S$ 332, 취소 454, 재LOC 465(하단 466).
  - J2 상단 ×1.1: 553 / 333 / 566 / 574.
  - J1 상단 ×1.1: 492 / 333 / 497 / 509.
  - J2 ×1.1 t180(FINAL-REP-X)은 ×1.1 120 s 행과 같은 값(553/333/566/574)이다. D-1에서 뺀 근거다.
- 13 OK 행의 $n_R - n_P$는 14~17주기(16이 10건)다. 8절 예측에 쓴다.

### 1.2 코드 읽기 (`03_src/outrigger_sim/control/c2.py`, master 859deef, 490c2db에서 같은 줄)

| 위치 | 사실 | 이 규칙에 주는 뜻 |
|---|---|---|
| `_apply_slope_clearance_margin`(8765~8781) | E3c10이 서면 `return`(decision 없음). 아니면 R4 조건을 판단하고 `would_block = is_r4_due and self._is_flat_soil_order_blocked()`, `is_applied = is_r4_due and not (gate_on and would_block)`. 그 뒤 **매 LOC decision을 기록**한다(관문 꺼짐도) | E3c10 LOC에는 decision이 없다(K-8). 관문 꺼짐에서 $L_1$ 뒤 LOC도 decision이 남는다. `_is_flat_soil_order_blocked`는 R4 조건이 참일 때만 불린다(단락 평가) |
| `_is_flat_soil_margin_due`(8753~8763) | R4 조건: 토양 모드 사용 + **틈 목표 없음**(`clearance_target_m is None`) + 정착 기울기 ≤ 1° | 틈 목표가 서 있으면 뒤 LOC는 R4 평가 LOC가 아니다 |
| `with_10hz_d1`(2619~, 2798~2804) | `loc_revoke`: `enable`, `soil_gate`, `stroke_guard`, **`keep_slope_margin_on_revoke=True`**, `max_revokes` 2(클래스 기본) | 관문 꺼짐: $L_1$에서 적용된 +30 mm 목표는 취소 뒤에도 남는다. 재LOC는 R4 평가가 아니다(adopt 13절 3과 같다) |
| `_revoke_loc`(8510~8533) | `soil.window.clear()`, `is_soil_mode=False`, `plateau_start_s=None`. keep이면 `clearance_target_m`를 유지한다 | 관문 켬에서 $L_1$이 막히면 목표가 없다. 그래서 취소 뒤 재LOC에서 **R4가 다시 평가된다** |
| 토양 모드 갱신(8880~8895), S-1 창(8296~8327) | 크롤러 구역이 이미 풀려 있으면 취소 다음 주기에 토양 모드가 바로 다시 시작한다(`source` `release`). 같은 주기부터 창이 다시 쌓인다. 창이 끊기지 않으면 LOC 꼬리 첫 표본 = 창 첫 표본 = 재시작 주기다 | 취소 뒤 재LOC의 dP = 0이 **구조적으로** 나온다. 창이 중간에 비면 dP > 0, 재시작이 늦으면 dP < 0일 수 있다 |
| `C2Controller.from_params`(4570) | `return cls(...)` | 하위 클래스가 같은 생성 경로를 쓸 수 있다(2.3절 변형) |

- 결론(코드): **K1이 켜진 실행에서 R4c30이 끝까지 안 켜지는 경로가 있다.**
  - 경로 ①: $L_1$에서 dP ≤ 0으로 막힘 → 취소 → 재LOC에서 R4 재평가 → 구조적 0이면 다시 막힘 → (최대 2회 취소) → R4c30 없음.
  - 경로 ②(늦은 R4): 첫 LOC가 R4 평가가 아님(정착 기울기 > 1° 등) → 취소 → 재LOC에서 처음 R4 평가 → 구조적 0이면 막힘. **관문 꺼짐이면 적용되는 행에서 K1이 R4c30을 없앤다.**
  - $L_1$ dP > 0이면 적용되고 keep으로 목표가 남는다. 그 뒤 취소가 있어도 R4c30을 잃지 않는다.

### 1.3 하네스 사전 점검 (정보용)

- 읽은 것: `06_analysis/03_hydraulic/coupled/v5/las/k1/k1_{Y0,YP,YS,YT}.jsonl` 563줄의 `k1.decisions`, `event_names` 건수, `job.d1.key`.
- 도구(control-expert scratchpad `…\scratchpad\k1_remeasure\`): `scan_k1_harness.py`, `show_multi.py`, `revoke_timeline.py`, `flat_dp.py`.

| 점검 | 하네스 | Chrono(저장, 옛 제어기) |
|---|---|---|
| 대상 키 대응 | J2·J1 평지 ×1.0: `D1|H-S-0|J2|{T,M,B}|flat|K1`, `D1|H-S-0|J1|T|flat|K1`. **×1.1(질량)·t180 키는 K1 묶음에 없다**(`d1_rows.py`에 질량 축 없음). 저장 ×1.1 하네스(rev82·rev85)는 옛 제어기이고 decisions·취소 기록이 없다 | — |
| J2 평지 ×1.0 첫 LOC dP | T +92~+93, M +94, B +94~+95(VB·V0, K1off·on 같음). LOC 1개, **취소 0** | 옛 제어기 4/4행 취소(R4 LOC 3주기 뒤) → 복원 불가 |
| J1 평지 ×1.0 첫 LOC dP | T +36~+38, M +39, B +40 | +49~+51(11건) |
| 패치 G1+J2@FL T | −4, −5, −8, −15 | −20(S-Ch 2행, 10-28 G6P 1행) |
| 취소 사슬 | 563줄 중 20줄(고유 10조건). **모두 경사 행 또는 H-S-C-g**이고 첫 LOC는 E3c10(R4 평가 아님). 평지 균일 연약 지면 취소 0 | J2·×1.1 평지에서 거의 늘 취소 |
| 취소 뒤 재LOC dP(그림자) | 고유 9건: 0이 6건, +12, +13, −5 | 21/21건 0 |
| K1 켬 막힘 → 취소 → 재평가 | **관측 0**(K1on 줄의 막힘은 패치 행뿐이고 그 행은 취소 0) | — |

- 하네스 ↔ Chrono dP 차이는 고정된 −12주기 이동이 아니다. 균일 연약 지면에서는 Chrono가 더 크고(J1 +12~+15), 패치에서는 Chrono가 더 작다(−5~−16).
- 하네스는 평지 J2의 Chrono 취소 사슬을 재현하지 못한다. 그래서 하네스로 대상 키를 고르거나 Chrono 공백을 메우지 않는다. 하네스 추가 실행은 하지 않는다.

### 1.4 저장 Chrono 사건 이름 건수 (값 없음)

- 도구: `…\scratchpad\k1_remeasure\patch_revokes.py`. adopt 목록 300행에서 패치·S-Ch 행 16행의 사건 이름 건수만 셌다.
- 16행 모두 `INFO_LOC_REVOKED` 0, LOC 1. S-Ch gateoff R4 1, gateon `SKIPPED` 1.
- 그래서 패치 키에서 경로 ①(막힘 → 취소)은 저장 Chrono에서도 관측된 적이 없다.

### 1.5 이 규칙을 쓰려고 이번에 본 것

- adopt 규칙·판정서 전문, S-Ch 판정서 0절, `las_k1_chrono_rows.py` 전문, `run_S9.py`의 P3b·FINAL-REP-X 행 정의부와 `C2Controller.from_params` 호출(5820), `s9_batch.py` 태그 상수·`v5_vb_argv`·`v5_rigid_setting_args`, 저장 batch.json의 행별 벽시계(11절).
- 대상 행의 새 실행 결과는 없다(실행 전).

## 2. 판정 묶음 (Chrono) — cad-expert 행 정의 명세

### 2.1 공통

| 항목 | 값 |
|---|---|
| 배치 이름 | `V5-LAS-K1-REM`. `s9_batch`에 등록한다. 행 정의 모듈은 `04_scripts/02_chrono/las_k1_rem_chrono_rows.py`이고 `las_k1_chrono_rows.py`와 같은 꼴이다 |
| 행 꼴 | `run_S9.p3b_case("V5-LAS-K1-REM", soil, "B", level, 4.0)` + `p3b_level_argv` + 플랜트 인자(VB = `sb.v5_vb_argv()`, V0 = v5 인자 없음) + `--k1-order-gate <off|on>`. ×1.1은 `mass_scale` 1.1(`--mass-scale 1.1`) |
| 바닥 | 평지(경사 0/0), 균일 토양(`--soil J1|J2`, 패치 없음), P3b 패드 격자(`P3B_PAD_GRID_M`) |
| 패드·F_s | B(`dwg_rear250`), 4 kN |
| 제어기 | 프리셋 `C2Config().with_10hz_d1()`, LAS-b b0(`las_candidate` P0). VB 행 `--expect-controller final_C4G2_P3_LAS`, V0 행 `final_C4G2_LAS`. 모든 행이 `--k1-order-gate`를 **명시**한다(off = 프리셋 값) |
| 센서 | 압력 normal, IMU ideal, seed 20261026(S-Ch와 같음) |
| 실행 조건 | `--threads` = `run_S9.SCM_THREADS_FIXED`(4), start_env `OMP_WAIT_POLICY=PASSIVE`·`OUTRIGGER_HULL_HOOK=fast`, DLL sha `cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15`, 계획 풀 P. **짝(gateoff/gateon/변형)은 같은 풀 종류에서 돌린다** |
| 폐루프 시간 | P3b 고정 120 s(모든 행) |
| 행 키 | `case`, `rem_key`(R1~R8, F1·F2), `k1_candidate`(`K1off`/`K1on`), `k1_order_gate`, `k1_forced_block`(`off`/`first`), `v5_setting`(`VB`/`V0`), `role`(`judge`/`diag`), `pair_case`(짝 있는 행), `source_rows`(1.1절 옛 제어기 대응 행, 기록) |

### 2.2 판정 행 (8행, 등급은 이 행들로만 정한다)

| # | `rem_key` | case | soil | 오거 | 질량 | 플랜트·태그 | gate | 짝 |
|---|---|---|---|---|---|---|---|---|
| 1 | R1 | `REM_J2_B_top_Fs4_VB_gateoff` | J2 | top | 1.0 | VB `final_C4G2_P3_LAS` | off | R7, F1 |
| 2 | R2 | `REM_J2_B_middle_Fs4_VB_gateoff` | J2 | middle | 1.0 | VB `final_C4G2_P3_LAS` | off | — |
| 3 | R3 | `REM_J2_B_bottom_Fs4_VB_gateoff` | J2 | bottom | 1.0 | VB `final_C4G2_P3_LAS` | off | — |
| 4 | R4 | `REM_J2_B_top_Fs4_m1p1_VB_gateoff` | J2 | top | 1.1 | VB `final_C4G2_P3_LAS` | off | R8, F2 |
| 5 | R5 | `REM_J2_B_top_Fs4_m1p1_V0_gateoff` | J2 | top | 1.1 | **V0** `final_C4G2_LAS` | off | — |
| 6 | R6 | `REM_J1_B_top_Fs4_m1p1_VB_gateoff` | J1 | top | 1.1 | VB `final_C4G2_P3_LAS` | off | — |
| 7 | R7 | `REM_J2_B_top_Fs4_VB_gateon` | J2 | top | 1.0 | VB `final_C4G2_P3_LAS` | on | R1 |
| 8 | R8 | `REM_J2_B_top_Fs4_m1p1_VB_gateon` | J2 | top | 1.1 | VB `final_C4G2_P3_LAS` | on | R4 |

- R5의 V0는 v5 유압 인자를 하나도 주지 않는다(`v5_rigid_setting_args("V0") = {}`와 같은 뜻). VB 행과 달리 R5는 플랜트와 태그가 둘 다 다르다. 그래서 R4와 R5는 짝이 아니다(짝 검사 없음).
- 행 모듈 `argv_check`에서 R5의 실행 config가 `final_C4G2_LAS` 기대값을 통과하지 못하면, 행 정의가 이 규칙과 맞지 않는 것이다. 실행 전 감사에서 차단하고 새 판으로 고친다(실행하지 않는다).

### 2.3 막힘 강제 진단 변형 (2행, `role` `diag`, **정보용**)

- 목적: $L_1$에서 K1이 막았을 때 "취소 → 재평가" 경로에서 R4c30이 끝까지 켜지지 않는지(경로 ①) 직접 기록한다. MUST 행에서 $L_1$ dP > 0이면 관문 켬 행(R7·R8)으로는 이 경로를 볼 수 없다(3.4절).
- **등급에 넣지 않는다.** F1·F2의 어떤 결과도 4.2절 등급과 ①~③ 조건을 바꾸지 않는다. 변형 행이 실패·결측이어도 판정은 계속한다.

| # | `rem_key` | case | 조건 | gate | forced |
|---|---|---|---|---|---|
| 9 | F1 | `REM_J2_B_top_Fs4_VB_gateon_forced1` | R7과 같음(J2 상단 ×1.0, VB) | on | `first` |
| 10 | F2 | `REM_J2_B_top_Fs4_m1p1_VB_gateon_forced1` | R8과 같음(J2 상단 ×1.1, VB) | on | `first` |

- 변형 정의(`first`)
  - 행의 **첫** `_is_flat_soil_order_blocked()` 호출에서 무조건 참(막힘)을 돌려준다. 1.2절대로 이 함수는 R4 조건이 참일 때만 불리므로, 첫 호출 = $L_1$이다.
  - 그 뒤 호출은 원래 규칙(`n_P > n_S`가 아니면 막힘)을 그대로 쓴다.
  - 강제한 호출에서도 원래 규칙의 값(`natural_blocked`)과 $n_P$, $n_S$, dP를 계산해 기록한다.
  - 그 밖의 동작은 바꾸지 않는다(설정·이득·사건 이름·명령 경로 그대로). decision 기록은 원래 함수가 하므로 F1·F2의 $L_1$ decision은 `would_block` 참, `applied` 거짓이다.
  - 관문 꺼짐(`--k1-order-gate off`)과 함께 쓰면 오류로 멈춘다(강제 막힘이 효과가 없기 때문이다).
- 변형 구현 위치: `c2.py`는 바꾸지 않는다. 9.3절 명세(python-expert 래퍼 + cad-expert run_S9 인자·행).
- 기록 필드(`controller_meta.k1_forced_block`)
  - `mode`(`first`), `class`(하위 클래스 전체 이름), `module_sha256`.
  - `forced_t_loc_s`, `forced_n_loc`, `natural_blocked`, `n_P`, `n_S`, `dP`(강제 호출 시점의 원래 값).
  - `calls`: 모든 `_is_flat_soil_order_blocked` 호출의 (`t_s`, `forced`, `result`, `n_P`, `n_S`).
- 판정 도구가 F1·F2에서 내는 정보용 기록
  - `FORCED_AT_L1`: 강제한 LOC = 행의 $L_1$(decision 주기)인가.
  - `FORCED_PAIR_L1`: F의 $L_1$ 튜플($n_{loc}$, $n_P$, $n_S$, dP, `t_P_s`, `t_S_s`)이 짝 R(R7·F1 ↔ R1, R8·F2 ↔ R4)과 같은가. 다르면 그 변형 결과는 "짝과 다른 궤적"으로 표시하고 해석하지 않는다.
  - 경로 분류
    - `FORCED_NO_REVOKE`: 강제 막힘 뒤 취소 0. 재평가가 없으므로 R4c30은 없다(+30 mm 없이 끝남).
    - `FORCED_R4_NEVER`: 취소 ≥ 1, 재평가 decision ≥ 1, 끝까지 `applied` 참 decision 0.
    - `FORCED_R4_LATE`: 재평가 decision 가운데 `applied` 참이 있다(그 주기와 dP).
  - 재평가 decision마다 `struct_zero`(3.1절)와 dP.
  - 행 끝: 최대 행정, 끝 크롤러 틈, 첫 DONE·READY, 최종 phase, 사건 `FAULT_*`·`WARN_*` 이름.

## 3. 분류 (행·LOC)

### 3.1 decision 표

- 각 행에서 decision을 시간순으로 읽는다. LOC 사건·취소 시각·토양 모드 시작과 대조해 decision마다 다음을 붙인다.
  - `post_revoke`: $n_{loc}$보다 작은 취소 주기 $n_{r,j}$가 있는가.
  - `restart_n`: 그 decision 앞 마지막 취소 뒤 첫 토양 모드 시작(주기 ≥ $n_{r,j}$)의 주기. 없으면 None.
  - `struct_zero`: `post_revoke` 참이고 $n_S$ = `restart_n`이고 $n_P = n_S$.

### 3.2 $L_1$과 행 상태 (판정 행 가운데 관문 꺼짐 6행 R1~R6)

| 행 상태 | 조건 | K1이 켜졌다면 |
|---|---|---|
| `POS` | $L_1$ 있음, $t_P$·$t_S$가 수, dP($L_1$) > 0 | $L_1$에서 적용, 목표 유지(keep) → R4c30 있음 |
| `NONPOS` | $L_1$ 있음, dP($L_1$) ≤ 0 또는 $t_P$·$t_S$ None, 그리고 $L_1$이 `struct_zero`가 아님 | $L_1$에서 막음(경로 ①로 끝까지 없을 수 있음) |
| `LATE_STRUCT` | $L_1$이 `post_revoke`이고 `struct_zero` | 막음(경로 ②). **구조적 0에 의한 R4c30 상실** |
| `NO_R4` | R4 평가 LOC 0(토양 모드 없음, E3c10, 정착 기울기 > 1°, LOC 없음, $L_1$ 전 FAULT 등) | K1 무관 |
| `MISSING` | 7절 결측 | 알 수 없음 |

- `POS`이면서 $L_1$이 `post_revoke`인 경우(늦은 R4, dP > 0)는 `POS`로 세고 FLAG `LATE_R4`를 단다.

### 3.3 재평가 LOC 처리 (사용자 결정 5)

1. **판정 단위는 $L_1$이다.** 관문 꺼짐 행에서는 keep 때문에 $L_1$ 뒤 R4 평가 LOC가 생기지 않는다(1.2절). 생기면 K-6 stop이다(가정 붕괴).
2. 관문 꺼짐 행의 **취소 뒤 LOC decision**(R4 평가 아님, `r4_due_without_gate` 거짓)은 "K1이 $L_1$을 막았다면 마주칠 재평가 LOC"의 그림자다. 그 dP와 `struct_zero`를 FLAG `SHADOW_RELOC`로 기록만 한다. 등급에 넣지 않는다(+30 mm 목표 유무로 궤적이 달라지므로 정확한 대리값이 아니다).
3. 관문 꺼짐에서 $L_1$이 취소 뒤 LOC이면(경로 ②) 그 dP를 그대로 센다. 구조적 0이면 `LATE_STRUCT` → 등급 `미달`(사유 `STRUCT_ZERO`). **구조적 0을 "측정 아님"으로 빼지 않는다.** K1이 실제로 그 LOC를 막기 때문이다.
4. 관문 켬 판정 행(R7·R8)에서 $L_1$이 막히고 재평가 LOC가 오면, 모든 R4 평가 decision을 기록한다. 행 결과는 `R4_APPLIED_LATE`(재평가에서 적용) / `R4_NEVER`(끝까지 막힘)와 재평가 decision마다의 `struct_zero`로 적는다. 이때 짝 gateoff 행은 이미 `NONPOS`라 등급은 `미달`이고, 관문 켬 결과는 원인 기록이다.
5. 관문 켬 판정 행에서 $L_1$이 적용되면, 그 뒤 R4 평가 decision은 0건이어야 하고(목표 유지) `INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order` 사건도 0건이어야 한다. 아니면 K-8 stop.
6. 막힘 강제 변형(F1·F2)의 재평가 경로는 2.3절 정보용 기록으로만 남긴다. 3.3 #4의 원인 기록과 같은 꼴로 적되, 등급·조건에 쓰지 않는다.

### 3.4 관문 켬 짝 (R7↔R1, R8↔R4)

- 관문은 R4 평가 decision에서만 동작한다. 그래서 $L_1$까지 두 행은 같아야 한다. $L_1$의 ($n_{loc}$, $n_P$, $n_S$, dP, `t_P_s`·`t_S_s` float)가 같아야 한다(K-7).
- $L_1$ dP > 0이면 관문 켬도 적용되고, 그 뒤 동작이 같아야 한다. 예측 P-8: `controller_commands.npz` sha256이 짝끼리 같다(기록, 등급 아님). 다르면 FLAG `PAIR_DIVERGE`와 첫 차이 주기를 적는다.
- $L_1$ dP > 0이면 "막힘 → 취소 → 재평가" 경로는 판정 행에서 **관측되지 않는다.** 판정서에 "관측 안 됨"을 적는다(0건을 통과로 세지 않음). 그 경로는 F1·F2(정보용)와 1.2절 코드, SHADOW_RELOC 기록으로만 본다.

## 4. 판정

### 4.1 조건 (판정 행 R1~R8만)

- ① **MUST**: 관문 꺼짐 6행(R1~R6)이 모두 `POS` 또는 `NO_R4`이고, `POS` ≥ 4행이고, J2 ×1.1 쪽(R4·R5) 중 `POS` ≥ 1행.
- ② **PATCH**: 이 묶음에는 패치 행이 없다. adopt ②(S-Ch 2행, dP −20, 봉인 전 기지 행)를 그대로 쓰고, 판정서에 "기지 행뿐"을 다시 공개한다.
- ③ **짝**: R7·R8 각각 K-7이 참이다. 그리고 짝 gateoff가 `POS`이면 관문 켬에서 $L_1$이 적용된다(`applied` 참, 같은 주기 사건 `INFO_LOC_FLAT_SOIL_MARGIN:` 있음, 3.3 #5 참). 짝 gateoff가 `POS`가 아니면 ③은 그 짝에서 검사하지 않는다(등급은 ①에서 이미 정해진다).

### 4.2 등급 (위에서부터 처음 해당하는 것)

| 등급 | 조건 | 행동 |
|---|---|---|
| `stop` | 5절 K-0~K-10 중 거짓(F1·F2 전용 항목 제외) | 판정 없음. 원인 공개, 사용자에게 묻는다 |
| `미달` | R1~R6에 `NONPOS` 또는 `LATE_STRUCT` ≥ 1(사유 코드 `MEASURED_NONPOS` / `STRUCT_ZERO`) | **전환하지 않는다.** 해당 행 표(키, $L_1$, $t_P$, $t_S$, dP, 취소·재평가 경로, 관문 켬 짝 결과)와 함께 묻는다. `STRUCT_ZERO`이면 K1 정의 보완안(예: 재평가 LOC는 취소 전 토양 모드 시작을 쓴다)을 선택지로 적는다(정의 변경 = K1 원판부터 다시) |
| `판정 불가` | R1~R6에 `MISSING` ≥ 1, 또는 `POS` < 4, 또는 R4·R5 모두 `NO_R4` | **전환하지 않는다.** 건수·행을 공개하고 선택지(재실행·범위 변경)를 묻는다 |
| `부분 통과` | ①은 참, ③이 거짓(K 검사 밖 원인. 예: R7·R8 결측, 짝 gateoff `POS`인데 관문 켬 행이 $L_1$ 전 FAULT로 끝남) | 자동 전환하지 않는다. 사용자에게 묻는다 |
| `통과` | ①·②·③ 참 | adopt 9절 전환 절차의 **승인 조건 충족**. 착수는 메인 세션이 사용자에게 알리고 승인을 받은 뒤 한다(2026-11-08 저녁 방침) |

- `미달`이 `판정 불가`보다 먼저다.
- 판정 뒤 문턱(dP > 0, `POS` ≥ 4, `THIN_MARGIN` 12)을 바꾸지 않는다.
- F1·F2(정보용)의 결과는 등급을 바꾸지 않는다. F의 경로가 `FORCED_R4_NEVER`여도 판정 행이 `통과`이면 `통과`다. 그 경우 판정서와 사용자 보고에 "K1이 첫 R4 LOC를 막으면 R4c30이 끝까지 없다는 경로가 Chrono에서 확인됨"을 반드시 적는다(채택 뒤 알려진 한계).
- adopt의 `UNRECOVERABLE` 18건은 이 판정에서 다시 세지 않는다(옛 제어기 행, 기록). 판정서에 "옛 제어기 18행 자체는 여전히 셀 수 없다"를 적는다.

## 5. 정체성·일관성 (판정 행 R1~R8: 하나라도 거짓이면 stop)

| # | 검사 |
|---|---|
| K-0 | 이 규칙 sha256 = `.sha256` 기록. 판정 도구 sha256 = 실행 전 감사 기록 = prelaunch = postrun = judge = 판정 때 파일. 실행 전 감사 리포트 파일 sha256 = prelaunch 기록(10절 #1) |
| K-1 | 실행 HEAD: 10행 `code_state.git_at_start.head`가 모두 prelaunch HEAD와 같다. `git diff --quiet <prelaunch HEAD> <postrun HEAD> -- 03_src 02_params 04_scripts` 참. 10행 dirty 목록 빈 목록. prelaunch·postrun `git status --porcelain`이 허용 목록(prelaunch에 미리 적음, 기본 빈 목록) 밖 0줄 |
| K-2 | 코드 sha(작업 트리 CRLF, HEAD blob LF): `run_S9.py`, `s9_batch.py`, `las_k1_rem_chrono_rows.py`, `k1_forced_block.py`(9.3절), `c2.py`, `zero_calibration.py`, `hull_hook.py`, `late_loc_rule.py`, `v5_options.py`. result.json·batch.json에 기록된 sha와 같다. `c2.py` blob이 `859deef`의 blob과 같다(변형이 `c2.py`를 바꾸지 않았음) |
| K-3 | DLL sha `cec997d7…7e15`, result.json `hull_hook.mode` = `requested` = `fast`, `fallback_reason` None, batch `mixed_hull_mode` 거짓 |
| K-4 | `args.threads` 4 = `num_threads_chrono`, batch `omp_wait_policy` PASSIVE, placement가 계획 풀과 같음, `affinity_ok`·`power_throttling_off_ok` 참, 짝(R1·R7·F1, R4·R8·F2) 같은 풀 종류 |
| K-5 | 인자: 각 행 `args`가 2.2·2.3 표와 같다. R1↔R7, R4↔R8의 argv 차이는 `--k1-order-gate` 값 하나(+ `case`). R7↔F1, R8↔F2의 차이는 `--k1-forced-block first` 하나(+ `case`). 고정값(seed, grade, F_s, pad, soil, level, mass_scale, duration, expect_controller, v5 인자) 일치 |
| K-6 | 제어기: `expect_controller.ok` 참(행의 태그). `c2_setup.k1_order_gate` = 행 값, `slope_clearance_margin.order_gate.enabled` = 행 값. `controller_meta.loc_revoke.settings.keep_slope_margin_on_revoke` 참, `max_revokes` 2, `period_s` 0.1. 판정 행 `controller_meta.k1_forced_block` 없음, `c2_setup.k1_forced_block` `off`, 제어기 클래스 = `C2Controller`. 관문 꺼짐 행: R4 평가 decision ≤ 1(keep 가정), `SKIPPED:order` 사건 0. `order_gate.decisions` 키 존재 |
| K-7 | 짝 일치: R7↔R1, R8↔R4의 $L_1$ 튜플(3.4절)이 완전히 같다. 둘 다 `NO_R4`이면 첫 LOC 주기가 같다 |
| K-8 | 기록 일관성: (a) decision 수 = 토양 모드 시작 뒤 LOC 가운데 E3c10이 아닌 LOC 수. (b) 각 decision $n_{loc}$가 LOC 사건 주기에 있다. (c) decision `t_S_s` = `mode_starts` 가운데 주기 < $n_{loc}$인 마지막 시작의 `t_s`(같은 float). (d) 취소 meta 건수 = `INFO_LOC_REVOKED` 사건 수, 주기가 같다. (e) `applied` 참 decision ↔ 같은 주기 `INFO_LOC_FLAT_SOIL_MARGIN:` 사건 1건, `would_block` 참·`applied` 거짓 ↔ `INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order` 1건. (f) 3.3 #5 |
| K-9 | 결측 처리 검사: `controller_meta`·`soil`·`events`가 정상(`{"error": …}` 아님), `restored_from` None, rc 0, `result.json` 존재. 거짓인 행은 stop이 아니라 7절 `MISSING`으로 간다. K-9는 `MISSING`이 규칙대로 붙었는가만 본다 |
| K-10 | 두 경로 재집계(9.2절) 완전 일치. **판정 도구 밖에서 판정서가 확정한다** |

- F1·F2 전용(거짓이면 그 변형 결과만 "무효"로 표시, 판정은 계속): K-1~K-5는 판정 행과 같이 본다. 그리고 `controller_meta.k1_forced_block.mode` `first`, `class`·`module_sha256` = K-2 기록, `c2_setup.k1_forced_block` `first`, 관문 `enabled` 참, 강제 호출 정확히 1건(`calls` 중 `forced` 참 1건). F1·F2의 K-1~K-5가 거짓이면 그것은 묶음 전체 실행 정체성 문제이므로 판정 행에서도 같은 항목을 다시 확인한다.

## 6. 기록 (등급에 영향 없음)

- 행별: 상태, $L_1$($n_{loc}$, $n_P$, $n_S$, dP, $n_{loc} - n_P$), decision 전부, 취소 주기, 토양 모드 시작(주기, source), E3c10 LOC 수, 첫 DONE·READY 시각, 최종 phase, 최대 행정, 끝 크롤러 틈.
- FLAG(판정 행)
  - `THIN_MARGIN`: `POS` 행 dP ≤ 12.
  - `LATE_R4`: $L_1$이 취소 뒤 LOC인 `POS` 행.
  - `SHADOW_RELOC`: 관문 꺼짐 행의 취소 뒤 decision(dP, `struct_zero`). 건수와 0의 비율.
  - `PAIR_DIVERGE`: 짝 명령 sha가 다름(첫 차이 주기).
  - `GATEON_PATH`: 관문 켬 판정 행의 R4 평가 decision 순서와 결과(`R4_APPLIED_LATE` / `R4_NEVER`).
  - `OLD_CTRL_SHIFT`: 각 행 $L_1$과 1.1절 옛 제어기 대응 값의 차이($n_{loc}$, $n_S$. 옛 행은 $n_P$ 없음). LAS-b 영향 기록.
- 정보용 FLAG(F1·F2, 2.3절): `FORCED_AT_L1`, `FORCED_PAIR_L1`, `FORCED_NO_REVOKE` / `FORCED_R4_NEVER` / `FORCED_R4_LATE`, 재평가 decision `struct_zero`.
- 하네스 대조: R1~R3·R6의 dP와 1.3절 하네스 값(×1.1은 하네스 값 없음, R6은 J1 ×1.0 하네스와 비교만).

## 7. 결측

| 경우 | 처리 |
|---|---|
| 행 실행 실패(rc ≠ 0, result.json 없음, 부분 기록) — Chrono·인프라 원인(크래시, 메모리, 재부팅) | `MISSING`. **같은 argv·같은 HEAD로 1회만** 다시 돌린다(사용자에게 알린 뒤). 다시 돈 행은 `rerun_of`와 원 행 로그를 남긴다. 두 번째도 실패하면 `MISSING`으로 확정한다 |
| 결과가 있으나 제어 FAULT·안전 정지로 $L_1$ 전에 끝남 | 결측이 아니다. `NO_R4`(K1 무관)로 세고 원인을 적는다 |
| 관문 켬 판정 행(R7·R8) 결측 | 남은 행은 따로 센다. ③은 그 짝에서 거짓 → `통과`가 될 수 없다. 등급은 ①이 참이면 `부분 통과` |
| 관문 꺼짐 행(R1~R6) 결측 | `판정 불가`(4.2) |
| 변형 행(F1·F2) 결측·실패 | 정보 없음으로 기록한다. 재실행 규칙은 판정 행과 같다(1회). 등급에 영향 없음 |
| decisions 키 없음(코드 회귀) | K-6 stop |

- 결측 행을 하네스·옛 Chrono 행으로 메우지 않는다.

## 8. 사전 예측 (판정 기준 아님)

- 근거: 1.1절 옛 제어기 $n_{loc}$·$n_S$와 13 OK 행의 $n_{loc} - n_P$ ∈ [14, 17]. 점 예측 dP ≈ $n_{loc}$ − 16 − $n_S$. LAS-b 영향은 작다고 본다. 같은 패치 키에서 옛 제어기와 LAS-b 제어기가 모두 −20이었다.

| # | 항목 | 예측 |
|---|---|---|
| P-1 | R1·R2·R3 dP | 모두 > 0. 점 ≈ +103, 범위 [+60, +140] |
| P-2 | R4·R5 dP | 모두 > 0. 점 ≈ +204, 범위 [+120, +240]. R5(V0)는 R4와 $n_{loc}$가 ±20주기 안 |
| P-3 | R6 dP | > 0. 점 ≈ +143, 범위 [+90, +180] |
| P-4 | 상태 | R1~R6 모두 `POS`. `NO_R4` 0, `LATE_STRUCT` 0 |
| P-5 | 취소 | R1~R6 중 4~6행에서 $L_1$ 뒤 취소 ≥ 1 |
| P-6 | `SHADOW_RELOC` | 취소 뒤 decision의 ≥ 70 %가 `struct_zero`(Chrono 옛 21/21, 하네스 6/9) |
| P-7 | R4 ↔ R5 | 두 행 모두 `POS`. dP 차 ≤ 30주기 |
| P-8 | 짝 | R7·R8에서 $L_1$이 적용되고 명령 sha가 짝(R1·R4)과 같다. 판정 행에서 막힘 → 취소 → 재평가 경로는 관측되지 않는다 |
| P-9 | `THIN_MARGIN` | 0 |
| P-10 | 등급 | `통과`(높음). 다음으로 가능한 것은 LAS-b로 정착 기울기·LOC 순서가 바뀐 `NO_R4` 증가에 의한 `판정 불가` |
| P-11 | F1·F2(정보용) | `FORCED_AT_L1`·`FORCED_PAIR_L1` 참. 강제 막힘 뒤 +30 mm 목표가 없어 R1·R4보다 행정이 작다. 취소는 확실하지 않다(F1 50 %, F2 60 % 정도로 본다). 취소가 나면 재평가 decision은 `struct_zero`이고 `FORCED_R4_NEVER`(높음). 취소가 없으면 `FORCED_NO_REVOKE` |

## 9. 판정 도구, 두 경로, 변형 구현

### 9.1 경로 1 — 판정 도구 (python-expert 구현)

- 파일: `06_analysis/02_control/verif_matrix/scripts/las_k1_rem_judge.py`(`verif_matrix/scripts/* -text` 대상). dynamics-dev, 표준 라이브러리만 쓴다. 프로젝트 모듈과 다른 판정 도구를 import하지 않는다. S-Ch 도구(`las_k1_sch_judge.py`)의 정체성 검사 코드는 **복사**한다.
- 하위 명령
  - `prelaunch --batch-plan <행 목록 JSON> --audit-report <rem_prelaunch_audit.md> --out <rem_prelaunch.json>`: HEAD, `git status` 허용 목록, K-2 코드 sha, DLL sha, 도구 sha, 규칙 sha, 실행 전 감사 리포트 파일 sha256.
  - `postrun --batch <배치 폴더> --prelaunch <…> --out <rem_postrun.json>`: K-1~K-4를 다시 확인한다.
  - `judge --batch <…> --prelaunch <…> --postrun <…> --rules <이 규칙> --expect-tool-sha <sha> --out <judge_REM.json>`: K-0~K-9, 3~6절, 2.3절 정보용 기록.
- 출력
  - `rules_sha256`, `tool_sha256`, `git_head`, `taken_utc`, `files_read_sha256`
  - `k_checks`, `rows`(3.1절 decision 표 포함), `pairs`, `flags`
  - `diag`(F1·F2: K 전용 항목, 정보용 FLAG, 경로 분류)
  - `grade_provisional`, `grade_reasons`, `predictions`(안/밖), **`k10: null`**
- 종료 코드: 0 `통과`(잠정), 1 `미달`·`판정 불가`·`부분 통과`, 2 `stop`, 3 도구 오류. 잠정 등급임을 출력 첫 줄과 JSON에 적는다(adopt 실행 전 감사 A-1 교훈). F1·F2 결과는 종료 코드에 영향을 주지 않는다.
- 단위 시험(`05_tests/unit/test_las_k1_rem_judge.py`, 합성 result.json)
  1. `POS`·`NONPOS`·`NO_R4`·`MISSING` 각 1행.
  2. 취소 뒤 재LOC $t_P = t_S$ → `struct_zero` 참. 재시작 뒤 창이 끊긴 재LOC(dP > 0) → 거짓.
  3. $L_1$이 취소 뒤 LOC + `struct_zero` → `LATE_STRUCT` → `미달`/`STRUCT_ZERO`.
  4. 관문 꺼짐 행에 R4 평가 decision 2건 → K-6 stop.
  5. 짝 $L_1$ float 1 ulp 차이 → K-7 stop.
  6. 관문 켬 `R4_NEVER`(막힘 → 취소 → 재평가 막힘) 경로 기록.
  7. `INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order`를 적용으로 세지 않는다(정확 이름).
  8. 같은 주기 토양 모드 시작은 $t_S$에 넣지 않는다(K-8 (c)).
  9. `POS` 3행 + `NO_R4` 3행 → `판정 불가`. R4·R5 모두 `NO_R4` → `판정 불가`.
  10. 반올림: 34.95/0.1 → 350, 34.85/0.1 → 348.
  11. 변형 행: `FORCED_R4_NEVER`·`FORCED_NO_REVOKE`·`FORCED_R4_LATE` 분류. 변형 행이 무엇이든(결측 포함) 등급·종료 코드가 바뀌지 않는다. 판정 행에 `k1_forced_block`가 있으면 K-6 stop.

### 9.2 경로 2 — 독립 재집계 (control-expert)

- scratchpad `recount_rem.py`. 판정 도구·프로젝트 모듈을 열지도 import하지도 않는다. result.json·batch.json·이 규칙만 읽는다.
- 출처를 경로 1과 다르게 둔다.
  - LOC: `controller_meta.soil.t_loc_s`와 decision 먼저, 사건은 대조용.
  - $t_S$: `mode_starts` → 사건 `soil_mode_start` 순.
  - 취소: 사건 → meta 순.
- 경로 2 출력 sha를 경로 1 실행 전에 메인 세션에 넘긴다. 그 뒤 고치지 않는다. 첫 불일치 뒤 맞춘 항목은 독립이 아님을 공개한다.
- K-10 비교 대상: 행별 (상태, $L_1$ 튜플, decision 표, `struct_zero`), 짝 결과, FLAG 건수, 등급, F1·F2 경로 분류. 허용 오차는 없다.

### 9.3 변형 구현 명세 (D-3)

- **python-expert**: `04_scripts/02_chrono/k1_forced_block.py`
  - `class K1ForcedBlockC2Controller(C2Controller)`
    - `_is_flat_soil_order_blocked` 재정의: 원래 값(`super()`)과 $n_P$, $n_S$(`_flat_soil_order_periods`)를 먼저 계산한다. 첫 호출이면 참을 돌려주고 강제 기록을 남긴다. 그 뒤는 원래 값을 돌려준다. 모든 호출을 `calls`에 쌓는다.
    - `meta()` 재정의: `super().meta()`에 `k1_forced_block`(2.3절 기록 필드)을 더한다. 다른 키는 바꾸지 않는다.
    - 생성 시 `config.slope_clearance_margin.flat_soil_margin_order_gate`가 거짓이면 `ValueError`.
  - `module_sha256()`: 이 파일 sha256(CRLF 작업 트리 원시 바이트).
  - `c2.py`는 바꾸지 않는다. private 메서드 이름에 기대므로, 모듈 import 때 `C2Controller`에 두 메서드가 있는지 확인하고 없으면 멈춘다.
  - 단위 시험 `05_tests/unit/test_k1_forced_block.py`(시뮬레이션 없음, 합성 상태)
    1. 첫 R4 조건 참 LOC에서 막힘, decision `would_block` 참·`applied` 거짓.
    2. 둘째 호출부터 원래 규칙(dP > 0 → 적용, dP ≤ 0 → 막힘).
    3. 관문 꺼짐 config → `ValueError`.
    4. 강제 기록 필드와 `calls` 내용.
    5. 강제 호출 전까지 명령·meta가 `C2Controller`와 같음(같은 입력 열).
- **cad-expert**
  - `run_S9.py level`에 `--k1-forced-block {off,first}`(기본 `off`)를 더한다.
    - `first`이면 `C2Controller.from_params` 대신 `K1ForcedBlockC2Controller.from_params`를 쓴다. `--k1-order-gate on`이 아니면 종료 2.
    - `c2_setup.k1_forced_block`(`requested`, `class`, `module_sha256`)을 기록한다. `off`이면 클래스가 `C2Controller`임을 기록한다.
    - `--expect-controller` 점검은 그대로 둔다(config는 같다).
  - `las_k1_rem_chrono_rows.py`: 2.2·2.3절 10행, `s9_batch` 등록, `argv_check`(S-Ch 꼴, 고정값 표, 짝 argv 차이, R5 `final_C4G2_LAS` 기대 통과, F1·F2 `--k1-forced-block first`).
  - 단위 시험 `05_tests/unit/test_las_k1_rem_chrono_rows.py`: 10행, 짝 argv 차이(K-5), `role`, 시뮬레이션 없음.
- 순서: 이 규칙 봉인·커밋 → python-expert 래퍼와 판정 도구, cad-expert run_S9 인자와 행 모듈(worktree) → 병합 → 실행 전 감사(차단 0) → 배치표 → 실행.

## 10. S-Ch·adopt 교훈 체크리스트

| # | 항목 | 이 규칙의 처리 |
|---|---|---|
| 1 | 실행 전 감사 결과를 판정서에 옮기는 절차 | 메인 세션이 verif-protocol-auditor `[시점] 실행 전` 리포트 원문을 `06_analysis/03_hydraulic/coupled/v5/las/k1/rem_prelaunch_audit.md`로 **그대로 저장**한다. 그 sha256을 `prelaunch`에 넣는다(K-0). 판정서는 그 파일과 sha를 인용한다 |
| 2 | K-9/K-10 외부 처리 | 도구 등급은 잠정(`grade_provisional`, `k10: null`). 등급과 P-예측 안/밖은 K-10 대조 뒤 판정서에서 확정한다. 도구는 K-10을 참으로 세지 않는다(adopt A-1·A-2) |
| 3 | 결측 처리 | 7절. 1회 재실행 규칙을 실행 전에 정했다. 결측을 다른 모델로 메우지 않는다 |
| 4 | 실행 중 커밋 금지 | prelaunch부터 postrun까지 **main checkout에 커밋·병합·체크아웃 금지**(다른 세션 포함). 다른 작업은 worktree에서 한다. 미추적 파일은 허용 목록이 아니라 `--untracked-files=no` 기준으로 본다(K-1, prelaunch에 기준을 적는다). 결과·판정서 커밋은 postrun 뒤에 한다 |
| 5 | 값과 무관한 건수를 봉인 전에 센다 | 저장 결과·하네스에서 사건 이름 건수(취소·R4·SKIPPED)를 봉인 전에 셌다(1.3·1.4절) |
| 6 | 하네스 주기 예측의 Chrono 이탈 | 예측은 저장 Chrono $n_{loc}$·$n_S$로 했다(8절). 하네스 값은 대조 기록만 한다 |
| 7 | 덮어쓰는 메타에 기대지 않음 | 판정은 decisions(LOC마다 남는 기록)만 쓴다. `soil.t_P_s`(마지막 값)는 대조용 |
| 8 | 0건 통과 금지 | `POS` ≥ 4, J2 ×1.1 `POS` ≥ 1. 관측 안 된 경로는 "관측 안 됨"으로 공개한다(3.4) |
| 9 | 정확 사건 이름·정수 주기 | `split(":",1)[0]` 정확 일치, `_SKIPPED` 접두어 함정 시험(9.1 #7), 같은 주기 시작 제외 |
| 10 | 태그 | 이 묶음은 옛 태그(`final_C4G2_P3_LAS`·`final_C4G2_LAS`)로 돈다. 전환은 adopt 9절(태그 소비자, `endswith("_LAS")` 함정)대로 한다 |
| 11 | 짝 정체성 | 짝 argv 차이 하나, 같은 풀 종류, $L_1$ float 동일(K-5·K-4·K-7) |
| 12 | 진단 변형과 판정 분리 | F1·F2는 `role` `diag`, 등급·종료 코드 영향 없음(단위 시험 9.1 #11). 판정 행에 변형이 섞이면 K-6 stop. `c2.py` 불변은 K-2 blob 대조로 확인한다 |

## 11. 비용 (가정)

- 근거(실측)
  - S-Ch 2행(VB, G1+J2@FL, 폐루프 200 s, 4스레드, hull fast, P 2행 동시): 5,628 / 5,658 s. 모의 1 s당 약 27 s.
  - 옛 P3b(hull off): J2 ×1.0 7,679~8,479 s, ×1.1 9,519~9,565 s(FINAL-C4G2, P).
  - 같은 시기 G6P J2FL 9,500 s(200 s) 대비 P3b J2는 모의 1 s당 약 1.26배, ×1.1은 ×1.0의 약 1.25배.
- 행당 추정(**가정**, P, 4스레드): ×1.0 120 s 약 4,400 s, ×1.1 120 s 약 5,500 s. 4행 동시면 1.2~1.5배 느려질 수 있다. 명목값은 요청 기준 5,650 s/행이다.
- 10행(판정 8 + 변형 2): 행·초 합 약 56,500 s(명목).

| 배치 안 | 동시 수 | 벽시계(가정) |
|---|---|---|
| P만, 4행씩 | 4 | 3묶음, 약 4.7~5.9 h |
| P 4 + E 3(E 약 1.5배, 짝 세트 R1·R7·F1 / R4·R8·F2는 같은 풀 종류) | 7 | 2묶음, 약 3.3~4.4 h |
| 판정 행 8을 먼저(P 4 + E 3), 변형 2를 마지막에 | 7 → 2 | 약 3.3~4.4 h, 판정 행 결과가 먼저 나온다 |

- 구현·시험(python-expert 래퍼·판정 도구 1.5~2 h, cad-expert run_S9 인자·행 모듈 0.5~1 h), 감사·두 경로·판정서 1~1.5 h를 더한다.
- 15분 넘게 걸리므로 long-running-task-monitor 점검 주기 호출, compute-scheduler-expert 배치표·예약(`reserve.py`)이 필요하다.

## 12. 한계

- 판정 행에서 "막힘 → 취소 → 재평가" 경로는 $L_1$ dP > 0이면 관측되지 않는다(P-8). F1·F2가 그 경로를 정보용으로 보이지만, 강제 막힘 뒤 +30 mm 목표가 없어 궤적이 판정 행과 달라진다. 그래서 취소가 나지 않으면(`FORCED_NO_REVOKE`) 경로 ①을 보지 못한다.
- PATCH ②는 기지 행(S-Ch)뿐이다. 패치 키의 취소는 저장 Chrono 16행·하네스 모두 0건이다. 그래서 패치에서 경로 ①이 나타날지는 모른다.
- 대상 밖(경사, 오거 중·하단 ×1.1, J1 ×1.0 LAS-b, S1, 잡음 시드, t180)은 보지 않는다. J1 ×1.0은 옛 제어기 11행 dP +49~+51로 대신한다(제어기 차이 한계).
- 옛 제어기 `UNRECOVERABLE` 18행은 여전히 셀 수 없다. 이 판정은 채택 대상 제어기로 같은 조건을 다시 잰 것이다.
- 하네스는 ×1.1·평지 취소를 재현하지 못한다(1.3절).
