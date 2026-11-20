# 436.9 J-P3 판 4a 재구현(J4a, `ad5024b`) 명세 적합성 검토

> 메인 세션 저장(2026-11-20): control-expert 리포트 원문 그대로. 결정·정오는 맨 끝 절에 덧붙인다.

작성: control-expert, 2026-11-20. 읽기 전용 검토이고, 코드·명세는 고치지 않았습니다. 시뮬레이션·배치·단위 시험도 돌리지 않았습니다(단위 시험 실행은 python-expert 몫).
- 대상: worktree `C:\workspace\outrigger_control\.claude\worktrees\z4369-jp3`, `git diff 221456d ad5024b`(15파일, +1955/−125)
- 명세: `jp3_remedy_spec.md` 판 4a(sha256 `8be9de22…`, 직접 확인)와 덧붙임 4a-1
- 의존성 점검: 생략했습니다. 숫자 계산은 봉인된 기준선 파일을 읽는 스크립트 3개뿐이라 dynamics-dev numpy만 썼습니다.
- Julia 교차 검증: 해당 없음. 이번 검토는 코드·명세 대조이고 새 제어 수치를 계산하지 않았습니다.

## 0. 판정 요약

| 구분 | 건수 | 요지 |
|---|---|---|
| 차단(사례 재생 A~F 전) | 3 | B1 봉인된 예측의 멈춤 조건이 단위 시험에서 이미 걸림(P4-6·P4-7·T-JR-05 (k)). 13.5에 따라 멈추고 보고할 일. B2 사례 F의 E 군(VBJ·LSJ)은 r67 경로라 P4(로드 판독 = M2 참값)가 걸리지 않을 가능성이 큼. B3 P4-4·T-JR-15의 "시드 순 힘 연속 ≤ 1 N" 판정 열이 항등식(언제나 0) |
| 차단(다음 단계에서) | 2 | B4 J4a-15(T-JR-10~15 배치와 T-JR-12 판정 도구)가 없음. T-JR-10~15로 넘어갈 수 없음. B5 J-P3 rev 5 판정 도구에 경로 2가 없음. 436.9 판정 전에 필요 |
| 권고 | 9 | 비교 스크립트 보강 4건, 죽은 함수 1건, `j_p3_over_rows` 판정 행 범위 등 |
| 이상 없음 | 제어기 쪽 | R5-6 고정, R5-7 적용 두 곳·비적용 두 곳, R9 이중 적용 없음, 시험 상수 검사, 정체성 복사, 반례 갈래, R7 재생 거부. P4-1(T8)을 깰 변경은 찾지 못함 |

**제어기 동작은 판 4a 의도와 맞습니다.** 걸린 것은 예측·판정 도구 쪽입니다.

## 1. 차단

### B1. 봉인된 예측의 멈춤 조건이 단위 시험에서 이미 걸림(13.5 "관문 하나라도 실패하면 멈추고 보고")

구현자는 아래 내용을 시험 코드의 `xfail(strict=True)`, docstring, 상수로 남겼습니다. 실제 통과·xfail 결과는 python-expert의 실행으로 확인해야 합니다.

