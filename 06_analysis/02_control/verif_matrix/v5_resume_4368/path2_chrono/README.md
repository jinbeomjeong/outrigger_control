# 436.8 경로 2 — Chrono C-1~C-5 판정 블록 재계산 (+ C-8 m·시간 기록)

- 작성: control-expert(새 인스턴스, 2026-11-13). 이 작성자는 경로 1 도구를 만들거나 고친 적이 없다(아래 "독립성 공개").
- 규칙: 원판 `v5_resume_4368_rules.md`(9019b405), rev1(d9094fda), rev2(497e4614, 우선). 9.1 표 C-1~C-5 행의 경로 2 = "`series.npz`·`r8_series` 재계산"(rev1 RV1-10 h: SCM `step_series.npz`·`r8_series.npz`, L2b·L1-R `r8_series.npz`·`s8_series.npz`).
- 이 도구는 결과의 **판정 블록을 읽지 않는다**. 원 시계열·단계·사건·설정·argv에서 다시 계산한다. 예외는 규칙이 이름으로 지정한 두 키다: `p3b.weight_N`(rev2 R2-5의 W), `p3b_ext.start_condition.crawler_attitude_deg`(원판 9.1 C-8 "기록된 크롤러 자세에서 2절 식으로 재계산").

## 1. 실행

dynamics-dev 활성화, PowerShell, E코어(0x00FF0000)로 돌렸다.

