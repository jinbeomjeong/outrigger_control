# J-P3 보완 명세 판 4a 덧붙임 4a-3 (2026-11-20, control-expert 문안)

- 대상: `jp3_remedy_spec.md` 판 4a(sha256 `8be9de229394882b…`, 커밋 `f67745f`). 봉인 본문, 덧붙임 4a-1(`143a0ef`), 덧붙임 4a-2(sha256 `2f3e36bdc2bf5ff76e2cdfe3ddfe41e23dbdd94b8fb9ea50b4bb532ffecf9b92`)는 고치지 않는다. 셋과 함께 읽는다.
- 근거: 보완 구현 `3b949f5`의 재검토 `jp3_impl_rereview_4a2.md`(차단 C1~C5, 권고 R-a~R-g)와 같은 파일 9절의 사용자 결정(2026-11-20, 질문 1~4 모두 권고안대로).
- 시점: 보완 구현 단위 시험 뒤, 사례 재생 A~F·T-JR-10~15 실행 전. 이 덧붙임을 쓸 때 사례 재생·T8·Dg-3 재실행 출력은 없다. 작성자가 연 자료:
  - 명세·덧붙임·재검토 원문, worktree `3b949f5`의 코드
  - 근거 폴더 `j4a_remedy_3b949f5/records_full`(단위 시험 기록)
  - 저장 기준 파일의 키 이름·READY 키·해시: `resume_k1/h10_reuse_rerun.jsonl`, `h6_dg3_v4on.json`, `h9_grid/grid_r67_top.json` results[13]
  - 봉인 기준선 `baseline_221456d`의 기록 키 이름(값은 열지 않음)
- 우선: 판 4a 본문·4a-1·4a-2와 이 덧붙임이 다르면 **이 덧붙임이 우선**하고, 차이를 판정서에 적는다.
- 구분: 1절은 단위 시험 기록값을 본 뒤 쓴 **사후 정정**이다. 2~5절은 해당 실행 결과 전에 고정하는 **판정 정의**다.

## 1. P4-7 측정량 정정과 4a-2 1.1 공개 문장 교체(사후, 질문 4)

### 1.1 P4-7 측정량

- 봉인 T-JR-04 ⑪b-P1 문장의 "첫 HOLD 읽기 초과 $p_{tr}-④$ = +27.4 bar"는 **명세 작성자(control-expert)의 표기 오류**다. 참조값 +27.4 bar의 출처는 유압 검토 11.1절 표이고, 그 지표는 "초과 $=p_{tr}-(13+p_h/3)$, $p_h$ = 참 헤드"다. 판독 헤드로 만든 ④와의 차가 아니다.
- **P4-7의 회귀 대조 양**은 그래서 q1 지표로 정한다: `model_only` 첫 HOLD 읽기에서 $p_{tr}-(13\ \text{bar}+p_{h,true}/3)$, $N$ = 14, 두 띠(0·4 kN) 가운데 큰 값, 기대 +27.4 ± 0.5 bar(시험 `_first_excess_bar`, `test_jp3_rev5_property.py:675-679`).
- $p_{tr}-④$는 기록이다.
- 이 정의는 단위 시험 기록값을 본 뒤 정한 해석이다. 판정서에 그 사실을 적는다.
- 기록값(`j4a_remedy_3b949f5/records_full/P4-7.json`, 두 띠 같은 값):

| $N$ | q1 지표 초과 [bar] | $p_{tr}-④$ [bar] | R5-7 최소 여유 [bar] | 판정 |
|---|---|---|---|---|
| 14(q1 모형) | +27.204 | +28.468 | +50.817 | 회귀 대조: 27.4 ± 0.5 안 |
| 12(모니터 관문) | +29.194 | +30.444 | +48.620 | 기록 |

- R5-7 여유 ≥ +4.30 bar는 $N$ = 12·14 두 띠 모두 판정한다(4a-2 6절 그대로).

### 1.2 4a-2 1.1 공개 문장의 교체본(판정서에 둘 문장)

판정서에는 4a-2 1.1의 인용문 대신 아래 문장을 둔다. 4a-2 1.1 둘째 글머리의 지시("시험 출력의 값으로 바꿔 적는다")를 적용한 문장이다. 수치는 모두 `3b949f5` 단위 시험 기록 시험의 값이다(근거 폴더 `06_analysis/02_control/j_p3_cause/j4a_remedy_3b949f5/`, 그 폴더의 `SHA256SUMS`).

