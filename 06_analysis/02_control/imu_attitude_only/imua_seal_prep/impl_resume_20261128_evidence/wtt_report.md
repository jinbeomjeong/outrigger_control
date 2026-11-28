# worktree_tests — worktree 코드 + 메인 checkout 저장 자료 시험

- worktree `C:\workspace\outrigger_control\.claude\worktrees\v5-imua`, 데이터 root `C:\workspace\outrigger_control`, 바꾼 폴더 07_results, 06_analysis
- pytest 종료 0(모든 시험 통과), 582.9 s · 시험 94: 통과 94, 실패 0, 오류 0, 건너뜀 0, 예상 실패 0, XPASS 0
- probe: `chrono_t45_replay` worktree, `imu_a_harness` worktree, `imua_classify` worktree, `imua_records` not_loaded, `v5_rerun` not_loaded
- 실행 중 바뀐 데이터 경로 6회, 원본 불변 True, 실행 폴더 삭제 True
- worktree git status --porcelain --ignored 줄: 실행 전 32 → 뒤 32
- 오류 0 · 경고 2 · 참고 5

## 복사본

| 파일 | 시험 | `__file__` | 감싼 경로 | 감싸지 않은 글자 |
|---|---|---|---|---|
| `05_tests/unit/test_chrono_t45_replay.py` | 예 | 1 | 25: `PROJECT_ROOT / "07_results"`<br>28: `PROJECT_ROOT / "07_results"`<br>31: `PROJECT_ROOT / "07_results"`<br>35: `PROJECT_ROOT / "07_results"`<br>38: `PROJECT_ROOT / "07_results"`<br>101: `PROJECT_ROOT / "06_analysis"` | 0 |
| `05_tests/unit/test_imua_check_judge.py` | 예 | 1 | 42: `RECORDS_ROOT / "06_analysis"` | 0 |
| `05_tests/unit/test_v5_setting_records.py` | 예 | 2 | 30: `RECORDS_ROOT / "06_analysis"` | 0 |
| `05_tests/unit/test_imua_classify.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_imua_replay.py` | 예 | 1 | - | 0 |
| `05_tests/conftest.py` | - | 1 | - | 0 |

## 발견 사항

### 경고 (warning) — 2건

| 분류 | 위치 | 대상 | 내용 |
|---|---|---|---|
| probe_not_loaded | probe | imua_records | 어느 pytest 프로세스도 import하지 않았다(확인 불가) |
| probe_not_loaded | probe | v5_rerun | 어느 pytest 프로세스도 import하지 않았다(확인 불가) |

### 참고 (info) — 5건

| 분류 | 위치 | 대상 | 내용 |
|---|---|---|---|
| no_data_paths | 05_tests/unit/test_imua_classify.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_imua_replay.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| probe_worktree | probe | chrono_t45_replay | worktree에서 import됨: C:\workspace\outrigger_control\.claude\worktrees\v5-imua\04_scripts\04_hydraulic\coupled\chrono_t45_replay.py (main) |
| probe_worktree | probe | imu_a_harness | worktree에서 import됨: C:\workspace\outrigger_control\.claude\worktrees\v5-imua\04_scripts\04_hydraulic\coupled\imu_a_harness.py (main) |
| probe_worktree | probe | imua_classify | worktree에서 import됨: C:\workspace\outrigger_control\.claude\worktrees\v5-imua\04_scripts\04_hydraulic\coupled\imua_classify.py (main) |


## pytest 로그 끝

```text
........................................................................ [ 76%]
......................                                                   [100%]
94 passed in 582.19s (0:09:42)
```
