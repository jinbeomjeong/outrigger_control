# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev4 (재집계 입력의 출처: Chrono 감시기·PS-c·r79 관문, 하네스 기록 필드, 결과 전, 봉인)

- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev4.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev4_seal_candidate_draft.md`와 1·3·5·7행만 다르다.
- 원판 `v5_resume_4368_rules.md`(sha256 `9019b405b7a196f28a756e7ca91f443f6241a58bd8e1eee0361483066cb19524`), rev1(`d9094fda104e25ac7eb7aea44d7c34d8215a839fc3771aa50b224d43082f02c7`), rev2(`497e4614d6780c3201027b3946e3c21da05e2fefe9a3609436bc35ea664c3199`), rev3(`dad8dfa68da7a988971f4d687706465289ec7dd95d09079c92215c64e5eae557`)는 고치지 않는다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 앞 판 그대로다.
- **시점: 436.8 본 실행 결과가 없을 때(봉인 2026-11-13 03:47:45 +09:00, 봉인 커밋 9ce2fdc).** 436.8 본 묶음과 0단계 T-3K는 한 줄·한 행도 돌지 않았다. 있는 것은 G-S 실행뿐이다(R4-0).
- 작성: control-expert, 2026-11-13. 기준 master `9ce2fdc`(rev3 봉인 커밋). 계기: rev3 봉인 뒤 Chrono 경로 2 작성자(N-1·N-2·N-4), H-6~H-10 경로 2 작성자(Q-R1~Q-R7), 하네스 경로 2 작성자(dynamics-expert, rev3 R3-A2·A3·B6·C5·K-0)가 낸 막힘.
- **봉인본이다.** 사용자 결정 Q-R4-1 = C(사용자 결정 2026-11-13)는 R4-9 결정 표와 R4-A에 반영했다.
- **바꾸지 않는 것**: 숫자 문턱, 등급과 우선순위, 멈춤 조건의 뜻, 묶음 범위와 행 목록, 사전 예측 값, 두 경로 요건(원판 9.2), rev3의 세 층 결정(Q-C1·Q-E3 = A). 이 판은 rev3 R3-G1·R3-E3의 "재집계" 층이 **무엇을 입력으로 읽는지**와 빠진 기록 필드만 정한다.

## R4-0. 결과 전 근거와 공개

- 2026-11-13 main checkout(`9ce2fdc`) 확인: `v5/resume_k1/`, `v5_rerun/las_k1/`, `v5/las/t3_k1/`이 없다. G-S 실행만 있다. `07_results/S9/batch_V5-RESUME-K1-GS_*` 3개, `07_results/S8/r4368gs_*` 2개, `07_results/S6/bundleC_d1c1_r4368gs_*` 2개다.
- 읽은 것:
  - 규칙: v5 기준 원판 10절, 개정 6 4~6절·14.5절(389~390행), 개정 7 1~4절, 개정 8 3.2절(42·68·71행), 개정 9 3.1~3.2절·109행, 개정 11 28행, 개정 12 70행.
  - 명세 405~407절(14720~14752행), 426.3절(17246~17268행).
  - 경로 2 README 두 개의 확인 필요 표(Chrono `path2_chrono/README.md` 질문 요약은 메인 세션 전달분, H-6~H-10 `path2_v5c/README.md` Q-R1~Q-R7 원문). 경로 2 도구 코드는 열지 않았다.
  - **필드 이름만**:
    - L2b G-S 행 `07_results/S8/r4368gs_D1C2_middle_fdown3.2_Fs4_20261113_020211/D1C2_middle_fdown3.2_Fs4/`의 `result.json` 키 경로와 그 폴더의 npz 배열 이름
    - 저장 r79 잡음 기록 한 줄(`v5/noise_vb/…partial.jsonl` 첫 줄)의 키 경로
    - 저장 r79 판정 파일 `s8/rev79/fin_r79_L3L4_final_judgement.json`의 키 경로
    - 값은 읽지 않았다.
  - 도구 이력: `git log f46b5ab..9ce2fdc`로 아래 판정 도구 파일의 커밋을 조회했다. 결과는 0건이다(436.8 규칙 봉인 뒤 바뀌지 않음).
    - `04_scripts/04_hydraulic/coupled/chrono_t45_replay.py`
    - `03_src/outrigger_sim/control/contact_replay.py`
    - `04_scripts/03_control/s8/r79_sensor_judge.py`
    - `04_scripts/03_control/s8/r79_L3L4_final.py`
- 사실 확인:
  - L2b 행 `result.json`에는 T4-0·T4·T5 항목 결과 키가 없다. 이 값들은 실행 중에 생기지 않는다. 실행 뒤 감시기 재생(개정 6 4.1 "재생기 `contact_replay.replay_fallback_monitor`")으로만 계산된다.
  - J-P3의 입력인 `hydraulics_record.extend_bound_check`(`rule`, `reads`, `breach_reads`, `locked_*`, `retract_*`)는 L2b `result.json`에 있다.
  - 잡음 r79 실행 기록에는 S-1~S-6 행 결과가 없다. 그 값은 r79 판정기(`r79_sensor_judge.py judge`, 판정 파일 `runs[].rows.S-1…S-6`, 최상위 `errors`·`unmatched`·`settings_mismatch`)가 L1 짝과 비교해 계산한다. 실행 기록에 있는 것은 판정기 입력(`base.*`, `r79.*`, `events`, `base.t_done_s` 등)이다.
  - R4-C를 쓰려고 더 읽은 것:
    - 하네스 경로 2 README(`path2/README.md`)의 rev3 반영 표(171~185행). 코드는 열지 않았다.
    - 저장 `v5/d1.jsonl`(868줄)·`v5/main.jsonl`(앞 400줄)의 필드 이름
    - 저장 정체성 기록 `v5/b1/b1_H.jsonl.identity.json`의 필드 이름
    - 값은 읽지 않았다.
- 이 작성자는 경로 2 작성자가 아니다(rev2 R2-0).

## R4-A. 재집계 입력의 출처 (N-1, N-2, Q-R1, 사용자 결정 2026-11-13: Q-R4-1 = C)

### R4-A1. 판정 값이 지금 계산되는 곳

| 항목 | 판정 정의(원본) | 값이 생기는 곳 |
|---|---|---|
| C-5 T4-0·T4·T5 | 개정 6 4.1~4.6, 개정 7(E 표본 제외·가드·B1), 개정 8 97행(③ 켬 감시기), 개정 11 28행(감시기 설정 = 실행 자신의 제어기) | 실행 뒤 감시기 재생. 개정 7 94행이 지정한 도구 `chrono_t45_replay`(t4, t5)와 재생기 `contact_replay`. 입력은 실행 폴더의 10 Hz 판독·명령과 `pads.npz` 1 ms(`F_pressure`, `F_pressure_min_interval`, `law_locked`, `airborne`) |
| C-5 J-P3 | 개정 8 3.2(ext_moving `sum(breach_reads)` = 0), 개정 9 3.2 표 | 실행 기록 `result.json` `hydraulics_record.extend_bound_check` |
| C-5 J11 창 | 개정 6 6절(1 ms `law_locked` 전이, 명령 기록에서 창 끝, 실제 대체 다리는 `fallback_lock_log`와 대조) | 실행 기록(`pads.npz` `law_locked`, 명령 기록, `controller_meta.two_pressure.fallback_lock_log`) |
| C-5 D2 | 개정 12 70행 "D2·잠금 창 항목" = 개정 6 14.5(389~390행: D2 대체 수, D2 위반 시작 비) | 실행 기록(`controller_events.json`의 대체 사건과 사유, `controller_meta.two_pressure.review_record.d2_violation_start_ratio`) |
| PS-c E-1~E-7 | 명세 426.3(E-1 부상, E-2 인접 다리 창, E-3 F_min, E-4 압력, E-5 끝 상태, E-6 크롤러, E-7 재발) | Chrono `run_S9`가 하네스와 같은 1 ms 행 꼴로 쓰는 `soil_event_series.npz`(사건 행). 판정은 하네스 연구 A 판정 함수(`s9_soil_event_screen`)와 같은 정의다 |
| 잡음 S-1~S-6, L1 게이트 개수 | v5 기준 10절, 명세 405~407.2·419.8·423.1, 13.2(`--s4-late-loc`) | r79 판정기 `r79_sensor_judge.py judge`(L1 짝 비교). 실행 기록은 그 입력만 가진다 |

### R4-A2. 정의 (안 C, 사용자 결정 2026-11-13)

**C-5 J-P3·J11·D2와 PS-c E-1~E-6은 기존 실행 기록에서 정의가 닫힌다(안 b).** 이 항목들은 rev3 R3-G1의 "재집계"가 아니라 **"재계산"** 층으로 옮긴다. 경로 2는 다음 기록에서 원 규칙 정의대로 다시 계산한다.
- J-P3: `hydraulics_record.extend_bound_check`. `breach_reads`(ext_moving, 개정 8 68행: 작용 명령 > 0인 판독의 초과 수)의 네 다리 합 = 0이면 통과, ≥ 1이면 H-7이다. 키가 없거나 null이면 개정 9 3.2 표로 처리한다. 블록의 `rule`이 ext_moving 정의와 같은지 G-S에서 확인한다.
- J11: 개정 6 6절 정의대로, `pads.npz` `law_locked` 전이와 명령 기록으로 창 끝을 계산한다. 실제 대체 다리는 `fallback_lock_log`와 10⁻¹² s 안에서 대조한다.
- D2:
  - D2 대체 수 = 사건 기록 가운데 사유가 D2인 로드 압력 대체 사건 수다. 기대 0이고 기록이다. J7은 원 규칙대로 본다.
  - D2 위반 시작 비 = `review_record.d2_violation_start_ratio`(기록)다.
- PS-c E-1~E-6: 명세 426.3 정의대로 `soil_event_series.npz` 1 ms 행(패드 접촉 법선, F_cyl, 틈 등)과 `result.json`의 사건 시각·단계에서 다시 계산한다.

**C-5 T4-0·T4·T5, PS-c E-7, 잡음 S-1~S-6·L1 게이트는 실행 기록만으로 닫히지 않는다.** 감시기 재생, 비틀림 일 묶음(248.3), L1 짝 비교가 필요하다. 이 항목들은 **경로 2가 원 규칙이 지정한 기존 판정 도구를 직접 실행해** 항목별 결과를 만들고, 그 결과를 재집계 입력으로 쓴다(안 c).

| 항목 | 경로 2가 실행하는 도구(원 규칙의 지정) | 입력 |
|---|---|---|
| T4-0·T4·T5 | `04_scripts/04_hydraulic/coupled/chrono_t45_replay.py`(t4, t5, `--criteria` rev7 기본; 개정 7 94행) | C-5의 원 규칙 대상 행의 실행 폴더 |
| E-7 | 하네스 연구 A 판정 함수(`s9_soil_event_screen`의 E 판정, 명세 426.3) | PS-c 행의 `soil_event_series.npz` |
| S-1~S-6, L1 게이트 | `04_scripts/03_control/s8/r79_sensor_judge.py judge … --s4-late-loc`(v5 기준 10절, 13.2; 3단계 판정이 쓴 꼴) | 436.8 r79 출력(rev1 RV1-3.3 이름)과 그 L1 짝 |

- 조건(모두 참이어야 한다. 하나라도 거짓이면 그 묶음은 S-11로 멈춘다):
  1. 도구 파일이 `git log f46b5ab..GIT_AT_START -- <파일>`에서 0커밋이다(436.8 규칙 봉인 뒤 판정 논리 변경 없음). `GIT_AT_START`는 판정서에 적을 채울 칸이다. 판정서에 도구 파일 sha256을 적는다.
  2. `chrono_t45_replay`는 개정 7 95행의 도구 회귀(3단계 저장 기록 18행에서 5절 수 재현)를 같은 커밋에서 통과한다.
  3. 경로 2는 자기 출력 폴더에 쓰고, 경로 1이 같은 도구로 만든 출력은 읽지 않는다(원판 9.2).
  4. 경로 2는 도구 출력의 항목별 결과에 원 규칙의 등급·FLAG·강등 규칙을 따로 적용한다. 예: 개정 6 4.6 문구, 개정 7 E·B1 집계, 13.2 `S4_late_loc`, S1 전방 제외, Clopper–Pearson 두 근, L1 게이트 네 개수(R4-B3). 도구가 내는 묶음 결론은 쓰지 않는다.
- **한계 공개(판정서 한계 절에 그대로 적는다. rev3 R3-G1·R3-E3 문장에 이 문장을 더한다)**: "T4-0·T4·T5, PS-c E-7, 잡음 S-1~S-6과 L1 게이트의 항목 값은 원 규칙이 지정한 같은 판정 도구를 경로 2가 따로 실행해 얻었다. 그래서 두 경로는 같은 계산 함수에 기댄다. 경로 2의 독립성은 도구 실행과 등급 재집계에 있고, 항목 값 계산에는 없다."
- 고르지 않은 안(기록):
  - A: 러너가 실행 직후 같은 재생·판정을 돌려 실행 기록에 남긴다(기록 전용). 실행 기록이 되므로 9.2 문구에는 맞다. 그러나 같은 함수에 기대는 점은 C와 같고, 러너 구현과 G-S 재실행이 늘어난다. 잡음 S-1~S-6은 L1 짝이 필요해서 실행 단위 러너가 계산할 수 없다.
  - B: 경로 2가 감시기·판정 논리를 독립 재구현한다. Q-C1·Q-E3에서 고르지 않은 안이다.
- 결정: **C**(사용자 결정 2026-11-13, Q-R4-1). 경로 2가 원 규칙이 지정한 기존 판정 도구를 직접 실행한다. 조건 4개와 한계 공개 문장은 위 그대로 쓴다.

### R4-A3. C-7 행 구분 (N-4, 기록)

- C-7a·C-7b는 `criteria_id`가 아니라 행 이름으로 구분한다. 원판 5.3 표대로 `P3a_G1_B_VB_FB` = C-7a, `P3a_G1_B_V0_FB` = C-7b다. `criteria_id`가 `C-7`이든 `C-7a`·`C-7b`이든 판정은 같다. 판정서에 행 생성기가 쓴 값을 적는다.
- 결정 필요: **아니오**.

## R4-B. 하네스 기록 필드와 정의 (Q-R2~Q-R7)

### R4-B1. SA-4 "정지 뒤 부상 0"의 기록 (Q-R2)

- 사실: 하네스 S8 줄에는 정지 뒤 패드 부상을 나타내는 필드가 없다(저장 기록 기준).
- **정의**: 경로 1 구현자가 v5 S8 계열 하네스 줄에 기록 전용 필드를 더한다. 명령은 바뀌지 않는다. 필드는 다리별 정지 뒤 부상 시간 [ms]이다. 정지 시각(`FAULT_LIFT_STROKE_LIMIT:soil` 주기)부터 실행 끝까지 그 다리 패드 접촉력 진값 ≤ 0인 1 ms 표본 수 × 1 ms로 잰다(rev3 R3-G10 Q-14 정의). 이름은 `values.sa4.lift_after_stop_ms`(다리 순서 FL, FR, RL, RR)로 한다.
  - `git_at_start` 이전 커밋으로 넣고 G-S에서 확인한다.
  - 필드가 없으면 그 S8 줄의 SA-4는 `판정 불가`다(rev3 R3-E5 Q-S6).
- 결정 필요: **아니오**(기록 전용 필드, rev3 R3-E4와 같은 처리).

### R4-B2. 419.8 조건 5의 첫 DONE 시각 (Q-R3)

- **정의**: r79 실행 기록의 `base.t_done_s`를 그 실행의 첫 DONE 시각으로 쓴다. 값이 None이면 DONE 없음이다. 조건 5(최종 LOC가 첫 DONE보다 먼저)는 rev3 R3-G10 Q-12 규칙으로 읽는다: LOC가 있고 (DONE 없음 ∨ t_LOC_fin < 첫 DONE).
  - `base.t_done_s`가 "첫" DONE인지(재레벨 뒤 DONE이 아닌지)는 G-S에서 한 줄의 단계 경로(`base.phase_path`)와 대조해 확인한다. 다르면 S-11이다.
  - 사건 이름 검색(`first_done` 등)은 쓰지 않는다.
- 결정 필요: **아니오**.

### R4-B3. L1 게이트 네 개수 (Q-R4)

- **정의**: v5 기준 10절 L1 게이트의 네 개수는 3단계 판정(`stage2_judgement.md` 139·576행)과 같은 정의로 센다.
  - 거짓 LOC = L1 줄 가운데 `r79.crawler_at_loc_over_W` ≥ 0.01인 줄 수(LOC 때 크롤러 하중 ≥ 0.01 W, S-5 기준, 명세 14747행).
  - unmatched = L1 짝(같은 harness, `case_index`, `inner`)이 없는 L2·L3 줄 수.
  - errors = 출력 meta의 `n_errors`와 `error` 키를 가진 결과 수의 합.
  - 설정 불일치 = `v5_setting`이 그 묶음 설정(VB 또는 V0)과 다른 줄 수.
  - 네 개수를 경로 2가 실행 기록에서 직접 센 값과 R4-A2 안 c의 판정기 출력의 같은 개수(`errors`, `unmatched`, `settings_mismatch`, L1 S-5 기준 수)를 함께 적는다. 다르면 그 묶음은 `판정 불가`(S-13)다.
- 결정 필요: **아니오**(경로 2 가정을 3단계 판정 정의로 확인).

### R4-B4. 격자 V0 표본 파일 꼴 (Q-R5)

- **정의**: rev3 R3-E1의 V0 표본 출력은 격자 러너의 고유 형식(`results[].runs[]`, run마다 `commands_sha256`)이다. 파일 이름은 `resume_k1/h9_grid_v0_sample/<저장 격자 파일 stem>.json`(4파일)이다.
  - 표본 run과 저장 V0 run은 (파일 stem, 결과 `key`, run `event`, run `offset_s`)로 맞춘다.
  - 한 표본 작업 = 저장 파일의 `results[]` 항목 하나다. 그 항목의 모든 run 해시가 같아야 "같음"이다.
  - 기록(경로 1 구현자 전달, 2026-11-13): 436.8 V0 격자는 `R67_V5_SETTING=V0`로 436.8 제어기(`final_C4G2_LAS_K1`)에서 돈다. 저장 V0 격자는 옛 제어기 결과다. 그래서 표본 해시가 다를 가능성이 크고, 그러면 rev3 R3-E1 3번대로 V0 768이 돈다. 이것은 예측 기록이며 판정 조건이 아니다.
- 결정 필요: **아니오**.

### R4-B5. `h9_family_F.jsonl` 줄 꼴 (Q-R6)

- **정의**: 한 줄 = 격자 러너 run 하나다. 필드는 다음과 같다.
  - `key`, `setting`(V0·VB), `v5_setting`, `controller_tag`, `offset_s`, `event`(= FS24)
  - run 객체 전체: `gates`(`Fmin_after_W`·`U57_outside` 포함 관문 전부), `fault_events`, `final_phase`, `commands_sha256`
  - 64줄(키 2 × 위상 16 × V0·VB)이어야 하고, 아니면 S-15다.
  - 기록(경로 1 구현자 전달, 2026-11-13): r67 격자 러너는 위상마다 사건 셋(G4·RE1bF·FS24)을 모두 돈다. 그래서 실제 run은 설정당 96개, 합 192개다. 판정(R-1~R-4)과 S-15에는 `event` = FS24인 64줄만 쓴다. 나머지 128 run은 `h9_family_F.jsonl`에 넣지 않거나, 넣으면 판정·S-15에서 제외하고 개수만 적는다.
  - R-1~R-4는 rev3 R3-E2(개정 5 5.2)대로 판정한다.
- 결정 필요: **아니오**.

### R4-B6. H-6 등급 (Q-R7)

- **정의**: v5 기준 개정 8 2절 #6과 7.1 표(116행 "판정: L2 실패 0(키별 꺼짐과 같음), L3 9(기록), J-P3 통과(ext_moving 0), 새 FAULT 0")의 항목으로 정한다.
  1. 135줄 가운데 J-P3 위반(ext_moving ≥ 1)이 있으면 H-7 멈춤이다.
  2. J9(M2 잘림)는 원 규칙대로 H-9이고, 대체 다리 n_late > 0은 H-7이다.
  3. 새 FAULT(같은 키 L1에 없던 FAULT 이름, S-6 기준)가 있으면 `미달`이다.
  4. L2 1키는 그 줄이 H-8 L2 집계(CP)에 들어간다(원판 5.1 H-8 "dg3 대체 처리는 원 규칙 그대로").
  5. L3 134키는 실패 수를 기록한다.
  6. 1~3에 걸리지 않으면 `통과`다. 줄 등급에 `판정 불가`가 있으면 그 묶음은 `판정 불가`다(원판 8.1).
- 결정 필요: **아니오**.

## R4-C. 하네스 경로 2의 rev3 적용 질문 (dynamics-expert)

### R4-C1. READY 기준점의 원점 확인 (rev3 R3-A3, 가장 급함)

- 사실:
  - 저장 `d1.jsonl`에는 단계 시작 시각 기록이 없다.
  - 있는 것은 `values.times.t_first_ready_s`·`t_touch_end_s`·`t_first_done_s`와 단계별 길이 `values.E1.<단계>.duration_s`다.
  - rev3 R3-A3의 원점 확인("첫 단계 CHECK 시작 ≤ 0.1 s")을 그대로 쓰면 H-1 전 줄이 판정 불가가 된다.
- **정의(안 a + 대체 b)**:
  1. 경로 1 구현자가 run_v5 계열 하네스 줄(H-1·H-9·H-10과 U-3 재사용 D-1 줄)에 기록 전용 필드 `values.times.t_check_start_s`(CHECK 단계 첫 제어 주기 시각, 폐루프 시작 기준)를 더한다(R4-D 표). 이 필드가 있으면 rev3 R3-A3대로 ≤ 0.1 s(+10⁻⁹)를 확인한다.
  2. 필드가 없는 줄은 **하네스 정의로 원점을 정한다**: 하네스 실행은 시각 0에서 폐루프를 시작하고, 첫 제어 주기는 T_s다. 근거는 저장 하네스 기록의 단계 표(`timeline` 첫 항 `[0.1, "check"]`) 꼴이다(저장 overlap 기준 기록·격자 기록의 필드 꼴, 값은 이 꼴 확인에만 썼다). 이 경우 원점 확인은 "정의에 의함"으로 적고 판정 불가로 두지 않는다.
  3. 두 경우 모두 `d1.t_ready_s`와의 대조(rev3 R3-A3)는 그대로다.
- 결정 필요: **아니오**. 1은 기록 전용이고, 2는 판정 불가를 막는 정의다.

### R4-C2. 정착 v2 블록의 단위·허용·표 목표 (rev3 R3-B6)

- **정의**:
  - 단위: 398.3 식에서 Δφ·Δθ(`d_attitude_deg`)는 rad로 바꿔 쓴다. 패드 좌표(`pad_xy_m`)는 mm로 바꿔 관입(mm)과 같은 단위로 쓴다. 식은 pen_mean,i [mm] = pen_inst,i [mm] + (y_i [mm] · Δφ [rad] − x_i [mm] · Δθ [rad])다.
  - `tolerances` 대조: 기록의 세 값(gap 1.0 mm, attitude min 0.005°, residual margin 0.002°)이 398.3의 값과 원판 7.6 비교 허용(10⁻⁹, 그 단위) 안에서 같아야 한다. 하나라도 다르면 S-11이다.
  - 표 목표 대조: 정착 표 파일의 형식은 규칙에 정의돼 있지 않다. 그래서 rev3 R3-B6의 "표 행 값과 같은지"는 다음 두 확인으로 바꾼다.
    1. `table_sha256`이 `table` 파일의 sha256과 같다.
    2. 경로 1 구현자가 기록 전용 필드 `settle_v2.inputs.table_gap_target_mm`(그 사례의 표 목표, 시작 틈 패드도 표 값)을 더한다(R4-D 표). `gap_target_source` = 표인 패드는 `gap_target_mm` = `table_gap_target_mm`이어야 한다.
  - 연구 D 시작 틈 패드의 "표 목표로도 계산"(rev3 R3-B7 공개)은 `table_gap_target_mm`로 한다.
  - 표 파일을 경로 2가 직접 읽어 값을 대조했으면 그 결과를 기록으로 적는다(판정 조건은 아님).
- 결정 필요: **아니오**.

### R4-C3. 강등 기록의 판별 (rev3 R3-A2)

- 사실: 저장 `d1` 블록의 필드 이름에는 강등을 나타내는 키가 없다. `d1.items`의 항목 이름에도 없다. 이름에 "demot"가 든 필드로 판별하는 것은 근거가 없다.
- **정의**:
  - 경로 1 구현자가 `d1` 블록에 기록 전용 필드 `d1.demoted_items`를 더한다(R4-D 표). 형식은 항목마다 세 필드 `item`, `rule`, `flag`를 가진 객체의 목록이다.
    - `item`: 거짓인데 `fail_items`에 넣지 않은 항목 이름
    - `rule`: 강등 근거(377, 424.11.2, 424.8.1, 419.8 중 하나)
    - `flag`: 그 FLAG 이름
  - 경로 2는 rev3 R3-A2 층 2에서 "거짓 항목 − `fail_items`" 집합이 `d1.demoted_items`의 `item` 집합과 같은지 본다. 다르거나 필드가 없으면 그 줄은 `판정 불가`(S-13)다.
- 결정 필요: **아니오**(기록 전용).

### R4-C4. K-0 정체성 필드 (H-0)

- **정의**: `.identity.json`(`start`·`end` 두 기록)에서 다음을 대조한다.

| K-0 항목 | 필드 | 조건 |
|---|---|---|
| 커밋 | `start.head`, `end.head` | 둘이 같고 `git_at_start`와 같다 |
| 작업 트리 | `start.is_clean`, `start.status_porcelain` | 깨끗하거나, 차이가 실행 전 감사가 허용한 파일뿐이다 |
| 코드 차이 | `start.code_diff_sha256`, `end.code_diff_sha256` | 둘이 같다 |
| 제어기 | `start.c2_sha256`, `end.c2_sha256` | 둘이 같고 `git_at_start`의 `03_src/outrigger_sim/control/c2.py` sha256과 같다 |
| 도구 | `start.tools_sha256`, `end.tools_sha256` | 둘이 같다 |
| 스레드 | `start.env`의 `MKL_NUM_THREADS`·`OMP_NUM_THREADS`·`OPENBLAS_NUM_THREADS`·`NUMBA_NUM_THREADS` = 1, `MKL_THREADING_LAYER` = TBB | 원판 6절 |
| 금지 env | `start.env.OUTRIGGER_LOC_SHADOW` | 없거나 빈 값(원판 4.2) |

- R-0·R-0K·T-3K 세 출력의 위 값은 서로 같아야 한다(`las_targeted_rules_rev5.md` 59행). 다르면 H-T3-3이다.
- 필드가 이 꼴이 아니면 G-S에서 대응을 확인하고 판정서에 적는다. 확인되지 않으면 그 항목은 `판정 불가`다.
- 결정 필요: **아니오**.

### R4-C5. main 줄의 바닥 각 (rev3 R3-C5)

- 사실: 저장 `main.jsonl` 줄에는 바닥 각 필드가 없다(`job.case`만 있다). D-1 줄은 `job.d1.roll_deg`·`pitch_deg`를 가진다.
- **정의**:
  - 경로 1 구현자가 run_v5 main·item8·overlap·u9 계열 줄에 기록 전용 필드 `values.case_floor_deg`(사례 정의의 바닥 [roll, pitch], deg)를 더한다(R4-D 표).
  - J3의 경사 판별(rev3 R3-C5)은 이 필드와 D-1 줄의 `job.d1` 각으로 한다.
  - 필드가 없는 줄의 J3 경사 판별은 `판정 불가`다. R1~R11의 J3는 기록 항목이므로 등급에는 영향이 없고, FLAG 한계 칸을 "미정"으로 적는다.
- 결정 필요: **아니오**.

## R4-D. 실행이 기록 전용으로 남길 필드 (경로 1 구현자용 한 표)

모든 필드는 명령을 바꾸지 않는 기록 전용이다. `git_at_start` 이전 커밋으로 넣는다(원판 A-5). "G-S 확인" 열이 예인 필드는 원판 11.2 G-S에서 실제 줄·행에 키가 있는지 본다. 없으면 S-11이다.

| # | 출처 질문 | 실행(러너) | 필드 | 내용 | G-S 확인 |
|---|---|---|---|---|---|
| F-1 | rev3 R3-A3 / R4-C1 | run_v5 계열 하네스 줄(H-1·H-9·H-10, U-3 재사용 D-1 줄) | `values.times.t_check_start_s` | CHECK 첫 제어 주기 시각(폐루프 시작 기준) [s] | 예 |
| F-2 | rev3 R3-A2 / R4-C3 | run_v5 `d1` 블록 | `d1.demoted_items` | 강등 항목 목록(`item`·`rule`·`flag`) | 예 |
| F-3 | rev3 R3-C5 / R4-C5 | run_v5 main·item8·overlap·u9 줄 | `values.case_floor_deg` | 사례 바닥 [roll, pitch] [deg] | 예 |
| F-4 | Q-R2 / R4-B1 | run_v5 S8 계열 줄 | `values.sa4.lift_after_stop_ms` | 다리별 정지 뒤 부상 시간(FL, FR, RL, RR) [ms] | 예 |
| F-5 | rev3 R3-B6·B7 / R4-C2 | U-3 v2 대상 묶음 레코드·D-1 재사용 줄 | `settle_v2.inputs.table_gap_target_mm` (`u3.settle_v2.inputs.…`) | 패드별 표 목표 틈 [mm] | 예 |
| F-6 | rev3 R3-E4 | r79 계열(H-6·H-7·H-8) | 결과 항목 최상위 `commands_sha256` | 명령 해시(하네스 줄과 같은 정의) | 예 |
| F-7 | (안 A 전용) | – | – | **해당 없음**(Q-R4-1 = C. T4-0·T4·T5는 경로 2가 `chrono_t45_replay`를 직접 실행해 얻는다) | – |

이미 있는 필드 가운데 G-S에서 뜻을 확인할 것:

| 필드 | 확인할 것 | 출처 |
|---|---|---|
| `hydraulics_record.extend_bound_check.rule`·`breach_reads` | ext_moving 정의(작용 명령 > 0 판독)인지 | R4-A2 |
| `head_only_declared`(하네스 줄) | 필드 유무 | rev3 R3-C8 |
| 격자 run의 `extend_bound_check` | 필드 유무 | rev3 R3-E5 Q-G3 |
| r79 `base.t_done_s` | 첫 DONE인지(`base.phase_path` 대조) | R4-B2 |
| `soil_event_series.npz`(PS-c 행이 있을 때) | 426.3 E-1~E-6 재계산에 필요한 열(패드 접촉 법선, F_cyl, 틈) | R4-A2 |

- 필드가 없어서 생기던 판정 불가는 이 판에서 다음처럼 정리된다.
  - N-1(T4-0·T4·T5): R4-A2 안 c(경로 2가 기존 도구 실행, Q-R4-1 = C)로 풀린다.
  - N-1의 나머지(J-P3·J11·D2): 기존 필드로 풀린다.
  - N-2(PS-c E-1~E-6): 기존 필드로, E-7은 안 c로 풀린다.
  - Q-R1(S-1~S-6): 안 c로 풀린다.
  - Q-R2: F-4로 풀린다.
  - Q-R3: 기존 필드로 풀린다.
  - R3-A3: F-1로 풀리고, 필드가 없어도 정의로 원점을 정한다.

## R4-9. 결정 표

| 항목 | 권고 | 결정 필요 |
|---|---|---|
| R4-A2 재집계 입력 | J-P3·J11·D2·PS-c E-1~E-6은 실행 기록으로 재계산(안 b). T4-0·T4·T5·E-7·S-1~S-6·L1 게이트는 경로 2가 기존 판정 도구를 직접 실행(안 c, 조건 4개, 한계 공개) | 결정됨: C(2026-11-13) |
| R4-A3 C-7 구분 | 행 이름으로 | 아니오 |
| R4-B1 SA-4 부상 | 기록 전용 `values.sa4.lift_after_stop_ms` 추가, 없으면 판정 불가 | 아니오 |
| R4-B2 첫 DONE | `base.t_done_s`, G-S에서 첫 DONE 확인 | 아니오 |
| R4-B3 L1 게이트 | 3단계 판정 정의, 판정기 개수와 대조 | 아니오 |
| R4-B4 V0 표본 꼴 | 격자 고유 형식, (stem, key, event, offset) 대조 | 아니오 |
| R4-B5 𝓕 줄 꼴 | run 하나 = 줄 하나, 64줄 | 아니오 |
| R4-B6 H-6 등급 | 개정 8 #6 항목(J-P3·새 FAULT·H-7·H-9), L2는 H-8, L3 기록 | 아니오 |
| R4-C1 READY 원점 | F-1 기록 전용 필드, 없으면 하네스 정의(시각 0 = 폐루프 시작) | 아니오 |
| R4-C2 정착 v2 단위·허용·표 목표 | deg→rad, m→mm, 허용 1e-9 대조, F-5 표 목표 필드 + 표 sha | 아니오 |
| R4-C3 강등 판별 | F-2 `d1.demoted_items` | 아니오 |
| R4-C4 K-0 필드 | `.identity.json` start·end 필드 표 | 아니오 |
| R4-C5 main 바닥 각 | F-3 `values.case_floor_deg` | 아니오 |
| R4-D 기록 필드 표 | F-1~F-6(필수), F-7 해당 없음 | 아니오 |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 파일 이름: `v5_resume_4368_rules_rev4_seal_candidate_draft.md` → `v5_resume_4368_rules_rev4.md`(같은 폴더). 초안 파일은 지우지 않고 그대로 둔다.
2. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev4 (재집계 입력의 출처: Chrono 감시기·PS-c·r79 관문, 하네스 기록 필드, 결과 전, 봉인)`
3. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev4.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev4_seal_candidate_draft.md`와 1·3·5·7행만 다르다.`
4. 5행("시점")에서 `SEAL_TIME`(예: 2026-11-13 10:00:00 +09:00)과 `SEAL_COMMIT`(봉인 파일을 넣는 커밋의 앞 커밋, 7자리)을 값으로 바꾼다. 이 두 이름 말고는 5행을 바꾸지 않는다.
5. 7행("봉인 준비판이다")을 다음으로 바꾼다:
   `- **봉인본이다.** 사용자 결정 Q-R4-1 = C(사용자 결정 2026-11-13)는 R4-9 결정 표와 R4-A에 반영했다.`
6. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules_rev4.sha256`에 `<sha256>  v5_resume_4368_rules_rev4.md  sealed <SEAL_TIME 값> (436.8 rev4: sources of the re-aggregation inputs before results; Chrono J-P3/J11/D2 and PS-c E-1..E-6 recomputed from run records, T4-0/T4/T5, E-7, noise S-1..S-6 and L1 gate counts by path 2 running the sealed-rule tools itself, C-7 by row name, SA-4 lift field, first DONE, L1 gate counts, grid V0 sample and family F line forms, H-6 grade, READY origin, settle v2 units and table target, demotion list, K-0 identity fields, case floor field, record-only field list F-1..F-6, user decision Q-R4-1 = C; thresholds and grades unchanged)` 한 줄로 쓴다.
7. `.gitattributes`에 다음을 더한다:
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev4.md -text`
   - `…/v5_resume_4368_rules_rev4.sha256 -text`
   - `…/v5_resume_4368_rules_rev4_seal_candidate_draft.md -text`
8. `tools/verif/seal_check.py`와 `tools/verif/placeholder_scan.py`(봉인본에 `SEAL_TIME`·`SEAL_COMMIT`이 남지 않음)로 확인한 뒤 커밋한다. 봉인 뒤 이 문서를 고치지 않는다. 고칠 것이 생기면 `v5_resume_4368_rules_rev5.md`로 새로 봉인한다.
