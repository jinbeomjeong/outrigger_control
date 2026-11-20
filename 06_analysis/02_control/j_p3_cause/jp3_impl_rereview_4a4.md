# 436.9 J4a 보완 구현 3(`b06e409e`) 재검토 — 덧붙임 4a-4 7절 기준

작성: control-expert, 2026-11-21. 읽기·분석만 했고, 코드 수정·시뮬레이션·단위 시험 실행은 하지 않았다.
- 대상: worktree `C:\workspace\outrigger_control\.claude\worktrees\z4369-jp3`, `git diff 738a09f b06e409e`(8파일, +817/−144)
- 기준: 덧붙임 4a-4(sha256 `67380b10…`)
- 연 자료: 위 diff, `r79_L3L4_final.py:178-289`, `las_t3_dg3.py` 호출부, 근거 폴더 `j4a_remedy_b06e409e/`(SUMS `8235c5ce…`)의 선택·키 파일·prelaunch·`runner_accepts.py`
- 새 사례 재생·건식 확인·T-JR 출력은 없었고, 열지 않았다.

## 0. 판정 요약

| 구분 | 건수 | 요지 |
|---|---|---|
| 차단 | 0 | — |
| 정오 필요 | 1 | 4a-4 3절 키 입력 `--keys` → `--keys-file`(사용자 확인 권고, 질문 1) |
| 권고 | 2 | R-1 r79 출력 meta의 `keys_file` sha 대조, R-2(선택) 새 판정 파일과 436.8 저장 판정의 키별 등급 대조 |
| 이상 없음 | 7절 6항목 | 아래 1절 |

## 1. 4a-4 7절 항목별 적합

| # | 판정 | 근거 |
|---|---|---|
| D1-a | 적합 | `scan_r79_keys`: `--scan-root` 아래 모든 `.json`·`.jsonl`을 바이트 정규식으로 훑고 `cand=…#` 접두를 뗀다. `generated_key`: seed 토큰만 `s25`부터 올린다. 선택 출력에 스캔 파일 수 3,257, r79 키가 있는 파일 239, seed 최댓값 24, 파일별 sha·키 수가 있다. 생성 키 `L2|s25|g6|0|g6|G1+J1@FL|top|Fs0`(n 25)는 스캔에도 Dg-3에도 없다(`r79_key_in_scan`·`r79_key_in_dg3` false). 4a-4 1절의 작성 시점 확인(239파일, seed 최대 24)과 같다 |
| D1-b | 적합(R-1) | `key_taken`: 출력 `key`(접두 제거)가 생성 키와 같고 `seed_index`가 n과 같아야 한다. 아니면 판정 불가이고 사유는 "다시 묻기" |
| W1 | 적합(정오 필요) | `r79_environment`가 3절 환경 변수 다섯 개(VBJ는 `R79_ROD_MODEL=plant_truth` 포함)를 넣고, 실행기는 `las_t3_dg3.py`다. VBH 기대는 ① = 0이고 ② > 0. 키 입력만 `--keys-file`(2절) |
| W2 | 적합 | `_t_jr_10_preconditions`: VB 누락·오류 줄·해시 다름(64자 비교) → T-JR-10만 판정 불가(사유 "저장값 노후 확인 전"). T-JR-11은 별도 판정. 묶음 상태는 나쁜 쪽 |
| D2 | 적합 | `jp3_fixed_inputs.py`의 고정값 상수가 4a-4 5절 표와 같다(h10, `main.jsonl`, H-6, 잡음 VB, 기준선 SUMS, grid). 대조 위치: t8 `--stored`·`--main-jsonl`, `run_v5 --p3-hash-source`, t12 VBH `--base`와 `--base-judge-sha256`(필수, 없으면 판정 불가), select의 세 입력과 기준선, case-f·case-f-path의 grid |
| P-1 | 적합 | `base-judge` 하위 명령은 r79_sensor_judge에 H-6와 잡음 VB의 L1 참조 추출을 넘겨 판정 파일을 만들고 sha를 낸다. `t12-selfcheck`는 4a-4 6절 기대값 표를 그대로 검사한다(상태 pass, 짝 135, L2 1, 빈 목록 4개, 둘 다 없음 7, X→X만). prelaunch `jp3_prelaunch_h6_selfcheck.json`에 두 단계 명령과 기대값이 있다 |

## 2. 정오 필요: r79 키 입력 옵션

