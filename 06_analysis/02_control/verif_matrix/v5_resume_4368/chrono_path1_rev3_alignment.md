# 436.8 Chrono 경로 1 판정 블록 ↔ rev3 R3-G3·G4·G5(D8)·G6·G8·G10 대조 (읽기 전용, 결과 전)

- 작성: cad-expert, 2026-11-13. 맡긴 근거: rev5 R5-A1 마지막 문단("대조표가 '미대조'로 남긴 R3-G3·G4·G5(D8)·G6·G8·G10은 cad-expert가 `git_at_start` 전에 같은 꼴로 대조한다").
- 기준 코드: master `31d543e`(작업 트리, 추적 파일 수정 없음). 규칙: 원판 `v5_resume_4368_rules.md`(9019b405), rev1~rev5. 대조 기준 문장은 rev3 `v5_resume_4368_rules_rev3.md`(dad8dfa6) R3-G3~G6·G8·G10(418~477행).
- 판정 칸: **같음** = 코드가 정의 문장과 같은 값을 낸다. **다름** = 다른 값·범위·경계를 낸다(어떻게를 적음). **코드 없음** = 그 정의를 계산하는 코드가 경로 1에 없다.
- 읽은 것(코드): `04_scripts/02_chrono/run_S9.py`(p3b 블록 전부), `run_S8C.py`(`job_l2b_s8` 요약·`judge` 동작), `run_S6C.py`(`judge` 동작·`R8Series`), `v5_resume_4368_chrono_rows.py`(판정 함수), `run_S8C.py judge`가 부르는 `03_src/outrigger_sim/verify/s8_control.py`·`s6_bundle_c.py`·`s6_control.py`의 해당 함수, `03_src/outrigger_sim/control/two_pressure.py`(`fallback_lock_log`), `c2.py` `_read`, `chrono/run_rows.py`, `chrono/l2b_pad_record_s8.py`. 참고로 기존 G6 Chrono 판정 함수 `04_scripts/03_control/s8/r76_g6_chrono_judge.py`(러너 밖).
- 읽은 것(데이터, 시각 열과 키 이름만): G-S `07_results/S8/r4368gs_D1C2_middle_fdown3.2_Fs4_20261113_020211/D1C2_middle_fdown3.2_Fs4`, `07_results/S6/bundleC_d1c1_r4368gs_D1C1_top_flat_crx3_L1R_20261113_020211/D1C1_top_flat_crx3`(5절). 판정 값은 읽지 않았다.
- 열지 않은 것: 경로 2 도구 폴더(`path2*`), 경로 2 지정 도구(`chrono_t45_replay.py` 등). Chrono 실행 없음.

## 1. 경로 1 판정 블록이 어디 있는가 (사실)

| 엔진·행 | `result.json`에 있는 것 | 등급(통과·실패·FLAG)을 내는 곳 | 근거 |
|---|---|---|---|
| SCM `run_S9.py level`(C-2 S-01·02, C-3 S-03·04, C-4, C-5 SCM 11) | `p3b`(P3-1~P3-9 값과 `checks`의 참·거짓·꼬리표), `p3b_ext`(사건 수) | **러너 안에 행 등급이 없다.** `p3b.checks`는 항목별 값·참거짓이다. G6 관문(G6-1~G6-7, `READY_le_120s`)은 러너 밖 `r76_g6_chrono_judge.py judge`가 낸다 | run_S9 `p3b_records` 5609~5831, `p3b_checks` 5551~5593; r76 314~357 |
| L2b `run_S8C.py run`(C-1 C2-01~08, C-2 C2-03·07, C-5 L2b 24) | `acceptance`(목표 코드·크롤러 자세), `h4`(재고정 결과), `s8_end`(끝 규칙·timeout), `phases`, `stroke` 등 **기록뿐** | `run_S8C.py judge --batch`(4430~4455) → `verify.s8_control.judge_batch` → `s6_bundle_c.judge`·`s6_control` 지표. D8·R40-1/R40-2 행(C1 행)은 여기서 나온다 | run_S8C 2074~2129; s8_control 554~608, 1694~1720, 2415~2421 |
| L1-R `run_S6C.py run`(C-1 C1-09~12, 기록 행) | 기록뿐 | `run_S6C.py judge` → `verify.s6_bundle_c.judge` | run_S6C 4~5, 14 |
| `v5_resume_4368_chrono_rows.py` | – | O-C5 R_c 탐침 절차(`oc5_evaluate`, 5.4)와 G-S 키 확인(`gs-check`)뿐. R3-G 항목을 계산하는 함수는 없다 | 430~469, 1037~1196 |

