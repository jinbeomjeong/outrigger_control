# chrono_rows_judge_4368 — 436.8 Chrono 경로 1 집계 새 판

- 근거: 규칙 rev5 R5-A1(경로 1 새 판, 요건 1~5), rev6 R6-A(D-26~D-39)·R6-B(C-1~C-9 정의)·R6-C3(377 분기)·R6-1(시각 원점).
- 대조표: `06_analysis/02_control/verif_matrix/v5_resume_4368/chrono_path1_rev3_alignment.md`(추적 밖, cad-expert 2026-11-13). 이 도구의 N-1~N-14 = rev6 D-26~D-39다.
- 고치지 않은 것: 러너(`run_S9.py`, `run_S8C.py`, `run_S6C.py`)와 기존 판정 함수(`r76_g6_chrono_judge.py`, `verify/s8_control.py`, `verify/s6_control.py`).
- 작성: cad-expert, 2026-11-13. 실행 환경: Chrono-dev `python -I -X utf8`(pychrono는 import하지 않는다. numpy·PyYAML만 쓴다).

## 1. 실행

```
python -I -X utf8 04_scripts/02_chrono/chrono_rows_judge_4368.py judge --out <out.json> \
    --batch <07_results/S9/batch_V5-RESUME-K1-C3_<stamp>> [--batch ...] [--row <행 폴더> ...] \
    [--results-root <07_results>] [--rules-dir <verif_matrix>] [--params <02_params/rexome33.yaml>]
python -I -X utf8 04_scripts/02_chrono/chrono_rows_judge_4368.py disclose [--out f.json]
python -I -X utf8 04_scripts/02_chrono/chrono_rows_judge_4368.py seals [--rules-dir <verif_matrix>]
```

- `--batch`: `s9_batch` 배치 폴더(`batch.json`). SCM 행은 `<batch>/<case>/`에서 찾는다. 행 번호(`S-03` 등)는 `batch.json`의 `d1_id`에서 읽는다.
- L2b·L1-R 행 폴더(v2, 2026-11-13. v1은 배치 시각과 같은 이름만 찾아 1 s 늦게 생긴 L1-R 폴더 `_082118`을 놓쳤다):
  1. 행 로그 `<batch>/<case>.log`의 마지막 `batch wall ... -> <폴더>` 줄을 읽는다(`s9_batch.s8c_case_check`, gs-check와 같은 규칙). 행 = `<폴더>/<--only>`. 그 폴더에 `result.json`이 없으면 같은 경로를 `--results-root` 아래(`.../07_results/<나머지>` → `<results-root>/<나머지>`)에서 한 번 더 찾는다(지운 worktree에서 돈 뒤 결과를 옮긴 경우). 그래도 없으면 종료 2.
  2. 로그에 그 줄이 없으면 `--tag`가 같은 러너 폴더(`S8/<tag>_*`, `S6/*_<tag>_*`) 가운데 이름 시각이 그 행의 `progress.log` START~END(없으면 배치 시각 ~ + `wall_s`) ± 2 s 안인 것을 쓴다. 정확히 하나일 때만 쓰고, 없거나 둘 이상이면 종료 2.
  - 행마다 찾은 방법을 `rows[].row_dir`(`source` = `batch_folder` / `case_log` / `case_log_relocated` / `time_window`)에 적는다.
- 열린 루프 행(C-6·C-7, `run_S9.py machine`, `series.npz` + `result.json` `p3a`)은 이 도구의 판정 대상이 아니다(원판 9.1: C-6·C-7 경로 1 = `result.json` `p3a`, 경로 2 = `openloop_compare.py` `analyse`. 원판 7.5·8.1: 기록 행. rev5 R5-A1: Chrono 경로 1 새 판 = C-1~C-5). 읽지 않고 `skipped_rows`(입력 sha256, 근거 규칙)에 적는다. 종료 코드에 영향 없음.
- `--row`: 행 폴더를 직접 준다(배치 정보 없이). C-3 두 행은 이름으로 알아본다.
- `--assume C-n=값`: 민감도 확인용이다. 출력에 `deviates_from_rev6`가 붙고, 그 출력은 경로 1 결과로 쓰지 않는다.
- 엔진 구분: `step_series.npz`가 있으면 SCM(run_S9), `pads.npz`에 `crawler_normal_N`이 있으면 L2b, 없으면 L1-R, `series.npz`와 `p3a`가 있으면 열린 루프(건너뜀)다. `batch.json` `criteria_id`가 C-6·C-7·C-7a·C-7b여도 건너뛴다.
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
| D-29 | N-4 | `d8_lift_time` | L2b t_lift = 단계 ∉ {idle, check, touch} ∧ `pads.npz` `crawler_normal_N` ≤ 0인 첫 1 ms 표본. 단계는 `phases` + `settings.start_t_s`(R6-1) |
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

