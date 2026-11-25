# worktree_tests — worktree 코드 + 메인 checkout 저장 자료 시험

- worktree `C:\workspace\outrigger_control\.claude\worktrees\ed7-impl`, 데이터 root `C:\workspace\outrigger_control`, 바꾼 폴더 07_results
- pytest 종료 0(모든 시험 통과), 389.6 s · 시험 343: 통과 343, 실패 0, 오류 0, 건너뜀 0, 예상 실패 0, XPASS 0
- probe: `outrigger_sim` worktree
- 실행 중 바뀐 데이터 경로 6회, 원본 불변 True, 실행 폴더 삭제 False
- 오류 0 · 경고 14 · 참고 3

## 복사본

| 파일 | 시험 | `__file__` | 감싼 경로 | 감싸지 않은 글자 |
|---|---|---|---|---|
| `05_tests/unit/test_two_pressure_cb_moving.py` | 예 | 1 | 272: `Path(__file__).resolve().parents[2] / "07_results"` | 1 |
| `05_tests/unit/test_two_pressure_d1_drain.py` | 예 | 1 | 241: `Path(__file__).resolve().parents[2] / "07_results"` | 1 |
| `05_tests/unit/test_two_pressure_d1_imu.py` | 예 | 2 | 429: `Path(__file__).resolve().parents[2] / "07_results"` | 5 |
| `05_tests/unit/test_two_pressure_d1_steps.py` | 예 | 1 | 266: `Path(__file__).resolve().parents[2] / "07_results"` | 2 |
| `05_tests/unit/test_two_pressure_lock_bound.py` | 예 | 1 | 52: `Path(__file__).resolve().parents[2] / "07_results"` | 1 |
| `05_tests/unit/test_two_pressure_lock_valve.py` | 예 | 1 | 47: `Path(__file__).resolve().parents[2] / "07_results"` | 4 |
| `05_tests/unit/test_ed6_lock_start_b.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_rev6.py` | 예 | 1 | - | 0 |
| `05_tests/conftest.py` | - | 1 | - | 0 |

## 발견 사항

### 경고 (warning) — 14건

| 분류 | 위치 | 대상 | 내용 |
|---|---|---|---|
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_cb_moving.py:334 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 CB batches not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_d1_drain.py:415 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 records absent': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_d1_imu.py:592 |  | 감싸지 않은 데이터 경로 글자 "07_results/S8 D1' ML records not present": 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_d1_imu.py:604 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 ML pilot not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_d1_imu.py:617 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 old ML episodes not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_d1_imu.py:636 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 ML pilot not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_d1_imu.py:720 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 ML pilot not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_d1_steps.py:318 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 old ML episodes absent': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_d1_steps.py:339 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 ML pilot bases not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_lock_bound.py:371 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 ML pilot bases not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_lock_valve.py:286 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 CB batch not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_lock_valve.py:293 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 p1r batch not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_lock_valve.py:304 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 p1r batch not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_lock_valve.py:315 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 ML pilot bases not present': 여기는 worktree를 읽는다 |

### 참고 (info) — 3건

| 분류 | 위치 | 대상 | 내용 |
|---|---|---|---|
| no_data_paths | 05_tests/unit/test_ed6_lock_start_b.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_rev6.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| probe_worktree | probe | outrigger_sim | worktree에서 import됨: C:\workspace\outrigger_control\.claude\worktrees\ed7-impl\03_src\outrigger_sim\__init__.py (main) |


## pytest 로그 끝

```text
........................................................................ [ 20%]
........................................................................ [ 41%]
........................................................................ [ 62%]
........................................................................ [ 83%]
.......................................................                  [100%]
343 passed in 388.90s (0:06:28)
```