- 그래서 아래 표에서 "러너"는 `result.json` 블록, "러너 judge"는 `run_S8C.py judge`/`run_S6C.py judge`가 부르는 verify 모듈이다. r76은 기존 G6 판정 함수로, 원판 9.1의 경로 1(러너 안 판정 블록)이 아니라 참고로만 대조했다.

## 2. 항목별 대조

### G3. S-03·S-04의 `stroke_limited_stop` 허용 (rev3 418~422행)

| # | 대상 | 판정 | 내용(줄) |
|---|---|---|---|
| G3-1 | run_S9 p3b (S-03·04) | **코드 없음** | 러너에 `stroke_limited_stop` 분류가 없다. 이 이름은 사례 표 주석(691~704, 854~880행)에만 나온다. `p3b_checks`(5551~5593)에도 `allowed_stop`·안전 정지 조건이 없다. 427.9 조건(첫 FAULT = `FAULT_LIFT_STROKE_LIMIT:soil`, `FAULT_STROKE_END` 없음, 부상 없음, 이탈 뒤 참 F_cyl ≥ F_min, 이동 ≤ 180 bar·포화 없음)을 Chrono 자료로 계산하는 코드는 하네스 모듈 `04_scripts/03_control/s9/soil_guard_stop_rule.py`에만 있고 run_S9는 쓰지 않는다 |
| G3-2 | r76 (참고) | **다름** | `fault = any(FAULT*)`(320행)이면 G6-6 거짓(345행), READY 없으면 READY 의존 관문 네 개를 실패로 센다(56, 309~311행). 안전 정지가 그대로 실패가 된다 |

### G4. S-03·S-04의 READY 한계 (rev3 424~430행)

| # | 대상 | 판정 | 내용(줄) |
|---|---|---|---|
| G4-1 | run_S9 P3-6 한계 | 같음(값) | `p36_ready_limit`(3756~3775): 바닥 경사 0, 패드 B, 뒤 패드 RL·RR = G1 바탕(J1은 FL에만) → "flat, other" 90 s(`P3B_READY_LIMIT_S` 3748행). S-03·04는 평지(`d1_chrono_rows.py` 21·189행). READY 시각 = 첫 `ready` − `t_loop_start_s`(5742~5745행). 값은 `within` 참·거짓뿐이고 "FLAG" 꼬리표는 없다(기록 항목이라 등급 영향 없음) |
| G4-2 | run_S9 G6 관문 READY ≤ 120 s | **코드 없음** | 러너에 없다 |
| G4-3 | r76 (참고) | 같음(값) / 다름(경계) | `READY_le_120s = ready <= 120.0`(46, 348행). 원판 7.6 비교 허용(+1e-9)이 없다 |

### G5. D8 이륙 = rev6 t_lift, P3 이탈 = t_D(R2-5) (rev3 432~436행)

