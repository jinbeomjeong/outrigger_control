# 436.9 J4a 보완 구현 2(`738a09f`) 재검토 — 덧붙임 4a-3 6절 K-1~K-9 기준

작성: control-expert, 2026-11-20. 읽기·분석만 했고, 코드 수정·시뮬레이션·단위 시험 실행은 하지 않았다.
- 대상: worktree `C:\workspace\outrigger_control\.claude\worktrees\z4369-jp3`, `git diff 3b949f5 738a09f`(11파일, +1404/−125)
- 기준: 덧붙임 4a-3(sha `f001383a…`)
- 연 자료:
  - `jp3_t8_rules.py`, `jp3_tjr_judge.py`(t8·t12), `jp3_dryrun_evidence.py`, `jp3_case_judge.py` case-f-path, `run_v5.py` 배치 부분
  - 근거 폴더 `j4a_remedy_738a09f/`의 `dryrun_selection.json`, `record_table_1_2.md`, `record_keys.json`, `SHA256SUMS`
  - 저장 파일의 키·seed 토큰: h8 잡음 파일, h10의 `event_names` 꼴
- 새 사례 재생·T-JR 출력은 없었고, 열지 않았다.

## 0. 판정 요약

| 구분 | 건수 | 요지 |
|---|---|---|
| 차단(실행 전) | 2 | D1 건식 확인 r79 키가 436.9 판정 집합 안(4a-3 5.1절 합집합 정의 누락, 작성자 오류). D2 t8·t12 입력 sha 미대조(5.4절) |
| 권고 | 2 | W1 건식 확인 r79 명령을 T-JR-12 실행기·환경 변수와 맞춤. W2 VB 재실행 차이를 판정 불가로(확인 필요 (1)) |
| 이상 없음 | K-1~K-9 대부분 | 아래 1절 |

## 1. K 항목별 적합

| # | 판정 | 비고 |
|---|---|---|
| K-1 | 적합(D2) | `jp3_t8_rules.py`의 상수가 4a-3 3.2절 표와 같다: ③ 키 2, 문구 경로 1, per-lock 9, 증거 2. `record_differences`는 per-lock·증거 키를 "저장에 없고 새 줄에 있을 때만" 뺀다. A는 `event_names`(사전, 키를 순회)와 `events`에서 본다. B는 64자 해시와 사건이 같은지 본다. C는 기록이다. 저장 줄의 태그(`final_C4G2_P3_LAS_K1`)와 T4h ③ revision 4가 아니면 판정 불가다. 22잡은 `p3_hash_jobs(--main-jsonl)`로 정한다 |
| K-2 | 적합 | `ready_time_s`가 `r79_sensor_judge._ready_time`을 쓴다. 4.2절 네 경우를 구현했다(`_ready_cases`). 저장 H-6 자기 대조는 판정 불가 0, 실패 0, 둘 다 READY 없음 7(보고) |
| K-3 | 적합 | `_l2_pass_to_fail`은 L2만 보고, pass·flag → fail이 실패다. 전 등급 전이는 `grade_transitions_record`. `h8.grade_lines`가 `level`을 넘겨준다(`h8_noise_judge_4368.py:258-263`) |
| K-4 | 적합 | VBJ 묶음의 기준 줄에도 증거 검사를 건다(`_check_lines`). VBH의 기준(저장 H-6)에는 증거 키가 없어 건너뛴다(4.4절과 같다) |
| K-5 | 부분(W2) | `j9_t8` 88행, `--p3-hash-source`. VB 차이는 `stop_before_reading_T-JR-10` 표지만 내고 상태는 그대로 둔다 |
| K-6 | 부분(D1·W1) | 선정·실행·요약 구조와 "증거 2키와 오류 여부만 읽음"은 맞다(`evidence_of`). 이벤트 잡 R14 eps 0 offset 0.025 s는 run_v5 판정 배치 합집합 밖이고, 저장 `main.jsonl`·h10·h1·h9_stage1에도 없음을 grep으로 확인했다. r79 키는 D1 |
| K-7 | 적합 | `record_keys.json`: VBG4·VBG5 플랜트 기록에 증거 2키가 있다(값 0, 실행 없음) |
| K-8 | 적합 | case-f-path는 offset 0.075 s 행을 거부하고, 세 run의 저장 해시 앞 12자, `breach_reads`, `min_gap_*` ≤ 10⁻⁹를 본다. grid sha `7160f9f1…`가 아니면 거부한다 |
| K-9 | 적합 | `record_table_1_2.md`의 37개 항목이 모두 일치한다. 출처 키 경로가 명시돼 있다 |

