# 경로 2 넘김: J-P3 rev 5 판정 정의(덧붙임 4a-7 1절·4절 발췌, 2026-11-21)

- 원문: `jp3_remedy_spec_addendum_4a7.md`의 1절과 4절을 바이트 그대로 옮겼다. 다른 절(경로 1 도구 이름이 있음)은 넣지 않았다.
- 함께 쓰는 규칙: `jp3_remedy_spec.md` 판 4a 6절·13.2·13.4·13.6, 덧붙임 4a-5 3.3·5.1.

## 1. 4a-5 2절 표 정정: 헤드 전용 선언 잡

### 1.1 잡의 구분
- T-JR-10·T-JR-11의 22잡(개정 8 7.2 규칙)은 하네스 경로로 둘로 나뉜다(개정 9 3.1·3.3).
  - **헤드 전용 선언 잡** 18개: R1~R11, S1~S5, S7, S8. steady 경로다.
  - **이벤트 경로 잡** 4개: R12, R14, R15, R16. 두 압력을 읽는다.
- 판별 근거는 줄의 헤드 전용 선언이고, 이 순서로 정한다.
  1. T4h meta `head_only_declared`
  2. 줄의 `head_only_declared`
  3. 둘 다 없으면 그 사례의 하네스 경로가 steady인지. 사례와 경로의 대응은 개정 9 3.1·3.3절이다: R1~R11·S1~S5·S7·S8 = steady(헤드 전용), R12·R14·R15·R16 = 이벤트 경로.
- 설정마다 선언 잡 18개, 이벤트 잡 4개여야 한다. 아니면 그 시험(VBH 줄이면 T-JR-10, VBJ·VBJ0 줄이면 T-JR-11)은 판정 불가다.

### 1.2 줄 규칙(4a-5 2절 표를 대신함)

| 줄 | 헤드 전용 선언 잡(18) | 이벤트 경로 잡(4) |
|---|---|---|
| VBH | ③ record 없음(`extend_bound_check` 없음 또는 null), ① = 0, ② = 0. 13.6절 정체성 검사 없음 | rev 5 record와 13.6절 정체성(`spec_edition` `8be9de22`, `carry_end_rule` `inherit_when_gate_shut`, `retract_start_rule` `with_tracker`). ① = 0이고 ② > 0 |
| VBJ | ③ record 없음, ① = 0, ② = 0. 정체성 검사 없음 | rev 5 record와 13.6절 정체성. ① = ② > 0 |
| VBJ0 | ③ record 없음, ① = 0, ② = 0 | ③ 꺼짐이라 정체성 해당 없음. ① = ② > 0 |
| VB(4a-3 5.3 기록) | 4a-5 2절 그대로(① = 0, 기록). 아래 결함 규칙도 같게 적용하고, 어기면 4a-4 4절대로 T-JR-10 판정 불가 사유에 더한다 | 같음 |

- 13.6절 정체성 검사는 **rev 5 record가 있는 줄에만** 건다.
- 다음은 `setting_defect`다(그 줄이 속한 시험을 판정 불가로 만든다). 개정 9 3.2절 표가 정한 원칙과 같다. 판독이 없는 줄은 헤드 전용으로 선언돼야 하고, 선언된 줄에는 record·판독이 없어야 하며, record가 있는 줄에는 판독이 있어야 한다.
  - 선언 없는(이벤트 경로) 줄에서 ② = 0(제어기가 로드 판독을 받지 못함)이거나 ③ record가 없다.
  - 선언된 줄에 ③ record가 있거나 ① > 0이거나 ② > 0이다.
  - rev 5 record가 있는 VBH·VBJ 줄이 13.6절 정체성과 다르다.
- 명령 해시 판정(T-JR-10 A·B·기록 일치, T-JR-11 64자 해시 같음)은 선언 여부와 관계없이 22잡 모두에 적용한다(4a-3 3절, 4a-5 2절 그대로).

## 4. 경로 2(J-P3 rev 5 판정)가 쓸 정의 문장

이 절은 경로 2 작성자에게 넘기는 정의다. 규칙 용어(키·열·설정 이름)만 쓰고, 구현 위치는 쓰지 않는다. 앞 절(1·2절)과 겹치면 이 절의 문장이 같은 뜻이다.