| 예측·시험 | 봉인 문장 | 시험 코드의 사실 | 원인(내 판정) |
|---|---|---|---|
| P4-6(T-JR-04 ⑪b 훅) | HOLD 시작 $p_{tr}$와 `model_only` 간격이 표에서 ±2 bar 넘게 다르면 멈춤 | `test_jp3_rev5_property.py:561-573`: 1 mm/s 두 행의 시작 $p_{tr}$가 표보다 약 7 bar 낮다는 이유로 strict xfail. `:576-586`: 0.3 mm/s 네 행은 $\kappa_x\cdot0.3$ mm/s = 1.15 % $v_{max}$에서 추적기 관문이 20 s 안에 열리지 않아 훅 플랜트가 풀리지 않음(행 구성 불가). 건전성 부분(R5-7 간격 ≥ 표 하한, 출처 `retract_tracker`, `model_only` ≤ −20 bar)은 1 mm/s 행에서 판정 대상(`:545-558`) | 명세 작성자(control)의 예측 전제 오류. `cr09`는 RET 시간만큼만 P3 (c)를 적분했고, 명령이 끝난 뒤 τ_v 0.1 s 밸브 꼬리의 추가 수축을 뺐다(예측 모델 경로 ≠ 구현 경로). 0.3 mm/s 행은 관문이 열린다고 잘못 가정했다. 관문이 열리지 않으면 CARRY_ret 끈끈 상계가 덮으므로 ⑪b 노출은 오히려 없다 |
| P4-7(T-JR-04 ⑪b-P1) | `model_only` 첫 HOLD 초과 +27.4 ± 0.5 bar. $N$ = 관문이 RET 안에서 열리는 가장 작은 주기 수 | `:661-684`: 모니터 자신의 관문으로는 $N$ = 12이고 초과는 **+29.19 bar**로 범위 밖이다. 시험은 유압 `q1`의 $N$ = 14로 바꿔 27.4 ± 0.5를 확인한다. R5-7 여유 ≥ +4.30 bar는 $N$ = 12에서 두 띠 모두 확인(`:641-653`) | 멈춤 조치(`hr11/q1`과 대조)는 구현자가 했다. q1은 관문 헤드를 $p_{h0}-4.62+e_h$로 고정하고, 모니터는 해제(242 ms) 뒤 내려가는 헤드 판독을 따라가 약 0.13 s 일찍 연다. 예측 모델 경로 차이이고, 건전성은 성립한다 |
| T-JR-05 (k) 둘째 문장 | "신장 감압 뒤 수축($\hat p+\delta_m\le$ 바닥)에서는 R5-7이 값을 바꾸지 않음(비트 동일)" | `test_jp3_edition4.py:204-216`: 반대로 "언제나 바닥 + δ_m 이상"을 assert한다(구현자 보고) | 명세 전제 오류. 수축 분류(RET·CARRY_ret) 주기마다 추적기가 $\hat p\leftarrow\max(\hat p,\ \max(p_{ret}, 13+p_h/3))$를 한다(`extend_start_bound.py` `_advance_classified`, 바닥 입력은 `two_pressure.py:2440-2442`). 그래서 $\hat p+\delta_m\le$ 바닥은 일어나지 않는다. R5-7은 수축 뒤 모든 구간의 창 후보를 같은 헤드에서 δ_m(0.5 bar ≈ 전방 0.19 kN, 후방 0.16 kN) 이상, RET 헤드가 창 헤드보다 높으면 $(h_{RET}-h_w)/3$만큼 더 올린다. 2.10절 비용 문장("늘어나는 과보수는 R5-3이 높게 시드한 수축에만")은 틀렸다. 상계 쪽이라 건전성 영향은 없고, 비용은 T-JR-12에서 잰다 |

- 영향: 셋 다 코드 결함이 아니라 명세(예측) 쪽 오류이고, 상계의 건전성 부분은 성립합니다.
  - 다만 P4-6은 13.11 R1에서 "적중"을 쓸 수 있는 두 항목 가운데 하나입니다. 판정서에 "적중"으로 쓸 수 없습니다.
  - strict xfail로 묶어 시험 묶음이 "통과"로 보이게 한 상태로 자동 진행하면, 봉인 멈춤 조건을 숨기게 됩니다.
- 필요한 일: 사용자 확인(확인 필요 질문 Q1) 뒤 판정서에 공개 문장을 넣고 진행합니다. 코드 수정은 필요 없습니다.

### B2. 사례 F의 E 군(VBJ·LSJ1~4)에 P4가 걸리지 않을 가능성(13.8 F-E, 6.4 "VBJ·LSJ의 로드 판독은 M2 참값")

- P4는 `harness_hydraulics.install_rod_reading_truth`(`harness_hydraulics.py:900-917`)가 `s9_soil_event_screen._s8_modules`를 감싸고, 그 함수가 불릴 때 `r64.with_two_pressures`를 바꾸는 방식으로만 걸립니다. 이벤트 경로 전용입니다.
- `jp3_case_f.py`는 `r67_g1_screen.py`를 단독 프로세스로 돌립니다.
  - r67은 `import r64_g4_closed_loop as r64`(`:83`)로 r64를 직접 불러 `r64.with_two_pressures`를 호출합니다(`:196`).
  - r67 단독 경로(`install_v5_setting`·`install_v5_run`, `:546-575`)에서 `_s8_modules()`를 부르는 곳을 찾지 못했습니다. `verdict_runs.py:465·619`의 호출은 `_run_event`와 t_a 계산 쪽입니다.