## 2. 차단

### D1. 건식 확인 r79 키가 436.9 판정 집합 안이다
- `select`는 `--noise h8_noise_VB.json`에서 Dg-3 135키가 아닌 첫 L2 키를 고른다(`jp3_dryrun_evidence.py:115-117`). 선택된 키는 `L2|s0|g6|0|g6|G1+J1@FL|top|Fs0`이다.
- 이 키는 저장 `h8_noise_VB.json`(1회)과 `h8_noise_V0.json`에 있다. 명세 7절의 436.9 재실행 범위는 "VB·LS 줄 전부를 VBJ·LSJ로"이므로, 이 키의 VBJ 실행은 436.9 판정 행(이상·normal 등급 행, 6.1절)이 된다.
- 원인: 4a-3 5.1절 합집합(run_v5 배치 4개, Dg-3 135키, 기준선)에 r79 잡음 계열을 넣지 않은 문안 작성자 오류다. 도구는 문안대로 구현했다.
- 저장 잡음 파일의 L2 seed 사용 범위:

| 파일 | L2 seed 범위 |
|---|---|
| `h8_noise_VB`·`h8_noise_V0` | s0~s4 |
| `h8_seedext_VB` | s0~s24 |

- 권고: 합집합에 436.9 본 실행이 다시 돌릴 저장 r79 잡음 계열 키 전부를 더한다(질문 1). 키는 어느 저장 파일에도 없는 seed 번호(예: s25 이상)로 만들고, 선정 출력에 "모든 저장 잡음·Dg-3·family 키 집합 밖"을 보인다. 실행기가 그 seed를 받지 못하면 멈추고 다시 묻는다.

### D2. t8·t12가 입력 sha를 대조하지 않는다
- 4a-3 5.4절은 "판정 도구가 입력 sha를 대조한다"이다.
- 지금 대조하는 것은 `jp3_case_judge.py`의 `GRID_SHA256`뿐이다. t8(h10 `ce526b1f…`, `main.jsonl` `9ad74990…`)과 t12(H-6 `ea0ab94c…`, 기준 판정 파일)는 sha를 기록만 한다.
- 수정: 고정값을 상수로 두고, 다르면 판정 불가로 처리한다. `run_v5 j9_t8`의 `--p3-hash-source`에도 같은 대조를 건다.

## 3. 권고

| # | 내용 |
|---|---|
| W1 | 건식 확인의 r79 명령(`r79_L3L4_final.py`, `R72_PATH=per_leg`, LAS_T3_DG3 환경 변수 없음)을 T-JR-12 실행 명령(`las_t3_dg3.py`, `LAS_T3_DG3_LAS/K1/P3=on`, `R79_T4H_DIR`, VBJ에는 `R79_ROD_MODEL=plant_truth`)과 같은 실행기·환경 변수로 맞춘다. r79 VBH 실행에서도 ② > 0을 기록한다(지금 기대는 ① = 0뿐) |
| W2 | 확인 필요 (1): VB 재실행 차이나 VB 줄 누락이 있으면 T-JR-10을 판정 불가로 낸다(5절) |

## 4. 이상 없음(근거)

- 03_src와 `harness_hydraulics.py`는 바뀌지 않았다. 다이제스트(모니터 552c768a…, 플랜트 7404b793…)가 `3b949f5`와 같다는 보고와 맞는다(diff stat에 두 경로가 없다).
- 저장 h10에는 `WARN_ROD_PRESSURE_FALLBACK`이 0건이다(파일 grep 0). 조건 A의 저장 쪽은 성립할 것으로 보인다.
- 단위 시험(보고): worktree 7,479 통과, 실패 2(기존·데이터), skip 132, xfail 0. 4a-2·4a-3 시험 65 통과.

## 5. 확인 필요 2건(python-expert) 권고

| # | 권고 | 근거 |
|---|---|---|
| 1 | VB 재실행이 저장 h10과 다르거나 줄이 없으면 **T-JR-10을 판정 불가(종료 2)**로 낸다. T-JR-11은 그대로 판정한다 | 4a-3 5.3절 "저장값 노후 여부부터 본다(멈춤)". K-5의 "기록으로만"은 VB를 판정 짝으로 쓰지 않는다는 뜻이다. T8상 VBH = 현재 VB이므로, VB가 저장값과 다르면 T-JR-10의 통과·실패가 T8 판정으로서 의미가 없다 |
| 2 | 스텁 자기 대조만으로는 부족하다. 4.4절의 기준 판정 파일을 만든 직후, 실제 파일로 저장 H-6 자기 대조를 실행 전 절차로 한 번 돌린다 | 기대: 판정 불가 0, 실패 0, L2 통과→실패 0, 전이 표 X→X만, 둘 다 READY 없음 7, 짝 135, L2 1. 실제 `grade_lines`의 키 대응(`cand=current#` 접두)과 관문 누락은 스텁이 볼 수 없다. 저장 자료만 써서 결과 전이다 |