```powershell
[System.Diagnostics.Process]::GetCurrentProcess().ProcessorAffinity = [IntPtr]0x00FF0000
$d = "<repo>\06_analysis\02_control\verif_matrix\v5_resume_4368\path2_chrono"
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B "$d\p2_chrono.py" seal
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B "$d\p2_chrono.py" judge --bundle C-1 `
    --batch <repo>\07_results\S9\batch_V5-RESUME-K1-C1_<stamp>\batch.json --out <출력>\p2_C1.json
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B "$d\test_p2_synthetic.py" --tmp <빈 폴더>
```

- `judge`는 `batch.json`의 `cases[]` 가운데 `criteria_id`(최상위 또는 `r4368.criteria_id`)가 묶음과 같고 G-S가 아닌 행만 판정한다. SCM 행 폴더 = `batch.json` 폴더/`case`. L2b·L1-R 행 폴더 = `07_results/S8|S6/*<argv --tag>*/<argv --only>/`(정확히 1개가 아니면 종료 2, `--row-dir CASE=PATH`로 지정).
- 종료: 0 = 묶음 `통과`·`기록 완료`, 1 = `미달`·`판정 불가`·`기록 불완전`·멈춤 있음, 2 = 입력·봉인 오류(S-1), 3 = 내부 오류. 마지막 줄 JSON에 `tool_sha256`(공통 4파일 + 묶음 모듈, 파일별 sha를 이름순 "이름 sha\n"로 이은 문자열의 sha256), `out_sha256`(출력 파일 바이트).
- 봉인 대조(원판 8.2 S-1, rev2 R2-9): 원판·rev1·rev2는 raw sha만, 부록 A 파일(d1 규칙·rev1, v5 rev6·12·12a·12b, `las_p5r4_k1_judgement.md`)은 raw가 다르면 CRLF→LF 정규화 sha를 보고 같으면 통과 + "CRLF 변환만 다름" 공개. 명세·YAML sha는 기록만.

## 2. 파일과 규칙 절 ↔ 함수

| 파일 | 역할 |
|---|---|
| `p2_rules.py` | 봉인 대조, 문턱 숫자(각 줄에 원문 절), 7.6 비교 허용(`ge`·`lt`·`gt`·`le`) |
| `p2_core.py` | 행 적재(`load_row`), 시각·항목 계산 |
| `p2_kinds.py` | 행 종류별 항목 묶음(D8·P, P3/G6, C-5), 묶음 상태(8.1) |
| `p2_b_c1.py`~`p2_b_c5.py`, `p2_b_c8.py` | 묶음별 행 종류 대응과 기대 행 수 |
| `p2_chrono.py` | CLI |
| `test_p2_synthetic.py` | 합성 입력 자체 시험(실제 결과를 읽지 않음) |

| 규칙 절 | 함수 | 정의(이 도구가 쓴 문장) |
|---|---|---|
| 원판 7.6 | `p2_rules.ge/lt/gt/le` | 비교 허용 10⁻⁹(그 단위) |
| 명세 284 P3-2 t_D, rev2 R2-5 | `p2_core.t_departure` | 폐루프 시작 뒤 크롤러 1 ms 법선 < 0.01 W가 0.1 s 이상 이어지는 첫 구간의 첫 표본. W = `p3b.weight_N` |
| v5 rev6 5 t_lift | `t_lift`, `t_lift_sus` | 단계가 idle·check·touch가 아니고 크롤러 ≤ 0인 첫 1 ms 표본, 1 ms 기록이 없으면 10 Hz 괄호(t_a + 1 ms) |
| 424.8.1 최종 LOC | `loc_times` | 뒤에 `INFO_LOC_REVOKED`가 없는 마지막 `crawler_liftoff_confirmed` |
| P3-1 + U-S9-G6d + 423.3 Q-G | `recontacts`, `classify_recontact`, `p3_1` | t_D 뒤 ≥ 0.01 W 구간을 사건으로. 최종 LOC 이전 시작: 지속 ≤ 0.5 s ∧ LOC 전 종료 ∧ 최대 ≤ 0.15 W → transient FLAG. LOC 뒤: 시작 ≤ LOC + 1.0 s ∧ 지속 ≤ 0.1 s ∧ 최대 ≤ 1.2 × 0.01 W → chatter FLAG. READY 뒤 시작·LOC 없음 → 엄격 실패. READY ~ +10 s 크롤러 최대 > 0 → 실패, 창이 안 차면 판정 불가 |
| P3-2 + 419.8/419.8.1 + 424.8.1 | `p3_2`, `reapproach_intervals` | 최종 LOC 존재 ∧ 첫 DONE 전 ∧ (t_LOC − 0.1, t_LOC] 크롤러 최대 < 0.01 W ∧ t_LOC − t_D ≤ T_lim. T_lim = 0.010/(0.25 v_max) + 1.0 s(YAML v_max, 규칙 표기 2.9 s는 기록). 시간만 넘으면 419.8 다섯 조건(창 재시작 포함 재접근, 재접근 끝 기준 지연, 거짓 LOC 아님, P3-3·FAULT 0, 순서) 또는 424.8.1 다섯 조건이 모두 참일 때 FLAG |
| P3-3 | `p3_3`, `min_force_after` | [t_D, 끝] 다리별 1 ms 참 F_cyl 최소 ≥ F_min(YAML) |
| P3-4 + 284.1 + 433.6 | `creep_stop_times`, `p3_4` | 1.0 s 후향 침하 속도(`pad_sinkage_geometric_m` 차분) \|v\| < 0.1 mm/s 네 패드가 끝까지 이어지는 마지막 구간 시작, 없으면 부호 판정 + `creep_vibration_suspect`. 창 = [max(그 시각, 마지막 READY 진입), 끝], 창 안 \|roll\|·\|pitch\| 최대 ≤ 0.2°. 창 < 5 s → `window_short`(판정 불가) |
| P3-5 | `p3_5` | 첫 READY ~ 끝 `s9_rows.rut_clearance_m` 최소 ≥ 25 mm, 실행 전체 `s_motor_m` 최대 ≤ 0.6848 m |
| P3-6, d1 rev1 | `ready_item` | 첫 READY 진입 − 폐루프 시작 ≤ 한계 |
| P3-8 + 377 | `p3_8` | min(첫 LOC, 토양 모드 시작) 전 `leg_reapproach_start`·`relevel_predicted`·`probe_aborted_low_load` 0. G6 행만 377 강등: 시작 다리 [시작, 첫 LOC + 1 s] 최소 ≥ F_min ∧ FAULT 0이면 FLAG |
| P3-9 | `p3_9` | 기록: `leg_reapproach_deferred`마다 보류 다리 [보류, 다음 재접근 시작 + 0.3 s] 최소 |
| G6-6 | `items_p3(g6=True)` | FAULT 0 ∧ READY ≤ 120 s |
| 398.1 SL-1, 427.12.5 SA-4 | `items_p3`, `stop_classification` | `WARN_LIFT_STROKE_LIMITED` → FAULT 0·부상 0·P3-1·P3-3·P3-4 통과면 P3-5 완화. `FAULT_LIFT_STROKE_LIMIT:soil` → SA-4 조건 전부 ∧ 이탈 뒤 정지면 `stroke_limited_stop`(허용 행은 통과), 아니면 실패 |
| 명세 3 항목 2·3·4, d1 11 D8·P | `d8_force`, `d8_end_attitude`, `pressure_item`, `ready_item` | t_lift 뒤 1 ms 최소(L2b·L1-R `F_cyl_min_interval`) ≥ F_min. 마지막 5 s(전부 READY) \|자세 − 목표\| 최대 + 0.02 ≤ 0.2°. 헤드 등가 F_cyl/A_p: 작용 명령 \|u\| > 10⁻⁶ 표본 ≤ 180 bar, 전 표본 ≤ 350 bar. READY 평지 90 / 경사 120 s. FAULT 0 |
| 명세 210.2 R40-2 | `d8_force(rigid_nsc_hold=True)` | L2b 판정 행: 원값 최소 < F_min ∧ 그 시각이 t_lift + 8 s 안 ∧ 같은 8 s의 1 s 중심 이동평균 최소 ≥ 14.41 kN → `hold`(행은 판정 불가) |
| 원판 4.2·6, rev2 R2-3, rev1 RV1-10 a | `identity_scm`, `identity_l2b` | 기록 확인(어긋나면 판정 불가 + S-2/S-3/S-4 검토) |
| 원판 7.2, rev2 R2-1·R2-2 | `k1_classification` | 기록 모순(`would_block`∧¬due, `applied`∧¬due, `applied`∧`would_block`) → S-5. `_SKIPPED:order` 수 ≠ 막힘 수 → S-5 |
| v5 rev6 5 H-9 | `items_c5` | M2 켬(`v5_hydraulics.hydraulic_options.m2_law`) 행에서 `hydraulics_record.m2_clip_times_s` 중 t_lift 뒤 잘림 > 0 → H-9 멈춤 |
| v5 rev6 6 (기록) | `items_c5` | `law_locked` 0↔1 전이 수(−1은 잠김으로 읽음) |
| 원판 7.4, rev2 R2-5·R2-6 | `p2_b_c8.judge_row`, `p2_b_c4` | m = t ≥ t_D 다리별 최소의 네 다리 최소 → 멈춤 / 여유 기록 / 기록. F<F_min·F<F_min+2 kN 시간 = [t_D, t_D + 8 s] 표본 수 × 1 ms(끝까지 창은 기록) |

## 3. 묶음별 대응

| 묶음 | 행 | 판정 항목(경로 2) | 등급에 넣는 항목 |
|---|---|---|---|
| C-1 | C2-01·02·04·05·06·08 L2b | D8·P | F·끝 자세·READY·압력·FAULT 0·기록 확인·K1 분류 |
| C-1 | C1-09~12 L1-R | D8·P(기록) | 기록 행 |
| C-2 | C2-03·07 L2b / S-01·02 SCM / 기준선 추가 / PS-c | D8·P / P3 + READY 120 s + `stroke_limited_stop` 허용 / 같은 계열 / E-5만 | 고정 4행 정확히 1번씩(rev2 R2-8), 추가 ≤ 4, PS-c ≤ 2, 합 4~10 |
| C-3 | S-03·04 SCM | P3 + G6(P3-6 90 s는 기록) | 2행 |
| C-4 | 4행 SCM 혼합 | D8 + G6 + P3-3 + R_c + 8 s 창 시간 + K1(끔 팔 'LAS 없음') | 기록 묶음 |
| C-5 | 35행 | t_lift·H-9·잠금 전이·K1만. **T4-0·T4·T5·J11 창·J-P3·D2는 만들지 않았다** | 모든 행 판정 불가 |
| C-8 | O-C5 2행 | 7.4 m·처리 칸·시간·R_c | 기록 묶음(배정 밖, rev2 R2-5·R2-6을 받아 더함) |

## 4. 읽은 것 (원판 9.2, 1.2절 꼴)

- 규칙: 원판 전체, rev1 전체, rev2 전체(코디네이터 통지 뒤, master `b33e686`), `d1_selection_rules.md` 1~64행·145~204행, `d1_selection_rules_rev1.md` 전체, `v5_criteria_rev6.md` 81~200행 + T4·T5·J11 줄 grep, `v5_criteria_rev12.md` 전체, `v5_criteria_rev12a.md` 60~105행, `v5_criteria_rev12b.md` 15~47행.
- 명세 `00_docs/04_control/s6_control_spec.md`(sha `1924ae89…`): 300~345행(S6 항목 1~8), 11010~11075행(284·284.1), 14278~14300행(377), 14795~14812행·15138~15165행(423.3), 15340~15360행(424.8.1), 16940~16975행(419.8), 17246~17270행(426.3), 그리고 grep 결과 줄(D8, 180 bar, 마지막 5 s, 8 s 규칙 210.2, chatter, `window_short`·433.6, `stroke_limited_stop`, 427.12, 17279·17475 줄 등).
- YAML `02_params/rexome33.yaml`의 `head_area_m2`, `max_speed_m_s`, `F_min_cylinder_N` 줄.
- 원 데이터(키 이름·형식 확인, G-S 배치만): `batch_V5-RESUME-K1-GS_20261113_010654`(두 행), `_012403`·`_020211`의 `batch.json`, `07_results/S8/r4368gs_D1C2_middle_fdown3.2_Fs4_20261113_020211/`, `07_results/S6/bundleC_d1c1_r4368gs_D1C1_top_flat_crx3_L1R_20261113_020211/`. 읽은 것: npz 배열 이름·모양, `result.json` 키 트리(값은 기록 필드만: `phases`, `events`, `settings`, `controller_tag`, `expect_controller`, `pad_record`, `runner`, `s9_rows[0]`, `start_condition` 키 이름, `mass_scale.judgement_weights`, `c2_setup.expect_controller`, `hydraulics_record.m2_*`, `v5_hydraulics.hydraulic_options`, `c2_soil`의 두 키, `args` 일부), `controller_events.json` 형식, 시각 기준(쿼터니언 ↔ `roll_pitch_deg` 차 3×10⁻¹²°, L2b·L1-R 단계·사건 시각 = `settings.start_t_s` 기준 상대). G-S 행으로 적재기·항목 함수가 키 결측 없이 도는지만 봤고 값·판정은 출력하지 않았다.
- **보지 않은 것**: `resume4368_judge.py`, `u3_judge_k1.py`, `resume_k1_record.py`, `resume_k1_steps.py`, `gs_check_*.txt`, `chrono_rows_check.json`, `chrono_rows_manifest.json`, `run_S9.py`·`run_S8C.py`·`run_S6C.py`·p3b 판정 함수, `result.json`의 `p3b`(위 `weight_N` 1개 제외)·`p3b_ext`(위 1개 키와 `start_condition` 키 이름 제외)·`acceptance`·`h4`·`c2`·`stroke`·`s8_end` 값, `las_p5r4_k1_judgement.md` 본문(sha만), `03_src` 코드.

### 독립성 공개

- 이 작성자는 rev1·rev2를 쓴 control-expert와 같은 에이전트 정의지만 다른 실행이다. 이 실행에서 경로 1 코드·출력은 열지 않았다.
- 에이전트 메모리 색인(`MEMORY.md`, 일반 함정 목록)이 시작 때 문맥에 들어 있었다. 이 프로젝트 경로 1의 코드·값은 들어 있지 않다.
- `d1_selection_rules_interp.md`(부록 A 밖 해석 문서)의 11행 한 줄을 grep 출력으로 보았다("D8 잠김 ≤ 350 bar = 실행 전체 F_cyl/A_p 최대"). 이 도구의 350 bar 정의(전 표본)는 그 줄과 같다. 그 문서의 나머지는 열지 않았다.
- rev1 머리 6행은 "경로 2는 dynamics-expert"라고 적었고, rev2 R2-0이 Chrono C-1~C-5를 새 control-expert 인스턴스로 다시 배정했다(사용자 결정 2026-11-13).

## 5. 만들지 않은 것 (경로 2 판정 불가로 남음)

| 항목 | 이유 |
|---|---|
| C-5 T4-0·T4·T5·J11 창·J-P3·D2·잠금 창 | 제어기 두 압력 감시기(`TwoPressureMonitor`)의 강제 대체 재생이 필요하다. 독립 재구현은 이번 범위에서 하지 않았다 |
| C-5 짝 비교(VB↔V0, LS−VB, 시드), 재실행↔저장 비트 비교, 12a 플랜트 선행 | 기록 항목이고 "앞 판 규칙"의 짝 정의를 이 판들에서 찾지 못했다 |
| PS-c E-1·E-2·E-3·E-4·E-6·E-7 | 처방 침하 사건 시각·창 W·부상 정의가 결과 기록 이름과 이어지지 않았다 |
| S-01·02 "토양 사건 0.5 s 평균(v5 3.1 ⑦)" | v5 3.1 ⑦ 원문을 읽지 않았다 |
| D8 LAS-b 설정 9값 대조 | 프리셋 값이 규칙 문장에 없다 |
| 424.11.2 "조건 1~6"의 6번째 조건 | 원문 위치를 찾지 못했다(424.8.1의 다섯 조건만 구현) |

## 6. 확인 필요 (rev3 후보)

| # | 곳 | 이 도구의 읽기 | 묻는 것 |
|---|---|---|---|
| Q-1 | C-5 9.1 경로 2 | T4·T5·J-P3·D2는 만들지 않아 C-5 행 전부 판정 불가 | C-5 경로 2의 범위(감시기 독립 재구현을 누가 하는가, 또는 경로 2를 t_lift·H-9·전이 기록으로 좁히는가). 그대로면 C-5는 S-13에 준해 판정 불가 |
| Q-2 | RV1-10 h | L2b·L1-R의 1 ms 참 F_cyl·크롤러·자세는 `r8_series`·`s8_series`(10 Hz)에 없어 `pads.npz`(`F_cyl_min_interval`, `F_cyl`, `crawler_normal_N`, `body_quat_wxyz`, `N`, `law_locked`)와 `record/record.npz`(L1-R 자세·크롤러 10 Hz)를 읽었다 | 이 두 파일을 경로 2 입력으로 인정하는가 |
| Q-3 | d1 11 S-03·04 | H-S-A처럼 `stroke_limited_stop` 허용 | S-03·04 행에 허용이 적혀 있지 않다. 허용인가 |
| Q-4 | d1 11 S-03·04 READY | P3-6(90 s)은 기록, G6-6에서 READY ≤ 120 s 판정 | rev1이 H-S-A G1 평지를 90 s로 정했는데 Chrono S-03·04에도 적용하는가 |
| Q-5 | D8 "이륙" | L2b·L1-R·SCM 모두 rev6 5 t_lift(단계 조건 + 크롤러 ≤ 0 첫 표본) | 명세 3 "법선력 합이 0이 된 첫 시각"·P3 t_D 중 무엇인가 |
| Q-6 | R40-2 | 느린 성분 문턱 14.41 kN(문자 그대로), `hold` 행은 판정 불가 | 현 F_min 기준(F_min + 5 kN = 14.415 kN)인가, `hold` 행의 등급은 무엇인가 |
| Q-7 | 433.6 `window_short` | 통과로 세지 않으므로 판정 불가 | d1 3절 "FLAG는 pass"와 충돌. 등급은 무엇인가 |
| Q-8 | 377 강등 문턱 | ≥ F_min(377)과 ≥ 14.4 kN(17279행 "424.11.2와 같음")이 갈리면 판정 불가 | 어느 문턱인가 |
| Q-9 | P3-4 장착 몫 | P3-4는 창 최대 ≤ 0.2°(장착 몫을 더하지 않음, 284.1 `sensor_allowance_left_deg` 식으로 읽음). D8 끝 자세는 + 0.02° | 맞는가 |
| Q-10 | P3-8 구간 | min(첫 LOC(취소된 것 포함), 토양 모드 시작) 전. 둘 다 없으면 실행 전체 | 맞는가 |
| Q-11 | 재접촉 지속 | (마지막 표본 − 첫 표본 + 1 ms) | 표본 수 × 1 ms로 맞는가 |
| Q-12 | P3-2 순서 | DONE이 없으면 순서 조항 참 | 맞는가 |
| Q-13 | 이동 압력 | 작용 명령(발령 `issued_u`가 다음 주기를 구동) \|u\| > 10⁻⁶을 이동으로, 압력 = F_cyl/A_p. 밸브 지연 꼬리는 이동으로 세지 않는다. L2b `head_pressure`·`law_locked`는 쓰지 않는다 | 맞는가 |
| Q-14 | 부상 | t_D 뒤 패드 법선 ≤ 0 표본(SCM `scm_pad_normal_N`, L2b `N`) | 부상 정의 원문 |
| Q-15 | 배정 | C-8은 배정 밖이지만 rev2 R2-5·R2-6을 받아 `p2_b_c8.py`로 더했다. C-6·C-7(R2-4)은 9.1이 경로 2를 `openloop_compare.py analyse`로 정해 만들지 않았다 | C-8을 이 도구로 낼지, C-6·C-7 경로 2 담당 |
| Q-16 | 424.11.2 "조건 1~6" | 424.8.1 다섯 조건만 구현 | 6번째 조건 원문 |
| Q-17 | P3-2 하중 조항 | 최종 LOC 주기만 본다(취소된 LOC는 LOC로 보지 않음, 424.8.1) | 원 표 "크롤러가 하중을 진 동안 LOC 0"을 취소된 LOC에도 적용하는가 |
| Q-18 | rev2 R2-5 W | `p3b.weight_N`을 읽는다(판정 블록 안의 키 1개). `mass_scale.judgement_weights.weight_N`과 다르면 기록 | 판정 블록 키 1개 읽기를 독립성 위반으로 보지 않는가 |
