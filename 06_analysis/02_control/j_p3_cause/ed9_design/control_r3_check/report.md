# 판 9(436.9) R3 전 확인 (control-expert, 2026-11-28)

- **성격**: 판 9 설계 입력. 판정 아님, 봉인 전. 코드는 고치지 않았고 시뮬레이션도 돌리지 않았다.
- **한 일**: 잠긴 worktree `ed9-c9`(C9 `86121e8f`)·`ed9-t9`(T9 `2deb5fd7`)와 `ed9-diag`(`8e0bce46`)를 읽기만 했다. 실제 설정 생성 함수를 한 프로세스에서 불러 설정값을 확인했다. 저장된 진단 trace 재생을 기록용으로 한 번 셌다.
- **판 9 결과는 열지 않았다.** R3·R4 출력, 처리 팔 줄, 금지 자료는 보지 않았다.

## 0. 요약

| 질문 | 결론 |
|---|---|
| 1. 판 9 실행이 모두 LOC 분기인가 | **예(경우 A).** v5 하네스의 제어기 생성 경로 다섯 곳이 모두 `preset_config` → `with_10hz_d1`를 거치고, 거기서 `soil.enable=True`가 된다. 그래서 `_is_crawler_lifted_for_d1`은 LOC 분기를 탄다. 실측: 판 9 배치 7개와 봉인 키 파일 두 개의 설정 16개 모두 `loc_rule`. 위상 규칙 설정은 run_v5가 쓰지 않는 `s9_soil_closed_loop.reference_config` 하나뿐이다 |
| 1′. bases를 P9-D1-5 모집단에 넣을지 | 에피소드 192는 판정에 둔다. bases_liftoff는 따로 행을 두되 **판정 근거는 late·tail 칸만** 쓴다. k0~k2는 구조상 C-m = C0인 항등 칸이다. bases_phase는 "판 9 실행 조건 밖" 공개 기록 행으로 남긴다(빼지 않는다) |
| 1″. C-m 규칙 자체의 결함인가 | 중앙값 식은 맞다. 문제는 **전제**에 있다. C-m은 "참조 3주기와 현재 주기가 같은 하중 경로 상태"라는 전제를 두는데, 코드는 이 전제를 `is_crawler_lifted`에 맡긴다. 흙 응답을 끈 구성에서는 위상 규칙이 이 전제를 깬다. 판 9에는 해당하지 않는다. 채택(프리셋 기본 켬) 전에는 막는 관문이 필요하다(4절 안). 유효 기준을 LOC 확정으로 두면 흙 응답을 끈 구성의 구멍은 닫힌다. 남는 위험은 LOC 뒤에 감지되지 않는 크롤러 재접촉 하나이고, 기록 항목으로 둔다 |
| 2. R3c ②·③ 둘 다 두기 | **둘 다 둔다.** ②(C9)가 판정, ③(진단 커밋)은 기록이다. 다만 ③ ≡ ② 정체성 관문을 더하고, `ed9-diag`를 잠가야 한다 |
| 3. `final fault*` 판별 | 끝 위상 이름은 `fault`/`fault_reground`로 시작한다. **하지만 T9 판별이 틀렸다.** 짝 판정의 J4 문장은 `J4 fail: final ready -> fault` 꼴이라서 `startswith("final fault")`가 늘 거짓이다. 그래서 FAULT로 끝난 J4가 모두 `end_state`로 분류된다(실측 확인). 수정이 필요하다 |
| 4. census V0 기준을 rerun 줄로 | **맞다.** 두 팔이 같은 제어기여야 하기 때문이다. 조건은 넷이다: ④→⑤ 대조가 봉인 전에 닫혀야 하고, rerun 줄의 개수·키 집합을 고정해야 하고, C-D·C-G가 저장 격자(끔)를 쓰는 비대칭을 문면에 적어야 하고, **처리 팔도 C-m 켬으로 돌아야 한다** |
| **요청 밖 추가** | **C9에는 판 9 처리 팔(VBN·LSN·VBN 민감도) 배치가 없다.** `D1_MEDIAN_BATCHES`에는 V0 배치만 있다. 그래서 판 9의 G′ 처리 팔, census(C-J·C-S·C-D·C-G) 처리 줄 `_CM_ED8`을 만들 수단이 없다. R3를 C9에 묶기 전에 정해야 한다(6절) |