원판·rev1~rev11의 md sha256을 도구 안 상수 `RULES_SEALS`와 각 `.sha256` 첫 토큰에 모두 대조한다. 하나라도 다르면 종료 1, 파일이 없으면 종료 2다. rev6 sha256 = `809e5639…`, rev7 = `e81f7d31…`, rev8 = `3ecafaaf…`, rev9 = `4cf7843c…`, rev10 = `62a0bd8d…`, rev11 = `9bac4524…`. rev11 R11-5: `judge` 출력(문서와 마지막 줄 요약)에 `grade_counts_R11_5`(등급별 행 수, 기록 전용)를 더했다. G-S에서는 행 등급을 판정하지 않으며 멈춤 사유가 아니다. `--out`은 필수다(R11-6).

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
  - G-S의 키 있음·형식 확인(S-11)은 `v5_resume_4368_chrono_rows.py gs-check`가 한다: level 행 `series_keys_missing`·`series_key_problems`·`law_locked_minus_one`, L2b 행 `pads_law_locked_missing`·`pads_law_locked_problems`, 닫힌 루프 행 `expect_controller_ok`(R9-1), 모든 행(열린 루프 포함) `batch.json` `code_at_launch.git.head`가 40자리 커밋인지(`code_at_launch_head_ok`, rev11 R11-4; 열린 루프 행은 `result.json` `code_state.git_at_start.head`도 있어야 함). `git_at_start`와의 대조(S-12)는 gs-check가 하지 않는다(판정서 값이 필요하므로 경로 1 판정 몫).
- **LS 판별 입력 경계(rev10 R10-1, `batch_full_name`·`ls_setting`)**: 묶음은 전체 묶음 이름(`V5-RESUME-K1-` 접두어 포함)이다. S9 배치 `batch.json` 최상위 `batch` 값을 폴더 이름의 `batch_`~`_<YYYYmmdd_HHMMSS>` 부분과 대조해 쓰고, 키가 없으면 폴더 이름 부분을 쓴다. 다르거나 정할 수 없거나 manifest `batches` 키가 아니면 묶음 이름 불명이다. 묶음 이름 불명, manifest 같은 `case` 행 0개·여럿, `batch.json` `cases[]` 같은 `case` 0개·여럿은 LS 판별 불가(`ls_setting.boundary_case`)이고, 두 출처 모두 행이 하나씩 있고 둘 다 `v5_setting`이 없거나 None일 때만 LS 아님이다. manifest 파일이 없거나 JSON이 아니거나 `batches`가 없으면 입력 오류(종료 2, 묶음 판정 안 함, S-11). G-S 확인(R10-2, `ls_source_check`)은 gs-check가 행마다 하며 어긋난 행은 실패다(`--rows-manifest`, 기본 저장 manifest; 출력 `ls_sources_R10_2`). `rev8_counts`의 `R10-1b_cases`에 경우별 행 수를 적는다.
- 묶음 요약 `rev8_counts`: J-P3 상태별 수(해당 없음 = `not_applicable`), S-2 행 수, J11 상태별 수, 판정 불가 C-5 행 수, rev9 R9-8 G-S 기록 항목(`R9-1_expect_failed`, `R9-2_form_problems_by_item`, `R9-2_key_missing`, `R9-3_minus_one`, `R9-4_ls_rows`·`R9-4_undecided`, `R9-6_no_input`). 마지막 줄 JSON에도 있다.
- 2026-11-13 G-S `…_082117`(기록 추가 전)에 돌리면 C-5 SCM 행 셋이 J11 멈춤이다(R8-4가 예상한 결과). `7527fc3` 기록 행(3.6 s VB)은 J-P3 `pass`, J11 대체 다리 없음(`no_fallback_leg`)이다.

## 8. 시험

`05_tests/unit/test_chrono_rows_judge_4368.py`: 시험 32개 = 합성 입력 30개(v2 행 폴더 찾기 7개·열린 루프 건너뜀 1개 포함)와 G-S 실행 경로 2개(`07_results/S9/batch_V5-RESUME-K1-GS_20261113_020211`, `..._082117`. 판정 아님, 없으면 건너뜀). 082117은 rev8부터 종료 1(C-5 SCM 행 셋의 J11 멈춤, 기록 추가 전 배치), L1-R 폴더 `_082118`을 행 로그에서 찾음, C-6 행 건너뜀을 확인한다. rev8·rev9 항목은 `test_resume4368_rev8.py`·`test_resume4368_rev9.py`, gs-check의 rev9 항목은 `test_v5_resume_4368_chrono_rows.py`.
