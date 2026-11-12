# 436.8 경로 1 새 판 판정기 (`*_4368.py`)

규칙: `v5_resume_4368_rules.md` 원판~rev5(`06_analysis/02_control/verif_matrix/`). rev5 R5-A1이 이 파일들을 하네스 묶음의 경로 1로 지정한다. 기존 판정기(`u3_judge_k1.py`, `judge_stage1_r5.py`, `u9_judge.py`, `las_t3_judge.py`·`las_h7.py`, `d1_runs.judgement`·`d1_select.py`)는 고치지 않았다. `u3_judge_k1.py`는 기록 전용 판이다(R5-A2).

## 공통 계약 (`judge4368_common.py`)

- 판정 전에 원판·rev1~rev5와 각 `.sha256`을 원시 바이트로 대조한다. 하나라도 다르면 S-1(종료 1)이다. 규칙 폴더는 `--rules-dir`(기본 `verif_matrix`).
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
| `d1_judge_4368.py` | H-1·H-2 | `d1_runs.py`(`judgement`), `d1_select.py` | D-23~D-25 | +208 / −514, +205 / −435 |
| (없음) | H-6 | 없음 | D-19 | 미작성 |

새 판은 기존 모듈을 import해 같은 값 계산(읽기·지표·관문)을 그대로 쓰고, 위 항목만 바꾼다. 그래서 numstat는 파일 전체 차이이고, 판정 정의의 차이는 `definition_changes` 목록이 원본이다.

## 실행 (python-dev, 프로젝트 루트)

```
python -I -B 04_scripts/04_hydraulic/coupled/d1_judge_4368.py --out <r.json> --h1 resume_k1/h1_d1.jsonl --regraded <h1_regraded.jsonl> --select-out <h2_select.json>
python -I -B 04_scripts/04_hydraulic/coupled/u3_judge_4368.py --out <r.json> --u3-dir <U-3 출력 폴더> --v4-dir 06_analysis/02_control/s9 --h1-d1 resume_k1/h1_d1.jsonl --g3 <g3.json> [--k1-report <u3_judge_k1 보고서>]
python -I -B 04_scripts/04_hydraulic/coupled/judge_stage1_4368.py --out <r.json> --h9 resume_k1/h9_stage1.jsonl --h10 resume_k1/h10_reuse_rerun.jsonl --t4h-dir <T4h 폴더> [--overlap-ref resume_k1/h10_overlap_t_a.json]
python -I -B 04_scripts/04_hydraulic/coupled/u9_judge_4368.py --out <r.json> --v0 resume_k1/h5_u9_v0.jsonl --h10 resume_k1/h10_reuse_rerun.jsonl --t4h-dir <T4h 폴더> [--stored-p3-hash v5/p3_hash.jsonl]
python -I -B 04_scripts/04_hydraulic/coupled/las_t3_judge_4368.py --out <r.json> --r0 <R-0> --r0k <R-0K> --t3 <T-3K> --baseline v5/d1.jsonl --identity <R-0.identity.json> --identity <R-0K...> --identity <T-3K...> --git-at-start <커밋>
```

## 알려진 한계 (판정서에 적을 것)

- `judge_stage1_4368` SA-4 "정지 뒤 네 다리 ≥ F_min"은 줄에 정지 뒤 최소 필드가 없어 이륙 뒤 최소(`values.forces.after_liftoff.min_kN`)로 본다. 이 값이 F_min 이상이면 충분 조건으로 참, 미만이면 `판정 불가`다. "포화 차단 0"은 `values.pressure.saturation_leg_chunks` = 0으로 읽는다(해석, 확인 필요).
- J-P3 로드 판독은 줄의 T4h 파일(`t4h_file`, `--t4h-dir`)의 `rod_pressure_Pa`로 본다. T4h 파일이 없는 ③ 줄은 `판정 불가`다(하네스 main 줄에는 구성 근거 규칙이 없다).
- `las_t3_judge_4368` K-0: 실제 sidecar(`d8x_record.run_identity`)에는 `git.head`·`git.is_clean`·`git.status_porcelain`·`threads`만 있다. `code_diff_sha256`·`c2_sha256`·`tools_sha256`·`OUTRIGGER_LOC_SHADOW`는 없으므로 G-S에서 대응을 정하기 전에는 그 행이 `판정 불가`다. 출력 헤더의 `identity`는 후보로만 보고한다.
- `u3_judge_4368` 이전 판 비교(V0 − v4)는 `u3_judge_k1`의 기록 방식 그대로이고 판정이 아니다.