stats 추가 질문(같은 보고에 넣음)
- (2) bases_liftoff k0~k2의 C-m = C0는 **폴백(유효 기준 < 3) 때문이다**(코드 행, 2절).
- (3) 하네스 `t_event`는 event twin의 패드 바닥 사건 시각이다. D1″ 적용 시작보다 2.97~23.5 s 늦다. k0에서 C-m = C0인 것은 **폴백이 아니다.** 참조가 모두 유효하고 사건 전 조용한 주기라서 `med ≈ r_{j-1}`이 되는 구조적 일치다(3절).
- (4) 경우 A라서 개정은 판 9 전제가 아니다. 다만 채택 전에 넣을 안을 4절에 적었다.

## 기호

| 기호 | 뜻 | 단위 |
|---|---|---|
| $r_j$ | D1″ 잔차 $\sum F_j - M_{eff} f_{z,j}$ (주기 j) | N |
| $\mathrm{med}_j$ | $\mathrm{median}(r_{j-1}, r_{j-2}, r_{j-3})$, 세 주기가 모두 유효할 때만 정의 | N |
| $\Delta F$ | 헤드 계단 후보의 힘 $|\Delta p_h| A_p$ | N |
| $\rho$ | 설명 비 0.5 (`IMU_RESIDUAL_STEP_RATIO`, `two_pressure.py:200`) | – |
| C0 | 현 D1″: $|r_j - r_{j-1}| \ge \rho\Delta F$이면 설명 안 됨(FAULT) | – |
| C-m | C0 ∧ $|r_j - \mathrm{med}_j| \ge \rho\Delta F$ (med가 없으면 C0) | – |
| D1′ | 합 규칙 $|\sum F_j - \sum F_{j-1}| \ge \rho\Delta F$ | – |

이산 10 Hz(주기 $T$ = 0.1 s), 기록 재생, 개루프 주입이다. 되먹임 제어 루프의 부호와는 무관하다.

## 1. 질문 1 (stats 위임 1): 판 9 실행이 LOC 분기만 타는가

### 1.1 분기 코드
- `c2.py:5622-5630` `_is_crawler_lifted_for_d1`
  - `soil.enable`이 False이면 `phase in CRAWLER_LIFTED_PHASES`(`c2.py:492-501`, LEVEL부터)를 쓴다.
  - True이면 `_is_liftoff_confirmed()` ∧ ¬`is_crawler_recontact_suspected`를 쓴다.
- 결과는 `_read`가 `is_crawler_lifted=`로 넘긴다(`c2.py:5576`).
- `soil.enable=True`를 넣는 곳은 프리셋 `with_10hz_d1`의 `soil = replace(config.soil, enable=True, …)` 한 곳이다(`c2.py:2991-2997`, 결합 `3061`).
- `03_src`·`04_scripts`(ed9-c9, `*.py`)에서 `soil=replace(…, enable=False)`나 `soil=SoilResponseSettings()`를 쓰는 곳:
  - `s9_soil_closed_loop.reference_config`(`s9_soil_closed_loop.py:463-470`)
  - Chrono 쪽 `run_S8C.with_soil_off_replay`(`run_S8C.py:2679-2683`)와 `s9_merge/m3_run.py:70`
  - run_v5 경로에는 없다.
- `apply_controller_options`(`v5_options.py:803-821`)와 그 안의 `with_lock_closure`·`with_lock_start_b`·`with_probe_d6`·`with_ed8`는 `soil`을 바꾸지 않는다. c2.py에서 `soil=`이 나오는 곳은 2991·3061·3101행뿐이다.

### 1.2 v5 하네스 제어기 생성 경로(run_v5 → `verdict_runs.execute`, `run_v5.py:1016-1020`)

| 경로 | 생성 | 근거 |
|---|---|---|
| 정상 사례 | `s9_soil_slope.run_one` → `_install_patches`가 `sl.make_controller`를 `_make_project_controller`로 바꾼다 → `cl.preset_config(COMBINED)` | `verdict_runs.py:668-677`, `s9_soil_slope.py:1459-1467`, `1406-1416`, `s9_soil_closed_loop.py:523`(모듈 전역 조회) |
| 사건 사례 | `r67.make_base` → `cl.preset_config(judge)` | `verdict_runs.py:697-713`, `r67_g1_screen.py:180-191` |
| t_a 기준 | 같은 `r67.make_base` | `verdict_runs.py:888-899` |
| G8·G6·센서(r79) | `r69_g8_screen.py:121`, `r72_g6_screen.py:269-271` `preset_config`, r79 `level_config`(soil 그대로) | `r79_sensor_screen.py:300-313`, `785-790` |
| `preset_config` 자체 | `C2Config(...).with_10hz_d1()` 뒤 zero_calibration·r8만 바꾼다 | `c2py_r8d1_closed_loop.py:77-93` |

