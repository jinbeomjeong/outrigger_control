# worktree_tests — worktree 코드 + 메인 checkout 저장 자료 시험

- worktree `C:\workspace\outrigger_control\.claude\worktrees\ed7-impl`, 데이터 root `C:\workspace\outrigger_control`, 바꾼 폴더 07_results
- pytest 종료 0(모든 시험 통과), 4.8 s · 시험 73: 통과 73, 실패 0, 오류 0, 건너뜀 0, 예상 실패 0, XPASS 0
- probe: `outrigger_sim.control.two_pressure` worktree, `outrigger_sim.control.lock_start_b` worktree, `outrigger_sim.control.c2` worktree
- 실행 중 바뀐 데이터 경로 2회, 원본 불변 True, 실행 폴더 삭제 False
- 오류 0 · 경고 5 · 참고 3

## 복사본

| 파일 | 시험 | `__file__` | 감싼 경로 | 감싸지 않은 글자 |
|---|---|---|---|---|
| `05_tests/unit/test_two_pressure_lock_bound.py` | 예 | 1 | 52: `Path(__file__).resolve().parents[2] / "07_results"` | 1 |
| `05_tests/unit/test_two_pressure_lock_valve.py` | 예 | 1 | 47: `Path(__file__).resolve().parents[2] / "07_results"` | 4 |
| `05_tests/conftest.py` | - | 1 | - | 0 |

## 발견 사항

### 경고 (warning) — 5건

| 분류 | 위치 | 대상 | 내용 |
|---|---|---|---|
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_lock_bound.py:371 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 ML pilot bases not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_lock_valve.py:286 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 CB batch not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_lock_valve.py:293 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 p1r batch not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_lock_valve.py:304 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 p1r batch not present': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_two_pressure_lock_valve.py:315 |  | 감싸지 않은 데이터 경로 글자 '07_results/S8 ML pilot bases not present': 여기는 worktree를 읽는다 |

### 참고 (info) — 3건

| 분류 | 위치 | 대상 | 내용 |
|---|---|---|---|
| probe_worktree | probe | outrigger_sim.control.two_pressure | worktree에서 import됨: C:\workspace\outrigger_control\.claude\worktrees\ed7-impl\03_src\outrigger_sim\control\two_pressure.py (main) |
| probe_worktree | probe | outrigger_sim.control.lock_start_b | worktree에서 import됨: C:\workspace\outrigger_control\.claude\worktrees\ed7-impl\03_src\outrigger_sim\control\lock_start_b.py (main) |
| probe_worktree | probe | outrigger_sim.control.c2 | worktree에서 import됨: C:\workspace\outrigger_control\.claude\worktrees\ed7-impl\03_src\outrigger_sim\control\c2.py (main) |


## pytest 로그 끝

```text
........................................................................ [ 98%]
.                                                                        [100%]
73 passed in 4.33s
```
