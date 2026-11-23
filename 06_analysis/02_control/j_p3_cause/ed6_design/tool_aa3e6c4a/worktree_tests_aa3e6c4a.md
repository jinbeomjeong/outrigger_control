# worktree_tests — worktree 코드 + 메인 checkout 저장 자료 시험

- worktree `C:\workspace\outrigger_control\.claude\worktrees\ed6-run6`, 데이터 root `C:\workspace\outrigger_control`, 바꾼 폴더 07_results
- pytest 종료 0(모든 시험 통과), 70.2 s · 시험 293: 통과 293, 실패 0, 오류 0, 건너뜀 0, 예상 실패 0, XPASS 0
- probe: `j_p3_inputs` worktree, `run_v5` worktree, `jp3_j9main_judge` worktree, `jp3_tjr_judge` worktree
- 실행 중 바뀐 데이터 경로 0회, 원본 불변 True, 실행 폴더 삭제 False
- 오류 0 · 경고 1 · 참고 13

## 복사본

| 파일 | 시험 | `__file__` | 감싼 경로 | 감싸지 않은 글자 |
|---|---|---|---|---|
| `05_tests/unit/test_jp3_addendum_4a3.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_addendum_4a4.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_addendum_4a4_erratum1.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_addendum_4a5.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_addendum_4a8.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_ed5_prelaunch_fix.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_ed5_s1_stored.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_j9main.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_jp3_prelaunch_audit.py` | 예 | 1 | - | 0 |
| `05_tests/conftest.py` | - | 1 | - | 0 |

## 발견 사항

### 경고 (warning) — 1건

| 분류 | 위치 | 대상 | 내용 |
|---|---|---|---|
| rebase_never_used | probe |  | 실행 중 데이터 경로가 한 번도 바뀌지 않았다 |

### 참고 (info) — 13건

| 분류 | 위치 | 대상 | 내용 |
|---|---|---|---|
| no_data_paths | 05_tests/unit/test_jp3_addendum_4a3.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_addendum_4a4.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_addendum_4a4_erratum1.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_addendum_4a5.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_addendum_4a8.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_ed5_prelaunch_fix.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_ed5_s1_stored.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_j9main.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_jp3_prelaunch_audit.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| probe_worktree | probe | j_p3_inputs | worktree에서 import됨: C:\workspace\outrigger_control\.claude\worktrees\ed6-run6\04_scripts\04_hydraulic\coupled\j_p3_inputs.py (main) |
| probe_worktree | probe | run_v5 | worktree에서 import됨: C:\workspace\outrigger_control\.claude\worktrees\ed6-run6\04_scripts\04_hydraulic\coupled\run_v5.py (main) |
| probe_worktree | probe | jp3_j9main_judge | worktree에서 import됨: C:\workspace\outrigger_control\.claude\worktrees\ed6-run6\04_scripts\04_hydraulic\coupled\jp3_j9main_judge.py (main) |
| probe_worktree | probe | jp3_tjr_judge | worktree에서 import됨: C:\workspace\outrigger_control\.claude\worktrees\ed6-run6\04_scripts\04_hydraulic\coupled\jp3_tjr_judge.py (main) |


## pytest 로그 끝

```text
........................................................................ [ 24%]
........................................................................ [ 49%]
........................................................................ [ 73%]
........................................................................ [ 98%]
.....                                                                    [100%]
293 passed in 69.62s (0:01:09)
```