- C-m 스위치 래퍼는 같은 `with_10hz_d1`을 감싼다(`verdict_runs.py:352-385`). 그래서 C-m 켬 프로세스의 모든 프리셋은 soil 켬 + C-m 켬이다.

### 1.3 실측(`scripts\cfg_paths_check.py`)
- 방법: C9 worktree에서 `install_d1_median(True)`를 건 한 프로세스로 실행했다. 실제 함수 `preset_config`와 `apply_controller_options(options_of(s))`로 설정을 만들었다.
- 대상: 판 9 배치 7개(`ed9_heldout_v0/aa2/aa3/same_shape/census_v0` + 끔 쌍둥이 2)의 설정(전부 V0), 키 파일 `census_keys_ed8.json`(LSN1~4, VBN, VBN 민감도 10)과 `heldout_g_ed8.json`(VBN)의 설정.
- 결과: 16개 설정과 `preset_config(COMBINED/PRESSURE)` 모두 `soil.enable=true`, `imu_residual_median_check=true`, `loc_rule`이다. 태그는 V0 `final_C4G2_LAS_K1_CM`, 처리 팔 `final_C4G2_P3X_LAS_K1_LSB_CM_ED8`이다.
- `phase_rule`은 `reference_config`(패치 전 공장) 하나다. run_v5 경로에서 이것이 쓰이지 않는다는 것도 확인했다(`s9_soil_slope_patch_replaces_make_controller: true`).
- 함께 드러난 점: **C-m 켬 프로세스에서도 soil 끔 + C-m 켬 설정을 만들 수 있다.** 지금 막는 관문이 없다(4절).
- 출력: `cfg_paths_check.json`(sha256 `d4674ad0…`).

**결론: 경우 A.** 판 9 run_v5 실행 줄은 모두 LOC 분기다. 줄 기록에 `soil.enable`은 없다(`run_v5.py:1111-1115` LINE_RECORD_KEYS). 그래서 근거는 코드 경로와 위 실측이다. 등록부에 이 파일:행을 적기를 권한다.

### 1.4 P9-D1-5 모집단 의견
- **LOC 규칙에서는 크롤러 이탈 과도의 대부분이 D1″ 대상이 아니다.**
  - LOC 확정 전에는 `_imu_residual_mass_kg`가 None이다(`two_pressure.py:2176-2179`). 그래서 D1′ 합 규칙으로 판정한다.
  - C-m 참조는 LOC 확정 뒤에야 쌓인다(`_keep_d1_reference`, `two_pressure.py:2151-2167`). 그래서 C-m은 LOC + 3주기부터 동작한다.
- bases_liftoff(실제 이탈부터 유효)는 C-m에 LOC보다 일찍 기회를 준다. 그래서 LOC 규칙의 **보수 쪽 대리**다(C-m이 C0를 잃을 기회가 더 많다).
- 권고
  - 에피소드 192: 판정 행(지금처럼)
  - bases_liftoff: 따로 둔 행. late·tail 칸만 C-m 증거로 쓴다. k0~k2 칸은 "C-m = C0(폴백, 구조적), 증거 아님"으로 적는다(2절).
  - bases_phase: "판 9 실행 조건 밖(soil 끔 위상 규칙)" 공개 기록 행. 결과 때문에 빼지 않는다. 빼지 않는 근거는 위 1.1·1.3 파일:행이다.
- stats Q-1 (a)와 같은 결론이다.

### 1.5 C-m 규칙 결함 여부
- **식은 맞다.** 기전은 이렇다.
  - 위상 규칙에서는 LEVEL 초반(크롤러가 아직 하중을 받는 주기)의 잔차가 참조에 들어간다.
  - 이탈 순간에는 실제 하중 경로가 바뀌어 잔차 수준이 크게 움직인다($|r_j - \mathrm{med}_j|$가 실제 하중 변화를 담는다).
  - 그 변화가 반대 부호 주입 계단을 상쇄해 "설명됨"이 된다.
  - C0는 한 주기 차만 보므로 덜 민감하다(C0 23/23).
