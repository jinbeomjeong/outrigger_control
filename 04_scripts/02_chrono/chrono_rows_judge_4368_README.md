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

- `--batch`: `s9_batch` 배치 폴더(`batch.json`). SCM 행은 `<batch>/<case>/`에서 찾는다. L2b·L1-R 행은 argv의 `--tag`·`--only`와 배치 시각으로 `<results-root>/S8/<tag>_<stamp>/<only>`, `<results-root>/S6/*_<tag>_*_<stamp>/<only>`에서 찾는다. 행 번호(`S-03` 등)는 `batch.json`의 `d1_id`에서 읽는다.
- `--row`: 행 폴더를 직접 준다(배치 정보 없이). C-3 두 행은 이름으로 알아본다.
- `--assume C-n=값`: 민감도 확인용이다. 출력에 `deviates_from_rev6`가 붙고, 그 출력은 경로 1 결과로 쓰지 않는다.
- 엔진 구분: `step_series.npz`가 있으면 SCM(run_S9), `pads.npz`에 `crawler_normal_N`이 있으면 L2b, 없으면 L1-R이다.

## 2. 종료 코드와 출력

| 코드 | 뜻 |
|---|---|
| 0 | 끝남, 멈춤 없음 |
| 1 | 확인 실패(봉인 불일치, 시각 원점·S-11 문제) 또는 멈춤(R40-2 보류 미해제) |
| 2 | 입력 없음·잘못됨(행 폴더, `result.json`, 규칙 파일, YAML, `--assume` 값) |
| 3 | 내부 오류(추적은 stderr) |

- 마지막 줄은 JSON(`exit`, 행 수, `seals_ok`, `stops`, `origin_failed`, `deviates_from_rev6`, 행 등급)이다. 그 앞 줄은 `errors N`이다(`tools/verif/log_errors.py`).
- `--out` JSON 항목:
  - 정의와 공개: `definitions_C`, `d_numbers`, `params`(YAML sha256·F_min), `seals`, `disclosure`
  - 행별: `rows[]`(`items`, `gates`, `grade`, `demoted_items`, `origin_check_R5_B1`, 입력 파일 sha256)
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

- 열린 잠금 구간의 J11 창 끝·n_late(R6-B7)는 C-5 J11 재집계 몫이다. 이 판은 대체 다리 집합과 열린 구간 다리만 낸다.
- D-32 사건 행(J-5·U58 창)은 판정 불가로 둔다. 제어 주기 사이의 압력 첨두는 보이지 않는다(R6-B5 한계).
- R40-2 보류 해제(7155행, L1 짝 자릿수 비교)는 값만 내고 사람이 판정한다(멈춤, 종료 1).

## 5. 기존 판정 함수와의 차이 (요건 3, `disclose`)

`git diff --no-index --numstat <기존> <새 판>`(2026-11-13, 새 판 sha256은 커밋 보고 참조). 기존 함수는 범위가 넓은 모듈이라 줄 수 차가 크다. 정의 차이는 3절 표와 rev6 R6-A 표가 원본이다.

| 기존 | 대상 D | 추가 | 삭제 |
|---|---|---|---|
| `04_scripts/03_control/s8/r76_g6_chrono_judge.py` | D-26·27·28·34·35 | 938 | 430 |
| `03_src/outrigger_sim/verify/s8_control.py` | D-31·39 | 910 | 7937 |
| `03_src/outrigger_sim/verify/s6_control.py` | D-29·30·32 | 899 | 3073 |

- 값은 새 판을 고치면 바뀐다. 판정서에는 실행 출력의 `disclosure` 블록 값을 적는다.

## 6. 봉인 대조 (요건 4)

원판·rev1~rev6의 md sha256을 도구 안 상수 `RULES_SEALS`와 각 `.sha256` 첫 토큰에 모두 대조한다. 하나라도 다르면 종료 1, 파일이 없으면 종료 2다. rev6 sha256 = `809e5639…`.

## 7. 시험

`05_tests/unit/test_chrono_rows_judge_4368.py`: 합성 입력 22개와 G-S 실행 경로 1개(`07_results/S9/batch_V5-RESUME-K1-GS_20261113_020211`, 판정 아님, 없으면 건너뜀).
