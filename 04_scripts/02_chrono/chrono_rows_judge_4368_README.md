# chrono_rows_judge_4368 — 436.8 Chrono 경로 1 집계 새 판

- 근거: 규칙 rev5 R5-A1(경로 1 새 판, 요건 1~5), rev6 R6-A(D-26~D-39)·R6-B(C-1~C-9 정의)·R6-C3(377 분기)·R6-1(시각 원점).
- 대조표: `06_analysis/02_control/verif_matrix/v5_resume_4368/chrono_path1_rev3_alignment.md`(추적 밖, cad-expert 2026-11-13). 이 도구의 N-1~N-14 = rev6 D-26~D-39다.
- 고치지 않은 것: 러너(`run_S9.py`, `run_S8C.py`, `run_S6C.py`)와 기존 판정 함수(`r76_g6_chrono_judge.py`, `verify/s8_control.py`, `verify/s6_control.py`).
- 작성: cad-expert, 2026-11-13. 실행 환경: Chrono-dev `python -I -X utf8`(pychrono는 import하지 않는다. numpy·PyYAML만 쓴다).

## 1. 실행

```
python -I -X utf8 04_scripts/02_chrono/chrono_rows_judge_4368.py judge --git-at-start <판정서 git_at_start> --out <out.json> \
    --batch <07_results/S9/batch_V5-RESUME-K1-C3_<stamp>> [--batch ...] [--row <행 폴더> ...] \
    [--results-root <07_results>] [--rules-dir <verif_matrix>] [--params <02_params/rexome33.yaml>]
python -I -X utf8 04_scripts/02_chrono/chrono_rows_judge_4368.py disclose [--out f.json]
python -I -X utf8 04_scripts/02_chrono/chrono_rows_judge_4368.py seals [--rules-dir <verif_matrix>]
```

- `--batch`: `s9_batch` 배치 폴더(`batch.json`). SCM 행은 `<batch>/<case>/`에서 찾는다. 행 번호(`S-03` 등)는 `batch.json`의 `d1_id`에서 읽는다.
- L2b·L1-R 행 폴더(v2, 2026-11-13. v1은 배치 시각과 같은 이름만 찾아 1 s 늦게 생긴 L1-R 폴더 `_082118`을 놓쳤다):
  1. 행 로그 `<batch>/<case>.log`의 마지막 `batch wall ... -> <폴더>` 줄을 읽는다(`s9_batch.s8c_case_check`, gs-check와 같은 규칙). 행 = `<폴더>/<--only>`. 그 폴더에 `result.json`이 없으면 같은 경로를 `--results-root` 아래(`.../07_results/<나머지>` → `<results-root>/<나머지>`)에서 한 번 더 찾는다(지운 worktree에서 돈 뒤 결과를 옮긴 경우). 그래도 없으면 종료 2.
  2. 로그에 그 줄이 없으면(rev12 R12-5) 이름이 정확히 맞는 러너 폴더(`S8/<tag>_<YYYYmmdd_HHMMSS>`, `S6/<기본>_<tag>_L1R_<YYYYmmdd_HHMMSS>`; 확인 실행 꼴 `…_<tag>_check_L1R_…`와 넓은 맞춤 `S6/*<tag>*`는 쓰지 않음) 가운데 이름 시각이 그 행의 `progress.log` START~END(없으면 배치 시각 ~ + `wall_s`, `est_s`는 쓰지 않음) ± 2 s 안이고 그 아래 `<--only>/result.json`이 있는 것을 쓴다. 정확히 하나일 때만 쓰고, 없거나 둘 이상이거나 창을 정할 수 없으면 입력 오류(종료 2, S-11).
  - 행마다 찾은 방법을 `rows[].row_dir`(`source` = `batch_folder` / `case_log` / `case_log_relocated` / `time_window`)에 적는다.
- 열린 루프 행(C-6·C-7, `run_S9.py machine`, `series.npz` + `result.json` `p3a`)은 이 도구의 판정 대상이 아니다(원판 9.1: C-6·C-7 경로 1 = `result.json` `p3a`, 경로 2 = `openloop_compare.py` `analyse`. 원판 7.5·8.1: 기록 행. rev5 R5-A1: Chrono 경로 1 새 판 = C-1~C-5). 읽지 않고 `skipped_rows`(입력 sha256, 근거 규칙)에 적는다. 종료 코드에 영향 없음.
- `--row`: 행 폴더를 직접 준다(배치 정보 없이). C-3 두 행은 이름으로 알아본다.
- `--assume C-n=값`: 민감도 확인용이다. 출력에 `deviates_from_rev6`가 붙고, 그 출력은 경로 1 결과로 쓰지 않는다.
- 엔진 구분(z4372, 2026-11-14): 파일로 행 형태를 정한다. `step_series.npz`가 있으면 SCM(run_S9), `pads.npz`가 있으면 L2b 또는 L1-R, `series.npz`와 `p3a`가 있으면 열린 루프(건너뜀)다. L2b와 L1-R은 명시 기록으로 가른다: `batch.json` 행의 `r4368.engine`·`engine`, `result.json` `settings.s8.engine`(`L2b_NSC` → L2b, `L1R` → L1-R, `SCM` → SCM). `pads.npz` 행에 기록이 없거나, 이름을 모르거나, 두 기록이 다르거나, 기록이 파일 형태와 맞지 않으면 입력 오류(종료 2)다. 예전 규칙(`crawler_normal_N`이 있으면 L2b)은 V0 L2b 행(`law_locked`는 있고 `crawler_normal_N`·`m2_*`는 없음)을 L1-R로 잘못 분류했다. 출력 행마다 `engine_record`(근거 기록)를 적는다. `batch.json` `criteria_id`가 C-6·C-7·C-7a·C-7b여도 건너뛴다.
- 읽는 키: V0 행(SCM P3b_J2 시드 행, O-C5 Kc1 V0)과 L1-R 행에 없는 `extend_start_rule`·`extend_bound_check`·`v5_hydraulics.controller_tag`는 읽지 않는다. rev8 R8-2(아래 7절)부터 ③ 판별은 행 태그(`--expect-controller`)로 하므로, ③이 아닌 행에서는 이 키들이 없어도 결측으로 세지 않는다.

## 2. 종료 코드와 출력

| 코드 | 뜻 |
|---|---|
| 0 | 끝남, 멈춤 없음 |
| 1 | 확인 실패(봉인 불일치, 시각 원점·S-11 문제) 또는 멈춤(R40-2 보류 미해제, rev8 S-2·J-P3 H-7·J11 멈춤, 7절) |
| 2 | 입력 없음·잘못됨(행 폴더, `result.json`, 규칙 파일, YAML, `--assume` 값) |
| 3 | 내부 오류(추적은 stderr) |

- 마지막 줄은 JSON(`exit`, 행 수, `seals_ok`, `stops`, `origin_failed`, `deviates_from_rev6`, 행 등급, `skipped`)이다. 그 앞 줄은 `errors N`이다(`tools/verif/log_errors.py`).
- `--out` JSON 항목:
  - 정의와 공개: `definitions_C`, `d_numbers`, `params`(YAML sha256·F_min), `seals`, `disclosure`
  - 행별: `rows[]`(`items`, `gates`, `grade`, `demoted_items`, `origin_check_R5_B1`, `row_dir`, 입력 파일 sha256)
  - 건너뛴 행: `skipped_rows[]`(`skipped` = `openloop_not_judged_here`, `rule`, 입력 sha256)
  - 묶음 요약: `stops`, `t_D_vs_runner_R6_B4`, `demoted_items`

## 3. 정의 (rev6)