| # | 대상 | 판정 | 내용(줄) |
|---|---|---|---|
| G5-1 | run_S9 P3 t_D | 같음 | `crawler_departure`(3257~3283): `scm_crawler_normal_N` < 0.01 W(`P3A_OFF_FRACTION` 3161행)가 0.1 s(`P3A_OFF_HOLD_S` 3163행) 이어진 첫 구간의 첫 표본, W = `p3b.weight_N`, 1 ms(`STEP_SERIES_S` 3733행). 경계: 지속 판정이 `t[k] − t[start] ≥ 0.1 − 1e-9`(3191행)라 1 ms 격자에서 101표본이 필요하다(R2-5 문장은 표본 셈을 정하지 않음, 6절 확인 필요 C-4) |
| G5-2 | L2b·L1-R D8 이륙(러너 judge) | **다름** | `s6_control._times`(232~247): t_lift = `record.npz` `F_crawler[:,2] > 0`인 **마지막** 표본의 다음 표본 시각. 정의(rev6 5 t_lift)와 네 곳이 다르다: ① 첫 표본이 아니라 마지막 양수 뒤(재접촉이 있으면 늦어짐), ② 1 ms가 아니라 `record.npz` 제어 주기 행(10 Hz, runner.py 465~467행, G-S `record.npz` dt 0.1 s), ③ `pads.npz` `crawler_normal_N`(바닥 법선 성분)이 아니라 세계 z 성분, ④ 단계 조건(`idle`·`check`·`touch` 제외)이 없다. 이 시각이 D8 최소(`_force_metrics` 773~786), "D8 no pad lift-off"(s6_bundle_c 1094~1096), R40-1/R40-2 C1 행(s8_control 1719~1720)의 창 시작이다 |
| G5-3 | SCM D8(C-4 등) | **코드 없음** | run_S9에 D8 t_lift가 없다(P3a 열린 루프 `p3a_lift_records`는 별개 규칙) |
| G5-4 | L1-R 입력 | 코드 없음(입력) | L1-R `pads.npz`에 `crawler_normal_N`이 없다(G-S 키 목록: `F_cyl`, `N`, `T`, … 뿐). 1 ms t_lift의 입력이 없다 |

### G6. R40-2 문턱 F_min + 5 kN = 14,414.589 N, 보류 행 = 판정 불가 (rev3 438~444행)

| # | 대상 | 판정 | 내용(줄) |
|---|---|---|---|
| G6-1 | 문턱 | 같음 | `c1_row(..., (f_min + D8_MARGIN_N) / 1e3)`(s8_control 2420행), `D8_MARGIN_N = 5000.0`(261행), `f_min` = 그 실행 YAML `control.F_min_cylinder_N`(s6_control 304~307·585행) = 9,414.58911 N(`02_params/rexome33.yaml` 829행). 문턱 14,414.589 N |
| G6-2 | 보류 세 조건 | 같음(조건) / 확인 필요(원값) | `c1_row`(584~608): 원값 최소 < 문턱 ∧ 그 시각이 이륙 뒤 ≤ 8 s(`LIFTOFF_WINDOW_S` 257행) ∧ 같은 8 s 구간의 1 s 중심 평균 최소 ≥ 문턱 ∧ 강체 크롤러(`lift_transient_rules_apply` 924~928행) → `kind` "hold", `passed` None. 다만 "원값"이 `judged_force_min`(1589~1600행)이다: 부상 표본(20 ms N ≤ 0, S8-A2)은 1 ms 최소 대신 20 ms 평균을 쓴다. rev3 문장은 "원값 최소"만 적었다 |
| G6-3 | 보류 = 판정 불가 | 같음(분류) / **코드 없음**(해제) | 보류 행은 `passed` None, `meta.hold` 수로 따로 센다(5478~5481행). 원문 해제 절차(같은 바닥 L1 짝(F_s 0)과 짝 차 자릿수, `d1_selection_rules.md` 8절)를 하는 코드는 없다(노트 문장만, 600~602행) |
| G6-4 | 이륙 시각 의존 | 다름(파생) | "이륙 뒤 8 s"의 이륙이 G5-2의 t_lift다. G5-2가 다르면 보류 판정 창도 다르다 |
| G6-5 | 러너 `result.json` | 코드 없음 | L2b 러너 요약에는 C1 행이 없다. `run_S8C.py judge`에서만 나온다 |