### 4.1 per-read 코드표(질문 1)
- T4h npz는 코드표를 함께 기록한다: `jp3_class_names`, `jp3_plant_state_names`, `jp3_source_names`. **기록된 표가 기준이다.** 코드는 그 표의 0부터 센 위치이고, −1은 "분류 없음"이다.
- 판 4a 코드의 표는 다음과 같다. 기록된 표가 이와 다르거나 없으면 그 파일은 판정 불가(`record_defect`)다.
  - `jp3_class_names` = (`lock`, `hold`, `carry_ext`, `carry_ret`, `ext`, `ret`)
  - `jp3_plant_state_names` = (`moving_ext`, `moving_ret`, `locked_ext`, `locked_ret`)
  - `jp3_source_names`의 첫 네 이름은 (`extend_bound`, `pilot_model`, `previous_moving`, `retract_hold`)이고, `retract_tracker`가 끝에 있다. 이름으로 찾고 번호를 고정하지 않는다.

### 4.2 판정 비교값(질문 2)
- 세 판정 모두 읽기별 비교값은 `jp3_used_bound_Pa`(모니터가 그 읽기에 쓴 추정)이고, 플랜트 참값은 `jp3_p_tr_Pa`다.
  - J-P3a: `ext`·`carry_ext` 읽기. 비교값 = $\hat p+\delta_m$
  - J-P3b: `lock`·`hold` 읽기. 비교값 = ④
  - J-P3c 갇힌 몫: `carry_ret` 읽기. 비교값 = $\max(\hat p+\delta_m,\ 수축\ 이동\ 모델)$
- `carry_ret` 읽기에서 `jp3_used_bound_Pa` ≥ `jp3_ext_bound_Pa` − 1 Pa여야 한다(정의상 최댓값이다). 어기면 `record_defect`(판정 불가)다. 경로 2의 해석이 맞다.
- 갇힌 몫과 채움 몫의 경계는 `jp3_p_star_ret_Pa`(플랜트 마지막 스텝 목표 $p^*_{last}$)와 `jp3_plant_state`로 정한다(6.2절, 판 3).

### 4.3 센서 등급(질문 3)
- 행의 등급은 다음 순서로 정한다.
  1. rev 5 record의 `sensor_grade` 값(`ideal`, `normal`, `conservative`, `old_worst`)
  2. 그것이 없으면 잡음 실행 결과 줄의 `level`: L0·L1 = ideal, L2·L2nocal·L2imuideal = normal, L3 = conservative, L4 = old_worst
  3. 둘 다 없고 하네스 배치 줄(`job` 필드가 있고 `level`이 없는 jsonl 줄)이면 ideal이다. 6.1절의 "이상 센서 경로로 선언된 경우"가 이것이다. **경로 2의 해석(그런 줄을 모두 ideal로 봄)이 맞다.**
- `sensor_grade`와 `level`이 둘 다 있는데 등급이 다르거나, 어느 규칙에도 맞지 않으면 `setting_defect`다.

### 4.4 분류 일관성과 NaN(질문 4)
- 판정 집합은 기록 분류(`jp3_class`)로 정한다(6.2절).
- 기록 분류는 작용 명령 $u$ = `jp3_u_m_s`와 2.1절 표에 맞아야 한다. $u_{hold}=0.01\,v_{max}$ = 2.0924×10⁻⁴ m/s이고, 경계 비교 허용은 ±10⁻¹² m/s다.

| 작용 명령 | 허용 분류 |
|---|---|
| $u$ = 0 | `lock` |
| $0<\lvert u\rvert\le u_{hold}$ | `hold` |
| $\lvert u\rvert>u_{hold}$, $u>0$ | `carry_ext` 또는 `ext` |
| $\lvert u\rvert>u_{hold}$, $u<0$ | `carry_ret` 또는 `ret` |

- 이 표 밖이면 `record_defect`(판정 불가)다.
- 판정 집합 읽기(위 4.2절의 판정 대상)에서 비교값이나 참값이 NaN이면 `record_defect`(판정 불가)다. 판정 밖 읽기의 NaN은 기록이다. **경로 2의 처리가 맞다.**

### 4.5 헤드 전용 선언 줄(질문 5)
- 헤드 전용 선언 줄(1.1절 판별)은 로드 판독이 없으므로 J-P3 판정 행이 아니다(개정 9 3.2절 "로드 판독 없음, 선언됨").
- 판정 불가도 결함도 아니다. 판정 행 수에 넣지 않고 따로 센다(`no_rod_reading_runs`).
- 결함은 1.2절과 같다. 선언된 줄에 rev 5 record나 로드 판독이 있거나, 선언 없는 줄에 판독이나 record가 없으면 `setting_defect`다.
- 경로 2가 "판정 행에 선언이 있으면 결함"으로 둔 것은 이 문장으로 바꾼다. 판정 행은 선언 없는 줄 가운데서만 고른다.