| D | N | 함수 | 정의 |
|---|---|---|---|
| D-26 | N-1 | `sgs_class` | 427.9 조건 1~5(첫 FAULT = `FAULT_LIFT_STROKE_LIMIT:soil`, `FAULT_STROKE_END` 없음, LEVEL 시작 뒤 부상(Q-14) 없음, t_D ~ 끝 참 F_cyl ≥ F_min, 이동 ≤ 180 bar·포화 0)이 모두 참이면 `stroke_limited_stop`(= `allowed_stop`). S-01·02·03·04(R6-B8) |
| D-27 | N-2 | `ready_items` | P3-6: 한계(`p3b.P3-6_ready.limit_s`) 밖이면 FLAG(기록) |
| D-28 | N-3 | `ready_items` | G6 관문 READY − 폐루프 시작 ≤ 120 s + 1e-9 |
| D-29 | N-4 | `sustained_lift_1ms` (rev21 R21-1) | L2b t_lift = t_lift,sus = 단계 ∉ {idle, check, touch}이고 그 표본부터 기록 끝까지 `pads.npz` `crawler_normal_N` ≤ 0.01 W(W 376.7 kN, `SUSTAINED_LIFT_WEIGHT_N`)가 이어지는 첫 1 ms 표본, `D8_t_lift_basis` = `1ms_sus`. 없으면 t_lift 없음(C1·Q-14 판정 불가). rev6의 첫 ≤ 0 표본은 `D8_t_lift_sus_R21_1.t_lift_first_le0_rev6_record_s`로 기록만 한다(R21-1 이전 판: ≤ 0인 첫 1 ms 표본). 단계는 `phases` + `settings.start_t_s`(R6-1). `crawler_normal_N`이 없는 L2b 행(V0)은 rev15 R15-3(사용자 결정 2026-11-14)에 따라 L1-R과 같은 R6-B1 10 Hz 구간 대체를 쓴다(`v0_l2b_bracket_lift`): `record/record.npz` `F_crawler`를 `result.json` `floor_plane.normal_world`(정규화)에 사영, 시간축 `t`(0.1 s), 단계는 `phases` + `settings.start_t_s`. L1-R 경로와 달리 세계 z 대체는 없다. 세 입력 중 하나라도 없으면 t_lift는 `not_judgeable`이고 `missing_inputs`에 이름을 적는다. 그 행들은 출력 `l2b_bracket_rows_R15_3`에 적는다. rev21 R21-1: V0 행에는 10 Hz t_lift,sus 대응값(그 10 Hz 표본부터 끝까지 법선 ≤ 0.01 W인 첫 표본)을 `D8_t_lift_sus_R21_1`(`t_lift_sus_10Hz_s`, t_b와 다르면 `differs_from_t_b` 참, 없으면 `기록 결측`)로 기록만 하고 등급은 t_b로 낸다 |
| D-30 | N-5 | `d8_lift_time`, `judge_rigid` | SCM: `step_series.npz` `scm_crawler_normal_N`. L1-R: 10 Hz 구간 대체(R6-B1). t_b = 단계 조건 ∧ `F_crawler`·바닥 법선 ≤ 0인 첫 `record.npz` 행, t_a = 그 앞 > 0인 마지막 행 |
| D-31 | N-6 | `c1_block` | R40-2 보류(강체 크롤러, 원값 최소 < F_min + 5 kN, 그 시각 ≤ t_lift + 8 s, 같은 8 s 느린 성분 최소 ≥ 문턱) = 판정 불가 + 멈춤. L1 짝 해제는 사람이 한다(값만 낸다) |
| D-32 | N-7 | `moving_pressure` | 10 Hz 제어 주기 행(R6-B5), 이동 = abs(u_applied) > 1e-9, p = F_cyl/A_p(YAML 다리별), 포화 = 신장 ∧ ≥ 210 bar. 사건 행(J-5·U58 창)은 이 판에 없다 → 판정 불가 |
| D-33 | N-8 | `lift_samples` | 부상 = 패드 법선 ≤ 0인 1 ms 표본(Q-14, R6-B9) |
| D-34 | N-9 | `p38_block` | 377: 창 [재접근 시작, 첫 확정 LOC + 1 s]의 시작 다리 참 F_cyl 최소 ≥ F_min ∧ FAULT 0 → `P3-8_demoted`. 거짓 ∧ G6-3 참 ∧ FAULT 0 → `P3-8_preloc_loss`(U-S9-G6c, R6-C3). 둘 다 `demoted_items`. 계산 불가면 판정 불가. 최종 LOC로 계산한 결과도 기록 |
| D-35 | N-10 | `p38_block` | P3-8 구간 끝 = min(첫 확정 LOC(취소 포함), 첫 `soil_mode_start`) |
| D-36 | N-11 | `recontact_events` | 재접촉 지속 = 표본 수 × 1 ms(≥ 0.01 W, 이탈 확인 뒤) |
| D-37 | N-12 | `p32_block` | 최종 LOC < 첫 DONE(엄격) |
| D-38 | N-13 | `p32_block` | 하중 = > 0.01 W. 취소된 LOC 시각의 크롤러 법선 기록 |
| D-39 | N-14 | `c1_block` | D-29 t_lift와 S8-A2 판정 힘(R6-B2, 부상 표본 = `F_cyl_mean_20ms`, 표본 수 기록)으로 C1 행 재계산 |
| R6-B4 | – | `departure` | t_D = 0.01 W 미만 100표본 연속의 첫 표본. 러너 `p3b.departure`와의 차를 행·묶음별로 기록. P3-3(G6-3)은 새 t_D로 다시 계산 |
| R6-B6·B7, R6-1 | – | `origin_check` | n = round((t − t0)/0.1) 연속, r8 행의 round(t/1 ms)가 1 ms 계열에 있음, 잔차 기록. 대체 다리 = 로그 ∪ `WARN_ROD_PRESSURE_FALLBACK` 다리. 사건 없는 로그 다리와 `phases` 시각 혼용은 S-11 |

- G6 행 등급(S-03·04, `g6_grade`)의 관문은 여덟 개다.
  - 다시 계산하는 관문:
    - G6-1: READY ~ +10 s 크롤러 0 ∧ 재접촉 D-36
    - G6-2: D-37·D-38. 러너의 419.8·424.8.1 FLAG 꼬리표는 받는다
    - G6-3: 새 t_D 뒤 최소 ≥ F_min
    - G6-6: FAULT 0 ∧ READY
    - G6-7: D-34·D-35
    - READY ≤ 120 s(D-28)
  - 러너 값을 받는 관문: G6-4(`p3b.checks.P3-4_verdict`), G6-5(`P3-5` 틈 ≥ 25 mm ∧ 행정)
  - 순서: 판정 불가 > 실패 > FLAG > 통과(원판 274, rev3 R3-G7)
  - 안전 정지 행은 `stroke_limited_stop`이다.
- 그 밖의 SCM 행(S-01·02, C-5 SCM)과 L2b·L1-R 행은 D 항목만 다시 계산하고 등급은 내지 않는다(`grade` null). 행 등급은 그 묶음 원 규칙 판정기 몫이다.

## 4. 한계 (판정서 공개용)

- 열린 잠금 구간의 J11 창 끝·n_late(R6-B7)는 v3부터 `J11_R8-3` 항목이 계산한다(7절). 사건에만 있는 다리의 늦은 열린 구간은 `lock_window_alignment`의 `late` 목록(최대 50행)에서 센다. 목록이 잘려 셀 수 없으면 판정 불가다.
- D-32 사건 행(J-5·U58 창)은 판정 불가로 둔다. 제어 주기 사이의 압력 첨두는 보이지 않는다(R6-B5 한계).
- R40-2 보류 해제(7155행, L1 짝 자릿수 비교)는 값만 내고 사람이 판정한다(멈춤, 종료 1).

## 5. 기존 판정 함수와의 차이 (요건 3, `disclose`)

`git diff --no-index --numstat <기존> <새 판>`(v2, 2026-11-13, 새 판 sha256은 커밋 보고 참조). 기존 함수는 범위가 넓은 모듈이라 줄 수 차가 크다. 정의 차이는 3절 표와 rev6 R6-A 표가 원본이다. v2는 행 폴더 찾기와 열린 루프 건너뜀만 더했고 D 항목 정의는 v1과 같다.

| 기존 | 대상 D | 추가 | 삭제 |
|---|---|---|---|
| `04_scripts/03_control/s8/r76_g6_chrono_judge.py` | D-26·27·28·34·35 | 1041 | 429 |
| `03_src/outrigger_sim/verify/s8_control.py` | D-31·39 | 991 | 7914 |
| `03_src/outrigger_sim/verify/s6_control.py` | D-29·30·32 | 1006 | 3076 |

- 값은 새 판을 고치면 바뀐다. 판정서에는 실행 출력의 `disclosure` 블록 값을 적는다.

## 6. 봉인 대조 (요건 4)