- 그래서 F-E 행은 P4가 빠진 채 돌 가능성이 큽니다. 그 행의 `hydraulic_options`에는 `rod_reading_truth: True`가 기록되므로 라벨과 실제 적용이 어긋납니다. 이 상태로는 F-E(판정 키 0, 재잠김 0, 어기면 멈춤)가 VBJ 정의의 행이 아닙니다.
- 필요한 일(python-expert):
  - r67 경로에도 P4를 거는 방법을 마련합니다. 예: 설치 때 `sys.modules["r64_g4_closed_loop"]`의 속성을 직접 바꾸거나, F를 run_v5·이벤트 경로로 돌립니다.
  - P4가 실제로 적용됐다는 기록 키를 하나 더합니다(예: 참값 판독 읽기 수).
  - 고친 뒤 VBJ F 1행으로 건식 확인합니다.

### B3. P4-4·T-JR-15·T-JR-18의 "시드 순 힘 연속 ≤ 1 N"이 항등식이다

- `harness_hydraulics.py:703-705`: `net_force_step_N = (step·A_ann/A_h)·A_h − step·A_ann`. 이 식은 정의상 0이고 부동소수 오차만 남습니다.
- 이 열로 판정하는 곳이 두 군데입니다.
  - `jp3_baseline_compare.py:195-210`(`seed_checks`, P4-4)
  - `test_jp3_harness_units.py`의 `test_t_jr_15_retract_seed_rows_and_net_force`
- 둘 다 실패할 수 없습니다. 플랜트 쪽 물리량인 `net_force_release_step_N`(시드 + M2 재고정 + 같은 스텝의 첫 완화)은 기록 열일 뿐입니다.
- 필요한 일(Q4): 둘 가운데 하나를 고릅니다.
  - (가) 시드 재고정 직후, 완화 전의 플랜트 순 힘 차를 따로 재서 판정 열로 씁니다.
  - (나) 덧붙임으로 이 항목을 "구현 확인(판정 아님)"으로 내립니다.
- P4-4의 시드 수·최대 계단 비교는 그대로 유효합니다. 기준선 값이 P4-4 문장과 같습니다(VBJ 7, LSJ1 11, LSJ2 8, LSJ3 11, LSJ4 11, 최대 33.870~33.986 bar, `hash_list.py`).

### B4. J4a-15 미구현(T-JR-10~15)

- `run_v5.py` 배치는 `j9_main`·`j9_cases`뿐입니다(`:229-232`). T8 짝(VBH 20/20·22/22, VBJ 대 VBJ0 20/20) 배치, T-JR-12 판정 도구(짝 135 assert, 판정 행 1 assert, READY 미도달 = 실패, 결과 없는 짝 = 판정 불가), T-JR-13~15 집계가 없습니다.
- `j_p3_judgement_rev5`의 `expected_judged_runs` 인자(판정 행 1 assert용)만 있습니다.
- 영향: 사례 재생 A~E는 돌릴 수 있습니다. 그러나 비용 관문 T-JR-12와 j9_main으로는 넘어갈 수 없습니다.

### B5. J-P3 rev 5 판정의 경로 2가 없다(13.2·13.6 "두 경로", J4a-8·10)

- `no_judged_runs`와 정체성 `setting_defect`는 경로 1(`extend_start_bound.py:1790-1884`, `j_p3_inputs.py`)에만 있습니다. rev 5 키(`jp3b_breach_over_tol`)를 읽는 다른 도구가 저장소와 `~/.claude/tools`에 없습니다.
- 사례 재생에는 영향이 없습니다. 436.9 판정 전에는 다른 작성자가 경로 2를 만들어야 합니다.

## 2. 권고