### G8. 377 강등 문턱 = F_min (rev3 455~459행)

| # | 대상 | 판정 | 내용(줄) |
|---|---|---|---|
| G8-1 | run_S9 p3b | **코드 없음** | `P3-8_false_triggers`(5752~5785)는 LOC 전 사건 목록·수와 `within`만 낸다. 재접근 시작 다리의 참 최소(시작 ~ LOC + 1 s)와 FAULT 0을 묶어 `P3-8_demoted`로 내리는 코드가 없다. `pre_liftoff_min_F_cyl`(3449~3469)은 다른 창(1.4 F_min 첫 초과 ~ 이탈)이다 |
| G8-2 | r76 (참고) | 코드 없음 | `G6-7_preloc = P3-8.within`(347행), 거짓이면 꼬리표 `P3-8_needs_leg_minimum`만 붙인다(350~352행) |

### G10. 경계 정의 여섯 가지 (rev3 468~477행)

| # | 정의 | 대상 | 판정 | 내용(줄) |
|---|---|---|---|---|
| G10-1 | Q-10 P3-8 구간 = 실행 시작 ~ min(첫 확정 LOC(취소 포함), 첫 토양 모드 시작), 둘 다 없으면 전체 | run_S9 | **다름** | `within`(G6-7 입력) = 최종 LOC `t_loc_fin` 전 사건 0(5773·5780행). ① 첫 LOC가 아니라 최종 LOC(취소가 있으면 더 길다), ② 토양 모드 시작(`soil_mode_start`)을 끝으로 쓰지 않는다. `within_first`(첫 LOC 기준, 5774·5785행)는 ①만 맞고 ②가 없다. 둘 다 없으면 전체(5761행 `inf`)는 같다 |
| G10-2 | Q-11 재접촉 지속 = 연속 ≥ 0.01 W 표본 수 × 1 ms | run_S9 | 같음 / 다름(끝 경계) | `recontact_events`(3331~3391): 문턱 `cn >= 0.01 W`(3356행), 끊기면 다른 사건. 지속 = 다음 미만 표본 시각 − 첫 표본(3369~3370행) = 표본 수 × 1 ms(1 ms 격자). 실행 끝까지 하중 중이면 `t[-1] − t_start` = (표본 수 − 1) × 1 ms로 1 ms 짧다 |
| G10-3 | Q-12 P3-2 순서 조항 = LOC 있고 (DONE 없음 ∨ 최종 LOC < 첫 DONE) | run_S9 | 다름(경계) | `t_loc <= t_done + 1e-9`(4906행)로 같은 시각을 참으로 본다(정의는 엄격 <). LOC 없으면 거짓(4900~4902행)은 같다. 최종 LOC를 쓴다(5650~5652행) |
| G10-4 | Q-13 이동 압력 = u_applied ≠ 0(1e-9) 표본, F_cyl/A_p, 사건 행은 J-5·U58 | L2b·L1-R 러너 judge | **다름** | `moving = |u_applied| > 1e-6`(s6_control 1423행, `MOVING_EPS_M_S` 812행). 문턱이 1e-9가 아니라 1e-6 m/s다. 표본은 `record.npz` 제어 주기 행(10 Hz)의 `u_applied`·`F_cyl`(1424행)이다(정의는 표본 주기를 정하지 않음, 6절 C-5). 사건 행: 창 밖 `u_applied > 1e-6` 신장만, 창 안 헤드 F/A_p 모든 상태 ≤ 350 bar(1376~1390, 1347~1361행) = J-5·U58 꼴은 같고 문턱만 1e-6 |
| G10-5 | 〃 | SCM run_S9 | **코드 없음** | 이동 압력 계산이 없다(`head_area`는 P3-7 순 힘 재구성에만, 5501행). 1 ms `step_series.npz`에는 `u_applied`가 없다(키 4352~4358행) |
| G10-6 | Q-14 부상 = 패드 법선 접촉력(진값) ≤ 0인 1 ms 표본 | L2b 러너 judge | 같음 | "D8 no pad lift-off" = D8 이륙 뒤 `pads.npz` `N` 최소 > 0(s6_bundle_c 1094~1096, s6_control 787행). 구간 시작은 G5-2 t_lift(파생 차이). `airborne`(20 ms N ≤ 0, l2b_pad_record_s8 204행)은 S8-A2 힘 대체용이고 부상 판정에 쓰지 않는다 |
| G10-7 | 〃 | SCM run_S9 | **코드 없음** | `scm_pad_normal_N`은 첫 접지 시각에만 쓴다(5755~5758행). 부상 판정이 없다 |
| G10-8 | Q-17 P3-2 하중 조항은 최종 LOC에만, 취소된 LOC가 하중 중이면 기록 | run_S9 | 같음(대상) / 다름(경계) / 코드 없음(기록) | 최종 LOC에서 `cn[k] >= 0.01 W`면 하중으로 본다(4907행). 정의는 "> 0.01 W"라 같은 값에서 갈린다. 취소된 LOC 시각은 `loc_timeline.revoked_loc_s`(4958~4999행)에 있으나 그 시각의 크롤러 법선·하중 여부 기록은 없다 |

