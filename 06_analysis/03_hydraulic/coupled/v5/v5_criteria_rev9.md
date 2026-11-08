# v5 유압 연성 인수 기준 — 개정 9 (정정: 로드 판독 없는 실행의 J-P3 = 해당 없음)

작성: control-expert, 2026-11-08.

> **상태: 봉인(2026-11-08).** SHA-256과 봉인 시각은 같은 폴더 `v5_criteria_rev9.sha256`에 있다. 이 파일은 더 고치지 않는다.
> - **짧은 정정 판이다.** 개정 8 3.2·7.2 ④의 "`extend_bound_check`가 null이면 설정 결함"이 로드측 판독이 없는 실행(헤드 압력만 읽는 하네스 행)에는 맞지 않아서 고친다. J-P3의 식·문턱(ext_moving `sum(breach_reads)` = 0)은 바꾸지 않는다.
> - **판정 결과를 보기 전의 정정이다.** 개정 8 7.2 해시 대조(`p3_hash.jsonl`)는 아직 돌지 않았다(이 판 작성 시각에 파일 없음). 본 것은 구현 코드와 저장 r5 T4h 기록의 로드 판독 유무(4절)뿐이다.
> - 근거 보고: python-expert(3d848a7 커밋 메시지·`decision_log.md` 4절 "남은 확인").

**고치는 판**: 아래 아홉 판을 순서대로 덮어 읽은 판이다. 앞 판들과 각 `.sha256`은 고치지 않는다. 여기 적지 않은 항목은 앞 판 그대로다.

| 판 | 파일 | SHA-256(앞 16자리) |
|---|---|---|
| 봉인본 | `v5_criteria.md` | `06ed0384fb942cfd` |
| 개정 1 | `v5_criteria_rev1.md` | `cbfac2b2de571500` |
| 개정 2 | `v5_criteria_rev2.md` | `e120474b8ebd721e` |
| 개정 3 | `v5_criteria_rev3.md` | `7084da25c6129681` |
| 개정 4 | `v5_criteria_rev4.md` | `642e96f9cfd20a9c` |
| 개정 5 | `v5_criteria_rev5.md` | `945f714660cd3ec7` |
| 개정 6 | `v5_criteria_rev6.md` | `fd5117031ef460cf` |
| 개정 7 | `v5_criteria_rev7.md` | `9ccde7a5a4128317` |
| 개정 8 | `v5_criteria_rev8.md` | `c6ec89f71c1d8de4` |

규약: 개정 8과 같다(음되먹임, $T_s$ 0.1 s, $d$ = 1, 압력 bar 게이지).

## 1. 개정 번호·사유