| # | 위치 | 내용 |
|---|---|---|
| R1 | `jp3_baseline_compare.py:170-183` `_unexplained_raises` | P4-2의 "그 구간에서 시드·운반으로 이어진 읽기"를 다음 LOCK·HOLD 읽기에서 끊어 셉니다. 그런데 R5-7이 올린 ④는 R5-3 시드로 $\hat p$를 올리고, 그 $\hat p$가 EXT를 거쳐 다음 신장 잠금 후보 $\max(13, \hat p+\delta_m)$(출처 `extend_bound`·`previous_moving`)까지 갑니다. 기준선 추적으로 보면 이 사슬(수축 뒤 구간 → 신장 → 새 구간)은 E 다섯 행의 다리마다 2~5회 있습니다(`chain_scan.py`). 그 가운데 RR 53.4~53.6 s → 59.3~59.4 s(57.0 s)는 수축 뒤 구간의 $\hat p+\delta_m-④$가 +0.6~+9.1 bar이고, 다음 잠금의 ④가 $\hat p+\delta_m$과 같습니다(차 0.000, `chain_detail.py`). 그래서 이 읽기들이 "설명 안 된 상승"으로 잡혀 P4-2가 멈출 위험이 있습니다. 결과를 보기 전에 해석을 고정하라고 권합니다(Q2). 스크립트는 R5-7 읽기에서 시작해 같은 다리의 `jp3_ext_bound_Pa`가 기준선보다 높은 상태가 끊기지 않는 읽기, 그리고 그 상태에서 연 구간의 읽기를 설명된 것으로 셉니다 |
| R2 | 같은 파일 `:231`, `:245-247` | 판정 행 수 > 0을 설정과 무관하게 `jp3_judged_row`로 셉니다(VBH·LSH·VBG5도 들어감). JUDGED_SETTINGS(VBJ·LSJ)만 세게 바꾸십시오. P4-3a의 `sum(check.get(key) or [0])`는 키가 없으면 0으로 통과합니다. 키가 없으면 판정 불가로 바꾸십시오 |
| R3 | 같은 파일 `:131-139`, `:224` | 정체성 위반(13.6 `setting_defect`)을 예측 실패(`failed`, 종료 1)로 냅니다. 판정 불가(종료 2) 또는 `setting_defect`로 따로 내십시오. VBG5(D, rev 5)는 정체성 검사를 건너뜁니다(`:133`). 기본 규칙 검사는 VBG5에도 거십시오 |
| R4 | 같은 파일 `:145-146` | 기준선 npz에 `jp3_t_s`가 없으면 `has_trace False`로 넘어갑니다. rev 5 짝(B·D·E)에서는 판정 불가로 멈추게 하십시오(13.1 "jp3_t_s 길이·값 같음" assert) |
| R5 | `two_pressure.py:2949-2954` | 명세 4.1·J4a-2가 이름을 붙인 `_retract_lock_start_model_Pa`를 정의만 하고 부르지 않습니다(죽은 코드). 실제 적용은 `_track_moving_leg:2918-2921`과 `_add_lock_candidate:3133-3134`가 `_retract_tracker_term_Pa`를 직접 max에 넣어서 하고, 값은 같습니다(T-JR-05 (j)가 확인). 두 곳이 이 함수를 부르게 하거나 함수를 지우십시오 |
| R6 | `j_p3_inputs.py:86-112` | 6.1·13.2의 판정 행은 "VBJ·LSJ"인데, rev 5 판정이 설정으로 거르지 않습니다(VBH·LSH 행이 섞이면 판정에 들어감). `REVISION_KEY`가 빠진 rev 5 기록은 rev 4 `j_p3_judgement`로 가고, 그 함수는 `rule_revision` 5를 거부하지 않습니다. `STATUS_ORDER`에서 `no_judged_runs`가 H-7보다 위라서 rev 4 H-7을 가립니다(사소) |
| R7 | `jp3_x11_replay.py`, `jp3_case_f.py` | 러너만 있고 판정 스크립트가 없습니다. P4-5a(해시 = 기준선 LSJ4 `3672c7222519`, FL 49.0 s HOLD `jp3b_breach_over_tol` 1, 간격 +10.674 ± 0.05 bar)와 F-A(저장 격자 `results[13].runs[3]`)·F-B(해시 = F-A)·F-E를 스크립트로 판정하게 하십시오. 손으로 판정하면 절차를 판정서에 적어야 합니다 |
| R8 | `jp3_case_f.py` | 13.8·J4a-14의 배치 이름 `j9_case_f`(run_v5 배치)가 아니라 독립 러너입니다. B2를 고칠 때 run_v5 배치로 옮기면 경로 문제도 함께 풀립니다 |
| R9 | `two_pressure.py:3083-3086` | `ret_after_gate_s`의 "관문 열림 시각"을 첫 RET 읽기 − T(직전 CARRY 읽기 시각)로 둡니다. 실제 관문 열림 소단계와 최대 0.1 s 다릅니다. 기록 전용이므로 T-JR-12 보고에 해상도를 적으십시오 |