> "436.9 판 4a 재구현(`ad5024b`)의 단위 시험에서 결과 전 고정 예측 P4-6(T-JR-04 사례 ⑪b 기대값 표)·P4-7(사례 ⑪b-P1의 `model_only` 첫 HOLD 초과 +27.4 ± 0.5 bar)과 시험 기준 T-JR-05 (k) 둘째 문장이 구현 경로의 값과 맞지 않았다. P4-6·P4-7의 '어기면' 칸(멈추고 원인을 본다)에 해당한다. 구현자는 멈추지 않고 이 차이를 시험 코드에 남겼다(strict xfail, $N$ 변경, 반대 assert). control-expert 구현 검토(J4a)가 이를 멈춤 조건 해당으로 판정했고, 사용자가 2026-11-20 공개 후 진행을 결정했다. 그 사이 사례 재생은 돌리지 않았다. 보완 구현 `3b949f5`에서 이 차이는 xfail 없이 기록 시험으로 남겼다.
> 세 항목 모두 원인은 명세 작성자(control-expert)의 예측 전제이고, 제어기 코드 결함이 아니다.
> (a) P4-6 기대값(`cr09`)은 RET 명령 시간 동안만 P3 (c)를 상수 속도로 적분했다. 밸브 1차 지연(τ_v 0.1 s)의 시작과 명령 뒤 꼬리, 관문 열림 시점, 읽기 시각을 넣지 않았다. 그래서 1 mm/s 두 행의 HOLD 시작 $p_{tr}$은 표(55.35·50.95 bar)보다 낮은 48.50·44.33 bar였다(−6.85·−6.62 bar). 또 0.3 mm/s에서도 관문이 열린다고 가정했으나, 네 행 모두 관문이 20 s 안에 열리지 않았다. 그래서 플랜트는 풀리지 않았고, 모든 읽기에서 사용 상계 − $p_{tr}$의 최솟값은 +11.0 bar(네 행 같은 값)라 ⑪b 노출이 없다.
> (b) P4-7의 참조값 +27.4 bar는 관문 헤드를 시작 헤드 − 4.62 bar + $e_h$로 고정한 유압 검토 모형(`hr11/q1_trapped_after_ret.py`, $N$ = 14)의 값이다. 모니터 관문은 플랜트 해제(242 ms) 뒤 내려가는 헤드 판독을 따라가 q1보다 두 주기 일찍 열린다($N$ = 12, 두 띠 모두). 초과는 q1 지표로 $N$ = 14에서 +27.204 bar, $N$ = 12에서 +29.194 bar다. 또 봉인 시험 문장은 이 초과를 '$p_{tr}-④$'로 적었으나, 참조값의 지표는 참 헤드 기준 수축 모델 대비 초과다. 이것도 명세 작성자의 표기 오류다. 판독 헤드로 만든 ④와의 차($N$ = 14에서 +28.468 bar, $N$ = 12에서 +30.444 bar)는 기록으로 둔다. 회귀 대조의 양을 q1 지표로 정한 것은 값을 본 뒤의 해석이다.
> (c) T-JR-05 (k) 둘째 문장과 2.10절 비용 문장은, 추적기가 수축 주기(RET·CARRY_ret)마다 $\hat p\leftarrow\max\big(\hat p,\ \max(p_{ret},\ 13+p_h/3)\big)$를 한다는 점을 빠뜨렸다. 그래서 같은 헤드에서 '$\hat p+\delta_m\le$ 바닥'은 일어나지 않고, R5-7은 수축 뒤 모든 구간의 창 후보를 올린다.
> 상계 쪽 변화라 건전성 판정 기준은 그대로다. 보완 뒤 단위 시험에서 다음을 확인했다.
> - R5-7 아래 HOLD 읽기 위반은 0이다.
> - P4-6 1 mm/s 두 행의 R5-7 간격은 43.46·47.63 bar로 표의 하한 간격 5.05·9.45 bar 이상이다. 첫 읽기 출처는 `retract_tracker`다.
> - `model_only` 간격은 −23.71·−20.008 bar로 기준 −20 bar 이하다. 둘째 행은 기준과 0.008 bar 차다.
> - P4-7의 R5-7 여유는 +48.62·+50.82 bar다($N$ = 12·14, 두 띠 같음).
> 늘어난 과보수는 T-JR-12 기록 열로 잰다. 예측은 판 4·4.1 원문(판 4a sha `8be9de22…`) 그대로 두며 고치지 않는다. **판정서에서 P4-6은 '적중'으로 쓰지 않는다.**"