원판·rev1~rev12·rev15~rev25의 md sha256을 도구 안 상수 `RULES_SEALS`와 각 `.sha256` 첫 토큰에 모두 대조한다. 하나라도 다르면 종료 1, 파일이 없으면 종료 2다. rev6 sha256 = `809e5639…`, rev7 = `e81f7d31…`, rev8 = `3ecafaaf…`, rev9 = `4cf7843c…`, rev10 = `62a0bd8d…`, rev11 = `9bac4524…`, rev12 = `78f1f99b…`, rev15 = `0162561c…`(R15-7, 봉인 커밋 `cc0d9b8`), rev16 = `b3899194…`, rev17 = `9400660e…`, rev18 = `3693a69c…`(rev18 R18-1 2, 봉인 파일 커밋 S6 `59c933b`), rev19 = `7f87b8bb…`(rev19 R19-8 2, 봉인 파일 커밋 S7 `38897f0`), rev20 = `615a8fbd…`(rev20 R20-4 2, 봉인 파일 커밋 S8 `4d8a95d`), rev21 = `ecd70949…`(rev21 R21-3 2, 봉인 파일 커밋 S9 `da12622`), rev22 = `a48a81f9…`(rev22 R22-2, 봉인 파일 커밋 S10 `570a9c1`), rev23 = `fa72e172…`(rev23 R23-2, 봉인 파일 커밋 S11 `f40935a`), rev24 = `f475cf77…`(rev24 R24-3, 봉인 파일 커밋 S12 `b75d874`), rev25 = `c0b778fd…`(rev25 R25-3, 봉인 파일 커밋 S13 `f381053`). rev13·rev14는 목록에 없고 `tools/verif/seal_check.py`로 확인한다(rev13 R13-7, rev14 R14-7). 묶음 등급 도구 `chrono_bundle_grade_4368.py`(9절)는 이 목록을 그대로 쓴다. 출력 `rules`는 설명 문자열(`RULES_DESCRIPTION`)이고, 대조 대상은 이 목록이다. rev11 R11-5: `judge` 출력(문서와 마지막 줄 요약)에 `grade_counts_R11_5`(등급별 행 수, 기록 전용)를 더했다. G-S에서는 행 등급을 판정하지 않으며 멈춤 사유가 아니다. `--out`은 필수다(R11-6).

## 7. rev8~rev10 반영: J-P3 범위, J11 입력·범위, LS 판별 (v3, python-expert 2026-11-13)

- **J-P3 적용 범위(R8-2, `j_p3_block`, 항목 `J-P3_R8-2`)**: 열린 루프가 아닌 모든 행에 적는다.
  - 행 태그 = `batch.json` argv의 `--expect-controller` 값(배치 정보가 없으면 SCM `result.json` `args.expect_controller`). 태그 확인(SCM `c2_setup.expect_controller.ok`, L2b·L1-R `expect_controller.ok`)이 거짓이거나 없으면 S-2(멈춤, rev9 R9-1. 그 전 v3는 J-P3 `not_judgeable`만).
  - ③ 판별은 `v5_options.is_extend_start_tag(태그)`뿐이다. ③이 아니면 `not_applicable`(해당 없음).
  - ③ 행: `controller_meta.two_pressure.settings.extend_start_rule`이 없으면 `not_judgeable`(원판 9.3), `tracked_bound`가 아니면 S-2. 같으면 개정 9 3.2 표(`extend_start_bound.j_p3_run_case`, 로드 판독 = `two_pressure.has_rod_sensor`, 헤드 전용 선언 없음)로 `hydraulics_record.extend_bound_check` `breach_reads` 합 0 = `pass`, ≥ 1 = H-7(멈춤), 기록 결함 = `setting_defect`(멈춤).
  - 요청 기록 대조: argv의 `--extend-start-tracked` 유무(배치 정보가 없으면 SCM `args.extend_start_tracked`)와 `v5_hydraulics.hydraulic_options.extend_start_tracked`(키 없음 = 끔, 블록이 없으면 대조하지 않음)가 태그의 ③ 판별과 다르면 S-2(멈춤).
- **J11(R8-3, `j11_block`, 항목 `J11_R8-3`)**: 개정 6 6절.
  - 잠금 상태: SCM `step_series.npz` `law_locked`(시간축 `t_s`), L2b `pads.npz` `law_locked`(시간축 `t`). 형식은 rev9 R9-2·R9-3(`law_locked_form`, gs-check와 같은 함수): 시간 열, [N, 4], int8, 값 {−1, 0, 1}, 인접 간격 |Δt − 1 ms| ≤ 10⁻⁶ s, −1은 처음부터 이어져 네 다리가 같은 표본에서 함께 벗어나는 꼴(`pre_arm_prefix`, 잠김으로 읽음)만 허용. 무장 뒤 −1(`after_arm`), 전 구간 −1(`whole_run`), 다리별로 다른 끝(`leg_mismatch`)은 형식 오류.
  - 창 끝: `r8_series.npz` `t`·`issued_u`로 `lock_window_alignment.lock_window_alignment`(규칙 함수, 고치지 않음)가 다시 계산하고, 감시기 `fallback_lock_log`·`fallback_lock_current`와 10⁻¹² s로 대조한다(어긋나면 S-11, 멈춤).
  - 대체 다리 = `fallback_lock_log` 다리 ∪ `WARN_ROD_PRESSURE_FALLBACK` 다리(R6-B7). 대체 다리 n_late = 로그·현재 구간과 맞은 늦은 구간 + 사건에만 있는 다리의 늦은 열린 구간. C-5 행에서 > 0이면 멈춤이고, 멈춤 코드는 아래 LS 판별로 정한다(LS 행 L-e, 그 밖 H-7). C-5가 아닌 행은 `late_recorded`로 기록만 한다. 모든 다리 n_late·unjudged는 기록이다.
  - LS 판별(`ls_setting`, rev9 R9-4, 사용자 결정 13): `--manifest`(기본 `06_analysis/02_control/verif_matrix/v5_resume_4368/chrono_rows_manifest.json`)의 `batches.<묶음>.rows[]`(배치 폴더 이름 `batch_<묶음>_<시각>`의 묶음, 없으면 전체 묶음에서 같은 `case` 행 하나)의 `v5_setting`과 S9 배치 폴더(`07_results/S9/batch_V5-RESUME-K1-<묶음>_<stamp>/`, 러너 결과 폴더의 것은 쓰지 않음) `batch.json` `cases[]` 같은 행의 `v5_setting`이 같고 LS1~LS4이면 LS 행(L-e), 같고 그 밖 값이면 LS 아님(H-7), 둘 다 없거나 None이면 LS 아님. 한쪽에만 있거나 둘이 다르거나 manifest 행이 없거나 여럿이면 판별 불가이고, 그 C-5 행에 늦은 대체 다리가 있으면 `not_judgeable` + 멈춤(사유는 `problems`·`ls_setting.reason`). 행 이름은 쓰지 않는다. LS 행인데 태그가 ③ 켬이 아니면 S-2(`J-P3_R8-2`). 출력 `ls_manifest`에 manifest 경로·sha256을 적는다.
  - 감시기에 잠금 구간이 없으면(로드 판독 없음 등) 대체 다리가 있을 때 `not_judgeable`, 없을 때 `not_computed`(R3-C7).
  - 대상 행은 `criteria_id` = C-5다(rev9 R9-6). C-5 행(SCM·L2b 같음, rev9 R9-5: rev8 R8-3 4항과 rev3 R3-C7의 `not_computed` 처리를 대체)에서 `law_locked`가 없거나 형식이 틀리면 `not_judgeable` + 멈춤이다. 다른 기준 행은 늦은 대체 다리를 `late_recorded`로, 입력 결측·형식 오류를 `no_input`(입력 없음)으로 기록만 한다. `--row`(기준 모름)는 `not_judgeable`로 적되 멈추지 않는다.
  - G-S의 키 있음·형식 확인(S-11)은 `v5_resume_4368_chrono_rows.py gs-check`가 한다: level 행 `series_keys_missing`·`series_key_problems`·`law_locked_minus_one`, L2b 행 `pads_law_locked_missing`·`pads_law_locked_problems`, 닫힌 루프 행 `expect_controller_ok`(R9-1), 모든 행(열린 루프 포함) `batch.json` `code_at_launch.git.head`가 40자리 커밋인지(`code_at_launch_head_ok`, rev11 R11-4). rev12 R12-3부터 gs-check도 `--git-at-start <최종 Y 커밋>`(필수, 없거나 형식이 틀리면 종료 2)을 받아 judge와 같은 R11-4 대조(`commit_identity_of`)를 행마다 하고 S-12인 행은 실패다(`commit_identity_ok`, 요약 `commit_identity_R11_4`). 열린 루프 행 `result.json` `code_state`는 필수 키가 아니고 기록만 한다(R12-4).
  - **커밋 정체성(rev11 R11-4, `commit_identity`, python-expert 2026-11-13)**: `judge`는 `--git-at-start <판정서 git_at_start>`(7~40자리 소문자 16진, 필수, 없거나 형식이 틀리면 종료 2)를 받아 열린 루프를 포함한 모든 행의 `batch.json` `cases[].code_at_launch.git.head`를 대조한다. 기록 없음·`git.error`·`head` 없음·다른 커밋이면 S-12(멈춤, `stops`). level·L2b·L1-R 행은 `result.json` `code_state.git_at_start`(L2b·L1-R은 행 로그로 찾은 러너 폴더의 result.json)와도 대조한다. 그 기록이 있는데 오류이거나 다른 커밋이면 S-12이고, 기록이 없으면 `no_result_record`로 적고 멈추지 않는다(R11-4 4항 "그 기록이 있는 행"; 지금 run_S8C·run_S6C는 이 기록을 쓰지 않는다). 열린 루프 행의 result.json 커밋은 기록만 한다(rev12 R12-4, `result_same_as_git_at_start`). `git.clean`·`dirty`·`paths`는 기록만 한다(rev12 R12-2). `--row` 입력은 `batch.json` 항목이 없어 `no_batch_entry`로 적고 멈추지 않는다(`--row` 기준 처리와 같음). 출력 `commit_identity_R11_4`(행별, 요약 `counts`·`s12_rows`·`dirty_rows_recorded`), 마지막 줄 요약에도 있다. 행 등급 수는 `grade_counts_R11_5`(기록 전용, R11-5).