- 실행기 `r79_L3L4_final.cmd_run`의 두 옵션(`r79_L3L4_final.py:224-243`)
  - `--keys`: 기본 seed 잡 목록(`plain_jobs`)에 있는 키만 받는다. s25 키는 "keys not in the job list"로 거부된다.
  - `--keys-file`: `keys_file_problems`(`:198-216`) 조건이면 받는다. 후보가 `current`이고, 표 규칙 사례이며, seed ≥ 0이어야 한다. 436.8 seedext 경로다.
- 두 옵션은 키 목록의 출처만 다르다. 실행 함수 `run_one`, Pool, `R79_*` 환경 변수, preset 검사(`settings_mismatch`)는 같다(`:244-284`).
- `las_t3_dg3.py`는 `final.main()`으로 이 parser를 그대로 쓴다(`:86`, `:134`).
- 출력 meta에 `seeds: "keys file"`와 `keys_file {path, n_keys, sha256}`이 남는다(`:285-287`).
- 판단: 사용자 결정 "실행기가 새 seed를 못 받으면 멈추고 다시 묻는다"의 멈춤 조건에는 해당하지 않는다. 같은 실행기가 문서화된 옵션으로 받기 때문이다. 다만 4a-4 3절 명령 꼴이 `--keys`이므로 정오가 필요하다. 결정 문구에 걸치는 해석이라 사용자 확인을 한 번 권한다(질문 1).

## 3. 권고

| # | 내용 |
|---|---|
| R-1 | `dryrun_selection.json`의 명령과 `r79_keys_file.path`는 scratchpad 원위치를 가리킨다. 실행에는 저장소 사본 `j4a_remedy_b06e409e/dryrun_selection_r79_key.txt`(sha256 `1a79e02f…`, 선택 기록 sha와 같음)를 쓴다. `summarize`가 r79 출력 meta의 `keys_file.sha256` = 선택 기록 sha이고 `n_keys` = 1인지 확인하게 한다. 다르면 판정 불가 |
| R-2 | (선택) 저장 436.8 H-6의 경로 1 r79 판정 결과가 있으면, `base-judge`로 만든 판정 파일의 키별 등급과 대조해 기록한다. 저장 자료끼리의 비교라 결과 전이다. 다르면 원인을 본 뒤 T-JR-12로 간다(판정 조건 아님) |

## 4. 확인 필요 질문(사용자)

1. r79 건식 확인 키(s25)를 같은 실행기의 `--keys-file` 옵션(436.8 seedext 경로)으로 넣고, 4a-4 3절 명령 꼴의 `--keys`를 정오로 바꿔 진행할까요? 권고는 "예"입니다(실행기·환경 변수·실행 함수 동일). 아니면 다른 방법을 설계할 때까지 건식 확인을 멈춥니다.

## 5. 정오 문안(질문 1에 "예"일 때, `jp3_remedy_spec_addendum_4a4_erratum1.md`)

(별도 파일로 저장한다.)

## 6. 사례 재생 전 남은 일(재검토 4a3 7절에서 갱신)

1. 질문 1 답 → 정오 저장·sha → python-expert R-1(그리고 선택한 경우 R-2) → 단위 시험 → control 확인.
2. 입력 고정(K-10, 메인)
   - 4a-3 5.4절·4a-4 1·5절 표의 파일
   - 키 파일 사본
   - 근거 폴더 `j4a_remedy_3b949f5/`·`j4a_remedy_738a09f/`·`j4a_remedy_b06e409e/`(SUMS `8235c5ce…`)
   - 덧붙임 4a-2~4a-4와 정오
   - 실행용 worktree 커밋에 `git worktree lock`
3. P-1(메인이 띄움): `base-judge` → 판정 파일 sha 기록 → `t12-selfcheck` 종료 0.
4. 5.1 건식 확인(메인이 띄움): 실행 다섯 개 → `summarize` 종료 0.
5. 5.2 F-A 경로 동등성(메인이 띄움): `j9_case_f_path` → `case-f-path` 종료 0.
6. verif-protocol-auditor 실행 전 감사.
7. 사용자 재승인 뒤 사례 재생과 T-JR 실행(배치표는 compute-scheduler-expert).

## 7. 핸드오프

- 위임 필요(python-expert): R-1, (선택) R-2.
- 위임 필요(verif-protocol-auditor): 6절 6.