- 4a-2 1.1의 "약 0.13 s"는 기록 시험에 없는 값이다(J4a 검토가 시험 docstring에서 읽은 값). 위처럼 기록값 "두 주기 일찍($N$ = 12 대 14)"으로 바꾼다.
- `model_only` −20.008 bar는 기준과 0.008 bar 차인 경계 근접 통과다. 시험 상수 훅의 건전성 확인 값이라 기준은 바꾸지 않고, 판정서에 정확한 값을 적는다.

## 2. T-JR-10·T-JR-11의 표본(결과 전, 질문 1)

- 봉인 5.5절의 "T-P3-5 표본 20행"은 목록이 저장소에 없다. 개정 8 7.2절(`v5_criteria_rev8.md:125`)이 같은 이유로 이 20행을 22행 규칙으로 바꾼 선례를 따른다.
- **정의**: T-JR-10·T-JR-11의 표본은 개정 8 7.2절의 22행 규칙이다. 저장 `v5/main.jsonl`의 `job.setting` = VB 행 가운데 사례마다 파일 순서상 첫 행이고, `run_v5.p3_hash_jobs`로 정한다. 22행은 22사례를 모두 덮는다.
  - T-JR-10: VBH 대 저장 VB, 명령 해시 **22/22**와 3절 meta 조항.
  - T-JR-11: VBJ 대 VBJ0, 명령 해시 **22/22**.
- 봉인 문구 "20/20"은 판정하지 않는다. 판정서에 "표본 목록 부재로 개정 8 7.2절 선례대로 22행 규칙으로 바꿈(사용자 결정 2026-11-20, 결과 전)"을 적는다.
- 판정 도구는 20행 목록 없이 22행으로 판정한다(지금의 "목록 없음 = 판정 불가"를 없앤다). 정확히 22짝이 아니거나 결과 없는 짝이 있으면 판정 불가다.

## 3. T-JR-10 meta 조항(결과 전, 질문 3)

### 3.1 비교 범위와 판정

봉인 5.5절 T-JR-10의 "meta 차이는 끝 상태값만(개정 10 조건 A·B·C)"을 하네스에서 다음과 같이 판정한다. 하네스 비교 범위는 개정 8 7.2절 선례대로 줄의 `hydraulics_record`, `commands_sha256`, `event_names`, `events`다(개정 10 3절 끝 "하네스 7.2는 `hydraulics_record`만 비교").

| 조건 | 판정/기록 | 정의 |
|---|---|---|
| A | 판정 | 22짝의 저장 줄과 새 줄 모두 `event_names`·`events`에 `WARN_ROD_PRESSURE_FALLBACK`이 0건이다 |
| B | 판정 | 짝마다 `commands_sha256`(64자), `event_names`, `events`가 같다 |
| 기록 일치 | 판정 | 짝마다 `hydraulics_record`가 같다. 단 3.2절 표의 경로는 뺀다. 그 밖의 경로가 하나라도 다르면 T-JR-10 실패다 |
| C | 기록 | T4h meta에 다리별 `fallback_rod_estimate_Pa`가 저장·새 쪽 모두 있으면 새 − 저장 [Pa]과 "≥ −1 Pa 여부"를 기록한다. 없으면 "기록 없음"으로 적는다(판정 불가 아님). rev 5 대 rev 4에서 단조성이 증명되지 않았으므로 판정에 쓰지 않는다 |

- 저장 VB = `06_analysis/03_hydraulic/coupled/v5/resume_k1/h10_reuse_rerun.jsonl`이다(identity git.head `b9f5707`, `is_clean` true). 명세 5.3절 A 행·T-JR-01과 같은 용례다. 도구는 짝마다 다음 두 가지를 assert하고, 어기면 판정 불가다.
  - 저장 줄의 `controller_tag` = `final_C4G2_P3_LAS_K1`
  - T4h meta의 ③ revision = 4(`two_pressure_settings.extend_start_bound.revision`)