## 3. 이상 없음(근거)

- **R5-6 고정**: `CARRY_END_RULES = (inherit,)`(`extend_start_bound.py:162`), `check_allowed`(`:325-351`). 상속은 `_carry_to_inherit`(`two_pressure.py:2519-2526`)와 `_inherit_carry_candidates`(`:2554-2568`)가 합집합과 $s_w$ 최댓값으로 합니다.
- **R5-7 적용 두 곳**
  - ① RET·CARRY_ret 이동 시작값: `_track_moving_leg:2918-2921`. `last_sign < 0`이고 rev 5·`with_tracker`일 때만 켜지고, 아니면 −∞(`_retract_tracker_term_Pa:2941-2947`)입니다. 그래서 rev 4와 `model_only` 경로는 그대로입니다.
  - ② `last_sign < 0` 창 후보: `_add_lock_candidate:3133-3134`. 조건이 없고(A5), 짝 헤드는 창 표본 헤드입니다(A4).
- **비적용 두 곳**: CARRY_ret 운반 후보 `:2464-2467`, HOLD R5-2 후보 `:2545-2548`. `_lock_start_model_Pa`(`:3364-3374`)는 고치지 않았습니다(R9 이중 적용 없음).
- **시험 상수 검사**: `__post_init__` → `check_allowed`(`:321`), 모니터 생성(`two_pressure.py:1367-1369`), 매 rev 5 읽기의 `ensure_hold_state`(`extend_start_bound.py:691-698`, `_period_classes:2429`). pickle은 복원 자체는 통과하고, 생성과 첫 읽기에서 `ValueError`가 납니다(13.7 문장대로, 시험 `test_jp3_edition4.py:102-120`). `HydraulicOptions`에는 경로가 없습니다(`:123-134`).
- **정체성(13.6)**: 추적 행에 `identity`(`two_pressure.py:2685`)가 붙고, `extend_bound_check` 최상위에 `spec_edition`·`carry_end_rule`·`retract_start_rule`·`identity_consistent`가 들어갑니다. `extend_start_record`에도 있습니다(`:2810`). 판정은 `is_default_rule_identity` → `J_P3_DEFECT_IDENTITY`(`extend_start_bound.py:1790-1801, 1845-1847`)이고, 시험 설정 이름(`VBG4`·`VBG5`·`*_X11`)이 섞이면 묶음 전체가 `setting_defect`입니다(`j_p3_inputs.py:45-56, 106-107`). `JP3_SPEC_EDITION = "8be9de22"`는 봉인 sha와 같습니다.
- **no_judged_runs(경로 1)**: `extend_start_bound.py:1862-1869`. 판정 행 0개 또는 `expected_judged_runs` 불일치이면 판정 불가이고, 결함이 있으면 결함이 먼저입니다.
- **반례 갈래 X11**: 두 상수를 함께 켜고 설정 `LSJ4_X11`을 씁니다. fresh만 켠 기록 갈래는 `LSJ4F_X11`이고, 별도 출력 폴더를 씁니다(`jp3_x11_replay.py:41-48, 88-90`). 두 이름 공간(`v5_options`·`harness_hydraulics`)의 `apply_controller_options`를 모두 바꾸고, spawn 작업자는 `__mp_main__`으로 다시 import합니다.
- **R7 옛 기록 재생 거부**: `t4h_replay.py:281-295`, `chrono_t45_replay.py:200-212`. `--retract-start-rule model_only`만 허용하고 `judged: False`를 붙입니다.
- **J4a-4**: `RETRACT_TRACKER`를 끝에 붙였고(`two_pressure.py:1034-1036`), `JP3_SOURCE_NAMES` 순서는 enum과 같습니다.
- **J4a-9 기준선**: SUMS sha `197ac14e…`(직접 확인), CR 떼기, SUMS 밖 파일 거부(`jp3_baseline_compare.py:64-91`), 짝 1:1, `jp3_t_s` 같음, 클래스별 읽기 수 > 0(rev 5 행만, 덧붙임 4a-1)을 확인합니다.
- **P4-1(T8) 논리**
  - diff에서 새로 읽거나 쓰는 상태는 후보·출처·기록·추적 행(`lower_force_N` 추가, `:1643`)뿐입니다.
  - 대체 추정(`rod_estimate_Pa`)이 힘에 들어가는 곳은 대체 다리뿐입니다(`_fallback_forces:3428-3433`). `_count_tension`(`:2821-2831`)은 기록입니다.
  - 하네스에 더한 `self.pressure()` 호출은 순수 함수입니다(`s8_g4_rodside_check.py:160-161`, 순 힘 [N]).
  - 플랜트·`v5_options`·`run_v5`·`c2.py`는 바뀌지 않았습니다.
  - 기준선 17행의 `commands_sha256` 앞 12자는 P4-1 목록과 모두 같습니다(`hash_list.py`). "커밋 전 트리 대 221456d 차이" 기록은 없습니다.