- **LS 판별 입력 경계(rev10 R10-1, `batch_full_name`·`ls_setting`)**: 묶음은 전체 묶음 이름(`V5-RESUME-K1-` 접두어 포함)이다. S9 배치 `batch.json` 최상위 `batch` 값을 폴더 이름의 `batch_`~`_<YYYYmmdd_HHMMSS>` 부분과 대조해 쓰고, 키가 없으면 폴더 이름 부분을 쓴다. 다르거나 정할 수 없거나 manifest `batches` 키가 아니면 묶음 이름 불명이다. 묶음 이름 불명, manifest 같은 `case` 행 0개·여럿, `batch.json` `cases[]` 같은 `case` 0개·여럿은 LS 판별 불가(`ls_setting.boundary_case`)이고, 두 출처 모두 행이 하나씩 있고 둘 다 `v5_setting`이 없거나 None일 때만 LS 아님이다. manifest 파일이 없거나 JSON이 아니거나 `batches`가 없으면 입력 오류(종료 2, 묶음 판정 안 함, S-11). G-S 확인(R10-2, `ls_source_check`)은 gs-check가 행마다 하며 어긋난 행은 실패다(`--rows-manifest`, 기본 저장 manifest; 출력 `ls_sources_R10_2`). `rev8_counts`의 `R10-1b_cases`에 경우별 행 수를 적는다.
- 묶음 요약 `rev8_counts`: J-P3 상태별 수(해당 없음 = `not_applicable`), S-2 행 수, J11 상태별 수, 판정 불가 C-5 행 수, rev9 R9-8 G-S 기록 항목(`R9-1_expect_failed`, `R9-2_form_problems_by_item`, `R9-2_key_missing`, `R9-3_minus_one`, `R9-4_ls_rows`·`R9-4_undecided`, `R9-6_no_input`). 마지막 줄 JSON에도 있다.
- 2026-11-13 G-S `…_082117`(기록 추가 전)에 돌리면 C-5 SCM 행 셋이 J11 멈춤이다(R8-4가 예상한 결과). `7527fc3` 기록 행(3.6 s VB)은 J-P3 `pass`, J11 대체 다리 없음(`no_fallback_leg`)이다.

## 7a. rev24 공통 정의 CD-3·CD-5 (행 판정 도구, python-expert 2026-11-15)

- **사건 행 판별(CD-3, `event_row_kind`, L2b 행)**: 닫힌 판별이다. 실행 설정 `settings.event`가 `settle_RR_30`·`drop_RR_30`·`drop_RR_30_probe`면 바닥 사건(`floor`), 그 밖에 `result.json` `event.spec`의 `kind` settle, `leg`가 네 다리 가운데 하나, `depth_m` 있음, `event_t_s`가 null이 아님, `depth_m`/`ramp_s` > v_max 20.924 mm/s(`ramp_s` 0·없음 = 무한 속도)면 빠른 침하(`fast`), 그 밖은 비사건 행이다. `event_t_s`가 있다는 것만으로는 사건 행이 아니다(`E_G4_` 7행, 5.75 mm/s = 비사건). L1-R 행은 이 블록 밖이라 앞 판 그대로다.
- **W(`event_window`)**: t_event = `event_t_s`(바닥 사건에 없으면 첫 READY + 5 s), T_3 = `s6_control.THREE_POINT_ROCKING_PERIOD_S[level]`(상단 0.82 s). 바닥 사건: W 끝 = min(RR 마지막 재접지 + T_3, t_event + 5 s), 재접지 = t_event 뒤 RR `pads.npz` `N` ≤ 0인 마지막 1 ms 표본의 다음 표본, 부상 없으면 t_event, 끝까지 떠 있으면 t_event + 5 s. 빠른 침하: 원 판정기 U-S8-32 분할(`s8_control.settle_lift_split`, `airborne`·`ball_centre_world`)로 W 끝, 그 기록이 없으면 t_event + 5 s. 창을 정할 수 없으면 `not_judgeable`, 사유 `사건 창 결정 불가: …`.
- **항목(`event_pressure_items`, `record.npz` 10 Hz 행)**: W 밖 신장 표본(u_applied > 10⁻⁹ m/s) 헤드 F_cyl/A_p ≤ 180 bar(`outside_extension`), W 밖 수축 표본 최대는 기록(`outside_retraction_record`), W 안 모든 상태 ≤ 350 bar(`inside`, 최대·다리·시각·상태), 포화 = W 밖 신장 표본 ≥ 210 bar 수 0(`saturated_samples`). 항목 키는 `moving_pressure_D-32`(사건 행은 `row_kind`, `window`, 판별 기록 `event_test_CD_3`; 비사건 행은 앞 판 D-32 그대로 + `event_test_CD_3`).
- **원 판정기 창 끝과의 차(`runner_event_window`, 새 선택 인자 `--runner-judge-dir`)**: `<C1|C2|C5>_<case>.verify_S8C.json`의 `metrics[]`에서 `case` = 행 폴더 안쪽 이름인 항목의 `event_window.pressure_end_s`(설정 시작 상대 시각). 차 > 0.1 s + 10⁻⁹ s이거나 그 끝으로 다시 계산한 W 밖·W 안·포화 판정이 달라지면 `runner_window_CD_3.stop` = 참이고, 묶음 집계 도구가 그 묶음을 멈춘다. 인자가 없거나 파일·기록이 없으면 상태만 적는다.
- **READY 없음(CD-5, rev25)**: `ready_items`는 첫 READY가 없으면 READY ≤ 120 s를 `fail`(사유 `READY 없음`)로 두고 P3-6 기록은 비운다(rev25: P3-6은 판정하는 C-5 SCM 행에서만 미달, 기록인 행은 `해당 없음(READY 없음)`이고 묶음 집계 도구가 정한다). `g6_grade`는 G6-1을 재접촉 조건만으로, G6-4·G6-5를 `not_applicable`(등급에서 뺌), G6-6·READY ≤ 120 s를 `fail`로 두고 사유를 `gate_reasons_CD_5`에 적는다.
- 표시 문구: SCM 행의 427.9 안전 종료 항목 사유를 `rev6 R6-B8: not a 427.9 soil-guard safe-stop row (rows S-01 .. S-04)`로 고쳤다(C-5 행에 "C-8" 문구가 나오던 곳).

## 8. 시험

