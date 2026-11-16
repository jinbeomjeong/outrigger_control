# 436.8 경로 1 새 판 판정기 (`*_4368.py`)

규칙: `v5_resume_4368_rules.md` 원판~rev25(`06_analysis/02_control/verif_matrix/`). R4 재판정의 읽기는 R4 공통 블록(sha256 `e451f067db9787c9a8a45b7fc2f3e711970a914b29bc089b37bd94414d259800`)이고, 아래 "R4 경로 1 하네스 도구" 절에 정리했다. rev5 R5-A1이 이 파일들을 하네스 묶음의 경로 1로 지정한다. 기존 판정기(`u3_judge_k1.py`, `judge_stage1_r5.py`, `u9_judge.py`, `las_t3_judge.py`·`las_h7.py`, `d1_runs.judgement`·`d1_select.py`)는 고치지 않았다. `u3_judge_k1.py`는 기록 전용 판이다(R5-A2).

## 공통 계약 (`judge4368_common.py`)

- 판정 전에 원판·rev1~rev25(26판, R4 RD-2)와 각 `.sha256`을 원시 바이트로 대조한다. 하나라도 다르면 S-1(종료 1)이다. 규칙 폴더는 `--rules-dir`(기본 `verif_matrix`). `resume4368_judge.py`도 같은 26판을 대조한다.
- rev9·rev10의 Chrono 항목(R9-1~R9-6 태그 확인·`law_locked` 형식·LS 행·J11 범위, R10-1·R10-2 LS 판별 입력 경계)은 Chrono 도구(`04_scripts/02_chrono/chrono_rows_judge_4368.py`, `v5_resume_4368_chrono_rows.py gs-check`)에만 적용되고, 이 하네스 판정기들에는 적용되지 않는다(여기서는 봉인 대조만 한다). rev11의 R11-1(줄 종류별 기대 스위치)·R11-2(T4h 찾기)·R11-3(H-6·H-7 명령 해시 기록)은 `resume4368_judge`(`record-check`·`gs`·`dg3-hash --h7`)에만 적용되고, 이 판정기들은 rev11 봉인 대조만 한다. rev12 R12-1(Q-R12-1 = A)부터는 이 판정기들의 J-P3 로드 판독(`h6_judge_4368`·`judge_stage1_4368`·`u9_judge_4368`)도 R11-2대로 찾는다(`judge4368_common.t4h_folders`·`locate_t4h`): 결과 파일의 러너 관례 폴더(`<stem>_t4h/`, 결과 옆 `t4h/`)에서만, 관례 폴더가 없을 때만 `--t4h-dir` 1개, 2개 이상이거나 관례 폴더가 있는데 주면 입력 오류(종료 2, S-11). `job.t4h_dir`는 찾지 않는다. 줄이 `t4h_file`을 기록했는데 0개·2개 이상 잡히면 S-2(③ 줄의 J-P3 멈춤, 구성 규칙으로 대신하지 않음)이고, `t4h_file` 키가 없는 줄만 R3-C8 구성 규칙이다. 출력 `inputs.t4h_folders_R12_1`, U-9는 `t4h_S2_R12_1`.
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
python -I -B 04_scripts/04_hydraulic/coupled/judge_stage1_4368.py --out <r.json> --h9 resume_k1/h9_stage1.jsonl --h10 resume_k1/h10_reuse_rerun.jsonl [--overlap-ref resume_k1/h10_overlap_t_a.json]
python -I -B 04_scripts/04_hydraulic/coupled/u9_judge_4368.py --out <r.json> --v0 resume_k1/h5_u9_v0.jsonl --h10 resume_k1/h10_reuse_rerun.jsonl [--stored-p3-hash v5/p3_hash.jsonl]
python -I -B 04_scripts/04_hydraulic/coupled/las_t3_judge_4368.py --out <r.json> --r0 <R-0> --r0k <R-0K> --t3 <T-3K> --baseline v5/d1.jsonl --identity <R-0.identity.json> --identity <R-0K...> --identity <T-3K...> --git-at-start <커밋> --import-check <resume4368_judge import-check 보고서>
python -I -B 04_scripts/04_hydraulic/coupled/h8_noise_judge_4368.py --out <r.json> --noise-vb resume_k1/h8_noise_VB.json --noise-v0 resume_k1/h8_noise_V0.json --h6 resume_k1/h6_dg3_v4on.json --seedext-vb resume_k1/h8_seedext_VB.json --seedext-v0 resume_k1/h8_seedext_V0.json --judge-dir <판정기 출력 폴더> --run-judge
python -I -B 04_scripts/04_hydraulic/coupled/h6_judge_4368.py --out <r.json> --h6 resume_k1/h6_dg3_v4on.json --l1-ref resume_k1/h8_noise_VB.json --judge <판정기 출력>/judge_h8_noise_VB.json
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
- J-P3 로드 판독은 줄의 T4h 파일(`t4h_file`, 결과 파일의 러너 관례 폴더, rev12 R12-1)의 `rod_pressure_Pa`로 본다. `t4h_file` 키가 없는 ③ 줄은 `판정 불가`다(하네스 main 줄에는 구성 근거 규칙이 없다). 기록한 파일이 0개·2개 이상 잡히면 S-2 멈춤이다(rev12 R12-1).
- `las_t3_judge_4368` K-0: 실제 sidecar(`d8x_record.run_identity`)에는 `git.head`·`git.is_clean`·`git.status_porcelain`·`threads`만 있다. `code_diff_sha256`·`c2_sha256`·`tools_sha256`·`OUTRIGGER_LOC_SHADOW`는 없으므로 G-S에서 대응을 정하기 전에는 그 행이 `판정 불가`다. 출력 헤더의 `identity`는 후보로만 보고한다.
- `u3_judge_4368` 이전 판 비교(V0 − v4)는 `u3_judge_k1`의 기록 방식 그대로이고 판정이 아니다.