- **P4-2 단조성의 코드 근거**: R5-7·R5-6은 최댓값 항과 합집합만 더합니다. 관문 문턱은 $\hat p$에 증가하므로 관문은 늦어지기만 합니다(EXT·RET → CARRY 방향). 낮아지는 경로는 찾지 못했습니다.
- **J4a-11**: T-JR-03 149 ms(허용 0), 연속 ODE 148.013 ms. T-JR-06은 로드 체크 해제 ≤ 해제 ≤ $t_B$ + 5 ms이고, 160.16 / 160.08 / 94.02 ms를 확인합니다.
- **J4a-16**: `OUTRIGGER_RECORDS_ROOT` 환경 변수로 skip 3건을 주 체크아웃 레코드에 연결했습니다(실행 결과는 python-expert).

## 4. J4a 항목별 적합 표

| # | 판정 | 비고 |
|---|---|---|
| J4a-1 | 적합 | meta `carry_end_rule`(rev 5 `to_meta`) |
| J4a-2 | 적합(형식 권고 R5) | 값은 명세 식과 같고, 이름 붙은 함수는 쓰지 않음 |
| J4a-3 | 적합 | 복원은 통과, 생성과 첫 읽기에서 거부 |
| J4a-4 | 적합 | |
| J4a-5 | 적합 | per-read 4열 + `trace_excerpt` `model_source, model_age_s` |
| J4a-6 | 부분 | 시드 기록·`carry_log`는 있음. 순 힘 연속 열은 항등식(B3) |
| J4a-7 | 적합(R9) | `retract_tracker_*`, T4h `jp3_ret_after_gate_s` |
| J4a-8 | 부분 | 경로 1과 J4a-9만 있고 경로 2 없음(B5). J4a-9는 `failed`로 냄(R3) |
| J4a-9 | 부분 | assert 4개는 구현. 판정 행 집계 범위(R2), 추적 없는 짝 통과(R4), P4-2 사슬 범위(R1) |
| J4a-10 | 부분 | 경로 1만(B5) |
| J4a-11 | 적합 | |
| J4a-12 | 부분 | 시험은 있으나 P4-6 strict xfail·행 4개 구성 불가, P4-7 $N$ 바꿈(B1) |
| J4a-13 | 적합 | 판정 스크립트 없음(R7) |
| J4a-14 | 부분 | 독립 러너, 판정 도구 없음, E 군 P4 의심(B2, R8). "기준선에도 같은 행"은 덧붙임 4a-1로 적용하지 않음 |
| J4a-15 | **미구현** | B4 |
| J4a-16 | 구현 | 실행 확인은 python-expert |
| J4a-17 | 코드 변경 없음 | T-JR-01 보고에 예외로 적을 일 |
| J4a-18 | 적합 | |

## 5. 결과 전 고정 예측별 판정 도구 준비 여부