- 그러니 결함은 **전제의 범위**에 있다. C-m의 전제는 "j−3..j 동안 크롤러 하중 0"인데, 코드는 이를 `is_crawler_lifted` 하나에 기대고 있다.
- **유효 기준을 LOC 확정으로 두면 끝나는가**
  - soil 끔 구성의 구멍은 닫힌다. LOC가 없으므로 참조가 생기지 않고 C-m ≡ C0가 된다.
  - **남는 위험(기록)**: LOC 뒤에 감지되지 않는 크롤러 부분 재접촉. 재접촉 감시는 READY에서만, 30 kN·1 s다(`two_pressure.py:85-89`, `239`).
  - 진짜 고장을 C-m이 놓치려면 세 가지가 함께 있어야 한다.
    - 3주기 안에 반대 부호 잔차 이동 $> (1-\rho)\Delta F = 0.5\,\Delta F$
    - 최소 후보 계단 100 bar(`max_step_Pa`, `two_pressure.py:553`)
    - 후방 ø110 $A_p$ = 9.50e-3 m² 기준 $\Delta F$ ≥ 95.0 kN, 따라서 이동 ≥ 47.5 kN(전방 ø130: 66.4 kN)
  - 이것은 감지 문턱 30 kN보다 큰 재접촉이 고장과 같은 0.3 s 안에 겹쳐야 한다는 뜻이다. 실행 전 예측이 없는 기록 항목으로 둔다.

## 2. stats 위임 2: bases_liftoff k0~k2의 C-m = C0는 폴백인가

**폴백이다(코드 확인).**
- `ml_inject_cm.py:159-166` `_median_reference`는 j−1, j−2, j−3이 모두 `lifted`이고 유한할 때만 값을 낸다. 아니면 None이다.
- `flags_of`(`ml_inject_cm.py:180-185`): None이면 `cm = c0`이다.
- bases_liftoff는 `lifted &= t_s >= t_lift`(`ml_inject_cm_bands.py:131-132`)이고, 구간 k0 = [0, 0.1) s다(`ml_inject_cm_bands.py:56`, `68-74`). 10 Hz라서 각 칸이 주기 하나다.
  - k0: 이탈 뒤 참조 0개
  - k1: 1개
  - k2: 2개
  - 셋째 참조가 차는 첫 주기는 t_lift + 0.3 s, 곧 late다.
- 그래서 k0~k2의 C-m = C0는 정의상 성립하는 항등이다(stats 1.1 추정과 같다).
- 덧붙임: bases_liftoff k0의 C0도 $r_{j-1}$로 이탈 전 주기(크롤러 하중 있음)를 쓴다. 실제 LOC 규칙이면 이 주기는 D1′로 판정된다. 그래서 bases_liftoff의 k0~k2는 "LOC에서의 C0"의 대리로도 정확하지 않다. C0 = D1′ = 100 %라 결론은 바뀌지 않는다.

## 3. stats 위임 3: 하네스 `t_event`와 k0 594/594 일치

### 3.1 `t_event`
- event twin의 패드 바닥 사건 시각이다. `verdict_runs.py:731` `t_event = (target if is_absolute else plant.t + r67.PRE_S) + twin.offset_s`.
  - `target`은 기준 실행 시간표(READY·LOC·DONE)에서 정한다(`_event_time`, `715`).
  - 사건 모양은 `event_shape(twin, r67.EVENTS)`다(예: RE1bF 30 mm / 0.05 s, `run_v5.py:494`).
- 진단 trace에서 잰 "사건 − D1″ 첫 적용 주기(trace의 `is_crawler_lifted` 첫 True)"는 75 trace에서 **2.97~23.5 s**다(`harness_k0_check.json` `event_minus_d1pp_start_s`).
- 그래서 사건 시각에는 D1″가 이미 적용 중이다. 사건 앞 주기가 C-m 참조로 쓰인다는 stats 추정이 맞다.

### 3.2 k0 일치의 원인(`scripts\harness_k0_check.py`)
- 방법: `d1_rule_eval.py`의 주입 반복을 같은 필터로 다시 돌렸다. 구간은 $t - t_{event}$이고 경계 허용은 1e-6 s다.

| 칸 | 후보 | med 없음 | med 있음 | $\max |r_{j-1}-\mathrm{med}|/\rho\Delta F$ | C0 − C-m |
|---|---|---|---|---|---|
| transient k0 | 596 | 0 | 596 | **0.0001** | 0 |
| quiet k0 | 264 | 0 | 264 | 0.0001 | 0 |
| transient k1 | 496 | 0 | 496 | 0.7106 | 79 |
| transient k2 | 513 | 0 | 513 | 0.1745 | 0 |
| transient late | 10 883 | 0 | 10 883 | 0.7228 | 107 |