## 3. "다름"·"코드 없음" 목록과 Chrono 경로 1 집계 새 판이 할 일

러너는 고치지 않는다(rev5 R5-A1). 새 판은 판정 블록·시계열을 읽어 rev3 정의로 다시 정한다. 이름 제안: `04_scripts/02_chrono/chrono_rows_judge_4368.py`(R5-A1 요건 5의 `_4368` 꼴). 요건 1~5(입출력 인자, `git diff --no-index` 공개 대상 = `r76_g6_chrono_judge.py`·`verify/s8_control.py` C1 행·`verify/s6_control.py` `_times`, `git_at_start` 전 커밋, 단위 시험)는 같다.

| # | 항목 | 지금 | 새 판이 할 일(입력) |
|---|---|---|---|
| N-1 | G3-1·G3-2 S-03·04 안전 정지 | 분류 없음 / 실패로 셈 | 427.9 조건 1~5를 Chrono 자료로 계산한다. 첫 `FAULT*` 사건(`result.json` `events`) = `FAULT_LIFT_STROKE_LIMIT:soil:…`, `FAULT_STROKE_END` 없음, 부상 없음(N-8 정의), t_D ~ 끝 `step_series.npz` `F_cyl_N` 최소 ≥ 9,414.589 N, 이동 ≤ 180 bar·포화 없음(N-7 정의). 모두 참이면 행 판정 `stroke_limited_stop` = 원판 `allowed_stop`(실패 아님). 하나라도 거짓이면 실패. 이 행의 READY 의존 관문은 READY가 없어도 "안전 정지"로 처리하고 그 사실을 적는다 |
| N-2 | G4-1 P3-6 | `within`만 | `p3b.P3-6_ready.within` 거짓 → FLAG(기록) 꼬리표. 한계 90 s(`limit_s`)를 그대로 옮겨 적는다 |
| N-3 | G4-2·G4-3 READY ≤ 120 s | 러너 없음 / r76 허용 없음 | `p3b.P3-6_ready.t_ready_after_loop_start_s ≤ 120 + 1e-9`(원판 7.6)를 G6 관문으로 판정한다 |
| N-4 | G5-2 D8 t_lift(L2b) | 10 Hz, 마지막 양수 뒤, 세계 z, 단계 무시 | `pads.npz` `t`·`crawler_normal_N`(1 ms)에서 "단계 ∉ {idle, check, touch} ∧ ≤ 0인 첫 표본". 단계는 `result.json` `phases`(**t0 기준 상대 시각**, 5절)를 `settings.start_t_s`로 절대 시각으로 바꿔 쓴다. 이 t_lift로 D8 최소·D8 부상·R40-1/R40-2 창을 다시 잡는다 |
| N-5 | G5-3·G5-4 SCM·L1-R D8 t_lift | 없음 / 입력 없음 | SCM: `step_series.npz` `t_s`·`scm_crawler_normal_N`(1 ms)과 `phases`(run_S9는 절대 시각)로 같은 정의. L1-R: 1 ms 입력이 없으므로 처리 규칙이 필요하다(6절 C-1). C1-09~12는 기록 행이다 |
| N-6 | G6-3 R40-2 보류 해제 | 없음 | 보류 행을 `판정 불가`로 세고, 같은 바닥 L1 짝(F_s 0, `d1_selection_rules.md` 8절 행)의 같은 지표와 짝 차 자릿수를 비교해 풀리면 푼다. 못 풀면 그 행을 "멈추고 묻기"로 낸다(rev3 R3-G6) |
| N-7 | G10-4·G10-5 이동 압력 | L2b·L1-R 1e-6 / SCM 없음 | 이동 = `|u_applied| > 1e-9`(0 판정 허용 1e-9)인 표본. L2b·L1-R은 `record.npz` `u_applied`·`F_cyl`, SCM은 `record/record.npz`(run_S9 level도 씀, 5597행 키) `u_applied`·`F_cyl`. 압력 = F_cyl/A_p(다리별 YAML 헤드 면적, `result.json`의 면적 기록 6434행). 사건 행은 J-5·U58(창 밖 신장만, 창 안 ≤ 350 bar). 1 ms로 할지는 6절 C-5 |
| N-8 | G10-7 SCM 부상 | 없음 | `step_series.npz` `scm_pad_normal_N ≤ 0`인 1 ms 표본. 구간은 각 항목 원문대로 |
| N-9 | G8 377 강등 | 없음 | P3-8 구간(N-10) 안 `leg_reapproach_start:<leg>` 사건마다 그 다리의 `step_series.npz` `F_cyl_N` 최소(시작 ~ LOC + 1 s) ≥ 9,414.589 N이고 FAULT(단계 `fault`·`fault_reground` 또는 `FAULT*` 사건) 0이면 FLAG `P3-8_demoted`, 아니면 실패. `relevel_predicted`·`probe_aborted_low_load`는 377 대상이 아니므로 그대로 둔다. "LOC + 1 s"의 LOC는 6절 C-3 |
| N-10 | G10-1 P3-8 구간 | 최종 LOC, 토양 모드 무시 | 끝 = min(`p3b.P3-2_loc.loc_timeline.t_loc_first_s`, `soil_mode_start` 첫 사건). 사건 목록은 `result.json` `events`(절대 시각) |
| N-11 | G10-2 재접촉 지속 | 끝까지 이어지면 1 ms 짧음 | 지속 = 표본 수 × 1 ms로 다시 센다(`step_series.npz`, 문턱 ≥ 0.01 W, 사건 시작은 이탈 확인 뒤) |
| N-12 | G10-3 P3-2 순서 | `≤ + 1e-9` | 최종 LOC < 첫 DONE(엄격)으로 다시 판정. 같은 시각이면 거짓 |
| N-13 | G10-8 P3-2 하중·취소 LOC | `≥`, 취소 LOC 기록 없음 | 최종 LOC에서 `scm_crawler_normal_N > 0.01 W`면 하중. `revoked_loc_s` 각 시각의 크롤러 법선과 하중 여부를 기록한다 |
| N-14 | G6-4 파생 | – | N-4를 쓴 뒤 C1 행(보류 포함)을 다시 계산한다. 원값 정의는 6절 C-2 결정에 따른다 |