## 6. 확인 필요 질문(사용자)

1. 4a-3 5.1절 건식 확인 합집합에 436.9 본 실행이 다시 돌릴 저장 r79 잡음 계열 키 전부를 더하고, 어느 저장 파일에도 없는 seed 번호(예: s25 이상)로 r79 키를 만들까요? 권고는 그렇게 하는 것입니다(결과 전 정정, 덧붙임 4a-4 또는 4a-3 정오 한 줄).

## 7. 사례 재생 전 남은 일

1. python-expert 수정: D1(선정 규칙, 질문 1 답 뒤), D2, W1, W2. 그 뒤 단위 시험과 control 재검토.
2. 입력 고정(K-10, 메인):
   - 4a-3 5.4절 표의 파일: h10과 T4h, `main.jsonl`, H-6과 T4h, grid
   - 덧붙임 4a-2·4a-3
   - 근거 폴더 `j4a_remedy_3b949f5/`·`j4a_remedy_738a09f/`(SUMS `82b6a851…`)
   - 건식 확인에 쓰는 잡음 파일과 기준 판정 파일
   - 실행용 worktree 커밋에 `git worktree lock`
3. H-6 기준 판정 파일 생성(4.4절)과 실제 판정 파일 자기 대조(5절 2).
4. 5.1 건식 확인(메인이 띄움): 고친 `select` → 실행 다섯 개(이벤트 세 개, T-JR-12와 같은 실행기의 r79 두 개) → `summarize` 종료 0. 출력은 `dryrun_evidence/`에 두고 판정에 쓰지 않는다.
5. 5.2 F-A 경로 동등성(메인이 띄움): `run_v5.py j9_case_f_path` 3행 → `jp3_case_judge.py case-f-path --grid <grid_r67_top.json>` 종료 0. 아니면 사례 F를 돌리지 않는다.
6. verif-protocol-auditor 실행 전 감사: `seal_check.py --sums --rev --check-tracked`, `baseline_check.py sums`·`identity`, `ref_check.py`, `placeholder_scan.py`, `ps1_lint.py`, `junit_skips.py`.
7. 사용자 재승인 뒤 다음 순서로 실행한다(배치표는 compute-scheduler-expert).
   - 사례 재생 A~E → `jp3_baseline_compare.py`
   - X11 → `x11`
   - 사례 F → `case-f`
   - `j9_t8` 88행 → `t8`
   - T-JR-12 VBH·VBJ·VBJ0 → `t12` 두 묶음
   - `records`

## 8. 수행한 작업

- `git diff --stat 3b949f5 738a09f`를 보고, 위 도구 파일들을 읽었다.
- 근거 폴더 `j4a_remedy_738a09f/`를 확인했다.
- grep으로 확인한 것:
  - 저장 잡음 파일의 seed 토큰(`h8_noise_VB`·`V0`, `h8_seedext_VB`, `h9_family_F_VB`)
  - 선택 키가 저장 잡음 파일에 있는지
  - 이벤트 잡이 저장 main·h10·h1·h9_stage1에 없는지
  - h10의 `event_names` 꼴과 대체 경고 수
- scratchpad는 쓰지 않았다.

## 9. 핸드오프

- 위임 필요(python-expert): D1·D2·W1·W2.
- 위임 필요(verif-protocol-auditor): 7절 6.
- 위임 필요(control-expert): 질문 1에 답이 오면 4a-4(또는 정오) 문안.

## 10. 사용자 결정(2026-11-21, 메인 세션 덧붙임)

- 질문 1: 권고안대로 한다. 4a-3 5.1절 합집합에 436.9 본 실행이 다시 돌릴 저장 r79 잡음 계열 키를 모두 더하고, 어느 저장 파일에도 없는 seed 번호(s25 이상)로 r79 건식 확인 키를 만든다. 짧은 덧붙임 4a-4로 남긴다. 실행기가 새 seed를 받지 못하면 멈추고 다시 묻는다.
- python 확인 필요 (1)·(2)는 5절 권고대로 처리한다(VB 재실행 차이·누락 = T-JR-10 판정 불가, 실제 기준 판정 파일로 H-6 자기 대조를 실행 전 절차로 추가).