| 예측 | 판정 도구 | 상태 |
|---|---|---|
| P4-1 | `jp3_baseline_compare.py`(짝별 해시) | 준비됨. 기준선 = P4-1 목록 17/17 |
| P4-2 | 같은 스크립트(낮아진 읽기 0, 상승 설명, 분류 변화) | 준비됨. 다만 상승 설명 사슬이 좁아 거짓 멈춤 위험(R1·Q2) |
| P4-3a | 같은 스크립트(VBJ·LSJ 판정 키 0, 재잠김 0) | 준비됨(키 누락 시 통과 문제 R2) |
| P4-4 | 같은 스크립트 | 시드 수·최대 계단은 준비됨. 순 힘 연속은 항등식(B3) |
| P4-5a | `jp3_x11_replay.py`(러너) | 판정 스크립트 없음(R7). 기록 키로 손 판정은 가능 |
| P4-6 | T-JR-04 ⑪b 단위 시험 | 건전성 부분은 준비됨. 수치 부분 strict xfail, 0.3 mm/s 네 행 구성 불가(B1) |
| P4-7 | T-JR-04 ⑪b-P1 단위 시험 | R5-7 여유는 준비됨. +27.4는 $N$을 q1 값으로 바꿔 확인(B1) |
| P4-8 | T-JR-05 (l)(m) 단위 시험 | 준비됨 |
| P4-9 | `jp3_baseline_compare.py` | 준비됨 |
| F-A·F-B·F-E | `jp3_case_f.py`(러너) | 판정 도구 없음. F-E는 P4 미적용 의심(B2) |
| T-JR-10~15(T-JR-12 포함) | 없음 | 미구현(B4) |

## 6. 확인 필요 질문

- **Q1**(B1): P4-6·P4-7·T-JR-05 (k)의 명세 전제 오류를 판정서에 공개하고 사례 재생으로 진행할지 정해 주십시오.
  - 공개할 내용: 밸브 꼬리 누락, 0.3 mm/s 관문 미개방, q1 관문 헤드 고정, RET 바닥 때문에 R5-7이 수축 뒤 언제나 δ_m 이상 올림.
  - 권고: 공개하고 진행합니다. 판정서에서는 P4-6을 "건전성 부분 성립, 수치 부분 예측 전제 오류(적중 아님)"로, P4-7을 "회귀 대조: $N$ 정의 차이로 +29.19 대 +27.4, 원인 확인"으로 쓰고, 2.10절 비용 문장의 정정을 각주로 붙입니다.
- **Q2**(R1): P4-2의 "그 구간에서 시드·운반으로 이어진 읽기"를 사례 재생 전에 덧붙임 4a-2로 "R5-7 읽기에서 시작해 같은 다리의 $\hat p+\delta_m$가 기준선보다 높은 상태가 이어지는 읽기와 그 상태에서 연 구간의 읽기"로 고정할지 정해 주십시오. 권고: 고정합니다(결과 전이고, P4-2 근거 문장의 단조성 논리와 같은 범위입니다). 고정하지 않으면 RR 약 57~59 s 잠금 읽기에서 P4-2가 멈출 수 있습니다.
- **Q3**(B2): 사례 F의 E 군을 P4 경로를 고친 뒤 돌릴지, F-E를 "P4 없음" 기록 행으로 낮출지 정해 주십시오. 권고: 고친 뒤 돌립니다.
- **Q4**(B3): 시드 순 힘 연속을 (가) 플랜트 측정 열로 바꿀지, (나) 덧붙임으로 판정에서 빼고 구현 확인으로 둘지 정해 주십시오. 권고: (가)입니다.

## 7. 수행한 작업