- **폴백이 아니다.** k0에서 참조는 모두 유효하다.
- 일치하는 이유: k0의 참조 j−1..j−3은 모두 사건 전 조용한 READY 주기라서 $\mathrm{med}_j = r_{j-1}$(차 ≤ 1e-4·문턱)이다. 두 시험이 사실상 같은 수를 비교하니 C-m = C0는 구조적 항등이다. 증거로 쓰지 않는다.
- k1에서 갈라지는 이유: j−1(사건 첫 주기)이 순간 10 Hz 압력 대 IMU 10 ms 평균의 시각 차를 담아 $r_{j-1}$이 중앙값에서 벗어난다(최대 0.71·문턱). 판 8 진단의 기전과 같다.
- 후보 수 596은 stats의 594와 2건 다르다.
  - 내 셈은 $|\text{step}| \le$ max_step 행(원 스크립트가 모두 False로 넣는 행)을 뺐다.
  - 구간 경계를 1e-6 s로 잘랐다(원 CSV의 `t_minus_event_s`는 4자리 반올림).
  - 어느 쪽이 차이를 만들었는지는 확인하지 않았다. 결론(k0 C0 − C-m = 0, med 전부 유효)에는 영향이 없다.

## 4. stats 위임 4: C-m 유효 기준 개정안
판 9는 경우 A라서 **판 9 전제는 아니다.** 프리셋 기본 켬으로 채택하기 전에, 또는 C9를 어차피 바꿀 때(6절) 함께 넣을 안이다.

1. **관문(권고, 최소)**: C-m 켬 ∧ `soil.enable` False인 설정을 거부한다.
   - 위치: `C2Config` 생성 검사 또는 `verdict_runs.d1_median_record`(`verdict_runs.py:388-406`)
   - 판 9 실행 줄에는 비트 동일이다(모두 soil 켬). 1.3에서 그 조합이 지금 만들어진다는 것을 확인했다.
2. **정의 개정(대안)**: "C-m 참조와 C-m 적용은 LOC 확정(흙 응답 켬) ∧ 재접촉 의심 없음인 주기만. 흙 응답 끔이면 C-m은 적용하지 않는다(C0)."
   - 구현: c2가 `TwoPressureMonitor`에 `is_lift_confirmed`를 따로 넘기고, `_keep_d1_reference`의 `is_valid`에 그 값을 쓴다. 판 9 실행 줄에는 비트 동일이다.
   - R2 재계산이 필요 없다. bases_liftoff가 이 정의의 보수 대리다.
   - 문면: "유효 기준 = LOC 확정 뒤 연속 3주기. LOC 해제·재접촉 의심이면 비운다. bases_phase는 이 정의에서 C-m이 적용되지 않는 구성의 기록이다."
3. 위상 규칙 구성을 그대로 지원하려면(경우 B 꼴) "실제 이탈 뒤" 판별 수단이 제어기에 없다. 위상만으로는 대신할 수 없으므로 권하지 않는다.

## 5. 질문 2: R3c ②·③

- **둘 다 둔다.**
  - **② on_plain(C9)이 판정 행이다.** 제어 2.4의 예측(9 job 사유 바뀜, 50 job 비트 동일)은 C9 코드에 대한 것이다.
  - **③ on_trace는 분기·비 기록용이다.**
- 근거: `ed9-diag`와 C9의 차이는 `two_pressure.py` 한 파일이다(+175 / −4, `git diff --stat 86121e8f 8e0bce46`). trace 켬 경로가 C-m 켬에서 명령을 바꾸지 않는다는 비트 시험은 없다(진단 커밋의 C8 비트 동일 시험은 trace 끔 기준).
- 붙일 조건
  1. **③ ≡ ② 관문(59 job)**: `commands_sha256`·`final_phase`·WARN/FAULT 이름 집합·D1 INFO 사유가 같아야 한다. 다르면 ③의 분기·비는 C9 동작의 근거가 아니다. ③만 버리고 ② 판정은 유지한다.
  2. **② ≡ R3b 겹침 5 job**(J1, J4, S1, S2, S3): 같은 C9, 같은 스위치이므로 같은 키 값이어야 한다(교차 확인).
  3. **경로 표지**: 줄의 `diag.two_pressure_file`(`r3c_run.py:70-72`)이 ②는 `ed9-c9`, ③은 `ed9-diag` 아래인지 확인한다.
  4. **`ed9-diag` 잠금**: 지금 잠기지 않은 브랜치 worktree다(`git worktree list`). `r3c_run.py`가 시작·끝 HEAD와 is_clean을 남기지만(79-87, 127, 154), 실행 전에 잠근다.
  5. ①(off_plain, C9 끔 ↔ 저장 진단 줄)도 그대로 둔다. ②의 "50개 비트 동일"은 ①이 identical일 때만 C-m 효과로 읽힌다.