### 3.2 허용 경로 목록(`hydraulics_record`, `3b949f5` 코드에서 확인)

| 종류 | 키(경로) | 출처 | 규칙 |
|---|---|---|---|
| ③ 키(개정 8 7.2 선례) | `extend_bound_check`, `tension_truth` | `p3_hash_check.py:43` `P3_RECORD_KEYS` | 비교에서 뺀다 |
| 문구만 | `m2_law.rule` | `p3_hash_check.py:45` `TEXT_ONLY_PATHS` | 비교에서 뺀다 |
| 436.9 per-lock 기록 | `lock_log`, `lock_log_columns`, `relock_count`, `relock_step_over_1bar_count`, `max_abs_dp_tr_step_bar`, `p1_retract_seed_count`, `p1_retract_seed_step_max_bar`, `p1_retract_seed_log`, `p1_retract_seed_log_columns` | `_LockLog.record()`(`harness_hydraulics.py:375-389`). rev 5(`extend_start_hold`)면 만들어진다(`_records_jp3`, `:431-435`, `:480`) | **저장 줄에 없고 새 줄에만 있을 때만** 뺀다 |
| 436.9 B2 증거 | `rod_reading_truth_calls`, `two_pressure_reads` | `plant_record`(`harness_hydraulics.py:862-863`), 무장한 v5 플랜트 전부 | 같음(저장 줄에 없을 때만 뺀다). 값은 4a-2 B2 규칙으로 따로 본다(VBH는 ① = 0) |

- 대조 근거(키 이름만 비교했다)
  - 저장 h10 VB 줄의 `hydraulics_record` 키 16개 가운데 위 표에 없는 키(`ext_lock_*` 7개, `lock_events`, `m2_*` 6개)는 판정 비교 대상이다.
  - 봉인 기준선 `221456d`의 VBH 행에 더해진 키는 per-lock 기록 7개였다. `ad5024b`에서 `p1_retract_seed_log`·`p1_retract_seed_log_columns`가, `3b949f5`에서 증거 2키가 더해졌다.
  - `lock_log_columns`·`p1_retract_seed_log_columns`의 열 구성은 코드 상수 `LOCK_LOG_COLUMNS`·`SEED_LOG_COLUMNS`다.
- 다음은 VBH에 생기지 않아야 하므로 허용 목록에 넣지 않는다. 생기면 기록 차이로 실패다.
  - `line_fill_gate`, `p1_output_exceptions`(P1 전용)
  - `check_delay`(M1c 전용)
- 줄 수준 키 `harness_commands_sha256`(`run_v5.py:546`)과 `hydraulic_options`는 `hydraulics_record` 밖이라 비교 범위 밖이다(기록).
- 목록은 이 덧붙임으로 고정한다. 바꾸려면 새 덧붙임이 필요하다. 도구는 목록을 코드 상수로 두고, 단위 시험이 이 표와 같은지 확인한다.
- 옛 `p3_hash_check.py`는 LAS 이전 기록 전용이다(docstring 3~4행). T-JR 판정에 쓰지 않는다(재검토 R-g).

## 4. T-JR-12 판정 정의(결과 전, 질문 2와 C1·C2·R-c)

### 4.1 READY 시각(C1)

- 줄의 첫 READY 시각은 `base.t_ready_s`가 있으면 그 값, 없으면 `base.t_ready`다. `r79_sensor_judge._ready_time`(`r79_sensor_judge.py:245-247`)과 같은 결과여야 하고, 그 함수를 쓰기를 권한다. 두 키가 모두 없거나 값이 None이면 "READY 없음"이다.
- 근거: 저장 H-6(`h6_dg3_v4on.json`)은 ref·g6·g6r 계열 91행이 `t_ready_s`, slope·main 계열 37행이 `t_ready`, 7행(모두 L3)이 READY 없음이다.
- **확인 시험(결과 전, 저장 자료만)**: 저장 H-6을 기준과 새 쪽 모두에 넣은 자기 대조(`t12 --bundle VBH`, base = new = H-6)를 단위 시험으로 둔다. 기대는 다음과 같다. 다르면 READY 읽기 결함이므로 멈춘다.
  - 판정 불가 0, 실패 0
  - "둘 다 READY 없음" 기록 7
  - 짝 135, L2 1