- 새 판은 러너 값과 다시 정한 값이 다른 행 수를 항목 번호(N-x)와 함께 판정서에 적는다(R5-A3와 같은 꼴). 위 항목은 R5-A3 D-01~D-25에 없으므로, 판정서 공개 표에 이어서 적는 것을 권한다(번호는 control 몫).

## 4. 같음으로 확인한 것 (요약)

- G5-1 P3 t_D(0.01 W, 0.1 s, 1 ms, W = `p3b.weight_N`).
- G6-1 R40-2 문턱 14,414.589 N(YAML F_min + 5,000 N), G6-2 보류 세 조건과 강체 크롤러 조건.
- G4-1 S-03·04 P3-6 한계 90 s와 READY 기준점(폐루프 시작).
- G10-6 L2b D8 부상(1 ms `N` ≤ 0).
- G10-2 재접촉 사건 분리·문턱(끝 경계만 다름), G10-8 하중 조항 대상(최종 LOC).

## 5. R5-B1 시각 원점 (`fallback_lock_log` ↔ `pads.npz`·`r8_series` `t`)

**결론: 같은 원점(Chrono `ChSystem` 시각, 절대)이다.** 코드와 G-S 두 행으로 확인했다. 단 G-S 두 행 모두 `fallback_lock_log`가 빈 목록이라 창 값 자체는 대조하지 못했다.