`05_tests/unit/test_chrono_rows_judge_4368.py`: 시험 72개(옛 값(R3d `0220671` 판, rev24 전) 51) = 합성 입력 70개(v2 행 폴더 찾기 7개·열린 루프 건너뜀 1개·z4372 엔진 기록 2개·rev15 R15-3 V0 L2b 10 Hz 구간 7개·rev15 봉인 2개·rev16~rev25 봉인 2개·rev21 R21-1 t_lift,sus 6개·rev24 CD-3·CD-5 21개(사건 행 판별 7: 바닥·빠른 침하·0 램프·램프 없음·느린 침하·null `event_t_s`·`event_t_s`만; 바닥 W 4; `event_t_s` 없는 바닥; 빠른 침하 W; W 안·밖과 포화; 창 끝 차 2; 차 ≤ 0.1 s지만 판정이 바뀜; 창 결정 불가·러너 파일 없음; 비사건 행; READY 없음 2)·그 밖의 판정 정의 17개(이탈 100 표본, 재접촉 지속, P3-2 순서·하중, LOC 시간선 철회, P3-8 5, 이동 압력 문턱, D8 부상 시각 조건, Q14 부상 표본, C1 보류 판정 불가·멈춤, SCM 행 G6 통과·t_D 기록, SCM 행 SGS 행정 제한 멈춤, S-11 2: 단계 시간 기준 혼합·사건 없는 다리의 대체 로그)·봉인·CLI·정의 5개(봉인, 입력 없음 종료 2, 가정 덮어쓰기 이탈 표시, 공개 셈, rev6 정의) 포함)와 G-S 실행 경로 2개(`07_results/S9/batch_V5-RESUME-K1-GS_20261113_020211`, `..._082117`. 판정 아님, 없으면 건너뜀). 082117은 rev8부터 종료 1(C-5 SCM 행 셋의 J11 멈춤, 기록 추가 전 배치), L1-R 폴더 `_082118`을 행 로그에서 찾음, C-6 행 건너뜀을 확인한다. rev8·rev9 항목은 `test_resume4368_rev8.py`·`test_resume4368_rev9.py`, gs-check의 rev9 항목은 `test_v5_resume_4368_chrono_rows.py`.

## 9. 경로 1 묶음 등급 집계 `chrono_bundle_grade_4368.py` (rev18 R18-2, rev19 R19-1~R19-6, rev21 R21-1·R21-2, rev22 R22-1, rev23 R23-1, rev24 R24-2, rev25 R25-2, python-expert 2026-11-16)

- 이 도구는 시뮬레이션·다른 판정기를 돌리지 않는다. 이미 만든 출력과 실행 파일(`result.json`, `step_series.npz`, `pads.npz`, `record/record.npz`, `soil_event_series.npz`)만 읽어 묶음 등급(C-1·C-2·C-3·C-5)과 기록 상태(C-4, C-6·C-7, C-8)를 낸다. 봉인 목록과 커밋 정체성·manifest·YAML 함수는 `chrono_rows_judge_4368.py`의 것을 import해 쓴다(같은 봉인 목록: 원판~rev12, rev15~rev25, rev25 R25-3).
- 실행(`--git-at-start`는 R2, R18-4):

```
python -I -B -X utf8 04_scripts/02_chrono/chrono_bundle_grade_4368.py grade --bundle C-1 --git-at-start <R2> \
    --batch <07_results/S9/batch_V5-RESUME-K1-C1_<stamp>> --rows-judge <judge_C1.json> \
    --runner-judge-dir <runner_judge> [--params 02_params/rexome33.yaml] --out <bundle_C1.json>
... grade --bundle C-5 ... --t45 <t45_C5.json>          # chrono_t45_replay --t5 (rev7) 출력
... grade --bundle C-6C7 --git-at-start <R2> --batch <...C6C7_<stamp>> --out <bundle_C6C7.json>
... grade --bundle C-8 --git-at-start <R2> --batch <...OC5_<stamp>> --oc5 <oc5_C-8a.json> --oc5 <oc5_C-8b.json> \
    --fmin-time <fmin_C-8a.json> --fmin-time <fmin_C-8b.json> --rows-judge <judge_OC5.json> --out <bundle_C8.json>
... grade --bundle C-4 --git-at-start <R2> --batch <...C4_<stamp>> --rows-judge <judge_C4.json> --out <bundle_C4.json>
... seals [--rules-dir <verif_matrix>]
```

- 종료 코드: 0 멈춤 없음, 1 멈춤(S-15, S-12, S-11 러너 셈·폴더, H-7, R40-2 보류, S-2, J11, T4-0·설정 불일치, VB 고유 실패, R19-5 t_lift 차, rev24 CD-3 창 끝 차, CD-7 사유 빈 칸, CD-11 항목 목록, C-8b S-9·S-10) 또는 봉인 불일치, 2 입력 없음·잘못됨, 3 내부 오류. 마지막 줄 JSON, 그 앞 줄 `errors N`. `미달`은 판정 결과이므로 종료 0이다.