## 6. 질문 3: ITEM_GROUPS의 FAULT 판별

- **끝 위상 이름**: `C2Phase.FAULT = "fault"`, `FAULT_REGROUND = "fault_reground"`(`c2.py:478-479`, StrEnum). 줄에는 `str(controller.phase)`로 들어간다(`verdict_runs.py:243`). 둘 다 `fault`로 시작한다.
- **결함**: T9의 `_group_of_item`(`jp3_ed8_judge.py:523-547`)은 `detail.lower().startswith("final fault")`로 판별한다.
  - 짝 판정의 J4 문장은 `judge_stage1_4368.j_items`(381-390) → `judge_stage1_r5.J_fails`가 만든다(`06_analysis\03_hydraulic\coupled\v5\paper_runs\scripts\judge_stage1_r5.py:126-130`). 꼴은 `f"final {base['final']} -> {on['final']}"`이다. 그래서 늘 `final ready -> …`로 시작한다.
  - 실측(`scripts\t9_item_group_check.py`, T9 함수 직접 호출)
    - `J4 fail: final ready -> fault`, `final ready -> fault_reground` → `["end_state"]`
    - `J4 fail: final fault`(시험 꼴) → `["fault"]`
  - 시험 `test_ed9_judge_tool.py:233-234`는 실제 생산자가 만들지 않는 `final fault` 꼴로 확인했다.
  - `final fault` 꼴은 V0 자기 실패(`jp3_j9main_judge.own_item_failures`, 664행)에서만 나온다.
- **영향**
  - 배타 귀속: 새 `FAULT_*` J7 항목이 함께 있으면 우선순위상 `fault`가 맞게 나온다(T9 스모크의 FAULT 3이 이 경우로 보인다. 추정).
  - 겹침 건수: FAULT로 끝난 모든 짝에서 `fault`가 빠지고 `end_state`가 늘어난다.
  - 새 FAULT_* J7 항목 없이 FAULT로 끝난 짝은 배타 귀속도 `end_state`로 틀린다.
- **수정 제안(python-expert)**: 문장 대신 후보 metric의 `final` 값으로 판별한다(`str(final).startswith("fault")`). 문장을 써야 한다면 `->` 뒤의 후보 위상을 본다.
  - 시험은 `old.J_fails`가 만든 실제 문장으로 둔다. FAULT·FAULT_REGROUND로 끝나는 경우 각각, 그리고 새 FAULT_* J7 없이 끝나는 경우를 넣는다.
  - T9 커밋이 바뀌므로 R4 전에 고친다. R3 실행 경로(C9)와는 무관하다.

## 7. 질문 4: ed9 census V0 기준을 rerun 줄로

- **맞다.** 판 9 V0 = "v5 제어기 + C-m"이다(지난 보고 1.7). 처리 팔도 C-m 켬이므로 기준 줄도 같은 C9 + C-m 켬이어야 한다.
  - 저장 main.jsonl V0(옛 실행본 `9ad74990…`, C-m 끔)를 쓰면 C-m 효과와 하네스 차이가 함께 섞인다.
  - C-J와 C-S가 같은 사전 `v0_by_job`을 쓰는 것을 확인했다(`jp3_ed8_judge.py:1266-1268`, `1285-1286`).
- 조건
  1. **④ → ⑤ 순서**와 봉인 전 확인값(stats 3.2와 같다). ④가 differs이면 멈춘다.
  2. **개수·키 집합 고정**: `rerun_v0_rows_by_job`(`jp3_ed8_judge.py:712-726`)은 오류 줄과 중복 job만 거른다. "100 job, 키 집합 = `batch_jobs('main')`의 V0 job 키, 설정 V0만"을 검사하지 않는다. 빠진 job은 C-J·C-S에서 "기준 없음"으로만 드러난다. 개수와 키 집합 대조를 구현 요구로 두기를 권한다. 태그는 `identity_defects`가 본다(1295-1296).
  3. **비대칭 명시**: 같은 census 안에서 C-D·C-G는 저장 격자 V0(C8, 끔) 해시를 분석 근거로 다시 쓴다(구현 2차 보고 7절 문면). C-J·C-S는 rerun(켬)이다. 이 비대칭과 그 근거를 규칙 문면에 함께 적는다.
  4. **처리 팔도 C9 켬**: 다음 절의 공백이 막히지 않으면 ed9 census는 처리 줄 입력이 없어 돌릴 수 없다.

