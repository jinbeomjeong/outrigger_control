# 436.8 경로 1 새 판 판정기 (`*_4368.py`)

규칙: `v5_resume_4368_rules.md` 원판~rev10(`06_analysis/02_control/verif_matrix/`). rev5 R5-A1이 이 파일들을 하네스 묶음의 경로 1로 지정한다. 기존 판정기(`u3_judge_k1.py`, `judge_stage1_r5.py`, `u9_judge.py`, `las_t3_judge.py`·`las_h7.py`, `d1_runs.judgement`·`d1_select.py`)는 고치지 않았다. `u3_judge_k1.py`는 기록 전용 판이다(R5-A2).

## 공통 계약 (`judge4368_common.py`)

- 판정 전에 원판·rev1~rev10과 각 `.sha256`을 원시 바이트로 대조한다. 하나라도 다르면 S-1(종료 1)이다. 규칙 폴더는 `--rules-dir`(기본 `verif_matrix`).
- rev9·rev10의 Chrono 항목(R9-1~R9-6 태그 확인·`law_locked` 형식·LS 행·J11 범위, R10-1·R10-2 LS 판별 입력 경계)은 Chrono 도구(`04_scripts/02_chrono/chrono_rows_judge_4368.py`, `v5_resume_4368_chrono_rows.py gs-check`)에만 적용되고, 이 하네스 판정기들에는 적용되지 않는다(여기서는 봉인 대조만 한다).
- 입력·출력 경로는 모두 인자다. 저장 결과 경로를 코드에 두지 않는다.
- 보고서(`--out`)에 다음을 넣는다: 스크립트 sha256, 봉인 대조, R5-A3 정의 차이 항목(`definition_changes`), `git diff --no-index --numstat <기존> <새 판>` 요약(`diff_vs_existing`).
- 종료 코드: 0 판정(발견 없음), 1 발견(멈춤·불일치·`판정 불가`), 2 입력 오류, 3 내부 오류. stdout 마지막 줄은 JSON 요약이다.
- 읽기만 한다. 시뮬레이션을 돌리지 않는다(`d1_judge_4368 --select-out`만 `d1_select.py`를 같은 인터프리터로 부른다).

## 판정기와 정의 차이 (R5-A3 번호)

| 새 판 | 묶음 | 기존 도구 | 정의 차이 | `git diff --no-index --numstat` (+/−, 2026-11-13) |
|---|---|---|---|---|
| `u3_judge_4368.py` | H-3·H-4 | `u3_judge_k1.py` | D-01~D-06 | +514 / −593 |
| `judge_stage1_4368.py` | H-9·H-10 | `v5/paper_runs/scripts/judge_stage1_r5.py` | D-07~D-17 | +692 / −430 |
| `u9_judge_4368.py` | H-5 | `v5/paper_runs/scripts/u9_judge.py` | D-18 | +275 / −180 |
| `las_t3_judge_4368.py` | H-0 | `las_t3_judge.py`, `las_h7.py` | D-20~D-22 | +301 / −848, +288 / −722 |
| `d1_judge_4368.py` | H-1·H-2 | `d1_runs.py`(`judgement`), `d1_select.py` | D-23~D-25(+ rev6 R6-C3) | (커밋 뒤 보고서 `diff_vs_existing`) |
| `h6_judge_4368.py` | H-6 | 없음 | D-19 | 기존 도구 없음(diff 대상 없음) |
| `h8_noise_judge_4368.py` | H-8 | `r79_L3L4_final.py`(`judge`), `r79_sensor_judge.py` | R5-A3 번호 없음(R3-E3·R4-B3·R5-C1~C3) | +569 / −398, +566 / −792(작업 중 값, 최종은 보고서) |

새 판은 기존 모듈을 import해 같은 값 계산(읽기·지표·관문)을 그대로 쓰고, 위 항목만 바꾼다. 그래서 numstat는 파일 전체 차이이고, 판정 정의의 차이는 `definition_changes` 목록이 원본이다.

## 실행 (python-dev, 프로젝트 루트)