- 명세 판 4a(13절과 2.1·2.9·2.10·4.1·4.5·5.2~5.7·6절), 덧붙임 4a-1을 읽었습니다. diff 15파일을 검토했습니다(제어기 2, 하네스·재생·비교·러너 7, 시험 6).
- 봉인된 기준선만 읽는 스크립트 3개를 실행했습니다(새 출력은 없고, 예측은 이미 봉인됨).
  - 실행 명령: `conda run -n dynamics-dev python -I -B <스크립트> C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\baseline_221456d`
  - `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\a7a5ff42-46cc-4233-b83c-72252c66f0f4\scratchpad\control-expert-j4a-review\hash_list.py`: 해시·P4-4 기준값 대조
  - `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\a7a5ff42-46cc-4233-b83c-72252c66f0f4\scratchpad\control-expert-j4a-review\chain_scan.py`: R1 사슬 수
  - `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\a7a5ff42-46cc-4233-b83c-72252c66f0f4\scratchpad\control-expert-j4a-review\chain_detail.py`: 사슬별 $\hat p+\delta_m-④$
- 중간 파일(diff 사본)은 지웠습니다.

## 8. 가정

- B1의 시험 결과(약 7 bar, $N$ 12 대 14, +29.19 bar)는 시험 코드의 xfail 사유·docstring·상수에서 읽었습니다. 실제 값은 python-expert의 단위 시험 실행으로 확인해야 합니다.
- B2는 코드 읽기 판단입니다. r67 단독 경로에서 `_s8_modules()`를 부르는 곳을 grep으로 찾지 못했다는 근거이고, 실행으로 확인하지 않았습니다.
- R1의 위험 크기는 기준선 추적만으로 추정했습니다. 새 출력의 $\hat p$ 차이가 EXT 동안 얼마나 남는지는 사례 재생에서야 알 수 있습니다.

## 9. 핸드오프

- 위임 필요(python-expert): B2(r67 경로 P4, 적용 기록 키), B3(순 힘 측정 열), B4(J4a-15 배치·T-JR-12 판정 도구), R1~R9. Q1~Q4 결정이 난 뒤에 합니다.
- 위임 필요(경로 2 작성자, 경로 1 코드를 보지 않는 다른 에이전트): J-P3 rev 5 경로 2 판정(`no_judged_runs`, 정체성 `setting_defect`, VBJ·LSJ 판정 행)(B5).
- 위임 필요(verif-protocol-auditor): Q1·Q2의 덧붙임(4a-2)을 쓰면 사례 재생 전에 실행 전 감사를 받습니다.
- 위임 필요(control-expert, 명세 작성): Q1·Q2 결정에 따른 덧붙임 4a-2 문안. 봉인 본문은 고치지 않습니다.

사용한 스킬: 없음

## 메인 세션 덧붙임(결정·정오)

- python-expert 단위 시험(같은 날, worktree `ad5024b`): 7,398 통과 / 2 실패 / 132 skip / 2 xfail. 13.10절 skip 3건은 `OUTRIGGER_RECORDS_ROOT`로 실행·통과. 실패 2건은 `test_d8x_diag`(master와 같은 해시, 기존)와 `test_hydraulics_flow_limit_run`(worktree에 `07_results` 없음, 메인 데이터로는 통과). xfail 2건은 P4-6 1 mm/s 두 행(B1과 같음). skip 122건 중 113건은 메인 데이터 + worktree 소스로 실행·통과. 검증 공백 10건(`test_chrono_t45_replay` 5, `test_s9_mass_scale` 4, `test_las_off_chrono` 1). 산출물은 세션 scratchpad `python-expert-j4a-tests\`.
- 사용자 결정(2026-11-20):
  - Q1: 덧붙임 4a-2로 예측 전제 오류(P4-6·P4-7·T-JR-05 (k), 2.10절 비용 문장)를 공개하고 진행한다. 봉인 본문은 고치지 않는다. 판정서에 P4-6은 '적중' 아님.
  - Q2: P4-2 '설명된 상승' 범위를 결과 전에 덧붙임 4a-2로 고정한다(검토 R1 문안).
  - Q4: 시드 순 힘 연속은 (가) 플랜트 측정 열로 바꾼다.
  - Q3·보완 범위: 사례 F의 P4 경로를 고친 뒤 돌린다. B2·B3·B4(J4a-15)·J4a-9 결함·X11·사례 F 러너·시험 공백·권고 R1~R9를 사례 재생 전에 모두 보완한다. 보완 뒤 단위 시험·control 재검토·실행 전 감사, 사례 재생 시작은 다시 승인.
  - B5(경로 2 rev 5 판정 도구)의 작성 주체는 436.9 판정 전에 따로 정한다.