코드 근거:

| 열 | 값의 출처 | 줄 |
|---|---|---|
| `fallback_lock_log[].t_start_s`·`window_end_s` | `_open_lock_stretch(leg, stretch, t_s)`의 `t_s`; `start_t_s = t_s`, `window_end_s = t_s + τ_v ln(...) + t_c + T` | two_pressure.py 2540~2556, `summary` 1088~1102, 메타 2825 |
| 위 `t_s` | `self._pressures.read(measurements.t_s, ...)` | c2.py 5328~5329 |
| `measurements.t_s` | 러너 평균기 표본 시각 = 엔진 시각 | runner.py 449~467 |
| `r8_series.npz` `t` | `meas.t_s`(같은 측정 객체) | run_S6C.py 1651(L2b·L1-R), chrono/run_rows.py 67(run_S9) |
| `pads.npz` `t` (L2b) | `model.system.GetChTime()`(스텝 훅) | l2b_pad_record_s8.py 92 |
| `step_series.npz` `t_s` (SCM) | `m.system.GetChTime()` | run_S9.py 4371 |

G-S 자료(scratchpad 스크립트 `gs_time_origin.py`, Chrono-dev `python -I -B`, 읽기만):

| 행 | `settings.start_t_s` [s] | `pads.npz` t[0] / dt | `r8_series` t[0] / dt | r8 t가 pads 격자 위 | (r8 t − start_t_s)/0.1의 정수 차 최대 | `fallback_lock_log` |
|---|---|---|---|---|---|---|
| L2b `D1C2_middle_fdown3.2_Fs4` | 3.0000000000019 | 3.001 / 1 ms (89,300) | 3.1 / 0.1 s (893) | 예(최대 차 0.0 s) | 1.9e-8 | 빈 목록 |
| L1-R `D1C1_top_flat_crx3` | 68.5000000000269 | 68.501 / 1 ms (74,000) | 68.6 / 0.1 s (740) | 예(최대 차 0.0 s) | 2.5e-8 | 빈 목록 |