```
python -I -B 04_scripts/04_hydraulic/coupled/d1_judge_4368.py --out <r.json> --h1 resume_k1/h1_d1.jsonl --regraded <h1_regraded.jsonl> --select-out <h2_select.json>
python -I -B 04_scripts/04_hydraulic/coupled/u3_judge_4368.py --out <r.json> --u3-dir <U-3 출력 폴더> --v4-dir 06_analysis/02_control/s9 --h1-d1 resume_k1/h1_d1.jsonl --g3 <g3.json> [--k1-report <u3_judge_k1 보고서>]
python -I -B 04_scripts/04_hydraulic/coupled/judge_stage1_4368.py --out <r.json> --h9 resume_k1/h9_stage1.jsonl --h10 resume_k1/h10_reuse_rerun.jsonl --t4h-dir <T4h 폴더> [--overlap-ref resume_k1/h10_overlap_t_a.json]
python -I -B 04_scripts/04_hydraulic/coupled/u9_judge_4368.py --out <r.json> --v0 resume_k1/h5_u9_v0.jsonl --h10 resume_k1/h10_reuse_rerun.jsonl --t4h-dir <T4h 폴더> [--stored-p3-hash v5/p3_hash.jsonl]
python -I -B 04_scripts/04_hydraulic/coupled/las_t3_judge_4368.py --out <r.json> --r0 <R-0> --r0k <R-0K> --t3 <T-3K> --baseline v5/d1.jsonl --identity <R-0.identity.json> --identity <R-0K...> --identity <T-3K...> --git-at-start <커밋> --import-check <resume4368_judge import-check 보고서>
python -I -B 04_scripts/04_hydraulic/coupled/h8_noise_judge_4368.py --out <r.json> --noise-vb resume_k1/h8_noise_VB.json --noise-v0 resume_k1/h8_noise_V0.json --h6 resume_k1/h6_dg3_v4on.json --seedext-vb resume_k1/h8_seedext_VB.json --seedext-v0 resume_k1/h8_seedext_V0.json --judge-dir <판정기 출력 폴더> --run-judge
python -I -B 04_scripts/04_hydraulic/coupled/h6_judge_4368.py --out <r.json> --h6 resume_k1/h6_dg3_v4on.json --l1-ref resume_k1/h8_noise_VB.json --judge <판정기 출력>/judge_h8_noise_VB.json --t4h-dir resume_k1/h6_dg3_v4on_t4h
```

## H-8 경로 1 집계 (`h8_noise_judge_4368.py`, R5-A1 표 H-8 행)

- 관문 값은 지정 판정기 `r79_sensor_judge.py`가 낸다. `--run-judge`이면 이 도구가 같은 인터프리터로 다음을 돌린다(명령은 보고서 `judge_runs`).
  - VB: `judge-merged <out> <h6> <h8_noise_VB> --s4-late-loc`. dg3 135키를 H-6 줄로 바꿔 판정한다(원판 5.1 H-8, rev1 RV1-3).
  - V0: `judge <out> <h8_noise_V0> --s4-late-loc`.
  - seedext: `judge <out> <h8_seedext_X> <h8_noise_X의 L1 줄만 뽑은 파일> --s4-late-loc`. L1 짝은 같은 설정 잡음 L1 줄이다(R5-C3).
- 줄 등급 재집계: S-4 실패의 원인이 LOC 관문뿐이고 419.8 기록(`base.late_loc_reapproach.is_flag`)이 FLAG면 `S4_late_loc` FLAG(13.2)다. 재접촉은 `strict_fail`만 센다(423.1·407.2). 원인 항목이 없는 S-4 실패는 실패로 두고 목록에 적는다(R5-C2).
- L2: S1 전방·패드 A 제외 n(기대 835), CP 두 근(`beta.ppf`, `binom.cdf` 근). 3 %를 넘으면 H-10이다.
- L1 게이트 네 개수: R4-B3 정의로 실행 기록에서 직접 센다. 판정기 출력의 같은 개수와 다르면 `판정 불가`(S-13)다. 판정기 출력에는 `settings_mismatch`가 없으므로 그 대조는 "대조 대상 없음"(R5-C1)이다.
  - errors 대조 기준: 판정기는 L2·L3의 오류 결과만 적는다. 그래서 대조는 "L2·L3 오류 결과 수"로 하고, 게이트 값은 R4-B3대로 meta `n_errors` + 오류 결과 수다(확인 필요 1).
- seedext: 키·설정별 k/25, CP 두 근, 실패 관문 분포, Fisher 단측 p, 개정 6 9절 문구. 시드 0~4 최상위 `commands_sha256`(F-6)이 잡음 줄과 다르면 H-15다. 기록이 없으면 "기록 불완전"이다.
- "VB 체계적 악화 의심(하네스)" 문구가 나오면 종료 1로 알린다(판정 보고 맨 앞 사용자 확인 항목, 멈춤 아님).

## H-6 등급 (`h6_judge_4368.py`, R4-B6, D-19)