### 4.2 READY 판정(질문 2, Dg-3 v4 선례 `p3_extend_start_spec.md` 13.1)

| 기준 행 | 새 행 | 처리 |
|---|---|---|
| READY 있음 | READY 있음 | 새 − 기준 > 30 s면 실패 |
| READY 있음 | READY 없음(시간 초과·FAULT·중단 포함) | 실패(13.9절 문장) |
| READY 없음 | READY 없음 | **기록**("둘 다 READY 없음", 두 줄의 `final_phase`를 함께 적음) |
| READY 없음 | READY 있음 | **기록**(개선) |

- 13.9절의 "READY에 닿지 못한 행은 +30 s 초과로 세어 실패"는 기준 행이 READY에 닿은 짝에 적용한다. 기준 행이 READY 없음인 짝은 +30 s 비교의 기준이 없으므로 위 표의 기록으로 둔다. 이 짝도 새 FAULT와 L2 통과 → 실패 판정에서는 빠지지 않는다.
- 판정서에 "기준 READY 없는 짝은 Dg-3 v4 선례대로 기록(사용자 결정 2026-11-20, 결과 전)"과 그 짝 수를 적는다.

### 4.3 판정 범위(C2)

- **"통과 → 실패"는 L2 1행만 판정한다**(13.9절 "L2 통과 → 실패 0", Dg-3 v4 선례). 기준 등급이 pass 또는 flag이고 새 등급이 fail이면 실패다(`h8_noise_judge_4368` 등급, flag는 실패가 아님).
- L2·L3 전 등급의 전이 수(pass→fail, fail→pass, pass→flag, flag→fail 등)는 기록으로 낸다.
- 새 FAULT 0과 READY(4.2절)는 135짝 전부에 적용한다.
- 등급이 판정 불가인 줄이 L2면 판정 불가다. L3이면 기록에 적는다.

### 4.4 기준 쪽 검사(R-c)와 기준 판정 파일

- VBJ 묶음의 기준 VBJ0 135줄에도 4a-2 B2 증거 규칙(P4 켬: ① = ② > 0)을 건다. 어기면 `setting_defect`다. VBJ0는 ③ 꺼짐이므로 rev 5 정체성 검사는 해당 없다.
- VBH 묶음의 기준은 저장 H-6이다. 그 r79 판정 파일(`--base-judge`)은 실행 전에 `r79_sensor_judge.py judge ... --s4-late-loc`로 저장 H-6에서 만들고, 명령과 sha256을 실행 전 기록에 남긴다. 새 쪽 판정 파일도 같은 명령 꼴로 만든다.

## 5. 실행 전 확인(결과 전)

### 5.1 B2 건식 확인(R-a)

- **잡 선정 규칙**: 판정 집합의 합집합에 들지 않는 잡만 쓴다. 합집합은 다음과 같다.
  - `run_v5` 배치 `j9_main`·`j9_cases`·`j9_case_f`·`j9_t8`의 잡
  - T-JR-12의 Dg-3 135키
  - 기준선 `baseline_221456d`의 잡
  - 잡 비교는 `job`에서 `setting`과 실행 키(`mask`, `t4h_dir`)를 뺀 정규화 JSON으로 하고, 선정 스크립트가 "합집합 밖"을 출력으로 보인다.
- 경로별로 하나씩, 아래 다섯 실행이다.

| # | 경로 | 설정 | 기대 |
|---|---|---|---|
| 1 | 이벤트 경로(로드 판독이 있는 사례, R12·R14·R15·R16 계열) | VBJ(P4 켬) | ① = ② > 0 |
| 2 | 같은 잡 | VBH(P4 끔) | ① = 0, ② > 0 |
| 3 | 같은 잡 | VBJ0(P4 켬, ③ 꺼짐) | ① = ② > 0 |
| 4 | r79 경로(Dg-3 135키 밖의 잡음 키, `R79_ROD_MODEL=plant_truth`) | VBJ | ① = ② > 0 |
| 5 | 같은 키, `plant_truth` 없이 | VBH | ① = 0 |