| 항목 | 정의 |
|---|---|
| 행 열거·행 수(S-15) | `--batch`의 `batch.json` `cases[]` 가운데 묶음 `criteria_id`(C-6C7 = C-6·C-7·C-7a·C-7b, C-8 = C-8a·C-8b) 행. 각 행이 manifest 그 묶음의 행이어야 하고 수가 C-1 10, C-2 6, C-3 2, C-4 4(rev24 CD-9), C-5 35, C-6C7 3, C-8 2와 같아야 한다. 다르거나 manifest에 없는 행·중복이 있으면 S-15이고 등급을 내지 않는다. 행 0개도 등급 없음 |
| 행 역할(R19-2) | `batch.json` `d1_role`: `record`(C1-09~12)·`timing base`(PS-c 기준 행) = 기록 행(묶음 등급 밖, `record_status` 기록 완료/불완전, 실패·판정 불가는 `record_rows_reported`). PS-c 기준 행은 E 항목을 계산하지 않는다(결측 아님). `judge…`·없음(C-5) = 판정 행 |
| L2b·L1-R 행(R19-4) | 러너 판정기 출력 `<C1\|C2\|C5>_<case>.verify_S8C.json`·`.verify_S6C.json`(`--runner-judge-dir`, `judge_b9f5707\chrono_path1\runner_judge\` 꼴)의 그 행과 `*` 행. 러너 부분 등급(`items[0]` `runner`) = `passed` 거짓이 하나라도 있으면 미달, 아니면 hold(또는 입력 없는 재계산 항목)가 있으면 판정 불가, 아니면 판정 종류 `passed` 참 항목이 0개면 판정 불가(빈 통과 막기), 아니면 FLAG/통과. 셈 대조: 파일 전체의 `passed` 거짓 수·`kind` hold 수 = `meta.failed`·`meta.hold`(없으면 0), 다르면 S-11(`runner_count_check_R19_4`). `meta.batch` 폴더 이름이 `chrono_rows_judge`가 찾은 러너 폴더와 다르면 입력 오류(S-11). 러너 항목 전체는 `runner_items`(분기 `branch`) |
| 재계산 항목 덮어쓰기(rev24 CD-2 닫힌 표, 항목 이름 전체 완전 일치) | `C1 D8 min true rod force (raw 1 ms, after lift-off, outside REANCHOR) >= F_min + 5 kN` ← `C1_R40`(D-31·D-39, 모든 L2b 행), `4 max moving pressure` ← `moving_pressure_D-32`(D-32, 비사건 행만), `4 max moving pressure outside the event transient` ← W 밖 신장 ≤ 180 bar, `4 max pressure in the event transient` ← W 안 모든 상태 ≤ 350 bar(사건 행만, 행 판정 도구 CD-3 판별), `4 saturation steps` ← 포화(비사건 행 신장 표본, 사건 행 W 밖 신장 표본, 모든 L2b 행). 앞부분만 같은 이름(예: `C1 D8 min true rod force (raw 1 ms) …`)과 적용 행이 아닌 행의 줄은 원 판정기 셈 그대로다. 창을 정할 수 없으면 사건 항목은 판정 불가(사유 `사건 창 결정 불가`). 행 판정 도구의 `runner_window_CD_3.stop`(원 판정기 창 끝과 차 > 0.1 s 또는 판정 변화)은 그 묶음을 멈춘다. 바꾼 항목에는 `override_reason`이 붙는다. L2b 행의 `D8 min true cylinder force >= F_min + 5 kN`(`pads.npz` `F_cyl_min_interval` 최소, 러너 문턱)·`D8 no pad lift-off`(`pads.npz` `N` ≤ 0 1 ms 표본 0개) ← D-29 t_lift부터 실행 끝(R19-5). D-29 t_lift가 없으면 D8 항목은 판정 불가. 행마다 `overrides[]`에 러너 값·재계산 값·D-29 t_lift를 남긴다. 러너가 기록 종류로 낸 항목은 기록 그대로 둔다 |
| 러너 t_lift(R19-5) | 러너 값을 그대로 쓰는 넷: `3 F_min (1 ms)`, `3 F_min before the event`, `5a rocking amplitude`, `F2 lower-bound soundness`. L2b 행에 러너 t_lift 항목(D8 셋 포함 일곱)이 하나라도 있으면 차를 계산한다: 러너 t_lift = `s8_metrics.<case>.liftoff_s` + 행 `t0_s`, D-29 t_lift(rev21 R21-1·R21-2: 1 ms t_lift,sus, 기준 `1ms_sus`)는 `record.npz` `t` 배열에서 t ≥ t_lift,sus − 10⁻⁹ s인 첫 표본으로 올리고(정수 연산·ceil 없음), t_lift,sus가 없으면 그 묶음 멈춤, 기준이 `1ms_sus`·구간 대체가 아니면 계산 불가(멈춤)이며, 10 Hz 구간 대체(R15-3)면 그대로. 차 > 0.1 s + 10⁻⁹ s 또는 계산 불가면 멈춤. 출력 행 `t_lift_check_R19_5`, 묶음 `runner_t_lift_R19_5`(`checks`, `max_difference_s`, `stop_rows`) |
| SCM 행(P3) | `p3b.checks`와 재계산 항목: P3-1 = 크롤러 0(`P3-1_crawler_zero_after_ready`) ∧ D-36 재접촉(FLAG 받음), P3-2 = D-37·D-38 `within`(거짓이면 늦은 LOC FLAG가 있을 때 FLAG), P3-3 = R6-B4 t_D 뒤 `within`, P3-4 = `P3-4_verdict`, P3-5·P3-6·P3-7 = `within`, P3-8 = D-34·D-35 판정, P3-9 = FLAG 수(기록 FLAG), FAULT0 = `has_fault` 거짓. None은 판정 불가(원판 9.3). rev24 CD-5(첫 READY 없음, 행 판정 도구 `ready_D-27_D-28.t_ready_rel_s` = null): P3-1은 재접촉 조건만 판정(크롤러 0 조건 `해당 없음(READY 없음)`), P3-4·P3-5 `해당 없음(READY 없음)`(등급 밖), P3-6 미달, 나머지는 그대로. 해당 없음과 기록을 뺀 등급 항목이 0인 행은 판정 불가 |
| 사유(rev24 CD-7) | 판정 불가·러너 미판정·해당 없음 항목과 판정 불가 행에 한 줄 사유(`reason`, 행 `grade_reason`; `원 입력 결측: …`, `READY 없음`, `사건 창 결정 불가`, `원 판정기 보류(hold)`, `러너 미판정: <note>`), 재계산으로 바꾼 러너 항목에 `override_reason`. 사유가 빈 항목·행은 `reasons_CD_7.gaps`에 적고 그 묶음을 멈춘다(CD-7 멈춤) |
| 항목 목록(rev24 CD-11) | `item_list_CD_11`: 행마다 등급에 쓴 항목(`common_id` = 원 판정기 항목 이름·`P3-n`·`FAULT0`·`T4`·`T5`·`J11`·`J-P3`·CD-3 `W 밖`·`W 안`·`포화`·`E-n`, `item`, `source`, `method` 원 판정기 실행/재계산, `interval`, `verdict`, `reason`). L2b 행은 러너 항목을 하나씩 싣는다(러너 항목이 없으면 러너 부분 등급). 목록 행 수 ≠ 묶음 행 수이거나 등급 항목이 없는 행이 있으면 멈춤(CD-11) |
| S-01~04(R19-1) | 첫 `FAULT*` 사건이 `FAULT_LIFT_STROKE_LIMIT:soil:`이면 이 도구가 실행 파일에서 조건 1~5를 계산해 그것만으로 `allowed_stop`/`fail`: 2 = `FAULT_STROKE_END` 사건 0, 3 = 첫 LEVEL `s9_rows` 행 시각부터 끝까지 `step_series.npz` `scm_pad_normal_N` ≤ 0 1 ms 표본 0, 4 = t_D(R6-B4 100표본, 없으면 거짓)부터 다리별 1 ms `F_cyl_N` 최소 ≥ F_min(YAML), 5 = `record.npz` 10 Hz 행 실행 전체 이동 최대 ≤ 180 bar·포화 0(`moving_pressure`, 두 값 따로). 입력 결측은 판정 불가. P3-1~P3-9·FAULT0·(S-03·04) G6는 기록(`record_items`). 기록으로 내리는 것은 이 등급 항목뿐이다(rev20 R20-2): 안전 종료 행에도 S-12 커밋 정체성(이 도구), `chrono_rows_judge`의 멈춤(S-2 태그 등, `stops`), J-P3는 그대로 걸리고, 원판 4.2·7.2는 R18-2a view의 `resume4368_judge.py record-check`·`k1-class`가 행 등급과 따로 판정한다 |
| C-3 | 토양 가드 정지가 아니면 `chrono_rows_judge` G6 등급(`stroke_limited_stop` = `allowed_stop`) + G6에 없는 P3-7 |
| PS-c 사건 행(R19-3) | `d1_select` psc인 판정 행: `soil_event.judgement.gates`의 E-1~E-7(러너 어댑터 `run_S9.judge_chrono_soil_event`가 가지 창 사건 − 0.5 s ~ `soil_event_stop_s`로 계산한 값; 느린 사건의 E-2는 해당 없음, 빠른 사건은 E-2 필요), 집단마다 게이트가 하나도 없으면 판정 불가, FLAG는 `flags`의 같은 번호. 행정 `stroke_max_run_mm` ≤ 684.8 mm. 기록: `branch_window`(`t_ev_s`, `stop_rel_s`, `stop_reason`), `after_branch`(가지 끝 뒤 `soil_event_series.npz` 다리별 최소 F_cyl·부상 표본 수), `p3b` |
| J-P3·J11 | J-P3(rev8 R8-2)는 ③ 행만: `pass` 통과, `H-7` 실패, 그 밖 판정 불가. J11은 C-5에서 판정(`pass`·`no_fallback_leg`·`not_computed` 통과, H-7·L-e 실패), 다른 묶음은 기록 |
| C-5 T4·T5 | 개정 6 3 18행(VB 12 + LS 6)에 `chrono_t45_replay`(개정 7, `--t5`) 행: 설정 불일치·T4-0 실패 = 판정 불가 + 멈춤, T4·T5 초과 ≥ 1 = 실패 + H-7. 출력이 개정 7이 아니면 입력 오류. 개정 6 4.6 문구를 `t4_t5_phrase`에 적는다. D2는 기록 |
| C-5 t45 짝짓기(rev22 R22-1) | t45 행은 이름이 아니라 **t45 입력 폴더 순서**로 판정 행에 짝짓는다(LS1·LS4·VB 행은 바깥 러너 폴더만 다르고 안쪽 이름이 같아 t45 `case`가 겹친다). 목록 = `--rows-judge` `judge_C5.json`의 `rows` 순서에서 `case`가 `T45_CASES`(18개)에 완전 일치(대소문자 구분)로 드는 행의 `dir`. 근거 사슬: `--t45-cases-script`(R3c 실행 스크립트)의 `$T45Cases` = `T45_CASES`, 대소문자 무시로 고른 목록 = 완전 일치 목록, `--t45-reference-judge`(R3c `judge_C5.json`, sha256 = `--t45-reference-sha256`, 기본 R3c `c1ba9382…d76a`)에서 만든 목록 = 위 목록(원천 고정), 빈 `dir` 없음, `--t45-folders`(선택, JSON 목록 또는 줄마다 한 경로)가 있으면 같은 목록. 대조: 1 t45 행 수 = 폴더 수(다르면 S-15), 2 i번째 판정 행 `dir` = i번째 폴더, 3 t45 `case` = 폴더 안쪽 이름, 4 폴더·판정 행 이름 중복 없음 ∧ 이름 집합 = `T45_CASES`(2~4·근거 사슬 거짓은 S-11). 멈추면 짝을 비워 T4·T5가 판정 불가가 되고 등급을 내지 않는다. 기록 블록 `t45_pairing_R22_1`(`folders`, `folders_sha256` = 경로를 줄마다 `\n`으로 끝내 이은 UTF-8의 sha256, `sources`, `checks`, `pairs`, `ok`). `t45_item` 판정 로직·문턱은 그대로 |
| 러너 이름 대응(rev23 R23-1) | 위 두 행(L2b·L1-R 행, 러너 t_lift)의 "그 행"과 `s8_metrics.<case>`는 **판정 행 `dir`의 안쪽 이름**(행 판정 출력에 적힌 `dir` 문자열의 마지막 경로 이름, 대소문자 구분 완전 일치)으로 찾는다. LS·V0 행은 VB 케이스를 돌려 러너 행 `case`와 `s8_metrics` 키가 VB 이름이다. 러너 판정 파일 이름(판정 행 이름)과 `meta.batch` 대조, 결측 문장(`runner judge rows of` + 판정 행 이름)은 그대로다. 대조(거짓이면 S-11, 사유 `S-11: check <이름> false (rev23 R23-1)`, 멈춤 목록 `case` = 판정 행 이름, 등급 없음): 1 `1_dir_set` 판정 행 `dir`이 비지 않음, 2 `2_dir_unique` 묶음의 대응 기록 행끼리 `dir` 전체 경로가 겹치지 않음(`dir` 없는 행은 뺌), 3 `3_runner_row_cases` 파일 안 `*`가 아닌 행 `case`가 모두 안쪽 이름, 4 `4_s8_metrics_keys` `s8_metrics`가 있으면 키가 모두 안쪽 이름. 행 판정 출력에 행이 없으면 1~4 모두 null(기존 결측), 러너 판정 파일이 없으면 3·4 null(기존 결측). 안쪽 이름 행이 없으면(`*`만) 기존 결측, 안쪽 이름 키·`liftoff_s`가 없으면 기존 R19-5 계산 불가 멈춤. 기록 블록 `runner_name_map_R23_1`(`rule`, `rows`, `name_differs_count`, `ok`): `rows`는 L2b·L1-R 행마다 묶음 행 순서로 `case`, `dir`, `inner_name`, `name_differs`, `runner_file`, `runner_meta_batch_name`, `runner_row_cases`(정렬), `runner_rows_found`, `s8_metrics_keys`(정렬, 블록 없으면 null), `checks`, `ok`. 행 출력 `rows[]`와 R19-4·R19-5 블록의 키는 그대로다 |
| C-5 짝(R19-6) | C-5 `batch.json` 행과 manifest C-5 행 이름의 합집합에서 찾은 VB↔V0 짝(`<case>_V0`·`_v0v`)이 개정 12 2.1의 6쌍과 정확히 같아야 한다. 다르면 S-15, 등급 없음(`vb_v0_pairs_S15`, `found_in_batch_json` 함께). VB 실패 ∧ V0 통과 = 멈춤(개정 12 2.2). 짝 등급은 `pairs_record`(기록) |
| 묶음 등급 | 판정 행의 최악(판정 불가 > 실패 > FLAG > 통과, `allowed_stop`은 통과 쪽, 사용자 결정 65). 결측 입력이 있는 행은 판정 불가. 멈춤이 하나라도 있으면 `grade`는 비우고 `grade_without_stop`에 둔다(원판 8.2). 행 문구 `row_phrase` = `통과 n / 안전 종료 m`(명세 427.9 "따로 센다"), 미달·판정 불가는 있을 때만. `러너 미판정`은 `runner_unjudged_R19_4`(수, 행, 항목 이름별 수, 목록 밖 `kind`) |
| C-6·C-7 | `p3a.checks` P3a-1~5와 `P3a-9_min_cylinder_force.before_liftoff.any_flag`(명세 11047 FLAG). 하나라도 없으면 그 행 `기록 불완전`. P3a-1 실패·`abort`는 `report_separately` |
| C-8 | `resume4368_judge.py oc5`(m, 분류)와 `fmin-time`(8 s 창 시간) 출력을 행 이름으로 붙인다. 없거나 `기록`이 아니면 `기록 불완전`. C-8a S-9는 rev18 R18-5(사용자 결정 60 (A))로 처리됨을 적고 멈추지 않는다. C-8b S-9와 S-10은 멈춤. rev24 CD-8 기록 값(`record_values_CD_8`, 하나라도 없으면 `기록 불완전`, 사유 `record_reason`): oc5 `values`의 `F_min_after_N`·`F_min_transient_N`(원판 7.4 a·t)·`t_min_after_s`, `las_start_s`·`las_end_s`·`las_end_reason`, `k1_decisions`(빈 목록도 값), `R_c_operating`·`crawler_attitude_deg`·`floor_roll_deg`·`floor_pitch_deg`, fmin-time `F_below_F_min.ms`·`F_below_F_min_plus_2kN.ms`, `result.json` `p3b.checks.P3-3_within`, 크롤러 강성 배수 k(`meta.rigid_base.crawler_kn_scale`), P3-1~P3-9(`--rows-judge` `judge_OC5.json`로 위 SCM 행 P3 정의, CD-5 포함), D8·G6는 `해당 없음`(SCM 행·C-3 아님). m·최소 다리가 R3d 출력과 같은지(CD-8 S-9 처리 조건)는 실행 스크립트의 K-10 비교가 본다 |
| C-4(rev24 CD-9) | 기록 묶음 4행(`--rows-judge` `judge_C4.json`). 행마다 P3-1~P3-9·FAULT0(위 SCM 행 정의, CD-5; 강체 바닥 `args.rigid_base` 행의 P3-5 = `해당 없음(rigid_base)`, 결측으로 세지 않음), t_D(`departure_t_D`), 다리별 이탈 뒤 최소 실린더 힘(`p3b.P3-3_leg_force.F_min_after_N`·`t_min_after_s`)과 최소 다리·시각, 실행 R_c(`p3b_ext.start_condition.R_c_operating`). 모두 있으면 `기록 완료`, 하나라도 없으면 `기록 불완전`(사유 `record_reason`). 묶음 `record_status`. rev24 결함 수정(rev25 R25-2 2): CD-7 빈 사유 검사(`reasons_CD_7`, 빈 칸이면 멈춤) |
| rev25 변경(R25-2, 공통 블록 rev25) | **P3-6(CD-4)**: 폐루프 시작 기준 첫 READY(`p3b.P3-6_ready.t_ready_after_loop_start_s`) ≤ 명세 421.1 한계(+10⁻⁹ s). 한계 = 실행 인자로 다시 정한 값(`p36_limit`: 바닥 경사 120 s, 평지·패드 B·후방 두 패드 J1/J2/S1 100 s, 그 밖 90 s; 후방 토양은 `soil_patch` `LEG:SET`이 덮으면 그 세트). P3b `limit_s`와 다르면 그 묶음 멈춤. C-5 SCM 행에서만 등급 항목, 그 밖(C-2 427.9·PS-c 기준 행, C-3, C-4, C-8)은 기록. READY가 없으면 등급 행은 미달, 기록 행은 `해당 없음(READY 없음)`. **P3-9**는 모든 행에서 기록(`record_items`). **CD-8**: 위 C-8 값에 더해 1 ms `step_series.npz`로 다리별 a(t_D~끝)·t([t_D, t_D + 8 s)) 최소와 각 시각(`F_a_min_N_by_leg`·`t_a_s_by_leg`·`F_t_min_N_by_leg`·`t_t_s_by_leg`, oc5 값과의 일치 `a_t_match_oc5`), O-C5 P3-5 = `해당 없음(rigid_base)`, SCM D8 ①~④(`D8_t_lift_s` = `scm_crawler_normal_N`의 t_lift,sus, `D8_F_min_after_t_lift_N`·`D8_F_min_leg`·`D8_F_min_t_s`, `D8_end_attitude_plus_mount_deg` = 마지막 5 s `roll_pitch_deg` 절대 최대(목표 0) + 0.02°, `D8_pad_lift_samples`), G6 값 `G6-6`·`READY_le_120s`(나머지 관문은 P3 값). 앞 판의 D8·G6 `해당 없음` 표기는 없앴다. **CD-11**: 열 `class`(등급 항목·관문·기록), `clause_id`(CD-2 표 n줄, CD-4 P3-n·FAULT0, CD-11 G6 대응표, CD-6, CD-1 ①, 명세 426.3 E-n, 명세 427.9 조건 n, CD-11 관문·기록), `description`; 공통 ID는 러너 항목 이름 전체(`W 밖` 등 rev24 ID는 없앰), case `*` 러너 항목은 `[case *]` 접미; C-3 G6 항목은 대응표 여덟 ID로, 427.9 항목은 `427.9-1`~`427.9-5`로 펼침(행 등급 셈은 그대로); 관문 `R11-4`·`R9-1`·`identity`·`K1_class`(뒤 둘은 실행 스크립트 view 단계에서 보며 이 도구는 자리만 적음)·`T4-0`·t_lift 차 확인·사건 창 끝 차 확인, 묶음 관문 `행 수 검사`; ③ 끔 행 J-P3 = `해당 없음(③ 끔)`; 기록 행(역할 record)은 "등급 항목 ≥ 1"에서 뺀다; PS-c 사건 행의 등급 항목은 E-1~E-7(`명세 426.3 E-n`)이고, 행정 684.8 mm 항목 `stroke_le_684.8mm`은 E-5 아래 기록(조항 ID `명세 426.3 E-5 (stroke limit 684.8 mm, record under E-5)`)으로 싣는다(행 `items`와 등급 셈은 그대로) |

**러너 행 분기**(`runner_verdict`, rev19 R19-4). 실제 출력의 `kind` 값은 2026-11-15에 메인 checkout `07_results/S8`·`S6`과 `judge_b9f5707\chrono_path1\runner_judge\`의 `verify_S*C*.json` 67개에서 셌다(kind, passed: 행 수).

| 분기(`branch`) | 조건 | 결과 | 실측 |
|---|---|---|---|
| `hold` | `kind` = hold | 판정 불가 | 표본에 없음(`s8_control`이 R40-2 보류에 쓴다) |
| `record_kind` | `kind` ∈ record, report, info, consistency, comparison, pair, sensitivity, superseded, leak_compare | 기록 | s8: record None 15191, pair None 2578, report None 1463, sensitivity None 1376, consistency None 909, info None 443, comparison None 130, superseded None 15. s6_bundle_c: report None 791, consistency None 650, info None 114, leak_compare None 34. s6_control: record None 32 |
| `passed_true` / `passed_false` | 판정 종류(function, judged, anomaly, replay, quality) 또는 `kind` 없음, `passed` 참/거짓 | 통과 / 실패 | s8: function T 9751·F 95, judged T 8287·F 67, anomaly T 905. s6_bundle_c: function T 3719·F 290, judged T 1099·F 41, anomaly T 426, replay T 271. s6_control: judged T 82·F 2. kind 없음: function T 23, quality T 2 |
| `passed_true_flag` | 위 참 행 가운데 anomaly note에 `FLAG` 또는 행 `flag` 참 | FLAG | – |
| `anomaly_flag` | anomaly, `passed` None, note에 `FLAG` | FLAG | s8 anomaly None 4(`WARN_ROD_PRESSURE_FALLBACK` FLAG) |
| `runner_unjudged` | 판정 종류, `passed` None | **러너 미판정**(기록, 실패·판정 불가 아님) | `2/5b window`(s8 15, s6 202), `3 lift-off RR time / ratio (report)`(s8 80, s6 45), `K8 shadow (B) - true floor`(s8 28, s6 270), `3 F_min after the re-READY`(8), `5a rocking amplitude after the re-READY`(8), `8 level trend time`(2), `I3 J_C: M4 max <= sensor share`(1), s6 `C-5a`·`C-5c`·`C-5`·`C-R5`·`T3` 행(40) |
| `unknown_kind` | 위 어느 목록에도 없는 `kind` | 러너 미판정(따로 표, `unknown_kind_items`) | 표본에 없음 |

- `judge_b9f5707` C-1 러너 출력 20개에는 판정 종류의 `passed` None 행이 없다.
- 결과 본 뒤 정한 정의(R18-0, rev19)다. 판정서에는 이 표와 출력 `rows[].overrides`·`t_lift_check_R19_5`·`runner_unjudged`를 싣는다.
- 도구 sha256(LF 바이트, R3f 경로 1 도구 커밋 판(R3d `0220671` + S12 병합 + rev24 R24-2 커밋 `086866a` + S13 병합 + rev25 R25-2 커밋 `3a61d4d` + `c3f4cad`(PS-c 행정 항목 `stroke_le_684.8mm`을 E-5 아래 기록으로 옮김, CD-11, 판정 전 감사) + `TOOL_VERSION` v8 커밋). 아래 표의 `chrono_bundle_grade_4368.py` 값은 v8 판이라 판정서 blob 표와 다르다. 판정서 blob 표와는 다음 줄의 R3f 판 `dd776429…`로 대조한다)
- `TOOL_VERSION`: `c3f4cad`에서 동작이 바뀌었는데 문자열은 v7 그대로였고, v8로 올렸다(문자열만 바뀜, 판정 로직·출력 키는 그대로). R3f `8a0c843`으로 만든 출력(`judge_8a0c843/chrono_path1`)에는 `c3f4cad`가 포함된 코드의 v7 문자열이 들어 있다(그 판의 sha256 `dd776429cb1e50f166030b6494a2f60af1d001cb8821ff48ded90adaa0982ae1`, 판정서 blob 표의 값).

| 파일 | sha256 |
|---|---|
| `chrono_bundle_grade_4368.py` | `2cda879b7cbc92211aa121348cf3f06e59be32732b6922796455b9e0b7045129` |
| `chrono_rows_judge_4368.py` | `dca1b3ab757b117c626ecc17148ae4fc2f1b5eb58cb5f1e2c5f9fa2c578bde15` |

- 시험: `05_tests/unit/test_chrono_bundle_grade_4368.py`(시험 127개, 옛 값(R3d `0220671` 판, rev24 전) 102; rev25 11개(PS-c 행정 항목 E-5 아래 기록, P3-6 한계 네 줄, P3-6 역할·한계 불일치 멈춤·P3-9 기록, READY 없음 P3-6 두 갈래는 CD-5 시험에 포함, CD-8 rev25 값, C-4 CD-7 빈 사유 멈춤, CD-11 `[case *]`·G6 펼침과 427.9 조건·기록 행 예외, 분류·조항 ID는 CD-11 목록 시험에 포함), 봉인 기대값 rev25; rev24 14개(CD-2 사건 행 줄·완전 일치, CD-3 창 끝 차 멈춤·창 결정 불가 사유, CD-5 READY 없음 표·재접촉 실패·등급 항목 0 행, CD-7 사유·빈 칸 멈춤, CD-11 항목 목록·빈 행 멈춤, CD-8 기록 값 결측·P3 값의 행 판정 입력, CD-9 C-4 기록 묶음·rigid_base P3-5·결측 값·행 수) 포함, C1 D8 합성 러너 항목 이름은 실제 전체 이름, 봉인 기대값 rev24; rev23 R23-1 이름 대응 19개(같은 안쪽 이름 세 행이 제 파일을 읽음, V0 꼴 행, 이름이 같은 행은 고치기 전 도구(`7cd7031`)와 출력이 같음(C-1·C-2, rev24 사유 키·새 블록 제외), `*` 행만 = 결측, 판정 행 이름·다른 이름·대소문자만 다른 러너 행 S-11, 다른·대소문자만 다른 `s8_metrics` 키 S-11, 안쪽 이름 키·`liftoff_s` 없음 = R19-5 계산 불가, 빈 `dir` S-11, 같은 `dir` S-11, 다른 행 바깥 폴더의 `meta.batch` = 입력 오류, 대응 기록 블록(C-5 9행, C-1·C-3), 적용하지 않은 대조 null) 포함, 합성 러너 행 `case`와 `s8_metrics` 키는 실제처럼 안쪽 이름; rev22 R22-1 짝짓기 11개(같은 안쪽 이름 세 행의 바른 짝, 행 수 불일치 S-15, 순서가 바뀐 `dir`, 안쪽 이름 불일치, 폴더 겹침, 대상 목록 불일치, 빈 `dir`, 대소문자만 다른 이름, 목록 파일 불일치, 기준 sha·근거 결측, 묶음 출력의 짝짓기 기록) 포함; 합성 입력: 행 수 불일치·빈 묶음·manifest 밖 행·결측 러너 출력·결측 judge 행·결측 E 항목·T4·T5 초과·VB 고유 실패·S-12·C-8 S-9 처리, 러너 행 분기 15개, 러너 미판정·미달 우선·빈 통과·셈 불일치 S-11, D8 재계산·t_lift 차(0.1 s 허용, 0.2 s 멈춤, 계산 불가, 구간 대체), 427.9 조건 2·3·4 거짓·창·결측·LEVEL 전 부상, C-3 토양 정지, C-5 짝 6쌍·manifest에만 있는 짝, 행 문구, 기록 행 상태, PS-c 기준 행·가지 끝 뒤 기록 포함), `test_resume4368_rev18.py`(fmin-time 3개).
- 시험 개수(8절 72·51, 이 절 127·102)는 `pytest --collect-only -q` 수집 수(parametrize 경우를 하나씩 셈)다. `def test_` 함수 수로는 8절 59·48, 이 절 101·79다.