## R4 경로 1 하네스 도구 (2026-11-16, 브랜치 `z4373-p1harness`, R3f `8a0c843`에서 가름)

- 지시문: `r4_handoff_path1.md`(sha256 `369fb3cd8ccf961ad4587d2710fb0bb9738b384bfd163418a5ad11cb0d1d167d`, 1,408줄). R4 공통 블록 sha256 `e451f067db9787c9a8a45b7fc2f3e711970a914b29bc089b37bd94414d259800`(표지 사이 LF 바이트, 경로 1이 다시 계산해 같음), 규칙 rev25 `c0b778fd3f53996a2caed37e373975afea591b3c798784843cb9e7eeaac6f233`.
- 고친 파일은 R4 허용 목록 (다)뿐이다(rev16:324). `h8_noise_judge_4368.py`는 고치지 않았다(H-8의 J-P3·J11 목록은 `resume4368_judge r4-lists`가 낸다).
- 공개(지시문 1.2 몫): 경로 1 구현자는 뽑은 글머리 P1-17(rev17 R17-2a [사실])의 H-12 첫 파일 관측값(강제 대체 FR 잠긴 표본 초과 1건)을 본 상태에서 `h12`를 만들었다.

### 바꾼 것

| 근거 | 파일 | 내용 |
|---|---|---|
| RD-2, R16-13, rev17~rev25 R4 글머리 | `judge4368_common.py`(`SEALED_RULES`), `resume4368_judge.py`(`SEALED_REVISIONS`) | 봉인 목록 = 원판 + rev1~rev25(26판). 두 목록이 같다(시험) |
| RD-8, RD-7 3 | `judge4368_common.assess_j_p3`·`j_p3_bound`·`breach_reads_problem` | J-P3 입력 = `hydraulics_record.extend_bound_check`(u3·u6 항목은 `v5.` 아래). `breach_reads`가 정수 ≥ 0 4개가 아니면 `판정 불가`(합 0 통과 없음). 같은 항목 최상위 `extend_bound_check`의 `breach_reads`가 다르면 `판정 불가` |
| R16-6, RD-10 | `judge4368_common.assess_j11`, `judge_stage1_4368.j11_items`, `h6_judge_4368.j11` | 실제 대체 다리(`fallback_legs`)의 `n_late_fallback_by_leg`. 멈춤 적용 설정 VB·LS1~LS4(item8·overlap VB 줄은 설정 VB). 멈춤 적용 줄의 블록 결측·값 결측은 `판정 불가`, 기록 설정 줄의 블록 결측은 "입력 없음" |
| R16-7 | `judge_stage1_4368.grid_grade`(`--grid`) | 격자 768 run마다 J-P3. 위반 = `멈춤 H-7` 표지 + RD-7 위반 목록(`미달` 아님), `판정 불가` run 수 |
| R16-3 | `resume4368_judge record-check` | ABL 줄(`controller` ABL ∧ 태그 `ABL_LAS_K1`)은 `require_soil_response` = False. 하나만 맞으면 판별 입력 결함(S-3, G-S S-11) |
| R16-4 | `resume4368_judge` R8-1 재계산 | `v5_setting` V0이고 `hydraulic_options`가 없으면(없음·null) ③ 끔 |
| RD-11 | `resume4368_judge jp-reuse` | 두 저장 J_P 배치 `batch.json` `cases`, 행 수 12 고정(인자 없음), 문자열 `C2Event(...)` 원소만, 기본 이름 비교, 그림자 줄 수 = 1. 입력 문제는 멈춤 표지(S-15, 사건 기록 판독 불가, 그림자 판독 불가)이고 재사용 값을 내지 않는다 |
| RD-7, RD-8, RD-9, RD-10 | `resume4368_judge r4-lists` | 모든 묶음의 R2 결과 파일에서 J-P3 위반(H-6·H-8·H-9 줄+격자·H-10), J11 멈춤(H-6·H-8·H-9·H-10 줄), 멈춤 S-6(H-1·H-3~H-10) 목록, RD-8 형식 수와 표지 `J-P3 입력 형식(RD-8)`(H-1·H-3·H-4), RD-9 ③ 켬 줄·run 수(0이면 S-8 표지), RD-10 수 |
| R16-8 | `resume4368_judge h11` | 8쌍 해시 같음, 키마다 양쪽 1줄, 실행 6건 정체성(R2·clean, 아니면 S-12). 거짓 짝 목록(RD-7 G-3 열) |
| R16-9 6, R17-2a | `resume4368_judge h12` | 공식 `t4h\` 파일만. 강제 대체 네 다리 범위와 실제 대체 다리 범위의 H-7 결론, 다르면 `R17-2a 범위 공백` 표지. 빈 창 막기, 파일 수 3(S-15) |
| R16-11, R16-11b | `resume4368_judge x16-records` | C-9~C-11 8행의 정체성(S-12·S-4)과 기록 항목, P-18 읽기 전제 |
| RD-13 | `resume4368_judge item-list` | 묶음별 항목 목록 파일(고정 바이트) |
| RD-5 | `resume4368_judge key-map` | 제외 키 대응표 초안 |
| RD-1 5, RD-1 4 | `resume4368_judge head-check` | HEAD = M4(아니면 S-12), `--r4`로 허용 목록 파일의 M4·R4 blob sha와 `b9f5707..M4 -- 03_src 02_params` 빈 diff(아니면 S-11) |
| RD-7 1 (G-5·G-6), R16-8 | `u3_judge_4368.py` | G-5·G-6 목록(RD-7 3 표기, `R4` 블록). `--g3`(`h11` 보고서)의 `pass`가 참이 아니면 등급을 내지 않고 멈춘다 |

### 경로 1이 고른 읽기 (공개, 판정서 한계 절)

1. J11은 "줄" 단위다(RD-7 1 J11 글머리, RD-10). H-9 격자 run에는 J-P3만 적용하고 J11은 적용하지 않는다.
2. RD-7 3 "같은 항목에 최상위 `extend_bound_check`"는 항목 바로 아래 키로 읽는다(r79 결과의 사본). u3·u6 항목의 `v5.extend_bound_check`는 대조하지 않는다.
3. H-8 줄의 J-P3: 태그로 ③ 판별, 로드 판독은 줄의 T4h(`t4h_file`) 또는 r79 구성 규칙(두 압력 판독 = 있음), 선언은 줄의 `head_only_declared`(없으면 거짓). H-6의 R8-2 `extend_start_rule` 확인은 H-6 판정기에만 둔다(H-8 r79 기록에는 그 키가 없다).
4. 격자 run: 태그 = `results[i].controller_tag`, 로드 판독 = 구성 규칙(r67·r69 축소 스크린 두 압력 판독, R3-C8 1), 선언 = run의 `head_only_declared`(없으면 거짓).
5. 멈춤 S-6 목록의 계열은 RV1-6 표(`--family-table`), 격자 run은 R2-7. 표가 나누지 못한 키는 `균일 연약`으로 적는다(RV1-6). `해당 없음`·`패치·처방 침하`·`강체`는 목록에 넣지 않는다.
6. RD-7 정렬의 묶음 순서는 번호 순(H-9 < H-10)이다.
7. H-12 실제 대체 다리 범위는 `t4h_replay`(강제 대체 재생)의 다리별 `over_0p6kN_by_leg` 가운데 `meta_json.fallback_start_s`가 있는 다리만 더한다(시각 제한 없음, R17-2a가 말한 두 범위의 글자 그대로). 빈 창 수는 실제 대체 다리마다 `t_s` ≥ `fallback_start_s`(7.6 허용)이고 `locked` = 1이며 작용 명령(앞 주기 `command_m_s`, `t4h_replay`와 같음)이 0인 표본 수다. 실제 대체 다리 하나라도 0이면 그 키는 판정하지 않고 묶음은 `기록 불완전`이다. `recorded_lower_max_abs_N`은 기록만 한다(관문 허용 1e-6 N, R17-1).
8. C-9~C-11 기록 항목의 원본 키: decisions = `controller_meta.slope_clearance_margin.order_gate.decisions`, 토양 모드 시작 = `c2_soil.soil_mode_t_s`, LOC = `c2_soil.t_loc_s`, 최대 행정 = `p3b.P3-5_clearance_stroke.s_motor_max_m`×10³, 끝 rut 틈 = `rut_clearance_end_m`×10³, P3-1~P3-9 = `p3b.checks`, 첫 READY = `phases`의 첫 `ready`, rc = `_runners/logs_<칸>/<id>_run.done`의 `exit=`, 마지막 표본 = `step_series.npz` `t_s` 끝. C-10 F < F_min 시간 = `fmin-time` 정의(RV1-7·R2-5), G6-1~G6-7 = 경로 1 Chrono 판정 도구의 G6 관문 코드(`chrono_rows_judge_4368.judge_scm`, 읽기만), 패치 다리 = `args.rigid_base`, 침하 = `p3b_ext.pad_sinkage`. C-11 LOC 주기 = 첫 LOC(`p3b.P3-2_loc.t_loc_first_s`)에서 끝나는 0.1 s 주기, 크롤러 법선 = `step_series.npz` `scm_crawler_normal_N`, LOC 취소 = `p3b.checks.loc_revokes`.
9. `u3_judge_4368`에 `--g3`를 주지 않으면 이전처럼 판정하고 "G-3 not passed" 발견을 남긴다(개발용). R4 판정에서는 `h11` 보고서를 준다.

### RD-5 키 대응표 초안 (`resume4368_judge key-map`)

| 키 | 만드는 곳 | 범주 |
|---|---|---|
| `script`, `script_sha256` | `judge4368_common.run_judge` | 도구 sha·공개 블록 |
| `rules_seal`, `rules_sha256`, `rules_rev*_sha256`, `rules_rev13_to_rev25_sha256` | `run_judge`, `resume4368_judge.main` | 봉인 블록 |
| `definition_changes`, `diff_vs_existing` | `run_judge` | 도구 판·규칙 설명 문자열 |
| `inputs.*`(경로·sha256·`t4h_folders_*`) | 각 판정기 `judge()` | 입력 파일 경로·sha256 블록 |
| `files[].sha256`, `family_table`, `replay`, `root`, `out_root`, `t4h_dir` | `resume4368_judge r4-lists`·`h12`·`x16-records` | 입력 파일 경로·sha256 블록 |
| `out`(요약 줄), `--out` 경로 원소 | `run_judge._finish`, `resume4368_judge.main` | 출력 위치 |
| `rules`, `section`, `rule`, `note`, `method`, `*_note`, `reason`, `problems`·`findings` 문장 | 모든 하위 명령 | 자유 문장 사유 키·규칙 설명 문자열 |
| `head`, `expected_head` | `resume4368_judge head-check` | 판정 도구 checkout 커밋 |
| `r4_block_sha256` | `resume4368_judge` R4 하위 명령 | 도구 판·규칙 설명 문자열 |
| `judge_run`(명령·종료 코드) | `h6_judge_4368`, `h8_noise_judge_4368` | 도구 판·실행 기록 |

### RD-13 항목 목록 (`resume4368_judge item-list`, 파일 `items_<묶음>.json`의 sha256)

| 묶음 | 항목 수 | sha256 |
|---|---|---|
| H-1 | 8 | `c5cc96c2a5f8e9b31e15ec516e0b5246be7e0ee26effcf99d301a0e506782ec4` |
| H-2 | 2 | `f8943efa4091a0faa761dad6617792f6ec293f00d470c07351cdbb458b1f2e8d` |
| H-3 | 13 | `333c5c1abbe7fc87e4dc36cd7212dfa7abdbc1643f72ba74aa153fc9431e1db0` |
| H-4 | 7 | `ec262189e8e51bcf766dce201b896a932b87d4a65d50be0edadfd7fb73491d6b` |
| H-5 | 2 | `4b00ce13fc5042c8a876844c4c404c52301984348b9956724c2109dbfc6d3c88` |
| H-6 | 7 | `9de457176079ec1d1dfff5be21b69341f87b1ec7d79224a270a7d16214c488dc` |
| H-7 | 3 | `eb2e4cd00c6bd0d4362e4b16ed1cd49567620a000598e5cba08ed3defb9ea968` |
| H-8 | 9 | `4719139ea66021e9d65eb011731d57c5d9a2d953261c6a6294cbd1a5125cc4a1` |
| H-9 | 9 | `9aa4b0844ca19bf79ea1e8f559ff370b19bd5815d6b94a1974bf7d4c537111bb` |
| H-10 | 11 | `ef156da77fadcf8f701709263bce4df24d62814858ea3771c4a7462f2c65cf2b` |
| H-11 | 3 | `13f6732a777e00f0f38fc3724951424e1ea4ab566b9359c25ff0df09162d11a8` |
| H-12 | 7 | `f8a9a72bf1c045e62486e33d090d20a845521faa5541febdcc268747aa1bcc30` |
| C-9 | 5 | `51aeddb2e17050e8c3ae95ad0fadcdd4bc66db2d52469fb2abf7bb54530dae23` |
| C-10 | 5 | `d249e8c3a93b5a314960a51cd039986e74fb2522a1fb00c221770fe6bca75d90` |
| C-11 | 3 | `f926f93732a71509b0b26bd2c505c300a073c05de03686b480814bd8a781cda6` |
| J_P | 6 | `aff3b5c0665a2465aa3749063fd37d7d5f1d398ad89a15055275336f542e3f58` |

### 판정 실행 명령 초안 (RD-1 5, 메인 checkout = M4, PowerShell)

`M4_FULL_HASH`, `R4_FULL_HASH`, `FAMILY_TABLE_JSON`, `H1_REGRADED_JSONL`은 메인 세션이 값으로 바꾼다. 출력은 `judge_<M4 짧은 해시>/harness_path1/`. 첫 단계가 종료 0이 아니면 아무 판정도 돌리지 않는다.

```powershell
$ErrorActionPreference = 'Stop'
$M4 = 'M4_FULL_HASH'; $R4 = 'R4_FULL_HASH'
$Root = 'C:\workspace\outrigger_control'; Set-Location $Root
$Py = 'C:\ProgramData\miniforge3\envs\python-dev\python.exe'
$Dyn = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$J = "$Root\06_analysis\02_control\verif_matrix\scripts\resume4368_judge.py"
$C = "$Root\04_scripts\04_hydraulic\coupled"
$RK = "$Root\06_analysis\03_hydraulic\coupled\v5\resume_k1"
$LK = "$Root\06_analysis\02_control\v5_rerun\las_k1"
$X = "$Root\07_results\S9\R4368X_b9f5707_20261115_013947"
$O = "$Root\06_analysis\02_control\verif_matrix\v5_resume_4368\judge_$($M4.Substring(0,7))\harness_path1"
New-Item -ItemType Directory -Force $O | Out-Null
# 1 RD-1 5 / RD-1 4: HEAD = M4 (S-12), M4 = R4 blobs of the two allow lists, no 03_src / 02_params diff (S-11)
& $Py -I -B $J head-check --expect $M4 --r4 $R4 --files <경로 1 (다) 목록> <경로 2 (라) 목록> --out "$O\head_check.json"
if ($LASTEXITCODE -ne 0) { throw 'head-check: S-12 / S-11 stop' }
# 2 RD-5 / RD-13 (before any judgement output)
& $Py -I -B $J key-map --out "$O\key_map.json"
& $Py -I -B $J item-list --out-dir "$O\items" --out "$O\item_list.json"
# 3 H-11 gate, C-9 .. C-11 records (before the H-3 / H-8 grades, RD-12), H-12, J_P
& $Py -I -B $J h11 --h11-dir "$X\H-11" --out "$O\h11.json"
& $Py -I -B $J x16-records --out-root $X --out "$O\x16_records.json"
& $Dyn -I -B "$C\t4h_replay.py" "$O\h12_t4h_replay.json" "$X\H-12\t4h" --check-recorded
& $Py -I -B $J h12 --h12-dir "$X\H-12" --replay "$O\h12_t4h_replay.json" --out "$O\h12.json"
& $Py -I -B $J jp-reuse --root $Root --out "$O\jp_reuse.json"
# 4 RD-7 lists, RD-8 / RD-9 / RD-10 counts
& $Py -I -B $J r4-lists --root $Root --family-table FAMILY_TABLE_JSON --out "$O\r4_lists.json"
# 5 bundle judges (H-1 .. H-10)
& $Py -I -B "$C\d1_judge_4368.py" --out "$O\h1_h2.json" --h1 "$RK\h1_d1.jsonl" --regraded H1_REGRADED_JSONL --select-out "$O\h2_select.json"
& $Py -I -B "$C\u3_judge_4368.py" --out "$O\h3_h4.json" --u3-dir $LK --v4-dir "$Root\06_analysis\02_control\s9" --h1-d1 "$RK\h1_d1.jsonl" --g3 "$O\h11.json"
& $Py -I -B "$C\u9_judge_4368.py" --out "$O\h5.json" --v0 "$RK\h5_u9_v0.jsonl" --h10 "$RK\h10_reuse_rerun.jsonl"
& $Py -I -B "$C\h8_noise_judge_4368.py" --out "$O\h8.json" --noise-vb "$RK\h8_noise_VB.json" --noise-v0 "$RK\h8_noise_V0.json" --h6 "$RK\h6_dg3_v4on.json" --seedext-vb "$RK\h8_seedext_VB.json" --seedext-v0 "$RK\h8_seedext_V0.json" --judge-dir "$O\r79_judge" --run-judge
& $Py -I -B "$C\h6_judge_4368.py" --out "$O\h6.json" --h6 "$RK\h6_dg3_v4on.json" --l1-ref "$RK\h8_noise_VB.json" --judge "$O\r79_judge\judge_h8_noise_VB.json"
& $Py -I -B "$C\judge_stage1_4368.py" --out "$O\h9_h10.json" --h9 "$RK\h9_stage1.jsonl" --h10 "$RK\h10_reuse_rerun.jsonl" --grid "$RK\h9_grid\grid_r67_main.json" "$RK\h9_grid\grid_r67_top.json" "$RK\h9_grid\grid_r69_bottom.json" "$RK\h9_grid\grid_r69_top.json" --overlap-ref "$RK\h10_overlap_t_a.json"
# 6 rev1 .. rev12 subcommands of the first judgement (record-check, k1-class, dg3-hash, anchor-map, family-f, ind-las, stroke-exposure ...): same arguments as the first path 1 run, new output folder
# 7 sha256 of every output file -> "$O\sha256_manifest.txt" (RD-6: before any comparison)
Get-ChildItem $O -Recurse -File | Get-FileHash -Algorithm SHA256 | ForEach-Object { "$($_.Hash.ToLower())  $($_.Path.Substring($O.Length + 1))" } | Set-Content -Encoding utf8NoBOM "$O\sha256_manifest.txt"
```

### sha256 (커밋 `301c932`의 blob, LF 바이트)

| 파일 | sha256 |
|---|---|
| `04_scripts/04_hydraulic/coupled/judge4368_common.py` | `a2a8af54fdb71eba83b2eea66927e50568e8edf3fbe97fa93d1886265301733b` |
| `04_scripts/04_hydraulic/coupled/judge_stage1_4368.py` | `422f9a0a066e98f573ff8a87a2905b6e42bf682a1437d15f9c988295f3a3e20c` |
| `04_scripts/04_hydraulic/coupled/h6_judge_4368.py` | `e9ae3ed9866dd8cc91ba8db275985544c1ab489bb297f9d672d3f8b7a224c31e` |
| `04_scripts/04_hydraulic/coupled/u3_judge_4368.py` | `b46cfa7cc80211905c1c83c9bce5e8b16c2d567e2cc267b08c68d3854766096e` |
| `04_scripts/04_hydraulic/coupled/h8_noise_judge_4368.py`(변경 없음) | `c037fe9ea8a10c1ba208a441ad2be1218d62841246db001e9d5ba9a54a3acf69` |
| `06_analysis/02_control/verif_matrix/scripts/resume4368_judge.py` | `0127512e479c073c21fa640df6ae91cf462c4b6aebffe13aae8804bfc412929a` |
| `05_tests/unit/test_judges_4368.py` | `d46ed1568225fc822588ee73c410b82068e9daed2ba7c793efef2168ea912703` |
| `05_tests/unit/test_judges_4368_h6_h8.py` | `ea81a4c6bc526ac8fec9b9b38516e58df89e37916a7f41dbea32cefd7e98b259` |
| `05_tests/unit/test_resume4368.py` | `b8851f7d80a8a185a577dd66f1a3a991511ce0fe60129bc64ee175fd37ac0498` |
| `05_tests/unit/test_resume4368_rev1.py` | `aaabe890a0317460cda85ead807e8e0d89936987776ba03dc9177c696b09c19e` |
| `05_tests/unit/test_resume4368_rev16.py`(새 파일) | `7e7cc4ea768f984577e82d12ef24920ca981e6a1178e735088b695dea04d9ba7` |

이 README 자신의 sha256은 이 표에 넣을 수 없다. R4 blob 표(RD-1 2)는 R4를 만든 뒤 메인 세션이 낸다.

### 읽은 것 (RD-6, 경로 1 R4 구현자)

1. 지시문 `r4_handoff_path1.md` 전부(머리, R4 공통 블록, 경로 1 몫, 뽑은 글머리 C-00~C-24, P1-01~P1-27). R4 공통 블록 sha256을 다시 계산했다.
2. 규칙 파일은 봉인 바이트 대조(sha256)만 했고, 지시문에 뽑힌 글머리 밖의 절은 열지 않았다.
3. 코드: 이 표의 경로 1 도구 전부와 그것이 import하는 모듈(`judge_stage1_r5.py`, `u3_judge_k1.py`, `v5_rerun.py` 일부, `lock_window_alignment.py`, `03_src/outrigger_sim/control/extend_start_bound.py`, `03_src/outrigger_sim/control/c2.py`의 결정 기록 형식, `t4h_replay.py`, `resume_k1_identity.py`·`run_v5._write_identity`, `resume_k1_family.py`의 키 형식, `r69_g5_screen.py` import 줄, `chrono_rows_judge_4368.py`의 G6 관문·행 읽기 함수).
4. `<OUT>` 준비물: `_tools/x16_identity.py`, `_tools/harness/h12_t4h_capture.py`, `_tools/rows.json`(키 구조), `_runners/steps_X1.json`, `_runners/logs_X1` 파일 이름과 `.done` 한 줄 형식.
5. R2 결과(`resume_k1/`, `v5_rerun/las_k1/`), `<OUT>/H-11`, `<OUT>/C-9`·`C-10` 한 행의 `result.json`: 키 경로·자료형·건수만 보는 스크립트로 구조를 확인했다(값은 출력하지 않음). 구조 확인 출력에는 일부 키의 자료형(null 여부)과 H-11 8키의 양쪽 건수(각 1)가 있었다. 판정 값은 보지 않았다.
6. 열지 않은 것: 경로 2 폴더 전부, `judge_b9f5707/`, `h0_judge*`, `gs_harness_*`, scratchpad의 `r4-p2`·`r4-handoff`·`r4-source`·`main`, `<OUT>/H-11/g3_pairs_check.json`.