- 읽는 값은 증거 2키와 오류 여부뿐이다. 출력은 별도 폴더(`dryrun_evidence/`)에 두고 어떤 판정에도 쓰지 않는다.
- `jp3_case_replay.py`(C·D) 행에 증거 키가 있는지는 실행하지 않고 단위 시험으로 본다. 무장한 하네스 플랜트(VB + P1 옵션)의 `plant_record`에 두 키가 있어야 한다.
- 이벤트 경로 합집합 밖의 잡이 없으면 멈추고 확인 필요로 올린다(판정 집합 안의 잡으로 대신하지 않는다).

### 5.2 F-A 경로 동등성(R-b)

- 사례 F 실행 전에, `j9_case_f`와 같은 이벤트 경로 구성으로 저장 `grid_r67_top.json`(sha256 `7160f9f1…`) **results[13].runs[0]·runs[1]·runs[2]**(G4, offset 0.0·0.025·0.05 s, 같은 FR 행)를 VB로 돌린다.
- 판정 대상 runs[3](0.075 s)은 쓰지 않는다.
- 기대: 세 run 모두 다음이 저장 run과 같다. 하나라도 다르면 사례 F를 돌리지 않고 경로부터 고친다.
  - `harness_commands_sha256`와 저장 `commands_sha256`(앞 12자: `4712c8fcfeb3`, `6d1d93ac77dd`, `7034ad6a41f1`)
  - `extend_bound_check`의 `breach_reads`, `min_gap_bar`(≤ 10⁻⁹ bar), `min_gap_t_s`(≤ 10⁻⁹ s)
- 이 실행은 저장 VB 값의 재현이라 새 판정 정보를 만들지 않는다.

### 5.3 T-JR-10 보강(R-d)

- `j9_t8`에 VB 22행 재실행을 **기록**으로 더한다(현재 코드 VB 대 저장 h10의 명령 해시). 판정은 2·3절대로 VBH 대 저장 h10이다.
- VB 재실행이 저장 h10과 다르면, T-JR-10 실패를 T8 결함으로 읽지 않고 저장값 노후 여부부터 본다(멈춤).

### 5.4 판정 입력 고정(C5)

실행 전에 아래 파일을 git으로 넣거나 고정 목록(SUMS)에 넣고, 판정 도구가 입력 sha를 대조한다. 지금은 모두 추적되지 않는다(`main.jsonl`은 `.git/info/exclude`).

| 파일 | sha256 | 쓰는 곳 |
|---|---|---|
| `06_analysis/03_hydraulic/coupled/v5/resume_k1/h10_reuse_rerun.jsonl` | `ce526b1f71e635e6b80d538f36841ece01710af46f02acb4b3fa1355a5a4dcb3` | T-JR-10 저장 VB |
| `06_analysis/03_hydraulic/coupled/v5/main.jsonl` | `9ad749907c34c9e9efb77579a8ab6e3b1f86cdc32d36162c0029005ca545b29e` | 22행 규칙의 잡 원본 |
| `06_analysis/03_hydraulic/coupled/v5/resume_k1/h6_dg3_v4on.json` | `ea0ab94c81e58eeb83ab2b6a63494a56c16bcd4165a62de47eba5efd03f23c89` | T-JR-12 VBH 기준 |
| `06_analysis/03_hydraulic/coupled/v5/resume_k1/h9_grid/grid_r67_top.json` | `7160f9f19b497ea264e9dd90c58c2da25540ded51e8510197205cf91f00bd827` | F-A, 5.2절 |
| `06_analysis/02_control/j_p3_cause/jp3_remedy_spec_addendum_4a2.md` | `2f3e36bdc2bf5ff76e2cdfe3ddfe41e23dbdd94b8fb9ea50b4bb532ffecf9b92` | 판정 정의 |
| `06_analysis/02_control/j_p3_cause/j4a_remedy_3b949f5/` | 폴더 안 `SHA256SUMS` | 1절 수치 |

- 저장 h10의 T4h(`h10_reuse_rerun_t4h/`)와 H-6의 T4h(`h6_dg3_v4on_t4h/`)도 3.1절 assert와 기록에 쓰므로 같은 목록에 넣는다.
- 4.4절의 기준 판정 파일도 실행 전에 같은 목록에 넣는다.

## 6. 보완 구현(python-expert) 작업 표