- 첫 공통 시각: r8 t[0] = start_t_s + 1 주기(0.1 s)이고 같은 값이 pads `t`에 있다(R5-B1의 G-S 확인 문장 "두 `t` 열의 첫 공통 시각이 정수 주기로 맞음"을 만족). 정수 차 1.9e-8~2.5e-8는 시각 누적 부동소수 오차다(R4/7.6의 1e-9보다 크므로, 주기 정수성 판정을 1e-9로 하면 거짓이 된다. 6절 C-6).
- **함정(경로 2·새 판 공통)**: `run_S8C`·`run_S6C`의 `result.json` `phases`는 **t0 기준 상대 시각**이다(`phases.append((meas.t_s - t0, ...))`, run_S8C 1876행; G-S에서 첫 `check` 0.1 s). 반면 `controller_events.json`(G-S 첫 사건 7.6 s), `fallback_lock_log`, `pads.npz`, `r8_series`는 절대 시각이다. 단계 창을 쓸 때 `settings.start_t_s`를 더해야 한다. `run_S9`의 `phases`는 절대 시각이다(6273행).
- 기록 범위: `fallback_lock_log`에는 **닫힌** 잠금 구간만, 닫힐 때 그 다리가 `FALLBACK` 상태일 때만 들어간다(2581~2588행). 실행 끝까지 열린 구간은 빠진다. "실제 대체 다리 = 목록의 `leg` 집합"(R5-B1)이 이 경우 다리를 놓칠 수 있다(6절 C-7).
- SCM G-S 행(run_S9 level)은 이 배치에 없다(`012403` 배치의 SCM 행은 열린 루프 `machine`). SCM은 코드로만 확인했다.

## 6. 확인 필요

| # | 질문 | 왜 |
|---|---|---|
| C-1 | L1-R(C1-09~12) D8 t_lift: 1 ms `crawler_normal_N`이 없다. `record.npz` `F_crawler`(10 Hz, 세계 z)로 대체할지, t_lift 의존 항목을 `판정 불가`(기록)로 둘지 | rev3 R3-G5 입력(rev6 152행)은 강체를 `pads.npz` `crawler_normal_N`으로만 정했다. L1-R `pads.npz`에는 그 키가 없다 |
| C-2 | R40-2 "원값 최소"에 S8-A2(부상 표본 = 20 ms 평균)를 적용한 값을 쓰는지 | s8_control `judged_force_min`(1589행)은 S8-A2를 적용한다. rev3 문장은 "원값"만 적었다 |
| C-3 | 377의 "LOC + 1 s"의 LOC = 첫 확정 LOC인지 최종 LOC인지 | Q-10은 P3-8 구간 끝을 첫 LOC로 정했다. 377 문장(rev3 R3-G8)은 LOC 종류를 말하지 않는다 |
| C-4 | t_D의 "0.1 s 이상 이어짐"을 표본 수 × 1 ms(100표본)로 보는지, 마지막 − 첫(101표본)으로 보는지 | 코드는 후자(3191행). Q-11은 지속을 전자로 정했다. 결과 차는 최대 1 ms |
| C-5 | Q-13 이동 압력의 표본 주기(10 Hz `record.npz` 행인지, 1 ms인지) | L2b `pads.npz`·SCM `step_series.npz`에는 1 ms `u_applied`가 없다. 1 ms로 하려면 제어 주기 명령의 영차 유지(`command_offset_s` 포함)를 가정해야 한다 |
| C-6 | R5-B1 G-S 확인의 "정수 주기" 비교 허용 | 실측 차 2.5e-8(누적 부동소수). 원판 7.6 1e-9로 하면 거짓이다. 시각을 pads 격자 값과 같음(0.0 s)으로 보는 지금 판독이 맞는지 |
| C-7 | `fallback_lock_log`에 열린 채 끝난 구간이 빠지는 것 | 대체 다리 판정을 `WARN_ROD_PRESSURE_FALLBACK:<다리>` 사건과 함께 볼지(R5-B2와 같은 꼴) |
| C-8 | S-01·S-02(C-2)도 `stroke_limited_stop` 허용 행이다(`d1_selection_rules.md` 11절). 러너에 분류가 없는 것은 G3와 같다 | rev3 R3-G3는 S-03·04만 말한다. 새 판 N-1을 S-01·02에도 쓰는지 |
| C-9 | SGS 조건 3(부상 없음)의 정의 | 하네스 모듈은 "참 F_cyl + 로드 무게가 0에 닿지 않음", rev3 Q-14는 "패드 법선 ≤ 0". 새 판 N-1은 Q-14를 쓰는 것으로 적었다 |