### 4.6 재잠김 1 bar 초과(질문 6)
- 정의: 플랜트가 잠길 때마다, 잠근 직후 참값($p_{r0}-G_{r,lock}/A_{ann}$)에서 잠그기 직전 이동 추적값을 뺀 계단을 잰다. 이 값은 per-lock 기록 열 `dp_tr_step_Pa`다. 그 절댓값이 1 bar(10⁵ Pa)를 넘는 잠금의 수가 `relock_step_over_1bar_count`다.
- P1 수축 시드의 계단(`p1_retract_seed_*`)은 잠금 계단이 아니라 세지 않는다.
- 판정(P4-3a, T-JR-15): VBJ·LSJ1~4 행에서 1 이상이면 **실패**다. 키가 없거나 정수가 아니면 판정 불가다. VBH·LSH 행은 기록이다.

### 4.7 기록 표지와 판정 행 차이(질문 7)
- 경로 2는 판정 행을 자기 정의(6.1절, 이 절 4.3·4.5)로 정한다. 기록된 `jp3_judged_row`는 비교 기록이다.
- 둘이 다른 행은 보고에 목록으로 남긴다. **판정 불가나 결함이 아니다.** 두 경로 대조 단계에서 판정 행 집합이 다르면 두 경로 불일치로 다룬다.

### 4.8 잡음 실행 결과 파일과 T4h(질문 8)
- 결과 파일은 JSON이고 `meta`와 `results`(줄 목록)를 가진다. 줄의 판정 필드는 다음과 같다.
  - `key`: 앞에 `cand=…#` 접두가 붙을 수 있다. 짝·키 비교는 접두를 뗀 키로 한다.
  - `level`, `v5_setting`
  - `hydraulics_record.extend_bound_check`가 기준 record다. 같은 이름의 최상위 `extend_bound_check`가 있으면 기준 record와 같아야 하고, 다르면 `record_defect`다.
  - `t4h_file`
  - `error`가 있으면 결과 없는 줄이다.
- T4h 파일 이름: 줄의 `t4h_file` 값의 파일 이름 부분이다. 그것은 접두를 포함한 `key`에서 `[^A-Za-z0-9._-]`를 `_`로 바꾸고 `.npz`를 붙인 것과 같아야 한다. 다르면 `record_defect`다.
- T4h 폴더: 그 실행의 명령 파일이 지정한 폴더다(실행 출력 폴더 규칙 4a-5 5.2절, 묶음마다 `<설정>_t4h/`). 경로 2 도구는 폴더를 입력 인자로 받고, 줄마다 파일이 있는지 확인한다. 없으면 판정 불가다.
- 하네스 배치(jsonl) 줄도 같다. T4h 폴더는 결과 파일 이름 줄기 + `_t4h/`다.

### 4.9 시험 전용 설정(질문 9)
- `*_X11`, `VBG4`, `VBG5` 설정의 줄이 J-P3 rev 5 판정 입력에 하나라도 들어 있으면, 판정 집합 밖이어도 **그 묶음 전체가 `setting_defect`**다(13.6절, 판 4a R6).
- 시험 전용 실행은 별도 폴더로만 다루고 판정 입력에 넣지 않는다.

### 4.10 오류 줄과 상태 우선순위(질문 10)
- 판정 설정(VBJ·LSJ1~4) 줄에 `error`가 있으면 그 줄은 결과가 없으므로 판정 불가다(`run_error`). 결과 없는 짝도 같다.
- 상태는 한 묶음에 하나이고, 우선순위는 `setting_defect` > `run_error` > `record_defect` > `judged_key_missing` > `no_judged_runs` > `H-7` > `pass`다.
  - `run_error`·`record_defect`·`judged_key_missing`·`no_judged_runs`는 모두 판정 불가(종료 2) 부류다.
- 두 경로 대조는 부류(결함·판정 불가·실패·통과)로 맞추고, 사유 이름은 보고에 함께 적는다.

### 4.11 J-P3b 허용폭의 $A_{ann}$(질문 11)
- $A_{ann}$은 파라미터 YAML의 다리별 `legs.<leg>.cylinder.annulus_area_m2` 정확값이다. 기호표의 4자리 값이 아니다.
  - 전방(FL·FR): 0.00376991118 m²(ø130/ø110)
  - 후방(RL·RR): 0.00314159265 m²(ø110/ø90)
- 허용폭은 0.6 kN/$A_{ann}$이다. 전방 1.591549 bar, 후방 1.909859 bar.
- 경계 비교: $p_{tr}$ − ④ > 허용폭을 초과로 센다(같으면 초과 아님). 허용폭과의 차가 10⁻⁹ bar 안인 읽기는 경계 근접으로 기록한다.