control 재검토와 실행 전 감사는 아래 기준으로 본다.

| # | 대상 | 할 일 | 판정 기준 |
|---|---|---|---|
| K-1 | `jp3_tjr_judge.py t8` | 20행 목록 요구를 없애고 22행으로 판정. 3.1절 A·B·기록 일치를 판정하고 C를 기록. 3.2절 허용 목록을 코드 상수로 둠. 저장 줄의 태그·revision을 assert | 단위 시험: 허용 키만 다른 짝 → 통과. 목록 밖 경로 하나 다름 → 실패. 저장 줄에 있는 허용 키 값이 다름 → 실패. `WARN_ROD_PRESSURE_FALLBACK` 1건 → 실패. 태그 다름 → 판정 불가. 허용 목록 상수 = 3.2절 표 |
| K-2 | `jp3_tjr_judge.py t12` READY | 4.1절 읽기, 4.2절 네 경우 | 단위 시험: `t_ready` 계열 줄 처리, 네 경우 각각, 저장 H-6 자기 대조(4.1절 기대: 판정 불가 0, 실패 0, 둘 다 없음 7) |
| K-3 | `jp3_tjr_judge.py t12` 범위 | 통과 → 실패는 L2만 판정, 전 등급 전이는 기록 | 단위 시험: L3 pass → fail만 있는 묶음 → 통과(기록에 1). L2 pass → fail → 실패. L2 flag → fail → 실패 |
| K-4 | `jp3_tjr_judge.py t12` 기준 쪽 | VBJ0 기준 줄에 B2 증거 검사 | 단위 시험: VBJ0 줄 ① = 0 → `setting_defect` |
| K-5 | `run_v5.py` `j9_t8` | VB 22행을 기록 묶음으로 더함(5.3절) | 배치 목록 시험: VBH·VBJ·VBJ0·VB × 22 = 88. 판정은 VB를 기록으로만 읽음 |
| K-6 | 건식 확인 스크립트 | 5.1절 잡 선정(합집합 밖 증명 출력)과 다섯 실행의 증거 2키만 읽는 요약 | 선정 출력에 합집합 밖임이 보이고, 요약에 증거 키 외의 값이 없다. 실행은 메인이 띄운다(메인 세션 권고) |
| K-7 | C·D 증거 키 | 무장한 VB + P1 플랜트의 `plant_record`에 두 키 | 단위 시험 |
| K-8 | F-A 경로 동등성 | 5.2절 세 run 대조 스크립트(또는 `jp3_case_judge.py` 하위 명령) | 저장 값 재현 시 종료 0, 하나라도 다르면 1. 판정 대상 runs[3]을 입력으로 받으면 거부 |
| K-9 | 1.2절 기록 수치 | 판정서 작성용으로 기록 시험 출력 경로와 값을 표로 냄(이미 있는 `records_full` 사용) | 1.2절 문장의 수치와 기록 파일 값이 같음(반올림만 다름) |
| K-10 | 입력 고정 | 5.4절 표(메인과 함께) | `seal_check`·`baseline_check` 등 실행 전 감사 도구 종료 0 |

## 7. 바뀌지 않는 것

- 봉인 문장은 하나도 고치지 않는다. 이 덧붙임이 정한 것은 다음뿐이다.
  - P4-7 회귀 대조 양과 판정서 공개 문장(1절)
  - T-JR-10·11 표본(2절)
  - T-JR-10 meta 조항의 하네스 판정(3절)
  - T-JR-12의 READY 읽기·READY 없음 처리·판정 범위·기준 쪽 검사(4절)
  - 실행 전 확인(5절)
- 4a-2의 2절(P4-2 사슬), 3절(시드 순 힘), 4절 기준, 6절 사용자 확인은 그대로다.
- 13.5절 자동 진행 범위는 2026-11-20 사용자 결정대로 좁힌 그대로다. 보완 → 단위 시험 → control 재검토 → 실행 전 감사 뒤, 사례 재생과 T-JR 실행 시작은 다시 승인을 받는다.
- 판정 행 0 = 판정 불가(통과 아님)는 모든 묶음에 그대로 적용한다.
- 2~4절의 정의 문장은 J-P3 rev 5 판정 도구의 경로 2(B5, 작성 주체 미정)도 그대로 쓴다.