| 항목 | 내용 |
|---|---|
| 개정 번호 | 개정 9(정정) |
| 종류 | 판정 적용 범위 정정. J-P3를 "로드 판독이 있는 VB·LS 실행"에만 적용하고, 로드 판독이 없는 실행은 `no_rod_reading`(해당 없음)으로 센다. 식·문턱·H-7 처리, 개정 7 E·B1, 개정 8의 나머지는 그대로다 |
| 사유 | ③ 추적기는 감시기가 로드측 압력을 읽는 판독에서만 돈다(2절 표 #1 근거). 로드 판독이 없는 실행에서는 ③ 상계가 만들어지지 않으므로 `extend_bound_check`가 구조적으로 null이다. 개정 8 3.2의 "추적기는 모든 다리에서 그림자로 돈다"는 로드 판독이 있는 실행에서만 맞다 |
| 결과를 본 상태 | 개정 8과 같다. 더해 저장 r5 `main/t4h` 388기록의 로드 판독 유무를 셌다(4절). 해시 대조·J-P3 결과는 보지 않았다 |

## 2. 바뀌는 항목

| # | 앞 판 위치 | 앞 판 문구 | 새 문구 |
|---|---|---|---|
| 1 | 개정 8 3.2 ext_moving 끝 문장 | 추적기는 모든 다리에서 그림자로 돌므로 대체 다리가 없는 실행도 이 항목을 시험한다 | 로드 판독이 있는 실행에서는 추적기가 모든 다리에서 그림자로 돌므로 대체 다리가 없는 실행도 이 항목을 시험한다. 로드 판독이 없는 실행은 3절 |
| 2 | 개정 8 3.2 넷째 항목 | `extend_bound_check`가 없거나 `null`인 VB·LS 실행: 설정 결함, 판정하지 않고 멈춘다 | 3절 표로 바꾼다 |
| 3 | 개정 8 7.2 기대 ④ | `extend_bound_check`가 `null`이 아니고 ext_moving `sum(breach_reads)` = 0 | 로드 판독이 있는 행: 개정 8 문구 그대로. 로드 판독이 없는 행: `extend_bound_check` = `null`이고 3.1 두 조건을 만족(J-P3 `no_rod_reading`). 22행의 기대 구분은 3.3 |
| 4 | 개정 8 7.3 기대 ④(Chrono) | ext_moving `sum(breach_reads)` = 0 | 그대로. Chrono L2b·SCM VB 실행은 헤드·로드 두 압력을 읽는 구성이라 로드 판독 없음이 허용되지 않는다(3.2 #4) |
| 5 | 개정 8 8절 판정 문구 | "J-P3 통과" | "J-P3 통과(판정 n, 해당 없음 k)"로 적는다. $k$ = `no_rod_reading_runs` |

## 3. 정의

### 3.1 로드 판독 유무

| 용어 | 정의 |
|---|---|
| 로드 판독 있음 | 제어기에 전달된 로드측 압력(`Measurements.rod_pressure_Pa`)이 실행 중 한 판독이라도 유한값이다. 하네스 T4h 기록에서는 `rod_pressure_Pa`가 하나라도 유한(전달값이 `None`이면 기록은 NaN 4개다, `verdict_runs.LoggedController._logged_readings`) |
| 헤드 전용 구성(선언) | 실행 설정이 처음부터 로드측 압력을 제어기에 주지 않는 구성이다. 지금 해당하는 것은 하네스 steady 경로(`verdict_cases`의 `SteadyTwin` 사례 R1~R11, S1~S8, `s9_soil_slope.run_one`)와 그 밖에 판독 설정이 `head`로 적힌 하네스 실행이다 |
| `no_rod_reading` | 다음 두 조건을 **모두** 만족하는 실행: (a) 로드 판독 없음, (b) 헤드 전용 구성(선언). J-P3 해당 없음이다 |

### 3.2 J-P3 판정 표 (VB·LS 실행마다)

| # | 로드 판독 | `extend_bound_check` | 처리 |
|---|---|---|---|
| 1 | 있음 | 있음 | 개정 8 3.2 그대로: ext_moving 네 다리 `sum(breach_reads)` = 0이면 통과, ≥ 1이면 H-7(멈춤) |
| 2 | 있음 | 없음·`null` | **설정 결함**(판정하지 않고 멈춤) |
| 3 | 없음, 헤드 전용 구성(선언) | `null` | **`no_rod_reading`(해당 없음)**. 실패도 통과도 아니며 수를 기록한다 |
| 4 | 없음, 선언 없음(두 압력 구성 행, Chrono L2b·SCM 전부, 하네스 사건 경로 등) | 무엇이든 | **설정 결함**(로드 센서가 빠진 구성 오류를 J-P3 해당 없음으로 숨기지 않는다) |
| 5 | 없음 | 있음 | **설정 결함**(구조상 생길 수 없는 조합, 기록·판독 경로 확인) |

- 묶음 문구: #2·#4·#5가 하나라도 있으면 그 묶음의 J-P3는 판정하지 않는다. 없으면 #1만으로 통과/H-7을 정하고 #3의 수를 함께 적는다.
- `no_rod_reading` 실행에서도 개정 8 3.1의 제어기 설정(`final_C4G2_P3`, ③ meta)은 확인한다(7.2 ⑤ 그대로).

### 3.3 개정 8 7.2 해시 대조 22행의 기대 구분

| 구분 | 행(개정 8 7.2 표 #) | 기대 ④ |
|---|---|---|
| 로드 판독 없음, steady 경로 | R1~R11(#1~#11), S1, S2, S3, S4, S5, S7, S8(#16~#22) — **18행** | `extend_bound_check` = `null`, T4h `rod_pressure_Pa` 전부 NaN → `no_rod_reading` |
| 로드 판독 있음, 사건 경로 | R12, R14, R15, R16(#12~#15) — **4행** | `extend_bound_check` 있음, ext_moving `sum(breach_reads)` = 0 |

- 이 구분과 다르면(예: steady 행에 로드 판독이 생김, 사건 행이 null) **설정 결함**으로 멈춘다. 22행 모두 ①②③⑤는 개정 8 그대로다.

## 4. 근거

### 4.1 구조(코드, 3d848a7)

| # | 위치 | 내용 |
|---|---|---|
| 1 | `03_src/outrigger_sim/control/two_pressure.py` 1509~1515행 | `rod_pressure_Pa is None`(또는 `LoadEstimate.HEAD_ONLY`)이면 헤드 힘만으로 돌아가고 반환한다. 대체 상한 갱신 `_update_rod_estimates`(1532행)와 그 안의 ③ `_advance_extend_bound`(2277행)에 닿지 않는다 |
| 2 | 같은 파일 2325~2331행 | 추적기가 없으면 `extend_bound_Pa()` = `None` |
| 3 | `03_src/outrigger_sim/runner.py` 278~291행 | 상계가 `None`이면 플랜트 비교 `check_extend_bound`를 부르지 않는다 → 기록이 만들어지지 않는다(`l2b_actuator.py` 513·660행, 하네스 `harness_hydraulics.py` 269행 같은 규약) |
| 4 | 결과 | 로드 판독이 없는 실행에서는 ③가 힘 하한·명령에 들어갈 경로가 없다. 그래서 그 실행의 T8(명령 비트 동일)은 구조적으로 성립하고, J-P3가 시험할 상계 주장도 없다. 해당 없음은 J-P3의 취지(③ 상계가 하한에 들어갈 수 있는 곳에서 그 상계가 진값 위에 있는가)와 맞다 |

### 4.2 저장 기록(두 독립 근거의 일치)

| 근거 | 값 |
|---|---|
| 저장 r5 `06_analysis/03_hydraulic/coupled/v5/main/t4h/*.npz` 388기록의 `rod_pressure_Pa` 유한값 수(numpy 계산) | 0인 기록 188(R1~R11, R2ra, S1~S8 전부), 유한값 있는 기록 200(R12 160, R14 10, R15 10, R16 20) |
| `verdict_cases.CASES`의 경로 구분(코드 읽기) | R1~R11·S1~S8 = `SteadyTwin`(R2ra는 R2의 REANCHOR 켬 묶음 이름, 같은 steady 경로), R12·R14~R16 = `EventTwin` |
| 일치 | 사례 23종 모두 "steady ↔ 로드 판독 없음", "사건 ↔ 로드 판독 있음"이 같다 |

계산: `conda run -n dynamics-dev python -I scan_rod.py <main/t4h> <out>`(control-expert scratchpad, 2026-11-08). 로드 판독 유무만 셌다. J-P3·해시는 보지 않았다.

### 4.3 적용 범위가 줄어드는 몫

- J-P3가 실제로 시험하는 실행은 로드 판독이 있는 실행이다: 하네스 사건 경로(1단계 R12·R14~R16 계열, 2단계 격자·잡음, Dg-3 135키), Chrono L2b·SCM VB 전부. 개정 8 7.1의 2단계 대체 135키 J-P3 통과(ext_moving 0)는 이 범위 안이라 그대로다.
- 헤드 전용 구성의 신장 이동 중 하한 낙관은 ③ 문제가 아니다(로드 추정이 하한에 들어가지 않는다). 이 판은 다루지 않는다.

## 5. 도구 대응 (3d848a7 기준, 읽기 확인)

| 도구 | 지금 처리 | 이 판과의 관계 |
|---|---|---|
| `extend_start_bound.j_p3_judgement(records, has_rod_reading)` | 기록 없음 + 로드 판독 없음 → `no_rod_reading_runs`, 기록 없음 + 로드 판독 있음 → `setting_defect` | 3.2 #1·#2·#3과 같다. #4(선언 확인)·#5(로드 없음 + 기록 있음)는 없다 → 위임 |
| `p3_hash_check.py` | `has_rod` False면 `no_rod_reading`, 그 밖 null은 `missing_record`; ④ 통과 = `pass` 또는 `no_rod_reading` | 3.3 행별 기대 구분 확인이 없다 → 위임. 위임 전에도 7.2 판정은 출력의 `rows[].j_p3`를 3.3 표와 손으로 대조해 낼 수 있다 |
| `chrono_t45_replay.j_p3_of` | `has_rod_reading` 없이 부름(모두 로드 있음으로 봄) → null = 설정 결함 | 3.2 #4와 같다(Chrono는 해당 없음 불가) |
| `t4h_replay` | `run_extend_start_rule` = `tracked_bound`인 행만 J-P3에 넣는다 | VB·LS인데 ③ meta가 빠진 행이 J-P3에서 조용히 빠질 수 있다 → 위임(설정 결함으로 세기) |

## 6. 가정

| 가정 | 값 | 근거 |
|---|---|---|
| 헤드 전용 구성 선언 | 하네스 steady 경로 + 판독 설정 `head` | 4.2 일치. 새 하네스 묶음(D-1 등)은 선언을 meta에 적는다(위임) |