## 8. 요청 밖 추가: 판 9 처리 팔 배치 공백
- C9 `D1_MEDIAN_BATCHES`(`run_v5.py:478-482`) = `ed9_heldout_v0`, `ed9_heldout_aa2`, `ed9_heldout_aa3`, `ed9_heldout_same_shape`, `ed9_census_v0`. 모두 V0다(`cfg_paths_check.json` `ed9_batch_settings`).
- census 1043줄과 G′ 처리 339줄을 만드는 배치는 `ed8_keys`(`run_v5.py:516-517`)뿐이다. 이것은 C-m 끔이고, 태그는 `_ED8`(`_CM` 없음)이다.
- T9 ed9 규칙 집합은 run commit = C9와 `_CM_ED8` 태그를 요구한다(`jp3_ed8_judge.py:257-259`, `1265`). 그래서 지금 C9로는 판 9의 census(C-J·C-S·C-D·C-G 처리 줄)와 G′ 처리 팔을 만들 수 없다.
- 지난 보고 1.3 (2)는 "판 9가 G′ 처리 팔·T8·사례를 돌리면 `ed9_keys` 등도 넣는다"였다. 구현되지 않았다.
- **R3를 C9에 묶기 전에 정해야 한다.**
  - (a) 지금 `ed9_keys`(필요하면 `ed9_t8`·`ed9_cases`)를 배치 표에 더해 C9′로 다시 고정한다. 이때 4절 관문 1도 함께 넣는다. R3는 C9′에서 돈다.
  - (b) C9로 R3를 돌리고 처리 팔은 뒤 커밋으로 돌린다. 이 경우 실행 경로 불변 시험(`test_working_tree_changes_since_c8_stay_off_the_run_path` 꼴)을 C9 → C9′에 대해 두고, T9 `run_commit`을 둘로 나누는 규칙이 필요하다.
  - 권고: **(a)**. 판정 커밋이 하나로 남는다.

## 수행한 작업
- 실행(PowerShell, `conda run -n dynamics-dev python -I -B`, `PYTHONDONTWRITEBYTECODE=1`, `NUMBA_CACHE_DIR` = scratchpad `control-ed9r3\numba`)
  - `scripts\t9_item_group_check.py <ed9-t9> t9_item_group_check.json` → ok
  - `scripts\harness_k0_check.py <ed8_design\stage5_aa_diag> <control_d1_rule\scripts> harness_k0_check.json` → ok
  - `scripts\cfg_paths_check.py --worktree <ed9-c9> --keys-dir <ed8_design\keys_seal_41e107e9> --numba-cache … --out cfg_paths_check.json` → ok. 첫 시도는 내 스크립트의 `load_params` import 오류로 종료 1이었고, 출력이 없어 다시 돌렸다.