1. 멈춤: J-P3(개정 9 3.2 표, ext_moving `breach_reads` ≥ 1 = H-7, 결함 행 = 설정 결함), J9(`m2_clipped_steps_post_lift` > 0 = H-9), 대체 다리 `n_late` > 0(H-7).
2. 같은 harness·`case_index`·`inner`의 L1 줄(H-8 VB 잡음)에 없던 FAULT 이름(`r79.warn_fault`, S-6 기준)은 `미달`이다.
3. 줄에 `판정 불가`가 있으면 묶음은 `판정 불가`다(원판 8.1 우선순위 판정 불가 > 미달 > 통과).
4. L3 134 실패 수는 기록이다. L2 1줄은 H-8 L2 집계에 들어간다(`h8_noise_judge_4368`이 대체해 센다).
- J-P3 로드 판독은 T4h `rod_pressure_Pa`로 보고, T4h가 없으면 구성 규칙(r79는 두 압력 판독 = 있음)으로 본다(R3-C8). 선언은 줄의 `head_only_declared`(r79는 거짓)다.
- rev8 R8-2: ③ 판별은 줄의 `controller_tag`(`v5_options.is_extend_start_tag`)로만 한다. 태그가 ③이 아닌 줄은 J-P3가 없고(`not_applicable`) 묶음 S-2다(H-6 줄은 ③ 줄). ③ 줄에 `controller_settings["two_pressure.extend_start_rule"]`이 없으면 J-P3 `판정 불가`, `tracked_bound`가 아니면 기존대로 S-2다.

## rev6 반영 (R6-C1~C3)

- F-9 `values.sa4.F_min_after_stop_N`(`verdict_runs.sa4_record`, 기록 전용): 정지 주기(`FAULT_LIFT_STROKE_LIMIT:soil`)부터 실행 끝까지 다리별 1 ms 참 F_cyl(`TRUE_FORCE`) 최소 [N]. 실행이 끝난 행만 읽으므로 명령 해시와 무관하다(시험). `judge_stage1_4368` SA-4 "정지 뒤 네 다리 ≥ F_min"은 F-9로 판정하고, F-9가 없을 때만 이륙 뒤 최소 ≥ F_min이면 참, 아니면 `판정 불가`다.
- `values.pressure.saturation_leg_chunks`의 정의(검증 항목 4 ② "레벨링 실행에서 포화 차단 0회"와 같은지): 신장 중(행 속도 U > `MOVING_SPEED_EPS_M_S`)이면서 참 압력 `TRUE_FORCE / A_p` ≥ 210 bar(릴리프)인 (행, 다리) 표본 수다. 포화 차단은 신장 중인 다리가 릴리프 압력에 닿아야 생기므로, 0이면 포화 차단 0회다. 같은 문장을 줄의 `values.pressure.saturation_rule`(`verdict_metrics.SATURATION_RULE`)에 기록하고, G-S(`resume4368_judge gs`)가 그 값을 대조한다(확인 필요 2).
- `d1_judge_4368`: G6-7 거짓일 때 `preloc_flag_ok` 참 → `P3-8_demoted`(377), 거짓 ∧ `G6-3_Fmin` 참 ∧ FAULT 없음(`final_phase`가 fault·fault_reground 아님) → `P3-8_preloc_loss`(U-S9-G6c). 둘 다 `demoted_items`에 들어간다. `preloc_flag_ok`가 없으면 `판정 불가`이고 `P3-8_unchecked`는 쓰지 않는다.
- `las_t3_judge_4368` K-0(안 b): `.identity.json` `start`·`end`의 `git.head`·`git.is_clean`(`status_porcelain`)·`threads` 다섯·`affinity_mask`·`rules_seals`(모두 `ok`). 제어기·도구 sha는 T-3K 출력의 줄·헤더 정체성(`las_t3_judge._header_problems`), `OUTRIGGER_LOC_SHADOW`는 `resume4368_judge import-check` 보고서(`--import-check`, RV1-9)로 본다. 원본이 없는 항목은 `판정 불가`다.

## 알려진 한계 (판정서에 적을 것)

- `judge_stage1_4368` SA-4 "정지 뒤 네 다리 ≥ F_min"은 F-9로 판정한다(rev6 R6-C1). F-9가 없는 줄만 이륙 뒤 최소(`values.forces.after_liftoff.min_kN`)가 F_min 이상이면 충분 조건으로 참, 미만이면 `판정 불가`다. "포화 차단 0"은 `values.pressure.saturation_leg_chunks` = 0이다(정의는 위 rev6 절, G-S 확인).
- J-P3 로드 판독은 줄의 T4h 파일(`t4h_file`, `--t4h-dir`)의 `rod_pressure_Pa`로 본다. T4h 파일이 없는 ③ 줄은 `판정 불가`다(하네스 main 줄에는 구성 근거 규칙이 없다).
- `las_t3_judge_4368` K-0: 실제 sidecar(`d8x_record.run_identity`)에는 `git.head`·`git.is_clean`·`git.status_porcelain`·`threads`만 있다. `code_diff_sha256`·`c2_sha256`·`tools_sha256`·`OUTRIGGER_LOC_SHADOW`는 없으므로 G-S에서 대응을 정하기 전에는 그 행이 `판정 불가`다. 출력 헤더의 `identity`는 후보로만 보고한다.
- `u3_judge_4368` 이전 판 비교(V0 − v4)는 `u3_judge_k1`의 기록 방식 그대로이고 판정이 아니다.