- 산출물(폴더 `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed9_design\control_r3_check\`)

  | 파일 | sha256 |
  |---|---|
  | `cfg_paths_check.json` | d4674ad0d27f0957f52f6e2e1441d6489966d3201e40ffd25e214dfb1f0d46fa |
  | `harness_k0_check.json` | 08ee7415c6d6d1a80c56b7773e218f7fe0b2386eb08cb358e452e7458a01e4b7 |
  | `t9_item_group_check.json` | 5b61ab5e498d47aba44380a7f96076c564ba3d7ac5ba00625b3189e8cab560c0 |
  | `scripts\cfg_paths_check.py` | 5b79849ea53eea01b23a149eef73875a59b443b5962f93f82b148c558bfa9f74 |
  | `scripts\harness_k0_check.py` | 9ad278d47347fe81dda1817e5c641fbcc19a7a664cdd234c1b5eea221f657005 |
  | `scripts\t9_item_group_check.py` | 64672b61b5aad6c31e0a5c0bd9bb0a652d1b987ab1736ea135d4b65bc827fa0c |

- Julia 교차 검증은 하지 않았다. 선형 루프·리카티 계산이 없는 코드 경로 확인과 기록 재생 셈이라 대상이 없다.

## 가정
| 가정 | 값 | 근거 |
|---|---|---|
| bases_liftoff = LOC의 보수 대리 | LOC 확정은 실제 이탈보다 늦다 | 1.4 논리. LOC 시각은 ML 기록에 없다(옛 프리셋 실행) |
| 실 재접촉 위험 크기 | 이동 ≥ 0.5 ΔF ≥ 47.5 kN | ø110·100 bar·ρ 0.5. 발생률은 계산하지 않음 |
| 6절 T9 스모크 FAULT 3의 출처 | 새 FAULT_* J7 | 추정. 스모크 출력은 열지 않았다 |
| 하네스 D1″ 시작 시각 | trace 첫 `is_crawler_lifted` 행 | trace가 base 복사 실행 행을 포함할 수 있다. 가장 행이 많은 감시기 기준(`d1_rule_eval.primary`) |

## 위임 필요
- **python-expert**
  - 6절 ITEM_GROUPS FAULT 판별 수정과 실제 생산자 문장 시험(T9 재고정)
  - 8절 판 9 처리 팔 배치(`ed9_keys` 등)를 `D1_MEDIAN_BATCHES`에 넣기
  - 4절 관문 1(C-m 켬 ∧ soil 끔 거부)과 비트 동일 시험
  - 7절 census rerun V0 개수·키 집합 검사
  - 5절 ③ ≡ ② 관문과 경로 표지 대조
- **stats-design-expert**: 3.2(하네스 k0 항등)와 2절(bases_liftoff k0~k2 항등)을 P9-D1-5·P9-D1-6 행 정의에 반영. 항등 칸은 증거 아님, 후보 0은 해당 없음.
- **verif-protocol-auditor**
  - 1.1·1.2 파일:행이 등록부에 있는지
  - 8절 결정 뒤 run commit 하나로 고정되는지
  - ITEM_GROUPS 시험이 실제 문장을 쓰는지

## 공개(실제 행위)
- **Read**
  - `impl_report_2.md`, `control_cm_switch\report.md`, `stats_r3_check\report.md` 전체
  - `ml_inject_cm_bands.csv`, `ml_inject_cm_bands.provenance.json`
  - `d1_prerun\scripts\r3c_run.py`, `ml_inject_cm_bands.py`, `ml_inject_cm.py` 140-189행
  - `control_d1_rule\scripts\d1_rule_eval.py`
  - ed9-c9: `c2.py`(464-501, 2847-3106, 5540-5660), `verdict_runs.py`(120-179, 340-469, 660-738, 840-959), `run_v5.py`(1-99, 100-299, 299-333, 400-544, 930-1045), `v5_options.py` 780-850, `two_pressure.py`(78-91, 2090-2269), `s9_soil_closed_loop.py` 440-519, `s9_soil_slope.py`(1385-1484, 1628-1667), `c2py_r8d1_closed_loop.py` 1-122, `r67_g1_screen.py` 180-204, `r79_sensor_screen.py` 795-834
  - ed9-t9: `jp3_ed8_judge.py`(255-284, 520-666, 700-749, 1240-1299), `jp3_ed7_judge.py` 700-719, `jp3_j9main_judge.py` 610-689, `judge_stage1_4368.py` 360-409
  - 내 메모리 파일 1개
- **Grep**(코드 `*.py`, 경로 지정): ed9-c9 `03_src`·`04_scripts`·해당 파일, ed9-t9 `coupled`·`04_scripts`·`test_ed9_judge_tool.py`, `judge_stage1_r5.py`
- **Glob**: `ed9-c9\04_scripts\04_hydraulic`, `ed9-c9\04_scripts\03_control`(파일명 지정), ed9-t9(파일명 지정), `d1_prerun\scripts`, `stats_r3_check`
- **스크립트가 읽은 것**: 키 파일 두 개의 `lines[*].job.setting`(job 정의만), `stage5_aa_diag` 진단 trace와 진단 jsonl(job·`t_event_s`·trace 행; 콘솔에는 건수만), `judge_stage1_r5.py` 124-131행
- **Bash**: git 조회 3회(`status`·`rev-parse`·`diff --name-only/--stat`·`worktree list`·`status --ignored`). 파이프와 heredoc은 쓰지 않았다.
- **쓰기**: `control_r3_check\` 아래 스크립트 3개와 JSON 3개, 내 에이전트 메모리(`judge-classification-pitfalls.md`, `MEMORY.md` 한 줄). 잠긴 worktree의 `status --ignored`는 실행 뒤에도 비어 있었다(쓰기 0).
- **지운 것**: 내 scratchpad `control-ed9r3\`(numba 캐시 폴더) 전체
- **열지 않은 것**: `j9_runs\` 아래 전부, `d1_prerun\judge_smoke_*\`, `scan_d1_step.json`, P8-2 경로 2 자료, `stage5_aa_cause\`. 상위 폴더 검색은 하지 않았다.
- 프로세스 종료 없음, 병렬 실행 없음, 설치 없음.
- 의존성 점검: 이 세션 이전 점검(STAMP)으로 생략했다.

사용한 스킬: 없음
